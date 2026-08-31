# -*- coding: utf-8 -*-
from __future__ import annotations
import base64, hashlib, html, json, os, random, re, urllib.parse, urllib.request, urllib.error
from functools import wraps
from pathlib import Path
from flask import Flask, Response, request, redirect, session, jsonify

app=Flask(__name__)
app.secret_key=os.getenv('APP_SECRET','change-this-on-render')
REPO=os.getenv('GITHUB_REPO','pythonminh/luyen-de-vat-ly').strip() or 'pythonminh/luyen-de-vat-ly'
BRANCH=os.getenv('GITHUB_BRANCH','main').strip() or 'main'
TOKEN=os.getenv('GITHUB_TOKEN','').strip()
ADMIN_USERNAME=os.getenv('ADMIN_USERNAME','ADMIN').strip() or 'ADMIN'
ADMIN_PASSWORD=os.getenv('ADMIN_PASSWORD','').strip()
GEMINI_API_KEY=os.getenv('GEMINI_API_KEY','').strip()
GEMINI_MODEL=(os.getenv('GEMINI_REVIEW_MODEL') or os.getenv('GEMINI_HINT_MODEL') or 'gemini-2.5-flash').strip()
ROOT=Path(__file__).resolve().parent
INDEX=ROOT/'bank_index.json'; MEMBERS=ROOT/'members.json'; ACCESS=ROOT/'lesson_access.json'
API='https://api.github.com'; RAW='https://raw.githubusercontent.com'
EX_RE=re.compile(r'\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}',re.I)
DANG_RE=re.compile(r'\\dangbt\s*\{([^{}]*)\}',re.I); LEVEL_RE=re.compile(r'%\s*Mức\s*:\s*([^\n%]+)',re.I)
CHOICE_RE=re.compile(r'\\choice\b',re.I); TF_RE=re.compile(r'\\choiceTF\b',re.I); SHORT_RE=re.compile(r'\\shortans\s*\{([^{}]*)\}',re.I)
LOIGIAI_RE=re.compile(r'\\loigiai\s*\{',re.I); ID_RE=re.compile(r'%\s*ID\s*:[^\n]*',re.I)
CSS='''*{box-sizing:border-box}body{margin:0;background:#f3f7fc;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#1769d2;color:#fff}.topin{max-width:1500px;margin:auto;padding:9px 14px;display:flex;align-items:center;gap:12px}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b9d5f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer}.nav a{background:transparent;color:#fff;border-color:#ffffff66}.wrap{max-width:1500px;margin:auto;padding:10px}.layout{display:grid;grid-template-columns:290px 1fr;gap:10px}.panel{background:#fff;border:1px solid #cfddea;border-radius:11px;overflow:hidden}.head,.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe8f0;font-weight:900}.mh{display:flex;justify-content:space-between;align-items:center;gap:8px}.body{padding:10px}.tree{max-height:calc(100vh - 175px);overflow:auto}.tree details{border-bottom:1px solid #e8eef5}.tree summary{cursor:pointer;padding:7px 4px;font-weight:800;list-style:none}.tree summary::-webkit-details-marker{display:none}.tree summary:before{content:'▶ ';font-size:10px}.tree details[open]>summary:before{content:'▼ '}.tree a{display:block;padding:5px 8px;margin:2px 0;color:#155da8;text-decoration:none;border-radius:6px}.tree a:hover{background:#eef6ff}.titlebar{padding:10px 12px;background:linear-gradient(90deg,#1d5ed5,#4c98ec);color:#fff;border-radius:9px;font-weight:900;font-size:17px}.meta{font-size:11px;color:#64748b}.table{width:100%;border-collapse:collapse;font-size:12px}.table th,.table td{border:1px solid #dfe8f0;padding:5px}.table th{background:#f5f8fc;text-align:center}.table td:first-child{font-weight:700}.stock{background:#eef7ff}.sel{width:58px;padding:4px;border:1px solid #b9cfe5;border-radius:6px}.type{font-weight:900;text-align:center}.total{font-weight:900;text-align:center;background:#f9fbfd}.summary{padding:9px;border:1px solid #9ed0a9;background:#f1fbf3;border-radius:8px;font-weight:900}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:8px}.lesson{border:1px solid #d9e3ec;border-radius:9px;padding:9px;background:#fff}.tag{display:inline-block;padding:3px 7px;border:1px solid #cbd8e5;border-radius:999px;font-size:10px;margin:2px}.free{border-color:#8dd6a3;background:#effbf3;color:#15733b}.vip{border-color:#f2a9cd;background:#fff0f8;color:#9b175f}.qcard{border:1px solid #d6e3ef;border-radius:10px;padding:12px;background:#fff}.qtext{font-size:16px;line-height:1.7}.opt{display:block;padding:10px;margin:7px 0;border:2px solid #d8e5f1;border-radius:9px;cursor:pointer}.opt.correct{border-color:#31a354;background:#eaf8ee}.opt.wrong{border-color:#e33b42;background:#fff0f1}.tfitem{padding:8px;margin:7px 0;border:2px solid #d8e5f1;border-radius:8px}.tfitem.correct{border-color:#31a354;background:#eaf8ee}.tfitem.wrong{border-color:#e33b42;background:#fff0f1}.score{padding:10px;border-radius:9px;background:#eef7ff;border:1px solid #a9cff4;font-weight:900}.review{margin-top:10px;padding:10px;border:1px solid #c8b7f4;background:#faf7ff;border-radius:9px}.code{width:100%;height:74vh;font:12px/1.5 Consolas,monospace}.login{max-width:420px;margin:70px auto}.err{color:#b42318;font-weight:800}.ok{color:#14773a;font-weight:800}@media(max-width:900px){.layout{grid-template-columns:1fr}.tree{max-height:none}.table{font-size:11px}}'''

