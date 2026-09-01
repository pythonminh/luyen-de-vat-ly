# -*- coding: utf-8 -*-
"""Single Render bootstrap.

Loads the class-based access layer first, then the one authoritative ADMIN
member/password/access-management layer.  Old read-only ADMIN routes are
intercepted by admin_overrides.py instead of maintaining a second UI.
"""
import access_control as _access_control

app = _access_control.app

# Must be last: it replaces the old ADMIN login/manager behaviour and applies
# the same student access rule to all existing question-opening endpoints.
import admin_overrides as _admin_overrides  # noqa: F401,E402
