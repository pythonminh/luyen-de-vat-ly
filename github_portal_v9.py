# -*- coding: utf-8 -*-
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.parse, urllib.request, urllib.error
from functools import wraps
from pathlib import Path
from flask import Flask, Response, redirect, request, session, jsonify

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET', 'change-this-on-render')
REPO = os.getenv('GITHUB_REPO', 'pythonminh/luyen-de-vat-ly').strip() or 'pythonminh/luyen-de-vat-ly'
BRANCH = os.getenv('GITHUB_BRANCH', 'main').strip() or 'main'
TOKEN = os.getenv('GITHUB_TOKEN', '').strip()
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'ADMIN').strip() or 'ADMIN'
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '').strip()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_MODEL = (os.getenv('GEMINI_REVIEW_MODEL') or os.getenv('GEMINI_HINT_MODEL') or 'gemini-2.5-flash').strip()
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'bank_index.json'
MEMBERS = ROOT / 'members.json'
ACCESS = ROOT / 'lesson_access.json'
API = 'https://api.github.com'
RAW = 'https://raw.githubusercontent.com'
EX_RE = re.compile(r'\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}', re.I)
DANG_RE = re.compile(r'\\dangbt\s*\{([^{}]*)\}', re.I)
LEVEL_RE = re.compile(r'%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\n]+)', re.I)
CHOICE_RE = re.compile(r'\\choice\b', re.I)
TF_RE = re.compile(r'\\choiceTF\b', re.I)
SHORT_RE = re.compile(r'\\shortans\s*\{([^{}]*)\}', re.I)

CSS='''*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#1970d5;color:#fff}.topin{max-width:1500px;margin:auto;padding:10px 14px;display:flex;align-items:center;gap:14px}.brand{font-size:21px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px}.nav a,.btn{display:inline-block;border:1px solid #bdd5f4;border-radius:8px;padding:7px 10px;text-decoration:none;font-weight:800;cursor:pointer;background:#fff;color:#155eaa}.nav a{background:#ffffff18;color:#fff;border-color:#ffffff66}.wrap{max-width:1500px;margin:auto;padding:12px}.toolbar{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:8px}.layout{display:grid;grid-template-columns:420px 1fr;gap:10px}.panel{background:#fff;border:1px solid #cddbea;border-radius:10px;overflow:hidden}.head{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dce6ef;font-weight:900}.body{padding:10px}.tree{height:72vh;overflow:auto}.tree details{margin:0 0 2px}.tree summary{cursor:pointer;padding:4px 2px;font-weight:800;list-style:none}.tree summary::-webkit-details-marker{display:none}.tree summary:before{content:'▶ ';font-size:10px}.tree details[open]>summary:before{content:'▼ '}.tree a{display:block;padding:4px 8px;color:#185ea9;text-decoration:none;border-radius:5px}.tree a:hover{background:#eef6ff}.tablewrap{overflow:auto}.selector{width:100%;border-collapse:separate;border-spacing:0 3px}.selector th,.selector td{padding:5px 6px;border-bottom:1px solid #e2ebf3;white-space:nowrap}.selector th{background:#edf6ff;text-align:center}.selector td:first-child{white-space:normal}.selector tr:nth-child(even) td{background:#fbfdff}.count{font-variant-numeric:tabular-nums;text-align:center}.sel{width:58px;padding:4px;border:1px solid #bfcddd;border-radius:5px}.type{font-weight:900;font-size:11px}.tn{background:#e9f7ff}.ds{background:#f7eefe}.tl{background:#fff2d6}.choice{background:#e8f7ec}.tot{font-weight:900}.sum{margin-top:8px;padding:9px;border:1px solid #a9ddb6;background:#f0fbf3;border-radius:8px}.row{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.pill{display:inline-block;border:1px solid #c5d4e2;border-radius:999px;padding:3px 7px;font-size:10px;background:#fff}.free{border-color:#86d8a2;background:#effcf3;color:#16733c}.vip{border-color:#f2a5cc;background:#fff1f8;color:#a01c60}.qwrap{margin-top:10px}.qcard{border:1px solid #d4e1ed;border-radius:10px;padding:12px;background:#fff}.qtext{font-size:16px;line-height:1.65}.opt{display:block;border:1px solid #d5e5f4;border-radius:8px;padding:9px;margin:6px 0;cursor:pointer}.opt.correct{background:#dcfce7;border-color:#58c97f}.opt.wrong{background:#fee2e2;border-color:#f18787}.tfrow{border:1px solid #d8e7f5;border-radius:8px;padding:8px;margin:6px 0}.tfrow.correct{background:#dcfce7;border-color:#58c97f}.tfrow.wrong{background:#fee2e2;border-color:#f18787}.score{padding:10px;border:1px solid #87d49a;background:#effbf2;border-radius:8px;font-weight:900}.review{margin-top:10px;padding:10px;border:1px solid #ccbaff;background:#f7f3ff;border-radius:8px;white-space:pre-wrap;line-height:1.6}.login{max-width:430px;margin:60px auto}.field{margin-bottom:8px}.field label{display:block;font-size:11px;font-weight:800;margin-bottom:3px;color:#64748b}.field input,.field select{width:100%;padding:8px;border:1px solid #c7d4e0;border-radius:7px}.code{width:100%;height:76vh;font:12px/1.5 Consolas,monospace}.err{color:#b42318;font-weight:800}.ok{color:#15803d;font-weight:800}@media(max-width:1000px){.layout{grid-template-columns:1fr}.tree{height:36vh}}'''

