# -*- coding: utf-8 -*-
"""Ngân hàng GitHub — giao diện quản lý duy nhất.
Nguồn: GitHub / ngan-hang/*.tex và bank_index.json.
Không dùng Google Sheet trong màn quản lý.
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
from flask import Blueprint, Response, jsonify, redirect, request, session, url_for
from app import app

bp = Blueprint("github_manager_ui", __name__)
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = "main"


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
            raw = r.read().decode("utf-8")
            return json.loads(raw)
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
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_tex(path):
    if not path.startswith("ngan-hang/") or not path.lower().endswith(".tex") or ".." in path:
        raise RuntimeError("Đường dẫn .tex không hợp lệ")
    owner, repo = repo_parts()
    api = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(BRANCH)}"
    d = github_json(api)
    content = (d.get("content") or "").replace("\n", "")
    return d.get("sha", ""), base64.b64decode(content).decode("utf-8", "replace")


def save_tex(path, content, sha, message):
    owner, repo = repo_parts()
    api = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}"
    body = {
        "message": message or "Cập nhật file .tex từ Ngân hàng GitHub",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": sha,
    }
    return github_json(api, "PUT", body)


def split_blocks(text):
    pat = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
    ms = list(pat.finditer(text or ""))
    if not ms:
        return text or "", [], ""
    return text[:ms[0].start()], [m.group(0) for m in ms], text[ms[-1].end():]


def question_kind(block):
    if re.search(r"\\choiceTF\b", block, re.I):
        return "B", "Đúng / Sai"
    if re.search(r"\\shortans\b", block, re.I):
        return "C", "Trả lời ngắn"
    if re.search(r"\\choice\b", block, re.I):
        return "A", "Trắc nghiệm"
    return "D", "Tự luận"


def one(pattern, block):
    m = re.search(pattern, block or "", re.I)
    return m.group(1).strip() if m else ""


def question_meta(block, n):
    kind, label = question_kind(block)
    title = ""
    m = re.search(
        r"\\begin\s*\{\s*ex\s*\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{\s*ex\s*\})",
        block or "", re.I | re.S,
    )
    if m:
        title = re.sub(r"%[^\r\n]*", "", m.group(1))
        title = re.sub(r"\\dangbt\s*\{[^{}]*\}", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()
    return {
        "n": n,
        "id": one(r"%\s*ID\s*:\s*([^\r\n]+)", block),
        "level": one(r"%\s*Mức\s*:\s*([^\r\n]+)", block),
        "dang": one(r"\\dangbt\s*\{([^{}]*)\}", block) or "Chưa phân dạng",
        "kind": kind,
        "label": label,
        "title": title[:300] or "(Chưa đọc được nội dung câu)",
        "has_image": bool(re.search(r"\\begin\s*\{\s*tikzpicture\s*\}|\\includegraphics", block or "", re.I)),
    }


def type_counts(blocks):
    out = {k: 0 for k in "ABCD"}
    for b in blocks:
        out[question_kind(b)[0]] += 1
    return out


def page(body):
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ngân hàng GitHub</title>
<style>
:root{{--blue:#1769d2;--blue2:#edf5ff;--ink:#17324d;--muted:#64748b;--line:#d8e2ec;--bg:#f4f7fb;--surface:#fff;--green:#15803d;--violet:#6d28d9;--orange:#c2410c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Segoe UI,Arial,sans-serif}}a{{color:inherit}}button,input,select,textarea{{font:inherit}}.top{{background:#1769d2;color:#fff;position:sticky;top:0;z-index:30;box-shadow:0 2px 12px #0f4fa833}}.toprow{{min-height:66px;display:flex;align-items:center;gap:12px;padding:10px 16px}}.brand{{font-size:20px;font-weight:900}}.sub{{font-size:11px;opacity:.9;margin-top:2px}}.tabs{{display:flex;gap:6px;margin-left:8px}}.tab{{border:1px solid #ffffff55;background:#ffffff12;color:#fff;border-radius:12px;padding:8px 14px;font-weight:900;cursor:pointer}}.tab.active{{background:#fff;color:#1558a6}}.toplinks{{margin-left:auto;display:flex;gap:6px}}.toplinks a{{border:1px solid #ffffff44;background:#ffffff12;color:#fff;text-decoration:none;border-radius:9px;padding:7px 10px;font-size:12px;font-weight:800}}.bar{{padding:8px 16px;background:#e8f3ff;border-bottom:1px solid #cfe0f5;color:#194b83;font-size:12px}}.wrap{{max-width:1520px;margin:0 auto;padding:12px}}.toolbar{{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:9px}}.btn{{border:1px solid #cbd7e4;background:#fff;color:#174a84;border-radius:9px;padding:8px 11px;font-weight:800;cursor:pointer;text-decoration:none;font-size:12px}}.btn.primary{{background:#1769d2;color:#fff;border-color:#1769d2}}.btn.green{{background:#eaf8ef;color:#166534;border-color:#86efac}}.btn.red{{background:#fff3f3;color:#b42318;border-color:#efb0b0}}.card{{background:var(--surface);border:1px solid var(--line);border-radius:15px;box-shadow:0 2px 9px #17324d0a}}.filters{{display:grid;grid-template-columns:1.5fr repeat(5,1fr);gap:8px;padding:11px}}.field label{{display:block;font-size:11px;font-weight:900;color:#526174;margin-bottom:4px}}.field input,.field select{{width:100%;border:1px solid #cad6e2;border-radius:8px;background:#fff;padding:8px;color:var(--ink)}}.intro{{margin-top:10px;padding:11px 13px;border:1px solid #cbe0f9;background:linear-gradient(180deg,#eff6ff,#fff);border-radius:15px}}.introTitle{{font-weight:950;color:#1e3a8a;font-size:16px}}.pills{{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}}.pill{{border:1px solid #bfdbfe;background:#fff;border-radius:999px;padding:4px 8px;font-size:11px;font-weight:900;color:#1d4ed8}}.shelf{{margin-top:10px}}.subject{{margin-bottom:14px}}.subjectHead{{padding:10px 13px;border-radius:13px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-size:16px;font-weight:950;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}}.grade{{margin-top:9px;border:1px solid #cfd9e4;border-radius:14px;overflow:hidden;background:#fff}}.gradeHead{{padding:9px 12px;background:#f1f5f9;font-weight:950;display:flex;justify-content:space-between}}.chapter{{margin:9px;border:1px solid #bdd8f6;border-radius:13px;overflow:hidden;background:#f8fbff}}.chapterHead{{padding:9px 11px;background:#dbeafe;color:#1e3a8a;font-weight:950;display:flex;justify-content:space-between}}.grid{{padding:9px;display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:9px}}.lesson{{border:1px solid #dfe7ef;border-radius:13px;background:#fff;padding:10px;display:flex;flex-direction:column;gap:7px}}.lessonTitle{{font-weight:950;line-height:1.3}}.lessonSub{{font-size:11px;color:#64748b}}.chips{{display:flex;gap:5px;flex-wrap:wrap}}.chip{{border:1px solid #d5dee8;background:#f8fafc;border-radius:999px;padding:4px 7px;font-size:10px;font-weight:850}}.chipA{{background:#eff6ff;color:#1d4ed8;border-color:#93c5fd}}.chipB{{background:#f5f3ff;color:#6d28d9;border-color:#c4b5fd}}.chipC{{background:#ecfdf5;color:#15803d;border-color:#86efac}}.chipD{{background:#fff7ed;color:#c2410c;border-color:#fdba74}}.dangbox{{border:1px solid #b9d6f6;background:#f8fbff;border-radius:10px;padding:7px}}.dangtitle{{font-size:11px;font-weight:950;color:#1e3a8a;margin-bottom:5px}}.dangrow{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px;align-items:center;border:1px solid #dbeafe;background:#fff;border-radius:8px;padding:6px 7px;margin:4px 0;cursor:pointer}}.dangrow:hover{{background:#eff6ff;border-color:#60a5fa}}.dangname{{font-size:10.5px;font-weight:850;line-height:1.3}}.dangmeta{{display:flex;flex-wrap:wrap;gap:3px;justify-content:flex-end}}.tiny{{border-radius:999px;padding:3px 5px;font-size:9px;font-weight:900;border:1px solid #d7dee7;background:#f8fafc;color:#475569}}.tinyA{{background:#eff6ff;color:#1d4ed8;border-color:#93c5fd}}.tinyB{{background:#f5f3ff;color:#6d28d9;border-color:#c4b5fd}}.tinyC{{background:#ecfdf5;color:#15803d;border-color:#86efac}}.tinyD{{background:#fff7ed;color:#c2410c;border-color:#fdba74}}.tinyT{{background:#eaf2ff;color:#1e3a8a;border-color:#bfdbfe}}.actions{{display:flex;gap:5px;flex-wrap:wrap}}.mini{{border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:8px;padding:5px 8px;font-size:10.5px;font-weight:900;cursor:pointer}}.empty{{padding:30px;text-align:center;color:#64748b}}.hidden{{display:none!important}}.editorGrid{{display:grid;grid-template-columns:330px 1fr;gap:10px}}.qlist{{max-height:calc(100vh - 175px);overflow:auto;padding:8px}}.qitem{{border:1px solid #e0e7ef;border-radius:9px;padding:8px;margin:5px 0;background:#fff;cursor:pointer}}.qitem.active,.qitem:hover{{background:#edf5ff;border-color:#8bb9ed}}.qtop{{display:flex;gap:4px;flex-wrap:wrap;align-items:center}}.qnum{{font-weight:950;color:#145bb0;font-size:11px}}.qtitle{{font-size:11px;font-weight:750;line-height:1.35;margin-top:3px}}.qmeta{{font-size:9.5px;color:#64748b;margin-top:3px}}.editor{{padding:12px}}.editorHead{{display:flex;justify-content:space-between;gap:7px;align-items:flex-start}}.editorTitle{{font-size:18px;font-weight:950}}.metaGrid{{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:9px 0}}.code{{width:100%;min-height:560px;border:1px solid #becddd;border-radius:9px;padding:11px;background:#fcfdff;font:13px/1.55 Consolas,monospace;resize:vertical}}.status{{margin:8px 0;padding:8px 10px;border-radius:8px;font-size:11px}}.ok{{background:#eaf8ef;border:1px solid #a7d8b6;color:#166534}}.err{{background:#fff0f0;border:1px solid #efb1b1;color:#b42318}}@media(max-width:1000px){{.filters{{grid-template-columns:1fr 1fr}}.grid{{grid-template-columns:1fr}}.editorGrid{{grid-template-columns:1fr}}.qlist{{max-height:330px}}}}@media(max-width:650px){{.toplinks{{display:none}}.filters{{grid-template-columns:1fr}}.metaGrid{{grid-template-columns:1fr}}.wrap{{padding:7px}}}}
</style></head><body>{body}</body></html>'''


@bp.get("/github/quan-ly")
def manager():
    g = guard()
    if g:
        return g
    try:
        data = load_index()
    except Exception as e:
        return page(f'<div class="wrap"><div class="status err">❌ Không đọc được bank_index.json từ GitHub: {esc(e)}</div></div>')
    lessons = data.get("lessons") or []
    payload = json.dumps(lessons, ensure_ascii=False).replace("</", "<\\/")
    requested_path = request.args.get("path", "")
    requested_dang = request.args.get("dang", "")
    boot = json.dumps({"path": requested_path, "dang": requested_dang}, ensure_ascii=False).replace("</", "<\\/")
    body = f'''<div class="top"><div class="toprow"><div><div class="brand">📚 LUYỆN ĐỀ AI · NGÂN HÀNG GITHUB</div><div class="sub">Đọc trực tiếp GitHub / ngan-hang/*.tex · bank_index.json · không dùng Google Sheet</div></div><div class="tabs"><button class="tab active" id="tabMath" onclick="pickSubject('Toán')">📐 Toán</button><button class="tab" id="tabPhys" onclick="pickSubject('Vật lý')">⚛️ Vật lí</button></div><div class="toplinks"><a href="/">⌂ Ứng dụng</a><a href="/ra-de">📝 Ra đề</a></div></div><div class="bar">🗂️ Mục lục → Bài → <b>Dạng bài tập</b> → chọn đúng loại → xem/sửa từng câu. Dữ liệu câu hỏi lấy từ file <b>.tex</b> trên GitHub.</div></div>
<div class="wrap"><div class="toolbar"><a class="btn" href="/">← Trang chính</a><a class="btn primary" href="/github/quan-ly">📚 Mục lục GitHub</a><button class="btn" onclick="openCurrentPath()">✏️ Mở bài đang chọn</button></div>
<div class="card"><div class="filters"><div class="field"><label>🔎 Tìm nhanh</label><input id="fSearch" placeholder="Tên bài, dạng bài, file .tex..." oninput="renderCatalog()"></div><div class="field"><label>Môn</label><select id="fMon" onchange="onFilter('mon')"></select></div><div class="field"><label>Khối</label><select id="fKhoi" onchange="onFilter('khoi')"></select></div><div class="field"><label>Lớp</label><select id="fLop" onchange="onFilter('lop')"></select></div><div class="field"><label>Chương</label><select id="fChuong" onchange="onFilter('chuong')"></select></div><div class="field"><label>Bài</label><select id="fBai" onchange="onFilter('bai')"></select></div><div class="field"><label>Loại câu</label><select id="fKind" onchange="renderCatalog()"><option value="">Tất cả</option><option value="A">A · Trắc nghiệm</option><option value="B">B · Đúng / Sai</option><option value="C">C · Trả lời ngắn</option><option value="D">D · Tự luận</option></select></div></div></div>
<div id="catalogIntro" class="intro"></div><div id="catalog" class="shelf"></div>
<div id="editorView" class="hidden"><div class="toolbar"><button class="btn" onclick="backCatalog()">← Quay lại mục lục</button><button class="btn" onclick="prevQuestion()">← Câu trước</button><button class="btn" onclick="nextQuestion()">Câu sau →</button><button class="btn green" onclick="saveQuestion()">💾 Lưu GitHub</button><button class="btn" onclick="newQuestion()">➕ Thêm câu</button><button class="btn" onclick="duplicateQuestion()">⧉ Nhân bản</button></div><div class="editorGrid"><div class="card"><div class="panelTitle" style="padding:12px 13px;font-weight:950;border-bottom:1px solid #e7edf3">📝 Câu hỏi trong file</div><div id="qList" class="qlist"></div></div><div class="card editor"><div class="editorHead"><div><div id="eTitle" class="editorTitle">Câu</div><div id="ePath" class="qmeta"></div></div><div id="eBadge" class="pill"></div></div><div class="metaGrid"><div class="field"><label>Loại câu</label><select id="eKind"><option value="A">A · Trắc nghiệm</option><option value="B">B · Đúng / Sai</option><option value="C">C · Trả lời ngắn</option><option value="D">D · Tự luận</option></select></div><div class="field"><label>Mức độ</label><input id="eLevel" placeholder="NB / TH / VD / VDC"></div><div class="field"><label>ID</label><input id="eId"></div><div class="field"><label>Dạng bài tập</label><input id="eDang"></div></div><div class="status">🖼 TikZ / includegraphics được giữ nguyên trong block .tex. Sửa xong bấm <b>Lưu GitHub</b>.</div><textarea id="eCode" class="code" spellcheck="false"></textarea><div id="saveStatus"></div></div></div></div>
<script>
const LESSONS={payload};
const BOOT={boot};
let state={{mon:'',khoi:'',lop:'',chuong:'',bai:'',kind:''}};
let current={{path:'',sha:'',head:'',tail:'',blocks:[],qs:[],idx:0}};
const esc=s=>String(s==null?'':s).replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]));
const escAttr=esc;
const norm=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/đ/g,'d').trim();
const uniq=a=>[...new Set(a.filter(x=>String(x||'').trim()))];
function deriveKhoi(lop){{let m=String(lop||'').match(/(10|11|12)/);return m?m[1]:String(lop||'').trim()}}
function subjectName(m){{let n=norm(m);return n.includes('toan')?'Toán':(n.includes('vat')?'Vật lý':m)}}
function setSel(id,vals,value,label){{let el=document.getElementById(id),arr=uniq(vals).sort((a,b)=>String(a).localeCompare(String(b),'vi'));el.innerHTML='<option value="">'+label+'</option>'+arr.map(v=>'<option value="'+escAttr(v)+'">'+esc(v)+'</option>').join('');el.value=value||''}}
function filteredLessons(){{let q=norm(document.getElementById('fSearch').value);return LESSONS.filter(x=>{{let ok=(!state.mon||x.Mon===state.mon)&&(!state.khoi||deriveKhoi(x.Lop)===state.khoi)&&(!state.lop||x.Lop===state.lop)&&(!state.chuong||x.Chuong===state.chuong)&&(!state.bai||(x.BaiHoc||x.De)===state.bai);let text=norm([x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.De,x.path,Object.keys(x.dang||{{}}).join(' ')].join(' '));return ok&&(!q||text.includes(q))}})}}
function refreshFilters(){{let a=LESSONS.filter(x=>!state.mon||x.Mon===state.mon);setSel('fMon',LESSONS.map(x=>x.Mon),state.mon,'Tất cả môn');let b=a.filter(x=>!state.khoi||deriveKhoi(x.Lop)===state.khoi);setSel('fKhoi',a.map(x=>deriveKhoi(x.Lop)),state.khoi,'Tất cả khối');let c=b.filter(x=>!state.lop||x.Lop===state.lop);setSel('fLop',b.map(x=>x.Lop),state.lop,'Tất cả lớp');let d=c.filter(x=>!state.chuong||x.Chuong===state.chuong);setSel('fChuong',c.map(x=>x.Chuong),state.chuong,'Tất cả chương');let e=d.filter(x=>!state.bai||(x.BaiHoc||x.De)===state.bai);setSel('fBai',d.map(x=>x.BaiHoc||x.De),state.bai,'Tất cả bài')}}
function onFilter(k){{if(k==='mon'){{state.mon=document.getElementById('fMon').value;state.khoi=state.lop=state.chuong=state.bai=''}}else if(k==='khoi'){{state.khoi=document.getElementById('fKhoi').value;state.lop=state.chuong=state.bai=''}}else if(k==='lop'){{state.lop=document.getElementById('fLop').value;state.chuong=state.bai=''}}else if(k==='chuong'){{state.chuong=document.getElementById('fChuong').value;state.bai=''}}else if(k==='bai')state.bai=document.getElementById('fBai').value;refreshFilters();renderCatalog();syncTabs()}}
function pickSubject(mon){{state.mon=LESSONS.some(x=>x.Mon===mon)?mon:'';state.khoi=state.lop=state.chuong=state.bai='';refreshFilters();renderCatalog();syncTabs()}}
function syncTabs(){{let m=subjectName(state.mon);document.getElementById('tabMath').classList.toggle('active',m==='Toán');document.getElementById('tabPhys').classList.toggle('active',m==='Vật lý')}}
function kindCountForLesson(x){{let out={{A:0,B:0,C:0,D:0}};Object.keys(x.dang||{{}}).forEach(d=>{{}});return out}}
function renderDangButtons(x){{let rows=Object.entries(x.dang||{{}}).filter(([d,n])=>Number(n||0)>0);if(!rows.length)return '<div class="dangbox"><div class="dangtitle">🏷️ Dạng bài tập</div><div style="font-size:10px;color:#9a3412">Chưa có dữ liệu dạng trong index</div></div>';return '<div class="dangbox"><div class="dangtitle">🏷️ DẠNG BÀI TẬP — bấm một dạng để chọn</div>'+rows.map(([d,n])=>'<div class="dangrow" data-path="'+escAttr(x.path||x.file||'')+'" data-dang="'+escAttr(d)+'"><div class="dangname">'+esc(d)+'</div><div class="dangmeta"><span class="tiny tinyT">Tổng '+Number(n||0)+'</span></div></div>').join('')+'</div>'}}
function renderCatalog(){{let list=filteredLessons();let kind=document.getElementById('fKind').value||'';if(kind){{list=list.filter(x=>Object.entries(x.dang||{{}}).some(([d,n])=>Number(n)>0))}}let qt=list.reduce((a,x)=>a+Number(x.questions||x.count||0),0);let ds=uniq(list.flatMap(x=>Object.keys(x.dang||{{}})));document.getElementById('catalogIntro').innerHTML='<div class="introTitle">📚 Mục lục kiểu sách <span class="pill">GitHub</span></div><div style="margin-top:4px;font-size:12px;color:#607083">Chọn <b>Môn → Khối → Chương → Bài</b>. Trong từng bài, từng <b>Dạng bài tập</b> là một vùng chọn riêng. Khi bấm dạng, hệ thống mở đúng file <b>.tex</b> và lọc đúng các câu thuộc dạng đó.</div><div class="pills"><span class="pill">'+uniq(list.map(x=>x.Mon)).length+' môn</span><span class="pill">'+uniq(list.map(x=>deriveKhoi(x.Lop))).length+' khối</span><span class="pill">'+uniq(list.map(x=>x.Chuong)).length+' chương</span><span class="pill">'+uniq(list.map(x=>x.BaiHoc||x.De)).length+' bài</span><span class="pill">'+ds.length+' dạng BT</span><span class="pill">'+qt+' câu</span></div>';
if(!list.length){{document.getElementById('catalog').innerHTML='<div class="card empty">Không có dữ liệu phù hợp.</div>';return}}
let out='';let mons=new Map();list.forEach(x=>{{let k=x.Mon||'Khác';if(!mons.has(k))mons.set(k,[]);mons.get(k).push(x)}});for(let [m,ml] of mons){{out+='<section class="subject"><div class="subjectHead"><span>'+esc(m)+'</span><span style="font-size:11px">'+ml.length+' bài · '+ml.reduce((a,x)=>a+Number(x.questions||x.count||0),0)+' câu</span></div>';let grades=new Map();ml.forEach(x=>{{let k=deriveKhoi(x.Lop)||'?';if(!grades.has(k))grades.set(k,[]);grades.get(k).push(x)}});for(let [g,gl] of grades){{out+='<div class="grade"><div class="gradeHead"><span>Khối '+esc(g)+'</span><span style="font-size:11px;color:#64748b">'+gl.length+' bài</span></div>';let chs=new Map();gl.forEach(x=>{{let k=x.Chuong||'Chưa phân chương';if(!chs.has(k))chs.set(k,[]);chs.get(k).push(x)}});for(let [c,cl] of chs){{out+='<div class="chapter"><div class="chapterHead"><span>'+esc(c)+'</span><span style="font-size:11px">'+cl.length+' bài · '+cl.reduce((a,x)=>a+Number(x.questions||x.count||0),0)+' câu</span></div><div class="grid">';for(let x of cl){{let p=x.path||x.file||'';let title=x.BaiHoc||x.De||p;out+='<div class="lesson"><div class="lessonTitle">'+esc(title)+'</div><div class="lessonSub">'+esc(x.Mon||'')+' · Lớp '+esc(x.Lop||'')+' · '+esc(c)+'</div><div class="chips"><span class="chip">'+Number(x.questions||x.count||0)+' câu</span>'+Object.entries(x.dang||{{}}).slice(0,4).map(([d,n])=>'<span class="chip">'+esc(d)+' · '+Number(n||0)+'</span>').join('')+'</div>'+renderDangButtons(x)+'<div class="actions"><button class="mini" onclick="openLesson('+JSON.stringify(p)+')">📖 Mở bài</button><button class="mini" onclick="openLesson('+JSON.stringify(p)+')">✏️ Sửa câu</button></div></div>'}}out+='</div></div>'}}out+='</div>'}}out+='</section>'}}document.getElementById('catalog').innerHTML=out}}
async function openLesson(path,dang){{if(!path)return;document.getElementById('catalog').classList.add('hidden');document.getElementById('catalogIntro').classList.add('hidden');document.querySelector('.filters').classList.add('hidden');document.querySelector('.toolbar').classList.add('hidden');document.getElementById('editorView').classList.remove('hidden');document.getElementById('qList').innerHTML='<div class="status">⏳ Đang đọc file .tex từ GitHub...</div>';try{{let u='/github/api/file?path='+encodeURIComponent(path);let r=await fetch(u,{{credentials:'same-origin'}});let j=await r.json();if(!r.ok)throw new Error(j.error||'Không đọc được file');current={{path:path,sha:j.sha,head:j.head,tail:j.tail,blocks:j.blocks,qs:j.questions,idx:0}};if(dang){{let i=(current.qs||[]).findIndex(q=>norm(q.dang)===norm(dang));if(i>=0)current.idx=i}}renderQuestions();showQuestion(current.idx)}}catch(e){{document.getElementById('qList').innerHTML='<div class="status err">❌ '+esc(e.message||e)+'</div>'}}}}
function renderQuestions(){{let arr=current.qs||[];document.getElementById('qList').innerHTML=arr.map((q,i)=>'<div class="qitem" id="q'+i+'" onclick="showQuestion('+i+')"><div class="qtop"><span class="qnum">Câu '+(i+1)+'</span><span class="pill">'+esc(q.kind)+' · '+esc(q.label)+'</span>'+(q.level?'<span class="pill">'+esc(q.level)+'</span>':'')+(q.has_image?'<span class="pill">🖼</span>':'')+'</div><div class="qtitle">'+esc(q.title)+'</div><div class="qmeta">'+esc(q.dang)+' · '+esc(q.id||'Chưa có ID')+'</div></div>').join('')||'<div class="status err">File không có block \\begin{{ex}}...\\end{{ex}}.</div>'}}
function showQuestion(i){{if(!current.qs||!current.qs.length)return;i=Math.max(0,Math.min(i,current.qs.length-1));current.idx=i;let q=current.qs[i];document.querySelectorAll('.qitem').forEach(e=>e.classList.remove('active'));let row=document.getElementById('q'+i);if(row){{row.classList.add('active');row.scrollIntoView({{block:'nearest'}})}}document.getElementById('eTitle').textContent='Câu '+(i+1)+' — '+(q.label||'');document.getElementById('ePath').textContent=current.path;document.getElementById('eBadge').textContent=q.dang||'Chưa phân dạng';document.getElementById('eKind').value=q.kind||'D';document.getElementById('eLevel').value=q.level||'';document.getElementById('eId').value=q.id||'';document.getElementById('eDang').value=q.dang||'Chưa phân dạng';document.getElementById('eCode').value=current.blocks[i]||'';document.getElementById('saveStatus').innerHTML=''}}
function prevQuestion(){{showQuestion(current.idx-1)}}function nextQuestion(){{showQuestion(current.idx+1)}}
function backCatalog(){{history.replaceState(null,'','/github/quan-ly');location.reload()}}
function openCurrentPath(){{if(current.path)openLesson(current.path);else alert('Chưa mở bài nào.')}}
async function saveQuestion(){{let block=current.blocks[current.idx]||document.getElementById('eCode').value||'';let code=document.getElementById('eCode').value||'';let qid=document.getElementById('eId').value.trim();let level=document.getElementById('eLevel').value.trim();let dang=document.getElementById('eDang').value.trim();let clean=code.replace(/%\\s*ID\\s*:[^\\r\\n]*\\r?\\n?/ig,'').replace(/%\\s*Mức\\s*:[^\\r\\n]*\\r?\\n?/ig,'').replace(/\\\\dangbt\\s*\\{{1}[^\\{{}]*\\}}\\s*/ig,'');let m=clean.match(/\\\\begin\\s*\\{{1}\\s*ex\\s*\\}}/i);if(!m){{alert('Không tìm thấy \\begin{{ex}} trong câu.');return}}let meta='';if(qid)meta+='% ID: '+qid+'\\n';if(level)meta+='% Mức: '+level+'\\n';if(dang)meta+='\\\\dangbt{'+dang+'}\\n';clean=clean.slice(0,m.index+m[0].length)+'\\n'+meta+clean.slice(m.index+m[0].length);current.blocks[current.idx]=clean;let full=current.head+current.blocks.join('\\n\\n')+current.tail;try{{let r=await fetch('/github/api/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{path:current.path,sha:current.sha,content:full,message:'Sửa câu '+(current.idx+1)+' trong '+current.path}}),credentials:'same-origin'}});let j=await r.json();if(!r.ok)throw new Error(j.error||'Lưu thất bại');current.sha=j.sha;current.blocks[current.idx]=clean;showQuestion(current.idx);document.getElementById('saveStatus').innerHTML='<div class="status ok">✅ Đã lưu trực tiếp vào GitHub.</div>'}}catch(e){{document.getElementById('saveStatus').innerHTML='<div class="status err">❌ '+esc(e.message||e)+'</div>'}}}}
function newQuestion(){{alert('Chọn một câu gần giống → Nhân bản. Chức năng thêm block mới sẽ được bổ sung sau khi luồng sửa đã ổn định.')}}function duplicateQuestion(){{if(!current.blocks.length)return;let b=current.blocks[current.idx]||'';let nid=(document.getElementById('eId').value||'').replace(/[^A-Za-z0-9_-]/g,'')+'_COPY';let cp=b.replace(/%\\s*ID\\s*:[^\\r\\n]*/i,'% ID: '+nid);current.blocks.splice(current.idx+1,0,cp);current.qs.splice(current.idx+1,0,{{...current.qs[current.idx],id:nid,n:current.idx+2,title:current.qs[current.idx].title+' (bản sao)'}});renderQuestions();showQuestion(current.idx+1)}}
function boot(){{refreshFilters();let first=LESSONS.find(x=>subjectName(x.Mon)==='Toán');state.mon=first?first.Mon:'';refreshFilters();renderCatalog();syncTabs();if(BOOT.path)setTimeout(()=>openLesson(BOOT.path,BOOT.dang),120)}}
document.addEventListener('click',e=>{{let r=e.target.closest('.dangrow');if(r){{e.preventDefault();e.stopPropagation();openLesson(r.getAttribute('data-path')||'',r.getAttribute('data-dang')||'')}}}});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
</script></div>'''
    return page(body)


@bp.get("/github/api/file")
def api_file():
    g = guard()
    if g:
        return g
    path = request.args.get("path", "")
    try:
        sha, text = fetch_tex(path)
        head, blocks, tail = split_blocks(text)
        qs = [question_meta(b, i + 1) for i, b in enumerate(blocks)]
        dang = request.args.get("dang", "")
        if dang:
            qs = [q for q in qs if str(q.get("dang", "")).strip().lower() == dang.strip().lower()]
        return jsonify({"ok": True, "path": path, "sha": sha, "head": head, "tail": tail, "blocks": blocks, "questions": qs})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@bp.post("/github/api/save")
def api_save():
    g = guard()
    if g:
        return g
    try:
        body = request.get_json(silent=True) or {}
        path = str(body.get("path") or "")
        sha = str(body.get("sha") or "")
        content = str(body.get("content") or "")
        if not sha:
            return jsonify({"ok": False, "error": "Thiếu SHA hiện tại của file GitHub."}), 400
        r = save_tex(path, content, sha, str(body.get("message") or "Cập nhật ngân hàng GitHub"))
        return jsonify({"ok": True, "sha": r.get("content", {}).get("sha", "") or r.get("commit", {}).get("sha", "")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
