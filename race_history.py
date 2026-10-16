"""Owner-only history, exports and archive integration for practice races."""
import html
import json
import re
import threading
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo

from flask import Response,abort,g,jsonify,redirect,request
import app as base
import race_archive as archive
import practice_race as race

TZ=ZoneInfo('Asia/Ho_Chi_Minh')
_RESTORE_LOCK=threading.Lock()


def esc(s):return html.escape(str(s),quote=True)


def stamp(value):
    return datetime.fromtimestamp(value,TZ).strftime('%d/%m/%Y %H:%M:%S') if value is not None else '—'


def duration(value):
    if value is None:return '—'
    return f'{int(value)//60:02d}:{int(value)%60:02d}'


def teacher():
    if not base.can_manage_bank():abort(403)
    return race.who()[1]


def restore_code(code):
    if not archive.configured() or not re.fullmatch(r'[A-F0-9]{8}',code):return
    with race.db() as c:
        if c.execute('SELECT 1 FROM race_rooms WHERE code=?',(code,)).fetchone():return
    with _RESTORE_LOCK:
        # The encrypted index avoids a remote request for every invalid public code.
        if code not in archive.index():return
        data=archive.load(code)
        if data:archive.restore(data)


def owned_room(code,user):
    try:restore_code(code)
    except Exception:abort(503,description='Chưa đọc được bản lưu lâu dài. Hãy thử lại hoặc nhập tệp sao lưu đã tải.')
    with race.db() as c:
        r=race.room(c,code)
        if r['owner']!=user:abort(403)
        return dict(r)


def history():
    user=teacher();remote_error=False
    with race.db() as c:
        rooms={r['code']:dict(r) for r in c.execute('SELECT * FROM race_rooms WHERE owner=?',(user,))}
        for code,r in rooms.items():
            r['students']=[p[0] for p in c.execute('SELECT name FROM race_players WHERE room=?',(code,))]
            r['players']=c.execute('SELECT COUNT(*) FROM race_players WHERE room=?',(code,)).fetchone()[0]
            r['submitted']=c.execute('SELECT COUNT(*) FROM race_players WHERE room=? AND finished IS NOT NULL',(code,)).fetchone()[0]
    if archive.configured():
        try:
            for code,r in archive.index().items():
                if r.get('owner')==user and code not in rooms:rooms[code]=r
        except Exception:remote_error=True
    start=request.args.get('from','');end=request.args.get('to','');search=request.args.get('q','').strip().casefold()
    try:
        lower=datetime.fromisoformat(start).replace(tzinfo=TZ).timestamp() if start else float('-inf')
        upper=(datetime.fromisoformat(end).replace(tzinfo=TZ)+timedelta(days=1)).timestamp() if end else float('inf')
    except ValueError:abort(400)
    rows=[]
    for r in sorted(rooms.values(),key=lambda r:r['created'],reverse=True):
        if not lower<=r['created']<upper or (search and search not in (r['title']+' '+r['code']+' '+' '.join(r.get('students',[]))).casefold()):continue
        rows.append('<tr><td>'+stamp(r['created'])+'</td><td><a href="/member/race/history/'+r['code']+'">'+esc(r['title'])+'</a><br><small>'+r['code']+'</small></td><td>'+str(r.get('submitted',0))+'/'+str(r.get('players',0))+' đã nộp</td><td>'+esc({'waiting':'Chờ thi','running':'Đang thi','closed':'Đã kết thúc'}.get(r['state'],r['state']))+'</td></tr>')
    state=archive.health()
    message='Bản lưu lâu dài đã kết nối. Đề, câu trả lời và kết quả được tự động đồng bộ sau khi nộp bài.' if state['verified'] else 'Đang kiểm tra nơi lưu lâu dài.' if state['configured'] else 'Hiện đang lưu trên máy chủ. Hãy tải tệp sao lưu của phòng để giữ bản riêng.'
    if remote_error:message+=' Chưa đọc được bản lưu lâu dài lúc này; các phòng đang có trên máy chủ vẫn hiển thị.'
    body='<div class="wrap race"><a class="btn" href="/member/race">← Phòng thi đua</a><h1>📚 Lịch sử bài làm học sinh</h1><p>'+message+'</p><form method="get"><label>Từ ngày <input type="date" name="from" value="'+esc(start)+'"></label><label>Đến ngày <input type="date" name="to" value="'+esc(end)+'"></label><label>Tên học sinh / phòng <input name="q" value="'+esc(request.args.get('q',''))+'"></label><button class="btn primary">Lọc lịch sử</button></form><p>Thời gian hiển thị theo giờ Việt Nam. Mở phòng để xem từng đề riêng, đáp án, bài làm và lịch sử trả lời.</p><div style="max-width:100%;overflow:auto"><table><thead><tr><th>Ngày tạo</th><th>Phòng</th><th>Bài nộp</th><th>Trạng thái</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div><p>'+('Chưa có phòng phù hợp.' if not rows else '')+'</p><details><summary>Khôi phục từ tệp sao lưu đã tải</summary><form method="post" action="/member/race/history/import" enctype="multipart/form-data"><input type="hidden" name="csrf" value="'+race.csrf()+'"><input type="file" name="backup" accept=".json" required><button class="btn">Nhập tệp sao lưu</button></form></details></div>'
    return page('Lịch sử bài làm',body)


