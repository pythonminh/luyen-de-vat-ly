# -*- coding: utf-8 -*-
"""
app.py - Ứng dụng luyện đề chạy Render + Google Sheet
====================================================
- Flask + Gunicorn.
- Đọc trực tiếp Google Sheet bằng GOOGLE_SHEET_ID và GOOGLE_CREDENTIALS_JSON.
- Đăng nhập bằng sheet HOC_VIEN: MaHS + MatKhau.
- Chống dùng chung tài khoản: đăng nhập mới đá phiên cũ.
- FREE: làm bài, xem điểm, không xem đáp án/lời giải.
- VIP/S.VIP: làm bài, dùng 50:50, xem đáp án/lời giải sau khi nộp.
- ADMIN: đăng nhập là xem đáp án/lời giải ngay, không cần làm; được sửa câu hỏi và ghi ngược Google Sheet.

Render Start Command:
    gunicorn app:app --bind 0.0.0.0:$PORT

requirements.txt:
    flask
    gunicorn
    gspread
    google-auth
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

APP_VERSION = "2026_05_30_V4"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "doi-khoa-bi-mat-nay-2026")
app.config["JSON_AS_ASCII"] = False

# ============================================================
# TIỆN ÍCH
# ============================================================

def strip_accents(s: Any) -> str:
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def key_norm(s: Any) -> str:
    s = strip_accents(str(s or "").strip().lower())
    s = re.sub(r"\s+", " ", s)
    return s


def clean(v: Any) -> str:
    s = str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def stable_hash(text: str, n: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n].upper()


def get_any(row: Dict[str, Any], names: List[str], default: str = "") -> str:
    keys = {key_norm(k): k for k in row.keys()}
    for name in names:
        k = keys.get(key_norm(name))
        if k is not None:
            return clean(row.get(k, default))
    return default


ALIASES: Dict[str, List[str]] = {
    "MaDe": ["MaDe", "Mã đề", "Ma De", "MA_DE", "ma_de"],
    "ID": ["ID", "Id", "Mã câu", "MaCau", "Ma Cau"],
    "BoDe": ["BoDe", "Bộ đề", "Bo De", "Bộ Đề"],
    "De": ["De", "Đề", "TenDe", "Tên đề", "Tên Đề"],
    "Lop": ["Lop", "Lớp", "LopHoc", "Lớp học", "Khoi", "Khối"],
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
    "HinhAnh": ["HinhAnh", "Hình ảnh", "Hình Ảnh", "Image"],
    "QuyenTruyCap": ["QuyenTruyCap", "Quyền truy cập", "Quyen", "Goi"],
}

FIELDS = [
    "MaDe", "ID", "BoDe", "De", "Lop", "Mon", "Chuong", "BaiHoc", "DangBaiTap", "MucDo",
    "Dang", "CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo", "LoiGiai", "HinhAnh", "QuyenTruyCap",
]

EDITABLE_FIELDS = ["CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo", "LoiGiai", "MucDo", "Dang", "DangBaiTap", "Chuong", "BaiHoc", "De", "BoDe", "HinhAnh"]


def normalize_dang(s: str) -> str:
    k = key_norm(s)
    if any(x in k for x in ["dung sai", "true", "tf", "ds"]):
        return "Đúng sai"
    if any(x in k for x in ["tra loi ngan", "short", "tln"]):
        return "Trả lời ngắn"
    if any(x in k for x in ["tu luan", "essay", "tl"]):
        return "Tự luận"
    return "Trắc nghiệm"


def make_made(q: Dict[str, str]) -> str:
    if clean(q.get("MaDe")):
        return clean(q.get("MaDe"))
    base = "|".join(key_norm(q.get(k, "")) for k in ["Lop", "Mon", "Chuong", "BaiHoc", "DangBaiTap", "BoDe", "De"])
    return "MD_" + stable_hash(base, 10)


def canonical_question(row: Dict[str, Any]) -> Dict[str, str]:
    q = {f: get_any(row, ALIASES.get(f, [f])) for f in FIELDS}
    q["Dang"] = normalize_dang(q.get("Dang", ""))
    q["MaDe"] = make_made(q)
    if not q.get("ID"):
        q["ID"] = "AUTO_" + stable_hash(json.dumps(q, ensure_ascii=False), 10)
    return q


def norm_letter(s: Any) -> str:
    m = re.search(r"[ABCD]", clean(s).upper())
    return m.group(0) if m else ""


def norm_tf_answer(s: Any) -> List[str]:
    x = strip_accents(clean(s).upper())
    x = x.replace("DUNG", "D").replace("TRUE", "D").replace("SAI", "S").replace("FALSE", "S")
    return re.findall(r"[DS]", x)[:4]


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


def check_answer(q: Dict[str, str], user_answer: Any) -> Tuple[bool, str, str]:
    dang = normalize_dang(q.get("Dang", ""))
    correct_raw = clean(q.get("DapAn", ""))
    if dang == "Trắc nghiệm":
        correct = norm_letter(correct_raw)
        chosen = norm_letter(user_answer)
        return bool(correct and chosen and correct == chosen), correct, chosen
    if dang == "Đúng sai":
        corr0 = norm_tf_answer(correct_raw)
        corr = ["Đ" if x == "D" else "S" for x in corr0]
        if isinstance(user_answer, list):
            chosen = ["Đ" if key_norm(x) in ["d", "dung", "đ", "đúng"] else "S" if key_norm(x) in ["s", "sai"] else "" for x in user_answer]
        else:
            chosen = ["Đ" if x == "D" else "S" for x in norm_tf_answer(user_answer)]
        while len(chosen) < 4:
            chosen.append("")
        ok = len(corr) == 4 and chosen[:4] == corr[:4]
        return ok, ",".join(corr), ",".join(chosen[:4])
    if dang == "Trả lời ngắn":
        cnum = parse_float_vn(correct_raw)
        unum = parse_float_vn(user_answer)
        tol = parse_float_vn(q.get("SaiSo", "")) or 0.0
        if cnum is not None and unum is not None:
            return abs(unum - cnum) <= tol + 1e-12, correct_raw, clean(user_answer)
        return key_norm(correct_raw) == key_norm(user_answer), correct_raw, clean(user_answer)
    return False, correct_raw, clean(user_answer)

# ============================================================
# GOOGLE SHEET
# ============================================================

class SheetClient:
    def __init__(self):
        self.gc = None
        self.sh = None
        self.connected = False
        self.error = ""
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
            sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
            if not creds_json or not sheet_id:
                raise RuntimeError("Thiếu GOOGLE_CREDENTIALS_JSON hoặc GOOGLE_SHEET_ID")
            info = json.loads(creds_json)
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(info, scopes=scopes)
            self.gc = gspread.authorize(creds)
            self.sh = self.gc.open_by_key(sheet_id)
            self.connected = True
        except Exception as e:
            self.error = str(e)

    def rows(self, worksheet_name: str) -> List[Dict[str, Any]]:
        if not self.connected:
            raise RuntimeError(self.error or "Chưa kết nối Google Sheet")
        ws = self.sh.worksheet(worksheet_name)
        return ws.get_all_records()

    def worksheet(self, worksheet_name: str):
        if not self.connected:
            raise RuntimeError(self.error or "Chưa kết nối Google Sheet")
        return self.sh.worksheet(worksheet_name)

    def ensure_worksheet(self, worksheet_name: str, headers: List[str]):
        if not self.connected:
            raise RuntimeError(self.error or "Chưa kết nối Google Sheet")
        try:
            ws = self.sh.worksheet(worksheet_name)
        except Exception:
            ws = self.sh.add_worksheet(title=worksheet_name, rows=1000, cols=max(10, len(headers)))
            ws.append_row(headers)
        return ws

    def _header_index(self, headers: List[str], aliases: List[str]) -> Optional[int]:
        hmap = {key_norm(h): i for i, h in enumerate(headers)}
        for a in aliases:
            if key_norm(a) in hmap:
                return hmap[key_norm(a)]
        return None

    def update_question_by_id(self, question_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """ADMIN sửa câu hỏi trực tiếp trong sheet Cau_Hoi theo cột ID."""
        ws = self.worksheet("Cau_Hoi")
        values = ws.get_all_values()
        if not values:
            raise RuntimeError("Sheet Cau_Hoi đang trống")
        headers = values[0]
        id_col = self._header_index(headers, ALIASES["ID"])
        if id_col is None:
            raise RuntimeError("Sheet Cau_Hoi chưa có cột ID")

        target_row = None
        for r_idx, row in enumerate(values[1:], start=2):
            val = row[id_col] if id_col < len(row) else ""
            if clean(val) == clean(question_id):
                target_row = r_idx
                break
        if target_row is None:
            raise RuntimeError(f"Không tìm thấy câu có ID: {question_id}")

        changed: Dict[str, str] = {}
        for field, value in updates.items():
            if field not in EDITABLE_FIELDS:
                continue
            col = self._header_index(headers, ALIASES.get(field, [field]))
            if col is None:
                continue
            ws.update_cell(target_row, col + 1, clean(value))
            changed[field] = clean(value)
        if not changed:
            raise RuntimeError("Không có cột nào được cập nhật. Kiểm tra tên cột trong sheet Cau_Hoi.")
        return {"row": target_row, "changed": changed}


SHEET = SheetClient()

# ============================================================
# KHO DỮ LIỆU
# ============================================================

class Store:
    def __init__(self):
        self.questions: List[Dict[str, str]] = []
        self.catalog: List[Dict[str, str]] = []
        self.by_made: Dict[str, List[Dict[str, str]]] = {}
        self.users: Dict[str, Dict[str, str]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.loaded_at = ""
        self.last_error = ""
        self.sync()

    def sync(self):
        self.last_error = ""
        try:
            qrows = SHEET.rows("Cau_Hoi")
            questions: List[Dict[str, str]] = []
            for row in qrows:
                q = canonical_question(row)
                if not clean(q.get("CauHoi")):
                    continue
                questions.append(q)
            self.questions = questions
            self._reindex()
            self.users = self._load_users()
            self.loaded_at = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            self.last_error = str(e)
            # fallback JSON để app không chết khi đang cấu hình Google Sheet
            path = "luyen_de_vat_ly.json"
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.questions = data.get("questions", [])
                for q in self.questions:
                    q["MaDe"] = q.get("MaDe") or make_made(q)
                self._reindex()

    def _reindex(self):
        self.by_made = {}
        for q in self.questions:
            q["MaDe"] = q.get("MaDe") or make_made(q)
            self.by_made.setdefault(q["MaDe"], []).append(q)
        self.catalog = self._build_catalog()

    def _build_catalog(self) -> List[Dict[str, str]]:
        groups: Dict[str, Dict[str, Any]] = {}
        for q in self.questions:
            m = q.get("MaDe") or make_made(q)
            if m not in groups:
                groups[m] = {
                    "MaDe": m, "Lop": q.get("Lop", ""), "Mon": q.get("Mon", ""),
                    "Chuong": q.get("Chuong", ""), "BaiHoc": q.get("BaiHoc", ""),
                    "DangBaiTap": q.get("DangBaiTap", ""), "BoDe": q.get("BoDe", ""),
                    "De": q.get("De", ""), "SoCau": 0, "MucDo": set(), "Dang": set(), "QuyenTruyCap": set(),
                }
            g = groups[m]
            g["SoCau"] += 1
            if q.get("MucDo"):
                g["MucDo"].add(q["MucDo"])
            if q.get("Dang"):
                g["Dang"].add(q["Dang"])
            if q.get("QuyenTruyCap"):
                g["QuyenTruyCap"].add(q["QuyenTruyCap"])
        out: List[Dict[str, str]] = []
        for g in groups.values():
            item = dict(g)
            item["SoCau"] = str(g["SoCau"])
            item["MucDo"] = ", ".join(sorted(g["MucDo"]))
            item["Dang"] = ", ".join(sorted(g["Dang"]))
            item["QuyenTruyCap"] = ", ".join(sorted(g["QuyenTruyCap"]))
            out.append(item)
        out.sort(key=lambda x: (key_norm(x.get("Mon")), key_norm(x.get("Lop")), key_norm(x.get("Chuong")), key_norm(x.get("BaiHoc")), key_norm(x.get("De"))))
        return out

    def _load_users(self) -> Dict[str, Dict[str, str]]:
        users: Dict[str, Dict[str, str]] = {}
        try:
            rows = SHEET.rows("HOC_VIEN")
        except Exception:
            return users
        for r in rows:
            mahs = get_any(r, ["MaHS", "Mã HS", "TaiKhoan", "Tài khoản", "Username"])
            if not mahs:
                continue
            phone = get_any(r, ["SoDienThoai", "Số điện thoại", "SDT", "SĐT"])
            password = get_any(r, ["MatKhau", "Mật khẩu", "Password"])
            if not password:
                digits = re.sub(r"\D", "", phone)
                password = digits[-6:] if len(digits) >= 6 else "123456"
            role = get_any(r, ["LoaiTaiKhoan", "Loại tài khoản", "Role", "Quyen"], "FREE").upper().replace(" ", "")
            if role in ["SVIP", "S-VIP", "S_VIP"]:
                role = "S.VIP"
            elif role not in ["FREE", "VIP", "S.VIP", "ADMIN"]:
                role = "FREE"
            status = get_any(r, ["TrangThai", "Trạng thái", "Status"], "ON").upper()
            users[mahs] = {
                "mahs": mahs,
                "hoten": get_any(r, ["HoTen", "Họ tên", "HọTên", "Name"]),
                "lop": get_any(r, ["LopHoc", "Lớp học", "Lop", "Lớp"]),
                "password": password,
                "role": role,
                "status": status,
                "phone": phone,
                "device_id": get_any(r, ["DeviceId", "DeviceID", "Thiết bị"]),
                "session_token": get_any(r, ["SessionToken"]),
            }
        return users

    def meta(self) -> Dict[str, Any]:
        def opts(field: str):
            return sorted({clean(x.get(field, "")) for x in self.catalog if clean(x.get(field, ""))}, key=key_norm)
        return {
            "version": APP_VERSION,
            "loaded_at": self.loaded_at,
            "sheet_connected": SHEET.connected,
            "sheet_error": SHEET.error,
            "last_error": self.last_error,
            "count_questions": len(self.questions),
            "count_catalog": len(self.catalog),
            "filters": {"Mon": opts("Mon"), "Lop": opts("Lop"), "Chuong": opts("Chuong"), "BaiHoc": opts("BaiHoc"), "BoDe": opts("BoDe")},
            "catalog": self.catalog,
        }

    def public_question(self, q: Dict[str, str], index: int, include_secret: bool = False) -> Dict[str, Any]:
        item = {
            "index": index,
            "ID": q.get("ID", ""),
            "MaDe": q.get("MaDe", ""),
            "Dang": normalize_dang(q.get("Dang", "")),
            "MucDo": q.get("MucDo", ""),
            "CauHoi": q.get("CauHoi", ""),
            "A": q.get("A", ""), "B": q.get("B", ""), "C": q.get("C", ""), "D": q.get("D", ""),
            "HinhAnh": q.get("HinhAnh", ""),
        }
        if include_secret:
            item.update({
                "DapAn": q.get("DapAn", ""),
                "SaiSo": q.get("SaiSo", ""),
                "LoiGiai": q.get("LoiGiai", ""),
                "DangBaiTap": q.get("DangBaiTap", ""),
                "Chuong": q.get("Chuong", ""),
                "BaiHoc": q.get("BaiHoc", ""),
                "De": q.get("De", ""),
                "BoDe": q.get("BoDe", ""),
            })
        return item

    def start_quiz(self, made: str) -> Dict[str, Any]:
        qs = list(self.by_made.get(made, []))
        if not qs:
            raise ValueError("Không có câu hỏi trong đề này")
        sid = stable_hash(f"{made}|{time.time()}|{random.random()}", 16)
        self.sessions[sid] = {"made": made, "created": time.time(), "questions": qs, "used_5050": set(), "mahs": current_user().get("mahs", "")}
        include_secret = current_role() == "ADMIN"
        return {"sid": sid, "admin_mode": include_secret, "questions": [self.public_question(q, i, include_secret=include_secret) for i, q in enumerate(qs)]}

    def question_by_id(self, question_id: str) -> Dict[str, str]:
        for q in self.questions:
            if clean(q.get("ID")) == clean(question_id):
                return q
        raise ValueError(f"Không tìm thấy câu ID: {question_id}")

    def update_question(self, question_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        changed_result = SHEET.update_question_by_id(question_id, updates)
        changed = changed_result.get("changed", {})
        # Cập nhật bộ nhớ RAM ngay, không cần đợi sync.
        q = self.question_by_id(question_id)
        for k, v in changed.items():
            q[k] = clean(v)
        if "Dang" in q:
            q["Dang"] = normalize_dang(q.get("Dang", ""))
        if any(k in changed for k in ["MaDe", "Lop", "Mon", "Chuong", "BaiHoc", "DangBaiTap", "BoDe", "De"]):
            q["MaDe"] = make_made(q)
        self._reindex()
        return changed_result

    def fifty_fifty(self, sid: str, index: int) -> Dict[str, Any]:
        ses = self.sessions.get(sid)
        if not ses:
            raise ValueError("Phiên làm bài đã hết hạn")
        if index in ses["used_5050"]:
            return {"hide": [], "message": "Câu này đã dùng Loại 2 câu sai rồi."}
        qs = ses["questions"]
        if not (0 <= index < len(qs)):
            raise ValueError("Số câu không hợp lệ")
        q = qs[index]
        if normalize_dang(q.get("Dang", "")) != "Trắc nghiệm":
            return {"hide": [], "message": "Chỉ dùng được cho câu trắc nghiệm A-B-C-D."}
        correct = norm_letter(q.get("DapAn", ""))
        letters = [x for x in "ABCD" if clean(q.get(x, ""))]
        wrongs = [x for x in letters if x != correct]
        random.shuffle(wrongs)
        hide = wrongs[:2]
        ses["used_5050"].add(index)
        return {"hide": hide, "message": "Đã loại 2 câu sai."}

    def submit(self, sid: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        ses = self.sessions.get(sid)
        if not ses:
            raise ValueError("Phiên làm bài đã hết hạn")
        qs = ses["questions"]
        role = current_role()
        can_view = role in ["VIP", "S.VIP", "ADMIN"]
        results = []
        correct_count = 0
        auto_count = 0
        for i, q in enumerate(qs):
            ans = answers.get(str(i), "")
            ok, correct, chosen = check_answer(q, ans)
            dang = normalize_dang(q.get("Dang", ""))
            if dang != "Tự luận":
                auto_count += 1
                if ok:
                    correct_count += 1
            item = {"index": i, "ID": q.get("ID", ""), "Dang": dang, "ok": ok, "chosen": chosen}
            if can_view:
                item.update({"correct": correct, "LoiGiai": q.get("LoiGiai", ""), "DapAn": q.get("DapAn", "")})
            results.append(item)
        score = round(10 * correct_count / auto_count, 2) if auto_count else 0
        self._save_result(ses.get("made", ""), score, correct_count, auto_count)
        return {"total": len(qs), "auto_count": auto_count, "correct_count": correct_count, "score": score, "can_view_solution": can_view, "results": results}

    def _save_result(self, made: str, score: float, correct_count: int, auto_count: int) -> None:
        try:
            user = current_user()
            ws = SHEET.ensure_worksheet("Ket_Qua", ["ThoiGian", "MaHS", "HoTen", "Lop", "LoaiTaiKhoan", "MaDe", "Diem", "SoDung", "TongCau"])
            ws.append_row([time.strftime("%Y-%m-%d %H:%M:%S"), user.get("mahs", ""), user.get("hoten", ""), user.get("lop", ""), user.get("role", ""), made, score, correct_count, auto_count])
        except Exception:
            pass


STORE = Store()

# ============================================================
# ĐĂNG NHẬP / PHÂN QUYỀN
# ============================================================

def current_user() -> Dict[str, str]:
    mahs = session.get("mahs", "")
    return STORE.users.get(mahs, {})


def current_role() -> str:
    return current_user().get("role", "FREE")


def can_use_5050() -> bool:
    return current_role() in ["VIP", "S.VIP", "ADMIN"]


def is_admin() -> bool:
    return current_role() == "ADMIN"


def update_session_token(mahs: str, token: str) -> None:
    if mahs in STORE.users:
        STORE.users[mahs]["session_token"] = token
    try:
        ws = SHEET.worksheet("HOC_VIEN")
        values = ws.get_all_values()
        if not values:
            return
        headers = values[0]
        hmap = {key_norm(h): i for i, h in enumerate(headers)}
        mahs_col = None
        for a in ["MaHS", "Mã HS", "TaiKhoan", "Tài khoản", "Username"]:
            if key_norm(a) in hmap:
                mahs_col = hmap[key_norm(a)]
                break
        if mahs_col is None:
            return
        token_col = hmap.get(key_norm("SessionToken"))
        if token_col is None:
            ws.update_cell(1, len(headers) + 1, "SessionToken")
            token_col = len(headers)
        for r_idx, row in enumerate(values[1:], start=2):
            val = row[mahs_col] if mahs_col < len(row) else ""
            if clean(val) == mahs:
                ws.update_cell(r_idx, token_col + 1, token)
                break
    except Exception:
        pass


def ensure_login_response():
    mahs = session.get("mahs")
    token = session.get("session_token")
    if not mahs or not token:
        return redirect(url_for("login"))
    u = STORE.users.get(mahs)
    if not u:
        session.clear()
        return redirect(url_for("login", msg="Tài khoản không còn tồn tại."))
    if u.get("status", "ON").upper() not in ["ON", "ACTIVE", "VIP", "S.VIP", "ADMIN"]:
        session.clear()
        return redirect(url_for("login", msg="Tài khoản đang bị khóa hoặc hết hạn."))
    saved = u.get("session_token", "")
    if saved and saved != token:
        session.clear()
        return redirect(url_for("login", msg="Tài khoản này đã đăng nhập ở thiết bị khác."))
    return None

# ============================================================
# HTML
# ============================================================

LOGIN_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Đăng nhập luyện đề</title>
<style>body{font-family:Arial;background:#f5f7fb;margin:0}.top{background:#1d4ed8;color:#fff;padding:14px 18px}.box{max-width:430px;margin:48px auto;background:#fff;border:1px solid #d6dee9;border-radius:14px;padding:22px;box-shadow:0 2px 10px #0001}input,button{width:100%;padding:12px;border-radius:9px;border:1px solid #d6dee9;margin:8px 0;font-size:16px}button{background:#1d4ed8;color:#fff;font-weight:700;cursor:pointer}.err{background:#fee2e2;color:#991b1b;padding:10px;border-radius:8px;margin-bottom:10px}.hint{background:#eff6ff;color:#1e3a8a;padding:10px;border-radius:8px;font-size:14px}</style>
</head><body><div class="top"><b>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</b></div><div class="box">
<h2>Đăng nhập học viên</h2>
{% if msg %}<div class="err">{{msg}}</div>{% endif %}
<form method="post"><label>Mã học sinh / MaHS</label><input name="mahs" autocomplete="username" autofocus required><label>Mật khẩu</label><input type="password" name="password" autocomplete="current-password" required><button>Đăng nhập</button></form>
<div class="hint">ADMIN đăng nhập bằng tài khoản có <b>LoaiTaiKhoan = ADMIN</b> trong sheet <b>HOC_VIEN</b>. ADMIN được xem đáp án/lời giải ngay và sửa câu hỏi.</div>
</div></body></html>
"""

