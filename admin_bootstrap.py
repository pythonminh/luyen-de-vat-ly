# -*- coding: utf-8 -*-
"""Single Render bootstrap.

Load access policy first, then the one authoritative ADMIN/member manager,
then the final filtered student index.  Old duplicate/read-only behaviour is
intercepted instead of maintaining another UI.
"""
import access_control as _access_control

app = _access_control.app

import admin_overrides as _admin_overrides  # noqa: F401,E402
import student_overrides as _student_overrides  # noqa: F401,E402
