# -*- coding: utf-8 -*-
"""Single stable GitHub question-bank portal."""
from __future__ import annotations
import base64,hashlib,html,json,os,random,re,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from flask import Flask,Response,request,redirect,session,jsonify
app=Flask(__name__);app.secret_key=os.getenv('APP_SECRET','change-this-on-render')
REPO=(os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').strip();BRANCH=(os.getenv('GITHUB_BRANCH') or 'main').strip() or 'main';TOKEN=(os.getenv('GITHUB_TOKEN') or '').strip();ADMIN_USER=(os.getenv('ADMIN_USERNAME') or 'ADMIN').strip() or 'ADMIN';ADMIN_PASS=(os.getenv('ADMIN_PASSWORD') or '').strip();GEMINI_KEY=(os.getenv('GEMINI_API_KEY') or '').strip();GEMINI_MODEL=(os.getenv('GEMINI_REVIEW_MODEL') or os.getenv('GEMINI_HINT_MODEL') or 'gemini-2.5-flash').strip();ROOT=Path(__file__).resolve().parent
EX_RE=re.compile(r'\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}',re.I);DANG_RE=re.compile(r'\\dang(?:bt)?\s*\{([^{}]*)\}',re.I);LV_RE=re.compile(r'%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\r\n%]+)',re.I);SHORT_RE=re.compile(r'\\shortans(?:\s*\{([^{}]*)\})?',re.I)
CSS='''*{box-sizing:border-box}body{margin:0;background:#f3f7fc;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#176bd3;color:#fff}.topin{max-width:1500px;margin:auto;padding:10px 16px;display:flex;align-items:center;gap:12px}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b7d5f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin:2px}.nav a{background:#ffffff18;color:#fff;border-color:#ffffff55}.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid #cfdae5;border-radius:11px;overflow:hidden}.head,.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.mh{display:flex;justify-content:space-between;align-items:center;gap:8px}.body{padding:10px}.login{max-width:430px;margin:60px auto}.field{margin:9px 0}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:7px}.layout{display:grid;grid-template-columns:300px 1fr;gap:10px}.tree{max-height:78vh;overflow:auto}.tree details{border-bottom:1px solid #e8eef5}.tree summary{cursor:pointer;padding:7px 4px;font-weight:800}.tree a{display:block;padding:5px 9px;color:#155da8;text-decoration:none;border-radius:6px}.tree a:hover{background:#eef6ff}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px}.card{border:1px solid #d8e3ec;border-radius:10px;padding:11px;background:#fff}.meta{font-size:11px;color:#64748b}.tag{display:inline-block;padding:3px 8px;border:1px solid #cbd5e1;border-radius:999px;font-size:10px;margin:2px}.free{background:#effcf3;border-color:#86d8a2;color:#15743a}.vip{background:#fff0f8;border-color:#f0a5cb;color:#9b175a}.selectgrid,.table{width:100%;border-collapse:collapse;font-size:12px}.selectgrid th,.selectgrid td,.table th,.table td{border:1px solid #dfe7ef;padding:6px}.selectgrid th,.table th{background:#eaf3ff;text-align:center}.n{width:52px;padding:5px;border:1px solid #cbd5e1;border-radius:6px}.qbox{border:1px solid #d4e1ed;border-radius:10px;padding:14px}.qtext{font-size:18px;line-height:1.75}.opt,.tf{display:block;border:2px solid #d8e5f1;border-radius:9px;padding:10px;margin:8px 0;cursor:pointer}.correct{background:#e8f8ee!important;border-color:#38aa63!important}.wrong{background:#fff0f1!important;border-color:#e3454d!important}.result{padding:10px;border-radius:8px;margin-top:10px;font-weight:900}.good{background:#eaf8ef;border:1px solid #8dd2a3;color:#126b34}.bad{background:#fff0f1;border:1px solid #efa3a8;color:#a51c24}.solution{margin-top:10px;padding:12px;border:1px solid #bcd7f5;background:#f7fbff;border-radius:8px;line-height:1.7}.palette{display:flex;gap:5px;flex-wrap:wrap;padding:8px;background:#f8fbff;border:1px solid #dfe7ef;border-radius:8px;margin-bottom:10px}.pitem{padding:4px 7px;border:1px solid #cbd5e1;border-radius:7px;background:#fff;font-size:11px}.pcur{border:2px solid #145bb0}.pdone{background:#eef9f1;border-color:#8bd2a3}.pwrong{background:#fff0f1;border-color:#ef9ea4}.praise{margin:10px 0;padding:10px;border:1px solid #f0c56d;border-radius:8px;background:#fff8df;color:#8a5a00;font-weight:900;font-size:16px}.review{margin-top:10px;padding:12px;border:1px solid #cbbaf2;border-radius:8px;background:#faf8ff;line-height:1.7}.code{width:100%;height:70vh;font:12px/1.5 Consolas,monospace;border:1px solid #cbd5e1;border-radius:8px;padding:10px}.err{color:#b42318;font-weight:800}@media(max-width:900px){.layout{grid-template-columns:1fr}.tree{max-height:40vh}.cards{grid-template-columns:1fr}}'''
def page(t,b):return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+html.escape(t)+"</title><style>"+CSS+"</style><script>window.MathJax={tex:{inlineMath:[['$','$'],['\\(','\\)']],displayMath:[['$$','$$'],['\\[','\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre']}};</script><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><div class='topin'><div><div class='brand'>📚 Ngân hàng câu hỏi GitHub</div><div class='sub'>GitHub là nguồn chính · ngan-hang/*.tex</div></div><div class='nav'><a href='/member'>📚 Mục lục</a><a href='/admin/login'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"+b+"</body></html>",mimetype='text/html')
def loadj(n,d):
    try:return json.loads((ROOT/n).read_text(encoding='utf-8'))
    except Exception:return d
