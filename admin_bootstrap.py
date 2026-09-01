# -*- coding: utf-8 -*-
"""Single Render bootstrap.

Load the access policy, authoritative ADMIN/member manager, student access
patches, legacy password compatibility, and the existing practice/Gemini UI.
The login layer is loaded before the UI patch so the ADMIN session remains
unchanged while Gemini features are added to member practice pages.
"""
import access_control as _access_control

app = _access_control.app

import admin_overrides as _admin_overrides  # noqa: F401,E402
import student_overrides as _student_overrides  # noqa: F401,E402
import security_patch as _security_patch  # noqa: F401,E402
import legacy_auth as _legacy_auth  # noqa: F401,E402
import wsgi as _wsgi  # noqa: F401,E402
