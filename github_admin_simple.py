# -*- coding: utf-8 -*-
"""GitHub-only question bank. Fast catalog + direct .tex editing."""
from __future__ import annotations
import base64, json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from flask import Flask, Response, jsonify, request, redirect

app = Flask(__name__)
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = (os.getenv("GITHUB_BRANCH") or "main").strip() or "main"
TOKEN = (os.getenv("GITHUB_TOKEN") or "").strip()
ADMIN_PASSWORD = (os.getenv("ADMIN_PASSWORD") or "").strip()
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "bank_index.json"
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
QRE = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
DRE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)

def gh(path, method="GET", data=None):
    if not TOKEN: raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode()
    req = urllib.request.Request(API + path, data=body, method=method, headers={
        "Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "ldvl-github-admin",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        s = e.read().decode("utf-8", "replace")
        try: s = json.loads(s).get("message", s)
        except Exception: pass
        raise RuntimeError(f"GitHub API {e.code}: {s}") from e

def index_data():
    if INDEX.exists(): return json.loads(INDEX.read_text(encoding="utf-8"))
    o, r = REPO.split("/", 1)
    u = f"{RAW}/{o}/{r}/{urllib.parse.quote(BRANCH)}/bank_index.json"
    with urllib.request.urlopen(u, timeout=12) as q: return json.loads(q.read().decode())

def safe_tex(p):
    return isinstance(p, str) and p.startswith("ngan-hang/") and p.lower().endswith(".tex") and ".." not in p

def read_tex(p):
    if not safe_tex(p): raise ValueError("Đường dẫn .tex không hợp lệ")
    o, r = REPO.split("/", 1)
    q = f"/repos/{o}/{r}/contents/{urllib.parse.quote(p, safe='/')}?ref={urllib.parse.quote(BRANCH)}"
    d = gh(q)
    text = base64.b64decode((d.get("content") or "").replace("\n", "")).decode("utf-8", "replace")
    return d.get("sha", ""), text

def kind(b):
    if re.search(r"\\choiceTF\b", b, re.I): return "B"
    if re.search(r"\\shortans\b", b, re.I): return "C"
    if re.search(r"\\choice\b", b, re.I): return "A"
    return "D"

def parse_questions(text):
    ms = list(QRE.finditer(text or "")); marks = list(DRE.finditer(text or "")); out=[]; mi=0; dang="Chưa phân dạng"
    for i, m in enumerate(ms, 1):
        while mi < len(marks) and marks[mi].start() < m.start(): dang = marks[mi].group(1).strip() or "Chưa phân dạng"; mi += 1
        if dang.casefold() in {"chưa có dạng", "chua co dang", "chưa phân dạng", "chua phan dang"}: dang="Chưa phân dạng"
        b=m.group(0); im=re.search(r"%\s*ID\s*:\s*([^\r\n%]+)",b,re.I); lm=re.search(r"%\s*Mức\s*:\s*([^\r\n%]+)",b,re.I)
        title=b.split("\\end",1)[0]; title=re.sub(r"%[^\r\n]*"," ",title); title=re.sub(r"\\dangbt\s*\{[^{}]*\}"," ",title,flags=re.I); title=re.sub(r"\\begin\s*\{\s*ex\s*\}"," ",title,flags=re.I); title=re.sub(r"\s+"," ",title).strip()
        out.append({"n":i,"id":im.group(1).strip() if im else "","level":lm.group(1).strip().upper() if lm else "","dang":dang,"kind":kind(b),"title":title[:240],"text":b})
    return out

def auth_ok():
    a=request.authorization
    return bool(a and a.username=="admin" and ADMIN_PASSWORD and a.password==ADMIN_PASSWORD)

def need_auth():
    if auth_ok(): return None
    return Response("Yêu cầu đăng nhập ADMIN",401,{"WWW-Authenticate":"Basic realm=GitHub Admin"})

@app.get("/")
def root(): return redirect("/github/quan-ly")

@app.get("/github/repo")
def repo(): return redirect(f"https://github.com/{REPO}",302)

@app.get("/github/quan-ly")
def page(): return Response(PAGE,mimetype="text/html")

@app.get("/github/api/catalog")
def catalog():
    try:
        d=index_data(); rows=[]
        for x in d.get("lessons",[]):
            if not isinstance(x,dict): continue
            p=str(x.get("path") or x.get("file") or "").strip()
            if not safe_tex(p): continue
            raw=x.get("dang") or {}; ds=[]
            if isinstance(raw,dict):
                for n,c in raw.items():
                    try: c=int(c or 0)
                    except: c=0
                    if c>0: ds.append({"name":str(n).strip() or "Chưa phân dạng","count":c})
            rows.append({"Mon":str(x.get("Mon") or ""),"Lop":str(x.get("Lop") or ""),"Chuong":str(x.get("Chuong") or ""),"BaiHoc":str(x.get("BaiHoc") or x.get("De") or Path(p).parent.name),"path":p,"count":int(x.get("questions") or x.get("count") or 0),"dang":ds})
        return jsonify({"ok":True,"total_files":int(d.get("total_files") or len(rows)),"total_questions":int(d.get("total_questions") or sum(x["count"] for x in rows)),"lessons":rows})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.get("/github/api/file")
def api_file():
    e=need_auth()
    if e:return e
    try:
        p=request.args.get("path",""); sha,text=read_tex(p)
        return jsonify({"ok":True,"path":p,"sha":sha,"text":text,"questions":parse_questions(text)})
    except Exception as e:return jsonify({"ok":False,"error":str(e)}),400

@app.post("/github/api/save")
def api_save():
    e=need_auth()
    if e:return e
    try:
        d=request.get_json(silent=True) or {}; p=d.get("path",""); text=d.get("text"); sha=str(d.get("sha") or "")
        if not safe_tex(p) or not isinstance(text,str) or not sha:return jsonify({"ok":False,"error":"Thiếu path/text/sha"}),400
        o,r=REPO.split("/",1); q=f"/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe='/')}"
        z=gh(q,"PUT",{"message":d.get("message") or "Admin cập nhật .tex","content":base64.b64encode(text.encode()).decode(),"branch":BRANCH,"sha":sha})
        return jsonify({"ok":True,"commit":str((z.get("commit") or {}).get("sha") or "")[:12]})
    except Exception as e:return jsonify({"ok":False,"error":str(e)}),409

PAGE=r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ngân hàng GitHub</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial}.top{background:#1769d2;color:#fff;padding:9px 16px}.row{display:flex;align-items:center;gap:10px}.brand{font-size:20px;font-weight:900}.sub{font-size:11px}.nav{margin-left:8px}.nav a{color:#fff;text-decoration:none;border:1px solid #fff6;border-radius:9px;padding:7px 11px;margin-right:5px;font-weight:800}.on{background:#fff!important;color:#1558a6!important}.src{margin-left:auto;font-size:11px}.bar{background:#eaf3ff;border-bottom:1px solid #c9def4;color:#18558e;padding:7px 16px;font-size:11px}.wrap{max-width:1500px;margin:auto;padding:10px 14px}.layout{display:grid;grid-template-columns:280px 1fr;gap:9px}.panel{background:#fff;border:1px solid #d5e0ea;border-radius:12px;overflow:hidden}.head{padding:9px 11px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.body{padding:9px}.field{margin-bottom:7px}.field label{display:block;font-size:10px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.mh{padding:9px 11px;background:#f8fbff;border-bottom:1px solid #dfe7ef;display:flex;justify-content:space-between;font-weight:900}.book{padding:8px}.subject{margin-bottom:9px}.sh{padding:8px 10px;border-radius:10px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:900;display:flex;justify-content:space-between}.grade{margin-top:6px;border:1px solid #d1dbe5;border-radius:10px;overflow:hidden}.gh{padding:7px 9px;background:#f1f5f9;font-weight:900}.chapter{margin:6px;border:1px solid #c8ddf7;border-radius:9px;overflow:hidden}.ch{padding:6px 9px;background:#dbeafe;color:#1e3a8a;font-weight:900}.grid{padding:6px;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:6px}.lesson{border:1px solid #dce5ed;border-radius:9px;padding:8px}.lt{font-weight:900}.ls{font-size:10px;color:#64748b}.tag{display:inline-block;font-size:9px;border:1px solid #d6e0e8;border-radius:99px;padding:3px 6px;margin:4px 3px 2px 0}.dang{margin-top:4px;padding:5px;border:1px solid #d4e5f8;border-radius:7px;background:#f8fbff}.dr{display:flex;justify-content:space-between;gap:5px;padding:4px;border:1px solid #dbeafe;background:#fff;border-radius:5px;margin:2px 0;font-size:9px;cursor:pointer}.btn{border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:7px;padding:5px 7px;font-size:9px;font-weight:900;cursor:pointer}.empty{text-align:center;padding:30px;color:#64748b}.modal{position:fixed;inset:0;background:#0f172a99;display:flex;align-items:center;justify-content:center;padding:12px;z-index:50}.hide{display:none}.box{width:min(1450px,98vw);height:min(92vh,930px);background:#fff;border-radius:12px;display:flex;flex-direction:column;overflow:hidden}.mb{display:grid;grid-template-columns:320px 1fr;min-height:0;flex:1}.ql{overflow:auto;padding:6px;border-right:1px solid #dde6ee}.qi{padding:6px;border:1px solid #e0e7ef;border-radius:7px;margin:3px 0;cursor:pointer}.qi.on{background:#eff6ff;border-color:#8bb8e8}.qn{font-size:10px;font-weight:900;color:#145bb0}.qm{font-size:9px;color:#64748b}.ed{display:flex;flex-direction:column;padding:7px;min-width:0}.code{flex:1;min-height:0;resize:none;border:1px solid #cbd5e1;border-radius:7px;padding:9px;font:12px/1.5 Consolas,monospace}.foot{display:flex;gap:6px;align-items:center;margin-top:6px}.ok{color:#15803d;font-size:10px;font-weight:800}.err{color:#b91c1c;font-size:10px;font-weight:800}@media(max-width:850px){.layout{grid-template-columns:1fr}.mb{grid-template-columns:1fr}.ql{max-height:230px;border-right:0;border-bottom:1px solid #dde6ee}.grid{grid-template-columns:1fr}}
</style></head><body><div class="top"><div class="row"><div><div class="brand">📚 Ngân hàng câu hỏi GitHub</div><div class="sub">Nguồn: bank_index.json + ngan-hang/*.tex</div></div><div class="nav"><a class="on" href="/github/quan-ly">Mục lục</a><a href="/github/repo" target="_blank">🐙 GitHub</a><a href="/admin-logout">Thoát ADMIN</a></div><div class="src">✓ GitHub</div></div></div><div class="bar">✓ GitHub là nguồn chính · Google Sheet không được gọi · Chỉ đọc .tex khi mở bài</div><div class="wrap"><div class="layout"><aside class="panel"><div class="head">🔎 Tìm nhanh</div><div class="body"><div class="field"><label>Từ khóa</label><input id="q" placeholder="Bài, chương, dạng..." oninput="render()"></div><div class="field"><label>Môn</label><select id="mon" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="lop" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="ch" onchange="render()"><option value="">Tất cả</option></select></div></div></aside><main class="panel"><div class="mh"><span>📖 Mục lục kiểu sách</span><span id="total">Đang tải...</span></div><div id="book" class="book"><div class="empty">Đang tải GitHub...</div></div></main></div></div><div id="modal" class="modal hide"><div class="box"><div class="mh"><b id="mt">Sửa file .tex</b><button class="btn" onclick="closeEdit()">Đóng</button></div><div class="mb"><div id="ql" class="ql"></div><div class="ed"><textarea id="code" class="code"></textarea><div class="foot"><button class="btn" onclick="saveFile()">💾 Lưu GitHub</button><button class="btn" onclick="openRaw()">🐙 GitHub</button><span id="msg"></span></div></div></div></div></div><script>
let DATA=[],CUR=null,QS=[];const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function load(){try{let j=await (await fetch('/github/api/catalog',{cache:'no-store'})).json();if(!j.ok)throw Error(j.error);DATA=j.lessons||[];fill();render()}catch(e){$('book').innerHTML='<div class="empty">❌ '+esc(e.message)+'</div>';$('total').textContent='Lỗi'}}
function fill(){for(let [id,key] of [['mon','Mon'],['lop','Lop'],['ch','Chuong']]){let s=$(id),v=[...new Set(DATA.map(x=>x[key]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'vi'));s.innerHTML='<option value="">Tất cả</option>'+v.map(x=>'<option>'+esc(x)+'</option>').join('')}}
function render(){let q=$('q').value.toLowerCase(),m=$('mon').value,l=$('lop').value,c=$('ch').value;let rows=DATA.filter(x=>(!m||x.Mon===m)&&(!l||x.Lop===l)&&(!c||x.Chuong===c)&&(!q||[x.BaiHoc,x.Mon,x.Lop,x.Chuong,...(x.dang||[]).map(d=>d.name)].join(' ').toLowerCase().includes(q)));$('total').textContent=DATA.length+' bài · '+DATA.reduce((a,x)=>a+x.count,0)+' câu';let by={};rows.forEach(x=>(by[x.Mon]??=[]).push(x));let h='';for(let [mon,arr] of Object.entries(by)){h+='<section class="subject"><div class="sh"><span>'+esc(mon)+'</span><span>'+arr.reduce((a,x)=>a+x.count,0)+' câu</span></div>';let gr={};arr.forEach(x=>(gr[x.Lop]??=[]).push(x));for(let [lop,ls] of Object.entries(gr)){h+='<div class="grade"><div class="gh">Khối '+esc(lop)+'</div>';let cc={};ls.forEach(x=>(cc[x.Chuong]??=[]).push(x));for(let [ch,bs] of Object.entries(cc)){h+='<div class="chapter"><div class="ch">'+esc(ch)+'</div><div class="grid">';for(let x of bs){h+='<div class="lesson"><div class="lt">'+esc(x.BaiHoc)+'</div><div class="ls">'+esc(x.Mon)+' · Lớp '+esc(x.Lop)+'</div><span class="tag">'+x.count+' câu</span><span class="tag">.tex</span><div class="dang"><b style="font-size:9px;color:#1e3a8a">🏷️ Dạng bài tập</b>';for(let d of (x.dang||[]))h+='<div class="dr" onclick="openLesson(\''+encodeURIComponent(x.path)+'\')"><span>'+esc(d.name)+'</span><b>'+d.count+'</b></div>';if(!(x.dang||[]).length)h+='<div class="dr" onclick="openLesson(\''+encodeURIComponent(x.path)+'\')"><span>Chưa phân dạng</span><b>'+x.count+'</b></div>';h+='</div><div style="margin-top:5px"><button class="btn" onclick="openLesson(\''+encodeURIComponent(x.path)+'\')">📂 Mở bài</button></div></div>'}h+='</div></div>'}h+='</div>'}h+='</section>'}$('book').innerHTML=h||'<div class="empty">Không có dữ liệu phù hợp.</div>'}
async function openLesson(ep){let p=decodeURIComponent(ep);$('modal').classList.remove('hide');$('ql').innerHTML='<div class="empty">Đang đọc .tex...</div>';let r=await fetch('/github/api/file?path='+encodeURIComponent(p));if(r.status===401){$('ql').innerHTML='<div class="empty">🔒 Cần ADMIN. <a href="/admin-login">Đăng nhập</a></div>';return}let j=await r.json();if(!j.ok){$('ql').innerHTML='<div class="empty">❌ '+esc(j.error)+'</div>';return}CUR=j;QS=j.questions||[];$('mt').textContent=p;$('ql').innerHTML=QS.map((x,i)=>'<div class="qi '+(i?'':'on')+'" onclick="selectQ('+i+')"><div class="qn">Câu '+x.n+' · '+x.kind+' · '+esc(x.level)+'</div><div>'+esc(x.title||x.dang)+'</div><div class="qm">'+esc(x.dang)+'</div></div>').join('');if(QS.length)selectQ(0)}
function selectQ(i){document.querySelectorAll('.qi').forEach((e,k)=>e.classList.toggle('on',k===i));$('code').value=QS[i].text||'';$('msg').textContent=''}
async function saveFile(){if(!CUR)return;let r=await fetch('/github/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:CUR.path,text:$('code').value,sha:CUR.sha})});let j=await r.json();$('msg').textContent=j.ok?'✅ Đã lưu GitHub · '+j.commit:'❌ '+(j.error||'Lỗi');$('msg').className=j.ok?'msg ok':'msg err';if(j.ok)CUR.sha=''}
function openRaw(){if(CUR?.path)window.open('https://github.com/pythonminh/luyen-de-vat-ly/blob/main/'+CUR.path,'_blank')}
function closeEdit(){$('modal').classList.add('hide')};load();</script></body></html>'''
