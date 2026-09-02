# -*- coding: utf-8 -*-
"""Chiếu chung: một người dẫn, máy khác theo cùng câu (poll ~1s, RAM 1 worker)."""
from __future__ import annotations

import json
import random
import secrets
import threading
import time

from flask import jsonify, redirect, request, session, url_for

import app as base

_LOCK = threading.Lock()
_ROOMS: dict = {}
_ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TTL = 6 * 3600


def _now():
    return time.time()


def _prune():
    t = _now()
    dead = [c for c, r in _ROOMS.items() if t - float(r.get("updated") or 0) > _TTL]
    for c in dead:
        _ROOMS.pop(c, None)


def _new_code():
    for _ in range(30):
        c = "".join(random.choice(_ALPH) for _ in range(4))
        if c not in _ROOMS:
            return c
    return secrets.token_hex(3).upper()[:6]


def _host_id():
    m = base.member_current()
    if m:
        return str(m.get("username") or m.get("name") or "member")
    if base.admin_current():
        return "ADMIN"
    return ""


def _public_q(q, show_sol):
    p = base.question_payload(q)
    if not show_sol:
        p["solution"] = ""
        p.pop("answer", None)
        for o in p.get("options") or []:
            o["correct"] = False
        for o in p.get("statements") or []:
            o["correct"] = False
    p.pop("src", None)
    p.pop("file_idx", None)
    return p


def _snapshot(show_sol=None, zoom=None):
    path = str(session.get("practice_path") or "")
    ids = list(session.get("practice_ids") or [])
    pos = int(session.get("practice_pos") or 0)
    if not path or not ids or pos < 0 or pos >= len(ids):
        return None, "Chưa đang chiếu một câu (hãy vào làm bài trước)."
    try:
        qs = {q["idx"]: q for q in base.parse_lesson_questions(path)}
        if not qs:
            _, tex = base.read_tex(path)
            qs = {q["idx"]: q for q in base.parse_questions(tex)}
    except Exception as e:
        return None, str(e)
    q = qs.get(ids[pos])
    if not q:
        return None, "Không tải được câu hiện tại."
    show = bool(show_sol) if show_sol is not None else False
    try:
        z = float(zoom if zoom is not None else 1)
    except (TypeError, ValueError):
        z = 1.0
    z = max(0.8, min(2.6, z))
    return {
        "path": path,
        "pos": pos,
        "total": len(ids),
        "show_sol": show,
        "zoom": z,
        "q": _public_q(q, show),
        "updated": _now(),
    }, ""


def _room_out(room, include_q=True):
    d = {
        "ok": True,
        "code": room["code"],
        "ver": int(room.get("ver") or 0),
        "pos": int(room.get("pos") or 0),
        "total": int(room.get("total") or 0),
        "show_sol": bool(room.get("show_sol")),
        "zoom": float(room.get("zoom") or 1),
        "host": room.get("host") or "",
    }
    if include_q:
        d["q"] = room.get("q") or {}
    return d


@base.app.post("/api/present/start")
def api_present_start():
    hid = _host_id()
    if not hid:
        return jsonify(ok=False, error="Hãy đăng nhập để mở phòng chiếu."), 401
    data = request.get_json(silent=True) or {}
    snap, err = _snapshot(data.get("show_sol"), data.get("zoom"))
    if not snap:
        return jsonify(ok=False, error=err), 400
    with _LOCK:
        _prune()
        old = str(session.get("present_code") or "")
        if old in _ROOMS and _ROOMS[old].get("host") == hid:
            room = _ROOMS[old]
            room.update(snap)
            room["ver"] = int(room.get("ver") or 0) + 1
        else:
            code = _new_code()
            tok = secrets.token_hex(8)
            room = {"code": code, "token": tok, "host": hid, "ver": 1, **snap}
            _ROOMS[code] = room
            session["present_code"] = code
            session["present_token"] = tok
    origin = request.host_url.rstrip("/")
    url = origin + "/xem/" + room["code"]
    return jsonify(ok=True, code=room["code"], url=url, token=session.get("present_token") or room["token"], ver=room["ver"])


@base.app.post("/api/present/push")
def api_present_push():
    hid = _host_id()
    if not hid:
        return jsonify(ok=False, error="Chưa đăng nhập."), 401
    data = request.get_json(silent=True) or {}
    code = str(data.get("code") or session.get("present_code") or "").strip().upper()
    token = str(data.get("token") or session.get("present_token") or "")
    with _LOCK:
        room = _ROOMS.get(code)
        if not room or room.get("token") != token or room.get("host") != hid:
            return jsonify(ok=False, error="Phòng chiếu không đúng (hãy bấm Chiếu chung lại)."), 403
    snap, err = _snapshot(data.get("show_sol"), data.get("zoom"))
    if not snap:
        return jsonify(ok=False, error=err), 400
    with _LOCK:
        room = _ROOMS.get(code)
        if not room:
            return jsonify(ok=False, error="Phòng đã đóng."), 404
        room.update(snap)
        room["ver"] = int(room.get("ver") or 0) + 1
        ver = room["ver"]
    return jsonify(ok=True, ver=ver, pos=snap["pos"], total=snap["total"])


