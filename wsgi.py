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

@app.after_request
def add_github_repo_link(response):
    """Hiện nút mở repository GitHub ngay trên giao diện ngân hàng."""
    try:
        if request.path.startswith('/github/quan-ly') and response.content_type == 'text/html; charset=utf-8':
            body = response.get_data(as_text=True)
            if 'id="ldvl-github-repo-link"' not in body:
                top_link = (
                    '<a id="ldvl-github-repo-link" href="/github/repo" target="_blank" rel="noopener" '
                    'style="display:inline-block;margin-left:auto;padding:8px 12px;border-radius:10px;'
                    'background:#24292f;color:#fff;text-decoration:none;font-weight:900;white-space:nowrap;">'
                    '🐙 GitHub</a>'
                )
                if '</body>' in body:
                    # Put the button in the visible top area as well as a floating shortcut.
                    body = body.replace('</body>', top_link + '<div id="ldvl-github-repo-float" '
                        'style="position:fixed;right:16px;bottom:16px;z-index:99999;">'
                        '<a href="/github/repo" target="_blank" rel="noopener" '
                        'style="display:inline-block;padding:10px 14px;border-radius:10px;'
                        'background:#24292f;color:#fff;text-decoration:none;font-weight:800;'
                        'box-shadow:0 4px 14px #0003">🐙 Mở GitHub</a></div></body>')
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
