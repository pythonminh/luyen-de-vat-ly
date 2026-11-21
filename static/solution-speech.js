/* Speak revealed explanations and LaTeX, never expose a hidden answer before submission. */
(() => {
  "use strict";
  // Trang ngân hàng câu hỏi chỉ hiển thị đề, đáp án và lời giải, không chèn bộ đọc.
  if (/^\/member\/(?:dang|select)(?:\/|$)/.test(location.pathname)) return;
  if (window.__ldvlSolutionSpeech) return;
  window.__ldvlSolutionSpeech = true;

  const FORMULA = "mjx-container,.katex,math,.MathJax,script[type^='math/tex'],.tikzfig,.tikz-row,.immini,img,svg,canvas";
  const SOLUTION = "#solbox, #solution, .solution, .answer-explanation, .explanation, .loigiai, [data-solution]";
  let speechId = 0, speaking = false, currentPanel = null, refreshPending = false, lastFocused = null;
  const LANG_KEY = "ldvlSolutionSpeechLanguage_v1";
  let chosen = "auto";
  try { chosen = localStorage.getItem(LANG_KEY) || "auto"; } catch(e) {}
  if (!["auto","vi","en"].includes(chosen)) chosen = "auto";
  const clean = text => String(text || "").replace(/\s+/g," ").trim();
  const isVisible = el => {
    if (!el || !el.isConnected || !el.getClientRects().length) return false;
    const css = getComputedStyle(el);
    return css.visibility !== "hidden" && css.display !== "none";
  };
  const hasVietnamese = text => /[ăâđêôơưĂÂĐÊÔƠƯàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]/i.test(text);
  function stop() {
    speechId++;
    const wasSpeaking=speaking;
    speaking = false;
    // An idle solution reader must not cancel the translation reader's TTS.
    if(wasSpeaking)try { window.speechSynthesis?.cancel(); } catch(e) {}
    updateButtons();
  }
  function updateButtons() {
    for (const box of document.querySelectorAll(".ll-sol-tools")) {
      const play=box.querySelector(".ll-sol-play"), stopBtn=box.querySelector(".ll-sol-stop");
      const active=speaking && currentPanel && box.closest(SOLUTION)===currentPanel;
      if (play) play.textContent=active ? "↻ Đọc lại lời giải" : "🔊 Đọc lời giải";
      if (stopBtn) stopBtn.disabled=!active;
    }
    for (const btn of document.querySelectorAll(".ll-sol-quick-play"))
      btn.textContent=speaking?"🔊 Đọc lại lời giải":"🔊 Đọc lời giải";
  }
  function solutions() {
    const found=Array.from(document.querySelectorAll(SOLUTION)).filter(el=>
      !el.closest(".ll-sol-tools,#ldvl-lang-panel") && isVisible(el));
    // Select only the largest visible explanation region in nested structures.
    return found.filter(el=>!found.some(parent=>parent!==el && parent.contains(el)));
  }
  function extract(root, language) {
    const converter=window.ldvlMathSpeech;
    if (converter?.prepareElement) converter.prepareElement(root);
    const marks={};
    let index=0;
    const wantsEnglish=language==="en";
    const allowed = n => {
      if (!n || n.nodeType!==1) return false;
      const tag=n.tagName?.toLowerCase()||"";
      if (/^(button|input|textarea|select|script|style|noscript|iframe|video|audio)$/.test(tag)) return false;
      if (n.matches(".ll-sol-tools,.ll-sol-speech-note,.ll-sol-preview,.ll-no-translate")) return false;
      if (n.matches(".ll-inline-original")){
        const target=n.parentElement?.querySelector(":scope > .ll-inline-target");
        if (wantsEnglish && target && clean(target.textContent)) return false;
        return true;
      }
      if (n.matches(".ll-inline-target")){
        const original=n.parentElement?.querySelector(":scope > .ll-inline-original");
        if (!wantsEnglish || !original || !clean(n.textContent)) return false;
        return true;
      }
      if (n !== root && (n.hasAttribute("hidden") || n.getAttribute("aria-hidden")==="true")) return false;
      return true;
    };
    function visit(node) {
      if (!node) return "";
      if (node.nodeType===3) return node.nodeValue||"";
      if (node.nodeType!==1 || !allowed(node)) return "";
      const el=node;
      if (el.matches(FORMULA)) {
        const key="⟦M"+(index++)+"⟧";
        marks[key]=el;
        return " "+key+" ";
      }
      if (el.tagName==="BR") return "\n";
      const tag=el.tagName||"";
      const parts=Array.from(el.childNodes).map(visit).join("");
      if (/^(P|DIV|SECTION|ARTICLE|LI|TR|H[1-6])$/.test(tag))
        return "\n"+parts+"\n";
      if (/^(TD|TH)$/.test(tag)) return parts+"; ";
      return parts;
    }
    const raw=visit(root).replace(/\n{3,}/g,"\n\n").trim();
    return {text:raw,marks,converter};
  }
  function getSpeech(root, language) {
    const d=extract(root,language);
    const rawText=d.text;
    const actual=language==="auto"
      ?(hasVietnamese(rawText) ? "vi" : "en")
      :language;
    // If English mode is selected but the solution has not yet been translated,
    // read the original Vietnamese with the right pronunciation rather than skip it.
    const fallback = actual==="en" && hasVietnamese(rawText) &&
      !root.querySelector(".ll-inline-target:not([hidden])");
    const lang=(fallback ? "vi" : actual)==="en"?"en-US":"vi-VN";
    const spoken=d.converter?.textToSpeech
      ?d.converter.textToSpeech(rawText,lang,d.marks) : rawText;
    return {spoken:clean(spoken),lang,converter:d.converter};
  }
  function solutionPanel(el) {
    return el.closest(SOLUTION);
  }
  function preferredVoice(lang) {
    const voices=window.speechSynthesis.getVoices()||[];
    const lowercase=lang.toLowerCase();
    return voices.find(v=>v.lang.toLowerCase()===lowercase&&v.localService)
      || voices.find(v=>v.lang.toLowerCase()===lowercase)
      || voices.find(v=>v.lang.toLowerCase().startsWith(lowercase.slice(0,2)));
  }
  function start(root) {
    if (!root || !isVisible(root)) return;
    if (!("speechSynthesis" in window)) {
      setNote(root,"Trình duyệt chưa hỗ trợ đọc lời giải.",true); return;
    }
    stop();
    window.dispatchEvent(new Event("ldvl:solution-speech-start"));
    currentPanel=root;
    const myId=speechId;
    const selector=root.querySelector(".ll-sol-language");
    let selection=selector?.value||chosen;
    if(selection==="auto"){
      let savedMode="vi";
      try{savedMode=localStorage.getItem("ldvlBilingualStudyMode_v1")||"vi";}catch(e){}
      if(savedMode==="en")selection="en";
    }
    const read=getSpeech(root,selection);
    if (!read.spoken) {
      setNote(root,"Không tìm thấy nội dung lời giải để đọc.",true);return;
    }
    const preview=root.querySelector(".ll-sol-preview-content");
    if (preview) preview.textContent=read.spoken;
    const chunks=read.converter?.chunks
      ?read.converter.chunks(read.spoken.slice(0,18000),170)
      :[read.spoken.slice(0,18000)];
    if (!chunks.length)return;
    speaking=true; updateButtons();
    const voice=preferredVoice(read.lang);
    let index=0;
    const next=()=>{
      if (myId!==speechId)return;
      if (index>=chunks.length) {
        speaking=false;updateButtons();
        setNote(root,"Đã đọc xong lời giải và công thức.");
        return;
      }
      const utterance=new SpeechSynthesisUtterance(chunks[index]);
      utterance.lang=read.lang;
      utterance.rate=Number(document.getElementById("ll-rate")?.value||0.9);
      utterance.pitch=1;
      if (voice) utterance.voice=voice;
      utterance.onstart=()=>{
        if (myId!==speechId)return;
        setNote(root,"Đang đọc "+(read.lang.startsWith("en")?"tiếng Anh":"tiếng Việt")+
          " · "+(index+1)+"/"+chunks.length+" đoạn");
      };
      utterance.onend=()=>{
        if (myId!==speechId)return;
        index++;
        next();
      };
      utterance.onerror=e=>{
        if (myId!==speechId || ["canceled","interrupted"].includes(e?.error))return;
        speaking=false;updateButtons();
        setNote(root,"Không phát được lời giải. Kiểm tra giọng đọc trên thiết bị hoặc xem phần “Cách đọc công thức”.",true);
      };
      window.speechSynthesis.speak(utterance);
    };
    next();
  }
  function setNote(root,message,isError=false) {
    const note=root?.querySelector(".ll-sol-speech-note");
    if (!note)return;
    note.textContent=message;
    note.classList.toggle("ll-error",Boolean(isError));
  }
  function mountSolution(root) {
    if (!root || root.querySelector(":scope > .ll-sol-tools")) return;
    // The toolbar appears only in a revealed solution, never in a concealed key.
    if (!isVisible(root))return;
    const tools=document.createElement("div");
    tools.className="ll-sol-tools";
    tools.setAttribute("role","group");
    tools.setAttribute("aria-label","Công cụ đọc lời giải");
    const play=document.createElement("button");
    play.type="button";play.className="ll-sol-play";
    play.textContent="🔊 Đọc lời giải";
    const stopBtn=document.createElement("button");
    stopBtn.type="button";stopBtn.className="ll-sol-stop";
    stopBtn.textContent="■ Dừng";
    stopBtn.disabled=true;
    const selector=document.createElement("select");
    selector.className="ll-sol-language";selector.setAttribute("aria-label","Chọn ngôn ngữ đọc lời giải");
    for (const [value,label] of [["auto","Tự động"],["vi","🇻🇳 Tiếng Việt"],["en","🇬🇧 English"]]) {
      const option=document.createElement("option");
      option.value=value; option.textContent=label;
      selector.append(option);
    }
    selector.value=chosen;
    const preview=document.createElement("details");
    preview.className="ll-sol-preview";
    const summary=document.createElement("summary");
    summary.textContent="∑ Cách đọc công thức";
    const content=document.createElement("div");
    content.className="ll-sol-preview-content";
    content.textContent="Bấm Đọc lời giải để xem văn bản máy sẽ đọc.";
    preview.append(summary,content);
    const note=document.createElement("span");
    note.className="ll-sol-speech-note";
    note.setAttribute("role","status");
    tools.append(play,stopBtn,selector,preview,note);
    root.insertBefore(tools,root.firstChild);
    play.addEventListener("click",()=>start(root));
    stopBtn.addEventListener("click",()=>{
      stop(); setNote(root,"Đã dừng đọc lời giải.");
    });
    selector.addEventListener("change",()=>{
      chosen=selector.value;
      try{localStorage.setItem(LANG_KEY,chosen);}catch(e){}
      if (speaking && currentPanel===root)start(root);
    });
  }
  function showFromAnswer() {
    // In member/practice, the result is created ONLY after the student submits.
    const result=document.querySelector("#q #r .result");
    if (!result || !isVisible(result))return;
    const parent=result.parentElement;
    if (!parent || parent.querySelector(".ll-sol-quick-play"))return;
    const quick=document.createElement("button");
    quick.type="button";quick.className="ll-sol-quick-play";
    quick.textContent="🔊 Đọc lời giải";
    quick.addEventListener("click",()=>{
      let root=document.querySelector("#q #solbox");
      if (!root)return;
      if (!isVisible(root)) {
        // Respect the same answer-release action as the existing View Solution button.
        const trigger=document.getElementById("solbtn");
        if (trigger && isVisible(trigger))trigger.click();
        else if (typeof window.openSolution==="function")window.openSolution();
      }
      root=document.querySelector("#q #solbox");
      if (root && isVisible(root)){
        mountSolution(root);start(root);
      }
    });
    result.insertAdjacentElement("afterend",quick);
  }
  function refresh() {
    refreshPending=false;
    showFromAnswer();
    for(const root of solutions())mountSolution(root);
    if(currentPanel && !isVisible(currentPanel) && speaking)stop();
  }
  function scheduleRefresh() {
    if(refreshPending)return;
    refreshPending=true;
    // Coalesce DOM mutations; do not mutate the DOM from the observer itself.
    Promise.resolve().then(refresh);
  }
  function mount() {
    refresh();
    const observer=new MutationObserver(records=>{
      const useful=records.some(r=>{
        if(r.type==="attributes" && /^(style|hidden|class)$/.test(r.attributeName||""))
          return r.target.matches?.(SOLUTION) || r.target.closest?.("#q,#r");
        if(r.type==="childList"){
          if(r.target.closest?.(".ll-sol-tools,.ll-sol-preview,#ldvl-lang-panel"))return false;
          return r.addedNodes.length>0 || r.removedNodes.length>0;
        }
        return false;
      });
      if(useful)scheduleRefresh();
    });
    observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:["style","hidden","class"]});
    window.addEventListener("ldvl:study-speech-start",()=>{
      if(speaking)stop();
    });
    window.addEventListener("pagehide",stop);
    document.addEventListener("visibilitychange",()=>{
      if(document.hidden && speaking)stop();
    });
  }
  if(document.readyState==="loading")
    document.addEventListener("DOMContentLoaded",mount,{once:true});
  else mount();
  window.ldvlSolutionSpeech={stop,start};
})();