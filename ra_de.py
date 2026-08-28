# -*- coding: utf-8 -*-
"""Ra de giao vien: Toan + Vat ly, nguon GitHub.
- Muc luc dung ngan-hang/muc_luc.json de mo trang nhanh.
- Du lieu bai hoc duoc cache trong RAM, khong goi GitHub lap lai.
- Ho tro Phan A 4 lua chon, Phan B Dung/Sai, Phan C tra loi ngan, Phan D tu luan.
- Hien thi ro A/B/C/D va dap an; tu dong cham A/B/C, D danh dau chua cham.
"""
from __future__ import annotations

import base64
import json
import os
import random
import re
import time
import urllib.parse
from functools import lru_cache
from typing import Any, Dict, List

from flask import Blueprint, request, render_template_string, redirect, url_for, session

try:
    from github_integration import gh
except Exception:
    gh = None

bp = Blueprint("ra_de", __name__)
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
INDEX_PATH = "ngan-hang/muc_luc.json"
LETTERS = "ABCD"

CSS = r"""
<style>
:root{--blue:#1769d5;--blue2:#318de9;--line:#d7e3ef;--soft:#f4f8fd;--text:#18324b;--green:#159447;--orange:#d98900;--red:#d33}
*{box-sizing:border-box}body{margin:0;background:var(--soft);color:var(--text);font-family:Arial,Helvetica,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:14px 18px 80px}.top{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;border-radius:14px;padding:16px 20px;box-shadow:0 5px 18px #0002}.top h1{margin:0;font-size:24px}.top p{margin:5px 0 0}.nav{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.nav a,.btn{display:inline-flex;align-items:center;justify-content:center;gap:5px;padding:8px 13px;border-radius:9px;border:1px solid #cbd8e5;background:#fff;color:var(--blue);text-decoration:none;cursor:pointer;font-weight:700}.btn.green{background:var(--green);border-color:var(--green);color:#fff}.btn.blue{background:var(--blue);border-color:var(--blue);color:#fff}.btn.gray{background:#edf3f8;color:#284762}.card{background:#fff;border:1px solid var(--line);border-radius:13px;padding:14px;margin:12px 0;box-shadow:0 2px 10px #00000009}.crumb{font-size:13px;color:#657b90;margin:8px 0}.muted{color:#708398;font-size:12px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:10px}.folder{display:block;background:#fff;border:1px solid var(--line);border-radius:11px;padding:13px;text-decoration:none;color:var(--text)}.folder:hover{border-color:#7eb7ef;box-shadow:0 4px 14px #1976d21c}.folder b{display:block;margin-bottom:5px}.subjects{display:flex;gap:9px;flex-wrap:wrap}.subject{min-width:140px}.subject.active{background:var(--blue);color:#fff;border-color:var(--blue)}
.stats{display:flex;gap:7px;flex-wrap:wrap}.pill{border:1px solid #cfe1f7;background:#edf6ff;color:var(--blue);border-radius:999px;padding:5px 9px;font-size:12px;font-weight:800}.pill.orange{background:#fff7df;border-color:#f3d48b;color:#9a6700}.pill.green{background:#eaf8ef;border-color:#b9e4c8;color:#16743a}.pill.red{background:#fff0f0;border-color:#f0c0c0;color:#b42318}.filters{display:grid;grid-template-columns:repeat(6,minmax(130px,1fr));gap:9px;align-items:end}.field label{display:block;font-size:12px;font-weight:800;margin-bottom:5px}.field input,.field select{width:100%;padding:9px;border:1px solid #c9d7e4;border-radius:8px;background:#fff;color:var(--text)}.parts{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.partbox{border:1px solid var(--line);border-radius:11px;padding:12px;background:#fbfdff}.partbox h3{margin:0 0 6px;color:var(--blue);font-size:15px}.partbox .field{margin-top:8px}.pool{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}.poolcard{border:1px solid #dce7f1;border-radius:11px;padding:11px;background:#fff}.poolcard h4{margin:0 0 5px;color:var(--blue)}.tag{display:inline-block;border-radius:999px;padding:3px 7px;font-size:10px;font-weight:800;background:#eef5fb;margin:2px}.tag.dbt{background:#fff6dc;color:#8a5a00}.tag.lv{background:#eaf8ef;color:#16743a}.tag.dang{background:#f1ecff;color:#6941c6}.section{border:1px solid var(--line);border-radius:12px;padding:13px;margin:12px 0;background:#fff}.section h2{font-size:18px;margin:0 0 10px;color:#1559a5}.q{border:1px solid #dce6ef;border-radius:10px;padding:12px;margin:9px 0;background:#fff}.qhead{display:flex;gap:8px;align-items:center;margin-bottom:6px}.qnum{font-weight:900;color:var(--blue);font-size:15px}.qtext{line-height:1.6;white-space:pre-wrap}.opts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.opt{display:block;border:1px solid #dfe7ef;border-radius:8px;padding:9px;cursor:pointer}.opt:hover{background:#f5faff;border-color:#8ebcf0}.opt b{color:var(--blue)}.tfrow{border:1px solid #e1e7ee;border-radius:8px;padding:9px;margin:7px 0}.tfrow .letter{font-weight:900;color:var(--blue);margin-right:5px}.tfbtn{margin-left:10px}.answer{margin-top:9px}.answer input,.answer textarea{width:100%;padding:9px;border:1px solid #c9d7e4;border-radius:8px}.result{border:2px solid #b8dfc5;background:#effbf3;border-radius:12px;padding:14px;margin:12px 0}.wrong{border-color:#f2c0c0;background:#fff4f4}.ok{border-color:#b8dfc5;background:#f3fcf5}.notice{border:1px solid #f1d18b;background:#fff8e5;border-radius:10px;padding:11px;color:#795600}.answerkey{background:#f7f9fc;border:1px dashed #b7c6d6;border-radius:8px;padding:7px;margin-top:7px;font-size:13px}.sticky{position:fixed;right:16px;bottom:16px;z-index:20}
@media(max-width:1050px){.parts{grid-template-columns:1fr 1fr}.filters{grid-template-columns:repeat(3,1fr)}}@media(max-width:650px){.wrap{padding:10px}.parts,.filters{grid-template-columns:1fr 1fr}.opts{grid-template-columns:1fr}.top h1{font-size:20px}}
@media print{.nav,.no-print,.sticky{display:none!important}body{background:#fff}.wrap{max-width:none}.q{break-inside:avoid}.top{box-shadow:none}}
</style>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
"""

