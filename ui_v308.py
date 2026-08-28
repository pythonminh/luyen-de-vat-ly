"""V308 visual layer for the existing Flask application.

The backend/routes remain in app.py. This module only injects the V308
CSS/JS into HTML responses so the existing application keeps its behavior.
"""

from __future__ import annotations

from flask import make_response

from app import app as app

_V308_HEAD = """
<link rel="stylesheet" href="/static/v308.css?v=309">
<script defer src="/static/v308.js?v=309"></script>
"""


@app.after_request
def _inject_v308(response):
    """Add V308 assets to every HTML response; never touch JSON/API data."""
    try:
        resp = make_response(response)
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type:
            return resp

        body = resp.get_data(as_text=True)
        if "v308.css?v=309" in body:
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


@app.route("/ui-v308-preview")
def ui_v308_preview():
    """Standalone visual preview; safe to remove after UI approval."""
    return """<!doctype html>
<html lang='vi'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Luyện Đề Vật Lý — V308 Preview</title>
<link rel='stylesheet' href='/static/v308.css?v=309'>
<script defer src='/static/v308.js?v=309'></script>
</head>
<body class='v308-preview'>
<main class='v308-preview-shell'>
  <section class='v308-hero'>
    <div class='v308-brand-mark'>⚛</div>
    <div>
      <p class='v308-eyebrow'>LỚP HỌC THẦY MINH</p>
      <h1>LUYỆN ĐỀ VẬT LÝ</h1>
      <p class='v308-subtitle'>Giao diện V309 — hiện đại, rõ ràng, tối ưu cho học sinh và giáo viên.</p>
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
