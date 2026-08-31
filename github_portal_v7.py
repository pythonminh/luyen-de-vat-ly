# -*- coding: utf-8 -*-
"""v7 overlay: typed question selection (4 kinds) + exact count by selected category, built on v6."""
from __future__ import annotations
import html, json, random, urllib.parse
from flask import request
from github_portal_v6 import app, reqmem, curmember, allowed, lesson_level, lesson_questions, page

KINDS={
    'choice':'① Trắc nghiệm 4 lựa chọn',
    'tf':'② Đúng / Sai',
    'short':'③ Trả lời ngắn',
    'essay':'④ Tự luận',
}

def intercept_select():
    if request.path!='/member/lesson/select' or request.method!='GET': return None
    m=curmember(); path=request.args.get('path','')
    if not m: return None
    if not allowed(m,path): return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này chỉ dành cho thành viên VIP.</div></div></div></div>")
    try: qs=lesson_questions(path)
    except Exception as e: return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(e))}</div></div></div></div>")
    dangs={}
    kinds={k:0 for k in KINDS}
    for q in qs:
        dangs[q.get('dang','Chưa phân dạng')]=dangs.get(q.get('dang','Chưa phân dạng'),0)+1
        if q.get('kind') in kinds:kinds[q['kind']]+=1
    dopt=''.join(f"<option value='{html.escape(k,quote=True)}'>{html.escape(k)} — {v} câu</option>" for k,v in dangs.items())
    kopt=''.join(f"<option value='{k}'>{html.escape(name)} — {kinds[k]} câu</option>" for k,name in KINDS.items())
    alln=len(qs)
    body=("<div class='wrap'><div class='panel'><div class='head'>📝 Chọn nội dung làm bài · <span class='pill'>"+str(alln)+" câu</span></div>"
          "<div class='body'><form method='get' action='/member/quiz'><input type='hidden' name='path' value='"+html.escape(path,quote=True)+"'>"
          "<div class='field'><label>Dạng bài tập</label><select name='dang' id='dang'><option value='__ALL__'>Tất cả dạng — "+str(alln)+" câu</option>"+dopt+"</select></div>"
          "<div class='field'><label>Loại câu hỏi</label><select name='kind' id='kind'><option value='__ALL__'>Tất cả 4 loại</option>"+kopt+"</select></div>"
          "<div class='field'><label>Số câu muốn làm</label><input name='n' id='n' type='number' min='1' value='"+str(min(10,alln))+"' required></div>"
          "<div class='notice'>Số câu được kiểm tra theo <b>dữ liệu thực tế trong file .tex</b>. Không thể chọn vượt quá số câu của Dạng bài tập + Loại câu hỏi đã chọn.</div>"
          "<button class='btn primary'>▶ Bắt đầu</button> <a class='btn' href='/member'>← Quay lại</a></form></div></div></div>"
          "<script>const D="+json.dumps(dangs,ensure_ascii=False)+",K="+json.dumps(kinds,ensure_ascii=False)+";document.getElementById('dang').onchange=upd;document.getElementById('kind').onchange=upd;function upd(){let d=document.getElementById('dang').value,k=document.getElementById('kind').value,n="+json.dumps(qs,ensure_ascii=False)+";let c=n.filter(q=>(d==='__ALL__'||q.dang===d)&&(k==='__ALL__'||q.kind===k)).length;let x=document.getElementById('n');x.max=c;if(+x.value>c)x.value=c||1;if(c<1)x.value=1;}</script>")
    return page('Chọn bài',body)


