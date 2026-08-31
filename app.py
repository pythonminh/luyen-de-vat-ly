# -*- coding: utf-8 -*-
"""Single-file stable portal. GitHub is the source of truth for question-bank .tex."""
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
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.getenv("GEMINI_REVIEW_MODEL") or os.getenv("GEMINI_HINT_MODEL") or "gemini-2.5-flash").strip()
ROOT = Path(__file__).resolve().parent

EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
DANG_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)
LEVEL_RE = re.compile(r"%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\r\n%]+)", re.I)

CSS = r"""
*{box-sizing:border-box}body{margin:0;background:#f3f7fc;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#1769d2;color:#fff;padding:10px 16px}.toprow{display:flex;align-items:center;gap:12px}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #b9d5f7;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin:2px}.nav a{background:#ffffff18;color:#fff;border-color:#ffffff55}.wrap{max-width:1450px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid #cfdae5;border-radius:11px;overflow:hidden}.head,.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.mh{display:flex;justify-content:space-between;align-items:center;gap:10px}.body{padding:10px}.login{max-width:430px;margin:65px auto}.field{margin-bottom:9px}.field label{display:block;font-size:11px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.layout{display:grid;grid-template-columns:290px 1fr;gap:10px}.tree{max-height:75vh;overflow:auto}.tree details{border-bottom:1px solid #e8eef5}.tree summary{cursor:pointer;padding:7px 4px;font-weight:800;list-style:none}.tree summary:before{content:'▶ ';font-size:10px}.tree details[open]>summary:before{content:'▼ '}.tree summary::-webkit-details-marker{display:none}.tree a{display:block;padding:5px 8px;color:#155da8;text-decoration:none;border-radius:6px}.tree a:hover{background:#eef6ff}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:8px}.card{border:1px solid #dce5ed;border-radius:9px;padding:10px;background:#fff}.small{font-size:11px;color:#64748b}.tag{display:inline-block;padding:3px 7px;border:1px solid #cbd5e1;border-radius:999px;font-size:10px;margin:2px}.free{border-color:#86d8a2;background:#effcf3;color:#16733c}.vip{border-color:#f2a5cd;background:#fff0f8;color:#a01c60}.bar{padding:9px;border:1px solid #9fd4aa;background:#f0fbf2;border-radius:8px;font-weight:900}.lesson{border:1px solid #d4e1ed;border-radius:10px;padding:12px;background:#fff}.qtext{font-size:17px;line-height:1.7}.opt,.tf{display:block;border:2px solid #d8e5f1;border-radius:9px;padding:10px;margin:7px 0;cursor:pointer}.correct{background:#e9f9ef!important;border-color:#35a95b!important}.wrong{background:#fff0f1!important;border-color:#e34149!important}.code{width:100%;height:72vh;resize:vertical;font:12px/1.5 Consolas,monospace;border:1px solid #cbd5e1;border-radius:8px;padding:10px}.ok{color:#15803d;font-weight:800}.err{color:#b91c1c;font-weight:800}.review{margin-top:10px;padding:10px;border:1px solid #cdbbff;background:#faf7ff;border-radius:8px;line-height:1.6}.table{width:100%;border-collapse:collapse}.table th,.table td{border:1px solid #dfe7ef;padding:6px}.table th{background:#f5f8fc}.selectgrid{width:100%;border-collapse:collapse}.selectgrid th,.selectgrid td{border:1px solid #dfe7ef;padding:5px}.selectgrid th{background:#eaf3ff}.n{width:55px}@media(max-width:850px){.layout{grid-template-columns:1fr}.tree{max-height:35vh}.cards{grid-template-columns:1fr}}
"""


def gh(path: str, method: str = "GET", data: dict | None = None) -> dict:
    if not TOKEN:
        raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    owner, repo = REPO.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{repo}/{path.lstrip('/')}"
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ldvl-stable-portal",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(text).get("message", text)
        except Exception:
            msg = text
        raise RuntimeError(f"GitHub API {e.code}: {msg}") from e


