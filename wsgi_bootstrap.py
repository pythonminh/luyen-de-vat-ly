# -*- coding: utf-8 -*-
"""Single Render bootstrap: load the stable app, then all small UI/auth extensions."""
import wsgi
import student_gemini_ui
import member_auth_fix

app = wsgi.app
