# -*- coding: utf-8 -*-
"""Single final UI layer for Render.

Keeps public/student pages clean and makes the header consistent across
laptop, tablet and phone. GitHub is exposed only in the authenticated ADMIN
area. Student Gemini controls are shown only on the practice page.
"""
from __future__ import annotations

import re
from flask import request, session
from app import app


BRAND = "📚 Luyện Đề Toán Lý"
SUBTITLE = "Zalo thầy Minh 0946111107"


CSS = r'''
<style>
/* ===== FINAL RESPONSIVE UI ===== */
.topin{width:100%;max-width:1500px;margin:0 auto;padding:9px 14px;display:flex;align-items:center;gap:12px;box-sizing:border-box}
.brand{font-weight:900;font-size:20px;line-height:1.2;white-space:nowrap}
.sub{font-size:11px;line-height:1.25;opacity:.92}
.nav{margin-left:auto;display:flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:nowrap}
.nav a,.nav button{white-space:nowrap}
.nav button{font:inherit;color:#fff;border:1px solid #ffffff66;background:#ffffff18;padding:7px 10px;border-radius:8px;font-weight:900;cursor:pointer}
.nav button:hover{background:#ffffff2b}
.ltdl-gemini-key{border-color:#ffe08a!important}
.ltdl-gemini-ai{border-color:#8fe1b0!important}
.ltdl-key-modal{position:fixed;inset:0;background:rgba(12,28,48,.52);display:none;align-items:center;justify-content:center;z-index:100000;padding:16px}
.ltdl-key-box{width:min(560px,96vw);background:#fff;color:#19324d;border:1px solid #cbd8e6;border-radius:12px;box-shadow:0 18px 50px rgba(0,0,0,.25);padding:18px}
.ltdl-key-title{font-size:19px;font-weight:900;margin-bottom:7px}
.ltdl-key-note{font-size:13px;color:#607387;line-height:1.55;margin-bottom:12px}
.ltdl-key-input{width:100%;padding:11px;border:1px solid #cbd8e6;border-radius:8px;font:14px Segoe UI,Arial;box-sizing:border-box}
.ltdl-key-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:12px}
.ltdl-key-status{font-size:11px;margin-left:3px}
/* Four compact question-type counters: TN / ĐS / TLN / TL */
.dangrow{display:grid!important;grid-template-columns:minmax(0,1fr) auto!important;align-items:center!important;gap:7px!important;padding:5px 3px!important;min-height:34px!important}
.dangrow>span:first-child{min-width:0;line-height:1.3;font-size:12px}
.dangrow .tag{margin:0 2px!important;padding:3px 7px!important;font-size:10px!important;white-space:nowrap!important;line-height:1.1!important}
@media(max-width:900px){
 .topin{padding:8px 10px;align-items:flex-start;flex-wrap:wrap;gap:7px}
 .topin>div:first-child{min-width:0;flex:1 1 100%}
 .brand{font-size:18px;white-space:normal}
 .sub{font-size:10px}
 .nav{width:100%;margin-left:0;justify-content:flex-start;flex-wrap:wrap}
 .nav a,.nav button{padding:6px 9px;font-size:12px}
}
@media(max-width:480px){
 .topin{padding:7px 8px}
 .brand{font-size:16px}
 .sub{font-size:10px}
 .nav{gap:4px}
 .nav a,.nav button{padding:6px 7px;font-size:11px}
 .wrap{padding:8px!important}
 .qtext{font-size:17px!important}
 .ltdl-key-box{padding:14px}
 .ltdl-key-actions{justify-content:stretch}
 .ltdl-key-actions button{flex:1}
}
</style>
'''


