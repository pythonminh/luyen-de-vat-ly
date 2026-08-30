# -*- coding: utf-8 -*-
"""
Ra đề — tạo đề thi từ ngân hàng câu hỏi GitHub (ngan-hang/*.tex), dựa trên
bank_index.json đã có sẵn trong repo (tạo bởi scripts/build_bank_index.py).

Route chính:
  GET  /ra-de            -> trang chọn Môn/Lớp/Chương/Bài + số câu theo từng dạng
                            (và theo từng loại câu: Trắc nghiệm/Đúng sai/Trả lời ngắn/Tự luận)
  POST /ra-de/generate   -> ghép các câu được chọn (random) thành 1 file .tex,
                            xem trước trong trình duyệt + tải file .tex.

Thêm:
  GET /ra-de/download-word/<token> -> tải đề Word .docx.
"""
from __future__ import annotations

import io
import json
import os
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, Response, request, render_template_string, send_file
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

bp = Blueprint("ra_de", __name__)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BANK_INDEX_PATH = os.path.join(APP_DIR, "bank_index.json")

_BLOCK_RE = re.compile(r"\\begin\s*\{\s*(ex|bt)\s*\}(.*?)\\end\s*\{\s*\1\s*\}", re.S | re.I)
_DANGBT_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)
_CHOICE_TF_RE = re.compile(r"\\choiceTF\b", re.I)
_SHORTANS_RE = re.compile(r"\\shortans\b", re.I)
_CHOICE_RE = re.compile(r"\\choice\b", re.I)
LOAI_CAU_LIST = ["Trắc nghiệm", "Đúng sai", "Trả lời ngắn", "Tự luận"]


def _loai_cau_of_block(body: str) -> str:
    body = body or ""
    if _CHOICE_TF_RE.search(body):
        return "Đúng sai"
    if _SHORTANS_RE.search(body):
        return "Trả lời ngắn"
    if _CHOICE_RE.search(body):
        return "Trắc nghiệm"
    return "Tự luận"


def _load_bank_index() -> Dict[str, Any]:
    try:
        with open(BANK_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"schema": 1, "total_files": 0, "total_questions": 0, "lessons": []}


def _resolve_tex_path(rel_path: str) -> str:
    rel = (rel_path or "").replace("\\", "/").lstrip("/")
    return os.path.join(APP_DIR, rel.replace("/", os.sep))


def extract_blocks_by_dang(text: str) -> List[Tuple[str, str, str]]:
    text = text or ""
    markers = [(m.start(), (m.group(1) or "").strip()) for m in _DANGBT_RE.finditer(text)]
    out: List[Tuple[str, str, str]] = []
    mi = 0
    current = ""
    for m in _BLOCK_RE.finditer(text):
        pos = m.start()
        while mi < len(markers) and markers[mi][0] < pos:
            current = markers[mi][1]
            mi += 1
        name = current or "Chưa phân dạng"
        loai_cau = _loai_cau_of_block(m.group(0))
        out.append((name, loai_cau, m.group(0)))
    return out


def _read_tex_text(rel_path: str) -> str:
    path = _resolve_tex_path(rel_path)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def blocks_grouped_by_dang(rel_path: str) -> Dict[str, List[str]]:
    text = _read_tex_text(rel_path)
    grouped: Dict[str, List[str]] = {}
    for name, _loai_cau, block in extract_blocks_by_dang(text):
        grouped.setdefault(name, []).append(block)
    return grouped


def blocks_grouped_by_dang_loai(rel_path: str) -> Dict[str, Dict[str, List[str]]]:
    text = _read_tex_text(rel_path)
    grouped: Dict[str, Dict[str, List[str]]] = {}
    for name, loai_cau, block in extract_blocks_by_dang(text):
        grouped.setdefault(name, {}).setdefault(loai_cau, []).append(block)
    return grouped


def dang_loai_counts(rel_path: str) -> Dict[str, Dict[str, int]]:
    grouped = blocks_grouped_by_dang_loai(rel_path)
    return {
        dang: {lc: len(loai_map.get(lc, [])) for lc in LOAI_CAU_LIST}
        for dang, loai_map in grouped.items()
    }


