# -*- coding: utf-8 -*-
"""Member question browser: show every question before building a test."""
from __future__ import annotations
import html
import time
import urllib.parse
from flask import request, jsonify, redirect, session
from app import admin_current, app, can_access, can_manage_bank, dup_index_by_question, find_duplicate_groups, github_blob_url, html_question, index_data, member_current, nguon_html, page, parse_questions, read_tex, sort_ids_by_kind

_STATS_CACHE = {}
_STATS_TTL = 300

def _esc(s):
    return html.escape(str(s), quote=True)

def _same_dang(a, b):
    return str(a or '').strip() == str(b or '').strip()

def _stats_for(path):
    now = time.time(); hit = _STATS_CACHE.get(path)
    if hit and now-hit[0] < _STATS_TTL: return hit[1]
    _, tex = read_tex(path); qs = parse_questions(tex); stats = {}
    for q in qs:
        d=(q.get('dang') or 'Chưa phân dạng').strip() or 'Chưa phân dạng'; k=q.get('kind') or 'TL'
        stats.setdefault(d, {'TN':0,'DS':0,'TLN':0,'TL':0})
        stats[d][k]=stats[d].get(k,0)+1
    _STATS_CACHE[path]=(now,stats); return stats

@app.get('/member/dang-stats')
def member_dang_stats():
    m=member_current()
    if not m:return jsonify(ok=False,error='Chưa đăng nhập'),401
    path=request.args.get('path','').strip()
    if not path or not can_access(m,path):return jsonify(ok=False,error='Không có quyền truy cập'),403
    try:return jsonify(ok=True,stats=_stats_for(path))
    except Exception as exc:return jsonify(ok=False,error=str(exc)),500

@app.get('/member/dang-stats-all')
def member_dang_stats_all():
    m=member_current()
    if not m:return jsonify(ok=False,error='Chưa đăng nhập'),401
    out={}
    for x in (index_data().get('lessons') or []):
        if not isinstance(x, dict):
            continue
        path=str(x.get('path') or x.get('file') or '').strip()
        if not path.startswith('ngan-hang/') or not can_access(m, path):
            continue
        try:
            out[path]=_stats_for(path)
        except Exception:
            continue
    return jsonify(ok=True, stats=out)


def _question_card(q, seq, total, path='', dup=None):
    n=q.get('idx',0); kind=q.get('kind','TL'); level=q.get('level','H'); text=q.get('text','')
    qid=str(q.get('id') or '').strip() or '—'
    cau=q.get('cau') or (n+1); line=int(q.get('line') or 0)
    badge={'TN':'TN · Trắc nghiệm','DS':'ĐS · Đúng / Sai','TLN':'TLN · Trả lời ngắn','TL':'TL · Tự luận'}.get(kind,kind)
    options=''
    if kind=='TN':
        letters='ABCD'
        options='<div class="opts">'+''.join(f"<div class='opt'><b>{letters[i]}.</b> {html_question(o.get('text',''))}</div>" for i,o in enumerate((q.get('options') or [])[:4]))+'</div>'
    elif kind=='DS':
        st=q.get('statements') or []
        options='<div class="tfgrid">'+''.join(f"<div class='tf'><b>{i+1}.</b> {html_question(o.get('text','') if isinstance(o,dict) else o)}</div>" for i,o in enumerate(st))+'</div>'
    elif kind=='TLN':
        options="<div class='answerline'>✎ Học viên nhập đáp án khi làm bài</div>"
    else:
        options="<div class='answerline'>✎ Câu tự luận</div>"
    gh=''
    if can_manage_bank() and path and line:
        gh=f" <a class='btn mini' href='{_esc(github_blob_url(path))}#L{line}' target='_blank' rel='noopener'>GitHub dòng {line}</a>"
    dup=dup or {}
    dcls=' dupcard' if dup.get('label') else ''
    dtag=f"<span class='dupbadge'>{html.escape(dup.get('label') or '')} · nhóm {','.join(str(x) for x in dup.get('n') or [])}</span>" if dup.get('label') else ''
    xoa=''
    if can_manage_bank() and dup.get('extra'):
        xoa=f" <label class='dupx'><input form='dupdel' type='checkbox' name='drop' value='{n}' checked> Xóa bản trùng này</label>"
    find=_esc(f"{qid} {cau} {text} {q.get('nguon') or ''} {dup.get('label') or ''}".lower())
    return (f"<article class='qcard{dcls}' data-find='{find}' data-dup='{1 if dup.get('label') else 0}'><div class='qhead'><label class='qcheck'><input type='checkbox' name='qid' value='{n}'><span>Câu {seq}/{total}</span></label>"
            f"<span class='qid'>ID: {html.escape(qid)}</span>{dtag}{xoa}<span class='badge'>{html.escape(badge)}</span>"
            f"<span class='metafile'>TEX Câu {html.escape(str(cau))} · STT file {n+1}</span>{gh}{nguon_html(q)}<span class='level'>{html.escape(level)}</span></div>"
            f"<div class='qtext'>{html_question(text)}</div>{options}</article>")