def detail(code):
    user=teacher();r=owned_room(code,user)
    with race.db() as c:
        players=c.execute('SELECT * FROM race_players WHERE room=? ORDER BY finished IS NULL,correct DESC,elapsed,name',(code,)).fetchall()
        sections=[]
        for p in players:
            score,pending,decisions=race.graded_result(c,code,p)
            qs=json.loads(p['questions']);answers=json.loads(p['answers'])
            content=[]
            for i,q in enumerate(qs):
                verdict='Chưa nộp' if p['finished'] is None else 'Chờ ADMIN chấm' if decisions[i] is None else '✅ Đúng' if decisions[i] else '❌ Sai'
                public=race.public_question(q)
                choices=''.join('<p><b>'+('ABCD' if q['kind']=='TN' else 'abcd')[j]+'.</b> '+text+'</p>' for j,text in enumerate(public.get('options') or public.get('statements') or []))
                content.append('<section><h3>Câu '+str(i+1)+' · '+verdict+'</h3>'+public['text']+choices+'<p><b>Học sinh trả lời:</b> '+esc(race.response_label(q,answers.get(str(i))))+'</p><p><b>Đáp án của đề này:</b> '+base.html_question(race.expected_label(q),q.get('src'))+'</p><details><summary>Lời giải</summary>'+base.html_question(q.get('solution',''),q.get('src'))+'</details></section>')
            events=c.execute('SELECT * FROM race_events WHERE room=? AND user=? AND kind IN (\'save\',\'submit\') ORDER BY at DESC,id DESC LIMIT 200',(code,p['user'])).fetchall()
            timeline=[]
            for e in reversed(events):
                changes=json.loads(e['payload']).get('changes',{})
                changes_text='; '.join('Câu '+str(int(k)+1)+': '+race.response_label(qs[int(k)],v) for k,v in changes.items() if str(k).isdigit() and int(k)<len(qs))
                timeline.append('<li>'+stamp(e['at'])+' · '+('Nộp bài' if e['kind']=='submit' else 'Lưu trả lời')+(' · '+esc(changes_text) if changes_text else '')+'</li>')
            sections.append('<details class="history-student"><summary>'+esc(p['name'])+' · '+(str(score)+'/'+str(len(qs))+' đúng' if p['finished'] is not None else 'Chưa nộp')+' · '+duration(p['elapsed'])+'</summary><p>Bắt đầu: <b>'+stamp(p['started'])+'</b><br>Nộp bài: <b>'+stamp(p['finished'])+'</b><br>Thời gian làm: <b>'+duration(p['elapsed'])+'</b>'+('<br>Còn '+str(pending)+' câu chờ ADMIN chấm.' if pending and p['finished'] else '')+'</p>'+''.join(content)+'<details><summary>Lịch sử trả lời · 200 thay đổi gần nhất</summary><ol>'+''.join(timeline)+'</ol><p>Tệp sao lưu giữ đầy đủ các thay đổi.</p></details></details>')
    storage=archive.status(code)
    save_text={'saved':'Đã lưu lâu dài','pending':'Đang đồng bộ bản lưu lâu dài','error':'Chưa đồng bộ được; hãy tải tệp sao lưu','local':'Đang lưu trên máy chủ; hãy tải tệp sao lưu'}[storage['state']]
    body='<div class="wrap race"><a class="btn" href="/member/race/history">← Lịch sử</a><h1>'+esc(r['title'])+' · '+code+'</h1><p>Tạo phòng: '+stamp(r['created'])+' · Bắt đầu: '+stamp(r['started'])+'</p><p>'+save_text+(' · '+stamp(storage['saved_at']) if storage['saved_at'] else '')+'</p><p><a class="btn primary" href="/member/race/history/'+code+'/export">⬇ Tải đề và toàn bộ bài làm (.json)</a> <a class="btn" href="/member/race/'+code+'">Mở phòng / Chấm tự luận</a></p><form method="post" action="/member/race/history/'+code+'/save"><input type="hidden" name="csrf" value="'+race.csrf()+'"><button class="btn">Lưu lâu dài ngay</button></form>'+''.join(sections)+('</div>')
    return page('Kết quả học sinh',body)


