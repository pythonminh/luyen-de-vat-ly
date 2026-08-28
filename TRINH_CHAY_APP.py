# -*- coding: utf-8 -*-
"""
TRINH_CHAY_APP.py
- Tự cài thư viện còn thiếu.
- Tự thiết lập Google Sheet lần đầu.
- Tự sửa .env.txt/env thành .env.
- Tự nhận hoặc cho chọn/dán service-account JSON.
- Tự tắt server cũ ở cổng 8000.
- Tự mở trình duyệt.
""" 
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Dict, Optional

BASE = Path(__file__).resolve().parent
APP_FILE = BASE / "app.py"
ENV_FILE = BASE / ".env"
CREDS_FILE = BASE / "service-account.json"
REQ_FILE = BASE / "requirements.txt"
PORT = "8000"


def show_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Ứng dụng luyện đề", message)
        root.destroy()
    except Exception:
        print("\nLỖI:", message)


def show_info(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Ứng dụng luyện đề", message)
        root.destroy()
    except Exception:
        print(message)


def install_dependencies() -> None:
    needed = {
        "flask": "Flask",
        "gspread": "gspread",
        "google.oauth2": "google-auth",
        "dotenv": "python-dotenv",
        "requests": "requests",
    }
    missing = []
    for module, package in needed.items():
        try:
            if importlib.util.find_spec(module) is None:
                missing.append(package)
        except (ImportError, ModuleNotFoundError, AttributeError):
            missing.append(package)

    if not missing:
        return

    print("Đang cài thư viện cần thiết, vui lòng chờ...")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQ_FILE)]
    result = subprocess.run(cmd, cwd=str(BASE))
    if result.returncode != 0:
        raise RuntimeError(
            "Không cài được thư viện. Hãy kiểm tra Internet rồi chạy lại."
        )


