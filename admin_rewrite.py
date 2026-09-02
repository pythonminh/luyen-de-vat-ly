# -*- coding: utf-8 -*-
"""ADMIN: AI viết lại đề + lời giải; chỉ ghi TEX khi ADMIN chấp nhận."""
from __future__ import annotations

import json
import re

from flask import jsonify, request

import app as base
from student_gemini import _keys_from_payload

_TAIL_RE = re.compile(r"\\(?:choiceTF|choice|shortans|loigiai)\b", re.I)
_FORBIDDEN = re.compile(r"\\(?:begin|end)\s*\{\s*(?:ex|bt)\s*\}", re.I)


def _repair_json_latex(s):
    """JSON biến \\frac thành form-feed; gấp đôi backslash lệnh LaTeX trong chuỗi."""
    out = []
    in_str = False
    esc = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if not in_str:
            if c == '"':
                in_str = True
            out.append(c)
            i += 1
            continue
        if esc:
            out.append(c)
            esc = False
            i += 1
            continue
        if c == "\\":
            nxt = s[i + 1] if i + 1 < n else ""
            rest = s[i + 1 : i + 12]
            if nxt == "f" and rest.startswith("frac"):
                out.append("\\\\")
                i += 1
                continue
            if nxt == "b" and (rest.startswith("egin") or rest.startswith("eta") or rest.startswith("ig")):
                out.append("\\\\")
                i += 1
                continue
            if nxt == "t" and (
                rest.startswith("ext")
                or rest.startswith("imes")
                or rest.startswith("an")
                or rest.startswith("o ")
                or rest.startswith("o$")
                or rest.startswith("heta")
            ):
                out.append("\\\\")
                i += 1
                continue
            if nxt == "n" and (rest.startswith("eq") or rest.startswith("abla") or rest.startswith("ot")):
                out.append("\\\\")
                i += 1
                continue
            if nxt in '"\\/bfnrtu':
                out.append(c)
                esc = True
                i += 1
                continue
            out.append("\\\\")
            i += 1
            continue
        if c == '"':
            in_str = False
        out.append(c)
        i += 1
    return "".join(out)


def _parse_obj(text):
    s = str(text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    if m:
        s = m.group(1).strip()
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b <= a:
        return {}
    chunk = s[a : b + 1]
    for cand in (chunk, _repair_json_latex(chunk)):
        try:
            data = json.loads(cand)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def _sect(raw, name):
    m = re.search(
        rf"===\s*{re.escape(name)}\s*===\s*([\s\S]*?)(?===\s*[A-Z]+\s*===|\Z)",
        str(raw or ""),
        re.I,
    )
    return (m.group(1).strip() if m else "")


def _extract_ai_fields(raw):
    obj = _parse_obj(raw)
    for key, name in (("stem", "STEM"), ("solution", "SOLUTION"), ("answer", "ANSWER"), ("note", "NOTE")):
        if not str(obj.get(key) or "").strip():
            got = _sect(raw, name)
            if got:
                obj[key] = got
    return obj


def _fix_latex(t):
    """Gỡ lỗi AI hay gặp: \\frac bị nuốt, \\ trước tiếng Việt, toán không bọc $."""
    t = str(t or "")
    t = t.replace("\x0c", r"\f")
    t = t.replace("\x08", r"\b")
    t = t.replace("\x0crac", r"\frac")
    t = re.sub(r"(?<!\\)\trac\{", r"\\frac{", t)
    t = re.sub(r"\\(?=[À-ỹĂăÂâÊêÔôƠơƯưĐđ])", "", t)
    t = re.sub(r"\\\s+(?=[A-ZÀ-ỸĐ])", " ", t)
    t = re.sub(r"([.:;,!?])\\(?=-?\d)", r"\1 ", t)
    t = re.sub(r"\\(?=-\d)", "-", t)
    t = re.sub(r"(?<!\\)\\([,;:])(?=\s|$)", r"\1", t)
    t = re.sub(r"\$\s*\$", "", t)
    return t.strip()


def _clean_tex(s):
    t = str(s or "").strip()
    t = re.sub(r"^```(?:latex|tex)?\s*", "", t, flags=re.I)
    t = re.sub(r"\s*```$", "", t)
    m = re.match(r"\\loigiai\s*\{", t, re.I)
    if m:
        inner, end = base.get_braced(t, m.end() - 1)
        if inner is not None and end >= len(t.rstrip()):
            t = inner.strip()
    t = _FORBIDDEN.sub("", t)
    t = re.sub(r"^\\True\s*", "", t, flags=re.I)
    return _fix_latex(t)


def _split_head_tail(inner):
    m = _TAIL_RE.search(inner or "")
    if not m:
        return inner or "", ""
    return inner[: m.start()], inner[m.start() :]


def _split_comments(head):
    lines = (head or "").splitlines(True)
    i = 0
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("%")):
        i += 1
    return "".join(lines[:i]), "".join(lines[i:]).strip()


