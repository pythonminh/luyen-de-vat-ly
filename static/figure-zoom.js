/* Independent figure zoom for shared presentation. No answers or server data. */
(function(){
'use strict';
const root=document.getElementById('q');if(!root)return;
// Exercise view: zoom only the figure in place; stem, options and answer stay visible.
if (document.querySelector('.vip-practice-wrap')) {
  const inlineStyle = document.createElement('style');
  inlineStyle.textContent = [
    '.fig-inline-frame{position:relative;width:100%;height:clamp(220px,29vw,340px);',
    'border:1px solid #cbd9ea;border-radius:8px;background:#fff;margin:12px 0;overflow:hidden;box-sizing:border-box}',
    '.fig-inline-stage{position:absolute;inset:0;overflow:hidden;touch-action:none;cursor:grab}',
    '.fig-inline-stage.is-dragging{cursor:grabbing}',
    '.fig-inline-content{position:absolute!important;top:50%!important;left:50%!important;',
    'width:max-content!important;max-width:none!important;max-height:none!important;',
    'height:max-content!important;overflow:visible!important;min-height:0!important;',
    'transform-origin:center center!important;box-sizing:border-box!important;margin:0!important}',
    '.fig-inline-content img,.fig-inline-content svg{display:block;max-width:none!important;',
    'max-height:none!important;width:auto!important;height:auto!important;object-fit:contain}',
    '.fig-inline-tools{position:absolute;right:6px;top:50%;transform:translateY(-50%);',
    'display:flex;flex-direction:column;gap:4px;z-index:5;background:#fffdf4;',
    'padding:4px;border:1px solid #cad6e3;border-radius:7px}',
    '.fig-inline-tools button{background:#159abb;color:#fff;border:0;border-radius:4px;',
    'min-width:36px;min-height:34px;font:700 21px Arial;cursor:pointer}',
    '.fig-inline-tools button:focus-visible{outline:3px solid #fbbf24}',
    '@media(max-width:600px){.fig-inline-frame{height:260px}.fig-inline-tools button{min-height:40px;min-width:40px}}'
  ].join('');
  document.head.append(inlineStyle);
  const selector='.qstem .immini,.qstem .tikz-row,.qstem .tikzfig,.qstem .tikz-live,.qfig .immini,.qfig .tikz-row,.qfig .tikzfig,.qfig .tikz-live';
  function mount(el) {
    if (!el.isConnected || el.closest('.fig-inline-frame')) return;
    // Do not create a second viewer around nested TikZ elements.
    if (el.parentElement?.closest('.immini,.tikz-row,.tikzfig,.tikz-live')) return;
    const frame=document.createElement('div');frame.className='fig-inline-frame';
    frame.setAttribute('aria-label','Hình minh họa có thể phóng to thu nhỏ');
    const stage=document.createElement('div');stage.className='fig-inline-stage';
    const bar=document.createElement('div');bar.className='fig-inline-tools';
    const originalParent=el.parentNode;
    originalParent.insertBefore(frame,el);
    stage.append(el);frame.append(stage);frame.append(bar);
    el.classList.add('fig-inline-content');
    let zoom=1,shiftX=0,shiftY=0,drag=null,pointers=new Map(),lastPinch=0;
    function paint(){
      el.style.setProperty('transform','translate(calc(-50% + '+shiftX+'px),calc(-50% + '+shiftY+'px)) scale('+zoom+')','important');
    }
    function setZoom(z){zoom=Math.min(6,Math.max(.12,z));paint();}
    function fit(){
      // Measure natural diagram dimensions, not the size of the question text.
      const w=Math.max(el.scrollWidth,el.offsetWidth,1);
      const h=Math.max(el.scrollHeight,el.offsetHeight,1);
      zoom=Math.max(.12,Math.min(2,(stage.clientWidth-24)/w,(stage.clientHeight-24)/h));
      shiftX=0;shiftY=0;paint();
    }
    function button(label,title,fn){
      const b=document.createElement('button');b.type='button';b.textContent=label;b.title=title;
      b.setAttribute('aria-label',title);b.addEventListener('click',e=>{e.stopPropagation();fn()});bar.append(b);
    }
    button('+','Phóng to hình',()=>setZoom(zoom*1.2));
    button('−','Thu nhỏ hình',()=>setZoom(zoom/1.2));
    button('↺','Đặt lại, vừa khung',fit);
    stage.addEventListener('wheel',e=>{if(e.ctrlKey||e.altKey){e.preventDefault();setZoom(zoom*(e.deltaY<0?1.12:1/1.12))}},{passive:false});
    stage.addEventListener('pointerdown',e=>{
      if(e.target.closest('button,a,input'))return;
      stage.setPointerCapture(e.pointerId);
      pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
      drag={x:e.clientX,y:e.clientY};stage.classList.add('is-dragging');
    });
    stage.addEventListener('pointermove',e=>{
      if(!pointers.has(e.pointerId))return;
      const prev=pointers.get(e.pointerId);
      pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
      if(pointers.size===1){shiftX+=e.clientX-prev.x;shiftY+=e.clientY-prev.y;paint();}
      else if(pointers.size===2){
        const p=Array.from(pointers.values());
        const d=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);
        if(lastPinch) setZoom(zoom*d/lastPinch);
        lastPinch=d;
      }
    });
    function end(e){pointers.delete(e.pointerId);lastPinch=0;if(!pointers.size){stage.classList.remove('is-dragging');drag=null;}}
    stage.addEventListener('pointerup',end);stage.addEventListener('pointercancel',end);
    if(window.ResizeObserver)new ResizeObserver(()=>{if(frame.isConnected&&zoom<=2)fit()}).observe(frame);
    requestAnimationFrame(fit);
    for(const img of el.querySelectorAll('img'))if(!img.complete)img.addEventListener('load',fit,{once:true});
    // MathJax/TikZ may arrive asynchronously.
    setTimeout(fit,450);
  }
  function mountAll(){
    root.querySelectorAll(selector).forEach(mount);
  }
  let scheduled=false;
  new MutationObserver(()=>{
    if(scheduled)return;scheduled=true;
    requestAnimationFrame(()=>{scheduled=false;mountAll()});
  }).observe(root,{childList:true,subtree:true});
  mountAll();
  return;
}
const css=document.createElement('style');
css.textContent=`
#q .qstem .immini,#q .qstem .tikz-row,#q .qfig .immini,#q .qfig .tikz-row{position:relative}
#q .fig-open{position:absolute;right:5px;top:5px;z-index:6;border:1px solid #b4d0ea;background:#fff;color:#144c7e;padding:5px 9px;border-radius:8px;font:700 13px system-ui;cursor:pointer;box-shadow:0 1px 6px #0002}
#q .immini:has(>.fig-open),#q .tikz-row:has(>.fig-open),#q .tikzfig:has(>.fig-open){overflow:visible!important}
.fig-lightbox{position:fixed;inset:0;z-index:2147483000;background:#071526ee;display:flex;flex-direction:column;color:white;align-items:center;padding:10px;gap:10px}
.fig-lightbox[hidden]{display:none}
.fig-lightbar{display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:8px;flex-shrink:0;width:100%}
.fig-lightbar button{border:1px solid #bbd3ef;border-radius:9px;background:#fff;color:#153a62;font:700 15px system-ui;padding:9px 13px;min-height:42px;cursor:pointer}
.fig-lightbar output{font:700 16px system-ui;min-width:64px;text-align:center}
.fig-lightviewport{flex:1;min-height:0;width:100%;background:white;border-radius:12px;overflow:hidden;touch-action:none;cursor:grab;position:relative}
.fig-lightviewport.dragging{cursor:grabbing}
.fig-lightcontent{position:absolute;left:50%;top:50%;transform-origin:center center;display:flex;align-items:center;justify-content:center;max-width:none!important;width:max-content;height:max-content}
.fig-lightcontent img,.fig-lightcontent svg{display:block!important;max-width:none!important;max-height:none!important}
.fig-lightcontent mjx-container{max-width:none!important}
.fig-lighthelp{font:13px system-ui;color:#dce9fa;text-align:center}
`;
document.head.append(css);
const modal=document.createElement('div');modal.className='fig-lightbox';modal.hidden=true;
modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.setAttribute('aria-label','Phóng to hình câu hỏi');
const bar=document.createElement('div');bar.className='fig-lightbar';
const view=document.createElement('div');view.className='fig-lightviewport';
const content=document.createElement('div');content.className='fig-lightcontent';view.append(content);
const help=document.createElement('div');help.className='fig-lighthelp';help.textContent='Kéo hình để di chuyển · Cuộn chuột hoặc chụm hai ngón để phóng to/thu nhỏ · Esc để đóng';
modal.append(bar,view,help);document.body.append(modal);
let scale=1,px=0,py=0,prevFocus=null,pointers=new Map(),prevDistance=0,baseScale=1;
const label=document.createElement('output');
function btn(t,fn){const b=document.createElement('button');b.type='button';b.textContent=t;b.addEventListener('click',fn);bar.append(b);return b}
btn('− Thu nhỏ',()=>zoom(scale/1.2));bar.append(label);btn('+ Phóng to',()=>zoom(scale*1.2));btn('Vừa khung',fit);btn('1:1',()=>{scale=1;px=0;py=0;paint()});const close=btn('✕ Đóng',hide);
function paint(){content.style.transform='translate(calc(-50% + '+px+'px),calc(-50% + '+py+'px)) scale('+scale+')';label.textContent=Math.round(scale*100)+'%'}
function zoom(z){scale=Math.max(.15,Math.min(8,z));paint()}
function fit(){
 const w=content.scrollWidth||content.offsetWidth||600,h=content.scrollHeight||content.offsetHeight||400;
 const rw=view.clientWidth||800,rh=view.clientHeight||600;
 scale=Math.max(.15,Math.min(5,Math.min((rw-30)/w,(rh-30)/h)));
 px=py=0;paint();
}
function hide(){modal.hidden=true;content.replaceChildren();pointers.clear();document.body.style.removeProperty('overflow');prevFocus?.focus?.()}
function open(target){
 const clone=target.cloneNode(true);clone.querySelectorAll('.fig-open,script,button,input').forEach(x=>x.remove());
 clone.querySelectorAll('[id]').forEach(x=>x.removeAttribute('id'));
 content.replaceChildren(clone);px=py=0;prevFocus=document.activeElement;modal.hidden=false;
 document.body.style.overflow='hidden';close.focus();
 if(window.MathJax?.typesetPromise)window.MathJax.typesetPromise([content]).catch(()=>{});
 requestAnimationFrame(()=>{fit();setTimeout(fit,100)});
 content.querySelectorAll('img').forEach(img=>{if(!img.complete)img.addEventListener('load',fit,{once:true})});
}
function figures(){
 const result=[];
 root.querySelectorAll('.qstem .immini,.qstem .tikz-row,.qstem .tikzfig,.qstem .tikz-live,.qfig .immini,.qfig .tikz-row,.qfig .tikzfig,.qfig .tikz-live').forEach(el=>{
  if(el.closest('.fig-lightbox')||el.closest('.immini,.tikz-row')!==null&& !el.matches('.immini,.tikz-row'))return;
  if(el.querySelector('.fig-open'))return;
  result.push(el);
 });
 return result;
}
function attach(){
 for(const el of figures()){
  el.style.position='relative';
  const b=document.createElement('button');b.type='button';b.className='fig-open';b.textContent='⛶ Phóng hình';b.title='Phóng lớn, thu nhỏ và kéo hình';b.onclick=e=>{e.preventDefault();e.stopPropagation();open(el)};el.append(b);
 }
}
let queued=false;
new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;attach()})}).observe(root,{childList:true,subtree:true});
attach();
view.addEventListener('wheel',e=>{e.preventDefault();zoom(scale*(e.deltaY>0?.9:1.1))},{passive:false});
view.addEventListener('pointerdown',e=>{view.setPointerCapture(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});view.classList.add('dragging')});
view.addEventListener('pointermove',e=>{
 if(!pointers.has(e.pointerId))return;
 const old=pointers.get(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
 if(pointers.size===1){px+=e.clientX-old.x;py+=e.clientY-old.y;paint()}
 else if(pointers.size===2){const p=Array.from(pointers.values()),d=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);if(prevDistance)zoom(baseScale*d/prevDistance);else{prevDistance=d;baseScale=scale}}
});
function pointerEnd(e){pointers.delete(e.pointerId);if(pointers.size<2)prevDistance=0;if(!pointers.size)view.classList.remove('dragging')}
view.addEventListener('pointerup',pointerEnd);view.addEventListener('pointercancel',pointerEnd);
document.addEventListener('keydown',e=>{if(modal.hidden)return;if(e.key==='Escape'){e.preventDefault();hide()}else if(e.key==='+'||e.key==='='){e.preventDefault();zoom(scale*1.2)}else if(e.key==='-'){e.preventDefault();zoom(scale/1.2)}});
})();