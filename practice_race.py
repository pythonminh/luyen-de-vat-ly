"""Timed, server-graded practice rooms with numeric or bank question sets."""
import race_variants as variants
import copy
import hashlib
import html
import io
import json
import os
import random
import re
import secrets
import sqlite3
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
import segno

from flask import Response, abort, jsonify, redirect, request, session
import app as base

DB_PATH = Path(os.environ.get('PRACTICE_RACE_DB', str(base.ROOT / 'data' / 'practice-race.sqlite3')))
RNG = random.SystemRandom()


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH), timeout=20)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    c.executescript('''CREATE TABLE IF NOT EXISTS race_rooms (
      code TEXT PRIMARY KEY, owner TEXT NOT NULL, title TEXT NOT NULL,
      path TEXT NOT NULL, pool TEXT NOT NULL, blueprint TEXT NOT NULL,
      duration INTEGER NOT NULL, state TEXT NOT NULL, created REAL NOT NULL,
      started REAL, shown INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS race_players (
      room TEXT NOT NULL, user TEXT NOT NULL, name TEXT NOT NULL,
      questions TEXT NOT NULL, answers TEXT NOT NULL DEFAULT '{}',
      started REAL, finished REAL, correct INTEGER, elapsed REAL,
      PRIMARY KEY(room,user));
    CREATE TABLE IF NOT EXISTS race_marks (
      room TEXT NOT NULL, user TEXT NOT NULL, pos INTEGER NOT NULL, ok INTEGER NOT NULL,
      PRIMARY KEY(room,user,pos));
    CREATE TABLE IF NOT EXISTS race_meta(room TEXT PRIMARY KEY, config TEXT NOT NULL);''')
    try:
        with c:
            yield c
    finally:
        c.close()


def who():
    m = base.member_current()
    if m:
        return m, str(m.get('username') or '').strip().casefold()
    if not session.get('race_guest'):
        session['race_guest'] = secrets.token_urlsafe(24)
    return {}, 'guest:' + session['race_guest']


def csrf():
    if not session.get('race_csrf'):
        session['race_csrf'] = secrets.token_urlsafe(24)
    return session['race_csrf']


def check_csrf():
    value = request.headers.get('X-Race-CSRF', '') or request.form.get('csrf', '') or request.form.get('race_pick_csrf', '')
    if not value or not secrets.compare_digest(value, session.get('race_csrf', '')):
        abort(403)


def room(c, code):
    r = c.execute('SELECT * FROM race_rooms WHERE code=?', (code,)).fetchone()
    if not r:
        abort(404)
    return r


def is_host(r, user):
    return base.can_manage_bank() and r['owner'] == user


def fingerprint(q):
    # Exclude IDs, answer order and metadata: repeated copies of a question are one item.
    value = str(q.get('text') or '')
    value += '|'.join(sorted(str(o.get('text') or '') for o in q.get('options', [])))
    value += '|'.join(str(o.get('text') or '') for o in q.get('statements', []))
    return hashlib.sha256(re.sub(r'\s+', '', value).encode()).hexdigest()


def auto_graded(q):
    if q.get('_race_set_answer') or q.get('_race_answer_components') or '_race_saved_answer' in q:
        return True
    kind = q.get('kind')
    if kind == 'TN':
        opts = q.get('options') or []
        return len(opts) == 4 and sum(bool(o.get('correct')) for o in opts) == 1
    if kind == 'DS':
        return len(q.get('statements') or []) == 4
    return kind == 'TLN' and bool(str(q.get('answer') or '').strip())


def eligible(q):
    return auto_graded(q) or (q.get('kind') in ('TL', 'TLN') and bool(str(q.get('text') or '').strip()))


def bucket(q):
    return json.dumps([q.get('kind'), q.get('dang') or '', q.get('muc') or q.get('level') or ''], ensure_ascii=False)


