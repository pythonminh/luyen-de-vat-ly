# -*- coding: utf-8 -*-
"""Ngân hàng GitHub: giao diện kiểu sách, nhanh, chỉ GitHub + .tex."""
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from flask import Blueprint, Response, jsonify, request

bp = Blueprint("github_bank_book", __name__)
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = (os.getenv("GITHUB_BRANCH") or "main").strip() or "main"
TOKEN = (os.getenv("GITHUB_TOKEN") or "").strip()
RAW = "https://raw.githubusercontent.com"
API = "https://api.github.com"
_cache = {"index": None}

def esc(x): return html.escape(str(x or ""), quote=True)
def clean(x): return str(x or "").strip()
def norm_path(p):
    p=clean(p)
    if p and not p.startswith("ngan-hang/"): p="ngan-hang/"+p.lstrip("/")
    return p
def valid_tex(p): return p.startswith("ngan-hang/") and p.lower().endswith(".tex") and ".." not in p

def repo_parts():
    if "/" not in REPO: raise RuntimeError("GITHUB_REPO không hợp lệ")
    return REPO.split("/",1)

def raw_get(path):
    o,r=repo_parts(); url=f"{RAW}/{o}/{r}/{urllib.parse.quote(BRANCH)}/{urllib.parse.quote(path,safe='/')}"
    req=urllib.request.Request(url,headers={"User-Agent":"ldvl-bank-book"})
    with urllib.request.urlopen(req,timeout=12) as res: return res.read().decode("utf-8","replace")

def get_index():
    if _cache["index"] is None: _cache["index"]=json.loads(raw_get("bank_index.json"))
    return _cache["index"]

def github_json(path,method="GET",payload=None):
    if not TOKEN: raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    body=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    req=urllib.request.Request(API+path,data=body,method=method,headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"ldvl-bank-book","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=20) as res: return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        try: msg=json.loads(e.read().decode()).get("message",str(e))
        except Exception: msg=str(e)
        raise RuntimeError(f"GitHub API {e.code}: {msg}")

def fetch_tex(path):
    if not valid_tex(path): raise RuntimeError("Đường dẫn .tex không hợp lệ")
    o,r=repo_parts(); q=f"/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(BRANCH)}"
    d=github_json(q); text=base64.b64decode((d.get("content") or "").replace("\n","")).decode("utf-8","replace")
    return clean(d.get("sha")),text

def save_tex(path,text,sha,message):
    if not valid_tex(path): raise RuntimeError("Đường dẫn .tex không hợp lệ")
    o,r=repo_parts(); q=f"/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe='/')}"
    return github_json(q,"PUT",{"message":message or "Cập nhật ngân hàng .tex","content":base64.b64encode(text.encode()).decode(),"branch":BRANCH,"sha":sha})

def blocks(text):
    pat=re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}",re.I)
    out=[]; prev=0
    for n,m in enumerate(pat.finditer(text or ""),1):
        b=m.group(0); dm=list(re.finditer(r"\\dangbt\s*\{([^{}]*)\}",text[:m.start()],re.I)); d=clean(dm[-1].group(1)) if dm else "Chưa phân dạng"
        if not d or d.casefold() in {"chưa có dạng","chua co dang","chưa phân dạng","chua phan dang"}: d="Chưa phân dạng"
        if re.search(r"\\choiceTF\b",b,re.I): k="B"
        elif re.search(r"\\shortans\b",b,re.I): k="C"
        elif re.search(r"\\choice\b",b,re.I): k="A"
        else: k="D"
        lv=clean((re.search(r"%\s*Mức\s*:\s*([^\r\n%]+)",b,re.I) or [None,""])[1]).upper()
        qid=clean((re.search(r"%\s*ID\s*:\s*([^\r\n%]+)",b,re.I) or [None,""])[1])
        tm=re.search(r"\\begin\s*\{ex\}([\s\S]*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{\s*ex\s*\})",b,re.I)
        title=re.sub(r"%[^\r\n]*","",tm.group(1) if tm else "")
        title=re.sub(r"\\dangbt\s*\{[^{}]*\}","",title,flags=re.I); title=re.sub(r"\s+"," ",title).strip()
        out.append({"n":n,"id":qid,"level":lv,"dang":d,"kind":k,"title":title[:260],"text":b,"image":bool(re.search(r"\\begin\s*\{\s*tikzpicture|\\includegraphics",b,re.I))})
        prev=m.end()
    return out

