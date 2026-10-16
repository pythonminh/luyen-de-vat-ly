"""Encrypted durable room snapshots on a separate Git branch.

No student names, answers or room titles are written as plaintext to GitHub.
SQLite remains the live store; encrypted snapshots survive service replacement.
"""
import base64
import json
import os
import queue
import re
import threading
import time
import urllib.parse
import zlib

from cryptography.fernet import Fernet

BRANCH = os.getenv('PRACTICE_RACE_ARCHIVE_BRANCH', 'race-results-archive')
_WRITE = threading.RLock()
_QUEUE = queue.Queue()
_PENDING = set()
_PENDING_LOCK = threading.Lock()
_STARTED = False
_VERIFIED = False
_ERROR = ''
_LAST_QUEUED = {}
_INDEX_CACHE = None
_INDEX_AT = 0
_PROBE_PID = None
_PROBE_AT = 0
_PROBE_THREAD = None
_PROBE_LOCK = threading.Lock()
RETRY_SECONDS = 60


def configured():
    import app
    return bool(os.getenv('PRACTICE_RACE_ARCHIVE_KEY') and app.github_token())


def cipher():
    return Fernet(os.environ['PRACTICE_RACE_ARCHIVE_KEY'].encode('ascii'))


def encrypt(data):
    return cipher().encrypt(zlib.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),9))


def decrypt(raw):
    compressed=cipher().decrypt(raw)
    # Bound decompression before parsing data received from the archive.
    decoder=zlib.decompressobj()
    plain=decoder.decompress(compressed,64*1024*1024+1)
    if len(plain)>64*1024*1024 or decoder.unconsumed_tail:
        raise ValueError('Tệp lưu quá lớn.')
    return json.loads(plain)


def api(path,method='GET',payload=None):
    import app
    return app.gh_api(path,method,payload)


