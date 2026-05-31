# -*- coding: utf-8 -*-
"""
APP V16 - Google Sheet luyện đề
- Đọc mục lục bằng cột A:J để lọc nhanh.
- Khi làm bài mới đọc A:U. Cột T là HinhAnh, cột U là QuyenTruyCap nếu có.
- Có đăng nhập, đăng ký TRIAL 3 ngày, phân quyền ADMIN/VIP/SVIP/FREE/TRIAL.
- ADMIN xem đáp án/lời giải ngay và sửa câu trực tiếp về Google Sheet.
- Hiển thị hình ảnh thật qua /img: Drive link, Drive file ID, link ảnh, hoặc mã/tên ảnh như 1 -> static/Images/1.png hoặc Drive folder.
"""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import mimetypes
import os
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gspread
from flask import Flask, Response, jsonify, redirect, render_template_string, request, session, url_for
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

APP_VERSION = "GOOGLE_SHEET_AJ_FILTER_HEADER_FULL_DYNAMIC_2026_05_31_V18"

SHEET_NAME_QUESTIONS = os.environ.get("SHEET_QUESTIONS", "Cau_Hoi")
SHEET_NAME_USERS = os.environ.get("SHEET_USERS", "HOC_VIEN")
SHEET_NAME_RESULTS = os.environ.get("SHEET_RESULTS", "Ket_Qua")
IMAGE_FOLDER_ID = os.environ.get("GOOGLE_IMAGE_FOLDER_ID", "").strip()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "luyen-de-vat-ly-secret-change-me")

_LOCK = threading.RLock()
_CATALOG_CACHE: Dict[str, Any] = {"time": 0, "items": [], "debug": {}}
_USERS_CACHE: Dict[str, Any] = {"time": 0, "items": {}}
_FULL_ROWS_CACHE: Dict[str, Any] = {"time": 0, "rows": [], "header_row": 1}
_ACTIVE_TOKENS: Dict[str, str] = {}

# ============================================================
# TIỆN ÍCH
# ============================================================

def strip_accents(s: Any) -> str:
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def norm(s: Any) -> str:
    s = strip_accents(str(s or "").strip().lower())
    s = re.sub(r"\s+", " ", s)
    return s


