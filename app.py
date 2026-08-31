# -*- coding: utf-8 -*-
"""Stable GitHub-only question bank portal."""
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
ADMIN_USERNAME = (os.getenv("ADMIN_USERNAME") or "ADMIN").strip() or "ADMIN"
ADMIN_PASSWORD = (os.getenv("ADMIN_PASSWORD") or "").strip()

ROOT = Path(__file__).resolve().parent
INDEX_FILE = ROOT / "bank_index.json"
MEMBERS_FILE = ROOT / "members.json"
ACCESS_FILE = ROOT / "lesson_access.json"

EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}", re.I)
DANG_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)
LEVEL_RE = re.compile(r"%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\r\n%]+)", re.I)
SHORT_RE = re.compile(r"\\shortans\s*\{([^{}]*)\}", re.I)

CSS = r"""
*{box-sizing:border-box}body{margin:0;background:#f3f7fb;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#1769d2;color:#fff}.topin{max-width:1500px;margin:auto;padding:10px 16px;display:flex;align-items:center;gap:14px}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b9d5f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer}.nav a{background:#ffffff18;color:#fff;border-color:#ffffff55}.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid #cfdae5;border-radius:11px;overflow:hidden}.head,.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.mh{display:flex;justify-content:space-between;align-items:center;gap:10px}.body{padding:10px}.notice,.bar{padding:9px;border:1px solid #abd7b4;background:#f0fbf2;border-radius:8px}.err{color:#b42318;font-weight:800}.muted{color:#64748b}.login{max-width:430px;margin:60px auto}.field{margin-bottom:9px}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:7px}.layout{display:grid;grid-template-columns:300px 1fr;gap:10px}.tree{max-height:78vh;overflow:auto}.tree details{border-bottom:1px solid #e8eef5}.tree summary{cursor:pointer;padding:7px 4px;font-weight:800;list-style:none}.tree summary:before{content:'▶ ';font-size:10px}.tree details[open]>summary:before{content:'▼ '}.tree summary::-webkit-details-marker{display:none}.tree a{display:block;padding:6px 9px;color:#155da8;text-decoration:none;border-radius:6px}.tree a:hover{background:#eef6ff}.titlebar{padding:10px 12px;background:linear-gradient(90deg,#1b5ed2,#5a9ce9);color:#fff;border-radius:9px;font-weight:900}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px}.card{border:1px solid #d9e3ed;border-radius:10px;padding:10px;background:#fff}.tag{display:inline-block;padding:3px 8px;border:1px solid #cbd5e1;border-radius:999px;font-size:11px;margin:2px}.free{border-color:#86d8a2;background:#effcf3;color:#15733b}.vip{border-color:#f2a5cd;background:#fff0f8;color:#9b175f}.dangbox{margin:8px 0;border:1px solid #d9e6f2;border-radius:8px;padding:7px;background:#fafcff}.dangrow{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid #edf2f7}.dangrow:last-child{border-bottom:0}.selectgrid{width:100%;border-collapse:collapse;font-size:12px}.selectgrid th,.selectgrid td{border:1px solid #dfe7ef;padding:6px}.selectgrid th{background:#eaf3ff;text-align:center}.selectgrid td:first-child{font-weight:800}.n{width:52px;padding:5px;border:1px solid #cbd5e1;border-radius:6px}.qtext{font-size:18px;line-height:1.7;margin-bottom:8px}.opt,.tf{display:block;border:2px solid #d8e5f1;border-radius:9px;padding:10px;margin:7px 0;cursor:pointer}.correct{background:#e8f8ee!important;border-color:#3aaa66!important}.wrong{background:#fff0f1!important;border-color:#e34a52!important}.answerbox{width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:7px}.result{padding:10px;border-radius:8px;margin-top:10px;font-weight:900}.good{background:#eaf8ef;border:1px solid #8bd2a1;color:#126b34}.bad{background:#fff0f1;border:1px solid #eea0a4;color:#a51c24}.review{margin-top:10px;padding:10px;border:1px solid #c9b9f2;border-radius:8px;background:#faf8ff;white-space:pre-wrap}.code{width:100%;height:70vh;font:12px/1.5 Consolas,monospace;border:1px solid #cbd5e1;border-radius:8px;padding:10px}.table{width:100%;border-collapse:collapse}.table th,.table td{border:1px solid #dfe7ef;padding:6px}.table th{background:#f5f8fc}@media(max-width:900px){.layout{grid-template-columns:1fr}.tree{max-height:40vh}.cards{grid-template-columns:1fr}}
"""