def members():return loadj('members.json',{'members':[]})
def access():
    d=loadj('lesson_access.json',{'default':'FREE','lessons':{}});d.setdefault('default','FREE');d.setdefault('lessons',{});return d
def savej(path,d,msg):
    raw=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode();cur=gh('contents/'+path+'?ref='+urllib.parse.quote(BRANCH));gh('contents/'+path,'PUT',{'message':msg,'content':base64.b64encode(raw).decode(),'branch':BRANCH,'sha':cur.get('sha')});(ROOT/path).write_bytes(raw)
def current():
    u=session.get('username');return next((m for m in members().get('members',[]) if m.get('username')==u and m.get('status','ON')=='ON'),None) if session.get('role')=='member' else None
def vip(m):return str(m.get('account_type','FREE')).upper() in {'VIP','S.VIP','ADMIN'}
def level(p):return str(access()['lessons'].get(p,access()['default'])).upper()
def allowed(m,p):return level(p)=='FREE' or vip(m)
def gh(path,method='GET',data=None):
    if not TOKEN:raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    owner,repo=REPO.split('/',1);body=None if data is None else json.dumps(data,ensure_ascii=False).encode();req=urllib.request.Request('https://api.github.com/repos/'+owner+'/'+repo+'/'+path.lstrip('/'),data=body,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl'})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try:m=json.loads(s).get('message',s)
        except Exception:m=s
        raise RuntimeError(f'GitHub API {e.code}: {m}')
def read_tex(p):
    if not p.startswith('ngan-hang/') or not p.endswith('.tex') or '..' in p:raise ValueError('File .tex không hợp lệ')
    d=gh('contents/'+urllib.parse.quote(p,safe='/')+'?ref='+urllib.parse.quote(BRANCH));return d.get('sha',''),base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')
def bcmd(text,cmd):
    m=re.search(re.escape(cmd)+r'\s*\{',text,re.I)
    if not m:return ''
    p=m.end();st=p;dep=1
    while p<len(text) and dep:
        if text[p]=='{' and text[p-1]!='\\':dep+=1
        elif text[p]=='}' and text[p-1]!='\\':dep-=1
        p+=1
    return text[st:p-1] if dep==0 else ''
def args(text,cmd):
    m=re.search(re.escape(cmd)+r'\b',text,re.I)
    if not m:return []
    out=[];p=m.end()
    while p<len(text):
        while p<len(text) and text[p].isspace():p+=1
        if p>=len(text) or text[p]!='{':break
        st=p+1;dep=1;p+=1
        while p<len(text) and dep:
            if text[p]=='{' and text[p-1]!='\\':dep+=1
            elif text[p]=='}' and text[p-1]!='\\':dep-=1
            p+=1
        if dep:break
        out.append(text[st:p-1])
    return out
def clean(s):return re.sub(r'\\vspace\s*\{[^{}]*\}|\\dang(?:bt)?\s*\{[^{}]*\}|%\s*(?:Mức|Muc|Muc do)\s*:[^\r\n%]+','',s,flags=re.I).strip()
def level_of(s):
    x=s.upper()
    if re.search(r'\bVDC\b|\bC\b',x):return 'C'
    if re.search(r'\bVD\b|VẬN DỤNG|VAN DUNG',x):return 'V'
    if re.search(r'\bNB\b|NHẬN BIẾT|NHAN BIET',x):return 'N'
    return 'H'
def parse(tex):
    out=[];prev=0;dang=''
    for i,m in enumerate(EX_RE.finditer(tex)):
        pre=tex[prev:m.start()];ds=DANG_RE.findall(pre)
        if ds:dang=ds[-1].strip()
        inside=m.group(1);dm=DANG_RE.search(inside);qd=dm.group(1).strip() if dm else dang or 'Chưa phân dạng';lm=LV_RE.search(inside) or LV_RE.search(pre[-400:]);lev=level_of(lm.group(1) if lm else inside[:500]);kind='DS' if re.search(r'\\choiceTF\b',inside,re.I) else 'TN' if re.search(r'\\choice\b',inside,re.I) else 'TLN' if SHORT_RE.search(inside) else 'TL'
        marks=[z for z in (re.search(r'\\choiceTF\b',inside,re.I),re.search(r'\\choice\b',inside,re.I),SHORT_RE.search(inside),re.search(r'\\loigiai\b',inside,re.I)) if z];cut=min([z.start() for z in marks],default=len(inside));q={'idx':i,'dang':qd,'level':lev,'kind':kind,'raw':m.group(0),'text':clean(inside[:cut]),'solution':bcmd(inside,'\\loigiai')}
        if kind=='TN':q['options']=[{'text':re.sub(r'^\\True\s*','',z,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',z,re.I))} for z in args(inside,'\\choice')[:4]]
        elif kind=='DS':q['statements']=[{'text':re.sub(r'^\\True\s*','',z,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',z,re.I))} for z in args(inside,'\\choiceTF')]
        elif kind=='TLN':
            sm=SHORT_RE.search(inside);q['answer']=(sm.group(1) or '').strip() if sm else ''
        out.append(q);prev=m.end()
    return out
@app.get('/health')
def health():return jsonify(ok=True,app='github-bank',repo=REPO,branch=BRANCH)
@app.get('/')
def root():return redirect('/member')
@app.get('/github/repo')
def repo():return redirect('https://github.com/'+REPO)
@app.route('/member/login',methods=['GET','POST'])
def mlogin():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();p=request.form.get('password','');h=hashlib.sha256(p.encode()).hexdigest()
        if any(m.get('username')==u and m.get('password_sha256')==h and m.get('status','ON')=='ON' for m in members().get('members',[])):session.clear();session.update(role='member',username=u);return redirect('/member')
        msg='Sai tài khoản hoặc mật khẩu.'
    return page('Đăng nhập',"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập học viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>")
@app.route('/member/register',methods=['GET','POST'])
def register():
    if request.method=='GET':return page('Đăng ký',"<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký FREE</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Tạo tài khoản</button></form></div></div></div>")
    u=request.form.get('username','').strip();n=request.form.get('name','').strip();p=request.form.get('password','');d=members()
    if not u or not p or any(m.get('username')==u for m in d.get('members',[])):return redirect('/member/register')
    d.setdefault('members',[]).append({'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
    savej('members.json',d,'Đăng ký thành viên');session.clear();session.update(role='member',username=u);return redirect('/member')
@app.get('/member/logout')
def logout():session.clear();return redirect('/member/login')
@app.get('/member')
def member():
    m=current()
    if not m:return redirect('/member/login')
    idx=loadj('bank_index.json',{'lessons':[]});groups={}
    for x in idx.get('lessons',[]):
        p=str(x.get('path') or x.get('file') or '')
        if not p.startswith('ngan-hang/') or not p.endswith('.tex'):continue
        groups.setdefault((str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or 'Chưa xác định')),[]).append(x)
    left=[];cards=[]
    for (sub,lop,ch),items in sorted(groups.items()):
        left.append('<details><summary>📘 '+html.escape(sub)+' · Lớp '+html.escape(lop)+' · '+html.escape(ch)+'</summary>'+''.join("<a href='/member/select?path="+urllib.parse.quote(str(x.get('path')),safe='')+"'>"+html.escape(str(x.get('BaiHoc') or x.get('De') or Path(str(x.get('path'))).parent.name))+"</a>" for x in items)+'</details>')
        for x in items:
            p=str(x.get('path'));lvl=level(p);dgs=x.get('dang') or {};dh=''.join('<div><span>'+html.escape(str(k))+'</span> <span class="tag">'+str(int(v))+' câu</span></div>' for k,v in dgs.items());cards.append("<div class='card'><b>"+html.escape(str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name))+"</b><div class='meta'>"+html.escape(sub)+" · Lớp "+html.escape(lop)+" · "+html.escape(ch)+"</div><span class='tag "+('vip' if lvl=='VIP' else 'free')+"'>"+lvl+"</span><span class='tag'>"+str(int(x.get('questions') or x.get('count') or 0))+" câu</span><div class='dangbox'>"+dh+"</div><a class='btn' href='/member/select?path="+urllib.parse.quote(p,safe='')+"'>Chọn dạng / số câu</a></div>")
    badge='VIP · FREE + VIP' if vip(m) else 'FREE · chỉ FREE';body="<div class='wrap'><div class='bar'>👤 <b>"+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản: <b>"+html.escape(str(m.get('username')))+"</b> · Quyền: <b>"+badge+"</b></div><div class='layout' style='margin-top:10px'><aside class='panel'><div class='head'>🌳 Môn → Lớp → Chương → Bài</div><div class='body tree'>"+''.join(left)+"</div></aside><main class='panel'><div class='mh'><span>📚 Mục lục</span><span>"+str(idx.get('total_files',0))+" bài · "+str(idx.get('total_questions',0))+" câu</span></div><div class='body'><div class='cards'>"+''.join(cards)+"</div></div></main></div></div>";return page('Mục lục',body)
@app.get('/member/select')
def select():
    m=current();
    if not m:return redirect('/member/login')
    p=request.args.get('path','')
    if not allowed(m,p):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho VIP.</div></div></div></div>")
    try:_,tex=read_tex(p);qs=parse(tex)
    except Exception as e:return page('Lỗi',"<div class='wrap'><div class='panel'><div class='body err'>"+html.escape(str(e))+"</div></div></div>")
    dangs=list(dict.fromkeys(q['dang'] for q in qs));rows=[]
    for rid,dang in enumerate(dangs):
        arr=[q for q in qs if q['dang']==dang]
        for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
            c={z:sum(1 for q in arr if q['kind']==kind and q['level']==z) for z in 'NHVC'};ins=''.join("<input class='n' type='number' min='0' max='"+str(c[z])+"' value='0' name='sel:"+str(rid)+":"+kind+":"+z+"'>" for z in 'NHVC');rows.append('<tr><td>'+html.escape(dang)+'</td><td>'+label+'</td><td>'+'/'.join(str(c[z]) for z in 'NHVC')+'</td><td>'+ins+'</td><td>'+str(sum(c.values()))+'</td></tr>')
    body="<div class='wrap'><div class='panel'><div class='mh'><span>🧩 Chọn dạng bài và số câu</span><span>"+str(len(qs))+" câu · 4 loại câu</span></div><div class='body'><form method='post' action='/member/start'><input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'><div style='overflow:auto'><table class='selectgrid'><tr><th>Dạng bài tập</th><th>Loại câu</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>"+''.join(rows)+"</table></div><div class='bar' id='sum'>TỔNG CHỌN: 0 câu</div><button class='btn'>▶ Tạo bài luyện tập</button> <a class='btn' href='/member'>← Mục lục</a></form></div></div></div><script>function u(){let t=0;document.querySelectorAll('.n').forEach(x=>{x.value=Math.max(0,Math.min(+x.max||0,+x.value||0));t+=+x.value});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu'}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',u));u()</script>";return page('Chọn dạng',body)
@app.post('/member/start')
def start():
    m=current();
    if not m:return redirect('/member/login')
    p=request.form.get('path','')
    if not allowed(m,p):return redirect('/member')
    try:_,tex=read_tex(p);qs=parse(tex)
    except Exception:return redirect('/member')
    dangs=list(dict.fromkeys(q['dang'] for q in qs));wanted=[]
    for k,v in request.form.items():
        if not k.startswith('sel:'):continue
        _,rid,kind,lev=k.split(':',3);want=max(0,int(v or 0));rid=int(rid);dang=dangs[rid] if 0<=rid<len(dangs) else '';pool=[q for q in qs if q['dang']==dang and q['kind']==kind and q['level']==lev];wanted.extend(q['idx'] for q in pool[:want])
    if not wanted:return redirect('/member/select?path='+urllib.parse.quote(p,safe=''))
    random.shuffle(wanted);session.update(practice_path=p,practice_ids=wanted,practice_pos=0,practice_right=0,practice_streak=0,practice_best=0,practice_done=[]);return redirect('/member/practice')
@app.get('/member/practice')
def practice():
    m=current();
    if not m:return redirect('/member/login')
    p=str(session.get('practice_path') or '');ids=list(session.get('practice_ids') or []);pos=int(session.get('practice_pos') or 0);right=int(session.get('practice_right') or 0);streak=int(session.get('practice_streak') or 0);best=int(session.get('practice_best') or 0);done=list(session.get('practice_done') or [])
    if not p or not ids:return redirect('/member')
    try:_,tex=read_tex(p);allq={q['idx']:q for q in parse(tex)}
    except Exception as e:return page('Lỗi',"<div class='wrap'><div class='panel'><div class='body err'>"+html.escape(str(e))+"</div></div></div>")
    if pos>=len(ids):
        score=right/len(ids)*10 if ids else 0;opts=''.join("<option value='"+str(i)+"'>Câu "+str(i+1)+" · "+('Đúng' if x.get('ok') else 'Sai')+"</option>" for i,x in enumerate(done));body="<div class='wrap'><div class='panel'><div class='mh'><span>🎉 Kết quả</span><span>Đúng "+str(right)+"/"+str(len(ids))+" · "+f"{score:.2f}"+"/10</span></div><div class='body'><div class='result good'>Hoàn thành · Đúng <b>"+str(right)+"/"+str(len(ids))+"</b> · Chuỗi tốt nhất <b>"+str(best)+"</b></div><div class='review'><b>🤖 Gemini phản biện 1 câu</b><div><select id='pick'>"+opts+"</select> <button class='btn' onclick='rv()'>Phản biện</button></div><div id='out'></div></div><a class='btn' href='/member'>← Mục lục</a></div></div></div><script>const D="+json.dumps(done,ensure_ascii=False)+";async function rv(){let a=D[+document.getElementById('pick').value],o=document.getElementById('out');o.textContent='⏳ Gemini...';let r=await fetch('/api/gemini/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(a)});let d=await r.json();o.innerHTML=d.ok?d.text:'<span class="err">'+(d.error||'Lỗi Gemini')+'</span>';if(window.MathJax)MathJax.typesetPromise()}</script>";return page('Kết quả',body)
    q=allq.get(ids[pos]);
    if not q:return redirect('/member')
    pal=[]
    for j,qid in enumerate(ids):
        cls='pitem pcur' if j==pos else 'pitem '+('pdone' if j<len(done) and done[j].get('ok') else ('pwrong' if j<len(done) else ''));pal.append("<span class='"+cls+"'>"+str(j+1)+" · "+q['kind']+"</span>")
    pay={'kind':q['kind'],'text':q['text'],'solution':q.get('solution',''),'dang':q['dang'],'level':q['level']};pay.update({'options':q['options']} if q['kind']=='TN' else {'statements':q['statements']} if q['kind']=='DS' else {'answer':q.get('answer','')} if q['kind']=='TLN' else {})
    js="""<script>const Q=__Q__;let checked=false;function E(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;')}function draw(){let q=Q,h='<div class=\\\"qtext\\\"><b>Câu __P__. </b>'+E(q.text)+'</div>';if(q.kind==='TN')q.options.forEach((o,i)=>h+='<label class=\\\"opt\\\" id=\\\"o'+i+'\\\"><input type=\\\"radio\\\" name=\\\"a\\\" value=\\\"'+i+'\\\"> <b>'+String.fromCharCode(65+i)+'.</b> '+E(o.text)+'</label>');else if(q.kind==='DS')q.statements.forEach((s,i)=>h+='<div class=\\\"tf\\\" id=\\\"t'+i+'\\\"><b>'+(i+1)+'.</b> '+E(s.text)+'<br><label><input type=\\\"radio\\\" name=\\\"t'+i+'\\\" value=\\\"1\\\"> Đúng</label> <label><input type=\\\"radio\\\" name=\\\"t'+i+'\\\" value=\\\"0\\\"> Sai</label></div>');else if(q.kind==='TLN')h+='<input id=\\\"ans\\\" class=\\\"answerbox\\\" style=\\\"width:100%;padding:9px\\\">';else h+='<textarea id=\\\"ans\\\" class=\\\"answerbox\\\" style=\\\"width:100%;height:180px\\\"></textarea>';h+='<button class=\\\"btn\\\" onclick=\\\"check()\\\">✅ Kiểm tra</button><button id=\\\"next\\\" class=\\\"btn\\\" style=\\\"display:none\\\" onclick=\\\"location.href=\\\'/member/practice/next\\\'\\\">→ Câu tiếp</button><div id=\\\"r\\\"></div>';document.getElementById('q').innerHTML=h;if(window.MathJax)MathJax.typesetPromise()}function check(){if(checked)return;let q=Q,ok=false,student='';if(q.kind==='TN'){let z=document.querySelector('input[name=a]:checked');if(!z)return alert('Chọn đáp án');let i=+z.value;student=String.fromCharCode(65+i);q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')});ok=!!q.options[i].correct}else if(q.kind==='DS'){ok=true;let a=[];for(let i=0;i<q.statements.length;i++){let z=document.querySelector('input[name=t'+i+']:checked');if(!z)return alert('Chọn đủ Đúng/Sai');let v=z.value==='1';a.push(v?'Đ':'S');document.getElementById('t'+i).classList.add(v===q.statements[i].correct?'correct':'wrong');if(v!==q.statements[i].correct)ok=false}student=a.join('')}else{let z=document.getElementById('ans');if(!z||!z.value.trim())return alert('Nhập câu trả lời');student=z.value.trim();ok=q.kind==='TLN'&&student.toLowerCase()===String(q.answer||'').trim().toLowerCase()}let sol=Q.solution||'Chưa có lời giải trong file TEX.';document.getElementById('r').innerHTML='<div class=\\\"result '+(ok?'good':'bad')+'\\\">'+(ok?'✅ ĐÚNG':'❌ SAI')+'</div><div class=\\\"solution\\\"><b>📖 Lời giải</b><div>'+E(sol).replace(/\\\\n/g,'<br>')+'</div></div>';if(window.MathJax)MathJax.typesetPromise();checked=true;document.getElementById('next').style.display='inline-block';fetch('/member/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ok:ok,student:student,text:q.text,solution:sol,kind:q.kind,dang:q.dang})}).then(r=>r.json()).then(d=>{if(d.praise)document.getElementById('praise').innerHTML='<div class=\\\"praise\\\">'+E(d.praise)+'</div>';});}draw()</script>""".replace('__Q__',json.dumps(pay,ensure_ascii=False)).replace('__P__',str(pos+1));body="<div class='wrap'><div class='panel'><div class='mh'><span>📝 Câu "+str(pos+1)+"/"+str(len(ids))+" · "+html.escape(q['dang'])+" · "+q['kind']+"</span><span>Đúng "+str(right)+" · Chuỗi "+str(streak)+"</span></div><div class='body'><div class='palette'>"+''.join(pal)+"</div><div id='praise'></div><div id='q' class='qbox'></div></div></div></div>";return page('Làm bài',body+js)
@app.get('/member/practice/next')
def nextq():return redirect('/member/practice') if current() else redirect('/member/login')
@app.post('/member/answer')
def answer():
    if not current():return jsonify(ok=False),401
    d=request.get_json(silent=True) or {};ok=bool(d.get('ok'));st=int(session.get('practice_streak') or 0);st=st+1 if ok else 0;best=max(int(session.get('practice_best') or 0),st);right=int(session.get('practice_right') or 0)+(1 if ok else 0);pos=int(session.get('practice_pos') or 0);done=list(session.get('practice_done') or []);done.append({'question':pos+1,'ok':ok,'student':str(d.get('student') or ''),'text':str(d.get('text') or ''),'solution':str(d.get('solution') or ''),'kind':str(d.get('kind') or ''),'dang':str(d.get('dang') or '')});session.update(practice_streak=st,practice_best=best,practice_right=right,practice_pos=pos+1,practice_done=done);praise=''
    if ok:
        if st>=10:praise='🏆 Xuất sắc! 10 câu đúng liên tiếp — tuyệt vời!'
        elif st>=5:praise='🌟 Rất tốt! 5 câu đúng liên tiếp!'
        elif st>=3:praise='👏 Tuyệt vời! 3 câu đúng liên tiếp!'
        elif st>=2:praise='🎉 Làm tốt lắm! 2 câu đúng liên tiếp!'
    return jsonify(ok=True,right=right,streak=st,best=best,praise=praise)
@app.post('/api/gemini/review')
def review():
    if not current():return jsonify(ok=False,error='Chưa đăng nhập'),401
    if not GEMINI_KEY:return jsonify(ok=False,error='Chưa cấu hình GEMINI_API_KEY'),400
    d=request.get_json(silent=True) or {};prompt='Phản biện đúng MỘT câu. Nêu học sinh trả lời gì, đúng/sai, lỗi, lời giải đúng từng bước. Giữ nguyên LaTeX. Không phân tích câu khác.\n'+json.dumps(d,ensure_ascii=False);url='https://generativelanguage.googleapis.com/v1beta/models/'+urllib.parse.quote(GEMINI_MODEL,safe='')+':generateContent?key='+urllib.parse.quote(GEMINI_KEY,safe='')
    try:
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]}).encode(),headers={'Content-Type':'application/json'});
        with urllib.request.urlopen(req,timeout=45) as r:x=json.loads(r.read().decode());return jsonify(ok=True,text=x['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:return jsonify(ok=False,error=str(e)),500
@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST' and request.form.get('username','').strip()==ADMIN_USER and ADMIN_PASS and request.form.get('password','')==ADMIN_PASS:session.clear();session['role']='admin';return redirect('/admin')
    if request.method=='POST':msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    return page('ADMIN',"<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='"+html.escape(ADMIN_USER)+"' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>")
@app.get('/admin')
def admin():
    if session.get('role')!='admin':return redirect('/admin/login')
    rows=''.join("<tr><td>"+html.escape(str(m.get('username','')))+"</td><td>"+html.escape(str(m.get('name','')))+"</td><td>"+html.escape(str(m.get('class','')))+"</td><td><form method='post' action='/admin/member/type'><input type='hidden' name='username' value='"+html.escape(str(m.get('username','')),quote=True)+"'><select name='account_type'><option "+('selected' if str(m.get('account_type','FREE')).upper()=='FREE' else '')+">FREE</option><option "+('selected' if str(m.get('account_type','FREE')).upper()=='VIP' else '')+">VIP</option></select><button class='btn'>Lưu</button></form></td></tr>" for m in members().get('members',[]));return page('ADMIN',"<div class='wrap'><div class='panel'><div class='mh'><span>🔐 ADMIN · Thành viên</span><a class='btn' href='/member'>📚 Mục lục</a></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th></tr>"+rows+"</table></div></div></div>")
@app.post('/admin/member/type')
def member_type():
    if session.get('role')!='admin':return redirect('/admin/login')
    u=request.form.get('username','');typ='VIP' if request.form.get('account_type')=='VIP' else 'FREE';d=members()
    for m in d.get('members',[]):
        if m.get('username')==u:m['account_type']=typ;break
    try:savej('members.json',d,'ADMIN đổi quyền thành viên')
    except Exception:pass
    return redirect('/admin')
@app.get('/admin/edit')
def edit_list():
    if session.get('role')!='admin':return redirect('/admin/login')
    idx=loadj('bank_index.json',{'lessons':[]});rows=''.join("<tr><td>"+html.escape(str(x.get('BaiHoc') or x.get('De') or x.get('path')))+"</td><td><a class='btn' href='/admin/edit/file?path="+urllib.parse.quote(str(x.get('path')),safe='')+"'>✏️ Mở</a></td></tr>" for x in idx.get('lessons',[]) if str(x.get('path','')).startswith('ngan-hang/') and str(x.get('path','')).endswith('.tex'));return page('Sửa TEX',"<div class='wrap'><div class='panel'><div class='mh'><span>✏️ ADMIN · File TEX</span><a class='btn' href='/admin'>← ADMIN</a></div><div class='body'><table class='table'><tr><th>Bài</th><th></th></tr>"+rows+"</table></div></div></div>")
@app.get('/admin/edit/file')
def edit_file():
    if session.get('role')!='admin':return redirect('/admin/login')
    p=request.args.get('path','')
    try:sha,tex=read_tex(p)
    except Exception as e:return page('Lỗi',"<div class='wrap'><div class='panel'><div class='body err'>"+html.escape(str(e))+"</div></div></div>")
    return page('Sửa TEX',"<div class='wrap'><div class='panel'><div class='mh'><b>✏️ "+html.escape(p)+"</b></div><div class='body'><textarea id='code' class='code'>"+html.escape(tex)+"</textarea><button class='btn' onclick='saveIt()'>💾 Lưu trực tiếp GitHub</button><span id='msg'></span></div></div></div><script>const p="+json.dumps(p)+",s="+json.dumps(sha)+";async function saveIt(){let r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,sha:s,text:document.getElementById('code').value})});let d=await r.json();document.getElementById('msg').textContent=d.ok?'✅ Đã commit '+d.commit:'❌ '+d.error}</script>")
@app.post('/admin/api/save')
def api_save():
    if session.get('role')!='admin':return jsonify(ok=False,error='Chưa đăng nhập'),401
    d=request.get_json(silent=True) or {};p=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not isinstance(text,str) or not p.startswith('ngan-hang/') or not p.endswith('.tex') or not sha:return jsonify(ok=False,error='Thiếu dữ liệu'),400
    try:z=gh('contents/'+urllib.parse.quote(p,safe='/'),'PUT',{'message':'ADMIN cập nhật trực tiếp file .tex','content':base64.b64encode(text.encode()).decode(),'branch':BRANCH,'sha':sha});return jsonify(ok=True,commit=str((z.get('commit') or {}).get('sha') or '')[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),409
@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')
@app.errorhandler(Exception)
def err(e):return page('Lỗi máy chủ',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>"+html.escape(str(e))+"</div><a class='btn' href='/health'>/health</a></div></div></div>"),500
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
