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
let mode='off',color='#e11d48',thickness=3,strokes=[],stroke=null,pointer=null,vw=1,vh=1,shapes=[],selected=-1,shapeDraft=null,drag=null;
function button(symbol,title,fn){const b=document.createElement('button');b.type='button';b.textContent=symbol;b.title=title;b.setAttribute('aria-label',title);b.addEventListener('click',fn);bar.append(b);return b;}
function separator(){const e=document.createElement('div');e.className='sep';bar.append(e);}
const select=button('☝','Chọn đáp án / tắt bút',()=>setMode('off'));
const pen=button('✎','Viết hoặc khoanh tròn',()=>setMode('pen'));
const eraser=button('⌫','Tẩy nét',()=>setMode('erase'));
const edit=button('⬡','Chọn hình và kéo các đỉnh',()=>setMode('edit'));
const shapeButtons={};
function setMode(m){mode=m;canvas.classList.toggle('active',m!=='off');[select,pen,eraser,edit].forEach((b,i)=>b.setAttribute('aria-pressed',String(m===['off','pen','erase','edit'][i])));Object.entries(shapeButtons).forEach(([k,b])=>b.setAttribute('aria-pressed',String(m===k)));draw();}
separator();
const choices=['#e11d48','#2563eb','#15803d','#111827','#f59e0b'];
const swatches=choices.map(c=>{const b=button('','Đổi màu '+c,()=>{color=c;updateColors();if(mode==='off')setMode('pen');});b.classList.add('ink-color');b.style.backgroundColor=c;return b;});
function updateColors(){swatches.forEach((b,i)=>b.setAttribute('aria-pressed',String(choices[i]===color)));}
updateColors();separator();
// Shapes remain editable: every displayed vertex is a draggable control.
const models=[['line','╱','Đoạn thẳng'],['triangle','△','Tam giác'],
 ['quad','▱','Tứ giác (kéo từng đỉnh)'],['circle','○','Đường tròn'],
 ['prism','⬡','Lăng trụ tam giác'],['box','▣','Hình hộp'],['pyramid','⌂','Hình chóp']];