def intercept_quiz():
    if request.path!='/member/quiz' or request.method!='GET': return None
    m=curmember(); path=request.args.get('path',''); dang=request.args.get('dang','__ALL__'); kind=request.args.get('kind','__ALL__')
    if not m or not allowed(m,path): return None
    try: qs=lesson_questions(path)
    except Exception as e: return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(e))}</div></div></div></div>")
    data=[q for q in qs if (dang=='__ALL__' or q.get('dang')==dang) and (kind=='__ALL__' or q.get('kind')==kind)]
    try:n=int(request.args.get('n','10'))
    except Exception:n=10
    n=max(1,min(n,len(data)))
    random.shuffle(data);data=data[:n]
    payload=json.dumps(data,ensure_ascii=False)
    label=(KINDS.get(kind,'Tất cả 4 loại'))
    title='Làm bài · '+(dang if dang!='__ALL__' else 'Tất cả dạng')+' · '+label
    script=r"""
const DATA=__PAYLOAD__;let i=0,A=Array(DATA.length).fill(null),checked=Array(DATA.length).fill(false);function esc(s){return String(s).replace(/[&<>\"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[m]))}function render(){const q=DATA[i];let h='<div class="quiztop"><b>Câu '+(i+1)+'/'+DATA.length+'</b><span>__LABEL__</span></div><div class="qcard"><div class="qtext">'+esc(q.text)+'</div>';if(q.kind==='choice'){q.options.forEach((o,j)=>{let c=checked[i]?(o.correct?'correct':(A[i]===j?'wrong':'')):'';h+='<label class="opt '+c+'"><input type="radio" name="a" onclick="A[i]='+j+'" '+(A[i]===j?'checked':'')+'> '+String.fromCharCode(65+j)+'. '+esc(o.text)+'</label>'})}else if(q.kind==='tf'){q.statements.forEach((s,j)=>{let v=Array.isArray(A[i])?A[i][j]:null;let c=checked[i]?(v===s.correct?'correct':'wrong'):'';h+='<div class="tfrow '+c+'"><b>'+(j+1)+'.</b> '+esc(s.text)+'<br><label><input type="radio" name="t'+j+'" onclick="picktf('+j+',true)" '+(v===true?'checked':'')+'> Đúng</label> <label><input type="radio" name="t'+j+'" onclick="picktf('+j+',false)" '+(v===false?'checked':'')+'> Sai</label></div>'})}else if(q.kind==='short'){h+='<div class="field"><input id="short" value="'+esc(A[i]||'')+'" oninput="A[i]=this.value" placeholder="Nhập đáp án"></div>'}else h+='<div class="notice">Câu tự luận — ghi lời giải. Chấm tự động chưa áp dụng cho tự luận.</div>';h+='<div class="row" style="margin-top:14px">';if(!checked[i])h+='<button class="btn primary" onclick="check()">✅ Kiểm tra câu</button>';else h+='<span class="pill '+((q.kind==='choice'&&q.options[A[i]]&&q.options[A[i]].correct)||(q.kind==='tf'&&Array.isArray(A[i])&&q.statements.every((s,j)=>A[i][j]===s.correct))?'free':'vip')+'">'+((q.kind==='choice'&&q.options[A[i]]&&q.options[A[i]].correct)||(q.kind==='tf'&&Array.isArray(A[i])&&q.statements.every((s,j)=>A[i][j]===s.correct))?'✅ Đúng':'❌ Kiểm tra lại')+'</span>';if(i>0)h+='<button class="btn" onclick="i--;render();MathJax.typeset()">← Trước</button>';if(i<DATA.length-1)h+='<button class="btn" onclick="i++;render();MathJax.typeset()">Câu tiếp →</button>';else h+='<button class="btn primary" onclick="finish()">🏁 Xem kết quả</button>';h+='</div></div>';document.getElementById('app').innerHTML=h;MathJax.typeset()}function picktf(j,v){if(!Array.isArray(A[i]))A[i]=[];A[i][j]=v}function check(){const q=DATA[i];if(q.kind==='choice'&&A[i]===null)return alert('Hãy chọn đáp án.');if(q.kind==='tf'&&(!Array.isArray(A[i])||A[i].length<q.statements.length))return alert('Hãy chọn đủ Đúng/Sai.');checked[i]=true;render()}function finish(){let right=0,total=0;DATA.forEach((q,k)=>{if(q.kind==='choice'){total++;if(q.options[A[k]]&&q.options[A[k]].correct)right++}else if(q.kind==='tf'){q.statements.forEach((s,j)=>{total++;if(Array.isArray(A[k])&&A[k][j]===s.correct)right++})}else if(q.kind==='short'){total++;}});let score=total?right/total*10:0;sessionStorage.setItem('quizResult',JSON.stringify({path:__PATH__,dang:__DANG__,kind:__KIND__,right,total,score,answers:A,questions:DATA}));location.href='/member/result'}render();
"""
    script=script.replace('__PAYLOAD__',payload).replace('__LABEL__',json.dumps(label,ensure_ascii=False)).replace('__PATH__',json.dumps(path,ensure_ascii=False)).replace('__DANG__',json.dumps(dang,ensure_ascii=False)).replace('__KIND__',json.dumps(kind,ensure_ascii=False))
    body="<div class='wrap'><div class='panel'><div class='head'>📖 "+html.escape(PathName(path))+" · "+str(n)+" câu</div><div class='body'><div id='app'></div></div></div></div><script>"+script+"</script>"
    return page(title,body)

def PathName(path):
    return path.replace('\\','/').rstrip('/').split('/')[-2] if path else 'Bài học'

app.before_request(intercept_select)
app.before_request(intercept_quiz)
