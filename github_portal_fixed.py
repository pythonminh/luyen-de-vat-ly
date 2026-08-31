# -*- coding: utf-8 -*-
"""Standalone portal: FREE/VIP members + ADMIN, GitHub is the source of truth."""
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
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "bank_index.json"
MEMBERS = ROOT / "members.json"
ACCESS = ROOT / "lesson_access.json"
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
SOL_RE = re.compile(r"\\loigiai\s*\{", re.I)
CHOICE_RE = re.compile(r"\\choice\b", re.I)
TF_RE = re.compile(r"\\choiceTF\b", re.I)
SHORT_RE = re.compile(r"\\shortans\s*\{([^{}]*)\}", re.I)
DANG_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)

CSS = """
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial}.top{background:#1769d2;color:#fff;padding:10px 16px}.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #bdd5f4;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin:3px}.nav a{background:transparent;color:#fff;border-color:#ffffff66}.wrap{max-width:1450px;margin:auto;padding:12px}.grid{display:grid;grid-template-columns:260px 1fr;gap:10px}.panel{background:#fff;border:1px solid #d6e0ea;border-radius:12px;overflow:hidden}.head{padding:10px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.body{padding:10px}.field{margin-bottom:8px}.field label{display:block;font-size:10px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;display:flex;justify-content:space-between;gap:8px;font-weight:900}.hero{padding:14px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px;padding:8px}.card{border:1px solid #dce5ed;border-radius:9px;padding:10px;background:#fff}.small{font-size:11px;color:#64748b}.tag{display:inline-block;padding:3px 7px;border:1px solid #cbd5e1;border-radius:999px;font-size:10px;margin:4px 3px 0 0}.free{border-color:#86efac;background:#f0fdf4;color:#166534}.vip{border-color:#f9a8d4;background:#fdf2f8;color:#9d174d}.lock{opacity:.72}.login{max-width:420px;margin:70px auto}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:7px;border-bottom:1px solid #e5e7eb;text-align:left}.code{width:100%;height:72vh;resize:vertical;border:1px solid #cbd5e1;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.actions{padding:0 10px 10px}.ok{color:#15803d;font-weight:800}.err{color:#b91c1c;font-weight:800}.qtext{line-height:1.6}.opt{padding:9px;border:1px solid #dbeafe;border-radius:8px;margin:6px 0;cursor:pointer}.opt:hover{background:#f8fbff}.answer{margin-top:12px;padding:10px;border:1px solid #bfdbfe;border-radius:8px;background:#eff6ff}.score{padding:10px;border:1px solid #86efac;background:#f0fdf4;border-radius:9px;font-weight:900}.section{margin:10px 0;padding:9px;border:1px solid #dbeafe;border-radius:8px;background:#f8fbff}.hide{display:none}@media(max-width:800px){.grid{grid-template-columns:1fr}.login{margin:25px auto}}
"""


def gh(path, method="GET", data=None):
    if not TOKEN:
        raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API + path,
        data=body,
        method=method,
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ldvl-portal",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(raw).get("message", raw)
        except Exception:
            msg = raw
        raise RuntimeError(f"GitHub API {e.code}: {msg}") from e


def index_data():
    if INDEX.exists():
        return json.loads(INDEX.read_text(encoding="utf-8"))
    owner, repo = REPO.split("/", 1)
    url = f"{RAW}/{owner}/{repo}/{urllib.parse.quote(BRANCH)}/bank_index.json"
    with urllib.request.urlopen(url, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))


def load_access():
    if not ACCESS.exists():
        return {"schema": 1, "default": "FREE", "lessons": {}}
    try:
        d = json.loads(ACCESS.read_text(encoding="utf-8"))
        d.setdefault("default", "FREE")
        d.setdefault("lessons", {})
        return d
    except Exception:
        return {"schema": 1, "default": "FREE", "lessons": {}}


def save_access(data):
    ACCESS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gh_put_file(path, content, message, sha=None):
    owner, repo = REPO.split("/", 1)
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
    }
    if sha:
        body["sha"] = sha
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}", "PUT", body)


def gh_get_file(path):
    owner, repo = REPO.split("/", 1)
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(BRANCH)}")


def read_tex(path):
    if not (isinstance(path, str) and path.startswith("ngan-hang/") and path.lower().endswith(".tex") and ".." not in path):
        raise ValueError("Đường dẫn .tex không hợp lệ")
    d = gh_get_file(path)
    text = base64.b64decode((d.get("content") or "").replace("\n", "")).decode("utf-8", "replace")
    return d.get("sha", ""), text