def local_json(name: str, default):
    try:
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def members():
    return local_json("members.json", {"members": []})


def access():
    d = local_json("lesson_access.json", {"default": "FREE", "lessons": {}})
    d.setdefault("default", "FREE")
    d.setdefault("lessons", {})
    return d


def is_vip(m):
    return str(m.get("account_type", "FREE")).upper() in {"VIP", "S.VIP", "ADMIN"}


def current_member():
    u = session.get("username")
    if not u:
        return None
    for m in members().get("members", []):
        if m.get("username") == u and m.get("status", "ON") == "ON":
            return m
    return None


def allowed(member, path: str):
    level = str(access().get("lessons", {}).get(path, access().get("default", "FREE"))).upper()
    return level == "FREE" or is_vip(member), level


def safe_tex(path: str):
    return isinstance(path, str) and path.startswith("ngan-hang/") and path.lower().endswith(".tex") and ".." not in path


def read_tex(path: str):
    if not safe_tex(path):
        raise ValueError("Đường dẫn .tex không hợp lệ")
    d = gh(f"contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(BRANCH)}")
    text = base64.b64decode((d.get("content") or "").replace("\n", "")).decode("utf-8", "replace")
    return d.get("sha", ""), text


def save_tex(path: str, text: str, sha: str):
    return gh(f"contents/{urllib.parse.quote(path, safe='/')}", "PUT", {
        "message": "ADMIN cập nhật trực tiếp file .tex",
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": sha,
    })


def index_data():
    p = ROOT / "bank_index.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    d = gh("contents/bank_index.json?ref=" + urllib.parse.quote(BRANCH))
    return json.loads(base64.b64decode((d.get("content") or "").replace("\n", "")).decode())


def parse_questions(text: str):
    out = []
    for i, block in enumerate(EX_RE.findall(text), 1):
        dang_m = DANG_RE.search(block)
        level_m = LEVEL_RE.search(block)
        dang = dang_m.group(1).strip() if dang_m else "Chưa phân dạng"
        level = (level_m.group(1).strip().upper()[:1] if level_m else "H")
        if level not in "NHVC":
            level = "H"
        if re.search(r"\\choiceTF\b", block, re.I):
            kind = "DS"
        elif re.search(r"\\choice\b", block, re.I):
            kind = "TN"
        elif re.search(r"\\shortans\b", block, re.I):
            kind = "TLN"
        else:
            kind = "TL"
        out.append({"index": i - 1, "kind": kind, "dang": dang, "level": level, "raw": block})
    return out


def page(title, body):
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
                    + f"<title>{html.escape(title)}</title><style>{CSS}</style>"
                    + "<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]}};</script>"
                    + "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body>"
                    + "<div class='top'><div class='toprow'><div><div class='brand'>📚 Luyện đề · Thầy Minh</div><div class='sub'>GitHub / ngan-hang/*.tex là nguồn chính</div></div>"
                    + "<div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin/login'>🔐 ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"
                    + body + "</body></html>", mimetype="text/html")


def need_member():
    return session.get("role") == "member" and current_member() is not None


def need_admin():
    return session.get("role") == "admin"


@app.get("/")
def root():
    return redirect("/member") if need_member() else redirect("/member/login")


@app.get("/health")
def health():
    return jsonify(ok=True, app="stable", repo=REPO, branch=BRANCH)


@app.get("/github/repo")
def repo_link():
    return redirect(f"https://github.com/{REPO}")


@app.route("/member/login", methods=["GET", "POST"])
def member_login():
    msg = ""
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        h = hashlib.sha256(p.encode()).hexdigest()
        for m in members().get("members", []):
            if m.get("username") == u and m.get("password_sha256") == h and m.get("status", "ON") == "ON":
                session.clear(); session.update(role="member", username=u)
                return redirect("/member")
        msg = "Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa."
    body = "<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div><div class='body'><form method='post'>" \
           "<div class='field'><label>Tài khoản</label><input name='username' required></div>" \
           "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div>" \
           "<button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a>" \
           f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>"
    return page("Đăng nhập", body)


