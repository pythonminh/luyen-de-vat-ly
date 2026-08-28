# -*- coding: utf-8 -*-
"""Teacher-facing Ra de page.
Nguon cau hoi: GitHub repository, khong phu thuoc Google Sheet khi tao de.
Ho tro Toan + Vat ly; Khối -> Chuong -> Bai -> Dang bai tap -> Muc do -> Loai cau.
"""
from __future__ import annotations

import base64
import math
import os
import random
import re
import urllib.parse
from typing import Any, Dict, List

from flask import Blueprint, request, render_template_string, session

try:
    from github_integration import gh
except Exception:
    gh = None

bp = Blueprint("ra_de", __name__)
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
SUBJECT_ROOTS = {"Vật lý": "ngan-hang/Vật lý", "Toán": "ngan-hang/Toán"}

CSS = r"""
<style>
:root{--blue:#1976d2;--line:#d7e3ef;--soft:#f4f8fd;--text:#18324b;--green:#159447}
*{box-sizing:border-box}body{margin:0;background:var(--soft);color:var(--text);font-family:Arial,Helvetica,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:14px 18px 80px}.top{background:linear-gradient(135deg,#1769d5,#318de9);color:#fff;border-radius:14px;padding:16px 20px;box-shadow:0 5px 18px #0002}.top h1{margin:0;font-size:24px}.top p{margin:5px 0 0;opacity:.95}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.nav a,.btn{display:inline-flex;align-items:center;justify-content:center;gap:5px;padding:8px 12px;border-radius:9px;border:1px solid #cbd8e5;background:#fff;color:#1769d5;text-decoration:none;cursor:pointer;font-weight:700}.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}.btn.green{background:var(--green);border-color:var(--green);color:#fff}.btn.gray{background:#edf3f8;color:#284762}
.card{background:#fff;border:1px solid var(--line);border-radius:13px;padding:14px;margin:12px 0;box-shadow:0 2px 10px #00000009}.crumb{font-size:13px;color:#657b90;margin:8px 0}.muted{color:#708398;font-size:12px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}.folder{display:block;background:#fff;border:1px solid var(--line);border-radius:11px;padding:13px;text-decoration:none;color:var(--text)}.folder:hover{border-color:#7eb7ef;box-shadow:0 4px 14px #1976d21c}.folder b{display:block;margin-bottom:5px}
.stats{display:flex;gap:7px;flex-wrap:wrap}.pill{border:1px solid #cfe1f7;background:#edf6ff;color:#1769d5;border-radius:999px;padding:5px 9px;font-size:12px;font-weight:800}.pill.orange{background:#fff7df;border-color:#f3d48b;color:#9a6700}.pill.green{background:#eaf8ef;border-color:#b9e4c8;color:#16743a}
.filters{display:grid;grid-template-columns:repeat(6,minmax(130px,1fr));gap:9px;align-items:end}.field label{display:block;font-size:12px;font-weight:800;margin-bottom:5px}.field input,.field select{width:100%;padding:9px;border:1px solid #c9d7e4;border-radius:8px;background:#fff;color:var(--text)}
.pool{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}.poolcard{border:1px solid #dce7f1;border-radius:11px;padding:11px;background:#fff}.poolcard h4{margin:0 0 5px;color:#1769d5}.tag{display:inline-block;border-radius:999px;padding:3px 7px;font-size:10px;font-weight:800;background:#eef5fb;margin:2px}.tag.dbt{background:#fff6dc;color:#8a5a00}.tag.lv{background:#eaf8ef;color:#16743a}.tag.dang{background:#f1ecff;color:#6941c6}
.examhead{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}.section{border:1px solid var(--line);border-radius:12px;padding:13px;margin:12px 0;background:#fff}.section h2{font-size:17px;margin:0 0 10px;color:#1559a5}.q{border:1px solid #dce6ef;border-radius:10px;padding:12px;margin:9px 0;background:#fff}.qnum{font-weight:800;color:#1769d5;margin-bottom:6px}.qtext{line-height:1.55;white-space:pre-wrap}.opts{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.opt{border:1px solid #e0e7ef;border-radius:8px;padding:8px}.answer{display:block;margin-top:9px}.notice{border:1px solid #f1d18b;background:#fff8e5;border-radius:10px;padding:11px;color:#795600}.result{border:2px solid #b8dfc5;background:#effbf3;border-radius:12px;padding:14px;margin:12px 0}.wrong{border-color:#f2c0c0;background:#fff4f4}.sticky{position:fixed;right:16px;bottom:16px;z-index:20}
@media(max-width:1000px){.filters{grid-template-columns:repeat(3,1fr)}}@media(max-width:650px){.wrap{padding:10px}.filters{grid-template-columns:1fr 1fr}.opts{grid-template-columns:1fr}.top h1{font-size:20px}}
</style><script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
"""

