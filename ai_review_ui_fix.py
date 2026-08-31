# -*- coding: utf-8 -*-
from flask import Response
from app import app

JS = r'''<script id="LDVL_AI_REVIEW_UI_FIX_V3">
(function(){
  if(window.__LDVL_AI_REVIEW_UI_FIX_V3__) return;
  window.__LDVL_AI_REVIEW_UI_FIX_V3__=true;
  function isAdmin(){try{return !!(window.USER&&(USER.is_admin||String(USER.role||'').toUpperCase()==='ADMIN'));}catch(e){return false}}
  function provider(){try{var p=localStorage.getItem('LDVL_REVIEW_PROVIDER_V3');if(['GEMINI','CLAUDE','OPENAI','AUTO'].includes(p))return p}catch(e){}try{var p=String((typeof adminAiProvider==='function'?adminAiProvider():'GEMINI')||'GEMINI').toUpperCase();if(['GEMINI','CLAUDE','OPENAI','AUTO'].includes(p))return p}catch(e){}return'GEMINI'}
  function setProvider(p){try{localStorage.setItem('LDVL_REVIEW_PROVIDER_V3',p)}catch(e){}try{if(typeof setAdminAiRuntimeProvider==='function')setAdminAiRuntimeProvider(p)}catch(e){}}
  function math(root){try{if(!root||!window.MathJax||!MathJax.typesetPromise)return;if(MathJax.typesetClear)MathJax.typesetClear([root]);MathJax.typesetPromise([root]).catch(function(){})}catch(e){}}
  function normalizeText(t){t=String(t==null?'':t);t=t.replace(/\\\\/g,'\\');t=t.replace(/\\\[/g,'$$').replace(/\\\]/g,'$$');t=t.replace(/\\\(/g,'$').replace(/\\\)/g,'$');return t}
  function normalizeDom(root){if(!root)return;var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null,false),a=[];while(w.nextNode())a.push(w.currentNode);a.forEach(function(n){var p=n.parentElement;if(!p||/^(SCRIPT|STYLE|TEXTAREA|CODE|PRE)$/.test(p.tagName))return;var t=normalizeText(n.nodeValue);if(t!==n.nodeValue)n.nodeValue=t})}
  function cardKind(el){var t=String(el.textContent||'');if(/\bClaude\b|Anthropic/i.test(t))return'CLAUDE';if(/\bGemini\b|Google AI/i.test(t))return'GEMINI';if(/\bGPT\b|ChatGPT|OpenAI/i.test(t))return'OPENAI';return''}
  function filterCards(){if(!isAdmin())return;var root=document.getElementById('hintBox');if(!root)return;var p=provider();Array.prototype.slice.call(root.children||[]).forEach(function(el){var k=cardKind(el);if(!k)return;el.style.display=(p==='AUTO'||p===k)?'':'none'});normalizeDom(root);math(root)}
  function ensureSelector(){if(!isAdmin()||document.getElementById('ldvlAiReviewSelectorV3'))return;var host=document.getElementById('quizAdminTools')||document.querySelector('.quizAdminTools')||document.getElementById('quizActions');if(!host)return;var w=document.createElement('span');w.id='ldvlAiReviewSelectorV3';w.style.cssText='display:inline-flex;align-items:center;gap:6px;margin-left:6px;padding:4px 7px;border:1px solid #93c5fd;border-radius:8px;background:#eff6ff';var l=document.createElement('span');l.textContent='🔍 Phản biện:';l.style.cssText='font-size:11px;font-weight:900;color:#1e3a8a';var s=document.createElement('select');s.id='ldvlAiReviewProviderV3';s.style.cssText='font-size:11px;padding:4px 7px;border:1px solid #93c5fd;border-radius:7px;background:#fff;color:#1e3a8a';[['GEMINI','Gemini'],['CLAUDE','Claude'],['OPENAI','GPT'],['AUTO','Tự động']].forEach(function(x){var o=document.createElement('option');o.value=x[0];o.textContent=x[1];s.appendChild(o)});s.value=provider();s.title='Chọn một AI để phản biện câu hiện tại';s.onchange=function(){setProvider(s.value);try{if(typeof HINT_BY_Q!=='undefined')delete HINT_BY_Q[CUR]}catch(e){}try{if(typeof requestHint==='function')requestHint()}catch(e){}filterCards()};w.appendChild(l);w.appendChild(s);host.appendChild(w)}
  function run(){ensureSelector();filterCards();var h=document.getElementById('hintBox');if(h){normalizeDom(h);math(h)}var q=document.getElementById('quiz');if(q){var o=new MutationObserver(function(){ensureSelector();filterCards()});o.observe(q,{subtree:true,childList:true,characterData:true})}}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
</script>'''

@app.after_request
def ldvl_ai_review_ui_fix(response):
    try:
        if response.content_type and 'text/html' in response.content_type:
            text=response.get_data(as_text=True)
            if 'LDVL_AI_REVIEW_UI_FIX_V3' not in text:
                pos=text.lower().rfind('</body>')
                if pos>=0:
                    text=text[:pos]+JS+text[pos:]
                else:
                    text += JS
                response.set_data(text)
    except Exception:
        pass
    return response