HOME_TPL = CSS + r'''
<div class="wrap">
<div class="top"><h1>📝 RA ĐỀ TỪ NGÂN HÀNG GITHUB</h1><p>Chọn <b>Môn → Khối → Chương → Bài</b>, sau đó chọn số câu cho <b>A/B/C/D</b>. Dữ liệu câu hỏi lấy trực tiếp từ GitHub và được cache.</p></div>
<div class="nav"><a href="/">🏠 Trang chủ</a><a class="btn {% if subject=='Vật lý' %}blue{% endif %}" href="/ra-de?subject=Vật%20lý">⚛ Vật lý</a><a class="btn {% if subject=='Toán' %}blue{% endif %}" href="/ra-de?subject=Toán">📐 Toán</a><a href="/github">🐙 GitHub</a></div>
{% if error %}<div class="notice">⚠️ {{error}}</div>{% endif %}
<div class="card"><h3 style="margin-top:0">1. Chọn môn</h3><div class="subjects"><a class="btn subject {% if subject=='Vật lý' %}active{% endif %}" href="/ra-de?subject=Vật%20lý">⚛ VẬT LÝ</a><a class="btn subject {% if subject=='Toán' %}active{% endif %}" href="/ra-de?subject=Toán">📐 TOÁN</a></div></div>
{% if subject %}<div class="card"><h3 style="margin-top:0">2. Chọn khối</h3><div class="grid">{% for x in grades %}<a class="folder" href="/ra-de?subject={{subject|urlencode}}&lop={{x}}"><b>📘 Lớp {{x}}</b><span class="muted">{{grade_counts.get(x,0)}} bài trong mục lục</span></a>{% endfor %}</div></div>{% endif %}
{% if lop %}<div class="card"><h3 style="margin-top:0">3. Chọn chương — Lớp {{lop}}</h3><div class="grid">{% for x in chapters %}<a class="folder" href="/ra-de?subject={{subject|urlencode}}&lop={{lop}}&chuong={{x|urlencode}}"><b>📚 {{x}}</b><span class="muted">Mở danh sách bài</span></a>{% endfor %}</div></div>{% endif %}
{% if chuong %}<div class="card"><h3 style="margin-top:0">4. Chọn bài</h3><div class="grid">{% for x in lessons %}<a class="folder" href="/ra-de?subject={{subject|urlencode}}&lop={{lop}}&chuong={{chuong|urlencode}}&path={{x.path|urlencode}}"><b>🎯 {{x.BaiHoc}}</b><span class="muted">{{x.count_questions}} câu · Mở để ra đề</span></a>{% endfor %}</div></div>{% endif %}
{% if lesson %}
<div class="crumb">{{subject}} › Lớp {{lop}} › {{chuong}} › {{lesson.BaiHoc}}</div>
<div class="card"><div class="stats"><span class="pill">{{counts.total}} câu</span><span class="pill">A · {{counts.A}} TN</span><span class="pill orange">B · {{counts.B}} Đ/S</span><span class="pill green">C · {{counts.C}} TLN</span><span class="pill red">D · {{counts.D}} Tự luận</span></div></div>
<form method="post" action="/ra-de/generate">
<input type="hidden" name="subject" value="{{subject}}"><input type="hidden" name="lop" value="{{lop}}"><input type="hidden" name="chuong" value="{{chuong}}"><input type="hidden" name="path" value="{{path}}">
<div class="card"><h3 style="margin-top:0">5. Cấu hình đề — giống cấu trúc bài tập trong app</h3>
<div class="parts">
<div class="partbox"><h3>PHẦN A — Trắc nghiệm</h3><div class="muted">Mỗi câu có A, B, C, D</div><div class="field"><label>Số câu</label><input name="nA" type="number" min="0" max="{{counts.A}}" value="10"></div></div>
<div class="partbox"><h3>PHẦN B — Đúng / Sai</h3><div class="muted">Mỗi câu có 4 ý A, B, C, D</div><div class="field"><label>Số câu</label><input name="nB" type="number" min="0" max="{{counts.B}}" value="2"></div></div>
<div class="partbox"><h3>PHẦN C — Trả lời ngắn</h3><div class="muted">Nhập đáp số</div><div class="field"><label>Số câu</label><input name="nC" type="number" min="0" max="{{counts.C}}" value="2"></div></div>
<div class="partbox"><h3>PHẦN D — Tự luận</h3><div class="muted">Giáo viên chấm</div><div class="field"><label>Số câu</label><input name="nD" type="number" min="0" max="{{counts.D}}" value="0"></div></div>
</div>
<div class="filters" style="margin-top:12px"><div class="field"><label>Dạng bài tập</label><select name="dbt"><option value="">Tất cả</option>{% for x,n in dbt_options %}<option value="{{x}}">{{x}} ({{n}})</option>{% endfor %}</select></div><div class="field"><label>Mức độ</label><select name="muc"><option value="">Tất cả</option><option>NB</option><option>TH</option><option>VD</option><option>VDC</option></select></div><div class="field"><label>Trộn câu</label><select name="shuffle"><option value="1">Có</option><option value="0">Không</option></select></div><div class="field"><label>Thời gian (phút)</label><input name="time" type="number" min="1" value="45"></div><div></div><div><button class="btn green" type="submit">🚀 TẠO ĐỀ A-B-C-D</button></div></div></div></form>
<div class="card"><h3 style="margin-top:0">📊 Ngân hàng câu hỏi — có phân loại dạng bài</h3><div class="pool">{% for q in preview %}<div class="poolcard"><h4>{{q.id or 'Câu'}}</h4><span class="tag dbt">{{q.dbt or 'Chưa phân loại'}}</span><span class="tag lv">{{q.muc or '—'}}</span><span class="tag dang">{{q.kind_label}}</span><div style="margin-top:7px;line-height:1.45">{{q.text}}</div></div>{% endfor %}</div></div>
{% endif %}
</div>
<script>window.MathJax&&MathJax.typesetPromise&&MathJax.typesetPromise();</script>
'''

