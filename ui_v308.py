"""
V308 UI wrapper for the existing Flask application.

The backend remains in app.py. This module imports the same Flask app and
adds the V308 visual layer to HTML responses from the existing root page.
"""

from __future__ import annotations

from flask import make_response

from app import app as app

_V308_HEAD = """
<link rel="stylesheet" href="/static/v308.css?v=308">
<script defer src="/static/v308.js?v=308"></script>
"""


def _inject_v308(response):
    """Add V308 assets to HTML only; never modify JSON/API responses."""
    try:
        resp = make_response(response)
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type:
            return resp

        body = resp.get_data(as_text=True)
        if "v308.css" in body:
            return resp

        lower = body.lower()
        marker = "</head>"
        if marker in lower:
            idx = lower.find(marker)
            body = body[:idx] + _V308_HEAD + body[idx:]
        else:
            body = _V308_HEAD + body

        resp.set_data(body)
        return resp
    except Exception:
        # The redesign must never take down the existing application.
        return response


# Wrap the existing root view without changing the Flask route or endpoint.
for _rule in list(app.url_map.iter_rules()):
    if _rule.rule == "/":
        _endpoint = _rule.endpoint
        _original = app.view_functions.get(_endpoint)
        if _original is not None and not getattr(_original, "_v308_wrapped", False):

            def _make_wrapper(view):
                def _wrapped(*args, **kwargs):
                    return _inject_v308(view(*args, **kwargs))

                _wrapped._v308_wrapped = True
                _wrapped.__name__ = getattr(view, "__name__", "v308_root")
                return _wrapped

            app.view_functions[_endpoint] = _make_wrapper(_original)


@app.route("/ui-v308-preview")
def ui_v308_preview():
    """Standalone visual preview; safe to remove after UI approval."""
    return """<!doctype html>
<html lang='vi'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Luyện Đề Vật Lý — V308 Preview</title>
<link rel='stylesheet' href='/static/v308.css?v=308'>
<script defer src='/static/v308.js?v=308'></script>
</head>
<body class='v308-preview'>
<main class='v308-preview-shell'>
  <section class='v308-hero'>
    <div class='v308-brand-mark'>⚛</div>
    <div>
      <p class='v308-eyebrow'>LỚP HỌC THẦY MINH</p>
      <h1>LUYỆN ĐỀ VẬT LÝ</h1>
      <p class='v308-subtitle'>Giao diện V308 — hiện đại, rõ ràng, tối ưu cho học sinh và giáo viên.</p>
    </div>
  </section>
  <section class='v308-grid'>
    <article class='v308-card v308-card-accent'><span>📚</span><strong>Kho đề</strong><small>Đề luyện tập theo lớp, chương và mức độ.</small><button type='button'>Xem kho đề</button></article>
    <article class='v308-card'><span>⚡</span><strong>Luyện đề</strong><small>Giao diện làm bài tập trung, đồng hồ và bảng câu hỏi.</small><button type='button'>Bắt đầu</button></article>
    <article class='v308-card'><span>📊</span><strong>Kết quả</strong><small>Theo dõi điểm số, tiến độ và các chủ đề cần ôn.</small><button type='button'>Xem kết quả</button></article>
    <article class='v308-card'><span>🤖</span><strong>Trợ lý AI</strong><small>Gợi ý phương pháp và hỗ trợ giải bài.</small><button type='button'>Mở AI</button></article>
  </section>
</main>
</body>
</html>"""
