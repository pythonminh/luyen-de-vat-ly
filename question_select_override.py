# -*- coding: utf-8 -*-
"""Start a practice using exactly the questions checked on /member/dang."""
from __future__ import annotations
import urllib.parse
import random
from flask import request, redirect, session
import app as base


def _start_selected():
    if request.method != 'POST':
        return redirect('/member')
    m = base.member_current()
    if not m:
        return redirect('/member/login')

    path = request.form.get('path', '').strip()
    dang = request.form.get('dang', '').strip()
    if not path or not base.can_access(m, path):
        return redirect('/member')

    try:
        _, tex = base.read_tex(path)
        qs = base.parse_questions(tex)
    except Exception:
        return redirect('/member')

    # Restrict IDs to the exact selected DẠNG, using the same idx values
    # rendered by dang_routes.py.  Never silently substitute another set.
    valid = {
        int(q.get('idx'))
        for q in qs
        if str(q.get('idx', '')).isdigit() and str(q.get('dang') or '').strip() == dang
    }
    if not valid and dang == 'Chưa phân dạng':
        valid = {
            int(q.get('idx'))
            for q in qs
            if str(q.get('idx', '')).isdigit() and not str(q.get('dang') or '').strip()
        }

    ids = []
    for raw in request.form.getlist('qid'):
        try:
            i = int(raw)
        except (TypeError, ValueError):
            continue
        if i in valid and i not in ids:
            ids.append(i)

    if not ids:
        url = '/member/dang?path=' + urllib.parse.quote(path, safe='')
        if dang:
            url += '&dang=' + urllib.parse.quote(dang, safe='')
        return redirect(url)

    # Keep the exact checked IDs. Do not re-select by N/H/V/C and do not
    # replace the selection with the old random-count mechanism.
    session.update(
        practice_path=path,
        practice_ids=ids,
        practice_pos=0,
        practice_right=0,
        practice_streak=0,
        practice_best=0,
        practice_done=[],
    )
    return redirect('/member/practice')


# Route lives in dang_routes.py so gunicorn wsgi:app also has it.
# Keep a fallback registration if that module was not imported.
if 'member_start_selected' not in base.app.view_functions:
    base.app.add_url_rule(
        '/member/start-selected',
        'member_start_selected',
        _start_selected,
        methods=['GET', 'POST'],
    )

# Keep /member/start compatible with the existing button elsewhere in the app,
# but route it through the exact-selection implementation when qid checkboxes
# are submitted.
_original_start = base.app.view_functions.get('start_practice')

def start_practice_compat():
    if request.form.getlist('qid'):
        return _start_selected()
    if _original_start:
        return _original_start()
    return redirect('/member')

base.app.view_functions['start_practice'] = start_practice_compat