def read_file(path, missing_ok=False):
    try:
        record=api('contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(BRANCH,safe=''))
    except RuntimeError as exc:
        if missing_ok and str(exc).startswith('GitHub API 404:'):
            return None,None
        raise
    sha=record['sha']
    if record.get('encoding')!='base64' or not record.get('content'):
        record=api('git/blobs/'+sha)
    return base64.b64decode(record['content']),sha


def put_file(path,data):
    _,sha=read_file(path,True)
    payload={'message':'Save encrypted practice history', 'branch':BRANCH,
             'content':base64.b64encode(encrypt(data)).decode('ascii')}
    if sha:payload['sha']=sha
    api('contents/'+urllib.parse.quote(path,safe='/'),'PUT',payload)


def ensure_branch():
    try:
        api('git/ref/heads/'+urllib.parse.quote(BRANCH,safe=''))
    except RuntimeError as exc:
        if not str(exc).startswith('GitHub API 404:'):raise
        import app
        head=api('git/ref/heads/'+urllib.parse.quote(app.BRANCH,safe=''))
        api('git/refs','POST',{'ref':'refs/heads/'+BRANCH,'sha':head['object']['sha']})


def index(fresh=False):
    global _INDEX_CACHE,_INDEX_AT
    if not configured():return {}
    if not fresh and _INDEX_CACHE is not None and time.time()-_INDEX_AT<60:return dict(_INDEX_CACHE)
    raw,_=read_file('history/index.enc',True)
    data=decrypt(raw) if raw else {}
    _INDEX_CACHE=data;_INDEX_AT=time.time()
    return dict(data)


def snapshot(code):
    import practice_race as race
    with race.db() as c:
        c.execute('BEGIN')
        room=c.execute('SELECT * FROM race_rooms WHERE code=?',(code,)).fetchone()
        if not room:raise ValueError('Không tìm thấy phòng.')
        data={'version':1,'room':dict(room),'saved_at':time.time()}
        for table in ('race_players','race_marks','race_meta','race_events'):
            data[table]=[dict(r) for r in c.execute('SELECT * FROM '+table+' WHERE room=?',(code,))]
        state=c.execute('SELECT revision FROM race_archive_state WHERE room=?',(code,)).fetchone()
        data['revision']=state[0] if state else 0
        return data


def room_summary(data):
    r=data['room'];players=data['race_players']
    return {'code':r['code'],'owner':r['owner'],'title':r['title'],'path':r['path'],
            'created':r['created'],'started':r['started'],'state':r['state'],
            'players':len(players),'students':[p['name'] for p in players],'submitted':sum(p['finished'] is not None for p in players),
            'saved_at':data['saved_at']}


def save(code):
    global _VERIFIED,_ERROR,_INDEX_CACHE,_INDEX_AT
    if not configured():return False
    import practice_race as race
    try:
        with _WRITE:
            data=snapshot(code)
            with race.db() as c:
                state=c.execute('SELECT saved_revision FROM race_archive_state WHERE room=?',(code,)).fetchone()
            if state and state[0]>=data['revision'] and data['revision']>0:return True
            ensure_branch()
            put_file('history/rooms/'+code+'.enc',data)
            summaries=index(fresh=True)
            summaries[code]=room_summary(data)
            put_file('history/index.enc',summaries)
            _INDEX_CACHE=summaries;_INDEX_AT=time.time()
            with race.db() as c:
                c.execute('INSERT INTO race_archive_state(room,revision,saved_revision,saved_at,error) VALUES (?,?,?,?,?) ON CONFLICT(room) DO UPDATE SET saved_revision=excluded.saved_revision,saved_at=excluded.saved_at,error=?',
                          (code,data['revision'],data['revision'],time.time(),'',''))
            _VERIFIED=True;_ERROR=''
            return True
    except Exception as exc:
        _ERROR=type(exc).__name__
        with race.db() as c:
            c.execute('UPDATE race_archive_state SET error=? WHERE room=?',('Chưa đồng bộ được bản lưu lâu dài. Dữ liệu vẫn đang có trên máy chủ; hãy tải bản sao lưu.',code))
        return False


def load(code):
    if not configured() or not re.fullmatch(r'[A-F0-9]{8}',code):return None
    raw,_=read_file('history/rooms/'+code+'.enc',True)
    if not raw:return None
    data=decrypt(raw)
    if data.get('version')!=1 or data.get('room',{}).get('code')!=code:raise ValueError('Bản lưu không hợp lệ.')
    return data


def restore(data):
    """Import authenticated snapshots without replacing a live room."""
    import practice_race as race
    code=data['room']['code']
    with race.db() as c:
        if c.execute('SELECT 1 FROM race_rooms WHERE code=?',(code,)).fetchone():return
        columns=('code','owner','title','path','pool','blueprint','duration','state','created','started','shown')
        c.execute('INSERT INTO race_rooms('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',tuple(data['room'][k] for k in columns))
        tables={'race_players':('room','user','name','questions','answers','started','finished','correct','elapsed'),
                'race_marks':('room','user','pos','ok'),'race_meta':('room','config'),
                'race_events':('room','user','at','kind','payload')}
        for table,cols in tables.items():
            for row in data.get(table,[]):
                if row.get('room')!=code:raise ValueError('Mã phòng trong bản lưu không khớp.')
                c.execute('INSERT INTO '+table+'('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')',tuple(row[k] for k in cols))
        revision=int(data.get('revision',0))
        c.execute('INSERT OR REPLACE INTO race_archive_state VALUES (?,?,?,?,?)',(code,revision,revision,data.get('saved_at'),''))


def status(code):
    import practice_race as race
    with race.db() as c:
        r=c.execute('SELECT * FROM race_archive_state WHERE room=?',(code,)).fetchone()
    if not configured():return {'state':'local','saved_at':None}
    if not r:return {'state':'pending','saved_at':None}
    return {'state':'error' if r['error'] else 'saved' if r['saved_revision']>=r['revision'] else 'pending','saved_at':r['saved_at']}


def _worker():
    while True:
        code=_QUEUE.get()
        # Coalesce simultaneous student submissions into one current snapshot.
        threading.Event().wait(1)
        try:save(code)
        except Exception:pass
        finally:
            with _PENDING_LOCK:_PENDING.discard(code)
            _QUEUE.task_done()
            try:state=status(code)['state']
            except Exception:state='error'
            if state=='pending':enqueue(code,force=True)
            elif state=='error':
                timer=threading.Timer(RETRY_SECONDS,lambda code=code:enqueue(code,force=True));timer.daemon=True;timer.start()


def enqueue(code,force=False):
    global _STARTED
    if not configured():return
    with _PENDING_LOCK:
        now=time.time()
        if code in _PENDING:return
        if not force and now-_LAST_QUEUED.get(code,0)<RETRY_SECONDS:return
        _LAST_QUEUED[code]=now
        _PENDING.add(code)
        if not _STARTED:
            threading.Thread(target=_worker,daemon=True,name='race-archive').start();_STARTED=True
        _QUEUE.put(code)


def probe():
    global _VERIFIED,_ERROR
    if not configured():return
    try:
        with _WRITE:
            ensure_branch()
            put_file('history/storage-check.enc',{'version':1,'check':'encrypted-history','at':time.time()})
            raw,_=read_file('history/storage-check.enc')
            if decrypt(raw).get('check')!='encrypted-history':raise ValueError('Kiểm tra bản lưu thất bại.')
            _VERIFIED=True;_ERROR=''
    except Exception as exc:_ERROR=type(exc).__name__


def start_probe():
    global _PROBE_PID,_PROBE_AT,_PROBE_THREAD
    if not configured() or _VERIFIED:return
    with _PROBE_LOCK:
        pid=os.getpid()
        if _PROBE_PID==pid and ((_PROBE_THREAD and _PROBE_THREAD.is_alive()) or time.time()-_PROBE_AT<60):return
        _PROBE_PID=pid;_PROBE_AT=time.time()
        _PROBE_THREAD=threading.Thread(target=probe,daemon=True,name='race-storage-check')
        _PROBE_THREAD.start()


def health():
    start_probe()
    return {'configured':configured(),'verified':_VERIFIED,'error':bool(_ERROR)}
