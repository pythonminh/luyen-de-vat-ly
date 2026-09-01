# -*- coding: utf-8 -*-
"""ADMIN-only member management and practice-result viewer."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import threading
import time
import urllib.parse
from pathlib import Path

from flask import jsonify, redirect, request, session
from app import app, page, members_data, member_current, admin_current, gh_api, BRANCH, MEMBERS_FILE

_LOCK = threading.Lock()
_RESULTS_FILE = Path(__file__).resolve().parent / "attempts_runtime.json"


def _load_results():
    try:
        data = json.loads(_RESULTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_results(rows):
    with _LOCK:
        _RESULTS_FILE.write_text(json.dumps(rows[-2000:], ensure_ascii=False, indent=2), encoding="utf-8")


def _save_members(data):
    d = gh_api(f"contents/{urllib.parse.quote('members.json', safe='/')}?ref={urllib.parse.quote(BRANCH)}")
    payload = {
        "message": "ADMIN cập nhật tài khoản thành viên",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": d.get("sha", ""),
    }
    gh_api(f"contents/members.json?ref={urllib.parse.quote(BRANCH)}", "PUT", payload)


def _admin_guard():
    return admin_current()


def admin_members():
    if not _admin_guard():
        return redirect("/admin/login")
    rows = []
    for i, m in enumerate(members_data().get("members", [])):
        u = str(m.get("username", "")); name = str(m.get("name", "")); cls = str(m.get("class", ""))
        typ = str(m.get("account_type", "FREE")).upper(); status = str(m.get("status", "ON")).upper()
        import re
        gm = re.search(r"(?<!\d)(10|11|12)(?!\d)", cls.upper())
        grade = gm.group(1) if gm else ""
        safe_u = html.escape(u, quote=True)
        rows.append(
            "<tr>"
            f"<td><b>{html.escape(u)}</b><input type='hidden' name='username' value='{safe_u}'></td>"
            f"<td>{html.escape(name)}</td>"
            f"<td><select name='class_{safe_u}'>"
            f"<option value='' {'selected' if not grade else ''}>Chưa cấp</option>"
            f"<option value='10' {'selected' if grade=='10' else ''}>10</option>"
            f"<option value='11' {'selected' if grade=='11' else ''}>11</option>"
            f"<option value='12' {'selected' if grade=='12' else ''}>12</option>"
            "</select></td>"
            f"<td><select name='account_type_{safe_u}'>"
            f"<option {'selected' if typ=='FREE' else ''}>FREE</option>"
            f"<option {'selected' if typ=='VIP' else ''}>VIP</option>"
            f"<option {'selected' if typ in {'SVIP','S.VIP','S-VIP'} else ''}>SVIP</option>"
            "</select></td>"
            f"<td><select name='status_{safe_u}'>"
            f"<option {'selected' if status=='ON' else ''}>ON</option><option {'selected' if status=='OFF' else ''}>OFF</option>"
            "</select></td>"
            f"<td><input name='new_password_{safe_u}' type='password' placeholder='Mật khẩu mới (bỏ trống = giữ nguyên)'></td>"
            f"<td><button class='btn green' name='save_user' value='{safe_u}'>💾 Lưu</button></td>"
            "</tr>"
        )
    body = (
        "<div class='wrap'><div class='panel'><div class='head'>👥 ADMIN · Quản lý thành viên</div><div class='body'>"
        "<div class='notice'>ADMIN có thể cấp <b>lớp 10/11/12</b>, đổi <b>FREE/VIP/SVIP</b>, bật/tắt tài khoản và đặt lại mật khẩu. <b>SVIP</b> được xem toàn bộ khối lớp.</div>"
        "<form method='post' action='/admin/members/save'><div style='overflow:auto;margin-top:10px'><table class='selectgrid'>"
        "<tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th><th>Mật khẩu mới</th><th></th></tr>"
        + "".join(rows) +
        "</table></div></form>"
        "<p><a class='btn' href='/admin'>← ADMIN</a> <a class='btn' href='/admin/results'>📊 Bài làm học viên</a></p>"
        "</div></div></div>"
    )
    return page("Quản lý thành viên", body)


@app.get('/admin/members')
def _admin_members_route():
    return admin_members()


@app.post('/admin/members/save')
def _admin_members_save():
    if not _admin_guard():
        return redirect('/admin/login')
    username = (request.form.get('save_user') or '').strip()
    if not username:
        return redirect('/admin/members')
    data = members_data(); target = next((m for m in data.get('members', []) if str(m.get('username','')).strip() == username), None)
    if not target:
        return page('ADMIN', "<div class='wrap'><div class='panel'><div class='body err'>Không tìm thấy tài khoản.</div></div></div>")
    account_type = (request.form.get(f'account_type_{username}') or target.get('account_type') or 'FREE').upper()
    if account_type in {'S.VIP','S-VIP'}:
        account_type = 'SVIP'
    if account_type not in {'FREE','VIP','SVIP'}:
        account_type = 'FREE'
    target['account_type'] = account_type
    target['status'] = (request.form.get(f'status_{username}') or target.get('status') or 'ON').upper()
    class_value = (request.form.get(f'class_{username}') or '').strip().upper()
    if class_value in {'10','11','12'}:
        target['class'] = class_value
        target['grade'] = class_value
    elif class_value == '':
        target['class'] = ''
        target['grade'] = ''
    new_password = request.form.get(f'new_password_{username}') or ''
    if new_password:
        target['password_sha256'] = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
    try:
        _save_members(data)
        return page('ADMIN', "<div class='wrap'><div class='panel'><div class='body'><div class='success'>✅ Đã cập nhật tài khoản, lớp và quyền; đồng bộ members.json lên GitHub.</div><a class='btn' href='/admin/members'>← Quản lý thành viên</a></div></div></div>")
    except Exception as e:
        return page('ADMIN lỗi', f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>"), 500


def admin_results():
    if not _admin_guard():
        return redirect("/admin/login")
    rows = _load_results()
    rows = list(reversed(rows))
    filt = (request.args.get('username') or '').strip()
    if filt:
        rows = [r for r in rows if str(r.get('username','')) == filt]
    body_rows=[]
    for r in rows[:500]:
        status = '✅ ĐÚNG' if r.get('ok') else '❌ SAI'
        body_rows.append(
            "<tr>"
            f"<td>{html.escape(str(r.get('time','')))}</td>"
            f"<td><b>{html.escape(str(r.get('username','')))}</b></td>"
            f"<td>{html.escape(str(r.get('name','')))}</td>"
            f"<td>{html.escape(str(r.get('kind','')))}</td>"
            f"<td>{html.escape(str(r.get('dang','')))}</td>"
            f"<td class='{'good' if r.get('ok') else 'bad'}'>{status}</td>"
            f"<td>{html.escape(str(r.get('student','')))}</td>"
            f"<td><details><summary>Xem câu</summary>{html.escape(str(r.get('text','')))}<hr><b>Lời giải:</b><br>{html.escape(str(r.get('solution','')))}</details></td>"
            "</tr>"
        )
    users = sorted({str(r.get('username','')) for r in _load_results() if r.get('username')})
    opts = "<option value=''>Tất cả học viên</option>" + "".join(f"<option value='{html.escape(u, quote=True)}' {'selected' if u==filt else ''}>{html.escape(u)}</option>" for u in users)
    body=(
        "<div class='wrap'><div class='panel'><div class='head'>📊 ADMIN · Xem bài làm học viên</div><div class='body'>"
        "<form method='get' style='display:flex;gap:8px;flex-wrap:wrap'>"
        f"<select name='username'>{opts}</select><button class='btn'>Lọc</button></form>"
        "<div class='notice' style='margin-top:10px'>Hiện lưu kết quả luyện tập ở bộ nhớ tệp của máy chủ Render; dữ liệu có thể mất khi service khởi động/deploy lại.</div>"
        "<div style='overflow:auto;margin-top:10px'><table class='selectgrid'><tr><th>Thời gian</th><th>Tài khoản</th><th>Họ tên</th><th>Loại</th><th>Dạng</th><th>Kết quả</th><th>HS trả lời</th><th>Câu / lời giải</th></tr>"
        + "".join(body_rows) + "</table></div>"
        "<p><a class='btn' href='/admin'>← ADMIN</a> <a class='btn' href='/admin/members'>👥 Thành viên</a></p>"
        "</div></div></div>"
    )
    return page('Bài làm học viên', body)


@app.get('/admin/results')
def _admin_results_route():
    return admin_results()


# Wrap the existing answer endpoint so ADMIN can inspect student work without
# storing Gemini/API keys. The question-bank flow remains GitHub-only.
_original_answer = app.view_functions.get('answer')
if _original_answer:
    def answer_with_admin_log(*args, **kwargs):
        resp = _original_answer(*args, **kwargs)
        try:
            if session.get('role') == 'member':
                d = request.get_json(silent=True) or {}
                m = member_current() or {}
                rows = _load_results()
                rows.append({
                    'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'username': session.get('username',''),
                    'name': m.get('name',''),
                    'ok': bool(d.get('ok')),
                    'student': str(d.get('student') or ''),
                    'text': str(d.get('text') or ''),
                    'solution': str(d.get('solution') or ''),
                    'kind': str(d.get('kind') or ''),
                    'dang': str(d.get('dang') or ''),
                })
                _save_results(rows)
        except Exception:
            pass
        return resp
    app.view_functions['answer'] = answer_with_admin_log
