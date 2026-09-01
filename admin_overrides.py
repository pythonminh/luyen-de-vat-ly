# -*- coding: utf-8 -*-
"""One authoritative ADMIN/member layer for the Render app.

This module is loaded last by admin_bootstrap.py.  It intercepts the old
read-only ADMIN pages so there is one management UI and one access policy.
"""
from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime
from urllib.parse import quote

import app as base
from flask import redirect, request, session

app = base.app


def _norm_type(v):
    s = str(v or "FREE").strip().upper().replace(".", "").replace("-", "")
    return {"SVIP": "SVIP", "VIP": "VIP", "FREE": "FREE", "ADMIN": "ADMIN"}.get(s, "FREE")


def _grade(v):
    m = re.search(r"(?<!\d)(10|11|12)(?!\d)", str(v or "").upper())
    return m.group(1) if m else ""


def _members():
    d = base.members_data()
    d.setdefault("members", [])
    return d


def _save_members(d, message="ADMIN cập nhật thành viên"):
    base.save_json_github(base.MEMBERS_FILE, d, "members.json", message)


def _admin_record(d=None):
    d = d or _members()
    return next((m for m in d["members"] if str(m.get("username", "")).strip().casefold() == "admin"), None)


def _is_admin_session():
    return session.get("role") == "admin"


def _is_svip(m):
    return _norm_type(m.get("account_type")) == "SVIP"


def _lesson_grade(item):
    return _grade(item.get("Lop") or item.get("lop") or item.get("class"))


def _can_member_see(m, item):
    if not m or str(m.get("status", "ON")).upper() != "ON":
        return False
    if _is_svip(m) or _norm_type(m.get("account_type")) in {"VIP", "ADMIN", "SVIP"}:
        sg = _grade(m.get("class") or m.get("grade"))
        lg = _lesson_grade(item)
        if sg and lg:
            return sg == lg
        return True
    sg = _grade(m.get("class") or m.get("grade"))
    lg = _lesson_grade(item)
    if sg and lg and sg != lg:
        return False
    level = str(base.lesson_level(str(item.get("path") or item.get("file") or ""))).upper()
    return level == "FREE"


def _allowed_items(m):
    return [
        x for x in base.index_data().get("lessons", [])
        if isinstance(x, dict) and str(x.get("path") or x.get("file") or "").startswith("ngan-hang/") and _can_member_see(m, x)
    ]


def _safe(v):
    return html.escape(str(v or ""), quote=True)


