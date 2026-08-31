# -*- coding: utf-8 -*-
"""Single stable GitHub question-bank portal."""
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
app.secret_key = os.getenv("APP_SECRET", "change-this-on-render")
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = (os.getenv("GITHUB_BRANCH") or "main").strip() or "main"
TOKEN = (os.getenv("GITHUB_TOKEN") or "").strip()
ADMIN_USER = (os.getenv("ADMIN_USERNAME") or "ADMIN").strip() or "ADMIN"
ADMIN_PASS = (os.getenv("ADMIN_PASSWORD") or "").strip()
GEMINI_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.getenv("GEMINI_REVIEW_MODEL") or os.getenv("GEMINI_HINT_MODEL") or "gemini-2.5-flash").strip()
ROOT = Path(__file__).resolve().parent
INDEX_FILE = ROOT / "bank_index.json"
MEMBERS_FILE = ROOT / "members.json"
ACCESS_FILE = ROOT / "lesson_access.json"
EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}", re.I)
DANG_RE = re.compile(r"\\dang(?:bt)?\s*\{([^{}]*)\}", re.I)
LEVEL_RE = re.compile(r"%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\r\n%]+)", re.I)
SHORT_RE = re.compile(r"\\shortans\s*", re.I)

CSS = r'''
*{box-sizing:border-box}body{margin:0;background:#f3f7fc;color:#17324d;font:14px "Segoe UI",Arial,sans-serif}
.top{background:#176bd3;color:#fff}.topin{max-width:1500px;margin:auto;padding:10px 16px;display:flex;align-items:center;gap:12px}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b7d5f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer}.nav a{background:#ffffff18;color:#fff;border-color:#ffffff55}
.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid #cfdae5;border-radius:11px;overflow:hidden}.head,.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.mh{display:flex;justify-content:space-between;gap:8px;align-items:center}.body{padding:10px}
.bar{padding:9px;border:1px solid #a8d7b1;background:#f0fbf2;border-radius:8px}.err{color:#b42318;font-weight:800}.login{max-width:430px;margin:60px auto}.field{margin:9px 0}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:3px}.field input{width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:7px}
.layout{display:grid;grid-template-columns:300px 1fr;gap:10px}.tree{max-height:78vh;overflow:auto}.tree details{border-bottom:1px solid #e7eef5}.tree summary{cursor:pointer;padding:7px 4px;font-weight:800}.tree a{display:block;padding:6px 8px;color:#155da8;text-decoration:none;border-radius:6px}.tree a:hover{background:#eef6ff}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px}.card{border:1px solid #d8e3ec;border-radius:10px;padding:11px;background:#fff}.meta{font-size:11px;color:#64748b}.tag{display:inline-block;padding:3px 8px;border:1px solid #cbd5e1;border-radius:999px;font-size:10px;margin:2px}.free{background:#effcf3;border-color:#86d8a2;color:#15743a}.vip{background:#fff0f8;border-color:#f0a5cb;color:#9b175a}
.dangbox{margin:8px 0;border:1px solid #d9e6f2;border-radius:8px;padding:7px;background:#fafcff}.dangrow{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #edf2f7}.dangrow:last-child{border-bottom:0}
.selectgrid,.table{width:100%;border-collapse:collapse;font-size:12px}.selectgrid th,.selectgrid td,.table th,.table td{border:1px solid #dfe7ef;padding:6px}.selectgrid th,.table th{background:#eaf3ff;text-align:center}.n{width:52px;padding:5px;border:1px solid #cbd5e1;border-radius:6px}
.qbox{border:1px solid #d4e1ed;border-radius:10px;padding:14px}.qtext{font-size:18px;line-height:1.75}.opt,.tf{display:block;border:2px solid #d8e5f1;border-radius:9px;padding:10px;margin:8px 0;cursor:pointer}.correct{background:#e8f8ee!important;border-color:#38aa63!important}.wrong{background:#fff0f1!important;border-color:#e3454d!important}
.result{padding:10px;border-radius:8px;margin-top:10px;font-weight:900}.good{background:#eaf8ef;border:1px solid #8dd2a3;color:#126b34}.bad{background:#fff0f1;border:1px solid #efa3a8;color:#a51c24}.solution{margin-top:10px;padding:12px;border:1px solid #bcd7f5;background:#f7fbff;border-radius:8px;line-height:1.7}
.palette{display:flex;gap:5px;flex-wrap:wrap;padding:8px;background:#f8fbff;border:1px solid #dfe7ef;border-radius:8px;margin-bottom:10px}.pitem{padding:4px 7px;border:1px solid #cbd5e1;border-radius:7px;background:#fff;font-size:11px}.pcur{border:2px solid #145bb0}.pdone{background:#eef9f1;border-color:#8bd2a3}.pwrong{background:#fff0f1;border-color:#ef9ea4}
.praise{margin:10px 0;padding:10px;border:1px solid #f0c56d;border-radius:8px;background:#fff8df;color:#8a5a00;font-weight:900;font-size:16px}.review{margin-top:10px;padding:12px;border:1px solid #cbbaf2;border-radius:8px;background:#faf8ff;line-height:1.7}.code{width:100%;height:70vh;font:12px/1.5 Consolas,monospace;border:1px solid #cbd5e1;border-radius:8px;padding:10px}
@media(max-width:900px){.layout{grid-template-columns:1fr}.tree{max-height:40vh}.cards{grid-template-columns:1fr}}
'''

