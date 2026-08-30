# -*- coding: utf-8 -*-
"""
Ra đề — tạo đề thi từ ngân hàng câu hỏi GitHub (ngan-hang/*.tex), dựa trên
bank_index.json đã có sẵn trong repo (tạo bởi scripts/build_bank_index.py).

Route chính:
  GET  /ra-de            -> trang chọn Môn/Lớp/Chương/Bài + số câu theo từng dạng
                            (và theo từng loại câu: Trắc nghiệm/Đúng sai/Trả lời ngắn/Tự luận)
  POST /ra-de/generate   -> ghép các câu được chọn (random) thành 1 file .tex,
                            xem trước trong trình duyệt + tải file .tex.

File này từng bị thiếu trong repo khiến wsgi.py import lỗi (bị nuốt bởi
`except Exception`) -> route /ra-de không được đăng ký -> nút "📝 Ra đề" trả 404.
"""
from __future__ import annotations

import io
import json
import os
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, Response, request, render_template_string, send_file

bp = Blueprint("ra_de", __name__)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BANK_INDEX_PATH = os.path.join(APP_DIR, "bank_index.json")

_BLOCK_RE = re.compile(r"\\begin\s*\{\s*(ex|bt)\s*\}(.*?)\\end\s*\{\s*\1\s*\}", re.S | re.I)
_DANGBT_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)

# --- Nhận diện "loại câu" từ nội dung mỗi block (giống ldvl/github_tex.py) ---
_CHOICE_TF_RE = re.compile(r"\\choiceTF\b", re.I)
_SHORTANS_RE = re.compile(r"\\shortans\b", re.I)
_CHOICE_RE = re.compile(r"\\choice\b", re.I)

LOAI_CAU_LIST = ["Trắc nghiệm", "Đúng sai", "Trả lời ngắn", "Tự luận"]


def _loai_cau_of_block(body: str) -> str:
    """Xác định loại câu: Trắc nghiệm / Đúng sai / Trả lời ngắn / Tự luận."""
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
    """rel_path đã ở dạng 'ngan-hang/.../de.tex' (tương đối APP_DIR)."""
    rel = (rel_path or "").replace("\\", "/").lstrip("/")
    return os.path.join(APP_DIR, rel.replace("/", os.sep))


def extract_blocks_by_dang(text: str) -> List[Tuple[str, str, str]]:
    """Trả về [(tên_dạng, loại_câu, nội_dung_block_đầy_đủ)] theo thứ tự xuất hiện."""
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
    """Nhóm block theo dạng bài (giữ tương thích với chức năng cũ)."""
    text = _read_tex_text(rel_path)
    grouped: Dict[str, List[str]] = {}
    for name, _loai_cau, block in extract_blocks_by_dang(text):
        grouped.setdefault(name, []).append(block)
    return grouped


def blocks_grouped_by_dang_loai(rel_path: str) -> Dict[str, Dict[str, List[str]]]:
    """Nhóm block theo (dạng bài, loại câu): grouped[dạng][loại_câu] = [block, ...]."""
    text = _read_tex_text(rel_path)
    grouped: Dict[str, Dict[str, List[str]]] = {}
    for name, loai_cau, block in extract_blocks_by_dang(text):
        grouped.setdefault(name, {}).setdefault(loai_cau, []).append(block)
    return grouped


def dang_loai_counts(rel_path: str) -> Dict[str, Dict[str, int]]:
    """Đếm số câu theo (dạng, loại câu) — dùng để hiển thị trên trang /ra-de."""
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
  <p class="muted">
    Nguồn: <b>{{ total_files }}</b> file · <b>{{ total_questions }}</b> câu hỏi.
    Tick loại câu <b>A/B/C/D</b> ở từng dạng bài rồi nhập số câu.
  </p>
  <div class="legend">
    <span>🔵 A — Trắc nghiệm 4 lựa chọn</span>
    <span>🟣 B — Đúng / Sai</span>
    <span>🟢 C — Trả lời ngắn</span>
    <span>🟠 D — Tự luận</span>
  </div>
