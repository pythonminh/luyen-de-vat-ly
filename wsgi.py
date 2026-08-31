from flask import send_file
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

# Optional old bank module: kept only for its helper APIs if it imports cleanly.
try:
    from github_bank_book import bp as github_bank_bp
    app.register_blueprint(github_bank_bp)
    app.config['GITHUB_BANK_BOOK'] = True
except Exception as e:
    app.config['GITHUB_BANK_BOOK'] = False
    app.config['GITHUB_BANK_BOOK_ERROR'] = str(e)

# FORCE the new lightweight GitHub bank UI after all legacy routes are loaded.
try:
    import github_bank_force  # noqa: F401
    app.config['GITHUB_BANK_FORCE'] = True
except Exception as e:
    app.config['GITHUB_BANK_FORCE'] = False
    app.config['GITHUB_BANK_FORCE_ERROR'] = str(e)

@app.get('/bank_index.json')
def serve_bank_index():
    import os
    return send_file(
        os.path.join(app.root_path, 'bank_index.json'),
        mimetype='application/json',
        max_age=120,
        conditional=True,
    )