KEY_JS = r'''
<script>
(function(){
  const KEY='student_gemini_api_key';
  function val(){return localStorage.getItem(KEY)||'';}
  function status(){
    const s=document.getElementById('ltdlKeyStatus');
    if(s)s.textContent=val()?'✓':'—';
    const b=document.getElementById('ltdlGeminiKey');
    if(b)b.title=val()?'Đã nạp Gemini API key':'Nạp Gemini API key';
  }
  function openKey(){
    const m=document.getElementById('ltdlKeyModal');
    const i=document.getElementById('ltdlKeyInput');
    if(!m||!i)return;
    i.value=val();m.style.display='flex';setTimeout(()=>i.focus(),30);
  }
  function closeKey(){const m=document.getElementById('ltdlKeyModal');if(m)m.style.display='none';}
  function saveKey(){
    const i=document.getElementById('ltdlKeyInput');
    const msg=document.getElementById('ltdlKeyMsg');
    const v=(i?.value||'').trim();
    if(!v){if(msg)msg.textContent='❌ Hãy dán Gemini API key.';return;}
    if(v.length<20){if(msg)msg.textContent='❌ Gemini API key có vẻ không hợp lệ.';return;}
    localStorage.setItem(KEY,v);status();
    if(msg)msg.textContent='✅ Đã lưu key trên trình duyệt này.';
    setTimeout(closeKey,450);
  }
  function clearKey(){localStorage.removeItem(KEY);const i=document.getElementById('ltdlKeyInput');if(i)i.value='';status();const m=document.getElementById('ltdlKeyMsg');if(m)m.textContent='🗑 Đã xóa key.';}
  function studentAnswer(){
    const q=(typeof Q!=='undefined')?Q:{};
    if(q.kind==='TN' || q.kind==='choice'){
      const z=document.querySelector('input[name=a]:checked') || document.querySelector('input[name=q]:checked');
      return z ? String.fromCharCode(65+(parseInt(z.value,10)||0)) : '';
    }
    if(q.kind==='DS' || q.kind==='tf'){
      const arr=[];
      (q.statements||[]).forEach(function(s,i){
        const z=document.querySelector('input[name=t'+i+']:checked') || document.querySelector('input[name=q'+(q.idx||0)+'_'+i+']:checked');
        arr.push(z ? ((z.value==='1'||z.value==='true'||z.value==='Đ')?'Đ':'S') : '?');
      });
      return arr.join('');
    }
    const ids=['ans','shortAns','short0'];
    for(const id of ids){const x=document.getElementById(id);if(x)return (x.value||'').trim();}
    return '';
  }
  async function review(){
    const out=document.getElementById('geminiOut');
    if(!out){alert('Chưa có vùng hiển thị AI Phản biện.');return;}
    const k=val();if(!k){openKey();return;}
    const q=(typeof Q!=='undefined')?Q:{};
    out.innerHTML='<div class="notice">⏳ Gemini đang phân tích câu hỏi, đáp án và bài làm...</div>';
    try{
      const r=await fetch('/api/gemini/review_student',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        api_key:k,text:q.text||'',answer:q.answer||'',student:studentAnswer(),solution:q.solution||'',kind:q.kind||'',dang:q.dang||'',level:q.level||''
      })});
      const d=await r.json();
      if(!d.ok){out.textContent='❌ '+(d.error||'Gemini không phản hồi.');return;}
      out.textContent=d.text||'';
      if(window.MathJax && MathJax.typesetPromise) await MathJax.typesetPromise([out]);
      const sp=document.getElementById('speakReview');if(sp)sp.style.display='inline-block';
    }catch(e){out.textContent='❌ Không gọi được AI Phản biện: '+e;}
  }
  window.openStudentGeminiKey=openKey;
  window.closeStudentGeminiKey=closeKey;
  window.saveStudentGeminiKey=saveKey;
  window.clearStudentGeminiKey=clearKey;
  window.askGemini=review;
  window.askStudentGemini=review;
  document.addEventListener('DOMContentLoaded',status);
})();
</script>
'''