HOME_TPL = CSS + r'''
<div class="wrap"><div class="top"><h1>📝 Ra đề từ GitHub</h1><p><b>{{subject}}</b> · Chọn Khối → Chương → Bài → Dạng bài tập → Mức độ → Loại câu. Không gọi Google Sheet khi tạo đề.</p></div>
<div class="nav"><a href="/">🏠 Trang chủ</a><a href="/ra-de?subject=Vật%20lý">⚛ Vật lý</a><a href="/ra-de?subject=Toán">📐 Toán</a><a href="/github">🐙 GitHub</a></div>
<div class="crumb">{{' › '.join(crumbs) if crumbs else 'Chọn nội dung từ ngân hàng GitHub'}}</div>{% if error %}<div class="notice">⚠️ {{error}}</div>{% endif %}
<div class="card"><div class="stats"><span class="pill">Nguồn: GitHub</span><span class="pill">{{repo}}</span>{% if path %}<span class="pill green">{{path}}</span>{% endif %}</div></div>
{% if folders %}<div class="card"><h2>📚 {{level_title}}</h2><div class="grid">{% for f in folders %}<a class="folder" href="/ra-de?subject={{subject|urlencode}}&path={{f.path|urlencode}}"><b>📁 {{f.name}}</b><span class="muted">Mở danh mục</span></a>{% endfor %}</div></div>{% endif %}
{% if lesson %}<div class="card"><div class="examhead"><div><h2 style="margin:0">{{lesson}}</h2><div class="muted">{{path}}</div></div><div class="stats"><span class="pill">{{counts.total}} câu</span><span class="pill">TN: {{counts.TN}}</span><span class="pill orange">Đ/S: {{counts.TF}}</span><span class="pill green">TLN: {{counts.TLN}}</span></div></div></div>
<div class="card"><h3 style="margin-top:0">🎯 Chọn cấu hình ra đề</h3><form method="post" action="/ra-de/generate"><input type="hidden" name="path" value="{{path}}"><input type="hidden" name="subject" value="{{subject}}"><div class="filters">
<div class="field"><label>Dạng bài tập</label><select name="dbt"><option value="">Tất cả</option>{% for x,n in dbt_options %}<option value="{{x}}">{{x}} ({{n}})</option>{% endfor %}</select></div>
<div class="field"><label>Mức độ</label><select name="muc"><option value="">Tất cả</option><option>NB</option><option>TH</option><option>VD</option><option>VDC</option></select></div>
<div class="field"><label>Loại câu</label><select name="dang"><option value="">Tất cả</option><option>Trắc nghiệm</option><option>Đúng sai</option><option>Trả lời ngắn</option><option>Tự luận</option></select></div>
<div class="field"><label>Số câu</label><input name="count" type="number" min="1" max="{{counts.total}}" value="20"></div><div class="field"><label>Thời gian (phút)</label><input name="time" type="number" min="1" value="45"></div><div><button class="btn green" type="submit">🚀 RA ĐỀ</button></div></div></form></div>
<div class="card"><h3 style="margin-top:0">📊 Kho câu hỏi trong bài</h3><div class="pool">{% for q in preview %}<div class="poolcard"><h4>{{q.id or 'Câu'}}</h4><span class="tag dbt">{{q.dbt or 'Chưa phân loại'}}</span><span class="tag lv">{{q.muc or '—'}}</span><span class="tag dang">{{q.dang}}</span><div style="margin-top:7px;line-height:1.45">{{q.text}}</div></div>{% endfor %}</div></div>{% endif %}</div>
'''

