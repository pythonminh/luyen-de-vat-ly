"""Timed, server-graded practice rooms with disjoint, stratified question sets."""
import copy
import hashlib
import html
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

from flask import abort, jsonify, redirect, request, session
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
      PRIMARY KEY(room,user));''')
    try:
        with c:
            yield c
    finally:
        c.close()


def who():
    m = base.member_current()
    if not m:
        abort(401)
    return m, str(m.get('username') or '').strip().casefold()


def csrf():
    if not session.get('race_csrf'):
        session['race_csrf'] = secrets.token_urlsafe(24)
    return session['race_csrf']


def check_csrf():
    value = request.headers.get('X-Race-CSRF', '') or request.form.get('csrf', '')
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


def eligible(q):
    kind = q.get('kind')
    if kind == 'TN':
        opts = q.get('options') or []
        return len(opts) == 4 and sum(bool(o.get('correct')) for o in opts) == 1
    if kind == 'DS':
        return len(q.get('statements') or []) == 4
    return kind == 'TLN' and bool(str(q.get('answer') or '').strip())


def bucket(q):
    return json.dumps([q.get('kind'), q.get('dang') or '', q.get('muc') or q.get('level') or ''], ensure_ascii=False)


def build_pool(qs, count):
    unique = {}
    for q in qs:
        if eligible(q):
            unique.setdefault(fingerprint(q), copy.deepcopy(q))
    pool = list(unique.values())
    if len(pool) < count:
        raise ValueError('Không đủ câu hợp lệ để tạo đề. Chỉ dùng TN, Đúng/Sai và trả lời ngắn có đáp án.')
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


def correct(q, answer):
    if q['kind'] == 'TN':
        return type(answer) is int and 0 <= answer < len(q['options']) and bool(q['options'][answer]['correct'])
    if q['kind'] == 'DS':
        return isinstance(answer, list) and len(answer) == 4 and all(type(a) is bool and a == bool(o.get('correct')) for a, o in zip(answer, q['statements']))
    return isinstance(answer, str) and len(answer) <= 100 and base.answer_equal(answer, q.get('answer'))


def finish(c, r, player, now):
    if player['finished'] is not None or r['started'] is None:
        return
    qs, answers = json.loads(player['questions']), json.loads(player['answers'])
    score = sum(correct(q, answers.get(str(i))) for i, q in enumerate(qs))
    elapsed = max(0, min(now - r['started'], r['duration']))
    c.execute('UPDATE race_players SET finished=?,correct=?,elapsed=? WHERE room=? AND user=? AND finished IS NULL',
              (now, score, elapsed, r['code'], player['user']))


def public_question(q):
    src = q.get('src')
    out = {'kind': q['kind'], 'text': base.html_question(q.get('text', ''), src)}
    for key in ('options', 'statements'):
        if q.get(key):
            out[key] = [base.html_question(o.get('text', ''), src) for o in q[key]]
    return out


@base.app.route('/member/race', methods=['GET', 'POST'])
def race_home():
    if not base.member_current():
        return redirect(base.login_url('/member/race'))
    m, user = who()
    token = csrf()
    error = ''
    if request.method == 'POST':
        check_csrf()
        if request.form.get('code'):
            return redirect('/member/race/' + re.sub('[^A-Z0-9]', '', request.form['code'].upper())[:8])
        if not base.can_manage_bank():
            abort(403)
        path = request.form.get('path', '')
        try:
            count = int(request.form.get('count', '10'))
            duration = int(request.form.get('minutes', '15')) * 60
            if not 1 <= count <= 60 or not 60 <= duration <= 10800:
                raise ValueError('Chọn 1–60 câu và thời gian 1–180 phút.')
            qs = base.parse_lesson_questions(path)
            pool, blueprint, capacity = build_pool(qs, count)
            code = secrets.token_hex(4).upper()
            with db() as c:
                c.execute('INSERT INTO race_rooms(code,owner,title,path,pool,blueprint,duration,state,created) VALUES (?,?,?,?,?,?,?,?,?)',
                          (code, user, request.form.get('title', 'Thi đua luyện đề')[:100], path, json.dumps(pool, ensure_ascii=False), json.dumps(blueprint, ensure_ascii=False), duration, 'waiting', time.time()))
            return redirect('/member/race/' + code)
        except (ValueError, OSError) as exc:
            error = '<p class="err">' + html.escape(str(exc)) + '</p>'
    creation = ''
    if base.can_manage_bank():
        selected = request.args.get('path', '')
        lessons = base.index_data().get('lessons', [])
        options = ''.join('<option value="' + html.escape(str(l.get('path', '')), quote=True) + '"' + (' selected' if l.get('path') == selected else '') + '>' + html.escape(str(l.get('path', ''))) + '</option>' for l in lessons if l.get('path'))
        creation = '<h2>ADMIN · Tạo phòng</h2><form method="post"><input type="hidden" name="csrf" value="' + token + '"><label>Tên phòng <input name="title" value="Thi đua luyện đề" maxlength="100" required></label><label>Bài học <select name="path" required>' + options + '</select></label><label>Số câu mỗi đề <input name="count" type="number" min="1" max="60" value="10" required></label><label>Thời gian (phút) <input name="minutes" type="number" min="1" max="180" value="15" required></label><button class="btn primary">Tạo phòng thi đua</button></form><p>Mỗi thành viên nhận bộ câu riêng, không trùng câu với người khác, cùng cấu trúc dạng bài và mức độ. Tự luận cần chấm tay nên chưa đưa vào bảng xếp hạng.</p>'
    with db() as c:
        if base.can_manage_bank():
            recent = c.execute('SELECT code,title,state FROM race_rooms WHERE owner=? ORDER BY created DESC LIMIT 20', (user,)).fetchall()
        else:
            recent = c.execute('SELECT r.code,r.title,r.state FROM race_rooms r JOIN race_players p ON p.room=r.code WHERE p.user=? ORDER BY r.created DESC LIMIT 20', (user,)).fetchall()
    links = ''.join('<li><a href="/member/race/' + r['code'] + '">' + html.escape(r['title']) + ' · ' + r['code'] + '</a></li>' for r in recent)
    body = '<div class="wrap race"><h1>🏁 Thi đua luyện đề</h1>' + error + '<form method="post"><input type="hidden" name="csrf" value="' + token + '"><label>Mã phòng <input name="code" maxlength="8" required placeholder="Nhập mã ADMIN cung cấp"></label><button class="btn primary">Vào phòng</button></form>' + creation + '<h2>Phòng của tôi</h2><ul>' + links + '</ul><a class="btn" href="/member">← Mục lục</a></div><style>.race{max-width:1000px}.race label{display:block;margin:12px 0}.race input,.race select{max-width:100%;padding:9px}.race select{width:100%}</style>'
    return base.page('Thi đua luyện đề', body)


@base.app.get('/member/race/<code>')
def race_page(code):
    if not base.member_current():
        return redirect(base.login_url(request.path))
    m, user = who()
    with db() as c:
        r = room(c, code)
        host = is_host(r, user)
        if not host and not base.can_practice(m, r['path']):
            abort(403)
    cfg = json.dumps({'code': code, 'csrf': csrf(), 'host': host}, ensure_ascii=True)
    body = '<div class="wrap race"><div class="racebar"><a class="btn" href="/member/race">← Quay lại</a><h2>' + html.escape(r['title']) + ' · ' + html.escape(code) + '</h2><button id="raceFull" class="btn">⛶ Toàn màn hình</button></div><div id="raceNotice" role="status"></div><div id="raceControls"></div><p id="raceClock" aria-live="off"></p><div class="racegrid"><section><div id="raceNav"></div><div id="raceQuestion"></div><div id="raceActions"></div></section><aside><h2>🏆 Bảng xếp hạng</h2><p>Ưu tiên số câu đúng; bằng điểm xét thời gian. Chỉ xếp hạng khi đã nộp. Mỗi câu đúng tính 1; câu Đúng/Sai cần đúng cả 4 ý.</p><div id="raceRanks"></div></aside></div></div><style>.race{max-width:1300px}.racebar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.racebar h2{flex:1}.racegrid{display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:20px}.racegrid section,.racegrid aside{background:#fff;border:1px solid #cbd5e1;padding:18px;border-radius:12px;min-width:0}#raceClock{font-size:26px;font-weight:800;color:#b45309;font-variant-numeric:tabular-nums}#raceQuestion{font-size:18px;line-height:1.6;overflow-wrap:anywhere}#raceQuestion label{display:flex;gap:10px;margin:12px 0;padding:10px;border:1px solid #cbd5e1;border-radius:8px}#raceQuestion select,#raceQuestion input{padding:10px;max-width:100%}#raceNav{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:15px}.race table{width:100%;border-collapse:collapse}.race th,.race td{padding:8px;border-bottom:1px solid #e2e8f0;text-align:left}.race tr.me{background:#dbeafe}.race .medal{font-weight:bold;color:#b45309}#raceControls{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}#raceNotice{padding:10px}#raceActions{margin-top:18px;display:flex;gap:8px;flex-wrap:wrap}@media(max-width:800px){.racegrid{grid-template-columns:1fr}}</style><script>window.RACE_CONFIG=' + cfg + ';</script><script src="/static/practice-race.js"></script>'
    response = base.page('Thi đua luyện đề', body)
    response.headers['Cache-Control'] = 'no-store'
    return response


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
        if not host and not base.can_practice(m, r['path']):
            abort(403)
        player = c.execute('SELECT * FROM race_players WHERE room=? AND user=?', (code, user)).fetchone()
        action = data.get('action') if request.method == 'POST' else None
        if action in ('start', 'close', 'show'):
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
                return jsonify(ok=False, error='ADMIN dùng màn hình điều khiển; thành viên đăng nhập tài khoản riêng.'), 400
            if not player:
                if r['state'] != 'waiting':
                    return jsonify(ok=False, error='Phòng đã bắt đầu hoặc đã đóng.'), 409
                existing = [json.loads(p[0]) for p in c.execute('SELECT questions FROM race_players WHERE room=?', (code,))]
                try:
                    qs = allocate(json.loads(r['pool']), json.loads(r['blueprint']), existing)
                except ValueError as exc:
                    return jsonify(ok=False, error=str(exc)), 409
                c.execute('INSERT INTO race_players(room,user,name,questions) VALUES (?,?,?,?)', (code, user, str(m.get('name') or m.get('username'))[:100], json.dumps(qs, ensure_ascii=False)))
                player = c.execute('SELECT * FROM race_players WHERE room=? AND user=?', (code, user)).fetchone()
        elif action in ('save', 'submit'):
            if not player or r['state'] != 'running':
                return jsonify(ok=False, error='Chưa bắt đầu hoặc phòng đã kết thúc.'), 409
            if player['finished'] is None and now < r['started'] + r['duration']:
                answers = data.get('answers')
                n = len(json.loads(player['questions']))
                if not isinstance(answers, dict) or len(json.dumps(answers)) > 16000 or any(k not in {str(i) for i in range(n)} for k in answers):
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
        capacity = min(counts[k] // n for k, n in blueprint.items())
        ranking = [{'name': p['name'], 'me': p['user'] == user, 'done': p['finished'] is not None, 'correct': p['correct'], 'elapsed': p['elapsed'], 'answered': len(json.loads(p['answers']))} for p in players]
        result = {'ok': True, 'host': host, 'state': r['state'], 'now': now, 'started': r['started'], 'duration': r['duration'], 'ranking': ranking, 'capacity': capacity, 'total': sum(blueprint.values()), 'joined': player is not None, 'shown': r['shown']}
        player = c.execute('SELECT * FROM race_players WHERE room=? AND user=?', (code, user)).fetchone()
        if player and r['state'] != 'waiting':
            qs = json.loads(player['questions'])
            result.update(questions=[public_question(q) for q in qs], answers=json.loads(player['answers']), finished=player['finished'] is not None)
            if r['state'] == 'closed':
                result['review'] = [{'correct': correct(q, result['answers'].get(str(i))), 'solution': base.html_question(q.get('solution', ''), q.get('src'))} for i, q in enumerate(qs)]
        if host:
            # Project a separate, fixed reference exam. Never expose anyone else's private paper.
            reference = []
            for key, n in blueprint.items():
                reference.extend([q for q in pool if bucket(q) == key][:n])
            result['reference'] = [public_question(q) for q in reference]
        return jsonify(result)


@base.app.after_request
def race_no_cache(response):
    if request.path.startswith('/api/race/') or request.path.startswith('/member/race'):
        response.headers['Cache-Control'] = 'no-store, private'
    return response
