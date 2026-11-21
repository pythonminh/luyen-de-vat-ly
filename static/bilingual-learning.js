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
        // Ask the inline layer which question the learner is viewing.
        // Convert math markers back to TeX for cross-frame text messaging.
        if(typeof window.ldvlInlineQuestionData==="function"){
          const selected=window.ldvlInlineQuestionData();
          if(selected?.text){
            return String(selected.text).replace(/⟦M\d+⟧/g,token=>{
              const node=selected.marks?.[token];
              const latex=node&&window.ldvlMathSpeech?.formulaSource?.(node);
              return latex?"\\("+latex+"\\)":" [hình minh họa] ";
            }).slice(0,5200);
          }
        }
        const candidates=Array.from(document.querySelectorAll("#q .qstem,.qstem,#question,.question-text,.question-content,.problem-text,.quiz-question"))
          .filter(el=>el.getClientRects().length);
        const selected=candidates.find(el=>el.matches(".active,.current,[aria-current='true']"));
        const stem=selected||candidates.sort((a,b)=>{
          const c=innerHeight*.45,ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();
          return Math.abs((ar.top+ar.bottom)/2-c)-Math.abs((br.top+br.bottom)/2-c);
        })[0];
        if(!stem)return "";
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
  let speechRunId=0, isStudySpeaking=false;
  let lastSource="",lastEnglish="",lastMarks={},activeGrammarRequest=0;
  const grammarCache=new Map();
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
    if(lastSource && lastSource!==source){
      activeGrammarRequest++;
      const grammarButton=$("ll-grammar");
      if(grammarButton){grammarButton.disabled=false;grammarButton.textContent="🧠 Phân tích ngữ pháp";}
    }
    parent.hidden=false;
    const showBoth=mode==="both";
    original.hidden=!showBoth;
    const sourceCard=parent.querySelector(".ll-source-card");
    if(sourceCard)sourceCard.hidden=!showBoth;
    if(showBoth) fill(original,source,marks);
    fill(out,translated,marks);
    $("ll-target-label").textContent=target==="en"?"ENGLISH TRANSLATION":"BẢN DỊCH TIẾNG VIỆT";
    $("ll-speak").disabled=!clean(translated);
    $("ll-copy").disabled=!clean(translated);
    lastResult=translated;resultLanguage=target;
    lastSource=source;lastEnglish=target==="en"?translated:source;lastMarks=marks;
    const sourceListen=$("ll-speak-original");if(sourceListen)sourceListen.disabled=!clean(source);
    showQuickGrammar();
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
    if(window.ldvlMathSpeech?.prepareElement)window.ldvlMathSpeech.prepareElement(el);
    const cloned=el.cloneNode(true);
    cloned.querySelectorAll(".ll-inline-original").forEach(n=>n.removeAttribute("hidden"));
    cloned.querySelectorAll("input, textarea, button, select, script, style, .ll-no-translate, .ll-inline-target, [hidden]").forEach(n=>n.remove());
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
          if(window.ldvlMathSpeech?.prepareElement)window.ldvlMathSpeech.prepareElement(opt);
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
    if(lastSource!==text){
      stopListening();
      activeGrammarRequest++;
      const grammarButton=$("ll-grammar");
      if(grammarButton){grammarButton.disabled=false;grammarButton.textContent="🧠 Phân tích ngữ pháp";}
    }
    // Enable 'Read original' immediately, even if Gemini translation is pending.
    lastSource=text;lastMarks=marks;lastResult="";lastEnglish="";
    const originalButton=$("ll-speak-original"),translationButton=$("ll-speak");
    if($("ll-copy"))$("ll-copy").disabled=true;
    if(originalButton)originalButton.disabled=false;
    if(translationButton)translationButton.disabled=true;
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
    const data=window.ldvlInlineQuestionData?.()||questionData();
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
    const script='<script src="'+location.origin+'/static/math-speech.js?v=20261122bilingual5"><\/script>'+
      '<script src="'+location.origin+'/static/bilingual-learning.js?v=20261122bilingual5"><\/script>'+
      '<script src="'+location.origin+'/static/bilingual-inline.js?v=20261122bilingual5"><\/script>'+
      '<script src="'+location.origin+'/static/solution-speech.js?v=20261122bilingual5"><\/script>';
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
  // A new visible question invalidates the previous translation, speech and
  // grammar. The inline reader will translate ONLY the newly visible question.
  window.addEventListener("ldvl:current-question-changed",event=>{
    const current=event.detail||{};
    activeJob++;
    activeGrammarRequest++;
    stopListening();
    lastSignature=String(current.text||"");
    lastSource=String(current.text||"");
    lastMarks=current.marks||{};
    lastEnglish="";lastResult="";lastOutput=null;
    const output=$("ll-output");if(output)output.hidden=true;
    const translatedSpeak=$("ll-speak");if(translatedSpeak)translatedSpeak.disabled=true;
    const copy=$("ll-copy");if(copy)copy.disabled=true;
    const sourceSpeak=$("ll-speak-original");if(sourceSpeak)sourceSpeak.disabled=!lastSource;
    const preview=$("ll-speech-preview");if(preview)preview.textContent="";
    const previewBox=$("ll-read-preview");if(previewBox)previewBox.hidden=true;
    const btn=$("ll-grammar");
    if(btn){btn.disabled=false;btn.textContent="🧠 Phân tích ngữ pháp";}
    if(opened&&mode!=="vi")toast(lastSource?"Đang dịch câu hỏi hiện tại…":"Chọn một câu hỏi để dịch.");
  });
  // Use English wording from the inline question translator for grammar hints.
  window.addEventListener("ldvl:inline-translated",event=>{
    const detail=event.detail||{};
    if(!detail.english||!detail.source)return;
    setOutput(String(detail.source),String(detail.english),detail.marks||{},"en");
  });
  function stopListening(){
    speechRunId++;
    const wasSpeaking=isStudySpeaking;
    isStudySpeaking=false;
    // Two independent readers share one Android TTS engine. Only the reader
    // which owns current speech may cancel; idle readers must never cancel.
    if(wasSpeaking){
      try{window.speechSynthesis?.cancel();}catch(e){}
    }
  }
  window.addEventListener("ldvl:solution-speech-start",()=>{
    if(isStudySpeaking)stopListening();
  });
  function listen(which="translation"){
    const isOriginal=which==="original";
    let source=isOriginal?lastSource:lastResult;
    let marks=lastMarks||{};
    if(!source && isOriginal){
      // Reading the original question must work even before translation.
      const current=questionData();
      if(current.text){
        lastSource=current.text;lastMarks=current.marks;
        source=current.text;marks=current.marks;
        const sourceBtn=$("ll-speak-original");if(sourceBtn)sourceBtn.disabled=false;
      }
    }
    if(!source){toast("Hãy mở câu hỏi hoặc dịch đoạn văn trước khi đọc.",true);return;}
    if(!("speechSynthesis" in window)){toast("Trình duyệt chưa hỗ trợ đọc bằng giọng nói.",true);return;}
    stopListening();
    window.dispatchEvent(new Event("ldvl:study-speech-start"));
    const readId=speechRunId;
    const vietnamese=/[ăâđêôơưĂÂĐÊÔƠƯàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]/i;
    const lang=isOriginal
      ?(vietnamese.test(source)?"vi-VN":"en-US")
      :(resultLanguage==="en"?"en-US":"vi-VN");
    const converter=window.ldvlMathSpeech;
    const spoken=converter?.textToSpeech
      ?converter.textToSpeech(source,lang,marks)
      :source.replace(/\$\$?([^$\n]+)\$\$?/g," $1 ");
    const preview=$("ll-speech-preview");
    if(preview){
      preview.textContent=spoken||"Không có nội dung đọc.";
      const wrap=$("ll-read-preview");
      if(wrap)wrap.hidden=!spoken;
    }
    if(!spoken){toast("Chưa đọc được nội dung. Hãy chọn một câu có chữ hoặc công thức.",true);return;}
    const segments=converter?.chunks?converter.chunks(spoken.slice(0,6500),180):[spoken.slice(0,2200)];
    if(!segments.length)return;
    const voices=window.speechSynthesis.getVoices()||[];
    const preferred=voices.find(v=>v.lang.toLowerCase()===lang.toLowerCase()&&v.localService)
      ||voices.find(v=>v.lang.toLowerCase()===lang.toLowerCase())
      ||voices.find(v=>v.lang.toLowerCase().startsWith(lang.slice(0,2).toLowerCase()));
    let index=0;
    const readNext=()=>{
      if(readId!==speechRunId)return;
      if(index>=segments.length){
        isStudySpeaking=false;
        toast("Đã đọc cả nội dung và công thức. Có thể bấm nghe lại để luyện tập.");
        return;
      }
      const utterance=new SpeechSynthesisUtterance(segments[index]);
      utterance.lang=lang;utterance.rate=Number($("ll-rate")?.value||0.9);
      utterance.pitch=1;
      if(preferred)utterance.voice=preferred;
      utterance.onstart=()=>{
        if(readId===speechRunId)
          toast("🔊 Đang đọc "+(lang.startsWith("en")?"tiếng Anh":"tiếng Việt")+
            " · đoạn "+(index+1)+"/"+segments.length+" (có công thức).");
      };
      utterance.onend=()=>{
        if(readId!==speechRunId)return;
        index++;
        readNext();
      };
      utterance.onerror=(event)=>{
        if(readId!==speechRunId || ["canceled","interrupted"].includes(event?.error))return;
        isStudySpeaking=false;
        toast("Không đọc được trên thiết bị. Kiểm tra cài đặt giọng đọc hoặc xem phần “Cách đọc công thức”.",true);
      };
      window.speechSynthesis.speak(utterance);
    };
    isStudySpeaking=true;
    readNext();
  }
  function grammarCard(item) {
    const wrap=document.createElement("article");
    wrap.className="ll-grammar-card";
    const head=document.createElement("strong");
    head.textContent=item.name||"Cấu trúc câu";
    wrap.appendChild(head);
    if(item.fragment){
      const code=document.createElement("span");
      code.className="ll-grammar-fragment";
      code.textContent=item.fragment;
      wrap.appendChild(code);
    }
    const desc=document.createElement("p");
    desc.textContent=item.explanation||"";
    wrap.appendChild(desc);
    if(item.example){
      const example=document.createElement("small");
      example.textContent="Ví dụ: "+item.example;
      wrap.appendChild(example);
    }
    return wrap;
  }
  const glossary={
    "pressure":"áp suất","volume":"thể tích","temperature":"nhiệt độ",
    "mass":"khối lượng","density":"khối lượng riêng",
    "velocity":"vận tốc","speed":"tốc độ","acceleration":"gia tốc",
    "force":"lực","energy":"năng lượng","power":"công suất",
    "increase":"tăng","decrease":"giảm","constant":"không đổi",
    "equation":"phương trình","function":"hàm số","triangle":"tam giác",
    "angle":"góc","calculate":"tính toán","determine":"xác định",
    "find":"tìm","given":"cho biết","proportional":"tỉ lệ",
    "respectively":"tương ứng","approximately":"xấp xỉ"
  };
  function quickPatterns(text) {
    const samples=[];
    const rules=[
      {re:/\bhow many\b/i,name:"How many + danh từ đếm được",cue:"Hỏi số lượng vật hoặc số lần.",example:"How many cycles are completed?"},
      {re:/\bhow much\b/i,name:"How much + danh từ không đếm được",cue:"Hỏi lượng, giá trị hoặc mức độ.",example:"How much energy is transferred?"},
      {re:/\bif\b[\s\S]{0,140}?(?:,|then\b)/i,name:"Mệnh đề điều kiện If",cue:"If + điều kiện; mệnh đề chính diễn tả kết quả. Xác định giả thiết trước khi đọc phần yêu cầu.",example:"If the volume increases, the pressure changes."},
      {re:/\b(?:is|are|was|were)\s+(?:\w+ly\s+)?(?:given|measured|heated|applied|released|transferred|calculated|increased|decreased|used|placed)\b/i,name:"Câu bị động (Passive voice)",cue:"Be + quá khứ phân từ (V3) tập trung vào đối tượng chịu tác động.",example:"The temperature is measured in kelvin."},
      {re:/\b(?:greater than|less than|larger than|smaller than|higher than|lower than|more than|fewer than)\b/i,name:"So sánh hơn",cue:"Tính từ so sánh + than để đối chiếu hai đại lượng.",example:"The second value is higher than the first."},
      {re:/\bwhen\b/i,name:"Mệnh đề When",cue:"When giới thiệu thời điểm hoặc điều kiện xảy ra hiện tượng.",example:"When the gas cools, its pressure decreases."},
      {re:/\b(?:calculate|determine|find|compare|identify|solve|choose)\b/i,name:"Động từ yêu cầu",cue:"Động từ ở đầu câu chỉ thao tác học sinh cần thực hiện: tính, xác định, tìm hoặc so sánh.",example:"Determine the value of the unknown."},
      {re:/\b(?:is|are)\s+(?:directly|inversely)?\s*proportional\s+to\b/i,name:"Be proportional to",cue:"Cấu trúc mô tả quan hệ tỉ lệ giữa hai đại lượng.",example:"One quantity is proportional to another."},
      {re:/\b(?:in order to|so that)\b/i,name:"Cấu trúc chỉ mục đích",cue:"In order to + động từ hoặc so that + mệnh đề diễn tả mục đích.",example:"Measure carefully in order to compare the results."}
    ];
    for(const rule of rules){
      if(rule.re.test(text))samples.push({name:rule.name,fragment:"",explanation:rule.cue,example:rule.example});
      if(samples.length>=3)break;
    }
    if(!samples.length && /\b(?:is|are|has|have|does|do|was|were)\b/i.test(text)){
      samples.push({name:"Chủ ngữ và động từ",fragment:"",explanation:"Tìm động từ chính (is/are/has/have/does...) để xác định chủ ngữ và ý nghĩa câu.",example:"The object has a constant mass."});
    }
    return samples;
  }
  function renderGrammar(payload){
    const holder=$("ll-grammar-patterns"),vocab=$("ll-grammar-vocab"),tip=$("ll-grammar-tip"),empty=$("ll-grammar-empty");
    if(!holder||!vocab||!tip||!empty)return;
    holder.replaceChildren();vocab.replaceChildren();
    for(const p of (payload.patterns||[]).slice(0,4))holder.appendChild(grammarCard(p));
    if(payload.vocabulary?.length){
      const heading=document.createElement("strong");
      heading.className="ll-vocab-heading";
      heading.textContent="Từ vựng Toán – Vật lí";
      vocab.appendChild(heading);
      for(const word of payload.vocabulary.slice(0,6)){
        const row=document.createElement("div");
        row.className="ll-word";
        const en=document.createElement("b");en.textContent=word.en||"";
        const vi=document.createElement("span");vi.textContent=word.vi||"";
        row.append(en,vi);vocab.appendChild(row);
      }
    }
    tip.hidden=!payload.practice_tip;
    if(!tip.hidden)tip.textContent="💡 "+payload.practice_tip;
    empty.hidden=Boolean(holder.children.length||vocab.children.length||!tip.hidden);
    if(!empty.hidden)empty.textContent="Đoạn này chưa có đủ cấu trúc tiếng Anh để gợi ý. Hãy dịch một câu có nội dung chữ.";
  }
  function showQuickGrammar(){
    const text=(lastEnglish||"").replace(tokenRE," ").replace(/\\\w+/g," ").trim();
    const words=[];
    for(const [word,translation] of Object.entries(glossary)){
      if(new RegExp("\\b"+word+"\\b","i").test(text))words.push({en:word,vi:translation});
      if(words.length>=5)break;
    }
    renderGrammar({patterns:quickPatterns(text),vocabulary:words,practice_tip:"Tìm chủ ngữ, động từ chính và từ chỉ yêu cầu trước khi giải bài."});
  }
  async function fetchGrammar(){
    const button=$("ll-grammar");
    if(!button)return;
    let src=lastSource,english=lastEnglish;
    if(!src){
      const selection=readSelection()||savedSelection;
      const picked=questionData();
      src=selection||picked.text;
      if(!src){toast("Chọn một câu hỏi hoặc đoạn văn để phân tích.",true);return;}
      english=src;
      lastSource=src;lastEnglish=english;lastMarks=selection?{}:(picked.marks||{});
    }
    const cacheKey=src+"\0"+english;
    if(grammarCache.has(cacheKey)){renderGrammar(grammarCache.get(cacheKey));return;}
    const job=++activeGrammarRequest;
    button.disabled=true;
    button.textContent="⏳ Đang phân tích…";
    toast("Đang phân tích cấu trúc tiếng Anh của câu đang học…");
    try{
      // Vietnamese-only mode also supports one-tap grammar help: translate
      // the question to English first, then analyze its actual English wording.
      const vietnamese=/[ăâđêôơưĂÂĐÊÔƠƯàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]/i;
      if(vietnamese.test(english)){
        button.textContent="⏳ Đang dịch sang tiếng Anh…";
        const translation=await fetch("/api/learning/translate",{
          method:"POST",credentials:"same-origin",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({text:src.slice(0,4500),target:"en",api_keys:keys()})
        });
        const translated=await translation.json();
        if(!translation.ok||!translated.ok)throw Error(translated.error||"Chưa dịch được câu tiếng Việt.");
        english=String(translated.translated||"");
        setOutput(src,english,lastMarks||{},"en");
        button.textContent="⏳ Đang tìm cấu trúc ngữ pháp…";
      }
      const response=await fetch("/api/learning/grammar",{
        method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({source:src.slice(0,4500),english:english.slice(0,4500),api_keys:keys()})
      });
      const data=await response.json();
      if(!response.ok||!data.ok)throw Error(data.error||"Chưa phân tích được ngữ pháp.");
      if(job!==activeGrammarRequest)return;
      grammarCache.set(cacheKey,data);
      renderGrammar(data);
      toast("Đã có cấu trúc, ví dụ và từ vựng gắn với câu đang học.");
    }catch(err){
      if(job!==activeGrammarRequest)return;
      showQuickGrammar();
      toast((err&&err.message||"Chưa gọi được Gemini.")+" Gợi ý nhanh vẫn hiển thị.",true);
    }finally{
      if(job===activeGrammarRequest){
        button.disabled=false;
        button.textContent="🧠 Phân tích ngữ pháp";
      }
    }
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
    lastResult="";lastSource="";lastEnglish="";lastMarks={};
    const sourceSpeak=$("ll-speak-original");
    if(sourceSpeak)sourceSpeak.disabled=false;
    // Old translated speech must not remain clickable after changing modes.
    if($("ll-speak"))$("ll-speak").disabled=true;
    if($("ll-copy"))$("ll-copy").disabled=true;
    if($("ll-speech-preview"))$("ll-speech-preview").textContent="";
    if($("ll-read-preview"))$("ll-read-preview").hidden=true;
    if($("ll-grammar-patterns"))renderGrammar({patterns:[],vocabulary:[],practice_tip:""});
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
    if(opened&&!lastSource&&!lastEnglish){
      const q=questionData();
      if(q.text){lastSource=q.text;lastEnglish=q.text;showQuickGrammar();}
    }
  }
  function watchQuestion(){
    const q=document.querySelector("#q")||document.querySelector("#question");
    if(!q || observedQuestion===q)return;
    if(observedQuestion&&observedQuestion.__ldvlObserver)observedQuestion.__ldvlObserver.disconnect();
    observedQuestion=q;
    let delayed=null;
    const observer=new MutationObserver(()=>{
      // Inline translator owns automatic per-question translations. Do not
      // duplicate its API request from the side panel on every DOM mutation.
      if(window.ldvlInlineSwitch)return;
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
          '<p class="ll-info">Chỉ dịch câu đang hiển thị, gồm đề và các phương án. Chuyển câu sẽ tự dịch câu mới; lời giải chỉ dịch khi được mở. Không thay đổi đáp án hoặc cách chấm.</p>'+
          '<div class="ll-actions">'+
            '<button type="button" class="ll-action primary" id="ll-translate">🌐 Dịch câu hiện tại</button>'+
            '<button type="button" class="ll-action" id="ll-selection">✏️ Dịch đoạn bôi đen</button>'+
          '</div>'+
          '<div class="ll-status" id="ll-status" role="status" aria-live="polite">Chọn ngôn ngữ để bắt đầu.</div>'+
          '<div class="ll-output" id="ll-output" hidden>'+
            '<div class="ll-translation-card ll-source-card"><div class="ll-card-label">🇻🇳 / 🇬🇧 <span>Văn bản gốc</span></div>'+
              '<div class="ll-original" id="ll-original" hidden></div></div>'+
            '<div class="ll-translation-card ll-target-card">'+
              '<div class="ll-label" id="ll-target-label">ENGLISH TRANSLATION</div>'+
              '<div class="ll-translation" id="ll-translated"></div></div>'+
          '</div>'+
          '<div class="ll-listen-toolbar" role="group" aria-label="Điều khiển đọc song ngữ">'+
            '<button type="button" class="ll-action" id="ll-speak-original">🔊 Đọc gốc</button>'+
            '<button type="button" class="ll-action primary" id="ll-speak" disabled>▶ Đọc bản dịch</button>'+
            '<label class="ll-speed">Tốc độ <select id="ll-rate"><option value="0.75">0,75×</option><option value="0.9" selected>0,9×</option><option value="1">1×</option><option value="1.15">1,15×</option></select></label>'+
            '<button type="button" class="ll-action ll-stop" id="ll-stop">■ Dừng</button>'+
          '</div>'+
          '<details class="ll-read-preview" id="ll-read-preview" hidden>'+
            '<summary>∑ Xem cách đọc công thức</summary>'+
            '<p class="ll-speech-preview" id="ll-speech-preview"></p>'+
          '</details>'+
          '<div class="ll-actions ll-next-actions">'+
            '<button type="button" class="ll-action" id="ll-copy" disabled>📋 Sao chép</button>'+
            '<button type="button" class="ll-action ll-grammar-button" id="ll-grammar">🧠 Phân tích ngữ pháp</button>'+
          '</div>'+
          '<section class="ll-grammar" id="ll-grammar-box" aria-label="Gợi ý ngữ pháp tiếng Anh">'+
            '<div class="ll-grammar-head"><strong>✦ Gợi ý ngữ pháp</strong><span>English coach</span></div>'+
            '<p class="ll-grammar-empty" id="ll-grammar-empty">Chọn Dịch câu hỏi để thấy cấu trúc tiếng Anh. Bấm “Phân tích ngữ pháp” để nhận giải thích theo đúng câu đang học.</p>'+
            '<div id="ll-grammar-patterns" class="ll-grammar-patterns"></div>'+
            '<div id="ll-grammar-vocab" class="ll-grammar-vocab"></div>'+
            '<div id="ll-grammar-tip" class="ll-grammar-tip" hidden></div>'+
          '</section>'+
          '<p class="ll-info">Bản dịch bằng Gemini chỉ để hỗ trợ học tập; luôn kiểm tra nội dung và thuật ngữ từ đề gốc.</p>'+
        '</div>';
      document.body.appendChild(panel);
      button.addEventListener("click",()=>openClose());
      $("ll-close").addEventListener("click",()=>openClose(false));
      for(const key of Object.keys(T))$("ll-mode-"+key).addEventListener("click",()=>setMode(key));
      $("ll-translate").addEventListener("click",translateQuestion);
      $("ll-selection").addEventListener("click",translateSelection);
      $("ll-speak").addEventListener("click",()=>listen("translation"));
      $("ll-speak-original").addEventListener("click",()=>listen("original"));
      $("ll-grammar").addEventListener("click",fetchGrammar);
      $("ll-stop").addEventListener("click",()=>{stopListening();toast("Đã dừng đọc.");});
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