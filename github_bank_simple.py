# -*- coding: utf-8 -*-
"""Ngân hàng GitHub — giao diện mới, đơn giản và nhanh.

Nguồn chính duy nhất cho ngân hàng: bank_index.json + ngan-hang/**/*.tex trên GitHub.
- Mục lục: đọc bank_index.json tại máy Render (rất nhanh).
- Mở bài: chỉ tải đúng file .tex cần xem.
- Dạng bài/A-B-C-D: đọc trực tiếp từ .tex khi mở bài.
- Sửa/lưu: commit trực tiếp file .tex lên GitHub.
- Google Sheet: không được gọi ở module này.
"""
from __future__ import annotations

import base64
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from flask import Blueprint, Response, jsonify, request, session
from app import app

bp = Blueprint("github_bank_simple", __name__)

REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = (os.getenv("GITHUB_BRANCH") or "main").strip() or "main"
TOKEN = (os.getenv("GITHUB_TOKEN") or "").strip()
RAW = "https://raw.githubusercontent.com"
API = "https://api.github.com"
INDEX_PATH = "bank_index.json"

_INDEX_CACHE = {"time": 0.0, "data": None}
_INDEX_TTL = 120

TYPE_LABEL = {"A": "Trắc nghiệm", "B": "Đúng / Sai", "C": "Trả lời ngắn", "D": "Tự luận"}


def _repo():
    if "/" not in REPO:
        raise RuntimeError("GITHUB_REPO phải có dạng owner/repository")
    return REPO.split("/", 1)


def _clean(v):
    return str(v or "").strip()


def _esc(v):
    return html.escape(str(v or ""), quote=True)


def _raw(path):
    owner, repo = _repo()
    url = f"{RAW}/{owner}/{repo}/{urllib.parse.quote(BRANCH)}/{urllib.parse.quote(path, safe='/')}"
    req = urllib.request.Request(url, headers={"User-Agent": "ldvl-github-bank"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.read().decode("utf-8", "replace")


def _gh(path, method="GET", payload=None):
    if not TOKEN:
        raise RuntimeError("Render chưa có GITHUB_TOKEN")
    owner, repo = _repo()
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ldvl-github-bank",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8"))
            msg = j.get("message", str(e))
        except Exception:
            msg = str(e)
        raise RuntimeError(f"GitHub API {e.code}: {msg}")


def _index():
    now = time.time()
    if _INDEX_CACHE["data"] is not None and now - _INDEX_CACHE["time"] < _INDEX_TTL:
        return _INDEX_CACHE["data"]
    data = json.loads(_raw(INDEX_PATH))
    _INDEX_CACHE["data"] = data
    _INDEX_CACHE["time"] = now
    return data


def _valid(path):
    return path.startswith("ngan-hang/") and path.lower().endswith(".tex") and ".." not in path


def _fetch_tex(path):
    if not _valid(path):
        raise RuntimeError("Đường dẫn .tex không hợp lệ")
    owner, repo = _repo()
    url = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(BRANCH)}"
    obj = _gh(url)
    raw = (obj.get("content") or "").replace("\n", "")
    return obj.get("sha", ""), base64.b64decode(raw).decode("utf-8", "replace")


def _save_tex(path, text, sha, message):
    if not _valid(path):
        raise RuntimeError("Đường dẫn .tex không hợp lệ")
    owner, repo = _repo()
    url = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}"
    payload = {
        "message": message or "Cập nhật ngân hàng .tex",
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": sha,
    }
    return _gh(url, "PUT", payload)


