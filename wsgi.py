from app import app
try:
    from github_integration import github_bp
    app.register_blueprint(github_bp)
except Exception:
    pass

@app.after_request
def add_github_source_link(response):
    try:
        if response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)
            marker = '<a href="/admin/json" title="ADMIN tạo, đọc thử, xuất JSON">'
            if marker in text and 'href="/github"' not in text:
                text = text.replace(marker, '<a href="/github" title="Đọc và quản lý dữ liệu trực tiếp từ GitHub"><i class="ti ti-brand-github"></i> GitHub</a>' + marker, 1)
                response.set_data(text)
    except Exception:
        pass
    return response
