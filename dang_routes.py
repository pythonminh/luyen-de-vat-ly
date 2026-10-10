# -*- coding: utf-8 -*-
"""Member question browser: show every question before building a test."""
from __future__ import annotations
import base64
import hashlib
import html
import io
import ipaddress
import json
import os
import posixpath
import re
import socket
import threading
import time
import zipfile
from xml.etree import ElementTree as ET
import urllib.error
import urllib.parse
import urllib.request
from flask import request, jsonify, redirect, session
from app import TOKEN, _safe_repo_file, admin_current, app, can_access, can_manage_bank, can_practice, can_view, dang_view_url, develop_reference_html, dup_index_by_question, edit_tex_href, find_duplicate_groups, github_blob_url, github_put_text, html_question, index_data, lesson_switch_html, login_url, member_current, muc_label, nest_developments, nguon_html, norm_muc, page, parse_lesson_questions, parse_questions, read_tex, sort_ids_by_kind, sort_questions_by_kind, sort_questions_for_study, tex_without_questions, view_only_notice_html

_FILL_JOBS = {}
_FILL_LIVE = set()
_FILL_LOCK = threading.Lock()
_FILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'fill-jobs')


def _fill_job_ok(job):
    return bool(re.fullmatch(r'[0-9a-f]{8,40}', str(job or '')))


def _fill_status_path(job):
    return os.path.join(_FILL_DIR, job + '.json')


def _fill_payload_path(job):
    return os.path.join(_FILL_DIR, job + '.payload.json')