PAGE_TPL = r"""
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📝 Ra đề — Luyện đề Vật lý</title>
<style>
body{font-family:Arial,Helvetica,sans-serif;background:#f6f8fa;color:#172b4d;margin:0}
.wrap{max-width:1200px;margin:20px auto;padding:0 16px 80px}
h1{font-size:22px;margin:5px 0 8px}
.card{background:#fff;border:1px solid #d0d7de;border-radius:12px;padding:16px;margin-bottom:14px}
.lesson{border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin:8px 0}
.lesson summary{cursor:pointer;font-weight:700}
.dang-block{border-top:1px dashed #e5e7eb;padding:9px 4px}
.dang-title{font-weight:600;margin-bottom:7px}
.type-grid{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:8px}
.type-box{display:flex;align-items:center;gap:7px;border:1px solid #dbe3ec;border-radius:8px;padding:8px;background:#fff}
.type-box input[type=number]{width:54px;padding:5px;border:1px solid #cbd5e1;border-radius:6px;margin-left:auto}
.type-box input[type=number]:disabled{background:#f1f5f9;color:#94a3b8}
.type-box.type-a{border-left:4px solid #2563eb}
.type-box.type-b{border-left:4px solid #7c3aed}
.type-box.type-c{border-left:4px solid #059669}
.type-box.type-d{border-left:4px solid #ea580c}
.type-name{font-size:13px;font-weight:600}
.type-count{font-size:12px;color:#64748b}
.muted{color:#64748b;font-size:13px}
.top-actions{position:sticky;top:0;background:#f6f8fa;padding:10px 0;z-index:5}
button,.btn{background:#1976d2;color:#fff;border:none;padding:9px 14px;border-radius:8px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}
button.secondary,.btn.secondary{background:#64748b}
button.small{padding:5px 9px;font-size:12px;background:#475569;margin-right:4px}
.search{width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:10px}
.badge{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:999px;padding:2px 8px;font-size:12px;margin-left:6px}
.legend{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}
.legend span{border:1px solid #dbe3ec;border-radius:999px;padding:4px 9px;font-size:12px;background:#fff}
.lesson-tools{margin:8px 0}
@media(max-width:850px){.type-grid{grid-template-columns:repeat(2,minmax(170px,1fr))}}
@media(max-width:520px){.type-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
<div class="top-actions">
  <h1>📝 Ra đề từ ngân hàng GitHub</h1>
  <p class="muted">Nguồn: <b>{{ total_files }}</b> file · <b>{{ total_questions }}</b> câu hỏi. Tick A/B/C/D ở từng dạng bài rồi nhập số câu.</p>
  <div class="legend">
    <span>🔵 A — Trắc nghiệm 4 lựa chọn</span>
    <span>🟣 B — Đúng / Sai</span>
    <span>🟢 C — Trả lời ngắn</span>
    <span>🟠 D — Tự luận</span>
  </div>
</div>
<form method="post" action="{{ url_for('ra_de.generate') }}">
  <div class="card">
    <input class="search" id="q" placeholder="🔎 Lọc theo Môn / Lớp / Chương / Bài..." onkeyup="filterLessons()">
    <label class="muted">Tên đề (tùy chọn):
      <input type="text" name="ten_de" placeholder="Đề ôn tập..." style="padding:6px 8px;border:1px solid #cbd5e1;border-radius:6px">
    </label>
  </div>
  {% for group_key, lessons in groups.items() %}
  <div class="card lesson-group" data-key="{{ group_key|lower }}">
    <h3>{{ group_key }}</h3>
    {% for item in lessons %}
    <details class="lesson">
      <summary>{{ item.BaiHoc or item.path }} <span class="badge">{{ item.questions }} câu</span></summary>
      <div class="lesson-tools">
        <button type="button" class="small" onclick="setLessonType(this,'A',true)">☑ Chọn A</button>
        <button type="button" class="small" onclick="setLessonType(this,'B',true)">☑ Chọn B</button>
        <button type="button" class="small" onclick="setLessonType(this,'C',true)">☑ Chọn C</button>
        <button type="button" class="small" onclick="setLessonType(this,'D',true)">☑ Chọn D</button>
        <button type="button" class="small" onclick="setLessonType(this,'ALL',true)">☑ Chọn cả 4</button>
        <button type="button" class="small" onclick="setLessonType(this,'ALL',false)">☐ Bỏ chọn</button>
      </div>
      {% for dang, counts in item.dang_loai.items() %}
      {% set dang_idx = loop.index0 %}
      <div class="dang-block">
        <div class="dang-title">{{ dang }} <span class="muted">— A: {{ counts.get("Trắc nghiệm",0) }}, B: {{ counts.get("Đúng sai",0) }}, C: {{ counts.get("Trả lời ngắn",0) }}, D: {{ counts.get("Tự luận",0) }}</span></div>
        <div class="type-grid">
          {% for loai_cau, code in [("Trắc nghiệm","A"),("Đúng sai","B"),("Trả lời ngắn","C"),("Tự luận","D")] %}
          {% set n2 = counts.get(loai_cau, 0) %}
          <label class="type-box type-{{ code|lower }}">
            <input type="checkbox" class="type-check" data-type="{{ code }}" data-max="{{ n2 }}" data-key="{{ item._ra_index }}|{{ dang_idx }}|{{ code }}" {% if n2 <= 0 %}disabled{% endif %} onchange="toggleCount(this)">
            <span class="type-name">{{ code }}. {{ loai_cau }}</span>
            <span class="type-count">({{ n2 }} câu)</span>
            <input type="number" min="0" max="{{ n2 }}" value="0" class="count-input" data-type="{{ code }}" disabled>
          </label>
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </details>
    {% endfor %}
  </div>
  {% endfor %}
  <input type="hidden" name="selections" id="selections">
  <div class="card"><button type="submit">✅ Tạo đề (.tex)</button><a class="btn secondary" href="{{ url_for('ra_de.home') }}">↺ Làm lại</a></div>
</form>
</div>
<script>
function toggleCount(check){const box=check.closest('.type-box');const input=box.querySelector('.count-input');input.disabled=!check.checked;if(check.checked){if(Number(input.value)<=0)input.value=1;const max=Number(check.dataset.max||0);if(Number(input.value)>max)input.value=max;}else input.value=0;}
function setLessonType(button,type,checked){const lesson=button.closest('.lesson');lesson.querySelectorAll('.type-check').forEach(function(check){if(type==='ALL'||check.dataset.type===type){if(!check.disabled){check.checked=checked;toggleCount(check);}}});}
function filterLessons(){const q=(document.getElementById('q').value||'').toLowerCase();document.querySelectorAll('.lesson-group').forEach(function(g){const show=!q||g.dataset.key.indexOf(q)>=0||g.innerText.toLowerCase().indexOf(q)>=0;g.style.display=show?'':'none';});}
document.querySelector('form').addEventListener('submit',function(){const selections=[];document.querySelectorAll('.type-check:checked').forEach(function(check){const box=check.closest('.type-box');const input=box.querySelector('.count-input');const n=Number(input.value||0);if(n>0)selections.push({k:check.dataset.key,n:n});});document.getElementById('selections').value=JSON.stringify(selections);});
</script>
</body>
</html>
"""