def _member_manager():
    d = _members()
    members = [m for m in d["members"] if str(m.get("username", "")).strip() and str(m.get("username", "")).strip().casefold() != "admin"]
    q = str(request.args.get("q") or "").strip().lower()
    grade = str(request.args.get("grade") or "").strip()
    typ = _norm_type(request.args.get("type")) if request.args.get("type") else ""
    status = str(request.args.get("status") or "").strip().upper()
    if q:
        members = [m for m in members if q in str(m.get("username", "")).lower() or q in str(m.get("name", "")).lower() or q in str(m.get("phone", "")).lower()]
    if grade:
        members = [m for m in members if _grade(m.get("class")) == grade]
    if typ:
        members = [m for m in members if _norm_type(m.get("account_type")) == typ]
    if status in {"ON", "OFF"}:
        members = [m for m in members if str(m.get("status", "ON")).upper() == status]

    allm = [m for m in d["members"] if str(m.get("username", "")).strip().casefold() != "admin"]
    counts = {
        "total": len(allm),
        "on": sum(str(m.get("status", "ON")).upper() == "ON" for m in allm),
        "free": sum(_norm_type(m.get("account_type")) == "FREE" for m in allm),
        "vip": sum(_norm_type(m.get("account_type")) == "VIP" for m in allm),
        "svip": sum(_norm_type(m.get("account_type")) == "SVIP" for m in allm),
        "10": sum(_grade(m.get("class")) == "10" for m in allm),
        "11": sum(_grade(m.get("class")) == "11" for m in allm),
        "12": sum(_grade(m.get("class")) == "12" for m in allm),
    }

    rows = []
    for m in members:
        u = str(m.get("username", "")).strip()
        su = _safe(u)
        name = _safe(m.get("name") or "—")
        phone = _safe(m.get("phone") or "—")
        g = _grade(m.get("class"))
        t = _norm_type(m.get("account_type"))
        st = str(m.get("status", "ON")).upper()
        seen = len(_allowed_items(m))
        badge = "⭐ SVIP" if t == "SVIP" else ("🔑 VIP" if t == "VIP" else "FREE")
        rows.append(
            f"<tr><td><input type='checkbox' name='selected' value='{su}' form='bulkForm'></td>"
            f"<td><b>{su}</b><small>{name}</small></td><td>{phone}</td>"
            f"<td><select class='mini' name='class_{su}' form='row_{su}'><option value=''>Chưa cấp</option>"
            f"<option value='10' {'selected' if g=='10' else ''}>10</option><option value='11' {'selected' if g=='11' else ''}>11</option><option value='12' {'selected' if g=='12' else ''}>12</option></select></td>"
            f"<td><span class='badge {t.lower()}'>{badge}</span><select class='mini' name='account_type' form='row_{su}'><option value='FREE' {'selected' if t=='FREE' else ''}>FREE</option><option value='VIP' {'selected' if t=='VIP' else ''}>VIP</option><option value='SVIP' {'selected' if t=='SVIP' else ''}>SVIP</option></select></td>"
            f"<td><select class='mini' name='status' form='row_{su}'><option value='ON' {'selected' if st=='ON' else ''}>ON</option><option value='OFF' {'selected' if st=='OFF' else ''}>OFF</option></select></td>"
            f"<td><div class='passrow'><input class='pass' name='new_password' form='row_{su}' type='password' placeholder='Mật khẩu mới' autocomplete='new-password'><button type='button' class='eye' onclick=\"togglePass(this)\">👁</button></div></td>"
            f"<td><b>{seen}</b> bài <a class='btn small' href='/admin/members/access?user={quote(u)}'>👁 Xem</a> <form id='row_{su}' method='post' action='/admin/members/save' style='display:inline'><input type='hidden' name='save_user' value='{su}'><button class='btn green small'>💾 Lưu</button></form></td></tr>"
        )

    body = f"""
<style>
.adminmembers{{max-width:1500px;margin:auto;padding:12px}}.hero{{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}}.hero h2{{margin:0}}
.stats{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:10px 0}}.stat{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;padding:9px}}.stat b{{display:block;font-size:20px}}.stat span{{font-size:11px;color:#6c7d90;font-weight:800}}
.toolbar,.bulk{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;padding:9px;margin:8px 0;display:flex;gap:7px;align-items:end;flex-wrap:wrap}}.toolbar .field{{min-width:150px;flex:1}}.toolbar label{{display:block;font-size:10px;font-weight:900;color:#6c7d90}}.toolbar input,.toolbar select,.mini,.pass{{height:34px;border:1px solid #cbd8e6;border-radius:6px;padding:5px;background:#fff}}.toolbar input{{width:100%}}
.membertable{{overflow:auto;background:#fff;border:1px solid #d7e2ee;border-radius:10px}}table{{width:100%;min-width:1250px;border-collapse:collapse}}th,td{{border:1px solid #dfe7ef;padding:7px}}th{{background:#e9f2ff;position:sticky;top:0;z-index:2}}td small{{display:block;color:#718196}}.mini{{width:82px}}.pass{{width:135px}}.passrow{{display:flex;gap:4px;align-items:center}}.eye{{height:34px;border:1px solid #cbd8e6;background:#fff;border-radius:6px;cursor:pointer}}.badge{{display:inline-block;border-radius:999px;padding:3px 7px;font-size:10px;font-weight:900;margin-right:4px}}.badge.free{{background:#eefbf2;color:#14743a}}.badge.vip{{background:#fff0f7;color:#a2175f}}.badge.svip{{background:#fff7dc;color:#855a00}}.btn{{display:inline-block;border:1px solid #b8d5f6;background:#fff;color:#145bb0;border-radius:7px;padding:7px 9px;font-weight:800;cursor:pointer}}.btn.primary{{background:#176bd3;color:#fff}}.btn.green{{background:#179b55;color:#fff}}.btn.small{{padding:5px 7px;font-size:11px}}.note{{background:#fffdf3;border:1px solid #ecd68c;border-radius:9px;padding:9px;margin:8px 0;font-size:12px}}@media(max-width:1000px){{.stats{{grid-template-columns:repeat(3,1fr)}}}}
</style>
<div class='adminmembers'><div class='hero'><div><h2>👥 Quản lý thành viên</h2><div class='muted'>Sửa lớp · quyền · ON/OFF · mật khẩu · xem chính xác bài được phép học</div></div><div><a class='btn primary' href='/admin'>📂 ngan-hang</a> <a class='btn' href='{html.escape(base.github_folder_url(), quote=True)}' target='_blank' rel='noopener'>🐙 GitHub</a> <a class='btn' href='/admin/password'>🔑 Đổi mật khẩu ADMIN</a></div></div>
<div class='stats'><div class='stat'><b>{counts['total']}</b><span>Tổng</span></div><div class='stat'><b>{counts['on']}</b><span>Đang dùng</span></div><div class='stat'><b>{counts['free']}</b><span>FREE</span></div><div class='stat'><b>{counts['vip']}</b><span>VIP</span></div><div class='stat'><b>{counts['svip']}</b><span>SVIP · tất cả</span></div><div class='stat'><b>10:{counts['10']} · 11:{counts['11']} · 12:{counts['12']}</b><span>Phân bố lớp</span></div></div>
<div class='note'>📌 <b>Quy tắc:</b> SVIP xem toàn bộ 10/11/12. FREE chỉ xem bài FREE đúng khối được cấp. VIP chỉ xem bài trong đúng khối được cấp và các bài có quyền VIP. Tài khoản chưa cấp lớp không xem bài.</div>
<form class='toolbar' method='get'><div class='field'><label>TÌM</label><input name='q' value='{_safe(q)}' placeholder='Tài khoản, họ tên, điện thoại'></div><div><label>LỚP</label><select name='grade'><option value=''>Tất cả</option><option value='10' {'selected' if grade=='10' else ''}>10</option><option value='11' {'selected' if grade=='11' else ''}>11</option><option value='12' {'selected' if grade=='12' else ''}>12</option></select></div><div><label>QUYỀN</label><select name='type'><option value=''>Tất cả</option><option value='FREE' {'selected' if typ=='FREE' else ''}>FREE</option><option value='VIP' {'selected' if typ=='VIP' else ''}>VIP</option><option value='SVIP' {'selected' if typ=='SVIP' else ''}>SVIP</option></select></div><div><label>TRẠNG THÁI</label><select name='status'><option value=''>Tất cả</option><option value='ON' {'selected' if status=='ON' else ''}>ON</option><option value='OFF' {'selected' if status=='OFF' else ''}>OFF</option></select></div><button class='btn primary'>🔎 Lọc</button><a class='btn' href='/admin/members'>↻ Tất cả</a></form>
<form id='bulkForm' method='post' action='/admin/members/bulk'></form><div class='bulk'><b>⚡ Đã chọn:</b><select name='account_type' form='bulkForm'><option value=''>Giữ quyền</option><option value='FREE'>FREE</option><option value='VIP'>VIP</option><option value='SVIP'>SVIP</option></select><select name='class' form='bulkForm'><option value=''>Giữ lớp</option><option value='10'>10</option><option value='11'>11</option><option value='12'>12</option></select><select name='status' form='bulkForm'><option value=''>Giữ trạng thái</option><option value='ON'>Mở</option><option value='OFF'>Khóa</option></select><button class='btn green' form='bulkForm'>💾 Áp dụng</button></div>
<div class='membertable'><table><tr><th>✓</th><th>Tài khoản / Họ tên</th><th>Điện thoại</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th><th>Đổi mật khẩu</th><th>Quyền xem</th></tr>{''.join(rows) or '<tr><td colspan=8 style=text-align:center>Không có thành viên</td></tr>'}</table></div></div>
<script>function togglePass(b){{const i=b.previousElementSibling;i.type=i.type==='password'?'text':'password';b.textContent=i.type==='password'?'👁':'🙈'}}</script>
"""
    return base.page("ADMIN · Thành viên", body)