def _fill_write_json(path, obj):
    os.makedirs(_FILL_DIR, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def _fill_read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _fill_job_gc():
    now = time.time()
    with _FILL_LOCK:
        dead = [k for k, v in _FILL_JOBS.items() if now - float(v.get('ts') or now) > 900 and k not in _FILL_LIVE]
        for k in dead:
            _FILL_JOBS.pop(k, None)
    if not os.path.isdir(_FILL_DIR):
        return
    for name in os.listdir(_FILL_DIR):
        path = os.path.join(_FILL_DIR, name)
        try:
            age = now - os.path.getmtime(path)
        except OSError:
            continue
        if age < 900:
            continue
        if name.endswith('.payload.json') and age < 1200:
            continue
        try:
            os.remove(path)
        except OSError:
            pass


def _fill_progress(job, note):
    if not job:
        return
    now = time.time()
    with _FILL_LOCK:
        rec = dict(_FILL_JOBS.get(job) or {})
        started = float(rec.get('started') or rec.get('ts') or now)
        rec.update(state='run', ts=now, started=started, note=str(note or '')[:240], result=None)
        _FILL_JOBS[job] = rec
    try:
        _fill_write_json(_fill_status_path(job), rec)
    except Exception:
        pass


def _start_fill_thread(job, payload):
    def work():
        try:
            with app.app_context():
                body_in = dict(payload or {})
                body_in['_job'] = job
                resp = _dang_fill_work(body_in)
                if isinstance(resp, tuple):
                    resp = resp[0]
                body = resp.get_json(silent=True) if resp is not None else None
            if not isinstance(body, dict):
                body = {'ok': False, 'error': 'Không đọc được kết quả.'}
        except Exception as e:
            body = {'ok': False, 'error': str(e)}
        with _FILL_LOCK:
            _FILL_JOBS[job] = {'state': 'done', 'ts': time.time(), 'result': body}
            _FILL_LIVE.discard(job)
        try:
            _fill_write_json(_fill_status_path(job), {'state': 'done', 'ts': time.time(), 'result': body})
        except Exception:
            pass
        try:
            os.remove(_fill_payload_path(job))
        except OSError:
            pass

    threading.Thread(target=work, daemon=True).start()


def _ensure_fill(job):
    if not _fill_job_ok(job):
        return
    with _FILL_LOCK:
        if job in _FILL_LIVE:
            return
        rec = _FILL_JOBS.get(job) or {}
        if rec.get('state') == 'done':
            return
        payload = _fill_read_json(_fill_payload_path(job))
        if not payload:
            return
        _FILL_LIVE.add(job)
    _start_fill_thread(job, payload)


def _spawn_dang_fill(data):
    """Chạy AI nền. Phiên ghi ra đĩa để máy khởi động lại vẫn nối được."""
    _fill_job_gc()
    job = hashlib.sha1(f'{time.time()}:{id(data)}'.encode()).hexdigest()[:16]
    payload = dict(data or {})
    payload.pop('background', None)
    with _FILL_LOCK:
        running = sum(1 for v in _FILL_JOBS.values() if v.get('state') == 'run')
        if running >= 2:
            return jsonify(ok=False, error='Đang có phiên AI chạy. Đợi xong rồi bấm lại.'), 429
        now = time.time()
        _FILL_JOBS[job] = {'state': 'run', 'ts': now, 'started': now, 'note': 'Đang đọc nguồn…', 'result': None}
    try:
        _fill_write_json(_fill_payload_path(job), payload)
        _fill_write_json(_fill_status_path(job), {'state': 'run', 'ts': now, 'started': now, 'note': 'Đang đọc nguồn…', 'result': None})
    except Exception as e:
        return jsonify(ok=False, error='Không mở được phiên: ' + str(e)), 500
    _ensure_fill(job)
    return jsonify(ok=True, pending=True, job=job)


_STATS_CACHE = {}
_STATS_TTL = 300
_QID_CACHE = {}
_QID_TTL = 300

def _esc(s):
    return html.escape(str(s), quote=True)

def _same_dang(a, b):
    return str(a or '').strip() == str(b or '').strip()

def _stats_for(path):
    now = time.time(); hit = _STATS_CACHE.get(path)
    if hit and now-hit[0] < _STATS_TTL: return hit[1]
    _, tex = read_tex(path); qs = parse_questions(tex); stats = {}
    for q in qs:
        if str(q.get('develop_from') or '').strip():
            continue
        d=(q.get('dang') or 'Chưa phân dạng').strip() or 'Chưa phân dạng'; k=q.get('kind') or 'TL'
        stats.setdefault(d, {'TN':0,'DS':0,'TLN':0,'TL':0})
        stats[d][k]=stats[d].get(k,0)+1
    _STATS_CACHE[path]=(now,stats); return stats

def _qid_entries_for(path):
    now = time.time(); hit = _QID_CACHE.get(path)
    if hit and now-hit[0] < _QID_TTL: return hit[1]
    _, tex = read_tex(path); qs = parse_questions(tex); rows = []
    for q in qs:
        qid=str(q.get('id') or '').strip()
        if not qid:
            continue
        dang=(q.get('dang') or 'Chưa phân dạng').strip() or 'Chưa phân dạng'
        try: idx=int(q.get('idx'))
        except (TypeError, ValueError):
            continue
        rows.append({'id':qid,'path':path,'dang':dang,'idx':idx,'kind':str(q.get('kind') or 'TL')})
    _QID_CACHE[path]=(now,rows); return rows

def find_questions_by_id(needle, member, limit=40):
    needle=str(needle or '').strip().lower()
    if len(needle)<2:
        return []
    out=[]
    for x in (index_data().get('lessons') or []):
        if not isinstance(x, dict):
            continue
        path=str(x.get('path') or x.get('file') or '').strip()
        if not path.startswith('ngan-hang/') or not can_view(member, path):
            continue
        try:
            rows=_qid_entries_for(path)
        except Exception:
            continue
        title=str(x.get('BaiHoc') or x.get('De') or (path.rsplit('/',2)[-2] if '/' in path else path))
        mon=str(x.get('Mon') or ''); lop=str(x.get('Lop') or '')
        for row in rows:
            if needle not in row['id'].lower():
                continue
            item=dict(row); item.update(title=title, mon=mon, lop=lop)
            out.append(item)
            if len(out)>=limit:
                return out
    return out

def qid_results_html(needle, member):
    hits=find_questions_by_id(needle, member)
    if not hits:
        return ''
    logged=bool(member)
    cards=[]
    for h in hits:
        view=('/member/dang?path='+urllib.parse.quote(h['path'],safe='')
              +'&dang='+urllib.parse.quote(h['dang'],safe='')
              +'&id='+urllib.parse.quote(h['id'],safe=''))
        do=''
        if logged and can_practice(member, h.get('path')):
            do=(f"<form method='post' action='/member/start-selected' style='display:inline'>"
                f"<input type='hidden' name='path' value='{_esc(h['path'])}'>"
                f"<input type='hidden' name='dang' value='{_esc(h['dang'])}'>"
                f"<input type='hidden' name='qid' value='{int(h['idx'])}'>"
                f"<input type='hidden' name='ai_review' value='0'>"
                f"<button class='btn primary' type='submit'>▶ Làm câu này</button></form> ")
        kind=html.escape(h.get('kind') or '?')
        cards.append(
            f"<div class='card'><b><span class='qid'>ID {html.escape(h['id'])}</span></b>"
            f"<div class='meta'>{html.escape(h.get('mon') or '')} · Lớp {html.escape(h.get('lop') or '')} · {html.escape(h.get('title') or '')}</div>"
            f"<div><span class='tag'>{kind}</span><span class='tag'>{html.escape(h['dang'])}</span></div>"
            f"<p style='margin:8px 0 0'>{do}<a class='btn' href='{_esc(view)}'>👁 Xem câu</a></p></div>"
        )
    return ("<div class='panel' style='margin-top:10px'><div class='head'>🔎 Câu theo ID <span class='tag'>"
            +str(len(hits))+"</span></div><div class='body'><div class='cards'>"+''.join(cards)+"</div></div></div>")

@app.get('/member/dang-stats')
def member_dang_stats():
    m=member_current()
    path=request.args.get('path','').strip()
    if not path or not can_view(m,path):return jsonify(ok=False,error='Không có quyền xem'),403
    try:return jsonify(ok=True,stats=_stats_for(path))
    except Exception as exc:return jsonify(ok=False,error=str(exc)),500

@app.get('/member/dang-stats-all')
def member_dang_stats_all():
    m=member_current()
    out={}
    for x in (index_data().get('lessons') or []):
        if not isinstance(x, dict):
            continue
        path=str(x.get('path') or x.get('file') or '').strip()
        if not path.startswith('ngan-hang/') or not can_view(m, path):
            continue
        try:
            out[path]=_stats_for(path)
        except Exception:
            continue
    return jsonify(ok=True, stats=out)


def _sol_block(q):
    sol=(q.get('solution') or '').strip()
    src=q.get('src') or ''
    inner=html_question(sol, src) if sol else "<div class='muted'>Chưa có lời giải trong file TEX.</div>"
    return f"<div class='solution'><b>📖 Lời giải</b><div>{inner}</div></div>"

_KIND_PARTS = (
    ('TN', 'Phần 1. Trắc nghiệm'),
    ('DS', 'Phần 2. Đúng/Sai'),
    ('TLN', 'Phần 3. Trả lời ngắn'),
    ('TL', 'Phần 4. Tự luận'),
)


def _study_cards(selected, path, dmap, show_solution, highlight_id):
    """Trong từng dạng: Phần 1 TN, Phần 2 ĐS, Phần 3 TLN, Phần 4 TL."""
    labels = dict(_KIND_PARTS)
    dangs = []
    for q in selected or []:
        d = str(q.get('dang') or '').strip() or 'Chưa phân dạng'
        if d not in dangs:
            dangs.append(d)
    multi = len(dangs) > 1
    bits = []
    bucket = []
    prev_d = None
    prev_k = None

    def flush():
        if not bucket:
            return
        kind = prev_k if prev_k in labels else 'TL'
        bits.append(
            f"<h2 class='kindpart k-{html.escape(kind)}'>{html.escape(labels.get(kind, labels['TL']))}"
            f" <span class='tag'>{len(bucket)} câu</span></h2>"
        )
        n = len(bucket)
        for seq, q in enumerate(bucket, 1):
            bits.append(_question_card(
                q, seq, n, q.get('src') or path, (dmap or {}).get(q.get('idx')),
                show_solution=show_solution, highlight_id=highlight_id,
            ))

    for q in selected or []:
        d = str(q.get('dang') or '').strip() or 'Chưa phân dạng'
        k = str(q.get('kind') or 'TL')
        if k not in labels:
            k = 'TL'
        if bucket and (k != prev_k or d != prev_d):
            flush()
            bucket = []
        if multi and d != prev_d:
            bits.append(f"<h2 class='dangpart'>{html.escape(d)}</h2>")
        bucket.append(q)
        prev_d, prev_k = d, k
    flush()
    return ''.join(bits)


def _question_card(q, seq, total, path='', dup=None, show_solution=False, highlight_id='', preview_only=False):
    n=q.get('idx',0); kind=q.get('kind','TL'); level=q.get('level','H'); text=q.get('text','')
    qid=str(q.get('id') or '').strip() or '—'
    cau=q.get('cau') or (n+1); line=int(q.get('line') or 0)
    src=str(q.get('src') or path or '').replace('\\','/')
    badge={'TN':'TN · Trắc nghiệm','DS':'ĐS · Đúng / Sai','TLN':'TLN · Trả lời ngắn','TL':'TL · Tự luận'}.get(kind,kind)
    muc=norm_muc(level) or 'H'
    options=''
    sol_html=''
    if kind=='TN':
        letters='ABCD'
        bits=[]
        for i,o in enumerate((q.get('options') or [])[:4]):
            ok=show_solution and bool(o.get('correct'))
            mark=" <span class='okmark'>Đáp án đúng</span>" if ok else ''
            bits.append(f"<div class='opt{' ok' if ok else ''}'><b>{letters[i]}.</b> {html_question(o.get('text',''), src)}{mark}</div>")
        options='<div class="opts">'+''.join(bits)+'</div>'
    elif kind=='DS':
        st=q.get('statements') or []
        bits=['<div class="tf-colhead"><span></span><span></span><span class="tf-h yes">Đúng</span><span class="tf-h no">Sai</span></div>']
        labs='ABCD'
        for i,o in enumerate(st):
            txt=html_question(o.get('text','') if isinstance(o,dict) else o, src)
            yes=bool((o or {}).get('correct')) if isinstance(o,dict) else False
            lab=labs[i] if i<4 else str(i+1)
            cls=' ok' if show_solution and yes else (' noans' if show_solution else '')
            y_on=" on" if show_solution and yes else ""
            n_on=" on" if show_solution and not yes else ""
            bits.append(f"<div class='tf{cls}'><span class='tflab'>{lab}</span><div class='tf-text'>{txt}</div><span class='tf-box yes{y_on}'></span><span class='tf-box no{n_on}'></span></div>")
        options='<div class="qbody ds"><div class="qfig" hidden></div><div class="qtf"><div class="tfgrid">'+''.join(bits)+'</div></div></div>'
    elif kind=='TLN':
        options="<div class='answerline'>✎ Học viên nhập đáp án khi làm bài</div>"
        if show_solution:
            ans=str(q.get('answer') or '').strip()
            options+=f"<div class='answerline'><b>Đáp án:</b> {html_question(ans, src) if ans else '—'}</div>"
    else:
        options="<div class='answerline'>✎ Câu tự luận</div>" if member_current() else "<div class='answerline'>✎ Câu tự luận · 🔒 Đăng nhập rồi làm bài mới xem lời giải</div>"
    if show_solution:
        sol_html=_sol_block(q)
    gh=''
    tex_badge=f"<span class='metafile'>TEX Câu {html.escape(str(cau))} · STT file {n+1}</span>"
    manage = can_manage_bank() and not preview_only
    if preview_only:
        tex_badge="<span class='badge'>Xem trước</span>"
    elif manage and src:
        try:
            q_idx=int(q.get('file_idx') if q.get('file_idx') is not None else n)
        except (TypeError, ValueError):
            q_idx=int(n or 0)
        view_path=str(request.args.get('path') or src or '').replace('\\','/')
        back=dang_view_url(view_path, request.args.get('dang') or '', request.args.get('kind') or '', request.args.get('muc') or '')
        if qid and qid != '—':
            back += '&id='+urllib.parse.quote(qid, safe='')
        back += '&idx='+str(q_idx)
        edit_href=edit_tex_href(src, line, back)
        tex_badge=f"<a class='btn mini metafile' href='{_esc(edit_href)}'>✏️ TEX Câu {html.escape(str(cau))} · STT file {n+1}</a>"
        if line:
            gh=f" <a class='btn mini' href='{_esc(github_blob_url(src))}#L{line}' target='_blank' rel='noopener'>GitHub dòng {line}</a>"
    dup=dup or {}
    hid=str(highlight_id or '').strip().lower()
    try: fi=int(q.get('file_idx') if q.get('file_idx') is not None else n)
    except (TypeError, ValueError): fi=int(n or 0)
    drop_key=_esc(src+'||'+str(fi))
    rw=''
    if manage:
        rw=(f"<details class='qtools-fold'><summary>🛠 Công cụ chỉnh sửa câu hỏi</summary><div class='rwbar'><button type='button' class='btn mini primary rwreshuf' data-drop='{drop_key}'>🎲 Đổi đề bài mới</button><button type='button' class='btn mini rwsim' data-drop='{drop_key}'>📘 Phát triển từ câu</button>"
            f"<button type='button' class='btn mini rwgo' data-drop='{drop_key}'>✍️ AI viết lại đề + lời giải</button>"
            f"<button type='button' class='btn mini rwedit' data-drop='{drop_key}'>✏️ Sửa đề / lời giải</button>"
            f"<button type='button' class='btn mini rwimgs' data-drop='{drop_key}'>🖼 Ảnh thư mục</button>"
            f"<button type='button' class='btn mini rwtikzbtn' data-drop='{drop_key}'>📐 Mã TikZ</button>"
            f"<button type='button' class='btn mini rwnbprompt' data-drop='{drop_key}'>✨ Prompt ảnh vở + Phiếu</button>"
            f"<button type='button' class='btn mini rwcanva' data-drop='{drop_key}'>🎲 Luyện đổi số</button>"
            f"<button form='qdel' class='btn mini red' type='submit' name='drop' value='{drop_key}' onclick=\"return confirm('Xóa vĩnh viễn câu này khỏi file TEX? Không hoàn tác trên trang này.')\">🗑 Xóa câu</button>"
            "<div class='rwout'></div></div></details>")
    dcls=' dupcard' if dup.get('label') else ''
    if hid and qid.lower()==hid:
        dcls+=' qhit'
    role=''
    if dup.get('label')=='CÙNG ĐỀ':
        role=' · thừa' if dup.get('extra') else (' · giữ' if dup.get('keep') else '')
    dtag=f"<span class='dupbadge'>{html.escape(dup.get('label') or '')} · nhóm {','.join(str(x) for x in dup.get('n') or [])}{role}</span>" if dup.get('label') else ''
    xoa=''
    if can_manage_bank() and dup.get('extra'):
        if dup.get('tick'):
            xoa=f" <label class='dupx'><input form='dupdel' type='checkbox' name='drop' value='{drop_key}' checked> Xóa bản trùng này</label>"
        else:
            xoa=f" <label class='dupx'><input form='dupdel' type='checkbox' name='drop' value='{drop_key}' data-cung='1'> Xóa bản cùng đề này</label>"
    find=_esc(f"{qid} {cau} {text} {q.get('nguon') or ''} {dup.get('label') or ''}".lower())
    qlab = (
        f"<span class='qbadge'>Câu {seq}/{total}</span>"
        if preview_only
        else f"<label class='qcheck'><input type='checkbox' name='qid' value='{n}'><span>Câu {seq}/{total}</span></label>"
    )
    return (f"<article class='qcard{dcls}' data-drop='{drop_key}' data-idx='{fi}' data-find='{find}' data-qid='{_esc(qid.lower())}' data-dup='{1 if dup.get('label') else 0}' data-kind='{kind}'><div class='qhead'>{qlab}"
            f"<span class='qid'>ID: {html.escape(qid)}</span>{dtag}{xoa}<span class='badge'>{html.escape(badge)}</span>"
            f"{tex_badge}{gh}{nguon_html(q)}<span class='level muc-{muc}'>Mức {html.escape(muc_label(muc))}</span>"
            + (f"<button type='button' class='btn mini primary rwreshuf' data-drop='{drop_key}'>🎲 Đổi đề bài mới</button>" if manage else "")
            + "</div>"
            f"<div class='qheadline'><span class='qbadge'>Câu {seq}</span><div class='qstem'>{html_question(text, src)}</div></div>{options}{develop_reference_html(q, src)}{rw}{sol_html}</article>")


@app.after_request
def _question_card_clean_styles(response):
    if request.method != 'GET' or request.path != '/member/dang' or response.status_code != 200 or response.mimetype != 'text/html':
        return response
    try:
        body=response.get_data(as_text=True)
        if '</head>' in body and 'question-card-clean-css' not in body:
            body=body.replace('</head>', "<style id=\"question-card-clean-css\">\n.qcard{padding:14px!important;border-radius:13px!important;margin:12px 0!important;max-width:100%;overflow-wrap:break-word}.qcard .solution{overflow-x:auto;word-break:normal!important;overflow-wrap:break-word!important}.qcard mjx-container{word-break:normal!important;overflow-wrap:normal!important;white-space:nowrap!important}.qcard mjx-container[display='true']{display:block!important;max-width:100%;overflow-x:auto}\n.qcard .qhead{display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding-bottom:10px;border-bottom:1px solid #e1e8f0}\n.qcard .qhead .btn{padding:6px 9px;font-size:12px}\n.qcard .qhead .metafile{max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n.qcard .qheadline{margin:14px 0 12px}\n.qcard .qheadline .qbadge{display:none}\n.qcard .qstem{font-size:17px!important;line-height:1.65!important}\n.qcard .qtools-fold{margin-top:14px;border:1px solid #d2e1ef;border-radius:10px;background:#f7fbff;overflow:hidden}\n.qcard .qtools-fold>summary{padding:12px 14px;cursor:pointer;color:#175a9d;font-weight:800;font-size:13px;list-style:none;min-height:44px}\n.qcard .qtools-fold>summary:before{content:'▸ ';margin-right:5px}\n.qcard .qtools-fold[open]>summary:before{content:'▾ '}\n.qcard .qtools-fold>summary::-webkit-details-marker{display:none}\n.qcard .qtools-fold .rwbar{border:0!important;margin:0!important;padding:10px!important;background:transparent!important;display:flex;gap:7px;flex-wrap:wrap}\n.qcard .qtools-fold .rwbar>.btn{font-size:12px;min-height:38px}\n.qcard .qtools-fold .rwout{width:100%;flex-basis:100%}\n@media(max-width:700px){.qcard{padding:10px!important;max-width:100%!important}.qcard .qhead{flex-wrap:wrap!important}.qcard .qhead>*{min-width:0;max-width:100%}.qcard .qhead .qid,.qcard .qhead .level{font-size:11px}.qcard .qhead .metafile{max-width:100%;white-space:normal}.qcard .qheadline,.qcard .qstem,.qcard .opt,.qcard .opts{min-width:0!important;max-width:100%!important;overflow-wrap:anywhere!important;word-break:break-word!important;white-space:normal!important}.qcard .opt{display:block!important}.qcard .qstem{font-size:16px!important}.qcard .qtools-fold .rwbar{display:grid;grid-template-columns:1fr 1fr;gap:6px}.qcard .qtools-fold .rwbar>.btn{white-space:normal;min-height:44px}.qcard .qtools-fold .rwout{grid-column:1/-1}}\n</style>"+'</head>', 1)
            response.set_data(body)
            response.headers.pop('Content-Length',None)
    except Exception:
        pass
    return response


@app.after_request
def _admin_ai_deep_link(response):
    """Expose the existing AI gap/fill/rewrite tools from the VIP practice screen."""
    if request.path != '/member/dang' or request.method != 'GET' or response.status_code != 200:
        return response
    if response.mimetype != 'text/html' or not can_manage_bank():
        return response
    action = str(request.args.get('admin_action') or '')
    if action not in {'gap', 'fill', 'rewrite'}:
        return response
    script = """<script>
document.addEventListener('DOMContentLoaded',function(){
  const fold=document.querySelector('.admindang-fold');
  if(fold)fold.open=true;
  if(__ACTION__==='rewrite'){
    const card=document.querySelector('.qcard');
    const tools=card&&card.querySelector('.qtools-fold');
    if(tools){tools.open=true;tools.scrollIntoView({block:'center'});}
    else if(card)card.scrollIntoView({block:'center'});
    return;
  }
  const id=__ACTION__==='gap'?'aiGap':'aiFill';
  const b=document.getElementById(id);
  if(b){b.scrollIntoView({block:'center'});b.focus();b.click();}
});
</script>""".replace('__ACTION__', json.dumps(action))
    try:
        body=response.get_data(as_text=True)
        if '</body>' in body:
            response.set_data(body.replace('</body>',script+'</body>',1))
            response.headers.pop('Content-Length',None)
    except Exception:
        pass
    return response

@app.get('/member/dang')
def member_dang():
    m=member_current()
    path=request.args.get('path','').strip(); dang=request.args.get('dang','').strip()
    kind_filter=str(request.args.get('kind') or '').strip().upper()
    muc=norm_muc(request.args.get('muc') or '')
    if kind_filter not in {'TN','DS','TLN','TL'}:
        kind_filter=''
    if not path:return redirect('/member')
    if not can_view(m,path):
        if not m:
            return redirect(login_url('/member/dang?path='+urllib.parse.quote(path,safe='')+'&dang='+urllib.parse.quote(dang,safe='')))
        return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try:
        qs = parse_lesson_questions(path)
        if not qs:
            _, tex = read_tex(path); qs = nest_developments(parse_questions(tex))
    except Exception as exc:
        return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div></div></div></div>")
    if dang:
        selected=[q for q in qs if _same_dang(q.get('dang'), dang)]
        if not selected and dang == 'Chưa phân dạng':
            selected=[q for q in qs if not str(q.get('dang') or '').strip() or _same_dang(q.get('dang'), dang)]
    else:
        selected=list(qs)
    notice_extra=''
    if dang and not selected and qs:
        selected=list(qs)
        notice_extra=f"<div class='notice'>Không khớp đúng tên dạng «{_esc(dang)}» — đang hiện {len(selected)} câu trong file.</div>"
    if kind_filter:
        selected=[q for q in selected if str(q.get('kind') or '')==kind_filter]
    pool=list(selected)
    if muc:
        selected=[q for q in selected if (norm_muc(q.get('level')) or 'H')==muc]
        if pool and not selected:
            notice_extra += f"<div class='notice'>Không có câu mức <b>{html.escape(muc_label(muc))}</b> trong phần đang xem. Bấm mức khác trên thanh <b>Mức độ</b>.</div>"
    if not pool:
        return page('Dạng bài',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>File TEX này chưa có câu hỏi \\begin{ex}...\\end{ex}.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    selected=sort_questions_for_study(selected)
    folder=path.replace('\\','/').rsplit('/',1)[0] if '/' in path.replace('\\','/') else path
    title=folder.rsplit('/',1)[-1] if '/' in folder else folder
    total=len(selected)
    kc={'TN':0,'DS':0,'TLN':0,'TL':0}
    for q in selected:
        k=str(q.get('kind') or 'TL')
        kc[k]=kc.get(k,0)+1
    kind_tags=''.join(f"<span class='tag'>{lab} {kc[k]}</span>" for k,lab in (('TN','TN'),('DS','ĐS'),('TLN','TLN'),('TL','TL')) if kc.get(k))
    kindbar=("<div class='kindbar'><b>Chọn số câu theo loại</b>"
             +''.join(f"<label>{lab} <input class='kn' data-k='{k}' type='number' min='0' max='{kc[k]}' value='0'> / {kc[k]}</label>"
                      for k,lab in (('TN','Trắc nghiệm'),('DS','Đúng/Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')) if kc.get(k))
             +"<button type='button' class='btn primary' onclick='applyKinds()'>Áp dụng số câu</button></div>")
    guest = not m
    can_do = can_practice(m, path)
    tabs=lesson_switch_html(path, qs, dang=dang, kind=kind_filter, guest=guest, muc=muc)
    groups=find_duplicate_groups(selected)
    dmap=dup_index_by_question(groups)
    dao_n=sum(len(g['extras']) for g in groups if g['type']=='dao')
    cung_n=sum(1 for g in groups if g['type']=='cungde')
    cung_extra=sum(len(g['extras']) for g in groups if g['type']=='cungde')
    admin_view=can_manage_bank()
    highlight_id=(request.args.get('id') or request.args.get('qid') or '').strip()
    cards=_study_cards(selected, path, dmap, admin_view or can_do, highlight_id)
    dup_note=''
    if dao_n or cung_n:
        dup_note=(f"<div class='notice' style='border-color:#efca73;background:#fff8df'>⚠️ Có <b>{dao_n}</b> câu trùng (kể cả đảo đáp án) và <b>{cung_n}</b> nhóm cùng đề khác đáp án. "
                  "Bấm <b>Chỉ trùng</b> để lọc.</div>")
    next_url='/member/dang?path='+urllib.parse.quote(path,safe='')+'&dang='+urllib.parse.quote(dang,safe='')
    srcs={str(q.get('src') or path).replace('\\','/') for q in selected}
    dup_form=''
    if can_manage_bank() and (dao_n or cung_extra):
        nfile=len(srcs)
        note_file=f" Trùng có thể nằm ở {nfile} file TEX trong bài — xóa đúng file chứa bản thừa." if nfile>1 else ""
        tick_cung=(
            f"<button type='button' class='btn' onclick=\"document.querySelectorAll('input[data-cung=1]').forEach(function(x){{x.checked=true}})\">☑ Chọn hết {cung_extra} bản cùng đề thừa</button> "
            if cung_extra else ""
        )
        dup_form=(
            f"<form id='dupdel' method='post' action='/admin/dups' class='dupbar' onsubmit=\"return confirm('Xóa các bản đã tick? Bản đầu mỗi nhóm (nhãn giữ) không bị xóa.')\">"
            f"<input type='hidden' name='path' value='{_esc(path)}'><input type='hidden' name='next' value='{_esc(next_url)}'>"
            f"<b>Xóa trùng:</b> đảo đáp án có <b>{dao_n}</b> bản thừa, ô đã tick sẵn.{note_file} "
            f"Cùng đề khác đáp án có <b>{cung_extra}</b> bản thừa — ô để trống, bấm «Chọn hết bản cùng đề thừa» hoặc tick từng thẻ. "
            "Bản đầu mỗi nhóm được giữ. "
            + tick_cung
            + "<label class='dupok'><input type='checkbox' name='confirm' value='yes' required> Tôi xác nhận xóa các bản đã tick</label> "
            "<button class='btn red' type='submit'>🗑 Xóa các bản đã chọn</button></form>"
        )
    flash=request.args.get('ok') or ''; ferr=request.args.get('err') or ''
    flash_html=(f"<div class='success'>{html.escape(flash)}</div>" if flash else "")+(f"<div class='err'>{html.escape(ferr)}</div>" if ferr else "")
    qdel_form=''
    if can_manage_bank():
        qdel_form=(
            f"<form id='qdel' method='post' action='/admin/delete-question'>"
            f"<input type='hidden' name='path' value='{_esc(path)}'>"
            f"<input type='hidden' name='dang' value='{_esc(dang)}'>"
            f"<input type='hidden' name='next' value='{_esc(next_url)}'>"
            f"<input type='hidden' name='confirm' value='yes'></form>"
        )
    slim_html=''
    if can_manage_bank():
        from admin_slim import slim_bar_html
        slim_html=slim_bar_html(path, dang, next_url)
    find_box=("<input id='findq' type='search' placeholder='Tìm ID hoặc nguồn, ví dụ SGK' "
              f"value='{_esc(highlight_id)}' style='flex:1;min-width:180px;padding:8px;border:1px solid #cbd8e6;border-radius:7px'>")
    login_next='/member/dang?path='+urllib.parse.quote(path,safe='')+'&dang='+urllib.parse.quote(dang,safe='')
    if highlight_id:
        login_next+='&id='+urllib.parse.quote(highlight_id,safe='')
    start_form=("<form method='post' action='/member/start-selected' id='questionForm'>"
                f"<input type='hidden' name='path' value='{_esc(path)}'><input type='hidden' name='dang' value='{_esc(dang)}'>")
    exam_btns=""
    matrix_html=""
    if can_manage_bank():
        from exam_paper import exam_buttons_html, exam_matrix_html
        exam_btns=exam_buttons_html(True)
        matrix_html=exam_matrix_html(path, qs, dang=dang, include_practice=False)
    start_bottom=("<div class='toolbar bottom modebar'>"
                  "<button class='btn primary' type='submit' name='ai_review' value='0'>▶ Làm bài (không phản biện)</button>"
                  "<button class='btn' type='submit' name='ai_review' value='1'>🤖 Làm bài + phản biện AI</button>"
                  +exam_btns+
                  "<a class='btn' href='/member'>← Mục lục</a></div>")
    if not can_do:
        guest_note=view_only_notice_html(m, login_next)
        tools=f"<div class='toolbar'>{find_box}</div>"
        bottom=f"<div class='toolbar bottom'><a class='btn' href='/member'>← Mục lục</a></div>"
        form_open="<div class='guestview'>"
        form_close="</div>"
    elif admin_view:
        guest_note="<div class='notice'>🔐 ADMIN · xem đáp án và lời giải ngay trên từng thẻ, không cần làm bài.</div>"
        tools=(kindbar+
          "<div class='photobar'><button type='button' class='btn aiPhotoBtn'>📷 Chụp hình</button><span>Chụp hoặc chọn ảnh đề — máy nhận dạng chữ rồi viết lại prompt.</span></div>"
          "<div class='toolbar'>"
          "<button type='button' class='btn primary' id='qPresentBtn'>📺 Chiếu câu đã chọn</button>"
          "<button type='submit' form='questionForm' name='practice_mode' value='number_mix' class='btn' style='border-color:#2563eb;color:#1d4ed8;font-weight:800' onclick='if(!document.querySelector(\"input[name=qid]:checked\")){alert(\"Hãy chọn ít nhất 2 câu để tạo bộ Luyện đổi số.\");return false;}if(document.querySelectorAll(\"input[name=qid]:checked\").length<2){alert(\"Hãy chọn từ 2 câu trở lên để tạo bộ luyện nhiều câu.\");return false;}'>🎲 Luyện đổi số từ câu đã chọn</button>"
          "<button type='button' class='btn' onclick='setAll(true)'>☑ Chọn tất cả</button><button type='button' class='btn' onclick='setAll(false)'>☐ Bỏ chọn</button>"
          "<button type='button' class='btn' onclick='onlyDup(false)'>Tất cả</button><button type='button' class='btn' onclick='onlyDup(true)'>Chỉ trùng</button>"
          + (f"<a class='btn' href='/admin/dups?path={_esc(path)}'>🔎 Xem nhóm trùng (cả file)</a>" if can_manage_bank() and (dao_n or cung_n) else "")
          + f"<a class='btn' href='{_esc(edit_tex_href(path, 0, dang_view_url(path, dang, kind_filter, muc)))}'>✏️ Sửa file TEX</a>"
          + exam_btns
          + find_box
          + "<span id='sum' class='notice mini'>Đã chọn: 0 câu</span></div>")
        bottom=start_bottom
        form_open=start_form
        form_close="</form>"
    else:
        guest_note="<div class='notice'>🔑 VIP · xem đáp án và lời giải trên từng thẻ, đồng thời chọn câu rồi bấm Làm bài.</div>"
        tools=(kindbar+
          "<div class='toolbar'><button type='button' class='btn' onclick='setAll(true)'>☑ Chọn tất cả</button><button type='button' class='btn' onclick='setAll(false)'>☐ Bỏ chọn</button>"
          + find_box
          + "<span id='sum' class='notice mini'>Đã chọn: 0 câu</span></div>")
        bottom=start_bottom
        form_open=start_form
        form_close="</form>"
    pick_js = can_do
    find_js=(
        f"<script>let DUPONLY=false,KINDFILTER={json.dumps(kind_filter)};"
        "function vis(c){const box=document.getElementById('findq');const q=(box&&box.value||'').trim().toLowerCase();const dup=c.getAttribute('data-dup')==='1';const miss=!!q&&!(c.getAttribute('data-find')||'').includes(q);const missK=!!KINDFILTER&&c.getAttribute('data-kind')!==KINDFILTER;c.classList.toggle('hideq',miss||missK||(DUPONLY&&!dup))}"
        "function filterQ(){document.querySelectorAll('.qcard').forEach(vis);function visUntil(h,stops){var n=h.nextElementSibling;while(n){if(stops.some(function(c){return n.classList.contains(c)}))break;if(n.classList.contains('qcard')&&!n.classList.contains('hideq'))return true;n=n.nextElementSibling}return false}document.querySelectorAll('.kindpart').forEach(function(h){h.classList.toggle('hideq',!visUntil(h,['kindpart','dangpart']))});document.querySelectorAll('.dangpart').forEach(function(h){h.classList.toggle('hideq',!visUntil(h,['dangpart']))});if(typeof upd==='function'&&document.getElementById('sum'))upd()}"
        "function bootFind(){const box=document.getElementById('findq');if(box)box.addEventListener('input',filterQ);const p=new URLSearchParams(location.search);const id=(p.get('id')||p.get('qid')||'').trim();const idx=(p.get('idx')||'').trim();function show(el){if(!el)return false;el.classList.add('qhit');el.scrollIntoView({block:'center'});return true}if(id){filterQ();const t=id.toLowerCase();const el=document.querySelector('.qcard.qhit')||Array.prototype.find.call(document.querySelectorAll('.qcard'),function(c){return (c.getAttribute('data-qid')||'')===t});if(show(el))return}if(/^\\d+$/.test(idx)){filterQ();if(show(document.querySelector('.qcard[data-idx=\"'+idx+'\"]')))return}filterQ()}"
    )
    if pick_js:
        find_js += (
            "function onlyDup(v){DUPONLY=!!v;filterQ()}function onlyKind(k){KINDFILTER=k||'';filterQ()}"
            "function kindCount(k){return Array.prototype.filter.call(document.querySelectorAll('.qcard:not(.hideq)'),function(c){return c.getAttribute('data-kind')===k}).reduce(function(n,c){const i=c.querySelector('input[name=qid]');return n+(i&&i.checked?1:0)},0)}"
            "function upd(){const sum=document.getElementById('sum');if(!sum)return;const a=Array.prototype.slice.call(document.querySelectorAll('.qcard:not(.hideq) input[name=qid]'));const n=a.filter(function(x){return x.checked}).length;const bits=['TN','DS','TLN','TL'].map(function(k){const c=kindCount(k);const inp=document.querySelector('.kn[data-k=\"'+k+'\"]');if(inp&&document.activeElement!==inp)inp.value=c;return c?((k==='DS'?'ĐS':k)+' '+c):''}).filter(Boolean);sum.textContent='Đã chọn: '+n+' câu'+(bits.length?' · '+bits.join(' · '):'')}"
            "function setAll(v){document.querySelectorAll('.qcard:not(.hideq) input[name=qid]').forEach(function(x){x.checked=v});upd()}"
            "function applyKinds(){setAll(false);document.querySelectorAll('.kn').forEach(function(inp){const k=inp.getAttribute('data-k');let want=Math.max(0,Math.min(Number(inp.max)||0,Number(inp.value)||0));inp.value=want;const cards=Array.prototype.filter.call(document.querySelectorAll('.qcard:not(.hideq)'),function(c){return c.getAttribute('data-kind')===k});cards.slice(0,want).forEach(function(c){const i=c.querySelector('input[name=qid]');if(i)i.checked=true})});upd()}"
            "document.querySelectorAll('input[name=qid]').forEach(function(x){x.addEventListener('change',upd)});"
            "document.querySelectorAll('.kn').forEach(function(x){x.addEventListener('click',function(e){e.stopPropagation()});x.addEventListener('keydown',function(e){e.stopPropagation()})});"
            "const form=document.getElementById('questionForm');if(form)form.addEventListener('submit',function(e){const act=(e.submitter&&e.submitter.getAttribute('name')==='exam_action');if(act&&!document.querySelector('.qcard:not(.hideq) input[name=qid]:checked')&&document.querySelector('.kn'))applyKinds();if(!document.querySelector('.qcard:not(.hideq) input[name=qid]:checked')){e.preventDefault();alert(act?'Hãy chọn số câu theo loại (hoặc tick câu) rồi Tạo đề / Trộn đề / In đề.':'Hãy chọn ít nhất một câu.')}});"
        )
    find_js += (
        "document.querySelectorAll('.qcard').forEach(function(card){"
        "const stem=card.querySelector('.qstem');const fig=card.querySelector('.qfig');const body=card.querySelector('.qbody.ds');"
        "if(!stem||!fig||!body)return;const bits=[];"
        "stem.querySelectorAll('.immini,.tikz-row,.tikzfig,.tikz-live,.ytbox,table.tex-table').forEach(function(el){"
        "if(el.closest('.immini,.tikz-row')&&!el.matches('.immini,.tikz-row'))return;bits.push(el);});"
        "if(!bits.length){fig.remove();return;}bits.forEach(function(el){fig.appendChild(el)});fig.hidden=false;body.classList.add('hassplit');});"
        "if(window.ldvlSplitPics)ldvlSplitPics(document);"
        "bootFind();if(window.ldvlTypeset)ldvlTypeset(document.body);</script>"
    )
    rw_js = ""
    if can_manage_bank():
        from admin_rewrite import REWRITE_CLIENT_JS
        from live_present import PRESENT_HOST_JS, PRESENT_TTS_JS
        rw_js = REWRITE_CLIENT_JS + PRESENT_TTS_JS + PRESENT_HOST_JS
    dang_lab=dang or 'Cả bài'
    body=("<div class='wrap'>"+tabs+"<div class='panel'><div class='head'>📌 "+_esc(title)+" <span class='tag'>"+_esc(dang_lab)+"</span> <span class='tag'>"+str(total)+" câu</span>"+kind_tags+"</div><div class='body'>"
          f"{guest_note}{notice_extra}{dup_note}{flash_html}{slim_html}{dup_form}{qdel_form}"
          +matrix_html+form_open+"<div id='presentSlot'></div>"+tools+
          f"<div class='questions'>{cards}</div>"
          +bottom+form_close+
          "</div></div></div>"
          "<style>.kindpart{margin:14px 0 2px;padding:8px 12px;border-radius:9px;background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;font-size:16px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.kindpart .tag{background:#fff;color:#1e3a8a}.kindpart.k-DS{background:#f0fdf4;border-color:#bbf7d0;color:#166534}.kindpart.k-DS .tag{color:#166534}.kindpart.k-TLN{background:#fffbeb;border-color:#fde68a;color:#92400e}.kindpart.k-TLN .tag{color:#92400e}.kindpart.k-TL{background:#fdf2f8;border-color:#fbcfe8;color:#9d174d}.kindpart.k-TL .tag{color:#9d174d}.dangpart{margin:18px 0 0;padding:8px 2px 0;font-size:15px;color:#0f172a;border-top:1px solid #dbe4ee}.questions>.dangpart:first-child{border-top:0;margin-top:4px}.guestview .qcheck{display:none}.photobar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 12px;padding:12px;border:2px solid #b45309;border-radius:10px;background:#fef3c7;font-weight:800}.photobar .btn{font-size:18px;padding:12px 18px}.toolbar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:10px 0}.kindbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0;padding:10px;border:1px solid #d9e5f0;border-radius:9px;background:#f8fbff}.kindbar label{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px}.kindbar input{width:58px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}.mini{padding:7px 10px}.questions{display:grid;gap:10px}.qcard{border:1px solid #cfddeb;border-radius:11px;background:#fff;padding:12px}.qhead{display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #e7eef5;padding-bottom:8px}.qcheck{font-weight:900;color:#145bb0;cursor:pointer}.qcheck input{width:17px;height:17px;vertical-align:middle;margin-right:5px}.badge,.level,.qid,.metafile,.dupbadge{border:1px solid #cbd9e7;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;background:#f8fbff}.qid{background:#fff7dc;border-color:#efca73;color:#7a5300;font-family:Consolas,monospace}.dupbadge{background:#ffe4e6;border-color:#fb7185;color:#9f1239}.dupcard{border-color:#fb7185;background:#fff7f7}.qhit{border:2px solid #176bd3;box-shadow:0 0 0 3px #176bd322}.slimhit{border-color:#c2410c;background:#fff7ed}.metafile{color:#4a6278}.level{margin-left:auto}.dupbar{margin:10px 0;padding:12px;border:2px solid #e11d48;border-radius:10px;background:#fff1f2;display:flex;flex-wrap:wrap;gap:10px;align-items:center}.dupx{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:#9f1239;color:#fff;font-weight:800;font-size:12px;cursor:pointer}.dupx input{width:16px;height:16px}.dupok{font-weight:800}.slimbar{margin:10px 0;padding:12px;border:1px solid #fdba74;border-radius:10px;background:#fff7ed;display:flex;flex-wrap:wrap;gap:10px;align-items:center}.slimbar input[type=number]{width:64px;padding:6px;border:1px solid #fdba74;border-radius:6px;text-align:center}.slimform{margin:8px 0 12px}.slimgrp{border:1px solid #fed7aa;border-radius:9px;padding:8px;margin:8px 0;background:#fff}.slimh{font-weight:800;margin-bottom:6px}.slimrow{padding:6px 0;border-top:1px dashed #fed7aa;font-size:14px;line-height:1.45}.slimrow.keep{background:#f0fdf4}.rwbar{margin:10px 0 0;padding:8px 10px;border:1px dashed #7dd3fc;border-radius:9px;background:#f0f9ff;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.rwout{width:100%}.rwprev{margin-top:8px;padding:10px;border:1px solid #bae6fd;border-radius:9px;background:#fff}.rwprev label{display:flex;gap:8px;align-items:center;font-weight:800;margin:8px 0 4px}.qtext{font-size:16px;line-height:1.7;padding:10px 2px;font-family:'Times New Roman',Times,serif;font-weight:400}.opts{display:grid;gap:7px}.opt{border:1px solid #d7e3ee;border-radius:8px;padding:9px;background:#fbfdff;display:flex;align-items:center;gap:10px}.opt.ok{background:#e8f8ee;border-color:#42ae6b}.okmark{display:inline-block;min-width:4.6em;text-align:center;margin-left:0;padding:3px 10px;border-radius:999px;background:#15803d;color:#fff;font-size:11px;font-weight:800}.answerline{border:1px dashed #b8cde2;border-radius:8px;padding:9px;color:#687d92;margin-top:6px}.solution{margin-top:11px;padding:12px;border:1px solid #bad5f2;border-radius:9px;background:#f7fbff}.qcard:has(input:checked){border:2px solid #176bd3;background:#fafdff}.qcard.hideq{display:none}.bottom{border-top:1px solid #e5edf5;padding-top:12px}@media(max-width:700px){.qtext{font-size:14px}}</style>"
          + find_js + rw_js
          )
    return page('Chọn câu' if can_do else 'Xem đề',body)

@app.post('/admin/delete-question')
def admin_delete_question():
    if not can_manage_bank():
        return redirect('/admin/login')
    path=str(request.form.get('path') or '').replace('\\','/').strip()
    dang=str(request.form.get('dang') or '').strip()
    nxt=str(request.form.get('next') or '')
    if not (nxt.startswith('/member/dang?') or nxt.startswith('/member/select?')):
        nxt='/member/dang?path='+urllib.parse.quote(path,safe='')+'&dang='+urllib.parse.quote(dang,safe='')

    def back(key, msg):
        sep='&' if '?' in nxt else '?'
        return redirect(nxt+sep+key+'='+urllib.parse.quote(msg))

    if request.form.get('confirm')!='yes':
        return back('err','Phải xác nhận trước khi xóa câu.')
    raw=str(request.form.get('drop') or '').strip()
    if '||' not in raw:
        return back('err','Thiếu vị trí câu cần xóa.')
    src,_,idx_s=raw.replace('\\','/').rpartition('||')
    src=src.replace('\\','/').strip()
    try:
        fi=int(idx_s)
    except (TypeError, ValueError):
        return back('err','Vị trí câu không hợp lệ.')
    if not src.startswith('ngan-hang/') or not src.lower().endswith('.tex'):
        return back('err','File TEX không hợp lệ.')
    try:
        qs=parse_lesson_questions(path) if path else []
        if not qs:
            _,tex=read_tex(src); qs=parse_questions(tex)
            for q in qs:
                q['src']=src; q['file_idx']=int(q.get('idx') or 0)
    except Exception as e:
        return back('err',str(e))
    allowed=False
    qid='—'
    for q in qs:
        qsrc=str(q.get('src') or src).replace('\\','/')
        try: qfi=int(q.get('file_idx') if q.get('file_idx') is not None else q.get('idx') or 0)
        except (TypeError, ValueError):
            continue
        if qsrc==src and qfi==fi:
            allowed=True
            qid=str(q.get('id') or '—').strip() or '—'
            break
    if not allowed:
        return back('err','Không tìm thấy câu này trong bài.')
    try:
        fsha, tex = read_tex(src, need_sha=True)
        new=tex_without_questions(tex, [fi])
        if new==tex:
            return back('err','Không gỡ được câu khỏi file TEX.')
        local=_safe_repo_file(src)[1]
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(new, encoding='utf-8')
        if TOKEN:
            github_put_text(src, new, 'ADMIN xóa câu '+qid+' trong '+src, fsha or None)
        _STATS_CACHE.clear(); _QID_CACHE.clear()
    except Exception as e:
        return back('err',str(e))
    return back('ok','Đã xóa câu '+qid+' khỏi file TEX.')

def _q_drop_key(q):
    src = str(q.get('src') or '').replace('\\', '/')
    try:
        fi = int(q.get('file_idx') if q.get('file_idx') is not None else q.get('idx') or 0)
    except (TypeError, ValueError):
        fi = 0
    return src + '||' + str(fi)

def _q_preview(q, n=90):
    t = re.sub(r'<[^>]+>', ' ', str(q.get('text') or ''))
    t = re.sub(r'\s+', ' ', t).strip()
    return (t[:n] + '…') if len(t) > n else t

def _review_similar_html(path, qs, dang, next_url):
    from admin_slim import cluster_similar
    from app import KIND_CHIP_LABS, KIND_ORDER, dang_kind_counts_of, dang_names_of, kind_gap_heuristic, kind_over_max, kind_quota_line, questions_in_scope
    names, _c = dang_names_of(qs)
    focus = [dang] if dang else list(names)
    if not focus:
        focus = ['Chưa phân dạng']
    head = (
        "<div class='simrev'><b>Soát từng dạng</b> — mục tiêu 9 TN / 2 ĐS / 3 TLN / 4 TL · trần 18 / 4 / 6 / 8. "
        "Câu gần trùng: giữ bản có lời giải. Tick nhiều câu rồi xóa một lần.</div>"
    )
    body = []
    n_drop = 0
    seen = set()
    per, _allc = dang_kind_counts_of(qs)
    for name in focus:
        scoped = questions_in_scope(qs, name)
        counts = {k: int((per.get(name) or {}).get(k) or 0) for k in KIND_ORDER}
        add = kind_gap_heuristic(counts)
        over = kind_over_max(counts)
        labs = dict(KIND_CHIP_LABS)
        extra = ' · '.join(f"{labs[k]} thừa {over[k]}" for k in KIND_ORDER if over.get(k))
        miss = ' · '.join(f"{labs[k]} +{add[k]}" for k in KIND_ORDER if add.get(k))
        body.append("<h4>" + html.escape(name) + "</h4><div class='muted'>" + html.escape(kind_quota_line(counts)) + "</div>")
        if extra:
            body.append("<div class='gapnote'>Vượt trần — bớt câu tương tự trước khi thêm mới. " + html.escape(extra) + "</div>")
        elif miss:
            body.append("<div class='muted'>Còn thiếu: " + html.escape(miss) + "</div>")
        groups = cluster_similar(scoped, 0.72) if len(scoped) >= 2 else []
        if not groups:
            body.append("<div class='muted'>Không thấy cặp gần trùng trong dạng này.</div>")
            continue
        for g in groups:
            keep = g.get('keep') or {}
            extras = g.get('extras') or []
            why = str(g.get('kind') or 'ý gần nhau')
            sim = int(g.get('sim') or 0)
            body.append(
                "<div class='simrow'><span class='dupok'>Giữ "
                + html.escape(str(keep.get('id') or '—')) + " · "
                + html.escape(_q_preview(keep, 70))
                + "</span> <span class='muted'>(" + html.escape(why) + " " + str(sim) + "%)</span></div>"
            )
            for ex in extras:
                dk = _q_drop_key(ex)
                if dk in seen:
                    continue
                seen.add(dk)
                n_drop += 1
                body.append(
                    "<div class='simrow'><label class='simx'><input type='checkbox' name='drop' value='"
                    + html.escape(dk, quote=True) + "' checked> Tick xóa "
                    + html.escape(str(ex.get('kind') or '')) + " "
                    + html.escape(str(ex.get('id') or '—')) + "</label> — "
                    + html.escape(_q_preview(ex, 80)) + "</div>"
                )
    if n_drop:
        bar = (
            "<form id='simdel' method='post' action='/admin/delete-questions' onsubmit=\"return confirm('Xóa '+document.querySelectorAll('#simdel input[name=drop]:checked').length+' câu đã tick khỏi TEX?')\">"
            + "<input type='hidden' name='path' value='" + html.escape(path, quote=True) + "'>"
            + "<input type='hidden' name='dang' value='" + html.escape(dang, quote=True) + "'>"
            + "<input type='hidden' name='next' value='" + html.escape(next_url, quote=True) + "'>"
            + "<div class='simbar'><b>Xóa hàng loạt:</b> các ô đỏ mặc định đã tick. Bản GIỮ không có ô."
            + " <button type='button' class='btn mini' onclick=\"document.querySelectorAll('#simdel input[name=drop]').forEach(function(x){x.checked=true})\">Tick hết gợi ý</button>"
            + " <button type='button' class='btn mini' onclick=\"document.querySelectorAll('#simdel input[name=drop]').forEach(function(x){x.checked=false})\">Bỏ tick</button>"
            + " <label class='dupok'><input type='checkbox' name='confirm' value='yes' required> Tôi xác nhận xóa các câu đã tick</label>"
            + " <button class='btn red' type='submit'>🗑 Xóa các câu đã tick</button></div>"
        )
        return head + bar + ''.join(body) + "</form>", n_drop
    return head + ''.join(body), n_drop

@app.post('/admin/delete-questions')
def admin_delete_questions():
    if not can_manage_bank():
        return redirect('/admin/login')
    path = str(request.form.get('path') or '').replace('\\', '/').strip()
    dang = str(request.form.get('dang') or '').strip()
    nxt = str(request.form.get('next') or '')
    if not (nxt.startswith('/member/dang?') or nxt.startswith('/member/select?')):
        nxt = '/member/dang?path=' + urllib.parse.quote(path, safe='') + '&dang=' + urllib.parse.quote(dang, safe='')

    def back(key, msg):
        sep = '&' if '?' in nxt else '?'
        return redirect(nxt + sep + key + '=' + urllib.parse.quote(msg))

    if request.form.get('confirm') != 'yes':
        return back('err', 'Phải xác nhận trước khi xóa các câu đã tick.')
    try:
        qs = parse_lesson_questions(path) if path else []
    except Exception as e:
        return back('err', str(e))
    allowed = set()
    for q in qs:
        src = str(q.get('src') or '').replace('\\', '/')
        try:
            fi = int(q.get('file_idx') if q.get('file_idx') is not None else q.get('idx') or 0)
        except (TypeError, ValueError):
            continue
        if src.startswith('ngan-hang/') and src.lower().endswith('.tex'):
            allowed.add((src, fi))
    drops_by = {}
    for raw in request.form.getlist('drop'):
        raw = str(raw or '').strip()
        if '||' not in raw:
            continue
        src, _, idx_s = raw.replace('\\', '/').rpartition('||')
        src = src.replace('\\', '/').strip()
        try:
            fi = int(idx_s)
        except (TypeError, ValueError):
            continue
        if (src, fi) not in allowed:
            continue
        drops_by.setdefault(src, []).append(fi)
    if not drops_by:
        return back('err', 'Chưa tick câu nào để xóa.')
    total = 0
    try:
        for src, idxs in drops_by.items():
            idxs = sorted(set(idxs))
            fsha, tex = read_tex(src, need_sha=True)
            new = tex_without_questions(tex, idxs)
            if new == tex:
                continue
            local = _safe_repo_file(src)[1]
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(new, encoding='utf-8')
            if TOKEN:
                github_put_text(src, new, 'ADMIN xóa ' + str(len(idxs)) + ' câu gần trùng trong ' + src, fsha or None)
            total += len(idxs)
        _STATS_CACHE.clear()
        _QID_CACHE.clear()
    except Exception as e:
        return back('err', str(e))
    if not total:
        return back('err', 'Không gỡ được câu khỏi file TEX.')
    return back('ok', 'Đã xóa ' + str(total) + ' câu đã tick, giữ các bản không tick.')

@app.post('/api/admin/dang-gaps')
def api_admin_dang_gaps():
    if not can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN.'), 403
    from app import KIND_AIM, KIND_CHIP_LABS, KIND_MAX, KIND_ORDER, dang_kind_counts_of, dang_names_of, kind_gap_heuristic, kind_over_max, load_lesson_questions
    from student_gemini import _gemini_generate, _keys_from_payload
    data = request.get_json(silent=True) or {}
    path = str(data.get('path') or '').replace('\\', '/').strip()
    dang = str(data.get('dang') or '').strip()
    if not path.startswith('ngan-hang/'):
        return jsonify(ok=False, error='Thiếu path bài.'), 400
    try:
        qs = load_lesson_questions(path)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    per, allc = dang_kind_counts_of(qs)
    counts = per.get(dang) if dang else allc
    counts = {k: int((counts or {}).get(k) or 0) for k in KIND_ORDER}
    add = kind_gap_heuristic(counts)
    note = ''
    names, _cnts = dang_names_of(qs)
    keys = _keys_from_payload(data)
    nxt = '/member/dang?path=' + urllib.parse.quote(path, safe='') + '&dang=' + urllib.parse.quote(dang, safe='')
    if not dang:
        nxt = '/member/select?path=' + urllib.parse.quote(path, safe='')
    if keys:
        rows = []
        for name in ( [dang] if dang else names[:20] ):
            bucket = per.get(name) if name else allc
            bucket = {k: int((bucket or {}).get(k) or 0) for k in KIND_ORDER}
            have = ', '.join(f"{lab} {bucket[k]}" for k, lab in KIND_CHIP_LABS)
            need = ', '.join(f"{lab} {kind_gap_heuristic(bucket)[k]}" for k, lab in KIND_CHIP_LABS if kind_gap_heuristic(bucket).get(k))
            rows.append(name + ': ' + have + (' → thiếu ' + need if need else ' → đủ mục tiêu'))
        prompt = (
            "Bạn là giáo viên ra đề THPT. Soát ngân hàng từng dạng. Trả về ĐÚNG một JSON, không markdown.\n"
            'Schema: {"add":{"TN":số,"DS":số,"TLN":số,"TL":số},"note":"tiếng Việt"}\n'
            "add = số câu CẦN THÊM cho dạng đang xét (0 nếu đủ hoặc đang quá nhiều câu cùng ý).\n"
            "Mục tiêu cố gắng mỗi dạng: 9 TN, 2 ĐS, 3 TLN, 4 TL.\n"
            "Trần tối đa: 18 TN, 4 ĐS, 6 TLN, 8 TL — không đề xuất thêm nếu đã chạm/vượt trần loại đó.\n"
            "Nếu nhiều câu cùng ý, để add=0 cho loại đó và note gợi ý xóa bản thừa, đừng viết thêm biến thể.\n"
            "Dạng đang xét: " + (dang or "Cả bài — add theo mức thiếu chung, note nhắc dạng nào thừa/thiếu") + "\n"
            "Hiện có dạng này: " + ", ".join(f"{lab} {counts[k]}" for k, lab in KIND_CHIP_LABS) + "\n"
            "Từng dạng:\n" + ("\n".join(rows) or "(trống)")
        )
        raw, err = '', ''
        for key in keys:
            try:
                raw = _gemini_generate(key, prompt, 900, 0.15)
                err = ''
                break
            except Exception as e:
                err = str(e)
                raw = ''
        if raw:
            m = re.search(r'\{[\s\S]*\}', raw)
            try:
                obj = json.loads(m.group(0) if m else raw)
                src = obj.get('add') if isinstance(obj, dict) else None
                if not isinstance(src, dict):
                    src = obj if isinstance(obj, dict) else {}
                for k in KIND_ORDER:
                    rawv = src.get(k)
                    if rawv is None and k == 'DS':
                        rawv = src.get('ĐS')
                    if rawv is None:
                        continue
                    try:
                        add[k] = max(0, int(rawv))
                    except (TypeError, ValueError):
                        pass
                note = str((obj or {}).get('note') or '').strip()
            except Exception:
                note = (raw or '')[:280]
        elif err:
            note = 'AI lỗi, dùng mức cố gắng. ' + err[:120]
    else:
        note = 'Chưa có key Gemini — dùng mức 9 TN / 2 ĐS / 3 TLN / 4 TL, trần 18 / 4 / 6 / 8.'
    for k in KIND_ORDER:
        n = counts[k]
        add[k] = min(int(add.get(k) or 0), max(0, KIND_AIM[k] - n), max(0, KIND_MAX[k] - n))
        if n >= KIND_MAX[k]:
            add[k] = 0
    review_html, n_drop = _review_similar_html(path, qs, dang, nxt)
    labs = dict(KIND_CHIP_LABS)
    bits = [f"{labs[k]} cần thêm {add[k]}" for k in KIND_ORDER if add.get(k)]
    over = kind_over_max(counts)
    over_bits = [f"{labs[k]} thừa {over[k]}" for k in KIND_ORDER if over.get(k)]
    if bits:
        summary = '; '.join(bits) + '.'
    elif over_bits:
        summary = 'Không thêm mới. ' + '; '.join(over_bits) + '.'
    else:
        summary = 'Đã đạt mức cố gắng cả 4 loại, chưa vượt trần.'
    if n_drop:
        summary += ' Gợi ý xóa ' + str(n_drop) + ' câu gần trùng.'
    return jsonify(ok=True, counts=counts, add=add, summary=summary, note=note, review_html=review_html)

@app.post('/api/admin/notebooklm-prompt')
def api_admin_notebooklm_prompt():
    if not can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN.'), 403
    from app import load_lesson_questions, notebooklm_prompt_text
    data = request.get_json(silent=True) or {}
    path = str(data.get('path') or '').replace('\\', '/').strip()
    dang = str(data.get('dang') or '').strip()
    if not path.startswith('ngan-hang/'):
        return jsonify(ok=False, error='Thiếu path bài.'), 400
    try:
        qs = load_lesson_questions(path)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    prompt = notebooklm_prompt_text(path, qs, dang)
    return jsonify(ok=True, prompt=prompt)

def _cap_fill_add(add, counts=None):
    from app import KIND_AIM, KIND_MAX, KIND_ORDER
    batch = {'TN': 5, 'DS': 2, 'TLN': 3, 'TL': 4}
    out, total = {}, 0
    for k in KIND_ORDER:
        try:
            n = max(0, int((add or {}).get(k) or 0))
        except (TypeError, ValueError):
            n = 0
        try:
            have = int((counts or {}).get(k) or 0)
        except (TypeError, ValueError):
            have = 0
        room = max(0, int(KIND_MAX[k]) - have)
        toward = max(0, int(KIND_AIM[k]) - have)
        n = min(n, batch[k], room, toward if toward else room)
        if toward == 0:
            n = 0
        if total + n > 12:
            n = max(0, 12 - total)
        out[k] = n
        total += n
    return out

def _extract_ex_blocks(text):
    blocks = []
    for m in re.finditer(r'\\begin\s*\{\s*ex\s*\}.*?\\end\s*\{\s*ex\s*\}', str(text or ''), re.I | re.S):
        blocks.append(m.group(0).strip())
    return blocks

def _stem_snip(q, n=140):
    t = re.sub(r'<[^>]+>', ' ', str((q or {}).get('text') or ''))
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) > n:
        t = t[:n].rstrip() + '…'
    return t


def _existing_dang_brief(qs, names):
    """Mỗi dạng: số câu và 2 đề đang có, để AI gán theo nội dung chứ không chỉ theo tên."""
    lines = []
    for name in names or []:
        if not name or name == 'Chưa phân dạng':
            continue
        stems = []
        count = 0
        for q in qs or []:
            if str(q.get('dang') or '').strip() != name:
                continue
            count += 1
            if len(stems) < 2:
                sn = _stem_snip(q)
                if sn:
                    stems.append('[' + str(q.get('kind') or '') + '] ' + sn)
        bit = '- «' + name + '» (' + str(count) + ' câu)'
        if stems:
            bit += '. Đang có: ' + ' | '.join(stems)
        lines.append(bit)
    return '\n'.join(lines)


def _snap_dang_name(name, names):
    """Kéo tên AI đặt về đúng dạng đã có khi cùng nghĩa hoặc gần chữ."""
    n = str(name or '').strip()
    pool = [x for x in (names or []) if x and x != 'Chưa phân dạng']
    if not n or n == 'Chưa phân dạng' or not pool:
        return n or 'Chưa phân dạng'
    folded = {x.casefold(): x for x in pool}
    if n.casefold() in folded:
        return folded[n.casefold()]
    from admin_classify import _sim
    best, score = '', 0.0
    for x in pool:
        s = _sim(n, x)
        if s > score:
            best, score = x, s
    if best and score >= 0.62:
        return best
    return n


def _chunks_from_import(text, fallback_dang=''):
    """Tách (tên dạng, khối ex) — AI có thể gắn \\dangbt trước từng câu."""
    text = str(text or '')
    marks = [(m.start(), 'd', (m.group(1) or '').strip()) for m in re.finditer(r'\\dang(?:bt)?\s*\{([^{}]*)\}', text, re.I)]
    exs = [(m.start(), 'e', m.group(0).strip()) for m in re.finditer(r'\\begin\s*\{\s*ex\s*\}.*?\\end\s*\{\s*ex\s*\}', text, re.I | re.S)]
    cur = (fallback_dang or '').strip() or 'Chưa phân dạng'
    out = []
    for _, kind, val in sorted(marks + exs, key=lambda x: x[0]):
        if kind == 'd':
            cur = val or cur
        else:
            out.append((cur, val))
    return out

def _import_tex_chunk(text, fallback_dang=''):
    rows = _chunks_from_import(text, fallback_dang)
    if not rows:
        return ''
    bits = []
    for dname, block in rows:
        bits.append('\\dangbt{' + dname + '}\n' + block)
    return '\n\n'.join(bits) + '\n'

def _tex_nguon_url(url):
    s = str(url or '').strip()
    s = re.sub(r'[{}\\]', '', s)
    return s.replace('%', '\\%').replace('#', '\\#')

def _block_with_nguon(block, url):
    src = _tex_nguon_url(url)
    if not src or not block:
        return block
    needle = src.replace('\\%', '%').replace('\\#', '#')
    existing = re.search(r'\\nguon\s*\{([^{}]*)\}', block, re.I)
    if existing and needle in (existing.group(1) or '').replace('\\%', '%').replace('\\#', '#'):
        return block
    cmd = '\\nguon{' + src + '}'
    if existing:
        return block[:existing.start()] + cmd + block[existing.end():]
    m = re.search(r'\\end\s*\{\s*ex\s*\}', block, re.I)
    if not m:
        return block.rstrip() + '\n' + cmd + '\n'
    return block[:m.start()] + cmd + '\n' + block[m.start():]

def _latex_with_nguon(text, url):
    if not url:
        return text
    parts, last = [], 0
    for m in re.finditer(r'\\begin\s*\{\s*ex\s*\}.*?\\end\s*\{\s*ex\s*\}', str(text or ''), re.I | re.S):
        parts.append(text[last:m.start()])
        parts.append(_block_with_nguon(m.group(0), url))
        last = m.end()
    parts.append(text[last:])
    return ''.join(parts)

def _kind_of_block(block):
    b = str(block or '')
    if re.search(r'\\choiceTF\b', b, re.I):
        return 'DS'
    if re.search(r'\\choice\b', b, re.I):
        return 'TN'
    if re.search(r'\\shortans\b', b, re.I):
        return 'TLN'
    return 'TL'

def _stem_of_ex(block):
    b = re.sub(r'\\begin\s*\{\s*ex\s*\}', '', str(block or ''), count=1, flags=re.I)
    return re.split(r'\\(?:choiceTF|choice|shortans|loigiai)\b', b, maxsplit=1, flags=re.I)[0]

def _block_ok_for_kind(block, kind):
    from app import command_args, split_true_mark
    from admin_rewrite import stem_incomplete, tn_style_stem
    kind = str(kind or '').upper()
    if _kind_of_block(block) != kind:
        return False
    if stem_incomplete(_stem_of_ex(block)):
        return False
    if kind == 'DS':
        opts = command_args(block, '\\choiceTF')
        if len(opts) != 4:
            return False
        if tn_style_stem(_stem_of_ex(block)):
            return False
        return all(len(re.sub(r'\s+', '', o or '')) >= 4 for o in opts)
    if kind == 'TN':
        opts = command_args(block, '\\choice')
        if len(opts) != 4:
            return False
        return sum(1 for o in opts if split_true_mark(o)[1]) == 1
    if kind == 'TLN':
        from app import solution_of
        from admin_rewrite import _sol_too_thin
        if not command_args(block, '\\shortans'):
            return False
        return not _sol_too_thin(solution_of(block))
    if re.search(r'\\choice(?:TF)?\b|\\shortans\b', block or '', re.I):
        return False
    return bool(re.search(r'\\loigiai\s*\{', block or '', re.I))

def _q_from_block(block, dang=''):
    wrap = '\\dangbt{' + str(dang or 'Chưa phân dạng') + '}\n' + str(block or '')
    qs = parse_questions(wrap)
    return qs[0] if qs else {'kind': _kind_of_block(block), 'text': block, 'dang': dang}

def _near_dup(new_q, pool, thr):
    from admin_slim import cluster_similar
    if not pool:
        return False
    groups = cluster_similar(list(pool) + [new_q], thr)
    for g in groups:
        mem = g.get('members') or []
        if new_q in mem and len(mem) > 1:
            return True
    return False

def _filter_import_rows(rows, qs, fallback_dang='', relax=False):
    """Lọc câu import. relax=True (file/link): chỉ bỏ sai cấu trúc — đưa lên xem trước rồi ADMIN lọc trùng sau."""
    from app import KIND_AIM, KIND_MAX, KIND_ORDER, _dang_name
    from collections import defaultdict
    have = defaultdict(lambda: {k: 0 for k in KIND_ORDER})
    pools = defaultdict(list)
    for q in qs or []:
        d = _dang_name(q)
        k = str(q.get('kind') or 'TL')
        if k not in KIND_ORDER:
            k = 'TL'
        have[d][k] += 1
        pools[(d, k)].append(q)
    kept, skipped = [], []
    for dname, block in rows:
        dname = (dname or fallback_dang or 'Chưa phân dạng').strip() or 'Chưa phân dạng'
        fake = _q_from_block(block, dname)
        k = str(fake.get('kind') or _kind_of_block(block) or 'TL')
        if k not in KIND_ORDER:
            k = 'TL'
        if not _block_ok_for_kind(block, k):
            skipped.append('sai cấu trúc ' + k)
            continue
        if not relax:
            n = have[dname][k]
            if n >= KIND_MAX[k]:
                skipped.append('vượt trần ' + k)
                continue
            pool = pools[(dname, k)]
            if _near_dup(fake, pool, 0.72):
                skipped.append('gần trùng ' + k)
                continue
            if n >= KIND_AIM[k] and _near_dup(fake, pool, 0.58):
                skipped.append('cùng ý khi đã đủ ' + k)
                continue
        kept.append((dname, block))
        have[dname][k] += 1
        pools[(dname, k)].append(fake)
    return kept, skipped

_BLOCK_HOSTS = {
    'localhost', '127.0.0.1', '::1', '0.0.0.0',
    'metadata.google.internal', 'metadata.google.internal.',
}

def _host_blocked(host):
    host = str(host or '').strip().rstrip('.').lower()
    if not host or host in _BLOCK_HOSTS or host.endswith('.localhost') or host.endswith('.local'):
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return True
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except Exception:
            return True
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
            or ip.is_reserved or ip.is_unspecified
        ):
            return True
        if ip.exploded in {'0000:0000:0000:0000:0000:0000:0000:0001'} or str(ip) == '169.254.169.254':
            return True
    return False