EXAM_TPL = CSS + r'''
<div class="wrap"><div class="top"><h1>📝 {{title}}</h1><p>{{subject}} · {{lesson_name}} · {{total}} câu · {{time}} phút · Ngân hàng GitHub</p></div>
<div class="nav no-print"><a class="btn gray" href="/ra-de?subject={{subject|urlencode}}&lop={{lop}}&chuong={{chuong|urlencode}}&path={{path|urlencode}}">← Cấu hình lại</a><button class="btn gray" onclick="window.print()">🖨 In đề</button></div>
<div class="card no-print"><div class="stats"><span class="pill">Tổng {{total}} câu</span><span class="pill orange">{{time}} phút</span><span class="pill green">GitHub + Cache</span><span class="pill">A: {{counts.A}}</span><span class="pill orange">B: {{counts.B}}</span><span class="pill green">C: {{counts.C}}</span><span class="pill red">D: {{counts.D}}</span></div></div>
<form method="post" action="/ra-de/submit"><input type="hidden" name="exam_id" value="{{exam_id}}">
{% set offset=0 %}
{% if sections.A %}<div class="section"><h2>PHẦN A. TRẮC NGHIỆM NHIỀU LỰA CHỌN</h2>{% for q in sections.A %}<div class="q"><div class="qhead"><span class="qnum">Câu {{loop.index}}</span><span class="tag dbt">{{q.dbt or 'Chưa phân loại'}}</span><span class="tag lv">{{q.muc or '—'}}</span></div><div class="qtext">{{q.text}}</div><div class="opts">{% for o in q.options %}<label class="opt"><input type="radio" name="q_{{q.uid}}" value="{{loop.index0}}"> <b>{{letters[loop.index0]}}.</b> {{o.text}}</label>{% endfor %}</div></div>{% endfor %}</div>{% endif %}
{% if sections.B %}<div class="section"><h2>PHẦN B. TRẮC NGHIỆM ĐÚNG / SAI</h2>{% for q in sections.B %}<div class="q"><div class="qhead"><span class="qnum">Câu {{loop.index}}</span><span class="tag dbt">{{q.dbt or 'Chưa phân loại'}}</span><span class="tag lv">{{q.muc or '—'}}</span></div><div class="qtext">{{q.text}}</div>{% for o in q.options %}<div class="tfrow"><span class="letter">{{letters[loop.index0]}}.</span>{{o.text}}<label class="tfbtn"><input type="radio" name="q_{{q.uid}}_{{loop.index0}}" value="D"> Đúng</label><label class="tfbtn"><input type="radio" name="q_{{q.uid}}_{{loop.index0}}" value="S"> Sai</label></div>{% endfor %}</div>{% endfor %}</div>{% endif %}
{% if sections.C %}<div class="section"><h2>PHẦN C. TRẮC NGHIỆM TRẢ LỜI NGẮN</h2>{% for q in sections.C %}<div class="q"><div class="qhead"><span class="qnum">Câu {{loop.index}}</span><span class="tag dbt">{{q.dbt or 'Chưa phân loại'}}</span><span class="tag lv">{{q.muc or '—'}}</span></div><div class="qtext">{{q.text}}</div><div class="answer"><input name="q_{{q.uid}}" placeholder="Nhập đáp án ngắn"></div></div>{% endfor %}</div>{% endif %}
{% if sections.D %}<div class="section"><h2>PHẦN D. TỰ LUẬN</h2>{% for q in sections.D %}<div class="q"><div class="qhead"><span class="qnum">Câu {{loop.index}}</span><span class="tag dbt">{{q.dbt or 'Chưa phân loại'}}</span><span class="tag lv">{{q.muc or '—'}}</span></div><div class="qtext">{{q.text}}</div><div class="answer"><textarea name="q_{{q.uid}}" rows="6" placeholder="Trình bày bài làm"></textarea></div></div>{% endfor %}</div>{% endif %}
<div class="card no-print"><button class="btn green" type="submit">✅ NỘP BÀI — CHẤM ĐIỂM</button></div></form></div><script>window.MathJax&&MathJax.typesetPromise&&MathJax.typesetPromise();</script>
'''

