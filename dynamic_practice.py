"""Verified oscillator templates. Classification is deliberately conservative."""
import base64
import html
import json
import re
from fractions import Fraction

LABELS = {
    'amplitude': 'Biên độ từ chiều dài quỹ đạo',
    'projection': 'Hình chiếu chuyển động tròn đều',
    'period': 'Chu kì từ số dao động',
    'orbit': 'Quỹ đạo từ tổng quãng đường',
    'distance': 'Quãng đường trong số nguyên nửa chu kì',
    'rotation': 'Chu kì và tần số của bóng trên màn',
    'spring': 'Độ cứng lò xo từ số dao động',
}
NUM = r'(\d+(?:[.,]\d+)?)'

def classify(q):
    if q.get('kind') not in {'TN', 'TLN'}:
        return None
    # Match the stem only, never numbers in options or solution.
    t = re.sub(r'%[^\n]*', '', q.get('text') or '')
    plain = re.sub(r'\\(?:mathrm|text)\{([^{}]*)\}', r'\1', t)
    plain = re.sub(r'\\[,;!]|[$~{}]', '', plain).lower()
    nums = re.findall(NUM, plain)
    key = None
    if 'quỹ đạo dài' in plain and 'biên độ' in plain and len(nums) == 1:
        key = 'amplitude'
    elif 'bán kính' in plain and 'biên độ và tần số góc' in plain and len(nums) == 2 and '\\pi' not in plain:
        key = 'projection'
    elif 'phút' in plain and 'dao động toàn phần' in plain and 'chu kì' in plain and len(nums) == 2:
        key = 'period'
    elif 'tổng quãng đường' in plain and 'chiều dài quỹ đạo' in plain and len(nums) == 2:
        key = 'orbit'
    elif 'bàn xoay' in plain and 'chu kì và tần số' in plain and len(nums) == 2 and '\\pi' in plain:
        key = 'rotation'
    elif 'con lắc lò xo' in plain and 'độ cứng' in plain and len(nums) == 5 and nums[-2:] == ['2', '10']:
        key = 'spring'
        nums = nums[:3]
    elif 'quãng đường' in plain and 'kể từ thời điểm ban đầu' in plain:
        # Only this verified cos form, with an integer number of half-periods.
        m = re.search(r'x\s*=\s*'+NUM+r'\s*\\cos\s*\(\s*'+NUM+r'\s*\\pi\s*t\s*\+\s*\\pi\s*/\s*(\d+)\s*\)', plain)
        end = re.search(r't\s*=\s*'+NUM+r'\s*s', plain)
        if m and end:
            a, w, phase = m.groups()
            dt = end.group(1)
            h = Fraction(w.replace(',', '.')) * Fraction(dt.replace(',', '.'))
            if h.denominator == 1 and h > 0:
                key, nums = 'distance', [a, w, phase, dt]
    if not key or any(Fraction(n.replace(',', '.')) <= 0 for n in nums):
        return None
    return {'template': key, 'params': [n.replace(',', '.') for n in nums]}

def groups_for(qs):
    from app import question_payload
    groups = {}
    for q in qs:
        spec = classify(q)
        if spec:
            key = spec['template']
            groups.setdefault(key, {'key': key, 'label': LABELS[key], 'items': []})['items'].append({**spec, 'original': question_payload(q)})
    return list(groups.values())

def launcher(qs, path, dang, allowed):
    count = sum(classify(q) is not None for q in qs)
    if not count or not allowed:
        return ''
    from urllib.parse import urlencode
    url = '/member/dynamic-practice?' + urlencode({'path': path, 'dang': dang})
    return '<div class="notice"><a class="btn primary" href="'+html.escape(url, quote=True)+'">🎲 Luyện bài động · gom mẫu tương tự</a> Đổi số tức thì, không cần gọi AI.</div>'

def register(app):
    from flask import request, redirect
    @app.get('/member/dynamic-practice')
    def dynamic_practice():
        from app import member_current, can_practice, login_url, parse_lesson_questions, read_tex, parse_questions, nest_developments, page, dang_view_url
        from dang_routes import _same_dang
        path = request.args.get('path', '')
        dang = request.args.get('dang', '')
        m = member_current()
        if not m:
            return redirect(login_url(request.full_path))
        if not path or not can_practice(m, path):
            return redirect('/member')
        qs = parse_lesson_questions(path)
        if not qs:
            _, tex = read_tex(path)
            qs = nest_developments(parse_questions(tex))
        if dang:
            qs = [q for q in qs if _same_dang(q.get('dang'), dang)]
        groups = groups_for(qs)
        if not groups:
            return page('Bài động', '<p>Chưa có mẫu tính toán đã kiểm chứng cho các câu này.</p>')
        packed = base64.b64encode(json.dumps(groups, ensure_ascii=False).encode()).decode()
        inner = '''<section id="dynamicPractice"><header class="dp-brand">Lớp Học Thầy Minh · Zalo 0946111107<small>lophocthayminh.onrender.com</small></header>
<div class="dp-controls"><a class="btn" href="BACK">← Về dạng bài</a><select id="dpGroup" aria-label="Mẫu bài"></select><select id="dpSource" aria-label="Câu gốc"></select><button type="button" id="dpNew">Đổi đề bài mới</button><button type="button" id="dpOriginal">Về đề gốc</button><button type="button" id="dpFull">⛶ Toàn màn hình</button></div>
<p id="dpMeta"></p><div class="dp-grid"><article><h3>1. Đề bài</h3><div id="dpStem"></div><div id="dpOptions"></div><label id="dpInputLabel">Nhập kết quả chính xác (có thể nhập phân số)<input id="dpInput" autocomplete="off"></label><button type="button" id="dpCheck">Kiểm tra</button><p id="dpFeedback" role="status" aria-live="polite"></p></article>
<article><h3>2. Công thức và kiến thức</h3><div id="dpFormula"></div></article><article><h3>3. Minh họa động</h3><div id="dpFigure"></div><button type="button" id="dpAnimate">▶ Chạy / Dừng</button></article><article><h3>4. Hướng dẫn và lời giải</h3><button type="button" id="dpReveal">Xem lời giải</button><div id="dpSolution" hidden></div></article></div></section>
<link rel="stylesheet" href="/static/dynamic-practice.css"><script id="dpData" type="application/json">PACKED</script><script src="/static/dynamic-practice.js"></script>'''
        return page('Luyện bài động', inner.replace('BACK', html.escape(dang_view_url(path, dang), quote=True)).replace('PACKED', packed))
