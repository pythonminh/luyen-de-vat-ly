# -*- coding: utf-8 -*-
"""Single Render bootstrap: load the stable app, then apply final public UI rules."""
import re
import wsgi
import student_gemini_ui
import gemini_ui_fix
import member_auth_fix
import gemini_header
import admin_manager

from flask import request, session

app = wsgi.app


def _final_html_filter(environ, start_response):
    """Final WSGI response filter. Runs after Flask extensions/after_request hooks."""
    captured = {}

    def capture_start(status, headers, exc_info=None):
        captured['status'] = status
        captured['headers'] = headers
        captured['exc_info'] = exc_info
        return lambda data: None

    chunks = []
    try:
        iterable = app.wsgi_app(environ, capture_start)
        for chunk in iterable:
            chunks.append(chunk)
        if hasattr(iterable, 'close'):
            iterable.close()
        body = b''.join(chunks)
    except Exception:
        raise

    headers = list(captured.get('headers', []))
    ctype = next((v for k, v in headers if k.lower() == 'content-type'), '')
    if 'text/html' in ctype:
        text = body.decode('utf-8', 'replace')

        # Final branding: this is the public name shown on laptop/phone/tablet.
        text = text.replace(
            '📚 Ngân hàng câu hỏi GitHub',
            '📚 Luyện Đề Toán Lý <span class="zalo-brand">Zalo thầy Minh 0946111107</span>'
        )

        role = session.get('role')
        path = environ.get('PATH_INFO', '') or '/'
        is_admin = role == 'admin'
        can_show_github = is_admin and (path.startswith('/admin') or path.startswith('/github'))

        # Remove every GitHub navigation link for students/public pages.
        # This is intentionally broader than matching one exact HTML form.
        if not can_show_github:
            text = re.sub(
                r'<a\\b[^>]*href=["\\\'][^"\\\']*github[^"\\\']*["\\\'][^>]*>.*?</a>',
                '', text, flags=re.I | re.S
            )
            text = re.sub(
                r'<a\\b[^>]*>\\s*(?:🐙\\s*)?GitHub\\s*</a>',
                '', text, flags=re.I | re.S
            )

        # Never expose the old GitHub branding/source label to students.
        if not is_admin:
            text = re.sub(r'\\s*·\\s*GitHub(?=\\s|</div>|</span>)', '', text, flags=re.I)

        body = text.encode('utf-8')
        headers = [(k, v) for k, v in headers if k.lower() != 'content-length']
        headers.append(('Content-Length', str(len(body))))

    start_response(captured.get('status', '200 OK'), headers, captured.get('exc_info'))
    return [body]


# Replace the final WSGI callable only after every imported extension has loaded.
# This guarantees the branding/GitHub rule is the LAST layer seen by Render.
_original_wsgi = app.wsgi_app


def _wrapped_wsgi(environ, start_response):
    # Temporarily expose the already-built Flask WSGI app through the filter.
    global _original_wsgi
    old = app.wsgi_app
    app.wsgi_app = _original_wsgi
    try:
        captured = {}
        def cap_start(status, headers, exc_info=None):
            captured['status'] = status
            captured['headers'] = headers
            captured['exc_info'] = exc_info
            return lambda data: None
        chunks = []
        iterable = _original_wsgi(environ, cap_start)
        for chunk in iterable:
            chunks.append(chunk)
        if hasattr(iterable, 'close'):
            iterable.close()
        body = b''.join(chunks)
        headers = list(captured.get('headers', []))
        ctype = next((v for k, v in headers if k.lower() == 'content-type'), '')
        if 'text/html' in ctype:
            text = body.decode('utf-8', 'replace')
            text = text.replace('📚 Ngân hàng câu hỏi GitHub', '📚 Luyện Đề Toán Lý <span class="zalo-brand">Zalo thầy Minh 0946111107</span>')
            role = session.get('role')
            path = environ.get('PATH_INFO', '') or '/'
            can_show_github = role == 'admin' and (path.startswith('/admin') or path.startswith('/github'))
            if not can_show_github:
                text = re.sub(r'<a\\b[^>]*href=["\\\'][^"\\\']*github[^"\\\']*["\\\'][^>]*>.*?</a>', '', text, flags=re.I|re.S)
                text = re.sub(r'<a\\b[^>]*>\\s*(?:🐙\\s*)?GitHub\\s*</a>', '', text, flags=re.I|re.S)
            if role != 'admin':
                text = re.sub(r'\\s*·\\s*GitHub(?=\\s|</div>|</span>)', '', text, flags=re.I)
            body = text.encode('utf-8')
            headers = [(k,v) for k,v in headers if k.lower() != 'content-length']
            headers.append(('Content-Length', str(len(body))))
        start_response(captured.get('status','200 OK'), headers, captured.get('exc_info'))
        return [body]
    finally:
        app.wsgi_app = old

app.wsgi_app = _wrapped_wsgi


# Responsive CSS is kept as an extra safety layer for all public pages.
@app.after_request
def responsive_branding_css(response):
    ctype = response.headers.get('Content-Type', '')
    if 'text/html' not in ctype:
        return response
    try:
        text = response.get_data(as_text=True)
    except Exception:
        return response
    css = '''<style>
.zalo-brand{color:#ffd21f;margin-left:6px;font-weight:900;white-space:nowrap}
@media(max-width:900px){.topin{flex-wrap:wrap!important;padding:8px 10px!important}.brand{font-size:18px!important}.nav{width:100%;margin-left:0!important;justify-content:flex-start!important}}
@media(max-width:480px){.brand{font-size:16px!important}.zalo-brand{display:block;margin-left:0;margin-top:2px;font-size:14px}.nav a,.nav button{padding:6px 8px!important;font-size:12px!important}}
</style>'''
    if '</head>' in text and 'zalo-brand' not in text:
        text = text.replace('</head>', css + '</head>', 1)
    response.set_data(text)
    return response
