# -*- coding: utf-8 -*-
"""Single Render bootstrap.

Load access policy first, then the one authoritative ADMIN/member manager,
then the final filtered student index, password compatibility, and finally
patch every question route to the same class/SVIP access check.
"""
import access_control as _access_control

app = _access_control.app

import admin_overrides as _admin_overrides  # noqa: F401,E402
import student_overrides as _student_overrides  # noqa: F401,E402
import security_patch as _security_patch  # noqa: F401,E402
import legacy_auth as _legacy_auth  # noqa: F401,E402