def lesson_rows():
    rows=[]
    for x in get_index().get("lessons") or []:
        p=norm_path(x.get("github") or x.get("path") or x.get("file"))
        if not p: continue
        d=x.get("dang") or {}; ds=[]
        if isinstance(d,dict):
            for name,n in d.items():
                try:n=int(n or 0)
                except:n=0
                if n>0: ds.append({"name":clean(name) or "Chưa phân dạng","count":n})
        rows.append({"Mon":clean(x.get("Mon")),"Lop":clean(x.get("Lop")),"Chuong":clean(x.get("Chuong")),"BaiHoc":clean(x.get("BaiHoc") or x.get("De")) or p,"path":p,"count":int(x.get("questions") or x.get("count_questions") or x.get("count") or 0),"dang":ds})
    return rows

def stats_for(path):
    _,text=fetch_tex(path); qs=blocks(text); m={}
    for q in qs:
        z=m.setdefault(q["dang"],{"total":0,"A":0,"B":0,"C":0,"D":0}); z["total"]+=1; z[q["kind"]]+=1
    return m

@bp.get('/github/quan-ly')
def page(): return Response(PAGE,mimetype='text/html')

@bp.get('/github/api/catalog-book')
def api_catalog():
    idx=get_index(); rows=lesson_rows(); return jsonify({"ok":True,"source":"GitHub","total_files":int(idx.get("total_files") or idx.get("count") or len(rows)),"total_questions":int(idx.get("total_questions") or sum(x['count'] for x in rows)),"lessons":rows})

@bp.get('/github/api/book-stats')
def api_stats():
    ps=[norm_path(x) for x in request.args.get('paths','').split('||') if norm_path(x)][:30]; out={}
    with ThreadPoolExecutor(max_workers=min(6,len(ps) or 1)) as pool:
        fs={pool.submit(stats_for,p):p for p in ps}
        for f,p in fs.items():
            try: out[p]=f.result()
            except Exception: out[p]={}
    return jsonify({"ok":True,"items":out})

@bp.get('/github/api/book-tex')
def api_tex():
    p=norm_path(request.args.get('path'))
    try:
        sha,text=fetch_tex(p); qs=blocks(text); return jsonify({"ok":True,"path":p,"sha":sha,"text":text,"questions":qs})
    except Exception as e:return jsonify({"ok":False,"error":str(e)}),400

@bp.post('/github/api/book-save')
def api_save():
    d=request.get_json(silent=True) or {}; p=norm_path(d.get('path')); text=d.get('text'); sha=clean(d.get('sha'))
    if not valid_tex(p) or not isinstance(text,str) or not sha:return jsonify({"ok":False,"error":"Thiếu path/text/sha"}),400
    try:
        r=save_tex(p,text,sha,clean(d.get('message'))); _cache['index']=None
        return jsonify({"ok":True,"commit":clean((r.get('commit') or {}).get('sha'))})
    except Exception as e:return jsonify({"ok":False,"error":str(e)}),409

app_blueprint_registered=False