def gh(path,method='GET',data=None):
    if not TOKEN: raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    raw=None if data is None else json.dumps(data,ensure_ascii=False).encode()
    req=urllib.request.Request(API+path,data=raw,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl-v8','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try:m=json.loads(s).get('message',s)
        except Exception:m=s
        raise RuntimeError(f'GitHub API {e.code}: {m}')

def gh_get(path):
    owner,repo=REPO.split('/',1);return gh(f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe="/")}?ref={urllib.parse.quote(BRANCH)}')
def gh_put(path,text,message,sha=None):
    owner,repo=REPO.split('/',1);d={'message':message,'content':base64.b64encode(text.encode()).decode(),'branch':BRANCH}
    if sha:d['sha']=sha
    return gh(f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe="/")}','PUT',d)
def read_json_local(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return default
def index_data():
    if INDEX.exists():return read_json_local(INDEX,{})
    d=gh_get('bank_index.json');return json.loads(base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8'))
def members():return read_json_local(MEMBERS,{'schema':2,'members':[]})
def access():
    d=read_json_local(ACCESS,{'schema':1,'default':'FREE','lessons':{}});d.setdefault('default','FREE');d.setdefault('lessons',{});return d
def save_json(name,data,msg):
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n';cur=gh_get(name);gh_put(name,text,msg,cur.get('sha'));(ROOT/name).write_text(text,encoding='utf-8')
def current_member():
    u=session.get('username')
    return next((m for m in members().get('members',[]) if m.get('username')==u and m.get('status','ON')=='ON'),None)
def is_vip(m):return str(m.get('account_type') or 'FREE').upper() in {'VIP','S.VIP','ADMIN'}
def lesson_level(path):return str(access().get('lessons',{}).get(path,access().get('default','FREE'))).upper()
def allowed(m,path):return lesson_level(path)=='FREE' or is_vip(m)
def safe_tex(p):return isinstance(p,str) and p.startswith('ngan-hang/') and p.lower().endswith('.tex') and '..' not in p
def read_tex(p):
    if not safe_tex(p):raise ValueError('Đường dẫn .tex không hợp lệ')
    d=gh_get(p);return d.get('sha',''),base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')
def brace_arg(s,pos):
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
def cmd_args(s,cmd):
    m=re.search(re.escape(cmd)+r'\b',s,re.I)
    if not m:return []
    out=[];pos=m.end()
    while 1:
        a,pos=brace_arg(s,pos)
        if a is None:break
        out.append(a)
    return out
def sol(block):
    m=LOIGIAI_RE.search(block)
    if not m:return ''
    a,_=brace_arg(block,m.end());return a or ''
def norm_level(block):
    m=LEVEL_RE.search(block)
    if not m:return 'H'
    x=m.group(1).strip().upper()
    if 'VDC' in x or x in {'C','VDC'}:return 'C'
    if 'VD' in x or x in {'V','K','KH'}:return 'V'
    if 'NB' in x or x in {'N','NHAN BIET'}:return 'N'
    return 'H'
def cleanq(s):
    s=ID_RE.sub('',s);s=LEVEL_RE.sub('',s);s=DANG_RE.sub('',s);return s.strip()
def parse_q(block,idx):
    dm=DANG_RE.search(block);dang=dm.group(1).strip() if dm else 'Chưa phân dạng';lev=norm_level(block);solution=sol(block)
    tf=cmd_args(block,'\\choiceTF')
    if tf:return {'idx':idx,'dang':dang,'level':lev,'kind':'tf','text':cleanq(TF_RE.split(block,1)[0]),'statements':[{'text':re.sub(r'^\\True\s*','',x,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in tf],'solution':solution}
    ch=cmd_args(block,'\\choice')
    if ch:return {'idx':idx,'dang':dang,'level':lev,'kind':'choice','text':cleanq(CHOICE_RE.split(block,1)[0]),'options':[{'text':re.sub(r'^\\True\s*','',x,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in ch[:4]],'solution':solution}
    sm=SHORT_RE.search(block)
    if sm:return {'idx':idx,'dang':dang,'level':lev,'kind':'short','text':cleanq(block[:sm.start()]),'answer':sm.group(1).strip(),'solution':solution}
    return {'idx':idx,'dang':dang,'level':lev,'kind':'essay','text':cleanq(block),'solution':solution}
def lesson_questions(path):
    _,t=read_tex(path);return [parse_q(b,i) for i,b in enumerate(EX_RE.findall(t))]
def render(title,body):
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"+f"<title>{html.escape(title)}</title><style>{CSS}</style><script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre']}};</script><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><div class='topin'><div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div><div class='sub'>GitHub / ngan-hang/*.tex là nguồn chính</div></div><div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"+body+"</body></html>",mimetype='text/html')
def reqmem(v):
    @wraps(v)
    def w(*a,**k):
        if not current_member():session.clear();return redirect('/member/login')
        return v(*a,**k)
    return w
def reqadmin(v):
    @wraps(v)
    def w(*a,**k):
        if session.get('role')!='admin':return redirect('/admin/login')
        return v(*a,**k)
    return w
@app.get('/')
def root():return redirect('/member/login')
@app.get('/github/repo')
def repo():return redirect(f'https://github.com/{REPO}')
@app.route('/member/login',methods=['GET','POST'])
def login():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();p=request.form.get('password','');h=hashlib.sha256(p.encode()).hexdigest()
        for m in members().get('members',[]):
            if m.get('username')==u and m.get('password_sha256')==h and m.get('status','ON')=='ON':session.clear();session.update(role='member',username=u);return redirect('/member')
        msg='Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa.'
    return render('Đăng nhập',f"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")
@app.route('/member/register',methods=['GET','POST'])
def register():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();n=request.form.get('name','').strip();p=request.form.get('password','');d=members()
        if not u or not p:msg='Thiếu tài khoản hoặc mật khẩu.'
        elif any(m.get('username')==u for m in d.get('members',[])):msg='Tài khoản đã tồn tại.'
        else:
            d.setdefault('members',[]).append({'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
            try:save_json('members.json',d,'Đăng ký thành viên');session.clear();session.update(role='member',username=u);return redirect('/member')
            except Exception as e:msg=str(e)
    return render('Đăng ký',f"<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký FREE</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Tạo tài khoản</button><div class='err'>{html.escape(msg)}</div></form></div></div></div>")
@app.get('/member/logout')
def logout():session.clear();return redirect('/member/login')
@app.get('/member')
@reqmem
def member_home():
    m=current_member();idx=index_data();groups={}
    for x in idx.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '')
        if safe_tex(p):groups.setdefault((str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or 'Chưa xác định')),[]).append(x)
    left=[];main=[];subjects={}
    for (sub,cl,ch),items in sorted(groups.items()):
        ls=[]
        for x in items:
            p=str(x.get('path'));title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name);cnt=int(x.get('questions') or x.get('count') or 0);dgs=x.get('dang') or {};lvl=lesson_level(p)
            tags=''.join(f"<div class='dangrow'><span>{html.escape(str(k))}</span><span class='tag'>{int(v)} câu</span></div>" for k,v in dgs.items())
            ls.append(f"<div class='lesson'><b>{html.escape(title)}</b><div class='meta'>{html.escape(sub)} · Lớp {html.escape(cl)} · {html.escape(ch)}</div><div><span class='tag {('vip' if lvl=='VIP' else 'free')}'>{lvl}</span><span class='tag'>{cnt} câu</span></div><div class='dangbox'>{tags}</div><a class='btn' href='/member/select?path={urllib.parse.quote(p,safe='')}'>Chọn dạng / số câu</a></div>")
            subjects.setdefault(sub,{}).setdefault(cl,[]).setdefault(ch,[]).append((p,title))
        main.append(f"<div class='titlebar'>{html.escape(sub)} · Lớp {html.escape(cl)}</div><div class='chapter'><div class='head'>{html.escape(ch)}</div><div class='cards'>{''.join(ls)}</div></div>")
    for sub,clsmap in subjects.items():
        s=f"<details><summary>📘 {html.escape(sub)}</summary>"
        for cl,chmap in clsmap.items():
            s+=f"<details><summary>Khối {html.escape(cl)}</summary>"
            for ch,arr in chmap.items():
                s+=f"<details><summary>{html.escape(ch)}</summary>"+''.join(f"<a href='/member/select?path={urllib.parse.quote(p,safe='')}'>{html.escape(t)}</a>" for p,t in arr)+"</details>"
            s+='</details>'
        s+='</details>';left.append(s)
    badge='VIP · FREE + VIP' if is_vip(m) else 'FREE · chỉ FREE'
    body=f"<div class='wrap'><div class='notice'><b>👤 {html.escape(str(m.get('name') or m.get('username')))}</b> · Tài khoản: <b>{html.escape(str(m.get('username')))}</b> · Quyền: <span class='tag {('vip' if is_vip(m) else 'free')}'>{badge}</span> · <a href='/member/logout'>Đăng xuất</a></div><div class='layout'><aside class='panel'><div class='head'>🌳 Cấu trúc Ngân hàng</div><div class='body tree'>{''.join(left)}</div></aside><main class='panel'><div class='mh'><span>📚 Mục lục · chọn Bài → Dạng bài</span><span>{int(idx.get('total_files') or 0)} bài · {int(idx.get('total_questions') or 0)} câu</span></div><div class='body'>{''.join(main)}</div></main></div></div>"
    return render('Ngân hàng',body)
@app.get('/member/select')
@reqmem
def select_page():
    m=current_member();p=request.args.get('path','')
    if not allowed(m,p):return render('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    qs=lesson_questions(p);groups={}
    for q in qs:groups.setdefault(q['dang'],[]).append(q)
    rows=[]; total=0
    for dang,arr in groups.items():
        cells=[]
        for kind,label in [('choice','TN'),('tf','ĐS'),('short','TLN'),('essay','TL')]:
            sub=[q for q in arr if q['kind']==kind];counts={k:sum(1 for q in sub if q['level']==k) for k in 'NHVC'};st=sum(counts.values());total+=st
            ins=''.join(f"<input class='sel' type='number' name='n_{re.sub(r'[^A-Za-z0-9]','_',dang)}_{kind}_{k}' min='0' max='{counts[k]}' value='0' data-max='{counts[k]}' data-total='{st}' data-kind='{kind}' data-dang='{html.escape(dang,quote=True)}'>" for k in 'NHVC')
            cells.append(f"<td class='type'>{label}</td><td class='stock'>{counts['N']}/{counts['H']}/{counts['V']}/{counts['C']}</td><td>{ins}</td><td class='total' data-rowtotal='1'>{st}</td>")
        rows.append(f"<tr><td>{html.escape(dang)}</td>"+''.join(cells)+"</tr>")
    heads="<tr><th>Dạng bài tập</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>"
    form=f"<form method='post' action='/member/start'><input type='hidden' name='path' value='{html.escape(p,quote=True)}'><div class='titlebar'>{html.escape(Path(p).parent.name)}</div><div class='meta'>{html.escape(p)}</div><div style='overflow:auto;margin-top:8px'><table class='table'>{heads}{''.join(rows)}</table></div><div class='summary' id='summary'>TỔNG CHỌN: 0 câu</div><div class='row' style='margin-top:8px'><button class='btn' type='submit'>▶ Tạo bài luyện tập</button><a class='btn' href='/member'>← Mục lục</a></div></form><script>function upd(){{let a=[...document.querySelectorAll('.sel')],t=0;a.forEach(x=>{{let m=+x.dataset.max,v=Math.max(0,Math.min(m,+x.value||0));x.value=v;t+=v}});document.getElementById('summary').textContent='TỔNG CHỌN: '+t+' câu';}}document.querySelectorAll('.sel').forEach(x=>x.addEventListener('input',upd));upd();</script>"
    return render('Chọn dạng bài',"<div class='wrap'><div class='panel'><div class='mh'><span>🧩 Chọn dạng bài và số câu</span><span>Tài khoản: "+html.escape(str(m.get('username')))+"</span></div><div class='body'>"+form+"</div></div></div>")
@app.post('/member/start')
@reqmem
def start_quiz():
    m=current_member();p=request.form.get('path','');
    if not allowed(m,p):return redirect('/member')
    qs=lesson_questions(p);chosen=[]
    for q in qs:
        for field in request.form:
            if not field.startswith('n_') or request.form.get(field,'0')=='0':continue
            parts=field.rsplit('_',2);kind=parts[-2];lev=parts[-1];dang='_'.join(parts[1:-2]);
            if q['kind']==kind and q['level']==lev and re.sub(r'[^A-Za-z0-9]','_',q['dang'])==dang:
                chosen.append(q['idx'])
                # consume one requested slot
                request.form
                break
    # precise recount using field quantities
    chosen=[]
    buckets={}
    for field,val in request.form.items():
        if not field.startswith('n_') or int(val or 0)<=0:continue
        parts=field.split('_');kind=parts[-2];lev=parts[-1];dang='_'.join(parts[1:-2]);buckets[(dang,kind,lev)]=int(val)
    for q in qs:
        key=(re.sub(r'[^A-Za-z0-9]','_',q['dang']),q['kind'],q['level'])
        if buckets.get(key,0)>0:chosen.append(q['idx']);buckets[key]-=1
    if not chosen:return redirect('/member/select?path='+urllib.parse.quote(p,safe=''))
    random.shuffle(chosen);return redirect('/member/quiz?path='+urllib.parse.quote(p,safe='')+'&ids='+','.join(map(str,chosen)))
@app.get('/member/quiz')
@reqmem
def quiz():
    m=current_member();p=request.args.get('path','');ids=[int(x) for x in request.args.get('ids','').split(',') if x.isdigit()];allq=lesson_questions(p);by={q['idx']:q for q in allq};qs=[by[i] for i in ids if i in by]
    data=json.dumps(qs,ensure_ascii=False)
    body="<div class='wrap'><div class='panel'><div class='mh'><span>📝 Luyện từng câu · "+html.escape(Path(p).parent.name)+"</span><span>Tài khoản: "+html.escape(str(m.get('username')))+" · "+('VIP' if is_vip(m) else 'FREE')+"</span></div><div class='body'><div id='score' class='score'>Câu 1/"+str(len(qs))+"</div><div id='quiz' style='margin-top:8px'></div></div></div></div>"
    js=r'''const Q=__DATA__;let k=0,right=0,answers=[];function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}function typeset(){if(window.MathJax)MathJax.typesetPromise()}function draw(){if(k>=Q.length){let pick=answers.map((a,i)=>'<option value="'+i+'">Câu '+(i+1)+'</option>').join('');document.getElementById('score').innerHTML='🎉 Hoàn thành · Đúng <b>'+right+'/'+Q.length+'</b> · Điểm <b>'+((right/Q.length)*10).toFixed(2)+'</b>/10';document.getElementById('quiz').innerHTML='<div class="review"><b>🤖 Gemini phản biện</b><div><select id="pick">'+pick+'</select> <button class="btn" onclick="review()">Phản biện câu đã chọn</button></div><div id="out"></div></div><a class="btn" href="/member">← Về mục lục</a>';typeset();return}let q=Q[k],h='<div class="qcard"><div class="qtext"><b>Câu '+(k+1)+'.</b> '+esc(q.text)+'</div>';if(q.kind==='choice')q.options.forEach((o,i)=>h+='<label class="opt" id="o'+i+'"><input type="radio" name="a" value="'+i+'"> <b>'+String.fromCharCode(65+i)+'.</b> '+esc(o.text)+'</label>');else if(q.kind==='tf')q.statements.forEach((s,i)=>h+='<div class="tfitem" id="t'+i+'">'+(i+1)+'. '+esc(s.text)+'<div><label><input type="radio" name="t'+i+'" value="1"> Đúng</label> <label><input type="radio" name="t'+i+'" value="0"> Sai</label></div></div>');else if(q.kind==='short')h+='<input id="short" class="sel" style="width:100%;padding:9px" placeholder="Nhập đáp án">';else h+='<textarea id="essay" style="width:100%;height:160px" placeholder="Nhập bài làm"></textarea>';h+='<div class="row" style="margin-top:10px"><button class="btn" onclick="check()">✅ Kiểm tra</button></div><div id="res"></div></div>';document.getElementById('quiz').innerHTML=h;document.getElementById('score').textContent='Câu '+(k+1)+'/'+Q.length+' · '+(q.dang||'Chưa phân dạng');typeset()}function check(){let q=Q[k],ok=false,student='';if(q.kind==='choice'){let e=document.querySelector('input[name=a]:checked');if(!e){alert('Hãy chọn đáp án');return}let i=+e.value;student=String.fromCharCode(65+i);q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')});ok=q.options[i].correct}else if(q.kind==='tf'){let vals=[];for(let i=0;i<q.statements.length;i++){let e=document.querySelector('input[name=t'+i+']:checked');if(!e){alert('Chọn Đúng/Sai cho tất cả ý');return}let v=e.value==='1';vals.push(v?'Đ':'S');let el=document.getElementById('t'+i);el.classList.add(v===q.statements[i].correct?'correct':'wrong')}student=vals.join('');ok=q.statements.every((s,i)=>(document.querySelector('input[name=t'+i+']:checked').value==='1')===s.correct)}else if(q.kind==='short'){student=document.getElementById('short').value.trim();if(!student){alert('Nhập đáp án');return}ok=student.toLowerCase()===String(q.answer||'').trim().toLowerCase();document.getElementById('res').innerHTML='<div class="'+(ok?'summary':'notice')+'">'+(ok?'✅ Đúng':'❌ Sai')+' · Đáp án: <b>'+esc(q.answer||'')+'</b></div>'}else{student=document.getElementById('essay').value;document.getElementById('res').innerHTML='<div class="notice">Đã ghi nhận bài tự luận.</div>'}if(q.kind!=='short'&&q.kind!=='essay')document.getElementById('res').innerHTML='<div class="'+(ok?'summary':'notice')+'">'+(ok?'✅ Đúng':'❌ Sai')+'</div>';if(ok)right++;answers.push({q,student});document.querySelectorAll('input').forEach(e=>e.disabled=true);document.getElementById('quiz').insertAdjacentHTML('beforeend','<button class="btn" onclick="k++;draw()">→ Câu tiếp</button>')}async function review(){let i=+document.getElementById('pick').value,a=answers[i],out=document.getElementById('out');out.textContent='⏳ Gemini đang phản biện...';try{let r=await fetch('/api/gemini/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:a.q,student_answer:a.student})});let d=await r.json();out.innerHTML=d.ok?'<div class="review">'+esc(d.text).replace(/\n/g,'<br>')+'</div>':'<div class="err">'+esc(d.error||'Lỗi Gemini')+'</div>'}catch(e){out.innerHTML='<div class="err">'+esc(e)+'</div>'}}draw();'''
    return render('Làm bài',body+"<script>"+js.replace('__DATA__',data)+"</script>")
@app.post('/api/gemini/review')
@reqmem
def gemini_review():
    if not GEMINI_API_KEY:return jsonify(ok=False,error='Chưa cấu hình GEMINI_API_KEY trên Render.'),400
    d=request.get_json(silent=True) or {};q=d.get('question') or {};student=d.get('student_answer','')
    prompt='Bạn là trợ lý phản biện cho học sinh THPT. Chỉ phản biện một câu được gửi. Nêu học sinh trả lời gì, đúng/sai, vì sao, lỗi dễ nhầm, cách làm đúng từng bước. Giữ công thức LaTeX. Không bịa dữ kiện.\n\nCÂU HỎI:\n'+str(q.get('text',''))+'\nLOẠI:'+str(q.get('kind',''))+'\nTRẢ LỜI:\n'+str(student)+'\nĐÁP ÁN:\n'+json.dumps(q.get('options') or q.get('statements') or q.get('answer') or '',ensure_ascii=False)+'\nLỜI GIẢI GỐC:\n'+str(q.get('solution',''))
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(GEMINI_MODEL,safe='')}:generateContent?key={urllib.parse.quote(GEMINI_API_KEY,safe='')}"
    try:
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=45) as r:res=json.loads(r.read().decode())
        return jsonify(ok=True,text=res['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:return jsonify(ok=False,error=str(e)),500
@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();p=request.form.get('password','')
        if u==ADMIN_USERNAME and ADMIN_PASSWORD and p==ADMIN_PASSWORD:session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    return render('ADMIN',f"<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='{html.escape(ADMIN_USERNAME)}' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button><div class='err'>{html.escape(msg)}</div></form></div></div></div>")
@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')
@app.get('/admin')
@reqadmin
def admin_home():
    d=members();rows=[]
    for m in d.get('members',[]):
        typ=str(m.get('account_type') or 'FREE').upper();u=html.escape(str(m.get('username','')),quote=True)
        rows.append(f"<tr><td>{html.escape(str(m.get('username','')))}</td><td>{html.escape(str(m.get('name','')))}</td><td>{html.escape(str(m.get('class','')))}</td><td><form method='post' action='/admin/member/type'><input type='hidden' name='username' value='{u}'><select name='account_type'><option {'selected' if typ=='FREE' else ''}>FREE</option><option {'selected' if typ=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu</button></form></td><td>{html.escape(str(m.get('status','ON')))}</td></tr>")
    body="<div class='wrap'><div class='panel'><div class='mh'><span>🔐 ADMIN · Thành viên</span><a class='btn' href='/github/quan-ly'>📚 Ngân hàng .tex</a></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th></tr>"+''.join(rows)+"</table></div></div></div>"
    return render('ADMIN',body)
@app.post('/admin/member/type')
@reqadmin
def member_type():
    u=request.form.get('username','');typ=request.form.get('account_type','FREE').upper();typ='VIP' if typ=='VIP' else 'FREE';d=members()
    for m in d.get('members',[]):
        if m.get('username')==u:m['account_type']=typ;break
    save_json('members.json',d,'ADMIN đổi quyền thành viên');return redirect('/admin')
@app.get('/github/quan-ly')
@reqadmin
def gh_manage():return render('Ngân hàng GitHub','<div class="wrap"><div class="panel"><div class="head">📚 Mở file .tex bằng GitHub</div><div class="body">Dùng <a class="btn" href="/member">Mục lục</a> để chọn bài. ADMIN có quyền sửa trực tiếp file .tex.</div></div></div>')
@app.get('/admin/edit')
@reqadmin
def edit_tex():
    p=request.args.get('path','');sha,text=read_tex(p)
    body="<div class='wrap'><div class='panel'><div class='mh'><b>✏️ "+html.escape(p)+"</b><a class='btn' href='/admin'>← ADMIN</a></div><div class='body'><textarea id='code' class='code'>"+html.escape(text)+"</textarea><div class='row' style='margin-top:8px'><button class='btn' onclick='saveTex()'>💾 Lưu trực tiếp GitHub</button><span id='msg'></span></div></div></div></div><script>const p="+json.dumps(p)+",s="+json.dumps(sha)+";async function saveTex(){let msg=document.getElementById('msg');msg.textContent='Đang lưu...';let r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,sha:s,text:document.getElementById('code').value})});let d=await r.json();msg.textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+(d.error||'Lỗi')}</script>"
    return render('Sửa .tex',body)
@app.post('/admin/api/save')
@reqadmin
def api_save():
    d=request.get_json(silent=True) or {};p=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not safe_tex(p) or not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu path/text/sha'),400
    try:r=gh_put(p,text,'ADMIN cập nhật .tex trực tiếp',sha);return jsonify(ok=True,commit=str((r.get('commit') or {}).get('sha',''))[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),500
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