</div>

<form method="post" action="{{ url_for('ra_de.generate') }}">

  <div class="card">
    <input class="search" id="q"
           placeholder="🔎 Lọc theo Môn / Lớp / Chương / Bài..."
           onkeyup="filterLessons()">

    <label class="muted">
      Tên đề (tùy chọn):
      <input type="text" name="ten_de" placeholder="Đề ôn tập..."
             style="padding:6px 8px;border:1px solid #cbd5e1;border-radius:6px">
    </label>
  </div>

  {% for group_key, lessons in groups.items() %}
  <div class="card lesson-group" data-key="{{ group_key|lower }}">
    <h3>{{ group_key }}</h3>

    {% for item in lessons %}
    <details class="lesson">
      <summary>
        {{ item.BaiHoc or item.path }}
        <span class="badge">{{ item.questions }} câu</span>
      </summary>

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
        <div class="dang-title">
          {{ dang }}
          <span class="muted">
            — A: {{ counts.get("Trắc nghiệm",0) }},
            B: {{ counts.get("Đúng sai",0) }},
            C: {{ counts.get("Trả lời ngắn",0) }},
            D: {{ counts.get("Tự luận",0) }}
          </span>
        </div>

        <div class="type-grid">
          {% for loai_cau, code in [
            ("Trắc nghiệm","A"),
            ("Đúng sai","B"),
            ("Trả lời ngắn","C"),
            ("Tự luận","D")
          ] %}
          {% set n2 = counts.get(loai_cau, 0) %}

          <label class="type-box type-{{ code|lower }}">
            <input type="checkbox"
                   class="type-check"
                   data-type="{{ code }}"
                   data-max="{{ n2 }}"
                   {% if n2 <= 0 %}disabled{% endif %}
                   onchange="toggleCount(this)">

            <span class="type-name">{{ code }}. {{ loai_cau }}</span>
            <span class="type-count">({{ n2 }} câu)</span>

            <input type="number"
                   min="0" max="{{ n2 }}" value="0"
                   class="count-input"
                   data-type="{{ code }}"
                   data-key="{{ item._ra_index }}|{{ dang_idx }}|{{ code }}"
                   disabled>
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

  <div class="card">
    <button type="submit">✅ Tạo đề (.tex)</button>
    <a class="btn secondary" href="{{ url_for('ra_de.home') }}">↺ Làm lại</a>
  </div>

</form>
</div>

<script>
function toggleCount(check){
  const box = check.closest('.type-box');
  const input = box.querySelector('.count-input');
  input.disabled = !check.checked;

  if(check.checked){
    if(Number(input.value) <= 0) input.value = 1;
    const max = Number(check.dataset.max || 0);
    if(Number(input.value) > max) input.value = max;
  }else{
    input.value = 0;
  }
}

function setLessonType(button, type, checked){
  const lesson = button.closest('.lesson');

  lesson.querySelectorAll('.type-check').forEach(function(check){
    if(type === 'ALL' || check.dataset.type === type){
      if(!check.disabled){
        check.checked = checked;
        toggleCount(check);
      }
    }
  });
}

function filterLessons(){
  const q=(document.getElementById('q').value||'').toLowerCase();

  document.querySelectorAll('.lesson-group').forEach(function(g){
    const show=!q ||
      g.dataset.key.indexOf(q)>=0 ||
      g.innerText.toLowerCase().indexOf(q)>=0;
    g.style.display=show?'':'none';
  });
}

