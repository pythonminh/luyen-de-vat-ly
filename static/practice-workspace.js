
/* Student visible index: uses server-rendered question statuses.
   It never calculates grades or writes the answer endpoint. */
(function(){
"use strict";
function init(){
 const root=document.querySelector(".vip-practice-wrap>.panel");
 if(!root||root.querySelector(".practice-three-zone"))return;
 const head=root.querySelector(".quiztop");
 const body=root.querySelector(":scope>.body");
 const source=root.querySelector(".practice-questions .pitems");
 if(!body||!source)return;
 const original=[...source.querySelectorAll("a[href^='/practice/jump/']")];
 if(!original.length)return;
 const zone=document.createElement("div");
 zone.className="practice-three-zone";
 const aside=document.createElement("aside");
 aside.className="practice-index-panel";
 aside.setAttribute("aria-label","Mục lục câu hỏi");
 aside.innerHTML='<div class="practice-index-heading"><h2>☷ Mục lục câu hỏi</h2><button type="button" class="practice-index-expand" aria-expanded="false">Xem tất cả</button><strong class="pidx-count" aria-live="polite"></strong></div><div class="practice-index-progress" aria-hidden="true"><span></span></div><nav class="practice-index-grid" aria-label="Chọn câu hỏi"></nav><div class="practice-index-legend"><span><i></i>Chưa làm</span><span class="pidx-wait"><i></i>Đang chọn</span><span class="pidx-ok"><i></i>Đúng</span><span class="pidx-bad"><i></i>Sai</span><span class="pidx-now"><i></i>Đang xem</span></div><div class="practice-index-summary" aria-live="polite"></div>';
 const nav=aside.querySelector(".practice-index-grid");
 const keys=[];
 original.forEach((a,index)=>{
   const clone=a.cloneNode(true);
   clone.classList.add("pidx-link");
   const href=a.getAttribute("href")||"";
   const pos=+(href.split("/").pop());
   clone.dataset.questionIndex=String(Number.isFinite(pos)?pos:index);
   clone.textContent="Câu "+(index+1);
   clone.title=clone.textContent+" · "+(a.classList.contains("pdone")?"Đã làm đúng":a.classList.contains("pwrong")?"Đã làm sai":"Chưa làm");
   if(clone.classList.contains("pcur"))clone.setAttribute("aria-current","step");
   nav.appendChild(clone);keys.push({src:a,view:clone});
 });
 root.insertBefore(zone,body);
 zone.appendChild(aside);
 zone.appendChild(body);
 function refresh(){
   const links=keys.map(x=>x.view);
   const done=links.filter(x=>x.classList.contains("pdone")||x.classList.contains("pwrong")).length;
   const correct=links.filter(x=>x.classList.contains("pdone")).length;
   const count=aside.querySelector(".pidx-count");
   count.textContent=done+"/"+links.length+" đã làm";
   aside.querySelector(".practice-index-progress>span").style.width=(100*done/links.length).toFixed(1)+"%";
   aside.querySelector(".practice-index-summary").textContent="Đúng "+correct+" · Sai "+(done-correct)+" · Chưa làm "+(links.length-done);
 }
 function markCurrentPending(ready){
   const cur=keys.find(x=>x.view.classList.contains("pcur"));
   if(cur&&!cur.view.classList.contains("pdone")&&!cur.view.classList.contains("pwrong")){
     cur.view.classList.toggle("pready",!!ready);
     cur.src.classList.toggle("pready",!!ready);
   }
 }
 function getReady(){
   const q=document.getElementById("q");
   if(!q)return false;
   const type=window.practiceKind||"";
   if(type==="TN")return !!q.querySelector('input[name="a"]:checked');
   if(type==="DS"){
     const names=[...new Set([...q.querySelectorAll(".tf input[type=radio]")].map(x=>x.name))];
     return !!names.length&&names.every(n=>!!q.querySelector('input[name="'+n+'"]:checked'));
   }
   const input=q.querySelector("#ans");
   return !!(input&&input.value.trim());
 }
 const q=document.getElementById("q");
 if(q){
   q.addEventListener("change",()=>markCurrentPending(getReady()));
   q.addEventListener("input",()=>markCurrentPending(getReady()));
 }
 window.practiceMarkAnswered=function(ok){
   const cur=keys.find(x=>x.view.classList.contains("pcur"));
   if(!cur)return;
   [cur.src,cur.view].forEach(a=>{
     a.classList.remove("pready","pdone","pwrong");
     a.classList.add(ok?"pdone":"pwrong");
     a.title="Câu đã "+(ok?"đúng":"sai");
   });
   refresh();
 };
 const expand=aside.querySelector(".practice-index-expand");
 expand.addEventListener("click",()=>{
   const isOpen=aside.dataset.expanded==="true";
   aside.dataset.expanded=isOpen?"false":"true";
   expand.textContent=isOpen?"Xem tất cả":"Thu gọn";
   expand.setAttribute("aria-expanded",isOpen?"false":"true");
 });
 // Existing bottom-bar "Mục lục" button now opens the visible inline index.
 const phoneBtn=document.getElementById("phoneQuestionMenu");
 if(phoneBtn){
  phoneBtn.addEventListener("click",function(event){
   event.stopImmediatePropagation();
   aside.dataset.expanded="true";
   expand.textContent="Thu gọn";expand.setAttribute("aria-expanded","true");
   aside.scrollIntoView({behavior:"smooth",block:"start"});
  },true);
 }
 // Move the compact status bar above both columns and preserve elapsed timer.
 const stats=root.querySelector(":scope>.practice-mini-stats");
 if(stats && head)head.insertAdjacentElement("afterend",stats);
 refresh();
 const onCurrent=keys.find(x=>x.view.classList.contains("pcur"));
 if(onCurrent && window.matchMedia("(max-width:1024px)").matches){
   // Keep active question discoverable even when many questions are present.
   const grid=aside.querySelector(".practice-index-grid");
   if(grid && onCurrent.view.offsetTop>grid.clientHeight){
     grid.scrollTop=Math.max(0,onCurrent.view.offsetTop-grid.offsetTop-grid.clientHeight/2);
   }
 }
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);
else init();
})();