def page(title: str, body: str) -> Response:
    return Response(
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + html.escape(title) + "</title><style>" + CSS + "</style>"
        "<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre']}};</script>"
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>"
        "</head><body><div class='top'><div class='topin'><div><div class='brand'>📚 Ngân hàng câu hỏi GitHub</div><div class='sub'>GitHub là nguồn chính · ngan-hang/*.tex</div></div>"
        "<div class='nav'><a href='/member'>📚 Mục lục</a><a href='/admin/login'>🔐 ADMIN</a>"
        f"<a href='https://github.com/{html.escape(REPO)}' target='_blank'>🐙 GitHub</a></div></div></div>{body}</body></html>", mimetype='text/html')

def loadj(path: Path, default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def members():return loadj(MEMBERS_FILE,{'members':[]})
def access():
    d=loadj(ACCESS_FILE,{'default':'FREE','lessons':{}});d.setdefault('lessons',{});d.setdefault('default','FREE');return d

def current_member():
    if session.get('role')!='member':return None
    u=session.get('username')
    return next((m for m in members().get('members',[]) if m.get('username')==u and m.get('status','ON')=='ON'),None)

def is_vip(m):return str(m.get('account_type','FREE')).upper() in {'VIP','S.VIP','ADMIN'}
def lesson_level(path):return str(access()['lessons'].get(path,access()['default'])).upper()
def can_access(m,path):return lesson_level(path)=='FREE' or is_vip(m)

def gh(path,method='GET',data=None):
    if not TOKEN:raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    owner,repo=REPO.split('/',1);body=None if data is None else json.dumps(data,ensure_ascii=False).encode()
    req=urllib.request.Request('https://api.github.com/repos/'+owner+'/'+repo+'/'+path.lstrip('/'),data=body,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl'})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try:msg=json.loads(s).get('message',s)
        except Exception:msg=s
        raise RuntimeError(f'GitHub API {e.code}: {msg}')

def read_tex(p):
    if not p.startswith('ngan-hang/') or not p.lower().endswith('.tex') or '..' in p:raise ValueError('File .tex không hợp lệ')
    d=gh('contents/'+urllib.parse.quote(p,safe='/')+'?ref='+urllib.parse.quote(BRANCH));return d.get('sha',''),base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')

def extract_braced(text,start):
    p=start
    while p<len(text) and text[p].isspace():p+=1
    if p>=len(text) or text[p]!='{':return None,p
    p+=1;depth=1;out=[]
    while p<len(text):
        c=text[p]
        if c=='{' and text[p-1]!='\\':depth+=1
        elif c=='}' and text[p-1]!='\\':
            depth-=1
            if depth==0:return ''.join(out),p+1
        out.append(c);p+=1
    return None,p

def command_args(block,cmd):
    m=re.search(re.escape(cmd)+r'\b',block,re.I)
    if not m:return []
    out=[];p=m.end()
    while True:
        val,p2=extract_braced(block,p)
        if val is None:break
        out.append(val);p=p2
    return out

def solution_of(block):
    m=re.search(r'\\loigiai\s*\{',block,re.I)
    if not m:return ''
    val,_=extract_braced(block,m.end()-1);return val or ''

def dang_before(tex,pos):
    s=tex[max(0,pos-1200):pos];ms=list(DANG_RE.finditer(s));return ms[-1].group(1).strip() if ms else 'Chưa phân dạng'

def level_of(block):
    vals=[x.strip().upper() for x in LEVEL_RE.findall(block)];s=vals[-1] if vals else ''
    if 'VDC' in s or re.search(r'\bC\b',s):return 'C'
    if 'VD' in s:return 'V'
    if 'NB' in s or 'NHAN BIET' in s:return 'N'
    return 'H'

def clean_q(block):
    s=LEVEL_RE.sub('',block);s=DANG_RE.sub('',s);s=re.sub(r'\\begin\s*\{\s*ex\s*\}|\\end\s*\{\s*ex\s*\}','',s,flags=re.I)
    s=re.split(r'\\choiceTF\b|\\choice\b|\\shortans\b',s,1,flags=re.I)[0]
    return s.strip()

def parse_questions(tex):
    out=[]
    for idx,m in enumerate(EX_RE.finditer(tex)):
        b=m.group(0);kind='DS' if re.search(r'\\choiceTF\b',b,re.I) else 'TN' if re.search(r'\\choice\b',b,re.I) else 'TLN' if SHORT_RE.search(b) else 'TL'
        q={'idx':idx,'dang':dang_before(tex,m.start()),'level':level_of(b),'kind':kind,'text':clean_q(b),'solution':solution_of(b),'raw':b}
        if kind=='TN':
            q['options']=[{'text':re.sub(r'^\\True\s*','',x,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in command_args(b,'\\choice')[:4]]
        elif kind=='DS':
            q['statements']=[{'text':re.sub(r'^\\True\s*','',x,flags=re.I).strip(),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in command_args(b,'\\choiceTF')]
        elif kind=='TLN':
            m2=re.search(r'\\shortans\s*',b,re.I);val,_=extract_braced(b,m2.end()-1) if m2 else (None,0);q['answer']=(val or '').strip()
        out.append(q)
    return out

def index_data():return loadj(INDEX_FILE,{'total_files':0,'total_questions':0,'lessons':[]})

def save_json(path:Path,data,github_path,msg):
    raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode();cur=gh('contents/'+github_path+'?ref='+urllib.parse.quote(BRANCH));gh('contents/'+github_path,'PUT',{'message':msg,'content':base64.b64encode(raw).decode(),'branch':BRANCH,'sha':cur.get('sha')});path.write_bytes(raw)

@app.get('/health')
def health():return jsonify(ok=True,app='github-bank',repo=REPO,branch=BRANCH)
@app.get('/')
def root():return redirect('/member')
@app.get('/github/repo')
def github_repo():return redirect(f'https://github.com/{REPO}')

@app.route('/member/login',methods=['GET','POST'])
def login():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();p=request.form.get('password','');h=hashlib.sha256(p.encode()).hexdigest()
        if any(m.get('username')==u and m.get('password_sha256')==h and m.get('status','ON')=='ON' for m in members().get('members',[])):
            session.clear();session.update(role='member',username=u);return redirect('/member')
        msg='Sai tài khoản hoặc mật khẩu.'
    body="<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập học viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button> <a class='btn' href='/admin/login'>ADMIN</a><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>"
    return page('Đăng nhập',body)
@app.get('/member/logout')
def logout():session.clear();return redirect('/member/login')
@app.get('/member')
def member_home():
    m=current_member()
    if not m:return redirect('/member/login')
    idx=index_data();groups={}
    for x in idx.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or x.get('file') or '')
        if p.startswith('ngan-hang/') and p.lower().endswith('.tex'):groups.setdefault((str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or 'Chưa xác định')),[]).append(x)
    tree=[];cards=[]
    for (mon,lop,ch),items in sorted(groups.items()):
        links=''.join("<a href='/member/select?path="+urllib.parse.quote(str(x.get('path')),safe='')+"'>"+html.escape(str(x.get('BaiHoc') or x.get('De') or 'Bài'))+"</a>" for x in items)
        tree.append("<details><summary>📘 "+html.escape(mon)+" · Lớp "+html.escape(lop)+" · "+html.escape(ch)+"</summary>"+links+"</details>")
        for x in items:
            p=str(x.get('path'));title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name);lvl=lesson_level(p);dhtml=''.join("<div class='dangrow'><span>"+html.escape(str(k))+"</span><span class='tag'>"+str(int(v))+" câu</span></div>" for k,v in (x.get('dang') or {}).items())
            cards.append("<div class='card'><b>"+html.escape(title)+"</b><div class='meta'>"+html.escape(mon)+" · Lớp "+html.escape(lop)+" · "+html.escape(ch)+"</div><span class='tag "+('vip' if lvl=='VIP' else 'free')+"'>"+lvl+"</span><span class='tag'>"+str(int(x.get('questions') or x.get('count') or 0))+" câu</span><div class='dangbox'>"+dhtml+"</div><a class='btn' href='/member/select?path="+urllib.parse.quote(p,safe='')+"'>🧩 Chọn dạng / số câu</a></div>")
    badge='VIP · FREE + VIP' if is_vip(m) else 'FREE · chỉ FREE'
    body="<div class='wrap'><div class='bar'>👤 <b>"+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản: <b>"+html.escape(str(m.get('username')))+"</b> · Quyền: <b>"+badge+"</b> · <a href='/member/logout'>Đăng xuất</a></div><div class='layout' style='margin-top:10px'><aside class='panel'><div class='head'>🌳 Môn → Lớp → Chương → Bài</div><div class='body tree'>"+''.join(tree)+"</div></aside><main class='panel'><div class='mh'><span>📚 Mục lục GitHub</span><span>"+str(int(idx.get('total_files') or 0))+" bài · "+str(int(idx.get('total_questions') or 0))+" câu</span></div><div class='body'><div class='cards'>"+''.join(cards)+"</div></div></main></div></div>"
    return page('Mục lục',body)
@app.get('/member/select')
def select_page():
    m=current_member()
    if not m:return redirect('/member/login')
    p=request.args.get('path','')
    if not can_access(m,p):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try:_,tex=read_tex(p);qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(e))}</div></div></div></div>")
    groups={}
    for q in qs:groups.setdefault(q['dang'],[]).append(q)
    rows=[];rid=0
    for dang,arr in groups.items():
        for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
            c={z:sum(1 for q in arr if q['kind']==kind and q['level']==z) for z in 'NHVC'}
            ins=''.join("<input class='n' type='number' name='sel:"+str(rid)+":"+kind+":"+z+"' min='0' max='"+str(c[z])+"' value='0'>" for z in 'NHVC')
            rows.append("<tr><td>"+html.escape(dang)+"</td><td>"+label+"</td><td>"+'/'.join(str(c[z]) for z in 'NHVC')+"</td><td>"+ins+"</td><td>"+str(sum(c.values()))+"</td></tr>");rid+=1
    body="<div class='wrap'><div class='panel'><div class='mh'><span>🧩 Chọn dạng bài và số câu</span><span>"+str(len(qs))+" câu</span></div><div class='body'><form method='post' action='/member/start'><input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'><div style='overflow:auto'><table class='selectgrid'><tr><th>Dạng bài</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>"+''.join(rows)+"</table></div><div class='bar' id='sum' style='margin-top:9px'>TỔNG CHỌN: 0 câu</div><button class='btn'>▶ Tạo bài luyện tập</button> <a class='btn' href='/member'>← Mục lục</a></form></div></div></div><script>function upd(){let t=0;document.querySelectorAll('.n').forEach(x=>{let v=Math.max(0,Math.min(Number(x.max)||0,Number(x.value)||0));x.value=v;t+=v});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu';}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',upd));upd();</script>"
    return page('Chọn dạng',body)
