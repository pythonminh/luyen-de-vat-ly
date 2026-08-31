# -*- coding: utf-8 -*-
"""Routes for opening one exercise type at a time and catalog summaries."""
from __future__ import annotations

import html
import time
import urllib.parse

from flask import request, jsonify, redirect
from app import app, can_access, member_current, page, parse_questions, read_tex

_STATS_CACHE = {}
_STATS_TTL = 300

def _esc_attr(s: str) -> str:
    return html.escape(str(s), quote=True)

def _stats_for(path: str):
    now = time.time(); hit = _STATS_CACHE.get(path)
    if hit and now-hit[0] < _STATS_TTL:return hit[1]
    _, tex = read_tex(path); qs = parse_questions(tex); stats={}
    for q in qs:
        dang=q.get('dang') or 'Chưa phân dạng'; kind=q.get('kind') or 'TL'
        stats.setdefault(dang, {'TN':0,'DS':0,'TLN':0,'TL':0}); stats[dang][kind]=stats[dang].get(kind,0)+1
    _STATS_CACHE[path]=(now,stats); return stats

@app.get('/member/dang-stats')
def member_dang_stats():
    m=member_current()
    if not m:return jsonify(ok=False,error='Chưa đăng nhập'),401
    path=request.args.get('path','')
    if not path or not can_access(m,path):return jsonify(ok=False,error='Không có quyền truy cập'),403
    try:return jsonify(ok=True,stats=_stats_for(path))
    except Exception as exc:return jsonify(ok=False,error=str(exc)),500