def read_env(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.is_file():
        return values
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def write_env(values: Dict[str, str]) -> None:
    order = [
        "GOOGLE_SHEET_ID",
        "GOOGLE_CREDENTIALS_FILE",
        "SECRET_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "AI_PROVIDER",
        "AI_ADMIN_PROVIDER",
        "AI_SVIP_PROVIDER",
    ]
    lines = [
        "# Tự tạo bởi TRINH_CHAY_APP.py",
        "# Không đưa file này lên GitHub.",
    ]
    written = set()
    for key in order:
        if values.get(key, ""):
            lines.append(f"{key}={values[key]}")
            written.add(key)
    for key, value in values.items():
        if key not in written and value:
            lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_old_env_files() -> None:
    if ENV_FILE.is_file():
        return
    for name in (".env.txt", "env", "env.txt"):
        candidate = BASE / name
        if candidate.is_file():
            shutil.copy2(candidate, ENV_FILE)
            print(f"Đã tự đổi {name} thành .env")
            return


def extract_sheet_id(raw: str) -> str:
    raw = (raw or "").strip()
    match = re.search(
        r"(?:spreadsheets/d/)([A-Za-z0-9_-]+)",
        raw,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else raw


def parse_service_account_text(text: str) -> dict:
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("JSON phải là một object.")
    if obj.get("type") != "service_account":
        raise ValueError('Thiếu "type": "service_account".')
    if not obj.get("client_email"):
        raise ValueError("Thiếu client_email.")
    if not obj.get("private_key"):
        raise ValueError("Thiếu private_key.")
    return obj


def load_valid_credentials(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8-sig")
        return parse_service_account_text(text)
    except Exception:
        return None


def find_existing_credentials(env: Dict[str, str]) -> Optional[Path]:
    raw = env.get("GOOGLE_CREDENTIALS_FILE", "").strip()
    candidates = []
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = BASE / p
        candidates.append(p)
    candidates.append(CREDS_FILE)

    # Tìm trong thư mục hiện tại và tối đa 2 cấp cha.
    for folder in (BASE, BASE.parent, BASE.parent.parent):
        if folder.exists():
            candidates.extend(folder.glob("*.json"))

    seen = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except Exception:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if load_valid_credentials(path):
            if path.resolve() != CREDS_FILE.resolve():
                shutil.copy2(path, CREDS_FILE)
            return CREDS_FILE
    return None


def setup_dialog(existing: Dict[str, str]) -> Optional[Dict[str, str]]:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext

    result: Dict[str, str] = {}
    selected_path = {"path": None}
    pasted_json = {"text": ""}

    root = tk.Tk()
    root.title("Thiết lập ứng dụng luyện đề")
    root.geometry("760x560")
    root.minsize(720, 520)

    title = tk.Label(
        root,
        text="THIẾT LẬP LẦN ĐẦU",
        font=("Arial", 18, "bold"),
    )
    title.pack(pady=(18, 4))

    note = tk.Label(
        root,
        text=(
            "Nhập ID hoặc đường link Google Sheet, sau đó chọn file "
            "service-account.json hoặc dán nội dung JSON từ Render."
        ),
        wraplength=700,
        justify="left",
    )
    note.pack(pady=(0, 14))

    form = tk.Frame(root)
    form.pack(fill="both", expand=True, padx=24)

    tk.Label(form, text="Google Sheet ID hoặc đường link:", anchor="w").pack(fill="x")
    sheet_var = tk.StringVar(value=existing.get("GOOGLE_SHEET_ID", ""))
    sheet_entry = tk.Entry(form, textvariable=sheet_var, font=("Arial", 11))
    sheet_entry.pack(fill="x", pady=(3, 12))

    tk.Label(form, text="Khóa Google service account:", anchor="w").pack(fill="x")

    status_var = tk.StringVar(value="Chưa chọn file JSON.")
    status = tk.Label(
        form,
        textvariable=status_var,
        anchor="w",
        fg="#334155",
        wraplength=690,
        justify="left",
    )
    status.pack(fill="x", pady=(3, 7))

    buttons = tk.Frame(form)
    buttons.pack(fill="x", pady=(0, 10))

    def choose_json() -> None:
        path = filedialog.askopenfilename(
            title="Chọn service-account.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        p = Path(path)
        try:
            obj = parse_service_account_text(
                p.read_text(encoding="utf-8-sig")
            )
        except Exception as exc:
            messagebox.showerror("File không hợp lệ", str(exc))
            return
        selected_path["path"] = p
        pasted_json["text"] = ""
        status_var.set(
            f"Đã chọn: {p.name}\nService account: {obj.get('client_email', '')}"
        )

    tk.Button(
        buttons,
        text="Chọn file JSON",
        command=choose_json,
        width=20,
    ).pack(side="left", padx=(0, 8))

    def paste_json_window() -> None:
        win = tk.Toplevel(root)
        win.title("Dán GOOGLE_CREDENTIALS_JSON")
        win.geometry("760x500")

        tk.Label(
            win,
            text=(
                "Dán toàn bộ giá trị GOOGLE_CREDENTIALS_JSON từ Render, "
                "bắt đầu bằng { và kết thúc bằng }."
            ),
            wraplength=710,
            justify="left",
        ).pack(padx=18, pady=(14, 8), anchor="w")

        text_box = scrolledtext.ScrolledText(win, wrap="word", font=("Consolas", 10))
        text_box.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        def accept_paste() -> None:
            text = text_box.get("1.0", "end").strip()
            try:
                obj = parse_service_account_text(text)
            except Exception as exc:
                messagebox.showerror("JSON không hợp lệ", str(exc), parent=win)
                return
            pasted_json["text"] = text
            selected_path["path"] = None
            status_var.set(
                "Đã nhận JSON dán từ Render.\n"
                f"Service account: {obj.get('client_email', '')}"
            )
            win.destroy()

        tk.Button(
            win,
            text="Dùng JSON này",
            command=accept_paste,
            font=("Arial", 11, "bold"),
        ).pack(pady=(0, 14))

    tk.Button(
        buttons,
        text="Dán JSON từ Render",
        command=paste_json_window,
        width=22,
    ).pack(side="left")

    tk.Label(
        form,
        text="Key Gemini (không bắt buộc):",
        anchor="w",
    ).pack(fill="x", pady=(8, 0))
    gemini_var = tk.StringVar(value=existing.get("GEMINI_API_KEY", ""))
    tk.Entry(form, textvariable=gemini_var, show="•").pack(fill="x", pady=(3, 8))

    tk.Label(
        form,
        text="Key OpenAI (không bắt buộc):",
        anchor="w",
    ).pack(fill="x")
    openai_var = tk.StringVar(value=existing.get("OPENAI_API_KEY", ""))
    tk.Entry(form, textvariable=openai_var, show="•").pack(fill="x", pady=(3, 12))

    footer = tk.Frame(root)
    footer.pack(fill="x", padx=24, pady=(6, 20))

    def save_and_close() -> None:
        sheet_id = extract_sheet_id(sheet_var.get())
        if not sheet_id:
            messagebox.showerror("Thiếu Google Sheet", "Hãy nhập ID hoặc đường link Google Sheet.")
            return

        existing_creds = load_valid_credentials(CREDS_FILE)
        if pasted_json["text"]:
            try:
                CREDS_FILE.write_text(pasted_json["text"], encoding="utf-8")
            except Exception as exc:
                messagebox.showerror("Không lưu được JSON", str(exc))
                return
        elif selected_path["path"]:
            try:
                shutil.copy2(selected_path["path"], CREDS_FILE)
            except Exception as exc:
                messagebox.showerror("Không sao chép được JSON", str(exc))
                return
        elif not existing_creds:
            messagebox.showerror(
                "Thiếu khóa Google",
                "Hãy chọn file service-account.json hoặc dán JSON từ Render.",
            )
            return

        result.update(
            {
                "GOOGLE_SHEET_ID": sheet_id,
                "GOOGLE_CREDENTIALS_FILE": "service-account.json",
                "SECRET_KEY": existing.get(
                    "SECRET_KEY", "luyen-de-thay-minh-2026"
                ),
                "GEMINI_API_KEY": gemini_var.get().strip(),
                "OPENAI_API_KEY": openai_var.get().strip(),
                "AI_PROVIDER": existing.get("AI_PROVIDER", "GEMINI"),
                "AI_ADMIN_PROVIDER": existing.get("AI_ADMIN_PROVIDER", "OPENAI"),
                "AI_SVIP_PROVIDER": existing.get("AI_SVIP_PROVIDER", "GEMINI"),
            }
        )
        root.destroy()

    tk.Button(
        footer,
        text="LƯU VÀ CHẠY ỨNG DỤNG",
        command=save_and_close,
        font=("Arial", 12, "bold"),
        bg="#2563eb",
        fg="white",
        padx=18,
        pady=8,
    ).pack(side="right")

    def cancel() -> None:
        root.destroy()

    tk.Button(
        footer,
        text="Hủy",
        command=cancel,
        padx=12,
        pady=8,
    ).pack(side="right", padx=(0, 8))

    sheet_entry.focus_set()
    root.mainloop()
    return result or None


def ensure_configuration() -> Dict[str, str]:
    normalize_old_env_files()
    env = read_env(ENV_FILE)

    sheet_id = extract_sheet_id(env.get("GOOGLE_SHEET_ID", ""))
    creds_path = find_existing_credentials(env)

    if sheet_id and creds_path:
        env["GOOGLE_SHEET_ID"] = sheet_id
        env["GOOGLE_CREDENTIALS_FILE"] = "service-account.json"
        env.setdefault("SECRET_KEY", "luyen-de-thay-minh-2026")
        write_env(env)
        return env

    configured = setup_dialog(env)
    if not configured:
        raise RuntimeError("Đã hủy thiết lập.")
    write_env(configured)
    return configured


def test_google_connection(env: Dict[str, str]) -> str:
    import gspread
    from google.oauth2.service_account import Credentials

    sheet_id = extract_sheet_id(env["GOOGLE_SHEET_ID"])
    info = json.loads(CREDS_FILE.read_text(encoding="utf-8-sig"))
    if "private_key" in info:
        info["private_key"] = str(info["private_key"]).replace("\\n", "\n")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.title


def kill_old_server() -> None:
    if os.name != "nt":
        return
    try:
        output = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        ).stdout
        pids = set()
        for line in output.splitlines():
            if "LISTENING" not in line.upper():
                continue
            if not re.search(rf":{PORT}\s", line):
                continue
            parts = line.split()
            if parts and parts[-1].isdigit():
                pids.add(parts[-1])

        for pid in pids:
            subprocess.run(
                ["taskkill", "/PID", pid, "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
    except Exception:
        pass


def open_browser_later() -> None:
    time.sleep(4)
    webbrowser.open(f"http://127.0.0.1:{PORT}")


def run_app(env: Dict[str, str]) -> int:
    child_env = os.environ.copy()
    child_env.update({k: v for k, v in env.items() if v})
    child_env["GOOGLE_CREDENTIALS_FILE"] = str(CREDS_FILE)
    child_env["PORT"] = PORT

    kill_old_server()

    print("\n" + "=" * 72)
    print("ĐANG CHẠY ỨNG DỤNG")
    print(f"Địa chỉ: http://127.0.0.1:{PORT}")
    print("Không đóng cửa sổ này khi đang sử dụng ứng dụng.")
    print("=" * 72 + "\n")

    threading.Thread(target=open_browser_later, daemon=True).start()
    process = subprocess.Popen(
        [sys.executable, str(APP_FILE)],
        cwd=str(BASE),
        env=child_env,
    )
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        return 0


def main() -> int:
    os.chdir(BASE)

    if not APP_FILE.is_file():
        show_error("Bộ cài thiếu app.py.")
        return 1

    try:
        install_dependencies()
        env = ensure_configuration()

        try:
            title = test_google_connection(env)
        except Exception as exc:
            show_error(
                "Không kết nối được Google Sheet.\n\n"
                f"Lỗi: {exc}\n\n"
                "Hãy kiểm tra Sheet đã chia sẻ quyền Editor cho email "
                "client_email trong service-account.json."
            )
            # Mở lại thiết lập vào lần chạy sau.
            return 1

        print(f"Kết nối Google Sheet thành công: {title}")
        return run_app(env)

    except Exception as exc:
        show_error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