def _replace_loigiai(block, new_inner):
    new_inner = _clean_tex(new_inner)
    m = re.search(r"\\loigiai\s*\{", block, re.I)
    if m:
        val, end = base.get_braced(block, m.end() - 1)
        if val is None:
            return block
        return block[: m.start()] + "\\loigiai{\n" + new_inner + "\n}" + block[end:]
    env = re.search(r"\\begin\s*\{\s*loigiai\s*\}.*?\\end\s*\{\s*loigiai\s*\}", block, re.I | re.S)
    if env:
        return block[: env.start()] + "\\loigiai{\n" + new_inner + "\n}" + block[env.end() :]
    return block.rstrip() + "\n\\loigiai{\n" + new_inner + "\n}\n"


def _replace_cmd_braces(block, cmd, new_vals, trues):
    m = re.search(re.escape(cmd) + r"\b", block, re.I)
    if not m or not new_vals:
        return block
    p = m.end()
    out = [block[:p]]
    for i, nv in enumerate(new_vals):
        while p < len(block) and block[p].isspace():
            out.append(block[p])
            p += 1
        val, p2 = base.get_braced(block, p)
        if val is None:
            return block
        inner = _clean_tex(nv)
        if i < len(trues) and trues[i]:
            inner = r"\True " + inner
        out.append("{" + inner + "}")
        p = p2
    out.append(block[p:])
    return "".join(out)


def _replace_shortans(block, new_ans):
    new_ans = _clean_tex(new_ans)
    m = re.search(r"\\shortans\s*(?:\[[^\]]*\])?\s*", block, re.I)
    if not m:
        return block
    val, end = base.get_braced(block, m.end())
    if val is None:
        return block
    brace = block.find("{", m.end())
    if brace < 0:
        return block
    return block[:brace] + "{" + new_ans + "}" + block[end:]


def _apply_inner(inner, kind, stem, solution, options, answer, flags):
    head, tail = _split_head_tail(inner)
    comments, _old_stem = _split_comments(head)
    if flags.get("stem") and stem:
        head = comments + stem.strip() + "\n"
    block = head + tail
    if flags.get("opts") and options and kind in {"TN", "DS"}:
        cmd = "\\choiceTF" if kind == "DS" else "\\choice"
        trues = [bool(x.get("correct")) for x in options]
        texts = [x.get("text") if isinstance(x, dict) else x for x in options]
        block = _replace_cmd_braces(block, cmd, texts, trues)
    if flags.get("answer") and answer and kind == "TLN":
        block = _replace_shortans(block, answer)
    if flags.get("sol") and solution:
        block = _replace_loigiai(block, solution)
    return block


def _replace_ex(tex, file_idx, new_inner):
    for i, m in enumerate(base.EX_RE.finditer(tex)):
        if i != file_idx:
            continue
        return tex[: m.start(1)] + new_inner.strip("\n") + "\n" + tex[m.end(1) :]
    return None


def _q_plain_pack(q):
    kind = str(q.get("kind") or "TL")
    opts = []
    if kind == "TN":
        for o in q.get("options") or []:
            opts.append(
                {
                    "text": o.get("text") if isinstance(o, dict) else o,
                    "correct": bool(o.get("correct")) if isinstance(o, dict) else False,
                }
            )
    elif kind == "DS":
        for o in q.get("statements") or []:
            opts.append(
                {
                    "text": o.get("text") if isinstance(o, dict) else o,
                    "correct": bool(o.get("correct")) if isinstance(o, dict) else False,
                }
            )
    return {
        "kind": kind,
        "id": str(q.get("id") or ""),
        "text": q.get("text") or "",
        "solution": q.get("solution") or "",
        "answer": q.get("answer") or "",
        "options": opts,
    }


