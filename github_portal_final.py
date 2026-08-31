# -*- coding: utf-8 -*-
"""GitHub-only portal: FREE/VIP members + ADMIN + direct .tex editing."""
from __future__ import annotations

import base64, hashlib, html, json, os, re, urllib.error, urllib.parse, urllib.request
from functools import wraps
from pathlib import Path
from flask import Flask, Response, redirect, request, session, jsonify

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET", "change-this-on-render")
REPO = os.getenv("GITHUB_REPO", "pythonminh/luyen-de-vat-ly").strip()
BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "ADMIN").strip() or "ADMIN"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "bank_index.json"
MEMBERS = ROOT / "members.json"
ACCESS = ROOT / "lesson_access.json"
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
CHOICE_RE = re.compile(r"\\choice\b", re.I)
TF_RE = re.compile(r"\\choiceTF\b", re.I)
SHORT_RE = re.compile(r"\\shortans\s*\{([^{}]*)\}", re.I)
DANG_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)

CSS = """
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial}.top{background:#1769d2;color:white;padding:10px 16px}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b9d5f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin:3px}.nav a{background:transparent;color:#fff;border-color:#ffffff66}.wrap{max-width:1450px;margin:auto;padding:12px}.grid{display:grid;grid-template-columns:260px 1fr;gap:10px}.panel{background:#fff;border:1px solid #d6e0ea;border-radius:12px;overflow:hidden}.head{padding:10px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.body{padding:10px}.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;display:flex;justify-content:space-between;gap:8px;align-items:center;font-weight:900}.hero{padding:14px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px;padding:8px}.card{border:1px solid #dce5ed;border-radius:9px;padding:10px;background:#fff}.small{font-size:11px;color:#64748b}.field{margin-bottom:8px}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:7px;border-bottom:1px solid #e5e7eb;text-align:left}.login{max-width:430px;margin:65px auto}.tag{display:inline-block;padding:3px 7px;border:1px solid #cbd5e1;border-radius:999px;font-size:10px;margin:4px 3px 0 0}.free{border-color:#86efac;background:#f0fdf4;color:#166534}.vip{border-color:#f9a8d4;background:#fdf2f8;color:#9d174d}.notice{margin:10px 0;padding:10px;border-radius:8px;border:1px solid #93c5fd;background:#eff6ff}.err{color:#b91c1c;font-weight:800}.ok{color:#15803d;font-weight:800}.qtext{line-height:1.6}.opt{display:block;padding:9px;border:1px solid #dbeafe;border-radius:8px;margin:6px 0}.section{margin:8px 0;padding:8px;border:1px solid #dbeafe;border-radius:8px;background:#f8fbff}.score{padding:10px;border:1px solid #86efac;background:#f0fdf4;border-radius:9px;font-weight:900}.code{width:100%;height:72vh;resize:vertical;border:1px solid #cbd5e1;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.actions{padding:0 10px 10px}@media(max-width:800px){.grid{grid-template-columns:1fr}.login{margin:25px auto}}
"""

def gh(path, method="GET", data=None):
    if not TOKEN:
        raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API + path, data=body, method=method, headers={
        "Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28","User-Agent":"ldvl-github-final",
        "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try: msg=json.loads(raw).get("message",raw)
        except Exception: msg=raw
        raise RuntimeError(f"GitHub API {e.code}: {msg}") from e

def gh_get(path):
    owner,repo=REPO.split("/",1)
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(BRANCH)}")

def gh_put(path, text, message, sha=None):
    owner,repo=REPO.split("/",1)
    data={"message":message,"content":base64.b64encode(text.encode("utf-8")).decode("ascii"),"branch":BRANCH}
    if sha: data["sha"]=sha
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe='/')}","PUT",data)

def index_data():
    if INDEX.exists(): return json.loads(INDEX.read_text(encoding="utf-8"))
    owner,repo=REPO.split("/",1)
    url=f"{RAW}/{owner}/{repo}/{urllib.parse.quote(BRANCH)}/bank_index.json"
    with urllib.request.urlopen(url,timeout=12) as r: return json.loads(r.read().decode("utf-8"))

