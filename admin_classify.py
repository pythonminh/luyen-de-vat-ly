# -*- coding: utf-8 -*-
"""ADMIN: AI phân dạng + mức độ trên trang /member/select."""
from __future__ import annotations
import html
import json
import re
import unicodedata
import urllib.error
import urllib.parse
from flask import jsonify, request

import app as base
from student_gemini import _gemini_generate, _keys_from_payload

BLOCK_RE = re.compile(r"\\begin\s*\{\s*(?:ex|bt)\s*\}[\s\S]*?\\end\s*\{\s*(?:ex|bt)\s*\}", re.I)
DANG_LINE_RE = re.compile(r"^[ \t]*\\dang(?:bt)?\s*\{[^{}]*\}[ \t]*\r?\n?", re.I | re.M)
LEVEL_LINE_RE = re.compile(r"(%\s*(?:Mức|Muc|Muc do)\s*:\s*)([^\r\n%]*)", re.I)
ID_LINE_RE = re.compile(r"(%\s*ID\s*:\s*)(\S*)", re.I)
KIND_OK = ("DS", "TN", "TLN", "TL")
ROMAN = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10"}

MUC_FROM_LETTER = {"N": "NB", "H": "TH", "V": "VD", "C": "VDC"}
LETTER_FROM_MUC = {"NB": "N", "TH": "H", "VD": "V", "VDC": "C", "N": "N", "H": "H", "V": "V", "C": "C"}


