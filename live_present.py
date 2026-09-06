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
        if c not in _ROOMS:
            return c
    return secrets.token_hex(3).upper()[:6]


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
    return {
        "path": de_path,
        "pos": idx,
        "total": len(secs),
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
        "updated": _now(),
    }, ""


def _keep_room_cursor(data, room):
    """Heartbeat không gửi sec thì giữ dạng/câu đang chiếu, không về mục 1."""
    if not room or not isinstance(data, dict):
        return
    if str(data.get("comp_kind") or "").strip().lower() in {"lt", "pp"} and not str(data.get("sec") or "").strip():
        data["sec"] = str(((room.get("q") or {}).get("sec_id")) or room.get("pos") or "")
    if data.get("quiz_ids") is not None and data.get("quiz_pos") is None and room.get("ids") is not None:
        data["quiz_pos"] = int(room.get("pos") or 0)


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
    if path and ids:
        try:
            session["practice_path"] = path
            session["practice_ids"] = ids
            session["practice_pos"] = max(0, min(pos, len(ids) - 1))
        except Exception:
            pass
        pos = int(session.get("practice_pos") or 0)
    else:
        path = str(session.get("practice_path") or "")
        ids = list(session.get("practice_ids") or [])
        pos = int(session.get("practice_pos") or 0)
    if not path or not ids or pos < 0 or pos >= len(ids):
        return None, "Chưa đang chiếu (vào Lý thuyết / Dạng mẫu / chọn câu bài tập rồi bấm Chiếu)."
    try:
        qs = _lesson_qs(path)
    except Exception as e:
        return None, str(e)
    q = qs.get(ids[pos])
    if not q:
        return None, "Không tải được câu hiện tại."
    show = bool(show_sol)
    keys = bool(show or reveal)
    return {
        "path": path,
        "ids": ids,
        "pos": pos,
        "total": len(ids),
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
        "show_sol": bool(room.get("show_sol")),
        "zoom": float(room.get("zoom") or 1),
        "host": room.get("host") or "",
        "live": room.get("live") or {},
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
        room["live"] = live
        room["host"] = hid
        room["code"] = code
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
    want_pre = _norm_code(data.get("code") or session.get("present_code") or "")
    with _LOCK:
        _keep_room_cursor(data, _ROOMS.get(want_pre))
    snap, err = _snapshot(data.get("show_sol"), data.get("zoom"), reveal=live["checked"], data=data)
    if not snap:
        return jsonify(ok=False, error=err), 400
    want = _norm_code(data.get("code"))
    if data.get("code") not in (None, "") and not want:
        return jsonify(ok=False, error="Mã phải 3–6 ký tự (chữ hoặc số), ví dụ 1234 hoặc K7M2."), 400
    with _LOCK:
        _prune()
        old = _norm_code(session.get("present_code"))
        mine = old if old in _ROOMS and _ROOMS[old].get("host") == hid else None
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
    with _LOCK:
        _keep_room_cursor(data, _ROOMS.get(code))
    snap, err = _snapshot(data.get("show_sol"), data.get("zoom"), reveal=live["checked"], data=data)
    if not snap:
        with _LOCK:
            room = _ROOMS.get(code)
            if room and room.get("host") == hid:
                room["live"] = live
                room["show_sol"] = bool(data.get("show_sol"))
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
        out = _room_out(room)
    return jsonify(out)


@base.app.post("/api/present/tts")
def api_present_tts():
    if not _host_id():
        return jsonify(ok=False, error="Chỉ ADMIN mới đọc được."), 401
    data = request.get_json(silent=True) or {}
    raw = re.sub(r"\s+", " ", str(data.get("text") or "")).strip()[:3500]
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
    try:
        delta = int(data.get("delta") or 0)
    except (TypeError, ValueError):
        delta = 0
    if delta not in (-1, 1) or not code:
        return jsonify(ok=False, error="Thiếu hướng chuyển dạng."), 400
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token:
            return jsonify(ok=False, error="Chỉ máy thầy đổi dạng được."), 401
        q = room.get("q") or {}
        qk = str(q.get("kind") or "")
        path = str(room.get("path") or "")
        pos = int(room.get("pos") or 0) + delta
        ids = list(room.get("ids") or [])
        zoom = room.get("zoom")
        hid = str(room.get("host") or "")
        show_sol = bool(room.get("show_sol"))
    if qk in {"LT", "PP"}:
        pos = max(0, min(max(1, int((room or {}).get("total") or 1)) - 1, pos))
        kind = "pp" if qk == "PP" else "lt"
        snap, err = _comp_snapshot(kind, path, pos, zoom)
    elif ids:
        pos = max(0, min(len(ids) - 1, pos))
        snap, err = _snapshot(show_sol, zoom, reveal=show_sol, data={"quiz_path": path, "quiz_ids": ids, "quiz_pos": pos})
    else:
        return jsonify(ok=False, error="Không chuyển được câu."), 400
    if not snap:
        return jsonify(ok=False, error=err or "Không tải được."), 400
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or str(room.get("token") or "") != token:
            return jsonify(ok=False, error="Phòng đã tắt."), 401
        live = room.get("live") or {}
        hid = str(room.get("host") or hid)
    room, rerr = _put_room(hid, code, token, snap, live if isinstance(live, dict) else {}, force_kind=True)
    if not room:
        return jsonify(ok=False, error=rerr), 409
    return jsonify(ok=True, pos=room.get("pos"), total=room.get("total"), ver=room.get("ver"))


@base.app.get("/xem")
@base.app.get("/xem/<code>")
def present_watch(code=""):
    code = _norm_code(code or request.args.get("code") or "")
    if not code:
        body = (
            "<div class='wrap'><div class='panel' style='max-width:480px;margin:40px auto'><div class='head'>📺 Vào chiếu chung</div><div class='body'>"
            "<p class='muted'>Gõ đúng mã thầy đưa sau khi bấm <b>Chiếu chung</b> (3–6 ký tự, ví dụ <code>K7M2</code> hoặc <code>1234</code> nếu thầy đặt mã đó). Không tự bịa mã khi thầy chưa mở phòng.</p>"
            "<form method='get' action='/xem' style='display:flex;gap:8px;flex-wrap:wrap'>"
            "<input name='code' maxlength='8' placeholder='Mã thầy đưa' style='flex:1;min-width:140px;padding:12px;font-size:22px;letter-spacing:.2em;text-transform:uppercase;text-align:center;border:1px solid #cbd8e6;border-radius:8px'>"
            "<button class='btn primary' type='submit'>Vào xem</button></form>"
            "<p class='muted'>Không cần đăng nhập. Trang tự theo câu / lý thuyết / dạng mẫu thầy đang chiếu.</p>"
            "</div></div></div>"
            "<script>document.querySelector('form').addEventListener('submit',function(e){e.preventDefault();var c=(this.code.value||'').trim().toUpperCase();if(c)location.href='/xem/'+encodeURIComponent(c)})</script>"
        )
        return base.page("Vào chiếu chung", body)
    admin_speak = False
    try:
        admin_speak = bool(base.can_manage_bank())
    except Exception:
        admin_speak = bool(base.admin_current())
    js = FOLLOW_JS.replace("__CODE__", json.dumps(code))
    if admin_speak:
        js = PRESENT_TTS_JS + js
        speak_bar = (
            "<div class='cinemaspeak' id='speakBar'>"
            "<button type='button' id='spkF' title='Giọng nữ Hoài My'>Nữ</button>"
            "<button type='button' id='spkM' title='Giọng nam Nam Minh'>Nam</button>"
            "<button type='button' id='spkPlay'>▶ Đọc</button>"
            "<button type='button' id='spkPause'>⏸ Dừng</button>"
            "<button type='button' id='spkResume' title='Đọc tiếp đoạn đang dừng'>▶ Đọc tiếp</button>"
            "<button type='button' id='secPrev' hidden>◀ Trước</button>"
            "<button type='button' id='secNext' hidden>Sau ▶</button>"
            "<button type='button' title='Toàn màn hình' onclick='ldvlToggleFs()'>⛶</button>"
            "<a href='/xem' title='Thoát'>✕</a>"
            "<span class='spkmsg' id='spkMsg'></span></div>"
        )
    else:
        speak_bar = "<a class='cinema-exit' href='/xem' title='Thoát'>✕</a>"
    body = (
        "<div class='cinema-q'>"
        + speak_bar
        + "<div id='perr' class='err'></div><div id='q' class='qbox' hidden></div></div>"
        + js
    )
    return base.page("Chiếu chung " + code, body, cinema=True)


PRESENT_TTS_JS = r"""
<script>
(function(){
if(window.ldvlSpeak) return;
const U={
  gender:(function(){try{return localStorage.getItem('ldvlSpeakG')||'f'}catch(e){return 'f'}})(),
  mode:'idle', wantPlay:false, gen:0, sig:'', audio:null, auto:false, unlocked:false
};
function msg(s){const el=document.getElementById('spkMsg'); if(el) el.textContent=s||'';}
function paint(){
  const f=document.getElementById('spkF'), m=document.getElementById('spkM');
  if(f) f.classList.toggle('on', U.gender==='f');
  if(m) m.classList.toggle('on', U.gender==='m');
  const play=document.getElementById('spkPlay'), pause=document.getElementById('spkPause'), resume=document.getElementById('spkResume');
  if(play) play.disabled=U.mode==='play';
  if(pause) pause.disabled=U.mode!=='play';
  if(resume) resume.disabled=U.mode!=='pause';
}
function speakTextOf(el){
  if(!el) return '';
  const c=el.cloneNode(true);
  c.querySelectorAll('script,style,button,.ltsec-tools,.cinemahud,.present-host,.qid,.pickmark,.okmark,.keygrid,.qbadge,.spkmsg,.cinemaspeak').forEach(function(n){n.remove()});
  return (c.innerText||c.textContent||'').replace(/\u00a0/g,' ').replace(/\s+/g,' ').trim();
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
async function run(text){
  const gen=++U.gen;
  U.mode='play'; U.wantPlay=true; paint();
  if(!navigator.onLine){ msg('Cần mạng để đọc giọng Nam/Nữ.'); U.mode='idle'; U.wantPlay=false; paint(); return; }
  try{
    await playNet(text, gen);
  }catch(e){
    if(U.gen!==gen) return;
    msg('Giọng máy…');
    await playLocal(text, gen);
  }
  if(U.gen!==gen) return;
  if(U.mode==='play'){ U.mode='idle'; if(!U.auto) U.wantPlay=false; paint(); msg(''); }
}
function startReadText(t){
  t=String(t||'').trim();
  U.sig=t.length+':'+(t.slice(0,60));
  if(!t){ msg('Không có chữ để đọc.'); return; }
  stopHard();
  try{ new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA').play().catch(function(){}); }catch(e){}
  U.unlocked=true; U.auto=false; U.wantPlay=true;
  run(t);
}
function startRead(){
  startReadText(speakTextOf(target()));
}
function isCinema(){return !!(document.body&&document.body.classList.contains('cinema'));}
function canClickHost(host){
  if(!host||!host.matches) return false;
  if(isCinema()) return !host.matches('label');
  return host.matches('.solution, .ai-y, .reviewout, .ltbox, details.lt-sol');
}
function markReading(host, btn){
  document.querySelectorAll('.spkchunk.on').forEach(function(x){x.classList.remove('on')});
  document.querySelectorAll('.spkhost.on').forEach(function(x){x.classList.remove('on')});
  if(btn) btn.classList.add('on');
  if(host) host.classList.add('on');
}
function addSpk(host, src){
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
      startReadText(speakTextOf(src));
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
      startReadText(speakTextOf(src));
    });
  }
}
function mountChunks(root){
  root=root||document;
  if(root.nodeType===1 && root.id!=='gkey-ping' && (root.matches('.ltbox, details.lt-sol, .qheadline, .opt, .tf, .solution, .ai-y, .reviewout') || root.id==='aiout')){
    const src=root.matches('.qheadline')?(root.querySelector('.qstem')||root):root;
    addSpk(root, src);
  }
  root.querySelectorAll('.ltbox').forEach(function(box){
    const k=box.querySelector(':scope > .k');
    addSpk(k||box, box);
  });
  root.querySelectorAll('details.lt-sol').forEach(function(d){ addSpk(d, d); });
  root.querySelectorAll('.ltbox-body > ol > li').forEach(function(li){ addSpk(li, li); });
  root.querySelectorAll('.qheadline').forEach(function(el){ addSpk(el, el.querySelector('.qstem')||el); });
  root.querySelectorAll('.opt, .tf, .solution').forEach(function(el){ addSpk(el, el); });
  root.querySelectorAll('.ai-y').forEach(function(el){ addSpk(el, el); });
  root.querySelectorAll('.reviewout').forEach(function(el){
    if(el.id==='gkey-ping') return;
    addSpk(el, el);
  });
}
window.ldvlSpeak={
  play:function(){ startRead(); },
  playEl:function(el){ startReadText(speakTextOf(el)); },
  mountChunks:mountChunks,
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
    if(U.mode==='play') stopHard();
    U.mode='idle'; U.wantPlay=false; paint();
    mountChunks(document.getElementById('q')||document);
    const pane=document.getElementById('aipane');
    if(pane) mountChunks(pane);
  },
  bind:function(){
    U.auto=false;
    const gate=document.getElementById('spkGate');
    if(gate) gate.hidden=true;
    if(!document.getElementById('spkPlay')){
      const host=document.getElementById('presentHost');
      if(host){
        const row=document.createElement('div');
        row.className='presentspeak';
        row.innerHTML='<button type="button" class="btn" id="spkF">Nữ</button><button type="button" class="btn" id="spkM">Nam</button><button type="button" class="btn primary" id="spkPlay">▶ Đọc</button><button type="button" class="btn" id="spkPause">⏸ Dừng</button><button type="button" class="btn" id="spkResume">▶ Tiếp</button><span class="spkmsg" id="spkMsg"></span>';
        host.appendChild(row);
      }
    }
    const f=document.getElementById('spkF'), m=document.getElementById('spkM');
    const play=document.getElementById('spkPlay'), pause=document.getElementById('spkPause'), resume=document.getElementById('spkResume');
    if(f && !f.__spk){ f.__spk=1; f.onclick=function(){ window.ldvlSpeak.setGender('f'); }; }
    if(m && !m.__spk){ m.__spk=1; m.onclick=function(){ window.ldvlSpeak.setGender('m'); }; }
    if(play && !play.__spk){ play.__spk=1; play.onclick=function(){ window.ldvlSpeak.play(); }; }
    if(pause && !pause.__spk){ pause.__spk=1; pause.onclick=function(){ window.ldvlSpeak.pause(); }; }
    if(resume && !resume.__spk){ resume.__spk=1; resume.onclick=function(){ window.ldvlSpeak.resume(); }; }
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
function hostTok(){
  try{
    const p=JSON.parse(localStorage.getItem('ldvlPresent')||'null');
    if(p&&String(p.code||'').toUpperCase()===String(CODE).toUpperCase()&&p.token) return p;
  }catch(e){}
  return null;
}
function paintSecNav(pos,total){
  const a=document.getElementById('secPrev'), b=document.getElementById('secNext');
  if(!a||!b) return;
  const on=!!hostTok();
  a.hidden=!on; b.hidden=!on;
  a.disabled=!on||!(pos>0);
  b.disabled=!on||!(pos<total-1);
}
async function stepDang(delta){
  const p=hostTok(); if(!p) return;
  await fetch('/api/present/step',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({code:p.code,token:p.token,delta:delta})});
}
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function drawKey(q, showSol, pos, total, live){
  live=live||{};
  if(q&&(q.kind==='LT'||q.kind==='PP')) return [q.kind,pos,total,q.title||''].join('\x1f');
  return [q&&q.kind,pos,total,!!showSol,q&&q.text||'',live.tn,JSON.stringify(live.ds||[]),live.text||'',!!live.checked,live.ok].join('\x1f');
}
function fitQuestion(){
  const box=document.getElementById('q');
  if(!box||box.hidden) return;
  if(box.querySelector('.ltsec')) return;
  const availH=Math.max(220, window.innerHeight-28);
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
  let h='<div class="qheadline"><span class="qbadge">Câu '+(pos+1)+'</span><div class="qstem">'+q.text+'</div></div>';
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
    h+='<div class="result '+(live.ok?'good':'bad')+'">'+head+extra+'</div>';
  }
  if(q.kind==='TN')(q.options||[]).forEach(function(o,i){
    const picked=live.tn===i;
    let cls='opt';
    if(o.correct) cls+=' correct';
    else if(checked&&picked) cls+=' wrong';
    else if(!checked&&picked) cls+=' picked';
    let flags='';
    if(picked) flags+='<span class="pickmark">◀ thầy chọn</span>';
    if(o.correct) flags+='<span class="okmark">Đáp án đúng</span>';
    h+='<div class="'+cls+'"><span class="tflab">'+String.fromCharCode(65+i)+'</span><div class="tf-text">'+o.text+'</div>'+(flags?'<div class="tf-flags">'+flags+'</div>':'')+'</div>';
  });
  else if(q.kind==='DS'){
    h+='<div class="qbody ds"><div class="qfig" hidden></div><div class="qtf"><div class="tfgrid"><div class="tf-colhead"><span></span><span></span><span class="tf-h yes">Đúng</span><span class="tf-h no">Sai</span></div>';
    (q.statements||[]).forEach(function(s,i){
    const pick=(live.ds||[])[i];
    const has=pick===true||pick===false;
    const revealed=showSol||checked;
    let cls='tf';
    if(revealed&&s.correct) cls+=' correct';
    else if(checked&&has&&pick!==s.correct) cls+=' wrong';
    const lab='ABCD'.charAt(i)||(i+1);
    h+='<div class="'+cls+'"><span class="tflab">'+lab+'</span><div class="tf-text">'+s.text+'</div>'
      +'<span class="tf-box yes'+(pick===true?' pick':'')+(revealed&&s.correct?' on':'')+'"></span>'
      +'<span class="tf-box no'+(pick===false?' pick':'')+(revealed&&!s.correct?' on':'')+'"></span></div>';
  });
    h+='</div></div></div>';
  }
  else {
    const typed=String(live.text||'').trim();
    h+='<div class="answerline">'+(typed?('<b>Thầy viết:</b> '+E(typed)):'✎ Đang chờ thầy nhập…')+'</div>';
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
    if(d.unchanged) return;
    lastVer=d.ver;
    if(err) err.textContent='';
    const changed=draw(d.q, !!d.show_sol, d.pos, d.total, d.live||{});
    if(changed!==false && window.ldvlSpeak) window.ldvlSpeak.onDraw();
    paintSecNav(d.pos, d.total);
  }catch(e){
    if(err) err.textContent='Mất kết nối, đang thử lại…';
  }
}
tick();
setInterval(tick,2500);
(function(){
  const a=document.getElementById('secPrev'), b=document.getElementById('secNext');
  if(a) a.onclick=function(){stepDang(-1)};
  if(b) b.onclick=function(){stepDang(1)};
})();
window.addEventListener('resize',function(){});
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
function solVisible(){
  const sol=document.getElementById('solbox');
  return !!(sol && sol.style.display==='block');
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
  const o={code:P&&P.code,token:P&&P.token,show_sol:solVisible(),zoom:typeof qZoom==='number'?qZoom:1,live:collectLive()};
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
  if(form && !page){
    const p=form.querySelector('input[name=path]');
    o.quiz_path=p?p.value:'';
    const boxes=Array.prototype.slice.call(document.querySelectorAll('.qcard input[name=qid]'));
    let ids=boxes.filter(function(x){return x.checked}).map(function(x){return +x.value});
    if(!ids.length) ids=boxes.map(function(x){return +x.value});
    o.quiz_ids=ids;
    if(opts.force || window.__ldvlQuizTouched){
      let pos=typeof window.__ldvlQuizPos==='number'?window.__ldvlQuizPos:0;
      if(pos<0||pos>=ids.length) pos=0;
      o.quiz_pos=pos;
      window.__ldvlQuizTouched=false;
    }
  }
  return o;
}
function subnavFolded(){
  if(window.matchMedia('(max-width:900px)').matches) return true;
  try{
    if(localStorage.getItem('ldvlSubnavFold')==='0') return false;
  }catch(e){}
  return true;
}
function presentFolded(){
  try{
    const v=localStorage.getItem('ldvlPresentFold');
    if(v==='0') return false;
  }catch(e){}
  return true;
}
function applySubnavFold(on){
  document.querySelectorAll('details.admin-chrome,details.admindang-fold').forEach(function(d){if(on) d.open=false});
  document.documentElement.classList.toggle('ldvlAdminCompact', !!on);
  if(document.body) document.body.classList.toggle('ldvlAdminCompact', !!on);
  const fold=document.getElementById('navFold');
  if(fold){
    fold.textContent=on?'▸ Mở rộng':'▾ Thu gọn';
    fold.title=on?'Mở tab dạng và công cụ ADMIN':'Ẩn tab dạng và công cụ ADMIN';
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
  const el=document.createElement('div');
  el.id='presentBar'; el.className='notice present-details'; el.hidden=true;
  host.appendChild(b);
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
function showBar(p){
  const host=ensureHost();
  if(!host) return;
  const el=document.getElementById('presentBar');
  if(!el) return;
  syncStartLabel();
  if(!p){el.innerHTML='';el.hidden=true;applyPresentFold(true);syncStartLabel();return;}
  el.hidden=false;
  applyPresentFold(presentFolded());
  const url=p.url||(location.origin+'/xem/'+p.code);
  el.innerHTML='<b>📺 Chiếu chung</b> · mã <code style="font-size:22px;letter-spacing:.12em">'+p.code+'</code> '
    +'<a class="btn primary" href="'+url+'" target="_blank" rel="noopener">🖥 Mở màn chiếu</a> '
    +'<button type="button" class="btn" id="pcopy">📋 Copy link</button> '
    +'<button type="button" class="btn red" id="pstop">Tắt chiếu</button> '
    +'<div class="muted">Máy chiếu tự hiện chữ. Bấm <b>🔊</b> cuối mỗi đoạn (định nghĩa, phương pháp, đề bài, lời giải) để đọc đúng đoạn đó. Nữ/Nam chọn giọng. Thanh trên: đọc cả mục / dừng / tiếp.</div>';
  const c=document.getElementById('pcopy');
  if(c) c.onclick=function(){navigator.clipboard.writeText(url).then(function(){c.textContent='✅ Đã copy'},function(){prompt('Copy link',url)})};
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
  const fp=JSON.stringify({comp_kind:body.comp_kind||'',de_path:body.de_path||'',sec:body.sec||'',quiz_path:body.quiz_path||'',quiz_ids:body.quiz_ids||[],quiz_pos:body.quiz_pos,show_sol:!!body.show_sol,zoom:body.zoom,live:body.live,force:!!opts.force,pos:window.practicePos||null});
  if(!opts.force && fp===window.__ldvlPresentFp) return;
  try{
    const r=await fetch('/api/present/push',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify(body)});
    const d=await r.json().catch(function(){return {}});
    if(d&&d.ok){
      window.__ldvlPresentFp=fp;
      if(d.token&&P){P.token=d.token;try{localStorage.setItem('ldvlPresent',JSON.stringify(P))}catch(e){}}
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
  const suggest=(P&&P.code)||'1234';
  const typed=prompt('Mã chiếu cho lớp gõ vào (3–6 ký tự). Có thể đặt 1234 cho dễ nhớ:', suggest);
  if(typed===null) return;
  const r=await fetch('/api/present/start',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify(Object.assign(payload({force:true}),{code:String(typed||'').trim(),force_kind:true}))});
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
    window.__ldvlQuizPos=0;
    window.__ldvlQuizTouched=true;
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
  if(P&&P.code){showBar(P);presentPush();}
  setInterval(function(){if(P&&P.code && !document.hidden) presentPush();},8000);
  if(window.ldvlSpeak) window.ldvlSpeak.bind();
  const jump=document.getElementById('ltjump');
  if(jump) jump.addEventListener('change', function(){
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