@app.after_request
def final_ui_sync(response):
    if 'text/html' not in response.headers.get('Content-Type',''):
        return response
    try:
        body=response.get_data(as_text=True)
        # 1) One public brand everywhere.
        body=re.sub(r'📚\s*Ngân hàng câu hỏi GitHub', BRAND, body, flags=re.I)
        body=body.replace('MỤC LỤC · GitHub','MỤC LỤC')
        body=re.sub(r'Nguồn đề:\s*bank_index\.json\s*\+\s*ngan-hang/\*\.tex\s*·\s*Google Sheet không dùng cho đề', SUBTITLE, body, flags=re.I)
        # 2) GitHub is ADMIN-only and only on admin/github pages.
        admin = session.get('role') == 'admin'
        allowed = admin and (request.path.startswith('/admin') or request.path.startswith('/github'))
        if not allowed:
            body=re.sub(r'<a\b[^>]*href=["\']https://github\.com/[^"\']+["\'][^>]*>[\s\S]*?</a>', '', body, flags=re.I)
            body=re.sub(r'<button\b[^>]*>\s*🐙\s*GitHub\s*</button>', '', body, flags=re.I)
            body=re.sub(r'\s*🐙\s*GitHub\s*', ' ', body, flags=re.I)
        # 3) Remove older duplicate Gemini UI injectors; this file owns the final UI.
        body=re.sub(r'<div\s+id=["\']studentGeminiPanel["\'][\s\S]*?</div>\s*<div\s+id=["\']studentKeyModal["\'][\s\S]*?</div>', '', body, flags=re.I)
        body=re.sub(r'<div\s+id=["\']sgkModal["\'][\s\S]*?</div>\s*</div>', '', body, flags=re.I)
        body=re.sub(r'<button\b[^>]*id=["\'](?:gkhBtn|topGeminiKeyBtn|studentGeminiKeyBtn)["\'][^>]*>[\s\S]*?</button>', '', body, flags=re.I)
        # 4) Student key + AI controls only on the actual practice page.
        is_member_practice = session.get('role') == 'member' and request.path == '/member/practice'
        if is_member_practice:
            if 'id="ltdlGeminiKey"' not in body and "id='ltdlGeminiKey'" not in body:
                controls=("<button type='button' id='ltdlGeminiKey' class='ltdl-gemini-key' onclick='openStudentGeminiKey()'>🔑 Gemini <span id='ltdlKeyStatus' class='ltdl-key-status'>—</span></button>"
                          "<button type='button' id='ltdlGeminiAI' class='ltdl-gemini-ai' onclick='askGemini()'>🤖 AI Phản biện</button>")
                if "class='nav'" in body:
                    body=body.replace("<div class='nav'>", "<div class='nav'>"+controls, 1)
                elif 'class="nav"' in body:
                    body=body.replace('<div class="nav">','<div class="nav">'+controls,1)
            if 'id="ltdlKeyModal"' not in body and "id='ltdlKeyModal'" not in body:
                modal="""<div id='ltdlKeyModal' class='ltdl-key-modal'><div class='ltdl-key-box'><div class='ltdl-key-title'>🔑 Nạp Gemini API Key</div><div class='ltdl-key-note'>Dán Gemini API key của học sinh. Key chỉ lưu trên trình duyệt này và chỉ gửi cho yêu cầu AI Phản biện; không lưu vào GitHub hoặc Google Sheet.</div><input id='ltdlKeyInput' class='ltdl-key-input' type='password' autocomplete='off' placeholder='Dán Gemini API key vào đây'><div id='ltdlKeyMsg' class='ltdl-key-note' style='margin:8px 0 0'></div><div class='ltdl-key-actions'><button type='button' class='btn' onclick='closeStudentGeminiKey()'>Hủy</button><button type='button' class='btn red' onclick='clearStudentGeminiKey()'>🗑 Xóa key</button><button type='button' class='btn primary' onclick='saveStudentGeminiKey()'>💾 Lưu key</button></div></div></div>"""
                body=body.replace('</body>',modal+KEY_JS+'</body>',1)
            else:
                body=body.replace('</body>',KEY_JS+'</body>',1)
        body=body.replace('</head>',CSS+'</head>',1)
        response.set_data(body)
    except Exception:
        pass
    return response
