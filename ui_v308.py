"""V308 visual layer for the existing Flask application.

The backend/routes remain in app.py. This module only injects the V308
CSS/JS into HTML responses so the existing application keeps its behavior.
"""

from __future__ import annotations

from flask import make_response

from app import app as app

_V308_HEAD = """
<link rel="stylesheet" href="/static/v308.css?v=311">
<script defer src="/static/v308.js?v=311"></script>
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
        if "v308.css?v=311" in body:
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
        return response


@app.route("/ui-v308-preview")
def ui_v308_preview():
    """Standalone visual preview; safe to remove after UI approval."""
    return """<!doctype html>
<html lang='vi'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Luyen De Vat Ly - V311 Preview</title>
<link rel='stylesheet' href='/static/v308.css?v=311'>
<script defer src='/static/v308.js?v=311'></script>
</head>
<body class='v308-preview'>
<main class='v308-preview-shell'>
  <section class='v308-hero'>
    <div class='v308-brand-mark'>V</div>
    <div>
      <p class='v308-eyebrow'>LOP HOC THAY MINH</p>
      <h1>LUYEN DE VAT LY</h1>
      <p class='v308-subtitle'>Giao dien V311 - hien dai, ro rang, toi uu cho hoc sinh va giao vien.</p>
    </div>
  </section>
  <section class='v308-grid'>
    <article class='v308-card v308-card-accent'><span>01</span><strong>Kho de</strong><small>De luyen tap theo lop, chuong va muc do.</small><button type='button'>Xem kho de</button></article>
    <article class='v308-card'><span>02</span><strong>Luyen de</strong><small>Giao dien lam bai tap trung, dong ho va bang cau hoi.</small><button type='button'>Bat dau</button></article>
    <article class='v308-card'><span>03</span><strong>Ket qua</strong><small>Theo doi diem so, tien do va cac chu de can on.</small><button type='button'>Xem ket qua</button></article>
    <article class='v308-card'><span>04</span><strong>Tro ly AI</strong><small>Goi y phuong phap va ho tro giai bai.</small><button type='button'>Mo AI</button></article>
  </section>
</main>
</body>
</html>"""
