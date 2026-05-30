# -*- coding: utf-8 -*-
"""
app_luyen_de_json_full.py
============================================================
Ứng dụng luyện đề đọc JSON cho nhẹ, có kèm chức năng chuyển XLSX Google Sheets sang JSON.

Tính năng chính:
- Chuyển file Google Sheets xuất .xlsx sang JSON một lần.
- App nạp JSON nhanh hơn đọc trực tiếp Excel.
- Giao diện chạy trên trình duyệt, có MathJax.
- Làm bài từng câu, không hiện đáp án/lời giải trước khi nộp.
- Có Loại 2 câu sai cho câu trắc nghiệm A-B-C-D.
- Sau khi nộp: tô xanh đáp án đúng, tô đỏ đáp án chọn sai.
- Hỗ trợ: Trắc nghiệm, Đúng/Sai, Trả lời ngắn, Tự luận.
- Lọc đúng đề theo MaDe nếu có; nếu chưa có thì tự sinh MaDe theo khóa:
  Lớp + Môn + Chương + Bài học + Dạng bài tập + Bộ đề + Đề.

Cách dùng:
1) Chuyển XLSX sang JSON:
   python app_luyen_de_json_full.py --convert "Luyện Đề Vật Lý.xlsx" --json luyen_de_vat_ly.json

2) Chạy app bằng JSON:
   python app_luyen_de_json_full.py --json luyen_de_vat_ly.json

3) Nếu để cùng thư mục có file luyen_de_vat_ly.json:
   python app_luyen_de_json_full.py

Không cần pandas, không cần openpyxl. Chỉ dùng thư viện chuẩn Python.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import random
import re
import socket
import sys
import threading
import time
import unicodedata
import urllib.parse
import webbrowser
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

# ============================================================
# PHẦN 1. ĐỌC NHANH XLSX KHÔNG CẦN OPENPYXL
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
            raise KeyError(f"Không có sheet {sheet_name!r}. Các sheet: {', '.join(self.sheet_names())}")
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
# PHẦN 2. CHUẨN HÓA DỮ LIỆU TỪ GOOGLE SHEETS
# ============================================================

ALIASES: Dict[str, List[str]] = {
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

CANONICAL_FIELDS = [
    "MaDe", "ID", "BoDe", "De", "Lop", "Mon", "Chuong", "BaiHoc", "DangBaiTap",
    "MucDo", "Dang", "CauHoi", "A", "B", "C", "D", "DapAn", "SaiSo",
    "LoiGiai", "Diem", "HinhAnh", "QuyenTruyCap", "SoCau",
]


def strip_accents(s: str) -> str:
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


def key_norm(s: Any) -> str:
    s = strip_accents(str(s or "").strip().lower())
    s = re.sub(r"\s+", " ", s)
    return s


def clean_value(v: Any) -> str:
    s = str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    # Google Sheet hay biến 9 thành 9.0, 12 thành 12.0.
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def get_any(row: Dict[str, Any], names: List[str]) -> str:
    direct = {key_norm(k): k for k in row.keys()}
    for name in names:
        k = direct.get(key_norm(name))
        if k is not None:
            return clean_value(row.get(k, ""))
    return ""


def canonical_row(row: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for field in CANONICAL_FIELDS:
        out[field] = get_any(row, ALIASES.get(field, [field]))
    return out


def stable_hash(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n].upper()


def make_group_base(q: Dict[str, str]) -> str:
    parts = [
        q.get("Lop", ""), q.get("Mon", ""), q.get("Chuong", ""), q.get("BaiHoc", ""),
        q.get("DangBaiTap", ""), q.get("BoDe", ""), q.get("De", ""),
    ]
    return "|".join(key_norm(x) for x in parts)


def make_made(q: Dict[str, str]) -> str:
    made = clean_value(q.get("MaDe", ""))
    if made:
        return made
    base = make_group_base(q)
    return "MD_" + stable_hash(base, 10)


def is_blank_question(q: Dict[str, str]) -> bool:
    return not clean_value(q.get("CauHoi"))


def normalize_dang(s: str) -> str:
    k = key_norm(s)
    if any(x in k for x in ["dung sai", "true", "tf", "ds"]):
        return "Đúng sai"
    if any(x in k for x in ["tra loi ngan", "short", "tln"]):
        return "Trả lời ngắn"
    if any(x in k for x in ["tu luan", "essay", "tl"]):
        return "Tự luận"
    return "Trắc nghiệm"


def build_catalog_from_questions(questions: List[Dict[str, str]]) -> List[Dict[str, str]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for q in questions:
        made = q["MaDe"]
        if made not in groups:
            groups[made] = {
                "MaDe": made,
                "Lop": q.get("Lop", ""),
                "Mon": q.get("Mon", ""),
                "Chuong": q.get("Chuong", ""),
                "BaiHoc": q.get("BaiHoc", ""),
                "DangBaiTap": q.get("DangBaiTap", ""),
                "BoDe": q.get("BoDe", ""),
                "De": q.get("De", ""),
                "SoCau": 0,
                "MucDo": set(),
                "Dang": set(),
                "QuyenTruyCap": set(),
            }
        g = groups[made]
        g["SoCau"] += 1
        if q.get("MucDo"):
            g["MucDo"].add(q.get("MucDo"))
        if q.get("Dang"):
            g["Dang"].add(q.get("Dang"))
        if q.get("QuyenTruyCap"):
            g["QuyenTruyCap"].add(q.get("QuyenTruyCap"))
    out: List[Dict[str, str]] = []
    for g in groups.values():
        item = dict(g)
        item["MucDo"] = ", ".join(sorted(g["MucDo"]))
        item["Dang"] = ", ".join(sorted(g["Dang"]))
        item["QuyenTruyCap"] = ", ".join(sorted(g["QuyenTruyCap"]))
        item["SoCau"] = str(g["SoCau"])
        out.append(item)
    out.sort(key=lambda x: (key_norm(x.get("Mon")), key_norm(x.get("Lop")), key_norm(x.get("Chuong")), key_norm(x.get("BaiHoc")), key_norm(x.get("De"))))
    return out


def convert_xlsx_to_json(xlsx_path: str, json_path: str) -> Dict[str, Any]:
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
            q = canonical_row(row)
            if is_blank_question(q):
                continue
            q["Dang"] = normalize_dang(q.get("Dang", ""))
            q["MaDe"] = make_made(q)
            q["ID"] = q.get("ID") or ("AUTO_" + stable_hash(json.dumps(q, ensure_ascii=False), 10))
            questions.append(q)

        # Thống kê sheet để thầy biết file đọc được gì.
        sheet_stats: Dict[str, Dict[str, int]] = {}
        for s in sheets:
            count = 0
            max_col = 0
            for row in reader.iter_rows(s):
                count += 1
                max_col = max(max_col, len(row))
            sheet_stats[s] = {"rows": count, "cols": max_col}

    catalog = build_catalog_from_questions(questions)
    data = {
        "version": "full-json-quiz-1.0",
        "meta": {
            "source_file": xlsx.name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "convert_seconds": round(time.time() - t0, 3),
        },
        "sheet_stats": sheet_stats,
        "questions": questions,
        "catalog_rows": catalog,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


# ============================================================
# PHẦN 3. CHẤM ĐIỂM
# ============================================================

def norm_letter(s: str) -> str:
    s = clean_value(s).upper()
    m = re.search(r"[ABCD]", s)
    return m.group(0) if m else ""


def norm_tf_answer(s: str) -> List[str]:
    s = strip_accents(clean_value(s).upper())
    s = s.replace("DUNG", "D").replace("TRUE", "D").replace("SAI", "S").replace("FALSE", "S")
    # Dấu Đ mất dấu thành D.
    vals = re.findall(r"[DS]", s)
    return vals[:4]


def parse_float_vn(s: str) -> Optional[float]:
    s = clean_value(s)
    if not s:
        return None
    s = s.replace(" ", "")
    # 2.079,9 hoặc 2,079.9 không xử lý quá sâu; ưu tiên dạng VN: 2079,9.
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
        if isinstance(user_answer, list):
            chosen_list = ["Đ" if key_norm(x) in ["d", "dung", "đ", "đúng"] else "S" if key_norm(x) in ["s", "sai"] else "" for x in user_answer]
        else:
            chosen_list = norm_tf_answer(str(user_answer or ""))
            chosen_list = ["Đ" if x == "D" else "S" for x in chosen_list]
        corr = ["Đ" if x == "D" else "S" for x in correct_list]
        while len(chosen_list) < 4:
            chosen_list.append("")
        ok = len(corr) == 4 and chosen_list[:4] == corr[:4]
        return ok, ",".join(corr), ",".join(chosen_list[:4])

    if dang == "Trả lời ngắn":
        correct_num = parse_float_vn(correct_raw)
        chosen_num = parse_float_vn(str(user_answer or ""))
        tol = parse_float_vn(q.get("SaiSo", ""))
        if tol is None:
            tol = 0.0
        if correct_num is not None and chosen_num is not None:
            return abs(chosen_num - correct_num) <= tol + 1e-12, correct_raw, str(user_answer or "")
        # Nếu không phải số thì so khớp chữ.
        return key_norm(correct_raw) == key_norm(str(user_answer or "")), correct_raw, str(user_answer or "")

    # Tự luận: không tự chấm đúng/sai, chỉ trả lời đã nộp.
    return False, correct_raw, str(user_answer or "")


# ============================================================
# PHẦN 4. KHO DỮ LIỆU VÀ API
# ============================================================

class QuizStore:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.questions: List[Dict[str, str]] = data.get("questions", [])
        self.catalog = build_catalog_from_questions(self.questions)
        self.by_made: Dict[str, List[Dict[str, str]]] = {}
        for q in self.questions:
            made = q.get("MaDe") or make_made(q)
            q["MaDe"] = made
            self.by_made.setdefault(made, []).append(q)
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def meta(self) -> Dict[str, Any]:
        def opts(field: str) -> List[str]:
            vals = sorted({clean_value(x.get(field, "")) for x in self.catalog if clean_value(x.get(field, ""))}, key=key_norm)
            return vals
        return {
            "meta": self.data.get("meta", {}),
            "count_questions": len(self.questions),
            "count_catalog": len(self.catalog),
            "filters": {
                "Mon": opts("Mon"),
                "Lop": opts("Lop"),
                "Chuong": opts("Chuong"),
                "BaiHoc": opts("BaiHoc"),
                "DangBaiTap": opts("DangBaiTap"),
                "BoDe": opts("BoDe"),
            },
            "catalog": self.catalog,
        }

    def start_quiz(self, made: str) -> Dict[str, Any]:
        qs = list(self.by_made.get(made, []))
        if not qs:
            raise ValueError("Không có câu hỏi trong đề này")
        sid = stable_hash(f"{made}|{time.time()}|{random.random()}", 16)
        self.sessions[sid] = {
            "made": made,
            "created": time.time(),
            "questions": qs,
            "used_5050": set(),
        }
        return {
            "sid": sid,
            "questions": [self.public_question(q, i) for i, q in enumerate(qs)],
        }

    def public_question(self, q: Dict[str, str], index: int) -> Dict[str, Any]:
        return {
            "index": index,
            "ID": q.get("ID", ""),
            "MaDe": q.get("MaDe", ""),
            "Dang": normalize_dang(q.get("Dang", "")),
            "MucDo": q.get("MucDo", ""),
            "CauHoi": q.get("CauHoi", ""),
            "A": q.get("A", ""),
            "B": q.get("B", ""),
            "C": q.get("C", ""),
            "D": q.get("D", ""),
            "HinhAnh": q.get("HinhAnh", ""),
        }

    def fifty_fifty(self, sid: str, index: int) -> Dict[str, Any]:
        ses = self.sessions.get(sid)
        if not ses:
            raise ValueError("Phiên làm bài đã hết hạn")
        if index in ses["used_5050"]:
            return {"hide": [], "message": "Câu này đã dùng Loại 2 câu sai rồi."}
        qs: List[Dict[str, str]] = ses["questions"]
        if not (0 <= index < len(qs)):
            raise ValueError("Số câu không hợp lệ")
        q = qs[index]
        if normalize_dang(q.get("Dang", "")) != "Trắc nghiệm":
            return {"hide": [], "message": "Chỉ dùng được cho câu trắc nghiệm A-B-C-D."}
        correct = norm_letter(q.get("DapAn", ""))
        letters = [x for x in "ABCD" if clean_value(q.get(x, ""))]
        wrongs = [x for x in letters if x != correct]
        random.shuffle(wrongs)
        hide = wrongs[:2]
        ses["used_5050"].add(index)
        return {"hide": hide, "message": "Đã loại 2 câu sai."}

    def submit(self, sid: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        ses = self.sessions.get(sid)
        if not ses:
            raise ValueError("Phiên làm bài đã hết hạn")
        qs: List[Dict[str, str]] = ses["questions"]
        results: List[Dict[str, Any]] = []
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
            results.append({
                "index": i,
                "ID": q.get("ID", ""),
                "Dang": dang,
                "ok": ok,
                "correct": correct,
                "chosen": chosen,
                "LoiGiai": q.get("LoiGiai", ""),
                "DapAn": q.get("DapAn", ""),
            })
        score = round(10 * correct_count / auto_count, 2) if auto_count else 0
        return {
            "total": len(qs),
            "auto_count": auto_count,
            "correct_count": correct_count,
            "score": score,
            "results": results,
        }


STORE: Optional[QuizStore] = None


def json_response(handler: BaseHTTPRequestHandler, obj: Any, status: int = 200) -> None:
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def read_body_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    n = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(n) if n else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


# ============================================================
# PHẦN 5. GIAO DIỆN HTML + JAVASCRIPT + MATHJAX
# ============================================================

INDEX_HTML = r'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ứng dụng luyện đề Vật lý - Toán học</title>
  <script>
    window.MathJax = {
      tex: {inlineMath: [['$', '$'], ['\\(', '\\)']], displayMath: [['$$','$$'], ['\\[','\\]']]},
      svg: {fontCache: 'global'}
    };
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
  <style>
    :root{--blue:#1d4ed8;--green:#dcfce7;--green2:#16a34a;--red:#fee2e2;--red2:#dc2626;--yellow:#fff7ed;--border:#d6dee9;--bg:#f5f7fb;--text:#111827}
    *{box-sizing:border-box} body{margin:0;background:var(--bg);font-family:Arial,Helvetica,sans-serif;color:var(--text);font-size:15px}
    .top{background:var(--blue);color:#fff;padding:12px 18px;position:sticky;top:0;z-index:5;box-shadow:0 2px 8px #0002}
    .top h1{margin:0;font-size:20px}.top small{opacity:.9}.wrap{padding:14px;max-width:1380px;margin:auto}
    .panel{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:12px;box-shadow:0 1px 3px #0001}
    .row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:4px;min-width:150px;flex:1}.field label{font-weight:700;font-size:12px;color:#374151}
    select,input,button,textarea{font-family:inherit;font-size:14px;border:1px solid var(--border);border-radius:8px;padding:9px 10px;background:#fff}button{cursor:pointer;font-weight:700}.btn{background:var(--blue);color:#fff;border-color:var(--blue)}.btn2{background:#eef2ff;color:#1e40af}.btnGreen{background:#dcfce7;color:#166534;border-color:#bbf7d0}.btnRed{background:#fee2e2;color:#991b1b;border-color:#fecaca}.btn:disabled,button:disabled{opacity:.55;cursor:not-allowed}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}.card{border:1px solid var(--border);background:#fff;border-radius:12px;padding:12px}.card h3{margin:0 0 8px;font-size:16px;color:#1e3a8a}.tag{display:inline-block;padding:3px 8px;border-radius:999px;background:#eef2ff;color:#1d4ed8;font-size:12px;font-weight:700;margin:2px}.muted{color:#6b7280}.line{height:1px;background:var(--border);margin:10px 0}
    .quizLayout{display:grid;grid-template-columns:1fr 260px;gap:12px}.qbox{border:1px solid #111827;background:#fff;border-radius:8px;padding:14px;min-height:170px;line-height:1.55;font-size:18px}.qid{font-size:20px;font-weight:800;margin-bottom:10px}.options{margin-top:12px}.opt{display:flex;gap:9px;align-items:flex-start;border:1px solid transparent;border-radius:10px;padding:10px;margin:7px 0;background:#fff}.opt:hover{background:#f8fafc}.opt input{margin-top:4px}.optionHidden{opacity:.25;pointer-events:none;text-decoration:line-through}.correct{background:var(--green)!important;border-color:#86efac!important}.wrong{background:var(--red)!important;border-color:#fecaca!important}.tfrow{display:grid;grid-template-columns:36px 1fr 90px 90px;gap:8px;align-items:center;border:1px solid var(--border);border-radius:10px;padding:8px;margin:8px 0}.navNums{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.num{padding:8px 0;border-radius:8px;background:#fff;border:1px solid var(--border);font-weight:800}.num.active{outline:3px solid #93c5fd}.num.answered{background:#fef3c7}.num.ok{background:var(--green);color:#166534}.num.bad{background:var(--red);color:#991b1b}.solution{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px;margin-top:12px;display:none}.resultBox{font-size:18px;font-weight:800}.hide{display:none!important}.imgQ{max-width:100%;border:1px solid var(--border);border-radius:8px;margin-top:10px}
    @media(max-width:900px){.quizLayout{grid-template-columns:1fr}.side{order:-1}.qbox{font-size:16px}.top h1{font-size:17px}}
  </style>
</head>
<body>
  <div class="top"><h1>ỨNG DỤNG LUYỆN ĐỀ VẬT LÝ - TOÁN HỌC</h1><small id="info">Đang nạp dữ liệu...</small></div>
  <div class="wrap">
    <div id="home">
      <div class="panel">
        <b>Thiết lập luyện tập</b>
        <div class="row" style="margin-top:10px">
          <div class="field"><label>Môn</label><select id="fMon"><option value="">Tất cả</option></select></div>
          <div class="field"><label>Lớp</label><select id="fLop"><option value="">Tất cả</option></select></div>
          <div class="field"><label>Chương</label><select id="fChuong"><option value="">Tất cả</option></select></div>
          <div class="field"><label>Bài học</label><select id="fBaiHoc"><option value="">Tất cả</option></select></div>
          <div class="field"><label>Bộ đề</label><select id="fBoDe"><option value="">Tất cả</option></select></div>
          <div class="field"><label>Tìm nhanh</label><input id="fSearch" placeholder="Nhập từ khóa..."></div>
          <button class="btn" onclick="renderCatalog()">Lọc đề</button>
        </div>
      </div>
      <div class="panel"><b>Mục lục đề</b> <span id="countCat" class="muted"></span><div id="catalog" class="grid" style="margin-top:10px"></div></div>
    </div>

    <div id="quiz" class="hide">
      <div class="panel row" style="justify-content:space-between">
        <div><button class="btn2" onclick="backHome()">← Về mục lục</button> <span id="quizTitle" style="font-weight:800"></span></div>
        <div class="resultBox" id="resultBox"></div>
      </div>
      <div class="quizLayout">
        <div>
          <div class="panel">
            <div class="row" style="justify-content:space-between;align-items:center">
              <div class="qid" id="qid"></div>
              <div>
                <button id="btn5050" class="btnGreen" onclick="use5050()">Loại 2 câu sai</button>
                <button id="btnSubmit" class="btn" onclick="submitQuiz()">Nộp bài</button>
              </div>
            </div>
            <div id="qtext" class="qbox"></div>
            <div id="options" class="options"></div>
            <div id="solution" class="solution"></div>
            <div class="row" style="margin-top:12px;justify-content:space-between">
              <button onclick="prevQ()">← Câu trước</button>
              <button onclick="nextQ()">Câu sau →</button>
            </div>
          </div>
        </div>
        <div class="side panel">
          <b>Bảng câu hỏi</b>
          <div id="navNums" class="navNums" style="margin-top:10px"></div>
          <div class="line"></div>
          <div class="muted">Màu vàng: đã làm. Sau khi nộp: xanh đúng, đỏ sai.</div>
        </div>
      </div>
    </div>
  </div>

<script>
let META=null, CATALOG=[], SID='', QUESTIONS=[], CUR=0, ANSWERS={}, SUBMITTED=false, RESULTS={};
function esc(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])).replace(/\n/g,'<br>')}
function val(id){return document.getElementById(id).value}
function setOptions(id, arr){let el=document.getElementById(id); el.innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option>${esc(x)}</option>`).join('')}
function typeset(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise().catch(()=>{})}
async function api(url, opts={}){let r=await fetch(url, opts); let j=await r.json(); if(!r.ok||j.error) throw new Error(j.error||'Lỗi API'); return j}
async function init(){META=await api('/api/meta'); CATALOG=META.catalog; document.getElementById('info').textContent=`${META.count_questions} câu hỏi | ${META.count_catalog} đề/thẻ đề`; setOptions('fMon',META.filters.Mon); setOptions('fLop',META.filters.Lop); setOptions('fChuong',META.filters.Chuong); setOptions('fBaiHoc',META.filters.BaiHoc); setOptions('fBoDe',META.filters.BoDe); renderCatalog()}
function okFilter(x){let s=val('fSearch').toLowerCase(); let blob=[x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.DangBaiTap,x.BoDe,x.De,x.MucDo,x.Dang].join(' ').toLowerCase(); return (!val('fMon')||x.Mon==val('fMon'))&&(!val('fLop')||x.Lop==val('fLop'))&&(!val('fChuong')||x.Chuong==val('fChuong'))&&(!val('fBaiHoc')||x.BaiHoc==val('fBaiHoc'))&&(!val('fBoDe')||x.BoDe==val('fBoDe'))&&(!s||blob.includes(s))}
function renderCatalog(){let list=CATALOG.filter(okFilter); document.getElementById('countCat').textContent=`(${list.length} mục)`; document.getElementById('catalog').innerHTML=list.map(x=>`<div class="card"><h3>${esc(x.De||x.BaiHoc||'Đề luyện tập')}</h3><div><span class="tag">${esc(x.Mon)}</span><span class="tag">Lớp ${esc(x.Lop)}</span><span class="tag">${esc(x.SoCau)} câu</span></div><div class="line"></div><div><b>Chương:</b> ${esc(x.Chuong||'')}</div><div><b>Bài:</b> ${esc(x.BaiHoc||'')}</div><div><b>Dạng:</b> ${esc(x.Dang||'')}</div><div><b>Mức độ:</b> ${esc(x.MucDo||'')}</div><div><b>Bộ đề:</b> ${esc(x.BoDe||'')}</div><div style="text-align:right;margin-top:10px"><button class="btn" onclick="startQuiz('${x.MaDe}')">Làm bài</button></div></div>`).join('')||'<div class="muted">Không có đề phù hợp.</div>'; typeset()}
async function startQuiz(made){let j=await api('/api/start?made='+encodeURIComponent(made)); SID=j.sid; QUESTIONS=j.questions; CUR=0; ANSWERS={}; SUBMITTED=false; RESULTS={}; document.getElementById('home').classList.add('hide'); document.getElementById('quiz').classList.remove('hide'); document.getElementById('resultBox').textContent=''; let c=CATALOG.find(x=>x.MaDe==made)||{}; document.getElementById('quizTitle').textContent=`${c.Mon||''} ${c.Lop?'- Lớp '+c.Lop:''} | ${c.De||c.BaiHoc||''}`; renderNav(); renderQuestion()}
function backHome(){document.getElementById('quiz').classList.add('hide'); document.getElementById('home').classList.remove('hide')}
function saveCurrent(){let q=QUESTIONS[CUR]; if(!q)return; if(q.Dang=='Trắc nghiệm'){let r=document.querySelector(`input[name="ans_${CUR}"]:checked`); if(r) ANSWERS[CUR]=r.value} else if(q.Dang=='Đúng sai'){let arr=[]; for(let L of ['A','B','C','D']){let r=document.querySelector(`input[name="tf_${CUR}_${L}"]:checked`); arr.push(r?r.value:'')} ANSWERS[CUR]=arr} else {let el=document.getElementById('shortAns'); if(el) ANSWERS[CUR]=el.value} renderNav()}
function renderNav(){let html=''; for(let i=0;i<QUESTIONS.length;i++){let cls='num'; if(i==CUR)cls+=' active'; if(ANSWERS[i]!=null&&String(ANSWERS[i]).length)cls+=' answered'; if(SUBMITTED&&RESULTS[i])cls+=RESULTS[i].ok?' ok':' bad'; html+=`<button class="${cls}" onclick="goQ(${i})">${i+1}</button>`} document.getElementById('navNums').innerHTML=html}
function goQ(i){saveCurrent(); CUR=i; renderQuestion()}
function prevQ(){if(CUR>0){saveCurrent(); CUR--; renderQuestion()}}
function nextQ(){if(CUR<QUESTIONS.length-1){saveCurrent(); CUR++; renderQuestion()}}
function renderQuestion(){let q=QUESTIONS[CUR]; renderNav(); document.getElementById('qid').textContent=`Câu ${CUR+1}/${QUESTIONS.length} | ID: ${q.ID||''} | ${q.MucDo||''} - ${q.Dang}`; let img=q.HinhAnh?`<br><img class="imgQ" src="${esc(q.HinhAnh)}">`:''; document.getElementById('qtext').innerHTML=esc(q.CauHoi)+img; document.getElementById('solution').style.display='none'; document.getElementById('solution').innerHTML=''; document.getElementById('btn5050').disabled=SUBMITTED||q.Dang!='Trắc nghiệm'; document.getElementById('btnSubmit').disabled=SUBMITTED; let html=''; if(q.Dang=='Trắc nghiệm'){for(let L of ['A','B','C','D']){if(!q[L])continue; let checked=ANSWERS[CUR]==L?'checked':''; let cls='opt'; if(SUBMITTED&&RESULTS[CUR]){if(RESULTS[CUR].correct==L)cls+=' correct'; if(RESULTS[CUR].chosen==L&&RESULTS[CUR].chosen!=RESULTS[CUR].correct)cls+=' wrong'} html+=`<label id="opt_${L}" class="${cls}"><input type="radio" name="ans_${CUR}" value="${L}" ${checked} ${SUBMITTED?'disabled':''} onchange="saveCurrent()"><b>${L}.</b><span>${esc(q[L])}</span></label>`}} else if(q.Dang=='Đúng sai'){let old=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:['','','','']; let corr=SUBMITTED&&RESULTS[CUR]?String(RESULTS[CUR].correct).split(','):[]; let chosen=SUBMITTED&&RESULTS[CUR]?String(RESULTS[CUR].chosen).split(','):old; for(let idx=0;idx<4;idx++){let L=['A','B','C','D'][idx]; if(!q[L])continue; let cls='tfrow'; if(SUBMITTED){if(chosen[idx]&&chosen[idx]==corr[idx])cls+=' correct'; else cls+=' wrong'} html+=`<div class="${cls}"><b>${L}.</b><div>${esc(q[L])}</div><label><input type="radio" name="tf_${CUR}_${L}" value="Đ" ${old[idx]=='Đ'?'checked':''} ${SUBMITTED?'disabled':''} onchange="saveCurrent()"> Đúng</label><label><input type="radio" name="tf_${CUR}_${L}" value="S" ${old[idx]=='S'?'checked':''} ${SUBMITTED?'disabled':''} onchange="saveCurrent()"> Sai</label></div>`}} else if(q.Dang=='Trả lời ngắn'){let cls=''; if(SUBMITTED&&RESULTS[CUR]) cls=RESULTS[CUR].ok?'correct':'wrong'; html=`<input id="shortAns" class="${cls}" style="width:100%;font-size:18px" placeholder="Nhập đáp án..." value="${esc(ANSWERS[CUR]||'')}" ${SUBMITTED?'disabled':''} oninput="saveCurrent()">`} else {html=`<textarea id="shortAns" style="width:100%;min-height:130px" placeholder="Nhập bài làm tự luận..." ${SUBMITTED?'disabled':''} oninput="saveCurrent()">${esc(ANSWERS[CUR]||'')}</textarea>`} document.getElementById('options').innerHTML=html; if(SUBMITTED&&RESULTS[CUR]){let r=RESULTS[CUR]; document.getElementById('solution').style.display='block'; document.getElementById('solution').innerHTML=`<b>Đáp án:</b> ${esc(r.correct||r.DapAn||'')}<br><b>Em chọn:</b> ${esc(r.chosen||'')}<div class="line"></div><b>Lời giải:</b><br>${esc(r.LoiGiai||'Chưa có lời giải.')}`;} typeset()}
async function use5050(){saveCurrent(); let j=await api('/api/fifty',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR})}); for(let L of j.hide||[]){let el=document.getElementById('opt_'+L); if(el)el.classList.add('optionHidden')} document.getElementById('btn5050').disabled=true; if(j.message) alert(j.message)}
async function submitQuiz(){saveCurrent(); if(!confirm('Nộp bài và xem đáp án/lời giải?'))return; let j=await api('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,answers:ANSWERS})}); SUBMITTED=true; RESULTS={}; for(let r of j.results)RESULTS[r.index]=r; document.getElementById('resultBox').textContent=`Điểm: ${j.score}/10 | Đúng ${j.correct_count}/${j.auto_count}`; renderQuestion(); renderNav()}
init().catch(e=>{document.body.innerHTML='<pre style="padding:20px;color:red">'+e.message+'</pre>'})
</script>
</body>
</html>'''


class QuizHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        global STORE
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)
            if path == "/":
                raw = INDEX_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if path == "/api/meta":
                json_response(self, STORE.meta())
                return
            if path == "/api/start":
                made = query.get("made", [""])[0]
                json_response(self, STORE.start_quiz(made))
                return
            json_response(self, {"error": "Không tìm thấy đường dẫn"}, 404)
        except Exception as e:
            json_response(self, {"error": str(e)}, 500)

    def do_POST(self) -> None:
        global STORE
        try:
            parsed = urllib.parse.urlparse(self.path)
            body = read_body_json(self)
            if parsed.path == "/api/fifty":
                sid = body.get("sid", "")
                index = int(body.get("index", 0))
                json_response(self, STORE.fifty_fifty(sid, index))
                return
            if parsed.path == "/api/submit":
                sid = body.get("sid", "")
                answers = body.get("answers", {})
                json_response(self, STORE.submit(sid, answers))
                return
            json_response(self, {"error": "Không tìm thấy đường dẫn"}, 404)
        except Exception as e:
            json_response(self, {"error": str(e)}, 500)




# ============================================================
# PHẦN 6A. WSGI APP CHO RENDER / GUNICORN
# ============================================================
# Render chạy lệnh: gunicorn app_luyen_de_json_full:app
# Vì vậy file này phải có biến app là một WSGI callable.
# Phần này KHÔNG cần Flask, chạy trực tiếp với gunicorn.


def get_store_for_web() -> QuizStore:
    """Nạp JSON một lần khi chạy trên hosting."""
    global STORE
    if STORE is None:
        json_path = os.environ.get("JSON_PATH", "") or str(Path(__file__).with_name("luyen_de_vat_ly.json"))
        data = load_json(json_path)
        STORE = QuizStore(data)
    return STORE


def _wsgi_send(start_response, status: str, body: bytes, content_type: str):
    start_response(status, [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ])
    return [body]


def _wsgi_json(start_response, obj: Any, code: int = 200):
    status_map = {200: "200 OK", 400: "400 Bad Request", 404: "404 Not Found", 500: "500 Internal Server Error"}
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return _wsgi_send(start_response, status_map.get(code, "200 OK"), raw, "application/json; charset=utf-8")


def _wsgi_read_json(environ) -> Dict[str, Any]:
    try:
        n = int(environ.get("CONTENT_LENGTH") or "0")
    except Exception:
        n = 0
    raw = environ["wsgi.input"].read(n) if n else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def app(environ, start_response):
    """WSGI application cho gunicorn trên Render."""
    try:
        method = (environ.get("REQUEST_METHOD") or "GET").upper()
        path = environ.get("PATH_INFO") or "/"
        query = urllib.parse.parse_qs(environ.get("QUERY_STRING") or "")
        store = get_store_for_web()

        if method == "GET" and path == "/":
            return _wsgi_send(start_response, "200 OK", INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")

        if method == "GET" and path == "/api/meta":
            return _wsgi_json(start_response, store.meta())

        if method == "GET" and path == "/api/start":
            made = query.get("made", [""])[0]
            return _wsgi_json(start_response, store.start_quiz(made))

        if method == "POST" and path == "/api/fifty":
            body = _wsgi_read_json(environ)
            sid = body.get("sid", "")
            index = int(body.get("index", 0))
            return _wsgi_json(start_response, store.fifty_fifty(sid, index))

        if method == "POST" and path == "/api/submit":
            body = _wsgi_read_json(environ)
            sid = body.get("sid", "")
            answers = body.get("answers", {})
            return _wsgi_json(start_response, store.submit(sid, answers))

        return _wsgi_json(start_response, {"error": "Không tìm thấy đường dẫn"}, 404)

    except Exception as e:
        return _wsgi_json(start_response, {"error": str(e)}, 500)


# ============================================================
# PHẦN 6. CHẠY CHƯƠNG TRÌNH
# ============================================================

def find_free_port(start: int = 8765) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Không tìm được cổng trống")


def load_json(json_path: str) -> Dict[str, Any]:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def default_paths() -> Tuple[str, str]:
    here = Path.cwd()
    json_path = here / "luyen_de_vat_ly.json"
    xlsx_path = here / "Luyện Đề Vật Lý.xlsx"
    return str(xlsx_path), str(json_path)


def main() -> None:
    global STORE
    parser = argparse.ArgumentParser(description="Ứng dụng luyện đề JSON + MathJax + 50:50")
    parser.add_argument("input", nargs="?", help="File .json hoặc .xlsx")
    parser.add_argument("--json", default="", help="Đường dẫn file JSON")
    parser.add_argument("--convert", default="", help="Chuyển file XLSX sang JSON rồi thoát")
    parser.add_argument("--port", type=int, default=None, help="Cổng chạy web app. Trên Render sẽ tự lấy biến PORT")
    parser.add_argument("--host", default="", help="Host chạy web app. Local mặc định 127.0.0.1, Render mặc định 0.0.0.0")
    parser.add_argument("--no-open", action="store_true", help="Không tự mở trình duyệt")
    args = parser.parse_args()

    default_xlsx, default_json = default_paths()
    json_path = args.json or default_json

    if args.convert:
        xlsx_path = args.convert
        print(f"Đang chuyển: {xlsx_path}")
        data = convert_xlsx_to_json(xlsx_path, json_path)
        print(f"Đã tạo JSON: {json_path}")
        print(f"Số câu hỏi: {len(data.get('questions', []))}")
        print(f"Số đề/thẻ đề: {len(data.get('catalog_rows', []))}")
        return

    input_path = args.input or json_path
    if input_path.lower().endswith(".xlsx"):
        print("Đang chuyển tạm XLSX sang JSON để chạy cho nhẹ...")
        data = convert_xlsx_to_json(input_path, json_path)
    else:
        if not Path(input_path).exists():
            if Path(default_xlsx).exists():
                print("Chưa có JSON, đang tự chuyển từ Luyện Đề Vật Lý.xlsx...")
                data = convert_xlsx_to_json(default_xlsx, json_path)
            else:
                raise FileNotFoundError("Không thấy luyen_de_vat_ly.json hoặc Luyện Đề Vật Lý.xlsx")
        else:
            data = load_json(input_path)

    STORE = QuizStore(data)

    # Chạy local: mở tại 127.0.0.1 và tự tìm cổng trống.
    # Chạy Render/hosting: bắt buộc lắng nghe tại 0.0.0.0 và đúng cổng PORT do Render cấp.
    env_port = os.environ.get("PORT")
    is_hosting = bool(env_port or os.environ.get("RENDER"))
    port = int(env_port or args.port or 8765)
    host = args.host or ("0.0.0.0" if is_hosting else "127.0.0.1")
    if not is_hosting:
        port = find_free_port(port)

    server = ThreadingHTTPServer((host, port), QuizHandler)
    url = f"http://127.0.0.1:{port}/" if host == "127.0.0.1" else f"http://0.0.0.0:{port}/"
    print("=" * 60, flush=True)
    print("ỨNG DỤNG LUYỆN ĐỀ ĐANG CHẠY", flush=True)
    print(f"Host: {host}", flush=True)
    print(f"Cổng: {port}", flush=True)
    print(f"Địa chỉ local: {url}", flush=True)
    print(f"Số câu hỏi: {len(STORE.questions)}", flush=True)
    print(f"Số đề/thẻ đề: {len(STORE.catalog)}", flush=True)
    print("Nhấn Ctrl+C để tắt.", flush=True)
    print("=" * 60, flush=True)
    if (not is_hosting) and (not args.no_open):
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã tắt ứng dụng.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