RESULT_TPL = r"""
<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>📝 Đề đã tạo</title>
<style>body{font-family:Arial,Helvetica,sans-serif;background:#f6f8fa;color:#172b4d;margin:0}.wrap{max-width:1000px;margin:20px auto;padding:0 16px 60px}.card{background:#fff;border:1px solid #d0d7de;border-radius:12px;padding:16px;margin-bottom:14px}pre{white-space:pre-wrap;word-break:break-word;background:#0f172a;color:#e2e8f0;padding:14px;border-radius:10px;max-height:70vh;overflow:auto}button,.btn{background:#1976d2;color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}.btn.secondary{background:#64748b}</style>
</head><body><div class="wrap"><div class="card"><h2>✅ Đã tạo đề — {{ total }} câu</h2><p><a class="btn" href="{{ url_for('ra_de.download', token=token) }}">⬇️ Tải file .tex</a><a class="btn" href="{{ url_for('ra_de.download_word', token=token) }}">📝 Tải Word (.docx)</a><a class="btn secondary" href="{{ url_for('ra_de.home') }}">↺ Tạo đề khác</a></p></div><div class="card"><h3>Xem trước</h3><pre>{{ content }}</pre></div></div></body></html>
"""

_LAST_GENERATED: Dict[str, str] = {}

