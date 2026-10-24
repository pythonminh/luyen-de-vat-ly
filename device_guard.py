# -*- coding: utf-8 -*-
"""Persistent student/device lock for exam and HTML-practice entry points."""
import hashlib
import html
import os
import secrets
from flask import request, session, redirect, make_response
from werkzeug.exceptions import Forbidden
import app as base

app = base.app
COOKIE = "thayminh_device"
DDL = """
CREATE TABLE IF NOT EXISTS student_device_bindings (
 username TEXT PRIMARY KEY,
 token_hash TEXT NOT NULL UNIQUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS student_device_audit (
 id BIGSERIAL PRIMARY KEY, username TEXT NOT NULL, event TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""
def connect():
    import psycopg
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("Chưa cấu hình DATABASE_URL PostgreSQL trên Render.")
    return psycopg.connect(url, autocommit=False)

def guarded(path):
    p = path.rstrip("/")
    if p in {"/member/html-practice", "/member/start", "/member/start-selected",
             "/member/practice", "/member/answer", "/member/exams/open",
             "/member/exam", "/member/exams/saved"}:
        return True
    return p.startswith(("/api/practice/", "/api/exam/", "/member/exam/",
                         "/member/html-practice/", "/api/html-practice/",
                         "/practice/jump/", "/practice/redo/"))

@app.before_request
def enforce_student_device():
    if not guarded(request.path) or session.get("role") != "member":
        return
    member = base.member_current()
    if not member:
        return redirect("/member/login")
    if base.is_admin_member(member):
        return
    username = str(member.get("username") or "").strip().casefold()
    if not username:
        raise Forbidden("Không xác định được tài khoản.")
    token = request.cookies.get(COOKIE, "")
    if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
        token = secrets.token_hex(32)
        # Only a newly generated token may be set on the successful response.
        request.environ["student_device_new_token"] = token
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
                # Serialize cross-account claims, including first-use races.
                cur.execute("SELECT pg_advisory_xact_lock(876512301)")
                cur.execute("SELECT username,token_hash FROM student_device_bindings WHERE username=%s OR token_hash=%s", (username,digest))
                records = cur.fetchall()
                if records:
                    if len(records) != 1 or records[0] != (username,digest):
                        return ("Thiết bị hoặc tài khoản đã được liên kết. Liên hệ ADMIN để mở khóa.", 403)
                else:
                    cur.execute("INSERT INTO student_device_bindings(username,token_hash) VALUES (%s,%s)", (username,digest))
                    cur.execute("INSERT INTO student_device_audit(username,event) VALUES (%s,'bind')", (username,))
    except Exception:
        app.logger.exception("Device lock database error")
        return ("Không thể xác minh thiết bị. Vui lòng thử lại hoặc liên hệ ADMIN.", 503)

@app.after_request
def issue_device_cookie(response):
    token = request.environ.get("student_device_new_token")
    if token and response.status_code < 400:
        response.set_cookie(COOKIE,token,max_age=365*24*3600,httponly=True,
                            secure=True,samesite="Lax",path="/")
    return response

@app.route("/admin/device-locks", methods=["GET","POST"])
def admin_device_locks():
    if not base.admin_current():
        raise Forbidden()
    message = ""
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
                if request.method == "POST":
                    # POST is protected by same-origin CSRF token in admin session.
                    csrf = session.get("device_admin_csrf")
                    if not csrf or not secrets.compare_digest(str(request.form.get("csrf") or ""),csrf):
                        raise Forbidden("Mã xác nhận không hợp lệ.")
                    username = str(request.form.get("username") or "").strip().casefold()
                    if username:
                        cur.execute("DELETE FROM student_device_bindings WHERE username=%s RETURNING username",(username,))
                        if cur.fetchone():
                            cur.execute("INSERT INTO student_device_audit(username,event) VALUES (%s,'admin_reset')",(username,))
                            message = "Đã mở khóa: "+html.escape(username)
                cur.execute("SELECT username,created_at FROM student_device_bindings ORDER BY created_at DESC LIMIT 500")
                rows = cur.fetchall()
    except Forbidden:
        raise
    except Exception:
        app.logger.exception("Admin device lock database error")
        return "Không thể truy cập cơ sở dữ liệu khóa thiết bị.",503
    csrf = session.setdefault("device_admin_csrf",secrets.token_hex(24))
    body = "<h2>Quản lý thiết bị học viên</h2><p>"+message+"</p><p><a href='/admin'>← ADMIN</a></p>"
    body += "<table border='1' cellpadding='8'><tr><th>Tài khoản</th><th>Ngày liên kết</th><th>Thao tác</th></tr>"
    for username,created in rows:
        u=html.escape(username,quote=True)
        body += "<tr><td>"+u+"</td><td>"+html.escape(str(created))+"</td><td><form method='post'><input type='hidden' name='csrf' value='"+csrf+"'><input type='hidden' name='username' value='"+u+"'><button onclick='return confirm(&quot;Mở khóa thiết bị?&quot;)'>Mở khóa</button></form></td></tr>"
    body += "</table>"
    return make_response("<!doctype html><html lang='vi'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Quản lý thiết bị</title><body style='font:16px Arial;max-width:1000px;margin:24px auto;padding:12px'>"+body+"</body></html>")
