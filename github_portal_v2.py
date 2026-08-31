# -*- coding: utf-8 -*-
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.parse, urllib.request, urllib.error
from functools import wraps
from pathlib import Path
from flask import Flask, Response, redirect, request, session, jsonify

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET', 'change-this-on-render')
REPO = os.getenv('GITHUB_REPO', 'pythonminh/luyen-de-vat-ly').strip()
BRANCH = os.getenv('GITHUB_BRANCH', 'main').strip() or 'main'
TOKEN = os.getenv('GITHUB_TOKEN', '').strip()
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'ADMIN').strip() or 'ADMIN'
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '').strip()
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'bank_index.json'
MEMBERS = ROOT / 'members.json'
ACCESS = ROOT / 'lesson_access.json'
API = 'https://api.github.com'
RAW = 'https://raw.githubusercontent.com'
EX_RE = re.compile(r'\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}', re.I)
DANG_RE = re.compile(r'\\dangbt\s*\{([^{}]*)\}', re.I)
CHOICE_RE = re.compile(r'\\choice\b', re.I)
TF_RE = re.compile(r'\\choiceTF\b', re.I)
SHORT_RE = re.compile(r'\\shortans\s*\{([^{}]*)\}', re.I)
CSS='''*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial}.top{background:#1769d2;color:#fff;padding:11px 16px}.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b9d5f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin:3px}.nav a{background:transparent;color:#fff;border-color:#ffffff66}.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid #d6e0ea;border-radius:12px;overflow:hidden}.head,.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.mh{display:flex;justify-content:space-between;align-items:center;gap:8px}.body{padding:12px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px;padding:8px}.card{border:1px solid #dce5ed;border-radius:9px;padding:10px;background:#fff}.small{font-size:11px;color:#64748b}.field{margin:8px 0}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.tag{display:inline-block;padding:3px 7px;border:1px solid #cbd5e1;border-radius:999px;font-size:10px;margin:4px 3px 0 0}.free{border-color:#86efac;background:#f0fdf4;color:#166534}.vip{border-color:#f9a8d4;background:#fdf2f8;color:#9d174d}.notice{margin:10px 0;padding:10px;border-radius:8px;border:1px solid #93c5fd;background:#eff6ff}.err{color:#b91c1c;font-weight:800}.ok{color:#15803d;font-weight:800}.login{max-width:430px;margin:65px auto}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:7px;border-bottom:1px solid #e5e7eb;text-align:left}.qtext{line-height:1.6;font-size:15px}.opt{display:block;padding:9px;border:1px solid #dbeafe;border-radius:8px;margin:6px 0}.section{margin:8px 0;padding:8px;border:1px solid #dbeafe;border-radius:8px;background:#f8fbff}.score{padding:10px;border:1px solid #86efac;background:#f0fdf4;border-radius:9px;font-weight:900}.code{width:100%;height:72vh;resize:vertical;border:1px solid #cbd5e1;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}@media(max-width:800px){.login{margin:25px auto}}'''

