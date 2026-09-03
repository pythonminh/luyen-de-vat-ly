# -*- coding: utf-8 -*-
"""Chiếu chung: một người dẫn, máy khác theo cùng câu (poll ~1s, RAM 1 worker)."""
from __future__ import annotations

import json
import random
import re
import secrets
import threading
import time

from flask import jsonify, request, session

import app as base

_LOCK = threading.Lock()
_QS_LOCK = threading.Lock()
_ROOMS: dict = {}
_QS_CACHE: dict = {}
_ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TTL = 6 * 3600


def _now():
    return time.time()


def _prune():
    t = _now()
    dead = [c for c, r in _ROOMS.items() if t - float(r.get("updated") or 0) > _TTL]
    for c in dead:
        _ROOMS.pop(c, None)


def _norm_code(raw):
    c = re.sub(r"[^A-Z0-9]", "", str(raw or "").upper())
    if 3 <= len(c) <= 6:
        return c
    return ""


def _new_code():
    for _ in range(40):
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


def _sanitize_live(raw):
    d = raw if isinstance(raw, dict) else {}
    live = {"tn": None, "ds": [], "text": "", "checked": False, "ok": None}
    try:
        if d.get("tn") is not None and d.get("tn") != "":
            n = int(d["tn"])
            live["tn"] = n if 0 <= n <= 8 else None
    except (TypeError, ValueError):
        live["tn"] = None
    ds = d.get("ds")
    if isinstance(ds, list):
        out = []
        for x in ds[:12]:
            if x is True or x == 1 or x == "1":
                out.append(True)
            elif x is False or x == 0 or x == "0":
                out.append(False)
            else:
                out.append(None)
        live["ds"] = out
    live["text"] = str(d.get("text") or "")[:2000]
    live["checked"] = bool(d.get("checked"))
    if d.get("ok") is not None:
        live["ok"] = bool(d.get("ok"))
    return live


def _lesson_qs(path):
    path = str(path or "")
    with _QS_LOCK:
        hit = _QS_CACHE.get(path)
        if hit is not None:
            return hit
    qs = {q["idx"]: q for q in base.parse_lesson_questions(path)}
    if not qs:
        _, tex = base.read_tex(path)
        qs = {q["idx"]: q for q in base.parse_questions(tex)}
    with _QS_LOCK:
        if len(_QS_CACHE) > 48:
            _QS_CACHE.clear()
        _QS_CACHE[path] = qs
    return qs


def _snapshot(show_sol=None, zoom=None, reveal=False):
    path = str(session.get("practice_path") or "")
    ids = list(session.get("practice_ids") or [])
    pos = int(session.get("practice_pos") or 0)
    if not path or not ids or pos < 0 or pos >= len(ids):
        return None, "Chưa đang chiếu một câu (hãy vào làm bài trước)."
    try:
        qs = _lesson_qs(path)
    except Exception as e:
        return None, str(e)
    q = qs.get(ids[pos])
    if not q:
        return None, "Không tải được câu hiện tại."
    show = bool(show_sol)
    keys = bool(show or reveal)
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
        "q": _public_q(q, keys),
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
        "live": room.get("live") or {},
    }
    if include_q:
        d["q"] = room.get("q") or {}
    return d


def _put_room(hid, code, token, snap, live):
    """Tạo/cập nhật phòng. Cùng thầy được lấy lại mã sau khi server restart."""
    with _LOCK:
        _prune()
        room = _ROOMS.get(code) if code else None
        if room and room.get("host") and room.get("host") != hid:
            return None, f"Mã {code} đang được người khác dùng. Chọn mã khác."
        if not room:
            if not code:
                code = _new_code()
            tok = token if token and len(str(token)) >= 8 else secrets.token_hex(8)
            room = {"code": code, "token": tok, "host": hid, "ver": 0}
            _ROOMS[code] = room
        room.update(snap)
        room["live"] = live
        room["host"] = hid
        room["code"] = code
        room["ver"] = int(room.get("ver") or 0) + 1
        room["updated"] = _now()
        session["present_code"] = room["code"]
        session["present_token"] = room["token"]
        return room, ""


