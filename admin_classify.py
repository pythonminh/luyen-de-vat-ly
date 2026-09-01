# -*- coding: utf-8 -*-
"""ADMIN: AI phân dạng + mức độ trên trang /member/select."""
from __future__ import annotations
import html
import json
import re
import urllib.error
import urllib.parse
from flask import jsonify, request

import app as base
from student_gemini import _gemini_generate, _keys_from_payload

BLOCK_RE = re.compile(r"\\begin\s*\{\s*(?:ex|bt)\s*\}[\s\S]*?\\end\s*\{\s*(?:ex|bt)\s*\}", re.I)
DANG_LINE_RE = re.compile(r"^[ \t]*\\dang(?:bt)?\s*\{[^{}]*\}[ \t]*\r?\n?", re.I | re.M)
LEVEL_LINE_RE = re.compile(r"(%\s*(?:Mức|Muc|Muc do)\s*:\s*)([^\r\n%]*)", re.I)

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


def apply_taxonomy(tex, by_idx):
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
        head, qhead = _split_qhead(inter)
        qhead = _set_level(qhead, muc) if qhead.strip() else qhead
        block = _set_level(m.group(0), muc)
        if dang != "Chưa phân dạng" and dang != last_dang:
            qhead = qhead.rstrip() + "\n\\dangbt{" + dang + "}\n"
            last_dang = dang
        elif dang == "Chưa phân dạng":
            last_dang = "Chưa phân dạng"
        chunks.append(head)
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
        "<label><input type='checkbox' id='onlyNew' checked> Chỉ câu «Chưa phân dạng» + các dạng đã tick «Sắp xếp lại» (bỏ tick = AI xếp lại cả file)</label>"
        + ("<div class='resortlist'>" + "".join(boxes) + "</div>" if boxes else "<p class='muted'>File này chưa có dạng nào — AI sẽ đặt dạng mới.</p>")
        + "<div class='gkeyrow'><button type='button' class='btn primary' id='aiPrev'>🤖 Xem gợi ý AI</button> "
        "<button type='button' class='btn green' id='aiSave' disabled>💾 Ghi vào TEX + GitHub</button></div>"
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
function keys(){return (window.ldvlFilledKeys&&ldvlFilledKeys())||[];}
function out(h){const el=document.getElementById('aiOut');if(el)el.innerHTML=h;}
function resorts(){return [...document.querySelectorAll('.resort:checked')].map(x=>x.value);}
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
    out('<div class="success">Gợi ý '+LAST.length+' câu. Kiểm tra rồi bấm Ghi vào TEX.</div><div class="selectwrap"><table class="selectgrid"><tr><th>idx</th><th>ID</th><th>Dạng cũ</th><th>Dạng AI</th><th>Mức</th></tr>'+rows+'</table></div>');
    if(sav)sav.disabled=false;
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
    by_idx = {}
    for q in qs:
        i = int(q.get("idx"))
        by_idx[i] = {
            "dang": q.get("dang") or "Chưa phân dạng",
            "muc": MUC_FROM_LETTER.get(str(q.get("level") or "H"), "TH"),
        }
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
        by_idx[i] = {"dang": dang, "muc": muc}
    new = apply_taxonomy(tex, by_idx)
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
    return jsonify(ok=True, changed=changed or len(rows))
