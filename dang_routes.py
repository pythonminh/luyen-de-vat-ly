# -*- coding: utf-8 -*-
"""Member question browser: show every question before building a test."""
from __future__ import annotations
import html
import time
import urllib.parse
from flask import request, jsonify, redirect, session
from app import admin_current, app, can_access, can_manage_bank, can_view, dup_index_by_question, find_duplicate_groups, github_blob_url, html_question, index_data, login_url, member_current, nguon_html, page, parse_lesson_questions, parse_questions, read_tex, sort_ids_by_kind, sort_questions_by_kind

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
        bits=[]
        for i,o in enumerate(st):
            txt=html_question(o.get('text','') if isinstance(o,dict) else o)
            yes=bool((o or {}).get('correct')) if isinstance(o,dict) else False
            cls=' ok' if show_solution and yes else (' noans' if show_solution else '')
            flag=f"<div class='tf-flags'><span class='okmark'>{'Đúng' if yes else 'Sai'}</span></div>" if show_solution else ''
            bits.append(f"<div class='tf{cls}'><div class='tf-text'><b>{i+1}.</b> {txt}</div>{flag}</div>")
        options='<div class="tfgrid">'+''.join(bits)+'</div>'
    elif kind=='TLN':
        options="<div class='answerline'>✎ Học viên nhập đáp án khi làm bài</div>"
        if show_solution:
            ans=str(q.get('answer') or '').strip()
            options+=f"<div class='answerline'><b>Đáp án:</b> {html_question(ans) if ans else '—'}</div>"
    else:
        options="<div class='answerline'>✎ Câu tự luận</div>" if member_current() else "<div class='answerline'>✎ Câu tự luận · 🔒 Đăng nhập rồi làm bài mới xem lời giải</div>"
    if show_solution:
        sol_html=_sol_block(q)
    gh=''
    if can_manage_bank() and path and line:
        gh=f" <a class='btn mini' href='{_esc(github_blob_url(path))}#L{line}' target='_blank' rel='noopener'>GitHub dòng {line}</a>"
    dup=dup or {}
    hid=str(highlight_id or '').strip().lower()
    src=str(q.get('src') or path or '').replace('\\','/')
    try: fi=int(q.get('file_idx') if q.get('file_idx') is not None else n)
    except (TypeError, ValueError): fi=int(n or 0)
    drop_key=_esc(src+'||'+str(fi))
    rw=''
    if can_manage_bank():
        rw=(f"<div class='rwbar'><button type='button' class='btn mini rwgo' data-drop='{drop_key}'>✍️ AI viết lại đề + lời giải</button>"
            f"<button type='button' class='btn mini rwedit' data-drop='{drop_key}'>✏️ Sửa đề / lời giải</button>"
            "<span class='muted'>Sửa trực tiếp trên ô LaTeX, không cần GitHub.</span><div class='rwout'></div></div>")
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
            f"<span class='metafile'>TEX Câu {html.escape(str(cau))} · STT file {n+1}</span>{gh}{nguon_html(q)}<span class='level'>{html.escape(level)}</span></div>"
            f"<div class='qtext'>{html_question(text)}</div>{options}{rw}{sol_html}</article>")

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
    kind_btns=''.join(f"<button type='button' class='btn' onclick=\"onlyKind('{k}')\">{lab}</button>"
                      for k,lab in (('TN','Chỉ TN'),('DS','Chỉ ĐS'),('TLN','Chỉ TLN'),('TL','Chỉ TL')) if kc.get(k))
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
    slim_html=''
    if can_manage_bank():
        from admin_slim import slim_bar_html
        slim_html=slim_bar_html(path, dang, next_url)
    guest = not m
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
    else:
        guest_note=("<div class='notice'>🔐 ADMIN · xem đáp án và lời giải ngay trên từng thẻ, không cần làm bài.</div>" if admin_view else '')
        tools=(kindbar+
          "<div class='toolbar'><button type='button' class='btn' onclick='setAll(true)'>☑ Chọn tất cả</button><button type='button' class='btn' onclick='setAll(false)'>☐ Bỏ chọn</button>"
          "<button type='button' class='btn' onclick='onlyKind(\"\")'>Tất cả loại</button>"+kind_btns+
          "<button type='button' class='btn' onclick='onlyDup(false)'>Tất cả</button><button type='button' class='btn' onclick='onlyDup(true)'>Chỉ trùng</button>"
          + (f"<a class='btn' href='/admin/dups?path={_esc(path)}'>🔎 Xem nhóm trùng (cả file)</a>" if can_manage_bank() and (dao_n or cung_n) else "")
          + find_box
          + "<span id='sum' class='notice mini'>Đã chọn: 0 câu</span></div>")
        bottom=("<div class='toolbar bottom modebar'>"
                "<button class='btn primary' type='submit' name='ai_review' value='0'>▶ Làm bài (không phản biện)</button>"
                "<button class='btn' type='submit' name='ai_review' value='1'>🤖 Làm bài + phản biện AI</button>"
                "<a class='btn' href='/member'>← Mục lục</a></div>")
        form_open=("<form method='post' action='/member/start-selected' id='questionForm'>"
                   f"<input type='hidden' name='path' value='{_esc(path)}'><input type='hidden' name='dang' value='{_esc(dang)}'>")
        form_close="</form>"
    find_js=(
        "<script>let DUPONLY=false,KINDFILTER='';"
        "function vis(c){const box=document.getElementById('findq');const q=(box&&box.value||'').trim().toLowerCase();const dup=c.getAttribute('data-dup')==='1';const miss=!!q&&!(c.getAttribute('data-find')||'').includes(q);const missK=!!KINDFILTER&&c.getAttribute('data-kind')!==KINDFILTER;c.classList.toggle('hideq',miss||missK||(DUPONLY&&!dup))}"
        "function filterQ(){document.querySelectorAll('.qcard').forEach(vis);if(typeof upd==='function'&&document.getElementById('sum'))upd()}"
        "function bootFind(){const box=document.getElementById('findq');if(!box)return;box.addEventListener('input',filterQ);const p=new URLSearchParams(location.search);const id=(p.get('id')||p.get('qid')||'').trim();if(id){if(!box.value)box.value=id;filterQ();const t=id.toLowerCase();const el=document.querySelector('.qcard.qhit')||Array.prototype.find.call(document.querySelectorAll('.qcard:not(.hideq)'),function(c){return (c.getAttribute('data-qid')||'')===t})||document.querySelector('.qcard:not(.hideq)');if(el){el.classList.add('qhit');el.scrollIntoView({block:'center'})}}else{filterQ()}}"
    )
    if not guest:
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
    find_js += "bootFind();if(window.ldvlTypeset)ldvlTypeset(document.body);</script>"
    rw_js = ""
    if can_manage_bank():
        from admin_rewrite import REWRITE_CLIENT_JS
        rw_js = REWRITE_CLIENT_JS
    body=("<div class='wrap'><div class='panel'><div class='head'>📌 "+_esc(title)+" <span class='tag'>"+_esc(dang)+"</span> <span class='tag'>"+str(total)+" câu</span>"+kind_tags+"</div><div class='body'>"
          f"{guest_note}{notice_extra}{dup_note}{flash_html}{slim_html}{dup_form}"
          +form_open+tools+
          f"<div class='questions'>{cards}</div>"
          +bottom+form_close+
          "</div></div></div>"
          "<style>.guestview .qcheck{display:none}.toolbar{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:10px 0}.kindbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0;padding:10px;border:1px solid #d9e5f0;border-radius:9px;background:#f8fbff}.kindbar label{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px}.kindbar input{width:58px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}.mini{padding:7px 10px}.questions{display:grid;gap:10px}.qcard{border:1px solid #cfddeb;border-radius:11px;background:#fff;padding:12px}.qhead{display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #e7eef5;padding-bottom:8px}.qcheck{font-weight:900;color:#145bb0;cursor:pointer}.qcheck input{width:17px;height:17px;vertical-align:middle;margin-right:5px}.badge,.level,.qid,.metafile,.dupbadge{border:1px solid #cbd9e7;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;background:#f8fbff}.qid{background:#fff7dc;border-color:#efca73;color:#7a5300;font-family:Consolas,monospace}.dupbadge{background:#ffe4e6;border-color:#fb7185;color:#9f1239}.dupcard{border-color:#fb7185;background:#fff7f7}.qhit{border:2px solid #176bd3;box-shadow:0 0 0 3px #176bd322}.slimhit{border-color:#c2410c;background:#fff7ed}.metafile{color:#4a6278}.level{margin-left:auto}.dupbar{margin:10px 0;padding:12px;border:2px solid #e11d48;border-radius:10px;background:#fff1f2;display:flex;flex-wrap:wrap;gap:10px;align-items:center}.dupx{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:#9f1239;color:#fff;font-weight:800;font-size:12px;cursor:pointer}.dupx input{width:16px;height:16px}.dupok{font-weight:800}.slimbar{margin:10px 0;padding:12px;border:1px solid #fdba74;border-radius:10px;background:#fff7ed;display:flex;flex-wrap:wrap;gap:10px;align-items:center}.slimbar input[type=number]{width:64px;padding:6px;border:1px solid #fdba74;border-radius:6px;text-align:center}.slimform{margin:8px 0 12px}.slimgrp{border:1px solid #fed7aa;border-radius:9px;padding:8px;margin:8px 0;background:#fff}.slimh{font-weight:800;margin-bottom:6px}.slimrow{padding:6px 0;border-top:1px dashed #fed7aa;font-size:14px;line-height:1.45}.slimrow.keep{background:#f0fdf4}.rwbar{margin:10px 0 0;padding:8px 10px;border:1px dashed #7dd3fc;border-radius:9px;background:#f0f9ff;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.rwout{width:100%}.rwprev{margin-top:8px;padding:10px;border:1px solid #bae6fd;border-radius:9px;background:#fff}.rwprev label{display:flex;gap:8px;align-items:center;font-weight:800;margin:8px 0 4px}.qtext{font-size:16px;line-height:1.7;padding:10px 2px}.opts{display:grid;gap:7px}.opt,.tf{border:1px solid #d7e3ee;border-radius:8px;padding:9px;background:#fbfdff;display:flex;align-items:center;gap:10px}.tf-text{flex:1;min-width:0}.tf-flags{margin-left:auto;flex-shrink:0}.opt.ok,.tf.ok{background:#e8f8ee;border-color:#42ae6b}.tf.noans{background:#fff8f0}.okmark{display:inline-block;min-width:4.6em;text-align:center;margin-left:0;padding:3px 10px;border-radius:999px;background:#15803d;color:#fff;font-size:11px;font-weight:800}.answerline{border:1px dashed #b8cde2;border-radius:8px;padding:9px;color:#687d92;margin-top:6px}.solution{margin-top:11px;padding:12px;border:1px solid #bad5f2;border-radius:9px;background:#f7fbff}.qcard:has(input:checked){border:2px solid #176bd3;background:#fafdff}.qcard.hideq{display:none}.bottom{border-top:1px solid #e5edf5;padding-top:12px}@media(max-width:700px){.qtext{font-size:14px}}</style>"
          + find_js + rw_js
          )
    return page('Chọn câu' if not guest else 'Xem đề',body)

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
    session.update(
        practice_path=path,
        practice_ids=ids,
        practice_pos=0,
        practice_right=0,
        practice_streak=0,
        practice_best=0,
        practice_done=[],
        practice_ai=request.form.get('ai_review') in ('1','on','true','yes'),
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