def _load_q(src, file_idx):
    src = str(src or "").replace("\\", "/")
    _, tex = base.read_tex(src)
    qs = base.parse_questions(tex)
    for q in qs:
        q["src"] = src
        try:
            fi = int(q.get("idx") or 0)
        except (TypeError, ValueError):
            continue
        if fi == int(file_idx):
            q["file_idx"] = fi
            return q, tex
    return None, tex


def _prompt(pack):
    letters = "ABCD"
    opt_lines = []
    for i, o in enumerate(pack.get("options") or []):
        mark = " [ĐÚNG]" if o.get("correct") else ""
        lab = letters[i] if pack["kind"] == "TN" else str(i + 1)
        opt_lines.append(f"{lab}.{mark} {o.get('text') or ''}")
    return (
        "Bạn là giáo viên THPT soạn đề. VIẾT LẠI ĐỀ và LỜI GIẢI đúng, gọn, giọng giáo viên.\n"
        "Giữ dữ kiện, loại câu, vị trí đáp án đúng. Tính lại cho khớp.\n"
        "LaTeX BẮT BUỘC:\n"
        "- Mọi công thức (kể cả \\pi, \\frac, \\Rightarrow, \\cos, \\left\\right) phải nằm trong $...$.\n"
        "- Không gõ \\ trước chữ tiếng Việt (sai: \\Để  .\\Để  :\\-3). Viết: Để  : -3.\n"
        "- Trong JSON, mỗi backslash LaTeX phải viết HAI lần: \\\\frac \\\\pi \\\\Rightarrow \\\\left \\\\right.\n"
        "- Xuống dòng bằng \\n trong JSON, không dùng \\\\ rồi xuống dòng lung tung.\n"
        "JSON một object: "
        '{"stem":"...","options":["..."],"answer":"...","solution":"...","note":""}\n'
        "Đồng thời lặp lại lời giải thuần LaTeX giữa các mốc:\n"
        "===STEM===\n...===SOLUTION===\n...===ANSWER===\n...===NOTE===\n"
        "options cùng số lượng, không \\True. solution không bọc \\loigiai / \\begin{ex}.\n\n"
        f"Loại: {pack['kind']} · ID: {pack['id']}\n"
        f"Đề cũ:\n{pack['text']}\n"
        + ("Phương án/mệnh đề cũ:\n" + "\n".join(opt_lines) + "\n" if opt_lines else "")
        + (f"Đáp án shortans cũ: {pack['answer']}\n" if pack.get("answer") else "")
        + f"Lời giải cũ:\n{pack['solution'] or '(trống)'}\n"
    )


def _raw_parts(q):
    raw = q.get("raw") or ""
    head, _tail = _split_head_tail(raw)
    _comments, stem = _split_comments(head)
    sol = base.solution_of(raw) or (q.get("solution") or "")
    return stem.strip(), sol.strip()


def _pack_payload(src, fi, kind, stem, solution, answer, options, note=""):
    opt_html = ""
    if options and kind == "TN":
        bits = []
        for i, o in enumerate(options[:4]):
            mark = " <span class='okmark'>Đáp án đúng</span>" if o.get("correct") else ""
            bits.append(
                f"<div class='opt{' ok' if o.get('correct') else ''}'><b>{'ABCD'[i]}.</b> {base.html_question(o.get('text',''))}{mark}</div>"
            )
        opt_html = "<div class='opts'>" + "".join(bits) + "</div>"
    elif options and kind == "DS":
        bits = []
        for i, o in enumerate(options):
            yes = bool(o.get("correct"))
            mark = f" <span class='okmark'>{'Đúng' if yes else 'Sai'}</span>"
            bits.append(
                f"<div class='tf{' ok' if yes else ' noans'}'><div class='tf-text'><b>{i+1}.</b> {base.html_question(o.get('text',''))}{mark}</div></div>"
            )
        opt_html = "<div class='tfgrid'>" + "".join(bits) + "</div>"
    return {
        "ok": True,
        "src": src,
        "file_idx": fi,
        "kind": kind,
        "note": note,
        "stem": stem,
        "solution": solution,
        "answer": answer,
        "options": options,
        "stem_html": base.html_question(stem),
        "sol_html": base.html_question(solution),
        "opt_html": opt_html,
        "answer_html": base.html_question(answer or ""),
    }


