# -*- coding: utf-8 -*-
"""Vẽ sẵn mọi hình TikZ trong ngan-hang thành PNG cache.

Chạy trên máy có TeX Live rồi commit data/tikz-cache/*.png:
    python scripts/prerender_tikz.py
Nhờ vậy Render chỉ việc trả ảnh có sẵn, không phải gọi dịch vụ biên dịch.
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402


def collect_figures():
    seen = {}
    for tex in sorted((ROOT / 'ngan-hang').rglob('*.tex')):
        try:
            content = tex.read_text(encoding='utf-8', errors='replace')
        except Exception as exc:
            print(f'  bỏ qua {tex.name}: {exc}')
            continue
        for m in app.TIKZ_RE.finditer(content):
            src = m.group(0).strip()
            seen.setdefault(app.tikz_hash(src), src)
    return seen


def main():
    if not app.pdflatex_bin():
        print('Không tìm thấy pdflatex. Cài TeX Live rồi chạy lại.')
        return 1
    figures = collect_figures()
    todo = {h: s for h, s in figures.items() if not app.tikz_png_path(h).is_file()}
    print(f'Tổng {len(figures)} hình · đã có {len(figures) - len(todo)} · cần vẽ {len(todo)}')
    if not todo:
        return 0

    done = failed = 0

    def build(item):
        hid, src = item
        app.tikz_remember(src)
        path, err = app.tikz_build_png(hid, src, allow_cloud=False)
        return hid, path, err

    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, (hid, path, err) in enumerate(pool.map(build, todo.items()), 1):
            if path:
                done += 1
            else:
                failed += 1
                print(f'  [{i}/{len(todo)}] {hid[:10]} lỗi: {err}')
            if i % 10 == 0:
                print(f'  ...{i}/{len(todo)}')

    print(f'Xong: vẽ được {done}, lỗi {failed}. Ảnh nằm ở data/tikz-cache/')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
