# -*- coding: utf-8 -*-
"""Clean GitHub-only practice portal for Render.
Source of questions: bank_index.json + ngan-hang/**/*.tex
No Google Sheet is used for the question flow.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import random
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, session

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or os.getenv("APP_SECRET") or "dev-change-me"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(os.getenv("RENDER") == "true" or os.getenv("RENDER") == "1"),
)

REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = (os.getenv("GITHUB_BRANCH") or "main").strip() or "main"
TOKEN = (os.getenv("GITHUB_TOKEN") or "").strip()
ADMIN_USER = (os.getenv("ADMIN_USERNAME") or "ADMIN").strip() or "ADMIN"
ADMIN_PASS = (os.getenv("ADMIN_PASSWORD") or "").strip()
GEMINI_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.getenv("GEMINI_REVIEW_MODEL") or "gemini-2.5-flash").strip()

ROOT = Path(__file__).resolve().parent
INDEX_FILE = ROOT / "bank_index.json"
MEMBERS_FILE = ROOT / "members.json"
ACCESS_FILE = ROOT / "lesson_access.json"

EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}", re.I)
DANG_RE = re.compile(r"\\dang(?:bt)?\s*\{([^{}]*)\}", re.I)
LEVEL_RE = re.compile(r"%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\r\n%]+)", re.I)
SHORT_RE = re.compile(r"\\shortans\b", re.I)

CSS = r"""
:root{--blue:#176bd3;--blue2:#0f57b4;--line:#d7e2ee;--bg:#f3f7fc;--green:#159447;--red:#cf2d38;--gold:#c98600}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#19324d;font:14px/1.45 Segoe UI,Arial,sans-serif}
a{text-decoration:none;color:#145bb0}.top{background:var(--blue);color:#fff}.topin{max-width:1500px;margin:auto;padding:9px 14px;display:flex;align-items:center;gap:14px}.brand{font-weight:900;font-size:20px}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}.nav a{color:#fff;border:1px solid #ffffff55;background:#ffffff15;padding:7px 10px;border-radius:8px;font-weight:800}
.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}.head{padding:11px 13px;background:#f8fbff;border-bottom:1px solid var(--line);font-weight:900}.body{padding:12px}.btn{display:inline-block;border:1px solid #b8d5f6;background:#fff;color:#145bb0;border-radius:8px;padding:8px 11px;font-weight:800;cursor:pointer}.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}.btn.green{background:#179b55;border-color:#179b55;color:#fff}.btn.red{background:#fff1f1;border-color:#efb1b1;color:#b5222b}.muted{color:#6c7d90}
.layout{display:grid;grid-template-columns:300px 1fr;gap:10px}.tree{max-height:78vh;overflow:auto}.tree details{border-bottom:1px solid #e8eef5}.tree summary{cursor:pointer;padding:8px 5px;font-weight:900}.tree a{display:block;padding:6px 8px;border-radius:6px}.tree a:hover{background:#eef6ff}.filters{display:grid;gap:8px}.field label{display:block;font-size:11px;color:#66778a;font-weight:800;margin-bottom:3px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd8e6;border-radius:7px;background:#fff}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:9px}.card{border:1px solid #d8e3ee;border-radius:10px;padding:11px;background:#fff}.titlebar{padding:10px 12px;border-radius:10px;background:linear-gradient(90deg,#1c61ce,#5798e7);color:#fff;font-weight:900}.meta{font-size:11px;color:#6a7d90}.tag{display:inline-block;border:1px solid #cbd9e7;border-radius:999px;padding:3px 8px;font-size:11px;margin:2px}.free{background:#eefbf2;border-color:#83d39e;color:#14743a}.vip{background:#fff0f7;border-color:#eaa3c9;color:#a2175f}.dang{margin-top:8px;border:1px solid #d9e5f0;background:#fbfdff;border-radius:8px;padding:7px}.dangrow{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid #edf2f7}.dangrow:last-child{border-bottom:0}
.selectwrap{overflow:auto}.selectgrid{width:100%;border-collapse:collapse;font-size:12px}.selectgrid th,.selectgrid td{border:1px solid #dfe7ef;padding:7px}.selectgrid th{background:#e9f2ff;text-align:center}.n{width:52px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}
.quiztop{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.palette{display:flex;flex-wrap:wrap;gap:5px;padding:9px;background:#f8fbff;border:1px solid var(--line);border-radius:9px;margin-bottom:10px}.pitem{padding:5px 8px;border:1px solid #cad7e6;border-radius:7px;background:#fff;font-size:11px}.pcur{border:2px solid var(--blue);font-weight:900}.pdone{background:#eaf9ef;border-color:#82c99b}.pwrong{background:#fff0f1;border-color:#eca0a7}.qbox{border:1px solid #cfddeb;border-radius:11px;padding:16px}.qtext{font-size:19px;line-height:1.8;margin-bottom:10px}.opt,.tf{display:block;border:2px solid #d8e4f0;border-radius:9px;padding:11px;margin:8px 0;cursor:pointer}.opt:hover,.tf:hover{background:#f8fbff}.correct{background:#e8f8ee!important;border-color:#42ae6b!important}.wrong{background:#fff0f1!important;border-color:#e04d56!important}.solution{margin-top:11px;padding:12px;border:1px solid #bad5f2;border-radius:9px;background:#f7fbff}.result{padding:10px;border-radius:9px;margin-top:10px;font-weight:900}.good{background:#eaf8ef;color:#116a32;border:1px solid #8ed1a2}.bad{background:#fff0f1;color:#a41f28;border:1px solid #efa2a8}.praise{margin:10px 0;padding:11px;border-radius:9px;background:#fff8df;border:1px solid #efca73;color:#855a00;font-size:16px;font-weight:900}.review{margin-top:12px;padding:12px;border:1px solid #cab9f0;background:#faf8ff;border-radius:9px}.reviewout{margin-top:10px;white-space:pre-wrap}.adminbox{display:grid;grid-template-columns:1fr 1fr;gap:10px}.code{width:100%;height:70vh;font:12px/1.5 Consolas,monospace;padding:10px;border:1px solid #cbd8e6;border-radius:8px}.notice{padding:10px;border:1px solid #b6d3ef;background:#f4f9ff;border-radius:8px}.err{color:#b42318;font-weight:800}.success{color:#0d7b35;font-weight:800}
@media(max-width:900px){.layout{grid-template-columns:1fr}.adminbox{grid-template-columns:1fr}.tree{max-height:38vh}}
"""

def page(title: str, body: str) -> Response:
    nav=["<a href='/member'>📚 Mục lục</a>"]
    if admin_current():
        nav.append("<a href='/admin'>🛠 ADMIN</a>")
        nav.append("<a href='/admin/logout'>↩ Đăng xuất</a>")
        nav.append(f"<a href='https://github.com/{html.escape(REPO)}' target='_blank'>🐙 GitHub</a>")
    elif member_current():
        nav.append("<a href='/member/logout'>↩ Đăng xuất</a>")
    else:
        nav.append("<a href='/login'>🔐 Đăng nhập</a>")
    top = (
        "<div class='top'><div class='topin'><div><div class='brand'>📚 Ngân hàng câu hỏi GitHub</div>"
        "<div class='sub'>Nguồn đề: bank_index.json + ngan-hang/*.tex · Google Sheet không dùng cho đề</div></div>"
        "<div class='nav'>"+"".join(nav)+"</div></div></div>"
    )
    mj = "<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre']}};</script><script async src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>"
    return Response(f"<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>{CSS}</style>{mj}</head><body>{top}{body}</body></html>", mimetype='text/html')

def load_json(path: Path, default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def index_data():return load_json(INDEX_FILE, {"lessons": [], "total_files": 0, "total_questions": 0})
def members_data():return load_json(MEMBERS_FILE, {"members": []})
def access_data():
    d=load_json(ACCESS_FILE, {"default":"FREE","lessons":{}}); d.setdefault('default','FREE'); d.setdefault('lessons',{}); return d

def member_record(username):
    return next((m for m in members_data().get('members',[]) if m.get('username')==username),None)

def member_current():
    if session.get('role')!='member':return None
    u=session.get('username')
    m=member_record(u)
    return m if m and str(m.get('status','ON')).upper()=='ON' else None
def admin_current():return session.get('role')=='admin'
def practice_current():
    if admin_current():return {'username':session.get('username') or ADMIN_USER,'name':'ADMIN','class':'','account_type':'ADMIN','status':'ON'}
    return member_current()
def is_vip(m):return str(m.get('account_type','FREE')).upper() in {'VIP','S.VIP','ADMIN'}
def lesson_level(path):
    d=access_data(); return str(d['lessons'].get(path,d['default'])).upper()
def can_access(m,path):return lesson_level(path)=='FREE' or is_vip(m)

def login_page(msg=''):
    err=f"<div class='err' style='margin-top:10px'>{html.escape(msg)}</div>" if msg else ''
    body=(
        "<div class='wrap'><div class='panel' style='max-width:500px;margin:60px auto'><div class='head'>🔐 Đăng nhập chung</div><div class='body'>"
        "<div class='notice'><b>Chỉ có 1 trang đăng nhập duy nhất.</b><br>Thành viên và ADMIN đều dùng cùng form này, hệ thống sẽ tự nhận diện tài khoản phù hợp.</div>"
        "<div class='meta' style='margin:10px 0 4px 0'>Nhập đúng tài khoản và mật khẩu của bạn để vào khu học tập hoặc quản trị.</div>"
        "<form method='post' action='/login' style='margin-top:10px'><div class='field'><label>Tài khoản</label><input name='username' placeholder='Ví dụ: hocvien01 hoặc ADMIN' required></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' placeholder='Nhập mật khẩu' required></div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:10px'><button class='btn primary'>Đăng nhập</button> <a class='btn' href='/member/register'>Chưa có tài khoản? Đăng ký</a></div>"
        +err+"</form></div></div></div>"
    )
    return page('Đăng nhập',body)

def gh_api(api_path,method='GET',payload=None):
    if not TOKEN:raise RuntimeError('Thiếu GITHUB_TOKEN trên Render.')
    owner,repo=REPO.split('/',1); body=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(f'https://api.github.com/repos/{owner}/{repo}/{api_path.lstrip("/")}',data=body,method=method,headers={'Authorization':f'Bearer {TOKEN}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'luyen-de-vat-ly-clean'})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try:msg=json.loads(s).get('message',s)
        except Exception:msg=s
        raise RuntimeError(f'GitHub API {e.code}: {msg}')

def read_tex(path):
    if not path.startswith('ngan-hang/') or not path.lower().endswith('.tex') or '..' in path:raise ValueError('Đường dẫn .tex không hợp lệ.')
    d=gh_api(f'contents/{urllib.parse.quote(path,safe="/")}?ref={urllib.parse.quote(BRANCH)}')
    raw=base64.b64decode((d.get('content') or '').replace('\n',''))
    return d.get('sha',''),raw.decode('utf-8','replace')

def get_braced(text,pos):
    while pos<len(text) and text[pos].isspace():pos+=1
    if pos>=len(text) or text[pos]!='{':return None,pos
    pos+=1;depth=1;out=[]
    while pos<len(text):
        c=text[pos];prev=text[pos-1] if pos else ''
        if c=='{' and prev!='\\':depth+=1
        elif c=='}' and prev!='\\':
            depth-=1
            if depth==0:return ''.join(out),pos+1
        out.append(c);pos+=1
    return None,pos

def command_args(block,cmd):
    m=re.search(re.escape(cmd)+r'\b',block,re.I)
    if not m:return []
    vals=[];p=m.end()
    while True:
        v,p2=get_braced(block,p)
        if v is None:break
        vals.append(v);p=p2
    return vals

def solution_of(block):
    m=re.search(r'\\loigiai\s*\{',block,re.I)
    if not m:return ''
    v,_=get_braced(block,m.end()-1);return v or ''

def clean_latex_web(s):
    s=re.sub(r'\\lq\s*\\lq','«',s,flags=re.I);s=re.sub(r'\\rq\s*\\rq','»',s,flags=re.I)
    s=re.sub(r'\\lq\b','«',s,flags=re.I);s=re.sub(r'\\rq\b','»',s,flags=re.I);s=re.sub(r'\\,',' ',s);return s.strip()

def dang_for_pos(tex,pos):
    ms=list(DANG_RE.finditer(tex[:pos]));return ms[-1].group(1).strip() if ms else 'Chưa phân dạng'

def level_of(block):
    vals=[x.strip().upper() for x in LEVEL_RE.findall(block)];s=vals[-1] if vals else 'H'
    if 'VDC' in s or re.search(r'\bC\b',s):return 'C'
    if 'VD' in s:return 'V'
    if 'NB' in s or 'NHAN BIET' in s:return 'N'
    return 'H'

def parse_questions(tex):
    out=[]
    for idx,m in enumerate(EX_RE.finditer(tex)):
        b=m.group(0)
        if re.search(r'\\choiceTF\b',b,re.I):kind='DS'
        elif re.search(r'\\choice\b',b,re.I):kind='TN'
        elif SHORT_RE.search(b):kind='TLN'
        else:kind='TL'
        q={'idx':idx,'dang':dang_for_pos(tex,m.start()),'level':level_of(b),'kind':kind,'text':clean_latex_web(re.split(r'\\choiceTF\b|\\choice\b|\\shortans\b',b,1,flags=re.I)[0]),'solution':clean_latex_web(solution_of(b)),'raw':b}
        if kind=='TN':q['options']=[{'text':clean_latex_web(re.sub(r'^\\True\s*','',x,flags=re.I)),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in command_args(b,'\\choice')[:4]]
        elif kind=='DS':q['statements']=[{'text':clean_latex_web(re.sub(r'^\\True\s*','',x,flags=re.I)),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in command_args(b,'\\choiceTF')]
        elif kind=='TLN':
            sm=re.search(r'\\shortans\s*',b,re.I);ans=''
            if sm:ans,_=get_braced(b,sm.end()-1)
            q['answer']=(ans or '').strip()
        out.append(q)
    return out

def norm_answer(s):
    s=clean_latex_web(str(s or ''));s=re.sub(r'\$+','',s).strip().lower();s=s.replace(',','.').replace(' ','');s=re.sub(r'\\text\{([^}]*)\}',r'\1',s);return s
def answer_equal(a,b):
    na,nb=norm_answer(a),norm_answer(b)
    if na==nb:return True
    try:return abs(float(na)-float(nb))<1e-9
    except Exception:return False

def save_json_github(path,data,repo_path,message):
    raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode();cur=gh_api(f'contents/{repo_path}?ref={urllib.parse.quote(BRANCH)}');gh_api(f'contents/{repo_path}','PUT',{'message':message,'content':base64.b64encode(raw).decode(),'branch':BRANCH,'sha':cur.get('sha')});path.write_bytes(raw)

@app.get('/health')
def health():return jsonify(ok=True,app='github-bank-clean',repo=REPO,branch=BRANCH)
@app.get('/')
def home():return redirect('/member')
@app.get('/github/repo')
def repo_redirect():
    if not admin_current():return redirect('/member')
    return redirect(f'https://github.com/{REPO}')

@app.route('/login',methods=['GET','POST'])
@app.route('/member/login',methods=['GET','POST'])
@app.route('/admin/login',methods=['GET','POST'])
def shared_login():
    if request.path!='/login':return redirect('/login',code=307 if request.method=='POST' else 302)
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();p=request.form.get('password','');h=hashlib.sha256(p.encode()).hexdigest()
        if u==ADMIN_USER and ADMIN_PASS and p==ADMIN_PASS:
            session.clear();session.update(role='admin',username=ADMIN_USER);return redirect('/admin')
        m=member_record(u)
        if m and str(m.get('status','ON')).upper()!='ON':msg='Tài khoản của bạn hiện đang bị tắt. Vui lòng liên hệ ADMIN.'
        elif m and m.get('password_sha256')==h:
            session.clear();session.update(role='member',username=u);return redirect('/member')
        elif m:msg='Sai mật khẩu.'
        else:msg='Sai tài khoản hoặc mật khẩu.'
    return login_page(msg)

@app.route('/member/register',methods=['GET','POST'])
def member_register():
    if request.method=='POST':
        u=request.form.get('username','').strip();n=request.form.get('name','').strip();p=request.form.get('password','');d=members_data()
        if not u or not p or any(x.get('username')==u for x in d.get('members',[])):return redirect('/member/register')
        d.setdefault('members',[]).append({'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()});save_json_github(MEMBERS_FILE,d,'members.json','Add member');session.clear();session.update(role='member',username=u);return redirect('/member')
    body="<div class='wrap'><div class='panel' style='max-width:430px;margin:60px auto'><div class='head'>📝 Đăng ký thành viên FREE</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Tạo tài khoản</button></form></div></div></div>";return page('Đăng ký',body)

@app.get('/member/logout')
def member_logout():session.clear();return redirect('/login')

@app.get('/member')
def member_index():
    m=practice_current()
    if not m:return redirect('/login')
    idx=index_data();items=[x for x in idx.get('lessons',[]) if isinstance(x,dict) and str(x.get('path','')).startswith('ngan-hang/')]
    subjects=sorted({str(x.get('Mon') or '') for x in items if x.get('Mon')});classes=sorted({str(x.get('Lop') or '') for x in items if x.get('Lop')});q=request.args.get('q','').strip().lower();sm=request.args.get('mon','');cl=request.args.get('lop','')
    def keep(x):
        t=' '.join(str(x.get(k) or '') for k in ('Mon','Lop','Chuong','BaiHoc','De')).lower();return (not q or q in t) and (not sm or str(x.get('Mon'))==sm) and (not cl or str(x.get('Lop'))==cl)
    items=[x for x in items if keep(x)];groups={}
    for x in items:groups.setdefault((str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or 'Chưa xác định')),[]).append(x)
    sections=[]
    for (mon,lop,chuong),arr in sorted(groups.items()):
        cards=[]
        for x in sorted(arr,key=lambda z:str(z.get('BaiHoc') or z.get('De') or '')):
            path=str(x.get('path'));title=str(x.get('BaiHoc') or x.get('De') or Path(path).parent.name);lvl=lesson_level(path);cnt=int(x.get('questions') or x.get('count') or 0);dangs=x.get('dang') or {};dh=''.join("<div class='dangrow'><span>"+html.escape(str(k))+"</span><span class='tag'>"+str(int(v))+" câu</span></div>" for k,v in dangs.items());lc='vip' if lvl=='VIP' else 'free';href=urllib.parse.quote(path,safe='')
            cards.append("<div class='card'><b>"+html.escape(title)+"</b><div class='meta'>"+html.escape(mon)+" · Lớp "+html.escape(lop)+" · "+html.escape(chuong)+"</div><div><span class='tag "+lc+"'>"+html.escape(lvl)+"</span><span class='tag'>"+str(cnt)+" câu</span></div><div class='dang'><b>📌 Dạng bài</b>"+(dh or "<div class='muted'>Xem trực tiếp từ TEX khi mở bài</div>")+"</div><a class='btn primary' href='/member/select?path="+href+"'>Mở bài</a></div>")
        sections.append("<section style='margin-top:10px'><div class='titlebar'>"+html.escape(mon)+" · Lớp "+html.escape(lop)+" · "+html.escape(chuong)+"</div><div class='cards' style='margin-top:8px'>"+''.join(cards)+"</div></section>")
    subjopts=''.join("<option value='"+html.escape(s,quote=True)+"'"+(" selected" if sm==s else "")+">"+html.escape(s)+"</option>" for s in subjects);classopts=''.join("<option value='"+html.escape(c,quote=True)+"'"+(" selected" if cl==c else "")+">"+html.escape(c)+"</option>" for c in classes)
    body=("<div class='wrap'><div class='panel'><div class='head'>📚 MỤC LỤC · GitHub <span class='tag'>"+str(idx.get('total_files',0))+" file</span><span class='tag'>"+str(idx.get('total_questions',0))+" câu</span></div><div class='body'><div class='notice'>👤 <b>"+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản <b>"+html.escape(str(m.get('username')))+"</b> · Quyền <b>"+html.escape(str(m.get('account_type','FREE')))+"</b></div><form method='get' style='display:grid;grid-template-columns:1fr 180px 160px auto;gap:7px;margin-top:10px'><input name='q' placeholder='Tìm bài, chương, dạng...' value='"+html.escape(q)+"'><select name='mon'><option value=''>Tất cả môn</option>"+subjopts+"</select><select name='lop'><option value=''>Tất cả lớp</option>"+classopts+"</select><button class='btn'>Tìm</button></form></div></div>"+(''.join(sections) or "<div class='panel' style='margin-top:10px'><div class='body muted'>Không có bài phù hợp.</div></div>")+"</div>")
    return page('Mục lục',body)

@app.get('/member/select')
def select_page():
    m=practice_current();
    if not m:return redirect('/login')
    p=request.args.get('path','')
    if not can_access(m,p):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try:_,tex=read_tex(p);qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    dang_names=[];seen=set()
    for q in qs:
        if q['dang'] not in seen:seen.add(q['dang']);dang_names.append(q['dang'])
    rows=[]
    for di,dang in enumerate(dang_names):
        arr=[q for q in qs if q['dang']==dang]
        for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
            c={z:sum(1 for q in arr if q['kind']==kind and q['level']==z) for z in 'NHVC'};inputs=''.join(f"<input class='n' type='number' min='0' max='{c[z]}' value='0' name='pick:{di}:{kind}:{z}'>" for z in 'NHVC');total=sum(c.values())
            rows.append(f"<tr><td>{html.escape(dang)}</td><td>{label}</td><td>{c['N']}/{c['H']}/{c['V']}/{c['C']}</td><td>{inputs}</td><td>{total}</td></tr>")
    body=f"<div class='wrap'><div class='panel'><div class='head'>🧩 Chọn dạng bài và số câu <span class='tag'>{len(qs)} câu thực tế trong TEX</span></div><div class='body'><form method='post' action='/member/start'><input type='hidden' name='path' value='{html.escape(p,quote=True)}'><div class='selectwrap'><table class='selectgrid'><tr><th>Dạng bài</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>{''.join(rows)}</table></div><div id='sum' class='notice' style='margin-top:10px'>TỔNG CHỌN: 0 câu</div><button class='btn primary'>▶ Tạo bài luyện tập</button> <a class='btn' href='/member'>← Mục lục</a></form></div></div></div><script>function upd(){{let t=0;document.querySelectorAll('.n').forEach(x=>{{let m=Number(x.max)||0,v=Math.max(0,Math.min(m,Number(x.value)||0));x.value=v;t+=v}});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu'}}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',upd));upd();</script>";return page('Chọn câu',body)

@app.post('/member/start')
def start_practice():
    m=practice_current();
    if not m:return redirect('/login')
    p=request.form.get('path','')
    if not can_access(m,p):return redirect('/member')
    try:_,tex=read_tex(p);qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    picks={}
    for k,v in request.form.items():
        if not k.startswith('pick:'):continue
        try:picks[k]=max(0,int(v or 0))
        except Exception:picks[k]=0
    wanted=[]
    dang_names=[];seen=set()
    for q in qs:
        if q['dang'] not in seen:seen.add(q['dang']);dang_names.append(q['dang'])
    for key,n in picks.items():
        if n<=0:continue
        _,di_s,kind,lev=key.split(':',3);di=int(di_s)
        if 0<=di<len(dang_names):
            pool=[q for q in qs if q['dang']==dang_names[di] and q['kind']==kind and q['level']==lev];wanted.extend(q['idx'] for q in random.sample(pool,min(n,len(pool))))
    if not wanted:return redirect('/member/select?path='+urllib.parse.quote(p,safe=''))
    random.shuffle(wanted);session.update(practice_path=p,practice_ids=wanted,practice_pos=0,practice_right=0,practice_streak=0,practice_best=0,practice_done=[]);return redirect('/member/practice')

@app.get('/member/practice')
def practice():
    m=practice_current();
    if not m:return redirect('/login')
    p=str(session.get('practice_path') or '');ids=list(session.get('practice_ids') or []);pos=int(session.get('practice_pos') or 0);right=int(session.get('practice_right') or 0);streak=int(session.get('practice_streak') or 0);best=int(session.get('practice_best') or 0);done=list(session.get('practice_done') or [])
    if not p or not ids:return redirect('/member')
    try:_,tex=read_tex(p);allq={q['idx']:q for q in parse_questions(tex)}
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    if pos>=len(ids):
        score=right/len(ids)*10 if ids else 0;opts=''.join(f"<option value='{i}'>Câu {i+1} · {'Đúng' if d.get('ok') else 'Sai'}</option>" for i,d in enumerate(done));body=f"<div class='wrap'><div class='panel'><div class='head'>🎉 Kết quả <span class='tag'>Đúng {right}/{len(ids)}</span> <span class='tag'>{score:.2f}/10</span></div><div class='body'><div class='result good'>Chuỗi tốt nhất: {best}</div><div class='review'><b>🔑 Gemini API key cá nhân</b><div class='meta'>Chỉ lưu trong trình duyệt này. Nếu để trống, hệ thống sẽ thử dùng key trên server.</div><div class='field' style='margin-top:7px'><input id='geminiKey' type='password' placeholder='AIza...'></div></div><div class='review'><b>🤖 Gemini phản biện 1 câu</b><div style='margin-top:7px'><select id='pick'>{opts}</select> <button class='btn' onclick='rv()'>Phản biện</button></div><div id='out' class='reviewout'></div></div><a class='btn' href='/member'>← Mục lục</a></div></div></div><script>const D={json.dumps(done,ensure_ascii=False)};function loadGeminiKey(){{try{{return localStorage.getItem('gemini_api_key')||''}}catch(e){{return''}}}}function currentGeminiKey(){{let x=document.getElementById('geminiKey');return ((x&&x.value)||'').trim()}}document.addEventListener('DOMContentLoaded',()=>{{let x=document.getElementById('geminiKey');if(x){{x.value=loadGeminiKey();x.addEventListener('input',()=>{{try{{localStorage.setItem('gemini_api_key',x.value||'')}}catch(e){{}}}})}}}});async function rv(){{let x=Object.assign({{}},D[+document.getElementById('pick').value]||{{}}),o=document.getElementById('out'),k=currentGeminiKey();if(k)x.api_key=k;o.textContent='⏳ Gemini đang phân tích...';let r=await fetch('/api/gemini/review',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(x)}});let d=await r.json();o.innerHTML=d.ok?d.text:'<span class=err>'+String(d.error||'Lỗi Gemini')+'</span>';if(window.MathJax)MathJax.typesetPromise()}}</script>";return page('Kết quả',body)
    q=allq.get(ids[pos]);
    if not q:return redirect('/member')
    palette=''.join(f"<span class='pitem {'pcur' if j==pos else ('pdone' if j<len(done) and done[j].get('ok') else ('pwrong' if j<len(done) else ''))}'>{j+1} · {allq.get(qid,{}).get('kind','?')}</span>" for j,qid in enumerate(ids))
    payload={'kind':q['kind'],'text':q['text'],'solution':q['solution'],'dang':q['dang'],'level':q['level']}
    if q['kind']=='TN':payload['options']=q['options']
    elif q['kind']=='DS':payload['statements']=q['statements']
    elif q['kind']=='TLN':payload['answer']=q.get('answer','')
    body=f"<div class='wrap'><div class='panel'><div class='head quiztop'><span>📝 Câu {pos+1}/{len(ids)} · {html.escape(q['dang'])} · {q['kind']}</span><span>Đúng {right} · Chuỗi {streak}</span></div><div class='body'><div class='palette'>{palette}</div><div class='review'><b>🔑 Gemini API key cá nhân</b><div class='meta'>Chỉ lưu trong trình duyệt này để dùng cho phần phản biện AI sau khi làm bài.</div><div class='field' style='margin-top:7px'><input id='geminiKey' type='password' placeholder='AIza...'></div></div><div id='praise'></div><div id='q' class='qbox'></div></div></div></div>"
    js=r'''<script>
const Q=__DATA__;let checked=false;
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function loadGeminiKey(){try{return localStorage.getItem('gemini_api_key')||''}catch(e){return''}}
document.addEventListener('DOMContentLoaded',()=>{let x=document.getElementById('geminiKey');if(x){x.value=loadGeminiKey();x.addEventListener('input',()=>{try{localStorage.setItem('gemini_api_key',x.value||'')}catch(e){}})}})
function draw(){let q=Q,h='<div class="qtext"><b>Câu __POS__. </b>'+q.text+'</div>';
if(q.kind==='TN')q.options.forEach((o,i)=>h+='<label class="opt" id="o'+i+'"><input type="radio" name="a" value="'+i+'"> <b>'+String.fromCharCode(65+i)+'.</b> '+o.text+'</label>');
else if(q.kind==='DS')q.statements.forEach((s,i)=>h+='<div class="tf" id="t'+i+'"><b>'+(i+1)+'.</b> '+s.text+'<br><label><input type="radio" name="t'+i+'" value="1"> Đúng</label> <label><input type="radio" name="t'+i+'" value="0"> Sai</label></div>');
else if(q.kind==='TLN')h+='<input id="ans" class="answerbox" style="width:100%;padding:10px;border:1px solid #cbd8e6;border-radius:7px" placeholder="Nhập đáp án">';
else h+='<textarea id="ans" class="answerbox" style="width:100%;height:190px;padding:10px;border:1px solid #cbd8e6;border-radius:7px" placeholder="Nhập bài làm"></textarea>';
h+='<div style="margin-top:10px"><button class="btn primary" onclick="check()">✅ Kiểm tra</button><button id="next" class="btn" style="display:none" onclick="location.href=\'/member/practice\'">→ Câu tiếp</button></div><div id="r"></div>';document.getElementById('q').innerHTML=h;if(window.MathJax)MathJax.typesetPromise()}
function check(){if(checked)return;let q=Q,ok=false,student='';
if(q.kind==='TN'){let z=document.querySelector('input[name=a]:checked');if(!z)return alert('Hãy chọn đáp án.');let i=+z.value;student=String.fromCharCode(65+i);q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')});ok=!!q.options[i].correct}
else if(q.kind==='DS'){ok=true;let a=[];for(let i=0;i<q.statements.length;i++){let z=document.querySelector('input[name=t'+i+']:checked');if(!z)return alert('Chọn đủ Đúng/Sai.');let v=z.value==='1';a.push(v?'Đ':'S');document.getElementById('t'+i).classList.add(v===q.statements[i].correct?'correct':'wrong');if(v!==q.statements[i].correct)ok=false}student=a.join('')}
else{let z=document.getElementById('ans');if(!z||!z.value.trim())return alert('Hãy nhập câu trả lời.');student=z.value.trim();ok=q.kind==='TLN'&&norm(student)===norm(q.answer);}
let note=q.kind==='TL'?'📝 Đã nộp bài tự luận — chờ chấm.':(ok?'✅ ĐÚNG':'❌ SAI');let sol=q.solution||'Chưa có lời giải trong file TEX.';document.getElementById('r').innerHTML='<div class="result '+(ok?'good':'bad')+'">'+note+'</div><div class="solution"><b>📖 Lời giải</b><div>'+sol+'</div></div>';if(window.MathJax)MathJax.typesetPromise();checked=true;document.getElementById('next').style.display='inline-block';fetch('/member/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ok:ok,student:student,text:q.text,solution:sol,kind:q.kind,dang:q.dang})}).then(r=>r.json()).then(d=>{if(d.praise)document.getElementById('praise').innerHTML='<div class="praise">'+E(d.praise)+'</div>'})}
function norm(s){return String(s??'').replace(/\$+/g,'').replace(/\s+/g,'').replace(/,/g,'.').toLowerCase()}
draw();</script>'''.replace('__DATA__',json.dumps(payload,ensure_ascii=False)).replace('__POS__',str(pos+1))
    return page('Làm bài',body+js)

@app.post('/member/answer')
def answer():
    m=practice_current();
    if not m:return jsonify(ok=False),401
    d=request.get_json(silent=True) or {};ok=bool(d.get('ok'));st=int(session.get('practice_streak') or 0);st=st+1 if ok else 0;best=max(int(session.get('practice_best') or 0),st);right=int(session.get('practice_right') or 0)+(1 if ok else 0);pos=int(session.get('practice_pos') or 0);done=list(session.get('practice_done') or []);praise=''
    if ok:
        if st==3:praise='🎉 Đúng 3 câu liên tiếp! Rất tốt!'
        elif st==5:praise='👏 Đúng 5 câu liên tiếp! Tuyệt vời!'
        elif st==10:praise='🏆 Đúng 10 câu liên tiếp! Xuất sắc!'
    done.append({'question':pos+1,'ok':ok,'student':str(d.get('student') or ''),'text':str(d.get('text') or ''),'solution':str(d.get('solution') or ''),'kind':str(d.get('kind') or ''),'dang':str(d.get('dang') or '')});session.update(practice_streak=st,practice_best=best,practice_right=right,practice_pos=pos+1,practice_done=done);return jsonify(ok=True,praise=praise,streak=st,right=right)

@app.post('/api/gemini/review')
def gemini_review():
    if not practice_current():return jsonify(ok=False,error='Chưa đăng nhập'),401
    d=request.get_json(silent=True) or {}
    client_api_key=str(d.pop('api_key','') or '').strip()
    api_key=client_api_key or GEMINI_KEY
    if not api_key:return jsonify(ok=False,error='Thiếu Gemini API key. Hãy nhập key của bạn hoặc cấu hình GEMINI_API_KEY trên server.'),400
    if client_api_key and not re.fullmatch(r'AIza[0-9A-Za-z\-_]{35}',client_api_key):return jsonify(ok=False,error='Gemini API key không hợp lệ.'),400
    prompt=("Bạn là giáo viên Toán/Vật lý THPT. Phản biện đúng MỘT câu học sinh vừa làm. Trình bày bằng tiếng Việt: câu hỏi, học sinh trả lời gì, đúng/sai, lỗi cụ thể, lời giải đúng từng bước, và kết luận ngắn. Giữ nguyên công thức LaTeX trong $...$.\n\n"+json.dumps(d,ensure_ascii=False))
    url='https://generativelanguage.googleapis.com/v1beta/models/'+urllib.parse.quote(GEMINI_MODEL,safe='')+':generateContent?key='+urllib.parse.quote(api_key,safe='')
    try:
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=40) as r:x=json.loads(r.read().decode())
        return jsonify(ok=True,text=x['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:return jsonify(ok=False,error=str(e)),500

@app.get('/admin')
def admin_home():
    if not admin_current():return redirect('/login')
    md=members_data().get('members',[]);rows=''.join(f"<tr><td>{html.escape(str(m.get('username','')))}</td><td>{html.escape(str(m.get('name','')))}</td><td>{html.escape(str(m.get('class','')))}</td><td>{html.escape(str(m.get('account_type','FREE')))}</td><td>{html.escape(str(m.get('status','ON')))}</td></tr>" for m in md)
    lessons=[x for x in index_data().get('lessons',[]) if isinstance(x,dict) and str(x.get('path','')).startswith('ngan-hang/')];lrows=''.join(f"<tr><td>{html.escape(str(x.get('Mon','')))}</td><td>{html.escape(str(x.get('Lop','')))}</td><td>{html.escape(str(x.get('Chuong','')))}</td><td>{html.escape(str(x.get('BaiHoc') or x.get('De') or ''))}</td><td><a class='btn' href='/admin/edit?path={urllib.parse.quote(str(x.get('path')),safe='')}'>✏️ Sửa TEX</a></td></tr>" for x in lessons)
    body=f"<div class='wrap'><div class='panel'><div class='head'>🔐 ADMIN <span class='tag'>GitHub trực tiếp</span></div><div class='body'><div class='notice'>ADMIN có quyền đọc/sửa file <code>.tex</code> và commit trực tiếp vào GitHub.</div><h3>👥 Thành viên</h3><table class='selectgrid'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th></tr>{rows}</table><h3>📚 Bài / TEX</h3><div style='max-height:55vh;overflow:auto'><table class='selectgrid'>{lrows}</table></div><p><a class='btn' href='/admin/logout'>Đăng xuất ADMIN</a> <a class='btn' href='/member'>Mục lục</a></p></div></div></div>";return page('ADMIN',body)

@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/login')

@app.route('/admin/edit',methods=['GET','POST'])
def admin_edit():
    if not admin_current():return redirect('/login')
    p=request.args.get('path','')
    if request.method=='POST':
        p=request.form.get('path','');new=request.form.get('content','');sha=request.form.get('sha','');msg=request.form.get('message','Cập nhật TEX từ ADMIN')
        if not sha:
            try:sha,_=read_tex(p)
            except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
        try:
            gh_api(f'contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(BRANCH)}','PUT',{'message':msg,'content':base64.b64encode(new.encode()).decode(),'branch':BRANCH,'sha':sha});return redirect('/admin/edit?path='+urllib.parse.quote(p,safe='')+'&saved=1')
        except Exception as e:return page('Lỗi commit',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    try:sha,txt=read_tex(p)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    saved=request.args.get('saved')=='1';notice="<div class='success'>✅ Đã commit lên GitHub.</div>" if saved else ''
    body=("<div class='wrap'><div class='panel'><div class='head'>✏️ ADMIN · Sửa trực tiếp TEX</div><div class='body'><div class='meta'>"+html.escape(p)+"</div>"+notice+"<form method='post'><input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'><input type='hidden' name='sha' value='"+html.escape(sha,quote=True)+"'><textarea name='content' class='code'>"+html.escape(txt)+"</textarea><div style='margin-top:8px'><input name='message' value='ADMIN cập nhật TEX' style='width:70%;padding:9px;border:1px solid #cbd8e6;border-radius:7px'><button class='btn green'>💾 Commit GitHub</button> <a class='btn' href='/admin'>← ADMIN</a></div></form></div></div></div>")
    return page('Sửa TEX',body)

@app.errorhandler(Exception)
def server_error(exc):return page('Lỗi máy chủ',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div><p><a class='btn' href='/health'>Kiểm tra /health</a></p></div></div></div>"),500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
