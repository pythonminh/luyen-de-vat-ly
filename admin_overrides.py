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
    if session.get("role") == "admin":
        return True
    try:
        return bool(base.can_manage_bank())
    except Exception:
        return False


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
    type_filter = str(request.args.get("type") or "").strip().lower()
    dur_filter = str(request.args.get("dur") or "").strip().lower()
    status = str(request.args.get("status") or "").strip().upper()
    if q:
        members = [m for m in members if q in str(m.get("username", "")).lower() or q in str(m.get("name", "")).lower() or q in str(m.get("phone", "")).lower()]
    if grade:
        members = [m for m in members if grade in (pkg.granted_package(m) or {}).get("grades", []) or pkg._grade(m.get("class")) == grade]
    if type_filter == "vip":
        members = [m for m in members if _norm_type(m.get("account_type")) in {"VIP", "SVIP"} and pkg.vip_active(m)]
    elif type_filter == "free":
        members = [m for m in members if not pkg.vip_active(m)]
    elif type_filter == "pending":
        members = [m for m in members if pkg.package_status(m) == "pending"]
    if dur_filter in dict(pkg.DURATIONS):
        members = [m for m in members if str(m.get("vip_plan") or "").strip().lower() == dur_filter]
    elif dur_filter == "none":
        members = [m for m in members if str(m.get("vip_plan") or "").strip().lower() not in dict(pkg.DURATIONS)]
    if status in {"ON", "OFF"}:
        members = [m for m in members if str(m.get("status", "ON")).upper() == status]

    allm = [m for m in d["members"] if str(m.get("username", "")).strip().casefold() != "admin"]
    counts = {
        "total": len(allm),
        "vip": sum(pkg.vip_active(m) for m in allm),
        "free": sum(not pkg.vip_active(m) for m in allm),
        "on": sum(str(m.get("status", "ON")).upper() == "ON" for m in allm),
        "pending": sum(pkg.package_status(m) == "pending" for m in allm),
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
        typ = _norm_type(m.get("account_type"))
        can_do = bool(getattr(base, "can_practice", lambda *_: False)(m))
        if can_do:
            type_badge = "<span class='badge svip'>⭐ SVIP</span>" if typ == "SVIP" else "<span class='badge vip'>🔑 VIP</span>"
            do_badge = "<span class='badge ok'>xem đáp án + làm bài</span>"
        else:
            type_badge = "<span class='badge free'>FREE</span>"
            do_badge = "<span class='badge no'>chỉ xem đề</span>"
        pst_badge = "<span class='badge pending'>⏳ Chờ duyệt</span>" if pst == "pending" else ""
        cards.append(
            f"<article class='memcard{' wait' if pst=='pending' else ''}'>"
            f"<div class='memtop'><label class='ck'><input type='checkbox' name='selected' value='{su}' form='bulkForm'> "
            f"<b>{name}</b> · {su}</label><span class='muted'>{phone}</span>"
            f"{type_badge}{do_badge}{pst_badge}</div>"
            f"{req_html}"
            f"<form id='row_{su}' class='memform' method='post' action='/admin/members/save'>"
            f"<input type='hidden' name='save_user' value='{su}'>"
            f"<div class='now'>Hiện có: <b>{_safe(pkg.package_label(granted))}</b> · {seen} bài "
            f"<a class='btn small' href='/admin/members/access?user={quote(u)}'>👁 Xem bài</a>"
            f"<div class='muted'>{_safe(pkg.vip_remaining_label(m))}</div></div>"
            + pkg.picker_html(prefix=u, selected=req or granted, student=False, duration=m.get("vip_plan"), expire_at=m.get("vip_expires_at"), started_at=m.get("vip_started_at"))
            + f"<div class='memacts'><select name='status'><option value='ON' {'selected' if st=='ON' else ''}>ON · đang dùng</option><option value='OFF' {'selected' if st=='OFF' else ''}>OFF · khóa</option></select>"
            f"<div class='passrow'><input class='pass' type='password' value='{cur_val}' placeholder='{cur_ph}' readonly autocomplete='off'><button type='button' class='eye' onclick=\"togglePass(this)\">👁</button></div>"
            f"<div class='passrow'><input class='pass' name='new_password' type='password' placeholder='Đặt mật khẩu mới' autocomplete='new-password'><button type='button' class='eye' onclick=\"togglePass(this)\">👁</button></div>"
            f"<button class='btn green' name='intent' value='save'>💾 Lưu / cấp VIP</button>"
            f"<button class='btn red small' name='intent' value='delete' onclick=\"return confirm('Xóa thành viên {su}? Không hoàn tác.')\">🗑 Xóa</button></div></form></article>"
        )

    dup_blocks = []
    for gi, group in enumerate(pkg.duplicate_groups(allm), 1):
        keep0 = str(group[0].get("username") or "")
        drops = "".join(f"<input type='hidden' name='also' value='{_safe(m.get('username'))}'>" for m in group)
        radios = "".join(
            f"<label class='pkgopt'><input type='radio' name='keep' value='{_safe(m.get('username'))}' {'checked' if str(m.get('username'))==keep0 else ''}> "
            f"<b>{_safe(m.get('username'))}</b> · {_safe(m.get('name') or '—')} · {_safe(m.get('phone') or 'không SĐT')} · {_safe(pkg.scope_label(m))}</label>"
            for m in group
        )
        dup_blocks.append(
            f"<div class='dupgroup'><div>Nhóm {gi} · trùng tên hoặc SĐT</div>"
            f"<form method='post' action='/admin/members/merge'>{drops}{radios}"
            f"<button class='btn green' type='submit'>🔗 Gộp vào tài khoản đang chọn</button></form></div>"
        )
    dup_html = (
        f"<div class='dupbox'><h3>⚠️ {len(dup_blocks)} nhóm trùng tên / số điện thoại</h3>"
        "<p class='muted' style='margin:0 0 6px'>Chọn tài khoản giữ lại (nên giữ VIP). Các tài khoản khác trong nhóm sẽ bị xóa sau khi gộp.</p>"
        + "".join(dup_blocks)
        + "</div>"
        if dup_blocks
        else ""
    )

    create = (
        "<details class='createbox'><summary>➕ Cấp thành viên mới (duyệt luôn)</summary>"
        "<form method='post' action='/admin/members/create' class='createform'>"
        "<div class='cgrid'><div class='field'><label>Họ tên</label><input name='name' required></div>"
        "<div class='field'><label>Tài khoản</label><input name='username' required></div>"
        "<div class='field'><label>Điện thoại</label><input name='phone'></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div></div>"
        + pkg.picker_html(student=False)
        + "<button class='btn primary' type='submit'>✅ Tạo và cấp VIP</button></form></details>"
    )

    body = f"""
{pkg.PKG_CSS}{pkg.PKG_JS}
<style>
.adminmembers{{max-width:1100px;margin:auto;padding:12px}}.hero{{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}}.hero h2{{margin:0}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:10px 0}}.stat{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;padding:9px}}.stat b{{display:block;font-size:20px}}.stat span{{font-size:11px;color:#6c7d90;font-weight:800}}.stat.warn b{{color:#a15b00}}
.toolbar,.bulk,.createbox{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;padding:9px;margin:8px 0}}.toolbar{{display:flex;gap:7px;align-items:end;flex-wrap:wrap}}.toolbar .field{{min-width:150px;flex:1}}.toolbar label,.createform label{{display:block;font-size:10px;font-weight:900;color:#6c7d90}}.toolbar input,.toolbar select,.pass,select{{height:34px;border:1px solid #cbd8e6;border-radius:6px;padding:5px;background:#fff}}.toolbar input{{width:100%}}
.memcard{{background:#fff;border:1px solid #d7e2ee;border-radius:12px;padding:10px;margin:8px 0}}.memcard.wait{{border-color:#e0b84a;background:#fffdf6}}.memtop{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}}.ck{{font-weight:800}}.now{{margin:6px 0;font-size:13px}}.memacts{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:8px}}.pass{{width:150px}}.passrow{{display:flex;gap:4px;align-items:center}}.eye{{height:34px;border:1px solid #cbd8e6;background:#fff;border-radius:6px;cursor:pointer}}
.badge{{display:inline-block;border-radius:999px;padding:3px 8px;font-size:10px;font-weight:900}}.badge.pending{{background:#fff4d6;color:#8a5a00}}.badge.approved{{background:#e8f8ee;color:#116a32}}.badge.none,.badge.rejected{{background:#f1f4f8;color:#5d7084}}.badge.vip{{background:#e8f1ff;color:#145bb0}}.badge.svip{{background:#fff4d6;color:#8a5a00}}.badge.free{{background:#f1f4f8;color:#5d7084}}.badge.ok{{background:#e8f8ee;color:#116a32}}.badge.no{{background:#fff1f2;color:#9f1239}}
.btn{{display:inline-block;border:1px solid #b8d5f6;background:#fff;color:#145bb0;border-radius:7px;padding:7px 9px;font-weight:800;cursor:pointer}}.btn.primary{{background:#176bd3;color:#fff}}.btn.green{{background:#179b55;color:#fff;border-color:#128a4a}}.btn.small{{padding:5px 7px;font-size:11px}}.btn.red{{background:#fff;color:#b91c1c;border-color:#fecaca}}
.note{{background:#eef7ff;border:1px solid #b9d5ef;border-radius:9px;padding:9px;margin:8px 0;font-size:12px}}.cgrid{{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}}@media(max-width:800px){{.stats{{grid-template-columns:repeat(2,1fr)}}.cgrid{{grid-template-columns:1fr}}}}
</style>
<div class='adminmembers'><div class='hero'><div><h2>👥 Quản lý thành viên</h2><div class='muted'>Tài khoản VIP / FREE · hạn dùng 3 ngày / 1 tháng / 3 tháng / 1 năm · khóa · mật khẩu</div></div><div><a class='btn primary' href='/admin'>📂 ngan-hang</a> <a class='btn' href='{html.escape(base.github_folder_url(), quote=True)}' target='_blank' rel='noopener'>🐙 GitHub</a> <a class='btn' href='/admin/password'>🔑 Đổi mật khẩu ADMIN</a></div></div>
<div class='stats'><div class='stat'><b>{counts['total']}</b><span>Tổng</span></div><div class='stat warn'><b>{counts['pending']}</b><span>Chờ duyệt</span></div><div class='stat'><b>{counts['vip']}</b><span>VIP</span></div><div class='stat'><b>{counts['free']}</b><span>FREE</span></div><div class='stat'><b>{counts['on']}</b><span>Đang dùng</span></div></div>
<div class='note'>📌 <b>Tài khoản VIP</b> = xem đáp án + làm bài. <b>FREE</b> = chỉ xem đề. <b>Gói</b> là hạn dùng: 3 ngày / 1 tháng / 3 tháng / 1 năm (ô cam: ngày đăng ký — ngày hết hạn). Trùng tên hoặc SĐT hiện ở khung cam — gộp để còn một tài khoản.</div>
{create}
{dup_html}
<form class='toolbar' method='get'><div class='field'><label>TÌM</label><input name='q' value='{_safe(q)}' placeholder='Tài khoản, họ tên, điện thoại'></div><div><label>LỚP</label><select name='grade'><option value=''>Tất cả</option><option value='10' {'selected' if grade=='10' else ''}>10</option><option value='11' {'selected' if grade=='11' else ''}>11</option><option value='12' {'selected' if grade=='12' else ''}>12</option></select></div><div><label>TÀI KHOẢN</label><select name='type'><option value=''>Tất cả</option><option value='vip' {'selected' if type_filter=='vip' else ''}>VIP</option><option value='free' {'selected' if type_filter=='free' else ''}>FREE</option><option value='pending' {'selected' if type_filter=='pending' else ''}>Chờ duyệt</option></select></div><div><label>GÓI · HẠN DÙNG</label><select name='dur'><option value=''>Tất cả</option><option value='3d' {'selected' if dur_filter=='3d' else ''}>3 ngày</option><option value='1m' {'selected' if dur_filter=='1m' else ''}>1 tháng</option><option value='3m' {'selected' if dur_filter=='3m' else ''}>3 tháng</option><option value='1y' {'selected' if dur_filter=='1y' else ''}>1 năm</option><option value='none' {'selected' if dur_filter=='none' else ''}>Chưa có hạn</option></select></div><div><label>TRẠNG THÁI</label><select name='status'><option value=''>Tất cả</option><option value='ON' {'selected' if status=='ON' else ''}>Đang dùng</option><option value='OFF' {'selected' if status=='OFF' else ''}>Khóa</option></select></div><button class='btn primary'>🔎 Lọc</button><a class='btn' href='/admin/members'>↻ Tất cả</a></form>
<form id='bulkForm' method='post' action='/admin/members/bulk'></form>
<div class='bulk'><b>⚡ Đã chọn:</b> <button class='btn green' name='intent' value='approve' form='bulkForm'>✅ Duyệt yêu cầu</button> <button class='btn' name='intent' value='off' form='bulkForm'>Khóa</button> <button class='btn' name='intent' value='on' form='bulkForm'>Mở</button> <button class='btn red' name='intent' value='delete' form='bulkForm' onclick="return confirm('Xóa các thành viên đang tick?')">🗑 Xóa đã chọn</button></div>
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
    do_lab = "VIP · làm bài + xem đáp án" if getattr(base, "can_practice", lambda *_: False)(m) else "FREE · chỉ xem đề"
    body = f"""
<div class='wrap'><div class='panel'><div class='head'>👁 Quyền xem của học viên</div><div class='body'><div class='notice'><b>{_safe(m.get('name') or username)}</b> · <b>{_safe(username)}</b> · Gói <b>{_safe(pkg.scope_label(m))}</b> · <b>{_safe(do_lab)}</b> · Được xem <b>{len(allowed)}</b> / {len(all_items)} bài · Bị khóa <b>{hidden}</b> bài</div>{''.join(blocks)}<p><a class='btn' href='/admin/members'>← Quản lý thành viên</a></p></div></div></div>
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
    if intent == "delete":
        d["members"] = [m for m in d["members"] if str(m.get("username", "")) != username]
        _save_members(d, f"ADMIN xóa thành viên {username}")
        return redirect("/admin/members")
    if intent == "reject":
        target["package_status"] = "rejected"
        target["requested_package"] = None
        target["account_type"] = "FREE"
        target["package"] = None
        target["vip_expires_at"] = ""
        target["vip_plan"] = ""
    elif intent == "approve":
        chosen = pkg.requested_package(target)
        if not chosen:
            chosen, err = pkg.package_from_form(request.form, prefix=username, student=False)
            if err:
                return base.page("ADMIN", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(err)}</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
        pkg.apply_granted(target, chosen, approved=True, duration=pkg.duration_from_form(request.form, prefix=username))
        target["status"] = "ON"
    else:
        chosen, err = pkg.package_from_form(request.form, prefix=username, student=False)
        if err:
            return base.page("ADMIN", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(err)}</div><a class='btn' href='/admin/members'>Quay lại</a></div></div>")
        pkg.apply_granted(target, chosen, approved=True, duration=pkg.duration_from_form(request.form, prefix=username))
    target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_members(d, f"ADMIN cấp gói {username}")
    return redirect("/admin/members")


def _merge_members():
    d = _members()
    keep_u = str(request.form.get("keep") or "").strip()
    also = [str(x).strip() for x in request.form.getlist("also") if str(x).strip()]
    if keep_u not in also:
        also.append(keep_u)
    by_u = {str(m.get("username") or "").strip(): m for m in d["members"]}
    keep = by_u.get(keep_u)
    if not keep or keep_u.casefold() == "admin":
        return redirect("/admin/members")
    extras = [by_u[u] for u in also if u != keep_u and u in by_u and u.casefold() != "admin"]
    if not extras:
        return redirect("/admin/members")
    pkg.merge_members(keep, extras)
    drop = {str(x.get("username") or "") for x in extras}
    d["members"] = [m for m in d["members"] if str(m.get("username") or "") not in drop]
    keep["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_members(d, f"ADMIN gộp thành viên vào {keep_u}")
    return redirect("/admin/members")
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
        elif intent == "delete":
            continue
        elif intent == "approve":
            chosen = pkg.requested_package(m) or pkg.granted_package(m)
            if chosen:
                pkg.apply_granted(m, chosen, approved=True, duration=pkg.duration_from_form(request.form) or "1m")
                m["status"] = "ON"
        m["updated_at"] = now
    if intent == "delete":
        d["members"] = [
            m for m in d["members"]
            if str(m.get("username")) not in selected or str(m.get("username")).casefold() == "admin"
        ]
        if selected:
            _save_members(d, "ADMIN xóa thành viên hàng loạt")
        return redirect("/admin/members")
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
    pkg.apply_granted(rec, chosen, approved=True, duration=pkg.duration_from_form(request.form) or "1m")
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
    try:
        if base.can_manage_bank():
            return redirect("/admin/members")
    except Exception:
        pass
    return redirect("/member/login")


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
    if p == "/admin/members/merge" and request.method == "POST": return _merge_members()
    if p == "/admin/password": return _admin_password_page()
    return None


# Replace the old admin login view; route rule remains /admin/login.
if "admin_login" in app.view_functions:
    app.view_functions["admin_login"] = _admin_login
app.add_url_rule("/admin/members/merge", "admin_members_merge", _merge_members, methods=["POST"])

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


# Mobile-only enhancement: leaves desktop/admin business logic unchanged.
_ADMIN_MOBILE_CSS = r"""
<style id="admin-mobile-ux">
@media (max-width: 700px) {
  html,body { max-width:100%; overflow-x:hidden; }
  .adminmembers,.wrap { width:100%; max-width:100%; padding:8px!important; }
  .adminmembers .hero { gap:8px; align-items:stretch; }
  .adminmembers .hero > div { min-width:0; }
  .adminmembers .hero > div:last-child { display:flex; overflow-x:auto; flex-wrap:nowrap; gap:6px; padding-bottom:4px; -webkit-overflow-scrolling:touch; }
  .adminmembers .hero > div:last-child .btn { flex:0 0 auto; white-space:nowrap; }
  .adminmembers .stats { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px; }
  .adminmembers .stat { padding:8px; }
  .adminmembers .stat b { font-size:18px; }
  .adminmembers .toolbar { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; align-items:end; }
  .adminmembers .toolbar .field { min-width:0; }
  .adminmembers .toolbar > :first-child { grid-column:1/-1; }
  .adminmembers .toolbar input,.adminmembers .toolbar select { width:100%; min-width:0; min-height:44px; font-size:16px; }
  .adminmembers .toolbar .btn { min-height:44px; text-align:center; }
  .adminmembers .memcard { padding:9px; }
  .adminmembers .memtop { align-items:flex-start; justify-content:flex-start; gap:6px; }
  .adminmembers .memtop .ck { flex-basis:100%; overflow-wrap:anywhere; }
  .adminmembers .memacts { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:7px; }
  .adminmembers .memacts > select,.adminmembers .memacts > .passrow { grid-column:1/-1; width:100%; }
  .adminmembers .passrow input { flex:1; min-width:0; width:100%; font-size:16px; }
  .adminmembers .passrow .eye { min-width:44px; min-height:44px; }
  .adminmembers .memacts .btn { min-height:44px; white-space:normal; }
  .adminmembers .bulk { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
  .adminmembers .bulk .btn { min-height:42px; flex:1 1 40%; }
  .adminmembers .createbox summary,.adminmembers .memcard .mobile-member-toggle { min-height:44px; cursor:pointer; }
  .adminmembers .memcard .mobile-member-toggle { display:flex; align-items:center; justify-content:space-between; width:100%; background:#eef5ff; color:#145bb0; border:1px solid #c7ddf6; border-radius:8px; padding:10px 12px; font:700 13px/1.3 inherit; margin:8px 0 0; }
  .adminmembers .memcard.mobile-collapsed .memform { display:none; }
  .adminmembers .memcard .pendcard { overflow-wrap:anywhere; }
  .adminmembers .note { font-size:12px; }
  .adminmembers .cgrid { grid-template-columns:1fr; }
  .adminmembers input,.adminmembers select,.adminmembers button { max-width:100%; }
  .adminmembers .pkgopt,.adminmembers .pkg-picker { max-width:100%; }
  .adminmembers .stats .stat:last-child { grid-column:auto; }
  .panel,.bankwrap,.selectgrid { max-width:100%; }
  .bankwrap { overflow-x:auto; -webkit-overflow-scrolling:touch; }
  textarea,input[type="text"],input[type="search"],input[type="number"],input[type="password"],select { font-size:16px; }
  button,a.btn,button.btn { touch-action:manipulation; }
}
@media (min-width:701px) { .mobile-member-toggle { display:none!important; } }
</style>
"""
_ADMIN_MOBILE_JS = r"""
<script id="admin-mobile-controls">
(function(){
  function setup(){
    if (!window.matchMedia || !window.matchMedia('(max-width:700px)').matches) return;
    document.querySelectorAll('.adminmembers .memcard').forEach(function(card,idx){
      if(card.querySelector('.mobile-member-toggle')) return;
      var form=card.querySelector('.memform');
      if(!form) return;
      if(!form.id) form.id='mobile-member-form-'+idx;
      var btn=document.createElement('button');
      btn.type='button';
      btn.className='mobile-member-toggle';
      btn.setAttribute('aria-controls',form.id);
      var open=card.classList.contains('wait');
      function render(){
        card.classList.toggle('mobile-collapsed',!open);
        btn.setAttribute('aria-expanded',String(open));
        btn.textContent=open?'Thu gọn chỉnh sửa ▲':'Chỉnh sửa / cấp quyền ▼';
      }
      btn.addEventListener('click',function(){open=!open;render();});
      form.parentNode.insertBefore(btn,form);
      render();
    });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',setup);
  else setup();
})();
</script>
"""

@app.after_request
def _admin_mobile_response(response):
    """Add small-screen layout enhancements only to authenticated admin HTML views."""
    if not request.path.startswith("/admin"):
        return response
    if response.status_code != 200 or not response.mimetype == "text/html":
        return response
    if not _is_admin_session():
        return response
    try:
        body = response.get_data(as_text=True)
        if 'id="admin-mobile-ux"' in body:
            return response
        if "</head>" in body:
            body = body.replace("</head>", _ADMIN_MOBILE_CSS + "</head>", 1)
        elif "</body>" in body:
            body = body.replace("</body>", _ADMIN_MOBILE_CSS + "</body>", 1)
        else:
            return response
        body = body.replace("</body>", _ADMIN_MOBILE_JS + "</body>", 1)
        response.set_data(body)
        response.headers.pop("Content-Length", None)
    except Exception:
        pass
    return response


# Six-tile mobile ADMIN home. Desktop retains the existing bank interface.
@app.after_request
def mobile_admin_dashboard(response):
    if request.path != "/admin" or request.method != "GET":
        return response
    if response.status_code != 200 or response.mimetype != "text/html" or not _is_admin_session():
        return response
    try:
        import json
        records=[]
        for x in base.list_bank_tex():
            records.append([
                str(x.get("Mon") or ""),
                str(x.get("Lop") or ""),
                str(x.get("Chuong") or ""),
                str(x.get("BaiHoc") or x.get("De") or ""),
                str(x.get("path") or "")
            ])
        ui = """
<style id="mobile-home-style">
.mhome{display:none}
@media(max-width:760px){
 .mhome{display:block;max-width:480px;margin:auto;padding:12px 12px 90px;font-family:Arial,sans-serif;color:#18344e}
 body:has(.mhome:not(.showbank)) .wrap{display:none!important}
 .mhome.showbank{display:none}
 .mhome *{box-sizing:border-box}
 .mhead{background:#132f4c;color:white;border-radius:10px;padding:14px}
 .mhead b{font-size:15px}.mhead small{display:block;margin:4px 0 9px}
 .mhead form{display:flex;align-items:center;background:white;border-radius:8px;padding:0 8px}
 .mhead input{width:100%;border:0;outline:0;min-height:44px;font-size:16px}
 .mhead button{border:0;background:none;font-size:20px;min-width:35px}
 .mhome h3{font-size:14px;margin:15px 0 9px}
 .mtiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
 .mtiles a{min-height:78px;border:1px solid #d7dfe8;border-radius:10px;background:#fff;color:#193955;text-decoration:none;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:7px;font-size:12px;font-weight:650;padding:8px}
 .mtiles strong{font-size:22px;font-weight:400}
 .mfilt{background:#f3f5f8;border:1px solid #d8dfe7;border-radius:11px;padding:12px;margin-top:12px}
 .mfilt h3{margin:0 0 9px}
 .mselects{display:grid;grid-template-columns:1fr 1fr;gap:8px}
 .mselects select{width:100%;min-width:0;border:1px solid #dce3ea;background:white;border-radius:8px;padding:10px 8px;min-height:44px;font-size:14px}
 .mselects .wide{grid-column:1/-1}
 .mgo{display:block;margin-top:9px;background:#176bd3;color:white;text-decoration:none;text-align:center;padding:12px;border-radius:8px;font-weight:700;font-size:13px}
 .mnav{position:fixed;bottom:0;left:0;right:0;z-index:2000;background:white;border-top:1px solid #d5dee8;display:flex;justify-content:space-around;padding:8px 4px calc(8px + env(safe-area-inset-bottom))}
 .mnav a{text-align:center;color:#38516e;text-decoration:none;font-size:11px;min-width:65px}
 .mnav span{display:block;font-size:19px;margin-bottom:3px}
}
</style>
<section class="mhome __STATE__" aria-label="Quản trị điện thoại">
 <div class="mhead"><b>Lớp Học Thầy Minh</b><small>Quản trị hệ thống</small>
  <form action="/admin"><input type="hidden" name="view" value="bank"><input type="search" name="q" placeholder="⌕ Tìm học sinh, bài tập, đề thi..." aria-label="Tìm file"><button aria-label="Tìm">→</button></form>
 </div>
 <h3>Truy cập nhanh</h3>
 <nav class="mtiles">
  <a href="/admin/members"><strong>♙</strong>Học sinh</a>
  <a href="/admin?view=bank"><strong>▣</strong>Ngân hàng câu hỏi</a>
  <a href="/admin?view=bank"><strong>▤</strong>Quản lý đề thi</a>
  <a href="/admin/results"><strong>▥</strong>Kết quả học tập</a>
  <a href="/admin/members?type=pending"><strong>♧</strong>Duyệt tài khoản</a>
  <a href="/admin/password"><strong>⚙</strong>Cài đặt</a>
 </nav>
 <div class="mfilt"><h3>Bộ lọc nhanh</h3><div class="mselects">
  <select id="msub" aria-label="Môn"></select><select id="mgrade" aria-label="Lớp"></select>
  <select id="mchapter" class="wide" aria-label="Chương"></select>
  <select id="mlesson" class="wide" aria-label="Bài"></select>
 </div><a class="mgo" id="mgo" href="/admin?view=bank">Mở bài đã chọn →</a></div>
 <nav class="mnav"><a href="/admin"><span>⌂</span>Trang chủ</a><a href="/admin?view=bank"><span>▣</span>Bài tập</a><a href="/admin/members"><span>♙</span>Học sinh</a><a href="/admin/ly-thuyet"><span>☷</span>Thêm</a></nav>
</section>
<script id="mobile-home-script">
(function(){
const rows=__ROWS__;
const nodes=['msub','mgrade','mchapter','mlesson'].map(id=>document.getElementById(id));
const go=document.getElementById('mgo');
if(nodes.some(x=>!x))return;
function fill(i){const el=nodes[i],old=el.value;el.replaceChildren(new Option(['Tất cả môn','Tất cả lớp','Tất cả chương','Tất cả bài'][i],''));const set=new Set(rows.filter(row=>nodes.every((node,j)=>j>=i||!node.value||row[j]===node.value)).map(row=>row[i]));Array.from(set).filter(Boolean).sort((a,b)=>a.localeCompare(b,'vi')).forEach(v=>el.add(new Option(v,v)));if(Array.from(el.options).some(o=>o.value===old))el.value=old;}
function change(i){for(let j=i+1;j<4;j++)fill(j);const match=rows.find(row=>nodes.every((el,k)=>!el.value||row[k]===el.value));const key=nodes[3].value&&match?match[4]:nodes.slice().reverse().find(el=>el.value)?.value||'';go.href='/admin?view=bank&q='+encodeURIComponent(key);}
nodes.forEach((el,i)=>el.addEventListener('change',()=>change(i)));
fill(0);change(0);
})();
</script>
"""
        state = "showbank" if request.args.get("view") == "bank" else ""
        ui = ui.replace("__STATE__", state).replace("__ROWS__", json.dumps(records, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e"))
        body=response.get_data(as_text=True)
        if "</body>" not in body:
            return response
        body=body.replace("</body>", ui+"</body>", 1)
        response.set_data(body)
        response.headers.pop("Content-Length",None)
    except Exception:
        pass
    return response
