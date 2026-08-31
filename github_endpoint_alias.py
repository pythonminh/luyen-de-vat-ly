# -*- coding: utf-8 -*-
"""Compatibility endpoints + registration of the GitHub manager UI."""
from __future__ import annotations
from app import app

def install_question_editor_alias() -> None:
    try:
        from github_question_editor import save_from_question_editor
    except Exception:
        save_from_question_editor = None
    if save_from_question_editor is not None:
        endpoint = "github_source.save_from_question_editor"
        if endpoint not in app.view_functions:
            app.add_url_rule(
                "/github/questions-save",
                endpoint=endpoint,
                view_func=save_from_question_editor,
                methods=["POST"],
            )

try:
    from github_manager_ui import bp as github_manager_bp
    app.register_blueprint(github_manager_bp)
    app.config['GITHUB_MANAGER_UI'] = True
except Exception as e:
    app.config['GITHUB_MANAGER_UI'] = False
    app.config['GITHUB_MANAGER_UI_ERROR'] = str(e)

install_question_editor_alias()