EXAM_TPL = CSS + r'''
<div class="wrap"><div class="top"><h1>📝 {{title}}</h1><p>{{subject}} · {{lesson}} · {{total}} câu · {{time}} phút · Nguồn GitHub</p></div><div class="nav"><a class="btn gray" href="/ra-de?subject={{subject|urlencode}}&path={{path|urlencode}}">← Cấu hình lại</a><button class="btn gray" onclick="window.print()">🖨 In đề</button></div>
<div class="card"><div class="stats"><span class="pill">{{total}} câu</span><span class="pill orange">{{time}} phút</span><span class="pill green">GitHub trực tiếp</span>{% if dbt %}<span class="pill orange">Dạng BT: {{dbt}}</span>{% endif %}</div></div>
<form method="post" action="/ra-de/submit" id="examForm"><input type="hidden" name="exam_id" value="{{exam_id}}">{% for sec in sections %}<div class="section"><h2>{{sec.title}}</h2>{% for q in sec.items %}<div class="q"><div class="qnum">Câu {{loop.index + sec.offset}}</div><div class="qtext">{{q.text}}</div>
{% if q.dang == 'Đúng sai' %}<div class="answer">{% for o in q.options %}<div style="margin:7px 0"><b>{{['A','B','C','D'][loop.index0]}}.</b> {{o.text}}<br><label><input type="radio" name="q_{{q.uid}}_{{loop.index0}}" value="Đ"> Đúng</label> <label><input type="radio" name="q_{{q.uid}}_{{loop.index0}}" value="S"> Sai</label></div>{% endfor %}</div>
{% elif q.options %}<div class="opts">{% for o in q.options %}<label class="opt"><input type="radio" name="q_{{q.uid}}" value="{{loop.index0}}"> {{['A','B','C','D'][loop.index0]}}. {{o.text}}</label>{% endfor %}</div>
{% elif q.dang == 'Trả lời ngắn' %}<div class="answer"><input name="q_{{q.uid}}" placeholder="Nhập đáp số / biểu thức" style="width:100%;padding:8px;border:1px solid #c9d7e4;border-radius:8px"></div>
{% else %}<div class="answer"><textarea name="q_{{q.uid}}" rows="4" style="width:100%;padding:8px;border:1px solid #c9d7e4;border-radius:8px" placeholder="Nhập bài làm"></textarea></div>{% endif %}</div>{% endfor %}</div>{% endfor %}
<div class="card"><button class="btn green" type="submit">✅ NỘP BÀI – CHẤM ĐIỂM</button></div></form></div><script>window.MathJax&&MathJax.typesetPromise&&MathJax.typesetPromise();</script>
'''

RESULT_TPL = CSS + r'''
<div class="wrap"><div class="top"><h1>📊 Kết quả chấm điểm</h1><p>{{subject}} · {{lesson}} · {{total}} câu</p></div><div class="result"><h2 style="margin-top:0">Điểm: {{score}}/10</h2><b>Đúng: {{correct}}/{{auto}}</b> · <b>Chưa chấm tự luận: {{essay}}</b> · Thời gian: {{time}} phút</div>
{% for sec in sections %}<div class="section"><h2>{{sec.title}}</h2>{% for q in sec.items %}<div class="q {% if q.ok is false %}wrong{% endif %}"><div class="qnum">Câu {{loop.index + sec.offset}} {% if q.ok %}✅{% elif q.ok is false %}❌{% endif %}</div><div class="qtext">{{q.text}}</div><div class="muted">Đáp án: {{q.answer_display}}</div>{% if q.chosen %}<div>Em chọn: <b>{{q.chosen}}</b></div>{% endif %}</div>{% endfor %}</div>{% endfor %}<div class="nav"><a class="btn primary" href="/ra-de?subject={{subject|urlencode}}&path={{path|urlencode}}">🔄 Ra đề khác</a><a class="btn gray" href="/">🏠 Trang chủ</a></div></div><script>window.MathJax&&MathJax.typesetPromise&&MathJax.typesetPromise();</script>
'''

def _clean(s: Any) -> str: return str(s or '').strip()
def _require_gh():
    if gh is None: raise RuntimeError('Không tải được mô-đun GitHub.')
