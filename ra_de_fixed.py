# -*- coding: utf-8 -*-
"""Blueprint 'ra_de' — Route /ra-de: Ra đề từ ngân hàng câu hỏi LaTeX."""
from __future__ import annotations

import json
import os

from flask import Blueprint, redirect, render_template_string, request, session, url_for

bp = Blueprint('ra_de', __name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _load_bank_index():
    path = os.path.join(_app_dir(), 'bank_index.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as exc:
        return {'error': str(exc), 'lessons': []}


def _read_tex(rel_path: str) -> str:
    try:
        from github_tex import github_tex_config, read_or_fetch_tex
        cfg = github_tex_config(_app_dir())
        # rel_path from bank_index already includes 'ngan-hang/...'
        # read_or_fetch_tex expects path relative to local_dir (which is <app_dir>/ngan-hang)
        # strip leading 'ngan-hang/' if present
        rel = rel_path
        ngan_hang_prefix = 'ngan-hang/'
        if rel.startswith(ngan_hang_prefix):
            rel = rel[len(ngan_hang_prefix):]
        return read_or_fetch_tex(cfg, rel)
    except Exception as exc:
        return f'% Lỗi đọc file: {exc}'


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_LIST_HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ra đề — Ngân hàng câu hỏi</title>
<style>
body{font-family:sans-serif;margin:0;background:#f5f6fa}
header{background:#1565c0;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px}
header a{color:#fff;text-decoration:none;font-size:.9em;opacity:.8}
h1{margin:0;font-size:1.3em}
.container{max-width:960px;margin:24px auto;padding:0 16px}
.filters{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px}
.filters select{padding:6px 10px;border-radius:6px;border:1px solid #bbb;font-size:.95em}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px #0001}
th{background:#1565c0;color:#fff;padding:9px 12px;text-align:left;font-size:.9em}
td{padding:8px 12px;border-bottom:1px solid #eee;font-size:.9em}
tr:last-child td{border-bottom:none}
tr:hover td{background:#e8f0fe}
a.view-btn{background:#1976d2;color:#fff;padding:4px 12px;border-radius:4px;text-decoration:none;font-size:.85em}
a.view-btn:hover{background:#1251a0}
.badge{display:inline-block;background:#e3f2fd;color:#1565c0;border-radius:10px;padding:1px 8px;font-size:.8em;margin-left:4px}
.error{background:#fff3e0;border-left:4px solid #e65100;padding:12px 16px;border-radius:4px;margin-bottom:16px}
</style>
</head>
<body>
<header>
  <h1>📚 Ra đề từ ngân hàng</h1>
  <a href="/">← Trang chủ</a>
</header>
<div class="container">
{% if error %}
<div class="error">⚠️ {{ error }}</div>
{% endif %}
<div class="filters">
  <select id="fMon" onchange="filterTable()"><option value="">— Tất cả môn —</option>
  {% for m in mons %}<option>{{ m }}</option>{% endfor %}
  </select>
  <select id="fLop" onchange="filterTable()"><option value="">— Tất cả lớp —</option>
  {% for l in lops %}<option>{{ l }}</option>{% endfor %}
  </select>
  <select id="fChuong" onchange="filterTable()"><option value="">— Tất cả chương —</option>
  {% for c in chuongs %}<option>{{ c }}</option>{% endfor %}
  </select>
</div>
<table id="tbl">
<thead><tr><th>Môn</th><th>Lớp</th><th>Chương</th><th>Bài học</th><th>Số câu</th><th></th></tr></thead>
<tbody>
{% for lesson in lessons %}
<tr data-mon="{{ lesson.Mon }}" data-lop="{{ lesson.Lop }}" data-chuong="{{ lesson.Chuong }}">
  <td>{{ lesson.Mon }}</td>
  <td>{{ lesson.Lop }}</td>
  <td>{{ lesson.Chuong }}</td>
  <td>{{ lesson.BaiHoc or lesson.De or '—' }}</td>
  <td><span class="badge">{{ lesson.count or lesson.questions or 0 }}</span></td>
  <td><a class="view-btn" href="/ra-de/xem?path={{ lesson.path | urlencode }}">Xem đề</a></td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
<script>
function filterTable(){
  var mon=document.getElementById('fMon').value;
  var lop=document.getElementById('fLop').value;
  var chuong=document.getElementById('fChuong').value;
  document.querySelectorAll('#tbl tbody tr').forEach(function(r){
    var ok=(!mon||r.dataset.mon===mon)&&(!lop||r.dataset.lop===lop)&&(!chuong||r.dataset.chuong===chuong);
    r.style.display=ok?'':'none';
  });
}
</script>
</body></html>"""

_VIEW_HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xem đề — {{ path }}</title>
<style>
body{font-family:'Courier New',monospace;margin:0;background:#f5f6fa}
header{background:#1565c0;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px}
header a{color:#fff;text-decoration:none;opacity:.8;font-size:.9em}
h1{margin:0;font-size:1.1em;font-family:sans-serif}
.container{max-width:960px;margin:24px auto;padding:0 16px}
pre{background:#fff;padding:16px;border-radius:8px;box-shadow:0 1px 4px #0001;white-space:pre-wrap;word-break:break-word;font-size:.85em;line-height:1.6}
.error{background:#fff3e0;border-left:4px solid #e65100;padding:12px 16px;border-radius:4px;font-family:sans-serif}
</style>
</head>
<body>
<header>
  <h1>📄 {{ path }}</h1>
  <a href="/ra-de">← Danh sách bài</a>
</header>
<div class="container">
{% if error %}
<div class="error">⚠️ {{ error }}</div>
{% else %}
<pre>{{ content }}</pre>
{% endif %}
</div>
</body></html>"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bp.route('/ra-de')
def ra_de_list():
    if not session.get('mahs'):
        return redirect(url_for('login', next=request.full_path.rstrip('?')))

    data = _load_bank_index()
    error = data.get('error')
    lessons = data.get('lessons', [])

    mons = sorted({l.get('Mon', '') for l in lessons if l.get('Mon')})
    lops = sorted({l.get('Lop', '') for l in lessons if l.get('Lop')})
    chuongs = sorted({l.get('Chuong', '') for l in lessons if l.get('Chuong')})

    return render_template_string(
        _LIST_HTML,
        error=error,
        lessons=lessons,
        mons=mons,
        lops=lops,
        chuongs=chuongs,
    )


@bp.route('/ra-de/xem')
def ra_de_xem():
    if not session.get('mahs'):
        return redirect(url_for('login', next=request.full_path.rstrip('?')))

    path = request.args.get('path', '').strip()
    if not path:
        return redirect(url_for('ra_de.ra_de_list'))

    # Safety: disallow path traversal outside repo
    norm = os.path.normpath(path).replace('\\', '/')
    if '..' in norm or norm.startswith('/'):
        return render_template_string(_VIEW_HTML, path=path, error='Đường dẫn không hợp lệ.', content='')

    content = ''
    error = None
    try:
        content = _read_tex(norm)
    except Exception as exc:
        error = str(exc)

    return render_template_string(_VIEW_HTML, path=path, error=error, content=content)
