# -*- coding: utf-8 -*-
"""
app.py - Ứng dụng luyện đề Google Sheet + đăng nhập + ADMIN sửa câu
Chạy Render:
    gunicorn app:app --bind 0.0.0.0:$PORT
Yêu cầu Environment Variables trên Render:
    GOOGLE_SHEET_ID
    GOOGLE_CREDENTIALS_JSON
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
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:  # Cho phép app vẫn mở nếu chưa cài gspread local
    gspread = None
    Credentials = None

APP_VERSION = "V10_WORKING_ADMIN_EDIT_DELETE_GS_2026_05_31"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "luyen-de-vat-ly-secret-key-change-me")

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
    if any(x in k for x in ["dung sai", "true false", "tf", "ds", "d s"]):
        return "Đúng sai"
    if any(x in k for x in ["tra loi ngan", "short", "tln", "shortans"]):
        return "Trả lời ngắn"
    if any(x in k for x in ["tu luan", "essay", "tl"]):
        return "Tự luận"
    return "Trắc nghiệm"


def norm_role(s: Any) -> str:
    k = key_norm(s).replace(".", "")
    if "admin" in k:
        return "ADMIN"
    if "svip" in k or "s vip" in k or "super" in k:
        return "S.VIP"
    if "trial" in k or "dung thu" in k or "thu nghiem" in k:
        return "TRIAL"
    if "vip" in k:
        return "VIP"
    if "free" in k or "mien phi" in k:
        return "FREE"
    return clean(s).upper() or "FREE"


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
    q["Dang"] = norm_dang(q.get("Dang"))
    if not q.get("MaDe"):
        base = "|".join(key_norm(q.get(x, "")) for x in ["Lop", "Mon", "Chuong", "BaiHoc", "DangBaiTap", "BoDe", "De"])
        q["MaDe"] = "MD_" + stable_hash(base, 12)
    if not q.get("ID"):
        q["ID"] = "AUTO_" + stable_hash(json.dumps(q, ensure_ascii=False), 10)
    return q


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
                    q[field] = clean(row_vals[col0])

            # Cột T là link hình ảnh. Ưu tiên T nếu T có link/file ID hợp lệ.
            if 19 < len(row_vals):
                t_img = clean(row_vals[19])
                if is_probably_link_or_drive(t_img) or (t_img and not clean(q.get("HinhAnh"))):
                    q["HinhAnh"] = t_img

            # Cột U là quyền truy cập nếu có; trống thì FREE.
            if 20 < len(row_vals) and not clean(q.get("QuyenTruyCap")):
                q["QuyenTruyCap"] = clean(row_vals[20])

            q["HinhAnh"] = normalize_image_src(q.get("HinhAnh"))

            if not clean(q.get("CauHoi")):
                continue
            q["_row"] = idx
            self.questions.append(q)
        self.by_made = {}
        for q in self.questions:
            self.by_made.setdefault(q["MaDe"], []).append(q)
        self.catalog = self.build_catalog()

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
            made = q["MaDe"]
            if made not in groups:
                groups[made] = {
                    "MaDe": made,
                    "Lop": q.get("Lop", ""), "Mon": q.get("Mon", ""), "Chuong": q.get("Chuong", ""),
                    "BaiHoc": q.get("BaiHoc", ""), "DangBaiTap": q.get("DangBaiTap", ""),
                    "BoDe": q.get("BoDe", ""), "De": q.get("De", ""),
                    "SoCau": 0, "MucDoSet": set(), "DangSet": set(), "QuyenTruyCapSet": set()
                }
            g = groups[made]
            g["SoCau"] += 1
            if q.get("MucDo"):
                g["MucDoSet"].add(q["MucDo"])
            if q.get("Dang"):
                g["DangSet"].add(q["Dang"])
            access = access_level_from_text(q.get("QuyenTruyCap", ""))
            g["QuyenTruyCapSet"].add(access)
        out: List[Dict[str, Any]] = []
        for g in groups.values():
            item = dict(g)
            item["MucDo"] = ", ".join(sorted(item.pop("MucDoSet"), key=key_norm))
            item["Dang"] = ", ".join(sorted(item.pop("DangSet"), key=key_norm))
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
        d["HinhAnh"] = normalize_image_src(d.get("HinhAnh"))
        d["index"] = index
        if reveal:
            d["DapAn"] = q.get("DapAn", "")
            d["LoiGiai"] = q.get("LoiGiai", "")
            d["SaiSo"] = q.get("SaiSo", "")
            d["_row"] = q.get("_row", "")
        return d

    def start_quiz(self, made: str) -> Dict[str, Any]:
        qs = list(self.by_made.get(made, []))
        if not qs:
            raise RuntimeError("Không có câu hỏi trong đề này. Có thể mã đề bị lệch, hãy bấm Đồng bộ dữ liệu.")
        access_level = quiz_access_level(qs)
        if is_trial() and access_level != "FREE":
            raise RuntimeError("Tài khoản dùng thử chỉ mở được đề FREE, không mở được đề VIP.")
        sid = stable_hash(f"{session.get('mahs')}|{made}|{time.time()}|{random.random()}", 18)
        self.quiz_sessions[sid] = {"made": made, "mahs": session.get("mahs"), "created": time.time(), "questions": qs, "used_5050": set(), "access_level": access_level}
        reveal = is_admin()
        return {
            "sid": sid,
            "admin": is_admin(),
            "is_trial": is_trial(),
            "access_level": access_level,
            "can_5050": can_use_5050(),
            "can_submit_score": not is_trial(),
            "trial_message": "Tài khoản dùng thử: chỉ luyện đề FREE, không nộp/chấm điểm và không xem đáp án/lời giải." if is_trial() else "",
            "questions": [self.public_question(q, i, reveal=reveal) for i, q in enumerate(qs)]
        }

    def check_quiz_session(self, sid: str) -> Dict[str, Any]:
        ses = self.quiz_sessions.get(sid)
        if not ses:
            raise RuntimeError("Phiên làm bài đã hết hạn")
        if ses.get("mahs") != session.get("mahs"):
            raise RuntimeError("Phiên làm bài không thuộc tài khoản hiện tại")
        return ses

    def fifty_fifty(self, sid: str, index: int) -> Dict[str, Any]:
        if not can_use_5050():
            raise RuntimeError("Tài khoản này chưa được dùng Loại 2 câu sai")
        ses = self.check_quiz_session(sid)
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

    def submit(self, sid: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        if is_trial():
            raise RuntimeError("Tài khoản dùng thử không được nộp/chấm điểm. Thầy chỉ cho luyện thử các đề FREE trong 3 ngày.")
        ses = self.check_quiz_session(sid)
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
        self.save_result(ses.get("made"), qs, score, correct_count, auto_count, results)
        return {"score": score, "correct_count": correct_count, "auto_count": auto_count, "total": len(qs), "show_solution": reveal, "results": results}

    def save_result(self, made: str, qs: List[Dict[str, Any]], score: float, so_dung: int, tong: int, results: List[Dict[str, Any]]):
        try:
            u = current_user_public()
            ten_de = qs[0].get("De") or qs[0].get("BaiHoc") or made if qs else made
            self.ws_results.append_row([
                now_str(), u.get("mahs"), u.get("hoten"), u.get("lop"), u.get("role"), made, ten_de, score, so_dung, tong,
                json.dumps(results, ensure_ascii=False)
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

        # Nạp lại dữ liệu sau khi lưu để ADMIN xem đúng ngay.
        self.load_questions()
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

        # Nạp lại dữ liệu để mục lục và câu hỏi không còn câu đã xóa.
        self.load_questions()
        return {"ok": True, "deleted": True, "row": row_number, "id": actual_id or question_id}


def check_answer(q: Dict[str, Any], user_answer: Any) -> Tuple[bool, str, str]:
    dang = norm_dang(q.get("Dang"))
    correct_raw = clean(q.get("DapAn"))
    if dang == "Trắc nghiệm":
        c = norm_letter(correct_raw)
        ch = norm_letter(user_answer)
        return bool(c and ch and c == ch), c, ch
    if dang == "Đúng sai":
        def tf_list(x):
            if isinstance(x, list):
                return ["Đ" if key_norm(v) in ["d", "đ", "dung", "đung", "đúng"] else "S" if key_norm(v) in ["s", "sai"] else "" for v in x][:4]
            s = strip_accents(clean(x).upper()).replace("DUNG", "D").replace("TRUE", "D").replace("SAI", "S").replace("FALSE", "S")
            vals = re.findall(r"[DS]", s)[:4]
            return ["Đ" if v == "D" else "S" for v in vals]
        corr = tf_list(correct_raw)
        chosen = tf_list(user_answer)
        while len(chosen) < 4:
            chosen.append("")
        return len(corr) == 4 and corr == chosen[:4], ",".join(corr), ",".join(chosen[:4])
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

STORE: Optional[SheetStore] = None

def get_store(force_reload: bool = False) -> SheetStore:
    global STORE
    if STORE is None:
        STORE = SheetStore()
    if force_reload:
        STORE.ensure_questions_loaded(force=True)
    return STORE


def current_user_public() -> Dict[str, Any]:
    return {
        "mahs": session.get("mahs", ""),
        "hoten": session.get("hoten", ""),
        "lop": session.get("lop", ""),
        "role": session.get("role", ""),
        "is_admin": is_admin(),
        "is_trial": is_trial(),
        "can_5050": can_use_5050(),
        "can_submit_score": not is_trial(),
        "trial_until": session.get("trial_until", ""),
        "account_until": session.get("account_until", ""),
    }

# ============================================================
# HTML
# ============================================================

LOGIN_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Đăng nhập luyện đề</title>
<style>body{margin:0;background:#f3f6fb;font-family:Arial,sans-serif}.box{max-width:460px;margin:55px auto;background:#fff;border:1px solid #d9e2ef;border-radius:16px;padding:24px;box-shadow:0 8px 30px #0001}.top{background:#1d4ed8;color:#fff;padding:16px 20px;font-weight:800}input,button{width:100%;padding:12px;margin:8px 0;border-radius:10px;border:1px solid #cbd5e1;font-size:16px}button{background:#1d4ed8;color:white;font-weight:800;cursor:pointer}.err{background:#fee2e2;color:#991b1b;padding:10px;border-radius:10px;margin:8px 0}.ok{background:#dcfce7;color:#166534;padding:10px;border-radius:10px;margin:8px 0}.hint{font-size:13px;color:#64748b;line-height:1.5}.link{display:block;text-align:center;margin-top:12px;color:#1d4ed8;font-weight:800;text-decoration:none}</style></head><body>
<div class="top">ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</div>
<div class="box"><h2>Đăng nhập học viên</h2>{% if error %}<div class="err">{{error}}</div>{% endif %}{% if msg %}<div class="ok">{{msg}}</div>{% endif %}
<form method="post"><input type="hidden" name="device_id" id="device_id"><label>Mã học sinh / tài khoản</label><input name="mahs" autofocus required placeholder="VD: HS001 hoặc TRIAL_xxxx"><label>Mật khẩu</label><input name="password" type="password" required placeholder="Nhập mật khẩu"><button>Đăng nhập</button></form>
<a class="link" href="/register">Đăng ký dùng thử miễn phí 3 ngày</a>
<div class="hint">Tài khoản lấy từ sheet <b>HOC_VIEN</b>. ADMIN được xem đáp án và sửa câu hỏi trực tiếp. Tài khoản dùng thử chỉ được đăng ký 1 lần theo số điện thoại và thiết bị; chỉ luyện đề FREE, không chấm điểm.</div></div>
<script>function did(){let k='LDVL_DEVICE_ID';let v=localStorage.getItem(k);if(!v){v='DEV_'+Date.now()+'_'+Math.random().toString(36).slice(2,10);localStorage.setItem(k,v)}document.getElementById('device_id').value=v}did();</script></body></html>
"""


