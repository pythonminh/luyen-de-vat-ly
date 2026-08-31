import os
from flask import send_file
from app import app

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

try:
    from github_manager_ui import bp as github_bank_bp
    app.register_blueprint(github_bank_bp)
    app.config['GITHUB_BANK_UI'] = True
except Exception as e:
    app.config['GITHUB_BANK_UI'] = False
    app.config['GITHUB_BANK_UI_ERROR'] = str(e)

# GitHub-only: render mục lục nhanh từ bank_index.json, không chờ Google Sheet.
try:
    import github_fast_catalog  # noqa: F401
    app.config['GITHUB_FAST_CATALOG'] = True
except Exception as e:
    app.config['GITHUB_FAST_CATALOG'] = False
    app.config['GITHUB_FAST_CATALOG_ERROR'] = str(e)

try:
    import github_ui_restyle  # noqa: F401
    app.config['GITHUB_UI_RESTYLE'] = True
except Exception as e:
    app.config['GITHUB_UI_RESTYLE'] = False
    app.config['GITHUB_UI_RESTYLE_ERROR'] = str(e)

try:
    import ai_review_ui_fix  # noqa: F401
    app.config['LDVL_AI_REVIEW_UI_FIX'] = True
except Exception as e:
    app.config['LDVL_AI_REVIEW_UI_FIX'] = False
    app.config['LDVL_AI_REVIEW_UI_FIX_ERROR'] = str(e)

@app.get('/bank_index.json')
def serve_bank_index():
    path = os.path.join(app.root_path, 'bank_index.json')
    return send_file(path, mimetype='application/json', max_age=300, conditional=True)
