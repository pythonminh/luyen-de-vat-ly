import os
from flask import send_file
from app import app

# Existing integration routes used elsewhere in the application.
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

# ONLY ONE GitHub bank-management UI.
# It reads bank_index.json and ngan-hang/*.tex directly from GitHub.
try:
    from github_manager_ui import bp as github_bank_bp
    app.register_blueprint(github_bank_bp)
    app.config['GITHUB_BANK_UI'] = True
except Exception as e:
    app.config['GITHUB_BANK_UI'] = False
    app.config['GITHUB_BANK_UI_ERROR'] = str(e)

# GitHub is the primary source for the existing Mục lục UI.
try:
    import github_catalog_backend  # noqa: F401
    app.config['GITHUB_CATALOG_ONLY'] = True
except Exception as e:
    app.config['GITHUB_CATALOG_ONLY'] = False
    app.config['GITHUB_CATALOG_ONLY_ERROR'] = str(e)

# Full Dạng bài tập + A/B/C/D breakdown from the .tex bank.
try:
    import github_manager_dang_fix  # noqa: F401
    app.config['GITHUB_MANAGER_DANG_FIX'] = True
except Exception as e:
    app.config['GITHUB_MANAGER_DANG_FIX'] = False
    app.config['GITHUB_MANAGER_DANG_FIX_ERROR'] = str(e)

# Force legacy catalog/meta endpoints to use GitHub and neutralize stale
# Google-Sheet loading labels on the original interface.
try:
    import github_runtime_bridge  # noqa: F401
    app.config['GITHUB_SOURCE_PRIMARY'] = True
    app.config['GOOGLE_SHEET_BANK_BACKUP_ONLY'] = True
except Exception as e:
    app.config['GITHUB_SOURCE_PRIMARY'] = False
    app.config['GITHUB_SOURCE_PRIMARY_ERROR'] = str(e)

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
