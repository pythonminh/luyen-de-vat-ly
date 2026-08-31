# -*- coding: utf-8 -*-
"""Small, single-purpose GitHub portal for members and ADMIN."""
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

from flask import Flask, Response, redirect, request, session

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET", "change-this-on-render")
REPO = os.getenv("GITHUB_REPO", "pythonminh/luyen-de-vat-ly").strip()
BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "bank_index.json"
MEMBERS = ROOT / "members.json"
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
QRE = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
DRE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)

CSS = """
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial}.top{background:#1769d2;color:#fff;padding:10px 16px}.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #bdd5f4;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin:3px}.nav a{background:transparent;color:#fff;border-color:#ffffff66}.wrap{max-width:1450px;margin:auto;padding:12px}.grid{display:grid;grid-template-columns:260px 1fr;gap:10px}.panel{background:#fff;border:1px solid #d6e0ea;border-radius:12px;overflow:hidden}.head{padding:10px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.body{padding:10px}.field{margin-bottom:8px}.field label{display:block;font-size:10px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;display:flex;justify-content:space-between;gap:8px;font-weight:900}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:7px;padding:8px}.card{border:1px solid #dce5ed;border-radius:9px;padding:9px}.small{font-size:10px;color:#64748b}.tag{display:inline-block;padding:3px 6px;border:1px solid #cbd5e1;border-radius:999px;font-size:9px;margin:4px 3px 0 0}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:7px;border-bottom:1px solid #e5e7eb;text-align:left}.login{max-width:420px;margin:70px auto}.hero{padding:16px;text-align:center}.code{width:100%;height:70vh;resize:vertical;border:1px solid #cbd5e1;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.actions{padding:0 10px 10px}.ok{color:#15803d;font-weight:800}.err{color:#b91c1c;font-weight:800}@media(max-width:800px){.grid{grid-template-columns:1fr}.login{margin:25px auto}}
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
        msg = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(msg).get("message", msg)
        except Exception:
            pass
        raise RuntimeError(f"GitHub API {e.code}: {msg}") from e


def index_data():
    if INDEX.exists():
        return json.loads(INDEX.read_text(encoding="utf-8"))
    owner, repo = REPO.split("/", 1)
    url = f"{RAW}/{owner}/{repo}/{urllib.parse.quote(BRANCH)}/bank_index.json"
    with urllib.request.urlopen(url, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))


def safe_tex(path):
    return (
        isinstance(path, str)
        and path.startswith("ngan-hang/")
        and path.lower().endswith(".tex")
        and ".." not in path
    )


def read_tex(path):
    if not safe_tex(path):
        raise ValueError("Đường dẫn .tex không hợp lệ")
    owner, repo = REPO.split("/", 1)
    api_path = (
        f"/repos/{owner}/{repo}/contents/"
        f"{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(BRANCH)}"
    )
    data = gh(api_path)
    text = base64.b64decode((data.get("content") or "").replace("\n", "")).decode(
        "utf-8", "replace"
    )
    return data.get("sha", ""), text


def load_members():
    try:
        return json.loads(MEMBERS.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": 1, "members": []}


def save_members(data):
    MEMBERS.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def gh_save_members(data):
    owner, repo = REPO.split("/", 1)
    path = "members.json"
    current = gh(f"/repos/{owner}/{repo}/contents/{path}?ref={urllib.parse.quote(BRANCH)}")
    content = base64.b64encode(
        (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    ).decode("ascii")
    gh(
        f"/repos/{owner}/{repo}/contents/{path}",
        "PUT",
        {
            "message": "Admin cập nhật thành viên",
            "content": content,
            "branch": BRANCH,
            "sha": current.get("sha"),
        },
    )


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
        return view(*args, **kwargs)
    return wrapped


def page(title, body):
    return Response(
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        "<body><div class='top'><div class='row'>"
        "<div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div>"
        "<div class='sub'>Nguồn chính: GitHub / ngan-hang/*.tex</div></div>"
        "<div class='nav'><a href='/member'>Thành viên</a>"
        "<a href='/admin'>ADMIN</a><a href='/github/repo' target='_blank'>🐙 GitHub</a>"
        "</div></div></div>" + body + "</body></html>",
        mimetype="text/html",
    )


@app.get("/")
def root():
    return redirect("/member")


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
            if (
                m.get("username") == username
                and m.get("password_sha256") == wanted
                and m.get("status", "ON") == "ON"
            ):
                session.clear()
                session.update(role="member", username=username, name=m.get("name") or username)
                return redirect("/member")
        msg = "Sai tài khoản hoặc mật khẩu."
    body = (
        "<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div>"
        "<div class='body'><form method='post'>"
        "<div class='field'><label>Tài khoản</label><input name='username' required></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div>"
        "<button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a>"
        f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>"
    )
    return page("Đăng nhập", body)


@app.route("/member/register", methods=["GET", "POST"])
def member_register():
    msg = ""
    ok = ""
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
            data.setdefault("members", []).append(
                {
                    "username": username,
                    "name": name or username,
                    "class": "",
                    "status": "ON",
                    "password_sha256": hashlib.sha256(password.encode()).hexdigest(),
                }
            )
            try:
                save_members(data)
                gh_save_members(data)
                ok = "Đăng ký thành công."
            except Exception as exc:
                msg = str(exc)
    body = (
        "<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký thành viên</div>"
        "<div class='body'><form method='post'>"
        "<div class='field'><label>Tên</label><input name='name'></div>"
        "<div class='field'><label>Tài khoản</label><input name='username' required></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div>"
        "<button class='btn'>Tạo tài khoản</button> <a class='btn' href='/member/login'>Quay lại</a>"
        f"<div class='err'>{html.escape(msg)}</div><div class='ok'>{html.escape(ok)}</div>"
        "</form></div></div></div>"
    )
    return page("Đăng ký", body)


@app.get("/member/logout")
def member_logout():
    session.clear()
    return redirect("/member/login")


@app.get("/member")
@require_member
def member_home():
    data = index_data()
    cards = []
    for item in data.get("lessons", []):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        if not safe_tex(path):
            continue
        title = str(item.get("BaiHoc") or item.get("De") or Path(path).parent.name)
        count = int(item.get("questions") or item.get("count") or 0)
        cards.append(
            "<div class='card'><b>"
            + html.escape(title)
            + f"</b><div class='small'>{html.escape(str(item.get('Mon') or ''))} · "
            + html.escape(str(item.get('Lop') or ''))
            + "</div><div><span class='tag'>"
            + str(count)
            + " câu</span></div><a class='btn' href='/member/lesson?path="
            + urllib.parse.quote(path, safe="")
            + "'>Làm bài</a></div>"
        )
    body = (
        "<div class='wrap'><div class='panel'><div class='mh'><span>👤 Xin chào "
        + html.escape(str(session.get("name") or session.get("username")))
        + "</span><a class='btn' href='/member/logout'>Thoát</a></div>"
        "<div class='hero'><h2>Chọn bài để học</h2><div class='small'>"
        + str(int(data.get("total_files") or len(cards)))
        + " bài · "
        + str(int(data.get("total_questions") or 0))
        + " câu</div></div><div class='cards'>"
        + "".join(cards)
        + "</div></div></div>"
    )
    return page("Thành viên", body)


@app.get("/member/lesson")
@require_member
def member_lesson():
    path = request.args.get("path", "")
    _, text = read_tex(path)
    qs = QRE.findall(text)
    items = []
    for i, q in enumerate(qs, 1):
        items.append(
            "<div class='card'><b>Câu "
            + str(i)
            + "</b><pre style='white-space:pre-wrap;font:12px Consolas'>"
            + html.escape(q)
            + "</pre></div>"
        )
    body = (
        "<div class='wrap'><div class='panel'><div class='mh'><span>📖 "
        + html.escape(Path(path).parent.name)
        + "</span><a class='btn' href='/member'>← Danh sách bài</a></div>"
        "<div class='cards'>"
        + "".join(items)
        + "</div></div></div>"
    )
    return page("Làm bài", body)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    msg = ""
    if request.method == "POST" and ADMIN_PASSWORD and request.form.get("password") == ADMIN_PASSWORD:
        session.clear()
        session["role"] = "admin"
        return redirect("/admin")
    if request.method == "POST":
        msg = "Mật khẩu ADMIN không đúng."
    body = (
        "<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div><div class='body'>"
        "<form method='post'><div class='field'><label>Mật khẩu ADMIN</label>"
        "<input name='password' type='password' required></div><button class='btn'>Đăng nhập</button>"
        f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>"
    )
    return page("ADMIN", body)


@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")


@app.get("/admin")
@require_admin
def admin_home():
    data = load_members()
    rows = []
    for m in data.get("members", []):
        rows.append(
            "<tr><td>"
            + html.escape(str(m.get("username") or ""))
            + "</td><td>"
            + html.escape(str(m.get("name") or ""))
            + "</td><td>"
            + html.escape(str(m.get("class") or ""))
            + "</td><td>"
            + html.escape(str(m.get("status") or "ON"))
            + "</td><td><form method='post' action='/admin/member/toggle'>"
            + "<input type='hidden' name='username' value='"
            + html.escape(str(m.get("username") or ""), quote=True)
            + "'><button class='btn'>Bật/Tắt</button></form></td></tr>"
        )
    body = (
        "<div class='wrap'><div class='grid'><aside class='panel'><div class='head'>⚙️ ADMIN</div>"
        "<div class='body'><a class='btn' href='/admin'>Thành viên</a>"
        "<a class='btn' href='/github/quan-ly'>Ngân hàng câu hỏi</a>"
        "<a class='btn' href='/admin/member/add'>+ Thêm</a>"
        "<a class='btn' href='/admin/logout'>Thoát</a></div></aside>"
        "<main class='panel'><div class='mh'><span>👥 Danh sách thành viên</span></div>"
        "<div class='body'><table class='table'><tr><th>Tài khoản</th><th>Tên</th><th>Lớp</th>"
        "<th>Trạng thái</th><th></th></tr>"
        + "".join(rows)
        + "</table></div></main></div></div>"
    )
    return page("Quản trị", body)


@app.route("/admin/member/add", methods=["GET", "POST"])
@require_admin
def admin_add():
    msg = ""
    ok = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        name = (request.form.get("name") or "").strip()
        cls = (request.form.get("class") or "").strip()
        password = request.form.get("password") or ""
        data = load_members()
        users = {m.get("username") for m in data.get("members", [])}
        if username in users:
            msg = "Tài khoản đã tồn tại."
        elif not username or not password:
            msg = "Thiếu tài khoản hoặc mật khẩu."
        else:
            data.setdefault("members", []).append(
                {
                    "username": username,
                    "name": name or username,
                    "class": cls,
                    "status": "ON",
                    "password_sha256": hashlib.sha256(password.encode()).hexdigest(),
                }
            )
            try:
                save_members(data)
                gh_save_members(data)
                ok = "Đã thêm thành viên."
            except Exception as exc:
                msg = str(exc)
    body = (
        "<div class='wrap'><div class='panel login'><div class='head'>➕ Thêm thành viên</div><div class='body'>"
        "<form method='post'><div class='field'><label>Tên</label><input name='name'></div>"
        "<div class='field'><label>Tài khoản</label><input name='username' required></div>"
        "<div class='field'><label>Lớp</label><input name='class'></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div>"
        "<button class='btn'>Lưu</button> <a class='btn' href='/admin'>Quay lại</a>"
        f"<div class='err'>{html.escape(msg)}</div><div class='ok'>{html.escape(ok)}</div></form>"
        "</div></div></div>"
    )
    return page("Thêm thành viên", body)


@app.post("/admin/member/toggle")
@require_admin
def admin_toggle():
    username = request.form.get("username", "")
    data = load_members()
    for m in data.get("members", []):
        if m.get("username") == username:
            m["status"] = "OFF" if m.get("status", "ON") == "ON" else "ON"
            break
    save_members(data)
    gh_save_members(data)
    return redirect("/admin")


@app.get("/github/quan-ly")
@require_admin
def github_manage():
    data = index_data()
    cards = []
    for item in data.get("lessons", []):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        if not safe_tex(path):
            continue
        title = str(item.get("BaiHoc") or item.get("De") or Path(path).parent.name)
        count = int(item.get("questions") or item.get("count") or 0)
        cards.append(
            "<div class='card'><b>"
            + html.escape(title)
            + "</b><div class='small'>"
            + html.escape(path)
            + f"</div><span class='tag'>{count} câu</span>"
            + "<a class='btn' href='/admin/edit?path="
            + urllib.parse.quote(path, safe="")
            + "'>✏️ Mở / sửa .tex</a></div>"
        )
    body = (
        "<div class='wrap'><div class='panel'><div class='mh'><span>📚 Mục lục GitHub</span>"
        + "<span>"
        + str(int(data.get("total_files") or len(cards)))
        + " bài · "
        + str(int(data.get("total_questions") or 0))
        + " câu</span></div><div class='cards'>"
        + "".join(cards)
        + "</div></div></div>"
    )
    return page("Ngân hàng GitHub", body)


@app.get("/admin/edit")
@require_admin
def admin_edit():
    path = request.args.get("path", "")
    sha, text = read_tex(path)
    body = (
        "<div class='wrap'><div class='panel'><div class='mh'><b>✏️ "
        + html.escape(path)
        + "</b><a class='btn' href='/github/quan-ly'>← Mục lục</a></div>"
        "<textarea id='code' class='code'>"
        + html.escape(text)
        + "</textarea><div class='actions'><button class='btn' onclick='saveTex()'>💾 Lưu GitHub</button>"
        "<span id='msg'></span></div></div></div>"
        "<script>const path="
        + json.dumps(path, ensure_ascii=False)
        + ",sha="
        + json.dumps(sha)
        + ";async function saveTex(){const msg=document.getElementById('msg');"
        "msg.textContent='Đang lưu...';try{const r=await fetch('/admin/api/save',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:JSON.stringify({path,sha,text:document.getElementById('code').value})});"
        "const d=await r.json();msg.textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+(d.error||'Lỗi');"
        "}catch(e){msg.textContent='❌ '+e}}</script>"
    )
    return page("Sửa .tex", body)


@app.post("/admin/api/save")
@require_admin
def admin_save():
    data = request.get_json(silent=True) or {}
    path = data.get("path", "")
    text = data.get("text")
    sha = data.get("sha", "")
    if not safe_tex(path) or not isinstance(text, str) or not sha:
        return {"ok": False, "error": "Thiếu path/text/sha"}, 400
    owner, repo = REPO.split("/", 1)
    api_path = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}"
    result = gh(
        api_path,
        "PUT",
        {
            "message": "ADMIN cập nhật .tex trực tiếp",
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "branch": BRANCH,
            "sha": sha,
        },
    )
    return {"ok": True, "commit": str((result.get("commit") or {}).get("sha") or "")[:12]}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
