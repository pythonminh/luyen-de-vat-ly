from flask import send_file
from app import app

# Các route khác của ứng dụng vẫn giữ nguyên.
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

# NGÂN HÀNG GITHUB — chỉ một giao diện, không gọi Google Sheet.
try:
    from github_bank_simple import bp as github_bank_bp
    # github_bank_simple tự register blueprint ở module; không đăng ký lần hai.
    app.config['GITHUB_BANK_SIMPLE'] = True
except Exception as e:
    app.config['GITHUB_BANK_SIMPLE'] = False
    app.config['GITHUB_BANK_SIMPLE_ERROR'] = str(e)

@app.get('/bank_index.json')
def serve_bank_index():
    import os
    return send_file(
        os.path.join(app.root_path, 'bank_index.json'),
        mimetype='application/json',
        max_age=120,
        conditional=True,
    )