def _plain(s, n=700):
    t = re.sub(r"<[^>]+>", " ", str(s or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n]


def _norm_dang(s):
    s = re.sub(r"\s+", " ", str(s or "").replace("{", "").replace("}", "").strip())
    if s.casefold() in {"chưa phân dạng", "chua phan dang", ""}:
        return "Chưa phân dạng"
    return s[:120]


def _norm_muc(s):
    u = str(s or "").strip().upper().replace(" ", "")
    if u in {"C", "VDC", "VẬNDỤNGCAO", "VANDUNGCAO"}:
        return "VDC"
    if u in {"V", "VD", "VẬNDỤNG", "VANDUNG"}:
        return "VD"
    if u in {"N", "NB", "NHẬNBIẾT", "NHANBIET"}:
        return "NB"
    return "TH"


def _has_level(raw):
    return bool(LEVEL_LINE_RE.search(raw or ""))


def _strip_dang(s):
    return DANG_LINE_RE.sub("", s or "")


def _set_level(s, muc):
    muc = _norm_muc(muc)
    if LEVEL_LINE_RE.search(s or ""):
        return LEVEL_LINE_RE.sub(lambda m: m.group(1) + muc, s, count=2)
    if re.search(r"\\begin\s*\{\s*(?:ex|bt)\s*\}", s or "", re.I):
        return re.sub(
            r"(\\begin\s*\{\s*(?:ex|bt)\s*\})",
            r"\1\n% Mức: " + muc,
            s,
            count=1,
            flags=re.I,
        )
    if re.search(r"%\s*ID\s*:", s or "", re.I):
        return re.sub(r"(%\s*ID\s*:[^\n]*\n?)", r"\1% Mức: " + muc + "\n", s, count=1, flags=re.I)
    return ("% Mức: " + muc + "\n") + (s or "")


def _set_id(s, qid):
    qid = str(qid or "").strip()
    if not qid:
        return s or ""
    if ID_LINE_RE.search(s or ""):
        return ID_LINE_RE.sub(lambda m: m.group(1) + qid, s, count=2)
    if re.search(r"\\begin\s*\{\s*(?:ex|bt)\s*\}", s or "", re.I):
        return re.sub(
            r"(\\begin\s*\{\s*(?:ex|bt)\s*\})",
            r"\1\n% ID: " + qid,
            s,
            count=1,
            flags=re.I,
        )
    return ("% ID: " + qid + "\n") + (s or "")


def apply_ids(tex, by_idx):
    """Chỉ ghi % ID: — không đụng dạng / mức."""
    matches = list(BLOCK_RE.finditer(tex or ""))
    if not matches:
        return tex
    chunks = []
    prev = 0
    for i, m in enumerate(matches):
        inter = tex[prev : m.start()]
        qid = str((by_idx.get(i) or {}).get("id") or "").strip()
        head, qhead = _split_qhead(inter)
        chunks.append(head)
        if qid:
            if qhead.strip():
                qhead = _set_id(qhead, qid)
            block = _set_id(m.group(0), qid)
        else:
            block = m.group(0)
        chunks.append(qhead)
        chunks.append(block)
        prev = m.end()
    chunks.append(tex[prev:])
    return "".join(chunks)


def apply_taxonomy(tex, by_idx, keep=None):
    matches = list(BLOCK_RE.finditer(tex or ""))
    if not matches:
        return tex
    chunks = []
    prev = 0
    last_dang = None
    for i, m in enumerate(matches):
        inter = _strip_dang(tex[prev:m.start()])
        asg = by_idx.get(i) or {}
        dang = _norm_dang(asg.get("dang") or "")
        muc = _norm_muc(asg.get("muc") or asg.get("level") or "TH")
        qid = str(asg.get("id") or "").strip()
        head, qhead = _split_qhead(inter)
        if i == 0:
            chunks.append(head)
        skip = keep is not None and i not in keep
        if skip:
            prev = m.end()
            continue
        if i > 0:
            chunks.append(head)
        if qhead.strip():
            qhead = _set_level(qhead, muc)
            if qid:
                qhead = _set_id(qhead, qid)
        block = _set_level(m.group(0), muc)
        if qid:
            block = _set_id(block, qid)
        if dang != "Chưa phân dạng" and dang != last_dang:
            qhead = qhead.rstrip() + "\n\\dangbt{" + dang + "}\n"
            last_dang = dang
        elif dang == "Chưa phân dạng":
            last_dang = "Chưa phân dạng"
        chunks.append(qhead)
        chunks.append(block)
        prev = m.end()
    tail = _strip_dang(tex[prev:])
    chunks.append(tail)
    return "".join(chunks)


def _split_qhead(inter):
    s = inter or ""
    found = list(re.finditer(r"(?m)^%[ \t]*=+[ \t]*Câu", s, re.I))
    if not found:
        found = list(re.finditer(r"(?m)^%[ \t]*ID\s*:", s, re.I))
    if not found:
        return s, ""
    i = found[-1].start()
    return s[:i], s[i:]


def id_prefix_from_path(path):
    rel = str(path or "").replace("\\", "/")
    folder = rel.rsplit("/", 1)[0].rsplit("/", 1)[-1] if "/" in rel else rel
    m = re.search(r"(?i)\b([LT])(\d{1,2})C(\d+)\s*B[aàáảãạ]i\s*(\d+)", folder)
    if not m:
        m = re.search(r"(?i)\b([LT])(\d{1,2})C(\d+)\s*Bai\s*(\d+)", folder)
    if m:
        return f"{m.group(1).upper()}{int(m.group(2)):02d}C{m.group(3)}B{m.group(4)}"
    parts = [p for p in rel.split("/") if p]
    if parts and parts[0].lower() == "ngan-hang":
        parts = parts[1:]
    mon = (parts[0] if parts else "").casefold()
    letter = "T" if ("toán" in mon or "toan" in mon) else "L"
    lop = "00"
    if len(parts) > 1:
        mm = re.search(r"(\d{1,2})", parts[1])
        if mm:
            lop = f"{int(mm.group(1)):02d}"
    chuong = "1"
    if len(parts) > 2:
        rm = re.search(r"Chương\s+([IVX]+)", parts[2], re.I)
        if rm:
            chuong = ROMAN.get(rm.group(1).upper(), "1")
        else:
            rm = re.search(r"(\d+)", parts[2])
            if rm:
                chuong = rm.group(1)
    bai = "1"
    if len(parts) > 3:
        bm = re.search(r"(?:B[aàáảãạ]i|Bai)\s*(\d+)", parts[3], re.I)
        if bm:
            bai = bm.group(1)
    return f"{letter}{lop}C{chuong}B{bai}"


def _id_ok(qid, prefix, kind):
    qid = str(qid or "").strip()
    k = str(kind or "TL")
    return bool(re.fullmatch(re.escape(prefix) + r"-\d+-" + re.escape(k), qid))


def _used_serials(folder, prefix):
    used = set()
    pat = re.compile(re.escape(prefix) + r"-(\d+)-(?:DS|TN|TLN|TL)")
    try:
        for fp in folder.glob("*.tex"):
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in pat.finditer(text):
                used.add(int(m.group(1)))
    except Exception:
        pass
    return used


def _next_serial(used):
    n = 1
    while n in used:
        n += 1
    used.add(n)
    return n


def _map_from_questions(qs):
    by_idx = {}
    for q in qs:
        i = int(q.get("idx"))
        by_idx[i] = {
            "dang": q.get("dang") or "Chưa phân dạng",
            "muc": MUC_FROM_LETTER.get(str(q.get("level") or "H"), "TH"),
            "id": str(q.get("id") or "").strip(),
            "kind": str(q.get("kind") or "TL"),
        }
    return by_idx


def stamp_missing_ids(tex, path, by_idx=None):
    qs = base.parse_questions(tex)
    by_idx = dict(by_idx or _map_from_questions(qs))
    prefix = id_prefix_from_path(path)
    _, local = base._safe_repo_file(path)
    used = _used_serials(local.parent, prefix)
    n_new = 0
    for q in qs:
        i = int(q.get("idx"))
        cur = by_idx.setdefault(i, {})
        kind = str(cur.get("kind") or q.get("kind") or "TL")
        if kind not in KIND_OK:
            kind = "TL"
        qid = str(cur.get("id") or q.get("id") or "").strip()
        if _id_ok(qid, prefix, kind):
            m = re.search(r"-(\d+)-", qid)
            if m:
                used.add(int(m.group(1)))
            continue
        serial = _next_serial(used)
        cur["id"] = f"{prefix}-{serial:02d}-{kind}"
        cur["kind"] = kind
        by_idx[i] = cur
        n_new += 1
    new = apply_ids(tex, by_idx)
    return new, n_new, by_idx


def _slug_dang(name):
    s = unicodedata.normalize("NFD", str(name or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return (s[:48] or "dang")


def _new_dang_path(folder_rel, dang, existing):
    slug = _slug_dang(dang)
    name = f"dang-{slug}.tex"
    n = 2
    while name in existing:
        name = f"dang-{slug}-{n}.tex"
        n += 1
    existing.add(name)
    return folder_rel.rstrip("/") + "/" + name


def _write_tex(path, text, message, sha=None):
    _, local = base._safe_repo_file(path)
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(text, encoding="utf-8")
    if base.TOKEN:
        base.github_put_text(path, text, message, sha or None)


def _header_fields(path, tex):
    mon = lop = chuong = bai = ""
    for m in re.finditer(r"(?m)^\s*%\s*(Môn|Lớp|Chương|Bài)\s*:\s*(.+?)\s*$", tex or "", re.I):
        k = m.group(1).casefold()
        v = m.group(2).strip()
        if k == "môn":
            mon = v
        elif k == "lớp":
            lop = v
        elif k == "chương":
            chuong = v
        elif k == "bài":
            bai = v
    if not (mon and bai):
        parts = str(path).replace("\\", "/").split("/")
        if len(parts) >= 5:
            mon = mon or parts[1]
            lop = lop or re.sub(r"(?i)^lớp\s*", "", parts[2])
            chuong = chuong or parts[3]
            bai = bai or parts[4]
    return mon, lop, chuong, bai


def _parse_ai_json(text):
    s = str(text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    if m:
        s = m.group(1).strip()
    a = s.find("[")
    b = s.rfind("]")
    if a < 0 or b <= a:
        raise ValueError("AI không trả JSON danh sách.")
    data = json.loads(s[a : b + 1])
    if not isinstance(data, list):
        raise ValueError("JSON không phải mảng.")
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("idx"))
        except (TypeError, ValueError):
            continue
        out.append({"idx": idx, "dang": _norm_dang(item.get("dang")), "muc": _norm_muc(item.get("muc") or item.get("level"))})
    return out


def _prompt(meta, existing, locked, items):
    exist = ", ".join(existing) if existing else "(chưa có dạng nào)"
    lock = ", ".join(locked) if locked else "(không khóa dạng nào)"
    rows = []
    for q in items:
        rows.append(
            f"- idx={q['idx']} | ID={q.get('id') or '—'} | loại={q['kind']} | dạng hiện tại={q['dang']} | mức={q.get('muc') or '—'} | đề: {q['text']}"
        )
    return (
        "Bạn là giáo viên Toán/Vật lý THPT. Hãy phân DẠNG BÀI và MỨC ĐỘ cho từng câu.\n"
        f"Bài học: {meta}\n"
        f"Dạng đã có trong file (ưu tiên dùng đúng tên, không đổi chữ nếu khớp): {exist}\n"
        f"Dạng đang giữ nguyên (không tạo tên mới trùng nghĩa, có thể gán câu mới vào đây nếu hợp): {lock}\n"
        "Mức độ chỉ một trong: NB (nhận biết), TH (thông hiểu), VD (vận dụng), VDC (vận dụng cao).\n"
        "Câu «Chưa phân dạng» phải được gán một dạng: dùng dạng đã có nếu đúng, hoặc đặt tên dạng mới ngắn gọn tiếng Việt.\n"
        "Không giải bài. Không thêm câu. Trả về DUY NHẤT một mảng JSON:\n"
        '[{"idx":0,"dang":"tên dạng","muc":"NB"}]\n'
        "Đủ mọi idx đã cho.\n\nCâu hỏi:\n" + "\n".join(rows)
    )


def _items_for_ai(qs, want_idx):
    items = []
    for q in qs:
        i = int(q.get("idx"))
        if i not in want_idx:
            continue
        muc = MUC_FROM_LETTER.get(str(q.get("level") or "H"), "TH")
        items.append(
            {
                "idx": i,
                "id": q.get("id") or "",
                "kind": q.get("kind") or "TL",
                "dang": q.get("dang") or "Chưa phân dạng",
                "muc": muc if _has_level(q.get("raw") or "") else "",
                "text": _plain(q.get("text") or ""),
            }
        )
    return items


def _refresh_index(path, qs):
    d = base.index_data()
    counts = {}
    kinds = {}
    for q in qs:
        name = str(q.get("dang") or "Chưa phân dạng").strip() or "Chưa phân dạng"
        counts[name] = counts.get(name, 0) + 1
        k = str(q.get("kind") or "TL")
        bucket = kinds.setdefault(name, {"TN": 0, "DS": 0, "TLN": 0, "TL": 0})
        bucket[k] = bucket.get(k, 0) + 1
    for x in d.get("lessons") or []:
        if str(x.get("path") or x.get("file") or "") == path:
            x["questions"] = len(qs)
            x["count"] = len(qs)
            x["dang"] = counts
            x["dang_kinds"] = kinds
            break
    try:
        base.save_json_github(base.INDEX_FILE, d, "bank_index.json", "ADMIN AI cập nhật dạng bài " + path)
    except Exception:
        try:
            base.INDEX_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


def _clear_caches():
    try:
        import dang_routes as dr
        dr._STATS_CACHE.clear()
        dr._QID_CACHE.clear()
    except Exception:
        pass


def _fold(s):
    t = unicodedata.normalize("NFD", str(s or "").casefold())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("đ", "d")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _tokens(s):
    stop = {
        "bai", "dang", "cau", "va", "cua", "trong", "cac", "lop", "chuong",
        "mot", "hay", "voi", "cho", "khi", "la", "tu", "on", "tap", "ve",
    }
    return [w for w in _fold(s).split() if len(w) > 1 and w not in stop]


def _sim(a, b):
    fa, fb = _fold(a), _fold(b)
    if not fa or not fb:
        return 0.0
    if fa == fb:
        return 1.0
    if fa in fb or fb in fa:
        return 0.86 if min(len(fa), len(fb)) >= 8 else 0.72
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _lop_key(s):
    m = re.search(r"(\d{1,2})", str(s or ""))
    return m.group(1) if m else ""


def _mon_key(s):
    return _fold(s).replace(" ", "")


def _homes():
    buckets = {}
    for x in base.index_data().get("lessons") or []:
        if not isinstance(x, dict):
            continue
        p = str(x.get("path") or x.get("file") or "").replace("\\", "/")
        if not p.startswith("ngan-hang/"):
            continue
        buckets.setdefault(base.lesson_folder(p), []).append(x)
    rows = []
    for folder, arr in buckets.items():
        title = base.lesson_card_title(folder, arr)
        dangs = set()
        mon = lop = chuong = ""
        de = folder + "/de.tex"
        for x in arr:
            mon = mon or str(x.get("Mon") or "")
            lop = lop or str(x.get("Lop") or "")
            chuong = chuong or str(x.get("Chuong") or "")
            pp = str(x.get("path") or "").replace("\\", "/")
            if pp.endswith("/de.tex"):
                de = pp
            for k in x.get("dang") or {}:
                name = _norm_dang(k)
                if name != "Chưa phân dạng":
                    dangs.add(name)
        rows.append(
            {
                "folder": folder,
                "title": title,
                "Mon": mon,
                "Lop": lop,
                "Chuong": chuong,
                "dangs": dangs,
                "de": de,
            }
        )
    return rows


def _score_home(dang, home):
    st = _sim(dang, home.get("title") or "")
    sd = max((_sim(dang, d) for d in (home.get("dangs") or [])), default=0.0)
    return max(st, sd)


def _suggest_for_dangs(path, dang_names, counts):
    cur_folder = base.lesson_folder(path)
    homes = _homes()
    cur = next((h for h in homes if h["folder"] == cur_folder), None)
    if not cur:
        cur = {
            "folder": cur_folder,
            "title": cur_folder.rsplit("/", 1)[-1],
            "Mon": "",
            "Lop": "",
            "Chuong": "",
            "dangs": set(),
            "de": cur_folder + "/de.tex",
        }
    mon, lop = _mon_key(cur["Mon"]), _lop_key(cur["Lop"])
    out = []
    for dang in dang_names:
        dang = _norm_dang(dang)
        if dang in {"", "Chưa phân dạng"}:
            continue
        here = _sim(dang, cur.get("title") or "")
        best = None
        best_s = -1.0
        why = ""
        for h in homes:
            if h["folder"] == cur_folder:
                continue
            if mon and _mon_key(h["Mon"]) != mon:
                continue
            if lop and _lop_key(h["Lop"]) != lop:
                continue
            s = _score_home(dang, h)
            if h.get("Chuong") and cur.get("Chuong") and str(h["Chuong"]) == str(cur["Chuong"]):
                s += 0.04
            if s > best_s:
                best_s = s
                best = h
                if max((_sim(dang, d) for d in h["dangs"]), default=0) >= 0.86:
                    why = "Bài đích đã có dạng gần giống."
                else:
                    why = "Tên dạng khớp tên bài đích hơn bài hiện tại."
        if not best or best_s < 0.42 or best_s < here + 0.12:
            continue
        out.append(
            {
                "dang": dang,
                "n": int((counts or {}).get(dang) or 0),
                "folder": best["folder"],
                "to_title": best["title"],
                "from_title": cur["title"],
                "score": round(best_s, 3),
                "here": round(here, 3),
                "why": why,
            }
        )
    return out, homes, cur


def _parse_move_json(text):
    s = str(text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    if m:
        s = m.group(1).strip()
    a = s.find("[")
    b = s.rfind("]")
    if a < 0 or b <= a:
        return []
    data = json.loads(s[a : b + 1])
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        dang = _norm_dang(item.get("dang"))
        folder = str(item.get("folder") or "").replace("\\", "/").rstrip("/")
        if dang in {"", "Chưa phân dạng"} or not folder.startswith("ngan-hang/"):
            continue
        out.append({"dang": dang, "folder": folder, "why": str(item.get("why") or "").strip()[:200]})
    return out


def _ai_moves(cur, homes, dang_names, keys):
    same = [
        h
        for h in homes
        if _mon_key(h["Mon"]) == _mon_key(cur["Mon"]) and _lop_key(h["Lop"]) == _lop_key(cur["Lop"])
    ]
    lines = []
    for h in same[:55]:
        ds = ", ".join(sorted(h["dangs"])[:8]) or "—"
        lines.append(f"- folder={h['folder']} | bài={h['title']} | dạng={ds}")
    prompt = (
        "Bạn là giáo viên THPT. Một số DẠNG BÀI đang nằm trong bài hiện tại có thể thuộc bài khác.\n"
        f"Bài hiện tại: {cur.get('title')} (folder={cur.get('folder')})\n"
        "Các bài cùng môn/lớp (folder phải copy đúng):\n"
        + "\n".join(lines)
        + "\nDạng cần xét: "
        + ", ".join(dang_names)
        + "\nChỉ đề xuất dạng THỰC SỰ lệch bài. Không chuyển nếu dạng đúng bài hiện tại.\n"
        'Trả về DUY NHẤT JSON: [{"dang":"...","folder":"ngan-hang/...","why":"..."}]\n'
        "Nếu không có dạng lệch, trả []."
    )
    raw = ""
    for key in keys:
        try:
            raw = _gemini_generate(key, prompt, 4000, 0.1)
            if raw:
                break
        except Exception:
            continue
    if not raw:
        return []
    try:
        return _parse_move_json(raw)
    except Exception:
        return []


def _merge_ai_moves(heuristic, ai_rows, homes, counts, cur):
    by_folder = {h["folder"]: h for h in homes}
    found = {m["dang"]: m for m in heuristic}
    for row in ai_rows:
        h = by_folder.get(row["folder"])
        if not h or h["folder"] == cur["folder"]:
            continue
        dang = row["dang"]
        item = {
            "dang": dang,
            "n": int((counts or {}).get(dang) or (found.get(dang) or {}).get("n") or 0),
            "folder": h["folder"],
            "to_title": h["title"],
            "from_title": cur.get("title") or "",
            "score": 0.9,
            "here": 0,
            "why": row.get("why") or "AI gợi ý chuyển về bài này.",
        }
        old = found.get(dang)
        if old and old["folder"] != item["folder"]:
            item["why"] = (row.get("why") or item["why"]) + " (AI chọn bài này.)"
        found[dang] = item
    return list(found.values())


def _strip_to_questions(tex):
    m = re.search(
        r"(?im)^(?:\\dang(?:bt)?\s*\{|[ \t]*%[ \t]*(?:=+[ \t]*Câu|ID\s*:)|\\begin\s*\{\s*(?:ex|bt))",
        tex or "",
    )
    if m:
        return (tex[m.start() :].strip() + "\n")
    m2 = BLOCK_RE.search(tex or "")
    return (tex[m2.start() :].strip() + "\n") if m2 else ""


def _extract_chunk(tex, by_idx, idxs, dang):
    body = apply_taxonomy(tex, by_idx, keep=set(idxs))
    chunk = _strip_to_questions(body)
    if not re.search(r"\\dang(?:bt)?\s*\{", chunk[:500], re.I):
        chunk = "\\dangbt{" + dang + "}\n" + chunk
    return chunk


def _preamble(tex, bai_line):
    lines = []
    for ln in (tex or "").splitlines():
        if re.match(r"\s*%\s*(Môn|Lớp|Chương)\s*:", ln, re.I):
            lines.append(ln)
        if len(lines) >= 3:
            break
    lines.append("% Bài: " + bai_line)
    return "\n".join(lines) + "\n"


def _dest_tex_path(folder, dang):
    folder = str(folder).replace("\\", "/").rstrip("/")
    paths = []
    try:
        paths = [p.replace("\\", "/") for p in base.lesson_tex_paths(folder + "/de.tex")]
    except Exception:
        paths = []
    for p in paths:
        try:
            _, t = base.read_tex(p)
            if any(_norm_dang(q.get("dang")) == dang for q in base.parse_questions(t)):
                return p
        except Exception:
            continue
    name = f"dang-{_slug_dang(dang)}.tex"
    return folder + "/" + name


def select_admin_panel(path, qs, dang_names):
    uncat = sum(1 for q in qs if str(q.get("dang") or "") in {"", "Chưa phân dạng"})
    boxes = []
    for name in dang_names:
        if name in {"", "Chưa phân dạng"}:
            continue
        n = sum(1 for q in qs if q.get("dang") == name)
        boxes.append(
            "<label class='resortbox'><input type='checkbox' class='resort' value='"
            + html.escape(name, quote=True)
            + "'> Sắp xếp lại · "
            + html.escape(name)
            + f" <span class='muted'>({n} câu)</span></label>"
        )
    return (
        "<div class='review' id='ai-classify' style='margin-bottom:12px'>"
        "<b>🤖 ADMIN · AI phân dạng và mức độ</b>"
        f"<p class='muted'>Câu chưa có dạng: <b>{uncat}</b> / {len(qs)}. "
        "Dạng <span class='tag miss'>Chưa có</span> cần xếp. Dạng <span class='tag had'>Đã có</span> mặc định giữ nguyên — tick ô dưới nếu muốn xếp lại.</p>"
        "<p class='muted'>ID tự động theo thư mục, ví dụ <code>L12C1B3-03-DS</code> · mức <code>NB/TH/VD/VDC</code> do AI. "
        "Tách file: mỗi dạng một <code>dang-....tex</code> cùng thư mục bài; file hiện tại chỉ giữ câu chưa phân dạng.</p>"
        "<p class='muted'>Nếu dạng thuộc <b>bài khác</b> (trùng tên dạng hoặc khớp tên bài), hệ thống gợi ý chuyển — chỉ chuyển khi ADMIN bấm <b>Đồng ý</b>.</p>"
        "<label><input type='checkbox' id='onlyNew' checked> Chỉ câu «Chưa phân dạng» + các dạng đã tick «Sắp xếp lại» (bỏ tick = AI xếp lại cả file)</label>"
        + ("<div class='resortlist'>" + "".join(boxes) + "</div>" if boxes else "<p class='muted'>File này chưa có dạng nào — AI sẽ đặt dạng mới.</p>")
        + "<div class='gkeyrow'><button type='button' class='btn primary' id='aiPrev'>🤖 Xem gợi ý AI</button> "
        "<button type='button' class='btn green' id='aiSave' disabled>💾 Ghi vào TEX + GitHub</button>"
        "<button type='button' class='btn' id='aiIds'>🔢 Gán ID còn thiếu</button>"
        "<button type='button' class='btn' id='aiSplit'>📂 Tách mỗi dạng ra file .tex</button>"
        "<button type='button' class='btn' id='aiHome'>🚚 Gợi ý chuyển sang bài đúng</button></div>"
        "<div id='aiOut' class='reviewout'></div></div>"
        "<style>.tag.had{background:#eefbf2;border-color:#83d39e;color:#14743a}.tag.miss{background:#fff8df;border-color:#efca73;color:#855a00}"
        ".resortlist{display:grid;gap:6px;margin:8px 0;padding:8px;border:1px dashed #cab9f0;border-radius:8px;background:#fff}"
        ".resortbox{display:flex;align-items:flex-start;gap:8px;font-weight:700;line-height:1.4}.selectgrid tr.uncat td:first-child{background:#fff8df}</style>"
        + _admin_js(path)
    )


def _admin_js(path):
    p = json.dumps(path, ensure_ascii=False)
    return r"""<script>
(function(){
const PATH=__PATH__;
let LAST=null;
let MOVES=[];
function keys(){return (window.ldvlFilledKeys&&ldvlFilledKeys())||[];}
function out(h){const el=document.getElementById('aiOut');if(el)el.innerHTML=h;}
function resorts(){return [...document.querySelectorAll('.resort:checked')].map(x=>x.value);}
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}
function renderMoves(extra){
  extra=extra||'';
  if(!MOVES.length){out(extra+'<div class="muted">Không thấy dạng nào giống bài khác.</div>');return;}
  const rows=MOVES.map((m,i)=>'<tr><td><input type="checkbox" class="mv" data-i="'+i+'" checked></td><td><b>'+esc(m.dang)+'</b><div class="muted">'+esc(m.n||0)+' câu</div></td><td>'+esc(m.from_title||'')+'</td><td><b>'+esc(m.to_title||'')+'</b><div class="muted">'+esc(m.why||'')+'</div></td></tr>').join('');
  out(extra+'<div class="success">Gợi ý chuyển <b>'+MOVES.length+'</b> dạng sang bài khác. Tick rồi bấm Đồng ý — chưa tick thì giữ nguyên.</div>'
    +'<div class="selectwrap"><table class="selectgrid"><tr><th></th><th>Dạng</th><th>Đang ở</th><th>Chuyển tới</th></tr>'+rows+'</table></div>'
    +'<p><button type="button" class="btn green" id="aiMoveGo">✅ Đồng ý chuyển các dạng đã tick</button></p>');
  const go=document.getElementById('aiMoveGo');
  if(go) go.addEventListener('click',doMove);
}
async function doMove(){
  const picked=[...document.querySelectorAll('.mv:checked')].map(x=>MOVES[+x.getAttribute('data-i')]).filter(Boolean);
  if(!picked.length){alert('Chưa tick dạng nào.');return;}
  if(!confirm('Chuyển '+picked.length+' dạng sang bài được gợi ý? ID sẽ gán lại theo bài đích.'))return;
  out('⏳ Đang chuyển...');
  try{
    if(LAST&&LAST.length){
      const s=await fetch('/api/admin/ai-classify-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({path:PATH,assignments:LAST})});
      const sd=await s.json();
      if(!sd.ok){out('<div class="err">'+(sd.error||'Chưa ghi được dạng, không chuyển.')+'</div>');return;}
    }
    const r=await fetch('/api/admin/move-dang',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:PATH,moves:picked.map(m=>({dang:m.dang,folder:m.folder}))})});
    const d=await r.json();
    if(!d.ok){out('<div class="err">'+(d.error||'Không chuyển được')+'</div>');return;}
    const n=(d.moved||[]).length;
    out('<div class="success">✅ Đã chuyển '+n+' dạng. Đang tải lại...</div>');
    location.reload();
  }catch(e){out('<div class="err">'+e+'</div>');}
}
async function loadMoves(dangs, counts){
  const k=keys();
  const r=await fetch('/api/admin/suggest-moves',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({path:PATH,dangs:dangs||[],counts:counts||{},api_keys:k})});
  const d=await r.json();
  if(!d.ok) throw new Error(d.error||'Lỗi gợi ý');
  MOVES=d.moves||[];
  return d;
}
async function preview(){
  const k=keys();
  if(!k.length){alert('Nạp key Gemini (trang 🤖 Gemini hoặc ô key trên máy này) rồi thử lại.');return;}
  const btn=document.getElementById('aiPrev'), sav=document.getElementById('aiSave');
  btn.disabled=true; if(sav)sav.disabled=true; LAST=null;
  out('⏳ Đang gọi AI phân dạng...');
  try{
    const r=await fetch('/api/admin/ai-classify',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:PATH,api_keys:k,only_new:!!document.getElementById('onlyNew').checked,resort:resorts()})});
    const d=await r.json();
    if(!d.ok){out('<div class="err">'+(d.error||'Lỗi AI')+'</div>');return;}
    LAST=d.assignments||[];
    if(!LAST.length){out('<div class="muted">Không có câu nào cần xếp (bỏ tick «Chỉ chưa phân dạng» hoặc tick «Sắp xếp lại»).</div>');return;}
    let rows=LAST.map(a=>'<tr><td>'+a.idx+'</td><td>'+(a.id||'—')+'</td><td>'+(a.old_dang||'')+'</td><td><b>'+a.dang+'</b></td><td>'+(a.old_muc||'')+' → <b>'+a.muc+'</b></td></tr>').join('');
    const table='<div class="success">Gợi ý '+LAST.length+' câu. Kiểm tra rồi bấm Ghi vào TEX.</div><div class="selectwrap"><table class="selectgrid"><tr><th>idx</th><th>ID</th><th>Dạng cũ</th><th>Dạng AI</th><th>Mức</th></tr>'+rows+'</table></div>';
    out(table);
    if(sav)sav.disabled=false;
    try{
      const names=[...new Set(LAST.map(a=>a.dang).filter(x=>x&&x!=='Chưa phân dạng'))];
      const counts={}; LAST.forEach(a=>{if(a.dang) counts[a.dang]=(counts[a.dang]||0)+1});
      await loadMoves(names, counts);
      if(MOVES.length) renderMoves(table);
    }catch(e){}
  }catch(e){out('<div class="err">'+e+'</div>');}
  finally{btn.disabled=false;}
}
async function save(){
  if(!LAST||!LAST.length)return;
  if(!confirm('Ghi dạng/mức mới vào file TEX và commit GitHub?'))return;
  const k=keys();
  const sav=document.getElementById('aiSave'); sav.disabled=true;
  out('⏳ Đang ghi TEX...');
  try{
    const r=await fetch('/api/admin/ai-classify-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:PATH,assignments:LAST})});
    const d=await r.json();
    if(!d.ok){out('<div class="err">'+(d.error||'Không ghi được')+'</div>');sav.disabled=false;return;}
    out('<div class="success">✅ Đã lưu '+ (d.changed||LAST.length) +' câu. Đang tải lại trang...</div>');
    location.reload();
  }catch(e){out('<div class="err">'+e+'</div>');sav.disabled=false;}
}
document.getElementById('aiPrev').addEventListener('click',preview);
document.getElementById('aiSave').addEventListener('click',save);
document.getElementById('aiIds').addEventListener('click',async function(){
  if(!confirm('Gán ID còn thiếu theo quy ước thư mục (ví dụ L12C1B3-08-TN) rồi ghi GitHub?'))return;
  out('⏳ Đang gán ID...');
  try{
    const r=await fetch('/api/admin/stamp-ids',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({path:PATH})});
    const d=await r.json();
    if(!d.ok){out('<div class="err">'+(d.error||'Lỗi gán ID')+'</div>');return;}
    out('<div class="success">✅ Prefix <b>'+(d.prefix||'')+'</b> · gán mới '+(d.ids||0)+' ID. Đang tải lại...</div>');
    location.reload();
  }catch(e){out('<div class="err">'+e+'</div>');}
});
document.getElementById('aiSplit').addEventListener('click',async function(){
  if(!confirm('Tách mỗi dạng đã có thành file dang-....tex trong cùng thư mục? File này sẽ chỉ còn câu «Chưa phân dạng».'))return;
  out('⏳ Đang tách file...');
  try{
    const r=await fetch('/api/admin/split-dang',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({path:PATH})});
    const d=await r.json();
    if(!d.ok){out('<div class="err">'+(d.error||'Lỗi tách file')+'</div>');return;}
    const n=(d.created||[]).length;
    out('<div class="success">✅ Đã tạo '+n+' file dạng. Còn '+(d.leftover||0)+' câu chưa phân dạng. Mở mục lục để vào file mới.</div>');
    setTimeout(function(){location.href='/member';},1200);
  }catch(e){out('<div class="err">'+e+'</div>');}
});
document.getElementById('aiHome').addEventListener('click',async function(){
  out('⏳ Đang đối chiếu dạng với các bài cùng môn/lớp...');
  try{
    await loadMoves([]);
    renderMoves();
  }catch(e){out('<div class="err">'+e+'</div>');}
});
})();</script>""".replace("__PATH__", p)


@base.app.post("/api/admin/ai-classify")
def api_ai_classify():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới phân dạng bằng AI."), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").strip()
    if not path:
        return jsonify(ok=False, error="Thiếu path."), 400
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error="Chưa có Gemini API key."), 400
    try:
        _, tex = base.read_tex(path)
        qs = base.parse_questions(tex)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    only_new = bool(data.get("only_new", True))
    resort = {_norm_dang(x) for x in (data.get("resort") or []) if str(x).strip()}
    want = set()
    for q in qs:
        dang = str(q.get("dang") or "Chưa phân dạng")
        if dang in {"", "Chưa phân dạng"}:
            want.add(int(q["idx"]))
        elif dang in resort:
            want.add(int(q["idx"]))
        elif not only_new:
            want.add(int(q["idx"]))
    items = _items_for_ai(qs, want)
    if not items:
        return jsonify(ok=True, assignments=[], message="Không có câu cần xếp.")
    existing = []
    seen = set()
    for q in qs:
        n = str(q.get("dang") or "")
        if n and n != "Chưa phân dạng" and n not in seen:
            seen.add(n)
            existing.append(n)
    locked = [x for x in existing if x not in resort]
    meta = path.replace("ngan-hang/", "").replace("/de.tex", "")
    prompt = _prompt(meta, existing, locked, items)
    last_err = "Gemini không trả lời."
    raw = ""
    for i, key in enumerate(keys, 1):
        try:
            raw = _gemini_generate(key, prompt, 8000, 0.1)
            if raw:
                break
            last_err = f"Key {i}: trống."
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            last_err = f"Key {i}: Gemini {e.code}: {msg[:240]}"
        except Exception as e:
            last_err = f"Key {i}: {e}"
    if not raw:
        return jsonify(ok=False, error=last_err), 502
    try:
        guessed = _parse_ai_json(raw)
    except Exception as e:
        return jsonify(ok=False, error="Không đọc được JSON từ AI: " + str(e)), 502
    by_id = {int(q["idx"]): q for q in qs}
    asg = []
    seen_idx = set()
    for g in guessed:
        idx = int(g["idx"])
        if idx not in want or idx in seen_idx:
            continue
        q = by_id.get(idx) or {}
        asg.append(
            {
                "idx": idx,
                "id": q.get("id") or "",
                "dang": g["dang"] if g["dang"] != "Chưa phân dạng" else (q.get("dang") or "Chưa phân dạng"),
                "muc": g["muc"],
                "old_dang": q.get("dang") or "",
                "old_muc": MUC_FROM_LETTER.get(str(q.get("level") or "H"), "TH"),
            }
        )
        seen_idx.add(idx)
    return jsonify(ok=True, assignments=asg, used=len(asg))


@base.app.post("/api/admin/ai-classify-save")
def api_ai_classify_save():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới ghi phân dạng."), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").strip()
    rows = data.get("assignments") or []
    if not path or not isinstance(rows, list) or not rows:
        return jsonify(ok=False, error="Thiếu danh sách gán dạng."), 400
    try:
        sha, tex = base.read_tex(path, need_sha=True)
        qs = base.parse_questions(tex)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    by_idx = _map_from_questions(qs)
    changed = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            i = int(row.get("idx"))
        except (TypeError, ValueError):
            continue
        if i not in by_idx:
            continue
        dang = _norm_dang(row.get("dang"))
        muc = _norm_muc(row.get("muc") or row.get("level"))
        if dang != by_idx[i]["dang"] or muc != by_idx[i]["muc"]:
            changed += 1
        by_idx[i]["dang"] = dang
        by_idx[i]["muc"] = muc
    new = apply_taxonomy(tex, by_idx)
    new, n_id, _ = stamp_missing_ids(new, path, by_idx)
    if new == tex:
        return jsonify(ok=True, changed=0, message="Không có thay đổi.")
    try:
        _, local = base._safe_repo_file(path)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(new, encoding="utf-8")
        if base.TOKEN:
            base.github_put_text(path, new, "ADMIN AI phân dạng " + path, sha or None)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    try:
        qs2 = base.parse_questions(new)
        _refresh_index(path, qs2)
    except Exception:
        pass
    _clear_caches()
    return jsonify(ok=True, changed=changed or len(rows), ids=n_id)


@base.app.post("/api/admin/stamp-ids")
def api_stamp_ids():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới gán ID."), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").strip()
    if not path:
        return jsonify(ok=False, error="Thiếu path."), 400
    try:
        sha, tex = base.read_tex(path, need_sha=True)
        new, n_id, _ = stamp_missing_ids(tex, path)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    if new == tex:
        return jsonify(ok=True, ids=0, prefix=id_prefix_from_path(path), message="Mọi câu đã có ID đúng quy ước.")
    try:
        _write_tex(path, new, "ADMIN gán ID " + path, sha)
        _refresh_index(path, base.parse_questions(new))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    _clear_caches()
    return jsonify(ok=True, ids=n_id, prefix=id_prefix_from_path(path))


