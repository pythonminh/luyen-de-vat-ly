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
let mode='off',color='#e11d48',thickness=3,strokes=[],stroke=null,pointer=null,vw=1,vh=1,shapes=[],selected=-1,shapeDraft=null,drag=null,lineStyle='solid',selectedEdge=-1,selectedVertex=-1,vectorHead='single';
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
 ['vector','→','Vectơ có mũi tên'],['doublevector','↔','Vectơ hai chiều'],
 ['prism','⬡','Lăng trụ tam giác'],['box','▣','Hình hộp'],['pyramid','⌂','Hình chóp']];
models.forEach(([key,icon,name])=>{shapeButtons[key]=button(icon,name+' — kéo để tạo',()=>setMode(key));});
const labelVector=button('A⃗','Đặt tên vectơ hoặc tên hai đầu mút',()=>{
  const sh=shapes[selected];if(!sh||!['vector','doublevector'].includes(sh.type)){setMode('edit');return;}
  const value=window.prompt('Nhãn vectơ (ví dụ: a, u, AB; bỏ trống để ẩn):',sh.label||'');
  if(value===null)return;sh.label=value.trim().slice(0,20);draw();
});
const reverseVector=button('⇄','Đảo chiều vectơ đã chọn',()=>{
  const sh=shapes[selected];if(!sh||!['vector','doublevector'].includes(sh.type))return;
  sh.points.reverse();draw();
});
const copyVector=button('⧉','Sao chép và tịnh tiến vectơ đã chọn',()=>{
  const sh=shapes[selected];if(!sh||!['vector','doublevector'].includes(sh.type))return;
  const offset=[45/vw,35/vh];
  const cloned={...sh,points:sh.points.map(p=>[p[0]+offset[0],p[1]+offset[1]]),edgeStyles:{...(sh.edgeStyles||{})}};
  shapes.push(cloned);selected=shapes.length-1;selectedEdge=-1;setMode('edit');draw();
});
separator();
const solidBtn=button('━','Nét liền: áp dụng cho cạnh đang chọn hoặc hình mới',()=>setLineStyle('solid'));
const dashedBtn=button('┄','Nét đứt: áp dụng cho cạnh đang chọn hoặc hình mới',()=>setLineStyle('dashed'));
function refreshLineStyles(){
  const active=selected>=0&&shapes[selected];
  const value=active?(selectedEdge>=0?(active.edgeStyles?.[selectedEdge]||active.lineStyle||'solid'):(active.lineStyle||'solid')):lineStyle;
  solidBtn.setAttribute('aria-pressed',String(value==='solid'));dashedBtn.setAttribute('aria-pressed',String(value==='dashed'));
}
function setLineStyle(value){
  lineStyle=value;
  if(selected>=0&&shapes[selected]){
    const sh=shapes[selected];
    if(selectedEdge>=0){sh.edgeStyles=sh.edgeStyles||{};sh.edgeStyles[selectedEdge]=value;}
    else{sh.lineStyle=value;sh.edgeStyles={};}
  }
  refreshLineStyles();draw();
}
refreshLineStyles();
// Geometric constructions are stored on their parent shape and recomputed while dragging vertices.
separator();
button('M','Đánh dấu trung điểm cạnh đã chọn',()=>addConstruction('midpoint'));
button('M↗','Vẽ đường trung tuyến từ đỉnh đối diện đến trung điểm cạnh',()=>addConstruction('median'));
button('⟂','Dựng đường vuông góc (đường cao hoặc trung trực)',()=>addConstruction('perpendicular'));
button('∠½','Dựng đường phân giác trong tam giác',()=>addConstruction('bisector'));
function addConstruction(kind){
  const sh=shapes[selected];
  if(!sh){window.alert('Chọn hình hoặc cạnh bằng công cụ ⬡ trước.');setMode('edit');return;}
  const edges=edgesFor(sh);
  if(!edges.length){window.alert('Hình này chưa hỗ trợ dựng đường theo cạnh.');return;}
  if((kind==='median'||kind==='bisector')&&sh.type!=='triangle'){
    window.alert('Chọn một tam giác để dựng trung tuyến hoặc phân giác.');return;
  }
  let edge=selectedEdge>=0?selectedEdge:0;
  // When a triangle vertex is selected, select the opposite edge instead.
  if(sh.type==='triangle'&&selectedVertex>=0&&kind!=='bisector'){
    const e=edges.findIndex(pair=>!pair.includes(selectedVertex));
    if(e>=0)edge=e;
  }
  const vertex=(kind==='bisector'?(selectedVertex>=0?selectedVertex:0):
    sh.type==='triangle'?[0,1,2].find(i=>!edges[edge].includes(i)):-1);
  if(kind==='bisector'&&selectedVertex<0&&selectedEdge>=0){
    window.alert('Để vẽ phân giác: bấm ⬡ rồi chọn đỉnh tam giác, sau đó bấm ∠½.');return;
  }
  const record={kind,edge,vertex,color,thickness,lineStyle};
  sh.constructions=sh.constructions||[];
  // Avoid stacking identical constructions when clicking the same button repeatedly.
  if(!sh.constructions.some(c=>c.kind===kind&&c.edge===edge&&c.vertex===vertex)){
    sh.constructions.push(record);
  }
  setMode('edit');draw();
}
const smaller=button('⊖','Thu nhỏ hình đang chọn',()=>scaleShape(.8));
const bigger=button('⊕','Phóng to hình đang chọn',()=>scaleShape(1.25));
button('⌦','Xóa hình đang chọn',()=>{if(selected>=0){shapes.splice(selected,1);selected=-1;selectedEdge=-1;refreshLineStyles();draw();}});
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
function edgesFor(s){
  const t=s.type;
  if(t==='line'||t==='vector'||t==='doublevector')return [[0,1]];
  if(t==='triangle')return [[0,1],[1,2],[2,0]];
  if(t==='quad')return [[0,1],[1,2],[2,3],[3,0]];
  if(t==='prism')return [[0,1],[1,2],[2,0],[3,4],[4,5],[5,3],[0,3],[1,4],[2,5]];
  if(t==='box')return [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
  if(t==='pyramid')return [[0,1],[1,2],[2,3],[3,0],[0,4],[1,4],[2,4],[3,4]];
  return [];
}
function vectorArrow(a,b,width){
  const ax=a[0]*vw,ay=a[1]*vh,bx=b[0]*vw,by=b[1]*vh;
  const dx=bx-ax,dy=by-ay,len=Math.hypot(dx,dy);
  if(len<1)return;
  const unitX=dx/len,unitY=dy/len;
  const side=Math.max(7,Math.min(17,width*3.7));
  const depth=Math.max(13,Math.min(24,width*6));
  ctx.beginPath();ctx.moveTo(bx-unitX*depth-unitY*side,by-unitY*depth+unitX*side);
  ctx.lineTo(bx,by);ctx.lineTo(bx-unitX*depth+unitY*side,by-unitY*depth-unitX*side);ctx.stroke();
}
function vectorCaption(s){
  if(!s.label)return;
  const p=s.points,a=p[0],b=p[1],dx=(b[0]-a[0])*vw,dy=(b[1]-a[1])*vh;
  const d=Math.max(1,Math.hypot(dx,dy)),cx=(a[0]+b[0])*vw/2,cy=(a[1]+b[1])*vh/2;
  const label=String(s.label).slice(0,20);
  ctx.save();ctx.setLineDash([]);ctx.fillStyle=s.color;ctx.textAlign='center';ctx.textBaseline='middle';
  ctx.font='bold 18px Arial, sans-serif';ctx.fillText(label,cx+dy/d*18,cy-dx/d*18);ctx.restore();
}
function constructionDraw(s){
  if(!s.constructions?.length)return;
  const p=s.points,edges=edgesFor(s);
  const pixel=i=>[p[i][0]*vw,p[i][1]*vh];
  const segment=(a,b)=>{
    ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();
  };
  for(const c of s.constructions){
    const pair=edges[c.edge];if(!pair)continue;
    const A=pixel(pair[0]),B=pixel(pair[1]);
    const ux=B[0]-A[0],uy=B[1]-A[1],L=Math.hypot(ux,uy);
    if(L<1e-5)continue;
    const M=[(A[0]+B[0])/2,(A[1]+B[1])/2];
    ctx.save();ctx.strokeStyle=c.color;ctx.fillStyle=c.color;
    ctx.lineWidth=c.thickness;ctx.setLineDash(c.lineStyle==='dashed'?[8,5]:[]);
    if(c.kind==='midpoint'||c.kind==='median'){
      ctx.beginPath();ctx.arc(M[0],M[1],4,0,2*Math.PI);ctx.fill();
      if(c.kind==='median'&&c.vertex>=0)segment(pixel(c.vertex),M);
      ctx.setLineDash([]);ctx.font='bold 13px Arial';ctx.fillText('M',M[0]+8,M[1]-7);
    }else if(c.kind==='perpendicular'){
      const vx=uy/L,vy=-ux/L;
      if(s.type==='triangle'&&c.vertex>=0){
        // The altitude from the opposite vertex falls on the full supporting line.
        const V=pixel(c.vertex);
        const t=((V[0]-A[0])*ux+(V[1]-A[1])*uy)/(L*L);
        const H=[A[0]+t*ux,A[1]+t*uy];
        segment(V,H);
        // right-angle marker at foot; oriented along side and toward vertex
        const side=Math.sign((V[0]-H[0])*vx+(V[1]-H[1])*vy)||1;
        const q=9,ex=ux/L,ey=uy/L;
        ctx.beginPath();ctx.moveTo(H[0]+ex*q,H[1]+ey*q);
        ctx.lineTo(H[0]+ex*q+vx*q*side,H[1]+ey*q+vy*q*side);
        ctx.lineTo(H[0]+vx*q*side,H[1]+vy*q*side);ctx.stroke();
      }else{
        const half=65;
        segment([M[0]-vx*half,M[1]-vy*half],[M[0]+vx*half,M[1]+vy*half]);
        ctx.setLineDash([]);ctx.beginPath();ctx.arc(M[0],M[1],3,0,2*Math.PI);ctx.fill();
      }
    }else if(c.kind==='bisector'&&s.type==='triangle'){
      const V=pixel(c.vertex);
      const others=[0,1,2].filter(i=>i!==c.vertex);
      if(others.length===2){
        const P=pixel(others[0]),Q=pixel(others[1]);
        const lp=Math.hypot(P[0]-V[0],P[1]-V[1]);
        const lq=Math.hypot(Q[0]-V[0],Q[1]-V[1]);
        if(lp>1e-6&&lq>1e-6){
          const t=lp/(lp+lq);
          const D=[P[0]+t*(Q[0]-P[0]),P[1]+t*(Q[1]-P[1])];
          segment(V,D);
        }
      }
    }
    ctx.restore();
  }
}
function drawShape(s,highlight=false){
  const p=s.points;ctx.save();ctx.lineWidth=s.thickness;ctx.strokeStyle=s.color;
  ctx.lineJoin='round';ctx.lineCap='round';
  if(s.type==='circle'){
    ctx.setLineDash((s.lineStyle||'solid')==='dashed'?[9,6]:[]);
    const c=p[0],r=p[1];ctx.beginPath();ctx.arc(c[0]*vw,c[1]*vh,Math.hypot((r[0]-c[0])*vw,(r[1]-c[1])*vh),0,Math.PI*2);ctx.stroke();
  }else{
    edgesFor(s).forEach(([i,j],idx)=>{
      ctx.setLineDash((s.edgeStyles?.[idx]||s.lineStyle||'solid')==='dashed'?[9,6]:[]);
      ctx.beginPath();ctx.moveTo(p[i][0]*vw,p[i][1]*vh);ctx.lineTo(p[j][0]*vw,p[j][1]*vh);ctx.stroke();
    });
  }
  ctx.setLineDash([]);
  constructionDraw(s);
  if(s.type==='vector'||s.type==='doublevector'){
    vectorArrow(p[0],p[1],s.thickness);
    if(s.type==='doublevector')vectorArrow(p[1],p[0],s.thickness);
    vectorCaption(s);
  }
  if(highlight){
    const edges=edgesFor(s);
    if(selectedEdge>=0&&edges[selectedEdge]&&s===shapes[selected]){
      const [i,j]=edges[selectedEdge],mid=[(p[i][0]+p[j][0])*vw/2,(p[i][1]+p[j][1])*vh/2];
      ctx.beginPath();ctx.fillStyle='#fef08a';ctx.strokeStyle='#92400e';ctx.lineWidth=2;
      ctx.arc(mid[0],mid[1],7,0,Math.PI*2);ctx.fill();ctx.stroke();
    }
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
  if(type==='line'||type==='vector'||type==='doublevector')p=[a,b];
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
  return {type,points:p,color,thickness,lineStyle,edgeStyles:{},label:''};
}
const dist=(a,b)=>Math.hypot((a[0]-b[0])*vw,(a[1]-b[1])*vh);
function edgeDistance(pt,a,b){
  const px=pt[0]*vw,py=pt[1]*vh,x=a[0]*vw,y=a[1]*vh;
  const dx=(b[0]-a[0])*vw,dy=(b[1]-a[1])*vh;
  const t=Math.max(0,Math.min(1,((px-x)*dx+(py-y)*dy)/(dx*dx+dy*dy||1)));
  return Math.hypot(px-x-t*dx,py-y-t*dy);
}
function findShape(pt){
  for(let i=shapes.length-1;i>=0;i--){
    for(let j=0;j<shapes[i].points.length;j++)if(dist(pt,shapes[i].points[j])<18)return {i,j,edge:-1};
    const edges=edgesFor(shapes[i]);
    for(let j=0;j<edges.length;j++){const [u,v]=edges[j];if(edgeDistance(pt,shapes[i].points[u],shapes[i].points[v])<13)return {i,j:-1,edge:j};}
    const p=shapes[i].points;
    if(p.length>1){
      const minX=Math.min(...p.map(v=>v[0]))-.02,maxX=Math.max(...p.map(v=>v[0]))+.02;
      const minY=Math.min(...p.map(v=>v[1]))-.02,maxY=Math.max(...p.map(v=>v[1]))+.02;
      if(pt[0]>=minX&&pt[0]<=maxX&&pt[1]>=minY&&pt[1]<=maxY)return {i,j:-1,edge:-1};
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
    const hit=findShape(p);selected=hit?hit.i:-1;selectedEdge=hit?hit.edge:-1;selectedVertex=hit?hit.j:-1;
    drag=hit?{kind:hit.j>=0?'vertex':hit.edge>=0?'edge':'move',j:hit.j,last:p}:null;
    refreshLineStyles();draw();return;
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
    else if(drag.kind==='edge'){/* click selects edge; drag moves whole figure */const dx=p[0]-drag.last[0],dy=p[1]-drag.last[1];target.points=target.points.map(q=>[q[0]+dx,q[1]+dy]);}
    else{const dx=p[0]-drag.last[0],dy=p[1]-drag.last[1];target.points=target.points.map(q=>[q[0]+dx,q[1]+dy]);}
    drag.last=p;draw();return;
  }
  if(drag?.kind==='create'){shapeDraft=geometry(mode,drag.start,p);draw();return;}
  if(stroke){stroke.points.push(p);draw();}
});
function end(e){
  if(e.pointerId!==pointer)return;
  if(stroke){strokes.push(stroke);stroke=null;}
  if(shapeDraft){shapes.push(shapeDraft);selected=shapes.length-1;selectedEdge=-1;selectedVertex=-1;shapeDraft=null;setMode('edit');refreshLineStyles();}
  drag=null;pointer=null;draw();
}
canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);
window.addEventListener('scroll',()=>{if(strokes.length||shapes.length){strokes=[];shapes=[];selected=-1;selectedEdge=-1;selectedVertex=-1;stroke=null;draw();}},{passive:true});
window.addEventListener('resize',resize);
document.addEventListener('keydown',e=>{if(e.key==='Escape')setMode('off');if(/INPUT|TEXTAREA|SELECT/.test(e.target?.tagName||'')||e.target?.isContentEditable)return;if(e.key.toLowerCase()==='p'&&!e.ctrlKey&&!e.altKey)setMode(mode==='pen'?'off':'pen');});
resize();
})();