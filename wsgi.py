import json
import re
import urllib.error
import urllib.parse
import urllib.request

from flask import request, redirect, session, jsonify
from app import app, member_current
import dang_routes
import student_gemini


def _gemini_model_name(s):
    s = (s or 'gemini-2.5-flash').strip()
    s = re.sub(r'^models/', '', s)
    return s or 'gemini-2.5-flash'


def _gemini_review_prompt(data):
    return f"""Bạn là trợ giảng Vật lý/Toán trung học phổ thông. Hãy phản biện bài làm của học sinh dựa đúng vào dữ liệu được cung cấp.

Dạng bài: {data.get('dang','')}
Loại câu: {data.get('kind','')}
Mức độ: {data.get('level','')}

CÂU HỎI:
{data.get('text','')}

TRẢ LỜI CỦA HỌC SINH:
{data.get('student','')}

LỜI GIẢI GỐC TRONG TEX:
{data.get('solution','')}

Yêu cầu phản biện:
1. Kết luận học sinh đúng hay sai hoặc phần nào đúng/sai.
2. Chỉ ra chính xác chỗ sai nếu có.
3. Giải thích ngắn gọn, dễ hiểu.
4. Nêu cách làm đúng.
5. Không tự thay đổi nội dung câu hỏi.
Trả lời bằng tiếng Việt, trình bày rõ ràng."""