@app.get('/member/dang')
def member_dang():
    m=member_current()
    if not m:return redirect('/member/login')
    path=request.args.get('path',''); dang=request.args.get('dang','').strip()
    if not path or not dang:return redirect('/member')
    if not can_access(m,path):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try:_,tex=read_tex(path);qs=parse_questions(tex)
    except Exception as exc:return page('Lỗi',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>"+html.escape(str(exc))+"</div></div></div></div>")
    selected=[q for q in qs if q.get('dang')==dang]
    if not selected:return page('Dạng bài',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>Không tìm thấy dạng bài này trong TEX.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    dang_names=[];seen=set()
    for q in qs:
        name=q.get('dang') or 'Chưa phân dạng'
        if name not in seen:seen.add(name);dang_names.append(name)
    di=dang_names.index(dang)
    # Hàng 1: thông báo 4 loại. Hàng 2: ô chọn N/H/V/C.
    rows=[]
    for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
        counts={lev:sum(1 for q in selected if q.get('kind')==kind and q.get('level')==lev) for lev in 'NHVC'}
        total=sum(counts.values())
        rows.append(f"<div class='typebox'><span class='typecode'>{kind}</span><span class='typename'>{label}</span><span class='typecount'>{total} câu</span></div>")
    pickboxes=[]
    for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
        counts={lev:sum(1 for q in selected if q.get('kind')==kind and q.get('level')==lev) for lev in 'NHVC'}
        inputs=''.join(f"<label class='lev'><span>{z}</span><input class='n' type='number' min='0' max='{counts[z]}' value='0' name='pick:{di}:{kind}:{z}' title='Tối đa {counts[z]} câu'></label>" for z in 'NHVC')
        pickboxes.append(f"<div class='pickbox'><div class='picktitle'>{kind} · {label}</div><div class='pickinputs'>{inputs}</div></div>")
    title=str(path.rsplit('/',1)[-2] if '/' in path else path)
    body=("<div class='wrap'><div class='panel'><div class='head'>📌 Dạng bài đang chọn</div><div class='body'>"
          f"<div class='notice'><b>{html.escape(title)}</b> · {html.escape(dang)} · <b>{len(selected)} câu</b></div>"
          "<form method='post' action='/member/start'>"
          f"<input type='hidden' name='path' value='{_esc_attr(path)}'>"
          "<div class='types2'>"+''.join(rows)+"</div>"
          "<div class='pickgrid'>"+''.join(pickboxes)+"</div>"
          "<div id='sum' class='notice' style='margin-top:10px'>TỔNG CHỌN: 0 câu</div>"
          "<button class='btn primary' type='submit'>▶ Làm dạng này</button> <a class='btn' href='/member'>← Mục lục</a>"
          "</form></div></div></div>"
          "<script>function upd(){let t=0;document.querySelectorAll('.n').forEach(x=>{let m=Number(x.max)||0,v=Math.max(0,Math.min(m,Number(x.value)||0));x.value=v;t+=v});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu'}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',upd));upd()</script>")
    # CSS 2 hàng: hàng thông tin 4 loại, hàng chọn N/H/V/C 4 ô thẳng cột.
    body=body.replace('</div></div></div><script>',"""<style>
.types2{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:8px;margin:12px 0 8px}.typebox{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:7px;padding:9px 10px;border:1px solid #d7e3ee;border-radius:8px;background:#fbfdff;min-height:40px}.typecode{font-weight:900;font-size:11px;border:1px solid #c8d9e9;border-radius:999px;padding:3px 7px;background:#fff;color:#145bb0}.typename{font-weight:700}.typecount{white-space:nowrap;font-weight:900}.pickgrid{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:8px}.pickbox{border:1px solid #d7e3ee;border-radius:8px;background:#fff;padding:8px}.picktitle{font-weight:900;margin-bottom:6px}.pickinputs{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.lev{display:grid;gap:3px;text-align:center;font-weight:900;font-size:11px;color:#587087}.lev .n{width:100%;padding:7px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}.danglink{color:inherit;text-decoration:none!important;cursor:pointer}.danglink:hover{background:#eef7ff}.danglink:after{content:' ›';color:#176bd3;font-weight:900}@media(max-width:900px){.types2,.pickgrid{grid-template-columns:repeat(2,minmax(150px,1fr))}}@media(max-width:560px){.types2,.pickgrid{grid-template-columns:1fr}}
</style></div></div></div><script>""")
    return page('Chọn dạng bài',body)

@app.after_request
def make_catalog_rows_enhanced(response):
    content_type=response.headers.get('Content-Type','')
    if request.path!='/member' or 'text/html' not in content_type:return response
    try:
        body=response.get_data(as_text=True)
        if "class='dangrow'" not in body or '/member/select?path=' not in body:return response
        script=r'''<script>document.addEventListener('DOMContentLoaded',function(){document.querySelectorAll('.card').forEach(function(card){const open=card.querySelector("a[href^='/member/select?path=']");if(!open)return;const u=new URL(open.href,location.origin);const path=u.searchParams.get('path')||'';fetch('/member/dang-stats?path='+encodeURIComponent(path),{credentials:'same-origin'}).then(r=>r.json()).then(data=>{if(!data.ok)return;card.querySelectorAll('.dangrow').forEach(function(row){const nameEl=row.querySelector('span');if(!nameEl)return;const name=nameEl.textContent.trim();const s=data.stats[name]||{TN:0,DS:0,TLN:0,TL:0};const a=document.createElement('a');a.className='dangrow danglink';a.href='/member/dang?path='+encodeURIComponent(path)+'&dang='+encodeURIComponent(name);a.innerHTML='<span class="dangname">'+name.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</span><span class="kind ktn">TN <b>'+s.TN+'</b></span><span class="kind kds">ĐS <b>'+s.DS+'</b></span><span class="kind ktln">TLN <b>'+s.TLN+'</b></span><span class="kind ktl">TL <b>'+s.TL+'</b></span><span class="kind ktotal">'+(s.TN+s.DS+s.TLN+s.TL)+'</span><span class="arrow">›</span>';row.replaceWith(a)})}).catch(()=>{})})})</script><style>.dang{padding:5px!important}.dangrow{display:grid!important;grid-template-columns:minmax(0,1fr) 52px 52px 52px 52px 54px 16px;align-items:center;column-gap:5px;min-height:34px;border-bottom:1px solid #edf2f7!important}.dangname{min-width:0;line-height:1.35}.kind{display:inline-flex;align-items:center;justify-content:center;border:1px solid #d3dfeb;border-radius:999px;padding:3px 2px;font-size:10px;white-space:nowrap;background:#fff}.ktn{color:#145bb0}.kds{color:#8a4d00}.ktln{color:#176f45}.ktl{color:#7a3fa0}.ktotal{justify-self:center;font-weight:900;font-size:11px}@media(max-width:700px){.dangrow{grid-template-columns:minmax(0,1fr) 43px 43px 43px 43px 42px 12px;column-gap:3px}.kind{font-size:9px}}</style>''';response.set_data(body.replace('</body>',script+'</body>'))
    except Exception:pass
    return response
