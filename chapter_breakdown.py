"""Read-only type and difficulty breakdown for chapter's lesson and exercise-form cards."""
from __future__ import annotations

import collections
import html
import threading
import time
from flask import jsonify, request
import app as base

app = base.app
_CACHE={}
_LOCK=threading.Lock()
_TTL=120

def _breakdown(path):
    now=time.monotonic()
    with _LOCK:
        v=_CACHE.get(path)
        if v and now-v[0]<_TTL:return v[1]
    questions=base.load_lesson_questions(path)
    def blank():
        return {"types":{k:0 for k in ("TN","DS","TLN","TL")},
                "levels":{k:0 for k in ("N","H","V","C")},
                "unknown":0,"total":0}
    total=blank()
    forms={}
    for q in questions:
        k=str(q.get("kind") or "").upper().strip()
        if k not in total["types"]:continue
        name=str(q.get("dang") or "Chưa phân dạng").strip() or "Chưa phân dạng"
        item=forms.setdefault(name,blank())
        level=base.norm_muc(q.get("level"))
        for c in (total,item):
            c["total"]+=1
            c["types"][k]+=1
            if level in c["levels"]:c["levels"][level]+=1
            else:c["unknown"]+=1
    output={"total":total,"forms":forms}
    with _LOCK:
        if len(_CACHE)>250:_CACHE.clear()
        _CACHE[path]=(now,output)
    return output

@app.get("/api/member/chapter-distribution")
def chapter_distribution():
    from dang_routes import _chapter_lessons
    member=base.member_current()
    mon=str(request.args.get("mon") or "").strip()
    lop=str(request.args.get("lop") or "").strip()
    chuong=str(request.args.get("chuong") or "").strip()
    path=str(request.args.get("path") or "").strip()
    if not (mon and lop and chuong and path):
        return jsonify(ok=False,error="Thiếu thông tin bài."),400
    available={str(r.get("path") or r.get("file") or "") for r in _chapter_lessons(mon,lop,chuong)}
    if path not in available or not base.can_view(member,path):
        return jsonify(ok=False,error="Không có quyền xem bài."),403
    try:
        data=_breakdown(path)
    except Exception:
        return jsonify(ok=False,error="Chưa đọc được phân bố câu của bài."),503
    response=jsonify(ok=True,**data)
    response.headers["Cache-Control"]="no-store"
    return response

