# -*- coding: utf-8 -*-
from flask import request, redirect, url_for
from app import app

try:
    import github_safe_editor  # registers the safe editor blueprint
except Exception:
    github_safe_editor = None

@app.before_request
def redirect_legacy_question_editor():
    if request.path == '/github/questions':
        return redirect(url_for('github_safe_editor.editor', **request.args))
