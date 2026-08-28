from wsgi import app

try:
    from ra_de import bp as ra_de_bp
    app.register_blueprint(ra_de_bp)
except Exception:
    ra_de_bp = None
