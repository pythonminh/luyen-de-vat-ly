"""Show actual question-type and difficulty breakdown for each supplementary game lesson."""
from __future__ import annotations

import collections
import html
import json
import threading
import time

from flask import jsonify, request
import app as base

app = base.app
_cache = {}
_lock = threading.Lock()
TTL = 120

def _stats(path):
    now = time.monotonic()
    with _lock:
        old = _cache.get(path)
        if old and now - old[0] < TTL:
            return old[1]
    rows = base.load_lesson_questions(path)
    kinds = {k: 0 for k in ("TN", "DS", "TLN", "TL")}
    levels = {k: 0 for k in ("N", "H", "V", "C")}
    matrix = {k: {lv: 0 for lv in levels} for k in kinds}
    unknown = 0
    for q in rows:
        k = str(q.get("kind") or "").strip().upper()
        if k not in kinds:
            continue
        kinds[k] += 1
        lv = base.norm_muc(q.get("level"))
        if lv in levels:
            levels[lv] += 1
            matrix[k][lv] += 1
        else:
            unknown += 1
    result = {"total": sum(kinds.values()), "kinds": kinds, "levels": levels, "matrix": matrix, "unknown": unknown}
    with _lock:
        if len(_cache) > 500:
            _cache.clear()
        _cache[path] = (now, result)
    return result

@app.post("/api/member/game/bank-stats")
def game_bank_stats():
    import exam_game
    member = base.member_current()
    if not member:
        return jsonify(ok=False, error="Cần đăng nhập."), 401
    data = request.get_json(silent=True) or {}
    main = str(data.get("main") or "").strip()
    ctx = exam_game.context_for(main)
    if not ctx or not base.can_practice(member, main):
        return jsonify(ok=False, error="Không có quyền truy cập."), 403
    lesson, subject, grade = ctx
    allowed = {str(r.get("path")) for r in exam_game.extra_lessons(main, member, lesson, subject, grade)}
    paths = data.get("paths") or []
    if not isinstance(paths, list) or len(paths) > 8 or len(paths) == 0 or any(not isinstance(p, str) or p not in allowed for p in paths):
        return jsonify(ok=False, error="Danh sách bài không hợp lệ."), 400
    out = {}
    for p in dict.fromkeys(paths):
        try:
            out[p] = _stats(p)
        except Exception:
            out[p] = {"error": "Không đọc được thống kê"}
    response = jsonify(ok=True, stats=out)
    response.headers["Cache-Control"] = "no-store"
    return response

