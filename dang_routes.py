# -*- coding: utf-8 -*-
"""Member question browser: show every question before building a test."""
from __future__ import annotations
import html
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from flask import request, jsonify, redirect, session
from app import TOKEN, _safe_repo_file, admin_current, app, can_access, can_manage_bank, can_view, dup_index_by_question, find_duplicate_groups, github_blob_url, github_put_text, html_question, index_data, lesson_switch_html, login_url, member_current, nguon_html, page, parse_lesson_questions, parse_questions, read_tex, sort_ids_by_kind, sort_questions_by_kind, tex_without_questions

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
        if logged:
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
    inner=html_question(sol) if sol else "<div class='muted'>Chưa có lời giải trong file TEX.</div>"
    return f"<div class='solution'><b>📖 Lời giải</b><div>{inner}</div></div>"

def _question_card(q, seq, total, path='', dup=None, show_solution=False, highlight_id=''):
    n=q.get('idx',0); kind=q.get('kind','TL'); level=q.get('level','H'); text=q.get('text','')
    qid=str(q.get('id') or '').strip() or '—'
    cau=q.get('cau') or (n+1); line=int(q.get('line') or 0)
    badge={'TN':'TN · Trắc nghiệm','DS':'ĐS · Đúng / Sai','TLN':'TLN · Trả lời ngắn','TL':'TL · Tự luận'}.get(kind,kind)
    options=''
    sol_html=''
    if kind=='TN':
        letters='ABCD'
        bits=[]
        for i,o in enumerate((q.get('options') or [])[:4]):
            ok=show_solution and bool(o.get('correct'))
            mark=" <span class='okmark'>Đáp án đúng</span>" if ok else ''
            bits.append(f"<div class='opt{' ok' if ok else ''}'><b>{letters[i]}.</b> {html_question(o.get('text',''))}{mark}</div>")
        options='<div class="opts">'+''.join(bits)+'</div>'
    elif kind=='DS':
        st=q.get('statements') or []
        bits=['<div class="tf-colhead"><span></span><span></span><span class="tf-h yes">Đúng</span><span class="tf-h no">Sai</span></div>']
        labs='ABCD'
        for i,o in enumerate(st):
            txt=html_question(o.get('text','') if isinstance(o,dict) else o)
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
            options+=f"<div class='answerline'><b>Đáp án:</b> {html_question(ans) if ans else '—'}</div>"
    else:
        options="<div class='answerline'>✎ Câu tự luận</div>" if member_current() else "<div class='answerline'>✎ Câu tự luận · 🔒 Đăng nhập rồi làm bài mới xem lời giải</div>"
    if show_solution:
        sol_html=_sol_block(q)
    src=str(q.get('src') or path or '').replace('\\','/')
    gh=''
    tex_badge=f"<span class='metafile'>TEX Câu {html.escape(str(cau))} · STT file {n+1}</span>"
    if can_manage_bank() and src:
        edit_href='/admin/edit?path='+urllib.parse.quote(src,safe='')
        if line:
            edit_href+='&line='+str(line)
        tex_badge=f"<a class='btn mini metafile' href='{_esc(edit_href)}'>✏️ TEX Câu {html.escape(str(cau))} · STT file {n+1}</a>"
        if line:
            gh=f" <a class='btn mini' href='{_esc(github_blob_url(src))}#L{line}' target='_blank' rel='noopener'>GitHub dòng {line}</a>"
    dup=dup or {}
    hid=str(highlight_id or '').strip().lower()
    try: fi=int(q.get('file_idx') if q.get('file_idx') is not None else n)
    except (TypeError, ValueError): fi=int(n or 0)
    drop_key=_esc(src+'||'+str(fi))
    rw=''
    if can_manage_bank():
        rw=(f"<div class='rwbar'><button type='button' class='btn mini rwgo' data-drop='{drop_key}'>✍️ AI viết lại đề + lời giải</button>"
            f"<button type='button' class='btn mini rwedit' data-drop='{drop_key}'>✏️ Sửa đề / lời giải</button>"
            f"<button form='qdel' class='btn mini red' type='submit' name='drop' value='{drop_key}' onclick=\"return confirm('Xóa vĩnh viễn câu này khỏi file TEX? Không hoàn tác trên trang này.')\">🗑 Xóa câu</button>"
            "<span class='muted'>Sửa / xóa trực tiếp trên file TEX, không cần GitHub.</span><div class='rwout'></div></div>")
    dcls=' dupcard' if dup.get('label') else ''
    if hid and qid.lower()==hid:
        dcls+=' qhit'
    dtag=f"<span class='dupbadge'>{html.escape(dup.get('label') or '')} · nhóm {','.join(str(x) for x in dup.get('n') or [])}</span>" if dup.get('label') else ''
    xoa=''
    if can_manage_bank() and dup.get('extra'):
        xoa=f" <label class='dupx'><input form='dupdel' type='checkbox' name='drop' value='{drop_key}' checked> Xóa bản trùng này</label>"
    find=_esc(f"{qid} {cau} {text} {q.get('nguon') or ''} {dup.get('label') or ''}".lower())
    return (f"<article class='qcard{dcls}' data-drop='{drop_key}' data-find='{find}' data-qid='{_esc(qid.lower())}' data-dup='{1 if dup.get('label') else 0}' data-kind='{kind}'><div class='qhead'><label class='qcheck'><input type='checkbox' name='qid' value='{n}'><span>Câu {seq}/{total}</span></label>"
            f"<span class='qid'>ID: {html.escape(qid)}</span>{dtag}{xoa}<span class='badge'>{html.escape(badge)}</span>"
            f"{tex_badge}{gh}{nguon_html(q)}<span class='level'>{html.escape(level)}</span></div>"
            f"<div class='qheadline'><span class='qbadge'>Câu {seq}</span><div class='qstem'>{html_question(text)}</div></div>{options}{rw}{sol_html}</article>")

