# -*- coding: utf-8 -*-
"""Navigation helpers for the one-question practice screen."""
from __future__ import annotations

from flask import request, redirect

from app import app, member_current


@app.get('/member/practice/jump')
def practice_jump():
    """Jump to any question already selected for the current practice session."""
    m = member_current()
    if not m:
        return redirect('/member/login')
    ids = list(__import__('flask').session.get('practice_ids') or [])
    if not ids:
        return redirect('/member')
    try:
        pos = int(request.args.get('pos', '0'))
    except Exception:
        pos = 0
    pos = max(0, min(pos, len(ids) - 1))
    __import__('flask').session['practice_pos'] = pos
    return redirect('/member/practice')


@app.after_request
def make_practice_palette_clickable(response):
    """Turn practice question palette items into real navigation buttons."""
    if request.path != '/member/practice' or 'text/html' not in response.headers.get('Content-Type', ''):
        return response
    try:
        body = response.get_data(as_text=True)
        if "class='pitem" not in body:
            return response
        script = r'''<script>
document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.palette .pitem').forEach(function(el, idx){
    if (el.closest('a')) return;
    const a = document.createElement('a');
    a.href = '/member/practice/jump?pos=' + idx;
    a.className = el.className;
    a.textContent = el.textContent;
    a.style.textDecoration = 'none';
    a.style.color = 'inherit';
    a.style.cursor = 'pointer';
    el.replaceWith(a);
  });
});
</script>'''
        response.set_data(body.replace('</body>', script + '</body>'))
    except Exception:
        pass
    return response
