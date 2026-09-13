# -*- coding: utf-8 -*-
"""Chiếu chung: một người dẫn, máy khác theo cùng câu (poll ~1s, RAM 1 worker)."""
from __future__ import annotations

import asyncio
import io
import json
import random
import re
import secrets
import threading
import time

import segno
from flask import Response, jsonify, request, session

import app as base

_LOCK = threading.Lock()
_QS_LOCK = threading.Lock()
_ROOMS: dict = {}
_QS_CACHE: dict = {}
_ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TTL = 6 * 3600


def _now():
    return time.time()


def _prune():
    t = _now()
    dead = [c for c, r in _ROOMS.items() if t - float(r.get("updated") or 0) > _TTL]
    for c in dead:
        _ROOMS.pop(c, None)


def _norm_code(raw):
    c = re.sub(r"[^A-Z0-9]", "", str(raw or "").upper())
    if 3 <= len(c) <= 6:
        return c
    return ""


def _new_code():
    for _ in range(40):
        c = "".join(random.choice(_ALPH) for _ in range(4))
        if c not in _ROOMS and not _weak_code(c):
            return c
    return secrets.token_hex(3).upper()[:6]


def _weak_code(c):
    c = str(c or "").upper()
    if len(c) < 3:
        return True
    if c in {"1234", "12345", "123456", "0000", "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999", "ABCD", "QWER"}:
        return True
    if len(set(c)) == 1:
        return True
    return False


def _host_id():
    if base.admin_current():
        return "ADMIN"
    m = base.member_current()
    if m and base.has_full_bank_access(m):
        return str(m.get("username") or m.get("name") or "admin")
    return ""


def _public_q(q, show_sol):
    p = base.question_payload(q)
    if not show_sol:
        p["solution"] = ""
        p.pop("answer", None)
        for o in p.get("options") or []:
            o["correct"] = False
        for o in p.get("statements") or []:
            o["correct"] = False
    p.pop("src", None)
    p.pop("file_idx", None)
    return p


def _want_sol(data, live, room):
    """Heartbeat ADMIN không gửi show_sol thì giữ trạng thái đã chiếu đáp án."""
    data = data if isinstance(data, dict) else {}
    live = live if isinstance(live, dict) else {}
    if "show_sol" in data:
        return bool(data.get("show_sol")) and bool(live.get("checked"))
    return bool((room or {}).get("show_sol"))


def _teacher_peek_payload(q):
    if not q:
        return None
    p = base.question_payload(q)
    kind = str(p.get("kind") or "").upper()
    labs = "ABCDEFGH"
    hint = ""
    if kind == "TN":
        hint = "".join(
            labs[i]
            for i, o in enumerate(p.get("options") or [])
            if o.get("correct") and i < len(labs)
        )
    elif kind == "DS":
        parts = []
        for i, s in enumerate(p.get("statements") or []):
            lab = labs[i] if i < len(labs) else str(i + 1)
            parts.append(lab + ("Đ" if s.get("correct") else "S"))
        hint = " ".join(parts)
    elif kind == "TLN":
        hint = str(p.get("answer") or "").strip()
    else:
        raw = re.sub(r"<[^>]+>", " ", str(p.get("solution") or ""))
        hint = re.sub(r"\s+", " ", raw).strip()[:180]
    return {"hint": hint or "—", "solution": p.get("solution") or "", "kind": kind}


def _sanitize_live(raw):
    d = raw if isinstance(raw, dict) else {}
    live = {"tn": None, "ds": [], "text": "", "checked": False, "ok": None}
    try:
        if d.get("tn") is not None and d.get("tn") != "":
            n = int(d["tn"])
            live["tn"] = n if 0 <= n <= 8 else None
    except (TypeError, ValueError):
        live["tn"] = None
    ds = d.get("ds")
    if isinstance(ds, list):
        out = []
        for x in ds[:12]:
            if x is True or x == 1 or x == "1":
                out.append(True)
            elif x is False or x == 0 or x == "0":
                out.append(False)
            else:
                out.append(None)
        live["ds"] = out
    live["text"] = str(d.get("text") or "")[:2000]
    live["checked"] = bool(d.get("checked"))
    if d.get("ok") is not None:
        live["ok"] = bool(d.get("ok"))
    return live


_INK_MAX_STROKES = 80
_INK_MAX_POINTS = 160


def _sanitize_ink(raw):
    strokes = raw if isinstance(raw, list) else []
    out = []
    for s in strokes[:_INK_MAX_STROKES]:
        if not isinstance(s, dict):
            continue
        pts = s.get("p")
        if not isinstance(pts, list):
            continue
        clean = []
        for pt in pts[:_INK_MAX_POINTS]:
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                continue
            try:
                x = max(0.0, min(1.0, float(pt[0])))
                y = max(0.0, min(1.0, float(pt[1])))
            except (TypeError, ValueError):
                continue
            if clean:
                dx = x - clean[-1][0]
                dy = y - clean[-1][1]
                if dx * dx + dy * dy < 4e-8:
                    continue
            clean.append([round(x, 4), round(y, 4)])
        if len(clean) < 2:
            continue
        color = str(s.get("c") or "#b91c1c")[:16]
        if not re.match(r"^#[0-9a-fA-F]{3,8}$", color):
            color = "#b91c1c"
        try:
            w = max(1.0, min(12.0, float(s.get("w") or 3)))
        except (TypeError, ValueError):
            w = 3.0
        out.append({"p": clean, "c": color, "w": w})
    return out


def _norm_ans(s):
    t = re.sub(r"\$+", "", str(s or ""))
    t = re.sub(r"\s+", "", t).replace(",", ".").lower()
    return t


def _raw_q_from_room(room):
    path = str((room or {}).get("path") or "")
    ids = list((room or {}).get("ids") or [])
    try:
        pos = int((room or {}).get("pos") or 0)
    except (TypeError, ValueError):
        pos = 0
    if not path or not ids or pos < 0 or pos >= len(ids):
        return None
    try:
        qs = _lesson_qs(path)
    except Exception:
        return None
    return qs.get(ids[pos])


def _score_live(q, live):
    live = _sanitize_live(live)
    kind = str((q or {}).get("kind") or "").upper()
    if kind == "TN":
        opts = q.get("options") or []
        i = live.get("tn")
        if i is None:
            return live, "Hãy chọn một phương án."
        try:
            i = int(i)
        except (TypeError, ValueError):
            return live, "Hãy chọn một phương án."
        if i < 0 or i >= len(opts):
            return live, "Hãy chọn một phương án."
        live["checked"] = True
        live["ok"] = bool(opts[i].get("correct"))
        return live, ""
    if kind == "DS":
        stmts = q.get("statements") or []
        ds = list(live.get("ds") or [])
        if len(ds) < len(stmts) or any(x is not True and x is not False for x in ds[: len(stmts)]):
            return live, "Hãy chọn Đúng/Sai đủ các ý."
        live["ds"] = ds[: len(stmts)]
        live["checked"] = True
        live["ok"] = all(bool(ds[i]) == bool(stmts[i].get("correct")) for i in range(len(stmts)))
        return live, ""
    text = str(live.get("text") or "").strip()
    if not text:
        return live, "Hãy nhập đáp án trước."
    live["checked"] = True
    ans = str((q or {}).get("answer") or "").strip()
    if kind == "TLN" and ans:
        live["ok"] = _norm_ans(text) == _norm_ans(ans)
    else:
        live["ok"] = None
    return live, ""


def _lesson_qs(path):
    path = str(path or "")
    with _QS_LOCK:
        hit = _QS_CACHE.get(path)
        if hit is not None:
            return hit
    qs = {q["idx"]: q for q in base.parse_lesson_questions(path)}
    if not qs:
        _, tex = base.read_tex(path)
        qs = {q["idx"]: q for q in base.parse_questions(tex)}
    with _QS_LOCK:
        if len(_QS_CACHE) > 48:
            _QS_CACHE.clear()
        _QS_CACHE[path] = qs
    return qs


def _zoom(zoom):
    try:
        z = float(zoom if zoom is not None else 1)
    except (TypeError, ValueError):
        z = 1.0
    return max(0.8, min(2.6, z))


def _comp_snapshot(kind, de_path, sec, zoom=None):
    import lythuyet as lt

    kind = "pp" if str(kind or "").strip().lower() == "pp" else "lt"
    de_path = str(de_path or "").strip()
    if not de_path:
        return None, "Thiếu đường dẫn bài."
    if not lt.companion_exists(de_path, kind):
        return None, "Chưa có file lý thuyết / dạng mẫu để chiếu."
    rel = lt.companion_path(de_path, kind)
    try:
        _, tex = base.read_tex(rel)
    except Exception as e:
        return None, str(e)
    secs, start = lt._theory_secs(tex)
    if not secs:
        return None, "Chưa tách được mục (\\subsubsection) để chiếu."
    idx = 0
    sec = str(sec or "").strip()
    if sec:
        found = False
        for i, s in enumerate(secs):
            if str(s.get("id") or "") == sec:
                idx = i
                found = True
                break
        if not found:
            try:
                n = int(sec)
                if 0 <= n < len(secs):
                    idx = n
            except (TypeError, ValueError):
                pass
    s = secs[idx]
    html_body = lt._html_secs([s], start=start + idx, admin=False)
    spec = lt.TRACKS.get(kind) or lt.TRACKS["lt"]
    titles = [str(x.get("title") or f"Mục {i + 1}").strip() or f"Mục {i + 1}" for i, x in enumerate(secs)]
    return {
        "path": de_path,
        "pos": idx,
        "total": len(secs),
        "sec_titles": titles,
        "show_sol": True,
        "zoom": _zoom(zoom),
        "q": {
            "kind": "LT" if kind == "lt" else "PP",
            "text": html_body,
            "title": str(s.get("title") or ""),
            "sec_id": str(s.get("id") or ""),
            "dang": spec["label"],
            "options": [],
            "statements": [],
            "solution": "",
        },
        "dang_nav": [],
        "dang_has_prev": idx > 0,
        "dang_has_next": idx < len(secs) - 1,
        "q_lo": 0,
        "q_hi": max(0, len(secs) - 1),
        "updated": _now(),
    }, ""


def _quiz_nav(qs, ids):
    titles = []
    dang_nav = []
    seen = set()
    n = len(ids)
    for i, qid in enumerate(ids):
        q = qs.get(qid) or {}
        kind = str(q.get("kind") or "?").upper()
        dang = base._dang_name(q)
        titles.append("Câu " + str(i + 1) + "/" + str(n) + " · " + kind)
        if dang not in seen:
            seen.add(dang)
            dang_nav.append({"name": dang, "pos": i})
    return titles, dang_nav


def _dang_index(dang_nav, cur):
    di = 0
    for i, d in enumerate(dang_nav or []):
        try:
            if int(d.get("pos") or 0) <= int(cur or 0):
                di = i
        except (TypeError, ValueError):
            pass
    return di


def _dang_span(qs, ids, pos):
    """Khoảng [lo, hi] inclusive các câu cùng dạng với câu đang chiếu."""
    ids = list(ids or [])
    n = len(ids)
    if n <= 0:
        return 0, -1
    pos = max(0, min(n - 1, int(pos or 0)))
    cur = base._dang_name((qs or {}).get(ids[pos]) or {})
    lo = pos
    while lo > 0 and base._dang_name((qs or {}).get(ids[lo - 1]) or {}) == cur:
        lo -= 1
    hi = pos
    while hi + 1 < n and base._dang_name((qs or {}).get(ids[hi + 1]) or {}) == cur:
        hi += 1
    return lo, hi


def _sort_ids_for_present(qs, ids):
    """Dạng theo thứ tự bài, rồi TN → ĐS → TLN → TL, rồi idx — khối dạng liền nhau."""
    ids = list(ids or [])
    if not ids:
        return ids
    ordered = [qs[k] for k in sorted(qs.keys())] if qs else []
    names, _cnts = base.dang_names_of(ordered)
    dang_rank = {n: i for i, n in enumerate(names)}
    kind_rank = {k: i for i, k in enumerate(base.KIND_ORDER)}
    seen = set()
    uniq = []
    for qid in ids:
        if qid in seen:
            continue
        seen.add(qid)
        uniq.append(qid)

    def key(qid):
        q = (qs or {}).get(qid) or {}
        d = base._dang_name(q)
        k = str(q.get("kind") or "TL").upper()
        try:
            idx = int(qid)
        except (TypeError, ValueError):
            idx = 0
        return (dang_rank.get(d, 999), kind_rank.get(k, 99), idx)

    return sorted(uniq, key=key)


def _dang_step(path, ids, cur, delta, zoom):
    try:
        qs = _lesson_qs(path)
    except Exception as e:
        return None, str(e)
    ids = list(ids or [])
    if not ids:
        return None, "Không chuyển được dạng."
    cur = max(0, min(len(ids) - 1, int(cur or 0)))
    _titles, dang_nav = _quiz_nav(qs, ids)
    di = _dang_index(dang_nav, cur)
    nxt = di + int(delta)
    if 0 <= nxt < len(dang_nav):
        pos = int(dang_nav[nxt].get("pos") or 0)
        return _snapshot(False, zoom, False, {"quiz_path": path, "quiz_ids": ids, "quiz_pos": pos})
    return None, "Hết dạng trong phần đã chọn."


def _pos_after_ids_change(old_ids, old_pos, new_ids):
    """Câu đang chiếu bị bỏ khỏi danh sách → lùi câu liền trước còn lại, không về câu 1."""
    old_ids = list(old_ids or [])
    new_ids = list(new_ids or [])
    if not new_ids:
        return 0
    try:
        old_pos = int(old_pos or 0)
    except (TypeError, ValueError):
        old_pos = 0
    cur = old_ids[old_pos] if 0 <= old_pos < len(old_ids) else None
    if cur is not None and cur in new_ids:
        return new_ids.index(cur)
    for i in range(old_pos - 1, -1, -1):
        if old_ids[i] in new_ids:
            return new_ids.index(old_ids[i])
    for i in range(old_pos, len(old_ids)):
        if old_ids[i] in new_ids:
            return new_ids.index(old_ids[i])
    return max(0, min(len(new_ids) - 1, old_pos))


def _keep_room_cursor(data, room):
    """Heartbeat không gửi sec/ids thì giữ dạng/câu đang chiếu, không về mục 1."""
    if not isinstance(data, dict):
        return
    if "_client_sent_quiz_pos" not in data:
        data["_client_sent_quiz_pos"] = data.get("quiz_pos") is not None
    if not room:
        return
    if str(data.get("comp_kind") or "").strip().lower() in {"lt", "pp"} and not str(data.get("sec") or "").strip():
        data["sec"] = str(((room.get("q") or {}).get("sec_id")) or room.get("pos") or "")
    if data.get("quiz_ids") is None:
        ids = list(room.get("ids") or [])
        if ids:
            data["quiz_ids"] = ids
            if data.get("quiz_pos") is None:
                data["quiz_pos"] = room.get("pos") or 0
            if not str(data.get("quiz_path") or "").strip():
                data["quiz_path"] = str(room.get("path") or "")
        return
    if room.get("ids") is not None:
        try:
            new_ids = [int(x) for x in data.get("quiz_ids") if str(x).isdigit() or isinstance(x, int)]
        except (TypeError, ValueError):
            new_ids = []
        if data.get("quiz_pos") is None:
            data["quiz_pos"] = _pos_after_ids_change(room.get("ids"), room.get("pos"), new_ids)


