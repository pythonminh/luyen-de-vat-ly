# -*- coding: utf-8 -*-
"""Giao diện duy nhất cho ngân hàng câu hỏi GitHub.

Nguồn duy nhất: bank_index.json + ngan-hang/*.tex trên GitHub.
Không gọi Google Sheet cho ngân hàng câu hỏi.
"""
from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

from flask import Blueprint, Response, request, redirect, url_for, session
from app import app

bp = Blueprint("github_manager_ui", __name__)
API = "https://api.github.com"
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()


def admin_ok():
    if not session.get("mahs"):
        return False
    try:
        from app import is_admin
        return bool(is_admin())
    except Exception:
        return True


def guard():
    if not session.get("mahs"):
        return redirect(url_for("login", next=request.full_path.rstrip("?")))
    if not admin_ok():
        return Response("<h3>403 — Chỉ ADMIN được dùng quản lý ngân hàng GitHub.</h3>", status=403, mimetype="text/html")
    return None


def gh(path: str, method: str = "GET", payload=None):
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Thiếu GITHUB_TOKEN trên Render.")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "luyen-de-vat-ly-github-bank",
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


def repo_parts():
    if "/" not in REPO:
        raise RuntimeError("GITHUB_REPO phải có dạng owner/repository.")
    return REPO.split("/", 1)


def load_index():
    p = os.path.join(app.root_path, "bank_index.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def valid_path(path: str) -> bool:
    p = (path or "").strip("/")
    return p.startswith("ngan-hang/") and p.lower().endswith(".tex") and ".." not in p


def fetch_tex(path: str):
    owner, repo = repo_parts()
    api = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref=main"
    d = gh(api)
    raw = base64.b64decode((d.get("content") or "").replace("\n", "")).decode("utf-8", "replace")
    return d.get("sha", ""), raw


def save_tex(path: str, content: str, sha: str | None, message: str):
    owner, repo = repo_parts()
    api = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}"
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha
    return gh(api, "PUT", body)


def split_questions(text: str):
    pat = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
    ms = list(pat.finditer(text or ""))
    if not ms:
        return text or "", [], ""
    return text[:ms[0].start()], [m.group(0) for m in ms], text[ms[-1].end():]


