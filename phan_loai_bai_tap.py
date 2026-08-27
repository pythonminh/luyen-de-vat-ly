#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phan_loai_bai_tap.py
Parse các file TeX trong ngân hàng Vật lý, phân loại câu hỏi theo dạng (TN/DS/TLN/TL),
và xuất metadata JSON để app.py hiển thị nhiều badge dạng bài trên mục lục.

Chạy: python phan_loai_bai_tap.py
Output: ngan-hang/Vật lý/bai_tap_phan_loai_metadata.json
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------

EXERCISE_TYPE_DEFINITIONS = [
    {"code": "TN",  "name": "Trắc nghiệm",   "order": 1},
    {"code": "DS",  "name": "Đúng sai",       "order": 2},
    {"code": "TLN", "name": "Trả lời ngắn",   "order": 3},
    {"code": "TL",  "name": "Tự luận",        "order": 4},
]

CODE_TO_NAME = {d["code"]: d["name"] for d in EXERCISE_TYPE_DEFINITIONS}

# Regex tìm điểm bắt đầu mỗi khối câu hỏi
_BEGIN_EX_RE  = re.compile(r"\\begin\s*\{\s*ex\s*\}", re.I)
_BEGIN_BT_RE  = re.compile(r"\\begin\s*\{\s*bt\s*\}", re.I)
_END_EX_RE    = re.compile(r"\\end\s*\{\s*ex\s*\}", re.I)
_END_BT_RE    = re.compile(r"\\end\s*\{\s*bt\s*\}", re.I)

# Phân loại nội dung trong khối \begin{ex}...\end{ex}
_CHOICE_TF_RE = re.compile(r"\\choiceTF\b", re.I)
_CHOICE_RE    = re.compile(r"\\choice\b", re.I)
_SHORTANS_RE  = re.compile(r"\\shortans\b", re.I)

# ID câu hỏi có hậu tố dạng (dùng để xác nhận)
_ID_SUFFIX_RE = re.compile(r"%\s*ID\s*:\s*\S+?-([A-Z]+)\s*$", re.M)

# ---------------------------------------------------------------------------
# Hàm phân loại
# ---------------------------------------------------------------------------