@bp.route("/ra-de")
def home():
    data = _load_bank_index()
    lessons = data.get("lessons") or []
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for lesson_idx, item in enumerate(lessons):
        if not isinstance(item, dict):
            continue
        mon = item.get("Mon") or "Khác"
        lop = item.get("Lop") or ""
        chuong = item.get("Chuong") or ""
        key = f"{mon} · Lớp {lop} · {chuong}".strip()
        item = dict(item)
        item["_ra_index"] = lesson_idx
        item["dang_loai"] = dang_loai_counts(item.get("path") or "")
        groups.setdefault(key, []).append(item)
    return render_template_string(PAGE_TPL, groups=groups, total_files=data.get("total_files", len(lessons)), total_questions=data.get("total_questions", 0))


def _parse_compact_selections(raw: str, lessons: List[Dict[str, Any]]) -> List[Tuple[str, str, str, int]]:
    try:
        data = json.loads(raw or "[]")
    except Exception:
        return []
    result: List[Tuple[str, str, str, int]] = []
    code_to_name = {"A":"Trắc nghiệm","B":"Đúng sai","C":"Trả lời ngắn","D":"Tự luận"}
    for row in data:
        if not isinstance(row, dict):
            continue
        try:
            key = str(row.get("k") or "")
            n = int(row.get("n") or 0)
        except Exception:
            continue
        if n <= 0:
            continue
        bits = key.split("|")
        if len(bits) != 3:
            continue
        try:
            lesson_idx, dang_idx = int(bits[0]), int(bits[1])
        except Exception:
            continue
        loai_code = bits[2].upper()
        if loai_code not in code_to_name or not (0 <= lesson_idx < len(lessons)):
            continue
        path = str(lessons[lesson_idx].get("path") or "")
        if not path:
            continue
        dang_map = dang_loai_counts(path)
        dang_names = list(dang_map.keys())
        if not (0 <= dang_idx < len(dang_names)):
            continue
        dang = dang_names[dang_idx]
        loai_cau = code_to_name[loai_code]
        n = min(n, int(dang_map[dang].get(loai_cau, 0)))
        if n > 0:
            result.append((path, dang, loai_cau, n))
    return result

@bp.route("/ra-de/generate", methods=["POST"])
def generate():
    ten_de = (request.form.get("ten_de") or "Đề ôn tập").strip()
    data = _load_bank_index()
    lessons = data.get("lessons") or []
    selections = _parse_compact_selections(request.form.get("selections") or "[]", lessons)
    wanted: Dict[str, Dict[str, Dict[str, int]]] = {x:{} for x in LOAI_CAU_LIST}
    for path, dang, loai_cau, n in selections:
        wanted.setdefault(loai_cau, {}).setdefault(path, {})[dang] = n

    picked: Dict[str, List[str]] = {x:[] for x in LOAI_CAU_LIST}
    errors: List[str] = []
    for loai_cau in LOAI_CAU_LIST:
        for path, dang_counts in wanted[loai_cau].items():
            grouped = blocks_grouped_by_dang_loai(path)
            if not grouped:
                errors.append(f"Không đọc được: {path}")
                continue
            for dang, n in dang_counts.items():
                pool = (grouped.get(dang) or {}).get(loai_cau) or []
                if pool:
                    picked[loai_cau].extend(random.sample(pool, min(n, len(pool))))
    for loai_cau in picked:
        random.shuffle(picked[loai_cau])

    counts = {loai: len(blocks) for loai, blocks in picked.items()}
    total = sum(counts.values())
    part_titles = {"Trắc nghiệm":"PHẦN A. TRẮC NGHIỆM 4 LỰA CHỌN","Đúng sai":"PHẦN B. TRẮC NGHIỆM ĐÚNG / SAI","Trả lời ngắn":"PHẦN C. TRẢ LỜI NGẮN","Tự luận":"PHẦN D. TỰ LUẬN"}
    part_codes = {"Trắc nghiệm":"A","Đúng sai":"B","Trả lời ngắn":"C","Tự luận":"D"}
    parts: List[str] = []
    for loai_cau in LOAI_CAU_LIST:
        blocks = picked[loai_cau]
        if not blocks:
            continue
        parts.extend([f"% ==================================================\n", f"% {part_titles[loai_cau]}\n", "% ==================================================\n\n"])
        for i, block in enumerate(blocks, 1):
            parts.append(f"% ===== {part_codes[loai_cau]} - Câu {i} =====\n{block.strip()}\n\n")
    header = (f"% ===== {ten_de} =====\n% Tự động tạo bởi Ra đề — {total} câu\n% A={counts['Trắc nghiệm']} | B={counts['Đúng sai']} | C={counts['Trả lời ngắn']} | D={counts['Tự luận']}\n\n")
    content = header + "".join(parts)
    if errors:
        content += "\n\n% Lỗi:\n% " + "\n% ".join(errors)
    if total == 0:
        content += "% Chưa có câu nào được chọn.\n% Hãy tick A/B/C/D và nhập số câu > 0.\n"
    token = f"{random.randint(100000, 999999)}"
    _LAST_GENERATED[token] = content
    return render_template_string(RESULT_TPL, content=content, total=total, token=token)