def page(title: str, body: str) -> Response:
    return Response(
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style>"
        "<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre']}};</script>"
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>"
        "</head><body><div class='top'><div class='topin'><div>"
        "<div class='brand'>📚 Ngân hàng câu hỏi GitHub</div>"
        "<div class='sub'>Nguồn chính: bank_index.json + ngan-hang/*.tex</div></div>"
        "<div class='nav'><a href='/member'>📚 Mục lục</a><a href='/admin/login'>🔐 ADMIN</a>"
        f"<a href='https://github.com/{html.escape(REPO)}' target='_blank'>🐙 GitHub</a></div></div></div>{body}</body></html>",
        mimetype="text/html",
    )


def local_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def index_data():
    return local_json(INDEX_FILE, {"total_files": 0, "total_questions": 0, "lessons": []})


def members_data():
    return local_json(MEMBERS_FILE, {"members": []})


def access_data():
    d = local_json(ACCESS_FILE, {"default": "FREE", "lessons": {}})
    d.setdefault("default", "FREE"); d.setdefault("lessons", {})
    return d


def member_now():
    u = session.get("username")
    if not u or session.get("role") != "member": return None
    for m in members_data().get("members", []):
        if m.get("username") == u and m.get("status", "ON") == "ON": return m
    return None


def vip(m):
    return str(m.get("account_type", "FREE")).upper() in {"VIP", "S.VIP", "ADMIN"}


def lesson_access(path):
    d = access_data(); return str(d.get("lessons", {}).get(path, d.get("default", "FREE"))).upper()


def can_open(m, path):
    return lesson_access(path) == "FREE" or vip(m)