def _snapshot(show_sol=None, zoom=None, reveal=False, data=None):
    data = data if isinstance(data, dict) else {}
    kind = str(data.get("comp_kind") or "").strip().lower()
    de_path = str(data.get("de_path") or "").strip()
    if kind in {"lt", "pp"} and de_path:
        return _comp_snapshot(kind, de_path, data.get("sec"), zoom)
    path = str(data.get("quiz_path") or session.get("practice_path") or "").strip()
    ids = data.get("quiz_ids")
    if not isinstance(ids, list):
        ids = list(session.get("practice_ids") or [])
    else:
        ids = [int(x) for x in ids if str(x).isdigit() or isinstance(x, int)]
    try:
        pos = int(data.get("quiz_pos") if data.get("quiz_pos") is not None else session.get("practice_pos") or 0)
    except (TypeError, ValueError):
        pos = 0
    sent_pos = data.get("_client_sent_quiz_pos")
    if sent_pos is None:
        sent_pos = data.get("quiz_pos") is not None
    if path and ids:
        try:
            session["practice_path"] = path
            session["practice_ids"] = ids
            if sent_pos:
                session["practice_pos"] = max(0, min(pos, len(ids) - 1))
        except Exception:
            pass
        if sent_pos:
            pos = int(session.get("practice_pos") or 0)
    else:
        path = str(session.get("practice_path") or "")
        ids = list(session.get("practice_ids") or [])
        pos = int(session.get("practice_pos") or 0)
    if ids:
        pos = max(0, min(len(ids) - 1, pos))
    if not path or not ids or pos < 0 or pos >= len(ids):
        return None, "Chưa đang chiếu (vào Lý thuyết / Dạng mẫu / chọn câu bài tập rồi bấm Chiếu)."
    try:
        qs = _lesson_qs(path)
    except Exception as e:
        return None, str(e)
    if data.get("sort_present") and ids:
        cur_id = ids[pos] if 0 <= pos < len(ids) else None
        ids = _sort_ids_for_present(qs, ids)
        if cur_id is not None and cur_id in ids:
            pos = ids.index(cur_id)
        else:
            pos = 0
        try:
            session["practice_ids"] = ids
            session["practice_pos"] = pos
        except Exception:
            pass
    q = qs.get(ids[pos])
    if not q:
        return None, "Không tải được câu hiện tại."
    show = bool(show_sol)
    keys = bool(show or reveal)
    titles, dang_nav = _quiz_nav(qs, ids)
    di = _dang_index(dang_nav, pos)
    q_lo, q_hi = _dang_span(qs, ids, pos)
    has_prev = di > 0
    has_next = di < len(dang_nav) - 1
    return {
        "path": path,
        "ids": ids,
        "pos": pos,
        "total": len(ids),
        "q_lo": q_lo,
        "q_hi": q_hi,
        "sec_titles": titles,
        "dang_nav": dang_nav,
        "dang_has_prev": has_prev,
        "dang_has_next": has_next,
        "show_sol": show,
        "zoom": _zoom(zoom),
        "q": _public_q(q, keys),
        "updated": _now(),
    }, ""


def _room_out(room, include_q=True):
    d = {
        "ok": True,
        "code": room["code"],
        "ver": int(room.get("ver") or 0),
        "pos": int(room.get("pos") or 0),
        "total": int(room.get("total") or 0),
        "q_lo": int(room.get("q_lo") if room.get("q_lo") is not None else 0),
        "q_hi": int(room.get("q_hi") if room.get("q_hi") is not None else max(0, int(room.get("total") or 1) - 1)),
        "show_sol": bool(room.get("show_sol")),
        "zoom": float(room.get("zoom") or 1),
        "host": room.get("host") or "",
        "live": room.get("live") or {},
        "secs": list(room.get("sec_titles") or []),
        "dangs": list(room.get("dang_nav") or []),
        "dang_has_prev": bool(room.get("dang_has_prev")),
        "dang_has_next": bool(room.get("dang_has_next")),
        "ids_sig": str(len(list(room.get("ids") or [])))
        + ":"
        + str((room.get("ids") or [None])[0])
        + ":"
        + str((room.get("ids") or [None])[-1])
        + ":"
        + str(room.get("path") or ""),
        "ink": list(room.get("ink") or []),
    }
    if include_q:
        d["q"] = room.get("q") or {}
    return d


def _companion_kind(snap):
    return str(((snap or {}).get("q") or {}).get("kind") or "")


def _block_kind_steal(room, snap, force_kind):
    if force_kind:
        return False
    old = _companion_kind(room)
    new = _companion_kind(snap)
    if old in {"LT", "PP"} and new in {"LT", "PP"} and old != new:
        return True
    return False


def _put_room(hid, code, token, snap, live, force_kind=False):
    """Tạo/cập nhật phòng. Cùng thầy được lấy lại mã sau khi server restart."""
    with _LOCK:
        _prune()
        room = _ROOMS.get(code) if code else None
        if room and room.get("host") and room.get("host") != hid:
            return None, f"Mã {code} đang được người khác dùng. Chọn mã khác."
        if not room:
            if not code:
                code = _new_code()
            tok = token if token and len(str(token)) >= 8 else secrets.token_hex(8)
            room = {"code": code, "token": tok, "host": hid, "ver": 0}
            _ROOMS[code] = room
        if room.get("q") and _block_kind_steal(room, snap, force_kind):
            room["updated"] = _now()
            session["present_code"] = room["code"]
            session["present_token"] = room["token"]
            return room, ""
        prev_fp = (
            room.get("pos"),
            room.get("total"),
            bool(room.get("show_sol")),
            (room.get("q") or {}).get("kind"),
            (room.get("q") or {}).get("text"),
            json.dumps(room.get("live") or {}, sort_keys=True, ensure_ascii=False),
        )
        room.update(snap)
        qk = str((snap.get("q") or {}).get("kind") or "")
        if qk in {"LT", "PP"}:
            room["ids"] = []
            room["dang_nav"] = []
        room["live"] = live
        room["host"] = hid
        room["code"] = code
        ink_q = (
            room.get("path"),
            room.get("pos"),
            (room.get("q") or {}).get("kind"),
            (room.get("q") or {}).get("text"),
        )
        if room.get("_ink_q") != ink_q:
            room["ink"] = []
            room["_ink_q"] = ink_q
        new_fp = (
            room.get("pos"),
            room.get("total"),
            bool(room.get("show_sol")),
            (room.get("q") or {}).get("kind"),
            (room.get("q") or {}).get("text"),
            json.dumps(live, sort_keys=True, ensure_ascii=False),
        )
        if prev_fp != new_fp:
            room["ver"] = int(room.get("ver") or 0) + 1
        room["updated"] = _now()
        session["present_code"] = room["code"]
        session["present_token"] = room["token"]
        return room, ""


@base.app.post("/api/present/start")
def api_present_start():
    hid = _host_id()
    if not hid:
        return jsonify(ok=False, error="Hãy đăng nhập để mở phòng chiếu."), 401
    data = dict(request.get_json(silent=True) or {})
    live = _sanitize_live(data.get("live"))
    fresh = bool(data.get("fresh"))
    want_pre = "" if fresh else _norm_code(data.get("code") or session.get("present_code") or "")
    if want_pre and _weak_code(want_pre) and want_pre not in _ROOMS:
        want_pre = ""
    if data.get("quiz_ids") is not None:
        data["sort_present"] = True
    with _LOCK:
        room_pre = _ROOMS.get(want_pre)
        _keep_room_cursor(data, room_pre)
        want_sol = _want_sol(data, live, room_pre)
    snap, err = _snapshot(want_sol, data.get("zoom"), reveal=want_sol, data=data)
    if not snap:
        return jsonify(ok=False, error=err), 400
    want = "" if fresh else _norm_code(data.get("code"))
    if want and _weak_code(want) and want not in _ROOMS:
        want = ""
    if data.get("code") not in (None, "") and not fresh and not want and not _weak_code(_norm_code(data.get("code"))):
        return jsonify(ok=False, error="Mã phải 3–6 ký tự (chữ hoặc số), ví dụ K7M2."), 400
    with _LOCK:
        _prune()
        old = _norm_code(session.get("present_code"))
        mine = old if old in _ROOMS and _ROOMS[old].get("host") == hid else None
        if fresh:
            for c, r0 in list(_ROOMS.items()):
                if r0.get("host") == hid:
                    _ROOMS.pop(c, None)
            mine = None
            want = ""
        if want:
            taken = _ROOMS.get(want)
            if taken and taken.get("host") != hid:
                return jsonify(ok=False, error=f"Mã {want} đang được người khác dùng. Chọn mã khác."), 409
            if mine and mine != want:
                room = _ROOMS.pop(mine)
                room["code"] = want
                _ROOMS[want] = room
                mine = want
            elif taken and taken.get("host") == hid:
                mine = want
        if mine:
            room = _ROOMS[mine]
            force_kind = bool(data.get("force_kind"))
            if not (room.get("q") and _block_kind_steal(room, snap, force_kind)):
                room.update(snap)
                room["live"] = live
                room["ver"] = int(room.get("ver") or 0) + 1
            session["present_code"] = room["code"]
            session["present_token"] = room["token"]
        else:
            code = want or _new_code()
            tok = secrets.token_hex(8)
            room = {"code": code, "token": tok, "host": hid, "ver": 1, "live": live, **snap}
            _ROOMS[code] = room
            session["present_code"] = code
            session["present_token"] = tok
    origin = request.host_url.rstrip("/")
    url = origin + "/xem/" + room["code"]
    return jsonify(ok=True, code=room["code"], url=url, token=session.get("present_token") or room["token"], ver=room["ver"])


@base.app.post("/api/present/push")
def api_present_push():
    hid = _host_id()
    if not hid:
        return jsonify(ok=False, error="Chưa đăng nhập."), 401
    data = dict(request.get_json(silent=True) or {})
    code = _norm_code(data.get("code") or session.get("present_code") or "")
    token = str(data.get("token") or session.get("present_token") or "")
    live = _sanitize_live(data.get("live"))
    if bool(data.get("force_kind")) and data.get("quiz_ids") is not None:
        data["sort_present"] = True
    with _LOCK:
        room_pre = _ROOMS.get(code)
        _keep_room_cursor(data, room_pre)
        want_sol = _want_sol(data, live, room_pre)
    snap, err = _snapshot(want_sol, data.get("zoom"), reveal=want_sol, data=data)
    if not snap:
        with _LOCK:
            room = _ROOMS.get(code)
            if room and room.get("host") == hid:
                room["live"] = live
                room["show_sol"] = want_sol
                room["ver"] = int(room.get("ver") or 0) + 1
                room["updated"] = _now()
                return jsonify(ok=True, ver=room["ver"], pos=room.get("pos"), total=room.get("total"), token=room.get("token"))
        return jsonify(ok=False, error=err), 400
    if not code:
        return jsonify(ok=False, error="Thiếu mã phòng."), 400
    room, rerr = _put_room(hid, code, token, snap, live, force_kind=bool(data.get("force_kind")))
    if not room:
        return jsonify(ok=False, error=rerr), 409
    return jsonify(ok=True, ver=room["ver"], pos=snap["pos"], total=snap["total"], token=room.get("token"), code=room["code"])


@base.app.post("/api/present/stop")
def api_present_stop():
    code = _norm_code((request.get_json(silent=True) or {}).get("code") or session.get("present_code") or "")
    token = str((request.get_json(silent=True) or {}).get("token") or session.get("present_token") or "")
    with _LOCK:
        room = _ROOMS.get(code)
        if room and room.get("token") == token:
            _ROOMS.pop(code, None)
    session.pop("present_code", None)
    session.pop("present_token", None)
    return jsonify(ok=True)


@base.app.get("/api/present/state")
def api_present_state():
    code = _norm_code(request.args.get("code") or "")
    try:
        since = int(request.args.get("ver") or 0)
    except (TypeError, ValueError):
        since = 0
    with _LOCK:
        _prune()
        room = _ROOMS.get(code)
        if not room:
            return jsonify(
                ok=False,
                waiting=True,
                error="Chưa có phòng mã này. Thầy phải vào làm bài, bấm 📺 Chiếu chung, rồi dùng đúng mã hiện trên thanh (hoặc đặt mã này).",
            ), 404
        ver = int(room.get("ver") or 0)
        room["updated"] = _now()
        if since and since == ver:
            return jsonify(ok=True, unchanged=True, ver=ver)
        qk = str((room.get("q") or {}).get("kind") or "")
        if qk in {"LT", "PP"} and not room.get("sec_titles"):
            kind = "pp" if qk == "PP" else "lt"
            snap, _err = _comp_snapshot(kind, room.get("path"), room.get("pos"), room.get("zoom"))
            if snap:
                room["sec_titles"] = list(snap.get("sec_titles") or [])
        out = _room_out(room)
    return jsonify(out)


@base.app.post("/api/present/peek")
def api_present_peek():
    data = request.get_json(silent=True) or {}
    code = _norm_code(data.get("code") or request.args.get("code") or "")
    token = str(data.get("token") or request.args.get("token") or "")
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token:
            return jsonify(ok=False, error="Chỉ máy thầy xem gợi ý được."), 401
        qk = str((room.get("q") or {}).get("kind") or "")
        pos = int(room.get("pos") or 0)
        raw = _raw_q_from_room(room) if qk not in {"LT", "PP"} else None
    if qk in {"LT", "PP"}:
        return jsonify(ok=True, kind=qk, hint="", solution="", pos=pos)
    peek = _teacher_peek_payload(raw)
    if not peek:
        return jsonify(ok=False, error="Không tải được đáp án."), 400
    peek.update(ok=True, pos=pos)
    return jsonify(peek)


def _tts_speak_letters(x: str) -> str:
    x = re.sub(r"[\\{}]", "", str(x or "")).replace(" ", "")
    if re.fullmatch(r"[A-Z]{2,8}", x):
        return " ".join(x)
    return x


