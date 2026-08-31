# -*- coding: utf-8 -*-
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.error, urllib.parse, urllib.request
from functools import wraps
from pathlib import Path
from flask import Flask, Response, redirect, request, session

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET", "change-this-on-render")
REPO = os.getenv("GITHUB_REPO", "pythonminh/luyen-de-vat-ly").strip() or "pythonminh/luyen-de-vat-ly"
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
EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}", re.I)
DANG_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)
CHOICE_RE = re.compile(r"\\choice\b", re.I)
TF_RE = re.compile(r"\\choiceTF\b", re.I)
SHORT_RE = re.compile(r"\\shortans\s*\{([^{}]*)\}", re.I)
ID_RE = re.compile(r"%\s*ID\s*:[^\n]*", re.I)
MUC_RE = re.compile(r"%\s*Mức\s*:[^\n]*", re.I)

CSS = """
*{box-sizing:border-box}body{margin:0;background:#f3f7fc;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#1769d2;color:#fff}.topin{max-width:1500px;margin:auto;padding:11px 16px;display:flex;gap:14px;align-items:center}.brand{font-size:21px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}.nav a{color:#fff;text-decoration:none;border:1px solid #ffffff66;padding:7px 10px;border-radius:9px;font-weight:800}.wrap{max-width:1500px;margin:auto;padding:14px}.layout{display:grid;grid-template-columns:245px 1fr;gap:12px}.panel{background:#fff;border:1px solid #cedceb;border-radius:12px;overflow:hidden}.head{padding:11px 13px;background:#f8fbff;border-bottom:1px solid #dce7f1;font-weight:900}.body{padding:12px}.field{margin-bottom:9px}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border:1px solid #c7d5e3;border-radius:8px;background:white}.btn{display:inline-block;padding:7px 10px;border:1px solid #a9c9ee;border-radius:8px;background:#fff;color:#105cae;font-weight:800;text-decoration:none;cursor:pointer}.btn.primary{background:#1769d2;color:#fff;border-color:#1769d2}.row{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.pill{display:inline-block;padding:4px 8px;border:1px solid #cbd8e5;border-radius:999px;font-size:10px;font-weight:800;background:#fff}.free{border-color:#8dd6a3;background:#effbf3;color:#15733b}.vip{border-color:#f3a4cb;background:#fff0f8;color:#9b175f}.tree details{border-bottom:1px solid #e5edf5}.tree summary{cursor:pointer;padding:8px 4px;font-weight:800;list-style:none}.tree summary::-webkit-details-marker{display:none}.tree summary:before{content:'▶ ';font-size:10px}.tree details[open]>summary:before{content:'▼ '}.tree a{display:block;padding:5px 8px;text-decoration:none;color:#1e5da8;border-radius:6px}.tree a:hover{background:#eef6ff}.subjectbar{padding:11px 13px;background:linear-gradient(90deg,#1d5ed5,#4c98ec);color:#fff;font-size:18px;font-weight:900;border-radius:11px}.chapter{margin-top:10px;border:1px solid #d4e1ee;border-radius:10px;overflow:hidden}.chapter>div:first-child{padding:9px 11px;background:#deebff;color:#164879;font-weight:900}.lessons{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:8px;padding:9px}.lesson{border:1px solid #d9e4ee;border-radius:10px;padding:10px;background:#fff}.lesson h3{font-size:14px;margin:0 0 4px}.dangbox{margin-top:8px;border:1px solid #d8e7f7;border-radius:8px;background:#f8fbff;padding:7px}.dangrow{display:flex;justify-content:space-between;gap:7px;padding:5px 3px;border-bottom:1px solid #e5edf5}.dangrow:last-child{border-bottom:0}.qgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:10px}.qcard{border:1px solid #d6e3ef;border-radius:10px;padding:11px;background:#fff}.qtext{font-size:15px;line-height:1.65}.sectiontitle{margin:11px 0 8px;padding:9px 11px;border-radius:9px;background:#dcecff;color:#174e82;font-weight:900}.opt{display:block;padding:8px;margin:6px 0;border:1px solid #d5e5f5;border-radius:8px}.tf{margin:6px 0;padding:7px;border:1px solid #deebf7;border-radius:8px;background:#f8fbff}.score{padding:11px;border:1px solid #91d5a8;background:#effbf3;border-radius:9px;font-weight:900;margin-bottom:8px}.notice{padding:10px;border:1px solid #a9cff4;background:#eef7ff;border-radius:9px;margin-bottom:10px}.login{max-width:430px;margin:60px auto}.code{width:100%;height:76vh;resize:vertical;border:1px solid #bdccdb;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.ok{color:#14773a;font-weight:900}.err{color:#b42318;font-weight:900}@media(max-width:900px){.layout{grid-template-columns:1fr}.qgrid{grid-template-columns:1fr}}
"""

