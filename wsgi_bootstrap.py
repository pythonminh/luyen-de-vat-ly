# -*- coding: utf-8 -*-
"""Single Render bootstrap: final synchronized UI/auth visibility guard."""
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
    return str(session.get('username') or 'Học viên')


def _final_nav(admin=False, member=False):
    links = ["<a href='/member'>📚 Mục lục</a>"]
    if admin:
        links += [
            "<a href='/admin'>🔐 ADMIN</a>",
            "<a href='https://github.com/pythonminh/luyen-de-vat-ly' target='_blank' rel='noopener'>🐙 GitHub</a>",
            "<a href='/admin/logout'>🚪 Thoát</a>",
        ]
    elif member:
        name = re.sub(r'[<>"&]', '', _member_display_name())
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

        # FINAL BRANDING: always use the teacher's public-facing name.
        text = text.replace('📚 Ngân hàng câu hỏi GitHub', '📚 Luyện Đề Toán Lý')
        text = text.replace('Ngân hàng câu hỏi GitHub', 'Luyện Đề Toán Lý')
        text = re.sub(
            r'Nguồn đề:\s*bank_index\.json\s*\+\s*ngan-hang/\\*\.tex\s*·\s*Google Sheet không dùng cho đề',
            'Zalo thầy Minh 0946111107', text, flags=re.I
        )
        text = text.replace('MỤC LỤC · GitHub', 'MỤC LỤC')
        text = text.replace('MỤC LỤC • GitHub', 'MỤC LỤC')

        # Replace every old navigation bar with ONE authoritative navigation bar.
        text = re.sub(r"<div class=['\"]nav['\"]>.*?</div>", _final_nav(admin, member), text, count=1, flags=re.I | re.S)

        # A second safety pass: GitHub is never visible unless a real ADMIN session exists.
        if not admin:
            text = re.sub(
                r'<a\b[^>]*(?:href=["\'][^"\']*github\.com[^"\']*["\']|href=["\']/github(?:/|["\']))[^>]*>.*?</a>',
                '', text, flags=re.I | re.S
            )
            text = re.sub(r'<a\b[^>]*>\s*(?:🐙\s*)?GitHub\s*</a>', '', text, flags=re.I | re.S)
            text = re.sub(r'<button\b[^>]*>\s*(?:🐙\s*)?GitHub\s*</button>', '', text, flags=re.I | re.S)

        # Student pages must not expose internal LaTeX environment markers or IDs.
        if path.startswith('/member') or path == '/':
            text = re.sub(r'\\begin\s*\{ex\}', '', text, flags=re.I)
            text = re.sub(r'\\end\s*\{ex\}', '', text, flags=re.I)
            text = re.sub(r'%\s*ID\s*:\s*[^%<\r\n]+', '', text, flags=re.I)
            text = re.sub(r'%\s*Mức\s*:\s*[^%<\r\n]+', '', text, flags=re.I)
            text = text.replace('MỤC LỤC · GitHub', 'MỤC LỤC')
            text = text.replace('MỤC LỤC • GitHub', 'MỤC LỤC')
            text = text.replace(' · GitHub', '')
            text = text.replace(' • GitHub', '')

        # Responsive final styling for laptop/tablet/phone.
        responsive = """
<style>
.user-pill{display:inline-flex;align-items:center;color:#fff;border:1px solid #ffffff55;background:#ffffff15;padding:7px 10px;border-radius:8px;font-weight:800;white-space:nowrap}
.zalo-brand{font-size:12px;font-weight:700;margin-left:10px;opacity:.95}
@media(max-width:900px){.topin{padding:8px 10px;align-items:flex-start}.brand{font-size:18px;line-height:1.2;white-space:normal}.sub{font-size:10px}.nav{gap:4px}.nav a,.user-pill{padding:6px 8px;font-size:12px}}
@media(max-width:560px){.topin{display:flex;flex-direction:column;gap:6px}.nav{width:100%;margin-left:0;display:flex}.nav a,.user-pill{font-size:11px;padding:5px 7px}.brand{font-size:16px}}
</style>
"""
        text = text.replace('</head>', responsive + '</head>', 1)

        # MathJax refresh after final HTML filtering.
        text = text.replace(
            '</body>',
            "<script>window.addEventListener('load',function(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise().catch(function(){});});</script></body>",
            1
        )

        body = text.encode('utf-8')
        headers = [(k, v) for k, v in headers if k.lower() != 'content-length']
        headers.append(('Content-Length', str(len(body))))

    start_response(captured.get('status', '200 OK'), headers, captured.get('exc_info'))
    return [body]


app.wsgi_app = _filter_final_response
