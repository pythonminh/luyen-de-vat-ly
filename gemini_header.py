from flask import request, session
from app import app

@app.after_request
def gemini_header_button(response):
    if 'text/html' not in response.headers.get('Content-Type',''):
        return response
    try:
        body=response.get_data(as_text=True)
        # GitHub is an ADMIN-only control. Remove the public GitHub link
        # from the header for members/guests before adding the Gemini key button.
        if session.get('role') != 'admin':
            import re
            body=re.sub(r"<a[^>]*href=['\"]https://github\.com/[^'\"]+['\"][^>]*>.*?</a>", '', body, flags=re.I|re.S)
        patch=r'''<style>
.gkh-btn{border:1px solid #ffffff66;background:#ffffff18;color:#fff;border-radius:8px;padding:7px 11px;font-weight:900;cursor:pointer}
.gkh-btn:hover{background:#ffffff2b}
.gkh-modal{position:fixed;inset:0;background:rgba(12,28,48,.48);display:none;align-items:center;justify-content:center;z-index:99999;padding:16px}
.gkh-box{width:min(560px,96vw);background:#fff;color:#18324d;border-radius:12px;border:1px solid #cad8e6;box-shadow:0 16px 44px rgba(0,0,0,.25);padding:18px}
.gkh-box h3{margin:0 0 8px}.gkh-note{font-size:13px;color:#64778b;line-height:1.5;margin-bottom:12px}.gkh-box input{width:100%;padding:11px;border:1px solid #cbd8e6;border-radius:8px;font:14px Segoe UI,Arial}.gkh-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px;flex-wrap:wrap}.gkh-status{font-size:12px;margin-left:6px}
</style>
<script>
(function(){
function key(){return localStorage.getItem('student_gemini_api_key')||'';}
function renderStatus(){var s=document.getElementById('gkhStatus');if(s)s.textContent=key()?'✅ Đã nạp':'⚪ Chưa nạp';}
function openGeminiKey(){var m=document.getElementById('gkhModal');if(!m)return;document.getElementById('gkhKey').value=key();m.style.display='flex';}
function closeGeminiKey(){var m=document.getElementById('gkhModal');if(m)m.style.display='none';}
function saveGeminiKey(){var v=document.getElementById('gkhKey').value.trim();if(!v){alert('Hãy dán Gemini API key.');return;}localStorage.setItem('student_gemini_api_key',v);closeGeminiKey();renderStatus();alert('✅ Đã lưu key trên trình duyệt này.');}
function clearGeminiKey(){localStorage.removeItem('student_gemini_api_key');var x=document.getElementById('gkhKey');if(x)x.value='';renderStatus();}
function install(){if(document.getElementById('gkhBtn'))return;var nav=document.querySelector('.nav');if(!nav)return;var b=document.createElement('button');b.id='gkhBtn';b.className='gkh-btn';b.type='button';b.textContent='🔑 Nạp key Gemini';b.onclick=openGeminiKey;nav.insertBefore(b,nav.firstChild);var m=document.createElement('div');m.id='gkhModal';m.className='gkh-modal';m.innerHTML='<div class="gkh-box"><h3>🔑 Nạp Gemini API key</h3><div class="gkh-note">Key của học sinh chỉ lưu trong trình duyệt này và dùng để gọi Gemini phản biện. Không lưu vào Google Sheet hoặc GitHub.</div><input id="gkhKey" type="password" placeholder="Dán Gemini API key vào đây"><div class="gkh-actions"><button type="button" class="btn" onclick="closeGeminiKey()">Hủy</button><button type="button" class="btn red" onclick="clearGeminiKey()">Xóa key</button><button type="button" class="btn primary" onclick="saveGeminiKey()">💾 Lưu key</button></div></div>';document.body.appendChild(m);renderStatus();}
window.openGeminiKey=openGeminiKey;window.closeGeminiKey=closeGeminiKey;window.saveGeminiKey=saveGeminiKey;window.clearGeminiKey=clearGeminiKey;
document.addEventListener('DOMContentLoaded',install);setTimeout(install,300);
})();
</script>'''
        if "</body>" in body:
            body=body.replace('</body>',patch+'</body>')
        response.set_data(body)
    except Exception:
        pass
    return response
