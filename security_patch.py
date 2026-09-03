# -*- coding: utf-8 -*-
"""Make the final class/SVIP access function authoritative everywhere."""
import app as base
import access_control
import dang_routes
from admin_overrides import _can_member_see


def final_can_access(member, path):
    if getattr(base, "has_full_bank_access", lambda *_: False)(member):
        return True
    try:
        if base.admin_current():
            return True
    except Exception:
        pass
    if not member:
        return False
    try:
        import membership as pkg
        return pkg.can_access_path(member, path)
    except Exception:
        pass
    for item in base.index_data().get('lessons', []):
        if not isinstance(item, dict):
            continue
        p = str(item.get('path') or item.get('file') or '')
        if p == str(path):
            return _can_member_see(member, item)
    return False


base.can_access = final_can_access
access_control.student_can_access = final_can_access
dang_routes.can_access = final_can_access
dang_routes.can_view = base.can_view
