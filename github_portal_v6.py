# -*- coding: utf-8 -*-
"""GitHub-only portal v6: member FREE/VIP, hierarchical catalog, typed quiz, scoring, Gemini review, ADMIN .tex editor."""
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.error, urllib.parse, urllib.request
from functools import wraps
from pathlib import Path
from flask import Flask, Response, redirect, request, session, jsonify

app=Flask(__name__)
app.secret_key=os.getenv('APP_SECRET','change-this-on-render')
REPO=os.getenv('GITHUB_REPO','pythonminh/luyen-de-vat-ly').strip() or 'pythonminh/luyen-de-vat-ly'
BRANCH=os.getenv('GITHUB_BRANCH','main').strip() or 'main'
TOKEN=os.getenv('GITHUB_TOKEN','').strip()
ADMIN_USERNAME=os.getenv('ADMIN_USERNAME','ADMIN').strip() or 'ADMIN'
ADMIN_PASSWORD=os.getenv('ADMIN_PASSWORD','').strip()
GEMINI_KEY=os.getenv('GEMINI_API_KEY','').strip()
GEMINI_MODEL=os.getenv('GEMINI_REVIEW_MODEL') or os.getenv('GEMINI_HINT_MODEL') or 'gemini-2.5-flash'
ROOT=Path(__file__).resolve().parent
INDEX=ROOT/'bank_index.json'; MEMBERS=ROOT/'members.json'; ACCESS=ROOT/'lesson_access.json'
API='https://api.github.com'; RAW='https://raw.githubusercontent.com'
EX_RE=re.compile(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}",re.I)
DANG_RE=re.compile(r"\\dangbt\s*\{([^{}]*)\}",re.I); CHOICE_RE=re.compile(r"\\choice\b",re.I); TF_RE=re.compile(r"\\choiceTF\b",re.I); SHORT_RE=re.compile(r"\\shortans\s*\{([^{}]*)\}",re.I)
CSS="""
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#1769d2;color:#fff}.topin{max-width:1500px;margin:auto;padding:10px 16px;display:flex;gap:14px;align-items:center}.brand{font-size:21px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}.nav a{color:#fff;text-decoration:none;border:1px solid #ffffff66;padding:7px 10px;border-radius:9px;font-weight:800}.wrap{max-width:1500px;margin:auto;padding:14px}.panel{background:#fff;border:1px solid #cedceb;border-radius:12px;overflow:hidden}.head{padding:11px 13px;background:#f8fbff;border-bottom:1px solid #dce7f1;font-weight:900}.body{padding:12px}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.btn{display:inline-block;padding:7px 10px;border:1px solid #a9c9ee;border-radius:8px;background:#fff;color:#105cae;font-weight:800;text-decoration:none;cursor:pointer}.primary{background:#1769d2;color:#fff;border-color:#1769d2}.danger{color:#b42318}.field{margin:8px 0}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border:1px solid #c7d5e3;border-radius:8px}.login{max-width:430px;margin:60px auto}.tree{border:1px solid #d7e4ef;border-radius:10px;overflow:hidden}.tree details{border-bottom:1px solid #e5edf5}.tree summary{cursor:pointer;padding:9px 11px;font-weight:900;background:#f8fbff}.tree a{display:block;padding:6px 12px;text-decoration:none;color:#1e5da8}.tree a:hover{background:#eef6ff}.subject{margin-top:10px;padding:11px 13px;background:linear-gradient(90deg,#1d5ed5,#4c98ec);color:#fff;border-radius:10px;font-size:18px;font-weight:900}.chapter{margin-top:10px;border:1px solid #d5e3ef;border-radius:10px;overflow:hidden}.chapter>div:first-child{padding:9px 11px;background:#deebff;font-weight:900}.lessons{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:8px;padding:9px}.lesson{border:1px solid #d9e4ee;border-radius:10px;padding:10px}.lesson h3{margin:0 0 5px;font-size:15px}.pill{display:inline-block;padding:4px 8px;border:1px solid #cbd8e5;border-radius:999px;font-size:10px;font-weight:900;margin:3px 3px 0 0}.free{border-color:#8dd6a3;background:#effbf3;color:#15733b}.vip{border-color:#f3a4cb;background:#fff0f8;color:#9b175f}.dangbox{margin-top:8px;border:1px solid #d8e6f4;border-radius:8px;background:#f8fbff;padding:6px}.dangrow{display:flex;justify-content:space-between;gap:8px;padding:6px 3px;border-bottom:1px solid #e5edf5}.dangrow:last-child{border-bottom:0}.quiztop{display:flex;justify-content:space-between;gap:8px;align-items:center;padding:10px 0}.qcard{max-width:900px;margin:auto;border:1px solid #d6e3ef;border-radius:12px;background:#fff;padding:16px}.qtext{font-size:17px;line-height:1.7}.opt{display:block;padding:11px;margin:8px 0;border:2px solid #d5e5f5;border-radius:9px;cursor:pointer}.opt.correct{background:#dcfce7;border-color:#22c55e}.opt.wrong{background:#fee2e2;border-color:#ef4444}.opt.correctanswer{background:#dcfce7;border-color:#22c55e}.tfrow{padding:9px;border:1px solid #dbe7f1;border-radius:8px;margin:7px 0}.result{padding:12px;border:1px solid #86d39f;background:#effbf3;border-radius:10px;font-weight:900}.review{margin-top:10px;padding:12px;border:1px solid #c8d9ec;border-radius:10px;background:#f8fbff;white-space:pre-wrap;line-height:1.6}.code{width:100%;height:76vh;resize:vertical;border:1px solid #bdccdb;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.small{font-size:11px;color:#64748b}.err{color:#b42318;font-weight:900}.ok{color:#14773a;font-weight:900}.center{text-align:center}@media(max-width:900px){.topin{flex-wrap:wrap}.nav{margin-left:0}.lessons{grid-template-columns:1fr}}
"""