def _question_blocks(text):
    pat = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
    matches = list(pat.finditer(text or ""))
    out = []
    for i, m in enumerate(matches, 1):
        block = m.group(0)
        # Dạng bài thường nằm ngay trước \begin{ex}; lấy lệnh \dangbt cuối cùng trước câu.
        before = text[:m.start()]
        db = list(re.finditer(r"\\dangbt\s*\{([^{}]*)\}", before, re.I))
        dang = _clean(db[-1].group(1)) if db else "Chưa phân dạng"
        if not dang or dang.casefold() in {"chưa có dạng", "chua co dang", "chưa phân dạng", "chua phan dang"}:
            dang = "Chưa phân dạng"
        kind = "D"
        if re.search(r"\\choiceTF\b", block, re.I):
            kind = "B"
        elif re.search(r"\\shortans\b", block, re.I):
            kind = "C"
        elif re.search(r"\\choice\b", block, re.I):
            kind = "A"
        mid = re.search(r"%\s*Mức\s*:\s*([^\r\n%]+)", block, re.I)
        level = _clean(mid.group(1)).upper() if mid else ""
        iq = re.search(r"%\s*ID\s*:\s*([^\r\n%]+)", block, re.I)
        qid = _clean(iq.group(1)) if iq else ""
        tm = re.search(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{\s*ex\s*\})", block, re.I)
        title = tm.group(1) if tm else ""
        title = re.sub(r"%[^\r\n]*", "", title)
        title = re.sub(r"\\dangbt\s*\{[^{}]*\}", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()
        out.append({
            "no": i,
            "id": qid,
            "level": level,
            "dang": dang,
            "kind": kind,
            "kind_label": TYPE_LABEL[kind],
            "title": title[:320] or "(Chưa đọc được nội dung)",
            "text": block,
            "has_image": bool(re.search(r"\\begin\s*\{\s*tikzpicture\s*\}|\\includegraphics", block, re.I)),
        })
    return out


def _detail(path):
    sha, text = _fetch_tex(path)
    qs = _question_blocks(text)
    type_counts = OrderedDict((k, 0) for k in "ABCD")
    dang_counts = {}
    for q in qs:
        type_counts[q["kind"]] += 1
        d = q["dang"]
        item = dang_counts.setdefault(d, {"total": 0, "A": 0, "B": 0, "C": 0, "D": 0})
        item["total"] += 1
        item[q["kind"]] += 1
    return {"sha": sha, "text": text, "questions": qs, "types": type_counts, "dang": dang_counts}


def _catalog():
    idx = _index()
    rows = []
    for x in idx.get("lessons") or []:
        path = _clean(x.get("github") or x.get("path") or x.get("file"))
        if not path:
            continue
        rows.append({
            "mon": _clean(x.get("Mon")),
            "lop": _clean(x.get("Lop")),
            "chuong": _clean(x.get("Chuong")),
            "bai": _clean(x.get("BaiHoc") or x.get("De")),
            "path": path,
            "count": int(x.get("count_questions") or x.get("questions") or x.get("count") or 0),
        })
    return idx, rows


@bp.get("/github/quan-ly")
def github_page():
    return Response(PAGE_HTML, mimetype="text/html")


@bp.get("/github/api/catalog-simple")
def api_catalog():
    try:
        idx, rows = _catalog()
        return jsonify({
            "ok": True,
            "source": "GitHub",
            "total_files": int(idx.get("total_files") or idx.get("count") or len(rows)),
            "total_questions": int(idx.get("total_questions") or sum(x["count"] for x in rows)),
            "lessons": rows,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc), "lessons": []}), 500