def gh(path,method='GET',data=None):
    if not TOKEN: raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    body=None if data is None else json.dumps(data,ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(API+path,data=body,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl-portal-v2','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=20) as r: return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8','replace')
        try: msg=json.loads(raw).get('message',raw)
        except Exception: msg=raw
        raise RuntimeError(f'GitHub API {e.code}: {msg}')

def gh_get(path):
    o,r=REPO.split('/',1); return gh(f'/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe="/")}?ref={urllib.parse.quote(BRANCH)}')
def gh_put(path,text,message,sha=None):
    o,r=REPO.split('/',1); d={'message':message,'content':base64.b64encode(text.encode('utf-8')).decode('ascii'),'branch':BRANCH}
    if sha: d['sha']=sha
    return gh(f'/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe="/")}', 'PUT', d)

def read_local(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def members(): return read_local(MEMBERS,{'schema':2,'members':[]})
def access():
    d=read_local(ACCESS,{'schema':1,'default':'FREE','lessons':{}}); d.setdefault('default','FREE'); d.setdefault('lessons',{}); return d
def index_data():
    if INDEX.exists(): return read_local(INDEX,{})
    o,r=REPO.split('/',1); u=f'{RAW}/{o}/{r}/{urllib.parse.quote(BRANCH)}/bank_index.json'
    with urllib.request.urlopen(u,timeout=12) as x:return json.loads(x.read().decode('utf-8'))

def sync_json(filename,data,message):
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'; cur=gh_get(filename); gh_put(filename,text,message,cur.get('sha')); (ROOT/filename).write_text(text,encoding='utf-8')

def current_member():
    u=session.get('username')
    if not u:return None
    for m in members().get('members',[]):
        if m.get('username')==u and m.get('status','ON')=='ON':return m
    return None

def is_vip(m):return str((m or {}).get('account_type') or 'FREE').upper() in {'VIP','S.VIP'}
def lesson_level(path):return str(access().get('lessons',{}).get(path,access().get('default','FREE'))).upper()
def allowed(m,path):return lesson_level(path)=='FREE' or is_vip(m)
def safe_tex(path):return isinstance(path,str) and path.startswith('ngan-hang/') and path.lower().endswith('.tex') and '..' not in path

def read_tex(path):
    if not safe_tex(path):raise ValueError('Đường dẫn .tex không hợp lệ')
    d=gh_get(path); text=base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace'); return d.get('sha',''),text

def brace_arg(s,pos):
    while pos<len(s) and s[pos].isspace():pos+=1
    if pos>=len(s) or s[pos]!='{':return None,pos
    dep=0;start=pos+1;i=pos
    while i<len(s):
        if s[i]=='{' and (i==0 or s[i-1]!='\\'):dep+=1
        elif s[i]=='}' and (i==0 or s[i-1]!='\\'):
            dep-=1
            if dep==0:return s[start:i],i+1
        i+=1
    return None,len(s)

def args_for(s,cmd):
    m=re.search(re.escape(cmd)+r'\b',s,re.I)
    if not m:return []
    out=[];p=m.end()
    while True:
        a,p2=brace_arg(s,p)
        if a is None:break
        out.append(a);p=p2
    return out

def clean(s):
    s=re.sub(r'%.*','',s);s=DANG_RE.sub('',s);s=re.sub(r'\\ID\s*:\s*[^\n]*','',s,flags=re.I);return s.strip()
def strip_true(s):return re.sub(r'^\s*\\True\s*','',s,flags=re.I).strip()
def parse_q(b):
    tf=args_for(b,'\\choiceTF')
    if tf:return {'kind':'tf','text':clean(TF_RE.split(b,1)[0]),'statements':[strip_true(x) for x in tf], 'correct':[bool(re.match(r'^\s*\\True\b',x,re.I)) for x in tf]}
    ch=args_for(b,'\\choice')
    if ch:return {'kind':'choice','text':clean(CHOICE_RE.split(b,1)[0]),'options':[strip_true(x) for x in ch[:4]],'correct':next((i for i,x in enumerate(ch[:4]) if re.match(r'^\s*\\True\b',x,re.I)),0)}
    sm=SHORT_RE.search(b)
    if sm:return {'kind':'short','text':clean(b[:sm.start()]),'answer':sm.group(1).strip()}
    return {'kind':'unsupported','text':clean(b)}
def lesson_questions(path):_,t=read_tex(path);return [parse_q(b) for b in EX_RE.findall(t)]

def page(title,body):
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"+f"<title>{html.escape(title)}</title><style>{CSS}</style><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><div class='row'><div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div><div class='sub'>Nguồn chính: GitHub / ngan-hang/*.tex</div></div><div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"+body+'</body></html>',mimetype='text/html')

def req_member(f):
    @wraps(f)
    def w(*a,**k):
        if session.get('role')!='member' or not current_member():session.clear();return redirect('/member/login')
        return f(*a,**k)
    return w
def req_admin(f):
    @wraps(f)
    def w(*a,**k):
        if session.get('role')!='admin':return redirect('/admin/login')
        return f(*a,**k)
    return w

@app.get('/')
def root():return redirect('/member/login')
@app.get('/github/repo')
def repo():return redirect(f'https://github.com/{REPO}')

@app.route('/member/login',methods=['GET','POST'])
def member_login():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();p=request.form.get('password') or '';h=hashlib.sha256(p.encode()).hexdigest()
        for m in members().get('members',[]):
            if m.get('username')==u and m.get('password_sha256')==h and m.get('status','ON')=='ON':
                session.clear();session.update(role='member',username=u);return redirect('/member')
        msg='Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa.'
    return page('Đăng nhập',"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a>"+f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.route('/member/register',methods=['GET','POST'])
def member_register():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();n=(request.form.get('name') or '').strip();p=request.form.get('password') or '';d=members()
        if not u or not p:msg='Thiếu tài khoản hoặc mật khẩu.'
        elif any(x.get('username')==u for x in d.get('members',[])):msg='Tài khoản đã tồn tại.'
        else:
            d.setdefault('members',[]).append({'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
            try:sync_json('members.json',d,'Đăng ký thành viên');session.clear();session.update(role='member',username=u);return redirect('/member')
            except Exception as e:msg=str(e)
    return page('Đăng ký',"<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký FREE</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng ký</button>"+f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.get('/member/logout')
def member_logout():session.clear();return redirect('/member/login')
@app.get('/member')
@req_member
def member_home():
    m=current_member();d=index_data();vip=is_vip(m);cards=[]
    for x in d.get('lessons',[]):
        if not isinstance(x,dict):continue
        path=str(x.get('path') or '');
        if not safe_tex(path):continue
        level=lesson_level(path);ok=allowed(m,path);title=str(x.get('BaiHoc') or x.get('De') or Path(path).parent.name);cnt=int(x.get('questions') or x.get('count') or 0)
        act=f"<a class='btn' href='/member/lesson?path={urllib.parse.quote(path,safe='')}'>📝 Làm bài</a>" if ok else "<span class='tag vip'>🔒 Chỉ VIP</span>"
        cards.append(f"<div class='card'><b>{html.escape(title)}</b><div class='small'>{html.escape(str(x.get('Mon') or ''))} · {html.escape(str(x.get('Lop') or ''))}</div><span class='tag {'vip' if level=='VIP' else 'free'}'>{level}</span><span class='tag'>{cnt} câu</span><div>{act}</div></div>")
    rights='VIP – xem, làm và chấm điểm FREE + VIP' if vip else 'FREE – chỉ xem, làm và chấm điểm bài FREE'
    info=f"<div class='notice'>👤 <b>Tài khoản:</b> {html.escape(str(m.get('username')))} · <b>Họ tên:</b> {html.escape(str(m.get('name') or ''))}<br>🔑 <b>Quyền:</b> {rights}</div>"
    return page('Thành viên',f"<div class='wrap'><div class='panel'><div class='mh'><span>📚 Ngân hàng bài tập</span><a class='btn' href='/member/logout'>Thoát</a></div>{info}<div class='cards'>{''.join(cards)}</div></div></div>")

@app.get('/member/lesson')
@req_member
def member_lesson():
    m=current_member();path=request.args.get('path','')
    if not allowed(m,path):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    try:qs=lesson_questions(path)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    data=json.dumps(qs,ensure_ascii=False)
    cards=[]
    for i,q in enumerate(qs,1):
        t=html.escape(q.get('text',''))
        if q.get('kind')=='choice': cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div>"+''.join(f"<label class='opt'><input type='radio' name='q{i}' value='{j}'> {chr(65+j)}. {html.escape(o)}</label>" for j,o in enumerate(q.get('options',[])))+"</div>")
        elif q.get('kind')=='tf': cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div>"+''.join(f"<div class='section'><b>{j+1}.</b> {html.escape(s)}<br><label><input type='radio' name='q{i}_{j}' value='1'> Đúng</label> &nbsp; <label><input type='radio' name='q{i}_{j}' value='0'> Sai</label></div>" for j,s in enumerate(q.get('statements',[])))+"</div>")
        elif q.get('kind')=='short':cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div><input class='field' id='s{i}' placeholder='Nhập đáp án'></div>")
        else:cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div></div>")
    js="""const D=%s;function grade(){let r=0,n=0;D.forEach((q,i)=>{if(q.kind==='choice'){n++;let e=document.querySelector(`input[name=q${i+1}]:checked`);if(e&&+e.value===+q.correct)r++;}else if(q.kind==='tf'){q.correct.forEach((c,j)=>{n++;let e=document.querySelector(`input[name=q${i+1}_${j}]:checked`);if(e&&+e.value===(c?1:0))r++;});}else if(q.kind==='short'){n++;let e=document.getElementById('s'+(i+1));if(e&&e.value.trim().toLowerCase()===String(q.answer||'').trim().toLowerCase())r++;}});document.getElementById('score').textContent=`✅ Đúng ${r}/${n} · Điểm ${(n?r/n*10:0).toFixed(2)}/10`;window.scrollTo({top:0,behavior:'smooth'});}MathJax.typeset();"""%data
    return page('Làm bài',f"<div class='wrap'><div class='panel'><div class='mh'><span>📖 {html.escape(Path(path).parent.name)}</span><a class='btn' href='/member'>← Bài học</a></div><div class='body'><div id='score' class='score'>Làm xong bấm Chấm điểm</div><button class='btn' onclick='grade()'>📝 Chấm điểm</button></div><div class='cards'>{''.join(cards)}</div></div></div><script>{js}</script>")

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();p=request.form.get('password') or ''
        if u==ADMIN_USERNAME and ADMIN_PASSWORD and p==ADMIN_PASSWORD:
            session.clear();session['role']='admin';return redirect('/admin')
        msg='Tài khoản hoặc mật khẩu ADMIN không đúng.'
    return page('ADMIN',"<div class='wrap'><div class='panel login'><div class='head'>🔐 Đăng nhập ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản ADMIN</label><input name='username' value='ADMIN' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button>"+f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')
@app.get('/admin')
@req_admin
def admin_home():
    d=members();rows=[]
    for m in d.get('members',[]):
        typ=str(m.get('account_type') or 'FREE').upper()
        rows.append(f"<tr><td>{html.escape(str(m.get('username') or ''))}</td><td>{html.escape(str(m.get('name') or ''))}</td><td>{html.escape(str(m.get('class') or ''))}</td><td><form method='post' action='/admin/member/type'><input type='hidden' name='username' value='{html.escape(str(m.get('username') or ''),quote=True)}'><select name='account_type'><option {'selected' if typ=='FREE' else ''}>FREE</option><option {'selected' if typ=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu quyền</button></form></td><td>{html.escape(str(m.get('status') or 'ON'))}</td></tr>")
    return page('ADMIN',"<div class='wrap'><div class='grid'><main class='panel'><div class='mh'><span>👥 Thành viên</span><span><a class='btn' href='/admin/access'>🔐 Quyền bài</a><a class='btn' href='/github/quan-ly'>📚 Ngân hàng</a><a class='btn' href='/admin/member/add'>+ Thêm</a><a class='btn' href='/admin/logout'>Thoát</a></span></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th></tr>"+''.join(rows)+"</table></div></main></div></div>")

@app.route('/admin/member/add',methods=['GET','POST'])
@req_admin
def admin_add():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();n=(request.form.get('name') or '').strip();c=(request.form.get('class') or '').strip();p=request.form.get('password') or '';typ=(request.form.get('account_type') or 'FREE').upper();d=members()
        if not u or not p:msg='Thiếu tài khoản hoặc mật khẩu.'
        elif any(m.get('username')==u for m in d.get('members',[])):msg='Tài khoản đã tồn tại.'
        else:
            d.setdefault('members',[]).append({'username':u,'name':n or u,'class':c,'account_type':'VIP' if typ=='VIP' else 'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
            try:sync_json('members.json',d,'ADMIN thêm thành viên');return redirect('/admin')
            except Exception as e:msg=str(e)
    return page('Thêm thành viên',"<div class='wrap'><div class='panel login'><div class='head'>➕ Thêm thành viên</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Lớp</label><input name='class'></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><div class='field'><label>Quyền</label><select name='account_type'><option>FREE</option><option>VIP</option></select></div><button class='btn'>Lưu</button> <a class='btn' href='/admin'>Quay lại</a>"+f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.post('/admin/member/type')
@req_admin
def member_type():
    u=request.form.get('username','');typ=(request.form.get('account_type') or 'FREE').upper();d=members()
    for m in d.get('members',[]):
        if m.get('username')==u:m['account_type']='VIP' if typ=='VIP' else 'FREE';break
    try:sync_json('members.json',d,'ADMIN đổi quyền FREE VIP')
    except Exception:return page('Lỗi','<div class="wrap"><div class="panel"><div class="body err">Không lưu được members.json</div></div></div>')
    return redirect('/admin')

@app.get('/admin/access')
@req_admin
def admin_access():
    idx=index_data();a=access();cards=[]
    for x in idx.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '')
        if not safe_tex(p):continue
        level=lesson_level(p);title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name)
        cards.append(f"<div class='card'><b>{html.escape(title)}</b><div class='small'>{html.escape(p)}</div><span class='tag {'vip' if level=='VIP' else 'free'}'>{level}</span><form method='post' action='/admin/access/save'><input type='hidden' name='path' value='{html.escape(p,quote=True)}'><select name='level'><option {'selected' if level=='FREE' else ''}>FREE</option><option {'selected' if level=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu quyền</button></form></div>")
    return page('Quyền FREE/VIP',"<div class='wrap'><div class='panel'><div class='mh'><span>🔐 Phân quyền bài học</span><a class='btn' href='/admin'>← ADMIN</a></div><div class='cards'>"+''.join(cards)+"</div></div></div>")

@app.post('/admin/access/save')
@req_admin
def access_save():
    p=request.form.get('path','');lvl=(request.form.get('level') or 'FREE').upper();d=access();d.setdefault('lessons',{})[p]='VIP' if lvl=='VIP' else 'FREE';
    try:save_access_local=d; text=json.dumps(d,ensure_ascii=False,indent=2)+'\n'; ACCESS.write_text(text,encoding='utf-8');cur=gh_get('lesson_access.json');gh_put('lesson_access.json',text,'ADMIN cập nhật quyền bài học',cur.get('sha'))
    except Exception:return page('Lỗi','<div class="wrap"><div class="panel"><div class="body err">Không lưu được quyền bài học lên GitHub.</div></div></div>')
    return redirect('/admin/access')

@app.get('/github/quan-ly')
@req_admin
def github_manage():
    d=index_data();a=access();cards=[]
    for x in d.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '')
        if not safe_tex(p):continue
        title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name);cnt=int(x.get('questions') or x.get('count') or 0);level=lesson_level(p)
        cards.append(f"<div class='card'><b>{html.escape(title)}</b><div class='small'>{html.escape(p)}</div><span class='tag {'vip' if level=='VIP' else 'free'}'>{level}</span><span class='tag'>{cnt} câu</span><br><a class='btn' href='/admin/edit?path={urllib.parse.quote(p,safe="")}'>✏️ Sửa .tex</a></div>")
    return page('Ngân hàng GitHub',"<div class='wrap'><div class='panel'><div class='mh'><span>📚 GitHub / ngan-hang</span><span>"+str(int(d.get('total_files') or 0))+" bài · "+str(int(d.get('total_questions') or 0))+" câu</span></div><div class='hero'><a class='btn' href='/admin/access'>🔐 Phân quyền FREE/VIP</a></div><div class='cards'>"+''.join(cards)+"</div></div></div>")

@app.get('/admin/edit')
@req_admin
def admin_edit():
    p=request.args.get('path','')
    try:sha,text=read_tex(p)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    return page('Sửa .tex',"<div class='wrap'><div class='panel'><div class='mh'><b>✏️ "+html.escape(p)+"</b><span><a class='btn' href='/github/quan-ly'>← Mục lục</a><a class='btn' target='_blank' href='https://github.com/"+html.escape(REPO)+"/blob/"+urllib.parse.quote(BRANCH)+"/"+urllib.parse.quote(p,safe='/')+"'>🐙 GitHub</a></span></div><div class='body'><textarea id='code' class='code'>"+html.escape(text)+"</textarea><div><button class='btn' onclick='saveTex()'>💾 Lưu trực tiếp GitHub</button><span id='msg'></span></div></div></div></div><script>const P="+json.dumps(p)+",S="+json.dumps(sha)+";async function saveTex(){let m=document.getElementById('msg');m.textContent='Đang lưu...';try{let r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:P,sha:S,text:document.getElementById('code').value})});let d=await r.json();m.textContent=d.ok?' ✅ Đã commit GitHub '+d.commit:' ❌ '+d.error;}catch(e){m.textContent=' ❌ '+e}}</script>")

@app.post('/admin/api/save')
@req_admin
def admin_save():
    d=request.get_json(silent=True) or {};p=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not safe_tex(p) or not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu dữ liệu'),400
    try:r=gh_put(p,text,'ADMIN cập nhật .tex trực tiếp',sha);return jsonify(ok=True,commit=str((r.get('commit') or {}).get('sha') or '')[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))