def _assert_public_http_url(raw):
    u = urllib.parse.urlparse(str(raw or '').strip())
    if u.scheme not in ('http', 'https'):
        raise ValueError('Chỉ nhận link http/https.')
    if u.username or u.password:
        raise ValueError('Link không hợp lệ.')
    host = u.hostname
    if not host or _host_blocked(host):
        raise ValueError('Không lấy được link nội bộ / địa chỉ cấm.')
    if u.port in (22, 25, 3306, 5432, 6379, 9200, 11211):
        raise ValueError('Cổng này không được phép.')
    return u.geturl()

class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _assert_public_http_url(newurl)
        return urllib.request.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)

def _html_to_text(raw):
    s = str(raw or '')
    s = re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', s)
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)
    s = re.sub(r'(?i)</(p|div|li|tr|h[1-6]|section|article)>', '\n', s)
    s = re.sub(r'(?s)<[^>]+>', ' ', s)
    s = html.unescape(s)
    s = re.sub(r'[ \t\f\v]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def _looks_like_latex(s):
    t = str(s or '')
    if len(t) < 20 or '\\' not in t:
        return False
    hits = 0
    for pat in (
        r'\\begin\s*\{',
        r'\\documentclass\b',
        r'\\chapter\b',
        r'\\section\b',
        r'\\choice\b',
        r'\\dangbt\b',
        r'\\kienthuc\b',
        r'\\phuongphap\b',
        r'\\textbf\b',
    ):
        if re.search(pat, t):
            hits += 1
    return hits >= 1

def _to_raw_source_url(url):
    u = urllib.parse.urlparse(str(url or '').strip())
    host = (u.hostname or '').lower()
    path = u.path or ''
    if host in {'github.com', 'www.github.com'}:
        m = re.match(r'^/([^/]+)/([^/]+)/(?:blob|raw)/(.+)$', path)
        if m:
            return 'https://raw.githubusercontent.com/' + m.group(1) + '/' + m.group(2) + '/' + m.group(3)
    if host == 'gist.github.com':
        parts = [p for p in path.split('/') if p and p != 'raw']
        if len(parts) >= 2:
            return 'https://gist.githubusercontent.com/' + parts[0] + '/' + parts[1] + '/raw'
        if len(parts) == 1:
            return 'https://gist.githubusercontent.com/' + parts[0] + '/raw'
    if 'gitlab.' in host or host == 'gitlab.com':
        path2 = path.replace('/-/blob/', '/-/raw/')
        if path2 != path:
            return urllib.parse.urlunparse(u._replace(path=path2))
    return url

def _extract_latex_from_html(html_s):
    chunks = []
    for m in re.finditer(r'(?is)<(?:pre|code|textarea)[^>]*>(.*?)</(?:pre|code|textarea)>', html_s or ''):
        inner = html.unescape(re.sub(r'(?s)<[^>]+>', '', m.group(1)))
        if _looks_like_latex(inner):
            chunks.append(inner.strip())
    if chunks:
        return '\n\n'.join(chunks)
    plain = _html_to_text(html_s)
    if _looks_like_latex(plain):
        return plain
    return ''

def _fetch_public_page(url):
    try:
        url = _assert_public_http_url(_to_raw_source_url(url))
    except ValueError as e:
        return '', str(e)
    low = url.lower()
    want_tex = low.endswith('.tex') or '/raw/' in low or 'raw.githubusercontent.com' in low or 'gist.githubusercontent.com' in low
    accept = 'text/html,application/xhtml+xml,text/plain,text/x-tex,application/x-tex,*/*;q=0.8'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'luyen-de-vat-ly-admin/1.0 (question import)',
        'Accept': accept,
    })
    opener = urllib.request.build_opener(_SafeRedirect)
    try:
        with opener.open(req, timeout=28) as r:
            ctype = str(r.headers.get('Content-Type') or '').lower()
            raw = r.read(1200000)
    except urllib.error.HTTPError as e:
        return '', 'Không tải được trang (HTTP %s).' % e.code
    except Exception as e:
        return '', 'Không tải được trang: ' + str(e)[:160]
    if len(raw) >= 1200000:
        raw = raw[:1190000]
    charset = 'utf-8'
    cm = re.search(r'charset=([A-Za-z0-9._-]+)', ctype)
    if cm:
        charset = cm.group(1)
    try:
        text = raw.decode(charset, errors='replace')
    except Exception:
        text = raw.decode('utf-8', errors='replace')
    ok_type = (not ctype) or any(
        x in ctype
        for x in ('html', 'text', 'xml', 'tex', 'latex', 'octet-stream', 'json')
    )
    if not ok_type and not _looks_like_latex(text):
        return '', 'Trang này không phải HTML/văn bản/LaTeX.'
    if want_tex or _looks_like_latex(text) or 'tex' in ctype or 'latex' in ctype:
        if '<html' in text[:800].lower() or '<!doctype html' in text[:400].lower():
            extracted = _extract_latex_from_html(text)
            if extracted:
                text = extracted
            else:
                text = _html_to_text(text)
        else:
            text = text.replace('\r\n', '\n')
        if len(text.strip()) < 40:
            return '', 'File LaTeX/trang gần như trống (có thể cần đăng nhập).'
        return text[:80000], ''
    extracted = _extract_latex_from_html(text)
    if extracted:
        return extracted[:80000], ''
    plain = _html_to_text(text)
    if len(plain) < 40:
        return '', 'Trang gần như không có chữ (có thể chặn bot / cần đăng nhập).'
    return plain[:48000], ''

