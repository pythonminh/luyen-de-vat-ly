"""Verified oscillator templates. Classification is deliberately conservative."""
import base64
import html
import json
import re
import os
import secrets
import sqlite3
import time
from fractions import Fraction

LABELS = {
    'acceleration': 'Gia tốc cực đại từ phương trình li độ',
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
    if 'gia tốc cực đại' in plain:
        m=re.search(r'x\s*=\s*'+NUM+r'\s*\\cos\s*\(\s*'+NUM+r'\s*\\pi\s*t\s*\+\s*(?:\\frac\s*)?\\pi\s*/?\s*(\d+)\s*\)',plain)
        if m: key,nums='acceleration',list(m.groups())
    elif 'quỹ đạo dài' in plain and 'biên độ' in plain and len(nums) == 1:
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

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'dynamic-practice.sqlite3')

def save_exercise(owner, path, exercise):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    token = secrets.token_urlsafe(24)
    with sqlite3.connect(DB_PATH, timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS exercises (token TEXT PRIMARY KEY, owner TEXT, path TEXT, expires REAL, payload TEXT)')
        db.execute('DELETE FROM exercises WHERE expires < ?', (time.time(),))
        db.execute('INSERT INTO exercises VALUES (?,?,?,?,?)', (token, owner, path, time.time()+7200, json.dumps(exercise, ensure_ascii=False)))
    return token

def load_exercise(token, owner):
    if not isinstance(token, str) or len(token)>100 or not owner:
        return None
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as db:
            row = db.execute('SELECT path,payload FROM exercises WHERE token=? AND owner=? AND expires>?', (token,owner,time.time())).fetchone()
        return (row[0], json.loads(row[1])) if row else None
    except sqlite3.OperationalError:
        return None

def public_exercise(exercise):
    return {k:v for k,v in exercise.items() if k not in {'answer','solution','options'}} | {'options':[{'text':o['text']} for o in exercise.get('options',[])]}

def lesson_questions(path, dang):
    from app import parse_lesson_questions, read_tex, parse_questions, nest_developments
    from dang_routes import _same_dang
    qs=parse_lesson_questions(path)
    if not qs:
        _,tex=read_tex(path)
        qs=nest_developments(parse_questions(tex))
    return [q for q in qs if _same_dang(q.get('dang'),dang)] if dang else qs

def register(app):
    from flask import request, redirect, jsonify, session

    @app.get('/api/dynamic-practice/code')
    def dynamic_code():
        from app import can_manage_bank
        if not can_manage_bank(): return jsonify(ok=False,error='Chỉ ADMIN được xem mã Python.'),403
        from pathlib import Path
        return jsonify(ok=True,code=Path(__file__).with_name('dynamic_engine.py').read_text(encoding='utf-8'))
    from dynamic_engine import SPECS, generate, solve, fraction

    @app.post('/api/dynamic-practice/new')
    def dynamic_new():
        from app import member_current, can_practice, can_manage_bank, question_payload
        m=member_current()
        body=request.get_json(silent=True) or {}
        if not isinstance(body,dict): return jsonify(ok=False,error='Yêu cầu không hợp lệ.'),400
        path=body.get('path','')
        if not m: return jsonify(ok=False,error='Cần đăng nhập.'),401
        if not isinstance(path,str) or not path or not can_practice(m,path): return jsonify(ok=False,error='Không có quyền luyện bài này.'),403
        try:
            groups=groups_for(lesson_questions(path,str(body.get('dang',''))))
            gi,si=body.get('group',0),body.get('source',0)
            if type(gi) is not int or type(si) is not int or gi<0 or si<0: raise ValueError('Chọn mẫu và câu gốc hợp lệ.')
            item=groups[gi]['items'][si]
            key=item['template']
            original=body.get('original') is True
            bounds=body.get('bounds')
            if bounds and not can_manage_bank(): return jsonify(ok=False,error='Chỉ giáo viên quản lý được cấu hình khoảng số.'),403
            previous=load_exercise(body.get('previous_token'),session.get('dp_owner'))
            last=previous[1]['params'] if previous and previous[0]==path and previous[1].get('template')==key else item['params']
            params=item['params'] if original else generate(key,bounds,last)
            exercise=solve(key,params)
            q=item['original']
            if original:
                exercise.update(text=q['text'],solution=q['solution'],html=True)
                exercise['options']=q.get('options',[])
                exercise['answer']=q.get('answer',exercise['answer'])
            if q['kind']=='TLN': exercise['options']=[]
            exercise.update(kind=q['kind'],source_id=q.get('id',''),file_idx=q['file_idx'],template=key)
            owner=session.get('dp_owner') or secrets.token_urlsafe(24)
            session['dp_owner']=owner
            token=save_exercise(owner,path,exercise)
            return jsonify(ok=True,token=token,exercise=public_exercise(exercise))
        except (ValueError,IndexError,KeyError,TypeError,ZeroDivisionError):
            return jsonify(ok=False,error='Mẫu, câu gốc hoặc khoảng số không hợp lệ.'),400

    def authorized_exercise():
        from app import member_current, can_practice
        m=member_current()
        if not m: return None
        body=request.get_json(silent=True) or {}
        if not isinstance(body,dict): return None
        found=load_exercise(body.get('token'),session.get('dp_owner'))
        return found[1] if found and can_practice(m,found[0]) else None

    @app.post('/api/dynamic-practice/check')
    def dynamic_check():
        exercise=authorized_exercise()
        if not exercise: return jsonify(ok=False,error='Đề đã hết hạn hoặc không có quyền. Hãy mở lại đề.'),403
        body=request.get_json(silent=True) or {}
        options=exercise.get('options',[])
        if options:
            idx=body.get('choice')
            if type(idx) is not int or not 0<=idx<len(options): return jsonify(ok=False,error='Hãy chọn một phương án.'),400
            correct=bool(options[idx].get('correct'))
        else:
            try:
                if len(str(body.get('answer','')))>100: raise ValueError()
                correct=fraction(body.get('answer',''))==fraction(exercise['answer'])
            except (ValueError,ZeroDivisionError): return jsonify(ok=False,error='Nhập số hoặc phân số chính xác.'),400
        return jsonify(ok=True,correct=correct)

    @app.post('/api/dynamic-practice/solution')
    def dynamic_solution():
        exercise=authorized_exercise()
        if not exercise: return jsonify(ok=False,error='Đề đã hết hạn hoặc không có quyền.'),403
        return jsonify(ok=True,solution=exercise['solution'],html=exercise['html'])

    @app.get('/member/dynamic-practice')
    def dynamic_practice():
        from app import member_current, can_practice, can_manage_bank, login_url, page, dang_view_url
        path = request.args.get('path', '')
        dang = request.args.get('dang', '')
        m = member_current()
        if not m:
            return redirect(login_url(request.full_path))
        if not path or not can_practice(m, path):
            return redirect('/member')
        groups = groups_for(lesson_questions(path,dang))
        if not groups:
            return page('Bài động', '<p>Chưa có mẫu tính toán đã kiểm chứng cho các câu này.</p>')
        safe_groups=[{'key':g['key'],'label':g['label'],'specs':SPECS[g['key']], 'items':[{'id':i['original']['id'],'file_idx':i['original']['file_idx']} for i in g['items']]} for g in groups]
        initial=(0,0)
        wanted_src=request.args.get('src','')
        wanted_idx=request.args.get('file_idx','')
        for gi,g in enumerate(groups):
            for si,i in enumerate(g['items']):
                if i['original']['src']==wanted_src and str(i['original']['file_idx'])==wanted_idx: initial=(gi,si)
        packed = base64.b64encode(json.dumps({'initial':initial,'show_code':request.args.get('show_code')=='1','groups':safe_groups,'path':path,'dang':dang,'can_configure':can_manage_bank()}, ensure_ascii=False).encode()).decode()
        inner = '<section id="dynamicPractice"><header class="dp-brand">Lớp Học Thầy Minh · Zalo 0946111107<small>lophocthayminh.onrender.com</small></header>\n<div class="dp-controls"><a class="btn" href="BACK">← Về dạng bài</a><select id="dpGroup" aria-label="Mẫu bài"></select><select id="dpSource" aria-label="Câu gốc"></select><button type="button" id="dpNew">Đổi đề bài mới</button><button type="button" id="dpOriginal">Về đề gốc</button><button type="button" id="dpFull">⛶ Toàn màn hình</button></div>\n<button type="button" id="dpConfigure" hidden>⚙ Cấu hình hàm Python</button><dialog id="dpConfig"><form method="dialog"><h3>Cấu hình sinh số</h3><p id="dpConfigName"></p><div id="dpBounds"></div><p>Các giá trị là số nguyên. Đề, đáp án và lời giải được Python tính đồng bộ. Cấu hình áp dụng trong lượt luyện hiện tại.</p><p id="dpConfigError" role="status"></p><button type="button" id="dpApply">Áp dụng và thử đổi đề</button><button type="submit">Đóng</button></form></dialog><button type="button" id="dpCodeButton" hidden>🐍 Xem hàm Python</button><dialog id="dpCodeDialog"><form method="dialog"><h3>Mã Python đang dùng để sinh và tính bài</h3><p>Các mẫu dùng chung hàm generate và solve; chọn nhánh theo tên mẫu.</p><pre id="dpCodeText"></pre><button type="submit">Đóng</button></form></dialog><p id="dpMeta"></p><div class="dp-grid"><article><h3>1. Đề bài</h3><div id="dpStem"></div><div id="dpOptions"></div><label id="dpInputLabel">Nhập kết quả chính xác (có thể nhập phân số)<input id="dpInput" autocomplete="off"></label><button type="button" id="dpCheck">Kiểm tra</button><p id="dpFeedback" role="status" aria-live="polite"></p></article>\n<article><h3>2. Công thức và kiến thức</h3><div id="dpFormula"></div></article><article><h3>3. Minh họa động</h3><div id="dpFigure"></div><button type="button" id="dpAnimate">▶ Chạy / Dừng</button></article><article><h3>4. Hướng dẫn và lời giải</h3><button type="button" id="dpReveal">Xem lời giải</button><div id="dpSolution" hidden></div></article></div></section>\n<link rel="stylesheet" href="/static/dynamic-practice.css"><script id="dpData" type="application/json">PACKED</script><script src="/static/dynamic-practice.js"></script>'
        return page('Luyện bài động', inner.replace('BACK', html.escape(dang_view_url(path, dang), quote=True)).replace('PACKED', packed))