@base.app.post("/api/admin/tex-preview")
def api_tex_preview():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    tex = _fix_latex(_clean_tex(data.get("tex") or data.get("latex") or ""))
    return jsonify(ok=True, html=base.html_question(tex))


@base.app.post("/api/admin/rewrite-question")
def api_rewrite_question():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới viết lại đề/lời giải."), 403
    data = request.get_json(silent=True) or {}
    src = str(data.get("src") or data.get("path") or "").replace("\\", "/").strip()
    try:
        fi = int(data.get("file_idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu file_idx."), 400
    if not src.startswith("ngan-hang/"):
        return jsonify(ok=False, error="File không hợp lệ."), 400
    q, _tex = _load_q(src, fi)
    if not q:
        return jsonify(ok=False, error="Không tìm thấy câu trong file."), 400
    pack = _q_plain_pack(q)
    raw_stem, raw_sol = _raw_parts(q)
    mode = str(data.get("mode") or "ai").strip().lower()
    if mode in {"current", "edit"}:
        return jsonify(
            _pack_payload(
                src,
                fi,
                pack["kind"],
                raw_stem or pack["text"],
                raw_sol or pack["solution"],
                pack.get("answer") or "",
                pack["options"],
                "Sửa trực tiếp — chưa ghi file.",
            )
        )
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error="Thiếu Gemini API key."), 400
    from admin_classify import _gemini_once

    raw, err = _gemini_once(keys, _prompt(pack), 5000)
    if not raw:
        return jsonify(ok=False, error=err or "Gemini không trả lời."), 400
    obj = _extract_ai_fields(raw)
    stem = _clean_tex(obj.get("stem") or "")
    solution = _clean_tex(obj.get("solution") or "")
    answer = _clean_tex(obj.get("answer") or "")
    raw_opts = obj.get("options") if isinstance(obj.get("options"), list) else []
    old_opts = pack["options"]
    new_opts = []
    if raw_opts and len(raw_opts) == len(old_opts):
        for i, o in enumerate(old_opts):
            txt = raw_opts[i]
            txt = txt.get("text") if isinstance(txt, dict) else txt
            new_opts.append({"text": _clean_tex(txt), "correct": bool(o.get("correct"))})
    if not stem and not solution:
        return jsonify(ok=False, error="AI không viết được đề/lời giải."), 400
    if not stem:
        stem = raw_stem or pack["text"]
    if not solution:
        solution = raw_sol or pack["solution"]
    return jsonify(
        _pack_payload(
            src,
            fi,
            pack["kind"],
            stem,
            solution,
            answer or pack.get("answer") or "",
            new_opts,
            str(obj.get("note") or "").strip()[:300],
        )
    )


