# -*- coding: utf-8 -*-
"""
app.py - Ứng dụng luyện đề Google Sheet + đăng nhập + ADMIN sửa câu
Chạy Render:
    gunicorn app:app --bind 0.0.0.0:$PORT
Yêu cầu Environment Variables trên Render:
    GOOGLE_SHEET_ID
    GOOGLE_CREDENTIALS_JSON
    GEMINI_API_KEY=AIza...
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
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:  # Cho phép app vẫn mở nếu chưa cài gspread local
    gspread = None
    Credentials = None

APP_VERSION = "V78_FIX_DANG_AFTER_LOAD_2026_06_02"
DEFAULT_GEMINI_HINT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_GEMINI_ADMIN_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_HINT_MODEL = "gpt-4.1-mini"
DEFAULT_AI_PROVIDER = "GEMINI"
AI_HINT_MAX_OUTPUT_TOKENS = max(120, min(int(os.environ.get("AI_HINT_MAX_TOKENS", "280") or 280), 800))
AI_HINT_MAX_CHARS = max(200, min(int(os.environ.get("AI_HINT_MAX_CHARS", "480") or 480), 1200))
AI_HINT_VIP_MAX_OUTPUT_TOKENS = max(220, min(int(os.environ.get("AI_HINT_VIP_MAX_TOKENS", "520") or 520), 1000))
AI_HINT_VIP_MAX_CHARS = max(350, min(int(os.environ.get("AI_HINT_VIP_MAX_CHARS", "850") or 850), 2000))
AI_HINT_ADMIN_MAX_OUTPUT_TOKENS = max(800, min(int(os.environ.get("AI_HINT_ADMIN_MAX_TOKENS", "2400") or 2400), 4096))
AI_HINT_ADMIN_MAX_CHARS = max(2000, min(int(os.environ.get("AI_HINT_ADMIN_MAX_CHARS", "10000") or 10000), 16000))
AI_HINT_ADMIN_MAX_CONTINUATIONS = max(0, min(int(os.environ.get("AI_HINT_ADMIN_CONTINUATIONS", "2") or 2), 3))
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
    s = re.sub(r"\s+", " ", s)
    s = s.replace("_", " ").replace("-", " ")
    return s.strip()


def clean(v: Any) -> str:
    s = str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


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
    return inner


def _fix_merged_inline_math(t: str) -> str:
    if "$" not in t:
        return _fix_plain_text_gaps(t)
    out, i = [], 0
    while i < len(t):
        d1 = t.find("$", i)
        if d1 < 0:
            out.append(_fix_plain_text_gaps(t[i:]))
            break
        out.append(_fix_plain_text_gaps(t[i:d1]))
        d2 = t.find("$", d1 + 1)
        if d2 < 0:
            out.append(t[d1:])
            break
        inner = _fix_one_math_inner(t[d1 + 1 : d2])
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


def normalize_latex_text(s: Any) -> str:
    """Chuẩn hóa LaTeX từ Word/Sheet: ${\\beta}$, \\item, khối $ nuốt tiếng Việt."""
    t = clean(s)
    if not t:
        return ""
    t = _strip_latex_list_markup(t)
    t = re.sub(r"\$\{\s*([^}$\n]+?)\s*\}\s*\$", r"$(\1)$", t)
    t = re.sub(r"\$\{\s*([^}$\n]+?)\s*\}", r"$(\1)$", t)
    t = re.sub(r"(?<![$\\])\{\s*\(\s*([^}]+?)\s*\)\s*\}(?![$])", r"$(\1)$", t)
    t = re.sub(r"\$\(\((\\?[a-zA-Z]+)\)\)\$\.?", r"$\\1$.", t)
    t = re.sub(r"\$\(\((\\?[a-zA-Z]+)\)\)(?!\$)", r"$\\1$", t)
    t = _fix_merged_inline_math(t)
    t = re.sub(r"(\$[^$\n]+?\$)\$+", r"\1", t)
    t = re.sub(r"\$\s*\$", " ", t)

    def _fix_math_bs(m: re.Match) -> str:
        inner = m.group(1).replace("\\\\", "\\")
        return f"${inner}$"

    t = re.sub(r"\$([^$]+)\$", _fix_math_bs, t)
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
    k = key_norm(s)
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
    return "Trắc nghiệm"


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


def effective_dang(q: Dict[str, Any]) -> str:
    """Suy luận dạng câu: đáp án Đ/S hoặc một chữ A-D quyết định, cột J là phụ."""
    raw_col = clean(q.get("Dang", ""))
    dang_col = norm_dang(raw_col)
    dapan = q.get("DapAn")
    has_opts = has_tf_statements(q)

    if dang_col == "Đúng sai":
        return "Đúng sai"
    if dang_col == "Trả lời ngắn":
        return "Trả lời ngắn"
    if dang_col == "Tự luận":
        return "Tự luận"

    # Đáp án SSĐĐ / Đúng,Sai,... → Đúng sai (kể cả cột J ghi nhầm Trắc nghiệm)
    if looks_like_dungsai_answer(dapan) and has_opts:
        return "Đúng sai"

    # Đáp án một chữ B/D... → trắc nghiệm
    if is_mcq_letter_answer(dapan) and has_opts:
        return "Trắc nghiệm"

    if raw_col:
        return dang_col
    return "Trắc nghiệm"


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
    return session.get("role") == "ADMIN"


def is_trial() -> bool:
    return session.get("role") == "TRIAL"


def can_use_5050() -> bool:
    # Học viên dùng thử KHÔNG dùng 50:50. Chỉ VIP/S.VIP/ADMIN.
    return session.get("role") in ["VIP", "S.VIP", "ADMIN"]


def can_view_solution_after_submit() -> bool:
    # FREE và TRIAL không xem đáp án/lời giải sau nộp.
    return session.get("role") in ["VIP", "S.VIP", "ADMIN"]


def can_view_solution_live() -> bool:
    """VIP/SVIP/ADMIN: xem đáp án + lời giải ngay sau khi chấm từng câu."""
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
    "BaiHoc": ["BaiHoc", "Bài học", "Bài Học"],
    "DangBaiTap": ["DangBaiTap", "Dạng bài tập", "Dạng Bài Tập", "Dang Bai Tap"],
    "MucDo": ["MucDo", "Mức độ", "Mức Độ"],
    "Dang": ["Dang", "Dạng", "Loai", "Loại", "LoaiCau", "Loại câu"],
    "CauHoi": ["CauHoi", "NoiDung", "Nội dung", "Câu hỏi", "DeBai", "Đề bài"],
    "A": ["A", "PA_A", "LuaChonA"],
    "B": ["B", "PA_B", "LuaChonB"],
    "C": ["C", "PA_C", "LuaChonC"],
    "D": ["D", "PA_D", "LuaChonD"],
    "DapAn": ["DapAn", "Đáp án", "Đáp Án", "Answer"],
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

EDITABLE_FIELDS = ["CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo", "MucDo", "Dang", "LoiGiai", "HinhAnh"]


def header_map(headers: List[str]) -> Dict[str, int]:
    return {key_norm(h): i for i, h in enumerate(headers)}


def find_col(headers: List[str], canonical: str) -> Optional[int]:
    mp = header_map(headers)
    for name in ALIASES.get(canonical, [canonical]):
        k = key_norm(name)
        if k in mp:
            return mp[k]
    return None


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
        self.users: Dict[str, Dict[str, Any]] = {}
        self.active_tokens: Dict[str, str] = {}
        self.quiz_sessions: Dict[str, Dict[str, Any]] = {}
        self.client = None
        self.sheet = None
        self.ws_questions = None
        self.ws_users = None
        self.ws_results = None
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
        self.question_col_index = {f: find_col(self.question_headers, f) for f in QUESTION_FIELDS}
        # Fallback vị trí cột để ADMIN lưu đúng khi tiêu đề chưa khớp alias.
        fallback_cols = {"CauHoi": 10, "A": 11, "B": 12, "C": 13, "D": 14, "DapAn": 15, "SaiSo": 16, "LoiGiai": 17, "HinhAnh": 19, "QuyenTruyCap": 20}
        for f, c in fallback_cols.items():
            if self.question_col_index.get(f) is None and c < len(self.question_headers):
                self.question_col_index[f] = c
        self.questions = []
        for idx, row_vals in enumerate(values[1:], start=2):
            raw = {self.question_headers[i]: row_vals[i] if i < len(row_vals) else "" for i in range(len(self.question_headers))}
            q = canonical_question(raw)

            # Fallback đúng theo bố cục thực tế của sheet thầy:
            # A:J dùng cho lọc; K:R là nội dung/đáp án/lời giải; T là link hình ảnh; U nếu có là quyền truy cập.
            exact = {
                "CauHoi": 10, "A": 11, "B": 12, "C": 13, "D": 14,
                "DapAn": 15, "SaiSo": 16, "LoiGiai": 17,
            }
            for field, col0 in exact.items():
                if not clean(q.get(field)) and col0 < len(row_vals):
                    q[field] = normalize_latex_text(row_vals[col0])
            for f in ("CauHoi", "A", "B", "C", "D", "LoiGiai"):
                q[f] = normalize_latex_text(q.get(f, ""))

            # Cột T là link hình ảnh. Ưu tiên T nếu T có link/file ID hợp lệ.
            if 19 < len(row_vals):
                t_img = clean(row_vals[19])
                if is_probably_link_or_drive(t_img) or (t_img and not clean(q.get("HinhAnh"))):
                    q["HinhAnh"] = t_img

            # Cột U là quyền truy cập nếu có; trống thì FREE.
            if 20 < len(row_vals) and not clean(q.get("QuyenTruyCap")):
                q["QuyenTruyCap"] = clean(row_vals[20])

            q["HinhAnh"] = normalize_image_src(q.get("HinhAnh"))

            # Cột I/J theo vị trí cố định — ưu tiên hơn alias header (tránh nhầm cột H "Dạng bài tập").
            if 8 < len(row_vals) and clean(row_vals[8]):
                q["MucDo"] = clean(row_vals[8])
            if 9 < len(row_vals) and clean(row_vals[9]):
                q["Dang"] = clean(row_vals[9])

            q["Dang"] = effective_dang(q)

            if not clean(q.get("CauHoi")):
                continue
            q["_row"] = idx
            self.questions.append(q)
        self.rebuild_question_indexes()

    def rebuild_question_indexes(self) -> None:
        self.by_made = {}
        self.by_group = {}
        for q in self.questions:
            self.by_made.setdefault(q.get("MaDe", ""), []).append(q)
            self.by_group.setdefault(catalog_group_key(q), []).append(q)
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
                }
            g = groups[gk]
            g["SoCau"] += 1
            if q.get("MucDo"):
                g["MucDoSet"].add(q["MucDo"])
            if q.get("Dang"):
                g["DangSet"].add(q["Dang"])
            if q.get("BoDe"):
                g["BoDeSet"].add(q["BoDe"])
            if q.get("De"):
                g["DeSet"].add(q["De"])
            access = access_level_from_text(q.get("QuyenTruyCap", ""))
            g["QuyenTruyCapSet"].add(access)
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
            out.append(item)
        out.sort(key=lambda x: (key_norm(x.get("Mon")), key_norm(x.get("Lop")), key_norm(x.get("Chuong")), key_norm(x.get("BaiHoc")), key_norm(x.get("De"))))
        return out

    def meta(self) -> Dict[str, Any]:
        def opts(field: str) -> List[str]:
            return sorted({clean(x.get(field, "")) for x in self.catalog if clean(x.get(field, ""))}, key=key_norm)
        return {
            "version": APP_VERSION,
            "loaded_at": self.loaded_at,
            "count_questions": len(self.questions),
            "count_catalog": len(self.catalog),
            "user": current_user_public(),
            "filters": {"Mon": opts("Mon"), "Lop": opts("Lop"), "Chuong": opts("Chuong"), "BaiHoc": opts("BaiHoc"), "BoDe": opts("BoDe")},
            "catalog": self.catalog,
        }

    def public_question(self, q: Dict[str, Any], index: int, reveal: bool = False) -> Dict[str, Any]:
        d = {k: q.get(k, "") for k in ["ID", "MaDe", "Dang", "MucDo", "CauHoi", "A", "B", "C", "D", "HinhAnh", "Chuong", "BaiHoc", "De", "QuyenTruyCap"]}
        d["Dang"] = effective_dang(q)
        d["HinhAnh"] = normalize_image_src(d.get("HinhAnh"))
        d["index"] = index
        if reveal:
            d["DapAn"] = q.get("DapAn", "")
            d["LoiGiai"] = q.get("LoiGiai", "")
            d["SaiSo"] = q.get("SaiSo", "")
            d["_row"] = q.get("_row", "")
        return d

    def start_quiz(self, made: str, shuffle_questions: bool = False, shuffle_options: bool = False, level_filter: str = "", dang_filter: str = "") -> Dict[str, Any]:
        if made.startswith("GRP_"):
            base_qs = list(self.by_group.get(made, []))
        else:
            base_qs = list(self.by_made.get(made, []))
        if not base_qs:
            raise RuntimeError("Không có câu hỏi trong đề này. Có thể mã đề bị lệch, hãy bấm Đồng bộ dữ liệu.")
        level_filter = clean(level_filter).upper()
        qs_source = base_qs
        if level_filter:
            def has_level(q: Dict[str, Any]) -> bool:
                lv = clean(q.get("MucDo", "")).upper()
                parts = [p.strip() for p in re.split(r"[,;/|]+", lv) if p.strip()]
                return level_filter in parts or level_filter in lv
            qs_source = [q for q in base_qs if has_level(q)]
            if not qs_source:
                raise RuntimeError(f"Đề này không có câu mức độ {level_filter}. Thầy chọn mức khác hoặc để Tất cả.")
        dang_filter = clean(dang_filter)
        if dang_filter:
            dang_norm = norm_dang(dang_filter)
            qs_source = [q for q in qs_source if norm_dang(q.get("Dang")) == dang_norm]
            if not qs_source:
                raise RuntimeError(f"Đề này không có câu dạng {dang_filter}. Thầy chọn dạng khác hoặc để Tất cả.")
        access_level = quiz_access_level(qs_source)
        if is_trial() and access_level != "FREE":
            raise RuntimeError("Tài khoản dùng thử chỉ mở được đề FREE, không mở được đề VIP.")
        qs = prepare_quiz_questions(qs_source, shuffle_questions, shuffle_options)
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
        }
        reveal = is_admin()
        return {
            "sid": sid,
            "admin": is_admin(),
            "is_trial": is_trial(),
            "access_level": access_level,
            "can_5050": can_use_5050(),
            "can_submit_score": not is_trial(),
            "shuffle_questions": shuffle_questions,
            "shuffle_options": shuffle_options,
            "level_filter": level_filter,
            "dang_filter": dang_filter,
            "trial_message": "Tài khoản dùng thử: chỉ luyện đề FREE, không nộp/chấm điểm và không xem đáp án/lời giải." if is_trial() else "",
            "questions": [self.public_question(q, i, reveal=reveal) for i, q in enumerate(qs)]
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
                    err_hint += f"\n\nLời giải Sheet (cột R):\n{sheet_loigiai[:600]}"
                return _admin_hint_payload(
                    index,
                    err_hint,
                    correct_sheet,
                    sheet_dapan,
                    sheet_loigiai,
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
                ai_configured=False,
                provider_mode=cfg.get("provider", "AUTO"),
            )

        # VIP / SVIP: giải chi tiết như ADMIN (đủ mục, có đáp án & lời giải gợi ý)
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
            sug = parse_admin_ai_suggestions(body)
            if not sug.get("suggested_dapan") and correct_sheet:
                sug["suggested_dapan"] = correct_sheet
            note = "\n\n💎 Gợi ý VIP: bài giải chi tiết (cùng độ sâu ADMIN)."
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
            if body and not _admin_hint_complete(body.split("💎")[0].strip()):
                note += "\n\n⚠️ AI có thể chưa đủ mục — bấm lại Gợi ý AI hoặc thử sau vài giây."
            return {
                "index": index,
                "exact": False,
                "vip_detailed": True,
                "hint": body + note,
                "hint_truncated": not _admin_hint_complete(body),
                "suggested_dapan": sug.get("suggested_dapan", ""),
                "suggested_loigiai": sug.get("suggested_loigiai", ""),
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
                q, answer, admin_review=True
            )
            if provider_used != "FALLBACK":
                return _vip_detailed_hint_response(
                    hint_text, key_index, provider_used, ai_error, True
                )
        fb = ai_hint_fallback(q, answer)
        return _vip_detailed_hint_response(fb, 0, "FALLBACK", "", bool(has_keys))

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
        fixed_col = {
            "MucDo": 9,        # I
            "Dang": 10,        # J
            "CauHoi": 11,      # K - Nội dung câu hỏi
            "A": 12,           # L
            "B": 13,           # M
            "C": 14,           # N
            "D": 15,           # O
            "DapAn": 16,       # P
            "SaiSo": 17,       # Q
            "LoiGiai": 18,     # R
            "HinhAnh": 20,     # T - link hình ảnh
        }

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
        """ADMIN xóa nguyên dòng câu hỏi khỏi sheet Cau_Hoi và nạp lại dữ liệu."""
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

        # Xóa khỏi RAM và chỉnh lại số dòng các câu phía dưới, không đọc lại cả sheet.
        new_questions = []
        for q in self.questions:
            r = int(q.get("_row") or 0)
            if r == int(row_number):
                continue
            if r > int(row_number):
                q["_row"] = r - 1
            new_questions.append(q)
        self.questions = new_questions
        self.patch_quiz_sessions_after_row_delete(row_number)
        self.rebuild_indexes_after_admin_change()
        return {"ok": True, "deleted": True, "row": row_number, "id": actual_id or question_id}


def shuffle_mcq_options(q: Dict[str, Any]) -> Dict[str, Any]:
    """Xáo trộn phương án A-D của câu trắc nghiệm, giữ đúng đáp án."""
    q = dict(q)
    if norm_dang(q.get("Dang")) != "Trắc nghiệm":
        return q
    pairs = [(L, q.get(L, "")) for L in "ABCD" if clean(q.get(L))]
    if len(pairs) < 2:
        return q
    correct = norm_letter(q.get("DapAn"))
    random.shuffle(pairs)
    for L in "ABCD":
        q[L] = ""
    new_correct = ""
    for i, (old_L, text) in enumerate(pairs):
        new_L = "ABCD"[i]
        q[new_L] = text
        if old_L == correct:
            new_correct = new_L
    if new_correct:
        q["DapAn"] = new_correct
    return q


def prepare_quiz_questions(
    qs: List[Dict[str, Any]],
    shuffle_questions: bool = False,
    shuffle_options: bool = False,
) -> List[Dict[str, Any]]:
    out = [dict(q) for q in qs]
    if shuffle_questions:
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
    """Key trên Render ENV (dùng chung / dự phòng)."""
    keys_local: List[str] = []
    env_names = [f"{prefix}_API_KEY"] + [f"{prefix}_API_KEY_{i}" for i in range(1, 10)]
    for name in env_names:
        v = clean_ai_key_2026(os.environ.get(name, ""))
        if v:
            keys_local.append(v)
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
    t = re.sub(r"\$\s*\$", "", t)
    t = re.sub(r"\$\s*\.", "$.", t)
    return normalize_latex_text(t)


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
        "5": r"5\.\s*ĐÁP ÁN AI KẾT LUẬN",
        "8": r"8\.\s*ĐỀ XUẤT LỜI GIẢI",
    }
    pat = patterns.get(section)
    if not pat:
        return False
    return bool(re.search(pat, str(txt or ""), re.I))


def _admin_hint_complete(txt: str) -> bool:
    return _admin_hint_has_section(txt, "5") and _admin_hint_has_section(txt, "8")


def _merge_admin_continuation(base: str, more: str) -> str:
    base = clean(base)
    more = clean(more)
    if not more:
        return base
    more = re.sub(r"^1\.\s*NHẮC LẠI ĐỀ[\s\S]*?(?=4\.|5\.|6\.|7\.|8\.)", "", more, flags=re.I)
    return (base.rstrip() + "\n\n" + more.lstrip()).strip()


def _finalize_admin_hint_text(txt: str) -> str:
    """ADMIN: không cắt ngắn — chỉ giới hạn an toàn rất cao."""
    txt = clean(txt)
    if len(txt) <= AI_HINT_ADMIN_MAX_CHARS:
        return txt
    return trim_ai_hint_text(txt, AI_HINT_ADMIN_MAX_CHARS)


def build_ai_admin_review_prompt_2026(q: Dict[str, Any], user_answer: Any) -> str:
    block = build_ai_question_block(q, user_answer, include_sheet_answer=True)
    sheet_da = clean(q.get("DapAn", "")) or "(trống)"
    sheet_lg = clean(q.get("LoiGiai", "")) or "(trống)"
    if len(sheet_lg) > 500:
        sheet_lg_show = sheet_lg[:500] + "…"
    else:
        sheet_lg_show = sheet_lg
    dang = effective_dang(q)
    dang_note = ""
    if dang == "Đúng sai":
        dang_note = (
            "- Dạng Đúng/Sai: mục 4 phân tích NGẮN từng ý A/B/C/D (2–4 câu/ý); "
            "mục 5 liệt kê rõ A=Đ/S, B=Đ/S, C=Đ/S, D=Đ/S."
        )
    elif dang == "Trắc nghiệm":
        dang_note = "- Dạng trắc nghiệm: mục 5 phải kết luận một phương án A/B/C/D."
    return "\n".join(
        [
            "ADMIN kiểm tra ngân hàng câu — nhắc đề, dạy cách làm, đối chiếu Sheet.",
            "",
            gemini_prompt_brand_2026(),
            "",
            "QUAN TRỌNG: BẮT BUỘC viết đủ 8 mục, KHÔNG dừng giữa chừng ở mục 4.",
            "Ưu tiên hoàn thành mục 5 (đáp án) và mục 8 (lời giải đề xuất).",
            "Mục 1–3 viết gọn; mục 4–8 đầy đủ nhưng súc tích.",
            dang_note,
            "",
            "Trình bày tiếng Việt, theo ĐÚNG 8 mục sau (giữ nguyên tiêu đề số):",
            "",
            "1. NHẮC LẠI ĐỀ",
            "- Tóm tắt đề bài (giữ số liệu, ký hiệu, yêu cầu cần tìm).",
            "",
            "2. ĐỊNH NGHĨA & CÔNG THỨC",
            "- Định nghĩa/khái niệm then chốt.",
            "- Công thức cần dùng (kèm điều kiện áp dụng, đơn vị).",
            "",
            "3. CÁCH LÀM (LỘ TRÌNH)",
            "- Liệt kê các bước giải theo thứ tự logic.",
            "",
            "4. BÀI GIẢI CHI TIẾT",
            "- Giải đầy đủ; nếu nhiều ý thì từng ý ngắn gọn, không lan man.",
            "",
            "5. ĐÁP ÁN AI KẾT LUẬN",
            "- Nêu rõ đáp án cuối (A/B/C/D, số, hoặc Đ/S từng ý). BẮT BUỘC có mục này.",
            "",
            "6. SO KHỚP SHEET — CỘT P (ĐÁP ÁN)",
            f"- Sheet đang ghi: {sheet_da}",
            "- Kết luận một dòng: KHỚP / KHÔNG KHỚP / SHEET TRỐNG — và giải thích ngắn.",
            "",
            "7. ĐÁNH GIÁ LỜI GIẢI SHEET — CỘT R",
            f"- Sheet đang ghi: {sheet_lg_show}",
            "- Kết luận một dòng: ĐÚNG / THIẾU / SAI / TRỐNG — và giải thích ngắn.",
            "",
            "8. ĐỀ XUẤT LỜI GIẢI CHO SHEET",
            "- Viết lời giải chuẩn để thầy copy vào cột R (nếu Sheet trống hoặc sai).",
            "- Nếu Sheet đã đúng, ghi: «Giữ nguyên lời giải Sheet».",
            "",
            "DỮ LIỆU CÂU:",
            block,
        ]
    )


def parse_admin_ai_suggestions(ai_text: str) -> Dict[str, str]:
    """Tách đáp án / lời giải đề xuất từ bản ADMIN AI kiểm tra."""
    body = str(ai_text or "").split("📋 Tham chiếu Sheet")[0].strip()
    dapan = ""
    loigiai = ""
    m2 = re.search(
        r"5\.\s*ĐÁP ÁN AI KẾT LUẬN\s*(.*?)(?=6\.\s*SO KHỚP|\Z)",
        body,
        re.I | re.S,
    )
    if not m2:
        m2 = re.search(
            r"2\.\s*ĐÁP ÁN AI KẾT LUẬN\s*(.*?)(?=3\.\s*SO KHỚP|\Z)",
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
    if not m5:
        m5 = re.search(r"5\.\s*ĐỀ XUẤT LỜI GIẢI[^\n]*\n(.*)", body, re.I | re.S)
    if m5:
        lg = clean(m5.group(1))
        if lg and "giữ nguyên lời giải sheet" not in lg.lower():
            loigiai = lg
    return {"suggested_dapan": dapan, "suggested_loigiai": loigiai}


def _admin_hint_payload(
    index: int,
    hint: str,
    correct_sheet: str,
    sheet_dapan: str,
    sheet_loigiai: str,
    **extra: Any,
) -> Dict[str, Any]:
    sug = parse_admin_ai_suggestions(hint)
    if not sug.get("suggested_dapan") and correct_sheet:
        sug["suggested_dapan"] = correct_sheet
    body_only = str(hint or "").split("📋 Tham chiếu Sheet")[0]
    return {
        "index": index,
        "exact": False,
        "admin_review": True,
        "hint": hint,
        "hint_truncated": not _admin_hint_complete(body_only),
        "correct": correct_sheet,
        "sheet_dapan": sheet_dapan,
        "sheet_loigiai": sheet_loigiai,
        "suggested_dapan": sug.get("suggested_dapan", ""),
        "suggested_loigiai": sug.get("suggested_loigiai", ""),
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


def ai_hint_from_provider(
    q: Dict[str, Any],
    user_answer: Any,
    admin_review: bool = False,
    vip_formula_only: bool = False,
) -> Tuple[str, int, str, str]:

    cfg = ai_runtime_config()
    openai_keys = load_ai_keys("OPENAI")
    gemini_keys = load_ai_keys("GEMINI")
    provider = cfg["provider"]
    last_error = ""
    if admin_review:
        max_tokens = AI_HINT_ADMIN_MAX_OUTPUT_TOKENS
        max_chars = AI_HINT_ADMIN_MAX_CHARS
    elif vip_formula_only:
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
            "Bạn là chuyên gia kiểm tra ngân hàng câu hỏi. Trả lời tiếng Việt, "
            "BẮT BUỘC đủ 8 mục theo yêu cầu — đặc biệt mục 5 (đáp án) và mục 8 (lời giải). "
            "Không dừng giữa mục 4."
        )
        teacher_prompt = build_ai_admin_review_prompt_2026(q, user_answer)
        temp = 0.1
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
        out = clean(txt)
        if not admin_review or not out or _admin_hint_complete(out):
            return out
        for step in range(AI_HINT_ADMIN_MAX_CONTINUATIONS):
            if _admin_hint_complete(out):
                break
            cont_prompt = (
                "Phản hồi TRƯỚC bị cắt giữa chừng. TIẾP TỤC ngay từ chỗ dừng, "
                "hoàn thành các mục còn thiếu (ưu tiên mục 5 ĐÁP ÁN AI KẾT LUẬN, "
                "mục 6, 7, 8). Không lặp lại nội dung đã viết.\n\n"
                "--- ĐÃ VIẾT ---\n" + out[-4500:]
            )
            more, more_finish, err = _gemini_hint_call(
                api_key, gmodel, sys_prompt, cont_prompt, max_tokens, temp, timeout=40
            )
            if err:
                last_error_local = err
                print(f"[AI_HINT][ADMIN_CONT] step={step+1} err={err[:120]}")
                break
            if not more:
                break
            out = _merge_admin_continuation(out, more)
            finish = more_finish
            print(f"[AI_HINT][ADMIN_CONT] step={step+1} model={gmodel} finish={finish}")
            if _admin_hint_complete(out):
                break
        return out

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
                with urllib.request.urlopen(req, timeout=18) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                txt = (((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content", "")
                txt = _postprocess_hint_text(clean(txt))
                if txt:
                    tag = "ADMIN_REVIEW" if admin_review else "OPENAI"
                    print(f"[AI_HINT][{tag}] using key #{idx}")
                    return txt, idx, "OPENAI", ""
            except Exception as e:
                last_error = _http_error_message(e)
                if _is_quota_or_rate_error(last_error):
                    print(f"[AI_HINT][OPENAI] key #{idx} quota/rate — thử key tiếp")
                    break
                continue
        return "", 0, "OPENAI", last_error

    def try_gemini() -> Tuple[str, int, str, str]:
        nonlocal last_error
        gem_timeout = 40 if admin_review else 22
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
    }

# ============================================================
# HTML
# ============================================================

LOGIN_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Đăng nhập luyện đề</title>
<script>(function(){try{var t=localStorage.getItem('LDVL_THEME')||'light';document.documentElement.setAttribute('data-theme',t==='dark'?'dark':'light')}catch(e){}})();</script>
<style>body{margin:0;background:#f3f6fb;font-family:Arial,sans-serif;color:#0f172a}html[data-theme="dark"] body{background:#0f172a;color:#e2e8f0}html[data-theme="dark"] .box{background:#1e293b;border-color:#334155}html[data-theme="dark"] input{background:#0f172a;color:#e2e8f0;border-color:#475569}html[data-theme="dark"] .hint{color:#94a3b8}.box{max-width:460px;margin:55px auto;background:#fff;border:1px solid #d9e2ef;border-radius:16px;padding:24px;box-shadow:0 8px 30px #0001}.top{background:#1d4ed8;color:#fff;padding:16px 20px;font-weight:800;display:flex;justify-content:space-between;align-items:center}.themeBtn{background:#ffffff22;border:1px solid #ffffff55;color:#fff;padding:5px 10px;border-radius:8px;font-size:15px;font-weight:800;cursor:pointer}input,button{width:100%;padding:12px;margin:8px 0;border-radius:10px;border:1px solid #cbd5e1;font-size:16px}button{background:#1d4ed8;color:white;font-weight:800;cursor:pointer}.err{background:#fee2e2;color:#991b1b;padding:10px;border-radius:10px;margin:8px 0}.ok{background:#dcfce7;color:#166534;padding:10px;border-radius:10px;margin:8px 0}.hint{font-size:13px;color:#64748b;line-height:1.5}.link{display:block;text-align:center;margin-top:12px;color:#1d4ed8;font-weight:800;text-decoration:none}</style></head><body>
<div class="top"><span>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOẠ HỌC</span><button type="button" class="themeBtn" onclick="(function(){var c=document.documentElement.getAttribute('data-theme')||'light';var d=c!=='dark';document.documentElement.setAttribute('data-theme',d?'dark':'light');try{localStorage.setItem('LDVL_THEME',d?'dark':'light')}catch(e){}event.target.textContent=d?'☀️':'🌙'})()">🌙</button></div>
<div class="box"><h2>Đăng nhập học viên</h2>{% if error %}<div class="err">{{error}}</div>{% endif %}{% if msg %}<div class="ok">{{msg}}</div>{% endif %}
<form method="post"><input type="hidden" name="device_id" id="device_id"><label>Mã học sinh / tài khoản</label><input name="mahs" autofocus required placeholder="VD: HS001 hoặc TRIAL_xxxx"><label>Mật khẩu</label><input name="password" type="password" required placeholder="Nhập mật khẩu"><button>Đăng nhập</button></form>
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
<script>window.MathJax={loader:{load:['[tex]/ams']},tex:{packages:{'[+]':['ams']},inlineMath:[["$","$"],["\\(","\\)"]],displayMath:[["$$","$$"],["\\[","\\]"]]},svg:{fontCache:"global"}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>
:root{--blue:#1d4ed8;--border:#d7e0ed;--bg:#f5f7fb;--surface:#fff;--text:#0f172a;--heading:#1e3a8a;--muted:#64748b;--green:#dcfce7;--red:#fee2e2;--yellow:#fff7ed;--exam-bg:#fff7ed;--exam-border:#fed7aa;--exam-text:#9a3412;--exam-timer-bg:#fff;--exam-timer-border:#fdba74;--btn2-bg:#eef2ff;--btn2-color:#1d4ed8;--quiz-timer-bg:#eef2ff;--quiz-timer-color:#1e40af;--quiz-timer-border:#bfdbfe;--shuffle-bg:#eff6ff;--shuffle-border:#93c5fd;--shuffle-text:#1e3a8a;--solution-bg:#fff7ed;--solution-border:#fed7aa;--opt-hover:#f8fafc;--num-answered:#fef3c7;--modal-overlay:#0008;--load-card-bg:#eff6ff;--load-card-border:#93c5fd;--load-warn-bg:#fff7ed;--load-warn-border:#fed7aa;--load-warn-text:#9a3412}html[data-theme="dark"]{--bg:#0f172a;--surface:#1e293b;--text:#e2e8f0;--heading:#93c5fd;--muted:#94a3b8;--border:#334155;--green:#14532d;--red:#450a0a;--yellow:#422006;--exam-bg:#422006;--exam-border:#9a3412;--exam-text:#fed7aa;--exam-timer-bg:#1e293b;--exam-timer-border:#c2410c;--btn2-bg:#1e3a5f;--btn2-color:#bfdbfe;--quiz-timer-bg:#1e3a5f;--quiz-timer-color:#bfdbfe;--quiz-timer-border:#475569;--shuffle-bg:#1e3a5f;--shuffle-border:#3b82f6;--shuffle-text:#bfdbfe;--solution-bg:#422006;--solution-border:#9a3412;--opt-hover:#334155;--num-answered:#422006;--modal-overlay:#000c;--load-card-bg:#1e3a5f;--load-card-border:#3b82f6;--load-warn-bg:#422006;--load-warn-border:#9a3412;--load-warn-text:#fed7aa;color:var(--text)}html[data-theme="dark"] .btnGreen{background:#166534;color:#dcfce7}html[data-theme="dark"] .btnRed{background:#991b1b;color:#fee2e2}html[data-theme="dark"] .correct{color:#86efac!important}html[data-theme="dark"] .wrong{color:#fecaca!important}html[data-theme="dark"] .num.ok{color:#86efac}html[data-theme="dark"] .num.bad{color:#fecaca}*{box-sizing:border-box}html{overflow-x:hidden;-webkit-text-size-adjust:100%;text-size-adjust:100%}body{margin:0;background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif;font-size:15px;overflow-x:hidden;width:100%;max-width:100vw}.themeBtn{background:#ffffff22;border:1px solid #ffffff55;color:#fff;padding:5px 10px;border-radius:8px;font-size:15px;font-weight:800;cursor:pointer;margin-right:6px}.top{position:sticky;top:0;z-index:9;background:var(--blue);color:#fff;padding:10px 14px;box-shadow:0 2px 8px #0002;width:100%;max-width:100vw}.topRow{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between}.top h1{font-size:18px;margin:0;flex:1;min-width:200px}.topRight{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;font-size:13px}.top a{color:#fff}.adminBar{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center;margin-right:4px}.adminTopBtn{background:#dcfce7;border:1px solid #86efac;color:#166534;padding:5px 10px;border-radius:8px;font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap}.adminTopBtn2{background:#ffffff22;border:1px solid #ffffff55;color:#fff}.adminTopBtn:hover{filter:brightness(1.05)}.adminTopBtn:disabled{opacity:.55;cursor:not-allowed}.examStrip{position:sticky;top:56px;z-index:8;display:flex;gap:10px;align-items:center;justify-content:center;padding:8px 10px;background:var(--exam-bg);border-top:1px solid var(--exam-border);border-bottom:1px solid var(--exam-border);color:var(--exam-text);font-weight:800}.examStrip .timer{background:var(--exam-timer-bg);border:1px solid var(--exam-timer-border);border-radius:999px;padding:2px 10px}.wrap{max-width:1420px;margin:auto;padding:12px;width:100%;min-width:0}.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px;margin-bottom:12px;box-shadow:0 1px 4px #0001}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:4px;min-width:160px;flex:1}.field label{font-weight:700;font-size:12px}select,input,textarea,button{font-family:inherit;font-size:14px;border:1px solid var(--border);border-radius:8px;padding:9px 10px;background:var(--surface);color:var(--text)}button{cursor:pointer;font-weight:800}.btn{background:var(--blue);border-color:var(--blue);color:#fff}.btn2{background:var(--btn2-bg);color:var(--btn2-color)}.btnGreen{background:#dcfce7;color:#166534}.btnRed{background:#fee2e2;color:#991b1b}.btnStartStrong{background:linear-gradient(135deg,#2563eb,#7c3aed);border-color:#1e40af;color:#fff;box-shadow:0 6px 16px #1e40af44}.btnStartStrong:hover{filter:brightness(1.03)}.quizTimer{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;background:var(--quiz-timer-bg);color:var(--quiz-timer-color);font-weight:800;border:1px solid var(--quiz-timer-border)}.shuffleHint{margin-top:8px;background:var(--shuffle-bg);border:1px dashed var(--shuffle-border);color:var(--shuffle-text);padding:7px 9px;border-radius:8px;font-size:12px;font-weight:700}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}.card{border:1px solid var(--border);border-radius:12px;background:var(--surface);padding:12px}.card h3{margin:0 0 8px;color:var(--heading)}.tag{display:inline-block;background:var(--btn2-bg);color:var(--btn2-color);padding:3px 8px;border-radius:999px;font-size:12px;font-weight:800;margin:2px}.line{height:1px;background:var(--border);margin:10px 0}.muted{color:var(--muted)}.hide{display:none!important}.quizLayout{display:grid;grid-template-columns:1fr 270px;gap:12px}.qid{font-size:19px;font-weight:800}.qbox{border:1px solid var(--border);background:var(--surface);border-radius:8px;padding:14px;min-height:150px;line-height:1.55;font-size:18px;color:var(--text)}.qimgWrap{display:block;width:100%;margin:10px 0 12px;clear:both}.qimg{max-width:100%;width:auto;height:auto;display:block;margin:0 auto;object-fit:contain;border:1px solid var(--border);border-radius:8px;background:var(--surface)}.qimgErr{margin:10px 0;padding:10px;border:1px solid #fed7aa;background:#fff7ed;border-radius:8px;color:#9a3412;font-size:13px}.opt{display:flex;gap:8px;align-items:flex-start;padding:10px;border-radius:10px;border:1px solid transparent;margin:7px 0;background:var(--surface);color:var(--text);position:relative;z-index:1}.opt:hover{background:var(--opt-hover)}.correct{background:var(--green)!important;border-color:#86efac!important}.wrong{background:var(--red)!important;border-color:#fecaca!important}.hidden5050{opacity:.25;pointer-events:none;text-decoration:line-through}.solution{background:var(--solution-bg);border:1px solid var(--solution-border);border-radius:10px;padding:12px;margin-top:12px;color:var(--text)}.latex-list{margin:8px 0 8px 22px;padding:0}.latex-list li{margin:6px 0;line-height:1.55}.hintAdminBody{width:100%;min-height:160px;max-height:520px;overflow:auto;font-size:15px;line-height:1.55;margin-top:8px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--surface);user-select:text;-webkit-user-select:text}.btnHintLoading{opacity:.82;cursor:wait!important;pointer-events:none}.hintSpin{display:inline-block;width:14px;height:14px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:hintSpin .75s linear infinite;vertical-align:-2px;margin-right:6px}.hintBoxLoading{border-color:#93c5fd!important;background:linear-gradient(180deg,var(--shuffle-bg),var(--surface))!important;animation:hintPulse 1.6s ease-in-out infinite}.hintLoadingPanel{display:flex;gap:12px;align-items:flex-start;padding:10px 4px 6px}.hintSpinBig{width:30px;height:30px;border:3px solid #93c5fd;border-top-color:var(--blue);border-radius:50%;animation:hintSpin .8s linear infinite;flex-shrink:0}@keyframes hintSpin{to{transform:rotate(360deg)}}@keyframes hintPulse{0%,100%{box-shadow:0 0 0 0 #3b82f633}50%{box-shadow:0 0 0 6px #3b82f611}}.hintAdminActions{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.hintAdminActions button{font-size:12px;padding:6px 10px;width:auto;margin:0}.navNums{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.num{padding:8px 0;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text)}.num.active{outline:3px solid #93c5fd}.num.answered{background:var(--num-answered)}.num.ok{background:var(--green);color:#166534}.num.bad{background:var(--red);color:#991b1b}.tfrow{display:grid;grid-template-columns:26px minmax(0,1fr) auto;gap:6px 8px;align-items:start;border:1px solid var(--border);border-radius:10px;padding:8px 10px;margin:7px 0}.tfrow>b{padding-top:2px}.tfStmt{min-width:0;line-height:1.45;font-size:15px;word-break:break-word}.tfOpts{display:flex;gap:6px;align-items:center;justify-content:flex-end;flex-shrink:0}.tfOptsHead{display:none}.tfOpt{display:inline-flex;align-items:center;justify-content:center;gap:4px;min-width:52px;padding:5px 10px;border:1px solid var(--border);border-radius:8px;background:var(--surface);font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap;user-select:none;position:relative}.tfOpt:has(input:checked){border-color:#93c5fd;background:var(--btn2-bg);color:var(--btn2-color)}.tfOpt input{width:13px;height:13px;margin:0;flex-shrink:0}.tfLbl{line-height:1}.tfLblShort{display:none}.tfLblFull{display:inline}.modal{position:fixed;inset:0;background:var(--modal-overlay);z-index:20;display:flex;align-items:center;justify-content:center;padding:15px}.modalBox{background:var(--surface);color:var(--text);border-radius:14px;padding:16px;max-width:900px;width:100%;max-height:90vh;overflow:auto;border:1px solid var(--border)}.editGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.editGrid textarea{min-height:80px;width:100%}.loadCard{border-color:var(--load-card-border)!important;background:var(--load-card-bg)!important}.loadWarn{background:var(--load-warn-bg);border:1px solid var(--load-warn-border);border-radius:10px;padding:10px;margin:10px 0;color:var(--load-warn-text)}.loadErr{color:#ef4444}#fsOnlyTools{display:none}body.fullde-mode{overflow:hidden}body.fullde-mode .top,body.fullde-mode #examStrip,body.fullde-mode #home{display:none!important}body.fullde-mode .wrap{max-width:none!important;margin:0!important;padding:0!important;width:100%!important}body.fullde-mode #quiz
{display:flex!important;flex-direction:column;position:fixed;inset:0;z-index:9999;background:var(--bg);padding:0;margin:0;overflow:hidden;width:100vw!important;max-width:none!important}body.fullde-mode #quiz>.panel:first-child{display:none}body.fullde-mode #quiz .quizLayout{flex:1;display:grid;grid-template-columns:minmax(0,1fr) 100px;gap:0;width:100%;max-width:none;height:100%;min-height:0;margin:0}body.fullde-mode #quiz .quizLayout>div:first-child{min-width:0;height:100%;display:flex;flex-direction:column}body.fullde-mode #quiz .quizLayout>div:first-child>.panel{flex:1;display:flex;flex-direction:column;margin:0;border-radius:0;border-left:none;border-right:none;border-top:none;width:100%;max-width:none;min-height:0;overflow:auto}body.fullde-mode #quiz .quizLayout>div:last-child{display:flex!important;height:100%;min-height:0}body.fullde-mode #quiz .quizLayout>div:last-child>.panel{margin:0;border-radius:0;border-top:none;border-right:none;border-bottom:none;height:100%;padding:6px;display:flex;flex-direction:column;min-height:0;overflow:hidden}body.fullde-mode #quiz .quizLayout>div:last-child .line,body.fullde-mode #quiz .quizLayout>div:last-child .muted{display:none!important}body.fullde-mode #quiz .quizLayout>div:last-child .fsNavTitle{display:block!important;font-size:11px;text-align:center;margin:0 0 4px;font-weight:800;color:var(--muted);flex-shrink:0}body.fullde-mode #navNums{grid-template-columns:repeat(3,1fr);gap:3px;overflow-y:auto;flex:1;align-content:start}body.fullde-mode #navNums .num{padding:4px 0;font-size:11px;line-height:1.1}body.fullde-mode #fsOnlyTools{display:flex;position:sticky;top:0;z-index:5;justify-content:flex-end;gap:8px;flex-wrap:wrap;background:var(--surface);padding:6px 8px;border-bottom:1px solid var(--border);flex-shrink:0}body.fullde-mode #qid{font-size:15px;padding:0 8px;flex-shrink:0}body.fullde-mode #quiz .quizLayout>div:first-child .row:first-child{flex-shrink:0;padding:4px 8px 0}body.fullde-mode #qtext,body.fullde-mode #options,body.fullde-mode #solution,body.fullde-mode #hintBox{width:100%}body.fullde-mode #qtext{flex:0 0 auto;min-height:0;overflow:visible}body.fullde-mode #options{flex:0 0 auto;margin-top:8px;padding:0 8px 4px;position:relative;z-index:2;background:var(--bg)}body.fullde-mode #qtext .qimg{max-height:min(42vh,280px)}body.fullde-mode #hintBox{flex-shrink:0;max-height:38vh;overflow:auto;margin-top:8px}body.fullde-mode #fsOnlyTools button{font-size:12px;padding:5px 8px;white-space:nowrap}body.fullde-mode #fsOnlyTools .quizTimer{font-size:11px;padding:3px 8px}body.fullde-mode #hintBox .hintAdminBody{max-height:28vh;font-size:14px}body.fullde-mode #quizActions{display:none!important}body.fullde-mode #btnRetry,body.fullde-mode #btnEdit,body.fullde-mode #btnSubmit{display:none!important}@media(max-width:760px){body.fullde-mode #quiz .quizLayout{grid-template-columns:1fr;grid-template-rows:minmax(0,1fr) auto}body.fullde-mode #quiz .quizLayout>div:last-child{max-height:96px}body.fullde-mode #navNums{grid-template-columns:repeat(8,1fr);overflow-x:auto;overflow-y:hidden}body.fullde-mode #fsOnlyTools{gap:4px;padding:4px 6px;flex-wrap:wrap;justify-content:flex-start}body.fullde-mode #fsOnlyTools button{font-size:10px!important;padding:4px 6px!important}body.fullde-mode #fsOnlyTools .quizTimer{font-size:10px;padding:2px 6px}body.fullde-mode #qid{font-size:12px;line-height:1.3}body.fullde-mode #qtext{font-size:15px;padding:8px 10px!important}body.fullde-mode #qtext .qimg{max-height:min(36vh,220px);margin:8px auto 10px}body.fullde-mode #options{padding:0 6px 6px}body.fullde-mode .opt{padding:7px 8px;margin:4px 0;font-size:14px}body.fullde-mode #quiz .quizLayout>div:first-child>.panel{padding-bottom:6px}.wrap{padding:8px}.top{padding:8px 10px}.top h1{font-size:14px;min-width:0;flex:1 1 100%}.topRight{font-size:11px;gap:4px 8px}.adminTopBtn{font-size:10px;padding:4px 7px}.themeBtn{font-size:12px;padding:4px 8px}.examStrip{top:48px;padding:6px 8px;font-size:12px;flex-wrap:wrap}.panel{padding:10px;margin-bottom:10px;min-width:0}#quiz>.panel:first-child{flex-wrap:wrap;gap:8px}#quiz>.panel:first-child>div{width:100%}#resultBox{font-size:14px!important}.quizLayout>div{min-width:0}#quiz .panel>.row:first-child{flex-direction:column;align-items:stretch;gap:8px}#qid{font-size:13px;line-height:1.35;word-break:break-word}#quizActions{display:flex;flex-wrap:wrap;gap:4px;width:100%}#quizActions button{font-size:10px;padding:5px 7px;flex:0 1 auto}#quiz .panel>.row:last-child button{font-size:13px;padding:8px 12px;flex:1}.qbox{font-size:15px;padding:10px;min-height:0;overflow-wrap:anywhere}.opt{padding:8px;font-size:14px;margin:5px 0}.qimg{max-height:min(40vh,240px)}.tfrow{grid-template-columns:22px minmax(0,1fr) 34px;grid-template-areas:"lbl stmt opts";gap:4px 6px;padding:7px 8px;align-items:start}.tfrow>b{grid-area:lbl}.tfStmt{grid-area:stmt;font-size:14px}.tfOpts{grid-area:opts;flex-direction:column;justify-content:flex-start;align-items:stretch;gap:3px;padding:0;width:34px}.tfOptsHead{display:grid;grid-template-columns:22px minmax(0,1fr) 34px;gap:4px 6px;margin:0 0 4px;padding:0 8px;font-size:10px;font-weight:800;color:var(--muted);align-items:center}.tfColHead{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;line-height:1.15;text-align:center}.tfOptsHead .tfLblShort{display:flex;flex-direction:column;align-items:center}.tfOptsHead .tfLblFull{display:none}.tfLblFull{display:none}.tfLblShort{display:inline}.tfOpt{flex:0;width:100%;max-width:none;min-width:0;padding:5px 2px;font-size:12px;border-radius:6px;text-align:center}.tfOpt input{position:absolute;opacity:0;width:0;height:0;margin:0}}html:fullscreen,body:fullscreen{background:var(--bg)}@media(max-width:900px){.quizLayout{grid-template-columns:1fr}.editGrid{grid-template-columns:1fr}.qbox{font-size:16px}.top h1{font-size:16px}.examStrip{top:52px;font-size:13px}}
</style></head>
<body><div class="top"><div class="topRow"><h1>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</h1><div class="topRight"><span id="adminBar" class="adminBar hide"><button type="button" id="syncBtn" class="adminTopBtn" onclick="syncData()">🔄 Đồng bộ Sheet</button><button type="button" id="testAiBtn" class="adminTopBtn adminTopBtn2" onclick="testServerAiKey()">🧪 Test AI</button><button type="button" id="adminEditBtn" class="adminTopBtn adminTopBtn2 hide" onclick="openEdit()">✏️ Sửa câu</button></span><span id="info">Đang nạp...</span> | <span id="me"></span> | <button type="button" id="btnTheme" class="themeBtn" onclick="toggleTheme()" title="Chuyển giao diện tối">🌙</button> <a href="/logout">Thoát</a></div></div></div>
<div id="examStrip" class="examStrip"><span id="examMsg">📢 Thông báo kỳ thi</span><span id="examTimer" class="timer"></span></div>
<div class="wrap">
<div id="home"><div class="panel"><b>Thiết lập luyện tập</b><div class="row" style="margin-top:10px"><div class="field"><label>Môn</label><select id="fMon"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="fLop"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="fChuong"><option value="">Tất cả</option></select></div><div class="field"><label>Bài học</label><select id="fBaiHoc"><option value="">Tất cả</option></select></div><div class="field"><label>Bộ đề</label><select id="fBoDe"><option value="">Tất cả</option></select></div><div class="field"><label>Mức độ</label><select id="fMucDo"><option value="">Tất cả</option><option value="NB">NB</option><option value="TH">TH</option><option value="VD">VD</option><option value="VDC">VDC</option></select></div><div class="field"><label>Dạng câu</label><select id="fDang"><option value="">Tất cả</option><option value="Trắc nghiệm">Trắc nghiệm</option><option value="Đúng sai">Đúng sai</option><option value="Trả lời ngắn">Trả lời ngắn</option><option value="Tự luận">Tự luận</option></select></div><div class="field"><label>Tìm nhanh</label><input id="fSearch" placeholder="Nhập từ khóa..."></div><button class="btn" onclick="renderCatalog()">Lọc đề</button></div></div><div id="aiKeyPanel" class="panel hide"><b>🔑 Key AI của tôi (Gemini)</b><p class="muted" style="margin:6px 0 10px">Chỉ dùng key <b>AIzaSy...</b> từ <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">Google AI Studio</a> (Create API key). <b>Không</b> dùng key <b>AQ...</b> hay key Google Cloud khác. Key của bạn được ưu tiên; không có thì dùng key server Render.</p><textarea id="myApiKeys" rows="3" style="width:100%;min-height:72px;font-family:Consolas,monospace" placeholder="AIzaSy...&#10;(có thể nhiều dòng — tự đổi khi hết quota)"></textarea><div class="row" style="margin-top:8px;flex-wrap:wrap"><button type="button" class="btn2" onclick="testMyAiKey()">🧪 Test key</button><button type="button" class="btnGreen" onclick="saveMyAiKey()">💾 Lưu key</button><button type="button" class="btn2" onclick="clearMyAiKey()">🗑 Xóa key của tôi</button></div><div id="aiKeyStatus" class="muted" style="margin-top:8px;font-size:13px"></div></div><div class="panel"><b>Mục lục đề</b> <span id="countCat" class="muted"></span><div id="catalog" class="grid" style="margin-top:10px"></div></div></div>
<div id="quiz" class="hide"><div class="panel row" style="justify-content:space-between"><div><button class="btn2" onclick="backHome()">← Về mục lục</button> <span id="quizTitle" style="font-weight:800"></span> <span id="shuffleBadge" class="tag hide"></span></div><div style="display:flex;gap:10px;align-items:center"><div id="quizTimer" class="quizTimer">⏱ <span id="quizTimerText">00:00</span></div><div id="resultBox" style="font-weight:800;font-size:18px"></div></div></div><div class="quizLayout"><div><div class="panel"><div class="row" style="justify-content:space-between;align-items:center"><div class="qid" id="qid"></div><div id="quizActions"><button id="btn5050" class="btnGreen" onclick="use5050()">Loại 2 câu sai</button><button id="btnHint" class="btn2" onclick="requestHint()">💡 Gợi ý AI</button><button id="btnRetry" class="btnStartStrong" onclick="openRetryModal()">🔁 Làm lại đề</button><button id="btnPresent" class="btn2" onclick="toggleQuizFullscreen()">📽 Full màn hình</button><button id="btnEdit" class="btn2 hide" onclick="openEdit()">ADMIN: Sửa câu</button><button id="btnSubmit" class="btn" onclick="submitQuiz()">Nộp bài</button></div></div><div id="fsOnlyTools"><div id="fsQuizTimer" class="quizTimer">⏱ <span id="fsQuizTimerText">00:00</span></div><button id="btnFsSync" class="btn2 hide" onclick="syncData()">🔄 Đồng bộ</button><button id="btnFsEdit" class="btn2 hide" onclick="openEdit()">✏️ Sửa câu</button><button id="btnFs5050" class="btnGreen" onclick="use5050()">Loại 2 câu sai</button><button id="btnFsHint" class="btn2" onclick="requestHint()">💡 Gợi ý AI</button><button class="btn2" onclick="toggleAnswerInFullscreen()">🔎 Ẩn/Hiện đáp án</button><button class="btn2" onclick="toggleExplainInFullscreen()">📘 Ẩn/Hiện lời giải</button><button type="button" id="btnFsTheme" class="btn2" onclick="toggleTheme()">🌙 Tối</button><button class="btn2" onclick="toggleQuizFullscreen()">⤢ Thoát full</button></div><div id="qtext" class="qbox"></div><div id="options"></div><div id="solution" class="solution hide"></div><div id="hintBox" class="solution hide"></div><div class="row" style="justify-content:space-between;margin-top:12px"><button onclick="prevQ()">← Câu trước</button><button onclick="nextQ()">Câu sau →</button></div></div></div><div class="panel fsNavPanel"><b class="fsNavTitle">Bảng câu hỏi</b><div id="navNums" class="navNums" style="margin-top:10px"></div><div class="line"></div><div class="muted">ADMIN vào đề sẽ thấy đáp án/lời giải ngay và được sửa câu.</div></div></div></div>
</div><div id="startModal" class="modal hide"><div class="modalBox" style="max-width:520px"><h3 id="startModalTitle">Thiết lập làm bài</h3><p class="muted">Chọn cách xáo trộn để tự rèn luyện. Có thể giữ nguyên thứ tự như đề gốc.</p><div style="display:flex;flex-direction:column;gap:10px;margin:14px 0"><label style="display:flex;gap:8px;align-items:flex-start;padding:10px;border:1px solid var(--border);border-radius:10px"><input type="checkbox" id="chkShuffleQ"> <span><b>Xáo trộn câu hỏi</b><br><span class="muted">Đổi thứ tự các câu trong đề.</span></span></label><label style="display:flex;gap:8px;align-items:flex-start;padding:10px;border:1px solid var(--border);border-radius:10px"><input type="checkbox" id="chkShuffleA"> <span><b>Xáo trộn đáp án</b><br><span class="muted">Chỉ áp dụng câu trắc nghiệm A-B-C-D.</span></span></label></div><div class="row" style="justify-content:flex-end;gap:8px"><button onclick="closeStartModal()">Hủy</button><button class="btn2" onclick="pickShufflePreset('none')">Giữ nguyên</button><button class="btn" onclick="confirmStartQuiz()">Bắt đầu</button></div></div></div><div id="modal" class="modal hide"><div class="modalBox"><h3>ADMIN: Sửa câu hỏi</h3><div id="editForm" class="editGrid"></div><div class="row" style="justify-content:space-between;margin-top:12px"><button class="btnRed" onclick="deleteQuestion()">Xóa câu này khỏi Google Sheet</button><div><button onclick="closeEdit()">Hủy</button><button class="btn" onclick="saveEdit()">Lưu vào Google Sheet</button></div></div><div class="muted" style="margin-top:8px">Xóa liên tiếp được — app tự cập nhật số dòng Sheet, không cần đồng bộ lại sau mỗi lần xóa. Chỉ bấm Đồng bộ khi sửa trực tiếp trên Google Sheet.</div></div></div>
<script>
let META=null,CATALOG=[],USER={},SID='',QUESTIONS=[],CUR=0,ANSWERS={},SUBMITTED=false,RESULTS={},CHECKED={},LOCKED_Q={},CURRENT_MADE='',CURRENT_LEVEL='',CURRENT_DANG='',START_IS_RETRY=false,QUIZ_ELAPSED=0,QUIZ_TIMER=null,FS_ANS_FORCE=null,FS_EXP_FORCE=null,FULLDE_ON=false,FS_NAV_HIDDEN=false,COMPLETED_NOTICE=false,HINT_BY_Q={},HINT_LOADING=false,HINT_LOADING_Q=null;
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
        "html[data-theme='dark'] .tag{background:linear-gradient(135deg,#1e3a5f,#1d4ed8);color:#e0ecff;border-color:#3b82f6}";
    document.head.appendChild(st);
}
function esc(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])).replace(/\n/g,'<br>')}
function escHtmlKeepMath(s){let out='',i=0,n=String(s||'').length;while(i<n){let d1=s.indexOf('$',i),d2=d1>=0?s.indexOf('$',d1+1):-1;if(d1<0){out+=esc(s.slice(i));break}out+=esc(s.slice(i,d1));if(d2<0){out+=esc(s.slice(d1));break}out+=s.slice(d1,d2+1);i=d2+1}return out}
function stripLatexListMarkup(s){s=String(s||'');s=s.replace(/\\begin\s*\{\s*enumerate\s*\}/gi,'');s=s.replace(/\\end\s*\{\s*enumerate\s*\}/gi,'');s=s.replace(/\\begin\s*\{\s*itemize\s*\}/gi,'');s=s.replace(/\\end\s*\{\s*itemize\s*\}/gi,'');s=s.replace(/\\item\s*/gi,'\n• ');s=s.replace(/\\item(?=[A-Za-zÀ-ỹĐđ])/gi,'\n• ');return s}
function fixPlainTextGaps(s){return String(s||'').replace(/(\d)([Nn]ên|[Đđ]iểm)/g,'$1 $2').replace(/(\))([A-Za-zÀ-ỹĐđ])/g,'$1 $2')}
function fixOneMathInner(inner){if(!inner)return inner;inner=inner.replace(/\)\s*\((\d[\d;\s,.\-]*)\)/g,')$ $( $1)$');inner=inner.replace(/\$\(([^)]+)\)(thuộc|mặt|phẳng|nên|điểm)/gi,'$( $1)$ $2');inner=inner.replace(/\(([^)]+)\)(thỏa|mãn|phương|trình|nên|điểm|thuộc|mặt|phẳng|khẳng|tọa|độ)/gi,'($1)$ $2');inner=inner.replace(/(=[\d.\-+]+)\s*(nên|điểm|thuộc|mặt|phẳng|khẳng|tọa)/gi,'$1$ $2');inner=inner.replace(/\)(thỏa|mãn|nên|điểm|thuộc|mặt|phẳng)/gi,') $1');inner=inner.replace(/(\d)([A-Za-zÀ-ỹĐđ][a-zà-ỹà-ỹ]{2,})/g,'$1 $2');inner=inner.replace(/(\))([A-Za-zÀ-ỹĐđ][a-zà-ỹà-ỹ]{2,})/g,'$1 $2');inner=inner.replace(/\(\((\\?[a-zA-Z]+)\)\)/g,'$1');return inner}
function fixMergedInlineMath(t){t=String(t||'');if(t.indexOf('$')<0)return fixPlainTextGaps(t);let out='',i=0;while(i<t.length){let d1=t.indexOf('$',i);if(d1<0){out+=fixPlainTextGaps(t.slice(i));break}out+=fixPlainTextGaps(t.slice(i,d1));let d2=t.indexOf('$',d1+1);if(d2<0){out+=t.slice(d1);break}out+='$'+fixOneMathInner(t.slice(d1+1,d2))+'$';i=d2+1}return out}
function normalizeLatexDelimiters(s){s=String(s||'');s=s.replace(/\$\{\s*([^}$\n]+?)\s*\}\s*\$/g,'$( $1 )$');s=s.replace(/\$\{\s*([^}$\n]+?)\s*\}/g,'$( $1 )$');s=s.replace(/\{\s*\(\s*([^}]+?)\s*\)\s*\}/g,function(m,g1,off,full){if(off>0&&full[off-1]==='$')return m;if(off+m.length<full.length&&full[off+m.length]==='$')return m;return '$( '+g1+' )$'});s=s.replace(/\$\(\((\\?[a-zA-Z]+)\)\)\$\.?/g,'$$$1$.');s=s.replace(/\$\(\((\\?[a-zA-Z]+)\)\)(?!\$)/g,'$$$1$');s=fixMergedInlineMath(s);s=s.replace(/(\$[^$\n]+?\$)\$+/g,'$1');s=s.replace(/\$\s*\$/g,' ');s=s.replace(/\$([^$]*)\$/g,function(_,inner){return '$'+String(inner).replace(/\\\\/g,'\\')+'$'});return s}
function readLatexBracedContent(s,bracePos){if(bracePos<0||bracePos>=s.length||s[bracePos]!=='{')return null;let depth=0;for(let i=bracePos;i<s.length;i++){let c=s[i];if(c==='{')depth++;else if(c==='}'){depth--;if(depth===0)return{content:s.slice(bracePos+1,i),end:i}}}return null}
function normalizeLatexTextCmds(s){s=String(s||'');s=s.replace(/\\{2,}(textbf|textit|emph|underline)\s*\{/gi,'\\$1{');s=s.replace(/(^|[^\\$])(textbf|textit|emph|underline)\s*\{/gi,'$1\\$2{');return s}
function replaceLatexFmtInPlain(s){s=normalizeLatexTextCmds(s);let cmds=[{re:/\\textbf\s*\{/gi,o:'@@B@@',c:'@@/B@@'},{re:/\\textit\s*\{/gi,o:'@@I@@',c:'@@/I@@'},{re:/\\emph\s*\{/gi,o:'@@I@@',c:'@@/I@@'},{re:/\\underline\s*\{/gi,o:'@@U@@',c:'@@/U@@'}];let loop=true;while(loop){loop=false;for(let cmd of cmds){cmd.re.lastIndex=0;let m=cmd.re.exec(s);if(!m)continue;let idx=m.index,bracePos=idx+m[0].length-1,got=readLatexBracedContent(s,bracePos);if(!got)continue;let inner=replaceLatexFmtInPlain(got.content);s=s.slice(0,idx)+cmd.o+inner+cmd.c+s.slice(got.end+1);loop=true;break}}return s}
function applyFmtOutsideMath(s,fn){let out='',i=0,n=String(s||'').length;while(i<n){let d1=s.indexOf('$',i);if(d1<0){out+=fn(s.slice(i));break}out+=fn(s.slice(i,d1));let d2=s.indexOf('$',d1+1);if(d2<0){out+=s.slice(d1);break}out+=s.slice(d1,d2+1);i=d2+1}return out}
function applyLatexTextFmtOutsideMath(s){return applyFmtOutsideMath(s,replaceLatexFmtInPlain)}
function applyMarkdownBoldOutsideMath(s){return applyFmtOutsideMath(s,x=>x.replace(/\*\*([^*\n]+)\*\*/g,'@@B@@$1@@/B@@'))}
function finalizeRichTokens(s){return s.replace(/@@OL@@/g,'<ol class="latex-list">').replace(/@@\/OL@@/g,'</ol>').replace(/@@UL@@/g,'<ul class="latex-list">').replace(/@@\/UL@@/g,'</ul>').replace(/@@LI@@/g,'<li>').replace(/@@\/LI@@/g,'</li>').replace(/@@B@@/g,'<b>').replace(/@@\/B@@/g,'</b>').replace(/@@I@@/g,'<i>').replace(/@@\/I@@/g,'</i>').replace(/@@U@@/g,'<u>').replace(/@@\/U@@/g,'</u>')}
function renderRichText(s){s=String(s||'').trim();s=s.replace(/\?\?\s*/g,'');s=stripLatexListMarkup(s);s=normalizeLatexDelimiters(s);s=s.replace(/\\begin\{enumerate\}([\s\S]*?)\\end\{enumerate\}/gi,function(_,b){let items=b.split(/\\item\s*/i).map(x=>x.trim()).filter(Boolean);return '@@OL@@'+items.map(it=>'@@LI@@'+it+'@@/LI@@').join('')+'@@/OL@@'});s=s.replace(/\\begin\{itemize\}([\s\S]*?)\\end\{itemize\}/gi,function(_,b){let items=b.split(/\\item\s*/i).map(x=>x.trim()).filter(Boolean);return '@@UL@@'+items.map(it=>'@@LI@@'+it+'@@/LI@@').join('')+'@@/UL@@'});s=s.replace(/\\item\s*/gi,'<br>• ');s=s.replace(/\\item(?=[A-Za-zÀ-ỹĐđ])/gi,'<br>• ');s=applyLatexTextFmtOutsideMath(s);s=applyMarkdownBoldOutsideMath(s);s=escHtmlKeepMath(s);return finalizeRichTokens(s)}
function escAttr(s){return String(s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function shortText(s,n=90){s=String(s||'').replace(/\s+/g,' ').trim();return s.length>n?s.slice(0,n-1)+'…':s}
function normText(s){return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'d')}
function normDangClient(s){let k=normText(s||'').replace(/[\/\\-]/g,' ');let k2=k.replace(/\s+/g,'');if(/dung\s*sai|dungsai|d\/s|true\s*false|truefalse/.test(k)||k2.includes('ds')||/\b(ds|tf)\b/.test(k))return 'Đúng sai';if(/tra\s*loi\s*ngan|short|tln|shortans/.test(k))return 'Trả lời ngắn';if(/tu\s*luan|essay/.test(k)||k==='tl')return 'Tự luận';if(/trac\s*nghiem|tracnghiem|mcq|multiple\s*choice/.test(k)||k==='tn'||k==='tn4')return 'Trắc nghiệm';return 'Trắc nghiệm'}
function tfTokenClient(p){let t=normText(p);if(!String(p||'').trim())return '';if(String(p).trim()==='Đ'||String(p).trim()==='D'||t==='d'||t==='dung'||t==='true')return 'Đ';if(String(p).trim()==='S'||t==='s'||t==='sai'||t==='false')return 'S';return ''}
function parseTfClient(v){let raw=String(v||'').trim();if(!raw)return [];let parts=raw.split(/[,;|/\n]+/).map(x=>x.trim()).filter(Boolean);if(parts.length>=2){let out=parts.map(tfTokenClient);if(out.filter(x=>x==='Đ'||x==='S').length>=2)return out}let s=raw.toUpperCase().replace(/\u0110/g,'D').replace(/\u0111/g,'D').replace(/DUNG/g,'D').replace(/TRUE/g,'D').replace(/SAI/g,'S').replace(/FALSE/g,'S');return (s.match(/[DSĐ]/g)||[]).map(c=>(c==='S'?'S':'Đ')).slice(0,4)}
function hasOptsClient(q){return ['A','B','C','D'].filter(L=>String((q||{})[L]||'').trim()).length>=2}
function looksDsAnswer(v){let raw=String(v||'').trim();if(!raw)return false;if(/^[ABCD]$/i.test(raw.replace(/\s/g,'')))return false;return parseTfClient(raw).filter(x=>x==='Đ'||x==='S').length>=2}
function isMcqLetter(v){let raw=String(v||'').trim().toUpperCase().replace(/\u0110/g,'D');return /^[ABCD]$/.test(raw)}
function resolveDang(q){if(!q)return 'Trắc nghiệm';let rawCol=String(q.Dang||'').trim();let dc=normDangClient(rawCol);if(dc==='Đúng sai'||dc==='Trả lời ngắn'||dc==='Tự luận')return dc;if(looksDsAnswer(q.DapAn)&&hasOptsClient(q))return 'Đúng sai';if(isMcqLetter(q.DapAn)&&hasOptsClient(q))return 'Trắc nghiệm';if(rawCol)return dc;return 'Trắc nghiệm'}
function applyResolvedDang(q){if(!q)return q;q.Dang=resolveDang(q);return q}
function isQuestionDone(i){let q=QUESTIONS[i];if(!q)return false;q=applyResolvedDang(q);let a=ANSWERS[i];if(q.Dang=='Trắc nghiệm')return !!String(a||'').trim();if(q.Dang=='Đúng sai'){if(!Array.isArray(a))return false;let req=0;for(let L of ['A','B','C','D'])if(q[L])req++;let filled=a.filter(v=>!!String(v||'').trim()).length;return req>0&&filled>=req}return !!String(a||'').trim()}
function countDone(){let n=0;for(let i=0;i<QUESTIONS.length;i++)if(isQuestionDone(i))n++;return n}
function notifyDoneIfNeeded(){if(SUBMITTED||COMPLETED_NOTICE||!QUESTIONS.length)return;let done=countDone();if(done>=QUESTIONS.length){COMPLETED_NOTICE=true;alert('✅ Đã làm hết đề. Thầy/các em có thể xem lại rồi bấm Nộp bài.')}} 
function val(id){return document.getElementById(id).value}
function typeset(els){if(window.MathJax&&MathJax.typesetPromise){let t=els?(Array.isArray(els)?els:[els]):undefined;return MathJax.typesetPromise(t).catch(()=>{})}}
function formatHintDisplay(s){s=String(s||'').trim();if(!s)return '';s=s.replace(/\$\$\s*/g,'$');s=s.replace(/\s*\$\$/g,'$');s=s.replace(/\$\s*\n+\s*\$/g,'');s=s.replace(/\$\s*\n+\s*([^$\n]+?)\s*\n+\s*\$/g,'$( $1 )$');s=s.replace(/\$\s*\n+([^$\n]+?)\s*\$/g,'$( $1 )$');s=s.replace(/\$\s*\$/g,'');s=s.replace(/^###\s+(.+)$/gm,'@@B@@$1@@/B@@');return renderRichText(s)}
function applyAuto5050(hide){if(!hide||!hide.length)return;for(let L of hide){let el=document.getElementById('opt_'+L);if(el)el.classList.add('hidden5050')}let b=document.getElementById('btn5050');if(b)b.disabled=true;let bf=document.getElementById('btnFs5050');if(bf)bf.disabled=true;let rb=document.getElementById('resultBox');if(rb){rb.textContent='🎯 Đã loại 2 đáp án sai: '+hide.join(', ');rb.style.color='#1d4ed8'}}
function hintRawText(){let j=HINT_BY_Q[CUR];return j?String(j.hint||''):''}
function quizRestorePayload(){return{made:CURRENT_MADE||'',questions:QUESTIONS||[],level_filter:CURRENT_LEVEL||'',dang_filter:CURRENT_DANG||''}}
function fmtTime(sec){sec=Math.max(0,Number(sec)||0);let m=Math.floor(sec/60),s=sec%60;return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`}
function syncQuizTimerText(){let v=fmtTime(QUIZ_ELAPSED);let x=document.getElementById('quizTimerText');if(x)x.textContent=v;let fx=document.getElementById('fsQuizTimerText');if(fx)fx.textContent=v}
function startQuizTimer(){stopQuizTimer();QUIZ_ELAPSED=0;syncQuizTimerText();QUIZ_TIMER=setInterval(()=>{QUIZ_ELAPSED++;syncQuizTimerText()},1000)}
function stopQuizTimer(){if(QUIZ_TIMER){clearInterval(QUIZ_TIMER);QUIZ_TIMER=null}}
async function api(url,opts={}){let r=await fetch(url,opts);let txt=await r.text();let j;try{j=txt?JSON.parse(txt):{};}catch(e){j={error:'Không đọc được phản hồi từ máy chủ. Có thể Render đang timeout hoặc trả về HTML. Mã HTTP: '+r.status+'. Nội dung đầu: '+txt.slice(0,120)}}if(!r.ok||j.error){if(r.status==401)location='/login';throw new Error(j.error||'Lỗi API')}return j}
function setOptions(id,arr){document.getElementById(id).innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option>${esc(x)}</option>`).join('')}
function updateExamStrip(){const el=document.getElementById('examStrip');const msg=document.getElementById('examMsg');const tm=document.getElementById('examTimer');if(!el||!msg||!tm)return;const start=new Date('2026-06-11T00:00:00+07:00');const end=new Date('2026-06-12T23:59:59+07:00');const now=new Date();if(now<start){let d=Math.floor((start-now)/1000);let day=Math.floor(d/86400);d%=86400;let h=Math.floor(d/3600);d%=3600;let m=Math.floor(d/60);let s=d%60;msg.textContent='📢 Thông báo: Kỳ thi diễn ra ngày 11-12/06/2026';tm.textContent=`Còn ${day} ngày ${h}h ${m}m ${s}s`;el.classList.remove('hide');return}if(now<=end){msg.textContent='🔥 ĐANG TRONG THỜI GIAN THI 11-12/06/2026';tm.textContent='Chúc các em bình tĩnh, tự tin!';el.classList.remove('hide');return}msg.textContent='✅ Kỳ thi 11-12/06/2026 đã kết thúc';tm.textContent='Tiếp tục luyện tập để nâng điểm.';el.classList.remove('hide')}
async function loadAiKeyPanel(){let panel=document.getElementById('aiKeyPanel');let st=document.getElementById('aiKeyStatus');if(!panel)return;if(USER.can_save_own_ai_key===false){panel.classList.add('hide');return}panel.classList.remove('hide');try{let j=await api('/api/ai-config');let parts=[];if(j.using_user_keys)parts.push(`Đã lưu ${j.user_gemini_keys||0} key của bạn`);else parts.push('Chưa lưu key — dán AIza... bên dưới');if(j.has_server_keys)parts.push('Server có key dự phòng');if(j.has_keys)parts.push('✅ Có thể dùng Gợi ý AI');else parts.push('⚠️ Chưa có key — cần Lưu key');if(st)st.textContent=parts.join(' · ')}catch(e){if(st)st.textContent='Không tải trạng thái key: '+e.message}}
async function saveMyAiKey(){if(!USER.can_ai_hint){alert('Key AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}let raw=document.getElementById('myApiKeys').value.trim();if(!raw){alert('Dán ít nhất một key AIza...');return}try{let j=await api('/api/ai-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_keys:raw,provider:'GEMINI'})});alert(j.message||'Đã lưu key.');await loadAiKeyPanel()}catch(e){alert('Không lưu được: '+e.message)}}
async function testMyAiKey(){if(!USER.can_ai_hint){alert('Key AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}let raw=document.getElementById('myApiKeys').value.trim();let body={provider:'GEMINI'};if(raw)body.api_keys=raw;try{let j=await api('/api/ai-key-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});alert((j.ok?'✅ ':'❌ ')+(j.message||''))}catch(e){alert(e.message)}}
async function clearMyAiKey(){if(!confirm('Xóa key AI đã lưu trên server (chỉ của tài khoản này)?'))return;try{let j=await api('/api/ai-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clear_keys:true})});document.getElementById('myApiKeys').value='';alert(j.message||'Đã xóa key.');await loadAiKeyPanel()}catch(e){alert(e.message)}}
function updateAdminChrome(){let bar=document.getElementById('adminBar');if(!bar)return;let show=!!USER.is_admin;bar.classList.toggle('hide',!show);let inQuiz=!!(document.getElementById('quiz')&&!document.getElementById('quiz').classList.contains('hide'));let eb=document.getElementById('adminEditBtn');if(eb)eb.classList.toggle('hide',!inQuiz);let fsAdmin=show&&inQuiz&&FULLDE_ON;let fss=document.getElementById('btnFsSync');if(fss)fss.classList.toggle('hide',!fsAdmin);let fse=document.getElementById('btnFsEdit');if(fse)fse.classList.toggle('hide',!fsAdmin)}
function reindexQuizMaps(removedIdx){function shift(obj){let out={};for(let k in obj){let i=parseInt(k,10);if(isNaN(i))continue;if(i<removedIdx)out[i]=obj[k];else if(i>removedIdx)out[i-1]=obj[k]}return out}ANSWERS=shift(ANSWERS);RESULTS=shift(RESULTS);CHECKED=shift(CHECKED);LOCKED_Q=shift(LOCKED_Q);HINT_BY_Q=shift(HINT_BY_Q)}
async function init(){updateExamStrip();META=await api('/api/meta');USER=META.user||{};document.getElementById('me').textContent=`${USER.hoten||''} (${USER.role||''}${USER.trial_until?' - hết trial: '+USER.trial_until:''}${USER.account_until?' - hết hạn: '+USER.account_until:''})`;updateAdminChrome();await loadAiKeyPanel();if(META.loading){document.getElementById('info').textContent='Đang nạp Google Sheet... lần đầu có thể chờ 10–40 giây';document.getElementById('catalog').innerHTML=`<div class="card loadCard"><h3>⏳ Hệ thống đang khởi động</h3><p><b>Vui lòng chờ, không cần bấm lại nhiều lần.</b></p><p>${esc(META.loading_message||'Đang nạp dữ liệu từ Google Sheet...')}</p><div class="loadWarn"><b>Lưu ý:</b> lần đầu Render Free vừa “thức dậy” và vừa nạp Google Sheet thì có thể chờ khoảng <b>10–40 giây</b>. Trang sẽ tự tải lại sau vài giây.</div>${META.load_error?'<p class="loadErr"><b>Lỗi:</b> '+esc(META.load_error)+'</p>':''}<p class="muted">Trang sẽ tự thử lại sau 3 giây. Không cần đăng nhập lại.</p></div>`;document.getElementById('countCat').textContent='';setTimeout(init,3000);return;}CATALOG=META.catalog||[];document.getElementById('info').textContent=`${META.count_questions} câu hỏi | ${META.count_catalog} đề/thẻ đề | Nạp: ${META.loaded_at}`;setOptions('fMon',META.filters.Mon);setOptions('fLop',META.filters.Lop);setOptions('fChuong',META.filters.Chuong);setOptions('fBaiHoc',META.filters.BaiHoc);setOptions('fBoDe',META.filters.BoDe);renderCatalog()}
function okFilter(x){let s=normText(val('fSearch'));let lv=normText(val('fMucDo'));let dang=normText(val('fDang'));let blob=normText([x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.DangBaiTap,x.BoDe,x.De,x.MucDo,x.Dang].join(' '));let levels=normText(x.MucDo||'').split(',').map(v=>v.trim()).filter(Boolean);let dangs=normText(x.Dang||'').split(',').map(v=>v.trim()).filter(Boolean);let levelOk=!lv||levels.includes(lv)||normText(x.MucDo||'').includes(lv);let dangOk=!dang||dangs.includes(dang)||normText(x.Dang||'').includes(dang);return(!val('fMon')||x.Mon==val('fMon'))&&(!val('fLop')||x.Lop==val('fLop'))&&(!val('fChuong')||x.Chuong==val('fChuong'))&&(!val('fBaiHoc')||x.BaiHoc==val('fBaiHoc'))&&(!val('fBoDe')||x.BoDe==val('fBoDe'))&&levelOk&&dangOk&&(!s||blob.includes(s))}
function renderCatalog(){let list=CATALOG.filter(okFilter);let selectedLv=(val('fMucDo')||'').toUpperCase();let selectedDang=(val('fDang')||'').trim();document.getElementById('countCat').textContent=`(${list.length} mục)`;document.getElementById('catalog').innerHTML=list.map(x=>{let access=x.QuyenTruyCap||'FREE';let locked=USER.is_trial&&access!='FREE';let btn=locked?`<button class="btnRed" disabled>Khóa VIP</button>`:`<button class="btnStartStrong" onclick="openStartModal('${x.MaDe}')">🚀 Làm bài + xáo trộn</button>`;let note=locked?`<div class="muted" style="color:#991b1b;margin-top:6px">Tài khoản dùng thử chỉ mở đề FREE.</div>`:'';let hint=locked?'':`<div class="shuffleHint">Có thể chọn: xáo câu, xáo đáp án hoặc xáo cả 2.</div>`;let lvNotice=selectedLv?`<div style="margin-top:6px;padding:6px 8px;border-radius:8px;background:#dbeafe;border:1px solid #60a5fa;color:#1e40af;font-weight:900">🎯 Đề được lọc theo mức ${esc(selectedLv)}</div>`:'';let dangNotice=selectedDang?`<div style="margin-top:6px;padding:6px 8px;border-radius:8px;background:#dcfce7;border:1px solid #86efac;color:#166534;font-weight:900">🧩 Đề được lọc theo dạng ${esc(selectedDang)}</div>`:'';let title=esc(x.BaiHoc||x.De||'Đề luyện tập');let sub=x.Chuong?`<div class="muted" style="margin-top:4px;font-size:13px">${esc(x.Chuong)}</div>`:'';return `<div class="card"><h3>${title}</h3>${sub}<div><span class="tag">${esc(x.Mon)}</span><span class="tag">Lớp ${esc(x.Lop)}</span><span class="tag">${esc(x.SoCau)} câu</span><span class="tag">${esc(access)}</span></div><div class="line"></div><div><b>Chương:</b> ${esc(x.Chuong)}</div><div><b>Bài:</b> ${esc(x.BaiHoc)}</div><div><b>Dạng:</b> ${esc(x.Dang)}</div><div><b>Mức độ:</b> ${esc(x.MucDo)}</div><div><b>Bộ đề:</b> ${esc(x.BoDe)}</div>${lvNotice}${dangNotice}${note}${hint}<div style="text-align:right;margin-top:10px">${btn}</div></div>`}).join('')||'<div class="muted">Không có đề phù hợp.</div>';typeset()}
async function syncData(){if(!confirm('Đồng bộ lại dữ liệu từ Google Sheet?'))return;let j=await api('/api/sync',{method:'POST'});alert(j.message||'Đã bắt đầu đồng bộ.');init()}
async function testServerAiKey(){try{let j=await api('/api/ai-key-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:'GEMINI'})});alert((j.ok?'✅ ':'❌ ')+(j.message||''));}catch(e){alert(e.message);}}
function closeStartModal(){document.getElementById('startModal').classList.add('hide')}
function openStartModal(made){CURRENT_MADE=made;CURRENT_LEVEL=val('fMucDo');CURRENT_DANG=val('fDang');START_IS_RETRY=false;document.getElementById('startModalTitle').textContent='Thiết lập làm bài';document.getElementById('chkShuffleQ').checked=false;document.getElementById('chkShuffleA').checked=false;document.getElementById('startModal').classList.remove('hide')}
function openRetryModal(){if(!CURRENT_MADE){alert('Chưa xác định được mã đề.');return;}CURRENT_LEVEL=CURRENT_LEVEL||val('fMucDo');CURRENT_DANG=CURRENT_DANG||val('fDang');START_IS_RETRY=true;document.getElementById('startModalTitle').textContent='Làm lại đề';document.getElementById('startModal').classList.remove('hide')}
function pickShufflePreset(kind){document.getElementById('chkShuffleQ').checked=kind==='q'||kind==='both';document.getElementById('chkShuffleA').checked=kind==='a'||kind==='both';if(kind==='none'){document.getElementById('chkShuffleQ').checked=false;document.getElementById('chkShuffleA').checked=false}confirmStartQuiz()}
async function confirmStartQuiz(){let made=CURRENT_MADE;if(!made)return;let sq=document.getElementById('chkShuffleQ').checked;let sa=document.getElementById('chkShuffleA').checked;let lv=CURRENT_LEVEL||val('fMucDo');let dg=CURRENT_DANG||val('fDang');closeStartModal();if(START_IS_RETRY&&!SUBMITTED&&Object.keys(ANSWERS).length){if(!confirm('Làm lại sẽ xóa bài đang làm. Tiếp tục?'))return}await startQuiz(made,sq,sa,lv,dg)}
function updateShuffleBadge(j){let el=document.getElementById('shuffleBadge');let parts=[];if(j.shuffle_questions)parts.push('Xáo câu');if(j.shuffle_options)parts.push('Xáo đáp án');if(parts.length){el.textContent=parts.join(' + ');el.classList.remove('hide')}else{el.textContent='';el.classList.add('hide')}}
async function startQuiz(made,shuffleQ=false,shuffleA=false,level='',dang=''){try{let lv=(level||'').trim().toUpperCase();let dg=(dang||'').trim();let url='/api/start?made='+encodeURIComponent(made)+'&shuffle_q='+(shuffleQ?1:0)+'&shuffle_a='+(shuffleA?1:0)+'&level='+encodeURIComponent(lv)+'&dang='+encodeURIComponent(dg);let j=await api(url);SID=j.sid;QUESTIONS=(j.questions||[]).map(q=>applyResolvedDang(q));CURRENT_MADE=made;CURRENT_LEVEL=lv;CURRENT_DANG=dg;CUR=0;ANSWERS={};SUBMITTED=!!USER.is_admin;RESULTS={};CHECKED={};LOCKED_Q={};COMPLETED_NOTICE=false;HINT_BY_Q={};FS_ANS_FORCE=null;FS_EXP_FORCE=null;document.getElementById('home').classList.add('hide');document.getElementById('quiz').classList.remove('hide');document.getElementById('resultBox').textContent=USER.is_admin?'ADMIN: đang xem đáp án/lời giải':(USER.is_trial?'DÙNG THỬ: chỉ luyện đề FREE, không chấm điểm':'');let c=CATALOG.find(x=>x.MaDe==made)||{};let lvTag=lv?` | Mức độ: ${lv}`:'';let dgTag=dg?` | Dạng: ${dg}`:'';document.getElementById('quizTitle').textContent=`${c.Mon||''} ${c.Lop?'- Lớp '+c.Lop:''} | ${c.De||c.BaiHoc||''}${lvTag}${dgTag}`;updateShuffleBadge(j);startQuizTimer();updateAdminChrome();renderNav();renderQuestion(); if(j.trial_message) alert(j.trial_message)}catch(e){alert('Không mở được đề: '+e.message)}}
function backHome(){stopQuizTimer();FS_ANS_FORCE=null;FS_EXP_FORCE=null;document.getElementById('quiz').classList.add('hide');document.getElementById('home').classList.remove('hide');updateAdminChrome()}
function ensureFullModeOverrides(){
    if(document.getElementById('LDVL_FS_OVR')) return;
    let st=document.createElement('style');
    st.id='LDVL_FS_OVR';
    st.textContent=
        "body.fullde-mode #quiz .quizLayout{grid-template-columns:minmax(0,1fr) 220px!important;gap:8px!important;padding:0 8px 8px!important}"+
        "body.fullde-mode #qtext{flex:0 0 auto!important;min-height:0!important;padding:12px!important;overflow:visible!important}"+
        "body.fullde-mode #options{flex:0 0 auto!important;margin-top:8px!important;position:relative!important;z-index:2!important;background:var(--bg)!important}"+
        "body.fullde-mode #qtext .qimg{max-height:min(42vh,280px)!important;display:block!important;margin:10px auto 12px!important}"+
        "body.fullde-mode #fsOnlyTools button{font-size:11px!important;padding:4px 7px!important}"+
        "body.fullde-mode #quiz .quizLayout>div:last-child{overflow:auto!important}"+
        "body.fullde-mode #quiz .quizLayout>div:last-child>.panel{overflow:auto!important}"+
        "body.fullde-mode #navNums{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:6px!important;overflow:auto!important;align-content:start!important}"+
        "body.fullde-mode #navNums .num{display:block!important;visibility:visible!important;opacity:1!important}"+
        "body.fullde-mode.fsnav-hidden #quiz .quizLayout{grid-template-columns:1fr 0px!important}"+
        "body.fullde-mode.fsnav-hidden #quiz .quizLayout>div:last-child{display:none!important}"+
        "@media(max-width:900px){body.fullde-mode #quiz .quizLayout{grid-template-columns:minmax(0,1fr) 150px!important}body.fullde-mode #navNums{grid-template-columns:repeat(3,minmax(0,1fr))!important}}"+
        "@media(max-width:760px){body.fullde-mode #quiz .quizLayout{grid-template-columns:1fr!important;grid-template-rows:minmax(0,1fr) auto!important;padding:0 4px 4px!important}body.fullde-mode #quiz .quizLayout>div:last-child{max-height:92px!important}body.fullde-mode #navNums{grid-template-columns:repeat(8,minmax(32px,1fr))!important;overflow-x:auto!important;overflow-y:hidden!important}body.fullde-mode #navNums .num{padding:3px 0!important;font-size:10px!important}body.fullde-mode #fsOnlyTools{gap:3px!important;padding:3px 4px!important}body.fullde-mode #fsOnlyTools button{font-size:9px!important;padding:3px 5px!important}body.fullde-mode #qtext{font-size:14px!important;padding:8px!important}body.fullde-mode #qtext .qimg{max-height:min(34vh,200px)!important}body.fullde-mode .opt{padding:6px 7px!important;font-size:13px!important;margin:3px 0!important}body.fullde-mode .tfrow{grid-template-columns:22px minmax(0,1fr) 34px!important;grid-template-areas:'lbl stmt opts'!important}body.fullde-mode .tfOpts{flex-direction:column!important;justify-content:flex-start!important;padding-left:0!important;width:34px!important}body.fullde-mode .tfLblFull{display:none!important}body.fullde-mode .tfLblShort{display:inline!important}body.fullde-mode .tfOpt{flex:0!important;width:100%!important;max-width:none!important;min-width:0!important;padding:5px 2px!important;font-size:11px!important;text-align:center!important}body.fullde-mode .tfOpt input{position:absolute!important;opacity:0!important;width:0!important;height:0!important}}";
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
async function toggleQuizFullscreen(){let btn=document.getElementById('btnPresent');if(!FULLDE_ON){ensureFullModeOverrides();FULLDE_ON=true;FS_ANS_FORCE=null;FS_EXP_FORCE=null;FS_NAV_HIDDEN=false;document.body.classList.remove('fsnav-hidden');document.body.classList.add('fullde-mode');ensureFsNavBtn();syncFsNavBtn();updateAdminChrome();if(btn)btn.textContent='⤢ Thoát full đề';try{if(!document.fullscreenElement&&document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen()}catch(e){}renderQuestion();return}FULLDE_ON=false;FS_ANS_FORCE=null;FS_EXP_FORCE=null;FS_NAV_HIDDEN=false;document.body.classList.remove('fsnav-hidden');document.body.classList.remove('fullde-mode');syncFsNavBtn();updateAdminChrome();if(btn)btn.textContent='📽 Full màn hình';try{if(document.fullscreenElement&&document.exitFullscreen)await document.exitFullscreen()}catch(e){}renderQuestion()}
function canViewSolutionLive(){return USER.is_admin||USER.can_view_solution_live===true}
function toggleAnswerInFullscreen(){if(!FULLDE_ON)return;let can=USER.is_admin||(canViewSolutionLive()&&(SUBMITTED||!!CHECKED[CUR]));if(!can){alert('Chưa đến chế độ xem đáp án.');return;}FS_ANS_FORCE=FS_ANS_FORCE===true?false:true;renderQuestion()}
function toggleExplainInFullscreen(){if(!FULLDE_ON)return;let can=USER.is_admin||(canViewSolutionLive()&&(SUBMITTED||!!CHECKED[CUR]));if(!can){alert('Chưa đến chế độ xem lời giải.');return;}FS_EXP_FORCE=FS_EXP_FORCE===true?false:true;renderQuestion()}
function formatDsAnswerLine(q,r){if(r&&r.correct_display)return esc(r.correct_display);if(r&&Array.isArray(r.rows)&&r.rows.length)return r.rows.map(x=>`${x.letter}=${x.correct==='Đ'?'Đúng':'Sai'}`).join(' · ');if(q.Dang==='Đúng sai'){let vals=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:[];let bits=[];for(let i=0;i<4;i++){let L=['A','B','C','D'][i];if(!q[L])continue;let v=String(q.DapAn||'').replace(/\u0110/g,'D').replace(/đ/g,'d');let parsed=(v.match(/[DSĐ]/gi)||[]);let c=parsed[i];if(c)c=c.toUpperCase()==='S'?'Sai':(c==='Đ'||c==='D'?'Đúng':c);bits.push(`${L}=${c||'?'}`)}return bits.join(' · ')}return r.correct||q.DapAn||''}
function saveCurrent(){let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||USER.is_admin)return;if(LOCKED_Q[CUR])return;if(q.Dang=='Trắc nghiệm'){let r=document.querySelector(`input[name="ans_${CUR}"]:checked`);if(r){ANSWERS[CUR]=r.value;LOCKED_Q[CUR]=true;checkCurrentQuestion()}}else if(q.Dang=='Đúng sai'){let arr=[];let req=0;for(let L of ['A','B','C','D']){if(q[L])req++;let r=document.querySelector(`input[name="tf_${CUR}_${L}"]:checked`);arr.push(r?r.value:'')}ANSWERS[CUR]=arr;let filled=arr.filter(v=>!!v).length;if(req>0&&filled>=req){LOCKED_Q[CUR]=true;checkCurrentQuestion()}}else{let el=document.getElementById('shortAns');if(el)ANSWERS[CUR]=el.value}renderNav();notifyDoneIfNeeded()}
async function checkCurrentQuestion(){if(USER.is_trial||SUBMITTED)return;let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||q.Dang=='Tự luận')return;let ans=ANSWERS[CUR];if(ans==null)return;if(Array.isArray(ans)&&ans.every(v=>!v))return;try{let j=await api('/api/check-one',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR,answer:ans,...quizRestorePayload()})});CHECKED[CUR]=j;RESULTS[CUR]=j;if(j.ok){document.getElementById('resultBox').textContent=`Câu ${CUR+1}: Đúng`;document.getElementById('resultBox').style.color='#166534'}else{document.getElementById('resultBox').textContent=`Câu ${CUR+1}: Sai`;document.getElementById('resultBox').style.color='#991b1b'}renderQuestion()}catch(e){}}
function renderNav(){let html='';for(let i=0;i<QUESTIONS.length;i++){let cls='num';if(i==CUR)cls+=' active';if(ANSWERS[i]!=null&&String(ANSWERS[i]).length)cls+=' answered';if((SUBMITTED||CHECKED[i])&&RESULTS[i])cls+=RESULTS[i].ok?' ok':' bad';let tip=shortText((QUESTIONS[i]&&QUESTIONS[i].CauHoi)||'',120);html+=`<button class="${cls}" title="${escAttr(tip)}" onclick="goQ(${i})">${i+1}</button>`}let nav=document.getElementById('navNums');nav.innerHTML=html;if(FULLDE_ON){let active=nav.querySelector('.num.active');if(active&&active.scrollIntoView)active.scrollIntoView({block:'nearest',inline:'nearest'})}}function goQ(i){saveCurrent();CUR=i;renderQuestion()}function prevQ(){if(CUR>0){saveCurrent();CUR--;renderQuestion()}else{alert('Đang ở câu đầu tiên của đề.')}}function nextQ(){if(CUR<QUESTIONS.length-1){saveCurrent();CUR++;renderQuestion()}else{saveCurrent();alert('✅ Đã hết đề. Thầy/các em có thể xem lại rồi bấm Nộp bài.')}} 
function renderQuestion(){let q=applyResolvedDang(QUESTIONS[CUR]);renderNav();let canAi=USER.can_ai_hint!==false;let hb=document.getElementById('hintBox');if(hb){if(HINT_LOADING&&HINT_LOADING_Q===CUR)showHintLoadingBox();else if(canAi&&HINT_BY_Q[CUR]){hb.classList.remove('hintBoxLoading');renderHintBox(HINT_BY_Q[CUR])}else{hb.classList.add('hide');hb.classList.remove('hintBoxLoading');hb.innerHTML=''}}let who=(USER.hoten||USER.mahs||'').trim();let prefix=who?`${who} | `:'';document.getElementById('qid').textContent=`${prefix}Câu ${CUR+1}/${QUESTIONS.length} | ID: ${q.ID||''} | ${q.MucDo||''} - ${q.Dang}`;document.getElementById('qtext').innerHTML=renderRichText(q.CauHoi)+(q.HinhAnh?`<div class="qimgWrap"><img class="qimg" src="${esc(q.HinhAnh)}" alt="Hình minh họa" onerror="this.parentElement.outerHTML='<div class=\'qimgErr\'>Không tải được hình. Kiểm tra cột T hoặc quyền chia sẻ ảnh.</div>'"></div>`:'' );document.getElementById('btn5050').disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!USER.can_5050||LOCKED_Q[CUR];let bfs=document.getElementById('btnFs5050');if(bfs)bfs.disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!USER.can_5050||LOCKED_Q[CUR];document.getElementById('btnSubmit').style.display=(USER.is_admin||USER.is_trial)?'none':'';document.getElementById('btnEdit').classList.toggle('hide',!USER.is_admin);syncHintButtons(canAi);let html='';if(q.Dang=='Trắc nghiệm'){for(let L of ['A','B','C','D']){if(!q[L])continue;let checked=ANSWERS[CUR]==L?'checked':'';let cls='opt';let correct=(q.DapAn||'').toUpperCase().match(/[ABCD]/)?.[0]||'';if(USER.is_admin&&correct==L)cls+=' correct';if((SUBMITTED||CHECKED[CUR])&&RESULTS[CUR]){if(RESULTS[CUR].correct==L)cls+=' correct';if(RESULTS[CUR].chosen==L&&RESULTS[CUR].chosen!=RESULTS[CUR].correct)cls+=' wrong'}html+=`<label id="opt_${L}" class="${cls}"><input type="radio" name="ans_${CUR}" value="${L}" ${checked} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()"><b>${L}.</b><span>${renderRichText(q[L])}</span></label>`}}else if(q.Dang=='Đúng sai'){let old=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:['','','',''];let rows=((RESULTS[CUR]&&RESULTS[CUR].rows)||[]);let tfHead=`<div class="tfOptsHead"><span></span><span></span><span class="tfColHead"><span class="tfLblFull">Đúng · Sai</span><span class="tfLblShort">Đ<br>S</span></span></div>`;let tfRows='';for(let idx=0;idx<4;idx++){let L=['A','B','C','D'][idx];if(!q[L])continue;let cls='tfrow';let rr=rows.find(x=>x.letter===L);if((SUBMITTED||CHECKED[CUR])&&rr){if(rr.ok===true)cls+=' correct';else if(rr.ok===false)cls+=' wrong'}tfRows+=`<div class="${cls}"><b>${L}.</b><div class="tfStmt">${renderRichText(q[L])}</div><div class="tfOpts"><label class="tfOpt tfD" title="Đúng"><input type="radio" name="tf_${CUR}_${L}" value="Đ" ${old[idx]=='Đ'?'checked':''} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()"><span class="tfLbl tfLblFull">Đúng</span><span class="tfLbl tfLblShort">Đ</span></label><label class="tfOpt tfS" title="Sai"><input type="radio" name="tf_${CUR}_${L}" value="S" ${old[idx]=='S'?'checked':''} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()"><span class="tfLbl tfLblFull">Sai</span><span class="tfLbl tfLblShort">S</span></label></div></div>`}html=tfHead+tfRows}else if(q.Dang=='Trả lời ngắn'){html=`<input id="shortAns" style="width:100%;font-size:18px" placeholder="Nhập đáp án..." value="${esc(ANSWERS[CUR]||'')}" ${SUBMITTED?'disabled':''} oninput="saveCurrent()">`}else{html=`<textarea id="shortAns" style="width:100%;min-height:120px" placeholder="Nhập bài làm tự luận..." ${SUBMITTED?'disabled':''} oninput="saveCurrent()">${esc(ANSWERS[CUR]||'')}</textarea>`}document.getElementById('options').innerHTML=html;let canShowAns=USER.is_admin||(canViewSolutionLive()&&(SUBMITTED||!!CHECKED[CUR]));let canShowExp=USER.is_admin||(canViewSolutionLive()&&(SUBMITTED||!!CHECKED[CUR]));let showAns=canShowAns,showExp=canShowExp;if(FULLDE_ON){if(FS_ANS_FORCE!==null)showAns=canShowAns&&FS_ANS_FORCE;if(FS_EXP_FORCE!==null)showExp=canShowExp&&FS_EXP_FORCE}let showBox=showAns||showExp;document.getElementById('solution').classList.toggle('hide',!showBox);if(showBox){let r=RESULTS[CUR]||{};let parts=[];if(showAns){let ansLine=q.Dang==='Đúng sai'?formatDsAnswerLine(q,r):renderRichText(r.correct||r.DapAn||q.DapAn||'');parts.push(`<b>Đáp án:</b> ${ansLine}`)}if(showExp)parts.push(`<b>Lời giải:</b><br>${formatHintDisplay(r.LoiGiai||q.LoiGiai||'Chưa có lời giải.')}`);document.getElementById('solution').innerHTML=parts.join('<br>')}typeset()}
async function use5050(){saveCurrent();try{let j=await api('/api/fifty',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR,...quizRestorePayload()})});for(let L of j.hide||[]){let el=document.getElementById('opt_'+L);if(el)el.classList.add('hidden5050')}document.getElementById('btn5050').disabled=true;let bfs=document.getElementById('btnFs5050');if(bfs)bfs.disabled=true;let msg=`50-50: đã loại ${((j.hide||[]).join(', ')||'2 đáp án sai')}`;document.getElementById('resultBox').textContent=msg;document.getElementById('resultBox').style.color='#1d4ed8';if(j.message&&!String(j.message).toLowerCase().includes('đã loại'))alert(j.message)}catch(e){alert(e.message)}}
function hintButtonLabel(){return USER.is_admin?'🔍 AI kiểm tra':(USER.is_vip?'💡 Gợi ý AI VIP (chi tiết)':'💡 Gợi ý AI')}
function syncHintButtons(canAi){let lbl=hintButtonLabel();for(let id of ['btnHint','btnFsHint']){let b=document.getElementById(id);if(!b)continue;b.classList.toggle('hide',!canAi);if(HINT_LOADING)continue;b.classList.remove('btnHintLoading');b.textContent=lbl;b.disabled=!canAi}}
function setHintLoading(on,qIndex){HINT_LOADING=!!on;HINT_LOADING_Q=on?qIndex:null;let lbl=hintButtonLabel();for(let id of ['btnHint','btnFsHint']){let b=document.getElementById(id);if(!b)continue;if(on){if(!b.dataset.hintLabel)b.dataset.hintLabel=b.textContent||lbl;b.disabled=true;b.classList.add('btnHintLoading');b.innerHTML='<span class="hintSpin"></span> AI đang xử lý…'}else{b.classList.remove('btnHintLoading');b.textContent=b.dataset.hintLabel||lbl;delete b.dataset.hintLabel}}}
function showHintLoadingBox(){let hb=document.getElementById('hintBox');if(!hb)return;hb.classList.remove('hide');hb.classList.add('hintBoxLoading');let title=USER.is_admin?'🔍 AI kiểm tra (ADMIN):':(USER.is_vip?'💡 Gợi ý AI VIP (chi tiết):':'💡 Gợi ý AI:');let sub=USER.is_admin||USER.is_vip?'Gemini đang soạn bài giải đủ 8 mục — thường mất 15–45 giây, vui lòng chờ…':'Đang phân tích câu hỏi và soạn gợi ý…';hb.innerHTML=`<b>${title}</b><div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang gọi AI…</b><div class="muted" style="margin-top:6px;font-size:13px;line-height:1.45">${esc(sub)}</div></div></div>`}
function renderHintBox(j){let hb=document.getElementById('hintBox');if(!hb||!j)return;hb.classList.remove('hide');hb.classList.remove('hintBoxLoading');let title=j.admin_review?'🔍 AI kiểm tra (ADMIN):':(j.vip_detailed?'💡 Gợi ý AI VIP (chi tiết):':'💡 Gợi ý AI:');let extra='';if(j.admin_review){extra=`<div class="muted" style="margin-top:6px;font-size:12px">Chọn/chép nội dung bên dưới hoặc bấm nút chuyển vào Sheet</div>`;if(j.key_index)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">AI: ${esc(j.provider_used||'')} | key #${j.key_index}</div>`;else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Cần GEMINI_API_KEY trên Render</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`;if(j.hint_truncated)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ AI có thể chưa đủ mục 5–8 — bấm lại <b>AI kiểm tra</b> hoặc tăng GEMINI_ADMIN_MODEL trên Render.</div>`;let sd=esc(j.suggested_dapan||'');let sl=esc(j.suggested_loigiai||'');extra+=`<div class="hintAdminActions"><button type="button" class="btn2" onclick="copyHintAll()">📋 Chép toàn bộ</button><button type="button" class="btn2" onclick="applyHintField('DapAn')">→ Đáp án (P)</button><button type="button" class="btn2" onclick="applyHintField('LoiGiai')">→ Lời giải (R)</button><button type="button" class="btnGreen" onclick="saveHintField('DapAn')">💾 Lưu đáp án Sheet</button><button type="button" class="btnGreen" onclick="saveHintField('LoiGiai')">💾 Lưu lời giải Sheet</button><button type="button" class="btn" onclick="openEditWithHint()">✏️ Mở Sửa câu</button></div>`;if(j.suggested_dapan)extra+=`<div class="muted hintSuggestDapan" style="margin-top:6px;font-size:12px"><b>Gợi ý đáp án:</b> <span class="hintMath">${formatHintDisplay(j.suggested_dapan)}</span></div>`}else if(j.vip_detailed){extra=`<div class="muted" style="margin-top:6px;font-size:12px">VIP: bài giải chi tiết như ADMIN (đủ 8 mục).</div>`;if(j.key_index)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">AI: ${esc(j.provider_used||'')} | key #${j.key_index}</div>`;else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Chưa có key — nạp tại 🔑 Key AI của tôi</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`;if(j.hint_truncated)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ AI có thể chưa đủ mục — bấm lại <b>Gợi ý AI</b>.</div>`;if(j.suggested_dapan)extra+=`<div class="muted hintSuggestDapan" style="margin-top:6px;font-size:12px"><b>Gợi ý đáp án:</b> <span class="hintMath">${formatHintDisplay(j.suggested_dapan)}</span></div>`;if(j.hide_5050&&j.hide_5050.length)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">Đã loại: ${esc(j.hide_5050.join(', '))}</div>`}else if(j.vip_formula_only){extra=`<div class="muted" style="margin-top:6px;font-size:12px">VIP: công thức đã thay số từ đề + tự loại 2 đáp án sai (trắc nghiệm)</div>`;if(j.hide_5050&&j.hide_5050.length)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">Đã loại: ${esc(j.hide_5050.join(', '))}</div>`;if(j.provider_used==='FALLBACK')extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">AI lỗi hoặc chưa có key — <a href="#" onclick="backHome();return false">🔑 Key AI của tôi</a></div>`;else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Chưa có key — nạp tại 🔑 Key AI của tôi</div>`}else if(j.key_index){extra=`<div class="muted" style="margin-top:6px;font-size:12px">AI: ${esc(j.provider_used||'')} | key #${j.key_index}</div>`}else{extra=`<div class="muted" style="margin-top:6px;font-size:12px">AI fallback${j.ai_configured?' (key lỗi hoặc hết quota)':' (chưa có key)'}</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`}if(j.message)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">${esc(j.message)}</div>`;let body=formatHintDisplay(j.hint||'');hb.innerHTML=`<b>${title}</b>${extra}<div id="hintAdminBody" class="hintAdminBody">${body||'<span class="muted">(trống)</span>'}</div>`;typeset(document.getElementById('hintAdminBody'));if(hb.querySelector('.hintSuggestDapan'))typeset(hb.querySelector('.hintSuggestDapan'))}
function copyHintAll(){let t=hintRawText();if(!t){alert('Chưa có nội dung.');return}navigator.clipboard.writeText(t).then(()=>alert('Đã chép vào clipboard (text gốc có $...$).')).catch(()=>{let el=document.getElementById('hintAdminBody');if(el){let r=document.createRange();r.selectNodeContents(el);let sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);try{document.execCommand('copy');alert('Đã chép vùng hiển thị (Ctrl+C).')}catch(e){alert('Chọn text trong ô gợi ý rồi Ctrl+C.')}}})}
function hintFieldValue(field){let j=HINT_BY_Q[CUR]||{};if(field==='DapAn')return String(j.suggested_dapan||'').trim();if(field==='LoiGiai'){let v=String(j.suggested_loigiai||'').trim();if(v)return v;return hintRawText().trim()}return ''}
function applyHintField(field){if(!USER.is_admin){alert('Chỉ ADMIN.');return}let v=hintFieldValue(field);if(!v){alert(field==='DapAn'?'Chưa tách được đáp án AI (mục 5).':'Chưa có lời giải đề xuất (mục 8).');return}openEditWithHint(field==='DapAn'?v:'',field==='LoiGiai'?v:'')}
function openEditWithHint(dapan='',loigiai=''){let j=HINT_BY_Q[CUR]||{};if(!dapan)dapan=String(j.suggested_dapan||'').trim();if(!loigiai)loigiai=String(j.suggested_loigiai||'').trim();openEdit();if(dapan){let el=document.getElementById('edit_DapAn');if(el)el.value=dapan}if(loigiai){let el=document.getElementById('edit_LoiGiai');if(el)el.value=loigiai}}
async function saveHintField(field){if(!USER.is_admin){alert('Chỉ ADMIN.');return}let q=QUESTIONS[CUR];if(!q||!q._row){alert('Không xác định dòng Sheet.');return}let v=hintFieldValue(field);if(!v){alert('Không có nội dung để lưu.');return}let col=field==='DapAn'?'P (đáp án)':'R (lời giải)';if(!confirm('Lưu vào Google Sheet cột '+col+'?\n\n'+v.slice(0,200)+(v.length>200?'…':'')))return;try{let updates={};updates[field]=v;let j=await api('/api/question/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row,updates})});Object.assign(q,updates);if(HINT_BY_Q[CUR]){if(field==='DapAn')HINT_BY_Q[CUR].sheet_dapan=v;if(field==='LoiGiai')HINT_BY_Q[CUR].sheet_loigiai=v}renderQuestion();alert('Đã lưu '+field+' vào Sheet dòng '+j.row)}catch(e){alert('Không lưu được: '+e.message)}}
async function requestHint(){if(!USER.can_ai_hint){alert('Gợi ý AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}if(HINT_LOADING){return}saveCurrent();let qIdx=CUR;setHintLoading(true,qIdx);showHintLoadingBox();let rb=document.getElementById('resultBox');if(rb){rb.textContent='⏳ AI đang làm…';rb.style.color='#1d4ed8'}try{let ans=ANSWERS[qIdx];let j=await api('/api/hint',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:qIdx,answer:ans,...quizRestorePayload()})});HINT_BY_Q[qIdx]=j;if(CUR===qIdx){renderHintBox(j);if(j.hide_5050&&j.hide_5050.length)applyAuto5050(j.hide_5050);let hb=document.getElementById('hintBox');if(hb&&!hb.classList.contains('hide')){hb.scrollIntoView({behavior:'smooth',block:'nearest'})}}else if(HINT_LOADING_Q===qIdx){let hb=document.getElementById('hintBox');if(hb){hb.classList.add('hide');hb.classList.remove('hintBoxLoading');hb.innerHTML=''}}}catch(e){if(CUR===qIdx){let hb=document.getElementById('hintBox');if(hb){hb.classList.remove('hintBoxLoading');hb.classList.remove('hide');hb.innerHTML='<b>❌ Không lấy được gợi ý AI</b><div class="muted" style="margin-top:8px">'+esc(e.message)+'</div>'}}alert('Không lấy được gợi ý: '+e.message)}finally{if(HINT_LOADING_Q===qIdx){setHintLoading(false);syncHintButtons(USER.can_ai_hint!==false)}if(CUR===qIdx&&rb){if(USER.is_admin)rb.textContent='ADMIN: đang xem đáp án/lời giải';else if(USER.is_trial)rb.textContent='DÙNG THỬ: chỉ luyện đề FREE, không chấm điểm';else rb.textContent=''}}}
async function submitQuiz(){if(USER.is_trial){alert('Tài khoản dùng thử không được nộp/chấm điểm.');return;}saveCurrent();if(!confirm('Nộp bài?'))return;let j=await api('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,answers:ANSWERS,...quizRestorePayload()})});SUBMITTED=true;stopQuizTimer();RESULTS={};for(let r of j.results)RESULTS[r.index]=r;document.getElementById('resultBox').textContent=`Điểm: ${j.score}/10 | Đúng ${j.correct_count}/${j.auto_count} | ⏱ ${fmtTime(QUIZ_ELAPSED)}`;renderQuestion();renderNav()}
function openEdit(){let q=QUESTIONS[CUR];let fields=['CauHoi','A','B','C','D','DapAn','SaiSo','MucDo','Dang','LoiGiai','HinhAnh'];let labels={CauHoi:'Câu hỏi / Nội dung - lưu cột K',DapAn:'Đáp án - lưu cột P',SaiSo:'Sai số - lưu cột Q',MucDo:'Mức độ - lưu cột I',Dang:'Dạng - lưu cột J',LoiGiai:'Lời giải - lưu cột R',HinhAnh:'Hình ảnh - lưu cột T'};document.getElementById('editForm').innerHTML=fields.map(f=>{let h=(f=='CauHoi'||f=='LoiGiai')?'150px':'78px';let val=String(q[f]||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));return `<div><label><b>${labels[f]||f}</b></label><textarea style="min-height:${h}" id="edit_${f}">${val}</textarea></div>`}).join('');document.getElementById('modal').classList.remove('hide')}
function closeEdit(){document.getElementById('modal').classList.add('hide')}async function saveEdit(){let q=QUESTIONS[CUR];let updates={};for(let f of ['CauHoi','A','B','C','D','DapAn','SaiSo','MucDo','Dang','LoiGiai','HinhAnh'])updates[f]=document.getElementById('edit_'+f).value;try{let j=await api('/api/question/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row,updates})});alert('Đã lưu vào Google Sheet dòng '+j.row+'\nĐã cập nhật: '+(j.fields||[]).join(', '));Object.assign(q,updates);closeEdit();renderQuestion()}catch(e){alert('Không lưu được: '+e.message)}}
async function deleteQuestion(){let q=QUESTIONS[CUR];if(!q||!q._row){alert('Không xác định được dòng Google Sheet của câu này.');return;}let msg='Xóa vĩnh viễn câu này khỏi Google Sheet?\n\nID: '+(q.ID||'')+'\nDòng: '+q._row+'\n\nCó thể xóa tiếp câu khác — không cần đồng bộ lại sau mỗi lần xóa.';if(!confirm(msg))return;if(!confirm('Xác nhận lần 2: thầy chắc chắn muốn xóa câu này?'))return;try{let j=await api('/api/question/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row,id:q.ID||''})});let deletedRow=parseInt(j.row,10)||0;let removedIdx=CUR;QUESTIONS.splice(removedIdx,1);for(let qq of QUESTIONS){let r=parseInt(qq._row,10)||0;if(r>deletedRow)qq._row=r-1}reindexQuizMaps(removedIdx);if(QUESTIONS.length===0){closeEdit();backHome();alert('Đã xóa câu cuối trong phiên này.\nBấm Đồng bộ Sheet trên thanh trên nếu cần cập nhật mục lục.');return}if(CUR>=QUESTIONS.length)CUR=QUESTIONS.length-1;closeEdit();renderNav();renderQuestion();document.getElementById('resultBox').textContent='Đã xóa dòng '+deletedRow+' — còn '+QUESTIONS.length+' câu';document.getElementById('resultBox').style.color='#166534'}catch(e){alert('Không xóa được: '+e.message)}}
setInterval(updateExamStrip,1000);
document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement&&FULLDE_ON){document.body.classList.add('fullde-mode')}if(!document.fullscreenElement){FS_ANS_FORCE=null;FS_EXP_FORCE=null;renderQuestion()}});
enhanceHomeColors();initTheme();init().catch(e=>{document.body.innerHTML='<pre style="padding:20px;color:red">'+e.message+'</pre>'})
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
        "retry_shuffle": True,
        "routes": ["/login", "/register", "/logout", "/api/meta", "/api/start", "/api/submit", "/api/question/update", "/api/question/delete"]
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
                return redirect(url_for("home"))
        except Exception as e:
            error = str(e)
    return render_template_string(LOGIN_HTML, error=error, msg=request.args.get("msg", ""))

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

@app.route("/api/start")
def api_start():
    bad = require_login_json()
    if bad:
        return bad
    made = request.args.get("made", "")
    shuffle_q = request.args.get("shuffle_q", "0").lower() in ("1", "true", "yes")
    shuffle_a = request.args.get("shuffle_a", "0").lower() in ("1", "true", "yes")
    level = clean(request.args.get("level", "")).upper()
    dang = clean(request.args.get("dang", ""))
    st = get_store()
    if not st.questions_loaded:
        st.start_questions_background(force=False)
        return jsonify({"error": "Dữ liệu đề đang nạp từ Google Sheet. Thầy chờ vài giây rồi bấm lại."}), 202
    return jsonify(st.start_quiz(made, shuffle_questions=shuffle_q, shuffle_options=shuffle_a, level_filter=level, dang_filter=dang))

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


def _api_ai_config_handler():
    if request.method == "GET":
        cfg = ai_runtime_config()
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
        })
    body = request.get_json(silent=True) or {}
    try:
        cfg = update_ai_runtime_config(body)
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
    keys = load_ai_keys(p)
    if not keys:
        return False, "Chưa có key trên Render ENV.", []
    details: List[Dict[str, Any]] = []
    ok_count = 0
    for idx, k in enumerate(keys, start=1):
        ok, msg = test_ai_key(p, k, model)
        details.append({"index": idx, "ok": ok, "message": msg})
        if ok:
            ok_count += 1
    if ok_count:
        summary = f"{ok_count}/{len(keys)} key Gemini OK."
        if ok_count < len(keys):
            summary += f" {len(keys) - ok_count} key lỗi/quota — app sẽ tự dùng key còn hoạt động."
        return True, summary, details
    first_err = details[0]["message"] if details else "Tất cả key đều lỗi."
    return False, f"0/{len(keys)} key OK. Lỗi key #1: {first_err}", details


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
    keys = load_ai_keys(p)
    if not keys:
        return False, "Chưa có key. Dán key AIza... tại 🔑 Key AI của tôi hoặc cấu hình Render.", []
    details: List[Dict[str, Any]] = []
    ok_count = 0
    for idx, k in enumerate(keys, start=1):
        ok, msg = test_ai_key(p, k, model)
        details.append({"index": idx, "ok": ok, "message": msg})
        if ok:
            ok_count += 1
    if ok_count:
        summary = f"{ok_count}/{len(keys)} key OK."
        if ok_count < len(keys):
            summary += f" {len(keys) - ok_count} key lỗi/quota — app tự chuyển key khác."
        return True, summary, details
    first_err = details[0]["message"] if details else "Tất cả key đều lỗi."
    return False, f"0/{len(keys)} key OK. Lỗi key #1: {first_err}", details


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
    key = _first_key_from_raw(body.get("api_keys"))
    if not key:
        key = _first_key_from_raw(body.get("gemini_keys"))
    if not key:
        key = _first_key_from_raw(body.get("openai_keys"))
    if not key:
        key = clean(body.get("api_key", ""))
    used_provider = provider
    if not key:
        keys = load_ai_keys("GEMINI" if provider in ["GEMINI", "AUTO"] else "OPENAI")
        if len(keys) >= 1:
            ok, msg, details = test_all_runtime_ai_keys(provider, model)
            return jsonify({
                "ok": ok,
                "message": msg,
                "provider_used": provider,
                "keys_tested": len(details),
                "keys_ok": sum(1 for d in details if d.get("ok")),
                "details": details,
            })
        key, used_provider = _resolve_runtime_test_key(provider)
    if not key:
        return jsonify({
            "ok": False,
            "message": "Chưa có key. Vào 🔑 Key AI của tôi → dán AIza... → Lưu key.",
        })
    ok, msg = test_ai_key(used_provider, key, model)
    return jsonify({"ok": ok, "message": msg, "provider_used": used_provider})


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

@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)