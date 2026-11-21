/* In-place bilingual learning: DOM-only display layer, never edits exam data. */
(function(){
"use strict";
if(window.__ldvlInlineLearningV2)return;
window.__ldvlInlineLearningV2=true;
const KEY="ldvlBilingualStudyMode_v1";
const MAX_ITEMS=10,MAX_CHAR=2600;
const regMarker=/⟦M\d+⟧/g;
let mode="vi", entries=new WeakMap(), active=[], cache=new Map(), busy=false, epoch=0, timer=0;
let frameRequest=null, currentFrame=null;
let statusWatchdog=0;
function showFinal(message,error=false){
 clearTimeout(statusWatchdog);statusWatchdog=0;status(message,error);
}
function showPending(message){
 showFinal(message);
 statusWatchdog=setTimeout(()=>{
  const el=document.getElementById("ll-status");
  if(el&&/Đang (kiểm tra|chuyển|dịch)/.test(el.textContent||"")){
   showFinal("Dịch chưa hoàn thành. Vẫn có thể làm bài và chơi game; hãy thử Dịch câu hỏi hoặc trở về Tiếng Việt.",true);
  }
 },16000);
}
let requestPausedUntil=0, pauseReason="",lastPageFingerprint="",frameDirty=true;
const elementIds=new WeakMap();let nextElementId=1;
function idOf(el){if(!elementIds.has(el))elementIds.set(el,nextElementId++);return elementIds.get(el);}
try{const m=localStorage.getItem(KEY);if(["vi","en","both"].includes(m))mode=m;}catch(e){}
function textValue(v){return String(v||"").replace(/\s+/g," ").trim();}
function onScreen(el){if(!el||!el.isConnected||!el.getClientRects().length)return false;const s=getComputedStyle(el);return s.display!=="none"&&s.visibility!=="hidden";}
function status(t,error){
 const el=document.getElementById("ll-status");
 if(el){el.textContent=t;el.className="ll-status "+(error?"error":"ok");}
}
function protectNodes(nodes){
 let counter=0, marks={};
 function walk(node){
   if(node.nodeType===3)return node.nodeValue||"";
   if(node.nodeType!==1)return "";
   if(node.matches("input,button,select,textarea,script,style,[hidden],.ll-inline-original,.ll-inline-target,.ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview"))return "";
   if(node.matches("mjx-container,.MathJax,.katex,math,svg,img,canvas,iframe,video,.tikzfig,.tikz-row,.immini,.tex-table")){
     const marker="⟦M"+counter+++"⟧";
     marks[marker]=node.cloneNode(true);
     return marker;
   }
   if(node.tagName==="BR")return "\n";
   const str=Array.from(node.childNodes).map(walk).join("");
   return /^(DIV|P|LI|H[1-6]|TR|SECTION|ARTICLE)$/.test(node.tagName)?"\n"+str+"\n":str;
 }
 const raw=nodes.map(walk).join("");
 return {text:raw.replace(/[ \t]{2,}/g," ").replace(/\n{3,}/g,"\n\n").trim(),marks};
}
function renderWords(dest,words,marks){
 dest.replaceChildren();
 const re=new RegExp(regMarker.source,"g");
 let last=0,m;
 while((m=re.exec(words))){
   if(m.index>last)dest.appendChild(document.createTextNode(words.slice(last,m.index)));
   dest.appendChild(marks[m[0]]?marks[m[0]].cloneNode(true):document.createTextNode(m[0]));
   last=re.lastIndex;
 }
 if(last<words.length)dest.appendChild(document.createTextNode(words.slice(last)));
 try{if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise([dest]).catch(()=>{});}catch(e){}
}
function prepare(el){
 if(!onScreen(el))return null;
 if(window.ldvlMathSpeech?.prepareElement)window.ldvlMathSpeech.prepareElement(el);
 let prev=entries.get(el);
 if(prev)return prev;
 if(el.closest(".ll-inline-original,.ll-inline-target,#ldvl-lang-panel,.ll-no-translate"))return null;
 const protectedPart=el.matches("label.opt,label.option,.opt,.option");
 const skip=protectedPart?Array.from(el.children).filter(n=>n.matches('input,.tflab,.answer-label')):[];
 let nodes=Array.from(el.childNodes).filter(n=>!skip.includes(n)&&!(n.nodeType===1&&n.matches(".ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview")));
 if(!nodes.length)return null;
 const result=protectNodes(nodes);
 if(!result.text||result.text.length>3200)return null;
 if(!/[\p{L}]/u.test(result.text))return null;
 const original=document.createElement("span");
 original.className="ll-inline-original";
 const target=document.createElement("span");
 target.className="ll-inline-target";
 target.hidden=true;
 nodes.forEach(n=>original.appendChild(n));
 el.append(original,target);
 prev={el,original,target,text:result.text,marks:result.marks,translated:null,lang:null};
 entries.set(el,prev);
 return prev;
}
function selectors(){
 if(document.querySelector("#q .qstem")){
   return "#q .qstem,#q .opt,#q .tf-text,#q .qdang,#q .nguon,#q .solution,#q #solbox,#q .hintline,.quiztop .quizdang";
 }
 if(document.querySelector("#question")){
   return "#question,#options .option,#options label,#solution,.formula";
 }
 return "main h1,main h2,main h3,main p,main li,main summary,main .head,.wrap h1,.wrap h2,.wrap h3,.wrap .panel>.head,.wrap .body>p,.wrap .body>li,.wrap .qstem,.wrap .tf-text,.wrap .opt,.question-text,.question-content,.question,.qstem";
}
function contentEntries(){
 const nodes=Array.from(document.querySelectorAll(selectors()));
 const selected=[], seen=new Set();
 for(const el of nodes){
   if(seen.has(el)||el.closest("#ldvl-lang-panel"))continue;
   if(el.closest("nav,.top,.sidebar,.ll-inline-original,.ll-inline-target"))continue;
   if(el.matches("article")&&el.querySelector("h1,h2,h3,p"))continue;
   let ancestor=el.parentElement;
   let nested=false;
   while(ancestor){
     if(seen.has(ancestor)){nested=true;break;}
     ancestor=ancestor.parentElement;
   }
   if(nested)continue;
   const e=prepare(el);
   if(!e)continue;
   selected.push(e);seen.add(el);
   if(selected.length>=70)break;
 }
 active=selected;
 return selected;
}
function showEntry(e,currentMode){
 if(!e||!e.el.isConnected)return;
 if(currentMode==="vi"||!e.translated){
   e.original.hidden=false;e.target.hidden=true;
   e.el.classList.remove("ll-inline-both");
   e.el.removeAttribute("data-ll-locale");
   return;
 }
 e.original.hidden=currentMode==="en";
 e.target.hidden=false;
 e.el.classList.toggle("ll-inline-both",currentMode==="both");
 e.el.setAttribute("data-ll-locale",currentMode);
}
function setTranslations(items,values,lang,desired){
 items.forEach((entry,i)=>{
   if(!entry.el.isConnected)return;
   const translated=values[i];
   if(typeof translated!=="string"||!translated.trim())return;
   entry.translated=translated;
   entry.lang=lang;
   renderWords(entry.target,translated,entry.marks);
   showEntry(entry,desired);
   if(window.parent===window && entry.el.matches(".qstem,#question,.question-text,.question-content")){
     window.dispatchEvent(new CustomEvent("ldvl:inline-translated",{
       detail:{source:entry.text,english:translated,marks:entry.marks}
     }));
   }
 });
}
function keySource(){try{
 if(typeof window.ldvlGetGeminiKeys==="function")return window.ldvlGetGeminiKeys().filter(k=>typeof k==="string"&&k.length>=20).slice(0,3);
 }catch(e){}
 return [];
}
async function translateBatch(strings,target){
 if(Date.now()<requestPausedUntil)throw new Error(pauseReason||"Dịch tự động đang tạm dừng.");
 let res;
 try{
   res=await fetch("/api/learning/translate-batch",{
     method:"POST",credentials:"same-origin",
     headers:{"Content-Type":"application/json"},
     body:JSON.stringify({texts:strings,target,api_keys:keySource()})
   });
 }catch(e){
   requestPausedUntil=Date.now()+20000;
   pauseReason="Không kết nối được dịch vụ dịch. Hãy thử lại sau.";
   throw e;
 }
 let body={};
 try{body=await res.json()}catch(e){}
 if(!res.ok||!body.ok||!Array.isArray(body.translations)||body.translations.length!==strings.length){
   const msg=body.error||"Không thể dịch đoạn này.";
   if(res.status===429){
     requestPausedUntil=Date.now()+65000;
     pauseReason="Dịch tự động đang tạm nghỉ 65 giây do quá nhiều yêu cầu.";
   }else if(res.status>=500){
     requestPausedUntil=Date.now()+30000;
     pauseReason="Gemini tạm thời lỗi. Dịch tự động nghỉ 30 giây.";
   }else if(res.status===401||res.status===403||res.status===409){
     requestPausedUntil=Date.now()+30000;
     pauseReason=msg;
   }
   throw new Error(pauseReason||msg);
 }
 requestPausedUntil=0;pauseReason="";
 return body.translations;
}
async function translateEntries(items,currentMode,revision){
 const dest="en";
 let pending=items.filter(e=>e.el.isConnected);
 if(!pending.length){if(revision===epoch)showFinal("Không có nội dung cần dịch.");return;}
 const total=pending.length;
 let idx=0,done=0;
 while(idx<total && revision===epoch && mode===currentMode){
   const group=[], names=[];
   let count=0;
   for(;idx<total && group.length<MAX_ITEMS;idx++){
     const e=pending[idx];
     const k=dest+"\0"+e.text;
     if(cache.has(k)){
       e.translated=cache.get(k);e.lang=dest;
       renderWords(e.target,e.translated,e.marks);
       showEntry(e,currentMode);
       if(window.parent===window && e.el.matches(".qstem,#question,.question-text,.question-content")){
         window.dispatchEvent(new CustomEvent("ldvl:inline-translated",{
           detail:{source:e.text,english:e.translated,marks:e.marks}
         }));
       }
       done++;
       continue;
     }
     if(group.length && count+e.text.length>MAX_CHAR)break;
     if(e.text.length>MAX_CHAR)continue;
     group.push(e);names.push(e.text);count+=e.text.length;
   }
   if(!group.length)continue;
   showPending("Đang dịch "+Math.min(idx,total)+"/"+total+" đoạn bài học…");
   try{
     const translated=await translateBatch(names,dest);
     translated.forEach((v,j)=>cache.set(dest+"\0"+names[j],v));
     if(revision!==epoch||mode!==currentMode)return;
     setTranslations(group,translated,dest,currentMode);
     done+=group.length;
     showFinal("Đã dịch "+done+"/"+total+" đoạn. Công thức và đáp án được giữ nguyên.");
   }catch(err){
     if(revision===epoch){
       showFinal((err&&err.message)||"Lỗi dịch trang.",true);
     }
     return;
   }
 }
 if(revision===epoch&&mode===currentMode){
   showFinal(done?"Đã dịch "+done+"/"+total+" đoạn trên trang.":"Không có đoạn phù hợp để dịch.");
 }
}
const UI={
 "Đổi đề bài mới":"New question","Xác nhận":"Submit answer","Kiểm tra":"Check",
 "Xem lời giải":"Show solution","Lời giải":"Solution","Gợi ý đáp án":"Answer hint",
 "Câu tiếp":"Next question","Tiếp theo":"Next","Quay lại":"Back","Mục lục":"Lessons",
 "Bài học":"Lessons","Chọn bài":"Choose lesson","Bài":"Lesson","Đúng":"True",
 "Sai":"False","Trắc nghiệm":"Multiple choice","Trả lời ngắn":"Short answer",
 "Tự luận":"Written response","Đúng sai":"True / False","Chọn đáp án":"Select an answer",
 "Kiểm tra kết quả":"Check result","Làm bài":"Start practice","Bắt đầu làm bài":"Start practice",
 "Xem như học sinh":"Student view","Kết quả":"Results","Đáp án":"Answer",
 "Bài luyện tập":"Practice","Đổi số":"New numbers","Toàn màn hình":"Fullscreen",
 "Thu nhỏ":"Minimize","Mở rộng bài":"Expand","Lý thuyết":"Theory",
 "Phương pháp":"Method","Xem lại":"Review","Mở luyện tập":"Open practice",
 "Đang học":"Learning","Đã hoàn thành":"Completed","Chương":"Chapter",
 "Dạng bài":"Problem type","Khối lớp":"Grade","Bài tập":"Exercises",
 "Gửi bài":"Submit","Nộp bài":"Submit"
};
function changeUI(){
 const elements=document.querySelectorAll("button,.nav a,.top a,summary,.quizacts a,.quizacts button,#q .tf-h,.head .tag");
 for(const el of elements){
   if(el.closest("#ldvl-lang-panel"))continue;
   for(const node of Array.from(el.childNodes)){
     if(node.nodeType!==3)continue;
     if(node.__llOriginal===undefined)node.__llOriginal=node.nodeValue;
     if(mode==="vi"){node.nodeValue=node.__llOriginal;continue;}
     const original=node.__llOriginal;
     const pure=original.trim().replace(/^[^A-Za-zÀ-ỹ0-9]+/u,"").trim();
     const translated=UI[pure];
     if(!translated)continue;
     const prefix=original.indexOf(pure)>=0?original.slice(0,original.indexOf(pure)):"";
     node.nodeValue=prefix+translated;
   }
 }
}
function resetAll(){
 epoch++;lastPageFingerprint="";frameDirty=true;
 for(const e of active)showEntry(e,"vi");
 changeUI();
 currentFrame=document.querySelector("#hpFrame,#hlFrame,#savedFrame");
 if(currentFrame&&currentFrame.contentWindow)
   currentFrame.contentWindow.postMessage({type:"LDVL_INLINE_RESET"},"*");
 showFinal("Đã trở lại trang tiếng Việt.");
}
function eligibleFrame(){
 return Array.from(document.querySelectorAll("#hpFrame,#hlFrame,#savedFrame"))
   .find(f=>f.getClientRects().length&&f.contentWindow)||null;
}
function captureFrame(revision){
 const frame=eligibleFrame();
 if(!frame)return;
 currentFrame=frame;
 const nonce="c"+Math.random().toString(36).slice(2);
 frameRequest={frame,nonce,revision};
 frame.contentWindow.postMessage({type:"LDVL_INLINE_CAPTURE",nonce},"*");
 setTimeout(()=>{
   if(frameRequest&&frameRequest.nonce===nonce){
     frameRequest=null;
     showFinal("Không lấy được nội dung bài HTML trong khung. Có thể mở bài ở tab riêng.",true);
   }
 },2800);
}
async function applyFrameData(frame,texts,nonce,revision){
 if(mode==="vi"||revision!==epoch)return;
 const data=Array.isArray(texts)?texts.slice(0,24):[];
 if(!data.length)return;
 const values=[],toTranslate=[],positions=[];
 for(let i=0;i<data.length;i++){
   const source=String(data[i]||"").trim();
   const k="en\0"+source;
   if(cache.has(k))values[i]=cache.get(k);
   else if(source){toTranslate.push(source);positions.push(i);}
 }
 try{
   if(toTranslate.length){
     let offset=0;
     while(offset<toTranslate.length){
       const batch=[],bp=[];let size=0;
       while(offset<toTranslate.length&&batch.length<MAX_ITEMS){
         const s=toTranslate[offset];if(batch.length&&size+s.length>MAX_CHAR)break;
         if(s.length>MAX_CHAR){offset++;continue;}
         batch.push(s);bp.push(positions[offset]);offset++;size+=s.length;
       }
       if(!batch.length)continue;
       const out=await translateBatch(batch,"en");
       for(let j=0;j<batch.length;j++){
         values[bp[j]]=out[j];cache.set("en\0"+batch[j],out[j]);
       }
     }
   }
   if(revision!==epoch||mode==="vi")return;
   frame.contentWindow.postMessage({type:"LDVL_INLINE_APPLY",nonce,values,mode},"*");
   showFinal("Đã dịch xong bài HTML trong khung.");
 }catch(e){if(revision===epoch)showFinal((e&&e.message)||"Không dịch được bài HTML.",true);}
}
window.addEventListener("message",event=>{
 const data=event.data||{};
 if(data.type==="LDVL_INLINE_CAPTURED"){
   if(!frameRequest||event.source!==frameRequest.frame.contentWindow||data.nonce!==frameRequest.nonce)return;
   const req=frameRequest;frameRequest=null;
   applyFrameData(req.frame,data.texts,req.nonce,req.revision);
 }else if(data.type==="LDVL_INLINE_DIRTY"){
   const frame=eligibleFrame();
   if(event.source===frame?.contentWindow&&mode!=="vi"){frameDirty=true;schedule();}
 }
});
function schedule(){
 clearTimeout(timer);
 timer=setTimeout(()=>{
  if(mode==="vi")return;
  try{
   changeUI();
   const path=location.pathname||"";
   if(/^\/member(?:\/game)?\/?$/.test(path)||
      /^\/member\/(?:html-menu|profile|settings|results)(?:\/|$)/.test(path)){
    lastPageFingerprint=mode+"|menu";frameDirty=false;
    showFinal("Đã chuyển nhãn giao diện. Hãy mở bài học để dịch nội dung; game vẫn hoạt động.");
    return;
   }
   const items=contentEntries();
   const fingerprint=mode+"|"+items.map(e=>idOf(e.el)+":"+e.text).join("␟");
   if(fingerprint===lastPageFingerprint&&!frameDirty){
    if(!items.length)showFinal("Trang hiện không có đoạn bài học cần dịch.");
    return;
   }
   lastPageFingerprint=fingerprint;
   const rev=++epoch;
   if(Date.now()<requestPausedUntil)showFinal(pauseReason||"Dịch tự động đang tạm dừng.",true);
   else if(items.length)translateEntries(items,mode,rev).catch(e=>{
    if(rev===epoch)showFinal("Lỗi dịch nội dung: "+(e?.message||"không xác định"),true);
   });
   if(frameDirty){frameDirty=false;captureFrame(rev);}
   if(!items.length&&!eligibleFrame()&&Date.now()>=requestPausedUntil)
    showFinal("Không có nội dung cần dịch tại đây. Hãy mở một câu hỏi và bấm Dịch câu hỏi.");
  }catch(e){showFinal("Không chuyển được trang: "+(e?.message||"lỗi hiển thị"),true);}
 },650);
}
function changeMode(next){
 if(!["vi","en","both"].includes(next))return;
 if(mode===next)return;
 mode=next;lastPageFingerprint="";frameDirty=true;
 if(mode==="vi"){clearTimeout(timer);resetAll();return;}
 showPending("Đang tìm nội dung để dịch…");
 schedule();
}
function startParent(){
 window.ldvlInlineSwitch=true;
 window.addEventListener("ldvl:languagechange",e=>changeMode(e.detail?.mode||"vi"));
 const obs=new MutationObserver(records=>{
   if(mode==="vi")return;
   const meaningful=records.some(rec=>{
     if(rec.type!=="childList"||!rec.addedNodes?.length)return false;
     const added=Array.from(rec.addedNodes);
     if(added.every(n=>n.nodeType===1&&n.matches(".ll-inline-original,.ll-inline-target,.ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview")))return false;
     const el=rec.target.nodeType===1?rec.target:rec.target.parentElement;
     return el&&!el.closest("#ldvl-lang-panel,.ll-inline-original,.ll-inline-target,.ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview");
   });
   if(meaningful)schedule();
 });
 obs.observe(document.body,{subtree:true,childList:true});
 document.querySelectorAll("#hpFrame,#hlFrame,#savedFrame").forEach(f=>f.addEventListener("load",()=>{if(mode!=="vi")schedule();}));
 if(mode!=="vi"){showPending("Đang kiểm tra nội dung song ngữ…");schedule();}
}
function startChild(){
 const hostOrigin=(()=>{try{return new URL(document.baseURI).origin;}catch(e){return "";}})();
 let localMode="vi", lastCapture=[];
 let defer=0;
 const observer=new MutationObserver(records=>{
   if(localMode==="vi")return;
   if(!records.some(r=>{
     if(!r.addedNodes?.length)return false;
     if(Array.from(r.addedNodes).every(n=>n.nodeType===1&&n.matches(".ll-inline-original,.ll-inline-target,.ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview")))return false;
     const el=r.target.nodeType===1?r.target:r.target.parentElement;
     return el&&!el.closest(".ll-inline-original,.ll-inline-target,.ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview");
   }))return;
   clearTimeout(defer);
   defer=setTimeout(()=>{window.parent.postMessage({type:"LDVL_INLINE_DIRTY"},hostOrigin);},550);
 });
 function capture(){
   lastCapture=contentEntries().slice(0,24);
   return lastCapture.map(e=>e.text);
 }
 window.addEventListener("message",e=>{
   if(e.source!==window.parent || !hostOrigin||e.origin!==hostOrigin)return;
   const d=e.data||{};
   if(d.type==="LDVL_INLINE_CAPTURE"){
     localMode="en";
     const texts=capture();
     window.parent.postMessage({type:"LDVL_INLINE_CAPTURED",nonce:d.nonce,texts},hostOrigin);
   }else if(d.type==="LDVL_INLINE_APPLY"){
     localMode=d.mode==="both"?"both":"en";
     if(!Array.isArray(d.values))return;
     setTranslations(lastCapture,d.values,"en",localMode);
   }else if(d.type==="LDVL_INLINE_RESET"){
     localMode="vi";
     for(const item of lastCapture)showEntry(item,"vi");
     lastCapture=[];
   }
 });
 observer.observe(document.documentElement,{childList:true,subtree:true});
}
function boot(){
 if(window.parent!==window){startChild();return;}
 startParent();
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});
else boot();
})();