def gh(path, method="GET", data=None):
    if not TOKEN: raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    owner, repo = REPO.split("/", 1)
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/{path.lstrip('/')}",
        data=body, method=method,
        headers={"Authorization": "Bearer "+TOKEN, "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent":"ldvl-stable"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        t=e.read().decode("utf-8","replace")
        try: msg=json.loads(t).get("message",t)
        except Exception: msg=t
        raise RuntimeError(f"GitHub API {e.code}: {msg}")


def read_tex(path):
    if not (path.startswith("ngan-hang/") and path.lower().endswith(".tex") and ".." not in path):
        raise ValueError("Đường dẫn file .tex không hợp lệ")
    d=gh(f"contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(BRANCH)}")
    text=base64.b64decode((d.get("content") or "").replace("\n","")).decode("utf-8","replace")
    return d.get("sha",""), text


def split_args(text, command):
    m=re.search(re.escape(command)+r"\b",text,re.I)
    if not m: return []
    out=[]; p=m.end()
    while p<len(text):
        while p<len(text) and text[p].isspace(): p+=1
        if p>=len(text) or text[p]!="{": break
        start=p+1; depth=1; p+=1
        while p<len(text) and depth:
            if text[p]=='{' and text[p-1]!='\\': depth+=1
            elif text[p]=='}' and text[p-1]!='\\': depth-=1
            p+=1
        if depth: break
        out.append(text[start:p-1])
    return out


def clean_text(s):
    s=re.sub(r"\\dangbt\s*\{[^{}]*\}","",s,flags=re.I)
    s=re.sub(r"%\s*(?:Mức|Muc|Muc do)\s*:\s*[^\r\n%]+","",s,flags=re.I)
    s=re.sub(r"\\vspace\s*\{[^{}]*\}","",s,flags=re.I)
    return s.strip()


def parse_questions(tex):
    result=[]
    for idx,b in enumerate(EX_RE.findall(tex)):
        dm=DANG_RE.search(b); lm=LEVEL_RE.search(b)
        dang=dm.group(1).strip() if dm else "Chưa phân dạng"
        level=(lm.group(1).strip().upper()[:2] if lm else "H").replace("NB","N").replace("TH","H").replace("VD","V")
        level=level[-1] if level[-1:] in "NHVC" else "H"
        if re.search(r"\\choiceTF\b",b,re.I): kind="DS"
        elif re.search(r"\\choice\b",b,re.I): kind="TN"
        elif SHORT_RE.search(b): kind="TLN"
        else: kind="TL"
        q={"idx":idx,"dang":dang,"level":level,"kind":kind,"raw":b}
        if kind=="TN":
            a=split_args(b,"\\choice"); q["options"]=[]
            for x in a[:4]: q["options"].append({"text":re.sub(r"^\\True\s*","",x,flags=re.I).strip(),"correct":bool(re.match(r"^\\True\b",x,re.I))})
            q["text"]=clean_text(re.split(r"\\choice\b",b,1,flags=re.I)[0])
        elif kind=="DS":
            a=split_args(b,"\\choiceTF"); q["statements"]=[]
            for x in a: q["statements"].append({"text":re.sub(r"^\\True\s*","",x,flags=re.I).strip(),"correct":bool(re.match(r"^\\True\b",x,re.I))})
            q["text"]=clean_text(re.split(r"\\choiceTF\b",b,1,flags=re.I)[0])
        elif kind=="TLN":
            sm=SHORT_RE.search(b); q["answer"]=sm.group(1).strip() if sm else ""; q["text"]=clean_text(b[:sm.start()] if sm else b)
        else:
            q["text"]=clean_text(b)
        result.append(q)
    return result


@app.get("/health")
def health():
    return jsonify(ok=True, app="github-bank", repo=REPO, branch=BRANCH)


@app.get("/")
def root():
    return redirect("/member")


@app.get("/github/repo")
def github_repo():
    return redirect(f"https://github.com/{REPO}")


@app.route("/member/login", methods=["GET","POST"])
def member_login():
    msg=""
    if request.method=="POST":
        u=request.form.get("username","").strip(); p=request.form.get("password",""); h=hashlib.sha256(p.encode()).hexdigest()
        for m in members_data().get("members",[]):
            if m.get("username")==u and m.get("password_sha256")==h and m.get("status","ON")=="ON":
                session.clear(); session.update(role="member",username=u); return redirect("/member")
        msg="Sai tài khoản hoặc mật khẩu."
    body=f"<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button> <a class='btn' href='/admin/login'>ADMIN</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>"
    return page("Đăng nhập",body)


@app.get("/member/logout")
def member_logout(): session.clear(); return redirect("/member/login")


@app.get("/member")
def member_home():
    m=member_now()
    if not m: return redirect("/member/login")
    d=index_data(); groups={}
    for x in d.get("lessons",[]):
        if not isinstance(x,dict): continue
        p=str(x.get("path") or x.get("file") or "")
        if not p.lower().endswith('.tex'): continue
        key=(str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or 'Chưa xác định'))
        groups.setdefault(key,[]).append(x)
    left=[]; cards=[]
    for (mon,lop,chuong),items in sorted(groups.items()):
        links=''.join(f"<a href='/member/select?path={urllib.parse.quote(str(x.get('path')),safe='')}'>{html.escape(str(x.get('BaiHoc') or x.get('De') or Path(str(x.get('path'))).parent.name))}</a>" for x in items)
        left.append(f"<details><summary>📘 {html.escape(mon)} · Lớp {html.escape(lop)} · {html.escape(chuong)}</summary>{links}</details>")
        for x in items:
            p=str(x.get('path')); title=str(x.get('BaiHoc') or x.get('De') or Path(p).parent.name); lv=lesson_access(p); count=int(x.get('questions') or x.get('count') or 0); dgs=x.get('dang') or {}
            rows=''.join(f"<div class='dangrow'><span>{html.escape(str(k))}</span><span class='tag'>{int(v)} câu</span></div>" for k,v in dgs.items())
            cards.append(f"<div class='card'><b>{html.escape(title)}</b><div class='muted'>{html.escape(mon)} · Lớp {html.escape(lop)} · {html.escape(chuong)}</div><div><span class='tag {'vip' if lv=='VIP' else 'free'}'>{lv}</span><span class='tag'>{count} câu</span></div><div class='dangbox'>{rows}</div><a class='btn' href='/member/select?path={urllib.parse.quote(p,safe='')}'>Chọn dạng / số câu</a></div>")
    role="VIP · FREE + VIP" if vip(m) else "FREE · chỉ FREE"
    body=f"<div class='wrap'><div class='notice'>👤 <b>{html.escape(str(m.get('name') or m.get('username')))}</b> · Tài khoản: <b>{html.escape(str(m.get('username')))}</b> · Quyền: <b>{role}</b> · <a href='/member/logout'>Đăng xuất</a></div><div class='layout' style='margin-top:10px'><aside class='panel'><div class='head'>🌳 Cấu trúc ngân hàng</div><div class='body tree'>{''.join(left)}</div></aside><main class='panel'><div class='mh'><span>📚 Mục lục</span><span>{int(d.get('total_files') or 0)} bài · {int(d.get('total_questions') or 0)} câu</span></div><div class='body'><div class='cards'>{''.join(cards)}</div></div></main></div></div>"
    return page("Mục lục",body)


