# -*- coding: utf-8 -*-
"""Single authoritative Render entry point.

Keeps one UI/auth policy and never rewrites LaTeX/JSON embedded inside the
student-practice JavaScript.
"""
from __future__ import annotations

import hashlib
import html
import os
import re
from datetime import timedelta

from flask import redirect, request, session

import app as base
import wsgi
import admin_manager  # noqa: F401

app = wsgi.app

BRAND = "📚 Luyện Đề Toán Lý"
CONTACT = "Zalo thầy Minh 0946111107"
ADMIN_USERNAME = (os.getenv("ADMIN_USERNAME") or "ADMIN").strip() or "ADMIN"
ADMIN_PASSWORD = (os.getenv("ADMIN_PASSWORD") or "").strip()
ADMIN_PASSWORD_SHA256 = (os.getenv("ADMIN_PASSWORD_SHA256") or "").strip().lower()


def _admin_password_ok(raw: str) -> bool:
    if ADMIN_PASSWORD:
        return raw == ADMIN_PASSWORD
    if ADMIN_PASSWORD_SHA256:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest().lower() == ADMIN_PASSWORD_SHA256
    return False


def _display_name() -> str:
    try:
        m = base.member_current()
        if m:
            return str(m.get("name") or m.get("username") or "Học viên")
    except Exception:
        pass
    return str(session.get("name") or session.get("username") or "Học viên")


def _nav() -> str:
    links = ["<a href='/member'>📚 Mục lục</a>"]
    role = session.get("role")
    if role == "admin":
        links += [
            "<a href='/admin'>🔐 ADMIN</a>",
            "<a href='https://github.com/pythonminh/luyen-de-vat-ly' target='_blank' rel='noopener'>🐙 GitHub</a>",
            "<a href='/admin/logout'>🚪 Thoát</a>",
        ]
    elif role == "member":
        links += [
            f"<span class='user-pill'>👤 {html.escape(_display_name())}</span>",
            "<a href='/member/logout'>🚪 Thoát</a>",
        ]
    else:
        links += [
            "<a href='/member/login'>🔑 Đăng nhập / Đăng ký</a>",
            "<a href='/admin/login'>🔐 ADMIN</a>",
        ]
    return "<div class='nav'>" + "".join(links) + "</div>"


def _replace_top(body: str) -> str:
    header = (
        "<div class='top'><div class='topin'>"
        "<div><div class='brand'>" + BRAND + "</div>"
        "<div class='sub'>" + CONTACT + "</div></div>"
        + _nav()
        + "</div></div>"
    )
    body = re.sub(
        r"<div\s+class=['\"]top['\"]>.*?</div>\s*(?=<div\s+class=['\"]wrap['\"]>)",
        header, body, count=1, flags=re.I | re.S,
    )
    if "class='top'" not in body and 'class="top"' not in body:
        body = re.sub(r"<body[^>]*>", lambda m: m.group(0) + header, body, count=1, flags=re.I)
    return body


def _clean_html(body: str) -> str:
    body = _replace_top(body)
    body = re.sub(r"<div\s+class=['\"]nav['\"]>.*?</div>", _nav(), body, count=1, flags=re.I | re.S)

    if session.get("role") != "admin":
        body = re.sub(
            r"<a\b[^>]*href=['\"][^'\"]*(?:github\.com|/github(?:/|['\"]))[^'\"]*['\"][^>]*>.*?</a>",
            "", body, flags=re.I | re.S,
        )
        body = re.sub(r"<button\b[^>]*>\s*(?:🐙\s*)?GitHub\s*</button>", "", body, flags=re.I | re.S)

    for old in (
        "📚 Ngân hàng câu hỏi GitHub",
        "Ngân hàng câu hỏi GitHub",
        "📚 Ngân hàng GitHub",
        "Ngân hàng GitHub",
        "📚 Luyện đề AI · Thầy Minh",
        "Luyện đề AI · Thầy Minh",
    ):
        body = body.replace(old, BRAND)
    body = re.sub(r"MỤC LỤC\s*[·•|]\s*GitHub", "MỤC LỤC", body, flags=re.I)
    body = re.sub(
        r"Nguồn đề:\s*bank_index\.json\s*\+\s*ngan-hang/\\?\*\.tex\s*(?:·|•|\|)\s*Google Sheet không dùng cho đề",
        CONTACT, body, flags=re.I,
    )

    if (request.path.startswith("/member") or request.path == "/") and request.path != "/member/practice":
        body = re.sub(r"\\begin\s*\{\s*ex\s*\}", "", body, flags=re.I)
        body = re.sub(r"\\end\s*\{\s*ex\s*\}", "", body, flags=re.I)
        body = re.sub(r"%\s*ID\s*:\s*[^%<\r\n]+", "", body, flags=re.I)
        body = re.sub(r"%\s*Mức\s*:\s*[^%<\r\n]+", "", body, flags=re.I)
    return body


_original_parse_questions = base.parse_questions


