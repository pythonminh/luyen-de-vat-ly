# -*- coding: utf-8 -*-
"""Tạo lt.tex / pp.tex cạnh de.tex cho mọi bài. Không ghi đè file đã có nội dung."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "ngan-hang"
INDEX = ROOT / "bank_index.json"
HEADER_RE = re.compile(r"^\s*%\s*(Môn|Lớp|Chương|Bài)\s*:\s*(.+?)\s*$", re.I | re.M)
SKIP_NAMES = {"lt.tex", "pp.tex"}


def clean(v):
    return re.sub(r"\s+", " ", v or "").strip()


def input_rel(lesson_dir: Path) -> str:
    rel = lesson_dir.resolve().relative_to(BANK.resolve())
    return "/".join([".."] * len(rel.parts)) + "/_lenh/lythuyet.tex"


def path_meta(rel: str) -> dict:
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    if parts and parts[0].lower() == "ngan-hang":
        parts = parts[1:]
    r = {
        "Mon": parts[0] if len(parts) > 0 else "",
        "Lop": parts[1] if len(parts) > 1 else "",
        "Chuong": parts[2] if len(parts) > 2 else "",
        "BaiHoc": parts[3] if len(parts) > 3 else "",
    }
    lop = r["Lop"]
    if lop.lower().startswith("lớp "):
        r["Lop"] = lop[4:].strip()
    return r


def header_of(de_path: Path, folder: Path) -> dict:
    text = ""
    try:
        text = de_path.read_text(encoding="utf-8", errors="replace")[:4000]
    except Exception:
        pass
    out = {}
    for m in HEADER_RE.finditer(text):
        k = clean(m.group(1)).lower()
        v = clean(m.group(2))
        key = {"môn": "Mon", "lớp": "Lop", "chương": "Chuong", "bài": "BaiHoc"}.get(k)
        if key and v:
            out[key] = v
    rel = (folder / "de.tex").relative_to(ROOT).as_posix()
    meta = {**path_meta(rel), **out}
    if not meta.get("BaiHoc"):
        meta["BaiHoc"] = folder.name
    return meta


def dang_names(folder_rel: str, index: dict) -> list[str]:
    names = []
    seen = set()
    for x in index.get("lessons") or []:
        p = str(x.get("path") or "").replace("\\", "/")
        if p.rsplit("/", 1)[0] != folder_rel:
            continue
        name = p.rsplit("/", 1)[-1].lower()
        if name in SKIP_NAMES:
            continue
        for k, v in (x.get("dang") or {}).items():
            k = str(k).strip()
            if not k or k in seen:
                continue
            try:
                if int(v or 0) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            seen.add(k)
            names.append(k)
    return names


def write_if_absent(path: Path, body: str) -> bool:
    if path.is_file():
        return False
    path.write_text(body, encoding="utf-8")
    return True


def lt_stub(meta: dict, inp: str) -> str:
    return (
        f"% Môn: {meta.get('Mon') or ''}\n"
        f"% Lớp: {meta.get('Lop') or ''}\n"
        f"% Chương: {meta.get('Chuong') or ''}\n"
        f"% Bài: {meta.get('BaiHoc') or ''}\n"
        "% Loại: Lý thuyết\n"
        "% File riêng, không trộn vào de.tex — thay nội dung khi soạn xong\n"
        f"\\input{{{inp}}}\n\n"
        "\\subsection{Lý thuyết}\n"
        "\\subsubsection{Nội dung}\n"
        "\\textit{Chưa soạn. Viết LaTeX vào file lt.tex này (cùng thư mục với de.tex).}\n"
        "\\begin{kienthuc}\n"
        "Các ý kiến thức cốt lõi của bài.\n"
        "\\end{kienthuc}\n"
        "\\begin{emdahoc}\n"
        "\\begin{itemize}\\item \\end{itemize}\n"
        "\\end{emdahoc}\n"
        "\\begin{emcothe}\n"
        "\\begin{itemize}\\item \\end{itemize}\n"
        "\\end{emcothe}\n"
    )


def pp_stub(meta: dict, inp: str, dangs: list[str]) -> str:
    bits = [
        f"% Môn: {meta.get('Mon') or ''}\n"
        f"% Lớp: {meta.get('Lop') or ''}\n"
        f"% Chương: {meta.get('Chuong') or ''}\n"
        f"% Bài: {meta.get('BaiHoc') or ''}\n"
        "% Loại: Dạng mẫu · phương pháp giải\n"
        "% File riêng pp.tex, không trộn vào de.tex\n"
        f"\\input{{{inp}}}\n\n"
        "\\subsection{Dạng bài tập mẫu}\n"
    ]
    if not dangs:
        dangs = ["Dạng 1"]
    for i, name in enumerate(dangs, 1):
        bits.append(
            f"\\subsubsection{{Dạng {i}. {name}}}\n"
            "\\begin{phuongphap}\n"
            "\\begin{enumerate}\n"
            "\\item Đọc đề, xác định đại lượng đã biết / cần tìm.\n"
            "\\item Ghi công thức hoặc mô hình liên quan.\n"
            "\\item Tính toán và đối chiếu đơn vị, dấu.\n"
            "\\end{enumerate}\n"
            "\\end{phuongphap}\n"
            "\\begin{vidumau}\n"
            "\\textit{Chèn bài mẫu và lời giải (không đưa vào de.tex).}\n"
            "\\end{vidumau}\n\n"
        )
    return "".join(bits)


def main():
    index = {}
    if INDEX.is_file():
        index = json.loads(INDEX.read_text(encoding="utf-8"))
    n_lt = n_pp = 0
    folders = sorted({p.parent for p in BANK.rglob("de.tex") if "_lenh" not in p.parts})
    for folder in folders:
        de = folder / "de.tex"
        meta = header_of(de, folder)
        inp = input_rel(folder)
        rel = folder.relative_to(ROOT).as_posix()
        dangs = dang_names(rel, index)
        if write_if_absent(folder / "lt.tex", lt_stub(meta, inp)):
            n_lt += 1
        if write_if_absent(folder / "pp.tex", pp_stub(meta, inp, dangs)):
            n_pp += 1
    print(f"[OK] tạo mới lt.tex={n_lt} pp.tex={n_pp} (bỏ qua file đã có)")


if __name__ == "__main__":
    main()
