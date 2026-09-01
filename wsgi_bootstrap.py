# -*- coding: utf-8 -*-
"""Render bootstrap: load extensions, then apply final public UI filtering."""
import re
import wsgi
import student_gemini_ui
import gemini_ui_fix
import member_auth_fix
import gemini_header
import admin_manager

app = wsgi.app


def _filter_final_response(environ, start_response):
    """Buffer Flask's final HTML and apply branding/navigation rules last."""
    captured = {}

    def capture_start(status, headers, exc_info=None):
        captured['status'] = status
        captured['headers'] = list(headers)
        captured['exc_info'] = exc_info
        return lambda data: None

    iterable = app.wsgi_app(environ, capture_start)
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

        # Public branding for every device.
        text = text.replace(
            '📚 Ngân hàng câu hỏi GitHub',
            '📚 Luyện Đề Toán Lý <span class="zalo-brand">Zalo thầy Minh 0946111107</span>'
        )

        # GitHub is an ADMIN editing tool only. It is never shown on /member.
        # /admin/login is also kept clean; authenticated /admin and /github pages
        # are allowed to keep their GitHub navigation link.
        can_show_github = (
            path.startswith('/admin/') and not path.startswith('/admin/login')
        ) or path.startswith('/github/')

        if not can_show_github:
            # Remove links whose href points to github.com, regardless of emoji,
            # spacing, target attribute, or the exact button text.
            text = re.sub(
                r'<a\b[^>]*href=["\'][^"\']*github\.com[^"\']*["\'][^>]*>.*?</a>',
                '', text, flags=re.I | re.S
            )
            # Also remove any residual button/link explicitly labelled GitHub.
            text = re.sub(
                r'<a\b[^>]*>\s*(?:[^<]{0,20})GitHub(?:\s*[^<]{0,20})?</a>',
                '', text, flags=re.I | re.S
            )

        body = text.encode('utf-8')
        headers = [(k, v) for k, v in headers if k.lower() != 'content-length']
        headers.append(('Content-Length', str(len(body))))

    start_response(
        captured.get('status', '200 OK'),
        headers,
        captured.get('exc_info')
    )
    return [body]


# Keep the original Flask callable and put the final filter around it.
_original_wsgi = app.wsgi_app
app.wsgi_app = lambda environ, start_response: _filter_final_response(environ, start_response)


@app.after_request
def responsive_css(response):
    """Responsive styling for laptop, tablet and phone."""
    ctype = response.headers.get('Content-Type', '')
    if 'text/html' not in ctype:
        return response
    try:
        text = response.get_data(as_text=True)
    except Exception:
        return response
    css = '''<style>
.zalo-brand{color:#ffd21f;margin-left:6px;font-weight:900;white-space:nowrap}
.topin{width:100%;max-width:1500px;margin:auto;display:flex;align-items:center;gap:14px}
@media(max-width:900px){.topin{flex-wrap:wrap!important;padding:8px 10px!important}.brand{font-size:18px!important}.nav{width:100%;margin-left:0!important;justify-content:flex-start!important}}
@media(max-width:480px){.brand{font-size:16px!important}.zalo-brand{display:block;margin-left:0;margin-top:2px;font-size:14px}.nav a,.nav button{padding:6px 8px!important;font-size:12px!important}}
</style>'''
    if '</head>' in text and 'zalo-brand' not in text:
        text = text.replace('</head>', css + '</head>', 1)
    response.set_data(text)
    return response