def export(code):
    owned_room(code,teacher())
    raw=json.dumps(archive.snapshot(code),ensure_ascii=False,indent=2)
    return Response(raw,mimetype='application/json',headers={'Content-Disposition':'attachment; filename="race-'+code+'.json"','Cache-Control':'no-store'})


def save_now(code):
    owned_room(code,teacher());race.check_csrf()
    if not archive.save(code):
        return page('Chưa lưu lâu dài','<div class="wrap race"><p>Chưa kết nối được nơi lưu lâu dài. Bài làm vẫn có trên máy chủ. Hãy tải bản sao lưu để giữ riêng.</p><a class="btn" href="/member/race/history/'+code+'/export">Tải bản sao lưu</a><a href="/member/race/history/'+code+'">← Quay lại</a></div>'),503
    return redirect('/member/race/history/'+code)


def import_backup():
    user=teacher();race.check_csrf()
    f=request.files.get('backup')
    if not f:abort(400)
    raw=f.read(12*1024*1024+1)
    if len(raw)>12*1024*1024:abort(413)
    try:
        data=json.loads(raw)
        code=data['room']['code']
        if data.get('version')!=1 or not re.fullmatch('[A-F0-9]{8}',code):raise ValueError()
        if archive.configured():
            remote=archive.index().get(code)
            if remote and remote.get('owner')!=user:abort(403)
        data['room']['owner']=user
        with race.db() as c:
            old=c.execute('SELECT owner FROM race_rooms WHERE code=?',(code,)).fetchone()
            if old and old['owner']!=user:abort(403)
        archive.restore(data)
        with race.db() as c:race.record_event(c,code,user,'import')
    except (ValueError,KeyError,TypeError):abort(400)
    return redirect('/member/race/history/'+code)


def page(title,body):
    return base.page(title,body+'<link rel="stylesheet" href="/static/practice-race.css?v=room50"><style>.history-student{border:1px solid #cbd5e1;border-radius:9px;padding:10px;margin:10px 0;background:#fff}.history-student>summary{cursor:pointer;font-weight:700}.history-student section{border-top:1px solid #ddd;padding:12px 0}.race table{width:100%;border-collapse:collapse}.race td,.race th{padding:8px;border-bottom:1px solid #ddd;text-align:left}.race form{display:flex;gap:8px;flex-wrap:wrap;align-items:end}.race label{display:flex;flex-direction:column}.race summary{overflow-wrap:anywhere}</style>')


def register():
    base.app.add_url_rule('/member/race/history','race_history',history)
    base.app.add_url_rule('/member/race/history/<code>','race_history_detail',detail)
    base.app.add_url_rule('/member/race/history/<code>/export','race_history_export',export)
    base.app.add_url_rule('/member/race/history/<code>/save','race_history_save',save_now,methods=['POST'])
    base.app.add_url_rule('/member/race/history/import','race_history_import',import_backup,methods=['POST'])
    base.app.add_url_rule('/api/race-storage-status','race_storage_status',lambda:jsonify(archive.health()))

    @base.app.before_request
    def restore_before_request():
        endpoint=request.endpoint or ''
        code=(request.view_args or {}).get('code')
        if endpoint in ('race_page','race_api','race_qr') and code:
            try:restore_code(code)
            except Exception:pass
        elif endpoint=='race_home' and request.method=='POST' and request.form.get('code'):
            code=re.sub('[^A-Z0-9]','',request.form['code'].upper())[:8]
            try:restore_code(code)
            except Exception:pass

    @base.app.after_request
    def archive_after_request(response):
        if response.status_code<400:
            for code in getattr(g,'race_archive_codes',set()):archive.enqueue(code,force=getattr(g,'race_archive_force',False))
            if request.endpoint=='race_api' and response.is_json:
                data=response.get_json();code=(request.view_args or {}).get('code')
                if isinstance(data,dict) and data.get('ok') and code and 'redirect' not in data:
                    data['storage']=archive.status(code)
                    if data.get('host'):data['history_url']='/member/race/history/'+code
                    if data['storage']['state'] in ('pending','error'):archive.enqueue(code)
                    response.set_data(json.dumps(data,ensure_ascii=False))
        if request.path.startswith('/member/race/history') or request.path=='/api/race-storage-status':response.headers['Cache-Control']='no-store, private'
        return response

    # Start connection checks in the serving worker, never during a preloaded import.
