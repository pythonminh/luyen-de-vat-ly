# -*- coding: utf-8 -*-
"""Show the actual questions on /member/dang without changing the quiz engine."""
from __future__ import annotations

import html
import json
import random

from flask import request, redirect
from app import app, member_current, can_access, read_tex, parse_questions, page


def _question_card(q):
    idx = int(q.get('idx', 0))
    kind = str(q.get('kind') or 'TL')
    level = str(q.get('level') or 'H')
    text = str(q.get('text') or '').strip()
    bits = [
        "<div class='question-card' data-qid='%d' data-kind='%s' data-level='%s'>" % (idx, html.escape(kind), html.escape(level)),
        "<div class='question-head'><label><input class='qpick' type='checkbox' name='qid' value='%d'> <b>Câu %d</b></label>" % (idx, idx + 1),
        "<span class='qbadge'>%s</span><span class='qbadge'>%s</span></div>" % (html.escape(kind), html.escape(level)),
        "<div class='question-text'>%s</div>" % text,
    ]
    if kind == 'TN':
        opts = q.get('options') or []
        letters = 'ABCD'
        for i, opt in enumerate(opts[:4]):
            if isinstance(opt, dict):
                ot = str(opt.get('text') or '')
            else:
                ot = str(opt)
            bits.append("<div class='option'><b>%s.</b> %s</div>" % (letters[i], ot))
    elif kind == 'DS':
        sts = q.get('statements') or []
        for i, st in enumerate(sts, 1):
            stt = str(st.get('text') if isinstance(st, dict) else st)
            bits.append("<div class='option'><b>%d)</b> %s</div>" % (i, stt))
    bits.append("</div>")
    return ''.join(bits)


@app.post('/member/start-selected')
def start_selected_questions():
    m = member_current()
    if not m:
        return redirect('/member/login')
    path = request.form.get('path', '').strip()
    if not path or not can_access(m, path):
        return redirect('/member')
    try:
        _, tex = read_tex(path)
        qs = parse_questions(tex)
    except Exception:
        return redirect('/member')
    valid = {str(q.get('idx')): q for q in qs}
    ids = []
    for raw in request.form.getlist('qid'):
        if raw in valid and int(raw) not in ids:
            ids.append(int(raw))
    if not ids:
        return redirect('/member/dang?path=' + __import__('urllib.parse').parse.quote(path, safe='') + '&dang=' + __import__('urllib.parse').parse.quote(request.form.get('dang',''), safe=''))
    random.shuffle(ids)
    from flask import session
    session.update(practice_path=path, practice_ids=ids, practice_pos=0, practice_right=0, practice_streak=0, practice_best=0, practice_done=[])
    return redirect('/member/practice')


@app.after_request
def inject_question_preview(response):
    if request.path != '/member/dang' or 'text/html' not in response.headers.get('Content-Type', ''):
        return response
    try:
        m = member_current()
        path = request.args.get('path', '').strip()
        dang = request.args.get('dang', '').strip()
        if not m or not path or not dang or not can_access(m, path):
            return response
        _, tex = read_tex(path)
        selected = [q for q in parse_questions(tex) if str(q.get('dang') or '') == dang]
        if not selected:
            return response
        cards = ''.join(_question_card(q) for q in selected)
        panel = """
<div class='question-preview panel'>
  <div class='head'>📝 Câu hỏi trong dạng này <span class='tag'>%d câu</span></div>
  <div class='body'>
    <div class='question-tools'>
      <button type='button' class='btn' id='pickAllQ'>☑ Chọn tất cả</button>
      <button type='button' class='btn' id='clearQ'>Bỏ chọn</button>
      <span id='pickCount' class='notice'>Đã chọn: 0 câu</span>
    </div>
    <form id='selectedQuestionForm' method='post' action='/member/start-selected'>
      <input type='hidden' name='path' value='%s'>
      <input type='hidden' name='dang' value='%s'>
      %s
      <button class='btn primary' type='submit'>▶ Làm các câu đã chọn</button>
    </form>
  </div>
</div>
<style>
.question-preview{margin-top:12px}.question-tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.question-card{border:1px solid #d7e3ee;border-radius:10px;padding:12px;margin:9px 0;background:#fff}.question-card.selected{border-color:#1976d2;box-shadow:0 0 0 2px #e5f0ff}
.question-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.question-head label{cursor:pointer}.qbadge{font-size:11px;border:1px solid #c8d9e9;border-radius:999px;padding:3px 8px;color:#145bb0;background:#f8fbff}.question-text{margin:9px 0;line-height:1.55}.option{margin:4px 0 4px 22px;line-height:1.5}
.qpick{transform:scale(1.15);margin-right:5px}.question-card .qpick:checked + b{color:#176bd3}
</style>
<script>
(function(){
 const form=document.getElementById('selectedQuestionForm'); if(!form)return;
 const boxes=[...form.querySelectorAll('.qpick')], count=document.getElementById('pickCount');
 function upd(){let n=boxes.filter(x=>x.checked).length;count.textContent='Đã chọn: '+n+' câu';boxes.forEach(x=>x.closest('.question-card').classList.toggle('selected',x.checked));}
 boxes.forEach(x=>x.addEventListener('change',upd));
 document.getElementById('pickAllQ').onclick=()=>{boxes.forEach(x=>x.checked=true);upd()};
 document.getElementById('clearQ').onclick=()=>{boxes.forEach(x=>x.checked=false);upd()};
 form.addEventListener('submit',e=>{if(!boxes.some(x=>x.checked)){e.preventDefault();alert('Hãy chọn ít nhất một câu.')}}); upd();
 if(window.MathJax && window.MathJax.typesetPromise) window.MathJax.typesetPromise();
})();
</script>
""" % (len(selected), html.escape(path, quote=True), html.escape(dang, quote=True), cards)
        body = response.get_data(as_text=True)
        marker = "<form method='post' action='/member/start'>"
        if marker in body:
            body = body.replace(marker, panel + marker, 1)
            response.set_data(body)
    except Exception:
        pass
    return response
