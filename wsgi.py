from app import app

# GitHub integration: fail loudly only on the GitHub page, never break the main app.
try:
    from github_integration import bp
    app.register_blueprint(bp)
except Exception:
    bp = None

@app.after_request
def add_github_source_link(response):
    """Always expose the GitHub reader in the main app UI.

    The previous version looked for one exact /admin/json HTML marker. The
    current UI does not always contain that marker, so the GitHub link could
    disappear even though the route was installed. We now inject a small
    fixed GitHub button into every HTML response that does not already have
    the link.
    """
    try:
        if response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)
            if 'href="/github"' not in text and "href='/github'" not in text:
                widget = '''
<div id="ldvl-github-link" style="position:fixed;right:14px;bottom:14px;z-index:99999">
  <a href="/github" title="Đọc và quản lý dữ liệu trực tiếp từ GitHub"
     style="display:inline-block;padding:9px 14px;border-radius:10px;background:#24292f;color:#fff;text-decoration:none;font:600 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">
     🐙 GitHub
  </a>
</div>
'''
                if '</body>' in text.lower():
                    idx = text.lower().rfind('</body>')
                    text = text[:idx] + widget + text[idx:]
                else:
                    text += widget
                response.set_data(text)
    except Exception:
        pass
    return response
