/* In-place bilingual learning: DOM-only display layer, never edits exam data. */
(function(){
"use strict";
if(window.__ldvlInlineLearningV2)return;
window.__ldvlInlineLearningV2=true;
const KEY="ldvlBilingualStudyMode_v1";
const MAX_ITEMS=12,MAX_CHAR=4800;
const regMarker=/⟦M\d+⟧/g;
let mode="vi", entries=new WeakMap(), active=[], cache=new Map(), busy=false, epoch=0, timer=0;
let frameRequest=null, currentFrame=null;
let touchedQuestion=null,lastQuestionKey="",frameQuestionKey="";
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
   if(node.matches("input,button,select,textarea,script,style,[hidden],.ll-inline-original,.ll-inline-target,.ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview,.solution,#solution,#solbox,.explanation,.answer-key"))return "";
   if(node.isConnected&&!onScreen(node))return "";
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
const CARD=".qcard,.question-card,.exam-question,.quiz-question,.quiz-item,.question-item,.question-block,[data-question-id],[data-question],.question";
const STEMS=".qstem,.question-text,.question-content,.problem-text,.quiz-question-text,[data-question-text],#question";
const ANSWER_PARTS=".opt,.option,.tf-text,label.answer,label.option,#options label,#options .option";
function owningCard(el){
 if(!el||!el.closest)return null;
 const card=el.closest(CARD);
 return card&&onScreen(card)?card:null;
}
function inViewport(el){
 if(!el||!el.getBoundingClientRect)return false;
 const r=el.getBoundingClientRect();
 return r.bottom>56&&r.top<(window.innerHeight||800)-36;
}
function activeCard(){
 if(touchedQuestion&&touchedQuestion.isConnected&&onScreen(touchedQuestion)&&inViewport(touchedQuestion))return touchedQuestion;
 const cards=Array.from(document.querySelectorAll(CARD))
  .filter(el=>onScreen(el) && !el.closest("#ldvl-lang-panel,.ll-inline-original,.ll-inline-target"));
 if(!cards.length)return null;
 const selected=cards.find(el=>el.matches('[aria-current="true"],.current,.active,[data-active="true"]'));
 if(selected)return selected;
 // The visible question nearest the middle of the viewport is the one
 // the learner is currently reading; never translate a whole exam at once.
 const center=window.innerHeight*.45;
 return cards.sort((a,b)=>{
  const ra=a.getBoundingClientRect(),rb=b.getBoundingClientRect();
  const da=Math.abs(Math.max(0,Math.min(center,ra.bottom)-Math.max(center,ra.top)))+
            Math.abs((ra.top+ra.bottom)/2-center)*.08;
  const db=Math.abs(Math.max(0,Math.min(center,rb.bottom)-Math.max(center,rb.top)))+
            Math.abs((rb.top+rb.bottom)/2-center)*.08;
  return da-db;
 })[0];
}
function currentQuestionNodes(){
 const live=document.getElementById("q");
 if(live&&onScreen(live)&&live.querySelector(".qstem")){
  // This container holds exactly one practice/game question.
  const stem=live.querySelector(".qstem");
  const choices=Array.from(live.querySelectorAll(".opt,.tf-text")).filter(el=>!el.closest("#solbox,.solution,.phat"));
  const nodes=[stem,...choices,...live.querySelectorAll("#solbox,.solution")];
  // Never translate hidden answers or unrelated practice navigation.
  return {nodes:nodes.filter(el=>el===stem||onScreen(el)),identity:stem};
 }
 const legacy=document.getElementById("question");
 if(legacy&&onScreen(legacy)){
  const parent=legacy.closest(CARD)||legacy.parentElement;
  const others=parent?Array.from(parent.querySelectorAll(ANSWER_PARTS)):Array.from(document.querySelectorAll("#options .option,#options label"));
  const nodes=[legacy,...others];
  const solution=parent?.querySelector("#solution,.solution,.explanation");
  if(solution&&onScreen(solution))nodes.push(solution);
  return {nodes:nodes.filter(onScreen),identity:legacy};
 }
 const root=activeCard();
 if(!root)return {nodes:[],identity:null};
 let stems=Array.from(root.querySelectorAll(STEMS)).filter(el=>onScreen(el));
 if(!stems.length)stems=[root];
 let choices=Array.from(root.querySelectorAll(ANSWER_PARTS)).filter(onScreen);
 if(!choices.length && root.matches(".qstem,.question-text,.question-content"))choices=[];
 const solution=Array.from(root.querySelectorAll(".solution,.explanation,[data-solution]"))
  .filter(onScreen);
 return {nodes:[...stems,...choices,...solution],identity:stems[0]||root};
}
function contentEntries(){
 const {nodes,identity}=currentQuestionNodes();
 const selected=[],seen=new Set();
 for(const el of nodes){
  if(!el||seen.has(el)||!onScreen(el))continue;
  if(el.closest("nav,.top,.sidebar,#ldvl-lang-panel,.ll-inline-original,.ll-inline-target"))continue;
  let parent=el.parentElement,nested=false;
  while(parent){if(seen.has(parent)){nested=true;break;}parent=parent.parentElement;}
  if(nested)continue;
  const e=prepare(el);
  if(!e)continue;
  selected.push(e);seen.add(el);
 }
 // Only the current question is bilingual; restore the previous question
 // when navigating or scrolling, and reuse cached translations on return.
 for(const old of active){if(!selected.some(e=>e.el===old.el))showEntry(old,"vi");}
 active=selected;
 const stem=selected.find(e=>e.el===identity)||selected[0];
 const nextKey=stem?String(idOf(stem.el))+":"+stem.text:"";
 if(nextKey!==lastQuestionKey){
  lastQuestionKey=nextKey;
  if(window.parent===window)window.dispatchEvent(new CustomEvent("ldvl:current-question-changed",{
    detail:{text:stem?.text||"",marks:stem?.marks||{}}
  }));
 }
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
   // Publish only after every part of this one question is translated.
 });
}
function combinedQuestion(items){
 const marks={},sourceParts=[],englishParts=[];
 let next=0;
 for(const entry of items){
  const ids={};
  const rename=text=>String(text||"").replace(regMarker,m=>{
   if(!ids[m]){
    const newKey="⟦M"+(next++)+"⟧";
    ids[m]=newKey;
    if(entry.marks[m])marks[newKey]=entry.marks[m];
   }
   return ids[m];
  });
  sourceParts.push(rename(entry.text));
  englishParts.push(rename(entry.translated||""));
 }
 return {source:sourceParts.join("\n"),english:englishParts.join("\n"),marks};
}
function publishCurrentTranslation(items){
 if(window.parent!==window || !items.length || items.some(e=>!e.translated))return;
 const data=combinedQuestion(items);
 window.dispatchEvent(new CustomEvent("ldvl:inline-translated",{
  detail:{...data,complete:true}
 }));
}
window.ldvlInlineQuestionData=()=>{
 const items=contentEntries();
 const result=combinedQuestion(items);
 return {text:result.source,marks:result.marks};
};
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
       // Cached parts are assembled and published together below.
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
   publishCurrentTranslation(pending);
   showFinal(done?"Đã dịch "+done+"/"+total+" phần của câu đang xem.":"Không có đoạn phù hợp để dịch.");
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
 epoch++;lastPageFingerprint="";lastQuestionKey="";touchedQuestion=null;frameQuestionKey="";frameDirty=true;
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
 document.addEventListener("pointerdown",e=>{const q=owningCard(e.target);if(q&&q!==touchedQuestion){touchedQuestion=q;if(mode!=="vi")schedule();}},{passive:true});
 window.addEventListener("ldvl:languagechange",e=>changeMode(e.detail?.mode||"vi"));
 const obs=new MutationObserver(records=>{
   if(mode==="vi")return;
   const meaningful=records.some(rec=>{
     if(rec.type==="attributes"){
       // Another question may become active without replacing DOM nodes.
       return rec.target.matches?.(CARD) &&
         !rec.target.matches(".ll-inline-original,.ll-inline-target") &&
         rec.attributeName!=="data-ll-locale";
     }
     if(rec.type!=="childList"||!rec.addedNodes?.length)return false;
     const added=Array.from(rec.addedNodes);
     if(added.every(n=>n.nodeType===1&&n.matches(".ll-inline-original,.ll-inline-target,.ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview")))return false;
     const el=rec.target.nodeType===1?rec.target:rec.target.parentElement;
     return el&&!el.closest("#ldvl-lang-panel,.ll-inline-original,.ll-inline-target,.ll-sol-tools,.ll-sol-quick-play,.ll-sol-preview");
   });
   if(meaningful)schedule();
 });
 obs.observe(document.body,{subtree:true,childList:true,
   attributes:true,attributeFilter:["class","style","hidden","aria-current","data-active"]});
 let scrollCheck=0;
 window.addEventListener("scroll",()=>{
  if(mode==="vi"||document.getElementById("q"))return;
  clearTimeout(scrollCheck);
  scrollCheck=setTimeout(schedule,180);
 },{passive:true});
 document.querySelectorAll("#hpFrame,#hlFrame,#savedFrame").forEach(f=>f.addEventListener("load",()=>{if(mode!=="vi")schedule();}));
 if(mode!=="vi"){showPending("Đang kiểm tra nội dung song ngữ…");schedule();}
}
function startChild(){
 document.addEventListener("pointerdown",e=>{const q=owningCard(e.target);if(q&&q!==touchedQuestion){touchedQuestion=q;frameQuestionKey="";if(localMode!=="vi")window.parent.postMessage({type:"LDVL_INLINE_DIRTY"},hostOrigin);}},{passive:true});
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