_W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
_M_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'
_A_NS = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
_R_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
_PKG_REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'


def _xml_local(tag):
    return str(tag or '').split('}')[-1]


def _omml_to_latex(el):
    tag = _xml_local(el.tag)
    if tag == 't':
        return el.text or ''
    kids = list(el)

    def child(name):
        for c in kids:
            if _xml_local(c.tag) == name:
                return _omml_to_latex(c)
        return ''

    if tag == 'f':
        return '\\frac{' + child('num') + '}{' + child('den') + '}'
    if tag == 'sSup':
        return child('e') + '^{' + child('sup') + '}'
    if tag == 'sSub':
        return child('e') + '_{' + child('sub') + '}'
    if tag == 'sSubSup':
        return child('e') + '_{' + child('sub') + '}^{' + child('sup') + '}'
    if tag == 'rad':
        deg = child('deg').strip()
        body = child('e')
        return ('\\sqrt[' + deg + ']{' + body + '}') if deg else ('\\sqrt{' + body + '}')
    if tag == 'd':
        beg, end = '(', ')'
        for c in el.iter():
            loc = _xml_local(c.tag)
            if loc == 'begChr' and (c.get(_M_NS + 'val') or c.get('val')):
                beg = c.get(_M_NS + 'val') or c.get('val')
            if loc == 'endChr' and (c.get(_M_NS + 'val') or c.get('val')):
                end = c.get(_M_NS + 'val') or c.get('val')
        inner = ''.join(_omml_to_latex(c) for c in kids if _xml_local(c.tag) == 'e')
        return beg + inner + end
    return ''.join(_omml_to_latex(c) for c in kids)


