# -*- coding: utf-8 -*-
"""
app.py — Ứng dụng luyện đề Google Sheet + đăng nhập + ADMIN sửa câu.

Dùng trên Render:
  Build Command: pip install -r requirements.txt
  Start Command: gunicorn app:app --bind 0.0.0.0:$PORT

Biến môi trường cần có trên Render:
  GOOGLE_SHEET_ID
  GOOGLE_CREDENTIALS_JSON
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import threading
import time
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import gspread
from flask import Flask, jsonify, render_template_string, request, session
from google.oauth2.service_account import Credentials

APP_VERSION = "GOOGLE_SHEET_LOGIN_ADMIN_TRIAL_FILTER_FIX_2026_05_31_V11"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "doi-khoa-bi-mat-nay-tren-render")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

DATA_LOCK = threading.RLock()
DATA_CACHE: Dict[str, Any] = {
    "loaded": False,
    "loading": False,
    "error": "",
    "loaded_at": "",
    "questions": [],
    "catalog": [],
    "headers": [],
    "header_map": {},
    "sample_rows": [],
}
USERS_LOCK = threading.RLock()
USERS_CACHE: Dict[str, Any] = {"loaded_at_ts": 0.0, "users": {}, "headers": [], "header_map": {}}
QUIZ_SESSIONS: Dict[str, Dict[str, Any]] = {}
ACTIVE_TOKENS: Dict[str, str] = {}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def date_str(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def clean(v: Any) -> str:
    s = str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def knorm(s: Any) -> str:
    s = strip_accents(str(s or "").strip().lower())
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 ._/-]+", "", s)
    return s


def stable_hash(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n].upper()


def norm_role(role: str) -> str:
    r = knorm(role).replace(" ", "")
    if r in ["admin", "quantri", "quanly"]:
        return "ADMIN"
    if r in ["svip", "s.vip", "s-vip", "supervip"]:
        return "S.VIP"
    if r in ["vip", "v.i.p"]:
        return "VIP"
    if r in ["trial", "dungthu", "dungthu3ngay", "demo"]:
        return "TRIAL"
    return "FREE"


def norm_access(v: str) -> str:
    x = knorm(v).replace(" ", "")
    if not x or x in ["free", "mienphi", "0"]:
        return "FREE"
    if x in ["vip", "co_phi", "cophi", "phi", "paid"]:
        return "VIP"
    if x in ["svip", "s.vip", "s-vip"]:
        return "S.VIP"
    return clean(v).upper()


def can_open_exam(role: str, access: str) -> bool:
    role = norm_role(role)
    access = norm_access(access)
    if role == "ADMIN":
        return True
    if access == "FREE":
        return True
    if access == "VIP":
        return role in ["VIP", "S.VIP"]
    if access == "S.VIP":
        return role == "S.VIP"
    return False


def can_submit(role: str, access: str) -> bool:
    role = norm_role(role)
    if role in ["TRIAL", "ADMIN"]:
        return False
    return can_open_exam(role, access)


def can_use_5050(role: str) -> bool:
    return norm_role(role) in ["VIP", "S.VIP", "ADMIN"]


def is_expired_date(s: str) -> bool:
    s = clean(s)
    if not s:
        return False
    for fmt in ["%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(s, fmt)
            if fmt in ["%d/%m/%Y", "%Y-%m-%d"]:
                dt = dt.replace(hour=23, minute=59, second=59)
            return datetime.now() > dt
        except Exception:
            pass
    return False


def norm_dang(s: str) -> str:
    k = knorm(s)
    if "dung sai" in k or k in ["ds", "tf", "truefalse"]:
        return "Đúng sai"
    if "tra loi ngan" in k or k in ["tln", "short"]:
        return "Trả lời ngắn"
    if "tu luan" in k or k in ["tl", "essay"]:
        return "Tự luận"
    return "Trắc nghiệm"


def norm_letter(s: str) -> str:
    m = re.search(r"[ABCD]", clean(s).upper())
    return m.group(0) if m else ""


def norm_tf_answer(s: str) -> List[str]:
    s = strip_accents(clean(s).upper())
    s = s.replace("DUNG", "D").replace("TRUE", "D").replace("SAI", "S").replace("FALSE", "S")
    return re.findall(r"[DS]", s)[:4]


def parse_float_vn(s: str) -> Optional[float]:
    s = clean(s)
    if not s:
        return None
    s = s.replace(" ", "")
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


def make_session_token() -> str:
    return stable_hash(f"{time.time()}|{random.random()}|{os.urandom(8).hex()}", 32)


def make_trial_mahs(phone: str, device_id: str) -> str:
    return "TRIAL_" + stable_hash(phone + "|" + device_id + "|" + str(time.time()), 8)


def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not creds_json:
        raise RuntimeError("Thiếu biến GOOGLE_CREDENTIALS_JSON trên Render.")
    if not sheet_id:
        raise RuntimeError("Thiếu biến GOOGLE_SHEET_ID trên Render.")
    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id)


def worksheet_or_create(sh, title: str, headers: Optional[List[str]] = None):
    try:
        return sh.worksheet(title)
    except Exception:
        ws = sh.add_worksheet(title=title, rows=1000, cols=max(20, len(headers or [])))
        if headers:
            ws.update("A1", [headers])
        return ws

ALIASES = {
    "MaDe": ["MaDe", "Mã đề", "Ma De", "MA_DE"],
    "ID": ["ID", "Id", "Mã câu", "MaCau", "Ma Cau"],
    "BoDe": ["BoDe", "Bộ đề", "Bo De", "Bộ Đề"],
    "De": ["De", "Đề", "TenDe", "Tên đề", "Tên Đề"],
    "Lop": ["Lop", "Lớp"],
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
    "HinhAnh": ["HinhAnh", "Hình ảnh", "Hình Ảnh", "Image"],
    "QuyenTruyCap": ["QuyenTruyCap", "Quyền truy cập", "Quyen", "Goi", "LoaiDe"],
}
CANONICAL_FIELDS = ["MaDe","ID","BoDe","De","Lop","Mon","Chuong","BaiHoc","DangBaiTap","MucDo","Dang","CauHoi","A","B","C","D","DapAn","SaiSo","LoiGiai","Diem","HinhAnh","QuyenTruyCap"]


def header_map(headers: List[str]) -> Dict[str, int]:
    normalized = {knorm(h): i for i, h in enumerate(headers)}
    result: Dict[str, int] = {}
    for field, names in ALIASES.items():
        for name in names:
            if knorm(name) in normalized:
                result[field] = normalized[knorm(name)]
                break
    return result


def get_field(row: List[str], hmap: Dict[str, int], field: str) -> str:
    idx = hmap.get(field)
    if idx is None or idx >= len(row):
        return ""
    return clean(row[idx])


def make_made(q: Dict[str, Any]) -> str:
    if clean(q.get("MaDe")):
        return clean(q.get("MaDe"))
    parts = [q.get("BoDe", ""), q.get("De", ""), q.get("Lop", ""), q.get("Mon", ""), q.get("Chuong", ""), q.get("BaiHoc", ""), q.get("DangBaiTap", "")]
    return "MD_" + stable_hash("|".join(knorm(x) for x in parts), 10)


def read_questions_from_sheet() -> Dict[str, Any]:
    sh = get_sheet()
    ws = sh.worksheet("Cau_Hoi")
    values = ws.get_all_values()
    if not values:
        raise RuntimeError("Sheet Cau_Hoi đang trống.")
    headers = [clean(x) for x in values[0]]
    hmap = header_map(headers)
    questions: List[Dict[str, Any]] = []
    samples: List[Dict[str, Any]] = []
    for row_index, row in enumerate(values[1:], start=2):
        if not any(clean(x) for x in row):
            continue
        q = {field: get_field(row, hmap, field) for field in CANONICAL_FIELDS}
        q["row_index"] = row_index
        q["Dang"] = norm_dang(q.get("Dang", ""))
        q["QuyenTruyCap"] = norm_access(q.get("QuyenTruyCap", "FREE"))
        q["MaDe"] = make_made(q)
        if not q.get("ID"):
            q["ID"] = "AUTO_" + stable_hash(json.dumps(q, ensure_ascii=False), 10)
        if not clean(q.get("CauHoi")):
            continue
        questions.append(q)
        if len(samples) < 10:
            samples.append({k: q.get(k, "") for k in ["row_index","ID","BoDe","De","Lop","Mon","Chuong","BaiHoc","DangBaiTap","MucDo","Dang","QuyenTruyCap"]} | {"CauHoi": q.get("CauHoi", "")[:120]})
    catalog = build_catalog(questions)
    return {"questions": questions, "catalog": catalog, "headers": headers, "header_map": hmap, "sample_rows": samples}


def build_catalog(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for q in questions:
        made = q["MaDe"]
        if made not in groups:
            groups[made] = {"MaDe": made, "BoDe": q.get("BoDe", ""), "De": q.get("De", ""), "Lop": q.get("Lop", ""), "Mon": q.get("Mon", ""), "Chuong": q.get("Chuong", ""), "BaiHoc": q.get("BaiHoc", ""), "DangBaiTap": q.get("DangBaiTap", ""), "MucDoSet": set(), "DangSet": set(), "AccessSet": set(), "SoCau": 0}
        g = groups[made]
        g["SoCau"] += 1
        if q.get("MucDo"):
            g["MucDoSet"].add(q.get("MucDo"))
        if q.get("Dang"):
            g["DangSet"].add(q.get("Dang"))
        g["AccessSet"].add(norm_access(q.get("QuyenTruyCap", "FREE")))
    out = []
    for g in groups.values():
        access = "FREE"
        if "S.VIP" in g["AccessSet"]:
            access = "S.VIP"
        elif "VIP" in g["AccessSet"]:
            access = "VIP"
        item = {k: v for k, v in g.items() if not k.endswith("Set")}
        item["MucDo"] = ", ".join(sorted(g["MucDoSet"], key=knorm))
        item["Dang"] = ", ".join(sorted(g["DangSet"], key=knorm))
        item["QuyenTruyCap"] = access
        out.append(item)
    out.sort(key=lambda x: (knorm(x.get("Mon")), knorm(x.get("Lop")), knorm(x.get("Chuong")), knorm(x.get("BaiHoc")), knorm(x.get("De"))))
    return out


def start_background_load(force: bool = False) -> None:
    with DATA_LOCK:
        if DATA_CACHE["loading"]:
            return
        if DATA_CACHE["loaded"] and not force:
            return
        DATA_CACHE["loading"] = True
        DATA_CACHE["error"] = ""
    def worker():
        try:
            data = read_questions_from_sheet()
            with DATA_LOCK:
                DATA_CACHE.update(data)
                DATA_CACHE["loaded"] = True
                DATA_CACHE["loading"] = False
                DATA_CACHE["error"] = ""
                DATA_CACHE["loaded_at"] = now_str()
        except Exception as e:
            with DATA_LOCK:
                DATA_CACHE["loading"] = False
                DATA_CACHE["error"] = str(e)
    threading.Thread(target=worker, daemon=True).start()


def require_loaded() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    with DATA_LOCK:
        if DATA_CACHE["loaded"]:
            return DATA_CACHE["questions"], DATA_CACHE["catalog"]
    start_background_load(False)
    raise RuntimeError("Dữ liệu đang được nạp. Vui lòng chờ vài giây.")

USER_ALIASES = {
    "MaHS": ["MaHS", "Mã HS", "Ma HS", "TaiKhoan", "Tài khoản", "Username"],
    "HoTen": ["HoTen", "HọTên", "Họ tên", "Ho Ten"],
    "LopHoc": ["LopHoc", "Lớp học", "Lop", "Lớp"],
    "LoaiTaiKhoan": ["LoaiTaiKhoan", "LoạiTàiKhoản", "Loại tài khoản", "Role", "Quyen"],
    "TrangThai": ["TrangThai", "Trạng thái", "Status"],
    "SoDienThoai": ["SoDienThoai", "SốĐiệnThoại", "Số điện thoại", "Phone"],
    "MatKhau": ["MatKhau", "Mật khẩu", "Password"],
    "NgayDangKy": ["NgayDangKy", "Ngày đăng ký"],
    "NgayHetHanTrial": ["NgayHetHanTrial", "Ngày hết hạn Trial", "NgayHetHanDungThu"],
    "DeviceId": ["DeviceId", "DeviceID", "Thiết bị"],
    "NgayHetHanTaiKhoan": ["NgayHetHanTaiKhoan", "Ngày hết hạn tài khoản"],
    "SessionToken": ["SessionToken"], "LastLogin": ["LastLogin"], "LastDevice": ["LastDevice"],
}


def user_header_map(headers: List[str]) -> Dict[str, int]:
    normalized = {knorm(h): i for i, h in enumerate(headers)}
    result = {}
    for field, names in USER_ALIASES.items():
        for name in names:
            if knorm(name) in normalized:
                result[field] = normalized[knorm(name)]
                break
    return result


def uget(row: List[str], hmap: Dict[str, int], field: str) -> str:
    idx = hmap.get(field)
    if idx is None or idx >= len(row):
        return ""
    return clean(row[idx])


def ensure_user_columns(ws) -> Tuple[List[str], Dict[str, int]]:
    values = ws.get_all_values()
    headers = [clean(x) for x in values[0]] if values else []
    required = ["MaHS","HoTen","LopHoc","LoaiTaiKhoan","TrangThai","SoDienThoai","MatKhau","NgayDangKy","NgayHetHanTrial","DeviceId","NgayHetHanTaiKhoan","SessionToken","LastLogin","LastDevice"]
    changed = False
    for h in required:
        if knorm(h) not in [knorm(x) for x in headers]:
            headers.append(h); changed = True
    if changed:
        ws.update("A1", [headers])
    return headers, user_header_map(headers)


def read_users_from_sheet(force: bool = False) -> Dict[str, Dict[str, Any]]:
    with USERS_LOCK:
        if not force and USERS_CACHE["users"] and time.time() - USERS_CACHE["loaded_at_ts"] < 20:
            return USERS_CACHE["users"]
    sh = get_sheet()
    ws = worksheet_or_create(sh, "HOC_VIEN", ["MaHS", "HoTen", "LopHoc", "LoaiTaiKhoan", "TrangThai", "SoDienThoai", "MatKhau"])
    values = ws.get_all_values()
    if not values:
        return {}
    headers = [clean(x) for x in values[0]]
    hmap = user_header_map(headers)
    users: Dict[str, Dict[str, Any]] = {}
    for row_index, row in enumerate(values[1:], start=2):
        if not any(clean(x) for x in row): continue
        mahs = uget(row, hmap, "MaHS")
        if not mahs: continue
        phone = uget(row, hmap, "SoDienThoai")
        password = uget(row, hmap, "MatKhau")
        if not password:
            digits = re.sub(r"\D+", "", phone)
            password = digits[-6:] if len(digits) >= 6 else "123456"
        role = norm_role(uget(row, hmap, "LoaiTaiKhoan") or "FREE")
        user = {"row_index": row_index, "MaHS": mahs, "HoTen": uget(row, hmap, "HoTen"), "LopHoc": uget(row, hmap, "LopHoc"), "LoaiTaiKhoan": role, "TrangThai": (uget(row, hmap, "TrangThai") or "ON").upper(), "SoDienThoai": phone, "MatKhau": password, "NgayDangKy": uget(row, hmap, "NgayDangKy"), "NgayHetHanTrial": uget(row, hmap, "NgayHetHanTrial"), "DeviceId": uget(row, hmap, "DeviceId"), "NgayHetHanTaiKhoan": uget(row, hmap, "NgayHetHanTaiKhoan"), "SessionToken": uget(row, hmap, "SessionToken"), "LastLogin": uget(row, hmap, "LastLogin"), "LastDevice": uget(row, hmap, "LastDevice")}
        users[mahs] = user
        if user["SessionToken"]:
            ACTIVE_TOKENS[mahs] = user["SessionToken"]
    with USERS_LOCK:
        USERS_CACHE.update({"loaded_at_ts": time.time(), "users": users, "headers": headers, "header_map": hmap})
    return users


def update_user_session_token(user: Dict[str, Any], token: str, device_id: str = "") -> None:
    try:
        sh = get_sheet(); ws = sh.worksheet("HOC_VIEN")
        headers, hmap = ensure_user_columns(ws)
        row = int(user["row_index"])
        for field, value in {"SessionToken": token, "LastLogin": now_str(), "LastDevice": device_id}.items():
            col = hmap.get(field)
            if col is not None: ws.update_cell(row, col + 1, value)
        with USERS_LOCK: USERS_CACHE["loaded_at_ts"] = 0
    finally:
        ACTIVE_TOKENS[user["MaHS"]] = token


def register_trial_user(hoten: str, lop: str, phone: str, password: str, device_id: str) -> Dict[str, Any]:
    phone_digits = re.sub(r"\D+", "", phone)
    if len(phone_digits) < 8: raise RuntimeError("Số điện thoại không hợp lệ.")
    if not password: password = phone_digits[-6:]
    if len(password) < 4: raise RuntimeError("Mật khẩu cần ít nhất 4 ký tự.")
    if not device_id: raise RuntimeError("Không nhận được mã thiết bị. Vui lòng tải lại trang rồi đăng ký lại.")
    sh = get_sheet(); ws = worksheet_or_create(sh, "HOC_VIEN", ["MaHS", "HoTen", "LopHoc", "LoaiTaiKhoan", "TrangThai", "SoDienThoai", "MatKhau"])
    headers, hmap = ensure_user_columns(ws)
    users = read_users_from_sheet(force=True)
    for u in users.values():
        if re.sub(r"\D+", "", u.get("SoDienThoai", "")) == phone_digits: raise RuntimeError("Số điện thoại này đã đăng ký tài khoản.")
        if clean(u.get("DeviceId")) and clean(u.get("DeviceId")) == device_id: raise RuntimeError("Thiết bị này đã đăng ký dùng thử.")
    mahs = make_trial_mahs(phone_digits, device_id)
    start = datetime.now(); end = start + timedelta(days=3)
    row_dict = {"MaHS": mahs, "HoTen": hoten, "LopHoc": lop, "LoaiTaiKhoan": "TRIAL", "TrangThai": "ON", "SoDienThoai": phone_digits, "MatKhau": password, "NgayDangKy": date_str(start), "NgayHetHanTrial": date_str(end), "DeviceId": device_id, "NgayHetHanTaiKhoan": "", "SessionToken": "", "LastLogin": "", "LastDevice": device_id}
    ws.append_row([row_dict.get(h, "") for h in headers], value_input_option="USER_ENTERED")
    with USERS_LOCK: USERS_CACHE["loaded_at_ts"] = 0
    return {"MaHS": mahs, "MatKhau": password, "NgayHetHanTrial": row_dict["NgayHetHanTrial"]}


def current_user() -> Optional[Dict[str, Any]]:
    mahs = session.get("MaHS"); token = session.get("SessionToken")
    if not mahs or not token: return None
    user = read_users_from_sheet(force=False).get(mahs)
    if not user: return None
    latest = ACTIVE_TOKENS.get(mahs) or user.get("SessionToken")
    if latest and latest != token:
        session.clear(); return None
    return user


def login_required_api():
    user = current_user()
    if not user: return None, jsonify({"error": "Chưa đăng nhập hoặc tài khoản đã đăng nhập ở thiết bị khác."}), 401
    if user["TrangThai"] not in ["ON", "ACTIVE", "TRUE", "1"]: return None, jsonify({"error": "Tài khoản đang bị khóa hoặc chưa kích hoạt."}), 403
    role = norm_role(user["LoaiTaiKhoan"])
    if role == "TRIAL" and is_expired_date(user.get("NgayHetHanTrial", "")): return None, jsonify({"error": "Tài khoản dùng thử đã hết hạn."}), 403
    if role in ["VIP", "S.VIP"] and is_expired_date(user.get("NgayHetHanTaiKhoan", "")): return None, jsonify({"error": "Tài khoản đã hết hạn."}), 403
    return user, None, None


def admin_required_api():
    user, resp, status = login_required_api()
    if resp is not None: return None, resp, status
    if norm_role(user["LoaiTaiKhoan"]) != "ADMIN": return None, jsonify({"error": "Chỉ ADMIN được dùng chức năng này."}), 403
    return user, None, None


def check_answer(q: Dict[str, Any], user_answer: Any) -> Tuple[bool, str, str]:
    dang = norm_dang(q.get("Dang", "")); correct_raw = clean(q.get("DapAn", ""))
    if dang == "Trắc nghiệm":
        correct = norm_letter(correct_raw); chosen = norm_letter(str(user_answer or ""))
        return bool(correct and chosen and correct == chosen), correct, chosen
    if dang == "Đúng sai":
        correct_list = norm_tf_answer(correct_raw)
        if isinstance(user_answer, list):
            chosen_list = []
            for x in user_answer:
                k = knorm(x)
                chosen_list.append("Đ" if k in ["d", "dung", "đ", "true"] else "S" if k in ["s", "sai", "false"] else "")
        else:
            chosen_list = ["Đ" if x == "D" else "S" for x in norm_tf_answer(str(user_answer or ""))]
        corr = ["Đ" if x == "D" else "S" for x in correct_list]
        while len(chosen_list) < 4: chosen_list.append("")
        return len(corr) == 4 and chosen_list[:4] == corr[:4], ",".join(corr), ",".join(chosen_list[:4])
    if dang == "Trả lời ngắn":
        correct_num = parse_float_vn(correct_raw); chosen_num = parse_float_vn(str(user_answer or "")); tol = parse_float_vn(q.get("SaiSo", "")) or 0.0
        if correct_num is not None and chosen_num is not None: return abs(chosen_num - correct_num) <= tol + 1e-12, correct_raw, str(user_answer or "")
        return knorm(correct_raw) == knorm(str(user_answer or "")), correct_raw, str(user_answer or "")
    return False, correct_raw, str(user_answer or "")


def save_result_to_sheet(user: Dict[str, Any], made: str, title: str, score: float, correct_count: int, total: int, detail: Any) -> None:
    try:
        sh = get_sheet(); headers = ["ThoiGian", "MaHS", "HoTen", "LopHoc", "LoaiTaiKhoan", "MaDe", "TenDe", "Diem", "SoDung", "TongCau", "ChiTiet"]
        ws = worksheet_or_create(sh, "Ket_Qua", headers)
        if not ws.get_all_values(): ws.update("A1", [headers])
        ws.append_row([now_str(), user.get("MaHS"), user.get("HoTen"), user.get("LopHoc"), user.get("LoaiTaiKhoan"), made, title, score, correct_count, total, json.dumps(detail, ensure_ascii=False)], value_input_option="USER_ENTERED")
    except Exception:
        pass

HTML = r'''
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ứng dụng luyện đề</title>
<script>window.MathJax={tex:{inlineMath:[["$","$"],["\\(","\\)"]],displayMath:[["$$","$$"],["\\[","\\]"]]},svg:{fontCache:"global"}};</script><script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>:root{--blue:#1d4ed8;--bg:#f5f7fb;--border:#d8e1ef;--green:#dcfce7;--red:#fee2e2;--yellow:#fff7ed}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#111827}.top{background:var(--blue);color:#fff;padding:12px 18px;box-shadow:0 2px 8px #0002;position:sticky;top:0;z-index:5}.top h1{margin:0;font-size:20px}.top small{opacity:.95}.wrap{max-width:1400px;margin:auto;padding:14px}.panel{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:12px;box-shadow:0 1px 4px #0001}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:5px;min-width:150px;flex:1}.field label{font-weight:700;font-size:12px}select,input,button,textarea{font-family:inherit;font-size:14px;border:1px solid var(--border);border-radius:8px;padding:9px 10px;background:#fff}button{font-weight:700;cursor:pointer}.btn{background:var(--blue);color:white;border-color:var(--blue)}.btn2{background:#eef2ff;color:#1e40af}.btnG{background:#dcfce7;color:#166534;border-color:#86efac}.btnR{background:#fee2e2;color:#991b1b;border-color:#fecaca}.muted{color:#6b7280}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}.card{border:1px solid var(--border);border-radius:12px;padding:12px;background:#fff}.card h3{margin:0 0 8px;color:#1e3a8a}.tag{display:inline-block;background:#eef2ff;color:#1d4ed8;border-radius:999px;padding:3px 9px;font-size:12px;font-weight:700;margin:2px}.line{height:1px;background:var(--border);margin:10px 0}.hide{display:none!important}.loginbox{max-width:460px;margin:50px auto}.notice{background:#fff7ed;border:1px solid #fdba74;color:#9a3412;border-radius:12px;padding:14px;margin-bottom:12px}.okbox{background:#ecfdf5;border:1px solid #86efac;color:#166534;border-radius:12px;padding:12px}.err{color:#dc2626;font-weight:700}.quizLayout{display:grid;grid-template-columns:1fr 270px;gap:12px}.qbox{border:1px solid #111827;border-radius:8px;background:#fff;padding:14px;min-height:160px;font-size:18px;line-height:1.55}.qid{font-weight:800;font-size:19px;margin-bottom:10px}.opt{display:flex;gap:9px;align-items:flex-start;border:1px solid transparent;border-radius:10px;padding:10px;margin:7px 0}.opt:hover{background:#f8fafc}.optionHidden{opacity:.25;pointer-events:none;text-decoration:line-through}.correct{background:var(--green)!important;border-color:#86efac!important}.wrong{background:var(--red)!important;border-color:#fecaca!important}.tfrow{display:grid;grid-template-columns:36px 1fr 90px 90px;gap:8px;align-items:center;border:1px solid var(--border);border-radius:10px;padding:8px;margin:8px 0}.navNums{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.num{padding:8px 0;border-radius:8px;background:#fff;border:1px solid var(--border);font-weight:800}.num.active{outline:3px solid #93c5fd}.num.answered{background:#fef3c7}.num.ok{background:var(--green);color:#166534}.num.bad{background:var(--red);color:#991b1b}.solution{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px;margin-top:12px}.adminEdit textarea{width:100%;min-height:90px}.adminEdit .field{min-width:120px}.imgQ{max-width:100%;border:1px solid var(--border);border-radius:8px;margin-top:10px}.small{font-size:13px}@media(max-width:900px){.quizLayout{grid-template-columns:1fr}.qbox{font-size:16px}.top h1{font-size:17px}}</style></head>
<body><div class="top"><h1>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</h1><small id="topInfo"></small></div><div class="wrap">
<div id="loginPage" class="loginbox panel"><h2>Đăng nhập học viên</h2><div class="field"><label>Mã học sinh</label><input id="loginMaHS" placeholder="VD: HS001"></div><br><div class="field"><label>Mật khẩu</label><input id="loginPass" type="password" placeholder="Mật khẩu"></div><br><button class="btn" onclick="login()">Đăng nhập</button> <button class="btn2" onclick="showRegister()">Đăng ký dùng thử 3 ngày</button><p id="loginMsg" class="err"></p><div class="notice small">Lưu ý: lần đầu Render Free vừa “thức dậy” và vừa nạp Google Sheet thì có thể chờ khoảng 10–40 giây. Trang sẽ tự thử lại khi đang nạp dữ liệu.</div></div>
<div id="registerPage" class="loginbox panel hide"><h2>Đăng ký dùng thử 3 ngày</h2><div class="field"><label>Họ tên</label><input id="regHoTen"></div><br><div class="field"><label>Lớp</label><input id="regLop" placeholder="VD: 12QT1"></div><br><div class="field"><label>Số điện thoại</label><input id="regPhone"></div><br><div class="field"><label>Mật khẩu</label><input id="regPass" type="password" placeholder="Bỏ trống sẽ lấy 6 số cuối SĐT"></div><br><button class="btnG" onclick="registerTrial()">Đăng ký</button> <button onclick="showLogin()">Quay lại đăng nhập</button><p id="regMsg" class="err"></p><div class="notice small">Tài khoản dùng thử chỉ mở được đề FREE, không nộp bài, không chấm điểm, không xem đáp án/lời giải.</div></div>
<div id="homePage" class="hide"><div class="panel row" style="justify-content:space-between"><div><b id="userInfo"></b><div class="muted small" id="roleInfo"></div></div><div><button class="btn2 hide" id="btnDebug" onclick="debugSheet()">ADMIN: Kiểm tra Sheet</button><button class="btnG hide" id="btnSync" onclick="syncSheet()">ADMIN: Đồng bộ Sheet</button><button onclick="logout()">Thoát</button></div></div><div id="loadingBox" class="notice hide"><h3>⏳ Hệ thống đang khởi động</h3><p>Vui lòng chờ, không cần bấm lại nhiều lần.</p><p>Lưu ý: lần đầu Render Free vừa “thức dậy” và vừa nạp Google Sheet thì có thể chờ khoảng 10–40 giây. Trang sẽ tự tải lại sau vài giây.</p><p>Trang sẽ tự thử lại sau 3 giây. Không cần đăng nhập lại.</p></div><div class="panel"><b>Thiết lập luyện tập</b><div class="row" style="margin-top:10px"><div class="field"><label>Môn</label><select id="fMon"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="fLop"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="fChuong"><option value="">Tất cả</option></select></div><div class="field"><label>Bài học</label><select id="fBaiHoc"><option value="">Tất cả</option></select></div><div class="field"><label>Bộ đề</label><select id="fBoDe"><option value="">Tất cả</option></select></div><div class="field"><label>Tìm nhanh</label><input id="fSearch" placeholder="Nhập từ khóa..."></div><button class="btn" onclick="renderCatalog()">Lọc đề</button></div></div><div id="debugBox" class="panel hide"></div><div class="panel"><b>Mục lục đề</b> <span id="countCat" class="muted"></span><div id="catalog" class="grid" style="margin-top:10px"></div></div></div>
<div id="quizPage" class="hide"><div class="panel row" style="justify-content:space-between"><div><button class="btn2" onclick="backHome()">← Về mục lục</button> <b id="quizTitle"></b></div><div id="scoreBox" style="font-weight:800;font-size:18px"></div></div><div id="trialWarn" class="notice hide">Tài khoản dùng thử chỉ được xem/làm thử đề FREE, không nộp bài, không chấm điểm và không xem đáp án.</div><div id="adminWarn" class="okbox hide">ADMIN: Đang ở chế độ soát đề. Thầy xem đáp án/lời giải ngay và có thể sửa câu hỏi trực tiếp.</div><div class="quizLayout"><div class="panel"><div class="row" style="justify-content:space-between"><div class="qid" id="qid"></div><div><button id="btn5050" class="btnG" onclick="use5050()">Loại 2 câu sai</button><button id="btnSubmit" class="btn" onclick="submitQuiz()">Nộp bài</button></div></div><div id="qtext" class="qbox"></div><div id="options"></div><div id="solution" class="solution hide"></div><div id="adminEdit" class="adminEdit panel hide"></div><div class="row" style="justify-content:space-between;margin-top:10px"><button onclick="prevQ()">← Câu trước</button><button onclick="nextQ()">Câu sau →</button></div></div><div class="panel"><b>Bảng câu hỏi</b><div id="navNums" class="navNums" style="margin-top:10px"></div><div class="line"></div><div class="muted small">Vàng: đã làm. Sau nộp: xanh đúng, đỏ sai.</div></div></div></div></div>
<script>
let USER=null,META=null,CATALOG=[],SID='',QUESTIONS=[],CUR=0,ANSWERS={},SUBMITTED=false,RESULTS={},QUIZ_PERM={};function esc(s){return String(s||'').replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])).replace(/\n/g,'<br>')}function raw(s){return String(s||'').replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]))}function val(id){return document.getElementById(id).value}function setOptions(id,arr){document.getElementById(id).innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option>${esc(x)}</option>`).join('')}function typeset(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise().catch(()=>{})}function getDeviceId(){let x=localStorage.getItem('device_id');if(!x){x='DEV_'+Date.now()+'_'+Math.random().toString(16).slice(2);localStorage.setItem('device_id',x)}return x}async function api(url,opts={}){let r=await fetch(url,opts);let j=await r.json().catch(()=>({error:'Không đọc được phản hồi'}));if(!r.ok||j.error)throw new Error(j.error||'Lỗi API');return j}async function apiNoThrow(url,opts={}){let r=await fetch(url,opts);return await r.json().catch(()=>({error:'Không đọc được phản hồi'}))}function showLogin(){loginPage.classList.remove('hide');registerPage.classList.add('hide');homePage.classList.add('hide');quizPage.classList.add('hide')}function showRegister(){loginPage.classList.add('hide');registerPage.classList.remove('hide')}async function checkMe(){let j=await apiNoThrow('/api/me');if(j.logged_in){USER=j.user;showHome();await loadMeta()}else showLogin()}async function login(){loginMsg.textContent='Đang đăng nhập...';try{let j=await api('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mahs:val('loginMaHS'),password:val('loginPass'),device_id:getDeviceId()})});USER=j.user;loginMsg.textContent='';showHome();await loadMeta()}catch(e){loginMsg.textContent=e.message}}async function logout(){await apiNoThrow('/api/logout',{method:'POST'});location.reload()}async function registerTrial(){regMsg.textContent='Đang đăng ký...';try{let j=await api('/api/register_trial',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hoten:val('regHoTen'),lop:val('regLop'),phone:val('regPhone'),password:val('regPass'),device_id:getDeviceId()})});regMsg.className='';regMsg.innerHTML=`Đăng ký thành công.<br>Mã đăng nhập: <b>${esc(j.MaHS)}</b><br>Mật khẩu: <b>${esc(j.MatKhau)}</b><br>Hạn dùng thử: ${esc(j.NgayHetHanTrial)}`}catch(e){regMsg.className='err';regMsg.textContent=e.message}}function showHome(){loginPage.classList.add('hide');registerPage.classList.add('hide');homePage.classList.remove('hide');quizPage.classList.add('hide');userInfo.textContent=`${USER.HoTen||USER.MaHS} (${USER.MaHS})`;roleInfo.textContent=`Quyền: ${USER.LoaiTaiKhoan} | Lớp: ${USER.LopHoc||''}`;if(USER.LoaiTaiKhoan=='ADMIN'){btnSync.classList.remove('hide');btnDebug.classList.remove('hide')}}async function loadMeta(){loadingBox.classList.add('hide');let j=await apiNoThrow('/api/meta');if(j.loading){loadingBox.classList.remove('hide');topInfo.textContent='Đang nạp Google Sheet...';setTimeout(loadMeta,3000);return}if(j.error){loadingBox.classList.remove('hide');loadingBox.innerHTML='<h3>Không nạp được dữ liệu</h3><p>'+esc(j.error)+'</p><p>Trang sẽ thử lại sau 5 giây.</p>';setTimeout(loadMeta,5000);return}META=j;CATALOG=j.catalog||[];topInfo.textContent=`${j.count_questions} câu hỏi | ${j.count_catalog} đề/thẻ đề | Đồng bộ: ${j.loaded_at||''}`;setOptions('fMon',j.filters.Mon||[]);setOptions('fLop',j.filters.Lop||[]);setOptions('fChuong',j.filters.Chuong||[]);setOptions('fBaiHoc',j.filters.BaiHoc||[]);setOptions('fBoDe',j.filters.BoDe||[]);renderCatalog()}function okFilter(x){let s=val('fSearch').toLowerCase();let blob=[x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.DangBaiTap,x.BoDe,x.De,x.MucDo,x.Dang,x.QuyenTruyCap].join(' ').toLowerCase();return(!val('fMon')||x.Mon==val('fMon'))&&(!val('fLop')||x.Lop==val('fLop'))&&(!val('fChuong')||x.Chuong==val('fChuong'))&&(!val('fBaiHoc')||x.BaiHoc==val('fBaiHoc'))&&(!val('fBoDe')||x.BoDe==val('fBoDe'))&&(!s||blob.includes(s))}function renderCatalog(){let list=CATALOG.filter(okFilter);countCat.textContent=`(${list.length} mục)`;catalog.innerHTML=list.map(x=>{let disabled=x.can_open===false;return `<div class="card"><h3>${esc(x.De||x.BaiHoc||'Đề luyện tập')}</h3><div><span class="tag">${esc(x.Mon)}</span><span class="tag">Lớp ${esc(x.Lop)}</span><span class="tag">${esc(x.SoCau)} câu</span><span class="tag">${esc(x.QuyenTruyCap||'FREE')}</span></div><div class="line"></div><div><b>Chương:</b> ${esc(x.Chuong)}</div><div><b>Bài:</b> ${esc(x.BaiHoc)}</div><div><b>Dạng:</b> ${esc(x.Dang)}</div><div><b>Mức độ:</b> ${esc(x.MucDo)}</div><div><b>Bộ đề:</b> ${esc(x.BoDe)}</div>${disabled?'<div class="err small">Tài khoản không có quyền mở đề này.</div>':''}<div style="text-align:right;margin-top:10px"><button class="btn" ${disabled?'disabled':''} onclick="startQuiz('${x.MaDe}')">Làm bài</button></div></div>`}).join('')||'<div class="muted">Không có đề phù hợp.</div>';typeset()}async function syncSheet(){alert('Đang đồng bộ nền. Trang sẽ tự cập nhật sau vài giây.');await api('/api/admin/sync',{method:'POST'});setTimeout(loadMeta,3000)}async function debugSheet(){let j=await api('/api/admin/debug');debugBox.classList.remove('hide');debugBox.innerHTML=`<h3>ADMIN: Kiểm tra dữ liệu đọc từ Google Sheet</h3><p>Số câu: ${j.count_questions} | Số mục: ${j.count_catalog} | Lúc: ${esc(j.loaded_at||'')}</p><pre style="white-space:pre-wrap;max-height:300px;overflow:auto">${esc(JSON.stringify(j.sample_rows,null,2))}</pre>`}async function startQuiz(made){try{let j=await api('/api/start?made='+encodeURIComponent(made));SID=j.sid;QUESTIONS=j.questions;QUIZ_PERM=j.permissions||{};CUR=0;ANSWERS={};SUBMITTED=false;RESULTS={};homePage.classList.add('hide');quizPage.classList.remove('hide');scoreBox.textContent='';quizTitle.textContent=j.title||'';trialWarn.classList.toggle('hide',!QUIZ_PERM.trial_mode);adminWarn.classList.toggle('hide',!QUIZ_PERM.admin_mode);renderNav();renderQuestion()}catch(e){alert(e.message)}}function backHome(){quizPage.classList.add('hide');homePage.classList.remove('hide')}function saveCurrent(){let q=QUESTIONS[CUR];if(!q||SUBMITTED||QUIZ_PERM.admin_mode)return;if(q.Dang=='Trắc nghiệm'){let r=document.querySelector(`input[name="ans_${CUR}"]:checked`);if(r)ANSWERS[CUR]=r.value}else if(q.Dang=='Đúng sai'){let arr=[];for(let L of ['A','B','C','D']){let r=document.querySelector(`input[name="tf_${CUR}_${L}"]:checked`);arr.push(r?r.value:'')}ANSWERS[CUR]=arr}else{let el=document.getElementById('shortAns');if(el)ANSWERS[CUR]=el.value}renderNav()}function renderNav(){let html='';for(let i=0;i<QUESTIONS.length;i++){let cls='num';if(i==CUR)cls+=' active';if(ANSWERS[i]!=null&&String(ANSWERS[i]).length)cls+=' answered';if(SUBMITTED&&RESULTS[i])cls+=RESULTS[i].ok?' ok':' bad';html+=`<button class="${cls}" onclick="goQ(${i})">${i+1}</button>`}navNums.innerHTML=html}function goQ(i){saveCurrent();CUR=i;renderQuestion()}function prevQ(){if(CUR>0){saveCurrent();CUR--;renderQuestion()}}function nextQ(){if(CUR<QUESTIONS.length-1){saveCurrent();CUR++;renderQuestion()}}function renderQuestion(){let q=QUESTIONS[CUR];renderNav();qid.textContent=`Câu ${CUR+1}/${QUESTIONS.length} | ID: ${q.ID||''} | ${q.MucDo||''} - ${q.Dang}`;qtext.innerHTML=esc(q.CauHoi)+(q.HinhAnh?`<br><img class="imgQ" src="${esc(q.HinhAnh)}">`:'');btn5050.disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!QUIZ_PERM.can_5050;btnSubmit.disabled=SUBMITTED||!QUIZ_PERM.can_submit;btnSubmit.title=QUIZ_PERM.can_submit?'':'Tài khoản này không được nộp/chấm điểm';let html='';let showSol=QUIZ_PERM.admin_mode||(SUBMITTED&&RESULTS[CUR]&&QUIZ_PERM.can_view_solution);if(q.Dang=='Trắc nghiệm'){for(let L of ['A','B','C','D']){if(!q[L])continue;let checked=ANSWERS[CUR]==L?'checked':'';let cls='opt';let corr=QUIZ_PERM.admin_mode?q.DapAn:(RESULTS[CUR]?RESULTS[CUR].correct:'');let chosen=RESULTS[CUR]?RESULTS[CUR].chosen:'';if(showSol){if(String(corr).includes(L))cls+=' correct';if(chosen==L&&!String(corr).includes(L))cls+=' wrong'}html+=`<label id="opt_${L}" class="${cls}"><input type="radio" name="ans_${CUR}" value="${L}" ${checked} ${SUBMITTED||QUIZ_PERM.admin_mode?'disabled':''} onchange="saveCurrent()"><b>${L}.</b><span>${esc(q[L])}</span></label>`}}else if(q.Dang=='Đúng sai'){let old=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:['','','',''];for(let idx=0;idx<4;idx++){let L=['A','B','C','D'][idx];if(!q[L])continue;html+=`<div class="tfrow"><b>${L}.</b><div>${esc(q[L])}</div><label><input type="radio" name="tf_${CUR}_${L}" value="Đ" ${old[idx]=='Đ'?'checked':''} ${SUBMITTED||QUIZ_PERM.admin_mode?'disabled':''} onchange="saveCurrent()"> Đúng</label><label><input type="radio" name="tf_${CUR}_${L}" value="S" ${old[idx]=='S'?'checked':''} ${SUBMITTED||QUIZ_PERM.admin_mode?'disabled':''} onchange="saveCurrent()"> Sai</label></div>`}}else if(q.Dang=='Trả lời ngắn'){html=`<input id="shortAns" style="width:100%;font-size:18px" value="${raw(ANSWERS[CUR]||'')}" ${SUBMITTED||QUIZ_PERM.admin_mode?'disabled':''} oninput="saveCurrent()" placeholder="Nhập đáp án...">`}else{html=`<textarea id="shortAns" style="width:100%;min-height:130px" ${SUBMITTED||QUIZ_PERM.admin_mode?'disabled':''} oninput="saveCurrent()" placeholder="Nhập bài làm tự luận...">${raw(ANSWERS[CUR]||'')}</textarea>`}options.innerHTML=html;if(showSol){solution.classList.remove('hide');let dap=QUIZ_PERM.admin_mode?q.DapAn:(RESULTS[CUR]?.correct||q.DapAn);let chosen=RESULTS[CUR]?.chosen||'';solution.innerHTML=`<b>Đáp án:</b> ${esc(dap||'')}<br>${chosen?'<b>Em chọn:</b> '+esc(chosen)+'<br>':''}<div class="line"></div><b>Lời giải:</b><br>${esc(q.LoiGiai||'Chưa có lời giải.')}`}else solution.classList.add('hide');renderAdminEdit();typeset()}function renderAdminEdit(){let q=QUESTIONS[CUR];if(!QUIZ_PERM.admin_mode){adminEdit.classList.add('hide');return}adminEdit.classList.remove('hide');adminEdit.innerHTML=`<h3>ADMIN: Sửa câu hỏi</h3><div class="field"><label>Nội dung</label><textarea id="edit_CauHoi">${raw(q.CauHoi)}</textarea></div><div class="row"><div class="field"><label>A</label><textarea id="edit_A">${raw(q.A)}</textarea></div><div class="field"><label>B</label><textarea id="edit_B">${raw(q.B)}</textarea></div><div class="field"><label>C</label><textarea id="edit_C">${raw(q.C)}</textarea></div><div class="field"><label>D</label><textarea id="edit_D">${raw(q.D)}</textarea></div></div><div class="row"><div class="field"><label>Đáp án</label><input id="edit_DapAn" value="${raw(q.DapAn)}"></div><div class="field"><label>Sai số</label><input id="edit_SaiSo" value="${raw(q.SaiSo)}"></div><div class="field"><label>Mức độ</label><input id="edit_MucDo" value="${raw(q.MucDo)}"></div><div class="field"><label>Dạng</label><input id="edit_Dang" value="${raw(q.Dang)}"></div><div class="field"><label>Quyền</label><input id="edit_QuyenTruyCap" value="${raw(q.QuyenTruyCap)}"></div></div><div class="field"><label>Lời giải</label><textarea id="edit_LoiGiai">${raw(q.LoiGiai)}</textarea></div><button class="btnG" onclick="saveEdit()">Lưu vào Google Sheet</button> <span id="editMsg"></span>`}async function saveEdit(){let q=QUESTIONS[CUR];let fields={};for(let k of ['CauHoi','A','B','C','D','DapAn','SaiSo','MucDo','Dang','LoiGiai','QuyenTruyCap'])fields[k]=document.getElementById('edit_'+k).value;editMsg.textContent='Đang lưu...';try{let j=await api('/api/admin/update_question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row_index:q.row_index,fields})});Object.assign(q,fields);editMsg.textContent='Đã lưu.';renderQuestion()}catch(e){editMsg.textContent=e.message}}async function use5050(){saveCurrent();try{let j=await api('/api/fifty',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR})});for(let L of j.hide||[]){let el=document.getElementById('opt_'+L);if(el)el.classList.add('optionHidden')}btn5050.disabled=true;if(j.message)alert(j.message)}catch(e){alert(e.message)}}async function submitQuiz(){saveCurrent();if(!confirm('Nộp bài và xem kết quả?'))return;try{let j=await api('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,answers:ANSWERS})});SUBMITTED=true;RESULTS={};for(let r of j.results)RESULTS[r.index]=r;scoreBox.textContent=`Điểm: ${j.score}/10 | Đúng ${j.correct_count}/${j.auto_count}`;QUIZ_PERM.can_view_solution=true;renderQuestion();renderNav()}catch(e){alert(e.message)}}checkMe();
</script></body></html>
'''

@app.route("/version")
def version():
    return jsonify({"version": APP_VERSION, "login_required": True, "admin_can_view_without_submit": True, "admin_can_edit_question": True, "trial_register_3_days": True, "trial_only_free_exam": True, "trial_no_submit_no_score": True, "safe_loading_notice": True, "filter_fix_exact_columns": True})

@app.route("/")
def index(): return render_template_string(HTML)

@app.route("/api/me")
def api_me():
    user = current_user()
    if not user: return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "user": public_user(user)})


def public_user(u: Dict[str, Any]) -> Dict[str, Any]:
    return {"MaHS": u.get("MaHS"), "HoTen": u.get("HoTen"), "LopHoc": u.get("LopHoc"), "LoaiTaiKhoan": norm_role(u.get("LoaiTaiKhoan")), "NgayHetHanTrial": u.get("NgayHetHanTrial"), "NgayHetHanTaiKhoan": u.get("NgayHetHanTaiKhoan")}

@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.get_json(silent=True) or {}; mahs = clean(body.get("mahs")); password = clean(body.get("password")); device_id = clean(body.get("device_id"))
    if not mahs or not password: return jsonify({"error": "Vui lòng nhập mã học sinh và mật khẩu."}), 400
    user = read_users_from_sheet(force=True).get(mahs)
    if not user or clean(user.get("MatKhau")) != password: return jsonify({"error": "Sai tài khoản hoặc mật khẩu."}), 401
    if user["TrangThai"] not in ["ON", "ACTIVE", "TRUE", "1"]: return jsonify({"error": "Tài khoản chưa được kích hoạt hoặc đã bị khóa."}), 403
    role = norm_role(user.get("LoaiTaiKhoan"))
    if role == "TRIAL" and is_expired_date(user.get("NgayHetHanTrial", "")): return jsonify({"error": "Tài khoản dùng thử đã hết hạn."}), 403
    if role in ["VIP", "S.VIP"] and is_expired_date(user.get("NgayHetHanTaiKhoan", "")): return jsonify({"error": "Tài khoản đã hết hạn."}), 403
    token = make_session_token(); session.clear(); session["MaHS"] = mahs; session["SessionToken"] = token; update_user_session_token(user, token, device_id)
    return jsonify({"ok": True, "user": public_user(user)})

@app.route("/api/logout", methods=["POST"])
def api_logout(): session.clear(); return jsonify({"ok": True})

@app.route("/api/register_trial", methods=["POST"])
def api_register_trial():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(register_trial_user(clean(body.get("hoten")), clean(body.get("lop")), clean(body.get("phone")), clean(body.get("password")), clean(body.get("device_id"))))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/meta")
def api_meta():
    user, resp, status = login_required_api()
    if resp is not None: return resp, status
    with DATA_LOCK:
        loaded = DATA_CACHE["loaded"]; loading = DATA_CACHE["loading"]; error = DATA_CACHE["error"]
    if not loaded:
        if not loading: start_background_load(False)
        return jsonify({"loading": True, "error": error, "message": "Đang nạp dữ liệu Google Sheet.", "notice": "Lần đầu Render Free có thể chờ 10–40 giây."})
    with DATA_LOCK:
        questions = DATA_CACHE["questions"]; catalog = [dict(x) for x in DATA_CACHE["catalog"]]; loaded_at = DATA_CACHE["loaded_at"]; err = DATA_CACHE["error"]
    role = norm_role(user["LoaiTaiKhoan"])
    for item in catalog: item["can_open"] = can_open_exam(role, item.get("QuyenTruyCap", "FREE"))
    def opts(field: str) -> List[str]: return sorted({clean(x.get(field, "")) for x in catalog if clean(x.get(field, ""))}, key=knorm)
    return jsonify({"loading": False, "error": err, "loaded_at": loaded_at, "count_questions": len(questions), "count_catalog": len(catalog), "filters": {"Mon": opts("Mon"), "Lop": opts("Lop"), "Chuong": opts("Chuong"), "BaiHoc": opts("BaiHoc"), "BoDe": opts("BoDe")}, "catalog": catalog})

@app.route("/api/admin/sync", methods=["POST"])
def api_admin_sync():
    user, resp, status = admin_required_api()
    if resp is not None: return resp, status
    start_background_load(True); return jsonify({"ok": True, "message": "Đang đồng bộ dữ liệu Google Sheet trong nền."})

@app.route("/api/admin/debug")
def api_admin_debug():
    user, resp, status = admin_required_api()
    if resp is not None: return resp, status
    with DATA_LOCK:
        return jsonify({"loaded": DATA_CACHE["loaded"], "loading": DATA_CACHE["loading"], "error": DATA_CACHE["error"], "loaded_at": DATA_CACHE["loaded_at"], "count_questions": len(DATA_CACHE["questions"]), "count_catalog": len(DATA_CACHE["catalog"]), "headers": DATA_CACHE["headers"], "header_map": DATA_CACHE["header_map"], "sample_rows": DATA_CACHE["sample_rows"]})

@app.route("/api/start")
def api_start():
    user, resp, status = login_required_api()
    if resp is not None: return resp, status
    made = clean(request.args.get("made"))
    if not made: return jsonify({"error": "Thiếu mã đề."}), 400
    questions, catalog = require_loaded(); qs = [q for q in questions if q.get("MaDe") == made]
    if not qs: return jsonify({"error": "Không tìm thấy câu hỏi của đề này. Hãy bấm ADMIN: Đồng bộ Sheet."}), 404
    item = next((x for x in catalog if x.get("MaDe") == made), {}); access = item.get("QuyenTruyCap", "FREE"); role = norm_role(user.get("LoaiTaiKhoan"))
    if not can_open_exam(role, access): return jsonify({"error": f"Tài khoản {role} không có quyền mở đề {access}."}), 403
    sid = make_session_token(); QUIZ_SESSIONS[sid] = {"MaHS": user.get("MaHS"), "role": role, "made": made, "title": item.get("De") or item.get("BaiHoc") or made, "access": access, "questions": qs, "used_5050": set(), "created": time.time()}
    admin_mode = role == "ADMIN"; trial_mode = role == "TRIAL"
    perms = {"admin_mode": admin_mode, "trial_mode": trial_mode, "can_submit": can_submit(role, access), "can_5050": can_use_5050(role), "can_view_solution": admin_mode}
    return jsonify({"sid": sid, "title": f"{item.get('Mon','')} {item.get('Lop','')} | {item.get('De') or item.get('BaiHoc') or ''}", "permissions": perms, "questions": [public_question(q, i, admin_mode) for i, q in enumerate(qs)]})


def public_question(q: Dict[str, Any], index: int, admin_mode: bool = False) -> Dict[str, Any]:
    out = {"index": index, "row_index": q.get("row_index"), "ID": q.get("ID", ""), "MaDe": q.get("MaDe", ""), "Dang": norm_dang(q.get("Dang", "")), "MucDo": q.get("MucDo", ""), "CauHoi": q.get("CauHoi", ""), "A": q.get("A", ""), "B": q.get("B", ""), "C": q.get("C", ""), "D": q.get("D", ""), "HinhAnh": q.get("HinhAnh", ""), "QuyenTruyCap": q.get("QuyenTruyCap", "FREE")}
    if admin_mode: out.update({"DapAn": q.get("DapAn", ""), "SaiSo": q.get("SaiSo", ""), "LoiGiai": q.get("LoiGiai", "")})
    return out

@app.route("/api/fifty", methods=["POST"])
def api_fifty():
    user, resp, status = login_required_api()
    if resp is not None: return resp, status
    role = norm_role(user.get("LoaiTaiKhoan"))
    if not can_use_5050(role): return jsonify({"error": "Chỉ VIP/S.VIP/ADMIN được dùng Loại 2 câu sai."}), 403
    body = request.get_json(silent=True) or {}; sid = clean(body.get("sid")); index = int(body.get("index", 0)); ses = QUIZ_SESSIONS.get(sid)
    if not ses: return jsonify({"error": "Phiên làm bài đã hết hạn."}), 400
    if ses.get("MaHS") != user.get("MaHS"): return jsonify({"error": "Phiên làm bài không thuộc tài khoản này."}), 403
    if index in ses["used_5050"]: return jsonify({"hide": [], "message": "Câu này đã dùng Loại 2 câu sai rồi."})
    qs = ses["questions"]
    if not (0 <= index < len(qs)): return jsonify({"error": "Số câu không hợp lệ."}), 400
    q = qs[index]
    if norm_dang(q.get("Dang", "")) != "Trắc nghiệm": return jsonify({"hide": [], "message": "Chỉ dùng được cho câu trắc nghiệm A-B-C-D."})
    correct = norm_letter(q.get("DapAn", "")); wrongs = [x for x in [L for L in "ABCD" if clean(q.get(L, ""))] if x != correct]
    random.shuffle(wrongs); hide = wrongs[:2]; ses["used_5050"].add(index); return jsonify({"hide": hide, "message": "Đã loại 2 câu sai."})

@app.route("/api/submit", methods=["POST"])
def api_submit():
    user, resp, status = login_required_api()
    if resp is not None: return resp, status
    body = request.get_json(silent=True) or {}; sid = clean(body.get("sid")); answers = body.get("answers") or {}; ses = QUIZ_SESSIONS.get(sid)
    if not ses: return jsonify({"error": "Phiên làm bài đã hết hạn."}), 400
    if ses.get("MaHS") != user.get("MaHS"): return jsonify({"error": "Phiên làm bài không thuộc tài khoản này."}), 403
    role = norm_role(user.get("LoaiTaiKhoan")); access = ses.get("access", "FREE")
    if not can_submit(role, access): return jsonify({"error": "Tài khoản này không được nộp/chấm điểm đề này."}), 403
    results = []; correct_count = 0; auto_count = 0
    for i, q in enumerate(ses["questions"]):
        ok, correct, chosen = check_answer(q, answers.get(str(i), "")); dang = norm_dang(q.get("Dang", ""))
        if dang != "Tự luận": auto_count += 1; correct_count += 1 if ok else 0
        results.append({"index": i, "ID": q.get("ID"), "ok": ok, "correct": correct, "chosen": chosen, "DapAn": q.get("DapAn", ""), "LoiGiai": q.get("LoiGiai", "")})
    score = round(10 * correct_count / auto_count, 2) if auto_count else 0; save_result_to_sheet(user, ses.get("made"), ses.get("title"), score, correct_count, auto_count, results)
    return jsonify({"score": score, "correct_count": correct_count, "auto_count": auto_count, "total": len(ses["questions"]), "results": results})

@app.route("/api/admin/update_question", methods=["POST"])
def api_admin_update_question():
    user, resp, status = admin_required_api()
    if resp is not None: return resp, status
    body = request.get_json(silent=True) or {}; row_index = int(body.get("row_index") or 0); fields = body.get("fields") or {}
    if row_index <= 1: return jsonify({"error": "row_index không hợp lệ."}), 400
    sh = get_sheet(); ws = sh.worksheet("Cau_Hoi"); values = ws.get_all_values(); headers = [clean(x) for x in values[0]]; hmap = header_map(headers); changed = False
    for field in fields.keys():
        if field not in hmap: headers.append("NoiDung" if field == "CauHoi" else field); changed = True
    if changed: ws.update("A1", [headers]); hmap = header_map(headers)
    updates = []
    for field, value in fields.items():
        col0 = hmap.get(field)
        if col0 is not None: updates.append({"range": gspread.utils.rowcol_to_a1(row_index, col0 + 1), "values": [[value]]})
    if updates: ws.batch_update(updates)
    with DATA_LOCK:
        for q in DATA_CACHE["questions"]:
            if int(q.get("row_index", 0)) == row_index: q.update(fields); q["Dang"] = norm_dang(q.get("Dang", "")); q["QuyenTruyCap"] = norm_access(q.get("QuyenTruyCap", "FREE")); break
        DATA_CACHE["catalog"] = build_catalog(DATA_CACHE["questions"]); DATA_CACHE["loaded_at"] = now_str()
    return jsonify({"ok": True, "message": "Đã lưu câu hỏi vào Google Sheet."})

@app.before_request
def warmup():
    if request.path.startswith("/api/login") or request.path.startswith("/api/register_trial") or request.path in ["/", "/api/me", "/version"]: return
    with DATA_LOCK:
        if not DATA_CACHE["loaded"] and not DATA_CACHE["loading"]: start_background_load(False)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000")); app.run(host="0.0.0.0", port=port, debug=False)
