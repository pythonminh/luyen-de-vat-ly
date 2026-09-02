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


def _parse_obj(text):
    s = str(text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    if m:
        s = m.group(1).strip()
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b <= a:
        return {}
    data = json.loads(s[a : b + 1])
    return data if isinstance(data, dict) else {}


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
    return t.strip()


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
        "Bạn là giáo viên THPT soạn đề. Hãy VIẾT LẠI ĐỀ và LỜI GIẢI cho đúng, gọn, "
        "giọng giáo viên trên lớp (mạch lạc, không sáo).\n"
        "Giữ nguyên dữ kiện số liệu, loại câu, đáp án đúng (vị trí A–D / Đúng-Sai không được đổi). "
        "Tính lại cho khớp đáp án. Nếu lời giải cũ mâu thuẫn đáp án, lấy vật lý đúng và ghi note.\n"
        "Công thức LaTeX trong $...$. Không bọc \\begin{ex}. Không đổi ID.\n"
        "JSON đúng một object:\n"
        '{"stem":"đề (LaTeX)","options":["pa1","pa2",...],'
        '"answer":"nếu TLN thì đáp án shortans","solution":"lời giải LaTeX","note":""}\n'
        "options cùng số lượng; không ghi \\True. solution là nội dung \\loigiai, không lệnh \\loigiai.\n\n"
        f"Loại: {pack['kind']} · ID: {pack['id']}\n"
        f"Đề cũ:\n{pack['text']}\n"
        + ("Phương án/mệnh đề cũ:\n" + "\n".join(opt_lines) + "\n" if opt_lines else "")
        + (f"Đáp án shortans cũ: {pack['answer']}\n" if pack.get("answer") else "")
        + f"Lời giải cũ:\n{pack['solution'] or '(trống)'}\n"
    )