RESULT_TPL = CSS + r'''
<div class="wrap"><div class="top"><h1>📊 KẾT QUẢ CHẤM ĐIỂM</h1><p>{{subject}} · {{lesson_name}}</p></div>
<div class="result"><h2 style="margin:0 0 8px">Điểm tự động: {{score}}/10</h2><div><b>Đúng:</b> {{correct}} câu/ý · <b>Tự luận:</b> {{essay}} câu chưa chấm</div><div class="muted" style="margin-top:6px">Điểm tự động được chuẩn hóa theo các câu A/B/C có đáp án; phần D để giáo viên chấm riêng.</div></div>
{% for sec_name,items in sections %}{% if items %}<div class="section"><h2>PHẦN {{sec_name}}</h2>{% for q in items %}<div class="q {% if q.ok is true %}ok{% elif q.ok is false %}wrong{% endif %}"><div class="qhead"><span class="qnum">Câu {{loop.index}}</span>{% if q.ok is true %}<span>✅</span>{% elif q.ok is false %}<span>❌</span>{% endif %}</div><div class="qtext">{{q.text}}</div>{% if q.chosen %}<div>Em chọn/nhập: <b>{{q.chosen}}</b></div>{% endif %}<div class="answerkey">Đáp án: <b>{{q.answer_display}}</b>{% if q.kind=='D' %} · <span class="muted">Giáo viên chấm</span>{% endif %}</div></div>{% endfor %}</div>{% endif %}{% endfor %}
<div class="nav"><a class="btn blue" href="/ra-de?subject={{subject|urlencode}}&lop={{lop}}&chuong={{chuong|urlencode}}&path={{path|urlencode}}">🔄 Ra đề khác</a><a class="btn gray" href="/">🏠 Trang chủ</a></div></div><script>window.MathJax&&MathJax.typesetPromise&&MathJax.typesetPromise();</script>
'''

