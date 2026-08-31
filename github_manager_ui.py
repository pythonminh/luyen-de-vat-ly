# -*- coding: utf-8 -*-
"""Ngân hàng GitHub — giao diện quản lý thống nhất.

Nguồn dữ liệu duy nhất cho ngân hàng câu hỏi:
    GitHub / ngan-hang/*.tex
    GitHub / bank_index.json (chỉ mục nhanh)

Không dùng Google Sheet cho ngân hàng câu hỏi.
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
from collections import defaultdict

from flask import Blueprint, Response, jsonify, redirect, request, session, url_for
from app import app

bp = Blueprint("github_manager_ui", __name__)

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = "main"


def clean(s):
    return str(s or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def esc(s):
    return html.escape(str(s or ""), quote=True)


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
        return Response("<h3>403 — Chỉ ADMIN được quản lý ngân hàng GitHub.</h3>", 403, mimetype="text/html")
    return None


def repo_parts():
    if "/" not in REPO:
        raise RuntimeError("GITHUB_REPO phải có dạng owner/repository")
    return REPO.split("/", 1)


def github_json(path, method="GET", payload=None):
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Render chưa có GITHUB_TOKEN.")
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
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            info = json.loads(e.read().decode("utf-8"))
            msg = info.get("message", str(e))
        except Exception:
            msg = str(e)
        raise RuntimeError(f"GitHub API {e.code}: {msg}")


def load_index():
    owner, repo = repo_parts()
    url = f"{RAW}/{owner}/{repo}/{BRANCH}/bank_index.json"
    req = urllib.request.Request(url, headers={"User-Agent": "luyen-de-vat-ly"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        # Chỉ là fallback khi GitHub Raw tạm thời chậm; file vẫn phải là bản GitHub đã deploy.
        local = os.path.join(app.root_path, "bank_index.json")
        with open(local, "r", encoding="utf-8") as f:
            return json.load(f)


def valid_path(path):
    p = clean(path).strip("/")
    return p.startswith("ngan-hang/") and p.lower().endswith(".tex") and ".." not in p


def fetch_tex(path):
    owner, repo = repo_parts()
    api = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(BRANCH)}"
    d = github_json(api)
    raw = base64.b64decode((d.get("content") or "").replace("\n", "")).decode("utf-8", "replace")
    return d.get("sha", ""), raw


def save_tex(path, content, sha, message):
    owner, repo = repo_parts()
    api = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}"
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": sha,
    }
    return github_json(api, "PUT", body)


def split_tex(text):
    pat = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
    ms = list(pat.finditer(text or ""))
    if not ms:
        return text or "", [], ""
    return text[:ms[0].start()], [m.group(0) for m in ms], text[ms[-1].end():]


def detect_kind(block):
    if re.search(r"\\choiceTF\b", block or "", re.I):
        return "B", "Đúng / Sai"
    if re.search(r"\\shortans\b", block or "", re.I):
        return "C", "Trả lời ngắn"
    if re.search(r"\\choice\b", block or "", re.I):
        return "A", "Trắc nghiệm"
    return "D", "Tự luận"


def qmeta(block, n):
    def one(pattern):
        m = re.search(pattern, block or "", re.I)
        return m.group(1).strip() if m else ""

    kind, label = detect_kind(block)
    title = ""
    m = re.search(
        r"\\begin\s*\{\s*ex\s*\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{\s*ex\s*\})",
        block or "", re.S | re.I,
    )
    if m:
        title = re.sub(r"%[^\r\n]*", "", m.group(1))
        title = re.sub(r"\\dangbt\s*\{[^{}]*\}", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()

    return {
        "n": n,
        "id": one(r"%\s*ID\s*:\s*([^\r\n]+)"),
        "level": one(r"%\s*Mức\s*:\s*([^\r\n]+)"),
        "dang": one(r"\\dangbt\s*\{([^{}]*)\}"),
        "kind": kind,
        "label": label,
        "title": title[:260] or "(Chưa đọc được nội dung câu)",
        "has_tikz": bool(re.search(r"\\begin\s*\{\s*tikzpicture\s*\}|\\includegraphics", block or "", re.I)),
    }


def rebuild_block(block, qid, level, dang):
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
    meta_text = ("\n" + "\n".join(lines) + "\n") if lines else "\n"
    b = b[:m.end()] + meta_text + b[m.end():]
    if dang:
        b = b[:m.start()] + "\\dangbt{" + dang + "}\n" + b[m.start():]
    return b


def classify_counts(blocks):
    c = {k: 0 for k in "ABCD"}
    levels = {k: 0 for k in ("NB", "TH", "VD", "VDC")}
    for b in blocks:
        k, _ = detect_kind(b)
        c[k] += 1
        m = re.search(r"%\s*Mức\s*:\s*(NB|TH|VD|VDC)\b", b or "", re.I)
        if m:
            levels[m.group(1).upper()] += 1
    return c, levels


CSS = r"""
<style>
:root{--blue:#1769d2;--blue2:#edf5ff;--ink:#18324d;--muted:#64748b;--line:#d9e3ee;--bg:#f4f7fb;--ok:#16813d;--violet:#6d4bd8;--orange:#e86b18;--surface:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}.page{max-width:1480px;margin:0 auto;padding:0 12px 50px}
.top{position:sticky;top:0;z-index:50;background:#1769d2;color:#fff;box-shadow:0 2px 12px #0f4fa844}.topRow{min-height:64px;display:flex;align-items:center;gap:14px;padding:10px 14px}.brand{font-size:21px;font-weight:900;letter-spacing:.2px}.brandSub{font-size:11px;opacity:.9;margin-top:2px}.subjectTabs{display:flex;gap:6px}.subjectBtn{border:1px solid #ffffff55;background:#ffffff14;color:#fff;border-radius:13px;padding:8px 15px;font-weight:900;cursor:pointer}.subjectBtn.active{background:#fff;color:#1558a6}.topRight{margin-left:auto;display:flex;align-items:center;gap:7px}.topBtn{border:1px solid #ffffff45;background:#ffffff12;color:#fff;border-radius:9px;padding:8px 10px;font-weight:800;cursor:pointer;text-decoration:none;font-size:12px}
.examStrip{margin-top:0;padding:8px 15px;background:#e9f3ff;border-bottom:1px solid #c8dff7;color:#174a84;font-size:12px}.nav{display:flex;gap:8px;flex-wrap:wrap;padding:12px 0}.btn{border:1px solid #cbd7e4;background:var(--surface);color:#174a84;border-radius:9px;padding:9px 12px;font-size:12px;font-weight:800;text-decoration:none;cursor:pointer}.btn:hover{background:#f8fbff}.btnPrimary{background:var(--blue);border-color:var(--blue);color:#fff}.btnGreen{background:var(--ok);border-color:var(--ok);color:#fff}.btnRed{background:#fff5f5;border-color:#efb2b2;color:#b42318}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;box-shadow:0 3px 14px #17324d0a}.filters{padding:13px;display:grid;grid-template-columns:1.4fr repeat(5,1fr);gap:8px}.field label{display:block;font-size:11px;font-weight:900;color:#526174;margin-bottom:4px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd6e2;border-radius:9px;background:#fff;color:var(--ink)}
.catalogIntro{margin-top:12px;padding:12px 14px;background:linear-gradient(180deg,#eff6ff,#fff);border:1px solid #c9ddfa;border-radius:16px}.introTitle{font-size:16px;font-weight:950;color:#1e3a8a;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.tag{display:inline-flex;align-items:center;gap:4px;padding:4px 8px;border-radius:999px;background:#f1f5f9;border:1px solid #dbe3ea;font-size:11px;font-weight:850;color:#475569}.stats{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.statPill{border:1px solid #bfdbfe;background:#fff;color:#1d4ed8;border-radius:999px;padding:4px 9px;font-size:11px;font-weight:900}.shelf{margin-top:12px}.subjectBlock{margin:12px 0 16px}.subjectHead{padding:11px 13px;border-radius:14px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:950;font-size:17px;display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap}.gradeBlock{margin:10px 0;border:1px solid #cbd7e4;border-radius:15px;overflow:hidden}.gradeHead{padding:10px 12px;background:#f1f5f9;display:flex;justify-content:space-between;gap:8px;align-items:center;font-weight:950}.chapterBlock{margin:9px;border:1px solid #bfdbfe;border-radius:13px;overflow:hidden;background:#f8fbff}.chapterHead{padding:9px 11px;background:#dbeafe;color:#1e3a8a;font-weight:950;display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap}.lessonGrid{padding:9px;display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:9px}.lessonCard{border:1px solid #e1e8ef;border-radius:13px;padding:10px;background:#fff;display:flex;flex-direction:column;gap:7px;box-shadow:0 1px 3px #0f172a0d}.lessonTitle{font-weight:950;color:#0f172a;line-height:1.3}.lessonSub{font-size:12px;color:#64748b;line-height:1.35}.chips{display:flex;flex-wrap:wrap;gap:5px}.chip{border:1px solid #d7dee7;background:#f8fafc;border-radius:999px;padding:4px 7px;font-size:10px;font-weight:850;color:#475569}.a{background:#edf4ff;border-color:#bfdbfe;color:#1557a6}.b{background:#f5efff;border-color:#d8b4fe;color:#6542c2}.c{background:#ecfbf3;border-color:#a7f3d0;color:#16804f}.d{background:#fff5eb;border-color:#fed7aa;color:#ae5a0b}.lessonActions{display:flex;gap:6px;flex-wrap:wrap}.miniBtn{border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:8px;padding:6px 8px;font-size:11px;font-weight:900;cursor:pointer}.miniBtn.green{background:#eaf8ef;color:#166534;border-color:#86efac}
.split{display:grid;grid-template-columns:340px 1fr;gap:12px}.sidebar{max-height:calc(100vh - 120px);overflow:auto}.panelTitle{padding:12px 14px;border-bottom:1px solid #e7edf3;font-weight:950}.qList{padding:9px}.qitem{border:1px solid #e0e7ef;border-radius:10px;padding:9px;margin:6px 0;cursor:pointer;background:#fff}.qitem:hover,.qitem.active{background:#edf5ff;border-color:#8bb9ed}.qtop{display:flex;gap:5px;align-items:center;flex-wrap:wrap}.qnum{font-weight:950;color:#145bb0}.qtitle{margin-top:4px;font-size:12px;font-weight:750;line-height:1.4;color:#243b53}.qmeta{margin-top:4px;font-size:10px;color:#64748b;line-height:1.4}.editor{padding:15px}.editorHead{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;flex-wrap:wrap}.editorTitle{font-size:20px;font-weight:950}.metaGrid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}.code{width:100%;min-height:540px;padding:12px;border:1px solid #bfcddd;border-radius:10px;background:#fcfdff;font:13px/1.55 Consolas,Monaco,monospace;resize:vertical}.hint{margin-top:8px;padding:9px 11px;border:1px dashed #bfd0e1;border-radius:9px;background:#f8fbff;color:#607083;font-size:11px;line-height:1.5}.hidden{display:none!important}.message{margin:10px 0;padding:10px 12px;border-radius:9px;font-size:12px}.ok{background:#eaf8ef;border:1px solid #a7d8b6;color:#166534}.error{background:#fff0f0;border:1px solid #efb1b1;color:#b42318}
@media(max-width:1050px){.filters{grid-template-columns:1fr 1fr}.filters .searchWide{grid-column:1/-1}.split{grid-template-columns:1fr}.sidebar{max-height:360px}.stats{grid-template-columns:1fr 1fr}.lessonGrid{grid-template-columns:1fr}}@media(max-width:640px){.topRow{gap:7px}.brand{font-size:17px}.brandSub{display:none}.subjectBtn{padding:7px 9px;font-size:11px}.topBtn{display:none}.filters{grid-template-columns:1fr}.metaGrid{grid-template-columns:1fr}.lessonGrid{grid-template-columns:1fr}.page{padding:0 6px 30px}}
</style>
"""


def page(html_body):
    return CSS + f'''<div class="top"><div class="topRow"><div><div class="brand">📚 LUYENDEVATLY · NGÂN HÀNG GITHUB</div><div class="brandSub">GitHub / ngan-hang/*.tex · bank_index.json · không dùng Google Sheet</div></div><div class="subjectTabs"><button class="subjectBtn" id="tabMath" onclick="pickSubject('Toán')">📐 Toán</button><button class="subjectBtn" id="tabPhys" onclick="pickSubject('Vật lý')">⚛️ Vật lí</button></div><div class="topRight"><span class="topBtn">✓ GitHub</span><a class="topBtn" href="/">⌂ Ứng dụng</a><a class="topBtn" href="/ra-de">📝 Ra đề</a></div></div></div><div class="examStrip">🗂️ Quản lý ngân hàng · Dữ liệu đọc trực tiếp từ file <b>.tex</b> trên GitHub. Chọn Môn → Khối/Lớp → Chương → Bài → Dạng → Câu.</div><div class="page">{html_body}</div>'''


@bp.get("/github/quan-ly")
def manager():
    g = guard()
    if g:
        return g
    try:
        data = load_index()
    except Exception as e:
        return page(f'<div class="message error"><b>Không đọc được bank_index.json từ GitHub:</b> {esc(e)}</div>')
    lessons = data.get("lessons", []) if isinstance(data, dict) else []
    payload = json.dumps(lessons, ensure_ascii=False).replace("</", "<\\/")
    body = f'''<div class="nav"><a class="btn" href="/">← Trang chính</a><a class="btn btnPrimary" href="/github/quan-ly">📚 Ngân hàng</a></div>
<div class="card"><div class="filters"><div class="field searchWide"><label>🔎 Tìm nhanh</label><input id="fSearch" placeholder="Tên bài, dạng bài, tên file..." oninput="renderCatalog()"></div><div class="field"><label>Môn</label><select id="fMon" onchange="onFilter('mon')"></select></div><div class="field"><label>Khối</label><select id="fKhoi" onchange="onFilter('khoi')"></select></div><div class="field"><label>Lớp</label><select id="fLop" onchange="onFilter('lop')"></select></div><div class="field"><label>Chương</label><select id="fChuong" onchange="onFilter('chuong')"></select></div><div class="field"><label>Bài học</label><select id="fBai" onchange="onFilter('bai')"></select></div><div class="field"><label>Dạng câu</label><select id="fKind" onchange="renderCatalog"><option value="">Tất cả</option><option value="A">A · Trắc nghiệm</option><option value="B">B · Đúng / Sai</option><option value="C">C · Trả lời ngắn</option><option value="D">D · Tự luận</option></select></div></div></div>
<div id="catalogIntro" class="catalogIntro"></div><div id="catalog" class="shelf"></div>
<div id="questionView" class="hidden"><div class="nav"><button class="btn" onclick="backCatalog()">← Mục lục</button><button class="btn" onclick="prevQuestion()">← Câu trước</button><button class="btn" onclick="nextQuestion()">Câu sau →</button><button class="btn btnGreen" onclick="saveCurrent()">💾 Lưu GitHub</button><button class="btn btnRed" onclick="deleteQuestion()">🗑 Xóa câu</button><button class="btn" onclick="duplicateQuestion()">⧉ Nhân bản</button></div><div class="split"><div class="card sidebar"><div class="panelTitle">📝 Danh sách câu</div><div class="qList" id="qList"></div></div><div class="card editor"><div class="editorHead"><div><div class="editorTitle" id="eTitle">Câu</div><div id="ePath" class="hint"></div></div><div id="eKind" class="tag"></div></div><div class="metaGrid"><div class="field"><label>Loại câu</label><select id="eKindSel"><option value="A">A · Trắc nghiệm</option><option value="B">B · Đúng / Sai</option><option value="C">C · Trả lời ngắn</option><option value="D">D · Tự luận</option></select></div><div class="field"><label>Mức độ</label><select id="eLevel"><option value="">—</option><option>NB</option><option>TH</option><option>VD</option><option>VDC</option></select></div><div class="field"><label>ID</label><input id="eId"></div><div class="field"><label>Dạng bài tập</label><input id="eDang"></div></div><div class="hint">🖼 Nếu câu có <b>TikZ</b> hoặc <b>includegraphics</b>, mã hình vẫn được giữ nguyên trong file .tex.</div><textarea id="eCode" class="code" spellcheck="false"></textarea></div></div></div>
<script>
const LESSONS={payload};
let state={{mon:'',khoi:'',lop:'',chuong:'',bai:'',kind:''}}, current={{path:'',sha:'',head:'',tail:'',blocks:[],qs:[],idx:0}};
function esc(s){{return String(s==null?'':s).replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]))}}
function norm(s){{try{{return String(s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/đ/g,'d').trim()}}catch(e){{return String(s||'').toLowerCase().trim()}}}}
function kindOfLesson(x){{let ds=x.dang||{{}};return Object.keys(ds)}}
function deriveKhoi(lop){{let m=String(lop||'').match(/(10|11|12)/);return m?m[1]:String(lop||'').trim()}}
function uniq(a){{return [...new Set(a.filter(x=>String(x||'').trim()))]}}
function setSel(id, vals, value, label){{let e=document.getElementById(id);let arr=uniq(vals).sort((a,b)=>String(a).localeCompare(String(b),'vi'));e.innerHTML='<option value="">'+label+'</option>'+arr.map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join('');e.value=value||''}}
function filteredLessons(){{let q=norm(document.getElementById('fSearch').value);return LESSONS.filter(x=>{{let ok=(!state.mon||x.Mon===state.mon)&&(!state.khoi||deriveKhoi(x.Lop)===state.khoi)&&(!state.lop||x.Lop===state.lop)&&(!state.chuong||x.Chuong===state.chuong)&&(!state.bai||(x.BaiHoc||x.De)===state.bai);let text=norm([x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.De,Object.keys(x.dang||{{}}).join(' ')].join(' '));return ok&&(!q||text.includes(q))}})}}
function refreshFilters(){{let all=LESSONS;let a=all.filter(x=>!state.mon||x.Mon===state.mon);setSel('fMon',all.map(x=>x.Mon),state.mon,'Tất cả môn');let b=a.filter(x=>!state.khoi||deriveKhoi(x.Lop)===state.khoi);setSel('fKhoi',a.map(x=>deriveKhoi(x.Lop)),state.khoi,'Tất cả khối');let c=b.filter(x=>!state.lop||x.Lop===state.lop);setSel('fLop',b.map(x=>x.Lop),state.lop,'Tất cả lớp');let d=c.filter(x=>!state.chuong||x.Chuong===state.chuong);setSel('fChuong',c.map(x=>x.Chuong),state.chuong,'Tất cả chương');let e=d.filter(x=>!state.bai||(x.BaiHoc||x.De)===state.bai);setSel('fBai',d.map(x=>x.BaiHoc||x.De),state.bai,'Tất cả bài')}}
function onFilter(k){{if(k==='mon'){{state.mon=document.getElementById('fMon').value;state.khoi='';state.lop='';state.chuong='';state.bai=''}}else if(k==='khoi'){{state.khoi=document.getElementById('fKhoi').value;state.lop='';state.chuong='';state.bai=''}}else if(k==='lop'){{state.lop=document.getElementById('fLop').value;state.chuong='';state.bai=''}}else if(k==='chuong'){{state.chuong=document.getElementById('fChuong').value;state.bai=''}}else if(k==='bai'){{state.bai=document.getElementById('fBai').value}}refreshFilters();renderCatalog();syncSubject()}}
function subjectName(mon){{return norm(mon).includes('toan')?'Toán':(norm(mon).includes('vat')?'Vật lý':mon)}}
function pickSubject(mon){{state.mon=mon;state.khoi='';state.lop='';state.chuong='';state.bai='';refreshFilters();document.getElementById('fMon').value=LESSONS.some(x=>x.Mon===mon)?mon:'';renderCatalog();syncSubject()}}
function syncSubject(){{let m=state.mon;document.getElementById('tabMath').classList.toggle('active',subjectName(m)==='Toán');document.getElementById('tabPhys').classList.toggle('active',subjectName(m)==='Vật lý')}}
function renderCatalog(){{let list=filteredLessons();let kind=document.getElementById('fKind').value||'';if(kind)list=list.filter(x=>Object.keys(x.dang||{{}}).some(d=>Number(x.dang[d]||0)>0)&&x._kind!==kind); // kind lọc sâu ở bước mở file; không làm mất bài
let qTotal=list.reduce((a,x)=>a+(Number(x.questions||x.count||0)),0);let mons=uniq(list.map(x=>x.Mon)).length, kh=uniq(list.map(x=>deriveKhoi(x.Lop))).length,ch=uniq(list.map(x=>x.Chuong)).length,ba=uniq(list.map(x=>x.BaiHoc||x.De)).length,dg=uniq(list.flatMap(x=>Object.keys(x.dang||{{}}))).length;document.getElementById('catalogIntro').innerHTML='<div class="introTitle">📚 Mục lục kiểu sách <span class="tag">GitHub</span></div><div style="margin-top:5px;color:#5f6f82;font-size:12px;line-height:1.45">Trong từng trang, ngân hàng được gom theo <b>Môn → Khối/Lớp → Chương → Bài</b>. Khi mở một bài, hệ thống đọc trực tiếp file <b>.tex</b> để lấy từng câu và phân loại A/B/C/D, mức độ, dạng bài.</div><div class="stats"><span class="statPill">'+mons+' môn</span><span class="statPill">'+kh+' khối</span><span class="statPill">'+ch+' chương</span><span class="statPill">'+ba+' bài</span><span class="statPill">'+dg+' dạng BT</span><span class="statPill">'+qTotal+' câu</span></div>';
if(!list.length){{document.getElementById('catalog').innerHTML='<div class="card" style="padding:35px;text-align:center;color:#738096">Không có đề phù hợp.</div>';return}}let html='<div>';let byM=new Map();list.forEach(x=>{{let k=x.Mon||'Khác';if(!byM.has(k))byM.set(k,[]);byM.get(k).push(x)}});for(let [m,ml] of byM){{let mq=ml.reduce((a,x)=>a+Number(x.questions||x.count||0),0);html+='<section class="subjectBlock"><div class="subjectHead"><span>'+esc(m)+'</span><small>'+ml.length+' bài · '+mq+' câu</small></div>';let byK=new Map();ml.forEach(x=>{{let k=deriveKhoi(x.Lop)||'?';if(!byK.has(k))byK.set(k,[]);byK.get(k).push(x)}});for(let [k,kl] of byK){{let kq=kl.reduce((a,x)=>a+Number(x.questions||x.count||0),0);html+='<div class="gradeBlock"><div class="gradeHead"><span>Khối '+esc(k)+'</span><span style="font-size:11px;color:#64748b">'+kl.length+' bài · '+kq+' câu</span></div>';let byC=new Map();kl.forEach(x=>{{let c=x.Chuong||'Chưa phân chương';if(!byC.has(c))byC.set(c,[]);byC.get(c).push(x)}});for(let [c,cl] of byC){{let cq=cl.reduce((a,x)=>a+Number(x.questions||x.count||0),0);html+='<div class="chapterBlock"><div class="chapterHead"><span>'+esc(c)+'</span><span style="font-size:11px">'+cl.length+' bài · '+cq+' câu</span></div><div class="lessonGrid">';cl.forEach(x=>{{let p=x.path||x.file||'';let title=x.BaiHoc||x.De||p;let ds=Object.keys(x.dang||{}).slice(0,4);html+='<div class="lessonCard"><div class="lessonTitle">'+esc(title)+'</div><div class="lessonSub">'+esc(x.Mon||'')+' · Lớp '+esc(x.Lop||'')+' · '+esc(c)+'</div><div class="chips"><span class="chip"><b>'+Number(x.questions||x.count||0)+'</b> câu</span>'+ds.map(d=>'<span class="chip">'+esc(d)+' · '+Number(x.dang[d]||0)+'</span>').join('')+'</div><div class="lessonActions"><button class="miniBtn" onclick="openLesson('+JSON.stringify(p)+')">📖 Mở bài</button><button class="miniBtn green" onclick="openLesson('+JSON.stringify(p)+')">✏️ Sửa câu</button></div></div>'}});html+='</div></div>'}}html+='</div>'}}html+='</div></section>'}}document.getElementById('catalog').innerHTML=html}}
async function openLesson(path){{if(!path)return;document.getElementById('catalog').classList.add('hidden');document.getElementById('catalogIntro').classList.add('hidden');document.querySelector('.filters').classList.add('hidden');document.getElementById('questionView').classList.remove('hidden');document.getElementById('qList').innerHTML='<div class="message">⏳ Đang đọc file .tex từ GitHub...</div>';try{{let r=await fetch('/github/api/file?path='+encodeURIComponent(path),{{credentials:'same-origin'}});let j=await r.json();if(!r.ok)throw new Error(j.error||'Không đọc được file');current={{path:path,sha:j.sha,head:j.head,tail:j.tail,blocks:j.blocks,qs:j.questions,idx:0}};renderQuestionList();showQuestion(0)}}catch(e){{document.getElementById('qList').innerHTML='<div class="message error">❌ '+esc(e.message||e)+'</div>'}}}}
function renderQuestionList(){{let arr=current.qs||[];document.getElementById('qList').innerHTML=arr.map((q,i)=>'<div class="qitem" id="qitem'+i+'" onclick="showQuestion('+i+')"><div class="qtop"><span class="qnum">Câu '+(i+1)+'</span><span class="kind '+String(q.kind).toLowerCase()+'">'+esc(q.kind)+' · '+esc(q.label)+'</span>'+(q.level?'<span class="tag">'+esc(q.level)+'</span>':'')+(q.has_tikz?'<span class="tag">🖼 hình</span>':'')+'</div><div class="qtitle">'+esc(q.title)+'</div><div class="qmeta">'+(q.id?'ID: '+esc(q.id):'ID: —')+(q.dang?' · '+esc(q.dang):'')+'</div></div>').join('')||'<div class="empty">File không có câu.</div>'}}
function showQuestion(i){{if(!current.qs.length)return;current.idx=Math.max(0,Math.min(i,current.qs.length-1));let q=current.qs[current.idx];document.querySelectorAll('.qitem').forEach(e=>e.classList.remove('active'));let el=document.getElementById('qitem'+current.idx);if(el)el.classList.add('active');document.getElementById('eTitle').textContent='Câu '+(current.idx+1)+' · '+(q.label||'');document.getElementById('ePath').textContent=current.path;document.getElementById('eKind').textContent=q.has_tikz?'🖼 Có hình/TikZ':'';document.getElementById('eKindSel').value=q.kind;document.getElementById('eLevel').value=q.level||'';document.getElementById('eId').value=q.id||'';document.getElementById('eDang').value=q.dang||'';document.getElementById('eCode').value=current.blocks[current.idx]||'';document.getElementById('questionView').scrollIntoView({{behavior:'smooth',block:'start'}})}}
function currentBlock(){{return current.blocks[current.idx]||''}}
function setKindInBlock(block,want){{let b=block||'',m=b.match(/\\choiceTF\\b|\\choice\\b|\\shortans\\b/i),map={{A:'\\\\choice',B:'\\\\choiceTF',C:'\\\\shortans',D:''}};if(m&&want)b=b.slice(0,m.index)+map[want]+b.slice(m.index+m[0].length);else if(m&&!want)b=b.slice(0,m.index)+b.slice(m.index+m[0].length);return b}}
async function saveCurrent(){{if(!current.blocks.length)return;let b=document.getElementById('eCode').value||'';b=setKindInBlock(b,document.getElementById('eKindSel').value);b=rebuildMetaClient(b,document.getElementById('eId').value,document.getElementById('eLevel').value,document.getElementById('eDang').value);current.blocks[current.idx]=b;let content=current.head+current.blocks.join('\\n\\n')+current.tail;try{{let r=await fetch('/github/api/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},credentials:'same-origin',body:JSON.stringify({{path:current.path,sha:current.sha,content:content,message:'ADMIN cập nhật Câu '+(current.idx+1)+' · '+current.path}})}});let j=await r.json();if(!r.ok)throw new Error(j.error||'Không lưu được');current.sha=j.sha||current.sha;document.getElementById('eCode').value=b;alert('✅ Đã lưu Câu '+(current.idx+1)+' lên GitHub.');await openLesson(current.path)}}catch(e){{alert('❌ '+(e.message||e))}}}}
function rebuildMetaClient(b,qid,level,dang){{b=b.replace(/%\\s*ID\\s*:[^\\r\\n]*\\r?\\n?/i,'').replace(/%\\s*Mức\\s*:[^\\r\\n]*\\r?\\n?/i,'').replace(/\\\\dangbt\\s*\\{{[^{{}}]*\\}}\\s*/ig,'');let m=b.match(/\\\\begin\\s*\\{{\\s*ex\\s*\\}}/i);if(!m)return b;let lines='';if(qid)lines+='% ID: '+qid+'\\n';if(level)lines+='% Mức: '+level+'\\n';if(lines)b=b.slice(0,m.index+m[0].length)+'\\n'+lines+b.slice(m.index+m[0].length);if(dang)b=b.slice(0,m.index)+'\\\\dangbt{{'+dang+'}}\\n'+b.slice(m.index);return b}}
async function duplicateQuestion(){{let b=currentBlock();if(!b)return;let n=b.replace(/%\\s*ID\\s*:[^\\r\\n]*\\r?\\n?/i,'');n=n.replace(/(%\\s*Mức\\s*:[^\\r\\n]+\\n)/i,'$1% ID: COPY_'+Date.now()+'\\n');current.blocks.splice(current.idx+1,0,n);await saveAllBlocks('ADMIN nhân bản Câu '+(current.idx+1));current.idx+=1;renderQuestionList();showQuestion(current.idx)}}
async function deleteQuestion(){{if(current.blocks.length<=1){{alert('Không xóa câu cuối cùng trong file.');return}}if(!confirm('Xóa Câu '+(current.idx+1)+' khỏi file .tex trên GitHub?'))return;current.blocks.splice(current.idx,1);current.idx=Math.max(0,Math.min(current.idx,current.blocks.length-1));await saveAllBlocks('ADMIN xóa câu khỏi '+current.path);renderQuestionList();showQuestion(current.idx)}}
async function saveAllBlocks(message){{let content=current.head+current.blocks.join('\\n\\n')+current.tail;let r=await fetch('/github/api/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},credentials:'same-origin',body:JSON.stringify({{path:current.path,sha:current.sha,content:content,message:message}})}});let j=await r.json();if(!r.ok)throw new Error(j.error||'Không lưu được');current.sha=j.sha||current.sha}}
function prevQuestion(){{showQuestion(current.idx-1)}}
function nextQuestion(){{showQuestion(current.idx+1)}}
function backCatalog(){{document.getElementById('questionView').classList.add('hidden');document.getElementById('catalog').classList.remove('hidden');document.getElementById('catalogIntro').classList.remove('hidden');document.querySelector('.filters').classList.remove('hidden');renderCatalog()}}
refreshFilters();syncSubject();renderCatalog();
</script>'''
    return page(body)


@bp.get("/github/api/file")
def api_file():
    g = guard()
    if g:
        return g
    path = request.args.get("path", "")
    if not valid_path(path):
        return jsonify({"error": "Đường dẫn file .tex không hợp lệ."}), 400
    try:
        sha, text = fetch_tex(path)
        head, blocks, tail = split_tex(text)
        qs = [qmeta(b, i + 1) for i, b in enumerate(blocks)]
        return jsonify({"ok": True, "path": path, "sha": sha, "head": head, "tail": tail, "blocks": blocks, "questions": qs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.post("/github/api/save")
def api_save():
    g = guard()
    if g:
        return g
    body = request.get_json(silent=True) or {}
    path = body.get("path", "")
    content = body.get("content", "")
    sha = body.get("sha", "")
    message = body.get("message", "ADMIN cập nhật ngân hàng GitHub")
    if not valid_path(path):
        return jsonify({"error": "Đường dẫn file .tex không hợp lệ."}), 400
    if not isinstance(content, str):
        return jsonify({"error": "Nội dung file phải là chuỗi UTF-8."}), 400
    try:
        result = save_tex(path, content, sha, message)
        return jsonify({"ok": True, "sha": result.get("content", {}).get("sha") or sha, "commit": result.get("commit", {}).get("sha", "")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


app.register_blueprint(bp)