STYLE="""
<style id="chapter-breakdown-style">
.chapter-ui .chapter-breakdown{display:flex;flex-wrap:wrap;align-items:center;gap:4px 6px;margin-top:6px;font-weight:500!important;line-height:1.45}
.chapter-ui .chapter-breakdown-row{display:flex;flex-wrap:wrap;align-items:center;gap:4px;max-width:100%}
.chapter-ui .chapter-breakdown-label{font-size:11px;font-weight:750;color:#476682;margin-right:2px}
.chapter-ui .chapter-count-chip{display:inline-flex;align-items:center;gap:3px;border:1px solid #dbe7f4;background:#f1f6fc;border-radius:6px;padding:2px 6px;font-size:11px;font-weight:600;color:#385a7d;white-space:nowrap}
.chapter-ui .chapter-count-chip b{font-variant-numeric:tabular-nums;color:#173a5b;font-weight:850}
.chapter-ui .chapter-count-chip.zero{opacity:.55}
.chapter-ui .chapter-count-note{font-size:10px;color:#945e28}
.chapter-ui .drawbai .chapter-breakdown{flex:1;min-width:0}
.chapter-ui .drawbai .chapter-breakdown-label{color:#53708c}
.chapter-ui .drawdang{align-items:center!important}
.chapter-ui .drawdang .chapter-card-left{flex:1;min-width:0}
.chapter-ui .chapter-breakdown-error{font-size:11px;color:#a04c29}
@media(max-width:700px){
 .chapter-ui .chapter-count-chip{font-size:10px;padding:2px 5px}
 .chapter-ui .chapter-breakdown{gap:4px}
 .chapter-ui .drawbai{flex-wrap:wrap}
 .chapter-ui .drawbai .chapter-breakdown{flex-basis:100%;order:3;margin-left:15px}
}
</style>
"""
JS=r"""
<script id="chapter-breakdown-script">
(function(){
const chapter=document.querySelector('.chapter-ui');
if(!chapter)return;
const params=new URLSearchParams(location.search);
const mon=params.get('mon'),lop=params.get('lop'),chuong=params.get('chuong');
if(!mon||!lop||!chuong)return;
const items=[...chapter.querySelectorAll('.drawbaiwrap')].map(w=>{
 const main=w.querySelector('summary.drawbai a[href]');
 const details=[...w.querySelectorAll('a.drawdang[href]')];
 if(!main)return null;
 let path;
 try{path=new URL(main.href,location.href).searchParams.get('path');}catch(e){}
 if(!path)return null;
 const host=document.createElement('span');host.className='chapter-breakdown';host.textContent='Đang thống kê loại câu và mức độ…';
 // A dedicated host beneath the heading avoids nested anchors and preserves click behavior.
 main.insertAdjacentElement('afterend',host);
 const more=details.map(link=>{
   const name=link.querySelector('.drawname');
   if(!name)return null;
   let d='';
   try{d=new URL(link.href,location.href).searchParams.get('dang')||'';}catch(e){}
   // Wrap only content: the existing anchor remains the actual clickable card.
   const wrapper=document.createElement('span');wrapper.className='chapter-card-left';
   name.parentNode.insertBefore(wrapper,name);
   wrapper.append(name);
   const el=document.createElement('span');el.className='chapter-breakdown';el.textContent='Đang thống kê…';
   wrapper.append(el);
   return {d,el};
 }).filter(Boolean);
 return {w,path,host,more,done:false};
}).filter(Boolean);
function row(title,arr){
 const el=document.createElement('span');el.className='chapter-breakdown-row';
 const label=document.createElement('span');label.className='chapter-breakdown-label';label.textContent=title;
 el.append(label);
 for(const [name,n] of arr){
  const v=Number(n)||0;
  const chip=document.createElement('span');chip.className='chapter-count-chip'+(!v?' zero':'');
  chip.append(document.createTextNode(name+' '));
  const count=document.createElement('b');count.textContent=String(v);chip.append(count);el.append(chip);
 }
 return el;
}
function render(where,data){
 where.replaceChildren();
 if(!data){where.textContent='Chưa có câu hoặc chưa có dữ liệu phân bố';return;}
 const k=data.types||{},l=data.levels||{};
 where.append(
  row('Loại:',[['TN',k.TN],['Đ/S',k.DS],['TLN',k.TLN],['TL',k.TL]]),
  row('Mức:',[['NB',l.N],['TH',l.H],['VD',l.V],['VDC',l.C]])
 );
 if(data.unknown){
  const note=document.createElement('span');note.className='chapter-count-note';
  note.textContent='Chưa rõ mức: '+data.unknown;where.append(note);
 }
}
function matching(forms,name){
 if(Object.prototype.hasOwnProperty.call(forms,name))return forms[name];
 const norm=s=>String(s||'').normalize('NFC').replace(/\s+/g,' ').trim().toLowerCase();
 const key=norm(name);
 const match=Object.keys(forms).find(k=>norm(k)===key);
 return match?forms[match]:null;
}
async function load(item){
 if(item.done)return;
 item.done=true;
 try{
  const u=new URL('/api/member/chapter-distribution',location.origin);
  for(const [k,v] of Object.entries({mon,lop,chuong,path:item.path}))u.searchParams.set(k,v);
  const res=await fetch(u.toString(),{credentials:'same-origin'});
  if(!res.ok)throw new Error('HTTP '+res.status);
  const data=await res.json();
  if(!data.ok)throw new Error(data.error||'Lỗi');
  render(item.host,data.total);
  for(const part of item.more)render(part.el,matching(data.forms||{},part.d));
 }catch(e){
  item.host.textContent='Chưa tải được thống kê';
  for(const part of item.more)part.el.textContent='Chưa tải được thống kê';
  item.done=false;
 }
}
const first=items[0];
if(first)load(first);
// An already expanded lesson is immediately populated, while folded lessons load on opening.
for(const item of items){
 if(item!==first && item.w.open)load(item);
 item.w.addEventListener('toggle',()=>{if(item.w.open)load(item);});
}
})();
</script>
"""
@app.after_request
def inject_chapter_breakdown(response):
    if request.path!="/member/chapter" or response.status_code!=200 or response.mimetype!="text/html":
        return response
    try:
        raw=response.get_data(as_text=True)
        if "chapter-ui" not in raw or "chapter-breakdown-script" in raw:return response
        raw=raw.replace("</head>",STYLE+"</head>",1) if "</head>" in raw else STYLE+raw
        raw=raw.replace("</body>",JS+"</body>",1) if "</body>" in raw else raw+JS
        response.set_data(raw)
        response.headers["Cache-Control"]="no-cache"
    except Exception:pass
    return response
