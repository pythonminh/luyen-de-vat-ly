# -*- coding: utf-8 -*-
"""Giao diện biên tập từng câu hỏi LaTeX trên GitHub, dễ dùng hơn textarea toàn file."""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from flask import Blueprint, request, redirect, url_for, session, render_template_string

bp = Blueprint("github_question_editor", __name__)
API = "https://api.github.com"


def gh(path: str, method: str = "GET", body=None):
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Chưa có GITHUB_TOKEN trên Render → Environment.")
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "luyen-de-vat-ly-question-editor",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("message", str(e))
        except Exception:
            msg = str(e)
        raise RuntimeError(f"GitHub API {e.code}: {msg}")


def gate():
    if not session.get("mahs"):
        return redirect(url_for("login", next=request.full_path.rstrip("?")))
    try:
        from app import is_admin
        if not is_admin():
            return ("<h3>403 — Chỉ ADMIN được dùng trình biên tập GitHub.</h3>", 403)
    except Exception:
        pass
    return None


def repo():
    return (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").split("/", 1)


def valid_path(path: str) -> bool:
    p = str(path or "").strip("/")
    return p.startswith("ngan-hang/") and p.lower().endswith(".tex") and ".." not in p


def split_tex(text: str):
    """Tách phần đầu + các block ex + phần cuối, giữ nguyên thứ tự và LaTeX."""
    pat = re.compile(r"\\begin\s*\{\s*ex\s*\}(.*?)\\end\s*\{\s*ex\s*\}", re.S | re.I)
    matches = list(pat.finditer(text or ""))
    if not matches:
        return text or "", [], ""
    head = text[: matches[0].start()]
    blocks = [m.group(0) for m in matches]
    tail = text[matches[-1].end() :]
    return head, blocks, tail


def block_meta(block: str, idx: int):
    def grab(pattern):
        m = re.search(pattern, block or "", re.I)
        return (m.group(1) or "").strip() if m else ""
    qid = grab(r"%\s*ID\s*:\s*([^\r\n]+)")
    level = grab(r"%\s*Mức\s*:\s*([^\r\n]+)")
    dangbt = grab(r"\\dangbt\s*\{([^{}]*)\}")
    kind = "Trắc nghiệm"
    if re.search(r"\\choiceTF\b", block):
        kind = "Đúng/Sai"
    elif re.search(r"\\shortans\b", block):
        kind = "Trả lời ngắn"
    elif re.search(r"\\choice\b", block):
        kind = "Trắc nghiệm"
    title = ""
    m = re.search(r"\\begin\s*\{ex\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{ex\})", block, re.S | re.I)
    if m:
        title = re.sub(r"%[^\r\n]*", "", m.group(1))
        title = re.sub(r"\\dangbt\s*\{[^{}]*\}", "", title, flags=re.I)
        title = re.sub(r"\\(?:label|newcommand)\b[^\n]*", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()
    return {"n": idx + 1, "id": qid, "level": level, "dangbt": dangbt, "kind": kind, "title": title[:150]}


CSS = r'''<style>
:root{--blue:#1565c0;--blue2:#e8f1ff;--line:#d7dee8;--text:#18324d;--muted:#64748b;--green:#188038;--red:#c62828;--bg:#f6f8fb}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif}.wrap{max-width:1500px;margin:14px auto;padding:0 14px}.top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.top h1{margin:0;font-size:28px}.path{margin-top:5px;color:var(--muted);font-size:13px;word-break:break-all}.bar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.btn{border:1px solid #c7d2e0;background:#fff;color:#174a84;padding:9px 13px;border-radius:9px;cursor:pointer;font-weight:700}.btn:hover{background:#f1f6ff}.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}.btn.green{background:var(--green);border-color:var(--green);color:#fff}.btn.red{background:#fff5f5;border-color:#ef9a9a;color:var(--red)}.layout{display:grid;grid-template-columns:330px 1fr;gap:12px}.card{background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:0 3px 14px rgba(30,60,90,.06)}.list{padding:10px;max-height:calc(100vh - 210px);overflow:auto}.listhead{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}.search{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:8px}.item{padding:10px;border:1px solid #dbe3ec;border-radius:9px;margin:6px 0;cursor:pointer;background:#fff}.item:hover{background:#f8fbff}.item.active{border-color:#69a5ef;background:#eaf3ff;box-shadow:0 0 0 2px #dcecff}.item .num{font-weight:800;color:#1557a6}.meta{font-size:11px;color:var(--muted);margin-top:4px}.editor{padding:12px}.editorHead{display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px}.badge{display:inline-block;padding:3px 8px;border-radius:999px;background:var(--blue2);color:#1557a6;font-size:11px;font-weight:800;margin-right:4px}.bigTitle{font-size:18px;font-weight:800}.hint{color:var(--muted);font-size:12px;line-height:1.4}.textarea{width:100%;min-height:630px;resize:vertical;padding:12px;border:1px solid #bcc9d8;border-radius:10px;font:13px/1.55 Consolas,Monaco,monospace;background:#fcfdff}.raw{min-height:700px}.status{padding:9px 11px;border-radius:8px;background:#f1f5f9;color:#475569;margin:8px 0;font-size:12px;white-space:pre-wrap}.ok{background:#eaf8ef;color:#166534;border:1px solid #a7d8b5}.err{background:#fff0f0;color:#b91c1c;border:1px solid #efb1b1}.foot{margin-top:8px;font-size:11px;color:var(--muted)}.hidden{display:none!important}@media(max-width:900px){.layout{grid-template-columns:1fr}.list{max-height:320px}.textarea{min-height:520px}}
</style>'''

TPL = CSS + r'''
<div class="wrap">
  <div class="top"><div style="font-size:30px">📝</div><div><h1>Biên tập câu hỏi dễ dùng</h1><div class="path">{{path}}</div></div></div>
  <div class="bar">
    <a class="btn" href="{{back_url}}">← Quản lý GitHub</a>
    <button class="btn" type="button" onclick="selectPrev()">← Câu trước</button>
    <button class="btn" type="button" onclick="selectNext()">Câu sau →</button>
    <button class="btn" type="button" onclick="duplicateCurrent()">⧉ Nhân bản</button>
    <button class="btn red" type="button" onclick="deleteCurrent()">🗑 Xóa câu</button>
    <button class="btn green" type="button" onclick="saveAll()">💾 Lưu GitHub</button>
    <button class="btn" type="button" onclick="toggleRaw()">🔧 Mã toàn file</button>
  </div>
  {% if msg %}<div class="status ok">{{msg}}</div>{% endif %}
  {% if error %}<div class="status err">{{error}}</div>{% endif %}
  <div id="status" class="status">Đã đọc {{blocks|length}} câu. Chọn một câu bên trái để sửa riêng câu đó.</div>
  <div class="layout">
    <div class="card list">
      <div class="listhead"><b>Danh sách câu</b><span id="count">{{blocks|length}}</span></div>
      <input id="search" class="search" placeholder="🔎 Tìm ID, mức độ, nội dung..." oninput="filterList()">
      <div id="items"></div>
    </div>
    <div class="card editor">
      <div id="questionPane">
        <div class="editorHead">
          <div><div id="qtitle" class="bigTitle">Chưa chọn câu</div><div id="qmeta" style="margin-top:5px"></div></div>
          <button class="btn" type="button" onclick="addQuestion()">➕ Thêm câu</button>
        </div>
        <div class="hint">Sửa <b>một câu duy nhất</b> trong ô dưới. Không phải kéo qua hàng nghìn dòng như trình sửa cũ. Hệ thống giữ nguyên LaTeX của các câu khác.</div>
        <textarea id="qeditor" class="textarea" spellcheck="false" placeholder="Chọn câu bên trái..."></textarea>
      </div>
      <div id="rawPane" class="hidden">
        <div class="bigTitle">🔧 Mã LaTeX toàn file</div>
        <div class="hint">Chỉ dùng khi cần chỉnh phần đầu/cuối file hoặc kiểm tra cấu trúc.</div>
        <textarea id="raweditor" class="textarea raw" spellcheck="false"></textarea>
      </div>
      <div class="foot">Lưu = tạo commit trên GitHub. Sau đó GitHub Actions có thể cập nhật chỉ mục ngân hàng.</div>
    </div>
  </div>
</div>
<script>
const HEAD={{head|tojson}}, TAIL={{tail|tojson}};
let blocks={{blocks|tojson}};
let metas=blocks.map((x,i)=>{{n:i+1,id:metaId(x),level:metaLevel(x),dangbt:metaDang(x),kind:metaKind(x),title:metaTitle(x)}});
let current=0, dirty=false;
function metaId(b){{let m=String(b).match(/%\s*ID\s*:\s*([^\r\n]+)/i);return m?m[1].trim():''}}
function metaLevel(b){{let m=String(b).match(/%\s*Mức\s*:\s*([^\r\n]+)/i);return m?m[1].trim():''}}
function metaDang(b){{let m=String(b).match(/\\dangbt\s*\{([^{{}}]*)\}/i);return m?m[1].trim():''}}
function metaKind(b){{if(/\\choiceTF\b/i.test(b))return 'Đúng/Sai';if(/\\shortans\b/i.test(b))return 'Trả lời ngắn';return 'Trắc nghiệm'}}
function metaTitle(b){{let m=String(b).match(/\\begin\s*\{ex\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{ex\})/is);if(!m)return '';let t=m[1].replace(/%[^\r\n]*/g,'').replace(/\\dangbt\s*\{[^{{}}]*\}/ig,'').replace(/\s+/g,' ').trim();return t.slice(0,150)}}
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function renderList(){{let q=document.getElementById('items'),term=(document.getElementById('search').value||'').toLowerCase();q.innerHTML=metas.map((m,i)=>{{let hay=(m.id+' '+m.level+' '+m.dangbt+' '+m.kind+' '+m.title).toLowerCase();if(term&&!hay.includes(term))return '';return `<div class="item ${i===current?'active':''}" data-i="${i}" onclick="selectQ(${i})"><div><span class="num">Câu ${m.n}</span> ${m.id?`<span class="badge">${esc(m.id)}</span>`:''}</div><div style="margin-top:4px">${esc(m.title||'(chưa đọc được nội dung)')}</div><div class="meta">${m.kind}${m.level?' · '+esc(m.level):''}${m.dangbt?' · '+esc(m.dangbt):''}</div></div>`}}).join('') || '<div class="hint">Không tìm thấy câu phù hợp.</div>';document.getElementById('count').textContent=metas.length}}
function selectQ(i){{saveCurrentToArray();current=Math.max(0,Math.min(i,blocks.length-1));let b=blocks[current]||'';document.getElementById('qeditor').value=b;document.getElementById('qtitle').textContent='Câu '+(current+1)+(metaTitle(b)?' · '+metaTitle(b):'');document.getElementById('qmeta').innerHTML='<span class="badge">'+esc(metaKind(b))+'</span>'+(metaLevel(b)?'<span class="badge">'+esc(metaLevel(b))+'</span>':'')+(metaId(b)?'<span class="badge">ID '+esc(metaId(b))+'</span>':'')+(metaDang(b)?'<span class="badge">'+esc(metaDang(b))+'</span>':'');renderList();}}
function saveCurrentToArray(){{if(!blocks.length)return;let el=document.getElementById('qeditor');if(el){{blocks[current]=el.value;metas[current]={{n:current+1,id:metaId(blocks[current]),level:metaLevel(blocks[current]),dangbt:metaDang(blocks[current]),kind:metaKind(blocks[current]),title:metaTitle(blocks[current])}};dirty=true;}}}}
function selectPrev(){{saveCurrentToArray();if(current>0)selectQ(current-1)}}
function selectNext(){{saveCurrentToArray();if(current<blocks.length-1)selectQ(current+1)}}
function addQuestion(){{saveCurrentToArray();blocks.push(`\\begin{{ex}}\n% ID: NEW-${{Date.now()}}\n% Mức: NB\n\nNội dung câu hỏi mới.\n\\choice\n{{\\True Phương án A đúng}}\n{{Phương án B}}\n{{Phương án C}}\n{{Phương án D}}\n\\loigiai{{\n\n}}\n\\end{{ex}}`);current=blocks.length-1;metas=blocks.map((x,i)=>{{n:i+1,id:metaId(x),level:metaLevel(x),dangbt:metaDang(x),kind:metaKind(x),title:metaTitle(x)}});selectQ(current);setStatus('Đã thêm một câu nháp. Sửa nội dung rồi bấm Lưu GitHub.')}}
function duplicateCurrent(){{saveCurrentToArray();if(!blocks.length)return;let cp=blocks[current];cp=cp.replace(/(%\s*ID\s*:\s*)[^\r\n]+/i,'$1NEW-'+Date.now());blocks.splice(current+1,0,cp);metas=blocks.map((x,i)=>{{n:i+1,id:metaId(x),level:metaLevel(x),dangbt:metaDang(x),kind:metaKind(x),title:metaTitle(x)}});current=current+1;selectQ(current);setStatus('Đã nhân bản câu. Hãy sửa ID và nội dung trước khi lưu.')}}
function deleteCurrent(){{saveCurrentToArray();if(blocks.length<=1){{alert('File phải còn ít nhất 1 câu.');return}}if(!confirm('Xóa Câu '+(current+1)+' khỏi file LaTeX?'))return;blocks.splice(current,1);metas=blocks.map((x,i)=>{{n:i+1,id:metaId(x),level:metaLevel(x),dangbt:metaDang(x),kind:metaKind(x),title:metaTitle(x)}});current=Math.min(current,blocks.length-1);selectQ(current);setStatus('Đã xóa câu khỏi bản nháp. Bấm Lưu GitHub để commit.')}}
function filterList(){{renderList()}}
function toggleRaw(){{saveCurrentToArray();let rp=document.getElementById('rawPane');let qp=document.getElementById('questionPane');let show=rp.classList.contains('hidden');if(show){{document.getElementById('raweditor').value=HEAD+blocks.join('\n\n')+TAIL;rp.classList.remove('hidden');qp.classList.add('hidden')}}else{{let raw=document.getElementById('raweditor').value;let m=raw.match(/\\begin\s*\{\s*ex\s*\}/ig);if(m){{let parser=raw.match(/([\s\S]*?)(\\begin\s*\{\s*ex\s*\}[\s\S]*\\end\s*\{\s*ex\s*\})[\s\S]*$/i);if(parser){{let p=splitRaw(raw);if(p){{blocks=p.blocks}}}}}}metas=blocks.map((x,i)=>{{n:i+1,id:metaId(x),level:metaLevel(x),dangbt:metaDang(x),kind:metaKind(x),title:metaTitle(x)}});rp.classList.add('hidden');qp.classList.remove('hidden');current=Math.min(current,blocks.length-1);selectQ(current)}}}}
function splitRaw(raw){{let re=/\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}/ig,ms=[...raw.matchAll(re)];if(!ms.length)return null;return {{head:raw.slice(0,ms[0].index),blocks:ms.map(x=>x[0]),tail:raw.slice(ms[ms.length-1].index+ms[ms.length-1][0].length)}}}}
function setStatus(s,ok=true){{let e=document.getElementById('status');e.textContent=s;e.className='status '+(ok?'ok':'err')}}
async function saveAll(){{saveCurrentToArray();let raw=HEAD+blocks.join('\n\n')+TAIL;let msg=(prompt('Nội dung commit:','ADMIN biên tập câu hỏi '+metas.length+' câu')||'').trim();if(!msg)return;let fd=new FormData();fd.append('branch','main');fd.append('path',{{path|tojson}});fd.append('sha',{{sha|tojson}});fd.append('content',raw);fd.append('message',msg);setStatus('⏳ Đang lưu lên GitHub...',true);try{{let r=await fetch({{save_url|tojson}},{{method:'POST',body:fd,credentials:'same-origin'}});let t=await r.text();document.open();document.write(t);document.close()}}catch(e){{setStatus('❌ '+(e.message||e),false)}}}}
selectQ(0);renderList();
</script>
'''


def fetch_file(path: str, branch: str = "main"):
    owner, name = repo()
    q = f"/repos/{owner}/{name}/contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(branch)}"
    d = gh(q)
    content = base64.b64decode((d.get("content") or "").replace("\n", "")).decode("utf-8", "replace")
    return d, content


@bp.route("/github/questions")
def questions():
    g = gate()
    if g:
        return g
    path = request.args.get("path", "").strip("/")
    branch = request.args.get("branch", "main")
    if not valid_path(path):
        return ("<h3>Chỉ được biên tập file .tex trong ngan-hang/.</h3>", 403)
    try:
        d, content = fetch_file(path, branch)
        head, blocks, tail = split_tex(content)
        msg = request.args.get("msg", "")
        return render_template_string(
            TPL,
            path=path,
            sha=d.get("sha", ""),
            head=head,
            blocks=blocks,
            tail=tail,
            msg=msg,
            error="",
            back_url=url_for("github_source.files", branch=branch, path="/".join(path.split("/")[:-1])),
            save_url=url_for("github_source.save_from_question_editor"),
        )
    except Exception as e:
        return render_template_string(
            TPL,
            path=path,
            sha="",
            head=content if 'content' in locals() else "",
            blocks=[],
            tail="",
            msg="",
            error=str(e),
            back_url=url_for("github_source.files", branch=branch, path="/".join(path.split("/")[:-1])),
            save_url=url_for("github_source.save_from_question_editor"),
        )


@bp.route("/github/questions/save", methods=["POST"])
def save_from_question_editor():
    g = gate()
    if g:
        return g
    owner, name = repo()
    b = request.form.get("branch", "main")
    p = request.form.get("path", "").strip("/")
    posted_sha = request.form.get("sha", "")
    content = request.form.get("content", "")
    message = request.form.get("message") or f"ADMIN biên tập {p}"
    if b != "main":
        return ("<h3>Chỉ lưu ngân hàng chính trên main.</h3>", 400)
    if not valid_path(p):
        return ("<h3>Đường dẫn không hợp lệ.</h3>", 403)
    try:
        base = f"/repos/{owner}/{name}/contents/{urllib.parse.quote(p, safe='/')}"
        old = gh(base + "?ref=" + urllib.parse.quote(b))
        current_sha = old.get("sha", "")
        if posted_sha and posted_sha != current_sha:
            return redirect(url_for("github_question_editor.questions", branch=b, path=p, msg="File đã thay đổi trên GitHub. Hãy tải lại và kiểm tra trước khi lưu."))
        result = gh(
            base,
            "PUT",
            {
                "message": message,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "sha": current_sha,
                "branch": b,
            },
        )
        commit = result.get("commit", {}).get("sha", "")[:12]
        return redirect(url_for("github_question_editor.questions", branch=b, path=p, msg=f"✅ Đã lưu GitHub — commit {commit}"))
    except Exception as e:
        return redirect(url_for("github_question_editor.questions", branch=b, path=p, msg="❌ Lưu thất bại: " + str(e)))
