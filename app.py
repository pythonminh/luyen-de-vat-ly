# -*- coding: utf-8 -*-
from flask import Flask, Response, request, redirect, session, jsonify
from pathlib import Path
import os, json, re, base64, hashlib, html, urllib.parse, urllib.request, urllib.error, random

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET", "change-this-on-render")
REPO = os.getenv("GITHUB_REPO", "pythonminh/luyen-de-vat-ly").strip()
BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
ADMIN_USER = os.getenv("ADMIN_USERNAME", "ADMIN").strip() or "ADMIN"
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ROOT = Path(__file__).resolve().parent
EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}", re.I)
DANG_RE = re.compile(r"\\dang(?:bt)?\s*\{([^{}]*)\}", re.I)
LEVEL_RE = re.compile(r"%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\r\n%]+)", re.I)
SHORT_RE = re.compile(r"\\shortans(?:\s*\{([^{}]*)\})?", re.I)
CSS = """
*{box-sizing:border-box}body{margin:0;background:#f3f7fc;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#176bd3;color:#fff;padding:10px 16px}.topin{max-width:1500px;margin:auto;display:flex;align-items:center;gap:12px}.brand{font-size:19px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b7d5f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin:2px}.nav a{background:#ffffff18;color:#fff;border-color:#ffffff55}.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid #cfdae5;border-radius:11px;overflow:hidden}.head,.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.mh{display:flex;justify-content:space-between;gap:8px;align-items:center}.body{padding:10px}.notice,.bar{padding:9px;border:1px solid #a8d7b1;background:#f0fbf2;border-radius:8px}.err{color:#b42318;font-weight:800}.login{max-width:430px;margin:65px auto}.field{margin:10px 0}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:7px}.layout{display:grid;grid-template-columns:300px 1fr;gap:10px}.tree{max-height:78vh;overflow:auto}.tree details{border-bottom:1px solid #e7eef5}.tree summary{cursor:pointer;padding:7px 4px;font-weight:800;list-style:none}.tree summary:before{content:'▶ ';font-size:10px}.tree details[open]>summary:before{content:'▼ '}.tree summary::-webkit-details-marker{display:none}.tree a{display:block;padding:6px 8px;color:#155da8;text-decoration:none;border-radius:6px}.tree a:hover{background:#eef6ff}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:8px}.card{border:1px solid #d8e3ec;border-radius:10px;padding:11px;background:#fff}.meta{font-size:11px;color:#64748b}.tag{display:inline-block;padding:3px 8px;border:1px solid #cbd5e1;border-radius:999px;font-size:10px;margin:2px}.free{background:#effcf3;border-color:#86d8a2;color:#15743a}.vip{background:#fff0f8;border-color:#f0a5cb;color:#9b175a}.dangbox{margin:8px 0;border:1px solid #d7e5f1;border-radius:8px;padding:7px}.dangrow{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #edf2f7}.dangrow:last-child{border-bottom:0}.selectgrid{width:100%;border-collapse:collapse;font-size:12px}.selectgrid th,.selectgrid td{border:1px solid #dfe7ef;padding:6px}.selectgrid th{background:#eaf3ff;text-align:center}.n{width:48px;padding:5px;border:1px solid #cbd5e1;border-radius:6px}.qbox{border:1px solid #d4e1ed;border-radius:10px;padding:14px}.qtext{font-size:18px;line-height:1.7}.opt,.tf{display:block;border:2px solid #d8e5f1;border-radius:9px;padding:10px;margin:8px 0;cursor:pointer}.correct{background:#e8f8ee!important;border-color:#38aa63!important}.wrong{background:#fff0f1!important;border-color:#e3454d!important}.result{padding:10px;border-radius:8px;margin-top:10px;font-weight:900}.good{background:#eaf8ef;border:1px solid #8dd2a3;color:#126b34}.bad{background:#fff0f1;border:1px solid #efa3a8;color:#a51c24}.code{width:100%;height:72vh;font:12px/1.5 Consolas,monospace}.review{margin-top:10px;padding:10px;border:1px solid #cbbaf2;border-radius:8px;background:#faf8ff;white-space:pre-wrap}@media(max-width:900px){.layout{grid-template-columns:1fr}.tree{max-height:40vh}.cards{grid-template-columns:1fr}}
"""
def page(title, body):
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+html.escape(title)+"</title><style>"+CSS+"</style>"+r"""<script>window.MathJax={tex:{inlineMath:[['$','$'],['\(','\)']],displayMath:[['$$','$$'],['\[','\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre']}};</script><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>"""+"</head><body><div class='top'><div class='topin'><div><div class='brand'>📚 Ngân hàng câu hỏi GitHub</div><div class='sub'>GitHub là nguồn chính · ngan-hang/*.tex</div></div><div class='nav'><a href='/member'>📚 Mục lục</a><a href='/admin/login'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"+body+"</body></html>", mimetype='text/html')
def load_json(name, default):
    try:return json.loads((ROOT/name).read_text(encoding='utf-8'))
    except Exception:return default