@app.route("/member/register", methods=["GET", "POST"])
def member_register():
    msg = ""
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        n = (request.form.get("name") or "").strip()
        p = request.form.get("password") or ""
        d = members()
        if not u or not p:
            msg = "Thiếu tài khoản hoặc mật khẩu."
        elif any(x.get("username") == u for x in d.get("members", [])):
            msg = "Tài khoản đã tồn tại."
        else:
            d.setdefault("members", []).append({"username":u,"name":n or u,"class":"","account_type":"FREE","status":"ON","password_sha256":hashlib.sha256(p.encode()).hexdigest()})
            try:
                cur = gh("contents/members.json?ref=" + urllib.parse.quote(BRANCH))
                gh(f"contents/members.json", "PUT", {"message":"Đăng ký thành viên", "content":base64.b64encode((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()).decode(), "branch":BRANCH, "sha":cur.get("sha")})
                (ROOT/"members.json").write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                session.clear(); session.update(role="member", username=u); return redirect("/member")
            except Exception as exc:
                msg = str(exc)
    body = "<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký FREE</div><div class='body'><form method='post'>" \
           "<div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div>" \
           "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Tạo tài khoản</button>" \
           f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>"
    return page("Đăng ký", body)


@app.get("/member/logout")
def member_logout():
    session.clear(); return redirect("/member/login")


@app.get("/member")
def member_home():
    if not need_member(): return redirect("/member/login")
    m = current_member(); d = index_data(); tree = {}; cards=[]
    for x in d.get("lessons", []):
        if not isinstance(x, dict): continue
        path = str(x.get("path") or x.get("file") or "")
        if not safe_tex(path): continue
        sub=str(x.get("Mon") or "Khác"); lop=str(x.get("Lop") or ""); chuong=str(x.get("Chuong") or "Chưa xác định")
        tree.setdefault((sub,lop,chuong),[]).append(x)
    left=[]
    for (sub,lop,chuong), items in sorted(tree.items()):
        links=''.join("<a href='/member/select?path="+urllib.parse.quote(str(x.get('path')),safe='')+"'>"+html.escape(str(x.get('BaiHoc') or x.get('De') or Path(str(x.get('path'))).parent.name))+"</a>" for x in items)
        left.append(f"<details><summary>📘 {html.escape(sub)} · Lớp {html.escape(lop)} · {html.escape(chuong)}</summary>{links}</details>")
        for x in items:
            path=str(x.get('path')); level=str(access().get('lessons',{}).get(path,access().get('default','FREE'))).upper(); cnt=int(x.get('questions') or x.get('count') or 0)
            cards.append(f"<div class='card'><b>{html.escape(str(x.get('BaiHoc') or x.get('De') or Path(path).parent.name))}</b><div class='small'>{html.escape(sub)} · Lớp {html.escape(lop)} · {html.escape(chuong)}</div><span class='tag {'vip' if level=='VIP' else 'free'}'>{level}</span><span class='tag'>{cnt} câu</span><div><a class='btn' href='/member/select?path={urllib.parse.quote(path,safe='')}'>Chọn dạng / số câu</a></div></div>")
    badge="VIP · FREE + VIP" if is_vip(m) else "FREE · chỉ FREE"
    body=f"<div class='wrap'><div class='bar'>👤 <b>{html.escape(str(m.get('name') or m.get('username')))}</b> · Tài khoản: <b>{html.escape(str(m.get('username')))}</b> · Quyền: <b>{badge}</b> · <a href='/member/logout'>Đăng xuất</a></div><div class='layout' style='margin-top:10px'><aside class='panel'><div class='head'>🌳 Cấu trúc ngân hàng</div><div class='body tree'>{''.join(left)}</div></aside><main class='panel'><div class='mh'><span>📚 Mục lục</span><span>{int(d.get('total_files') or 0)} bài · {int(d.get('total_questions') or 0)} câu</span></div><div class='body'><div class='cards'>{''.join(cards)}</div></div></main></div></div>"
    return page("Ngân hàng", body)


@app.get("/member/select")
def select_lesson():
    if not need_member(): return redirect("/member/login")
    m=current_member(); path=request.args.get("path","")
    allowed_flag, level = allowed(m,path)
    if not allowed_flag: return page("Bài VIP", "<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    try: _, text = read_tex(path); qs=parse_questions(text)
    except Exception as exc: return page("Lỗi", f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div></div></div></div>")
    groups={}
    for q in qs: groups.setdefault(q['dang'],[]).append(q)
    rows=[]
    for dang, arr in groups.items():
        cells=[]
        for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
            counts={z:sum(1 for q in arr if q['kind']==kind and q['level']==z) for z in 'NHVC'}
            inputs=''.join(f"<input class='n' type='number' name='n_{re.sub(r'[^A-Za-z0-9]','_',dang)}_{kind}_{z}' min='0' max='{counts[z]}' value='0'>" for z in 'NHVC')
            cells.append(f"<td><b>{label}</b></td><td>{counts['N']}/{counts['H']}/{counts['V']}/{counts['C']}</td><td>{inputs}</td><td>{sum(counts.values())}</td>")
        rows.append("<tr><td rowspan='4'><b>"+html.escape(dang)+"</b></td>"+''.join(cells)+"</tr>")
    heads="<tr><th>Dạng bài</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>"
    body=f"<div class='wrap'><div class='panel'><div class='mh'><span>🧩 {html.escape(Path(path).parent.name)} · <span class='tag {'vip' if level=='VIP' else 'free'}'>{level}</span></span><span>{len(qs)} câu</span></div><div class='body'><form method='post' action='/member/start'><input type='hidden' name='path' value='{html.escape(path,quote=True)}'><table class='selectgrid'><thead>{heads}</thead><tbody>{''.join(rows)}</tbody></table><div class='bar' style='margin-top:9px' id='sum'>TỔNG CHỌN: 0 câu</div><button class='btn' type='submit'>▶ Tạo bài luyện tập</button> <a class='btn' href='/member'>← Mục lục</a></form></div></div></div><script>function rec(){let t=0;document.querySelectorAll('.n').forEach(x=>{let m=+x.max||0,v=Math.max(0,Math.min(m,+x.value||0));x.value=v;t+=v});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu';}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',rec));rec();</script>"
    return page("Chọn dạng bài", body)


@app.post("/member/start")
def start_quiz():
    if not need_member(): return redirect("/member/login")
    m=current_member(); path=request.form.get('path',''); ok, _ = allowed(m,path)
    if not ok: return redirect('/member')
    try: _, text = read_tex(path); qs=parse_questions(text)
    except Exception: return redirect('/member')
    buckets={}
    for key,val in request.form.items():
        if not key.startswith('n_'): continue
        try: want=max(0,int(val or 0))
        except Exception: want=0
        parts=key.split('_'); kind=parts[-2]; level=parts[-1]; dang='_'.join(parts[1:-2]); buckets[(dang,kind,level)]=want
    chosen=[]
    for q in qs:
        k=(re.sub(r'[^A-Za-z0-9]','_',q['dang']),q['kind'],q['level'])
        if buckets.get(k,0)>0:
            chosen.append(q['index']); buckets[k]-=1
    if not chosen: return redirect('/member/select?path='+urllib.parse.quote(path,safe=''))
    session['practice_path']=path; session['practice_indices']=chosen; session['practice_pos']=0; session['practice_right']=0; session['practice_answered']=[]; return redirect('/member/practice')


@app.get('/member/practice')
def practice():
    if not need_member(): return redirect('/member/login')
    path=str(session.get('practice_path') or ''); ids=list(session.get('practice_indices') or []); pos=int(session.get('practice_pos') or 0); right=int(session.get('practice_right') or 0); answered=list(session.get('practice_answered') or [])
    if not path or not ids: return redirect('/member')
    try: _, text=read_tex(path); allq=parse_questions(text); by={q['index']:q for q in allq}; raw=[by[i]['raw'] for i in ids if i in by]
    except Exception as exc: return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div></div></div></div>")
    if pos>=len(raw): return page('Kết quả',f"<div class='wrap'><div class='panel'><div class='body'><div class='bar'>🎉 Hoàn thành · Đúng {right}/{len(raw)} · Điểm {(right/len(raw)*10 if raw else 0):.2f}/10</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    q=parse_questions(raw[pos])[0] if False else None
    # parse one raw block with the same small parser
    item=parse_questions(raw[pos])[0]
    kind=item['kind']; rawblock=raw[pos]
    def args(cmd):
        mm=re.search(re.escape(cmd)+r'\b',rawblock,re.I)
        if not mm:return []
        vals=[]; p=mm.end(); depth=0
        while p<len(rawblock):
            while p<len(rawblock) and rawblock[p].isspace():p+=1
            if p>=len(rawblock) or rawblock[p]!='{':break
            start=p+1; depth=1; p+=1
            while p<len(rawblock) and depth:
                if rawblock[p]=='{' and rawblock[p-1]!='\\': depth+=1
                elif rawblock[p]=='}' and rawblock[p-1]!='\\': depth-=1
                p+=1
            if depth==0: vals.append(rawblock[start:p-1])
            else: break
        return vals
    def strip_true(s): return re.sub(r'^\\True\s*','',s,flags=re.I).strip()
    correct=[]
    opts=[]
    if kind=='TN':
        oa=args('\\choice'); opts=[strip_true(x) for x in oa[:4]]; correct=next((i for i,x in enumerate(oa[:4]) if re.match(r'^\\True\b',x,re.I)),-1)
    elif kind=='DS':
        oa=args('\\choiceTF'); opts=[strip_true(x) for x in oa]; correct=[bool(re.match(r'^\\True\b',x,re.I)) for x in oa]
    elif kind=='TLN':
        mm=re.search(r'\\shortans\s*\{([^{}]*)\}',rawblock,re.I); opts=[mm.group(1).strip() if mm else '']
    text=rawblock
    text=re.sub(r'\\begin\s*\{\s*ex\s*\}|\\end\s*\{\s*ex\s*\}','',text,flags=re.I)
    text=DANG_RE.sub('',text); text=LEVEL_RE.sub('',text); text=re.split(r'\\choiceTF|\\choice|\\shortans',text,1,flags=re.I)[0].strip()
    qdata=json.dumps({'kind':kind,'text':text,'opts':opts,'correct':correct},ensure_ascii=False)
    body=f"<div class='wrap'><div class='panel'><div class='mh'><span>📝 Câu {pos+1}/{len(raw)} · {html.escape(item['dang'])}</span><span>Đúng {right}</span></div><div class='body'><div id='q' class='lesson'></div><div class='bar' id='st'>Sau khi kiểm tra mới sang câu tiếp.</div></div></div></div>"
    js=r"""
const Q=__Q__;let checked=false;function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}function ts(){if(window.MathJax)MathJax.typesetPromise()}function draw(){let q=Q,h='<div class="qtext"><b>Câu __P__.</b> '+esc(q.text)+'</div>';if(q.kind==='TN'){q.opts.forEach((x,i)=>h+='<label class="opt" data-i="'+i+'"><input type="radio" name="a" value="'+i+'"> <b>'+String.fromCharCode(65+i)+'.</b> '+esc(x)+'</label>')}else if(q.kind==='DS'){q.opts.forEach((x,i)=>h+='<div class="tf" data-i="'+i+'"><b>'+(i+1)+'.</b> '+esc(x)+'<br><label><input type="radio" name="t'+i+'" value="1"> Đúng</label> <label><input type="radio" name="t'+i+'" value="0"> Sai</label></div>')}else if(q.kind==='TLN'){h+='<input id="ans" class="field" style="width:100%;padding:9px" placeholder="Nhập đáp án">'}else{h+='<textarea id="ans" class="code" style="height:170px" placeholder="Nhập bài làm"></textarea>'}h+='<div style="margin-top:10px"><button class="btn" onclick="checkQ()">✅ Kiểm tra</button> <button class="btn" id="next" disabled onclick="nextQ()">→ Câu tiếp</button></div><div id="res"></div>';document.getElementById('q').innerHTML=h;ts()}function checkQ(){if(checked)return;let q=Q,ok=false;if(q.kind==='TN'){let e=document.querySelector('input[name=a]:checked');if(!e)return alert('Chọn đáp án.');let i=+e.value;q.opts.forEach((x,j)=>{let el=document.querySelector('.opt[data-i="'+j+'"]');if(j===q.correct)el.classList.add('correct');if(j===i&&i!==q.correct)el.classList.add('wrong')});ok=i===q.correct}else if(q.kind==='DS'){let all=true;q.opts.forEach((x,j)=>{let e=document.querySelector('input[name=t'+j+']:checked');if(!e)all=false;else{let v=e.value==='1';let el=document.querySelector('.tf[data-i="'+j+'"]');if(v===q.correct[j])el.classList.add('correct');else el.classList.add('wrong')}});if(!all)return alert('Chọn Đúng/Sai đủ các ý.');ok=q.correct.every((v,j)=>(document.querySelector('input[name=t'+j+']:checked').value==='1')===v)}else if(q.kind==='TLN'){let e=document.getElementById('ans');if(!e||!e.value.trim())return alert('Nhập đáp án.');ok=e.value.trim().toLowerCase()===String(q.opts[0]||'').trim().toLowerCase();document.getElementById('res').innerHTML='<div class="bar">'+(ok?'✅ ĐÚNG':'❌ SAI')+' · Đáp án: '+esc(q.opts[0]||'')+'</div>'}else{let e=document.getElementById('ans');if(!e||!e.value.trim())return alert('Nhập bài làm.');document.getElementById('res').innerHTML='<div class="bar">📝 Đã ghi nhận bài tự luận.</div>'}if(q.kind!=='TLN'&&q.kind!=='TL')document.getElementById('res').innerHTML='<div class="bar">'+(ok?'✅ ĐÚNG':'❌ SAI')+'</div>';checked=true;document.querySelectorAll('input').forEach(x=>x.disabled=true);document.getElementById('next').disabled=false;fetch('/api/practice/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ok:ok})});}function nextQ(){location.href='/member/practice/next'}draw();
"""
    js=js.replace('__Q__',qdata).replace('__P__',str(pos+1))
    return page('Làm bài',body+"<script>"+js+"</script>")


@app.post('/api/practice/result')
def practice_result():
    if not need_member(): return jsonify(ok=False),401
    d=request.get_json(silent=True) or {}; a=list(session.get('practice_answered') or []); pos=int(session.get('practice_pos') or 0)
    if pos not in a:
        if d.get('ok'): session['practice_right']=int(session.get('practice_right') or 0)+1
        a.append(pos); session['practice_answered']=a
    return jsonify(ok=True)


@app.get('/member/practice/next')
def practice_next():
    if not need_member(): return redirect('/member/login')
    session['practice_pos']=int(session.get('practice_pos') or 0)+1
    return redirect('/member/practice')


@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        u=(request.form.get('username') or '').strip();p=request.form.get('password') or ''
        if u==ADMIN_USERNAME and ADMIN_PASSWORD and p==ADMIN_PASSWORD:
            session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    body="<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='"+html.escape(ADMIN_USERNAME)+"' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button><div class='err'>"+html.escape(msg)+"</div></form></div></div></div>"
    return page('ADMIN',body)


@app.get('/admin/logout')
def admin_logout():
    session.clear();return redirect('/admin/login')


@app.get('/admin')
def admin_home():
    if not need_admin(): return redirect('/admin/login')
    d=members(); rows=[]
    for m in d.get('members',[]):
        typ=str(m.get('account_type') or 'FREE').upper();u=html.escape(str(m.get('username') or ''),quote=True)
        rows.append(f"<tr><td>{html.escape(str(m.get('username') or ''))}</td><td>{html.escape(str(m.get('name') or ''))}</td><td>{html.escape(str(m.get('class') or ''))}</td><td><form method='post' action='/admin/member/type'><input type='hidden' name='username' value='{u}'><select name='account_type'><option {'selected' if typ=='FREE' else ''}>FREE</option><option {'selected' if typ=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu</button></form></td><td>{html.escape(str(m.get('status') or 'ON'))}</td></tr>")
    body="<div class='wrap'><div class='panel'><div class='mh'><span>🔐 ADMIN · Thành viên</span><span><a class='btn' href='/github/quan-ly'>📚 Ngân hàng GitHub</a> <a class='btn' href='/admin/logout'>Thoát</a></span></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th></tr>"+''.join(rows)+"</table></div></div></div>"
    return page('ADMIN',body)


@app.post('/admin/member/type')
def admin_member_type():
    if not need_admin(): return redirect('/admin/login')
    u=request.form.get('username','');typ='VIP' if request.form.get('account_type')=='VIP' else 'FREE';d=members()
    for m in d.get('members',[]):
        if m.get('username')==u:m['account_type']=typ;break
    cur=gh('contents/members.json?ref='+urllib.parse.quote(BRANCH));gh('contents/members.json','PUT',{'message':'ADMIN đổi quyền thành viên','content':base64.b64encode((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()).decode(),'branch':BRANCH,'sha':cur.get('sha')});(ROOT/'members.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return redirect('/admin')


@app.get('/admin/edit')
def admin_edit():
    if not need_admin(): return redirect('/admin/login')
    path=request.args.get('path','')
    try: sha,text=read_tex(path)
    except Exception as exc: return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div></div></div></div>")
    body="<div class='wrap'><div class='panel'><div class='mh'><b>✏️ "+html.escape(path)+"</b><a class='btn' href='/admin'>← ADMIN</a></div><div class='body'><textarea id='code' class='code'>"+html.escape(text)+"</textarea><div><button class='btn' onclick='saveIt()'>💾 Lưu GitHub</button><span id='msg'></span></div></div></div></div>"
    body += "<script>const path="+json.dumps(path)+",sha="+json.dumps(sha)+";async function saveIt(){let r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,sha,text:document.getElementById('code').value})});let d=await r.json();document.getElementById('msg').textContent=d.ok?'✅ Đã commit '+d.commit:'❌ '+(d.error||'Lỗi');}</script>"
    return page('Sửa .tex',body)


@app.post('/admin/api/save')
def admin_save():
    if not need_admin(): return jsonify(ok=False,error='Chưa đăng nhập ADMIN'),401
    d=request.get_json(silent=True) or {};path=d.get('path','');text=d.get('text');sha=d.get('sha','')
    if not safe_tex(path) or not isinstance(text,str) or not sha:return jsonify(ok=False,error='Thiếu path/text/sha'),400
    try:
        z=save_tex(path,text,sha);return jsonify(ok=True,commit=str((z.get('commit') or {}).get('sha') or '')[:12])
    except Exception as exc:return jsonify(ok=False,error=str(exc)),409


@app.errorhandler(Exception)
def all_errors(exc):
    return page('Lỗi máy chủ', "<div class='wrap'><div class='panel'><div class='head'>⚠️ Lỗi máy chủ</div><div class='body'><div class='err'>"+html.escape(str(exc))+"</div><p>Vào <a href='/health'>/health</a> để kiểm tra dịch vụ.</p></div></div></div>"),500

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
