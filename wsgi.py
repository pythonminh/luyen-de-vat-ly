# -*- coding: utf-8 -*-
"""Production entrypoint: GitHub question bank only.

Kept under the traditional ``wsgi:app`` name so Render configurations that
still use the old start command cannot accidentally boot the Google Sheets app.
"""
from wsgi_github import app
