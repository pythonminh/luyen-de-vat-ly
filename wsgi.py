from flask import send_file
from app import app

# Giữ các route khác của ứng dụng.
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

# NGÂN HÀNG GITHUB — giao diện kiểu sách, một module duy nhất.
# Không gọi Google Sheet trong luồng ngân hàng.
try:
    from github_bank_book import bp as github_bank_bp
    app.register_blueprint(github_bank_bp)
    app.config['GITHUB_BANK_BOOK'] = True
except Exception as e:
    app.config['GITHUB_BANK_BOOK'] = False
    app.config['GITHUB_BANK_BOOK_ERROR'] = str(e)

@app.get('/bank_index.json')
def serve_bank_index():
    import os
    return send_file(os.path.join(app.root_path, 'bank_index.json'), mimetype='application/json', max_age=120, conditional=True)
