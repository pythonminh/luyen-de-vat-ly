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
    """Enhance only the practice HTML: clickable palette + clean student-facing layout."""
    if request.path != '/member/practice' or not response.content_type or 'text/html' not in response.content_type:
        return response
    try:
        text = response.get_data(as_text=True)
        import re
        pat = re.compile(r"<span class='pitem([^']*)'>(\\d+) · ([^<]+)</span>")

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
}
function alignTF(){
  document.querySelectorAll('.tf').forEach(function(row){
    if(row.dataset.aligned==='1') return;
    const b=row.querySelector('b');
    const labels=[...row.querySelectorAll('label')];
    const textNodes=[...row.childNodes].filter(function(n){return n.nodeType===3 && n.textContent.trim();});
    if(!b || labels.length<2 || textNodes.length<1) return;
    const text=textNodes.map(function(n){return n.textContent;}).join(' ').replace(/\s+/g,' ').trim();
    row.innerHTML='';
    const num=document.createElement('div');num.className='tf-num';num.textContent=b.textContent.trim();
    const content=document.createElement('div');content.className='tf-text';content.textContent=text;
    const yes=labels[0].cloneNode(true);yes.className='tf-choice';
    const no=labels[1].cloneNode(true);no.className='tf-choice';
    row.append(num,content,yes,no);
    row.dataset.aligned='1';
  });
}
document.addEventListener('DOMContentLoaded',function(){
  cleanPracticeLatex();
  alignTF();
  if(window.MathJax) MathJax.typesetPromise();
});
</script>
<style>
button.pitem{font:inherit;cursor:pointer}
button.pitem:hover{border-color:#145bb0;box-shadow:0 1px 4px #b9cce2}
.qtext{user-select:text}
/* Đúng/Sai: bố cục 4 cột thẳng hàng */
.tf{
  display:grid!important;
  grid-template-columns:56px minmax(320px,1fr) 120px 120px!important;
  align-items:center!important;
  gap:14px!important;
  font-size:20px!important;
  line-height:1.45!important;
  padding:16px 18px!important;
  min-height:78px;
}
.tf br{display:none!important}
.tf > b,.tf-num{
  font-size:21px!important;
  font-weight:800!important;
  text-align:center!important;
}
.tf-text{
  min-width:0;
  font-size:20px!important;
}
.tf-choice{
  display:flex!important;
  align-items:center!important;
  justify-content:flex-start!important;
  gap:8px!important;
  margin:0!important;
  font-size:20px!important;
  line-height:1.4!important;
  white-space:nowrap!important;
  cursor:pointer;
}
.tf-choice input[type='radio']{
  width:24px!important;
  height:24px!important;
  margin:0!important;
  accent-color:#176bd3;
  cursor:pointer;
}
@media(max-width:800px){
  .tf{grid-template-columns:44px minmax(180px,1fr) 100px 100px!important;gap:8px!important;padding:13px!important}
  .tf-text,.tf-choice{font-size:17px!important}
  .tf-choice input[type='radio']{width:22px!important;height:22px!important}
}
</style>
"""
        response.set_data(text2.replace('</body>', patch + '</body>'))
    except Exception:
        pass
    return response


@app.after_request
def catalog_two_rows(response):
    """Make each exercise type a clean two-row block: name, then aligned counts."""
    if request.path != '/member' or 'text/html' not in response.headers.get('Content-Type',''):
        return response
    try:
        body = response.get_data(as_text=True)
        style = r"""
<style>
/* Mỗi dạng bài: hàng 1 là tên; hàng 2 là 4 loại + tổng + nút mở */
.dangrow{
  display:grid!important;
  grid-template-columns:1fr!important;
  grid-template-rows:auto auto!important;
  align-items:center!important;
  row-gap:5px!important;
  padding:7px 4px!important;
  min-height:58px!important;
}
.dangrow .dangname{
  grid-column:1!important;
  grid-row:1!important;
  width:100%!important;
  line-height:1.35!important;
  font-size:13px!important;
  white-space:normal!important;
}
.dangrow .kind,
.dangrow .ktotal,
.dangrow .arrow{
  grid-row:2!important;
}
.dangrow .kind:first-of-type{margin-left:0!important}
.dangrow .kind{
  display:inline-flex!important;
  align-items:center!important;
  justify-content:center!important;
  min-width:44px!important;
  height:24px!important;
  padding:2px 6px!important;
  font-size:10px!important;
}
.dangrow .ktotal{
  display:inline-flex!important;
  align-items:center!important;
  justify-content:center!important;
  min-width:44px!important;
  height:24px!important;
  border:1px solid #d3dfeb!important;
  border-radius:999px!important;
  background:#fff!important;
  font-size:10px!important;
}
.dangrow .arrow{justify-self:end!important;font-size:16px!important}
/* Các phần tử hàng 2 nằm trên cùng một dòng */
.dangrow{grid-template-columns:44px 44px 44px 44px 52px 18px!important;column-gap:5px!important}
.dangrow .dangname{grid-column:1 / -1!important}
@media(max-width:700px){
  .dangrow{grid-template-columns:42px 42px 42px 42px 48px 14px!important;column-gap:3px!important}
  .dangrow .kind,.dangrow .ktotal{min-width:0!important;font-size:9px!important}
  .dangrow .dangname{font-size:12px!important}
}
</style>"""
        response.set_data(body.replace('</body>', style + '</body>'))
    except Exception:
        pass
    return response