@base.app.post("/api/admin/rewrite-question")
def api_rewrite_question():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới viết lại đề/lời giải."), 403
    data = request.get_json(silent=True) or {}
    src = str(data.get("src") or data.get("path") or "").replace("\\", "/").strip()
    keys = _keys_from_payload(data)
    try:
        fi = int(data.get("file_idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu file_idx."), 400
    if not src.startswith("ngan-hang/") or not keys:
        return jsonify(ok=False, error="Thiếu file TEX hoặc Gemini API key."), 400
    q, _tex = _load_q(src, fi)
    if not q:
        return jsonify(ok=False, error="Không tìm thấy câu trong file."), 400
    pack = _q_plain_pack(q)
    from admin_classify import _gemini_once

    raw, err = _gemini_once(keys, _prompt(pack), 5000)
    if not raw:
        return jsonify(ok=False, error=err or "Gemini không trả lời."), 400
    try:
        obj = _parse_obj(raw)
    except Exception as e:
        return jsonify(ok=False, error="AI không trả JSON hợp lệ: " + str(e)), 400
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
    opt_html = ""
    if new_opts and pack["kind"] == "TN":
        bits = []
        for i, o in enumerate(new_opts[:4]):
            mark = " <span class='okmark'>Đáp án đúng</span>" if o.get("correct") else ""
            bits.append(
                f"<div class='opt{' ok' if o.get('correct') else ''}'><b>{'ABCD'[i]}.</b> {base.html_question(o.get('text',''))}{mark}</div>"
            )
        opt_html = "<div class='opts'>" + "".join(bits) + "</div>"
    elif new_opts and pack["kind"] == "DS":
        bits = []
        for i, o in enumerate(new_opts):
            yes = bool(o.get("correct"))
            mark = f" <span class='okmark'>{'Đúng' if yes else 'Sai'}</span>"
            bits.append(
                f"<div class='tf{' ok' if yes else ' noans'}'><b>{i+1}.</b> {base.html_question(o.get('text',''))}{mark}</div>"
            )
        opt_html = "<div class='tfgrid'>" + "".join(bits) + "</div>"
    return jsonify(
        ok=True,
        src=src,
        file_idx=fi,
        kind=pack["kind"],
        note=str(obj.get("note") or "").strip()[:300],
        stem=stem,
        solution=solution,
        answer=answer or pack.get("answer") or "",
        options=new_opts,
        stem_html=base.html_question(stem or pack["text"]),
        sol_html=base.html_question(solution or pack["solution"]),
        opt_html=opt_html,
        answer_html=base.html_question(answer or pack.get("answer") or ""),
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
<style>.rwbar{margin:10px 0 0;padding:8px 10px;border:1px dashed #7dd3fc;border-radius:9px;background:#f0f9ff;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.rwout{width:100%}.rwprev{margin-top:8px;padding:10px;border:1px solid #bae6fd;border-radius:9px;background:#fff}.rwprev label{display:flex;gap:8px;align-items:center;font-weight:800;margin:8px 0 4px}</style>
<script>
(function(){
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}
function keys(){return (window.ldvlFilledKeys&&ldvlFilledKeys())||[];}
async function runRewrite(src, fi, box){
  const k=keys();
  if(!k.length){alert('Nạp key Gemini (trang 🤖 Gemini) rồi thử lại.');return;}
  box.innerHTML='⏳ AI đang viết lại đề và lời giải...';
  try{
    const r=await fetch('/api/admin/rewrite-question',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({src:src,file_idx:fi,api_keys:k})});
    const d=await r.json();
    if(!d.ok){box.innerHTML='<div class="err">'+(d.error||'Lỗi AI')+'</div>';return;}
    window.__rwDraft=d;
    let h='<div class="rwprev"><div class="success">Bản AI — chưa ghi file. Bỏ tick phần không muốn thay.</div>';
    if(d.note) h+='<p class="muted">'+esc(d.note)+'</p>';
    h+='<label><input type="checkbox" class="rwf" data-k="stem" checked> Thay đề</label>';
    h+='<div class="qtext">'+d.stem_html+'</div>';
    if(d.opt_html){h+='<label><input type="checkbox" class="rwf" data-k="opts" checked> Thay cách diễn đạt phương án (không đổi đáp án đúng)</label>'+d.opt_html;}
    if(d.kind==='TLN'&&d.answer){h+='<label><input type="checkbox" class="rwf" data-k="answer" checked> Thay đáp án TLN</label><div class="answerline"><b>Đáp án:</b> '+d.answer_html+'</div>';}
    h+='<label><input type="checkbox" class="rwf" data-k="sol" checked> Thay lời giải</label>';
    h+='<div class="solution"><b>📖 Lời giải mới</b><div>'+d.sol_html+'</div></div>';
    h+='<p><button type="button" class="btn green" id="rwAccept">✅ Chấp nhận và ghi TEX</button> <button type="button" class="btn" id="rwCancel">Hủy</button></p></div>';
    box.innerHTML=h;
    if(window.ldvlTypeset)ldvlTypeset(box);
    document.getElementById('rwCancel').onclick=function(){box.innerHTML='';};
    document.getElementById('rwAccept').onclick=async function(){
      if(!confirm('Ghi đề/lời giải mới vào TEX + GitHub? Bản cũ sẽ bị thay.'))return;
      const flags={};
      box.querySelectorAll('.rwf').forEach(function(x){flags[x.getAttribute('data-k')]=x.checked});
      const s=await fetch('/api/admin/rewrite-question-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({src:d.src,file_idx:d.file_idx,stem:d.stem,solution:d.solution,answer:d.answer,options:d.options||[],
          apply_stem:!!flags.stem,apply_opts:!!flags.opts,apply_sol:!!flags.sol,apply_answer:!!flags.answer})});
      const sd=await s.json();
      if(!sd.ok){alert(sd.error||'Không ghi được');return;}
      box.innerHTML='<div class="success">✅ Đã ghi. Đang tải lại...</div>';
      location.reload();
    };
  }catch(e){box.innerHTML='<div class="err">'+e+'</div>';}
}
window.ldvlAdminRewrite=runRewrite;
document.addEventListener('click',function(e){
  const btn=e.target.closest&&e.target.closest('.rwgo');
  if(!btn) return;
  e.preventDefault();
  const raw=btn.getAttribute('data-drop')||'';
  const i=raw.lastIndexOf('||');
  if(i<0) return;
  const src=raw.slice(0,i), fi=+raw.slice(i+2);
  let box=btn.parentElement&&btn.parentElement.querySelector('.rwout');
  if(!box){box=document.createElement('div');box.className='rwout';btn.parentElement.appendChild(box);}
  runRewrite(src,fi,box);
});
})();
</script>
"""
