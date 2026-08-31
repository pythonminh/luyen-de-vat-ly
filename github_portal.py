# -*- coding: utf-8 -*-
"""Portal thành viên + ADMIN cho ngân hàng GitHub."""
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from functools import wraps
from flask import Flask, Response, jsonify, request, redirect, session

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET", "doi-APP_SECRET-tren-Render")
REPO = os.getenv("GITHUB_REPO", "pythonminh/luyen-de-vat-ly").strip()
BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "bank_index.json"
MEMBERS = ROOT / "members.json"
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
QRE = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
DRE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)

CSS = r'''*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial}.top{background:#1769d2;color:#fff;padding:10px 16px}.row{display:flex;gap:10px;align-items:center}.brand{font-size:20px;font-weight:900}.sub{font-size:11px}.nav{margin-left:12px}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b9d4f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin-right:5px}.nav a{background:transparent;color:#fff;border-color:#ffffff66}.wrap{max-width:1450px;margin:auto;padding:12px}.grid{display:grid;grid-template-columns:260px 1fr;gap:10px}.panel{background:#fff;border:1px solid #d6e0ea;border-radius:12px;overflow:hidden}.head{padding:10px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.body{padding:10px}.field{margin:0 0 8px}.field label{display:block;font-size:10px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;display:flex;justify-content:space-between;font-weight:900}.book{padding:10px}.subject{margin-bottom:10px}.sh{padding:9px 10px;border-radius:10px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:900}.chapter{margin:7px 0;border:1px solid #c8ddf7;border-radius:9px;overflow:hidden}.ch{padding:7px 9px;background:#dbeafe;color:#1e3a8a;font-weight:900}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:7px;padding:7px}.card{border:1px solid #dce5ed;border-radius:9px;padding:9px}.small{font-size:10px;color:#64748b}.tag{display:inline-block;padding:3px 6px;border:1px solid #cbd5e1;border-radius:999px;font-size:9px;margin:4px 3px 0 0}.dang{margin-top:5px;padding:6px;border:1px solid #d5e7fb;border-radius:7px;background:#f8fbff}.dr{display:flex;justify-content:space-between;border:1px solid #dbeafe;border-radius:6px;padding:5px;margin:3px 0;font-size:10px;cursor:pointer}.ok{color:#15803d;font-weight:800}.err{color:#b91c1c;font-weight:800}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:7px;border-bottom:1px solid #e5e7eb;text-align:left}.login{max-width:420px;margin:70px auto}.hero{padding:16px;text-align:center}.count{font-size:11px;border:1px solid #cbd5e1;border-radius:999px;padding:3px 7px}.modal{position:fixed;inset:0;background:#0f172a99;display:flex;align-items:center;justify-content:center;padding:12px}.hide{display:none}.box{background:#fff;width:min(1200px,96vw);height:min(88vh,900px);border-radius:12px;display:flex;flex-direction:column;overflow:hidden}.code{flex:1;resize:none;border:1px solid #cbd5e1;border-radius:7px;margin:8px;padding:10px;font:12px/1.5 Consolas,monospace}.actions{padding:0 8px 8px}.cardrow{display:flex;justify-content:space-between;align-items:center;gap:8px}@media(max-width:800px){.grid{grid-template-columns:1fr}.login{margin:25px auto}}'''