def _access_report():
    d = _members(); username = str(request.args.get("user") or "").strip()
    m = next((x for x in d["members"] if str(x.get("username", "")) == username), None)
    if not m:
        return base.page("ADMIN", "<div class='wrap'><div class='panel'><div class='body err'>Không tìm thấy học viên.</div></div></div>")
    all_items = [x for x in base.index_data().get("lessons", []) if isinstance(x, dict) and str(x.get("path") or x.get("file") or "").startswith("ngan-hang/")]
    allowed = [x for x in all_items if _can_member_see(m, x)]
    hidden = len(all_items) - len(allowed)
    by_grade = {g: [x for x in allowed if _lesson_grade(x) == g] for g in ("10", "11", "12")}
    blocks = []
    for g in ("10", "11", "12"):
        arr = by_grade[g]
        lines = ''.join(f"<tr><td>{_safe(x.get('Mon'))}</td><td>{_safe(x.get('Chuong'))}</td><td>{_safe(x.get('BaiHoc') or x.get('De'))}</td><td>{int(x.get('questions') or x.get('count') or 0)}</td><td>{_safe(x.get('path'))}</td></tr>" for x in arr)
        blocks.append(f"<h3>Khối {g} · {len(arr)} bài</h3><div style='overflow:auto'><table><tr><th>Môn</th><th>Chương</th><th>Bài</th><th>Câu</th><th>File</th></tr>{lines or '<tr><td colspan=5>Không được xem</td></tr>'}</table></div>")
    body = f"""
<div class='wrap'><div class='panel'><div class='head'>👁 Quyền xem của học viên</div><div class='body'><div class='notice'><b>{_safe(m.get('name') or username)}</b> · <b>{_safe(username)}</b> · Lớp <b>{_safe(_grade(m.get('class')) or 'chưa cấp')}</b> · Quyền <b>{_safe(_norm_type(m.get('account_type')))}</b> · Được xem <b>{len(allowed)}</b> / {len(all_items)} bài · Bị khóa <b>{hidden}</b> bài</div>{''.join(blocks)}<p><a class='btn' href='/admin/members'>← Quản lý thành viên</a></p></div></div></div>
"""
    return base.page("ADMIN · Quyền xem", body)


