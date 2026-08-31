# -*- coding: utf-8 -*-
"""NGÂN HÀNG GITHUB - giao diện gọn, nhanh.
Nguồn chính duy nhất: bank_index.json + ngan-hang/**/*.tex.
Google Sheet không được gọi trong module này.

Thiết kế tốc độ:
- Mở trang: chỉ đọc bank_index.json -> không đọc 85 file .tex.
- Bấm một Bài: mới đọc đúng 1 file .tex từ GitHub.
- Dạng bài tập: lấy từ bank_index; A/B/C/D được tính khi mở bài từ .tex.
- Sửa/Lưu: commit trực tiếp đúng file .tex lên GitHub.
"""
from __future__ import annotations
import base64, html, json, os, re, urllib.error, urllib.parse, urllib.request
from typing import Any
from flask import Blueprint, Response, jsonify, request, session
from app import app

bp = Blueprint("github_bank_fast", __name__)
REPO=(os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH=(os.getenv("GITHUB_BRANCH") or "main").strip() or "main"
TOKEN=(os.getenv("GITHUB_TOKEN") or "").strip()
RAW_BASE="https://raw.githubusercontent.com"
API_BASE="https://api.github.com"
INDEX_PATH="bank_index.json"
INDEX_CACHE={"text":None}

def _clean(v): return str(v or "").strip()
def _valid_tex(p): return p.startswith("ngan-hang/") and p.lower().endswith(".tex") and ".." not in p

def _repo_parts():
    if "/" not in REPO: raise RuntimeError("GITHUB_REPO phải có dạng owner/repository")
    return REPO.split("/",1)

def _raw(path):
    o,r=_repo_parts(); u=f"{RAW_BASE}/{o}/{r}/{urllib.parse.quote(BRANCH)}/{urllib.parse.quote(path,safe='/')}"
    with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"ldvl-github-bank"}),timeout=12) as x: return x.read().decode("utf-8","replace")

def _index():
    if INDEX_CACHE["text"] is None: INDEX_CACHE["text"]=json.loads(_raw(INDEX_PATH))
    return INDEX_CACHE["text"]

def _gh(path,method="GET",payload=None):
    if not TOKEN: raise RuntimeError("Render chưa có GITHUB_TOKEN")
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(API_BASE+path,data=data,method=method,headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"ldvl-github-bank","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=18) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:m=json.loads(e.read().decode()).get("message",str(e))
        except Exception:m=str(e)
        raise RuntimeError(f"GitHub API {e.code}: {m}")

def _get_tex(path):
    if not _valid_tex(path): raise RuntimeError("Đường dẫn .tex không hợp lệ")
    o,r=_repo_parts(); api=f"/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(BRANCH)}"; d=_gh(api)
    return _clean(d.get("sha")),base64.b64decode((d.get("content") or "").replace("\n","")).decode("utf-8","replace")

def _save_tex(path,text,sha,msg):
    if not _valid_tex(path): raise RuntimeError("Đường dẫn .tex không hợp lệ")
    o,r=_repo_parts(); api=f"/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe='/')}"
    return _gh(api,"PUT",{"message":msg or "Cập nhật ngân hàng câu hỏi .tex","content":base64.b64encode(text.encode()).decode("ascii"),"branch":BRANCH,"sha":sha})

def _kind(b):
    if re.search(r"\\choiceTF\b",b,re.I): return "B"
    if re.search(r"\\shortans\b",b,re.I): return "C"
    if re.search(r"\\choice\b",b,re.I): return "A"
    return "D"

def _level(b):
    m=re.search(r"%\s*Mức\s*:\s*([^\r\n%]+)",b,re.I); return _clean(m.group(1)).upper() if m else ""

def _qid(b):
    m=re.search(r"%\s*ID\s*:\s*([^\r\n%]+)",b,re.I); return _clean(m.group(1)) if m else ""

def _dang(text,start):
    ms=list(re.finditer(r"\\dangbt\s*\{([^{}]*)\}",text[:start],re.I))
    if not ms:return "Chưa phân dạng"
    x=_clean(ms[-1].group(1)); return x if x and x.casefold() not in {"chưa có dạng","chua co dang","chưa phân dạng","chua phan dang"} else "Chưa phân dạng"

def _blocks(text):
    pat=re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}",re.I);out=[]
    for n,m in enumerate(pat.finditer(text or ""),1):
        b=m.group(0); tm=_kind(b); lv=_level(b); im=_qid(b); dm=_dang(text,m.start())
        xm=re.search(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{\s*ex\s*\})",b,re.I)
        title=xm.group(1) if xm else ""; title=re.sub(r"%[^\r\n]*","",title); title=re.sub(r"\\dangbt\s*\{[^{}]*\}","",title,flags=re.I); title=re.sub(r"\s+"," ",title).strip()
        out.append({"n":n,"id":im,"level":lv,"dang":dm,"kind":tm,"title":title[:260],"image":bool(re.search(r"\\begin\s*\{\s*tikzpicture|\\includegraphics",b,re.I)),"text":b})
    return out