def gh(path,method='GET',data=None):
    if not TOKEN: raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    raw=None if data is None else json.dumps(data,ensure_ascii=False).encode()
    req=urllib.request.Request(API+path,data=raw,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl-v6','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try:m=json.loads(s).get('message',s)
        except Exception:m=s
        raise RuntimeError(f'GitHub API {e.code}: {m}') from e

def gh_get(path):
    owner,repo=REPO.split('/',1); return gh(f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe="/")}?ref={urllib.parse.quote(BRANCH)}')
def gh_put(path,text,msg,sha=None):
    owner,repo=REPO.split('/',1); d={'message':msg,'content':base64.b64encode(text.encode()).decode(),'branch':BRANCH}
    if sha:d['sha']=sha
    return gh(f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe="/")}', 'PUT', d)

def load_json(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def idx():
    if INDEX.exists():return load_json(INDEX,{})
    owner,repo=REPO.split('/',1); url=f'{RAW}/{owner}/{repo}/{urllib.parse.quote(BRANCH)}/bank_index.json'
    with urllib.request.urlopen(url,timeout=12) as r:return json.loads(r.read().decode())
def members():return load_json(MEMBERS,{'schema':2,'members':[]})
def access():
    d=load_json(ACCESS,{'schema':1,'default':'FREE','lessons':{}}); d.setdefault('default','FREE'); d.setdefault('lessons',{}); return d

def sync_json(name,data,msg):
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    cur=gh_get(name); gh_put(name,text,msg,cur.get('sha')); (ROOT/name).write_text(text,encoding='utf-8')

def is_vip(m):return str(m.get('account_type') or 'FREE').upper() in {'VIP','S.VIP','ADMIN'}
def curmember():
    u=session.get('username')
    for m in members().get('members',[]):
        if u and m.get('username')==u and m.get('status','ON')=='ON':return m
    return None
def lesson_level(path):return str(access().get('lessons',{}).get(path,access().get('default','FREE'))).upper()
def allowed(m,path):return lesson_level(path)=='FREE' or is_vip(m)
def safe_tex(p):return isinstance(p,str) and p.startswith('ngan-hang/') and p.lower().endswith('.tex') and '..' not in p
def read_tex(p):
    if not safe_tex(p):raise ValueError('Đường dẫn .tex không hợp lệ')
    d=gh_get(p); return d.get('sha',''),base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')

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
    out=[];p=m.end()
    while True:
        a,p2=arg_at(s,p)
        if a is None:break
        out.append(a);p=p2
    return out
def clean(s):
    s=re.sub(r'%.*','',s);s=DANG_RE.sub('',s);s=re.sub(r'\\ID\s*:\s*[^\n]*','',s,flags=re.I);s=re.sub(r'\\Mức\s*:\s*[^\n]*','',s,flags=re.I);return s.strip()
def parse_q(block):
    dm=DANG_RE.search(block); dang=dm.group(1).strip() if dm else 'Chưa phân dạng'
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
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+html.escape(title)+"</title><style>"+CSS+"</style><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><div class='topin'><div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div><div class='sub'>Nguồn chính: GitHub / ngan-hang/*.tex · Google Sheet không dùng</div></div><div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"+body+"</body></html>",mimetype='text/html')
def reqmem(v):
    @wraps(v)
    def w(*a,**k):
        if session.get('role')!='member' or not curmember():session.clear();return redirect('/member/login')
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
def member_login():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();p=request.form.get('password') or '';h=hashlib.sha256(p.encode()).hexdigest()
        for m in members().get('members',[]):
            if m.get('username')==u and m.get('password_sha256')==h and m.get('status','ON')=='ON':session.clear();session.update(role='member',username=u);return redirect('/member')
        msg='Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa.'
    return page('Đăng nhập',f"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")
