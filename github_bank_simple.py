# -*- coding: utf-8 -*-
"""Ngân hàng GitHub đơn giản.
Nguồn duy nhất: GitHub / bank_index.json + ngan-hang/**/*.tex.
Google Sheet không được gọi ở đây.
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

from flask import Blueprint, Response, jsonify, request
from app import app

bp = Blueprint("github_bank_simple", __name__)

REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = (os.getenv("GITHUB_BRANCH") or "main").strip() or "main"
TOKEN = (os.getenv("GITHUB_TOKEN") or "").strip()
RAW_BASE = "https://raw.githubusercontent.com"
API_BASE = "https://api.github.com"
INDEX_PATH = "bank_index.json"
_CACHE = {"at": 0.0, "index": None}
CACHE_SECONDS = 120

TYPE_LABELS = {"A": "Trắc nghiệm", "B": "Đúng / Sai", "C": "Trả lời ngắn", "D": "Tự luận"}
TYPE_KEYS = ("A", "B", "C", "D")


def _repo_parts():
    if "/" not in REPO:
        raise RuntimeError("GITHUB_REPO phải có dạng owner/repository")
    return REPO.split("/", 1)


def _esc(v):
    return html.escape(str(v or ""), quote=True)


def _clean(v):
    return str(v or "").strip()


def _github_json(path: str, method: str = "GET", payload=None):
    if not TOKEN:
        raise RuntimeError("Thiếu biến môi trường GITHUB_TOKEN trên Render.")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "luyen-de-vat-ly-github-bank",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            obj = json.loads(exc.read().decode("utf-8"))
            msg = obj.get("message", str(exc))
        except Exception:
            msg = str(exc)
        raise RuntimeError(f"GitHub API {exc.code}: {msg}")


def _raw_text(path: str):
    owner, repo = _repo_parts()
    url = f"{RAW_BASE}/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/{urllib.parse.quote(BRANCH)}/{urllib.parse.quote(path, safe='/')}"
    req = urllib.request.Request(url, headers={"User-Agent": "luyen-de-vat-ly-github-bank"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Không đọc được GitHub: HTTP {exc.code}")


def _index():
    now = time.time()
    if _CACHE["index"] is not None and now - _CACHE["at"] < CACHE_SECONDS:
        return _CACHE["index"]
    text = _raw_text(INDEX_PATH)
    obj = json.loads(text)
    _CACHE["index"] = obj
    _CACHE["at"] = now
    return obj


def _valid_tex(path):
    return path.startswith("ngan-hang/") and path.lower().endswith(".tex") and ".." not in path


def _fetch_tex(path):
    if not _valid_tex(path):
        raise RuntimeError("Đường dẫn .tex không hợp lệ.")
    owner, repo = _repo_parts()
    api_path = "/repos/{}/{}/contents/{}?ref={}".format(
        owner,
        repo,
        urllib.parse.quote(path, safe="/"),
        urllib.parse.quote(BRANCH),
    )
    obj = _github_json(api_path)
    raw = (obj.get("content") or "").replace("\n", "")
    return obj.get("sha", ""), base64.b64decode(raw).decode("utf-8", "replace")


def _save_tex(path, text, sha, message):
    if not _valid_tex(path):
        raise RuntimeError("Đường dẫn .tex không hợp lệ.")
    owner, repo = _repo_parts()
    api_path = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}"
    payload = {
        "message": message or "Cập nhật ngân hàng .tex",
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": sha,
    }
    return _github_json(api_path, "PUT", payload)


def _kind(block):
    if re.search(r"\\choiceTF\b", block, re.I):
        return "B"
    if re.search(r"\\shortans\b", block, re.I):
        return "C"
    if re.search(r"\\choice\b", block, re.I):
        return "A"
    return "D"


def _level(block):
    m = re.search(r"%\s*Mức\s*:\s*([^\r\n%]+)", block, re.I)
    return _clean(m.group(1)).upper() if m else ""


def _dang(block, prefix=""):
    blob = prefix[-1200:] + "\n" + block
    m = list(re.finditer(r"\\dangbt\s*\{([^{}]*)\}", blob, re.I))
    return _clean(m[-1].group(1)) if m else "Chưa phân dạng"


def _question_blocks(text):
    pat = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
    matches = list(pat.finditer(text or ""))
    out = []
    prev_end = 0
    for i, m in enumerate(matches, 1):
        block = m.group(0)
        prefix = text[prev_end:m.start()]
        full = prefix + block
        # Keep exactly the ex block for editing/saving, but metadata can use prefix.
        qid_m = re.search(r"%\s*ID\s*:\s*([^\r\n]+)", block, re.I)
        title_m = re.search(
            r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{\s*ex\s*\})",
            block,
            re.I,
        )
        title = title_m.group(1) if title_m else ""
        title = re.sub(r"%[^\r\n]*", "", title)
        title = re.sub(r"\\dangbt\s*\{[^{}]*\}", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()
        out.append({
            "n": i,
            "start": m.start(),
            "end": m.end(),
            "text": block,
            "id": _clean(qid_m.group(1)) if qid_m else "",
            "level": _level(block),
            "dang": _dang(block, prefix),
            "kind": _kind(block),
            "title": title[:300] or "(Chưa đọc được nội dung câu)",
            "has_image": bool(re.search(r"\\begin\s*\{\s*tikzpicture\s*\}|\\includegraphics", full, re.I)),
        })
        prev_end = m.end()
    return out


def _detail(path):
    sha, text = _fetch_tex(path)
    blocks = _question_blocks(text)
    stats = {k: 0 for k in TYPE_KEYS}
    dang_map = {}
    level_map = {k: 0 for k in ("NB", "TH", "VD", "VDC")}
    for q in blocks:
        stats[q["kind"]] += 1
        d = q["dang"] or "Chưa phân dạng"
        item = dang_map.setdefault(d, {"total": 0, "A": 0, "B": 0, "C": 0, "D": 0})
        item["total"] += 1
        item[q["kind"]] += 1
        lv = q["level"]
        for k in level_map:
            if re.search(rf"\b{re.escape(k)}\b", lv):
                level_map[k] += 1
    return {
        "sha": sha,
        "text": text,
        "questions": blocks,
        "stats": stats,
        "levels": level_map,
        "dang": dang_map,
    }


def _catalog_rows():
    idx = _index()
    rows = []
    for item in idx.get("lessons") or []:
        p = _clean(item.get("github") or item.get("path") or item.get("file"))
        if not p:
            continue
        rows.append({
            "Mon": _clean(item.get("Mon")),
            "Lop": _clean(item.get("Lop")),
            "Chuong": _clean(item.get("Chuong")),
            "BaiHoc": _clean(item.get("BaiHoc") or item.get("De")),
            "path": p,
            "count": int(item.get("count_questions") or item.get("questions") or item.get("count") or 0),
            "dang_index": item.get("dang") or {},
        })
    return rows


@bp.get("/github/quan-ly")
def page():
    return Response(PAGE_HTML, mimetype="text/html")


@bp.get("/github/api/catalog-simple")
def api_catalog():
    rows = _catalog_rows()
    idx = _index()
    return jsonify({
        "ok": True,
        "source": "GitHub",
        "total_files": int(idx.get("total_files") or idx.get("count") or len(rows)),
        "total_questions": int(idx.get("total_questions") or sum(x["count"] for x in rows)),
        "lessons": rows,
    })


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
    try:
        result = _save_tex(path, text, sha, message)
        _CACHE["at"] = 0
        return jsonify({"ok": True, "commit": result.get("commit", {}).get("sha", ""), "content_sha": result.get("content", {}).get("sha", "")})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 409


app.register_blueprint(bp)

PAGE_HTML = r'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ngân hàng GitHub</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f8fc;color:#17324d;font-family:Segoe UI,Arial,sans-serif}button,input,select,textarea{font:inherit}.top{background:#1769d2;color:#fff;padding:11px 16px;position:sticky;top:0;z-index:20;box-shadow:0 2px 10px #17324d22}.brand{font-weight:950;font-size:19px}.sub{font-size:11px;opacity:.9}.wrap{max-width:1500px;margin:auto;padding:12px}.bar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-bottom:9px}.btn{border:1px solid #cbd7e4;background:#fff;color:#174a84;border-radius:9px;padding:7px 10px;cursor:pointer;font-weight:850;font-size:12px}.btn.primary{background:#1769d2;color:#fff;border-color:#1769d2}.btn.green{background:#eaf8ef;color:#166534;border-color:#86efac}.btn.red{background:#fff1f2;color:#b42318;border-color:#fecaca}.filters{display:grid;grid-template-columns:1.5fr repeat(4,1fr);gap:7px;background:#fff;border:1px solid #d8e2ec;border-radius:13px;padding:10px}.field label{display:block;font-size:10px;font-weight:900;color:#64748b;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px;background:#fff}.intro{margin-top:9px;background:linear-gradient(#eff6ff,#fff);border:1px solid #c5ddfa;border-radius:13px;padding:10px}.intro b{color:#1d4ed8}.pills{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}.pill{border:1px solid #bfdbfe;border-radius:999px;padding:4px 7px;background:#fff;color:#1d4ed8;font-size:10px;font-weight:900}.subject{margin-top:10px}.subjectHead{padding:9px 12px;border-radius:12px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:950;display:flex;justify-content:space-between}.grade{margin-top:8px;border:1px solid #ccd7e2;border-radius:12px;background:#fff;overflow:hidden}.gradeHead{padding:8px 11px;background:#f1f5f9;font-weight:900}.chap{margin:8px;border:1px solid #c8ddf5;border-radius:11px;overflow:hidden;background:#f8fbff}.chapHead{padding:8px 10px;background:#dbeafe;color:#1e3a8a;font-weight:950}.grid{padding:8px;display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:8px}.lesson{border:1px solid #dce5ed;border-radius:12px;background:#fff;padding:9px}.title{font-weight:950;line-height:1.3}.muted{color:#64748b;font-size:11px}.tags{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0}.tag{border:1px solid #d7e0e8;border-radius:999px;padding:3px 6px;font-size:9.5px;font-weight:900;background:#f8fafc}.dbt{margin-top:5px;border:1px solid #d7e7f8;border-radius:9px;background:#f8fbff;padding:6px}.dbtHead{font-size:10px;font-weight:950;color:#1e3a8a;margin-bottom:4px}.dbtBtn{display:flex;justify-content:space-between;gap:8px;width:100%;text-align:left;border:1px solid #dbeafe;background:#fff;border-radius:7px;padding:5px 6px;margin:3px 0;cursor:pointer;font-size:10px;font-weight:800;color:#17324d}.dbtBtn:hover{background:#eff6ff;border-color:#60a5fa}.counts{display:flex;gap:3px;flex-wrap:wrap}.tiny{font-size:9px;padding:2px 4px;border-radius:999px;border:1px solid #d1d9e2;font-weight:900}.a{background:#eff6ff;color:#1d4ed8;border-color:#93c5fd}.b{background:#f5f3ff;color:#6d28d9;border-color:#c4b5fd}.c{background:#ecfdf5;color:#15803d;border-color:#86efac}.d{background:#fff7ed;color:#c2410c;border-color:#fdba74}.actions{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}.modal{position:fixed;inset:0;background:#0f172a88;display:flex;align-items:center;justify-content:center;padding:16px;z-index:100}.modal.hide{display:none}.box{width:min(1400px,96vw);height:min(90vh,900px);background:#fff;border-radius:14px;overflow:hidden;display:flex;flex-direction:column}.head{padding:10px 13px;background:#eef6ff;border-bottom:1px solid #cbdcef;display:flex;justify-content:space-between;gap:8px}.body{display:grid;grid-template-columns:330px 1fr;gap:0;min-height:0;flex:1}.qlist{overflow:auto;border-right:1px solid #dbe4ed;padding:7px}.q{padding:7px;border:1px solid #e0e7ef;border-radius:8px;margin:4px 0;cursor:pointer}.q.active,.q:hover{background:#eff6ff;border-color:#8db8e9}.qn{font-size:10px;font-weight:950;color:#1d4ed8}.qt{font-size:10px;line-height:1.35;margin-top:2px}.qmeta{font-size:9px;color:#64748b;margin-top:2px}.editor{padding:10px;display:flex;flex-direction:column;min-width:0}.meta{display:grid;grid-template-columns:1fr 1fr;gap:6px}.meta input{width:100%;padding:7px;border:1px solid #cbd5e1;border-radius:7px}.code{flex:1;min-height:0;margin-top:8px;width:100%;resize:none;border:1px solid #cbd5e1;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.status{font-size:11px;padding:7px 9px;border-radius:8px;margin-top:7px}.ok{background:#ecfdf5;border:1px solid #86efac;color:#166534}.err{background:#fff1f2;border:1px solid #fecaca;color:#b42318}.close{border:0;background:#475569;color:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;font-weight:900}.empty{text-align:center;padding:30px;color:#64748b}@media(max-width:850px){.filters{grid-template-columns:1fr 1fr}.body{grid-template-columns:1fr}.qlist{max-height:220px;border-right:0;border-bottom:1px solid #dbe4ed}.meta{grid-template-columns:1fr}.grid{grid-template-columns:1fr}} 
</style>
</head>
<body>
<div class="top"><div class="brand">📚 Ngân hàng đề — GitHub</div><div class="sub">Đọc trực tiếp bank_index.json và ngan-hang/*.tex · Google Sheet không dùng</div></div>
<div class="wrap">
  <div class="bar"><button class="btn primary" onclick="loadCatalog(true)">↻ Làm mới</button><button class="btn" onclick="location.href='/'">⌂ Trang chính</button><span id="status" class="muted"></span></div>
  <div class="filters">
    <div class="field"><label>Tìm nhanh</label><input id="search" placeholder="Bài, chương, dạng bài..." oninput="render()"></div>
    <div class="field"><label>Môn</label><select id="mon" onchange="rebuildFilters();render()"><option value="">Tất cả</option></select></div>
    <div class="field"><label>Lớp</label><select id="lop" onchange="rebuildFilters();render()"><option value="">Tất cả</option></select></div>
    <div class="field"><label>Chương</label><select id="chuong" onchange="render()"><option value="">Tất cả</option></select></div>
    <div class="field"><label>Dạng bài tập</label><input id="dang" placeholder="Nhập/ chọn dạng" oninput="render()"></div>
  </div>
  <div id="intro" class="intro"></div>
  <div id="catalog"></div>
</div>
<div id="modal" class="modal hide"><div class="box"><div class="head"><div><b id="modalTitle">Sửa file .tex</b><div id="modalSub" class="muted"></div></div><button class="close" onclick="closeModal()">Đóng</button></div><div class="body"><div id="qlist" class="qlist"></div><div class="editor"><div class="meta"><input id="qid" placeholder="ID câu"><input id="qlevel" placeholder="Mức độ"></div><textarea id="code" class="code" spellcheck="false"></textarea><div class="actions"><button class="btn green" onclick="saveTex()">💾 Lưu trực tiếp GitHub</button><button class="btn" onclick="reloadDetail()">↻ Đọc lại .tex</button><button class="btn red" onclick="closeModal()">Hủy</button></div><div id="editStatus" class="status hide"></div></div></div></div></div>
<script>
let DATA=[], DETAIL=null, PATH='', SHA='', ACTIVE=-1;
const $=id=>document.getElementById(id);
function esc(s){return String(s??'').replace(/[&<>\"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\':'\\\\','"':'&quot;'}[m]));}
function showStatus(t,err=false){$('status').textContent=t;$('status').style.color=err?'#b42318':'#166534'}
async function getJSON(url,opt){let r=await fetch(url,opt);let j=await r.json();if(!r.ok||j.ok===false)throw Error(j.error||'Lỗi máy chủ');return j}
async function loadCatalog(refresh=false){try{showStatus('⏳ Đọc GitHub...');let j=await getJSON('/github/api/catalog-simple'+(refresh?'?t='+Date.now():''));DATA=j.lessons||[];$('intro').innerHTML='<b>📚 Mục lục kiểu sách</b> · <span class="pill">'+j.total_files+' file</span> <span class="pill">'+j.total_questions+' câu</span> <span class="pill">✓ GitHub</span>';rebuildFilters();render();showStatus('✓ Đã nạp '+j.total_questions+' câu từ GitHub')}catch(e){showStatus('❌ '+e.message,true)}}
function opts(id,arr,keep){let el=$(id),old=keep??el.value,vals=[...new Set(arr.filter(Boolean).sort((a,b)=>a.localeCompare(b,'vi')))];el.innerHTML='<option value="">Tất cả</option>'+vals.map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join('');if(vals.includes(old))el.value=old}
function filteredBase(){let mon=$('mon').value,lop=$('lop').value;return DATA.filter(x=>(!mon||x.Mon===mon)&&(!lop||x.Lop===lop))}
function rebuildFilters(){let monKeep=$('mon').value,lopKeep=$('lop').value,chuKeep=$('chuong').value;opts('mon',DATA.map(x=>x.Mon),monKeep);opts('lop',DATA.filter(x=>!$('mon').value||x.Mon===$('mon').value).map(x=>x.Lop),lopKeep);let base=filteredBase();opts('chuong',base.map(x=>x.Chuong),chuKeep)}
function escapeAttr(s){return esc(s).replace(/'/g,'&#39;')}
function groupBy(arr,key){let m=new Map();for(let x of arr){let k=x[key]||'Chưa rõ';if(!m.has(k))m.set(k,[]);m.get(k).push(x)}return m}
function render(){let q=($('search').value||'').toLowerCase().trim(),mon=$('mon').value,lop=$('lop').value,chu=$('chuong').value,dang=($('dang').value||'').toLowerCase().trim();let list=DATA.filter(x=>(!mon||x.Mon===mon)&&(!lop||x.Lop===lop)&&(!chu||x.Chuong===chu)&&(!q||[x.BaiHoc,x.Chuong,x.Mon,x.Lop].join(' ').toLowerCase().includes(q)));$('catalog').innerHTML='';if(!list.length){$('catalog').innerHTML='<div class="card empty">Không có bài phù hợp.</div>';return}let hs=groupBy(list,'Mon');let html='';for(let [m,ml] of hs){html+='<section class="subject"><div class="subjectHead"><span>'+esc(m||'Môn chưa rõ')+'</span><span>'+ml.reduce((a,x)=>a+x.count,0)+' câu</span></div>';for(let [lopv,ll] of groupBy(ml,'Lop')){html+='<div class="grade"><div class="gradeHead">Khối '+esc(lopv)+'</div>';for(let [ch,cl] of groupBy(ll,'Chuong')){html+='<div class="chap"><div class="chapHead">'+esc(ch)+'</div><div class="grid">';for(let item of cl){let id='L'+Math.random().toString(36).slice(2);html+='<div class="lesson"><div class="title">'+esc(item.BaiHoc||'Chưa rõ bài')+'</div><div class="muted">'+esc(item.Mon)+' · Lớp '+esc(item.Lop)+'</div><div class="tags"><span class="tag">'+item.count+' câu</span><span class="tag">GitHub .tex</span></div><div id="'+id+'" class="dbt"><div class="dbtHead">🏷️ Dạng bài tập</div><div class="muted">Đang đọc .tex khi mở bài…</div></div><div class="actions"><button class="btn primary" onclick="openDetail('+JSON.stringify(item.path)+','+JSON.stringify(item.BaiHoc||'')+')">📖 Mở bài</button></div></div>';setTimeout(()=>loadLessonCard(id,item.path),0)}html+='</div></div>'}html+='</div>'}html+='</section>'} $('catalog').innerHTML=html}
async function loadLessonCard(id,path){let el=$(id);if(!el)return;try{let d=await getJSON('/github/api/tex?path='+encodeURIComponent(path));let html='';let ds=d.dang||{};let entries=Object.entries(ds);if(!entries.length)html='<div class="muted">Chưa có Dạng BT</div>';else for(let [name,c] of entries){let searchDang=($('dang').value||'').toLowerCase().trim();if(searchDang&&!name.toLowerCase().includes(searchDang))continue;html+='<button class="dbtBtn" onclick="openDetail('+JSON.stringify(path)+','+JSON.stringify(name)+')"><span>'+esc(name)+'</span><span class="counts"><span class="tiny a">A '+c.A+'</span><span class="tiny b">B '+c.B+'</span><span class="tiny c">C '+c.C+'</span><span class="tiny d">D '+c.D+'</span><span class="tiny">Σ '+c.total+'</span></span></button>'}el.innerHTML='<div class="dbtHead">🏷️ Dạng bài tập ('+entries.length+')</div>'+html}catch(e){el.innerHTML='<div class="muted">Không đọc được .tex: '+esc(e.message)+'</div>'}}
async function openDetail(path,title){PATH=path;ACTIVE=-1;$('modal').classList.remove('hide');$('modalTitle').textContent='📖 '+title;$('modalSub').textContent=path;$('code').value='';$('qlist').innerHTML='<div class="muted">⏳ Đọc file .tex…</div>';try{DETAIL=await getJSON('/github/api/tex?path='+encodeURIComponent(path));SHA=DETAIL.sha;renderQList();if(DETAIL.questions.length)selectQ(0)}catch(e){$('qlist').innerHTML='<div class="muted">❌ '+esc(e.message)+'</div>'}}
function renderQList(){let html='';for(let q of DETAIL.questions){html+='<div class="q" id="q_'+q.n+'" onclick="selectQ('+q.n+')"><div class="qn">Câu '+q.n+' · '+q.kind+' · '+esc(q.level||'')+(q.has_image?' · 🖼':'')+'</div><div class="qt">'+esc(q.title)+'</div><div class="qmeta">'+esc(q.dang)+'</div></div>'}$('qlist').innerHTML=html}
function selectQ(n){let q=DETAIL.questions[n-1];if(!q)return;ACTIVE=n;document.querySelectorAll('.q').forEach(x=>x.classList.remove('active'));let el=$('q_'+n);if(el)el.classList.add('active');$('qid').value=q.id||'';$('qlevel').value=q.level||'';$('code').value=q.text||''}
function reloadDetail(){if(PATH)openDetail(PATH,$('modalTitle').textContent.replace(/^📖\s*/,''))}
function closeModal(){$('modal').classList.add('hide');DETAIL=null;PATH='';SHA='';ACTIVE=-1}
function setEditStatus(t,err=false){let e=$('editStatus');e.className='status '+(err?'err':'ok');e.textContent=t;e.classList.remove('hide')}
async function saveTex(){if(!PATH||!DETAIL)return;let text=$('code').value||'';if(!text.trim()){setEditStatus('Nội dung .tex trống.',true);return}if(ACTIVE>0){let q=DETAIL.questions[ACTIVE-1];let all=DETAIL.text;let start=q.start,end=q.end;all=all.slice(0,start)+text+all.slice(end);text=all}try{setEditStatus('⏳ Đang commit lên GitHub...');let j=await getJSON('/github/api/save-tex',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:PATH,text,sha:SHA,message:'Cập nhật '+PATH})});setEditStatus('✅ Đã lưu GitHub · commit '+(j.commit||'').slice(0,8));await new Promise(r=>setTimeout(r,250));DETAIL=await getJSON('/github/api/tex?path='+encodeURIComponent(PATH));SHA=DETAIL.sha;renderQList();selectQ(ACTIVE>0?ACTIVE:1)}catch(e){setEditStatus('❌ '+e.message,true)}}
loadCatalog();
</script>
</body></html>'''
