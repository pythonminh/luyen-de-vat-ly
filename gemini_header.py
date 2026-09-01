from flask import request, session
from app import app

@app.after_request
def gemini_header_button(response):
    if 'text/html' not in response.headers.get('Content-Type',''):
        return response
    try:
        body=response.get_data(as_text=True)
        # GitHub/ADMIN links are visible only after ADMIN login.
        if session.get('role') != 'admin':
            import re
            body=re.sub(r"\s*<a[^>]*href=['\"](?:https://github\\.com/[^'\"]+|/github/repo)['\"][^>]*>.*?</a>", '', body, flags=re.I|re.S)
            body=re.sub(r"\s*<a[^>]*href=['\"](?:/admin|/admin/login)['\"][^>]*>.*?</a>", '', body, flags=re.I|re.S)

        # Insert the Gemini key button directly into the header on every HTML page.
        if 'id="gkhBtn"' not in body and 'id=\'gkhBtn\'' not in body:
            marker='</div></div></div>'
            button=("<button id='gkhBtn' class='gkh-btn' type='button' onclick='openGeminiKey()'>"
                    "🔑 Nạp key Gemini <span id='gkhStatus' class='gkh-status'></span></button>")
            # Prefer putting the button in the navigation area; fallback to top header.
            if "class='nav'" in body:
                body=body.replace("</div></div></div>", button+"</div></div></div>", 1)
            else:
                body=body.replace(marker, button+marker, 1)

        patch=r'''<style>
.gkh-btn{border:1px solid #ffffff66;background:#ffffff18;color:#fff;border-radius:8px;padding:7px 11px;font-weight:900;cursor:pointer;margin-left:6px}.gkh-btn:hover{background:#ffffff2b}.gkh-status{font-size:11px;margin-left:4px}.gkh-modal{position:fixed;inset:0;background:rgba(12,28,48,.48);display:none;align-items:center;justify-content:center;z-index:99999;padding:16px}.gkh-box{width:min(560px,96vw);background:#fff;color:#18324d;border-radius:12px;border:1px solid #cad8e6;box-shadow:0 16px 44px rgba(0,0,0,.25);padding:18px}.gkh-box h3{margin:0 0 8px}.gkh-note{font-size:13px;color:#64778b;line-height:1.5;margin-bottom:12px}.gkh-box input{width:100%;padding:11px;border:1px solid #cbd8e6;border-radius:8px;font:14px Segoe UI,Arial}.gkh-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px;flex-wrap:wrap}
</style>
<script>
(function(){
function key(){return localStorage.getItem('student_gemini_api_key')||'';}
function renderStatus(){var s=document.getElementById('gkhStatus');if(s)s.textContent=key()?'✅ Đã nạp':'⚪ Chưa nạp';}
function openGeminiKey(){var m=document.getElementById('gkhModal');if(!m)return;document.getElementById('gkhKey').value=key();m.style.display='flex';}
function closeGeminiKey(){var m=document.getElementById('gkhModal');if(m)m.style.display='none';}
function saveGeminiKey(){var v=document.getElementById('gkhKey').value.trim();if(!v){alert('Hãy dán Gemini API key.');return;}localStorage.setItem('student_gemini_api_key',v);closeGeminiKey();renderStatus();alert('✅ Đã lưu key trên trình duyệt này.');}
function clearGeminiKey(){localStorage.removeItem('student_gemini_api_key');var x=document.getElementById('gkhKey');if(x)x.value='';renderStatus();}
function installModal(){if(document.getElementById('gkhModal')){renderStatus();return;}var m=document.createElement('div');m.id='gkhModal';m.className='gkh-modal';m.innerHTML='<div class="gkh-box"><h3>🔑 Nạp Gemini API key</h3><div class="gkh-note">Key của học sinh chỉ lưu trong trình duyệt này và chỉ dùng khi phản biện. Không lưu vào Google Sheet hoặc GitHub.</div><input id="gkhKey" type="password" placeholder="Dán Gemini API key vào đây"><div class="gkh-actions"><button type="button" class="btn" onclick="closeGeminiKey()">Hủy</button><button type="button" class="btn red" onclick="clearGeminiKey()">Xóa key</button><button type="button" class="btn primary" onclick="saveGeminiKey()">💾 Lưu key</button></div></div>';document.body.appendChild(m);renderStatus();}
window.openGeminiKey=openGeminiKey;window.closeGeminiKey=closeGeminiKey;window.saveGeminiKey=saveGeminiKey;window.clearGeminiKey=clearGeminiKey;
document.addEventListener('DOMContentLoaded',installModal);setTimeout(installModal,100);
})();
</script>'''
        body=body.replace('</body>',patch+'</body>')
        response.set_data(body)
    except Exception:
        pass
    return response
