# -*- coding: utf-8 -*-
"""
github_admin.py
Dashboard Flask nhỏ để đọc và quản lý GitHub repository.

Mục đích:
- Đọc branch / commit / file trực tiếp từ GitHub.
- Xem nội dung file.
- Xóa branch.
- Xóa file khỏi branch bằng GitHub API (tạo commit xóa file).
- Không lưu GitHub token trong mã nguồn.

Render Environment Variables:
    GITHUB_TOKEN=ghp_... hoặc fine-grained token
    GITHUB_REPO=pythonminh/luyen-de-vat-ly
    ADMIN_PASSWORD=<mat khau dashboard>
    PORT=<Render tự cấp>

Quyền token nên tối thiểu:
- Contents: Read and write
- Metadata: Read
Không cần cấp quyền không liên quan.

Chạy local:
    pip install -r requirements-github-admin.txt
    python github_admin.py

Chạy Render:
    gunicorn github_admin:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import wraps

from flask import Flask, request, redirect, url_for, session, render_template_string

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SESSION_SECRET", "change-this-secret")

GITHUB_TOKEN = (os.environ.get("GITHUB_TOKEN") or "").strip()
GITHUB_REPO = (os.environ.get("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
ADMIN_PASSWORD = (os.environ.get("ADMIN_PASSWORD") or "").strip()
GITHUB_API = "https://api.github.com"


def repo_parts():
    m = re.fullmatch(r"([^/]+)/([^/]+)", GITHUB_REPO)
    if not m:
        raise RuntimeError("GITHUB_REPO phải có dạng owner/repository")
    return m.group(1), m.group(2)


def gh_request(path: str, method: str = "GET", body=None):
    if not GITHUB_TOKEN:
        raise RuntimeError("Thiếu Environment Variable GITHUB_TOKEN trên Render.")

    url = GITHUB_API + path
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-admin-dashboard",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
            msg = detail.get("message", raw)
        except Exception:
            msg = raw
        raise RuntimeError(f"GitHub API {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Không kết nối được GitHub: {e}") from e


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_ok"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


def esc(v):
    return html.escape(str(v or ""), quote=True)


def flash_box(msg, error=False):
    if not msg:
        return ""
    cls = "error" if error else "ok"
    return f'<div class="{cls}">{esc(msg)}</div>'


STYLE = """
<style>
body{font-family:Arial,sans-serif;background:#f6f8fa;color:#24292f;margin:0}
.wrap{max-width:1250px;margin:24px auto;padding:0 18px}
.card{background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:18px;margin-bottom:16px}
h1,h2{margin-top:0}
nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
a,.btn{display:inline-block;padding:8px 12px;border:1px solid #d0d7de;border-radius:7px;text-decoration:none;background:#fff;color:#0969da;cursor:pointer}
.btn.danger{color:#cf222e;border-color:#cf222e;background:#fff}
.btn.green{color:#1a7f37;border-color:#1a7f37}
input,select{padding:9px;border:1px solid #d0d7de;border-radius:6px;width:100%;box-sizing:border-box}
table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid #d8dee4;padding:10px;text-align:left;vertical-align:top}
.code{white-space:pre-wrap;background:#f6f8fa;padding:14px;border-radius:7px;overflow:auto;max-height:650px}
.ok{padding:12px;background:#dafbe1;border:1px solid #1a7f37;border-radius:7px;margin-bottom:12px}
.error{padding:12px;background:#ffebe9;border:1px solid #cf222e;border-radius:7px;margin-bottom:12px}
.muted{color:#656d76}
.small{font-size:13px}
form.inline{display:inline}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.badge{background:#ddf4ff;border-radius:20px;padding:3px 8px;font-size:12px}
</style>
"""


LOGIN_HTML = STYLE + """
<div class="wrap" style="max-width:500px">
<div class="card">
<h1>GitHub Admin</h1>
<p class="muted">Đăng nhập quản trị repository</p>
<form method="post">
<label>Mật khẩu</label><br><br>
<input type="password" name="password" autofocus required><br><br>
<button class="btn green" type="submit">Đăng nhập</button>
</form>
{% if error %}<div class="error">{{error}}</div>{% endif %}
</div></div>
"""


HOME_HTML = STYLE + """
<div class="wrap">
<h1>GitHub Admin — {{repo}}</h1>
<nav>
<a href="{{url_for('home')}}">Tổng quan</a>
<a href="{{url_for('branches')}}">Branches</a>
<a href="{{url_for('commits')}}">Commits</a>
<a href="{{url_for('files_view')}}">Files</a>
<a href="{{url_for('logout')}}">Đăng xuất</a>
</nav>
{{message|safe}}
<div class="grid">
<div class="card"><h2>Repository</h2><b>{{repo}}</b><p class="muted">Nguồn dữ liệu: GitHub REST API</p></div>
<div class="card"><h2>Thao tác</h2><a class="btn" href="{{url_for('branches')}}">Quản lý branch</a></div>
<div class="card"><h2>File</h2><a class="btn" href="{{url_for('files_view')}}">Đọc / xóa file</a></div>
</div>
</div>
"""


BRANCHES_HTML = STYLE + """
<div class="wrap">
<h1>Branches — {{repo}}</h1>
<nav><a href="{{url_for('home')}}">Trang chủ</a><a href="{{url_for('commits')}}">Commits</a><a href="{{url_for('files_view')}}">Files</a><a href="{{url_for('logout')}}">Đăng xuất</a></nav>
{{message|safe}}
<div class="card">
<table>
<tr><th>Branch</th><th>SHA</th><th>Default</th><th>Thao tác</th></tr>
{% for b in branches %}
<tr>
<td><b>{{b.name}}</b></td>
<td class="small">{{b.sha}}</td>
<td>{% if b.default %}<span class="badge">default</span>{% endif %}</td>
<td>
{% if not b.default %}
<form class="inline" method="post" action="{{url_for('delete_branch')}}">
<input type="hidden" name="branch" value="{{b.name}}">
<button class="btn danger" type="submit" onclick="return confirm('XÓA branch {{b.name}} khỏi GitHub? Không thể hoàn tác bằng nút này.')">Xóa branch</button>
</form>
{% else %}<span class="muted">Không cho xóa main</span>{% endif %}
</td>
</tr>
{% endfor %}
</table>
</div>
</div>
"""


COMMITS_HTML = STYLE + """
<div class="wrap">
<h1>Commits — {{repo}}</h1>
<nav><a href="{{url_for('home')}}">Trang chủ</a><a href="{{url_for('branches')}}">Branches</a><a href="{{url_for('files_view')}}">Files</a><a href="{{url_for('logout')}}">Đăng xuất</a></nav>
<div class="card">
<form method="get">
<label>Branch</label><br><br>
<select name="branch">{% for b in branches %}<option {% if b==branch %}selected{% endif %}>{{b}}</option>{% endfor %}</select><br><br>
<button class="btn" type="submit">Đọc commits</button>
</form>
</div>
<div class="card">
<table>
<tr><th>SHA</th><th>Ngày</th><th>Thông điệp</th><th>Tác giả</th></tr>
{% for c in commits %}
<tr>
<td><a href="{{c.html_url}}" target="_blank">{{c.sha7}}</a></td>
<td class="small">{{c.date}}</td>
<td>{{c.message}}</td>
<td>{{c.author}}</td>
</tr>
{% endfor %}
</table>
</div>
</div>
"""


FILES_HTML = STYLE + """
<div class="wrap">
<h1>Files — {{repo}}</h1>
<nav><a href="{{url_for('home')}}">Trang chủ</a><a href="{{url_for('branches')}}">Branches</a><a href="{{url_for('commits')}}">Commits</a><a href="{{url_for('logout')}}">Đăng xuất</a></nav>
{{message|safe}}
<div class="card">
<form method="get">
<label>Branch</label><br><br>
<select name="branch">{% for b in branches %}<option {% if b==branch %}selected{% endif %}>{{b}}</option>{% endfor %}</select><br><br>
<label>Đường dẫn thư mục</label><br><br>
<input name="path" value="{{path}}" placeholder="ví dụ: data/json_questions"><br><br>
<button class="btn" type="submit">Đọc</button>
</form>
</div>
<div class="card">
<table>
<tr><th>Tên</th><th>Loại</th><th>Thao tác</th></tr>
{% for f in files %}
<tr>
<td>{{f.name}}</td>
<td>{{f.type}}</td>
<td>
{% if f.type == 'file' %}
<a class="btn" href="{{url_for('read_file', branch=branch, path=f.path)}}">Đọc</a>
<form class="inline" method="post" action="{{url_for('delete_file')}}">
<input type="hidden" name="branch" value="{{branch}}">
<input type="hidden" name="path" value="{{f.path}}">
<button class="btn danger" type="submit" onclick="return confirm('XÓA FILE {{f.path}} và tạo commit xóa trên GitHub?')">Xóa</button>
</form>
{% else %}
<a class="btn" href="{{url_for('files_view', branch=branch, path=f.path)}}">Mở</a>
{% endif %}
</td>
</tr>
{% endfor %}
</table>
</div>
</div>
"""


READ_FILE_HTML = STYLE + """
<div class="wrap">
<h1>Đọc file</h1>
<nav><a href="{{url_for('files_view', branch=branch)}}">Quay lại Files</a><a href="{{url_for('branches')}}">Branches</a><a href="{{url_for('logout')}}">Đăng xuất</a></nav>
<div class="card">
<p><b>Branch:</b> {{branch}}</p>
<p><b>Path:</b> {{path}}</p>
<p><b>SHA:</b> {{sha}}</p>
</div>
<div class="card">
<div class="code">{{content}}</div>
</div>
</div>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not ADMIN_PASSWORD:
            return render_template_string(LOGIN_HTML, error="Thiếu ADMIN_PASSWORD trên Render.")
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["admin_ok"] = True
            return redirect(request.args.get("next") or url_for("home"))
        return render_template_string(LOGIN_HTML, error="Sai mật khẩu.")
    return render_template_string(LOGIN_HTML, error="")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    try:
        owner, repo = repo_parts()
        data = gh_request(f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}")
        msg = f'<div class="card"><b>{esc(data.get("full_name"))}</b><br>{esc(data.get("description"))}</div>'
        return render_template_string(HOME_HTML, repo=GITHUB_REPO, message=msg)
    except Exception as e:
        return render_template_string(HOME_HTML, repo=GITHUB_REPO, message=flash_box(str(e), True))


def get_branches():
    owner, repo = repo_parts()
    repo_q = urllib.parse.quote(repo, safe="")
    owner_q = urllib.parse.quote(owner, safe="")
    out = []
    page = 1
    while page <= 10:
        arr = gh_request(f"/repos/{owner_q}/{repo_q}/branches?per_page=100&page={page}")
        if not arr:
            break
        for b in arr:
            out.append({
                "name": b["name"],
                "sha": b["commit"]["sha"],
                "default": False,
            })
        if len(arr) < 100:
            break
        page += 1

    repo_info = gh_request(f"/repos/{owner_q}/{repo_q}")
    default = repo_info.get("default_branch", "main")
    for b in out:
        b["default"] = b["name"] == default
    return out


@app.route("/branches")
@login_required
def branches():
    try:
        bs = get_branches()
        msg = flash_box(request.args.get("msg", ""))
        return render_template_string(BRANCHES_HTML, repo=GITHUB_REPO, branches=bs, message=msg)
    except Exception as e:
        return render_template_string(BRANCHES_HTML, repo=GITHUB_REPO, branches=[], message=flash_box(str(e), True))


@app.route("/branches/delete", methods=["POST"])
@login_required
def delete_branch():
    branch = (request.form.get("branch") or "").strip()
    if not branch:
        return redirect(url_for("branches", msg="Thiếu branch."))

    try:
        bs = get_branches()
        target = next((b for b in bs if b["name"] == branch), None)
        if not target:
            raise RuntimeError("Không tìm thấy branch.")
        if target["default"]:
            raise RuntimeError("Không cho xóa default branch.")

        owner, repo = repo_parts()
        owner_q = urllib.parse.quote(owner, safe="")
        repo_q = urllib.parse.quote(repo, safe="")
        branch_q = urllib.parse.quote(branch, safe="")
        gh_request(f"/repos/{owner_q}/{repo_q}/git/refs/heads/{branch_q}", method="DELETE")
        return redirect(url_for("branches", msg=f"Đã xóa branch: {branch}"))
    except Exception as e:
        return redirect(url_for("branches", msg=f"Lỗi: {e}"))


@app.route("/commits")
@login_required
def commits():
    try:
        bs = get_branches()
        names = [b["name"] for b in bs]
        branch = request.args.get("branch") or next((b["name"] for b in bs if b["default"]), "main")
        owner, repo = repo_parts()
        owner_q = urllib.parse.quote(owner, safe="")
        repo_q = urllib.parse.quote(repo, safe="")
        branch_q = urllib.parse.quote(branch, safe="")
        arr = gh_request(f"/repos/{owner_q}/{repo_q}/commits?sha={branch_q}&per_page=50")
        out = []
        for c in arr:
            commit = c.get("commit", {})
            author = commit.get("author") or {}
            out.append({
                "sha7": c.get("sha", "")[:7],
                "date": author.get("date", ""),
                "message": (commit.get("message") or "").splitlines()[0][:180],
                "author": author.get("name") or "",
                "html_url": c.get("html_url") or "#",
            })
        return render_template_string(COMMITS_HTML, repo=GITHUB_REPO, branches=names, branch=branch, commits=out)
    except Exception as e:
        return render_template_string(COMMITS_HTML, repo=GITHUB_REPO, branches=[], branch="", commits=[], message=flash_box(str(e), True))


@app.route("/files")
@login_required
def files_view():
    try:
        bs = get_branches()
        names = [b["name"] for b in bs]
        branch = request.args.get("branch") or next((b["name"] for b in bs if b["default"]), "main")
        path = (request.args.get("path") or "").strip().strip("/")
        owner, repo = repo_parts()
        owner_q = urllib.parse.quote(owner, safe="")
        repo_q = urllib.parse.quote(repo, safe="")
        branch_q = urllib.parse.quote(branch, safe="")
        path_q = urllib.parse.quote(path, safe="/")
        data = gh_request(f"/repos/{owner_q}/{repo_q}/contents/{path_q}?ref={branch_q}")
        if isinstance(data, dict):
            data = [data]
        files = []
        for f in data:
            files.append({"name": f.get("name"), "type": f.get("type"), "path": f.get("path")})
        return render_template_string(
            FILES_HTML, repo=GITHUB_REPO, branches=names, branch=branch,
            path=path, files=files, message=""
        )
    except Exception as e:
        return render_template_string(
            FILES_HTML, repo=GITHUB_REPO, branches=[], branch="", path="", files=[],
            message=flash_box(str(e), True)
        )


@app.route("/file")
@login_required
def read_file():
    branch = (request.args.get("branch") or "main").strip()
    path = (request.args.get("path") or "").strip().strip("/")
    if not path:
        return redirect(url_for("files_view", branch=branch))

    try:
        owner, repo = repo_parts()
        owner_q = urllib.parse.quote(owner, safe="")
        repo_q = urllib.parse.quote(repo, safe="")
        path_q = urllib.parse.quote(path, safe="/")
        branch_q = urllib.parse.quote(branch, safe="")
        data = gh_request(f"/repos/{owner_q}/{repo_q}/contents/{path_q}?ref={branch_q}")
        if data.get("type") != "file":
            raise RuntimeError("Đây không phải file.")

        raw = base64.b64decode((data.get("content") or "").replace("\n", ""))
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = f"[File nhị phân, {len(raw)} bytes — không hiển thị text]"
        return render_template_string(
            READ_FILE_HTML, branch=branch, path=path,
            sha=data.get("sha", ""), content=content
        )
    except Exception as e:
        return render_template_string(
            READ_FILE_HTML, branch=branch, path=path, sha="",
            content=f"LỖI: {e}"
        )


@app.route("/files/delete", methods=["POST"])
@login_required
def delete_file():
    branch = (request.form.get("branch") or "").strip()
    path = (request.form.get("path") or "").strip().strip("/")
    if not branch or not path:
        return redirect(url_for("files_view", branch=branch, msg="Thiếu branch/path."))

    try:
        owner, repo = repo_parts()
        owner_q = urllib.parse.quote(owner, safe="")
        repo_q = urllib.parse.quote(repo, safe="")
        path_q = urllib.parse.quote(path, safe="/")
        branch_q = urllib.parse.quote(branch, safe="")

        # Lấy SHA hiện tại của file trước khi DELETE.
        data = gh_request(f"/repos/{owner_q}/{repo_q}/contents/{path_q}?ref={branch_q}")
        if data.get("type") != "file":
            raise RuntimeError("Chỉ hỗ trợ xóa file, không xóa thư mục.")
        sha = data.get("sha")
        if not sha:
            raise RuntimeError("GitHub không trả về SHA của file.")

        # Không cho xóa file nếu đang ở default branch qua dashboard này.
        bs = get_branches()
        target = next((b for b in bs if b["name"] == branch), None)
        if target and target["default"]:
            raise RuntimeError("Để an toàn, dashboard không cho xóa file trực tiếp trên default branch. Hãy xóa/sửa qua branch riêng rồi merge.")

        gh_request(
            f"/repos/{owner_q}/{repo_q}/contents/{path_q}",
            method="DELETE",
            body={
                "message": f"Delete {path}",
                "sha": sha,
                "branch": branch,
            },
        )
        return redirect(url_for("files_view", branch=branch, msg=f"Đã xóa file {path} và tạo commit trên branch {branch}."))
    except Exception as e:
        return redirect(url_for("files_view", branch=branch, msg=f"Lỗi: {e}"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
