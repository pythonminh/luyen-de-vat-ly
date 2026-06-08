# -*- coding: utf-8 -*-
"""
app.py - Ứng dụng luyện đề Google Sheet + đăng nhập + ADMIN sửa câu
Chạy Render:
    gunicorn app:app --bind 0.0.0.0:$PORT
Yêu cầu Environment Variables trên Render:
    GOOGLE_SHEET_ID
    GOOGLE_CREDENTIALS_JSON
    GEMINI_API_KEY=AIza...   (hoặc nhiều key cách nhau dấu phẩy / xuống dòng)
    GEMINI_API_KEY_2=AIza...   (tuỳ chọn — tự chuyển khi key 1 hết quota)
    GEMINI_API_KEYS=AIza...,AIza...   (hoặc nhiều key cách nhau dấu phẩy)
    GEMINI_HINT_MODEL=gemini-2.5-flash-lite
    AI_PROVIDER=GEMINI
"""
from __future__ import annotations

import json
import os
import random
import re
import time
import unicodedata
import hashlib
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:  # Cho phép app vẫn mở nếu chưa cài gspread local
    gspread = None
    Credentials = None

APP_VERSION = "V182_ADMIN_DANG_REGROUP_2026_06_06"
DEFAULT_GEMINI_HINT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_GEMINI_ADMIN_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_HINT_MODEL = "gpt-4.1-mini"
DEFAULT_AI_PROVIDER = "GEMINI"
AI_HINT_MAX_OUTPUT_TOKENS = max(120, min(int(os.environ.get("AI_HINT_MAX_TOKENS", "280") or 280), 800))
AI_HINT_MAX_CHARS = max(200, min(int(os.environ.get("AI_HINT_MAX_CHARS", "480") or 480), 1200))
AI_HINT_VIP_MAX_OUTPUT_TOKENS = max(180, min(int(os.environ.get("AI_HINT_VIP_MAX_TOKENS", "420") or 420), 800))
AI_HINT_VIP_MAX_CHARS = max(280, min(int(os.environ.get("AI_HINT_VIP_MAX_CHARS", "700") or 700), 1500))
AI_HINT_ADMIN_MAX_OUTPUT_TOKENS = max(2000, min(int(os.environ.get("AI_HINT_ADMIN_MAX_TOKENS", "8192") or 8192), 12000))
AI_HINT_ADMIN_MAX_CHARS = max(6000, min(int(os.environ.get("AI_HINT_ADMIN_MAX_CHARS", "26000") or 26000), 50000))
AI_HINT_ADMIN_MAX_CONTINUATIONS = max(1, min(int(os.environ.get("AI_HINT_ADMIN_CONTINUATIONS", "6") or 6), 8))
AI_HINT_ADMIN_FINISH_DEADLINE_SEC = max(60, min(int(os.environ.get("AI_HINT_ADMIN_DEADLINE_SEC", "110") or 110), 180))
AI_HINT_SIMILAR_MAX_OUTPUT_TOKENS = max(
    400, min(int(os.environ.get("AI_HINT_SIMILAR_MAX_TOKENS", "1024") or 1024), 2000)
)
AI_HINT_SIMILAR_MAX_CHARS = max(
    800, min(int(os.environ.get("AI_HINT_SIMILAR_MAX_CHARS", "3500") or 3500), 6000)
)
MAX_AI_KEYS_PER_PROVIDER = max(1, min(int(os.environ.get("AI_MAX_KEYS", "8") or 8), 20))
GEMINI_HINT_MODEL_FALLBACKS = [
    DEFAULT_GEMINI_HINT_MODEL,
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "luyen-de-vat-ly-secret-key-change-me")

# Key AI theo từng học viên (mahs) — mỗi người nhập key riêng
AI_USER_OVERRIDES: Dict[str, Dict[str, Any]] = {}

# ============================================================
# TIỆN ÍCH CHUẨN HÓA
# ============================================================

def strip_accents(s: Any) -> str:
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def key_norm(s: Any) -> str:
    s = strip_accents(str(s or "").strip().lower())
    s = s.replace("\u0111", "d").replace("\u0110", "d")  # đ/Đ → d (strip_accents không xử lý)
    s = re.sub(r"\s+", " ", s)
    s = s.replace("_", " ").replace("-", " ")
    return s.strip()


_ROMAN_CHAPTER = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
    "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
}


def extract_lesson_number(s: Any) -> int:
    t = key_norm(s)
    m = re.search(r"\bbai\s*(\d+)\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"^(\d+)\b", t)
    if m:
        return int(m.group(1))
    return 9999


def extract_chapter_number(s: Any) -> int:
    t = key_norm(s)
    m = re.search(r"\bchuong\s*(viii|vii|vi|iv|iii|ii|ix|x|i|\d+)\b", t)
    if m:
        token = m.group(1)
        if token.isdigit():
            return int(token)
        return _ROMAN_CHAPTER.get(token, 9999)
    m = re.search(r"^(\d+)\b", t)
    if m:
        return int(m.group(1))
    return 9999


def catalog_sort_key(item: Dict[str, Any]) -> Tuple[Any, ...]:
    bai = clean(item.get("BaiHoc", "")) or clean(item.get("De", ""))
    return (
        key_norm(item.get("Mon", "")),
        key_norm(item.get("Lop", "")),
        extract_chapter_number(item.get("Chuong", "")),
        key_norm(item.get("Chuong", "")),
        extract_lesson_number(bai),
        key_norm(bai),
        key_norm(item.get("BoDe", "")),
    )


def sort_catalog_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(items, key=catalog_sort_key)


def sort_field_values(field: str, values: List[str]) -> List[str]:
    if field == "BaiHoc":
        return sorted(values, key=lambda v: (extract_lesson_number(v), key_norm(v)))
    if field == "Chuong":
        return sorted(values, key=lambda v: (extract_chapter_number(v), key_norm(v)))
    return sorted(values, key=key_norm)


def clean(v: Any) -> str:
    s = str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def safe_next_url(raw: Any) -> str:
    u = clean(raw)
    if not u or not u.startswith("/") or u.startswith("//"):
        return ""
    return u


_LATEX_VN_BREAK = (
    r"thỏa|mãn|phương|trình|nên|điểm|thuộc|mặt|phẳng|khẳng|tọa|độ|sai|đúng",
)


def _fix_plain_text_gaps(s: str) -> str:
    if not s:
        return s
    s = re.sub(r"(\d)([Nn]ên|[Đđ]iểm)", r"\1 \2", s)
    s = re.sub(r"(\))([A-Za-zÀ-ỹĐđ])", r"\1 \2", s)
    return s


def _fix_one_math_inner(inner: str) -> str:
    if not inner:
        return inner
    # $(M)(4;5;2) → $(M)$ $(4;5;2)$
    inner = re.sub(r"\)\s*\((\d[\d;\s,.\-]*)\)", r")$ $(\1)$", inner)
    inner = re.sub(
        r"\$\(([^)]+)\)(thuộc|mặt|phẳng|nên|điểm)",
        r"$(\1)$ $\2",
        inner,
        flags=re.I,
    )
    # (M)thuộc / (M)nên (không có $ giữa hai cụm)
    inner = re.sub(
        rf"\(([^)]+)\)({_LATEX_VN_BREAK})",
        r"(\1)$ $\2",
        inner,
        flags=re.I,
    )
    inner = re.sub(
        rf"(=[\d.\-+]+)\s*({_LATEX_VN_BREAK})",
        r"\1$ $\2",
        inner,
        flags=re.I,
    )
    inner = re.sub(
        rf"(\))({_LATEX_VN_BREAK})",
        r"\1 \2",
        inner,
        flags=re.I,
    )
    inner = re.sub(r"(\d)([A-Za-zÀ-ỹĐđ][a-zà-ỹà-ỹ]{2,})", r"\1 \2", inner)
    inner = re.sub(r"(\))([A-Za-zÀ-ỹĐđ][a-zà-ỹà-ỹ]{2,})", r"\1 \2", inner)
    inner = re.sub(r"\(\((\\?[a-zA-Z]+)\)\)", r"\1", inner)
    # Dấu } thừa sau mũ: 10^{5}}Pa → 10^{5}\,\text{Pa}
    inner = re.sub(r"(\d+)\^\{([^{}]+)\}\}+", r"\1^{\2}", inner)
    inner = re.sub(
        r"(\d+)\^\{([^{}]+)\}(Pa|kPa|atm|bar)\.?",
        r"\1^{\2}\\,\\text{\3}.",
        inner,
        flags=re.I,
    )
    inner = re.sub(
        r"^\((\d+\^\{[^{}]+\}\\,\\text\{Pa\}\.?)\)\.?$",
        r"\1.",
        inner,
        flags=re.I,
    )
    inner = re.sub(
        r"^\((\d+\^\{[^{}]+\}\\,\\text\{Pa\}\.?)\.?$",
        r"\1.",
        inner,
        flags=re.I,
    )
    inner = re.sub(r"\\text\{cm\}\^\{3\}\}+", r"\\text{cm}^{3}", inner)
    inner = re.sub(r"\^\{([^{}]+)\}\}+", r"^{\1}", inner)
    # c{{m}^{3}} / cm^3 dính số
    inner = re.sub(r"(\d+)\s*c\{\{?\s*m\s*\}\}?\^\{3\}", r"\1\\,\\text{cm}^{3}", inner, flags=re.I)
    inner = re.sub(r"\\acute\{\\mathrm\{i\}\}", "í", inner, flags=re.I)
    inner = re.sub(
        r"\\text\{\s*([^}]*?)\s*\}\s*í\s*\\text\{\s*t\s*\}",
        r"\\text{\1ít}",
        inner,
        flags=re.I,
    )
    return inner


def _latex_dollar_count(t: str) -> int:
    """Đếm $ inline (bỏ qua $$ display)."""
    n, i, L = 0, 0, len(t)
    while i < L:
        if t[i] == "$" and i + 1 < L and t[i + 1] == "$":
            i += 2
            continue
        if t[i] == "$":
            n += 1
        i += 1
    return n


def _latex_structure_ok(t: str) -> bool:
    """True nếu $ cân bằng và không còn \\text/\\, lẻ ngoài khối $...$."""
    if not t:
        return True
    if _latex_dollar_count(t) % 2 != 0:
        return False
    plain = t
    plain = re.sub(r"\$\$[^$]*\$\$", "", plain)
    plain = re.sub(r"\$[^$]*\$", "", plain)
    if re.search(r"\\(?:text|mathrm|frac|sqrt|left|right|times|cdot|pm|mp|leq|geq|neq|approx|,)", plain):
        return False
    return True


def _fix_surplus_dollar_signs(t: str) -> str:
    """Gỡ $ thừa / lệch cặp — lỗi Word/Sheet hay gặp nhất."""
    if not t or "$" not in t:
        return t
    # $$$... → $$ hoặc $
    t = re.sub(r"\${3,}", "$$", t)
    # $$...$$ một dòng ngắn (inline lỡ gõ $$) → $...$
    t = re.sub(r"\$\$([^$\n]{1,160}?)\$\$", r"$\1$", t)
    # $$...$ hoặc $...$$
    t = re.sub(r"\$\$([^$\n]+?)\$(?!\$)", r"$\1$", t)
    t = re.sub(r"\$([^$\n]+?)\$\$(?!\$)", r"$\1$", t)
    # $..$ rồi còn $ dính ngay sau
    t = re.sub(r"(\$[^$\n]+?\$)\$+", r"\1", t)
    # $ $10^{5}$ → $10^{5}$ (bỏ $ rỗng đầu, giữ công thức)
    t = re.sub(r"\$\s+\$(?=[^$\n])", "$", t)
    # $ $ thật sự rỗng
    t = re.sub(r"\$\s+\$(?=\s|$)", " ", t)
    t = re.sub(r"\$\s*\$", " ", t)
    # $ lẻ giữa khoảng trắng
    t = re.sub(r"(?<=\s)\$(?=\s)", "", t)
    # KHÔNG gỡ $ trước dấu câu — sẽ làm hỏng $20$, $H$… trong lời giải dài
    # .$ / ,$ rác sau công thức (giữ $10^{5}$.)
    t = re.sub(r"(\$[^$\n]+?\$)\.(\$)(?=\s|$|[A-Za-zÀ-ỹĐđ])", r"\1.", t)
    t = re.sub(r"(\$[^$\n]+?\$)([,.;:])\$(?=\s|$)", r"\1\2", t)
    # Chỉ gỡ $ lẻ cuối chuỗi khi số $ lẻ (mở chưa đóng) — KHÔNG gỡ $ đóng hợp lệ ($...$)
    if t.endswith("$") and _latex_dollar_count(t) % 2 == 1:
        t = t[:-1]
    return t


def _fix_merged_inline_math(t: str) -> str:
    if "$" not in t:
        return _fix_plain_text_gaps(t)
    out, i = [], 0
    n = len(t)
    while i < n:
        if t[i] != "$":
            d1 = t.find("$", i)
            if d1 < 0:
                out.append(_fix_plain_text_gaps(t[i:]))
                break
            out.append(_fix_plain_text_gaps(t[i:d1]))
            i = d1
            continue
        # Giữ khối display $$ ... $$
        if i + 1 < n and t[i + 1] == "$":
            end = t.find("$$", i + 2)
            if end >= 0:
                out.append(t[i : end + 2])
                i = end + 2
                continue
        d2 = t.find("$", i + 1)
        if d2 < 0:
            rest = t[i + 1 :]
            if rest.strip() and ("\\" in rest or "{" in rest):
                out.append(f"${_fix_one_math_inner(rest)}$")
            else:
                out.append(_fix_plain_text_gaps(rest))
            break
        inner = t[i + 1 : d2]
        if not inner.strip():
            i = d2 + 1
            continue
        while d2 + 1 < n and t[d2 + 1] == "$" and (d2 + 2 >= n or t[d2 + 2] != "$"):
            d2 += 1
        inner = _fix_one_math_inner(inner)
        out.append(f"${inner}$")
        i = d2 + 1
    return "".join(out)


def _strip_latex_list_markup(t: str) -> str:
    t = re.sub(r"\\begin\s*\{\s*enumerate\s*\}", "", t, flags=re.I)
    t = re.sub(r"\\end\s*\{\s*enumerate\s*\}", "", t, flags=re.I)
    t = re.sub(r"\\begin\s*\{\s*itemize\s*\}", "", t, flags=re.I)
    t = re.sub(r"\\end\s*\{\s*itemize\s*\}", "", t, flags=re.I)
    t = re.sub(r"\\item\s*", "\n• ", t, flags=re.I)
    t = re.sub(r"\\item(?=[A-Za-zÀ-ỹĐđ])", "\n• ", t, flags=re.I)
    return t


def _fix_math_bs_in_pairs(t: str) -> str:
    def _fix_math_bs(m: re.Match) -> str:
        inner = m.group(1).replace("\\\\", "\\")
        return f"${inner}$"
    return re.sub(r"\$([^$]+)\$", _fix_math_bs, t)


def _latex_needs_heavy_normalize(t: str) -> bool:
    """Chỉ chạy gộp khối $ / sửa Word khi text thật sự lỗi — tránh phá prose tiếng Việt."""
    if not t:
        return False
    if re.search(r"\\(?:item|begin\s*\{enumerate|begin\s*\{itemize|acute)", t, re.I):
        return True
    if re.search(r"\$\{|\$\$[^$]", t):
        return True
    if re.search(r"\$\s+\$(?=[^$\n])", t):
        return True
    if not _latex_structure_ok(t):
        return True
    return False


def normalize_latex_light(s: Any) -> str:
    """Chuẩn hóa nhẹ — AI hint / lời giải đã đúng: KHÔNG gộp khối $, không sửa câu chữ."""
    t = clean(s)
    if not t:
        return ""
    orig = t
    t = re.sub(r"\$\$\s*", "$", t)
    t = re.sub(r"\s*\$\$", "$", t)
    t = re.sub(r"\$\s*\n+\s*\$", "", t)
    t = re.sub(r"\$\s*\n+\s*([^$\n]+?)\s*\n+\s*\$", r"$(\1)$", t)
    t = re.sub(r"\$\s*\n+([^$\n]+?)\s*\$", r"$(\1)$", t)
    if _latex_structure_ok(t):
        return _fix_math_bs_in_pairs(t)
    t = _fix_surplus_dollar_signs(t)
    t = _fix_math_bs_in_pairs(t)
    if not _latex_structure_ok(t) and _latex_structure_ok(orig):
        return _fix_math_bs_in_pairs(orig)
    return t


def normalize_latex_text(s: Any) -> str:
    """Chuẩn hóa LaTeX từ Word/Sheet: ${\\beta}$, \\item, khối $ nuốt tiếng Việt."""
    t = clean(s)
    if not t:
        return ""
    orig = t
    if _latex_structure_ok(t) and not _latex_needs_heavy_normalize(t):
        return normalize_latex_light(t)
    t = _strip_latex_list_markup(t)
    t = _fix_surplus_dollar_signs(t)
    t = re.sub(r"\$\{\s*([^}$\n]+?)\s*\}\s*\$", r"$(\1)$", t)
    t = re.sub(r"\$\{\s*([^}$\n]+?)\s*\}", r"$(\1)$", t)
    t = re.sub(r"(?<![$\\])\{\s*\(\s*([^}]+?)\s*\)\s*\}(?![$])", r"$(\1)$", t)
    t = re.sub(r"\$\(\((\\?[a-zA-Z]+)\)\)\$\.?", r"$\\1$.", t)
    t = re.sub(r"\$\(\((\\?[a-zA-Z]+)\)\)(?!\$)", r"$\\1$", t)
    t = _fix_merged_inline_math(t)
    t = _fix_surplus_dollar_signs(t)
    t = re.sub(r"(\$[^$\n]+?\$)\$+", r"\1", t)
    t = re.sub(r"\$\s*\$", " ", t)
    t = _fix_math_bs_in_pairs(t)
    t = _fix_broken_latex_patterns(t)
    if not _latex_structure_ok(t) and _latex_structure_ok(orig):
        return orig
    return t


def _fix_broken_latex_patterns(t: str) -> str:
    """Sửa lỗi LaTeX phổ biến từ Word/Sheet (ngoài khối $...$)."""
    if not t:
        return t
    t = re.sub(r"\\acute\{\\mathrm\{i\}\}", "í", t, flags=re.I)
    t = re.sub(
        r"\\text\{\s*([^}]*?)\s*\}\s*\\acute\{[^}]+\}\s*\\text\{\s*t\s*\}",
        r"\\text{\1ít}",
        t,
        flags=re.I,
    )
    t = re.sub(r"(\d+)\s*c\{\{?\s*m\s*\}\}?\^\{3\}", r"$\\1\\,\\text{cm}^{3}$", t, flags=re.I)
    t = re.sub(
        r"\$\(\s*(\d+)\^\{([^{}]+)\}\}(Pa|kPa)\.?\s*\$",
        r"$\1^{\2}\\,\\text{\3}.$",
        t,
        flags=re.I,
    )
    t = re.sub(
        r"\$(\d+)\^\{([^{}]+)\}\}(Pa|kPa)\.?\$",
        r"$\1^{\2}\\,\\text{\3}.$",
        t,
        flags=re.I,
    )
    return t



def stable_hash(text: str, n: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n].upper()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime_any(s: Any) -> Optional[datetime]:
    """Đọc ngày giờ từ Google Sheet: 30/05/2026 13:37, 2026-05-30, hoặc serial dạng text."""
    s = clean(s)
    if not s:
        return None
    # Nếu Google Sheet trả serial ngày dạng số, 1 tương ứng 1899-12-30.
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", s):
            base = datetime(1899, 12, 30)
            return base + timedelta(days=float(s))
    except Exception:
        pass
    fmts = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def fmt_datetime(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def expired_datetime(s: Any) -> bool:
    dt = parse_datetime_any(s)
    return bool(dt and datetime.now() > dt)


def parse_float_vn(s: Any) -> Optional[float]:
    s = clean(s).replace(" ", "")
    if not s:
        return None
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def norm_letter(s: Any) -> str:
    s = clean(s).upper()
    m = re.search(r"[ABCD]", s)
    return m.group(0) if m else ""


def norm_dang(s: Any) -> str:
    t = re.sub(r"[/\\]+", " ", str(s or ""))
    k = key_norm(t)
    k2 = k.replace(" ", "")
    if (
        "dung sai" in k
        or "dungsai" in k2
        or "d/s" in k2
        or re.search(r"\b(ds|tf)\b", k)
        or "true false" in k
        or "truefalse" in k2
    ):
        return "Đúng sai"
    if any(x in k for x in ["tra loi ngan", "short", "tln", "shortans"]):
        return "Trả lời ngắn"
    if any(x in k for x in ["tu luan", "essay"]) or k == "tl":
        return "Tự luận"
    if any(x in k for x in ["trac nghiem", "tracnghiem", "mcq", "multiple choice"]) or k in ("tn", "tn4"):
        return "Trắc nghiệm"
    if k2 in ("ds", "d/s") or k == "ds":
        return "Đúng sai"
    return "Trắc nghiệm"


def bump_count(d: Dict[str, int], key: str) -> None:
    if not key:
        return
    d[key] = int(d.get(key, 0)) + 1


def question_mucdo_parts(q: Dict[str, Any]) -> List[str]:
    lv = clean(q.get("MucDo", "")).upper()
    parts = [p.strip() for p in re.split(r"[,;/|]+", lv) if p.strip()]
    if parts:
        return parts
    return [lv] if lv else []


def infographic_mucdo_label(q: Dict[str, Any]) -> str:
    """Chuẩn hóa mức độ từ cột I để đưa vào prompt infographic."""
    parts = question_mucdo_parts(q)
    if parts:
        return " · ".join(parts)
    return clean(q.get("MucDo", ""))


def infographic_mucdo_highlight_hint(label: str) -> str:
    """Gợi ý màu badge mức độ trên infographic."""
    if not label:
        return "Sheet chưa ghi mức độ (cột I) — vẫn để badge «Mức độ: ?» hoặc bỏ qua."
    u = key_norm(label)
    hints: List[str] = []
    if "nb" in u or "nen tang" in u:
        hints.append("NB → badge xanh lá, chữ TO")
    if re.search(r"\bth\b", u) or "thong hieu" in u:
        hints.append("TH → badge xanh dương")
    if "vdc" in u:
        hints.append("VDC → badge đỏ đậm")
    elif re.search(r"\bvd\b", u) or "van dung" in u:
        hints.append("VD → badge cam")
    if not hints:
        hints.append(f"Badge nổi bật ghi đúng «{label}»")
    return " | ".join(hints)


def _infographic_notebook_style_rules() -> List[str]:
    """Poster giáo dục hiện đại + ký hiệu khoa học cho prompt Gemini tạo ảnh."""
    return [
        "═══ PHONG CÁCH: POSTER GIÁO DỤC HIỆN ĐẠI (BẮT BUỘC) ═══",
        "• Thiết kế POSTER INFOGRAPHIC đầy đủ màu, hiện đại — gradient, card bo góc, bóng đổ nhẹ, layout sạch như Canva/Pinterest giáo dục",
        "• Nền poster: gradient tối–sáng (xanh đậm→tím, hoặc navy→cyan) HOẶC nền trắng/xám nhạt với các card màu nổi — phải trông HIỆN ĐẠI, không nhạt nhoà",
        "• Chữ: tiêu đề vùng font sans-serif đậm, hiện đại; nội dung rõ ràng (có thể viết tay sạch hoặc font tròn dễ đọc) — không nguệch ngoạc",
        "• Trình bày KHOA HỌC theo ĐÚNG 4 VÙNG tách rõ (xem mục PHÂN VÙNG) — mỗi vùng là một CARD/PANEL màu riêng",
        "• Lời giải: đánh số bước trong badge/vòng tròn màu (Bước 1, 2…); «Cho:», «KL:», «Đáp án:» trong hộp highlight",
        "• Hình vẽ: sơ đồ vector phẳng (flat design) nhiều màu, nhãn F, v, I, B⃗… chuẩn SGK",
        "",
        "═══ KÝ HIỆU & CÔNG THỨC (PHẢI ĐÚNG — KHÔNG SAI, KHÔNG LỘ MÃ LATEX) ═══",
        "• Viết ký hiệu Toán-Lý CHUẨN bằng tay, dễ đọc — KHÔNG in raw LaTeX ($, \\frac, \\text, \\cdot…)",
        "• Chữ Hy Lạp: α β γ Δ θ λ μ ν ρ σ τ φ ω Ω π — viết đúng hình dạng, không nhầm chữ Latin",
        "• Chỉ số trên/dưới: v₀, x₁, F_N, m_n, U_m, Q_thu, I_0 — viết nhỏ, rõ ràng dưới/trên ký tự gốc",
        "• Phân số: viết dạng a/b hoặc phân số dọc tay (tử trên, mẫu dưới, gạch ngang) — không dùng \\frac",
        "• Căn: √2, √(2as) — dấu căn bao trùm biểu thức",
        "• Vectơ: v⃗, F⃗ hoặc mũi tên trên chữ — thống nhất trong cả ảnh",
        "• Toán tử: · hoặc × (nhân), ±, ≤, ≥, ≠, ≈, →, ⇒ — đúng nghĩa vật lý",
        "• Đơn vị SI: m, kg, s, A, V, Ω, W, J, N, Hz, °C — viết đúng, có khoảng cách với số (10 m/s, 5 Ω)",
        "• Số & đơn vị: 3,14·10⁸ hoặc 3,14×10⁸ — lũy thừa viết superscript nhỏ (10⁸, cm², m/s²)",
        "• Vật lý thường gặp: F=ma, P=UI, Q=mcΔt, v²−v₀²=2as, sin/cos/tan, log — viết đúng công thức SGK",
        "• Mạch điện / quang / cơ: ký hiệu chuẩn (nguồn, R, C, L, mũi tên sáng, trục tọa độ Oxy)",
        "• Copy ĐÚNG số liệu & ký hiệu từ Sheet — chỉ đổi từ mã LaTeX sang dạng viết tay chuẩn, không đổi giá trị",
    ]


def _infographic_scientific_layout_rules() -> List[str]:
    """Bố cục 4 vùng poster hiện đại — khoa học đúng Sheet."""
    return [
        "═══ LAYOUT POSTER HIỆN ĐẠI (GIỮ 4 VÙNG — KHOA HỌC) ═══",
        "• Header full-width gradient: «MÔN · CHƯƠNG · BÀI» chữ trắng to + badge MỨC ĐỘ 3D/glow góc phải",
        "• 4 CARD/PANEL xếp dọc — mỗi card bo góc 12–16px, bóng đổ, viền màu, nền gradient riêng:",
        "  – Card ĐỀ BÀI | Card PHƯƠNG ÁN | Card HÌNH MINH HỌA | Card LỜI GIẢI",
        "• KHÔNG in chữ «KHỐI 1», «KHỐI 2»… — chỉ tiêu đề «ĐỀ BÀI», «PHƯƠNG ÁN», «HÌNH MINH HỌA», «LỜI GIẢI» trên thanh màu",
        "• Phương án A/B/C/D: grid 2×2 hoặc xếp dọc trong card — mỗi ô một màu nhẹ; đáp án đúng card nổi bật nhất",
        "• Đ/S: badge pill «ĐÚNG» xanh neon / «SAI» đỏ cam cạnh từng ý",
        "",
        "• TRÁNH: emoji, clip-art vui, chữ tiếng Anh, chữ «KHỐI»",
        "• ID câu, Mã đề: footer nhỏ, opacity thấp",
    ]


def _infographic_vivid_color_rules() -> List[str]:
    """Palette poster hiện đại đầy đủ màu — bão hòa, gradient, nổi bật."""
    return [
        "═══ MÀU SẮC POSTER ĐẦY ĐỦ & HIỆN ĐẠI (BẮT BUỘC) ═══",
        "• Tổng thể: POSTER GIÁO DỤC hiện đại — màu BÃO HÒA, gradient đầy đủ, tương phản mạnh, nhìn từ xa vẫn rõ",
        "• Nền toàn poster: gradient dọc đậm (ví dụ #1E3A8A → #7C3AED → #0F172A) hoặc nền sáng #F8FAFC với card màu rực",
        "",
        "• MÀU TỪNG CARD (gradient + viền sáng):",
        "  – ĐỀ BÀI: gradient xanh dương #2563EB → #3B82F6, chữ trắng, icon nhỏ (nếu có) trắng",
        "  – PHƯƠNG ÁN: gradient xanh lá #059669 → #10B981 hoặc vàng #EAB308 → #FACC15; ô A/B/C/D xen kẽ màu",
        "  – HÌNH MINH HỌA: gradient tím cyan #6366F1 → #06B6D4 — sơ đồ flat vector đa màu (xanh/đỏ/cam/hồng)",
        "  – LỜI GIẢI: gradient cam hồng #F97316 → #EC4899 hoặc tím #8B5CF6 → #A855F7 — bước giải badge tròn đánh số",
        "",
        "• NHẤN MẠNH (poster style):",
        "  – Đáp án đúng TN: card glow vàng #FDE047, viền 3px, scale lớn hơn các ô khác",
        "  – ĐÚNG: pill xanh #22C55E chữ trắng | SAI: pill đỏ #EF4444 chữ trắng",
        "  – Công thức: khung glassmorphism (nền trắng 80% opacity, viền cyan)",
        "  – KL / Đáp án: banner gradient cam→đỏ, chữ trắng đậm",
        "",
        "• Badge MỨC ĐỘ: sticker 3D/glow — NB #22C55E · TH #3B82F6 · VD #F59E0B · VDC #DC2626",
        "• Header: gradient xanh→tím full bleed, chữ trắng bold, có thể thêm pattern hình học mờ (grid, dots)",
        "• Sơ đồ: flat illustration hiện đại, ≥4 màu, nét sạch, không xám đơn điệu",
        "• Hiệu ứng: bóng đổ card, bo góc, có thể viền gradient — trông như poster Canva 2024–2026",
        "• Vẫn KHÔNG: emoji, clip-art trẻ con, tiếng Anh, chữ «KHỐI 1/2/3/4»",
    ]


def _tf_token_to_ds(token: Any) -> str:
    t = clean(token)
    if not t:
        return ""
    if t.upper() in ("Đ", "D"):
        return "Đ"
    if t.upper() == "S":
        return "S"
    k = key_norm(t)
    if k in ["d", "đ", "dung", "đung", "đúng", "true", "t"]:
        return "Đ"
    if k in ["s", "sai", "false", "f"]:
        return "S"
    return ""


def parse_tf_values(value: Any) -> List[str]:
    """Chuẩn hóa đáp án Đ/S thành danh sách 4 phần tử (A,B,C,D)."""
    if isinstance(value, list):
        out = [_tf_token_to_ds(v) for v in value]
        while len(out) < 4:
            out.append("")
        return out[:4]

    raw = clean(value)
    if not raw:
        return ["", "", "", ""]

    low = strip_accents(raw).lower()
    letter_hits = re.findall(
        r"(?:^|[\s;,|]+)(?:[\[\(]?\s*([abcd])\s*[\]\)]?\s*[-.:=]?\s*)"
        r"(đúng|dung|d|đ|sai|s|true|false)\b",
        low,
        re.I,
    )
    if len(letter_hits) >= 2:
        mp = {"a": 0, "b": 1, "c": 2, "d": 3}
        out = ["", "", "", ""]
        for letter, word in letter_hits:
            idx = mp.get(clean(letter).lower())
            if idx is None:
                continue
            tok = _tf_token_to_ds(word)
            if tok:
                out[idx] = tok
        if sum(1 for x in out if x) >= 2:
            return out

    parts = re.split(r"[,;|/\n]+", raw)
    if len(parts) >= 2:
        out = [_tf_token_to_ds(p) for p in parts]
        if sum(1 for x in out if x) >= 2:
            while len(out) < 4:
                out.append("")
            return out[:4]

    s = strip_accents(raw).upper()
    s = s.replace("\u0110", "D").replace("\u0111", "D")
    s = s.replace("DUNG", "D").replace("TRUE", "D").replace("SAI", "S").replace("FALSE", "S")
    vals = re.findall(r"[DS]", s)[:4]
    out = ["Đ" if v == "D" else "S" for v in vals]
    while len(out) < 4:
        out.append("")
    return out[:4]


def format_tf_answer_display(q: Dict[str, Any], dapan: Any = None) -> str:
    vals = parse_tf_values(dapan if dapan is not None else q.get("DapAn"))
    bits = []
    for idx, L in enumerate(["A", "B", "C", "D"]):
        if not clean(q.get(L)):
            continue
        v = vals[idx] if idx < len(vals) else ""
        if v == "Đ":
            bits.append(f"{L}=Đúng")
        elif v == "S":
            bits.append(f"{L}=Sai")
    return " · ".join(bits) if bits else clean(dapan if dapan is not None else q.get("DapAn"))


def looks_like_dungsai_answer(value: Any) -> bool:
    """Đáp án có ≥2 mệnh đề Đ/S — không nhầm trắc nghiệm một chữ A/B/C/D."""
    if value is None or not clean(value):
        return False
    raw = strip_accents(clean(value).upper()).strip()
    if re.fullmatch(r"[ABCD]", raw):
        return False
    vals = parse_tf_values(value)
    filled = [v for v in vals if v in ("Đ", "S")]
    return len(filled) >= 2


def has_tf_statements(q: Dict[str, Any]) -> bool:
    count = 0
    for L in ["A", "B", "C", "D"]:
        if clean(q.get(L)):
            count += 1
    return count >= 2


def is_mcq_letter_answer(value: Any) -> bool:
    """Đáp án trắc nghiệm: đúng một chữ A/B/C/D."""
    raw = strip_accents(clean(value).upper()).strip()
    return bool(re.fullmatch(r"[ABCD]", raw))


def looks_like_short_answer(q: Dict[str, Any]) -> bool:
    """Đáp án là số hoặc chuỗi kết quả — không phải chọn A/B/C/D hay Đ/S."""
    dapan = clean(q.get("DapAn"))
    if not dapan:
        return False
    if is_mcq_letter_answer(dapan):
        return False
    if looks_like_dungsai_answer(dapan):
        return False
    if parse_float_vn(dapan) is not None:
        return True
    return len(dapan) <= 200



def question_dang(q: Dict[str, Any]) -> str:
    """Dạng câu chuẩn — luôn suy từ cột J/H + đáp án."""
    ed = effective_dang(q)
    if ed in ("Đúng sai", "Trắc nghiệm", "Trả lời ngắn", "Tự luận"):
        return ed
    return norm_dang(ed)


def dang_matches(q: Dict[str, Any], dang_filter: str) -> bool:
    if not clean(dang_filter):
        return True
    return question_dang(q) == norm_dang(dang_filter)


def dang_metadata_raw(q: Dict[str, Any]) -> str:
    """Cột mô tả dạng câu: J (_DangCol) → H (Dạng bài tập) → header Dang."""
    for k in ("_DangCol", "DangBaiTap", "Dang"):
        v = clean(q.get(k, ""))
        if v:
            return v
    return ""


def effective_dang(q: Dict[str, Any]) -> str:
    """Suy luận dạng câu từ cột J/H + đáp án."""
    raw_col = dang_metadata_raw(q)
    if raw_col:
        dang_col = norm_dang(raw_col)
        if dang_col in DANG_GROUP_ORDER:
            return dang_col

    dapan = q.get("DapAn")
    has_opts = has_tf_statements(q)

    # Đáp án SSĐĐ / Đ,S,... → Đúng sai khi cột J/H trống hoặc không rõ
    if looks_like_dungsai_answer(dapan):
        return "Đúng sai"

    # Đáp án một chữ B/D... → trắc nghiệm
    if is_mcq_letter_answer(dapan) and has_opts:
        return "Trắc nghiệm"

    # Đáp án số/chữ (không phải A-D, không phải Đ/S) → trả lời ngắn
    if looks_like_short_answer(q):
        return "Trả lời ngắn"

    return "Trắc nghiệm"


DANG_GROUP_ORDER = ["Trắc nghiệm", "Đúng sai", "Trả lời ngắn", "Tự luận"]
RANDOM_PRACTICE_SPEC: List[Tuple[str, int]] = [
    ("Trắc nghiệm", 18),
    ("Đúng sai", 4),
    ("Trả lời ngắn", 6),
]


def question_solution_status(q: Dict[str, Any]) -> str:
    """Đánh giá lời giải Sheet: full (đủ tự học) | partial | none."""
    dap = clean(q.get("DapAn", ""))
    lg = clean(q.get("LoiGiai", ""))
    if not lg or len(lg) < 20:
        return "none" if not dap else "partial"
    if not dap:
        return "partial"
    dang = effective_dang(q)
    if dang == "Đúng sai":
        need = [L for L in "ABCD" if clean(q.get(L))]
        lg_map = _parse_loigiai_bodies_by_letter(lg)
        if len(need) >= 2:
            missing = [L for L in need if L not in lg_map or len(lg_map.get(L, "")) < 12]
            if not missing and len(lg) >= 50:
                return "full"
            return "partial" if lg_map else ("partial" if len(lg) >= 35 else "none")
        return "partial" if len(lg) >= 40 else "none"
    if dang == "Trắc nghiệm":
        if is_mcq_letter_answer(dap) and len(lg) >= 40:
            return "full"
        return "partial" if len(lg) >= 22 else "none"
    if dang == "Trả lời ngắn":
        return "full" if len(lg) >= 30 else ("partial" if len(lg) >= 18 else "none")
    if dang == "Tự luận":
        return "full" if len(lg) >= 70 else ("partial" if len(lg) >= 35 else "none")
    return "full" if len(lg) >= 45 else "partial"


def derive_khoi(lop: Any) -> str:
    """Suy Khối (10/11/12) từ cột Lớp — vd. 12QT1 → 12."""
    s = clean(lop)
    if not s:
        return ""
    m = re.match(r"^(\d{1,2})", s)
    if m:
        return m.group(1)
    m2 = re.search(r"\b(10|11|12)\b", s)
    return m2.group(1) if m2 else ""


def question_matches_pool_filter(
    q: Dict[str, Any],
    *,
    mon: str = "",
    khoi: str = "",
    lop: str = "",
    chuong: str = "",
    chuongs: Optional[List[str]] = None,
    baihoc: str = "",
    bode: str = "",
    level: str = "",
    sol_full_only: bool = False,
) -> bool:
    if mon and clean(q.get("Mon")) != mon:
        return False
    if khoi and derive_khoi(q.get("Lop", "")) != clean(khoi):
        return False
    if lop and clean(q.get("Lop")) != lop:
        return False
    ch_list = [clean(c) for c in (chuongs or []) if clean(c)]
    if ch_list:
        if clean(q.get("Chuong")) not in ch_list:
            return False
    elif chuong and clean(q.get("Chuong")) != chuong:
        return False
    if baihoc and clean(q.get("BaiHoc")) != baihoc:
        return False
    if bode and clean(q.get("BoDe")) != bode:
        return False
    lv = clean(level).upper()
    if lv and lv not in question_mucdo_parts(q) and lv not in clean(q.get("MucDo", "")).upper():
        return False
    if sol_full_only and question_solution_status(q) != "full":
        return False
    if is_trial() and access_level_from_text(q.get("QuyenTruyCap", "")) != "FREE":
        return False
    return True


def sort_questions_by_dang_groups(
    qs: List[Dict[str, Any]],
    *,
    shuffle_within: bool = False,
) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {d: [] for d in DANG_GROUP_ORDER}
    other: List[Dict[str, Any]] = []
    for q in qs:
        d = question_dang(q)
        if d in buckets:
            buckets[d].append(q)
        else:
            other.append(q)
    out: List[Dict[str, Any]] = []
    for d in DANG_GROUP_ORDER:
        chunk = list(buckets[d])
        if shuffle_within and len(chunk) > 1:
            random.shuffle(chunk)
        out.extend(chunk)
    if other:
        if shuffle_within:
            random.shuffle(other)
        out.extend(other)
    return out


def norm_role(s: Any) -> str:
    k = key_norm(s).replace(".", "")
    if "admin" in k:
        return "ADMIN"
    if "svip" in k or "s vip" in k or "super" in k:
        return "S.VIP"
    if "trial" in k or "dung thu" in k or "thu nghiem" in k:
        return "TRIAL"
    if (
        "vip" in k
        or "premium" in k
        or "co phi" in k
        or "tra phi" in k
        or "traphi" in k
        or "member" in k
        or "plus" in k
    ):
        return "VIP"
    if "free" in k or "mien phi" in k:
        return "FREE"
    return clean(s).upper() or "FREE"


def refresh_session_role_from_store() -> None:
    """Cập nhật role từ sheet HOC_VIEN (tránh session cũ ghi FREE trong khi sheet đã VIP)."""
    mahs = clean(session.get("mahs", ""))
    if not mahs:
        return
    try:
        st = get_store()
        st.ensure_users_loaded()
        user = st.users.get(mahs)
        if not user:
            for k, v in st.users.items():
                if key_norm(k) == key_norm(mahs):
                    user = v
                    break
        if user and user.get("role"):
            session["role"] = norm_role(user.get("role"))
    except Exception:
        pass


def is_admin() -> bool:
    refresh_session_role_from_store()
    return norm_role(session.get("role", "")) == "ADMIN"


def is_trial() -> bool:
    return session.get("role") == "TRIAL"


def can_use_5050() -> bool:
    # Học viên dùng thử KHÔNG dùng 50:50. Chỉ VIP/S.VIP/ADMIN.
    return session.get("role") in ["VIP", "S.VIP", "ADMIN"]


def can_view_solution_after_submit() -> bool:
    # FREE và TRIAL không xem đáp án/lời giải sau nộp.
    return session.get("role") in ["VIP", "S.VIP", "ADMIN"]


def can_view_solution_live() -> bool:
    """VIP/SVIP/ADMIN có quyền xem đáp án/lời giải khi làm bài (client: sau khi làm + chấm từng câu)."""
    refresh_session_role_from_store()
    return norm_role(session.get("role", "")) in ["VIP", "S.VIP", "ADMIN"]


def can_use_infographic() -> bool:
    """VIP/SVIP/ADMIN: tạo prompt infographic (VIP/SVIP phải trả lời đúng câu trước)."""
    refresh_session_role_from_store()
    return norm_role(session.get("role", "")) in ["VIP", "S.VIP", "ADMIN"]


def can_exact_hint() -> bool:
    role = session.get("role", "")
    return role in ["VIP", "S.VIP", "SVIP", "ADMIN"]


def is_vip_formula_hint() -> bool:
    """VIP/SVIP: gợi ý công thức thay số — không đưa đáp án cuối trong AI gợi ý."""
    refresh_session_role_from_store()
    r = norm_role(session.get("role", ""))
    return r in ["VIP", "S.VIP"]


def can_use_ai_hint() -> bool:
    """Chỉ VIP / SVIP / ADMIN được dùng Gợi ý AI."""
    if is_admin():
        return True
    refresh_session_role_from_store()
    return norm_role(session.get("role", "")) in ["VIP", "S.VIP"]


def require_ai_hint_json():
    """Trả về Response lỗi nếu tài khoản không được dùng AI."""
    if can_use_ai_hint():
        return None
    return jsonify(
        {"error": "Gợi ý AI chỉ dành tài khoản VIP / SVIP / ADMIN."}
    ), 403


def access_level_from_text(value: Any) -> str:
    """Chuẩn hóa quyền truy cập đề: FREE hoặc VIP.
    Nếu cột QuyenTruyCap/Gói để trống thì mặc định là FREE để dễ đưa kho câu lên trước.
    Chỉ khi ghi rõ VIP / có phí / trả phí / premium thì coi là đề VIP.
    """
    k = key_norm(value)
    if not k:
        return "FREE"
    if any(x in k for x in ["vip", "s vip", "svip", "co phi", "tra phi", "premium", "paid", "thu phi"]):
        return "VIP"
    return "FREE"


def is_free_access(value: Any) -> bool:
    return access_level_from_text(value) == "FREE"


def quiz_access_level(qs: List[Dict[str, Any]]) -> str:
    # Nếu chỉ cần 1 câu trong đề ghi VIP thì cả đề là VIP.
    for q in qs:
        if access_level_from_text(q.get("QuyenTruyCap", "")) == "VIP":
            return "VIP"
    return "FREE"


def require_login_json():
    if not session.get("mahs"):
        return jsonify({"error": "Chưa đăng nhập"}), 401
    # Chống 2 thiết bị dùng chung tài khoản: token mới đá token cũ trong RAM.
    store = get_store()
    mahs = session.get("mahs")
    token = session.get("session_token")
    if mahs and token and store.active_tokens.get(mahs) and store.active_tokens.get(mahs) != token:
        session.clear()
        return jsonify({"error": "Tài khoản này đã đăng nhập ở thiết bị khác."}), 401
    return None

# ============================================================
# ÁNH XẠ CỘT
# ============================================================

ALIASES: Dict[str, List[str]] = {
    "MaDe": ["MaDe", "Mã đề", "Ma De", "MA_DE", "ma_de"],
    "ID": ["ID", "Id", "Mã câu", "MaCau", "Ma Cau"],
    "BoDe": ["BoDe", "Bộ đề", "Bo De", "Bộ Đề"],
    "De": ["De", "Đề", "TenDe", "Tên đề", "Tên Đề"],
    "Lop": ["Lop", "Lớp", "LopHoc", "Lớp học", "Khối"],
    "Mon": ["Mon", "Môn"],
    "Chuong": ["Chuong", "Chương", "ChuDe", "Chủ đề", "Chủ Đề"],
    "BaiHoc": ["BaiHoc", "Bài học", "Bài Học", "Bai", "Bài"],
    "DangBaiTap": ["DangBaiTap", "Dạng bài tập", "Dạng Bài Tập", "Dang Bai Tap"],
    "MucDo": ["MucDo", "Mức độ", "Mức Độ", "Muc_do"],
    "Dang": ["Dang", "Dạng", "Loai", "Loại", "LoaiCau", "Loại câu", "Loai_Cau_Hoi", "Loại câu hỏi", "Loai Cau Hoi"],
    "CauHoi": ["CauHoi", "NoiDung", "Nội dung", "Câu hỏi", "DeBai", "Đề bài", "Cau_hoi"],
    "A": ["A", "PA_A", "LuaChonA"],
    "B": ["B", "PA_B", "LuaChonB"],
    "C": ["C", "PA_C", "LuaChonC"],
    "D": ["D", "PA_D", "LuaChonD"],
    "DapAn": ["DapAn", "Đáp án", "Đáp Án", "Answer", "Dap_an"],
    "SaiSo": ["SaiSo", "Sai số", "Sai Số", "Tolerance"],
    "LoiGiai": ["LoiGiai", "Lời giải", "Lời Giải", "Giai", "Giải"],
    "Diem": ["Diem", "Điểm"],
    "HinhAnh": ["HinhAnh", "Hình ảnh", "Hình Ảnh", "Image", "LinkHinhAnh", "Link hình ảnh", "Link ảnh", "Anh", "Ảnh"],
    "QuyenTruyCap": ["QuyenTruyCap", "Quyền truy cập", "Quyen", "Goi", "Gói"],
    # HOC_VIEN
    "MaHS": ["MaHS", "Mã HS", "Mã học sinh", "TaiKhoan", "Tài khoản", "Username"],
    "HoTen": ["HoTen", "Họ tên", "Họ Tên", "Tên", "Name"],
    "MatKhau": ["MatKhau", "Mật khẩu", "Mat Khau", "Password"],
    "LoaiTaiKhoan": ["LoaiTaiKhoan", "Loại tài khoản", "Loai TK", "Role", "Quyen"],
    "TrangThai": ["TrangThai", "Trạng thái", "Status"],
    "SoDienThoai": ["SoDienThoai", "Số điện thoại", "SDT", "SĐT", "Phone"],
    "DeviceId": ["DeviceId", "DeviceID", "Thiết bị"],
    "NgayDangKy": ["NgayDangKy", "Ngày đăng ký", "Ngay Dang Ky", "RegisterAt", "CreatedAt"],
    "NgayHetHanTrial": ["NgayHetHanTrial", "Ngày hết hạn trial", "Ngay Het Han Trial", "TrialUntil", "HetHanDungThu"],
    "NgayHetHanTaiKhoan": ["NgayHetHanTaiKhoan", "Ngày hết hạn tài khoản", "Ngay Het Han Tai Khoan", "AccountUntil", "HetHanTaiKhoan"],
}

USER_REQUIRED_HEADERS = [
    "MaHS", "HoTen", "LopHoc", "LoaiTaiKhoan", "TrangThai", "SoDienThoai",
    "NgayDangKy", "NgayHetHanTrial", "DeviceId", "NgayHetHanTaiKhoan", "MatKhau"
]

QUESTION_FIELDS = [
    "MaDe", "ID", "BoDe", "De", "Lop", "Mon", "Chuong", "BaiHoc", "DangBaiTap",
    "MucDo", "Dang", "CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo",
    "LoiGiai", "Diem", "HinhAnh", "QuyenTruyCap",
]

EDITABLE_FIELDS = ["CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo", "MucDo", "Dang", "LoiGiai", "HinhAnh", "QuyenTruyCap"]

CREATE_QUESTION_FIELDS = [
    "MaDe", "ID", "BoDe", "De", "Lop", "Mon", "Chuong", "BaiHoc", "DangBaiTap",
    "QuyenTruyCap", "Diem",
] + EDITABLE_FIELDS

# Cột 1-indexed theo Google Sheet thực tế (I=MucDo … T=HinhAnh).
SHEET_QUESTION_FIXED_COL_1: Dict[str, int] = {
    "MucDo": 9,
    "Dang": 10,
    "CauHoi": 11,
    "A": 12,
    "B": 13,
    "C": 14,
    "D": 15,
    "DapAn": 16,
    "SaiSo": 17,
    "LoiGiai": 18,
    "HinhAnh": 20,
}


def header_map(headers: List[str]) -> Dict[str, int]:
    return {key_norm(h): i for i, h in enumerate(headers)}


def find_col(headers: List[str], canonical: str) -> Optional[int]:
    mp = header_map(headers)
    for name in ALIASES.get(canonical, [canonical]):
        k = key_norm(name)
        if k in mp:
            return mp[k]
    return None


def header_matches_field(headers: List[str], col0: int, field: str) -> bool:
    """Tiêu đề cột tại col0 có khớp field (MucDo, Dang, CauHoi...) không."""
    if col0 < 0 or col0 >= len(headers):
        return False
    h = key_norm(headers[col0])
    if not h:
        return False
    for name in ALIASES.get(field, [field]):
        kn = key_norm(name)
        if h == kn or kn in h or h in kn:
            return True
    return False


def resolve_question_col_index(headers: List[str]) -> Dict[str, int]:
    """Ánh xạ cột theo tiêu đề — hỗ trợ cả bố cục G=Dạng (sheet gọn) và J=Dạng (sheet mở rộng)."""
    out: Dict[str, int] = {}
    for f in QUESTION_FIELDS:
        c = find_col(headers, f)
        if c is not None:
            out[f] = c
    content_fallback = {"CauHoi": 10, "A": 11, "B": 12, "C": 13, "D": 14, "DapAn": 15, "SaiSo": 16, "LoiGiai": 17, "HinhAnh": 19, "QuyenTruyCap": 20}
    for f, col0 in content_fallback.items():
        if f not in out and col0 < len(headers) and header_matches_field(headers, col0, f):
            out[f] = col0
    for f, candidates in (("Dang", (6, 9, 7)), ("MucDo", (8, 7, 6))):
        if f not in out:
            for col0 in candidates:
                if col0 < len(headers) and header_matches_field(headers, col0, f):
                    out[f] = col0
                    break
    return out


def row_val(row_vals: List[str], col: Optional[int]) -> str:
    if col is None or col < 0 or col >= len(row_vals):
        return ""
    return clean(row_vals[col])


def get_field(row: Dict[str, Any], canonical: str) -> str:
    mp = {key_norm(k): k for k in row.keys()}
    for name in ALIASES.get(canonical, [canonical]):
        k = mp.get(key_norm(name))
        if k is not None:
            return clean(row.get(k, ""))
    return ""


def canonical_question(row: Dict[str, Any]) -> Dict[str, str]:
    q = {f: get_field(row, f) for f in QUESTION_FIELDS}
    for f in ("CauHoi", "A", "B", "C", "D", "LoiGiai"):
        q[f] = normalize_latex_text(q.get(f, ""))
    da = clean(q.get("DapAn", ""))
    if da and any(x in da for x in ("$", "\\", "{", "}")):
        q["DapAn"] = normalize_latex_text(da)
    q["Dang"] = effective_dang(q)
    if not q.get("MaDe"):
        base = "|".join(key_norm(q.get(x, "")) for x in ["Lop", "Mon", "Chuong", "BaiHoc", "DangBaiTap", "BoDe", "De"])
        q["MaDe"] = "MD_" + stable_hash(base, 12)
    if not q.get("ID"):
        q["ID"] = "AUTO_" + stable_hash(json.dumps(q, ensure_ascii=False), 10)
    return q


def client_question_to_internal(raw: Any) -> Dict[str, Any]:
    """Chuyển câu hỏi từ trình duyệt về dạng server (khôi phục phiên làm bài)."""
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}
    for f in QUESTION_FIELDS:
        out[f] = clean(raw.get(f, ""))
    out["Dang"] = effective_dang(out)
    out["HinhAnh"] = normalize_image_src(out.get("HinhAnh"))
    if raw.get("_row"):
        try:
            out["_row"] = int(raw.get("_row"))
        except Exception:
            out["_row"] = raw.get("_row")
    return out


def quiz_restore_payload_from_body(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    qs = body.get("questions")
    if not isinstance(qs, list) or not qs:
        return None
    return {
        "made": clean(body.get("made", "")),
        "questions": qs[:300],
        "level_filter": clean(body.get("level_filter", "")),
        "dang_filter": clean(body.get("dang_filter", "")),
    }


def catalog_group_key(q: Dict[str, Any]) -> str:
    """Gom mục lục theo Môn + Lớp + Chương + Bài học (một thẻ / một bài)."""
    chuong = clean(q.get("Chuong", ""))
    bai = clean(q.get("BaiHoc", ""))
    if not chuong and not bai:
        return clean(q.get("MaDe", "")) or "MD_" + stable_hash("empty", 12)
    base = "|".join(key_norm(q.get(x, "")) for x in ["Mon", "Lop", "Chuong", "BaiHoc"])
    return "GRP_" + stable_hash(base, 12)


def question_content_fingerprint(q: Dict[str, Any]) -> str:
    """Dấu vết nội dung để phát hiện câu trùng trên Sheet."""
    parts = [
        clean(q.get("MaDe", "")),
        key_norm(clean(q.get("CauHoi", ""))[:2500]),
        key_norm(clean(q.get("DapAn", ""))[:300]),
        key_norm(clean(q.get("A", ""))[:400]),
        key_norm(clean(q.get("B", ""))[:400]),
    ]
    return stable_hash("|".join(parts), 16)


def analyze_question_duplicates(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Thống kê dòng trùng ID hoặc trùng nội dung (MaDe + câu hỏi + đáp án)."""
    by_id: Dict[str, List[int]] = {}
    by_fp: Dict[str, List[int]] = {}
    for q in questions:
        row = int(q.get("_row") or 0)
        if not row:
            continue
        qid = clean(q.get("ID", ""))
        fp = question_content_fingerprint(q)
        if qid:
            by_id.setdefault(qid, []).append(row)
        by_fp.setdefault(fp, []).append(row)
    dup_ids = {k: sorted(v) for k, v in by_id.items() if len(v) > 1}
    dup_content = {k: sorted(v) for k, v in by_fp.items() if len(v) > 1}
    duplicate_rows: set = set()
    for rows in dup_ids.values():
        duplicate_rows.update(rows[1:])
    for rows in dup_content.values():
        duplicate_rows.update(rows[1:])
    samples: List[str] = []
    for qid, rows in list(dup_ids.items())[:5]:
        samples.append(f"ID {qid}: dòng {', '.join(map(str, rows))}")
    shown_rows = set(sum(dup_ids.values(), []))
    for fp, rows in list(dup_content.items())[:8]:
        if rows[0] in shown_rows and len(rows) < 2:
            continue
        q0 = next((x for x in questions if int(x.get("_row") or 0) == rows[0]), {})
        tip = clean(q0.get("CauHoi", ""))[:60]
        if not any(r in shown_rows for r in rows[1:]):
            samples.append(f"Trùng nội dung ({tip}…): dòng {', '.join(map(str, rows))}")
        elif rows[0] not in shown_rows:
            samples.append(f"Trùng nội dung ({tip}…): dòng {', '.join(map(str, rows))}")
    return {
        "duplicate_id_groups": len(dup_ids),
        "duplicate_content_groups": len(dup_content),
        "extra_duplicate_rows": len(duplicate_rows),
        "samples": samples[:8],
    }


def plan_sheet_duplicate_removals(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Gom dòng trùng (cùng ID hoặc cùng nội dung). Giữ dòng có số nhỏ nhất trong mỗi nhóm."""
    rows_data: Dict[int, Dict[str, Any]] = {}
    for q in questions:
        row = int(q.get("_row") or 0)
        if row:
            rows_data[row] = q
    if not rows_data:
        return {
            "rows_to_delete": [],
            "rows_to_keep": [],
            "duplicate_groups": 0,
            "delete_count": 0,
            "samples": [],
        }

    parent = {r: r for r in rows_data}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_id: Dict[str, int] = {}
    by_fp: Dict[str, int] = {}
    for row, q in rows_data.items():
        qid = clean(q.get("ID", ""))
        fp = question_content_fingerprint(q)
        if qid:
            prev_id = by_id.get(qid)
            if prev_id is not None:
                union(row, prev_id)
            else:
                by_id[qid] = row
        prev_fp = by_fp.get(fp)
        if prev_fp is not None:
            union(row, prev_fp)
        else:
            by_fp[fp] = row

    clusters: Dict[int, List[int]] = defaultdict(list)
    for r in rows_data:
        clusters[find(r)].append(r)

    rows_to_delete: List[int] = []
    rows_to_keep: List[int] = []
    samples: List[str] = []
    group_count = 0
    for _root, members in clusters.items():
        if len(members) < 2:
            continue
        group_count += 1
        members = sorted(members)
        keep = members[0]
        rows_to_keep.append(keep)
        rows_to_delete.extend(members[1:])
        qk = rows_data.get(keep, {})
        tip = clean(qk.get("CauHoi", ""))[:50]
        qid = clean(qk.get("ID", ""))
        samples.append(
            f"Giữ dòng {keep}"
            + (f" (ID {qid})" if qid else "")
            + f", xóa {', '.join(map(str, members[1:]))}"
            + (f" — {tip}…" if tip else "")
        )

    rows_to_delete = sorted(set(rows_to_delete), reverse=True)
    return {
        "rows_to_delete": rows_to_delete,
        "rows_to_keep": sorted(set(rows_to_keep)),
        "duplicate_groups": group_count,
        "delete_count": len(rows_to_delete),
        "samples": samples[:12],
    }


def dedupe_questions_by_row(qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Giữ một bản / dòng Sheet — tránh hiển thị lặp nếu dữ liệu Sheet bị trùng."""
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for q in qs:
        row = int(q.get("_row") or 0)
        if row:
            if row in seen:
                continue
            seen.add(row)
        out.append(q)
    return out


def extract_drive_file_id(value: Any) -> str:
    """Lấy FILE_ID từ link Google Drive hoặc chuỗi file id."""
    s = clean(value)
    if not s:
        return ""
    # =IMAGE("url") trong Google Sheet
    m = re.search(r'=\s*IMAGE\s*\(\s*["\']([^"\']+)["\']', s, flags=re.I)
    if m:
        s = m.group(1)
    # /file/d/FILE_ID/view
    m = re.search(r'/d/([A-Za-z0-9_-]{20,})', s)
    if m:
        return m.group(1)
    # open?id=FILE_ID hoặc uc?id=FILE_ID
    try:
        pr = urllib.parse.urlparse(s)
        qs = urllib.parse.parse_qs(pr.query)
        if qs.get('id') and qs['id'][0]:
            return qs['id'][0]
    except Exception:
        pass
    # Chuỗi file id thuần
    if re.fullmatch(r'[A-Za-z0-9_-]{20,}', s):
        return s
    return ""


def normalize_image_src(value: Any) -> str:
    """Chuẩn hóa cột hình ảnh để <img> hiện được ngay.
    - Link Drive dạng xem -> thumbnail public.
    - File ID Drive -> thumbnail public.
    - Link ảnh trực tiếp -> giữ nguyên.
    - Images/abc.png -> /static/Images/abc.png nếu repo có thư mục static.
    """
    s = clean(value)
    if not s:
        return ""
    m = re.search(r'=\s*IMAGE\s*\(\s*["\']([^"\']+)["\']', s, flags=re.I)
    if m:
        s = m.group(1).strip()
    fid = extract_drive_file_id(s)
    if fid:
        return f"https://drive.google.com/thumbnail?id={fid}&sz=w1600"
    if s.startswith('http://') or s.startswith('https://'):
        return s
    # Hỗ trợ ảnh local nếu thầy upload vào GitHub: static/Images/tenfile.png
    if s.startswith('/static/'):
        return s
    if s.lower().startswith('static/'):
        return '/' + s
    if s.lower().startswith('images/'):
        return '/static/' + s
    return s


def is_probably_link_or_drive(value: Any) -> bool:
    s = clean(value)
    return bool(s.startswith('http://') or s.startswith('https://') or extract_drive_file_id(s))

# ============================================================
# GOOGLE SHEET CLIENT + DATA STORE
# ============================================================

class SheetStore:
    def __init__(self):
        self.loaded_at = ""
        self.questions: List[Dict[str, Any]] = []
        self.catalog: List[Dict[str, Any]] = []
        self.by_made: Dict[str, List[Dict[str, Any]]] = {}
        self.by_group: Dict[str, List[Dict[str, Any]]] = {}
        self.by_id: Dict[str, List[Dict[str, Any]]] = {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.active_tokens: Dict[str, str] = {}
        self.quiz_sessions: Dict[str, Dict[str, Any]] = {}
        self.client = None
        self.sheet = None
        self.ws_questions = None
        self.ws_users = None
        self.ws_results = None
        self.ws_latex_rules = None
        self.question_headers: List[str] = []
        self.question_col_index: Dict[str, int] = {}
        # V8 FAST LOGIN:
        # Không nạp toàn bộ sheet Cau_Hoi ngay khi mở trang/login.
        # Login chỉ đọc nhanh sheet HOC_VIEN; dữ liệu đề chỉ nạp khi vào app hoặc ADMIN bấm đồng bộ.
        self.questions_loaded = False
        self.users_loaded = False
        # V9 SAFE LOADING:
        # Không để /api/meta chờ Google Sheet quá lâu rồi bị Render cắt kết nối.
        # Dữ liệu câu hỏi sẽ nạp nền; trang web hiển thị trạng thái và tự thử lại.
        self.questions_loading = False
        self.questions_error = ""
        self.load_lock = threading.Lock()
        self.add_question_lock = threading.Lock()
        self.duplicate_report: Dict[str, Any] = {}

    def connect(self):
        if self.sheet is not None:
            return
        if gspread is None or Credentials is None:
            raise RuntimeError("Thiếu thư viện gspread/google-auth. Hãy kiểm tra requirements.txt")
        sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
        creds_raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
        if not sheet_id or not creds_raw:
            raise RuntimeError("Thiếu GOOGLE_SHEET_ID hoặc GOOGLE_CREDENTIALS_JSON trên Render")
        try:
            info = json.loads(creds_raw)
        except json.JSONDecodeError as e:
            raise RuntimeError("GOOGLE_CREDENTIALS_JSON không phải JSON hợp lệ. Hãy dán toàn bộ file key JSON.") from e
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(sheet_id)

    def worksheet_or_none(self, name: str):
        try:
            return self.sheet.worksheet(name)
        except Exception:
            return None

    def ensure_users_loaded(self, force: bool = False):
        """Chỉ nạp sheet HOC_VIEN để đăng nhập nhanh, không đọc Cau_Hoi."""
        if self.users_loaded and self.users and not force:
            return
        self.connect()
        self.ws_users = self.worksheet_or_none("HOC_VIEN")
        self.load_users()
        self.users_loaded = True

    def ensure_questions_loaded(self, force: bool = False):
        """Nạp Cau_Hoi + catalog khi thật sự cần. Lần đầu có thể chậm, các lần sau dùng RAM."""
        if self.questions_loaded and self.questions and not force:
            return
        with self.load_lock:
            if self.questions_loaded and self.questions and not force:
                return
            self.questions_error = ""
            self.load()

    def start_questions_background(self, force: bool = False) -> None:
        """Khởi động nạp dữ liệu nền để tránh request /api/meta bị timeout trên Render Free."""
        if self.questions_loaded and self.questions and not force:
            return
        if self.questions_loading:
            return

        def worker():
            self.questions_loading = True
            self.questions_error = ""
            try:
                self.ensure_questions_loaded(force=force)
            except Exception as e:
                self.questions_error = str(e)
            finally:
                self.questions_loading = False

        threading.Thread(target=worker, daemon=True).start()

    def meta_light(self) -> Dict[str, Any]:
        """Trả về nhanh cho trang chủ. Nếu chưa nạp xong, không bắt trình duyệt chờ Google Sheet."""
        if not self.questions_loaded:
            self.start_questions_background(force=False)
            return {
                "version": APP_VERSION,
                "loaded_at": self.loaded_at,
                "loading": True,
                "loading_message": "Hệ thống đang khởi động và nạp dữ liệu từ Google Sheet. Nếu dùng Render Free, lần đầu truy cập sau khi app ngủ có thể chờ khoảng 10–40 giây. Trang sẽ tự thử lại, thầy/các em không cần đăng nhập lại.",
                "load_error": self.questions_error,
                "count_questions": len(self.questions),
                "count_catalog": len(self.catalog),
                "user": current_user_public(),
                "filters": {"Mon": [], "Lop": [], "Chuong": [], "BaiHoc": [], "BoDe": []},
                "catalog": [],
            }
        m = self.meta()
        m["loading"] = False
        m["load_error"] = self.questions_error
        return m

    def ensure_ws(self, name: str, headers: List[str]):
        self.connect()
        ws = self.worksheet_or_none(name)
        if ws is None:
            ws = self.sheet.add_worksheet(title=name, rows=1000, cols=max(10, len(headers)))
            ws.append_row(headers)
        values = ws.get_all_values()
        if not values:
            ws.append_row(headers)
        return ws

    def ensure_user_headers(self):
        """Bảo đảm sheet HOC_VIEN có đủ cột để đăng ký dùng thử."""
        self.connect()
        if self.ws_users is None:
            self.ws_users = self.ensure_ws("HOC_VIEN", USER_REQUIRED_HEADERS)
            return
        values = self.ws_users.get_all_values()
        if not values:
            self.ws_users.append_row(USER_REQUIRED_HEADERS)
            return
        headers = list(values[0])
        existing = {key_norm(h) for h in headers}
        changed = False
        for h in USER_REQUIRED_HEADERS:
            # Riêng LopHoc chấp nhận nếu đã có Lop/Lớp.
            if h == "LopHoc" and ("lop" in existing or "lop hoc" in existing):
                continue
            if key_norm(h) not in existing:
                headers.append(h)
                existing.add(key_norm(h))
                changed = True
        if changed:
            self.ws_users.update("1:1", [headers], value_input_option="USER_ENTERED")

    def user_header_value(self, header: str, values: Dict[str, Any]) -> str:
        """Đổ dữ liệu đăng ký vào đúng cột hiện có của sheet HOC_VIEN."""
        hn = key_norm(header)
        for canonical, names in {
            "MaHS": ALIASES["MaHS"],
            "HoTen": ALIASES["HoTen"],
            "Lop": ALIASES["Lop"],
            "LoaiTaiKhoan": ALIASES["LoaiTaiKhoan"],
            "TrangThai": ALIASES["TrangThai"],
            "SoDienThoai": ALIASES["SoDienThoai"],
            "DeviceId": ALIASES["DeviceId"],
            "MatKhau": ALIASES["MatKhau"],
            "NgayDangKy": ALIASES["NgayDangKy"],
            "NgayHetHanTrial": ALIASES["NgayHetHanTrial"],
            "NgayHetHanTaiKhoan": ALIASES["NgayHetHanTaiKhoan"],
        }.items():
            if hn in {key_norm(x) for x in names}:
                return clean(values.get(canonical, ""))
        return ""

    def load(self):
        self.connect()
        self.ws_questions = self.worksheet_or_none("Cau_Hoi")
        if self.ws_questions is None:
            raise RuntimeError("Không thấy sheet Cau_Hoi")
        self.ws_users = self.worksheet_or_none("HOC_VIEN")
        self.ws_results = self.ensure_ws("Ket_Qua", [
            "ThoiGian", "MaHS", "HoTen", "Lop", "LoaiTaiKhoan", "MaDe", "TenDe", "Diem", "SoDung", "TongCau", "ChiTiet"
        ])
        self.load_questions()
        self.load_users()
        self.questions_loaded = True
        self.users_loaded = True
        self.loaded_at = now_str()

    def load_questions(self):
        values = self.ws_questions.get_all_values()
        if not values:
            self.questions = []
            self.catalog = []
            self.by_made = {}
            return
        self.question_headers = values[0]
        self.question_col_index = resolve_question_col_index(self.question_headers)
        self.questions = []
        cols = self.question_col_index
        for idx, row_vals in enumerate(values[1:], start=2):
            raw = {self.question_headers[i]: row_vals[i] if i < len(row_vals) else "" for i in range(len(self.question_headers))}
            q = canonical_question(raw)

            # Nội dung / đáp án: đọc đúng cột theo tiêu đề (G=Dạng, I=Câu hỏi hoặc J=Dạng, K=Câu hỏi...).
            for field in ("CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo", "LoiGiai"):
                v = row_val(row_vals, cols.get(field))
                if not v:
                    continue
                if field in ("CauHoi", "A", "B", "C", "D", "LoiGiai"):
                    q[field] = normalize_latex_text(v)
                elif field == "DapAn" and any(x in v for x in ("$", "\\", "{", "}")):
                    q[field] = normalize_latex_text(v)
                else:
                    q[field] = v
            for f in ("CauHoi", "A", "B", "C", "D", "LoiGiai"):
                q[f] = normalize_latex_text(q.get(f, ""))

            # Cột T (index 19) hoặc cột HinhAnh theo header.
            t_col = cols.get("HinhAnh", 19 if len(self.question_headers) > 19 else None)
            if t_col is not None:
                t_img = row_val(row_vals, t_col)
                if is_probably_link_or_drive(t_img) or (t_img and not clean(q.get("HinhAnh"))):
                    q["HinhAnh"] = t_img

            u_col = cols.get("QuyenTruyCap", 20 if len(self.question_headers) > 20 else None)
            if u_col is not None and not clean(q.get("QuyenTruyCap")):
                q["QuyenTruyCap"] = row_val(row_vals, u_col)

            q["HinhAnh"] = normalize_image_src(q.get("HinhAnh"))

            # Mức độ + Dạng: ƯU TIÊN tiêu đề cột (G=Dạng hoặc J=Dạng), KHÔNG ghi đè bằng nội dung câu hỏi / đáp án A.
            md = row_val(row_vals, cols.get("MucDo"))
            if md:
                q["MucDo"] = md
            dang_raw = row_val(row_vals, cols.get("Dang"))
            if dang_raw:
                q["_DangCol"] = dang_raw
            elif clean(q.get("DangBaiTap", "")):
                q["_DangCol"] = clean(q.get("DangBaiTap", ""))
            elif clean(q.get("Dang", "")):
                q["_DangCol"] = clean(q.get("Dang", ""))

            q["Dang"] = effective_dang(q)

            if not clean(q.get("CauHoi")):
                continue
            q["_row"] = idx
            self.questions.append(q)
        self.duplicate_report = analyze_question_duplicates(self.questions)
        self.rebuild_question_indexes()

    def rebuild_question_indexes(self) -> None:
        for q in self.questions:
            q["Dang"] = effective_dang(q)
        self.by_made = {}
        self.by_group = {}
        self.by_id = {}
        for q in self.questions:
            self.by_made.setdefault(q.get("MaDe", ""), []).append(q)
            self.by_group.setdefault(catalog_group_key(q), []).append(q)
            qid = clean(q.get("ID", ""))
            if qid:
                self.by_id.setdefault(qid, []).append(q)
        self.catalog = self.build_catalog()

    def rebuild_indexes_after_admin_change(self):
        """Cập nhật lại by_made/catalog từ RAM, không đọc lại toàn bộ Google Sheet.
        Việc đọc lại toàn bộ Cau_Hoi sau mỗi lần lưu/xóa rất chậm trên Render Free
        và dễ làm trình duyệt báo Không đọc được phản hồi.
        """
        self.rebuild_question_indexes()
        self.loaded_at = now_str()

    def patch_quiz_sessions_after_row_delete(self, deleted_row: int) -> None:
        """Sau khi xóa dòng trên Sheet, cập nhật _row trong các phiên làm bài đang mở."""
        deleted_row = int(deleted_row)
        for ses in self.quiz_sessions.values():
            new_qs: List[Dict[str, Any]] = []
            for q in ses.get("questions", []):
                r = int(q.get("_row") or 0)
                if r == deleted_row:
                    continue
                if r > deleted_row:
                    q = dict(q)
                    q["_row"] = r - 1
                new_qs.append(q)
            ses["questions"] = new_qs

    def load_users(self):
        self.users = {}
        if self.ws_users is None:
            self.users["admin"] = {"mahs": "admin", "hoten": "ADMIN", "lop": "", "role": "ADMIN", "password": "admin123", "status": "ON"}
            return
        values = self.ws_users.get_all_values()
        if not values:
            self.users["admin"] = {"mahs": "admin", "hoten": "ADMIN", "lop": "", "role": "ADMIN", "password": "admin123", "status": "ON"}
            return
        headers = values[0]
        for row_vals in values[1:]:
            raw = {headers[i]: row_vals[i] if i < len(row_vals) else "" for i in range(len(headers))}
            mahs = get_field(raw, "MaHS")
            if not mahs:
                continue
            phone = re.sub(r"\D", "", get_field(raw, "SoDienThoai"))
            password = get_field(raw, "MatKhau") or (phone[-6:] if len(phone) >= 6 else "123456")
            role = norm_role(get_field(raw, "LoaiTaiKhoan"))
            status = (get_field(raw, "TrangThai") or "ON").upper()
            self.users[mahs] = {
                "mahs": mahs,
                "hoten": get_field(raw, "HoTen") or mahs,
                "lop": get_field(raw, "Lop"),
                "role": role,
                "password": password,
                "status": status,
                "phone": phone,
                "device_id": get_field(raw, "DeviceId"),
                "registered_at": get_field(raw, "NgayDangKy"),
                "trial_until": get_field(raw, "NgayHetHanTrial"),
                "account_until": get_field(raw, "NgayHetHanTaiKhoan"),
            }
        # Tài khoản dự phòng nếu sheet chưa có ADMIN.
        if not any(u.get("role") == "ADMIN" for u in self.users.values()):
            self.users["admin"] = {"mahs": "admin", "hoten": "ADMIN", "lop": "", "role": "ADMIN", "password": "admin123", "status": "ON"}

    def is_user_expired(self, user: Dict[str, Any]) -> Tuple[bool, str]:
        if user.get("role") == "ADMIN":
            return False, ""
        trial_until = user.get("trial_until", "")
        account_until = user.get("account_until", "")
        # Tài khoản có hạn chính thức thì kiểm tra ngày hết hạn tài khoản.
        if account_until and expired_datetime(account_until):
            return True, f"Tài khoản đã hết hạn ngày {account_until}."
        # Tài khoản dùng thử thì kiểm tra ngày hết hạn trial.
        if trial_until and expired_datetime(trial_until):
            return True, f"Tài khoản dùng thử đã hết hạn ngày {trial_until}."
        return False, ""

    def register_trial(self, hoten: str, lop: str, phone: str, password: str, device_id: str) -> Dict[str, Any]:
        self.ensure_user_headers()
        self.load_users()
        self.users_loaded = True
        phone_digits = re.sub(r"\D", "", phone or "")
        device_id = clean(device_id)
        if len(phone_digits) < 8:
            raise RuntimeError("Số điện thoại không hợp lệ. Vui lòng nhập ít nhất 8 chữ số.")
        if not clean(hoten):
            raise RuntimeError("Vui lòng nhập họ tên.")
        if not clean(password) or len(clean(password)) < 4:
            raise RuntimeError("Mật khẩu cần tối thiểu 4 ký tự.")
        # Chặn dùng lại số điện thoại hoặc thiết bị để lấy trial nhiều lần.
        for u in self.users.values():
            if u.get("phone") and u.get("phone") == phone_digits:
                raise RuntimeError("Số điện thoại này đã từng đăng ký. Vui lòng đăng nhập hoặc liên hệ giáo viên.")
            if device_id and u.get("device_id") and clean(u.get("device_id")) == device_id:
                raise RuntimeError("Thiết bị này đã từng đăng ký dùng thử. Vui lòng đăng nhập hoặc liên hệ giáo viên.")
        base = "TRIAL_" + stable_hash(phone_digits + device_id + str(time.time()), 8)
        mahs = base
        i = 1
        while mahs in self.users:
            i += 1
            mahs = f"{base}_{i}"
        now = datetime.now()
        until = now + timedelta(days=3)
        record = {
            "MaHS": mahs,
            "HoTen": clean(hoten),
            "Lop": clean(lop) or "Chưa khai báo",
            "LoaiTaiKhoan": "TRIAL",
            "TrangThai": "ON",
            "SoDienThoai": phone_digits,
            "NgayDangKy": fmt_datetime(now),
            "NgayHetHanTrial": fmt_datetime(until),
            "DeviceId": device_id,
            "NgayHetHanTaiKhoan": "",
            "MatKhau": clean(password),
        }
        headers = self.ws_users.get_all_values()[0]
        row = [self.user_header_value(h, record) for h in headers]
        self.ws_users.append_row(row, value_input_option="USER_ENTERED")
        self.load_users()
        self.users_loaded = True
        user = self.users.get(mahs)
        if not user:
            raise RuntimeError("Đã ghi tài khoản nhưng chưa nạp lại được dữ liệu HOC_VIEN.")
        return user

    def build_catalog(self) -> List[Dict[str, Any]]:
        groups: Dict[str, Dict[str, Any]] = {}
        for q in self.questions:
            gk = catalog_group_key(q)
            if gk not in groups:
                groups[gk] = {
                    "MaDe": gk,
                    "GroupKey": gk,
                    "Lop": q.get("Lop", ""), "Mon": q.get("Mon", ""), "Chuong": q.get("Chuong", ""),
                    "BaiHoc": q.get("BaiHoc", ""), "DangBaiTap": q.get("DangBaiTap", ""),
                    "BoDe": q.get("BoDe", ""), "De": q.get("De", ""),
                    "SoCau": 0, "MucDoSet": set(), "DangSet": set(), "QuyenTruyCapSet": set(),
                    "BoDeSet": set(), "DeSet": set(),
                    "DangCounts": {}, "LevelCounts": {}, "ComboCounts": {},
                    "SolFull": 0, "SolPartial": 0, "SolNone": 0,
                }
            g = groups[gk]
            g["SoCau"] += 1
            ed = question_dang(q)
            bump_count(g["DangCounts"], ed)
            for lv in question_mucdo_parts(q):
                bump_count(g["LevelCounts"], lv)
                bump_count(g["ComboCounts"], f"{lv}|{ed}")
            if q.get("MucDo"):
                g["MucDoSet"].add(q["MucDo"])
            if q.get("Dang"):
                g["DangSet"].add(ed)
            if q.get("BoDe"):
                g["BoDeSet"].add(q["BoDe"])
            if q.get("De"):
                g["DeSet"].add(q["De"])
            access = access_level_from_text(q.get("QuyenTruyCap", ""))
            g["QuyenTruyCapSet"].add(access)
            sol = question_solution_status(q)
            if sol == "full":
                g["SolFull"] += 1
            elif sol == "partial":
                g["SolPartial"] += 1
            else:
                g["SolNone"] += 1
        out: List[Dict[str, Any]] = []
        for g in groups.values():
            item = dict(g)
            item["MucDo"] = ", ".join(sorted(item.pop("MucDoSet"), key=key_norm))
            item["Dang"] = ", ".join(sorted(item.pop("DangSet"), key=key_norm))
            bode_set = item.pop("BoDeSet")
            de_set = item.pop("DeSet")
            if bode_set:
                item["BoDe"] = ", ".join(sorted(bode_set, key=key_norm))
            if de_set and not clean(item.get("BaiHoc")):
                item["De"] = ", ".join(sorted(de_set, key=key_norm))
            elif clean(item.get("BaiHoc")):
                item["De"] = clean(item.get("BaiHoc"))
            access_values = sorted(item.pop("QuyenTruyCapSet"), key=key_norm)
            item["QuyenTruyCap"] = "VIP" if "VIP" in access_values else "FREE"
            item["IsFree"] = item["QuyenTruyCap"] == "FREE"
            item["FilterCounts"] = {
                "dang": dict(item.pop("DangCounts")),
                "level": dict(item.pop("LevelCounts")),
                "combo": dict(item.pop("ComboCounts")),
            }
            out.append(item)
        out.sort(key=catalog_sort_key)
        return out

    def meta(self) -> Dict[str, Any]:
        def opts(field: str) -> List[str]:
            vals = list({clean(x.get(field, "")) for x in self.catalog if clean(x.get(field, ""))})
            return sort_field_values(field, vals)
        return {
            "version": APP_VERSION,
            "loaded_at": self.loaded_at,
            "count_questions": len(self.questions),
            "count_catalog": len(self.catalog),
            "user": current_user_public(),
            "filters": {"Mon": opts("Mon"), "Lop": opts("Lop"), "Chuong": opts("Chuong"), "BaiHoc": opts("BaiHoc"), "BoDe": opts("BoDe")},
            "catalog": self.catalog,
            "duplicate_report": self.duplicate_report if is_admin() else {},
        }

    def public_question(self, q: Dict[str, Any], index: int, reveal: bool = False) -> Dict[str, Any]:
        reveal = reveal or is_admin()
        d = {k: q.get(k, "") for k in ["ID", "MaDe", "Dang", "MucDo", "CauHoi", "A", "B", "C", "D", "HinhAnh", "Chuong", "BaiHoc", "De", "QuyenTruyCap"]}
        d["Dang"] = question_dang(q)
        d["HinhAnh"] = normalize_image_src(d.get("HinhAnh"))
        d["index"] = index
        d["sol_status"] = question_solution_status(q)
        d["has_full_solution"] = d["sol_status"] == "full"
        if reveal:
            d["DapAn"] = q.get("DapAn", "")
            d["LoiGiai"] = q.get("LoiGiai", "")
            d["SaiSo"] = q.get("SaiSo", "")
            d["_row"] = q.get("_row", "")
        return d

    def _lookup_match_item(self, q: Dict[str, Any]) -> Dict[str, Any]:
        made = clean(q.get("MaDe", ""))
        qs_in_de = self.resolve_quiz_base(made)
        idx = 0
        target_row = int(q.get("_row") or 0)
        target_id = clean(q.get("ID", ""))
        for i, x in enumerate(qs_in_de):
            if target_row and int(x.get("_row") or 0) == target_row:
                idx = i
                break
            if target_id and clean(x.get("ID", "")) == target_id:
                idx = i
                break
        preview = clean(q.get("CauHoi", ""))
        if len(preview) > 120:
            preview = preview[:117].rstrip() + "…"
        return {
            "ID": target_id,
            "MaDe": made,
            "row": target_row,
            "Mon": clean(q.get("Mon", "")),
            "Lop": clean(q.get("Lop", "")),
            "Chuong": clean(q.get("Chuong", "")),
            "BaiHoc": clean(q.get("BaiHoc", "")),
            "Dang": effective_dang(q),
            "MucDo": clean(q.get("MucDo", "")),
            "index_in_de": idx,
            "question_no": idx + 1,
            "QuyenTruyCap": clean(q.get("QuyenTruyCap", "VIP")) or "VIP",
            "preview": preview,
        }

    def lookup_questions_by_id(self, qid: str) -> Dict[str, Any]:
        """Tra cứu câu theo ID (cột A) — hỗ trợ khớp một phần."""
        self.ensure_questions_loaded()
        qid = clean(qid)
        if not qid:
            return {"id": "", "matches": [], "count": 0}
        hits: List[Dict[str, Any]] = []
        seen_rows: set = set()
        for q in self.by_id.get(qid, []):
            row = int(q.get("_row") or 0)
            if row in seen_rows:
                continue
            seen_rows.add(row)
            hits.append(self._lookup_match_item(q))
        if not hits:
            u = qid.upper()
            for kid, qs in self.by_id.items():
                if u not in kid.upper():
                    continue
                for q in qs:
                    row = int(q.get("_row") or 0)
                    if row in seen_rows:
                        continue
                    seen_rows.add(row)
                    hits.append(self._lookup_match_item(q))
                if len(hits) >= 25:
                    break
        return {"id": qid, "matches": hits[:25], "count": len(hits[:25])}

    def resolve_quiz_base(self, made: str) -> List[Dict[str, Any]]:
        made = clean(made)
        if made.startswith("GRP_"):
            qs = list(self.by_group.get(made, []))
            if qs:
                return dedupe_questions_by_row(qs)
        qs = list(self.by_made.get(made, []))
        if qs:
            return dedupe_questions_by_row(qs)
        for item in self.catalog:
            if item.get("MaDe") == made or item.get("GroupKey") == made:
                gk = clean(item.get("GroupKey") or item.get("MaDe"))
                if gk.startswith("GRP_"):
                    return dedupe_questions_by_row(list(self.by_group.get(gk, [])))
                return dedupe_questions_by_row(list(self.by_made.get(gk, [])))
        return []

    def catalog_filter_count(self, made: str, level_filter: str = "", dang_filter: str = "") -> Optional[int]:
        item = next((x for x in self.catalog if x.get("MaDe") == made or x.get("GroupKey") == made), None)
        if not item:
            return None
        fc = item.get("FilterCounts") or {}
        lv = clean(level_filter).upper()
        dg = norm_dang(dang_filter) if clean(dang_filter) else ""
        if lv and dg:
            combo = fc.get("combo") or {}
            return int(combo.get(f"{lv}|{dg}", combo.get(f"{lv}|{dang_filter}", 0)) or 0)
        if dg:
            dang = fc.get("dang") or {}
            return int(dang.get(dg, dang.get(dang_filter, 0)) or 0)
        if lv:
            return int((fc.get("level") or {}).get(lv, 0) or 0)
        return None

    def start_quiz(
        self,
        made: str,
        shuffle_questions: bool = False,
        shuffle_options: bool = False,
        level_filter: str = "",
        dang_filter: str = "",
        group_by_dang: bool = True,
    ) -> Dict[str, Any]:
        base_qs = self.resolve_quiz_base(made)
        if not base_qs:
            raise RuntimeError("Không có câu hỏi trong đề này. Có thể mã đề bị lệch, hãy bấm Đồng bộ dữ liệu.")
        total_in_de = len(base_qs)
        level_filter = clean(level_filter).upper()
        qs_source = base_qs
        if level_filter:
            def has_level(q: Dict[str, Any]) -> bool:
                return level_filter in question_mucdo_parts(q) or level_filter in clean(q.get("MucDo", "")).upper()
            qs_source = [q for q in base_qs if has_level(q)]
            if not qs_source:
                raise RuntimeError(f"Đề này không có câu mức độ {level_filter}. Thầy chọn mức khác hoặc để Tất cả.")
        dang_filter = norm_dang(dang_filter) if clean(dang_filter) else ""
        if dang_filter:
            dang_norm = dang_filter
            after_level = qs_source
            qs_source = [q for q in qs_source if dang_matches(q, dang_norm)]
            if not qs_source:
                n_dang_all = sum(1 for q in base_qs if dang_matches(q, dang_norm))
                cat_n = self.catalog_filter_count(made, level_filter, dang_norm)
                hint = f" Mục lục báo {cat_n} câu — bấm Đồng bộ Sheet, Ctrl+F5." if cat_n else ""
                if level_filter:
                    n_level_all = len(after_level)
                    raise RuntimeError(
                        f"Không có câu mức {level_filter} dạng {dang_filter}. "
                        f"Đề có {n_dang_all} câu {dang_filter} (mức khác) và {n_level_all} câu mức {level_filter} (dạng khác). "
                        f"Thử bỏ một bộ lọc hoặc chọn Tất cả.{hint}"
                    )
                raise RuntimeError(
                    f"Không có câu dạng {dang_filter} trong đề này "
                    f"(đề có {total_in_de} câu, trong đó {n_dang_all} câu {dang_filter}).{hint}"
                )
        access_level = quiz_access_level(qs_source)
        if is_trial() and access_level != "FREE":
            raise RuntimeError("Tài khoản dùng thử chỉ mở được đề FREE, không mở được đề VIP.")
        qs = prepare_quiz_questions(
            qs_source,
            shuffle_questions=shuffle_questions,
            shuffle_options=shuffle_options,
            group_by_dang=group_by_dang,
        )
        sid = stable_hash(f"{session.get('mahs')}|{made}|{time.time()}|{random.random()}", 18)
        self.quiz_sessions[sid] = {
            "made": made,
            "mahs": session.get("mahs"),
            "created": time.time(),
            "questions": qs,
            "used_5050": set(),
            "access_level": access_level,
            "level_filter": level_filter,
            "dang_filter": dang_filter,
            "shuffle_questions": shuffle_questions,
            "shuffle_options": shuffle_options,
            "group_by_dang": group_by_dang,
            "random_practice": made.startswith("__RANDOM__"),
        }
        reveal = is_admin() or can_view_solution_live()
        return {
            "sid": sid,
            "admin": is_admin(),
            "is_trial": is_trial(),
            "can_view_solution_live": can_view_solution_live(),
            "access_level": access_level,
            "can_5050": can_use_5050(),
            "can_submit_score": not is_trial(),
            "shuffle_questions": shuffle_questions,
            "shuffle_options": shuffle_options,
            "group_by_dang": group_by_dang,
            "random_practice": made.startswith("__RANDOM__"),
            "level_filter": level_filter,
            "dang_filter": dang_filter,
            "question_count": len(qs),
            "total_in_de": total_in_de,
            "trial_message": "Tài khoản dùng thử: chỉ luyện đề FREE, không nộp/chấm điểm và không xem đáp án/lời giải." if is_trial() else "",
            "questions": [self.public_question(q, i, reveal=reveal) for i, q in enumerate(qs)]
        }

    def start_random_practice(
        self,
        mon: str = "",
        khoi: str = "",
        lop: str = "",
        chuongs: Optional[List[str]] = None,
        chuong: str = "",
        baihoc: str = "",
        bode: str = "",
        level_filter: str = "",
        sol_full_only: bool = False,
        shuffle_options: bool = True,
    ) -> Dict[str, Any]:
        """Tạo đề tự luyện ngẫu nhiên: 18 TN + 4 Đ/S + 6 TLN trong phạm vi Môn/Khối/Lớp/Chương."""
        mon = clean(mon)
        khoi = clean(khoi)
        lop = clean(lop)
        if not mon or not khoi or not lop:
            raise RuntimeError("Phải chọn đủ Môn, Khối và Lớp trước khi tự luyện ngẫu nhiên.")
        ch_list = [clean(c) for c in (chuongs or []) if clean(c)]
        pool = [
            q for q in self.questions
            if question_matches_pool_filter(
                q,
                mon=mon,
                khoi=khoi,
                lop=lop,
                chuongs=ch_list,
                chuong=clean(chuong),
                baihoc=clean(baihoc),
                bode=clean(bode),
                level=clean(level_filter).upper(),
                sol_full_only=sol_full_only,
            )
        ]
        if not pool:
            ch_hint = f" ({len(ch_list)} chương đã chọn)" if ch_list else " (tất cả chương)"
            raise RuntimeError(
                f"Không có câu nào trong phạm vi {mon} · Khối {khoi} · Lớp {lop}{ch_hint}."
                + (" Thử bỏ «Chỉ LG đầy đủ» hoặc chọn thêm chương." if sol_full_only else " Thử chọn thêm chương hoặc mở rộng phạm vi.")
            )
        by_dang: Dict[str, List[Dict[str, Any]]] = {}
        for q in pool:
            by_dang.setdefault(question_dang(q), []).append(q)
        picked: List[Dict[str, Any]] = []
        shortages: List[str] = []
        for dang, need in RANDOM_PRACTICE_SPEC:
            avail = list(by_dang.get(dang, []))
            if len(avail) < need:
                shortages.append(f"{dang}: cần {need}, có {len(avail)}")
                if avail:
                    picked.extend(random.sample(avail, len(avail)))
            else:
                picked.extend(random.sample(avail, need))
        if len(picked) < 8:
            raise RuntimeError(
                "Không đủ câu để ghép đề ngẫu nhiên.\n"
                + "\n".join(shortages)
                + "\n\nHãy mở rộng bộ lọc (Chương/Bài học) hoặc bỏ «Chỉ câu LG đầy đủ»."
            )
        made = "__RANDOM__" + stable_hash(
            f"{session.get('mahs')}|{mon}|{khoi}|{lop}|{'|'.join(ch_list)}|{time.time()}|{random.random()}",
            12,
        )
        qs = prepare_quiz_questions(
            picked,
            shuffle_questions=False,
            shuffle_options=shuffle_options,
            group_by_dang=True,
        )
        access_level = quiz_access_level(qs)
        sid = stable_hash(f"{session.get('mahs')}|{made}|{time.time()}|{random.random()}", 18)
        self.quiz_sessions[sid] = {
            "made": made,
            "mahs": session.get("mahs"),
            "created": time.time(),
            "questions": qs,
            "used_5050": set(),
            "access_level": access_level,
            "level_filter": clean(level_filter).upper(),
            "dang_filter": "",
            "shuffle_questions": False,
            "shuffle_options": shuffle_options,
            "group_by_dang": True,
            "random_practice": True,
        }
        reveal = is_admin() or can_view_solution_live()
        title_parts = [p for p in [mon, f"Khối {khoi}" if khoi else "", f"Lớp {lop}" if lop else ""] if p]
        if ch_list:
            title_parts.append(f"{len(ch_list)} chương")
        elif clean(chuong):
            title_parts.append(clean(chuong))
        return {
            "sid": sid,
            "made": made,
            "admin": is_admin(),
            "is_trial": is_trial(),
            "can_view_solution_live": can_view_solution_live(),
            "access_level": access_level,
            "can_5050": can_use_5050(),
            "can_submit_score": not is_trial(),
            "shuffle_questions": False,
            "shuffle_options": shuffle_options,
            "group_by_dang": True,
            "random_practice": True,
            "level_filter": clean(level_filter).upper(),
            "dang_filter": "",
            "question_count": len(qs),
            "total_in_de": len(pool),
            "random_shortages": shortages,
            "random_title": " · ".join(title_parts) if title_parts else "Tự luyện ngẫu nhiên",
            "trial_message": "Tài khoản dùng thử: chỉ luyện đề FREE, không nộp/chấm điểm và không xem đáp án/lời giải." if is_trial() else "",
            "questions": [self.public_question(q, i, reveal=reveal) for i, q in enumerate(qs)],
        }

    def restore_quiz_session(self, sid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Khôi phục phiên làm bài từ dữ liệu trình duyệt khi Render restart / mất RAM."""
        sid = clean(sid)
        if not sid:
            raise RuntimeError("Phiên làm bài không hợp lệ.")
        mahs = session.get("mahs")
        raw_qs = payload.get("questions") or []
        if not isinstance(raw_qs, list) or not raw_qs:
            raise RuntimeError("Không khôi phục được phiên làm bài (thiếu danh sách câu).")
        qs = [client_question_to_internal(q) for q in raw_qs[:300]]
        qs = [q for q in qs if clean(q.get("CauHoi"))]
        if not qs:
            raise RuntimeError("Không khôi phục được phiên làm bài (dữ liệu câu rỗng).")
        ses = {
            "made": clean(payload.get("made", "")),
            "mahs": mahs,
            "created": time.time(),
            "questions": qs,
            "used_5050": set(),
            "access_level": quiz_access_level(qs),
            "level_filter": clean(payload.get("level_filter", "")).upper(),
            "dang_filter": clean(payload.get("dang_filter", "")),
            "shuffle_questions": False,
            "shuffle_options": False,
            "restored": True,
        }
        self.quiz_sessions[sid] = ses
        return ses

    def check_quiz_session(
        self, sid: str, restore_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        sid = clean(sid)
        if not sid:
            raise RuntimeError("Phiên làm bài không hợp lệ.")
        ses = self.quiz_sessions.get(sid)
        if not ses and restore_payload and restore_payload.get("questions"):
            ses = self.restore_quiz_session(sid, restore_payload)
        if not ses:
            raise RuntimeError(
                "Phiên làm bài đã hết hạn (server vừa khởi động lại). "
                "Bấm lại Gợi ý AI — app sẽ tự khôi phục, hoặc ← Về mục lục → mở lại đề."
            )
        if ses.get("mahs") != session.get("mahs"):
            raise RuntimeError("Phiên làm bài không thuộc tài khoản hiện tại")
        return ses

    def fifty_fifty(
        self, sid: str, index: int, restore_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not can_use_5050():
            raise RuntimeError("Tài khoản này chưa được dùng Loại 2 câu sai")
        ses = self.check_quiz_session(sid, restore_payload)
        if index in ses["used_5050"]:
            return {"hide": [], "message": "Câu này đã dùng Loại 2 câu sai rồi."}
        qs = ses["questions"]
        if not (0 <= index < len(qs)):
            raise RuntimeError("Số câu không hợp lệ")
        q = qs[index]
        if norm_dang(q.get("Dang")) != "Trắc nghiệm":
            return {"hide": [], "message": "Chỉ dùng được cho câu trắc nghiệm A-B-C-D."}
        correct = norm_letter(q.get("DapAn"))
        letters = [x for x in "ABCD" if clean(q.get(x))]
        wrongs = [x for x in letters if x != correct]
        random.shuffle(wrongs)
        ses["used_5050"].add(index)
        return {"hide": wrongs[:2], "message": "Đã loại 2 câu sai."}

    def check_one(
        self, sid: str, index: int, answer: Any, restore_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Chấm nhanh 1 câu để tô màu đúng/sai ngay khi chọn."""
        ses = self.check_quiz_session(sid, restore_payload)
        qs = ses["questions"]
        if not (0 <= index < len(qs)):
            raise RuntimeError("Số câu không hợp lệ")
        q = qs[index]
        ok, correct, chosen = check_answer(q, answer)
        out = {
            "index": index,
            "ID": q.get("ID"),
            "Dang": q.get("Dang"),
            "ok": ok,
            "correct": correct,
            "chosen": chosen,
        }
        if effective_dang(q) == "Đúng sai":
            out["rows"] = dungsai_rows_detail(q, answer)
            out["correct_display"] = format_tf_answer_display(q)
        if can_view_solution_live():
            out["LoiGiai"] = clean(q.get("LoiGiai", ""))
            out["DapAn"] = clean(q.get("DapAn", ""))
        return out

    def hint_one(
        self, sid: str, index: int, answer: Any, restore_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not can_use_ai_hint():
            raise RuntimeError("Gợi ý AI chỉ dành tài khoản VIP / SVIP / ADMIN.")
        ses = self.check_quiz_session(sid, restore_payload)
        qs = ses["questions"]
        if not (0 <= index < len(qs)):
            raise RuntimeError("Số câu không hợp lệ")
        q = qs[index]
        cfg = ai_runtime_config()
        has_keys = bool(cfg.get("has_keys"))
        ok_sheet, correct_sheet, chosen_sheet = check_answer(q, answer)
        sheet_dapan = clean(q.get("DapAn", ""))
        sheet_loigiai = clean(q.get("LoiGiai", ""))

        def _admin_sheet_footer() -> str:
            p = sheet_dapan or "(trống)"
            r = "(có nội dung)" if sheet_loigiai else "(trống)"
            return f"\n\n📋 Tham chiếu Sheet — cột P: {p} | cột R: {r}"

        # ADMIN: AI giải đầy đủ + đối chiếu đáp án/lời giải Sheet
        if is_admin():
            if has_keys:
                hint_text, key_index, provider_used, ai_error = ai_hint_from_provider(
                    q, answer, admin_review=True
                )
                if provider_used != "FALLBACK":
                    return _admin_hint_payload(
                        index,
                        hint_text + _admin_sheet_footer(),
                        correct_sheet,
                        sheet_dapan,
                        sheet_loigiai,
                        q=q,
                        key_index=key_index,
                        provider_used=provider_used,
                        ai_configured=True,
                        provider_mode=cfg.get("provider", "AUTO"),
                        ai_error="",
                    )
                err_hint = f"AI lỗi: {ai_error or 'không phản hồi'}.{ _admin_sheet_footer()}"
                if correct_sheet:
                    err_hint += f"\n\nĐáp án Sheet (cột P): {correct_sheet}"
                if sheet_loigiai:
                    err_hint += f"\n\nLời giải Sheet (cột R):\n{sheet_loigiai[:8000]}"
                return _admin_hint_payload(
                    index,
                    err_hint,
                    correct_sheet,
                    sheet_dapan,
                    sheet_loigiai,
                        q=q,
                    key_index=0,
                    provider_used="FALLBACK",
                    ai_configured=True,
                    provider_mode=cfg.get("provider", "AUTO"),
                    ai_error=ai_error,
                )
            no_key = (
                "Chưa có GEMINI_API_KEY trên Render — chưa gọi được AI kiểm tra.\n\n"
                f"Sheet cột P (đáp án): {sheet_dapan or '(trống)'}\n"
                f"Sheet cột R (lời giải): {sheet_loigiai or '(trống)'}"
            )
            return _admin_hint_payload(
                index,
                no_key,
                correct_sheet,
                sheet_dapan,
                sheet_loigiai,
                        q=q,
                ai_configured=False,
                provider_mode=cfg.get("provider", "AUTO"),
            )

        # VIP / SVIP: phương hướng ngắn + kết quả cuối (không giải từng phương án)
        def _vip_detailed_hint_response(
            hint_text: str,
            key_index: int,
            provider_used: str,
            ai_error: str,
            ai_configured: bool,
        ) -> Dict[str, Any]:
            body = sanitize_hint_math_text(hint_text) or sanitize_hint_math_text(
                ai_hint_fallback(q, answer)
            )
            sug = parse_vip_ai_suggestions(body)
            if not sug.get("suggested_dapan") and correct_sheet:
                sug["suggested_dapan"] = correct_sheet
            note = "\n\n💎 VIP/SVIP: phương hướng làm bài + kết quả cuối (không giải từng A/B/C/D)."
            hide_5050: List[str] = []
            if can_use_5050() and effective_dang(q) == "Trắc nghiệm":
                try:
                    ff = self.fifty_fifty(sid, index, restore_payload)
                    hide_5050 = list(ff.get("hide") or [])
                    if hide_5050:
                        note += (
                            f"\n\n🎯 Luyện tập: đã tự loại 2 đáp án sai "
                            f"({', '.join(hide_5050)})."
                        )
                except Exception:
                    pass
            if provider_used == "FALLBACK" and ai_error:
                note += f"\n\n⚠️ AI tạm lỗi: {ai_error[:160]}. Đang hiển thị gợi ý cơ bản."
            elif not ai_configured:
                note += (
                    "\n\n⚠️ Chưa có key AI — gợi ý cơ bản. "
                    "VIP: vào mục lục → 🔑 Key AI của tôi → dán key AIza... (Google AI Studio) → Lưu key."
                )
            body_main = body.split("💎")[0].strip()
            if body_main and not _vip_hint_complete(body_main):
                note += "\n\n⚠️ AI có thể chưa đủ 2 bước — bấm lại Gợi ý AI."
            return {
                "index": index,
                "exact": True,
                "show_answer": True,
                "vip_detailed": True,
                "hint": body + note,
                "hint_truncated": not _vip_hint_complete(body_main),
                "suggested_dapan": sug.get("suggested_dapan", ""),
                "suggested_loigiai": sug.get("suggested_huong", ""),
                "sheet_dapan": sheet_dapan,
                "sheet_loigiai": sheet_loigiai[:2000] if sheet_loigiai else "",
                "hide_5050": hide_5050,
                "correct": correct_sheet,
                "key_index": key_index,
                "provider_used": provider_used,
                "ai_configured": ai_configured,
                "provider_mode": cfg.get("provider", "AUTO"),
                "ai_error": ai_error,
            }

        if has_keys:
            hint_text, key_index, provider_used, ai_error = ai_hint_from_provider(
                q, answer, vip_short=True
            )
            if provider_used != "FALLBACK":
                return _vip_detailed_hint_response(
                    hint_text, key_index, provider_used, ai_error, True
                )
        fb = ai_hint_fallback(q, answer)
        return _vip_detailed_hint_response(fb, 0, "FALLBACK", "", bool(has_keys))

    def similar_one(
        self, sid: str, index: int, restore_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not can_use_ai_hint():
            raise RuntimeError("Tạo câu tương tự chỉ dành tài khoản VIP / SVIP / ADMIN.")
        ses = self.check_quiz_session(sid, restore_payload)
        qs = ses["questions"]
        if not (0 <= index < len(qs)):
            raise RuntimeError("Số câu không hợp lệ")
        q = qs[index]
        cfg = ai_runtime_config()
        has_keys = bool(cfg.get("has_keys"))
        text, key_index, provider_used, ai_error = ai_similar_question_from_provider(q)
        body = sanitize_hint_math_text(text) or (
            "Chưa tạo được câu tương tự — thử lại sau hoặc kiểm tra key AI."
        )
        return {
            "index": index,
            "similar": body,
            "key_index": key_index,
            "provider_used": provider_used,
            "ai_configured": has_keys,
            "provider_mode": cfg.get("provider", "AUTO"),
            "ai_error": ai_error,
        }

    def infographic_prompt_one(
        self,
        sid: str,
        index: int,
        answer: Any = None,
        restore_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not can_use_infographic():
            raise RuntimeError("Infographic chỉ dành tài khoản VIP / SVIP / ADMIN.")
        ses = self.check_quiz_session(sid, restore_payload)
        qs = ses["questions"]
        if not (0 <= index < len(qs)):
            raise RuntimeError("Số câu không hợp lệ")
        q = qs[index]
        if not is_admin():
            ok, _, _ = check_answer(q, answer)
            if not ok:
                raise RuntimeError("Phải trả lời đúng câu này mới mở khóa infographic.")
        prompt = build_gemini_infographic_prompt(q)
        dang = effective_dang(q)
        spec = _infographic_dang_spec(dang)
        warnings = _infographic_completeness_warnings(q)
        return {
            "index": index,
            "id": clean(q.get("ID", "")),
            "prompt": prompt,
            "has_image": bool(clean(q.get("HinhAnh", ""))),
            "mucdo": infographic_mucdo_label(q),
            "dang": dang,
            "dang_code": spec.get("code", ""),
            "dang_title": spec.get("title", ""),
            "warnings": warnings,
        }

    def submit(
        self, sid: str, answers: Dict[str, Any], restore_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if is_trial():
            raise RuntimeError("Tài khoản dùng thử không được nộp/chấm điểm. Thầy chỉ cho luyện thử các đề FREE trong 3 ngày.")
        ses = self.check_quiz_session(sid, restore_payload)
        qs = ses["questions"]
        results = []
        correct_count = 0
        auto_count = 0
        reveal = can_view_solution_after_submit() or is_admin()
        for i, q in enumerate(qs):
            ans = answers.get(str(i), "")
            ok, correct, chosen = check_answer(q, ans)
            if norm_dang(q.get("Dang")) != "Tự luận":
                auto_count += 1
                if ok:
                    correct_count += 1
            r = {"index": i, "ID": q.get("ID"), "Dang": q.get("Dang"), "ok": ok, "correct": correct, "chosen": chosen}
            if effective_dang(q) == "Đúng sai":
                r["rows"] = dungsai_rows_detail(q, ans)
                r["correct_display"] = format_tf_answer_display(q)
            if reveal:
                r.update({"DapAn": q.get("DapAn", ""), "LoiGiai": q.get("LoiGiai", "")})
            results.append(r)
        score = round(10 * correct_count / auto_count, 2) if auto_count else 0
        self.save_result(ses.get("made"), qs, score, correct_count, auto_count, results, ses.get("level_filter", ""))
        return {"score": score, "correct_count": correct_count, "auto_count": auto_count, "total": len(qs), "show_solution": reveal, "results": results}

    def save_result(self, made: str, qs: List[Dict[str, Any]], score: float, so_dung: int, tong: int, results: List[Dict[str, Any]], level_filter: str = ""):
        try:
            u = current_user_public()
            ten_de = qs[0].get("De") or qs[0].get("BaiHoc") or made if qs else made
            so_sai = max(0, int(tong or 0) - int(so_dung or 0))
            detail = {
                "level_filter": clean(level_filter).upper(),
                "so_dung": int(so_dung or 0),
                "so_sai": so_sai,
                "tong_cau_cham_tu_dong": int(tong or 0),
                "results": results,
            }
            self.ws_results.append_row([
                now_str(), u.get("mahs"), u.get("hoten"), u.get("lop"), u.get("role"), made, ten_de, score, so_dung, tong,
                json.dumps(detail, ensure_ascii=False)
            ], value_input_option="USER_ENTERED")
        except Exception:
            pass

    def update_question(self, row_number: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """ADMIN sửa câu hỏi.

        Bản này ưu tiên ghi theo đúng bố cục Google Sheet của thầy để không bị lỗi
        do tiêu đề cột khác nhau:
        I: MucDo, J: Dang, K: CauHoi/NoiDung, L: A, M: B, N: C, O: D,
        P: DapAn, Q: SaiSo, R: LoiGiai, T: HinhAnh.
        Nếu sau này đổi cấu trúc, app vẫn thử dùng header map làm phương án phụ.
        """
        if not is_admin():
            raise RuntimeError("Chỉ ADMIN được sửa câu hỏi")
        if row_number < 2:
            raise RuntimeError("Dòng Google Sheet không hợp lệ")

        # 1-indexed column numbers theo Google Sheet thực tế.
        fixed_col = SHEET_QUESTION_FIXED_COL_1

        batch = []
        updated_fields = []
        for field, value in updates.items():
            if field not in EDITABLE_FIELDS:
                continue

            col = fixed_col.get(field)

            # Phương án phụ: nếu field không có trong fixed_col thì thử theo header.
            if col is None:
                col0 = self.question_col_index.get(field)
                if col0 is not None:
                    col = col0 + 1

            if col is None:
                continue

            a1 = gspread.utils.rowcol_to_a1(row_number, col)
            batch.append({"range": a1, "values": [[clean(value)]]})
            updated_fields.append(f"{field}->{a1}")

        if not batch:
            raise RuntimeError("Không có cột nào phù hợp để cập nhật. Kiểm tra cấu trúc sheet Cau_Hoi.")

        self.ws_questions.batch_update(batch, value_input_option="USER_ENTERED")

        # Cập nhật ngay trong RAM để tránh đọc lại cả Google Sheet sau khi lưu.
        for q in self.questions:
            if int(q.get("_row") or 0) == int(row_number):
                for field, value in updates.items():
                    if field in EDITABLE_FIELDS:
                        q[field] = clean(value)
                q["HinhAnh"] = normalize_image_src(q.get("HinhAnh"))
                q["Dang"] = effective_dang(q)
                break
        self.rebuild_indexes_after_admin_change()
        return {"ok": True, "updated": len(batch), "row": row_number, "fields": updated_fields}

    def delete_question(self, row_number: int, question_id: str = "") -> Dict[str, Any]:
        """ADMIN xóa nguyên dòng câu hỏi khỏi sheet Cau_Hoi — cập nhật RAM, không đọc lại cả Sheet."""
        if not is_admin():
            raise RuntimeError("Chỉ ADMIN được xóa câu hỏi")
        if row_number < 2:
            raise RuntimeError("Dòng Google Sheet không hợp lệ")

        # Kiểm tra ID trước khi xóa để tránh xóa nhầm khi sheet vừa bị sắp xếp/dồn dòng.
        actual_id = clean(self.ws_questions.acell(f"A{row_number}").value)
        question_id = clean(question_id)
        if question_id and actual_id and actual_id != question_id:
            raise RuntimeError(f"Không xóa để tránh nhầm dòng: ID ở app là {question_id}, nhưng A{row_number} trên Google Sheet là {actual_id}. Hãy bấm Đồng bộ Sheet rồi thử lại.")

        # Xóa nguyên dòng. Các dòng dưới sẽ tự dồn lên trong Google Sheet.
        self.ws_questions.delete_rows(row_number)
        self._purge_question_row_in_memory(row_number)
        self.rebuild_indexes_after_admin_change()
        return {"ok": True, "deleted": True, "row": row_number, "id": actual_id or question_id}

    def _purge_question_row_in_memory(self, row_number: int) -> None:
        """Bỏ câu khỏi RAM và giảm _row các dòng phía dưới sau khi xóa trên Sheet."""
        self._purge_question_rows_in_memory([row_number])

    def _purge_question_rows_in_memory(self, row_numbers: List[int]) -> None:
        """Bỏ nhiều dòng khỏi RAM và cập nhật _row sau khi xóa hàng loạt trên Sheet."""
        to_del = sorted({int(r) for r in row_numbers if int(r) > 0})
        if not to_del:
            return
        to_del_set = set(to_del)
        new_questions: List[Dict[str, Any]] = []
        for q in self.questions:
            r = int(q.get("_row") or 0)
            if r in to_del_set:
                continue
            shift = sum(1 for d in to_del if d < r)
            if shift:
                q = dict(q)
                q["_row"] = r - shift
            new_questions.append(q)
        self.questions = new_questions
        for ses in self.quiz_sessions.values():
            new_qs: List[Dict[str, Any]] = []
            for q in ses.get("questions", []):
                r = int(q.get("_row") or 0)
                if r in to_del_set:
                    continue
                shift = sum(1 for d in to_del if d < r)
                if shift:
                    q = dict(q)
                    q["_row"] = r - shift
                new_qs.append(q)
            ses["questions"] = new_qs

    def _batch_delete_question_rows(self, row_numbers: List[int]) -> None:
        """Xóa nhiều dòng Sheet trong ít request nhất (tránh quota 429). Không dùng AI."""
        rows = sorted({int(r) for r in row_numbers if int(r) > 0}, reverse=True)
        if not rows:
            return
        self.connect()
        ws = self.ws_questions
        sheet_id = ws.id
        chunk_size = 120
        for off in range(0, len(rows), chunk_size):
            chunk = rows[off : off + chunk_size]
            body = {
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": row - 1,
                                "endIndex": row,
                            }
                        }
                    }
                    for row in chunk
                ]
            }
            last_err: Optional[Exception] = None
            for attempt in range(4):
                try:
                    ws.spreadsheet.batch_update(body)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    msg = str(e).lower()
                    if "429" in msg or "quota" in msg or "rate" in msg:
                        time.sleep(8 + attempt * 12)
                        continue
                    raise
            if last_err is not None:
                raise RuntimeError(
                    "Google Sheet giới hạn ghi (429) — xóa trùng không dùng AI, chỉ gọi API Sheet. "
                    "Đợi ~1 phút rồi thử lại."
                ) from last_err
            if off + chunk_size < len(rows):
                time.sleep(1.2)

    def remove_duplicate_questions(self, dry_run: bool = False) -> Dict[str, Any]:
        """ADMIN xóa các dòng trùng trên Cau_Hoi — giữ bản đầu tiên (số dòng nhỏ nhất)."""
        if not is_admin():
            raise RuntimeError("Chỉ ADMIN được xóa câu trùng")
        plan = plan_sheet_duplicate_removals(self.questions)
        to_delete: List[int] = plan["rows_to_delete"]
        if not to_delete:
            return {
                "ok": True,
                "dry_run": dry_run,
                "deleted": 0,
                "message": "Không có dòng trùng cần xóa.",
                "plan": plan,
                "duplicate_report": self.duplicate_report,
            }
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "would_delete": len(to_delete),
                "message": f"Sẽ xóa {len(to_delete)} dòng trùng (giữ {len(plan['rows_to_keep'])} bản).",
                "plan": plan,
            }

        with self.add_question_lock:
            self._batch_delete_question_rows(to_delete)
            self._purge_question_rows_in_memory(to_delete)

        self.duplicate_report = analyze_question_duplicates(self.questions)
        self.rebuild_indexes_after_admin_change()
        return {
            "ok": True,
            "dry_run": False,
            "deleted": len(to_delete),
            "message": f"Đã xóa {len(to_delete)} dòng trùng khỏi Google Sheet (giữ {len(plan['rows_to_keep'])} bản).",
            "plan": plan,
            "duplicate_report": self.duplicate_report,
        }

    def _write_question_field_to_row(
        self, row: List[str], min_len: int, field: str, value: str
    ) -> None:
        value = clean(value)
        if not value:
            return
        cols = self.question_col_index or {}
        col0 = cols.get(field)
        if col0 is not None:
            while len(row) <= col0:
                row.append("")
            row[col0] = value
        fixed = SHEET_QUESTION_FIXED_COL_1.get(field)
        if fixed is not None:
            idx = fixed - 1
            while len(row) <= idx:
                row.append("")
            row[idx] = value
        if len(row) < min_len:
            row.extend([""] * (min_len - len(row)))

    def _question_from_sheet_row(self, row_number: int, row_vals: List[str]) -> Optional[Dict[str, Any]]:
        headers = self.question_headers or []
        raw = {headers[i]: row_vals[i] if i < len(row_vals) else "" for i in range(len(headers))}
        q = canonical_question(raw)
        cols = self.question_col_index or {}
        for field in ("CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo", "LoiGiai"):
            v = row_val(row_vals, cols.get(field))
            if not v:
                continue
            if field in ("CauHoi", "A", "B", "C", "D", "LoiGiai"):
                q[field] = normalize_latex_text(v)
            elif field == "DapAn" and any(x in v for x in ("$", "\\", "{", "}")):
                q[field] = normalize_latex_text(v)
            else:
                q[field] = v
        for f in ("CauHoi", "A", "B", "C", "D", "LoiGiai"):
            q[f] = normalize_latex_text(q.get(f, ""))
        t_col = cols.get("HinhAnh", 19 if len(headers) > 19 else None)
        if t_col is not None:
            t_img = row_val(row_vals, t_col)
            if is_probably_link_or_drive(t_img) or (t_img and not clean(q.get("HinhAnh"))):
                q["HinhAnh"] = t_img
        u_col = cols.get("QuyenTruyCap", 20 if len(headers) > 20 else None)
        if u_col is not None and not clean(q.get("QuyenTruyCap")):
            q["QuyenTruyCap"] = row_val(row_vals, u_col)
        q["HinhAnh"] = normalize_image_src(q.get("HinhAnh"))
        md = row_val(row_vals, cols.get("MucDo"))
        if md:
            q["MucDo"] = md
        dang_raw = row_val(row_vals, cols.get("Dang"))
        if dang_raw:
            q["_DangCol"] = dang_raw
        elif clean(q.get("DangBaiTap", "")):
            q["_DangCol"] = clean(q.get("DangBaiTap", ""))
        elif clean(q.get("Dang", "")):
            q["_DangCol"] = clean(q.get("Dang", ""))
        q["Dang"] = effective_dang(q)
        if not clean(q.get("CauHoi")):
            return None
        q["_row"] = row_number
        return q

    def patch_quiz_sessions_after_row_add(self, new_q: Dict[str, Any]) -> None:
        made = clean(new_q.get("MaDe"))
        new_row = int(new_q.get("_row") or 0)
        new_id = clean(new_q.get("ID", ""))
        for ses in self.quiz_sessions.values():
            ses_made = clean(ses.get("made", ""))
            if made and ses_made and made != ses_made:
                continue
            qs = list(ses.get("questions") or [])
            if new_row and any(int(x.get("_row") or 0) == new_row for x in qs):
                continue
            if new_id and any(clean(x.get("ID", "")) == new_id for x in qs):
                continue
            qs.append(dict(new_q))
            ses["questions"] = qs

    def _find_recent_sheet_duplicate(self, data: Dict[str, Any], lookback: int = 10) -> Optional[int]:
        """Trả về số dòng Sheet nếu vài dòng cuối trùng MaDe + nội dung (chống bấm Thêm 2 lần)."""
        try:
            seed = {f: clean(data.get(f, "")) for f in QUESTION_FIELDS}
            fp_new = question_content_fingerprint(canonical_question(seed))
            values = self.ws_questions.get_all_values()
            if len(values) < 2:
                return None
            headers = self.question_headers or (values[0] if values else [])
            tail = list(enumerate(values[1:], start=2))[-lookback:]
            for row_num, row_vals in tail:
                raw = {headers[i]: row_vals[i] if i < len(row_vals) else "" for i in range(len(headers))}
                q = canonical_question(raw)
                if not clean(q.get("CauHoi")):
                    continue
                if question_content_fingerprint(q) == fp_new:
                    return row_num
        except Exception:
            return None
        return None

    def add_question(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ADMIN thêm câu hỏi mới vào cuối sheet Cau_Hoi."""
        if not is_admin():
            raise RuntimeError("Chỉ ADMIN được thêm câu hỏi")
        data = {k: clean(v) for k, v in (data or {}).items()}
        if not clean(data.get("CauHoi")):
            raise RuntimeError("Phải nhập nội dung câu hỏi (CauHoi).")

        with self.add_question_lock:
            dup_row = self._find_recent_sheet_duplicate(data)
            if dup_row:
                raise RuntimeError(
                    f"Câu này đã có trên Sheet (dòng {dup_row}) — cùng mã đề và nội dung. "
                    "Không thêm lại để tránh lặp. Nếu cần sửa, mở dòng đó hoặc xóa bản trùng trên Google Sheet."
                )

            if not self.question_headers:
                headers_row = self.ws_questions.row_values(1)
                self.question_headers = headers_row
                self.question_col_index = resolve_question_col_index(headers_row)
            headers = list(self.question_headers or [])
            if not headers:
                raise RuntimeError("Sheet Cau_Hoi không có tiêu đề cột.")

            seed = {f: data.get(f, "") for f in QUESTION_FIELDS}
            cq = canonical_question(seed)
            if not clean(data.get("ID")):
                data["ID"] = cq.get("ID") or ("NEW_" + stable_hash(f"{time.time()}|{random.random()}", 10))
            if not clean(data.get("MaDe")):
                data["MaDe"] = cq.get("MaDe", "")

            row: List[str] = []
            min_len = max(len(headers), 20)
            for field in CREATE_QUESTION_FIELDS:
                val = clean(data.get(field, ""))
                if not val and field in ("ID", "MaDe"):
                    val = clean(cq.get(field, ""))
                if val:
                    self._write_question_field_to_row(row, min_len, field, val)
            if len(row) < len(headers):
                row.extend([""] * (len(headers) - len(row)))
            elif len(row) > len(headers):
                row = row[: len(headers)]

            self.ws_questions.append_row(row, value_input_option="USER_ENTERED")
            values = self.ws_questions.get_all_values()
            new_row = len(values)
            row_vals = values[-1] if values else row
            q = self._question_from_sheet_row(new_row, row_vals)
            if not q:
                raise RuntimeError("Đã thêm dòng nhưng không đọc lại được câu hỏi — kiểm tra Sheet.")
            self.questions.append(q)
            self.patch_quiz_sessions_after_row_add(q)
            self.duplicate_report = analyze_question_duplicates(self.questions)
            self.rebuild_indexes_after_admin_change()
            return {
                "ok": True,
                "created": True,
                "row": new_row,
                "id": q.get("ID", ""),
                "question": self.public_question(q, len(self.questions) - 1, reveal=True),
            }


_OPTION_LABEL_RE = re.compile(r"^\s*([ABCD])\s*[\.\)\]:]\s*", re.I)


def _split_option_label(text: Any) -> Tuple[str, Optional[str]]:
    """Tách nhãn đầu dòng A./B./… khỏi nội dung ý (nếu có)."""
    raw = clean(text)
    if not raw:
        return "", None
    m = _OPTION_LABEL_RE.match(raw)
    if m:
        return raw[m.end() :].strip(), m.group(1).upper()
    return raw, None


def _apply_option_label(body: str, new_L: str, had_label: bool) -> str:
    """Gắn lại nhãn A/B/C/D đúng vị trí sau xáo trộn."""
    body = clean(body)
    if not body:
        return ""
    if had_label:
        return f"{new_L}. {body}"
    return body


def _parse_loigiai_bodies_by_letter(text: Any) -> Dict[str, str]:
    """Tách lời giải Đ/S theo chữ A/B/C/D → phần giải thích (không gồm nhãn)."""
    raw = clean(text)
    if not raw:
        return {}
    tagged = list(
        re.finditer(
            r"(?:^|\n|[•\-\*]\s*|\(\s*)(?:\*\*)?([ABCD])\s*[\.\):]\s*(?:(Đúng|Sai)\s*[\-—:–]\s*)?",
            raw,
            re.I | re.M,
        )
    )
    if not tagged:
        return {}
    out: Dict[str, str] = {}
    for i, m in enumerate(tagged[:4]):
        letter = m.group(1).upper()
        start = m.end()
        end = tagged[i + 1].start() if i + 1 < len(tagged) else len(raw)
        body = clean(raw[start:end]).strip(" ).\n")
        body = re.sub(r"\*\*", "", body)
        if body:
            out[letter] = body
    return out


def _format_tf_dapan(bits: List[str], original: Any = "") -> str:
    """Ghép lại đáp án Đ/S sau xáo trộn (giữ kiểu gọn hoặc có dấu phẩy)."""
    orig = clean(original)
    active = [(bits[i] if i < len(bits) else "") for i in range(4)]
    while active and not active[-1]:
        active.pop()
    if not active:
        return orig
    if re.search(r"[,;|]", orig):
        return ",".join(active)
    return "".join(active)


def _format_ds_loigiai_line(letter: str, tf: str, body: str) -> str:
    body = clean(body)
    if not body:
        return ""
    verdict = "Sai" if tf == "S" else "Đúng"
    return f"{letter}. {verdict} — {body}"


def shuffle_mcq_options(q: Dict[str, Any]) -> Dict[str, Any]:
    """Xáo trộn phương án A-D; trắc nghiệm đổi chữ đáp án, Đ/S giữ cặp ý–Đ/S–lời giải."""
    q = dict(q)
    dang = effective_dang(q)
    pairs = [(L, q.get(L, "")) for L in "ABCD" if clean(q.get(L))]
    if len(pairs) < 2:
        return q

    if dang == "Trắc nghiệm":
        correct = norm_letter(q.get("DapAn"))
        items_mcq: List[Dict[str, Any]] = []
        for old_L, text in pairs:
            body, old_label = _split_option_label(text)
            items_mcq.append({"body": body, "had_label": old_label is not None, "old_L": old_L})
        random.shuffle(items_mcq)
        for L in "ABCD":
            q[L] = ""
        new_correct = ""
        for i, item in enumerate(items_mcq):
            new_L = "ABCD"[i]
            q[new_L] = _apply_option_label(item["body"], new_L, item["had_label"])
            if item["old_L"] == correct:
                new_correct = new_L
        if new_correct:
            q["DapAn"] = new_correct
        return q

    if dang == "Đúng sai":
        tf = parse_tf_values(q.get("DapAn"))
        lg_map = _parse_loigiai_bodies_by_letter(q.get("LoiGiai", ""))
        items: List[Dict[str, Any]] = []
        for old_L, text in pairs:
            idx = "ABCD".index(old_L)
            body, old_label = _split_option_label(text)
            items.append(
                {
                    "body": body,
                    "had_label": old_label is not None,
                    "tf": tf[idx] if idx < len(tf) else "",
                    "lg": lg_map.get(old_L, ""),
                }
            )
        random.shuffle(items)
        for L in "ABCD":
            q[L] = ""
        new_tf = ["", "", "", ""]
        lg_lines: List[str] = []
        for i, item in enumerate(items):
            new_L = "ABCD"[i]
            q[new_L] = _apply_option_label(item["body"], new_L, item["had_label"])
            new_tf[i] = item["tf"]
            line = _format_ds_loigiai_line(new_L, item["tf"], item["lg"])
            if line:
                lg_lines.append(line)
        q["DapAn"] = _format_tf_dapan(new_tf, q.get("DapAn"))
        if lg_lines:
            q["LoiGiai"] = "\n".join(lg_lines)
        return q

    return q


def prepare_quiz_questions(
    qs: List[Dict[str, Any]],
    shuffle_questions: bool = False,
    shuffle_options: bool = False,
    group_by_dang: bool = True,
) -> List[Dict[str, Any]]:
    out = [dict(q) for q in qs]
    if group_by_dang:
        out = sort_questions_by_dang_groups(out, shuffle_within=shuffle_questions)
    elif shuffle_questions:
        random.shuffle(out)
    if shuffle_options:
        out = [shuffle_mcq_options(q) for q in out]
    return out


def check_answer(q: Dict[str, Any], user_answer: Any) -> Tuple[bool, str, str]:
    dang = effective_dang(q)
    correct_raw = clean(q.get("DapAn"))
    if dang == "Trắc nghiệm":
        c = norm_letter(correct_raw)
        ch = norm_letter(user_answer)
        return bool(c and ch and c == ch), c, ch
    if dang == "Đúng sai":
        corr = parse_tf_values(correct_raw)
        chosen = parse_tf_values(user_answer)
        corr_bits: List[str] = []
        chosen_bits: List[str] = []
        for idx, L in enumerate("ABCD"):
            if not clean(q.get(L)):
                continue
            corr_bits.append(corr[idx] if idx < len(corr) else "")
            chosen_bits.append(chosen[idx] if idx < len(chosen) else "")
        ok = (
            len(corr_bits) >= 2
            and all(corr_bits)
            and all(chosen_bits)
            and corr_bits == chosen_bits
        )
        return ok, format_tf_answer_display(q, correct_raw), ",".join(chosen_bits)
    if dang == "Trả lời ngắn":
        cn = parse_float_vn(correct_raw)
        un = parse_float_vn(user_answer)
        tol = parse_float_vn(q.get("SaiSo"))
        if tol is None:
            tol = 0.0
        if cn is not None and un is not None:
            return abs(cn - un) <= tol + 1e-12, correct_raw, clean(user_answer)
        return key_norm(correct_raw) == key_norm(user_answer), correct_raw, clean(user_answer)
    return False, correct_raw, clean(user_answer)


def dungsai_rows_detail(q: Dict[str, Any], user_answer: Any) -> List[Dict[str, Any]]:
    corr = parse_tf_values(q.get("DapAn"))
    chosen = parse_tf_values(user_answer)
    while len(chosen) < 4:
        chosen.append("")
    rows: List[Dict[str, Any]] = []
    for idx, L in enumerate(["A", "B", "C", "D"]):
        if not clean(q.get(L)):
            continue
        c = corr[idx] if idx < len(corr) else ""
        ch = chosen[idx] if idx < len(chosen) else ""
        ok = bool(ch) and bool(c) and ch == c
        rows.append({"letter": L, "correct": c, "chosen": ch, "ok": ok if ch else None})
    return rows


def ai_hint_fallback(q: Dict[str, Any], user_answer: Any) -> str:
    dang = effective_dang(q)
    stem = clean(q.get("CauHoi", ""))
    topics = []
    if q.get("Mon"):
        topics.append(f"Môn: {q.get('Mon')}")
    if q.get("Chuong"):
        topics.append(f"Chương: {q.get('Chuong')}")
    if q.get("BaiHoc"):
        topics.append(f"Bài: {q.get('BaiHoc')}")
    base = " | ".join(topics)
    if dang == "Trắc nghiệm":
        opts = [f"{L}. {clean(q.get(L))}" for L in "ABCD" if clean(q.get(L))]
        chosen = norm_letter(user_answer)
        m = re.search(
            r"(-?\d+(?:[.,]\d+)?)\s*x\s*([+\-])\s*(\d+(?:[.,]\d+)?)\s*y\s*([+\-])\s*(\d+(?:[.,]\d+)?)\s*z\s*([+\-])\s*(\d+(?:[.,]\d+)?)",
            stem,
            re.I,
        )
        plane_extra = ""
        if m:

            def _sc(sign: str, num: str) -> str:
                return f"-{num}" if sign == "-" else num

            a = m.group(1).replace(",", ".")
            b = _sc(m.group(2), m.group(3)).replace(",", ".")
            c = _sc(m.group(4), m.group(5)).replace(",", ".")
            d = _sc(m.group(6), m.group(7)).replace(",", ".")
            plane_extra = (
                f"\nCÔNG THỨC (đã thay số): ${a}x{b}y{c}z{d}=0$.\n"
                f"Vectơ pháp tuyến $\\vec{{n}}=({a};{b};{c})$.\n"
                "CÁCH LÀM: so sánh từng phương án A–D với $\\vec{n}$ (cùng tỉ lệ hoặc ngược dấu).\n"
            )
        return (
            f"{base}\n"
            f"ĐỀ: {stem[:240]}\n"
            f"{plane_extra}"
            f"Phương án: {' ; '.join(opts[:4])}\n"
            f"Ý đang làm: {chosen or 'chưa chọn'}.\n"
            "LƯU Ý: app đã loại 2 đáp án sai — em chọn trong 2 phương án còn lại."
        )
    if dang == "Đúng sai":
        chosen = parse_tf_values(user_answer)
        rows = []
        for i, L in enumerate("ABCD"):
            if clean(q.get(L)):
                cur = chosen[i] if i < len(chosen) else "?"
                rows.append(f"{L}: đang chọn {cur} | mệnh đề: {clean(q.get(L))[:120]}")
        return (
            f"{base}\nGợi ý Đúng/Sai: xét từng mệnh đề độc lập theo định nghĩa, điều kiện áp dụng công thức và dấu.\n"
            + "\n".join(rows)
        )
    if dang == "Trả lời ngắn":
        return (
            f"{base}\nGợi ý trả lời ngắn: viết công thức tổng quát, biến đổi để tách đại lượng cần tìm, rồi thay số cẩn thận đơn vị.\n"
            f"Đề bài: {stem[:260]}"
        )
    return f"{base}\nGợi ý tự luận: tách bài thành giả thiết - công thức - biến đổi - kết luận. Đề bài: {stem[:260]}"


def current_mahs() -> str:
    return clean(session.get("mahs", "")) or "_guest"


def get_user_ai_overrides() -> Dict[str, Any]:
    uid = current_mahs()
    if uid not in AI_USER_OVERRIDES:
        AI_USER_OVERRIDES[uid] = {
            "provider": "",
            "openai_keys": [],
            "gemini_keys": [],
            "gemini_model": "",
            "openai_model": "",
        }
    return AI_USER_OVERRIDES[uid]


def clean_ai_key_2026(k: Any) -> str:
    s = clean(k).strip().strip('"').strip("'")
    if not s:
        return ""
    upper = s.upper()
    if "DAN_GEMINI_KEY" in upper or "DAN_OPENAI" in upper or s.startswith("//"):
        return ""
    return s


def parse_api_keys_2026(raw: Any) -> Tuple[List[str], List[str]]:
    """Tách mảng API_KEYS kiểu GAS: AIza... → Gemini, sk-... → OpenAI."""
    if isinstance(raw, list):
        vals = raw
    else:
        vals = re.split(r"[\n,;]+", str(raw or ""))
    gemini: List[str] = []
    openai: List[str] = []
    for x in vals:
        k = clean_ai_key_2026(x)
        if not k:
            continue
        if k.startswith("AIza"):
            gemini.append(k)
        elif k.startswith("sk-"):
            openai.append(k)
    seen_g: set = set()
    seen_o: set = set()
    g_out: List[str] = []
    o_out: List[str] = []
    for k in gemini:
        if k not in seen_g:
            seen_g.add(k)
            g_out.append(k)
    for k in openai:
        if k not in seen_o:
            seen_o.add(k)
            o_out.append(k)
    return g_out[:MAX_AI_KEYS_PER_PROVIDER], o_out[:MAX_AI_KEYS_PER_PROVIDER]


def _validate_key_format(prefix: str, key: str) -> Optional[str]:
    k = clean_ai_key_2026(key)
    if not k:
        return None
    if prefix == "GEMINI":
        if k.startswith("AQ."):
            return (
                "Key AQ... không phải API key Gemini. "
                "Vào https://aistudio.google.com/apikey → Create API key → copy key dạng AIzaSy..."
            )
        if not k.startswith("AIza"):
            return (
                "Gemini API key phải bắt đầu bằng AIza (Google AI Studio). "
                "Không dùng key Google Cloud / OAuth / key AQ..."
            )
    elif prefix == "OPENAI":
        if not k.startswith("sk-"):
            return "OpenAI API key phải bắt đầu bằng sk-."
    return None


def load_ai_keys_from_env(prefix: str) -> List[str]:
    """Key trên Render ENV (dùng chung / dự phòng). Hỗ trợ nhiều key trong một biến (phẩy/xuống dòng)."""
    keys_local: List[str] = []
    env_names = [f"{prefix}_API_KEY"] + [f"{prefix}_API_KEY_{i}" for i in range(1, 10)]
    for name in env_names:
        raw = os.environ.get(name, "")
        if not str(raw or "").strip():
            continue
        for part in re.split(r"[\n,;]+", str(raw)):
            kk = clean_ai_key_2026(part)
            if kk:
                keys_local.append(kk)
    for k in re.split(r"[\n,;]+", os.environ.get(f"{prefix}_API_KEYS", "")):
        kk = clean_ai_key_2026(k)
        if kk:
            keys_local.append(kk)
    seen_local = set()
    uniq_local: List[str] = []
    for k in keys_local:
        if k not in seen_local:
            seen_local.add(k)
            uniq_local.append(k)
    return uniq_local[:MAX_AI_KEYS_PER_PROVIDER]


def load_user_ai_keys(prefix: str) -> List[str]:
    """Key học viên/VIP tự nạp trên web (theo mã HS, lưu RAM server)."""
    mahs = current_mahs()
    if not mahs or mahs == "_guest":
        return []
    ov = get_user_ai_overrides()
    field = "gemini_keys" if prefix == "GEMINI" else "openai_keys"
    out: List[str] = []
    seen: set = set()
    for k in ov.get(field) or []:
        kk = clean_ai_key_2026(k)
        if kk and kk not in seen:
            seen.add(kk)
            out.append(kk)
    return out[:MAX_AI_KEYS_PER_PROVIDER]


def load_ai_keys(prefix: str) -> List[str]:
    """Ưu tiên key tự nạp, sau đó key Render ENV."""
    merged: List[str] = []
    seen: set = set()
    for k in load_user_ai_keys(prefix) + load_ai_keys_from_env(prefix):
        if k and k not in seen:
            seen.add(k)
            merged.append(k)
    return merged[:MAX_AI_KEYS_PER_PROVIDER]


def can_save_own_ai_key() -> bool:
    return can_use_ai_hint()


def ai_runtime_config() -> Dict[str, Any]:
    env_provider = clean(os.environ.get("AI_PROVIDER", DEFAULT_AI_PROVIDER)).upper() or DEFAULT_AI_PROVIDER
    if env_provider not in ["AUTO", "OPENAI", "GEMINI"]:
        env_provider = DEFAULT_AI_PROVIDER
    ov = get_user_ai_overrides() if current_mahs() not in ("", "_guest") else {}
    user_provider = clean(ov.get("provider", "")).upper()
    provider = user_provider if user_provider in ["AUTO", "OPENAI", "GEMINI"] else env_provider

    user_g = load_user_ai_keys("GEMINI")
    user_o = load_user_ai_keys("OPENAI")
    server_g = load_ai_keys_from_env("GEMINI")
    server_o = load_ai_keys_from_env("OPENAI")
    gemini_keys = load_ai_keys("GEMINI")
    openai_keys = load_ai_keys("OPENAI")

    gemini_model = (
        clean(ov.get("gemini_model"))
        or clean(os.environ.get("GEMINI_HINT_MODEL", DEFAULT_GEMINI_HINT_MODEL)).strip()
        or DEFAULT_GEMINI_HINT_MODEL
    )
    openai_model = (
        clean(ov.get("openai_model"))
        or clean(os.environ.get("OPENAI_HINT_MODEL", DEFAULT_OPENAI_HINT_MODEL)).strip()
        or DEFAULT_OPENAI_HINT_MODEL
    )

    def _mask_list(vals: List[str]) -> List[str]:
        out: List[str] = []
        for v in vals[:5]:
            if len(v) <= 10:
                out.append(v)
            else:
                out.append(f"{v[:6]}...{v[-4:]}")
        return out

    return {
        "provider": provider,
        "openai_keys": len(openai_keys),
        "gemini_keys": len(gemini_keys),
        "user_gemini_keys": len(user_g),
        "user_openai_keys": len(user_o),
        "has_keys": bool(openai_keys or gemini_keys),
        "openai_keys_masked": _mask_list(openai_keys),
        "gemini_keys_masked": _mask_list(gemini_keys),
        "gemini_model": gemini_model,
        "openai_model": openai_model,
        "using_user_keys": bool(user_g or user_o),
        "has_server_keys": bool(server_g or server_o),
        "can_save_own_key": can_save_own_ai_key(),
    }


def classify_user_ai_profile(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Phân loại nguồn AI ngay khi đăng nhập: key cá nhân / pool lớp / chưa có key."""
    cfg = cfg or ai_runtime_config()
    adm = is_admin()
    can_ai = can_use_ai_hint()
    using_user = bool(cfg.get("using_user_keys"))
    user_g = int(cfg.get("user_gemini_keys") or 0)
    user_o = int(cfg.get("user_openai_keys") or 0)
    user_keys_n = user_g + user_o
    has_server = bool(cfg.get("has_server_keys"))
    server_n = len(load_ai_keys_from_env("GEMINI"))

    if not can_ai:
        return {
            "ai_profile": "FREE",
            "ai_profile_label": "FREE · Không AI",
            "ai_profile_hint": "Tài khoản này làm đề bình thường, không có Gợi ý AI. Liên hệ giáo viên nếu cần nâng VIP.",
            "ai_profile_action": "",
            "ai_key_source": "none",
            "ai_show_key_panel": False,
            "ai_nudge_key": False,
            "ai_server_key_count": server_n,
        }

    if using_user and user_keys_n > 0:
        code = "ADMIN_OWN" if adm else "VIP_OWN"
        label = "ADMIN · Key cá nhân" if adm else "VIP · Key cá nhân"
        hint = (
            f"Đã lưu {user_g or user_keys_n} key Gemini — ưu tiên khi Gợi ý AI, không tranh quota với lớp."
            if not adm
            else f"ADMIN: {user_g or user_keys_n} key riêng. Pool Render ({server_n} key) dự phòng cho học sinh chưa nạp key."
        )
        return {
            "ai_profile": code,
            "ai_profile_label": label,
            "ai_profile_hint": hint,
            "ai_profile_action": "",
            "ai_key_source": "own",
            "ai_show_key_panel": True,
            "ai_nudge_key": False,
            "ai_server_key_count": server_n,
        }

    if has_server:
        code = "ADMIN_POOL" if adm else "VIP_POOL"
        label = "ADMIN · Pool server" if adm else "VIP · Pool lớp"
        hint = (
            f"Đang dùng {server_n} key chung trên server. "
            "Nên tạo key tại Google AI Studio → 🔑 Key AI của tôi → Lưu để luyện ổn định, không tranh với lớp."
            if not adm
            else f"Chưa có key ADMIN riêng — đang dùng pool Render ({server_n} key). Nên nạp key cá nhân khi tự luyện."
        )
        return {
            "ai_profile": code,
            "ai_profile_label": label,
            "ai_profile_hint": hint,
            "ai_profile_action": "add_own_key",
            "ai_key_source": "pool",
            "ai_show_key_panel": True,
            "ai_nudge_key": True,
            "ai_server_key_count": server_n,
        }

    code = "ADMIN_NO_KEY" if adm else "VIP_NO_KEY"
    label = "ADMIN · Chưa có key" if adm else "VIP · Chưa có key"
    hint = (
        "Chưa có key AI. Dán key AIza... tại 🔑 Key AI của tôi hoặc nhờ giáo viên cấu hình GEMINI_API_KEY trên Render."
        if not adm
        else "Chưa có key AI trên server và chưa nạp key riêng — cần cấu hình Render hoặc Lưu key ADMIN."
    )
    return {
        "ai_profile": code,
        "ai_profile_label": label,
        "ai_profile_hint": hint,
        "ai_profile_action": "add_key_required",
        "ai_key_source": "none",
        "ai_show_key_panel": True,
        "ai_nudge_key": True,
        "ai_server_key_count": 0,
    }


def update_ai_runtime_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not can_save_own_ai_key():
        raise ValueError("Lưu key AI chỉ dành tài khoản VIP / SVIP / ADMIN.")
    ov = get_user_ai_overrides()
    if payload.get("clear_keys"):
        ov["gemini_keys"] = []
        ov["openai_keys"] = []
        return ai_runtime_config()
    provider = clean(payload.get("provider", "")).upper()
    if provider and provider in ["AUTO", "OPENAI", "GEMINI"]:
        ov["provider"] = provider
    elif provider:
        raise ValueError("AI_PROVIDER chỉ nhận AUTO, OPENAI hoặc GEMINI")

    # Giống GAS: api_keys rỗng → không ghi đè key đã lưu
    if "api_keys" in payload and str(payload.get("api_keys") or "").strip():
        g_keys, o_keys = parse_api_keys_2026(payload.get("api_keys"))
        if g_keys:
            for k in g_keys:
                err = _validate_key_format("GEMINI", k)
                if err:
                    raise ValueError(err)
            ov["gemini_keys"] = g_keys
        if o_keys:
            for k in o_keys:
                err = _validate_key_format("OPENAI", k)
                if err:
                    raise ValueError(err)
            ov["openai_keys"] = o_keys
        if not g_keys and not o_keys:
            raise ValueError("Không nhận diện được key. Dán Gemini (AIza...) hoặc OpenAI (sk-...) mỗi dòng một key.")

    if "gemini_keys" in payload and str(payload.get("gemini_keys") or "").strip():
        parsed, _ = parse_api_keys_2026(payload.get("gemini_keys"))
        for k in parsed:
            err = _validate_key_format("GEMINI", k)
            if err:
                raise ValueError(err)
        ov["gemini_keys"] = parsed
    if "openai_keys" in payload and str(payload.get("openai_keys") or "").strip():
        _, parsed = parse_api_keys_2026(payload.get("openai_keys"))
        for k in parsed:
            err = _validate_key_format("OPENAI", k)
            if err:
                raise ValueError(err)
        ov["openai_keys"] = parsed
    if "gemini_model" in payload:
        ov["gemini_model"] = clean(payload.get("gemini_model"))
    if "openai_model" in payload:
        ov["openai_model"] = clean(payload.get("openai_model"))

    return ai_runtime_config()


def gemini_prompt_brand_2026() -> str:
    return "Bạn là trợ giảng luyện đề của Lớp học Thầy Minh, ưu tiên tính chính xác và sư phạm."


def build_ai_question_block(
    q: Dict[str, Any], user_answer: Any, *, include_sheet_answer: bool = True
) -> str:
    dang = effective_dang(q)
    opts = []
    for L in "ABCD":
        v = clean(q.get(L, ""))
        if v:
            opts.append(f"{L}. {v}")
    options_text = "\n".join(opts) if opts else "(không có phương án lựa chọn)"
    chosen_text = ""
    if dang == "Đúng sai":
        chosen_text = ",".join(parse_tf_values(user_answer))
    else:
        chosen_text = clean(user_answer)
    lines = [
        f"Môn: {clean(q.get('Mon', ''))}",
        f"Chương: {clean(q.get('Chuong', ''))}",
        f"Bài học: {clean(q.get('BaiHoc', ''))}",
        f"Mức độ: {clean(q.get('MucDo', ''))}",
        f"Dạng câu: {dang}",
        "",
        "Đề bài:",
        clean(q.get("CauHoi", "")),
        "",
        "Phương án:",
        options_text,
        "",
        f"Học sinh đang chọn: {chosen_text or '(chưa chọn)'}",
    ]
    if include_sheet_answer:
        lines.extend(
            [
                f"Đáp án chuẩn tham chiếu nội bộ (Sheet cột P): {clean(q.get('DapAn', ''))}",
                f"Lời giải hiện có (Sheet cột R): {clean(q.get('LoiGiai', ''))}",
            ]
        )
    else:
        lines.append("(Không tiết lộ đáp án Sheet — học sinh tự làm.)")
    return "\n".join(lines)


def _latex_one_line_infographic(t: str) -> str:
    if not t:
        return ""
    m = re.search(r"\\immini\s*\{([\s\S]*)\}\s*$", t, flags=re.I)
    if m:
        t = m.group(1).strip()
    t = re.sub(r"\\immini\s*\{", "", t, flags=re.I)
    if t.endswith("}"):
        t = t[:-1].strip()
    for _ in range(6):
        t = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"(\1)/(\2)", t)
    repl = [
        (r"\\cdot", "·"),
        (r"\\times", "×"),
        (r"\\pm", "±"),
        (r"\\leq", "≤"),
        (r"\\geq", "≥"),
        (r"\\neq", "≠"),
        (r"\\approx", "≈"),
        (r"\\infty", "∞"),
        (r"\\pi", "π"),
        (r"\\alpha", "α"),
        (r"\\beta", "β"),
        (r"\\gamma", "γ"),
        (r"\\Delta", "Δ"),
        (r"\\theta", "θ"),
        (r"\\phi", "φ"),
        (r"\\rho", "ρ"),
        (r"\\sigma", "σ"),
        (r"\\tau", "τ"),
        (r"\\nu", "ν"),
        (r"\\epsilon", "ε"),
        (r"\\eta", "η"),
        (r"\\Omega", "Ω"),
        (r"\\ohm", "Ω"),
        (r"\\degree", "°"),
        (r"\\circ", "°"),
        (r"\\mu", "μ"),
        (r"\\rightarrow", "→"),
        (r"\\Rightarrow", "⇒"),
        (r"\\to", "→"),
        (r"\\sqrt\s*\{([^{}]+)\}", r"√(\1)"),
        (r"\\overrightarrow\s*\{([^{}]+)\}", r"→\1"),
        (r"\\vec\s*\{([^{}]+)\}", r"\1⃗"),
        (r"\\text\s*\{([^{}]+)\}", r"\1"),
        (r"\\mathrm\s*\{([^{}]+)\}", r"\1"),
        (r"\\left\s*\(", "("),
        (r"\\right\s*\)", ")"),
        (r"\\left\s*\[", "["),
        (r"\\right\s*\]", "]"),
        (r"\\,", " "),
        (r"\\;", " "),
        (r"\\!", ""),
        (r"\\quad", "  "),
        (r"\\\\", " "),
        (r"\\%", "%"),
    ]
    for pat, rep in repl:
        t = re.sub(pat, rep, t)
    t = re.sub(r"_\{([^{}]+)\}", r"_\1", t)
    t = re.sub(r"\^\{([^{}]+)\}", r"^\1", t)
    t = re.sub(r"\$([^$]+)\$", r"\1", t)
    t = t.replace("$", "")
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = t.replace("{", "").replace("}", "")
    t = re.sub(r"[ \t]+", " ", t).strip()
    return _fix_plain_text_gaps(t)


def latex_to_infographic_plain(s: Any, *, preserve_lines: bool = False) -> str:
    """Chuyển LaTeX/Sheet sang chữ thường dễ đọc cho prompt tạo infographic."""
    t = normalize_latex_text(s)
    if not t:
        return ""
    if preserve_lines:
        lines = [_latex_one_line_infographic(line) for line in t.split("\n")]
        out = "\n".join(lines)
        out = re.sub(r"\n{3,}", "\n\n", out)
        return out.strip()
    return _latex_one_line_infographic(t)


def _infographic_dang_spec(dang: str) -> Dict[str, Any]:
    specs = {
        "Trắc nghiệm": {
            "code": "TN",
            "title": "TRẮC NGHIỆM (TN)",
            "desc": "Một phương án A/B/C/D đúng duy nhất.",
            "must_show": [
                "Badge MỨC ĐỘ (cột I: NB/TH/VD/VDC) — nổi bật góc trên infographic",
                "Đề bài (cột K) đầy đủ",
                "Đủ 4 phương án A, B, C, D (cột L–O) có trong Sheet",
                "Đáp án đúng: một chữ A/B/C/D (cột P) — ghi rõ và tô/highlight",
                "Bài giải / lời giải đầy đủ (cột R) — không cắt bớt",
                "Vùng hình minh họa (cột T nếu có link; nếu không thì vẽ bám đề + lời giải)",
            ],
            "layout": "Đề bài → bốn phương án A–D (tô đáp án đúng) → hình minh họa → lời giải (4 vùng tách rõ).",
        },
        "Đúng sai": {
            "code": "Đ/S",
            "title": "ĐÚNG SAI (Đ/S)",
            "desc": "Bốn mệnh đề A–D, mỗi ý Đúng hoặc Sai.",
            "must_show": [
                "Badge MỨC ĐỘ (cột I) nổi bật",
                "Đề bài / câu dẫn (cột K)",
                "Đủ các mệnh đề A, B, C, D (cột L–O) — mỗi ý kèm nhãn Đúng hoặc Sai",
                "Đáp án tổng hợp A=… · B=… (cột P)",
                "Bài giải từng ý A. Đúng/Sai — … (cột R) — đủ 4 dòng nếu Sheet có",
                "Hình minh họa (cột T hoặc vẽ theo đề)",
            ],
            "layout": "Đề/câu dẫn → bốn mệnh đề A–D kèm Đúng/Sai → hình → lời giải từng ý (4 vùng tách rõ).",
        },
        "Trả lời ngắn": {
            "code": "TLN",
            "title": "TRẢ LỜI NGẮN (TLN)",
            "desc": "Học sinh nhập kết quả số hoặc biểu thức — không chọn A/B/C/D.",
            "must_show": [
                "Badge MỨC ĐỘ (cột I) nổi bật",
                "Đề bài (cột K) — thường không có phương án A–D",
                "Đáp án đúng: số/biểu thức (cột P) + sai số nếu có (cột Q)",
                "Bài giải / lời giải chi tiết từng bước (cột R)",
                "Hình minh họa (cột T hoặc vẽ theo đề + bài giải)",
            ],
            "layout": "Đề bài → khung ĐÁP ÁN (cột P) → hình → lời giải từng bước (4 vùng tách rõ).",
        },
        "Tự luận": {
            "code": "TL",
            "title": "TỰ LUẬN (TL)",
            "desc": "Câu mở — trình bày lời giải dài.",
            "must_show": [
                "Badge MỨC ĐỘ (cột I) nổi bật",
                "Đề bài (cột K)",
                "Đáp án / kết quả chính (cột P) nếu có",
                "Bài giải đầy đủ (cột R)",
                "Hình minh họa (cột T hoặc vẽ theo đề)",
            ],
            "layout": "Đề bài → kết quả chính (nếu có) → hình → lời giải dài (4 vùng tách rõ).",
        },
    }
    return specs.get(dang, specs["Trắc nghiệm"])


def _infographic_format_options(q: Dict[str, Any], dang: str) -> List[str]:
    lines: List[str] = []
    if dang == "Trả lời ngắn":
        has_opt = any(clean(q.get(L)) for L in "ABCD")
        if not has_opt:
            return []
    if dang not in ("Trắc nghiệm", "Đúng sai") and not any(clean(q.get(L)) for L in "ABCD"):
        return []
    correct = norm_letter(q.get("DapAn")) if dang == "Trắc nghiệm" else ""
    tf = parse_tf_values(q.get("DapAn")) if dang == "Đúng sai" else []
    for idx, L in enumerate("ABCD"):
        v = latex_to_infographic_plain(q.get(L, ""))
        if not v:
            continue
        if dang == "Trắc nghiệm":
            tag = "  ← ĐÁP ÁN ĐÚNG (Sheet P)" if L == correct else ""
            lines.append(f"{L}. {v}{tag}")
        elif dang == "Đúng sai":
            verdict = ""
            if idx < len(tf) and tf[idx] == "Đ":
                verdict = " [ĐÚNG]"
            elif idx < len(tf) and tf[idx] == "S":
                verdict = " [SAI]"
            lines.append(f"{L}. {v}{verdict}")
        else:
            lines.append(f"{L}. {v}")
    return lines


def _infographic_format_dapan(q: Dict[str, Any], dang: str) -> str:
    raw = clean(q.get("DapAn", ""))
    if not raw:
        return ""
    if dang == "Đúng sai":
        return format_tf_answer_display(q)
    if dang == "Trắc nghiệm":
        c = norm_letter(raw)
        if c:
            return f"Phương án đúng: {c}"
        return latex_to_infographic_plain(raw)
    return latex_to_infographic_plain(raw)


def _infographic_format_loigiai(q: Dict[str, Any], dang: str) -> str:
    raw = clean(q.get("LoiGiai", ""))
    if not raw:
        return ""
    if dang == "Đúng sai":
        lg_map = _parse_loigiai_bodies_by_letter(raw)
        tf = parse_tf_values(q.get("DapAn"))
        lines: List[str] = []
        for idx, L in enumerate("ABCD"):
            if not clean(q.get(L)) and L not in lg_map:
                continue
            verdict = "Đúng" if idx < len(tf) and tf[idx] == "Đ" else (
                "Sai" if idx < len(tf) and tf[idx] == "S" else ""
            )
            body = lg_map.get(L, "")
            if body:
                body = latex_to_infographic_plain(body, preserve_lines=True)
                head = f"{L}. {verdict} — " if verdict else f"{L}. "
                lines.append(head + body)
            elif verdict:
                stmt = latex_to_infographic_plain(q.get(L, ""))
                if stmt:
                    lines.append(f"{L}. {verdict} — (mệnh đề) {stmt}")
        if lines:
            return "\n".join(lines)
    return latex_to_infographic_plain(raw, preserve_lines=True)


def _infographic_block2_phuong_an(
    q: Dict[str, Any], dang: str, opts_lines: List[str], dapan: str
) -> List[str]:
    """Khối 2: phương án / mệnh đề / đáp án ngắn — gộp đáp án P vào đây, không tách khối riêng."""
    lines: List[str] = []
    if opts_lines:
        lines.extend(opts_lines)
    if dang == "Trắc nghiệm":
        if dapan and not any("ĐÁP ÁN" in x for x in lines):
            lines.extend(["", f"→ {dapan}"])
    elif dang == "Đúng sai":
        if dapan:
            lines.extend(["", f"Tổng hợp đáp án (cột P): {dapan}"])
    elif dang == "Trả lời ngắn":
        lines.append(f"ĐÁP ÁN: {dapan or '(trống — cột P)'}")
        saiso = clean(q.get("SaiSo", ""))
        if saiso:
            lines.append(f"Sai số cho phép (cột Q): {latex_to_infographic_plain(saiso)}")
    elif dang == "Tự luận":
        if dapan:
            lines.append(f"Kết quả / đáp án chính (cột P): {dapan}")
        elif not lines:
            lines.append("(Dạng tự luận — không có phương án A/B/C/D)")
    elif dapan and not lines:
        lines.append(dapan)
    return lines


def _infographic_completeness_warnings(q: Dict[str, Any]) -> List[str]:
    dang = effective_dang(q)
    spec = _infographic_dang_spec(dang)
    warnings: List[str] = []
    if not clean(q.get("CauHoi", "")):
        warnings.append("Thiếu câu hỏi (cột K).")
    if not clean(q.get("LoiGiai", "")):
        warnings.append("Thiếu bài giải / lời giải (cột R).")
    if not clean(q.get("DapAn", "")):
        warnings.append("Thiếu đáp án (cột P).")
    if dang in ("Trắc nghiệm", "Đúng sai"):
        n_opts = sum(1 for L in "ABCD" if clean(q.get(L)))
        if n_opts < 2:
            warnings.append(f"Dạng {spec['code']}: thiếu phương án/mệnh đề A–D (cột L–O).")
        if dang == "Trắc nghiệm" and not is_mcq_letter_answer(q.get("DapAn")):
            warnings.append("Dạng TN: đáp án P không phải một chữ A/B/C/D.")
        if dang == "Đúng sai":
            lg_map = _parse_loigiai_bodies_by_letter(q.get("LoiGiai", ""))
            need = [L for L in "ABCD" if clean(q.get(L))]
            miss_lg = [L for L in need if L not in lg_map]
            if miss_lg:
                warnings.append(f"Dạng Đ/S: lời giải thiếu ý {', '.join(miss_lg)}.")
    if not clean(q.get("HinhAnh", "")):
        warnings.append("Chưa có link hình (cột T) — prompt yêu cầu Gemini vẽ minh họa bám đề.")
    if not infographic_mucdo_label(q):
        warnings.append("Chưa có Mức độ (cột I) — infographic vẫn tạo được nhưng nên ghi NB/TH/VD/VDC trên Sheet.")
    return warnings


def build_gemini_infographic_prompt(q: Dict[str, Any]) -> str:
    """Prompt Gemini tạo ảnh trang vở học sinh — ký hiệu khoa học đúng, đủ TN/Đ/S/TLN/TL."""
    dang = effective_dang(q)
    spec = _infographic_dang_spec(dang)
    q_text = latex_to_infographic_plain(q.get("CauHoi", ""), preserve_lines=True)
    opts_lines = _infographic_format_options(q, dang)
    dapan = _infographic_format_dapan(q, dang)
    loigiai = _infographic_format_loigiai(q, dang)
    hinh = clean(q.get("HinhAnh", ""))
    mucdo = infographic_mucdo_label(q)
    meta = [
        ("Môn", clean(q.get("Mon", "Vật lý"))),
        ("Chương", clean(q.get("Chuong", ""))),
        ("Bài học", clean(q.get("BaiHoc", ""))),
        ("ID câu", clean(q.get("ID", ""))),
        ("Mã đề", clean(q.get("MaDe", ""))),
    ]
    lines = [
        "Bạn vẽ POSTER INFOGRAPHIC GIÁO DỤC HIỆN ĐẠI Vật lý/Toán THPT — màu đầy đủ, gradient, 4 card (đề | phương án | hình | lời giải), nổi bật như poster Canva.",
        "Poster màu bão hòa, hiện đại 2024–2026 — KHÔNG in chữ «KHỐI»; mỗi vùng là card gradient riêng. Nội dung đúng Sheet/SGK.",
        "",
        "═══ LOẠI CÂU (XÁC ĐỊNH RÕ — BẮT BUỘC TUÂN THEO) ═══",
        f"• Dạng: {spec['title']}",
        f"• Mô tả: {spec['desc']}",
        f"• Bố cục gợi ý: {spec['layout']}",
        "• Infographic PHẢI hiển thị đủ các mục sau (theo đúng dạng câu trên):",
    ]
    for item in spec["must_show"]:
        lines.append(f"  – {item}")
    mucdo_block = mucdo or "(trống — cột I chưa ghi NB/TH/VD/VDC)"
    lines.extend(
        [
            "",
            "═══ MỨC ĐỘ (CỘT I — BẮT BUỘC NỔI BẬT TRÊN INFOGRAPHIC) ═══",
            f"• Giá trị Google Sheet: {mucdo_block}",
            f"• Thiết kế badge: {infographic_mucdo_highlight_hint(mucdo)}",
            "• Badge «MỨC ĐỘ: …» góc trên phải — sticker 3D glow, màu bão hòa (NB #22C55E · TH #3B82F6 · VD #F59E0B · VDC #DC2626)",
            "• NB = Nhận biết | TH = Thông hiểu | VD = Vận dụng | VDC = Vận dụng cao",
        ]
    )
    lines.extend(
        [
            "",
            "═══ ĐỘ CHÍNH XÁC (NGUỒN DUY NHẤT: GOOGLE SHEET) ═══",
            "• COPY NGUYÊN VĂN từ các khối NỘI DUNG SHEET bên dưới — không paraphrase làm sai",
            "• KHÔNG bịa thêm số liệu, công thức, bước giải, phương án hay kết luận",
            "• KHÔNG đổi đáp án; TN không được chọn sai chữ A/B/C/D; Đ/S không đảo Đúng/Sai",
            "• Bài giải (cột R) phải in ĐỦ — không tóm tắt mất bước",
            "• Tiếng Việt đúng chính tả, dấu thanh đầy đủ",
            "• Công thức trong Sheet có thể là mã LaTeX — phải CHUYỂN sang ký hiệu viết tay chuẩn (xem mục KÝ HIỆU bên dưới)",
            "",
        ]
    )
    block2 = _infographic_block2_phuong_an(q, dang, opts_lines, dapan)
    if dang == "Trắc nghiệm":
        block2_title = "VÙNG 2 — PHƯƠNG ÁN (cột L–O + đáp án đúng cột P)"
    elif dang == "Đúng sai":
        block2_title = "VÙNG 2 — PHƯƠNG ÁN / MỆNH ĐỀ (cột L–O + Đúng/Sai cột P)"
    elif dang == "Trả lời ngắn":
        block2_title = "VÙNG 2 — ĐÁP ÁN (cột P, không có A/B/C/D)"
    else:
        block2_title = "VÙNG 2 — PHƯƠNG ÁN / KẾT QUẢ"
    if hinh:
        block3_lines = [
            hinh,
            "Yêu cầu vẽ: flat vector poster hiện đại theo link/mô tả — đa màu, sạch, chuẩn SGK; không clip-art trẻ em, không chữ giải dài.",
        ]
    else:
        block3_lines = [
            "Sheet chưa có link (cột T) — vẽ flat vector poster BÁM SÁT đề và lời giải.",
            "Sơ đồ đa màu hiện đại + nhãn (A, B, I₁, Oxy, v⃗, B⃗…). Không clip-art trẻ em, không chép bài giải vào card hình.",
        ]
    lines.extend(_infographic_notebook_style_rules())
    lines.extend(_infographic_scientific_layout_rules())
    lines.extend(_infographic_vivid_color_rules())
    lines.extend(
        [
            "",
            "═══ PHÂN VÙNG 4 CARD TRÊN POSTER (BẮT BUỘC — TÁCH RÕ, HIỆN ĐẠI) ═══",
            "Poster dọc 3:4 hoặc 4:5 — 4 CARD gradient xếp dọc, bo góc, bóng đổ, tiêu đề trên thanh màu:",
            "",
            "  ┌──────────────────────────────────────────┐",
            "  │ ĐỀ BÀI (câu hỏi / câu dẫn)               │",
            "  ├──────────────────────────────────────────┤",
            "  │ PHƯƠNG ÁN / MỆNH ĐỀ (A B C D)            │",
            "  ├──────────────────────────────────────────┤",
            "  │ HÌNH MINH HỌA (sơ đồ, vectơ…)            │",
            "  ├──────────────────────────────────────────┤",
            "  │ LỜI GIẢI (từng bước, đủ cột R)           │",
            "  └──────────────────────────────────────────┘",
            "",
            "• QUAN TRỌNG: KHÔNG in chữ «KHỐI 1», «KHỐI 2», «KHỐI 3», «KHỐI 4» trên ảnh — chỉ phân vùng + (tuỳ chọn) tiêu đề «ĐỀ BÀI»…",
            "• Các nhãn «VÙNG 1/2/3/4» bên dưới prompt chỉ để bạn biết nội dung — KHÔNG xuất hiện trên ảnh",
            "• Header trên cùng: «MÔN · CHƯƠNG · BÀI» (từ metadata) + badge MỨC ĐỘ góc phải",
            "• Tỷ lệ poster: 3:4 hoặc 4:5 (dọc — poster giáo dục in treo tường / share mạng xã hội)",
            "• KHÔNG trộn đề + phương án + hình + lời giải vào một đống — nhìn là thấy 4 vùng riêng",
            "",
            "═══ METADATA (ghi nhỏ góc trên hoặc dưới badge mức độ) ═══",
        ]
    )
    for label, val in meta:
        if val:
            lines.append(f"• {label}: {val}")
    lines.extend(
        [
            "",
            "═══ NỘI DUNG SHEET — CHÉP ĐÚNG VÀO TỪNG KHỐI TƯƠNG ỨNG ═══",
            "",
            "════════ VÙNG 1 — ĐỀ BÀI (cột K) [chỉ nội dung prompt, không in «KHỐI» trên ảnh] ════════",
            q_text or "(trống — không tự bịa đề)",
            "",
            f"════════ {block2_title} ════════",
            *(
                block2
                if block2
                else ["(Không có phương án — chỉ ghi đáp án nếu Sheet có cột P)"]
            ),
            "",
            "════════ VÙNG 3 — HÌNH MINH HỌA (cột T) ════════",
            *block3_lines,
            "",
            "════════ VÙNG 4 — LỜI GIẢI (cột R — ĐỦ, KHÔNG CẮT) ════════",
            loigiai or "(trống — ghi «Chưa có bài giải trên Sheet», không tự viết)",
            "",
            "═══ CHECKLIST TRƯỚC KHI XUẤT ẢNH ═══",
            f"☑ Đúng dạng {spec['title']} — thứ tự 4 vùng: Đề → Phương án → Hình → Lời giải",
            f"☑ Badge MỨC ĐỘ «{mucdo_block}» nổi bật (cột I)",
            "☑ Poster màu đầy đủ, gradient hiện đại — 4 card nổi bật, KHÔNG chữ «KHỐI»",
            "☑ Đáp án đúng glow/viền vàng; ĐÚNG-SAI pill màu; sơ đồ flat đa màu; lời giải badge từng bước",
            "☑ Mọi chữ khớp Sheet; lời giải không bị cắt ngắn",
            "☑ Trông như poster Canva giáo dục 2024–2026 — bão hòa, bóng đổ, bo góc",
            "☑ Ký hiệu α Δ λ Ω v₀ F⃗ 10⁸ m/s… đúng — KHÔNG còn $ \\frac \\text trong ảnh",
            "",
            "Xuất ảnh POSTER INFOGRAPHIC HIỆN ĐẠI — màu đầy đủ, 4 card gradient, đúng Sheet, không chữ Khối.",
        ]
    )
    return "\n".join(lines)


def sanitize_hint_math_text(s: Any) -> str:
    """Sửa LaTeX AI hay xuống dòng trong $...$ khiến MathJax trống."""
    t = clean(s)
    if not t:
        return ""
    t = re.sub(r"\$\$\s*", "$", t)
    t = re.sub(r"\s*\$\$", "$", t)
    t = re.sub(r"\$\s*\n+\s*\$", "", t)
    t = re.sub(r"\$\s*\n+\s*([^$\n]+?)\s*\n+\s*\$", r"$(\1)$", t)
    t = re.sub(r"\$\s*\n+([^$\n]+?)\s*\$", r"$(\1)$", t)
    return t


def trim_ai_hint_text(txt: str, max_chars: Optional[int] = None) -> str:
    txt = clean(txt)
    limit = AI_HINT_MAX_CHARS if max_chars is None else max_chars
    if len(txt) <= limit:
        return txt
    cut = txt[:limit]
    for sep in ["\n\n", "\n", ". "]:
        pos = cut.rfind(sep)
        if pos > limit // 3:
            return cut[: pos + (1 if sep == "\n" else len(sep))].strip() + "…"
    return cut.rstrip() + "…"


def _admin_hint_has_section(txt: str, section: str) -> bool:
    patterns = {
        "1": r"1\.\s*GIẢI TỪNG Ý",
        "2": r"2\.\s*CHỐT ĐÁP ÁN",
        # Legacy 8 mục (bản cũ)
        "4": r"4\.\s*BÀI GIẢI",
        "5": r"5\.\s*(?:ĐÁP ÁN AI KẾT LUẬN|ĐÁP ÁN|KẾT LUẬN)",
        "8": r"8\.\s*(?:ĐỀ XUẤT LỜI GIẢI|LỜI GIẢI)",
    }
    pat = patterns.get(section)
    if not pat:
        return False
    return bool(re.search(pat, str(txt or ""), re.I))


def _admin_section_body(txt: str, section: str) -> str:
    markers = {
        "1": (r"1\.\s*GIẢI TỪNG Ý[^\n]*\n", r"2\.\s"),
        "2": (r"2\.\s*CHỐT ĐÁP ÁN[^\n]*\n", r"\Z"),
        "4": (r"4\.\s*BÀI GIẢI[^\n]*\n", r"5\.\s"),
        "5": (r"5\.\s*(?:ĐÁP ÁN AI KẾT LUẬN|ĐÁP ÁN|KẾT LUẬN)[^\n]*\n", r"6\.\s"),
        "8": (r"8\.\s*(?:ĐỀ XUẤT LỜI GIẢI|LỜI GIẢI)[^\n]*\n", r"\Z"),
    }
    spec = markers.get(section)
    if not spec:
        return ""
    m = re.search(spec[0] + r"(.*?)(?=" + spec[1] + r"|\Z)", txt, re.I | re.S)
    return clean(m.group(1)) if m else ""


def _admin_ds_has_four_lines(body1: str) -> bool:
    found: set = set()
    for m in re.finditer(
        r"(?:^|\n)\s*([ABCD])\s*[\.\):]\s*(?:Đúng|Sai)",
        clean(body1),
        re.I | re.M,
    ):
        found.add(m.group(1).upper())
    return len(found) >= 4


def _admin_tn_has_four_opts(body1: str) -> bool:
    found: set = set()
    text = clean(body1)
    for pat in (
        r"(?:^|\n)\s*\*\*([ABCD])\.\*\*",
        r"(?:^|\n)\s*([ABCD])\s*[\.\):]",
    ):
        for m in re.finditer(pat, text, re.I | re.M):
            found.add(m.group(1).upper())
    return len(found) >= 3


def _admin_section1_min_len(q: Optional[Dict[str, Any]] = None) -> int:
    if not q:
        return 80
    dang = effective_dang(q)
    if dang == "Đúng sai":
        return 180
    if dang == "Trắc nghiệm":
        return 220
    if dang == "Trả lời ngắn":
        return 140
    return 90


def _admin_section1_detailed_enough(body1: str, q: Optional[Dict[str, Any]] = None) -> bool:
    body1 = clean(body1)
    if len(body1) < _admin_section1_min_len(q):
        return False
    if q and effective_dang(q) == "Đúng sai":
        return _admin_ds_has_four_lines(body1)
    if q and effective_dang(q) == "Trắc nghiệm":
        return _admin_tn_has_four_opts(body1)
    return True


def _admin_hint_complete(txt: str, q: Optional[Dict[str, Any]] = None) -> bool:
    """Đủ khi có mục 1 (giải chi tiết từng ý) + mục 2 (chốt đáp án)."""
    txt = clean(txt)
    if not txt:
        return False
    if _admin_hint_has_section(txt, "1") and _admin_hint_has_section(txt, "2"):
        body1 = _admin_section_body(txt, "1")
        body2 = _admin_section_body(txt, "2")
        return (
            _admin_section1_detailed_enough(body1, q)
            and bool(body2.strip())
            and not body1.endswith("…")
        )
    # Legacy 8 mục
    for sec in ("4", "5", "8"):
        if not _admin_hint_has_section(txt, sec):
            return False
    body4 = _admin_section_body(txt, "4")
    body5 = _admin_section_body(txt, "5")
    body8 = _admin_section_body(txt, "8")
    if len(body4) < 20 or not body5.strip():
        return False
    if not body8:
        return False
    if re.search(r"giữ nguyên lời giải sheet", body8, re.I):
        return True
    return len(body8) >= 12 and not body8.endswith("…")


def _admin_hint_needs_continuation(txt: str, finish: str, q: Optional[Dict[str, Any]] = None) -> bool:
    if not clean(txt):
        return False
    return not _admin_hint_complete(txt, q)


def _admin_missing_sections(txt: str, q: Optional[Dict[str, Any]] = None) -> List[str]:
    txt = clean(txt)
    if _admin_hint_has_section(txt, "1"):
        missing: List[str] = []
        if not _admin_hint_has_section(txt, "2"):
            missing.append("2")
        body1 = _admin_section_body(txt, "1")
        if not _admin_section1_detailed_enough(body1, q):
            missing.append("1")
        body2 = _admin_section_body(txt, "2")
        if not body2.strip() and "2" not in missing:
            missing.append("2")
        return missing
    if _admin_hint_has_section(txt, "4"):
        missing = []
        for sec in ("4", "5", "8"):
            if not _admin_hint_has_section(txt, sec):
                missing.append(sec)
        if len(_admin_section_body(txt, "4")) < 20:
            missing.append("4")
        if not _admin_section_body(txt, "5").strip():
            missing.append("5")
        if not _admin_section_body(txt, "8"):
            missing.append("8")
        return missing
    return ["1", "2"]


def _admin_continuation_user_prompt(out: str, teacher_prompt: str) -> str:
    return (
        "Phản hồi TRƯỚC bị cắt giữa chừng hoặc thiếu mục. Hãy TIẾP TỤC ngay từ chỗ dừng, "
        "hoàn thành đủ 2 mục: 1. GIẢI TỪNG Ý (CHI TIẾT từng A/B/C/D, có $...$) và 2. CHỐT ĐÁP ÁN. "
        "KHÔNG tóm tắt đề. KHÔNG gợi ý ngắn kiểu VIP. KHÔNG dùng \\begin{enumerate}, \\item hay bullet • làm khung chính.\n\n"
        "--- DỮ LIỆU GỐC ---\n" + teacher_prompt[-6500:] +
        "\n\n--- ĐÃ VIẾT ---\n" + out[-6500:]
    )


def _admin_supplement_user_prompt(
    out: str, teacher_prompt: str, missing: List[str], q: Optional[Dict[str, Any]] = None
) -> str:
    focus = ", ".join(missing) if missing else "1, 2"
    dang = effective_dang(q) if q else ""
    dang_note = ""
    if "1" in missing:
        if dang == "Đúng sai":
            dang_note = (
                " Mục 1: BẮT BUỘC 4 dòng đủ dài `A. Đúng — công thức $...$` … `D. ...`."
            )
        elif dang == "Trắc nghiệm":
            dang_note = (
                " Mục 1: BẮT BUỘC phân tích **A.** **B.** **C.** **D.** — mỗi phương án ≥1 câu lý do."
            )
        else:
            dang_note = " Mục 1: giải chi tiết có công thức $...$ và thay số."
    return (
        f"Bản ADMIN trước THIẾU hoặc cắt cụt mục: {focus}.{dang_note} "
        "Viết CHỈ phần còn thiếu, đúng tiêu đề: "
        "'1. GIẢI TỪNG Ý' (lời giải CHI TIẾT copy Sheet) và "
        "'2. CHỐT ĐÁP ÁN' (một dòng đáp án cuối). "
        "KHÔNG tóm tắt đề. KHÔNG gợi ý ngắn kiểu VIP. KHÔNG \\begin{enumerate}.\n\n"
        "--- ĐÃ VIẾT ---\n" + out[-8000:] +
        "\n\n--- DỮ LIỆU CÂU ---\n" + teacher_prompt[-4000:]
    )


def _merge_admin_continuation(base: str, more: str) -> str:
    base = clean(base)
    more = clean(more)
    if not more:
        return base
    more = re.sub(r"^\\begin\{enumerate\}[\s\S]*?(?=1\.|2\.)", "", more, flags=re.I)
    return (base.rstrip() + "\n\n" + more.lstrip()).strip()


def _finish_admin_review_text(
    txt: str,
    finish: str,
    teacher_prompt: str,
    call_fn,
    q: Optional[Dict[str, Any]] = None,
) -> str:
    """Tiếp tục + bổ sung mục thiếu cho lời giải ADMIN."""
    out = clean(txt)
    if not out:
        return out
    deadline = time.time() + AI_HINT_ADMIN_FINISH_DEADLINE_SEC
    for step in range(AI_HINT_ADMIN_MAX_CONTINUATIONS):
        if _admin_hint_complete(out, q) or time.time() >= deadline:
            break
        if not _admin_hint_needs_continuation(out, finish, q):
            break
        cont_prompt = _admin_continuation_user_prompt(out, teacher_prompt)
        more, finish, err = call_fn(cont_prompt, 55)
        if err:
            print(f"[AI_HINT][ADMIN_CONT] step={step+1} err={err[:120]}")
            break
        if not more:
            break
        out = _merge_admin_continuation(out, more)
        print(f"[AI_HINT][ADMIN_CONT] step={step+1} finish={finish}")
    for sup_step in range(2):
        if _admin_hint_complete(out, q) or time.time() >= deadline:
            break
        missing = _admin_missing_sections(out, q)
        if not missing:
            break
        sup_prompt = _admin_supplement_user_prompt(out, teacher_prompt, missing, q)
        more, finish, err = call_fn(sup_prompt, 55)
        if err:
            print(f"[AI_HINT][ADMIN_SUP] step={sup_step+1} err={err[:120]}")
            break
        if not more:
            break
        out = _merge_admin_continuation(out, more)
        print(f"[AI_HINT][ADMIN_SUP] step={sup_step+1} missing={','.join(missing)} finish={finish}")
    return out


def _finalize_admin_hint_text(txt: str) -> str:
    """ADMIN: không cắt ngắn — chỉ giới hạn an toàn rất cao."""
    txt = clean(txt)
    if len(txt) <= AI_HINT_ADMIN_MAX_CHARS:
        return txt
    return trim_ai_hint_text(txt, AI_HINT_ADMIN_MAX_CHARS)


def build_ai_admin_review_prompt_2026(q: Dict[str, Any], user_answer: Any) -> str:
    block = build_ai_question_block(q, user_answer, include_sheet_answer=True)
    sheet_da = clean(q.get("DapAn", "")) or "(trống)"
    dang = effective_dang(q)
    if dang == "Đúng sai":
        step1 = (
            "Giải CHI TIẾT và kết luận Đ/S từng ý A B C D — BẮT BUỘC đúng 4 dòng (copy vào cột R Sheet):\n"
            "`A. Đúng — giải thích + công thức $...$ + thay số` / `B. Sai — ...` / `C. ...` / `D. ...`\n"
            "Mỗi dòng ≥25 ký tự, có lý do vật lý/toán cụ thể — không viết chung chung.\n"
            "Cuối mục 1: tóm tắt 1 dòng «A=Đúng · B=Sai · C=… · D=…» theo kết luận vật lý."
        )
        step2 = (
            "Một dòng đáp án cuối — PHẢI khớp mục 1 (nếu D. Sai thì không ghi D=Đúng): "
            "`Đ,Đ,Đ,S` hoặc `A=Đúng · B=Đúng · C=Đúng · D=Sai` "
            f"(Sheet cột P đang: {sheet_da}).\n"
            "PHÂN TÍCH BẮT BUỘC: so từng ý A/B/C/D — Sheet P có khớp kết luận AI không? "
            "Cột P có khớp cột R không? Nếu lệch, ghi rõ «Ý X: Sheet sai, nên sửa P thành … / R thành …»."
        )
    elif dang == "Trắc nghiệm":
        step1 = (
            "Giải CHI TIẾT: (1) công thức $...$, thay số từ đề, tính kết quả; "
            "(2) BẮT BUỘC phân tích từng phương án **A.** **B.** **C.** **D.** — "
            "mỗi phương án ≥1 câu: vì sao đúng hoặc vì sao sai (so với kết quả tính)."
        )
        step2 = f"Một chữ A/B/C/D là đáp án đúng (Sheet cột P đang: {sheet_da})."
    elif dang == "Trả lời ngắn":
        step1 = (
            "Giải CHI TIẾT từng bước: ghi công thức $...$, thay số từ đề, "
            "biến đổi từng bước, tính ra kết quả cuối kèm đơn vị — không bỏ qua phép tính."
        )
        step2 = f"Một dòng số/biểu thức cuối (Sheet cột P đang: {sheet_da})."
    else:
        step1 = "Giải/luận CHI TIẾT từng bước đến kết quả cuối (công thức + lý luận)."
        step2 = "Một dòng kết luận đáp án."
    return "\n".join(
        [
            "ADMIN kiểm tra ngân hàng câu — phân tích Đúng/Sai từng ý, so Sheet P/R, gợi ý sửa (KHÁC gợi ý VIP ngắn).",
            "",
            gemini_prompt_brand_2026(),
            "",
            "QUAN TRỌNG: KHÔNG tóm tắt đề, KHÔNG nhắc lại đề bài, KHÔNG viết mục phụ.",
            "CHỈ 2 mục — giữ nguyên tiêu đề số:",
            "",
            "1. GIẢI TỪNG Ý",
            step1,
            "CHI TIẾT, đủ công thức $...$ — đây là lời giải copy Sheet, KHÔNG viết ngắn kiểu VIP.",
            "KHÔNG \\begin{enumerate}, KHÔNG bullet • làm khung.",
            "",
            "2. CHỐT ĐÁP ÁN",
            step2,
            "Tối đa 2–3 dòng; không viết 'cần thêm dữ kiện' nếu đề đủ số liệu.",
            "",
            "DỮ LIỆU CÂU:",
            block,
        ]
    )



def extract_ds_verdicts_from_loigiai(text: str) -> Dict[str, str]:
    """Đọc Đúng/Sai từng ý A-D trong lời giải (không dùng cột P Sheet)."""
    text = clean(text)
    if not text:
        return {}
    out: Dict[str, str] = {}
    tagged = list(
        re.finditer(
            r"(?:^|\n|[•\-\*]\s*|\(\s*)(?:\*\*)?([ABCD])\s*[\.\):]\s*(?:(Đúng|Sai)\s*[\-—:–]\s*)?",
            text,
            re.I | re.M,
        )
    )
    for m in tagged[:4]:
        letter = m.group(1).upper()
        verdict = m.group(2)
        if verdict:
            out[letter] = "Sai" if verdict.lower().startswith("s") else "Đúng"
    if len(out) >= 2:
        return out
    for m in re.finditer(
        r"(?:^|\n)\s*([ABCD])(?!\s*[\.\):])\s+(?:(Đúng|Sai)\s*[\-—:–]\s*)?",
        text,
        re.I | re.M,
    ):
        if m.group(2):
            out[m.group(1).upper()] = (
                "Sai" if m.group(2).lower().startswith("s") else "Đúng"
            )
    return out


def format_ds_dapan_from_verdicts(verdicts: Dict[str, str], q: Optional[Dict[str, Any]] = None) -> str:
    """Chuỗi đáp án P kiểu A=Đúng · B=Sai … để lưu Sheet."""
    letters = ["A", "B", "C", "D"]
    if q:
        letters = [L for L in letters if clean(q.get(L))]
    bits = [f"{L}={verdicts[L]}" for L in letters if verdicts.get(L)]
    return " · ".join(bits)


def ds_dapan_from_loigiai(loigiai: str, q: Optional[Dict[str, Any]] = None) -> str:
    """Suy cột P từ lời giải — ưu tiên hơn dòng chốt mục 2 của AI."""
    vmap = extract_ds_verdicts_from_loigiai(loigiai)
    if len(vmap) >= 2:
        return format_ds_dapan_from_verdicts(vmap, q)
    return ""


def ds_verdicts_from_dapan(dapan: Any, q: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Đọc Đúng/Sai từng ý A–D từ cột P."""
    vals = parse_tf_values(dapan)
    letters = [L for L in "ABCD" if not q or clean(q.get(L))]
    out: Dict[str, str] = {}
    for i, L in enumerate("ABCD"):
        if L not in letters:
            continue
        v = vals[i] if i < len(vals) else ""
        if v == "Đ":
            out[L] = "Đúng"
        elif v == "S":
            out[L] = "Sai"
    return out


def build_admin_review_analysis(
    q: Dict[str, Any],
    sheet_dapan: str,
    sheet_loigiai: str,
    suggested_dapan: str,
    suggested_loigiai: str,
) -> Dict[str, Any]:
    """Phân tích ADMIN: so Sheet P/R với kết luận AI — phát hiện lệch & gợi ý sửa."""
    dang = effective_dang(q)
    issues: List[str] = []
    rows: List[Dict[str, Any]] = []
    fix_loigiai = clean(suggested_loigiai)
    fix_dapan = clean(suggested_dapan)

    if dang == "Đúng sai":
        if fix_loigiai:
            fix_loigiai = normalize_ds_loigiai(fix_loigiai, q, use_sheet_dapan=False)
        dapan_from_lg = ds_dapan_from_loigiai(fix_loigiai or suggested_loigiai, q)
        if dapan_from_lg:
            fix_dapan = dapan_from_lg
        elif not fix_dapan:
            ai_v = extract_ds_verdicts_from_loigiai(fix_loigiai or suggested_loigiai)
            if len(ai_v) >= 2:
                fix_dapan = format_ds_dapan_from_verdicts(ai_v, q)

        sheet_p = ds_verdicts_from_dapan(sheet_dapan, q)
        sheet_r = extract_ds_verdicts_from_loigiai(sheet_loigiai)
        ai_v = extract_ds_verdicts_from_loigiai(fix_loigiai or suggested_loigiai)
        if len(ai_v) < 2:
            ai_v = ds_verdicts_from_dapan(fix_dapan or suggested_dapan, q)

        letters = [L for L in "ABCD" if clean(q.get(L))]
        dapan_match = True
        loigiai_match = True
        p_r_consistent = True

        for L in letters:
            sp = sheet_p.get(L, "")
            ar = sheet_r.get(L, "")
            av = ai_v.get(L, "")
            p_r_ok = not sp or not ar or sp == ar
            ai_ok = not sp or not av or sp == av
            if sp and av and sp != av:
                dapan_match = False
                issues.append(f"Ý {L}: Sheet P={sp} · AI={av}")
            if sp and ar and sp != ar:
                p_r_consistent = False
                loigiai_match = False
                issues.append(f"Ý {L}: cột P ({sp}) lệch cột R ({ar})")
            if av and ar and av != ar:
                loigiai_match = False
                issues.append(f"Ý {L}: AI lời giải ({ar}) lệch kết luận AI ({av})")
            note_parts: List[str] = []
            if sp and av and sp != av:
                note_parts.append(f"Sửa P→{av}")
            if sp and ar and sp != ar:
                note_parts.append(f"Sửa R→{av or ar}")
            rows.append(
                {
                    "letter": L,
                    "sheet_p": sp or "—",
                    "sheet_r": ar or "—",
                    "ai": av or "—",
                    "ok": ai_ok and p_r_ok,
                    "p_r_ok": p_r_ok,
                    "note": " · ".join(note_parts),
                }
            )

        all_ok = dapan_match and p_r_consistent and (not issues)
        if all_ok and sheet_p and len(ai_v) >= 2:
            summary = "✅ Sheet P/R khớp kết luận AI từng ý A–D."
        elif not sheet_p and ai_v:
            summary = "⚠️ Sheet chưa có đáp án P — AI đề xuất ghi cột P và R bên dưới."
            all_ok = False
        elif issues:
            summary = f"⚠️ Phát hiện {len(issues)} điểm lệch — nên sửa Sheet theo AI."
        else:
            summary = "Chưa đủ dữ liệu so khớp — xem lời giải AI mục 1."

        return {
            "dang": dang,
            "all_ok": all_ok,
            "dapan_match": dapan_match,
            "loigiai_match": loigiai_match,
            "p_r_consistent": p_r_consistent,
            "rows": rows,
            "issues": issues,
            "fix_dapan": fix_dapan,
            "fix_loigiai": fix_loigiai,
            "summary": summary,
        }

    sheet_da = clean(sheet_dapan)
    ai_da = clean(fix_dapan or suggested_dapan)
    dapan_match = True
    if sheet_da and ai_da and key_norm(sheet_da) != key_norm(ai_da):
        dapan_match = False
        issues.append(f"Đáp án P Sheet ({sheet_da}) khác AI ({ai_da})")
        fix_dapan = ai_da
    elif not fix_dapan:
        fix_dapan = sheet_da

    loigiai_match = True
    sheet_lg = clean(sheet_loigiai)
    ai_lg = clean(fix_loigiai or suggested_loigiai)
    if sheet_lg and ai_lg and key_norm(sheet_lg) != key_norm(ai_lg):
        loigiai_match = False
        issues.append("Lời giải R Sheet khác đề xuất AI")
        fix_loigiai = ai_lg
    elif not fix_loigiai:
        fix_loigiai = sheet_lg

    all_ok = dapan_match and loigiai_match and not issues
    if all_ok:
        summary = "✅ Sheet P/R khớp AI."
    elif issues:
        summary = f"⚠️ {' · '.join(issues)}"
    else:
        summary = "Xem đề xuất AI bên dưới."

    return {
        "dang": dang,
        "all_ok": all_ok,
        "dapan_match": dapan_match,
        "loigiai_match": loigiai_match,
        "p_r_consistent": True,
        "rows": rows,
        "issues": issues,
        "fix_dapan": fix_dapan,
        "fix_loigiai": fix_loigiai,
        "summary": summary,
    }


def normalize_ds_loigiai(
    text: str, q: Optional[Dict[str, Any]] = None, use_sheet_dapan: bool = True
) -> str:
    """Chuẩn hóa lời giải Đ/S: A. Đúng — giải thích (mỗi ý một dòng)."""
    text = clean(text)
    if not text:
        return ""
    tagged = list(
        re.finditer(
            r"(?:^|\n|[•\-\*]\s*|\(\s*)(?:\*\*)?([ABCD])\s*[\.\):]\s*(?:(Đúng|Sai)\s*[\-—:–]\s*)?",
            text,
            re.I | re.M,
        )
    )
    if not tagged:
        line_hits = list(
            re.finditer(
                r"(?:^|\n)\s*([ABCD])(?!\s*[\.\):])\s+(?:(Đúng|Sai)\s*[\-—:–]\s*)?(.+?)\s*$",
                text,
                re.I | re.M,
            )
        )
        if line_hits:
            dap_map2: Dict[str, str] = {}
            if q and use_sheet_dapan:
                da = clean(q.get("DapAn", ""))
                compact = re.sub(r"[^DSĐđ]", "", da.upper().replace("Đ", "D"))
                for i, c in enumerate(compact[:4]):
                    dap_map2[["A", "B", "C", "D"][i]] = "Sai" if c == "S" else "Đúng"
            lines2: List[str] = []
            for m in line_hits[:4]:
                letter = m.group(1).upper()
                verdict = m.group(2)
                body = clean(m.group(3)).strip(" ).\n")
                body = re.sub(r"\*\*", "", body)
                if verdict:
                    vl = "Sai" if verdict.lower().startswith("s") else "Đúng"
                else:
                    vl = dap_map2.get(letter, "")
                if vl:
                    lines2.append(f"{letter}. {vl} — {body}" if body else f"{letter}. {vl}")
                elif body:
                    lines2.append(f"{letter}. — {body}")
            if lines2:
                return "\n".join(lines2)
        return text
    dap_map: Dict[str, str] = {}
    if q and use_sheet_dapan:
        da = clean(q.get("DapAn", ""))
        parts = re.findall(r"([ABCD])\s*[=:\-]\s*(Đúng|Sai|Đ|S)", da, re.I)
        if parts:
            for letter, v in parts:
                dap_map[letter.upper()] = "Sai" if str(v).upper() in ("S", "SAI") else "Đúng"
        else:
            compact = re.sub(r"[^DSĐđ]", "", da.upper().replace("Đ", "D"))
            for i, c in enumerate(compact[:4]):
                dap_map[["A", "B", "C", "D"][i]] = "Sai" if c == "S" else "Đúng"
    lines: List[str] = []
    for i, m in enumerate(tagged[:4]):
        letter = m.group(1).upper()
        verdict = m.group(2)
        if verdict:
            vl = "Sai" if verdict.lower().startswith("s") else "Đúng"
        else:
            vl = dap_map.get(letter, "")
        start = m.end()
        end = tagged[i + 1].start() if i + 1 < len(tagged) else len(text)
        body = clean(text[start:end]).strip(" ).\n")
        body = re.sub(r"\*\*", "", body)
        if vl:
            lines.append(f"{letter}. {vl} — {body}" if body else f"{letter}. {vl}")
        elif body:
            lines.append(f"{letter}. — {body}")
    return "\n".join(lines) if lines else text


def parse_admin_ai_suggestions(ai_text: str) -> Dict[str, str]:
    """Tách đáp án / lời giải đề xuất từ bản ADMIN AI kiểm tra."""
    body = str(ai_text or "").split("📋 Tham chiếu Sheet")[0].strip()
    dapan = ""
    loigiai = ""
    # Format mới: 2 bước
    body1 = _admin_section_body(body, "1")
    body2 = _admin_section_body(body, "2")
    if body1:
        loigiai = body1
    if body2:
        block = clean(body2)
        if re.search(r"[ABCD]\s*[:：=]", block, re.I):
            dapan = block.splitlines()[0].strip()
        else:
            lines = [re.sub(r"^[-•*]\s*", "", x.strip()) for x in block.splitlines() if clean(x)]
            if lines:
                dapan = lines[0]
                dapan = re.sub(r"^(đáp án|kết luận)\s*[:：\-]\s*", "", dapan, flags=re.I).strip()
    if loigiai:
        dapan_from_lg = ds_dapan_from_loigiai(loigiai)
        if dapan_from_lg:
            dapan = dapan_from_lg
    if loigiai and dapan:
        return {"suggested_dapan": dapan, "suggested_loigiai": loigiai}
    # Legacy 8 mục
    m2 = re.search(
        r"5\.\s*ĐÁP ÁN AI KẾT LUẬN\s*(.*?)(?=6\.\s*SO KHỚP|\Z)",
        body,
        re.I | re.S,
    )
    if m2:
        block = clean(m2.group(1))
        if re.search(r"[ABCD]\s*[:：=]", block, re.I):
            dapan = block
        else:
            lines = [re.sub(r"^[-•*]\s*", "", x.strip()) for x in block.splitlines() if clean(x)]
            if lines:
                dapan = lines[-1]
                dapan = re.sub(r"^(đáp án|kết luận)\s*[:：\-]\s*", "", dapan, flags=re.I).strip()
    m5 = re.search(r"8\.\s*ĐỀ XUẤT LỜI GIẢI[^\n]*\n(.*)", body, re.I | re.S)
    if m5:
        lg = clean(m5.group(1))
        if lg and "giữ nguyên lời giải sheet" not in lg.lower():
            loigiai = lg
    if not loigiai:
        lg4 = _admin_section_body(body, "4")
        if lg4:
            loigiai = lg4
    if loigiai and not dapan:
        dapan = ds_dapan_from_loigiai(loigiai)
    return {"suggested_dapan": dapan, "suggested_loigiai": loigiai}


def _vip_section_body(txt: str, section: str) -> str:
    markers = {
        "1": (r"1\.\s*PHƯƠNG HƯỚNG LÀM BÀI[^\n]*\n", r"2\.\s"),
        "2": (r"2\.\s*KẾT QUẢ CUỐI[^\n]*\n", r"\Z"),
    }
    spec = markers.get(section)
    if not spec:
        return ""
    m = re.search(spec[0] + r"(.*?)(?=" + spec[1] + r"|\Z)", txt, re.I | re.S)
    return clean(m.group(1)) if m else ""


def _vip_hint_complete(txt: str) -> bool:
    txt = clean(txt)
    if not txt:
        return False
    if not re.search(r"1\.\s*PHƯƠNG HƯỚNG LÀM BÀI", txt, re.I):
        return False
    if not re.search(r"2\.\s*KẾT QUẢ CUỐI", txt, re.I):
        return False
    body1 = _vip_section_body(txt, "1")
    body2 = _vip_section_body(txt, "2")
    return len(body1) >= 12 and bool(body2.strip())


def parse_vip_ai_suggestions(ai_text: str) -> Dict[str, str]:
    """Tách phương hướng + kết quả cuối từ gợi ý VIP."""
    body = str(ai_text or "").split("📋 Tham chiếu Sheet")[0].strip()
    huong = _vip_section_body(body, "1")
    dapan_raw = _vip_section_body(body, "2")
    dapan = ""
    if dapan_raw:
        block = clean(dapan_raw)
        lines = [re.sub(r"^[-•*]\s*", "", x.strip()) for x in block.splitlines() if clean(x)]
        if lines:
            dapan = lines[0]
            dapan = re.sub(r"^(đáp án|kết quả)\s*[:：\-]\s*", "", dapan, flags=re.I).strip()
    return {"suggested_dapan": dapan, "suggested_huong": huong}


def build_ai_vip_hint_prompt_2026(q: Dict[str, Any], user_answer: Any) -> str:
    block = build_ai_question_block(q, user_answer, include_sheet_answer=False)
    dang = effective_dang(q)
    if dang == "Đúng sai":
        step1 = (
            "Ghi công thức/bước xét chung (2–4 bước, có $...$). "
            "KHÔNG giải riêng từng ý A B C D, KHÔNG bullet dài từng phương án."
        )
        step2 = "Một dòng: `Đ,S,S,Đ` hoặc `A=Đúng, B=Sai, C=Sai, D=Đúng`."
    elif dang == "Trắc nghiệm":
        step1 = (
            "Công thức đã thay số từ đề + 2–4 bước tính. "
            "KHÔNG phân tích riêng A B C D từng phương án."
        )
        step2 = "Một chữ A/B/C/D."
    elif dang == "Trả lời ngắn":
        step1 = "Công thức $...$ + các bước thay số (ngắn gọn)."
        step2 = "Một dòng số/biểu thức kèm đơn vị."
    else:
        step1 = "Phương hướng/luận giải ngắn (2–4 ý)."
        step2 = "Kết luận một dòng."
    return "\n".join(
        [
            "VIP/SVIP — gợi ý NGẮN, tiết kiệm token.",
            "",
            gemini_prompt_brand_2026(),
            "",
            "KHÔNG tóm tắt đề dài. KHÔNG giải từng phương án A/B/C/D.",
            "CHỈ 2 mục (giữ nguyên tiêu đề):",
            "",
            "1. PHƯƠNG HƯỚNG LÀM BÀI",
            step1,
            "Tối đa 80–120 từ. LaTeX trong $...$ một dòng.",
            "",
            "2. KẾT QUẢ CUỐI",
            step2,
            "",
            "DỮ LIỆU CÂU:",
            block,
        ]
    )


def _admin_hint_payload(
    index: int,
    hint: str,
    correct_sheet: str,
    sheet_dapan: str,
    sheet_loigiai: str,
    q: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    sug = parse_admin_ai_suggestions(hint)
    if q and effective_dang(q) == "Đúng sai" and sug.get("suggested_loigiai"):
        sug["suggested_loigiai"] = normalize_ds_loigiai(
            sug["suggested_loigiai"], q, use_sheet_dapan=False
        )
        dapan_sync = ds_dapan_from_loigiai(sug["suggested_loigiai"], q)
        if dapan_sync:
            sug["suggested_dapan"] = dapan_sync
    if not sug.get("suggested_dapan") and correct_sheet:
        sug["suggested_dapan"] = correct_sheet
    if not sug.get("suggested_loigiai") and sheet_loigiai:
        sug["suggested_loigiai"] = sheet_loigiai
    body_only = str(hint or "").split("📋 Tham chiếu Sheet")[0]
    analysis = build_admin_review_analysis(
        q or {},
        sheet_dapan,
        sheet_loigiai,
        sug.get("suggested_dapan", ""),
        sug.get("suggested_loigiai", ""),
    )
    if analysis.get("fix_dapan"):
        sug["suggested_dapan"] = analysis["fix_dapan"]
    if analysis.get("fix_loigiai"):
        sug["suggested_loigiai"] = analysis["fix_loigiai"]
    return {
        "index": index,
        "exact": True,
        "show_answer": True,
        "admin_review": True,
        "hint": hint,
        "hint_truncated": not _admin_hint_complete(body_only, q),
        "correct": correct_sheet,
        "sheet_dapan": sheet_dapan,
        "sheet_loigiai": sheet_loigiai,
        "suggested_dapan": sug.get("suggested_dapan", ""),
        "suggested_loigiai": sug.get("suggested_loigiai", ""),
        "admin_analysis": analysis,
        **extra,
    }


def build_ai_teacher_prompt_2026(q: Dict[str, Any], user_answer: Any) -> str:
    block = build_ai_question_block(q, user_answer, include_sheet_answer=False)
    dang = effective_dang(q)
    dang_note = {
        "Trắc nghiệm": "Gợi ý hướng chọn, không phân tích hết A-D.",
        "Đúng sai": "Gợi ý cách xét nhanh từng ý, không viết bài luận.",
        "Trả lời ngắn": "Nêu công thức + hướng thay số, không tính hết chi tiết.",
        "Tự luận": "Nêu 2–3 bước chính, không viết lời giải đầy đủ.",
    }.get(dang, "Gợi ý ngắn, súc tích.")
    return "\n".join(
        [
            "Viết GỢI Ý NGẮN cho học sinh đang làm câu này (KHÔNG viết bài giải dài).",
            "",
            gemini_prompt_brand_2026(),
            "",
            "QUY TẮC:",
            f"- Tối đa 4–5 dòng bullet, khoảng 80–120 từ.",
            f"- {dang_note}",
            "- Dòng 1: nhận dạng dạng bài.",
            "- Dòng 2: công thức / kiến thức then chốt.",
            "- Dòng 3–4: bước làm tiếp theo hoặc mẹo tránh sai.",
            "- Không lặp lại nguyên đề bài.",
            "- Không nêu thẳng đáp án cuối (chữ A/B/C/D hoặc số kết quả).",
            "- Không kết thúc bằng chữ ký / Zalo.",
            "",
            "DỮ LIỆU CÂU:",
            block,
        ]
    )


def build_ai_vip_formula_prompt_2026(q: Dict[str, Any], user_answer: Any) -> str:
    block = build_ai_question_block(q, user_answer, include_sheet_answer=False)
    dang = effective_dang(q)
    dang_note = {
        "Trắc nghiệm": (
            "Đã thay số từ phương trình đề vào công thức; hướng so từng phương án A–D "
            "với vectơ tính được — KHÔNG nói «đáp án là B»."
        ),
        "Đúng sai": "Cách xét từng ý với số từ đề — không chốt Đ/S cuối.",
        "Trả lời ngắn": "Công thức đã thay số, chỉ thiếu bước tính nhỏ cuối.",
        "Tự luận": "Định nghĩa + công thức đã thay số + 3 bước.",
    }.get(dang, "Công thức đã thay số từ đề.")
    return "\n".join(
        [
            "Viết GỢI Ý VIP/SVIP — em chỉ việc đọc số và chọn, KHÔNG ghi đáp án cuối (A/B/C/D).",
            "",
            gemini_prompt_brand_2026(),
            "",
            "Cấu trúc bắt buộc (giữ tiêu đề bullet):",
            "- ĐỀ: 1–2 câu, giữ số liệu/phương trình trong đề.",
            "- ĐỊNH NGHĨA: khái niệm then chốt (1–2 câu).",
            "- CÔNG THỨC: viết công thức tổng quát VÀ bản đã THAY SỐ từ đề (vd mặt phẳng $ax+by+cz+d=0$ → thay $a,b,c,d$ bằng số trong đề; vectơ pháp tuyến $\\vec{n}=(a;b;c)$ → thay số cụ thể).",
            "- CÁCH LÀM: 2–4 bước (đọc hệ số → tính $\\vec{n}$ → so khớp từng phương án).",
            "- LƯU Ý: 1 mẹo tránh sai.",
            "",
            "QUY TẮC LaTeX:",
            "- Mỗi công thức trong $...$ trên MỘT dòng, không để trống giữa hai dấu $.",
            "- Dùng $\\vec{n}$ hoặc $\\overrightarrow{n}$, $\\dfrac{}{}$ nếu cần.",
            "",
            "QUY TẮC nội dung:",
            f"- {dang_note}",
            "- Khoảng 120–180 từ.",
            "- TUYỆT ĐỐI KHÔNG: kết luận «đáp án là A/B/C/D», «chọn B», kết quả số cuối.",
            "- App sẽ tự loại 2 đáp án sai (50-50) sau gợi ý — không cần em nêu đáp án đúng.",
            "",
            "DỮ LIỆU CÂU:",
            block,
        ]
    )


def build_ai_similar_question_prompt(q: Dict[str, Any]) -> str:
    block = build_ai_question_block(q, "", include_sheet_answer=False)
    dang = effective_dang(q)
    dang_fmt = {
        "Trắc nghiệm": (
            "Viết đủ 4 phương án A, B, C, D (mỗi phương án một dòng). "
            "Cuối cùng ghi rõ đáp án đúng (A/B/C/D)."
        ),
        "Đúng sai": (
            "Viết 4 ý a), b), c), d) — mỗi ý một dòng. "
            "Cuối cùng ghi đáp án dạng Đ,S,Đ,S hoặc tương đương."
        ),
        "Trả lời ngắn": "Cuối cùng ghi đáp án số/kết quả rõ ràng (có đơn vị nếu cần).",
        "Tự luận": "Cuối cùng ghi đáp án / kết quả chính và tóm tắt lời giải.",
    }.get(dang, "Cuối cùng ghi đáp án rõ ràng.")
    return "\n".join(
        [
            "Tạo MỘT câu hỏi TƯƠNG TỰ câu gốc: cùng dạng bài, cùng chủ đề kiến thức, "
            "nhưng ĐỔI số liệu / tình huống / phương trình (không copy y nguyên).",
            "",
            gemini_prompt_brand_2026(),
            "",
            "Cấu trúc bắt buộc (giữ tiêu đề số):",
            "1. CÂU HỎI MỚI — nội dung đề (giữ mức độ tương đương)",
            "2. CÁC LỰA CHỌN — phù hợp dạng bài (TN: A-D; Đ/S: 4 ý; TLN: bỏ qua nếu không cần)",
            "3. ĐÁP ÁN — kết quả cuối rõ ràng",
            "4. LỜI GIẢI — 4–8 bước ngắn gọn, có công thức LaTeX",
            "",
            "QUY TẮC LaTeX (MathJax):",
            "- Mọi công thức trong $...$ trên MỘT dòng, không để trống giữa hai dấu $.",
            "- Dùng $\\vec{v}$, $\\dfrac{}{}$, $\\sin$, $\\cos$ khi cần.",
            "",
            f"Dạng bài gốc: {dang}. {dang_fmt}",
            "- Khoảng 150–350 từ.",
            "- Không kết thúc bằng chữ ký / Zalo.",
            "",
            "CÂU GỐC (tham khảo, không copy):",
            block,
        ]
    )


def ai_similar_question_from_provider(q: Dict[str, Any]) -> Tuple[str, int, str, str]:
    cfg = ai_runtime_config()
    openai_keys = load_ai_keys("OPENAI")
    gemini_keys = load_ai_keys("GEMINI")
    provider = cfg["provider"]
    last_error = ""
    max_tokens = AI_HINT_SIMILAR_MAX_OUTPUT_TOKENS
    max_chars = AI_HINT_SIMILAR_MAX_CHARS
    model_openai = clean(os.environ.get("OPENAI_HINT_MODEL", DEFAULT_OPENAI_HINT_MODEL)).strip() or DEFAULT_OPENAI_HINT_MODEL
    model_gemini = clean(os.environ.get("GEMINI_HINT_MODEL", DEFAULT_GEMINI_HINT_MODEL)).strip() or DEFAULT_GEMINI_HINT_MODEL
    gemini_models = [model_gemini] + [m for m in GEMINI_HINT_MODEL_FALLBACKS if m != model_gemini]
    sys_prompt = (
        "Bạn là giáo viên Vật lý/Toán. Tạo câu hỏi luyện tập tương tự câu gốc. "
        "Trả lời tiếng Việt, có đáp án và lời giải. LaTeX trong $...$ một dòng."
    )
    teacher_prompt = build_ai_similar_question_prompt(q)
    temp = 0.35

    def _postprocess(raw: str) -> str:
        return trim_ai_hint_text(sanitize_hint_math_text(clean(raw)), max_chars)

    def try_openai() -> Tuple[str, int, str, str]:
        nonlocal last_error
        body = {
            "model": model_openai,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": teacher_prompt},
            ],
            "temperature": temp,
            "max_tokens": max_tokens,
        }
        for idx, api_key in enumerate(openai_keys, start=1):
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                txt = _postprocess(
                    (((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content", "")
                )
                if txt:
                    print(f"[AI_SIMILAR][OPENAI] using key #{idx}")
                    return txt, idx, "OPENAI", ""
            except Exception as e:
                last_error = _http_error_message(e)
                if _is_quota_or_rate_error(last_error):
                    break
                continue
        return "", 0, "OPENAI", last_error

    def try_gemini() -> Tuple[str, int, str, str]:
        nonlocal last_error
        for idx, api_key in enumerate(gemini_keys, start=1):
            for gmodel in gemini_models:
                txt, finish, err = _gemini_hint_call(
                    api_key, gmodel, sys_prompt, teacher_prompt, max_tokens, temp, timeout=28
                )
                if err:
                    last_error = err
                    if _is_quota_or_rate_error(last_error):
                        break
                    continue
                txt = _postprocess(txt)
                if txt:
                    print(f"[AI_SIMILAR][GEMINI] model={gmodel} key=#{idx} finish={finish}")
                    return txt, idx, "GEMINI", ""
        return "", 0, "GEMINI", last_error

    txt, idx, used_provider, err = "", 0, provider, ""
    if provider == "OPENAI":
        txt, idx, used_provider, err = try_openai()
    elif provider == "GEMINI":
        txt, idx, used_provider, err = try_gemini()
    else:
        if gemini_keys:
            txt, idx, used_provider, err = try_gemini()
            if not txt:
                txt, idx, used_provider, err = try_openai()
        else:
            txt, idx, used_provider, err = try_openai()

    if txt:
        return txt, idx, used_provider, ""
    fallback = (
        f"⚠️ Chưa gọi được AI ({err or 'không phản hồi'}).\n\n"
        f"Thử lại sau hoặc kiểm tra key AI.\n\n"
        f"Câu gốc ({effective_dang(q)}): {clean(q.get('CauHoi', ''))[:200]}…"
    )
    return fallback, 0, "FALLBACK", err or last_error


def _is_quota_or_rate_error(msg: str) -> bool:
    m = clean(msg).lower()
    return any(
        x in m
        for x in [
            "quota",
            "rate limit",
            "rate_limit",
            "resource_exhausted",
            "exceeded your current",
            "429",
            "too many requests",
        ]
    )


def _http_error_message(e: Exception) -> str:
    try:
        body = ""
        if hasattr(e, "read"):
            body = e.read().decode("utf-8", errors="ignore")
        elif getattr(e, "fp", None):
            body = e.fp.read().decode("utf-8", errors="ignore")  # type: ignore
        if body:
            try:
                j = json.loads(body)
                msg = clean(((j or {}).get("error") or {}).get("message") or "")
                if msg:
                    return msg[:220]
            except Exception:
                pass
            return clean(body)[:220]
    except Exception:
        pass
    return clean(str(e))[:220]


def _gemini_hint_call(
    api_key: str,
    gmodel: str,
    sys_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temp: float,
    timeout: int = 22,
) -> Tuple[str, str, str]:
    """Gọi Gemini một lần. Trả về (text, finish_reason, error)."""
    body = {
        "contents": [{"parts": [{"text": sys_prompt}, {"text": user_prompt}]}],
        "generationConfig": {"temperature": temp, "maxOutputTokens": max_tokens},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{gmodel}:generateContent"
        f"?key={urllib.parse.quote(api_key)}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        cands = (data or {}).get("candidates") or []
        cand0 = cands[0] if cands else {}
        parts = ((cand0.get("content") or {}).get("parts") or [])
        txt = ""
        if parts and isinstance(parts[0], dict):
            txt = clean(parts[0].get("text", ""))
        finish = clean(cand0.get("finishReason", ""))
        return txt, finish, ""
    except Exception as e:
        return "", "", _http_error_message(e)


def _openai_chat_call(
    api_key: str,
    model: str,
    sys_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temp: float,
    timeout: int = 45,
) -> Tuple[str, str, str]:
    """Gọi OpenAI chat một lần. Trả về (text, finish_reason, error)."""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temp,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        choice = ((data or {}).get("choices") or [{}])[0]
        txt = clean(((choice.get("message") or {}).get("content") or ""))
        finish = clean(choice.get("finish_reason") or "")
        return txt, finish, ""
    except Exception as e:
        return "", "", _http_error_message(e)



def ai_hint_from_provider(
    q: Dict[str, Any],
    user_answer: Any,
    admin_review: bool = False,
    vip_formula_only: bool = False,
    vip_short: bool = False,
) -> Tuple[str, int, str, str]:

    cfg = ai_runtime_config()
    openai_keys = load_ai_keys("OPENAI")
    gemini_keys = load_ai_keys("GEMINI")
    provider = cfg["provider"]
    last_error = ""
    if admin_review:
        max_tokens = AI_HINT_ADMIN_MAX_OUTPUT_TOKENS
        max_chars = AI_HINT_ADMIN_MAX_CHARS
    elif vip_short or vip_formula_only:
        max_tokens = AI_HINT_VIP_MAX_OUTPUT_TOKENS
        max_chars = AI_HINT_VIP_MAX_CHARS
    else:
        max_tokens = AI_HINT_MAX_OUTPUT_TOKENS
        max_chars = AI_HINT_MAX_CHARS

    model_openai = clean(os.environ.get("OPENAI_HINT_MODEL", DEFAULT_OPENAI_HINT_MODEL)).strip() or DEFAULT_OPENAI_HINT_MODEL
    model_gemini = clean(os.environ.get("GEMINI_HINT_MODEL", DEFAULT_GEMINI_HINT_MODEL)).strip() or DEFAULT_GEMINI_HINT_MODEL
    if admin_review:
        admin_model = (
            clean(os.environ.get("GEMINI_ADMIN_MODEL", DEFAULT_GEMINI_ADMIN_MODEL)).strip()
            or DEFAULT_GEMINI_ADMIN_MODEL
        )
        gemini_models_raw = [admin_model, model_gemini] + GEMINI_HINT_MODEL_FALLBACKS
    else:
        gemini_models_raw = [model_gemini] + GEMINI_HINT_MODEL_FALLBACKS
    seen_models: set = set()
    gemini_models: List[str] = []
    for m in gemini_models_raw:
        if m and m not in seen_models:
            seen_models.add(m)
            gemini_models.append(m)
    if admin_review:
        sys_prompt = (
            "Bạn là chuyên gia Vật lý/Toán kiểm tra ngân hàng câu hỏi. Trả lời tiếng Việt. "
            "ADMIN viết lời giải CHI TIẾT từng ý/phương án — KHÁC hoàn toàn gợi ý VIP ngắn. "
            "CHỈ 2 mục: 1. GIẢI TỪNG Ý (lời giải copy Sheet) và 2. CHỐT ĐÁP ÁN. "
            "Đ/S: mục 1 bắt buộc 4 dòng A. Đúng — ... B. Sai — ... C. ... D. ... đủ công thức. "
            "TN: mục 1 bắt buộc phân tích **A.** **B.** **C.** **D.** từng phương án. "
            "KHÔNG tóm tắt đề, KHÔNG nhắc lại đề bài, KHÔNG viết thêm mục phụ. "
            "Không dùng \\begin{enumerate}, \\item hay bullet • làm khung — chỉ tiêu đề 1. và 2."
        )
        teacher_prompt = build_ai_admin_review_prompt_2026(q, user_answer)
        temp = 0.1
    elif vip_short:
        sys_prompt = (
            "Bạn là trợ giảng VIP. Trả lời tiếng Việt, NGẮN GỌN. "
            "CHỈ 2 mục: 1. PHƯƠNG HƯỚNG LÀM BÀI và 2. KẾT QUẢ CUỐI. "
            "KHÔNG giải từng phương án A/B/C/D. KHÔNG tóm tắt đề dài. "
            "LaTeX trong $...$ một dòng."
        )
        teacher_prompt = build_ai_vip_hint_prompt_2026(q, user_answer)
        temp = 0.12
    elif vip_formula_only:
        sys_prompt = (
            "Bạn là trợ giảng VIP. Trả lời tiếng Việt: nhắc đề, định nghĩa, "
            "công thức ĐÃ THAY SỐ từ đề bài, các bước so khớp phương án. "
            "Không nêu đáp án A/B/C/D cuối. LaTeX trong $...$ một dòng, không để trống."
        )
        teacher_prompt = build_ai_vip_formula_prompt_2026(q, user_answer)
        temp = 0.12
    else:
        sys_prompt = (
            "Bạn là trợ giảng luyện đề. Trả lời tiếng Việt, NGẮN GỌN (4–5 dòng), "
            "chỉ gợi ý hướng làm — không viết bài giải dài, không đáp án cuối."
        )
        teacher_prompt = build_ai_teacher_prompt_2026(q, user_answer)
        temp = 0.15

    def _postprocess_hint_text(raw: str) -> str:
        raw = clean(raw)
        if admin_review:
            return _finalize_admin_hint_text(raw)
        return trim_ai_hint_text(raw, max_chars)

    def _continue_admin_gemini(txt: str, finish: str, api_key: str, gmodel: str) -> str:
        nonlocal last_error

        def call_fn(user_prompt: str, timeout: int) -> Tuple[str, str, str]:
            return _gemini_hint_call(
                api_key, gmodel, sys_prompt, user_prompt, max_tokens, temp, timeout=timeout
            )

        return _finish_admin_review_text(txt, finish, teacher_prompt, call_fn, q)

    def _continue_admin_openai(txt: str, finish: str, api_key: str, omodel: str) -> str:
        nonlocal last_error

        def call_fn(user_prompt: str, timeout: int) -> Tuple[str, str, str]:
            return _openai_chat_call(
                api_key, omodel, sys_prompt, user_prompt, max_tokens, temp, timeout=timeout
            )

        return _finish_admin_review_text(txt, finish, teacher_prompt, call_fn, q)

    def try_openai() -> Tuple[str, int, str, str]:
        nonlocal last_error
        oa_timeout = 70 if admin_review else 18
        for idx, api_key in enumerate(openai_keys, start=1):
            txt, finish, err = _openai_chat_call(
                api_key, model_openai, sys_prompt, teacher_prompt, max_tokens, temp, timeout=oa_timeout
            )
            if err:
                last_error = err
                if _is_quota_or_rate_error(last_error):
                    print(f"[AI_HINT][OPENAI] key #{idx} quota/rate — thử key tiếp")
                    break
                continue
            if not txt:
                continue
            if admin_review:
                txt = _continue_admin_openai(txt, finish, api_key, model_openai)
            txt = _postprocess_hint_text(clean(txt))
            if txt:
                tag = "ADMIN_REVIEW" if admin_review else "OPENAI"
                print(f"[AI_HINT][{tag}] using key #{idx}")
                return txt, idx, "OPENAI", ""
        return "", 0, "OPENAI", last_error

    def try_gemini() -> Tuple[str, int, str, str]:
        nonlocal last_error
        gem_timeout = 70 if admin_review else 22
        for idx, api_key in enumerate(gemini_keys, start=1):
            for gmodel in gemini_models:
                txt, finish, err = _gemini_hint_call(
                    api_key, gmodel, sys_prompt, teacher_prompt, max_tokens, temp, timeout=gem_timeout
                )
                if err:
                    last_error = err
                    if _is_quota_or_rate_error(last_error):
                        print(f"[AI_HINT][GEMINI] key #{idx} quota/rate — thử key tiếp")
                        break
                    continue
                if not txt:
                    continue
                if admin_review:
                    txt = _continue_admin_gemini(txt, finish, api_key, gmodel)
                txt = _postprocess_hint_text(txt)
                if txt:
                    tag = "ADMIN_REVIEW" if admin_review else "GEMINI"
                    print(f"[AI_HINT][{tag}] model={gmodel} key=#{idx} finish={finish}")
                    return txt, idx, "GEMINI", ""
        return "", 0, "GEMINI", last_error

    txt, idx, used_provider, err = "", 0, provider, ""
    if provider == "OPENAI":
        txt, idx, used_provider, err = try_openai()
    elif provider == "GEMINI":
        txt, idx, used_provider, err = try_gemini()
    else:
        if gemini_keys:
            txt, idx, used_provider, err = try_gemini()
            if not txt:
                txt, idx, used_provider, err = try_openai()
        else:
            txt, idx, used_provider, err = try_openai()

    if txt:
        return txt, idx, used_provider, ""
    return ai_hint_fallback(q, user_answer), 0, "FALLBACK", err or last_error

STORE: Optional[SheetStore] = None

def get_store(force_reload: bool = False) -> SheetStore:
    global STORE
    if STORE is None:
        STORE = SheetStore()
    if force_reload:
        STORE.ensure_questions_loaded(force=True)
    return STORE


def current_user_public() -> Dict[str, Any]:
    refresh_session_role_from_store()
    cfg = ai_runtime_config()
    role = norm_role(session.get("role", ""))
    profile = classify_user_ai_profile(cfg)
    return {
        "mahs": session.get("mahs", ""),
        "hoten": session.get("hoten", ""),
        "lop": session.get("lop", ""),
        "role": role,
        "is_admin": is_admin(),
        "is_trial": is_trial(),
        "is_vip": role in ["VIP", "S.VIP"],
        "can_5050": can_use_5050(),
        "can_submit_score": not is_trial(),
        "can_ai_hint": can_use_ai_hint(),
        "can_view_solution_live": can_view_solution_live(),
        "can_save_own_ai_key": can_save_own_ai_key(),
        "ai_has_keys": bool(cfg.get("has_keys")),
        "ai_using_user_keys": bool(cfg.get("using_user_keys")),
        "ai_user_gemini_keys": int(cfg.get("user_gemini_keys") or 0),
        "trial_until": session.get("trial_until", ""),
        "account_until": session.get("account_until", ""),
        **profile,
    }


def catalog_find_by_made(store: Any, made: str) -> Optional[Dict[str, Any]]:
    m = clean(made)
    for x in store.catalog:
        if clean(x.get("MaDe")) == m:
            return x
    return None


def exam_display_title(item: Optional[Dict[str, Any]]) -> str:
    """Cùng format tiêu đề khi làm bài: Vật lý - Lớp 10 | Bài 1. ..."""
    if not item:
        return "Luyện đề Vật lý - Toán học"
    mon = clean(item.get("Mon"))
    lop = clean(item.get("Lop"))
    bai = clean(item.get("BaiHoc") or item.get("De") or "Đề luyện tập")
    if mon:
        head = f"{mon} - Lớp {lop}" if lop else mon
        return f"{head} | {bai}"
    if lop:
        return f"Lớp {lop} | {bai}"
    return bai


def exam_share_preview_text(item: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    if not item:
        return "Luyện đề Vật lý - Toán học", "Đăng nhập để làm bài luyện tập trực tuyến."
    og_title = exam_display_title(item)
    socau = int(item.get("SoCau") or 0)
    chuong = clean(item.get("Chuong"))
    dang = clean(item.get("Dang"))
    access = clean(item.get("QuyenTruyCap") or "FREE")
    parts: List[str] = []
    if socau:
        parts.append(f"{socau} câu hỏi")
    if chuong:
        parts.append(chuong)
    if dang:
        parts.append(dang)
    if access:
        parts.append(access)
    og_desc = " · ".join(parts) if parts else "Bấm để đăng nhập và làm bài."
    return og_title, og_desc


def parse_de_from_next(next_url: str) -> str:
    u = safe_next_url(next_url)
    if not u:
        return ""
    parsed = urllib.parse.urlparse(u)
    if parsed.path.startswith("/d/"):
        return clean(parsed.path[3:].split("/")[0])
    qs = urllib.parse.parse_qs(parsed.query)
    return clean((qs.get("de") or qs.get("made") or [""])[0])


def is_link_preview_bot() -> bool:
    ua = (request.headers.get("User-Agent") or "").lower()
    keys = (
        "facebookexternalhit", "facebot", "twitterbot", "linkedinbot",
        "whatsapp", "telegrambot", "slackbot", "discordbot", "zalo",
        "line-poker", "bingpreview", "crawler", "spider", "preview",
    )
    return any(k in ua for k in keys)


def build_exam_entry_url(de: str, args: Any = None) -> str:
    """URL vào app — chỉ giữ mã đề + tuỳ chọn làm bài, không nhét mon/lop/chuong."""
    made = clean(de or (args.get("de") if args else "") or (args.get("made") if args else ""))
    if not made:
        return "/"
    pairs: List[Tuple[str, str]] = [("de", made)]
    has_start = clean(args.get("start") if args else "") == "1"
    has_open = clean(args.get("open") if args else "") == "1"
    for k in ("level", "dang", "sq", "sa", "open", "start"):
        v = clean(args.get(k) if args else "")
        if not v:
            continue
        pairs.append((k, v))
        if k == "start":
            has_start = True
        if k == "open":
            has_open = True
    if not has_start and not has_open:
        pairs.append(("start", "1"))
    return "/?" + urllib.parse.urlencode(pairs)


def render_share_page(de: str, args: Any):
    store = get_store()
    item = None
    og_title, og_desc = "Luyện đề Vật lý - Toán học", "Đăng nhập để làm bài luyện tập trực tuyến."
    if de:
        try:
            og_title, og_desc = share_og_context(store, de)
            item = catalog_find_by_made(store, de)
        except Exception:
            pass
    target_url = build_exam_entry_url(de, args)
    return render_template_string(
        SHARE_HTML,
        og_title=og_title,
        og_desc=og_desc,
        og_url=request.url,
        target_url=target_url,
        target_url_json=json.dumps(target_url),
        card_title=exam_display_title(item),
        item=item,
        auto_redirect=not is_link_preview_bot(),
    )


def share_og_context(store: Any, de: str) -> Tuple[str, str]:
    store.ensure_questions_loaded()
    return exam_share_preview_text(catalog_find_by_made(store, de))

# ============================================================
# HTML
# ============================================================

SHARE_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ og_title }}</title>
<meta name="description" content="{{ og_desc }}">
<meta property="og:title" content="{{ og_title }}">
<meta property="og:description" content="{{ og_desc }}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Luyện đề Vật lý - Toán học">
<meta property="og:url" content="{{ og_url }}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{{ og_title }}">
<meta name="twitter:description" content="{{ og_desc }}">
{% if auto_redirect %}<meta http-equiv="refresh" content="1;url={{ target_url }}">{% endif %}
<style>body{margin:0;background:#f3f6fb;font-family:Arial,sans-serif;color:#0f172a}.top{background:#1d4ed8;color:#fff;padding:16px 20px;font-weight:800}.box{max-width:520px;margin:40px auto;background:#fff;border:1px solid #d9e2ef;border-radius:16px;padding:24px;box-shadow:0 8px 30px #0001}h1{margin:0 0 10px;font-size:22px;color:#1e3a8a}.meta{color:#64748b;font-size:14px;line-height:1.6;margin:8px 0}.tag{display:inline-block;background:#eef2ff;color:#1d4ed8;padding:3px 8px;border-radius:999px;font-size:12px;font-weight:800;margin:2px}.btn{display:inline-block;margin-top:14px;background:#1d4ed8;color:#fff;font-weight:800;text-decoration:none;padding:12px 18px;border-radius:10px}.muted{font-size:13px;color:#64748b;margin-top:12px}</style>
</head><body>
<div class="top">ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</div>
<div class="box">
<h1>{{ card_title }}</h1>
{% if item %}
<div>
{% if item.Mon %}<span class="tag">{{ item.Mon }}</span>{% endif %}
{% if item.Lop %}<span class="tag">Lớp {{ item.Lop }}</span>{% endif %}
{% if item.SoCau %}<span class="tag">{{ item.SoCau }} câu</span>{% endif %}
{% if item.QuyenTruyCap %}<span class="tag">{{ item.QuyenTruyCap }}</span>{% endif %}
</div>
<div class="meta">{% if item.Chuong %}<div><b>Chương:</b> {{ item.Chuong }}</div>{% endif %}{% if item.Dang %}<div><b>Dạng:</b> {{ item.Dang }}</div>{% endif %}{% if item.BoDe %}<div><b>Bộ đề:</b> {{ item.BoDe }}</div>{% endif %}</div>
{% else %}
<p class="meta">Không tìm thấy thông tin đề. Có thể hệ thống đang nạp dữ liệu hoặc mã đề đã đổi.</p>
{% endif %}
<a class="btn" href="{{ target_url }}">🚀 Đăng nhập và làm bài</a>
<p class="muted">Link này dùng để gửi học viên. Zalo/Messenger sẽ hiện tên đề và số câu ở trên.</p>
</div>
{% if auto_redirect %}<script>setTimeout(function(){location.replace({{ target_url_json|safe }});},900);</script>{% endif %}
</body></html>
"""

LOGIN_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{% if og_title %}<title>{{ og_title }}</title><meta name="description" content="{{ og_desc }}"><meta property="og:title" content="{{ og_title }}"><meta property="og:description" content="{{ og_desc }}"><meta property="og:type" content="website"><meta property="og:site_name" content="Luyện đề Vật lý - Toán học">{% if og_url %}<meta property="og:url" content="{{ og_url }}">{% endif %}<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{{ og_title }}"><meta name="twitter:description" content="{{ og_desc }}">{% else %}<title>Đăng nhập luyện đề</title>{% endif %}
<script>(function(){try{var t=localStorage.getItem('LDVL_THEME')||'light';document.documentElement.setAttribute('data-theme',t==='dark'?'dark':'light')}catch(e){}})();</script>
<style>body{margin:0;background:#f3f6fb;font-family:Arial,sans-serif;color:#0f172a}html[data-theme="dark"] body{background:#0f172a;color:#e2e8f0}html[data-theme="dark"] .box{background:#1e293b;border-color:#334155}html[data-theme="dark"] input{background:#0f172a;color:#e2e8f0;border-color:#475569}html[data-theme="dark"] .hint{color:#94a3b8}.box{max-width:460px;margin:55px auto;background:#fff;border:1px solid #d9e2ef;border-radius:16px;padding:24px;box-shadow:0 8px 30px #0001}.top{background:#1d4ed8;color:#fff;padding:16px 20px;font-weight:800;display:flex;justify-content:space-between;align-items:center}.themeBtn{background:#ffffff22;border:1px solid #ffffff55;color:#fff;padding:5px 10px;border-radius:8px;font-size:15px;font-weight:800;cursor:pointer}input,button{width:100%;padding:12px;margin:8px 0;border-radius:10px;border:1px solid #cbd5e1;font-size:16px}button{background:#1d4ed8;color:white;font-weight:800;cursor:pointer}.err{background:#fee2e2;color:#991b1b;padding:10px;border-radius:10px;margin:8px 0}.ok{background:#dcfce7;color:#166534;padding:10px;border-radius:10px;margin:8px 0}.hint{font-size:13px;color:#64748b;line-height:1.5}.link{display:block;text-align:center;margin-top:12px;color:#1d4ed8;font-weight:800;text-decoration:none}</style></head><body>
<div class="top"><span>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</span><button type="button" class="themeBtn" onclick="(function(){var c=document.documentElement.getAttribute('data-theme')||'light';var d=c!=='dark';document.documentElement.setAttribute('data-theme',d?'dark':'light');try{localStorage.setItem('LDVL_THEME',d?'dark':'light')}catch(e){}event.target.textContent=d?'☀️':'🌙'})()">🌙</button></div>
<div class="box"><h2>Đăng nhập học viên</h2>{% if error %}<div class="err">{{error}}</div>{% endif %}{% if msg %}<div class="ok">{{msg}}</div>{% endif %}
<form method="post"><input type="hidden" name="device_id" id="device_id"><input type="hidden" name="next" value="{{ next or '' }}"><label>Mã học sinh / tài khoản</label><input name="mahs" autofocus required placeholder="VD: HS001 hoặc TRIAL_xxxx"><label>Mật khẩu</label><input name="password" type="password" required placeholder="Nhập mật khẩu"><button>Đăng nhập</button></form>
<a class="link" href="/register">Đăng ký dùng thử miễn phí 3 ngày</a>
<div class="hint">Tài khoản lấy từ sheet <b>HOC_VIEN</b>. ADMIN được xem đáp án và sửa câu hỏi trực tiếp. Tài khoản dùng thử chỉ được đăng ký 1 lần theo số điện thoại và thiết bị; chỉ luyện đề FREE, không chấm điểm.</div></div>
<script>function did(){let k='LDVL_DEVICE_ID';let v=localStorage.getItem(k);if(!v){v='DEV_'+Date.now()+'_'+Math.random().toString(36).slice(2,10);localStorage.setItem(k,v)}document.getElementById('device_id').value=v}did();(function(){try{var t=localStorage.getItem('LDVL_THEME')||'light';var b=document.querySelector('.themeBtn');if(b)b.textContent=t==='dark'?'☀️':'🌙'}catch(e){}})();</script></body></html>
"""


REGISTER_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Đăng ký dùng thử</title>
<script>(function(){try{var t=localStorage.getItem('LDVL_THEME')||'light';document.documentElement.setAttribute('data-theme',t==='dark'?'dark':'light')}catch(e){}})();</script>
<style>body{margin:0;background:#f3f6fb;font-family:Arial,sans-serif;color:#0f172a}html[data-theme="dark"] body{background:#0f172a;color:#e2e8f0}html[data-theme="dark"] .box{background:#1e293b;border-color:#334155}html[data-theme="dark"] input,html[data-theme="dark"] select{background:#0f172a;color:#e2e8f0;border-color:#475569}html[data-theme="dark"] .hint{color:#94a3b8}.box{max-width:500px;margin:40px auto;background:#fff;border:1px solid #d9e2ef;border-radius:16px;padding:24px;box-shadow:0 8px 30px #0001}.top{background:#1d4ed8;color:#fff;padding:16px 20px;font-weight:800;display:flex;justify-content:space-between;align-items:center}.themeBtn{background:#ffffff22;border:1px solid #ffffff55;color:#fff;padding:5px 10px;border-radius:8px;font-size:15px;font-weight:800;cursor:pointer}input,button,select{width:100%;padding:12px;margin:8px 0;border-radius:10px;border:1px solid #cbd5e1;font-size:16px}button{background:#1d4ed8;color:white;font-weight:800;cursor:pointer}.err{background:#fee2e2;color:#991b1b;padding:10px;border-radius:10px;margin:8px 0}.hint{font-size:13px;color:#64748b;line-height:1.5}.link{display:block;text-align:center;margin-top:12px;color:#1d4ed8;font-weight:800;text-decoration:none}</style></head><body>
<div class="top"><span>ĐĂNG KÝ DÙNG THỬ 3 NGÀY</span><button type="button" class="themeBtn" onclick="(function(){var c=document.documentElement.getAttribute('data-theme')||'light';var d=c!=='dark';document.documentElement.setAttribute('data-theme',d?'dark':'light');try{localStorage.setItem('LDVL_THEME',d?'dark':'light')}catch(e){}event.target.textContent=d?'☀️':'🌙'})()">🌙</button></div>
<div class="box"><h2>Tạo tài khoản dùng thử</h2>{% if error %}<div class="err">{{error}}</div>{% endif %}
<form method="post"><input type="hidden" name="device_id" id="device_id"><label>Họ tên học sinh</label><input name="hoten" required placeholder="Nhập họ tên"><label>Lớp</label><input name="lop" placeholder="VD: 12QT1"><label>Số điện thoại</label><input name="phone" required inputmode="tel" placeholder="Nhập số điện thoại"><label>Mật khẩu</label><input name="password" type="password" required placeholder="Tối thiểu 4 ký tự"><button>Đăng ký và vào làm bài</button></form>
<a class="link" href="/login">Đã có tài khoản? Đăng nhập</a>
<div class="hint">Mỗi số điện thoại và mỗi thiết bị chỉ được đăng ký dùng thử 1 lần. Tài khoản dùng thử được dùng 3 ngày, chỉ mở được các đề FREE. Tài khoản dùng thử không mở đề VIP, không nộp/chấm điểm, không xem đáp án/lời giải và không dùng Loại 2 câu sai.</div></div>
<script>function did(){let k='LDVL_DEVICE_ID';let v=localStorage.getItem(k);if(!v){v='DEV_'+Date.now()+'_'+Math.random().toString(36).slice(2,10);localStorage.setItem(k,v)}document.getElementById('device_id').value=v}did();(function(){try{var t=localStorage.getItem('LDVL_THEME')||'light';var b=document.querySelector('.themeBtn');if(b)b.textContent=t==='dark'?'☀️':'🌙'}catch(e){}})();</script></body></html>
"""

APP_HTML = r"""
<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>Luyện đề</title>
<script>(function(){try{var t=localStorage.getItem('LDVL_THEME')||'light';document.documentElement.setAttribute('data-theme',t==='dark'?'dark':'light')}catch(e){}})();</script>
<script>window.MathJax={loader:{load:['[tex]/ams']},tex:{packages:{'[+]':['ams']},inlineMath:[["$","$"],["\\(","\\)"]],displayMath:[["$$","$$"],["\\[","\\]"]],processEscapes:true},svg:{fontCache:"global"},options:{renderActions:{addMenu:[0,0,'']}}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>
:root{--blue:#1d4ed8;--border:#d7e0ed;--bg:#f5f7fb;--surface:#fff;--text:#0f172a;--heading:#1e3a8a;--muted:#64748b;--green:#dcfce7;--red:#fee2e2;--yellow:#fff7ed;--exam-bg:#fff7ed;--exam-border:#fed7aa;--exam-text:#9a3412;--exam-timer-bg:#fff;--exam-timer-border:#fdba74;--btn2-bg:#eef2ff;--btn2-color:#1d4ed8;--quiz-timer-bg:#eef2ff;--quiz-timer-color:#1e40af;--quiz-timer-border:#bfdbfe;--shuffle-bg:#eff6ff;--shuffle-border:#93c5fd;--shuffle-text:#1e3a8a;--solution-bg:#fff7ed;--solution-border:#fed7aa;--opt-hover:#f8fafc;--num-answered:#fef3c7;--modal-overlay:#0008;--load-card-bg:#eff6ff;--load-card-border:#93c5fd;--load-warn-bg:#fff7ed;--load-warn-border:#fed7aa;--load-warn-text:#9a3412}html[data-theme="dark"]{--bg:#0f172a;--surface:#1e293b;--text:#e2e8f0;--heading:#93c5fd;--muted:#94a3b8;--border:#334155;--green:#14532d;--red:#450a0a;--yellow:#422006;--exam-bg:#422006;--exam-border:#9a3412;--exam-text:#fed7aa;--exam-timer-bg:#1e293b;--exam-timer-border:#c2410c;--btn2-bg:#1e3a5f;--btn2-color:#bfdbfe;--quiz-timer-bg:#1e3a5f;--quiz-timer-color:#bfdbfe;--quiz-timer-border:#475569;--shuffle-bg:#1e3a5f;--shuffle-border:#3b82f6;--shuffle-text:#bfdbfe;--solution-bg:#422006;--solution-border:#9a3412;--opt-hover:#334155;--num-answered:#422006;--modal-overlay:#000c;--load-card-bg:#1e3a5f;--load-card-border:#3b82f6;--load-warn-bg:#422006;--load-warn-border:#9a3412;--load-warn-text:#fed7aa;color:var(--text)}html[data-theme="dark"] .btnGreen{background:#166534;color:#dcfce7}html[data-theme="dark"] .btnRed{background:#991b1b;color:#fee2e2}html[data-theme="dark"] .correct{color:#86efac!important}html[data-theme="dark"] .wrong{color:#fecaca!important}html[data-theme="dark"] .num.ok{color:#86efac}html[data-theme="dark"] .num.bad{color:#fecaca}*{box-sizing:border-box}html{overflow-x:hidden;-webkit-text-size-adjust:100%;text-size-adjust:100%}body{margin:0;background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif;font-size:15px;overflow-x:hidden;width:100%;max-width:100vw}.themeBtn{background:#ffffff22;border:1px solid #ffffff55;color:#fff;padding:5px 10px;border-radius:8px;font-size:15px;font-weight:800;cursor:pointer;margin-right:6px}.top{position:sticky;top:0;z-index:9;background:var(--blue);color:#fff;padding:10px 14px;box-shadow:0 2px 8px #0002;width:100%;max-width:100vw}.topRow{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between}.top h1{font-size:18px;margin:0;flex:1;min-width:200px}.topRight{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;font-size:13px}.top a{color:#fff}.adminBar{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center;margin-right:4px}.adminTopBtn{background:#dcfce7;border:1px solid #86efac;color:#166534;padding:5px 10px;border-radius:8px;font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap}.adminTopBtn2{background:#ffffff22;border:1px solid #ffffff55;color:#fff}.adminTopBtn:hover{filter:brightness(1.05)}.adminTopBtn:disabled{opacity:.55;cursor:not-allowed}.examStrip{position:sticky;top:56px;z-index:8;display:flex;gap:10px;align-items:center;justify-content:center;padding:8px 10px;background:var(--exam-bg);border-top:1px solid var(--exam-border);border-bottom:1px solid var(--exam-border);color:var(--exam-text);font-weight:800}.examStrip .timer{background:var(--exam-timer-bg);border:1px solid var(--exam-timer-border);border-radius:999px;padding:2px 10px}.wrap{max-width:1420px;margin:auto;padding:12px;width:100%;min-width:0}.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px;margin-bottom:12px;box-shadow:0 1px 4px #0001}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:4px;min-width:160px;flex:1}.field label{font-weight:700;font-size:12px}select,input,textarea,button{font-family:inherit;font-size:14px;border:1px solid var(--border);border-radius:8px;padding:9px 10px;background:var(--surface);color:var(--text)}button{cursor:pointer;font-weight:800}.btn{background:var(--blue);border-color:var(--blue);color:#fff}.btn2{background:var(--btn2-bg);color:var(--btn2-color)}.btnGreen{background:#dcfce7;color:#166534}.btnRed{background:#fee2e2;color:#991b1b}.btnStartStrong{background:linear-gradient(135deg,#2563eb,#7c3aed);border-color:#1e40af;color:#fff;box-shadow:0 6px 16px #1e40af44}.btnStartStrong:hover{filter:brightness(1.03)}.quizTimer{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;background:var(--quiz-timer-bg);color:var(--quiz-timer-color);font-weight:800;border:1px solid var(--quiz-timer-border)}.shuffleHint{margin-top:8px;background:var(--shuffle-bg);border:1px dashed var(--shuffle-border);color:var(--shuffle-text);padding:7px 9px;border-radius:8px;font-size:12px;font-weight:700}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}.card{border:1px solid var(--border);border-radius:12px;background:var(--surface);padding:12px}.card h3{margin:0 0 8px;color:var(--heading)}.tag{display:inline-block;background:var(--btn2-bg);color:var(--btn2-color);padding:3px 8px;border-radius:999px;font-size:12px;font-weight:800;margin:2px}.line{height:1px;background:var(--border);margin:10px 0}.muted{color:var(--muted)}.hide{display:none!important}.quizLayout{display:grid;grid-template-columns:1fr 270px;gap:12px}.quizHeadRow{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:nowrap}.btnQuizToolsToggle{display:none;width:auto;margin:0;padding:6px 10px;font-size:18px;line-height:1;border-radius:8px;background:var(--btn2-bg);color:var(--btn2-color);border:1px solid var(--border);flex-shrink:0;cursor:pointer;font-weight:800}.quizActionsPanel{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end;margin-top:0}.quizToolbarStrip{background:transparent;border:none;padding:0;margin:0 0 8px;box-shadow:none}.quizToolbarHead{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:4px;flex-wrap:wrap}.quizToolbarHead .qid{flex:1;min-width:0;margin:0}.quizAdminTools{display:flex;gap:4px;flex-shrink:0;align-items:center;flex-wrap:wrap;justify-content:flex-end}.quizAdminTools .btn2,.adminQuizAct{background:#1e40af!important;color:#fff!important;border-color:#1d4ed8!important;font-weight:700!important}.quizAdminTools button{font-size:11px!important;padding:4px 8px!important;margin:0!important;white-space:nowrap}.quizToolsRow{display:flex;flex-wrap:nowrap;gap:4px;align-items:center;overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%;padding-bottom:2px}.quizToolsRow .quizNavRow{display:flex;flex-wrap:nowrap;gap:4px;margin:0;align-items:center;flex-shrink:0;justify-content:flex-start}.quizToolsRow .quizActionsPanel{display:flex!important;flex-wrap:nowrap;gap:4px;margin:0;align-items:center;justify-content:flex-start;width:auto;flex:1;min-width:0;border:none;background:transparent;padding:0}.quizToolsRow #quizActions button,.quizToolsRow .quizNavRow button,.quizToolsRow .quizNavRow .btnNavWide{font-size:11px!important;padding:4px 8px!important;margin:0!important;white-space:nowrap;flex-shrink:0;border-radius:6px!important;min-height:0!important;line-height:1.2!important;width:auto}.quizToolbarStrip .btnGreen,.quizToolbarStrip .btnStartStrong,.quizToolbarStrip .btn{background:var(--btn2-bg)!important;color:var(--btn2-color)!important;border:1px solid var(--border)!important;box-shadow:none!important;transform:none!important;filter:none!important}.quizToolbarStrip .btnGreen:hover,.quizToolbarStrip .btnStartStrong:hover,.quizToolbarStrip .btn:hover{filter:brightness(0.98)!important;transform:none!important}.quizToolbarStrip .btnSolToggle.active,.quizToolbarStrip .btnMobileSolToggle.active,.btnSolToggle.active,.btnMobileSolToggle.active{background:var(--surface)!important;color:var(--text)!important;border-color:var(--border)!important;font-weight:800}.btnMobileSolToggle.vipSolLocked,.btnSolToggle.vipSolLocked{opacity:.45;cursor:not-allowed}.quizQuestionPanel{margin-top:0}.quizToolsRow .btnNavPrimary{background:var(--btn2-bg)!important;color:var(--btn2-color)!important;border:1px solid var(--border)!important}.quizNavRow{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:12px;flex-wrap:wrap}.btnNavMini{display:none;width:auto;margin:0;padding:8px 14px;font-size:18px;font-weight:800;border-radius:8px;min-width:44px;border:1px solid var(--border);background:var(--surface);color:var(--text);cursor:pointer}.btnNavMini.btnNavPrimary{background:var(--blue);color:#fff;border-color:var(--blue)}.btnNavWide{width:auto;margin:0}@media(max-width:768px),(orientation:landscape) and (max-height:520px){.btnQuizToolsToggle{display:inline-flex!important;align-items:center;justify-content:center}.quizHeadRow{flex-wrap:wrap;align-items:center}.qid{font-size:13px;line-height:1.3;flex:1;min-width:0;width:100%}.quizToolbarStrip{margin-bottom:6px}body.mobile-quiz-ui .quizToolbarStrip{display:flex!important;flex-wrap:nowrap!important;align-items:center!important;gap:4px!important}body.mobile-quiz-ui .quizToolbarHead{flex:1 1 auto!important;min-width:0!important;margin-bottom:0!important;flex-wrap:nowrap!important;align-items:center!important;overflow:hidden!important}body.mobile-quiz-ui .quizToolbarHead .qid{width:auto!important;white-space:nowrap!important;overflow-x:auto!important;-webkit-overflow-scrolling:touch;font-size:11px!important;line-height:1.2!important}body.mobile-quiz-ui:not(.fullde-mode) .quizToolsRow{flex-shrink:0!important;overflow:visible!important;padding-bottom:0!important}body.mobile-quiz-ui.fullde-mode .quizToolsRow{display:none!important}body.mobile-quiz-ui.mobile-quiz-tools-open .quizToolbarStrip{flex-wrap:wrap!important}body.mobile-quiz-ui.mobile-quiz-tools-open:not(.fullde-mode) .quizToolsRow{width:100%!important}.quizToolsRow .quizNavRow.hide-mobile{display:none!important}body.mobile-quiz-ui:not(.fullde-mode):not(.mobile-quiz-tools-open) .quizToolsRow .quizActionsPanel{display:none!important}body.mobile-quiz-ui:not(.fullde-mode).mobile-quiz-tools-open .quizToolsRow{flex-wrap:wrap!important}body.mobile-quiz-ui:not(.fullde-mode).mobile-quiz-tools-open .quizToolsRow .quizActionsPanel{display:flex!important;flex-wrap:wrap!important;width:100%;overflow:visible}.quizToolsRow .quizActionsPanel{flex-wrap:nowrap!important;overflow-x:auto;width:100%}.quizToolsRow #quizActions button{font-size:10px!important;padding:3px 6px!important}#quizActions button,.quizNavRow .btnNavWide,.shortAnsBtn{font-size:10px!important;padding:3px 6px!important;border-radius:6px!important;min-height:0!important;line-height:1.2!important;width:auto;margin:0}body.fullde-mode #fsOnlyTools{display:flex!important;flex-wrap:wrap;gap:3px!important;padding:4px 6px!important;margin:0 0 4px!important;border-bottom:1px solid var(--border);border-radius:0;background:var(--surface);width:100%}body.fullde-mode #fsOnlyTools button{font-size:10px!important;padding:3px 6px!important}body.mobile-quiz-ui.fullde-mode #fsOnlyTools{flex-wrap:nowrap!important;overflow-x:auto!important;-webkit-overflow-scrolling:touch;flex-shrink:0!important;width:auto!important;margin:0!important;padding:0!important;border:none!important;background:transparent!important}body.mobile-quiz-ui.fullde-mode:not(.mobile-quiz-tools-open) #fsOnlyTools>:not(:nth-child(-n+2)){display:none!important}body.mobile-quiz-ui.fullde-mode.mobile-quiz-tools-open #fsOnlyTools{width:100%!important}body.mobile-quiz-ui.fullde-mode #fsQuizTimer,body.mobile-quiz-ui.fullde-mode #btnFsNav{display:none!important}.btnFsToolsToggle{font-weight:800!important;flex-shrink:0!important}.btnNavMini{display:inline-flex!important;align-items:center;justify-content:center}.btnNavWide.hide-mobile{display:none!important}#quiz>.panel.row{padding:8px 10px;font-size:13px}#quiz>.panel.row #resultBox{font-size:14px!important}#quiz>.panel.row .quizTimer{font-size:12px;padding:3px 8px}.panel{padding:10px;margin-bottom:8px}.quizLayout{grid-template-columns:1fr!important;gap:8px!important}.dsSolutionRows{grid-template-columns:1fr!important}.dsSolutionTn:not(.dsSolutionRows),.dsSolutionDs:not(.dsSolutionRows){grid-template-columns:repeat(2,minmax(0,1fr))!important}}body.mobile-quiz-ui .dsSolutionTn:not(.dsSolutionRows),body.mobile-quiz-ui .dsSolutionDs:not(.dsSolutionRows){grid-template-columns:repeat(2,minmax(0,1fr))!important}body.mobile-quiz-ui .dsSolutionCompact .dsSolutionItem{padding:5px 7px}body.mobile-quiz-ui .dsSolutionCompact .dsSolutionHead{gap:4px}body.mobile-quiz-ui .dsSolutionCompact .dsStmtInline{font-size:13px;line-height:1.35}body.mobile-quiz-ui .mcqSplitOpts,body.mobile-quiz-ui .mcqSplitWrap .mcqSplitOpts{max-height:none!important;overflow:visible!important}body.mobile-quiz-ui .shortAnsCompact .shortAnsQtext{max-height:none!important;overflow:visible!important}body.mobile-quiz-ui #qtext,body.mobile-quiz-ui #options,body.mobile-quiz-ui #solution,body.mobile-quiz-ui #hintBox{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}body.mobile-quiz-ui .qbox,body.mobile-quiz-ui .solution,body.mobile-quiz-ui .hintAdminBody,body.mobile-quiz-ui .dsSolutionBody,body.mobile-quiz-ui .dsStmtBlock{overflow-x:auto;-webkit-overflow-scrolling:touch}html.mobile-quiz-ui,body.mobile-quiz-ui{overscroll-behavior-y:none}body.quiz-scroll-lock{overscroll-behavior-y:none}body.mobile-quiz-ui.quiz-scroll-lock:not(.fullde-mode) #quiz{display:flex!important;flex-direction:column!important;max-height:calc(100dvh - 56px)!important;overflow:hidden!important}body.mobile-quiz-ui.quiz-scroll-lock:not(.fullde-mode) #quiz>.panel.row{flex-shrink:0!important}body.mobile-quiz-ui.quiz-scroll-lock:not(.fullde-mode) #quiz .quizLayout{flex:1 1 auto!important;min-height:0!important;overflow:hidden!important;display:flex!important;flex-direction:column!important}body.mobile-quiz-ui.quiz-scroll-lock:not(.fullde-mode) #quiz .quizLayout>div:first-child{flex:1 1 auto!important;min-height:0!important;display:flex!important;flex-direction:column!important}body.mobile-quiz-ui.quiz-scroll-lock:not(.fullde-mode) #quiz .quizLayout>div:first-child>.panel{flex:1 1 auto!important;min-height:0!important;overflow-y:auto!important;-webkit-overflow-scrolling:touch!important;overscroll-behavior:contain!important;touch-action:pan-y!important;max-height:none!important}body.mobile-quiz-ui #quiz{overscroll-behavior:contain}body.fullde-mode.mobile-quiz-ui #quiz .quizLayout>div:first-child>.panel{overflow:hidden!important;display:flex!important;flex-direction:column!important;min-height:0!important;flex:1!important}body.fullde-mode.mobile-quiz-ui #qtext{flex:0 0 auto!important;max-height:min(42vh,320px)!important;overflow-y:auto!important;overscroll-behavior:contain!important;-webkit-overflow-scrolling:touch!important;touch-action:pan-y!important;position:sticky!important;top:0!important;z-index:4!important;background:var(--surface)!important;box-shadow:0 2px 10px #00000014}body.fullde-mode.mobile-quiz-ui #options{flex:1 1 auto!important;min-height:0!important;overflow-y:auto!important;overscroll-behavior:contain!important;-webkit-overflow-scrolling:touch!important;touch-action:pan-y!important;padding-bottom:16px!important}.mobileNavDock{display:none}.mobileNavBody{display:contents}@media(max-width:768px),(orientation:landscape) and (max-height:520px){body.mobile-quiz-ui .mobileNavDock{display:flex!important;align-items:center;justify-content:space-between;gap:8px;padding:6px 8px;border-top:1px solid var(--border);background:var(--surface);flex-shrink:0}body.mobile-quiz-ui .mobileDockTimer{margin:0!important;font-size:12px!important;white-space:nowrap;flex-shrink:0;padding:4px 6px!important}body.mobile-quiz-ui .mobileDockNavGroup{display:flex!important;align-items:center;gap:4px;flex-shrink:0}body.mobile-quiz-ui .btnMobileNavMini{display:inline-flex!important;align-items:center;justify-content:center;width:34px;min-width:34px;height:34px;padding:0;font-size:20px;font-weight:800;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);cursor:pointer;line-height:1;flex-shrink:0}body.mobile-quiz-ui .btnMobileNavMini.btnMobileNavPrimary{background:var(--blue);color:#fff;border-color:var(--blue)}body.mobile-quiz-ui .btnMobileNavMini:disabled{opacity:.35;cursor:default}body.mobile-quiz-ui .mobileDockMid{display:flex!important;gap:4px;flex:1;justify-content:center;align-items:center;min-width:0}body.mobile-quiz-ui .btnMobileSolToggle{padding:5px 6px;font-size:10px;font-weight:800;border-radius:7px;border:1px solid var(--border);background:var(--surface);color:var(--text);margin:0;width:auto;flex:1;max-width:76px;cursor:pointer;line-height:1.2;white-space:nowrap}body.mobile-quiz-ui .btnMobileSolToggle.active{background:var(--blue)!important;color:#fff!important;border-color:var(--blue)!important}body.mobile-quiz-ui .btnMobileNavToggle{width:auto;margin:0;padding:6px 8px;font-size:11px;font-weight:800;border-radius:8px;border:1px solid var(--border);background:var(--btn2-bg);color:var(--btn2-color);cursor:pointer;text-align:center;flex:0 1 auto!important;max-width:42%}.vipSolBtnsTop{display:none;gap:6px;align-items:center}.vipSolBtnsTop:not(.hide){display:inline-flex!important}.btnMobileSolToggle{padding:5px 10px;font-size:11px;font-weight:800;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);margin:0;width:auto;cursor:pointer;line-height:1.2;white-space:nowrap}.btnMobileSolToggle.active{background:var(--blue)!important;color:#fff!important;border-color:var(--blue)!important}body.mobile-quiz-ui .fsNavPanel{display:flex!important;flex-direction:column!important;padding:0!important;overflow:hidden!important;min-height:0!important}body.mobile-quiz-ui .mobileNavBody{display:none!important;flex:1;min-height:0;overflow:auto;padding:6px 8px;flex-direction:column!important}body.mobile-quiz-ui.mobile-nav-open .mobileNavBody{display:flex!important}body.mobile-quiz-ui.mobile-nav-open .fsNavPanel{max-height:min(42vh,320px)!important}body.mobile-quiz-ui:not(.fullde-mode) #quiz>.panel.row .quizTimer{display:none!important}body.mobile-quiz-ui:not(.fullde-mode) #quiz .quizLayout>div:last-child{flex-shrink:0!important}body.fullde-mode.mobile-quiz-ui #quiz .quizLayout>div:last-child{max-height:52px!important;min-height:0!important}body.mobile-quiz-ui #fsQuizTimer,body.mobile-quiz-ui #btnFsNav{display:none!important}body.fullde-mode.mobile-quiz-ui.mobile-nav-open #quiz .quizLayout>div:last-child{max-height:min(40vh,300px)!important}}body.mobile-quiz-ui.fullde-mode #quiz .quizLayout>div:first-child>.panel{overscroll-behavior:contain!important}body.mobile-quiz-ui .opt>span:not(.dsCircle),body.mobile-quiz-ui .tfStmt{overflow-x:auto;-webkit-overflow-scrolling:touch;display:block}body.mobile-quiz-ui .opt .dsCircle,body.mobile-quiz-ui .tfrow .dsCircle{display:inline-flex!important;align-items:center!important;justify-content:center!important;flex:0 0 auto!important;padding:0!important;line-height:1!important;text-align:center!important}.qid{font-size:19px;font-weight:800}.qidIdBadge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:8px;border:1px solid #bfdbfe;background:#eff6ff;color:#1e3a8a;font-size:inherit;font-weight:800;font-family:ui-monospace,Consolas,monospace;cursor:pointer;line-height:1.3;vertical-align:middle}.qidIdBadge:hover{filter:brightness(1.03);box-shadow:0 1px 4px #1d4ed833}.qidIdBadge.qidIdEmpty{cursor:default;opacity:.7;background:var(--surface);border-color:var(--border);color:var(--muted)}html[data-theme="dark"] .qidIdBadge{background:#1e3a5f;border-color:#3b82f6;color:#bfdbfe}.quizIdJumpWrap{display:inline-flex;gap:4px;align-items:center;flex-shrink:0}.quizIdJumpInp{width:148px;font-size:12px;padding:5px 8px;font-family:ui-monospace,Consolas,monospace}.quizIdJumpBtn{padding:5px 8px!important;font-size:12px!important;min-width:0!important}.idLookupCard{border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin:8px 0;background:var(--surface)}.idLookupCard h4{margin:0 0 6px;font-size:15px;color:var(--heading)}.idLookupMeta{font-size:13px;line-height:1.45;margin:4px 0}.idLookupPreview{font-size:13px;color:var(--muted);margin-top:6px;line-height:1.4}.qbox{border:1px solid var(--border);background:var(--surface);border-radius:8px;padding:clamp(10px,2vw,14px);min-height:0;line-height:1.5;font-size:clamp(15px,2.2vw,18px);color:var(--text)}.qimgWrap{display:block;width:100%;margin:8px 0 10px;clear:both}.qimg{max-width:100%;width:auto;height:auto;display:block;margin:0 auto;object-fit:contain;border:1px solid var(--border);border-radius:8px;background:var(--surface);max-height:min(42vh,340px)}@media(max-width:768px) and (orientation:portrait){.qimg{max-height:min(50vh,400px)}}.mcqSplitWrap{margin-top:8px}.mcqSplit{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(210px,0.85fr);gap:12px;align-items:start}.mcqSplitDs{grid-template-columns:minmax(0,1.05fr) minmax(260px,0.95fr)}.mcqSplitTln{grid-template-columns:minmax(0,1.1fr) minmax(220px,0.9fr)}.mcqSplitTln .mcqSplitImg .qimg{max-height:min(55vh,420px)}.mcqSplitImg .qimgWrap{margin:0}.mcqSplitImg .qimg{width:100%;max-height:min(48vh,360px)}.mcqSplitDs .mcqSplitImg .qimg{max-height:min(52vh,400px)}.mcqSplitOpts{min-width:0;min-height:0;display:flex;flex-direction:column;gap:4px}.mcqSplitOpts .opt{margin:4px 0;padding:8px 10px}.mcqSplitOpts .tfrow{margin:4px 0;padding:6px 8px;grid-template-columns:24px minmax(0,1fr) auto;gap:5px 6px}.mcqSplitOpts .tfStmt{font-size:14px;line-height:1.4}.mcqSplitOpts .tfOptsHead{display:grid;grid-template-columns:24px minmax(0,1fr) auto;gap:5px 6px;margin:0 0 4px;font-size:11px;font-weight:800;color:var(--muted)}.mcqSplitOpts .tfOpt{min-width:42px;padding:4px 7px;font-size:11px}@media(max-width:768px) and (orientation:portrait){.mcqSplit,.mcqSplitDs,.mcqSplitTln{grid-template-columns:1fr;gap:10px}.mcqSplitImg .qimg,.mcqSplitDs .mcqSplitImg .qimg,.mcqSplitTln .mcqSplitImg .qimg{max-height:min(52vh,420px);width:100%}}@media(orientation:landscape) and (max-height:520px){.mcqSplit,.mcqSplitDs,.mcqSplitTln{grid-template-columns:minmax(0,40%) minmax(0,60%);gap:8px;align-items:start}.mcqSplitImg .qimg,.mcqSplitDs .mcqSplitImg .qimg,.mcqSplitTln .mcqSplitImg .qimg{max-height:min(calc(100dvh - 130px),260px);width:100%}.mcqSplitOpts{overflow:visible;max-height:none;-webkit-overflow-scrolling:touch}.shortAnsCompact .shortAnsQtext{max-height:none;overflow:visible;font-size:14px;margin-bottom:6px}.shortAnsFieldRow{position:sticky;bottom:0;background:var(--surface);padding:6px 0 2px;z-index:3;border-top:1px solid var(--border);margin-top:4px;box-shadow:0 -4px 12px #0001}.shortAnsNote{display:none}.mcqSplitOpts .opt{padding:5px 7px;margin:2px 0;font-size:13px}}@media(max-width:480px) and (orientation:portrait){.qbox{font-size:15px}.mcqSplitImg .qimg,.mcqSplitDs .mcqSplitImg .qimg,.mcqSplitTln .mcqSplitImg .qimg{max-height:min(50vh,400px)}}.shortAnsBox{border:1px solid var(--border);border-radius:10px;background:var(--surface);padding:12px;margin-top:10px}.shortAnsCompact{margin:0;padding:10px 12px}.shortAnsQtext{margin:0 0 10px;padding:0;border:none;background:transparent;line-height:1.5;font-size:clamp(15px,2vw,18px);min-height:0;color:var(--text)}.shortAnsFieldRow{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.shortAnsLbl{font-weight:800;font-size:14px;white-space:nowrap}.shortAnsInput{width:5.5em;max-width:120px;min-width:4.5em;font-size:20px;font-weight:800;text-align:center;padding:6px 8px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);letter-spacing:.04em}.shortAnsInputWide{width:100%;max-width:none;font-size:18px;font-weight:600;text-align:left}.shortAnsBtn{width:auto;margin:0;padding:6px 12px;min-width:0}.shortAnsHint{font-size:12px}.shortAnsNote{margin-top:8px;font-size:12px}.qimgErr{margin:10px 0;padding:10px;border:1px solid #fed7aa;background:#fff7ed;border-radius:8px;color:#9a3412;font-size:13px}.opt{display:flex;gap:8px;align-items:flex-start;padding:10px;border-radius:10px;border:1px solid transparent;margin:7px 0;background:var(--surface);color:var(--text);position:relative;z-index:1}.opt:hover{background:var(--opt-hover)}.correct{background:var(--green)!important;border-color:#86efac!important}.wrong{background:var(--red)!important;border-color:#fecaca!important}.hidden5050{opacity:.25;pointer-events:none;text-decoration:line-through}.solution{background:var(--solution-bg);border:1px solid var(--solution-border);border-radius:10px;padding:10px 12px;margin-top:10px;color:var(--text);font-size:clamp(13px,1.8vw,15px);line-height:1.45}.latex-list{margin:8px 0 8px 22px;padding:0}.latex-list li{margin:6px 0;line-height:1.55}.latex-tabular-wrap{overflow-x:auto;margin:12px 0;width:100%}.latex-tabular{border-collapse:collapse;width:100%;max-width:100%;font-size:15px}.latex-tabular td,.latex-tabular th{border:1px solid var(--border);padding:6px 10px;vertical-align:middle;line-height:1.45}.latex-tabular tr.hline-top td{border-top:2px solid var(--border)}.hintAdminBody{width:100%;min-height:160px;max-height:520px;overflow:auto;font-size:15px;line-height:1.55;margin-top:8px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--surface);user-select:text;-webkit-user-select:text}.btnHintLoading{opacity:.82;cursor:wait!important;pointer-events:none}.hintSpin{display:inline-block;width:14px;height:14px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:hintSpin .75s linear infinite;vertical-align:-2px;margin-right:6px}.hintBoxLoading{border-color:#93c5fd!important;background:linear-gradient(180deg,var(--shuffle-bg),var(--surface))!important;animation:hintPulse 1.6s ease-in-out infinite}.hintLoadingPanel{display:flex;gap:12px;align-items:flex-start;padding:10px 4px 6px}.hintSpinBig{width:30px;height:30px;border:3px solid #93c5fd;border-top-color:var(--blue);border-radius:50%;animation:hintSpin .8s linear infinite;flex-shrink:0}@keyframes hintSpin{to{transform:rotate(360deg)}}@keyframes hintPulse{0%,100%{box-shadow:0 0 0 0 #3b82f633}50%{box-shadow:0 0 0 6px #3b82f611}}.hintAdminActions{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.hintAdminActions button{font-size:12px;padding:6px 10px;width:auto;margin:0}.infographicPromptBox{width:100%;min-height:300px;max-height:55vh;font-family:ui-monospace,Consolas,monospace;font-size:12px;line-height:1.5;padding:12px;border:1px solid var(--border);border-radius:10px;resize:vertical;background:var(--surface);color:var(--text);box-sizing:border-box}.hintAnswerCard{background:var(--green);border:2px solid #86efac;border-radius:10px;padding:12px 14px;margin:10px 0 8px}.hintAnswerCard.hintAnswerPending{background:var(--load-warn-bg);border-color:var(--load-warn-border)}.hintAnswerCard.hintAnswerPending .hintAnswerTitle{color:var(--load-warn-text)}.hintAnswerCard .hintAnswerTitle{font-size:16px;font-weight:800;color:#166534;margin:0 0 8px}html[data-theme="dark"] .hintAnswerCard .hintAnswerTitle{color:#86efac}.hintAnswerRow{margin:6px 0;line-height:1.55;font-size:15px}.hintAnswerRow b{color:#14532d}html[data-theme="dark"] .hintAnswerRow b{color:#bbf7d0}.hintSimilarBox{margin-top:10px;padding:10px 12px;border:1px dashed var(--shuffle-border);border-radius:10px;background:var(--shuffle-bg)}.hintSimilarBox .hintSimilarTitle{font-weight:800;margin-bottom:6px;color:var(--shuffle-text)}.hintSimilarBody{font-size:15px;line-height:1.55}.hintAiActions{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.hintAiActions button{font-size:12px;padding:6px 10px;width:auto;margin:0}.navNums{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.num{padding:8px 0;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text)}.num.active{outline:3px solid #93c5fd}.num.answered{background:var(--num-answered)}.num.ok{background:var(--green);color:#166534}.num.bad{background:var(--red);color:#991b1b}.tfrow{display:grid;grid-template-columns:26px minmax(0,1fr) auto;gap:6px 8px;align-items:start;border:1px solid var(--border);border-radius:10px;padding:8px 10px;margin:7px 0}.tfrow>b{padding-top:2px}.tfrow .dsCircle{margin-top:1px}.dsCircle{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;min-width:28px;min-height:28px;border-radius:50%;background:var(--blue);color:#fff;font-weight:800;font-size:14px;line-height:1;padding:0;box-sizing:border-box;flex-shrink:0;box-shadow:0 1px 3px #0002;text-align:center}.tfrow .dsCircle{width:26px;height:26px;min-width:26px;min-height:26px;font-size:13px}html[data-theme="dark"] .dsCircle{background:#2563eb;color:#eff6ff}.dsAnswerRow{display:flex;flex-wrap:wrap;gap:8px 12px;margin:4px 0}.dsAnswerItem{display:inline-flex;align-items:center;gap:6px}.dsVerdictDung{color:#166534;font-weight:800}html[data-theme="dark"] .dsVerdictDung{color:#86efac}.dsVerdictSai{color:#991b1b;font-weight:800}html[data-theme="dark"] .dsVerdictSai{color:#fecaca}.dsSolutionList{display:grid;grid-template-columns:1fr;gap:8px;margin-top:6px}.dsSolutionRows{grid-template-columns:1fr!important}.dsSolutionTn{grid-template-columns:1fr}@media(min-width:560px){.dsSolutionTn:not(.dsSolutionRows){grid-template-columns:repeat(2,minmax(0,1fr))}}@media(min-width:1100px){.dsSolutionTn:not(.dsSolutionRows){grid-template-columns:repeat(4,minmax(0,1fr))}}.dsSolutionDs{grid-template-columns:1fr}@media(min-width:640px){.dsSolutionDs:not(.dsSolutionRows){grid-template-columns:repeat(2,minmax(0,1fr))}}.dsSolutionItem{border:1px solid var(--border);border-radius:8px;padding:8px 10px;background:var(--surface)}.dsSolutionCompact .dsSolutionItem{padding:6px 9px}.dsSolutionHead{display:flex;flex-wrap:wrap;align-items:flex-start;gap:6px;margin-bottom:0}.dsSolutionHead+.dsSolutionBody,.dsSolutionHead+.dsStmtBlock{margin-top:6px}.dsSolutionBody{font-size:13px;line-height:1.45;overflow-x:auto;-webkit-overflow-scrolling:touch}.dsStmtInline{font-size:14px;line-height:1.4;flex:1 1 auto;min-width:0;word-break:break-word}.dsStmtBlock{width:100%;font-size:14px;line-height:1.45;overflow-x:auto;-webkit-overflow-scrolling:touch;word-break:break-word}.mcqSplitOpts .opt>span:not(.dsCircle){display:block;flex:1;min-width:0;overflow-x:auto;-webkit-overflow-scrolling:touch}.opt .dsCircle{flex:0 0 auto;flex-shrink:0;margin-top:1px;align-self:flex-start;padding:0;min-width:28px;text-align:center}.opt input[type=radio]{position:absolute;opacity:0;width:0;height:0;margin:0}.opt:has(input:checked) .dsCircle{background:#166534;box-shadow:0 0 0 2px #86efac}.opt.correct{background:#dcfce7!important;border-color:#86efac!important;box-shadow:inset 0 0 0 1px #bbf7d0}.opt.wrong{background:#fee2e2!important;border-color:#fecaca!important;box-shadow:inset 0 0 0 1px #fecaca}.tfrow.correct{background:#dcfce7!important;border-color:#86efac!important}.tfrow.wrong{background:#fee2e2!important;border-color:#fecaca!important}.tfRowFb{grid-column:1/-1;font-size:12px;font-weight:700;margin-top:2px;padding:2px 0 6px 28px;line-height:1.35}.tfRowFb.ok{color:#166534}.tfRowFb.bad{color:#991b1b}#resultBox.dsResultRich{font-size:13px;line-height:1.25;text-align:right}.dsCheckBox{display:flex;flex-direction:column;align-items:flex-end;gap:3px}.dsCheckHead{font-weight:800;font-size:15px;white-space:nowrap}.dsCheckRow{display:flex;flex-wrap:wrap;gap:4px;justify-content:flex-end}.dsCheckItem{display:inline-flex;align-items:center;padding:2px 7px;border-radius:6px;font-weight:800;font-size:12px;border:1px solid var(--border)}.dsCheckOk{background:var(--green);color:#166534;border-color:#86efac}.dsCheckBad{background:var(--red);color:#991b1b;border-color:#fca5a5}html[data-theme="dark"] .opt.correct,html[data-theme="dark"] .tfrow.correct{background:#14532d!important;border-color:#166534!important}html[data-theme="dark"] .opt.wrong,html[data-theme="dark"] .tfrow.wrong{background:#450a0a!important;border-color:#991b1b!important}.opt.correct .dsCircle{background:#166534}.opt.wrong .dsCircle{background:#991b1b}.tfStmt{min-width:0;line-height:1.45;font-size:15px;word-break:break-word}.tfOpts{display:flex;gap:6px;align-items:center;justify-content:flex-end;flex-shrink:0}.tfOptsHead{display:none}.tfOpt{display:inline-flex;align-items:center;justify-content:center;gap:4px;min-width:52px;padding:5px 10px;border:1px solid var(--border);border-radius:8px;background:var(--surface);font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap;user-select:none;position:relative}.tfOpt:has(input:checked){border-color:#93c5fd;background:var(--btn2-bg);color:var(--btn2-color)}.tfOpt input{width:13px;height:13px;margin:0;flex-shrink:0}.tfLbl{line-height:1}.tfLblShort{display:none}.tfLblFull{display:inline}.modal{position:fixed;inset:0;background:var(--modal-overlay);z-index:20;display:flex;align-items:center;justify-content:center;padding:15px}.modalBox{background:var(--surface);color:var(--text);border-radius:14px;padding:16px;max-width:900px;width:100%;max-height:90vh;overflow:auto;border:1px solid var(--border)}.editGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.editGrid textarea{min-height:80px;width:100%}.loadCard{border-color:var(--load-card-border)!important;background:var(--load-card-bg)!important}.loadWarn{background:var(--load-warn-bg);border:1px solid var(--load-warn-border);border-radius:10px;padding:10px;margin:10px 0;color:var(--load-warn-text)}.loadErr{color:#ef4444}#fsOnlyTools{display:none}body.fullde-mode{overflow:hidden}body.fullde-mode .top,body.fullde-mode #examStrip,body.fullde-mode #home{display:none!important}body.fullde-mode .wrap{max-width:none!important;margin:0!important;padding:0!important;width:100%!important}body.fullde-mode #quiz
{display:flex!important;flex-direction:column;position:fixed;inset:0;z-index:9999;background:var(--bg);padding:0;margin:0;overflow:hidden;width:100vw!important;max-width:none!important}body.fullde-mode #quiz>.panel:first-child{display:none}body.fullde-mode #quiz .quizLayout{flex:1;display:grid;grid-template-columns:minmax(0,1fr) 100px;gap:0;width:100%;max-width:none;height:100%;min-height:0;margin:0}body.fullde-mode #quiz .quizLayout>div:first-child{min-width:0;height:100%;display:flex;flex-direction:column}body.fullde-mode #quiz .quizToolbarStrip{flex-shrink:0;padding:4px 8px 2px;margin:0;border:none;background:var(--bg)}body.fullde-mode #quiz .quizLayout>div:first-child>.quizQuestionPanel{flex:1;display:flex;flex-direction:column;margin:0;border-radius:0;border-left:none;border-right:none;border-top:none;width:100%;max-width:none;min-height:0;overflow:auto}body.fullde-mode #quiz .quizLayout>div:last-child{display:flex!important;height:100%;min-height:0}body.fullde-mode #quiz .quizLayout>div:last-child>.panel{margin:0;border-radius:0;border-top:none;border-right:none;border-bottom:none;height:100%;padding:6px;display:flex;flex-direction:column;min-height:0;overflow:hidden}body.fullde-mode #quiz .quizLayout>div:last-child .line,body.fullde-mode #quiz .quizLayout>div:last-child .muted{display:none!important}body.fullde-mode #quiz .quizLayout>div:last-child .fsNavTitle{display:block!important;font-size:11px;text-align:center;margin:0 0 4px;font-weight:800;color:var(--muted);flex-shrink:0}body.fullde-mode #navNums{grid-template-columns:repeat(3,1fr);gap:3px;overflow-y:auto;flex:1;align-content:start}body.fullde-mode #navNums .num{padding:4px 0;font-size:11px;line-height:1.1}body.fullde-mode #fsOnlyTools{display:flex;position:sticky;top:0;z-index:5;justify-content:flex-end;gap:8px;flex-wrap:wrap;background:var(--surface);padding:6px 8px;border-bottom:1px solid var(--border);flex-shrink:0}body.fullde-mode #qid{font-size:15px;padding:0 8px;flex-shrink:0}body.fullde-mode #quiz .quizLayout>div:first-child .row:first-child{flex-shrink:0;padding:4px 8px 0}body.fullde-mode #qtext,body.fullde-mode #options,body.fullde-mode #solution,body.fullde-mode #hintBox{width:100%}body.fullde-mode #qtext{flex:0 0 auto;min-height:0;overflow:visible}body.fullde-mode #options{flex:0 0 auto;margin-top:8px;padding:0 8px 4px;position:relative;z-index:2;background:var(--bg)}body.fullde-mode #qtext .qimg{max-height:min(42vh,280px)}body.fullde-mode #hintBox{flex-shrink:0;max-height:38vh;overflow:auto;margin-top:8px}body.fullde-mode #fsOnlyTools button{font-size:12px;padding:5px 8px;white-space:nowrap}body.fullde-mode #fsOnlyTools .quizTimer{font-size:11px;padding:3px 8px}body.fullde-mode #hintBox .hintAdminBody{max-height:28vh;font-size:14px}body.fullde-mode #quizActions{display:none!important}body.fullde-mode #btnRetry,body.fullde-mode #btnEdit,body.fullde-mode #btnSubmit{display:none!important}@media(max-width:760px){body.fullde-mode #quiz .quizLayout{grid-template-columns:1fr;grid-template-rows:minmax(0,1fr) auto}body.fullde-mode #quiz .quizLayout>div:last-child{max-height:96px}body.fullde-mode #navNums{grid-template-columns:repeat(8,1fr);overflow-x:auto;overflow-y:hidden}body.fullde-mode #fsOnlyTools{gap:4px;padding:4px 6px;flex-wrap:wrap;justify-content:flex-start}body.fullde-mode #fsOnlyTools button{font-size:10px!important;padding:4px 6px!important}body.fullde-mode #fsOnlyTools .quizTimer{font-size:10px;padding:2px 6px}body.fullde-mode #qid{font-size:12px;line-height:1.3}body.fullde-mode #qtext{font-size:15px;padding:8px 10px!important}body.fullde-mode #qtext .qimg{max-height:min(36vh,220px);margin:8px auto 10px}body.fullde-mode #options{padding:0 6px 6px}body.fullde-mode .opt{padding:7px 8px;margin:4px 0;font-size:14px}body.fullde-mode #quiz .quizLayout>div:first-child>.panel{padding-bottom:6px}.wrap{padding:8px}.top{padding:8px 10px}.top h1{font-size:14px;min-width:0;flex:1 1 100%}.topRight{font-size:11px;gap:4px 8px}.adminTopBtn{font-size:10px;padding:4px 7px}.themeBtn{font-size:12px;padding:4px 8px}.examStrip{top:48px;padding:6px 8px;font-size:12px;flex-wrap:wrap}.panel{padding:10px;margin-bottom:10px;min-width:0}#quiz>.panel:first-child{flex-wrap:wrap;gap:8px}#quiz>.panel:first-child>div{width:100%}#resultBox{font-size:14px!important}.quizLayout>div{min-width:0}#quiz .panel>.row:first-child{flex-direction:column;align-items:stretch;gap:8px}#qid{font-size:13px;line-height:1.35;word-break:break-word}#quizActions{display:flex;flex-wrap:wrap;gap:4px;width:100%}#quizActions button{font-size:10px;padding:5px 7px;flex:0 1 auto}#quiz .panel>.row:last-child button{font-size:13px;padding:8px 12px;flex:1}.qbox{font-size:15px;padding:10px;min-height:0;overflow-wrap:anywhere}.opt{padding:8px;font-size:14px;margin:5px 0}.qimg{max-height:min(40vh,240px)}.tfrow{grid-template-columns:28px minmax(0,1fr) 34px;grid-template-areas:"lbl stmt opts";gap:4px 6px;padding:7px 8px;align-items:start}.tfrow>b,.tfrow .dsCircle{grid-area:lbl;justify-self:center}.tfStmt{grid-area:stmt;font-size:14px}.tfOpts{grid-area:opts;flex-direction:column;justify-content:flex-start;align-items:stretch;gap:3px;padding:0;width:34px}.tfOptsHead{display:grid;grid-template-columns:28px minmax(0,1fr) 34px;gap:4px 6px;margin:0 0 4px;padding:0 8px;font-size:10px;font-weight:800;color:var(--muted);align-items:center}.tfColHead{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;line-height:1.15;text-align:center}.tfOptsHead .tfLblShort{display:flex;flex-direction:column;align-items:center}.tfOptsHead .tfLblFull{display:none}.tfLblFull{display:none}.tfLblShort{display:inline}.tfOpt{flex:0;width:100%;max-width:none;min-width:0;padding:5px 2px;font-size:12px;border-radius:6px;text-align:center}.tfOpt input{position:absolute;opacity:0;width:0;height:0;margin:0}}html:fullscreen,body:fullscreen{background:var(--bg)}@media(max-width:900px){.quizLayout{grid-template-columns:1fr}.editGrid{grid-template-columns:1fr}.qbox{font-size:16px}.top h1{font-size:16px}.examStrip{top:52px;font-size:13px}}
</style></head>
<body><div class="top"><div class="topRow"><h1>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</h1><div class="topRight"><span id="quizTopBar" class="adminBar hide"><button type="button" class="adminTopBtn adminTopBtn2" onclick="backHome()">← Về mục lục</button></span><span id="adminBar" class="adminBar hide"><button type="button" id="syncBtn" class="adminTopBtn" onclick="syncData()">🔄 Đồng bộ Sheet</button><button type="button" id="dedupeBtn" class="adminTopBtn adminTopBtn2" onclick="dedupeSheetDuplicates()">🧹 Xóa trùng Sheet</button><button type="button" id="testAiBtn" class="adminTopBtn adminTopBtn2" onclick="testServerAiKey()">🧪 Test AI</button></span><span id="info">Đang nạp...</span> | <span id="me"></span> <span id="aiProfileBadge" class="aiProfileBadge hide"></span> | <button type="button" id="btnTheme" class="themeBtn" onclick="toggleTheme()" title="Chuyển giao diện tối">🌙</button> <a href="/logout">Thoát</a></div></div></div>
<div id="examStrip" class="examStrip"><span id="examMsg">📢 Thông báo kỳ thi</span><span id="examTimer" class="timer"></span></div>
<div class="wrap">
<div id="home"><div id="aiProfileBanner" class="aiProfileBanner hide"></div><div class="panel"><b>Thiết lập luyện tập</b><div class="row" style="margin-top:10px"><div class="field"><label>Môn</label><select id="fMon" onchange="onFilterChange('mon')"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="fLop" onchange="onFilterChange('lop')"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="fChuong" onchange="onFilterChange('chuong')"><option value="">Tất cả</option></select></div><div class="field"><label>Bài học</label><select id="fBaiHoc" onchange="onFilterChange('baihoc')"><option value="">Tất cả</option></select></div><div class="field"><label>Bộ đề</label><select id="fBoDe" onchange="onFilterChange('bode')"><option value="">Tất cả</option></select></div><div class="field"><label>Mức độ</label><select id="fMucDo" onchange="onFilterChange('extra')"><option value="">Tất cả</option><option value="NB">NB</option><option value="TH">TH</option><option value="VD">VD</option><option value="VDC">VDC</option></select></div><div class="field"><label>Dạng câu</label><select id="fDang" onchange="onFilterChange('extra')"><option value="">Tất cả</option><option value="Trắc nghiệm">Trắc nghiệm</option><option value="Đúng sai">Đúng sai</option><option value="Trả lời ngắn">Trả lời ngắn</option><option value="Tự luận">Tự luận</option></select></div><div class="field"><label>Tìm nhanh</label><input id="fSearch" placeholder="Nhập từ khóa..." oninput="onFilterChange('extra')"></div><button class="btn" onclick="renderCatalog()">Lọc đề</button></div></div><div id="idLookupPanel" class="panel"><b>🔎 Tìm theo ID câu</b><p class="muted" style="margin:6px 0 8px;line-height:1.45">Mỗi câu có <b>ID</b> (vd. <code>AUTO_caab355259</code>) trên thanh khi làm bài — học sinh tra cứu, ADMIN mở để sửa nhanh.</p><div class="row" style="flex-wrap:wrap;gap:8px;align-items:flex-end"><div class="field" style="flex:1;min-width:220px"><label>ID câu</label><input id="fIdLookup" placeholder="AUTO_... hoặc một phần ID" onkeydown="if(event.key==='Enter')lookupQuestionById()"></div><button type="button" class="btn" onclick="lookupQuestionById()">Tìm</button></div><div id="idLookupResult" style="margin-top:10px"></div></div><div id="aiKeyPanel" class="panel hide"><b>🔑 Key AI của tôi (Gemini)</b><div id="aiProfileDetail" class="aiProfileBanner aiProfileBannerOk hide" style="margin:8px 0 10px"></div><p class="muted" style="margin:6px 0 10px">Chỉ dùng key <b>AIzaSy...</b> từ <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">Google AI Studio</a> (Create API key). <b>Không</b> dùng key <b>AQ...</b> hay key Google Cloud khác. Key của bạn được ưu tiên; không có thì dùng key server Render.</p><textarea id="myApiKeys" rows="3" style="width:100%;min-height:72px;font-family:Consolas,monospace" placeholder="AIzaSy...&#10;(có thể nhiều dòng — tự đổi khi hết quota)"></textarea><div class="row" style="margin-top:8px;flex-wrap:wrap"><button type="button" class="btn2" onclick="testMyAiKey()">🧪 Test key</button><button type="button" class="btnGreen" onclick="saveMyAiKey()">💾 Lưu key</button><button type="button" class="btn2" onclick="clearMyAiKey()">🗑 Xóa key của tôi</button></div><div id="aiKeyStatus" class="muted" style="margin-top:8px;font-size:13px"></div></div><div class="panel practiceRandomPanel"><b>🎲 Tự luyện ngẫu nhiên</b><p class="muted" style="margin:6px 0 8px">Ghép đề <b>28 câu</b> (18 TN · 4 Đ/S · 6 TLN). Chọn <b>Môn · Khối · Lớp</b> — khóa sau khi chọn đủ; sau đó chọn một hoặc nhiều <b>Chương</b> (hoặc tất cả).</p><div class="row" style="margin-top:8px;flex-wrap:wrap"><div class="field"><label>Môn <span class="muted">*</span></label><select id="rpMon" onchange="onRpScopeChange('mon')"><option value="">— Chọn môn —</option></select></div><div class="field"><label>Khối <span class="muted">*</span></label><select id="rpKhoi" onchange="onRpScopeChange('khoi')" disabled><option value="">— Chọn khối —</option></select></div><div class="field"><label>Lớp <span class="muted">*</span></label><select id="rpLop" onchange="onRpScopeChange('lop')" disabled><option value="">— Chọn lớp —</option></select></div><div class="field" style="align-self:flex-end"><button type="button" class="btn2" id="btnRpUnlock" onclick="unlockRpScope()" style="display:none">🔓 Đổi Môn/Khối/Lớp</button></div></div><div id="rpScopeNote" class="hide" style="margin:8px 0;padding:8px 10px;border-radius:8px;background:#dbeafe;border:1px solid #93c5fd;color:#1e3a8a;font-weight:800;font-size:13px"></div><div id="rpChuongWrap" class="hide" style="margin-top:8px"><b>Chương</b><label style="display:flex;gap:8px;align-items:center;margin:8px 0 6px;font-size:13px"><input type="checkbox" id="rpChuongAll" checked onchange="toggleRpChuongAll()"> <b>Tất cả chương</b> trong phạm vi đã chọn</label><div id="rpChuongList" class="rpChuongList"></div></div><label style="display:flex;gap:8px;align-items:center;margin:10px 0 8px;font-size:13px"><input type="checkbox" id="fSolFullOnly" onchange="renderCatalog()"> Chỉ lấy câu có <b>lời giải đầy đủ</b> 📗</label><button type="button" class="btnStartStrong" onclick="startRandomPractice()">🎲 Bắt đầu tự luyện ngẫu nhiên</button><div class="muted" style="margin-top:8px;font-size:12px;line-height:1.45">📗 LG đầy đủ = có đáp án + lời giải đủ từng dạng. Khối suy từ cột Lớp (vd. 12QT1 → Khối 12).</div></div><div class="panel"><b>Mục lục đề</b> <span id="countCat" class="muted"></span><div id="catalog" class="grid" style="margin-top:10px"></div></div></div>
<div id="quiz" class="hide"><div class="panel row" style="justify-content:space-between"><div><span id="quizTitle" style="font-weight:800"></span> <span id="filterBadge" class="tag hide"></span> <span id="shuffleBadge" class="tag hide"></span></div><div style="display:flex;gap:10px;align-items:center"><div id="quizTimer" class="quizTimer">⏱ <span id="quizTimerText">00:00</span></div><span id="vipSolBtnsTop" class="vipSolBtnsTop hide"><button type="button" id="btnTopShowAns" class="btnMobileSolToggle" onclick="toggleQuestionAnswer(event)" title="Xem/ẩn đáp án">Đáp án</button><button type="button" id="btnTopShowExp" class="btnMobileSolToggle" onclick="toggleQuestionExplain(event)" title="Xem/ẩn lời giải">Lời giải</button></span><div id="resultBox" style="font-weight:800;font-size:18px"></div></div></div><div class="quizLayout"><div><div class="quizToolbarStrip"><div class="quizToolbarHead"><div class="qid" id="qid"></div><div id="quizIdJumpWrap" class="quizIdJumpWrap hide"><input id="quizIdJump" class="quizIdJumpInp" placeholder="Tìm ID trong đề…" title="ADMIN: nhập ID → Enter" onkeydown="if(event.key==='Enter')jumpToIdInQuiz()"><button type="button" class="btn2 quizIdJumpBtn" onclick="jumpToIdInQuiz()" title="Nhảy tới ID">→</button></div><div id="quizAdminTools" class="quizAdminTools hide"><button type="button" id="btnEdit" class="btn2" onclick="openEdit()">✏️ Sửa câu</button><button type="button" id="btnAdd" class="btn2" onclick="openAddQuestion()">➕ Thêm câu</button><button type="button" id="btnInfographic" class="btn2" onclick="openInfographicPrompt()">📊 Infographic</button></div></div><div class="quizToolsRow"><button type="button" id="btnQuizToolsToggle" class="btnQuizToolsToggle" onclick="toggleQuizTools(event)" title="Công cụ làm bài" aria-expanded="false">☰</button><div class="quizNavRow hide-mobile"><button type="button" class="btnNavMini" onclick="prevQ()" title="Câu trước" aria-label="Câu trước">‹</button><button type="button" class="btnNavWide hide-mobile" onclick="prevQ()">← Câu trước</button><button type="button" class="btnNavWide btnNavPrimary hide-mobile" onclick="nextQ()">Câu sau →</button><button type="button" class="btnNavMini btnNavPrimary" onclick="nextQ()" title="Câu sau" aria-label="Câu sau">›</button></div><div id="quizActions" class="quizActionsPanel"><button id="btn5050" class="btn2" onclick="use5050()">Loại 2 câu sai</button><button type="button" id="btnQuizShowAns" class="btn2 btnSolToggle hide" onclick="toggleQuestionAnswer(event)" title="Xem/ẩn đáp án">Đáp án</button><button type="button" id="btnQuizShowExp" class="btn2 btnSolToggle hide" onclick="toggleQuestionExplain(event)" title="Xem/ẩn lời giải">Lời giải</button><button id="btnHint" class="btn2" onclick="requestHint()">💡 Gợi ý AI</button><button id="btnSimilar" class="btn2 hide" onclick="requestSimilarQuestion()">📝 Tạo câu tương tự</button><button id="btnRetry" class="btn2" onclick="openRetryModal()">🔁 Làm lại đề</button><button id="btnPresent" class="btn2" onclick="toggleQuizFullscreen()">📽 Full màn hình</button><button id="btnSubmit" class="btn2" onclick="submitQuiz()">Nộp bài</button></div></div><div id="fsOnlyTools"><button class="btn2" onclick="backHome()">← Mục lục</button><button type="button" id="btnFsToolsToggle" class="btn2 btnFsToolsToggle hide" onclick="toggleQuizTools(event)" title="Công cụ" aria-expanded="false">☰</button><div id="fsQuizTimer" class="quizTimer">⏱ <span id="fsQuizTimerText">00:00</span></div><button id="btnFsSync" class="btn2 hide" onclick="syncData()">🔄 Đồng bộ</button><button id="btnFsEdit" class="btn2 hide" onclick="openEdit()">✏️ Sửa câu</button><button id="btnFsAdd" class="btn2 hide" onclick="openAddQuestion()">➕ Thêm câu</button><button id="btnFsInfographic" class="btn2 hide" onclick="openInfographicPrompt()">📊 Infographic</button><button id="btnFs5050" class="btn2" onclick="use5050()">50-50</button><button type="button" id="btnFsShowAns" class="btn2 btnSolToggle hide" onclick="toggleQuestionAnswer(event)" title="Xem/ẩn đáp án">Đáp án</button><button type="button" id="btnFsShowExp" class="btn2 btnSolToggle hide" onclick="toggleQuestionExplain(event)" title="Xem/ẩn lời giải">Lời giải</button><button id="btnFsHint" class="btn2" onclick="requestHint()">💡 Gợi ý AI</button><button id="btnFsSimilar" class="btn2 hide" onclick="requestSimilarQuestion()">📝 Câu tương tự</button><button type="button" id="btnFsTheme" class="btn2" onclick="toggleTheme()">🌙 Tối</button><button class="btn2" onclick="toggleQuizFullscreen()">⤢ Thoát full</button></div></div><div class="panel quizQuestionPanel"><div id="qtext" class="qbox"></div><div id="options"></div><div id="solution" class="solution hide"></div><div id="hintBox" class="solution hide"></div></div></div><div class="panel fsNavPanel"><div class="mobileNavDock"><div class="mobileDockNavGroup"><button type="button" id="btnMobilePrev" class="btnMobileNavMini" onclick="prevQ()" title="Câu trước" aria-label="Câu trước">‹</button><div id="mobileQuizTimer" class="quizTimer mobileDockTimer">⏱ <span id="mobileQuizTimerText">00:00</span></div><button type="button" id="btnMobileNext" class="btnMobileNavMini btnMobileNavPrimary" onclick="nextQ()" title="Câu sau" aria-label="Câu sau">›</button></div><div id="mobileDockVipBtns" class="mobileDockMid hide"><button type="button" id="btnMobileShowAns" class="btnMobileSolToggle" onclick="toggleQuestionAnswer(event)" title="Xem/ẩn đáp án">Đáp án</button><button type="button" id="btnMobileShowExp" class="btnMobileSolToggle" onclick="toggleQuestionExplain(event)" title="Xem/ẩn lời giải">Lời giải</button></div><button type="button" id="btnMobileNavToggle" class="btnMobileNavToggle" onclick="toggleMobileNavBoard(event)" aria-expanded="false" title="Mở/đóng bảng câu hỏi">▾ Bảng câu</button></div><div class="mobileNavBody"><b class="fsNavTitle">Bảng câu hỏi</b><div id="navNums" class="navNums" style="margin-top:10px"></div><div class="line"></div><div class="muted">ADMIN vào đề sẽ thấy đáp án/lời giải ngay và được sửa câu.</div></div></div></div></div>
</div><div id="startModal" class="modal hide"><div class="modalBox" style="max-width:520px"><h3 id="startModalTitle">Thiết lập làm bài</h3><p class="muted">Chọn cách xáo trộn để tự rèn luyện. Có thể giữ nguyên thứ tự như đề gốc.</p><p id="startFilterNote" class="hide" style="margin:8px 0;padding:8px 10px;border-radius:8px;background:#dcfce7;border:1px solid #86efac;color:#166534;font-weight:800;font-size:13px"></p><div style="display:flex;flex-direction:column;gap:10px;margin:14px 0"><label style="display:flex;gap:8px;align-items:flex-start;padding:10px;border:1px solid var(--border);border-radius:10px"><input type="checkbox" id="chkShuffleQ"> <span><b>Xáo trộn câu hỏi</b><br><span class="muted">Đổi thứ tự các câu trong đề.</span></span></label><label style="display:flex;gap:8px;align-items:flex-start;padding:10px;border:1px solid var(--border);border-radius:10px"><input type="checkbox" id="chkGroupDang" checked> <span><b>Nhóm theo dạng câu</b><br><span class="muted">Trắc nghiệm → Đúng/Sai → Trả lời ngắn → Tự luận (xáo câu chỉ trong từng nhóm).</span></span></label><label style="display:flex;gap:8px;align-items:flex-start;padding:10px;border:1px solid var(--border);border-radius:10px"><input type="checkbox" id="chkShuffleA"> <span><b>Xáo trộn đáp án</b><br><span class="muted">Xáo trộn các ý A-B-C-D (trắc nghiệm + đúng/sai); mỗi ý vẫn ghép đúng đáp án/lời giải.</span></span></label></div><div class="row" style="justify-content:flex-end;gap:8px"><button onclick="closeStartModal()">Hủy</button><button class="btn2" onclick="pickShufflePreset('none')">Giữ nguyên</button><button class="btn" onclick="confirmStartQuiz()">Bắt đầu</button></div></div></div><div id="modal" class="modal hide"><div class="modalBox"><h3 id="editModalTitle">ADMIN: Sửa câu hỏi</h3><div id="editForm" class="editGrid"></div><div class="row" style="justify-content:space-between;margin-top:12px"><button id="btnDeleteQuestion" class="btnRed" onclick="deleteQuestion()">Xóa câu này khỏi Google Sheet</button><div><button onclick="closeEdit()">Hủy</button><button id="btnSaveQuestion" class="btn" onclick="saveQuestionModal()">Lưu vào Google Sheet</button></div></div><div class="muted" style="margin-top:8px" id="editModalNote">Xóa liên tiếp được — app tự cập nhật số dòng Sheet, không cần đồng bộ lại sau mỗi lần xóa. Chỉ bấm Đồng bộ khi sửa trực tiếp trên Google Sheet.</div></div></div><div id="infographicModal" class="modal hide"><div class="modalBox" style="max-width:760px"><h3 id="infographicModalTitle">📊 Prompt Gemini — Infographic</h3><p class="muted" style="margin:6px 0 10px;line-height:1.45">Gemini vẽ <b>poster hiện đại đầy màu</b> — 4 card gradient (Đề → Phương án → Hình → Lời giải), không chữ «Khối». VIP/SVIP: mở khóa sau khi <b>trả lời đúng</b>.</p><textarea id="infographicPromptText" class="infographicPromptBox" readonly placeholder="Đang tạo prompt…"></textarea><div class="row" style="justify-content:space-between;margin-top:12px;flex-wrap:wrap;gap:8px"><a id="infographicGeminiLink" class="btn2" href="https://gemini.google.com/app" target="_blank" rel="noopener">↗ Mở Gemini</a><div style="display:flex;gap:8px"><button type="button" onclick="closeInfographicModal()">Đóng</button><button type="button" class="btn" onclick="copyInfographicPrompt()">📋 Chép prompt</button></div></div></div></div><script>
let META=null,CATALOG=[],USER={},SID='',QUESTIONS=[],CUR=0,ANSWERS={},SUBMITTED=false,RESULTS={},CHECKED={},LOCKED_Q={},CURRENT_MADE='',CURRENT_LEVEL='',CURRENT_DANG='',START_IS_RETRY=false,GROUP_BY_DANG=true,RANDOM_PRACTICE=false,RP_SCOPE_LOCKED=false,QUIZ_ELAPSED=0,QUIZ_TIMER=null,FS_ANS_FORCE=null,FS_EXP_FORCE=null,FULLDE_ON=false,FS_NAV_HIDDEN=false,COMPLETED_NOTICE=false,HINT_BY_Q={},HINT_LOADING=false,HINT_LOADING_Q=null,SIMILAR_BY_Q={},SIMILAR_LOADING=false,SIMILAR_LOADING_Q=null,MOBILE_QUIZ_TOOLS_OPEN=false,MOBILE_NAV_OPEN=false,QUIZ_SCROLL_Y=0,VIP_Q_SHOW_ANS={},VIP_Q_SHOW_EXP={},QUESTION_MODAL_MODE='edit',ADMIN_HINT_SAVED={};
const THEME_KEY='LDVL_THEME';
function applyTheme(mode){let dark=mode==='dark';document.documentElement.setAttribute('data-theme',dark?'dark':'light');try{localStorage.setItem(THEME_KEY,dark?'dark':'light')}catch(e){}let b=document.getElementById('btnTheme');if(b){b.textContent=dark?'☀️':'🌙';b.title=dark?'Chuyển giao diện sáng':'Chuyển giao diện tối'}let bf=document.getElementById('btnFsTheme');if(bf)bf.textContent=dark?'☀️ Sáng':'🌙 Tối';if(window.MathJax&&MathJax.config&&MathJax.config.svg){MathJax.config.svg.color=dark?'#e2e8f0':'#0f172a';if(MathJax.typesetPromise)MathJax.typesetPromise().catch(()=>{})}}
function toggleTheme(){let cur=document.documentElement.getAttribute('data-theme')||'light';applyTheme(cur==='dark'?'light':'dark')}
function initTheme(){let t='light';try{t=localStorage.getItem(THEME_KEY)||'light'}catch(e){}applyTheme(t==='dark'?'dark':'light')}
function enhanceHomeColors(){
    if(document.getElementById('LDVL_HOME_COLORS'))return;
    let st=document.createElement('style');
    st.id='LDVL_HOME_COLORS';
    st.textContent=
        ".card{border:1px solid #bfdbfe;border-radius:14px;background:linear-gradient(180deg,#ffffff,#f8fbff);box-shadow:0 8px 22px #1d4ed81a}"+
        ".card h3{color:#1e40af;font-size:30px;font-weight:900;letter-spacing:.2px}"+
        ".tag{background:linear-gradient(135deg,#dbeafe,#bfdbfe);color:#1d4ed8;border:1px solid #93c5fd;padding:4px 10px;font-weight:900}"+
        ".btnStartStrong{box-shadow:0 10px 22px #4338ca55,0 2px 6px #1e40af55;transform:translateZ(0)}"+
        ".btnStartStrong:hover{filter:brightness(1.08);transform:translateY(-1px)}"+
        "html[data-theme='dark'] .card{background:linear-gradient(180deg,#1e293b,#182236);border-color:#334155;box-shadow:0 10px 24px #0005}"+
        "html[data-theme='dark'] .card h3{color:#93c5fd}"+
        "html[data-theme='dark'] .tag{background:linear-gradient(135deg,#1e3a5f,#1d4ed8);color:#e0ecff;border-color:#3b82f6}"+
        ".shareRow{margin-top:8px;padding:8px 10px;border:1px dashed #93c5fd;border-radius:10px;background:#f8fbff;display:flex;flex-wrap:wrap;gap:6px;align-items:center;justify-content:space-between}"+
        ".shareUrl{font-size:11px;color:#64748b;word-break:break-all;flex:1;min-width:0;line-height:1.35}"+
        ".btnShare{font-size:11px;padding:5px 10px;border-radius:8px;border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;font-weight:800;white-space:nowrap}"+
        ".btnShare:hover{filter:brightness(1.03)}"+
        ".card.shareTarget{outline:3px solid #60a5fa;box-shadow:0 0 0 4px #dbeafe}"+
        "html[data-theme='dark'] .shareRow{background:#1e293b;border-color:#3b82f6}"+
        "html[data-theme='dark'] .shareUrl{color:#94a3b8}"+
        "html[data-theme='dark'] .btnShare{background:#1e3a5f;color:#bfdbfe;border-color:#3b82f6}"+
        ".shortAnsFb{padding:8px 10px;border-radius:8px;margin-top:8px;font-weight:800;line-height:1.45}"+
        ".shortAnsFb.ok{background:#dcfce7;color:#166534;border:1px solid #86efac}"+
        ".shortAnsFb.bad{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}"+
        ".shortAnsBox.correct{border-color:#86efac!important;box-shadow:0 0 0 2px #dcfce7}"+
        ".shortAnsBox.wrong{border-color:#fecaca!important;box-shadow:0 0 0 2px #fee2e2}"+
        ".adminTlnAns{margin-top:8px;padding:8px 10px;border-radius:8px;background:#dcfce7;border:1px solid #86efac;color:#166534;font-weight:800;line-height:1.45}"+
        ".adminTlnAnsWarn{background:#fff7ed;border-color:#fed7aa;color:#9a3412;font-weight:700}"+
        ".mucdoBadge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:900;letter-spacing:.4px;border:2px solid transparent;vertical-align:middle;line-height:1.35;margin:0 2px}"+
        ".mucdo-nb{background:#dcfce7;color:#166534;border-color:#86efac}"+
        ".mucdo-th{background:#dbeafe;color:#1d4ed8;border-color:#93c5fd}"+
        ".mucdo-vd{background:#ffedd5;color:#c2410c;border-color:#fdba74}"+
        ".mucdo-vdc{background:#fee2e2;color:#991b1b;border-color:#fca5a5}"+
        ".mucdo-other{background:#f1f5f9;color:#334155;border-color:#cbd5e1}"+
        ".mucdo-empty{background:#f8fafc;color:#94a3b8;border-color:#e2e8f0;font-weight:700}"+
        ".qidDang{font-weight:800;color:var(--heading)}"+
        "html[data-theme='dark'] .mucdo-nb{background:#14532d;color:#bbf7d0;border-color:#22c55e}"+
        "html[data-theme='dark'] .mucdo-th{background:#1e3a5f;color:#bfdbfe;border-color:#3b82f6}"+
        "html[data-theme='dark'] .mucdo-vd{background:#7c2d12;color:#fed7aa;border-color:#ea580c}"+
        "html[data-theme='dark'] .mucdo-vdc{background:#450a0a;color:#fecaca;border-color:#ef4444}"+
        ".adminAnalysisCard{margin-bottom:10px}"+
        ".adminAnalysisOk{padding:8px 10px;border-radius:8px;background:#dcfce7;border:1px solid #86efac;color:#166534;font-weight:800}"+
        ".adminAnalysisWarn{padding:8px 10px;border-radius:8px;background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;font-weight:800;line-height:1.45}"+
        ".adminAnalysisTbl{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px}"+
        ".adminAnalysisTbl th,.adminAnalysisTbl td{border:1px solid var(--border);padding:5px 7px;text-align:center}"+
        ".adminAnalysisTbl th{background:#f1f5f9;font-weight:800}"+
        ".adminAnalysisBadRow td{background:#fee2e2}"+
        ".adminAnalysisOkRow td{background:#f0fdf4}"+
        ".aiProfileBadge{display:inline-block;margin-left:6px;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:900;vertical-align:middle;white-space:nowrap}"+
        ".aiProfileOwn{background:#dcfce7;color:#166534;border:1px solid #86efac}"+
        ".aiProfilePool{background:#fff7ed;color:#9a3412;border:1px solid #fed7aa}"+
        ".aiProfileWarn{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}"+
        ".aiProfileFree{background:#f1f5f9;color:#64748b;border:1px solid #cbd5e1}"+
        ".aiProfileBanner{margin:0 0 12px;padding:12px 14px;border-radius:12px;border:1px solid var(--border);background:var(--surface);line-height:1.5}"+
        ".aiProfileBannerOk{border-color:#86efac;background:#f0fdf4}"+
        ".aiProfileBannerNudge{border-color:#fed7aa;background:#fff7ed}"+
        ".aiProfileBannerErr{border-color:#fca5a5;background:#fef2f2}"+
        ".aiProfileBannerTxt{margin-top:4px;font-size:13px;color:var(--muted)}"+
        ".aiProfileBannerBtn{margin-top:8px}"+
        ".adminChipRow{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}"+
        ".adminChip{border:1px solid var(--border);background:var(--surface);color:var(--text);padding:7px 12px;border-radius:999px;font-size:13px;font-weight:800;cursor:pointer;line-height:1.2}"+
        ".adminChip:hover{border-color:#93c5fd;background:#eff6ff}"+
        ".adminChipOn{background:linear-gradient(135deg,#1d4ed8,#2563eb);color:#fff;border-color:#1d4ed8;box-shadow:0 2px 8px #1d4ed844}"+
        ".adminChip.mucdo-nb.adminChipOn{background:linear-gradient(135deg,#22c55e,#16a34a);border-color:#22c55e}"+
        ".adminChip.mucdo-th.adminChipOn{background:linear-gradient(135deg,#3b82f6,#2563eb);border-color:#3b82f6}"+
        ".adminChip.mucdo-vd.adminChipOn{background:linear-gradient(135deg,#f59e0b,#ea580c);border-color:#f59e0b}"+
        ".adminChip.mucdo-vdc.adminChipOn{background:linear-gradient(135deg,#dc2626,#b91c1c);border-color:#dc2626}"+
        ".adminChipFree.adminChipOn{background:linear-gradient(135deg,#64748b,#475569);border-color:#64748b}"+
        ".adminChipVip.adminChipOn{background:linear-gradient(135deg,#7c3aed,#6d28d9);border-color:#7c3aed}"+
        ".adminQuickField{margin-bottom:12px}"+
        ".adminQuickField input[type=hidden]{display:none}"+
        ".solFullTag{background:#dcfce7!important;color:#166534!important;border:1px solid #86efac!important}"+
        ".solPartTag{background:#fff7ed!important;color:#9a3412!important;border:1px solid #fed7aa!important}"+
        ".quizSectionHead{margin:12px 0 8px;padding:10px 12px;border-radius:10px;background:linear-gradient(135deg,#eff6ff,#dbeafe);border:1px solid #93c5fd;font-weight:900;color:#1e3a8a}"+
        ".navSectionLbl{grid-column:1/-1;font-size:11px;font-weight:900;color:#1d4ed8;padding:4px 2px 0;text-align:left}"+
        ".practiceRandomPanel{border:1px solid #93c5fd;background:linear-gradient(135deg,#eff6ff,#f0fdf4)}"+
        ".rpChuongList{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}"+
        ".rpChuongList label{display:flex;gap:6px;align-items:center;padding:6px 10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--surface);cursor:pointer}"+
        ".rpChuongList label.rpChOn{border-color:#3b82f6;background:#eff6ff;font-weight:800}"+
        ".practiceRandomPanel.rpLocked select.rpLockable{background:#f1f5f9;opacity:.92}";
    document.head.appendChild(st);
}
function shortAnswerFeedbackHtml(q){let r=RESULTS[CUR]||CHECKED[CUR];if(!r||!(r.ok===true||r.ok===false))return '';let chosen=esc(String(r.chosen||ANSWERS[CUR]||'').trim());if(r.ok===true)return `<div class="shortAnsFb ok">✅ <b>Đúng!</b>${chosen?` Bạn nhập: <b>${chosen}</b>`:''}</div>`;let extra='';if(canViewSolutionLive()||USER.is_admin){let cor=esc(String(r.correct||r.DapAn||q.DapAn||'').trim());if(cor)extra=`<div style="margin-top:4px;font-size:13px">Đáp án đúng: <b>${cor}</b></div>`}else extra='<div style="margin-top:4px;font-size:12px;font-weight:600">Nâng VIP để xem đáp án đúng ngay sau khi kiểm tra.</div>';return `<div class="shortAnsFb bad">❌ <b>Chưa đúng.</b> Bạn nhập: <b>${chosen||'—'}</b></div>${extra}`}
function examDisplayTitle(item){item=item||{};let mon=String(item.Mon||'').trim();let lop=String(item.Lop||'').trim();let bai=String(item.BaiHoc||item.De||'Đề luyện tập').trim();if(mon){let head=lop?mon+' - Lớp '+lop:mon;return head+' | '+bai}if(lop)return'Lớp '+lop+' | '+bai;return bai}
function getShareParams(){let p=new URLSearchParams(location.search);let de=(p.get('de')||p.get('made')||'').trim();if(!de){let m=location.pathname.match(/^\/d\/([^/]+)/i);if(m)de=decodeURIComponent(m[1])}let fromShort=/^\/d\//i.test(location.pathname);let open=p.get('open')==='1';return{de,level:(p.get('level')||'').trim().toUpperCase(),dang:(p.get('dang')||'').trim(),start:p.get('start')==='1'||(fromShort&&!open),open:!fromShort?p.get('start')!=='1'&&(p.get('open')||'1')!=='0':open,sq:p.get('sq')==='1',sa:p.get('sa')==='1'}}
function buildExamShareUrl(item,extra){item=item||{};extra=extra||{};let de=extra.de||item.MaDe||'';if(!de)return location.origin+'/';let auto=extra.start!==0&&extra.start!=='0';let u=new URL(location.origin+'/d/'+de);if(!auto)u.searchParams.set('open','1');if(extra.sq)u.searchParams.set('sq','1');if(extra.sa)u.searchParams.set('sa','1');let lv=extra.level||val('fMucDo')||'';let dg=extra.dang||val('fDang')||'';if(lv)u.searchParams.set('level',lv);if(dg)u.searchParams.set('dang',dg);return u.toString()}
function clearShareQuery(){let p=new URLSearchParams(location.search);if(!p.get('de')&&!p.get('made'))return;['de','made','mon','lop','chuong','baihoc','bode','level','dang','open','start','sq','sa'].forEach(k=>p.delete(k));let q=p.toString();history.replaceState(null,'',location.pathname+(q?'?'+q:''))}
function setSel(id,v){let el=document.getElementById(id);if(!el||!v)return;for(let o of el.options){if(o.value===v){el.value=v;return}}let opt=document.createElement('option');opt.value=v;opt.textContent=v;el.appendChild(opt);el.value=v}
async function copyTextToClipboard(text){try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(text);return true}}catch(e){}let ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();try{document.execCommand('copy');document.body.removeChild(ta);return true}catch(e){document.body.removeChild(ta);return false}}
async function copyExamShareLink(made,withModal){let item=CATALOG.find(x=>x.MaDe===made);if(!item){alert('Không tìm thấy đề.');return}let url=buildExamShareUrl(item,withModal?{start:0,open:1}:{start:1});let ok=await copyTextToClipboard(url);let ten=examDisplayTitle(item);let socau=item.SoCau?(item.SoCau+' câu'):'';let note=withModal?'Học viên mở link sẽ chọn xáo trộn trước khi làm.':'Học viên mở link sẽ vào làm bài luôn.';alert(ok?'✅ Đã chép link gửi Zalo/Messenger.\n\n'+ten+(socau?'\n'+socau:'')+'\n'+note:'Không chép được. Hãy bấm lại nút Chép link.')}
let ID_LOOKUP_MATCHES=[];
function setVal(id,v){let el=document.getElementById(id);if(el)el.value=v==null?'':String(v)}
function findQuestionIndexById(id){let u=String(id||'').trim().toUpperCase();if(!u)return -1;for(let i=0;i<QUESTIONS.length;i++){let qid=String(QUESTIONS[i].ID||'').trim().toUpperCase();if(qid===u)return i}return -1}
async function lookupQuestionById(){let raw=String(val('fIdLookup')||'').trim();if(!raw){alert('Nhập ID câu.');return}let box=document.getElementById('idLookupResult');if(box)box.innerHTML='<span class="muted">Đang tìm…</span>';try{let j=await api('/api/question/lookup?id='+encodeURIComponent(raw));if(j.loading){if(box)box.innerHTML='<span class="muted">'+esc(j.message||j.error||'Đang nạp Sheet…')+'</span>';setTimeout(lookupQuestionById,2500);return}renderIdLookupResult(j)}catch(e){if(box)box.innerHTML='<span style="color:#991b1b">'+esc(e.message)+'</span>'}}
function renderIdLookupResult(j){let box=document.getElementById('idLookupResult');if(!box)return;let matches=j.matches||[];ID_LOOKUP_MATCHES=matches;if(!matches.length){box.innerHTML='<span class="muted">Không tìm thấy ID «'+esc(j.id||val('fIdLookup')||'')+'».</span>';return}let admin=!!USER.is_admin;box.innerHTML=matches.map((m,i)=>{let openBtn=`<button class="btn" type="button" onclick="openQuestionByIdMatch(${i},false)">🚀 Mở đề</button>`;let editBtn=admin?`<button class="btn2" type="button" onclick="openQuestionByIdMatch(${i},true)">✏️ Mở & sửa</button>`:'';let copyBtn=m.ID?`<button class="btn2" type="button" onclick="copyIdFromLookup('${escAttr(m.ID)}')">📋 Chép ID</button>`:'';return `<div class="idLookupCard"><h4>ID: ${esc(m.ID)} · Câu ${m.question_no||'?'} · ${esc(m.MaDe)}</h4><div class="idLookupMeta"><span class="tag">${esc(m.Mon)}</span> Lớp ${esc(m.Lop)} · ${esc(m.Chuong||'')} · ${esc(m.BaiHoc||'')}</div><div class="idLookupMeta">${esc(m.Dang||'')} · ${esc(m.MucDo||'')} · ${esc(m.QuyenTruyCap||'VIP')}</div><div class="idLookupPreview">${esc(m.preview||'')}</div><div class="row" style="margin-top:8px;flex-wrap:wrap;gap:6px">${openBtn}${editBtn}${copyBtn}</div></div>`}).join('')}
async function copyIdFromLookup(id){let ok=await copyTextToClipboard(id);alert(ok?'✅ Đã chép ID: '+id:'Không chép được.')}
async function openQuestionByIdMatch(idx,doEdit){let m=ID_LOOKUP_MATCHES[idx];if(!m||!m.MaDe){alert('Không có mã đề.');return}if(USER.is_trial&&(m.QuyenTruyCap||'VIP')!=='FREE'){alert('Tài khoản dùng thử chỉ mở đề FREE.');return}await startQuiz(m.MaDe,false,false,'','');let qIdx=findQuestionIndexById(m.ID);if(qIdx<0)qIdx=Math.max(0,parseInt(m.index_in_de,10)||0);saveCurrent();CUR=qIdx;renderQuestion();if(doEdit&&USER.is_admin)openEdit()}
async function copyQuestionId(){let q=QUESTIONS[CUR];let id=String(q&&q.ID||'').trim();if(!id){alert('Câu này chưa có ID.');return}let ok=await copyTextToClipboard(id);alert(ok?'✅ Đã chép ID: '+id:'Không chép được. Hãy chọn và chép thủ công.')}
function jumpToIdInQuiz(){let raw=String(val('quizIdJump')||'').trim();if(!raw){alert('Nhập ID câu.');return}let idx=findQuestionIndexById(raw);if(idx<0){alert('Không thấy ID «'+raw+'» trong đề này.');return}saveCurrent();CUR=idx;renderQuestion();if(USER.is_admin)openEdit()}
function handleQidDeepLink(){let p=new URLSearchParams(location.search);let qid=(p.get('qid')||p.get('question_id')||'').trim();if(!qid)return;setVal('fIdLookup',qid);setTimeout(()=>lookupQuestionById(),400);p.delete('qid');p.delete('question_id');let q=p.toString();history.replaceState(null,'',location.pathname+(q?'?'+q:''))}
function clearShareTarget(){document.querySelectorAll('.card.shareTarget').forEach(el=>el.classList.remove('shareTarget'))}
function markShareTarget(made){clearShareTarget();let el=document.getElementById('shareCard_'+made);if(el){el.classList.add('shareTarget');setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'nearest'}),120)}}
function handleShareDeepLink(){let sp=getShareParams();if(!sp.de)return;let item=CATALOG.find(x=>x.MaDe===sp.de);if(!item){alert('Không tìm thấy đề trong link. Có thể đề đã đổi hoặc cần Đồng bộ Sheet.');return}if(item.Mon)setSel('fMon',item.Mon);refreshFilterOptions();if(item.Lop)setSel('fLop',item.Lop);refreshFilterOptions();if(item.Chuong)setSel('fChuong',item.Chuong);refreshFilterOptions();if(item.BaiHoc)setSel('fBaiHoc',item.BaiHoc);refreshFilterOptions();if(item.BoDe)setSel('fBoDe',item.BoDe);if(sp.level)setSel('fMucDo',sp.level);if(sp.dang)setSel('fDang',sp.dang);renderCatalog();let lv=sp.level||val('fMucDo');let dg=sp.dang||val('fDang');if(sp.start){if(USER.is_trial&&(item.QuyenTruyCap||'FREE')!=='FREE'){markShareTarget(sp.de);alert('Tài khoản dùng thử chỉ mở đề FREE.');return}setTimeout(()=>startQuiz(sp.de,sp.sq,sp.sa,lv,dg),280)}else if(sp.open){markShareTarget(sp.de);setTimeout(()=>openStartModal(sp.de),280)}}
function esc(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])).replace(/\n/g,'<br>')}
function escHtmlKeepMath(s){let out='',i=0,n=String(s||'').length;while(i<n){let d1=s.indexOf('$',i),d2=d1>=0?s.indexOf('$',d1+1):-1;if(d1<0){out+=esc(s.slice(i));break}out+=esc(s.slice(i,d1));if(d2<0){out+=esc(s.slice(d1));break}out+=s.slice(d1,d2+1);i=d2+1}return out}
function stripLatexListMarkup(s){s=String(s||'');s=s.replace(/\\begin\s*\{\s*enumerate\s*\}/gi,'');s=s.replace(/\\end\s*\{\s*enumerate\s*\}/gi,'');s=s.replace(/\\begin\s*\{\s*itemize\s*\}/gi,'');s=s.replace(/\\end\s*\{\s*itemize\s*\}/gi,'');s=s.replace(/\\item\s*/gi,'\n• ');s=s.replace(/\\item(?=[A-Za-zÀ-ỹĐđ])/gi,'\n• ');return s}
function fixPlainTextGaps(s){return String(s||'').replace(/(\d)([Nn]ên|[Đđ]iểm)/g,'$1 $2').replace(/(\))([A-Za-zÀ-ỹĐđ])/g,'$1 $2')}
function fixOneMathInner(inner){if(!inner)return inner;inner=inner.replace(/\)\s*\((\d[\d;\s,.\-]*)\)/g,')$ $( $1)$');inner=inner.replace(/\$\(([^)]+)\)(thuộc|mặt|phẳng|nên|điểm)/gi,'$( $1)$ $2');inner=inner.replace(/\(([^)]+)\)(thỏa|mãn|phương|trình|nên|điểm|thuộc|mặt|phẳng|khẳng|tọa|độ)/gi,'($1)$ $2');inner=inner.replace(/(=[\d.\-+]+)\s*(nên|điểm|thuộc|mặt|phẳng|khẳng|tọa)/gi,'$1$ $2');inner=inner.replace(/\)(thỏa|mãn|nên|điểm|thuộc|mặt|phẳng)/gi,') $1');inner=inner.replace(/(\d)([A-Za-zÀ-ỹĐđ][a-zà-ỹà-ỹ]{2,})/g,'$1 $2');inner=inner.replace(/(\))([A-Za-zÀ-ỹĐđ][a-zà-ỹà-ỹ]{2,})/g,'$1 $2');inner=inner.replace(/\(\((\\?[a-zA-Z]+)\)\)/g,'$1');return inner}
function latexDollarCount(s){s=String(s||'');let n=0;for(let i=0;i<s.length;i++){if(s[i]==='$'&&s[i+1]==='$'){i++;continue}if(s[i]==='$')n++}return n}
function latexStructureOk(s){s=String(s||'');if(latexDollarCount(s)%2)return false;let plain=s.replace(/\$\$[^$]*\$\$/g,'').replace(/\$[^$]*\$/g,'');return !/\\(?:text|mathrm|frac|sqrt|left|right|times|cdot|pm|mp|leq|geq|neq|approx|,)/.test(plain)}
function fixSurplusDollars(s){s=String(s||'');if(s.indexOf('$')<0)return s;s=s.replace(/\${3,}/g,'$$');s=s.replace(/\$\$([^$\n]{1,160}?)\$\$/g,'$$$1$');s=s.replace(/\$\$([^$\n]+?)\$(?!\$)/g,'$$$1$');s=s.replace(/\$([^$\n]+?)\$\$(?!\$)/g,'$$$1$');s=s.replace(/(\$[^$\n]+?\$)\$+/g,'$1');s=s.replace(/\$\s+\$(?=[^$\n])/g,'$');s=s.replace(/\$\s+\$(?=\s|$)/g,' ');s=s.replace(/\$\s*\$/g,' ');s=s.replace(/(?<=\s)\$(?=\s)/g,'');s=s.replace(/(\$[^$\n]+?\$)\.(\$)(?=\s|$|[A-Za-zÀ-ỹĐđ])/g,'$1.');s=s.replace(/(\$[^$\n]+?\$)([,.;:])\$(?=\s|$)/g,'$1$2');if(s.endsWith('$')&&latexDollarCount(s)%2===1)s=s.slice(0,-1);return s}
function fixMergedInlineMath(t){t=String(t||'');if(t.indexOf('$')<0)return fixPlainTextGaps(t);let out='',i=0,n=t.length;while(i<n){if(t[i]!=='$'){let d1=t.indexOf('$',i);if(d1<0){out+=fixPlainTextGaps(t.slice(i));break}out+=fixPlainTextGaps(t.slice(i,d1));i=d1;continue}if(i+1<n&&t[i+1]==='$'){let end=t.indexOf('$$',i+2);if(end>=0){out+=t.slice(i,end+2);i=end+2;continue}}let d2=t.indexOf('$',i+1);if(d2<0){let rest=t.slice(i+1);if(String(rest).trim()&&(rest.indexOf('\\')>=0||rest.indexOf('{')>=0))out+='$'+fixOneMathInner(rest)+'$';else out+=fixPlainTextGaps(rest);break}let inner=t.slice(i+1,d2);if(!String(inner).trim()){i=d2+1;continue}while(d2+1<n&&t[d2+1]==='$'&&(d2+2>=n||t[d2+2]!=='$'))d2++;out+='$'+fixOneMathInner(t.slice(i+1,d2))+'$';i=d2+1}return out}
function normalizeLatexDelimiters(s){s=String(s||'');s=fixSurplusDollars(s);let heavy=/\\(?:item|begin\s*\{enumerate|begin\s*\{itemize|acute)|\$\{|\$\$[^$]|\$\s+\$(?=[^$\n])/.test(s)||!latexStructureOk(s);if(heavy){s=s.replace(/\$\{\s*([^}$\n]+?)\s*\}\s*\$/g,'$( $1 )$');s=s.replace(/\$\{\s*([^}$\n]+?)\s*\}/g,'$( $1 )$');s=s.replace(/\{\s*\(\s*([^}]+?)\s*\)\s*\}/g,function(m,g1,off,full){if(off>0&&full[off-1]==='$')return m;if(off+m.length<full.length&&full[off+m.length]==='$')return m;return '$( '+g1+' )$'});s=s.replace(/\$\(\((\\?[a-zA-Z]+)\)\)\$\.?/g,'$$$1$.');s=s.replace(/\$\(\((\\?[a-zA-Z]+)\)\)(?!\$)/g,'$$$1$');s=fixMergedInlineMath(s);s=fixSurplusDollars(s);s=s.replace(/(\$[^$\n]+?\$)\$+/g,'$1');s=s.replace(/\$\s*\$/g,' ')}s=s.replace(/\$([^$]*)\$/g,function(_,inner){return '$'+String(inner).replace(/\\\\/g,'\\')+'$'});return s}
function readLatexBracedContent(s,bracePos){if(bracePos<0||bracePos>=s.length||s[bracePos]!=='{')return null;let depth=0;for(let i=bracePos;i<s.length;i++){let c=s[i];if(c==='{')depth++;else if(c==='}'){depth--;if(depth===0)return{content:s.slice(bracePos+1,i),end:i}}}return null}
function normalizeLatexTextCmds(s){s=String(s||'');s=s.replace(/\\{2,}(textbf|textit|emph|underline)\s*\{/gi,'\\$1{');s=s.replace(/(^|[^\\$])(textbf|textit|emph|underline)\s*\{/gi,'$1\\$2{');return s}
function replaceLatexFmtInPlain(s){s=normalizeLatexTextCmds(s);let cmds=[{re:/\\textbf\s*\{/gi,o:'@@B@@',c:'@@/B@@'},{re:/\\textit\s*\{/gi,o:'@@I@@',c:'@@/I@@'},{re:/\\emph\s*\{/gi,o:'@@I@@',c:'@@/I@@'},{re:/\\underline\s*\{/gi,o:'@@U@@',c:'@@/U@@'}];let loop=true;while(loop){loop=false;for(let cmd of cmds){cmd.re.lastIndex=0;let m=cmd.re.exec(s);if(!m)continue;let idx=m.index,bracePos=idx+m[0].length-1,got=readLatexBracedContent(s,bracePos);if(!got)continue;let inner=replaceLatexFmtInPlain(got.content);s=s.slice(0,idx)+cmd.o+inner+cmd.c+s.slice(got.end+1);loop=true;break}}return s}
function applyFmtOutsideMath(s,fn){let out='',i=0,n=String(s||'').length;while(i<n){let d1=s.indexOf('$',i);if(d1<0){out+=fn(s.slice(i));break}out+=fn(s.slice(i,d1));let d2=s.indexOf('$',d1+1);if(d2<0){out+=s.slice(d1);break}out+=s.slice(d1,d2+1);i=d2+1}return out}
function applyLatexTextFmtOutsideMath(s){return applyFmtOutsideMath(s,replaceLatexFmtInPlain)}
function applyMarkdownBoldOutsideMath(s){return applyFmtOutsideMath(s,x=>x.replace(/\*\*([^*\n]+)\*\*/g,'@@B@@$1@@/B@@'))}
function splitTabularRows(body){body=String(body||'').replace(/\r/g,'').trim();if(/\\\\/.test(body)){return body.replace(/\\\\\s*\n?/g,'@@ROW@@').split('@@ROW@@')}return body.split(/\n+/).filter(Boolean)}
let LATEX_TAB_HTML=[];
function convertLatexTabular(s){LATEX_TAB_HTML=[];return String(s||'').replace(/\\begin\s*\{tabular\*?\}\s*(\{[^}]*\})?\s*([\s\S]*?)\\end\s*\{tabular\*?\}/gi,function(_,colSpec,body){let spec=(colSpec||'').replace(/^\{|\}$/g,'');let aligns=[];for(let i=0;i<spec.length;i++){let c=spec[i];if(c==='c'||c==='l'||c==='r')aligns.push(c)}let html='<div class="latex-tabular-wrap"><table class="latex-tabular"><tbody>';let borderNext=false;for(let row of splitTabularRows(body)){row=row.trim();if(!row)continue;if(/^\\hline\s*$/i.test(row)){borderNext=true;continue}if(/^\\hline/i.test(row))row=row.replace(/^\\hline\s*/i,'');row=row.replace(/\\hline/g,'').trim();if(!row)continue;if(!row.includes('&'))continue;let cells=row.split('&').map(c=>c.trim());let trCls=borderNext?' class="hline-top"':'';borderNext=false;html+=`<tr${trCls}>`;for(let i=0;i<cells.length;i++){let al=aligns[i]||'c';let st=al==='r'?'text-align:right':(al==='l'?'text-align:left':'text-align:center');html+=`<td style="${st}">${cells[i]}</td>`}html+='</tr>'}html+='</tbody></table></div>';let id=LATEX_TAB_HTML.length;LATEX_TAB_HTML.push(html);return `@@LTXTAB${id}@@`})}
function restoreLatexTabular(s){return String(s||'').replace(/@@LTXTAB(\d+)@@/g,function(_,i){return LATEX_TAB_HTML[+i]||''})}
function finalizeRichTokens(s){return s.replace(/@@OL@@/g,'<ol class="latex-list">').replace(/@@\/OL@@/g,'</ol>').replace(/@@UL@@/g,'<ul class="latex-list">').replace(/@@\/UL@@/g,'</ul>').replace(/@@LI@@/g,'<li>').replace(/@@\/LI@@/g,'</li>').replace(/@@B@@/g,'<b>').replace(/@@\/B@@/g,'</b>').replace(/@@I@@/g,'<i>').replace(/@@\/I@@/g,'</i>').replace(/@@U@@/g,'<u>').replace(/@@\/U@@/g,'</u>')}
function renderRichText(s){s=String(s||'').trim();s=s.replace(/\?\?\s*/g,'');s=convertLatexTabular(s);s=stripLatexListMarkup(s);s=normalizeLatexDelimiters(s);s=s.replace(/\\begin\{enumerate\}([\s\S]*?)\\end\{enumerate\}/gi,function(_,b){let items=b.split(/\\item\s*/i).map(x=>x.trim()).filter(Boolean);return '@@OL@@'+items.map(it=>'@@LI@@'+it+'@@/LI@@').join('')+'@@/OL@@'});s=s.replace(/\\begin\{itemize\}([\s\S]*?)\\end\{itemize\}/gi,function(_,b){let items=b.split(/\\item\s*/i).map(x=>x.trim()).filter(Boolean);return '@@UL@@'+items.map(it=>'@@LI@@'+it+'@@/LI@@').join('')+'@@/UL@@'});s=s.replace(/\\item\s*/gi,'<br>• ');s=s.replace(/\\item(?=[A-Za-zÀ-ỹĐđ])/gi,'<br>• ');s=applyLatexTextFmtOutsideMath(s);s=applyMarkdownBoldOutsideMath(s);s=escHtmlKeepMath(s);s=restoreLatexTabular(s);return finalizeRichTokens(s)}
function escAttr(s){return String(s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function shortText(s,n=90){s=String(s||'').replace(/\s+/g,' ').trim();return s.length>n?s.slice(0,n-1)+'…':s}
function normText(s){return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'d')}
function normDangClient(s){let t=String(s||'').replace(/[/\\]+/g,' ');let k=normText(t).replace(/[\/\\-]/g,' ');let k2=k.replace(/\s+/g,'');if(/dung\s*sai|dungsai|d\/s|true\s*false|truefalse/.test(k)||k2.includes('ds')||/\b(ds|tf)\b/.test(k))return 'Đúng sai';if(/tra\s*loi\s*ngan|short|tln|shortans/.test(k))return 'Trả lời ngắn';if(/tu\s*luan|essay/.test(k)||k==='tl')return 'Tự luận';if(/trac\s*nghiem|tracnghiem|mcq|multiple\s*choice/.test(k)||k==='tn'||k==='tn4')return 'Trắc nghiệm';return 'Trắc nghiệm'}
function tfTokenClient(p){let t=normText(p);if(!String(p||'').trim())return '';if(String(p).trim()==='Đ'||String(p).trim()==='D'||t==='d'||t==='dung'||t==='true')return 'Đ';if(String(p).trim()==='S'||t==='s'||t==='sai'||t==='false')return 'S';return ''}
function parseTfClient(v){let raw=String(v||'').trim();if(!raw)return [];let parts=raw.split(/[,;|/\n]+/).map(x=>x.trim()).filter(Boolean);if(parts.length>=2){let out=parts.map(tfTokenClient);if(out.filter(x=>x==='Đ'||x==='S').length>=2)return out}let s=raw.toUpperCase().replace(/\u0110/g,'D').replace(/\u0111/g,'D').replace(/DUNG/g,'D').replace(/TRUE/g,'D').replace(/SAI/g,'S').replace(/FALSE/g,'S');return (s.match(/[DSĐ]/g)||[]).map(c=>(c==='S'?'S':'Đ')).slice(0,4)}
function hasOptsClient(q){return ['A','B','C','D'].filter(L=>String((q||{})[L]||'').trim()).length>=2}
function looksDsAnswer(v){let raw=String(v||'').trim();if(!raw)return false;if(/^[ABCD]$/i.test(raw.replace(/\s/g,'')))return false;return parseTfClient(raw).filter(x=>x==='Đ'||x==='S').length>=2}
function isMcqLetter(v){let raw=String(v||'').trim().toUpperCase().replace(/\u0110/g,'D');return /^[ABCD]$/.test(raw)}
function looksShortAnswerClient(q){let d=String((q&&q.DapAn)||'').trim();if(!d)return false;if(isMcqLetter(q.DapAn))return false;if(looksDsAnswer(q.DapAn))return false;let n=d.replace(/\s/g,'').replace(',','.');if(/^-?\d+(\.\d+)?$/.test(n))return true;return d.length<=200}
function dangMetaRaw(q){if(!q)return '';for(let k of ['_DangCol','DangBaiTap','Dang']){let v=String(q[k]||'').trim();if(v)return v}return ''}
const DANG_GROUP_ORDER_CLIENT=['Trắc nghiệm','Đúng sai','Trả lời ngắn','Tự luận'];
function resolveDang(q){if(!q)return 'Trắc nghiệm';let rawCol=dangMetaRaw(q);let dc=normDangClient(rawCol);if(rawCol&&DANG_GROUP_ORDER_CLIENT.includes(dc))return dc;if(looksDsAnswer(q.DapAn))return 'Đúng sai';if(isMcqLetter(q.DapAn)&&hasOptsClient(q))return 'Trắc nghiệm';if(looksShortAnswerClient(q))return 'Trả lời ngắn';return 'Trắc nghiệm'}
function applyResolvedDang(q){if(!q)return q;q.Dang=resolveDang(q);return q}
function dangSame(a,b){return normDangClient(a)===normDangClient(b)}
function questionLevelMatch(q,lv){if(!lv)return true;let u=String(q.MucDo||'').toUpperCase();let parts=u.split(/[,;/|]+/).map(x=>x.trim()).filter(Boolean);return parts.includes(lv)||u.includes(lv)}
function mucdoBadgeClass(lv){let u=String(lv||'').trim().toUpperCase();if(!u)return'mucdo-other';if(u==='NB'||/\bNB\b/.test(u))return'mucdo-nb';if(u==='TH'||/\bTH\b/.test(u))return'mucdo-th';if(u==='VDC'||u.includes('VDC'))return'mucdo-vdc';if(u==='VD'||/\bVD\b/.test(u))return'mucdo-vd';return'mucdo-other'}
function formatMucDoBadges(mucdo){let raw=String(mucdo||'').trim();if(!raw)return'';let parts=raw.split(/[,;/|]+/).map(x=>x.trim()).filter(Boolean);if(!parts.length)parts=[raw];return parts.map(p=>`<span class="mucdoBadge ${mucdoBadgeClass(p)}" title="Mức độ (cột I): ${escAttr(p)}">${esc(p)}</span>`).join(' ')}
function filterQuestionsByDang(qs,dang){dang=String(dang||'').trim();if(!dang)return qs||[];let want=normDangClient(dang);return (qs||[]).filter(q=>normDangClient(applyResolvedDang(q).Dang)===want)}
function filterQuestionsByLevel(qs,lv){lv=(lv||'').trim().toUpperCase();if(!lv)return qs||[];return (qs||[]).filter(q=>questionLevelMatch(q,lv))}
function applyQuizFilters(qs,lv,dg){return filterQuestionsByDang(filterQuestionsByLevel(qs||[],lv),dg)}
function updateFilterBadge(lv,dg,count){let el=document.getElementById('filterBadge');if(!el)return;if(!lv&&!dg){el.textContent='';el.classList.add('hide');return}let parts=[];if(dg)parts.push(dg);if(lv)parts.push('mức '+lv);el.textContent='🎯 Lọc: '+parts.join(' · ')+(count!=null?' ('+count+' câu)':'');el.classList.remove('hide')}
function isQuestionDone(i){let q=QUESTIONS[i];if(!q)return false;q=applyResolvedDang(q);let a=ANSWERS[i];if(q.Dang=='Trắc nghiệm')return !!String(a||'').trim();if(q.Dang=='Đúng sai'){if(!Array.isArray(a))return false;let req=0;for(let L of ['A','B','C','D'])if(q[L])req++;let filled=a.filter(v=>!!String(v||'').trim()).length;return req>0&&filled>=req}return !!String(a||'').trim()}
function countDone(){let n=0;for(let i=0;i<QUESTIONS.length;i++)if(isQuestionDone(i))n++;return n}
function notifyDoneIfNeeded(){if(SUBMITTED||COMPLETED_NOTICE||!QUESTIONS.length)return;let done=countDone();if(done>=QUESTIONS.length){COMPLETED_NOTICE=true;alert('✅ Đã làm hết đề. Thầy/các em có thể xem lại rồi bấm Nộp bài.')}} 
function val(id){return document.getElementById(id).value}
function typeset(els){if(!window.MathJax)return Promise.resolve();let list=els?(Array.isArray(els)?els:[els]).filter(Boolean):null;let run=()=>{try{if(list&&list.length&&MathJax.typesetClear)MathJax.typesetClear(list)}catch(e){}if(MathJax.typesetPromise)return MathJax.typesetPromise(list&&list.length?list:undefined).catch(()=>{});if(MathJax.typeset){try{MathJax.typeset(list&&list.length?list:undefined)}catch(e){}}return Promise.resolve()};if(MathJax.startup&&MathJax.startup.promise)return MathJax.startup.promise.then(run);return run()}
function typesetQuizMath(){return typeset([document.getElementById('qtext'),document.getElementById('options'),document.getElementById('solution'),document.getElementById('hintBox')])}
function formatHintDisplay(s){s=String(s||'').trim();if(!s)return '';s=s.replace(/\$\$\s*/g,'$');s=s.replace(/\s*\$\$/g,'$');s=s.replace(/\$\s*\n+\s*\$/g,'');s=s.replace(/\$\s*\n+\s*([^$\n]+?)\s*\n+\s*\$/g,'$( $1 )$');s=s.replace(/\$\s*\n+([^$\n]+?)\s*\$/g,'$( $1 )$');s=s.replace(/\$\s*\$/g,'');s=s.replace(/^###\s+(.+)$/gm,'@@B@@$1@@/B@@');return renderRichText(s)}
function dsCircleHtml(L){return `<span class="dsCircle" aria-label="Ý ${L}">${L}</span>`}
function stripOptionPrefix(text,L){text=String(text||'').trim();if(!text)return text;let m=text.match(new RegExp('^\\s*'+L+'\\s*[\\.\\)\\:]\\s*','i'));if(m)return text.slice(m[0].length).trim();let any=text.match(/^\s*[ABCD]\s*[\.\)\:]\s*/i);if(any)return text.slice(any[0].length).trim();return text}
function stripImmini(text){text=String(text||'').trim();let m=text.match(/\\immini\s*\{([\s\S]*)\}\s*$/i);if(m)return m[1].trim();return text.replace(/^\\immini\s*\{/i,'').replace(/\}\s*$/,'').trim()}
function buildQimgHtml(src){return `<div class="qimgWrap"><img class="qimg" src="${esc(src)}" alt="Hình minh họa" onerror="this.parentElement.outerHTML='<div class=\\'qimgErr\\'>Không tải được hình. Kiểm tra cột T hoặc quyền chia sẻ ảnh.</div>'"></div>`}
function usesImgSplit(q){if(!q||!String(q.HinhAnh||'').trim())return false;return q.Dang==='Trắc nghiệm'||q.Dang==='Đúng sai'||q.Dang==='Trả lời ngắn'}
function isTlnImgSplit(q){return !!(q&&q.Dang==='Trả lời ngắn'&&String(q.HinhAnh||'').trim())}
function mcqUsesSplit(q){return usesImgSplit(q)}
function adminTlnSheetAnswerHtml(q){if(!USER.is_admin||!q)return '';let da=String(q.DapAn||'').trim();if(!da)return '<div class="adminTlnAns adminTlnAnsWarn">⚠ ADMIN: cột P (Đáp án) đang trống.</div>';let ss=String(q.SaiSo||'').trim();let ssNote=ss?` <span class="muted">· sai số ±${esc(ss)}</span>`:'';return `<div class="adminTlnAns">📋 ADMIN — Đáp án Sheet (P): <b>${renderRichText(da)}</b>${ssNote}</div>`}
function buildShortAnsHtml(q,opts){opts=opts||{};let compact=opts.compact!==false;let withQ=!!opts.withQuestion;let saDis=SUBMITTED?'disabled':'';let saCls='shortAnsBox';let cr=RESULTS[CUR]||CHECKED[CUR];if(cr&&cr.ok===true)saCls+=' correct';else if(cr&&cr.ok===false)saCls+=' wrong';if(compact)saCls+=' shortAnsCompact';let saFb=shortAnswerFeedbackHtml(q);let qBlock=withQ?`<div class="shortAnsQtext">${renderRichText(stripImmini(q.CauHoi))}</div>`:'';let adminBlock=adminTlnSheetAnswerHtml(q);if(USER.is_admin){return `<div class="${saCls}">${qBlock}${adminBlock}<div class="muted shortAnsNote">ADMIN xem đáp án/lời giải ngay — không cần nhập hay chấm.</div></div>`}if(compact)return `<div class="${saCls}">${qBlock}<div class="shortAnsFieldRow"><span class="shortAnsLbl">Đáp án</span><input id="shortAnsInput" class="shortAnsInput" type="text" maxlength="16" inputmode="decimal" autocomplete="off" spellcheck="false" placeholder="…" value="${escAttr(ANSWERS[CUR]||'')}" ${saDis} oninput="saveShortAnswer(false)" onkeydown="if(event.key==='Enter'){saveShortAnswer(true);event.preventDefault()}"><button type="button" class="btn shortAnsBtn" onclick="saveShortAnswer(true)" ${saDis}>✓</button><span class="muted shortAnsHint">Enter</span></div>${saFb}<div class="muted shortAnsNote">Bấm <b>Nộp bài</b> sau khi làm hết đề.</div></div>`;return `<div class="${saCls}"><label style="display:block;font-weight:800;margin-bottom:8px">✏️ Điền đáp án (trả lời ngắn)</label><input id="shortAnsInput" class="shortAnsInput shortAnsInputWide" type="text" maxlength="16" inputmode="decimal" placeholder="Nhập số hoặc kết quả…" value="${escAttr(ANSWERS[CUR]||'')}" ${saDis} oninput="saveShortAnswer(false)" onkeydown="if(event.key==='Enter'){saveShortAnswer(true);event.preventDefault()}"><div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center"><button type="button" class="btn" style="width:auto;margin:0" onclick="saveShortAnswer(true)" ${saDis}>✓ Kiểm tra</button></div>${saFb}</div>`}
function dsVerdictLabel(v){let t=String(v||'').trim();if(!t)return '';if(/^s(ai)?$/i.test(t)||t==='S')return 'Sai';return 'Đúng'}
function currentQuestion(){let q=QUESTIONS[CUR];return q?applyResolvedDang(q):null}
function isCurrentQuestionDs(){let q=currentQuestion();return !!(q&&q.Dang==='Đúng sai')}
function isCurrentQuestionTn(){let q=currentQuestion();return !!(q&&q.Dang==='Trắc nghiệm')}
function parseDsAnswerTokens(text){let t=String(text||'').trim();if(!t)return [];let tagged=[...t.matchAll(/([ABCD])\s*[=:\-]\s*(Đúng|Sai|Đ|S|D)/gi)];if(tagged.length>=2)return tagged.map(x=>({letter:x[1].toUpperCase(),verdict:dsVerdictLabel(x[2])}));let parts=t.split(/[,;|/\s]+/).map(x=>x.trim()).filter(Boolean);if(parts.length>=2&&parts.every(p=>/^[ĐDSđds]$/i.test(p.replace(/\u0110/g,'D')))){return parts.slice(0,4).map((p,i)=>({letter:['A','B','C','D'][i],verdict:dsVerdictLabel(p)}))}let compact=t.toUpperCase().replace(/\u0110/g,'D').replace(/[^DS]/g,'');if(compact.length>=2&&compact.length<=4){return compact.split('').map((c,i)=>({letter:['A','B','C','D'][i],verdict:c==='S'?'Sai':'Đúng'}))}return []}
function formatDsAnswerBadges(text){let parts=parseDsAnswerTokens(text);if(!parts.length)return formatHintDisplay(text);return `<div class="dsAnswerRow">${parts.map(p=>`<div class="dsAnswerItem">${dsCircleHtml(p.letter)} <b class="${p.verdict==='Sai'?'dsVerdictSai':'dsVerdictDung'}">${esc(p.verdict)}</b></div>`).join('')}</div>`}
function dsTokenLabel(v){let t=String(v||'').trim();if(!t)return '?';if(/^s$/i.test(t)||t==='S')return 'Sai';return 'Đúng'}
function isQuestionChecked(qIdx){if(SUBMITTED){let r=RESULTS[qIdx];return !!(r&&(r.ok===true||r.ok===false))}return !!CHECKED[qIdx]}
function getDsCheckRows(q,r,ans){if(r&&Array.isArray(r.rows)&&r.rows.length)return r.rows;let vMap={};parseDsAnswerTokens(String(q.DapAn||'')).forEach(t=>vMap[t.letter]=t.verdict==='Sai'?'S':'Đ');if(!Object.keys(vMap).length){let c=String(q.DapAn||'').toUpperCase().replace(/\u0110/g,'D').replace(/[^DS]/g,'');c.split('').forEach((x,i)=>{let L=['A','B','C','D'][i];if(L&&q[L])vMap[L]=x==='S'?'S':'Đ'})}let old=Array.isArray(ans)?ans.slice():[];while(old.length<4)old.push('');let rows=[];['A','B','C','D'].forEach((L,i)=>{if(!q[L])return;let c=vMap[L]||'';let ch=String(old[i]||'').trim();if(ch==='D'||ch==='d')ch='Đ';rows.push({letter:L,correct:c,chosen:ch,ok:ch?!!(c&&ch===c):null})});return rows}
function formatDsCheckResultBox(qIdx,j,q,ans){let rows=getDsCheckRows(q,j,ans);if(!rows.length)return `<span>Câu ${qIdx+1}: ${j.ok?'✅ Đúng':'❌ Sai'}</span>`;let okN=rows.filter(x=>x.ok===true).length,tot=rows.length;let head=j.ok?`✅ Đúng (${tot}/${tot} ý)`: `❌ Sai (${okN}/${tot} ý đúng)`;let badges=rows.map(r=>{let cls=r.ok===true?'dsCheckOk':(r.ok===false?'dsCheckBad':'');let mark=r.ok===true?'✓':(r.ok===false?'✗':'?');let title='';if(r.ok===false){title=` title="Bạn: ${dsTokenLabel(r.chosen)}`;if(canViewSolutionLive()||USER.is_admin)title+=` · Đáp án: ${dsTokenLabel(r.correct)}`;title+='"' }return `<span class="dsCheckItem ${cls}"${title}>${r.letter} ${mark}</span>`}).join('');return `<div class="dsCheckBox"><div class="dsCheckHead">Câu ${qIdx+1}: ${head}</div><div class="dsCheckRow">${badges}</div></div>`}
function updateResultBox(qIdx){let rb=document.getElementById('resultBox');if(!rb)return;let q=applyResolvedDang(QUESTIONS[qIdx]);if(!q)return;let r=RESULTS[qIdx]||CHECKED[qIdx];if(SUBMITTED){if(q.Dang==='Đúng sai'&&r&&(r.ok===true||r.ok===false)){rb.innerHTML=formatDsCheckResultBox(qIdx,r,q,ANSWERS[qIdx]);rb.classList.add('dsResultRich');rb.style.color=r.ok?'#166534':'#991b1b'}return}if(!r||!(r.ok===true||r.ok===false)){rb.textContent='';rb.classList.remove('dsResultRich');return}if(q.Dang==='Đúng sai'){rb.innerHTML=formatDsCheckResultBox(qIdx,r,q,ANSWERS[qIdx]);rb.classList.add('dsResultRich');rb.style.color=r.ok?'#166534':'#991b1b'}else{rb.classList.remove('dsResultRich');rb.textContent=`Câu ${qIdx+1}: ${r.ok?'✅ Đúng':'❌ Sai'}`;rb.style.color=r.ok?'#166534':'#991b1b'}}
function formatMcqAnswerBadge(text){let raw=String(text||'').trim();let m=raw.toUpperCase().match(/^([ABCD])$/);if(!m){let lm=raw.match(/(?:đáp án|chọn|kết luận|phương án)[^ABCD]*([ABCD])/i);if(lm)m=[null,lm[1].toUpperCase()]}if(m&&m[1])return `<div class="dsAnswerRow"><div class="dsAnswerItem">${dsCircleHtml(m[1])} <b class="dsVerdictDung">đáp án đúng</b></div></div>`;return formatHintDisplay(raw)}
function extractAbcdSolutionChunks(text){let t=String(text||'').replace(/\r/g,'');let tagged=[...t.matchAll(/(?:^|\n|[•\-\*]\s*|\(\s*)(?:\*\*)?([ABCD])\s*[\.\):]\s*(?:(Đúng|Sai)\s*[\-—:–]\s*)?/gi)];if(tagged.length>=1){let out=[];for(let i=0;i<tagged.length;i++){let start=tagged[i].index+tagged[i][0].length;let end=i+1<tagged.length?tagged[i+1].index:t.length;out.push({letter:tagged[i][1].toUpperCase(),verdict:tagged[i][2]?dsVerdictLabel(tagged[i][2]):'',body:t.slice(start,end).trim().replace(/^[\)\s.,]+|[\(\s.,]+$/g,'')})}return out.slice(0,4)}let lineTagged=[...t.matchAll(/(?:^|\n)\s*(?:\*\*)?([ABCD])(?!\s*[\.\):])(?:\s+(?:(Đúng|Sai)\s*[\-—:–]\s*)?(.+))?$/gim)];if(lineTagged.length>=1){return lineTagged.slice(0,4).map(m=>({letter:m[1].toUpperCase(),verdict:m[2]?dsVerdictLabel(m[2]):'',body:(m[3]||'').trim().replace(/^[\)\s.,]+|[\(\s.,]+$/g,'')}))}t=t.replace(/\(\s*•\s*/g,'\n• ').replace(/\s*•\s*/g,'\n• ');let markers=[];let rx=/(?:^|\n|[•\-\*]\s*)(Đúng|Sai)\.\s*/gi,m;while((m=rx.exec(t))!==null)markers.push({verdict:m[1],start:m.index+m[0].length,head:m.index});if(markers.length>=1){return markers.map((mk,i)=>{let end=i+1<markers.length?markers[i+1].head:t.length;return {letter:['A','B','C','D'][i]||String(i+1),verdict:dsVerdictLabel(mk.verdict),body:t.slice(mk.start,end).trim().replace(/^[\)\s.,]+|[\(\s.,]+$/g,'')}}).slice(0,4)}return []}
function finalizeAbcdSolutionChunks(chunks,q,isDs,skipSheet){if(!q)return chunks||[];let letters=['A','B','C','D'].filter(L=>q[L]);if(!letters.length)return chunks||[];let byL={};(chunks||[]).forEach(c=>{byL[c.letter]=c});let tokens=isDs&&!skipSheet?parseDsAnswerTokens(q.DapAn||''):[];let vMap={};tokens.forEach(t=>vMap[t.letter]=t.verdict);let corrMcq=String(q.DapAn||'').trim().toUpperCase().match(/^([ABCD])$/)?.[1];return letters.map(L=>{if(byL[L]){let c=byL[L];if(isDs&&!skipSheet&&!c.verdict&&vMap[L])return Object.assign({},c,{verdict:vMap[L]});return c}return {letter:L,verdict:isDs&&!skipSheet?(vMap[L]||''):'',body:''}})}
function formatAbcdSolutionList(chunks,q,isDs){q=q||{};chunks=finalizeAbcdSolutionChunks(chunks,q,isDs);if(!chunks.length)return '';let corrMcq=String(q.DapAn||'').trim().toUpperCase().match(/^([ABCD])$/)?.[1];let stacked=needsAbcdStackedLayout(q,chunks);let listCls='dsSolutionList dsSolutionCompact'+(stacked?' dsSolutionRows':(isDs?' dsSolutionDs':' dsSolutionTn'));return `<div class="${listCls}">${chunks.map(c=>{let headVerdict='';if(c.verdict)headVerdict=`<b class="${c.verdict==='Sai'?'dsVerdictSai':'dsVerdictDung'}">${esc(c.verdict)}</b>`;else if(!isDs&&c.letter===corrMcq)headVerdict=`<b class="dsVerdictDung">✓ Đúng</b>`;else if(!isDs&&corrMcq)headVerdict=`<span class="muted">sai</span>`;let stmt='';if(q[c.letter]&&!c.body){let st=renderRichText(stripOptionPrefix(q[c.letter],c.letter));stmt=stacked?`<div class="dsStmtBlock">${st}</div>`:`<span class="dsStmtInline">${st}</span>`}let body=c.body?`<div class="dsSolutionBody">${formatHintDisplay(c.body)}</div>`:'';if(stacked&&stmt)return `<div class="dsSolutionItem"><div class="dsSolutionHead">${dsCircleHtml(c.letter)} ${headVerdict}</div>${stmt}${body}</div>`;return `<div class="dsSolutionItem"><div class="dsSolutionHead">${dsCircleHtml(c.letter)} ${headVerdict}${stmt}</div>${body}</div>`}).join('')}</div>`}
function stripLoigiaiMarkdown(s){return String(s||'').replace(/\*\*/g,'').replace(/^#+\s+/gm,'').trim()}function buildDsSolutionPlainLine(c,keepBreaks){let v=c.verdict||'';let body=stripLoigiaiMarkdown(c.body||'');if(!keepBreaks)body=body.replace(/\s+/g,' ').trim();else body=body.trim();if(!v&&!body)return '';return v?(body?`${c.letter}. ${v} — ${body}`:`${c.letter}. ${v}`):(body?`${c.letter}. — ${body}`:`${c.letter}.`)}function buildDsSolutionCopyText(text,q,forAi){q=q||currentQuestion();let chunks=extractAbcdSolutionChunks(String(text||''));if(forAi){let letters=['A','B','C','D'].filter(L=>q[L]);let byL={};chunks.forEach(c=>{byL[c.letter]=c});chunks=letters.map(L=>byL[L]||{letter:L,verdict:'',body:''})}else chunks=finalizeAbcdSolutionChunks(chunks,q,true,false);return chunks.map(c=>buildDsSolutionPlainLine(c,!!forAi)).filter(Boolean).join('\n')}function formatDsSolutionPlainList(text,q,fromAi){q=q||currentQuestion();let chunks=extractAbcdSolutionChunks(String(text||''));chunks=finalizeAbcdSolutionChunks(chunks,q,true,!!fromAi);if(!chunks.length)return formatHintDisplay(String(text||''));let rows=chunks.map(c=>{let v=c.verdict||'';let rawBody=stripLoigiaiMarkdown(c.body||'');if(!v&&!rawBody)return '';let vCls=v==='Sai'?'dsVerdictSai':'dsVerdictDung';let head=v?`<span class="dsPlainHead"><b class="${vCls}">${esc(c.letter)}. ${esc(v)}</b> — </span>`:`<span class="dsPlainHead"><b>${esc(c.letter)}.</b> </span>`;let body=rawBody?`<span class="dsPlainBody">${formatHintDisplay(rawBody)}</span>`:'';return `<div class="dsSolutionPlainRow">${head}${body}</div>`}).filter(Boolean);return rows.length?`<div class="dsSolutionPlainList">${rows.join('')}</div>`:formatHintDisplay(String(text||''))}function formatDsSolutionRows(text,q,fromAi){let t=String(text||'').trim();q=q||currentQuestion();if(q&&q.Dang==='Đúng sai')return formatDsSolutionPlainList(t,q,!!fromAi);if(!t&&isCurrentQuestionDs())return formatDsSolutionPlainList('',q,!!fromAi);let chunks=extractAbcdSolutionChunks(t);if(chunks.length>=1||(q&&['A','B','C','D'].some(L=>q[L])))return formatAbcdSolutionList(chunks,q,true);return formatHintDisplay(t)}
function formatMcqSolutionRows(text,q){let t=String(text||'').trim();q=q||currentQuestion();let chunks=extractAbcdSolutionChunks(t);if(chunks.length>=1||q)return formatAbcdSolutionList(chunks,q,false);return formatHintDisplay(t)}
function formatDsHintText(text,isSolution,fromAi){text=String(text||'').trim();if(!text)return '';let q=currentQuestion();return isSolution?formatDsSolutionRows(text,q,fromAi):formatDsAnswerBadges(text)}
function formatTnHintText(text,isSolution){text=String(text||'').trim();if(!text)return '';return isSolution?formatMcqSolutionRows(text,currentQuestion()):formatMcqAnswerBadge(text)}
function applyAuto5050(hide){if(!hide||!hide.length)return;for(let L of hide){let el=document.getElementById('opt_'+L);if(el)el.classList.add('hidden5050')}let b=document.getElementById('btn5050');if(b)b.disabled=true;let bf=document.getElementById('btnFs5050');if(bf)bf.disabled=true;let rb=document.getElementById('resultBox');if(rb){rb.textContent='🎯 Đã loại 2 đáp án sai: '+hide.join(', ');rb.style.color='#1d4ed8'}}
function hintRawText(){let j=HINT_BY_Q[CUR];return j?String(j.hint||''):''}
function quizRestorePayload(){return{made:CURRENT_MADE||'',questions:QUESTIONS||[],level_filter:CURRENT_LEVEL||'',dang_filter:CURRENT_DANG||''}}
function optionHasHeavyMath(text){text=String(text||'');return text.length>48||/\$|\\frac|\\sqrt|\\begin|\\\[|\\\(/.test(text)}
function needsAbcdStackedLayout(q,chunks){q=q||{};for(let L of ['A','B','C','D']){if(q[L]&&optionHasHeavyMath(q[L]))return true;let c=(chunks||[]).find(x=>x.letter===L);if(c&&c.body&&optionHasHeavyMath(c.body))return true}return false}
function isQuizVisible(){let q=document.getElementById('quiz');return !!(q&&!q.classList.contains('hide'))}
function lockQuizPageScroll(){if(!isMobileQuizUI()||!isQuizVisible())return;document.body.classList.add('quiz-scroll-lock')}
function unlockQuizPageScroll(){document.body.classList.remove('quiz-scroll-lock');document.body.style.top=''}
function findTouchScrollEl(x,y){let el=document.elementFromPoint(x,y);while(el&&el!==document.documentElement){if(el.nodeType===1){let oy=getComputedStyle(el).overflowY;if((oy==='auto'||oy==='scroll')&&el.scrollHeight>el.clientHeight+1)return el}el=el.parentElement}return null}
function initMobileGestureGuard(){if(window._mobileGestureGuardInited)return;window._mobileGestureGuardInited=true;let startY=0,startX=0,tracking=false;document.addEventListener('touchstart',function(e){if(!isMobileQuizUI()||!isQuizVisible())return;if(e.touches.length!==1)return;startY=e.touches[0].clientY;startX=e.touches[0].clientX;tracking=true},{passive:true});document.addEventListener('touchmove',function(e){if(!tracking||!isMobileQuizUI()||!isQuizVisible())return;if(e.touches.length!==1)return;let y=e.touches[0].clientY,x=e.touches[0].clientX;let dy=y-startY;if(Math.abs(x-startX)>Math.abs(dy)+6)return;let scrollEl=findTouchScrollEl(x,y);if(scrollEl){if(scrollEl.scrollTop<=0&&dy>10){e.preventDefault()}return}let docTop=(document.scrollingElement||document.documentElement).scrollTop||0;if(docTop<=0&&dy>10)e.preventDefault()},{passive:false});document.addEventListener('touchend',function(){tracking=false},{passive:true})}
function toggleMobileNavBoard(e){if(e&&e.stopPropagation)e.stopPropagation();if(!isMobileQuizUI())return;MOBILE_NAV_OPEN=!MOBILE_NAV_OPEN;syncMobileQuizChrome()}
function syncMobileQuizChrome(){let mobile=isMobileQuizUI();document.documentElement.classList.toggle('mobile-quiz-ui',mobile);document.body.classList.toggle('mobile-nav-open',mobile&&MOBILE_NAV_OPEN);let nb=document.getElementById('btnMobileNavToggle');if(nb){nb.textContent=MOBILE_NAV_OPEN?'▴ Đóng bảng':'▾ Bảng câu';nb.setAttribute('aria-expanded',MOBILE_NAV_OPEN?'true':'false')}syncMobileQuizToolbar();syncVipSolutionButtons();syncInfographicButtons();if(mobile&&isQuizVisible())lockQuizPageScroll();else unlockQuizPageScroll()}
function isMobileQuizUI(){return window.matchMedia('(max-width:768px)').matches||window.matchMedia('(orientation:landscape) and (max-height:520px)').matches}
function syncMobileQuizToolbar(){let mobile=isMobileQuizUI();document.body.classList.toggle('mobile-quiz-ui',mobile);document.body.classList.toggle('mobile-quiz-tools-open',mobile&&MOBILE_QUIZ_TOOLS_OPEN);let tbtn=document.getElementById('btnQuizToolsToggle');if(tbtn){tbtn.classList.toggle('hide',!(mobile&&!FULLDE_ON));tbtn.textContent=MOBILE_QUIZ_TOOLS_OPEN?'✕':'☰';tbtn.setAttribute('aria-expanded',MOBILE_QUIZ_TOOLS_OPEN?'true':'false')}let fsTbtn=document.getElementById('btnFsToolsToggle');if(fsTbtn){fsTbtn.classList.toggle('hide',!(mobile&&FULLDE_ON));fsTbtn.textContent=MOBILE_QUIZ_TOOLS_OPEN?'✕':'☰';fsTbtn.setAttribute('aria-expanded',MOBILE_QUIZ_TOOLS_OPEN?'true':'false')}}
function toggleQuizTools(e){if(e&&e.stopPropagation)e.stopPropagation();if(!isMobileQuizUI())return;MOBILE_QUIZ_TOOLS_OPEN=!MOBILE_QUIZ_TOOLS_OPEN;syncMobileQuizToolbar()}
function initMobileQuizToolbar(){syncMobileQuizChrome();initMobileGestureGuard();if(window._mobileQuizToolbarInited)return;window._mobileQuizToolbarInited=true;window.addEventListener('resize',function(){syncMobileQuizChrome();if(!isQuizVisible())return;if(typeof CUR!=='undefined'&&QUESTIONS.length)renderQuestion()});window.addEventListener('orientationchange',function(){setTimeout(function(){syncMobileQuizChrome();if(!isQuizVisible())return;if(typeof CUR!=='undefined'&&QUESTIONS.length)renderQuestion()},120)})}
function fmtTime(sec){sec=Math.max(0,parseInt(sec,10)||0);let h=Math.floor(sec/3600);sec%=3600;let m=Math.floor(sec/60);let s=sec%60;let p=n=>String(n).padStart(2,'0');return h>0?`${p(h)}:${p(m)}:${p(s)}`:`${p(m)}:${p(s)}`}
function syncQuizTimerText(){let v=fmtTime(QUIZ_ELAPSED);let x=document.getElementById('quizTimerText');if(x)x.textContent=v;let fx=document.getElementById('fsQuizTimerText');if(fx)fx.textContent=v;let mx=document.getElementById('mobileQuizTimerText');if(mx)mx.textContent=v}
function startQuizTimer(){stopQuizTimer();QUIZ_ELAPSED=0;syncQuizTimerText();QUIZ_TIMER=setInterval(()=>{QUIZ_ELAPSED++;syncQuizTimerText()},1000)}
function stopQuizTimer(){if(QUIZ_TIMER){clearInterval(QUIZ_TIMER);QUIZ_TIMER=null}}
async function api(url,opts={}){let r=await fetch(url,opts);let txt=await r.text();let j;try{j=txt?JSON.parse(txt):{};}catch(e){j={error:'Không đọc được phản hồi từ máy chủ. Có thể Render đang timeout hoặc trả về HTML. Mã HTTP: '+r.status+'. Nội dung đầu: '+txt.slice(0,120)}}if(!r.ok||j.error){if(r.status==401){let next=encodeURIComponent(location.pathname+location.search);location='/login?next='+next}throw new Error(j.error||'Lỗi API')}return j}
function setOptions(id,arr){document.getElementById(id).innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option>${esc(x)}</option>`).join('')}
function lessonNum(s){s=normText(s||'');let m=s.match(/\bbai\s*(\d+)/);if(m)return parseInt(m[1],10);m=s.match(/^(\d+)/);return m?parseInt(m[1],10):9999}
function chapterNum(s){s=normText(s||'');let m=s.match(/\bchuong\s*(viii|vii|vi|iv|iii|ii|ix|x|i|\d+)\b/);if(m){let t=m[1];if(/^\d+$/.test(t))return parseInt(t,10);let rom={i:1,ii:2,iii:3,iv:4,v:5,vi:6,vii:7,viii:8,ix:9,x:10};return rom[t]||9999}return 9999}
function catalogSortKey(x){return [normText(x.Mon||''),normText(x.Lop||''),chapterNum(x.Chuong||''),normText(x.Chuong||''),lessonNum(x.BaiHoc||x.De||''),normText(x.BaiHoc||x.De||''),normText(x.BoDe||'')]}
function compareCatalog(a,b){let ka=catalogSortKey(a),kb=catalogSortKey(b);for(let i=0;i<ka.length;i++){if(ka[i]<kb[i])return -1;if(ka[i]>kb[i])return 1}return 0}
function uniqField(list,field){let seen=new Set(),out=[];for(let x of list||[]){let v=String((x||{})[field]||'').trim();if(!v||seen.has(v))continue;seen.add(v);out.push(v)}if(field==='BaiHoc')return out.sort((a,b)=>lessonNum(a)-lessonNum(b)||normText(a).localeCompare(normText(b),'vi'));if(field==='Chuong')return out.sort((a,b)=>chapterNum(a)-chapterNum(b)||normText(a).localeCompare(normText(b),'vi'));return out.sort((a,b)=>normText(a).localeCompare(normText(b),'vi'))}
function filterBaseCatalog(){let mon=val('fMon')||'';if(!mon)return CATALOG.slice();return CATALOG.filter(x=>x.Mon==mon)}
function filterCatalogUpTo(stopBefore){let list=filterBaseCatalog();let lop=val('fLop');if(lop)list=list.filter(x=>x.Lop==lop);if(stopBefore==='lop')return list;let chuong=val('fChuong');if(chuong)list=list.filter(x=>x.Chuong==chuong);if(stopBefore==='chuong')return list;let bai=val('fBaiHoc');if(bai)list=list.filter(x=>x.BaiHoc==bai);if(stopBefore==='baihoc')return list;let bode=val('fBoDe');if(bode)list=list.filter(x=>x.BoDe==bode);return list}
function setOptionsKeep(id,arr,keep){let el=document.getElementById(id);if(!el)return;keep=String(keep||'');if(keep&&!arr.includes(keep))keep='';el.innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option${x===keep?' selected':''}>${esc(x)}</option>`).join('');el.value=keep}
function refreshFilterOptions(){setOptionsKeep('fMon',uniqField(CATALOG,'Mon'),val('fMon'));let base=filterBaseCatalog();setOptionsKeep('fLop',uniqField(base,'Lop'),val('fLop'));let l1=filterCatalogUpTo('lop');setOptionsKeep('fChuong',uniqField(l1,'Chuong'),val('fChuong'));let l2=filterCatalogUpTo('chuong');setOptionsKeep('fBaiHoc',uniqField(l2,'BaiHoc'),val('fBaiHoc'));let l3=filterCatalogUpTo('baihoc');setOptionsKeep('fBoDe',uniqField(l3,'BoDe'),val('fBoDe'))}
function onFilterChange(level){if(level==='mon'){let e=document.getElementById('fLop');if(e)e.value='';let c=document.getElementById('fChuong');if(c)c.value='';let b=document.getElementById('fBaiHoc');if(b)b.value='';let d=document.getElementById('fBoDe');if(d)d.value=''}else if(level==='lop'){let c=document.getElementById('fChuong');if(c)c.value='';let b=document.getElementById('fBaiHoc');if(b)b.value='';let d=document.getElementById('fBoDe');if(d)d.value=''}else if(level==='chuong'){let b=document.getElementById('fBaiHoc');if(b)b.value='';let d=document.getElementById('fBoDe');if(d)d.value=''}else if(level==='baihoc'){let d=document.getElementById('fBoDe');if(d)d.value=''}if(level!=='extra')refreshFilterOptions();renderCatalog()}
function updateExamStrip(){const el=document.getElementById('examStrip');const msg=document.getElementById('examMsg');const tm=document.getElementById('examTimer');if(!el||!msg||!tm)return;const start=new Date('2026-06-11T00:00:00+07:00');const end=new Date('2026-06-12T23:59:59+07:00');const now=new Date();if(now<start){let d=Math.floor((start-now)/1000);let day=Math.floor(d/86400);d%=86400;let h=Math.floor(d/3600);d%=3600;let m=Math.floor(d/60);let s=d%60;msg.textContent='📢 Thông báo: Kỳ thi diễn ra ngày 11-12/06/2026';tm.textContent=`Còn ${day} ngày ${h}h ${m}m ${s}s`;el.classList.remove('hide');return}if(now<=end){msg.textContent='🔥 ĐANG TRONG THỜI GIAN THI 11-12/06/2026';tm.textContent='Chúc các em bình tĩnh, tự tin!';el.classList.remove('hide');return}msg.textContent='✅ Kỳ thi 11-12/06/2026 đã kết thúc';tm.textContent='Tiếp tục luyện tập để nâng điểm.';el.classList.remove('hide')}
function mergeUserAiProfile(src){src=src||{};if(src.ai_profile!==undefined)USER.ai_profile=src.ai_profile;if(src.ai_profile_label!==undefined)USER.ai_profile_label=src.ai_profile_label;if(src.ai_profile_hint!==undefined)USER.ai_profile_hint=src.ai_profile_hint;if(src.ai_profile_action!==undefined)USER.ai_profile_action=src.ai_profile_action;if(src.ai_key_source!==undefined)USER.ai_key_source=src.ai_key_source;if(src.ai_show_key_panel!==undefined)USER.ai_show_key_panel=src.ai_show_key_panel;if(src.ai_nudge_key!==undefined)USER.ai_nudge_key=src.ai_nudge_key;if(src.ai_server_key_count!==undefined)USER.ai_server_key_count=src.ai_server_key_count;if(src.using_user_keys!==undefined)USER.ai_using_user_keys=!!src.using_user_keys;if(src.user_gemini_keys!==undefined)USER.ai_user_gemini_keys=src.user_gemini_keys;if(src.has_keys!==undefined)USER.ai_has_keys=!!src.has_keys}
function aiProfileBadgeClass(code){if(!code)return'hide';if(String(code).endsWith('_OWN'))return'aiProfileOwn';if(String(code).endsWith('_POOL'))return'aiProfilePool';if(String(code)==='FREE')return'aiProfileFree';return'aiProfileWarn'}
function renderUserAiProfile(u){u=u||USER||{};let badge=document.getElementById('aiProfileBadge');if(badge){if(u.ai_profile&&u.ai_profile!=='FREE'&&u.can_ai_hint!==false){badge.textContent=u.ai_profile_label||'';badge.className='aiProfileBadge '+aiProfileBadgeClass(u.ai_profile)}else badge.className='aiProfileBadge hide'}let banner=document.getElementById('aiProfileBanner');if(banner){if(u.can_ai_hint&&u.ai_profile_hint){let cls='aiProfileBanner ';if(u.ai_profile&&String(u.ai_profile).endsWith('_NO_KEY'))cls+='aiProfileBannerErr';else if(u.ai_nudge_key)cls+='aiProfileBannerNudge';else cls+='aiProfileBannerOk';banner.className=cls;banner.innerHTML=`<b>${esc(u.ai_profile_label||'AI')}</b><div class="aiProfileBannerTxt">${esc(u.ai_profile_hint||'')}</div>`+(u.ai_nudge_key?'<button type="button" class="btn2 aiProfileBannerBtn" onclick="scrollToAiKeyPanel()">→ Nạp key AI của bạn</button>':'')}else banner.className='aiProfileBanner hide'}let detail=document.getElementById('aiProfileDetail');if(detail){if(u.can_ai_hint&&u.ai_profile_hint){let dcls='aiProfileBanner ';dcls+=u.ai_profile&&String(u.ai_profile).endsWith('_OWN')?'aiProfileBannerOk':(u.ai_nudge_key?'aiProfileBannerNudge':'aiProfileBannerOk');detail.className=dcls;detail.style.margin='8px 0 10px';detail.innerHTML=`<b>${esc(u.ai_profile_label||'')}</b><div class="aiProfileBannerTxt">${esc(u.ai_profile_hint||'')}</div>`}else detail.className='aiProfileBanner aiProfileBannerOk hide'}let panel=document.getElementById('aiKeyPanel');if(panel){if(u.ai_show_key_panel===false||u.can_save_own_ai_key===false)panel.classList.add('hide');else if(u.can_ai_hint)panel.classList.remove('hide')}}
function scrollToAiKeyPanel(){let p=document.getElementById('aiKeyPanel');if(!p)return;p.classList.remove('hide');p.scrollIntoView({behavior:'smooth',block:'start'})}
async function loadAiKeyPanel(){let panel=document.getElementById('aiKeyPanel');let st=document.getElementById('aiKeyStatus');if(!panel)return;if(USER.can_save_own_ai_key===false){panel.classList.add('hide');renderUserAiProfile(USER);return}try{let j=await api('/api/ai-config');mergeUserAiProfile(j);if(j.ai_show_key_panel!==false)panel.classList.remove('hide');else panel.classList.add('hide');renderUserAiProfile(USER);let parts=[];if(j.using_user_keys)parts.push(`Đã lưu ${j.user_gemini_keys||0} key của bạn`);else parts.push('Chưa lưu key — dán AIza... bên dưới');if(j.has_server_keys)parts.push(`Server có ${j.ai_server_key_count||0} key dự phòng`);if(j.has_keys)parts.push('✅ Có thể dùng Gợi ý AI');else parts.push('⚠️ Chưa có key — cần Lưu key');if(st)st.textContent=parts.join(' · ')}catch(e){if(st)st.textContent='Không tải trạng thái key: '+e.message}}
async function saveMyAiKey(){if(!USER.can_ai_hint){alert('Key AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}let raw=document.getElementById('myApiKeys').value.trim();if(!raw){alert('Dán ít nhất một key AIza...');return}try{let j=await api('/api/ai-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_keys:raw,provider:'GEMINI'})});alert(j.message||'Đã lưu key.');await loadAiKeyPanel()}catch(e){alert('Không lưu được: '+e.message)}}
function formatAiKeyCheckAlert(j){j=j||{};let msg=(j.ok?'✅ ':'❌ ')+(j.message||'');if(j.details&&j.details.length){let extra=[];for(let d of j.details){let lab=d.label||(d.key_hint?('Key #'+d.index+' ('+d.key_hint+')'):('Key #'+d.index));if(d.source&&!String(lab).includes(d.source))lab+=' — '+d.source;extra.push((d.ok?'✅':'❌')+' '+lab+': '+(d.message||''))}if(extra.length&&!String(msg).includes('Key #'))msg+='\n\n'+extra.join('\n')}return msg}
async function testMyAiKey(){if(!USER.can_ai_hint){alert('Key AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}let raw=document.getElementById('myApiKeys').value.trim();let body={provider:'GEMINI'};if(raw)body.api_keys=raw;try{let j=await api('/api/ai-key-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let ver=j.version?`\n\nPhiên bản server: ${j.version}`:'';alert(formatAiKeyCheckAlert(j)+ver)}catch(e){alert(e.message)}}
async function clearMyAiKey(){if(!confirm('Xóa key AI đã lưu trên server (chỉ của tài khoản này)?'))return;try{let j=await api('/api/ai-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clear_keys:true})});document.getElementById('myApiKeys').value='';alert(j.message||'Đã xóa key.');await loadAiKeyPanel()}catch(e){alert(e.message)}}
function updateAdminChrome(){let inQuiz=!!(document.getElementById('quiz')&&!document.getElementById('quiz').classList.contains('hide'));let qtb=document.getElementById('quizTopBar');if(qtb)qtb.classList.toggle('hide',!inQuiz);let bar=document.getElementById('adminBar');if(bar)bar.classList.toggle('hide',!USER.is_admin);let fsAdmin=!!USER.is_admin&&inQuiz;let fss=document.getElementById('btnFsSync');if(fss)fss.classList.toggle('hide',!fsAdmin||!FULLDE_ON);let fse=document.getElementById('btnFsEdit');if(fse)fse.classList.toggle('hide',!fsAdmin);let fsa=document.getElementById('btnFsAdd');if(fsa)fsa.classList.toggle('hide',!fsAdmin);let qat=document.getElementById('quizAdminTools');if(qat)qat.classList.toggle('hide',!USER.is_admin||!inQuiz);let qjw=document.getElementById('quizIdJumpWrap');if(qjw)qjw.classList.toggle('hide',!USER.is_admin||!inQuiz);syncInfographicButtons()}
function reindexQuizMaps(removedIdx){function shift(obj){let out={};for(let k in obj){let i=parseInt(k,10);if(isNaN(i))continue;if(i<removedIdx)out[i]=obj[k];else if(i>removedIdx)out[i-1]=obj[k]}return out}ANSWERS=shift(ANSWERS);RESULTS=shift(RESULTS);CHECKED=shift(CHECKED);LOCKED_Q=shift(LOCKED_Q);HINT_BY_Q=shift(HINT_BY_Q);SIMILAR_BY_Q=shift(SIMILAR_BY_Q)}
function insertQuizMaps(insertIdx){function shiftInsert(obj){let out={};for(let k in obj){let i=parseInt(k,10);if(isNaN(i))continue;if(i<insertIdx)out[i]=obj[k];else out[i+1]=obj[k]}return out}ANSWERS=shiftInsert(ANSWERS);RESULTS=shiftInsert(RESULTS);CHECKED=shiftInsert(CHECKED);LOCKED_Q=shiftInsert(LOCKED_Q);HINT_BY_Q=shiftInsert(HINT_BY_Q);SIMILAR_BY_Q=shiftInsert(SIMILAR_BY_Q)}
function remapQuizMapsByPerm(perm){function remap(obj){let out={};for(let ni=0;ni<perm.length;ni++){let oi=perm[ni];if(obj[oi]!==undefined)out[ni]=obj[oi];else if(obj[String(oi)]!==undefined)out[ni]=obj[String(oi)]}return out}ANSWERS=remap(ANSWERS);RESULTS=remap(RESULTS);CHECKED=remap(CHECKED);LOCKED_Q=remap(LOCKED_Q);HINT_BY_Q=remap(HINT_BY_Q);SIMILAR_BY_Q=remap(SIMILAR_BY_Q);VIP_Q_SHOW_ANS=remap(VIP_Q_SHOW_ANS);VIP_Q_SHOW_EXP=remap(VIP_Q_SHOW_EXP);ADMIN_HINT_SAVED=remap(ADMIN_HINT_SAVED)}
function regroupQuestionsByDang(anchorRow){if(!GROUP_BY_DANG||!QUESTIONS.length)return CUR;let tagged=QUESTIONS.map((q,i)=>({q:applyResolvedDang(Object.assign({},q)),oi:i}));let buckets={};for(let d of DANG_GROUP_ORDER_CLIENT)buckets[d]=[];let other=[];for(let t of tagged){let d=t.q.Dang||'Trắc nghiệm';if(buckets[d])buckets[d].push(t);else other.push(t)}let merged=[];for(let d of DANG_GROUP_ORDER_CLIENT)merged=merged.concat(buckets[d]);merged=merged.concat(other);let perm=merged.map(t=>t.oi);QUESTIONS=merged.map(t=>QUESTIONS[t.oi]);remapQuizMapsByPerm(perm);if(anchorRow){let ni=QUESTIONS.findIndex(q=>q._row===anchorRow);if(ni>=0)return ni}let ni=perm.indexOf(CUR);return ni>=0?ni:0}
async function refreshCatalogFromMeta(){try{let m=await api('/api/meta');if(m.loading)return false;META=META||{};Object.assign(META,m);if(m.user){USER=m.user;renderUserAiProfile(USER)}CATALOG=m.catalog||[];let info=document.getElementById('info');if(info)info.textContent=`${m.count_questions} câu hỏi | ${m.count_catalog} đề/thẻ đề | Nạp: ${m.loaded_at}`;if(!document.getElementById('home').classList.contains('hide')){refreshFilterOptions();renderCatalog();initRpPracticePanel()}showAdminDuplicateSheetNotice();return true}catch(e){return false}}
async function init(){updateExamStrip();META=await api('/api/meta');USER=META.user||{};document.getElementById('me').textContent=`${USER.hoten||''} (${USER.role||''}${USER.trial_until?' - hết trial: '+USER.trial_until:''}${USER.account_until?' - hết hạn: '+USER.account_until:''})`;renderUserAiProfile(USER);updateAdminChrome();await loadAiKeyPanel();if(META.loading){document.getElementById('info').textContent='Đang nạp Google Sheet... lần đầu có thể chờ 10–40 giây';document.getElementById('catalog').innerHTML=`<div class="card loadCard"><h3>⏳ Hệ thống đang khởi động</h3><p><b>Vui lòng chờ, không cần bấm lại nhiều lần.</b></p><p>${esc(META.loading_message||'Đang nạp dữ liệu từ Google Sheet...')}</p><div class="loadWarn"><b>Lưu ý:</b> lần đầu Render Free vừa “thức dậy” và vừa nạp Google Sheet thì có thể chờ khoảng <b>10–40 giây</b>. Trang sẽ tự tải lại sau vài giây.</div>${META.load_error?'<p class="loadErr"><b>Lỗi:</b> '+esc(META.load_error)+'</p>':''}<p class="muted">Trang sẽ tự thử lại sau 3 giây. Không cần đăng nhập lại.</p></div>`;document.getElementById('countCat').textContent='';setTimeout(init,3000);return;}CATALOG=META.catalog||[];document.getElementById('info').textContent=`${META.count_questions} câu hỏi | ${META.count_catalog} đề/thẻ đề | Nạp: ${META.loaded_at}`;refreshFilterOptions();renderCatalog();initRpPracticePanel();showAdminDuplicateSheetNotice();handleShareDeepLink();handleQidDeepLink()}
function dangCountLookup(fc,dang){if(!fc||!fc.dang)return 0;let nd=normDangClient(dang);if(fc.dang[nd]!=null)return fc.dang[nd];let n=0;for(let k in fc.dang)if(normDangClient(k)===nd)n+=fc.dang[k]||0;return n}
function comboCountLookup(fc,lv,dang){if(!fc||!fc.combo)return 0;lv=(lv||'').trim().toUpperCase();let nd=normDangClient(dang);let k1=lv+'|'+nd,k2=lv+'|'+dang;if(fc.combo[k1]!=null)return fc.combo[k1];if(fc.combo[k2]!=null)return fc.combo[k2];let n=0;for(let k in fc.combo){let p=k.split('|');if(p[0]===lv&&normDangClient(p[1]||'')===nd)n+=fc.combo[k]||0}return n}
function filterMatchCount(x,lv,dang){let fc=x&&x.FilterCounts;if(!fc)return null;lv=(lv||'').trim().toUpperCase();dang=(dang||'').trim();if(lv&&dang)return comboCountLookup(fc,lv,dang);if(dang)return dangCountLookup(fc,dang);if(lv)return fc.level[lv]||0;return null}
function okFilter(x){let s=normText(val('fSearch'));let lv=(val('fMucDo')||'').trim().toUpperCase();let dg=(val('fDang')||'').trim();let mc=filterMatchCount(x,lv,dg);if(mc!==null&&mc===0)return false;let solOnly=document.getElementById('fSolFullOnly')&&document.getElementById('fSolFullOnly').checked;if(solOnly&&(parseInt(x.SolFull,10)||0)<=0)return false;let blob=normText([x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.DangBaiTap,x.BoDe,x.De,x.MucDo,x.Dang].join(' '));let levelOk=!lv||mc!==null||normText(x.MucDo||'').includes(normText(lv));let dangOk=!dg||mc!==null||normText(x.Dang||'').includes(normText(dg));return(!val('fMon')||x.Mon==val('fMon'))&&(!val('fLop')||x.Lop==val('fLop'))&&(!val('fChuong')||x.Chuong==val('fChuong'))&&(!val('fBaiHoc')||x.BaiHoc==val('fBaiHoc'))&&(!val('fBoDe')||x.BoDe==val('fBoDe'))&&levelOk&&dangOk&&(!s||blob.includes(s))}
function renderCatalog(){let list=CATALOG.filter(okFilter).sort(compareCatalog);let selectedLv=(val('fMucDo')||'').toUpperCase();let selectedDang=(val('fDang')||'').trim();document.getElementById('countCat').textContent=`(${list.length} mục)`;document.getElementById('catalog').innerHTML=list.map(x=>{let access=x.QuyenTruyCap||'FREE';let solFull=parseInt(x.SolFull,10)||0;let solPart=parseInt(x.SolPartial,10)||0;let solLine=(solFull||solPart)?`<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px">${solFull?`<span class="tag solFullTag">📗 LG đầy đủ: ${solFull}</span>`:''}${solPart?`<span class="tag solPartTag">📝 LG một phần: ${solPart}</span>`:''}</div>`:'';let locked=USER.is_trial&&access!='FREE';let btn=locked?`<button class="btnRed" disabled>Khóa VIP</button>`:`<button class="btnStartStrong" onclick="openStartModal('${x.MaDe}')">🚀 Làm bài + xáo trộn</button>`;let note=locked?`<div class="muted" style="color:#991b1b;margin-top:6px">Tài khoản dùng thử chỉ mở đề FREE.</div>`:'';let hint=locked?'':`<div class="shuffleHint">Có thể chọn: xáo câu, xáo đáp án hoặc xáo cả 2.</div>`;let mc=filterMatchCount(x,selectedLv,selectedDang);let filterNotice='';if((selectedLv||selectedDang)&&mc!==null){filterNotice=`<div style="margin-top:6px;padding:6px 8px;border-radius:8px;background:#dcfce7;border:1px solid #86efac;color:#166534;font-weight:900">🎯 Có <b>${mc}</b> câu${selectedLv?' · mức '+esc(selectedLv):''}${selectedDang?' · dạng '+esc(selectedDang):''} trong đề này</div>`}let title=esc(x.BaiHoc||x.De||'Đề luyện tập');let sub=x.Chuong?`<div class="muted" style="margin-top:4px;font-size:13px">${esc(x.Chuong)}</div>`:'';let mid=String(x.MaDe||'').replace(/'/g,"\\'");let shareLabel=esc(examDisplayTitle(x));let shareRow=`<div class="shareRow"><span class="shareUrl">🔗 ${shareLabel}</span><span style="display:flex;gap:6px;flex-wrap:wrap"><button type="button" class="btnShare" onclick="copyExamShareLink('${mid}')">📋 Chép link</button><button type="button" class="btnShare" onclick="copyExamShareLink('${mid}',1)" title="Học viên tự chọn xáo trộn">⚙️ Link có xáo trộn</button></span></div>`;return `<div class="card" id="shareCard_${String(x.MaDe||'').replace(/"/g,'')}"><h3>${title}</h3>${sub}<div><span class="tag">${esc(x.Mon)}</span><span class="tag">Lớp ${esc(x.Lop)}</span><span class="tag">${esc(x.SoCau)} câu</span><span class="tag">${esc(access)}</span></div><div class="line"></div><div><b>Chương:</b> ${esc(x.Chuong)}</div><div><b>Bài:</b> ${esc(x.BaiHoc)}</div><div><b>Dạng:</b> ${esc(x.Dang)}</div><div><b>Mức độ:</b> ${esc(x.MucDo)}</div><div><b>Bộ đề:</b> ${esc(x.BoDe)}</div>${filterNotice}${solLine}${note}${hint}${shareRow}<div style="text-align:right;margin-top:10px">${btn}</div></div>`}).join('')||'<div class="muted">Không có đề phù hợp.</div>';typeset()}
async function syncData(){if(!confirm('Đồng bộ lại dữ liệu từ Google Sheet?'))return;let j=await api('/api/sync',{method:'POST'});alert(j.message||'Đã bắt đầu đồng bộ.');await init();if(USER.is_admin&&META&&META.duplicate_report)alertDuplicateSheetReport(META.duplicate_report)}
async function dedupeSheetDuplicates(){if(!USER.is_admin)return;try{let j=await api('/api/question/dedupe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:true})});let n=parseInt(j.would_delete||((j.plan||{}).delete_count),10)||0;if(n<=0){alert(j.message||'Không có dòng trùng trên Sheet.');return}let lines=((j.plan||{}).samples||[]).slice(0,8);let msg='Phát hiện '+n+' dòng TRÙNG trên tab Cau_Hoi.\n\nQuy tắc: giữ dòng đầu (số nhỏ nhất), xóa các bản sao.\n\n(Không dùng AI — chỉ xóa dòng trên Google Sheet.)\n\n'+(lines.length?('Ví dụ:\n'+lines.join('\n')+'\n\n'):'')+'Xóa '+n+' dòng trùng khỏi Google Sheet?';if(!confirm(msg))return;if(!confirm('Xác nhận lần 2: xóa vĩnh viễn '+n+' dòng trùng?'))return;let j2=await api('/api/question/dedupe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:false})});alert((j2.message||('Đã xóa '+j2.deleted+' dòng trùng.'))+'\n\n✅ Mục lục tự cập nhật — không cần bấm Đồng bộ Sheet thêm.');if(j2.duplicate_report)META=META||{},META.duplicate_report=j2.duplicate_report;await refreshCatalogFromMeta()}catch(e){let m=e.message||'';if(/429|quota|write requests/i.test(m))alert('Không xóa trùng được — Google Sheet giới hạn ghi (429).\n\n🧹 Xóa trùng KHÔNG dùng AI (nút 🧪 Test AI / 💡 AI kiểm tra là chức năng khác).\n\nĐợi ~1 phút rồi bấm lại 🧹 Xóa trùng Sheet.');else alert('Không xóa trùng được: '+m)}}
async function testServerAiKey(){try{let j=await api('/api/ai-key-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:'GEMINI'})});let ver=j.version?`\n\nPhiên bản server: ${j.version}`:'';alert(formatAiKeyCheckAlert(j)+ver);}catch(e){alert(e.message);}}
function closeStartModal(){document.getElementById('startModal').classList.add('hide')}
function openStartModal(made){CURRENT_MADE=made;CURRENT_LEVEL=(val('fMucDo')||'').trim().toUpperCase();CURRENT_DANG=(val('fDang')||'').trim();START_IS_RETRY=false;document.getElementById('startModalTitle').textContent='Thiết lập làm bài';document.getElementById('chkShuffleQ').checked=false;document.getElementById('chkShuffleA').checked=false;let gd=document.getElementById('chkGroupDang');if(gd)gd.checked=true;let note=document.getElementById('startFilterNote');if(note){let item=CATALOG.find(x=>x.MaDe===made)||{};let lv=CURRENT_LEVEL;let dg=CURRENT_DANG;let mc=filterMatchCount(item,lv,dg);if(dg||lv){let parts=[];if(dg)parts.push('dạng <b>'+esc(dg)+'</b>'+(mc!=null?' — <b>'+mc+'</b> câu':''));if(lv)parts.push('mức <b>'+esc(lv)+'</b>');note.innerHTML='🎯 Chỉ làm câu '+parts.join(' · ')+'.';note.classList.remove('hide')}else{note.innerHTML='';note.classList.add('hide')}}document.getElementById('startModal').classList.remove('hide')}
function openRetryModal(){if(!CURRENT_MADE){alert('Chưa xác định được mã đề.');return}CURRENT_LEVEL=(val('fMucDo')||CURRENT_LEVEL||'').trim().toUpperCase();CURRENT_DANG=(val('fDang')||CURRENT_DANG||'').trim();START_IS_RETRY=true;document.getElementById('startModalTitle').textContent='Làm lại đề';let note=document.getElementById('startFilterNote');if(note){let item=CATALOG.find(x=>x.MaDe===CURRENT_MADE)||{};let mc=filterMatchCount(item,CURRENT_LEVEL,CURRENT_DANG);if(CURRENT_DANG||CURRENT_LEVEL){let parts=[];if(CURRENT_DANG)parts.push('dạng <b>'+esc(CURRENT_DANG)+'</b>'+(mc!=null?' — <b>'+mc+'</b> câu':''));if(CURRENT_LEVEL)parts.push('mức <b>'+esc(CURRENT_LEVEL)+'</b>');note.innerHTML='🎯 Chỉ làm câu '+parts.join(' · ')+'.';note.classList.remove('hide')}else{note.innerHTML='';note.classList.add('hide')}}document.getElementById('startModal').classList.remove('hide')}
async function confirmStartQuiz(){let made=CURRENT_MADE;if(!made)return;let sq=document.getElementById('chkShuffleQ').checked;let sa=document.getElementById('chkShuffleA').checked;let gd=document.getElementById('chkGroupDang');let groupBy=gd?gd.checked:true;let lv=(val('fMucDo')||'').trim().toUpperCase();let dg=(val('fDang')||'').trim();CURRENT_LEVEL=lv;CURRENT_DANG=dg;closeStartModal();if(START_IS_RETRY&&!SUBMITTED&&Object.keys(ANSWERS).length){if(!confirm('Làm lại sẽ xóa bài đang làm. Tiếp tục?'))return}await startQuiz(made,sq,sa,lv,dg,groupBy)}
function pickShufflePreset(kind){document.getElementById('chkShuffleQ').checked=kind==='q'||kind==='both';document.getElementById('chkShuffleA').checked=kind==='a'||kind==='both';if(kind==='none'){document.getElementById('chkShuffleQ').checked=false;document.getElementById('chkShuffleA').checked=false}confirmStartQuiz()}
function updateShuffleBadge(j){let el=document.getElementById('shuffleBadge');if(!el)return;let parts=[];if(j&&j.shuffle_questions)parts.push('Xáo câu');if(j&&j.shuffle_options)parts.push('Xáo đáp án');if(parts.length){el.textContent=parts.join(' + ');el.classList.remove('hide')}else{el.textContent='';el.classList.add('hide')}}
function deriveKhoi(lop){let s=String(lop||'').trim();if(!s)return '';let m=s.match(/^(\d{1,2})/);if(m)return m[1];let m2=s.match(/\b(10|11|12)\b/);return m2?m2[1]:''}
function rpCatalogBase(){return(CATALOG||[]).filter(x=>x.Mon&&x.Lop)}
function rpFilterCatalog(){let mon=val('rpMon'),khoi=val('rpKhoi'),lop=val('rpLop');return rpCatalogBase().filter(x=>{if(mon&&x.Mon!==mon)return false;if(khoi&&deriveKhoi(x.Lop)!==khoi)return false;if(lop&&x.Lop!==lop)return false;return true})}
function setRpSelectOptions(selId,opts,cur,ph){let el=document.getElementById(selId);if(!el)return;let keep=cur||el.value;el.innerHTML=(ph||'<option value="">—</option>')+opts.map(v=>`<option value="${escAttr(v)}">${esc(v)}</option>`).join('');if(keep&&opts.includes(keep))el.value=keep}
function refreshRpScopeOptions(){if(RP_SCOPE_LOCKED)return;let mon=val('rpMon');let base=rpCatalogBase();setRpSelectOptions('rpMon',uniqField(base,'Mon'),mon,'<option value="">— Chọn môn —</option>');let k1=mon?base.filter(x=>x.Mon===mon):[];let khois=[...new Set(k1.map(x=>deriveKhoi(x.Lop)).filter(Boolean))].sort((a,b)=>(Number(a)||0)-(Number(b)||0)||String(a).localeCompare(String(b),'vi'));let khoiEl=document.getElementById('rpKhoi');if(khoiEl){khoiEl.disabled=!mon;khoiEl.classList.toggle('rpLockable',true);setRpSelectOptions('rpKhoi',khois,val('rpKhoi'),'<option value="">— Chọn khối —</option>')}let khoi=val('rpKhoi');let k2=khoi?k1.filter(x=>deriveKhoi(x.Lop)===khoi):[];let lopEl=document.getElementById('rpLop');if(lopEl){lopEl.disabled=!khoi;lopEl.classList.toggle('rpLockable',true);setRpSelectOptions('rpLop',uniqField(k2,'Lop'),val('rpLop'),'<option value="">— Chọn lớp —</option>')}maybeLockRpScope()}
function onRpScopeChange(level){if(RP_SCOPE_LOCKED)return;if(level==='mon'){setVal('rpKhoi','');setVal('rpLop','')}else if(level==='khoi')setVal('rpLop','');refreshRpScopeOptions()}
function maybeLockRpScope(){let mon=val('rpMon'),khoi=val('rpKhoi'),lop=val('rpLop');if(!mon||!khoi||!lop)return;RP_SCOPE_LOCKED=true;let wrap=document.querySelector('.practiceRandomPanel');if(wrap)wrap.classList.add('rpLocked');['rpMon','rpKhoi','rpLop'].forEach(id=>{let e=document.getElementById(id);if(e)e.disabled=true});let bu=document.getElementById('btnRpUnlock');if(bu)bu.style.display='';let note=document.getElementById('rpScopeNote');if(note){note.innerHTML=`🔒 Phạm vi: <b>${esc(mon)}</b> · Khối <b>${esc(khoi)}</b> · Lớp <b>${esc(lop)}</b>`;note.classList.remove('hide')}let cw=document.getElementById('rpChuongWrap');if(cw)cw.classList.remove('hide');renderRpChuongList()}
function unlockRpScope(){RP_SCOPE_LOCKED=false;let wrap=document.querySelector('.practiceRandomPanel');if(wrap)wrap.classList.remove('rpLocked');let bu=document.getElementById('btnRpUnlock');if(bu)bu.style.display='none';let note=document.getElementById('rpScopeNote');if(note){note.innerHTML='';note.classList.add('hide')}let cw=document.getElementById('rpChuongWrap');if(cw)cw.classList.add('hide');refreshRpScopeOptions()}
function renderRpChuongList(){let list=uniqField(rpFilterCatalog(),'Chuong');let box=document.getElementById('rpChuongList');if(!box)return;let allOn=!!(document.getElementById('rpChuongAll')&&document.getElementById('rpChuongAll').checked);if(!list.length){box.innerHTML='<span class="muted">Chưa có chương trong phạm vi này.</span>';return}box.innerHTML=list.map(c=>`<label class="${allOn?'rpChOn':''}"><input type="checkbox" class="rpChuongCb" value="${escAttr(c)}" ${allOn?'disabled checked':'onchange="syncRpChuongLbl(this)"'}> ${esc(c)}</label>`).join('')}
function toggleRpChuongAll(){renderRpChuongList()}
function syncRpChuongLbl(cb){if(!cb)return;let lb=cb.closest('label');if(lb)lb.classList.toggle('rpChOn',cb.checked)}
function getRpSelectedChuongs(){let allEl=document.getElementById('rpChuongAll');if(allEl&&allEl.checked)return[];let out=[];document.querySelectorAll('.rpChuongCb:checked').forEach(cb=>{if(cb.value)out.push(cb.value)});return out}
function syncRpFromMainFilters(){if(RP_SCOPE_LOCKED)return;let m=val('fMon'),l=val('fLop');if(m)setVal('rpMon',m);refreshRpScopeOptions();if(l&&deriveKhoi(l)){setVal('rpKhoi',deriveKhoi(l));refreshRpScopeOptions();setVal('rpLop',l);refreshRpScopeOptions()}}
function initRpPracticePanel(){syncRpFromMainFilters();if(!RP_SCOPE_LOCKED)refreshRpScopeOptions()}
async function startRandomPractice(){try{let mon=val('rpMon'),khoi=val('rpKhoi'),lop=val('rpLop');if(!mon||!khoi||!lop){alert('Hãy chọn đủ Môn, Khối và Lớp trước.');return}if(!RP_SCOPE_LOCKED)maybeLockRpScope();let chuongs=getRpSelectedChuongs();let allEl=document.getElementById('rpChuongAll');if(allEl&&!allEl.checked&&!chuongs.length){alert('Chọn ít nhất một Chương, hoặc tick «Tất cả chương».');return}let solOnly=!!(document.getElementById('fSolFullOnly')&&document.getElementById('fSolFullOnly').checked);let lv=(val('fMucDo')||'').trim().toUpperCase();let j=await api('/api/start-random',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mon,khoi,lop,chuongs,level:lv,sol_full_only:solOnly?1:0,shuffle_a:1})});if(!j||!j.questions||!j.questions.length){alert(j&&j.error?j.error:'Không đủ câu trong phạm vi đã chọn để ghép đề (cần 18 TN + 4 Đ/S + 6 TLN).');return}enterQuizSession(j,j.made||'',lv,'','',false)}catch(e){alert('Không tạo được đề ngẫu nhiên: '+(e.message||e))}}
function quizSectionLabel(i){if(!GROUP_BY_DANG||!QUESTIONS.length)return null;let q=applyResolvedDang(QUESTIONS[i]);if(i===0)return q.Dang||null;let prev=applyResolvedDang(QUESTIONS[i-1]);return(q.Dang||'')!==(prev.Dang||'')?q.Dang:null}
function enterQuizSession(j,made,lv,dgNorm,dg,applyClientFilter){if(getShareParams().de)clearShareQuery();SID=j.sid;GROUP_BY_DANG=j.group_by_dang!==false;RANDOM_PRACTICE=!!j.random_practice;if(typeof j.admin==='boolean')USER.is_admin=j.admin;if(typeof j.can_view_solution_live==='boolean')USER.can_view_solution_live=j.can_view_solution_live;QUESTIONS=(j.questions||[]).map(q=>applyResolvedDang(q));if(applyClientFilter&&(lv||dgNorm||dg)){QUESTIONS=applyQuizFilters(QUESTIONS,lv,dgNorm||dg)}if(!QUESTIONS.length){let item=CATALOG.find(x=>x.MaDe==made)||{};let mc=filterMatchCount(item,lv,dgNorm||dg);let msg=RANDOM_PRACTICE?'Không ghép được đề ngẫu nhiên.':'Không có câu';if(lv&&dg)msg+=` mức ${lv} dạng ${dgNorm||dg}`;else if(dg)msg+=` dạng ${dgNorm||dg}`;else if(lv)msg+=` mức ${lv}`;msg+=' trong đề này.';if(mc)msg+=`\n\nMục lục báo có ${mc} câu — bấm 🔄 Đồng bộ Sheet, Ctrl+F5, thử lại.`;else if(lv&&dg)msg+='\n\nThử bỏ Mức độ hoặc Dạng câu về Tất cả.';alert(msg);return}CURRENT_MADE=made;CURRENT_LEVEL=lv;CURRENT_DANG=dgNorm||dg||j.dang_filter||'';CUR=0;ANSWERS={};SUBMITTED=!!USER.is_admin;RESULTS={};CHECKED={};LOCKED_Q={};COMPLETED_NOTICE=false;HINT_BY_Q={};SIMILAR_BY_Q={};SIMILAR_LOADING=false;SIMILAR_LOADING_Q=null;FS_ANS_FORCE=null;FS_EXP_FORCE=null;VIP_Q_SHOW_ANS={};VIP_Q_SHOW_EXP={};document.getElementById('home').classList.add('hide');document.getElementById('quiz').classList.remove('hide');document.getElementById('resultBox').textContent=USER.is_admin?'ADMIN: đang xem đáp án/lời giải':(USER.is_trial?'DÙNG THỬ: chỉ luyện đề FREE, không chấm điểm':'');let c=CATALOG.find(x=>x.MaDe==made)||{};let lvTag=lv?` | Mức: ${lv}`:'';let n=QUESTIONS.length;let dgShow=CURRENT_DANG||j.dang_filter||'';let dgTag=dgShow?` | Dạng: ${dgShow} (${n} câu)`:'';if(RANDOM_PRACTICE||j.random_title){document.getElementById('quizTitle').textContent=`🎲 ${j.random_title||'Tự luyện ngẫu nhiên'} | ${n} câu${lvTag}`}else{document.getElementById('quizTitle').textContent=`${c.Mon||''} ${c.Lop?'- Lớp '+c.Lop:''} | ${c.De||c.BaiHoc||''}${lvTag}${dgTag}`}updateFilterBadge(lv,dgShow,n);updateShuffleBadge(j);startQuizTimer();updateAdminChrome();renderNav();renderQuestion();MOBILE_NAV_OPEN=false;syncMobileQuizChrome();if(j.trial_message)alert(j.trial_message)}
async function startQuiz(made,shuffleQ=false,shuffleA=false,level='',dang='',groupByDang=true){try{let lv=(level||val('fMucDo')||CURRENT_LEVEL||'').trim().toUpperCase();let dg=(dang||val('fDang')||CURRENT_DANG||'').trim();let dgNorm=dg?normDangClient(dg):'';let j=await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({made,shuffle_q:shuffleQ?1:0,shuffle_a:shuffleA?1:0,level:lv,dang:dgNorm||dg,group_by_dang:groupByDang?1:0})});enterQuizSession(j,made,lv,dgNorm,dg,true)}catch(e){alert('Không mở được đề: '+e.message)}}
function backHome(){stopQuizTimer();FS_ANS_FORCE=null;FS_EXP_FORCE=null;MOBILE_NAV_OPEN=false;MOBILE_QUIZ_TOOLS_OPEN=false;VIP_Q_SHOW_ANS={};VIP_Q_SHOW_EXP={};unlockQuizPageScroll();updateFilterBadge('','',null);document.getElementById('quiz').classList.add('hide');document.getElementById('home').classList.remove('hide');syncMobileQuizChrome();updateAdminChrome()}
function ensureFullModeOverrides(){
    if(document.getElementById('LDVL_FS_OVR')) return;
    let st=document.createElement('style');
    st.id='LDVL_FS_OVR';
    st.textContent=
        "body.fullde-mode #quiz .quizLayout{grid-template-columns:minmax(0,1fr) 220px!important;gap:8px!important;padding:0 8px 8px!important}"+
        "body.fullde-mode #qtext{flex:0 0 auto!important;min-height:0!important;padding:12px!important;overflow:visible!important;font-size:clamp(16px,2.4vw,22px)!important}"+
        "body.fullde-mode #options{flex:0 0 auto!important;margin-top:8px!important;position:relative!important;z-index:2!important;background:var(--bg)!important}"+
        "body.fullde-mode .mcqSplit,body.fullde-mode .mcqSplitDs,body.fullde-mode .mcqSplitTln{grid-template-columns:minmax(0,1.2fr) minmax(260px,0.8fr)!important;gap:16px!important}"+
        "body.fullde-mode .mcqSplitDs{grid-template-columns:minmax(0,1.1fr) minmax(300px,0.9fr)!important}"+
        "body.fullde-mode .mcqSplitTln{grid-template-columns:minmax(0,1.15fr) minmax(280px,0.85fr)!important}"+
        "body.fullde-mode .mcqSplitImg .qimg{max-height:min(58vh,480px)!important}"+
        "body.fullde-mode .mcqSplitDs .mcqSplitImg .qimg{max-height:min(60vh,500px)!important}"+
        "body.fullde-mode .mcqSplitTln .mcqSplitImg .qimg{max-height:min(62vh,520px)!important}"+
        "body.fullde-mode .shortAnsInput{font-size:24px!important;width:6em!important;max-width:140px!important}"+
        "body.fullde-mode .dsSolutionTn:not(.dsSolutionRows){grid-template-columns:repeat(2,minmax(0,1fr))!important}"+
        "@media(min-width:1200px){body.fullde-mode .dsSolutionTn:not(.dsSolutionRows){grid-template-columns:repeat(4,minmax(0,1fr))!important}body.fullde-mode .mcqSplit{grid-template-columns:minmax(0,1.1fr) minmax(300px,0.9fr)!important}body.fullde-mode .mcqSplitDs{grid-template-columns:minmax(0,1fr) minmax(340px,1fr)!important}body.fullde-mode .mcqSplitTln{grid-template-columns:minmax(0,1.1fr) minmax(320px,0.9fr)!important}}"+
        "body.fullde-mode #qtext .qimg{max-height:min(42vh,280px)!important;display:block!important;margin:10px auto 12px!important}"+
        "body.fullde-mode #fsOnlyTools button{font-size:11px!important;padding:4px 7px!important}"+
        "body.fullde-mode #quiz .quizLayout>div:last-child{overflow:auto!important}"+
        "body.fullde-mode #quiz .quizLayout>div:last-child>.panel{overflow:auto!important}"+
        "body.fullde-mode #navNums{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:6px!important;overflow:auto!important;align-content:start!important}"+
        "body.fullde-mode #navNums .num{display:block!important;visibility:visible!important;opacity:1!important}"+
        "body.fullde-mode.fsnav-hidden #quiz .quizLayout{grid-template-columns:1fr 0px!important}"+
        "body.fullde-mode.fsnav-hidden #quiz .quizLayout>div:last-child{display:none!important}"+
        "@media(max-width:900px){body.fullde-mode #quiz .quizLayout{grid-template-columns:minmax(0,1fr) 150px!important}body.fullde-mode #navNums{grid-template-columns:repeat(3,minmax(0,1fr))!important}}"+
        "@media(max-width:768px) and (orientation:portrait){body.fullde-mode .mcqSplit,body.fullde-mode .mcqSplitDs,body.fullde-mode .mcqSplitTln{grid-template-columns:1fr!important}body.fullde-mode .mcqSplitImg .qimg,body.fullde-mode .mcqSplitDs .mcqSplitImg .qimg,body.fullde-mode .mcqSplitTln .mcqSplitImg .qimg{max-height:min(52vh,420px)!important}body.fullde-mode #qtext .qimg{max-height:min(50vh,400px)!important}}"+
        "@media(orientation:landscape) and (max-height:520px){body.fullde-mode .mcqSplit,body.fullde-mode .mcqSplitDs,body.fullde-mode .mcqSplitTln{grid-template-columns:minmax(0,38%) minmax(0,62%)!important;gap:8px!important}body.fullde-mode .mcqSplitImg .qimg,body.fullde-mode .mcqSplitDs .mcqSplitImg .qimg,body.fullde-mode .mcqSplitTln .mcqSplitImg .qimg{max-height:min(calc(100dvh - 120px),240px)!important}body.fullde-mode .mcqSplitOpts{max-height:none!important;overflow:visible!important}body.fullde-mode .shortAnsCompact .shortAnsQtext{max-height:none!important;overflow:visible!important}body.fullde-mode .shortAnsFieldRow{position:sticky!important;bottom:0!important;background:var(--surface)!important;z-index:5!important}}"+
        "@media(max-width:760px){body.fullde-mode #quiz .quizLayout{grid-template-columns:1fr!important;grid-template-rows:minmax(0,1fr) auto!important;padding:0 4px 4px!important}body.fullde-mode #quiz .quizLayout>div:last-child{max-height:92px!important}body.fullde-mode #navNums{grid-template-columns:repeat(8,minmax(32px,1fr))!important;overflow-x:auto!important;overflow-y:hidden!important}body.fullde-mode #navNums .num{padding:3px 0!important;font-size:10px!important}body.fullde-mode #fsOnlyTools{gap:3px!important;padding:3px 4px!important}body.fullde-mode #fsOnlyTools button{font-size:9px!important;padding:3px 5px!important}body.fullde-mode #qtext{font-size:14px!important;padding:8px!important}body.fullde-mode #qtext .qimg{max-height:min(34vh,200px)!important}body.fullde-mode .opt{padding:6px 7px!important;font-size:13px!important;margin:3px 0!important}body.fullde-mode .tfrow{grid-template-columns:28px minmax(0,1fr) 34px!important;grid-template-areas:'lbl stmt opts'!important}body.fullde-mode .tfrow .dsCircle{grid-area:lbl!important;justify-self:center!important}body.fullde-mode .tfOpts{flex-direction:column!important;justify-content:flex-start!important;padding-left:0!important;width:34px!important}body.fullde-mode .tfLblFull{display:none!important}body.fullde-mode .tfLblShort{display:inline!important}body.fullde-mode .tfOpt{flex:0!important;width:100%!important;max-width:none!important;min-width:0!important;padding:5px 2px!important;font-size:11px!important;text-align:center!important}body.fullde-mode .tfOpt input{position:absolute!important;opacity:0!important;width:0!important;height:0!important}}";
    document.head.appendChild(st);
}
function syncFsNavBtn(){
    let btn=document.getElementById('btnFsNav');
    if(btn)btn.textContent=FS_NAV_HIDDEN?'☰ Hiện bảng':'☰ Ẩn bảng';
}
function ensureFsNavBtn(){
    let box=document.getElementById('fsOnlyTools');
    if(!box)return;
    let btn=document.getElementById('btnFsNav');
    if(!btn){
        btn=document.createElement('button');
        btn.type='button';
        btn.id='btnFsNav';
        btn.className='btn2';
        btn.onclick=toggleFsNav;
        box.appendChild(btn);
    }
    syncFsNavBtn();
}
function ensureNavInfo(){
    let panel=document.querySelector('.fsNavPanel');
    if(!panel) return null;
    let title=panel.querySelector('.fsNavTitle');
    if(title) title.textContent='Bảng câu hỏi';
    let info=document.getElementById('navInfo');
    if(!info){
        info=document.createElement('div');
        info.id='navInfo';
        info.className='fsNavInfo';
        info.style.cssText='display:block!important;color:var(--muted)!important;font-size:11px;line-height:1.35;margin:2px 0 8px;padding:6px;border:1px solid var(--border);border-radius:8px;max-height:72px;overflow:auto';
        let nav=document.getElementById('navNums');
        if(nav) panel.insertBefore(info,nav);
    }
    return info;
}
function toggleFsNav(){
    if(!FULLDE_ON)return;
    FS_NAV_HIDDEN=!FS_NAV_HIDDEN;
    document.body.classList.toggle('fsnav-hidden',FS_NAV_HIDDEN);
    syncFsNavBtn();
    renderQuestion();
}
async function toggleQuizFullscreen(){let btn=document.getElementById('btnPresent');if(!FULLDE_ON){ensureFullModeOverrides();FULLDE_ON=true;FS_ANS_FORCE=null;FS_EXP_FORCE=null;FS_NAV_HIDDEN=false;MOBILE_QUIZ_TOOLS_OPEN=false;MOBILE_NAV_OPEN=false;document.body.classList.remove('fsnav-hidden');document.body.classList.add('fullde-mode');ensureFsNavBtn();syncFsNavBtn();updateAdminChrome();if(btn)btn.textContent='⤢ Thoát full đề';try{if(!document.fullscreenElement&&document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen()}catch(e){}syncMobileQuizChrome();renderQuestion();return}FULLDE_ON=false;FS_ANS_FORCE=null;FS_EXP_FORCE=null;FS_NAV_HIDDEN=false;MOBILE_QUIZ_TOOLS_OPEN=false;MOBILE_NAV_OPEN=false;document.body.classList.remove('fsnav-hidden');document.body.classList.remove('fullde-mode');syncFsNavBtn();updateAdminChrome();if(btn)btn.textContent='📽 Full màn hình';try{if(document.fullscreenElement&&document.exitFullscreen)await document.exitFullscreen()}catch(e){}syncMobileQuizChrome();renderQuestion()}
function canViewSolutionLive(){return !!(USER.is_admin||USER.can_view_solution_live===true||['ADMIN','VIP','S.VIP'].includes(String(USER.role||'').toUpperCase()))}
function hasAttemptedQuestion(qIdx){qIdx=(qIdx==null||qIdx===undefined)?CUR:qIdx;let q=applyResolvedDang(QUESTIONS[qIdx]);if(!q)return false;if(q.Dang==='Tự luận')return isQuestionDone(qIdx);return isQuestionChecked(qIdx)}
function canShowSolutionNow(){if(!canViewSolutionLive())return false;if(USER.is_admin)return true;return hasAttemptedQuestion(CUR)}
function canUseInfographicRole(){return !!(USER.is_admin||canViewSolutionLive())}
function isQuestionCorrect(qIdx){qIdx=(qIdx==null||qIdx===undefined)?CUR:qIdx;let r=SUBMITTED?RESULTS[qIdx]:(RESULTS[qIdx]||CHECKED[qIdx]);return !!(r&&r.ok===true)}
function canUnlockInfographic(qIdx){if(!canUseInfographicRole())return false;if(USER.is_admin)return true;return isQuestionCorrect(qIdx)}
function syncInfographicButtons(){let inQuiz=!!(document.getElementById('quiz')&&!document.getElementById('quiz').classList.contains('hide'));let roleOk=canUseInfographicRole()&&inQuiz;let ready=canUnlockInfographic(CUR);let lockTip='Trả lời đúng câu này mới mở khóa infographic.';for(let spec of [['btnFsInfographic',false],['btnInfographic',true]]){let b=document.getElementById(spec[0]);if(!b)continue;if(spec[1]&&!USER.is_admin){b.classList.add('hide');continue}b.classList.toggle('hide',!roleOk);if(!USER.is_admin||!spec[1]){b.disabled=!ready;b.title=ready?'Tạo prompt infographic chính xác từ Sheet':lockTip;b.classList.toggle('vipSolLocked',!ready)}else{b.disabled=false;b.title='Tạo prompt infographic (ADMIN — không cần làm bài)'}}}
function syncVipSolutionButtons(){let roleOk=canViewSolutionLive();let ready=canShowSolutionNow();let on=ready&&!!VIP_Q_SHOW_ANS[CUR],ex=ready&&!!VIP_Q_SHOW_EXP[CUR];let mobile=isMobileQuizUI();let lockTip='Làm và chấm câu này trước khi xem đáp án / lời giải.';let mv=document.getElementById('mobileDockVipBtns');if(mv)mv.classList.toggle('hide',!roleOk);let vt=document.getElementById('vipSolBtnsTop');if(vt)vt.classList.toggle('hide',!roleOk||mobile);for(let id of ['btnQuizShowAns','btnQuizShowExp']){let b=document.getElementById(id);if(b)b.classList.toggle('hide',!roleOk||mobile)}for(let id of ['btnFsShowAns','btnFsShowExp']){let b=document.getElementById(id);if(b)b.classList.toggle('hide',!roleOk||mobile)}for(let spec of [['btnMobileShowAns',on,'Ẩn ĐA','Đáp án'],['btnMobileShowExp',ex,'Ẩn LG','Lời giải'],['btnTopShowAns',on,'Ẩn ĐA','Đáp án'],['btnTopShowExp',ex,'Ẩn LG','Lời giải'],['btnQuizShowAns',on,'Ẩn ĐA','Đáp án'],['btnQuizShowExp',ex,'Ẩn LG','Lời giải'],['btnFsShowAns',on,'Ẩn ĐA','Đáp án'],['btnFsShowExp',ex,'Ẩn LG','Lời giải']]){let b=document.getElementById(spec[0]);if(!b)continue;b.classList.toggle('active',spec[1]);b.textContent=spec[1]?spec[2]:spec[3];if(!USER.is_admin){b.disabled=!ready;b.title=ready?(spec[1]?'Ẩn':'Xem/ẩn')+(spec[0].includes('Exp')?' lời giải':' đáp án'):lockTip;b.classList.toggle('vipSolLocked',!ready)}}}
function toggleQuestionAnswer(e){if(e&&e.stopPropagation)e.stopPropagation();if(!canViewSolutionLive()){alert('Chỉ VIP / SVIP / ADMIN được xem đáp án khi làm bài.');return}if(!canShowSolutionNow()){alert('Hãy làm và chấm câu này trước khi xem đáp án.');return}VIP_Q_SHOW_ANS[CUR]=!VIP_Q_SHOW_ANS[CUR];renderQuestion()}
function toggleQuestionExplain(e){if(e&&e.stopPropagation)e.stopPropagation();if(!canViewSolutionLive()){alert('Chỉ VIP / SVIP / ADMIN được xem lời giải khi làm bài.');return}if(!canShowSolutionNow()){alert('Hãy làm và chấm câu này trước khi xem lời giải.');return}VIP_Q_SHOW_EXP[CUR]=!VIP_Q_SHOW_EXP[CUR];renderQuestion()}
function toggleAnswerInFullscreen(){toggleQuestionAnswer()}
function toggleExplainInFullscreen(){toggleQuestionExplain()}
function formatDsAnswerLine(q,r){if(r&&r.correct_display)return formatDsAnswerBadges(r.correct_display);if(r&&Array.isArray(r.rows)&&r.rows.length)return formatDsAnswerBadges(r.rows.map(x=>`${x.letter}=${x.correct==='Đ'?'Đúng':'Sai'}`).join(' · '));if(q.Dang==='Đúng sai'){let bits=[];for(let i=0;i<4;i++){let L=['A','B','C','D'][i];if(!q[L])continue;let v=String(q.DapAn||'').replace(/\u0110/g,'D').replace(/đ/g,'d');let parsed=(v.match(/[DSĐ]/gi)||[]);let c=parsed[i];if(c)c=c.toUpperCase()==='S'?'Sai':(c==='Đ'||c==='D'?'Đúng':c);bits.push(`${L}=${c||'?'}`)}return formatDsAnswerBadges(bits.join(' · '))}return formatHintDisplay(r.correct||q.DapAn||'')}
function saveShortAnswer(doCheck){let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||USER.is_admin||q.Dang!='Trả lời ngắn')return;if(SUBMITTED)return;let el=document.getElementById('shortAnsInput');if(!el)return;ANSWERS[CUR]=el.value;if(doCheck){if(USER.is_trial){alert('Tài khoản dùng thử chỉ luyện đề, không chấm đúng/sai từng câu.');return}if(!String(ANSWERS[CUR]).trim()){alert('Hãy nhập đáp án trước khi kiểm tra.');return}checkCurrentQuestion()}renderNav();notifyDoneIfNeeded()}
function saveCurrent(){let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||USER.is_admin)return;if(LOCKED_Q[CUR]&&q.Dang!='Trả lời ngắn')return;if(q.Dang=='Trắc nghiệm'){let r=document.querySelector(`input[name="ans_${CUR}"]:checked`);if(r){ANSWERS[CUR]=r.value;LOCKED_Q[CUR]=true;checkCurrentQuestion()}}else if(q.Dang=='Đúng sai'){let arr=[];let req=0;for(let L of ['A','B','C','D']){if(q[L])req++;let r=document.querySelector(`input[name="tf_${CUR}_${L}"]:checked`);arr.push(r?r.value:'')}ANSWERS[CUR]=arr;let filled=arr.filter(v=>!!v).length;if(req>0&&filled>=req){LOCKED_Q[CUR]=true;checkCurrentQuestion()}}else if(q.Dang=='Trả lời ngắn'){saveShortAnswer(false)}else{let el=document.getElementById('essayAns');if(el)ANSWERS[CUR]=el.value}renderNav();notifyDoneIfNeeded()}
async function checkCurrentQuestion(){if(SUBMITTED)return;if(USER.is_trial){alert('Tài khoản dùng thử chỉ luyện đề, không chấm đúng/sai từng câu.');return}let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||q.Dang=='Tự luận')return;let ans=ANSWERS[CUR];if(ans==null)return;if(Array.isArray(ans)&&ans.every(v=>!v))return;if(String(ans).trim()==='')return;try{let j=await api('/api/check-one',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR,answer:ans,...quizRestorePayload()})});CHECKED[CUR]=j;RESULTS[CUR]=j;updateResultBox(CUR);renderQuestion()}catch(e){alert(e.message||'Không kiểm tra được câu này.')}}
function syncNavButtons(){let af=CUR<=0,al=CUR>=QUESTIONS.length-1;let p=document.getElementById('btnMobilePrev');if(p)p.disabled=af;let n=document.getElementById('btnMobileNext');if(n)n.disabled=al}
function renderNav(){let html='';for(let i=0;i<QUESTIONS.length;i++){let sec=quizSectionLabel(i);if(sec)html+=`<div class="navSectionLbl">${esc(sec)}</div>`;let cls='num';if(i==CUR)cls+=' active';if(ANSWERS[i]!=null&&String(ANSWERS[i]).length)cls+=' answered';if((SUBMITTED||CHECKED[i])&&RESULTS[i])cls+=RESULTS[i].ok?' ok':' bad';let tip=shortText((QUESTIONS[i]&&QUESTIONS[i].CauHoi)||'',120);html+=`<button class="${cls}" title="${escAttr(tip)}" onclick="goQ(${i})">${i+1}</button>`}let nav=document.getElementById('navNums');nav.innerHTML=html;if(FULLDE_ON){let active=nav.querySelector('.num.active');if(active&&active.scrollIntoView)active.scrollIntoView({block:'nearest',inline:'nearest'})}syncNavButtons()}function goQ(i){saveCurrent();CUR=i;renderQuestion()}function prevQ(){if(CUR>0){saveCurrent();CUR--;renderQuestion()}else{alert('Đang ở câu đầu tiên của đề.')}}function nextQ(){if(CUR<QUESTIONS.length-1){saveCurrent();CUR++;renderQuestion()}else{saveCurrent();alert('✅ Đã hết đề. Thầy/các em có thể xem lại rồi bấm Nộp bài.')}} 
function renderQuestion(){let q=applyResolvedDang(QUESTIONS[CUR]);if(q.Dang=='Trắc nghiệm'){let hasOpt=false;for(let L of ['A','B','C','D'])if(q[L])hasOpt=true;if(!hasOpt&&looksShortAnswerClient(q))q.Dang='Trả lời ngắn'}renderNav();let canAi=USER.can_ai_hint!==false;let hb=document.getElementById('hintBox');if(hb){if(HINT_LOADING&&HINT_LOADING_Q===CUR)showHintLoadingBox();else if(canAi&&(HINT_BY_Q[CUR]||SIMILAR_BY_Q[CUR])){hb.classList.remove('hintBoxLoading');renderHintBox(HINT_BY_Q[CUR]||{})}else if(canAi&&SIMILAR_LOADING&&SIMILAR_LOADING_Q===CUR){hb.classList.remove('hide');hb.classList.remove('hintBoxLoading');hb.innerHTML='<b>📝 Tạo câu tương tự</b><div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang gọi AI…</b><div class="muted" style="margin-top:6px;font-size:13px">Soạn câu mới cùng dạng, có đáp án và lời giải…</div></div></div>'}else{hb.classList.add('hide');hb.classList.remove('hintBoxLoading');hb.innerHTML=''}}let who=(USER.hoten||USER.mahs||'').trim();let prefix=who?`${who} | `:'';let idHtml=q.ID?`<button type="button" class="qidIdBadge" onclick="copyQuestionId()" title="Bấm để chép ID câu">ID: ${esc(q.ID)}</button>`:`<span class="qidIdBadge qidIdEmpty">ID: —</span>`;let solTag=q.has_full_solution?'<span class="tag solFullTag" style="font-size:11px;padding:2px 6px">📗 LG đầy đủ</span>':(q.sol_status==='partial'?'<span class="tag solPartTag" style="font-size:11px;padding:2px 6px">📝 LG một phần</span>':'');document.getElementById('qid').innerHTML=`${prefix?esc(prefix):''}Câu ${CUR+1}/${QUESTIONS.length} | ${idHtml} | ${formatMucDoBadges(q.MucDo)||'<span class="mucdoBadge mucdo-empty" title="Chưa ghi cột I">—</span>'} · <span class="qidDang">${esc(q.Dang||'')}</span>${solTag?' · '+solTag:''}`;let qImgHtml=q.HinhAnh?buildQimgHtml(q.HinhAnh):'';let splitImg=usesImgSplit(q);let splitTln=isTlnImgSplit(q);let secLbl=quizSectionLabel(CUR);let secHead=secLbl?`<div class="quizSectionHead">📂 Phần: ${esc(secLbl)}</div>`:'';let qtextEl=document.getElementById('qtext');if(splitTln){qtextEl.innerHTML=secHead;qtextEl.classList.toggle('hide',!secHead)}else{qtextEl.classList.remove('hide');qtextEl.innerHTML=secHead+renderRichText(stripImmini(q.CauHoi))+(splitImg?'':qImgHtml)};document.getElementById('btn5050').disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!USER.can_5050||LOCKED_Q[CUR];let bfs=document.getElementById('btnFs5050');if(bfs)bfs.disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!USER.can_5050||LOCKED_Q[CUR];document.getElementById('btnSubmit').style.display=(USER.is_admin||USER.is_trial)?'none':'';syncHintButtons(canAi);let html='';if(q.Dang=='Trắc nghiệm'){for(let L of ['A','B','C','D']){if(!q[L])continue;let checked=ANSWERS[CUR]==L?'checked':'';let cls='opt';let correct=(q.DapAn||'').toUpperCase().match(/[ABCD]/)?.[0]||'';if(USER.is_admin&&correct==L)cls+=' correct';let fb=RESULTS[CUR]||CHECKED[CUR];if((SUBMITTED||fb)&&fb){if(fb.correct==L||(fb.ok===true&&fb.chosen==L))cls+=' correct';if(fb.chosen==L&&fb.ok===false)cls+=' wrong'}html+=`<label id="opt_${L}" class="${cls}"><input type="radio" name="ans_${CUR}" value="${L}" ${checked} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()">${dsCircleHtml(L)}<span>${renderRichText(stripOptionPrefix(q[L],L))}</span></label>`}}else if(q.Dang=='Đúng sai'){let old=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:['','','',''];let crFb=RESULTS[CUR]||CHECKED[CUR];let rows=getDsCheckRows(q,crFb,old);let tfHead=`<div class="tfOptsHead"><span></span><span></span><span class="tfColHead"><span class="tfLblFull">Đúng · Sai</span><span class="tfLblShort">Đ<br>S</span></span></div>`;let tfRows='';for(let idx=0;idx<4;idx++){let L=['A','B','C','D'][idx];if(!q[L])continue;let cls='tfrow';let rr=rows.find(x=>x.letter===L);if(isQuestionChecked(CUR)&&rr){if(rr.ok===true)cls+=' correct';else if(rr.ok===false)cls+=' wrong'}tfRows+=`<div class="${cls}">${dsCircleHtml(L)}<div class="tfStmt">${renderRichText(q[L])}</div><div class="tfOpts"><label class="tfOpt tfD" title="Đúng"><input type="radio" name="tf_${CUR}_${L}" value="Đ" ${old[idx]=='Đ'?'checked':''} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()"><span class="tfLbl tfLblFull">Đúng</span><span class="tfLbl tfLblShort">Đ</span></label><label class="tfOpt tfS" title="Sai"><input type="radio" name="tf_${CUR}_${L}" value="S" ${old[idx]=='S'?'checked':''} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()"><span class="tfLbl tfLblFull">Sai</span><span class="tfLbl tfLblShort">S</span></label></div></div>`}html=tfHead+tfRows}else if(q.Dang=='Trả lời ngắn'){html=buildShortAnsHtml(q,{compact:true,withQuestion:splitTln})}else{html=`<div style="margin-top:10px"><label style="display:block;font-weight:800;margin-bottom:8px">✏️ Bài làm tự luận</label><textarea id="essayAns" style="width:100%;min-height:120px;padding:10px;border:1px solid var(--border);border-radius:8px" placeholder="Nhập bài làm tự luận..." ${SUBMITTED?'disabled':''} oninput="saveCurrent()">${esc(ANSWERS[CUR]||'')}</textarea></div>`}let optEl=document.getElementById('options');optEl.classList.toggle('mcqSplitWrap',splitImg);let splitCls='mcqSplit'+(q.Dang==='Đúng sai'?' mcqSplitDs':(splitTln?' mcqSplitTln':''));optEl.innerHTML=splitImg?`<div class="${splitCls}"><div class="mcqSplitImg">${qImgHtml}</div><div class="mcqSplitOpts">${html}</div></div>`:html;if(!canShowSolutionNow()){VIP_Q_SHOW_ANS[CUR]=false;VIP_Q_SHOW_EXP[CUR]=false}else if(USER.is_admin){VIP_Q_SHOW_ANS[CUR]=true;VIP_Q_SHOW_EXP[CUR]=true}let canShowAns=canShowSolutionNow(),canShowExp=canShowSolutionNow();let showAns=canShowAns&&!!VIP_Q_SHOW_ANS[CUR],showExp=canShowExp&&!!VIP_Q_SHOW_EXP[CUR];let showBox=showAns||showExp;document.getElementById('solution').classList.toggle('hide',!showBox);if(showBox){let r=RESULTS[CUR]||{};let parts=[];if(showAns){let ansLine=q.Dang==='Đúng sai'?formatDsAnswerLine(q,null):(q.Dang==='Trắc nghiệm'?formatMcqAnswerBadge(q.DapAn||''):renderRichText(q.DapAn||''));parts.push(`<b>Đáp án:</b> ${ansLine}`)}if(showExp){let lg=q.LoiGiai||r.LoiGiai||'Chưa có lời giải.';parts.push(`<b>Lời giải:</b><br>${q.Dang==='Đúng sai'?formatDsSolutionRows(lg,q):(q.Dang==='Trắc nghiệm'?formatMcqSolutionRows(lg,q):formatHintDisplay(lg))}`)};document.getElementById('solution').innerHTML=parts.join('<br>')}typesetQuizMath();syncMobileQuizToolbar();syncVipSolutionButtons();syncInfographicButtons();updateResultBox(CUR)}
async function use5050(){saveCurrent();try{let j=await api('/api/fifty',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR,...quizRestorePayload()})});for(let L of j.hide||[]){let el=document.getElementById('opt_'+L);if(el)el.classList.add('hidden5050')}document.getElementById('btn5050').disabled=true;let bfs=document.getElementById('btnFs5050');if(bfs)bfs.disabled=true;let msg=`50-50: đã loại ${((j.hide||[]).join(', ')||'2 đáp án sai')}`;document.getElementById('resultBox').textContent=msg;document.getElementById('resultBox').style.color='#1d4ed8';if(j.message&&!String(j.message).toLowerCase().includes('đã loại'))alert(j.message)}catch(e){alert(e.message)}}
function hintButtonLabel(){return USER.is_admin?'🔍 AI kiểm tra':(USER.is_vip?'💡 AI':'💡 Gợi ý AI')}
function syncHintButtons(canAi){let lbl=hintButtonLabel();for(let id of ['btnHint','btnFsHint']){let b=document.getElementById(id);if(!b)continue;b.classList.toggle('hide',!canAi);if(HINT_LOADING)continue;b.classList.remove('btnHintLoading');b.textContent=lbl;b.disabled=!canAi||SIMILAR_LOADING}for(let id of ['btnSimilar','btnFsSimilar']){let b=document.getElementById(id);if(!b)continue;b.classList.toggle('hide',!canAi||!!USER.is_admin);if(SIMILAR_LOADING&&SIMILAR_LOADING_Q===CUR){b.disabled=true;b.textContent='⏳ Đang tạo…'}else{b.disabled=HINT_LOADING;b.textContent=id==='btnFsSimilar'?'📝 tương tự':'📝 Tạo câu tương tự'}}}
function setHintLoading(on,qIndex){HINT_LOADING=!!on;HINT_LOADING_Q=on?qIndex:null;let lbl=hintButtonLabel();for(let id of ['btnHint','btnFsHint']){let b=document.getElementById(id);if(!b)continue;if(on){if(!b.dataset.hintLabel)b.dataset.hintLabel=b.textContent||lbl;b.disabled=true;b.classList.add('btnHintLoading');b.innerHTML='<span class="hintSpin"></span> AI đang xử lý…'}else{b.classList.remove('btnHintLoading');b.textContent=b.dataset.hintLabel||lbl;delete b.dataset.hintLabel;b.disabled=SIMILAR_LOADING}}syncHintButtons(USER.can_ai_hint!==false)}
function setSimilarLoading(on,qIndex){SIMILAR_LOADING=!!on;SIMILAR_LOADING_Q=on?qIndex:null;syncHintButtons(USER.can_ai_hint!==false)}
function adminHintNeedsSave(qIdx){qIdx=qIdx==null?CUR:qIdx;let j=HINT_BY_Q[qIdx];return !!(j&&j.admin_review&&!ADMIN_HINT_SAVED[qIdx])}
function markAdminHintSaved(qIdx){qIdx=qIdx==null?CUR:qIdx;ADMIN_HINT_SAVED[qIdx]=true;if(HINT_BY_Q[qIdx])HINT_BY_Q[qIdx].admin_sheet_confirmed=true}
function dsDapAnFromSolutionText(text,q){q=q||currentQuestion();let chunks=extractAbcdSolutionChunks(String(text||''));let m={};chunks.forEach(c=>{if(c.verdict)m[c.letter]=c.verdict});let letters=['A','B','C','D'].filter(L=>q[L]);let bits=letters.filter(L=>m[L]).map(L=>`${L}=${m[L]}`);return bits.length?bits.join(' · '):''}
function hintSection1Raw(){let t=hintRawText().split('📋 Tham chiếu Sheet')[0];let m=t.match(/1\.\s*GIẢI TỪNG Ý[^\n]*\n([\s\S]*?)(?=2\.\s*CHỐT ĐÁP ÁN|\Z)/i);return m?m[1].trim():''}
function hintLoigiaiFromHintBody(){let t=hintRawText();let m=t.match(/Lời giải Sheet \(cột R\):\s*\n([\s\S]*?)(?=\n\n📋 Tham chiếu Sheet|$)/i);return m?m[1].trim():''}
function hintAiLoigiaiRaw(){let j=HINT_BY_Q[CUR]||{};let q=QUESTIONS[CUR]||{};let cand=[String(j.suggested_loigiai||'').trim(),hintSection1Raw(),hintLoigiaiFromHintBody(),String(j.sheet_loigiai||'').trim(),String(q.LoiGiai||'').trim()].filter(Boolean);cand.sort((a,b)=>b.length-a.length);return cand[0]||''}
function hintAiDapAn(){if(isCurrentQuestionDs()){let fromLg=dsDapAnFromSolutionText(hintAiLoigiaiRaw(),currentQuestion());if(fromLg)return fromLg}let j=HINT_BY_Q[CUR]||{};return String(j.suggested_dapan||'').trim()}
function hintAiLoigiai(){let v=hintAiLoigiaiRaw();return v?stripLoigiaiMarkdown(v).replace(/\r/g,''):''}
function adminLoigiaiMissingLetters(text,q){q=q||currentQuestion();if(!q||q.Dang!=='Đúng sai')return [];let need=['A','B','C','D'].filter(L=>!!q[L]);let found=new Set();String(text||'').split(/\n/).forEach(line=>{let m=line.match(/^\s*([ABCD])\s*[\.\):]/i);if(m)found.add(m[1].toUpperCase())});return need.filter(L=>!found.has(L))}
function buildAdminAnalysisCard(j){if(!j||!j.admin_review)return '';let a=j.admin_analysis;if(!a)return '';let head=a.all_ok?`<div class="adminAnalysisOk">${esc(a.summary||'Sheet khớp AI')}</div>`:`<div class="adminAnalysisWarn">${esc(a.summary||'Có điểm cần sửa')}</div>`;let table='';if(a.rows&&a.rows.length){let trs=a.rows.map(r=>{let cls=r.ok?'adminAnalysisOkRow':'adminAnalysisBadRow';let mark=r.ok?'✓':'✗';let note=r.note?`<div class="muted" style="font-size:11px;margin-top:2px">${esc(r.note)}</div>`:'';return `<tr class="${cls}"><td><b>${esc(r.letter)}</b></td><td>${esc(r.sheet_p||'—')}</td><td>${esc(r.ai||'—')}</td><td>${esc(r.sheet_r||'—')}</td><td>${mark}${note}</td></tr>`}).join('');table=`<table class="adminAnalysisTbl"><thead><tr><th>Ý</th><th>Sheet P</th><th>AI</th><th>Sheet R</th><th></th></tr></thead><tbody>${trs}</tbody></table>`}let fixes='';if(!a.all_ok&&(a.fix_dapan||a.fix_loigiai))fixes=`<div class="hintAiActions" style="margin-top:8px"><button type="button" class="btnGreen" onclick="applyAdminFixAll()">✏️ Sửa Sheet (điền gợi ý AI)</button></div>`;else if(a.all_ok&&adminHintNeedsSave())fixes=`<div class="muted" style="margin-top:8px;font-size:12px">Sheet đã khớp AI — vẫn có thể bấm <b>Lưu</b> nếu vừa chỉnh tay.</div>`;return `<div class="hintAnswerCard adminAnalysisCard"><div class="hintAnswerTitle">🔬 Phân tích Đúng/Sai (ADMIN)</div>${head}${table}${fixes}</div>`}
function applyAdminFixAll(){if(!USER.is_admin)return;let j=HINT_BY_Q[CUR]||{};let a=j.admin_analysis||{};openEditWithHint(String(a.fix_dapan||'').trim(),String(a.fix_loigiai||'').trim())}
function buildHintAnswerCard(j){if(!j)return '';if(!j.show_answer&&!j.vip_detailed&&!j.exact&&!j.admin_review)return '';if(j.admin_review&&adminHintNeedsSave())return `<div class="hintAnswerCard hintAnswerPending"><div class="hintAnswerTitle">📋 Đề xuất lưu Sheet</div><div class="muted" style="font-size:13px;line-height:1.45;margin-top:6px">Xem bảng phân tích phía trên → <b>✏️ Sửa Sheet (điền gợi ý AI)</b> → kiểm tra <b>P + R</b> → <b>Lưu vào Google Sheet</b>.</div></div>`;if((j.vip_detailed||j.show_answer)&&!j.admin_review&&!USER.is_admin&&!canShowSolutionNow())return `<div class="hintAnswerCard hintAnswerPending"><div class="hintAnswerTitle">🔒 Chưa làm câu</div><div class="muted" style="font-size:13px;line-height:1.45;margin-top:6px">VIP/SVIP: chọn đáp án và <b>chấm câu này</b> (TN/ĐS tự chấm; TLN bấm ✓) trước khi xem <b>Đáp án</b> và <b>Lời giải</b> từ Sheet.</div></div>`;let q=currentQuestion();let aiDa=String(j.suggested_dapan||j.correct||'').trim();let sheetDa=String(j.sheet_dapan||'').trim();let aiLg=String(j.suggested_loigiai||'').trim();let sheetLg=String(j.sheet_loigiai||'').trim();if(j.admin_review&&isCurrentQuestionDs()){let daFromLg=dsDapAnFromSolutionText(aiLg||hintSection1Raw(),q);if(daFromLg)aiDa=daFromLg}if(!sheetDa&&q)sheetDa=String(q.DapAn||'').trim();if(!sheetLg&&q)sheetLg=String(q.LoiGiai||'').trim();if(j.admin_review&&ADMIN_HINT_SAVED[CUR]){sheetDa=String(q.DapAn||sheetDa||'').trim();sheetLg=String(q.LoiGiai||sheetLg||'').trim()}if(!aiDa&&sheetDa)aiDa=sheetDa;if(!aiLg&&sheetLg)aiLg=sheetLg;if(!aiDa&&!sheetDa&&!aiLg&&!sheetLg)return '';let isDs=isCurrentQuestionDs();let isTn=isCurrentQuestionTn();let vipShort=!!(j.vip_detailed&&!j.admin_review);function fmtAns(t){if(isDs)return formatDsHintText(t,false);if(isTn)return formatTnHintText(t,false);return formatHintDisplay(t)}function fmtSol(t,fromAi){if(vipShort)return formatHintDisplay(t);if(isDs)return formatDsHintText(t,true,fromAi);if(isTn)return formatTnHintText(t,true);return formatHintDisplay(t)}let rows='';if(sheetDa||aiDa){rows+=`<div class="hintAnswerRow"><b>📌 Đáp án:</b> <span class="hintMath hintAnswerMain">${fmtAns(sheetDa||aiDa)}</span></div>`;if(j.admin_review&&sheetDa&&aiDa&&sheetDa.replace(/\s/g,'')!==aiDa.replace(/\s/g,''))rows+=`<div class="hintAnswerRow muted" style="font-size:13px"><b>Sheet (P):</b> <span class="hintMath">${fmtAns(sheetDa)}</span> · <b>AI đề xuất:</b> <span class="hintMath">${fmtAns(aiDa)}</span></div>`;else if(j.admin_review&&sheetDa&&aiDa&&sheetDa.replace(/\s/g,'')===aiDa.replace(/\s/g,''))rows+=`<div class="hintAnswerRow" style="font-size:13px;color:#166534"><b>✓ Đáp án Sheet khớp AI</b></div>`}let aiLgRaw=j.admin_review?hintAiLoigiaiRaw():'';let lgShow=j.admin_review?(adminHintNeedsSave()?aiLgRaw:(sheetLg||String(q.LoiGiai||''))):(sheetLg||aiLg);if(lgShow){let lgLabel=j.admin_review?(adminHintNeedsSave()?'📝 Lời giải AI (mục 1):':'📝 Lời giải (Sheet R):'):(vipShort?'📝 Phương hướng:':'📝 Lời giải:');rows+=`<div class="hintAnswerRow" style="margin-top:8px"><b>${lgLabel}</b> <span class="hintMath">${fmtSol(lgShow,j.admin_review&&adminHintNeedsSave())}</span></div>`;if(j.admin_review&&adminHintNeedsSave()&&sheetLg&&aiLgRaw&&sheetLg.trim()!==aiLgRaw.trim())rows+=`<div class="hintAnswerRow muted" style="font-size:13px"><b>Sheet (R) hiện tại:</b> <span class="hintMath">${fmtSol(sheetLg,false)}</span></div>`;else if(j.admin_review&&!adminHintNeedsSave()&&aiLgRaw&&sheetLg&&sheetLg.trim()!==aiLgRaw.trim())rows+=`<div class="hintAnswerRow muted" style="font-size:13px"><b>AI đề xuất (mục 1):</b> <span class="hintMath">${fmtSol(aiLgRaw,true)}</span></div>`}if(!rows)return '';let cardTitle=j.admin_review?'✅ Đã lưu Sheet — so khớp P/R với AI':(vipShort?'✅ Kết quả &amp; phương hướng':'✅ Đáp án &amp; lời giải — so sánh ôn tập');return `<div class="hintAnswerCard"><div class="hintAnswerTitle">${cardTitle}</div>${rows}</div>`}
function buildSheetPreviewCard(){if(!canViewSolutionLive()||USER.is_admin||!canShowSolutionNow())return '';let q=currentQuestion();if(!q)return '';return buildHintAnswerCard({show_answer:true,vip_detailed:true,sheet_dapan:q.DapAn||'',sheet_loigiai:q.LoiGiai||'',suggested_dapan:q.DapAn||'',suggested_loigiai:q.LoiGiai||''})}
function buildHintSimilarSection(){if(!USER.can_ai_hint||USER.is_admin)return '';let sim=SIMILAR_BY_Q[CUR];let loading=SIMILAR_LOADING&&SIMILAR_LOADING_Q===CUR;let html=`<div class="hintAiActions"><button type="button" class="btn2" id="btnSimilarInline" onclick="requestSimilarQuestion()" ${loading?'disabled':''}>${loading?'⏳ Đang tạo câu tương tự…':'📝 Tạo câu tương tự'}</button></div>`;if(sim&&sim.similar)html+=`<div class="hintSimilarBox" id="hintSimilarBox"><div class="hintSimilarTitle">📝 Câu tương tự (AI)</div><div class="hintSimilarBody hintMath" id="hintSimilarBody">${formatHintDisplay(sim.similar)}</div></div>`;return html}
function showHintLoadingBox(){let hb=document.getElementById('hintBox');if(!hb)return;hb.classList.remove('hide');hb.classList.add('hintBoxLoading');let title=USER.is_admin?'🔍 AI kiểm tra (ADMIN):':(USER.is_vip?'💡 AI VIP + đáp án:':'💡 Gợi ý AI:');let sub=USER.is_admin?'Phân tích Đúng/Sai từng ý A–D, so Sheet P/R, gợi ý sửa — thường 20–60 giây…':(USER.is_vip?'Gemini: phương hướng + kết quả cuối — thường 10–25 giây…':'Đang phân tích câu hỏi…');let preview=(USER.is_admin?'':((USER.is_vip||USER.can_view_solution_live)?buildSheetPreviewCard():''));hb.innerHTML=`<b>${title}</b>${preview}<div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang gọi AI…</b><div class="muted" style="margin-top:6px;font-size:13px;line-height:1.45">${esc(sub)}</div></div></div>`;if(preview)typesetQuizMath()}
function renderHintBox(j){let hb=document.getElementById('hintBox');if(!hb)return;j=j||{};hb.classList.remove('hide');hb.classList.remove('hintBoxLoading');let title=j.admin_review?'🔍 AI kiểm tra (ADMIN):':(j.vip_detailed?'💡 AI VIP:':'💡 Gợi ý AI:');if(!j.hint&&!j.admin_review&&!j.vip_detailed&&SIMILAR_BY_Q[CUR])title='📝 Câu tương tự (AI)';let extra='';if(j.admin_review){extra=`<div class="muted" style="margin-top:6px;font-size:12px">ADMIN: bảng <b>Phân tích Đúng/Sai</b> so Sheet P/R với AI → <b>Sửa Sheet</b> nếu lệch → <b>Lưu</b></div>`;if(j.key_index)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">AI: ${esc(j.provider_used||'')} | key #${j.key_index}</div>`;else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Cần GEMINI_API_KEY trên Render</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ AI lỗi/quota — vẫn chép được lời giải Sheet/AI bên dưới vào cột R qua <b>Sửa câu</b>.</div>`;if(j.hint_truncated)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ AI có thể chưa đủ 2 bước — bấm lại <b>AI kiểm tra</b> hoặc thử GEMINI_ADMIN_MODEL trên Render.</div>`;extra+=`<div class="hintAdminActions"><button type="button" class="btnGreen" onclick="openEditWithHint()">✏️ Sửa câu (điền AI)</button><button type="button" class="btn2" onclick="copyHintLoigiai()">📋 Chép lời giải</button><button type="button" class="btn2" onclick="copyHintAll()">📋 Chép toàn bộ</button><button type="button" class="btn2" onclick="applyHintField('DapAn')">→ Chỉ đáp án (P)</button><button type="button" class="btn2" onclick="applyHintField('LoiGiai')">→ Chỉ lời giải (R)</button><button type="button" class="btn2" onclick="openInfographicPrompt()">📊 Prompt infographic</button></div>`}else if(j.vip_detailed){extra=`<div class="muted" style="margin-top:6px;font-size:12px">VIP/SVIP: phương hướng ngắn + kết quả cuối (không giải từng A/B/C/D).</div>`;if(j.key_index)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">AI: ${esc(j.provider_used||'')} | key #${j.key_index}</div>`;else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Chưa có key — nạp tại 🔑 Key AI của tôi</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`;if(j.hint_truncated)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ AI có thể chưa đủ mục — bấm lại <b>Gợi ý AI</b>.</div>`;if(j.hide_5050&&j.hide_5050.length)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">Đã loại: ${esc(j.hide_5050.join(', '))}</div>`;if(canUnlockInfographic(CUR))extra+=`<div class="hintAiActions"><button type="button" class="btn2" onclick="openInfographicPrompt()">📊 Prompt infographic</button></div>`}else if(j.vip_formula_only){extra=`<div class="muted" style="margin-top:6px;font-size:12px">VIP: công thức đã thay số từ đề + tự loại 2 đáp án sai (trắc nghiệm)</div>`;if(j.hide_5050&&j.hide_5050.length)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">Đã loại: ${esc(j.hide_5050.join(', '))}</div>`;if(j.provider_used==='FALLBACK')extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">AI lỗi hoặc chưa có key — <a href="#" onclick="backHome();return false">🔑 Key AI của tôi</a></div>`;else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Chưa có key — nạp tại 🔑 Key AI của tôi</div>`}else if(j.key_index){extra=`<div class="muted" style="margin-top:6px;font-size:12px">AI: ${esc(j.provider_used||'')} | key #${j.key_index}</div>`}else if(j.hint){extra=`<div class="muted" style="margin-top:6px;font-size:12px">AI fallback${j.ai_configured?' (key lỗi hoặc hết quota)':' (chưa có key)'}</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`}if(j.message)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">${esc(j.message)}</div>`;let analysisCard=j.admin_review?buildAdminAnalysisCard(j):'';let answerCard=buildHintAnswerCard(j);let similarSec=buildHintSimilarSection();let body=j.hint?formatHintDisplay(j.hint):'';let bodyHtml=body?`<div id="hintAdminBody" class="hintAdminBody">${body}</div>`:'';hb.innerHTML=`<b>${title}</b>${analysisCard}${answerCard}${extra}${bodyHtml}${similarSec}`;typesetQuizMath()}
function copyHintLoigiai(){let t=hintFieldValue('LoiGiai');if(!t){alert('Chưa có lời giải đề xuất (mục 1).');return}navigator.clipboard.writeText(t).then(()=>alert('Đã chép lời giải (đúng mẫu A. Đúng — …).')).catch(()=>alert('Không chép được — thử bấm → Lời giải (R) rồi Ctrl+C.'))}
function copyHintAll(){let t=hintRawText();if(!t){alert('Chưa có nội dung.');return}navigator.clipboard.writeText(t).then(()=>alert('Đã chép vào clipboard (text gốc có $...$).')).catch(()=>{let el=document.getElementById('hintAdminBody');if(el){let r=document.createRange();r.selectNodeContents(el);let sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);try{document.execCommand('copy');alert('Đã chép vùng hiển thị (Ctrl+C).')}catch(e){alert('Chọn text trong ô gợi ý rồi Ctrl+C.')}}})}
function hintFieldValue(field){let j=HINT_BY_Q[CUR]||{};let a=j.admin_analysis||{};if(field==='DapAn')return String(a.fix_dapan||'').trim()||hintAiDapAn();if(field==='LoiGiai')return String(a.fix_loigiai||'').trim()||hintAiLoigiai();return ''}
function applyHintField(field){if(!USER.is_admin){alert('Chỉ ADMIN.');return}let v=hintFieldValue(field);if(!v){alert(field==='DapAn'?'Chưa tách được đáp án AI (mục 2).':'Chưa có lời giải đề xuất (mục 1).');return}openEditWithHint(field==='DapAn'?v:'',field==='LoiGiai'?v:'')}
function openEditWithHint(dapan='',loigiai=''){let j=HINT_BY_Q[CUR]||{};let a=j.admin_analysis||{};if(!dapan)dapan=String(a.fix_dapan||'').trim()||hintAiDapAn();if(!loigiai)loigiai=String(a.fix_loigiai||'').trim()||hintAiLoigiai();if(isCurrentQuestionDs()&&loigiai){let sync=dsDapAnFromSolutionText(loigiai,QUESTIONS[CUR]);if(sync)dapan=sync}openEdit();syncQuestionModalChrome();if(dapan){let el=document.getElementById('edit_DapAn');if(el)el.value=dapan}if(loigiai){let el=document.getElementById('edit_LoiGiai');if(el)el.value=loigiai}}
async function saveHintField(field){alert('ADMIN: hãy bấm ✏️ Sửa câu (điền AI), kiểm tra đủ Đáp án + Lời giải, rồi Lưu vào Google Sheet — không lưu thẳng từ AI.')}
async function requestSimilarQuestion(){if(!USER.can_ai_hint){alert('Tạo câu tương tự chỉ dành tài khoản VIP / SVIP / ADMIN.');return}if(SIMILAR_LOADING||HINT_LOADING)return;saveCurrent();let qIdx=CUR;setSimilarLoading(true,qIdx);if(HINT_BY_Q[qIdx])renderHintBox(HINT_BY_Q[qIdx]);else{let hb=document.getElementById('hintBox');if(hb){hb.classList.remove('hide');hb.innerHTML='<b>📝 Tạo câu tương tự</b><div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang gọi AI…</b></div></div>'}}try{let j=await api('/api/hint/similar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:qIdx,...quizRestorePayload()})});SIMILAR_BY_Q[qIdx]=j;if(CUR===qIdx)renderHintBox(HINT_BY_Q[qIdx]||{});let hb=document.getElementById('hintBox');if(hb&&!hb.classList.contains('hide'))hb.scrollIntoView({behavior:'smooth',block:'nearest'})}catch(e){alert('Không tạo được câu tương tự: '+e.message)}finally{if(SIMILAR_LOADING_Q===qIdx){setSimilarLoading(false);if(CUR===qIdx&&(HINT_BY_Q[qIdx]||SIMILAR_BY_Q[qIdx]))renderHintBox(HINT_BY_Q[qIdx]||{})}}}
async function requestHint(){if(!USER.can_ai_hint){alert('Gợi ý AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}if(HINT_LOADING||SIMILAR_LOADING){return}saveCurrent();let qIdx=CUR;setHintLoading(true,qIdx);showHintLoadingBox();let rb=document.getElementById('resultBox');if(rb){rb.textContent='⏳ AI đang làm…';rb.style.color='#1d4ed8'}try{let ans=ANSWERS[qIdx];let j=await api('/api/hint',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:qIdx,answer:ans,...quizRestorePayload()})});HINT_BY_Q[qIdx]=j;if(j.admin_review)ADMIN_HINT_SAVED[qIdx]=false;if(CUR===qIdx){renderHintBox(j);if(j.hide_5050&&j.hide_5050.length)applyAuto5050(j.hide_5050);let hb=document.getElementById('hintBox');if(hb&&!hb.classList.contains('hide')){hb.scrollIntoView({behavior:'smooth',block:'nearest'})}}else if(HINT_LOADING_Q===qIdx){let hb=document.getElementById('hintBox');if(hb){hb.classList.add('hide');hb.classList.remove('hintBoxLoading');hb.innerHTML=''}}}catch(e){if(CUR===qIdx){let hb=document.getElementById('hintBox');if(hb){hb.classList.remove('hintBoxLoading');hb.classList.remove('hide');hb.innerHTML='<b>❌ Không lấy được gợi ý AI</b><div class="muted" style="margin-top:8px">'+esc(e.message)+'</div>'}}alert('Không lấy được gợi ý: '+e.message)}finally{if(HINT_LOADING_Q===qIdx){setHintLoading(false);syncHintButtons(USER.can_ai_hint!==false)}if(CUR===qIdx&&rb){if(USER.is_admin)rb.textContent='ADMIN: đang xem đáp án/lời giải';else if(USER.is_trial)rb.textContent='DÙNG THỬ: chỉ luyện đề FREE, không chấm điểm';else rb.textContent=''}}}
async function submitQuiz(){if(USER.is_trial){alert('Tài khoản dùng thử không được nộp/chấm điểm.');return;}saveCurrent();if(!confirm('Nộp bài?'))return;let j=await api('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,answers:ANSWERS,...quizRestorePayload()})});SUBMITTED=true;stopQuizTimer();RESULTS={};for(let r of j.results)RESULTS[r.index]=r;document.getElementById('resultBox').textContent=`Điểm: ${j.score}/10 | Đúng ${j.correct_count}/${j.auto_count} | ⏱ ${fmtTime(QUIZ_ELAPSED)}`;renderQuestion();renderNav()}
const QUESTION_FORM_FIELDS=['MaDe','ID','Mon','Lop','Chuong','BaiHoc','QuyenTruyCap','MucDo','Dang','CauHoi','A','B','C','D','DapAn','SaiSo','LoiGiai','HinhAnh'];
const QUESTION_FORM_LABELS={MaDe:'Mã đề (MaDe)',ID:'ID câu (để trống = tự tạo)',Mon:'Môn',Lop:'Lớp',Chuong:'Chương',BaiHoc:'Bài học',QuyenTruyCap:'Quyền (FREE/VIP)',MucDo:'Mức độ - cột I',Dang:'Dạng - cột J',CauHoi:'Câu hỏi / Nội dung - cột K',DapAn:'Đáp án - cột P',SaiSo:'Sai số - cột Q',LoiGiai:'Lời giải - cột R',HinhAnh:'Hình ảnh - cột T',A:'A - cột L',B:'B - cột M',C:'C - cột N',D:'D - cột O'};
const ADMIN_MUCDO_OPTS=['NB','TH','VD','VDC'];
const ADMIN_DANG_OPTS=['Trắc nghiệm','Đúng sai','Trả lời ngắn','Tự luận'];
const ADMIN_QUYEN_OPTS=[{v:'FREE',l:'FREE',cls:'adminChipFree'},{v:'VIP',l:'VIP',cls:'adminChipVip'}];
function normQuyenFormVal(s){let t=normText(s);if(!t)return'FREE';if(/vip|paid|premium|co phi|tra phi|thu phi|svip/.test(t))return'VIP';return'FREE'}
function normMucDoFormVal(s){let u=String(s||'').trim().toUpperCase();if(ADMIN_MUCDO_OPTS.includes(u))return u;if(/\bNB\b/.test(u))return'NB';if(/\bTH\b/.test(u))return'TH';if(/\bVDC\b/.test(u))return'VDC';if(/\bVD\b/.test(u))return'VD';return''}
function normDangFormVal(s){let d=normDangClient(s);if(ADMIN_DANG_OPTS.includes(d))return d;return d||'Trắc nghiệm'}
function escFormVal(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}
function setAdminChip(field,value){let el=document.getElementById('edit_'+field);if(el)el.value=value;syncAdminChipGroup(field)}
function syncAdminChipGroup(field){let el=document.getElementById('edit_'+field);let val=el?String(el.value||''):'';document.querySelectorAll('[data-chip-field="'+field+'"]').forEach(btn=>{btn.classList.toggle('adminChipOn',btn.getAttribute('data-chip-value')===val)})}
function renderAdminChipGroup(field,options,current,normFn){let cur=normFn?normFn(current):String(current||'');let chips='';for(let opt of options){let v=typeof opt==='string'?opt:opt.v;let lab=typeof opt==='string'?opt:opt.l;let cls=typeof opt==='string'?(field==='MucDo'?mucdoBadgeClass(v):''):(opt.cls||'');let on=cur===v?' adminChipOn':'';chips+=`<button type="button" class="adminChip ${cls}${on}" data-chip-field="${field}" data-chip-value="${escAttr(v)}" onclick="setAdminChip('${field}','${escAttr(v)}')">${esc(lab)}</button>`}return `<div class="adminQuickField"><label><b>${QUESTION_FORM_LABELS[field]||field}</b></label><input type="hidden" id="edit_${field}" value="${escAttr(cur)}"><div class="adminChipRow">${chips}</div></div>`}
function renderQuestionFormField(f,q){let raw=String((q&&q[f])||'');if(f==='QuyenTruyCap')return renderAdminChipGroup(f,ADMIN_QUYEN_OPTS,raw,normQuyenFormVal);if(f==='MucDo'){let chips=ADMIN_MUCDO_OPTS.map(v=>{let on=normMucDoFormVal(raw)===v?' adminChipOn':'';return `<button type="button" class="adminChip ${mucdoBadgeClass(v)}${on}" data-chip-field="MucDo" data-chip-value="${v}" onclick="setAdminChip('MucDo','${v}')">${v}</button>`}).join('');let cur=normMucDoFormVal(raw);return `<div class="adminQuickField"><label><b>${QUESTION_FORM_LABELS.MucDo}</b></label><input type="hidden" id="edit_MucDo" value="${escAttr(cur)}"><div class="adminChipRow">${chips}<button type="button" class="adminChip${cur?'':' adminChipOn'}" data-chip-field="MucDo" data-chip-value="" onclick="setAdminChip('MucDo','')">—</button></div></div>`}if(f==='Dang')return renderAdminChipGroup(f,ADMIN_DANG_OPTS,raw,normDangFormVal);let h=(f=='CauHoi'||f=='LoiGiai')?'150px':((f=='MaDe'||f=='ID'||f=='Mon'||f=='Lop'||f=='Chuong'||f=='BaiHoc'||f=='DapAn'||f=='SaiSo'||f=='HinhAnh')?'56px':'78px');return `<div><label><b>${QUESTION_FORM_LABELS[f]||f}</b></label><textarea style="min-height:${h}" id="edit_${f}">${escFormVal(raw)}</textarea></div>`}
function renderQuestionForm(q){document.getElementById('editForm').innerHTML=QUESTION_FORM_FIELDS.map(f=>renderQuestionFormField(f,q)).join('');['QuyenTruyCap','MucDo','Dang'].forEach(syncAdminChipGroup)}
function readQuestionFormData(){let data={};for(let f of QUESTION_FORM_FIELDS){let el=document.getElementById('edit_'+f);data[f]=el?(el.value||''):''}return data}
function syncQuestionModalChrome(){let isAdd=QUESTION_MODAL_MODE==='add';let t=document.getElementById('editModalTitle');if(t)t.textContent=isAdd?'ADMIN: Thêm câu hỏi mới':'ADMIN: Sửa câu hỏi';let del=document.getElementById('btnDeleteQuestion');if(del)del.classList.toggle('hide',isAdd);let save=document.getElementById('btnSaveQuestion');if(save)save.textContent=isAdd?'➕ Thêm vào Google Sheet':'✅ Lưu vào Google Sheet (sau khi kiểm tra)';let note=document.getElementById('editModalNote');if(note){if(isAdd)note.textContent='Câu mới được thêm vào cuối sheet Cau_Hoi, cùng mã đề/bài học với câu hiện tại (có thể sửa trước khi lưu).';else if(adminHintNeedsSave())note.textContent='Kiểm tra đủ Đáp án (cột P) và Lời giải (cột R). Câu Đ/S: phải có đủ 4 dòng A. B. C. D. Xong mới bấm Lưu — sau đó app mới so khớp Sheet với AI.';else note.textContent='Xóa liên tiếp được — app tự cập nhật số dòng Sheet. Chỉ bấm Đồng bộ khi sửa trực tiếp trên Google Sheet.'}}
function openEdit(){if(!USER.is_admin){alert('Chỉ ADMIN.');return}QUESTION_MODAL_MODE='edit';renderQuestionForm(QUESTIONS[CUR]||{});syncQuestionModalChrome();document.getElementById('modal').classList.remove('hide')}
function openAddQuestion(){if(!USER.is_admin){alert('Chỉ ADMIN.');return}if(!QUESTIONS.length){alert('Hãy mở một đề trước khi thêm câu.');return}QUESTION_MODAL_MODE='add';let tpl=QUESTIONS[CUR]||{};let seed={MaDe:tpl.MaDe||CURRENT_MADE||'',Mon:tpl.Mon||'',Lop:tpl.Lop||'',Chuong:tpl.Chuong||'',BaiHoc:tpl.BaiHoc||tpl.De||'',QuyenTruyCap:tpl.QuyenTruyCap||'VIP',MucDo:tpl.MucDo||'',Dang:tpl.Dang||'Trắc nghiệm',CauHoi:'',A:'',B:'',C:'',D:'',DapAn:'',SaiSo:'',LoiGiai:'',HinhAnh:'',ID:''};renderQuestionForm(seed);syncQuestionModalChrome();document.getElementById('modal').classList.remove('hide')}
function closeEdit(){document.getElementById('modal').classList.add('hide')}
function closeInfographicModal(){let m=document.getElementById('infographicModal');if(m)m.classList.add('hide')}
async function openInfographicPrompt(){if(!canUseInfographicRole()){alert('Infographic chỉ dành VIP / SVIP / ADMIN.');return}if(!canUnlockInfographic(CUR)){alert('Phải trả lời đúng câu này mới mở khóa infographic.');return}if(!SID||!QUESTIONS.length){alert('Hãy mở một đề và chọn câu trước.');return}saveCurrent();let ta=document.getElementById('infographicPromptText');let title=document.getElementById('infographicModalTitle');let modal=document.getElementById('infographicModal');if(!ta||!modal){alert('Không tìm thấy hộp prompt.');return}ta.value='Đang tạo prompt từ Sheet (câu hiện tại)…';if(title){let q=QUESTIONS[CUR]||{};let md=String(q.MucDo||'').trim();title.textContent='📊 Infographic · Câu '+(CUR+1)+(q.ID?' · ID '+q.ID:'')+(md?' · Mức độ '+md:'')}modal.classList.remove('hide');try{let j=await api('/api/infographic-prompt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR,answer:ANSWERS[CUR],...quizRestorePayload()})});ta.value=j.prompt||'';if(!ta.value)ta.value='Không tạo được prompt.';if(title){let q=QUESTIONS[CUR]||{};let parts=['📊 Infographic · Câu '+(CUR+1)];if(q.ID)parts.push('ID '+q.ID);let md=String(j.mucdo||q.MucDo||'').trim();if(md)parts.push('Mức độ '+md);if(j.dang_title)parts.push(j.dang_title);title.textContent=parts.join(' · ')}if(j.warnings&&j.warnings.length)alert('⚠️ Kiểm tra Sheet:\n'+j.warnings.join('\n'))}catch(e){ta.value='';alert('Không tạo được prompt: '+(e.message||e))}}
function copyInfographicPrompt(){let ta=document.getElementById('infographicPromptText');if(!ta||!String(ta.value||'').trim()){alert('Chưa có prompt.');return}navigator.clipboard.writeText(ta.value).then(()=>alert('Đã chép prompt.\n\nDán Gemini — poster hiện đại đầy màu, 4 card gradient, không chữ Khối.')).catch(()=>{ta.focus();ta.select();try{document.execCommand('copy');alert('Đã chép (Ctrl+C).')}catch(e){alert('Chọn text trong ô rồi Ctrl+C.')}})}
let QUESTION_SAVE_BUSY=false;
function alertDuplicateSheetReport(dr){if(!dr||!USER.is_admin)return;let extra=parseInt(dr.extra_duplicate_rows,10)||0;if(extra<=0)return;let lines=(dr.samples||[]).slice(0,6);alert('⚠ Phát hiện câu TRÙNG trên Google Sheet (Cau_Hoi):\n\n≈ '+extra+' dòng thừa (thường do bấm Thêm câu 2 lần hoặc copy/dán).\n\n'+(lines.length?('Ví dụ:\n'+lines.join('\n')+'\n\n'):'')+'Bấm nút 🧹 Xóa trùng Sheet trên thanh ADMIN để tự xóa (giữ 1 bản / câu).')}
function showAdminDuplicateSheetNotice(){if(!USER.is_admin||!META||!META.duplicate_report)return;let dr=META.duplicate_report;let extra=parseInt(dr.extra_duplicate_rows,10)||0;if(extra<=0)return;let info=document.getElementById('info');if(info&&!String(info.textContent||'').includes('dòng trùng')){info.textContent+=` | ⚠ ${extra} dòng trùng Sheet`;if(dr.samples&&dr.samples.length)info.title=dr.samples.join('\n')}}
async function saveQuestionModal(){if(QUESTION_SAVE_BUSY)return;if(QUESTION_MODAL_MODE==='add')return saveAddQuestion();return saveEdit()}
async function saveEdit(){if(QUESTION_SAVE_BUSY)return;let q=QUESTIONS[CUR];if(!q||!q._row){alert('Không xác định dòng Sheet.');return}let updates={};for(let f of ['CauHoi','A','B','C','D','DapAn','SaiSo','MucDo','Dang','QuyenTruyCap','LoiGiai','HinhAnh'])updates[f]=document.getElementById('edit_'+f).value;let miss=adminLoigiaiMissingLetters(updates.LoiGiai,q);if(miss.length&&!confirm('Lời giải thiếu ý '+miss.join(', ')+'.\n\nVẫn lưu Sheet?'))return;if(!String(updates.DapAn||'').trim()&&!confirm('Đáp án (P) đang trống.\n\nVẫn lưu Sheet?'))return;QUESTION_SAVE_BUSY=true;let saveBtn=document.getElementById('btnSaveQuestion');if(saveBtn){saveBtn.disabled=true;saveBtn.textContent='⏳ Đang lưu…'}try{let j=await api('/api/question/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row,updates})});let savedRow=q._row;Object.assign(q,updates);applyResolvedDang(q);if(HINT_BY_Q[CUR]&&HINT_BY_Q[CUR].admin_review){markAdminHintSaved(CUR);HINT_BY_Q[CUR].sheet_dapan=updates.DapAn||'';HINT_BY_Q[CUR].sheet_loigiai=updates.LoiGiai||''}if(CHECKED[CUR]){delete CHECKED[CUR].LoiGiai;delete CHECKED[CUR].DapAn;if(updates.DapAn)delete CHECKED[CUR].rows}if(RESULTS[CUR]){delete RESULTS[CUR].LoiGiai;delete RESULTS[CUR].DapAn;if(updates.DapAn)delete RESULTS[CUR].rows}CUR=regroupQuestionsByDang(savedRow);closeEdit();renderQuestion();if(HINT_BY_Q[CUR]&&!document.getElementById('hintBox').classList.contains('hide'))renderHintBox(HINT_BY_Q[CUR]);alert('Đã lưu vào Google Sheet dòng '+j.row+'\nĐã cập nhật: '+(j.fields||[]).join(', ')+(adminHintNeedsSave(CUR)?'':'\\n\\n✅ Có thể so khớp ĐA/LG với AI ở trên.'))}catch(e){alert('Không lưu được: '+e.message)}finally{QUESTION_SAVE_BUSY=false;syncQuestionModalChrome();let sb=document.getElementById('btnSaveQuestion');if(sb)sb.disabled=false}}
async function saveAddQuestion(){if(QUESTION_SAVE_BUSY)return;let data=readQuestionFormData();if(!String(data.CauHoi||'').trim()){alert('Phải nhập nội dung câu hỏi.');return}QUESTION_SAVE_BUSY=true;let saveBtn=document.getElementById('btnSaveQuestion');if(saveBtn){saveBtn.disabled=true;saveBtn.textContent='⏳ Đang thêm…'}try{let j=await api('/api/question/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data})});let nq=applyResolvedDang(j.question||{});if(!nq._row)nq._row=j.row;let insertAt=Math.min(CUR+1,QUESTIONS.length);QUESTIONS.splice(insertAt,0,nq);insertQuizMaps(insertAt);CUR=regroupQuestionsByDang(nq._row);closeEdit();renderNav();renderQuestion();refreshCatalogFromMeta();alert('Đã thêm câu mới vào Google Sheet dòng '+j.row+(j.id?('\nID: '+j.id):''))}catch(e){alert('Không thêm được: '+e.message)}finally{QUESTION_SAVE_BUSY=false;syncQuestionModalChrome();let sb=document.getElementById('btnSaveQuestion');if(sb)sb.disabled=false}}
async function deleteQuestion(){let q=QUESTIONS[CUR];if(!q||!q._row){alert('Không xác định được dòng Google Sheet của câu này.');return;}let msg='Xóa vĩnh viễn câu này khỏi Google Sheet?\n\nID: '+(q.ID||'')+'\nDòng: '+q._row+'\n\nApp tự cập nhật — không cần bấm Đồng bộ Sheet sau mỗi lần xóa.';if(!confirm(msg))return;if(!confirm('Xác nhận lần 2: thầy chắc chắn muốn xóa câu này?'))return;try{let j=await api('/api/question/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row,id:q.ID||''})});let deletedRow=parseInt(j.row,10)||0;let removedIdx=CUR;QUESTIONS.splice(removedIdx,1);for(let qq of QUESTIONS){let r=parseInt(qq._row,10)||0;if(r>deletedRow)qq._row=r-1}reindexQuizMaps(removedIdx);refreshCatalogFromMeta();if(QUESTIONS.length===0){closeEdit();backHome();alert('Đã xóa câu cuối trong phiên này.\nMục lục đã tự cập nhật — không cần Đồng bộ Sheet.');return}if(CUR>=QUESTIONS.length)CUR=QUESTIONS.length-1;closeEdit();renderNav();renderQuestion();document.getElementById('resultBox').textContent='Đã xóa dòng '+deletedRow+' — còn '+QUESTIONS.length+' câu';document.getElementById('resultBox').style.color='#166534'}catch(e){alert('Không xóa được: '+e.message)}}
setInterval(updateExamStrip,1000);
document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement&&FULLDE_ON){document.body.classList.add('fullde-mode')}if(!document.fullscreenElement){FS_ANS_FORCE=null;FS_EXP_FORCE=null;renderQuestion()}});
enhanceHomeColors();initTheme();initMobileQuizToolbar();init().catch(e=>{document.body.innerHTML='<pre style="padding:20px;color:red">'+e.message+'</pre>'})
</script></body></html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route("/version")
def version():
    return jsonify({
        "version": APP_VERSION,
        "login_required": True,
        "fast_login_cache": True,
        "login_reads_only_hoc_vien": True,
        "trial_register_3_days": True,
        "trial_only_free_exam": True,
        "trial_no_submit_no_score": True,
        "base": "V10_SAFE_LOADING_NOTICE_WORKING",
        "image_column_T_fix": True,
        "trial_no_vip_exam": True,
        "admin_can_view_without_submit": True,
        "admin_can_edit_question": True,
        "admin_can_delete_question": True,
        "admin_save_fast_no_full_reload": True,
        "admin_delete_fast_no_full_reload": True,
        "admin_delete_chain_no_resync": True,
        "admin_fixed_top_bar": True,
        "catalog_group_chuong_bai": True,
        "admin_ai_full_answer_v66": True,
        "ai_hint_loading_ui": True,
        "quiz_session_restore_v68": True,
        "mobile_fs_layout_v69": True,
        "mobile_tf_layout_v70": True,
        "mobile_tf_labels_v71": True,
        "latex_textbf_v72": True,
        "mobile_tf_ds_col_v73": True,
        "latex_textbf_md_bold_v74": True,
        "vip_ds_ai_detail_v75": True,
        "fix_dang_mcq_ds_v76": True,
        "fix_dang_ds_priority_v77": True,
        "fix_dang_after_load_v78": True,
        "cascade_filters_v80": True,
        "fix_hint_500_timeout_v82": True,
        "fix_test_key_admin_review_v83": True,
        "latex_norm_removed_v178": True,
        "admin_toolbar_dedup_v179": True,
        "retry_shuffle": True,
        "routes": ["/login", "/register", "/logout", "/share", "/d/<made>", "/api/meta", "/api/start", "/api/start-random", "/api/submit", "/api/question/create", "/api/question/update", "/api/question/delete", "/api/question/dedupe", "/api/question/lookup", "/api/infographic-prompt"]
    })

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        mahs = clean(request.form.get("mahs"))
        password = clean(request.form.get("password"))
        try:
            store = get_store()
            store.ensure_users_loaded()
            user = store.users.get(mahs)
            if not user:
                # Không phân biệt hoa thường
                for k, v in store.users.items():
                    if key_norm(k) == key_norm(mahs):
                        user = v
                        mahs = k
                        break
            if not user:
                error = "Không thấy tài khoản trong sheet HOC_VIEN."
            elif user.get("status", "ON").upper() not in ["ON", "ACTIVE", "1", "TRUE", "VIP", "ADMIN", "TRIAL"]:
                error = "Tài khoản đang bị khóa hoặc chưa kích hoạt."
            elif store.is_user_expired(user)[0]:
                error = store.is_user_expired(user)[1]
            elif clean(user.get("password")) != password:
                error = "Sai mật khẩu."
            else:
                token = stable_hash(f"{mahs}|{time.time()}|{random.random()}", 24)
                store.active_tokens[mahs] = token
                session.clear()
                session.update({
                    "mahs": user.get("mahs"), "hoten": user.get("hoten"), "lop": user.get("lop"),
                    "role": user.get("role"), "session_token": token,
                    "trial_until": user.get("trial_until", ""), "account_until": user.get("account_until", "")
                })
                nxt = safe_next_url(request.form.get("next"))
                return redirect(nxt or url_for("home"))
        except Exception as e:
            error = str(e)
    next_url = safe_next_url(request.args.get("next", ""))
    og_title = og_desc = og_url = ""
    if next_url:
        de = parse_de_from_next(next_url)
        if de:
            try:
                store = get_store()
                og_title, og_desc = share_og_context(store, de)
                og_url = request.url_root.rstrip("/") + next_url
            except Exception:
                pass
    return render_template_string(
        LOGIN_HTML,
        error=error,
        msg=request.args.get("msg", ""),
        next=next_url,
        og_title=og_title,
        og_desc=og_desc,
        og_url=og_url,
    )

@app.route("/d/<made>")
def share_exam_short(made):
    return render_share_page(clean(made), request.args)


@app.route("/share")
def share_exam():
    de = clean(request.args.get("de") or request.args.get("made"))
    if not de:
        return render_share_page("", request.args)
    extras = []
    for k in ("open", "sq", "sa", "level", "dang"):
        v = clean(request.args.get(k))
        if v:
            extras.append(f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}")
    short = f"/d/{de}" + ("?" + "&".join(extras) if extras else "")
    return redirect(short)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""
    if request.method == "POST":
        try:
            store = get_store()
            user = store.register_trial(
                request.form.get("hoten", ""),
                request.form.get("lop", ""),
                request.form.get("phone", ""),
                request.form.get("password", ""),
                request.form.get("device_id", ""),
            )
            token = stable_hash(f"{user.get('mahs')}|{time.time()}|{random.random()}", 24)
            store.active_tokens[user.get("mahs")] = token
            session.clear()
            session.update({
                "mahs": user.get("mahs"), "hoten": user.get("hoten"), "lop": user.get("lop"),
                "role": user.get("role"), "session_token": token,
                "trial_until": user.get("trial_until", ""), "account_until": user.get("account_until", "")
            })
            return redirect(url_for("home"))
        except Exception as e:
            error = str(e)
    return render_template_string(REGISTER_HTML, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def home():
    if not session.get("mahs"):
        de = clean(request.args.get("de") or request.args.get("made"))
        if de and is_link_preview_bot():
            return redirect(f"/d/{de}")
        fp = request.full_path
        if fp.endswith("?") and not request.args:
            fp = request.path
        if fp and fp not in ("/", ""):
            return redirect(url_for("login", next=fp))
        return redirect(url_for("login"))
    return render_template_string(APP_HTML)

@app.route("/api/meta")
def api_meta():
    bad = require_login_json()
    if bad:
        return bad
    st = get_store()
    return jsonify(st.meta_light())

@app.route("/api/sync", methods=["POST"])
def api_sync():
    bad = require_login_json()
    if bad:
        return bad
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được đồng bộ dữ liệu"}), 403
    st = get_store()
    st.questions_loaded = False
    st.start_questions_background(force=True)
    return jsonify({"ok": True, "loading": True, "message": "Đã bắt đầu đồng bộ Google Sheet ở nền. Trang sẽ tự cập nhật sau vài giây."})

@app.route("/api/start", methods=["GET", "POST"])
def api_start():
    bad = require_login_json()
    if bad:
        return bad
    body = request.get_json(silent=True) or {} if request.method == "POST" else {}
    def _arg(name: str, default: str = "") -> str:
        if name in body and body.get(name) is not None:
            return clean(body.get(name))
        return clean(request.args.get(name, default))

    made = _arg("made")
    shuffle_q = str(_arg("shuffle_q", "0")).lower() in ("1", "true", "yes")
    shuffle_a = str(_arg("shuffle_a", "0")).lower() in ("1", "true", "yes")
    group_by_dang = str(_arg("group_by_dang", "1")).lower() not in ("0", "false", "no")
    level = _arg("level").upper()
    dang = _arg("dang") or _arg("dang_filter")
    if dang:
        dang = norm_dang(dang)
    st = get_store()
    if not st.questions_loaded:
        st.start_questions_background(force=False)
        return jsonify({"error": "Dữ liệu đề đang nạp từ Google Sheet. Thầy chờ vài giây rồi bấm lại."}), 202
    return jsonify(st.start_quiz(
        made,
        shuffle_questions=shuffle_q,
        shuffle_options=shuffle_a,
        level_filter=level,
        dang_filter=dang,
        group_by_dang=group_by_dang,
    ))


@app.route("/api/start-random", methods=["POST"])
def api_start_random():
    bad = require_login_json()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    st = get_store()
    if not st.questions_loaded:
        st.start_questions_background(force=False)
        return jsonify({"error": "Dữ liệu đề đang nạp từ Google Sheet. Thầy chờ vài giây rồi bấm lại."}), 202
    try:
        chuongs_raw = body.get("chuongs") or body.get("chapters") or []
        if isinstance(chuongs_raw, str):
            chuongs_raw = [x.strip() for x in chuongs_raw.split(",") if x.strip()]
        if not isinstance(chuongs_raw, list):
            chuongs_raw = []
        return jsonify(st.start_random_practice(
            mon=clean(body.get("mon", "")),
            khoi=clean(body.get("khoi", "")),
            lop=clean(body.get("lop", "")),
            chuongs=[clean(x) for x in chuongs_raw if clean(x)],
            chuong=clean(body.get("chuong", "")),
            baihoc=clean(body.get("bai_hoc", body.get("baihoc", ""))),
            bode=clean(body.get("bode", "")),
            level_filter=clean(body.get("level", "")).upper(),
            sol_full_only=str(body.get("sol_full_only", "0")).lower() in ("1", "true", "yes"),
            shuffle_options=str(body.get("shuffle_a", "1")).lower() not in ("0", "false", "no"),
        ))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/fifty", methods=["POST"])
def api_fifty():
    bad = require_login_json()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    restore = quiz_restore_payload_from_body(body)
    try:
        return jsonify(get_store().fifty_fifty(body.get("sid", ""), int(body.get("index", 0)), restore))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/check-one", methods=["POST"])
def api_check_one():
    bad = require_login_json()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    restore = quiz_restore_payload_from_body(body)
    try:
        return jsonify(get_store().check_one(body.get("sid", ""), int(body.get("index", 0)), body.get("answer", ""), restore))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/hint", methods=["POST"])
def api_hint():
    bad = require_login_json()
    if bad:
        return bad
    bad_ai = require_ai_hint_json()
    if bad_ai:
        return bad_ai
    refresh_session_role_from_store()
    data = request.get_json(silent=True) or {}
    sid = clean(data.get("sid"))
    try:
        idx = int(data.get("index", 0))
    except Exception:
        idx = 0
    answer = data.get("answer", "")
    st = get_store()
    restore = quiz_restore_payload_from_body(data)
    try:
        return jsonify(st.hint_one(sid, idx, answer, restore))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/hint/similar", methods=["POST"])
def api_hint_similar():
    bad = require_login_json()
    if bad:
        return bad
    bad_ai = require_ai_hint_json()
    if bad_ai:
        return bad_ai
    refresh_session_role_from_store()
    data = request.get_json(silent=True) or {}
    sid = clean(data.get("sid"))
    try:
        idx = int(data.get("index", 0))
    except Exception:
        idx = 0
    st = get_store()
    restore = quiz_restore_payload_from_body(data)
    try:
        return jsonify(st.similar_one(sid, idx, restore))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/infographic-prompt", methods=["POST"])
def api_infographic_prompt():
    bad = require_login_json()
    if bad:
        return bad
    if not can_use_infographic():
        return jsonify({"error": "Infographic chỉ dành tài khoản VIP / SVIP / ADMIN."}), 403
    data = request.get_json(silent=True) or {}
    sid = clean(data.get("sid"))
    try:
        idx = int(data.get("index", 0))
    except Exception:
        idx = 0
    answer = data.get("answer", "")
    st = get_store()
    restore = quiz_restore_payload_from_body(data)
    try:
        return jsonify(st.infographic_prompt_one(sid, idx, answer, restore))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def _api_ai_config_handler():
    if request.method == "GET":
        cfg = ai_runtime_config()
        profile = classify_user_ai_profile(cfg)
        return jsonify({
            "ok": True,
            "provider": cfg.get("provider", "AUTO"),
            "openai_keys_count": cfg.get("openai_keys", 0),
            "gemini_keys_count": cfg.get("gemini_keys", 0),
            "has_keys": cfg.get("has_keys", False),
            "openai_keys_raw": cfg.get("openai_keys_raw", []),
            "gemini_keys_raw": cfg.get("gemini_keys_raw", []),
            "openai_keys_masked": cfg.get("openai_keys_masked", []),
            "gemini_keys_masked": cfg.get("gemini_keys_masked", []),
            "gemini_model": cfg.get("gemini_model", DEFAULT_GEMINI_HINT_MODEL),
            "openai_model": cfg.get("openai_model", DEFAULT_OPENAI_HINT_MODEL),
            "using_user_keys": cfg.get("using_user_keys", False),
            "has_server_keys": cfg.get("has_server_keys", False),
            "user_gemini_keys": cfg.get("user_gemini_keys", 0),
            "can_save_own_key": cfg.get("can_save_own_key", False),
            "personal": True,
            **profile,
        })
    body = request.get_json(silent=True) or {}
    try:
        cfg = update_ai_runtime_config(body)
        profile = classify_user_ai_profile(cfg)
        return jsonify({
            "ok": True,
            "message": "Đã lưu key AI của bạn (ưu tiên khi bấm Gợi ý AI).",
            "provider": cfg.get("provider", "AUTO"),
            "openai_keys_count": cfg.get("openai_keys", 0),
            "gemini_keys_count": cfg.get("gemini_keys", 0),
            "user_gemini_keys": cfg.get("user_gemini_keys", 0),
            "has_keys": cfg.get("has_keys", False),
            "using_user_keys": cfg.get("using_user_keys", False),
            "gemini_model": cfg.get("gemini_model", ""),
            **profile,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def _first_key_from_raw(raw: Any) -> str:
    g, o = parse_api_keys_2026(raw)
    if g:
        return g[0]
    if o:
        return o[0]
    return ""


def _resolve_runtime_test_key(provider: str) -> Tuple[str, str]:
    """Lấy key đang dùng thật (cá nhân hoặc ENV) khi ô nhập trống — giống GAS đọc ScriptProperties."""
    p = clean(provider).upper() or DEFAULT_AI_PROVIDER
    if p == "AUTO":
        g = load_ai_keys("GEMINI")
        if g:
            return g[0], "GEMINI"
        o = load_ai_keys("OPENAI")
        if o:
            return o[0], "OPENAI"
        return "", "AUTO"
    if p == "GEMINI":
        keys = load_ai_keys("GEMINI")
        return (keys[0] if keys else ""), "GEMINI"
    keys = load_ai_keys("OPENAI")
    return (keys[0] if keys else ""), "OPENAI"


def mask_api_key_hint(key: str) -> str:
    """Hiển thị một phần key để user biết đang nói key nào — không lộ full key."""
    k = clean_ai_key_2026(key)
    if not k:
        return "???"
    if len(k) <= 14:
        return k[:6] + "…"
    return f"{k[:8]}…{k[-4:]}"


def _ai_key_test_label(index: int, key: str, source: str = "") -> str:
    hint = mask_api_key_hint(key)
    label = f"Key #{index} ({hint})"
    if source:
        label += f" — {source}"
    return label


def _build_ai_key_test_summary(details: List[Dict[str, Any]], provider: str = "GEMINI") -> Tuple[bool, str]:
    if not details:
        return False, "Không có key để test."
    ok_count = sum(1 for d in details if d.get("ok"))
    total = len(details)
    prov = clean(provider).upper() or "GEMINI"
    if ok_count == total:
        return True, f"{ok_count}/{total} key {prov} OK."
    if ok_count > 0:
        summary = f"{ok_count}/{total} key OK."
        bad = [d for d in details if not d.get("ok")]
        summary += f" {len(bad)} key lỗi — app sẽ dùng key còn hoạt động."
        summary += "\n" + "\n".join(f"✗ {d.get('label', '')}: {d.get('message', '')}" for d in bad)
        return True, summary
    summary = f"0/{total} key OK."
    summary += "\n" + "\n".join(f"✗ {d.get('label', '')}: {d.get('message', '')}" for d in details)
    return False, summary


def test_ai_key_batch(
    provider: str,
    key_items: List[Tuple[str, str]],
    model: str = "",
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Test lần lượt từng key — báo rõ số thứ tự, mã che và nguồn (Key của bạn / Render ENV)."""
    p = clean(provider).upper() or DEFAULT_AI_PROVIDER
    if p == "AUTO":
        p = "GEMINI"
    details: List[Dict[str, Any]] = []
    for idx, (k, source) in enumerate(key_items, start=1):
        fmt_err = _validate_key_format(p, k)
        label = _ai_key_test_label(idx, k, source)
        if fmt_err:
            details.append({
                "index": idx,
                "ok": False,
                "message": fmt_err,
                "key_hint": mask_api_key_hint(k),
                "source": source,
                "label": label,
            })
            continue
        ok, msg = test_ai_key(p, k, model)
        details.append({
            "index": idx,
            "ok": ok,
            "message": msg,
            "key_hint": mask_api_key_hint(k),
            "source": source,
            "label": label,
        })
    ok_all, summary = _build_ai_key_test_summary(details, p)
    return ok_all, summary, details


def _runtime_ai_key_items(provider: str) -> List[Tuple[str, str]]:
    p = clean(provider).upper() or DEFAULT_AI_PROVIDER
    if p == "AUTO":
        p = "GEMINI"
    items: List[Tuple[str, str]] = []
    seen: set = set()
    for k in load_user_ai_keys(p):
        if k not in seen:
            seen.add(k)
            items.append((k, "Key của bạn"))
    for k in load_ai_keys_from_env(p):
        if k not in seen:
            seen.add(k)
            items.append((k, "Render ENV"))
    return items[:MAX_AI_KEYS_PER_PROVIDER]


def test_ai_key(provider: str, api_key: str, model: str = "") -> Tuple[bool, str]:
    p = clean(provider).upper() or "AUTO"
    k = clean(api_key)
    if not k:
        return False, "Chưa có key để test."

    if p == "AUTO":
        p = "GEMINI" if k.startswith("AIza") else "OPENAI"

    if p == "GEMINI":
        gmodel = clean(model) or os.environ.get("GEMINI_HINT_MODEL", DEFAULT_GEMINI_HINT_MODEL).strip() or DEFAULT_GEMINI_HINT_MODEL
        models_try = [gmodel] + [m for m in GEMINI_HINT_MODEL_FALLBACKS if m != gmodel]
        body = {"contents": [{"parts": [{"text": "Trả lời đúng 1 từ: OK"}]}], "generationConfig": {"temperature": 0}}
        last_err = ""
        for gmodel in models_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gmodel}:generateContent?key={urllib.parse.quote(k)}"
            req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=18) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                cands = (data or {}).get("candidates") or []
                parts = (((cands[0] if cands else {}).get("content") or {}).get("parts") or [])
                txt = clean((parts[0] if parts and isinstance(parts[0], dict) else {}).get("text", ""))
                if txt:
                    return True, f"Gemini OK — model {gmodel}."
                last_err = "Gemini phản hồi rỗng."
            except Exception as e:
                last_err = _http_error_message(e)
                continue
        return False, last_err or "Gemini lỗi."

    omodel = clean(model) or os.environ.get("OPENAI_HINT_MODEL", DEFAULT_OPENAI_HINT_MODEL).strip() or DEFAULT_OPENAI_HINT_MODEL
    body = {"model": omodel, "messages": [{"role": "user", "content": "Reply with OK only."}], "temperature": 0}
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {k}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=18) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        txt = clean((((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content", ""))
        if txt:
            return True, f"OpenAI OK với model {omodel}."
        return False, "OpenAI phản hồi rỗng."
    except Exception as e:
        return False, _http_error_message(e)


def test_all_server_ai_keys(provider: str = "GEMINI", model: str = "") -> Tuple[bool, str, List[Dict[str, Any]]]:
    p = clean(provider).upper() or DEFAULT_AI_PROVIDER
    if p == "AUTO":
        p = "GEMINI"
    keys = load_ai_keys_from_env(p)
    if not keys:
        return False, "Chưa có key trên Render ENV.", []
    items = [(k, "Render ENV") for k in keys]
    return test_ai_key_batch(p, items, model)


@app.route("/api/ai-config", methods=["GET", "POST"])
@app.route("/api/admin/ai-config", methods=["GET", "POST"])
def api_ai_config():
    bad = require_login_json()
    if bad:
        return bad
    if request.method == "POST":
        bad_ai = require_ai_hint_json()
        if bad_ai:
            return bad_ai
    return _api_ai_config_handler()


def test_all_runtime_ai_keys(provider: str = "GEMINI", model: str = "") -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Test toàn bộ key đang dùng (tự nạp + Render ENV)."""
    p = clean(provider).upper() or DEFAULT_AI_PROVIDER
    if p == "AUTO":
        p = "GEMINI"
    items = _runtime_ai_key_items(p)
    if not items:
        return False, "Chưa có key. Dán key AIza... tại 🔑 Key AI của tôi hoặc cấu hình Render.", []
    return test_ai_key_batch(p, items, model)


def _keys_from_check_body(body: Dict[str, Any], provider: str) -> List[Tuple[str, str]]:
    """Lấy danh sách key từ body test — mỗi dòng một key trong ô nhập."""
    p = clean(provider).upper() or DEFAULT_AI_PROVIDER
    items: List[Tuple[str, str]] = []
    seen: set = set()
    for field in ("api_keys", "gemini_keys", "openai_keys"):
        raw = body.get(field)
        if not str(raw or "").strip():
            continue
        g_keys, o_keys = parse_api_keys_2026(raw)
        pick = g_keys if p in ("GEMINI", "AUTO") else o_keys
        if p == "AUTO" and not pick:
            pick = o_keys
        for idx, k in enumerate(pick, start=1):
            if k in seen:
                continue
            seen.add(k)
            src = "Ô nhập" if len(pick) == 1 else f"Ô nhập (dòng {idx})"
            items.append((k, src))
    single = clean_ai_key_2026(body.get("api_key", ""))
    if single and single not in seen:
        items.append((single, "Ô nhập"))
    return items[:MAX_AI_KEYS_PER_PROVIDER]


def _ai_key_check_response(ok: bool, msg: str, provider: str, details: List[Dict[str, Any]]) -> Any:
    return jsonify({
        "ok": ok,
        "message": msg,
        "version": APP_VERSION,
        "provider_used": provider,
        "keys_tested": len(details),
        "keys_ok": sum(1 for d in details if d.get("ok")),
        "details": details,
    })


@app.route("/api/ai-key-check", methods=["POST"])
def api_ai_key_check():
    bad = require_login_json()
    if bad:
        return bad
    bad_ai = require_ai_hint_json()
    if bad_ai:
        return bad_ai
    body = request.get_json(silent=True) or {}
    provider = clean(body.get("provider", DEFAULT_AI_PROVIDER)).upper() or DEFAULT_AI_PROVIDER
    model = clean(body.get("model", ""))
    if not model and provider in ["GEMINI", "AUTO"]:
        model = clean(body.get("gemini_model", ""))
    if not model and provider in ["OPENAI", "AUTO"]:
        model = clean(body.get("openai_model", ""))
    used_provider = provider
    if provider in ["GEMINI", "AUTO"]:
        used_provider = "GEMINI"
    elif provider == "OPENAI":
        used_provider = "OPENAI"

    input_items = _keys_from_check_body(body, provider)
    if len(input_items) >= 1:
        ok, msg, details = test_ai_key_batch(used_provider, input_items, model)
        return _ai_key_check_response(ok, msg, used_provider, details)

    runtime_items = _runtime_ai_key_items(used_provider)
    if runtime_items:
        ok, msg, details = test_ai_key_batch(used_provider, runtime_items, model)
        return _ai_key_check_response(ok, msg, used_provider, details)

    key, used_provider = _resolve_runtime_test_key(provider)
    if not key:
        return jsonify({
            "ok": False,
            "message": "Chưa có key. Vào 🔑 Key AI của tôi → dán AIza... (mỗi dòng một key) → Lưu key.",
            "version": APP_VERSION,
            "details": [],
        })
    ok, msg, details = test_ai_key_batch(used_provider, [(key, "Key đang dùng")], model)
    return _ai_key_check_response(ok, msg, used_provider, details)


@app.route("/api/submit", methods=["POST"])
def api_submit():
    bad = require_login_json()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    restore = quiz_restore_payload_from_body(body)
    try:
        return jsonify(get_store().submit(body.get("sid", ""), body.get("answers", {}), restore))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/question/lookup", methods=["GET", "POST"])
def api_question_lookup():
    bad = require_login_json()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    qid = clean(body.get("id") or request.args.get("id") or "")
    st = get_store()
    if not st.questions_loaded:
        st.start_questions_background(force=False)
        return jsonify({
            "id": qid,
            "matches": [],
            "count": 0,
            "loading": True,
            "message": "Đang nạp Sheet, thử lại sau vài giây.",
        })
    return jsonify(st.lookup_questions_by_id(qid))


@app.route("/api/question/update", methods=["POST"])
def api_question_update():
    bad = require_login_json()
    if bad:
        return bad
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được sửa câu hỏi"}), 403
    body = request.get_json(silent=True) or {}
    try:
        st = get_store()
        st.ensure_questions_loaded()
        return jsonify(st.update_question(int(body.get("row", 0)), body.get("updates", {})))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/question/create", methods=["POST"])
def api_question_create():
    bad = require_login_json()
    if bad:
        return bad
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được thêm câu hỏi"}), 403
    body = request.get_json(silent=True) or {}
    try:
        st = get_store()
        st.ensure_questions_loaded()
        return jsonify(st.add_question(body.get("data") or body.get("question") or body))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/question/delete", methods=["POST"])
def api_question_delete():
    bad = require_login_json()
    if bad:
        return bad
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được xóa câu hỏi"}), 403
    body = request.get_json(silent=True) or {}
    try:
        st = get_store()
        st.ensure_questions_loaded()
        return jsonify(st.delete_question(int(body.get("row", 0)), body.get("id", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/question/dedupe", methods=["POST"])
def api_question_dedupe():
    bad = require_login_json()
    if bad:
        return bad
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được xóa câu trùng"}), 403
    body = request.get_json(silent=True) or {}
    dry_run = str(body.get("dry_run", "false")).lower() in ("1", "true", "yes")
    try:
        st = get_store()
        st.ensure_questions_loaded()
        return jsonify(st.remove_duplicate_questions(dry_run=dry_run))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)