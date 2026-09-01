# -*- coding: utf-8 -*-
"""Single authoritative Render entry point.

Keeps one UI/auth policy and, importantly, never rewrites LaTeX/JSON embedded
inside the student-practice JavaScript.  Old cleanup code was deleting the
question payload itself because `% ID` and `% Mức` comments lived on the same
line as the question text.
"""
from __future__ import annotations

import hashlib
import html
import os
import re

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
            "<a href='/member/login'>🔑 Đăng nhập</a>",
            "<a href='/member/register'>📝 Đăng ký</a>",
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
    # Only replace a real visible legacy navigation. Do not touch scripts.
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

    # IMPORTANT: Never strip LaTeX comments from /member/practice HTML.
    # The practice page stores the question payload inside a <script> JSON
    # literal; stripping `% ID` / `% Mức` there can delete the question text.
    if (request.path.startswith("/member") or request.path == "/") and request.path != "/member/practice":
        body = re.sub(r"\\begin\s*\{\s*ex\s*\}", "", body, flags=re.I)
        body = re.sub(r"\\end\s*\{\s*ex\s*\}", "", body, flags=re.I)
        body = re.sub(r"%\s*ID\s*:\s*[^%<\r\n]+", "", body, flags=re.I)
        body = re.sub(r"%\s*Mức\s*:\s*[^%<\r\n]+", "", body, flags=re.I)
    return body


# Clean the question text at the source instead of deleting pieces from the
# rendered HTML/JavaScript later.
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


_original_member_login = app.view_functions.get("member_login")
if _original_member_login:
    def unified_member_login(*args, **kwargs):
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            if username == ADMIN_USERNAME and _admin_password_ok(password):
                session.clear()
                session.update(role="admin", username=ADMIN_USERNAME, name="ADMIN")
                return redirect("/admin")
        return _original_member_login(*args, **kwargs)
    app.view_functions["member_login"] = unified_member_login


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


# Remove the destructive legacy wsgi response filter.  It ran after this
# module's filter and deleted `% ID` / `% Mức` from the embedded practice JSON.
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