def _docx_p_line(p):
    bits = []

    def walk(node):
        loc = _xml_local(node.tag)
        if loc == 't' and str(node.tag).startswith(_W_NS):
            bits.append(node.text or '')
            return
        if loc in ('oMath', 'oMathPara'):
            latex = _omml_to_latex(node).strip()
            if latex:
                bits.append('$' + latex + '$')
            return
        if loc == 'tab':
            bits.append(' ')
        elif loc in ('br', 'cr'):
            bits.append(' ')
        for c in list(node):
            walk(c)

    for c in list(p):
        walk(c)
    return re.sub(r'[ \t]{2,}', ' ', ''.join(bits)).strip()


def _docx_para_figs(p, rid_to_file):
    lines = []
    seen = set()
    for el in p.iter():
        rid = el.get(_R_NS + 'embed')
        if not rid or rid in seen or rid not in rid_to_file:
            continue
        seen.add(rid)
        lines.append(_fig_tex(rid_to_file[rid]))
    return lines


def _docx_blocks(el, out, rid_to_file=None):
    rid_to_file = rid_to_file or {}
    for node in list(el):
        loc = _xml_local(node.tag)
        if loc == 'p':
            line = _docx_p_line(node)
            if line:
                out.append(line)
            out.extend(_docx_para_figs(node, rid_to_file))
        elif loc == 'tbl':
            for tr in node.findall(_W_NS + 'tr'):
                cells = []
                for tc in tr.findall(_W_NS + 'tc'):
                    cells.append(' '.join(_docx_p_line(p) for p in tc.findall(_W_NS + 'p')).strip())
                    for p in tc.findall(_W_NS + 'p'):
                        out.extend(_docx_para_figs(p, rid_to_file))
                row = ' | '.join(c for c in cells if c)
                if row:
                    out.append(row)
        elif loc in ('sdt', 'sdtContent', 'tc', 'body'):
            _docx_blocks(node, out, rid_to_file)


def _image_px(raw, ext):
    if ext == 'png' and raw[:8] == b'\x89PNG\r\n\x1a\n' and len(raw) >= 24:
        return int.from_bytes(raw[16:20], 'big'), int.from_bytes(raw[20:24], 'big')
    if ext in ('jpg', 'jpeg') and raw[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(raw):
            if raw[i] != 0xFF:
                i += 1
                continue
            marker = raw[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h = int.from_bytes(raw[i + 5:i + 7], 'big')
                w = int.from_bytes(raw[i + 7:i + 9], 'big')
                return w, h
            if marker in (0xD8, 0xD9):
                i += 2
                continue
            if i + 4 > len(raw):
                break
            seglen = int.from_bytes(raw[i + 2:i + 4], 'big')
            if seglen < 2:
                break
            i += 2 + seglen
    return 0, 0


def _docx_images(zf, root, limit=6):
    rel_name = 'word/_rels/document.xml.rels'
    if rel_name not in zf.namelist():
        return []
    id_to_target = {}
    try:
        rel_root = ET.fromstring(zf.read(rel_name))
    except ET.ParseError:
        return []
    for rel in list(rel_root):
        rid = rel.get('Id')
        target = rel.get('Target') or ''
        if rid and target:
            id_to_target[rid] = target.replace('\\', '/')
    found = []
    seen = set()
    hashes = set()
    for el in root.iter():
        rid = el.get(_R_NS + 'embed') or el.get(_R_NS + 'id')
        if not rid or rid in seen or rid not in id_to_target:
            continue
        seen.add(rid)
        target = id_to_target[rid]
        if target.startswith('/'):
            zpath = target.lstrip('/')
        else:
            zpath = posixpath.normpath(posixpath.join('word', target))
        if zpath not in zf.namelist():
            continue
        raw = zf.read(zpath)
        if not raw or len(raw) < 2500 or len(raw) > 1_500_000:
            continue
        ext = zpath.rsplit('.', 1)[-1].lower()
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext)
        if not mime:
            continue
        w, h = _image_px(raw, ext)
        if w and h and (w < 64 or h < 64):
            continue
        digest = hashlib.sha1(raw).hexdigest()
        if digest in hashes:
            continue
        hashes.add(digest)
        ext_name = 'jpg' if ext == 'jpeg' else ext
        found.append({'mime': mime, 'ext': ext_name, 'data': base64.b64encode(raw).decode('ascii'), 'raw': raw, 'sha': digest[:10], 'file': 'images/w-' + digest[:10] + '.' + ext_name, 'rid': rid})
        if len(found) >= limit:
            break
    return found


def _ole_images(blob, limit=16):
    """Ảnh nhúng trong Word .doc, theo đúng thứ tự xuất hiện trong file."""
    blob = bytes(blob or b'')
    bag = []
    hashes = set()

    def add(offset, raw, ext):
        if len(bag) >= 40 or not raw or len(raw) < 2500 or len(raw) > 1_500_000:
            return
        w, h = _image_px(raw, ext)
        if w and h and (w < 64 or h < 64):
            return
        digest = hashlib.sha1(raw).hexdigest()
        if digest in hashes:
            return
        hashes.add(digest)
        mime = {'png': 'image/png', 'jpg': 'image/jpeg'}.get(ext, 'image/png')
        bag.append((offset, {
            'mime': mime,
            'ext': ext,
            'data': base64.b64encode(raw).decode('ascii'),
            'raw': raw,
            'sha': digest[:10],
            'file': 'images/w-' + digest[:10] + '.' + ext,
        }))

    sig = b'\x89PNG\r\n\x1a\n'
    i = 0
    while True:
        j = blob.find(sig, i)
        if j < 0:
            break
        k = blob.find(b'IEND', j + 8)
        if k < 0:
            i = j + 8
            continue
        add(j, blob[j:k + 8], 'png')
        i = k + 8
    i = 0
    sig = b'\xff\xd8\xff'
    while True:
        j = blob.find(sig, i)
        if j < 0:
            break
        k = blob.find(b'\xff\xd9', j + 3)
        if k < 0:
            break
        add(j, blob[j:k + 2], 'jpg')
        i = k + 2
    bag.sort(key=lambda item: item[0])
    return [im for _, im in bag[:limit]]


_OLE_MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'


def _fig_tex(name):
    return '\\begin{center}\\includegraphics[width=0.55\\linewidth]{%s}\\end{center}' % name


def _ole_marked_text(blob, images):
    """Chữ trong Word .doc, mỗi ảnh đứng ngay chỗ nó nằm trong câu."""
    try:
        import olefile
    except Exception:
        return ''
    blob = bytes(blob or b'')
    try:
        ole = olefile.OleFileIO(io.BytesIO(blob))
    except Exception:
        return ''
    try:
        if not ole.exists('WordDocument'):
            return ''
        word = ole.openstream('WordDocument').read()
        if len(word) < 0x1AA:
            return ''
        flags = int.from_bytes(word[0x000A:0x000C], 'little')
        table_name = '1Table' if flags & 0x0200 else '0Table'
        if not ole.exists(table_name):
            return ''
        table = ole.openstream(table_name).read()
        fc_clx = int.from_bytes(word[0x01A2:0x01A6], 'little')
        lcb_clx = int.from_bytes(word[0x01A6:0x01AA], 'little')
        if lcb_clx < 5 or fc_clx < 0 or fc_clx + lcb_clx > len(table):
            return ''
        clx = table[fc_clx:fc_clx + lcb_clx]
        i = 0
        while i < len(clx) and clx[i] == 1:
            i += 1
            if i + 2 > len(clx):
                return ''
            cb = int.from_bytes(clx[i:i + 2], 'little')
            i += 2 + cb
        if i >= len(clx) or clx[i] != 2:
            return ''
        i += 1
        lcb = int.from_bytes(clx[i:i + 4], 'little')
        i += 4
        if lcb < 4 or (lcb - 4) % 12 or i + lcb > len(clx):
            return ''
        plc = clx[i:i + lcb]
        n = (lcb - 4) // 12
        chars = []
        for pi in range(n):
            cp0 = int.from_bytes(plc[pi * 4:pi * 4 + 4], 'little')
            cp1 = int.from_bytes(plc[(pi + 1) * 4:(pi + 2) * 4], 'little')
            pcd = plc[(n + 1) * 4 + pi * 8:(n + 1) * 4 + (pi + 1) * 8]
            if len(pcd) < 6:
                continue
            fc = int.from_bytes(pcd[2:6], 'little')
            compressed = bool(fc & 0x40000000)
            fc &= 0x3FFFFFFF
            length = cp1 - cp0
            if length <= 0 or length > 500000:
                continue
            if compressed:
                fc //= 2
                raw = word[fc:fc + length]
                chars.append(raw.decode('cp1252', 'replace'))
            else:
                raw = word[fc:fc + length * 2]
                chars.append(raw.decode('utf-16le', 'replace'))
    finally:
        ole.close()
    full = ''.join(chars)
    figs = [_fig_tex(im.get('file')) for im in images if im.get('file')]
    out = []
    fi = 0
    for ch in full:
        if ch == '\x01':
            if fi < len(figs):
                out.append('\n' + figs[fi] + '\n')
                fi += 1
        elif ch in '\r\x07\x0b':
            out.append('\n')
        elif ch >= ' ' or ch == '\n':
            out.append(ch)
    return re.sub(r'\n{3,}', '\n\n', ''.join(out)).strip()


def _docx_extract(blob):
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        return '', [], 'File không phải Word .docx (hãy Lưu thành .docx).'
    try:
        if 'word/document.xml' not in zf.namelist():
            return '', [], 'File Word không có nội dung.'
        try:
            root = ET.fromstring(zf.read('word/document.xml'))
        except ET.ParseError:
            return '', [], 'Không đọc được nội dung Word.'
        lines = []
        body = root.find(_W_NS + 'body')
        images = _docx_images(zf, root, limit=16)
        rid_to_file = {im['rid']: im['file'] for im in images if im.get('rid') and im.get('file')}
        _docx_blocks(body if body is not None else root, lines, rid_to_file)
        text = '\n'.join(lines).strip()
        for im in images:
            im.pop('raw', None)
            im.pop('rid', None)
    finally:
        zf.close()
    if len(text) < 20 and not images:
        return '', [], 'File Word gần như không có chữ.'
    return text[:80000], images, ''


def _save_docx_images(path, blob):
    """Tách ảnh nhúng trong Word, bỏ icon nhỏ, ghi vài ảnh vào images/ của bài."""
    from app import github_file_sha, github_put_bytes, lesson_folder
    folder = lesson_folder(path)
    if not str(folder).startswith('ngan-hang/'):
        return [], 'Thiếu bài để lưu ảnh.'
    images = []
    if bytes(blob[:8]) == _OLE_MAGIC:
        images = _ole_images(blob)
    else:
        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
        except zipfile.BadZipFile:
            return [], 'File không phải Word .docx. File .doc cũ vẫn tách được nếu là Word.'
        try:
            if 'word/document.xml' not in zf.namelist():
                return [], 'File Word không có nội dung.'
            try:
                root = ET.fromstring(zf.read('word/document.xml'))
            except ET.ParseError:
                return [], 'Không đọc được nội dung Word.'
            images = _docx_images(zf, root, limit=12)
        finally:
            zf.close()
    saved = []
    for im in images:
        raw = im.get('raw') or b''
        if not raw:
            continue
        ext = im.get('ext') or 'png'
        name = 'w-' + str(im.get('sha') or 'img') + '.' + ext
        rel = folder.rstrip('/') + '/images/' + name
        sha = None
        try:
            sha = github_file_sha(rel) or None
        except Exception:
            sha = None
        web = '/bank-img/' + urllib.parse.quote(rel[len('ngan-hang/'):], safe='/')
        preview = raw if len(raw) <= 350_000 else b''
        item = {
            'name': name,
            'file': 'images/' + name,
            'url': web,
            'mime': im.get('mime') or 'image/png',
            'data': base64.b64encode(preview).decode('ascii') if preview else '',
        }
        try:
            github_put_bytes(rel, raw, 'ADMIN ảnh từ Word ' + name, sha)
        except Exception as e:
            saved.append(item)
            return saved, str(e)
        saved.append(item)
    return saved, ''


@app.post('/api/admin/docx-images')
def api_admin_docx_images():
    if not can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN.'), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get('path') or '').replace('\\', '/').strip()
    if not path.startswith('ngan-hang/'):
        return jsonify(ok=False, error='Thiếu bài học để lưu ảnh.'), 400
    blob, err = _b64_blob(data.get('docx') or data.get('source_docx') or '')
    if err or not blob:
        return jsonify(ok=False, error=err or 'Chưa có file Word.'), 400
    if len(blob) > 6_000_000:
        return jsonify(ok=False, error='File Word quá lớn (dưới 6MB).'), 400
    saved, serr = _save_docx_images(path, blob)
    if serr and not saved:
        return jsonify(ok=False, error=serr), 400
    return jsonify(ok=True, n=len(saved), images=saved, error=serr or '')


def _b64_blob(raw):
    s = str(raw or '').strip()
    if s.startswith('data:'):
        s = s.split(',', 1)[-1]
    s = re.sub(r'\s+', '', s)
    if not s:
        return b'', ''
    try:
        return base64.b64decode(s, validate=True), ''
    except Exception:
        return b'', 'Dữ liệu file không hợp lệ.'


def _image_files_from_payload(data):
    raw = (data or {}).get('image_files') or []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[:12]:
        s = str(item or '').replace('\\', '/').strip().lstrip('/')
        if not re.fullmatch(r'images/w-[0-9a-f]{6,40}\.(?:png|jpe?g|gif|webp)', s, re.I):
            continue
        if s not in out:
            out.append(s)
    return out


def _place_images_from_source(latex, source):
    """Ảnh chỉ vào câu mà Word đã đặt nó, không rải sang câu khác."""
    source = source or ''
    files_in_source = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{(images/w-[^}]+)\}', source)
    if not files_in_source or not latex:
        return latex
    parts = re.split(r'(?=Câu\s+\d+\s*[\.:])', source)
    chunks = []
    for part in parts:
        files = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{(images/w-[^}]+)\}', part)
        words = set(re.findall(r'[0-9A-Za-z\u00C0-\u1EF9]{6,}', part.lower()))
        if files:
            chunks.append((words, files))
    if not chunks:
        return latex

    def strip_figs(body):
        return re.sub(
            r'\\begin\{center\}(?:(?!\\end\{center\}).)*\\includegraphics(?:(?!\\end\{center\}).)*\\end\{center\}\s*',
            '',
            body,
            flags=re.S,
        )

    matches = list(re.finditer(r'\\begin\s*\{ex\}.*?\\end\s*\{ex\}', latex, re.S))
    if not matches:
        return latex
    used = set()
    chosen = {}
    for mi, m in enumerate(matches):
        words = set(re.findall(r'[0-9A-Za-z\u00C0-\u1EF9]{6,}', strip_figs(m.group(0)).lower()))
        best_i, best_score = None, 0
        for ci, (cw, _files) in enumerate(chunks):
            if ci in used:
                continue
            score = sum(len(w) for w in (words & cw))
            if score > best_score:
                best_i, best_score = ci, score
        if best_i is not None and best_score >= 28:
            used.add(best_i)
            chosen[mi] = chunks[best_i][1]
    if not chosen:
        return latex
    out = latex
    for mi, m in reversed(list(enumerate(matches))):
        files = chosen.get(mi) or []
        body = strip_figs(m.group(0))
        if files:
            snippet = '\n'.join(_fig_tex(name) for name in files) + '\n'
            cut = re.search(r'\\choiceTF|\\choice|\\shortans|\\loigiai', body)
            if cut:
                body = body[:cut.start()] + snippet + body[cut.start():]
            else:
                body = body.replace('\\end{ex}', snippet + '\\end{ex}', 1)
        out = out[:m.start()] + body + out[m.end():]
    return out


def _images_from_payload(data):
    raw = (data or {}).get('source_images') or (data or {}).get('images') or []
    if not isinstance(raw, list):
        return []
    out = []
    allow = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
    for item in raw[:4]:
        if not isinstance(item, dict):
            continue
        mime = str(item.get('mime') or item.get('mime_type') or 'image/jpeg').split(';', 1)[0].strip().lower()
        if mime not in allow:
            continue
        blob, err = _b64_blob(item.get('data'))
        if err or not blob or len(blob) > 1_600_000:
            continue
        out.append({'mime': mime, 'data': base64.b64encode(blob).decode('ascii')})
    return out


def _named_b64_list(data, many_key, one_key, limit=6):
    items = []
    raw = (data or {}).get(many_key)
    if isinstance(raw, list):
        for it in raw[:limit]:
            if isinstance(it, dict):
                b64 = str(it.get('b64') or it.get('data') or '').strip()
                name = str(it.get('name') or '').strip() or 'tep'
            else:
                b64 = str(it or '').strip()
                name = 'tep'
            if b64:
                items.append((name[:80], b64))
    if not items:
        one = str((data or {}).get(one_key) or '').strip()
        if one:
            items.append(('tep', one))
    return items[:limit]


def _join_named(parts, cap=80000):
    out, used = [], 0
    for name, text in parts:
        text = str(text or '').strip()
        if not text:
            continue
        block = '===== ' + str(name or 'nguon') + ' =====\n' + text
        if used >= cap:
            break
        if used + len(block) > cap:
            block = block[: max(0, cap - used)]
        if block:
            out.append(block)
            used += len(block) + 2
    return '\n\n'.join(out).strip()


def _docx_from_payload(data):
    raw = str((data or {}).get('source_docx') or '').strip()
    if not raw:
        return '', [], ''
    blob, err = _b64_blob(raw)
    if err:
        return '', [], err
    if not blob:
        return '', [], ''
    if len(blob) > 6_000_000:
        return '', [], 'File Word quá lớn (dưới 6MB).'
    if bytes(blob[:8]) == _OLE_MAGIC:
        images = _ole_images(blob)
        text = _ole_marked_text(blob, images)
        for im in images:
            im.pop('raw', None)
        return text, images, ''
    return _docx_extract(blob)


def _pdf_page_jpeg(page):
    import fitz
    for zoom, quality in ((1.35, 62), (1.05, 50)):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        raw, mime = None, 'image/jpeg'
        try:
            raw = pix.tobytes('jpeg', jpg_quality=quality)
        except Exception:
            try:
                raw = pix.tobytes('jpg')
            except Exception:
                raw = pix.tobytes('png')
                mime = 'image/png'
        if raw and len(raw) <= 1_500_000:
            return {'mime': mime, 'data': base64.b64encode(raw).decode('ascii')}
    return None


def _pdf_extract(blob):
    try:
        import fitz
    except Exception:
        return '', [], 'Máy chủ chưa có thư viện đọc PDF.'
    try:
        doc = fitz.open(stream=blob, filetype='pdf')
    except Exception:
        return '', [], 'Không đọc được file PDF.'
    lines = []
    images = []
    try:
        total = doc.page_count or 0
        n = min(total, 12)
        if total > n:
            lines.append('(PDF có %d trang, chỉ đọc %d trang đầu.)' % (total, n))
        for i in range(n):
            page = doc.load_page(i)
            text = re.sub(r'\n{3,}', '\n\n', (page.get_text('text') or '')).strip()
            if text:
                lines.append('--- Trang %d ---\n%s' % (i + 1, text))
            sparse = len(re.sub(r'\s+', '', text)) < 40
            if sparse and len(images) < 4:
                shot = _pdf_page_jpeg(page)
                if shot:
                    images.append(shot)
    finally:
        doc.close()
    text_out = '\n\n'.join(lines).strip()
    if len(text_out) < 20 and not images:
        return '', [], 'File PDF gần như không có chữ.'
    return text_out[:80000], images, ''