def _tts_speak_tex(t: str) -> str:
    t = str(t or "")

    def vec(m):
        return " vectơ " + _tts_speak_letters(m.group(1)) + " "

    t = re.sub(r"\\overrightarrow\s*\{([^{}]*)\}", vec, t)
    t = re.sub(r"\\vec\s*\{([^{}]*)\}", vec, t)
    t = re.sub(r"\\overline\s*\{([^{}]*)\}", lambda m: " " + _tts_speak_letters(m.group(1)) + " ", t)
    t = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", lambda m: " " + _tts_speak_tex(m.group(1)) + " trên " + _tts_speak_tex(m.group(2)) + " ", t)
    t = re.sub(r"\\sqrt\s*\{([^{}]*)\}", lambda m: " căn " + _tts_speak_tex(m.group(1)) + " ", t)
    t = re.sub(r"\\(?:left|right)\b", "", t)
    t = re.sub(r"\\[,;!]|\\quad|\\qquad", " ", t)
    t = re.sub(r"\\(?:times|cdot|ast)\b", " nhân ", t)
    t = re.sub(r"\\(?:leq|le)\b", " nhỏ hơn hoặc bằng ", t)
    t = re.sub(r"\\(?:geq|ge)\b", " lớn hơn hoặc bằng ", t)
    t = re.sub(r"\\(?:neq|ne)\b", " khác ", t)
    t = re.sub(r"\\approx\b", " khoảng ", t)
    t = re.sub(r"\\infty\b", " vô cực ", t)
    t = re.sub(r"\\pi\b", " pi ", t)
    t = re.sub(r"\\(?:mathrm|text)\s*\{([^{}]*)\}", r" \1 ", t)
    t = re.sub(r"\^{2}|\^\{2\}", " bình ", t)
    t = re.sub(r"\^\{([^}]+)\}", r" mũ \1 ", t)
    t = re.sub(r"\|([^|]+)\|", r" độ dài \1 ", t)
    t = re.sub(r"\\[a-zA-Z]+", " ", t)
    t = re.sub(r"[{}]", "", t)
    t = t.replace("=", " bằng ").replace("+", " cộng ").replace("-", " trừ ")
    t = re.sub(r"\b([A-Z]{2,8})\b", lambda m: " ".join(m.group(1)), t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _tts_speak_latex(raw: str) -> str:
    s = str(raw or "")

    def wrap(m):
        return " " + _tts_speak_tex(m.group(1)) + " "

    s = re.sub(r"\$\$([\s\S]*?)\$\$", wrap, s)
    s = re.sub(r"\$([^$]+)\$", wrap, s)
    s = re.sub(r"\\\(([\s\S]*?)\\\)", wrap, s)
    s = re.sub(r"\\\[([\s\S]*?)\\\]", wrap, s)
    s = re.sub(r"\\?overrightarrow\s*\{([^{}]*)\}", lambda m: " vectơ " + _tts_speak_letters(m.group(1)) + " ", s)
    s = re.sub(r"\|([^|]+)\|", r" độ dài \1 ", s)
    s = re.sub(r"vectơ\s+vectơ", "vectơ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


@base.app.post("/api/present/tts")
def api_present_tts():
    if not _host_id():
        return jsonify(ok=False, error="Chỉ ADMIN mới đọc được."), 401
    data = request.get_json(silent=True) or {}
    raw = _tts_speak_latex(str(data.get("text") or ""))
    raw = re.sub(r"\s+", " ", raw).strip()[:4000]
    if len(raw) < 2:
        return jsonify(ok=False, error="Không có chữ để đọc."), 400
    gender = "m" if str(data.get("gender") or "").strip().lower() in {"m", "male", "nam"} else "f"
    voice = "vi-VN-NamMinhNeural" if gender == "m" else "vi-VN-HoaiMyNeural"

    async def _synth():
        import edge_tts

        buf = io.BytesIO()
        comm = edge_tts.Communicate(raw, voice, rate="-3%", pitch="-2Hz" if gender == "m" else "+0Hz")
        async for chunk in comm.stream():
            if chunk.get("type") == "audio":
                buf.write(chunk.get("data") or b"")
        return buf.getvalue()

    try:
        try:
            mp3 = asyncio.run(_synth())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                mp3 = loop.run_until_complete(_synth())
            finally:
                loop.close()
    except Exception as e:
        return jsonify(ok=False, error="Chưa đọc được giọng Việt online: " + str(e)[:180]), 502
    if not mp3:
        return jsonify(ok=False, error="Không tạo được âm thanh."), 502
    return Response(mp3, mimetype="audio/mpeg", headers={"Cache-Control": "no-store"})


@base.app.post("/api/present/step")
def api_present_step():
    data = request.get_json(silent=True) or {}
    code = _norm_code(data.get("code") or "")
    token = str(data.get("token") or "")
    have_abs = data.get("pos") is not None and str(data.get("pos")) != ""
    mode = str(data.get("mode") or "q").strip().lower()
    try:
        delta = int(data.get("delta") or 0)
    except (TypeError, ValueError):
        delta = 0
    try:
        abs_pos = int(data.get("pos")) if have_abs else None
    except (TypeError, ValueError):
        abs_pos = None
        have_abs = False
    if not code or (not have_abs and delta not in (-1, 1)):
        return jsonify(ok=False, error="Thiếu hướng chuyển câu / dạng."), 400
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token:
            return jsonify(ok=False, error="Chỉ máy thầy đổi dạng được."), 401
        q = room.get("q") or {}
        qk = str(q.get("kind") or "")
        path = str(room.get("path") or "")
        cur = int(room.get("pos") or 0)
        pos = abs_pos if have_abs else cur + delta
        ids = list(room.get("ids") or [])
        zoom = room.get("zoom")
        hid = str(room.get("host") or "")
        show_sol = False
        live_clear = {"tn": None, "ds": [], "text": "", "checked": False, "ok": None}
    if qk in {"LT", "PP"}:
        pos = max(0, min(max(1, int((room or {}).get("total") or 1)) - 1, pos))
        kind = "pp" if qk == "PP" else "lt"
        snap, err = _comp_snapshot(kind, path, pos, zoom)
    elif ids and mode == "dang" and not have_abs:
        snap, err = _dang_step(path, ids, cur, delta, zoom)
    elif ids:
        pos = max(0, min(len(ids) - 1, pos))
        snap, err = _snapshot(False, zoom, reveal=False, data={"quiz_path": path, "quiz_ids": ids, "quiz_pos": pos})
    else:
        return jsonify(ok=False, error="Không chuyển được câu."), 400
    if not snap:
        return jsonify(ok=False, error=err or "Không tải được."), 400
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token:
            return jsonify(ok=False, error="Phòng đã tắt."), 401
        hid = str(room.get("host") or hid)
    room, rerr = _put_room(hid, code, token, snap, live_clear, force_kind=True)
    if not room:
        return jsonify(ok=False, error=rerr), 409
    return jsonify(ok=True, pos=room.get("pos"), total=room.get("total"), ver=room.get("ver"))


@base.app.post("/api/present/reveal")
def api_present_reveal():
    hid = _host_id()
    if not hid:
        return jsonify(ok=False, error="Hãy đăng nhập ADMIN trên máy đang chiếu."), 401
    data = request.get_json(silent=True) or {}
    code = _norm_code(data.get("code") or session.get("present_code") or "")
    token = str(data.get("token") or session.get("present_token") or "")
    show = bool(data.get("show_sol"))
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token or str(room.get("host") or "") != hid:
            return jsonify(ok=False, error="Không phải phòng của bạn."), 401
        qk = str((room.get("q") or {}).get("kind") or "")
        path = str(room.get("path") or "")
        ids = list(room.get("ids") or [])
        pos = int(room.get("pos") or 0)
        zoom = room.get("zoom")
        live = room.get("live") if isinstance(room.get("live"), dict) else {}
    live = _sanitize_live(live)
    if qk in {"LT", "PP"}:
        return jsonify(ok=True, show_sol=False, ver=int((room or {}).get("ver") or 0))
    if show and not live.get("checked"):
        return jsonify(ok=False, error="Hãy chọn đáp án và bấm Xác nhận trước."), 400
    snap, err = _snapshot(show, zoom, reveal=show, data={"quiz_path": path, "quiz_ids": ids, "quiz_pos": pos})
    if not snap:
        return jsonify(ok=False, error=err or "Không tải được câu."), 400
    room, rerr = _put_room(hid, code, token, snap, live if isinstance(live, dict) else {}, force_kind=True)
    if not room:
        return jsonify(ok=False, error=rerr), 409
    return jsonify(ok=True, show_sol=bool(room.get("show_sol")), ver=room.get("ver"))


@base.app.post("/api/present/live")
def api_present_live():
    hid = _host_id()
    if not hid:
        return jsonify(ok=False, error="Hãy đăng nhập ADMIN trên máy đang chiếu."), 401
    data = request.get_json(silent=True) or {}
    code = _norm_code(data.get("code") or session.get("present_code") or "")
    token = str(data.get("token") or session.get("present_token") or "")
    commit = bool(data.get("commit"))
    incoming = _sanitize_live(data.get("live"))
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token or str(room.get("host") or "") != hid:
            return jsonify(ok=False, error="Không phải phòng của bạn."), 401
        qk = str((room.get("q") or {}).get("kind") or "")
        path = str(room.get("path") or "")
        ids = list(room.get("ids") or [])
        pos = int(room.get("pos") or 0)
        zoom = room.get("zoom")
        show_sol = bool(room.get("show_sol"))
        old = _sanitize_live(room.get("live") if isinstance(room.get("live"), dict) else {})
    if qk in {"LT", "PP"}:
        return jsonify(ok=True, ver=int((room or {}).get("ver") or 0))
    if old.get("checked") and not commit:
        return jsonify(ok=True, ver=int((room or {}).get("ver") or 0), live=old)
    if commit:
        if old.get("checked"):
            incoming = old
        else:
            q = _raw_q_from_room({"path": path, "ids": ids, "pos": pos})
            if not q:
                return jsonify(ok=False, error="Không tải được câu."), 400
            incoming, err = _score_live(q, incoming)
            if err:
                return jsonify(ok=False, error=err), 400
        want_sol = show_sol and bool(incoming.get("checked"))
        snap, err = _snapshot(want_sol, zoom, reveal=want_sol, data={"quiz_path": path, "quiz_ids": ids, "quiz_pos": pos})
        if not snap:
            return jsonify(ok=False, error=err or "Không tải được câu."), 400
        room, rerr = _put_room(hid, code, token, snap, incoming, force_kind=True)
        if not room:
            return jsonify(ok=False, error=rerr), 409
        return jsonify(ok=True, ver=room.get("ver"), live=room.get("live") or incoming)
    incoming["checked"] = False
    incoming["ok"] = None
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token or str(room.get("host") or "") != hid:
            return jsonify(ok=False, error="Phòng đã tắt."), 401
        room["live"] = incoming
        room["ver"] = int(room.get("ver") or 0) + 1
        room["updated"] = _now()
        return jsonify(ok=True, ver=room["ver"], live=incoming)


@base.app.post("/api/present/ink")
def api_present_ink():
    hid = _host_id()
    if not hid:
        return jsonify(ok=False, error="Hãy đăng nhập ADMIN trên máy chiếu."), 401
    data = request.get_json(silent=True) or {}
    code = _norm_code(data.get("code") or "")
    token = str(data.get("token") or "")
    ink = _sanitize_ink(data.get("ink"))
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token or str(room.get("host") or "") != hid:
            return jsonify(ok=False, error="Phòng đã tắt."), 401
        prev = room.get("ink") or []
        if json.dumps(prev, sort_keys=True) != json.dumps(ink, sort_keys=True):
            room["ink"] = ink
            room["ver"] = int(room.get("ver") or 0) + 1
        room["updated"] = _now()
        return jsonify(ok=True, ver=int(room.get("ver") or 0))


@base.app.get("/xem/<code>/qr.svg")
def present_qr_svg(code):
    code = _norm_code(code)
    if not code:
        return Response("Mã không hợp lệ.", status=400, mimetype="text/plain")
    url = request.host_url.rstrip("/") + "/xem/" + code
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=4, border=2)
    return Response(buf.getvalue(), mimetype="image/svg+xml")


@base.app.get("/xem")
@base.app.get("/xem/<code>")
def present_watch(code=""):
    code = _norm_code(code or request.args.get("code") or "")
    if not code:
        body = (
            "<div class='wrap'><div class='panel' style='max-width:480px;margin:40px auto'><div class='head'>📺 Vào chiếu chung</div><div class='body'>"
            "<p class='muted'>Gõ đúng mã thầy đưa sau khi bấm <b>Chiếu chung</b> (4 ký tự, đổi mỗi buổi). Không dùng mã buổi trước — phòng cũ đã tắt.</p>"
            "<form method='get' action='/xem' style='display:flex;gap:8px;flex-wrap:wrap'>"
            "<input name='code' maxlength='8' inputmode='text' autocomplete='off' placeholder='Mã thầy đưa' style='flex:1;min-width:140px;padding:12px;font-size:16px;letter-spacing:.2em;text-transform:uppercase;text-align:center;border:1px solid #cbd8e6;border-radius:8px'>"
            "<button class='btn primary' type='submit'>Vào xem</button></form>"
            "<p class='muted'>Không cần đăng nhập. Trang tự theo câu / lý thuyết / dạng mẫu thầy đang chiếu.</p>"
            "</div></div></div>"
            "<script>document.querySelector('form').addEventListener('submit',function(e){e.preventDefault();var c=(this.code.value||'').trim().toUpperCase();if(c)location.href='/xem/'+encodeURIComponent(c)})</script>"
        )
        return base.page("Vào chiếu chung", body)
    js = FOLLOW_JS.replace("__CODE__", json.dumps(code))
    qr_src = "/xem/" + code + "/qr.svg"
    body = (
        "<div class='cinema-q'>"
        "<button type='button' class='cinema-exit' id='cinemaExit' title='Thoát chiếu'>✕</button>"
        "<div class='cinemahost' id='cinemaHost' hidden>"
        "<div class='cinema-navrow' id='dangNav' hidden>"
        "<span class='cinema-navlab'>Dạng</span>"
        "<button type='button' class='cinema-tool' id='secPrev' title='Dạng trước'>◀</button>"
        "<select id='dangJump' aria-label='Chọn dạng'></select>"
        "<button type='button' class='cinema-tool' id='secNext' title='Dạng sau'>▶</button>"
        "</div>"
        "<div class='cinema-navrow' id='qNav'>"
        "<span class='cinema-navlab'>Câu</span>"
        "<button type='button' class='cinema-tool' id='qPrev' title='Câu trước cùng dạng'>◀</button>"
        "<select id='secJump' aria-label='Chọn câu trong dạng'></select>"
        "<button type='button' class='cinema-tool' id='qNext' title='Câu sau cùng dạng'>▶</button>"
        "</div>"
        "<button type='button' class='cinema-tool' id='chkToggle' hidden>✅ Xác nhận</button>"
        "<button type='button' class='cinema-tool' id='peekToggle' hidden>💡 Gợi ý</button>"
        "<button type='button' class='cinema-tool' id='inkToggle' hidden>✏️ Bút</button>"
        "<button type='button' class='cinema-tool' id='inkClear' hidden>🧹 Xóa</button>"
        "<button type='button' class='cinema-tool' id='solToggle' hidden>📖 Đáp án</button>"
        "<button type='button' class='cinema-tool' id='aiToggle' hidden>🤖 Phản biện</button>"
        "<button type='button' class='cinema-tool spk-f'>Nữ</button>"
        "<button type='button' class='cinema-tool spk-m'>Nam</button>"
        "<button type='button' class='cinema-tool spk-play'>▶ Đọc</button>"
        "<button type='button' class='cinema-tool spk-pause'>⏸</button>"
        "<button type='button' class='cinema-tool cinema-leave' id='cinemaLeave' title='Thoát chiếu, về màn trước'>✕</button>"
        "<span class='spkmsg' id='spkMsg'></span>"
        "</div>"
        "<div class='cinema-qr is-min' id='cinemaQr'>"
        "<div class='qr-tools'>"
        "<button type='button' id='qrHide' title='Ẩn QR'>✕</button>"
        "<button type='button' id='qrShrink' title='Thu nhỏ QR'>−</button>"
        "<button type='button' id='qrGrow' title='Mở rộng QR để quét'>+</button>"
        "</div>"
        "<img src='" + qr_src + "' width='72' height='72' alt='QR vào chiếu'>"
        "<span>Quét · " + code + "</span></div>"
        "<div id='cinemaPeek' class='cinema-peek' hidden></div>"
        "<div id='perr' class='err'></div>"
        "<div class='cinema-stage'><div id='q' class='qbox' hidden></div>"
        "<div class='cinema-inkpad' id='cinemaInkPad'>"
        "<div class='cinema-inktools'>"
        "<span>Ô ghi</span>"
        "<button type='button' class='inkpaper' data-paper='lines'>Kẻ hàng</button>"
        "<button type='button' class='inkpaper' data-paper='grid'>Lưới mờ</button>"
        "<button type='button' class='inkpaper' data-paper='plain'>Không kẻ</button>"
        "<button type='button' class='inkpaper' id='inkTaller'>Hạ ô ▾</button>"
        "<button type='button' class='inkpaper' id='inkShorter'>Thu ▴</button>"
        "</div>"
        "<div class='cinema-inkframe' data-paper='lines'><canvas id='cinemaInk' class='cinema-ink' width='1' height='1'></canvas></div>"
        "<div class='cinema-inkresize' id='inkResize' title='Kéo xuống để ghi thêm'>▾ kéo xuống để ghi thêm ▾</div>"
        "</div></div>"
        "<div class='cinema-ai' id='cinemaAi' hidden></div></div>"
        + js
    )
    extra = PRESENT_TTS_JS + (base.GEMINI_CLIENT_JS if _host_id() else "")
    return base.page("Chiếu chung " + code, body + extra, cinema=True)


PRESENT_TTS_JS = r"""
<script>
(function(){
if(window.ldvlSpeak) return;
const U={
  gender:(function(){try{return localStorage.getItem('ldvlSpeakG')||'f'}catch(e){return 'f'}})(),
  mode:'idle', wantPlay:false, gen:0, sig:'', audio:null, auto:false, unlocked:false, piece:false, lastEl:null
};
function msg(s){
  document.querySelectorAll('#spkMsg, .spkmsg').forEach(function(el){el.textContent=s||'';});
}
function paint(){
  document.querySelectorAll('#spkF, .spk-f').forEach(function(f){f.classList.toggle('on', U.gender==='f');});
  document.querySelectorAll('#spkM, .spk-m').forEach(function(m){m.classList.toggle('on', U.gender==='m');});
  document.querySelectorAll('#spkPlay, .spk-play').forEach(function(play){play.disabled=U.mode==='play';});
  document.querySelectorAll('#spkPause, .spk-pause').forEach(function(pause){pause.disabled=U.mode!=='play';});
  document.querySelectorAll('#spkResume, .spk-resume').forEach(function(resume){resume.disabled=U.mode!=='pause';});
}
function speakLetters(x){
  x=String(x||'').replace(/\\/g,'').replace(/[{}]/g,'').replace(/\s+/g,'').trim();
  if(/^[A-Z]{2,8}$/.test(x)) return x.split('').join(' ');
  return x;
}
function speakTexBody(t){
  t=String(t||'');
  t=t.replace(/\\overrightarrow\s*\{([^{}]*)\}/g,function(_,x){return ' vectơ '+speakLetters(x)+' ';});
  t=t.replace(/\\vec\s*\{([^{}]*)\}/g,function(_,x){return ' vectơ '+speakLetters(x)+' ';});
  t=t.replace(/\\overline\s*\{([^{}]*)\}/g,function(_,x){return ' '+speakLetters(x)+' ';});
  t=t.replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g,function(_,a,b){return ' '+speakTexBody(a)+' trên '+speakTexBody(b)+' ';});
  t=t.replace(/\\sqrt\s*\{([^{}]*)\}/g,function(_,x){return ' căn '+speakTexBody(x)+' ';});
  t=t.replace(/\\left|\\right/g,'');
  t=t.replace(/\\,|\\;|\\!|\\quad|\\qquad/g,' ');
  t=t.replace(/\\times|\\cdot|\\ast/g,' nhân ');
  t=t.replace(/\\leq|\\le/g,' nhỏ hơn hoặc bằng ');
  t=t.replace(/\\geq|\\ge/g,' lớn hơn hoặc bằng ');
  t=t.replace(/\\neq|\\ne/g,' khác ');
  t=t.replace(/\\approx/g,' khoảng ');
  t=t.replace(/\\infty/g,' vô cực ');
  t=t.replace(/\\pi/g,' pi ');
  t=t.replace(/\\alpha/g,' alpha ');
  t=t.replace(/\\beta/g,' beta ');
  t=t.replace(/\\theta/g,' theta ');
  t=t.replace(/\\Delta/g,' delta ');
  t=t.replace(/\\mathrm\s*\{([^{}]*)\}/g,' $1 ');
  t=t.replace(/\\text\s*\{([^{}]*)\}/g,' $1 ');
  t=t.replace(/\^{2}|\^\{2\}/g,' bình ');
  t=t.replace(/\^\{([^}]+)\}/g,' mũ $1 ');
  t=t.replace(/\|([^|]+)\|/g,function(_,x){return ' độ dài '+x+' ';});
  t=t.replace(/\\[a-zA-Z]+/g,' ');
  t=t.replace(/[{}]/g,'');
  t=t.replace(/=/g,' bằng ');
  t=t.replace(/\+/g,' cộng ');
  t=t.replace(/-/g,' trừ ');
  t=t.replace(/\b([A-Z]{2,8})\b/g,function(_,x){return x.split('').join(' ');});
  t=t.replace(/\s+/g,' ').trim();
  return t;
}
function speakLatex(s){
  s=String(s||'');
  s=s.replace(/\$\$([\s\S]*?)\$\$/g,function(_,m){return ' '+speakTexBody(m)+' ';});
  s=s.replace(/\$([^$]+)\$/g,function(_,m){return ' '+speakTexBody(m)+' ';});
  s=s.replace(/\\\(([\s\S]*?)\\\)/g,function(_,m){return ' '+speakTexBody(m)+' ';});
  s=s.replace(/\\\[([\s\S]*?)\\\]/g,function(_,m){return ' '+speakTexBody(m)+' ';});
  s=s.replace(/\\?overrightarrow\s*\{([^{}]*)\}/g,function(_,x){return ' vectơ '+speakLetters(x)+' ';});
  s=s.replace(/\|([^|]+)\|/g,function(_,x){return ' độ dài '+x+' ';});
  return s.replace(/vectơ\s+vectơ/gi,'vectơ').replace(/\s+/g,' ').trim();
}
function speakTextOf(el){
  if(!el) return '';
  const c=el.cloneNode(true);
  c.querySelectorAll('script,style,button,.ltsec-tools,.cinemahud,.present-host,.cinema-qr,.qid,.pickmark,.qbadge,.spkmsg,.cinemaspeak,.spkchunk').forEach(function(n){n.remove()});
  c.querySelectorAll('mjx-container, .MathJax').forEach(function(n){
    const lab=n.getAttribute('aria-label')||n.textContent||'';
    n.replaceWith(document.createTextNode(' '+lab+' '));
  });
  return speakLatex((c.innerText||c.textContent||'').replace(/\u00a0/g,' '));
}
function kindLabel(k){
  k=String(k||'').toUpperCase();
  return {TN:'Trắc nghiệm',DS:'Đúng sai',TLN:'Trả lời ngắn',TL:'Tự luận',LT:'Lý thuyết',PP:'Dạng mẫu'}[k]||'';
}
function dangSpeak(q){
  const d=String((q&&q.dang)||'').trim();
  const k=kindLabel(q&&q.kind);
  if(!d) return k?('Dạng '+k):'';
  let s=d.replace(/\s*[-–]\s*\b(TN|DS|TLN|TL)\b\s*$/i, function(_,x){return ' '+kindLabel(x);});
  if(k && s.toLowerCase().indexOf(k.toLowerCase())<0) s=s+' '+k;
  return 'Dạng '+s;
}
function dangHtml(q){
  const t=dangSpeak(q);
  if(!t) return '';
  const e=String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  return '<div class="qdang">'+e+'</div>';
}
function target(){
  const q=document.getElementById('q');
  if(q && !q.hidden && (q.innerText||'').trim()) return q;
  const jump=document.getElementById('ltjump');
  if(jump && jump.value){
    const el=document.getElementById(jump.value);
    if(el) return el;
  }
  const h=(location.hash||'').replace(/^#/,'');
  if(h){
    const el=document.getElementById(h);
    if(el) return el;
  }
  return document.querySelector('.ltpage .ltsec') || document.querySelector('.ltpage');
}
function stopHard(){
  U.gen+=1;
  try{speechSynthesis.cancel()}catch(e){}
  if(U.audio){
    try{U.audio.onended=null; U.audio.pause(); U.audio.src='';}catch(e){}
    U.audio=null;
  }
}
function playAudio(url, gen){
  return new Promise(function(resolve, reject){
    const a=new Audio(url);
    U.audio=a;
    a.onended=function(){ if(U.gen===gen) resolve('end'); };
    a.onerror=function(){ reject(new Error('audio')); };
    const p=a.play();
    if(p&&p.catch) p.catch(reject);
  });
}
async function playNet(text, gen){
  msg(U.gender==='m'?'Nam Minh…':'Hoài My…');
  const r=await fetch('/api/present/tts',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({text:text,gender:U.gender})});
  if(U.gen!==gen) return;
  if(!r.ok){
    const d=await r.json().catch(function(){return {}});
    throw new Error(d.error||('tts '+r.status));
  }
  const blob=await r.blob();
  if(U.gen!==gen) return;
  const url=URL.createObjectURL(blob);
  msg(U.gender==='m'?'Nam Minh':'Hoài My');
  await playAudio(url, gen);
}
function pickVoice(){
  let vs=[];
  try{vs=speechSynthesis.getVoices()||[]}catch(e){}
  const vi=vs.filter(function(v){
    const lang=String(v.lang||'').toLowerCase();
    const name=String(v.name||'').toLowerCase();
    return lang.indexOf('vi')===0 || name.indexOf('viet')>=0 || name.indexOf('việt')>=0;
  });
  const want=U.gender==='m'
    ? /nam\s*minh|namminh|\bmale\b/
    : /hoai\s*my|hoaimy|linh|nữ|\bnu\b|female|\bmy\b/;
  return vi.filter(function(v){return want.test(String(v.name||'').toLowerCase())})[0] || vi[0] || null;
}
function playLocal(text, gen){
  return new Promise(function(resolve){
    const v=pickVoice();
    const u=new SpeechSynthesisUtterance(text);
    u.lang='vi-VN';
    if(v) u.voice=v;
    u.rate=U.gender==='m'?0.92:1;
    u.pitch=U.gender==='m'?0.72:1.18;
    u.onend=function(){ if(U.gen===gen) resolve(); };
    u.onerror=function(){ if(U.gen===gen) resolve(); };
    speechSynthesis.speak(u);
  });
}
function splitSpeak(t){
  t=String(t||'').trim();
  const max=2800, out=[];
  while(t.length>max){
    let cut=t.lastIndexOf('. ', max);
    if(cut<Math.floor(max*0.4)) cut=max;
    out.push(t.slice(0,cut).trim());
    t=t.slice(cut).replace(/^[.\s]+/,'').trim();
  }
  if(t) out.push(t);
  return out;
}
async function run(text){
  const gen=++U.gen;
  U.mode='play'; U.wantPlay=true; paint();
  if(!navigator.onLine){ msg('Cần mạng để đọc giọng Nam/Nữ.'); U.mode='idle'; U.wantPlay=false; paint(); return; }
  const parts=splitSpeak(text);
  try{
    for(let i=0;i<parts.length;i++){
      if(U.gen!==gen) return;
      await playNet(parts[i], gen);
    }
  }catch(e){
    if(U.gen!==gen) return;
    msg('Giọng máy…');
    await playLocal(text, gen);
  }
  if(U.gen!==gen) return;
  if(U.mode==='play'){ U.mode='idle'; if(!U.auto) U.wantPlay=false; paint(); msg(''); }
}
function startReadText(t, asPiece){
  t=speakLatex(String(t||'').trim());
  if(!t){ msg('Không có chữ để đọc.'); return; }
  U.piece=asPiece!==false;
  if(!U.piece) U.sig=t.length+':'+(t.slice(0,60));
  stopHard();
  try{ new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA').play().catch(function(){}); }catch(e){}
  U.unlocked=true; U.auto=false; U.wantPlay=true;
  run(t);
}
async function cinemaRead(){
  const bits=[];
  const q=document.getElementById('q');
  if(q && !q.hidden) bits.push(speakTextOf(q));
  const ai=document.getElementById('aiout');
  const wrap=document.getElementById('cinemaAi');
  if(ai && (!wrap || !wrap.hidden) && (ai.innerText||'').replace(/\s+/g,' ').trim().length>20){
    bits.push('Phản biện. '+speakTextOf(ai));
  }
  startReadText(bits.filter(Boolean).join('. '), false);
}
function startRead(){
  if(isCinema()){ cinemaRead(); return; }
  const pane=document.getElementById('aiout');
  if(U.lastEl && pane && pane.contains(U.lastEl)) startReadText(speakTextOf(U.lastEl), true);
  else if(pane && pane.innerText.trim()) startReadText(speakTextOf(pane), true);
  else startReadText(speakTextOf(target()), false);
}
function isCinema(){return !!(document.body&&document.body.classList.contains('cinema'));}
function canClickHost(host){
  if(!host||!host.matches) return false;
  if(isCinema()) return !host.matches('label');
  return host.matches('.solution, .ai-y, .ai-sec, .qdang, details.lt-sol');
}
function markReading(host, btn){
  document.querySelectorAll('.spkchunk.on').forEach(function(x){x.classList.remove('on')});
  document.querySelectorAll('.spkhost.on').forEach(function(x){x.classList.remove('on')});
  if(btn) btn.classList.add('on');
  if(host) host.classList.add('on');
}
function addSpk(host, src){
  if(isCinema()) return;
  if(!host||!src) return;
  if(!host.querySelector(':scope > .spkchunk, :scope > summary > .spkchunk')){
    const b=document.createElement('button');
    b.type='button';
    b.className='spkchunk';
    b.title='Đọc đoạn này';
    b.setAttribute('aria-label','Đọc đoạn này');
    b.textContent='🔊';
    b.onclick=function(ev){
      ev.preventDefault();
      ev.stopPropagation();
      markReading(host, b);
      U.lastEl=src;
      startReadText(speakTextOf(src), true);
    };
    const sum=host.tagName==='DETAILS'?host.querySelector('summary'):null;
    if(sum) sum.appendChild(b);
    else host.appendChild(b);
  }
  if(!host.__spkClick && canClickHost(host)){
    host.__spkClick=1;
    host.classList.add('spkhost');
    host.addEventListener('click', function(ev){
      if(ev.target.closest('button,a,input,textarea,select,label,.spkchunk')) return;
      ev.preventDefault();
      ev.stopPropagation();
      markReading(host, host.querySelector(':scope > .spkchunk, :scope > summary > .spkchunk'));
      U.lastEl=src;
      startReadText(speakTextOf(src), true);
    });
  }
}
function mountChunks(root){
  if(isCinema()){
    (root&&root.querySelectorAll?root:document).querySelectorAll('.spkchunk').forEach(function(n){n.remove()});
    return;
  }
  root=root||document;
  function skipWhole(el){return el && el.matches && el.matches('.reviewout') && el.querySelector('.ai-sec,.ai-y');}
  if(root.nodeType===1 && root.id!=='gkey-ping' && !skipWhole(root) && (root.matches('.ltbox, details.lt-sol, .qheadline, .qdang, .opt, .tf, .solution, .ai-y, .ai-sec, .reviewout') || root.id==='aiout')){
    const src=root.matches('.qheadline')?(root.querySelector('.qstem')||root):root;
    addSpk(root, src);
  }
  root.querySelectorAll('.ltbox').forEach(function(box){
    const k=box.querySelector(':scope > .k');
    addSpk(k||box, box);
  });
  root.querySelectorAll('details.lt-sol').forEach(function(d){ addSpk(d, d); });
  root.querySelectorAll('.ltbox-body > ol > li').forEach(function(li){ addSpk(li, li); });
  root.querySelectorAll('.qheadline').forEach(function(el){ addSpk(el, el); });
  root.querySelectorAll('.qdang').forEach(function(el){ addSpk(el, el); });
  root.querySelectorAll('.opt, .tf, .solution').forEach(function(el){ addSpk(el, el); });
  root.querySelectorAll('.ai-sec, .ai-y').forEach(function(el){ addSpk(el, el); });
  root.querySelectorAll('.reviewout').forEach(function(el){
    if(el.id==='gkey-ping' || skipWhole(el)) return;
    addSpk(el, el);
  });
}
window.ldvlSpeak={
  play:function(){ startRead(); },
  playEl:function(el){ U.lastEl=el||null; startReadText(speakTextOf(el), true); },
  mountChunks:mountChunks,
  stop:function(){
    stopHard();
    U.mode='idle'; U.wantPlay=false; U.piece=false; paint(); msg('');
  },
  pause:function(){
    if(U.mode!=='play') return;
    U.mode='pause';
    if(U.audio && !U.audio.paused){ try{U.audio.pause()}catch(e){} }
    else { try{speechSynthesis.pause(); if(!speechSynthesis.paused) speechSynthesis.cancel();}catch(e){} }
    paint();
  },
  resume:function(){
    if(U.mode!=='pause'){ startRead(); return; }
    U.mode='play'; U.wantPlay=true; paint();
    if(U.audio){
      const p=U.audio.play();
      if(p&&p.catch) p.catch(function(){ startRead(); });
      return;
    }
    try{ if(speechSynthesis.paused){ speechSynthesis.resume(); return; } }catch(e){}
    startRead();
  },
  setGender:function(g){
    U.gender=g==='m'?'m':'f';
    try{localStorage.setItem('ldvlSpeakG', U.gender)}catch(e){}
    paint();
    if(U.mode==='play'||U.wantPlay) startRead();
  },
  onDraw:function(){
    const t=speakTextOf(target());
    const sig=t.length+':'+(t.slice(0,60));
    if(sig===U.sig) return;
    U.sig=sig;
    if(U.mode==='play' && !U.piece){ stopHard(); U.mode='idle'; U.wantPlay=false; paint(); }
    else if(U.mode!=='play' && U.mode!=='pause'){ U.mode='idle'; U.wantPlay=false; paint(); }
    mountChunks(document.getElementById('q')||document);
    const pane=document.getElementById('aipane')||document.getElementById('cinemaAi');
    if(pane) mountChunks(pane);
  },
  bind:function(){
    U.auto=false;
    const gate=document.getElementById('spkGate');
    if(gate) gate.hidden=true;
    if(!document.getElementById('spkPlay') && !document.querySelector('.spk-play')){
      const host=document.getElementById('presentHost');
      if(host){
        const row=document.createElement('div');
        row.className='presentspeak';
        row.innerHTML='<button type="button" class="btn" id="spkF">Nữ</button><button type="button" class="btn" id="spkM">Nam</button><button type="button" class="btn primary" id="spkPlay">▶ Đọc</button><button type="button" class="btn" id="spkPause">⏸ Dừng</button><button type="button" class="btn" id="spkResume">▶ Tiếp</button><span class="spkmsg" id="spkMsg"></span>';
        host.appendChild(row);
      }
    }
    function wire(sel, fn){
      document.querySelectorAll(sel).forEach(function(el){
        if(el.__spk) return;
        el.__spk=1;
        el.onclick=fn;
      });
    }
    wire('#spkF, .spk-f', function(){ window.ldvlSpeak.setGender('f'); });
    wire('#spkM, .spk-m', function(){ window.ldvlSpeak.setGender('m'); });
    wire('#spkPlay, .spk-play', function(){ window.ldvlSpeak.play(); });
    wire('#spkPause, .spk-pause', function(){ window.ldvlSpeak.stop(); });
    wire('#spkResume, .spk-resume', function(){ window.ldvlSpeak.resume(); });
    const jump=document.getElementById('ltjump');
    if(jump && !jump.__spk){
      jump.__spk=1;
      jump.addEventListener('change', function(){ if(U.wantPlay && U.mode!=='pause') startRead(); });
    }
    try{ speechSynthesis.getVoices(); }catch(e){}
    paint();
    mountChunks(document);
  }
};
document.addEventListener('visibilitychange', function(){
  if(document.hidden && U.mode==='play') window.ldvlSpeak.pause();
});
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', function(){ window.ldvlSpeak.bind(); });
else window.ldvlSpeak.bind();
})();
</script>
"""

FOLLOW_JS = r"""
<script>
const CODE=__CODE__;
let lastVer=-1;
let lastDrawKey='';
let lastQ=null;
let lastLive={};
let lastShowSol=false;
let lastPeekPos=-1;
let inkStrokes=[];
let inkDrawing=false;
let inkCur=null;
let inkTimer=0;
let inkLocalAt=0;
let lastInkQ='';
function hostTok(){
  try{
    const p=JSON.parse(localStorage.getItem('ldvlPresent')||'null');
    if(p&&String(p.code||'').toUpperCase()===String(CODE).toUpperCase()&&p.token) return p;
  }catch(e){}
  return null;
}
function paintSecNav(pos,total,secs,kind,dangs,dangPrev,dangNext,qLo,qHi){
  const bar=document.getElementById('cinemaHost');
  const jump=document.getElementById('secJump');
  const qPrev=document.getElementById('qPrev'), qNext=document.getElementById('qNext');
  const a=document.getElementById('secPrev'), b=document.getElementById('secNext');
  const dangJump=document.getElementById('dangJump');
  const dangNav=document.getElementById('dangNav');
  const qNav=document.getElementById('qNav');
  const on=!!hostTok();
  if(bar) bar.hidden=!on;
  if(!on){paintHostTools();return;}
  const n=Math.max(1, total||1);
  const p=Math.max(0, Math.min(n-1, pos||0));
  const k=String(kind||'').toUpperCase();
  const quiz=k && k!=='LT' && k!=='PP';
  let lo=0, hi=n-1;
  if(quiz){
    lo=Math.max(0, Math.min(n-1, Number(qLo)));
    hi=Math.max(lo, Math.min(n-1, Number(qHi)));
    if(!isFinite(lo)) lo=0;
    if(!isFinite(hi)) hi=n-1;
  }
  if(qNav) qNav.hidden=false;
  if(qPrev){ qPrev.hidden=!on; qPrev.disabled=!(p>lo); qPrev.textContent='◀'; qPrev.title=quiz?'Câu trước cùng dạng':'Mục trước'; }
  if(qNext){ qNext.hidden=!on; qNext.disabled=!(p<hi); qNext.textContent='▶'; qNext.title=quiz?'Câu sau cùng dạng':'Mục sau'; }
  const lab={PP:'Dạng',LT:'Mục'}[k]||'Câu';
  let titles=Array.isArray(secs)&&secs.length?secs.map(function(t,i){return String(t||'').trim()||(lab+' '+(i+1));}):null;
  if(!titles) titles=Array.from({length:n},function(_,i){return lab+' '+(i+1)+' / '+n;});
  const localN=hi-lo+1;
  const localTitles=titles.slice(lo, hi+1);
  if(jump){
    const fp=lo+'\x1f'+hi+'\x1f'+localTitles.join('\x1f');
    if(jump.dataset.fp!==fp){
      jump.innerHTML=localTitles.map(function(t,i){
        return '<option value="'+(lo+i)+'">'+(i+1)+'/'+localN+'. '+E(t)+'</option>';
      }).join('');
      jump.dataset.fp=fp;
    }
    jump.value=String(p);
  }
  const rows=Array.isArray(dangs)?dangs:[];
  if(dangNav) dangNav.hidden=!quiz;
  if(quiz && dangJump){
    const dfp=rows.map(function(d){return String(d.pos)+'\x1f'+String(d.name||'');}).join('\n');
    if(dangJump.dataset.fp!==dfp){
      dangJump.innerHTML=rows.map(function(d,i){
        const nm=String(d.name||('Dạng '+(i+1))).trim()||('Dạng '+(i+1));
        return '<option value="'+Number(d.pos||0)+'">'+(i+1)+'. '+E(nm)+'</option>';
      }).join('');
      dangJump.dataset.fp=dfp;
    }
    let di=0;
    for(let i=0;i<rows.length;i++) if(p>=Number(rows[i].pos||0)) di=i;
    if(rows[di]) dangJump.value=String(rows[di].pos||0);
  }
  if(a){ a.hidden=!quiz; a.disabled=quiz?!dangPrev:true; }
  if(b){ b.hidden=!quiz; b.disabled=quiz?!dangNext:true; }
  paintHostTools();
}
function hideCinemaAi(){
  const pane=document.getElementById('cinemaAi');
  if(pane) pane.hidden=true;
  hideCinemaPeek();
}
function hideCinemaPeek(){
  const el=document.getElementById('cinemaPeek');
  if(el){ el.hidden=true; el.innerHTML=''; }
  const b=document.getElementById('peekToggle');
  if(b) b.classList.remove('on');
}
function isQuizQ(q){
  const k=String((q&&q.kind)||'').toUpperCase();
  return k && k!=='LT' && k!=='PP';
}
function cinemaReady(){
  const q=lastQ||{};
  const live=lastLive||{};
  const k=String(q.kind||'').toUpperCase();
  if(k==='TN') return live.tn!=null && live.tn!=='';
  if(k==='DS'){
    const n=(q.statements||[]).length;
    const ds=live.ds||[];
    if(!n || ds.length<n) return false;
    for(let i=0;i<n;i++) if(ds[i]!==true && ds[i]!==false) return false;
    return true;
  }
  return String(live.text||'').trim().length>0;
}
function paintHostTools(){
  const on=!!hostTok();
  const quiz=on && isQuizQ(lastQ);
  const done=!!(lastLive&&lastLive.checked);
  document.body.classList.toggle('is-host', on);
  document.body.classList.toggle('sol-on', !!lastShowSol);
  const chk=document.getElementById('chkToggle');
  const peek=document.getElementById('peekToggle');
  const sol=document.getElementById('solToggle');
  const ai=document.getElementById('aiToggle');
  if(chk){
    chk.hidden=!quiz || !!lastShowSol;
    chk.disabled=done || !cinemaReady();
    chk.textContent=done?'✅ Đã xác nhận':'✅ Xác nhận';
    chk.title=done?'Đã khóa lựa chọn':(cinemaReady()?'Khóa đáp án lớp chọn':'Hãy chọn đủ đáp án trước.');
  }
  if(peek){
    peek.hidden=!quiz;
    peek.disabled=false;
    peek.title='Chỉ máy thầy — lớp không thấy cho đến khi bấm Đáp án.';
  }
  if(sol){
    sol.hidden=!quiz;
    sol.disabled=!done && !lastShowSol;
    sol.classList.toggle('on', !!lastShowSol);
    sol.textContent=lastShowSol?'🙈 Ẩn đáp án':'📖 Đáp án';
    sol.title=done||lastShowSol?'':'Hãy chọn đáp án và bấm Xác nhận trước.';
  }
  if(ai){
    ai.hidden=!quiz;
    ai.disabled=!done;
    ai.title=done?'':'Hãy chọn đáp án và bấm Xác nhận trước.';
  }
  const inkBtn=document.getElementById('inkToggle');
  const inkClr=document.getElementById('inkClear');
  if(inkBtn){
    inkBtn.hidden=!on;
    inkBtn.classList.toggle('on', on && document.body.classList.contains('ink-on'));
    inkBtn.title='Viết trong ô ghi chú bên dưới. Tắt Bút để chọn đáp án.';
  }
  if(inkClr) inkClr.hidden=!on;
}
async function presentReveal(show){
  const p=hostTok(); if(!p) return false;
  if(show && !(lastLive&&lastLive.checked)){
    alert('Hãy chọn đáp án và bấm Xác nhận trước.');
    return false;
  }
  const r=await fetch('/api/present/reveal',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({code:p.code,token:p.token,show_sol:!!show})});
  const d=await r.json().catch(function(){return {}});
  if(!d||!d.ok){alert((d&&d.error)||'Không hiện được đáp án. Đăng nhập ADMIN trên máy này.');return false;}
  lastVer=-1;
  await tick();
  return true;
}
async function presentLive(patch, commit){
  const p=hostTok(); if(!p) return false;
  const live=Object.assign({tn:null,ds:[],text:'',checked:false,ok:null}, lastLive||{}, patch||{});
  if(patch && Object.prototype.hasOwnProperty.call(patch,'ds')) live.ds=patch.ds;
  const r=await fetch('/api/present/live',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({code:p.code,token:p.token,live:live,commit:!!commit})});
  const d=await r.json().catch(function(){return {}});
  if(!d||!d.ok){alert((d&&d.error)||'Không gửi được lựa chọn.');return false;}
  lastVer=-1;
  await tick();
  return true;
}
function cinemaDsCopy(){
  const n=((lastQ&&lastQ.statements)||[]).length;
  const ds=(lastLive.ds||[]).slice();
  while(ds.length<n) ds.push(null);
  return ds.slice(0,n);
}
function bindCinemaPick(){
  if(!hostTok() || lastShowSol || (lastLive&&lastLive.checked) || !isQuizQ(lastQ)) return;
  if(document.body.classList.contains('ink-on')) return;
  const k=String((lastQ&&lastQ.kind)||'').toUpperCase();
  document.querySelectorAll('#q .opt').forEach(function(el,i){
    el.onclick=function(){ presentLive({tn:i}, false); };
  });
  document.querySelectorAll('#q .tf').forEach(function(row,i){
    const yes=row.querySelector('.tf-box.yes');
    const no=row.querySelector('.tf-box.no');
    if(yes) yes.onclick=function(){ const ds=cinemaDsCopy(); ds[i]=true; presentLive({ds:ds}, false); };
    if(no) no.onclick=function(){ const ds=cinemaDsCopy(); ds[i]=false; presentLive({ds:ds}, false); };
  });
  const save=document.getElementById('cinemaAnsSave');
  const inp=document.getElementById('cinemaAns');
  if(save && inp && (k==='TLN'||k==='TL')){
    save.onclick=function(){ presentLive({text:String(inp.value||'')}, false); };
  }
}
function liveStudent(q, live){
  live=live||{};
  const k=String((q&&q.kind)||'').toUpperCase();
  if(k==='TN') return live.tn==null||live.tn===''?'':String.fromCharCode(65+Number(live.tn));
  if(k==='DS') return (live.ds||[]).map(function(x){return x===true?'Đ':(x===false?'S':'')}).join('');
  return String(live.text||'').trim();
}
async function stepDang(delta, mode){
  const p=hostTok(); if(!p) return;
  hideCinemaAi();
  const r=await fetch('/api/present/step',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({code:p.code,token:p.token,delta:delta,mode:mode||'q'})});
  const d=await r.json().catch(function(){return {}});
  if(d&&d.error){ alert(d.error); return; }
  clearInkCanvas();
  lastVer=-1; tick();
}
async function jumpPos(pos){
  const p=hostTok(); if(!p) return;
  hideCinemaAi();
  const r=await fetch('/api/present/step',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({code:p.code,token:p.token,pos:pos})});
  const d=await r.json().catch(function(){return {}});
  if(d&&d.error){ alert(d.error); return; }
  clearInkCanvas();
  lastVer=-1; tick();
}
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function dangLine(q){
  const d=String((q&&q.dang)||'').trim();
  const k={TN:'Trắc nghiệm',DS:'Đúng sai',TLN:'Trả lời ngắn',TL:'Tự luận',LT:'Lý thuyết',PP:'Dạng mẫu'}[String((q&&q.kind)||'').toUpperCase()]||'';
  if(!d) return k?('Dạng '+k):'';
  let s=d.replace(/\s*[-–]\s*\b(TN|DS|TLN|TL)\b\s*$/i, function(_,x){
    const lab={TN:'Trắc nghiệm',DS:'Đúng sai',TLN:'Trả lời ngắn',TL:'Tự luận'}[String(x).toUpperCase()]||x;
    return ' '+lab;
  });
  if(k && s.toLowerCase().indexOf(k.toLowerCase())<0) s=s+' '+k;
  return 'Dạng '+s;
}
function drawKey(q, showSol, pos, total, live){
  live=live||{};
  if(q&&(q.kind==='LT'||q.kind==='PP')) return [q.kind,pos,total,q.title||''].join('\x1f');
  return [q&&q.kind,q&&q.dang,pos,total,!!showSol,q&&q.text||'',live.tn,JSON.stringify(live.ds||[]),live.text||'',!!live.checked,live.ok].join('\x1f');
}
let inkCssH=0;
function clampInkH(h){
  return Math.max(140, Math.min(Math.round(window.innerHeight*0.9), Math.max(140, h|0)));
}
function setInkPadHeight(h, remap){
  const pad=document.getElementById('cinemaInkPad');
  const frame=document.querySelector('.cinema-inkframe');
  if(!frame) return;
  h=clampInkH(h);
  frame.style.height=h+'px';
  if(pad) pad.style.setProperty('--ink-h', h+'px');
  try{localStorage.setItem('ldvlInkH', String(h))}catch(e){}
  if(remap!==false) sizeInk();
}
function sizeInk(){
  const cv=document.getElementById('cinemaInk');
  const frame=document.querySelector('.cinema-inkframe');
  if(!cv||!frame) return;
  const r=frame.getBoundingClientRect();
  if(r.width<8||r.height<8) return;
  if(inkCssH && Math.abs(inkCssH-r.height)>2){
    const k=inkCssH/r.height;
    function remap(s){ (s.p||[]).forEach(function(pt){ pt[1]=Math.max(0, Math.min(1, pt[1]*k)); }); }
    inkStrokes.forEach(remap);
    if(inkCur) remap(inkCur);
  }
  inkCssH=r.height;
  const dpr=Math.min(2, window.devicePixelRatio||1);
  const w=Math.max(1, Math.floor(r.width*dpr));
  const h=Math.max(1, Math.floor(r.height*dpr));
  if(cv.width!==w || cv.height!==h){
    cv.width=w; cv.height=h;
  }
  paintInk();
}
function clearInkCanvas(){
  clearTimeout(inkTimer);
  inkStrokes=[];
  inkCur=null;
  inkDrawing=false;
  inkLocalAt=0;
  lastInkQ='';
  const cv=document.getElementById('cinemaInk');
  if(cv){
    const ctx=cv.getContext('2d');
    if(ctx) ctx.clearRect(0,0,cv.width,cv.height);
  }
}
function paintInk(){
  const cv=document.getElementById('cinemaInk');
  if(!cv) return;
  const ctx=cv.getContext('2d');
  if(!ctx) return;
  const w=cv.width, h=cv.height;
  ctx.clearRect(0,0,w,h);
  const strokes=inkStrokes.slice();
  if(inkCur&&inkCur.p&&inkCur.p.length) strokes.push(inkCur);
  strokes.forEach(function(s){
    const pts=s.p||[];
    if(pts.length<1) return;
    ctx.beginPath();
    ctx.strokeStyle=s.c||'#b91c1c';
    ctx.lineWidth=Math.max(2, (s.w||3)*Math.min(w,h)/280);
    ctx.lineCap='round';
    ctx.lineJoin='round';
    pts.forEach(function(pt,i){
      const x=pt[0]*w, y=pt[1]*h;
      if(i) ctx.lineTo(x,y); else ctx.moveTo(x,y);
    });
    if(pts.length===1){
      ctx.lineTo(pts[0][0]*w+0.01, pts[0][1]*h);
    }
    ctx.stroke();
  });
}
function applyInk(d){
  const qk=String((d&&d.pos)||0)+'\x1f'+String((d&&d.q&&d.q.text)||'').slice(0,120);
  if(qk!==lastInkQ){
    clearInkCanvas();
    lastInkQ=qk;
  }
  if(inkDrawing || (Date.now()-inkLocalAt)<500) return;
  inkStrokes=Array.isArray(d.ink)?d.ink:[];
  paintInk();
}
function pushInkSoon(){
  clearTimeout(inkTimer);
  inkTimer=setTimeout(pushInk, 140);
}
function inkPayload(){
  const s=inkStrokes.slice();
  if(inkCur&&inkCur.p&&inkCur.p.length) s.push(inkCur);
  return s;
}
async function pushInk(){
  const p=hostTok(); if(!p) return;
  try{
    await fetch('/api/present/ink',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({code:p.code,token:p.token,ink:inkPayload()})});
  }catch(e){}
}
function bindCinemaInk(){
  const cv=document.getElementById('cinemaInk');
  if(!cv || cv.dataset.bound==='1') return;
  cv.dataset.bound='1';
  function pos(ev){
    const r=cv.getBoundingClientRect();
    const x=(ev.clientX-r.left)/Math.max(1,r.width);
    const y=(ev.clientY-r.top)/Math.max(1,r.height);
    return [Math.max(0,Math.min(1,x)), Math.max(0,Math.min(1,y))];
  }
  function down(ev){
    if(!hostTok() || !document.body.classList.contains('ink-on')) return;
    if(ev.pointerType==='mouse' && ev.button!==0) return;
    ev.preventDefault();
    try{cv.setPointerCapture(ev.pointerId)}catch(e){}
    inkDrawing=true;
    inkLocalAt=Date.now();
    inkCur={p:[pos(ev)],c:'#b91c1c',w:3};
    paintInk();
  }
  function move(ev){
    if(!inkDrawing||!inkCur) return;
    ev.preventDefault();
    const pt=pos(ev);
    const last=inkCur.p[inkCur.p.length-1];
    if(last){
      const dx=pt[0]-last[0], dy=pt[1]-last[1];
      if(dx*dx+dy*dy<4e-6) return;
    }
    inkCur.p.push(pt);
    if(inkCur.p.length>160) inkCur.p=inkCur.p.slice(-160);
    inkLocalAt=Date.now();
    paintInk();
    pushInkSoon();
  }
  function up(ev){
    if(!inkDrawing) return;
    if(ev) try{cv.releasePointerCapture(ev.pointerId)}catch(e){}
    if(inkCur&&inkCur.p&&inkCur.p.length){
      if(inkCur.p.length===1){
        const a=inkCur.p[0];
        inkCur.p=[a,[Math.min(1,a[0]+0.002),a[1]]];
      }
      inkStrokes.push(inkCur);
      if(inkStrokes.length>80) inkStrokes=inkStrokes.slice(-80);
    }
    inkCur=null;
    inkDrawing=false;
    inkLocalAt=Date.now();
    paintInk();
    pushInk();
  }
  cv.addEventListener('pointerdown', down);
  cv.addEventListener('pointermove', move);
  cv.addEventListener('pointerup', up);
  cv.addEventListener('pointercancel', up);
}
function setInkPaper(kind){
  const frame=document.querySelector('.cinema-inkframe');
  if(!frame) return;
  const k=(kind==='grid'||kind==='plain')?kind:'lines';
  frame.setAttribute('data-paper', k);
  try{localStorage.setItem('ldvlInkPaper', k)}catch(e){}
  document.querySelectorAll('.cinema-inktools .inkpaper[data-paper]').forEach(function(b){
    b.classList.toggle('on', b.getAttribute('data-paper')===k);
  });
}
function bindInkPadUi(){
  const pad=document.getElementById('cinemaInkPad');
  if(!pad || pad.dataset.ui==='1') return;
  pad.dataset.ui='1';
  let paper='lines', h=220;
  try{paper=localStorage.getItem('ldvlInkPaper')||'lines'}catch(e){}
  try{h=parseInt(localStorage.getItem('ldvlInkH')||'220',10)||220}catch(e){}
  setInkPaper(paper);
  setInkPadHeight(h, false);
  document.querySelectorAll('.cinema-inktools .inkpaper[data-paper]').forEach(function(b){
    b.onclick=function(){ setInkPaper(b.getAttribute('data-paper')); };
  });
  const taller=document.getElementById('inkTaller');
  const shorter=document.getElementById('inkShorter');
  if(taller) taller.onclick=function(){
    const frame=document.querySelector('.cinema-inkframe');
    setInkPadHeight((frame?frame.getBoundingClientRect().height:220)+90);
  };
  if(shorter) shorter.onclick=function(){
    const frame=document.querySelector('.cinema-inkframe');
    setInkPadHeight((frame?frame.getBoundingClientRect().height:220)-80);
  };
  const grip=document.getElementById('inkResize');
  if(grip){
    let drag=false, y0=0, h0=220;
    function start(ev){
      if(ev.pointerType==='mouse' && ev.button!==0) return;
      ev.preventDefault();
      drag=true;
      y0=ev.clientY;
      const frame=document.querySelector('.cinema-inkframe');
      h0=frame?frame.getBoundingClientRect().height:220;
      try{grip.setPointerCapture(ev.pointerId)}catch(e){}
    }
    function move(ev){
      if(!drag) return;
      ev.preventDefault();
      setInkPadHeight(h0+(ev.clientY-y0));
    }
    function end(ev){
      if(!drag) return;
      drag=false;
      try{grip.releasePointerCapture(ev.pointerId)}catch(e){}
    }
    grip.addEventListener('pointerdown', start);
    grip.addEventListener('pointermove', move);
    grip.addEventListener('pointerup', end);
    grip.addEventListener('pointercancel', end);
  }
}
function fitQuestion(){
  const box=document.getElementById('q');
  if(!box||box.hidden) return;
  if(box.querySelector('.ltsec')) return;
  const pad=document.getElementById('cinemaInkPad');
  const padH=pad?Math.round(pad.offsetHeight||0):0;
  const availH=Math.max(180, window.innerHeight-36-padH);
  const availW=Math.max(240, window.innerWidth-20);
  let lo=0.95, hi=2.5, best=0.95;
  for(let i=0;i<12;i++){
    const mid=(lo+hi)/2;
    box.style.setProperty('--qzoom', String(mid));
    void box.offsetHeight;
    if(box.scrollHeight<=availH+6 && box.scrollWidth<=availW+6){best=mid;lo=mid;}
    else hi=mid;
  }
  box.style.setProperty('--qzoom', String(Math.max(0.95, Math.min(2.5, Math.round(best*0.97*10)/10))));
  sizeInk();
}
function typeset(el){
  const box=el||document.getElementById('q');
  if(box&&box.getAttribute('data-mj')==='1') return;
  const done=function(){if(box) box.setAttribute('data-mj','1'); fitQuestion();};
  const p=window.ldvlTypeset?window.ldvlTypeset(box):null;
  if(p&&typeof p.then==='function') p.then(done, done); else setTimeout(done,120);
}
function draw(q, showSol, pos, total, live){
  const box=document.getElementById('q');
  if(!box||!q) return false;
  live=live||{};
  const key=drawKey(q, showSol, pos, total, live);
  if(key===lastDrawKey && box.innerHTML) return false;
  lastDrawKey=key;
  box.removeAttribute('data-mj');
  if(q.kind==='LT'||q.kind==='PP'){
    const lab=q.kind==='LT'?'Lý thuyết':'Dạng mẫu';
    box.hidden=false;
    box.innerHTML='<div class="qheadline"><span class="qbadge">'+lab+' · '+(pos+1)+'/'+total+'</span></div>'+(q.text||'');
    if(window.ldvlSpeak&&window.ldvlSpeak.mountChunks) window.ldvlSpeak.mountChunks(box);
    typeset(box);
    return true;
  }
  const checked=!!live.checked;
  box.hidden=false;
  let h='<div class="qheadline"><span class="qbadge">Câu '+(pos+1)+'</span>'+(dangLine(q)?'<div class="qdang">'+E(dangLine(q))+'</div>':'')+'<div class="qstem">'+q.text+'</div></div>';
  if(checked && live.ok!=null){
    const labs='ABCD';
    let head=live.ok?'Đúng':'Sai';
    function row(label, items){
      const n=Math.max(items.length,1);
      const cells=items.map(function(it){
        const ds=it.mark||'';
        if(!ds){
          return '<span class="keycell '+(it.cls||'')+'"><span class="kcirc tn">'+it.letter+'</span></span>';
        }
        const kind=ds==='Đ'?'d':(ds==='S'?'s':'');
        return '<span class="keycell '+(it.cls||'')+'"><span class="klet">'+it.letter+'</span><span class="kcirc '+kind+'">'+ds+'</span></span>';
      }).join('');
      return '<div class="keyrow" style="grid-template-columns:7.2em repeat('+n+',2.6em)"><span class="keylab">'+label+'</span>'+cells+'</div>';
    }
    let extra='';
    if(showSol){
      if(q.kind==='TN'){
        const key=(q.options||[]).map(function(o,i){return o.correct?labs.charAt(i):''}).filter(Boolean).join('')||'?';
        const pick=live.tn==null?'?':labs.charAt(live.tn);
        extra='<div class="keygrid">'+row('Đáp án đúng',[{letter:key,mark:'',cls:'ok'}])+row('Thầy chọn',[{letter:pick,mark:'',cls:pick===key?'ok':'bad'}])+'</div>';
      }else if(q.kind==='DS'){
        const keys=(q.statements||[]).map(function(s){return s.correct?'Đ':'S'});
        const ans=keys.map(function(m,i){return {letter:labs.charAt(i),mark:m,cls:'ok'}});
        const you=keys.map(function(m,i){const p=(live.ds||[])[i];const mk=p===true?'Đ':(p===false?'S':'?');return {letter:labs.charAt(i),mark:mk,cls:mk===m?'ok':'bad'}});
        extra='<div class="keygrid">'+row('Đáp án đúng',ans)+row('Thầy chọn',you)+'</div>';
      }
    }
    h+='<div class="result '+(live.ok?'good':'bad')+'">'+head+extra+'</div>';
  }
  if(q.kind==='TN')(q.options||[]).forEach(function(o,i){
    const picked=live.tn===i;
    let cls='opt';
    if(showSol && o.correct) cls+=' correct';
    else if(showSol && picked) cls+=' wrong';
    else if(!showSol && picked) cls+=' picked';
    let flags='';
    if(picked) flags+='<span class="pickmark">◀ thầy chọn</span>';
    if(showSol && o.correct) flags+='<span class="okmark">Đáp án đúng</span>';
    h+='<div class="'+cls+'"><span class="tflab">'+String.fromCharCode(65+i)+'</span><div class="tf-text">'+o.text+'</div>'+(flags?'<div class="tf-flags">'+flags+'</div>':'')+'</div>';
  });
  else if(q.kind==='DS'){
    h+='<div class="qbody ds"><div class="qfig" hidden></div><div class="qtf"><div class="tfgrid"><div class="tf-colhead"><span></span><span></span><span class="tf-h yes">Đúng</span><span class="tf-h no">Sai</span></div>';
    (q.statements||[]).forEach(function(s,i){
    const pick=(live.ds||[])[i];
    const has=pick===true||pick===false;
    const revealed=!!showSol;
    let cls='tf';
    if(revealed && has && pick!==s.correct) cls+=' wrong';
    else if(revealed) cls+=' ok';
    const lab='ABCD'.charAt(i)||(i+1);
    function box(side, val, right){
      let c='tf-box '+side;
      if(revealed && right) c+=' ok';
      if(has && pick===val){
        if(revealed && !right) c+=' bad';
        else if(!revealed) c+=' pick';
      }
      return c;
    }
    h+='<div class="'+cls+'"><span class="tflab">'+lab+'</span><div class="tf-text">'+s.text+'</div>'
      +'<span class="'+box('yes',true,!!s.correct)+'"></span>'
      +'<span class="'+box('no',false,!s.correct)+'"></span></div>';
  });
    h+='</div></div></div>';
  }
  else {
    const typed=String(live.text||'').trim();
    if(hostTok() && !showSol && !checked){
      h+='<div class="answerline"><input id="cinemaAns" class="cinema-ans" value="'+E(typed)+'" placeholder="Nhập đáp án lớp chọn"><button type="button" class="cinema-tool" id="cinemaAnsSave">Ghi</button></div>';
    }else{
      h+='<div class="answerline">'+(typed?('<b>Thầy viết:</b> '+E(typed)):'✎ Đang chờ thầy nhập…')+'</div>';
    }
    if(showSol&&q.answer) h+='<div class="answerline result good"><b>Đáp án đúng:</b> '+E(q.answer)+'</div>';
  }
  if(showSol&&q.solution) h+='<div class="solution"><b>📖 Lời giải</b><div>'+q.solution+'</div></div>';
  box.innerHTML=h;
  (function(){
    const stem=box.querySelector('.qstem');
    const fig=box.querySelector('.qfig');
    const body=box.querySelector('.qbody.ds');
    if(!stem||!fig||!body) return;
    const bits=[];
    stem.querySelectorAll('.immini,.tikz-row,.tikzfig,.tikz-live,.ytbox,table.tex-table').forEach(function(el){
      if(el.closest('.immini,.tikz-row')&&!el.matches('.immini,.tikz-row')) return;
      bits.push(el);
    });
    if(!bits.length){fig.remove();return;}
    bits.forEach(function(el){fig.appendChild(el)});
    fig.hidden=false;
    body.classList.add('hassplit');
  })();
  typeset(box);
  return true;
}
async function tick(){
  const err=document.getElementById('perr');
  const box=document.getElementById('q');
  try{
    const r=await fetch('/api/present/state?code='+encodeURIComponent(CODE)+'&ver='+lastVer,{credentials:'same-origin'});
    const d=await r.json();
    if(!d.ok){
      if(lastVer<0){
        if(box) box.hidden=true;
        if(err) err.innerHTML=(d.error||'Chưa có phòng.')
          +'<div class="muted" style="margin-top:8px;font-weight:400">Đợi thầy bấm <b>Chiếu chung</b> với mã <code>'+E(CODE)+'</code> · <a href="/xem">Mã khác</a></div>';
      }else if(err){
        err.innerHTML='<span class="muted" style="font-weight:700">Đang kết nối lại…</span>';
      }
      return;
    }
    if(d.unchanged){
      sizeInk();
      return;
    }
    lastVer=d.ver;
    lastQ=d.q||null;
    lastLive=d.live||{};
    lastShowSol=!!d.show_sol;
    if(typeof d.pos==='number' && d.pos!==lastPeekPos){
      if(lastPeekPos>=0){ hideCinemaPeek(); clearInkCanvas(); }
      lastPeekPos=d.pos;
    }
    if(err) err.textContent='';
    const changed=draw(d.q, !!d.show_sol, d.pos, d.total, d.live||{});
    if(changed!==false && window.ldvlSpeak) window.ldvlSpeak.onDraw();
    paintSecNav(d.pos, d.total, d.secs||[], (d.q&&d.q.kind)||'', d.dangs||[], !!d.dang_has_prev, !!d.dang_has_next, d.q_lo, d.q_hi);
    bindCinemaPick();
    bindCinemaInk();
    bindInkPadUi();
    applyInk(d);
    sizeInk();
  }catch(e){
    if(err) err.textContent='Mất kết nối, đang thử lại…';
  }
}
tick();
setInterval(tick,900);
(function(){
  const qPrev=document.getElementById('qPrev'), qNext=document.getElementById('qNext');
  const a=document.getElementById('secPrev'), b=document.getElementById('secNext'), jump=document.getElementById('secJump');
  const dangJump=document.getElementById('dangJump');
  if(qPrev) qPrev.onclick=function(){stepDang(-1)};
  if(qNext) qNext.onclick=function(){stepDang(1)};
  if(a) a.onclick=function(){stepDang(-1,'dang')};
  if(b) b.onclick=function(){stepDang(1,'dang')};
  if(jump) jump.onchange=function(){jumpPos(parseInt(jump.value,10)||0)};
  if(dangJump) dangJump.onchange=function(){jumpPos(parseInt(dangJump.value,10)||0)};
  function leaveCinema(){
    if(window.history.length>1){ history.back(); return; }
    location.href=hostTok()?'/member':'/xem';
  }
  const x=document.getElementById('cinemaExit');
  const leave=document.getElementById('cinemaLeave');
  if(x) x.onclick=leaveCinema;
  if(leave) leave.onclick=leaveCinema;
  const peekBtn=document.getElementById('peekToggle');
  if(peekBtn) peekBtn.onclick=async function(){
    const el=document.getElementById('cinemaPeek');
    if(!el) return;
    if(!el.hidden){ hideCinemaPeek(); return; }
    const p=hostTok(); if(!p) return;
    const r=await fetch('/api/present/peek',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({code:p.code,token:p.token})});
    const d=await r.json().catch(function(){return {}});
    if(!d||!d.ok){alert((d&&d.error)||'Không xem được gợi ý.');return;}
    const sol=d.solution?('<div class="cinema-peek-sol">'+d.solution+'</div>'):'';
    el.innerHTML='<b>💡 Chỉ thầy</b> · lớp chưa thấy · <span>'+E(d.hint||'—')+'</span>'+sol;
    el.hidden=false;
    peekBtn.classList.add('on');
    if(window.ldvlTypeset) window.ldvlTypeset(el);
    else if(window.MathJax&&MathJax.typesetPromise) MathJax.typesetPromise([el]).catch(function(){});
  };
  const sol=document.getElementById('solToggle');
  if(sol) sol.onclick=async function(){ await presentReveal(!lastShowSol); };
  const chk=document.getElementById('chkToggle');
  if(chk) chk.onclick=async function(){ await presentLive(null, true); };
  const inkBtn=document.getElementById('inkToggle');
  if(inkBtn) inkBtn.onclick=function(){
    if(!hostTok()) return;
    document.body.classList.toggle('ink-on');
    paintHostTools();
    bindCinemaPick();
    sizeInk();
  };
  const inkClr=document.getElementById('inkClear');
  if(inkClr) inkClr.onclick=function(){
    if(!hostTok()) return;
    clearInkCanvas();
    pushInk();
  };
  const ai=document.getElementById('aiToggle');
  if(ai) ai.onclick=async function(){
    const pane=document.getElementById('cinemaAi');
    if(!pane) return;
    if(!pane.hidden){ pane.hidden=true; return; }
    if(!(lastLive&&lastLive.checked)){
      alert('Hãy chọn đáp án và bấm Xác nhận trước.');
      return;
    }
    if(!lastShowSol) await presentReveal(true);
    pane.hidden=false;
    if(typeof ldvlGeminiReview!=='function'){
      pane.innerHTML='<p class="err">Hãy đăng nhập ADMIN trên máy này rồi tải lại trang chiếu.</p>';
      return;
    }
    pane.innerHTML=(typeof ldvlGeminiMiniHtml==='function'?ldvlGeminiMiniHtml('🤖 Phản biện AI'):'')
      +'<p style="margin:8px 0"><button type="button" class="btn primary" id="cinemaAiGo">🤖 Phản biện câu này</button></p>'
      +'<div id="aiout" class="reviewout"></div>';
    if(window.ldvlFillGeminiInputs) ldvlFillGeminiInputs();
    const go=document.getElementById('cinemaAiGo');
    const out=document.getElementById('aiout');
    const run=async function(){
      if(!lastQ) return;
      window.LAST_REVIEW=Object.assign({}, lastQ, {student:liveStudent(lastQ, lastLive), ok:lastLive&&lastLive.ok});
      await ldvlGeminiReview(window.LAST_REVIEW, out);
      if(window.ldvlSpeak){ window.ldvlSpeak.bind(); window.ldvlSpeak.onDraw(); }
    };
    if(go) go.onclick=run;
    if(typeof ldvlFilledKeys==='function' && ldvlFilledKeys().length) run();
  };
  (function(){
    const box=document.getElementById('cinemaQr');
    if(!box) return;
    const sizes=['min','mid','max'];
    function cur(){
      if(box.classList.contains('is-max')) return 'max';
      if(box.classList.contains('is-min')) return 'min';
      return 'mid';
    }
    function apply(sz){
      sizes.forEach(function(s){ box.classList.toggle('is-'+s, s===sz); });
      try{localStorage.setItem('ldvlCinemaQr', sz)}catch(e){}
    }
    let start='';
    try{start=localStorage.getItem('ldvlCinemaQr')||''}catch(e){}
    if(sizes.indexOf(start)<0) start='min';
    apply(start);
    const minus=document.getElementById('qrShrink'), plus=document.getElementById('qrGrow'), hide=document.getElementById('qrHide');
    if(minus) minus.onclick=function(){ apply(sizes[Math.max(0, sizes.indexOf(cur())-1)]); };
    if(plus) plus.onclick=function(){
      if(box.classList.contains('is-hide')){ box.classList.remove('is-hide'); document.body.classList.remove('qr-hidden'); if(hide){hide.textContent='✕';hide.title='Ẩn QR';} return; }
      apply(sizes[Math.min(sizes.length-1, sizes.indexOf(cur())+1)]);
    };
    function setHide(on){
      box.classList.toggle('is-hide', on);
      document.body.classList.toggle('qr-hidden', on);
      if(hide){ hide.textContent=on?'QR':'✕'; hide.title=on?'Hiện QR':'Ẩn QR'; }
      try{localStorage.setItem('ldvlCinemaQrHide', on?'1':'0')}catch(e){}
    }
    let hid='';
    try{hid=localStorage.getItem('ldvlCinemaQrHide')||''}catch(e){}
    if(hid==='1') setHide(true);
    if(hide) hide.onclick=function(){ setHide(!box.classList.contains('is-hide')); };
  })();
})();
window.addEventListener('resize',function(){sizeInk();});
document.addEventListener('DOMContentLoaded',function(){bindInkPadUi();sizeInk();});
</script>
"""

PRESENT_HOST_JS = r"""
<script>
(function(){
if(window.__ldvlPresentHost) return;
window.__ldvlPresentHost=true;
try{
  var phone=window.matchMedia('(max-width:900px)').matches;
  var saved='';
  try{saved=localStorage.getItem('ldvlSubnavFold')||''}catch(e){}
  var compact=phone||saved!=='0';
  document.documentElement.classList.toggle('ldvlAdminCompact',compact);
  if(document.body) document.body.classList.toggle('ldvlAdminCompact',compact);
}catch(e){}
let P=null;
try{P=JSON.parse(localStorage.getItem('ldvlPresent')||'null')}catch(e){P=null}
if(P&&P.code && ['1234','12345','123456','0000','1111'].indexOf(String(P.code).toUpperCase())>=0){
  P=null; try{localStorage.removeItem('ldvlPresent')}catch(e){}
}
function solVisible(){
  const sol=document.getElementById('solbox');
  return !!(sol && sol.style.display==='block');
}
function adminQuizPos(){
  const items=document.querySelectorAll('.palette .pitem');
  if(!items.length) return null;
  for(let i=0;i<items.length;i++){
    if(items[i].classList.contains('pcur')) return i;
  }
  return null;
}
function adminGoPos(pos){
  pos=Number(pos);
  if(!(pos>=0)) return;
  const page=document.querySelector('.ltpage[data-de-path]');
  if(page){
    const jump=document.getElementById('ltjump');
    if(!jump||jump.options.length<2) return;
    const idx=Math.max(0, Math.min(jump.options.length-2, pos));
    const opt=jump.options[idx+1];
    if(!opt) return;
    if(jump.selectedIndex===idx+1) return;
    window.__ldvlFollowRoom=true;
    jump.selectedIndex=idx+1;
    jump.dispatchEvent(new Event('change'));
    window.__ldvlFollowRoom=false;
    return;
  }
  if(!document.querySelector('.palette .pitem')) return;
  const cur=adminQuizPos();
  if(cur===pos) return;
  window.__ldvlFollowing=true;
  location.href='/practice/jump/'+pos;
}
async function followPresentRoom(){
  if(!P||!P.code||document.hidden||window.__ldvlFollowing) return;
  try{
    const r=await fetch('/api/present/state?code='+encodeURIComponent(P.code),{credentials:'same-origin'});
    const d=await r.json().catch(function(){return {}});
    if(!d||!d.ok) return;
    if(typeof d.pos!=='number') return;
    window.__ldvlRoomPos=d.pos;
    if(d.ids_sig && d.ids_sig!==window.__ldvlIdsSig){
      const first=!window.__ldvlIdsSig;
      window.__ldvlIdsSig=d.ids_sig;
      if(!first && document.querySelector('.palette .pitem')){
        window.__ldvlFollowing=true;
        location.href='/practice/jump/'+(d.pos||0);
        return;
      }
    }
    const qk=String((d.q&&d.q.kind)||'').toUpperCase();
    const page=document.querySelector('.ltpage[data-de-path]');
    if(page){
      if(qk!=='LT'&&qk!=='PP') return;
      adminGoPos(d.pos);
      return;
    }
    if(document.querySelector('.palette .pitem')){
      if(qk==='LT'||qk==='PP') return;
      const cur=adminQuizPos();
      if(typeof cur==='number'){
        if(cur===d.pos) window.__ldvlRoomPos=d.pos;
        return;
      }
      adminGoPos(d.pos);
    }
  }catch(e){}
}
function collectLive(){
  const q=window.Q||{};
  const live={tn:null,ds:[],text:'',checked:!!window.checked,ok:null};
  if(q.kind==='TN'){
    const z=document.querySelector('#q input[name=a]:checked');
    live.tn=z?+z.value:null;
  }else if(q.kind==='DS'){
    const n=(q.statements||[]).length;
    for(let i=0;i<n;i++){
      const z=document.querySelector('#q input[name=t'+i+']:checked');
      live.ds.push(z?z.value==='1':null);
    }
  }else{
    const z=document.getElementById('ans');
    live.text=z?String(z.value||''):'';
  }
  if(window.checked && window.LAST_REVIEW && typeof window.LAST_REVIEW.ok==='boolean') live.ok=window.LAST_REVIEW.ok;
  return live;
}
function payload(opts){
  opts=opts||{};
  const o={code:P&&P.code,token:P&&P.token,zoom:typeof qZoom==='number'?qZoom:1,live:collectLive()};
  const page=document.querySelector('.ltpage[data-de-path]');
  if(page){
    o.comp_kind=page.getAttribute('data-lt-kind')||'lt';
    o.de_path=page.getAttribute('data-de-path')||'';
    if(opts.force || window.__ldvlSecTouched){
      const sel=document.getElementById('ltjump');
      let sec=(sel&&sel.value)||'';
      if(!sec) sec=window.__ldvlPresentSec||'';
      if(sec){ window.__ldvlPresentSec=sec; o.sec=sec; }
      window.__ldvlSecTouched=false;
    }
  }
  const form=document.getElementById('questionForm');
  if(form && !page && (opts.force || window.__ldvlQuizTouched)){
    const p=form.querySelector('input[name=path]');
    o.quiz_path=p?p.value:'';
    const boxes=Array.prototype.slice.call(document.querySelectorAll('.qcard input[name=qid]'));
    let ids=boxes.filter(function(x){return x.checked}).map(function(x){return +x.value});
    if(!ids.length) ids=boxes.map(function(x){return +x.value});
    o.quiz_ids=ids;
    let pos=typeof window.__ldvlQuizPos==='number'?window.__ldvlQuizPos:0;
    if(pos<0||pos>=ids.length) pos=0;
    o.quiz_pos=pos;
    window.__ldvlQuizTouched=false;
  }else if(!page && document.querySelector('.palette .pitem')){
    const ids=Array.isArray(window.practiceIds)?window.practiceIds.slice():[];
    const path=window.practicePath||'';
    let pos=adminQuizPos();
    if(pos==null && typeof window.__ldvlQuizPos==='number') pos=window.__ldvlQuizPos;
    if(pos==null && typeof window.practicePos==='number') pos=window.practicePos;
    if(ids.length){
      o.quiz_path=path;
      o.quiz_ids=ids;
      if(pos==null||pos<0||pos>=ids.length) pos=0;
      o.quiz_pos=pos;
    }
  }
  return o;
}
function subnavFolded(){
  if(window.matchMedia('(max-width:900px)').matches){
    try{ if(localStorage.getItem('ldvlSubnavFold')==='0') return false; }catch(e){}
    return true;
  }
  try{
    if(localStorage.getItem('ldvlSubnavFold')==='1') return true;
    if(localStorage.getItem('ldvlSubnavFold')==='0') return false;
  }catch(e){}
  return false;
}
function presentFolded(){
  try{
    const v=localStorage.getItem('ldvlPresentFold');
    if(v==='0') return false;
  }catch(e){}
  return true;
}
function applySubnavFold(on){
  document.documentElement.classList.toggle('ldvlAdminCompact', !!on);
  if(document.body) document.body.classList.toggle('ldvlAdminCompact', !!on);
  document.querySelectorAll('details.admin-chrome,details.admindang-fold').forEach(function(d){
    d.open=!on;
    const sum=d.querySelector('summary');
    if(sum && /Công cụ ADMIN/.test(sum.textContent||'')){
      sum.textContent=d.open?'▾ Công cụ ADMIN · TEX / AI / link':'▸ Công cụ ADMIN · TEX / AI / link';
    }
  });
  const fold=document.getElementById('navFold');
  if(fold){
    fold.textContent=on?'▸ Mở rộng':'▾ Thu gọn';
    fold.title=on?'Mở tab dạng và công cụ ADMIN (AI viết lại, TEX, link)':'Ẩn tab dạng và thu gọn công cụ ADMIN';
  }
  try{localStorage.setItem('ldvlSubnavFold', on?'1':'0')}catch(e){}
}
function applyPresentFold(on){
  const host=document.getElementById('presentHost');
  if(host) host.classList.toggle('is-folded', !!on);
  try{localStorage.setItem('ldvlPresentFold', on?'1':'0')}catch(e){}
}
function presentKindLabel(){
  const page=document.querySelector('.ltpage[data-lt-kind]');
  const k=page&&page.getAttribute('data-lt-kind');
  if(k==='pp') return 'Chiếu dạng mẫu';
  if(k==='lt') return 'Chiếu lý thuyết';
  if(document.getElementById('questionForm')) return 'Chiếu câu';
  return 'Chiếu chung';
}
function syncStartLabel(){
  const b=document.getElementById('pStart');
  if(!b) return;
  if(P&&P.code){
    b.textContent='📺 Đang chiếu · '+P.code;
    b.title='Bấm để hiện / ẩn mã và link chiếu';
  }else{
    b.textContent='📺 '+presentKindLabel();
    b.title='Học viên xem cùng nội dung trên điện thoại / máy khác';
  }
}
function ensureHost(){
  let host=document.getElementById('presentHost');
  if(host) return host;
  host=document.createElement('div');
  host.id='presentHost';
  host.className='present-host is-folded';
  const fold=document.createElement('button');
  fold.type='button'; fold.className='btn'; fold.id='navFold';
  fold.textContent='▾ Thu gọn';
  const b=document.createElement('button');
  b.type='button'; b.className='btn primary'; b.id='pStart';
  b.textContent='📺 '+presentKindLabel();
  const codeEl=document.createElement('b');
  codeEl.id='pCode';
  const prev=document.createElement('button');
  prev.type='button'; prev.className='btn'; prev.id='pPrevQuick'; prev.textContent='◀';
  prev.title='Câu trước'; prev.onclick=function(){presentStep(-1)};
  const next=document.createElement('button');
  next.type='button'; next.className='btn'; next.id='pNextQuick'; next.textContent='▶';
  next.title='Câu sau'; next.onclick=function(){presentStep(1)};
  const el=document.createElement('div');
  el.id='presentBar'; el.className='notice present-details'; el.hidden=true;
  host.appendChild(b);
  host.appendChild(codeEl);
  host.appendChild(prev);
  host.appendChild(next);
  host.appendChild(fold);
  host.appendChild(el);
  const slot=document.getElementById('presentSlot');
  const ltBody=document.querySelector('.ltpage .panel > .body');
  const sub=document.querySelector('.subnav');
  if(slot) slot.appendChild(host);
  else if(ltBody) ltBody.insertBefore(host, ltBody.firstChild);
  else if(sub&&sub.parentNode) sub.parentNode.insertBefore(host, sub);
  else{
    const lt=document.querySelector('.ltnav');
    if(lt&&lt.parentNode) lt.parentNode.insertBefore(host, lt);
    else{
    const qz=document.querySelector('.quiztop')||document.querySelector('.qzoombar')||document.querySelector('.panel .toolbar');
    if(qz&&qz.parentNode) qz.parentNode.insertBefore(host, qz);
    else return null;
    }
  }
  fold.onclick=function(){applySubnavFold(!(document.documentElement.classList.contains('ldvlAdminCompact')||document.body.classList.contains('ldvlAdminCompact')))};
  b.onclick=function(){
    if(P&&P.code){applyPresentFold(!host.classList.contains('is-folded'));return;}
    presentStart();
  };
  applySubnavFold(subnavFolded());
  applyPresentFold(presentFolded());
  return host;
}
async function presentStep(delta){
  if(!P||!P.code) return;
  try{
    const r=await fetch('/api/present/step',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({code:P.code,token:P.token,delta:delta})});
    const d=await r.json().catch(function(){return {}});
    if(d&&d.ok){
      if(typeof d.pos==='number'){
        window.__ldvlQuizPos=d.pos;
        window.__ldvlRoomPos=d.pos;
        window.__ldvlQuizTouched=false;
        adminGoPos(d.pos);
      }
    }
  }catch(e){}
}
function showBar(p){
  const host=ensureHost();
  if(!host) return;
  const el=document.getElementById('presentBar');
  if(!el) return;
  syncStartLabel();
  const codeEl=document.getElementById('pCode');
  if(!p){
    host.classList.remove('has-code');
    if(codeEl) codeEl.textContent='';
    el.innerHTML='';el.hidden=true;applyPresentFold(true);syncStartLabel();return;
  }
  host.classList.add('has-code');
  if(codeEl) codeEl.textContent=p.code||'';
  el.hidden=false;
  applyPresentFold(presentFolded());
  const url=p.url||(location.origin+'/xem/'+p.code);
  const qr='/xem/'+encodeURIComponent(p.code)+'/qr.svg';
  el.innerHTML='<span class="present-qr"><img src="'+qr+'" width="88" height="88" alt="QR vào chiếu"></span>'
    +'<b>📺 Chiếu chung</b> · mã <code style="font-size:22px;letter-spacing:.12em">'+p.code+'</code> '
    +'<a class="btn primary" href="'+url+'" target="_blank" rel="noopener">🖥 Mở màn chiếu</a> '
    +'<button type="button" class="btn" id="pPrev">◀ Câu trước</button> '
    +'<button type="button" class="btn" id="pNext">Câu sau ▶</button> '
    +'<button type="button" class="btn" id="pcopy">📋 Copy link</button> '
    +'<button type="button" class="btn" id="prefresh">🔄 Mã mới</button> '
    +'<button type="button" class="btn red" id="pstop">Tắt chiếu</button> '
    +'<div class="muted">Mã và QR đổi mỗi lần bấm Chiếu. Học sinh phải quét QR buổi này — mã buổi trước không vào được.</div>';
  const c=document.getElementById('pcopy');
  if(c) c.onclick=function(){navigator.clipboard.writeText(url).then(function(){c.textContent='✅ Đã copy'},function(){prompt('Copy link',url)})};
  const pv=document.getElementById('pPrev');
  if(pv) pv.onclick=function(){presentStep(-1)};
  const nx=document.getElementById('pNext');
  if(nx) nx.onclick=function(){presentStep(1)};
  const rf=document.getElementById('prefresh');
  if(rf) rf.onclick=function(){ presentStart(); };
  const s=document.getElementById('pstop');
  if(s) s.onclick=async function(){
    await fetch('/api/present/stop',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({code:p.code,token:p.token})});
    P=null; try{localStorage.removeItem('ldvlPresent')}catch(e){}
    showBar(null);
  };
  syncStartLabel();
}
async function presentPush(opts){
  opts=opts||{};
  if(!P||!P.code||P._busy) return;
  if(!opts.force && document.hidden) return;
  const body=payload(opts);
  if(opts.force) body.force_kind=true;
  const fp=JSON.stringify({comp_kind:body.comp_kind||'',de_path:body.de_path||'',sec:body.sec||'',quiz_path:body.quiz_path||'',quiz_ids:body.quiz_ids||[],quiz_pos:body.quiz_pos,zoom:body.zoom,live:body.live,force:!!opts.force,pos:window.practicePos||null});
  if(!opts.force && fp===window.__ldvlPresentFp) return;
  try{
    const r=await fetch('/api/present/push',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify(body)});
    const d=await r.json().catch(function(){return {}});
    if(d&&d.ok){
      window.__ldvlPresentFp=fp;
      if(d.token&&P){P.token=d.token;try{localStorage.setItem('ldvlPresent',JSON.stringify(P))}catch(e){}}
      if(typeof d.pos==='number'){
        window.__ldvlQuizPos=d.pos;
        window.__ldvlRoomPos=d.pos;
      }
      return;
    }
    if(r.status===401) return;
    await presentResume();
  }catch(e){}
}
async function presentResume(){
  if(!P||!P.code||P._busy) return;
  P._busy=true;
  try{
    const r=await fetch('/api/present/start',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify(Object.assign(payload(),{code:P.code,force_kind:false}))});
    const d=await r.json().catch(function(){return {}});
    if(d&&d.ok){
      P={code:d.code,token:d.token,url:d.url};
      try{localStorage.setItem('ldvlPresent',JSON.stringify(P))}catch(e){}
      showBar(P);
    }
  }catch(e){}
  finally{if(P)P._busy=false}
}
async function presentStart(){
  const r=await fetch('/api/present/start',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify(Object.assign(payload({force:true}),{force_kind:true,fresh:true}))});
  const d=await r.json();
  if(!d.ok){alert(d.error||'Không mở được phòng chiếu');return;}
  P={code:d.code,token:d.token,url:d.url};
  try{localStorage.setItem('ldvlPresent',JSON.stringify(P))}catch(e){}
  window.__ldvlPresentFp='';
  showBar(P);
  try{ if(d.url) window.open(d.url,'_blank','noopener'); }catch(e){}
}
let pushTimer=0;
function presentPushSoon(){
  clearTimeout(pushTimer);
  pushTimer=setTimeout(presentPush,160);
}
function mountBtn(){
  if(window.__ldvlPresentMounted) return;
  if(!ensureHost()) return;
  window.__ldvlPresentMounted=true;
  const ltBtn=document.getElementById('ltPresentBtn');
  const qBtn=document.getElementById('qPresentBtn');
  if(qBtn) qBtn.onclick=async function(){
    if(!(P&&P.code)){
      window.__ldvlQuizPos=0;
      window.__ldvlQuizTouched=true;
    }
    window.__ldvlPresentFp='';
    if(P&&P.code){applyPresentFold(false);await presentPush({force:true});window.open(P.url||(location.origin+'/xem/'+P.code),'_blank','noopener');return;}
    presentStart();
  };
  document.querySelectorAll('.presentQ').forEach(function(b){
    b.onclick=async function(e){
      e.preventDefault();
      const id=+b.getAttribute('data-idx');
      document.querySelectorAll('.qcard input[name=qid]').forEach(function(x){x.checked=+x.value===id});
      window.__ldvlQuizPos=0;
      window.__ldvlQuizTouched=true;
      window.__ldvlPresentFp='';
      if(P&&P.code){applyPresentFold(false);await presentPush({force:true});window.open(P.url||(location.origin+'/xem/'+P.code),'_blank','noopener');return;}
      presentStart();
    };
  });
  if(ltBtn) ltBtn.onclick=async function(){
    if(P&&P.code){
      applyPresentFold(false);
      await presentPush({force:true});
      window.open(P.url||(location.origin+'/xem/'+P.code),'_blank','noopener');
      return;
    }
    presentStart();
  };
  document.addEventListener('click',function(e){
    if(!P||!P.code) return;
    const t=e.target;
    if(!t||!t.closest) return;
    const btn=t.closest('button[form="qdel"],button[form=qdel]');
    if(!btn) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    presentStep(-1);
  },true);
  document.addEventListener('submit',function(e){
    if(!P||!P.code) return;
    if(e.target&&e.target.id==='qdel'){
      e.preventDefault();
      presentStep(-1);
    }
  },true);
  if(P&&P.code){showBar(P);(async function(){await presentPush();followPresentRoom();})();}
  setInterval(function(){if(P&&P.code && !document.hidden) presentPush();},8000);
  setInterval(function(){if(P&&P.code && !document.hidden) followPresentRoom();},2000);
  if(window.ldvlSpeak) window.ldvlSpeak.bind();
  const jump=document.getElementById('ltjump');
  if(jump) jump.addEventListener('change', function(){
    if(window.__ldvlFollowRoom) return;
    if(jump.value) window.__ldvlPresentSec=jump.value;
    window.__ldvlSecTouched=true;
    window.__ldvlPresentFp='';
    presentPushSoon();
  });
  document.addEventListener('change',function(e){
    const qel=document.getElementById('q');
    if(P&&qel&&e.target&&qel.contains(e.target)) presentPushSoon();
  });
  document.addEventListener('input',function(e){
    const qel=document.getElementById('q');
    if(P&&qel&&e.target&&qel.contains(e.target)) presentPushSoon();
  });
}
function wrap(name, afterMs){
  const fn=window[name];
  if(typeof fn!=='function'||fn.__ldvlPresent) return;
  const wrapped=function(){
    const out=fn.apply(this,arguments);
    if(afterMs) setTimeout(presentPush, afterMs);
    else presentPush();
    if(name==='draw' && window.ldvlSpeak) setTimeout(function(){window.ldvlSpeak.onDraw()}, afterMs||80);
    return out;
  };
  wrapped.__ldvlPresent=true;
  window[name]=wrapped;
}
wrap('openSolution',60);
wrap('check',80);
wrap('draw',80);
mountBtn();
})();
</script>
"""