@base.app.post("/api/admin/rewrite-question-save")
def api_rewrite_question_save():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới ghi đề/lời giải."), 403
    data = request.get_json(silent=True) or {}
    src = str(data.get("src") or "").replace("\\", "/").strip()
    try:
        fi = int(data.get("file_idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu file_idx."), 400
    if not src.startswith("ngan-hang/"):
        return jsonify(ok=False, error="File không hợp lệ."), 400
    flags = {
        "stem": bool(data.get("apply_stem", True)),
        "opts": bool(data.get("apply_opts", True)),
        "sol": bool(data.get("apply_sol", True)),
        "answer": bool(data.get("apply_answer", True)),
    }
    if not any(flags.values()):
        return jsonify(ok=False, error="Chưa chọn phần nào để ghi."), 400
    q, tex = _load_q(src, fi)
    if not q:
        return jsonify(ok=False, error="Không tìm thấy câu trong file."), 400
    inner = None
    for i, m in enumerate(base.EX_RE.finditer(tex)):
        if i == fi:
            inner = m.group(1)
            break
    if inner is None:
        return jsonify(ok=False, error="Không khớp khối \\begin{ex}."), 400
    opts_in = data.get("options") if isinstance(data.get("options"), list) else []
    merged_opts = []
    old = _q_plain_pack(q)["options"]
    if opts_in and len(opts_in) == len(old):
        for i, o in enumerate(old):
            t = opts_in[i]
            t = t.get("text") if isinstance(t, dict) else t
            merged_opts.append({"text": _clean_tex(t), "correct": bool(o.get("correct"))})
    new_inner = _apply_inner(
        inner,
        str(q.get("kind") or "TL"),
        _clean_tex(data.get("stem") or ""),
        _clean_tex(data.get("solution") or ""),
        merged_opts,
        _clean_tex(data.get("answer") or ""),
        flags,
    )
    new_tex = _replace_ex(tex, fi, new_inner)
    if new_tex is None:
        return jsonify(ok=False, error="Không ghi được khối câu."), 400
    try:
        sha, _ = base.read_tex(src, need_sha=True)
        from admin_classify import _write_tex

        _write_tex(src, new_tex, "ADMIN viết lại đề/lời giải " + src, sha)
        try:
            from dang_routes import _STATS_CACHE, _QID_CACHE

            _STATS_CACHE.clear()
            _QID_CACHE.clear()
        except Exception:
            pass
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    return jsonify(ok=True)


REWRITE_CLIENT_JS = r"""
<style>.rwbar{margin:10px 0 0;padding:8px 10px;border:1px dashed #7dd3fc;border-radius:9px;background:#f0f9ff;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.rwout{width:100%}.rwprev{margin-top:8px;padding:10px;border:1px solid #bae6fd;border-radius:9px;background:#fff}.rwprev label{display:flex;gap:8px;align-items:center;font-weight:800;margin:8px 0 4px}.rwta{width:100%;min-height:120px;font:13px/1.45 Consolas,ui-monospace,monospace;padding:8px;border:1px solid #7dd3fc;border-radius:8px;margin:4px 0 8px}.rwta.sm{min-height:72px}.rwlook{margin:8px 0;padding:10px;border:1px dashed #bae6fd;border-radius:8px;background:#f8fbff}</style>
<script>
(function(){
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}
function keys(){return (window.ldvlFilledKeys&&ldvlFilledKeys())||[];}
function dropOf(btn){
  const raw=btn.getAttribute('data-drop')||'';
  const i=raw.lastIndexOf('||');
  if(i<0) return null;
  return {src:raw.slice(0,i), fi:+raw.slice(i+2)};
}
function outBox(btn){
  let box=btn.parentElement&&btn.parentElement.querySelector('.rwout');
  if(!box){box=document.createElement('div');box.className='rwout';btn.parentElement.appendChild(box);}
  return box;
}
function readDraft(box, d){
  const stem=(box.querySelector('[data-ta=stem]')||{}).value;
  const solution=(box.querySelector('[data-ta=sol]')||{}).value;
  const answer=(box.querySelector('[data-ta=ans]')||{}).value;
  const flags={};
  box.querySelectorAll('.rwf').forEach(function(x){flags[x.getAttribute('data-k')]=x.checked});
  const opts=(d.options||[]).map(function(o,i){
    const el=box.querySelector('[data-ta=opt-'+i+']');
    return {text:el?el.value:(o.text||''), correct:!!o.correct};
  });
  return {stem:stem!=null?stem:d.stem, solution:solution!=null?solution:d.solution, answer:answer!=null?answer:d.answer, options:opts, flags:flags};
}
async function previewBox(box){
  const tas=box.querySelectorAll('.rwta');
  const look=box.querySelector('.rwlook');
  if(!look) return;
  look.innerHTML='⏳ Đang xem trước...';
  const parts=[];
  for(const ta of tas){
    const lab=ta.getAttribute('data-lab')||'';
    const r=await fetch('/api/admin/tex-preview',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({tex:ta.value||''})});
    const d=await r.json();
    parts.push('<div class="muted">'+esc(lab)+'</div><div>'+(d.html||'')+'</div>');
  }
  look.innerHTML=parts.join('');
  if(window.ldvlTypeset)ldvlTypeset(look);
}
function showEditor(box, d){
  let h='<div class="rwprev"><div class="success">Chưa ghi file. Sửa LaTeX trong ô, bấm Xem trước, rồi Chấp nhận.</div>';
  if(d.note) h+='<p class="muted">'+esc(d.note)+'</p>';
  h+='<label><input type="checkbox" class="rwf" data-k="stem" checked> Thay đề</label>';
  h+='<textarea class="rwta" data-ta="stem" data-lab="Đề">'+esc(d.stem||'')+'</textarea>';
  (d.options||[]).forEach(function(o,i){
    if(!i) h+='<label><input type="checkbox" class="rwf" data-k="opts" checked> Thay cách diễn đạt phương án (không đổi đáp án đúng)</label>';
    h+='<textarea class="rwta sm" data-ta="opt-'+i+'" data-lab="PA '+(d.kind==='TN'?'ABCD'[i]:(i+1))+'">'+esc(o.text||'')+'</textarea>';
  });
  if(d.kind==='TLN'){
    h+='<label><input type="checkbox" class="rwf" data-k="answer" checked> Thay đáp án TLN</label>';
    h+='<textarea class="rwta sm" data-ta="ans" data-lab="Đáp án">'+esc(d.answer||'')+'</textarea>';
  }
  h+='<label><input type="checkbox" class="rwf" data-k="sol" checked> Thay lời giải</label>';
  h+='<textarea class="rwta" data-ta="sol" data-lab="Lời giải" style="min-height:180px">'+esc(d.solution||'')+'</textarea>';
  h+='<p><button type="button" class="btn rwPrev">👁 Xem trước</button> <button type="button" class="btn green rwSave">✅ Chấp nhận và ghi TEX</button> <button type="button" class="btn rwCancel">Hủy</button></p>';
  h+='<div class="rwlook"></div></div>';
  box.innerHTML=h;
  box.querySelector('.rwCancel').onclick=function(){box.innerHTML='';};
  box.querySelector('.rwPrev').onclick=function(){previewBox(box)};
  box.querySelector('.rwSave').onclick=async function(){
    if(!confirm('Ghi đề/lời giải vào TEX + GitHub?'))return;
    const x=readDraft(box,d);
    const s=await fetch('/api/admin/rewrite-question-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({src:d.src,file_idx:d.file_idx,stem:x.stem,solution:x.solution,answer:x.answer,options:x.options,
        apply_stem:!!x.flags.stem,apply_opts:!!x.flags.opts,apply_sol:!!x.flags.sol,apply_answer:!!x.flags.answer})});
    const sd=await s.json();
    if(!sd.ok){alert(sd.error||'Không ghi được');return;}
    box.innerHTML='<div class="success">✅ Đã ghi. Đang tải lại...</div>';
    location.reload();
  };
  previewBox(box);
}
async function loadRewrite(src, fi, box, mode){
  box.innerHTML=mode==='edit'?'⏳ Đang tải lời giải hiện tại...':'⏳ AI đang viết lại đề và lời giải...';
  try{
    const body={src:src,file_idx:fi,mode:mode||'ai'};
    if(mode!=='edit') body.api_keys=keys();
    if(mode!=='edit'&&!(body.api_keys||[]).length){alert('Nạp key Gemini (trang 🤖 Gemini) rồi thử lại.');box.innerHTML='';return;}
    const r=await fetch('/api/admin/rewrite-question',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    const d=await r.json();
    if(!d.ok){box.innerHTML='<div class="err">'+(d.error||'Lỗi')+'</div>';return;}
    showEditor(box,d);
  }catch(e){box.innerHTML='<div class="err">'+e+'</div>';}
}
window.ldvlAdminRewrite=function(src,fi,box){loadRewrite(src,fi,box,'ai')};
window.ldvlAdminEdit=function(src,fi,box){loadRewrite(src,fi,box,'edit')};
document.addEventListener('click',function(e){
  const go=e.target.closest&&e.target.closest('.rwgo');
  const ed=e.target.closest&&e.target.closest('.rwedit');
  const btn=go||ed;
  if(!btn) return;
  e.preventDefault();
  const p=dropOf(btn);
  if(!p) return;
  loadRewrite(p.src,p.fi,outBox(btn),ed?'edit':'ai');
});
})();
</script>
"""
