# -*- coding: utf-8 -*-
"""Small, idempotent practice leaderboard backed by optional Render PostgreSQL."""
import os
import threading
from datetime import datetime, timezone
from flask import jsonify, request
import app as base

_lock = threading.Lock()
_ready = False

def _connect():
    url = str(os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return None
    import psycopg
    return psycopg.connect(url, connect_timeout=5, autocommit=False)

def _ensure(conn):
    global _ready
    if _ready:
        return
    with _lock:
        if _ready:
            return
        with conn.cursor() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS practice_attempts (
                attempt_id VARCHAR(64) PRIMARY KEY,
                username VARCHAR(120) NOT NULL,
                lesson_path TEXT NOT NULL,
                total INTEGER NOT NULL CHECK(total > 0),
                correct INTEGER NOT NULL CHECK(correct >= 0 AND correct <= total),
                longest_streak INTEGER NOT NULL CHECK(longest_streak >= 0),
                elapsed_seconds INTEGER NOT NULL CHECK(elapsed_seconds >= 0),
                completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""")
            c.execute("""
            CREATE INDEX IF NOT EXISTS idx_practice_attempts_user_path
            ON practice_attempts(username, lesson_path)
            """)
        conn.commit()
        _ready = True

def username(m):
    return str((m or {}).get('username') or '').strip().casefold()

def _summary(conn, user, path):
    with conn.cursor() as c:
        c.execute("""SELECT COUNT(*), MAX(correct::numeric / NULLIF(total,0) * 10),
                 MAX(longest_streak) FROM practice_attempts
                 WHERE username=%s AND lesson_path=%s""", (user,path))
        count, score, streak = c.fetchone()
        # Fastest completion is compared only within equal quiz length and best score.
        c.execute("""SELECT total, MIN(elapsed_seconds) FROM practice_attempts
                 WHERE username=%s AND lesson_path=%s AND total = (
                    SELECT total FROM practice_attempts WHERE username=%s AND lesson_path=%s
                    ORDER BY completed_at DESC, attempt_id DESC LIMIT 1
                 ) AND correct::numeric / total = (
                    SELECT MAX(correct::numeric / total) FROM practice_attempts
                    WHERE username=%s AND lesson_path=%s
                      AND total = (
                        SELECT total FROM practice_attempts WHERE username=%s AND lesson_path=%s
                        ORDER BY completed_at DESC, attempt_id DESC LIMIT 1
                      )
                 )
                 GROUP BY total LIMIT 1""",(user,path,user,path,user,path,user,path))
        row=c.fetchone()
    return {'attempts':int(count or 0),'best_score':round(float(score or 0),2),
            'best_streak':int(streak or 0),
            'fastest_seconds':(int(row[1]) if row else None),
            'fastest_total':(int(row[0]) if row else None)}

def finish_current(m, session):
    user=username(m)
    path=str(session.get('practice_path') or '')
    ids=list(session.get('practice_ids') or [])
    pos=int(session.get('practice_pos') or 0)
    done=list(session.get('practice_done') or [])
    if not user or not path or not ids or pos<len(ids) or len(done)!=len(ids):
        return None
    attempt=str(session.get('practice_attempt_id') or '')
    if not attempt or len(attempt)>64:
        return None
    right=sum(bool(x.get('ok')) for x in done)
    longest=run=0
    for x in done:
        run=(run+1) if x.get('ok') else 0
        longest=max(longest,run)
    import time
    elapsed=max(0,int(time.time()-float(session.get('practice_started_at') or time.time())))
    conn=_connect()
    if conn is None:
        return None
    try:
        _ensure(conn)
        with conn.cursor() as c:
            c.execute("""INSERT INTO practice_attempts
                (attempt_id,username,lesson_path,total,correct,longest_streak,elapsed_seconds)
                VALUES(%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(attempt_id) DO NOTHING""",
                (attempt,user,path,len(ids),right,longest,elapsed))
        conn.commit()
        return _summary(conn,user,path)
    finally:
        conn.close()

def lookup_current(m, session):
    user=username(m)
    path=str(session.get('practice_path') or '')
    if not user or not path:
        return None
    conn=_connect()
    if conn is None:
        return None
    try:
        _ensure(conn)
        return _summary(conn,user,path)
    finally:
        conn.close()

@base.app.get('/member/practice/records')
def current_records():
    m=base.member_current()
    if not m:
        return jsonify(ok=False,error='Cần đăng nhập.'),401
    path=str(base.session.get('practice_path') or '')
    if not path or not base.can_practice(m,path):
        return jsonify(ok=False,error='Không có quyền xem lượt luyện này.'),403
    try:
        data=lookup_current(m,base.session)
        if data is None:
            return jsonify(ok=False,storage='local',error='Chưa kết nối database, kỷ lục đang lưu trên thiết bị.')
        return jsonify(ok=True,storage='database',record=data)
    except Exception:
        return jsonify(ok=False,storage='local',error='Chưa truy vấn được dữ liệu máy chủ.'),503