INDEX_HTML = r"""
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ứng dụng luyện đề</title>
  <script>window.MathJax={tex:{inlineMath:[["$","$"],["\\(","\\)"]],displayMath:[["$$","$$"],["\\[","\\]"]]},svg:{fontCache:"global"}};</script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
  <style>
    :root{--blue:#1d4ed8;--green:#dcfce7;--red:#fee2e2;--border:#d6dee9;--bg:#f5f7fb;--text:#111827}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:Arial,Helvetica,sans-serif;color:var(--text);font-size:15px}.top{background:var(--blue);color:#fff;padding:12px 18px;position:sticky;top:0;z-index:5;box-shadow:0 2px 8px #0002}.top h1{margin:0;font-size:20px}.top small{opacity:.95}.wrap{padding:14px;max-width:1380px;margin:auto}.panel{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:12px;box-shadow:0 1px 3px #0001}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:4px;min-width:150px;flex:1}.field label{font-weight:700;font-size:12px;color:#374151}select,input,button,textarea{font-family:inherit;font-size:14px;border:1px solid var(--border);border-radius:8px;padding:9px 10px;background:#fff}button{cursor:pointer;font-weight:700}.btn{background:var(--blue);color:#fff;border-color:var(--blue)}.btn2{background:#eef2ff;color:#1e40af}.btnGreen{background:#dcfce7;color:#166534;border-color:#bbf7d0}.btnRed{background:#fee2e2;color:#991b1b;border-color:#fecaca}.btnOrange{background:#fff7ed;color:#9a3412;border-color:#fed7aa}.btn:disabled,button:disabled{opacity:.55;cursor:not-allowed}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}.card{border:1px solid var(--border);background:#fff;border-radius:12px;padding:12px}.card h3{margin:0 0 8px;font-size:16px;color:#1e3a8a}.tag{display:inline-block;padding:3px 8px;border-radius:999px;background:#eef2ff;color:#1d4ed8;font-size:12px;font-weight:700;margin:2px}.muted{color:#6b7280}.line{height:1px;background:var(--border);margin:10px 0}.quizLayout{display:grid;grid-template-columns:1fr 280px;gap:12px}.qbox{border:1px solid #111827;background:#fff;border-radius:8px;padding:14px;min-height:170px;line-height:1.55;font-size:18px}.qid{font-size:20px;font-weight:800;margin-bottom:10px}.options{margin-top:12px}.opt{display:flex;gap:9px;align-items:flex-start;border:1px solid transparent;border-radius:10px;padding:10px;margin:7px 0;background:#fff}.optionHidden{opacity:.25;pointer-events:none;text-decoration:line-through}.correct{background:var(--green)!important;border-color:#86efac!important}.wrong{background:var(--red)!important;border-color:#fecaca!important}.tfrow{display:grid;grid-template-columns:36px 1fr 90px 90px;gap:8px;align-items:center;border:1px solid var(--border);border-radius:10px;padding:8px;margin:8px 0}.navNums{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.num{padding:8px 0;border-radius:8px;background:#fff;border:1px solid var(--border);font-weight:800}.num.active{outline:3px solid #93c5fd}.num.answered{background:#fef3c7}.num.ok{background:var(--green);color:#166534}.num.bad{background:var(--red);color:#991b1b}.solution{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px;margin-top:12px;display:none}.adminEdit{background:#f8fafc;border:1px solid #cbd5e1;border-radius:10px;padding:12px;margin-top:12px;display:none}.adminEdit textarea{width:100%;min-height:70px}.resultBox{font-size:18px;font-weight:800}.hide{display:none!important}.imgQ{max-width:100%;border:1px solid var(--border);border-radius:8px;margin-top:10px}@media(max-width:900px){.quizLayout{grid-template-columns:1fr}.side{order:-1}.qbox{font-size:16px}.top h1{font-size:17px}}
  </style>
</head>
<body>
  <div class="top"><h1>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</h1><small id="info">Đang nạp dữ liệu...</small><span style="float:right">{{user.hoten}} - {{user.role}} | <a style="color:white" href="/logout">Thoát</a></span></div>
  <div class="wrap">
    <div class="panel row" style="justify-content:space-between"><div><b>Đã đăng nhập:</b> {{user.mahs}} - {{user.hoten}} - {{user.lop}} - {{user.role}}</div>{% if user.role=='ADMIN' %}<div><button class="btnRed" onclick="adminSync()">ADMIN: Đồng bộ Google Sheet</button></div>{% endif %}</div>
    {% if user.role=='ADMIN' %}<div class="panel" style="background:#fff7ed;border-color:#fed7aa"><b>Chế độ ADMIN:</b> Thầy xem đáp án/lời giải ngay, không cần làm bài. Có thể sửa câu và lưu ngược về Google Sheet.</div>{% endif %}
    <div id="home"><div class="panel"><b>Thiết lập luyện tập</b><div class="row" style="margin-top:10px"><div class="field"><label>Môn</label><select id="fMon"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="fLop"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="fChuong"><option value="">Tất cả</option></select></div><div class="field"><label>Bài học</label><select id="fBaiHoc"><option value="">Tất cả</option></select></div><div class="field"><label>Bộ đề</label><select id="fBoDe"><option value="">Tất cả</option></select></div><div class="field"><label>Tìm nhanh</label><input id="fSearch" placeholder="Nhập từ khóa..."></div><button class="btn" onclick="renderCatalog()">Lọc đề</button></div></div><div class="panel"><b>Mục lục đề</b> <span id="countCat" class="muted"></span><div id="catalog" class="grid" style="margin-top:10px"></div></div></div>
    <div id="quiz" class="hide"><div class="panel row" style="justify-content:space-between"><div><button class="btn2" onclick="backHome()">← Về mục lục</button> <span id="quizTitle" style="font-weight:800"></span></div><div class="resultBox" id="resultBox"></div></div><div class="quizLayout"><div><div class="panel"><div class="row" style="justify-content:space-between;align-items:center"><div class="qid" id="qid"></div><div><button id="btn5050" class="btnGreen" onclick="use5050()">Loại 2 câu sai</button><button id="btnAdminAnswer" class="btnOrange" onclick="adminShowAnswer()">ADMIN: Xem đáp án</button><button id="btnAdminEdit" class="btnRed" onclick="adminOpenEdit()">ADMIN: Sửa câu</button><button id="btnSubmit" class="btn" onclick="submitQuiz()">Nộp bài</button></div></div><div id="qtext" class="qbox"></div><div id="options" class="options"></div><div id="solution" class="solution"></div><div id="adminEdit" class="adminEdit"></div><div class="row" style="margin-top:12px;justify-content:space-between"><button onclick="prevQ()">← Câu trước</button><button onclick="nextQ()">Câu sau →</button></div></div></div><div class="side panel"><b>Bảng câu hỏi</b><div id="navNums" class="navNums" style="margin-top:10px"></div><div class="line"></div><div class="muted" id="sideHint">FREE chỉ xem điểm. VIP/S.VIP xem đáp án/lời giải sau nộp. ADMIN xem và sửa ngay.</div></div></div></div>
  </div>
<script>
let META=null,CATALOG=[],SID='',QUESTIONS=[],CUR=0,ANSWERS={},SUBMITTED=false,RESULTS={},CAN_VIEW=false;
const USER_ROLE={{user.role|tojson}};
const IS_ADMIN=USER_ROLE==='ADMIN';
let CAN_5050={{'true' if can5050 else 'false'}};
function h(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}
function br(s){return h(s).replace(/\n/g,'<br>')}
function val(id){return document.getElementById(id).value}
function setOptions(id,arr){document.getElementById(id).innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option>${h(x)}</option>`).join('')}
function typeset(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise().catch(()=>{})}
async function api(url,opts={}){let r=await fetch(url,opts); if(r.redirected){location.href=r.url;return} let j=await r.json(); if(!r.ok||j.error)throw new Error(j.error||'Lỗi API'); return j}
async function init(){META=await api('/api/meta');CATALOG=META.catalog;document.getElementById('info').textContent=`${META.count_questions} câu hỏi | ${META.count_catalog} đề/thẻ đề | ${META.version}`;setOptions('fMon',META.filters.Mon);setOptions('fLop',META.filters.Lop);setOptions('fChuong',META.filters.Chuong);setOptions('fBaiHoc',META.filters.BaiHoc);setOptions('fBoDe',META.filters.BoDe);renderCatalog()}
function okFilter(x){let s=val('fSearch').toLowerCase();let blob=[x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.DangBaiTap,x.BoDe,x.De,x.MucDo,x.Dang].join(' ').toLowerCase();return(!val('fMon')||x.Mon==val('fMon'))&&(!val('fLop')||x.Lop==val('fLop'))&&(!val('fChuong')||x.Chuong==val('fChuong'))&&(!val('fBaiHoc')||x.BaiHoc==val('fBaiHoc'))&&(!val('fBoDe')||x.BoDe==val('fBoDe'))&&(!s||blob.includes(s))}
function renderCatalog(){let list=CATALOG.filter(okFilter);document.getElementById('countCat').textContent=`(${list.length} mục)`;document.getElementById('catalog').innerHTML=list.map(x=>`<div class="card"><h3>${h(x.De||x.BaiHoc||'Đề luyện tập')}</h3><div><span class="tag">${h(x.Mon)}</span><span class="tag">Lớp ${h(x.Lop)}</span><span class="tag">${h(x.SoCau)} câu</span></div><div class="line"></div><div><b>Chương:</b> ${h(x.Chuong||'')}</div><div><b>Bài:</b> ${h(x.BaiHoc||'')}</div><div><b>Dạng:</b> ${h(x.Dang||'')}</div><div><b>Mức độ:</b> ${h(x.MucDo||'')}</div><div><b>Bộ đề:</b> ${h(x.BoDe||'')}</div><div style="text-align:right;margin-top:10px"><button class="btn" onclick="startQuiz('${x.MaDe}')">${IS_ADMIN?'Xem/Sửa':'Làm bài'}</button></div></div>`).join('')||'<div class="muted">Không có đề phù hợp.</div>';typeset()}
async function startQuiz(made){let j=await api('/api/start?made='+encodeURIComponent(made));SID=j.sid;QUESTIONS=j.questions;CUR=0;ANSWERS={};SUBMITTED=false;RESULTS={};CAN_VIEW=IS_ADMIN;document.getElementById('home').classList.add('hide');document.getElementById('quiz').classList.remove('hide');document.getElementById('resultBox').textContent=IS_ADMIN?'ADMIN: đang soát đề':'';let c=CATALOG.find(x=>x.MaDe==made)||{};document.getElementById('quizTitle').textContent=`${c.Mon||''} ${c.Lop?'- Lớp '+c.Lop:''} | ${c.De||c.BaiHoc||''}`;renderNav();renderQuestion()}
function backHome(){document.getElementById('quiz').classList.add('hide');document.getElementById('home').classList.remove('hide')}
function saveCurrent(){let q=QUESTIONS[CUR];if(!q||IS_ADMIN)return;if(q.Dang=='Trắc nghiệm'){let r=document.querySelector(`input[name="ans_${CUR}"]:checked`);if(r)ANSWERS[CUR]=r.value}else if(q.Dang=='Đúng sai'){let arr=[];for(let L of ['A','B','C','D']){let r=document.querySelector(`input[name="tf_${CUR}_${L}"]:checked`);arr.push(r?r.value:'')}ANSWERS[CUR]=arr}else{let el=document.getElementById('shortAns');if(el)ANSWERS[CUR]=el.value}renderNav()}
function renderNav(){let html='';for(let i=0;i<QUESTIONS.length;i++){let cls='num';if(i==CUR)cls+=' active';if(ANSWERS[i]!=null&&String(ANSWERS[i]).length)cls+=' answered';if(SUBMITTED&&RESULTS[i])cls+=RESULTS[i].ok?' ok':' bad';html+=`<button class="${cls}" onclick="goQ(${i})">${i+1}</button>`}document.getElementById('navNums').innerHTML=html}
function goQ(i){saveCurrent();CUR=i;renderQuestion()}
function prevQ(){if(CUR>0){saveCurrent();CUR--;renderQuestion()}}
function nextQ(){if(CUR<QUESTIONS.length-1){saveCurrent();CUR++;renderQuestion()}}
function correctFor(q){return String(q.DapAn||'').match(/[ABCD]/i)?.[0]?.toUpperCase()||String(q.DapAn||'')}
function renderQuestion(){let q=QUESTIONS[CUR];renderNav();document.getElementById('qid').textContent=`Câu ${CUR+1}/${QUESTIONS.length} | ID: ${q.ID||''} | ${q.MucDo||''} - ${q.Dang}`;let img=q.HinhAnh?`<br><img class="imgQ" src="${h(q.HinhAnh)}">`:'';document.getElementById('qtext').innerHTML=br(q.CauHoi)+img;document.getElementById('solution').style.display='none';document.getElementById('solution').innerHTML='';document.getElementById('adminEdit').style.display='none';document.getElementById('adminEdit').innerHTML='';document.getElementById('btnAdminAnswer').style.display=IS_ADMIN?'inline-block':'none';document.getElementById('btnAdminEdit').style.display=IS_ADMIN?'inline-block':'none';document.getElementById('btn5050').style.display=IS_ADMIN?'none':'inline-block';document.getElementById('btnSubmit').style.display=IS_ADMIN?'none':'inline-block';document.getElementById('btn5050').disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!CAN_5050;document.getElementById('btnSubmit').disabled=SUBMITTED;let html='';if(q.Dang=='Trắc nghiệm'){let corr=IS_ADMIN?correctFor(q):'';for(let L of ['A','B','C','D']){if(!q[L])continue;let checked=ANSWERS[CUR]==L?'checked':'';let cls='opt';if(IS_ADMIN&&corr==L)cls+=' correct';if(SUBMITTED&&RESULTS[CUR]){if(CAN_VIEW&&RESULTS[CUR].correct==L)cls+=' correct';if(RESULTS[CUR].chosen==L&&(!CAN_VIEW||RESULTS[CUR].chosen!=RESULTS[CUR].correct))cls+=' wrong'}html+=`<label id="opt_${L}" class="${cls}"><input type="radio" name="ans_${CUR}" value="${L}" ${checked} ${SUBMITTED||IS_ADMIN?'disabled':''} onchange="saveCurrent()"><b>${L}.</b><span>${br(q[L])}</span></label>`}}else if(q.Dang=='Đúng sai'){let old=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:['','','',''];let corr=IS_ADMIN?String(q.DapAn||'').replace(/Đ/g,'D').match(/[DS]/g)||[]:(SUBMITTED&&RESULTS[CUR]&&CAN_VIEW?String(RESULTS[CUR].correct||'').split(','):[]);let chosen=SUBMITTED&&RESULTS[CUR]?String(RESULTS[CUR].chosen||'').split(','):old;for(let idx=0;idx<4;idx++){let L=['A','B','C','D'][idx];if(!q[L])continue;let cls='tfrow';if(IS_ADMIN&&corr[idx])cls+=' correct';else if(SUBMITTED){if(CAN_VIEW&&chosen[idx]&&chosen[idx]==corr[idx])cls+=' correct';else cls+=' wrong'}html+=`<div class="${cls}"><b>${L}.</b><div>${br(q[L])}</div><label><input type="radio" name="tf_${CUR}_${L}" value="Đ" ${old[idx]=='Đ'?'checked':''} ${SUBMITTED||IS_ADMIN?'disabled':''} onchange="saveCurrent()"> Đúng</label><label><input type="radio" name="tf_${CUR}_${L}" value="S" ${old[idx]=='S'?'checked':''} ${SUBMITTED||IS_ADMIN?'disabled':''} onchange="saveCurrent()"> Sai</label></div>`}}else if(q.Dang=='Trả lời ngắn'){let cls='';if(SUBMITTED&&RESULTS[CUR])cls=RESULTS[CUR].ok?'correct':'wrong';html=`<input id="shortAns" class="${cls}" style="width:100%;font-size:18px" placeholder="Nhập đáp án..." value="${h(ANSWERS[CUR]||'')}" ${SUBMITTED||IS_ADMIN?'disabled':''} oninput="saveCurrent()">`}else{html=`<textarea id="shortAns" style="width:100%;min-height:130px" placeholder="Nhập bài làm tự luận..." ${SUBMITTED||IS_ADMIN?'disabled':''} oninput="saveCurrent()">${h(ANSWERS[CUR]||'')}</textarea>`}document.getElementById('options').innerHTML=html;if(IS_ADMIN){adminShowAnswer(false)}else if(SUBMITTED&&RESULTS[CUR]){let r=RESULTS[CUR];document.getElementById('solution').style.display='block';if(CAN_VIEW){document.getElementById('solution').innerHTML=`<b>Đáp án:</b> ${br(r.correct||r.DapAn||'')}<br><b>Em chọn:</b> ${br(r.chosen||'')}<div class="line"></div><b>Lời giải:</b><br>${br(r.LoiGiai||'Chưa có lời giải.')}`}else{document.getElementById('solution').innerHTML=`<b>FREE:</b> Em đã nộp bài. Tài khoản FREE chỉ xem điểm, chưa xem đáp án/lời giải.`}}typeset()}
async function use5050(){saveCurrent();let j=await api('/api/fifty',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR})});for(let L of j.hide||[]){let el=document.getElementById('opt_'+L);if(el)el.classList.add('optionHidden')}document.getElementById('btn5050').disabled=true;if(j.message)alert(j.message)}
async function submitQuiz(){saveCurrent();if(!confirm('Nộp bài?'))return;let j=await api('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,answers:ANSWERS})});SUBMITTED=true;CAN_VIEW=!!j.can_view_solution;RESULTS={};for(let r of j.results)RESULTS[r.index]=r;document.getElementById('resultBox').textContent=`Điểm: ${j.score}/10 | Đúng ${j.correct_count}/${j.auto_count}`;renderQuestion();renderNav()}
function adminShowAnswer(alertMissing=true){if(!IS_ADMIN)return;let q=QUESTIONS[CUR];document.getElementById('solution').style.display='block';document.getElementById('solution').innerHTML=`<b>ADMIN - Đáp án:</b> ${br(q.DapAn||'Chưa có đáp án')}<br><b>Sai số:</b> ${br(q.SaiSo||'')}<div class="line"></div><b>Lời giải:</b><br>${br(q.LoiGiai||'Chưa có lời giải.')}`;typeset()}
function adminOpenEdit(){if(!IS_ADMIN)return;let q=QUESTIONS[CUR];let box=document.getElementById('adminEdit');box.style.display='block';box.innerHTML=`<h3>ADMIN: Sửa câu ${CUR+1} - ID ${h(q.ID)}</h3><label>Nội dung câu hỏi</label><textarea id="ed_CauHoi">${h(q.CauHoi)}</textarea><div class="row"><div class="field"><label>A</label><textarea id="ed_A">${h(q.A)}</textarea></div><div class="field"><label>B</label><textarea id="ed_B">${h(q.B)}</textarea></div></div><div class="row"><div class="field"><label>C</label><textarea id="ed_C">${h(q.C)}</textarea></div><div class="field"><label>D</label><textarea id="ed_D">${h(q.D)}</textarea></div></div><div class="row"><div class="field"><label>Đáp án</label><input id="ed_DapAn" value="${h(q.DapAn)}"></div><div class="field"><label>Sai số</label><input id="ed_SaiSo" value="${h(q.SaiSo)}"></div><div class="field"><label>Mức độ</label><input id="ed_MucDo" value="${h(q.MucDo)}"></div><div class="field"><label>Dạng</label><input id="ed_Dang" value="${h(q.Dang)}"></div></div><label>Lời giải</label><textarea id="ed_LoiGiai" style="min-height:120px">${h(q.LoiGiai)}</textarea><div class="row" style="margin-top:10px"><button class="btnRed" onclick="adminSaveEdit()">Lưu sửa vào Google Sheet</button><button onclick="document.getElementById('adminEdit').style.display='none'">Đóng</button></div>`}
async function adminSaveEdit(){let q=QUESTIONS[CUR];let fields={CauHoi:val('ed_CauHoi'),A:val('ed_A'),B:val('ed_B'),C:val('ed_C'),D:val('ed_D'),DapAn:val('ed_DapAn'),SaiSo:val('ed_SaiSo'),MucDo:val('ed_MucDo'),Dang:val('ed_Dang'),LoiGiai:val('ed_LoiGiai')};let j=await api('/admin/update_question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ID:q.ID,fields})});Object.assign(q,fields);alert(j.message||'Đã lưu.');renderQuestion()}
async function adminSync(){let j=await api('/admin/sync',{method:'POST'});alert(j.message);location.reload()}
init().catch(e=>{document.body.innerHTML='<pre style="padding:20px;color:red">'+h(e.message)+'</pre>'})
</script>
</body></html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route("/version")
def version():
    return jsonify({
        "version": APP_VERSION,
        "login_required": True,
        "admin_can_view_without_submit": True,
        "admin_can_edit_question": True,
        "sheet_connected": SHEET.connected,
        "sheet_error": SHEET.error,
        "users": len(STORE.users),
        "questions": len(STORE.questions),
    })

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = request.args.get("msg", "")
    if request.method == "POST":
        mahs = clean(request.form.get("mahs"))
        password = clean(request.form.get("password"))
        user = STORE.users.get(mahs)
        if not user:
            return render_template_string(LOGIN_HTML, msg="Không tìm thấy mã học sinh.")
        if clean(user.get("password")) != password:
            return render_template_string(LOGIN_HTML, msg="Sai mật khẩu.")
        if user.get("status", "ON").upper() not in ["ON", "ACTIVE", "VIP", "S.VIP", "ADMIN"]:
            return render_template_string(LOGIN_HTML, msg="Tài khoản đang bị khóa hoặc hết hạn.")
        token = stable_hash(f"{mahs}|{time.time()}|{random.random()}", 24)
        session.clear()
        session["mahs"] = mahs
        session["session_token"] = token
        update_session_token(mahs, token)
        return redirect(url_for("index"))
    return render_template_string(LOGIN_HTML, msg=msg)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login", msg="Đã thoát tài khoản."))

@app.route("/")
def index():
    r = ensure_login_response()
    if r:
        return r
    return render_template_string(INDEX_HTML, user=current_user(), can5050=can_use_5050())

@app.route("/api/meta")
def api_meta():
    r = ensure_login_response()
    if r:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    return jsonify(STORE.meta())

@app.route("/api/start")
def api_start():
    r = ensure_login_response()
    if r:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    made = request.args.get("made", "")
    return jsonify(STORE.start_quiz(made))

@app.route("/api/fifty", methods=["POST"])
def api_fifty():
    r = ensure_login_response()
    if r:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    if not can_use_5050():
        return jsonify({"error": "Chỉ VIP/S.VIP/ADMIN được dùng Loại 2 câu sai."}), 403
    data = request.get_json(silent=True) or {}
    return jsonify(STORE.fifty_fifty(data.get("sid", ""), int(data.get("index", 0))))

@app.route("/api/submit", methods=["POST"])
def api_submit():
    r = ensure_login_response()
    if r:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    data = request.get_json(silent=True) or {}
    return jsonify(STORE.submit(data.get("sid", ""), data.get("answers", {})))

@app.route("/admin/sync", methods=["POST"])
def admin_sync():
    r = ensure_login_response()
    if r:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được đồng bộ."}), 403
    STORE.sync()
    return jsonify({"ok": True, "message": f"Đã đồng bộ: {len(STORE.questions)} câu, {len(STORE.catalog)} đề, {len(STORE.users)} tài khoản."})

@app.route("/admin/question")
def admin_question():
    r = ensure_login_response()
    if r:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được xem đầy đủ câu hỏi."}), 403
    qid = request.args.get("id", "")
    return jsonify({"question": STORE.public_question(STORE.question_by_id(qid), 0, include_secret=True)})

@app.route("/admin/update_question", methods=["POST"])
def admin_update_question():
    r = ensure_login_response()
    if r:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được sửa câu hỏi."}), 403
    data = request.get_json(silent=True) or {}
    qid = clean(data.get("ID"))
    fields = data.get("fields", {}) or {}
    result = STORE.update_question(qid, fields)
    return jsonify({"ok": True, "message": f"Đã lưu sửa câu {qid} ở dòng {result.get('row')} trên Google Sheet.", "result": result})

@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({"error": str(e), "version": APP_VERSION}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