@app.route('/member/register',methods=['GET','POST'])
def member_register():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();n=(request.form.get('name') or '').strip();p=request.form.get('password') or '';d=members()
        if not u or not p:msg='Thiếu tài khoản hoặc mật khẩu.'
        elif any(m.get('username')==u for m in d.get('members',[])):msg='Tài khoản đã tồn tại.'
        else:
            d.setdefault('members',[]).append({'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
            try:sync_json('members.json',d,'Đăng ký thành viên');session.clear();session.update(role='member',username=u);return redirect('/member')
            except Exception as e:msg=str(e)
    return page('Đăng ký',f"<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký thành viên FREE</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Tạo tài khoản FREE</button><a class='btn' href='/member/login'>Quay lại</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")
@app.get('/member/logout')
def member_logout():session.clear();return redirect('/member/login')

@app.get('/member')
@reqmem
def member_home():
    m=curmember(); d=idx(); groups={}
    for x in d.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '');
        if not safe_tex(p):continue
        groups.setdefault((str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or '')),[]).append(x)
    blocks=[]
    for (mon,lop,chu),items in groups.items():
        lessons=[]
        for x in items:
            p=str(x.get('path') or ''); title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name); level=lesson_level(p); dang=x.get('dang') or {}; dg=[]
            for k,v in dang.items():dg.append(f"<div class='dangrow'><span>{html.escape(str(k))}</span><span class='pill'>{int(v or 0)} câu</span></div>")
            act="<a class='btn primary' href='/member/lesson/select?path="+urllib.parse.quote(p,safe='')+"'>Chọn dạng → Làm bài</a>"
            if level=='VIP' and not is_vip(m):act="<span class='pill vip'>🔒 Chỉ VIP</span>"
            lessons.append("<div class='lesson'><h3>"+html.escape(title)+"</h3><div class='small'>"+html.escape(mon)+" · Lớp "+html.escape(lop)+"</div><span class='pill '+('vip' if level=='VIP' else 'free')+'>'+level+'</span><span class='pill'>"+str(int(x.get('questions') or x.get('count') or 0))+" câu</span><div class='dangbox'>"+''.join(dg)+"</div><div class='row' style='margin-top:8px'>"+act+"</div></div>")
        blocks.append("<div class='chapter'><div>"+html.escape(chu or 'Chương')+"</div><div class='lessons'>"+''.join(lessons)+"</div></div>")
    badge='VIP – xem/làm FREE + VIP' if is_vip(m) else 'THƯỜNG – chỉ xem/làm FREE'
    return page('Trang thành viên',"<div class='wrap'><div class='panel'><div class='head'>👤 "+html.escape(str(m.get('name') or m.get('username')))+" · <span class='pill "+('vip' if is_vip(m) else 'free')+"'>"+badge+"</span><a class='btn' style='float:right' href='/member/logout'>Thoát</a></div><div class='body'><div class='notice'>Tài khoản: <b>"+html.escape(str(m.get('username')))+"</b> · Quyền: <b>"+html.escape(str(m.get('account_type') or 'FREE'))+"</b></div>"+''.join(blocks)+"</div></div></div>")

