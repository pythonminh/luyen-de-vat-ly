/* Timed full-exam game: real clock, server-based deadline, leave/split detection.
   Browser detection is best-effort; server independently rejects expired answers. */
(function () {
  'use strict';
  function mountGameMonitor() {
  const cfg=window.__ldvlGameConfig;
  const box=document.querySelector('.vip-practice-wrap[data-game-level]');
  if (!cfg || !box || !cfg.attempt) return;
  const hud=document.querySelector('.practice-game-hud');
  if(!hud) return;
  const clocks=document.createElement('div');
  clocks.className='game-live-clocks';
  clocks.setAttribute('role','group');
  clocks.setAttribute('aria-label','Đồng hồ và thời gian còn lại');
  clocks.innerHTML='<span class="game-remaining">⏳ Còn <b id="gameRemaining">--:--</b></span>'+
      '<span class="game-realtime">🕒 <b id="gameClock">--:--:--</b></span>';
  const meters=hud.querySelector('.ph-meters');
  if(meters) hud.insertBefore(clocks,meters); else hud.appendChild(clocks);

  let ended=false,localNavigating=false;
  const key='ldvlExamEnded_'+String(cfg.attempt);
  function formatClock(){
    const n=new Date();
    return [n.getHours(),n.getMinutes(),n.getSeconds()]
      .map(v=>String(v).padStart(2,'0')).join(':');
  }
  function formatRemaining(t){
    t=Math.max(0,Math.ceil(t));
    return String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0');
  }
  function send(reason){
    if(ended || localNavigating)return;
    ended=true;
    try{sessionStorage.setItem(key,reason)}catch(e){}
    const payload=JSON.stringify({reason:reason,attempt:cfg.attempt});
    try{
      if(navigator.sendBeacon){
        navigator.sendBeacon('/member/game/violation',
          new Blob([payload],{type:'application/json'}));
      }
    }catch(e){}
    try{
      fetch('/member/game/violation',{
        method:'POST',credentials:'same-origin',keepalive:true,
        headers:{'Content-Type':'application/json'},body:payload
      }).catch(function(){});
    }catch(e){}
    if(document.visibilityState==='visible'){
      setTimeout(()=>{if(!localNavigating)location.replace('/member/game/ended');},160);
    }
  }
  function tick(){
    const clock=document.getElementById('gameClock');
    if(clock)clock.textContent=formatClock();
    const left=Number(cfg.deadline)*1000-Date.now();
    const remaining=document.getElementById('gameRemaining');
    if(remaining)remaining.textContent=formatRemaining(left/1000);
    if(left<=0)send('timeout');
    else if(left<=5*60*1000 && clocks)clocks.classList.add('game-time-warning');
  }
  function split(){
    // Android tablet viewport relative to its physical screen.
    // Some WebViews report window dimensions as screen dimensions; impossible
    // to detect every split configuration reliably in a standard webpage.
    const android=/Android/i.test(navigator.userAgent);
    const sw=Number(screen.width)||0,sh=Number(screen.height)||0;
    if(!android || Math.min(sw,sh)<600)return false;
    const width=window.visualViewport?window.visualViewport.width:window.innerWidth;
    const height=window.visualViewport?window.visualViewport.height:window.innerHeight;
    // Soft keyboard changes height, but is not a split-screen violation.
    const typing=document.activeElement &&
      document.activeElement.matches('input,textarea,[contenteditable="true"]');
    return width<sw*.68 || (!typing && height<sh*.58);
  }
  function internalLink(target){
    if(!(target instanceof Element))return false;
    const link=target.closest('a[href]');
    if(link){
      try{
        const url=new URL(link.href,location.href);
        if(url.origin===location.origin &&
           (/^\/practice\/jump\/\d+$/.test(url.pathname) ||
            url.pathname==='/member/practice'))return true;
      }catch(e){}
    }
    const btn=target.closest('button');
    if(btn && btn.id==='next')return true;
    return false;
  }
  document.addEventListener('click',function(event){
    if(internalLink(event.target))localNavigating=true;
  },true);
  window.addEventListener('pagehide',function(){
    if(!localNavigating)send('pagehide');
  });
  document.addEventListener('visibilitychange',function(){
    if(document.visibilityState==='hidden')send('hidden');
    else if(ended){
      location.replace('/member/game/ended');
    }
  });
  let blurred=null;
  window.addEventListener('blur',function(){
    if(localNavigating || ended)return;
    blurred=setTimeout(function(){
      if(!localNavigating && document.visibilityState==='visible' &&
         !document.hasFocus())send('blur');
    },550);
  });
  window.addEventListener('focus',function(){
    if(blurred){clearTimeout(blurred);blurred=null;}
    if(ended)location.replace('/member/game/ended');
  });
  let resizeTimer=null;
  window.addEventListener('resize',function(){
    clearTimeout(resizeTimer);
    resizeTimer=setTimeout(()=>{if(split())send('split');},450);
  },{passive:true});
  if(split()){send('split');return;}
  tick();
  const id=setInterval(()=>{if(ended){clearInterval(id);return;}tick();},1000);
  try{if(sessionStorage.getItem(key)){ended=true;location.replace('/member/game/ended');}}catch(e){}
  }
  // The compact question HUD is built on DOMContentLoaded by practice-workspace.js.
  // Both files load with defer; starting here earlier would silently skip all clocks.
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',mountGameMonitor,{once:true});
  } else {
    mountGameMonitor();
  }
})();