def gemini_review():
    if not member_current():
        return jsonify(ok=False, error='Chưa đăng nhập'), 401
    data = request.get_json(silent=True) or {}
    api_key = str(data.get('api_key') or '').strip()
    if not api_key:
        return jsonify(ok=False, error='Chưa nhập Gemini API key.'), 400
    if len(api_key) < 20:
        return jsonify(ok=False, error='Gemini API key có vẻ không hợp lệ.'), 400
    model = _gemini_model_name(str(data.get('model') or 'gemini-2.5-flash'))
    url = 'https://generativelanguage.googleapis.com/v1beta/models/' + urllib.parse.quote(model, safe='-_.') + ':generateContent?key=' + urllib.parse.quote(api_key, safe='')
    payload = {
        'contents': [{'parts': [{'text': _gemini_review_prompt(data)}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 1200},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        method='POST',
        headers={'Content-Type': 'application/json', 'User-Agent': 'luyen-de-vat-ly-student-gemini'},
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            obj = json.loads(r.read().decode('utf-8'))
        text = ''.join(p.get('text', '') for c in obj.get('candidates', []) for p in c.get('content', {}).get('parts', []) if isinstance(p, dict)).strip()
        if not text:
            return jsonify(ok=False, error='Gemini không trả về nội dung phản biện.'), 502
        return jsonify(ok=True, text=text)
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            msg = json.loads(raw).get('error', {}).get('message', raw)
        except Exception:
            msg = raw
        return jsonify(ok=False, error=f'Gemini {e.code}: {msg}'), 400 if e.code in (400, 401, 403) else 502
    except urllib.error.URLError:
        return jsonify(ok=False, error='Không kết nối được Gemini API.'), 502
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 502


app.view_functions['gemini_review'] = gemini_review

@app.get('/practice/jump/<int:pos>')
def practice_jump(pos):
    ids=list(session.get('practice_ids') or [])
    if session.get('role')!='member' or not ids:return redirect('/member/login')
    pos=max(0,min(pos,len(ids)-1));session['practice_pos']=pos
    return redirect('/member/practice')

@app.get('/practice/redo/<int:pos>')
def practice_redo(pos):
    m=member_current()
    if not m:return redirect('/member/login')
    ids=list(session.get('practice_ids') or [])
    if pos<0 or pos>=len(ids):return redirect('/member/practice')
    qnum=pos+1;done=list(session.get('practice_done') or [])
    removed=[d for d in done if int(d.get('question',-1))==qnum]
    kept=[d for d in done if int(d.get('question',-1))!=qnum]
    right=int(session.get('practice_right') or 0)-sum(1 for d in removed if d.get('ok'))
    session['practice_done']=kept;session['practice_right']=max(0,right)
    session['practice_pos']=pos;session['practice_streak']=0;session.modified=True
    return redirect('/member/practice')

@app.after_request
def practice_ui_patch(response):
    if request.path!='/member/practice' or 'text/html' not in response.headers.get('Content-Type',''):
        return response
    try:
        body=response.get_data(as_text=True)
        pat=re.compile(r"<span class='pitem([^']*)'>(\\d+) · ([^<]+)</span>")
        def repl(m):
            c=m.group(1).strip();n=int(m.group(2));label=m.group(3);extra=(' '+c) if c else ''
            return f"<button type='button' class='pitem{extra}' data-pos='{n-1}' onclick='jumpPractice({n-1})'>{n} · {label}</button>"
        body=pat.sub(repl,body)
        patch=r'''<script>
function jumpPractice(pos){location.href='/practice/jump/'+pos;}
function retryCurrent(){var x=document.querySelector('.pcur');if(x&&x.dataset.pos!==undefined)location.href='/practice/redo/'+x.dataset.pos;}
function currentQ(){return (typeof Q!=='undefined')?Q:{};}
function studentAnswer(){var q=currentQ();if(q.kind==='TN'){var z=document.querySelector('input[name=a]:checked');return z?String.fromCharCode(65+(+z.value)):'';}if(q.kind==='DS'){var a=[];(q.statements||[]).forEach(function(s,i){var z=document.querySelector('input[name=t'+i+']:checked');a.push(z?(z.value==='1'?'Đ':'S'):'?');});return a.join('');}var x=document.getElementById('ans');return x?x.value.trim():'';}
function askGemini(){var q=currentQ(),out=document.getElementById('geminiOut');if(!out)return;var key=(localStorage.getItem('gemini_student_key')||'').trim();if(!key){key=(prompt('Nhập Gemini API key của bạn (chỉ dùng cho lần gọi này):',key)||'').trim();}else{key=(prompt('Nhập Gemini API key của bạn:',key)||'').trim();}if(!key){out.textContent='❌ Bạn chưa nhập Gemini API key.';return;}if(key.length<20){out.textContent='❌ Gemini API key có vẻ không hợp lệ.';return;}localStorage.setItem('gemini_student_key',key);out.textContent='⏳ Gemini đang phản biện...';fetch('/api/gemini/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key,model:'gemini-2.5-flash',text:q.text||'',student:studentAnswer(),solution:q.solution||'',kind:q.kind||'',dang:q.dang||'',level:q.level||''})}).then(function(r){return r.json();}).then(function(d){if(!d.ok){out.textContent='❌ '+(d.error||'Không gọi được Gemini');return;}out.textContent=d.text||'';var b=document.getElementById('speakReview');if(b)b.style.display='inline-block';if(window.MathJax)MathJax.typesetPromise([out]);}).catch(function(e){out.textContent='❌ '+e;});}
function speakReview(){var o=document.getElementById('geminiOut');if(!o||!o.textContent.trim())return;if(!('speechSynthesis' in window)){alert('Trình duyệt không hỗ trợ đọc giọng nói.');return;}speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(o.textContent);u.lang='vi-VN';u.rate=.95;speechSynthesis.speak(u);}
function installTools(){var q=document.getElementById('q');if(!q||document.getElementById('practiceTools'))return;var bar=document.createElement('div');bar.id='practiceTools';bar.innerHTML='<button type="button" class="btn redo" onclick="retryCurrent()">🔁 Đánh dấu làm lại</button><button type="button" class="btn gem" onclick="askGemini()">🤖 Gemini phản biện</button><button type="button" id="speakReview" class="btn speak" style="display:none" onclick="speakReview()">🔊 Nghe phản biện</button><div id="geminiOut" class="gemOut"></div>';q.appendChild(bar);}
document.addEventListener('DOMContentLoaded',function(){document.querySelectorAll('.pitem').forEach(function(b,i){b.dataset.pos=String(i);});installTools();var q=document.getElementById('q');if(q)new MutationObserver(installTools).observe(q,{childList:true,subtree:true});});
</script><style>
button.pitem{font:inherit;cursor:pointer}button.pitem:hover{border-color:#145bb0;box-shadow:0 1px 4px #b9cce2}button.pitem.pcur{border:2px solid #176bd3;font-weight:900}button.pitem.pdone{background:#eaf9ef;border-color:#82c99b}button.pitem.pwrong{background:#fff0f1;border-color:#eca0a7}
.practiceTools{margin-top:14px;padding-top:10px;border-top:1px dashed #cbd8e6;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.practiceTools .redo{background:#fff8e8!important;border-color:#e5c77e!important;color:#805b00!important}.practiceTools .gem{background:#f6efff!important;border-color:#cbb2ea!important;color:#6b379f!important}.practiceTools .speak{background:#eef8ff!important;border-color:#afd5ef!important;color:#185e96!important}.gemOut{width:100%;min-height:26px;white-space:pre-wrap;line-height:1.6;padding:11px;border:1px solid #cdb8ea;border-radius:8px;background:#fbf9ff}
</style>'''
        response.set_data(body.replace('</body>',patch+'</body>'))
    except Exception:
        pass
    return response

@app.after_request
def catalog_two_rows(response):
    if request.path!='/member' or 'text/html' not in response.headers.get('Content-Type',''):
        return response
    try:
        body=response.get_data(as_text=True)
        style=r'''<style>
.dangrow{display:grid!important;grid-template-columns:1fr!important;grid-template-rows:auto auto!important;align-items:center!important;row-gap:5px!important;padding:7px 4px!important;min-height:58px!important}.dangrow .dangname{grid-column:1 / -1!important;grid-row:1!important;width:100%!important;line-height:1.35!important;font-size:13px!important;white-space:normal!important}.dangrow .kind,.dangrow .ktotal,.dangrow .arrow{grid-row:2!important}.dangrow .kind{display:inline-flex!important;align-items:center!important;justify-content:center!important;min-width:44px!important;height:24px!important;padding:2px 6px!important;font-size:10px!important}.dangrow .ktotal{display:inline-flex!important;align-items:center!important;justify-content:center!important;min-width:44px!important;height:24px!important;border:1px solid #d3dfeb!important;border-radius:999px!important;background:#fff!important;font-size:10px!important}.dangrow .arrow{justify-self:end!important;font-size:16px!important}.dangrow{grid-template-columns:44px 44px 44px 44px 52px 18px!important;column-gap:5px!important}@media(max-width:700px){.dangrow{grid-template-columns:42px 42px 42px 42px 48px 14px!important;column-gap:3px!important}.dangrow .kind,.dangrow .ktotal{min-width:0!important;font-size:9px!important}.dangrow .dangname{font-size:12px!important}}
</style>'''
        response.set_data(body.replace('</body>',style+'</body>'))
    except Exception:
        pass
    return response
