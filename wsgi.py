from flask import request, redirect, session
from app import app, member_current
import dang_routes
import student_gemini

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
        import re
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
function askGemini(){var q=currentQ(),out=document.getElementById('geminiOut');if(!out)return;var key=localStorage.getItem('student_gemini_api_key')||'';if(!key){if(window.openStudentGeminiKey)window.openStudentGeminiKey();else alert('Hãy nạp Gemini API key trước.');return;}out.textContent='⏳ AI đang phân tích câu hỏi, đáp án và bài làm...';fetch('/api/gemini/review_student',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key,text:q.text||'',answer:q.answer||q.correct_answer||q.correct||'',student:studentAnswer(),solution:q.solution||'',kind:q.kind||'',dang:q.dang||'',level:q.level||''})}).then(function(r){return r.json();}).then(function(d){if(!d.ok){out.textContent='❌ '+(d.error||'Không gọi được AI');return;}out.textContent=d.text||'';var b=document.getElementById('speakReview');if(b)b.style.display='inline-block';if(window.MathJax&&window.MathJax.typesetPromise){window.MathJax.typesetClear([out]);window.MathJax.typesetPromise([out]).catch(function(){});}}).catch(function(e){out.textContent='❌ '+e;});}
function speakReview(){var o=document.getElementById('geminiOut');if(!o||!o.textContent.trim())return;if(!('speechSynthesis' in window)){alert('Trình duyệt không hỗ trợ đọc giọng nói.');return;}speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(o.textContent);u.lang='vi-VN';u.rate=.95;speechSynthesis.speak(u);}
function installTools(){var q=document.getElementById('q');if(!q||document.getElementById('practiceTools'))return;var bar=document.createElement('div');bar.id='practiceTools';bar.innerHTML='<button type="button" class="btn redo" onclick="retryCurrent()">🔁 Đánh dấu làm lại</button><button type="button" class="btn gem" onclick="askGemini()">🤖 AI Phản biện</button><button type="button" id="speakReview" class="btn speak" style="display:none" onclick="speakReview()">🔊 Nghe phản biện</button><div id="geminiOut" class="gemOut"></div>';q.appendChild(bar);}
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
