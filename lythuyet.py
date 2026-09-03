# -*- coding: utf-8 -*-
"""Lý thuyết: file lt.tex cạnh de.tex, không đụng ngân hàng câu hỏi."""
from __future__ import annotations

import html
import re
from pathlib import Path

import app as base
from flask import redirect, request

app = base.app
ROOT = Path(base.ROOT)

LT_CSS = """
<style>
.ltpage{max-width:none;width:100%}
.lttoc{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.lttoc a{border:1px solid #c9d8e8;background:#fff;color:#173a5e;border-radius:8px;padding:5px 9px;font-size:12px;font-weight:400}
.lttoc a.on{background:#145bb0;color:#fff;border-color:#145bb0}
.ltsec{margin:0 0 18px;padding:12px 14px;border:1px solid #d7e2ee;border-radius:12px;background:#fff}
.ltsec h2{margin:0 0 10px;font-size:18px;font-weight:700;color:#145bb0}
.ltsec h3{margin:14px 0 8px;font-size:15px;font-weight:600}
.ltsec h4{margin:12px 0 6px;font-size:14px;font-weight:600}
.ltbox{margin:10px 0;padding:10px 12px;border-radius:10px;border:1px solid #d7e2ee}
.ltbox.hd{background:#fff7ed;border-color:#fdba74}
.ltbox.know{background:#f4f9ff;border-color:#b9d5ef}
.ltbox.fun{background:#f5f3ff;border-color:#c4b5fd}
.ltbox.sum{background:#f0fdf4;border-color:#86efac}
.ltbox .k{display:block;font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:#64748b;margin-bottom:6px;font-weight:600}
.lt-split{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(220px,.9fr);gap:14px;align-items:start;margin:10px 0}
.lt-chuy{margin:8px 0;padding:8px 10px;border-left:4px solid #f59e0b;background:#fffbeb;font-style:italic}
@media(max-width:800px){.lt-split{grid-template-columns:1fr}}
</style>
"""


def theory_tex_path(de_path: str) -> str:
    p = str(de_path or "").replace("\\", "/").strip()
    if p.lower().endswith("/lt.tex"):
        return p
    folder = base.lesson_folder(p)
    return folder.rstrip("/") + "/lt.tex"


def theory_exists(de_path: str) -> bool:
    rel = theory_tex_path(de_path)
    local = ROOT / rel
    return local.is_file()


def _grab_group(s: str, i: int):
    while i < len(s) and s[i] in " \t\n\r":
        i += 1
    if i >= len(s) or s[i] != "{":
        return "", i
    depth = 0
    j = i
    while j < len(s):
        if s[j] == "\\" and j + 1 < len(s):
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1 : j], j + 1
        j += 1
    return s[i + 1 :], len(s)


def _replace_macro_two(s: str, name: str, wrap):
    token = "\\" + name
    out = []
    i = 0
    while True:
        j = s.find(token, i)
        if j < 0:
            out.append(s[i:])
            break
        if j > 0 and s[j - 1] == "\\":
            out.append(s[i : j + 1])
            i = j + 1
            continue
        out.append(s[i:j])
        a, k = _grab_group(s, j + len(token))
        b, k2 = _grab_group(s, k)
        out.append(wrap(a, b))
        i = k2
    return "".join(out)


def _replace_macro_one(s: str, name: str, wrap):
    token = "\\" + name
    out = []
    i = 0
    n = len(token)
    while True:
        j = s.find(token, i)
        if j < 0:
            out.append(s[i:])
            break
        nxt = s[j + n : j + n + 1] if j + n < len(s) else ""
        if nxt.isalpha():
            out.append(s[i : j + n])
            i = j + n
            continue
        out.append(s[i:j])
        body, k = _grab_group(s, j + n)
        out.append(wrap(body))
        i = k
    return "".join(out)


def _replace_env(s: str, name: str, wrap, titled=False):
    open_re = re.compile(r"\\begin\s*\{\s*" + re.escape(name) + r"\s*\}", re.I)
    close_re = re.compile(r"\\end\s*\{\s*" + re.escape(name) + r"\s*\}", re.I)
    out = []
    i = 0
    while True:
        m = open_re.search(s, i)
        if not m:
            out.append(s[i:])
            break
        out.append(s[i : m.start()])
        k = m.end()
        title = ""
        if titled:
            title, k = _grab_group(s, k)
        depth = 1
        j = k
        body_end = len(s)
        while j < len(s) and depth:
            m_open = open_re.search(s, j)
            m_close = close_re.search(s, j)
            if not m_close:
                j = len(s)
                break
            if m_open and m_open.start() < m_close.start():
                depth += 1
                j = m_open.end()
                continue
            depth -= 1
            if depth == 0:
                body_end = m_close.start()
                j = m_close.end()
                break
            j = m_close.end()
        body = s[k:body_end]
        out.append(wrap(title, body) if titled else wrap(body))
        i = j
    return "".join(out)