def _clean(s: Any) -> str:
    return str(s or "").strip()

def _gate():
    if not session.get("mahs"):
        return redirect(url_for("login", next=request.full_path.rstrip("?")))
    try:
        from app import is_admin
        if not is_admin():
            return ("<h3>403 — Chỉ ADMIN được dùng chức năng Ra đề.</h3>", 403)
    except Exception:
        pass
    return None

def _require_gh():
    if gh is None:
        raise RuntimeError("Không tải được mô-đun GitHub.")

def _gh(path: str, ref: str="main") -> Any:
    _require_gh()
    p=urllib.parse.quote(path.strip('/'), safe='/')
    return gh(f"/repos/{REPO}/contents/{p}?ref={urllib.parse.quote(ref)}")

def _decode_file(data: Dict[str,Any]) -> str:
    return base64.b64decode(_clean(data.get("content")).replace("\n","")).decode("utf-8","replace")

@lru_cache(maxsize=1)
def _index() -> List[Dict[str,Any]]:
    d=_gh(INDEX_PATH)
    raw=_decode_file(d)
    obj=json.loads(raw)
    return obj.get("lessons",[]) if isinstance(obj,dict) else []

def _balanced(text: str, pos: int):
    while pos < len(text) and text[pos].isspace(): pos += 1
    if pos>=len(text) or text[pos] != '{': return None,pos
    depth=0; start=pos+1; i=pos
    while i<len(text):
        c=text[i]
        if c=='{' and (i==0 or text[i-1] != '\\'): depth += 1
        elif c=='}' and (i==0 or text[i-1] != '\\'):
            depth -= 1
            if depth==0: return text[start:i],i+1
        i += 1
    return None,pos