def _pdf_from_payload(data):
    raw = str((data or {}).get('source_pdf') or '').strip()
    if not raw:
        return '', [], ''
    blob, err = _b64_blob(raw)
    if err:
        return '', [], err
    if not blob:
        return '', [], ''
    if len(blob) > 8_000_000:
        return '', [], 'File PDF quá lớn (dưới 8MB).'
    if not blob.startswith(b'%PDF'):
        return '', [], 'File không phải PDF.'
    return _pdf_extract(blob)


def _page_text_from_payload(data):
    """Ưu tiên file .tex gửi từ máy ADMIN; không thì tải http/https."""
    data = data or {}
    raw = str(data.get('source_tex') or data.get('source_text') or data.get('tex') or '')
    if raw.strip():
        return raw.replace('\r\n', '\n')[:80000], ''
    url = str(data.get('source_url') or data.get('url') or '').strip()
    if url:
        return _fetch_public_page(url)
    return '', ''

def _gemini_fill_raw(keys, prompt, tok, temp=0.25, images=None):
    from student_gemini import _gemini_generate
    raw, err = '', ''
    for key in keys:
        try:
            raw = _gemini_generate(key, prompt, tok, temp, images)
            err = ''
            break
        except Exception as e:
            err = str(e)
            raw = ''
    return raw, err

def _kind_rules_all():
    from admin_rewrite import kind_structure_text
    parts = [
        'Mỗi câu một khối \\begin{ex}...\\end{ex}. Công thức $...$. Không markdown, không % ID, không \\dangbt (trừ khi được yêu cầu).\n',
        kind_structure_text('TN'),
        'TN LaTeX:\n\\begin{ex}\nĐề...\n\\choice\n{\\True phương án đúng}\n{sai}\n{sai}\n{sai}\n\\loigiai{...}\n\\end{ex}\n',
        kind_structure_text('DS'),
        'ĐS LaTeX:\n\\begin{ex}\nXét các phát biểu sau.\n\\choiceTF\n{\\True mệnh đề đúng}\n{mệnh đề sai}\n{...}\n{...}\n\\loigiai{a đúng vì ...; b sai vì ...}\n\\end{ex}\n',
        kind_structure_text('TLN'),
        'TLN LaTeX: \\shortans{12}\\loigiai{12} — cùng một số, không đơn vị.\n',
        kind_structure_text('TL'),
    ]
    return ''.join(parts)

def _fill_kind_blocks(keys, dang, kind, n, samples, tok=5000):
    from admin_rewrite import kind_structure_text
    if n <= 0:
        return []
    lab = {'TN': 'trắc nghiệm 4 lựa chọn', 'DS': 'đúng/sai 4 mệnh đề', 'TLN': 'trả lời ngắn', 'TL': 'tự luận'}.get(kind, kind)
    sample_txt = '\n'.join(f'- {k}: {t}' for k, t in samples if not k or k == kind) or '(chưa có cùng loại)'
    prompt = (
        f'Bạn là giáo viên ra đề thi THPT. Viết ĐÚNG {n} câu loại {kind} ({lab}) về dạng: {dang}\n'
        'Chỉ trả về các khối \\begin{ex}...\\end{ex}. Không markdown, không lời dẫn.\n'
        'CẤM viết loại khác. CẤM biến thể cùng số liệu. CẤM trùng mẫu dưới.\n'
        + kind_structure_text(kind)
        + ('ĐS: stem ngắn «Xét các phát biểu sau»; \\choiceTF đủ 4 mệnh đề; CẤM câu hỏi «tính chất nào / đâu là».\n' if kind == 'DS' else '')
        + ('TLN: đề đủ số liệu trước \\shortans. \\shortans{chỉ số}. \\loigiai{công thức, đổi đơn vị, tính ra số — CẤM chỉ ghi một số}.\n' if kind == 'TLN' else '')
        + 'Mỗi câu phải có \\loigiai{...}. Công thức trong $...$. Không \\dangbt, không % ID.\n'
        'Mẫu đang có (cấm trùng):\n' + sample_txt
    )
    raw, _err = _gemini_fill_raw(keys, prompt, tok, 0.25)
    raw = re.sub(r'^```(?:latex|tex)?\s*|\s*```$', '', (raw or '').strip(), flags=re.I)
    kept = [b for b in _extract_ex_blocks(raw) if _block_ok_for_kind(b, kind)]
    if len(kept) < n:
        more = (
            prompt
            + f'\n\nLần trước chỉ nhận được {len(kept)}/{n} câu ĐÚNG cấu trúc {kind}. '
            f'Viết THÊM {n - len(kept)} câu {kind} nữa, không lặp.\n'
        )
        extra, _ = _gemini_fill_raw(keys, more, tok, 0.2)
        extra = re.sub(r'^```(?:latex|tex)?\s*|\s*```$', '', (extra or '').strip(), flags=re.I)
        for b in _extract_ex_blocks(extra):
            if _block_ok_for_kind(b, kind) and b not in kept:
                kept.append(b)
            if len(kept) >= n:
                break
    return kept[:n]

def _chapter_lessons(mon, lop, chuong):
    from app import _lesson_sort_key, index_data, merge_catalog_lessons
    raw = [x for x in (index_data().get('lessons') or []) if isinstance(x, dict)]
    items = merge_catalog_lessons(raw)
    key = (str(mon or '').strip(), str(lop or '').strip(), str(chuong or '').strip())
    sibs = [
        x for x in items
        if (
            str(x.get('Mon') or '').strip(),
            str(x.get('Lop') or '').strip(),
            str(x.get('Chuong') or '').strip(),
        ) == key
    ]
    sibs.sort(key=_lesson_sort_key)
    return sibs


def _lesson_title(item):
    return str((item or {}).get('BaiHoc') or (item or {}).get('De') or '').strip()


def _chapter_brief(sibs):
    from app import dang_pairs_of
    lines = []
    packs = []
    for item in sibs[:12]:
        title = _lesson_title(item)
        path = str(item.get('path') or item.get('file') or '').replace('\\', '/')
        if not title or not path.startswith('ngan-hang/'):
            continue
        pairs = dang_pairs_of(item)
        names = [n for n, _c in pairs if n]
        dang_lines = []
        for name, cnt in pairs:
            if not name or name == 'Chưa phân dạng':
                continue
            dang_lines.append('- «' + name + '» (' + str(cnt) + ' câu)')
            if len(dang_lines) >= 14:
                break
        lines.append('## Bài: ' + title + '\n' + ('\n'.join(dang_lines) or '- (chưa có dạng — tự đặt tên ngắn)'))
        packs.append({'title': title, 'path': path, 'names': names, 'qs': None})
    return '\n'.join(lines)[:8000], packs


def _triples_from_import(text):
    text = str(text or '')
    marks = [(m.start(), 'b', (m.group(1) or '').strip()) for m in re.finditer(r'\\baibt\s*\{([^{}]*)\}', text, re.I)]
    marks += [(m.start(), 'd', (m.group(1) or '').strip()) for m in re.finditer(r'\\dang(?:bt)?\s*\{([^{}]*)\}', text, re.I)]
    marks += [(m.start(), 'e', m.group(0).strip()) for m in re.finditer(r'\\begin\s*\{\s*ex\s*\}.*?\\end\s*\{\s*ex\s*\}', text, re.I | re.S)]
    bai, dang = '', 'Chưa phân dạng'
    out = []
    for _, kind, val in sorted(marks, key=lambda x: x[0]):
        if kind == 'b':
            bai = val or bai
        elif kind == 'd':
            dang = val or dang
        else:
            out.append((bai, dang, val))
    return out


def _fill_chapter_work(data, page_text, images, source_url, n_files):
    from app import dang_tex_anchor
    job = str((data or {}).get('_job') or '')
    mon = str(data.get('mon') or '').strip()
    lop = str(data.get('lop') or '').strip()
    chuong = str(data.get('chuong') or '').strip()
    sibs = _chapter_lessons(mon, lop, chuong)
    if len(sibs) < 1:
        return jsonify(ok=False, error='Không thấy bài nào trong chương này.'), 400
    if not str(page_text or '').strip() and not images:
        return jsonify(ok=False, error='Thả file Word, PDF, TEX hoặc dán chữ của cả chương, rồi bấm AI phân tích.'), 400
    _fill_progress(job, 'Đang đối chiếu bài và dạng trong chương…')
    brief, packs = _chapter_brief(sibs)
    if not packs:
        return jsonify(ok=False, error='Chương chưa có bài để lọc vào.'), 400
    titles = [p['title'] for p in packs]
    by_title = {p['title']: p for p in packs}
    keys = _keys_from_payload_safe(data)
    kind_rules = (
        'Mỗi câu một khối \\begin{ex}...\\end{ex}. Công thức $...$. Có \\loigiai. Không markdown, không % ID.\n'
        'TN: \\choice 4 ý, một \\True. ĐS: \\choiceTF đúng 4 mệnh đề. TLN: \\shortans{chỉ số}.\n'
    )
    src_all = str(page_text or '')[:54000]
    step = 18000
    parts = [src_all[i:i + step] for i in range(0, len(src_all), step)][:4]
    if not parts:
        parts = ['']
    use_images = images if (images and len(src_all) < 4000) else None
    raw_all = []
    last_err = ''
    for i, piece in enumerate(parts, 1):
        _fill_progress(job, 'AI đang tách lô ' + str(i) + '/' + str(len(parts)) + ' — cứ để trang mở.')
        prompt = (
            'Bạn là giáo viên ra đề thi THPT. Nguồn có thể là cả chương (Word/PDF/TEX/link).\n'
            'Tách TỪNG CÂU rồi lọc vào ĐÚNG BÀI và ĐÚNG DẠNG đã có trong chương «' + chuong + '».\n'
            'Bỏ câu thuộc chương khác. Không bịa đề không có trong nguồn.\n'
            'Với MỖI câu, đúng thứ tự:\n'
            '\\baibt{Tên bài chép đúng một bài dưới đây}\n'
            '\\dangbt{Tên dạng chép đúng một dạng của bài đó}\n'
            '\\begin{ex}...\\end{ex}\n'
            'Chỉ đặt dạng mới khi bài đó chưa có dạng cùng kỹ năng. Không markdown.\n'
            + kind_rules
            + 'Các bài và dạng đang có:\n' + brief
            + '\n\nNguồn (lô ' + str(i) + '/' + str(len(parts)) + '):\n' + piece
        )
        raw, err = _gemini_fill_raw(keys, prompt, 8000, 0.2, use_images if i == 1 else None)
        last_err = err or last_err
        if raw:
            raw = re.sub(r'^```(?:latex|tex)?\s*|\s*```$', '', raw.strip(), flags=re.I)
            raw_all.append(raw)
    if not raw_all:
        return jsonify(ok=False, error='AI không viết được: ' + (last_err or 'trống')), 400
    _fill_progress(job, 'Đang lọc trùng và gán vào bài…')
    triples = _triples_from_import('\n\n'.join(raw_all))
    if not triples:
        return jsonify(ok=False, error='AI không ra khối \\begin{ex}. Thử lại.'), 400
    grouped = {}
    skipped_bai = 0
    for bai0, dang0, block in triples:
        bai = _snap_dang_name(bai0, titles)
        pack = by_title.get(bai)
        if not pack:
            skipped_bai += 1
            continue
        dang = _snap_dang_name(dang0, pack['names']) if pack['names'] else (dang0 or 'Chưa phân dạng')
        grouped.setdefault(bai, []).append((dang, block))
    kept_bits = []
    n_dup = n_bad = n_keep = 0
    per_bai = []
    for title in titles:
        rows = grouped.get(title) or []
        if not rows:
            continue
        pack = by_title[title]
        if pack.get('qs') is None:
            try:
                pack['qs'] = parse_lesson_questions(pack['path'])
            except Exception:
                pack['qs'] = []
        kept, skipped = _filter_import_rows(rows, pack['qs'], '', relax=False)
        n_dup += sum(1 for s in skipped if ('trùng' in s or 'cùng ý' in s or 'trần' in s))
        n_bad += sum(1 for s in skipped if 'sai cấu trúc' in s)
        if not kept:
            continue
        n_keep += len(kept)
        per_bai.append(title + ': ' + str(len(kept)) + ' câu')
        chunk = ['\\baibt{' + title + '}']
        for dang, block in kept:
            chunk.append('\\dangbt{' + dang + '}\n' + block)
        kept_bits.append('\n'.join(chunk))
    latex = _latex_with_nguon('\n\n'.join(kept_bits).strip() + ('\n' if kept_bits else ''), source_url)
    if not n_keep:
        extra = (' Bỏ ' + str(skipped_bai) + ' câu không thuộc bài nào trong chương.') if skipped_bai else ''
        summary = 'Đã lọc hết câu gần trùng hoặc không thuộc chương này.' + extra
        return jsonify(ok=True, latex='', n=0, summary=summary, chapter=True)
    bits = []
    if n_dup:
        bits.append(str(n_dup) + ' câu gần trùng hoặc vượt trần')
    if n_bad:
        bits.append(str(n_bad) + ' câu sai cấu trúc')
    if skipped_bai:
        bits.append(str(skipped_bai) + ' câu không thuộc bài trong chương')
    skip_txt = (' Đã lọc bỏ ' + ', '.join(bits) + '.') if bits else ''
    summary = (
        'Giữ ' + str(n_keep) + ' câu từ ' + str(max(1, n_files)) + ' nguồn, tách vào '
        + str(len(per_bai)) + ' bài. ' + ' · '.join(per_bai) + '.' + skip_txt
        + ' Xem ô LaTeX rồi bấm Chấp nhận ghi TEX.'
    )
    src, _line = dang_tex_anchor(packs[0]['path'], '', qs=packs[0].get('qs') or [])
    return jsonify(ok=True, src=src, latex=latex, n=n_keep, summary=summary, chapter=True)


def _keys_from_payload_safe(data):
    from student_gemini import _keys_from_payload
    return _keys_from_payload(data)