def _html(chunk: str) -> str:
    t = chunk or ""
    t = re.sub(r"%[^\n]*", "", t)
    t = re.sub(r"\\Blythuyet\b", "", t)
    t = re.sub(r"\\captionof\s*\{figure\}\s*\{([^{}]*)\}", r"\n\\textbf{Hình: \1}\n", t)
    t = re.sub(r"\\label\s*\{[^{}]*\}", "", t)
    t = re.sub(r"\\ref\s*\{[^{}]*\}", "hình trên", t)
    t = t.replace("\\centering", "")
    return base.html_question(t)


def preprocess(s: str) -> str:
    s = s.replace("\r\n", "\n")
    s = re.sub(r"\\input\s*\{[^{}]*lythuyet\.tex\}", "", s)
    s = _replace_macro_one(s, "indam", lambda b: r"\textbf{" + b + "}")
    s = _replace_macro_one(s, "chuy", lambda b: "\n@@CHUY@@" + b + "@@/CHUY@@\n")
    s = _replace_macro_one(s, "luuy", lambda b: "\n@@NOTE@@" + b + "@@/NOTE@@\n")
    s = _replace_macro_one(s, "ghichu", lambda b: "\n@@NOTE@@" + b + "@@/NOTE@@\n")
    s = _replace_macro_one(s, "vidu", lambda b: "\n@@EX@@" + b + "@@/EX@@\n")
    s = _replace_macro_two(
        s,
        "kienthuccot",
        lambda a, b: "\n@@SPLIT@@" + a + "@@MID@@" + b + "@@/SPLIT@@\n",
    )
    s = _replace_macro_two(
        s,
        "haicotchay",
        lambda a, b: "\n@@SPLIT@@" + a + "@@MID@@" + b + "@@/SPLIT@@\n",
    )
    s = _replace_env(s, "hoatdong", lambda t, b: "\n@@HD:" + t + "@@" + b + "@@/HD@@\n", titled=True)
    s = _replace_env(s, "emcobiet", lambda b: "\n@@FUN@@" + b + "@@/FUN@@\n")
    s = _replace_env(s, "emdahoc", lambda b: "\n@@SUM1@@" + b + "@@/SUM1@@\n")
    s = _replace_env(s, "emcothe", lambda b: "\n@@SUM2@@" + b + "@@/SUM2@@\n")
    s = _replace_env(s, "kienthuc", lambda b: "\n@@KNOW@@" + b + "@@/KNOW@@\n")
    s = _replace_env(s, "traloi", lambda b: "\n@@ANS@@" + b + "@@/ANS@@\n")
    return s


def _flush_tokens(s: str) -> str:
    def split_box(tok_open, tok_close, cls, label):
        nonlocal s
        while tok_open in s:
            a = s.find(tok_open)
            b = s.find(tok_close, a)
            if b < 0:
                break
            inner = s[a + len(tok_open) : b]
            box = f"<div class='ltbox {cls}'><span class='k'>{html.escape(label)}</span>{inner}</div>"
            s = s[:a] + box + s[b + len(tok_close) :]
        return s

    while "@@SPLIT@@" in s:
        a = s.find("@@SPLIT@@")
        m = s.find("@@MID@@", a)
        e = s.find("@@/SPLIT@@", m if m > 0 else a)
        if m < 0 or e < 0:
            break
        left, right = s[a + 9 : m], s[m + 7 : e]
        block = f"<div class='lt-split'><div>{left}</div><div>{right}</div></div>"
        s = s[:a] + block + s[e + 10 :]
    while "@@CHUY@@" in s:
        a = s.find("@@CHUY@@")
        e = s.find("@@/CHUY@@", a)
        if e < 0:
            break
        s = s[:a] + f"<p class='lt-chuy'>{s[a + 8 : e]}</p>" + s[e + 9 :]
    while "@@HD:" in s:
        a = s.find("@@HD:")
        mid = s.find("@@", a + 5)
        e = s.find("@@/HD@@", mid if mid > 0 else a)
        if mid < 0 or e < 0:
            break
        title = s[a + 5 : mid]
        body = s[mid + 2 : e]
        box = f"<div class='ltbox hd'><span class='k'>Hoạt động</span><b>{html.escape(title)}</b>{body}</div>"
        s = s[:a] + box + s[e + 7 :]
    s = split_box("@@FUN@@", "@@/FUN@@", "fun", "Em có biết")
    s = split_box("@@SUM1@@", "@@/SUM1@@", "sum", "Em đã học")
    s = split_box("@@SUM2@@", "@@/SUM2@@", "sum", "Em có thể")
    s = split_box("@@KNOW@@", "@@/KNOW@@", "know", "Kiến thức cốt lõi")
    s = split_box("@@NOTE@@", "@@/NOTE@@", "hd", "Lưu ý")
    s = split_box("@@EX@@", "@@/EX@@", "know", "Ví dụ")
    s = split_box("@@ANS@@", "@@/ANS@@", "sum", "Trả lời")
    return s


