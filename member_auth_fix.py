# -*- coding: utf-8 -*-
"""Stable member authentication: FREE registration + login from members.json."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import urllib.parse

from flask import request, redirect, session
from app import app, members_data, page, gh_api, BRANCH


def _save_members(data, message='Update members.json'):
    d = gh_api(f'contents/members.json?ref={urllib.parse.quote(BRANCH)}')
    sha = d.get('sha','')
    payload = {
        'message': message,
        'content': base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')).decode('ascii'),
        'branch': BRANCH,
        'sha': sha,
    }
    gh_api('contents/members.json', 'PUT', payload)


def member_login_fixed():
    msg = ''
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        wanted = hashlib.sha256(password.encode('utf-8')).hexdigest()
        member = next((m for m in members_data().get('members', []) if str(m.get('username','')).strip().lower() == username.lower()), None)
        if member and str(member.get('password_sha256','')) == wanted and str(member.get('status','ON')).upper() == 'ON':
            session.clear(); session.update(role='member', username=str(member.get('username')), name=member.get('name') or username, account_type=str(member.get('account_type') or 'FREE').upper())
            return redirect('/member')
        msg = 'Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa.'
    err_html = (f"<div class='mt-3 text-sm text-red-600 font-semibold text-center'>{html.escape(msg)}</div>" if msg else '')
    body = (
        "<div class='flex justify-center'>"
        "<div class='w-full max-w-sm'>"
        "<div class='bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden mt-6'>"
        "<div class='bg-gradient-to-r from-blue-700 to-blue-500 px-6 py-5 text-center'>"
        "<div class='text-4xl mb-2'>👤</div>"
        "<h2 class='text-white font-black text-xl'>Đăng nhập</h2>"
        "<p class='text-blue-200 text-sm mt-1'>Học viên / Thành viên</p>"
        "</div>"
        "<div class='p-6'>"
        "<div class='mb-3 p-3 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-700'>"
        "🎓 <b>FREE</b>: xem bài FREE · <b>VIP</b>: dùng cả FREE + VIP"
        "</div>"
        "<form method='post'>"
        "<div class='mb-4'><label class='block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide'>Tài khoản</label>"
        "<input name='username' autocomplete='username' required"
        " class='w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm"
        " focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50'></div>"
        "<div class='mb-5'><label class='block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide'>Mật khẩu</label>"
        "<input name='password' type='password' autocomplete='current-password' required"
        " class='w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm"
        " focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50'></div>"
        "<button type='submit' class='w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition text-sm'>"
        "🔐 Đăng nhập</button>"
        "<div class='mt-3 text-center'>"
        "<a href='/member/register' class='text-sm text-blue-600 hover:underline font-semibold'>📝 Chưa có tài khoản? Đăng ký FREE</a>"
        "</div>"
        + err_html +
        "</form>"
        "</div></div></div></div>"
    )
    return page('Đăng nhập học viên', body)


def member_register_fixed():
    msg=''
    if request.method == 'POST':
        name=(request.form.get('name') or '').strip(); username=(request.form.get('username') or '').strip(); password=request.form.get('password') or ''
        if len(username)<3 or len(password)<4: msg='Tài khoản tối thiểu 3 ký tự, mật khẩu tối thiểu 4 ký tự.'
        else:
            data=members_data(); members=data.setdefault('members',[])
            if any(str(m.get('username','')).strip().lower()==username.lower() for m in members): msg='Tài khoản đã tồn tại.'
            else:
                members.append({'username':username,'name':name or username,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(password.encode('utf-8')).hexdigest()})
                try:
                    _save_members(data, f'Tạo tài khoản FREE: {username}')
                    session.clear(); session.update(role='member',username=username,name=name or username,account_type='FREE')
                    return redirect('/member')
                except Exception as e: msg='Không lưu được tài khoản lên GitHub: '+str(e)
    err_html = (f"<div class='mt-3 text-sm text-red-600 font-semibold text-center'>{html.escape(msg)}</div>" if msg else '')
    body = (
        "<div class='flex justify-center'>"
        "<div class='w-full max-w-sm'>"
        "<div class='bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden mt-6'>"
        "<div class='bg-gradient-to-r from-green-600 to-teal-500 px-6 py-5 text-center'>"
        "<div class='text-4xl mb-2'>📝</div>"
        "<h2 class='text-white font-black text-xl'>Đăng ký</h2>"
        "<p class='text-green-100 text-sm mt-1'>Tạo tài khoản FREE miễn phí</p>"
        "</div>"
        "<div class='p-6'>"
        "<div class='mb-3 p-3 bg-green-50 border border-green-100 rounded-xl text-xs text-green-700'>"
        "✅ Tài khoản mới mặc định là <b>FREE</b>. ADMIN có thể nâng lên <b>VIP</b>."
        "</div>"
        "<form method='post'>"
        "<div class='mb-4'><label class='block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide'>Họ tên</label>"
        "<input name='name' placeholder='Nguyễn Văn A'"
        " class='w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm"
        " focus:outline-none focus:ring-2 focus:ring-green-500 bg-gray-50'></div>"
        "<div class='mb-4'><label class='block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide'>Tài khoản</label>"
        "<input name='username' required placeholder='vd: minhhoc123'"
        " class='w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm"
        " focus:outline-none focus:ring-2 focus:ring-green-500 bg-gray-50'></div>"
        "<div class='mb-5'><label class='block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide'>Mật khẩu</label>"
        "<input name='password' type='password' required"
        " class='w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm"
        " focus:outline-none focus:ring-2 focus:ring-green-500 bg-gray-50'></div>"
        "<button class='w-full py-2.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-xl transition text-sm'>"
        "✅ Tạo tài khoản FREE</button>"
        "<div class='mt-3 text-center'>"
        "<a href='/member/login' class='text-sm text-blue-600 hover:underline font-semibold'>← Đã có tài khoản? Đăng nhập</a>"
        "</div>"
        + err_html +
        "</form>"
        "</div></div></div></div>"
    )
    return page('Đăng ký FREE', body)

# Override or create the endpoints.
if 'member_login' in app.view_functions:
    app.view_functions['member_login'] = member_login_fixed
else:
    app.add_url_rule('/member/login', endpoint='member_login', view_func=member_login_fixed, methods=['GET','POST'])
if 'member_register' in app.view_functions:
    app.view_functions['member_register'] = member_register_fixed
else:
    app.add_url_rule('/member/register', endpoint='member_register', view_func=member_register_fixed, methods=['GET','POST'])
