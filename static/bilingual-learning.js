/* Song ngữ Việt–Anh cho trang học. Không thay đổi đề, đáp án hoặc chấm điểm. */
(() => {
  "use strict";
  // Saved HTML exercises run in sandboxed iframes. They never receive
  // credentials or Gemini keys; only the parent may call the translation API.
  if (window.parent !== window) {
    let selectedText="";
    document.addEventListener("selectionchange",()=>{
      try{const s=window.getSelection();if(s&&!s.isCollapsed)selectedText=String(s).trim().slice(0,5200);}catch(e){}
    });
    function frameText(which){
      try{
        if(which==="selection")return selectedText;
        let stem=document.querySelector("#q .qstem, .qstem, #question, .question-text, .question, .problem-text, .quiz-question");
        if(!stem)stem=document.querySelector("main")||document.body;
        const copy=stem.cloneNode(true);
        copy.querySelectorAll("script,style,button,input,textarea,select,[hidden],.solution,#solution,#solbox,.answer-key").forEach(n=>n.remove());
        let parts=[String(copy.textContent||"").trim()];
        if(stem.matches(".qstem")){
          document.querySelectorAll("#q .opt").forEach((o,i)=>{
            const clone=o.cloneNode(true);
            clone.querySelectorAll("input,.tflab").forEach(n=>n.remove());
            parts.push("ABCD".charAt(i)+". "+String(clone.textContent||"").trim());
          });
        }
        return parts.filter(Boolean).join("\n").slice(0,5200);
      }catch(e){return "";}
    }
    window.addEventListener("message",event=>{
      const data=event.data||{};
      if(event.source!==window.parent || data.type!=="LDVL_STUDY_REQ")return;
      // Accept only messages from the hosting site; never share lesson text
      // with a cross-site parent that embedded a logged-in page.
      let ownOrigin="";
      try{ownOrigin=new URL(document.baseURI).origin;}catch(e){}
      if(!ownOrigin || ownOrigin==="null" || event.origin!==ownOrigin)return;
      const text=frameText(data.which);
      window.parent.postMessage({type:"LDVL_STUDY_REPLY",nonce:data.nonce,text},ownOrigin);
    });
    return;
  }
  if (window.__ldvlBilingualMounted) return;
  window.__ldvlBilingualMounted = true;
  const STORAGE = "ldvlBilingualStudyMode_v1";
  const T = {
    vi: {name:"🇻🇳 Tiếng Việt",label:"Tiếng Việt", target:"vi"},
    en: {name:"🇬🇧 English",label:"English", target:"en"},
    both: {name:"📚 Song ngữ",label:"Song ngữ", target:"en"}
  };
  let mode = "vi";
  try { const saved=localStorage.getItem(STORAGE); if(T[saved]) mode=saved; } catch(e) {}
  let opened=false, savedSelection="", activeJob=0, lastSignature="", lastResult="", resultLanguage="en", observedQuestion=null;
  let lastOutput=null;
  let pendingFrame=null;
  const cache = new Map();
  const $ = id => document.getElementById(id);
  const tokenRE = /⟦(?:M|IMG)\d+⟧/g;
  const escapeID = n => "⟦M" + n + "⟧";
  const clean = v => String(v||"").replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g,"").trim();

  function toast(s, error=false) {
    const el=$("ll-status"); if(!el) return;
    el.textContent=s; el.className="ll-status "+(error?"error":"ok");
  }
  function setOutput(source,translated,marks,target) {
    const parent=$("ll-output"), original=$("ll-original"), out=$("ll-translated");
    if(!parent||!original||!out) return;
    parent.hidden=false;
    const showBoth=mode==="both";
    original.hidden=!showBoth;
    if(showBoth) fill(original,source,marks);
    fill(out,translated,marks);
    $("ll-target-label").textContent=target==="en"?"ENGLISH TRANSLATION":"BẢN DỊCH TIẾNG VIỆT";
    $("ll-speak").disabled=!clean(translated);
    $("ll-copy").disabled=!clean(translated);
    lastResult=translated;resultLanguage=target;
  }
  function fill(container,txt,marks) {
    container.replaceChildren();
    let last=0,m;
    const re=new RegExp(tokenRE.source,"g");
    while((m=re.exec(txt))!==null){
      if(m.index>last) container.appendChild(document.createTextNode(txt.slice(last,m.index)));
      const saved=marks[m[0]];
      container.appendChild(saved?saved.cloneNode(true):document.createTextNode(m[0]));
      last=re.lastIndex;
    }
    if(last<txt.length) container.appendChild(document.createTextNode(txt.slice(last)));
  }
  function plainNode(el,marks,indexObj) {
    const cloned=el.cloneNode(true);
    cloned.querySelectorAll("input, textarea, button, select, script, style, .ll-no-translate").forEach(n=>n.remove());
    const imgs=Array.from(cloned.querySelectorAll("mjx-container, .MathJax, .katex, .tikzfig, img, svg, canvas"));
    for(const n of imgs){
      if(!cloned.contains(n)) continue;
      const marker=escapeID(indexObj.i++);
      marks[marker]=n.cloneNode(true);
      n.replaceWith(document.createTextNode(marker));
    }
    return clean(cloned.textContent).replace(/[ \t]+/g," ");
  }
  function questionData(){
    const marks={},indexObj={i:0},rows=[];
    const quiz=document.getElementById("q");
    if(quiz&&quiz.querySelector(".qstem")){
      rows.push(plainNode(quiz.querySelector(".qstem"),marks,indexObj));
      const opts=quiz.querySelectorAll(".opt");
      if(opts.length){
        opts.forEach((opt,i)=>{
          const clone=opt.cloneNode(true);
          const badge=clone.querySelector(".tflab");
          if(badge) badge.remove();
          rows.push("ABCD".charAt(i)+". "+plainNode(clone,marks,indexObj));
        });
      }else{
        quiz.querySelectorAll(".tf-text").forEach((el,i)=>
          rows.push("ABCD".charAt(i)+". "+plainNode(el,marks,indexObj)));
      }
      return {text:clean(rows.filter(Boolean).join("\n")),marks};
    }
    const candidates=[
      "#question",".question-text",".question-content",".problem-text",
      ".quiz-question",".qstem","[data-question]",".question"
    ];
    let node=null;
    // On multi-question pages use the last question the learner touched.
    if(lastOutput && lastOutput.isConnected){
      const root=lastOutput.closest(".question,.qcard,.quiz-question,.exam-question,.question-card");
      if(root) node=root.querySelector(".qstem,.question-text,.question-content")||root;
    }
    if(!node) for(const selector of candidates){
      const el=document.querySelector(selector);
      if(el && el.getClientRects().length){node=el;break;}
    }
    if(!node) return {text:"",marks};
    return {text:plainNode(node,marks,indexObj),marks};
  }
  function readSelection(){
    const selection=window.getSelection();
    if(!selection||selection.isCollapsed) return "";
    if(selection.anchorNode && $("ldvl-lang-panel") && $("ldvl-lang-panel").contains(selection.anchorNode)) return "";
    return clean(selection.toString());
  }
  function updateSavedSelection(){
    const text=readSelection();
    if(text && text.length<=5500) savedSelection=text;
  }
  function chosenLanguage(text){
    if(mode==="vi") return "vi";
    if(mode==="en") return "en";
    // "Both" aims to show the opposite language beside the original.
    const hasVietnamese=/[ăâđêôơưĂÂĐÊÔƠƯ\u0300-\u036fàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]/i.test(text);
    return hasVietnamese?"en":"vi";
  }
  function keys(){
    try{
      if(typeof window.ldvlGetGeminiKeys==="function"){
        return window.ldvlGetGeminiKeys().filter(k=>typeof k==="string"&&k.length>=20).slice(0,3);
      }
    }catch(e){}
    return [];
  }
  async function runTranslation(data) {
    const text=data.text, marks=data.marks||{};
    if(!text){toast("Hãy mở một câu hỏi hoặc bôi đen đoạn muốn dịch.",true);return;}
    if(text.length>5300){toast("Đoạn quá dài. Hãy bôi đen phần ngắn hơn (tối đa 5.300 ký tự).",true);return;}
    const target=chosenLanguage(text);
    const key=target+"\0"+text;
    activeJob++;
    const job=activeJob;
    lastOutput=null;
    const button=$("ll-translate"),selectionButton=$("ll-selection");
    button.disabled=selectionButton.disabled=true;
    toast(target==="en"?"Đang dịch sang tiếng Anh…":"Đang dịch sang tiếng Việt…");
    $("ll-output").hidden=true;
    let result=cache.get(key);
    try{
      if(!result){
        const resp=await fetch("/api/learning/translate",{
          method:"POST",credentials:"same-origin",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({text,target,api_keys:keys()})
        });
        const body=await resp.json();
        if(!resp.ok||!body.ok)throw new Error(body.error||"Không thể dịch bài này.");
        result=body.translated;
        if(cache.size>=50)cache.delete(cache.keys().next().value);
        cache.set(key,result);
      }
      if(job!==activeJob)return;
      setOutput(text,result,marks,target);
      toast("Đã dịch. Công thức và số liệu được giữ nguyên; hãy đối chiếu với đề gốc.");
    }catch(e){
      if(job!==activeJob)return;
      toast((e&&e.message)||"Có lỗi khi dịch.",true);
    }finally{
      if(job===activeJob){
        button.disabled=selectionButton.disabled=false;
      }
    }
  }
  function translateQuestion(){
    const data=questionData();
    if(!data.text && requestFromFrame("question")) return;
    lastSignature=data.text;
    runTranslation(data);
  }
  function translateSelection(){
    const txt=readSelection()||savedSelection;
    if(!txt){if(requestFromFrame("selection"))return;toast("Bôi đen câu hoặc đoạn văn bằng chuột/ngón tay, rồi bấm nút này.",true);return;}
    runTranslation({text:txt,marks:{}});
  }
  function requestFromFrame(which){
    const frame=Array.from(document.querySelectorAll("#hpFrame,#hlFrame,#savedFrame"))
      .find(f=>f.getClientRects().length && f.contentWindow);
    if(!frame)return false;
    const nonce=Math.random().toString(36).slice(2)+Date.now().toString(36);
    pendingFrame={nonce,frame,created:Date.now()};
    frame.contentWindow.postMessage({type:"LDVL_STUDY_REQ",which,nonce},"*");
    toast("Đang đọc nội dung bài HTML…");
    setTimeout(()=>{
      if(pendingFrame&&pendingFrame.nonce===nonce){
        pendingFrame=null;
        toast("Chưa đọc được bài HTML. Hãy mở bài riêng hoặc bôi đen phần văn bản trên trang.",true);
      }
    },2200);
    return true;
  }
  function installFrameBridge(){
    const script='<script src="'+location.origin+'/static/bilingual-learning.js?v=20261116b"><\/script>'+
      '<script src="'+location.origin+'/static/bilingual-inline.js?v=20261116b"><\/script>';
    document.querySelectorAll("#hpFrame,#hlFrame").forEach(frame=>{
      function inject(){
        const source=frame.getAttribute("srcdoc")||"";
        if(!source||source.includes("/static/bilingual-learning.js"))return;
        const html=/<\/body\s*>/i.test(source)?
          source.replace(/<\/body\s*>/i,script+"</body>"):source+script;
        frame.setAttribute("srcdoc",html);
      }
      new MutationObserver(inject).observe(frame,{attributes:true,attributeFilter:["srcdoc"]});
      inject();
    });
  }
  window.addEventListener("message",event=>{
    const data=event.data||{};
    if(data.type!=="LDVL_STUDY_REPLY"||!pendingFrame)return;
    if(event.source!==pendingFrame.frame.contentWindow||data.nonce!==pendingFrame.nonce)return;
    pendingFrame=null;
    if(!data.text){toast("Không tìm được nội dung chữ trong bài HTML.",true);return;}
    const src=clean(data.text);
    lastSignature=src;
    runTranslation({text:src,marks:{}});
  });
  function stopListening(){
    try{if(window.speechSynthesis)window.speechSynthesis.cancel();}catch(e){}
  }
  function listen(){
    if(!lastResult){toast("Hãy dịch đoạn văn trước.",true);return;}
    if(!("speechSynthesis" in window)){toast("Trình duyệt chưa hỗ trợ đọc tiếng Anh/Việt.",true);return;}
    stopListening();
    const phrase=lastResult.replace(tokenRE, " công thức ").slice(0,2800);
    const utterance=new SpeechSynthesisUtterance(phrase);
    utterance.lang=resultLanguage==="en"?"en-US":"vi-VN";
    utterance.rate=0.9;
    window.speechSynthesis.speak(utterance);
  }
  function copyResult(){
    if(!lastResult)return;
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(lastResult).then(()=>toast("Đã sao chép bản dịch.")).catch(()=>toast("Trình duyệt không cho phép sao chép.",true));
    }else toast("Không hỗ trợ sao chép trên trình duyệt này.",true);
  }
  function refreshControls(){
    const toggle=$("ldvl-lang-toggle");
    if(toggle)toggle.textContent="🌐 "+(mode==="both"?"VI · EN":mode.toUpperCase());
    for(const key of Object.keys(T)){
      const btn=$("ll-mode-"+key);
      if(btn)btn.setAttribute("aria-pressed",String(mode===key));
    }
    $("ll-original").hidden=mode!=="both";
  }
  function setMode(next){
    if(!T[next])return;
    mode=next;
    try{localStorage.setItem(STORAGE,mode);}catch(e){}
    refreshControls();
    activeJob++;
    lastSignature="";
    stopListening();
    $("ll-output").hidden=true;
    toast(mode==="vi"?
      "Đang ưu tiên tiếng Việt. Chọn Dịch câu hỏi để dịch từ tiếng Anh sang tiếng Việt.":
      mode==="en"?"Đang chuyển câu hỏi sang tiếng Anh ngay trên trang.":
      "Chế độ song ngữ: bản gốc và tiếng Anh ngay trong bài.");
    window.dispatchEvent(new CustomEvent("ldvl:languagechange",{detail:{mode}}));
    if(mode!=="vi" && !window.ldvlInlineSwitch) translateQuestion();
  }
  function openClose(force){
    opened=typeof force==="boolean"?force:!opened;
    $("ldvl-lang-panel").hidden=!opened;
    $("ldvl-lang-toggle").setAttribute("aria-expanded",String(opened));
    if(!opened)stopListening();
    if(opened&&mode!=="vi"&&!lastSignature&&!window.ldvlInlineSwitch)translateQuestion();
  }
  function watchQuestion(){
    const q=document.querySelector("#q")||document.querySelector("#question");
    if(!q || observedQuestion===q)return;
    if(observedQuestion&&observedQuestion.__ldvlObserver)observedQuestion.__ldvlObserver.disconnect();
    observedQuestion=q;
    let delayed=null;
    const observer=new MutationObserver(()=>{
      clearTimeout(delayed);
      delayed=setTimeout(()=>{
        if(!opened||mode==="vi")return;
        const data=questionData();
        if(data.text && data.text!==lastSignature){
          lastSignature=data.text;
          runTranslation(data);
        }
      },550);
    });
    observer.observe(q,{childList:true,subtree:false,characterData:false});
    q.__ldvlObserver=observer;
  }
  function mount(){
    if(!$("ldvl-lang-toggle")){
      const button=document.createElement("button");
      button.type="button";
      button.id="ldvl-lang-toggle";
      button.setAttribute("aria-label","Mở công cụ học song ngữ Việt–Anh");
      button.setAttribute("aria-controls","ldvl-lang-panel");
      button.setAttribute("aria-expanded","false");
      document.body.appendChild(button);
      const panel=document.createElement("section");
      panel.id="ldvl-lang-panel";panel.hidden=true;
      panel.setAttribute("aria-label","Công cụ học song ngữ");
      panel.innerHTML=
        '<div class="ll-head"><strong>🌐 Học song ngữ Việt – Anh</strong>'+
          '<button type="button" class="ll-close" aria-label="Đóng" id="ll-close">×</button></div>'+
        '<div class="ll-body">'+
          '<div class="ll-modes" role="group" aria-label="Chọn ngôn ngữ">'+
            '<button type="button" class="ll-mode" id="ll-mode-vi">🇻🇳 Tiếng Việt</button>'+
            '<button type="button" class="ll-mode" id="ll-mode-en">🇬🇧 English</button>'+
            '<button type="button" class="ll-mode" id="ll-mode-both">📚 Song ngữ</button>'+
          '</div>'+
          '<p class="ll-info">Dịch câu hỏi hoặc đoạn được bôi đen. Không thay đổi đề gốc, công thức, lựa chọn hay kết quả chấm.</p>'+
          '<div class="ll-actions">'+
            '<button type="button" class="ll-action primary" id="ll-translate">🌐 Dịch câu hỏi</button>'+
            '<button type="button" class="ll-action" id="ll-selection">✏️ Dịch đoạn bôi đen</button>'+
          '</div>'+
          '<div class="ll-status" id="ll-status" role="status" aria-live="polite">Chọn ngôn ngữ để bắt đầu.</div>'+
          '<div class="ll-output" id="ll-output" hidden>'+
            '<div class="ll-original" id="ll-original" hidden></div>'+
            '<div class="ll-label" id="ll-target-label">ENGLISH TRANSLATION</div>'+
            '<div class="ll-translation" id="ll-translated"></div>'+
          '</div>'+
          '<div class="ll-actions">'+
            '<button type="button" class="ll-action" id="ll-speak" disabled>🔊 Nghe phát âm</button>'+
            '<button type="button" class="ll-action" id="ll-copy" disabled>📋 Sao chép</button>'+
            '<button type="button" class="ll-action" id="ll-stop">◼ Dừng đọc</button>'+
          '</div>'+
          '<p class="ll-info">Bản dịch bằng Gemini chỉ để hỗ trợ học tập; luôn kiểm tra nội dung và thuật ngữ từ đề gốc.</p>'+
        '</div>';
      document.body.appendChild(panel);
      button.addEventListener("click",()=>openClose());
      $("ll-close").addEventListener("click",()=>openClose(false));
      for(const key of Object.keys(T))$("ll-mode-"+key).addEventListener("click",()=>setMode(key));
      $("ll-translate").addEventListener("click",translateQuestion);
      $("ll-selection").addEventListener("click",translateSelection);
      $("ll-speak").addEventListener("click",listen);
      $("ll-stop").addEventListener("click",stopListening);
      $("ll-copy").addEventListener("click",copyResult);
      document.addEventListener("selectionchange",updateSavedSelection,{passive:true});
      document.addEventListener("pointerdown",e=>{
        if(!e.target.closest("#ldvl-lang-panel,#ldvl-lang-toggle"))lastOutput=e.target;
      },{passive:true});
      document.addEventListener("keydown",e=>{
        if(e.key==="Escape"&&opened)openClose(false);
      });
    }
    refreshControls();
    watchQuestion();
    installFrameBridge();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",mount,{once:true});
  else mount();
  window.ldvlBilingual={open:()=>openClose(true),translateQuestion,translateSelection};
})();