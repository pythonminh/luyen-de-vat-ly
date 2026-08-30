# -*- coding: utf-8 -*-
"""
Ra đề — tạo đề thi từ ngân hàng câu hỏi GitHub (ngan-hang/*.tex), dựa trên
bank_index.json đã có sẵn trong repo (tạo bởi scripts/build_bank_index.py).

Route chính:
  GET  /ra-de            -> trang chọn Môn/Lớp/Chương/Bài + số câu theo từng dạng
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
from typing import Any, Dict, List, Tuple

from flask import Blueprint, Response, jsonify, request, render_template_string, send_file

bp = Blueprint("ra_de", __name__)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BANK_DIR = os.path.realpath(os.path.join(APP_DIR, "ngan-hang"))
BANK_INDEX_PATH = os.path.join(APP_DIR, "bank_index.json")

_BLOCK_RE = re.compile(r"\\begin\s*\{\s*(ex|bt)\s*\}(.*?)\\end\s*\{\s*\1\s*\}", re.S | re.I)
_DANGBT_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)
_REL_TEX_PATH_RE = re.compile(r"^ngan-hang(?:/[^/\0]+)+\.tex$")
_PREVIEW_UNWRAP_PASSES = 3


def _load_bank_index() -> Dict[str, Any]:
    try:
        with open(BANK_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"schema": 1, "total_files": 0, "total_questions": 0, "lessons": []}


def _resolve_tex_path(rel_path: str) -> str:
    """rel_path đã ở dạng 'ngan-hang/.../de.tex' (tương đối APP_DIR)."""
    rel = (rel_path or "").replace("\\", "/").lstrip("/")
    if not _REL_TEX_PATH_RE.fullmatch(rel):
        return ""
    full = os.path.realpath(os.path.join(APP_DIR, rel.replace("/", os.sep)))
    try:
        if os.path.commonpath([BANK_DIR, full]) != BANK_DIR:
            return ""
    except ValueError:
        return ""
    return full


def extract_blocks_by_dang(text: str) -> List[Tuple[str, str]]:
    """Trả về [(tên_dạng, nội_dung_block_đầy_đủ)] theo thứ tự xuất hiện trong file."""
    text = text or ""
    markers = [(m.start(), (m.group(1) or "").strip()) for m in _DANGBT_RE.finditer(text)]
    out: List[Tuple[str, str]] = []
    mi = 0
    current = ""
    for m in _BLOCK_RE.finditer(text):
        pos = m.start()
        while mi < len(markers) and markers[mi][0] < pos:
            current = markers[mi][1]
            mi += 1
        name = current or "Chưa phân dạng"
        out.append((name, m.group(0)))
    return out


def blocks_grouped_by_dang(rel_path: str) -> Dict[str, List[str]]:
    text = _read_tex_text(rel_path)
    if text is None:
        return {}
    grouped: Dict[str, List[str]] = {}
    for name, block in extract_blocks_by_dang(text):
        grouped.setdefault(name, []).append(block)
    return grouped


def _read_tex_text(rel_path: str) -> str | None:
    path = _resolve_tex_path(rel_path)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def make_block_preview(block: str, limit: int = 180) -> str:
    text = block or ""
    text = re.sub(r"(?is)\\begin\s*\{\s*(?:ex|bt)\s*\}|\\end\s*\{\s*(?:ex|bt)\s*\}", " ", text)
    text = _DANGBT_RE.sub(" ", text)
    text = re.sub(r"(?m)^\s*%.*$", " ", text)
    text = re.split(r"\\loigiai\b", text, maxsplit=1)[0]
    text = re.sub(r"\\(?:choiceTF|choice|shortans)\b", " ", text)
    for _ in range(_PREVIEW_UNWRAP_PASSES):
        text = re.sub(r"\\[a-zA-Z]+\*?\s*(?:\[[^\]]*\])?\s*\{([^{}]*)\}", r" \1 ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = text.replace("$", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    if not text:
        return "(Không có nội dung xem trước)"
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


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
.dang-row{display:flex;align-items:center;gap:8px;padding:5px 4px;border-top:1px dashed #e5e7eb}
.dang-row label{flex:1}
.dang-row input[type=number]{width:64px;padding:4px 6px;border:1px solid #cbd5e1;border-radius:6px}
.dang-picker{border-top:1px dashed #e5e7eb}
.dang-picker:first-of-type{border-top:none}
.dang-picker .dang-row{border-top:none}
.picker-details{padding:0 4px 8px 4px}
.picker-details summary{cursor:pointer;color:#1976d2;font-size:13px;margin:0 0 6px 0}
.preview-list{display:flex;flex-direction:column;gap:6px}
.preview-item{display:flex;align-items:flex-start;gap:8px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px}
.preview-item input{margin-top:2px}
.preview-index{font-weight:700;color:#334155}
.preview-text{color:#0f172a}
.muted{color:#64748b;font-size:13px}
.top-actions{position:sticky;top:0;background:#f6f8fa;padding:10px 0;z-index:5}
button,.btn{background:#1976d2;color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}
button.secondary{background:#64748b}
.search{width:100%;padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:10px}
.badge{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:999px;padding:2px 8px;font-size:12px;margin-left:6px}
</style>
</head><body>
<div class="wrap">
  <div class="top-actions">
    <h1>📝 Ra đề từ ngân hàng GitHub</h1>
    <p class="muted">Nguồn: <b>{{ total_files }}</b> file · <b>{{ total_questions }}</b> câu hỏi.
      Chọn số câu theo từng dạng hoặc mở danh sách để tick từng câu cụ thể rồi bấm <b>Tạo đề</b>.</p>
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
        <div class="dang-picker" data-path="{{ item.path }}" data-dang="{{ dang }}" data-preview-url="{{ url_for('ra_de.preview') }}">
          <div class="dang-row">
            <label>{{ dang }} <span class="muted">(tối đa {{ n }})</span></label>
            <input type="number" min="0" max="{{ n }}" value="0"
                   name="c__{{ item.path }}__{{ dang }}">
          </div>
          <details class="picker-details">
            <summary>☑️ Chọn câu cụ thể</summary>
            <div class="muted">Nếu tick câu cụ thể, hệ thống sẽ dùng đúng các câu đã tick và bỏ qua ô số lượng ở dạng này.</div>
            <div class="preview-list muted">Mở mục này để tải danh sách câu hỏi.</div>
          </details>
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
function syncManualSelection(wrapper){
  var countInput = wrapper.querySelector('input[type="number"]');
  var checked = wrapper.querySelectorAll('.preview-list input[type="checkbox"]:checked').length;
  if(!countInput){ return; }
  countInput.disabled = checked > 0;
  countInput.title = checked > 0 ? 'Đang ưu tiên các câu đã tick cụ thể.' : '';
}
function renderPreviewList(wrapper, items){
  var list = wrapper.querySelector('.preview-list');
  list.innerHTML = '';
  if(!items.length){
    list.textContent = 'Không có câu hỏi trong dạng này.';
    list.classList.add('muted');
    return;
  }
  list.classList.remove('muted');
  items.forEach(function(item){
    var row = document.createElement('label');
    row.className = 'preview-item';

    var input = document.createElement('input');
    input.type = 'checkbox';
    input.name = 'q__' + wrapper.dataset.path + '__' + wrapper.dataset.dang + '__' + item.index;
    input.value = '1';
    input.addEventListener('change', function(){ syncManualSelection(wrapper); });

    var textWrap = document.createElement('span');
    var idx = document.createElement('span');
    idx.className = 'preview-index';
    idx.textContent = 'Câu ' + (item.index + 1) + ': ';

    var text = document.createElement('span');
    text.className = 'preview-text';
    text.textContent = item.preview || '(Không có nội dung xem trước)';

    textWrap.appendChild(idx);
    textWrap.appendChild(text);
    row.appendChild(input);
    row.appendChild(textWrap);
    list.appendChild(row);
  });
}
async function loadDangPreview(detailsEl){
  if(!detailsEl.open){ return; }
  var wrapper = detailsEl.closest('.dang-picker');
  var list = detailsEl.querySelector('.preview-list');
  if(!wrapper || !list || list.dataset.loaded === '1' || list.dataset.loading === '1'){ return; }
  list.dataset.loading = '1';
  list.textContent = 'Đang tải danh sách câu hỏi...';
  try{
    var url = new URL(wrapper.dataset.previewUrl, window.location.origin);
    url.searchParams.set('path', wrapper.dataset.path);
    url.searchParams.set('dang', wrapper.dataset.dang);
    var resp = await fetch(url.toString(), {headers:{'Accept':'application/json'}});
    var data = await resp.json();
    if(!resp.ok || !data.ok){ throw new Error(data.error || 'Không tải được danh sách câu hỏi.'); }
    renderPreviewList(wrapper, data.items || []);
    list.dataset.loaded = '1';
  }catch(err){
    list.textContent = (err && err.message) ? err.message : 'Không tải được danh sách câu hỏi.';
    list.classList.add('muted');
  }finally{
    delete list.dataset.loading;
  }
}
document.querySelectorAll('.picker-details').forEach(function(el){
  el.addEventListener('toggle', function(){ loadDangPreview(el); });
});
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
        groups.setdefault(key, []).append(item)
    return render_template_string(
        PAGE_TPL,
        groups=groups,
        total_files=data.get("total_files", len(lessons)),
        total_questions=data.get("total_questions", 0),
    )


@bp.route("/ra-de/preview")
def preview():
    path = (request.args.get("path") or "").strip()
    dang = (request.args.get("dang") or "").strip()
    if not path or not dang:
        return jsonify({"ok": False, "error": "Thiếu path hoặc dang.", "items": []}), 400
    text = _read_tex_text(path)
    if text is None:
        return jsonify({"ok": False, "error": f"Không đọc được: {path}", "items": []}), 404
    items = []
    for name, block in extract_blocks_by_dang(text):
        if name != dang:
            continue
        items.append({"index": len(items), "preview": make_block_preview(block)})
    return jsonify({"ok": True, "items": items, "total": len(items)})


@bp.route("/ra-de/generate", methods=["POST"])
def generate():
    ten_de = (request.form.get("ten_de") or "Đề ôn tập").strip()
    wanted: Dict[str, Dict[str, int]] = {}
    selected: Dict[str, Dict[str, List[int]]] = {}
    for key, val in request.form.items():
        if key.startswith("c__"):
            try:
                n = int(val or 0)
            except Exception:
                n = 0
            if n <= 0:
                continue
            try:
                _, path, dang = key.split("__", 2)
            except ValueError:
                continue
            wanted.setdefault(path, {})[dang] = n
        elif key.startswith("q__"):
            try:
                _, path, dang, index_str = key.split("__", 3)
                index = int(index_str)
            except Exception:
                continue
            if index < 0:
                continue
            selected.setdefault(path, {}).setdefault(dang, []).append(index)

    picked_manual_blocks: List[str] = []
    picked_random_blocks: List[str] = []
    total = 0
    errors: List[str] = []
    for path in sorted(set(wanted) | set(selected)):
        grouped = blocks_grouped_by_dang(path)
        if not grouped:
            errors.append(f"Không đọc được: {path}")
            continue
        path_selected = selected.get(path) or {}
        path_wanted = wanted.get(path) or {}
        for dang, indexes in path_selected.items():
            pool = grouped.get(dang) or []
            if not pool:
                continue
            for idx in sorted(set(indexes)):
                if idx >= len(pool):
                    continue
                picked_manual_blocks.append(pool[idx])
                total += 1
        for dang, n in path_wanted.items():
            if path_selected.get(dang):
                continue
            pool = grouped.get(dang) or []
            if not pool:
                continue
            k = min(n, len(pool))
            sample = random.sample(pool, k)
            picked_random_blocks.extend(sample)
            total += len(sample)

    random.shuffle(picked_random_blocks)
    picked_blocks = picked_manual_blocks + picked_random_blocks
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