def _extract_blocks(text: str) -> List[Tuple[str, str]]:
    """
    Trả list (env_type, block_content): env_type là 'ex' hoặc 'bt'.
    Dùng tìm kiếm tuyến tính để tránh backtracking quá lâu trên file lớn.
    """
    blocks: List[Tuple[str, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        # Tìm \begin{ex} hoặc \begin{bt} gần nhất
        m_ex = _BEGIN_EX_RE.search(text, pos)
        m_bt = _BEGIN_BT_RE.search(text, pos)
        if m_ex is None and m_bt is None:
            break
        # Chọn cái xuất hiện trước
        if m_bt is None or (m_ex is not None and m_ex.start() <= m_bt.start()):
            start = m_ex.start()  # type: ignore[union-attr]
            end_re = _END_EX_RE
            env = "ex"
        else:
            start = m_bt.start()
            end_re = _END_BT_RE
            env = "bt"
        m_end = end_re.search(text, start)
        if m_end is None:
            break
        blocks.append((env, text[start: m_end.end()]))
        pos = m_end.end()
    return blocks


def classify_block(env: str, content: str) -> str:
    """Trả về code dạng: 'TN', 'DS', 'TLN', 'TL'."""
    if env == "bt":
        return "TL"
    # Ưu tiên: DS > TLN > TN
    if _CHOICE_TF_RE.search(content):
        return "DS"
    if _SHORTANS_RE.search(content):
        return "TLN"
    # Nếu có \choice (không phải \choiceTF) → TN
    if _CHOICE_RE.search(content):
        return "TN"
    # Fallback dựa vào hậu tố ID
    m = _ID_SUFFIX_RE.search(content)
    if m:
        suffix = m.group(1).upper()
        if suffix in CODE_TO_NAME:
            return suffix
    return "TN"  # mặc định


def count_by_type(text: str) -> Dict[str, int]:
    """Đếm số câu theo từng dạng trong một file TeX."""
    counts: Dict[str, int] = {}
    for env, block in _extract_blocks(text):
        code = classify_block(env, block)
        counts[code] = counts.get(code, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Tìm và xử lý file
# ---------------------------------------------------------------------------

def find_tex_files(ngan_hang_dir: str) -> List[Tuple[str, str]]:
    """
    Trả list (rel_path, abs_path) cho tất cả file de.tex trong Vật lý/Lớp {10,11,12}.
    rel_path là đường dẫn tương đối từ thư mục ngan_hang_dir (không có "ngan-hang/").
    """
    results: List[Tuple[str, str]] = []
    vat_ly_dir = os.path.join(ngan_hang_dir, "Vật lý")
    if not os.path.isdir(vat_ly_dir):
        return results
    for lop in ("Lớp 10", "Lớp 11", "Lớp 12"):
        lop_dir = os.path.join(vat_ly_dir, lop)
        if not os.path.isdir(lop_dir):
            continue
        for root, _dirs, files in os.walk(lop_dir):
            for fn in files:
                if fn.lower() == "de.tex":
                    abs_path = os.path.join(root, fn)
                    rel_path = os.path.relpath(abs_path, ngan_hang_dir).replace("\\", "/")
                    results.append((rel_path, abs_path))
    return results


def build_metadata(ngan_hang_dir: str) -> Dict:
    """Xây dựng dict metadata từ tất cả file TeX."""
    lessons = []
    tex_files = find_tex_files(ngan_hang_dir)
    for rel_path, abs_path in sorted(tex_files):
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as e:
            print(f"  [WARN] Không đọc được {rel_path}: {e}", file=sys.stderr)
            continue
        counts = count_by_type(text)
        if not counts:
            continue
        # github path = "ngan-hang/" + rel_path
        lessons.append({
            "path": rel_path,
            "github": "ngan-hang/" + rel_path,
            "counts_by_type": counts,
        })
    return {
        "exercise_type_definitions": EXERCISE_TYPE_DEFINITIONS,
        "lessons": lessons,
    }


# ---------------------------------------------------------------------------
# Hàm tiện ích cho app.py
# ---------------------------------------------------------------------------

def load_physics_exercise_metadata_map(ngan_hang_dir: str) -> Dict[str, Dict[str, int]]:
    """
    Đọc bai_tap_phan_loai_metadata.json và trả về dict:
      { rel_path -> {type_name: count, ...} }
    rel_path ví dụ: "Vật lý/Lớp 10/Chương I.../L10C1 Bài 1.../de.tex"
    type_name ví dụ: "Trắc nghiệm", "Đúng sai", "Trả lời ngắn", "Tự luận"
    """
    metadata_file = os.path.join(ngan_hang_dir, "Vật lý", "bai_tap_phan_loai_metadata.json")
    if not os.path.isfile(metadata_file):
        return {}
    try:
        with open(metadata_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    result: Dict[str, Dict[str, int]] = {}
    for lesson in data.get("lessons", []):
        rel = lesson.get("path", "")
        if not rel:
            continue
        counts_by_code = lesson.get("counts_by_type", {})
        # Chuyển code sang tên hiển thị
        counts_by_name: Dict[str, int] = {}
        for code, cnt in counts_by_code.items():
            name = CODE_TO_NAME.get(code, code)
            counts_by_name[name] = int(cnt or 0)
        if counts_by_name:
            result[rel] = counts_by_name
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    ngan_hang_dir = os.path.join(repo_dir, "ngan-hang")
    output_file = os.path.join(ngan_hang_dir, "Vật lý", "bai_tap_phan_loai_metadata.json")

    print(f"[phan_loai_bai_tap] Đang đọc file TeX từ {ngan_hang_dir} …")
    metadata = build_metadata(ngan_hang_dir)
    n = len(metadata["lessons"])
    print(f"[phan_loai_bai_tap] Đã phân loại {n} bài.")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, ensure_ascii=False, indent=2)
    print(f"[phan_loai_bai_tap] Đã ghi {output_file}")

    # Thống kê tổng
    totals: Dict[str, int] = {}
    for lesson in metadata["lessons"]:
        for code, cnt in lesson["counts_by_type"].items():
            totals[code] = totals.get(code, 0) + cnt
    for code, cnt in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        name = CODE_TO_NAME.get(code, code)
        print(f"  {name} ({code}): {cnt:,} câu")


if __name__ == "__main__":
    main()