@app.get('/member/dang')
def member_dang():
    m=member_current()
    path=request.args.get('path','').strip(); dang=request.args.get('dang','').strip()
    if not path or not dang:return redirect('/member')
    if not can_view(m,path):
        if not m:
            return redirect(login_url('/member/dang?path='+urllib.parse.quote(path,safe='')+'&dang='+urllib.parse.quote(dang,safe='')))
        return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try:
        qs = parse_lesson_questions(path)
        if not qs:
            _, tex = read_tex(path); qs = parse_questions(tex)
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
    selected=sort_questions_by_kind(selected)
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
    tabs=lesson_switch_html(path, qs, dang=dang, kind='', guest=guest)
    groups=find_duplicate_groups(selected)
    dmap=dup_index_by_question(groups)
    dao_n=sum(len(g['extras']) for g in groups if g['type']=='dao')
    cung_n=sum(1 for g in groups if g['type']=='cungde')
    admin_view=can_manage_bank()
    highlight_id=(request.args.get('id') or request.args.get('qid') or '').strip()
    cards=''.join(_question_card(q,i+1,total,q.get('src') or path,dmap.get(q.get('idx')),show_solution=admin_view,highlight_id=highlight_id) for i,q in enumerate(selected))
    dup_note=''
    if dao_n or cung_n:
        dup_note=(f"<div class='notice' style='border-color:#efca73;background:#fff8df'>⚠️ Có <b>{dao_n}</b> câu trùng (kể cả đảo đáp án) và <b>{cung_n}</b> nhóm cùng đề khác đáp án. "
                  "Bấm <b>Chỉ trùng</b> để lọc.</div>")
    next_url='/member/dang?path='+urllib.parse.quote(path,safe='')+'&dang='+urllib.parse.quote(dang,safe='')
    srcs={str(q.get('src') or path).replace('\\','/') for q in selected}
    dup_form=''
    if can_manage_bank() and dao_n:
        nfile=len(srcs)
        note_file=f" Trùng có thể nằm ở {nfile} file TEX trong bài — xóa đúng file chứa bản thừa." if nfile>1 else ""
        dup_form=(
            f"<form id='dupdel' method='post' action='/admin/dups' class='dupbar' onsubmit=\"return confirm('Xóa các bản trùng đã tick trên thẻ đỏ? Bản đầu mỗi nhóm được giữ lại.')\">"
            f"<input type='hidden' name='path' value='{_esc(path)}'><input type='hidden' name='next' value='{_esc(next_url)}'>"
            f"<b>Xóa trùng:</b> thẻ đỏ (bản thừa) có ô <b>Xóa bản trùng này</b> — mặc định đã tick. Còn <b>{dao_n}</b> bản thừa.{note_file} "
            "Nhóm «cùng đề khác đáp án» không xóa hàng loạt. "
            "<label class='dupok'><input type='checkbox' name='confirm' value='yes' required> Tôi xác nhận xóa các bản đã tick</label> "
            "<button class='btn red' type='submit'>🗑 Xóa các bản trùng đã chọn</button></form>"
        )
    elif can_manage_bank() and cung_n:
        dup_form="<div class='notice'>Nhóm «cùng đề khác đáp án» chỉ để xem lại, không xóa hàng loạt.</div>"
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
    if guest:
        guest_note=("<div class='notice'>👁 Bạn đang xem đề — chưa đăng nhập nên không làm bài và không gọi Gemini. "
                    f"<a class='btn primary' href='{_esc(login_url(login_next))}'>Đăng nhập để làm bài</a></div>")
        tools=f"<div class='toolbar'>{find_box}</div>"
        bottom=f"<div class='toolbar bottom'><a class='btn' href='/member'>← Mục lục</a></div>"
        form_open=f"<div class='guestview'>"
        form_close="</div>"
    elif admin_view:
        guest_note="<div class='notice'>🔐 ADMIN · xem đáp án và lời giải ngay trên từng thẻ, không cần làm bài.</div>"
        tools=(kindbar+
          "<div class='toolbar'><button type='button' class='btn' onclick='setAll(true)'>☑ Chọn tất cả</button><button type='button' class='btn' onclick='setAll(false)'>☐ Bỏ chọn</button>"
          "<button type='button' class='btn' onclick='onlyDup(false)'>Tất cả</button><button type='button' class='btn' onclick='onlyDup(true)'>Chỉ trùng</button>"
          + (f"<a class='btn' href='/admin/dups?path={_esc(path)}'>🔎 Xem nhóm trùng (cả file)</a>" if can_manage_bank() and (dao_n or cung_n) else "")
          + f"<a class='btn' href='{_esc('/admin/edit?path='+urllib.parse.quote(path,safe=''))}'>✏️ Sửa file TEX</a>"
          + find_box
          + "<span id='sum' class='notice mini'>Đã chọn: 0 câu</span></div>")
        bottom=("<div class='toolbar bottom modebar'>"
                "<button class='btn primary' type='submit' name='ai_review' value='0'>▶ Làm bài (không phản biện)</button>"
                "<button class='btn' type='submit' name='ai_review' value='1'>🤖 Làm bài + phản biện AI</button>"
                "<a class='btn' href='/member'>← Mục lục</a></div>")
        form_open=("<form method='post' action='/member/start-selected' id='questionForm'>"
                   f"<input type='hidden' name='path' value='{_esc(path)}'><input type='hidden' name='dang' value='{_esc(dang)}'>")
        form_close="</form>"
    else:
        guest_note=''
        tools=f"<div class='toolbar'>{find_box}</div>"
        bottom=f"<div class='toolbar bottom'><a class='btn' href='/member'>← Mục lục</a></div>"
        form_open="<div class='guestview'>"
        form_close="</div>"
    find_js=(
        "<script>let DUPONLY=false,KINDFILTER='';"
        "function vis(c){const box=document.getElementById('findq');const q=(box&&box.value||'').trim().toLowerCase();const dup=c.getAttribute('data-dup')==='1';const miss=!!q&&!(c.getAttribute('data-find')||'').includes(q);const missK=!!KINDFILTER&&c.getAttribute('data-kind')!==KINDFILTER;c.classList.toggle('hideq',miss||missK||(DUPONLY&&!dup))}"
        "function filterQ(){document.querySelectorAll('.qcard').forEach(vis);if(typeof upd==='function'&&document.getElementById('sum'))upd()}"
        "function bootFind(){const box=document.getElementById('findq');if(!box)return;box.addEventListener('input',filterQ);const p=new URLSearchParams(location.search);const id=(p.get('id')||p.get('qid')||'').trim();if(id){if(!box.value)box.value=id;filterQ();const t=id.toLowerCase();const el=document.querySelector('.qcard.qhit')||Array.prototype.find.call(document.querySelectorAll('.qcard:not(.hideq)'),function(c){return (c.getAttribute('data-qid')||'')===t})||document.querySelector('.qcard:not(.hideq)');if(el){el.classList.add('qhit');el.scrollIntoView({block:'center'})}}else{filterQ()}}"
    )
    if admin_view:
        find_js += (
            "function onlyDup(v){DUPONLY=!!v;filterQ()}function onlyKind(k){KINDFILTER=k||'';filterQ()}"
            "function kindCount(k){return Array.prototype.filter.call(document.querySelectorAll('.qcard:not(.hideq)'),function(c){return c.getAttribute('data-kind')===k}).reduce(function(n,c){const i=c.querySelector('input[name=qid]');return n+(i&&i.checked?1:0)},0)}"
            "function upd(){const sum=document.getElementById('sum');if(!sum)return;const a=Array.prototype.slice.call(document.querySelectorAll('.qcard:not(.hideq) input[name=qid]'));const n=a.filter(function(x){return x.checked}).length;const bits=['TN','DS','TLN','TL'].map(function(k){const c=kindCount(k);const inp=document.querySelector('.kn[data-k=\"'+k+'\"]');if(inp&&document.activeElement!==inp)inp.value=c;return c?((k==='DS'?'ĐS':k)+' '+c):''}).filter(Boolean);sum.textContent='Đã chọn: '+n+' câu'+(bits.length?' · '+bits.join(' · '):'')}"
            "function setAll(v){document.querySelectorAll('.qcard:not(.hideq) input[name=qid]').forEach(function(x){x.checked=v});upd()}"
            "function applyKinds(){setAll(false);document.querySelectorAll('.kn').forEach(function(inp){const k=inp.getAttribute('data-k');let want=Math.max(0,Math.min(Number(inp.max)||0,Number(inp.value)||0));inp.value=want;const cards=Array.prototype.filter.call(document.querySelectorAll('.qcard:not(.hideq)'),function(c){return c.getAttribute('data-kind')===k});cards.slice(0,want).forEach(function(c){const i=c.querySelector('input[name=qid]');if(i)i.checked=true})});upd()}"
            "document.querySelectorAll('input[name=qid]').forEach(function(x){x.addEventListener('change',upd)});"
            "document.querySelectorAll('.kn').forEach(function(x){x.addEventListener('change',applyKinds)});"
            "const form=document.getElementById('questionForm');if(form)form.addEventListener('submit',function(e){if(!document.querySelector('.qcard:not(.hideq) input[name=qid]:checked')){e.preventDefault();alert('Hãy chọn ít nhất một câu.')}});"
        )
    find_js += (
        "document.querySelectorAll('.qcard').forEach(function(card){"
        "const stem=card.querySelector('.qstem');const fig=card.querySelector('.qfig');const body=card.querySelector('.qbody.ds');"
        "if(!stem||!fig||!body)return;const bits=[];"
        "stem.querySelectorAll('.immini,.tikz-row,.tikzfig,.tikz-live,.ytbox,table.tex-table').forEach(function(el){"
        "if(el.closest('.immini,.tikz-row')&&!el.matches('.immini,.tikz-row'))return;bits.push(el);});"
        "if(!bits.length){fig.remove();return;}bits.forEach(function(el){fig.appendChild(el)});fig.hidden=false;body.classList.add('hassplit');});"
        "bootFind();if(window.ldvlTypeset)ldvlTypeset(document.body);</script>"
    )
    rw_js = ""
    if can_manage_bank():
        from admin_rewrite import REWRITE_CLIENT_JS
        rw_js = REWRITE_CLIENT_JS
    body=("<div class='wrap'>"+tabs+"<div class='panel'><div class='head'>📌 "+_esc(title)+" <span class='tag'>"+_esc(dang)+"</span> <span class='tag'>"+str(total)+" câu</span>"+kind_tags+"</div><div class='body'>"
          f"{guest_note}{notice_extra}{dup_note}{flash_html}{slim_html}{dup_form}{qdel_form}"
          +form_open+tools+
          f"<div class='questions'>{cards}</div>"
          +bottom+form_close+
          "</div></div></div>"
          "<style>.guestview .qcheck{display:none}.toolbar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:10px 0}.kindbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0;padding:10px;border:1px solid #d9e5f0;border-radius:9px;background:#f8fbff}.kindbar label{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px}.kindbar input{width:58px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}.mini{padding:7px 10px}.questions{display:grid;gap:10px}.qcard{border:1px solid #cfddeb;border-radius:11px;background:#fff;padding:12px}.qhead{display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #e7eef5;padding-bottom:8px}.qcheck{font-weight:900;color:#145bb0;cursor:pointer}.qcheck input{width:17px;height:17px;vertical-align:middle;margin-right:5px}.badge,.level,.qid,.metafile,.dupbadge{border:1px solid #cbd9e7;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;background:#f8fbff}.qid{background:#fff7dc;border-color:#efca73;color:#7a5300;font-family:Consolas,monospace}.dupbadge{background:#ffe4e6;border-color:#fb7185;color:#9f1239}.dupcard{border-color:#fb7185;background:#fff7f7}.qhit{border:2px solid #176bd3;box-shadow:0 0 0 3px #176bd322}.slimhit{border-color:#c2410c;background:#fff7ed}.metafile{color:#4a6278}.level{margin-left:auto}.dupbar{margin:10px 0;padding:12px;border:2px solid #e11d48;border-radius:10px;background:#fff1f2;display:flex;flex-wrap:wrap;gap:10px;align-items:center}.dupx{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:#9f1239;color:#fff;font-weight:800;font-size:12px;cursor:pointer}.dupx input{width:16px;height:16px}.dupok{font-weight:800}.slimbar{margin:10px 0;padding:12px;border:1px solid #fdba74;border-radius:10px;background:#fff7ed;display:flex;flex-wrap:wrap;gap:10px;align-items:center}.slimbar input[type=number]{width:64px;padding:6px;border:1px solid #fdba74;border-radius:6px;text-align:center}.slimform{margin:8px 0 12px}.slimgrp{border:1px solid #fed7aa;border-radius:9px;padding:8px;margin:8px 0;background:#fff}.slimh{font-weight:800;margin-bottom:6px}.slimrow{padding:6px 0;border-top:1px dashed #fed7aa;font-size:14px;line-height:1.45}.slimrow.keep{background:#f0fdf4}.rwbar{margin:10px 0 0;padding:8px 10px;border:1px dashed #7dd3fc;border-radius:9px;background:#f0f9ff;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.rwout{width:100%}.rwprev{margin-top:8px;padding:10px;border:1px solid #bae6fd;border-radius:9px;background:#fff}.rwprev label{display:flex;gap:8px;align-items:center;font-weight:800;margin:8px 0 4px}.qtext{font-size:16px;line-height:1.7;padding:10px 2px;font-family:'Times New Roman',Times,serif;font-weight:400}.opts{display:grid;gap:7px}.opt{border:1px solid #d7e3ee;border-radius:8px;padding:9px;background:#fbfdff;display:flex;align-items:center;gap:10px}.opt.ok{background:#e8f8ee;border-color:#42ae6b}.okmark{display:inline-block;min-width:4.6em;text-align:center;margin-left:0;padding:3px 10px;border-radius:999px;background:#15803d;color:#fff;font-size:11px;font-weight:800}.answerline{border:1px dashed #b8cde2;border-radius:8px;padding:9px;color:#687d92;margin-top:6px}.solution{margin-top:11px;padding:12px;border:1px solid #bad5f2;border-radius:9px;background:#f7fbff}.qcard:has(input:checked){border:2px solid #176bd3;background:#fafdff}.qcard.hideq{display:none}.bottom{border-top:1px solid #e5edf5;padding-top:12px}@media(max-width:700px){.qtext{font-size:14px}}</style>"
          + find_js + rw_js
          )
    return page('Chọn câu' if not guest else 'Xem đề',body)

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
                    + html.escape(dk, quote=True) + "' checked> Gợi ý xóa "
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