def _gh_contents(path: str, ref: str='main') -> Any:
    _require_gh(); p=urllib.parse.quote(path.strip('/'),safe='/'); return gh(f'/repos/{REPO}/contents/{p}?ref={urllib.parse.quote(ref)}')
def _decode_file(data: Dict[str,Any]) -> str: return base64.b64decode((_clean(data.get('content'))).replace('\n','')).decode('utf-8','replace')
def _strip_tex(s: str) -> str:
    s=re.sub(r'%[^\n]*','',s); s=re.sub(r'\\nguon\{.*?\}','',s,flags=re.S); s=re.sub(r'\\label\{.*?\}','',s); s=re.sub(r'\\(?:centering|small|footnotesize|normalsize|large|Large|item)\b','',s); s=re.sub(r'\\vspace\{.*?\}','',s); return re.sub(r'\n{3,}','\n\n',s).strip()
def _brace_text(s: str, command: str) -> str:
    m=re.search(r'\\'+re.escape(command)+r'\s*\{',s)
    if not m:return ''
    start=m.end(); depth=1; i=start
    while i<len(s):
        if s[i]=='{' and (i==0 or s[i-1]!='\\'): depth+=1
        elif s[i]=='}' and (i==0 or s[i-1]!='\\'):
            depth-=1
            if depth==0:return s[start:i].strip()
        i+=1
    return ''
def _extract_options(text: str, command: str) -> List[Dict[str,Any]]:
    pos=text.find('\\'+command)
    if pos<0:return []
    rest=text[pos+len(command)+1:]; stop=len(rest)
    for marker in ('\\loigiai','\\end{ex}'):
        j=rest.find(marker)
        if j>=0:stop=min(stop,j)
    rest=rest[:stop]; out=[]; i=0
    while i<len(rest):
        if rest[i]!='{':i+=1;continue
        start=i+1;depth=1;i=start
        while i<len(rest) and depth:
            if rest[i]=='{' and (i==0 or rest[i-1]!='\\'):depth+=1
            elif rest[i]=='}' and (i==0 or rest[i-1]!='\\'):depth-=1
            i+=1
        if depth==0:
            raw=rest[start:i-1].strip(); correct=bool(re.search(r'\\True\b',raw)); raw=re.sub(r'\\True\s*','',raw).strip(); out.append({'text':raw,'correct':correct})
    return out
def parse_questions(tex: str) -> List[Dict[str,Any]]:
    out=[]; starts=[m.start() for m in re.finditer(r'\\begin\{ex\}',tex)]
    for idx,start in enumerate(starts):
        end=tex.find(r'\end{ex}',start)
        if end<0:continue
        block=tex[start:end]; prefix=tex[max(0,start-1800):start]
        qid=re.search(r'%\s*ID:\s*([^\s\n]+)',block) or re.search(r'%\s*ID:\s*([^\s\n]+)',prefix)
        muc=re.search(r'%\s*Mức:\s*(NB|TH|VD|VDC|N|H|V)',block,re.I) or re.search(r'%\s*Mức:\s*(NB|TH|VD|VDC|N|H|V)',prefix,re.I)
        dbt=_brace_text(prefix,'dangbt') or _brace_text(block,'dangbt')
        if '\\choiceTF' in block:dang='Đúng sai';opts=_extract_options(block,'choiceTF')
        elif '\\choice' in block:dang='Trắc nghiệm';opts=_extract_options(block,'choice')
        elif '\\shortans' in block:dang='Trả lời ngắn';opts=[]
        else:dang='Tự luận';opts=[]
        body=block
        for marker in ('\\choiceTF','\\choice','\\shortans'):body=body.split(marker,1)[0]
        body=re.sub(r'%[^\n]*','',body); body=re.sub(r'\\dangbt\s*\{.*?\}','',body,flags=re.S); body=re.sub(r'\\begin\{ex\}','',body); body=re.sub(r'\\(?:nguon|label)\{.*?\}','',body,flags=re.S)
        text=_strip_tex(body); ans_short=_brace_text(block,'shortans') if dang=='Trả lời ngắn' else ''
        uid=qid.group(1).strip() if qid else f'Q{idx+1}'
        out.append({'uid':uid,'id':uid,'muc':muc.group(1).upper() if muc else '','dbt':dbt,'dang':dang,'text':text,'options':opts,'short_answer':ans_short})
    return out
