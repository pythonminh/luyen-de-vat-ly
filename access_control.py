# -*- coding: utf-8 -*-
"""Student class-based access control.

Rules:
- Student sees only lessons belonging to their assigned grade (10/11/12).
- Only SVIP can see all grades.
- ADMIN is never restricted by this student policy.
"""
from __future__ import annotations

import html
import re
from urllib.parse import unquote

import server_clean
import app as base
import dang_routes

app = server_clean.app


def _grade(value: object) -> str:
    """Extract the school grade (10/11/12) from values such as 12QT1, 10D12, Lớp 11."""
    s = str(value or "").strip().upper()
    m = re.search(r"(?<!\d)(10|11|12)(?!\d)", s)
    return m.group(1) if m else ""


def is_svip(member: dict | None) -> bool:
    if not member:
        return False
    return str(member.get("account_type", "FREE")).strip().upper() in {"SVIP", "S.VIP", "S-VIP"}


def lesson_grade(path: str) -> str:
    """Read lesson grade from bank_index.json by path."""
    target = str(path or "").strip()
    for item in base.index_data().get("lessons", []):
        if not isinstance(item, dict):
            continue
        p = str(item.get("path") or item.get("file") or "").strip()
        if p == target:
            return _grade(item.get("Lop") or item.get("lop") or item.get("class"))
    return ""


def student_can_access(member: dict | None, path: str) -> bool:
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
    if is_svip(member):
        return True
    student_grade = _grade(member.get("class"))
    if not student_grade:
        return False
    return bool(lesson_grade(path) and lesson_grade(path) == student_grade)


# app.member_select uses app.can_access dynamically; dang_routes imported its
# helper by value, so patch both references.
base.can_access = student_can_access
dang_routes.can_access = student_can_access


def _card_blocks(body: str):
    """Yield (start,end,html) for top-level .card blocks, handling nested divs."""
    starts = list(re.finditer(r"<div\b[^>]*class=['\"][^'\"]*\bcard\b[^'\"]*['\"][^>]*>", body, re.I))
    token = re.compile(r"<div\b[^>]*>|</div\s*>", re.I)
    for start in starts:
        depth = 0
        for m in token.finditer(body, start.start()):
            if m.group(0).lower().startswith("<div"):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    yield start.start(), m.end(), body[start.start():m.end()]
                    break


def _allowed_paths(member: dict) -> set[str]:
    try:
        import membership as pkg
        return pkg.allowed_paths(member)
    except Exception:
        pass
    all_paths = {
        str(x.get("path") or x.get("file") or "").strip()
        for x in base.index_data().get("lessons", [])
        if isinstance(x, dict) and str(x.get("path") or x.get("file") or "").strip()
    }
    if getattr(base, "is_admin_member", lambda *_: False)(member) or is_svip(member):
        return all_paths
    try:
        if base.admin_current():
            return all_paths
    except Exception:
        pass
    sg = _grade(member.get("class"))
    if not sg:
        return set()
    out = set()
    for item in base.index_data().get("lessons", []):
        if not isinstance(item, dict):
            continue
        p = str(item.get("path") or item.get("file") or "").strip()
        lg = _grade(item.get("Lop") or item.get("lop") or item.get("class"))
        if p and lg == sg:
            out.add(p)
    return out


_original_nav = server_clean._nav


def _nav_with_class() -> str:
    nav = _original_nav()
    try:
        if server_clean.session.get("role") == "member":
            m = base.member_current() or {}
            name = html.escape(str(m.get("name") or m.get("username") or "Học viên"))
            grade = _grade(m.get("class"))
            label = f"🎓 Lớp {grade}" if grade else "🎓 Chưa được cấp lớp"
            user = f"<span class='user-pill'>👤 {name} · {html.escape(label)}</span>"
            nav = re.sub(r"<span class='user-pill'>.*?</span>", user, nav, count=1, flags=re.I | re.S)
    except Exception:
        pass
    return nav


server_clean._nav = _nav_with_class


@app.after_request
def filter_member_catalog(response):
    if server_clean.request.path != "/member" or "text/html" not in response.headers.get("Content-Type", ""):
        return response
    try:
        member = base.member_current()
        if not member:
            return response
        if getattr(base, "has_full_bank_access", lambda *_: False)(member) or getattr(base, "is_admin_member", lambda *_: False)(member):
            return response
        allowed = _allowed_paths(member)
        body = response.get_data(as_text=True)

        # Remove lesson cards that are outside the student's grade.
        replacements = []
        for start, end, block in _card_blocks(body):
            m = re.search(r"/member/select\?path=([^'\"]+)", block, re.I)
            if not m:
                continue
            path = unquote(m.group(1))
            if path not in allowed:
                replacements.append((start, end, ""))
        for start, end, replacement in reversed(replacements):
            body = body[:start] + replacement + body[end:]

        grade = _grade(member.get("class"))
        if is_svip(member):
            notice = "<div class='notice access-note'><b>⭐ SVIP</b> · Được xem toàn bộ khối lớp.</div>"
        elif grade:
            notice = f"<div class='notice access-note'><b>🎓 Học viên: {html.escape(str(member.get('name') or member.get('username') or ''))}</b> · <b>Lớp {html.escape(grade)}</b> · Chỉ hiển thị bài của khối {html.escape(grade)}.</div>"
        else:
            notice = "<div class='notice access-note err'><b>⚠ Chưa được ADMIN cấp lớp.</b> Vui lòng liên hệ thầy Minh để được cấp quyền truy cập.</div>"
        if "access-note" not in body:
            body = re.sub(r"(<div class=['\"]body['\"]>)", r"\1" + notice, body, count=1, flags=re.I)

        style = "<style>.access-note{margin-bottom:10px;font-weight:700}.user-pill{white-space:nowrap}@media(max-width:600px){.user-pill{font-size:11px}}</style>"
        if "</head>" in body:
            body = body.replace("</head>", style + "</head>", 1)
        response.set_data(body)
    except Exception:
        pass
    return response


@app.after_request
def add_svip_option_for_admin(response):
    if server_clean.request.path != "/admin/members" or "text/html" not in response.headers.get("Content-Type", ""):
        return response
    try:
        body = response.get_data(as_text=True)
        if ">SVIP</option>" not in body:
            body = body.replace(">VIP</option>", ">VIP</option><option>SVIP</option>", 1)
        body = body.replace("ADMIN có thể đổi <b>VIP/FREE</b>", "ADMIN có thể đổi <b>FREE/VIP/SVIP</b>")
        response.set_data(body)
    except Exception:
        pass
    return response
