# -*- coding: utf-8 -*-
"""Kiểm tra nhanh kết nối Google Sheets khi chạy local."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def load_info():
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    filename = os.getenv("GOOGLE_CREDENTIALS_FILE", "").strip()
    if raw:
        return json.loads(raw)
    if filename:
        path = Path(filename)
        if not path.is_absolute():
            path = BASE_DIR / path
        return json.loads(path.read_text(encoding="utf-8"))
    raise RuntimeError("Thiếu GOOGLE_CREDENTIALS_JSON hoặc GOOGLE_CREDENTIALS_FILE trong .env")


def main():
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("Thiếu GOOGLE_SHEET_ID trong .env")

    info = load_info()
    email = info.get("client_email", "")
    if "private_key" in info:
        info["private_key"] = str(info["private_key"]).replace("\\n", "\n")

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)

    print("KẾT NỐI THÀNH CÔNG")
    print("Tên Google Sheet:", sheet.title)
    print("Service account:", email)
    print("Các trang tính:", ", ".join(ws.title for ws in sheet.worksheets()))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("KẾT NỐI THẤT BẠI:", exc)
        print("\nKiểm tra:")
        print("1. .env nằm cùng thư mục với file này.")
        print("2. GOOGLE_SHEET_ID chỉ là đoạn ID giữa /d/ và /edit.")
        print("3. Sheet đã chia sẻ Editor cho client_email trong service-account.json.")
        print("4. Google Sheets API và Google Drive API đã được bật.")
        sys.exit(1)
