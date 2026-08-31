# -*- coding: utf-8 -*-
"""Stable member authentication: FREE registration + login from members.json."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import urllib.parse

from flask import request, redirect, session
from app import app, members_data, page, gh_api, BRANCH, MEMBERS_FILE


def _save_members(data, message='Update members.json'):
    if not hasattr(app, '_member_sha'):
        try:
            d = gh_api(f'contents/{urllib.parse.quote("members.json", safe="/")}?ref={urllib.parse.quote(BRANCH)}')
            app._member_sha = d.get('sha', '')
        except Exception:
            app._member_sha = ''
    payload = {
        'message': message,
        'content': base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')).decode('ascii'),
        'branch': BRANCH,
    }
    if app._member_sha:
        payload['sha'] = app._member_sha
    d = gh_api(f'contents/members.json?ref={urllib.parse.quote(BRANCH)}', 'PUT', payload)
    app._member_sha = d.get('content', {}).get('sha') or app._member_sha


def member_login_fixed():
    msg = ''
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        wanted = hashlib.sha256(password.encode('utf-8')).hexdigest()
        member = next((m for m in members_data().get('members', []) if str(m.get('username','')).strip() == username), None)
        if member and str(member.get('password_sha256','')) == wanted and str(member.get('status','ON')).upper() == 'ON':
            session.clear()
            session.update(role='member', username=username, name=member.get('name') or username, account_type=str(member.get('account_type') or 'FREE').upper())
            return redirect('/member')
        msg = 'Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa.'
    body = """
<div class='wrap'><div class='panel login' style='max-width:480px;margin:40px auto'>
<div class='head'>👤 Đăng nhập học viên</div><div class='body'>
<div class='notice' style='margin-bottom:10px'>Học viên thường dùng <b>tài khoản FREE</b> để xem và làm bài FREE. Học viên VIP dùng được cả FREE + VIP.</div>
<form method='post'>
<div class='field'><label>Tài khoản</label><input name='username' autocomplete='username' required></div>
<div class='field'><label>Mật khẩu</label><input name='password' type='password' autocomplete='current-password' required></div>
<button class='btn primary' type='submit'>🔐 Đăng nhập</button>
<a class='btn' href='/member/register'>📝 Tạo tài khoản FREE</a>
""" + (f"<div class='err' style='margin-top:8px'>{html.escape(msg)}</div>" if msg else '') + "</form></div></div></div>"
    return page('Đăng nhập học viên', body)


def member_register_fixed():
    msg=''
    if request.method == 'POST':
        name=(request.form.get('name') or '').strip()
        username=(request.form.get('username') or '').strip()
        password=request.form.get('password') or ''
        if len(username)<3 or len(password)<4:
            msg='Tài khoản tối thiểu 3 ký tự, mật khẩu tối thiểu 4 ký tự.'
        else:
            data=members_data(); members=data.setdefault('members',[])
            if any(str(m.get('username','')).strip().lower()==username.lower() for m in members):
                msg='Tài khoản đã tồn tại.'
            else:
                members.append({'username':username,'name':name or username,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(password.encode('utf-8')).hexdigest()})
                try:
                    _save_members(data, f'Tạo tài khoản FREE: {username}')
                    session.clear(); session.update(role='member',username=username,name=name or username,account_type='FREE')
                    return redirect('/member')
                except Exception as e:
                    msg='Không lưu được tài khoản lên GitHub: ' + str(e)
    body = """
<div class='wrap'><div class='panel login' style='max-width:480px;margin:40px auto'>
<div class='head'>📝 Đăng ký thành viên FREE</div><div class='body'>
<div class='notice' style='margin-bottom:10px'>Tài khoản mới mặc định là <b>FREE</b>. ADMIN có thể nâng thành VIP sau.</div>
<form method='post'>
<div class='field'><label>Họ tên</label><input name='name'></div>
<div class='field'><label>Tài khoản</label><input name='username' required></div>
<div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div>
<button class='btn primary'>✅ Tạo tài khoản</button> <a class='btn' href='/member/login'>← Đăng nhập</a>
""" + (f"<div class='err' style='margin-top:8px'>{html.escape(msg)}</div>" if msg else '') + "</form></div></div></div>"
    return page('Đăng ký FREE', body)

# Override existing endpoint functions by endpoint name.
if 'member_login' in app.view_functions:
    app.view_functions['member_login'] = member_login_fixed
if 'member_register' in app.view_functions:
    app.view_functions['member_register'] = member_register_fixed
else:
    app.add_url_rule('/member/register', endpoint='member_register', view_func=member_register_fixed, methods=['GET','POST'])
