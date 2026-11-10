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
    create_access = bool(m and (getattr(base, 'can_manage_bank', lambda *_: False)() or str(m.get('account_type') or '').upper() == 'ADMIN'))
    create_url = '/admin/html-studio' if create_access else '/member/login'
    create_label = 'Mở xưởng tạo câu hỏi AI' if create_access else 'Đăng nhập ADMIN để tạo câu hỏi'
    hero = f"""
<style>
.mc-hero{{background:linear-gradient(120deg,#0b2344,#155487);color:#fff;border-radius:20px;padding:clamp(18px,4vw,34px);margin:14px 0 18px;box-shadow:0 12px 30px #09284224}}
.mc-hero h1{{font-size:clamp(23px,3vw,34px);margin:8px 0;color:#fff;line-height:1.25}}
.mc-hero p{{max-width:740px;color:#e7f1fd;font-size:15px;line-height:1.65}}
.mc-label{{display:inline-block;border:1px solid #ffffff75;background:#ffffff18;border-radius:99px;padding:6px 11px;font-size:12px;font-weight:700}}
.mc-actions{{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}}
.mc-actions a{{display:inline-flex;align-items:center;justify-content:center;min-height:44px;box-sizing:border-box;padding:11px 19px;border-radius:12px;text-decoration:none;font-weight:800;background:#fff;color:#103962}}
.mc-actions a.mc-outline{{border:1px solid #ffffff80;background:#ffffff13;color:#fff}}
.mc-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}}
.mc-tile{{min-width:0;background:#fff;border:1px solid #d5e2f1;border-radius:15px;padding:16px}}
.mc-tile b{{display:block;color:#183856;margin:7px 0;font-size:15px}}.mc-tile small{{font-size:13px;color:#526579;line-height:1.55;display:block}}.mc-tile .ico{{font-size:27px}}
@media(max-width:760px){{.mc-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.mc-actions a{{width:100%}}}}
@media(max-width:360px){{.mc-grid{{grid-template-columns:1fr}}}}
</style>
<section class="mc-hero"><span class="mc-label">LỚP HỌC THẦY MINH · AI QUESTION STUDIO</span>
<h1>Biến ảnh chụp thành bài tập tương tác</h1>
<p>Chụp ảnh đề, tải PDF/Word hoặc dán nội dung. Gemini tạo bài tập có đổi số, đáp án và lời giải; xem trước, thử câu hỏi rồi mới lưu chờ duyệt.</p>
<div class="mc-actions"><a href="{create_url}">✨ {create_label}</a><a class="mc-outline" href="/member/html-menu">📚 Kho bài luyện HTML</a></div>
<small>Không tự ghi đè bài cũ · Chức năng tạo bài chỉ dành cho ADMIN</small>
</section>
<div class="mc-grid" aria-label="Công cụ học tập">
<div class="mc-tile"><span class="ico">📷</span><b>Chụp ảnh đề</b><small>Chụp trực tiếp bằng camera điện thoại và gửi cho AI đọc.</small></div>
<div class="mc-tile"><span class="ico">📄</span><b>Đọc PDF / Word</b><small>Trích câu hỏi, công thức và hình ảnh từ tài liệu.</small></div>
<div class="mc-tile"><span class="ico">✨</span><b>Đổi số thông minh</b><small>Tạo đáp án và lời giải theo dữ liệu bài tập.</small></div>
<div class="mc-tile"><span class="ico">✅</span><b>Xem thử & duyệt</b><small>Thử nghiệm trước khi lưu bài HTML mới.</small></div>
</div>
"""
    body = f"""
{hero}
<div class='wrap><div class='panel'><div class='head'>📚 MỤC LỤC <span class='tag'>{len(items)} bài được phép</span></div><div class='body'>
{who}
<form method='get' class='catsearch'><input name='q' placeholder='Tìm ID câu, bài, chương...' value='{html.escape(request.args.get('q',''))}'><select name='mon'><option value=''>Tất cả môn</option>{subjopts}</select><select name='lop'><option value=''>Tất cả lớp</option>{classopts}</select><button class='btn'>Tìm</button></form>
</div></div>{id_block}{''.join(sections) or ('' if id_block else "<div class='panel' style='margin-top:10px'><div class='body muted'>Chưa có bài trong gói hiện tại. Nếu vừa đăng ký, hãy chờ ADMIN duyệt gói.</div></div>")}</div>
"""
    return base.page('Mục lục', body)


@app.before_request
def _final_student_index():
    if request.path.rstrip('/') == '/member' and request.method == 'GET':
        return _member_index()
    return None