def _fixed_parse_questions(tex: str):
    qs = _original_parse_questions(tex)
    for q in qs:
        text = str(q.get("text") or "")
        text = re.sub(
            r"^\s*\\begin\s*\{\s*ex\s*\}\s*%\s*ID\s*:\s*[^%\r\n]*%\s*Mức\s*:\s*\S+\s*",
            "", text, count=1, flags=re.I,
        )
        text = re.sub(r"^\s*\\begin\s*\{\s*ex\s*\}\s*", "", text, count=1, flags=re.I)
        text = re.sub(r"\\end\s*\{\s*ex\s*\}\s*$", "", text, count=1, flags=re.I)
        q["text"] = text.strip()
    return qs


base.parse_questions = _fixed_parse_questions
_original_page = base.page


def authoritative_page(title: str, body: str):
    response = _original_page(title, body)
    if "text/html" in response.headers.get("Content-Type", ""):
        response.set_data(_clean_html(response.get_data(as_text=True)))
    return response


base.page = authoritative_page
try:
    admin_manager.page = authoritative_page
except Exception:
    pass


# ---------------------------------------------------------------------------
# ONE member authentication page: login + registration in the same card.
# Password is never stored in localStorage. Browser password managers can save
# it through autocomplete attributes; the optional Remember login stores only
# the username locally and makes the Flask session persistent for 30 days.
# ---------------------------------------------------------------------------
_original_member_login = app.view_functions.get("member_login")
_original_member_register = app.view_functions.get("member_register")


def _member_lookup(username: str, password: str):
    h = hashlib.sha256(password.encode("utf-8")).hexdigest()
    for m in base.members_data().get("members", []):
        if m.get("username") == username and m.get("status", "ON") == "ON" and m.get("password_sha256") == h:
            return m
    return None


def _auth_page(msg: str = "", mode: str = "login", values=None):
    values = values or {}
    username = html.escape(str(values.get("username", "")), quote=True)
    name = html.escape(str(values.get("name", "")), quote=True)
    cls = html.escape(str(values.get("class", "")), quote=True)
    err = f"<div class='err authmsg'>{html.escape(msg)}</div>" if msg else "<div class='authmsg'></div>"
    login_active = " active" if mode == "login" else ""
    reg_active = " active" if mode == "register" else ""
    body = f"""
<div class='wrap'><div class='panel authpanel'>
  <div class='head'>👤 Tài khoản học viên</div>
  <div class='body'>
    <div class='authtabs'>
      <button type='button' class='authtab{login_active}' onclick=\"authMode('login')\">🔑 Đăng nhập</button>
      <button type='button' class='authtab{reg_active}' onclick=\"authMode('register')\">📝 Đăng ký</button>
    </div>

    <form id='loginForm' class='authform' method='post' action='/member/login' style='display:{'block' if mode == 'login' else 'none'}'>
      <input type='hidden' name='action' value='login'>
      <div class='field'><label>Tài khoản</label><input id='loginUsername' name='username' value='{username}' autocomplete='username' required></div>
      <div class='field'><label>Mật khẩu</label><div class='passrow'><input id='loginPassword' name='password' type='password' autocomplete='current-password' required><button type='button' class='eye' onclick=\"togglePass('loginPassword',this)\">👁</button></div></div>
      <label class='check'><input id='remember' name='remember' type='checkbox'> Ghi nhớ đăng nhập trên thiết bị này</label>
      <button class='btn primary authsubmit' type='submit'>Đăng nhập</button>
      {err if mode == 'login' else ''}
    </form>

    <form id='registerForm' class='authform' method='post' action='/member/login' style='display:{'block' if mode == 'register' else 'none'}'>
      <input type='hidden' name='action' value='register'>
      <div class='field'><label>Họ tên</label><input id='regName' name='name' value='{name}' autocomplete='name'></div>
      <div class='field'><label>Tài khoản</label><input id='regUsername' name='username' value='{username}' autocomplete='username' required></div>
      <div class='field'><label>Mật khẩu</label><div class='passrow'><input id='regPassword' name='password' type='password' autocomplete='new-password' required><button type='button' class='eye' onclick=\"togglePass('regPassword',this)\">👁</button></div></div>
      <div class='field'><label>Nhập lại mật khẩu</label><div class='passrow'><input id='regPassword2' name='password2' type='password' autocomplete='new-password' required><button type='button' class='eye' onclick=\"togglePass('regPassword2',this)\">👁</button></div></div>
      <div class='field'><label>Lớp <span class='muted'>(không bắt buộc)</span></label><input name='class' value='{cls}' autocomplete='organization-title'></div>
      <label class='check'><input id='rememberReg' name='remember' type='checkbox' checked> Ghi nhớ đăng nhập trên thiết bị này</label>
      <button class='btn primary authsubmit' type='submit'>Tạo tài khoản &amp; đăng nhập</button>
      {err if mode == 'register' else ''}
    </form>

    <div class='muted authnote'>Có thể bật/tắt mật khẩu bằng 👁. Trình duyệt có thể lưu mật khẩu; ứng dụng chỉ lưu tên tài khoản khi chọn “Ghi nhớ đăng nhập”.</div>
  </div>
</div></div>
<script>
function authMode(m){{
  document.getElementById('loginForm').style.display=m==='login'?'block':'none';
  document.getElementById('registerForm').style.display=m==='register'?'block':'none';
  document.querySelectorAll('.authtab').forEach((x,i)=>x.classList.toggle('active',(m==='login'&&i===0)||(m==='register'&&i===1)));
  try{{localStorage.setItem('auth_mode',m)}}catch(e){{}}
}}
function togglePass(id,btn){{const x=document.getElementById(id);if(!x)return;x.type=x.type==='password'?'text':'password';btn.textContent=x.type==='password'?'👁':'🙈'}}
(function(){{
  try{{
    const u=localStorage.getItem('member_username')||'';
    const x=document.getElementById('loginUsername');
    if(x&&!x.value&&u)x.value=u;
  }}catch(e){{}}
}})();
</script>
"""
    return authoritative_page("Tài khoản học viên", body)