def _filter_import_rows(rows, qs, fallback_dang=''):
    """Bỏ câu gần trùng / vượt trần; ưu tiên đủ mức cố gắng rồi mới nhận câu khác biệt."""
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

def _fetch_public_page(url):
    try:
        url = _assert_public_http_url(url)
    except ValueError as e:
        return '', str(e)
    req = urllib.request.Request(url, headers={
        'User-Agent': 'luyen-de-vat-ly-admin/1.0 (question import)',
        'Accept': 'text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1',
    })
    opener = urllib.request.build_opener(_SafeRedirect)
    try:
        with opener.open(req, timeout=18) as r:
            ctype = str(r.headers.get('Content-Type') or '').lower()
            if ctype and 'html' not in ctype and 'text' not in ctype and 'xml' not in ctype:
                return '', 'Trang này không phải HTML/văn bản.'
            raw = r.read(900000)
    except urllib.error.HTTPError as e:
        return '', 'Không tải được trang (HTTP %s).' % e.code
    except Exception as e:
        return '', 'Không tải được trang: ' + str(e)[:160]
    if len(raw) >= 900000:
        raw = raw[:899000]
    charset = 'utf-8'
    cm = re.search(r'charset=([A-Za-z0-9._-]+)', ctype)
    if cm:
        charset = cm.group(1)
    try:
        text = raw.decode(charset, errors='replace')
    except Exception:
        text = raw.decode('utf-8', errors='replace')
    plain = _html_to_text(text)
    if len(plain) < 40:
        return '', 'Trang gần như không có chữ (có thể chặn bot / cần đăng nhập).'
    return plain[:36000], ''

