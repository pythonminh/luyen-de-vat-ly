# -*- coding: utf-8 -*-
"""Allow /member/dang to submit exact question ids via checkboxes."""
from __future__ import annotations
import urllib.parse, random
from flask import request, redirect, session
import app as base


def start_practice_exact():
    m=base.member_current()
    if not m:return redirect('/member/login')
    p=request.form.get('path','').strip()
    if not p or not base.can_access(m,p):return redirect('/member')
    try:
        _,tex=base.read_tex(p); qs=base.parse_questions(tex)
    except Exception:
        return redirect('/member')
    valid={int(q.get('idx')) for q in qs if str(q.get('idx','')).isdigit() and (q.get('dang') or '')==request.args.get('dang','')}
    raw=request.form.getlist('qid')
    ids=[]
    for x in raw:
        try:
            i=int(x)
            if i in valid: ids.append(i)
        except Exception: pass
    # Fallback: accept valid ids from the submitted page even if dang query is absent.
    if not ids:
        all_valid={int(q.get('idx')) for q in qs if str(q.get('idx','')).isdigit()}
        for x in raw:
            try:
                i=int(x)
                if i in all_valid: ids.append(i)
            except Exception: pass
    ids=list(dict.fromkeys(ids))
    if not ids:return redirect('/member/dang?path='+urllib.parse.quote(p,safe='')+'&dang='+urllib.parse.quote(request.args.get('dang',''),safe=''))
    random.shuffle(ids)
    session.update(practice_path=p,practice_ids=ids,practice_pos=0,practice_right=0,practice_streak=0,practice_best=0,practice_done=[])
    return redirect('/member/practice')

# Replace only the selection/start handler; all authentication and practice code remains unchanged.
base.app.view_functions['start_practice']=start_practice_exact
