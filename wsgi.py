from flask import request, redirect, session
from app import app
import dang_routes  # registers /member/dang and makes catalog types clickable


@app.get('/practice/jump/<int:pos>')
def practice_jump(pos):
    """Jump to any question already selected for the current practice session."""
    ids = list(session.get('practice_ids') or [])
    if session.get('role') != 'member' or not ids:
        return redirect('/member/login')
    if pos < 0 or pos >= len(ids):
        return redirect('/member/practice')
    session['practice_pos'] = pos
    return redirect('/member/practice')


@app.after_request
def practice_ui_patch(response):
    """Enhance only the practice HTML: clickable palette + clean student-facing DS layout."""
    if request.path != '/member/practice' or not response.content_type or 'text/html' not in response.content_type:
        return response
    try:
        text = response.get_data(as_text=True)
        import re
        pat = re.compile(r"<span class='pitem([^']*)'>(\d+) · ([^<]+)</span>")

        def repl(m):
            classes = m.group(1).strip()
            n = int(m.group(2))
            label = m.group(3)
            extra = (' ' + classes) if classes else ''
            return (
                f"<button type='button' class='pitem{extra}' "
                f"onclick='jumpPractice({n-1})'>{n} · {label}</button>"
            )

        text2 = pat.sub(repl, text)
        patch = r"""
<script>
function jumpPractice(pos){window.location.href='/practice/jump/'+pos;}
function cleanPracticeLatex(){
  document.querySelectorAll('.qtext,.opt,.tf,.solution').forEach(function(el){
    let s=el.innerHTML;
    s=s.replace(/\\begin\s*\{ex\}/gi,'');
    s=s.replace(/%\s*ID\s*:\s*[^%<\n]*?/gi,'');
    s=s.replace(/%\s*Mức\s*:\s*[^%<\n]*?/gi,'');
    s=s.replace(/%\s*Muc(?: do)?\s*:\s*[^%<\n]*?/gi,'');
    el.innerHTML=s.replace(/\s{2,}/g,' ').trim();
  });
  if(window.MathJax){MathJax.typesetPromise(document.querySelectorAll('.qtext,.opt,.tf,.solution'));}
}
document.addEventListener('DOMContentLoaded',function(){cleanPracticeLatex();});
</script>
<style>
button.pitem{font:inherit;cursor:pointer}
button.pitem:hover{border-color:#145bb0;box-shadow:0 1px 4px #b9cce2}
.qtext{user-select:text}
/* Đúng/Sai: đưa nút Đúng/Sai lên cùng hàng với nội dung ý và phóng to để dễ bấm */
.tf{display:flex!important;align-items:center;gap:18px;flex-wrap:wrap;font-size:20px!important;line-height:1.5!important;padding:16px!important;min-height:78px}
.tf br{display:none!important}
.tf > label{display:inline-flex!important;align-items:center;gap:8px;margin-left:6px;font-size:20px!important;line-height:1.5!important;white-space:nowrap;cursor:pointer}
.tf input[type='radio']{width:22px!important;height:22px!important;accent-color:#176bd3;cursor:pointer}
.tf > b{font-size:21px!important;min-width:28px}
</style>
"""
        response.set_data(text2.replace('</body>', patch + '</body>'))
    except Exception:
        pass
    return response
