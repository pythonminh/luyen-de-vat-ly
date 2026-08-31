# -*- coding: utf-8 -*-
from flask import request, redirect, session
from app import app
import dang_routes  # registers /member/dang and makes catalog types clickable


@app.get('/practice/jump/<int:pos>')
def practice_jump(pos):
    """Jump to any question already selected for the current practice session."""
    ids = list(session.get('practice_ids') or [])
    if session.get('role') != 'member' or not ids:
        return redirect('/member/login')
    if pos < 0 or pos >= len(ids):
        return redirect('/member/practice')
    session['practice_pos'] = pos
    return redirect('/member/practice')


@app.after_request
def practice_palette_clickable(response):
    """The old practice page renders palette items as spans; make them clickable."""
    if request.path != '/member/practice' or not response.content_type or 'text/html' not in response.content_type:
        return response
    try:
        text = response.get_data(as_text=True)
        import re
        pat = re.compile(r"<span class='pitem([^']*)'>(\d+) · ([^<]+)</span>")

        def repl(m):
            classes = m.group(1).strip()
            n = int(m.group(2))
            label = m.group(3)
            extra = (' ' + classes) if classes else ''
            return (
                f"<button type='button' class='pitem{extra}' "
                f"onclick='jumpPractice({n-1})'>{n} · {label}</button>"
            )

        new_text = pat.sub(repl, text)
        patch = """
<script>
function jumpPractice(pos){
  window.location.href='/practice/jump/'+pos;
}
</script>
<style>
button.pitem{font:inherit;cursor:pointer}
button.pitem:hover{border-color:#145bb0;box-shadow:0 1px 4px #b9cce2}
</style>
"""
        if new_text != text:
            response.set_data(new_text.replace('</body>', patch + '</body>'))
    except Exception:
        pass
    return response
