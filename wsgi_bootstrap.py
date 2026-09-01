# -*- coding: utf-8 -*-
"""Single Render bootstrap: one authoritative header/auth visibility layer."""
import re
import wsgi
import member_auth_fix
import student_gemini
import admin_manager
import ui_sync
from flask import session

app = wsgi.app
_original_wsgi = app.wsgi_app


def _member_display_name():
    try:
        m = wsgi.member_current()
        if m:
            return str(m.get('name') or m.get('username') or 'Học viên')
    except Exception:
        pass
    return str(session.get('name') or session.get('username') or 'Học viên')


def _final_nav(admin=False, member=False):
    links = ["<a href='/member'>📚 Mục lục</a>"]
    if admin:
        links += [
            "<a href='/admin'>🔐 ADMIN</a>",
            "<a href='https://github.com/pythonminh/luyen-de-vat-ly' target='_blank' rel='noopener'>🐙 GitHub</a>",
            "<a href='/admin/logout'>🚪 Thoát</a>",
        ]
    elif member:
        name = html_escape(_member_display_name())
        links += [
            f"<span class='user-pill'>👤 {name}</span>",
            "<a href='/member/logout'>🚪 Thoát</a>",
        ]
    else:
        links += [
            "<a href='/member/login'>🔑 Đăng nhập</a>",
            "<a href='/member/register'>📝 Đăng ký</a>",
            "<a href='/admin/login'>🔐 ADMIN</a>",
        ]
    return "<div class='nav'>" + ''.join(links) + "</div>"


def html_escape(value):
    return re.sub(r'[<>"&]', '', str(value))


def _filter_final_response(environ, start_response):
    captured = {}

    def capture_start(status, headers, exc_info=None):
        captured['status'] = status
        captured['headers'] = list(headers)
        captured['exc_info'] = exc_info
        return lambda data: None

    iterable = _original_wsgi(environ, capture_start)
    try:
        body = b''.join(iterable)
    finally:
        if hasattr(iterable, 'close'):
            iterable.close()

    headers = captured.get('headers', [])
    ctype = next((v for k, v in headers if k.lower() == 'content-type'), '')
    if 'text/html' in ctype:
        text = body.decode('utf-8', 'replace')
        path = environ.get('PATH_INFO', '') or '/'
        admin = session.get('role') == 'admin'
        member = session.get('role') == 'member'

        # ONE BRAND for every HTML page, including admin/login and GitHub portal.
        old_brands = [
            '📚 Ngân hàng câu hỏi GitHub',
            'Ngân hàng câu hỏi GitHub',
            '📚 Ngân hàng GitHub',
            'Ngân hàng GitHub',
            '📚 Luyện đề AI · Thầy Minh',
            'Luyện đề AI · Thầy Minh',
        ]
        for old in old_brands:
            text = text.replace(old, '📚 Luyện Đề Toán Lý')

        # Replace all legacy source/subtitle strings with the single public brand contact.
        text = re.sub(
            r'Nguồn đề:\s*bank_index\.json\s*\+\s*ngan-hang/(?:\\\*)?\.tex\s*(?:·|•|\|)\s*Google Sheet không dùng cho đề',
            'Zalo thầy Minh 0946111107', text, flags=re.I
        )
        text = re.sub(
            r'Nguồn:\s*bank_index\.json\s*\+\s*ngan-hang/(?:\\\*)?\.tex(?:\s*·[^<]*)?',
            'Zalo thầy Minh 0946111107', text, flags=re.I
        )
        text = text.replace('MỤC LỤC · GitHub', 'MỤC LỤC')
        text = text.replace('MỤC LỤC • GitHub', 'MỤC LỤC')
        text = text.replace('MỤC LỤC | GitHub', 'MỤC LỤC')

        # Replace the first/primary navigation with one authoritative navigation.
        text = re.sub(
            r"<div\s+class=['\"]nav['\"]>.*?</div>",
            _final_nav(admin, member), text, count=1, flags=re.I | re.S
        )

        # GitHub is never exposed to guests or students. Only an authenticated ADMIN sees it.
        if not admin:
            text = re.sub(
                r'<a\b[^>]*href=["\'][^"\']*github\.com[^"\']*["\'][^>]*>.*?</a>',
                '', text, flags=re.I | re.S
            )
            text = re.sub(
                r'<a\b[^>]*href=["\']/github(?:/[^"\']*)?["\'][^>]*>.*?</a>',
                '', text, flags=re.I | re.S
            )
            text = re.sub(r'<a\b[^>]*>\s*(?:🐙\s*)?GitHub\s*</a>', '', text, flags=re.I | re.S)
            text = re.sub(r'<button\b[^>]*>\s*(?:🐙\s*)?GitHub\s*</button>', '', text, flags=re.I | re.S)

        # Student-facing pages: hide implementation markers, never hide actual formulas.
        if path.startswith('/member') or path == '/':
            text = re.sub(r'\\begin\s*\{ex\}', '', text, flags=re.I)
            text = re.sub(r'\\end\s*\{ex\}', '', text, flags=re.I)
            text = re.sub(r'%\s*ID\s*:\s*[^%<\r\n]+', '', text, flags=re.I)
            text = re.sub(r'%\s*Mức\s*:\s*[^%<\r\n]+', '', text, flags=re.I)
            text = text.replace(' · GitHub', '').replace(' • GitHub', '')

        responsive = """
<style>
.user-pill{display:inline-flex;align-items:center;color:#fff;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.10);padding:7px 10px;border-radius:8px;font-weight:800;white-space:nowrap}
.brand{font-weight:900;font-size:20px}.sub{font-size:11px}
@media(max-width:900px){.topin{padding:8px 10px;align-items:flex-start}.brand{font-size:18px;line-height:1.2;white-space:normal}.sub{font-size:10px}.nav{gap:4px}.nav a,.user-pill{padding:6px 8px;font-size:12px}}
@media(max-width:560px){.topin{display:flex;flex-direction:column;gap:6px}.nav{width:100%;margin-left:0;display:flex}.nav a,.user-pill{font-size:11px;padding:5px 7px}.brand{font-size:16px}}
</style>
"""
        text = text.replace('</head>', responsive + '</head>', 1)
        text = text.replace(
            '</body>',
            "<script>window.addEventListener('load',function(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise().catch(function(){});});</script></body>",
            1
        )

        body = text.encode('utf-8')
        headers = [(k, v) for k, v in headers if k.lower() not in ('content-length', 'etag', 'cache-control')]
        headers.append(('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'))
        headers.append(('Pragma', 'no-cache'))
        headers.append(('Content-Length', str(len(body))))

    start_response(captured.get('status', '200 OK'), headers, captured.get('exc_info'))
    return [body]


app.wsgi_app = _filter_final_response