PAGE=r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ngân hàng câu hỏi GitHub</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font-family:Segoe UI,Arial,sans-serif;font-size:14px}.top{background:#1769d2;color:#fff;padding:8px 18px;position:sticky;top:0;z-index:20;box-shadow:0 2px 12px #17324d26}.topline{display:flex;align-items:center;gap:10px}.brand{font-size:20px;font-weight:950}.brand small{display:block;font-size:11px;font-weight:600;opacity:.9}.nav{display:flex;gap:6px;margin-left:8px}.nav button{background:#ffffff16;color:#fff;border:1px solid #ffffff55;border-radius:11px;padding:7px 12px;font-weight:900;cursor:pointer}.nav .on{background:#fff;color:#1557a6}.src{margin-left:auto;font-size:11px;font-weight:850}.subbar{background:#eaf3ff;color:#19558e;border-bottom:1px solid #c8ddf5;padding:7px 18px;font-size:11px}.wrap{max-width:1500px;margin:auto;padding:10px 14px}.tools{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}.btn{border:1px solid #bcd2e9;background:#fff;color:#174a84;border-radius:8px;padding:7px 10px;font-weight:850;cursor:pointer;font-size:11px}.btn.primary{background:#1769d2;border-color:#1769d2;color:#fff}.layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:10px}.side,.main{background:#fff;border:1px solid #d5e0ea;border-radius:14px}.side{overflow:hidden;position:sticky;top:106px;align-self:start}.sideHead,.mainHead{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:950}.sideBody{padding:10px}.field{margin-bottom:8px}.field label{display:block;font-size:10px;font-weight:900;color:#637083;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px;background:#fff}.tree{border-top:1px solid #e5ebf1;margin:8px -10px -10px;padding:7px 10px}.tree button{display:block;border:0;background:none;color:#17324d;font-weight:900;padding:5px 0;cursor:pointer;text-align:left;width:100%;font-size:11px}.mainHead{display:flex;justify-content:space-between;align-items:center}.book{padding:8px}.subject{margin-bottom:10px}.subjectHead{padding:9px 12px;border-radius:12px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:950;display:flex;justify-content:space-between}.grade{margin-top:7px;border:1px solid #d0dbe5;border-radius:12px;overflow:hidden}.gradeHead{padding:8px 10px;background:#f1f5f9;font-weight:950}.chapter{margin:7px;border:1px solid #c7ddf7;border-radius:10px;overflow:hidden;background:#f8fbff}.chapterHead{padding:7px 10px;background:#dbeafe;color:#1e3a8a;font-weight:950}.grid{padding:7px;display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:7px}.lesson{border:1px solid #dce5ed;border-radius:11px;background:#fff;padding:9px;box-shadow:0 1px 3px #17324d0b}.lt{font-weight:950;line-height:1.3}.ls{font-size:10px;color:#64748b;margin-top:3px}.tags{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0}.tag{border:1px solid #d6e0e8;border-radius:999px;padding:3px 6px;background:#f8fafc;font-size:9px;font-weight:900}.dbt{border:1px solid #d4e5f8;background:#f8fbff;border-radius:8px;padding:5px;margin-top:5px}.dbthead{font-size:9.5px;font-weight:950;color:#1e3a8a;margin-bottom:4px}.dbtrow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px;align-items:center;padding:4px 5px;background:#fff;border:1px solid #dbeafe;border-radius:6px;margin:3px 0;cursor:pointer}.dbtrow:hover{background:#eff6ff}.dn{font-size:9.5px;font-weight:850;line-height:1.25}.counts{display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end}.c{font-size:8px;font-weight:950;border-radius:999px;padding:2px 4px;border:1px solid #d4dde7}.ca{color:#1d4ed8;background:#eff6ff;border-color:#93c5fd}.cb{color:#6d28d9;background:#f5f3ff;border-color:#c4b5fd}.cc{color:#15803d;background:#ecfdf5;border-color:#86efac}.cd{color:#c2410c;background:#fff7ed;border-color:#fdba74}.ct{color:#1e3a8a;background:#eaf2ff;border-color:#bfdbfe}.actions{display:flex;gap:4px;flex-wrap:wrap;margin-top:6px}.mini{border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:7px;padding:5px 7px;font-size:9px;font-weight:900;cursor:pointer}.empty{padding:25px;text-align:center;color:#64748b}.modal{position:fixed;inset:0;background:#0f172a99;z-index:60;display:flex;align-items:center;justify-content:center;padding:12px}.hide{display:none}.box{width:min(1450px,98vw);height:min(92vh,930px);background:#fff;border-radius:14px;display:flex;flex-direction:column;overflow:hidden}.mh{padding:9px 12px;background:#eef6ff;border-bottom:1px solid #d2e1f0;display:flex;justify-content:space-between;align-items:center}.mb{display:grid;grid-template-columns:320px minmax(0,1fr);min-height:0;flex:1}.ql{overflow:auto;padding:7px;border-right:1px solid #dde6ee}.qi{padding:7px;border:1px solid #e0e7ef;border-radius:8px;margin:4px 0;cursor:pointer}.qi:hover,.qi.on{background:#edf5ff;border-color:#8bb7e5}.qn{font-weight:950;font-size:10px;color:#145bb0}.qt{font-size:9.5px;line-height:1.35;margin-top:2px}.qm{font-size:8.5px;color:#64748b;margin-top:2px}.ed{padding:9px;display:flex;flex-direction:column;min-width:0}.edtop{display:flex;justify-content:space-between;gap:8px;align-items:center}.etype{font-size:10px;font-weight:950}.code{width:100%;flex:1;min-height:0;margin-top:7px;resize:none;border:1px solid #bdcad8;border-radius:8px;padding:10px;background:#fcfdff;font:12px/1.5 Consolas,monospace}.foot{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.msg{font-size:10px;padding:6px 8px;border-radius:7px;background:#edf8ef;color:#166534;border:1px solid #b7dfc0}.err{background:#fff1f2;color:#b42318;border-color:#fecaca}@media(max-width:900px){.layout{grid-template-columns:1fr}.side{position:static}.grid{grid-template-columns:1fr}.mb{grid-template-columns:1fr}.ql{max-height:240px;border-right:0;border-bottom:1px solid #dde6ee}}
</style></head><body>
<div class="top"><div class="topline"><div class="brand">📚 Ngân hàng câu hỏi GitHub<small>Nguồn chính: bank_index.json + ngan-hang/*.tex</small></div><div class="nav"><button class="on" id="navBook">📖 Mục lục</button><button id="navEdit">✏️ Chỉnh sửa</button></div><div class="src">85 bài · GitHub</div></div></div>
<div class="subbar">🟢 <b>GitHub là nguồn chính</b> · Google Sheet không được gọi · File .tex chỉ đọc khi cần</div>
<div class="wrap"><div class="tools"><button class="btn primary" id="reload">↻ Tải mục lục</button><button class="btn" id="clear">Bộ lọc</button><button class="btn" id="allBook">📚 Mục lục</button></div>
<div class="layout"><aside class="side"><div class="sideHead">🔎 Tìm nhanh</div><div class="sideBody"><div class="field"><label>Từ khóa</label><input id="q" placeholder="Bài, chương, dạng..."></div><div class="field"><label>Môn</label><select id="fMon"></select></div><div class="field"><label>Lớp</label><select id="fLop"></select></div><div class="field"><label>Chương</label><select id="fChuong"></select></div><div class="tree" id="tree"></div></div></aside><main class="main"><div class="mainHead"><span>📖 Mục lục kiểu sách</span><span id="sum"></span></div><div class="book" id="book"><div class="empty">Đang tải mục lục...</div></div></main></div></div>
<div class="modal hide" id="modal"><div class="box"><div class="mh"><b id="mtitle">Chỉnh sửa .tex</b><button class="btn" onclick="closeModal()">Đóng</button></div><div class="mb"><div class="ql" id="ql"></div><div class="ed"><div class="edtop"><span id="etype" class="etype"></span><span id="mmsg"></span></div><textarea id="code" class="code"></textarea><div class="foot"><button class="btn green" id="save">💾 Lưu GitHub</button><button class="btn" id="ra">📝 Ra đề từ bài</button></div></div></div></div></div>
<script>
const S={rows:[],stats:{},path:'',sha:'',qs:[],cur:0};
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pathNorm=p=>(String(p||'').startsWith('ngan-hang/')?String(p):'ngan-hang/'+String(p||'').replace(/^\//,''));
async function load(){try{const r=await fetch('/github/api/catalog-book',{cache:'no-store'});const j=await r.json();if(!j.ok)throw Error(j.error||'Lỗi');S.rows=j.lessons||[];renderFilters();render();lazyStats()}catch(e){$('book').innerHTML='<div class="empty">❌ '+esc(e.message)+'</div>'}}
function opts(id,vals){$(id).innerHTML='<option value="">Tất cả</option>'+[...new Set(vals.filter(Boolean))].map(v=>'<option>'+esc(v)+'</option>').join('')}
function renderFilters(){opts('fMon',S.rows.map(x=>x.Mon));opts('fLop',S.rows.map(x=>x.Lop));opts('fChuong',S.rows.map(x=>x.Chuong));let tree='';for(const mon of [...new Set(S.rows.map(x=>x.Mon).filter(Boolean))]){tree+='<button data-mon="'+esc(mon)+'">▾ 📘 '+esc(mon)+'</button>';for(const lop of [...new Set(S.rows.filter(x=>x.Mon===mon).map(x=>x.Lop))])tree+='<button style="padding-left:16px" data-lop="'+esc(lop)+'" data-mon2="'+esc(mon)+'">▾ Lớp '+esc(lop)+'</button>'}$('tree').innerHTML=tree;$('tree').onclick=e=>{let b=e.target.closest('button');if(!b)return;if(b.dataset.mon){$('fMon').value=b.dataset.mon;$('fLop').value='';$('fChuong').value='';render()}else if(b.dataset.lop){$('fMon').value=b.dataset.mon2;$('fLop').value=b.dataset.lop;$('fChuong').value='';render()}}}
function filtered(){const k=$('q').value.trim().toLowerCase(),m=$('fMon').value,l=$('fLop').value,c=$('fChuong').value;return S.rows.filter(x=>(!m||x.Mon===m)&&(!l||x.Lop===l)&&(!c||x.Chuong===c)&&(!k||[x.BaiHoc,x.Chuong,x.Mon,(x.dang||[]).map(d=>d.name).join(' ')].join(' ').toLowerCase().includes(k)))}
function group(arr,key){const o={};for(const x of arr)(o[x[key]]??=[]).push(x);return o}
function render(){const arr=filtered();$('sum').textContent=arr.length+' bài';if(!arr.length){$('book').innerHTML='<div class="empty">Không có bài phù hợp.</div>';return}const byM=group(arr,'Mon');let h='';for(const [mon,mRows] of Object.entries(byM)){const byL=group(mRows,'Lop');h+='<section class="subject"><div class="subjectHead"><span>'+esc(mon||'Khác')+'</span><span>'+mRows.length+' bài</span></div>';for(const [lop,lRows] of Object.entries(byL)){h+='<div class="grade"><div class="gradeHead">Khối '+esc(lop)+'</div>';const byC=group(lRows,'Chuong');for(const [ch,cRows] of Object.entries(byC)){h+='<div class="chapter"><div class="chapterHead">'+esc(ch||'Chưa có chương')+'</div><div class="grid">';for(const x of cRows)h+=lessonCard(x);h+='</div></div>'}h+='</div>'}h+='</section>'}$('book').innerHTML=h;document.querySelectorAll('.openLesson').forEach(b=>b.onclick=()=>openLesson(b.dataset.path));document.querySelectorAll('.editLesson').forEach(b=>b.onclick=()=>openLesson(b.dataset.path));document.querySelectorAll('.dbtrow').forEach(b=>b.onclick=()=>openLesson(b.dataset.path,b.dataset.dang))}
function lessonCard(x){let ds=(x.dang||[]).filter(d=>d.count>0);let h='<article class="lesson"><div class="lt">'+esc(x.BaiHoc)+'</div><div class="ls">'+esc(x.Mon)+' · Lớp '+esc(x.Lop)+' · '+esc(x.Chuong)+'</div><div class="tags"><span class="tag">'+x.count+' câu</span><span class="tag">.tex</span></div><div class="dbt"><div class="dbthead">🏷️ Dạng bài tập</div><div class="dbtlist">';if(ds.length)for(const d of ds)h+='<div class="dbtrow" data-path="'+esc(pathNorm(x.path))+'" data-dang="'+esc(d.name)+'"><div class="dn">'+esc(d.name)+'</div><div class="counts"><span class="c ca" data-k="A">A —</span><span class="c cb" data-k="B">B —</span><span class="c cc" data-k="C">C —</span><span class="c cd" data-k="D">D —</span><span class="c ct">'+d.count+'</span></div></div>';else h+='<div class="dbtrow"><div class="dn">Chưa phân dạng</div><div class="counts"><span class="c ct">'+x.count+'</span></div></div>';h+='</div></div><div class="actions"><button class="mini openLesson" data-path="'+esc(pathNorm(x.path))+'">📂 Mở bài</button><button class="mini editLesson" data-path="'+esc(pathNorm(x.path))+'">✏️ Chỉnh sửa</button><button class="mini" onclick="event.stopPropagation();raDe(\''+esc(pathNorm(x.path))+'\')">📝 Ra đề</button></div></article>';return h}
async function lazyStats(){const visible=[...document.querySelectorAll('.lesson')].map(a=>a.querySelector('.openLesson')?.dataset.path).filter(Boolean).slice(0,18);if(!visible.length)return;try{const r=await fetch('/github/api/book-stats?paths='+encodeURIComponent([...new Set(visible)].join('||')));const j=await r.json();S.stats=Object.assign(S.stats,j.items||{});document.querySelectorAll('.dbtrow[data-path]').forEach(row=>{const m=S.stats[row.dataset.path]?.[row.dataset.dang];if(!m)return;for(const k of ['A','B','C','D']){const c=row.querySelector('.c.'+({'A':'ca','B':'cb','C':'cc','D':'cd'}[k]));if(c)c.textContent=k+' '+(m[k]||0)}})}catch(e){}}
async function openLesson(path,dang){path=pathNorm(path);S.path=path;$('modal').classList.remove('hide');$('mtitle').textContent='Đọc file .tex — '+path.split('/').pop();$('ql').innerHTML='<div class="empty">Đang đọc .tex...</div>';try{const r=await fetch('/github/api/book-tex?path='+encodeURIComponent(path));const j=await r.json();if(!j.ok)throw Error(j.error||'Lỗi');S.sha=j.sha;S.qs=j.questions||[];S.cur=Math.max(0,dang?S.qs.findIndex(q=>q.dang===dang):0);if(S.cur<0)S.cur=0;renderQuestions();showQ(S.cur)}catch(e){$('ql').innerHTML='<div class="empty">❌ '+esc(e.message)+'</div>'}}
function renderQuestions(){ $('ql').innerHTML=S.qs.map((q,i)=>'<div class="qi '+(i===S.cur?'on':'')+'" data-i="'+i+'"><div><span class="qn">Câu '+q.n+'</span> <span class="tag">'+q.kind+'</span> <span class="tag">'+esc(q.level)+'</span></div><div class="qt">'+esc(q.title||'(Không có tiêu đề)')+'</div><div class="qm">'+esc(q.dang)+(q.image?' · 🖼':'')+'</div></div>').join('');document.querySelectorAll('.qi').forEach(x=>x.onclick=()=>{S.cur=+x.dataset.i;showQ(S.cur);renderQuestions()})}
function showQ(i){const q=S.qs[i];if(!q)return;$('etype').textContent='Câu '+q.n+' · '+q.kind+' · '+(q.level||'')+' · '+q.dang;$('code').value=q.text;$('ra').onclick=()=>raDe(S.path,q.dang)}
$('save').onclick=async()=>{const msg=$('mmsg');msg.className='msg';msg.textContent='Đang lưu...';try{const r=await fetch('/github/api/book-save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:S.path,text:$('code').value,sha:S.sha,message:'Sửa câu trong '+S.path})});const j=await r.json();if(!j.ok)throw Error(j.error||'Lỗi');msg.textContent='✓ Đã commit GitHub';S.sha=j.content_sha||S.sha;setTimeout(()=>msg.textContent='',1800)}catch(e){msg.className='msg err';msg.textContent='❌ '+e.message}};
function closeModal(){$('modal').classList.add('hide')}
function raDe(path,dang){location.href='/ra-de?path='+encodeURIComponent(path)+(dang?'&dang='+encodeURIComponent(dang):'')}
$('q').oninput=render;$('fMon').onchange=render;$('fLop').onchange=render;$('fChuong').onchange=render;$('reload').onclick=load;$('clear').onclick=()=>{$('q').value='';$('fMon').value='';$('fLop').value='';$('fChuong').value='';render()};$('allBook').onclick=()=>{$('fMon').value='';$('fLop').value='';$('fChuong').value='';$('q').value='';render()};$('navEdit').onclick=()=>{const first=filtered()[0];if(first)openLesson(first.path)};load();
</script></body></html>'''

app.register_blueprint(bp)