def _catalog_rows():
    rows=[]
    for x in _index().get("lessons") or []:
        p=_clean(x.get("github") or x.get("path") or x.get("file"));
        if not p: continue
        if not p.startswith("ngan-hang/"):p="ngan-hang/"+p.lstrip("/")
        raw=x.get("dang") or {}; ds=[]
        if isinstance(raw,dict):
            for k,v in raw.items():
                try:n=int(v or 0)
                except:n=0
                if n>0: ds.append({"name":_clean(k) or "Chưa phân dạng","count":n})
        rows.append({"Mon":_clean(x.get("Mon")),"Lop":_clean(x.get("Lop")),"Chuong":_clean(x.get("Chuong")),"BaiHoc":_clean(x.get("BaiHoc") or x.get("De")) or p,"path":p,"count":int(x.get("count_questions") or x.get("questions") or x.get("count") or 0),"dang":ds})
    return rows

def _guard():
    if not session.get("mahs"): return None
    try:
        from app import is_admin
        if not is_admin(): return Response("<h3>403 — Chỉ ADMIN được quản lý ngân hàng GitHub.</h3>",403,mimetype="text/html")
    except Exception: pass
    return None

@bp.get("/github/quan-ly")
def page():
    bad=_guard(); return bad if bad else Response(PAGE,mimetype="text/html")

@bp.get("/github/api/catalog-fast")
def api_catalog():
    rows=_catalog_rows(); idx=_index(); return jsonify({"ok":True,"source":"GitHub","total_files":int(idx.get("total_files") or idx.get("count") or len(rows)),"total_questions":int(idx.get("total_questions") or sum(x["count"] for x in rows)),"lessons":rows})

@bp.get("/github/api/tex-fast")
def api_tex():
    bad=_guard();
    if bad:return jsonify({"ok":False,"error":"Không có quyền"}),403
    try:
        p=_clean(request.args.get("path")); sha,text=_get_tex(p); qs=_blocks(text); st={k:0 for k in "ABCD"}; lv={k:0 for k in ("NB","TH","VD","VDC")}; dm={}
        for q in qs:
            st[q["kind"]]+=1
            for k in lv:
                if re.search(r"\b"+re.escape(k)+r"\b",q["level"]):lv[k]+=1
            z=dm.setdefault(q["dang"],{"total":0,"A":0,"B":0,"C":0,"D":0});z["total"]+=1;z[q["kind"]]+=1
        return jsonify({"ok":True,"path":p,"sha":sha,"text":text,"questions":qs,"stats":st,"levels":lv,"dang":dm})
    except Exception as e:return jsonify({"ok":False,"error":str(e)}),400

@bp.post("/github/api/save-tex-fast")
def api_save():
    bad=_guard();
    if bad:return jsonify({"ok":False,"error":"Không có quyền"}),403
    d=request.get_json(silent=True) or {};p=_clean(d.get("path"));text=d.get("text");sha=_clean(d.get("sha"))
    if not _valid_tex(p) or not isinstance(text,str) or not sha:return jsonify({"ok":False,"error":"Thiếu path/text/sha"}),400
    try:
        r=_save_tex(p,text,sha,_clean(d.get("message")));INDEX_CACHE["text"]=None;return jsonify({"ok":True,"commit":_clean((r.get("commit") or {}).get("sha")),"content_sha":_clean((r.get("content") or {}).get("sha"))})
    except Exception as e:return jsonify({"ok":False,"error":str(e)}),409

app.register_blueprint(bp)