@base.app.post("/api/present/stop")
def api_present_stop():
    code = str((request.get_json(silent=True) or {}).get("code") or session.get("present_code") or "").strip().upper()
    token = str((request.get_json(silent=True) or {}).get("token") or session.get("present_token") or "")
    with _LOCK:
        room = _ROOMS.get(code)
        if room and room.get("token") == token:
            _ROOMS.pop(code, None)
    session.pop("present_code", None)
    session.pop("present_token", None)
    return jsonify(ok=True)


@base.app.get("/api/present/state")
def api_present_state():
    code = str(request.args.get("code") or "").strip().upper()
    try:
        since = int(request.args.get("ver") or 0)
    except (TypeError, ValueError):
        since = 0
    with _LOCK:
        _prune()
        room = _ROOMS.get(code)
        if not room:
            return jsonify(ok=False, error="Không có phòng này (hết hạn hoặc đã tắt)."), 404
        ver = int(room.get("ver") or 0)
        if since and since == ver:
            return jsonify(ok=True, unchanged=True, ver=ver)
        out = _room_out(room)
    return jsonify(out)


@base.app.get("/xem")
@base.app.get("/xem/<code>")
def present_watch(code=""):
    code = str(code or request.args.get("code") or "").strip().upper()
    if not code:
        body = (
            "<div class='wrap'><div class='panel' style='max-width:480px;margin:40px auto'><div class='head'>📺 Vào chiếu chung</div><div class='body'>"
            "<p class='muted'>Nhập mã 4 ký tự thầy/cô đưa (hoặc mở link <code>/xem/XXXX</code>).</p>"
            "<form method='get' action='/xem' style='display:flex;gap:8px;flex-wrap:wrap'>"
            "<input name='code' maxlength='8' placeholder='Ví dụ K7M2' style='flex:1;min-width:140px;padding:12px;font-size:22px;letter-spacing:.2em;text-transform:uppercase;text-align:center;border:1px solid #cbd8e6;border-radius:8px'>"
            "<button class='btn primary' type='submit'>Vào xem</button></form>"
            "<p class='muted'>Không cần đăng nhập. Màn hình sẽ tự theo câu thầy đang chiếu.</p>"
            "</div></div></div>"
            "<script>document.querySelector('form').addEventListener('submit',function(e){e.preventDefault();var c=(this.code.value||'').trim().toUpperCase();if(c)location.href='/xem/'+encodeURIComponent(c)})</script>"
        )
        return base.page("Vào chiếu chung", body)
    body = (
        "<div class='wrap'><div class='panel'><div class='head quiztop'>"
        f"<span>📺 Chiếu chung · mã <b id='pc'>{base.html.escape(code)}</b> · <span id='pmeta'>đang kết nối…</span></span>"
        "<span class='qzoombar'><span class='muted' id='phost'></span></span></div>"
        "<div class='body'><div id='perr' class='err'></div><div class='practice-q'><div id='q' class='qbox'></div></div>"
        "<p class='muted'>Tự cập nhật khi thầy chuyển câu. Toàn màn hình: nút ⛶ trên thanh xanh.</p></div></div></div>"
    )
    js = FOLLOW_JS.replace("__CODE__", json.dumps(code))
    return base.page("Chiếu chung " + code, body + js)


FOLLOW_JS = r"""
<script>
const CODE=__CODE__;
let lastVer=-1;
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function typeset(el){if(window.ldvlTypeset)return window.ldvlTypeset(el||document.getElementById('q'));}
function draw(q, showSol, zoom, pos, total){
  const box=document.getElementById('q');
  if(!box||!q) return;
  box.style.setProperty('--qzoom', String(zoom||1));
  let h=(q.nguon?'<div class="nguonrow"><span class="nguon">Nguồn: '+E(q.nguon)+'</span></div>':'')
    +'<div class="qtext"><b>Câu '+(pos+1)+'/'+total+'. </b>'+(q.id?'<span class="qid">ID '+E(q.id)+'</span> ':'')+q.text+'</div>';
  if(q.kind==='TN')(q.options||[]).forEach(function(o,i){
    const ok=showSol&&o.correct;
    h+='<div class="opt'+(ok?' correct':'')+'"><b>'+String.fromCharCode(65+i)+'.</b> '+o.text+(ok?' <span class="okmark">Đáp án đúng</span>':'')+'</div>';
  });
  else if(q.kind==='DS')(q.statements||[]).forEach(function(s,i){
    const mark=showSol?(' <span class="okmark">'+(s.correct?'Đúng':'Sai')+'</span>'):'';
    h+='<div class="tf'+(showSol?(s.correct?' correct':' wrong'):'')+'"><div class="tf-text"><b>'+(i+1)+'.</b> '+s.text+mark+'</div></div>';
  });
  else if(q.kind==='TLN') h+='<div class="answerline">'+(showSol?('<b>Đáp án:</b> '+E(q.answer||'—')):'✎ Trả lời ngắn')+'</div>';
  else h+='<div class="answerline">✎ Câu tự luận</div>';
  if(showSol&&q.solution) h+='<div class="solution"><b>📖 Lời giải</b><div>'+q.solution+'</div></div>';
  box.innerHTML=h;
  typeset(box);
  const m=document.getElementById('pmeta');
  if(m) m.textContent='câu '+(pos+1)+'/'+total+(showSol?' · đã mở lời giải':'');
}
async function tick(){
  const err=document.getElementById('perr');
  try{
    const r=await fetch('/api/present/state?code='+encodeURIComponent(CODE)+'&ver='+lastVer,{credentials:'same-origin'});
    const d=await r.json();
    if(!d.ok){if(err)err.textContent=d.error||'Mất phòng chiếu.';return;}
    if(d.unchanged) return;
    lastVer=d.ver;
    if(err) err.textContent='';
    const h=document.getElementById('phost');
    if(h) h.textContent=d.host?('Theo '+d.host):'';
    draw(d.q, !!d.show_sol, d.zoom, d.pos, d.total);
  }catch(e){if(err)err.textContent='Mất kết nối, đang thử lại…';}
}
tick();
setInterval(tick,1200);
</script>
"""

