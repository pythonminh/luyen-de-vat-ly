# -*- coding: utf-8 -*-
"""GitHub-only data adapter for the existing student catalog UI.

The frontend stays the original app interface.  This module replaces the
metadata endpoint with data parsed from bank_index.json + local ngan-hang/*.tex.
No Google Sheet is needed for the catalog.
"""
from __future__ import annotations

import json
import os
import re
import time
from functools import lru_cache
from typing import Any, Dict, List

from flask import jsonify, session
from app import app


ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(ROOT, "bank_index.json")


def _clean(v: Any) -> str:
    return str(v or "").strip()


def _read_index() -> Dict[str, Any]:
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"schema": 1, "source": "GitHub", "total_files": 0, "total_questions": 0, "lessons": []}


def _guess_type(block: str) -> str:
    if re.search(r"\\choiceTF\b", block, re.I):
        return "Đúng sai"
    if re.search(r"\\shortans\b", block, re.I):
        return "Trả lời ngắn"
    if re.search(r"\\choice\b", block, re.I):
        return "Trắc nghiệm"
    return "Tự luận"


def _level(block: str) -> str:
    m = re.search(r"%\s*Mức\s*:\s*([^\r\n%]+)", block, re.I)
    if not m:
        return ""
    return _clean(m.group(1)).upper()


def _dang_bt(block: str) -> str:
    m = re.search(r"\\dangbt\s*\{([^{}]*)\}", block, re.I)
    if m:
        return _clean(m.group(1))
    m = re.search(r"%\s*(?:Dạng(?:\s*bài(?:\s*tập)?)?|DangBaiTap)\s*:\s*([^\r\n%]+)", block, re.I)
    return _clean(m.group(1)) if m else ""


def _question_id(block: str) -> str:
    m = re.search(r"%\s*ID\s*:\s*([^\r\n%]+)", block, re.I)
    return _clean(m.group(1)) if m else ""


def _field_after(block: str, name: str) -> str:
    # Used only for lightweight metadata; the full question parser remains in app.py.
    pat = rf"\\{re.escape(name)}\s*\{{"
    m = re.search(pat, block, re.I)
    if not m:
        return ""
    start = m.end()
    depth = 1
    i = start
    while i < len(block) and depth:
        if block[i] == "\\":
            i += 2
            continue
        if block[i] == "{":
            depth += 1
        elif block[i] == "}":
            depth -= 1
        i += 1
    return block[start:i - 1].strip() if depth == 0 else ""


@lru_cache(maxsize=128)
def _parse_file(path: str) -> Dict[str, Any]:
    full = os.path.join(ROOT, path)
    try:
        with open(full, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return {"questions": [], "counts": {}}

    blocks = re.findall(r"\\begin\{ex\}([\s\S]*?)\\end\{ex\}", text, re.I)
    qs: List[Dict[str, Any]] = []
    level_counts: Dict[str, int] = {}
    type_counts: Dict[str, int] = {}
    dbt_counts: Dict[str, int] = {}
    combo_counts: Dict[str, int] = {}

    for i, block in enumerate(blocks, 1):
        typ = _guess_type(block)
        lv = _level(block)
        dbt = _dang_bt(block)
        qid = _question_id(block)
        q = {
            "ID": qid,
            "MucDo": lv,
            "Dang": typ,
            "DangBaiTap": dbt,
            "_block": block,
            "_local_index": i - 1,
        }
        qs.append(q)
        type_counts[typ] = type_counts.get(typ, 0) + 1
        if lv:
            level_counts[lv] = level_counts.get(lv, 0) + 1
        if dbt:
            dbt_counts[dbt] = dbt_counts.get(dbt, 0) + 1
        if lv:
            combo_counts[f"{lv}|{typ}"] = combo_counts.get(f"{lv}|{typ}", 0) + 1

    return {
        "questions": qs,
        "counts": {
            "level": level_counts,
            "dang": type_counts,
            "dangbaitap": dbt_counts,
            "combo": combo_counts,
        },
    }


def _catalog() -> List[Dict[str, Any]]:
    idx = _read_index()
    out: List[Dict[str, Any]] = []
    for item in idx.get("lessons") or []:
        path = _clean(item.get("path") or item.get("file"))
        if not path:
            continue
        parsed = _parse_file(path)
        counts = parsed["counts"]
        qn = int(item.get("questions") or item.get("count") or len(parsed["questions"]) or 0)
        made = path
        dbts = list((counts.get("dangbaitap") or {}).keys())
        out.append({
            "MaDe": made,
            "De": _clean(item.get("De") or item.get("BaiHoc")) or path,
            "BaiHoc": _clean(item.get("BaiHoc")),
            "Mon": _clean(item.get("Mon")),
            "Lop": _clean(item.get("Lop")),
            "Chuong": _clean(item.get("Chuong")),
            "SoCau": qn,
            "DangBaiTap": ", ".join(dbts),
            "FilterCounts": counts,
            "DbtOrder": dbts,
            "GitHubPath": path,
            "Nguon": "GitHub",
            "File": path,
            "id": _clean(item.get("id")) or path,
        })
    return out


@lru_cache(maxsize=1)
def _cached_catalog() -> List[Dict[str, Any]]:
    return _catalog()


def github_meta_response():
    # Preserve a tiny compatible user object so the existing UI keeps working.
    user = {
        "is_admin": bool(session.get("is_admin") or session.get("role") == "ADMIN"),
        "role": session.get("role", ""),
        "hoten": _clean(session.get("hoten")),
        "mahs": _clean(session.get("mahs")),
        "can_ai_hint": bool(session.get("can_ai_hint", True)),
    }
    cat = _cached_catalog()
    idx = _read_index()
    return jsonify({
        "loading": False,
        "source": "GitHub",
        "catalog_source": "GitHub bank_index.json + ngan-hang/*.tex",
        "count_questions": int(idx.get("total_questions") or sum(x.get("SoCau", 0) for x in cat)),
        "count_catalog": len(cat),
        "loaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "catalog": cat,
        "user": user,
        "dbt_orders": {x["MaDe"]: list(x.get("DbtOrder") or []) for x in cat},
        "duplicate_report": None,
    })


# Replace the existing /api/meta endpoint while leaving every visual part of
# the original frontend untouched.
if "api_meta" in app.view_functions:
    app.view_functions["api_meta"] = github_meta_response

app.config["GITHUB_CATALOG_ONLY"] = True