def gh(path, method="GET", data=None):
    if not TOKEN: raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    raw = None if data is None else json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(API+path, data=raw, method=method, headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"ldvl-v4","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try: m=json.loads(s).get('message',s)
        except Exception: m=s
        raise RuntimeError(f"GitHub API {e.code}: {m}") from e

def gh_get(path):
    owner,repo=REPO.split('/',1)
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(BRANCH)}")

def gh_put(path,text,message,sha=None):
    owner,repo=REPO.split('/',1)
    d={"message":message,"content":base64.b64encode(text.encode('utf-8')).decode('ascii'),"branch":BRANCH}
    if sha:d['sha']=sha
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe='/')}",'PUT',d)

def read_index():
    if INDEX.exists(): return json.loads(INDEX.read_text(encoding='utf-8'))
    owner,repo=REPO.split('/',1); url=f"{RAW}/{owner}/{repo}/{urllib.parse.quote(BRANCH)}/bank_index.json"
    with urllib.request.urlopen(url,timeout=12) as r:return json.loads(r.read().decode('utf-8'))

def load_json(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def members():return load_json(MEMBERS,{"schema":2,"members":[]})
def access():
    d=load_json(ACCESS,{"schema":1,"default":"FREE","lessons":{}});d.setdefault('default','FREE');d.setdefault('lessons',{});return d

def save_json(filename,data,message):
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    try:sha=gh_get(filename).get('sha')
    except Exception:sha=None
    gh_put(filename,text,message,sha);(ROOT/filename).write_text(text,encoding='utf-8')

def is_vip(m):return str(m.get('account_type') or 'FREE').upper() in {'VIP','S.VIP','ADMIN'}
def current_member():
    u=session.get('username')
    for m in members().get('members',[]):
        if u and m.get('username')==u and m.get('status','ON')=='ON':return m
    return None

def level(path):return str(access().get('lessons',{}).get(path,access().get('default','FREE'))).upper()
def safe_tex(path):return isinstance(path,str) and path.startswith('ngan-hang/') and path.lower().endswith('.tex') and '..' not in path
def read_tex(path):
    if not safe_tex(path):raise ValueError('Đường dẫn .tex không hợp lệ')
    d=gh_get(path);return d.get('sha',''),base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')

def arg_at(s,pos):
    while pos<len(s) and s[pos].isspace():pos+=1
    if pos>=len(s) or s[pos]!='{':return None,pos
    dep=0;st=pos+1;i=pos
    while i<len(s):
        if s[i]=='{' and (i==0 or s[i-1]!='\\'):dep+=1
        elif s[i]=='}' and (i==0 or s[i-1]!='\\'):
            dep-=1
            if dep==0:return s[st:i],i+1
        i+=1
    return None,len(s)

def args(s,cmd):
    m=re.search(re.escape(cmd)+r'\b',s,re.I)
    if not m:return []
    out=[];pos=m.end()
    while True:
        a,pos2=arg_at(s,pos)
        if a is None:break
        out.append(a);pos=pos2
    return out

def clean(s):
    s=ID_RE.sub('',s);s=MUC_RE.sub('',s);s=DANG_RE.sub('',s);return s.strip()

def parse_q(block):
    dm=DANG_RE.search(block);dang=dm.group(1).strip() if dm else 'Chưa phân dạng'
    tf=args(block,'\\choiceTF')
    if tf:
        arr=[{'text':re.sub(r'^\\True\s*','',x,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in tf]
        return {'dang':dang,'kind':'tf','text':clean(TF_RE.split(block,1)[0]),'statements':arr}
    ch=args(block,'\\choice')
    if ch:
        arr=[{'text':re.sub(r'^\\True\s*','',x,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in ch[:4]]
        return {'dang':dang,'kind':'choice','text':clean(CHOICE_RE.split(block,1)[0]),'options':arr}
    sm=SHORT_RE.search(block)
    if sm:return {'dang':dang,'kind':'short','text':clean(block[:sm.start()]),'answer':sm.group(1).strip()}
    return {'dang':dang,'kind':'essay','text':clean(block)}

def lesson_questions(path):
    _,text=read_tex(path);return [parse_q(b) for b in EX_RE.findall(text)]

def page(title,body):
    return Response(f"<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>{CSS}</style><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><div class='topin'><div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div><div class='sub'>Nguồn chính: GitHub / ngan-hang/*.tex</div></div><div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>{body}</body></html>",mimetype='text/html')

def require_member(v):
    @wraps(v)
    def w(*a,**k):
        if session.get('role')!='member' or not current_member():session.clear();return redirect('/member/login')
        return v(*a,**k)
    return w

def require_admin(v):
    @wraps(v)
    def w(*a,**k):
        if session.get('role')!='admin':return redirect('/admin/login')
        return v(*a,**k)
    return w

@app.get('/')
def root():return redirect('/member/login')

@app.get('/github/repo')
def repo_link():return redirect(f'https://github.com/{REPO}')

@app.route('/member/login',methods=['GET','POST'])
def member_login():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();p=request.form.get('password') or '';h=hashlib.sha256(p.encode()).hexdigest()
        for m in members().get('members',[]):
            if m.get('username')==u and m.get('password_sha256')==h and m.get('status','ON')=='ON':session.clear();session.update(role='member',username=u);return redirect('/member')
        msg='Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa.'
    return page('Đăng nhập',f"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Đăng nhập</button><a class='btn' href='/member/register'>Đăng ký</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.route('/member/register',methods=['GET','POST'])
def member_register():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();n=(request.form.get('name') or '').strip();p=request.form.get('password') or '';d=members()
        if not u or not p:msg='Thiếu tài khoản hoặc mật khẩu.'
        elif any(m.get('username')==u for m in d.get('members',[])):msg='Tài khoản đã tồn tại.'
        else:
            d.setdefault('members',[]).append({'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
            try:save_json('members.json',d,'Đăng ký thành viên mới');session.clear();session.update(role='member',username=u);return redirect('/member')
            except Exception as e:msg=str(e)
    return page('Đăng ký',f"<div class='wrap'><div class='panel login'><div class='head'>📝 Tạo tài khoản FREE</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Tạo tài khoản</button><a class='btn' href='/member/login'>Quay lại</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.get('/member/logout')
def member_logout():session.clear();return redirect('/member/login')

@app.get('/member')
@require_member
def member_home():
    m=current_member();idx=read_index();by={};
    for it in idx.get('lessons',[]):
        if not isinstance(it,dict) or not safe_tex(it.get('path','')):continue
        mon=str(it.get('Mon') or 'Khác');lop=str(it.get('Lop') or '');chuong=str(it.get('Chuong') or 'Chưa có chương');bai=str(it.get('BaiHoc') or it.get('De') or Path(it['path']).parent.name)
        by.setdefault(mon,{}).setdefault(lop,{}).setdefault(chuong,[]).append(it)
    tree=[]
    for mon,grades in sorted(by.items()):
        g=[]
        for lop,chs in sorted(grades.items()):
            c=[]
            for chuong,items in sorted(chs.items()):
                links=[]
                for it in items:
                    path=it['path'];lv=level(path);ok=lv=='FREE' or is_vip(m);name=str(it.get('BaiHoc') or it.get('De') or Path(path).parent.name);n=int(it.get('questions') or it.get('count') or 0)
                    links.append(f"<a href='/member/lesson?path={urllib.parse.quote(path,safe='')}'>{'🔓' if ok else '🔒'} {html.escape(name)} <span class='small'>({n} câu · {lv})</span></a>")
                c.append(f"<details><summary>{html.escape(chuong)} · {sum(int(x.get('questions') or x.get('count') or 0) for x in items)} câu</summary>{''.join(links)}</details>")
            g.append(f"<details><summary>Lớp {html.escape(lop)}</summary>{''.join(c)}</details>")
        tree.append(f"<details><summary>📘 {html.escape(mon)}</summary>{''.join(g)}</details>")
    badge='VIP · xem/làm FREE + VIP' if is_vip(m) else 'THÀNH VIÊN · chỉ FREE'
    body=f"<div class='wrap'><div class='notice'>👤 <b>{html.escape(str(m.get('name') or m.get('username')))}</b> · Tài khoản: <b>{html.escape(str(m.get('username')))}</b> · Quyền: <span class='pill {'vip' if is_vip(m) else 'free'}'>{badge}</span> · <a href='/member/logout'>Thoát</a></div><div class='layout'><aside class='panel'><div class='head'>📚 MỤC LỤC</div><div class='body tree'>{''.join(tree)}</div></aside><main><div class='subjectbar'>MÔN → LỚP → CHƯƠNG → BÀI → DẠNG BÀI TẬP → 4 DẠNG CÂU</div><div class='panel' style='margin-top:10px'><div class='head'>Chọn Bài học ở cây bên trái để bắt đầu</div><div class='body'><div class='small'>FREE: thành viên thường · VIP: thành viên VIP · Trong bài sẽ chia tiếp từng Dạng bài tập và 4 loại câu: Trắc nghiệm, Đúng/Sai, Trả lời ngắn, Tự luận.</div></div></div></main></div></div>"
    return page('Mục lục',body)

@app.get('/member/lesson')
@require_member
def member_lesson():
    m=current_member();path=request.args.get('path','');lv=level(path)
    if not safe_tex(path):return page('Lỗi','<div class="wrap"><div class="panel"><div class="body">Đường dẫn không hợp lệ.</div></div></div>')
    if lv!='FREE' and not is_vip(m):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho thành viên VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    try:qs=lesson_questions(path)
    except Exception as e:return page('Lỗi đọc .tex',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(e))}</div></div></div></div>")
    groups={}
    for i,q in enumerate(qs,1):groups.setdefault(q.get('dang') or 'Chưa phân dạng',[]).append((i,q))
    qh=[];ans=[];auto=0
    for dang,items in groups.items():
        qh.append(f"<div class='sectiontitle'>🏷️ {html.escape(dang)} · {len(items)} câu</div><div class='qgrid'>")
        for i,q in items:
            t=html.escape(q.get('text') or '')
            if q['kind']=='choice':
                opts=''.join(f"<label class='opt'><input type='radio' name='q{i}' value='{j}'> <b>{chr(65+j)}.</b> {html.escape(o['text'])}</label>" for j,o in enumerate(q['options']))
                ca=next((j for j,o in enumerate(q['options']) if o['correct']),0);ans.append({'i':i,'k':'c','a':ca});auto+=1
                qh.append(f"<div class='qcard'><div class='row'><b>Câu {i}</b><span class='pill'>Trắc nghiệm</span></div><div class='qtext'>{t}</div>{opts}</div>")
            elif q['kind']=='tf':
                rows=''.join(f"<div class='tf'><b>{j+1}.</b> {html.escape(s['text'])}<br><label><input type='radio' name='q{i}_{j}' value='1'> Đúng</label> <label><input type='radio' name='q{i}_{j}' value='0'> Sai</label></div>" for j,s in enumerate(q['statements']))
                ans.append({'i':i,'k':'tf','a':[bool(s['correct']) for s in q['statements']]});auto+=len(q['statements'])
                qh.append(f"<div class='qcard'><div class='row'><b>Câu {i}</b><span class='pill'>Đúng / Sai</span></div><div class='qtext'>{t}</div>{rows}</div>")
            elif q['kind']=='short':
                ans.append({'i':i,'k':'s','a':q['answer']});auto+=1
                qh.append(f"<div class='qcard'><div class='row'><b>Câu {i}</b><span class='pill'>Trả lời ngắn</span></div><div class='qtext'>{t}</div><input class='field' id='s{i}' placeholder='Nhập đáp án'></div>")
            else:qh.append(f"<div class='qcard'><div class='row'><b>Câu {i}</b><span class='pill'>Tự luận</span></div><div class='qtext'>{t}</div></div>")
        qh.append('</div>')
    aj=json.dumps(ans,ensure_ascii=False)
    js=f"<script>const ANS={aj};function grade(){{let r=0,t=0;for(const q of ANS){{if(q.k==='c'){{t++;const e=document.querySelector('input[name=q'+q.i+']:checked');if(e&&+e.value===+q.a)r++;}}else if(q.k==='tf'){{q.a.forEach((a,j)=>{{t++;const e=document.querySelector('input[name=q'+q.i+'_'+j+']:checked');if(e&&+e.value===(a?1:0))r++;}})}}else{{t++;const e=document.getElementById('s'+q.i);if(e&&e.value.trim().toLowerCase()===String(q.a).trim().toLowerCase())r++;}}}}document.getElementById('score').innerHTML='✅ Đúng <b>'+r+'/'+t+'</b> · Điểm <b>'+(t?(10*r/t).toFixed(2):'0.00')+'/10</b>';MathJax.typesetPromise();}}MathJax.typesetPromise();</script>"
    body=f"<div class='wrap'><div class='panel'><div class='head'><div class='row'><span>📖 {html.escape(Path(path).parent.name)}</span><span class='pill {'vip' if lv=='VIP' else 'free'}'>{lv}</span><a class='btn' style='margin-left:auto' href='/member'>← Bài học</a></div></div><div class='body'><div id='score' class='score'>Đã tải {len(qs)} câu · {auto} ý/câu có thể chấm tự động</div><button class='btn primary' onclick='grade()'>📝 Chấm điểm</button>{''.join(qh)}</div></div></div>{js}"
    return page('Làm bài',body)

@app.get('/admin/login')
def admin_login():
    body=f"<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post' action='/admin/login'><div class='field'><label>Tài khoản</label><input name='username' value='{html.escape(ADMIN_USERNAME)}' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Đăng nhập</button></form></div></div></div>"
    return page('ADMIN',body)

@app.post('/admin/login')
def admin_login_post():
    if (request.form.get('username') or '').strip()==ADMIN_USERNAME and ADMIN_PASSWORD and request.form.get('password')==ADMIN_PASSWORD:
        session.clear();session['role']='admin';return redirect('/admin')
    return redirect('/admin/login?bad=1')

@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')

@app.get('/admin')
@require_admin
def admin_home():
    ms=members().get('members',[]);rows=[]
    for m in ms:
        typ=str(m.get('account_type') or 'FREE').upper();u=str(m.get('username') or '')
        rows.append(f"<tr><td>{html.escape(u)}</td><td>{html.escape(str(m.get('name') or ''))}</td><td>{html.escape(str(m.get('class') or ''))}</td><td><form method='post' action='/admin/member/type'><input type='hidden' name='username' value='{html.escape(u,quote=True)}'><select name='account_type'><option {'selected' if typ=='FREE' else ''}>FREE</option><option {'selected' if typ=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu</button></form></td><td>{html.escape(str(m.get('status') or 'ON'))}</td></tr>")
    body="<div class='wrap'><div class='layout'><aside class='panel'><div class='head'>⚙️ ADMIN</div><div class='body'><a class='btn primary' href='/admin'>👥 Thành viên</a> <a class='btn' href='/github/quan-ly'>📚 GitHub .tex</a> <a class='btn' href='/admin/access'>🔐 Quyền bài</a> <a class='btn' href='/admin/logout'>Thoát</a></div></aside><main class='panel'><div class='head'>👥 Thành viên</div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th></tr>"+''.join(rows)+"</table></div></main></div></div>"
    return page('ADMIN',body)

@app.post('/admin/member/type')
@require_admin
def admin_member_type():
    u=request.form.get('username','');typ=(request.form.get('account_type') or 'FREE').upper();typ='VIP' if typ=='VIP' else 'FREE';d=members()
    for m in d.get('members',[]):
        if m.get('username')==u:m['account_type']=typ;break
    save_json('members.json',d,'ADMIN đổi quyền thành viên');return redirect('/admin')

@app.get('/admin/access')
@require_admin
def admin_access():
    idx=read_index();ac=access();rows=[]
    for it in idx.get('lessons',[]):
        if not isinstance(it,dict) or not safe_tex(it.get('path','')):continue
        p=it['path'];lv=level(p);title=str(it.get('BaiHoc') or it.get('De') or Path(p).parent.name)
        rows.append(f"<div class='lesson'><b>{html.escape(title)}</b><div class='small'>{html.escape(p)}</div><form method='post' action='/admin/access/save'><input type='hidden' name='path' value='{html.escape(p,quote=True)}'><select name='level'><option {'selected' if lv=='FREE' else ''}>FREE</option><option {'selected' if lv=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu</button><span class='pill {'vip' if lv=='VIP' else 'free'}'>{lv}</span></form></div>")
    return page('Phân quyền',"<div class='wrap'><div class='panel'><div class='head'>🔐 Phân quyền từng Bài: FREE / VIP</div><div class='body'>"+''.join(rows)+"</div></div></div>")

@app.post('/admin/access/save')
@require_admin
def admin_access_save():
    p=request.form.get('path','');lv=(request.form.get('level') or 'FREE').upper();lv='VIP' if lv=='VIP' else 'FREE';d=access();d.setdefault('lessons',{})[p]=lv;save_json('lesson_access.json',d,'ADMIN phân quyền bài học');return redirect('/admin/access')

@app.get('/github/quan-ly')
@require_admin
def github_manage():
    idx=read_index(); cards=[]
    for it in idx.get('lessons',[]):
        if not isinstance(it,dict) or not safe_tex(it.get('path','')):continue
        p=it['path'];title=str(it.get('BaiHoc') or it.get('De') or Path(p).parent.name);n=int(it.get('questions') or it.get('count') or 0)
        cards.append(f"<div class='lesson'><h3>{html.escape(title)}</h3><div class='small'>{html.escape(p)}</div><span class='pill'>{n} câu</span><a class='btn' href='/admin/edit?path={urllib.parse.quote(p,safe="")}'>✏️ Đọc / sửa .tex</a></div>")
    return page('GitHub',"<div class='wrap'><div class='panel'><div class='head'>📚 Ngân hàng GitHub</div><div class='body'>"+''.join(cards)+"</div></div></div>")

@app.get('/admin/edit')
@require_admin
def admin_edit():
    p=request.args.get('path','');sha,text=read_tex(p)
    body=f"<div class='wrap'><div class='panel'><div class='head'>✏️ {html.escape(p)}</div><div class='body'><textarea id='code' class='code'>{html.escape(text)}</textarea><div class='row' style='margin-top:8px'><button class='btn primary' onclick='saveTex()'>💾 Lưu trực tiếp GitHub</button><a class='btn' href='/github/quan-ly'>← Ngân hàng</a><span id='msg'></span></div></div></div></div><script>const P={json.dumps(p,ensure_ascii=False)},S={json.dumps(sha)};async function saveTex(){{let m=document.getElementById('msg');m.textContent='Đang lưu...';let r=await fetch('/admin/api/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{path:P,sha:S,text:document.getElementById('code').value}})}});let d=await r.json();m.textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+(d.error||'Lỗi')}}}</script>"
    return page('Sửa .tex',body)

@app.post('/admin/api/save')
@require_admin
def admin_save():
    d=request.get_json(silent=True) or {};p=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not safe_tex(p) or not isinstance(text,str) or not sha:return {'ok':False,'error':'Thiếu path/text/sha'},400
    try:r=gh_put(p,text,'ADMIN cập nhật .tex trực tiếp',sha);return {'ok':True,'commit':str((r.get('commit') or {}).get('sha') or '')[:12]}
    except Exception as e:return {'ok':False,'error':str(e)},500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