@app.get("/member/select")
def select_lesson():
    m=member_now()
    if not m:return redirect('/member/login')
    path=request.args.get('path',''); ok,lv=can_open(m,path),lesson_access(path)
    if not ok:return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    try: _,tex=read_tex(path); qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(e))}</div></div></div></div>")
    groups={}
    for q in qs: groups.setdefault(q['dang'],[]).append(q)
    rows=[]
    for dang,arr in groups.items():
        first=True
        for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
            c={z:sum(1 for q in arr if q['kind']==kind and q['level']==z) for z in 'NHVC'}; total=sum(c.values())
            inputs=''.join(f"<input class='n' type='number' min='0' max='{c[z]}' value='0' name='n_{re.sub(r'[^A-Za-z0-9]','_',dang)}_{kind}_{z}'>" for z in 'NHVC')
            rows.append(f"<tr><td>{html.escape(dang) if first else ''}</td><td><b>{label}</b></td><td>{c['N']}/{c['H']}/{c['V']}/{c['C']}</td><td>{inputs}</td><td><b>{total}</b></td></tr>"); first=False
    body=f"<div class='wrap'><div class='panel'><div class='mh'><span>🧩 Chọn dạng bài · {html.escape(Path(path).parent.name)}</span><span>{len(qs)} câu · {lv}</span></div><div class='body'><form method='post' action='/member/start'><input type='hidden' name='path' value='{html.escape(path,quote=True)}'><table class='selectgrid'><tr><th>Dạng bài tập</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>{''.join(rows)}</table><div id='sum' class='bar' style='margin:9px 0'>TỔNG CHỌN: 0 câu</div><button class='btn'>▶ Tạo bài luyện tập</button> <a class='btn' href='/member'>← Mục lục</a></form></div></div></div><script>function r(){{let t=0;document.querySelectorAll('.n').forEach(x=>{{let m=+x.max||0;let v=Math.max(0,Math.min(m,+x.value||0));x.value=v;t+=v}});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu'}}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',r));r();</script>"
    return page('Chọn dạng bài',body)


@app.post('/member/start')
def start_quiz():
    m=member_now();
    if not m:return redirect('/member/login')
    path=request.form.get('path','')
    if not can_open(m,path):return redirect('/member')
    try:_,tex=read_tex(path);qs=parse_questions(tex)
    except Exception:return redirect('/member')
    need={}
    for k,v in request.form.items():
        if not k.startswith('n_'):continue
        try:v=max(0,int(v or 0))
        except Exception:v=0
        if v<=0:continue
        p=k.split('_'); need[('_'.join(p[1:-2]),p[-2],p[-1])]=v
    chosen=[]
    for q in qs:
        key=(re.sub(r'[^A-Za-z0-9]','_',q['dang']),q['kind'],q['level'])
        if need.get(key,0)>0: chosen.append(q['idx']); need[key]-=1
    if not chosen:return redirect('/member/select?path='+urllib.parse.quote(path,safe=''))
    random.shuffle(chosen);session['quiz_path']=path;session['quiz_ids']=chosen;session['quiz_pos']=0;session['quiz_right']=0;session['quiz_answers']=[];return redirect('/member/quiz')