CSS = """
<style id="game-bank-breakdown-style">
.game-more-item > span {flex:1;min-width:0}
.game-bank-stats{display:block;margin-top:7px;color:#315574;font-size:11px;line-height:1.5}
.game-bank-line{display:flex;flex-wrap:wrap;align-items:center;gap:4px 6px;margin-top:4px}
.game-bank-chip{display:inline-flex;align-items:center;gap:3px;border:1px solid #d8e4f2;background:#f5f9ff;border-radius:6px;padding:2px 6px;font-size:11px;font-weight:700;color:#31567c;white-space:nowrap}
.game-bank-chip b{font-weight:850;color:#113a65;font-variant-numeric:tabular-nums}
.game-bank-chip.no{opacity:.57}
.game-bank-details{display:block;margin-top:5px;font-size:10px;color:#5c7089}
.game-bank-label{font-weight:750;color:#254d76}
.game-bank-error{color:#aa4b34}
.game-more-item:has(input:checked) .game-bank-chip{background:#fff}
@media(max-width:720px){.game-bank-chip{font-size:10px;padding:2px 5px}.game-bank-stats{font-size:10px}}
</style>
"""
JS = r"""
<script id="game-bank-breakdown-script">
(function(){
 const list = document.querySelector('.game-more-list');
 const form = document.querySelector('.game-select form[action="/member/game"]');
 if(!list || !form) return;
 const main = form.querySelector('input[name="path"]')?.value;
 if(!main) return;
 const items = [...list.querySelectorAll('.game-more-item')].map(el => {
  const p = el.querySelector('input[name="more"]')?.value;
  const label = el.querySelector('span');
  if(!p || !label)return null;
  let box=label.querySelector('.game-bank-stats');
  if(box && box.dataset.serverStats==='1')return null;
  if(!box){
   box=document.createElement('span');
   box.className='game-bank-stats';
   box.setAttribute('role','status');
   box.textContent='Đang tải phân bố câu…';
   label.appendChild(box);
  }
  return {p,el,box,queued:false,loaded:false};
 }).filter(Boolean);
 if(!items.length)return;
 const pending = new Set();
 let busy=false;
 function chip(name,n){
  const span=document.createElement('span');
  span.className='game-bank-chip'+(n===0?' no':'');
  const b=document.createElement('b'); b.textContent=String(n);
  span.append(document.createTextNode(name+' '),b);return span;
 }
 function line(label, pairs){
  const row=document.createElement('span');row.className='game-bank-line';
  const head=document.createElement('span');head.className='game-bank-label';head.textContent=label;
  row.append(head);
  for(const [name,num] of pairs)row.append(chip(name,Number(num)||0));
  return row;
 }
 function show(item, data){
  item.box.replaceChildren();
  if(!data || data.error){
   const err=document.createElement('span');err.className='game-bank-error';
   err.textContent=data?.error||'Chưa tải được phân bố câu';
   item.box.append(err);return;
  }
  const k=data.kinds||{},lv=data.levels||{};
  item.box.append(line('Loại:',[['TN',k.TN],['Đ/S',k.DS],['TLN',k.TLN],['TL',k.TL]]));
  item.box.append(line('Mức:',[['NB',lv.N],['TH',lv.H],['VD',lv.V],['VDC',lv.C]]));
  const small=document.createElement('span'); small.className='game-bank-details';
  small.textContent='Tổng đã phân loại: '+data.total+' câu'+(data.unknown?' · Chưa rõ mức: '+data.unknown:'');
  const matrix=data.matrix||{};
  small.title=['TN','DS','TLN','TL'].map(k=>{
    const m=matrix[k]||{};
    return k+': NB '+(m.N||0)+' · TH '+(m.H||0)+' · VD '+(m.V||0)+' · VDC '+(m.C||0);
  }).join('\n');
  item.box.append(small);
 }
 function queue(item){if(item.queued||item.loaded)return;item.queued=true;pending.add(item);drain();}
 async function drain(){
  if(busy||!pending.size)return;
  busy=true;
  while(pending.size){
   const batch=[...pending].slice(0,8);
   for(const item of batch)pending.delete(item);
   try{
    const res=await fetch('/api/member/game/bank-stats',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({main,paths:batch.map(x=>x.p)})});
    if(!res.ok)throw new Error('HTTP '+res.status);
    const data=await res.json();
    if(!data.ok)throw new Error(data.error||'Không đọc được');
    for(const item of batch){item.loaded=true;show(item,data.stats?.[item.p]);}
   }catch(err){for(const item of batch){item.queued=false;item.box.textContent='Chưa tải được thống kê';}}
  }
  busy=false;
 }
 const observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries=>{
  for(const entry of entries)if(entry.isIntersecting){const item=items.find(x=>x.el===entry.target);if(item){queue(item);observer.unobserve(item.el);}}
 },{root:list,rootMargin:'140px'}) : null;
 // The list scrolls inside an enclosing 360px panel; observe it rather than the full page.
 // Use a viewport fallback when browsers don't support the nested scroll root.
 if(observer)for(const item of items)observer.observe(item.el);
 else for(const item of items)queue(item);
 for(const item of items)if(item.el.querySelector('input[name="more"]:checked'))queue(item);
})();
</script>
"""

@app.after_request
def game_breakdown_ui(response):
    if request.path != "/member/game" or response.status_code != 200 or response.mimetype != "text/html":
        return response
    try:
        body=response.get_data(as_text=True)
        if 'game-more-list' not in body or 'game-bank-breakdown-script' in body:
            return response
        body=body.replace('</head>',CSS+'</head>',1) if '</head>' in body else CSS+body
        body=body.replace('</body>',JS+'</body>',1) if '</body>' in body else body+JS
        response.set_data(body)
        response.headers['Cache-Control']='no-cache'
    except Exception:
        pass
    return response