@app.post('/member/start')
def start():
    m=current_member()
    if not m:return redirect('/member/login')
    p=request.form.get('path','')
    if not can_access(m,p):return redirect('/member')
    try:_,tex=read_tex(p);qs=parse_questions(tex)
    except Exception:return redirect('/member')
    wanted=[];dangs=list(dict.fromkeys(q['dang'] for q in qs))
    for k,v in request.form.items():
        if not k.startswith('sel:'):continue
        _,rid,kind,lev=k.split(':',3)
        try:want=max(0,int(v or 0));rid=int(rid)
        except Exception:continue
        if want<=0 or rid<0 or rid//4>=len(dangs):continue
        dang=dangs[rid//4];pool=[q for q in qs if q['dang']==dang and q['kind']==kind and q['level']==lev];wanted.extend(q['idx'] for q in pool[:want])
    if not wanted:return redirect('/member/select?path='+urllib.parse.quote(p,safe=''))
    random.shuffle(wanted);session.update(practice_path=p,practice_ids=wanted,practice_pos=0,practice_right=0,practice_streak=0,practice_best=0,practice_done=[]);return redirect('/member/practice')
@app.get('/member/practice')
def practice():
    m=current_member()
    if not m:return redirect('/member/login')
    p=str(session.get('practice_path') or '');ids=list(session.get('practice_ids') or []);pos=int(session.get('practice_pos') or 0);right=int(session.get('practice_right') or 0);streak=int(session.get('practice_streak') or 0);best=int(session.get('practice_best') or 0);done=list(session.get('practice_done') or [])
    if not p or not ids:return redirect('/member')
    try:_,tex=read_tex(p);allq={q['idx']:q for q in parse_questions(tex)}
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    if pos>=len(ids):
        score=right/len(ids)*10 if ids else 0;opts=''.join("<option value='"+str(i)+"'>Câu "+str(i+1)+" · "+('Đúng' if x.get('ok') else 'Sai')+"</option>" for i,x in enumerate(done))
        body="<div class='wrap'><div class='panel'><div class='mh'><span>🎉 Kết quả</span><span>Đúng "+str(right)+"/"+str(len(ids))+" · "+f"{score:.2f}"+"/10</span></div><div class='body'><div class='result good'>Hoàn thành · Đúng <b>"+str(right)+"/"+str(len(ids))+"</b> · Chuỗi tốt nhất <b>"+str(best)+"</b></div><div class='review'><b>🤖 Gemini phản biện 1 câu</b><div><select id='pick'>"+opts+"</select> <button class='btn' onclick='reviewPick()'>Phản biện</button></div><div id='out'></div></div><a class='btn' href='/member'>← Mục lục</a></div></div></div><script>const DONE="+json.dumps(done,ensure_ascii=False)+";async function reviewPick(){const i=Number(document.getElementById('pick').value),out=document.getElementById('out');out.textContent='⏳ Gemini...';const r=await fetch('/api/gemini/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(DONE[i]||{})});const d=await r.json();out.textContent=d.ok?d.text:(d.error||'Lỗi Gemini');if(window.MathJax)MathJax.typesetPromise();}</script>"
        return page('Kết quả',body)
    q=allq.get(ids[pos])
    if not q:return redirect('/member')
    pay={'kind':q['kind'],'text':q['text'],'solution':q.get('solution',''),'dang':q['dang']}
    if q['kind']=='TN':pay['options']=q.get('options',[])
    elif q['kind']=='DS':pay['statements']=q.get('statements',[])
    elif q['kind']=='TLN':pay['answer']=q.get('answer','')
    palette=[]
    for j,qid in enumerate(ids):
        cls='pitem pcur' if j==pos else 'pitem '+('pdone' if j<len(done) and done[j].get('ok') else ('pwrong' if j<len(done) else ''))
        palette.append("<span class='"+cls+"'>"+str(j+1)+" · "+html.escape(str(allq.get(qid,{}).get('kind','')))+"</span>")
    JS="""
<script>
const Q=__Q__; let checked=false;
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function draw(){
 let h='<div class="qtext"><b>Câu __P__.</b> '+E(Q.text)+'</div>';
 if(Q.kind==='TN'){Q.options.forEach((o,i)=>h+='<label class="opt" id="o'+i+'"><input type="radio" name="a" value="'+i+'"> <b>'+String.fromCharCode(65+i)+'.</b> '+E(o.text)+'</label>');}
 else if(Q.kind==='DS'){Q.statements.forEach((s,i)=>h+='<div class="tf" id="t'+i+'"><b>'+(i+1)+'.</b> '+E(s.text)+'<br><label><input type="radio" name="t'+i+'" value="1"> Đúng</label> <label><input type="radio" name="t'+i+'" value="0"> Sai</label></div>');}
 else if(Q.kind==='TLN'){h+='<input id="ans" style="width:100%;padding:9px">';}
 else {h+='<textarea id="ans" style="width:100%;height:180px"></textarea>';}
 h+='<button class="btn" onclick="check()">✅ Kiểm tra</button><button id="next" class="btn" style="display:none" onclick="location.href=\'/member/practice/next\'">→ Câu tiếp</button><div id="r"></div>';
 document.getElementById('q').innerHTML=h; if(window.MathJax)MathJax.typesetPromise();
}
function check(){
 if(checked)return; let ok=false,student='';
 if(Q.kind==='TN'){let z=document.querySelector('input[name=a]:checked');if(!z)return alert('Chọn đáp án');let i=+z.value;student=String.fromCharCode(65+i);Q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong');});ok=!!Q.options[i].correct;}
 else if(Q.kind==='DS'){ok=true;let a=[];for(let i=0;i<Q.statements.length;i++){let z=document.querySelector('input[name=t'+i+']:checked');if(!z)return alert('Chọn đủ Đúng/Sai');let v=z.value==='1';a.push(v?'Đ':'S');document.getElementById('t'+i).classList.add(v===Q.statements[i].correct?'correct':'wrong');if(v!==Q.statements[i].correct)ok=false;}student=a.join('');}
 else {let z=document.getElementById('ans');if(!z||!z.value.trim())return alert('Nhập câu trả lời');student=z.value.trim();ok=Q.kind==='TLN'&&student.toLowerCase()===String(Q.answer||'').trim().toLowerCase();}
 document.getElementById('r').innerHTML='<div class="result '+(ok?'good':'bad')+'">'+(ok?'✅ ĐÚNG':'❌ SAI')+'</div><div class="solution"><b>📖 Lời giải</b><div>'+E(Q.solution||'Chưa có lời giải trong file TEX.').replace(/\\n/g,'<br>')+'</div></div>';
 if(window.MathJax)MathJax.typesetPromise(); checked=true; document.getElementById('next').style.display='inline-block';
 fetch('/member/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ok,student,text:Q.text,solution:Q.solution||'',kind:Q.kind,dang:Q.dang})}).then(r=>r.json()).then(d=>{if(d.praise)document.getElementById('praise').innerHTML='<div class="praise">'+E(d.praise)+'</div>';});
}
draw();
</script>
"""
    js=JS.replace('__Q__',json.dumps(pay,ensure_ascii=False)).replace('__P__',str(pos+1))
    body="<div class='wrap'><div class='panel'><div class='mh'><span>📝 Câu "+str(pos+1)+"/"+str(len(ids))+" · "+html.escape(q['dang'])+" · "+q['kind']+"</span><span>Đúng "+str(right)+" · Chuỗi "+str(streak)+"</span></div><div class='body'><div class='palette'>"+''.join(palette)+"</div><div id='praise'></div><div id='q' class='qbox'></div></div></div></div>"+js
    return page('Làm bài',body)
@app.get('/member/practice/next')
def next_question():return redirect('/member/practice') if current_member() else redirect('/member/login')
@app.post('/member/answer')
def answer():
    if not current_member():return jsonify(ok=False),401
    d=request.get_json(silent=True) or {};ok=bool(d.get('ok'));streak=int(session.get('practice_streak') or 0);streak=streak+1 if ok else 0;best=max(int(session.get('practice_best') or 0),streak);right=int(session.get('practice_right') or 0)+(1 if ok else 0);pos=int(session.get('practice_pos') or 0);done=list(session.get('practice_done') or [])
    done.append({'question':pos+1,'ok':ok,'student':str(d.get('student') or ''),'text':str(d.get('text') or ''),'solution':str(d.get('solution') or ''),'kind':str(d.get('kind') or ''),'dang':str(d.get('dang') or '')});session.update(practice_streak=streak,practice_best=best,practice_right=right,practice_pos=pos+1,practice_done=done)
    praise=''
    if ok and streak in {2,3,5,10}:praise={2:'🎉 Làm tốt lắm! 2 câu đúng liên tiếp!',3:'👏 Tuyệt vời! 3 câu đúng liên tiếp!',5:'🌟 Rất tốt! 5 câu đúng liên tiếp!',10:'🏆 Xuất sắc! 10 câu đúng liên tiếp!'}[streak]
    return jsonify(ok=True,praise=praise,streak=streak)
@app.post('/api/gemini/review')
def gemini_review():
    if not current_member():return jsonify(ok=False,error='Chưa đăng nhập'),401
    if not GEMINI_KEY:return jsonify(ok=False,error='Chưa cấu hình GEMINI_API_KEY trên Render'),400
    d=request.get_json(silent=True) or {};prompt='Phản biện đúng một câu THPT. Nêu học sinh trả lời gì, đúng/sai, sai ở đâu, cách làm đúng từng bước, kết luận. Giữ nguyên LaTeX.\n'+json.dumps(d,ensure_ascii=False)
    url='https://generativelanguage.googleapis.com/v1beta/models/'+urllib.parse.quote(GEMINI_MODEL,safe='')+':generateContent?key='+urllib.parse.quote(GEMINI_KEY,safe='')
    try:
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]},ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=45) as r:x=json.loads(r.read().decode())
        return jsonify(ok=True,text=x['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:return jsonify(ok=False,error=str(e)),500
@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        if request.form.get('username','').strip()==ADMIN_USER and ADMIN_PASS and request.form.get('password','')==ADMIN_PASS:
            session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    body="<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='"+html.escape(ADMIN_USER)+"' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>"
    return page('ADMIN',body)
@app.get('/admin')
def admin_home():
    if session.get('role')!='admin':return redirect('/admin/login')
    d=members();rows=''.join("<tr><td>"+html.escape(str(m.get('username','')))+"</td><td>"+html.escape(str(m.get('name','')))+"</td><td>"+html.escape(str(m.get('class','')))+"</td><td>"+html.escape(str(m.get('account_type','FREE')))+"</td><td>"+html.escape(str(m.get('status','ON')))+"</td></tr>" for m in d.get('members',[]))
    body="<div class='wrap'><div class='panel'><div class='mh'><span>🔐 ADMIN</span><a class='btn' href='/admin/edit'>✏️ Sửa .tex</a></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th></tr>"+rows+"</table></div></div></div>";return page('ADMIN',body)
@app.get('/admin/edit')
def admin_edit_index():
    if session.get('role')!='admin':return redirect('/admin/login')
    idx=index_data();links=[]
    for x in idx.get('lessons',[]):
        p=str(x.get('path') or '')
        if p.startswith('ngan-hang/') and p.lower().endswith('.tex'):
            title=str(x.get('BaiHoc') or x.get('De') or p);links.append("<a class='btn' href='/admin/edit/file?path="+urllib.parse.quote(p,safe='')+"'>✏️ "+html.escape(title)+"</a>")
    return page('Sửa TEX',"<div class='wrap'><div class='panel'><div class='mh'><span>✏️ ADMIN · Chọn file TEX</span><a class='btn' href='/admin'>← ADMIN</a></div><div class='body'>"+' '.join(links)+"</div></div></div>")
@app.get('/admin/edit/file')
def admin_edit_file():
    if session.get('role')!='admin':return redirect('/admin/login')
    p=request.args.get('path','')
    try:sha,text=read_tex(p)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    body="<div class='wrap'><div class='panel'><div class='mh'><b>✏️ "+html.escape(p)+"</b><a class='btn' href='/admin'>← ADMIN</a></div><div class='body'><textarea id='code' class='code'>"+html.escape(text)+"</textarea><div><button class='btn' onclick='saveTex()'>💾 Commit GitHub</button> <span id='msg'></span></div></div></div></div>"
    script="<script>const P="+json.dumps(p)+",S="+json.dumps(sha)+";async function saveTex(){const r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:P,sha:S,text:document.getElementById('code').value})});const d=await r.json();document.getElementById('msg').textContent=d.ok?'✅ Đã commit '+d.commit:'❌ '+(d.error||'Lỗi');}</script>"
    return page('Sửa TEX',body+script)
@app.post('/admin/api/save')
def admin_save():
    if session.get('role')!='admin':return jsonify(ok=False,error='Chưa đăng nhập ADMIN'),401
    d=request.get_json(silent=True) or {};p=str(d.get('path') or '');text=d.get('text');sha=str(d.get('sha') or '')
    if not p.startswith('ngan-hang/') or not p.lower().endswith('.tex') or not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu path/text/sha'),400
    try:
        z=gh('contents/'+urllib.parse.quote(p,safe='/'),'PUT',{'message':'ADMIN cập nhật trực tiếp file .tex','content':base64.b64encode(text.encode()).decode(),'branch':BRANCH,'sha':sha});return jsonify(ok=True,commit=str((z.get('commit') or {}).get('sha') or '')[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),409
@app.errorhandler(Exception)
def all_errors(exc):return page('Lỗi máy chủ',"<div class='wrap'><div class='panel'><div class='head'>⚠️ Lỗi máy chủ</div><div class='body'><div class='err'>"+html.escape(str(exc))+"</div><p><a class='btn' href='/health'>Kiểm tra /health</a></p></div></div></div>"),500
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
