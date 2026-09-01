# -*- coding: utf-8 -*-
"""ADMIN: quản lý thành viên, phân quyền và xem kết quả luyện tập."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import threading
import time
import urllib.parse
from pathlib import Path

from flask import redirect, request, session
from app import app, page, members_data, member_current, admin_current, gh_api, BRANCH

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
    d = gh_api(f"contents/members.json?ref={urllib.parse.quote(BRANCH)}")
    payload = {
        "message": "ADMIN cập nhật quyền thành viên",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": d.get("sha", ""),
    }
    gh_api("contents/members.json", "PUT", payload)


def _admin_guard():
    return admin_current()


def _norm_type(value):
    value = str(value or "FREE").strip().upper().replace(".", "").replace("-", "")
    return {"SVIP": "SVIP", "VIP": "VIP", "FREE": "FREE"}.get(value, "FREE")


def _norm_class(value):
    value = str(value or "").strip().upper()
    return value if value in {"10", "11", "12"} else ""


def _member_class(m):
    value = str(m.get("class", m.get("grade", "")) or "").upper()
    for g in ("10", "11", "12"):
        if value == g or f"LỚP {g}" in value or f"LOP {g}" in value:
            return g
    return ""


def _safe_user(u):
    return html.escape(str(u), quote=True)


def _admin_members_html():
    data = members_data()
    members = list(data.get("members", []))
    q = (request.args.get("q") or "").strip().lower()
    grade_filter = (request.args.get("grade") or "").strip()
    type_filter = _norm_type(request.args.get("type")) if request.args.get("type") else ""
    status_filter = (request.args.get("status") or "").strip().upper()

    if q:
        members = [m for m in members if q in str(m.get("username", "")).lower() or q in str(m.get("name", "")).lower() or q in str(m.get("phone", "")).lower()]
    if grade_filter:
        members = [m for m in members if _member_class(m) == grade_filter]
    if type_filter:
        members = [m for m in members if _norm_type(m.get("account_type")) == type_filter]
    if status_filter in {"ON", "OFF"}:
        members = [m for m in members if str(m.get("status", "ON")).upper() == status_filter]

    all_members = list(data.get("members", []))
    total = len(all_members)
    counts = {
        "ON": sum(str(m.get("status", "ON")).upper() == "ON" for m in all_members),
        "FREE": sum(_norm_type(m.get("account_type")) == "FREE" for m in all_members),
        "VIP": sum(_norm_type(m.get("account_type")) == "VIP" for m in all_members),
        "SVIP": sum(_norm_type(m.get("account_type")) == "SVIP" for m in all_members),
        "10": sum(_member_class(m) == "10" for m in all_members),
        "11": sum(_member_class(m) == "11" for m in all_members),
        "12": sum(_member_class(m) == "12" for m in all_members),
    }

    cards = (
        f"<div class='statgrid'>"
        f"<div class='stat'><b>{total}</b><span>Tổng thành viên</span></div>"
        f"<div class='stat on'><b>{counts['ON']}</b><span>Đang hoạt động</span></div>"
        f"<div class='stat free'><b>{counts['FREE']}</b><span>FREE</span></div>"
        f"<div class='stat vip'><b>{counts['VIP']}</b><span>VIP</span></div>"
        f"<div class='stat svip'><b>{counts['SVIP']}</b><span>SVIP · toàn bộ</span></div>"
        f"<div class='stat'><b>10:{counts['10']} · 11:{counts['11']} · 12:{counts['12']}</b><span>Phân bố lớp</span></div>"
        "</div>"
    )

    rows = []
    for m in members:
        u = str(m.get("username", "")).strip()
        if not u:
            continue
        su = _safe_user(u)
        name = str(m.get("name", "")).strip() or "—"
        phone = str(m.get("phone", "")).strip() or "—"
        grade = _member_class(m)
        typ = _norm_type(m.get("account_type"))
        status = str(m.get("status", "ON")).upper()
        updated = str(m.get("updated_at", "")).strip() or "Chưa ghi nhận"
        type_badge = "<span class='badge svip'>⭐ SVIP</span>" if typ == "SVIP" else ("<span class='badge vip'>🔑 VIP</span>" if typ == "VIP" else "<span class='badge free'>FREE</span>")
        status_badge = "<span class='badge on'>● Đang dùng</span>" if status == "ON" else "<span class='badge off'>● Khóa</span>"
        rows.append(
            "<tr>"
            f"<td class='check'><input type='checkbox' name='selected' value='{su}' form='bulkForm'></td>"
            f"<td><b>{html.escape(u)}</b><small>{html.escape(name)}</small></td>"
            f"<td>{html.escape(phone)}</td>"
            f"<td><select class='mini' name='class_{su}' form='row_{su}'><option value=''>Chưa cấp</option><option value='10' {'selected' if grade=='10' else ''}>10</option><option value='11' {'selected' if grade=='11' else ''}>11</option><option value='12' {'selected' if grade=='12' else ''}>12</option></select></td>"
            f"<td>{type_badge}<select class='mini' name='account_type' form='row_{su}'><option value='FREE' {'selected' if typ=='FREE' else ''}>FREE</option><option value='VIP' {'selected' if typ=='VIP' else ''}>VIP</option><option value='SVIP' {'selected' if typ=='SVIP' else ''}>SVIP</option></select></td>"
            f"<td>{status_badge}<select class='mini' name='status' form='row_{su}'><option value='ON' {'selected' if status=='ON' else ''}>ON</option><option value='OFF' {'selected' if status=='OFF' else ''}>OFF</option></select></td>"
            f"<td><input class='pass' name='new_password' form='row_{su}' type='password' placeholder='Đổi mật khẩu'></td>"
            f"<td><span class='updated'>{html.escape(updated)}</span><form id='row_{su}' method='post' action='/admin/members/save'><input type='hidden' name='save_user' value='{su}'><button class='btn green small' type='submit'>💾 Lưu</button></form></td>"
            "</tr>"
        )

    empty = "<tr><td colspan='8' class='empty'>Không tìm thấy thành viên phù hợp.</td></tr>" if not rows else ""
    query_keep = html.escape(request.args.get("q", ""), quote=True)
    body = f"""
    <style>
    .adminmembers{{max-width:1500px;margin:auto;padding:12px}}
    .hero{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px}}
    .hero h2{{margin:0;font-size:20px}}.hero p{{margin:2px 0 0;color:#68798d;font-size:12px}}
    .statgrid{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:10px 0}}
    .stat{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;padding:10px 11px}.stat b{{display:block;font-size:20px;color:#164f8d}}.stat span{{font-size:11px;color:#697b8f;font-weight:800}}.stat.on b{{color:#159447}}.stat.free b{{color:#16814a}}.stat.vip b{{color:#a2175f}}.stat.svip b{{color:#825500}}
    .toolbar{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;padding:10px;margin-bottom:10px;display:flex;gap:7px;align-items:end;flex-wrap:wrap}}.toolbar .field{{min-width:145px}}.toolbar .field.search{{flex:1;min-width:240px}}.toolbar label{{display:block;font-size:10px;color:#6c7d90;font-weight:900;margin-bottom:3px}}.toolbar input,.toolbar select{{width:100%;height:36px;border:1px solid #cbd8e6;border-radius:7px;padding:7px;background:#fff}}
    .bulk{{display:flex;align-items:center;gap:7px;flex-wrap:wrap;background:#f4f9ff;border:1px solid #b9d5ef;border-radius:9px;padding:9px;margin-bottom:10px}}.bulk b{{margin-right:5px}}.bulk select{{height:34px;border:1px solid #bfd0e2;border-radius:7px;padding:5px}}
    .membertable{{background:#fff;border:1px solid #d7e2ee;border-radius:10px;overflow:auto}}.membertable table{{min-width:1100px}}.membertable th{{position:sticky;top:0;z-index:1}}.membertable td small{{display:block;color:#718196;margin-top:2px}}.membertable .check{{width:35px;text-align:center}}.membertable .mini{{margin-top:4px;width:82px;padding:5px;border:1px solid #cbd8e6;border-radius:6px;background:#fff}}.membertable .pass{{width:140px;padding:6px;border:1px solid #cbd8e6;border-radius:6px}}.badge{{display:inline-block;border-radius:999px;padding:3px 7px;font-size:10px;font-weight:900;margin-right:5px;white-space:nowrap}}.badge.free{{background:#eefbf2;color:#14743a;border:1px solid #83d39e}}.badge.vip{{background:#fff0f7;color:#a2175f;border:1px solid #eaa3c9}}.badge.svip{{background:#fff7dc;color:#855a00;border:1px solid #e9c56d}}.badge.on{{background:#eaf8ef;color:#116a32;border:1px solid #8ed1a2}}.badge.off{{background:#fff0f1;color:#a41f28;border:1px solid #efa2a8}}.updated{{display:block;color:#78899b;font-size:9px;margin-bottom:3px}}.small{{padding:6px 9px;font-size:11px}}.empty{{text-align:center;padding:30px;color:#75869a}}
    .tip{{background:#fffdf3;border:1px solid #ecd68c;border-radius:9px;padding:9px;margin-bottom:10px;font-size:12px}}.tip strong{{color:#805700}}
    @media(max-width:1000px){{.statgrid{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:600px){{.statgrid{{grid-template-columns:repeat(2,1fr)}}.adminmembers{{padding:7px}}.hero h2{{font-size:17px}}}}
    </style>
    <div class='adminmembers'>
      <div class='hero'><div><h2>👥 Thành viên</h2><p>ADMIN quản lý tập trung · lớp · quyền · trạng thái · mật khẩu</p></div><div><a class='btn' href='/admin'>← ADMIN</a> <a class='btn' href='/admin/results'>📊 Bài làm</a></div></div>
      {cards}
      <div class='tip'>💡 <strong>SVIP = xem toàn bộ khối 10, 11, 12.</strong> FREE/VIP chỉ xem đúng khối lớp ADMIN cấp. Mọi thay đổi quyền/lớp đều được ghi thời gian và đồng bộ vào <b>members.json</b>.</div>
      <form class='toolbar' method='get'>
        <div class='field search'><label>TÌM HỌC VIÊN</label><input name='q' value='{query_keep}' placeholder='Tên, tài khoản hoặc số điện thoại...'></div>
        <div class='field'><label>LỚP</label><select name='grade'><option value=''>Tất cả lớp</option><option value='10' {'selected' if grade_filter=='10' else ''}>Lớp 10</option><option value='11' {'selected' if grade_filter=='11' else ''}>Lớp 11</option><option value='12' {'selected' if grade_filter=='12' else ''}>Lớp 12</option></select></div>
        <div class='field'><label>QUYỀN</label><select name='type'><option value=''>Tất cả quyền</option><option value='FREE' {'selected' if type_filter=='FREE' else ''}>FREE</option><option value='VIP' {'selected' if type_filter=='VIP' else ''}>VIP</option><option value='SVIP' {'selected' if type_filter=='SVIP' else ''}>SVIP</option></select></div>
        <div class='field'><label>TRẠNG THÁI</label><select name='status'><option value=''>Tất cả</option><option value='ON' {'selected' if status_filter=='ON' else ''}>Đang dùng</option><option value='OFF' {'selected' if status_filter=='OFF' else ''}>Khóa</option></select></div>
        <button class='btn primary' type='submit'>🔎 Lọc</button><a class='btn' href='/admin/members'>↻ Tất cả</a>
      </form>
      <form id='bulkForm' method='post' action='/admin/members/bulk'></form>
      <div class='bulk'><b>⚡ Cấp nhanh cho các dòng đã chọn:</b><select name='account_type' form='bulkForm'><option value=''>Giữ quyền</option><option value='FREE'>FREE</option><option value='VIP'>VIP</option><option value='SVIP'>⭐ SVIP</option></select><select name='class' form='bulkForm'><option value=''>Giữ lớp</option><option value='10'>Lớp 10</option><option value='11'>Lớp 11</option><option value='12'>Lớp 12</option></select><select name='status' form='bulkForm'><option value=''>Giữ trạng thái</option><option value='ON'>Mở</option><option value='OFF'>Khóa</option></select><button class='btn green' form='bulkForm' type='submit'>💾 Áp dụng</button><span class='muted'>Chọn ☐ bên trái từng học viên.</span></div>
      <div class='membertable'><table class='selectgrid'><tr><th>☑</th><th>HỌC VIÊN</th><th>ĐIỆN THOẠI</th><th>LỚP</th><th>QUYỀN</th><th>TRẠNG THÁI</th><th>ĐỔI PASS</th><th>CẬP NHẬT</th></tr>{''.join(rows)}{empty}</table></div>
    </div>
    """
    return body


@app.get('/admin/members')
def _admin_members_route():
    if not _admin_guard():
        return redirect('/admin/login')
    return page('ADMIN · Thành viên', _admin_members_html())


@app.post('/admin/members/save')
def _admin_members_save():
    if not _admin_guard():
        return redirect('/admin/login')
    username = (request.form.get('save_user') or '').strip()
    if not username:
        return redirect('/admin/members')
    data = members_data()
    target = next((m for m in data.get('members', []) if str(m.get('username', '')).strip() == username), None)
    if not target:
        return page('ADMIN', "<div class='wrap'><div class='panel'><div class='body err'>Không tìm thấy tài khoản.</div></div></div>")
    target['account_type'] = _norm_type(request.form.get('account_type') or target.get('account_type'))
    target['status'] = (request.form.get('status') or target.get('status') or 'ON').upper()
    if target['status'] not in {'ON', 'OFF'}:
        target['status'] = 'ON'
    grade = _norm_class(request.form.get(f'class_{username}'))
    target['class'] = grade
    target['grade'] = grade
    new_password = request.form.get('new_password') or ''
    if new_password:
        target['password_sha256'] = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
    target['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    try:
        _save_members(data)
        return redirect('/admin/members')
    except Exception as e:
        return page('ADMIN lỗi', f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>"), 500


@app.post('/admin/members/bulk')
def _admin_members_bulk():
    if not _admin_guard():
        return redirect('/admin/login')
    selected = [str(x).strip() for x in request.form.getlist('selected') if str(x).strip()]
    if not selected:
        return redirect('/admin/members')
    new_type = request.form.get('account_type') or ''
    new_class = request.form.get('class') or ''
    new_status = request.form.get('status') or ''
    data = members_data(); selected_set = set(selected); now = time.strftime('%Y-%m-%d %H:%M:%S')
    changed = 0
    for m in data.get('members', []):
        if str(m.get('username', '')).strip() not in selected_set:
            continue
        if new_type:
            m['account_type'] = _norm_type(new_type)
        if new_class:
            g = _norm_class(new_class); m['class'] = g; m['grade'] = g
        if new_status in {'ON', 'OFF'}:
            m['status'] = new_status
        m['updated_at'] = now
        changed += 1
    try:
        _save_members(data)
        return redirect('/admin/members')
    except Exception as e:
        return page('ADMIN lỗi', f"<div class='wrap'><div class='panel'><div class='body err'>Cập nhật {changed} tài khoản nhưng đồng bộ GitHub thất bại: {html.escape(str(e))}</div></div></div>"), 500


def admin_results():
    if not _admin_guard():
        return redirect('/admin/login')
    rows = list(reversed(_load_results()))
    filt = (request.args.get('username') or '').strip()
    if filt:
        rows = [r for r in rows if str(r.get('username', '')) == filt]
    body_rows = []
    for r in rows[:500]:
        ok = bool(r.get('ok'))
        status = '✅ ĐÚNG' if ok else '❌ SAI'
        body_rows.append(
            "<tr>"
            f"<td>{html.escape(str(r.get('time', '')))}</td>"
            f"<td><b>{html.escape(str(r.get('username', '')))}</b></td>"
            f"<td>{html.escape(str(r.get('name', '')))}</td>"
            f"<td>{html.escape(str(r.get('kind', '')))}</td>"
            f"<td>{html.escape(str(r.get('dang', '')))}</td>"
            f"<td class='{'good' if ok else 'bad'}'>{status}</td>"
            f"<td>{html.escape(str(r.get('student', '')))}</td>"
            f"<td><details><summary>Xem câu</summary>{html.escape(str(r.get('text', '')))}<hr><b>Lời giải:</b><br>{html.escape(str(r.get('solution', '')))}</details></td>"
            "</tr>"
        )
    users = sorted({str(r.get('username', '')) for r in _load_results() if r.get('username')})
    opts = "<option value=''>Tất cả học viên</option>" + ''.join(f"<option value='{html.escape(u, quote=True)}' {'selected' if u == filt else ''}>{html.escape(u)}</option>" for u in users)
    body = (
        "<div class='wrap'><div class='panel'><div class='head'>📊 ADMIN · Xem bài làm học viên</div><div class='body'>"
        "<form method='get' style='display:flex;gap:8px;flex-wrap:wrap'>"
        f"<select name='username'>{opts}</select><button class='btn'>Lọc</button></form>"
        "<div class='notice' style='margin-top:10px'>Kết quả luyện tập hiện lưu trong tệp runtime của Render; dữ liệu có thể mất khi service khởi động/deploy lại.</div>"
        "<div style='overflow:auto;margin-top:10px'><table class='selectgrid'><tr><th>Thời gian</th><th>Tài khoản</th><th>Họ tên</th><th>Loại</th><th>Dạng</th><th>Kết quả</th><th>HS trả lời</th><th>Câu / lời giải</th></tr>"
        + ''.join(body_rows) + "</table></div>"
        "<p><a class='btn' href='/admin'>← ADMIN</a> <a class='btn' href='/admin/members'>👥 Thành viên</a></p>"
        "</div></div></div>"
    )
    return page('Bài làm học viên', body)


@app.get('/admin/results')
def _admin_results_route():
    return admin_results()


# Ghi nhận kết quả trả lời của học viên cho khu vực ADMIN.
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
                    'username': session.get('username', ''),
                    'name': m.get('name', ''),
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


# ===== PHÂN QUYỀN HỌC VIÊN: lớp được cấp hoặc SVIP toàn bộ =====
# server_clean.py nạp module này sau các route chính, vì vậy có thể thay
# chính sách quyền tại một chỗ mà không phải sửa hàng loạt route cũ.
try:
    import app as _base_app
except Exception:
    _base_app = None


def _strict_member_access(m, path):
    if not m or not path or not str(path).startswith('ngan-hang/'):
        return False
    typ = _norm_type(m.get('account_type'))
    if typ == 'SVIP' or str(m.get('role', '')).lower() == 'admin':
        return True
    if typ not in {'FREE', 'VIP'}:
        return False
    wanted = _member_class(m)
    if not wanted:
        return False
    # Chỉ cho phép đúng khối lớp của tài khoản; bài VIP/FREE vẫn giữ chính sách
    # phí cũ ở can_access của app, nhưng không được vượt qua khối lớp.
    return f'/Lớp {wanted}/' in ('/' + str(path)) or f'/Lop {wanted}/' in ('/' + str(path))


if _base_app is not None:
    _base_app.can_access = _strict_member_access
    # dang_routes đã import can_access bằng tên cục bộ; cập nhật cả tên đó.
    try:
        import dang_routes as _dang_routes
        _dang_routes.can_access = _strict_member_access
    except Exception:
        pass


def _strict_member_index():
    """Mục lục chỉ dựng các bài đúng khối lớp; SVIP thấy tất cả."""
    m = member_current()
    if not m:
        return redirect('/member/login')
    idx = _base_app.index_data() if _base_app is not None else {'lessons': []}
    typ = _norm_type(m.get('account_type'))
    allowed_grade = _member_class(m)
    svip = typ == 'SVIP'
    q = (request.args.get('q') or '').strip().lower()
    sm = (request.args.get('mon') or '').strip()
    cl = (request.args.get('lop') or '').strip()
    items = [x for x in idx.get('lessons', []) if isinstance(x, dict) and str(x.get('path', '')).startswith('ngan-hang/')]
    if not svip:
        items = [x for x in items if _member_class({'class': str(x.get('Lop', ''))}) == allowed_grade]
    if q:
        items = [x for x in items if q in ' '.join(str(x.get(k, '')) for k in ('Mon','Lop','Chuong','BaiHoc','De','path')).lower()]
    if sm:
        items = [x for x in items if str(x.get('Mon','')) == sm]
    if cl:
        items = [x for x in items if str(x.get('Lop','')) == cl]

    groups = {}
    for x in items:
        key = (str(x.get('Mon','')), str(x.get('Lop','')), str(x.get('Chuong','')))
        groups.setdefault(key, []).append(x)
    sections = []
    for (mon, lop, chuong), arr in sorted(groups.items()):
        cards = []
        for x in sorted(arr, key=lambda z: str(z.get('BaiHoc') or z.get('De') or '')):
            path = str(x.get('path')); title = str(x.get('BaiHoc') or x.get('De') or Path(path).parent.name)
            lvl = str(_base_app.lesson_level(path) if _base_app else 'FREE').upper()
            cnt = int(x.get('questions') or x.get('count') or 0)
            dangs = x.get('dang') or {}
            dh = ''.join("<div class='dangrow'><span>" + html.escape(str(k)) + "</span><span class='tag'>" + str(int(v)) + " câu</span></div>" for k,v in dangs.items())
            lc = 'vip' if lvl == 'VIP' else 'free'; href = urllib.parse.quote(path, safe='')
            cards.append("<div class='card'><b>" + html.escape(title) + "</b><div class='meta'>" + html.escape(mon) + " · Lớp " + html.escape(lop) + " · " + html.escape(chuong) + "</div><div><span class='tag " + lc + "'>" + html.escape(lvl) + "</span><span class='tag'>" + str(cnt) + " câu</span></div><div class='dang'><b>📌 Dạng bài</b>" + (dh or "<div class='muted'>Xem trực tiếp từ TEX khi mở bài</div>") + "</div><a class='btn primary' href='/member/select?path=" + href + "'>Mở bài</a></div>")
        sections.append("<section style='margin-top:10px'><div class='titlebar'>" + html.escape(mon) + " · Lớp " + html.escape(lop) + " · " + html.escape(chuong) + "</div><div class='cards' style='margin-top:8px'>" + ''.join(cards) + "</div></section>")

    subjects = sorted({str(x.get('Mon','')) for x in items if x.get('Mon')})
    classes = sorted({str(x.get('Lop','')) for x in items if x.get('Lop')})
    subjopts = ''.join("<option value='" + html.escape(s, quote=True) + "'" + (" selected" if sm == s else "") + ">" + html.escape(s) + "</option>" for s in subjects)
    classopts = ''.join("<option value='" + html.escape(c, quote=True) + "'" + (" selected" if cl == c else "") + ">" + html.escape(c) + "</option>" for c in classes)
    display_class = 'Tất cả khối lớp' if svip else ('Lớp ' + allowed_grade if allowed_grade else 'Chưa được cấp lớp')
    body = "<div class='wrap'><div class='panel'><div class='head'>📚 MỤC LỤC <span class='tag'>" + str(idx.get('total_files',0)) + " file</span><span class='tag'>" + str(idx.get('total_questions',0)) + " câu</span></div><div class='body'><div class='notice'>👤 <b>" + html.escape(str(m.get('name') or m.get('username'))) + "</b> · Tài khoản <b>" + html.escape(str(m.get('username'))) + "</b> · 🎓 <b>" + html.escape(display_class) + "</b> · Quyền <b>" + html.escape(typ) + "</b></div><form method='get' style='display:grid;grid-template-columns:1fr 180px 160px auto;gap:7px;margin-top:10px'><input name='q' placeholder='Tìm bài, chương, dạng...' value='" + html.escape(q) + "'><select name='mon'><option value=''>Tất cả môn</option>" + subjopts + "</select><select name='lop'><option value=''>Tất cả lớp</option>" + classopts + "</select><button class='btn'>Tìm</button></form></div></div>" + (''.join(sections) or "<div class='panel' style='margin-top:10px'><div class='body muted'>Không có bài phù hợp với quyền/lớp hiện tại.</div></div>") + "</div>"
    return page('Mục lục', body)


# Thay route cũ bằng mục lục có lọc khối lớp.
if 'member_index' in app.view_functions:
    app.view_functions['member_index'] = _strict_member_index
