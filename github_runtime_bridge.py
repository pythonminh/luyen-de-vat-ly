# -*- coding: utf-8 -*-
"""GitHub-only catalog bridge for the existing app UI.

Nguồn chính:
  - bank_index.json
  - ngan-hang/**/*.tex

Mục lục dùng GitHub làm nguồn chính. Dạng bài tập được đọc trực tiếp từ
\\dangbt{...} trong từng file .tex để không phụ thuộc việc bank_index.json
đã được tạo đúng hay chưa.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from flask import jsonify, request
from app import app

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "bank_index.json")
DBT_UNCLASSIFIED = "__CHUA_PHAN_LOAI__"


def _load_index():
    try:
        with open(INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"source": "GitHub", "total_files": 0, "total_questions": 0, "lessons": []}


def _clean(v):
    return str(v or "").strip()


def _question_kind(block):
    if re.search(r"\\choiceTF\b", block or "", re.I):
        return "Đúng sai"
    if re.search(r"\\shortans\b", block or "", re.I):
        return "Trả lời ngắn"
    if re.search(r"\\choice\b", block or "", re.I):
        return "Trắc nghiệm"
    return "Tự luận"


def _question_level(block):
    m = re.search(r"%\s*Mức\s*:\s*([^\r\n%]+)", block or "", re.I)
    return _clean(m.group(1)).upper() if m else ""


def _split_blocks(text):
    return list(re.finditer(
        r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}",
        text or "", re.I,
    ))


def _read_local_tex(path):
    if not path.startswith("ngan-hang/") or ".." in path:
        return ""
    full = os.path.join(ROOT, path)
    try:
        with open(full, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _normalize_dbt_name(name):
    """Đưa placeholder về nhóm Chưa phân loại."""
    t = _clean(name)
    if not t:
        return DBT_UNCLASSIFIED
    k = re.sub(r"\s+", " ", t).strip().casefold()
    if k in {
        "chưa có dạng",
        "chua co dang",
        "chưa phân dạng",
        "chua phan dang",
        "chưa có dạng bài tập",
        "chua co dang bai tap",
        "chưa phân loại",
        "chua phan loai",
        "chưa có dạng bài",
        "chua co dang bai",
    }:
        return DBT_UNCLASSIFIED
    return t


@lru_cache(maxsize=256)
def _tex_counts(path):
    """Đọc .tex thật để đếm loại câu + mức độ + tổ hợp."""
    text = _read_local_tex(path)
    type_counts = {"Trắc nghiệm": 0, "Đúng sai": 0, "Trả lời ngắn": 0, "Tự luận": 0}
    level_counts = {"NB": 0, "TH": 0, "VD": 0, "VDC": 0}
    combo_counts = {}
    dbt_counts = {}

    blocks = _split_blocks(text)
    prev_end = 0
    for m in blocks:
        block = m.group(0)
        typ = _question_kind(block)
        lv = _question_level(block)
        type_counts[typ] = type_counts.get(typ, 0) + 1
        if lv:
            for one in ("NB", "TH", "VD", "VDC"):
                if re.search(rf"\b{re.escape(one)}\b", lv):
                    level_counts[one] += 1
                    combo_key = f"{one}|{typ}"
                    combo_counts[combo_key] = combo_counts.get(combo_key, 0) + 1

        # \\dangbt{...} thường nằm ngay trước \\begin{ex}.
        # Lấy lệnh cuối cùng kể từ cuối block trước để gắn đúng dạng cho câu này.
        prefix = text[prev_end:m.start()]
        found = list(re.finditer(r"\\dangbt\s*\{([^{}]*)\}", prefix, re.I))
        if found:
            dbt_name = _normalize_dbt_name(found[-1].group(1))
        else:
            dbt_name = DBT_UNCLASSIFIED
        dbt_counts[dbt_name] = dbt_counts.get(dbt_name, 0) + 1
        prev_end = m.end()

    return {
        "dang": type_counts,
        "level": {k: v for k, v in level_counts.items() if v},
        "combo": combo_counts,
        "dangbaitap": dbt_counts,
        "question_count": len(blocks),
    }


def _dbt_counts(index_item, tex_count):
    """Ưu tiên\\dangbt trong .tex; chỉ dùng bank_index khi .tex chưa đọc được."""
    tex_map = (tex_count or {}).get("dangbaitap") or {}
    if tex_map:
        return {k: int(v or 0) for k, v in tex_map.items() if int(v or 0) > 0}

    raw = index_item.get("dang") or {}
    out = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                n = int(v or 0)
            except Exception:
                n = 0
            if n > 0:
                name = _normalize_dbt_name(k)
                out[name] = out.get(name, 0) + n

    total = int(index_item.get("questions") or index_item.get("count") or 0)
    classified = sum(v for k, v in out.items() if k != DBT_UNCLASSIFIED)
    if total > classified + out.get(DBT_UNCLASSIFIED, 0):
        out[DBT_UNCLASSIFIED] = max(0, total - classified - out.get(DBT_UNCLASSIFIED, 0))
    return out


def load_catalog():
    idx = _load_index()
    rows = []
    for item in idx.get("lessons") or []:
        path = _clean(item.get("path") or item.get("file"))
        if not path:
            continue

        tex_counts = _tex_counts(path)
        dbt = _dbt_counts(item, tex_counts)
        dbt_names = [k for k in dbt if k != DBT_UNCLASSIFIED]

        qn_index = int(item.get("questions") or item.get("count") or 0)
        qn_tex = int(tex_counts.get("question_count") or 0)
        qn = qn_tex or qn_index

        type_counts = tex_counts.get("dang") or {}
        level_counts = tex_counts.get("level") or {}
        combo_counts = tex_counts.get("combo") or {}

        # Nếu file .tex không đọc được, giữ metadata trong bank_index.
        if not any(type_counts.values()):
            type_counts = {"Trắc nghiệm": 0, "Đúng sai": 0, "Trả lời ngắn": 0, "Tự luận": 0}

        rows.append({
            "Mon": _clean(item.get("Mon")),
            "Khoi": _clean(item.get("Lop")),
            "Lop": _clean(item.get("Lop")),
            "Chuong": _clean(item.get("Chuong")),
            "Bai": _clean(item.get("BaiHoc") or item.get("De")),
            "BaiHoc": _clean(item.get("BaiHoc")),
            "De": _clean(item.get("De") or item.get("BaiHoc") or path),
            "MaDe": path,
            "File": path,
            "GitHubPath": path,
            "SoCau": qn,
            "MucDo": ", ".join(k for k in ("NB", "TH", "VD", "VDC") if level_counts.get(k)),
            "Dang": ", ".join(k for k in ("Trắc nghiệm", "Đúng sai", "Trả lời ngắn", "Tự luận") if type_counts.get(k)),
            "DangBaiTap": ", ".join(dbt_names),
            "FilterCounts": {
                "dang": type_counts,
                "level": level_counts,
                "combo": combo_counts,
                "dangbaitap": dbt,
            },
            "DbtOrder": dbt_names,
            "QuyenTruyCap": "FREE",
            "IsFree": True,
            "Nguon": "GitHub",
        })
    return idx, rows


@lru_cache(maxsize=1)
def _cached_catalog():
    return load_catalog()


@app.get('/api/github/catalog')
def github_catalog():
    idx, rows = _cached_catalog()
    return jsonify({
        "loading": False,
        "source": "GitHub",
        "catalog_source": "GitHub / bank_index.json + ngan-hang/*.tex",
        "count_questions": int(idx.get("total_questions") or sum(x.get("SoCau", 0) for x in rows)),
        "count_files": int(idx.get("total_files") or 0),
        "count_catalog": len(rows),
        "catalog": rows,
        "data": rows,
        "items": rows,
        "lessons": rows,
        "user": {},
    })


def _github_meta():
    idx, rows = _cached_catalog()
    return jsonify({
        "loading": False,
        "source": "GitHub",
        "catalog_source": "GitHub bank_index.json + ngan-hang/*.tex",
        "count_questions": int(idx.get("total_questions") or sum(x.get("SoCau", 0) for x in rows)),
        "count_catalog": len(rows),
        "loaded_at": "GitHub",
        "catalog": rows,
        "dbt_orders": {x["MaDe"]: list(x.get("DbtOrder") or []) for x in rows},
        "duplicate_report": None,
        "user": {},
        "filters": {
            "Mon": [], "Lop": [], "Chuong": [], "BaiHoc": [],
            "DangBaiTap": [], "BoDe": [],
        },
    })


# app.py registers /api/meta as endpoint api_meta. Replace that handler so
# init() receives GitHub data immediately rather than waiting for Google.
if "api_meta" in app.view_functions:
    app.view_functions["api_meta"] = _github_meta


BRIDGE_SCRIPT = r'''<script id="ldvl-github-bridge">
(function(){
  if(window.__LDVL_GITHUB_BRIDGE__) return;
  window.__LDVL_GITHUB_BRIDGE__ = true;
  function cleanLoading(){
    document.querySelectorAll('body *').forEach(function(el){
      if(el.children.length===0){
        var t=(el.textContent||'').trim();
        if(/Đang tải dữ liệu Sheet|Đang tải mục lục đề/i.test(t)){
          el.textContent='✓ Đang tải dữ liệu từ GitHub...';
          el.style.color='#166534';
          el.style.fontWeight='700';
        }
      }
    });
  }
  cleanLoading();
  setTimeout(cleanLoading,300);
  setTimeout(cleanLoading,1000);
})();
</script>'''


@app.after_request
def inject_github_bridge(response):
    try:
        if request.path == '/' and response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)
            if 'ldvl-github-bridge' not in text:
                i = text.lower().find('</head>')
                text = text[:i] + BRIDGE_SCRIPT + text[i:] if i >= 0 else BRIDGE_SCRIPT + text
                response.set_data(text)
            response.headers['X-LDVL-Source'] = 'GitHub'
    except Exception:
        pass
    return response

app.config['GITHUB_SOURCE_PRIMARY'] = True
app.config['GOOGLE_SHEET_BANK_BACKUP_ONLY'] = True
