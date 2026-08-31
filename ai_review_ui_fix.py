# -*- coding: utf-8 -*-
from app import app

JS = r'''<script id="LDVL_AI_REVIEW_UI_FIX_V4">
(function(){
if(window.__LDVL_AI_REVIEW_UI_FIX_V4__)return;window.__LDVL_AI_REVIEW_UI_FIX_V4__=true;
function isAdmin(){try{return!!(window.USER&&(USER.is_admin||String(USER.role||'').toUpperCase()==='ADMIN'))}catch(e){return false}}
function provider(){try{var p=localStorage.getItem('LDVL_REVIEW_PROVIDER_V4');if(['GEMINI','CLAUDE','OPENAI','AUTO'].includes(p))return p}catch(e){}try{var p=String((typeof adminAiProvider==='function'?adminAiProvider():'GEMINI')||'GEMINI').toUpperCase();if(['GEMINI','CLAUDE','OPENAI','AUTO'].includes(p))return p}catch(e){}return'GEMINI'}
function setProvider(p){try{localStorage.setItem('LDVL_REVIEW_PROVIDER_V4',p)}catch(e){}try{if(typeof setAdminAiRuntimeProvider==='function')setAdminAiRuntimeProvider(p)}catch(e){}}
function typeset(root){try{if(!root||!window.MathJax||!MathJax.typesetPromise)return;if(MathJax.typesetClear)MathJax.typesetClear([root]);MathJax.typesetPromise([root]).catch(function(){})}catch(e){}}
function mathFixText(t){t=String(t==null?'':t);t=t.replace(/\\\\/g,'\\').replace(/\\\[/g,'$$').replace(/\\\]/g,'$$').replace(/\\\(/g,'$').replace(/\\\)/g,'$');return t}
function addBareMathDelims(t){
 t=mathFixText(t);
 if(!t||t.indexOf('$')>=0)return t;
 // Các biểu thức thường bị AI trả ra không có dấu $.
 t=t.replace(/\b([A-Za-z](?:_[A-Za-z0-9]+)?\s*=\s*[^.!?\n]{1,140}(?:\\(?:infty|cup|cap|le|ge|leq|geq|frac|dfrac|sqrt|times|cdot|pm|pi|forall|exists)[^.!?\n]{0,120})[^.!?\n]*)/g,function(_,x){return '$'+x.trim()+'$'});
 t=t.replace(/\b([A-Za-z](?:_[A-Za-z0-9]+)?\s*=\s*[-+]?\d+(?:[.,]\d+)?)/g,function(_,x){return '$'+x.trim()+'$'});
 t=t.replace(/\b(\\(?:infty|alpha|beta|gamma|Delta|pi|le|ge|leq|geq|times|cdot|pm))\b/g,function(_,x){return '$'+x+'$'});
 return t;
}
function normalizeDom(root){if(!root)return;var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null,false),a=[];while(w.nextNode())a.push(w.currentNode);a.forEach(function(n){var p=n.parentElement;if(!p||/^(SCRIPT|STYLE|TEXTAREA|CODE|PRE)$/.test(p.tagName))return;var t=addBareMathDelims(n.nodeValue);if(t!==n.nodeValue)n.nodeValue=t})}
function cardKind(el){var t=String(el.textContent||'');if(/\bClaude\b|Anthropic/i.test(t))return'CLAUDE';if(/\bGemini\b|Google AI/i.test(t))return'GEMINI';if(/\bGPT\b|ChatGPT|OpenAI/i.test(t))return'OPENAI';if(/Trợ lý\s*AI\s*thầy\s*Minh/i.test(t))return'ASSISTANT';return''}
function filterCards(){if(!isAdmin())return;var root=document.getElementById('hintBox');if(!root)return;var p=provider();Array.prototype.slice.call(root.children||[]).forEach(function(el){var k=cardKind(el);if(!k)return;el.style.display=(p==='AUTO'||(k!=='ASSISTANT'&&k===p))?'':'none'});normalizeDom(root);typeset(root)}
function ensureSelector(){if(!isAdmin()||document.getElementById('ldvlAiReviewSelectorV4'))return;var host=document.getElementById('quizAdminTools')||document.querySelector('.quizAdminTools')||document.getElementById('quizActions');if(!host)return;var w=document.createElement('span');w.id='ldvlAiReviewSelectorV4';w.style.cssText='display:inline-flex;align-items:center;gap:5px;margin-left:6px;padding:4px 7px;border:1px solid #93c5fd;border-radius:8px;background:#eff6ff';var l=document.createElement('span');l.textContent='🔍 反辩 AI:';l.style.cssText='font-size:11px;font-weight:900;color:#1e3a8a';var s=document.createElement('select');s.id='ldvlAiReviewProviderV4';s.style.cssText='font-size:11px;padding:4px 7px;border:1px solid #93c5fd;border-radius:7px;background:#fff;color:#1e3a8a';[['GEMINI','Gemini'],['CLAUDE','Claude'],['OPENAI','GPT'],['AUTO','Tự động']].forEach(function(x){var o=document.createElement('option');o.value=x[0];o.textContent=x[1];s.appendChild(o)});s.value=provider();s.onchange=function(){setProvider(s.value);try{if(typeof HINT_BY_Q!=='undefined')delete HINT_BY_Q[CUR]}catch(e){}try{if(typeof requestHint==='function')requestHint()}catch(e){}};w.appendChild(l);w.appendChild(s);host.appendChild(w)}
function run(){ensureSelector();filterCards();var q=document.getElementById('quiz');if(q){var o=new MutationObserver(function(){ensureSelector();filterCards()});o.observe(q,{subtree:true,childList:true,characterData:true})}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
</script>'''

@app.after_request
def ldvl_ai_review_ui_fix(response):
 try:
  if response.content_type and 'text/html' in response.content_type:
   text=response.get_data(as_text=True)
   if 'LDVL_AI_REVIEW_UI_FIX_V4' not in text:
    pos=text.lower().rfind('</body>')
    text=text[:pos]+JS+text[pos:] if pos>=0 else text+JS
    response.set_data(text)
 except Exception:
  pass
 return response