def _arg(text: str, pos: int):
    return _balanced(text,pos)

def _strip_meta(s: str) -> str:
    s=re.sub(r'(?m)^\s*%.*$', '', s)
    s=re.sub(r'\\(?:nguon|label)\{.*?\}', '', s, flags=re.S)
    s=re.sub(r'\\(?:centering|small|footnotesize|normalsize|large|Large)\b', '', s)
    s=re.sub(r'\\vspace\{.*?\}', '', s)
    s=re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def _extract_options(block: str, command: str):
    m=re.search(re.escape(command),block)
    if not m: return []
    out=[]; pos=m.end()
    while True:
        val,nxt=_arg(block,pos)
        if val is None: break
        out.append(val.strip()); pos=nxt
    return out

def _normalize(s: str) -> str:
    s=_clean(s).lower().replace(',', '.').replace(' ', '')
    s=re.sub(r'\$','',s)
    return s

def _parse_tex(text: str, path: str) -> List[Dict[str,Any]]:
    blocks=re.findall(r'\\begin\{(?:ex|bt)\}(.*?)\\end\{(?:ex|bt)\}', text, flags=re.S)
    out=[]; uid=0
    for block in blocks:
        uid+=1
        mid=re.search(r'%\s*ID:\s*([^\n\r]+)',block)
        mmu=re.search(r'%\s*Mức:\s*([^\n\r]+)',block)
        mdb=re.search(r'\\dangbt\{',block)
        dbt=''
        if mdb:
            a,_=_arg(block,mdb.end()-1); dbt=_strip_meta(a or '')
        kind='D'; label='Tự luận'; options=[]; answer=''
        cmd_tf=re.search(r'\\choiceTF\b',block)
        cmd_mc=re.search(r'\\choice\b',block)
        cmd_sa=re.search(r'\\shortans\s*\{',block)
        if cmd_tf:
            kind='B'; label='Đúng / Sai'; vals=_extract_options(block,'\\choiceTF')
            for v in vals[:4]:
                true='\\True' in v
                v=re.sub(r'\\True\s*','',v).strip()
                options.append({'text':_strip_meta(v),'answer':'D' if true else 'S'})
            end=cmd_tf.end()
            text_part=block[:cmd_tf.start()]
        elif cmd_mc:
            kind='A'; label='Trắc nghiệm'; vals=_extract_options(block,'\\choice')
            for v in vals[:4]:
                true='\\True' in v
                v=re.sub(r'\\True\s*','',v).strip()
                options.append({'text':_strip_meta(v),'answer':len(options) if not true else len(options)})
                if true: answer=len(options)-1
            end=cmd_mc.end(); text_part=block[:cmd_mc.start()]
        elif cmd_sa:
            kind='C'; label='Trả lời ngắn'; a,_=_arg(block,cmd_sa.end()-1); answer=_strip_meta(a or '')
            text_part=block[:cmd_sa.start()]
        else:
            text_part=block
        text_part=re.sub(r'\\loigiai\s*\{.*', '', text_part, flags=re.S)
        text_part=re.sub(r'\\dangbt\{.*?\}', '', text_part, flags=re.S)
        q={'uid':f'q{uid}','id':_clean(mid.group(1)) if mid else '', 'muc':_clean(mmu.group(1)) if mmu else '', 'dbt':dbt, 'kind':kind, 'kind_label':label, 'text':_strip_meta(text_part), 'options':options, 'answer':answer, 'path':path}
        if kind=='A':
            for i,o in enumerate(options): o['answer']=i
        out.append(q)
    return out

@lru_cache(maxsize=256)
def _load_lesson(path: str) -> List[Dict[str,Any]]:
    d=_gh('ngan-hang/'+path if not path.startswith('ngan-hang/') else path)
    return _parse_tex(_decode_file(d),path)