@base.app.post("/api/present/start")
def api_present_start():
    hid = _host_id()
    if not hid:
        return jsonify(ok=False, error="Hãy đăng nhập để mở phòng chiếu."), 401
    data = request.get_json(silent=True) or {}
    live = _sanitize_live(data.get("live"))
    snap, err = _snapshot(data.get("show_sol"), data.get("zoom"), reveal=live["checked"])
    if not snap:
        return jsonify(ok=False, error=err), 400
    want = _norm_code(data.get("code"))
    if data.get("code") not in (None, "") and not want:
        return jsonify(ok=False, error="Mã phải 3–6 ký tự (chữ hoặc số), ví dụ 1234 hoặc K7M2."), 400
    with _LOCK:
        _prune()
        old = _norm_code(session.get("present_code"))
        mine = old if old in _ROOMS and _ROOMS[old].get("host") == hid else None
        if want:
            taken = _ROOMS.get(want)
            if taken and taken.get("host") != hid:
                return jsonify(ok=False, error=f"Mã {want} đang được người khác dùng. Chọn mã khác."), 409
            if mine and mine != want:
                room = _ROOMS.pop(mine)
                room["code"] = want
                _ROOMS[want] = room
                mine = want
            elif taken and taken.get("host") == hid:
                mine = want
        if mine:
            room = _ROOMS[mine]
            room.update(snap)
            room["live"] = live
            room["ver"] = int(room.get("ver") or 0) + 1
            session["present_code"] = room["code"]
            session["present_token"] = room["token"]
        else:
            code = want or _new_code()
            tok = secrets.token_hex(8)
            room = {"code": code, "token": tok, "host": hid, "ver": 1, "live": live, **snap}
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
    code = _norm_code(data.get("code") or session.get("present_code") or "")
    token = str(data.get("token") or session.get("present_token") or "")
    live = _sanitize_live(data.get("live"))
    snap, err = _snapshot(data.get("show_sol"), data.get("zoom"), reveal=live["checked"])
    if not snap:
        with _LOCK:
            room = _ROOMS.get(code)
            if room and room.get("host") == hid:
                room["live"] = live
                room["show_sol"] = bool(data.get("show_sol"))
                room["ver"] = int(room.get("ver") or 0) + 1
                room["updated"] = _now()
                return jsonify(ok=True, ver=room["ver"], pos=room.get("pos"), total=room.get("total"), token=room.get("token"))
        return jsonify(ok=False, error=err), 400
    if not code:
        return jsonify(ok=False, error="Thiếu mã phòng."), 400
    room, rerr = _put_room(hid, code, token, snap, live)
    if not room:
        return jsonify(ok=False, error=rerr), 409
    return jsonify(ok=True, ver=room["ver"], pos=snap["pos"], total=snap["total"], token=room.get("token"), code=room["code"])


@base.app.post("/api/present/stop")
def api_present_stop():
    code = _norm_code((request.get_json(silent=True) or {}).get("code") or session.get("present_code") or "")
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
    code = _norm_code(request.args.get("code") or "")
    try:
        since = int(request.args.get("ver") or 0)
    except (TypeError, ValueError):
        since = 0
    with _LOCK:
        _prune()
        room = _ROOMS.get(code)
        if not room:
            return jsonify(
                ok=False,
                waiting=True,
                error="Chưa có phòng mã này. Thầy phải vào làm bài, bấm 📺 Chiếu chung, rồi dùng đúng mã hiện trên thanh (hoặc đặt mã này).",
            ), 404
        ver = int(room.get("ver") or 0)
        room["updated"] = _now()
        if since and since == ver:
            return jsonify(ok=True, unchanged=True, ver=ver)
        out = _room_out(room)
    return jsonify(out)