models.forEach(([key,icon,name])=>{shapeButtons[key]=button(icon,name+' — kéo để tạo',()=>setMode(key));});
const smaller=button('⊖','Thu nhỏ hình đang chọn',()=>scaleShape(.8));
const bigger=button('⊕','Phóng to hình đang chọn',()=>scaleShape(1.25));
button('⌦','Xóa hình đang chọn',()=>{if(selected>=0){shapes.splice(selected,1);selected=-1;draw();}});
separator();
const thin=button('•','Nét mảnh',()=>setThickness(3)),bold=button('●','Nét đậm',()=>setThickness(7));
function setThickness(n){thickness=n;thin.setAttribute('aria-pressed',String(n===3));bold.setAttribute('aria-pressed',String(n===7));}
setThickness(3);separator();
button('↶','Hoàn tác nét/hình cuối',()=>{if(selected>=0){shapes.splice(selected,1);selected=-1;}else if(shapes.length)shapes.pop();else strokes.pop();draw()});
button('▤','Xóa toàn bộ nét và hình',()=>{strokes=[];shapes=[];stroke=null;shapeDraft=null;selected=-1;draw()});
const tab=document.createElement('button');tab.id='ldvlInkTab';tab.textContent='✎';tab.title='Mở công cụ vẽ';tab.hidden=true;tab.onclick=()=>{bar.hidden=false;tab.hidden=true};document.body.append(tab);
button('✕','Ẩn bảng bút',()=>{bar.hidden=true;tab.hidden=false;setMode('off')});
setMode('off');
function resize(){vw=Math.max(1,innerWidth);vh=Math.max(1,innerHeight);const dpr=Math.min(3,devicePixelRatio||1);canvas.width=Math.round(vw*dpr);canvas.height=Math.round(vh*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);draw();}
function paint(s){if(!s||!s.points.length)return;ctx.beginPath();ctx.strokeStyle=s.color;ctx.lineWidth=s.thickness;ctx.lineJoin='round';ctx.lineCap='round';s.points.forEach((p,i)=>i?ctx.lineTo(p[0]*vw,p[1]*vh):ctx.moveTo(p[0]*vw,p[1]*vh));if(s.points.length===1){const p=s.points[0];ctx.lineTo(p[0]*vw+.01,p[1]*vh+.01);}ctx.stroke();}
function polygon(points,closed){
  if(!points.length)return;ctx.beginPath();
  points.forEach((p,i)=>i?ctx.lineTo(p[0]*vw,p[1]*vh):ctx.moveTo(p[0]*vw,p[1]*vh));
  if(closed)ctx.closePath();ctx.stroke();
}
function drawShape(s,highlight=false){
  const p=s.points;ctx.save();ctx.lineWidth=s.thickness;ctx.strokeStyle=s.color;
  ctx.lineJoin='round';ctx.lineCap='round';
  if(s.type==='circle'){
    const c=p[0],r=p[1];ctx.beginPath();ctx.arc(c[0]*vw,c[1]*vh,Math.hypot((r[0]-c[0])*vw,(r[1]-c[1])*vh),0,Math.PI*2);ctx.stroke();
  }else if(s.type==='line')polygon(p,false);
  else if(s.type==='triangle'||s.type==='quad')polygon(p,true);
  else if(s.type==='prism'){
    polygon(p.slice(0,3),true);polygon(p.slice(3,6),true);
    for(let i=0;i<3;i++)polygon([p[i],p[i+3]],false);
  }else if(s.type==='box'){
    polygon(p.slice(0,4),true);polygon(p.slice(4,8),true);
    for(let i=0;i<4;i++)polygon([p[i],p[i+4]],false);
  }else if(s.type==='pyramid'){
    polygon(p.slice(0,4),true);for(let i=0;i<4;i++)polygon([p[i],p[4]],false);
  }
  if(highlight){
    ctx.lineWidth=1;ctx.strokeStyle='#145bb0';ctx.fillStyle='#fff';
    p.forEach(pt=>{ctx.beginPath();ctx.arc(pt[0]*vw,pt[1]*vh,7,0,Math.PI*2);ctx.fill();ctx.stroke();});
  }
  ctx.restore();
}
function draw(){ctx.clearRect(0,0,vw,vh);strokes.forEach(paint);paint(stroke);shapes.forEach((s,i)=>drawShape(s,selected===i&&mode==='edit'));if(shapeDraft)drawShape(shapeDraft,true);}
function scaleShape(f){
  if(selected<0||!shapes[selected]){setMode('edit');return;}
  const s=shapes[selected];const cx=s.points.reduce((a,p)=>a+p[0],0)/s.points.length;
  const cy=s.points.reduce((a,p)=>a+p[1],0)/s.points.length;
  s.points=s.points.map(p=>[cx+(p[0]-cx)*f,cy+(p[1]-cy)*f]);setMode('edit');
}
function geometry(type,a,b){
  const minX=Math.min(a[0],b[0]),maxX=Math.max(a[0],b[0]);
  const minY=Math.min(a[1],b[1]),maxY=Math.max(a[1],b[1]);
  const dx=maxX-minX,dy=maxY-minY;
  let p;
  if(type==='line')p=[a,b];
  else if(type==='triangle')p=[[minX,minY+dy],[minX+dx/2,minY],[maxX,maxY]];
  else if(type==='quad')p=[[minX,minY],[maxX,minY],[maxX,maxY],[minX,maxY]];
  else if(type==='circle')p=[[(a[0]+b[0])/2,(a[1]+b[1])/2],[(a[0]+b[0])/2+Math.max(dx*vw,dy*vh)/2/vw,(a[1]+b[1])/2]];
  else if(type==='prism'){
    const base=[[minX,minY+dy*.5],[minX+dx*.38,minY],[minX+dx*.67,minY+dy*.65]];
    p=base.concat(base.map(q=>[q[0]+dx*.33,q[1]+dy*.35]));
  }else if(type==='box'){
    const base=[[minX,minY+dy*.35],[minX+dx*.68,minY+dy*.35],[minX+dx*.68,maxY],[minX,maxY]];
    p=base.concat(base.map(q=>[q[0]+dx*.3,q[1]-dy*.32]));
  }else if(type==='pyramid'){
    p=[[minX,minY+dy*.57],[minX+dx*.65,minY+dy*.57],[maxX,maxY],[minX+dx*.35,maxY],[minX+dx*.52,minY]];
  }else p=[a,b];
  return {type,points:p,color,thickness};
}
const dist=(a,b)=>Math.hypot((a[0]-b[0])*vw,(a[1]-b[1])*vh);
function findShape(pt){
  for(let i=shapes.length-1;i>=0;i--){
    for(let j=0;j<shapes[i].points.length;j++)if(dist(pt,shapes[i].points[j])<18)return {i,j};
    const p=shapes[i].points;
    if(p.length>1){
      const minX=Math.min(...p.map(v=>v[0]))-.02,maxX=Math.max(...p.map(v=>v[0]))+.02;
      const minY=Math.min(...p.map(v=>v[1]))-.02,maxY=Math.max(...p.map(v=>v[1]))+.02;
      if(pt[0]>=minX&&pt[0]<=maxX&&pt[1]>=minY&&pt[1]<=maxY)return {i,j:-1};
    }
  }
  return null;
}
function pos(e){return[e.clientX/vw,e.clientY/vh];}
function erase(p){const x=p[0]*vw,y=p[1]*vh;strokes=strokes.filter(s=>!s.points.some(q=>Math.hypot(q[0]*vw-x,q[1]*vh-y)<20));draw();}
canvas.addEventListener('pointerdown',e=>{
  if(mode==='off')return;e.preventDefault();canvas.setPointerCapture(e.pointerId);pointer=e.pointerId;
  const p=pos(e);
  if(mode==='erase'){erase(p);return;}
  if(mode==='edit'){
    const hit=findShape(p);selected=hit?hit.i:-1;
    drag=hit?{kind:hit.j>=0?'vertex':'move',j:hit.j,last:p}:null;
    draw();return;
  }
  if(shapeButtons[mode]){shapeDraft=geometry(mode,p,[p[0]+.08,p[1]+.10]);drag={kind:'create',start:p};draw();return;}
  stroke={color,thickness,points:[p]};draw();
});
canvas.addEventListener('pointermove',e=>{
  if(e.pointerId!==pointer)return;
  const p=pos(e);
  if(mode==='erase'){erase(p);return;}
  if(mode==='edit'&&drag&&selected>=0){
    const target=shapes[selected];
    if(drag.kind==='vertex')target.points[drag.j]=p;
    else{const dx=p[0]-drag.last[0],dy=p[1]-drag.last[1];target.points=target.points.map(q=>[q[0]+dx,q[1]+dy]);}
    drag.last=p;draw();return;
  }
  if(drag?.kind==='create'){shapeDraft=geometry(mode,drag.start,p);draw();return;}
  if(stroke){stroke.points.push(p);draw();}
});
function end(e){
  if(e.pointerId!==pointer)return;
  if(stroke){strokes.push(stroke);stroke=null;}
  if(shapeDraft){shapes.push(shapeDraft);selected=shapes.length-1;shapeDraft=null;setMode('edit');}
  drag=null;pointer=null;draw();
}
canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);
window.addEventListener('scroll',()=>{if(strokes.length||shapes.length){strokes=[];shapes=[];selected=-1;stroke=null;draw();}},{passive:true});
window.addEventListener('resize',resize);
document.addEventListener('keydown',e=>{if(e.key==='Escape')setMode('off');if(/INPUT|TEXTAREA|SELECT/.test(e.target?.tagName||'')||e.target?.isContentEditable)return;if(e.key.toLowerCase()==='p'&&!e.ctrlKey&&!e.altKey)setMode(mode==='pen'?'off':'pen');});
resize();
})();