def _clear_cache():
    _index.cache_clear(); _load_lesson.cache_clear()

def _filter(qs,dbt='',muc=''):
    return [q for q in qs if (not dbt or q['dbt']==dbt) and (not muc or q['muc']==muc)]

def _counts(qs):
    return {'total':len(qs),'A':sum(q['kind']=='A' for q in qs),'B':sum(q['kind']=='B' for q in qs),'C':sum(q['kind']=='C' for q in qs),'D':sum(q['kind']=='D' for q in qs)}

def _render_home(**kw):
    return render_template_string(HOME_TPL,repo=REPO,**kw)

@bp.route('/ra-de',methods=['GET'])
def home():
    g=_gate()
    if g:return g
    if request.args.get('refresh')=='1': _clear_cache()
    subject=request.args.get('subject','Vật lý')
    if subject not in ('Vật lý','Toán'): subject='Vật lý'
    lop=request.args.get('lop','').strip(); chuong=request.args.get('chuong','').strip(); path=request.args.get('path','').strip()
    try: rows=[x for x in _index() if x.get('Mon')==subject]
    except Exception as e: return _render_home(subject=subject,grades=[],grade_counts={},chapters=[],lessons=[],lesson=None,counts=_counts([]),preview=[],dbt_options=[],path=path,lop=lop,chuong=chuong,error=str(e))
    grades=sorted({str(x.get('Lop','')) for x in rows if x.get('Lop')},key=lambda x:int(x) if x.isdigit() else 999)
    grade_counts={g:sum(1 for x in rows if str(x.get('Lop'))==g) for g in grades}
    r2=[x for x in rows if str(x.get('Lop'))==lop] if lop else []
    chapters=[]
    if lop: chapters=sorted({x.get('Chuong','') for x in r2})
    r3=[x for x in r2 if x.get('Chuong')==chuong] if chuong else []
    lessons=sorted(r3,key=lambda x:x.get('BaiHoc','')) if chuong else []
    lesson=None; qs=[]; counts=_counts([]); preview=[]; dbt_options=[]
    if path:
        lesson=next((x for x in rows if x.get('path')==path),None)
        if lesson:
            qs=_load_lesson(path); counts=_counts(qs); preview=qs[:24]
            dc={}
            for q in qs:
                if q['dbt']: dc[q['dbt']]=dc.get(q['dbt'],0)+1
            dbt_options=sorted(dc.items())
    crumbs=[subject];
    if lop: crumbs.append('Lớp '+lop)
    if chuong: crumbs.append(chuong)
    if lesson: crumbs.append(lesson.get('BaiHoc',''))
    return _render_home(subject=subject,grades=grades,grade_counts=grade_counts,chapters=chapters,lessons=lessons,lesson=lesson,counts=counts,preview=preview,dbt_options=dbt_options,path=path,lop=lop,chuong=chuong,error='',crumbs=crumbs)

@bp.route('/ra-de/generate',methods=['POST'])
def generate():
    g=_gate()
    if g:return g
    path=_clean(request.form.get('path')); subject=_clean(request.form.get('subject')) or 'Vật lý'; lop=_clean(request.form.get('lop')); chuong=_clean(request.form.get('chuong'))
    try:
        qs=_load_lesson(path)
        dbt=_clean(request.form.get('dbt')); muc=_clean(request.form.get('muc'))
        qs=_filter(qs,dbt,muc)
        nums={k:max(0,int(request.form.get(k,0) or 0)) for k in ('nA','nB','nC','nD')}
        pools={k:[q for q in qs if q['kind']==k] for k in 'ABCD'}
        selected={}
        for k in 'ABCD':
            n=nums[k]
            if n>len(pools[k]): raise RuntimeError(f'Phần {k} cần {n} câu nhưng chỉ có {len(pools[k])} câu phù hợp bộ lọc.')
            selected[k]=random.sample(pools[k],n) if request.form.get('shuffle','1')=='1' else pools[k][:n]
        exam_id=f"{int(time.time()*1000)}-{random.randint(1000,9999)}"
        exams=session.setdefault('ra_de_exams',{})
        exams[exam_id]={'sections':selected,'subject':subject,'lop':lop,'chuong':chuong,'path':path,'lesson_name':next((x.get('BaiHoc','') for x in _index() if x.get('path')==path),path),'time':int(request.form.get('time',45) or 45)}
        session.modified=True
        return redirect(url_for('ra_de.exam',exam_id=exam_id))
    except Exception as e:
        return f'<div style="font:16px Arial;padding:30px"><h3>Không tạo được đề</h3><p>{e}</p><a href="/ra-de">Quay lại</a></div>'