def clean(s: Any) -> str:
    s = str(s or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def stable_hash(text: str, n: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_date_any(s: Any) -> Optional[datetime]:
    s = clean(s)
    if not s:
        return None
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def make_key(row: Dict[str, str]) -> str:
    parts = [row.get("BoDe", ""), row.get("De", ""), row.get("Lop", ""), row.get("Mon", ""), row.get("Chuong", ""), row.get("BaiHoc", ""), row.get("DangBaiTap", "")]
    return "MD_" + stable_hash("|".join(norm(x) for x in parts), 12)


def normalize_role(s: Any) -> str:
    k = norm(s)
    if k in ["admin", "quan tri", "quantri"]:
        return "ADMIN"
    if k in ["s.vip", "svip", "s vip", "super vip"]:
        return "SVIP"
    if k == "vip":
        return "VIP"
    if k in ["trial", "dung thu", "dungthu", "thu"]:
        return "TRIAL"
    return "FREE"


def is_admin() -> bool:
    return session.get("role") == "ADMIN"


def current_user() -> Dict[str, Any]:
    if not session.get("mahs"):
        return {}
    return {
        "mahs": session.get("mahs"),
        "hoten": session.get("hoten", ""),
        "lop": session.get("lop", ""),
        "role": session.get("role", "FREE"),
    }

# ============================================================
# GOOGLE SHEET
# ============================================================

def get_credentials() -> Credentials:
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    if not raw:
        raise RuntimeError("Thiếu biến GOOGLE_CREDENTIALS_JSON trên Render")
    try:
        info = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"GOOGLE_CREDENTIALS_JSON không phải JSON hợp lệ: {e}")
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def get_book():
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("Thiếu biến GOOGLE_SHEET_ID trên Render")
    gc = gspread.authorize(get_credentials())
    return gc.open_by_key(sheet_id)


def get_ws(name: str):
    return get_book().worksheet(name)


def get_values_a1(sheet: str, a1: str) -> List[List[str]]:
    ws = get_ws(sheet)
    vals = ws.get(a1)
    return [[clean(x) for x in row] for row in vals]


def find_header_row(rows: List[List[str]]) -> int:
    for i, row in enumerate(rows[:10], start=1):
        joined = "|".join(norm(x) for x in row)
        if "id" in joined and "bode" in joined and "de" in joined and "lop" in joined:
            return i
    return 1


def pad(row: List[str], n: int) -> List[str]:
    return row + [""] * max(0, n - len(row))


def row_AJ_to_dict(row: List[str], row_number: int) -> Dict[str, str]:
    r = pad(row, 10)
    d = {
        "Row": str(row_number),
        "ID": r[0],
        "BoDe": r[1],
        "De": r[2],
        "Lop": r[3],
        "Mon": r[4],
        "Chuong": r[5],
        "BaiHoc": r[6],
        "DangBaiTap": r[7],
        "MucDo": r[8],
        "Dang": r[9],
    }
    d["MaDe"] = make_key(d)
    return d


# Các cột A:J dùng cố định để lọc mục lục.
# Từ K trở đi cho phép đổi thứ tự; app sẽ ưu tiên đọc theo tên tiêu đề.
# Nếu không có tiêu đề HinhAnh thì mặc định lấy cột T như thầy đang dùng.
FULL_FIELD_ALIASES = {
    "CauHoi": ["NoiDung", "Nội dung", "CauHoi", "Câu hỏi", "DeBai", "Đề bài"],
    "A": ["A", "PhuongAnA", "Phương án A", "LuaChonA", "Lựa chọn A"],
    "B": ["B", "PhuongAnB", "Phương án B", "LuaChonB", "Lựa chọn B"],
    "C": ["C", "PhuongAnC", "Phương án C", "LuaChonC", "Lựa chọn C"],
    "D": ["D", "PhuongAnD", "Phương án D", "LuaChonD", "Lựa chọn D"],
    "DapAn": ["DapAn", "Đáp án", "Dap an", "Answer"],
    "SaiSo": ["SaiSo", "Sai số", "Sai so", "Tolerance"],
    "LoiGiai": ["LoiGiai", "Lời giải", "Loi giai", "Giai", "Giải"],
    "HinhAnh": ["HinhAnh", "Hình ảnh", "Hinh anh", "LinkAnh", "Link ảnh", "LinkHinh", "Link hình", "Anh", "Ảnh", "Image", "ImageUrl", "URL ảnh"],
    "QuyenTruyCap": ["QuyenTruyCap", "Quyền truy cập", "Quyen", "Quyền", "LoaiDe", "Loại đề", "Goi", "Gói"],
}

def _header_map(headers: List[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for i, h in enumerate(headers):
        hn = norm(h)
        if hn and hn not in out:
            out[hn] = i
    return out

def _col_by_header(row: List[str], hmap: Dict[str, int], aliases: List[str], fallback_index: Optional[int] = None) -> str:
    for name in aliases:
        idx = hmap.get(norm(name))
        if idx is not None and idx < len(row):
            return clean(row[idx])
    if fallback_index is not None and fallback_index < len(row):
        return clean(row[fallback_index])
    return ""

def _looks_like_image_value(v: str) -> bool:
    v = clean(v)
    if not v:
        return False
    low = v.lower()
    if "drive.google.com" in low or "docs.google.com" in low:
        return True
    if low.startswith("http://") or low.startswith("https://"):
        return True
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", v):
        return True
    if re.search(r"\.(png|jpg|jpeg|webp|gif|svg)(\?|$)", low):
        return True
    return False

def row_full_to_dict(row: List[str], row_number: int, headers: List[str]) -> Dict[str, str]:
    # Đảm bảo ít nhất tới U để fallback T/U không lỗi.
    r = pad(row, 21)
    d = row_AJ_to_dict(r[:10], row_number)
    hmap = _header_map(headers)
    fallback = {
        "CauHoi": 10,  # K
        "A": 11,       # L
        "B": 12,       # M
        "C": 13,       # N
        "D": 14,       # O
        "DapAn": 15,   # P
        "SaiSo": 16,   # Q
        "LoiGiai": 17, # R
        "HinhAnh": 19, # T: theo file hiện tại của thầy
        "QuyenTruyCap": 20, # U nếu có
    }
    for field in ["CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo", "LoiGiai", "HinhAnh", "QuyenTruyCap"]:
        d[field] = _col_by_header(r, hmap, FULL_FIELD_ALIASES[field], fallback[field])

    # Nếu tiêu đề chưa chuẩn mà T trống, tự dò các cột sau R xem ô nào giống link/ID ảnh.
    if not d.get("HinhAnh"):
        for v in r[18:]:
            if _looks_like_image_value(v):
                d["HinhAnh"] = clean(v)
                break

    if not d.get("QuyenTruyCap"):
        d["QuyenTruyCap"] = "FREE"
    if not d["ID"]:
        d["ID"] = "AUTO_" + stable_hash(json.dumps(d, ensure_ascii=False), 10)
    return d


def load_catalog(force: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    with _LOCK:
        if not force and _CATALOG_CACHE["items"] and time.time() - _CATALOG_CACHE["time"] < 300:
            return _CATALOG_CACHE["items"], _CATALOG_CACHE["debug"]

    rows = get_values_a1(SHEET_NAME_QUESTIONS, "A:J")
    header_row = find_header_row(rows)
    data_rows = rows[header_row:]
    groups: Dict[str, Dict[str, Any]] = {}
    samples: List[Dict[str, str]] = []
    for idx, row in enumerate(data_rows, start=header_row + 1):
        d = row_AJ_to_dict(row, idx)
        if not d["ID"] and not d["De"] and not d["Mon"] and not d["BaiHoc"]:
            continue
        if len(samples) < 10:
            samples.append(d.copy())
        key = d["MaDe"]
        if key not in groups:
            groups[key] = {
                "MaDe": key,
                "BoDe": d["BoDe"],
                "De": d["De"],
                "Lop": d["Lop"],
                "Mon": d["Mon"],
                "Chuong": d["Chuong"],
                "BaiHoc": d["BaiHoc"],
                "DangBaiTap": d["DangBaiTap"],
                "MucDoSet": set(),
                "DangSet": set(),
                "Rows": [],
                "SoCau": 0,
            }
        g = groups[key]
        g["SoCau"] += 1
        g["Rows"].append(idx)
        if d["MucDo"]:
            g["MucDoSet"].add(d["MucDo"])
        if d["Dang"]:
            g["DangSet"].add(d["Dang"])

    items: List[Dict[str, Any]] = []
    for g in groups.values():
        item = dict(g)
        item["MucDo"] = ", ".join(sorted(g.pop("MucDoSet"), key=norm))
        item["Dang"] = ", ".join(sorted(g.pop("DangSet"), key=norm))
        item["QuyenTruyCap"] = "FREE"  # Mục lục A:J chưa đọc cột T, khi làm bài sẽ kiểm tra T.
        items.append(item)
    items.sort(key=lambda x: (norm(x.get("Mon")), norm(x.get("Lop")), norm(x.get("Chuong")), norm(x.get("BaiHoc")), norm(x.get("De"))))
    debug = {"mode": "EXACT_A_TO_J_FOR_FILTER", "header_row": header_row, "count_rows": len(data_rows), "count_catalog": len(items), "samples": samples, "time": now_str()}
    with _LOCK:
        _CATALOG_CACHE.update({"time": time.time(), "items": items, "debug": debug})
    return items, debug


def load_full_rows(force: bool = False) -> Tuple[List[Dict[str, str]], int]:
    with _LOCK:
        if not force and _FULL_ROWS_CACHE["rows"] and time.time() - _FULL_ROWS_CACHE["time"] < 300:
            return _FULL_ROWS_CACHE["rows"], _FULL_ROWS_CACHE["header_row"]
    # Đọc rộng tới AZ để không bị sai khi thầy chèn thêm cột sau J.
    # A:J vẫn là khóa lọc; K trở đi đọc theo tiêu đề/fallback.
    rows = get_values_a1(SHEET_NAME_QUESTIONS, "A:AZ")
    header_row = find_header_row(rows)
    headers = rows[header_row - 1] if rows and header_row - 1 < len(rows) else []
    out: List[Dict[str, str]] = []
    for idx, row in enumerate(rows[header_row:], start=header_row + 1):
        d = row_full_to_dict(row, idx, headers)
        if not d["ID"] and not d["De"] and not d["CauHoi"]:
            continue
        out.append(d)
    debug_extra = {"full_header_row": header_row, "headers": headers[:30]}
    with _LOCK:
        _FULL_ROWS_CACHE.update({"time": time.time(), "rows": out, "header_row": header_row, "debug": debug_extra})
    return out, header_row


def load_questions_by_made(made: str) -> List[Dict[str, str]]:
    rows, _ = load_full_rows(False)
    qs = [r for r in rows if r.get("MaDe") == made]
    return qs


def invalidate_question_cache():
    with _LOCK:
        _CATALOG_CACHE.update({"time": 0, "items": [], "debug": {}})
        _FULL_ROWS_CACHE.update({"time": 0, "rows": [], "header_row": 1})


def load_users(force: bool = False) -> Dict[str, Dict[str, str]]:
    with _LOCK:
        if not force and _USERS_CACHE["items"] and time.time() - _USERS_CACHE["time"] < 120:
            return _USERS_CACHE["items"]
    rows = get_ws(SHEET_NAME_USERS).get_all_records()
    users: Dict[str, Dict[str, str]] = {}
    for r in rows:
        mahs = clean(r.get("MaHS") or r.get("Mã HS") or r.get("ID") or "")
        if not mahs:
            continue
        phone = clean(r.get("SoDienThoai") or r.get("Số điện thoại") or r.get("SDT") or "")
        mk = clean(r.get("MatKhau") or r.get("Mật khẩu") or r.get("Password") or "")
        if not mk:
            digits = re.sub(r"\D+", "", phone)
            mk = digits[-6:] if len(digits) >= 6 else "123456"
        role = normalize_role(r.get("LoaiTaiKhoan") or r.get("Loại tài khoản") or r.get("Role") or "FREE")
        users[mahs] = {
            "mahs": mahs,
            "password": mk,
            "hoten": clean(r.get("HoTen") or r.get("HọTên") or r.get("Họ tên") or ""),
            "lop": clean(r.get("Lop") or r.get("Lớp") or ""),
            "role": role,
            "status": clean(r.get("TrangThai") or r.get("Trạng thái") or "ON").upper() or "ON",
            "phone": phone,
            "device": clean(r.get("DeviceId") or r.get("DeviceID") or ""),
            "trial_end": clean(r.get("NgayHetHanTrial") or r.get("NgayHetHanTaiKhoan") or r.get("Ngày hết hạn") or ""),
        }
    with _LOCK:
        _USERS_CACHE.update({"time": time.time(), "items": users})
    return users


def append_trial_user(mahs: str, hoten: str, lop: str, phone: str, password: str, device: str) -> None:
    ws = get_ws(SHEET_NAME_USERS)
    headers = [clean(x) for x in ws.row_values(1)]
    if not headers:
        raise RuntimeError("Sheet HOC_VIEN chưa có hàng tiêu đề")
    end = datetime.now() + timedelta(days=3)
    values_map = {
        "MaHS": mahs,
        "HoTen": hoten,
        "Lop": lop,
        "LoaiTaiKhoan": "TRIAL",
        "TrangThai": "ON",
        "SoDienThoai": phone,
        "MatKhau": password,
        "NgayDangKy": now_str(),
        "NgayHetHanTrial": end.strftime("%Y-%m-%d %H:%M:%S"),
        "DeviceId": device,
    }
    row = []
    for h in headers:
        hn = norm(h)
        val = ""
        for k, v in values_map.items():
            if norm(k) == hn:
                val = v
                break
        row.append(val)
    ws.append_row(row, value_input_option="USER_ENTERED")
    load_users(True)

# ============================================================
# HÌNH ẢNH
# ============================================================

def parse_drive_id(src: str) -> str:
    s = clean(src)
    if not s:
        return ""
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", s)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", s):
        return s
    return ""


def guess_mime(path_or_url: str) -> str:
    mt = mimetypes.guess_type(path_or_url)[0]
    return mt or "image/png"


def svg_error(message: str) -> bytes:
    msg = html.escape(message)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="110">
<rect width="100%" height="100%" fill="#fff7ed" stroke="#fb923c" stroke-width="2"/>
<text x="18" y="42" font-family="Arial" font-size="18" fill="#9a3412">Không hiển thị được hình ảnh</text>
<text x="18" y="74" font-family="Arial" font-size="15" fill="#7c2d12">{msg}</text>
</svg>'''.encode("utf-8")


def local_image_candidates(src: str) -> List[Path]:
    s = clean(src).strip().lstrip("/")
    roots = [Path(__file__).parent / "static" / "Images", Path(__file__).parent / "static" / "images", Path(__file__).parent / "Images"]
    cands: List[Path] = []
    if s:
        cands.append(Path(__file__).parent / s)
        for root in roots:
            cands.append(root / s)
            if "." not in Path(s).name:
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]:
                    cands.append(root / f"{s}{ext}")
    return cands


def drive_authed_session() -> AuthorizedSession:
    return AuthorizedSession(get_credentials())


def drive_download_file(file_id: str) -> Tuple[bytes, str]:
    authed = drive_authed_session()
    meta_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name,mimeType"
    meta = authed.get(meta_url, timeout=20)
    if meta.status_code >= 400:
        raise RuntimeError(f"Drive không đọc được file ID {file_id}: {meta.status_code}")
    mj = meta.json()
    mime = mj.get("mimeType") or "image/png"
    dl_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    r = authed.get(dl_url, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Drive không tải được ảnh: {r.status_code}")
    return r.content, mime


def drive_search_by_name(name: str) -> str:
    if not IMAGE_FOLDER_ID:
        return ""
    names = [name]
    if "." not in Path(name).name:
        names += [f"{name}{ext}" for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]]
    authed = drive_authed_session()
    for nm in names:
        q = f"'{IMAGE_FOLDER_ID}' in parents and trashed=false and name='{nm.replace(chr(39), chr(92)+chr(39))}'"
        url = "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode({"q": q, "fields": "files(id,name,mimeType)", "pageSize": "1"})
        r = authed.get(url, timeout=20)
        if r.status_code < 400:
            files = r.json().get("files", [])
            if files:
                return files[0]["id"]
    return ""


def read_image_bytes(src: str) -> Tuple[bytes, str]:
    s = clean(src)
    if not s:
        raise RuntimeError("Cột T:HinhAnh đang trống")

    # 1) File local trong repo: static/Images/1.png, static/Images/hinh1.png...
    for p in local_image_candidates(s):
        if p.exists() and p.is_file():
            return p.read_bytes(), guess_mime(str(p))

    # 2) Drive link hoặc Drive file ID.
    fid = parse_drive_id(s)
    if fid:
        return drive_download_file(fid)

    # 3) Nếu ô chỉ là 1, hinh1... và có GOOGLE_IMAGE_FOLDER_ID thì tìm trong thư mục Drive.
    fid2 = drive_search_by_name(s)
    if fid2:
        return drive_download_file(fid2)

    # 4) Link ảnh trực tiếp.
    if s.startswith("http://") or s.startswith("https://"):
        req = urllib.request.Request(s, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
            mt = resp.headers.get("Content-Type") or guess_mime(s)
            return data, mt

    raise RuntimeError(f"Cột T:HinhAnh đang là '{s}'. Cần có static/Images/{s}.png hoặc GOOGLE_IMAGE_FOLDER_ID chứa ảnh tên {s}.png, hoặc dán link/file ID Drive.")

# ============================================================
# CHẤM ĐIỂM
# ============================================================

def normalize_dang(s: str) -> str:
    k = norm(s)
    if "dung sai" in k or k in ["ds", "tf", "true false"]:
        return "Đúng sai"
    if "tra loi ngan" in k or k in ["tln", "short"]:
        return "Trả lời ngắn"
    if "tu luan" in k or k == "tl":
        return "Tự luận"
    return "Trắc nghiệm"


def norm_letter(s: str) -> str:
    m = re.search(r"[ABCD]", clean(s).upper())
    return m.group(0) if m else ""


def parse_float_vn(s: str) -> Optional[float]:
    s = clean(s).replace(" ", "")
    if not s:
        return None
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    try:
        return float(m.group(0)) if m else None
    except Exception:
        return None


def check_answer(q: Dict[str, str], ans: Any) -> Tuple[bool, str, str]:
    dang = normalize_dang(q.get("Dang", ""))
    correct_raw = clean(q.get("DapAn", ""))
    if dang == "Trắc nghiệm":
        c = norm_letter(correct_raw)
        ch = norm_letter(str(ans or ""))
        return bool(c and ch and c == ch), c, ch
    if dang == "Trả lời ngắn":
        cnum = parse_float_vn(correct_raw)
        anum = parse_float_vn(str(ans or ""))
        tol = parse_float_vn(q.get("SaiSo", "")) or 0.0
        if cnum is not None and anum is not None:
            return abs(cnum - anum) <= tol + 1e-12, correct_raw, str(ans or "")
        return norm(correct_raw) == norm(ans), correct_raw, str(ans or "")
    if dang == "Đúng sai":
        # Hỗ trợ đơn giản: đáp án dạng Đ,S,Đ,S hoặc D,S,D,S.
        def arr(x: Any) -> List[str]:
            if isinstance(x, list):
                return [("Đ" if norm(v) in ["d", "đ", "dung", "đung", "true"] else "S" if norm(v) in ["s", "sai", "false"] else "") for v in x]
            raw = strip_accents(clean(x).upper()).replace("DUNG", "D").replace("SAI", "S")
            return ["Đ" if z == "D" else "S" for z in re.findall(r"[DS]", raw)[:4]]
        c = arr(correct_raw)
        a = arr(ans)
        while len(a) < 4:
            a.append("")
        return bool(c and a[:len(c)] == c), ",".join(c), ",".join(a[:4])
    return False, correct_raw, str(ans or "")

# ============================================================
# HTML
# ============================================================

LOGIN_HTML = """
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Đăng nhập</title>
<style>body{font-family:Arial;background:#f3f6fb;margin:0}.box{max-width:430px;margin:8vh auto;background:#fff;border:1px solid #d6dee9;border-radius:16px;padding:22px;box-shadow:0 8px 28px #0001}.top{background:#1d4ed8;color:#fff;padding:14px 20px;font-weight:800}input,button{width:100%;padding:12px;margin:7px 0;border:1px solid #cbd5e1;border-radius:10px;font-size:15px}button{background:#1d4ed8;color:#fff;font-weight:800}.err{color:#b91c1c;background:#fee2e2;padding:10px;border-radius:10px}.muted{color:#64748b;font-size:13px}.trial{background:#16a34a}</style></head>
<body><div class="top">ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</div><div class="box">
<h2>Đăng nhập học viên</h2>{% if error %}<div class="err">{{error}}</div>{% endif %}
<form method="post" action="/login"><input name="mahs" placeholder="Mã học sinh / ADMIN" required><input name="password" placeholder="Mật khẩu" type="password" required><button>Đăng nhập</button></form>
<hr><h3>Đăng ký dùng thử 3 ngày</h3><p class="muted">Tài khoản dùng thử chỉ mở được đề FREE, không chấm điểm, không xem đáp án/lời giải.</p>
<form method="post" action="/trial-register"><input name="hoten" placeholder="Họ tên" required><input name="lop" placeholder="Lớp"><input name="phone" placeholder="Số điện thoại" required><input name="password" placeholder="Mật khẩu tự đặt" required><button class="trial">Đăng ký dùng thử</button></form>
</div></body></html>"""

INDEX_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Luyện đề</title>
<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\(','\\)']],displayMath:[['$$','$$'],['\\[','\\]']]},svg:{fontCache:'global'}};</script><script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>
body{margin:0;background:#f5f7fb;font-family:Arial,Helvetica,sans-serif;color:#111827}.top{background:#1d4ed8;color:#fff;padding:10px 18px;position:sticky;top:0;z-index:10}.wrap{max-width:1420px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid #d6dee9;border-radius:12px;padding:14px;margin-bottom:12px;box-shadow:0 1px 4px #0001}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:4px;min-width:160px;flex:1}.field label{font-size:12px;font-weight:700}select,input,textarea,button{font-family:inherit;font-size:15px;border:1px solid #cbd5e1;border-radius:8px;padding:9px 10px}button{font-weight:800;cursor:pointer}.btn{background:#1d4ed8;color:#fff;border-color:#1d4ed8}.btn2{background:#eef2ff;color:#1d4ed8}.green{background:#dcfce7;color:#166534;border-color:#bbf7d0}.red{background:#fee2e2;color:#991b1b;border-color:#fecaca}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}.card{background:#fff;border:1px solid #d6dee9;border-radius:12px;padding:12px}.card h3{margin:0 0 8px;color:#1e3a8a}.tag{display:inline-block;background:#eef2ff;color:#1d4ed8;border-radius:999px;padding:3px 9px;font-size:12px;font-weight:800;margin:2px}.line{height:1px;background:#dbe3ee;margin:10px 0}.muted{color:#64748b}.quiz{display:grid;grid-template-columns:1fr 260px;gap:12px}.qbox{border:1px solid #111;background:#fff;border-radius:8px;padding:14px;min-height:145px;line-height:1.55;font-size:18px}.opt{display:flex;gap:8px;align-items:flex-start;border:1px solid transparent;border-radius:10px;padding:10px;margin:7px 0}.correct{background:#dcfce7!important;border-color:#86efac!important}.wrong{background:#fee2e2!important;border-color:#fecaca!important}.solution{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px;margin-top:10px}.imgQ{display:block;max-width:100%;max-height:520px;margin:12px 0;border:1px solid #cbd5e1;border-radius:10px;background:#fff}.nav{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.num{padding:8px 0;background:#fff}.active{outline:3px solid #93c5fd}.adminbar{background:#ecfdf5;border:1px solid #86efac;color:#166534}.hide{display:none!important}.small{font-size:13px}@media(max-width:900px){.quiz{grid-template-columns:1fr}.qbox{font-size:16px}}
</style></head><body><div class="top"><b>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</b><span style="float:right">{{hoten}} | {{role}} | <a style="color:white" href="/logout">Thoát</a></span><br><small id="info">Đang nạp...</small></div><div class="wrap">
<div id="home"><div class="panel"><b>Thiết lập luyện tập</b><div class="row" style="margin-top:10px"><div class="field"><label>Môn</label><select id="fMon"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="fLop"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="fChuong"><option value="">Tất cả</option></select></div><div class="field"><label>Bài học</label><select id="fBaiHoc"><option value="">Tất cả</option></select></div><div class="field"><label>Bộ đề</label><select id="fBoDe"><option value="">Tất cả</option></select></div><div class="field"><label>Tìm nhanh</label><input id="fSearch" placeholder="Nhập từ khóa..."></div><button class="btn" onclick="renderCatalog()">Lọc đề</button>{% if role=='ADMIN' %}<button class="green" onclick="syncSheet()">ADMIN: Đồng bộ Sheet</button><button class="btn2" onclick="checkSheet()">ADMIN: Kiểm tra Sheet</button>{% endif %}</div></div><div id="loading" class="panel">⏳ Hệ thống đang nạp dữ liệu Google Sheet. Lần đầu Render Free vừa thức dậy có thể chờ 10–40 giây. Trang sẽ tự thử lại, không cần bấm nhiều lần.</div><div class="panel"><b>Mục lục đề</b> <span id="countCat" class="muted"></span><pre id="debug" class="small"></pre><div id="catalog" class="grid" style="margin-top:10px"></div></div></div>
<div id="quiz" class="hide"><div class="panel row" style="justify-content:space-between"><div><button class="btn2" onclick="backHome()">← Về mục lục</button> <b id="quizTitle"></b></div><div id="resultBox" style="font-weight:800"></div></div>{% if role=='ADMIN' %}<div class="panel adminbar">ADMIN: Đang ở chế độ soát đề. Thầy xem đáp án/lời giải ngay và có thể sửa câu hỏi trực tiếp.</div>{% endif %}<div class="quiz"><div><div class="panel"><div class="row" style="justify-content:space-between"><h2 id="qid"></h2><div><button id="btn5050" class="green" onclick="use5050()">Loại 2 câu sai</button><button id="btnSubmit" class="btn" onclick="submitQuiz()">Nộp bài</button></div></div><div id="qtext" class="qbox"></div><div id="options"></div><div id="solution" class="solution hide"></div>{% if role=='ADMIN' %}<div id="editBox" class="panel"></div>{% endif %}<div class="row" style="justify-content:space-between"><button onclick="prevQ()">← Câu trước</button><button onclick="nextQ()">Câu sau →</button></div></div></div><div class="panel"><b>Bảng câu hỏi</b><div id="nav" class="nav" style="margin-top:10px"></div></div></div></div>
</div><script>
const ROLE={{role|tojson}}; let META=null,CATALOG=[],SID='',QUESTIONS=[],CUR=0,ANS={},SUB=false,RES={};
function esc(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])).replace(/\n/g,'<br>')} function val(id){return document.getElementById(id).value} function typeset(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise().catch(()=>{})}
async function api(u,o={}){let r=await fetch(u,o); let t=await r.text(); let j=null; try{j=JSON.parse(t)}catch(e){if(r.status==401||t.includes('Đăng nhập học viên')){location.href='/login';return null} throw new Error('Máy chủ trả về HTML, không phải JSON. Hãy tải lại trang hoặc đăng nhập lại.')} if(!r.ok||j.error)throw new Error(j.error||'Lỗi'); return j}
function setOpts(id,a){document.getElementById(id).innerHTML='<option value="">Tất cả</option>'+a.map(x=>`<option>${esc(x)}</option>`).join('')}
async function init(){try{META=await api('/api/meta'); document.getElementById('loading').classList.add('hide'); CATALOG=META.catalog; document.getElementById('info').textContent=`${META.count_questions||''} dòng | ${META.count_catalog} mục | ${META.mode||''}`; for(let k of ['Mon','Lop','Chuong','BaiHoc','BoDe'])setOpts('f'+k,META.filters[k]||[]); renderCatalog()}catch(e){document.getElementById('loading').textContent='⏳ Đang nạp dữ liệu Google Sheet... '+e.message+' Trang sẽ tự thử lại sau 3 giây.'; setTimeout(init,3000)}}
function ok(x){let s=val('fSearch').toLowerCase(); let b=[x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.DangBaiTap,x.BoDe,x.De,x.MucDo,x.Dang].join(' ').toLowerCase(); return (!val('fMon')||x.Mon==val('fMon'))&&(!val('fLop')||x.Lop==val('fLop'))&&(!val('fChuong')||x.Chuong==val('fChuong'))&&(!val('fBaiHoc')||x.BaiHoc==val('fBaiHoc'))&&(!val('fBoDe')||x.BoDe==val('fBoDe'))&&(!s||b.includes(s))}
function renderCatalog(){let list=CATALOG.filter(ok); document.getElementById('countCat').textContent=`(${list.length} mục)`; document.getElementById('catalog').innerHTML=list.map(x=>`<div class="card"><h3>${esc(x.De||x.BaiHoc||'Đề')}</h3><span class="tag">${esc(x.Mon)}</span><span class="tag">Lớp ${esc(x.Lop)}</span><span class="tag">${esc(x.SoCau)} câu</span><div class="line"></div><b>Chương:</b> ${esc(x.Chuong)}<br><b>Bài:</b> ${esc(x.BaiHoc)}<br><b>Dạng:</b> ${esc(x.Dang)}<br><b>Mức độ:</b> ${esc(x.MucDo)}<br><b>Bộ đề:</b> ${esc(x.BoDe)}<div style="text-align:right;margin-top:10px"><button class="btn" onclick="startQuiz('${x.MaDe}')">Làm bài</button></div></div>`).join('')||'Không có đề phù hợp.'}
async function syncSheet(){await api('/api/admin/sync',{method:'POST'}); alert('Đã đồng bộ Sheet.'); await init()} async function checkSheet(){let j=await api('/api/admin/check'); document.getElementById('debug').textContent=JSON.stringify(j,null,2)}
async function startQuiz(made){try{let j=await api('/api/start?made='+encodeURIComponent(made)); SID=j.sid; QUESTIONS=j.questions; CUR=0; ANS={}; SUB=(ROLE=='ADMIN'); RES={}; if(j.results){for(let r of j.results)RES[r.index]=r} document.getElementById('home').classList.add('hide'); document.getElementById('quiz').classList.remove('hide'); document.getElementById('btnSubmit').style.display=(ROLE=='TRIAL'||ROLE=='ADMIN')?'none':''; renderQ()}catch(e){alert(e.message)}}
function save(){let q=QUESTIONS[CUR]; if(!q)return; if(q.Dang=='Trắc nghiệm'){let r=document.querySelector(`input[name="a${CUR}"]:checked`); if(r)ANS[CUR]=r.value}else{let el=document.getElementById('shortAns'); if(el)ANS[CUR]=el.value} renderNav()}
function renderNav(){let h=''; for(let i=0;i<QUESTIONS.length;i++){let c='num'; if(i==CUR)c+=' active'; if(SUB&&RES[i])c+=RES[i].ok?' correct':' wrong'; h+=`<button class="${c}" onclick="goQ(${i})">${i+1}</button>`} document.getElementById('nav').innerHTML=h}
function goQ(i){save(); CUR=i; renderQ()} function prevQ(){if(CUR>0){save();CUR--;renderQ()}} function nextQ(){if(CUR<QUESTIONS.length-1){save();CUR++;renderQ()}}
function renderQ(){let q=QUESTIONS[CUR]; renderNav(); document.getElementById('qid').textContent=`Câu ${CUR+1}/${QUESTIONS.length} | ID: ${q.ID} | ${q.MucDo} - ${q.Dang}`; let img=q.HinhAnh?`<img class="imgQ" src="/img?src=${encodeURIComponent(q.HinhAnh)}">`:''; document.getElementById('qtext').innerHTML=esc(q.CauHoi)+img; let h=''; if(q.Dang=='Trắc nghiệm'){for(let L of ['A','B','C','D']){if(!q[L])continue; let cls='opt'; if(SUB&&RES[CUR]){if(RES[CUR].correct==L)cls+=' correct'; if(RES[CUR].chosen==L&&RES[CUR].chosen!=RES[CUR].correct)cls+=' wrong'} h+=`<label id="opt${L}" class="${cls}"><input type="radio" name="a${CUR}" value="${L}" ${ANS[CUR]==L?'checked':''} ${SUB?'disabled':''} onchange="save()"><b>${L}.</b> <span>${esc(q[L])}</span></label>`}}else{h=`<textarea id="shortAns" style="width:100%;min-height:100px" ${SUB?'disabled':''} oninput="save()">${esc(ANS[CUR]||'')}</textarea>`} document.getElementById('options').innerHTML=h; let sol=document.getElementById('solution'); if(SUB&&RES[CUR]){sol.classList.remove('hide'); sol.innerHTML=`<b>Đáp án:</b> ${esc(RES[CUR].correct||RES[CUR].DapAn)}<div class="line"></div><b>Lời giải:</b><br>${esc(RES[CUR].LoiGiai||'Chưa có lời giải')}`}else sol.classList.add('hide'); if(ROLE=='ADMIN')renderEdit(q); typeset()}
function renderEdit(q){document.getElementById('editBox').innerHTML=`<h3>ADMIN: Sửa câu hỏi</h3><textarea id="eCauHoi" style="width:100%;min-height:80px">${esc(q.CauHoi)}</textarea><div class="row"><input id="eA" value="${esc(q.A)}" placeholder="A"><input id="eB" value="${esc(q.B)}" placeholder="B"><input id="eC" value="${esc(q.C)}" placeholder="C"><input id="eD" value="${esc(q.D)}" placeholder="D"></div><div class="row"><input id="eDapAn" value="${esc(q.DapAn)}" placeholder="Đáp án"><input id="eHinhAnh" value="${esc(q.HinhAnh)}" placeholder="Hình ảnh/link/ID/tên ảnh"><input id="eMucDo" value="${esc(q.MucDo)}" placeholder="Mức độ"><input id="eDang" value="${esc(q.Dang)}" placeholder="Dạng"></div><textarea id="eLoiGiai" style="width:100%;min-height:90px" placeholder="Lời giải">${esc(q.LoiGiai)}</textarea><button class="green" onclick="saveEdit()">Lưu vào Google Sheet</button>`}
async function saveEdit(){let q=QUESTIONS[CUR]; let payload={row:q.Row,CauHoi:val('eCauHoi'),A:val('eA'),B:val('eB'),C:val('eC'),D:val('eD'),DapAn:val('eDapAn'),HinhAnh:val('eHinhAnh'),MucDo:val('eMucDo'),Dang:val('eDang'),LoiGiai:val('eLoiGiai')}; await api('/api/admin/save-question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); alert('Đã lưu. Bấm đồng bộ nếu cần cập nhật mục lục.'); Object.assign(q,payload); renderQ()}
async function use5050(){let q=QUESTIONS[CUR]; if(q.Dang!='Trắc nghiệm')return alert('Chỉ dùng cho trắc nghiệm'); if(!(ROLE=='VIP'||ROLE=='SVIP'||ROLE=='ADMIN'))return alert('Chỉ VIP/S.VIP/ADMIN được dùng'); let c=String(q.DapAn||'').match(/[ABCD]/); c=c?c[0]:''; let wrong=['A','B','C','D'].filter(x=>x!=c&&q[x]); wrong.sort(()=>Math.random()-.5); for(let L of wrong.slice(0,2)){let el=document.getElementById('opt'+L); if(el){el.style.opacity=.25; el.style.textDecoration='line-through'}}}
async function submitQuiz(){save(); if(!confirm('Nộp bài?'))return; let j=await api('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,answers:ANS})}); SUB=true; RES={}; for(let r of j.results)RES[r.index]=r; document.getElementById('resultBox').textContent=`Điểm ${j.score}/10 | Đúng ${j.correct_count}/${j.auto_count}`; renderQ()}
function backHome(){document.getElementById('quiz').classList.add('hide'); document.getElementById('home').classList.remove('hide')}
init();
</script></body></html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route("/version")
def version():
    return jsonify({
        "version": APP_VERSION,
        "exact_AJ_filter": True,
        "full_rows_dynamic_header": True,
        "image_column": "header HinhAnh, fallback T",
        "quiz_reads_range": "A:AZ",
        "optional_env_GOOGLE_IMAGE_FOLDER_ID": bool(IMAGE_FOLDER_ID),
    })


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template_string(LOGIN_HTML, error=request.args.get("error", ""))
    mahs = clean(request.form.get("mahs"))
    pw = clean(request.form.get("password"))
    users = load_users(False)
    u = users.get(mahs)
    if not u or u.get("password") != pw:
        return render_template_string(LOGIN_HTML, error="Sai mã học sinh hoặc mật khẩu")
    if u.get("status") not in ["ON", "ACTIVE", ""]:
        return render_template_string(LOGIN_HTML, error="Tài khoản đang bị khóa")
    if u.get("role") == "TRIAL":
        end = parse_date_any(u.get("trial_end"))
        if end and datetime.now() > end:
            return render_template_string(LOGIN_HTML, error="Tài khoản dùng thử đã hết hạn")
    token = stable_hash(mahs + str(time.time()) + os.urandom(8).hex(), 24)
    _ACTIVE_TOKENS[mahs] = token
    session.update({"mahs": mahs, "hoten": u.get("hoten"), "lop": u.get("lop"), "role": u.get("role"), "token": token})
    return redirect("/")


@app.route("/trial-register", methods=["POST"])
def trial_register():
    hoten = clean(request.form.get("hoten"))
    lop = clean(request.form.get("lop"))
    phone = clean(request.form.get("phone"))
    password = clean(request.form.get("password")) or "123456"
    digits = re.sub(r"\D+", "", phone)
    if len(digits) < 6:
        return render_template_string(LOGIN_HTML, error="Số điện thoại chưa hợp lệ")
    users = load_users(True)
    for u in users.values():
        if re.sub(r"\D+", "", u.get("phone", "")) == digits:
            return render_template_string(LOGIN_HTML, error="Số điện thoại này đã đăng ký")
    mahs = "TRIAL_" + stable_hash(digits + str(time.time()), 8).upper()
    device = request.headers.get("User-Agent", "")[:80]
    append_trial_user(mahs, hoten, lop, phone, password, device)
    return render_template_string(LOGIN_HTML, error=f"Đăng ký thành công. Mã đăng nhập: {mahs}. Mật khẩu: {password}")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


def require_login():
    if not session.get("mahs"):
        return False
    # Đá phiên cũ nếu có phiên mới đăng nhập cùng tài khoản.
    token = _ACTIVE_TOKENS.get(session.get("mahs"))
    if token and token != session.get("token"):
        session.clear()
        return False
    return True


@app.route("/")
def home():
    if not require_login():
        return redirect("/login")
    return render_template_string(INDEX_HTML, **current_user())


@app.route("/api/meta")
def api_meta():
    if not require_login():
        return jsonify(error="Chưa đăng nhập"), 401
    items, debug = load_catalog(False)
    def opts(field: str):
        return sorted({clean(x.get(field, "")) for x in items if clean(x.get(field, ""))}, key=norm)
    return jsonify({
        "mode": debug.get("mode"),
        "count_catalog": len(items),
        "count_questions": debug.get("count_rows"),
        "filters": {"Mon": opts("Mon"), "Lop": opts("Lop"), "Chuong": opts("Chuong"), "BaiHoc": opts("BaiHoc"), "BoDe": opts("BoDe")},
        "catalog": items,
    })


@app.route("/api/admin/sync", methods=["POST"])
def api_admin_sync():
    if not is_admin():
        return jsonify(error="Chỉ ADMIN"), 403
    invalidate_question_cache()
    load_catalog(True)
    load_full_rows(True)
    return jsonify(ok=True, time=now_str())


@app.route("/api/admin/check")
def api_admin_check():
    if not is_admin():
        return jsonify(error="Chỉ ADMIN"), 403
    items, debug = load_catalog(False)
    return jsonify({"version": APP_VERSION, "catalog_count": len(items), "debug": debug})


@app.route("/api/start")
def api_start():
    if not require_login():
        return jsonify(error="Chưa đăng nhập"), 401
    made = clean(request.args.get("made"))
    qs = load_questions_by_made(made)
    if not qs:
        return jsonify(error="Không có câu hỏi trong đề này hoặc MaDe chưa khớp"), 404
    role = session.get("role", "FREE")
    # Quyền truy cập: nếu có câu VIP thì TRIAL/FREE không được mở.
    access = "FREE"
    for q in qs:
        if norm(q.get("QuyenTruyCap")) in ["vip", "s.vip", "svip"]:
            access = "VIP"
            break
    if access == "VIP" and role not in ["VIP", "SVIP", "ADMIN"]:
        return jsonify(error="Đề này dành cho VIP/S.VIP. Tài khoản hiện tại không được mở."), 403
    sid = stable_hash(made + session.get("mahs", "") + str(time.time()), 16)
    session["sid"] = sid
    session["quiz_made"] = made
    public = []
    results = []
    for i, q in enumerate(qs):
        qq = {k: q.get(k, "") for k in ["Row","ID","MaDe","Dang","MucDo","CauHoi","A","B","C","D","DapAn","SaiSo","LoiGiai","HinhAnh","QuyenTruyCap"]}
        qq["Dang"] = normalize_dang(qq.get("Dang", ""))
        public.append(qq)
        if role == "ADMIN":
            results.append({"index": i, "ok": True, "correct": norm_letter(q.get("DapAn")) or q.get("DapAn"), "chosen": "", "DapAn": q.get("DapAn"), "LoiGiai": q.get("LoiGiai")})
    return jsonify({"sid": sid, "questions": public, "admin": role == "ADMIN", "results": results})


@app.route("/api/submit", methods=["POST"])
def api_submit():
    if not require_login():
        return jsonify(error="Chưa đăng nhập"), 401
    role = session.get("role", "FREE")
    if role == "TRIAL":
        return jsonify(error="Tài khoản dùng thử không chấm điểm và không nộp bài."), 403
    body = request.get_json(silent=True) or {}
    made = session.get("quiz_made", "")
    qs = load_questions_by_made(made)
    answers = body.get("answers", {})
    results = []
    correct_count = 0
    auto_count = 0
    for i, q in enumerate(qs):
        ok, correct, chosen = check_answer(q, answers.get(str(i), ""))
        if normalize_dang(q.get("Dang")) != "Tự luận":
            auto_count += 1
            correct_count += 1 if ok else 0
        results.append({"index": i, "ID": q.get("ID"), "ok": ok, "correct": correct, "chosen": chosen, "DapAn": q.get("DapAn"), "LoiGiai": q.get("LoiGiai")})
    score = round(10 * correct_count / auto_count, 2) if auto_count else 0
    # Ghi Ket_Qua nếu có sheet.
    try:
        ws = get_ws(SHEET_NAME_RESULTS)
        ws.append_row([now_str(), session.get("mahs"), session.get("hoten"), made, score, correct_count, auto_count], value_input_option="USER_ENTERED")
    except Exception:
        pass
    return jsonify({"score": score, "correct_count": correct_count, "auto_count": auto_count, "results": results})


@app.route("/api/admin/save-question", methods=["POST"])
def api_admin_save_question():
    if not is_admin():
        return jsonify(error="Chỉ ADMIN"), 403
    body = request.get_json(silent=True) or {}
    row = int(body.get("row") or 0)
    if row <= 1:
        return jsonify(error="Row không hợp lệ"), 400
    ws = get_ws(SHEET_NAME_QUESTIONS)
    # A:J cố định; từ K trở đi tìm cột theo tiêu đề, fallback theo bố cục thường dùng.
    headers = [clean(x) for x in ws.row_values(1)]
    hmap = _header_map(headers)
    def col_letter(idx0: int) -> str:
        n = idx0 + 1
        out = ""
        while n:
            n, r = divmod(n - 1, 26)
            out = chr(65 + r) + out
        return out
    fallback_idx = {"MucDo":8, "Dang":9, "CauHoi":10, "A":11, "B":12, "C":13, "D":14, "DapAn":15, "SaiSo":16, "LoiGiai":17, "HinhAnh":19, "QuyenTruyCap":20}
    save_aliases = dict(FULL_FIELD_ALIASES)
    save_aliases.update({"MucDo":["MucDo", "Mức độ", "Muc do"], "Dang":["Dang", "Dạng" ]})
    updates = []
    for k, aliases in save_aliases.items():
        if k not in body:
            continue
        idx = None
        for name in aliases:
            idx = hmap.get(norm(name))
            if idx is not None:
                break
        if idx is None:
            idx = fallback_idx.get(k)
        if idx is not None:
            updates.append({"range": f"{col_letter(idx)}{row}", "values": [[clean(body.get(k))]]})
    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        invalidate_question_cache()
    return jsonify(ok=True, row=row)


@app.route("/img")
def img_route():
    src = request.args.get("src", "")
    try:
        data, mt = read_image_bytes(src)
        return Response(data, mimetype=mt, headers={"Cache-Control": "public, max-age=3600"})
    except Exception as e:
        return Response(svg_error(str(e)), mimetype="image/svg+xml")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
