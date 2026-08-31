# -*- coding: utf-8 -*-
"""Luyen de AI - GitHub only: members, VIP/FREE, quiz one-by-one, MathJax, Gemini review, ADMIN .tex."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import wraps
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, session

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET", "change-this-on-render")
REPO = os.getenv("GITHUB_REPO", "pythonminh/luyen-de-vat-ly").strip()
BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "ADMIN").strip() or "ADMIN"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = (os.getenv("GEMINI_REVIEW_MODEL") or os.getenv("GEMINI_HINT_MODEL") or "gemini-2.5-flash").strip()

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "bank_index.json"
MEMBERS = ROOT / "members.json"
ACCESS = ROOT / "lesson_access.json"

EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}", re.I)
DANG_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)
CHOICE_RE = re.compile(r"\\choice\b", re.I)
TF_RE = re.compile(r"\\choiceTF\b", re.I)
SHORT_RE = re.compile(r"\\shortans\s*\{([^{}]*)\}", re.I)
ID_RE = re.compile(r"%\s*ID\s*:[^\n]*", re.I)
LEVEL_RE = re.compile(r"%\s*Mức\s*:[^\n]*", re.I)
LOIGIAI_RE = re.compile(r"\\loigiai\s*\{", re.I)

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial,sans-serif}
.top{background:#1769d2;color:#fff;position:sticky;top:0;z-index:20}
.topin{max-width:1500px;margin:auto;padding:10px 16px;display:flex;align-items:center;gap:14px}
.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.nav a{color:#fff;text-decoration:none;border:1px solid #ffffff66;border-radius:8px;padding:7px 10px;font-weight:800}
.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid #d4dfeb;border-radius:12px;overflow:hidden}
.head,.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dce7f1;font-weight:900}
.mh{display:flex;justify-content:space-between;gap:8px;align-items:center}.body{padding:12px}
.layout{display:grid;grid-template-columns:250px 1fr;gap:12px}
.field{margin-bottom:8px}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:3px}
.field input,.field select{width:100%;padding:8px;border:1px solid #c7d5e3;border-radius:8px;background:#fff}
.btn{display:inline-block;padding:7px 10px;border:1px solid #a9c9ee;border-radius:8px;background:#fff;color:#145bb0;font-weight:800;text-decoration:none;cursor:pointer}
.btn.primary{background:#1769d2;color:#fff;border-color:#1769d2}.btn.good{background:#eaf9ef;border-color:#86d99e;color:#166534}
.btn.warn{background:#fff7e8;border-color:#f0c36a;color:#8a5300}.row{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.pill,.tag{display:inline-block;padding:4px 8px;border:1px solid #cbd8e5;border-radius:999px;font-size:10px;font-weight:800;background:#fff}
.free{border-color:#86d39c;background:#effbf3;color:#15733b}.vip{border-color:#ef9cc7;background:#fff0f8;color:#9b175f}
.notice{padding:10px;border:1px solid #acd2f4;background:#eef7ff;border-radius:9px;margin-bottom:10px}
.err{color:#b42318;font-weight:900}.ok{color:#14773a;font-weight:900}
.subject{margin-bottom:12px}.subjectbar{padding:10px 12px;border-radius:10px;background:linear-gradient(90deg,#1d5ed5,#4c98ec);color:#fff;font-size:18px;font-weight:900}
.classbar{margin-top:8px;padding:8px 12px;background:#eef3f8;border:1px solid #d7e2ec;border-radius:9px;font-weight:900}
.chapter{margin-top:8px;border:1px solid #d4e1ee;border-radius:10px;overflow:hidden}.chaptertitle{padding:8px 11px;background:#deebff;color:#164879;font-weight:900}
.lessons{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:8px;padding:8px}
.lesson{border:1px solid #d9e4ee;border-radius:10px;padding:9px}.lesson h3{font-size:14px;margin:0 0 4px}
.dangbox{margin-top:8px;border:1px solid #d8e7f7;border-radius:8px;background:#f8fbff;padding:7px}
.dangrow{display:flex;justify-content:space-between;gap:7px;padding:5px 3px;border-bottom:1px solid #e5edf5}.dangrow:last-child{border-bottom:0}
.quizgrid{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin:10px 0}.typebtn{padding:8px;border:1px solid #bcd7f4;border-radius:8px;background:#fff;color:#145bb0;font-weight:900;cursor:pointer}
.qwrap{max-width:1100px;margin:auto}.qcard{border:1px solid #d4e2ee;border-radius:12px;background:#fff;padding:14px}.qtext{font-size:17px;line-height:1.8}
.opt{display:block;padding:10px;margin:7px 0;border:1px solid #d6e5f5;border-radius:9px;cursor:pointer}.opt input{margin-right:7px}
.opt.correct{background:#dcfce7;border-color:#4ade80}.opt.wrong{background:#fee2e2;border-color:#f87171}
.tfrow{padding:9px;border:1px solid #dce9f6;border-radius:9px;background:#f8fbff;margin:7px 0}.tfrow.correct{background:#dcfce7;border-color:#4ade80}.tfrow.wrong{background:#fee2e2;border-color:#f87171}
.shortinput{width:100%;max-width:560px;padding:10px;border:1px solid #cbd5e1;border-radius:8px}
.result{margin-top:10px;padding:11px;border-radius:9px;background:#effbf3;border:1px solid #8fdaa5;font-weight:900}
.review{margin-top:10px;padding:11px;border:1px solid #c5d9f4;background:#f5f9ff;border-radius:9px;line-height:1.7}
.code{width:100%;height:72vh;resize:vertical;border:1px solid #bdccdb;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}
.login{max-width:430px;margin:60px auto}.hide{display:none}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:8px}
@media(max-width:900px){.layout{grid-template-columns:1fr}.quizgrid{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.quizgrid{grid-template-columns:1fr}.qtext{font-size:15px}}
"""

