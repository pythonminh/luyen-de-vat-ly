/* Presenter ink overlay for /member/lesson/game?mode=present. No backend changes. */
(() => {
  'use strict';
  const stage=document.getElementById('gameStage'), question=document.getElementById('gameQuestion');
  if (!stage || !question || stage.dataset.game!=='present') return;
  const style=document.createElement('style');
  style.textContent='.game-question{position:relative}.present-ink{position:absolute;inset:0;width:100%;height:100%;touch-action:none;pointer-events:none;z-index:2}.present-ink.active{pointer-events:auto;cursor:crosshair}.present-tools{display:flex;gap:6px;flex-wrap:wrap;align-items:center}.present-tools button{min-height:38px;padding:7px 10px;border:1px solid #aec9e6;border-radius:8px;background:#fff;color:#143d68;font-weight:700}.present-tools button[aria-pressed=true]{background:#174f91;color:white}.game-question{min-height:130px}';
  document.head.append(style);
  const toolbar=document.createElement('div');toolbar.className='present-tools';
  toolbar.setAttribute('role','group');toolbar.setAttribute('aria-label','Bút viết trên câu hỏi');
  const controls=stage.querySelector('.game-ctrl');
  if(!controls)return;
  controls.prepend(toolbar);
  let mode='off',drawing=false,last=null,strokes=[];
  const canvas=document.createElement('canvas');canvas.className='present-ink';canvas.setAttribute('aria-label','Lớp nét bút trên câu hỏi');
  question.append(canvas);
  const context=canvas.getContext('2d');
  function button(label,value,action){
    const b=document.createElement('button');b.type='button';b.textContent=label;
    if(value)b.setAttribute('aria-pressed','false');
    b.onclick=()=>action();toolbar.append(b);return b;
  }
  const pen=button('✎ Bút','pen',()=>setMode(mode==='pen'?'off':'pen'));
  const eraser=button('⌫ Tẩy','erase',()=>setMode(mode==='erase'?'off':'erase'));
  button('↺ Xóa nét',null,()=>{strokes=[];redraw()});
  function setMode(m){
    mode=m;pen.setAttribute('aria-pressed',String(m==='pen'));eraser.setAttribute('aria-pressed',String(m==='erase'));
    canvas.classList.toggle('active',m!=='off');
  }
  function measure(){
    const box=question.getBoundingClientRect(),scale=window.devicePixelRatio||1;
    const width=Math.max(1,Math.round(box.width*scale)),height=Math.max(1,Math.round(box.height*scale));
    if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;redraw();}
  }
  function redraw(){
    if(!context)return;
    const w=canvas.width,h=canvas.height;context.clearRect(0,0,w,h);
    for(const s of strokes){if(!s.points.length)continue;context.beginPath();context.strokeStyle=s.color;context.lineWidth=s.width*Math.min(w,h)/500;context.lineCap='round';context.lineJoin='round';
      s.points.forEach((p,i)=>i?context.lineTo(p[0]*w,p[1]*h):context.moveTo(p[0]*w,p[1]*h));if(s.points.length===1){context.lineTo(s.points[0][0]*w+0.2,s.points[0][1]*h+0.2)}context.stroke();
    }
  }
  function point(e){const r=canvas.getBoundingClientRect();return [(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height];}
  canvas.addEventListener('pointerdown',e=>{
    if(mode==='off')return;e.preventDefault();canvas.setPointerCapture(e.pointerId);drawing=true;
    const p=point(e);
    if(mode==='erase'){
      strokes=strokes.filter(s=>!s.points.some(q=>Math.hypot((q[0]-p[0])*canvas.width,(q[1]-p[1])*canvas.height)<25*(window.devicePixelRatio||1)));redraw();drawing=false;return;
    }
    last={color:'#d62828',width:3,points:[p]};strokes.push(last);redraw();
  });
  canvas.addEventListener('pointermove',e=>{if(!drawing||mode!=='pen'||!last)return;last.points.push(point(e));redraw();});
  function stop(){drawing=false;last=null;}
  canvas.addEventListener('pointerup',stop);canvas.addEventListener('pointercancel',stop);
  const questionText=document.createElement('span'); // Observe question changes without monitoring the canvas.
  const obs=new MutationObserver(mutations=>{
    if(mutations.some(m=>m.type==='characterData'||Array.from(m.removedNodes).some(n=>n!==canvas))) {
      strokes=[];window.requestAnimationFrame(()=>{if(!question.contains(canvas))question.append(canvas);measure();redraw();});
    }
  });
  obs.observe(question,{childList:true,characterData:true,subtree:false});
  if(window.ResizeObserver)new ResizeObserver(measure).observe(question);
  window.addEventListener('resize',measure);
  document.addEventListener('keydown',e=>{
    if(e.target.closest('input,textarea,select,[contenteditable]'))return;
    if(e.key.toLowerCase()==='p'){setMode(mode==='pen'?'off':'pen');}
    if(e.key==='Escape')setMode('off');
    if(e.key==='ArrowRight'&&!document.getElementById('gameNext').disabled)document.getElementById('gameNext').click();
  });
  measure();
})();