@app.get('/member/quiz')
def quiz():
    m=member_now();
    if not m:return redirect('/member/login')
    path=session.get('quiz_path','');ids=list(session.get('quiz_ids') or []);pos=int(session.get('quiz_pos') or 0);right=int(session.get('quiz_right') or 0);answers=list(session.get('quiz_answers') or [])
    if not path or not ids:return redirect('/member')
    try:_,tex=read_tex(path);allq=parse_questions(tex);by={q['idx']:q for q in allq};qs=[by[i] for i in ids if i in by]
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(e))}</div></div></div></div>")
    if pos>=len(qs):
        total=len(qs);score=(right/total*10 if total else 0); body=f"<div class='wrap'><div class='panel'><div class='mh'>🎉 Kết quả</div><div class='body'><div class='notice'>Đúng <b>{right}/{total}</b> · Điểm <b>{score:.2f}/10</b></div><p>Chọn một câu để xem lại:</p><form method='get' action='/member/review'><select name='i'>{''.join(f'<option value="{i}">Câu {i+1}</option>' for i in range(len(answers)))}</select> <button class='btn'>🤖 Xem phản biện</button></form><a class='btn' href='/member'>← Mục lục</a></div></div></div>";return page('Kết quả',body)
    q=qs[pos]; raw=q['raw']; text=q['text']
    if q['kind']=='TN':
        opts=''.join(f"<label class='opt' id='o{i}'><input type='radio' name='a' value='{i}'> <b>{chr(65+i)}.</b> {html.escape(o['text'])}</label>" for i,o in enumerate(q['options']))
    elif q['kind']=='DS':
        opts=''.join(f"<div class='tf' id='t{i}'><b>{i+1}.</b> {html.escape(s['text'])}<div><label><input type='radio' name='t{i}' value='1'> Đúng</label> <label><input type='radio' name='t{i}' value='0'> Sai</label></div></div>" for i,s in enumerate(q['statements']))
    elif q['kind']=='TLN':opts="<input class='answerbox' id='ans' placeholder='Nhập đáp án'>"
    else:opts="<textarea class='answerbox' id='ans' rows='8' placeholder='Nhập bài tự luận'></textarea>"
    data=json.dumps(q,ensure_ascii=False)
    body=f"<div class='wrap'><div class='panel'><div class='mh'><span>📝 Câu {pos+1}/{len(qs)} · {html.escape(q['dang'])}</span><span>Đúng {right}</span></div><div class='body'><div class='qtext'><b>Câu {pos+1}.</b> {html.escape(text)}</div>{opts}<div style='margin-top:10px'><button id='check' class='btn'>✅ Kiểm tra</button></div><div id='res'></div></div></div></div>"
    js=f"""
const Q={data};let checked=false;function ts(){{if(window.MathJax)MathJax.typesetPromise()}}function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;')}}document.getElementById('check').onclick=async()=>{{if(checked)return;let ok=false,student='';if(Q.kind==='TN'){{let e=document.querySelector('input[name=a]:checked');if(!e)return alert('Hãy chọn đáp án.');let i=+e.value;student=String.fromCharCode(65+i);Q.options.forEach((o,j)=>{{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')}});ok=Q.options[i].correct}}else if(Q.kind==='DS'){{let arr=[];for(let i=0;i<Q.statements.length;i++){{let e=document.querySelector('input[name=t'+i+']:checked');if(!e)return alert('Chọn Đúng/Sai đủ các ý.');let v=e.value==='1';arr.push(v?'Đ':'S');document.getElementById('t'+i).classList.add(v===Q.statements[i].correct?'correct':'wrong')}}student=arr.join('');ok=Q.statements.every((s,i)=>(document.querySelector('input[name=t'+i+']:checked').value==='1')===s.correct)}}else{{let e=document.getElementById('ans');if(!e||!e.value.trim())return alert('Hãy nhập đáp án.');student=e.value.trim();ok=Q.kind==='TLN' && student.toLowerCase()===String(Q.answer||'').trim().toLowerCase()}}document.querySelectorAll('input,textarea').forEach(x=>x.disabled=true);document.getElementById('res').innerHTML='<div class=\"result '+(ok?'good':'bad')+'\">'+(ok?'✅ ĐÚNG':'❌ SAI')+'</div><div style=\"margin-top:8px\"><a class=\"btn\" href=\"/member/quiz/next\">→ Câu tiếp</a></div>';checked=true;fetch('/member/answer',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{ok:ok,student:student,index:Q.idx}})}}).catch(()=>{{}});ts()}};ts();
"""
    return page('Làm bài',body+f"<script>{js}</script>")