def question_meta(block: str, number: int):
    def one(pattern: str):
        m = re.search(pattern, block or "", re.I)
        return m.group(1).strip() if m else ""

    if re.search(r"\\choiceTF\b", block or "", re.I):
        kind = "B"
        label = "Đúng / Sai"
    elif re.search(r"\\shortans\b", block or "", re.I):
        kind = "C"
        label = "Trả lời ngắn"
    elif re.search(r"\\choice\b", block or "", re.I):
        kind = "A"
        label = "Trắc nghiệm"
    else:
        kind = "D"
        label = "Tự luận"

    title = ""
    m = re.search(
        r"\\begin\s*\{\s*ex\s*\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{\s*ex\s*\})",
        block or "",
        re.S | re.I,
    )
    if m:
        title = re.sub(r"%[^\r\n]*", "", m.group(1))
        title = re.sub(r"\\dangbt\s*\{[^{}]*\}", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()

    return {
        "n": number,
        "id": one(r"%\s*ID\s*:\s*([^\r\n]+)"),
        "level": one(r"%\s*Mức\s*:\s*([^\r\n]+)"),
        "dang": one(r"\\dangbt\s*\{([^{}]*)\}"),
        "kind": kind,
        "label": label,
        "title": title[:220] or "(Chưa có tiêu đề)",
    }


def rebuild_meta(block: str, qid: str, level: str, dang: str):
    b = re.sub(r"%\s*ID\s*:[^\r\n]*\r?\n?", "", block, count=1, flags=re.I)
    b = re.sub(r"%\s*Mức\s*:[^\r\n]*\r?\n?", "", b, count=1, flags=re.I)
    b = re.sub(r"\\dangbt\s*\{[^{}]*\}\s*", "", b, count=1, flags=re.I)
    m = re.search(r"(\\begin\s*\{\s*ex\s*\})", b, re.I)
    if not m:
        return b
    lines = []
    if qid:
        lines.append("% ID: " + qid)
    if level:
        lines.append("% Mức: " + level)
    insert = "\n" + "\n".join(lines) + "\n" if lines else "\n"
    b = b[:m.end()] + insert + b[m.end():]
    if dang:
        b = b[:m.start()] + "\\dangbt{" + dang + "}\n" + b[m.start():]
    return b


def h(s):
    return html.escape(str(s or ""), quote=True)


CSS = r"""
<style>
:root{--blue:#1769d2;--blue2:#edf5ff;--ink:#18324d;--muted:#64748b;--line:#d9e3ee;--bg:#f4f7fb;--ok:#16813d;--violet:#6d4bd8;--orange:#e86b18}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}.page{max-width:1500px;margin:18px auto;padding:0 16px 48px}
.header{background:linear-gradient(135deg,#1565c0,#2588df);color:white;border-radius:18px;padding:18px 20px;box-shadow:0 10px 30px #135ca822}.header-row{display:flex;justify-content:space-between;align-items:center;gap:15px}.brand{font-size:23px;font-weight:800}.sub{margin-top:4px;font-size:12px;opacity:.9}.status{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;background:#ffffff1b;border:1px solid #ffffff35;font-weight:700;font-size:12px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.btn{border:1px solid #c8d5e3;background:#fff;color:#174a84;border-radius:9px;padding:9px 12px;font-weight:750;font-size:12px;text-decoration:none;cursor:pointer}.btn:hover{background:#f8fbff}.primary{background:var(--blue);color:#fff;border-color:var(--blue)}.green{background:var(--ok);color:#fff;border-color:var(--ok)}.red{color:#b42318;background:#fff5f5;border-color:#efb3b3}
.card{background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:0 4px 18px #15345c0a}.filters{padding:14px;display:grid;grid-template-columns:1.4fr repeat(5,1fr);gap:9px}.field label{display:block;font-size:11px;font-weight:800;color:#526174;margin-bottom:4px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd6e2;border-radius:9px;background:white;color:var(--ink)}
.layout{display:grid;grid-template-columns:330px 1fr;gap:12px}.panel-title{padding:13px 15px;border-bottom:1px solid #e8edf3;font-weight:800}.tree{padding:10px;max-height:calc(100vh - 270px);overflow:auto}.node{border:1px solid #e2e8ef;border-radius:10px;margin:6px 0;overflow:hidden}.node summary{cursor:pointer;padding:9px;background:#fbfdff;font-size:13px}.child{padding:4px 8px 8px 18px}.lesson{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px;border-radius:8px;color:#21486c;cursor:pointer}.lesson:hover,.lesson.active{background:var(--blue2)}.count{font-size:11px;color:#64748b;white-space:nowrap}
.content{padding:16px}.hero{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.hero h2{margin:0 0 5px;font-size:22px}.crumb{color:var(--muted);font-size:12px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:14px 0}.stat{border:1px solid #e1e7ee;border-radius:10px;padding:11px}.stat b{font-size:19px;display:block}.stat span{font-size:11px;color:var(--muted)}.chips{display:flex;gap:6px;flex-wrap:wrap}.chip{font-size:10px;padding:5px 8px;border-radius:999px;background:#f1f5f9;color:#475569;border:1px solid #e0e6ed}.chip-a{background:#edf4ff;color:#1557a6}.chip-b{background:#f4efff;color:#6542c2}.chip-c{background:#ebfbf4;color:#16804f}.chip-d{background:#fff4ec;color:#b85a0a}
.qrow{border:1px solid #e2e8ef;border-radius:11px;padding:11px;margin:8px 0;display:flex;justify-content:space-between;align-items:center;gap:12px}.qmain{min-width:0}.qtop{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.qtitle{font-weight:800}.qdesc{margin-top:4px;font-size:12px;color:#53657a;line-height:1.45}.qactions{display:flex;gap:6px;flex-wrap:wrap}.empty{padding:50px 20px;text-align:center;color:#738096}
.editor-card{padding:16px}.editor-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.editor-head h2{margin:0;font-size:21px}.meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin:13px 0}.code{width:100%;min-height:560px;padding:13px;border:1px solid #bfcddd;border-radius:11px;background:#fcfdff;font:13px/1.55 Consolas,Monaco,monospace;resize:vertical}.hint{margin-top:8px;padding:10px 12px;border:1px dashed #c3d1df;border-radius:9px;background:#f8fbff;color:#607083;font-size:11px;line-height:1.5}.kind{display:inline-flex;padding:4px 7px;border-radius:999px;font-size:10px;font-weight:800}.ka{background:#eaf2ff;color:#1558a3}.kb{background:#f2edff;color:#6544c5}.kc{background:#e9fbf3;color:#13814d}.kd{background:#fff1e7;color:#ae5a0b}
@media(max-width:1050px){.layout{grid-template-columns:1fr}.tree{max-height:360px}.filters{grid-template-columns:1fr 1fr}.filters .wide{grid-column:1/-1}.stats{grid-template-columns:1fr 1fr}}
</style>
"""


def page_shell(title: str, body: str):
    nav = '<div class="toolbar"><a class="btn" href="/">← Ứng dụng</a><a class="btn" href="/github/quan-ly">📚 Ngân hàng GitHub</a><a class="btn primary" href="/ra-de">📝 Ra đề</a></div>'
    return CSS + f'''<div class="page">
<div class="header"><div class="header-row"><div><div class="brand">🐙 NGÂN HÀNG GITHUB</div><div class="sub">Nguồn chính: GitHub / ngan-hang/*.tex → bank_index.json · Không dùng Google Sheet</div></div><div class="status">✓ GitHub sẵn sàng</div></div></div>
{nav}{body}</div>'''


@bp.get("/github/quan-ly")
def manager():
    g = guard()
    if g:
        return g
    try:
        data = load_index()
        lessons = data.get("lessons", []) if isinstance(data, dict) else []
    except Exception as e:
        return page_shell("Lỗi", f'<div class="card" style="padding:20px;color:#b42318"><b>Không đọc được bank_index.json:</b> {h(e)}</div>')

    payload = json.dumps(lessons, ensure_ascii=False).replace("</", "<\\/")
    body = r'''<div class="card"><div class="filters">
<div class="field wide"><label>🔎 Tìm kiếm</label><input id="q" placeholder="Tìm bài, dạng bài, tên file..." oninput="render()"></div>
<div class="field"><label>Môn</label><select id="mon" onchange="render()"></select></div>
<div class="field"><label>Lớp</label><select id="lop" onchange="render()"></select></div>
<div class="field"><label>Chương</label><select id="chuong" onchange="render()"></select></div>
<div class="field"><label>Bài</label><select id="bai" onchange="render()"></select></div>
<div class="field"><label>Dạng bài</label><select id="dang" onchange="render()"></select></div>
</div></div>
<div class="layout" style="margin-top:12px">
<div class="card"><div class="panel-title">📚 MỤC LỤC ĐỀ</div><div id="tree" class="tree"></div></div>
<div class="card"><div id="content" class="content"><div class="empty">Chọn một Bài trong mục lục.</div></div></div>
</div>
<script>
const LESSONS=__LESSONS__;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let S={mon:'',lop:'',chuong:'',bai:'',dang:''};
function uniq(a){return [...new Set(a.filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b),'vi'))}
function fill(id,values,value,label){const e=document.getElementById(id);e.innerHTML='<option value="">'+label+'</option>'+uniq(values).map(v=>'<option value="'+esc(v)+'" '+(v===value?'selected':'')+'>'+esc(v)+'</option>').join('')}
function filtered(){const t=(document.getElementById('q').value||'').toLowerCase();return LESSONS.filter(x=>{const ok=(!S.mon||x.Mon===S.mon)&&(!S.lop||x.Lop===S.lop)&&(!S.chuong||x.Chuong===S.chuong)&&(!S.bai||x.BaiHoc===S.bai)&&(!S.dang||Object.keys(x.dang||{}).includes(S.dang));const text=(x.Mon+' '+x.Lop+' '+x.Chuong+' '+x.BaiHoc+' '+x.De+' '+x.file+' '+Object.keys(x.dang||{}).join(' ')).toLowerCase();return ok&&(!t||text.includes(t))})}
function render(){
 let m=LESSONS.filter(x=>!S.mon||x.Mon===S.mon);fill('mon',LESSONS.map(x=>x.Mon),S.mon,'Tất cả');fill('lop',m.map(x=>x.Lop),S.lop,'Tất cả');let c=m.filter(x=>!S.lop||x.Lop===S.lop);fill('chuong',c.map(x=>x.Chuong),S.chuong,'Tất cả');let b=c.filter(x=>!S.chuong||x.Chuong===S.chuong);fill('bai',b.map(x=>x.BaiHoc),S.bai,'Tất cả');let d=b.filter(x=>!S.bai||x.BaiHoc===S.bai),ds=[];d.forEach(x=>Object.keys(x.dang||{}).forEach(k=>ds.push(k)));fill('dang',ds,S.dang,'Tất cả');
 const list=filtered();renderTree(list);renderDetail(list)
}
function renderTree(list){let g={};list.forEach(x=>{const m=x.Mon||'Khác',l=x.Lop||'?',c=x.Chuong||'Chưa phân chương';g[m]??={};g[m][l]??={};g[m][l][c]??=[];g[m][l][c].push(x)});let h='';Object.keys(g).sort().forEach(m=>{h+='<details class="node" open><summary><b>'+esc(m)+'</b></summary><div class="child">';Object.keys(g[m]).sort().forEach(l=>{h+='<details class="node" open><summary>Lớp '+esc(l)+'</summary><div class="child">';Object.keys(g[m][l]).sort().forEach(c=>{h+='<details class="node" open><summary>'+esc(c)+'</summary><div class="child">';g[m][l][c].sort((a,b)=>(a.BaiHoc||'').localeCompare(b.BaiHoc||'','vi')).forEach(x=>{const p=x.path||x.file||'';h+='<div class="lesson" onclick="openLesson('+JSON.stringify(p)+')"><span>'+esc(x.BaiHoc||x.De||x.file)+'</span><span class="count">'+Number(x.questions||x.count||0)+' câu</span></div>'});h+='</div></details>'});h+='</div></details>'});h+='</div></details>'});document.getElementById('tree').innerHTML=h||'<div class="empty">Không có dữ liệu.</div>'}
function openLesson(path){window.location.href='/github/questions?path='+encodeURIComponent(path)+'&n=1'}
function renderDetail(list){const total=list.reduce((s,x)=>s+Number(x.questions||x.count||0),0);let h='<div class="hero"><div><h2>Ngân hàng câu hỏi</h2><div class="crumb">GitHub · '+list.length+' file · '+total+' câu</div></div></div>';h+='<div class="stats"><div class="stat"><b>'+list.length+'</b><span>file</span></div><div class="stat"><b>'+total+'</b><span>câu hỏi</span></div><div class="stat"><b>'+new Set(list.map(x=>x.Chuong)).size+'</b><span>chương</span></div><div class="stat"><b>GitHub</b><span>nguồn chính</span></div></div>';list.forEach(x=>{const p=x.path||x.file||'',d=Object.entries(x.dang||{});h+='<div class="qrow"><div class="qmain"><div class="qtop"><div class="qtitle">'+esc(x.BaiHoc||x.De||x.file)+'</div><span class="chip">'+Number(x.questions||x.count||0)+' câu</span></div><div class="qdesc">'+esc(p)+'</div><div class="chips">'+d.slice(0,6).map(([k,v])=>'<span class="chip">'+esc(k)+' · '+v+'</span>').join('')+(d.length>6?'<span class="chip">+'+(d.length-6)+' dạng</span>':'')+'</div></div><div class="qactions"><a class="btn primary" href="/github/questions?path='+encodeURIComponent(p)+'&n=1">✏️ Mở bài</a></div></div>'});document.getElementById('content').innerHTML=h}
render();
</script>'''.replace("__LESSONS__", payload)
    return page_shell("Ngân hàng GitHub", body)


@bp.route("/github/questions", methods=["GET", "POST"])
def questions():
    g = guard()
    if g:
        return g
    path = (request.values.get("path") or "").strip("/")
    if not valid_path(path):
        return page_shell("Lỗi", '<div class="card" style="padding:20px;color:#b42318"><b>Đường dẫn file ngân hàng không hợp lệ.</b></div>')

    try:
        sha, full = fetch_tex(path)
        head, blocks, tail = split_questions(full)
        if not blocks:
            return page_shell("Lỗi", '<div class="card" style="padding:20px;color:#b42318"><b>File không có block \\begin{ex}...\\end{ex}.</b></div>')
        n = max(1, min(int(request.values.get("n", "1")), len(blocks)))

        if request.method == "POST":
            idx = n - 1
            edited = request.form.get("content", blocks[idx])
            edited = rebuild_meta(edited, request.form.get("qid", "").strip(), request.form.get("level", "").strip(), request.form.get("dang", "").strip())
            blocks[idx] = edited
            content = head + "\n\n".join(blocks) + tail
            old_sha = sha
            if request.form.get("sha") and request.form.get("sha") != old_sha:
                return redirect(url_for("github_manager_ui.questions", path=path, n=n, error="File trên GitHub đã thay đổi. Hãy tải lại trước khi lưu."))
            result = save_tex(path, content, old_sha, f"Sửa Câu {n}: {path}")
            commit = (result.get("commit") or {}).get("sha", "")[:10]
            return redirect(url_for("github_manager_ui.questions", path=path, n=n, msg=f"Đã lưu Câu {n} lên GitHub · {commit}"))

        qs = [question_meta(b, i+1) for i,b in enumerate(blocks)]
        curm = qs[n-1]
        sidebar=''.join(f'<a class="qrow" style="display:block;text-decoration:none;color:inherit" href="{url_for("github_manager_ui.questions",path=path,n=q["n"])}"><div class="qtop"><span class="kind {("ka" if q["kind"]=="A" else "kb" if q["kind"]=="B" else "kc" if q["kind"]=="C" else "kd")}">{q["kind"]} · {h(q["label"])}</span><b>Câu {q["n"]}</b></div><div class="qdesc">{h(q["title"])}</div></a>' for q in qs)
        level_options=''.join(f'<option value="{x}" {"selected" if curm["level"]==x else ""}>{x}</option>' for x in ["NB","TH","VD","VDC"])
        body=f'''<div class="layout"><div class="card"><div class="panel-title">📋 Câu hỏi <span style="color:#64748b;font-size:11px">({len(qs)} câu)</span></div><div class="tree">{sidebar}</div></div><div class="card editor-card"><div class="editor-head"><div><h2>Câu {n}</h2><div class="crumb">{h(path)}</div></div><div class="chips"><span class="kind {('ka' if curm['kind']=='A' else 'kb' if curm['kind']=='B' else 'kc' if curm['kind']=='C' else 'kd')}">{curm['kind']} · {h(curm['label'])}</span></div></div>'''
        if request.args.get("msg"):
            body += f'<div class="hint" style="background:#ecfdf3;border-color:#b7dec5;color:#166534">✅ {h(request.args.get("msg"))}</div>'
        if request.args.get("error"):
            body += f'<div class="hint" style="background:#fff3f3;border-color:#efb1b1;color:#b42318">⚠️ {h(request.args.get("error"))}</div>'
        body += f'''<form method="post"><input type="hidden" name="sha" value="{h(sha)}"><div class="meta-grid"><div class="field"><label>Loại câu</label><input value="{curm['kind']} — {h(curm['label'])}" disabled></div><div class="field"><label>Mức độ</label><select name="level"><option value="">— Chưa chọn —</option>{level_options}</select></div><div class="field"><label>ID câu</label><input name="qid" value="{h(curm['id'])}" placeholder="T10C1..." ></div><div class="field"><label>Dạng bài</label><input name="dang" value="{h(curm['dang'])}" placeholder="Nhập tên dạng bài"></div></div><div class="field"><label>Mã LaTeX của Câu {n}</label><textarea class="code" name="content" spellcheck="false">{h(blocks[n-1])}</textarea></div><div class="hint">🖼 Hình/TikZ nằm trong chính mã LaTeX của câu sẽ được giữ nguyên khi lưu. Có thể sửa trực tiếp rồi bấm <b>Lưu GitHub</b>.</div><div class="toolbar"><button class="btn green" type="submit">💾 Lưu GitHub</button><a class="btn" href="{url_for('github_manager_ui.questions',path=path,n=max(1,n-1))}">← Câu trước</a><a class="btn" href="{url_for('github_manager_ui.questions',path=path,n=min(len(qs),n+1))}">Câu sau →</a><a class="btn" href="{url_for('github_manager_ui.manager')}">📚 Mục lục</a></div></form></div></div>'''
        return page_shell("Sửa câu", body)
    except Exception as e:
        return page_shell("Lỗi", f'<div class="card" style="padding:20px;color:#b42318"><b>Không mở được file:</b><pre style="white-space:pre-wrap">{h(e)}</pre></div>')


# Backward-compatible route name used by a few old links.
@bp.get("/github/open")
def open_file():
    return redirect(url_for("github_manager_ui.questions", path=request.args.get("path", ""), n=request.args.get("n", "1")))


# wsgi.py registers this blueprint once.
