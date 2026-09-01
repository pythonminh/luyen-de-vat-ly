# -*- coding: utf-8 -*-
"""Small authentication/UI overrides for the stable portal."""
from __future__ import annotations

import hashlib
import html
import os

from flask import redirect, request, session


def install(app, portal):
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "ADMIN").strip() or "ADMIN"
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

    def admin_login():
        msg = ""
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            if username == ADMIN_USERNAME and ADMIN_PASSWORD and password == ADMIN_PASSWORD:
                session.clear()
                session.update(role="admin", username=ADMIN_USERNAME, name="ADMIN")
                return redirect("/admin")
            msg = "Sai tài khoản hoặc mật khẩu ADMIN."
        err_html = (f"<div class='mt-3 text-sm text-red-600 font-semibold text-center'>{html.escape(msg)}</div>" if msg else '')
        body = (
            "<div class='flex justify-center'>"
            "<div class='w-full max-w-xs'>"
            "<div class='bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden mt-6'>"
            "<div class='bg-gradient-to-r from-gray-800 to-gray-600 px-6 py-5 text-center'>"
            "<div class='text-4xl mb-2'>🔐</div>"
            "<h2 class='text-white font-black text-xl'>ADMIN</h2>"
            "<p class='text-gray-400 text-sm mt-1'>Quản trị viên</p>"
            "</div>"
            "<div class='p-6'>"
            "<form method='post'>"
            "<div class='mb-4'><label class='block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide'>Tài khoản</label>"
            f"<input name='username' value='{html.escape(ADMIN_USERNAME, quote=True)}' required"
            " class='w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm"
            " focus:outline-none focus:ring-2 focus:ring-gray-500 bg-gray-50'></div>"
            "<div class='mb-5'><label class='block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide'>Mật khẩu</label>"
            "<input name='password' type='password' required autocomplete='current-password'"
            " class='w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm"
            " focus:outline-none focus:ring-2 focus:ring-gray-500 bg-gray-50'></div>"
            "<button class='w-full py-2.5 bg-gray-800 hover:bg-gray-900 text-white font-bold rounded-xl transition text-sm'>"
            "Đăng nhập ADMIN</button>"
            + err_html +
            "</form>"
            "</div></div></div></div>"
        )
        return portal.page("Đăng nhập ADMIN", body)

    def member_login():
        msg = ""
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            wanted = hashlib.sha256(password.encode()).hexdigest()
            member = None
            for m in portal.load_members().get("members", []):
                if m.get("username") == username:
                    member = m
                    break
            if member and member.get("password_sha256") == wanted and member.get("status", "ON") == "ON":
                session.clear()
                session.update(
                    role="member",
                    username=username,
                    name=member.get("name") or username,
                    account_type=portal.account_type(member),
                )
                return redirect("/member")
            msg = "Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa."
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
            "<input name='username' required autocomplete='username'"
            " class='w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm"
            " focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50'></div>"
            "<div class='mb-5'><label class='block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide'>Mật khẩu</label>"
            "<input name='password' type='password' required autocomplete='current-password'"
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
        return portal.page("Đăng nhập thành viên", body)

    def member_home():
        if session.get("role") != "member":
            return redirect("/member/login")
        member = portal.current_member()
        if not member:
            session.clear()
            return redirect("/member/login")
        data = portal.index_data()
        vip = portal.is_vip(member)
        account = portal.account_type(member)
        allowed_text = "FREE + VIP" if vip else "FREE"
        summary = (
            "<div class='hero'><h2>Thông tin đăng nhập</h2>"
            "<div class='section'><b>Tài khoản:</b> " + html.escape(str(member.get("username") or ""))
            + "<br><b>Họ tên:</b> " + html.escape(str(member.get("name") or ""))
            + "<br><b>Loại tài khoản:</b> <span class='tag " + ("vip" if vip else "free") + "'>"
            + html.escape(account) + "</span>"
            + "<br><b>Được sử dụng:</b> " + allowed_text
            + "<br><b>Chức năng:</b> Xem bài · Làm bài · Chấm điểm"
            + "</div></div>"
        )
        cards = []
        acc = portal.load_access()
        for item in data.get("lessons", []):
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "")
            if not path.startswith("ngan-hang/"):
                continue
            title = str(item.get("BaiHoc") or item.get("De") or path.rsplit("/", 1)[-1])
            count = int(item.get("questions") or item.get("count") or 0)
            level = str(acc.get("lessons", {}).get(path, acc.get("default", "FREE"))).upper()
            allowed = level == "FREE" or vip
            badge = "VIP" if level == "VIP" else "FREE"
            action = (
                f"<a class='btn' href='/member/lesson?path={portal.urllib.parse.quote(path, safe='')}'>Làm bài</a>"
                if allowed else "<span class='tag vip'>🔒 Chỉ VIP</span>"
            )
            cards.append(
                "<div class='card'><b>" + html.escape(title) + "</b>"
                + "<div class='small'>" + html.escape(str(item.get('Mon') or '')) + " · " + html.escape(str(item.get('Lop') or '')) + "</div>"
                + f"<span class='tag {'vip' if level == 'VIP' else 'free'}'>{badge}</span><span class='tag'>{count} câu</span><div>" + action + "</div></div>"
            )
        body = (
            "<div class='wrap'><div class='panel'><div class='mh'><span>👤 Khu vực thành viên</span>"
            + "<a class='btn' href='/member/logout'>Đăng xuất</a></div>"
            + summary
            + "<div class='hero'><h2>Ngân hàng bài tập</h2>"
            + str(int(data.get('total_files') or 0)) + " bài · " + str(int(data.get('total_questions') or 0)) + " câu</div>"
            + "<div class='cards'>" + "".join(cards) + "</div></div></div>"
        )
        return portal.page("Trang thành viên", body)

    # Replace existing endpoints while keeping their original URL rules.
    app.view_functions["admin_login"] = admin_login
    app.view_functions["member_login"] = member_login
    app.view_functions["member_home"] = member_home

    return ADMIN_USERNAME