// QUAN TRỌNG: không gửi hàng nghìn ô input lên Render.
// Chỉ gửi các ô thực sự được tick dưới dạng JSON rất gọn.
document.querySelector('form').addEventListener('submit', function(){
  const selections = [];

  document.querySelectorAll('.type-check:checked').forEach(function(check){
    const box = check.closest('.type-box');
    const input = box.querySelector('.count-input');
    const n = Number(input.value || 0);

    if(n > 0){
      selections.push({
        k: check.dataset.key,
        n: n
      });
    }
  });

  document.getElementById('selections').value = JSON.stringify(selections);
});
</script>
</body>
</html>
"""

RESULT_TPL = r"""
<!doctype html>
<html lang="vi"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📝 Đề đã tạo</title>
<style>
body{font-family:Arial,Helvetica,sans-serif;background:#f6f8fa;color:#172b4d;margin:0}
.wrap{max-width:1000px;margin:20px auto;padding:0 16px 60px}
.card{background:#fff;border:1px solid #d0d7de;border-radius:12px;padding:16px;margin-bottom:14px}
pre{white-space:pre-wrap;word-break:break-word;background:#0f172a;color:#e2e8f0;padding:14px;border-radius:10px;max-height:70vh;overflow:auto}
button,.btn{background:#1976d2;color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}
.btn.secondary{background:#64748b}
</style>
</head><body>
<div class="wrap">
  <div class="card">
    <h2>✅ Đã tạo đề — {{ total }} câu</h2>
    <p><a class="btn" href="{{ url_for('ra_de.download', token=token) }}">⬇️ Tải file .tex</a>
       <a class="btn secondary" href="{{ url_for('ra_de.home') }}">↺ Tạo đề khác</a></p>
  </div>
  <div class="card">
    <h3>Xem trước</h3>
    <pre>{{ content }}</pre>
  </div>
</div>
</body></html>
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
        # Tính chi tiết số câu theo (dạng, loại câu) để hiển thị lựa chọn lọc theo loại câu.
        item = dict(item)
        item["_ra_index"] = lesson_idx
        item["dang_loai"] = dang_loai_counts(item.get("path") or "")
        groups.setdefault(key, []).append(item)
    return render_template_string(
        PAGE_TPL,
        groups=groups,
        total_files=data.get("total_files", len(lessons)),
        total_questions=data.get("total_questions", 0),
    )


def _parse_compact_selections(raw: str, lessons: List[Dict[str, Any]]) -> List[Tuple[str, str, str, int]]:
    """
    Giải mã lựa chọn dạng cực gọn:
      [{"k":"12|3|A","n":5}, ...]

    k = lesson_index | dang_index | A/B/C/D

    Cách này tránh lỗi HTTP 413 do form cũ gửi path + tên dạng bài
    cho hàng nghìn input.
    """
    try:
        data = json.loads(raw or "[]")
    except Exception:
        return []

    result: List[Tuple[str, str, str, int]] = []

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
            lesson_idx = int(bits[0])
            dang_idx = int(bits[1])
        except Exception:
            continue

        loai_code = bits[2].upper()
        if loai_code not in ("A", "B", "C", "D"):
            continue
        if not (0 <= lesson_idx < len(lessons)):
            continue

        item = lessons[lesson_idx]
        path = str(item.get("path") or "")
        if not path:
            continue

        # dang_loai_counts giữ thứ tự dict theo thứ tự \dangbt xuất hiện.
        dang_map = dang_loai_counts(path)
        dang_names = list(dang_map.keys())

        if not (0 <= dang_idx < len(dang_names)):
            continue

        dang = dang_names[dang_idx]

        code_to_name = {
            "A": "Trắc nghiệm",
            "B": "Đúng sai",
            "C": "Trả lời ngắn",
            "D": "Tự luận",
        }
        loai_cau = code_to_name[loai_code]

        # Không cho nhập vượt quá số câu thực có.
        max_n = int(dang_map[dang].get(loai_cau, 0))
        n = min(n, max_n)

        if n > 0:
            result.append((path, dang, loai_cau, n))

    return result


@bp.route("/ra-de/generate", methods=["POST"])
def generate():
    ten_de = (request.form.get("ten_de") or "Đề ôn tập").strip()

    data = _load_bank_index()
    lessons = data.get("lessons") or []

    # Ưu tiên format mới cực gọn -> tránh 413.
    selections = _parse_compact_selections(
        request.form.get("selections") or "[]",
        lessons,
    )

    # wanted[loại][path][dạng] = số câu
    wanted: Dict[str, Dict[str, Dict[str, int]]] = {
        "Trắc nghiệm": {},
        "Đúng sai": {},
        "Trả lời ngắn": {},
        "Tự luận": {},
    }

    for path, dang, loai_cau, n in selections:
        wanted.setdefault(loai_cau, {}).setdefault(path, {})[dang] = n

    picked: Dict[str, List[str]] = {
        "Trắc nghiệm": [],
        "Đúng sai": [],
        "Trả lời ngắn": [],
        "Tự luận": [],
    }

    errors: List[str] = []

    for loai_cau in ("Trắc nghiệm", "Đúng sai", "Trả lời ngắn", "Tự luận"):
        for path, dang_counts in wanted[loai_cau].items():
            grouped = blocks_grouped_by_dang_loai(path)

            if not grouped:
                errors.append(f"Không đọc được: {path}")
                continue

            for dang, n in dang_counts.items():
                pool = (grouped.get(dang) or {}).get(loai_cau) or []

                if not pool:
                    continue

                k = min(n, len(pool))
                picked[loai_cau].extend(random.sample(pool, k))

    for loai_cau in picked:
        random.shuffle(picked[loai_cau])

    counts = {loai: len(blocks) for loai, blocks in picked.items()}
    total = sum(counts.values())

    part_titles = {
        "Trắc nghiệm": "PHẦN A. TRẮC NGHIỆM 4 LỰA CHỌN",
        "Đúng sai": "PHẦN B. TRẮC NGHIỆM ĐÚNG / SAI",
        "Trả lời ngắn": "PHẦN C. TRẢ LỜI NGẮN",
        "Tự luận": "PHẦN D. TỰ LUẬN",
    }
    part_codes = {
        "Trắc nghiệm": "A",
        "Đúng sai": "B",
        "Trả lời ngắn": "C",
        "Tự luận": "D",
    }

    header = (
        f"% ===== {ten_de} =====\n"
        f"% Tự động tạo bởi Ra đề — {total} câu\n"
        f"% A={counts['Trắc nghiệm']} | "
        f"B={counts['Đúng sai']} | "
        f"C={counts['Trả lời ngắn']} | "
        f"D={counts['Tự luận']}\n\n"
    )

    parts: List[str] = []

    for loai_cau in ("Trắc nghiệm", "Đúng sai", "Trả lời ngắn", "Tự luận"):
        blocks = picked[loai_cau]
        if not blocks:
            continue

        code = part_codes[loai_cau]
        parts.append("% ==================================================\n")
        parts.append(f"% {part_titles[loai_cau]}\n")
        parts.append("% ==================================================\n\n")

        for i, block in enumerate(blocks, start=1):
            parts.append(
                f"% ===== {code} - Câu {i} =====\n"
                f"{block.strip()}\n\n"
            )

    content = header + "".join(parts)

    if errors:
        content += "\n\n% Lỗi:\n% " + "\n% ".join(errors)

    if total == 0:
        content += (
            "% Chưa có câu nào được chọn.\n"
            "% Hãy tick A/B/C/D và nhập số câu > 0.\n"
        )

    token = f"{random.randint(100000, 999999)}"
    _LAST_GENERATED[token] = content

    return render_template_string(
        RESULT_TPL,
        content=content,
        total=total,
        token=token,
    )


@bp.route("/ra-de/download/<token>")
def download(token: str):
    content = _LAST_GENERATED.get(token, "")
    buf = io.BytesIO(content.encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="text/plain; charset=utf-8",
        as_attachment=True,
        download_name="de_thi.tex",
    )
