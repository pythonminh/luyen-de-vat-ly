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
    return {dang: {lc: len(blocks) for lc, blocks in loai_map.items()} for dang, loai_map in grouped.items()}


PAGE_TPL = r"""
<!doctype html>
<html lang="vi"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📝 Ra đề — Luyện đề Vật lý</title>
<style>
body{font-family:Arial,Helvetica,sans-serif;background:#f6f8fa;color:#172b4d;margin:0}
.wrap{max-width:1100px;margin:20px auto;padding:0 16px 80px}
h1{font-size:22px}
.card{background:#fff;border:1px solid #d0d7de;border-radius:12px;padding:16px;margin-bottom:14px}
.lesson{border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin:8px 0}
.lesson summary{cursor:pointer;font-weight:700}
.dang-block{border-top:1px dashed #e5e7eb;padding:6px 4px}
.dang-title{font-weight:600;margin:4px 0}
.dang-row{display:flex;align-items:center;gap:8px;padding:4px 4px 4px 14px}
.dang-row label{flex:1}
.dang-row input[type=number]{width:64px;padding:4px 6px;border:1px solid #cbd5e1;border-radius:6px}
.loai-row{display:flex;align-items:center;gap:8px;padding:3px 4px 3px 28px}
.loai-row label{flex:1;color:#334155;font-size:13px}
.loai-row input[type=number]{width:56px;padding:3px 5px;border:1px solid #cbd5e1;border-radius:6px}
.muted{color:#64748b;font-size:13px}
.top-actions{position:sticky;top:0;background:#f6f8fa;padding:10px 0;z-index:5}
button,.btn{background:#1976d2;color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}
button.secondary{background:#64748b}
.search{width:100%;padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:10px}
.badge{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:999px;padding:2px 8px;font-size:12px;margin-left:6px}
.badge.loai{background:#ecfdf5;color:#065f46}
</style>
</head><body>
<div class="wrap">
  <div class="top-actions">
    <h1>📝 Ra đề từ ngân hàng GitHub</h1>
    <p class="muted">Nguồn: <b>{{ total_files }}</b> file · <b>{{ total_questions }}</b> câu hỏi.
      Chọn số câu theo từng dạng (và có thể lọc thêm theo loại câu: Trắc nghiệm / Đúng sai / Trả lời ngắn / Tự luận)
      rồi bấm <b>Tạo đề</b>.</p>
  </div>
  <form method="post" action="{{ url_for('ra_de.generate') }}">
    <div class="card">
      <input class="search" id="q" placeholder="🔎 Lọc theo Môn / Lớp / Chương / Bài..." onkeyup="filterLessons()">
      <label class="muted">Tên đề (tùy chọn): <input type="text" name="ten_de" placeholder="Đề ôn tập..." style="padding:6px 8px;border:1px solid #cbd5e1;border-radius:6px"></label>
    </div>
    {% for group_key, lessons in groups.items() %}
    <div class="card lesson-group" data-key="{{ group_key|lower }}">
      <h3>{{ group_key }}</h3>
      {% for item in lessons %}
      <details class="lesson">
        <summary>{{ item.BaiHoc or item.path }} <span class="badge">{{ item.questions }} câu</span></summary>
        {% for dang, n in item.dang.items() %}
        <div class="dang-block">
          <div class="dang-row">
            <label><b>{{ dang }}</b> <span class="muted">( {{ n }} câu — random không phân biệt loại câu)</span></label>
            <input type="number" min="0" max="{{ n }}" value="0"
                   name="c__{{ item.path }}__{{ dang }}">
          </div>
          {% set loai_map = item.dang_loai.get(dang, {}) %}
          {% if loai_map %}
          {% for loai_cau, n2 in loai_map.items() %}
          <div class="loai-row">
            <label>↳ {{ loai_cau }} <span class="badge loai"> {{ n2 }}</span></label>
            <input type="number" min="0" max="{{ n2 }}" value="0"
                   name="c__{{ item.path }}__{{ dang }}__{{ loai_cau }}">
          </div>
          {% endfor %}
          {% endif %}
        </div>
        {% endfor %}
      </details>
      {% endfor %}
    </div>
    {% endfor %}
    <div class="card">
      <button type="submit">✅ Tạo đề (.tex)</button>
      <a class="btn secondary" href="{{ url_for('ra_de.home') }}">↺ Làm lại</a>
    </div>
  </form>
</div>
<script>
function filterLessons(){
  var q=(document.getElementById('q').value||'').toLowerCase();
  document.querySelectorAll('.lesson-group').forEach(function(g){
    var show = !q || g.dataset.key.indexOf(q)>=0 || g.innerText.toLowerCase().indexOf(q)>=0;
    g.style.display = show ? '' : 'none';
  });
}
</script>
</body></html>
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
    for item in lessons:
        if not isinstance(item, dict):
            continue
        mon = item.get("Mon") or "Khác"
        lop = item.get("Lop") or ""
        chuong = item.get("Chuong") or ""
        key = f"{mon} · Lớp {lop} · {chuong}".strip()
        # Tính chi tiết số câu theo (dạng, loại câu) để hiển thị lựa chọn lọc theo loại câu.
        item = dict(item)
        item["dang_loai"] = dang_loai_counts(item.get("path") or "")
        groups.setdefault(key, []).append(item)
    return render_template_string(
        PAGE_TPL,
        groups=groups,
        total_files=data.get("total_files", len(lessons)),
        total_questions=data.get("total_questions", 0),
    )


def _parse_wanted_key(key: str) -> Optional[Tuple[str, str, Optional[str]]]:
    """Phân tích key input dạng:
      - c__{path}__{dang}                 -> (path, dang, None)
      - c__{path}__{dang}__{loai_cau}      -> (path, dang, loai_cau)
    Loại câu luôn nằm trong LOAI_CAU_LIST nên có thể tách an toàn ở cuối.
    """
    if not key.startswith("c__"):
        return None
    rest = key[len("c__"):]
    parts = rest.split("__")
    if len(parts) < 2:
        return None
    if len(parts) >= 3 and parts[-1] in LOAI_CAU_LIST:
        loai_cau = parts[-1]
        dang = parts[-2]
        path = "__".join(parts[:-2])
        return path, dang, loai_cau
    dang = parts[-1]
    path = "__".join(parts[:-1])
    return path, dang, None


@bp.route("/ra-de/generate", methods=["POST"])
def generate():
    ten_de = (request.form.get("ten_de") or "Đề ôn tập").strip()
    # wanted[path]["dang"][dang] = n  (random trong toàn bộ dạng, không phân biệt loại câu)
    # wanted[path]["dangloai"][(dang, loai_cau)] = n  (lọc thêm theo loại câu)
    wanted: Dict[str, Dict[str, Dict[Any, int]]] = {}
    for key, val in request.form.items():
        parsed = _parse_wanted_key(key)
        if not parsed:
            continue
        try:
            n = int(val or 0)
        except Exception:
            n = 0
        if n <= 0:
            continue
        path, dang, loai_cau = parsed
        entry = wanted.setdefault(path, {"dang": {}, "dangloai": {}})
        if loai_cau is None:
            entry["dang"][dang] = n
        else:
            entry["dangloai"][(dang, loai_cau)] = n

    picked_blocks: List[str] = []
    total = 0
    errors: List[str] = []
    for path, req in wanted.items():
        dang_counts = req.get("dang") or {}
        dangloai_counts = req.get("dangloai") or {}
        if dang_counts:
            grouped = blocks_grouped_by_dang(path)
            if not grouped and dang_counts:
                errors.append(f"Không đọc được: {path}")
            for dang, n in dang_counts.items():
                pool = grouped.get(dang) or []
                if not pool:
                    continue
                k = min(n, len(pool))
                sample = random.sample(pool, k)
                picked_blocks.extend(sample)
                total += len(sample)
        if dangloai_counts:
            grouped2 = blocks_grouped_by_dang_loai(path)
            if not grouped2:
                errors.append(f"Không đọc được: {path}")
            for (dang, loai_cau), n in dangloai_counts.items():
                pool = (grouped2.get(dang) or {}).get(loai_cau) or []
                if not pool:
                    continue
                k = min(n, len(pool))
                sample = random.sample(pool, k)
                picked_blocks.extend(sample)
                total += len(sample)

    random.shuffle(picked_blocks)
    header = f"% ===== {ten_de} =====\n% Tự động tạo bởi Ra đề — {total} câu\n\n"
    numbered = []
    for i, block in enumerate(picked_blocks, start=1):
        numbered.append(f"% ===== Câu {i} =====\n{block.strip()}\n")
    content = header + "\n".join(numbered)
    if errors:
        content += "\n\n% Lỗi:\n% " + "\n% ".join(errors)

    token = f"{random.randint(100000, 999999)}"
    _LAST_GENERATED[token] = content

    return render_template_string(RESULT_TPL, content=content, total=total, token=token)


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