def build_pool(qs, count):
    unique = {}
    for q in qs:
        if eligible(q):
            unique.setdefault(fingerprint(q), copy.deepcopy(q))
    pool = list(unique.values())
    if len(pool) < count:
        raise ValueError('Bài này có ' + str(len(pool)) + ' câu hợp lệ, không đủ ' + str(count) + ' câu/đề. Hãy giảm số câu hoặc chọn bài khác. Có thể dùng câu tự luận hoặc chưa có đáp án; ADMIN sẽ chấm các câu này.')
    # Fixed blueprint shared by everyone; rare buckets are not silently replaced.
    groups = defaultdict(list)
    for q in pool:
        groups[bucket(q)].append(q)
    # Round-robin weighted by available stock so a rare bucket doesn't cap the whole room at one.
    blueprint = Counter()
    for _ in range(count):
        key = max(groups, key=lambda k: len(groups[k]) / (blueprint[k] + 1))
        blueprint[key] += 1
    capacity = min(len(groups[k]) // n for k, n in blueprint.items())
    return pool, dict(blueprint), capacity


def allocate(pool, blueprint, existing):
    used = {fingerprint(q) for questions in existing for q in questions}
    groups = defaultdict(list)
    for q in pool:
        if fingerprint(q) not in used:
            groups[bucket(q)].append(q)
    selected = []
    for key, n in blueprint.items():
        if len(groups[key]) < n:
            raise ValueError('Phòng đã đủ người theo ngân hàng hiện có. ADMIN cần mở phòng khác hoặc bổ sung câu.')
        selected.extend(copy.deepcopy(RNG.sample(groups[key], n)))
    RNG.shuffle(selected)
    for q in selected:
        if q.get('kind') == 'TN':
            RNG.shuffle(q['options'])
    return selected


def numeric_pool(qs, count):
    pool = []
    for i, q in enumerate(qs):
        config = variants.spec(q)
        if not config:
            raise ValueError('Câu ' + str(i+1) + ' chưa có bộ đổi số. Hãy chọn các câu đã có bộ đổi số, hoặc chọn chế độ lấy câu từ ngân hàng. Hiện đã hỗ trợ bài Cosin–Sin và 7 câu Tham số về tập hợp và khoảng đã kiểm tra.')
        item = copy.deepcopy(q)
        item['_race_variant_spec'] = config
        pool.append(item)
    if not 1 <= count <= len(pool):
        raise ValueError('Số câu mỗi đề phải không vượt số câu đã chọn.')
    pool = RNG.sample(pool, count) if count < len(pool) else pool
    return pool, dict(Counter(bucket(q) for q in pool)), 200


def numeric_allocate(pool, existing):
    if len(existing) >= 200:
        raise ValueError('Phòng đã đủ 200 học sinh.')
    used = {fingerprint(q) for paper in existing for q in paper}
    paper = []
    for seed in pool:
        for _ in range(100):
            q = variants.generate(seed)
            if fingerprint(q) not in used:
                used.add(fingerprint(q)); paper.append(q); break
        else:
            raise ValueError('Đã hết bộ số khác nhau cho câu này. Hãy tạo lượt mới.')
    return paper


def correct(q, answer):
    if q.get("_race_set_answer") or q.get("_race_answer_components") or ("_race_saved_answer" in q and q.get("kind") != "TN"):
        return isinstance(answer, str) and variants.matches(q, answer)
    if not auto_graded(q):
        return False
    if q['kind'] == 'TN':
        return type(answer) is int and 0 <= answer < len(q['options']) and bool(q['options'][answer]['correct'])
    if q['kind'] == 'DS':
        return isinstance(answer, list) and len(answer) == 4 and all(type(a) is bool and a == bool(o.get('correct')) for a, o in zip(answer, q['statements']))
    return isinstance(answer, str) and len(answer) <= 100 and base.answer_equal(answer, q.get('answer'))


def graded_result(c, code, player):
    qs, answers = json.loads(player['questions']), json.loads(player['answers'])
    marks = {r['pos']: bool(r['ok']) for r in c.execute('SELECT pos,ok FROM race_marks WHERE room=? AND user=?', (code, player['user']))}
    pending = sum(not auto_graded(q) and i not in marks for i, q in enumerate(qs))
    results = [correct(q, answers.get(str(i))) if auto_graded(q) else marks.get(i) for i, q in enumerate(qs)]
    return sum(v is True for v in results), pending, results


def finish(c, r, player, now):
    if player['finished'] is not None or r['started'] is None:
        return
    qs, answers = json.loads(player['questions']), json.loads(player['answers'])
    score = sum(correct(q, answers.get(str(i))) for i, q in enumerate(qs))
    elapsed = max(0, min(now - r['started'], r['duration']))
    c.execute('UPDATE race_players SET finished=?,correct=?,elapsed=? WHERE room=? AND user=? AND finished IS NULL',
              (now, score, elapsed, r['code'], player['user']))


def response_label(q, answer):
    if answer is None or answer == '':
        return '(Chưa trả lời)'
    if q['kind'] == 'TN' and type(answer) is int and 0 <= answer < 4:
        return 'ABCD'[answer]
    if q['kind'] == 'DS' and isinstance(answer, list):
        return '; '.join(('abcd'[i] + ') ' + ('Đúng' if v is True else 'Sai' if v is False else 'Chưa chọn')) for i, v in enumerate(answer[:4]))
    return str(answer)


def expected_label(q):
    if q.get('_race_answer_display'):
        return q['_race_answer_display']
    if q.get('_race_answer_components'):
        return '$' + r';\quad '.join(variants.fmt(variants.parse_expression(v, False)) for v in q['_race_answer_components']) + '$'
    if q['kind'] == 'TN':
        return '; '.join('ABCD'[i] for i,o in enumerate(q.get('options', [])) if o.get('correct'))
    if q['kind'] == 'DS':
        return response_label(q, [bool(o.get('correct')) for o in q.get('statements', [])])
    return str(q.get('_race_saved_answer') or q.get('answer') or 'Xem lời giải / ADMIN chấm')


def public_question(q):
    src = q.get('src')
    out = {'kind': q['kind'], 'text': base.html_question(q.get('text', ''), src), 'manual': not auto_graded(q), 'numeric': bool(q.get('_race_answer_components') or q.get('_race_set_answer'))}
    for key in ('options', 'statements'):
        if q.get(key):
            out[key] = [base.html_question(o.get('text', ''), src) for o in q[key]]
    return out


def selected_race_button():
    if not base.can_manage_bank():
        return ''
    return '<button type="submit" form="questionForm" formaction="/member/race/from-selected" formmethod="post" name="race_pick_csrf" value="' + html.escape(csrf(), quote=True) + '" class="btn primary" onclick="if(!document.querySelector(\'input[name=qid]:checked\')){alert(\'Tick các câu muốn dùng trước khi tạo phòng.\');return false;}">🏁 Tạo phòng thi đua từ câu đã chọn</button>'


def source_questions(path, selection=''):
    qs = base.parse_lesson_questions(path)
    if not selection and any(q.get('src') for q in qs):
        # The dropdown names one file; the shared lesson parser reads the folder.
        # Keep global indices for compatibility with the checked-question flow.
        selected_path = str(path).replace('\\', '/')
        qs = [q for q in qs if str(q.get('src') or '').replace('\\', '/') == selected_path]
    if selection:
        pick = session.get('race_pick') or {}
        if pick.get('token') != selection or pick.get('path') != path:
            raise ValueError('Lựa chọn câu đã thay đổi. Quay lại bài, tick câu và tạo phòng lại.')
        ids = set(pick.get('ids') or [])
        qs = [q for q in qs if str(q.get('idx')) in ids]
        if len(qs) != len(ids):
            raise ValueError('Ngân hàng câu hỏi đã thay đổi. Hãy chọn lại câu trước khi tạo phòng.')
    return qs


@base.app.post('/member/race/from-selected')
def race_from_selected():
    if not base.can_manage_bank():
        abort(403)
    check_csrf()
    path = request.form.get('path', '')
    ids = list(dict.fromkeys(request.form.getlist('qid')))
    if not ids or len(ids) > 120:
        return base.page('Chọn câu thi đua', '<div class="wrap"><p>Hãy chọn từ 1 đến 120 câu để tạo phòng.</p><a class="btn" href="' + html.escape(base.dang_view_url(path), quote=True) + '">← Quay lại chọn câu</a></div>'), 400
    qs = base.parse_lesson_questions(path)
    selected = [q for q in qs if str(q.get('idx')) in set(ids)]
    if len(selected) != len(ids) or not any(eligible(q) for q in selected):
        return base.page('Chọn câu thi đua', '<div class="wrap"><p>Không tìm thấy các câu đã tick trong bài. Hãy tải lại danh sách câu rồi chọn lại.</p><a class="btn" href="' + html.escape(base.dang_view_url(path), quote=True) + '">← Quay lại chọn câu</a></div>'), 400
    token = secrets.token_hex(12)
    session['race_pick'] = {'token': token, 'path': path, 'ids': ids}
    return redirect('/member/race?selection=' + token)


@base.app.route('/race', methods=['GET', 'POST'], strict_slashes=False)
@base.app.route('/member/race', methods=['GET', 'POST'], strict_slashes=False)
def race_home():
    m, user = who()
    token = csrf()
    error = ''
    selection = request.form.get('selection') or request.args.get('selection', '')
    if request.method == 'POST':
        check_csrf()
        if request.form.get('code'):
            code = re.sub('[^A-Z0-9]', '', request.form['code'].upper())[:8]
            with db() as c:
                exists = c.execute('SELECT 1 FROM race_rooms WHERE code=?', (code,)).fetchone()
            if exists:
                return redirect('/member/race/' + code)
            error = '<p class="err">Mã phòng chưa tồn tại. ADMIN cần tạo phòng trước rồi gửi mã hoặc QR cho học sinh. Không tự nhập một mã bất kỳ để tạo phòng.</p>'
        elif not base.can_manage_bank():
            abort(403)
        if not request.form.get('code'):
            path = request.form.get('path', '')
            try:
                count = int(request.form.get('count', '10'))
                duration = int(request.form.get('minutes', '15')) * 60
                if not 1 <= count <= 60 or not 60 <= duration <= 10800:
                    raise ValueError('Chọn 1–60 câu và thời gian 1–180 phút.')
                qs = source_questions(path, selection)
                mode = request.form.get('mode', 'pool')
                pool, blueprint, capacity = numeric_pool(qs, count) if mode == 'numeric' else build_pool(qs, count)
                code = secrets.token_hex(4).upper()
                with db() as c:
                    c.execute('INSERT INTO race_rooms(code,owner,title,path,pool,blueprint,duration,state,created) VALUES (?,?,?,?,?,?,?,?,?)',
                              (code, user, request.form.get('title', 'Thi đua luyện đề')[:100], path, json.dumps(pool, ensure_ascii=False), json.dumps(blueprint, ensure_ascii=False), duration, 'waiting', time.time()))
                    c.execute('INSERT INTO race_meta VALUES (?,?)', (code, json.dumps({'mode':mode, 'reference':numeric_allocate(pool, []) if mode == 'numeric' else []}, ensure_ascii=False)))
                return redirect('/member/race/' + code)
            except (ValueError, OSError) as exc:
                error = '<p class="err">' + html.escape(str(exc)) + '</p>'
    creation = '<p><a class="btn" href="' + html.escape(base.login_url('/member/race'), quote=True) + '">ADMIN: Đăng nhập để tạo phòng + QR</a></p>'
    if base.can_manage_bank():
        selected = request.form.get('path') or request.args.get('path', '')
        lessons = [l for l in base.index_data().get('lessons', []) if l.get('path') and int(l.get('questions', l.get('count', 0)) or 0) > 0]
        options = '<option value="">— Chọn bài học để tạo phòng —</option>' + ''.join('<option value="' + html.escape(str(l['path']), quote=True) + '"' + (' selected' if l['path'] == selected else '') + '>' + html.escape(' · '.join(str(l.get(k) or '') for k in ('Mon','Lop','BaiHoc'))) + ' (' + str(l.get('questions', l.get('count', 0))) + ' câu)</option>' for l in lessons)
        creation = '<section class="race-create"><h2>📺 ADMIN · Tạo phòng chiếu thi đua + QR</h2><p>Chọn bài rồi bấm tạo phòng. Hệ thống sẽ tự sinh mã phòng và mã QR cho học sinh quét.</p><form method="post"><input type="hidden" name="csrf" value="' + token + '"><label>Tên phòng <input name="title" value="Thi đua luyện đề" maxlength="100" required></label><label>Bài học <select id="raceLesson" name="path" required>' + options + '</select></label><label>Chế độ <select id="raceMode" name="mode"><option value="numeric" selected>Đổi số riêng từng học sinh · chấm tự động</option><option value="pool">Lấy câu khác nhau từ ngân hàng</option></select></label><label>Số câu mỗi đề <input id="raceCount" name="count" type="number" min="1" max="60" value="5" required></label><label>Thời gian (phút) <input name="minutes" type="number" min="1" max="180" value="15" required></label><p id="racePoolInfo" role="status">Chọn bài để kiểm tra số câu và số học sinh có thể tham gia.</p><button id="raceCreate" class="btn primary" disabled>📺 Tạo phòng + Hiện mã QR</button></form><p>Chế độ đổi số: cùng dạng câu, mỗi học sinh nhận dữ kiện riêng và đáp án được tính lại. Chế độ ngân hàng: lấy các câu có sẵn khác nhau. Câu tự luận hoặc thiếu đáp án vẫn làm được; ADMIN chấm xong mới xếp hạng chính thức.</p></section>' + _SETUP_JS
        if selection:
            pick = session.get('race_pick') or {}
            if pick.get('token') != selection:
                return base.page('Chọn lại câu', '<div class="wrap"><p>Lựa chọn đã thay đổi hoặc hết hiệu lực. Quay lại bài để chọn câu.</p><a class="btn" href="/member">← Ngân hàng câu hỏi</a></div>'), 400
            picked_path = str(pick.get('path') or '')
            picked_qs = source_questions(picked_path, selection)
            valid_count = len({fingerprint(q) for q in picked_qs if eligible(q)})
            manual_count = sum(eligible(q) and not auto_graded(q) for q in picked_qs)
            start = creation.index('<label>Bài học')
            end = creation.index('</select></label>', start) + len('</select></label>')
            picked_html = '<p><b>Đã chọn ' + str(len(picked_qs)) + ' câu · ' + str(valid_count) + ' câu dùng được.</b></p><p>Trong đó ' + str(manual_count) + ' câu cần ADMIN chấm nếu dùng chế độ ngân hàng. Chế độ đổi số tính lại đáp án và chấm tự động. Phòng chỉ lấy câu trong danh sách thầy đã tick.</p><input id="raceLesson" type="hidden" name="path" value="' + html.escape(picked_path, quote=True) + '"><input id="raceSelection" type="hidden" name="selection" value="' + selection + '"><p><a href="' + html.escape(base.dang_view_url(picked_path), quote=True) + '">← Chọn lại câu trong bài</a> · <a href="/member/race">Dùng toàn bộ bài khác</a></p>'
            creation = creation[:start] + picked_html + creation[end:]
            creation = creation.replace('value="5" required', 'value="' + str(min(60, valid_count) if all(variants.spec(q) for q in picked_qs) else min(5, valid_count)) + '" required')
            creation = creation.replace('Chọn bài rồi bấm tạo phòng.', 'Các câu đã tick được chuyển sẵn vào phòng.')
    with db() as c:
        if base.can_manage_bank():
            recent = c.execute('SELECT code,title,state FROM race_rooms WHERE owner=? ORDER BY created DESC LIMIT 20', (user,)).fetchall()
        else:
            recent = c.execute('SELECT r.code,r.title,r.state FROM race_rooms r JOIN race_players p ON p.room=r.code WHERE p.user=? ORDER BY r.created DESC LIMIT 20', (user,)).fetchall()
    links = ''.join('<li><a href="/member/race/' + r['code'] + '">' + html.escape(r['title']) + ' · ' + r['code'] + '</a></li>' for r in recent)
    body = '<div class="wrap race"><h1>🏁 Thi đua luyện đề</h1><p>Học sinh chỉ cần mã phòng và họ tên, không cần đăng nhập tài khoản.</p>' + error + creation + '<section class="race-join"><h2>👨‍🎓 Học sinh · Vào phòng đã tạo</h2><form method="post"><input type="hidden" name="csrf" value="' + token + '"><label>Mã phòng <input name="code" maxlength="8" required placeholder="Nhập đúng mã ADMIN cung cấp"></label><button class="btn primary">Vào phòng</button></form></section>' + '<h2>Phòng của tôi</h2><ul>' + links + '</ul><a class="btn" href="/member">← Mục lục</a></div><style>.race{max-width:1000px}.race label{display:block;margin:12px 0}.race input,.race select{max-width:100%;padding:9px}.race select{width:100%}.race-create{border:2px solid #2563eb;background:#eff6ff;padding:20px;border-radius:12px;margin:16px 0}.race-join{border:1px solid #cbd5e1;padding:20px;border-radius:12px;margin:16px 0}</style>'
    body += '<link rel="stylesheet" href="/static/practice-race.css?v=mobile2">'
    return base.page('Thi đua luyện đề', body)


@base.app.get('/member/race/<code>', strict_slashes=False)
def race_page(code):
    m, user = who()
    with db() as c:
        r = c.execute('SELECT * FROM race_rooms WHERE code=?', (code,)).fetchone()
        if not r:
            return base.page('Không tìm thấy phòng', '<div class="wrap"><h2>Mã phòng chưa tồn tại hoặc đã hết hiệu lực</h2><p>ADMIN cần tạo phòng trước, sau đó gửi mã hoặc QR mới cho học sinh.</p><a class="btn primary" href="/member/race">← Tạo phòng / Nhập mã khác</a></div>'), 404
        host = is_host(r, user)
    cfg = json.dumps({'code': code, 'csrf': csrf(), 'host': host, 'name': m.get('name') or ''}, ensure_ascii=True).replace('<', '\\u003c')
    body = '<div class="wrap race"><div class="racebar"><a class="btn" href="/member/race">← Quay lại</a><h2>' + html.escape(r['title']) + ' · ' + html.escape(code) + '</h2><button id="raceFull" class="btn">⛶ Toàn màn hình</button></div><div id="raceNotice" role="status"></div><div id="raceControls"></div><p id="raceClock" aria-live="off"></p><div class="racegrid"><section><div id="raceNav"></div><div id="raceQuestion"></div><div id="raceActions"></div><div id="raceGrading"></div><div id="raceResults"></div></section><aside><h2>🏆 Bảng xếp hạng</h2><p>Ưu tiên số câu đúng; bằng điểm xét thời gian. Chỉ xếp hạng khi đã nộp và chấm đủ. Câu thiếu đáp án/tự luận chờ ADMIN chấm. Mỗi câu đúng tính 1; câu Đúng/Sai cần đúng cả 4 ý.</p><div id="raceRanks"></div></aside></div></div><style>.race{max-width:1300px}.racebar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.racebar h2{flex:1}.racegrid{display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:20px}.racegrid section,.racegrid aside{background:#fff;border:1px solid #cbd5e1;padding:18px;border-radius:12px;min-width:0}#raceClock{font-size:26px;font-weight:800;color:#b45309;font-variant-numeric:tabular-nums}#raceQuestion{font-size:18px;line-height:1.6;overflow-wrap:anywhere}#raceQuestion label{display:flex;gap:10px;margin:12px 0;padding:10px;border:1px solid #cbd5e1;border-radius:8px}#raceQuestion select,#raceQuestion input{padding:10px;max-width:100%}#raceNav{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:15px}.race table{width:100%;border-collapse:collapse}.race th,.race td{padding:8px;border-bottom:1px solid #e2e8f0;text-align:left}.race tr.me{background:#dbeafe}.race .medal{font-weight:bold;color:#b45309}#raceControls{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}#raceNotice{padding:10px}#raceActions{margin-top:18px;display:flex;gap:8px;flex-wrap:wrap}@media(max-width:800px){.racegrid{grid-template-columns:1fr}}</style><script>window.RACE_CONFIG=' + cfg + ';</script><script src="/static/practice-race.js?v=mobile2"></script>'
    if host:
        join_url = base.public_origin() + '/member/race/' + code
        qr = '<section id="raceQR" class="race-qr"><img src="/race/' + code + '/qr.svg" alt="Mã QR tham gia phòng ' + code + '" width="260" height="260"><div><h2>📱 Quét QR để tham gia</h2><p>MÃ PHÒNG</p><strong style="font:800 38px monospace;letter-spacing:4px">' + code + '</strong><p>Học sinh quét QR → nhập họ tên → chờ bắt đầu. Quét và tham gia trước khi ADMIN bấm bắt đầu.</p><input readonly aria-label="Link tham gia" value="' + html.escape(join_url, quote=True) + '" style="width:100%;padding:10px"></div></section><style>.race-qr{display:flex;gap:24px;align-items:center;border:2px solid #2563eb;border-radius:14px;background:white;padding:20px;margin:16px 0}.race-qr[hidden]{display:none}.race-qr img{max-width:42%;height:auto}.race-qr>div{flex:1;min-width:0}@media(max-width:600px){.race-qr{display:block;text-align:center}.race-qr img{max-width:100%;width:220px}}</style>'
        body = body.replace('<div id="raceControls"></div>', qr + '<div id="raceControls"></div>')
    body += '<link rel="stylesheet" href="/static/practice-race.css?v=mobile2">'
    response = base.page('Thi đua luyện đề', body)
    response.headers['Cache-Control'] = 'no-store'
    return response


_SETUP_JS = '''<script>(function(){
const lesson=document.getElementById('raceLesson'),count=document.getElementById('raceCount'),info=document.getElementById('racePoolInfo'),create=document.getElementById('raceCreate');let version=0;
async function preview(){const mine=++version;create.disabled=true;if(!lesson.value){info.textContent='Chọn bài học để tạo phòng.';return}info.textContent='Đang kiểm tra ngân hàng câu hỏi…';try{const r=await fetch('/api/race-preview?'+new URLSearchParams({path:lesson.value,count:count.value,mode:document.getElementById('raceMode').value,selection:(document.getElementById('raceSelection')||{}).value||''}),{cache:'no-store'}),d=await r.json();if(mine!==version)return;if(!r.ok||!d.ok)throw Error(d.error||'Không kiểm tra được bài');info.textContent=d.mode==='numeric'?'Đổi số riêng · '+d.count+' câu/đề · chấm tự động · tối đa 200 học sinh.':'Có '+d.available+' câu dùng được ('+d.manual+' câu ADMIN chấm) · '+d.count+' câu/đề · Tối đa '+d.capacity+' học sinh với các đề không trùng câu.';create.disabled=d.capacity<1}catch(e){if(mine===version)info.textContent=e.message}}
document.getElementById('raceMode').addEventListener('change',preview);lesson.addEventListener('change',preview);count.addEventListener('change',preview);preview();})();</script>'''


@base.app.get('/api/race-preview')
def race_preview():
    if not base.can_manage_bank():
        abort(403)
    try:
        n = int(request.args.get('count', '5'))
        if not 1 <= n <= 60:
            raise ValueError('Số câu phải từ 1 đến 60.')
        qs = source_questions(request.args.get('path', ''), request.args.get('selection', ''))
        mode = request.args.get('mode', 'pool')
        pool, blueprint, capacity = numeric_pool(qs, n) if mode == 'numeric' else build_pool(qs, n)
        return jsonify(ok=True, mode=mode, available=len(pool), count=n, capacity=capacity, manual=0 if mode == 'numeric' else sum(not auto_graded(q) for q in pool))
    except (ValueError, OSError) as exc:
        return jsonify(ok=False, error=str(exc)), 400


@base.app.get('/race/<code>/qr.svg')
def race_qr(code):
    with db() as c:
        room(c, code)
    out = io.BytesIO()
    segno.make(base.public_origin() + '/member/race/' + code, error='m').save(out, kind='svg', scale=8, border=4, dark='#102746', light='white')
    return Response(out.getvalue(), mimetype='image/svg+xml', headers={'Cache-Control':'no-store'})


@base.app.route('/api/race/<code>', methods=['GET', 'POST'])
def race_api(code):
    m, user = who()
    if request.method == 'POST':
        check_csrf()
    data = request.get_json(silent=True) or {}
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        now = time.time()
        r = room(c, code)
        host = is_host(r, user)
        meta_row = c.execute('SELECT config FROM race_meta WHERE room=?', (code,)).fetchone()
        meta = json.loads(meta_row[0]) if meta_row else {'mode':'pool'}
        numeric = meta.get('mode') == 'numeric'
        player = c.execute('SELECT * FROM race_players WHERE room=? AND user=?', (code, user)).fetchone()
        action = data.get('action') if request.method == 'POST' else None
        if action == 'new_round':
            if not host: abort(403)
            if r['state'] != 'closed':
                return jsonify(ok=False, error='Kết thúc lượt hiện tại trước khi tạo lượt mới.'), 409
            newcode = secrets.token_hex(4).upper()
            c.execute('INSERT INTO race_rooms(code,owner,title,path,pool,blueprint,duration,state,created) VALUES (?,?,?,?,?,?,?,?,?)',
                      (newcode, user, r['title'], r['path'], r['pool'], r['blueprint'], r['duration'], 'waiting', now))
            if numeric:
                meta['reference'] = numeric_allocate(json.loads(r['pool']), [meta.get('reference', [])])
            c.execute('INSERT INTO race_meta VALUES (?,?)', (newcode, json.dumps(meta, ensure_ascii=False)))
            return jsonify(ok=True, redirect='/member/race/'+newcode)
        elif action == 'variant':
            if not host: abort(403)
            if not numeric: return jsonify(ok=False, error='Phòng này dùng câu cố định. Hãy tạo phòng ở chế độ đổi số.'), 400
            meta['reference'] = numeric_allocate(json.loads(r['pool']), [meta.get('reference', [])])
            c.execute('INSERT OR REPLACE INTO race_meta VALUES (?,?)', (code, json.dumps(meta, ensure_ascii=False)))
        elif action in ('start', 'close', 'show'):
            if not host:
                abort(403)
            if action == 'start' and r['state'] == 'waiting':
                if not c.execute('SELECT 1 FROM race_players WHERE room=?', (code,)).fetchone():
                    return jsonify(ok=False, error='Chờ ít nhất một thành viên tham gia.'), 400
                c.execute("UPDATE race_rooms SET state='running',started=? WHERE code=?", (now, code))
                c.execute('UPDATE race_players SET started=? WHERE room=?', (now, code))
            elif action == 'close' and r['state'] != 'closed':
                c.execute("UPDATE race_rooms SET state='closed' WHERE code=?", (code,))
            elif action == 'show':
                n = sum(json.loads(r['blueprint']).values())
                pos = data.get('pos')
                if type(pos) is not int or not 0 <= pos < n:
                    abort(400)
                c.execute('UPDATE race_rooms SET shown=? WHERE code=?', (pos, code))
            r = room(c, code)
        elif action == 'join':
            if host:
                return jsonify(ok=False, error='ADMIN dùng màn hình điều khiển; học sinh mở link trên thiết bị khác và ghi tên.'), 400
            if not player:
                if r['state'] != 'waiting':
                    return jsonify(ok=False, error='Phòng đã bắt đầu hoặc đã đóng.'), 409
                name = ' '.join(str(data.get('name') or m.get('name') or '').split())
                if not 2 <= len(name) <= 80 or not name.isprintable():
                    return jsonify(ok=False, error='Nhập tên học sinh từ 2 đến 80 ký tự.'), 400
                original_name, suffix = name, 2
                while c.execute('SELECT 1 FROM race_players WHERE room=? AND name=?', (code, name)).fetchone():
                    name = original_name + ' (' + str(suffix) + ')'
                    suffix += 1
                existing = [json.loads(p[0]) for p in c.execute('SELECT questions FROM race_players WHERE room=?', (code,))]
                try:
                    qs = numeric_allocate(json.loads(r['pool']), existing) if numeric else allocate(json.loads(r['pool']), json.loads(r['blueprint']), existing)
                except ValueError as exc:
                    return jsonify(ok=False, error=str(exc)), 409
                c.execute('INSERT INTO race_players(room,user,name,questions) VALUES (?,?,?,?)', (code, user, name, json.dumps(qs, ensure_ascii=False)))
                player = c.execute('SELECT * FROM race_players WHERE room=? AND user=?', (code, user)).fetchone()
        elif action == 'grade':
            if not host:
                abort(403)
            target, pos, decision = data.get('player'), data.get('pos'), data.get('correct')
            p = c.execute('SELECT * FROM race_players WHERE room=? AND user=?', (code, target)).fetchone() if isinstance(target, str) else None
            if not p or p['finished'] is None or type(pos) is not int or type(decision) is not bool:
                return jsonify(ok=False, error='Chỉ chấm bài đã nộp; hãy chọn câu và Đúng/Sai.'), 400
            qs = json.loads(p['questions'])
            if not 0 <= pos < len(qs) or auto_graded(qs[pos]):
                return jsonify(ok=False, error='Câu này đã được chấm tự động.'), 400
            c.execute('INSERT OR REPLACE INTO race_marks(room,user,pos,ok) VALUES (?,?,?,?)', (code, target, pos, int(decision)))
            score, _, _ = graded_result(c, code, p)
            c.execute('UPDATE race_players SET correct=? WHERE room=? AND user=?', (score, code, target))
        elif action in ('save', 'submit'):
            if not player or r['state'] != 'running':
                return jsonify(ok=False, error='Chưa bắt đầu hoặc phòng đã kết thúc.'), 409
            if player['finished'] is None and now < r['started'] + r['duration']:
                answers = data.get('answers')
                n = len(json.loads(player['questions']))
                if not isinstance(answers, dict) or len(json.dumps(answers)) > 200000 or any(k not in {str(i) for i in range(n)} for k in answers) or any(isinstance(v, str) and len(v)>5000 for v in answers.values()):
                    abort(400)
                c.execute('UPDATE race_players SET answers=? WHERE room=? AND user=?', (json.dumps(answers), code, user))
                player = c.execute('SELECT * FROM race_players WHERE room=? AND user=?', (code, user)).fetchone()
                if action == 'submit':
                    finish(c, r, player, now)
        elif action is not None:
            abort(400)
        if r['state'] == 'running' and now >= r['started'] + r['duration']:
            c.execute("UPDATE race_rooms SET state='closed' WHERE code=?", (code,))
            r = room(c, code)
        if r['state'] == 'closed':
            for p in c.execute('SELECT * FROM race_players WHERE room=? AND finished IS NULL', (code,)).fetchall():
                finish(c, r, p, now)
        players = c.execute('SELECT * FROM race_players WHERE room=? ORDER BY finished IS NULL,correct DESC,elapsed ASC,name', (code,)).fetchall()
        blueprint = json.loads(r['blueprint'])
        pool = json.loads(r['pool'])
        counts = Counter(bucket(q) for q in pool)
        capacity = 200 if numeric else min(counts[k] // n for k, n in blueprint.items())
        ranking = []
        assessments = {}
        for p in players:
            score, pending, decisions = graded_result(c, code, p)
            assessments[p['user']] = (score, pending, decisions)
            submitted = p['finished'] is not None
            ranking.append({'name': p['name'], 'me': p['user'] == user, 'done': submitted and pending == 0, 'submitted': submitted, 'pending': pending if submitted else 0, 'correct': score if submitted else None, 'elapsed': p['elapsed'], 'answered': len(json.loads(p['answers']))})
        ranking.sort(key=lambda p: (not p['done'], -(p['correct'] or 0), p['elapsed'] if p['elapsed'] is not None else float('inf'), p['name']))
        result = {'ok': True, 'mode':meta.get('mode','pool'), 'host': host, 'state': r['state'], 'now': now, 'started': r['started'], 'duration': r['duration'], 'ranking': ranking, 'capacity': capacity, 'total': sum(blueprint.values()), 'joined': player is not None, 'shown': r['shown']}
        player = c.execute('SELECT * FROM race_players WHERE room=? AND user=?', (code, user)).fetchone()
        if player and r['state'] != 'waiting':
            qs = json.loads(player['questions'])
            result.update(questions=[public_question(q) for q in qs], answers=json.loads(player['answers']), finished=player['finished'] is not None)
            if r['state'] == 'closed':
                _, _, decisions = graded_result(c, code, player)
                result['review'] = [{'correct': decisions[i], 'solution': base.html_question(q.get('solution', ''), q.get('src'))} for i, q in enumerate(qs)]
        if host:
            # Project a separate, fixed reference exam. Never expose anyone else's private paper.
            reference = []
            for key, n in blueprint.items():
                reference.extend([q for q in pool if bucket(q) == key][:n])
            result['reference'] = [public_question(q) for q in (meta['reference'] if numeric else reference)]
            result['grading'] = []
            result['results'] = []
            for p in players:
                if p['finished'] is None:
                    continue
                answers = json.loads(p['answers'])
                score, pending, decisions = assessments[p['user']]
                result['results'].append({'name':p['name'], 'score':score, 'pending':pending, 'elapsed':p['elapsed'], 'questions':[
                    {'question':public_question(q), 'answer':response_label(q, answers.get(str(i))),
                     'expected':base.html_question(expected_label(q), q.get('src')),
                     'solution':base.html_question(q.get('solution', ''), q.get('src')), 'correct':decisions[i]}
                    for i,q in enumerate(json.loads(p['questions']))]})
                for i, q in enumerate(json.loads(p['questions'])):
                    if not auto_graded(q):
                        result['grading'].append({'player':p['user'], 'name':p['name'], 'pos':i, 'text':base.html_question(q.get('text',''),q.get('src')), 'answer':str(answers.get(str(i)) or ''), 'solution':base.html_question(q.get('solution',''),q.get('src')), 'correct':decisions[i]})
        return jsonify(result)


@base.app.after_request
def race_no_cache(response):
    if request.path.startswith('/api/race/') or request.path.startswith('/member/race') or request.path.rstrip('/') == '/race':
        response.headers['Cache-Control'] = 'no-store, private'
    return response