def gh(path, method="GET", data=None):
    if not TOKEN:
        raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    raw = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("https://api.github.com" + path, data=raw, method=method, headers={
        "Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28","User-Agent":"ldvl-github-v5",
        "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try: msg=json.loads(raw).get("message",raw)
        except Exception: msg=raw
        raise RuntimeError(f"GitHub API {e.code}: {msg}") from e

def gh_get(path):
    owner,repo=REPO.split("/",1)
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(BRANCH)}")

def gh_put(path,text,message,sha=None):
    owner,repo=REPO.split("/",1)
    d={"message":message,"content":base64.b64encode(text.encode()).decode(),"branch":BRANCH}
    if sha:d["sha"]=sha
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe='/')}",'PUT',d)

def local_json(path, default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

def index_data():
    if INDEX.exists():return local_json(INDEX,{})
    d=gh_get("bank_index.json"); text=base64.b64decode((d.get("content") or "").replace("\n","")).decode("utf-8","replace")
    return json.loads(text)

def members_data():return local_json(MEMBERS,{"schema":2,"members":[]})
def access_data():
    d=local_json(ACCESS,{"schema":1,"default":"FREE","lessons":{}});d.setdefault("default","FREE");d.setdefault("lessons",{});return d

def save_json(filename,data,message):
    text=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    try:sha=gh_get(filename).get("sha")
    except Exception:sha=None
    gh_put(filename,text,message,sha);Path(ROOT/filename).write_text(text,encoding="utf-8")

def save_members(data):save_json("members.json",data,"ADMIN cập nhật thành viên")
def save_access(data):save_json("lesson_access.json",data,"ADMIN cập nhật quyền FREE/VIP")
def account_type(m):return str(m.get("account_type") or "FREE").upper()
def is_vip(m):return account_type(m) in {"VIP","S.VIP","ADMIN"}
def current_member():
    u=session.get("username")
    for m in members_data().get("members",[]):
        if u and m.get("username")==u and m.get("status","ON")=="ON":return m
    return None
def lesson_level(path):
    a=access_data();return str(a.get("lessons",{}).get(path,a.get("default","FREE"))).upper()
def allowed(m,path):return lesson_level(path)=="FREE" or is_vip(m)
def safe_tex(path):return isinstance(path,str) and path.startswith("ngan-hang/") and path.lower().endswith(".tex") and ".." not in path
def read_tex(path):
    if not safe_tex(path):raise ValueError("Đường dẫn .tex không hợp lệ")
    d=gh_get(path);return d.get("sha",""),base64.b64decode((d.get("content") or "").replace("\n","")).decode("utf-8","replace")

def brace_arg(s,pos):
    while pos<len(s) and s[pos].isspace():pos+=1
    if pos>=len(s) or s[pos]!="{":return None,pos
    dep=0;st=pos+1;i=pos
    while i<len(s):
        if s[i]=="{" and (i==0 or s[i-1]!="\\"):dep+=1
        elif s[i]=="}" and (i==0 or s[i-1]!="\\"):
            dep-=1
            if dep==0:return s[st:i],i+1
        i+=1
    return None,len(s)

def cmd_args(s,cmd):
    m=re.search(re.escape(cmd)+r"\b",s,re.I)
    if not m:return []
    out=[];pos=m.end()
    while True:
        a,pos2=brace_arg(s,pos)
        if a is None:break
        out.append(a);pos=pos2
    return out

def clean_question(s):
    s=ID_RE.sub("",s);s=LEVEL_RE.sub("",s);s=DANG_RE.sub("",s)
    s=re.sub(r"^\s*%[^\n]*\n?","",s);s=re.sub(r"\\begin\s*\{ex\}","",s,flags=re.I);s=re.sub(r"\\end\s*\{ex\}","",s,flags=re.I)
    return s.strip()

def extract_solution(block):
    m=LOIGIAI_RE.search(block)
    if not m:return ""
    a,_=brace_arg(block,m.end());return a or ""

def parse_q(block):
    dm=DANG_RE.search(block);dang=dm.group(1).strip() if dm else "Chưa phân dạng";sol=extract_solution(block)
    tf=cmd_args(block,"\\choiceTF")
    if tf:
        arr=[{"text":re.sub(r"^\\True\s*","",x,flags=re.I).strip(),"correct":bool(re.match(r"^\\True\b",x,re.I))} for x in tf]
        return {"dang":dang,"kind":"tf","text":clean_question(TF_RE.split(block,1)[0]),"statements":arr,"solution":sol}
    ch=cmd_args(block,"\\choice")
    if ch:
        arr=[{"text":re.sub(r"^\\True\s*","",x,flags=re.I).strip(),"correct":bool(re.match(r"^\\True\b",x,re.I))} for x in ch[:4]]
        return {"dang":dang,"kind":"choice","text":clean_question(CHOICE_RE.split(block,1)[0]),"options":arr,"solution":sol}
    sm=SHORT_RE.search(block)
    if sm:return {"dang":dang,"kind":"short","text":clean_question(block[:sm.start()]),"answer":sm.group(1).strip(),"solution":sol}
    return {"dang":dang,"kind":"essay","text":clean_question(block),"solution":sol}

def lesson_questions(path):
    _,text=read_tex(path);return [parse_q(b) for b in EX_RE.findall(text)]

def render(title,body):
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"+f"<title>{html.escape(title)}</title><style>{CSS}</style>"+
        "<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre']}};</script>"+
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><div class='topin'><div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div><div class='sub'>GitHub là nguồn chính · ngan-hang/*.tex</div></div><div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"+body+"</body></html>",mimetype="text/html")

def require_member(v):
    @wraps(v)
    def w(*a,**k):
        if session.get("role")!="member" or not current_member():session.clear();return redirect("/member/login")
        return v(*a,**k)
    return w

def require_admin(v):
    @wraps(v)
    def w(*a,**k):
        if session.get("role")!="admin":return redirect("/admin/login")
        return v(*a,**k)
    return w

@app.get("/")
def root():return redirect("/member/login")
@app.get("/github/repo")
def repo_link():return redirect(f"https://github.com/{REPO}")

@app.route("/member/login",methods=["GET","POST"])
def member_login():
    msg=""
    if request.method=="POST":
        u=(request.form.get("username") or "").strip();p=request.form.get("password") or "";h=hashlib.sha256(p.encode()).hexdigest()
        for m in members_data().get("members",[]):
            if m.get("username")==u and m.get("password_sha256")==h and m.get("status","ON")=="ON":session.clear();session.update(role="member",username=u);return redirect("/member")
        msg="Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa."
    return render("Đăng nhập","<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>")

@app.route("/member/register",methods=["GET","POST"])
def member_register():
    msg=""
    if request.method=="POST":
        u=(request.form.get("username") or "").strip();n=(request.form.get("name") or "").strip();p=request.form.get("password") or "";d=members_data()
        if not u or not p:msg="Thiếu tài khoản hoặc mật khẩu."
        elif any(m.get("username")==u for m in d.get("members",[])):msg="Tài khoản đã tồn tại."
        else:
            d.setdefault("members",[]).append({"username":u,"name":n or u,"class":"","account_type":"FREE","status":"ON","password_sha256":hashlib.sha256(p.encode()).hexdigest()})
            try:save_members(d);session.clear();session.update(role="member",username=u);return redirect("/member")
            except Exception as e:msg=str(e)
    return render("Đăng ký","<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký thành viên FREE</div><div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Tạo tài khoản</button> <a class='btn' href='/member/login'>Quay lại</a><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>")

@app.get("/member/logout")
def member_logout():session.clear();return redirect("/member/login")

@app.get("/member")
@require_member
def member_home():
    m=current_member();idx=index_data();groups={}
    for x in idx.get("lessons",[]):
        if not isinstance(x,dict):continue
        p=str(x.get("path") or "")
        if safe_tex(p):groups.setdefault((str(x.get("Mon") or "Khác"),str(x.get("Lop") or ""),str(x.get("Chuong") or "Chưa xác định")),[]).append(x)
    blocks=[]
    for (sub,cls,ch),items in sorted(groups.items()):
        cards=[]
        for x in items:
            p=str(x.get("path"));title=str(x.get("BaiHoc") or x.get("De") or Path(p).parent.name);cnt=int(x.get("questions") or x.get("count") or 0);dgs=x.get("dang") or {};level=lesson_level(p);ok=allowed(m,p)
            chips="".join(f"<div class='dangrow'><span>{html.escape(str(k))}</span><span class='tag'>{int(v)} câu</span></div>" for k,v in dgs.items())
            action=f"<a class='btn primary' href='/member/lesson?path={urllib.parse.quote(p,safe='')}'>Mở bài</a>" if ok else "<span class='pill vip'>🔒 Chỉ VIP</span>"
            cards.append("<div class='lesson'><h3>"+html.escape(title)+"</h3><div class='sub'>"+html.escape(sub)+" · Lớp "+html.escape(cls)+"</div><div class='row'><span class='pill "+("vip" if level=="VIP" else "free")+"'>"+level+"</span><span class='pill'>"+str(cnt)+" câu</span></div><div class='dangbox'><b>📌 Dạng bài tập</b>"+chips+"</div><div class='row' style='margin-top:7px'>"+action+"</div></div>")
        blocks.append("<div class='subjectbar'>"+html.escape(sub)+" · Lớp "+html.escape(cls)+"</div><div class='chapter'><div class='chaptertitle'>"+html.escape(ch)+"</div><div class='lessons'>"+''.join(cards)+"</div></div>")
    badge="VIP — xem và làm FREE + VIP" if is_vip(m) else "FREE — chỉ xem và làm FREE"
    body="<div class='wrap'><div class='notice'><b>👤 "+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản: <b>"+html.escape(str(m.get('username')))+"</b> · Quyền: <b>"+badge+"</b> · <a href='/member/logout'>Đăng xuất</a></div><div class='panel'><div class='mh'><span>📚 Mục lục học tập</span><span>"+str(int(idx.get('total_files') or 0))+" bài · "+str(int(idx.get('total_questions') or 0))+" câu</span></div><div class='body'>"+''.join(blocks)+"</div></div></div>"
    return render("Thành viên",body)

@app.get("/member/lesson")
@require_member
def member_lesson():
    m=current_member();p=request.args.get("path","")
    if not allowed(m,p):return render("Bài VIP","<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho thành viên VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    try:qs=lesson_questions(p)
    except Exception as e:return render("Lỗi",f"<div class='wrap err'>{html.escape(str(e))}</div>")
    payload=json.dumps(qs,ensure_ascii=False)
    qtypes={"choice":"① Trắc nghiệm 4 lựa chọn","tf":"② Đúng / Sai","short":"③ Trả lời ngắn","essay":"④ Tự luận"}
    counts={k:sum(1 for q in qs if q.get('kind')==k) for k in qtypes}
    dcounts={}
    for q in qs:dcounts[q.get('dang','Chưa phân dạng')]=dcounts.get(q.get('dang','Chưa phân dạng'),0)+1
    chips=''.join(f"<span class='pill'>{html.escape(str(k))} · {int(v)} câu</span> " for k,v in dcounts.items())
    buttons="<button class='typebtn' onclick=\"setType('all')\">Tất cả · "+str(len(qs))+"</button>"+''.join(f"<button class='typebtn' onclick=\"setType('{k}')\">{v} · {counts[k]}</button>" for k,v in qtypes.items())
    body="<div class='wrap'><div class='qwrap'><div class='panel'><div class='mh'><span>📖 "+html.escape(Path(p).parent.name)+" · Tài khoản: "+html.escape(str(m.get('username')))+" · "+("VIP" if is_vip(m) else "FREE")+"</span><a class='btn' href='/member'>← Bài học</a></div><div class='body'><div class='notice'><b>📌 Dạng bài tập trong bài:</b> "+chips+"</div><div class='quizgrid'>"+buttons+"</div><div id='quiz'></div></div></div></div></div>"
    js=r"""
const DATA=__DATA__, TYPES=__TYPES__; let filter='all',items=[],pos=0,score=0,reviewable=[];
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function setType(t){filter=t;items=DATA.map((q,i)=>({q,i})).filter(x=>t==='all'||x.q.kind===t).map(x=>x.i);pos=0;score=0;reviewable=[];renderQ()}
function renderQ(){
 if(!items.length){document.getElementById('quiz').innerHTML='<div class="notice">Không có câu thuộc dạng này.</div>';return}
 const q=DATA[items[pos]],n=items.length;let h='<div class="row" style="justify-content:space-between;margin:10px 0"><span><b>Câu '+(pos+1)+'/'+n+'</b> · '+esc(q.dang||'Chưa phân dạng')+'</span><span class="tag">Đúng: '+score+'</span></div>';
 h+='<div class="qcard"><div class="qtext">'+esc(q.text)+'</div>';
 if(q.kind==='choice')q.options.forEach((o,i)=>h+='<label class="opt" id="o'+i+'"><input type="radio" name="ans" value="'+i+'"> <b>'+String.fromCharCode(65+i)+'.</b> '+esc(o.text)+'</label>');
 else if(q.kind==='tf')q.statements.forEach((s,j)=>h+='<div class="tfrow" id="tf'+j+'">'+(j+1)+'. '+esc(s.text)+'<div><label><input type="radio" name="tf'+j+'" value="1"> Đúng</label> &nbsp; <label><input type="radio" name="tf'+j+'" value="0"> Sai</label></div></div>');
 else if(q.kind==='short')h+='<input id="short" class="shortinput" placeholder="Nhập đáp án">';
 else h+='<textarea id="essay" class="shortinput" style="height:150px" placeholder="Nhập bài làm"></textarea>';
 h+='<div class="row" style="margin-top:12px"><button class="btn primary" onclick="checkQ()">✅ Chọn / kiểm tra</button><button class="btn" onclick="nextQ()">→ Câu tiếp</button></div><div id="res"></div></div>';document.getElementById('quiz').innerHTML=h;if(window.MathJax)MathJax.typesetPromise();}
function checkQ(){
 const q=DATA[items[pos]],res=document.getElementById('res');if(res.dataset.done==='1')return;let ok=false,student='';
 if(q.kind==='choice'){const e=document.querySelector('input[name=ans]:checked');if(!e){alert('Hãy chọn đáp án.');return}const i=Number(e.value);student=String.fromCharCode(65+i);q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')});ok=q.options[i].correct}
 else if(q.kind==='tf'){let all=true;for(let j=0;j<q.statements.length;j++)if(!document.querySelector('input[name=tf'+j+']:checked'))all=false;if(!all){alert('Hãy chọn Đúng/Sai cho tất cả ý.');return}let a=[];q.statements.forEach((s,j)=>{const e=document.querySelector('input[name=tf'+j+']:checked');const v=e.value==='1';a.push(v?'Đ':'S');const el=document.getElementById('tf'+j);if(v===s.correct)el.classList.add('correct');else el.classList.add('wrong')});student=a.join('');ok=q.statements.every((s,j)=>(document.querySelector('input[name=tf'+j+']:checked').value==='1')===s.correct)}
 else if(q.kind==='short'){const e=document.getElementById('short');if(!e.value.trim()){alert('Nhập đáp án.');return}student=e.value.trim();ok=student.toLowerCase()===String(q.answer||'').trim().toLowerCase();res.innerHTML='<div class="'+(ok?'result':'notice')+'">'+(ok?'✅ Đúng':'❌ Sai')+' · Đáp án: <b>'+esc(q.answer||'')+'</b></div>'}
 else {student=document.getElementById('essay')?.value||'';res.innerHTML='<div class="notice">Đã ghi nhận bài tự luận. Có thể chọn câu này để Gemini phản biện.</div>'}
 if(q.kind!=='short'&&q.kind!=='essay')res.innerHTML='<div class="'+(ok?'result':'notice')+'">'+(ok?'✅ Đúng':'❌ Sai')+'</div>';if(ok)score++;res.dataset.done='1';reviewable.push({idx:items[pos],student});
}
function nextQ(){if(pos<items.length-1){pos++;renderQ()}else{let opts=reviewable.map((x,i)=>'<option value="'+x.idx+'">Câu '+(DATA.slice(0,x.idx).filter(()=>true).length+1)+' — '+esc(DATA[x.idx].text.slice(0,100))+'</option>').join('');document.getElementById('quiz').innerHTML='<div class="result">🎉 Hoàn thành · Đúng <b>'+score+'/'+items.length+'</b><div class="row" style="margin-top:9px"><button class="btn warn" onclick="reviewPick()">🤖 Chọn 1 câu để Gemini phản biện</button> <button class="btn" onclick="setType(filter)">Làm lại</button></div><div id="reviewbox"></div></div>';window._reviewOpts=opts}}
function reviewPick(){document.getElementById('reviewbox').innerHTML='<div class="review"><b>Chọn 1 câu cần phản biện:</b><select id="reviewSel" style="padding:7px;margin:6px">'+(window._reviewOpts||'')+'</select><button class="btn primary" onclick="sendReview()">🤖 Gemini phản biện</button><div id="reviewout"></div></div>'}
async function sendReview(){const idx=Number(document.getElementById('reviewSel').value),q=DATA[idx],rinfo=reviewable.find(x=>x.idx===idx)||{};const out=document.getElementById('reviewout');out.textContent='⏳ Gemini đang phân tích câu đã chọn...';try{const r=await fetch('/api/gemini/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,student_answer:rinfo.student||''})});const d=await r.json();out.innerHTML=d.ok?'<div class="review">'+esc(d.text).replace(/\n/g,'<br>')+'</div>':'<div class="err">'+esc(d.error||'Gemini không phản hồi')+'</div>'}catch(e){out.innerHTML='<div class="err">Gemini lỗi: '+esc(e)+'</div>'}}
setType('all');
"""
    return render("Làm bài",body+"<script>"+js.replace("__DATA__",payload).replace("__TYPES__",json.dumps(qtypes,ensure_ascii=False))+"</script>")

@app.post("/api/gemini/review")
@require_member
def gemini_review():
    if not GEMINI_API_KEY:return jsonify(ok=False,error="Chưa cấu hình GEMINI_API_KEY trên Render."),400
    d=request.get_json(silent=True) or {};q=d.get('question') or {};student=d.get('student_answer','')
    prompt=("Bạn là trợ lý phản biện cho học sinh THPT. Chỉ phản biện DUY NHẤT câu được gửi, không phân tích các câu khác. "
            "Hãy nêu rõ: học sinh đã trả lời gì; đúng hay sai; vì sao; lỗi dễ nhầm; cách làm đúng ngắn gọn từng bước. "
            "Giữ công thức bằng LaTeX. Không bịa dữ kiện và không thay đổi đề bài.\n\n"
            f"CÂU HỎI:\n{q.get('text','')}\nLOẠI: {q.get('kind','')}\n"
            f"TRẢ LỜI CỦA HỌC SINH:\n{student}\nĐÁP ÁN CHUẨN:\n{json.dumps(q.get('options') or q.get('statements') or q.get('answer') or '',ensure_ascii=False)}\n"
            f"LỜI GIẢI GỐC:\n{q.get('solution','')}")
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(GEMINI_MODEL,safe='')}:generateContent?key={urllib.parse.quote(GEMINI_API_KEY,safe='')}"
    try:
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]},ensure_ascii=False).encode(),method='POST',headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=45) as r:res=json.loads(r.read().decode())
        text=res['candidates'][0]['content']['parts'][0]['text'];return jsonify(ok=True,text=text)
    except Exception as e:return jsonify(ok=False,error=str(e)),500

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    msg=""
    if request.method=="POST":
        u=(request.form.get('username') or '').strip();p=request.form.get('password') or ''
        if u==ADMIN_USERNAME and ADMIN_PASSWORD and p==ADMIN_PASSWORD:session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    return render('ADMIN',"<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='ADMIN' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Đăng nhập</button><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>")

@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')

@app.get('/admin')
@require_admin
def admin_home():
    d=members_data();rows=[]
    for m in d.get('members',[]):
        typ=account_type(m); rows.append("<tr><td>"+html.escape(str(m.get('username','')))+"</td><td>"+html.escape(str(m.get('name','')))+"</td><td>"+html.escape(str(m.get('class','')))+"</td><td><form method='post' action='/admin/member/type'><input type='hidden' name='username' value='"+html.escape(str(m.get('username','')),quote=True)+"'><select name='account_type'><option "+('selected' if typ=='FREE' else '')+">FREE</option><option "+('selected' if typ=='VIP' else '')+">VIP</option></select><button class='btn'>Lưu quyền</button></form></td><td>"+html.escape(str(m.get('status','ON')))+"</td></tr>")
    body="<div class='wrap'><div class='layout'><aside class='panel'><div class='head'>⚙️ ADMIN</div><div class='body'><a class='btn' href='/admin'>👥 Thành viên</a> <a class='btn' href='/admin/access'>🔐 Quyền bài</a> <a class='btn' href='/github/quan-ly'>📚 Ngân hàng .tex</a> <a class='btn' href='/admin/logout'>Thoát</a></div></aside><main class='panel'><div class='mh'>👥 Danh sách thành viên</div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th></tr>"+''.join(rows)+"</table></div></main></div></div>"
    return render('Quản trị',body)

@app.post('/admin/member/type')
@require_admin
def admin_member_type():
    u=request.form.get('username','');typ='VIP' if (request.form.get('account_type') or 'FREE').upper()=='VIP' else 'FREE';d=members_data()
    for m in d.get('members',[]):
        if m.get('username')==u:m['account_type']=typ;break
    save_members(d);return redirect('/admin')

@app.get('/admin/access')
@require_admin
def admin_access():
    idx=index_data();a=access_data();cards=[]
    for x in idx.get('lessons',[]):
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '')
        if not safe_tex(p):continue
        lev=lesson_level(p);title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name)
        cards.append("<div class='lesson'><b>"+html.escape(title)+"</b><div class='sub'>"+html.escape(p)+"</div><form method='post' action='/admin/access/save' class='row' style='margin-top:6px'><input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'><select name='level'><option "+('selected' if lev=='FREE' else '')+">FREE</option><option "+('selected' if lev=='VIP' else '')+">VIP</option></select><button class='btn'>Lưu</button><span class='pill "+('vip' if lev=='VIP' else 'free')+"'>"+lev+"</span></form></div>")
    return render('Quyền bài',"<div class='wrap'><div class='panel'><div class='mh'>🔐 Phân quyền bài học FREE / VIP <a class='btn' href='/admin'>← ADMIN</a></div><div class='cards'>"+''.join(cards)+"</div></div></div>")

@app.post('/admin/access/save')
@require_admin
def admin_access_save():
    p=request.form.get('path','');lev='VIP' if (request.form.get('level') or 'FREE').upper()=='VIP' else 'FREE'
    if not safe_tex(p):return 'bad path',400
    d=access_data();d.setdefault('lessons',{})[p]=lev;save_access(d);return redirect('/admin/access')

@app.get('/github/quan-ly')
@require_admin
def github_manage():
    idx=index_data();cards=[]
    for x in idx.get('lessons',[]):
        p=str(x.get('path') or '')
        if not safe_tex(p):continue
        title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name);dgs=x.get('dang') or {}
        chips=''.join(f"<span class='pill'>{html.escape(str(k))} · {int(v)}</span> " for k,v in dgs.items())
        cards.append("<div class='lesson'><h3>"+html.escape(title)+"</h3><div class='sub'>"+html.escape(p)+"</div><div class='row' style='margin:5px 0'>"+chips+"</div><a class='btn primary' href='/admin/edit?path="+urllib.parse.quote(p,safe='')+"'>✏️ Đọc / sửa .tex</a></div>")
    return render('Ngân hàng GitHub',"<div class='wrap'><div class='panel'><div class='mh'>📚 Mục lục GitHub <span>"+str(int(idx.get('total_files') or 0))+" bài · "+str(int(idx.get('total_questions') or 0))+" câu</span></div><div class='cards'>"+''.join(cards)+"</div></div></div>")

@app.get('/admin/edit')
@require_admin
def admin_edit():
    p=request.args.get('path','')
    try:sha,text=read_tex(p)
    except Exception as e:return render('Lỗi',f"<div class='wrap err'>{html.escape(str(e))}</div>")
    body="<div class='wrap'><div class='panel'><div class='mh'>✏️ "+html.escape(p)+" <a class='btn' href='/github/quan-ly'>← Mục lục</a></div><div class='body'><textarea id='code' class='code'>"+html.escape(text)+"</textarea><div class='row' style='margin-top:8px'><button class='btn primary' onclick='saveTex()'>💾 Lưu trực tiếp GitHub</button><a class='btn' target='_blank' href='https://github.com/"+html.escape(REPO)+"/blob/"+urllib.parse.quote(BRANCH)+"/"+urllib.parse.quote(p,safe='/')+"'>🐙 Mở GitHub</a><span id='msg'></span></div></div></div></div>"
    js="const P="+json.dumps(p,ensure_ascii=False)+",S="+json.dumps(sha)+";async function saveTex(){const m=document.getElementById('msg');m.textContent='⏳ Đang lưu...';try{const r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:P,sha:S,text:document.getElementById('code').value})});const d=await r.json();m.textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+(d.error||'Lỗi')}catch(e){m.textContent='❌ '+e}}"
    return render('Sửa .tex',body+'<script>'+js+'</script>')

@app.post('/admin/api/save')
@require_admin
def admin_save():
    d=request.get_json(silent=True) or {};p=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not safe_tex(p) or not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu dữ liệu'),400
    try:r=gh_put(p,text,'ADMIN cập nhật .tex trực tiếp',sha);return jsonify(ok=True,commit=str((r.get('commit') or {}).get('sha') or '')[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