@app.get('/member/dang')
def member_dang():
    m=member_current()
    if not m:return redirect('/member/login')
    path=request.args.get('path','').strip(); dang=request.args.get('dang','').strip()
    if not path or not dang:return redirect('/member')
    if not can_access(m,path):
        return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try: _,tex=read_tex(path); qs=parse_questions(tex)
    except Exception as exc:
        return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div></div></div></div>")
    selected=[q for q in qs if _same_dang(q.get('dang'), dang)]
    if not selected and dang == 'Chưa phân dạng':
        selected=[q for q in qs if not str(q.get('dang') or '').strip() or _same_dang(q.get('dang'), dang)]
    notice_extra=''
    if not selected and qs:
        selected=list(qs)
        notice_extra=f"<div class='notice'>Không khớp đúng tên dạng «{_esc(dang)}» — đang hiện {len(selected)} câu trong file.</div>"
    if not selected:
        return page('Dạng bài',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>File TEX này chưa có câu hỏi \\begin{ex}...\\end{ex}.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    title=str(path.rsplit('/',1)[-2] if '/' in path else path)
    total=len(selected)
    groups=find_duplicate_groups(selected)
    dmap=dup_index_by_question(groups)
    dao_n=sum(len(g['extras']) for g in groups if g['type']=='dao')
    cung_n=sum(1 for g in groups if g['type']=='cungde')
    cards=''.join(_question_card(q,i+1,total,path,dmap.get(q.get('idx'))) for i,q in enumerate(selected))
    dup_note=''
    if dao_n or cung_n:
        dup_note=(f"<div class='notice' style='border-color:#efca73;background:#fff8df'>⚠️ Có <b>{dao_n}</b> câu trùng (kể cả đảo đáp án) và <b>{cung_n}</b> nhóm cùng đề khác đáp án. "
                  "Bấm <b>Chỉ trùng</b> để lọc.</div>")
    next_url='/member/dang?path='+urllib.parse.quote(path,safe='')+'&dang='+urllib.parse.quote(dang,safe='')
    dup_form=''
    if can_manage_bank() and dao_n:
        dup_form=(
            f"<form id='dupdel' method='post' action='/admin/dups' class='dupbar' onsubmit=\"return confirm('Xóa các bản trùng đã tick trên thẻ đỏ? Bản đầu mỗi nhóm được giữ lại.')\">"
            f"<input type='hidden' name='path' value='{_esc(path)}'><input type='hidden' name='next' value='{_esc(next_url)}'>"
            f"<b>Xóa trùng:</b> thẻ đỏ (bản thừa) có ô <b>Xóa bản trùng này</b> — mặc định đã tick. Còn <b>{dao_n}</b> bản thừa. "
            "Nhóm «cùng đề khác đáp án» không xóa hàng loạt. "
            "<label class='dupok'><input type='checkbox' name='confirm' value='yes' required> Tôi xác nhận xóa các bản đã tick</label> "
            "<button class='btn red' type='submit'>🗑 Xóa các bản trùng đã chọn</button></form>"
        )
    elif can_manage_bank() and cung_n:
        dup_form="<div class='notice'>Nhóm «cùng đề khác đáp án» chỉ để xem lại, không xóa hàng loạt.</div>"
    flash=request.args.get('ok') or ''; ferr=request.args.get('err') or ''
    flash_html=(f"<div class='success'>{html.escape(flash)}</div>" if flash else "")+(f"<div class='err'>{html.escape(ferr)}</div>" if ferr else "")
    body=("<div class='wrap'><div class='panel'><div class='head'>📌 "+_esc(title)+" <span class='tag'>"+_esc(dang)+"</span> <span class='tag'>"+str(total)+" câu</span></div><div class='body'>"
          f"{notice_extra}{dup_note}{flash_html}{dup_form}"
          "<form method='post' action='/member/start-selected' id='questionForm'>"
          f"<input type='hidden' name='path' value='{_esc(path)}'><input type='hidden' name='dang' value='{_esc(dang)}'>"
          "<div class='toolbar'><button type='button' class='btn' onclick='setAll(true)'>☑ Chọn tất cả</button><button type='button' class='btn' onclick='setAll(false)'>☐ Bỏ chọn</button>"
          "<button type='button' class='btn' onclick='onlyDup(false)'>Tất cả</button><button type='button' class='btn' onclick='onlyDup(true)'>Chỉ trùng</button>"
          + (f"<a class='btn' href='/admin/dups?path={_esc(path)}'>🔎 Xem nhóm trùng (cả file)</a>" if can_manage_bank() and (dao_n or cung_n) else "")
          + "<input id='findq' type='search' placeholder='Tìm ID hoặc nguồn, ví dụ SGK' style='flex:1;min-width:180px;padding:8px;border:1px solid #cbd8e6;border-radius:7px'>"
          "<span id='sum' class='notice mini'>Đã chọn: 0 câu</span></div>"
          f"<div class='questions'>{cards}</div>"
          "<div class='toolbar bottom'><button class='btn primary' type='submit'>▶ Làm các câu đã chọn</button><a class='btn' href='/member'>← Mục lục</a></div>"
          "</form></div></div></div>"
          "<style>.toolbar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:10px 0}.mini{padding:7px 10px}.questions{display:grid;gap:10px}.qcard{border:1px solid #cfddeb;border-radius:11px;background:#fff;padding:12px}.qhead{display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #e7eef5;padding-bottom:8px}.qcheck{font-weight:900;color:#145bb0;cursor:pointer}.qcheck input{width:17px;height:17px;vertical-align:middle;margin-right:5px}.badge,.level,.qid,.metafile,.dupbadge{border:1px solid #cbd9e7;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;background:#f8fbff}.qid{background:#fff7dc;border-color:#efca73;color:#7a5300;font-family:Consolas,monospace}.dupbadge{background:#ffe4e6;border-color:#fb7185;color:#9f1239}.dupcard{border-color:#fb7185;background:#fff7f7}.metafile{color:#4a6278}.level{margin-left:auto}.dupbar{margin:10px 0;padding:12px;border:2px solid #e11d48;border-radius:10px;background:#fff1f2;display:flex;flex-wrap:wrap;gap:10px;align-items:center}.dupx{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:#9f1239;color:#fff;font-weight:800;font-size:12px;cursor:pointer}.dupx input{width:16px;height:16px}.dupok{font-weight:800}.qtext{font-size:16px;line-height:1.7;padding:10px 2px}.opts{display:grid;gap:7px}.opt,.tf{border:1px solid #d7e3ee;border-radius:8px;padding:9px;background:#fbfdff}.answerline{border:1px dashed #b8cde2;border-radius:8px;padding:9px;color:#687d92}.qcard:has(input:checked){border:2px solid #176bd3;background:#fafdff}.qcard.hideq{display:none}.bottom{border-top:1px solid #e5edf5;padding-top:12px}@media(max-width:700px){.qtext{font-size:14px}}</style>"
          "<script>let DUPONLY=false;function vis(c){const q=(document.getElementById('findq').value||'').trim().toLowerCase();const dup=c.getAttribute('data-dup')==='1';const miss=!!q&&!(c.getAttribute('data-find')||'').includes(q);c.classList.toggle('hideq',miss||(DUPONLY&&!dup))}function filterQ(){document.querySelectorAll('.qcard').forEach(vis);upd()}function onlyDup(v){DUPONLY=!!v;filterQ()}function upd(){const a=[...document.querySelectorAll('.qcard:not(.hideq) input[name=qid]')];document.getElementById('sum').textContent='Đã chọn: '+a.filter(x=>x.checked).length+' câu'}function setAll(v){document.querySelectorAll('.qcard:not(.hideq) input[name=qid]').forEach(x=>x.checked=v);upd()}document.querySelectorAll('input[name=qid]').forEach(x=>x.addEventListener('change',upd));document.getElementById('findq').addEventListener('input',filterQ);document.getElementById('questionForm').addEventListener('submit',function(e){if(!document.querySelector('.qcard:not(.hideq) input[name=qid]:checked')){e.preventDefault();alert('Hãy chọn ít nhất một câu.')}});upd();if(window.ldvlTypeset)ldvlTypeset(document.body);</script>")
    return page('Chọn câu',body)

def start_selected_questions():
    """Start practice from checkbox qid values. Used by /member/start-selected and /member/start."""
    m=member_current()
    if not m:return redirect('/member/login')
    if request.method!='POST':
        return redirect('/member')
    path=request.form.get('path','').strip()
    dang=request.form.get('dang','').strip()
    if not path or not can_access(m,path):
        return redirect('/member')
    try:
        _,tex=read_tex(path); qs=parse_questions(tex)
    except Exception:
        return redirect('/member')
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
    ids = sort_ids_by_kind(qs, ids, shuffle_within=False)
    session.update(
        practice_path=path,
        practice_ids=ids,
        practice_pos=0,
        practice_right=0,
        practice_streak=0,
        practice_best=0,
        practice_done=[],
    )
    return redirect('/member/practice')

@app.route('/member/start-selected', methods=['GET','POST'])
def member_start_selected():
    return start_selected_questions()

@app.get('/practice/jump/<int:pos>')
def practice_jump(pos):
    ids=list(session.get('practice_ids') or [])
    if session.get('role')!='member' or not ids:return redirect('/member/login')
    pos=max(0,min(pos,len(ids)-1));session['practice_pos']=pos
    return redirect('/member/practice')

@app.get('/practice/redo/<int:pos>')
def practice_redo(pos):
    m=member_current()
    if not m:return redirect('/member/login')
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
        if "class='dangrow'" not in body or '/member/select?path=' not in body:return response
        script=r'''<script>document.addEventListener('DOMContentLoaded',function(){fetch('/member/dang-stats-all',{credentials:'same-origin'}).then(r=>r.json()).then(all=>{if(!all.ok)return;document.querySelectorAll('.card').forEach(function(card){const open=card.querySelector("a[href^='/member/select?path=']");if(!open)return;const u=new URL(open.href,location.origin),path=u.searchParams.get('path')||'',data=all.stats[path]||{};card.querySelectorAll('.dangrow').forEach(function(row){const e=row.querySelector('span');if(!e)return;const name=e.textContent.trim(),s=data[name]||{TN:0,DS:0,TLN:0,TL:0};const a=document.createElement('a');a.className='dangrow danglink';a.href='/member/dang?path='+encodeURIComponent(path)+'&dang='+encodeURIComponent(name);a.innerHTML='<span class="dangname">'+name.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</span><span class="kind">TN <b>'+s.TN+'</b></span><span class="kind">ĐS <b>'+s.DS+'</b></span><span class="kind">TLN <b>'+s.TLN+'</b></span><span class="kind">TL <b>'+s.TL+'</b></span><span class="kind ktotal">'+(s.TN+s.DS+s.TLN+s.TL)+'</span><span>›</span>';row.replaceWith(a)})})}).catch(()=>{})});</script><style>.dangrow{display:grid!important;grid-template-columns:minmax(0,1fr) 52px 52px 52px 52px 50px 15px;align-items:center;gap:5px}.danglink{color:inherit;text-decoration:none!important}.kind{border:1px solid #d3dfeb;border-radius:999px;padding:3px 2px;text-align:center;font-size:10px;background:#fff}.ktotal{font-weight:900}</style>'''
        response.set_data(body.replace('</body>',script+'</body>'))
    except Exception: pass
    return response