def _read_braced_arg(s: str, start: int) -> Tuple[str, int]:
    n, i = len(s), start
    while i < n and s[i].isspace(): i += 1
    if i >= n or s[i] != "{": return "", start
    depth, begin = 0, i + 1
    i += 1
    while i < n:
        ch = s[i]
        if ch == "\\": i += 2; continue
        if ch == "{": depth += 1
        elif ch == "}":
            if depth == 0: return s[begin:i], i + 1
            depth -= 1
        i += 1
    return s[begin:], n


def _extract_n_args(s: str, start: int, count: int) -> List[str]:
    args, pos = [], start
    for _ in range(count):
        arg, pos2 = _read_braced_arg(s, pos)
        if pos2 == pos: break
        args.append(arg); pos = pos2
    return args


def _remove_macro_block(s: str, macro: str) -> str:
    pat = re.compile(r"\\" + re.escape(macro) + r"\s*\{", re.I)
    while True:
        m = pat.search(s)
        if not m: return s
        _, end = _read_braced_arg(s, m.end() - 1)
        s = s[:m.start()] + s[end:]


def _tex_to_word_text(s: str) -> str:
    s = s or ""
    s = re.sub(r"%.*$", "", s, flags=re.M)
    s = re.sub(r"\\begin\s*\{\s*tikzpicture\s*\}.*?\\end\s*\{\s*tikzpicture\s*\}", "[Hình minh họa]", s, flags=re.S|re.I)
    s = re.sub(r"\\(?:textbf|mathbf|mathrm|textit|emph|textrm|text|underline)\s*\{([^{}]*)\}", r"\1", s)
    for old,new in {r"\quad":"    ",r"\qquad":"        ",r"\,":" ",r"\;":" ",r"\!":"",r"\ldots":"...",r"\dots":"...",r"\times":"×",r"\cdot":"·",r"\le":"≤",r"\ge":"≥",r"\neq":"≠",r"\approx":"≈",r"\pm":"±",r"\to":"→",r"\rightarrow":"→",r"\Rightarrow":"⇒",r"\infty":"∞",r"\alpha":"α",r"\beta":"β",r"\gamma":"γ",r"\Delta":"Δ",r"\Omega":"Ω"}.items(): s=s.replace(old,new)
    for _ in range(6):
        old=s; s=re.sub(r"\\(?:d?frac)\s*\{([^{}]*)\}\s*\{([^{}]*)\}",r"(\1)/(\2)",s)
        if s==old: break
    s=s.replace("$$","")
    s=re.sub(r"\$(.*?)\$",r"\1",s,flags=re.S)
    s=re.sub(r"\\(?:left|right|big|Big|bigg|Bigg)\b","",s)
    s=re.sub(r"\\[a-zA-Z]+\*?(?!\w)","",s)
    return re.sub(r"\n{3,}","\n\n",s).strip()


