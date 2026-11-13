/* Independent figure zoom for shared presentation. No answers or server data. */
(function(){
'use strict';
const root=document.getElementById('q');if(!root)return;
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