@app.get('/member/lesson/select')
@reqmem
def lesson_select():
    path=request.args.get('path','');m=curmember();level=lesson_level(path)
    if not allowed(m,path):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho thành viên VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    qs=lesson_questions(path); counts={}
    for q in qs:counts[q['dang']]=counts.get(q['dang'],0)+1
    opts=''.join(f"<option value='{html.escape(k,quote=True)}'>{html.escape(k)} — {v} câu</option>" for k,v in counts.items())
    maxall=len(qs)
    return page('Chọn bài',f"<div class='wrap'><div class='panel'><div class='head'>📝 {html.escape(Path(path).parent.name)} · <span class='pill'>{maxall} câu</span></div><div class='body'><form method='get' action='/member/quiz'><input type='hidden' name='path' value='{html.escape(path,quote=True)}'><div class='field'><label>Dạng bài tập</label><select name='dang'><option value='__ALL__'>Tất cả dạng — {maxall} câu</option>{opts}</select></div><div class='field'><label>Số câu muốn làm</label><input name='n' type='number' min='1' max='{maxall}' value='{min(10,maxall)}' required><div class='small'>Số câu phải từ 1 đến đúng số câu đang có của dạng đã chọn. Hệ thống tự giới hạn.</div></div><button class='btn primary'>▶ Bắt đầu làm bài</button> <a class='btn' href='/member'>← Quay lại</a></form></div></div></div>")