@bp.get("/github/api/tex")
def api_tex():
    path = _clean(request.args.get("path"))
    if not path:
        return jsonify({"ok": False, "error": "Thiếu path"}), 400
    try:
        return jsonify({"ok": True, "path": path, **_detail(path)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.post("/github/api/save-tex")
def api_save_tex():
    data = request.get_json(silent=True) or {}
    path = _clean(data.get("path"))
    text = data.get("text")
    sha = _clean(data.get("sha"))
    message = _clean(data.get("message"))
    if not path or not isinstance(text, str) or not sha:
        return jsonify({"ok": False, "error": "Thiếu path/text/sha"}), 400
    # Cho phép xem rộng, nhưng chỉ tài khoản ADMIN mới được ghi GitHub.
    try:
        from app import is_admin
        if not is_admin():
            return jsonify({"ok": False, "error": "Chỉ ADMIN được lưu file .tex."}), 403
    except Exception:
        if not session.get("mahs"):
            return jsonify({"ok": False, "error": "Chưa đăng nhập ADMIN."}), 403
    try:
        result = _save_tex(path, text, sha, message)
        _INDEX_CACHE["time"] = 0
        return jsonify({
            "ok": True,
            "commit": ((result.get("commit") or {}).get("sha") or ""),
            "content_sha": ((result.get("content") or {}).get("sha") or ""),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 409


PAGE_HTML = r'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ngân hàng GitHub</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font-family:Segoe UI,Arial,sans-serif}button,input,select,textarea{font:inherit}
.top{background:linear-gradient(90deg,#1769d2,#2b8be0);color:#fff;position:sticky;top:0;z-index:20;box-shadow:0 3px 12px #154c8a35}.topin{max-width:1500px;margin:auto;padding:10px 14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}.brand{font-weight:950;font-size:19px}.sub{font-size:10px;opacity:.9}.nav{display:flex;gap:6px;margin-left:8px}.nav button{border:1px solid #ffffff55;background:#ffffff15;color:#fff;border-radius:11px;padding:7px 12px;font-weight:900;cursor:pointer}.nav button.on{background:#fff;color:#1558a6}.topstat{margin-left:auto;font-size:11px;font-weight:850}.wrap{max-width:1500px;margin:auto;padding:12px}.source{display:flex;justify-content:space-between;gap:8px;align-items:center;background:#eaf3ff;border:1px solid #c9def7;border-radius:12px;padding:8px 11px;color:#1b4e83;font-size:12px}.source b{color:#166534}.toolbar{display:flex;gap:6px;flex-wrap:wrap;margin:9px 0}.btn{border:1px solid #cbd5e1;background:#fff;color:#174a84;border-radius:9px;padding:7px 10px;font-size:11px;font-weight:850;cursor:pointer}.btn.primary{background:#1769d2;border-color:#1769d2;color:#fff}.btn.green{background:#eaf8ef;border-color:#86efac;color:#166534}.layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:10px;align-items:start}.card{background:#fff;border:1px solid #d8e2ec;border-radius:14px;box-shadow:0 2px 9px #18324b0b}.sideHead,.mainHead{padding:10px 12px;border-bottom:1px solid #e1e8ef;background:#f8fbff;font-weight:950}.side{position:sticky;top:78px;max-height:calc(100vh - 92px);overflow:hidden}.filters{padding:9px}.field{margin-bottom:7px}.field label{display:block;font-size:10px;font-weight:900;color:#64748b;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;color:#17324d}.tree{border-top:1px solid #e5eaf0;max-height:calc(100vh - 280px);overflow:auto;padding:7px}.tree details{margin:2px 0}.tree summary{cursor:pointer;padding:5px 4px;border-radius:6px;font-size:11px;font-weight:850}.tree summary:hover{background:#eef6ff}.tree .node{padding:4px 9px;color:#315b83;font-size:10.5px;cursor:pointer;border-radius:6px}.tree .node:hover,.tree .node.sel{background:#eaf3ff;color:#1458a5;font-weight:900}.mainHead{display:flex;justify-content:space-between;gap:8px;align-items:center}.stats{display:flex;gap:5px;flex-wrap:wrap}.stat{border:1px solid #bfdbfe;border-radius:999px;padding:4px 7px;background:#fff;color:#1d4ed8;font-size:10px;font-weight:900}.books{padding:9px}.subject{margin-bottom:12px}.subjectHead{padding:9px 11px;border-radius:11px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:950}.grade{margin-top:8px;border:1px solid #d2dbe4;border-radius:11px;overflow:hidden}.gradeHead{padding:8px 10px;background:#f1f5f9;font-weight:950;font-size:11px}.chapter{margin:8px;border:1px solid #bfd9f5;border-radius:10px;overflow:hidden;background:#f8fbff}.chapterHead{padding:8px 9px;background:#dbeafe;color:#1e3a8a;font-size:11px;font-weight:950}.lessons{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:8px;padding:8px}.lesson{border:1px solid #dfe7ef;border-radius:11px;background:#fff;padding:9px}.lessonTitle{font-size:12px;font-weight:950;line-height:1.35}.muted{color:#64748b;font-size:10px}.chips{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0}.chip{border:1px solid #d7e0e8;border-radius:999px;padding:3px 6px;background:#f8fafc;color:#475569;font-size:9px;font-weight:900}.chipA{background:#eff6ff;color:#1d4ed8;border-color:#93c5fd}.chipB{background:#f5f3ff;color:#6d28d9;border-color:#c4b5fd}.chipC{background:#ecfdf5;color:#15803d;border-color:#86efac}.chipD{background:#fff7ed;color:#c2410c;border-color:#fdba74}.dbt{margin-top:5px;border:1px solid #d5e5f6;border-radius:9px;background:#f8fbff;padding:6px}.dbtHead{font-size:10px;font-weight:950;color:#1e3a8a;margin-bottom:4px}.dbtrow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px;align-items:center;border:1px solid #dbeafe;background:#fff;border-radius:7px;padding:5px 6px;margin:3px 0;cursor:pointer}.dbtrow:hover{background:#eff6ff;border-color:#60a5fa}.dbtname{font-size:9.5px;font-weight:850;line-height:1.3}.dbtmeta{display:flex;gap:3px;justify-content:flex-end;flex-wrap:wrap}.mini{border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:7px;padding:4px 7px;font-size:9.5px;font-weight:900;cursor:pointer}.empty{padding:32px;text-align:center;color:#64748b}.editorTop{display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px}.qgrid{display:grid;grid-template-columns:300px minmax(0,1fr);gap:9px}.qside{max-height:calc(100vh - 170px);overflow:auto}.qitem{border:1px solid #e0e7ef;border-radius:9px;padding:7px;margin:4px 0;background:#fff;cursor:pointer}.qitem:hover,.qitem.active{background:#eef6ff;border-color:#82b5e7}.qtop{display:flex;gap:4px;align-items:center;flex-wrap:wrap}.qnum{font-weight:950;color:#1458a5;font-size:10px}.qtitle{font-size:10px;line-height:1.35;font-weight:750;margin-top:3px}.qmeta{font-size:9px;color:#64748b;margin-top:3px}.pill{border-radius:999px;padding:2px 5px;font-size:8.5px;font-weight:900;border:1px solid #d5dde7;background:#f8fafc}.pill.A{background:#eff6ff;color:#1d4ed8;border-color:#93c5fd}.pill.B{background:#f5f3ff;color:#6d28d9;border-color:#c4b5fd}.pill.C{background:#ecfdf5;color:#15803d;border-color:#86efac}.pill.D{background:#fff7ed;color:#c2410c;border-color:#fdba74}.editor{border:1px solid #d8e2ec;border-radius:11px;background:#fff;padding:9px}.editor h3{margin:0;font-size:14px}.edmeta{display:flex;gap:5px;flex-wrap:wrap;margin:6px 0}.code{width:100%;min-height:58vh;border:1px solid #cbd5e1;border-radius:9px;padding:10px;background:#fcfdff;color:#172b3f;font:12px/1.55 Consolas,monospace;resize:vertical}.status{margin:7px 0;padding:7px 9px;border-radius:8px;font-size:10px}.ok{background:#eaf8ef;border:1px solid #86efac;color:#166534}.err{background:#fff0f0;border:1px solid #fecaca;color:#b42318}.loading{padding:25px;text-align:center;color:#64748b}@media(max-width:1050px){.layout{grid-template-columns:1fr}.side{position:static;max-height:none}.tree{max-height:300px}.qgrid{grid-template-columns:1fr}.qside{max-height:300px}.lessons{grid-template-columns:1fr}}@media(max-width:600px){.topstat{display:none}.lessons{grid-template-columns:1fr;padding:6px}.filters{grid-template-columns:1fr}.wrap{padding:7px}}
</style></head>
<body>
<div class="top"><div class="topin"><div><div class="brand">📚 Ngân hàng câu hỏi GitHub</div><div class="sub">Nguồn chính: bank_index.json + ngan-hang/*.tex</div></div><div class="nav"><button id="navCatalog" class="on" onclick="showCatalog()">Mục lục</button><button id="navEditor" onclick="showEditor()">Chỉnh sửa</button></div><div class="topstat" id="topStat">GitHub</div></div></div>
<div class="wrap">
<div class="source">🟢 <b>GitHub đang là nguồn chính</b> · Google Sheet không được gọi · File .tex được đọc khi mở bài</div>
<div class="toolbar"><button class="btn primary" onclick="loadCatalog(true)">↻ Tải mục lục</button><button class="btn" onclick="clearFilters()">Bỏ lọc</button><button class="btn" onclick="showCatalog()">📚 Mục lục</button><button class="btn" onclick="showEditor()">✏️ Chỉnh sửa</button></div>
<div id="catalogView" class="layout">
 <aside class="card side"><div class="sideHead">🔎 Tìm nhanh</div><div class="filters"><div class="field"><label>Từ khóa</label><input id="search" placeholder="Bài, chương, dạng..." oninput="render()"></div><div class="field"><label>Môn</label><select id="fMon" onchange="renderTree();render()"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="fLop" onchange="renderTree();render()"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="fChuong" onchange="render()"><option value="">Tất cả</option></select></div></div><div id="tree" class="tree"></div></aside>
 <main class="card"><div class="mainHead"><span>📖 Mục lục kiểu sách</span><span id="summary" class="stats"></span></div><div id="books" class="books"><div class="loading">Đang tải mục lục GitHub...</div></div></main>
</div>
<div id="editorView" class="card" style="display:none;padding:10px"><div class="editorTop"><div><b id="editorPath">Chưa chọn file .tex</b><div class="muted" id="editorInfo"></div></div><div><button class="btn" onclick="showCatalog()">← Mục lục</button><button id="saveBtn" class="btn green" onclick="saveTex()">💾 Lưu GitHub</button></div></div><div id="editorBody"><div class="empty">Chọn một Bài → chọn Dạng → chọn câu để chỉnh sửa.</div></div></div>
</div>
<script>
const TYPE_LABEL={A:'Trắc nghiệm',B:'Đúng / Sai',C:'Trả lời ngắn',D:'Tự luận'};
let ALL=[],FILTERED=[],CURRENT=null,CURRENT_DANG='';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/gi,'d').toLowerCase().trim();
const pathQ=s=>encodeURIComponent(String(s||''));
function uniq(a){return [...new Set(a.filter(Boolean))]};
function setOpts(id,vals){const e=document.getElementById(id),cur=e.value; e.innerHTML='<option value="">Tất cả</option>'+vals.sort((a,b)=>norm(a).localeCompare(norm(b),'vi')).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');if(vals.includes(cur))e.value=cur}
function clearFilters(){['search','fMon','fLop','fChuong'].forEach(id=>document.getElementById(id).value='');renderTree();render()}
function filtered(){const mon=document.getElementById('fMon').value,lop=document.getElementById('fLop').value,ch=document.getElementById('fChuong').value,q=norm(document.getElementById('search').value);return ALL.filter(x=>(!mon||x.mon===mon)&&(!lop||x.lop===lop)&&(!ch||x.chuong===ch)&&(!q||norm([x.mon,x.lop,x.chuong,x.bai].join(' ')).includes(q)))}
function syncFilters(){const base=ALL.filter(x=>!document.getElementById('fMon').value||x.mon===document.getElementById('fMon').value);setOpts('fLop',uniq(base.map(x=>x.lop)));const b2=base.filter(x=>!document.getElementById('fLop').value||x.lop===document.getElementById('fLop').value);setOpts('fChuong',uniq(b2.map(x=>x.chuong)))}
function renderTree(){syncFilters();const root=document.getElementById('tree');const list=filtered();const mons={};for(const x of list)(mons[x.mon]??=[]).push(x);let h='';for(const m of Object.keys(mons).sort((a,b)=>norm(a).localeCompare(norm(b),'vi'))){const grades={};mons[m].forEach(x=>(grades[x.lop]??=[]).push(x));h+=`<details open><summary>📘 ${esc(m)}</summary>`;for(const g of Object.keys(grades).sort()){const chapters=uniq(grades[g].map(x=>x.chuong));h+=`<details><summary>  └─ Lớp ${esc(g)}</summary>`;for(const c of chapters){const x=grades[g].find(v=>v.chuong===c);h+=`<div class="node" onclick="pickScope('${esc(m)}','${esc(g)}','${esc(c)}')">${esc(c)}</div>`}h+='</details>'}h+='</details>'}root.innerHTML=h||'<div class="empty">Không có mục phù hợp.</div>'}
function pickScope(m,g,c){document.getElementById('fMon').value=m;syncFilters();document.getElementById('fLop').value=g;syncFilters();document.getElementById('fChuong').value=c;render()}
function render(){FILTERED=filtered();const byM={};FILTERED.forEach(x=>(byM[x.mon]??=[]).push(x));let html='';for(const m of Object.keys(byM).sort()){html+=`<section class="subject"><div class="subjectHead">${esc(m)} <span style="font-size:10px">${byM[m].reduce((a,x)=>a+x.count,0)} câu</span></div>`;const byG={};byM[m].forEach(x=>(byG[x.lop]??=[]).push(x));for(const g of Object.keys(byG).sort()){html+=`<div class="grade"><div class="gradeHead">Khối ${esc(g)}</div>`;const byC={};byG[g].forEach(x=>(byC[x.chuong]??=[]).push(x));for(const c of Object.keys(byC)){html+=`<div class="chapter"><div class="chapterHead">${esc(c)}</div><div class="lessons">`;byC[c].forEach(x=>{html+=lessonHtml(x)});html+='</div></div>'}html+='</div>'}html+='</section>'}document.getElementById('books').innerHTML=html||'<div class="empty">Không có bài phù hợp.</div>';document.getElementById('summary').innerHTML=`<span class="stat">${FILTERED.length} bài</span><span class="stat">${FILTERED.reduce((a,x)=>a+x.count,0)} câu</span>`;document.getElementById('topStat').textContent=`${FILTERED.length} bài · GitHub`}
function lessonHtml(x){const id='L'+Math.random().toString(36).slice(2);return `<article class="lesson" id="${id}"><div class="lessonTitle">${esc(x.bai||'Chưa rõ bài')}</div><div class="muted">${esc(x.mon)} · Lớp ${esc(x.lop)} · ${esc(x.chuong)}</div><div class="chips"><span class="chip">${x.count} câu</span><span class="chip">.tex</span></div><div class="dbt"><div class="dbtHead">🏷️ Dạng bài tập</div><div class="muted">Đang đọc file .tex...</div></div><div class="actions"><button class="mini" onclick="openDetail(this,'${pathQ(x.path)}')">📂 Mở bài</button></div></article>`}
async function openDetail(btn,p){const card=btn.closest('.lesson');const path=decodeURIComponent(p);btn.disabled=true;btn.textContent='⏳ Đọc .tex...';try{const r=await fetch('/github/api/tex?path='+p,{cache:'no-store'});const j=await r.json();if(!j.ok)throw new Error(j.error||'Không đọc được file');card.querySelector('.dbt').innerHTML=buildDang(j);card.querySelector('.actions').innerHTML=`<button class="mini" onclick="openEditor('${pathQ(path)}')">✏️ Chỉnh sửa</button><button class="mini" onclick="chooseAll('${pathQ(path)}')">📂 Tất cả câu</button>`;card.dataset.detail='1'}catch(e){card.querySelector('.dbt').innerHTML='<span style="color:#b42318">'+esc(e.message)+'</span>'}finally{btn.disabled=false}}
function buildDang(j){let map=j.dang||{};const names=Object.keys(map).sort((a,b)=>norm(a).localeCompare(norm(b),'vi'));if(!names.length)return '<div class="muted">Chưa có Dạng bài tập trong file.</div>';return names.map(d=>{const z=map[d];return `<div class="dbtrow" onclick="chooseDang('${pathQ(j.path)}','${pathQ(d)}')"><div class="dbtname">${esc(d)}</div><div class="dbtmeta"><span class="pill A">A ${z.A||0}</span><span class="pill B">B ${z.B||0}</span><span class="pill C">C ${z.C||0}</span><span class="pill D">D ${z.D||0}</span><span class="pill">${z.total||0}</span></div></div>`}).join('')}
async function chooseDang(p,d){const path=decodeURIComponent(p),dang=decodeURIComponent(d);showEditor();await openEditor(path,dang)}
async function chooseAll(p){const path=decodeURIComponent(p);showEditor();await openEditor(path,'')}
async function openEditor(path,dang=''){const r=await fetch('/github/api/tex?path='+pathQ(path),{cache:'no-store'});const j=await r.json();if(!j.ok){alert(j.error||'Không đọc được .tex');return}CURRENT={path,sha:j.sha,text:j.text,questions:j.questions,dang:j.dang};CURRENT_DANG=dang;document.getElementById('editorPath').textContent=path;document.getElementById('editorInfo').textContent=`${j.questions.length} câu · ${Object.keys(j.dang||{}).length} dạng · GitHub`;renderEditorList();}
function renderEditorList(){const qs=(CURRENT.questions||[]).filter(q=>!CURRENT_DANG||q.dang===CURRENT_DANG);let list='';for(const q of qs){list+=`<div class="qitem" onclick="selectQ(${q.no})"><div class="qtop"><span class="qnum">Câu ${q.no}</span><span class="pill ${q.kind}">${q.kind} · ${esc(q.kind_label)}</span>${q.level?`<span class="pill">${esc(q.level)}</span>`:''}${q.has_image?'<span class="pill">🖼</span>':''}</div><div class="qtitle">${esc(q.title)}</div><div class="qmeta">${esc(q.dang)}${q.id?' · '+esc(q.id):''}</div></div>`}document.getElementById('editorBody').innerHTML=`<div class="qgrid"><div class="card qside" style="padding:7px"><div class="muted" style="padding:3px">${qs.length} câu${CURRENT_DANG?' · Dạng: '+esc(CURRENT_DANG):''}</div>${list||'<div class="empty">Không có câu.</div>'}</div><div id="ed" class="editor"><div class="empty">Chọn câu bên trái.</div></div></div>`}
function selectQ(no){const q=(CURRENT.questions||[]).find(x=>x.no===no);if(!q)return;document.getElementById('ed').innerHTML=`<div class="editor"><h3>Câu ${q.no}</h3><div class="edmeta"><span class="pill ${q.kind}">${q.kind} · ${esc(q.kind_label)}</span><span class="pill">${esc(q.level||'—')}</span><span class="pill">${esc(q.dang)}</span>${q.id?`<span class="pill">${esc(q.id)}</span>`:''}</div><textarea id="code" class="code" spellcheck="false">${esc(q.text)}</textarea><div class="muted" style="margin-top:5px">Sửa trực tiếp block <b>\\begin{ex} ... \\end{ex}</b>. Có TikZ/hình thì giữ nguyên trong block.</div><div style="margin-top:7px"><button class="btn green" onclick="replaceAndSave(${q.no})">💾 Lưu câu lên GitHub</button></div></div>`}
async function replaceAndSave(no){if(!CURRENT)return;const q=CURRENT.questions.find(x=>x.no===no);if(!q)return;const nv=document.getElementById('code').value;const before=CURRENT.text.slice(0,q.text?CURRENT.text.indexOf(q.text,q.start||0):0);const idx=CURRENT.questions.findIndex(x=>x.no===no);const pos=findBlockStart(CURRENT.text,idx),end=findBlockEnd(CURRENT.text,idx);const next=CURRENT.text.slice(0,pos)+nv+CURRENT.text.slice(end);await saveText(next,'Cập nhật câu '+no+' trong '+CURRENT.path)}
function findBlockStart(text,index){const ms=[...text.matchAll(/\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}/gi)];return ms[index]?.index??0}
function findBlockEnd(text,index){const ms=[...text.matchAll(/\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}/gi)];const m=ms[index];return m?m.index+m[0].length:text.length}
async function saveText(text,msg){const r=await fetch('/github/api/save-tex',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:CURRENT.path,text,sha:CURRENT.sha,message:msg})});const j=await r.json();if(!j.ok){alert(j.error||'Lưu thất bại');return}CURRENT.sha=j.content_sha||CURRENT.sha;CURRENT.text=text;document.getElementById('editorInfo').textContent='✅ Đã commit GitHub · '+(j.commit||'');}
async function saveTex(){if(!CURRENT){alert('Chưa mở file .tex');return}await saveText(CURRENT.text,'Cập nhật '+CURRENT.path)}
function showCatalog(){document.getElementById('catalogView').style.display='grid';document.getElementById('editorView').style.display='none';document.getElementById('navCatalog').classList.add('on');document.getElementById('navEditor').classList.remove('on')}
function showEditor(){document.getElementById('catalogView').style.display='none';document.getElementById('editorView').style.display='block';document.getElementById('navEditor').classList.add('on');document.getElementById('navCatalog').classList.remove('on');}
async function loadCatalog(refresh=false){try{document.getElementById('books').innerHTML='<div class="loading">Đang tải bank_index.json...</div>';const r=await fetch('/github/api/catalog-simple'+(refresh?'?t='+Date.now():''),{cache:'no-store'});const j=await r.json();if(!j.ok)throw new Error(j.error||'Không đọc được mục lục');ALL=j.lessons||[];setOpts('fMon',uniq(ALL.map(x=>x.mon)));syncFilters();renderTree();render();}catch(e){document.getElementById('books').innerHTML='<div class="empty" style="color:#b42318">'+esc(e.message)+'</div>'}}
loadCatalog();
</script></body></html>'''

app.register_blueprint(bp)