def unified_member_auth(*args, **kwargs):
    if request.method == "POST":
        action = (request.form.get("action") or "login").strip().lower()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember = request.form.get("remember") == "on"

        if action == "register":
            name = (request.form.get("name") or "").strip()
            cls = (request.form.get("class") or "").strip()
            password2 = request.form.get("password2") or ""
            if not username or not password:
                return _auth_page("Vui lòng nhập tài khoản và mật khẩu.", "register", request.form)
            if len(username) < 3:
                return _auth_page("Tài khoản phải có ít nhất 3 ký tự.", "register", request.form)
            if len(password) < 4:
                return _auth_page("Mật khẩu phải có ít nhất 4 ký tự.", "register", request.form)
            if password != password2:
                return _auth_page("Hai mật khẩu chưa giống nhau.", "register", request.form)
            d = base.members_data()
            if any(str(x.get("username", "")).casefold() == username.casefold() for x in d.get("members", [])):
                return _auth_page("Tài khoản đã tồn tại. Hãy chọn tên khác hoặc chuyển sang Đăng nhập.", "register", request.form)
            member = {
                "username": username,
                "name": name or username,
                "class": cls,
                "account_type": "FREE",
                "status": "ON",
                "password_sha256": hashlib.sha256(password.encode("utf-8")).hexdigest(),
            }
            d.setdefault("members", []).append(member)
            try:
                base.save_json_github(base.MEMBERS_FILE, d, "members.json", "Register member")
            except Exception as e:
                return _auth_page(f"Không thể lưu tài khoản: {e}", "register", request.form)
            session.clear()
            session.update(role="member", username=username, name=member["name"])
            session.permanent = remember
            return redirect("/member")

        member = _member_lookup(username, password)
        if member:
            session.clear()
            session.update(role="member", username=username, name=str(member.get("name") or username))
            session.permanent = remember
            return redirect("/member")
        return _auth_page("Sai tài khoản hoặc mật khẩu.", "login", request.form)

    return _auth_page("", "login")


if _original_member_login:
    app.view_functions["member_login"] = unified_member_auth
if _original_member_register:
    app.view_functions["member_register"] = unified_member_auth

# Persistent session lifetime used only when the user ticks Remember login.
app.permanent_session_lifetime = timedelta(days=30)


def clean_admin_login():
    msg = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if username == ADMIN_USERNAME and _admin_password_ok(password):
            session.clear()
            session.update(role="admin", username=ADMIN_USERNAME, name="ADMIN")
            return redirect("/admin")
        msg = (
            "ADMIN chưa được cấu hình mật khẩu trên Render. Hãy đặt ADMIN_PASSWORD hoặc ADMIN_PASSWORD_SHA256 trong Environment Variables."
            if not ADMIN_PASSWORD and not ADMIN_PASSWORD_SHA256
            else "Sai tài khoản hoặc mật khẩu ADMIN."
        )
    error = f"<div class='err' style='margin-top:8px'>{html.escape(msg)}</div>" if msg else ""
    body = (
        "<div class='wrap'><div class='panel' style='max-width:430px;margin:60px auto'>"
        "<div class='head'>🔐 ADMIN</div><div class='body'><form method='post'>"
        f"<div class='field'><label>Tài khoản</label><input name='username' autocomplete='username' value='{html.escape(ADMIN_USERNAME, quote=True)}' required></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' autocomplete='current-password' required></div>"
        "<button class='btn primary' type='submit'>Đăng nhập</button>"
        f"{error}</form></div></div></div>"
    )
    return authoritative_page("ADMIN", body)


app.view_functions["admin_login"] = clean_admin_login


def clean_admin_logout():
    session.clear()
    return redirect("/member")


app.view_functions["admin_logout"] = clean_admin_logout

try:
    funcs = app.after_request_funcs.get(None, [])
    app.after_request_funcs[None] = [f for f in funcs if getattr(f, "__name__", "") != "final_student_ui"]
except Exception:
    pass


@app.after_request
def final_authoritative_ui(response):
    if "text/html" not in response.headers.get("Content-Type", ""):
        return response
    try:
        response.set_data(_clean_html(response.get_data(as_text=True)))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers.pop("ETag", None)
    except Exception:
        pass
    return response
