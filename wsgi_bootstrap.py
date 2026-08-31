# -*- coding: utf-8 -*-
"""Single Render bootstrap: load the stable app, then all required extensions."""
import wsgi
import student_gemini_ui
import gemini_ui_fix
import member_auth_fix

app = wsgi.app
