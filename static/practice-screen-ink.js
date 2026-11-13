/* Screen annotation: presentation ink, local only, independent of answers. */
(()=>{'use strict';
if(!document.querySelector('.vip-practice-wrap')||document.getElementById('ldvlInkToolbar'))return;
const style=document.createElement('style');
style.textContent=[
'#ldvlInkCanvas{position:fixed;inset:0;width:100vw;height:100vh;z-index:2147481800;pointer-events:none;touch-action:none}',
'#ldvlInkCanvas.active{pointer-events:auto;cursor:crosshair}',
'#ldvlInkToolbar{position:fixed;right:8px;top:50%;transform:translateY(-50%);z-index:2147481900;display:flex;flex-direction:column;gap:4px;padding:5px;background:#fff;border:1px solid #b9cde3;border-radius:12px;box-shadow:0 5px 20px #0b295333;max-height:90dvh;overflow:auto}',
'#ldvlInkToolbar[hidden]{display:none}',
'#ldvlInkToolbar button{width:36px;height:36px;border:1px solid #c3d3e6;border-radius:7px;background:#edf5ff;color:#17466d;font-size:19px;cursor:pointer}',
'#ldvlInkToolbar button[aria-pressed=true]{background:#176bd3;color:#fff;border-color:#176bd3}',
'#ldvlInkToolbar .ink-color{width:25px;height:25px;border-radius:50%;margin:1px auto;border:2px solid #fff;box-shadow:0 0 0 1px #9aafc4}',
'#ldvlInkToolbar .ink-color[aria-pressed=true]{box-shadow:0 0 0 3px #176bd3}',
'#ldvlInkToolbar .sep{height:1px;background:#cbd5e1;margin:2px 3px}',
'#ldvlInkTab{position:fixed;right:6px;bottom:90px;z-index:2147481900;border:1px solid #b9cde3;border-radius:9px;background:#176bd3;color:#fff;padding:9px 12px}',
'#ldvlInkTab[hidden]{display:none}',
'@media print{#ldvlInkToolbar,#ldvlInkCanvas,#ldvlInkTab{display:none!important}}'
].join('');
document.head.append(style);
const canvas=document.createElement('canvas');canvas.id='ldvlInkCanvas';document.body.append(canvas);
const bar=document.createElement('div');bar.id='ldvlInkToolbar';bar.setAttribute('role','toolbar');bar.setAttribute('aria-label','Bút viết trên màn hình');document.body.append(bar);
const ctx=canvas.getContext('2d');if(!ctx){canvas.remove();bar.remove();return;}
let mode='off',color='#e11d48',thickness=3,strokes=[],stroke=null,pointer=null,vw=1,vh=1;
function button(symbol,title,fn){const b=document.createElement('button');b.type='button';b.textContent=symbol;b.title=title;b.setAttribute('aria-label',title);b.addEventListener('click',fn);bar.append(b);return b;}
function separator(){const e=document.createElement('div');e.className='sep';bar.append(e);}
const select=button('☝','Chọn đáp án / tắt bút',()=>setMode('off'));
const pen=button('✎','Viết hoặc khoanh tròn',()=>setMode('pen'));
const eraser=button('⌫','Tẩy nét',()=>setMode('erase'));
function setMode(m){mode=m;canvas.classList.toggle('active',m!=='off');[select,pen,eraser].forEach((b,i)=>b.setAttribute('aria-pressed',String(m===['off','pen','erase'][i])));}
separator();
const choices=['#e11d48','#2563eb','#15803d','#111827','#f59e0b'];
const swatches=choices.map(c=>{const b=button('','Đổi màu '+c,()=>{color=c;updateColors();if(mode==='off')setMode('pen');});b.classList.add('ink-color');b.style.backgroundColor=c;return b;});
function updateColors(){swatches.forEach((b,i)=>b.setAttribute('aria-pressed',String(choices[i]===color)));}
updateColors();separator();
const thin=button('•','Nét mảnh',()=>setThickness(3)),bold=button('●','Nét đậm',()=>setThickness(7));
function setThickness(n){thickness=n;thin.setAttribute('aria-pressed',String(n===3));bold.setAttribute('aria-pressed',String(n===7));}
setThickness(3);separator();
button('↶','Hoàn tác nét cuối',()=>{strokes.pop();draw()});
button('▤','Xóa toàn bộ nét',()=>{strokes=[];stroke=null;draw()});
const tab=document.createElement('button');tab.id='ldvlInkTab';tab.textContent='✎';tab.title='Mở công cụ vẽ';tab.hidden=true;tab.onclick=()=>{bar.hidden=false;tab.hidden=true};document.body.append(tab);
button('✕','Ẩn bảng bút',()=>{bar.hidden=true;tab.hidden=false;setMode('off')});
setMode('off');
function resize(){vw=Math.max(1,innerWidth);vh=Math.max(1,innerHeight);const dpr=Math.min(3,devicePixelRatio||1);canvas.width=Math.round(vw*dpr);canvas.height=Math.round(vh*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);draw();}
function paint(s){if(!s||!s.points.length)return;ctx.beginPath();ctx.strokeStyle=s.color;ctx.lineWidth=s.thickness;ctx.lineJoin='round';ctx.lineCap='round';s.points.forEach((p,i)=>i?ctx.lineTo(p[0]*vw,p[1]*vh):ctx.moveTo(p[0]*vw,p[1]*vh));if(s.points.length===1){const p=s.points[0];ctx.lineTo(p[0]*vw+.01,p[1]*vh+.01);}ctx.stroke();}
function draw(){ctx.clearRect(0,0,vw,vh);strokes.forEach(paint);paint(stroke);}
function pos(e){return[e.clientX/vw,e.clientY/vh];}
function erase(p){const x=p[0]*vw,y=p[1]*vh;strokes=strokes.filter(s=>!s.points.some(q=>Math.hypot(q[0]*vw-x,q[1]*vh-y)<20));draw();}
canvas.addEventListener('pointerdown',e=>{if(mode==='off')return;e.preventDefault();canvas.setPointerCapture(e.pointerId);pointer=e.pointerId;if(mode==='erase'){erase(pos(e));return;}stroke={color,thickness,points:[pos(e)]};draw();});
canvas.addEventListener('pointermove',e=>{if(e.pointerId!==pointer)return;if(mode==='erase'){erase(pos(e));return;}if(stroke){stroke.points.push(pos(e));draw();}});
function end(e){if(e.pointerId!==pointer)return;if(stroke){strokes.push(stroke);stroke=null;}pointer=null;draw();}
canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);
window.addEventListener('scroll',()=>{if(strokes.length){strokes=[];stroke=null;draw();}},{passive:true});
window.addEventListener('resize',resize);
document.addEventListener('keydown',e=>{if(e.key==='Escape')setMode('off');if(/INPUT|TEXTAREA|SELECT/.test(e.target?.tagName||'')||e.target?.isContentEditable)return;if(e.key.toLowerCase()==='p'&&!e.ctrlKey&&!e.altKey)setMode(mode==='pen'?'off':'pen');});
resize();
})();