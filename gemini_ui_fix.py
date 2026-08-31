# -*- coding: utf-8 -*-
"""Reliable student Gemini-key UI override.
The student's own Gemini key is kept in browser localStorage and sent only for review requests.
"""
from flask import request
from app import app

@app.after_request
def inject_student_gemini_key_ui(response):
    if request.path != '/member/practice' or 'text/html' not in response.headers.get('Content-Type', ''):
        return response
    try:
        body = response.get_data(as_text=True)
        patch = r'''<script>
(function(){
  const KEY='student_gemini_api_key';
  function getKey(){return localStorage.getItem(KEY)||'';}
  function showKey(){
    let old=document.getElementById('sgkModal');
    if(!old){
      old=document.createElement('div'); old.id='sgkModal'; old.className='sgk-bg';
      old.innerHTML='<div class="sgk-box"><div class="sgk-title">🔑 Nạp Gemini API key</div><div class="sgk-note">Học sinh tự nhập key Gemini của mình. Key chỉ lưu trên trình duyệt này, không lưu vào GitHub hay Google Sheet.</div><input id="sgkInput" type="password" autocomplete="off" placeholder="Dán Gemini API key vào đây"><div class="sgk-actions"><button class="btn" type="button" onclick="window.closeStudentKey()">Hủy</button><button class="btn red" type="button" onclick="window.clearStudentKey()">Xóa key</button><button class="btn primary" type="button" onclick="window.saveStudentKey()">💾 Lưu key</button></div></div>';
      document.body.appendChild(old);
    }
    document.getElementById('sgkInput').value=getKey(); old.style.display='flex';
  }
  window.closeStudentKey=function(){let x=document.getElementById('sgkModal');if(x)x.style.display='none';};
  window.saveStudentKey=function(){let x=document.getElementById('sgkInput');let v=(x.value||'').trim();if(!v){alert('Hãy dán Gemini API key.');return;}localStorage.setItem(KEY,v);window.closeStudentKey();};
  window.clearStudentKey=function(){localStorage.removeItem(KEY);let x=document.getElementById('sgkInput');if(x)x.value='';};
  window.openStudentGeminiKey=showKey;
  function studentAnswer(){
    if(typeof Q==='undefined')return '';
    if(Q.kind==='TN'){let z=document.querySelector('input[name=a]:checked');return z?String.fromCharCode(65+(+z.value)):'';}
    if(Q.kind==='DS'){let a=[];(Q.statements||[]).forEach(function(s,i){let z=document.querySelector('input[name=t'+i+']:checked');a.push(z?(z.value==='1'?'Đ':'S'):'?');});return a.join('');}
    let x=document.getElementById('ans');return x?(x.value||'').trim():'';
  }
  window.askGemini=function(){
    let out=document.getElementById('geminiOut'); if(!out)return;
    let k=getKey(); if(!k){showKey(); return;}
    let q=(typeof Q!=='undefined')?Q:{};
    out.textContent='⏳ Gemini đang phản biện...';
    fetch('/api/gemini/review_student',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:k,text:q.text||'',student:studentAnswer(),solution:q.solution||'',kind:q.kind||'',dang:q.dang||'',level:q.level||''})})
      .then(r=>r.json()).then(d=>{if(!d.ok){out.textContent='❌ '+(d.error||'Gemini không phản hồi');return;}out.textContent=d.text||'';let b=document.getElementById('speakReview');if(b)b.style.display='inline-block';if(window.MathJax)MathJax.typesetPromise([out]);})
      .catch(e=>out.textContent='❌ '+e);
  };
  function install(){
    let tools=document.getElementById('practiceTools'); if(!tools)return;
    if(!document.getElementById('studentGeminiKeyBtn')){
      let b=document.createElement('button'); b.id='studentGeminiKeyBtn'; b.type='button'; b.className='btn'; b.textContent='🔑 Nạp key Gemini'; b.onclick=showKey; tools.insertBefore(b,tools.firstChild);
    }
  }
  function boot(){install();let obs=new MutationObserver(install);obs.observe(document.body,{childList:true,subtree:true});setTimeout(install,300);setTimeout(install,1000);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
</script><style>
.sgk-bg{position:fixed;inset:0;background:rgba(15,30,50,.48);display:none;align-items:center;justify-content:center;z-index:100000;padding:16px}
.sgk-box{width:min(560px,95vw);background:#fff;border:1px solid #cbd8e6;border-radius:12px;padding:18px;box-shadow:0 18px 50px rgba(0,0,0,.25)}
.sgk-title{font-size:19px;font-weight:900;margin-bottom:6px}.sgk-note{font-size:13px;color:#607387;line-height:1.55;margin-bottom:12px}.sgk-box input{width:100%;padding:11px;border:1px solid #cbd8e6;border-radius:8px;font:14px Segoe UI,Arial}.sgk-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:12px}
</style>'''
        response.set_data(body.replace('</body>', patch + '</body>'))
    except Exception:
        pass
    return response