@app.post('/api/admin/dang-fill')
def api_admin_dang_fill():
    if not can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN.'), 403
    from app import KIND_CHIP_LABS, KIND_ORDER, dang_kind_counts_of, dang_tex_anchor, kind_gap_heuristic, load_lesson_questions, questions_in_scope
    from student_gemini import _gemini_generate, _keys_from_payload
    data = request.get_json(silent=True) or {}
    path = str(data.get('path') or '').replace('\\', '/').strip()
    dang = str(data.get('dang') or '').strip()
    if not path.startswith('ngan-hang/'):
        return jsonify(ok=False, error='Thiếu path bài.'), 400
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error='Nạp key Gemini rồi bấm lại.'), 400
    source_url = str(data.get('source_url') or data.get('url') or '').strip()
    page_text = ''
    if source_url:
        page_text, ferr = _fetch_public_page(source_url)
        if ferr:
            return jsonify(ok=False, error=ferr), 400
    if not dang and not page_text:
        return jsonify(ok=False, error='Đang ở Cả bài: dán link rồi bấm Lấy từ link (không cần chọn dạng). Muốn AI viết câu mới thì hãy mở một dạng.'), 400
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
    nguon_line = '\\nguon{' + _tex_nguon_url(source_url) + '}' if source_url else ''
    kind_rules = (
        "Quy ước loại câu:\n"
        "- TN: \\choice rồi 4 dòng {A}{B}{C}{D}, đúng thì {\\True ...}\n"
        "- ĐS: \\choiceTF rồi 4 mệnh đề, đúng thì {\\True ...}\n"
        "- TLN: \\shortans{đáp án} rồi \\loigiai{...}\n"
        "- TL: không \\choice, có \\loigiai{...}\n"
        "Mỗi câu có \\loigiai{...} (trang không có lời giải thì viết ngắn đúng đáp án). Công thức $...$. Không % ID.\n"
        + ("Trong MỖI khối \\begin{ex} phải có đúng một " + nguon_line + " (link tải trang, không đổi).\n" if nguon_line else "")
    )
    if page_text and not dang:
        prompt = (
            "Bạn là giáo viên ra đề thi THPT. Chuyển đề từ TRANG WEB sang LaTeX ngân hàng.\n"
            "Gán vào dạng đã có; mỗi dạng cố gắng 9 TN / 2 ĐS / 3 TLN / 4 TL, trần 18 / 4 / 6 / 8.\n"
            "Không lấy hai câu cùng ý. Đủ mục tiêu thì chỉ lấy câu thật khác; chạm trần thì bỏ.\n"
            "Không bịa đề không có trên trang.\n"
            "Với MỖI câu, trước \\begin{ex} phải có đúng một dòng \\dangbt{Tên dạng}.\n"
            "Ưu tiên gán vào các dạng ĐÃ CÓ của bài: " + dang_list + "\n"
            "Chỉ tạo tên dạng mới khi câu không khớp dạng nào ở trên. Không markdown, không lời dẫn.\n"
            "Không bịa đề không có trên trang.\n"
            + kind_rules
            + "Nội dung trang:\n" + page_text
        )
    elif page_text:
        prompt = (
            "Bạn là giáo viên ra đề thi THPT. Chuyển đề từ TRANG WEB sang LaTeX ngân hàng câu hỏi.\n"
            "Chỉ trả về các khối \\begin{ex}...\\end{ex}, không markdown, không lời dẫn.\n"
            "Dạng đang nạp: " + dang + "\n"
            "Lấy các câu trên trang CÙNG CHỦ ĐỀ dạng này. Ý khác nhau — bỏ biến thể cùng một bài toán.\n"
            "Không vượt trần mỗi dạng: 18 TN, 4 ĐS, 6 TLN, 8 TL. Ưu tiên đủ 9 TN, 2 ĐS, 3 TLN, 4 TL rồi dừng nếu chỉ còn câu giống.\n"
            "Không bịa đề không có trên trang. Không \\dangbt.\n"
            + kind_rules
            + "Nội dung trang (đã gỡ HTML):\n" + page_text
        )
    else:
        prompt = (
            "Bạn là giáo viên ra đề thi THPT. Viết câu hỏi LaTeX MỚI cho đúng dạng bài, không copy đề mẫu.\n"
            "Chỉ trả về các khối \\begin{ex}...\\end{ex}, không markdown, không lời dẫn.\n"
            "Dạng: " + dang + "\nCần viết: " + want + "\n"
            "Mỗi câu một ý khác nhau, không viết biến thể cùng số liệu. Cấm trùng / gần trùng mẫu dưới.\n"
            "Quy ước:\n"
            "- TN: \\choice rồi 4 dòng {A}{B}{C}{D}, đúng thì {\\True ...}\n"
            "- ĐS: \\choiceTF rồi 4 mệnh đề, đúng thì {\\True ...}\n"
            "- TLN: \\shortans{đáp án} rồi \\loigiai{...}\n"
            "- TL: không \\choice, có \\loigiai{...}\n"
            "Mỗi câu phải có \\loigiai{...}. Công thức trong $...$. Không \\dangbt, không % ID.\n"
            "Mẫu đề đang có (chỉ để cùng phong cách, cấm trùng):\n"
            + ("\n".join(f"- {k}: {t}" for k, t in samples) or "(chưa có)")
        )
    tok = 16000 if page_text else 8000
    raw, err = '', ''
    for key in keys:
        try:
            raw = _gemini_generate(key, prompt, tok, 0.25)
            err = ''
            break
        except Exception as e:
            err = str(e)
            raw = ''
    if not raw:
        return jsonify(ok=False, error='AI không viết được: ' + (err or 'trống')), 400
    raw = re.sub(r'^```(?:latex|tex)?\s*|\s*```$', '', raw.strip(), flags=re.I)
    blocks = _extract_ex_blocks(raw)
    if page_text and len(blocks) < 4 and keys:
        more_prompt = (
            prompt
            + "\n\nLần trước chỉ ra được " + str(len(blocks)) + " câu. Trang còn nhiều câu. "
            "Viết TIẾP các khối \\begin{ex} CHƯA có, không lặp đề cũ. Vẫn đủ \\nguon và \\loigiai.\n"
            "Đã có (cấm trùng):\n" + raw[-4000:]
        )
        extra = ''
        for key in keys:
            try:
                extra = _gemini_generate(key, more_prompt, tok, 0.2)
                break
            except Exception:
                extra = ''
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
    kept, skipped = _filter_import_rows(rows, qs, dang)
    if kept:
        latex = '\n\n'.join('\\dangbt{' + d + '}\n' + b for d, b in kept) + '\n'
    elif page_text:
        return jsonify(ok=False, error='Mọi câu từ link đều gần trùng hoặc đã chạm trần dạng. Soát gợi ý xóa rồi thử lại.'), 400
    else:
        return jsonify(ok=False, error='Câu AI viết gần trùng đề đang có. Soát xóa bản thừa, đừng nhồi thêm biến thể.'), 400
    latex = _latex_with_nguon(latex, source_url)
    nd = len(_chunks_from_import(latex, dang))
    skip_txt = (' Bỏ ' + str(len(skipped)) + ' câu (gần trùng / vượt trần).') if skipped else ''
    summary = 'AI soạn ' + str(nd or len(blocks)) + ' câu' + (' từ link (tự gán dạng)' if (source_url and not dang) else (' từ link' if source_url else ' (' + want + ')')) + skip_txt + '. Mỗi câu có \\nguon{link}. Sửa ô LaTeX nếu cần, rồi bấm Chấp nhận ghi TEX.'
    return jsonify(ok=True, src=src, latex=latex, n=nd or len(blocks), add=add, counts=counts, summary=summary)

@app.post('/api/admin/dang-fill-save')
def api_admin_dang_fill_save():
    if not can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN.'), 403
    from app import TOKEN, _safe_repo_file, dang_tex_anchor, github_put_text, load_lesson_questions, read_tex
    data = request.get_json(silent=True) or {}
    path = str(data.get('path') or '').replace('\\', '/').strip()
    dang = str(data.get('dang') or '').strip()
    raw_tex = str(data.get('latex') or '')
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
    if not path or not can_access(m,path):
        return redirect('/member')
    try:
        qs=parse_lesson_questions(path)
        if not qs:
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
    return redirect('/member/practice')

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
