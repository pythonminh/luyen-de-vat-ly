# -*- coding: utf-8 -*-
from flask import Response
from app import app

JS = r'''<script id="LDVL_AI_REVIEW_UI_FIX_V2">
(function(){
  if(window.__LDVL_AI_REVIEW_UI_FIX_V2__) return;
  window.__LDVL_AI_REVIEW_UI_FIX_V2__=true;

  function admin(){
    try{return !!(window.USER && (USER.is_admin || String(USER.role||'').toUpperCase()==='ADMIN'));}
    catch(e){return false}
  }
  function provider(){
    try{var p=localStorage.getItem('LDVL_REVIEW_PROVIDER_V2');if(['GEMINI','CLAUDE','OPENAI','AUTO'].includes(p))return p}catch(e){}
    try{var p=String((typeof adminAiProvider==='function'?adminAiProvider():'GEMINI')||'GEMINI').toUpperCase();if(['GEMINI','CLAUDE','OPENAI','AUTO'].includes(p))return p}catch(e){}
    return 'GEMINI';
  }
  function saveProvider(p){try{localStorage.setItem('LDVL_REVIEW_PROVIDER_V2',p)}catch(e){}}
  function mj(root){
    try{
      if(!root||!window.MathJax||!MathJax.typesetPromise)return;
      if(MathJax.typesetClear) MathJax.typesetClear([root]);
      MathJax.typesetPromise([root]).catch(function(){});
    }catch(e){}
  }
  function normalizeMathText(s){
    s=String(s==null?'':s);
    s=s.replace(/\\\\/g,'\\');
    s=s.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>');
    s=s.replace(/\\\[/g,'$$').replace(/\\\]/g,'$$');
    s=s.replace(/\\\(/g,'$').replace(/\\\)/g,'$');
    return s;
  }
  function wrapBareMath(root){
    if(!root)return;
    var walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null,false), nodes=[];
    while(walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function(n){
      var p=n.parentElement;if(!p||/^(SCRIPT|STYLE|TEXTAREA|OPTION|CODE|PRE)$/.test(p.tagName))return;
      var t=n.nodeValue;if(!t||!/[\\^_]/.test(t))return;
      t=normalizeMathText(t);
      // Chỉ bọc các biểu thức LaTeX rõ ràng, không đụng URL hoặc text thường.
      t=t.replace(/(^|[^$A-Za-z0-9])((?:\\(?:frac|dfrac|sqrt|sin|cos|tan|cot|log|ln|left|right|leq|geq|times|cdot|pm|pi|infty|forall|exists|ge|le)|[A-Za-z])[^$\n]{0,120}(?:\^[^$\n]{1,20}|_[^$\n]{1,20}|\\(?:frac|dfrac|sqrt)\{)[^$\n]{0,160})(?=$|[^A-Za-z0-9])/g,function(m,a,x){return a+'$'+x.trim()+'$'});
      if(t!==n.nodeValue)n.nodeValue=t;
    });
  }
  function fixMath(root){
    if(!root)return;
    wrapBareMath(root);
    mj(root);
  }
  function cardProvider(el){
    var t=String(el.textContent||'');
    if(/\\bClaude\\b|Anthropic/i.test(t))return'CLAUDE';
    if(/\\bGemini\\b|Google AI/i.test(t))return'GEMINI';
    if(/\\bGPT\\b|ChatGPT|OpenAI/i.test(t))return'OPENAI';
    return'';
  }
  function filterCards(){
    if(!admin())return;
    var root=document.getElementById('hintBox');if(!root)return;
    var p=provider();
    Array.prototype.slice.call(root.children||[]).forEach(function(el){
      var cp=cardProvider(el);if(!cp)return;
      el.style.display=(p==='AUTO'||p===cp)?'':'none';
    });
    fixMath(root);
  }
  function selector(){
    if(!admin())return;
    var host=document.getElementById('quizAdminTools')||document.getElementById('quizActions')||document.querySelector('.quizAdminTools');
    if(!host||document.getElementById('ldvlAiReviewSelector'))return;
    var w=document.createElement('span');w.id='ldvlAiReviewSelector';w.style.cssText='display:inline-flex;align-items:center;gap:5px;margin-left:6px;padding:4px 7px;border:1px solid #93c5fd;border-radius:8px;background:#eff6ff';
    var l=document.createElement('span');l.textContent='🔍 Phản biện:';l.style.cssText='font-size:11px;font-weight:900;color:#1e3a8a';
    var s=document.createElement('select');s.id='ldvlAiReviewProvider';s.style.cssText='font-size:11px;padding:4px 7px;border:1px solid #93c5fd;border-radius:7px;background:#fff;color:#1e3a8a';
    [['GEMINI','Gemini'],['CLAUDE','Claude'],['OPENAI','GPT'],['AUTO','Tự động']].forEach(function(x){var o=document.createElement('option');o.value=x[0];o.textContent=x[1];s.appendChild(o)});
    s.value=provider();s.title='Mỗi lần chỉ dùng AI được chọn';
    s.onchange=function(){var p=s.value;saveProvider(p);try{if(typeof setAdminAiRuntimeProvider==='function')setAdminAiRuntimeProvider(p)}catch(e){}try{if(typeof HINT_BY_Q!=='undefined')delete HINT_BY_Q[CUR]}catch(e){}filterCards();try{if(typeof requestHint==='function')requestHint()}catch(e){}};
    w.appendChild(l);w.appendChild(s);host.appendChild(w);
  }
  var obs=new MutationObserver(function(){selector();filterCards();var h=document.getElementById('hintBox');if(h)fixMath(h)});
  function boot(){selector();var h=document.getElementById('hintBox');if(h)fixMath(h);var q=document.getElementById('quiz');if(q)obs.observe(q,{subtree:true,childList:true,characterData:true})}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
  window.LDVL_fixAiReviewMath=fixMath;
})();
</script>'''

def _inject():
    try:
        src = getattr(app, 'view_functions', {})
        for fn in list(src.values()):
            try:
                if not callable(fn): continue
            except Exception: continue
        return Response(JS, mimetype='text/html')
    except Exception:
        return Response(JS, mimetype='text/html')

# This module is intentionally loaded only for side effects.  The real HTML is
# served by app.py; wsgi.py can append JS to pages through the normal restyle hook.
app.config['LDVL_AI_REVIEW_UI_FIX'] = True