def gh(path, method="GET", data=None):
    if not TOKEN: raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode()
    req = urllib.request.Request(API + path, data=body, method=method, headers={
        "Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28","User-Agent":"ldvl-portal","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg=e.read().decode("utf-8","replace")
        try: msg=json.loads(msg).get("message",msg)
        except Exception: pass
        raise RuntimeError(f"GitHub API {e.code}: {msg}")

def index_data():
    if INDEX.exists(): return json.loads(INDEX.read_text(encoding="utf-8"))
    o,r=REPO.split("/",1); u=f"{RAW}/{o}/{r}/{urllib.parse.quote(BRANCH)}/bank_index.json"
    with urllib.request.urlopen(u,timeout=12) as q:return json.loads(q.read().decode())

def safe_tex(p): return isinstance(p,str) and p.startswith("ngan-hang/") and p.lower().endswith(".tex") and ".." not in p

def read_tex(p):
    if not safe_tex(p): raise ValueError("Đường dẫn .tex không hợp lệ")
    o,r=REPO.split("/",1); q=f"/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe='/')}?ref={urllib.parse.quote(BRANCH)}"
    d=gh(q); text=base64.b64decode((d.get("content") or "").replace("\n","")).decode("utf-8","replace")
    return d.get("sha","") , text

def qcount(text): return len(QRE.findall(text or ""))

def load_members():
    try:return json.loads(MEMBERS.read_text(encoding="utf-8"))
    except Exception:return {"members":[],"schema":1}

def save_members(data):
    MEMBERS.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def gh_save_members(data):
    if not TOKEN: raise RuntimeError("Thiếu GITHUB_TOKEN")
    o,r=REPO.split("/",1); path="members.json"; q=f"/repos/{o}/{r}/contents/{path}?ref={urllib.parse.quote(BRANCH)}"
    d=gh(q); content=base64.b64encode((json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode()).decode()
    gh(f"/repos/{o}/{r}/contents/{path}","PUT",{"message":"Admin cập nhật thành viên","content":content,"branch":BRANCH,"sha":d.get("sha")})

def admin_ok(): return bool(session.get("role")=="admin")
def member_ok(): return bool(session.get("role")=="member")
def require_admin(f):
    @wraps(f)
    def w(*a,**kw): return f(*a,**kw) if admin_ok() else redirect('/admin/login')
    return w

def require_member(f):
    @wraps(f)
    def w(*a,**kw): return f(*a,**kw) if member_ok() else redirect('/member/login')
    return w

def page(title,body):
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{CSS}</style></head><body><div class="top"><div class="row"><div><div class="brand">📚 Luyện đề AI · Thầy Minh</div><div class="sub">Nguồn chính: GitHub / ngan-hang/*.tex</div></div><div class="nav"><a href="/member">Thành viên</a><a href="/admin">ADMIN</a><a href="/github/repo" target="_blank">🐙 GitHub</a></div></div></div>{body}</body></html>'''

@app.get('/')
def root(): return redirect('/member')
@app.get('/github/repo')
def repo(): return redirect(f'https://github.com/{REPO}')

@app.route('/member/login',methods=['GET','POST'])
def member_login():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip(); p=request.form.get('password') or ''
        data=load_members()
        for m in data.get('members',[]):
            if m.get('username')==u and m.get('password_sha256')==hashlib.sha256(p.encode()).hexdigest() and m.get('status','ON')=='ON':
                session.clear(); session.update(role='member',username=u,name=m.get('name') or u); return redirect('/member')
        msg='Sai tài khoản hoặc mật khẩu.'
    body=f'''<div class="wrap"><div class="panel login"><div class="head">👤 Đăng nhập thành viên</div><div class="body"><form method="post"><div class="field"><label>Tài khoản</label><input name="username" required></div><div class="field"><label>Mật khẩu</label><input name="password" type="password" required></div><button class="btn">Đăng nhập</button> <a class="btn" href="/member/register">Đăng ký</a><div class="err">{msg}</div></form></div></div></div>'''
    return page('Đăng nhập thành viên',body)

@app.route('/member/register',methods=['GET','POST'])
def member_register():
    msg=''; ok=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip(); name=(request.form.get('name') or '').strip(); p=request.form.get('password') or ''
        data=load_members(); users={m.get('username') for m in data.get('members',[])}
        if not u or not p: msg='Thiếu tài khoản/mật khẩu.'
        elif u in users: msg='Tài khoản đã tồn tại.'
        else:
            data.setdefault('members',[]).append({'username':u,'name':name or u,'password_sha256':hashlib.sha256(p.encode()).hexdigest(),'class':'','status':'ON'})
            save_members(data); gh_save_members(data); ok='Đăng ký thành công. Có thể đăng nhập.'
    body=f'''<div class="wrap"><div class="panel login"><div class="head">📝 Đăng ký thành viên</div><div class="body"><form method="post"><div class="field"><label>Tên hiển thị</label><input name="name"></div><div class="field"><label>Tài khoản</label><input name="username" required></div><div class="field"><label>Mật khẩu</label><input name="password" type="password" required></div><button class="btn">Tạo tài khoản</button> <a class="btn" href="/member/login">Quay lại</a><div class="err">{msg}</div><div class="ok">{ok}</div></form></div></div></div>'''
    return page('Đăng ký',body)

@app.get('/member/logout')
def member_logout(): session.clear(); return redirect('/member/login')

@app.get('/member')
@require_member
def member_home():
    d=index_data(); cards=''
    for x in d.get('lessons',[]):
        if not isinstance(x,dict): continue
        p=str(x.get('path') or '')
        if not safe_tex(p): continue
        title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name); c=int(x.get('questions') or x.get('count') or 0)
        cards += f'<div class="card"><div class="cardrow"><b>{title}</b><span class="count">{c} câu</span></div><div class="small">{x.get("Mon","")} · {x.get("Lop","")} · {x.get("Chuong","")}</div><div style="margin-top:6px"><a class="btn" href="/member/lesson?path={urllib.parse.quote(p)}">Làm bài</a></div></div>'
    body=f'''<div class="wrap"><div class="panel"><div class="mh"><span>👤 Xin chào {session.get('name') or session.get('username')}</span><span><a class="btn" href="/member/logout">Thoát</a></span></div><div class="book"><div class="hero"><h2>Chọn bài để học</h2><div class="small">{int(d.get('total_files') or 0)} bài · {int(d.get('total_questions') or 0)} câu</div></div><div class="cards">{cards}</div></div></div></div>'''
    return page('Trang thành viên',body)

@app.get('/member/lesson')
@require_member
def member_lesson():
    p=request.args.get('path',''); sha,text=read_tex(p); qs=QRE.findall(text)
    items=''.join(f'<div class="card"><b>Câu {i}</b><pre style="white-space:pre-wrap;font:12px Segoe UI">{q}</pre></div>' for i,q in enumerate(qs,1))
    body=f'''<div class="wrap"><div class="panel"><div class="mh"><span>📖 {Path(p).parent.name}</span><a class="btn" href="/member">← Danh sách bài</a></div><div class="book"><div class="cards">{items}</div></div></div></div>'''
    return page('Làm bài',body)

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        if ADMIN_PASSWORD and request.form.get('password')==ADMIN_PASSWORD:
            session.clear();session.update(role='admin');return redirect('/admin')
        msg='Mật khẩu ADMIN không đúng.'
    body=f'''<div class="wrap"><div class="panel login"><div class="head">🔐 ADMIN</div><div class="body"><form method="post"><div class="field"><label>Mật khẩu ADMIN</label><input name="password" type="password" required></div><button class="btn">Đăng nhập</button><div class="err">{msg}</div></form></div></div></div>'''
    return page('ADMIN',body)

@app.get('/admin/logout')
def admin_logout(): session.clear(); return redirect('/admin/login')

@app.get('/admin')
@require_admin
def admin_home():
    data=load_members(); rows=''.join(f'<tr><td>{m.get("username","")}</td><td>{m.get("name","")}</td><td>{m.get("class","")}</td><td>{m.get("status","ON")}</td><td><form method="post" action="/admin/member/toggle" style="display:inline"><input type="hidden" name="username" value="{m.get("username","")}"><button class="btn">Bật/Tắt</button></form></td></tr>' for m in data.get('members',[]))
    body=f'''<div class="wrap"><div class="grid"><aside class="panel"><div class="head">⚙️ ADMIN</div><div class="body"><a class="btn" href="/admin">Thành viên</a><a class="btn" href="/github/quan-ly">Ngân hàng câu hỏi</a><a class="btn" href="/admin/logout">Thoát</a><hr><div class="small">Nguồn câu hỏi: GitHub<br>Người dùng: members.json</div></div></aside><main class="panel"><div class="mh"><span>👥 Danh sách thành viên</span><a class="btn" href="/admin/member/add">+ Thêm</a></div><div class="body"><table class="table"><tr><th>Tài khoản</th><th>Tên</th><th>Lớp</th><th>Trạng thái</th><th></th></tr>{rows}</table></div></main></div></div>'''
    return page('Quản trị',body)

@app.route('/admin/member/add',methods=['GET','POST'])
@require_admin
def admin_add():
    msg='';ok=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip(); name=(request.form.get('name') or '').strip(); cls=(request.form.get('class') or '').strip(); p=request.form.get('password') or ''
        data=load_members(); users={m.get('username') for m in data.get('members',[])}
        if u in users: msg='Tài khoản đã tồn tại.'
        elif not u or not p: msg='Thiếu tài khoản/mật khẩu.'
        else:
            data.setdefault('members',[]).append({'username':u,'name':name or u,'class':cls,'status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()}); save_members(data); gh_save_members(data); ok='Đã thêm thành viên.'
    body=f'''<div class="wrap"><div class="panel login"><div class="head">➕ Thêm thành viên</div><div class="body"><form method="post"><div class="field"><label>Tên</label><input name="name"></div><div class="field"><label>Tài khoản</label><input name="username" required></div><div class="field"><label>Lớp</label><input name="class"></div><div class="field"><label>Mật khẩu</label><input name="password" type="password" required></div><button class="btn">Lưu</button> <a class="btn" href="/admin">Quay lại</a><div class="err">{msg}</div><div class="ok">{ok}</div></form></div></div></div>'''
    return page('Thêm thành viên',body)

@app.post('/admin/member/toggle')
@require_admin
def admin_toggle():
    u=request.form.get('username',''); data=load_members()
    for m in data.get('members',[]):
        if m.get('username')==u: m['status']='OFF' if m.get('status','ON')=='ON' else 'ON'
    save_members(data); gh_save_members(data); return redirect('/admin')

@app.get('/github/quan-ly')
@require_admin
def github_manage():
    d=index_data(); cards=''.join(f'<div class="card"><div class="lt"><b>{x.get("BaiHoc") or x.get("De")}</b></div><div class="small">{x.get("path")}</div><div><span class="tag">{int(x.get("questions") or 0)} câu</span></div><a class="btn" href="/admin/edit?path={urllib.parse.quote(str(x.get("path") or ""))}">✏️ Mở / sửa .tex</a></div>' for x in d.get('lessons',[]) if isinstance(x,dict) and safe_tex(str(x.get('path') or '')))
    body=f'''<div class="wrap"><div class="panel"><div class="mh"><span>📚 Mục lục GitHub</span><span>{int(d.get('total_files') or 0)} bài · {int(d.get('total_questions') or 0)} câu</span></div><div class="cards">{cards}</div></div></div>'''
    return page('Ngân hàng GitHub',body)

@app.get('/admin/edit')
@require_admin
def admin_edit():
    p=request.args.get('path',''); sha,text=read_tex(p)
    body=f'''<div class="wrap"><div class="panel"><div class="mh"><b>✏️ {p}</b><a class="btn" href="/github/quan-ly">← Mục lục</a></div><textarea id="code" class="code">{text}</textarea><div class="actions"><button class="btn" onclick="saveTex()">💾 Lưu trực tiếp GitHub</button><span id="msg"></span></div></div></div><script>const path={json.dumps(p,ensure_ascii=False)},sha={json.dumps(sha)};async function saveTex(){const msg=document.getElementById('msg');msg.textContent='Đang lưu...';try{const r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,sha,text:document.getElementById('code').value})});const d=await r.json();msg.textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+(d.error||'Lỗi');}catch(e){msg.textContent='❌ '+e}}</script>'''
    return page('Sửa .tex',body)

@app.post('/admin/api/save')
@require_admin
def admin_save():
    d=request.get_json(silent=True) or {}; p=d.get('path',''); text=d.get('text'); sha=d.get('sha','')
    if not safe_tex(p) or not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu path/text/sha'),400
    o,r=REPO.split('/',1);q=f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}'
    z=gh(q,'PUT',{'message':'ADMIN cập nhật .tex trực tiếp','content':base64.b64encode(text.encode()).decode(),'branch':BRANCH,'sha':sha})
    return jsonify(ok=True,commit=str((z.get('commit') or {}).get('sha') or '')[:12])

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
