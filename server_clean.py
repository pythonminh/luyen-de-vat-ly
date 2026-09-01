# -*- coding: utf-8 -*-
"""Authoritative Render entry point.

Only this module is used by Gunicorn. It provides one final branding/navigation
layer and one ADMIN login/logout implementation while reusing the existing
question, member, practice and Gemini routes from app/wsgi.
"""
from __future__ import annotations

import hashlib
import html
import os
import re

from flask import redirect, request, session

import wsgi
import admin_manager  # registers ADMIN member/result management routes

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
        m = wsgi.member_current()
        if m:
            return str(m.get("name") or m.get("username") or "Học viên")
    except Exception:
        pass
    return str(session.get("name") or session.get("username") or "Học viên")


def _nav() -> str:
    links = ["<a href='/member'>📚 Mục lục</a>"]
    if session.get("role") == "admin":
        links += [
            "<a href='/admin'>🔐 ADMIN</a>",
            "<a href='https://github.com/pythonminh/luyen-de-vat-ly' target='_blank' rel='noopener'>🐙 GitHub</a>",
            "<a href='/admin/logout'>🚪 Thoát</a>",
        ]
    elif session.get("role") == "member":
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


def _clean_header(body: str) -> str:
    for old in (
        "📚 Ngân hàng câu hỏi GitHub",
        "Ngân hàng câu hỏi GitHub",
        "📚 Ngân hàng GitHub",
        "Ngân hàng GitHub",
        "📚 Luyện đề AI · Thầy Minh",
        "Luyện đề AI · Thầy Minh",
    ):
        body = body.replace(old, BRAND)

    body = re.sub(
        r"<div\s+class=['\"]sub['\"]>.*?</div>",
        f"<div class='sub'>{CONTACT}</div>",
        body,
        count=1,
        flags=re.I | re.S,
    )
    body = re.sub(
        r"<div\s+class=['\"]nav['\"]>.*?</div>",
        _nav(),
        body,
        count=1,
        flags=re.I | re.S,
    )

    if session.get("role") != "admin":
        body = re.sub(
            r"<a\b[^>]*href=['\"][^'\"]*(?:github\.com|/github(?:/|['\"]))[^'\"]*['\"][^>]*>.*?</a>",
            "",
            body,
            flags=re.I | re.S,
        )
        body = re.sub(
            r"<button\b[^>]*>\s*(?:🐙\s*)?GitHub\s*</button>",
            "",
            body,
            flags=re.I | re.S,
        )

    body = re.sub(
        r"Nguồn đề:\s*bank_index\.json\s*\+\s*ngan-hang/\\?\*\.tex\s*(?:·|•|\|)\s*Google Sheet không dùng cho đề",
        CONTACT,
        body,
        flags=re.I,
    )
    body = re.sub(r"MỤC LỤC\s*[·•|]\s*GitHub", "MỤC LỤC", body, flags=re.I)

    if request.path.startswith("/member") or request.path == "/":
        body = re.sub(r"\\begin\s*\{\s*ex\s*\}", "", body, flags=re.I)
        body = re.sub(r"\\end\s*\{\s*ex\s*\}", "", body, flags=re.I)
        body = re.sub(r"%\s*ID\s*:\s*[^%<\r\n]+", "", body, flags=re.I)
        body = re.sub(r"%\s*Mức\s*:\s*[^%<\r\n]+", "", body, flags=re.I)
    return body


@app.after_request
def authoritative_ui(response):
    if "text/html" not in response.headers.get("Content-Type", ""):
        return response
    try:
        body = _clean_header(response.get_data(as_text=True))
        css = """
<style>
.user-pill{display:inline-flex;align-items:center;color:#fff;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.10);padding:7px 10px;border-radius:8px;font-weight:800;white-space:nowrap}
.brand{font-weight:900;font-size:20px}.sub{font-size:11px;opacity:.9}
@media(max-width:900px){.topin{padding:8px 10px;align-items:flex-start}.brand{font-size:18px;line-height:1.2}.sub{font-size:10px}.nav{gap:4px}.nav a,.user-pill{padding:6px 8px;font-size:12px}}
@media(max-width:560px){.topin{display:flex;flex-direction:column;gap:6px}.nav{width:100%;margin-left:0}.nav a,.user-pill{font-size:11px;padding:5px 7px}.brand{font-size:16px}}
</style>
"""
        body = body.replace("</head>", css + "</head>", 1)
        body = body.replace(
            "</body>",
            "<script>window.addEventListener('load',function(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise().catch(function(){});});</script></body>",
            1,
        )
        response.set_data(body)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers.pop("ETag", None)
    except Exception:
        pass
    return response


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
            "ADMIN chưa được cấu hình mật khẩu trên Render (ADMIN_PASSWORD hoặc ADMIN_PASSWORD_SHA256)."
            if not ADMIN_PASSWORD and not ADMIN_PASSWORD_SHA256
            else "Sai tài khoản hoặc mật khẩu ADMIN."
        )

    error = f"<div class='err' style='margin-top:8px'>{html.escape(msg)}</div>" if msg else ""
    body = (
        "<div class='wrap'><div class='panel' style='max-width:430px;margin:60px auto'>"
        "<div class='head'>🔐 ADMIN</div><div class='body'>"
        "<form method='post'>"
        f"<div class='field'><label>Tài khoản</label><input name='username' autocomplete='username' value='{html.escape(ADMIN_USERNAME, quote=True)}' required></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' autocomplete='current-password' required></div>"
        "<button class='btn primary' type='submit'>Đăng nhập</button>"
        f"{error}</form></div></div></div>"
    )
    return wsgi.page("ADMIN", body)


# Replace the existing endpoint without adding a second /admin/login route.
app.view_functions["admin_login"] = clean_admin_login


def clean_admin_logout():
    session.clear()
    return redirect("/member")


if "admin_logout" in app.view_functions:
    app.view_functions["admin_logout"] = clean_admin_logout
else:
    app.add_url_rule("/admin/logout", endpoint="admin_logout", view_func=clean_admin_logout, methods=["GET"])
