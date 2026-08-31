from flask import send_file
from app import app

# Existing non-bank routes (kept for the main application).
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

# GitHub bank UI: this module owns /github/quan-ly and its API routes.
try:
    import github_bank_force  # noqa: F401
    app.config['GITHUB_BANK_FORCE'] = True
except Exception as e:
    app.config['GITHUB_BANK_FORCE'] = False
    app.config['GITHUB_BANK_FORCE_ERROR'] = str(e)

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
