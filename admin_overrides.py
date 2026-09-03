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
import membership as pkg
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


def _is_admin_account(m):
    if not m:
        return False
    if _norm_type(m.get("account_type")) == "ADMIN":
        return True
    u = str(m.get("username") or "").strip()
    return bool(u) and u.casefold() == "admin"


def _can_member_see(m, item):
    if not m or str(m.get("status", "ON")).upper() != "ON":
        return False
    if _is_admin_account(m):
        return True
    return pkg.can_see_item(m, item)


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
    pack_filter = str(request.args.get("pack") or "").strip()
    status = str(request.args.get("status") or "").strip().upper()
    if q:
        members = [m for m in members if q in str(m.get("username", "")).lower() or q in str(m.get("name", "")).lower() or q in str(m.get("phone", "")).lower()]
    if grade:
        members = [m for m in members if grade in (pkg.granted_package(m) or {}).get("grades", []) or pkg._grade(m.get("class")) == grade]
    if pack_filter == "pending":
        members = [m for m in members if pkg.package_status(m) == "pending"]
    elif pack_filter == "approved":
        members = [m for m in members if pkg.package_status(m) == "approved"]
    elif pack_filter == "none":
        members = [m for m in members if pkg.package_status(m) in {"none", "rejected"}]
    if status in {"ON", "OFF"}:
        members = [m for m in members if str(m.get("status", "ON")).upper() == status]

    allm = [m for m in d["members"] if str(m.get("username", "")).strip().casefold() != "admin"]
    counts = {
        "total": len(allm),
        "on": sum(str(m.get("status", "ON")).upper() == "ON" for m in allm),
        "pending": sum(pkg.package_status(m) == "pending" for m in allm),
        "approved": sum(pkg.package_status(m) == "approved" for m in allm),
        "none": sum(pkg.package_status(m) in {"none", "rejected"} for m in allm),
    }
    members.sort(key=lambda m: (0 if pkg.package_status(m) == "pending" else 1, str(m.get("name") or m.get("username") or "")))

    cards = []
    for m in members:
        u = str(m.get("username", "")).strip()
        su = _safe(u)
        name = _safe(m.get("name") or "—")
        phone = _safe(m.get("phone") or "—")
        st = str(m.get("status", "ON")).upper()
        seen = len(_allowed_items(m))
        pst = pkg.package_status(m)
        granted = pkg.granted_package(m)
        req = pkg.requested_package(m)
        cur_pw = base.member_password_plain(m)
        cur_val = _safe(cur_pw)
        cur_ph = "Chưa xem được" if not cur_pw else "Mật khẩu hiện tại"
        req_html = ""
        if pst == "pending" and req:
            req_html = (
                f"<div class='pendcard'>⏳ Yêu cầu: <b class='req'>{_safe(pkg.package_label(req))}</b> "
                f"<button class='btn green small' name='intent' value='approve' form='row_{su}'>✅ Duyệt đúng yêu cầu</button> "
                f"<button class='btn small' name='intent' value='reject' form='row_{su}'>Từ chối</button></div>"
            )
        cards.append(
            f"<article class='memcard{' wait' if pst=='pending' else ''}'>"
            f"<div class='memtop'><label class='ck'><input type='checkbox' name='selected' value='{su}' form='bulkForm'> "
            f"<b>{name}</b> · {su}</label><span class='muted'>{phone}</span>"
            f"<span class='badge {pst}'>{'⏳ Chờ duyệt' if pst=='pending' else ('✅ Đã cấp' if pst=='approved' else 'Chưa cấp')}</span></div>"
            f"{req_html}"
            f"<form id='row_{su}' class='memform' method='post' action='/admin/members/save'>"
            f"<input type='hidden' name='save_user' value='{su}'>"
            f"<div class='now'>Hiện có: <b>{_safe(pkg.package_label(granted))}</b> · {seen} bài "
            f"<a class='btn small' href='/admin/members/access?user={quote(u)}'>👁 Xem bài</a></div>"
            + pkg.picker_html(prefix=u, selected=req or granted, student=False)
            + f"<div class='memacts'><select name='status'><option value='ON' {'selected' if st=='ON' else ''}>ON · đang dùng</option><option value='OFF' {'selected' if st=='OFF' else ''}>OFF · khóa</option></select>"
            f"<div class='passrow'><input class='pass' type='password' value='{cur_val}' placeholder='{cur_ph}' readonly autocomplete='off'><button type='button' class='eye' onclick=\"togglePass(this)\">👁</button></div>"
            f"<div class='passrow'><input class='pass' name='new_password' type='password' placeholder='Đặt mật khẩu mới' autocomplete='new-password'><button type='button' class='eye' onclick=\"togglePass(this)\">👁</button></div>"
            f"<button class='btn green' name='intent' value='save'>💾 Lưu / cấp gói</button></div></form></article>"
        )

    create = (
        "<details class='createbox'><summary>➕ Cấp thành viên mới (duyệt luôn)</summary>"
        "<form method='post' action='/admin/members/create' class='createform'>"
        "<div class='cgrid'><div class='field'><label>Họ tên</label><input name='name' required></div>"
        "<div class='field'><label>Tài khoản</label><input name='username' required></div>"
        "<div class='field'><label>Điện thoại</label><input name='phone'></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div></div>"
        + pkg.picker_html(student=False)
        + "<button class='btn primary' type='submit'>✅ Tạo và cấp gói</button></form></details>"
    )

    body = f"""
{pkg.PKG_CSS}
<style>
.adminmembers{{max-width:1100px;margin:auto;padding:12px}}.hero{{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}}.hero h2{{margin:0}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:10px 0}}.stat{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;padding:9px}}.stat b{{display:block;font-size:20px}}.stat span{{font-size:11px;color:#6c7d90;font-weight:800}}.stat.warn b{{color:#a15b00}}
.toolbar,.bulk,.createbox{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;padding:9px;margin:8px 0}}.toolbar{{display:flex;gap:7px;align-items:end;flex-wrap:wrap}}.toolbar .field{{min-width:150px;flex:1}}.toolbar label,.createform label{{display:block;font-size:10px;font-weight:900;color:#6c7d90}}.toolbar input,.toolbar select,.pass,select{{height:34px;border:1px solid #cbd8e6;border-radius:6px;padding:5px;background:#fff}}.toolbar input{{width:100%}}
.memcard{{background:#fff;border:1px solid #d7e2ee;border-radius:12px;padding:10px;margin:8px 0}}.memcard.wait{{border-color:#e0b84a;background:#fffdf6}}.memtop{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}}.ck{{font-weight:800}}.now{{margin:6px 0;font-size:13px}}.memacts{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:8px}}.pass{{width:150px}}.passrow{{display:flex;gap:4px;align-items:center}}.eye{{height:34px;border:1px solid #cbd8e6;background:#fff;border-radius:6px;cursor:pointer}}
.badge{{display:inline-block;border-radius:999px;padding:3px 8px;font-size:10px;font-weight:900}}.badge.pending{{background:#fff4d6;color:#8a5a00}}.badge.approved{{background:#e8f8ee;color:#116a32}}.badge.none,.badge.rejected{{background:#f1f4f8;color:#5d7084}}
.btn{{display:inline-block;border:1px solid #b8d5f6;background:#fff;color:#145bb0;border-radius:7px;padding:7px 9px;font-weight:800;cursor:pointer}}.btn.primary{{background:#176bd3;color:#fff}}.btn.green{{background:#179b55;color:#fff;border-color:#128a4a}}.btn.small{{padding:5px 7px;font-size:11px}}
.note{{background:#eef7ff;border:1px solid #b9d5ef;border-radius:9px;padding:9px;margin:8px 0;font-size:12px}}.cgrid{{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}}@media(max-width:800px){{.stats{{grid-template-columns:repeat(2,1fr)}}.cgrid{{grid-template-columns:1fr}}}}
</style>
<div class='adminmembers'><div class='hero'><div><h2>👥 Quản lý thành viên</h2><div class='muted'>Duyệt gói 1–3 lớp / 1–2 môn · cấp quyền · khóa · mật khẩu</div></div><div><a class='btn primary' href='/admin'>📂 ngan-hang</a> <a class='btn' href='{html.escape(base.github_folder_url(), quote=True)}' target='_blank' rel='noopener'>🐙 GitHub</a> <a class='btn' href='/admin/password'>🔑 Đổi mật khẩu ADMIN</a></div></div>
<div class='stats'><div class='stat'><b>{counts['total']}</b><span>Tổng</span></div><div class='stat warn'><b>{counts['pending']}</b><span>Chờ duyệt</span></div><div class='stat'><b>{counts['approved']}</b><span>Đã cấp gói</span></div><div class='stat'><b>{counts['none']}</b><span>Chưa cấp</span></div><div class='stat'><b>{counts['on']}</b><span>Đang dùng</span></div></div>
<div class='note'>📌 Học viên tự chọn gói khi đăng ký. ADMIN duyệt đúng yêu cầu, hoặc sửa gói rồi bấm <b>Lưu / cấp gói</b>. 1–3 lớp = cả Toán và Lý các khối đó. 1–2 môn = môn đó cho cả 10/11/12. Tài khoản cũ VIP vẫn giữ đúng lớp đã cấp.</div>
{create}
<form class='toolbar' method='get'><div class='field'><label>TÌM</label><input name='q' value='{_safe(q)}' placeholder='Tài khoản, họ tên, điện thoại'></div><div><label>LỚP</label><select name='grade'><option value=''>Tất cả</option><option value='10' {'selected' if grade=='10' else ''}>10</option><option value='11' {'selected' if grade=='11' else ''}>11</option><option value='12' {'selected' if grade=='12' else ''}>12</option></select></div><div><label>GÓI</label><select name='pack'><option value=''>Tất cả</option><option value='pending' {'selected' if pack_filter=='pending' else ''}>Chờ duyệt</option><option value='approved' {'selected' if pack_filter=='approved' else ''}>Đã cấp</option><option value='none' {'selected' if pack_filter=='none' else ''}>Chưa cấp</option></select></div><div><label>TÀI KHOẢN</label><select name='status'><option value=''>Tất cả</option><option value='ON' {'selected' if status=='ON' else ''}>Đang dùng</option><option value='OFF' {'selected' if status=='OFF' else ''}>Khóa</option></select></div><button class='btn primary'>🔎 Lọc</button><a class='btn' href='/admin/members'>↻ Tất cả</a></form>
<form id='bulkForm' method='post' action='/admin/members/bulk'></form>
<div class='bulk'><b>⚡ Đã chọn:</b> <button class='btn green' name='intent' value='approve' form='bulkForm'>✅ Duyệt yêu cầu</button> <button class='btn' name='intent' value='off' form='bulkForm'>Khóa</button> <button class='btn' name='intent' value='on' form='bulkForm'>Mở</button></div>
{''.join(cards) or "<div class='note'>Không có thành viên phù hợp.</div>"}
</div>
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
<div class='wrap'><div class='panel'><div class='head'>👁 Quyền xem của học viên</div><div class='body'><div class='notice'><b>{_safe(m.get('name') or username)}</b> · <b>{_safe(username)}</b> · Gói <b>{_safe(pkg.scope_label(m))}</b> · Được xem <b>{len(allowed)}</b> / {len(all_items)} bài · Bị khóa <b>{hidden}</b> bài</div>{''.join(blocks)}<p><a class='btn' href='/admin/members'>← Quản lý thành viên</a></p></div></div></div>
"""
    return base.page("ADMIN · Quyền xem", body)