@base.app.post("/api/admin/split-dang")
def api_split_dang():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới tách file theo dạng."), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").strip()
    if not path:
        return jsonify(ok=False, error="Thiếu path."), 400
    try:
        sha, tex = base.read_tex(path, need_sha=True)
        qs = base.parse_questions(tex)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    by_idx = _map_from_questions(qs)
    groups = {}
    for q in qs:
        dang = _norm_dang(q.get("dang"))
        groups.setdefault(dang, []).append(int(q.get("idx")))
    named = {k: v for k, v in groups.items() if k != "Chưa phân dạng" and v}
    if not named:
        return jsonify(ok=False, error="Chưa có dạng nào để tách. Hãy chạy AI phân dạng trước."), 400
    folder_rel = path.replace("\\", "/").rsplit("/", 1)[0]
    _, local = base._safe_repo_file(path)
    existing = {p.name for p in local.parent.glob("*.tex")}
    mon, lop, chuong, bai0 = _header_fields(path, tex)
    created = []
    for dang, idxs in named.items():
        new_path = _new_dang_path(folder_rel, dang, existing)
        body = apply_taxonomy(tex, by_idx, keep=set(idxs))
        # Đổi dòng % Bài: để mục lục phân biệt file
        title = (bai0 or "Bài") + " · " + dang
        if re.search(r"(?m)^\s*%\s*Bài\s*:", body):
            body = re.sub(r"(?m)^(\s*%\s*Bài\s*:\s*).+$", r"\1" + title, body, count=1)
        else:
            body = "% Bài: " + title + "\n" + body
        try:
            _write_tex(new_path, body, "ADMIN tách dạng " + dang)
            try:
                base.index_upsert_lesson(new_path, mon, lop, chuong, title)
            except Exception:
                pass
            _refresh_index(new_path, base.parse_questions(body))
        except Exception as e:
            return jsonify(ok=False, error=str(e), created=created), 500
        created.append({"path": new_path, "dang": dang, "n": len(idxs)})
    leftover = set(groups.get("Chưa phân dạng") or [])
    rest = apply_taxonomy(tex, by_idx, keep=leftover)
    try:
        _write_tex(path, rest, "ADMIN để lại câu chưa phân dạng " + path, sha)
        _refresh_index(path, base.parse_questions(rest))
    except Exception as e:
        return jsonify(ok=False, error=str(e), created=created), 500
    _clear_caches()
    return jsonify(ok=True, created=created, leftover=len(leftover))