@app.get('/member/quiz')
@reqmem
def quiz():
    path=request.args.get('path','');dang=request.args.get('dang','__ALL__');m=curmember()
    if not allowed(m,path):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Chỉ VIP.</div></div></div></div>")
    qs=lesson_questions(path); filtered=[q for q in qs if dang=='__ALL__' or q['dang']==dang]
    try:n=int(request.args.get('n','10'))
    except:n=10
    n=max(1,min(n,len(filtered)))
    import random; random.shuffle(filtered); data=filtered[:n]; token=hashlib.sha256((path+dang+str(n)).encode()).hexdigest()[:16]
    session['quiz_'+token]={'path':path,'dang':dang,'questions':data}
    qjson=json.dumps(data,ensure_ascii=False)
    return page('Làm bài',f"<div class='wrap'><div class='panel'><div class='head'>📖 {html.escape(Path(path).parent.name)} · {html.escape(dang if dang!='__ALL__' else 'Tất cả dạng')} · {n} câu</div><div class='body'><div id='app'></div></div></div></div><script>const DATA={qjson};const TOKEN={json.dumps(token)};let i=0,answers=Array(DATA.length).fill(null),checked=Array(DATA.length).fill(false);function esc(s){{return String(s).replace(/[&<>\"]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[m]))}}function render(){{const q=DATA[i];let h='<div class=\"quiztop\"><b>Câu '+(i+1)+'/'+DATA.length+'</b><span>'+({json.dumps(dang if dang!='__ALL__' else 'Tất cả dạng')})+'</span></div><div class=\"qcard\"><div class=\"qtext\">'+esc(q.text)+'</div>';if(q.kind==='choice'){{q.options.forEach((o,j)=>{{let c='';if(checked[i])c=o.correct?'correct':(answers[i]===j?'wrong':'');h+='<label class=\"opt '+c+'\"><input type=radio name=a value='+j+' '+(answers[i]===j?'checked':'')+' onclick=\"pick('+j+')\"> '+String.fromCharCode(65+j)+'. '+esc(o.text)+'</label>'}})}}else if(q.kind==='tf'){{q.statements.forEach((s,j)=>{{let v=answers[i]?.[j];let right=checked[i]&&q.statements[j].correct;h+='<div class=\"tfrow '+(checked[i]?(v===q.statements[j].correct?'opt correct':'opt wrong'):'')+'\"><b>'+(j+1)+'.</b> '+esc(s.text)+'<br><label><input type=radio name=t'+j+' onclick=\"picktf('+j+',true)\" '+(v===true?'checked':'')+'> Đúng</label> <label><input type=radio name=t'+j+' onclick=\"picktf('+j+',false)\" '+(v===false?'checked':'')+'> Sai</label></div>'}})}}else if(q.kind==='short'){{h+='<div class=\"field\"><input id=short value='+JSON.stringify(answers[i]||'')+' oninput=\"answers[i]=this.value\"></div>'}}else h+='<div class=\"small\">Câu tự luận — chưa chấm tự động.</div>';h+='<div class=\"row\" style=\"margin-top:12px\">';if(!checked[i])h+='<button class=\"btn primary\" onclick=\"check()\">Kiểm tra câu</button>';if(i>0)h+='<button class=\"btn\" onclick=\"i--;render();MathJax.typeset()\">← Trước</button>';if(i<DATA.length-1)h+='<button class=\"btn\" onclick=\"i++;render();MathJax.typeset()\">Câu tiếp →</button>';else h+='<button class=\"btn primary\" onclick=\"finish()\">🏁 Xem kết quả</button>';h+='</div></div>';document.getElementById('app').innerHTML=h;MathJax.typeset()}}function pick(v){{answers[i]=v}}function picktf(j,v){{if(!Array.isArray(answers[i]))answers[i]=[];answers[i][j]=v}}function check(){{const q=DATA[i];if(q.kind==='choice'&&answers[i]===null)return alert('Hãy chọn đáp án.');if(q.kind==='tf'&&( !Array.isArray(answers[i]) || answers[i].length<q.statements.length))return alert('Hãy chọn đủ Đúng/Sai.');checked[i]=true;render();}}function finish(){{let right=0,total=0;DATA.forEach((q,k)=>{{if(q.kind==='choice'){{total++;if(answers[k]!==null&&q.options[answers[k]].correct)right++}}else if(q.kind==='tf'){{q.statements.forEach((s,j)=>{{total++;if(Array.isArray(answers[k])&&answers[k][j]===s.correct)right++}})}}else if(q.kind==='short'){{total++;}}}});let score=total?right/total*10:0;sessionStorage.setItem('quizResult',JSON.stringify({{path:DATAPATH,dang:{json.dumps(dang)},right,total,score,answers,questions:DATA}}));location.href='/member/result'}}const DATAPATH={json.dumps(path)};render();</script>")

@app.get('/member/result')
@reqmem
def result():
    return page('Kết quả',"<div class='wrap'><div class='panel'><div class='body center'><h2>🏁 Kết quả</h2><div id='r' class='result'>Đang tính...</div><div class='review' id='rv'>Sau khi có kết quả, chọn một câu rồi bấm <b>🤖 Gemini phản biện câu này</b>.</div><div id='sel'></div><a class='btn' href='/member'>← Về danh sách bài</a></div></div></div><script>const z=JSON.parse(sessionStorage.getItem('quizResult')||'null');if(!z)location.href='/member';else{{document.getElementById('r').innerHTML='Đúng <b>'+z.right+'/'+z.total+'</b> · Điểm <b>'+z.score.toFixed(2)+'/10</b>';let s='<div class=\"field\"><label>Chọn câu cần Gemini phản biện</label><select id=qpick>'+z.questions.map((q,i)=>'<option value='+i+'>Câu '+(i+1)+': '+String(q.dang).replace(/</g,'&lt;')+'</option>').join('')+'</select></div><button class=\"btn primary\" onclick=\"review()\">🤖 Gemini phản biện câu này</button>';document.getElementById('sel').innerHTML=s;}}async function review(){{const i=+document.getElementById('qpick').value;const q=z.questions[i];const r=await fetch('/api/gemini/review',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{question:q,answer:z.answers[i]}})}});const d=await r.json();document.getElementById('rv').textContent=d.ok?d.text:'❌ '+d.error;MathJax.typeset()}}</script>")