def _lesson_questions(path: str) -> List[Dict[str,Any]]:
    data=_gh_contents(path); data=[data] if isinstance(data,dict) else data; tex=next((x for x in data if x.get('name','').lower()=='de.tex'),None)
    return parse_questions(_decode_file(_gh_contents(tex['path']))) if tex else []
def _counts(qs: List[Dict[str,Any]]) -> Dict[str,int]: return {'total':len(qs),'TN':sum(q['dang']=='Trắc nghiệm' for q in qs),'TF':sum(q['dang']=='Đúng sai' for q in qs),'TLN':sum(q['dang']=='Trả lời ngắn' for q in qs),'TL':sum(q['dang']=='Tự luận' for q in qs)}
def _number_norm(s: str) -> str: return _clean(s).lower().replace(' ','').replace(',','.').replace('\\,','')
def _score_short(user: str, correct: str) -> bool:
    u=_number_norm(user);c=_number_norm(correct)
    if not u or not c:return False
    if u==c:return True
    try:return math.isclose(float(u),float(c),rel_tol=1e-5,abs_tol=1e-6)
    except Exception:return False
def _session_exam(): return session.get('ra_de_exam') or {}

@bp.route('/ra-de',methods=['GET'])
def home():
    subject=_clean(request.args.get('subject') or 'Vật lý'); subject=subject if subject in SUBJECT_ROOTS else 'Vật lý'; root=SUBJECT_ROOTS[subject]; path=_clean(request.args.get('path')).strip('/') or root
    try:
        data=_gh_contents(path); data=[data] if isinstance(data,dict) else data; has_tex=any(x.get('name','').lower()=='de.tex' for x in data)
        if not has_tex:
            folders=[{'name':x.get('name'),'path':x.get('path')} for x in data if x.get('type')=='dir']; rel=path[len(root):].strip('/'); crumbs=[subject]+([x for x in rel.split('/') if x] if rel else []); level_title='Chọn Khối' if path==root else ('Chọn Chương' if '/Lớp ' in path and path.count('/')==2 else 'Chọn Bài')
            return render_template_string(HOME_TPL,subject=subject,repo=REPO,path=path,crumbs=crumbs,folders=folders,level_title=level_title,lesson='',counts={'total':0,'TN':0,'TF':0,'TLN':0,'TL':0},preview=[],dbt_options=[],error=None)
        qs=parse_questions(_decode_file(next(x for x in data if x.get('name')=='de.tex'))); counts=_counts(qs); freq={}
        for q in qs:freq[q['dbt'] or 'Chưa phân loại']=freq.get(q['dbt'] or 'Chưa phân loại',0)+1
        dbt_options=sorted(freq.items(),key=lambda x:(-x[1],x[0])); rel=path[len(root):].strip('/'); crumbs=[subject]+([x for x in rel.split('/') if x] if rel else [])
        return render_template_string(HOME_TPL,subject=subject,repo=REPO,path=path,crumbs=crumbs,folders=[],level_title='',lesson=path.split('/')[-1],counts=counts,preview=qs[:24],dbt_options=dbt_options,error=None)
    except Exception as e:
        return render_template_string(HOME_TPL,subject=subject,repo=REPO,path=path,crumbs=[subject],folders=[],level_title='',lesson='',counts={'total':0,'TN':0,'TF':0,'TLN':0,'TL':0},preview=[],dbt_options=[],error=str(e))