REGISTER_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Đăng ký dùng thử</title>
<style>body{margin:0;background:#f3f6fb;font-family:Arial,sans-serif}.box{max-width:500px;margin:40px auto;background:#fff;border:1px solid #d9e2ef;border-radius:16px;padding:24px;box-shadow:0 8px 30px #0001}.top{background:#1d4ed8;color:#fff;padding:16px 20px;font-weight:800}input,button,select{width:100%;padding:12px;margin:8px 0;border-radius:10px;border:1px solid #cbd5e1;font-size:16px}button{background:#1d4ed8;color:white;font-weight:800;cursor:pointer}.err{background:#fee2e2;color:#991b1b;padding:10px;border-radius:10px;margin:8px 0}.hint{font-size:13px;color:#64748b;line-height:1.5}.link{display:block;text-align:center;margin-top:12px;color:#1d4ed8;font-weight:800;text-decoration:none}</style></head><body>
<div class="top">ĐĂNG KÝ DÙNG THỬ 3 NGÀY</div>
<div class="box"><h2>Tạo tài khoản dùng thử</h2>{% if error %}<div class="err">{{error}}</div>{% endif %}
<form method="post"><input type="hidden" name="device_id" id="device_id"><label>Họ tên học sinh</label><input name="hoten" required placeholder="Nhập họ tên"><label>Lớp</label><input name="lop" placeholder="VD: 12QT1"><label>Số điện thoại</label><input name="phone" required inputmode="tel" placeholder="Nhập số điện thoại"><label>Mật khẩu</label><input name="password" type="password" required placeholder="Tối thiểu 4 ký tự"><button>Đăng ký và vào làm bài</button></form>
<a class="link" href="/login">Đã có tài khoản? Đăng nhập</a>
<div class="hint">Mỗi số điện thoại và mỗi thiết bị chỉ được đăng ký dùng thử 1 lần. Tài khoản dùng thử được dùng 3 ngày, chỉ mở được các đề FREE. Tài khoản dùng thử không mở đề VIP, không nộp/chấm điểm, không xem đáp án/lời giải và không dùng Loại 2 câu sai.</div></div>
<script>function did(){let k='LDVL_DEVICE_ID';let v=localStorage.getItem(k);if(!v){v='DEV_'+Date.now()+'_'+Math.random().toString(36).slice(2,10);localStorage.setItem(k,v)}document.getElementById('device_id').value=v}did();</script></body></html>
"""

APP_HTML = r"""
<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Luyện đề</title>
<script>window.MathJax={tex:{inlineMath:[["$","$"],["\\(","\\)"]],displayMath:[["$$","$$"],["\\[","\\]"]]},svg:{fontCache:"global"}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>
:root{--blue:#1d4ed8;--border:#d7e0ed;--bg:#f5f7fb;--green:#dcfce7;--red:#fee2e2;--yellow:#fff7ed}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:Arial,Helvetica,sans-serif;font-size:15px}.top{position:sticky;top:0;z-index:9;background:var(--blue);color:#fff;padding:10px 14px;box-shadow:0 2px 8px #0002}.top h1{font-size:18px;margin:0}.top a{color:#fff}.wrap{max-width:1420px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid var(--border);border-radius:12px;padding:12px;margin-bottom:12px;box-shadow:0 1px 4px #0001}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:4px;min-width:160px;flex:1}.field label{font-weight:700;font-size:12px}select,input,textarea,button{font-family:inherit;font-size:14px;border:1px solid var(--border);border-radius:8px;padding:9px 10px;background:#fff}button{cursor:pointer;font-weight:800}.btn{background:var(--blue);border-color:var(--blue);color:#fff}.btn2{background:#eef2ff;color:#1d4ed8}.btnGreen{background:#dcfce7;color:#166534}.btnRed{background:#fee2e2;color:#991b1b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}.card{border:1px solid var(--border);border-radius:12px;background:#fff;padding:12px}.card h3{margin:0 0 8px;color:#1e3a8a}.tag{display:inline-block;background:#eef2ff;color:#1d4ed8;padding:3px 8px;border-radius:999px;font-size:12px;font-weight:800;margin:2px}.line{height:1px;background:var(--border);margin:10px 0}.muted{color:#64748b}.hide{display:none!important}.quizLayout{display:grid;grid-template-columns:1fr 270px;gap:12px}.qid{font-size:19px;font-weight:800}.qbox{border:1px solid #111827;background:#fff;border-radius:8px;padding:14px;min-height:150px;line-height:1.55;font-size:18px}.opt{display:flex;gap:8px;align-items:flex-start;padding:10px;border-radius:10px;border:1px solid transparent;margin:7px 0;background:#fff}.opt:hover{background:#f8fafc}.correct{background:var(--green)!important;border-color:#86efac!important}.wrong{background:var(--red)!important;border-color:#fecaca!important}.hidden5050{opacity:.25;pointer-events:none;text-decoration:line-through}.solution{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px;margin-top:12px}.navNums{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.num{padding:8px 0;border-radius:8px;border:1px solid var(--border);background:#fff}.num.active{outline:3px solid #93c5fd}.num.answered{background:#fef3c7}.num.ok{background:var(--green);color:#166534}.num.bad{background:var(--red);color:#991b1b}.tfrow{display:grid;grid-template-columns:35px 1fr 85px 85px;gap:7px;border:1px solid var(--border);border-radius:10px;padding:8px;margin:7px 0}.modal{position:fixed;inset:0;background:#0008;z-index:20;display:flex;align-items:center;justify-content:center;padding:15px}.modalBox{background:#fff;border-radius:14px;padding:16px;max-width:900px;width:100%;max-height:90vh;overflow:auto}.editGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.editGrid textarea{min-height:80px;width:100%}@media(max-width:900px){.quizLayout{grid-template-columns:1fr}.editGrid{grid-template-columns:1fr}.qbox{font-size:16px}.top h1{font-size:16px}}
</style></head>
<body><div class="top"><h1>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</h1><div><span id="info">Đang nạp...</span> | <span id="me"></span> | <a href="/logout">Thoát</a></div></div>
<div class="wrap">
<div id="home"><div class="panel"><b>Thiết lập luyện tập</b><div class="row" style="margin-top:10px"><div class="field"><label>Môn</label><select id="fMon"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="fLop"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="fChuong"><option value="">Tất cả</option></select></div><div class="field"><label>Bài học</label><select id="fBaiHoc"><option value="">Tất cả</option></select></div><div class="field"><label>Bộ đề</label><select id="fBoDe"><option value="">Tất cả</option></select></div><div class="field"><label>Tìm nhanh</label><input id="fSearch" placeholder="Nhập từ khóa..."></div><button class="btn" onclick="renderCatalog()">Lọc đề</button><button id="syncBtn" class="btnGreen hide" onclick="syncData()">ADMIN: Đồng bộ Sheet</button></div></div><div class="panel"><b>Mục lục đề</b> <span id="countCat" class="muted"></span><div id="catalog" class="grid" style="margin-top:10px"></div></div></div>
<div id="quiz" class="hide"><div class="panel row" style="justify-content:space-between"><div><button class="btn2" onclick="backHome()">← Về mục lục</button> <span id="quizTitle" style="font-weight:800"></span></div><div id="resultBox" style="font-weight:800;font-size:18px"></div></div><div class="quizLayout"><div><div class="panel"><div class="row" style="justify-content:space-between;align-items:center"><div class="qid" id="qid"></div><div><button id="btn5050" class="btnGreen" onclick="use5050()">Loại 2 câu sai</button><button id="btnEdit" class="btn2 hide" onclick="openEdit()">ADMIN: Sửa câu</button><button id="btnSubmit" class="btn" onclick="submitQuiz()">Nộp bài</button></div></div><div id="qtext" class="qbox"></div><div id="options"></div><div id="solution" class="solution hide"></div><div class="row" style="justify-content:space-between;margin-top:12px"><button onclick="prevQ()">← Câu trước</button><button onclick="nextQ()">Câu sau →</button></div></div></div><div class="panel"><b>Bảng câu hỏi</b><div id="navNums" class="navNums" style="margin-top:10px"></div><div class="line"></div><div class="muted">ADMIN vào đề sẽ thấy đáp án/lời giải ngay và được sửa câu.</div></div></div></div>
</div><div id="modal" class="modal hide"><div class="modalBox"><h3>ADMIN: Sửa câu hỏi</h3><div id="editForm" class="editGrid"></div><div class="row" style="justify-content:space-between;margin-top:12px"><button class="btnRed" onclick="deleteQuestion()">Xóa câu này khỏi Google Sheet</button><div><button onclick="closeEdit()">Hủy</button><button class="btn" onclick="saveEdit()">Lưu vào Google Sheet</button></div></div><div class="muted" style="margin-top:8px">Lưu ý: nút xóa sẽ xóa nguyên dòng câu hỏi trong sheet Cau_Hoi và đồng bộ lại dữ liệu.</div></div></div>
<script>
let META=null,CATALOG=[],USER={},SID='',QUESTIONS=[],CUR=0,ANSWERS={},SUBMITTED=false,RESULTS={};
function esc(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])).replace(/\n/g,'<br>')}
function val(id){return document.getElementById(id).value}function typeset(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise().catch(()=>{})}
async function api(url,opts={}){let r=await fetch(url,opts);let j=await r.json().catch(()=>({error:'Không đọc được phản hồi'}));if(!r.ok||j.error){if(r.status==401)location='/login';throw new Error(j.error||'Lỗi API')}return j}
function setOptions(id,arr){document.getElementById(id).innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option>${esc(x)}</option>`).join('')}
async function init(){META=await api('/api/meta');USER=META.user||{};document.getElementById('me').textContent=`${USER.hoten||''} (${USER.role||''}${USER.trial_until?' - hết trial: '+USER.trial_until:''}${USER.account_until?' - hết hạn: '+USER.account_until:''})`;if(USER.is_admin)document.getElementById('syncBtn').classList.remove('hide');if(META.loading){document.getElementById('info').textContent='Đang nạp Google Sheet... lần đầu có thể chờ 10–40 giây';document.getElementById('catalog').innerHTML=`<div class="card" style="border-color:#93c5fd;background:#eff6ff"><h3>⏳ Hệ thống đang khởi động</h3><p><b>Vui lòng chờ, không cần bấm lại nhiều lần.</b></p><p>${esc(META.loading_message||'Đang nạp dữ liệu từ Google Sheet...')}</p><div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:10px;margin:10px 0"><b>Lưu ý:</b> lần đầu Render Free vừa “thức dậy” và vừa nạp Google Sheet thì có thể chờ khoảng <b>10–40 giây</b>. Trang sẽ tự tải lại sau vài giây.</div>${META.load_error?'<p style="color:red"><b>Lỗi:</b> '+esc(META.load_error)+'</p>':''}<p class="muted">Trang sẽ tự thử lại sau 3 giây. Không cần đăng nhập lại.</p></div>`;document.getElementById('countCat').textContent='';setTimeout(init,3000);return;}CATALOG=META.catalog||[];document.getElementById('info').textContent=`${META.count_questions} câu hỏi | ${META.count_catalog} đề/thẻ đề | Nạp: ${META.loaded_at}`;setOptions('fMon',META.filters.Mon);setOptions('fLop',META.filters.Lop);setOptions('fChuong',META.filters.Chuong);setOptions('fBaiHoc',META.filters.BaiHoc);setOptions('fBoDe',META.filters.BoDe);renderCatalog()}
function okFilter(x){let s=val('fSearch').toLowerCase();let blob=[x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.DangBaiTap,x.BoDe,x.De,x.MucDo,x.Dang].join(' ').toLowerCase();return(!val('fMon')||x.Mon==val('fMon'))&&(!val('fLop')||x.Lop==val('fLop'))&&(!val('fChuong')||x.Chuong==val('fChuong'))&&(!val('fBaiHoc')||x.BaiHoc==val('fBaiHoc'))&&(!val('fBoDe')||x.BoDe==val('fBoDe'))&&(!s||blob.includes(s))}
function renderCatalog(){let list=CATALOG.filter(okFilter);document.getElementById('countCat').textContent=`(${list.length} mục)`;document.getElementById('catalog').innerHTML=list.map(x=>{let access=x.QuyenTruyCap||'FREE';let locked=USER.is_trial&&access!='FREE';let btn=locked?`<button class="btnRed" disabled>Khóa VIP</button>`:`<button class="btn" onclick="startQuiz('${x.MaDe}')">Làm bài</button>`;let note=locked?`<div class="muted" style="color:#991b1b;margin-top:6px">Tài khoản dùng thử chỉ mở đề FREE.</div>`:'';return `<div class="card"><h3>${esc(x.De||x.BaiHoc||'Đề luyện tập')}</h3><div><span class="tag">${esc(x.Mon)}</span><span class="tag">Lớp ${esc(x.Lop)}</span><span class="tag">${esc(x.SoCau)} câu</span><span class="tag">${esc(access)}</span></div><div class="line"></div><div><b>Chương:</b> ${esc(x.Chuong)}</div><div><b>Bài:</b> ${esc(x.BaiHoc)}</div><div><b>Dạng:</b> ${esc(x.Dang)}</div><div><b>Mức độ:</b> ${esc(x.MucDo)}</div><div><b>Bộ đề:</b> ${esc(x.BoDe)}</div>${note}<div style="text-align:right;margin-top:10px">${btn}</div></div>`}).join('')||'<div class="muted">Không có đề phù hợp.</div>';typeset()}
async function syncData(){if(!confirm('Đồng bộ lại dữ liệu từ Google Sheet?'))return;let j=await api('/api/sync',{method:'POST'});alert(j.message||'Đã bắt đầu đồng bộ.');init()}
async function startQuiz(made){try{let j=await api('/api/start?made='+encodeURIComponent(made));SID=j.sid;QUESTIONS=j.questions;CUR=0;ANSWERS={};SUBMITTED=!!USER.is_admin;RESULTS={};document.getElementById('home').classList.add('hide');document.getElementById('quiz').classList.remove('hide');document.getElementById('resultBox').textContent=USER.is_admin?'ADMIN: đang xem đáp án/lời giải':(USER.is_trial?'DÙNG THỬ: chỉ luyện đề FREE, không chấm điểm':'');let c=CATALOG.find(x=>x.MaDe==made)||{};document.getElementById('quizTitle').textContent=`${c.Mon||''} ${c.Lop?'- Lớp '+c.Lop:''} | ${c.De||c.BaiHoc||''}`;renderNav();renderQuestion(); if(j.trial_message) alert(j.trial_message)}catch(e){alert('Không mở được đề: '+e.message)}}
function backHome(){document.getElementById('quiz').classList.add('hide');document.getElementById('home').classList.remove('hide')}function saveCurrent(){let q=QUESTIONS[CUR];if(!q||USER.is_admin)return;if(q.Dang=='Trắc nghiệm'){let r=document.querySelector(`input[name="ans_${CUR}"]:checked`);if(r)ANSWERS[CUR]=r.value}else if(q.Dang=='Đúng sai'){let arr=[];for(let L of ['A','B','C','D']){let r=document.querySelector(`input[name="tf_${CUR}_${L}"]:checked`);arr.push(r?r.value:'')}ANSWERS[CUR]=arr}else{let el=document.getElementById('shortAns');if(el)ANSWERS[CUR]=el.value}renderNav()}
function renderNav(){let html='';for(let i=0;i<QUESTIONS.length;i++){let cls='num';if(i==CUR)cls+=' active';if(ANSWERS[i]!=null&&String(ANSWERS[i]).length)cls+=' answered';if(SUBMITTED&&RESULTS[i])cls+=RESULTS[i].ok?' ok':' bad';html+=`<button class="${cls}" onclick="goQ(${i})">${i+1}</button>`}document.getElementById('navNums').innerHTML=html}function goQ(i){saveCurrent();CUR=i;renderQuestion()}function prevQ(){if(CUR>0){saveCurrent();CUR--;renderQuestion()}}function nextQ(){if(CUR<QUESTIONS.length-1){saveCurrent();CUR++;renderQuestion()}}
function renderQuestion(){let q=QUESTIONS[CUR];renderNav();document.getElementById('qid').textContent=`Câu ${CUR+1}/${QUESTIONS.length} | ID: ${q.ID||''} | ${q.MucDo||''} - ${q.Dang}`;document.getElementById('qtext').innerHTML=esc(q.CauHoi)+(q.HinhAnh?`<br><img class="qimg" style="max-width:100%;margin-top:10px;border:1px solid #d7e0ed;border-radius:8px" src="${esc(q.HinhAnh)}" onerror="this.outerHTML='<div style=\'margin-top:10px;padding:10px;border:1px solid #fed7aa;background:#fff7ed;border-radius:8px;color:#9a3412\'>Không tải được hình. Kiểm tra cột T hoặc quyền chia sẻ ảnh.</div>'">`:'' );document.getElementById('btn5050').disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!USER.can_5050;document.getElementById('btnSubmit').style.display=(USER.is_admin||USER.is_trial)?'none':'';document.getElementById('btnEdit').classList.toggle('hide',!USER.is_admin);let html='';if(q.Dang=='Trắc nghiệm'){for(let L of ['A','B','C','D']){if(!q[L])continue;let checked=ANSWERS[CUR]==L?'checked':'';let cls='opt';let correct=(q.DapAn||'').toUpperCase().match(/[ABCD]/)?.[0]||'';if(USER.is_admin&&correct==L)cls+=' correct';if(SUBMITTED&&RESULTS[CUR]){if(RESULTS[CUR].correct==L)cls+=' correct';if(RESULTS[CUR].chosen==L&&RESULTS[CUR].chosen!=RESULTS[CUR].correct)cls+=' wrong'}html+=`<label id="opt_${L}" class="${cls}"><input type="radio" name="ans_${CUR}" value="${L}" ${checked} ${SUBMITTED?'disabled':''} onchange="saveCurrent()"><b>${L}.</b><span>${esc(q[L])}</span></label>`}}else if(q.Dang=='Đúng sai'){let old=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:['','','',''];let corr=String(q.DapAn||'').toUpperCase();for(let idx=0;idx<4;idx++){let L=['A','B','C','D'][idx];if(!q[L])continue;html+=`<div class="tfrow"><b>${L}.</b><div>${esc(q[L])}</div><label><input type="radio" name="tf_${CUR}_${L}" value="Đ" ${old[idx]=='Đ'?'checked':''} ${SUBMITTED?'disabled':''} onchange="saveCurrent()"> Đúng</label><label><input type="radio" name="tf_${CUR}_${L}" value="S" ${old[idx]=='S'?'checked':''} ${SUBMITTED?'disabled':''} onchange="saveCurrent()"> Sai</label></div>`}}else if(q.Dang=='Trả lời ngắn'){html=`<input id="shortAns" style="width:100%;font-size:18px" placeholder="Nhập đáp án..." value="${esc(ANSWERS[CUR]||'')}" ${SUBMITTED?'disabled':''} oninput="saveCurrent()">`}else{html=`<textarea id="shortAns" style="width:100%;min-height:120px" placeholder="Nhập bài làm tự luận..." ${SUBMITTED?'disabled':''} oninput="saveCurrent()">${esc(ANSWERS[CUR]||'')}</textarea>`}document.getElementById('options').innerHTML=html;let showSol=USER.is_admin||(SUBMITTED&&RESULTS[CUR]&&META.user.role!='FREE'&&META.user.role!='TRIAL');document.getElementById('solution').classList.toggle('hide',!showSol);if(showSol){let r=RESULTS[CUR]||{};document.getElementById('solution').innerHTML=`<b>Đáp án:</b> ${esc(r.correct||q.DapAn||'')}<br><b>Lời giải:</b><br>${esc(r.LoiGiai||q.LoiGiai||'Chưa có lời giải.')}`}typeset()}
async function use5050(){saveCurrent();try{let j=await api('/api/fifty',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR})});for(let L of j.hide||[]){let el=document.getElementById('opt_'+L);if(el)el.classList.add('hidden5050')}document.getElementById('btn5050').disabled=true;if(j.message)alert(j.message)}catch(e){alert(e.message)}}
async function submitQuiz(){if(USER.is_trial){alert('Tài khoản dùng thử không được nộp/chấm điểm.');return;}saveCurrent();if(!confirm('Nộp bài?'))return;let j=await api('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,answers:ANSWERS})});SUBMITTED=true;RESULTS={};for(let r of j.results)RESULTS[r.index]=r;document.getElementById('resultBox').textContent=`Điểm: ${j.score}/10 | Đúng ${j.correct_count}/${j.auto_count}`;renderQuestion();renderNav()}
function openEdit(){let q=QUESTIONS[CUR];let fields=['CauHoi','A','B','C','D','DapAn','SaiSo','MucDo','Dang','LoiGiai','HinhAnh'];let labels={CauHoi:'Câu hỏi / Nội dung - lưu cột K',DapAn:'Đáp án - lưu cột P',SaiSo:'Sai số - lưu cột Q',MucDo:'Mức độ - lưu cột I',Dang:'Dạng - lưu cột J',LoiGiai:'Lời giải - lưu cột R',HinhAnh:'Hình ảnh - lưu cột T'};document.getElementById('editForm').innerHTML=fields.map(f=>{let h=(f=='CauHoi'||f=='LoiGiai')?'150px':'78px';let val=String(q[f]||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));return `<div><label><b>${labels[f]||f}</b></label><textarea style="min-height:${h}" id="edit_${f}">${val}</textarea></div>`}).join('');document.getElementById('modal').classList.remove('hide')}
function closeEdit(){document.getElementById('modal').classList.add('hide')}async function saveEdit(){let q=QUESTIONS[CUR];let updates={};for(let f of ['CauHoi','A','B','C','D','DapAn','SaiSo','MucDo','Dang','LoiGiai','HinhAnh'])updates[f]=document.getElementById('edit_'+f).value;try{let j=await api('/api/question/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row,updates})});alert('Đã lưu vào Google Sheet dòng '+j.row+'\nĐã cập nhật: '+(j.fields||[]).join(', '));Object.assign(q,updates);closeEdit();renderQuestion()}catch(e){alert('Không lưu được: '+e.message)}}
async function deleteQuestion(){let q=QUESTIONS[CUR];if(!q||!q._row){alert('Không xác định được dòng Google Sheet của câu này.');return;}let msg='Xóa vĩnh viễn câu này khỏi Google Sheet?\n\nID: '+(q.ID||'')+'\nDòng: '+q._row+'\n\nSau khi xóa, các dòng phía dưới trong Google Sheet sẽ tự dồn lên.';if(!confirm(msg))return;if(!confirm('Xác nhận lần 2: thầy chắc chắn muốn xóa câu này?'))return;try{let j=await api('/api/question/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row,id:q.ID||''})});alert('Đã xóa câu khỏi Google Sheet.\nDòng đã xóa: '+j.row+'\nID: '+(j.id||''));QUESTIONS.splice(CUR,1);if(QUESTIONS.length===0){closeEdit();backHome();await syncSheet();return;}if(CUR>=QUESTIONS.length)CUR=QUESTIONS.length-1;closeEdit();renderNav();renderQuestion();}catch(e){alert('Không xóa được: '+e.message)}}
init().catch(e=>{document.body.innerHTML='<pre style="padding:20px;color:red">'+e.message+'</pre>'})
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
        "routes": ["/login", "/register", "/logout", "/api/meta", "/api/start", "/api/submit", "/api/question/update"]
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
    st = get_store()
    if not st.questions_loaded:
        st.start_questions_background(force=False)
        return jsonify({"error": "Dữ liệu đề đang nạp từ Google Sheet. Thầy chờ vài giây rồi bấm lại."}), 202
    return jsonify(st.start_quiz(made))

@app.route("/api/fifty", methods=["POST"])
def api_fifty():
    bad = require_login_json()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(get_store().fifty_fifty(body.get("sid", ""), int(body.get("index", 0))))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/submit", methods=["POST"])
def api_submit():
    bad = require_login_json()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(get_store().submit(body.get("sid", ""), body.get("answers", {})))
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