def _dang_fill_work(data):
    from app import KIND_CHIP_LABS, KIND_ORDER, dang_kind_counts_of, dang_tex_anchor, kind_gap_heuristic, load_lesson_questions, questions_in_scope
    from student_gemini import _keys_from_payload
    data = data or {}
    path = str(data.get('path') or '').replace('\\', '/').strip()
    dang = str(data.get('dang') or '').strip()
    if not path.startswith('ngan-hang/'):
        return jsonify(ok=False, error='Thiếu path bài.'), 400
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error='Nạp key Gemini rồi bấm lại.'), 400
    source_url = str(data.get('source_url') or data.get('url') or '').strip()
    page_text, ferr = _page_text_from_payload(data)
    if ferr:
        return jsonify(ok=False, error=ferr), 400
    image_files = _image_files_from_payload(data)
    parts = []
    if page_text.strip():
        parts.append(('Chữ / TEX', page_text))
    docx_images, pdf_images = [], []
    n_files = 1 if page_text.strip() else 0
    for name, b64 in _named_b64_list(data, 'source_docxs', 'source_docx'):
        text, images, err = _docx_from_payload({'source_docx': b64})
        if err:
            return jsonify(ok=False, error=name + ': ' + err), 400
        n_files += 1
        if text.strip():
            parts.append((name, text))
        docx_images.extend(images or [])
    for name, b64 in _named_b64_list(data, 'source_pdfs', 'source_pdf'):
        text, images, err = _pdf_from_payload({'source_pdf': b64})
        if err:
            return jsonify(ok=False, error=name + ': ' + err), 400
        n_files += 1
        if text.strip():
            parts.append((name, text))
        pdf_images.extend(images or [])
    if parts:
        page_text = _join_named(parts)
    for im in list(docx_images) + list(pdf_images):
        name = str((im or {}).get('file') or '')
        if name and name not in image_files and re.fullmatch(r'images/w-[0-9a-f]{6,40}\.(?:png|jpe?g|gif|webp)', name, re.I):
            image_files.append(name)
    image_files = image_files[:12]
    if image_files:
        images = []
    else:
        images = (_images_from_payload(data) + pdf_images + docx_images)[:4]
    if images and not page_text.strip():
        page_text = 'Nguồn là hình đính kèm. Hãy đọc đề, phương án và lời giải trên hình.'
    if str(data.get('chapter') or '') in ('1', 'true', 'yes'):
        return _fill_chapter_work(data, page_text, images, source_url, n_files)
    if not dang and not page_text:
        return jsonify(ok=False, error='Chọn file .tex trên máy hoặc dán link, rồi bấm AI từ file/link (không cần chọn dạng).'), 400
    try:
        qs = load_lesson_questions(path)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    from app import dang_names_of
    names, _cnts = dang_names_of(qs)
    per, _allc = dang_kind_counts_of(qs)
    counts = {k: int((per.get(dang) or {}).get(k) or 0) for k in KIND_ORDER} if dang else {k: int((_allc or {}).get(k) or 0) for k in KIND_ORDER}
    add = data.get('add') if isinstance(data.get('add'), dict) else (kind_gap_heuristic(counts) if dang else {})
    add = _cap_fill_add(add, counts) if dang else {k: 0 for k in KIND_ORDER}
    if dang and not page_text and not any(add.values()):
        return jsonify(ok=False, error='Dạng này chưa cần thêm câu (hoặc bấm Đếm số câu thiếu trước).'), 400
    samples = []
    for q in (questions_in_scope(qs, dang) if dang else qs)[:3]:
        samples.append((str(q.get('kind') or ''), str(q.get('text') or '')[:280]))
    want = ', '.join(f"{lab} {add[k]}" for k, lab in KIND_CHIP_LABS if add.get(k)) or 'các câu trên trang'
    dang_list = '; '.join(names) if names else '(chưa có dạng — tự đặt tên ngắn, rõ)'
    dang_brief = _existing_dang_brief(qs, names)
    nguon_line = '\\nguon{' + _tex_nguon_url(source_url) + '}' if source_url else ''
    kind_rules = (
        _kind_rules_all()
        + "Mỗi câu có \\loigiai{...} (trang không có lời giải thì viết ngắn đúng đáp án). Không % ID.\n"
        + ("Trong MỖI khối \\begin{ex} phải có đúng một " + nguon_line + " (link tải trang, không đổi).\n" if nguon_line else "")
    )
    if image_files:
        kind_rules += (
            "Ảnh đã đứng sẵn trong nguồn bằng \\includegraphics, ngay câu của nó. "
            "Giữ mỗi ảnh trong đúng câu đó. Không chuyển ảnh sang câu khác, không rải ảnh theo thứ tự file.\n"
            + '\n'.join('- ' + name for name in image_files) + '\n'
        )
    elif images:
        kind_rules += (
            "Nếu ảnh có đồ thị, trục số, sơ đồ, mạch hoặc hình học: vẽ lại bằng TikZ trong câu, bọc \\begin{center}...\\end{center}.\n"
            "TikZ biên dịch bằng pdflatex: chỉ \\draw, \\node, \\path, \\fill, \\foreach; mũi tên >=stealth.\n"
            "Nhãn tiếng Việt có dấu dùng \\text{...}, cấm \\mathrm với chữ có dấu.\n"
            "Không \\usetikzlibrary, không pgfplots. Giữ đúng số và ký hiệu trên hình. Không bịa hình không có trong ảnh.\n"
        )
    if page_text and not dang:
        prompt = (
            "Bạn là giáo viên ra đề thi THPT. Chuyển đề từ Word, PDF, ảnh chụp, chữ thường, trang web hoặc file LaTeX sang ngân hàng.\n"
            "CHỈ lấy câu thuộc BÀI đang soạn (đúng chủ đề các dạng dưới). Bỏ bài/chương khác trong cùng file.\n"
            "Gán vào dạng đã có; mỗi dạng cố gắng 9 TN / 2 ĐS / 3 TLN / 4 TL, trần 18 / 4 / 6 / 8.\n"
            "Không lấy hai câu cùng ý. Đủ mục tiêu thì chỉ lấy câu thật khác; chạm trần thì bỏ.\n"
            "Không bịa đề không có trong nguồn. Nếu nguồn là .tex: lọc \\begin{ex}, sửa cho khớp cấu trúc ngân hàng.\n"
            "Nếu có hình đính kèm: đọc hết chữ và công thức trên hình, kể cả đề viết tay, trang PDF scan hoặc ảnh trong file Word.\n"
            "Với MỖI câu, trước \\begin{ex} phải có đúng một dòng \\dangbt{Tên dạng}.\n"
            "Tách nguồn thành từng câu, rồi gán vào dạng ĐÃ CÓ bằng cách so với các câu mẫu (cùng việc phải làm), không gán chỉ vì tên na ná.\n"
            "Dạng đã có:\n" + (dang_brief or dang_list) + "\n"
            "Tên trong \\dangbt phải chép đúng một tên ở trên. Chỉ đặt tên mới khi không câu mẫu nào cùng kỹ năng.\n"
            "Không markdown, không lời dẫn.\n"
            + kind_rules
            + "Nguồn (HTML đã gỡ hoặc LaTeX gốc):\n" + page_text
        )
    elif page_text:
        prompt = (
            "Bạn là giáo viên ra đề thi THPT. Chuyển đề từ Word, PDF, ảnh chụp, chữ thường, trang web hoặc file LaTeX sang ngân hàng câu hỏi.\n"
            "Chỉ trả về các khối \\begin{ex}...\\end{ex}, không markdown, không lời dẫn.\n"
            "Dạng đang nạp: " + dang + "\n"
            "Lấy các câu trong nguồn CÙNG CHỦ ĐỀ dạng này. Ý khác nhau — bỏ biến thể cùng một bài toán.\n"
            "Không vượt trần mỗi dạng: 18 TN, 4 ĐS, 6 TLN, 8 TL. Ưu tiên đủ 9 TN, 2 ĐS, 3 TLN, 4 TL rồi dừng nếu chỉ còn câu giống.\n"
            "Không bịa đề không có trong nguồn. Không \\dangbt.\n"
            + kind_rules
            + "Nguồn:\n" + page_text
        )
    else:
        blocks = []
        miss = []
        for k, lab in KIND_CHIP_LABS:
            n = int(add.get(k) or 0)
            if n <= 0:
                continue
            got = _fill_kind_blocks(keys, dang, k, n, samples)
            blocks.extend(got)
            if len(got) < n:
                miss.append(f'{lab} {len(got)}/{n}')
        if not blocks:
            return jsonify(ok=False, error='AI không ra đúng cấu trúc từng loại (ĐS phải \\choiceTF 4 mệnh đề, TN phải \\choice 4 ý). Thử lại.'), 400
        raw = '\n\n'.join(blocks)
        if miss:
            want = want + ' — thiếu cấu trúc: ' + ', '.join(miss)
        tok = 8000
        prompt = ''
        err = ''
    if page_text:
        tok = 16000
        raw, err = _gemini_fill_raw(keys, prompt, tok, 0.25, images)
        if not raw:
            return jsonify(ok=False, error='AI không viết được: ' + (err or 'trống')), 400
        raw = re.sub(r'^```(?:latex|tex)?\s*|\s*```$', '', raw.strip(), flags=re.I)
        blocks = _extract_ex_blocks(raw)
        if len(blocks) < 4 and keys:
            more_prompt = (
                prompt
                + "\n\nLần trước chỉ ra được " + str(len(blocks)) + " câu. Trang còn nhiều câu. "
                "Viết TIẾP các khối \\begin{ex} CHƯA có, không lặp đề cũ. Vẫn đủ \\nguon và \\loigiai.\n"
                "Đã có (cấm trùng):\n" + raw[-4000:]
            )
            extra, _ = _gemini_fill_raw(keys, more_prompt, tok, 0.2, images)
            if extra:
                extra = re.sub(r'^```(?:latex|tex)?\s*|\s*```$', '', extra.strip(), flags=re.I)
                raw = (raw + '\n\n' + extra).strip()
                blocks = _extract_ex_blocks(raw)
        if not blocks:
            return jsonify(ok=False, error='AI không ra khối \\begin{ex}...\\end{ex}. Thử lại.'), 400
    src, _line = dang_tex_anchor(path, dang, qs=qs)
    latex = _import_tex_chunk(raw, dang) if (page_text and not dang) else ('\n\n'.join(blocks) + '\n')
    if not latex.strip():
        latex = '\n\n'.join(blocks) + '\n'
    rows = _chunks_from_import(latex, dang)
    kept, skipped = _filter_import_rows(rows, qs, dang, relax=False)
    if kept and page_text and not dang:
        pool = [n for n in names if n and n != 'Chưa phân dạng']
        kept = [(_snap_dang_name(d, pool), b) for d, b in kept]
    n_dup = sum(1 for s in skipped if ('trùng' in s or 'cùng ý' in s or 'trần' in s))
    n_bad = sum(1 for s in skipped if 'sai cấu trúc' in s)
    if kept:
        latex = '\n\n'.join('\\dangbt{' + d + '}\n' + b for d, b in kept) + '\n'
    elif page_text and skipped and n_bad < len(skipped):
        summary = 'Đã lọc hết ' + str(len(skipped)) + ' câu'
        if n_dup:
            summary += ' (gần trùng hoặc vượt trần: ' + str(n_dup) + ')'
        if n_bad:
            summary += ', sai cấu trúc: ' + str(n_bad)
        summary += '. Không còn câu mới để ghi.'
        return jsonify(ok=True, src='', latex='', n=0, summary=summary)
    elif page_text:
        return jsonify(ok=False, error='AI không ra câu đúng cấu trúc (\\begin{ex} + \\choice/\\choiceTF...). Thử lại hoặc sửa nguồn.'), 400
    else:
        if skipped and all('sai cấu trúc' in s for s in skipped):
            return jsonify(ok=False, error='Câu AI viết sai cấu trúc loại (ĐS = \\choiceTF 4 mệnh đề, không hỏi «nào sau đây»; TN = \\choice 4 ý). Thử lại.'), 400
        return jsonify(ok=False, error='Câu AI viết gần trùng đề đang có. Soát xóa bản thừa, đừng nhồi thêm biến thể.'), 400
    latex = _place_images_from_source(_latex_with_nguon(latex, source_url), page_text)
    nd = len(_chunks_from_import(latex, dang))
    if page_text:
        bits = []
        if n_dup:
            bits.append(str(n_dup) + ' câu gần trùng hoặc vượt trần')
        if n_bad:
            bits.append(str(n_bad) + ' câu sai cấu trúc')
        skip_txt = (' Đã lọc bỏ ' + ', '.join(bits) + '.') if bits else ' Không còn câu trùng để bỏ.'
        summary = (
            'Giữ ' + str(nd or len(blocks)) + ' câu từ ' + str(max(1, n_files)) + ' nguồn'
            + (' (gán vào dạng đang có)' if not dang else '')
            + '.' + skip_txt
            + ' Xem ô LaTeX rồi bấm Chấp nhận ghi TEX.'
        )
    else:
        skip_txt = (' Bỏ ' + str(len(skipped)) + ' câu (gần trùng / vượt trần / sai cấu trúc).') if skipped else ''
        summary = 'AI soạn ' + str(nd or len(blocks)) + ' câu (' + want + ')' + skip_txt + '. Mỗi câu có \\nguon{link}. Sửa ô LaTeX nếu cần, rồi bấm Chấp nhận ghi TEX.'
    return jsonify(ok=True, src=src, latex=latex, n=nd or len(blocks), add=add, counts=counts, summary=summary)


@app.post('/api/admin/dang-fill')
def api_admin_dang_fill():
    if not can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN.'), 403
    data = request.get_json(silent=True) or {}
    if data.get('background'):
        payload = dict(data)
        payload.pop('background', None)
        return _spawn_dang_fill(payload)
    return _dang_fill_work(data)


@app.get('/api/admin/dang-fill-job')
def api_admin_dang_fill_job():
    if not can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN.'), 403
    job = str(request.args.get('job') or '').strip()
    if not _fill_job_ok(job):
        return jsonify(ok=False, error='Không thấy phiên đang chạy. Bấm lại.'), 404
    with _FILL_LOCK:
        rec = dict(_FILL_JOBS.get(job) or {})
    if not rec:
        rec = _fill_read_json(_fill_status_path(job)) or {}
        if rec:
            with _FILL_LOCK:
                _FILL_JOBS[job] = rec
    if not rec:
        return jsonify(ok=False, error='Không thấy phiên đang chạy. Bấm lại.'), 404
    if rec.get('state') != 'done':
        _ensure_fill(job)
        started = float(rec.get('started') or rec.get('ts') or time.time())
        elapsed = max(0, int(time.time() - started))
        return jsonify(ok=True, pending=True, job=job, elapsed=elapsed, note=rec.get('note') or '')
    result = rec.get('result')
    if not isinstance(result, dict):
        disk = _fill_read_json(_fill_status_path(job)) or {}
        result = disk.get('result')
    if not isinstance(result, dict):
        return jsonify(ok=False, error='Không đọc được kết quả.')
    return jsonify(result)


def _save_chapter_fill(data, raw_tex):
    from admin_classify import _refresh_index
    from app import TOKEN, _safe_repo_file, dang_tex_anchor, github_put_text, load_lesson_questions, read_tex
    mon = str((data or {}).get('mon') or '').strip()
    lop = str((data or {}).get('lop') or '').strip()
    chuong = str((data or {}).get('chuong') or '').strip()
    triples = _triples_from_import(raw_tex)
    if not triples:
        return jsonify(ok=False, error='Không có \\begin{ex} để ghi.'), 400
    sibs = _chapter_lessons(mon, lop, chuong)
    titles = [_lesson_title(x) for x in sibs if _lesson_title(x)]
    by_title = {_lesson_title(x): x for x in sibs if _lesson_title(x)}
    grouped = {}
    for bai0, dang0, block in triples:
        bai = _snap_dang_name(bai0, titles) if titles else bai0
        if bai not in by_title:
            continue
        grouped.setdefault(bai, []).append((dang0 or 'Chưa phân dạng', block))
    if not grouped:
        return jsonify(ok=False, error='Không khớp bài nào trong chương. Giữ nguyên tên bài trong \\baibt{...}.'), 400
    written = []
    url = (data or {}).get('source_url') or ''
    for title, rows in grouped.items():
        item = by_title[title]
        path = str(item.get('path') or item.get('file') or '').replace('\\', '/')
        try:
            qs = load_lesson_questions(path)
        except Exception:
            qs = []
        src, _line = dang_tex_anchor(path, '', qs=qs)
        if not src.startswith('ngan-hang/') or not src.lower().endswith('.tex'):
            return jsonify(ok=False, error='File TEX không hợp lệ: ' + title), 400
        bits = []
        for dang, block in rows:
            bits.append('\\dangbt{' + dang + '}\n' + block)
        chunk = _latex_with_nguon('\n\n'.join(bits) + '\n', url)
        try:
            sha, tex = read_tex(src, need_sha=True)
            new = (tex or '').rstrip() + '\n' + chunk
            local = _safe_repo_file(src)[1]
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(new, encoding='utf-8')
            if TOKEN:
                github_put_text(src, new, 'ADMIN lọc cả chương vào ' + title, sha or None)
            try:
                qs2 = load_lesson_questions(path)
                _refresh_index(path, qs2)
            except Exception:
                pass
        except Exception as e:
            return jsonify(ok=False, error=title + ': ' + str(e)), 500
        written.append(title + ' ' + str(len(rows)))
    _STATS_CACHE.clear()
    _QID_CACHE.clear()
    return jsonify(ok=True, n=sum(len(v) for v in grouped.values()), src='', note='Đã ghi ' + ', '.join(written))


