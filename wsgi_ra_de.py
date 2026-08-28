from wsgi import app

try:
    from ra_de import bp as ra_de_bp
    app.register_blueprint(ra_de_bp)
except Exception:
    ra_de_bp = None

@app.after_request
def add_ra_de_button(response):
    try:
        if response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)
            if 'data-ldvl-ra-de="1"' not in text:
                widget = '''<div data-ldvl-ra-de="1" style="position:fixed;right:14px;bottom:14px;z-index:99999"><a href="/ra-de" style="display:inline-block;padding:10px 16px;border-radius:10px;background:#1976d2;color:#fff;text-decoration:none;font:700 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">📝 Ra đề</a></div>'''
                low = text.lower()
                if '</body>' in low:
                    i = low.rfind('</body>')
                    text = text[:i] + widget + text[i:]
                else:
                    text += widget
                response.set_data(text)
    except Exception:
        pass
    return response
