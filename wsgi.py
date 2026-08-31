from flask import send_file, request
from app import app

# Existing non-bank routes.
try:
    from github_integration import bp as github_bp
    app.register_blueprint(github_bp)
except Exception as e:
    app.config['GITHUB_IMPORT_ERROR'] = str(e)

try:
    from ra_de_fixed import bp as ra_de_bp
    app.register_blueprint(ra_de_bp)
except Exception as e:
    app.config['RA_DE_IMPORT_ERROR'] = str(e)

# GitHub bank UI.
try:
    import github_bank_force  # noqa: F401
    app.config['GITHUB_BANK_FORCE'] = True
except Exception as e:
    app.config['GITHUB_BANK_FORCE'] = False
    app.config['GITHUB_BANK_FORCE_ERROR'] = str(e)

# DEPLOY MARKER: 2026-08-31 — Render must reload wsgi.py from this commit.
# IMPORTANT: Procfile runs `gunicorn wsgi:app -c gunicorn.conf.py`, so this file
# is the actual production entrypoint for the GitHub bank UI.

@app.after_request
def add_github_repo_link(response):
    """Hiện nút GitHub trên giao diện chính và giao diện ngân hàng."""
    try:
        if response.content_type == 'text/html; charset=utf-8':
            body = response.get_data(as_text=True)
            if 'id="ldvl-github-main-link"' not in body:
                top_link = (
                    '<div id="ldvl-github-main-link" '
                    'style="position:fixed;right:16px;top:78px;z-index:2147483647;">'
                    '<a href="/github/quan-ly" '
                    'style="display:inline-flex;align-items:center;gap:6px;padding:8px 13px;'
                    'border-radius:10px;background:#24292f;color:#fff;text-decoration:none;'
                    'font-weight:900;font-size:12px;box-shadow:0 3px 12px #0003;">'
                    '🐙 Ngân hàng GitHub</a></div>'
                )
                body = body.replace('</body>', top_link + '</body>')
                response.set_data(body)
    except Exception:
        pass
    return response

@app.get('/github/repo')
def github_repo_redirect():
    from flask import redirect
    return redirect('https://github.com/pythonminh/luyen-de-vat-ly', code=302)

@app.get('/bank_index.json')
def serve_bank_index():
    import os
    return send_file(
        os.path.join(app.root_path, 'bank_index.json'),
        mimetype='application/json',
        max_age=120,
        conditional=True,
    )
