# -*- coding: utf-8 -*-
"""Final student index: only show lessons the current member can access."""
from __future__ import annotations

import html
from urllib.parse import quote

import app as base
from flask import redirect, request, session
from admin_overrides import _can_member_see, _grade, _norm_type

app = base.app


def _member_index():
    m = base.member_current()
    if not m:
        return redirect('/member/login')
    idx = base.index_data()
    items = [x for x in idx.get('lessons', []) if isinstance(x, dict) and str(x.get('path') or x.get('file') or '').startswith('ngan-hang/') and _can_member_see(m, x)]
    q = str(request.args.get('q') or '').strip().lower()
    sm = str(request.args.get('mon') or '')
    cl = str(request.args.get('lop') or '')
    if q:
        items = [x for x in items if q in ' '.join(str(x.get(k) or '') for k in ('Mon','Lop','Chuong','BaiHoc','De','dang','path')).lower()]
    if sm:
        items = [x for x in items if str(x.get('Mon') or '') == sm]
    if cl:
        items = [x for x in items if _grade(x.get('Lop') or x.get('lop')) == _grade(cl)]

    subjects = sorted({str(x.get('Mon') or '') for x in items if x.get('Mon')})
    classes = sorted({_grade(x.get('Lop') or x.get('lop')) for x in items if _grade(x.get('Lop') or x.get('lop'))})
    groups = {}
    for x in items:
        key = (str(x.get('Mon') or ''), _grade(x.get('Lop') or x.get('lop')), str(x.get('Chuong') or ''))
        groups.setdefault(key, []).append(x)

    sections = []
    for (mon, lop, chuong), arr in groups.items():
        cards = []
        for x in arr:
            path = str(x.get('path') or x.get('file') or '')
            title = str(x.get('BaiHoc') or x.get('De') or path.rsplit('/', 1)[-1])
            level = str(base.lesson_level(path)).upper()
            cnt = int(x.get('questions') or x.get('count') or 0)
            dangs = x.get('dang') or {}
            dh = ''.join(f"<div class='dangrow'><span>{html.escape(str(k))}</span><span class='tag'>{int(v)} câu</span></div>" for k,v in dangs.items() if str(v).isdigit())
            href = quote(path, safe='')
            cards.append(f"<div class='card'><b>{html.escape(title)}</b><div class='meta'>{html.escape(mon)} · Lớp {html.escape(lop)} · {html.escape(chuong)}</div><div><span class='tag {'vip' if level=='VIP' else 'free'}'>{html.escape(level)}</span><span class='tag'>{cnt} câu</span></div><div class='dang'><b>📌 Dạng bài</b>{dh or '<div class=muted>Xem trực tiếp từ TEX khi mở bài</div>'}</div><a class='btn primary' href='/member/select?path={href}'>Mở bài</a></div>")
        sections.append(f"<section style='margin-top:10px'><div class='titlebar'>{html.escape(mon)} · Lớp {html.escape(lop)} · {html.escape(chuong)}</div><div class='cards' style='margin-top:8px'>{''.join(cards)}</div></section>")

    subjopts = ''.join(f"<option value='{html.escape(s, quote=True)}' {'selected' if sm==s else ''}>{html.escape(s)}</option>" for s in subjects)
    classopts = ''.join(f"<option value='{html.escape(c, quote=True)}' {'selected' if _grade(cl)==c else ''}>{html.escape(c)}</option>" for c in classes)
    grade = _grade(m.get('class')) or 'Chưa cấp'
    typ = _norm_type(m.get('account_type'))
    note = '⭐ SVIP · được xem toàn bộ khối 10, 11, 12' if typ == 'SVIP' else f'🎓 Lớp {grade} · chỉ hiển thị bài đúng khối được cấp'
    body = f"""
<div class='wrap'><div class='panel'><div class='head'>📚 MỤC LỤC <span class='tag'>{len(items)} bài được phép</span></div><div class='body'>
<div class='notice'>👤 <b>{html.escape(str(m.get('name') or m.get('username')))}</b> · Tài khoản <b>{html.escape(str(m.get('username')))}</b> · Quyền <b>{html.escape(typ)}</b> · {html.escape(note)}</div>
<form method='get' style='display:grid;grid-template-columns:1fr 180px 160px auto;gap:7px;margin-top:10px'><input name='q' placeholder='Tìm bài, chương, dạng...' value='{html.escape(request.args.get('q',''))}'><select name='mon'><option value=''>Tất cả môn</option>{subjopts}</select><select name='lop'><option value=''>Tất cả lớp</option>{classopts}</select><button class='btn'>Tìm</button></form>
</div></div>{''.join(sections) or "<div class='panel' style='margin-top:10px'><div class='body muted'>Chưa có bài phù hợp với quyền hiện tại.</div></div>"}</div>
"""
    return base.page('Mục lục', body)


@app.before_request
def _final_student_index():
    if request.path.rstrip('/') == '/member' and request.method == 'GET':
        return _member_index()
    return None