@app.post('/api/gemini/review')
def gemini_review():
    if not GEMINI_KEY:return jsonify(ok=False,error='Chưa cấu hình GEMINI_API_KEY trên Render.'),503
    d=request.get_json(silent=True) or {};q=d.get('question') or {};answer=d.get('answer')
    prompt='Bạn là trợ lý phản biện bài tập phổ thông. Chỉ phân tích đúng 1 câu dưới đây. Nêu: học sinh đã trả lời gì; đúng/sai; chỗ sai; cách làm đúng từng bước; lỗi dễ nhầm. Giữ nguyên công thức LaTeX, không phân tích câu khác.\n\nCâu hỏi:\n'+json.dumps(q,ensure_ascii=False,indent=2)+'\n\nTrả lời của học sinh:\n'+json.dumps(answer,ensure_ascii=False)
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(GEMINI_MODEL)}:generateContent?key={urllib.parse.quote(GEMINI_KEY)}'
    body=json.dumps({'contents':[{'parts':[{'text':prompt}]}]},ensure_ascii=False).encode()
    try:
        req=urllib.request.Request(url,data=body,method='POST',headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=45) as r:data=json.loads(r.read().decode())
        text=data['candidates'][0]['content']['parts'][0]['text'];return jsonify(ok=True,text=text)
    except Exception as e:return jsonify(ok=False,error=str(e)),500

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();p=request.form.get('password') or ''
        if u==ADMIN_USERNAME and ADMIN_PASSWORD and p==ADMIN_PASSWORD:session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    return page('ADMIN',f"<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='ADMIN' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Đăng nhập</button><div class='err'>{html.escape(msg)}</div></form></div></div></div>")
@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')
@app.get('/admin')
@reqadmin
def admin_home():
    rows=[]
    for m in members().get('members',[]):
        typ=str(m.get('account_type') or 'FREE').upper();u=str(m.get('username') or '')
        rows.append(f"<tr><td>{html.escape(u)}</td><td>{html.escape(str(m.get('name') or ''))}</td><td>{html.escape(str(m.get('class') or ''))}</td><td><form method='post' action='/admin/member/type'><input type='hidden' name='username' value='{html.escape(u,quote=True)}'><select name='account_type'><option {'selected' if typ=='FREE' else ''}>FREE</option><option {'selected' if typ=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu</button></form></td><td>{html.escape(str(m.get('status') or 'ON'))} <form method='post' action='/admin/member/toggle' style='display:inline'><input type='hidden' name='username' value='{html.escape(u,quote=True)}'><button class='btn'>Bật/Tắt</button></form></td></tr>")
    return page('ADMIN',"<div class='wrap'><div class='panel'><div class='head'>🔐 ADMIN <a class='btn' style='float:right' href='/admin/logout'>Thoát</a></div><div class='body'><div class='row'><a class='btn primary' href='/admin/access'>🔐 Phân quyền bài FREE/VIP</a><a class='btn' href='/github/quan-ly'>📚 Ngân hàng GitHub</a></div><table class='table' style='width:100%;margin-top:10px'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th></tr>"+''.join(rows)+"</table></div></div></div>")
@app.post('/admin/member/type')
@reqadmin
def admin_type():
    u=request.form.get('username','');typ='VIP' if (request.form.get('account_type') or '').upper()=='VIP' else 'FREE';d=members()
    for m in d.get('members',[]):
        if m.get('username')==u:m['account_type']=typ;break
    sync_json('members.json',d,'ADMIN đổi quyền thành viên');return redirect('/admin')
@app.post('/admin/member/toggle')
@reqadmin
def admin_toggle():
    u=request.form.get('username','');d=members()
    for m in d.get('members',[]):
        if m.get('username')==u:m['status']='OFF' if m.get('status','ON')=='ON' else 'ON';break
    sync_json('members.json',d,'ADMIN đổi trạng thái thành viên');return redirect('/admin')
