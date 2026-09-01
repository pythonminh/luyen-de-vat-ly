# -*- coding: utf-8 -*-
"""Final student index: only show lessons the current member can access."""
from __future__ import annotations

import html

import app as base
from flask import redirect, request, session
from admin_overrides import _can_member_see, _grade, _norm_type

app = base.app


def _member_index():
    m = base.member_current()
    idx = base.index_data()
    lessons = [x for x in idx.get('lessons', []) if isinstance(x, dict) and str(x.get('path') or x.get('file') or '').startswith('ngan-hang/')]
    if not m:
        items = [x for x in lessons if str(base.lesson_level(str(x.get('path') or x.get('file') or ''))).upper() != 'VIP']
    elif getattr(base, 'has_full_bank_access', lambda *_: False)(m):
        items = lessons
    else:
        items = [x for x in lessons if _can_member_see(m, x)]
    q = str(request.args.get('q') or '').strip().lower()
    sm = str(request.args.get('mon') or '')
    cl = str(request.args.get('lop') or '')
    id_block = ''
    if q:
        import dang_routes as dr
        id_block = dr.qid_results_html(q, m)
    if sm:
        items = [x for x in items if str(x.get('Mon') or '') == sm]
    if cl:
        items = [x for x in items if _grade(x.get('Lop') or x.get('lop')) == _grade(cl)]
    items = base.merge_catalog_lessons(items)
    if q:
        def _hit(x):
            dang = x.get('dang') or {}
            blob = ' '.join(
                [str(x.get(k) or '') for k in ('Mon', 'Lop', 'Chuong', 'BaiHoc', 'De', 'path')]
                + [str(k) for k in dang]
            ).lower()
            return q in blob
        items = [x for x in items if _hit(x)]

    subjects = sorted({str(x.get('Mon') or '') for x in items if x.get('Mon')})
    classes = sorted({_grade(x.get('Lop') or x.get('lop')) for x in items if _grade(x.get('Lop') or x.get('lop'))})
    groups = {}
    for x in items:
        key = (str(x.get('Mon') or ''), _grade(x.get('Lop') or x.get('lop')), str(x.get('Chuong') or ''))
        groups.setdefault(key, []).append(x)

    sections = []
    for (mon, lop, chuong), arr in sorted(groups.items()):
        sections.append(base.catalog_chapter_html(mon, lop, chuong, arr))

    subjopts = ''.join(f"<option value='{html.escape(s, quote=True)}' {'selected' if sm==s else ''}>{html.escape(s)}</option>" for s in subjects)
    classopts = ''.join(f"<option value='{html.escape(c, quote=True)}' {'selected' if _grade(cl)==c else ''}>{html.escape(c)}</option>" for c in classes)
    if not m:
        note = '👁 Xem đề không cần đăng nhập · Đăng nhập để làm bài và dùng Gemini phản biện'
        who = f"<div class='notice'>{html.escape(note)} · <a class='btn primary' href='/member/login'>Đăng nhập</a> <a class='btn' href='/member/register'>Đăng ký</a></div>"
    else:
        grade = _grade(m.get('class')) or 'Chưa cấp'
        typ = _norm_type(m.get('account_type'))
        if getattr(base, 'has_full_bank_access', lambda *_: False)(m) or typ == 'ADMIN':
            note = '🔐 ADMIN · được xem toàn bộ bài, mọi khối, VIP lẫn FREE'
        elif typ == 'SVIP':
            note = '⭐ SVIP · được xem toàn bộ khối 10, 11, 12'
        else:
            note = f'🎓 Lớp {grade} · chỉ hiển thị bài đúng khối được cấp'
        who = f"<div class='notice'>👤 <b>{html.escape(str(m.get('name') or m.get('username')))}</b> · Tài khoản <b>{html.escape(str(m.get('username')))}</b> · Quyền <b>{html.escape(typ)}</b> · {html.escape(note)}</div>"
    body = f"""
<div class='wrap'><div class='panel'><div class='head'>📚 MỤC LỤC <span class='tag'>{len(items)} bài được phép</span></div><div class='body'>
{who}
<form method='get' style='display:grid;grid-template-columns:1fr 180px 160px auto;gap:7px;margin-top:10px'><input name='q' placeholder='Tìm ID câu, bài, chương...' value='{html.escape(request.args.get('q',''))}'><select name='mon'><option value=''>Tất cả môn</option>{subjopts}</select><select name='lop'><option value=''>Tất cả lớp</option>{classopts}</select><button class='btn'>Tìm</button></form>
</div></div>{id_block}{''.join(sections) or ('' if id_block else "<div class='panel' style='margin-top:10px'><div class='body muted'>Chưa có bài phù hợp. Tài khoản FREE xem bài Free; VIP xem theo lớp (nếu chưa ghi lớp thì xem hết).</div></div>")}</div>
"""
    return base.page('Mục lục', body)


@app.before_request
def _final_student_index():
    if request.path.rstrip('/') == '/member' and request.method == 'GET':
        return _member_index()
    return None
