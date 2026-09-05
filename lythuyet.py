# -*- coding: utf-8 -*-
"""Lý thuyết: file lt.tex cạnh de.tex, không đụng ngân hàng câu hỏi."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import app as base
from flask import jsonify, redirect, request

app = base.app
ROOT = Path(base.ROOT)
STATUS_FILE = ROOT / "companion_status.json"

LT_CSS = """
<style>
.ltpage{max-width:none;width:100%}
.ltnav{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px;position:relative;z-index:6}
.lttoc{margin:0 0 14px;max-width:min(100%,720px)}
.lttoc label{display:block;font-size:12px;color:#64748b;margin:0 0 5px;font-weight:600}
.lttoc select{width:100%;padding:9px 12px;border:1px solid #c9d8e8;border-radius:10px;background:#fff;color:#173a5e;font-size:14px;line-height:1.35}
.ltsec{margin:0 0 18px;padding:14px 16px 16px;border:1px solid #d7e2ee;border-radius:14px;background:#fff;scroll-margin-top:110px}
.ltsec-h{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start;justify-content:space-between;margin:0 0 12px}
.ltsec-h h2,.ltsec h2{margin:0;font-size:18px;font-weight:700;color:#145bb0;flex:1}
.ltsec-tools{display:flex;gap:6px;flex-wrap:wrap;flex:0 0 auto}
.ltsec-tools .btn{font-size:13px;padding:6px 10px;white-space:nowrap}
.ltsecedit{margin-top:10px;padding:10px 12px;border:1px dashed #7dd3fc;border-radius:10px;background:#f0f9ff}
.ltsecedit .rwta{width:100%;min-height:240px;font:13px/1.45 Consolas,ui-monospace,monospace;padding:8px;border:1px solid #7dd3fc;border-radius:8px;margin:4px 0 8px}
.lt-title-in{width:100%;padding:8px 10px;border:1px solid #7dd3fc;border-radius:8px;margin:4px 0 8px;font-size:15px;box-sizing:border-box}
.ltsecedit .rwlook{margin:8px 0;padding:10px;border:1px dashed #bae6fd;border-radius:8px;background:#fff}
.ltsec h3{margin:16px 0 8px;font-size:15px;font-weight:700;color:#0f3f73}
.ltsec h4{margin:14px 0 6px;font-size:14px;font-weight:700;color:#334155}
.ltbox{margin:14px 0;padding:0;overflow:hidden;border-radius:14px;border:1px solid #d7e2ee;background:#fff;box-shadow:0 1px 2px #0f172a0c,0 10px 28px -18px #0f172a33}
.ltbox .k{display:flex;align-items:center;gap:8px;margin:0;padding:9px 14px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:800;line-height:1.2}
.ltbox .k:before{content:'';flex:0 0 auto;width:26px;height:26px;border-radius:8px;background:center/14px 14px no-repeat #fff;box-shadow:inset 0 0 0 1px #0001}
.ltbox-body{padding:10px 16px 14px;line-height:1.62;color:#1e293b}
.ltbox-body>:first-child{margin-top:0}
.lt-math{margin:10px 0;overflow-x:auto;padding:4px 0}
.ltsec-tools .btn.primary{background:#145bb0;color:#fff;border:0}
.ltbox-body ul{margin:6px 0 4px;padding-left:1.35em}
.ltbox-body ol,ol.tex-list{list-style:none;counter-reset:ltn;margin:8px 0 6px;padding:0}
.ltbox-body ol>li,ol.tex-list>li{position:relative;margin:8px 0;padding:2px 0 2px 2.45em;line-height:1.55}
.ltbox-body ol>li::before,ol.tex-list>li::before{content:counter(ltn);counter-increment:ltn;position:absolute;left:0;top:.12em;width:1.65em;height:1.65em;border:1.5px solid #145bb0;border-radius:50%;background:#fff;color:#145bb0;font:800 12px/1.65em Segoe UI,Arial,sans-serif;text-align:center;box-sizing:border-box}
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
.lt-chuy ul,.lt-chuy ol{margin:6px 0 0;padding-left:1.3em}
.lt-q{margin:4px 0}
.lt-opts{display:grid;gap:6px;margin:10px 0 8px}
.lt-opt{display:flex;align-items:flex-start;gap:8px;padding:8px 10px;border:1px solid #d7e2ee;border-radius:10px;background:#fff}
.lt-opt.ok{border-color:#86efac;background:#f0fdf4}
.lt-let{flex:0 0 1.6em;width:1.6em;height:1.6em;border-radius:999px;background:#e2e8f0;color:#334155;font-weight:800;font-size:12px;display:inline-flex;align-items:center;justify-content:center}
.lt-opt.ok .lt-let{background:#16a34a;color:#fff}
.lt-key{margin-left:auto;font-size:11px;font-weight:800;color:#166534;white-space:nowrap}
.lt-sol{margin:10px 0 0;padding:8px 10px;border:1px solid #bad5f2;border-radius:10px;background:#f7fbff}
.lt-sol summary{cursor:pointer;font-weight:800;color:#145bb0}
.lt-sol div{margin-top:8px}
.lt-short{margin:8px 0;font-weight:700}
@media(max-width:800px){.lt-split{grid-template-columns:1fr}}
</style>
"""


TRACKS = {
    "lt": {
        "file": "lt.tex",
        "route": "/member/ly-thuyet",
        "label": "Lý thuyết",
        "icon": "📖",
    },
    "pp": {
        "file": "pp.tex",
        "route": "/member/phuong-phap",
        "label": "Dạng mẫu",
        "icon": "✏️",
    },
}


def companion_path(de_path: str, kind: str = "lt") -> str:
    spec = TRACKS.get(kind) or TRACKS["lt"]
    p = str(de_path or "").replace("\\", "/").strip()
    if p.lower().endswith("/" + spec["file"]):
        return p
    folder = base.lesson_folder(p)
    return folder.rstrip("/") + "/" + spec["file"]


def companion_exists(de_path: str, kind: str = "lt") -> bool:
    return (ROOT / companion_path(de_path, kind)).is_file()


def theory_tex_path(de_path: str) -> str:
    return companion_path(de_path, "lt")


def theory_exists(de_path: str) -> bool:
    return companion_exists(de_path, "lt")


def _folder_key(de_path: str) -> str:
    return base.lesson_folder(de_path).replace("\\", "/").strip("/")


def _kind_of_file(path: str) -> str:
    name = str(path or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name == "pp.tex":
        return "pp"
    return "lt"


def status_data():
    d = base.load_json(STATUS_FILE, {"lessons": {}})
    d.setdefault("lessons", {})
    return d


def save_status(data, message="ADMIN duyệt lý thuyết / dạng mẫu"):
    base.save_json_github(STATUS_FILE, data, "companion_status.json", message)


def is_approved(de_path: str, kind: str = "lt") -> bool:
    folder = _folder_key(de_path)
    rec = (status_data().get("lessons") or {}).get(folder) or {}
    st = str((rec.get(kind) or {}).get("status") or "pending").strip().lower()
    return st == "approved"


def set_status(de_path: str, kind: str, approved: bool):
    folder = _folder_key(de_path)
    d = status_data()
    lessons = d.setdefault("lessons", {})
    rec = lessons.setdefault(folder, {})
    rec[kind] = {
        "status": "approved" if approved else "pending",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_status(d, "ADMIN " + ("duyệt" if approved else "gỡ duyệt") + f" {kind} " + folder)


def companion_visible(de_path: str, kind: str = "lt", for_admin: bool = False) -> bool:
    if not companion_exists(de_path, kind):
        return False
    if is_approved(de_path, kind):
        return True
    return bool(for_admin)


def looks_like_stub(de_path: str, kind: str = "lt") -> bool:
    p = ROOT / companion_path(de_path, kind)
    if not p.is_file():
        return True
    try:
        t = p.read_text(encoding="utf-8", errors="replace")[:2500]
    except Exception:
        return True
    return "Chưa soạn" in t or "Chèn bài mẫu" in t


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


def _html_tex(chunk: str) -> str:
    t = chunk or ""
    t = re.sub(r"(?<!\\)%[^\n]*", "", t)
    t = t.replace(r"\%", "%")
    t = re.sub(r"\\Blythuyet\b", "", t)
    t = re.sub(r"\\captionof\s*\{figure\}\s*\{([^{}]*)\}", r"\n\\textbf{Hình: \1}\n", t)
    t = re.sub(r"\\label\s*\{[^{}]*\}", "", t)
    t = re.sub(r"(?i)hình\s*\\ref\s*\{[^{}]*\}", "hình bên", t)
    t = re.sub(r"\\ref\s*\{[^{}]*\}", "hình bên", t)
    t = t.replace("\\centering", "")
    return base.html_question(t)


def _html(chunk: str) -> str:
    t = chunk or ""
    if re.search(r"\\(?:choiceTF|choice|shortans|loigiai)\b", t, re.I):
        return _html_quiz(t)
    return _html_tex(t)


def _html_quiz(chunk: str) -> str:
    """Render \\choice / \\choiceTF / \\shortans / \\loigiai like a bank question."""
    b = chunk or ""
    sol = base.solution_of(b)
    if not (sol or "").strip():
        m = re.search(
            r"\\begin\s*\{\s*loigiai\s*\}(.*?)\\end\s*\{\s*loigiai\s*\}",
            b,
            flags=re.I | re.S,
        )
        if m:
            sol = m.group(1)
    opts_html = ""
    letters = "ABCD"
    if re.search(r"\\choiceTF\b", b, re.I):
        rows = []
        for i, x in enumerate(base.command_args(b, "\\choiceTF")):
            ok = bool(re.match(r"^\\True\b", x.strip(), re.I))
            txt = re.sub(r"^\\True\s*", "", x.strip(), flags=re.I)
            mark = "Đúng" if ok else "Sai"
            cls = " ok" if ok else ""
            rows.append(
                f"<div class='lt-opt{cls}'><b>{i + 1}.</b> {_html_tex(txt)} "
                f"<span class='lt-key'>{mark}</span></div>"
            )
        opts_html = "<div class='lt-opts'>" + "".join(rows) + "</div>"
        stem = re.split(r"\\choiceTF\b|\\loigiai\b|\\begin\s*\{\s*loigiai", b, 1, flags=re.I)[0]
    elif re.search(r"\\choice\b", b, re.I):
        rows = []
        for i, x in enumerate(base.command_args(b, "\\choice")[:4]):
            ok = bool(re.match(r"^\\True\b", x.strip(), re.I))
            txt = re.sub(r"^\\True\s*", "", x.strip(), flags=re.I)
            let = letters[i] if i < 4 else str(i + 1)
            cls = " ok" if ok else ""
            rows.append(
                f"<div class='lt-opt{cls}'><span class='lt-let'>{let}</span> {_html_tex(txt)}</div>"
            )
        opts_html = "<div class='lt-opts'>" + "".join(rows) + "</div>"
        stem = re.split(r"\\choice\b|\\loigiai\b|\\begin\s*\{\s*loigiai", b, 1, flags=re.I)[0]
    else:
        stem = re.split(r"\\shortans\b|\\loigiai\b|\\begin\s*\{\s*loigiai", b, 1, flags=re.I)[0]
        sm = re.search(r"\\shortans\s*(?:\[[^\]]*\])?\s*", b, re.I)
        if sm:
            ans, _ = base.get_braced(b, sm.end())
            if ans:
                opts_html = f"<p class='lt-short'><b>Đáp án:</b> {_html_tex(ans)}</p>"
    stem_html = _html_tex(base.strip_loigiai(stem))
    sol_html = ""
    if (sol or "").strip():
        sol_html = (
            "<details class='lt-sol' open><summary>Lời giải</summary>"
            f"<div>{_html_tex(sol)}</div></details>"
        )
    return f"<div class='lt-q'>{stem_html}{opts_html}{sol_html}</div>"


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
    s = _replace_env(s, "dangmau", lambda t, b: "\n@@HD:" + t + "@@" + b + "@@/HD@@\n", titled=True)
    s = _replace_env(s, "emcobiet", lambda b: "\n@@FUN@@" + b + "@@/FUN@@\n")
    s = _replace_env(s, "emdahoc", lambda b: "\n@@SUM1@@" + b + "@@/SUM1@@\n")
    s = _replace_env(s, "emcothe", lambda b: "\n@@SUM2@@" + b + "@@/SUM2@@\n")
    s = _replace_env(s, "kienthuc", lambda b: "\n@@KNOW@@" + b + "@@/KNOW@@\n")
    s = _replace_env(s, "traloi", lambda b: "\n@@ANS@@" + b + "@@/ANS@@\n")
    s = _replace_env(s, "phuongphap", lambda b: "\n@@METH@@" + b + "@@/METH@@\n")
    s = _replace_env(s, "vidumau", lambda b: "\n@@SAMPLE@@" + b + "@@/SAMPLE@@\n")
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
        s = s[:a] + f"<div class='lt-chuy'>{s[a + 8 : e]}</div>" + s[e + 9 :]
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
    s = split_box("@@METH@@", "@@/METH@@", "know", "Phương pháp giải")
    s = split_box("@@SAMPLE@@", "@@/SAMPLE@@", "example", "Bài mẫu")
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
        r"(@@(?:SPLIT|CHUY|HD:[^@]+|FUN|SUM1|SUM2|KNOW|NOTE|EX|ANS|METH|SAMPLE|H3|H4)@@|@@/(?:SPLIT|CHUY|HD|FUN|SUM1|SUM2|KNOW|NOTE|EX|ANS|METH|SAMPLE|H3|H4)@@|@@MID@@)",
        chunk,
    )
    out = []
    mode = ""
    for b in bits:
        if not b:
            continue
        if b == "@@SAMPLE@@" or b == "@@EX@@":
            mode = "quiz"
            out.append(b)
            continue
        if b in ("@@/SAMPLE@@", "@@/EX@@"):
            mode = ""
            out.append(b)
            continue
        if b.startswith("@@"):
            out.append(b)
        elif mode == "quiz":
            out.append(_html_quiz(b))
        else:
            out.append(_html(b))
    return "".join(out)


def page_companion(de_path: str, kind: str = "lt"):
    spec = TRACKS.get(kind) or TRACKS["lt"]
    m = base.member_current()
    de_path = str(de_path or "").strip()
    if not de_path or not base.can_view(m, de_path):
        if not m:
            return redirect(base.login_url(spec["route"] + "?path=" + de_path))
        return redirect("/member")
    rel = companion_path(de_path, kind)
    admin = bool(base.has_full_bank_access(m))
    if not companion_exists(de_path, kind):
        return base.page(
            spec["label"],
            f"<div class='wrap'><div class='panel'><div class='body err'>Chưa có file {html.escape(spec['file'])}.</div>"
            f"<p><a class='btn' href='/member/select?path={html.escape(de_path, quote=True)}'>← Luyện đề</a></p></div></div></div>",
        )
    if not is_approved(de_path, kind) and not admin:
        return base.page(
            spec["label"],
            "<div class='wrap'><div class='panel'><div class='head'>"
            + html.escape(spec["icon"] + " " + spec["label"])
            + "</div><div class='body'><p>Nội dung đang chờ ADMIN soạn và duyệt. Học viên sẽ thấy khi được duyệt.</p>"
            f"<p><a class='btn' href='/member/select?path={html.escape(de_path, quote=True)}'>← Luyện đề</a></p></div></div></div>",
        )
    try:
        _, tex = base.read_tex(rel)
    except Exception as e:
        return base.page(
            spec["label"],
            f"<div class='wrap'><div class='panel'><div class='body err'>Chưa có file {html.escape(spec['file'])}. {html.escape(str(e))}</div>"
            f"<p><a class='btn' href='/member/select?path={html.escape(de_path, quote=True)}'>← Luyện đề</a></p></div></div></div>",
        )
    secs, blocks = _section_blocks_html(tex, admin=admin)
    nsec = len(secs)
    opts = "".join(
        f"<option value='{html.escape(s['id'], quote=True)}'>{html.escape(s['title'])}</option>"
        for s in secs
    )
    toc = (
        f"<nav class='lttoc'><label for='ltjump'>Mục lục · {nsec} mục</label>"
        f"<select id='ltjump'><option value=''>Chọn mục để xem…</option>{opts}</select></nav>"
        "<script>(function(){var s=document.getElementById('ltjump');if(!s)return;"
        "s.addEventListener('change',function(){if(!this.value)return;var el=document.getElementById(this.value);"
        "if(el){history.replaceState(null,'','#'+this.value);el.scrollIntoView({behavior:'smooth',block:'start'});}});"
        "})();</script>"
    )
    if not blocks.strip():
        blocks = (
            f"<p class='muted'>Chưa tách được mục. Kiểm tra \\subsubsection trong {html.escape(spec['file'])}.</p>"
        )
    folder = base.lesson_folder(de_path)
    title = ""
    for x in base.index_data().get("lessons") or []:
        p = str(x.get("path") or x.get("file") or "")
        if base.lesson_folder(p) == folder and base.is_bank_question_tex(p):
            title = str(x.get("BaiHoc") or x.get("De") or "")
            if str(p).replace("\\", "/").lower().endswith("/de.tex"):
                break
    qhref = "/member/select?path=" + html.escape(de_path, quote=True)
    nav = []
    for k, meta in TRACKS.items():
        if not companion_visible(de_path, k, for_admin=admin):
            continue
        href = meta["route"] + "?path=" + html.escape(de_path, quote=True)
        on = " primary" if k == kind else ""
        nav.append(f"<a class='btn{on}' href='{href}'>{html.escape(meta['icon'] + ' ' + meta['label'])}</a>")
    nav.append(f"<a class='btn' href='{qhref}'>▶ Luyện đề</a>")
    if admin:
        fp = companion_path(de_path, kind)
        nav.append(f"<a class='btn' href='/admin/edit?path={quote(fp, safe='')}'>✏️ Sửa file TEX</a>")
        nav.append("<a class='btn' href='/admin/ly-thuyet'>📋 Duyệt</a>")
    banner = ""
    if admin:
        fp = companion_path(de_path, kind)
        if not is_approved(de_path, kind):
            banner = (
                "<div class='notice' style='margin-bottom:10px'><b>ADMIN xem trước.</b> "
                "Học viên chưa thấy mục này.<br>"
                "<b>Sửa từng mục:</b> <b>✏️ Sửa mục</b> hoặc <b>✍️ AI viết lại mục</b> "
                "(LaTeX → Xem trước → Chấp nhận ghi GitHub, giống câu hỏi). "
                "Có thể thêm/xóa <code>\\subsubsection</code>. Ghi xong vào <b>📋 Duyệt</b>.</div>"
            )
        else:
            banner = (
                "<div class='notice' style='margin-bottom:10px'>"
                "ADMIN: sửa từng mục bằng <b>✏️ Sửa mục</b>. Ghi TEX sẽ <b>gỡ duyệt</b> — duyệt lại khi xong."
                "</div>"
            )
        banner += companion_ai_panel_html(fp, kind)
        banner += SECTION_EDIT_JS
    head = html.escape(spec["icon"] + " " + spec["label"] + " · " + (title or "Bài"))
    wrap_attrs = ""
    if admin:
        wrap_attrs = (
            " data-lt-path='"
            + html.escape(companion_path(de_path, kind), quote=True)
            + "' data-lt-kind='"
            + html.escape(kind)
            + "'"
        )
    body = (
        LT_CSS
        + f"<div class='wrap ltpage'{wrap_attrs}>"
        + f"<div class='panel'><div class='head'>{head}</div><div class='body'>"
        + banner
        + f"<p class='ltnav'>{''.join(nav)}</p>"
        + toc
        + blocks
        + "</div></div></div>"
    )
    return base.page(spec["label"], body)


def page_theory(de_path: str):
    return page_companion(de_path, "lt")


@app.get("/member/ly-thuyet")
def member_ly_thuyet():
    return page_companion(request.args.get("path") or "", "lt")


@app.get("/member/phuong-phap")
def member_phuong_phap():
    return page_companion(request.args.get("path") or "", "pp")


def _lesson_rows():
    rows = []
    seen = set()
    for x in base.index_data().get("lessons") or []:
        p = str(x.get("path") or x.get("file") or "").replace("\\", "/")
        if not base.is_bank_question_tex(p):
            continue
        folder = base.lesson_folder(p)
        if folder in seen:
            continue
        seen.add(folder)
        rows.append(
            {
                "folder": folder,
                "path": folder + "/de.tex",
                "mon": str(x.get("Mon") or ""),
                "lop": str(x.get("Lop") or ""),
                "chuong": str(x.get("Chuong") or ""),
                "bai": str(x.get("BaiHoc") or x.get("De") or folder.rsplit("/", 1)[-1]),
            }
        )
    rows.sort(key=lambda z: (z["mon"], z["lop"], z["chuong"], z["bai"]))
    return rows


@app.get("/admin/ly-thuyet")
def admin_companion_list():
    if not base.can_manage_bank():
        return redirect("/admin/login")
    want = str(request.args.get("st") or "pending").strip().lower()
    if want not in {"pending", "approved", "all"}:
        want = "pending"
    q = str(request.args.get("q") or "").strip().lower()
    bits = []
    n_wait = n_ok = 0
    for row in _lesson_rows():
        blob = " ".join(row[k] for k in ("mon", "lop", "chuong", "bai")).lower()
        if q and q not in blob:
            continue
        cells = []
        for kind, meta in TRACKS.items():
            exists = companion_exists(row["path"], kind)
            ok = is_approved(row["path"], kind) if exists else False
            stub = looks_like_stub(row["path"], kind) if exists else True
            if ok:
                n_ok += 1
            elif exists:
                n_wait += 1
            fp = companion_path(row["path"], kind)
            if not exists:
                cells.append("<td class='muted'>—</td>")
                continue
            badge = (
                "<span class='tag had'>Đã duyệt</span>"
                if ok
                else "<span class='tag miss'>Chờ duyệt</span>"
            )
            if stub and not ok:
                badge += " <span class='muted'>khung trống</span>"
            qp = quote(fp, safe="")
            cells.append(
                "<td>"
                + badge
                + f"<div style='margin-top:6px;display:flex;gap:4px;flex-wrap:wrap'>"
                f"<a class='btn' href='{html.escape(meta['route'])}?path={quote(row['path'], safe='')}'>✏️ Sửa từng mục</a>"
                f"<a class='btn' href='/admin/edit?path={qp}'>📄 Cả file</a>"
                f"<form method='post' action='/admin/companion/status' style='display:inline'>"
                f"<input type='hidden' name='path' value='{html.escape(fp, quote=True)}'>"
                f"<input type='hidden' name='kind' value='{kind}'>"
                f"<input type='hidden' name='next' value='/admin/ly-thuyet?st={html.escape(want)}'>"
                + (
                    f"<button class='btn green' name='status' value='approved' type='submit'>Duyệt</button>"
                    if not ok
                    else f"<button class='btn red' name='status' value='pending' type='submit'>Gỡ</button>"
                )
                + "</form></div></td>"
            )
        if want != "all":
            keep = False
            for kind in TRACKS:
                exists = companion_exists(row["path"], kind)
                ok = is_approved(row["path"], kind) if exists else False
                if want == "pending" and exists and not ok:
                    keep = True
                if want == "approved" and ok:
                    keep = True
            if not keep:
                continue
        bits.append(
            "<tr><td>"
            + html.escape(row["mon"])
            + "</td><td>"
            + html.escape(row["lop"])
            + "</td><td>"
            + html.escape(row["bai"])
            + "</td>"
            + "".join(cells)
            + "</tr>"
        )
    tabs = "".join(
        f"<a class='btn{' primary' if want==k else ''}' href='/admin/ly-thuyet?st={k}'>{lab}</a>"
        for k, lab in (("pending", "Chờ duyệt"), ("approved", "Đã duyệt"), ("all", "Tất cả"))
    )
    body = (
        "<div class='wrap'><div class='panel'><div class='head'>📖 ADMIN · Lý thuyết và dạng mẫu</div><div class='body'>"
        "<div class='notice'>Học viên chỉ thấy mục đã <b>Duyệt</b>. Sửa từng mục trên trang xem (✏️ Sửa mục) hoặc sửa file sẽ tự <b>gỡ duyệt</b> — duyệt lại khi xong. "
        "ADMIN bấm <b>Sửa / AI</b> để đọc TEX hiện có, dán link SGK/SBT, rồi để Gemini viết lại lý thuyết hoặc phương pháp. "
        f"Đang chờ: <b>{n_wait}</b> · Đã duyệt: <b>{n_ok}</b>.</div>"
        f"<p style='display:flex;gap:8px;flex-wrap:wrap'>{tabs}"
        f"<a class='btn' href='/admin'>← ngan-hang</a></p>"
        "<form method='get' style='display:flex;gap:8px;margin:8px 0'><input type='hidden' name='st' value='"
        + html.escape(want)
        + "'><input name='q' value='"
        + html.escape(q)
        + "' placeholder='Tìm bài…' style='flex:1;padding:8px;border:1px solid #cbd8e6;border-radius:8px'>"
        "<button class='btn'>Tìm</button></form>"
        "<div class='bankwrap'><table class='selectgrid'><thead><tr><th>Môn</th><th>Lớp</th><th>Bài</th>"
        "<th>Lý thuyết</th><th>Dạng mẫu</th></tr></thead><tbody>"
        + ("".join(bits) or "<tr><td colspan='5' class='muted'>Không có mục phù hợp.</td></tr>")
        + "</tbody></table></div></div></div></div>"
    )
    return base.page("Duyệt lý thuyết", body)


@app.post("/admin/companion/status")
def admin_companion_status():
    if not base.can_manage_bank():
        return redirect("/admin/login")
    path = str(request.form.get("path") or "")
    kind = str(request.form.get("kind") or "lt")
    if kind not in TRACKS:
        kind = _kind_of_file(path)
    approved = str(request.form.get("status") or "") == "approved"
    if path:
        set_status(path, kind, approved)
    nxt = str(request.form.get("next") or "/admin/ly-thuyet")
    if not nxt.startswith("/admin"):
        nxt = "/admin/ly-thuyet"
    return redirect(nxt)


def _lythuyet_input(folder):
    parts = [p for p in str(folder or "").replace("\\", "/").split("/") if p]
    if parts and parts[0].lower() == "ngan-hang":
        parts = parts[1:]
    ups = "../" * max(1, len(parts))
    return "\\input{" + ups + "_lenh/lythuyet.tex}"


def _companion_prefix(folder, kind, old=""):
    m = re.search(r"\\input\s*\{[^{}]*lythuyet\.tex\}", str(old or ""), re.I)
    inp = m.group(0) if m else _lythuyet_input(folder)
    meta = {}
    for x in base.index_data().get("lessons") or []:
        p = str(x.get("path") or x.get("file") or "").replace("\\", "/")
        if base.lesson_folder(p) == folder.replace("\\", "/"):
            meta = x
            if p.lower().endswith("/de.tex"):
                break
    spec = TRACKS.get(kind) or TRACKS["lt"]
    heads = [
        "% Môn: " + str(meta.get("Mon") or ""),
        "% Lớp: " + str(meta.get("Lop") or ""),
        "% Chương: " + str(meta.get("Chuong") or ""),
        "% Bài: " + str(meta.get("BaiHoc") or meta.get("De") or folder.rsplit("/", 1)[-1]),
        "% Loại: " + spec["label"],
        "% File riêng, không trộn vào de.tex",
        inp,
    ]
    return "\n".join(heads) + "\n\n"


def _split_companion_tex(tex):
    lines = str(tex or "").splitlines(True)
    i = 0
    while i < len(lines):
        t = lines[i].strip()
        if (not t) or t.startswith("%") or t.lower().startswith("\\input"):
            i += 1
            continue
        break
    return "".join(lines[:i]), "".join(lines[i:])


def split_companion_sections(tex):
    prefix, rest = _split_companion_tex(tex)
    parts = re.split(r"\\subsubsection\s*\{([^{}]*)\}", rest)
    secs = [{"idx": 0, "title": "", "body": parts[0] if parts else rest}]
    n = 1
    for i in range(1, len(parts), 2):
        secs.append(
            {
                "idx": n,
                "title": (parts[i] or "").strip(),
                "body": parts[i + 1] if i + 1 < len(parts) else "",
            }
        )
        n += 1
    return prefix, secs


def join_companion_sections(prefix, secs):
    bits = [str(prefix or "")]
    if bits[0] and not bits[0].endswith("\n"):
        bits[0] += "\n"
    for s in secs or []:
        idx = int(s.get("idx") or 0)
        body = str(s.get("body") or "")
        if idx == 0:
            bits.append(body)
            continue
        title = str(s.get("title") or "Mục").replace("}", "").strip() or "Mục"
        if bits and not str(bits[-1]).endswith("\n"):
            bits.append("\n")
        bits.append("\\subsubsection{" + title + "}")
        if not body.startswith("\n"):
            bits.append("\n")
        bits.append(body)
    text = "".join(bits)
    return text if text.endswith("\n") else text + "\n"


def _normalize_section_payload(idx, title, body):
    title = str(title or "").replace("}", "").strip()
    body = str(body or "")
    m = re.match(r"\\subsubsection\s*\{([^{}]*)\}\s*", body)
    if m:
        if int(idx) != 0 and not title:
            title = (m.group(1) or "").strip()
        body = body[m.end() :]
    if int(idx) != 0 and not title:
        title = "Mục"
    return title, body


def _section_preview_html(idx, title, body):
    if int(idx) == 0:
        secs = parse_theory(body)
    else:
        secs = parse_theory("\\subsubsection{" + (title or "Mục") + "}\n" + body)
    return "".join((s.get("html") or "") for s in secs[:6])


def _section_blocks_html(tex, admin=False):
    secs = parse_theory(tex)
    _, raw_secs = split_companion_sections(tex)
    has_pre = bool(raw_secs) and _html_preamble_visible(raw_secs[0].get("body") or "")
    start = 0 if has_pre else 1
    bits = []
    for i, s in enumerate(secs):
        raw_idx = start + i
        tools = ""
        if admin:
            del_btn = (
                f"<button type='button' class='btn red ltSecDel' data-idx='{raw_idx}'>🗑 Xóa mục</button>"
                if raw_idx
                else ""
            )
            tools = (
                "<div class='ltsec-tools'>"
                f"<button type='button' class='btn primary ltSecEdit' data-idx='{raw_idx}' style='background:#145bb0;color:#fff'>✏️ Sửa mục này</button>"
                + (
                    f"<button type='button' class='btn green ltSecAi' data-idx='{raw_idx}'>✍️ AI viết lại mục</button>"
                    if raw_idx
                    else ""
                )
                + del_btn
                + "</div>"
            )
        bits.append(
            f"<section class='ltsec' id='{html.escape(s['id'], quote=True)}' data-idx='{raw_idx}'>"
            f"<div class='ltsec-h'><h2>{html.escape(s['title'])}</h2>{tools}</div>"
            f"{s['html']}<div class='ltSecOut'></div></section>"
        )
    blocks = "".join(bits) or "<p class='muted'>Chưa tách được mục \\subsubsection.</p>"
    if admin:
        blocks += (
            "<p style='margin-top:12px'><button type='button' class='btn ltSecAdd'>＋ Thêm mục (\\subsubsection)</button></p>"
            "<div class='ltSecOut ltSecAddOut'></div>"
        )
    return secs, blocks


def companion_section_editor_html(path, kind, tex):
    _secs, blocks = _section_blocks_html(tex, admin=True)
    return (
        LT_CSS
        + "<div class='ltpage' data-lt-path='"
        + html.escape(path, quote=True)
        + "' data-lt-kind='"
        + html.escape(kind)
        + "'>"
        "<p class='notice'><b>Sửa từng mục</b> giống câu hỏi: ✏️ Sửa / ✍️ AI → xem trước → "
        "✅ Chấp nhận ghi TEX + GitHub (Render cập nhật theo). Ghi xong cần <b>Duyệt</b> lại.</p>"
        + blocks
        + "</div>"
        + SECTION_EDIT_JS
    )


def _html_preamble_visible(body):
    preamble = re.sub(r"\\subsection\s*\{[^{}]*\}", "", body or "")
    html_body = _flush_tokens(_html_or_tokens(preprocess(preamble)))
    return bool(re.sub(r"<[^>]+>", "", html_body).strip())


def _strip_tex_fence(s):
    t = str(s or "").strip()
    t = re.sub(r"^```(?:latex|tex)?\s*", "", t, flags=re.I)
    t = re.sub(r"\s*```$", "", t)
    t = re.sub(
        r"\n*\(?⚠️ Phần phản biện bị cắt vì quá dài[^\n]*\)?\s*$",
        "",
        t,
    )
    return t.strip()


def _tex_window(s, n=14000):
    s = str(s or "")
    if len(s) <= n:
        return s
    half = n // 2
    return s[:half] + "\n\n% ... [cắt giữa file dài] ...\n\n" + s[-half:]


def _merge_companion_tex(old, generated, kind, folder):
    body = _strip_tex_fence(generated)
    _, body = _split_companion_tex(body)
    body = re.sub(r"\\input\s*\{[^{}]*lythuyet\.tex\}\s*", "", body, flags=re.I)
    prefix = _companion_prefix(folder, kind, old)
    return prefix + body.lstrip() + ("\n" if not body.endswith("\n") else "")


def _companion_quality_error(kind, latex):
    t = str(latex or "")
    if "Chưa soạn" in t or "Chèn bài mẫu" in t:
        return "AI còn chữ khung (Chưa soạn / Chèn bài mẫu). Thử lại."
    if kind == "pp":
        generic = 0
        generic += len(re.findall(r"Đọc đề, xác định đại lượng", t))
        generic += len(re.findall(r"Đọc đề, nêu dữ kiện", t))
        generic += len(re.findall(r"Tính toán và đối chiếu đơn vị, dấu", t))
        if generic >= 2:
            return "AI còn phương pháp 3 bước chung. Thử lại hoặc dán link SGK."
    return ""


def _companion_preview_html(latex):
    bits = []
    for sec in parse_theory(latex)[:8]:
        bits.append("<h3>" + html.escape(sec.get("title") or "") + "</h3>" + (sec.get("html") or ""))
    out = "<div class='ltpage'>" + "".join(bits) + "</div>"
    if len(out) > 80000:
        out = out[:80000] + "…"
    return out


def _lesson_ai_context(path):
    folder = base.lesson_folder(path)
    de = folder.rstrip("/") + "/de.tex"
    try:
        qs = base.load_lesson_questions(de)
    except Exception:
        qs = []
    names, _c = base.dang_names_of(qs)
    samples = []
    seen = set()
    for q in qs:
        d = str(q.get("dang") or "").strip()
        if d in seen:
            continue
        seen.add(d)
        samples.append((d, str(q.get("kind") or ""), str(q.get("text") or "")[:220]))
        if len(samples) >= 12:
            break
    title = ""
    for x in base.index_data().get("lessons") or []:
        p = str(x.get("path") or "")
        if base.lesson_folder(p) == folder:
            title = str(x.get("BaiHoc") or x.get("De") or "")
            break
    return {
        "folder": folder,
        "title": title or folder.rsplit("/", 1)[-1],
        "dangs": names,
        "samples": samples,
    }


def _ensure_companion_file(rel, kind):
    local = ROOT / rel
    if local.is_file():
        return
    folder = base.lesson_folder(rel)
    prefix = _companion_prefix(folder, kind, "")
    if kind == "pp":
        ctx = _lesson_ai_context(rel)
        bits = [prefix, "\\subsection{Dạng bài tập mẫu}\n"]
        dangs = ctx["dangs"] or ["Dạng 1"]
        for i, name in enumerate(dangs, 1):
            bits.append(
                f"\\subsubsection{{Dạng {i}. {name}}}\n"
                "\\begin{phuongphap}\n"
                "\\begin{enumerate}\n"
                "\\item Đọc đề, nêu dữ kiện và cái cần tìm.\n"
                "\\item Chọn công thức / mô hình đúng bài.\n"
                "\\item Tính, đổi đơn vị, đối chiếu kết quả.\n"
                "\\end{enumerate}\n"
                "\\end{phuongphap}\n"
                "\\begin{vidumau}\n"
                "\\textit{Chưa soạn bài mẫu.}\n"
                "\\end{vidumau}\n\n"
            )
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text("".join(bits), encoding="utf-8")
        return
    body = (
        prefix
        + "\\subsection{Lý thuyết}\n"
        "\\subsubsection{Nội dung}\n"
        "\\textit{Chưa soạn.}\n"
        "\\begin{kienthuc}\nCác ý kiến thức cốt lõi.\n\\end{kienthuc}\n"
    )
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(body, encoding="utf-8")


def _companion_prompt(kind, ctx, old_tex, page_text):
    dangs = "; ".join(ctx.get("dangs") or []) or "(chưa có dạng — tự đặt tên ngắn theo bài)"
    samples = "\n".join(f"- [{k}] {d}: {t}" for d, k, t in (ctx.get("samples") or [])) or "(chưa có câu)"
    page = (page_text or "").strip()
    if page:
        src = (
            "Nguồn từ file .tex trên máy ADMIN hoặc link (HTML/LaTeX). Có thể cả chương/sách — CHỈ lọc phần khớp BÀI này, bỏ bài khác.\n"
            "Giữ công thức, viết lại cho đúng file đích, không dump nguyên cuốn.\n"
            + page[:48000]
        )
    else:
        src = "Không có link. Dựa TEX hiện có + dạng/câu mẫu của bài. Không bịa định luật sai."
    old = _tex_window(old_tex, 14000)
    if kind == "pp":
        return (
            "Bạn là giáo viên THPT soạn DẠNG MẪU · PHƯƠNG PHÁP GIẢI (file pp.tex), KNTT.\n"
            f"Bài: {ctx.get('title')}\nCác dạng đang có trong ngân hàng: {dangs}\n"
            "Viết lại pp.tex cho ĐÚNG phương pháp từng dạng — không 3 bước chung chung.\n"
            "Bắt buộc:\n"
            "- Giữ % đầu file và \\input{...lythuyet.tex} (hoặc để hệ thống ghép).\n"
            "- \\subsection{Dạng bài tập mẫu}\n"
            "- Mỗi dạng một \\subsubsection{Dạng: ...} đúng tên dạng ở trên.\n"
            "- \\begin{phuongphap} ... các bước CỤ THỂ (công thức, đổi đơn vị, dấu, bẫy) \\end{phuongphap}\n"
            "- \\begin{vidumau} một bài ngắn cùng dạng: stem + \\choice 4 ý một \\True HOẶC lời giải tự luận; có \\loigiai{...} \\end{vidumau}\n"
            "- Công thức $...$. Không markdown. Không \\dangbt. Không trộn vào de.tex.\n"
            "Câu mẫu (chỉ để cùng chủ đề, đừng copy nguyên văn):\n"
            + samples
            + "\n\nTEX hiện có:\n"
            + old
            + "\n\n"
            + src
        )
    return (
        "Bạn là giáo viên THPT soạn LÝ THUYẾT (file lt.tex), SGK KNTT.\n"
        f"Bài: {ctx.get('title')}\nDạng liên quan: {dangs}\n"
        "Viết lại lt.tex cho ĐÚNG lý thuyết, đủ mục, giọng SGK. Sửa chỗ sai/thiếu trong TEX cũ.\n"
        "Bắt buộc:\n"
        "- Giữ % đầu file và \\input{...lythuyet.tex} (hoặc để hệ thống ghép).\n"
        "- \\subsection{Lý thuyết} rồi từng \\subsubsection{...}.\n"
        "- Dùng môi trường: hoatdong, kienthuc, emcobiet, emdahoc, emcothe; macro \\chuy{...}.\n"
        "- Có thể \\haicotchay{chữ}{hình TikZ đơn giản} khi cần minh họa.\n"
        "- Công thức $...$. Không markdown. Không \\begin{ex} ngân hàng, không \\dangbt.\n"
        "Câu mẫu của bài (để khớp nội dung, đừng copy đề):\n"
        + samples
        + "\n\nTEX hiện có:\n"
        + old
        + "\n\n"
        + src
    )


def companion_ai_panel_html(path, kind="lt"):
    kinds = ["lt", "pp"]
    folder = base.lesson_folder(path)
    de = folder.rstrip("/") + "/de.tex"
    btns = []
    for k in kinds:
        lab = TRACKS[k]["icon"] + " AI viết " + TRACKS[k]["label"]
        btns.append(
            f"<button type='button' class='btn green ltAiGo' data-kind='{k}' data-path='{html.escape(path, quote=True)}'>{html.escape(lab)}</button>"
        )
    btns.append(
        "<button type='button' class='btn primary ltAiGo' data-kind='all' data-path='"
        + html.escape(path, quote=True)
        + "'>📚 AI từ file/link · LT + dạng mẫu + bài tập</button>"
    )
    return (
        "<div class='notice ltai' data-path='"
        + html.escape(path, quote=True)
        + "' data-de-path='"
        + html.escape(de, quote=True)
        + "' style='margin:10px 0'>"
        "<b>ADMIN · AI soạn lý thuyết / dạng mẫu / bài tập</b><br>"
        "<span class='muted'>Máy Render <b>không mở được ổ C:\\</b>. Hãy <b>Chọn file .tex trên máy</b> (trình duyệt gửi nội dung lên), hoặc dán link GitHub/SGK nếu file đã lên mạng. "
        "AI lọc đúng bài này, viết lý thuyết + dạng mẫu + bài tập. Nạp key Gemini. Xem trước → Chấp nhận ghi.</span>"
        "<div style='display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;align-items:center'>"
        "<label class='btn' style='margin:0'>📂 Chọn .tex trên máy"
        "<input class='ltAiFile' type='file' accept='.tex,.ltx,.txt,text/plain' hidden></label>"
        "<span class='ltAiFileName muted'>Chưa chọn file</span>"
        "<input class='ltAiUrl' type='url' placeholder='Hoặc link http/https (không bắt buộc nếu đã chọn file)' "
        "style='flex:1;min-width:16rem;padding:8px;border:1px solid #cbd8e6;border-radius:7px'>"
        + "".join(btns)
        + "</div><div class='ltAiOut'></div></div>"
        + COMPANION_AI_JS
    )


COMPANION_AI_JS = r"""
<script>
(function(){
if(window.ldvlCompanionAi) return;
window.ldvlCompanionAi=true;
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}
function keys(){return (window.ldvlFilledKeys&&ldvlFilledKeys())||[];}
function readLocalTex(box){
  return new Promise(function(resolve,reject){
    const inp=box.querySelector('.ltAiFile');
    const file=inp&&inp.files&&inp.files[0];
    if(!file){resolve('');return;}
    if(file.size>900000){reject(new Error('File .tex quá lớn (dưới 900KB).'));return;}
    const r=new FileReader();
    r.onload=function(){resolve(String(r.result||''));};
    r.onerror=function(){reject(new Error('Không đọc được file trên máy.'));};
    r.readAsText(file,'UTF-8');
  });
}
document.addEventListener('change',function(e){
  const inp=e.target&&e.target.classList&&e.target.classList.contains('ltAiFile')?e.target:null;
  if(!inp) return;
  const box=inp.closest('.ltai');
  const lab=box&&box.querySelector('.ltAiFileName');
  if(lab) lab.textContent=(inp.files&&inp.files[0]&&inp.files[0].name)||'Chưa chọn file';
});
document.addEventListener('click',async function(e){
  const go=e.target.closest&&e.target.closest('.ltAiGo');
  const save=e.target.closest&&e.target.closest('.ltAiSave');
  const saveEx=e.target.closest&&e.target.closest('.ltAiSaveEx');
  const saveAll=e.target.closest&&e.target.closest('.ltAiSaveAll');
  if(!go&&!save&&!saveEx&&!saveAll) return;
  e.preventDefault();
  const box=e.target.closest('.ltai');
  if(!box) return;
  const out=box.querySelector('.ltAiOut');
  const path=box.getAttribute('data-path')||'';
  const dePath=box.getAttribute('data-de-path')||path;
  const urlEl=box.querySelector('.ltAiUrl');
  const sourceUrl=urlEl?String(urlEl.value||'').trim():'';
  if(saveEx){
    const ta=box.querySelector('.ltAiEx');
    if(!ta||!(ta.value||'').trim()){alert('Chưa có bài tập.');return;}
    if(!confirm('Thêm các \\begin{ex} vào ngân hàng + GitHub?'))return;
    saveEx.disabled=true;
    try{
      const r=await fetch('/api/admin/dang-fill-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({path:dePath,dang:'',latex:ta.value,source_url:sourceUrl})});
      const d=await r.json();
      if(!d.ok){alert(d.error||'Không ghi bài tập');saveEx.disabled=false;return;}
      out.insertAdjacentHTML('afterbegin','<div class="success">✅ Đã thêm '+(d.n||'')+' câu vào ngân hàng.</div>');
    }catch(err){alert(err);saveEx.disabled=false;}
    return;
  }
  if(saveAll){
    saveAll.disabled=true;
    try{
      const jobs=[];
      const lt=box.querySelector('.ltAiTex[data-kind=lt]');
      const pp=box.querySelector('.ltAiTex[data-kind=pp]');
      const ex=box.querySelector('.ltAiEx');
      if(lt&&(lt.value||'').trim()){
        jobs.push(fetch('/api/admin/companion-ai-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
          body:JSON.stringify({path:path,kind:'lt',latex:lt.value})}).then(r=>r.json()));
      }
      if(pp&&(pp.value||'').trim()){
        jobs.push(fetch('/api/admin/companion-ai-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
          body:JSON.stringify({path:path,kind:'pp',latex:pp.value})}).then(r=>r.json()));
      }
      if(ex&&(ex.value||'').trim()){
        jobs.push(fetch('/api/admin/dang-fill-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
          body:JSON.stringify({path:dePath,dang:'',latex:ex.value,source_url:sourceUrl})}).then(r=>r.json()));
      }
      const rs=await Promise.all(jobs);
      const bad=rs.find(d=>!d.ok);
      if(bad){alert(bad.error||'Có phần chưa ghi được');saveAll.disabled=false;return;}
      out.innerHTML='<div class="success">✅ Đã ghi LT / dạng mẫu / bài tập. Đang tải lại...</div>';
      location.reload();
    }catch(err){alert(err);saveAll.disabled=false;}
    return;
  }
  if(save){
    const kind=save.getAttribute('data-kind')||'lt';
    const ta=box.querySelector('.ltAiTex[data-kind="'+kind+'"]')||box.querySelector('.ltAiTex');
    if(!ta||!(ta.value||'').trim()){alert('Chưa có LaTeX.');return;}
    if(!confirm('Ghi vào file TEX + GitHub? Học viên chỉ thấy sau khi Duyệt lại.'))return;
    save.disabled=true;
    try{
      const r=await fetch('/api/admin/companion-ai-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({path:path,kind:kind,latex:ta.value})});
      const d=await r.json();
      if(!d.ok){out.insertAdjacentHTML('afterbegin','<div class="err">'+(d.error||'Không ghi được')+'</div>');save.disabled=false;return;}
      out.innerHTML='<div class="success">✅ Đã ghi. Đang tải lại...</div>';
      location.reload();
    }catch(err){out.insertAdjacentHTML('afterbegin','<div class="err">'+esc(err)+'</div>');save.disabled=false;}
    return;
  }
  const ks=keys();
  if(!ks.length){alert('Nạp key Gemini (nút 🤖 Gemini trên thanh menu) rồi bấm lại.');return;}
  const kind=go.getAttribute('data-kind')||'lt';
  let sourceTex='';
  try{sourceTex=await readLocalTex(box);}catch(err){out.innerHTML='<div class="err">'+esc(err)+'</div>';return;}
  sourceTex=String(sourceTex||'').trim();
  const sourceUrl2=sourceUrl;
  if(kind==='all'&&!sourceUrl2&&!sourceTex){alert('Chọn file .tex trên máy (hoặc dán link mạng) rồi bấm AI từ file/link.');return;}
  out.innerHTML=sourceTex?'⏳ Đang đọc file trên máy, lọc đúng bài này...':(sourceUrl2?'⏳ Đang đọc link (lọc đúng bài này)...':'⏳ AI đang đọc TEX hiện có rồi viết lại...');
  async function runOne(k){
    const r=await fetch('/api/admin/companion-ai',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:path,kind:k,api_keys:ks,source_url:sourceUrl2,source_tex:sourceTex})});
    return r.json();
  }
  try{
    if(kind==='all'){
      out.innerHTML='⏳ 1/3 Lý thuyết từ file/link...';
      const lt=await runOne('lt');
      out.innerHTML='⏳ 2/3 Dạng mẫu từ file/link...';
      const pp=await runOne('pp');
      out.innerHTML='⏳ 3/3 Lọc bài tập \\begin{ex}...';
      const er=await fetch('/api/admin/dang-fill',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({path:dePath,dang:'',api_keys:ks,source_url:sourceUrl2,source_tex:sourceTex})});
      const ex=await er.json();
      let h='';
      if(lt.ok){
        h+='<div class="success">'+esc(lt.summary||'Lý thuyết')+'</div>'
          +'<details open><summary>Xem trước LT</summary><div class="ltAiPrevWrap" style="max-height:280px;overflow:auto;border:1px solid #e2e8f0;border-radius:10px;padding:8px;background:#fff;margin:6px 0">'+(lt.preview||'')+'</div></details>'
          +'<textarea class="ltAiTex rwta" data-kind="lt" style="width:100%;min-height:180px;font:13px/1.45 Consolas,ui-monospace,monospace;padding:8px;margin:6px 0">'+esc(lt.latex||'')+'</textarea>'
          +'<p><button type="button" class="btn green ltAiSave" data-kind="lt">✅ Ghi lt.tex</button></p>';
      }else h+='<div class="err">LT: '+esc(lt.error||'lỗi')+'</div>';
      if(pp.ok){
        h+='<div class="success">'+esc(pp.summary||'Dạng mẫu')+'</div>'
          +'<details><summary>Xem trước dạng mẫu</summary><div class="ltAiPrevWrap" style="max-height:280px;overflow:auto;border:1px solid #e2e8f0;border-radius:10px;padding:8px;background:#fff;margin:6px 0">'+(pp.preview||'')+'</div></details>'
          +'<textarea class="ltAiTex rwta" data-kind="pp" style="width:100%;min-height:180px;font:13px/1.45 Consolas,ui-monospace,monospace;padding:8px;margin:6px 0">'+esc(pp.latex||'')+'</textarea>'
          +'<p><button type="button" class="btn green ltAiSave" data-kind="pp">✅ Ghi pp.tex</button></p>';
      }else h+='<div class="err">Dạng mẫu: '+esc(pp.error||'lỗi')+'</div>';
      if(ex.ok){
        h+='<div class="success">'+esc(ex.summary||'Bài tập')+'</div>'
          +'<textarea class="ltAiEx rwta" style="width:100%;min-height:220px;font:13px/1.45 Consolas,ui-monospace,monospace;padding:8px;margin:6px 0">'+esc(ex.latex||'')+'</textarea>'
          +'<p><button type="button" class="btn green ltAiSaveEx">✅ Thêm bài tập vào ngân hàng</button></p>';
      }else h+='<div class="err">Bài tập: '+esc(ex.error||'lỗi')+'</div>';
      if((lt.ok||pp.ok||ex.ok)) h+='<p><button type="button" class="btn primary ltAiSaveAll">✅ Chấp nhận ghi cả ba</button></p>';
      out.innerHTML=h;
      return;
    }
    const r=await fetch('/api/admin/companion-ai',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:path,kind:kind,api_keys:ks,source_url:sourceUrl2,source_tex:sourceTex})});
    const d=await r.json();
    if(!d.ok){out.innerHTML='<div class="err">'+(d.error||'Lỗi')+'</div>';return;}
    out.innerHTML='<div class="success">'+esc(d.summary||'Đã soạn. Soát LaTeX rồi bấm Chấp nhận.')+'</div>'
      +'<details open style="margin:8px 0"><summary>Xem trước (như học viên)</summary>'
      +'<div class="ltAiPrevWrap" style="max-height:420px;overflow:auto;border:1px solid #e2e8f0;border-radius:10px;padding:10px;background:#fff;margin-top:8px">'+(d.preview||'')+'</div></details>'
      +'<textarea class="ltAiTex rwta" data-kind="'+esc(kind)+'" style="width:100%;min-height:260px;font:13px/1.45 Consolas,ui-monospace,monospace;padding:8px;border:1px solid #7dd3fc;border-radius:8px;margin:8px 0">'+esc(d.latex||'')+'</textarea>'
      +'<p><button type="button" class="btn green ltAiSave" data-kind="'+esc(kind)+'">✅ Chấp nhận ghi '+esc(d.file||'')+'</button></p>';
  }catch(err){out.innerHTML='<div class="err">'+esc(err)+'</div>';}
});
})();
</script>
"""

SECTION_EDIT_JS = r"""
<script>
(function(){
if(window.ldvlCompanionSec) return;
window.ldvlCompanionSec=true;
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}
function ctx(){
  const w=document.querySelector('.ltpage');
  return {path:(w&&w.getAttribute('data-lt-path'))||'', kind:(w&&w.getAttribute('data-lt-kind'))||'lt'};
}
function showEditor(out, d){
  const isPre=Number(d.idx)===0;
  let h='<div class="ltsecedit"><div class="success">Chưa ghi file. Sửa LaTeX, Xem trước, rồi Chấp nhận (TEX + GitHub).</div>';
  if(!isPre){
    h+='<label>Tiêu đề \\subsubsection</label><input class="lt-title-in" data-k="title" value="'+esc(d.title||'')+'">';
  }else{
    h+='<p class="muted">Phần mở đầu (trước mục đầu tiên). Có thể giữ \\subsection{...}.</p>';
  }
  h+='<label>LaTeX mục này</label><textarea class="rwta" data-k="body">'+esc(d.body||'')+'</textarea>';
  h+='<p><button type="button" class="btn ltSecPrev">👁 Xem trước</button> '
    +'<button type="button" class="btn green ltSecSave">✅ Chấp nhận ghi TEX</button> '
    +'<button type="button" class="btn ltSecCancel">Hủy</button></p>';
  h+='<div class="rwlook"></div></div>';
  out.innerHTML=h;
  out.querySelector('.ltSecCancel').onclick=function(){out.innerHTML='';};
  async function preview(){
    const look=out.querySelector('.rwlook');
    look.innerHTML='⏳ Đang xem trước...';
    const title=(out.querySelector('[data-k=title]')||{}).value||d.title||'';
    const body=(out.querySelector('[data-k=body]')||{}).value||'';
    const r=await fetch('/api/admin/companion-section-preview',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({idx:d.idx,title:title,body:body})});
    const x=await r.json();
    look.innerHTML=x.ok?(x.html||'(trống)'):('<div class="err">'+(x.error||'Lỗi')+'</div>');
    if(window.ldvlTypeset) ldvlTypeset(look);
  }
  out.querySelector('.ltSecPrev').onclick=preview;
  out.querySelector('.ltSecSave').onclick=async function(){
    if(!confirm('Ghi mục này vào TEX + GitHub? Học viên chỉ thấy sau khi Duyệt lại.')) return;
    const c=ctx();
    const title=(out.querySelector('[data-k=title]')||{}).value||d.title||'';
    const body=(out.querySelector('[data-k=body]')||{}).value||'';
    const r=await fetch('/api/admin/companion-section-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:c.path,kind:c.kind,idx:d.idx,title:title,body:body})});
    const x=await r.json();
    if(!x.ok){alert(x.error||'Không ghi được');return;}
    out.innerHTML='<div class="success">✅ Đã ghi. Đang tải lại...</div>';
    location.reload();
  };
  preview();
}
document.addEventListener('click',async function(e){
  const ed=e.target.closest&&e.target.closest('.ltSecEdit');
  const ai=e.target.closest&&e.target.closest('.ltSecAi');
  const del=e.target.closest&&e.target.closest('.ltSecDel');
  const add=e.target.closest&&e.target.closest('.ltSecAdd');
  if(!ed&&!ai&&!del&&!add) return;
  e.preventDefault();
  const c=ctx();
  if(add){
    const out=document.querySelector('.ltSecAddOut');
    if(out) showEditor(out,{idx:-1,title:'',body:''});
    return;
  }
  if(del){
    const idx=+del.getAttribute('data-idx');
    if(!idx) return;
    if(!confirm('Xóa mục này khỏi TEX + GitHub?')) return;
    const r=await fetch('/api/admin/companion-section-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:c.path,kind:c.kind,idx:idx,delete:true})});
    const d=await r.json();
    if(!d.ok){alert(d.error||'Không xóa được');return;}
    location.reload();
    return;
  }
  const btn=ed||ai;
  const sec=btn.closest('.ltsec');
  const out=sec&&sec.querySelector('.ltSecOut');
  if(!out) return;
  if(ai){
    const ks=(window.ldvlFilledKeys&&ldvlFilledKeys())||[];
    if(!ks.length){alert('Nạp key Gemini (nút 🤖 Gemini trên thanh menu) rồi bấm lại.');return;}
    out.innerHTML='⏳ AI đang viết lại mục này...';
    try{
      const r=await fetch('/api/admin/companion-section-ai',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({path:c.path,kind:c.kind,idx:+ai.getAttribute('data-idx'),api_keys:ks})});
      const d=await r.json();
      if(!d.ok){out.innerHTML='<div class="err">'+(d.error||'Lỗi')+'</div>';return;}
      showEditor(out,d);
    }catch(err){out.innerHTML='<div class="err">'+esc(err)+'</div>';}
    return;
  }
  out.innerHTML='⏳ Đang tải LaTeX mục...';
  try{
    const r=await fetch('/api/admin/companion-section',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:c.path,kind:c.kind,idx:+ed.getAttribute('data-idx')})});
    const d=await r.json();
    if(!d.ok){out.innerHTML='<div class="err">'+(d.error||'Lỗi')+'</div>';return;}
    showEditor(out,d);
  }catch(err){out.innerHTML='<div class="err">'+esc(err)+'</div>';}
});
})();
</script>
"""


@app.post("/api/admin/companion-ai")
def api_admin_companion_ai():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    from student_gemini import _gemini_generate, _keys_from_payload
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").replace("\\", "/").strip()
    kind = str(data.get("kind") or _kind_of_file(path) or "lt").strip().lower()
    if kind not in TRACKS:
        kind = "lt"
    if not path.startswith("ngan-hang/"):
        return jsonify(ok=False, error="File không hợp lệ."), 400
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error="Nạp key Gemini rồi bấm lại."), 400
    rel = companion_path(path, kind)
    try:
        _ensure_companion_file(rel, kind)
    except Exception as e:
        return jsonify(ok=False, error="Không tạo được file: " + str(e)), 500
    try:
        _sha, old = base.read_tex(rel)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    page_text = ""
    source_url = str(data.get("source_url") or data.get("url") or "").strip()
    from dang_routes import _page_text_from_payload
    page_text, ferr = _page_text_from_payload(data)
    if ferr:
        return jsonify(ok=False, error=ferr), 400
    ctx = _lesson_ai_context(path)
    tok = 16000 if page_text else 12000
    latex, err, qerr = "", "", ""
    extra = ""
    for _attempt in range(2):
        prompt = _companion_prompt(kind, ctx, old, page_text) + extra
        raw = ""
        for key in keys:
            try:
                raw = _gemini_generate(key, prompt, tok, 0.2)
                err = ""
                break
            except Exception as e:
                err = str(e)
                raw = ""
        if not raw:
            continue
        latex = _merge_companion_tex(old, raw, kind, ctx["folder"])
        if "\\subsubsection" not in latex:
            qerr = "AI không ra \\subsubsection."
            extra = "\n\nLần trước thiếu \\subsubsection. Viết đủ mục."
            continue
        if kind == "pp" and "\\begin{phuongphap}" not in latex:
            qerr = "AI thiếu \\begin{phuongphap}."
            extra = "\n\nLần trước thiếu \\begin{phuongphap}."
            continue
        qerr = _companion_quality_error(kind, latex)
        if qerr:
            extra = "\n\nLần trước bị từ chối: " + qerr + " Viết cụ thể, không khung 3 bước chung."
            continue
        qerr = ""
        break
    if not latex or "\\subsubsection" not in latex:
        return jsonify(ok=False, error="AI không viết được: " + (qerr or err or "trống")), 400
    if qerr:
        return jsonify(ok=False, error=qerr + " Thử lại hoặc dán link SGK."), 400
    spec = TRACKS[kind]
    summary = (
        "AI soạn "
        + spec["label"]
        + " từ TEX"
        + (" + file trên máy" if str(data.get("source_tex") or "").strip() else (" + link" if source_url else ""))
        + ". Soát xem trước + ô LaTeX, rồi Chấp nhận ghi "
        + spec["file"]
        + "."
    )
    return jsonify(
        ok=True,
        latex=latex,
        file=spec["file"],
        kind=kind,
        src=rel,
        summary=summary,
        preview=_companion_preview_html(latex),
    )


@app.post("/api/admin/companion-ai-save")
def api_admin_companion_ai_save():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").replace("\\", "/").strip()
    kind = str(data.get("kind") or _kind_of_file(path) or "lt").strip().lower()
    if kind not in TRACKS:
        kind = "lt"
    latex = str(data.get("latex") or "")
    if not path.startswith("ngan-hang/") or "\\subsubsection" not in latex:
        return jsonify(ok=False, error="Thiếu LaTeX (cần \\subsubsection)."), 400
    rel = companion_path(path, kind)
    try:
        _ensure_companion_file(rel, kind)
        sha, old = base.read_tex(rel, need_sha=True)
        folder = base.lesson_folder(rel)
        text = _merge_companion_tex(old, latex, kind, folder)
        from admin_classify import _write_tex
        _write_tex(rel, text, "ADMIN AI soạn " + TRACKS[kind]["file"], sha or None)
        set_status(rel, kind, False)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    return jsonify(ok=True, src=rel, kind=kind)


def _companion_admin_file(path, kind):
    kind = str(kind or _kind_of_file(path) or "lt").strip().lower()
    if kind not in TRACKS:
        kind = "lt"
    rel = companion_path(path, kind)
    if not rel.startswith("ngan-hang/"):
        return None, None, "File không hợp lệ."
    return rel, kind, ""


@app.post("/api/admin/companion-section")
def api_admin_companion_section():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    rel, kind, err = _companion_admin_file(data.get("path"), data.get("kind"))
    if err:
        return jsonify(ok=False, error=err), 400
    try:
        idx = int(data.get("idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu idx."), 400
    try:
        _sha, tex = base.read_tex(rel)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    _prefix, secs = split_companion_sections(tex)
    hit = next((s for s in secs if int(s["idx"]) == idx), None)
    if not hit:
        return jsonify(ok=False, error="Không thấy mục."), 400
    return jsonify(ok=True, idx=idx, title=hit.get("title") or "", body=hit.get("body") or "", file=TRACKS[kind]["file"])


@app.post("/api/admin/companion-section-ai")
def api_admin_companion_section_ai():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    from student_gemini import _gemini_generate, _keys_from_payload
    data = request.get_json(silent=True) or {}
    rel, kind, err = _companion_admin_file(data.get("path"), data.get("kind"))
    if err:
        return jsonify(ok=False, error=err), 400
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error="Nạp key Gemini rồi bấm lại."), 400
    try:
        idx = int(data.get("idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu idx."), 400
    if idx <= 0:
        return jsonify(ok=False, error="Chọn một \\subsubsection (không phải phần mở đầu)."), 400
    try:
        _sha, tex = base.read_tex(rel)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    _prefix, secs = split_companion_sections(tex)
    hit = next((s for s in secs if int(s["idx"]) == idx), None)
    if not hit:
        return jsonify(ok=False, error="Không thấy mục."), 400
    spec = TRACKS[kind]
    extra = ""
    if kind == "pp":
        extra = (
            "Dùng \\begin{phuongphap} các bước CỤ THỂ (không 3 bước chung) "
            "và \\begin{vidumau} bài ngắn + \\loigiai.\n"
        )
    else:
        extra = "Dùng hoatdong / kienthuc / emcobiet / emdahoc / emcothe / \\chuy khi hợp.\n"
    prompt = (
        f"Bạn là giáo viên THPT. Viết lại ĐÚNG MỘT mục của file {spec['file']} (KNTT).\n"
        f"Tiêu đề hiện tại: {hit.get('title') or 'Mục'}\n"
        "Chỉ trả LaTeX:\n\\subsubsection{tiêu đề}\n"
        "rồi nội dung. Công thức $...$. Không markdown, không \\dangbt, không \\input, không cả file.\n"
        + extra
        + "Nội dung cũ:\n"
        + str(hit.get("body") or "")[:8000]
    )
    raw, err = "", ""
    for key in keys:
        try:
            raw = _gemini_generate(key, prompt, 8000, 0.2)
            err = ""
            break
        except Exception as e:
            err = str(e)
            raw = ""
    if not raw:
        return jsonify(ok=False, error="AI không viết được: " + (err or "trống")), 400
    title, body = _normalize_section_payload(idx, hit.get("title") or "", _strip_tex_fence(raw))
    if not body.strip():
        return jsonify(ok=False, error="AI trả về trống."), 400
    return jsonify(
        ok=True,
        idx=idx,
        title=title,
        body=body,
        file=spec["file"],
        note="Chưa ghi file. Soát rồi Chấp nhận.",
    )


@app.post("/api/admin/companion-section-preview")
def api_admin_companion_section_preview():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    try:
        idx = int(data.get("idx") if data.get("idx") is not None else -1)
    except (TypeError, ValueError):
        idx = -1
    title, body = _normalize_section_payload(idx, data.get("title") or "", data.get("body") or "")
    return jsonify(ok=True, html=_section_preview_html(idx, title, body))


@app.post("/api/admin/companion-section-save")
def api_admin_companion_section_save():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    rel, kind, err = _companion_admin_file(data.get("path"), data.get("kind"))
    if err:
        return jsonify(ok=False, error=err), 400
    try:
        idx = int(data.get("idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu idx."), 400
    try:
        sha, tex = base.read_tex(rel, need_sha=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    prefix, secs = split_companion_sections(tex)
    if data.get("delete"):
        if idx <= 0:
            return jsonify(ok=False, error="Không xóa phần mở đầu."), 400
        nxt = [s for s in secs if int(s["idx"]) != idx]
        if len(nxt) == len(secs):
            return jsonify(ok=False, error="Không thấy mục."), 400
        secs = nxt
        msg = "ADMIN xóa mục " + TRACKS[kind]["file"]
    else:
        title, body = _normalize_section_payload(idx, data.get("title") or "", data.get("body") or "")
        if idx < 0:
            new_idx = max(int(s["idx"]) for s in secs) + 1 if secs else 1
            secs.append({"idx": new_idx, "title": title, "body": body})
            msg = "ADMIN thêm mục " + TRACKS[kind]["file"]
        else:
            hit = next((s for s in secs if int(s["idx"]) == idx), None)
            if not hit:
                return jsonify(ok=False, error="Không thấy mục."), 400
            hit["title"] = title
            hit["body"] = body
            msg = "ADMIN sửa mục " + TRACKS[kind]["file"]
    text = join_companion_sections(prefix, secs)
    try:
        from admin_classify import _write_tex
        _write_tex(rel, text, msg, sha or None)
        set_status(rel, kind, False)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    return jsonify(ok=True, src=rel, kind=kind)