def load_json_file(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def load_members(): return load_json_file(MEMBERS,{"schema":2,"members":[]})
def load_access():
    d=load_json_file(ACCESS,{"schema":1,"default":"FREE","lessons":{}})
    d.setdefault("default","FREE"); d.setdefault("lessons",{}); return d

def sync_json(filename, data, message):
    text=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    current=gh_get(filename) if True else None
    gh_put(filename,text,message,current.get("sha"))
    Path(ROOT/filename).write_text(text,encoding="utf-8")

def save_members(data): sync_json("members.json",data,"Admin cập nhật thành viên")
def save_access(data):
    try: current=gh_get("lesson_access.json"); sha=current.get("sha")
    except Exception: sha=None
    text=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    gh_put("lesson_access.json",text,"Admin cập nhật quyền bài học",sha)
    ACCESS.write_text(text,encoding="utf-8")

def account_type(m): return str(m.get("account_type") or "FREE").upper()
def is_vip(m): return account_type(m) in {"VIP","S.VIP","ADMIN"}
def current_member():
    u=session.get("username")
    if not u:return None
    for m in load_members().get("members",[]):
        if m.get("username")==u and m.get("status","ON")=="ON": return m
    return None

def lesson_level(path):
    a=load_access(); return str(a.get("lessons",{}).get(path,a.get("default","FREE"))).upper()
def allowed(m,path):
    level=lesson_level(path); return level=="FREE" or is_vip(m)

def safe_tex(path): return isinstance(path,str) and path.startswith("ngan-hang/") and path.lower().endswith(".tex") and ".." not in path

def read_tex(path):
    if not safe_tex(path): raise ValueError("Đường dẫn .tex không hợp lệ")
    d=gh_get(path); text=base64.b64decode((d.get("content") or "").replace("\n","")).decode("utf-8","replace")
    return d.get("sha",""),text

def brace_arg(s,pos):
    while pos<len(s) and s[pos].isspace(): pos+=1
    if pos>=len(s) or s[pos]!="{": return None,pos
    depth=0; start=pos+1; i=pos
    while i<len(s):
        if s[i]=="{" and (i==0 or s[i-1]!="\\"): depth+=1
        elif s[i]=="}" and (i==0 or s[i-1]!="\\"):
            depth-=1
            if depth==0:return s[start:i],i+1
        i+=1
    return None,len(s)

def cmd_args(s,cmd):
    m=re.search(re.escape(cmd)+r"\b",s,re.I)
    if not m:return []
    out=[]; pos=m.end()
    while True:
        a,pos2=brace_arg(s,pos)
        if a is None: break
        out.append(a); pos=pos2
    return out

def clean(s):
    s=re.sub(r"%.*", "", s); s=DANG_RE.sub("",s); s=re.sub(r"\\ID\s*:\s*[^\n]*", "", s, flags=re.I)
    return s.strip()

def parse_q(block):
    tf=cmd_args(block,"\\choiceTF")
    if tf:
        return {"kind":"tf","text":clean(TF_RE.split(block,1)[0]),"statements":[re.sub(r"^\\True\s*","",x,flags=re.I).strip() for x in tf],"correct":[bool(re.match(r"^\\True\b",x,re.I)) for x in tf]}
    ch=cmd_args(block,"\\choice")
    if ch:
        return {"kind":"choice","text":clean(CHOICE_RE.split(block,1)[0]),"options":[re.sub(r"^\\True\s*","",x,flags=re.I).strip() for x in ch[:4]],"correct":next((i for i,x in enumerate(ch[:4]) if re.match(r"^\\True\b",x,re.I)),0)}
    sm=SHORT_RE.search(block)
    if sm:return {"kind":"short","text":clean(block[:sm.start()]),"answer":sm.group(1).strip()}
    return {"kind":"unsupported","text":clean(block)}

def questions(path):
    _,text=read_tex(path); return [parse_q(b) for b in EX_RE.findall(text)]

def require_member(view):
    @wraps(view)
    def w(*a,**k):
        if session.get("role")!="member" or not current_member(): session.clear(); return redirect("/member/login")
        return view(*a,**k)
    return w

def require_admin(view):
    @wraps(view)
    def w(*a,**k):
        if session.get("role")!="admin": return redirect("/admin/login")
        return view(*a,**k)
    return w

def page(title,body):
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"+f"<title>{html.escape(title)}</title><style>{CSS}</style><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><div class='row'><div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div><div class='sub'>Nguồn chính: GitHub / ngan-hang/*.tex</div></div><div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>{body}</body></html>",mimetype="text/html")

@app.get("/")
def root(): return redirect("/member/login")
@app.get("/github/repo")
def repo_link(): return redirect(f"https://github.com/{REPO}")

@app.route("/member/login",methods=["GET","POST"])
def member_login():
    msg=""
    if request.method=="POST":
        u=(request.form.get("username") or "").strip(); p=request.form.get("password") or ""; h=hashlib.sha256(p.encode()).hexdigest()
        for m in load_members().get("members",[]):
            if m.get("username")==u and m.get("password_sha256")==h and m.get("status","ON")=="ON":
                session.clear(); session.update(role="member",username=u,name=m.get("name") or u)
                return redirect("/member")
        msg="Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa."
    return page("Đăng nhập",f"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.route("/member/register",methods=["GET","POST"])
def member_register():
    msg=""
    if request.method=="POST":
        u=(request.form.get("username") or "").strip(); name=(request.form.get("name") or "").strip(); p=request.form.get("password") or ""; data=load_members()
        if not u or not p: msg="Thiếu tài khoản hoặc mật khẩu."
        elif any(m.get("username")==u for m in data.get("members",[])): msg="Tài khoản đã tồn tại."
        else:
            data.setdefault("members",[]).append({"username":u,"name":name or u,"class":"","account_type":"FREE","status":"ON","password_sha256":hashlib.sha256(p.encode()).hexdigest()})
            try: save_members(data); session.clear(); session.update(role="member",username=u,name=name or u); return redirect("/member")
            except Exception as e: msg=str(e)
    return page("Đăng ký",f"<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký thành viên FREE</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng ký FREE</button> <a class='btn' href='/member/login'>Quay lại</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.get("/member/logout")
def member_logout(): session.clear(); return redirect("/member/login")

@app.get("/member")
@require_member
def member_home():
    m=current_member(); d=index_data(); cards=[]
    for x in d.get("lessons",[]):
        if not isinstance(x,dict):continue
        p=str(x.get("path") or "")
        if not safe_tex(p):continue
        title=str(x.get("BaiHoc") or x.get("De") or Path(p).parent.name); c=int(x.get("questions") or x.get("count") or 0); lv=lesson_level(p); can=allowed(m,p)
        tag=f"<span class='tag {'vip' if lv=='VIP' else 'free'}'>{lv}</span>"; act=f"<a class='btn' href='/member/lesson?path={urllib.parse.quote(p,safe='')}'>📝 Làm bài</a>" if can else "<span class='tag vip'>🔒 Chỉ VIP</span>"
        cards.append(f"<div class='card'><b>{html.escape(title)}</b><div class='small'>{html.escape(str(x.get('Mon') or ''))} · {html.escape(str(x.get('Lop') or ''))}</div>{tag}<span class='tag'>{c} câu</span><div>{act}</div></div>")
    vip=is_vip(m); badge="VIP — được xem và làm FREE + VIP" if vip else "THƯỜNG — chỉ được xem và làm FREE"
    body=f"<div class='wrap'><div class='panel'><div class='mh'><span>👤 {html.escape(str(m.get('name') or m.get('username')))} · <span class='tag {'vip' if vip else 'free'}'>{badge}</span></span><a class='btn' href='/member/logout'>Thoát</a></div><div class='notice'><b>Tài khoản:</b> {html.escape(str(m.get('username') or ''))} &nbsp; <b>Quyền:</b> {html.escape(account_type(m))}. Bạn chỉ sử dụng được các chức năng phù hợp với quyền này.</div><div class='hero'><h2>📚 Danh sách bài học</h2><div class='small'>{int(d.get('total_files') or 0)} bài · {int(d.get('total_questions') or 0)} câu</div></div><div class='cards'>{''.join(cards)}</div></div></div>"
    return page("Thành viên",body)

@app.get("/member/lesson")
@require_member
def member_lesson():
    m=current_member(); p=request.args.get("path","")
    if not safe_tex(p): return page("Lỗi", "<div class='wrap'><div class='panel'><div class='body err'>Đường dẫn không hợp lệ.</div></div></div>")
    if not allowed(m,p): return page("Bài VIP", "<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho thành viên VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    try: qs=questions(p)
    except Exception as e: return page("Lỗi đọc bài",f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    payload=json.dumps(qs,ensure_ascii=False)
    cards=[]
    for i,q in enumerate(qs,1):
        t=html.escape(q.get("text",''))
        if q["kind"]=="choice": opts=''.join(f"<label class='opt'><input type='radio' name='q{i}' value='{j}'> {chr(65+j)}. {html.escape(o)}</label>" for j,o in enumerate(q["options"])); cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div>{opts}</div>")
        elif q["kind"]=="tf": st=''.join(f"<div class='section'><b>{j+1}.</b> {html.escape(s)}<br><label><input type='radio' name='q{i}_{j}' value='1'> Đúng</label> &nbsp; <label><input type='radio' name='q{i}_{j}' value='0'> Sai</label></div>" for j,s in enumerate(q["statements"])); cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div>{st}</div>")
        elif q["kind"]=="short": cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div><div class='field'><input id='short{i}' placeholder='Nhập đáp án'></div></div>")
        else: cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div><div class='small'>Câu chưa hỗ trợ chấm tự động.</div></div>")
    js="""const DATA=%s;function score(){let r=0,t=0;DATA.forEach((q,i)=>{if(q.kind==='choice'){t++;let e=document.querySelector(`input[name=q${i+1}]:checked`);if(e&&+e.value===+q.correct)r++;}else if(q.kind==='tf'){q.correct.forEach((c,j)=>{t++;let e=document.querySelector(`input[name=q${i+1}_${j}]:checked`);if(e&&+e.value===(c?1:0))r++;});}else if(q.kind==='short'){t++;let e=document.getElementById(`short${i+1}`);if(e&&e.value.trim().toLowerCase()===String(q.answer||'').trim().toLowerCase())r++;}});document.getElementById('score').textContent=`✅ Đúng ${r}/${t} · Điểm ${t?(r/t*10).toFixed(2):'0.00'}/10`;MathJax.typesetPromise&&MathJax.typesetPromise();} """%payload
    body=f"<div class='wrap'><div class='panel'><div class='mh'><span>📖 {html.escape(Path(p).parent.name)} · <span class='tag {'vip' if lesson_level(p)=='VIP' else 'free'}'>{lesson_level(p)}</span></span><a class='btn' href='/member'>← Danh sách bài</a></div><div class='hero'><div id='score' class='score'>Làm xong bấm Chấm điểm</div><button class='btn' onclick='score()'>📝 Chấm điểm</button></div><div class='cards'>{''.join(cards)}</div></div></div><script>{js}</script>"
    return page("Làm bài",body)

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    msg=""
    if request.method=="POST":
        u=(request.form.get("username") or "").strip(); p=request.form.get("password") or ""
        if ADMIN_PASSWORD and u==ADMIN_USERNAME and p==ADMIN_PASSWORD:
            session.clear(); session["role"]="admin"; session["username"]=ADMIN_USERNAME; return redirect("/admin")
        msg="Sai tài khoản hoặc mật khẩu ADMIN."
    return page("ADMIN",f"<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản ADMIN</label><input name='username' value='{html.escape(ADMIN_USERNAME,quote=True)}' required></div><div class='field'><label>Mật khẩu ADMIN</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button><div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.get("/admin/logout")
def admin_logout(): session.clear(); return redirect("/admin/login")

@app.get("/admin")
@require_admin
def admin_home():
    rows=[]
    for m in load_members().get("members",[]):
        typ=account_type(m); u=str(m.get("username") or "")
        rows.append(f"<tr><td>{html.escape(u)}</td><td>{html.escape(str(m.get('name') or ''))}</td><td>{html.escape(str(m.get('class') or ''))}</td><td>{html.escape(typ)}</td><td>{html.escape(str(m.get('status') or 'ON'))}</td><td><form method='post' action='/admin/member/type' style='display:inline'><input type='hidden' name='username' value='{html.escape(u,quote=True)}'><select name='account_type'><option {'selected' if typ=='FREE' else ''}>FREE</option><option {'selected' if typ=='VIP' else ''}>VIP</option></select><button class='btn'>Quyền</button></form><form method='post' action='/admin/member/toggle' style='display:inline'><input type='hidden' name='username' value='{html.escape(u,quote=True)}'><button class='btn'>Bật/Tắt</button></form></td></tr>")
    body=f"<div class='wrap'><div class='grid'><aside class='panel'><div class='head'>⚙️ ADMIN</div><div class='body'><a class='btn' href='/admin'>👥 Thành viên</a><a class='btn' href='/admin/access'>🔐 Quyền FREE/VIP</a><a class='btn' href='/github/quan-ly'>📚 Ngân hàng GitHub</a><a class='btn' href='/admin/member/add'>➕ Thêm thành viên</a><a class='btn' href='/admin/logout'>Thoát</a></div></aside><main class='panel'><div class='mh'><span>👥 Thành viên</span><span>{len(rows)} tài khoản</span></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th><th>Thao tác</th></tr>{''.join(rows)}</table></div></main></div></div>"
    return page("ADMIN",body)

@app.route("/admin/member/add",methods=["GET","POST"])
@require_admin
def admin_add():
    msg=""
    if request.method=="POST":
        u=(request.form.get("username") or "").strip(); name=(request.form.get("name") or "").strip(); cls=(request.form.get("class") or "").strip(); p=request.form.get("password") or ""; typ=(request.form.get("account_type") or "FREE").upper(); data=load_members()
        if not u or not p: msg="Thiếu tài khoản hoặc mật khẩu."
        elif any(m.get("username")==u for m in data.get("members",[])): msg="Tài khoản đã tồn tại."
        else:
            data.setdefault("members",[]).append({"username":u,"name":name or u,"class":cls,"account_type":"VIP" if typ=="VIP" else "FREE","status":"ON","password_sha256":hashlib.sha256(p.encode()).hexdigest()})
            try: save_members(data); return redirect("/admin")
            except Exception as e: msg=str(e)
    return page("Thêm thành viên",f"<div class='wrap'><div class='panel login'><div class='head'>➕ Thêm thành viên</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Lớp</label><input name='class'></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><div class='field'><label>Quyền</label><select name='account_type'><option>FREE</option><option>VIP</option></select></div><button class='btn'>Lưu</button> <a class='btn' href='/admin'>Quay lại</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.post("/admin/member/type")
@require_admin
def admin_type():
    u=request.form.get("username",""); typ="VIP" if (request.form.get("account_type") or "FREE").upper()=="VIP" else "FREE"; data=load_members()
    for m in data.get("members",[]):
        if m.get("username")==u: m["account_type"]=typ; break
    save_members(data); return redirect("/admin")

@app.post("/admin/member/toggle")
@require_admin
def admin_toggle():
    u=request.form.get("username",""); data=load_members()
    for m in data.get("members",[]):
        if m.get("username")==u: m["status"]="OFF" if m.get("status","ON")=="ON" else "ON"; break
    save_members(data); return redirect("/admin")

@app.get("/admin/access")
@require_admin
def admin_access():
    d=index_data(); a=load_access(); cards=[]
    for x in d.get("lessons",[]):
        if not isinstance(x,dict):continue
        p=str(x.get("path") or "")
        if not safe_tex(p):continue
        lv=lesson_level(p); title=str(x.get("BaiHoc") or x.get("De") or Path(p).parent.name); c=int(x.get("questions") or x.get("count") or 0)
        cards.append(f"<div class='card'><b>{html.escape(title)}</b><div class='small'>{html.escape(p)}</div><span class='tag {'vip' if lv=='VIP' else 'free'}'>{lv}</span><span class='tag'>{c} câu</span><form method='post' action='/admin/access/save'><input type='hidden' name='path' value='{html.escape(p,quote=True)}'><select name='level'><option {'selected' if lv=='FREE' else ''}>FREE</option><option {'selected' if lv=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu quyền</button></form></div>")
    return page("Quyền bài học",f"<div class='wrap'><div class='panel'><div class='mh'><span>🔐 Phân quyền bài học</span><a class='btn' href='/admin'>← ADMIN</a></div><div class='hero'>FREE: thành viên thường + VIP · VIP: chỉ VIP</div><div class='cards'>{''.join(cards)}</div></div></div>")

@app.post("/admin/access/save")
@require_admin
def admin_access_save():
    p=request.form.get("path",""); lv="VIP" if (request.form.get("level") or "FREE").upper()=="VIP" else "FREE"; a=load_access(); a.setdefault("lessons",{})[p]=lv; save_access(a); return redirect("/admin/access")

@app.get("/github/quan-ly")
@require_admin
def github_manage():
    d=index_data(); a=load_access(); cards=[]
    for x in d.get("lessons",[]):
        if not isinstance(x,dict):continue
        p=str(x.get("path") or "")
        if not safe_tex(p):continue
        title=str(x.get("BaiHoc") or x.get("De") or Path(p).parent.name); lv=lesson_level(p); c=int(x.get("questions") or x.get("count") or 0)
        cards.append(f"<div class='card'><b>{html.escape(title)}</b><div class='small'>{html.escape(p)}</div><span class='tag {'vip' if lv=='VIP' else 'free'}'>{lv}</span><span class='tag'>{c} câu</span><a class='btn' href='/admin/edit?path={urllib.parse.quote(p,safe='')}'>✏️ Đọc / sửa .tex</a></div>")
    body=f"<div class='wrap'><div class='panel'><div class='mh'><span>📚 Ngân hàng GitHub</span><span>{int(d.get('total_files') or 0)} bài · {int(d.get('total_questions') or 0)} câu</span></div><div class='hero'><a class='btn' href='/admin/access'>🔐 Phân quyền FREE/VIP</a></div><div class='cards'>{''.join(cards)}</div></div></div>"
    return page("Ngân hàng GitHub",body)

@app.get("/admin/edit")
@require_admin
def admin_edit():
    p=request.args.get("path","")
    try: sha,text=read_tex(p)
    except Exception as e:return page("Lỗi",f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    body=f"<div class='wrap'><div class='panel'><div class='mh'><b>✏️ {html.escape(p)}</b><span><a class='btn' href='/github/quan-ly'>← Mục lục</a></span></div><textarea id='code' class='code'>{html.escape(text)}</textarea><div class='actions'><button class='btn' onclick='saveTex()'>💾 Lưu trực tiếp GitHub</button><a class='btn' href='https://github.com/{html.escape(REPO)}/blob/{urllib.parse.quote(BRANCH)}/{urllib.parse.quote(p,safe="/")}' target='_blank'>🐙 Mở GitHub</a><span id='msg'></span></div></div></div><script>const PATH={json.dumps(p,ensure_ascii=False)},SHA={json.dumps(sha)};async function saveTex(){let m=document.getElementById('msg');m.textContent='Đang lưu...';try{{let r=await fetch('/admin/api/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{path:PATH,sha:SHA,text:document.getElementById('code').value}})}});let d=await r.json();m.textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+(d.error||'Lỗi');}}catch(e){{m.textContent='❌ '+e}}}}</script>"
    return page("Sửa .tex",body)

@app.post("/admin/api/save")
@require_admin
def admin_save():
    d=request.get_json(silent=True) or {}; p=d.get("path",""); text=d.get("text"); sha=d.get("sha","")
    if not safe_tex(p) or not isinstance(text,str) or not sha:return jsonify(ok=False,error="Thiếu path/text/sha"),400
    try:
        z=gh_put(p,text,"ADMIN cập nhật .tex trực tiếp",sha); return jsonify(ok=True,commit=str((z.get("commit") or {}).get("sha") or "")[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),500

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
