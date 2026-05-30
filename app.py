# -*- coding: utf-8 -*-
"""
app.py - Ứng dụng luyện đề JSON + đăng nhập học viên + công cụ chuyển XLSX Google Sheets sang JSON.

Dùng trên Render:
    Start Command: gunicorn app:app --bind 0.0.0.0:$PORT

Dùng ở máy thầy:
    python app.py --convert "Luyện Đề Vật Lý.xlsx" --json luyen_de_vat_ly.json --users users.json
    python app.py --check --json luyen_de_vat_ly.json --users users.json
    python app.py --serve --json luyen_de_vat_ly.json --users users.json

File cần có khi đưa lên Render:
    app.py
    luyen_de_vat_ly.json
    users.json
    requirements.txt

Đăng nhập lấy từ sheet HOC_VIEN:
    Tên đăng nhập: MaHS
    Mật khẩu: MatKhau
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import random
import re
import tempfile
import time
import unicodedata
import webbrowser
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    from flask import Flask, Response, jsonify, redirect, render_template_string, request, send_file, session, url_for
    HAS_FLASK = True
except ModuleNotFoundError:
    Flask = Response = jsonify = redirect = render_template_string = request = send_file = session = url_for = None
    HAS_FLASK = False

# ============================================================
# 1) ĐỌC NHANH XLSX - KHÔNG CẦN PANDAS, KHÔNG CẦN OPENPYXL
# ============================================================

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


@dataclass
class SheetInfo:
    name: str
    xml_path: str
    state: str = "visible"


def cell_to_col_index(cell_ref: str) -> int:
    m = re.match(r"([A-Z]+)", cell_ref or "")
    if not m:
        return 0
    n = 0
    for ch in m.group(1):
        n = n * 26 + ord(ch) - 64
    return n


def text_from_si(si: ET.Element) -> str:
    parts: List[str] = []
    for node in si.iter():
        if node.tag.endswith("}t") and node.text:
            parts.append(node.text)
    return "".join(parts)


def normalize_headers(headers: List[str]) -> List[str]:
    out: List[str] = []
    used: Dict[str, int] = {}
    for i, h in enumerate(headers, start=1):
        h = str(h or "").strip()
        if not h:
            h = f"COL_{i}"
        if h in used:
            used[h] += 1
            h = f"{h}_{used[h]}"
        else:
            used[h] = 1
        out.append(h)
    return out


class FastXlsxReader:
    def __init__(self, xlsx_path: str | os.PathLike[str]):
        self.path = Path(xlsx_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Không thấy file: {self.path}")
        self.zf = zipfile.ZipFile(self.path)
        self.shared_strings = self._load_shared_strings()
        self.sheets = self._load_sheets()

    def close(self) -> None:
        self.zf.close()

    def __enter__(self) -> "FastXlsxReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _load_shared_strings(self) -> List[str]:
        if "xl/sharedStrings.xml" not in self.zf.namelist():
            return []
        strings: List[str] = []
        with self.zf.open("xl/sharedStrings.xml") as f:
            for _, elem in ET.iterparse(f, events=("end",)):
                if elem.tag.endswith("}si"):
                    strings.append(text_from_si(elem))
                    elem.clear()
        return strings

    def _load_sheets(self) -> Dict[str, SheetInfo]:
        workbook_xml = ET.fromstring(self.zf.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(self.zf.read("xl/_rels/workbook.xml.rels"))
        rid_to_target: Dict[str, str] = {}
        for rel in rels_xml:
            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target", "")
            if rid:
                if not target.startswith("xl/"):
                    target = "xl/" + target.lstrip("/")
                rid_to_target[rid] = target
        result: Dict[str, SheetInfo] = {}
        sheets_node = workbook_xml.find(NS_MAIN + "sheets")
        if sheets_node is None:
            return result
        for sh in sheets_node:
            name = sh.attrib.get("name", "Sheet")
            state = sh.attrib.get("state", "visible")
            rid = sh.attrib.get(NS_REL + "id")
            xml_path = rid_to_target.get(rid or "", "")
            if xml_path:
                result[name] = SheetInfo(name=name, xml_path=xml_path, state=state)
        return result

    def sheet_names(self) -> List[str]:
        return list(self.sheets.keys())

    def _cell_value(self, cell: ET.Element) -> str:
        t = cell.attrib.get("t")
        if t == "s":
            v = cell.find(NS_MAIN + "v")
            if v is None or v.text is None:
                return ""
            try:
                idx = int(v.text)
                return self.shared_strings[idx] if 0 <= idx < len(self.shared_strings) else ""
            except Exception:
                return ""
        if t == "inlineStr":
            parts: List[str] = []
            for node in cell.iter():
                if node.tag.endswith("}t") and node.text:
                    parts.append(node.text)
            return "".join(parts)
        v = cell.find(NS_MAIN + "v")
        return v.text if v is not None and v.text is not None else ""

    def iter_rows(self, sheet_name: str) -> Iterator[List[str]]:
        if sheet_name not in self.sheets:
            raise KeyError(f"Không có sheet {sheet_name!r}. Có: {', '.join(self.sheet_names())}")
        with self.zf.open(self.sheets[sheet_name].xml_path) as f:
            for _, elem in ET.iterparse(f, events=("end",)):
                if elem.tag.endswith("}row"):
                    values: Dict[int, str] = {}
                    max_col = 0
                    for cell in elem:
                        if not cell.tag.endswith("}c"):
                            continue
                        col = cell_to_col_index(cell.attrib.get("r", ""))
                        if col <= 0:
                            continue
                        values[col] = self._cell_value(cell)
                        max_col = max(max_col, col)
                    row = [values.get(i, "") for i in range(1, max_col + 1)]
                    elem.clear()
                    yield row

    def iter_dicts(self, sheet_name: str) -> Iterator[Dict[str, str]]:
        it = self.iter_rows(sheet_name)
        try:
            headers = normalize_headers(next(it))
        except StopIteration:
            return
        for row in it:
            if len(row) < len(headers):
                row += [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                headers = headers + [f"COL_{i}" for i in range(len(headers) + 1, len(row) + 1)]
            yield dict(zip(headers, row))

# ============================================================
# 2) CHUẨN HÓA DỮ LIỆU
# ============================================================

QUESTION_ALIASES: Dict[str, List[str]] = {
    "MaDe": ["MaDe", "Mã đề", "Ma De", "MA_DE", "ma_de"],
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
    "QuyenTruyCap": ["QuyenTruyCap", "Quyền truy cập", "Quyen", "Goi"],
    "SoCau": ["SoCau", "Số câu", "Số Câu"],
}
QUESTION_FIELDS = list(QUESTION_ALIASES.keys())

USER_ALIASES: Dict[str, List[str]] = {
    "MaHS": ["MaHS", "Mã HS", "Mã học sinh", "Username", "TaiKhoan", "Tài khoản"],
    "MatKhau": ["MatKhau", "Mật khẩu", "Password"],
    "HoTen": ["HoTen", "Họ tên", "Họ Tên", "TenHS", "Tên HS"],
    "LopHoc": ["LopHoc", "Lớp học", "Lớp"],
    "LoaiTaiKhoan": ["LoaiTaiKhoan", "Loại tài khoản", "Quyen", "Quyền", "Goi"],
    "TrangThai": ["TrangThai", "Trạng thái", "Status"],
    "SoDienThoai": ["SoDienThoai", "Số điện thoại", "SDT", "Điện thoại"],
    "NgayDangKy": ["NgayDangKy", "Ngày đăng ký"],
    "NgayHetHanTrial": ["NgayHetHanTrial", "Ngày hết hạn trial"],
    "DeviceId": ["DeviceId", "Device ID", "Thiết bị"],
    "NgayHetHanTaiKhoan": ["NgayHetHanTaiKhoan", "Ngày hết hạn tài khoản", "Hết hạn"],
}
USER_FIELDS = list(USER_ALIASES.keys())


def strip_accents(s: str) -> str:
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def key_norm(s: Any) -> str:
    s = strip_accents(str(s or "").strip().lower())
    return re.sub(r"\s+", " ", s)


def clean_value(v: Any) -> str:
    s = str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def excel_serial_to_datetime_text(s: str) -> str:
    s = clean_value(s)
    if not s:
        return ""
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        try:
            n = float(s)
            if 20000 <= n <= 80000:
                dt = datetime(1899, 12, 30) + timedelta(days=n)
                return dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            pass
    return s


def parse_date_guess(s: str) -> Optional[datetime]:
    s = excel_serial_to_datetime_text(s)
    if not s:
        return None
    fmts = ["%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def get_any(row: Dict[str, Any], names: List[str]) -> str:
    direct = {key_norm(k): k for k in row.keys()}
    for name in names:
        k = direct.get(key_norm(name))
        if k is not None:
            return clean_value(row.get(k, ""))
    return ""


def canonical_question(row: Dict[str, Any]) -> Dict[str, str]:
    return {f: get_any(row, QUESTION_ALIASES[f]) for f in QUESTION_FIELDS}


def canonical_user(row: Dict[str, Any]) -> Dict[str, str]:
    u = {f: get_any(row, USER_ALIASES[f]) for f in USER_FIELDS}
    for f in ["NgayDangKy", "NgayHetHanTrial", "NgayHetHanTaiKhoan"]:
        u[f] = excel_serial_to_datetime_text(u.get(f, ""))
    u["LoaiTaiKhoan"] = (u.get("LoaiTaiKhoan") or "FREE").upper().replace(" ", "")
    u["TrangThai"] = (u.get("TrangThai") or "ON").upper().strip()
    return u


def stable_hash(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n].upper()


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
    made = clean_value(q.get("MaDe", ""))
    if made:
        return made
    parts = [q.get("Lop", ""), q.get("Mon", ""), q.get("Chuong", ""), q.get("BaiHoc", ""), q.get("DangBaiTap", ""), q.get("BoDe", ""), q.get("De", "")]
    return "MD_" + stable_hash("|".join(key_norm(x) for x in parts), 10)


def build_catalog(questions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for q in questions:
        made = q.get("MaDe") or make_made(q)
        q["MaDe"] = made
        g = groups.setdefault(made, {
            "MaDe": made, "Lop": q.get("Lop", ""), "Mon": q.get("Mon", ""), "Chuong": q.get("Chuong", ""),
            "BaiHoc": q.get("BaiHoc", ""), "DangBaiTap": q.get("DangBaiTap", ""), "BoDe": q.get("BoDe", ""),
            "De": q.get("De", ""), "SoCau": 0, "MucDo": set(), "Dang": set(), "QuyenTruyCap": set()
        })
        g["SoCau"] += 1
        if q.get("MucDo"):
            g["MucDo"].add(q.get("MucDo"))
        if q.get("Dang"):
            g["Dang"].add(q.get("Dang"))
        if q.get("QuyenTruyCap"):
            g["QuyenTruyCap"].add(q.get("QuyenTruyCap"))
    out: List[Dict[str, Any]] = []
    for g in groups.values():
        item = dict(g)
        item["MucDo"] = ", ".join(sorted(g["MucDo"]))
        item["Dang"] = ", ".join(sorted(g["Dang"]))
        item["QuyenTruyCap"] = ", ".join(sorted(g["QuyenTruyCap"]))
        out.append(item)
    out.sort(key=lambda x: (key_norm(x.get("Mon")), key_norm(x.get("Lop")), key_norm(x.get("Chuong")), key_norm(x.get("BaiHoc")), key_norm(x.get("De"))))
    return out


def convert_xlsx_to_json_files(xlsx_path: str, data_json_path: str = "luyen_de_vat_ly.json", users_json_path: str = "users.json") -> Dict[str, Any]:
    t0 = time.time()
    xlsx = Path(xlsx_path)
    if not xlsx.exists():
        raise FileNotFoundError(f"Không thấy file Excel: {xlsx}")

    with FastXlsxReader(xlsx) as reader:
        sheets = reader.sheet_names()
        if "Cau_Hoi" not in sheets:
            raise RuntimeError("File chưa có sheet Cau_Hoi")

        questions: List[Dict[str, str]] = []
        for row in reader.iter_dicts("Cau_Hoi"):
            q = canonical_question(row)
            if not clean_value(q.get("CauHoi", "")):
                continue
            q["Dang"] = normalize_dang(q.get("Dang", ""))
            q["MaDe"] = make_made(q)
            if not q.get("ID"):
                q["ID"] = "AUTO_" + stable_hash(json.dumps(q, ensure_ascii=False), 10)
            questions.append(q)

        users: List[Dict[str, str]] = []
        if "HOC_VIEN" in sheets:
            for row in reader.iter_dicts("HOC_VIEN"):
                u = canonical_user(row)
                if not clean_value(u.get("MaHS", "")):
                    continue
                if not clean_value(u.get("MatKhau", "")):
                    # Nếu chưa có mật khẩu thì tạm lấy 6 số cuối SĐT.
                    phone = re.sub(r"\D", "", u.get("SoDienThoai", ""))
                    u["MatKhau"] = phone[-6:] if len(phone) >= 6 else "123456"
                users.append(u)

        sheet_stats: Dict[str, Dict[str, int]] = {}
        for s in sheets:
            rows = 0
            max_col = 0
            for row in reader.iter_rows(s):
                rows += 1
                max_col = max(max_col, len(row))
            sheet_stats[s] = {"rows": rows, "cols": max_col}

    data = {
        "version": "quiz-json-2.0",
        "meta": {
            "source_file": xlsx.name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "convert_seconds": round(time.time() - t0, 3),
        },
        "sheet_stats": sheet_stats,
        "questions": questions,
        "catalog_rows": build_catalog(questions),
    }
    users_data = {
        "version": "users-json-2.0",
        "meta": {
            "source_file": xlsx.name,
            "source_sheet": "HOC_VIEN",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "users": users,
    }
    Path(data_json_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(users_json_path).write_text(json.dumps(users_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"data": data, "users_data": users_data}


def check_json_files(data_json_path: str = "luyen_de_vat_ly.json", users_json_path: str = "users.json") -> str:
    data = json.loads(Path(data_json_path).read_text(encoding="utf-8"))
    users_data = json.loads(Path(users_json_path).read_text(encoding="utf-8")) if Path(users_json_path).exists() else {"users": []}
    questions = data.get("questions", [])
    catalog = build_catalog(questions)
    users = users_data.get("users", [])
    missing_answer = [q for q in questions if normalize_dang(q.get("Dang", "")) != "Tự luận" and not clean_value(q.get("DapAn", ""))]
    missing_content = [q for q in questions if not clean_value(q.get("CauHoi", ""))]
    bad_users = [u for u in users if not clean_value(u.get("MaHS", "")) or not clean_value(u.get("MatKhau", ""))]
    lines = []
    lines.append("BÁO CÁO KIỂM TRA JSON")
    lines.append("=" * 40)
    lines.append(f"File đề: {data_json_path}")
    lines.append(f"File users: {users_json_path}")
    lines.append(f"Số câu hỏi: {len(questions)}")
    lines.append(f"Số đề/thẻ đề: {len(catalog)}")
    lines.append(f"Số tài khoản HOC_VIEN: {len(users)}")
    lines.append(f"Câu thiếu nội dung: {len(missing_content)}")
    lines.append(f"Câu thiếu đáp án, trừ tự luận: {len(missing_answer)}")
    lines.append(f"Tài khoản thiếu MaHS/MatKhau: {len(bad_users)}")
    lines.append("")
    lines.append("Thống kê sheet:")
    for name, st in data.get("sheet_stats", {}).items():
        lines.append(f"- {name}: {st.get('rows', 0)} dòng x {st.get('cols', 0)} cột")
    if missing_answer[:10]:
        lines.append("")
        lines.append("10 câu đầu thiếu đáp án:")
        for q in missing_answer[:10]:
            lines.append(f"- {q.get('ID')} | {q.get('Mon')} | {q.get('Lop')} | {q.get('CauHoi','')[:80]}")
    return "\n".join(lines)

# ============================================================
# 3) FLASK APP - ĐĂNG NHẬP + LÀM BÀI
# ============================================================

if HAS_FLASK:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "doi-mat-khau-secret-key-2026")

    DATA_JSON = os.environ.get("QUIZ_JSON", "luyen_de_vat_ly.json")
    USERS_JSON = os.environ.get("USERS_JSON", "users.json")


    def load_json_file(path: str, default: Any) -> Any:
        p = Path(path)
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))


    def load_data() -> Dict[str, Any]:
        return load_json_file(DATA_JSON, {"questions": [], "catalog_rows": [], "meta": {}})


    def load_users() -> List[Dict[str, str]]:
        data = load_json_file(USERS_JSON, {"users": []})
        if isinstance(data, list):
            return data
        return data.get("users", [])


    def current_user() -> Optional[Dict[str, str]]:
        ma = session.get("MaHS")
        if not ma:
            return None
        for u in load_users():
            if key_norm(u.get("MaHS")) == key_norm(ma):
                return u
        return None


    def role_of(u: Optional[Dict[str, str]]) -> str:
        if not u:
            return "GUEST"
        return (u.get("LoaiTaiKhoan") or "FREE").upper().replace(" ", "")


    def is_admin(u: Optional[Dict[str, str]]) -> bool:
        return role_of(u) == "ADMIN" or key_norm(u.get("MaHS", "") if u else "") == "admin"


    def is_active_user(u: Dict[str, str]) -> Tuple[bool, str]:
        if (u.get("TrangThai") or "ON").upper() not in ["ON", "ACTIVE", "1", "TRUE"]:
            return False, "Tài khoản đang OFF hoặc bị khóa."
        role = role_of(u)
        if role in ["ADMIN", "S.VIP", "SVIP"]:
            return True, ""
        # Nếu có ngày hết hạn tài khoản thì kiểm tra.
        exp = parse_date_guess(u.get("NgayHetHanTaiKhoan", ""))
        if exp and datetime.now() > exp:
            # Trial có thể vẫn còn hạn.
            trial = parse_date_guess(u.get("NgayHetHanTrial", ""))
            if not trial or datetime.now() > trial:
                return False, "Tài khoản đã hết hạn."
        return True, ""


    def can_use_5050(u: Optional[Dict[str, str]]) -> bool:
        return role_of(u) in ["VIP", "S.VIP", "SVIP", "ADMIN", "PAID"]


    def can_view_solution(u: Optional[Dict[str, str]]) -> bool:
        return role_of(u) in ["VIP", "S.VIP", "SVIP", "ADMIN", "PAID"]


    def norm_letter(s: str) -> str:
        s = clean_value(s).upper()
        m = re.search(r"[ABCD]", s)
        return m.group(0) if m else ""


    def norm_tf_answer(s: str) -> List[str]:
        s = strip_accents(clean_value(s).upper())
        s = s.replace("DUNG", "D").replace("TRUE", "D").replace("SAI", "S").replace("FALSE", "S")
        vals = re.findall(r"[DS]", s)
        return vals[:4]


    def parse_float_vn(s: str) -> Optional[float]:
        s = clean_value(s)
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


    def check_answer(q: Dict[str, str], user_answer: Any) -> Tuple[bool, str, str]:
        dang = normalize_dang(q.get("Dang", ""))
        correct_raw = clean_value(q.get("DapAn", ""))
        if dang == "Trắc nghiệm":
            correct = norm_letter(correct_raw)
            chosen = norm_letter(str(user_answer or ""))
            return bool(correct and chosen and correct == chosen), correct, chosen
        if dang == "Đúng sai":
            correct_list = norm_tf_answer(correct_raw)
            corr = ["Đ" if x == "D" else "S" for x in correct_list]
            if isinstance(user_answer, list):
                chosen = ["Đ" if key_norm(x) in ["d", "dung", "đ", "đúng"] else "S" if key_norm(x) in ["s", "sai"] else "" for x in user_answer]
            else:
                chosen = ["Đ" if x == "D" else "S" for x in norm_tf_answer(str(user_answer or ""))]
            while len(chosen) < 4:
                chosen.append("")
            ok = len(corr) == 4 and chosen[:4] == corr[:4]
            return ok, ",".join(corr), ",".join(chosen[:4])
        if dang == "Trả lời ngắn":
            c = parse_float_vn(correct_raw)
            a = parse_float_vn(str(user_answer or ""))
            tol = parse_float_vn(q.get("SaiSo", "")) or 0.0
            if c is not None and a is not None:
                return abs(a - c) <= tol + 1e-12, correct_raw, str(user_answer or "")
            return key_norm(correct_raw) == key_norm(str(user_answer or "")), correct_raw, str(user_answer or "")
        return False, correct_raw, str(user_answer or "")


    def quiz_meta() -> Dict[str, Any]:
        data = load_data()
        questions = data.get("questions", [])
        catalog = build_catalog(questions)
        def opts(field: str) -> List[str]:
            return sorted({clean_value(x.get(field, "")) for x in catalog if clean_value(x.get(field, ""))}, key=key_norm)
        return {
            "meta": data.get("meta", {}),
            "count_questions": len(questions),
            "count_catalog": len(catalog),
            "filters": {"Mon": opts("Mon"), "Lop": opts("Lop"), "Chuong": opts("Chuong"), "BaiHoc": opts("BaiHoc"), "DangBaiTap": opts("DangBaiTap"), "BoDe": opts("BoDe")},
            "catalog": catalog,
        }


    LOGIN_HTML = r"""
    <!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Đăng nhập luyện đề</title>
    <style>
    body{font-family:Arial,sans-serif;background:#f1f5f9;margin:0}.box{max-width:420px;margin:9vh auto;background:white;border-radius:16px;padding:24px;box-shadow:0 10px 25px #0001}.brand{background:#1d4ed8;color:white;padding:14px 20px;border-radius:12px;margin-bottom:16px}input,button{width:100%;box-sizing:border-box;padding:12px;margin:8px 0;border:1px solid #cbd5e1;border-radius:10px;font-size:16px}button{background:#1d4ed8;color:white;font-weight:bold;border:none}.err{background:#fee2e2;color:#991b1b;padding:10px;border-radius:10px}.hint{font-size:13px;color:#475569;line-height:1.5}
    </style></head><body><div class="box"><div class="brand"><b>ỨNG DỤNG LUYỆN ĐỀ</b><br>Đăng nhập bằng tài khoản trong sheet HOC_VIEN</div>
    {% if error %}<div class="err">{{error}}</div>{% endif %}
    <form method="post"><label>Mã học sinh / MaHS</label><input name="mahs" placeholder="VD: HS001 hoặc ADMIN" autofocus required>
    <label>Mật khẩu / MatKhau</label><input name="matkhau" type="password" placeholder="Nhập mật khẩu" required>
    <button>Đăng nhập</button></form>
    <div class="hint">Tài khoản lấy từ sheet <b>HOC_VIEN</b>: cột <b>MaHS</b> và <b>MatKhau</b>. ADMIN sẽ thấy thêm công cụ chuyển Excel sang JSON.</div></div></body></html>
    """

    APP_HTML = r"""
    <!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Luyện đề</title>
    <script>window.MathJax={tex:{inlineMath:[["$","$"],["\\(","\\)"]]},svg:{fontCache:"global"}};</script>
    <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
    <style>
    :root{--blue:#1d4ed8;--bg:#f1f5f9;--border:#dbe4ef;--green:#dcfce7;--red:#fee2e2;--yellow:#fef3c7}*{box-sizing:border-box}body{font-family:Arial,sans-serif;background:var(--bg);margin:0;color:#0f172a}.top{background:var(--blue);color:white;padding:12px 16px;display:flex;justify-content:space-between;gap:10px;align-items:center}.top a{color:white}.wrap{padding:12px}.card{background:white;border:1px solid var(--border);border-radius:14px;padding:12px;margin-bottom:12px;box-shadow:0 2px 8px #0000000b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}.deck{border:1px solid var(--border);border-radius:12px;padding:12px;background:#fff}.tag{display:inline-block;padding:4px 8px;background:#e0f2fe;border-radius:999px;margin:2px;font-size:12px}.btn{border:none;background:var(--blue);color:white;padding:9px 12px;border-radius:10px;cursor:pointer;font-weight:600}.btn.gray{background:#64748b}.btn.green{background:#16a34a}.btn.red{background:#dc2626}.btn.light{background:#e2e8f0;color:#0f172a}.filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px}select,input{width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:9px}.quiz{display:grid;grid-template-columns:minmax(0,1fr) 210px;gap:12px}.qnav{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.qbtn{padding:8px;border:1px solid #cbd5e1;border-radius:8px;background:white}.qbtn.active{outline:3px solid #93c5fd}.qbtn.ok{background:var(--green)}.qbtn.bad{background:var(--red)}.choice{display:block;border:1px solid #cbd5e1;border-radius:10px;padding:10px;margin:8px 0;background:white}.choice.hidden{opacity:.25;text-decoration:line-through}.choice.correct{background:var(--green);border-color:#22c55e}.choice.wrong{background:var(--red);border-color:#ef4444}.questionbox{min-height:120px;border:1px solid #334155;border-radius:8px;padding:12px;background:white}.solution{background:#fff7ed;border:1px solid #fdba74;border-radius:10px;padding:10px;margin-top:10px}.muted{color:#64748b}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}@media(max-width:850px){.quiz{grid-template-columns:1fr}.side{order:-1}.qnav{grid-template-columns:repeat(8,1fr)}}
    </style></head><body>
    <div class="top"><div><b>ỨNG DỤNG LUYỆN ĐỀ</b> <span class="muted" style="color:#dbeafe">JSON + MathJax</span></div><div>👤 {{u.HoTen}} | {{u.MaHS}} | {{u.LoaiTaiKhoan}} &nbsp; <a href="/logout">Thoát</a></div></div>
    <div class="wrap">
    <div class="card row"><button class="btn" onclick="showCatalog()">Mục lục đề</button>{% if admin %}<a class="btn green" style="text-decoration:none" href="/admin/convert">Chuyển Excel sang JSON</a><a class="btn gray" style="text-decoration:none" href="/admin/check">Kiểm tra JSON</a>{% endif %}<span id="info" class="muted"></span></div>
    <div id="catalogView" class="card"><h3>Mục lục đề</h3><div class="filters"><select id="fMon"><option value="">Tất cả môn</option></select><select id="fLop"><option value="">Tất cả lớp</option></select><select id="fChuong"><option value="">Tất cả chương</option></select><select id="fBaiHoc"><option value="">Tất cả bài học</option></select><select id="fBoDe"><option value="">Tất cả bộ đề</option></select><input id="kw" placeholder="Tìm đề, chương, bài học..."></div><p></p><div id="decks" class="grid"></div></div>
    <div id="quizView" style="display:none"><div class="quiz"><div class="card"><div class="row" style="justify-content:space-between"><h3 id="qtitle"></h3><div class="row"><button class="btn light" onclick="fifty()">Loại 2 câu sai</button><button class="btn green" onclick="submitQuiz()">Nộp bài</button></div></div><div id="question"></div><div id="choices"></div><div class="row"><button class="btn gray" onclick="prevQ()">← Câu trước</button><button class="btn" onclick="nextQ()">Câu sau →</button></div><div id="solution"></div></div><div class="card side"><b>Bảng câu hỏi</b><div id="qnav" class="qnav" style="margin-top:10px"></div><hr><div id="score"></div></div></div></div>
    </div>
    <script>
    let META=null, CATALOG=[], QUIZ=null, IDX=0, ANSWERS={}, RESULT=null, HIDDEN={};
    async function api(url, data){let opt=data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{};let r=await fetch(url,opt); if(r.status===401){location='/login'; return null;} return await r.json();}
    function optionFill(sel, arr, first){sel.innerHTML='<option value="">'+first+'</option>'+arr.map(x=>`<option>${esc(x)}</option>`).join('')}
    function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
    async function loadMeta(){META=await api('/api/meta'); if(!META)return; CATALOG=META.catalog||[]; info.textContent=`Số câu: ${META.count_questions} | Số đề: ${META.count_catalog}`; optionFill(fMon,META.filters.Mon,'Tất cả môn'); optionFill(fLop,META.filters.Lop,'Tất cả lớp'); optionFill(fChuong,META.filters.Chuong,'Tất cả chương'); optionFill(fBaiHoc,META.filters.BaiHoc,'Tất cả bài học'); optionFill(fBoDe,META.filters.BoDe,'Tất cả bộ đề'); renderCatalog();}
    [fMon,fLop,fChuong,fBaiHoc,fBoDe,kw].forEach(e=>e.addEventListener('input',renderCatalog));
    function match(c){let k=kw.value.toLowerCase(); return (!fMon.value||c.Mon===fMon.value)&&(!fLop.value||c.Lop===fLop.value)&&(!fChuong.value||c.Chuong===fChuong.value)&&(!fBaiHoc.value||c.BaiHoc===fBaiHoc.value)&&(!fBoDe.value||c.BoDe===fBoDe.value)&&(!k||JSON.stringify(c).toLowerCase().includes(k));}
    function renderCatalog(){let arr=CATALOG.filter(match); decks.innerHTML=arr.map(c=>`<div class="deck"><b>${esc(c.De||'Đề')}</b><br><span class="tag">${esc(c.Mon)}</span><span class="tag">Lớp ${esc(c.Lop)}</span><span class="tag">${esc(c.SoCau)} câu</span><p><b>Chương:</b> ${esc(c.Chuong||'')}</p><p><b>Bài:</b> ${esc(c.BaiHoc||'')}</p><p><b>Dạng:</b> ${esc(c.DangBaiTap||c.Dang||'')}</p><button class="btn" onclick="startQuiz('${c.MaDe}')">Làm bài</button></div>`).join('')||'<p>Không có đề phù hợp.</p>';}
    async function startQuiz(made){RESULT=null; ANSWERS={}; HIDDEN={}; IDX=0; QUIZ=await api('/api/start',{MaDe:made}); if(!QUIZ||QUIZ.error){alert(QUIZ?.error||'Lỗi');return;} catalogView.style.display='none'; quizView.style.display='block'; renderQuiz();}
    function showCatalog(){quizView.style.display='none'; catalogView.style.display='block';}
    function renderQuiz(){if(!QUIZ)return; let q=QUIZ.questions[IDX]; qtitle.textContent=`Câu ${IDX+1}/${QUIZ.questions.length} | ID: ${q.ID} | ${q.MucDo} - ${q.Dang}`; question.innerHTML=`<div class="questionbox">${q.CauHoi||''}${q.HinhAnh?'<p><img src="'+esc(q.HinhAnh)+'" style="max-width:100%"></p>':''}</div>`; renderChoices(q); renderNav(); renderResult(q); MathJax.typesetPromise();}
    function renderChoices(q){let dang=q.Dang||'Trắc nghiệm'; let html=''; if(dang.includes('Trắc nghiệm')){['A','B','C','D'].forEach(L=>{let cls='choice'; if(HIDDEN[q.ID]?.includes(L))cls+=' hidden'; if(RESULT){let r=RESULT.details[IDX]; if(r.correct_answer===L)cls+=' correct'; if(r.user_answer===L && !r.is_correct)cls+=' wrong';} html+=`<label class="${cls}"><input type="radio" name="ans" value="${L}" ${ANSWERS[q.ID]===L?'checked':''} onchange="ANSWERS['${q.ID}']='${L}'"> <b>${L}.</b> ${q[L]||''}</label>`})} else if(dang.includes('Đúng sai')){let arr=ANSWERS[q.ID]||['','','','']; ['A','B','C','D'].forEach((L,i)=>{html+=`<div class="choice"><b>${L}.</b> ${q[L]||''}<div><label><input type="radio" name="tf${i}" onchange="setTF('${q.ID}',${i},'Đ')" ${arr[i]==='Đ'?'checked':''}> Đúng</label> <label><input type="radio" name="tf${i}" onchange="setTF('${q.ID}',${i},'S')" ${arr[i]==='S'?'checked':''}> Sai</label></div></div>`})} else {html=`<textarea style="width:100%;min-height:80px;border:1px solid #cbd5e1;border-radius:10px;padding:10px" oninput="ANSWERS['${q.ID}']=this.value">${esc(ANSWERS[q.ID]||'')}</textarea>`} choices.innerHTML=html;}
    function setTF(id,i,v){let arr=ANSWERS[id]||['','','','']; arr[i]=v; ANSWERS[id]=arr;}
    function renderNav(){qnav.innerHTML=QUIZ.questions.map((q,i)=>{let cls='qbtn'+(i===IDX?' active':''); if(RESULT){cls+=RESULT.details[i].is_correct?' ok':' bad'} return `<button class="${cls}" onclick="IDX=${i};renderQuiz()">${i+1}</button>`}).join('');}
    function renderResult(q){if(!RESULT){solution.innerHTML=''; score.innerHTML=`Đã làm: ${Object.keys(ANSWERS).length}/${QUIZ.questions.length}`; return;} let r=RESULT.details[IDX]; score.innerHTML=`<b>Điểm:</b> ${RESULT.score}/${RESULT.total}<br><b>Đúng:</b> ${RESULT.correct_count}/${RESULT.total}`; if(RESULT.can_view_solution){solution.innerHTML=`<div class="solution"><b>Đáp án:</b> ${esc(r.correct_answer)}<br><b>Em chọn:</b> ${esc(r.user_answer||'Chưa chọn')}<hr><b>Lời giải:</b><br>${q.LoiGiai||''}</div>`} else {solution.innerHTML=`<div class="solution">Tài khoản FREE chỉ xem điểm. Cần VIP/S.VIP để xem đáp án và lời giải.</div>`} MathJax.typesetPromise();}
    function prevQ(){if(IDX>0){IDX--;renderQuiz()}} function nextQ(){if(QUIZ&&IDX<QUIZ.questions.length-1){IDX++;renderQuiz()}}
    async function fifty(){if(!QUIZ)return; let q=QUIZ.questions[IDX]; let res=await api('/api/fifty',{question_id:q.ID}); if(res.error){alert(res.error);return;} HIDDEN[q.ID]=res.hide||[]; renderQuiz();}
    async function submitQuiz(){if(!QUIZ)return; if(!confirm('Nộp bài?'))return; RESULT=await api('/api/submit',{session_id:QUIZ.session_id, answers:ANSWERS}); renderQuiz();}
    loadMeta();
    </script></body></html>
    """

    CONVERT_HTML = r"""
    <!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chuyển Excel sang JSON</title>
    <style>body{font-family:Arial,sans-serif;background:#f1f5f9;margin:0}.box{max-width:760px;margin:40px auto;background:white;border-radius:14px;padding:20px;border:1px solid #dbe4ef}.btn{background:#1d4ed8;color:white;border:none;border-radius:9px;padding:10px 14px;font-weight:bold}input{padding:10px;border:1px solid #cbd5e1;border-radius:8px;width:100%}pre{background:#0f172a;color:#e2e8f0;padding:12px;border-radius:10px;overflow:auto}</style></head><body><div class="box"><h2>Chuyển Google Sheet Excel sang JSON</h2><p>Công cụ này đọc sheet <b>Cau_Hoi</b> để tạo <b>luyen_de_vat_ly.json</b> và đọc sheet <b>HOC_VIEN</b> để tạo <b>users.json</b>.</p><form method="post" enctype="multipart/form-data"><input type="file" name="xlsx" accept=".xlsx" required><p><button class="btn">Chuyển và tải file ZIP</button></p></form><p><a href="/">← Quay lại app</a></p></div></body></html>
    """


    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = ""
        if request.method == "POST":
            mahs = clean_value(request.form.get("mahs", ""))
            mk = clean_value(request.form.get("matkhau", ""))
            for u in load_users():
                if key_norm(u.get("MaHS")) == key_norm(mahs) and clean_value(u.get("MatKhau")) == mk:
                    ok, msg = is_active_user(u)
                    if not ok:
                        error = msg
                        break
                    session["MaHS"] = u.get("MaHS")
                    return redirect(url_for("index"))
            else:
                error = "Sai MaHS hoặc MatKhau."
        return render_template_string(LOGIN_HTML, error=error)


    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))


    @app.route("/")
    def index():
        u = current_user()
        if not u:
            return redirect(url_for("login"))
        return render_template_string(APP_HTML, u=u, admin=is_admin(u))


    @app.route("/api/meta")
    def api_meta():
        if not current_user():
            return jsonify({"error": "Chưa đăng nhập"}), 401
        return jsonify(quiz_meta())


    @app.route("/api/start", methods=["POST"])
    def api_start():
        u = current_user()
        if not u:
            return jsonify({"error": "Chưa đăng nhập"}), 401
        made = clean_value((request.get_json(silent=True) or {}).get("MaDe", ""))
        data = load_data()
        qs = [q for q in data.get("questions", []) if clean_value(q.get("MaDe", "")) == made]
        if not qs:
            return jsonify({"error": "Không tìm thấy đề."})
        sid = stable_hash(f"{u.get('MaHS')}|{made}|{time.time()}|{random.random()}", 16)
        safe_qs = []
        for q in qs:
            x = dict(q)
            x.pop("DapAn", None)
            x.pop("LoiGiai", None)
            safe_qs.append(x)
        session.setdefault("quiz_sessions", {})[sid] = {"MaDe": made, "question_ids": [q.get("ID") for q in qs], "start": time.time()}
        session.modified = True
        return jsonify({"session_id": sid, "questions": safe_qs})


    @app.route("/api/fifty", methods=["POST"])
    def api_fifty():
        u = current_user()
        if not u:
            return jsonify({"error": "Chưa đăng nhập"}), 401
        if not can_use_5050(u):
            return jsonify({"error": "Tài khoản này chưa được dùng tính năng Loại 2 câu sai."})
        qid = clean_value((request.get_json(silent=True) or {}).get("question_id", ""))
        data = load_data()
        q = next((x for x in data.get("questions", []) if clean_value(x.get("ID", "")) == qid), None)
        if not q or normalize_dang(q.get("Dang", "")) != "Trắc nghiệm":
            return jsonify({"error": "Chỉ dùng cho câu trắc nghiệm A-B-C-D."})
        correct = norm_letter(q.get("DapAn", ""))
        wrong = [x for x in ["A", "B", "C", "D"] if x != correct and clean_value(q.get(x, ""))]
        random.shuffle(wrong)
        return jsonify({"hide": wrong[:2]})


    @app.route("/api/submit", methods=["POST"])
    def api_submit():
        u = current_user()
        if not u:
            return jsonify({"error": "Chưa đăng nhập"}), 401
        payload = request.get_json(silent=True) or {}
        sid = clean_value(payload.get("session_id", ""))
        answers = payload.get("answers", {}) or {}
        qsess = (session.get("quiz_sessions") or {}).get(sid)
        if not qsess:
            return jsonify({"error": "Phiên làm bài không hợp lệ."})
        ids = qsess.get("question_ids", [])
        data = load_data()
        qmap = {q.get("ID"): q for q in data.get("questions", [])}
        details = []
        correct_count = 0
        for qid in ids:
            q = qmap.get(qid)
            if not q:
                continue
            ok, corr, chosen = check_answer(q, answers.get(qid))
            if ok:
                correct_count += 1
            details.append({"question_id": qid, "is_correct": ok, "correct_answer": corr, "user_answer": chosen})
        total = len(details)
        score = round(10 * correct_count / total, 2) if total else 0
        return jsonify({"correct_count": correct_count, "total": total, "score": score, "can_view_solution": can_view_solution(u), "details": details})


    @app.route("/admin/check")
    def admin_check():
        u = current_user()
        if not u or not is_admin(u):
            return redirect(url_for("login"))
        report = check_json_files(DATA_JSON, USERS_JSON)
        return Response(report, mimetype="text/plain; charset=utf-8")


    @app.route("/admin/convert", methods=["GET", "POST"])
    def admin_convert():
        u = current_user()
        if not u or not is_admin(u):
            return redirect(url_for("login"))
        if request.method == "GET":
            return render_template_string(CONVERT_HTML)
        f = request.files.get("xlsx")
        if not f or not f.filename.lower().endswith(".xlsx"):
            return Response("Vui lòng chọn file .xlsx", status=400)
        with tempfile.TemporaryDirectory() as td:
            xlsx_path = Path(td) / "input.xlsx"
            data_path = Path(td) / "luyen_de_vat_ly.json"
            users_path = Path(td) / "users.json"
            f.save(xlsx_path)
            convert_xlsx_to_json_files(str(xlsx_path), str(data_path), str(users_path))
            report = check_json_files(str(data_path), str(users_path))
            mem = io.BytesIO()
            with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(data_path, "luyen_de_vat_ly.json")
                z.write(users_path, "users.json")
                z.writestr("bao_cao_kiem_tra.txt", report)
            mem.seek(0)
            return send_file(mem, as_attachment=True, download_name="json_luyen_de_va_users.zip", mimetype="application/zip")


# ============================================================
# 4) CLI DÙNG LOCAL
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Luyện đề JSON + chuyển XLSX sang JSON + users từ HOC_VIEN")
    parser.add_argument("--convert", help="File Excel .xlsx cần chuyển")
    parser.add_argument("--json", default="luyen_de_vat_ly.json", help="File JSON đề")
    parser.add_argument("--users", default="users.json", help="File JSON tài khoản")
    parser.add_argument("--check", action="store_true", help="Kiểm tra JSON")
    parser.add_argument("--serve", action="store_true", help="Chạy web app local")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    global DATA_JSON, USERS_JSON
    DATA_JSON = args.json
    USERS_JSON = args.users

    if args.convert:
        result = convert_xlsx_to_json_files(args.convert, args.json, args.users)
        print("ĐÃ CHUYỂN XONG")
        print(f"- File đề: {args.json}")
        print(f"- File users: {args.users}")
        print(f"- Số câu hỏi: {len(result['data'].get('questions', []))}")
        print(f"- Số đề/thẻ đề: {len(result['data'].get('catalog_rows', []))}")
        print(f"- Số tài khoản HOC_VIEN: {len(result['users_data'].get('users', []))}")
        print()
        print(check_json_files(args.json, args.users))
        return

    if args.check:
        print(check_json_files(args.json, args.users))
        return

    if args.serve or True:
        if not HAS_FLASK:
            print("Chưa cài Flask. Hãy chạy: pip install -r requirements.txt")
            return
        url = f"http://127.0.0.1:{args.port}"
        print("ỨNG DỤNG LUYỆN ĐỀ ĐANG CHẠY")
        print(f"- Dữ liệu đề: {DATA_JSON}")
        print(f"- Dữ liệu users: {USERS_JSON}")
        print(f"- Link máy này: {url}")
        print(f"- Link học sinh cùng Wi-Fi: http://IP-MAY-THAY:{args.port}")
        if not args.no_open:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