@app.get('/member/chapter')
def member_chapter():
    from app import dang_pairs_of, dang_view_url, page
    m = member_current()
    mon = str(request.args.get('mon') or '').strip()
    lop = str(request.args.get('lop') or '').strip()
    chuong = str(request.args.get('chuong') or '').strip()
    if not mon or not chuong:
        return redirect('/member')
    sibs = _chapter_lessons(mon, lop, chuong)
    if m:
        sibs = [x for x in sibs if can_view(m, str(x.get('path') or x.get('file') or ''))]
    if not sibs:
        return page('Chương', "<div class='wrap'><div class='panel'><div class='body'><div class='err'>Không thấy bài trong chương này.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    blocks = []
    total = 0
    for item in sibs:
        title = _lesson_title(item)
        path = str(item.get('path') or item.get('file') or '')
        n = int(item.get('questions') or item.get('count') or 0)
        total += n
        dlinks = []
        for i, (dname, cnt) in enumerate(dang_pairs_of(item), 1):
            short = dname if len(dname) <= 64 else dname[:63] + '…'
            href = dang_view_url(path, dname)
            dlinks.append(
                "<a class='drawdang' href='" + html.escape(href, quote=True) + "'><span class='drawname'>"
                + str(i) + '. ' + html.escape(short) + "</span><span class='drawn'>" + str(cnt) + "</span></a>"
            )
        bai_href = dang_view_url(path, '')
        blocks.append(
            "<details class='drawbaiwrap'><summary class='drawbai'><a href='"
            + html.escape(bai_href, quote=True) + "' onclick='event.stopPropagation()'>"
            + html.escape(title) + "</a> <span class='drawn'>" + str(n) + "</span></summary><div class='drawdangs'>"
            + (''.join(dlinks) or "<p class='muted'>Chưa có dạng</p>")
            + "</div></details>"
        )
    first = str(sibs[0].get('path') or sibs[0].get('file') or '')
    admin = ''
    extra = ''
    if can_manage_bank():
        admin = (
            "<details class='admindang-fold'><summary class='admindang-sum'>▸ Lọc đề vào các bài và dạng của chương</summary>"
            "<div class='admindang' data-chapter='1' data-path='" + html.escape(first, quote=True) + "' data-dang=''"
            " data-mon='" + html.escape(mon, quote=True) + "' data-lop='" + html.escape(lop, quote=True) + "' data-chuong='" + html.escape(chuong, quote=True) + "'>"
            "<div class='ai-intake' id='aiIntake' tabindex='0'><div class='ai-intake-bar'>"
            "<strong>Nhận đề cả chương</strong>"
            "<span class='ai-hint'>Nhiều file · Word · PDF · TEX</span>"
            "<label class='btn'>Ảnh<input id='aiImgFile' type='file' accept='image/png,image/jpeg,image/webp,image/gif' multiple></label>"
            "<button type='button' class='btn aiPhotoBtn'>📷 Chụp ảnh → prompt</button>"
            "<label class='btn'>Word / PDF / TEX<input id='aiSrcFile' type='file' multiple accept='.doc,.docx,.pdf,.tex,.ltx,.txt,text/plain,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document'></label>"
            "<button type='button' class='btn green' id='aiImport'>AI phân tích → tách bài / dạng</button>"
            "</div><div id='aiStatus' class='ai-status' hidden></div><div class='ai-shots' id='aiShots'></div>"
            "<textarea id='aiPaste' rows='3' placeholder='Thả đề của cả chương. AI lọc từng câu vào đúng bài và đúng dạng ở dưới.'></textarea>"
            "<input id='aiSrcUrl' type='url' placeholder='Link http tuỳ chọn'>"
            "</div><div id='aiGapOut'></div></div></details>"
        )
        from admin_rewrite import REWRITE_CLIENT_JS
        extra = REWRITE_CLIENT_JS
    body = (
        "<div class='wrap chapter-ui'><div class='panel'><div class='head'>📚 "
        + html.escape(mon) + " · Lớp " + html.escape(lop) + " · " + html.escape(chuong)
        + " <span class='tag'>" + str(len(sibs)) + " bài · " + str(total) + " câu</span></div><div class='body'>"
        + "<p class='chapter-tip'>Chọn một bài để xem các dạng bài tập. Bấm tên bài để mở toàn bộ câu hỏi.</p>"
        + (
            "<p><a class='btn green' href='"
            + html.escape(
                "/member/chapter/matrix?mon=" + urllib.parse.quote(mon, safe="")
                + "&lop=" + urllib.parse.quote(lop, safe="")
                + "&chuong=" + urllib.parse.quote(chuong, safe=""),
                quote=True,
            )
            + "'>📝 Tạo đề theo ma trận</a></p>"
            if can_manage_bank() else ""
        )
        + admin
        + "<div class='drawbais'>" + ''.join(blocks) + "</div>"
        + "<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>"
    )
    return page('Cả chương', "<style id=\"chapter-refresh\">\n.chapter-ui{--chapter-blue:#1e5caa;width:100%!important;max-width:none!important;margin:0!important;padding:12px 18px!important}\n.chapter-ui .panel{border:0!important;background:transparent!important;box-shadow:none!important;overflow:visible!important}\n.chapter-ui .head{background:linear-gradient(110deg,#15385c,#2369b8)!important;color:white!important;border-radius:13px;padding:17px 20px!important;font-size:17px!important;font-weight:800!important}\n.chapter-ui .head .tag{background:#ffffff28!important;color:white!important;border:1px solid #ffffff50!important}\n.chapter-ui .body{padding:12px 0!important}\n.chapter-ui .drawbais{display:grid;gap:12px;margin:12px 0 20px}\n.chapter-ui .drawbaiwrap{border:1px solid #d4e0ec!important;border-radius:12px!important;background:white!important;overflow:hidden;box-shadow:0 2px 8px #122c4a08}\n.chapter-ui .drawbai{list-style:none!important;min-height:60px;display:flex!important;align-items:center;gap:10px;padding:13px 16px!important;background:#fff!important;color:#163958!important;font-size:15px!important;font-weight:750!important;cursor:pointer}\n.chapter-ui .drawbai::-webkit-details-marker{display:none}\n.chapter-ui .drawbai:before{content:\"▸\";color:#2a6fbd;font-size:14px;flex:0 0 auto}\n.chapter-ui .drawbaiwrap[open]>.drawbai:before{content:\"▾\"}\n.chapter-ui .drawbai a{color:#163958!important;text-decoration:none!important;flex:1;min-width:0;overflow-wrap:anywhere}\n.chapter-ui .drawbai .drawn{margin-left:auto;border:1px solid #c5daef;background:#edf6ff;border-radius:999px;padding:4px 10px!important;white-space:nowrap;font-size:12px;color:#215b93!important}\n.chapter-ui .drawdangs{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px!important;padding:13px!important;background:#f6f9fd!important;border-top:1px solid #e4ecf4}\n.chapter-ui .drawdang{display:flex!important;align-items:center;gap:10px;border:1px solid #dce6ef!important;background:white!important;color:#254765!important;border-radius:9px!important;padding:12px!important;font-size:13px!important;line-height:1.45!important;min-height:52px;text-decoration:none!important;transition:border-color .12s}\n.chapter-ui .drawdang:hover{border-color:#4484c5!important;background:#f0f7ff!important}\n.chapter-ui .drawdang .drawname{flex:1;min-width:0;white-space:normal!important;overflow-wrap:anywhere}\n.chapter-ui .drawdang .drawn{margin-left:auto;flex:0 0 auto;background:#eaf2fb;border-radius:999px;padding:3px 9px!important;color:#215c99!important;font-weight:750}\n.chapter-ui .admindang-fold{border-radius:12px;border:1px solid #d5e2ef;background:white;margin:12px 0;overflow:hidden}\n.chapter-ui .admindang-sum{padding:13px!important;background:#eff6ff!important;color:#175b9d!important;font-weight:800!important;cursor:pointer}\n.chapter-ui .chapter-tip{margin:10px 0!important;font-size:13px;line-height:1.5;color:#62778c}\n@media(max-width:740px){\n .chapter-ui{padding:8px!important}\n .chapter-ui .head{padding:13px!important;font-size:14px!important;line-height:1.5}\n .chapter-ui .drawbais{gap:8px}\n .chapter-ui .drawbai{padding:12px!important;min-height:56px;font-size:13px!important}\n .chapter-ui .drawdangs{grid-template-columns:1fr;gap:7px!important;padding:9px!important}\n .chapter-ui .drawdang{min-height:46px;padding:10px!important;font-size:12px!important}\n .chapter-ui .body{padding:8px 0!important}\n}\n</style>" + body + extra)


@app.post('/api/admin/dang-fill-save')
def api_admin_dang_fill_save():
    if not can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN.'), 403
    from app import TOKEN, _safe_repo_file, dang_tex_anchor, github_put_text, load_lesson_questions, read_tex
    data = request.get_json(silent=True) or {}
    path = str(data.get('path') or '').replace('\\', '/').strip()
    dang = str(data.get('dang') or '').strip()
    raw_tex = str(data.get('latex') or '')
    if str(data.get('chapter') or '') in ('1', 'true', 'yes') or '\\baibt' in raw_tex.lower():
        return _save_chapter_fill(data, raw_tex)
    rows = _chunks_from_import(raw_tex, dang)
    if not path.startswith('ngan-hang/') or not rows:
        return jsonify(ok=False, error='Thiếu bài hoặc không có \\begin{ex}.'), 400
    try:
        qs = load_lesson_questions(path)
    except Exception:
        qs = []
    src, _line = dang_tex_anchor(path, dang, qs=qs)
    if not src.startswith('ngan-hang/') or not src.lower().endswith('.tex'):
        return jsonify(ok=False, error='File TEX không hợp lệ.'), 400
    chunk = _latex_with_nguon(_import_tex_chunk(raw_tex, dang), data.get('source_url') or '')
    try:
        sha, tex = read_tex(src, need_sha=True)
        new = (tex or '').rstrip() + '\n' + chunk
        local = _safe_repo_file(src)[1]
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(new, encoding='utf-8')
        if TOKEN:
            github_put_text(src, new, 'ADMIN AI thêm ' + str(len(rows)) + ' câu từ link/bài', sha or None)
        _STATS_CACHE.clear()
        _QID_CACHE.clear()
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    return jsonify(ok=True, n=len(rows), src=src)

def start_selected_questions():
    """Start practice from checkbox qid values. Used by /member/start-selected and /member/start."""
    m=member_current()
    if not m:return redirect(login_url('/member/practice'))
    if request.method!='POST':
        return redirect('/member')
    path=request.form.get('path','').strip()
    dang=request.form.get('dang','').strip()
    if not path or not can_practice(m,path):
        return redirect(dang_view_url(path, dang) if path else '/member')
    try:
        qs=parse_lesson_questions(path)
        if not qs:
            _,tex=read_tex(path); qs=nest_developments(parse_questions(tex))
    except Exception:
        return redirect('/member')
    if dang:
        valid={
            int(q.get('idx'))
            for q in qs
            if str(q.get('idx','')).isdigit() and _same_dang(q.get('dang'), dang)
        }
        if not valid and dang=='Chưa phân dạng':
            valid={
                int(q.get('idx'))
                for q in qs
                if str(q.get('idx','')).isdigit() and not str(q.get('dang') or '').strip()
            }
    else:
        valid={int(q.get('idx')) for q in qs if str(q.get('idx','')).isdigit()}
    ids=[]
    for raw in request.form.getlist('qid'):
        try:i=int(raw)
        except (TypeError,ValueError):
            continue
        if i in valid and i not in ids:
            ids.append(i)
    if not ids:
        url='/member/dang?path='+urllib.parse.quote(path,safe='')
        if dang:
            url+='&dang='+urllib.parse.quote(dang,safe='')
        return redirect(url)
    if request.form.get('practice_mode')=='number_mix' and len(ids)<2:
        return redirect(dang_view_url(path, dang))
    ids = sort_ids_by_kind(qs, ids, shuffle_within=False)
    kinds={str((next((q for q in qs if q.get('idx')==i),{}) or {}).get('kind') or '') for i in ids}
    kinds={k for k in kinds if k}
    session.update(
        practice_path=path,
        practice_dang=dang,
        practice_kind=(next(iter(kinds)) if len(kinds)==1 else ''),
        practice_ids=ids,
        practice_pos=0,
        practice_right=0,
        practice_streak=0,
        practice_best=0,
        practice_done=[],
        practice_ai=True,
    )
    if request.form.get('practice_mode')=='number_mix':
        session['number_mix_path']=path
        session['number_mix_ids']=ids[:120]
        session.modified=True
        return redirect('/member/number-mix')
    return redirect('/member/practice')


@app.get('/member/number-mix')
def member_number_mix():
    """Chương trình luyện nhiều câu từ danh sách đã chọn, không sửa ngân hàng."""
    m=member_current()
    path=str(session.get('number_mix_path') or '')
    ids=[int(i) for i in (session.get('number_mix_ids') or []) if str(i).isdigit()]
    if not m or not path or not ids or not can_practice(m,path):
        return redirect(login_url('/member') if not m else '/member')
    try:
        qs=parse_lesson_questions(path)
        if not qs:
            _,tex=read_tex(path)
            qs=nest_developments(parse_questions(tex))
        from app import question_payload
        by={int(q.get('idx')):q for q in qs if str(q.get('idx','')).isdigit()}
        items=[question_payload(by[i]) for i in ids if i in by]
    except Exception as exc:
        return page('Luyện đổi số', "<p>Không đọc được câu đã chọn: "+html.escape(str(exc))+"</p>")
    if not items:
        return page('Luyện đổi số', '<p>Không còn câu hợp lệ.</p>')
    packed=base64.b64encode(json.dumps(items,ensure_ascii=False).encode('utf-8')).decode('ascii')
    back=dang_view_url(path,session.get('practice_dang') or '')
    inner=r"""
<div class="nm-wrap">
  <header class="nm-head"><h2>🎲 Chương trình luyện đổi số nhiều câu</h2>
  <p>Chọn câu từ danh sách, tự làm và kiểm tra. Có thể đổi số từng câu bằng AI; câu gốc không thay đổi.</p>
  <div class="nm-toolbar"><b id="nmCount"></b><button type="button" id="nmFullscreen">⛶ Toàn màn hình</button><button id="nmReset" type="button">↻ Làm lại bộ này</button>
  <a href="BACK_URL">← Quay lại ngân hàng</a></div></header>
  <details class="nm-prompt" open><summary>📝 Prompt / yêu cầu đổi số cho AI</summary><textarea id="nmPrompt" rows="3" placeholder="Ví dụ: Giữ nguyên dạng câu, đổi tất cả dữ kiện, không làm tròn đáp án, tính lại phương án và lời giải."></textarea><small>Yêu cầu này được gửi cho AI khi bấm Đổi số câu này.</small></details><nav id="nmNav" class="nm-nav"></nav>
  <main class="nm-body"><section class="nm-question">
    <h3 id="nmTitle"></h3><div id="nmStem"></div><div id="nmOpts"></div>
    <div id="nmControls"><button type="button" id="nmCheck">✅ Kiểm tra</button>
    <button type="button" id="nmChange">🎲 Đổi số câu này</button>
    <button type="button" id="nmSolution">📖 Xem lời giải</button></div>
    <div id="nmStatus" aria-live="polite"></div><div id="nmSol" hidden></div>
    <div class="nm-toolbar"><button type="button" id="nmPrev">← Câu trước</button>
    <button type="button" id="nmNext">Câu tiếp →</button></div>
  </section></main></div>
<div id="nmData" data-json="PACKED" hidden></div>
<style>
.nm-wrap{max-width:none;width:100%;box-sizing:border-box;margin:0 auto;padding:12px;font-family:Arial,sans-serif;min-height:85vh}
.nm-head,.nm-question{background:#fff;border:1px solid #cbd5e1;border-radius:12px;padding:16px}
.nm-head{background:#eff6ff}.nm-head h2{font-size:20px;margin:0 0 6px;color:#123b70}
.nm-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin:10px 0}
.nm-prompt{border:1px solid #93c5fd;border-radius:9px;padding:12px;margin:12px 0;background:#f8fbff}.nm-prompt summary{cursor:pointer;font-weight:700}.nm-prompt textarea{width:100%;box-sizing:border-box;margin:8px 0;padding:10px;font:14px/1.5 Arial,sans-serif}.nm-prompt small{display:block;color:#475569}.nm-wrap:fullscreen{overflow:auto;background:#f1f5f9;padding:18px}.nm-wrap:fullscreen .nm-question{min-height:50vh}.nm-nav{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}
.nm-nav button{padding:7px 10px;min-width:44px;border:1px solid #93c5fd;border-radius:7px;background:white;cursor:pointer}
.nm-nav button.on{background:#1d4ed8;color:white}.nm-nav button.done{border-color:#16a34a}
.nm-question{font-size:16px;line-height:1.5}.nm-question h3{color:#1d4ed8}
.nm-question label{display:block;margin:8px 0;padding:9px;border:1px solid #e2e8f0;border-radius:7px;cursor:pointer}
.nm-question input[type=text]{width:100%;max-width:350px;padding:10px;border:1px solid #93c5fd;border-radius:7px;font-size:17px}
.nm-question button,.nm-toolbar button{cursor:pointer;padding:9px 13px;margin:4px;border-radius:7px;border:1px solid #93c5fd;background:#eff6ff}
#nmControls{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
#nmStatus{margin:9px 0;font-weight:bold}#nmSol{border:1px solid #cbd5e1;background:#f8fafc;padding:12px;border-radius:8px}
.nm-progress{height:9px;background:#dbeafe;border-radius:9px;overflow:hidden}
.nm-progress i{display:block;height:100%;width:30%;background:#2563eb;animation:nm-slide 1.2s linear infinite}
@keyframes nm-slide{0%{transform:translateX(-100%)}100%{transform:translateX(340%)}}
@media print{.nm-nav,.nm-toolbar,#nmControls{display:none}}
</style>
<script>
(function(){
const data=document.getElementById('nmData');
let questions;
try{questions=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(data.dataset.json),c=>c.charCodeAt(0))))}
catch(e){document.getElementById('nmCount').textContent='Không đọc được bộ câu hỏi';return}
let index=0;
const states=questions.map(()=>({checked:false,correct:false,show:false}));
const fs=document.getElementById('nmFullscreen');fs.onclick=async()=>{const box=document.querySelector('.nm-wrap');try{if(document.fullscreenElement)await document.exitFullscreen();else if(box.requestFullscreen)await box.requestFullscreen();else{box.classList.toggle('nm-wide');fs.textContent='⛶ Vừa màn hình';}}catch(e){box.classList.toggle('nm-wide')}};document.addEventListener('fullscreenchange',()=>{fs.textContent=document.fullscreenElement?'⤢ Thoát toàn màn hình':'⛶ Toàn màn hình'});
const el=id=>document.getElementById(id);
function typeset(){if(window.MathJax&&MathJax.typesetPromise)window.MathJax.typesetPromise().catch(()=>{});}
function norm(v){return String(v||'').trim().replace(/\s/g,'').replace(/,/g,'.').replace(/^\+/,'').toLowerCase()}
function render(){
 const q=questions[index],st=states[index];
 el('nmCount').textContent=questions.length+' câu đã chọn · '+states.filter(x=>x.checked).length+' câu đã kiểm tra';
 el('nmNav').innerHTML='';
 questions.forEach((p,i)=>{const b=document.createElement('button');b.type='button';b.textContent=i+1;b.className=(i===index?'on ':'')+(states[i].checked?'done':'');
   b.onclick=()=>{index=i;render()};el('nmNav').appendChild(b)});
 el('nmTitle').textContent='Câu '+(index+1)+' / '+questions.length+' · '+(q.kind==='TLN'?'Trả lời ngắn':q.kind==='DS'?'Đúng/Sai':q.kind==='TN'?'Trắc nghiệm':'Tự luận');
 el('nmStem').innerHTML=q.text||'';
 let h='';
 if(q.kind==='TN')h=(q.options||[]).map((o,i)=>'<label><input type="radio" name="nmAns" value="'+i+'"> '+'ABCD'[i]+'. '+o.text+'</label>').join('');
 else if(q.kind==='DS')h=(q.statements||[]).map((o,i)=>'<label>'+('abcd'[i]||i)+') '+o.text+' <select data-tf="'+i+'"><option value="">Chọn</option><option value="1">Đúng</option><option value="0">Sai</option></select></label>').join('');
 else h='<label>Đáp án của em <input id="nmAnswer" type="text" autocomplete="off" placeholder="Nhập đáp án"></label>';
 el('nmOpts').innerHTML=h;el('nmStatus').textContent=st.checked?(st.correct?'✅ Đã làm đúng':'❌ Chưa đúng'):'';
 el('nmSol').innerHTML=q.solution||'Chưa có lời giải';el('nmSol').hidden=!st.show;
 el('nmPrev').disabled=index===0;el('nmNext').disabled=index===questions.length-1;
 typeset()
}
el('nmCheck').onclick=()=>{
 const q=questions[index],st=states[index];let ok=false;
 if(q.kind==='TN'){const input=document.querySelector('input[name=nmAns]:checked');if(!input)return alert('Chọn đáp án');
  ok=!!((q.options||[])[+input.value]||{}).correct}
 else if(q.kind==='DS'){const selects=[...document.querySelectorAll('[data-tf]')];if(selects.some(x=>!x.value))return alert('Chọn đủ Đúng/Sai');
  ok=selects.every((x,i)=>(x.value==='1')===!!((q.statements||[])[i]||{}).correct)}
 else {const input=el('nmAnswer');if(!input.value.trim())return alert('Nhập đáp án');ok=q.kind==='TLN'&&norm(input.value)===norm(q.answer)}
 st.checked=true;st.correct=ok;el('nmStatus').textContent=ok?'✅ Chính xác':'❌ Chưa đúng, hãy kiểm tra cách giải';render()
};
el('nmSolution').onclick=()=>{states[index].show=!states[index].show;render()};
el('nmNext').onclick=()=>{index++;render()};
el('nmPrev').onclick=()=>{index--;render()};
el('nmReset').onclick=()=>{if(!confirm('Làm lại bộ câu hỏi này?'))return;states.forEach(x=>{x.checked=false;x.correct=false;x.show=false});index=0;render()};
el('nmChange').onclick=async()=>{
 const q=questions[index],btn=el('nmChange');
 if(!q.src||q.file_idx==null){alert('Câu này chưa hỗ trợ đổi số');return}
 const keys=window.ldvlFilledKeys?window.ldvlFilledKeys():[];
 if(!keys.length){alert('Hãy nạp Gemini API key trước khi đổi số');return}
 btn.disabled=true;const start=performance.now();
 const fmt=()=>{const n=Math.floor((performance.now()-start)/1000);return String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0')};
 el('nmStatus').innerHTML='⏳ AI đang đổi số: <b id="nmClock">00:00</b><div class="nm-progress"><i></i></div>';
 const timer=setInterval(()=>{if(el('nmClock'))el('nmClock').textContent=fmt()},250);
 try{
  let response=await fetch('/api/practice/reshuffle',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({src:q.src,file_idx:q.file_idx,api_keys:keys,requirements:el('nmPrompt').value.trim()})});
  let result=await response.json();
  if(result.ok&&result.job){
   for(let tries=0;tries<90;tries++){
    await new Promise(done=>setTimeout(done,1000));
    response=await fetch('/api/practice/reshuffle?job='+encodeURIComponent(result.job),{credentials:'same-origin'});
    result=await response.json();
    if(result.state!=='run')break;
   }
  }
  if(!result.ok||!result.q)throw Error(result.error||'Chưa đổi được số liệu');
  questions[index]=result.q;states[index]={checked:false,correct:false,show:false};render();
  el('nmStatus').textContent='✅ Đã đổi số sau '+fmt()+'. Đề và đáp án đã cập nhật.';
 }catch(e){el('nmStatus').textContent='❌ '+String(e.message||e)}
 finally{clearInterval(timer);btn.disabled=false}
};
render();
})();
</script>
"""
    inner=inner.replace('PACKED',packed).replace('BACK_URL',html.escape(back,quote=True))
    return page('Luyện đổi số nhiều câu',inner)

@app.route('/member/start-selected', methods=['GET','POST'])
def member_start_selected():
    return start_selected_questions()

@app.get('/practice/jump/<int:pos>')
def practice_jump(pos):
    ids=list(session.get('practice_ids') or [])
    if session.get('role') not in {'member', 'admin'} or not ids:return redirect(login_url('/member/practice'))
    pos=max(0,min(pos,len(ids)-1));session['practice_pos']=pos
    return redirect('/member/practice')

@app.get('/practice/redo/<int:pos>')
def practice_redo(pos):
    m=member_current()
    if not m:return redirect(login_url('/member/practice'))
    ids=list(session.get('practice_ids') or [])
    if pos<0 or pos>=len(ids):return redirect('/member/practice')
    qnum=pos+1;done=list(session.get('practice_done') or [])
    removed=[d for d in done if int(d.get('question',-1))==qnum]
    kept=[d for d in done if int(d.get('question',-1))!=qnum]
    right=int(session.get('practice_right') or 0)-sum(1 for d in removed if d.get('ok'))
    session['practice_done']=kept;session['practice_right']=max(0,right)
    session['practice_pos']=pos;session['practice_streak']=0;session.modified=True
    return redirect('/member/practice')

@app.after_request
def make_catalog_rows_enhanced(response):
    if request.path!='/member' or 'text/html' not in response.headers.get('Content-Type',''): return response
    try:
        body=response.get_data(as_text=True)
        if "class='dangkinds'" in body or "class=\"dangkinds\"" in body: return response
        if "class='dangrow'" not in body or '/member/select?path=' not in body:return response
        script=r'''<script>document.addEventListener('DOMContentLoaded',function(){fetch('/member/dang-stats-all',{credentials:'same-origin'}).then(r=>r.json()).then(all=>{if(!all.ok)return;document.querySelectorAll('.card').forEach(function(card){const open=card.querySelector("a[href^='/member/select?path=']");if(!open)return;const u=new URL(open.href,location.origin),path=u.searchParams.get('path')||'',data=all.stats[path]||{};card.querySelectorAll('.dangrow').forEach(function(row,idx){const e=row.querySelector('.dangname')||row.querySelector('span');if(!e)return;const name=(row.getAttribute('data-dang')||e.textContent||'').replace(/^\s*\d+\.\s*/,'').trim(),s=data[name]||{TN:0,DS:0,TLN:0,TL:0};const a=document.createElement('a');a.className='dangrow danglink';a.setAttribute('data-dang',name);a.href='/member/dang?path='+encodeURIComponent(path)+'&dang='+encodeURIComponent(name);a.innerHTML='<span class="dangname"><span class="dangno">'+(idx+1)+'.</span> '+name.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</span><span class="kind">TN <b>'+s.TN+'</b></span><span class="kind">ĐS <b>'+s.DS+'</b></span><span class="kind">TLN <b>'+s.TLN+'</b></span><span class="kind">TL <b>'+s.TL+'</b></span><span class="kind ktotal">'+(s.TN+s.DS+s.TLN+s.TL)+'</span><span>›</span>';row.replaceWith(a)})})}).catch(()=>{})});</script><style>.dangrow{display:grid!important;grid-template-columns:minmax(0,1fr) 52px 52px 52px 52px 50px 15px;align-items:center;gap:5px}.danglink,.dangname,.dangno{color:#1a6bb8;font-weight:400;text-decoration:none!important}.kind{border:1px solid #d3dfeb;border-radius:999px;padding:3px 2px;text-align:center;font-size:10px;background:#fff}.ktotal{font-weight:900}</style>'''
        response.set_data(body.replace('</body>',script+'</body>'))
    except Exception: pass
    return response
