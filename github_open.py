# -*- coding: utf-8 -*-
"""Ổn định hóa liên kết từ Mục lục GitHub sang trình sửa từng câu."""
from __future__ import annotations

from flask import Blueprint, request, redirect, url_for

bp = Blueprint("github_open", __name__)


@bp.get("/github/open")
def open_bank_file():
    path = (request.args.get("path") or "").strip("/")
    branch = (request.args.get("branch") or "main").strip()
    if not (path.startswith("ngan-hang/") and path.lower().endswith(".tex") and ".." not in path):
        return ("<h3>Đường dẫn file ngân hàng không hợp lệ.</h3>", 400)
    return redirect(url_for("github_question_editor.questions", branch=branch, path=path))

app = None
try:
    from app import app as _app
    _app.register_blueprint(bp)
    app = _app
except Exception:
    pass
