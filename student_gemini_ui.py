# -*- coding: utf-8 -*-
"""UI for entering a student's own Gemini API key in the browser."""
from flask import request
from app import app


@app.after_request
def student_gemini_ui(response):
    if request.path != '/member/practice' or 'text/html' not in response.headers.get('Content-Type', ''):
        return response
    try:
        body = response.get_data(as_text=True)
        patch = r'''<script>
(function(){
  function key(){return localStorage.getItem('student_gemini_api_key')||'';}
  function saveKey(){
    var x=document.getElementById('studentGeminiKey');
    if(!x)return;
    var v=x.value.trim();
    if(!v){alert('Hãy nhập Gemini API key.');return;}
    localStorage.setItem('student_gemini_api_key',v);
    closeKey();
    toastKey('✅ Đã lưu key trên thiết bị này');
  }
  function openKey(){
    var old=key();
    var box=document.getElementById('studentKeyModal');
    if(!box){
      box=document.createElement('div');box.id='studentKeyModal';box.className='sgm-backdrop';
      box.innerHTML='<div class="sgm-box"><div class="sgm-title">🔑 Gemini API key của học sinh</div><div class="sgm-note">Key chỉ lưu trong trình duyệt của học sinh và chỉ gửi cùng lúc bấm phản biện. Không lưu vào Google Sheet hoặc GitHub.</div><input id="studentGeminiKey" type="password" placeholder="Dán Gemini API key vào đây"><div class="sgm-actions"><button class="btn" type="button" onclick="closeStudentGeminiKey()">Hủy</button><button class="btn red" type="button" onclick="clearStudentGeminiKey()">Xóa key</button><button class="btn primary" type="button" onclick="saveStudentGeminiKey()">💾 Lưu trên máy này</button></div></div>';
      document.body.appendChild(box);
    }
    document.getElementById('studentGeminiKey').value=old;box.style.display='flex';
  }
  function closeKey(){var b=document.getElementById('studentKeyModal');if(b)b.style.display='none';}
  function clearKey(){localStorage.removeItem('student_gemini_api_key');var x=document.getElementById('studentGeminiKey');if(x)x.value='';toastKey('🗑️ Đã xóa key');}
  function toastKey(msg){var d=document.createElement('div');d.className='sgm-toast';d.textContent=msg;document.body.appendChild(d);setTimeout(function(){d.remove();},2200);}
  window.openStudentGeminiKey=openKey;window.closeStudentGeminiKey=closeKey;window.saveStudentGeminiKey=saveKey;window.clearStudentGeminiKey=clearKey;

  window.askGemini=function(){
    var k=key();
    if(!k){openKey();return;}
    var q=(typeof Q!=='undefined')?Q:{};
    var out=document.getElementById('geminiOut');if(!out)return;
    out.textContent='⏳ Gemini đang phản biện...';
    fetch('/api/gemini/review_student',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      api_key:k,text:q.text||'',student:(typeof studentAnswer==='function'?studentAnswer():''),solution:q.solution||'',kind:q.kind||'',dang:q.dang||'',level:q.level||''
    })}).then(function(r){return r.json();}).then(function(d){
      if(!d.ok){out.textContent='❌ '+(d.error||'Không gọi được Gemini');return;}
      out.textContent=d.text||'';
      var b=document.getElementById('speakReview');if(b)b.style.display='inline-block';
      if(window.MathJax)MathJax.typesetPromise([out]);
    }).catch(function(e){out.textContent='❌ '+e;});
  };

  function install(){
    var tools=document.getElementById('practiceTools');
    if(!tools || document.getElementById('studentGeminiKeyBtn'))return;
    var b=document.createElement('button');b.type='button';b.id='studentGeminiKeyBtn';b.className='btn';b.textContent='🔑 Gemini key';b.onclick=openKey;
    tools.insertBefore(b,tools.firstChild);
  }
  document.addEventListener('DOMContentLoaded',function(){
    install();
    var obs=new MutationObserver(install);obs.observe(document.body,{childList:true,subtree:true});
    document.addEventListener('click',function(e){if(e.target&&e.target.id==='studentKeyModal' )closeKey();});
  });
})();
</script>
<style>
.sgm-backdrop{position:fixed;inset:0;background:rgba(20,35,55,.48);display:none;align-items:center;justify-content:center;z-index:99999;padding:16px}
.sgm-box{width:min(560px,96vw);background:#fff;border:1px solid #cbd8e6;border-radius:12px;box-shadow:0 16px 45px rgba(0,0,0,.22);padding:18px}
.sgm-title{font-size:18px;font-weight:900;margin-bottom:8px}.sgm-note{font-size:13px;color:#5d7084;line-height:1.55;margin-bottom:12px}.sgm-box input{width:100%;padding:11px;border:1px solid #cbd8e6;border-radius:8px;font:14px Segoe UI,Arial}.sgm-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:12px}.sgm-toast{position:fixed;right:18px;bottom:18px;z-index:100000;background:#17324f;color:#fff;border-radius:9px;padding:10px 13px;box-shadow:0 5px 20px rgba(0,0,0,.2);font-weight:800}
</style>'''
        response.set_data(body.replace('</body>',patch+'</body>'))
    except Exception:
        pass
    return response
