# -*- coding: utf-8 -*-
"""Export Google Sheets câu hỏi → JSON cache trên GitHub.

Chạy local:
    python scripts/export_sheets_to_json.py

Hoặc qua GitHub Actions (xem .github/workflows/sync_sheets_to_json.yml).

Đầu ra:
    data/json_questions/questions_db.json  — toàn bộ câu hỏi (tương thích QUESTION_SOURCE=JSON_ONLY/GITHUB_JSON)
    data/catalog.json                      — mục lục bài học từ DANH_MUC_BAI_HOC
    data/lesson_index.json                 — index tra cứu nhanh theo Mon/Lop/Chuong/BaiHoc

Biến môi trường cần có:
    GOOGLE_SHEET_ID
    GOOGLE_CREDENTIALS_JSON   (JSON chuỗi hoặc đường dẫn file .json)
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    sys.exit("Thiếu gspread/google-auth. Chạy: pip install gspread google-auth")

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

QUESTION_FIELDS = [
    "ID", "MaDe", "BoDe", "De", "Lop", "Mon", "Chuong", "BaiHoc",
    "DangBaiTap", "MucDo", "Dang", "CauHoi", "A", "B", "C", "D",
    "DapAn", "SaiSo", "LoiGiai", "HinhAnh", "QuyenTruyCap", "TrangThai",
    "NangLucVatLy", "NgayCapNhat",
]


def _clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _load_credentials() -> Dict[str, Any]:
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    if not raw:
        sys.exit("Thiếu GOOGLE_CREDENTIALS_JSON")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        path = Path(raw)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        sys.exit(f"GOOGLE_CREDENTIALS_JSON không phải JSON hợp lệ và file '{raw}' không tồn tại.")


def _connect() -> gspread.Spreadsheet:
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        sys.exit("Thiếu GOOGLE_SHEET_ID")
    info = _load_credentials()
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id)


def _worksheet_rows(sheet: gspread.Spreadsheet, name: str) -> List[Dict[str, str]]:
    try:
        ws = sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"[WARN] Không tìm thấy sheet '{name}' — bỏ qua.")
        return []
    return ws.get_all_records(default_blank="")


def export_questions(sheet: gspread.Spreadsheet) -> List[Dict[str, Any]]:
    print("[INFO] Đang đọc sheet Cau_Hoi…")
    rows = _worksheet_rows(sheet, "Cau_Hoi")
    questions = []
    for i, row in enumerate(rows):
        q: Dict[str, Any] = {}
        for f in QUESTION_FIELDS:
            q[f] = _clean(row.get(f, ""))
        # Gán _row ảo để tương thích với app.py
        q["_row"] = 900000 + i + 1
        q["_source"] = "GITHUB_JSON"
        q["_readonly_json"] = True
        questions.append(q)
    print(f"[INFO] Đọc được {len(questions)} câu hỏi.")
    return questions


def export_catalog(sheet: gspread.Spreadsheet) -> List[Dict[str, Any]]:
    print("[INFO] Đang đọc sheet DANH_MUC_BAI_HOC…")
    rows = _worksheet_rows(sheet, "DANH_MUC_BAI_HOC")
    catalog = []
    for row in rows:
        item = {k: _clean(v) for k, v in row.items()}
        if any(item.values()):
            catalog.append(item)
    print(f"[INFO] Mục lục: {len(catalog)} mục.")
    return catalog


def build_lesson_index(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tạo index tra cứu nhanh theo Mon/Lop/Chuong/BaiHoc."""
    index: Dict[str, Any] = {}
    for q in questions:
        mon = _clean(q.get("Mon"))
        lop = _clean(q.get("Lop"))
        chuong = _clean(q.get("Chuong"))
        bai = _clean(q.get("BaiHoc"))
        if not mon:
            continue
        key = f"{mon}|{lop}|{chuong}|{bai}"
        if key not in index:
            index[key] = {"Mon": mon, "Lop": lop, "Chuong": chuong, "BaiHoc": bai, "count": 0}
        index[key]["count"] += 1
    return {"generated_at": datetime.now().isoformat(timespec="seconds"), "lessons": list(index.values())}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Ghi {path} ({path.stat().st_size // 1024} KB)")


def main() -> None:
    sheet = _connect()

    questions = export_questions(sheet)
    catalog = export_catalog(sheet)
    lesson_index = build_lesson_index(questions)

    now = datetime.now().isoformat(timespec="seconds")

    questions_pkg = {
        "title": "Ngân hàng câu hỏi — GitHub JSON cache",
        "exportedAt": now,
        "count": len(questions),
        "questions": questions,
    }

    catalog_pkg = {
        "title": "Mục lục bài học — GitHub JSON cache",
        "exportedAt": now,
        "count": len(catalog),
        "catalog": catalog,
    }

    write_json(ROOT / "data" / "json_questions" / "questions_db.json", questions_pkg)
    write_json(ROOT / "data" / "catalog.json", catalog_pkg)
    write_json(ROOT / "data" / "lesson_index.json", lesson_index)

    print(f"\n✅ Export xong: {len(questions)} câu, {len(catalog)} mục lục, {len(lesson_index['lessons'])} bài.")
    print("   → Commit data/ lên GitHub, đặt QUESTION_SOURCE=GITHUB_JSON trên Render để app đọc nhanh.")


if __name__ == "__main__":
    main()