def gh(path, method='GET', data=None):
    if not TOKEN: raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    raw = None if data is None else json.dumps(data, ensure_ascii=False).encode()
    req = urllib.request.Request(API+path, data=raw, method=method, headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl-v9','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try: m=json.loads(s).get('message',s)
        except Exception: m=s
        raise RuntimeError(f'GitHub API {e.code}: {m}')

def gh_get(path):
    owner,repo=REPO.split('/',1)
    return gh(f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe="/")}?ref={urllib.parse.quote(BRANCH)}')

def gh_put(path,text,message,sha=None):
    owner,repo=REPO.split('/',1); d={'message':message,'content':base64.b64encode(text.encode()).decode(),'branch':BRANCH}
    if sha:d['sha']=sha
    return gh(f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe="/")}', 'PUT', d)

def load_local(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def index_data():
    if INDEX.exists(): return load_local(INDEX,{})
    d=gh_get('bank_index.json');return json.loads(base64.b64decode((d.get('content') or '').replace('\n','')).decode())

def members():return load_local(MEMBERS,{'schema':2,'members':[]})
def access_data():return load_local(ACCESS,{'schema':1,'default':'FREE','lessons':{}})
def is_vip(m):return str(m.get('account_type') or 'FREE').upper() in {'VIP','S.VIP','ADMIN'}
def current_member():
    u=session.get('username')
    for m in members().get('members',[]):
        if u and m.get('username')==u and m.get('status','ON')=='ON':return m
    return None
def lesson_level(path):
    a=access_data();return str(a.get('lessons',{}).get(path,a.get('default','FREE'))).upper()
def safe_tex(p):return isinstance(p,str) and p.startswith('ngan-hang/') and p.lower().endswith('.tex') and '..' not in p
def read_tex(p):
    if not safe_tex(p):raise ValueError('Đường dẫn .tex không hợp lệ')
    d=gh_get(p);return d.get('sha',''),base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')

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

def cmd_args(s,cmd):
    m=re.search(re.escape(cmd)+r'\b',s,re.I)
    if not m:return []
    out=[];p=m.end()
    while True:
        a,p2=arg_at(s,p)
        if a is None:break
        out.append(a);p=p2
    return out

def clean(s):
    s=re.sub(r'%[^\n]*','',s);s=DANG_RE.sub('',s);s=re.sub(r'\\begin\s*\{ex\}|\\end\s*\{ex\}','',s,flags=re.I);return s.strip()

def parse_q(block):
    dm=DANG_RE.search(block); dang=dm.group(1).strip() if dm else 'Chưa phân dạng'
    lm=LEVEL_RE.search(block); level=(lm.group(1).strip().upper()[:1] if lm else '')
    if level not in 'NHSVTC': level=''
    tf=cmd_args(block,'\\choiceTF')
    if tf:
        return {'kind':'DS','dang':dang,'level':level,'text':clean(block.split('\\choiceTF',1)[0]),'statements':[{'text':re.sub(r'^\\True\s*','',x,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in tf]}
    ch=cmd_args(block,'\\choice')
    if ch:
        return {'kind':'TN','dang':dang,'level':level,'text':clean(block.split('\\choice',1)[0]),'options':[{'text':re.sub(r'^\\True\s*','',x,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in ch[:4]]}
    sm=SHORT_RE.search(block)
    if sm:return {'kind':'TLN','dang':dang,'level':level,'text':clean(block[:sm.start()]),'answer':sm.group(1).strip()}
    return {'kind':'TL','dang':dang,'level':level,'text':clean(block)}

def questions(path):
    _,t=read_tex(path);return [parse_q(b) for b in EX_RE.findall(t)]

def page(title,body):
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"+f"<title>{html.escape(title)}</title><style>{CSS}</style><script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre']}};</script><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><div class='topin'><div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div><div class='sub'>GitHub là nguồn chính · ngan-hang/*.tex</div></div><div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>{body}</body></html>",mimetype='text/html')

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
    return page('Đăng nhập',f"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.get('/member/logout')
def member_logout():session.clear();return redirect('/member/login')

@app.get('/member')
@require_member
def member_home():
    m=current_member();idx=index_data(); groups={}
    for x in idx.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '')
        if not safe_tex(p):continue
        sub=str(x.get('Mon') or 'Khác'); cls=str(x.get('Lop') or ''); ch=str(x.get('Chuong') or 'Chưa xác định');groups.setdefault((sub,cls,ch),[]).append(x)
    blocks=[]
    for (sub,cls,ch),items in sorted(groups.items()):
        links=''.join("<a href='/member/select?path="+urllib.parse.quote(str(x.get('path')),safe='')+"'>"+html.escape(str(x.get('BaiHoc') or x.get('De') or Path(str(x.get('path'))).parent.name))+" <span class='pill'>"+str(int(x.get('questions') or x.get('count') or 0))+" câu</span></a>" for x in items)
        blocks.append("<details><summary>"+html.escape(sub)+" · Lớp "+html.escape(cls)+" · "+html.escape(ch)+" <span class='pill'>"+str(len(items))+" bài</span></summary>"+links+"</details>")
    badge='VIP — xem/làm FREE + VIP' if is_vip(m) else 'FREE — chỉ xem/làm FREE'
    body="<div class='wrap'><div class='notice'><b>👤 "+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản: <b>"+html.escape(str(m.get('username')))+"</b> · Quyền: <b>"+badge+"</b></div><div class='panel'><div class='head'>📚 Mục lục — chọn Môn → Lớp → Chương → Bài</div><div class='body tree'>"+''.join(blocks)+"</div></div></div>"
    return page('Mục lục',body)

@app.get('/member/select')
@require_member
def select_lesson():
    m=current_member();path=request.args.get('path','');items=questions(path); dgs={}
    for q in items:dgs[q['dang']]=dgs.get(q['dang'],0)+1
    rows=[]
    for dang,total in dgs.items():
        sub=[q for q in items if q['dang']==dang];cells=[]
        for kind,label in [('TN','TN'),('DS','Đ/S'),('TLN','TLN'),('TL','TL')]:
            for lev in ['N','H','V','C']:
                n=sum(1 for q in sub if q['kind']==kind and q['level']==lev); name=f'{kind}_{lev}';cells.append(f"<td class='count'><input class='sel pick' data-kind='{kind}' data-level='{lev}' data-max='{n}' type='number' min='0' max='{n}' value='0' name='{name}'></td>")
        rows.append("<tr><td><b>"+html.escape(dang)+"</b><div class='small'>"+str(total)+" câu</div></td>"+''.join(cells)+"<td class='count tot rowtotal'>0/"+str(total)+"</td></tr>")
    # header has 16 selection columns: TN/DS/TLN/TL x N/H/V/C
    header=''.join("<th>"+k+"-"+l+"</th>" for k in ['TN','Đ/S','TLN','TL'] for l in ['N','H','V','C'])
    body="<div class='wrap'><div class='panel'><div class='head'>📊 Cấu trúc bài · "+html.escape(Path(path).parent.name)+"</div><div class='body'><div class='notice'>Chọn số câu theo <b>Dạng bài tập</b> và 4 loại <b>TN / Đúng-Sai / Trả lời ngắn / Tự luận</b>. Mỗi ô chỉ cho chọn từ 0 đến đúng số câu thực tế trong file .tex.</div><form method='post' action='/member/practice'><input type='hidden' name='path' value='"+html.escape(path,quote=True)+"'><div class='tablewrap'><table class='selector'><tr><th>Dạng bài tập</th>"+header+"<th>Tổng</th></tr>"+''.join(rows)+"</table></div><div class='sum'>TỔNG CHỌN: <span id='grand'>0</span> câu <span id='limit'></span></div><div class='toolbar'><button class='btn primary' type='submit'>▶ Tạo bài luyện tập</button><a class='btn' href='/member'>← Mục lục</a></div></form></div></div></div><script>const picks=[...document.querySelectorAll('.pick')];function recalc(){let g=0;picks.forEach(e=>{let mx=Number(e.max);let v=Math.max(0,Math.min(mx,Number(e.value)||0));if(v!==Number(e.value))e.value=v;g+=v;});document.getElementById('grand').textContent=g;}picks.forEach(e=>e.addEventListener('input',recalc));recalc();</script>"
    return page('Chọn số câu',body)

@app.post('/member/practice')
@require_member
def practice():
    m=current_member();path=request.form.get('path','');qs=questions(path);wanted=[]
    for q in qs:
        key=f"{q['kind']}_{q['level']}"; target=0
        # consume in stable order; client cannot request above real max because server clamps to actual inventory
    for kind in ['TN','DS','TLN','TL']:
        for lev in ['N','H','V','C']:
            n=max(0,min(999,int(request.form.get(f'{kind}_{lev}',0) or 0)))
            pool=[q for q in qs if q['kind']==kind and q['level']==lev]
            wanted.extend(pool[:min(n,len(pool))])
    if not wanted:return redirect('/member/select?path='+urllib.parse.quote(path,safe=''))
    payload=json.dumps(wanted,ensure_ascii=False)
    body="<div class='wrap'><div class='panel'><div class='head'>📝 Bài luyện tập · <span class='pill'>"+str(len(wanted))+" câu</span><a class='btn' style='float:right' href='/member'>← Mục lục</a></div><div class='body'><div id='score' class='score'>Câu 1/"+str(len(wanted))+" · Chưa chấm</div><div id='quiz' class='qwrap'></div><div class='toolbar'><button id='reviewBtn' class='btn' style='display:none' onclick='reviewPick()'>🤖 Gemini phản biện 1 câu</button></div><div id='review'></div></div></div></div><script>const DATA="+payload+";let i=0,good=0,done=[];function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}function show(){let q=DATA[i],h='<div class=qcard><div class=qtext><b>Câu '+(i+1)+'.</b> '+esc(q.text)+'</div>';if(q.kind==='TN'){q.options.forEach((o,j)=>h+='<label class=opt id=o'+j+'><input type=radio name=a value='+j+'> <b>'+String.fromCharCode(65+j)+'.</b> '+esc(o.text)+'</label>')}else if(q.kind==='DS'){q.statements.forEach((s,j)=>h+='<div class=tfrow id=t'+j+'><b>'+String(j+1)+'.</b> '+esc(s.text)+'<br><label><input type=radio name=t'+j+' value=1> Đúng</label> <label><input type=radio name=t'+j+' value=0> Sai</label></div>')}else if(q.kind==='TLN'){h+='<input id=ans class=sel style="width:180px" placeholder="Nhập đáp án">'}else{h+='<textarea id=ans class=code style="height:130px" placeholder="Nhập bài làm"></textarea>'}h+='<div class=toolbar><button class="btn primary" onclick="check()">✅ Chọn / kiểm tra</button><button class=btn onclick="next()">→ Câu tiếp</button></div><div id=res></div></div>';document.getElementById('quiz').innerHTML=h;if(window.MathJax)MathJax.typesetPromise()}function check(){let q=DATA[i],ok=false,student='';if(q.kind==='TN'){let e=document.querySelector('input[name=a]:checked');if(!e)return alert('Hãy chọn đáp án.');let j=Number(e.value);student=String.fromCharCode(65+j);q.options.forEach((o,k)=>{if(o.correct)document.getElementById('o'+k).classList.add('correct');if(k===j&&!o.correct)document.getElementById('o'+k).classList.add('wrong')});ok=q.options[j].correct}else if(q.kind==='DS'){let arr=[];for(let j=0;j<q.statements.length;j++){let e=document.querySelector('input[name=t'+j+']:checked');if(!e)return alert('Chọn Đúng/Sai đủ các ý.');let v=e.value==='1';arr.push(v?'Đ':'S');let el=document.getElementById('t'+j);el.classList.add(v===q.statements[j].correct?'correct':'wrong')}student=arr.join('');ok=q.statements.every((s,j)=>document.querySelector('input[name=t'+j+']:checked').value==='1'===s.correct)}else{let e=document.getElementById('ans');if(!e||!e.value.trim())return alert('Hãy nhập câu trả lời.');student=e.value.trim();ok=q.kind==='TLN'&&student.toLowerCase()===String(q.answer||'').trim().toLowerCase()}document.getElementById('res').innerHTML='<div class="'+(ok?'score':'notice')+'">'+(ok?'✅ ĐÚNG':'❌ SAI')+'</div>';if(ok)good++;done.push({i,student});document.getElementById('score').textContent='Câu '+(i+1)+'/'+DATA.length+' · Đúng '+good;document.querySelectorAll('.btn').forEach(b=>{if(b.textContent.includes('kiểm tra'))b.disabled=true});}
function next(){if(i<DATA.length-1){i++;show()}else{document.getElementById('quiz').innerHTML='<div class=score>🎉 Hoàn thành · Đúng '+good+'/'+DATA.length+' · Điểm '+(good/DATA.length*10).toFixed(2)+'/10</div>';document.getElementById('reviewBtn').style.display='inline-block'}}function reviewPick(){let opts=done.map(x=>'<option value='+x.i+'>Câu '+(x.i+1)+'</option>').join('');document.getElementById('review').innerHTML='<div class=review><b>Chọn 1 câu:</b> <select id=rv>'+opts+'</select> <button class="btn primary" onclick="sendReview()">Gemini phản biện</button><div id=ro></div></div>'}async function sendReview(){let j=Number(document.getElementById('rv').value),r=done.find(x=>x.i===j),o=document.getElementById('ro');o.textContent='Đang phản biện...';try{let z=await fetch('/api/gemini/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:DATA[j],student_answer:r?r.student:''})});let d=await z.json();o.textContent=d.ok?d.text:(d.error||'Gemini lỗi')}catch(e){o.textContent=String(e)}}show();</script>"
    return page('Làm bài',body)

@app.post('/api/gemini/review')
@require_member
def gemini_review():
    if not GEMINI_API_KEY:return jsonify(ok=False,error='Chưa có GEMINI_API_KEY trên Render.'),400
    d=request.get_json(silent=True) or {};q=d.get('question') or {};student=d.get('student_answer','')
    prompt=('Bạn là trợ lý phản biện bài tập THPT. Chỉ phân tích đúng câu được gửi. Nêu: học sinh trả lời gì; đúng/sai; vì sao; lỗi dễ nhầm; cách làm đúng từng bước. Giữ nguyên công thức LaTeX.\n\n'+json.dumps({'question':q,'student_answer':student},ensure_ascii=False))
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(GEMINI_MODEL,safe="")}:generateContent?key={urllib.parse.quote(GEMINI_API_KEY,safe="")}'
    try:
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]}).encode(),method='POST',headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=45) as r:z=json.loads(r.read().decode())
        return jsonify(ok=True,text=z['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:return jsonify(ok=False,error=str(e)),500

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();p=request.form.get('password') or ''
        if u==ADMIN_USERNAME and ADMIN_PASSWORD and p==ADMIN_PASSWORD:session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    return page('ADMIN',f"<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='ADMIN' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button><div class='err'>{html.escape(msg)}</div></form></div></div></div>")

@app.get('/admin')
@require_admin
def admin_home():
    data=members();rows=[]
    for m in data.get('members',[]):rows.append('<tr><td>'+html.escape(str(m.get('username','')) )+'</td><td>'+html.escape(str(m.get('name','')) )+'</td><td>'+html.escape(str(m.get('class','')) )+'</td><td>'+html.escape(str(m.get('account_type','FREE')) )+'</td><td>'+html.escape(str(m.get('status','ON')) )+'</td></tr>')
    body="<div class='wrap'><div class='panel'><div class='head'>🔐 ADMIN</div><div class='body'><div class='toolbar'><a class='btn' href='/github/quan-ly'>📚 Ngân hàng GitHub · sửa .tex</a><a class='btn' href='/admin/logout'>Thoát</a></div><table class='selector'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>TT</th></tr>"+''.join(rows)+"</table></div></div></div>"
    return page('ADMIN',body)

@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')

@app.get('/github/quan-ly')
@require_admin
def github_manage():
    idx=index_data();cards=[]
    for x in idx.get('lessons',[]):
        if not isinstance(x,dict) or not safe_tex(str(x.get('path') or '')):continue
        p=str(x.get('path'));title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name);cards.append("<a class='btn' style='display:block;margin:4px 0' href='/admin/edit?path="+urllib.parse.quote(p,safe='')+"'>✏️ "+html.escape(title)+" · "+str(int(x.get('questions') or x.get('count') or 0))+" câu</a>")
    return page('Ngân hàng GitHub',"<div class='wrap'><div class='panel'><div class='head'>📚 Ngân hàng GitHub</div><div class='body'>"+''.join(cards)+"</div></div></div>")

@app.get('/admin/edit')
@require_admin
def admin_edit():
    p=request.args.get('path','');sha,text=read_tex(p)
    body="<div class='wrap'><div class='panel'><div class='head'>✏️ "+html.escape(p)+"</div><div class='body'><textarea id='code' class='code'>"+html.escape(text)+"</textarea><div class='toolbar'><button class='btn primary' onclick='save()'>💾 Lưu GitHub</button><a class='btn' target='_blank' href='https://github.com/"+html.escape(REPO)+"/blob/"+urllib.parse.quote(BRANCH)+"/"+urllib.parse.quote(p,safe='/')+"'>🐙 GitHub</a><span id=m></span></div></div></div></div><script>const p="+json.dumps(p)+",sha="+json.dumps(sha)+";async function save(){let r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,sha,text:document.getElementById('code').value})});let d=await r.json();document.getElementById('m').textContent=d.ok?'✅ Đã lưu GitHub':'❌ '+(d.error||'Lỗi')}</script>"
    return page('Sửa .tex',body)

@app.post('/admin/api/save')
@require_admin
def admin_save():
    d=request.get_json(silent=True) or {};p=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not safe_tex(p) or not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu dữ liệu'),400
    try:r=gh_put(p,text,'ADMIN cập nhật .tex trực tiếp',sha);return jsonify(ok=True,commit=(r.get('commit') or {}).get('sha','')[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))