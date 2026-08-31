# -*- coding: utf-8 -*-
"""Compatibility aliases for legacy endpoint names used by the editor."""
from __future__ import annotations

from app import app


def install_question_editor_alias() -> None:
    """Expose the old github_source endpoint name without changing the real route."""
    try:
        from github_question_editor import save_from_question_editor
    except Exception:
        return

    endpoint = "github_source.save_from_question_editor"
    if endpoint in app.view_functions:
        return

    # The real route is already registered by github_question_editor.
    # This alias exists mainly so url_for('github_source.save_from_question_editor')
    # used by older templates continues to resolve.
    app.add_url_rule(
        "/github/questions-save",
        endpoint=endpoint,
        view_func=save_from_question_editor,
        methods=["POST"],
    )


install_question_editor_alias()
