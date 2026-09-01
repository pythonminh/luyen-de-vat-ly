# -*- coding: utf-8 -*-
"""Single production bootstrap for Render.

Architecture:
- access_control: authentication/session guards
- admin_overrides: member permissions and ADMIN management
- student_overrides: member-only question-bank index
- security_patch: final access checks
- wsgi: practice, testing, Gemini review and GitHub editing UI

Authentication is intentionally single-source: members.json.  No legacy
password layer is loaded here.
"""
import access_control as _access_control

app = _access_control.app

# Apply the application layers in a fixed order.  Do not add alternate
# authentication implementations here.
import admin_overrides as _admin_overrides  # noqa: F401,E402
import student_overrides as _student_overrides  # noqa: F401,E402
import security_patch as _security_patch  # noqa: F401,E402
import wsgi as _wsgi  # noqa: F401,E402