@app.post('/member/answer')
def save_answer():
    if not member_now():return jsonify(ok=False),401
    d=request.get_json(silent=True) or {};ok=bool(d.get('ok'));a=list(session.get('quiz_answers') or []);a.append({'index':d.get('index'),'student':d.get('student',''),'ok':ok});session['quiz_answers']=a
    if ok:session['quiz_right']=int(session.get('quiz_right') or 0)+1
    return jsonify(ok=True)


@app.get('/member/quiz/next')
def next_question():
    if not member_now():return redirect('/member/login')
    session['quiz_pos']=int(session.get('quiz_pos') or 0)+1;return redirect('/member/quiz')


@app.get('/member/review')
def review():
    m=member_now();
    if not m:return redirect('/member/login')
    i=int(request.args.get('i','0')); path=session.get('quiz_path',''); ids=list(session.get('quiz_ids') or []); answers=list(session.get('quiz_answers') or [])
    if i<0 or i>=len(answers):return redirect('/member')
    try:_,tex=read_tex(path);allq=parse_questions(tex);by={q['idx']:q}; q=next(x for x in allq if x['idx']==answers[i]['index'])
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    body=f"<div class='wrap'><div class='panel'><div class='mh'>🤖 Phản biện câu {i+1}</div><div class='body'><div class='qtext'>{html.escape(q['text'])}</div><div class='review'>Học sinh trả lời: <b>{html.escape(str(answers[i]['student']))}</b>\n\nKết quả: {'ĐÚNG' if answers[i]['ok'] else 'SAI'}\n\nLời giải gốc được lấy trực tiếp từ file TEX khi ADMIN mở chỉnh sửa.\n\nMuốn Gemini phản biện chi tiết, cấu hình GEMINI_API_KEY rồi nối endpoint Gemini.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>"
    return page('Phản biện',body)


@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''; user=ADMIN_USERNAME
    if request.method=='POST':
        u=request.form.get('username','').strip();p=request.form.get('password','')
        if u==user and ADMIN_PASSWORD and p==ADMIN_PASSWORD:session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    return page('ADMIN',f"<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='{html.escape(user)}'></div><div class='field'><label>Mật khẩu</label><input name='password' type='password'></div><button class='btn'>Đăng nhập</button><div class='err'>{html.escape(msg)}</div></form></div></div></div>")


@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')


@app.get('/admin')
def admin_home():
    if session.get('role')!='admin':return redirect('/admin/login')
    d=members_data();rows=[]
    for m in d.get('members',[]):
        typ=str(m.get('account_type') or 'FREE').upper();u=html.escape(str(m.get('username') or ''),quote=True)
        rows.append(f"<tr><td>{html.escape(str(m.get('username') or ''))}</td><td>{html.escape(str(m.get('name') or ''))}</td><td>{html.escape(str(m.get('class') or ''))}</td><td><form method='post' action='/admin/member/type'><input type='hidden' name='username' value='{u}'><select name='account_type'><option {'selected' if typ=='FREE' else ''}>FREE</option><option {'selected' if typ=='VIP' else ''}>VIP</option></select> <button class='btn'>Lưu</button></form></td></tr>")
    return page('ADMIN',f"<div class='wrap'><div class='panel'><div class='mh'><b>🔐 ADMIN · Thành viên</b><span><a class='btn' href='/admin/edit'>✏️ Sửa TEX</a><a class='btn' href='/admin/logout'>Thoát</a></span></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th></tr>{''.join(rows)}</table></div></div></div>")


