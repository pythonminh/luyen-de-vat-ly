# -*- coding: utf-8 -*-
"""Student-owned Gemini API key UI.

The key is stored only in this browser's localStorage and is sent to the
student-only Gemini endpoint for a review request. It is never written to
members.json, Google Sheet, or GitHub.
"""
from flask import request
from app import app


@app.after_request
def student_gemini_ui(response):
    if request.path != '/member/practice' or 'text/html' not in response.headers.get('Content-Type', ''):
        return response
    try:
        body = response.get_data(as_text=True)
        patch = r'''
<div id="studentGeminiPanel" class="sgm-panel">
  <button type="button" class="btn" onclick="openStudentGeminiKey()">🔑 Nạp key Gemini</button>
  <span id="sgmStatus" class="sgm-status">Chưa nạp key</span>
</div>
<div id="studentKeyModal" class="sgm-backdrop" style="display:none">
  <div class="sgm-box">
    <div class="sgm-title">🔑 Nạp Gemini API key</div>
    <div class="sgm-note">
      Học sinh tự nhập Gemini API key của mình. Key chỉ được lưu trong trình duyệt này,
      không lưu vào Google Sheet hay GitHub.
    </div>
    <input id="studentGeminiKey" type="password" autocomplete="off"
           placeholder="Dán Gemini API key vào đây">
    <div class="sgm-actions">
      <button class="btn" type="button" onclick="closeStudentGeminiKey()">Hủy</button>
      <button class="btn red" type="button" onclick="clearStudentGeminiKey()">🗑 Xóa key</button>
      <button class="btn primary" type="button" onclick="saveStudentGeminiKey()">💾 Lưu key</button>
    </div>
    <div id="sgmMessage" class="sgm-message"></div>
  </div>
</div>
<script>
(function(){
  const KEY_NAME='student_gemini_api_key';
  const keyValue=()=>localStorage.getItem(KEY_NAME)||'';
  const status=()=>document.getElementById('sgmStatus');
  function refreshStatus(){
    const ok=!!keyValue();
    if(status()) status.textContent=ok?'✅ Đã nạp key':'Chưa nạp key';
  }
  function openKey(){
    const box=document.getElementById('studentKeyModal');
    const input=document.getElementById('studentGeminiKey');
    const msg=document.getElementById('sgmMessage');
    if(!box||!input)return;
    input.value=keyValue();
    if(msg)msg.textContent='';
    box.style.display='flex';
    setTimeout(()=>input.focus(),30);
  }
  function closeKey(){
    const box=document.getElementById('studentKeyModal');
    if(box)box.style.display='none';
  }
  function saveKey(){
    const input=document.getElementById('studentGeminiKey');
    const msg=document.getElementById('sgmMessage');
    const value=(input?.value||'').trim();
    if(!value){if(msg)msg.textContent='❌ Hãy dán Gemini API key.';return;}
    if(value.length<20){if(msg)msg.textContent='❌ Key có vẻ quá ngắn.';return;}
    localStorage.setItem(KEY_NAME,value);
    refreshStatus();
    if(msg)msg.textContent='✅ Đã lưu key trên trình duyệt này.';
    setTimeout(closeKey,500);
  }
  function clearKey(){
    localStorage.removeItem(KEY_NAME);
    const input=document.getElementById('studentGeminiKey');
    const msg=document.getElementById('sgmMessage');
    if(input)input.value='';
    refreshStatus();
    if(msg)msg.textContent='🗑 Đã xóa key.';
  }
  function askWithStudentKey(){
    const key=keyValue();
    if(!key){openKey();return;}
    const q=(typeof Q!=='undefined')?Q:{};
    const out=document.getElementById('geminiOut');
    if(!out){alert('Chưa có vùng phản biện.');return;}
    let student='';
    if(typeof studentAnswer==='function') student=studentAnswer();
    out.textContent='⏳ Gemini đang phản biện...';
    fetch('/api/gemini/review_student',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({api_key:key,text:q.text||'',student:student,
        solution:q.solution||'',kind:q.kind||'',dang:q.dang||'',level:q.level||''})
    }).then(r=>r.json()).then(d=>{
      if(!d.ok){out.textContent='❌ '+(d.error||'Không gọi được Gemini');return;}
      out.textContent=d.text||'';
      const speak=document.getElementById('speakReview');
      if(speak)speak.style.display='inline-block';
      if(window.MathJax) MathJax.typesetPromise([out]);
    }).catch(e=>{out.textContent='❌ '+e;});
  }
  window.openStudentGeminiKey=openKey;
  window.closeStudentGeminiKey=closeKey;
  window.saveStudentGeminiKey=saveKey;
  window.clearStudentGeminiKey=clearKey;
  window.askStudentGemini=askWithStudentKey;
  document.addEventListener('DOMContentLoaded',function(){
    refreshStatus();
    const old=document.getElementById('studentKeyModal');
    if(old)old.addEventListener('click',e=>{if(e.target===old)closeKey();});
  });
  if(document.readyState!=='loading') refreshStatus();
})();
</script>
<style>
.sgm-panel{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin:0 0 10px 0;padding:9px 11px;border:1px solid #cbd8e6;border-radius:9px;background:#f8fbff}
.sgm-status{font-size:12px;font-weight:800;color:#6b7b8d}
.sgm-backdrop{position:fixed;inset:0;background:rgba(20,35,55,.48);align-items:center;justify-content:center;z-index:99999;padding:16px}
.sgm-box{width:min(560px,96vw);background:#fff;border:1px solid #cbd8e6;border-radius:12px;box-shadow:0 16px 45px rgba(0,0,0,.22);padding:18px}
.sgm-title{font-size:19px;font-weight:900;margin-bottom:8px}.sgm-note{font-size:13px;color:#5d7084;line-height:1.55;margin-bottom:12px}
.sgm-box input{width:100%;padding:11px;border:1px solid #cbd8e6;border-radius:8px;font:14px Segoe UI,Arial}
.sgm-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:12px}.sgm-message{margin-top:9px;font-weight:800;color:#176bd3}
</style>
'''
        marker='</body>'
        if 'id="studentGeminiPanel"' not in body:
            body=body.replace(marker, patch+marker)
        response.set_data(body)
    except Exception:
        pass
    return response
