# -*- coding: utf-8 -*-
"""Single Render bootstrap: stable app + auth + Gemini endpoint + final UI."""
import re
import wsgi
import member_auth_fix
import student_gemini
import admin_manager
import ui_sync

app = wsgi.app
_original_wsgi = app.wsgi_app


def _filter_final_response(environ, start_response):
    """Final safety pass after every Flask extension response."""
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
        text = text.replace('📚 Ngân hàng câu hỏi GitHub', '📚 Luyện Đề Toán Lý')
        text = text.replace('MỤC LỤC · GitHub', 'MỤC LỤC')
        # GitHub is visible only in the authenticated admin editing area.
        can_show_github = (
            path == '/admin' or path.startswith('/admin/')
            or path == '/github' or path.startswith('/github/')
        ) and not path.startswith('/admin/login')
        if not can_show_github:
            text = re.sub(r'<a\b[^>]*href=["\'][^"\']*github\.com[^"\']*["\'][^>]*>.*?</a>', '', text, flags=re.I|re.S)
            text = re.sub(r'<button\b[^>]*>\s*🐙\s*GitHub\s*</button>', '', text, flags=re.I)
            text = re.sub(r'\s*🐙\s*GitHub\s*', ' ', text, flags=re.I)
        body = text.encode('utf-8')
        headers = [(k, v) for k, v in headers if k.lower() != 'content-length']
        headers.append(('Content-Length', str(len(body))))

    start_response(captured.get('status', '200 OK'), headers, captured.get('exc_info'))
    return [body]


# This WSGI wrapper is the last safety layer for public HTML.
app.wsgi_app = _filter_final_response
