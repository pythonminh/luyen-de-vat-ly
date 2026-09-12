# -*- coding: utf-8 -*-
"""Bổ sung file Ôn tập bài 1 vào thanh Dạng mẫu mà không sửa app.py/lythuyet.py."""
from __future__ import annotations
import importlib.abc
import sys

TARGET = "lythuyet"

class _Loader(importlib.abc.Loader):
    def __init__(self, wrapped): self.wrapped = wrapped
    def create_module(self, spec):
        fn = getattr(self.wrapped, "create_module", None)
        return fn(spec) if fn else None
    def exec_module(self, module):
        self.wrapped.exec_module(module)
        _patch(module)

class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname != TARGET: return None
        for finder in list(sys.meta_path):
            if finder is self: continue
            try: spec = finder.find_spec(fullname, path, target)
            except Exception: continue
            if spec and spec.loader:
                spec.loader = _Loader(spec.loader)
                return spec
        return None

def _patch(lt):
    if getattr(lt, "_ontap_patched", False): return
    lt.TRACKS["on_tap"] = {
        "file": "Ôn tập bài 1.tex",
        "route": "/member/on-tap-bai-1",
        "label": "Ôn tập bài 1",
        "icon": "📝",
    }
    old_approved = lt.is_approved
    def is_approved(de_path, kind="lt"):
        if str(kind).strip().lower() == "on_tap":
            return lt.companion_exists(de_path, "on_tap")
        return old_approved(de_path, kind)
    lt.is_approved = is_approved
    from flask import request
    def member_on_tap_bai_1():
        return lt.page_companion(request.args.get("path") or "", "on_tap")
    try:
        lt.app.add_url_rule("/member/on-tap-bai-1", endpoint="member_on_tap_bai_1", view_func=member_on_tap_bai_1, methods=["GET"])
    except Exception:
        pass
    lt._ontap_patched = True

sys.meta_path.insert(0, _Finder())