def _parse_question_block(block: str) -> Tuple[str, List[str], str]:
    raw=block or ""; typ="D"; options=[]
    m=re.search(r"\\choiceTF\b",raw,re.I)
    if m: typ="B"; body=raw[:m.start()]; options=_extract_n_args(raw,m.end(),4)
    else:
        m=re.search(r"\\choice\b",raw,re.I)
        if m: typ="A"; body=raw[:m.start()]; options=_extract_n_args(raw,m.end(),4)
        else:
            m=re.search(r"\\shortans\b",raw,re.I)
            if m: typ="C"; body=raw[:m.start()]; options=_extract_n_args(raw,m.end(),1)
            else: body=raw
    body=_remove_macro_block(body,"loigiai")
    body=_remove_macro_block(body,"dapan")
    body=re.sub(r"\\end\s*\{\s*(ex|bt)\s*\}","",body,flags=re.I)
    body=re.sub(r"\\begin\s*\{\s*(ex|bt)\s*\}","",body,flags=re.I)
    body=re.sub(r"^\s*%\s*.*$","",body,flags=re.M)
    body=_tex_to_word_text(body)
    opts=[]
    for opt in options:
        opts.append(_tex_to_word_text(re.sub(r"\\True\b","",opt,flags=re.I)))
    return typ,opts,body


def _blocks_from_generated(content: str) -> Dict[str,List[str]]:
    result={"A":[],"B":[],"C":[],"D":[]}
    for m in _BLOCK_RE.finditer(content or ""):
        typ,_,_=_parse_question_block(m.group(0)); result[typ].append(m.group(0))
    return result


def _build_word_file(content: str, ten_de: str) -> io.BytesIO:
    doc=Document(); sec=doc.sections[0]; sec.top_margin=Cm(1.6); sec.bottom_margin=Cm(1.6); sec.left_margin=Cm(1.8); sec.right_margin=Cm(1.8)
    doc.styles["Normal"].font.name="Arial"; doc.styles["Normal"].font.size=Pt(11)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(ten_de or "Đề ôn tập"); r.bold=True; r.font.size=Pt(16)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run("Đề được tạo tự động từ ngân hàng câu hỏi GitHub").italic=True
    grouped=_blocks_from_generated(content)
    for code,heading in [("A","PHẦN A. TRẮC NGHIỆM 4 LỰA CHỌN"),("B","PHẦN B. TRẮC NGHIỆM ĐÚNG / SAI"),("C","PHẦN C. TRẢ LỜI NGẮN"),("D","PHẦN D. TỰ LUẬN")]:
        blocks=grouped.get(code,[])
        if not blocks: continue
        h=doc.add_paragraph(); h.paragraph_format.space_before=Pt(10); rr=h.add_run(heading); rr.bold=True; rr.font.size=Pt(13)
        for i,block in enumerate(blocks,1):
            _,options,body=_parse_question_block(block)
            p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(4); r=p.add_run(f"Câu {i}. "); r.bold=True; p.add_run(body)
            if code in ("A","B"):
                for j,opt in enumerate(options[:4]):
                    q=doc.add_paragraph(); q.paragraph_format.left_indent=Cm(.7); q.add_run(f"{'ABCD'[j]}. ").bold=True; q.add_run(opt)
            elif code=="C":
                q=doc.add_paragraph(); q.paragraph_format.left_indent=Cm(.7); q.add_run("Trả lời: ").bold=True; q.add_run("........................................................................")
    buf=io.BytesIO(); doc.save(buf); buf.seek(0); return buf

@bp.route("/ra-de/download-word/<token>")
def download_word(token: str):
    content=_LAST_GENERATED.get(token,"")
    if not content: return Response("Không tìm thấy đề đã tạo hoặc đề đã hết phiên.",status=404)
    m=re.search(r"^%\s*=====\s*(.*?)\s*=====",content,flags=re.M); ten_de=(m.group(1).strip() if m else "Đề ôn tập") or "Đề ôn tập"
    try: buf=_build_word_file(content,ten_de)
    except Exception as exc: return Response(f"Lỗi tạo file Word: {type(exc).__name__}: {exc}",status=500,mimetype="text/plain; charset=utf-8")
    safe_name=re.sub(r'[\\/:*?"<>|]+',"_",ten_de).strip() or "de_thi"
    return send_file(buf,mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",as_attachment=True,download_name=f"{safe_name}.docx")

@bp.route("/ra-de/download/<token>")
def download(token: str):
    content=_LAST_GENERATED.get(token,""); buf=io.BytesIO(content.encode("utf-8")); buf.seek(0)
    return send_file(buf,mimetype="text/plain; charset=utf-8",as_attachment=True,download_name="de_thi.tex")