@app.route('/admin/member/add',methods=['GET','POST'])
@reqadmin
def admin_add():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();n=(request.form.get('name') or '').strip();c=(request.form.get('class') or '').strip();p=request.form.get('password') or '';t='VIP' if (request.form.get('account_type') or '').upper()=='VIP' else 'FREE';d=members()
        if not u or not p:msg='Thiếu tài khoản/mật khẩu.'
        elif any(m.get('username')==u for m in d.get('members',[])):msg='Tài khoản đã tồn tại.'
        else:
            d.setdefault('members',[]).append({'username':u,'name':n or u,'class':c,'account_type':t,'status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
            try:sync_json('members.json',d,'ADMIN thêm thành viên');return redirect('/admin')
            except Exception as e:msg=str(e)
    return page('Thêm thành viên',f"<div class='wrap'><div class='panel login'><div class='head'>➕ Thêm thành viên</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Lớp</label><input name='class'></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><div class='field'><label>Quyền</label><select name='account_type'><option>FREE</option><option>VIP</option></select></div><button class='btn primary'>Lưu</button> <a class='btn' href='/admin'>Quay lại</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")
@app.get('/admin/access')
@reqadmin
def admin_access():
    d=idx();a=access();cards=[]
    for x in d.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '')
        if not safe_tex(p):continue
        lv=lesson_level(p);title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name)
        cards.append("<div class='lesson'><b>"+html.escape(title)+"</b><div class='small'>"+html.escape(p)+"</div><form method='post' action='/admin/access/save'><input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'><select name='level'><option "+('selected' if lv=='FREE' else '')+">FREE</option><option "+('selected' if lv=='VIP' else '')+">VIP</option></select><button class='btn'>Lưu quyền</button></form></div>")
    return page('Quyền FREE/VIP',"<div class='wrap'><div class='panel'><div class='head'>🔐 Phân quyền từng bài</div><div class='body lessons'>"+''.join(cards)+"</div></div></div>")
@app.post('/admin/access/save')
@reqadmin
def admin_access_save():
    p=request.form.get('path','');lv='VIP' if (request.form.get('level') or '').upper()=='VIP' else 'FREE';d=access();d.setdefault('lessons',{})[p]=lv;sync_json('lesson_access.json',d,'ADMIN cập nhật quyền FREE/VIP');return redirect('/admin/access')

@app.get('/github/quan-ly')
@reqadmin
def github_manage():
    d=idx();a=access();cards=[]
    for x in d.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '');
        if not safe_tex(p):continue
        lv=lesson_level(p);title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name);n=int(x.get('questions') or x.get('count') or 0)
        cards.append(f"<div class='lesson'><h3>{html.escape(title)}</h3><div class='small'>{html.escape(p)}</div><span class='pill {'vip' if lv=='VIP' else 'free'}'>{lv}</span><span class='pill'>{n} câu</span><div style='margin-top:8px'><a class='btn primary' href='/admin/edit?path={urllib.parse.quote(p,safe='')}'>✏️ Đọc / sửa .tex</a></div></div>")
    return page('Ngân hàng GitHub',"<div class='wrap'><div class='panel'><div class='head'>📚 Mục lục GitHub</div><div class='body lessons'>"+''.join(cards)+"</div></div></div>")
@app.get('/admin/edit')
@reqadmin
def admin_edit():
    p=request.args.get('path','');sha,text=read_tex(p)
    return page('Sửa .tex',"<div class='wrap'><div class='panel'><div class='head'>✏️ "+html.escape(p)+"</div><div class='body'><textarea id='code' class='code'>"+html.escape(text)+"</textarea><div class='row' style='margin-top:8px'><button class='btn primary' onclick='saveTex()'>💾 Lưu trực tiếp GitHub</button><a class='btn' href='/github/quan-ly'>← Mục lục</a><span id='msg'></span></div></div></div></div><script>const P="+json.dumps(p)+",S="+json.dumps(sha)+";async function saveTex(){let r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:P,sha:S,text:document.getElementById('code').value})});let d=await r.json();document.getElementById('msg').textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+d.error}</script>")
@app.post('/admin/api/save')
@reqadmin
def admin_save():
    d=request.get_json(silent=True) or {};p=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not safe_tex(p) or not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu dữ liệu'),400
    try:r=gh_put(p,text,'ADMIN cập nhật .tex trực tiếp',sha);return jsonify(ok=True,commit=str((r.get('commit') or {}).get('sha') or '')[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),500

@app.get('/health')
def health():return jsonify(ok=True,source='GitHub',index=str(INDEX.exists()))

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