@bp.route('/ra-de/exam/<exam_id>',methods=['GET'])
def exam(exam_id):
    g=_gate()
    if g:return g
    data=session.get('ra_de_exams',{}).get(exam_id)
    if not data:return redirect('/ra-de')
    sections=data['sections']; counts={k:len(sections.get(k,[])) for k in 'ABCD'}
    return render_template_string(EXAM_TPL,title='Đề luyện tập',subject=data['subject'],lesson_name=data['lesson_name'],total=sum(counts.values()),time=data['time'],exam_id=exam_id,sections=sections,counts=counts,letters=list(LETTERS),path=data['path'],lop=data['lop'],chuong=data['chuong'])

def _chosen_display(q,form):
    if q['kind']=='A':
        v=form.get('q_'+q['uid'],'');
        try: return LETTERS[int(v)]
        except: return _clean(v)
    if q['kind']=='B':
        return ' · '.join(f"{LETTERS[i]}:{form.get('q_'+q['uid']+'_'+str(i),'—')}" for i in range(min(4,len(q['options']))))
    return _clean(form.get('q_'+q['uid'],''))

def _grade(q,form):
    chosen=_chosen_display(q,form)
    if q['kind']=='A':
        v=form.get('q_'+q['uid'],'')
        try: ok=int(v)==int(q['answer'])
        except: ok=False
        return ok,chosen
    if q['kind']=='B':
        got=[form.get('q_'+q['uid']+'_'+str(i),'') for i in range(len(q['options']))]
        want=[o['answer'] for o in q['options']]
        return got==want,chosen
    if q['kind']=='C': return _normalize(chosen)==_normalize(q['answer']),chosen
    return None,chosen

@bp.route('/ra-de/submit',methods=['POST'])
def submit():
    g=_gate()
    if g:return g
    exam_id=_clean(request.form.get('exam_id')); data=session.get('ra_de_exams',{}).get(exam_id)
    if not data:return redirect('/ra-de')
    sections=data['sections']; result={}; earned=0; max_auto=0; correct=0; essay=0
    for k in 'ABCD':
        result[k]=[]
        for q in sections.get(k,[]):
            ok,chosen=_grade(q,request.form)
            if k=='A': max_auto+=1
            elif k=='B': max_auto+=1
            elif k=='C': max_auto+=1
            if ok is True: earned+=1; correct+=1
            if k=='B' and ok is True: pass
            if k=='D': essay+=1
            q2=dict(q); q2['ok']=ok; q2['chosen']=chosen
            if k=='A': q2['answer_display']=LETTERS[q['answer']] if isinstance(q['answer'],int) and q['answer']<4 else str(q['answer'])
            elif k=='B': q2['answer_display']=' · '.join(f"{LETTERS[i]}:{q['options'][i]['answer']}" for i in range(len(q['options'])))
            else: q2['answer_display']=q['answer'] if k=='C' else 'Tự luận — giáo viên chấm'
            result[k].append(q2)
    score=round(earned/max_auto*10,2) if max_auto else 0
    return render_template_string(RESULT_TPL,subject=data['subject'],lesson_name=data['lesson_name'],total=sum(len(v) for v in sections.values()),score=score,correct=correct,essay=essay,sections=[(k,result[k]) for k in 'ABCD'],path=data['path'],lop=data['lop'],chuong=data['chuong'])
''