def _save_member():
    d = _members(); username = str(request.form.get("save_user") or "").strip()
    target = next((m for m in d["members"] if str(m.get("username", "")) == username), None)
    if not target or username.casefold() == "admin":
        return redirect("/admin/members")
    target["name"] = str(target.get("name") or username).strip()
    target["class"] = _grade(request.form.get("class_" + username) or "")
    target["grade"] = target["class"]
    target["account_type"] = _norm_type(request.form.get("account_type") or target.get("account_type"))
    target["status"] = "ON" if str(request.form.get("status") or target.get("status") or "ON").upper() == "ON" else "OFF"
    pw = str(request.form.get("new_password") or "")
    if pw:
        if len(pw) < 4:
            return base.page("ADMIN", "<div class='wrap'><div class='panel'><div class='body err'>Mật khẩu phải có ít nhất 4 ký tự.</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
        target["password_sha256"] = hashlib.sha256(pw.encode()).hexdigest()
    target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_members(d)
    return redirect("/admin/members")


def _bulk_save():
    d = _members(); selected = set(request.form.getlist("selected"))
    typ = request.form.get("account_type") or ""; cls = request.form.get("class") or ""; st = request.form.get("status") or ""
    for m in d["members"]:
        if str(m.get("username")) not in selected or str(m.get("username")).casefold() == "admin":
            continue
        if typ: m["account_type"] = _norm_type(typ)
        if cls: m["class"] = _grade(cls); m["grade"] = m["class"]
        if st in {"ON", "OFF"}: m["status"] = st
        m["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if selected: _save_members(d, "ADMIN cấp quyền hàng loạt")
    return redirect("/admin/members")


def _admin_password_page():
    msg = ""
    if request.method == "POST":
        current = request.form.get("current_password") or ""
        new = request.form.get("new_password") or ""
        new2 = request.form.get("new_password2") or ""
        d = _members(); a = _admin_record(d)
        if not a:
            return base.page("ADMIN", "<div class='wrap'><div class='panel'><div class='body err'>Thiếu tài khoản ADMIN.</div></div></div>")
        if hashlib.sha256(current.encode()).hexdigest() != str(a.get("password_sha256", "")):
            msg = "Mật khẩu ADMIN hiện tại không đúng."
        elif len(new) < 6:
            msg = "Mật khẩu mới phải có ít nhất 6 ký tự."
        elif new != new2:
            msg = "Hai mật khẩu mới không giống nhau."
        else:
            a["password_sha256"] = hashlib.sha256(new.encode()).hexdigest(); a["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _save_members(d, "ADMIN đổi mật khẩu")
            session.clear(); session.update(role="admin", username="ADMIN", name="ADMIN")
            return base.page("ADMIN", "<div class='wrap'><div class='panel'><div class='body success'>✅ Đã đổi mật khẩu ADMIN và lưu vào members.json.</div><a class='btn primary' href='/admin/members'>Tiếp tục quản lý</a></div></div>")
    e = f"<div class='err'>{_safe(msg)}</div>" if msg else ""
    body = (
        "<div class='wrap'><div class='panel' style='max-width:520px;margin:30px auto'><div class='head'>🔑 Đổi mật khẩu ADMIN</div><div class='body'>"
        "<div class='note'>Mật khẩu ADMIN được lưu dưới dạng SHA-256 trong <b>members.json</b>, không lưu mật khẩu thô.</div>"
        "<form method='post'><div class='field'><label>Mật khẩu hiện tại</label><div class='passrow'>"
        "<input id='a1' name='current_password' type='password' autocomplete='current-password' required>"
        "<button type='button' class='eye' onclick=\"tp('a1',this)\">👁</button></div></div>"
        "<div class='field'><label>Mật khẩu mới</label><div class='passrow'>"
        "<input id='a2' name='new_password' type='password' autocomplete='new-password' required>"
        "<button type='button' class='eye' onclick=\"tp('a2',this)\">👁</button></div></div>"
        "<div class='field'><label>Nhập lại mật khẩu mới</label><div class='passrow'>"
        "<input id='a3' name='new_password2' type='password' autocomplete='new-password' required>"
        "<button type='button' class='eye' onclick=\"tp('a3',this)\">👁</button></div></div>"
        f"<button class='btn primary'>💾 Lưu mật khẩu mới</button> <a class='btn' href='/admin/members'>Hủy</a>{e}</form></div></div></div>"
        "<script>function tp(id,b){let x=document.getElementById(id);x.type=x.type==='password'?'text':'password';b.textContent=x.type==='password'?'👁':'🙈'}</script>"
    )
    return base.page("ADMIN · Mật khẩu", body)


def _admin_login():
    if request.method == "POST":
        u = str(request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        d = _members(); a = _admin_record(d)
        if a and u.casefold() == "admin" and str(a.get("status", "ON")).upper() == "ON" and hashlib.sha256(p.encode()).hexdigest() == str(a.get("password_sha256", "")):
            session.clear(); session.update(role="admin", username="ADMIN", name="ADMIN"); session.permanent = request.form.get("remember") == "on"
            return redirect("/admin")
        return _admin_login_page("Sai tài khoản hoặc mật khẩu ADMIN.")
    return _admin_login_page("")


def _admin_login_page(msg):
    err = f"<div class='err'>{_safe(msg)}</div>" if msg else ""
    body = f"<div class='wrap'><div class='panel' style='max-width:440px;margin:55px auto'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='ADMIN' autocomplete='username' required></div><div class='field'><label>Mật khẩu</label><div class='passrow'><input id='apass' name='password' type='password' autocomplete='current-password' required><button type='button' class='eye' onclick='tp(this)'>👁</button></div></div><label><input type='checkbox' name='remember'> Ghi nhớ đăng nhập trên thiết bị này</label><p><button class='btn primary'>Đăng nhập</button></p>{err}</form></div></div></div><script>function tp(b){{let x=document.getElementById('apass');x.type=x.type==='password'?'text':'password';b.textContent=x.type==='password'?'👁':'🙈'}}</script>"
    return base.page("ADMIN", body)


@app.before_request
def _authoritative_admin_routes():
    if not _is_admin_session():
        return None
    p = request.path.rstrip("/") or "/"
    if p == "/admin/members" and request.method == "GET": return _member_manager()
    if p == "/admin/members/access" and request.method == "GET": return _access_report()
    if p == "/admin/members/save" and request.method == "POST": return _save_member()
    if p == "/admin/members/bulk" and request.method == "POST": return _bulk_save()
    if p == "/admin/password": return _admin_password_page()
    return None


# Replace the old admin login view; route rule remains /admin/login.
if "admin_login" in app.view_functions:
    app.view_functions["admin_login"] = _admin_login

# Make every existing question-opening endpoint enforce the same class/SVIP rule.
try:
    import access_control
    base.can_access = lambda member, path: any(
        str(x.get("path") or x.get("file") or "") == str(path) and _can_member_see(member, x)
        for x in base.index_data().get("lessons", []) if isinstance(x, dict)
    )
    access_control.student_can_access = base.can_access
except Exception:
    pass