@base.app.post("/api/admin/suggest-moves")
def api_suggest_moves():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới xem gợi ý chuyển bài."), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").strip()
    if not path:
        return jsonify(ok=False, error="Thiếu path."), 400
    try:
        _, tex = base.read_tex(path)
        qs = base.parse_questions(tex)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    counts = {}
    for q in qs:
        d = _norm_dang(q.get("dang"))
        counts[d] = counts.get(d, 0) + 1
    extra = data.get("counts") if isinstance(data.get("counts"), dict) else {}
    for k, v in extra.items():
        try:
            counts[_norm_dang(k)] = int(v)
        except (TypeError, ValueError):
            continue
    names = [_norm_dang(x) for x in (data.get("dangs") or []) if str(x).strip()]
    if not names:
        names = [d for d in counts if d not in {"", "Chưa phân dạng"}]
    moves, homes, cur = _suggest_for_dangs(path, names, counts)
    keys = _keys_from_payload(data)
    if keys and names:
        try:
            ai_rows = _ai_moves(cur, homes, names, keys)
            if ai_rows:
                moves = _merge_ai_moves(moves, ai_rows, homes, counts, cur)
        except Exception:
            pass
    return jsonify(ok=True, moves=moves)


@base.app.post("/api/admin/move-dang")
def api_move_dang():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới chuyển dạng sang bài khác."), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").strip()
    rows = data.get("moves") or []
    if not path or not isinstance(rows, list) or not rows:
        return jsonify(ok=False, error="Thiếu danh sách chuyển."), 400
    try:
        sha, tex = base.read_tex(path, need_sha=True)
        qs = base.parse_questions(tex)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    by_idx = _map_from_questions(qs)
    groups = {}
    for q in qs:
        groups.setdefault(_norm_dang(q.get("dang")), []).append(int(q.get("idx")))
    homes = {h["folder"]: h for h in _homes()}
    moved_idxs = set()
    done = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        dang = _norm_dang(row.get("dang"))
        folder = str(row.get("folder") or "").replace("\\", "/").rstrip("/")
        if dang in {"", "Chưa phân dạng"} or ".." in folder.split("/") or not folder.startswith("ngan-hang/"):
            continue
        h = homes.get(folder)
        if not h:
            return jsonify(ok=False, error="Không tìm thấy bài đích: " + folder), 400
        if folder == base.lesson_folder(path):
            continue
        idxs = [i for i in (groups.get(dang) or []) if i not in moved_idxs]
        if not idxs:
            continue
        chunk = _extract_chunk(tex, by_idx, idxs, dang)
        dest = _dest_tex_path(folder, dang)
        existed = False
        dsha, dtex = None, ""
        try:
            dsha, dtex = base.read_tex(dest, need_sha=True)
            existed = True
        except Exception:
            existed = False
        if existed:
            new_dest = dtex.rstrip() + "\n\n" + chunk + "\n"
        else:
            try:
                _, de_tex = base.read_tex(h.get("de") or (folder + "/de.tex"))
            except Exception:
                de_tex = ""
            title = (h.get("title") or "Bài") + " · " + dang
            new_dest = _preamble(de_tex, title) + chunk
        new_dest, _, _ = stamp_missing_ids(new_dest, dest)
        try:
            _write_tex(dest, new_dest, "ADMIN chuyển dạng " + dang + " → " + folder, dsha if existed else None)
            if not dest.replace("\\", "/").endswith("/de.tex"):
                try:
                    base.index_upsert_lesson(
                        dest,
                        h.get("Mon") or "",
                        h.get("Lop") or "",
                        h.get("Chuong") or "",
                        (h.get("title") or "Bài") + " · " + dang,
                    )
                except Exception:
                    pass
            _refresh_index(dest, base.parse_questions(new_dest))
        except Exception as e:
            return jsonify(ok=False, error=str(e), moved=done), 500
        moved_idxs.update(idxs)
        done.append({"dang": dang, "n": len(idxs), "dest": dest, "folder": folder})
    if not done:
        return jsonify(ok=False, error="Không có câu nào để chuyển (hãy ghi dạng vào TEX trước)."), 400
    keep = {int(q.get("idx")) for q in qs} - moved_idxs
    rest = apply_taxonomy(tex, by_idx, keep=keep)
    try:
        _write_tex(path, rest, "ADMIN chuyển dạng khỏi " + path, sha)
        _refresh_index(path, base.parse_questions(rest))
    except Exception as e:
        return jsonify(ok=False, error=str(e), moved=done), 500
    _clear_caches()
    return jsonify(ok=True, moved=done)

