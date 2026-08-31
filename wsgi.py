import os
from flask import send_file
from app import app

# GitHub file browser / authentication integration already used by the app.
try:
    from github_integration import bp as github_bp
    app.register_blueprint(github_bp)
except Exception as e:
    app.config['GITHUB_IMPORT_ERROR'] = str(e)

# Existing exam-generation route; kept for the learning application.
try:
    from ra_de_fixed import bp as ra_de_bp
    app.register_blueprint(ra_de_bp)
except Exception as e:
    app.config['RA_DE_IMPORT_ERROR'] = str(e)

# ONE GitHub bank interface: catalog + filtering + per-question editing.
try:
    from github_manager_ui import bp as github_bank_bp
    app.register_blueprint(github_bank_bp)
    app.config['GITHUB_BANK_UI'] = True
except Exception as e:
    app.config['GITHUB_BANK_UI'] = False
    app.config['GITHUB_BANK_UI_ERROR'] = str(e)

# Fast GitHub catalog: renders from local bank_index.json immediately and
# prevents the old Google-Sheet catalog from leaving the page stuck loading.
try:
    import github_fast_catalog  # noqa: F401
    app.config['GITHUB_FAST_CATALOG'] = True
except Exception as e:
    app.config['GITHUB_FAST_CATALOG'] = False
    app.config['GITHUB_FAST_CATALOG_ERROR'] = str(e)


@app.get('/bank_index.json')
def serve_bank_index():
    path = os.path.join(app.root_path, 'bank_index.json')
    return send_file(path, mimetype='application/json', max_age=300, conditional=True)