PRESENT_HOST_JS = r"""
<script>
(function(){
if(window.__ldvlPresentHost) return;
window.__ldvlPresentHost=true;
let P=null;
try{P=JSON.parse(localStorage.getItem('ldvlPresent')||'null')}catch(e){P=null}
function solVisible(){
  const sol=document.getElementById('solbox');
  return !!(sol && sol.style.display==='block');
}
function showBar(p){
  let el=document.getElementById('presentBar');
  if(!el){
    el=document.createElement('div');
    el.id='presentBar';
    el.className='notice';
    el.style.margin='0 0 10px';
    const body=document.querySelector('.panel .body');
    if(body) body.insertBefore(el, body.firstChild);
    else return;
  }
  if(!p){el.innerHTML='';el.hidden=true;return;}
  el.hidden=false;
  const url=p.url||(location.origin+'/xem/'+p.code);
  el.innerHTML='<b>📺 Chiếu chung</b> · mã <code style="font-size:22px;letter-spacing:.12em">'+p.code+'</code> '
    +'<a href="'+url+'" target="_blank" rel="noopener">'+url+'</a> '
    +'<button type="button" class="btn" id="pcopy">📋 Copy link</button> '
    +'<button type="button" class="btn red" id="pstop">Tắt chiếu</button> '
    +'<div class="muted">Học viên mở link (không cần đăng nhập). Máy họ tự theo câu thầy đang chiếu, kể cả khi thầy mở lời giải hoặc chỉnh cỡ chữ.</div>';
  const c=document.getElementById('pcopy');
  if(c) c.onclick=function(){navigator.clipboard.writeText(url).then(function(){c.textContent='✅ Đã copy'},function(){prompt('Copy link',url)})};
  const s=document.getElementById('pstop');
  if(s) s.onclick=async function(){
    await fetch('/api/present/stop',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({code:p.code,token:p.token})});
    P=null; try{localStorage.removeItem('ldvlPresent')}catch(e){}
    showBar(null);
  };
}
async function presentPush(){
  if(!P||!P.code) return;
  try{
    const r=await fetch('/api/present/push',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({code:P.code,token:P.token,show_sol:solVisible(),zoom:typeof qZoom==='number'?qZoom:1})});
    const d=await r.json().catch(function(){return {}});
    if(r.status===403||r.status===404){
      P=null; try{localStorage.removeItem('ldvlPresent')}catch(e){}
      showBar(null);
      if(d&&d.error) console.warn(d.error);
    }
  }catch(e){}
}
async function presentStart(){
  const r=await fetch('/api/present/start',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({show_sol:solVisible(),zoom:typeof qZoom==='number'?qZoom:1})});
  const d=await r.json();
  if(!d.ok){alert(d.error||'Không mở được phòng chiếu');return;}
  P={code:d.code,token:d.token,url:d.url};
  try{localStorage.setItem('ldvlPresent',JSON.stringify(P))}catch(e){}
  showBar(P);
}
function mountBtn(){
  const bar=document.querySelector('.qzoombar');
  if(!bar||document.getElementById('pStart')) return;
  const b=document.createElement('button');
  b.type='button'; b.className='btn primary'; b.id='pStart'; b.textContent='📺 Chiếu chung';
  b.title='Học viên xem cùng câu trên điện thoại / máy khác';
  b.onclick=presentStart;
  bar.appendChild(b);
  if(P&&P.code){showBar(P);presentPush();}
}
function wrap(name, afterMs){
  const fn=window[name];
  if(typeof fn!=='function'||fn.__ldvlPresent) return;
  const wrapped=function(){
    const out=fn.apply(this,arguments);
    if(afterMs) setTimeout(presentPush, afterMs);
    else presentPush();
    return out;
  };
  wrapped.__ldvlPresent=true;
  window[name]=wrapped;
}
wrap('ldvlApplyQZoom',0);
wrap('openSolution',60);
wrap('check',80);
wrap('draw',80);
mountBtn();
})();
</script>
"""