def load_members():
    try:
        return json.loads(MEMBERS.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": 2, "members": []}


def save_members(data):
    MEMBERS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_members(data):
    current = gh_get_file("members.json")
    gh_put_file("members.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n", "Admin cập nhật thành viên", current.get("sha"))


def sync_access(data):
    current = None
    try:
        current = gh_get_file("lesson_access.json")
    except Exception:
        pass
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    gh_put_file("lesson_access.json", content, "Admin cập nhật quyền bài học", current.get("sha") if current else None)


def account_type(member):
    return str(member.get("account_type") or "FREE").upper()


def is_vip(member):
    return account_type(member) in {"VIP", "S.VIP", "ADMIN"}


def current_member():
    u = session.get("username")
    if not u:
        return None
    for m in load_members().get("members", []):
        if m.get("username") == u and m.get("status", "ON") == "ON":
            return m
    return None


def can_open_lesson(member, path):
    a = load_access()
    level = str(a.get("lessons", {}).get(path, a.get("default", "FREE"))).upper()
    return level == "FREE" or is_vip(member), level


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect("/admin/login")
        return view(*args, **kwargs)
    return wrapped


def require_member(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "member":
            return redirect("/member/login")
        if not current_member():
            session.clear()
            return redirect("/member/login")
        return view(*args, **kwargs)
    return wrapped


def page(title, body):
    return Response(
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style>"
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>"
        "</head><body><div class='top'><div class='row'>"
        "<div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div>"
        "<div class='sub'>Nguồn chính: GitHub / ngan-hang/*.tex · Google Sheet không dùng khi chạy</div></div>"
        "<div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a>"
        "<a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"
        + body + "</body></html>",
        mimetype="text/html",
    )


def brace_arg(text, pos):
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] != "{":
        return None, pos
    depth = 0
    start = pos + 1
    i = pos
    while i < len(text):
        if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif text[i] == "}" and (i == 0 or text[i - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    return None, len(text)


def extract_args(text, command):
    m = re.search(re.escape(command) + r"\b", text, re.I)
    if not m:
        return []
    out = []
    pos = m.end()
    while True:
        arg, pos2 = brace_arg(text, pos)
        if arg is None:
            break
        out.append(arg)
        pos = pos2
    return out


def strip_true(s):
    return re.sub(r"^\s*\\True\s*", "", s, flags=re.I)


def parse_question(block):
    tf_args = extract_args(block, "\\choiceTF")
    if tf_args:
        statements = [strip_true(x).strip() for x in tf_args[:6]]
        correct = [bool(re.match(r"^\s*\\True\b", x, re.I)) for x in tf_args[:6]]
        qtext = TF_RE.split(block, maxsplit=1)[0]
        qtext = clean_question(qtext)
        return {"kind": "tf", "text": qtext, "statements": statements, "correct": correct}
    args = extract_args(block, "\\choice")
    if args:
        options = [strip_true(x).strip() for x in args[:4]]
        correct = 0
        for i, x in enumerate(args[:4]):
            if re.match(r"^\s*\\True\b", x, re.I):
                correct = i
                break
        qtext = CHOICE_RE.split(block, maxsplit=1)[0]
        qtext = clean_question(qtext)
        return {"kind": "choice", "text": qtext, "options": options, "correct": correct}
    sm = SHORT_RE.search(block)
    if sm:
        qtext = clean_question(block[: sm.start()])
        return {"kind": "short", "text": qtext, "answer": sm.group(1).strip()}
    return {"kind": "unsupported", "text": clean_question(block)}


def clean_question(text):
    text = re.sub(r"%.*", "", text)
    text = DANG_RE.sub("", text)
    text = re.sub(r"\\ID\s*:\s*[^\n]*", "", text, flags=re.I)
    text = re.sub(r"\\begin\s*\{ex\}", "", text, flags=re.I)
    text = re.sub(r"\\end\s*\{ex\}", "", text, flags=re.I)
    return text.strip()


def lesson_questions(path):
    _, text = read_tex(path)
    return [parse_question(b) for b in EX_RE.findall(text)]


@app.get("/")
def root():
    return redirect("/member/login")


@app.get("/github/repo")
def repo_link():
    return redirect(f"https://github.com/{REPO}")


@app.route("/member/login", methods=["GET", "POST"])
def member_login():
    msg = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        wanted = hashlib.sha256(password.encode()).hexdigest()
        for m in load_members().get("members", []):
            if m.get("username") == username and m.get("password_sha256") == wanted and m.get("status", "ON") == "ON":
                session.clear()
                session.update(role="member", username=username, name=m.get("name") or username)
                return redirect("/member")
        msg = "Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa."
    body = ("<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div>"
            "<div class='body'><form method='post'><div class='field'><label>Tài khoản</label>"
            "<input name='username' required></div><div class='field'><label>Mật khẩu</label>"
            "<input name='password' type='password' required></div><button class='btn'>Đăng nhập</button>"
            " <a class='btn' href='/member/register'>Đăng ký</a>"
            f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>")
    return page("Đăng nhập thành viên", body)


@app.route("/member/register", methods=["GET", "POST"])
def member_register():
    msg = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        name = (request.form.get("name") or "").strip()
        password = request.form.get("password") or ""
        data = load_members()
        users = {m.get("username") for m in data.get("members", [])}
        if not username or not password:
            msg = "Thiếu tài khoản hoặc mật khẩu."
        elif username in users:
            msg = "Tài khoản đã tồn tại."
        else:
            data.setdefault("members", []).append({
                "username": username, "name": name or username, "class": "",
                "account_type": "FREE", "status": "ON",
                "password_sha256": hashlib.sha256(password.encode()).hexdigest(),
            })
            try:
                save_members(data)
                sync_members(data)
                session.clear(); session.update(role="member", username=username, name=name or username)
                return redirect("/member")
            except Exception as exc:
                msg = str(exc)
    body = ("<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký thành viên</div>"
            "<div class='body'><form method='post'><div class='field'><label>Họ tên</label><input name='name'></div>"
            "<div class='field'><label>Tài khoản</label><input name='username' required></div>"
            "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div>"
            "<button class='btn'>Tạo tài khoản FREE</button> <a class='btn' href='/member/login'>Quay lại</a>"
            f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>")
    return page("Đăng ký", body)


@app.get("/member/logout")
def member_logout():
    session.clear()
    return redirect("/member/login")


@app.get("/member")
@require_member
def member_home():
    member = current_member(); data = index_data();
    vip = is_vip(member)
    cards = []
    for item in data.get("lessons", []):
        if not isinstance(item, dict): continue
        path = str(item.get("path") or "")
        if not path.startswith("ngan-hang/"): continue
        title = str(item.get("BaiHoc") or item.get("De") or Path(path).parent.name)
        count = int(item.get("questions") or item.get("count") or 0)
        allowed, level = can_open_lesson(member, path)
        tag = "VIP" if level == "VIP" else "FREE"
        action = (f"<a class='btn' href='/member/lesson?path={urllib.parse.quote(path, safe='')}'>Làm bài</a>"
                  if allowed else "<span class='tag vip'>🔒 Chỉ VIP</span>")
        cards.append("<div class='card'><b>" + html.escape(title) + "</b>"
                     + f"<div class='small'>{html.escape(str(item.get('Mon') or ''))} · {html.escape(str(item.get('Lop') or ''))}</div>"
                     + f"<span class='tag {('vip' if tag=='VIP' else 'free')}'>{tag}</span>"
                     + f"<span class='tag'>{count} câu</span><div>{action}</div></div>")
    badge = "VIP – được làm FREE + VIP" if vip else "Thành viên thường – chỉ FREE"
    body = ("<div class='wrap'><div class='panel'><div class='mh'><span>👤 "
            + html.escape(str(member.get("name") or member.get("username")))
            + f" · <span class='tag {('vip' if vip else 'free')}'>{badge}</span></span>"
            + "<a class='btn' href='/member/logout'>Thoát</a></div>"
            + "<div class='hero'><h2>Chọn bài để học</h2><div class='small'>"
            + str(int(data.get("total_files") or 0)) + " bài · " + str(int(data.get("total_questions") or 0))
            + " câu</div></div><div class='cards'>" + "".join(cards) + "</div></div></div>")
    return page("Trang thành viên", body)


@app.get("/member/lesson")
@require_member
def member_lesson():
    member = current_member(); path = request.args.get("path", "")
    allowed, level = can_open_lesson(member, path)
    if not allowed:
        return page("Bài VIP", "<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho thành viên VIP.</div><a class='btn' href='/member'>← Quay lại</a></div></div></div>")
    try:
        qs = lesson_questions(path)
    except Exception as exc:
        return page("Lỗi đọc bài", f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div></div></div></div>")
    payload = json.dumps(qs, ensure_ascii=False)
    cards = []
    for i, q in enumerate(qs, 1):
        t = html.escape(q["text"] if isinstance(q, dict) else str(q))
        if q.get("kind") == "choice":
            opts = "".join(f"<label class='opt'><input type='radio' name='q{i}' value='{j}'> {chr(65+j)}. {html.escape(o)}</label>" for j,o in enumerate(q.get("options", [])))
            cards.append(f"<div class='card' data-i='{i-1}'><div class='qtext'><b>Câu {i}.</b> {t}</div>{opts}</div>")
        elif q.get("kind") == "tf":
            stmts = "".join(f"<div class='section'><b>{j+1}.</b> {html.escape(s)}<br><label><input type='radio' name='q{i}_{j}' value='1'> Đúng</label> &nbsp; <label><input type='radio' name='q{i}_{j}' value='0'> Sai</label></div>" for j,s in enumerate(q.get("statements", [])))
            cards.append(f"<div class='card tf' data-i='{i-1}'><div class='qtext'><b>Câu {i}.</b> {t}</div>{stmts}</div>")
        elif q.get("kind") == "short":
            cards.append(f"<div class='card' data-i='{i-1}'><div class='qtext'><b>Câu {i}.</b> {t}</div><input id='short{i}' class='field' placeholder='Nhập đáp án'></div>")
        else:
            cards.append(f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div><div class='small'>Câu tự luận/không hỗ trợ chấm tự động.</div></div>")
    score_js = """const DATA=%s;function score(){let right=0,total=0;DATA.forEach((q,i)=>{if(q.kind==='choice'){total++;const e=document.querySelector(`input[name=q${i+1}]:checked`);if(e&&Number(e.value)===Number(q.correct))right++;}else if(q.kind==='tf'){q.correct.forEach((c,j)=>{total++;const e=document.querySelector(`input[name=q${i+1}_${j}]:checked`);if(e&&Number(e.value)===(c?1:0))right++;});}else if(q.kind==='short'){total++;const e=document.getElementById(`short${i+1}`);if(e&&e.value.trim().toLowerCase()===String(q.answer||'').trim().toLowerCase())right++;}});const pct=total?right/total*10:0;document.getElementById('score').innerHTML=`✅ Đúng <b>${right}/${total}</b> · Điểm <b>${pct.toFixed(2)}</b>/10`;window.scrollTo({top:0,behavior:'smooth'});}""" % payload
    body = ("<div class='wrap'><div class='panel'><div class='mh'><span>📖 "
            + html.escape(Path(path).parent.name) + f" · <span class='tag {('vip' if level=='VIP' else 'free')}'>{level}</span></span>"
            + "<a class='btn' href='/member'>← Danh sách bài</a></div><div class='hero'><div id='score' class='score'>Làm xong bấm <b>Chấm điểm</b></div><button class='btn' onclick='score()'>📝 Chấm điểm</button></div>"
            + "<div class='cards'>" + "".join(cards) + "</div></div></div><script>" + score_js + "</script>")
    return page("Làm bài", body)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    msg = ""
    if request.method == "POST":
        if ADMIN_PASSWORD and request.form.get("password") == ADMIN_PASSWORD:
            session.clear(); session["role"] = "admin"; return redirect("/admin")
        msg = "Mật khẩu ADMIN không đúng."
    body = ("<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'>"
            "<div class='field'><label>Mật khẩu ADMIN</label><input name='password' type='password' required></div>"
            "<button class='btn'>Đăng nhập</button>" + f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>")
    return page("ADMIN", body)


@app.get("/admin/logout")
def admin_logout():
    session.clear(); return redirect("/admin/login")


@app.get("/admin")
@require_admin
def admin_home():
    data = load_members(); rows=[]
    for m in data.get("members",[]):
        typ=account_type(m)
        rows.append("<tr><td>"+html.escape(str(m.get("username") or ""))+"</td><td>"+html.escape(str(m.get("name") or ""))+"</td><td>"+html.escape(str(m.get("class") or ""))+"</td><td>"+html.escape(typ)+"</td><td>"+html.escape(str(m.get("status") or "ON"))+"</td><td>"
                     + f"<form method='post' action='/admin/member/type' style='display:inline'><input type='hidden' name='username' value='{html.escape(str(m.get('username') or ''), quote=True)}'><select name='account_type'><option {'selected' if typ=='FREE' else ''}>FREE</option><option {'selected' if typ=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu quyền</button></form>"
                     + f"<form method='post' action='/admin/member/toggle' style='display:inline'><input type='hidden' name='username' value='{html.escape(str(m.get('username') or ''), quote=True)}'><button class='btn'>Bật/Tắt</button></form></td></tr>")
    body = ("<div class='wrap'><div class='grid'><aside class='panel'><div class='head'>⚙️ ADMIN</div><div class='body'>"
            "<a class='btn' href='/admin'>👥 Thành viên</a><a class='btn' href='/admin/access'>🔐 Quyền FREE/VIP</a>"
            "<a class='btn' href='/github/quan-ly'>📚 Ngân hàng GitHub</a><a class='btn' href='/admin/logout'>Thoát</a>"
            "<hr><div class='small'>Nguồn câu hỏi: GitHub .tex<br>Quyền bài: lesson_access.json<br>Thành viên: members.json</div></div></aside>"
            "<main class='panel'><div class='mh'><span>👥 Thành viên</span><a class='btn' href='/admin/member/add'>+ Thêm</a></div><div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th><th>Thao tác</th></tr>"
            + "".join(rows) + "</table></div></main></div></div>")
    return page("Quản trị", body)


@app.route("/admin/member/add", methods=["GET", "POST"])
@require_admin
def admin_add():
    msg = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip(); name = (request.form.get("name") or "").strip(); cls = (request.form.get("class") or "").strip(); password = request.form.get("password") or ""; typ=(request.form.get("account_type") or "FREE").upper()
        data = load_members(); users={m.get("username") for m in data.get("members",[])}
        if not username or not password: msg="Thiếu tài khoản/mật khẩu."
        elif username in users: msg="Tài khoản đã tồn tại."
        else:
            data.setdefault("members",[]).append({"username":username,"name":name or username,"class":cls,"account_type":"VIP" if typ=="VIP" else "FREE","status":"ON","password_sha256":hashlib.sha256(password.encode()).hexdigest()})
            try: save_members(data); sync_members(data); return redirect('/admin')
            except Exception as exc: msg=str(exc)
    body=("<div class='wrap'><div class='panel login'><div class='head'>➕ Thêm thành viên</div><div class='body'><form method='post'>"
          "<div class='field'><label>Họ tên</label><input name='name'></div><div class='field'><label>Tài khoản</label><input name='username' required></div>"
          "<div class='field'><label>Lớp</label><input name='class'></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div>"
          "<div class='field'><label>Quyền</label><select name='account_type'><option>FREE</option><option>VIP</option></select></div>"
          "<button class='btn'>Lưu</button> <a class='btn' href='/admin'>Quay lại</a>"+f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>")
    return page("Thêm thành viên", body)


@app.post("/admin/member/type")
@require_admin
def admin_member_type():
    username=request.form.get("username",""); typ=(request.form.get("account_type") or "FREE").upper(); typ="VIP" if typ=="VIP" else "FREE"; data=load_members()
    for m in data.get("members",[]):
        if m.get("username")==username: m["account_type"]=typ; break
    save_members(data); sync_members(data); return redirect('/admin')


@app.post("/admin/member/toggle")
@require_admin
def admin_toggle():
    username=request.form.get("username",""); data=load_members()
    for m in data.get("members",[]):
        if m.get("username")==username: m["status"]="OFF" if m.get("status","ON")=="ON" else "ON"; break
    save_members(data); sync_members(data); return redirect('/admin')


@app.get("/admin/access")
@require_admin
def admin_access():
    idx=index_data(); acc=load_access(); rows=[]
    for item in idx.get("lessons",[]):
        if not isinstance(item,dict): continue
        path=str(item.get("path") or "")
        if not path.startswith("ngan-hang/"): continue
        level=str(acc.get("lessons",{}).get(path,acc.get("default","FREE"))).upper()
        title=str(item.get("BaiHoc") or item.get("De") or Path(path).parent.name)
        rows.append("<div class='card'><b>"+html.escape(title)+"</b><div class='small'>"+html.escape(path)+"</div><form method='post' action='/admin/access/save'><input type='hidden' name='path' value='"+html.escape(path,quote=True)+"'><select name='level'><option {'selected' if level=='FREE' else ''}>FREE</option><option {'selected' if level=='VIP' else ''}>VIP</option></select><button class='btn'>Lưu quyền</button><span class='tag '+('vip' if level=='VIP' else 'free')+'>'+level+'</span></form></div>")
    body=("<div class='wrap'><div class='panel'><div class='mh'><span>🔐 Quyền bài học FREE / VIP</span><a class='btn' href='/admin'>← ADMIN</a></div>"
          "<div class='hero'><div class='small'>FREE: tất cả thành viên · VIP: chỉ VIP</div></div><div class='cards'>"+"".join(rows)+"</div></div></div>")
    return page("Quyền bài học", body)


@app.post("/admin/access/save")
@require_admin
def admin_access_save():
    path=request.form.get("path",""); level=(request.form.get("level") or "FREE").upper(); level="VIP" if level=="VIP" else "FREE"; data=load_access(); data.setdefault("lessons",{})[path]=level; save_access(data); sync_access(data); return redirect('/admin/access')


@app.get("/github/quan-ly")
@require_admin
def github_manage():
    data=index_data(); cards=[]; acc=load_access()
    for item in data.get("lessons",[]):
        if not isinstance(item,dict): continue
        path=str(item.get("path") or "")
        if not path.startswith("ngan-hang/"): continue
        title=str(item.get("BaiHoc") or item.get("De") or Path(path).parent.name); count=int(item.get("questions") or item.get("count") or 0); level=str(acc.get("lessons",{}).get(path,acc.get("default","FREE"))).upper()
        cards.append("<div class='card'><b>"+html.escape(title)+"</b><div class='small'>"+html.escape(path)+f"</div><span class='tag {('vip' if level=='VIP' else 'free')}'>{level}</span><span class='tag'>{count} câu</span>"
                     + "<a class='btn' href='/admin/edit?path="+urllib.parse.quote(path,safe="")+"'>✏️ Đọc / sửa .tex</a></div>")
    body=("<div class='wrap'><div class='panel'><div class='mh'><span>📚 Ngân hàng GitHub</span><span>"+str(int(data.get('total_files') or 0))+" bài · "+str(int(data.get('total_questions') or 0))+" câu</span></div>"
          "<div class='hero'><a class='btn' href='/admin/access'>🔐 Phân quyền FREE/VIP</a></div><div class='cards'>"+"".join(cards)+"</div></div></div>")
    return page("Ngân hàng GitHub", body)


@app.get("/admin/edit")
@require_admin
def admin_edit():
    path=request.args.get("path","")
    try: sha,text=read_tex(path)
    except Exception as exc: return page("Lỗi", f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div></div></div></div>")
    body=("<div class='wrap'><div class='panel'><div class='mh'><b>✏️ "+html.escape(path)+"</b><a class='btn' href='/github/quan-ly'>← Mục lục</a></div>"
          "<textarea id='code' class='code'>"+html.escape(text)+"</textarea><div class='actions'><button class='btn' onclick='saveTex()'>💾 Lưu trực tiếp GitHub</button><a class='btn' href='https://github.com/"+html.escape(REPO)+"/blob/"+urllib.parse.quote(BRANCH)+"/"+urllib.parse.quote(path,safe='/')+"' target='_blank'>🐙 Mở GitHub</a><span id='msg'></span></div></div></div>"
          "<script>const path="+json.dumps(path,ensure_ascii=False)+",sha="+json.dumps(sha)+";async function saveTex(){const msg=document.getElementById('msg');msg.textContent='Đang lưu...';try{const r=await fetch('/admin/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,sha,text:document.getElementById('code').value})});const d=await r.json();msg.textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+(d.error||'Lỗi');}catch(e){msg.textContent='❌ '+e}}</script>")
    return page("Sửa .tex", body)


@app.post("/admin/api/save")
@require_admin
def admin_save():
    data=request.get_json(silent=True) or {}; path=data.get("path",""); text=data.get("text"); sha=data.get("sha","")
    if not isinstance(text,str) or not path.startswith("ngan-hang/") or not sha: return jsonify(ok=False,error="Thiếu path/text/sha"),400
    try:
        result=gh_put_file(path,text,"ADMIN cập nhật .tex trực tiếp",sha)
        return jsonify(ok=True,commit=str((result.get('commit') or {}).get('sha') or '')[:12])
    except Exception as exc:
        return jsonify(ok=False,error=str(exc)),500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