@base.app.get("/xem")
@base.app.get("/xem/<code>")
def present_watch(code=""):
    code = _norm_code(code or request.args.get("code") or "")
    if not code:
        body = (
            "<div class='wrap'><div class='panel' style='max-width:480px;margin:40px auto'><div class='head'>📺 Vào chiếu chung</div><div class='body'>"
            "<p class='muted'>Gõ đúng mã thầy đưa sau khi bấm <b>Chiếu chung</b> (3–6 ký tự, ví dụ <code>K7M2</code> hoặc <code>1234</code> nếu thầy đặt mã đó). Không tự bịa mã khi thầy chưa mở phòng.</p>"
            "<form method='get' action='/xem' style='display:flex;gap:8px;flex-wrap:wrap'>"
            "<input name='code' maxlength='8' placeholder='Mã thầy đưa' style='flex:1;min-width:140px;padding:12px;font-size:22px;letter-spacing:.2em;text-transform:uppercase;text-align:center;border:1px solid #cbd8e6;border-radius:8px'>"
            "<button class='btn primary' type='submit'>Vào xem</button></form>"
            "<p class='muted'>Không cần đăng nhập. Trang tự theo câu thầy đang chiếu.</p>"
            "</div></div></div>"
            "<script>document.querySelector('form').addEventListener('submit',function(e){e.preventDefault();var c=(this.code.value||'').trim().toUpperCase();if(c)location.href='/xem/'+encodeURIComponent(c)})</script>"
        )
        return base.page("Vào chiếu chung", body)
    js = FOLLOW_JS.replace("__CODE__", json.dumps(code))
    body = (
        "<div class='cinemahud'>"
        "<button type='button' title='Toàn màn hình' onclick='ldvlToggleFs()'>⛶</button>"
        "<a href='/xem' title='Thoát'>✕</a></div>"
        f"<div class='cinema-q'><div id='perr' class='err'></div><div id='q' class='qbox' hidden></div></div>"
        + js
    )
    return base.page("Chiếu chung " + code, body, cinema=True)