def parse_theory(tex: str):
    raw = preprocess(tex or "")
    parts = re.split(r"\\subsubsection\s*\{([^{}]*)\}", raw)
    secs = []
    preamble = parts[0] if parts else ""
    preamble = re.sub(r"\\subsection\s*\{[^{}]*\}", "", preamble)
    body = _flush_tokens(_html_or_tokens(preamble))
    if re.sub(r"<[^>]+>", "", body).strip():
        secs.append({"title": "Khởi động", "html": body, "id": "lt0"})
    idx = 1
    for i in range(1, len(parts), 2):
        title = (parts[i] or "").strip() or f"Mục {idx}"
        chunk = parts[i + 1] if i + 1 < len(parts) else ""
        chunk = re.sub(
            r"\\paragraph\s*\{([^{}]*)\}",
            lambda m: "\n@@H3@@" + m.group(1) + "@@/H3@@\n",
            chunk,
        )
        chunk = re.sub(
            r"\\subparagraph\s*\{([^{}]*)\}",
            lambda m: "\n@@H4@@" + m.group(1) + "@@/H4@@\n",
            chunk,
        )
        html_body = _flush_tokens(_html_or_tokens(chunk))
        html_body = re.sub(
            r"@@H3@@(.*?)@@/H3@@",
            lambda m: f"<h3>{html.escape(m.group(1))}</h3>",
            html_body,
            flags=re.S,
        )
        html_body = re.sub(
            r"@@H4@@(.*?)@@/H4@@",
            lambda m: f"<h4>{html.escape(m.group(1))}</h4>",
            html_body,
            flags=re.S,
        )
        secs.append({"title": title, "html": html_body, "id": f"lt{idx}"})
        idx += 1
    return secs


def _html_or_tokens(chunk: str) -> str:
    """Keep @@ tokens, convert the rest with latex_to_web in pieces."""
    bits = re.split(
        r"(@@(?:SPLIT|CHUY|HD:[^@]+|FUN|SUM1|SUM2|KNOW|NOTE|EX|ANS|H3|H4)@@|@@/(?:SPLIT|CHUY|HD|FUN|SUM1|SUM2|KNOW|NOTE|EX|ANS|H3|H4)@@|@@MID@@)",
        chunk,
    )
    out = []
    for b in bits:
        if not b:
            continue
        if b.startswith("@@"):
            out.append(b)
        else:
            out.append(_html(b))
    return "".join(out)


def page_theory(de_path: str):
    m = base.member_current()
    de_path = str(de_path or "").strip()
    if not de_path or not base.can_view(m, de_path):
        if not m:
            return redirect(base.login_url("/member/ly-thuyet?path=" + de_path))
        return redirect("/member")
    lt = theory_tex_path(de_path)
    try:
        _, tex = base.read_tex(lt)
    except Exception as e:
        return base.page(
            "Lý thuyết",
            f"<div class='wrap'><div class='panel'><div class='body err'>Chưa có file lt.tex. {html.escape(str(e))}</div>"
            f"<p><a class='btn' href='/member/select?path={html.escape(de_path, quote=True)}'>← Luyện đề</a></p></div></div></div>",
        )
    secs = parse_theory(tex)
    toc = "".join(
        f"<a href='#{s['id']}'>{html.escape(s['title'])}</a>" for s in secs
    )
    blocks = "".join(
        f"<section class='ltsec' id='{s['id']}'><h2>{html.escape(s['title'])}</h2>{s['html']}</section>"
        for s in secs
    ) or "<p class='muted'>Chưa tách được mục. Kiểm tra \\subsubsection trong lt.tex.</p>"
    title = ""
    for x in base.index_data().get("lessons") or []:
        if str(x.get("path") or x.get("file") or "") == de_path:
            title = str(x.get("BaiHoc") or x.get("De") or "")
            break
    qhref = "/member/select?path=" + html.escape(de_path, quote=True)
    body = (
        LT_CSS
        + "<div class='wrap ltpage'>"
        + f"<div class='panel'><div class='head'>📖 Lý thuyết · {html.escape(title or 'Bài')}</div><div class='body'>"
        + f"<p><a class='btn primary' href='{qhref}'>▶ Luyện đề bài này</a></p>"
        + f"<nav class='lttoc'>{toc}</nav>{blocks}</div></div></div>"
    )
    return base.page("Lý thuyết", body)


@app.get("/member/ly-thuyet")
def member_ly_thuyet():
    return page_theory(request.args.get("path") or "")