@app.post('/admin/member/type')
def admin_member_type():
    if session.get('role')!='admin':return redirect('/admin/login')
    u=request.form.get('username','');typ='VIP' if request.form.get('account_type')=='VIP' else 'FREE';d=members_data()
    for m in d.get('members',[]):
        if m.get('username')==u:m['account_type']=typ;break
    if not TOKEN:return page('Lỗi',"<div class='wrap err'>Thiếu GITHUB_TOKEN.</div>")
    cur=gh('contents/members.json?ref='+urllib.parse.quote(BRANCH))
    gh('contents/members.json','PUT',{'message':'ADMIN cập nhật quyền thành viên','content':base64.b64encode((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()).decode(),'branch':BRANCH,'sha':cur.get('sha')})
    MEMBERS_FILE.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return redirect('/admin')


@app.get('/admin/edit')
def admin_edit():
    if session.get('role')!='admin':return redirect('/admin/login')
    # show .tex paths from index for quick selection
    lessons=[x for x in index_data().get('lessons',[]) if isinstance(x,dict) and str(x.get('path','')).lower().endswith('.tex')]
    links=''.join(f"<div><a class='btn' href='/admin/edit?path={urllib.parse.quote(str(x.get('path')),safe='')}'>{html.escape(str(x.get('BaiHoc') or x.get('De') or x.get('path')))}</a></div>" for x in lessons)
    path=request.args.get('path','')
    if not path:return page('Sửa TEX',f"<div class='wrap'><div class='panel'><div class='head'>✏️ Chọn file .tex</div><div class='body'>{links}</div></div></div>")
    try:sha,text=read_tex(path)
    except Exception as e:return page('Lỗi',f"<div class='wrap err'>{html.escape(str(e))}</div>")
    body=f"<div class='wrap'><div class='panel'><div class='mh'><b>✏️ {html.escape(path)}</b><a class='btn' href='/admin'>← ADMIN</a></div><div class='body'><textarea id='code' class='code'>{html.escape(text)}</textarea><p><button class='btn' onclick='saveTex()'>💾 Commit GitHub</button> <span id='msg'></span></p></div></div></div><script>async function saveTex(){{let r=await fetch('/admin/api/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{path:{json.dumps(path)},sha:{json.dumps(sha)},text:document.getElementById('code').value}})}});let d=await r.json();document.getElementById('msg').textContent=d.ok?'✅ Đã commit '+d.commit:'❌ '+(d.error||'Lỗi')}}}</script>"
    return page('Sửa TEX',body)


@app.post('/admin/api/save')
def admin_save():
    if session.get('role')!='admin':return jsonify(ok=False,error='Chưa đăng nhập ADMIN'),401
    d=request.get_json(silent=True) or {};path=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not isinstance(path,str) or not path.startswith('ngan-hang/') or not path.lower().endswith('.tex') or '..' in path:return jsonify(ok=False,error='Path .tex không hợp lệ'),400
    if not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu dữ liệu'),400
    try:z=gh(f"contents/{urllib.parse.quote(path,safe='/')}",'PUT',{'message':'ADMIN sửa trực tiếp file TEX','content':base64.b64encode(text.encode()).decode(),'branch':BRANCH,'sha':sha});return jsonify(ok=True,commit=str((z.get('commit') or {}).get('sha',''))[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),500


@app.errorhandler(Exception)
def error_page(exc):
    return page('Lỗi máy chủ',f"<div class='wrap'><div class='panel'><div class='head'>⚠️ Lỗi máy chủ</div><div class='body'><div class='err'>{html.escape(str(exc))}</div><a class='btn' href='/health'>/health</a></div></div></div>"),500

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
