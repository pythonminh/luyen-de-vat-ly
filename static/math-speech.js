/* Turn LaTeX/MathJax/MathML into understandable Vietnamese or English speech.
   Display mathematics is NEVER modified; this only produces TTS text.
   No external libraries, APIs, or Gemini keys required. */
(function(){
"use strict";
if(window.ldvlMathSpeech)return;
const MARKER=/⟦(?:M|IMG)\d+⟧/g;
const names={
 vi:{
   plus:"cộng",minus:"trừ",negative:"âm",times:"nhân",divide:"chia",over:"trên",
   equal:"bằng",notequal:"khác",approx:"xấp xỉ bằng",
   gt:"lớn hơn",lt:"nhỏ hơn",ge:"lớn hơn hoặc bằng",le:"nhỏ hơn hoặc bằng",
   power:"mũ",sub:"chỉ số",squared:"bình phương",cubed:"lập phương",
   fraction:"phân số",root:"căn bậc hai của",nthroot:"căn bậc",of:"của",
   lparen:"mở ngoặc",rparen:"đóng ngoặc",percent:"phần trăm",
   infinity:"vô cực",sum:"tổng",integral:"tích phân",product:"tích",to:"tiến tới",
   from:"từ",dot:"chấm",vector:"véc tơ",bar:"gạch ngang",
   isconstant:"không đổi",angle:"góc",degree:"độ",
   pi:"pi",theta:"thê ta",alpha:"an pha",beta:"bê ta",gamma:"gam ma",
   delta:"đen ta",lambda:"lam đa",mu:"miu",omega:"ô mê ga",sigma:"xích ma",
   phi:"phi",rho:"rô",epsilon:"ép xi lon",
   forall:"với mọi",exists:"tồn tại",element:"thuộc",notElement:"không thuộc"
 },
 en:{
   plus:"plus",minus:"minus",negative:"negative",times:"times",divide:"divided by",over:"over",
   equal:"equals",notequal:"not equal to",approx:"approximately equal to",
   gt:"greater than",lt:"less than",ge:"greater than or equal to",le:"less than or equal to",
   power:"to the power of",sub:"subscript",squared:"squared",cubed:"cubed",
   fraction:"fraction",root:"square root of",nthroot:"root",of:"of",
   lparen:"open parenthesis",rparen:"close parenthesis",percent:"percent",
   infinity:"infinity",sum:"sum",integral:"integral",product:"product",to:"tends to",
   from:"from",dot:"dot",vector:"vector",bar:"bar",
   isconstant:"constant",angle:"angle",degree:"degrees",
   pi:"pi",theta:"theta",alpha:"alpha",beta:"beta",gamma:"gamma",
   delta:"delta",lambda:"lambda",mu:"mu",omega:"omega",sigma:"sigma",
   phi:"phi",rho:"rho",epsilon:"epsilon",
   forall:"for all",exists:"there exists",element:"belongs to",notElement:"does not belong to"
 }
};
const units={
 vi:{
  "pa":"pascal","kpa":"ki lô pascal","mpa":"mê ga pascal",
  "n":"niutơn","j":"jun","kj":"ki lô jun","w":"oát","kw":"ki lô oát",
  "kg":"ki lô gam","g":"gam","m":"mét","cm":"xen ti mét","mm":"mi li mét",
  "km":"ki lô mét","s":"giây","ms":"mi li giây","min":"phút","h":"giờ",
  "l":"lít","ml":"mi li lít","k":"kelvin","hz":"héc","khz":"ki lô héc",
  "v":"vôn","a":"ampe","t":"tesla","wb":"vê be",
  "mol":"mol","°c":"độ C","oc":"độ C","m/s":"mét trên giây",
  "m/s^2":"mét trên giây bình phương","m/s^{2}":"mét trên giây bình phương",
  "m^2":"mét vuông","m^{2}":"mét vuông","m^3":"mét khối","m^{3}":"mét khối",
  "n/m^2":"niutơn trên mét vuông","n/m^{2}":"niutơn trên mét vuông"
 },
 en:{
  "pa":"pascals","kpa":"kilopascals","mpa":"megapascals",
  "n":"newtons","j":"joules","kj":"kilojoules","w":"watts","kw":"kilowatts",
  "kg":"kilograms","g":"grams","m":"meters","cm":"centimeters","mm":"millimeters",
  "km":"kilometers","s":"seconds","ms":"milliseconds","min":"minutes","h":"hours",
  "l":"liters","ml":"milliliters","k":"kelvin","hz":"hertz","khz":"kilohertz",
  "v":"volts","a":"amperes","t":"tesla","wb":"webers",
  "mol":"moles","°c":"degrees Celsius","oc":"degrees Celsius","m/s":"meters per second",
  "m/s^2":"meters per second squared","m/s^{2}":"meters per second squared",
  "m^2":"square meters","m^{2}":"square meters","m^3":"cubic meters","m^{3}":"cubic meters",
  "n/m^2":"newtons per square meter","n/m^{2}":"newtons per square meter"
 }
};
const commandNames={
 "pi":"pi","theta":"theta","vartheta":"theta","alpha":"alpha","beta":"beta",
 "gamma":"gamma","delta":"delta","Delta":"delta","lambda":"lambda",
 "mu":"mu","omega":"omega","Omega":"omega","sigma":"sigma","Sigma":"sigma",
 "phi":"phi","varphi":"phi","rho":"rho","epsilon":"epsilon","varepsilon":"epsilon",
 "infty":"infinity","sum":"sum","prod":"product","int":"integral","iint":"integral",
 "rightarrow":"to","to":"to","longrightarrow":"to","Rightarrow":"to",
 "le":"le","leq":"le","ge":"ge","geq":"ge","neq":"notequal","ne":"notequal",
 "approx":"approx","simeq":"approx","sim":"approx",
 "times":"times","cdot":"times","ast":"times","div":"divide",
 "pm":"plusminus","mp":"minusplus","in":"element","notin":"notElement",
 "forall":"forall","exists":"exists","angle":"angle",
 "degree":"degree","circ":"degree","partial":"partial",
 "sin":"sin","cos":"cos","tan":"tan","cot":"cot","ln":"ln",
 "log":"log","lim":"lim","max":"max","min":"min",
 "sqrt":"sqrt","frac":"frac","dfrac":"frac","tfrac":"frac",
 "over":"over","left":"left","right":"right",
 "quad":"space","qquad":"space",",":"space",";":"space","!":"space",":":"space",
 "text":"text","textrm":"text","textbf":"text","mathrm":"unit","mathit":"text",
 "mathbf":"text","mathsf":"text","operatorname":"text",
 "vec":"vector","overrightarrow":"vector","overleftarrow":"vector",
 "hat":"hat","bar":"bar","overline":"bar","underline":"underline",
 "underbrace":"text","overbrace":"text",
 "begin":"begin","end":"end","big":"space","Big":"space",
 "bigl":"space","bigr":"space","leftarrow":"to"
};
const symbolKeys={
 "=":"equal","+":"plus","−":"minus","-":"minus","×":"times","⋅":"times",
 "·":"times","*":"times","/":"over","÷":"divide",
 "≈":"approx","≃":"approx","≠":"notequal",
 "<":"lt",">":"gt","≤":"le","≥":"ge",
 "∞":"infinity","π":"pi","θ":"theta","α":"alpha","β":"beta",
 "γ":"gamma","Δ":"delta","δ":"delta","λ":"lambda","μ":"mu",
 "ω":"omega","Ω":"omega","σ":"sigma","φ":"phi","ρ":"rho",
 "∑":"sum","∫":"integral","∏":"product","→":"to",
 "∈":"element","∉":"notElement","∀":"forall","∃":"exists",
 "%":"percent","°":"degree",
 "(":"lparen",")":"rparen","[":"lparen","]":"rparen"
};
function isEnglish(locale){return String(locale||"").toLowerCase().startsWith("en");}
function words(locale){return names[isEnglish(locale)?"en":"vi"];}
function clean(s){return String(s||"").replace(/\s+/g," ").trim();}
function speakUnit(text,lang) {
 const original=String(text||"").replace(/\\,/g,"").trim();
 const key=original.replace(/\s+/g,"").toLowerCase();
 return units[isEnglish(lang)?"en":"vi"][key]||"";
}
function mathToSpeech(input,locale) {
 const W=words(locale);
 const raw=String(input||"").trim();
 if(!raw)return "";
 let s=raw
   .replace(/^\$\$|\$\$$/g,"")
   .replace(/^\$|\$$/g,"")
   .replace(/^\\\(|\\\)$/g,"")
   .replace(/^\\\[|\\\]$/g,"")
   .replace(/\\begin\{(?:aligned|align\*?|equation\*?|gather\*?|array)\}/g," ")
   .replace(/\\end\{(?:aligned|align\*?|equation\*?|gather\*?|array)\}/g," ");
 let i=0;
 function nextGroup(depth=0) {
   while(/\s/.test(s[i]||"")&&i<s.length)i++;
   if(s[i]==="{"){i++;return parse("}",depth+1);}
   if(s[i]==="("){i++;return parse(")",depth+1);}
   if(s[i]==="["){i++;return parse("]",depth+1);}
   if(s[i]==="\\"){
     return parseOne(depth+1);
   }
   if(i>=s.length)return "";
   const m=s.slice(i).match(/^(?:\d+(?:[.,]\d+)*|[a-zA-Z]+|.)/s);
   const piece=m?m[0]:s[i];
   i+=piece.length;
   return mathToSpeech(piece,locale);
 }
 function parseOne(depth){
   if(depth>25||i>=s.length)return "";
   const ch=s[i++];
   if(ch==="\\"){
     if(i>=s.length)return "";
     let cmd="";
     if(/[a-zA-Z]/.test(s[i])){
       while(i<s.length&&/[a-zA-Z]/.test(s[i]))cmd+=s[i++];
     }else cmd=s[i++];
     const op=commandNames[cmd]||cmd;
     if(op==="frac"){
       const a=nextGroup(depth),b=nextGroup(depth);
       return [W.fraction,a,W.over,b].filter(Boolean).join(" ");
     }
     if(op==="sqrt"){
       let index="";
       if(s[i]==="["){i++;index=parse("]",depth+1);}
       const val=nextGroup(depth);
       return index?[W.nthroot,index,W.of,val].join(" "):
         [W.root,val].join(" ");
     }
     if(op==="vector"||op==="bar"||op==="hat"||op==="underline"){
       const val=nextGroup(depth);
       const prefix=op==="vector"?W.vector:op==="bar"?W.bar:op==="hat"?(isEnglish(locale)?"hat":"dấu mũ"):(isEnglish(locale)?"underlined":"gạch dưới");
       return prefix+" "+val;
     }
     if(op==="text"||op==="unit"){
       // Original text/units are NOT thrown away.
       while(/\s/.test(s[i]||"")&&i<s.length)i++;
       if(s[i]==="{"){
         i++;let from=i,depth2=1;
         while(i<s.length&&depth2>0){
           if(s[i]==="{")depth2++;
           else if(s[i]==="}")depth2--;
           if(depth2>0)i++;
         }
         const original=s.slice(from,i);
         if(s[i]==="}")i++;
         const unit=op==="unit"?speakUnit(original,locale):"";
         return unit||mathToSpeech(original,locale);
       }
       return "";
     }
     if(op==="space"||op==="left"||op==="right")return "";
     if(op==="begin"||op==="end"){
       const env=nextGroup(depth);
       return op==="begin"&&(env==="cases"||env==="hệ")?(isEnglish(locale)?"system of equations":"hệ phương trình"):"";
     }
     if(op==="plusminus")return isEnglish(locale)?"plus or minus":"cộng hoặc trừ";
     if(op==="minusplus")return isEnglish(locale)?"minus or plus":"trừ hoặc cộng";
     if(op==="partial")return isEnglish(locale)?"partial":"đạo hàm riêng";
     if(op==="to")return W.to;
     if(op in W)return W[op];
     if(["sin","cos","tan","cot","ln","log","lim","max","min"].includes(op))return op;
     // For unknown command, pronounce its letters/name rather than skip.
     return cmd.replace(/([a-z])([A-Z])/g,"$1 $2");
   }
   if(ch==="{")return parse("}",depth+1);
   if(ch==="^"||ch==="_"){
     const val=clean(nextGroup(depth));
     if(ch==="^"){
       if(val==="2")return W.squared;
       if(val==="3")return W.cubed;
       return W.power+" "+val;
     }
     return W.sub+" "+val;
   }
   if(ch==="\\n"||ch==="&")return " ";
   if(ch==="'" )return isEnglish(locale)?"prime":"phẩy";
   if(symbolKeys[ch]){
     if(ch==="-" && (i===1||/[(=+\-*/^,{]/.test(s[i-2]||"")))return W.negative;
     return W[symbolKeys[ch]]||ch;
   }
   if(/[0-9]/.test(ch)){
     let token=ch;
     while(i<s.length && /[0-9.,]/.test(s[i])) token+=s[i++];
     return token.replace(/[.,]$/,"");
   }
   if(/[a-zA-Z]/.test(ch)){
     let token=ch;
     while(i<s.length&&/[a-zA-Z]/.test(s[i]))token+=s[i++];
     if(token==="const")return W.isconstant;
     if(token==="pV")return "p "+W.times+" V";
     if(token==="PV")return "P "+W.times+" V";
     return token;
   }
   if(ch==="\\\\"){ if(s[i]==="\\\\")i++; return ", ";}
   if(/[,:;!]/.test(ch))return ",";
   return ch===" "?" ":ch;
 }
 function parse(stop=null,depth=0){
   if(depth>25)return "";
   const terms=[];
   while(i<s.length){
     if(stop && s[i]===stop){i++;break;}
     const token=clean(parseOne(depth+1));
     if(token)terms.push(token);
   }
   return terms.join(" ");
 }
 const read=clean(parse());
 return read.replace(/\s+,/g,",").replace(/,\s*,/g,",");
}
function mathMLToSpeech(root,locale){
 if(!root)return "";
 const W=words(locale);
 function walk(n,depth=0){
   if(!n||depth>22)return "";
   if(n.nodeType===3)return clean(n.nodeValue);
   const tag=String(n.localName||n.nodeName||"").toLowerCase();
   const cs=Array.from(n.children||[]);
   const child=(i)=>walk(cs[i],depth+1);
   const all=()=>clean(cs.map(c=>walk(c,depth+1)).join(" "));
   if(tag==="annotation"||tag==="annotation-xml"||tag==="mjx-assistive-mml")return "";
   if(tag==="mfrac")return [W.fraction,child(0),W.over,child(1)].join(" ");
   if(tag==="msqrt")return [W.root,all()].join(" ");
   if(tag==="mroot")return [W.nthroot,child(1),W.of,child(0)].join(" ");
   if(tag==="msup")return [child(0),child(1)==="2"?W.squared:child(1)==="3"?W.cubed:W.power+" "+child(1)].join(" ");
   if(tag==="msub")return [child(0),W.sub,child(1)].join(" ");
   if(tag==="msubsup")return [child(0),W.sub,child(1),W.power,child(2)].join(" ");
   if(tag==="mover")return [W.vector,child(0)].join(" ");
   if(tag==="munder"||tag==="munderover")return all();
   if(tag==="mi"||tag==="mn"||tag==="mo"||tag==="mtext"){
     return mathToSpeech(n.textContent||"",locale);
   }
   return all()||clean(n.textContent);
 }
 return clean(walk(root));
}
function texFromMathJaxItem(el){
 const mj=window.MathJax;
 const doc=mj?.startup?.document;
 if(!doc)return "";
 let candidates=[];
 try{
   if(typeof doc.getMathItemsWithin==="function")candidates=doc.getMathItemsWithin([el])||[];
 }catch(e){}
 try{
   const ml=doc.math;
   if(ml){
     if(typeof ml.toArray==="function")candidates.push(...ml.toArray());
     else if(typeof ml[Symbol.iterator]==="function")candidates.push(...ml);
     else if(Array.isArray(ml))candidates.push(...ml);
     else if(ml.list && Array.isArray(ml.list))candidates.push(...ml.list);
   }
 }catch(e){}
 for(const item of candidates){
   if(!item)continue;
   let root=item.typesetRoot||item.root||item.start?.node;
   if(root===el || (root?.contains && root.contains(el)) || (el.contains && el.contains(root))){
     if(typeof item.math==="string"&&item.math.trim())return item.math;
   }
 }
 return "";
}
function formulaSource(el){
 if(!el)return "";
 for(const name of ["data-ll-tex","data-tex","data-latex","data-math","data-mathml"]){
   const v=el.getAttribute?.(name);
   if(v&&v.trim())return v.trim();
 }
 const annotation=el.querySelector?.(
  'annotation[encoding="application/x-tex"],annotation[encoding="application/x-latex"],script[type^="math/tex"]');
 if(annotation?.textContent?.trim())return annotation.textContent.trim();
 const direct=texFromMathJaxItem(el);
 if(direct)return direct;
 return "";
}
function prepareElement(root){
 if(!root?.querySelectorAll)return;
 const selectors='mjx-container,.katex,math,.MathJax,script[type^="math/tex"]';
 const nodes=[];
 if(root.matches?.(selectors))nodes.push(root);
 nodes.push(...root.querySelectorAll(selectors));
 for(const el of nodes){
   if(el.hasAttribute?.("data-ll-tex"))continue;
   const value=formulaSource(el);
   if(value)el.setAttribute?.("data-ll-tex",value);
 }
}
function formulaSpeak(el,locale){
 if(!el)return "";
 const raw=formulaSource(el);
 if(raw){
   if(raw.trim().startsWith("<math"))return mathMLToSpeech(el.querySelector?.("math"),locale);
   return mathToSpeech(raw,locale);
 }
 const mml=el.matches?.("math")?el:el.querySelector?.("math,mjx-assistive-mml math,.katex-mathml math");
 if(mml)return mathMLToSpeech(mml,locale);
 const label=el.getAttribute?.("aria-label")||el.querySelector?.("[aria-label]")?.getAttribute("aria-label");
 if(label)return clean(label);
 if(el.matches?.("img,svg,canvas,.tikzfig,.tikz-row,.immini")){
   const alt=el.getAttribute?.("alt")||el.getAttribute?.("aria-label")||"";
   return alt|| (isEnglish(locale)?"illustration":"hình minh họa");
 }
 return clean(el.textContent||"");
}
function textToSpeech(text,locale,marks={}){
 let s=String(text||"");
 // MathJax markers must be expanded BEFORE deleting punctuation or commands.
 s=s.replace(MARKER,mark=>{
   const el=marks?.[mark];
   return el?" "+(formulaSpeak(el,locale)|| (isEnglish(locale)?"mathematical expression":"biểu thức toán học"))+" ":" ";
 });
 s=s.replace(/\$\$([\s\S]*?)\$\$/g,(_,m)=>" "+mathToSpeech(m,locale)+" ");
 s=s.replace(/\\\[([\s\S]*?)\\\]/g,(_,m)=>" "+mathToSpeech(m,locale)+" ");
 s=s.replace(/\\\(([\s\S]*?)\\\)/g,(_,m)=>" "+mathToSpeech(m,locale)+" ");
 s=s.replace(/\$([^$\n]+)\$/g,(_,m)=>" "+mathToSpeech(m,locale)+" ");
 // Raw LaTeX can appear without delimiters in learner text.
 s=s.replace(/\\(?:frac|dfrac|tfrac|sqrt|vec|overrightarrow|Delta|pi|theta|alpha|mathrm)\b(?:\{[^{}]*\}){0,2}/g,
   value=>" "+mathToSpeech(value,locale)+" ");
 s=s.replace(/(\d+(?:[.,]\d+)?)\s*°\s*C\b/gi,(_,n)=>n+" "+(isEnglish(locale)?"degrees Celsius":"độ C"));
 return clean(s.replace(/⟦(?:M|IMG)\d+⟧/g," ").replace(/\s+([,.;!?])/g,"$1"));
}
function chunks(text,max=170){
 const src=clean(text);
 if(!src)return [];
 const out=[];
 let rest=src;
 while(rest.length){
   if(rest.length<=max){out.push(rest);break;}
   let split=-1;
   for(const punctuation of [". ","? ","! ","; ",", "," "]) {
     const n=rest.lastIndexOf(punctuation,max);
     if(n>=Math.floor(max*.48)){split=n+punctuation.length;break;}
   }
   if(split<0)split=max;
   out.push(rest.slice(0,split).trim());
   rest=rest.slice(split).trim();
 }
 return out.filter(Boolean);
}
window.ldvlMathSpeech={
 mathToSpeech, textToSpeech, formulaSpeak, formulaSource,
 prepareElement, chunks, mathMLToSpeech
};
})();