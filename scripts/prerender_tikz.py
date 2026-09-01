# -*- coding: utf-8 -*-
"""Vẽ sẵn mọi hình TikZ trong ngan-hang thành PNG cache.

Chạy trên máy có TeX Live rồi commit data/tikz-cache/*.png:
    python scripts/prerender_tikz.py
Nhờ vậy Render chỉ việc trả ảnh có sẵn, không phải gọi dịch vụ biên dịch.

Script đi qua đúng pipeline hiển thị của app (parse_questions → html_question)
nên mã hash của ảnh trùng khớp với hash mà trang web yêu cầu.
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402


def walk_bank():
    """Dựng HTML mọi câu để app tự ghi mã TikZ vào cache, trả về hash cần có."""
    for old in app.TIKZ_CACHE.glob('*.tex'):
        old.unlink()
    files = sorted((ROOT / 'ngan-hang').rglob('*.tex'))
    for i, tex in enumerate(files, 1):
        try:
            questions = app.parse_questions(tex.read_text(encoding='utf-8', errors='replace'))
        except Exception as exc:
            print(f'  bỏ qua {tex.parent.name}: {exc}')
            continue
        for q in questions:
            chunks = [q.get('text') or '', q.get('solution') or '']
            for opt in (q.get('options') or []) + (q.get('statements') or []):
                chunks.append(opt.get('text') if isinstance(opt, dict) else str(opt))
            for chunk in chunks:
                if '\\begin{tikzpicture}' in chunk or 'tikzpicture' in chunk:
                    app.html_question(chunk)
        if i % 25 == 0:
            print(f'  đọc {i}/{len(files)} file')
    return {p.stem for p in app.TIKZ_CACHE.glob('*.tex')}


def main():
    if not app.pdflatex_bin():
        print('Không tìm thấy pdflatex. Cài TeX Live rồi chạy lại.')
        return 1

    app.TIKZ_CACHE.mkdir(parents=True, exist_ok=True)
    print('Quét ngân hàng...')
    wanted = walk_bank()

    orphans = [p for p in app.TIKZ_CACHE.glob('*.png') if p.stem not in wanted]
    for p in orphans:
        p.unlink()
    if orphans:
        print(f'Xóa {len(orphans)} ảnh cũ không còn dùng.')

    todo = sorted(h for h in wanted if not app.tikz_png_path(h).is_file())
    print(f'Tổng {len(wanted)} hình · đã có {len(wanted) - len(todo)} · cần vẽ {len(todo)}')
    if not todo:
        return 0

    done = 0
    failures = []

    def build(hid):
        path, err = app.tikz_build_png(hid, allow_cloud=False)
        return hid, path, err

    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, (hid, path, err) in enumerate(pool.map(build, todo), 1):
            if path:
                done += 1
            else:
                failures.append((hid, err))
            if i % 20 == 0:
                print(f'  ...{i}/{len(todo)}')

    print(f'Xong: vẽ được {done}, lỗi {len(failures)}. Ảnh nằm ở data/tikz-cache/')
    for hid, err in failures:
        print(f'  LỖI {hid} · {err}')
        print(f'       mã nguồn: data/tikz-cache/{hid}.tex')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
