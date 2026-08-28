from app import app

# GitHub source integration
try:
    from github_integration import bp as github_bp
    app.register_blueprint(github_bp)
except Exception as e:
    github_bp = None
    app.config['GITHUB_IMPORT_ERROR'] = str(e)

# Ra de integration: wrapper patches the question parser before registering
# the existing Ra de blueprint, so \\dangbt{} outside the ex/bt block is read.
try:
    from ra_de_fixed import bp as ra_de_bp
    app.register_blueprint(ra_de_bp)
except Exception as e:
    ra_de_bp = None
    app.config['RA_DE_IMPORT_ERROR'] = str(e)


@app.after_request
def add_source_links(response):
    """Keep GitHub and Ra de reachable from the existing application UI."""
    try:
        if response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)
            if 'data-ldvl-tools="1"' not in text:
                widget = '''
<div data-ldvl-tools="1" style="position:fixed;right:14px;bottom:14px;z-index:99999;display:flex;gap:8px">
  <a href="/ra-de" title="Ra de tu ngan hang GitHub"
     style="display:inline-block;padding:10px 15px;border-radius:10px;background:#1976d2;color:#fff;text-decoration:none;font:700 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">📝 Ra đề</a>
  <a href="/github" title="Doc va quan ly du lieu truc tiep tu GitHub"
     style="display:inline-block;padding:10px 15px;border-radius:10px;background:#24292f;color:#fff;text-decoration:none;font:600 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">🐙 GitHub</a>
</div>
'''
                low = text.lower()
                if '</body>' in low:
                    i = low.rfind('</body>')
                    text = text[:i] + widget + text[i:]
                else:
                    text += widget
                response.set_data(text)
    except Exception:
        pass
    return response