def _save_member():
    d = _members()
    username = str(request.form.get("save_user") or "").strip()
    target = next((m for m in d["members"] if str(m.get("username", "")) == username), None)
    if not target or username.casefold() == "admin":
        return redirect("/admin/members")
    intent = str(request.form.get("intent") or "save").strip().lower()
    target["status"] = "ON" if str(request.form.get("status") or target.get("status") or "ON").upper() == "ON" else "OFF"
    pw = str(request.form.get("new_password") or "")
    if pw:
        if len(pw) < 4:
            return base.page("ADMIN", "<div class='wrap'><div class='panel'><div class='body err'>Mật khẩu phải có ít nhất 4 ký tự.</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
        base.set_member_password(target, pw)
    if intent == "reject":
        target["package_status"] = "rejected"
        target["requested_package"] = None
        target["account_type"] = "FREE"
        target["package"] = None
    elif intent == "approve":
        chosen = pkg.requested_package(target)
        if not chosen:
            chosen, err = pkg.package_from_form(request.form, prefix=username, student=False)
            if err:
                return base.page("ADMIN", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(err)}</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
        pkg.apply_granted(target, chosen, approved=True)
        target["status"] = "ON"
    else:
        chosen, err = pkg.package_from_form(request.form, prefix=username, student=False)
        if err:
            return base.page("ADMIN", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(err)}</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
        pkg.apply_granted(target, chosen, approved=True)
    target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_members(d, f"ADMIN cấp gói {username}")
    return redirect("/admin/members")


def _bulk_save():
    d = _members()
    selected = set(request.form.getlist("selected"))
    intent = str(request.form.get("intent") or "").strip().lower()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for m in d["members"]:
        if str(m.get("username")) not in selected or str(m.get("username")).casefold() == "admin":
            continue
        if intent == "off":
            m["status"] = "OFF"
        elif intent == "on":
            m["status"] = "ON"
        elif intent == "approve":
            chosen = pkg.requested_package(m) or pkg.granted_package(m)
            if chosen:
                pkg.apply_granted(m, chosen, approved=True)
                m["status"] = "ON"
        m["updated_at"] = now
    if selected:
        _save_members(d, "ADMIN duyệt / khóa hàng loạt")
    return redirect("/admin/members")


def _create_member():
    d = _members()
    username = str(request.form.get("username") or "").strip()
    name = str(request.form.get("name") or username).strip()
    phone = str(request.form.get("phone") or "").strip()
    password = str(request.form.get("password") or "")
    if len(username) < 3:
        return base.page("ADMIN", "<div class='wrap'><div class='panel'><div class='body err'>Tài khoản phải có ít nhất 3 ký tự.</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
    if len(password) < 4:
        return base.page("ADMIN", "<div class='wrap'><div class='panel'><div class='body err'>Mật khẩu phải có ít nhất 4 ký tự.</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
    if any(str(x.get("username", "")).casefold() == username.casefold() for x in d.get("members", [])):
        return base.page("ADMIN", "<div class='wrap'><div class='panel'><div class='body err'>Tài khoản đã tồn tại.</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
    chosen, err = pkg.package_from_form(request.form, student=False)
    if err:
        return base.page("ADMIN", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(err)}</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
    rec = {"username": username, "name": name or username, "phone": phone, "status": "ON", "account_type": "VIP"}
    base.set_member_password(rec, password)
    pkg.apply_granted(rec, chosen, approved=True)
    rec["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d.setdefault("members", []).append(rec)
    _save_members(d, f"ADMIN tạo thành viên {username}")
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
    if p == "/admin/members/create" and request.method == "POST": return _create_member()
    if p == "/admin/password": return _admin_password_page()
    return None


# Replace the old admin login view; route rule remains /admin/login.
if "admin_login" in app.view_functions:
    app.view_functions["admin_login"] = _admin_login

# Make every existing question-opening endpoint enforce the same class/SVIP rule.
try:
    import access_control
    def _admin_aware_can_access(member, path):
        if getattr(base, "has_full_bank_access", lambda *_: False)(member) or _is_admin_account(member):
            return True
        return any(
            str(x.get("path") or x.get("file") or "") == str(path) and _can_member_see(member, x)
            for x in base.index_data().get("lessons", []) if isinstance(x, dict)
        )
    base.can_access = _admin_aware_can_access
    access_control.student_can_access = base.can_access
except Exception:
    pass