FOLLOW_JS = r"""
<script>
const CODE=__CODE__;
let lastVer=-1;
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function fitQuestion(){
  const box=document.getElementById('q');
  if(!box||box.hidden) return;
  const availH=Math.max(220, window.innerHeight-28);
  const availW=Math.max(240, window.innerWidth-20);
  let lo=0.95, hi=2.5, best=0.95;
  for(let i=0;i<12;i++){
    const mid=(lo+hi)/2;
    box.style.setProperty('--qzoom', String(mid));
    void box.offsetHeight;
    if(box.scrollHeight<=availH+6 && box.scrollWidth<=availW+6){best=mid;lo=mid;}
    else hi=mid;
  }
  box.style.setProperty('--qzoom', String(Math.max(0.95, Math.min(2.5, Math.round(best*0.97*10)/10))));
}
function typeset(el){
  const box=el||document.getElementById('q');
  const done=function(){fitQuestion()};
  const p=window.ldvlTypeset?window.ldvlTypeset(box):null;
  if(p&&typeof p.then==='function') p.then(done, done); else setTimeout(done,120);
}
function draw(q, showSol, pos, total, live){
  const box=document.getElementById('q');
  if(!box||!q) return;
  live=live||{};
  const checked=!!live.checked;
  box.hidden=false;
  let h='<div class="qheadline"><span class="qbadge">Câu '+(pos+1)+'</span><div class="qstem">'+q.text+'</div></div>';
  if(checked && live.ok!=null){
    const labs='ABCD';
    let head=live.ok?'Đúng':'Sai';
    function row(label, items){
      const n=Math.max(items.length,1);
      const cells=items.map(function(it){
        const ds=it.mark||'';
        if(!ds){
          return '<span class="keycell '+(it.cls||'')+'"><span class="kcirc tn">'+it.letter+'</span></span>';
        }
        const kind=ds==='Đ'?'d':(ds==='S'?'s':'');
        return '<span class="keycell '+(it.cls||'')+'"><span class="klet">'+it.letter+'</span><span class="kcirc '+kind+'">'+ds+'</span></span>';
      }).join('');
      return '<div class="keyrow" style="grid-template-columns:7.2em repeat('+n+',2.6em)"><span class="keylab">'+label+'</span>'+cells+'</div>';
    }
    let extra='';
    if(q.kind==='TN'){
      const key=(q.options||[]).map(function(o,i){return o.correct?labs.charAt(i):''}).filter(Boolean).join('')||'?';
      const pick=live.tn==null?'?':labs.charAt(live.tn);
      extra='<div class="keygrid">'+row('Đáp án đúng',[{letter:key,mark:'',cls:'ok'}])+row('Thầy chọn',[{letter:pick,mark:'',cls:pick===key?'ok':'bad'}])+'</div>';
    }else if(q.kind==='DS'){
      const keys=(q.statements||[]).map(function(s){return s.correct?'Đ':'S'});
      const ans=keys.map(function(m,i){return {letter:labs.charAt(i),mark:m,cls:'ok'}});
      const you=keys.map(function(m,i){const p=(live.ds||[])[i];const mk=p===true?'Đ':(p===false?'S':'?');return {letter:labs.charAt(i),mark:mk,cls:mk===m?'ok':'bad'}});
      extra='<div class="keygrid">'+row('Đáp án đúng',ans)+row('Thầy chọn',you)+'</div>';
    }
    h+='<div class="result '+(live.ok?'good':'bad')+'">'+head+extra+'</div>';
  }
  if(q.kind==='TN')(q.options||[]).forEach(function(o,i){
    const picked=live.tn===i;
    let cls='opt';
    if(o.correct) cls+=' correct';
    else if(checked&&picked) cls+=' wrong';
    else if(!checked&&picked) cls+=' picked';
    let flags='';
    if(picked) flags+='<span class="pickmark">◀ thầy chọn</span>';
    if(o.correct) flags+='<span class="okmark">Đáp án đúng</span>';
    h+='<div class="'+cls+'"><span class="tflab">'+String.fromCharCode(65+i)+'</span><div class="tf-text">'+o.text+'</div>'+(flags?'<div class="tf-flags">'+flags+'</div>':'')+'</div>';
  });
  else if(q.kind==='DS'){
    h+='<div class="qbody ds"><div class="qfig" hidden></div><div class="qtf"><div class="tfgrid"><div class="tf-colhead"><span></span><span></span><span class="tf-h yes">Đúng</span><span class="tf-h no">Sai</span></div>';
    (q.statements||[]).forEach(function(s,i){
    const pick=(live.ds||[])[i];
    const has=pick===true||pick===false;
    const revealed=showSol||checked;
    let cls='tf';
    if(revealed&&s.correct) cls+=' correct';
    else if(checked&&has&&pick!==s.correct) cls+=' wrong';
    const lab='ABCD'.charAt(i)||(i+1);
    h+='<div class="'+cls+'"><span class="tflab">'+lab+'</span><div class="tf-text">'+s.text+'</div>'
      +'<span class="tf-box yes'+(pick===true?' pick':'')+(revealed&&s.correct?' on':'')+'"></span>'
      +'<span class="tf-box no'+(pick===false?' pick':'')+(revealed&&!s.correct?' on':'')+'"></span></div>';
  });
    h+='</div></div></div>';
  }
  else {
    const typed=String(live.text||'').trim();
    h+='<div class="answerline">'+(typed?('<b>Thầy viết:</b> '+E(typed)):'✎ Đang chờ thầy nhập…')+'</div>';
    if(showSol&&q.answer) h+='<div class="answerline result good"><b>Đáp án đúng:</b> '+E(q.answer)+'</div>';
  }
  if(showSol&&q.solution) h+='<div class="solution"><b>📖 Lời giải</b><div>'+q.solution+'</div></div>';
  box.innerHTML=h;
  (function(){
    const stem=box.querySelector('.qstem');
    const fig=box.querySelector('.qfig');
    const body=box.querySelector('.qbody.ds');
    if(!stem||!fig||!body) return;
    const bits=[];
    stem.querySelectorAll('.immini,.tikz-row,.tikzfig,.tikz-live,.ytbox,table.tex-table').forEach(function(el){
      if(el.closest('.immini,.tikz-row')&&!el.matches('.immini,.tikz-row')) return;
      bits.push(el);
    });
    if(!bits.length){fig.remove();return;}
    bits.forEach(function(el){fig.appendChild(el)});
    fig.hidden=false;
    body.classList.add('hassplit');
  })();
  typeset(box);
}
async function tick(){
  const err=document.getElementById('perr');
  const box=document.getElementById('q');
  try{
    const r=await fetch('/api/present/state?code='+encodeURIComponent(CODE)+'&ver='+lastVer,{credentials:'same-origin'});
    const d=await r.json();
    if(!d.ok){
      if(lastVer<0){
        if(box) box.hidden=true;
        if(err) err.innerHTML=(d.error||'Chưa có phòng.')
          +'<div class="muted" style="margin-top:8px;font-weight:400">Đợi thầy bấm <b>Chiếu chung</b> với mã <code>'+E(CODE)+'</code> · <a href="/xem">Mã khác</a></div>';
      }else if(err){
        err.innerHTML='<span class="muted" style="font-weight:700">Đang kết nối lại…</span>';
      }
      return;
    }
    if(d.unchanged) return;
    lastVer=d.ver;
    if(err) err.textContent='';
    draw(d.q, !!d.show_sol, d.pos, d.total, d.live||{});
  }catch(e){
    if(err) err.textContent='Mất kết nối, đang thử lại…';
  }
}
tick();
setInterval(tick,900);
window.addEventListener('resize',function(){fitQuestion()});
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
function collectLive(){
  const q=window.Q||{};
  const live={tn:null,ds:[],text:'',checked:!!window.checked,ok:null};
  if(q.kind==='TN'){
    const z=document.querySelector('#q input[name=a]:checked');
    live.tn=z?+z.value:null;
  }else if(q.kind==='DS'){
    const n=(q.statements||[]).length;
    for(let i=0;i<n;i++){
      const z=document.querySelector('#q input[name=t'+i+']:checked');
      live.ds.push(z?z.value==='1':null);
    }
  }else{
    const z=document.getElementById('ans');
    live.text=z?String(z.value||''):'';
  }
  if(window.checked && window.LAST_REVIEW && typeof window.LAST_REVIEW.ok==='boolean') live.ok=window.LAST_REVIEW.ok;
  return live;
}
function payload(){
  return {code:P&&P.code,token:P&&P.token,show_sol:solVisible(),zoom:typeof qZoom==='number'?qZoom:1,live:collectLive()};
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
    +'<div class="muted">Học viên mở link: chỉ thấy câu hỏi (ẩn menu). Họ theo bước chọn và lời giải khi thầy mở.</div>';
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
  if(!P||!P.code||P._busy) return;
  try{
    const r=await fetch('/api/present/push',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify(payload())});
    const d=await r.json().catch(function(){return {}});
    if(d&&d.ok){
      if(d.token&&P){P.token=d.token;try{localStorage.setItem('ldvlPresent',JSON.stringify(P))}catch(e){}}
      return;
    }
    if(r.status===401) return;
    await presentResume();
  }catch(e){}
}
async function presentResume(){
  if(!P||!P.code||P._busy) return;
  P._busy=true;
  try{
    const r=await fetch('/api/present/start',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify(Object.assign(payload(),{code:P.code}))});
    const d=await r.json().catch(function(){return {}});
    if(d&&d.ok){
      P={code:d.code,token:d.token,url:d.url};
      try{localStorage.setItem('ldvlPresent',JSON.stringify(P))}catch(e){}
      showBar(P);
    }
  }catch(e){}
  finally{if(P)P._busy=false}
}
async function presentStart(){
  const suggest=(P&&P.code)||'1234';
  const typed=prompt('Mã chiếu cho lớp gõ vào (3–6 ký tự). Có thể đặt 1234 cho dễ nhớ:', suggest);
  if(typed===null) return;
  const r=await fetch('/api/present/start',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify(Object.assign(payload(),{code:String(typed||'').trim()}))});
  const d=await r.json();
  if(!d.ok){alert(d.error||'Không mở được phòng chiếu');return;}
  P={code:d.code,token:d.token,url:d.url};
  try{localStorage.setItem('ldvlPresent',JSON.stringify(P))}catch(e){}
  showBar(P);
}
let pushTimer=0;
function presentPushSoon(){
  clearTimeout(pushTimer);
  pushTimer=setTimeout(presentPush,160);
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
  setInterval(function(){if(P&&P.code)presentPush();},5000);
  document.addEventListener('change',function(e){
    const qel=document.getElementById('q');
    if(P&&qel&&e.target&&qel.contains(e.target)) presentPushSoon();
  });
  document.addEventListener('input',function(e){
    const qel=document.getElementById('q');
    if(P&&qel&&e.target&&qel.contains(e.target)) presentPushSoon();
  });
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
wrap('openSolution',60);
wrap('check',80);
wrap('draw',80);
mountBtn();
})();
</script>
"""
