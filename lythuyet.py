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
.lttoc{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px}
.lttoc a{border:1px solid #c9d8e8;background:#fff;color:#173a5e;border-radius:8px;padding:5px 9px;font-size:12px;font-weight:400}
.lttoc a.on{background:#145bb0;color:#fff;border-color:#145bb0}
.ltsec{margin:0 0 18px;padding:14px 16px 16px;border:1px solid #d7e2ee;border-radius:14px;background:#fff}
.ltsec h2{margin:0 0 12px;font-size:18px;font-weight:700;color:#145bb0}
.ltsec h3{margin:16px 0 8px;font-size:15px;font-weight:700;color:#0f3f73}
.ltsec h4{margin:14px 0 6px;font-size:14px;font-weight:700;color:#334155}
.ltbox{margin:14px 0;padding:0;overflow:hidden;border-radius:14px;border:1px solid #d7e2ee;background:#fff;box-shadow:0 1px 2px #0f172a0c,0 10px 28px -18px #0f172a33}
.ltbox .k{display:flex;align-items:center;gap:8px;margin:0;padding:9px 14px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:800;line-height:1.2}
.ltbox .k:before{content:'';flex:0 0 auto;width:26px;height:26px;border-radius:8px;background:center/14px 14px no-repeat #fff;box-shadow:inset 0 0 0 1px #0001}
.ltbox-body{padding:10px 16px 14px;line-height:1.62;color:#1e293b}
.ltbox-body>:first-child{margin-top:0}
.ltbox-body>:last-child{margin-bottom:0}
.ltbox-body ul,.ltbox-body ol{margin:6px 0 4px;padding-left:1.25em}
.ltbox-body li{margin:4px 0}
.lt-hd-title{margin:0 0 8px;font-size:15px;font-weight:700;color:#9a3412}
.ltbox.hd{background:#fff8f1;border-color:#fdba74;border-left:5px solid #ea580c}
.ltbox.hd .k{background:#ffedd5;color:#9a3412}
.ltbox.hd .k:before{background-color:#fff;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ea580c' stroke-width='2.2' stroke-linecap='round'><path d='M4 19h4l10-10-4-4L4 15v4z'/><path d='M13 6l4 4'/></svg>")}
.ltbox.know{background:#f4f9ff;border-color:#93c5fd;border-left:5px solid #2563eb}
.ltbox.know .k{background:#dbeafe;color:#1e40af}
.ltbox.know .k:before{background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2.2' stroke-linecap='round'><path d='M4 5h10a3 3 0 013 3v11H7a3 3 0 00-3 3V5z'/><path d='M20 19V8a3 3 0 00-3-3'/></svg>")}
.ltbox.fun{background:#f7f4ff;border-color:#c4b5fd;border-left:5px solid #7c3aed}
.ltbox.fun .k{background:#ede9fe;color:#5b21b6}
.ltbox.fun .k:before{background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%237c3aed' stroke-width='2.2' stroke-linecap='round'><path d='M9 18h6'/><path d='M10 21h4'/><path d='M12 3a6 6 0 00-3.5 10.8c.6.5 1 1.2 1.1 2.2h4.8c.1-1 .5-1.7 1.1-2.2A6 6 0 0012 3z'/></svg>")}
.ltbox.learned{background:#f3fdf6;border-color:#86efac;border-left:5px solid #16a34a}
.ltbox.learned .k{background:#dcfce7;color:#166534}
.ltbox.learned .k:before{background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2316a34a' stroke-width='2.4' stroke-linecap='round'><path d='M5 12.5l4.2 4.2L19 7.5'/></svg>")}
.ltbox.can{background:#f0fbfd;border-color:#67e8f9;border-left:5px solid #0891b2}
.ltbox.can .k{background:#cffafe;color:#155e75}
.ltbox.can .k:before{background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%230891b2' stroke-width='2.2' stroke-linecap='round'><circle cx='12' cy='12' r='8'/><circle cx='12' cy='12' r='3'/><path d='M12 4v2M12 18v2M4 12h2M18 12h2'/></svg>")}
.ltbox.note{background:#fffbeb;border-color:#fcd34d;border-left:5px solid #d97706}
.ltbox.note .k{background:#fef3c7;color:#92400e}
.ltbox.note .k:before{background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d97706' stroke-width='2.2' stroke-linecap='round'><path d='M12 9v4'/><path d='M12 17h.01'/><path d='M12 4l9 16H3L12 4z'/></svg>")}
.ltbox.example{background:#f8fafc;border-color:#cbd5e1;border-left:5px solid #475569}
.ltbox.example .k{background:#e2e8f0;color:#334155}
.ltbox.example .k:before{background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23475569' stroke-width='2.2' stroke-linecap='round'><circle cx='12' cy='12' r='8'/><path d='M12 8v5'/><path d='M12 16h.01'/></svg>")}
.ltbox.ans{background:#f8fafc;border-color:#cbd5e1;border-left:5px solid #64748b}
.ltbox.ans .k{background:#e2e8f0;color:#334155}
.ltbox.ans .k:before{background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2.2' stroke-linecap='round'><path d='M4 19V7a2 2 0 012-2h9l5 5v9a2 2 0 01-2 2H6a2 2 0 01-2-2z'/><path d='M15 5v4h4'/></svg>")}
.lt-split{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(220px,.85fr);gap:16px;align-items:start;margin:12px 0}
.lt-split>div:last-child{background:#f8fbff;border:1px solid #d7e2ee;border-radius:12px;padding:10px;text-align:center}
.lt-chuy{margin:10px 0;padding:10px 12px 10px 14px;border-radius:10px;border:1px solid #fcd34d;border-left:5px solid #d97706;background:#fffbeb;font-style:italic;color:#78350f}
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
    t = re.sub(r"(?<!\\)%[^\n]*", "", t)
    t = t.replace(r"\%", "%")
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
            box = (
                f"<div class='ltbox {cls}'><div class='k'>{html.escape(label)}</div>"
                f"<div class='ltbox-body'>{inner}</div></div>"
            )
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
        box = (
            f"<div class='ltbox hd'><div class='k'>Hoạt động</div>"
            f"<div class='ltbox-body'><div class='lt-hd-title'>{html.escape(title)}</div>{body}</div></div>"
        )
        s = s[:a] + box + s[e + 7 :]
    s = split_box("@@FUN@@", "@@/FUN@@", "fun", "Em có biết")
    s = split_box("@@SUM1@@", "@@/SUM1@@", "learned", "Em đã học")
    s = split_box("@@SUM2@@", "@@/SUM2@@", "can", "Em có thể")
    s = split_box("@@KNOW@@", "@@/KNOW@@", "know", "Kiến thức cốt lõi")
    s = split_box("@@NOTE@@", "@@/NOTE@@", "note", "Lưu ý")
    s = split_box("@@EX@@", "@@/EX@@", "example", "Ví dụ")
    s = split_box("@@ANS@@", "@@/ANS@@", "ans", "Trả lời")
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
