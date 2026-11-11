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
    lessons = [x for x in idx.get('lessons', []) if isinstance(x, dict) and str(x.get('path') or x.get('file') or '').startswith('ngan-hang/') and base.is_bank_question_tex(str(x.get('path') or x.get('file') or ''))]
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
        who = "<div class='notice'>👁 Chỉ xem đề không cần đăng nhập. Cần <b>VIP</b> (ADMIN cấp gói) để làm bài. <a class='btn primary' href='/member/login'>Đăng nhập</a> <a class='btn' href='/member/register'>Đăng ký</a></div>"
    else:
        typ = _norm_type(m.get('account_type'))
        extra = ''
        if getattr(base, 'has_full_bank_access', lambda *_: False)(m) or typ == 'ADMIN':
            note = '🔐 ADMIN · được xem toàn bộ bài, mọi khối, VIP lẫn FREE'
        else:
            import membership as _pkg
            st = _pkg.package_status(m)
            if st == 'pending':
                note = '⏳ Gói đang chờ ADMIN duyệt · <a href="/member/goi">Xem gói</a>'
            elif st == 'approved':
                note = '🎫 ' + _pkg.scope_label(m) + ' · ' + _pkg.vip_remaining_label(m) + ' · <a href="/member/goi">Đổi gói</a>'
            else:
                note = 'Chưa có gói thành viên · <a href="/member/goi">Chọn gói</a>'
            if getattr(base, 'can_practice', lambda *_: False)(m):
                extra = ' · ✅ Xem đáp án và làm bài'
            else:
                extra = ' · 👁 Chỉ xem đề, chưa VIP'
        who = f"<div class='notice'>👤 <b>{html.escape(str(m.get('name') or m.get('username')))}</b> · Tài khoản <b>{html.escape(str(m.get('username')))}</b> · {note}{extra}</div>"
    is_teacher = bool(m and getattr(base, 'has_full_bank_access', lambda *_: False)(m))
    if is_teacher:
        hero = """
        <section class="student-home-hero teacher-hero">
          <span class="student-eyebrow">KHU VỰC GIÁO VIÊN</span>
          <h1>Quản lý ngân hàng và tạo bài tập</h1>
          <p>Chọn một bài bên dưới hoặc mở công cụ tạo đề từ ảnh và tài liệu.</p>
          <div class="student-home-actions">
            <a class="student-start" href="/admin/html-studio">✨ Tạo câu hỏi từ ảnh / PDF / Word</a>
            <a href="/member/exams/saved">📚 Đề thi đã lưu</a>
          </div>
        </section>"""
    elif m:
        hero = """
        <section class="student-home-hero">
          <span class="student-eyebrow">LỚP HỌC THẦY MINH · HỌC SINH</span>
          <h1>Chọn bài để bắt đầu luyện tập</h1>
          <p>Chọn môn, lớp, chương và bài học. Mỗi bài sẽ có nút Bắt đầu làm bài hoặc trạng thái cần cấp quyền.</p>
          <div class="student-home-actions">
            <a class="student-start" href="#studentLessonList">📘 Chọn bài làm ngay</a>
            <a href="/member/html-menu">🧩 Luyện HTML đổi số</a>
          </div>
        </section>"""
    else:
        hero = """
        <section class="student-home-hero">
          <span class="student-eyebrow">LỚP HỌC THẦY MINH</span>
          <h1>Đăng nhập để chọn bài luyện tập</h1>
          <div class="student-home-actions">
            <a class="student-start" href="/member/login">🔑 Đăng nhập học sinh</a>
          </div>
        </section>"""

    def student_card(x):
        path = str(x.get('path') or x.get('file') or '')
        title = html.escape(str(x.get('BaiHoc') or x.get('De') or 'Bài học'))
        n = int(x.get('questions') or x.get('count') or 0)
        href = html.escape(path, quote=True)
        from urllib.parse import quote
        encoded = quote(path, safe='')
        can_start = bool(m and base.can_practice(m, path) and n > 0)
        if can_start:
            action = (f"<a class='student-start' href='/member/go-kind?path={encoded}'>▶ Bắt đầu làm bài</a>"
                      f"<a class='student-secondary' href='/member/select?path={encoded}'>📋 Xem bài / chọn dạng</a>")
        elif m:
            action = (f"<a class='student-secondary' href='/member/select?path={encoded}'>👁 Xem nội dung bài</a>"
                      "<a class='student-locked' href='/member/goi'>🔒 Cần quyền VIP để làm bài</a>")
        else:
            action = f"<a class='student-start' href='/member/login'>Đăng nhập để làm bài</a>"
        return (f"<article class='student-lesson-card'><div><h3>{title}</h3>"
                f"<p>{n} câu hỏi · {html.escape(str(x.get('Mon') or ''))} · Lớp {html.escape(_grade(x.get('Lop') or x.get('lop')))}</p></div>"
                f"<div class='student-lesson-actions'>{action}</div></article>")

    if not is_teacher:
        student_sections = []
        for (mon, lop, chuong), arr in sorted(groups.items()):
            cards = ''.join(student_card(x) for x in sorted(arr, key=lambda y: str(y.get('BaiHoc') or y.get('De') or '')))
            student_sections.append(
                "<details class='student-chapter' open><summary>"
                + html.escape(str(mon)) + " · Lớp " + html.escape(str(lop))
                + " · " + html.escape(str(chuong))
                + " <span>(" + str(len(arr)) + " bài)</span></summary>"
                + cards + "</details>")
        sections = student_sections

    stylesheet = """
<style>
.student-home-shell{max-width:1200px;margin:0 auto;padding:12px 14px 40px}
.student-home-hero{background:linear-gradient(120deg,#102c51,#1166a5);color:white;border-radius:18px;padding:clamp(18px,4vw,30px);margin-bottom:14px}
.student-home-hero h1{font-size:clamp(23px,4vw,32px);color:#fff;line-height:1.24;margin:9px 0}
.student-home-hero p{color:#e5f1ff;line-height:1.55;margin:0}
.student-eyebrow{font-size:12px;font-weight:800;letter-spacing:.04em;color:#c5e8ff}
.student-home-actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:18px}
.student-home-actions a,.student-lesson-actions a{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 15px;border-radius:10px;text-decoration:none;border:1px solid #c1d4e8;background:#fff;color:#14436f;font-weight:800;box-sizing:border-box;text-align:center}
.student-home-actions .student-start,.student-lesson-actions .student-start{background:#176bd3;color:white;border-color:#176bd3}
.student-home-hero .student-home-actions a:not(.student-start){background:#ffffff18;border-color:#ffffff80;color:#fff}
.student-home-shell .notice{border-radius:10px;padding:11px 13px;margin:0 0 12px;line-height:1.6}
.student-home-shell .catsearch{display:grid;grid-template-columns:minmax(0,1fr) repeat(2,minmax(120px,.35fr)) auto;gap:9px;margin:0}
.student-home-shell .catsearch input,.student-home-shell .catsearch select{min-width:0;width:100%;box-sizing:border-box;min-height:44px}
.student-home-shell .catsearch button{min-height:44px}
.student-list-title{font-size:20px;color:#143958;margin:16px 0 10px}
.student-chapter{border:1px solid #d2e0ee;border-radius:12px;background:#fff;margin:10px 0;overflow:hidden}
.student-chapter>summary{cursor:pointer;padding:14px 16px;background:#eff6ff;color:#164677;font-weight:800;line-height:1.45}
.student-chapter>summary span{font-size:12px;color:#59718b}
.student-lesson-card{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:10px 12px;padding:13px 14px;border:1px solid #dbe6f3;border-radius:11px;background:#fff}
.student-lesson-card h3{font-size:16px;line-height:1.4;color:#173756;margin:0 0 6px}
.student-lesson-card p{font-size:13px;color:#64748b;margin:0}
.student-lesson-actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}
.student-lesson-actions a{font-size:13px;min-height:42px}
.student-lesson-actions .student-locked{color:#885e16;background:#fff6df;border-color:#efd5a0}
@media(max-width:760px){
 .student-home-shell{padding:7px 9px 24px}
 .student-home-hero{padding:18px 15px;margin-bottom:9px}
 .student-home-hero h1{font-size:23px}
 .student-home-actions a{flex:1 1 100%}
 .student-home-shell .catsearch{grid-template-columns:1fr 1fr}
 .student-home-shell .catsearch input{grid-column:1/-1}
 .student-home-shell .catsearch button{grid-column:1/-1}
 .student-lesson-card{display:block;margin:8px;padding:12px}
 .student-lesson-actions{margin-top:12px;justify-content:stretch}
 .student-lesson-actions a{flex:1 1 100%}
 .student-chapter>summary{padding:12px}
}
</style>"""
    from urllib.parse import quote
    form = (
        "<form method='get' class='catsearch' aria-label='Lọc bài học'>"
        "<input name='q' aria-label='Tìm bài học' placeholder='🔎 Tìm bài học, chương, dạng...' value='"
        + html.escape(request.args.get('q',''), quote=True) + "'>"
        "<select name='mon' aria-label='Chọn môn'><option value=''>Tất cả môn</option>"
        + subjopts + "</select>"
        "<select name='lop' aria-label='Chọn lớp'><option value=''>Tất cả lớp</option>"
        + classopts + "</select><button class='btn primary' type='submit'>Tìm bài</button></form>"
    )
    empty = ("<div class='panel'><div class='body'>Không có bài phù hợp hoặc chưa được cấp quyền. "
             "<a href='/member/goi'>Xem gói học tập</a>.</div></div>")
    body = (
        stylesheet
        + "<main class='student-home-shell'>" + hero
        + "<section class='student-lessons' id='studentLessonList'>"
        + "<h2 class='student-list-title'>📚 Bài tập của tôi · " + str(len(items)) + " bài</h2>"
        + who + form + id_block
        + (''.join(sections) if sections else ('' if id_block else empty))
        + "</section></main>"
    )
    return base.page('Mục lục', body)


@app.before_request
def _final_student_index():
    if request.path.rstrip('/') == '/member' and request.method == 'GET':
        return _member_index()
    return None