@bp.route('/ra-de/generate',methods=['POST'])
def generate():
    path=_clean(request.form.get('path')).strip('/'); subject=_clean(request.form.get('subject') or 'Vật lý')
    try:
        qs=_lesson_questions(path); dbt=_clean(request.form.get('dbt')); muc=_clean(request.form.get('muc')).upper(); dang=_clean(request.form.get('dang')); count=max(1,int(request.form.get('count') or 20)); time=max(1,int(request.form.get('time') or 45))
        if dbt:qs=[q for q in qs if (q['dbt'] or 'Chưa phân loại')==dbt]
        if muc:qs=[q for q in qs if q['muc']==muc]
        if dang:qs=[q for q in qs if q['dang']==dang]
        random.shuffle(qs);qs=qs[:count]
        if not qs:raise RuntimeError('Không có câu phù hợp bộ lọc đã chọn.')
        for i,q in enumerate(qs):q['uid']=f"{q['id']}__{i}"
        sections=[];offset=0
        for typ,title in [('Trắc nghiệm','PHẦN A — TRẮC NGHIỆM'),('Đúng sai','PHẦN B — ĐÚNG / SAI'),('Trả lời ngắn','PHẦN C — TRẢ LỜI NGẮN'),('Tự luận','PHẦN D — TỰ LUẬN')]:
            arr=[q for q in qs if q['dang']==typ]
            if arr:sections.append({'title':title,'items':arr,'offset':offset});offset+=len(arr)
        exam_id=os.urandom(8).hex();session['ra_de_exam']={'id':exam_id,'subject':subject,'path':path,'lesson':path.split('/')[-1],'time':time,'dbt':dbt,'questions':qs}
        return render_template_string(EXAM_TPL,title='ĐỀ LUYỆN TẬP',subject=subject,lesson=path.split('/')[-1],path=path,total=len(qs),time=time,dbt=dbt,sections=sections,exam_id=exam_id)
    except Exception as e:
        return render_template_string(CSS+'<div class="wrap"><div class="notice">❌ Lỗi tạo đề: {{e}}</div><div class="nav"><a class="btn" href="/ra-de?subject={{subject|urlencode}}&path={{path|urlencode}}">← Quay lại</a></div></div>',e=str(e),subject=subject,path=path)

@bp.route('/ra-de/submit',methods=['POST'])
def submit():
    exam=_session_exam()
    if not exam or exam.get('id')!=_clean(request.form.get('exam_id')):return 'Phiên đề đã hết. Vui lòng tạo đề mới.',400
    qs=exam.get('questions') or [];correct=0;auto=0;essay=0
    for q in qs:
        uid=q['uid'];chosen='';ok=None
        if q['dang']=='Trắc nghiệm':
            raw=request.form.get('q_'+uid,'');chosen=raw;auto+=1
            try:ok=bool(q['options'][int(raw)].get('correct'))
            except Exception:ok=False
        elif q['dang']=='Đúng sai':
            vals=[];ok=True
            for i,o in enumerate(q['options'][:4]):
                v=request.form.get(f'q_{uid}_{i}','');vals.append(v);want='Đ' if o.get('correct') else 'S'
                if v!=want:ok=False
            chosen=' · '.join(vals);auto+=1
        elif q['dang']=='Trả lời ngắn':chosen=request.form.get('q_'+uid,'');auto+=1;ok=_score_short(chosen,q.get('short_answer',''))
        else:chosen=request.form.get('q_'+uid,'');essay+=1;ok=None
        if ok is True:correct+=1
        q['chosen']=chosen;q['ok']=ok
        if q['dang']=='Trắc nghiệm':q['answer_display']=next((chr(65+i) for i,o in enumerate(q['options']) if o.get('correct')),'—')
        elif q['dang']=='Đúng sai':q['answer_display']=' · '.join('Đ' if o.get('correct') else 'S' for o in q['options'][:4])
        elif q['dang']=='Trả lời ngắn':q['answer_display']=q.get('short_answer') or '—'
        else:q['answer_display']='Tự luận — giáo viên chấm'
    score=round(10*correct/auto,2) if auto else 0;sections=[];offset=0
    for typ,title in [('Trắc nghiệm','PHẦN A — TRẮC NGHIỆM'),('Đúng sai','PHẦN B — ĐÚNG / SAI'),('Trả lời ngắn','PHẦN C — TRẢ LỜI NGẮN'),('Tự luận','PHẦN D — TỰ LUẬN')]:
        arr=[q for q in qs if q['dang']==typ]
        if arr:sections.append({'title':title,'items':arr,'offset':offset});offset+=len(arr)
    return render_template_string(RESULT_TPL,subject=exam.get('subject',''),lesson=exam.get('lesson',''),path=exam.get('path',''),total=len(qs),score=score,correct=correct,auto=auto,essay=essay,time=exam.get('time',45),sections=sections)