PAGE=r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ngân hàng đề GitHub</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f8fc;color:#17324d;font:14px Segoe UI,Arial,sans-serif}button,input,select,textarea{font:inherit}.top{background:#1769d2;color:#fff;padding:11px 16px;position:sticky;top:0;z-index:20;box-shadow:0 2px 10px #17324d22}.toprow{display:flex;align-items:center;gap:12px}.brand{font-weight:950;font-size:20px}.sub{font-size:11px;opacity:.9}.source{margin-left:auto;border:1px solid #ffffff55;padding:7px 10px;border-radius:9px;font-size:11px;font-weight:900}.wrap{max-width:1550px;margin:auto;padding:12px}.tools{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:9px}.btn{border:1px solid #cbd7e4;background:#fff;color:#174a84;padding:8px 11px;border-radius:9px;font-weight:850;cursor:pointer;font-size:12px}.btn.primary{background:#1769d2;color:#fff;border-color:#1769d2}.btn.green{background:#eaf8ef;color:#166534;border-color:#86efac}.filters{display:grid;grid-template-columns:1.7fr 1fr 1fr 1.5fr 1.5fr;gap:8px;background:#fff;border:1px solid #d7e1eb;border-radius:14px;padding:10px}.field label{display:block;font-size:10px;font-weight:900;color:#64748b;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px}.intro{margin-top:9px;padding:10px 12px;border:1px solid #c7defa;background:linear-gradient(#eff6ff,#fff);border-radius:14px}.stats{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}.pill{border:1px solid #bfdbfe;background:#fff;color:#1d4ed8;border-radius:999px;padding:4px 8px;font-size:10px;font-weight:900}.subject{margin-top:10px}.subjectHead{padding:10px 12px;border-radius:12px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:950;display:flex;justify-content:space-between}.grade{margin-top:8px;border:1px solid #d0dae5;border-radius:12px;background:#fff;overflow:hidden}.gradeHead{padding:8px 11px;background:#f1f5f9;font-weight:900}.chapter{margin:8px;border:1px solid #c8ddf6;border-radius:11px;overflow:hidden;background:#f8fbff}.chapterHead{padding:8px 10px;background:#dbeafe;color:#1e3a8a;font-weight:950}.grid{padding:8px;display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:8px}.lesson{border:1px solid #dce5ed;border-radius:12px;background:#fff;padding:10px}.title{font-weight:950;line-height:1.3}.muted{font-size:11px;color:#64748b}.tags{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0}.tag{padding:3px 6px;border:1px solid #d7e0e8;border-radius:999px;background:#f8fafc;font-size:9.5px;font-weight:900}.dbt{margin-top:5px;border:1px solid #d3e4f8;border-radius:9px;background:#f8fbff;padding:6px}.dbthead{font-size:10px;font-weight:950;color:#1e3a8a;margin-bottom:4px}.dbtrow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px;align-items:center;padding:5px 6px;margin:3px 0;border:1px solid #dbeafe;border-radius:7px;background:#fff;cursor:pointer}.dbtrow:hover{background:#eff6ff;border-color:#60a5fa}.dbtname{font-size:10px;font-weight:850;line-height:1.3}.dbtcount{font-size:9px;font-weight:900;color:#1e3a8a;background:#eaf2ff;border:1px solid #bfdbfe;border-radius:999px;padding:3px 5px}.actions{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.empty{text-align:center;padding:35px;color:#64748b}.modal{position:fixed;inset:0;background:#0f172a99;z-index:50;display:flex;align-items:center;justify-content:center;padding:12px}.hide{display:none}.box{width:min(1500px,98vw);height:min(92vh,930px);background:#fff;border-radius:14px;overflow:hidden;display:flex;flex-direction:column}.mh{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:10px 13px;background:#eef6ff;border-bottom:1px solid #d3e0ed}.mcontent{display:grid;grid-template-columns:310px minmax(0,1fr);min-height:0;flex:1}.ql{padding:7px;overflow:auto;border-right:1px solid #dbe4ed}.qi{padding:7px;border:1px solid #e0e7ef;border-radius:8px;margin:4px 0;cursor:pointer}.qi:hover,.qi.on{background:#eff6ff;border-color:#8bb8e8}.qn{font-size:10px;font-weight:950;color:#145bb0}.qt{font-size:10px;line-height:1.35}.qm{font-size:9px;color:#64748b;margin-top:2px}.ed{display:flex;flex-direction:column;min-width:0;padding:10px}.editorTitle{font-size:18px;font-weight:950}.meta{display:grid;grid-template-columns:1fr 1fr;gap:6px}.meta input{width:100%;padding:7px;border:1px solid #cbd5e1;border-radius:7px}.code{flex:1;min-height:0;margin-top:7px;resize:none;border:1px solid #cbd5e1;border-radius:8px;padding:10px;background:#fcfdff;color:#111;font:12px/1.5 Consolas,monospace}.foot{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.msg{font-size:11px;padding:7px 9px;border-radius:8px}.ok{background:#ecfdf5;color:#166534;border:1px solid #86efac}.err{background:#fff1f2;color:#b42318;border:1px solid #fecaca}@media(max-width:900px){.filters{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}.mcontent{grid-template-columns:1fr}.ql{max-height:250px;border-right:0;border-bottom:1px solid #dbe4ed}.meta{grid-template-columns:1fr}}@media(max-width:600px){.filters{grid-template-columns:1fr}.source{display:none}.brand{font-size:17px}}
</style></head><body><div class="top"><div class="toprow"><div><div class="brand">📚 Ngân hàng đề</div><div class="sub">GitHub · .tex trực tiếp · Google Sheet chỉ backup</div></div><div class="source">✓ GitHub</div></div></div><div class="wrap"><div class="tools"><button class="btn primary" id="reload">↻ Tải lại</button><a class="btn" href="/">← Trang chính</a><span id="status" class="msg ok">Đang đọc mục lục GitHub...</span></div><div class="filters"><div class="field"><label>🔎 Tìm bài / chương</label><input id="search" placeholder="Nhập tên bài..." autocomplete="off"></div><div class="field"><label>Môn</label><select id="mon"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="lop"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="chuong"><option value="">Tất cả</option></select></div><div class="field"><label>Bài</label><select id="bai"><option value="">Tất cả</option></select></div></div><div class="intro"><b>📖 Mục lục GitHub</b><span class="muted"> — Chọn một bài, sau đó chọn đúng Dạng bài tập.</span><div class="stats" id="stats"></div></div><div id="catalog" class="shelf"><div class="empty">Đang đọc GitHub...</div></div></div><div id="modal" class="modal hide"><div class="box"><div class="mh"><div><div id="mTitle" class="editorTitle">Bài</div><div id="mPath" class="muted"></div></div><button class="btn" id="close">✕ Đóng</button></div><div class="mcontent"><div class="ql" id="ql"></div><div class="ed"><div id="qTitle" class="editorTitle">Chọn câu</div><div class="meta"><input id="qid" placeholder="ID"><input id="qlevel" placeholder="Mức"></div><textarea id="code" class="code" spellcheck="false"></textarea><div class="foot"><button class="btn green" id="save">💾 Lưu GitHub</button><button class="btn" id="reloadTex">↻ Đọc lại .tex</button><span id="editmsg" class="msg"></span></div></div></div></div></div><script>
let LESSONS=[],CURRENT='',QS=[],QI=-1;
const $=x=>document.getElementById(x), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/gi,'d').toLowerCase().trim();
function unique(f,a){return [...new Set(a.map(x=>x[f]).filter(Boolean))].sort((x,y)=>norm(x).localeCompare(norm(y),'vi'))}
function setOpts(id,a,keep){const e=$(id);e.innerHTML='<option value="">Tất cả</option>'+a.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');e.value=a.includes(keep)?keep:''}
function refreshFilters(){const m=$('mon').value,l=$('lop').value,c=$('chuong').value,b=$('bai').value;let a=LESSONS.filter(x=>!m||x.Mon===m);setOpts('lop',unique('Lop',a),l);a=a.filter(x=>!l||x.Lop===l);setOpts('chuong',unique('Chuong',a),c);a=a.filter(x=>!c||x.Chuong===c);setOpts('bai',unique('BaiHoc',a),b);render()}
function filtered(){let q=norm($('search').value),m=$('mon').value,l=$('lop').value,c=$('chuong').value,b=$('bai').value;return LESSONS.filter(x=>(!q||norm(x.BaiHoc).includes(q)||norm(x.Chuong).includes(q))&&(!m||x.Mon===m)&&(!l||x.Lop===l)&&(!c||x.Chuong===c)&&(!b||x.BaiHoc===b))}
function lesson(x){let h=`<article class="lesson"><div class="title">${esc(x.BaiHoc)}</div><div class="muted">${esc(x.Mon)} · Lớp ${esc(x.Lop)} · ${esc(x.Chuong)}</div><div class="tags"><span class="tag">${x.count} câu</span><span class="tag">${(x.dang||[]).length} dạng</span></div><div class="dbt"><div class="dbthead">🏷️ Dạng bài tập</div>`;for(const d of x.dang||[])h+=`<div class="dbtrow" data-dang-open="1" data-path="${esc(x.path)}"><div class="dbtname">${esc(d.name)}</div><span class="dbtcount">${d.count} câu</span></div>`;h+='</div><div class="actions"><button class="btn primary" data-open="'+esc(x.path)+'">📖 Mở bài</button></div></article>';return h}
function render(){const a=filtered();const g={};for(const x of a){const k=x.Mon+'|'+x.Lop+'|'+x.Chuong;(g[k]??=[]).push(x)}let h='';for(const [k,v] of Object.entries(g)){const [m,l,c]=k.split('|');h+=`<section class="subject"><div class="subjectHead"><span>${esc(m)}</span><span>Lớp ${esc(l)} · ${v.reduce((n,x)=>n+x.count,0)} câu</span></div><div class="grade"><div class="gradeHead">${esc(c)}</div><div class="grid">${v.map(lesson).join('')}</div></div></section>`}$('catalog').innerHTML=h||'<div class="empty">Không có bài phù hợp.</div>';$('stats').innerHTML=`<span class="pill">${a.length} bài</span><span class="pill">${a.reduce((n,x)=>n+x.count,0)} câu</span><span class="pill">Nguồn GitHub</span>`}
async function load(){try{$('status').textContent='Đang đọc GitHub...';$('status').className='msg ok';const r=await fetch('/github/api/catalog-fast',{cache:'no-store'}),j=await r.json();if(!j.ok)throw Error(j.error||'Không đọc được GitHub');LESSONS=j.lessons||[];setOpts('mon',unique('Mon',LESSONS),'');refreshFilters();$('status').textContent=`✓ GitHub · ${j.total_files} file · ${j.total_questions} câu`;}catch(e){$('status').className='msg err';$('status').textContent='❌ '+e.message;$('catalog').innerHTML='<div class="empty">❌ '+esc(e.message)+'</div>'}}
async function openLesson(path){CURRENT=path;$('modal').classList.remove('hide');$('ql').innerHTML='<div class="empty">Đang đọc .tex...</div>';$('mTitle').textContent='Đang đọc bài';$('mPath').textContent=path;try{const r=await fetch('/github/api/tex-fast?path='+encodeURIComponent(path),{cache:'no-store'}),j=await r.json();if(!j.ok)throw Error(j.error||'Không đọc được .tex');window.SHA=j.sha;window.RAW=j.text;QS=j.questions||[];$('mTitle').textContent=path.split('/').slice(-2,-1)[0]||'Bài';renderQ();if(QS.length)selectQ(0)}catch(e){$('ql').innerHTML='<div class="empty">❌ '+esc(e.message)+'</div>'}}
function renderQ(){ $('ql').innerHTML=QS.map((q,i)=>`<div class="qi" data-i="${i}"><div class="qn">Câu ${q.n} · ${q.kind} · ${esc(q.level)}</div><div class="qt">${esc(q.title)}</div><div class="qm">${esc(q.dang)}${q.image?' · 🖼️':''}</div></div>`).join('')}
function selectQ(i){const q=QS[i];if(!q)return;QI=i;document.querySelectorAll('.qi').forEach((x,n)=>x.classList.toggle('on',n===i));$('qTitle').textContent=`Câu ${q.n} · ${q.kind}`;$('qid').value=q.id||'';$('qlevel').value=q.level||'';$('code').value=q.text||''}
async function saveQ(){if(QI<0)return;try{const r=await fetch('/github/api/tex-fast?path='+encodeURIComponent(CURRENT),{cache:'no-store'}),j=await r.json();if(!j.ok)throw Error(j.error||'Không đọc được file');const q=j.questions[QI];if(!q)throw Error('Không tìm thấy câu');let txt=$('code').value;const old=q.text;const pos=j.text.indexOf(old);if(pos<0)throw Error('Không xác định được vị trí câu');let updated=j.text.slice(0,pos)+txt+j.text.slice(pos+old.length);const sr=await fetch('/github/api/save-tex-fast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:CURRENT,text:updated,sha:j.sha,message:'Sửa câu hỏi trực tiếp trong .tex'})}),sj=await sr.json();if(!sj.ok)throw Error(sj.error||'Lưu thất bại');$('editmsg').className='msg ok';$('editmsg').textContent='✓ Đã commit GitHub '+(sj.commit||'').slice(0,8);openLesson(CURRENT)}catch(e){$('editmsg').className='msg err';$('editmsg').textContent='❌ '+e.message}}
$('catalog').addEventListener('click',e=>{const o=e.target.closest('[data-open]');if(o)openLesson(o.dataset.open);const d=e.target.closest('[data-dang-open]');if(d)openLesson(d.dataset.path)});$('ql').addEventListener('click',e=>{const x=e.target.closest('.qi');if(x)selectQ(+x.dataset.i)});$('save').onclick=saveQ;$('reloadTex').onclick=()=>CURRENT&&openLesson(CURRENT);$('close').onclick=()=>{$('modal').classList.add('hide')};$('reload').onclick=load;$('search').oninput=render;['mon','lop','chuong'].forEach(id=>$(id).onchange=refreshFilters);$('bai').onchange=render;load();
</script></body></html>'''