def members():return load_json('members.json',{'members':[]})
def access():
    d=load_json('lesson_access.json',{'default':'FREE','lessons':{}});d.setdefault('lessons',{});d.setdefault('default','FREE');return d
def current_member():
    if session.get('role')!='member':return None
    u=session.get('username')
    return next((m for m in members().get('members',[]) if m.get('username')==u and m.get('status','ON')=='ON'),None)
def is_vip(m):return str(m.get('account_type','FREE')).upper() in {'VIP','S.VIP','ADMIN'}
def lesson_level(p):return str(access()['lessons'].get(p,access()['default'])).upper()
def gh(path,method='GET',data=None):
    if not TOKEN:raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    owner,repo=REPO.split('/',1);body=None if data is None else json.dumps(data,ensure_ascii=False).encode()
    req=urllib.request.Request('https://api.github.com/repos/'+owner+'/'+repo+'/'+path.lstrip('/'),data=body,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl'})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try:m=json.loads(s).get('message',s)
        except Exception:m=s
        raise RuntimeError(f'GitHub API {e.code}: {m}')
def read_tex(p):
    if not p.startswith('ngan-hang/') or not p.lower().endswith('.tex') or '..' in p:raise ValueError('File .tex không hợp lệ')
    d=gh('contents/'+urllib.parse.quote(p,safe='/')+'?ref='+urllib.parse.quote(BRANCH));return d.get('sha',''),base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')
def split_args(text,cmd):
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
def parse_questions(tex):
    out=[]
    for idx,b in enumerate(EX_RE.findall(tex)):
        dm=DANG_RE.search(b);lm=LEVEL_RE.search(b);dang=dm.group(1).strip() if dm else 'Chưa phân dạng';x=lm.group(1).strip().upper() if lm else 'H'
        if 'VDC' in x or re.search(r'\bC\b',x):lev='C'
        elif re.search(r'\bVD\b',x):lev='V'
        elif 'NB' in x or 'NHAN BIET' in x:lev='N'
        else:lev='H'
        kind='DS' if re.search(r'\\choiceTF\b',b,re.I) else 'TN' if re.search(r'\\choice\b',b,re.I) else 'TLN' if re.search(r'\\shortans\b',b,re.I) else 'TL'
        text=clean_text(re.split(r'\\choiceTF|\\choice|\\shortans',b,1,flags=re.I)[0])
        q={'idx':idx,'raw':b,'dang':dang,'level':lev,'kind':kind,'text':text}
        if kind=='TN':q['options']=[{'text':re.sub(r'^\\True\s*','',z,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',z,re.I))} for z in split_args(b,'\\choice')[:4]]
        elif kind=='DS':q['statements']=[{'text':re.sub(r'^\\True\s*','',z,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',z,re.I))} for z in split_args(b,'\\choiceTF')]
        elif kind=='TLN':
            sm=SHORT_RE.search(b);q['answer']=sm.group(1).strip() if sm and sm.group(1) else ''
        out.append(q)
    return out
def clean_text(s):
    return re.sub(r'\\vspace\s*\{[^{}]*\}|%\s*(?:Mức|Muc|Muc do)\s*:[^\r\n%]+|\\dang(?:bt)?\s*\{[^{}]*\}','',s,flags=re.I).strip()

def save_json(path,data,msg):
    raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode();cur=gh('contents/'+path+'?ref='+urllib.parse.quote(BRANCH));gh('contents/'+path,'PUT',{'message':msg,'content':base64.b64encode(raw).decode(),'branch':BRANCH,'sha':cur.get('sha')});(ROOT/path).write_bytes(raw)
@app.get('/health')
def health():return jsonify(ok=True,app='github-bank',repo=REPO,branch=BRANCH)
@app.get('/')
def root():return redirect('/member')
@app.route('/member/login',methods=['GET','POST'])
def login():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();p=request.form.get('password','');h=hashlib.sha256(p.encode()).hexdigest()
        if any(m.get('username')==u and m.get('password_sha256')==h and m.get('status','ON')=='ON' for m in members().get('members',[])):
            session.clear();session.update(role='member',username=u);return redirect('/member')
        msg='Sai tài khoản hoặc mật khẩu.'
    return page('Đăng nhập',"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập học viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>")
@app.get('/member/logout')
def logout():session.clear();return redirect('/member/login')
@app.get('/member')
def member_home():
    m=current_member()
    if not m:return redirect('/member/login')
    idx=load_json('bank_index.json',{'total_files':0,'total_questions':0,'lessons':[]}); groups={}
    for x in idx.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or x.get('file') or '')
        if p.startswith('ngan-hang/') and p.lower().endswith('.tex'):groups.setdefault((str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or 'Chưa xác định')),[]).append(x)
    tree=[];cards=[]
    for (sub,lop,ch),items in sorted(groups.items()):
        links=''.join("<a href='/member/select?path="+urllib.parse.quote(str(x.get('path')),safe='')+"'>"+html.escape(str(x.get('BaiHoc') or x.get('De') or Path(str(x.get('path'))).parent.name))+"</a>" for x in items)
        tree.append("<details><summary>📘 "+html.escape(sub)+" · Lớp "+html.escape(lop)+" · "+html.escape(ch)+"</summary>"+links+"</details>")
        for x in items:
            p=str(x.get('path'));title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name);lvl=lesson_level(p);cnt=int(x.get('questions') or x.get('count') or 0);dgs=x.get('dang') or {};dhtml=''.join("<div class='dangrow'><span>"+html.escape(str(k))+"</span><span class='tag'>"+str(int(v))+" câu</span></div>" for k,v in dgs.items())
            cards.append("<div class='card'><b>"+html.escape(title)+"</b><div class='meta'>"+html.escape(sub)+" · Lớp "+html.escape(lop)+" · "+html.escape(ch)+"</div><span class='tag "+('vip' if lvl=='VIP' else 'free')+"'>"+lvl+"</span><span class='tag'>"+str(cnt)+" câu</span><div class='dangbox'>"+dhtml+"</div><a class='btn' href='/member/select?path="+urllib.parse.quote(p,safe='')+"'>Chọn dạng / số câu</a></div>")
    badge='VIP · xem/làm FREE + VIP' if is_vip(m) else 'FREE · xem/làm FREE'
    body="<div class='wrap'><div class='notice'>👤 <b>"+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản: <b>"+html.escape(str(m.get('username')))+"</b> · Quyền: <b>"+badge+"</b> · <a href='/member/logout'>Đăng xuất</a></div><div class='layout' style='margin-top:10px'><aside class='panel'><div class='head'>🌳 Môn → Lớp → Chương → Bài</div><div class='body tree'>"+''.join(tree)+"</div></aside><main class='panel'><div class='mh'><span>📚 Mục lục GitHub</span><span>"+str(int(idx.get('total_files') or 0))+" bài · "+str(int(idx.get('total_questions') or 0))+" câu</span></div><div class='body'><div class='cards'>"+''.join(cards)+"</div></div></main></div></div>"
    return page('Mục lục',body)
@app.get('/member/register')
def register_form():return page('Đăng ký',"<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký FREE</div><div class='body'><form method='post' action='/member/register'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Tạo tài khoản</button></form></div></div></div>")
@app.post('/member/register')
def register():
    u=request.form.get('username','').strip();n=request.form.get('name','').strip();p=request.form.get('password','');d=members()
    if not u or not p or any(m.get('username')==u for m in d.get('members',[])):return redirect('/member/register')
    d.setdefault('members',[]).append({'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
    save_json('members.json',d,'Đăng ký thành viên');session.clear();session.update(role='member',username=u);return redirect('/member')
@app.get('/member/select')
def select_page():
    m=current_member()
    if not m:return redirect('/member/login')
    p=request.args.get('path','')
    if lesson_level(p)!='FREE' and not is_vip(m):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try:_,tex=read_tex(p);qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>"+html.escape(str(e))+"</div></div></div></div>")
    groups={}
    for q in qs:groups.setdefault(q['dang'],[]).append(q)
    rows=[]
    for dang,arr in groups.items():
        for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
            c={z:sum(1 for q in arr if q['kind']==kind and q['level']==z) for z in 'NHVC'};ins=''.join("<input class='n' type='number' min='0' max='"+str(c[z])+"' value='0' name='sel_"+re.sub(r'[^A-Za-z0-9]','_',dang)+"_"+kind+"_"+z+"'>" for z in 'NHVC')
            rows.append("<tr><td>"+html.escape(dang)+"</td><td>"+label+"</td><td>"+str(c['N'])+"/"+str(c['H'])+"/"+str(c['V'])+"/"+str(c['C'])+"</td><td>"+ins+"</td><td>"+str(sum(c.values()))+"</td></tr>")
    body="<div class='wrap'><div class='panel'><div class='mh'><span>🧩 Chọn dạng bài và số câu</span><span>"+str(len(qs))+" câu</span></div><div class='body'><form method='post' action='/member/start'><input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'><div style='overflow:auto'><table class='selectgrid'><tr><th>Dạng bài</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>"+''.join(rows)+"</table></div><div class='bar' id='sum' style='margin-top:9px'>TỔNG CHỌN: 0 câu</div><button class='btn'>▶ Tạo bài luyện tập</button> <a class='btn' href='/member'>← Mục lục</a></form></div></div></div><script>function u(){let t=0;document.querySelectorAll('.n').forEach(x=>{let v=Math.max(0,Math.min(Number(x.max)||0,Number(x.value)||0));x.value=v;t+=v});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu'}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',u));u()</script>"
    return page('Chọn dạng',body)
@app.post('/member/start')
def start():
    m=current_member()
    if not m:return redirect('/member/login')
    p=request.form.get('path','')
    if not can_access(m,p):return redirect('/member')
    try:_,tex=read_tex(p);qs=parse_questions(tex)
    except Exception:return redirect('/member')
    buckets={}
    for k,v in request.form.items():
        if k.startswith('sel_'):
            try:n=max(0,int(v))
            except Exception:n=0
            b=k.split('_');buckets[('_'.join(b[1:-2]),b[-2],b[-1])]=n
    chosen=[]
    for q in qs:
        key=(re.sub(r'[^A-Za-z0-9]','_',q['dang']),q['kind'],q['level'])
        if buckets.get(key,0)>0:chosen.append(q['idx']);buckets[key]-=1
    if not chosen:return redirect('/member/select?path='+urllib.parse.quote(p,safe=''))
    random.shuffle(chosen);session.update(practice_path=p,practice_ids=chosen,practice_pos=0,practice_right=0,practice_done=[]);return redirect('/member/practice')
def can_access(m,p):return lesson_level(p)=='FREE' or is_vip(m)
@app.get('/member/practice')
def practice():
    m=current_member()
    if not m:return redirect('/member/login')
    p=str(session.get('practice_path') or '');ids=list(session.get('practice_ids') or []);pos=int(session.get('practice_pos') or 0);right=int(session.get('practice_right') or 0);done=list(session.get('practice_done') or [])
    if not p or not ids:return redirect('/member')
    try:_,tex=read_tex(p);allq={q['idx']:q for q in parse_questions(tex)}
    except Exception as e:return page('Lỗi',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>"+html.escape(str(e))+"</div></div></div></div>")
    if pos>=len(ids):
        body="<div class='wrap'><div class='panel'><div class='mh'><span>🎉 Kết quả</span><span>"+str(right)+"/"+str(len(ids))+" · "+f"{right/len(ids)*10:.2f}"+"/10</span></div><div class='body'><div class='result good'>Hoàn thành · Đúng <b>"+str(right)+"/"+str(len(ids))+"</b></div><div class='review'><b>🤖 Gemini phản biện 1 câu</b><div><select id='pick'>"+''.join("<option value='"+str(i)+"'>Câu "+str(i+1)+"</option>" for i in range(len(done)))+"</select> <button class='btn' onclick='rv()'>Phản biện</button></div><div id='out'></div></div><a class='btn' href='/member'>← Mục lục</a></div></div></div><script>const D="+json.dumps(done,ensure_ascii=False)+";async function rv(){let a=D[Number(document.getElementById('pick').value)],o=document.getElementById('out');o.textContent='⏳ Gemini...';let r=await fetch('/api/gemini/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(a)});let d=await r.json();o.textContent=d.ok?d.text:(d.error||'Lỗi Gemini')}</script>"
        return page('Kết quả',body)
    q=allq.get(ids[pos])
    if not q:return redirect('/member')
    pay={'kind':q['kind'],'text':q['text']};
    if q['kind']=='TN':pay['options']=q['options']
    if q['kind']=='DS':pay['statements']=q['statements']
    if q['kind']=='TLN':pay['answer']=q.get('answer','')
    body="<div class='wrap'><div class='panel'><div class='mh'><span>📝 Câu "+str(pos+1)+"/"+str(len(ids))+" · "+html.escape(q['dang'])+"</span><span>Đúng "+str(right)+"</span></div><div class='body'><div id='q' class='qbox'></div></div></div></div><script>const Q="+json.dumps(pay,ensure_ascii=False)+";let checked=false;function e(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;')}function d(){let q=Q,h='<div class=\"qtext\">'+e(q.text)+'</div>';if(q.kind==='TN')q.options.forEach((o,i)=>h+='<label class=\"opt\" id=\"o'+i+'\"><input type=\"radio\" name=\"a\" value=\"'+i+'\"> <b>'+String.fromCharCode(65+i)+'.</b> '+e(o.text)+'</label>');else if(q.kind==='DS')q.statements.forEach((s,i)=>h+='<div class=\"tf\" id=\"t'+i+'\"><b>'+(i+1)+'.</b> '+e(s.text)+'<br><label><input type=\"radio\" name=\"t'+i+'\" value=\"1\"> Đúng</label> <label><input type=\"radio\" name=\"t'+i+'\" value=\"0\"> Sai</label></div>');else h+='<input id=\"ans\" style=\"width:100%;padding:9px\">';h+='<button class=\"btn\" onclick=\"c()\">✅ Kiểm tra</button><div id=\"r\"></div>';document.getElementById('q').innerHTML=h;if(window.MathJax)MathJax.typesetPromise()}function c(){if(checked)return;let q=Q,ok=false,student='';if(q.kind==='TN'){let z=document.querySelector('input[name=a]:checked');if(!z)return alert('Chọn đáp án');let i=+z.value;student=String.fromCharCode(65+i);q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')});ok=!!q.options[i].correct}else if(q.kind==='DS'){ok=true;let a=[];for(let i=0;i<q.statements.length;i++){let z=document.querySelector('input[name=t'+i+']:checked');if(!z)return alert('Chọn đủ Đúng/Sai');let v=z.value==='1';a.push(v?'Đ':'S');document.getElementById('t'+i).classList.add(v===q.statements[i].correct?'correct':'wrong');if(v!==q.statements[i].correct)ok=false}student=a.join('')}else{student=document.getElementById('ans').value.trim();if(!student)return alert('Nhập đáp án');ok=q.kind==='TLN'&&student.toLowerCase()===String(q.answer||'').trim().toLowerCase()}document.getElementById('r').innerHTML='<div class=\"result '+(ok?'good':'bad')+'\">'+(ok?'✅ ĐÚNG':'❌ SAI')+'</div>';checked=true;fetch('/member/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ok:ok,student:student})})}d()</script>"
    return page('Làm bài',body)
@app.post('/member/answer')
def answer():
    if not current_member():return jsonify(ok=False),401
    d=request.get_json(silent=True) or {};done=list(session.get('practice_done') or []);done.append({'question':int(session.get('practice_pos') or 0),'student':str(d.get('student') or ''),'ok':bool(d.get('ok'))});session['practice_done']=done
    if d.get('ok'):session['practice_right']=int(session.get('practice_right') or 0)+1
    session['practice_pos']=int(session.get('practice_pos') or 0)+1;return jsonify(ok=True)
@app.post('/api/gemini/review')
def gemini_review():
    if not current_member():return jsonify(ok=False,error='Chưa đăng nhập'),401
    if not GEMINI_KEY:return jsonify(ok=False,error='Chưa cấu hình GEMINI_API_KEY'),400
    d=request.get_json(silent=True) or {};prompt='Phản biện đúng một câu THPT. Nêu trả lời học sinh, đúng/sai, lỗi, cách làm đúng từng bước. Giữ LaTeX.\n'+json.dumps(d,ensure_ascii=False)
    url='https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key='+urllib.parse.quote(GEMINI_KEY,safe='')
    try:
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=45) as r:x=json.loads(r.read().decode())
        return jsonify(ok=True,text=x['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:return jsonify(ok=False,error=str(e)),500
@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        if request.form.get('username','').strip()==ADMIN_USER and ADMIN_PASS and request.form.get('password','')==ADMIN_PASS:session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    body="<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='"+html.escape(ADMIN_USER)+"' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>"
    return page('ADMIN',body)
@app.get('/admin')
def admin_home():
    if session.get('role')!='admin':return redirect('/admin/login')
    d=members();rows=''.join("<tr><td>"+html.escape(str(m.get('username','')))+"</td><td>"+html.escape(str(m.get('name','')))+"</td><td>"+html.escape(str(m.get('class','')))+"</td><td>"+html.escape(str(m.get('account_type','FREE')))+"</td></tr>" for m in d.get('members',[]))
    return page('ADMIN',"<div class='wrap'><div class='panel'><div class='mh'><span>🔐 ADMIN</span><a class='btn' href='/member'>📚 Mục lục</a></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th></tr>"+rows+"</table></div></div></div>")
@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')
@app.get('/admin/edit')
def admin_edit():return redirect('/member') if session.get('role')!='admin' else page('ADMIN','<div class="wrap"><div class="panel"><div class="body"><div class="bar">ADMIN đã đăng nhập. Chức năng sửa .tex sẽ được nối sau khi luồng mục lục ổn định.</div></div></div></div>')
@app.errorhandler(Exception)
def all_errors(exc):return page('Lỗi máy chủ',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>"+html.escape(str(exc))+"</div><a class='btn' href='/health'>/health</a></div></div></div>"),500
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
