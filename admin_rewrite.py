# -*- coding: utf-8 -*-
"""ADMIN: AI viết lại đề + lời giải; chỉ ghi TEX khi ADMIN chấp nhận."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.parse

from flask import jsonify, request

import app as base
from student_gemini import _keys_from_payload

_TAIL_RE = re.compile(r"\\(?:choiceTF|choice|shortans|loigiai)\b", re.I)
_FORBIDDEN = re.compile(r"\\(?:begin|end)\s*\{\s*(?:ex|bt)\s*\}", re.I)


def _repair_json_latex(s):
    """JSON biến \\frac thành form-feed; gấp đôi backslash lệnh LaTeX trong chuỗi."""
    out = []
    in_str = False
    esc = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if not in_str:
            if c == '"':
                in_str = True
            out.append(c)
            i += 1
            continue
        if esc:
            out.append(c)
            esc = False
            i += 1
            continue
        if c == "\\":
            nxt = s[i + 1] if i + 1 < n else ""
            rest = s[i + 1 : i + 12]
            if nxt == "f" and rest.startswith("frac"):
                out.append("\\\\")
                i += 1
                continue
            if nxt == "b" and (rest.startswith("egin") or rest.startswith("eta") or rest.startswith("ig")):
                out.append("\\\\")
                i += 1
                continue
            if nxt == "t" and (
                rest.startswith("ext")
                or rest.startswith("imes")
                or rest.startswith("an")
                or rest.startswith("o ")
                or rest.startswith("o$")
                or rest.startswith("heta")
            ):
                out.append("\\\\")
                i += 1
                continue
            if nxt == "n" and (rest.startswith("eq") or rest.startswith("abla") or rest.startswith("ot")):
                out.append("\\\\")
                i += 1
                continue
            if nxt in '"\\/bfnrtu':
                out.append(c)
                esc = True
                i += 1
                continue
            out.append("\\\\")
            i += 1
            continue
        if c == '"':
            in_str = False
        out.append(c)
        i += 1
    return "".join(out)


def _parse_obj(text):
    s = str(text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    if m:
        s = m.group(1).strip()
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b <= a:
        return {}
    chunk = s[a : b + 1]
    for cand in (chunk, _repair_json_latex(chunk)):
        try:
            data = json.loads(cand)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def _sect(raw, name):
    m = re.search(
        rf"===\s*{re.escape(name)}\s*===\s*([\s\S]*?)(?===\s*[A-Z]+\s*===|\Z)",
        str(raw or ""),
        re.I,
    )
    return (m.group(1).strip() if m else "")


def _extract_ai_fields(raw):
    obj = _parse_obj(raw)
    for key, name in (("stem", "STEM"), ("solution", "SOLUTION"), ("answer", "ANSWER"), ("note", "NOTE")):
        if not str(obj.get(key) or "").strip():
            got = _sect(raw, name)
            if got:
                obj[key] = got
    return obj


def _is_math_glue(s):
    if "\n" in str(s or ""):
        return False
    u = re.sub(r"\\(?:times|cdot|pm|mp|left|right|quad|Rightarrow|to)\b", "", s or "")
    u = re.sub(r"\s+", "", u)
    if not u or u in {")", ").", ");", ")!", ")?"}:
        return False
    return bool(re.fullmatch(r"[+\-=≈≡×·(),]+", u))


def _merge_broken_math(t):
    """Gộp $\\vec{A}$ + $\\vec{B}$ thành $\\vec{A}+\\vec{B}$, tránh lồng $."""
    t = str(t or "")
    matches = list(re.finditer(r"\$([^$]*)\$", t))
    if len(matches) < 2:
        t = re.sub(
            r"\$([^$]+)\$\s*(=)\s*((?:\\(?:vec|overrightarrow)\s*\{[^{}]+\}|-?\d+(?:[.,]\d+)?))(?!\s*\$)",
            lambda m: "$" + m.group(1) + m.group(2) + m.group(3) + "$",
            t,
        )
        return t
    out = []
    last = 0
    i = 0
    n = len(matches)
    while i < n:
        m = matches[i]
        out.append(t[last:m.start()])
        buf = [m.group(1)]
        end = m.end()
        i += 1
        while i < n and _is_math_glue(t[end:matches[i].start()]):
            buf.append(t[end:matches[i].start()])
            buf.append(matches[i].group(1))
            end = matches[i].end()
            i += 1
        trail = re.match(r"^[ \t]*\)+[ \t]*", t[end:])
        if trail and ")" in trail.group(0):
            buf.append(trail.group(0))
            end += trail.end()
        out.append("$" + "".join(buf).replace("$", "") + "$")
        last = end
    out.append(t[last:])
    t = "".join(out)
    t = re.sub(
        r"\$([^$]+)\$\s*(=)\s*((?:\\(?:vec|overrightarrow)\s*\{[^{}]+\}|-?\d+(?:[.,]\d+)?))(?!\s*\$)",
        lambda m: "$" + m.group(1) + m.group(2) + m.group(3) + "$",
        t,
    )
    t = re.sub(r"\$\s*\$", "", t)
    return t


def _fix_latex(t):
    """Gỡ lỗi AI hay gặp: \\frac bị nuốt, \\ trước tiếng Việt, toán không bọc $."""
    t = str(t or "")
    t = t.replace("\x0c", r"\f")
    t = t.replace("\x08", r"\b")
    t = t.replace("\x0crac", r"\frac")
    t = re.sub(r"(?<!\\)\trac\{", r"\\frac{", t)
    t = re.sub(r"\\(?=[À-ỹĂăÂâÊêÔôƠơƯưĐđ])", "", t)
    t = re.sub(r"\\\s+(?=[A-ZÀ-ỸĐ])", " ", t)
    t = re.sub(r"([.:;,!?])\\(?=-?\d)", r"\1 ", t)
    t = re.sub(r"\\(?=-\d)", "-", t)
    t = re.sub(r"(?<!\\)\\([,;:])(?=\s|$)", r"\1", t)
    t = re.sub(r"\$\s*\$", "", t)
    t = _merge_broken_math(t)
    return t.strip()


def _strip_meta(s):
    """Bỏ comment % ID / % Mức / %=== Câu và \\begin{ex} khỏi đề AI — không ghi vào khối ex."""
    t = str(s or "").replace("\ufeff", "")
    t = _FORBIDDEN.sub("", t)
    keep = []
    for line in t.splitlines():
        raw = line.strip()
        if not raw:
            if keep and keep[-1] != "":
                keep.append("")
            continue
        if raw.startswith("%") or raw.startswith("％"):
            continue
        if re.match(r"^[=-]{0,6}\s*Câu\s+\d+", raw, re.I):
            continue
        keep.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip()


def _clean_tex(s):
    t = str(s or "").strip()
    t = re.sub(r"^```(?:latex|tex)?\s*", "", t, flags=re.I)
    t = re.sub(r"\s*```$", "", t)
    m = re.match(r"\\loigiai\s*\{", t, re.I)
    if m:
        inner, end = base.get_braced(t, m.end() - 1)
        if inner is not None and end >= len(t.rstrip()):
            t = inner.strip()
    t = _FORBIDDEN.sub("", t)
    t = re.sub(r"^\\True\s*", "", t, flags=re.I)
    return _strip_meta(_fix_latex(t))


def _compact_solution(sol, options):
    """Xóa phần lời giải chép lại nguyên văn từng phương án (A. <đề PA>: ...)."""
    orig = _clean_tex(sol)
    if not orig:
        return orig
    if re.search(r"(?m)^\s*[A-D]\s*[\.\)]\s*(Đúng|Sai)\b", orig):
        return orig
    t = orig
    letters = "ABCD"
    for i, o in enumerate(options or []):
        piece = _clean_tex((o.get("text") if isinstance(o, dict) else o) or "")
        if not piece:
            continue
        lab = letters[i] if i < 4 else str(i + 1)
        body = re.escape(piece)
        t = re.sub(
            rf"(?:Phương án\s+)?{lab}\s*[\.\)\:：]\s*{body}\s*[:：.\-–]?",
            f"Phương án {lab}: ",
            t,
            flags=re.I,
        )
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"(?:Phương án [A-D]:\s*){2,}", lambda m: m.group(0).split(":")[0] + ": ", t)
    t = t.strip()
    if options and len(t) < max(80, int(len(orig) * 0.45)):
        return orig
    return t


def _split_head_tail(inner):
    m = _TAIL_RE.search(inner or "")
    if not m:
        return inner or "", ""
    return inner[: m.start()], inner[m.start() :]


def _split_comments(head):
    lines = (head or "").splitlines(True)
    i = 0
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("%")):
        i += 1
    return "".join(lines[:i]), "".join(lines[i:]).strip()


def _replace_loigiai(block, new_inner):
    new_inner = _clean_tex(new_inner)
    m = re.search(r"\\loigiai\s*\{", block, re.I)
    if m:
        val, end = base.get_braced(block, m.end() - 1)
        if val is None:
            return block
        return block[: m.start()] + "\\loigiai{\n" + new_inner + "\n}" + block[end:]
    env = re.search(r"\\begin\s*\{\s*loigiai\s*\}.*?\\end\s*\{\s*loigiai\s*\}", block, re.I | re.S)
    if env:
        return block[: env.start()] + "\\loigiai{\n" + new_inner + "\n}" + block[env.end() :]
    return block.rstrip() + "\n\\loigiai{\n" + new_inner + "\n}\n"


def _pack_choice_braces(new_vals, trues):
    parts = []
    for i, nv in enumerate(new_vals):
        inner = _clean_tex(nv)
        if i < len(trues) and trues[i]:
            inner = r"\True " + inner
        parts.append("{" + inner + "}")
    return "".join(parts)


def _replace_cmd_braces(block, cmd, new_vals, trues):
    if not new_vals:
        return block
    packed = _pack_choice_braces(new_vals, trues)
    m = re.search(re.escape(cmd) + r"\b", block, re.I)
    if not m:
        lg = re.search(r"\\loigiai\s*\{", block, re.I)
        if lg:
            return block[: lg.start()] + cmd + packed + "\n" + block[lg.start() :]
        return block.rstrip() + "\n" + cmd + packed + "\n"
    p = m.end()
    p_scan = p
    while p_scan < len(block) and block[p_scan].isspace():
        p_scan += 1
    if p_scan >= len(block) or block[p_scan] != "{":
        return block[:p] + packed + "\n" + block[p:]
    out = [block[:p]]
    for i, nv in enumerate(new_vals):
        while p < len(block) and block[p].isspace():
            out.append(block[p])
            p += 1
        val, p2 = base.get_braced(block, p)
        if val is None:
            return block[: m.end()] + packed + "\n" + block[m.end() :]
        inner = _clean_tex(nv)
        if i < len(trues) and trues[i]:
            inner = r"\True " + inner
        out.append("{" + inner + "}")
        p = p2
    out.append(block[p:])
    return "".join(out)


def _replace_shortans(block, new_ans):
    new_ans = _clean_tex(new_ans)
    m = re.search(r"\\shortans\s*(?:\[[^\]]*\])?\s*", block, re.I)
    if not m:
        return block
    val, end = base.get_braced(block, m.end())
    if val is None:
        return block
    brace = block.find("{", m.end())
    if brace < 0:
        return block
    return block[:brace] + "{" + new_ans + "}" + block[end:]


def _apply_inner(inner, kind, stem, solution, options, answer, flags):
    head, tail = _split_head_tail(inner)
    comments, _old_stem = _split_comments(head)
    comments = _strip_meta(comments)
    comments = (comments.rstrip() + "\n") if comments.strip() else ""
    if flags.get("stem") and stem:
        head = comments + _clean_tex(stem).strip() + "\n"
    block = head + tail
    if flags.get("opts") and options and kind in {"TN", "DS"}:
        cmd = "\\choiceTF" if kind == "DS" else "\\choice"
        trues = [bool(x.get("correct")) for x in options]
        texts = [x.get("text") if isinstance(x, dict) else x for x in options]
        block = _replace_cmd_braces(block, cmd, texts, trues)
    if flags.get("answer") and answer and kind == "TLN":
        block = _replace_shortans(block, answer)
    if flags.get("sol") and solution:
        block = _replace_loigiai(block, solution)
    return block


def _build_develop_inner(kind, stem, solution, options, answer, parent_mark, meta_lines):
    lines = [f"% Phát triển từ: {parent_mark}"]
    for ln in meta_lines or []:
        raw = str(ln or "").strip()
        if raw and "phát triển từ" not in raw.casefold():
            lines.append(raw)
    lines.append(r"\nguon{Phát triển từ câu}")
    lines.append(_clean_tex(stem).strip())
    kind = str(kind or "TL").upper()
    if kind in {"TN", "DS"} and options:
        cmd = "\\choiceTF" if kind == "DS" else "\\choice"
        trues = [bool(x.get("correct")) for x in options]
        texts = [x.get("text") if isinstance(x, dict) else x for x in options]
        lines.append(cmd + _pack_choice_braces(texts, trues))
    elif kind == "TLN" and answer:
        lines.append("\\shortans{" + _clean_tex(answer) + "}")
    if solution:
        lines.append("\\loigiai{\n" + _clean_tex(solution) + "\n}")
    return "\n".join(lines).strip() + "\n"


def _insert_after_ex(tex, file_idx, new_inner):
    for i, m in enumerate(base.EX_RE.finditer(tex)):
        if i != file_idx:
            continue
        block = "\\begin{ex}\n" + new_inner.strip() + "\n\\end{ex}\n"
        return tex[: m.end()] + "\n" + block + tex[m.end() :]
    return None


def _replace_ex(tex, file_idx, new_inner):
    for i, m in enumerate(base.EX_RE.finditer(tex)):
        if i != file_idx:
            continue
        return tex[: m.start(1)] + new_inner.strip("\n") + "\n" + tex[m.end(1) :]
    return None


def _q_plain_pack(q):
    kind = str(q.get("kind") or "TL")
    opts = []
    if kind == "TN":
        for o in q.get("options") or []:
            opts.append(
                {
                    "text": o.get("text") if isinstance(o, dict) else o,
                    "correct": bool(o.get("correct")) if isinstance(o, dict) else False,
                }
            )
    elif kind == "DS":
        for o in q.get("statements") or []:
            opts.append(
                {
                    "text": o.get("text") if isinstance(o, dict) else o,
                    "correct": bool(o.get("correct")) if isinstance(o, dict) else False,
                }
            )
        if len(opts) < 4:
            rec = base.ds_statements_from_solution(
                base.solution_of(q.get("raw") or "") or (q.get("solution") or "")
            )
            if rec:
                opts = rec
    return {
        "kind": kind,
        "id": str(q.get("id") or ""),
        "text": _clean_tex(q.get("text") or ""),
        "solution": _clean_tex(q.get("solution") or ""),
        "answer": _clean_tex(q.get("answer") or ""),
        "options": [{"text": _clean_tex(o.get("text") or ""), "correct": bool(o.get("correct"))} for o in opts],
    }


def _load_q(src, file_idx):
    src = str(src or "").replace("\\", "/")
    _, tex = base.read_tex(src)
    qs = base.parse_questions(tex)
    for q in qs:
        q["src"] = src
        try:
            fi = int(q.get("idx") or 0)
        except (TypeError, ValueError):
            continue
        if fi == int(file_idx):
            q["file_idx"] = fi
            return q, tex
    return None, tex


def _norm_cmp(s):
    t = re.sub(r"%[^\n]*", "", str(s or ""))
    t = re.sub(r"\\(?:begin|end)\s*\{[^}]*\}", " ", t, flags=re.I)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = re.sub(r"[{}$\\\[\]().,;:!?'\"«»–—\-]", "", t)
    t = t.casefold()
    return re.sub(r"\s+", "", t)


def _copied_stem_or_opts(pack, stem, new_opts):
    old_stem = _norm_cmp(pack.get("text") or "")
    stem_same = bool(old_stem) and _norm_cmp(stem) == old_stem
    old_opts = pack.get("options") or []
    if not old_opts:
        return stem_same
    if not new_opts or len(new_opts) != len(old_opts):
        return True
    prose = []
    for i, o in enumerate(old_opts):
        txt = o.get("text") or ""
        if len(re.findall(r"[A-Za-zÀ-ỹ]", txt)) >= 8:
            prose.append(i)
    if prose:
        opts_same = all(_norm_cmp(old_opts[i].get("text")) == _norm_cmp(new_opts[i].get("text")) for i in prose)
        return stem_same or opts_same
    return stem_same


_EXCEL_DATE_RE = re.compile(
    r"^\s*\$?\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(?:19)?0{2,4}\s*\$?\s*$"
)
_TLN_LETTER_RE = re.compile(r"^\s*\$?\s*[A-Da-d]\s*\$?\s*$")
_TLN_NUM_RE = re.compile(
    r"(-?\d+(?:[.,]\d+)?(?:\s*/\s*-?\d+(?:[.,]\d+)?)?)"
)


def _tln_plain_number(s):
    """Đáp án TLN: chỉ số, không đơn vị / A–D / ngày Excel 15/01/1900."""
    t = _clean_tex(s)
    t = re.sub(r"^\$+|\$+$", "", t).strip()
    t = t.replace(r"\,", "").replace("~", " ")
    if _EXCEL_DATE_RE.match(t) or _TLN_LETTER_RE.match(t):
        return ""
    t = re.sub(r"\\(?:mathrm|text|textrm|textbf)\s*\{[^{}]*\}", "", t)
    t = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", t)
    t = re.sub(r"\\dfrac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", t)
    t = re.sub(r"[{}$\\]", "", t)
    t = re.sub(r"(cm/s|rad/s|m/s|Hz|cm|mm|ms|s|m|J|N|W|kg|g)\b", "", t, flags=re.I)
    t = t.strip(" .,;:")
    t = re.sub(r"\s+", "", t)
    m = _TLN_NUM_RE.fullmatch(t)
    if not m:
        return ""
    val = m.group(1).replace(".", ",").replace(" ", "")
    if re.fullmatch(r"-?\d+/1", val):
        val = val.split("/")[0]
    return val


def _sol_too_thin(sol):
    """Lời giải TLN chỉ còn một số (vd 20) — chưa đủ bước."""
    t = _clean_tex(sol)
    return len(re.findall(r"[A-Za-zÀ-ỹ]", t)) < 24


def _coerce_tln(answer, solution, keep_solution=True):
    ans = _tln_plain_number(answer)
    if not ans:
        from_sol = _tln_plain_number(solution)
        if from_sol:
            ans = from_sol
        else:
            nums = _TLN_NUM_RE.findall(_clean_tex(solution) or "")
            if nums:
                val = nums[-1].replace(".", ",")
                val = re.sub(r"\s+", "", val)
                if re.fullmatch(r"-?\d+/1", val):
                    val = val.split("/")[0]
                ans = val
    sol = _clean_tex(solution)
    if not ans:
        return "", sol if keep_solution else ""
    if keep_solution:
        return ans, sol
    return ans, ans


_TN_STYLE_STEM_RE = re.compile(
    r"(nào\s+sau\s+đây|đâu\s+là|phương\s+án\s+nào|chọn\s+(?:câu|đáp\s+án)|"
    r"tính\s+chất\s+nào|phát\s+biểu\s+nào|ý\s+nào\s+sau|không\s+phải\s+là\s+đặc\s+trưng)",
    re.I,
)


def tn_style_stem(s):
    t = re.sub(r"\s+", " ", str(s or ""))
    return bool(_TN_STYLE_STEM_RE.search(t))


def stem_incomplete(s):
    """Đề rỗng / chỉ comment / quá ngắn — cần AI viết bổ sung từ lời giải."""
    t = _clean_tex(s)
    t = re.sub(r"%[^\n]*", " ", t)
    t = re.sub(r"\\(?:begin|end)\s*\{\s*ex\s*\}", " ", t, flags=re.I)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = re.sub(r"[{}$\\\[\]]", " ", t)
    letters = re.findall(r"[A-Za-zÀ-ỹ0-9]", t)
    return len(letters) < 18


def kind_structure_text(kind):
    kind = str(kind or "").upper()
    if kind == "DS":
        return (
            "Cấu trúc ĐÚNG/SAI (DS) bắt buộc:\n"
            "- Stem: câu dẫn ngắn, kiểu «Xét các phát biểu sau» / «Khi phân tích … hãy nhận xét».\n"
            "- CẤM stem chọn 1 ý (nào sau đây, đâu là, tính chất nào, phương án nào).\n"
            "- Đúng 4 mệnh đề khẳng định độc lập trong options (JSON) hoặc \\choiceTF {..}{..}{..}{..}.\n"
            "- Mỗi mệnh đề tự đứng được (đúng hoặc sai), không phải A/B/C/D của một câu TN.\n"
            "- Lời giải lần lượt ý a/b/c/d: đúng/sai vì sao. Không chép nguyên văn từng mệnh đề.\n"
        )
    if kind == "TN":
        return (
            "Cấu trúc TRẮC NGHIỆM (TN) bắt buộc:\n"
            "- Stem hỏi chọn 1 đáp án. Đúng 4 phương án trong options / \\choice {A}{B}{C}{D}, một \\True.\n"
            "- Không dùng \\choiceTF. Không để trống phương án.\n"
        )
    if kind == "TLN":
        return (
            "Cấu trúc TRẢ LỜI NGẮN (TLN) bắt buộc:\n"
            "- Stem nêu rõ đại lượng và đơn vị học sinh phải ghi (ví dụ theo mΩ).\n"
            "- Đề phải đủ giả thiết; cấm stem trống.\n"
            "- answer là SỐ (12 hoặc 25,12 hoặc 3/2). Cấm đơn vị trong answer, CẤM A–D, CẤM ngày 15/01/1900.\n"
            "- solution: các bước tính đầy đủ, kết quả khớp answer. Không chỉ một số trơ.\n"
            "- \\shortans{số}. Không \\choice.\n"
        )
    return (
        "Cấu trúc TỰ LUẬN (TL) bắt buộc:\n"
        "- Chỉ đề + lời giải. Không \\choice, không \\choiceTF, không \\shortans, không A/B/C/D.\n"
    )


def _rewrite_bad_structure(kind, stem, new_opts, answer, solution=""):
    kind = str(kind or "").upper()
    if stem_incomplete(stem):
        return True
    opts = list(new_opts or [])
    if kind == "DS":
        if tn_style_stem(stem):
            return True
        if len(opts) != 4:
            return True
        return any(len(str((o.get("text") if isinstance(o, dict) else o) or "").strip()) < 4 for o in opts)
    if kind == "TN":
        if len(opts) != 4:
            return True
        return not any(bool(o.get("correct")) for o in opts if isinstance(o, dict))
    if kind == "TLN":
        return (not _tln_plain_number(answer)) or _sol_too_thin(solution)
    if kind == "TL":
        return bool(opts)
    return False


def _formula_keep_block(pack):
    texts = [pack.get("text") or "", pack.get("solution") or "", pack.get("answer") or ""]
    for o in pack.get("options") or []:
        texts.append((o.get("text") if isinstance(o, dict) else o) or "")
    blob = "\n".join(str(x) for x in texts)
    bits = re.findall(r"\$[^$\n]{1,240}\$", blob)
    cmds = re.findall(r"\\(?:vec|overrightarrow|frac|dfrac|sqrt|Delta|alpha|beta|theta|omega|pi)\b(?:\s*\{[^{}]{1,80}\})?", blob)
    lines = [
        "CÔNG THỨC — ưu tiên tuyệt đối:\n"
        "- Copy nguyên các $...$ và \\vec / \\frac / \\sqrt của đề cũ. Chỉ viết lại chữ tiếng Việt.\n"
        "- Mỗi đẳng thức / mỗi vector MỘT cặp $...$ duy nhất. CẤM $ lồng trong $, CẤM tách $\\vec{GA}$ rồi dấu = rồi $\\vec{a}$.\n"
        "  SAI: $\\vec{GC}$ = -($\\vec{GA}$ + $\\vec{GB}$)\n"
        "  ĐÚNG: $\\vec{GC}=-(\\vec{GA}+\\vec{GB})$\n"
        "- CẤM bọc từng tên điểm: $A$ $B$ $C$ $G$ $ABC$. Viết: tam giác ABC, trọng tâm G.\n"
        "- Vector: $\\vec{GA}=-\\vec{a}$ (cả vế trong cùng $).\n"
    ]
    if bits:
        lines.append("Copy nguyên các công thức này:\n" + "\n".join(list(dict.fromkeys(bits))[:24]))
    if cmds:
        lines.append("Giữ các lệnh: " + ", ".join(list(dict.fromkeys(cmds))[:30]))
    return "\n".join(lines) + "\n"


def _prompt_similar(pack):
    letters = "ABCD"
    kind = str(pack.get("kind") or "TL").upper()
    opt_lines = []
    for i, o in enumerate(pack.get("options") or []):
        mark = " [ĐÚNG]" if o.get("correct") else ""
        lab = letters[i] if kind == "TN" else str(i + 1)
        opt_lines.append(f"{lab}.{mark} {o.get('text') or ''}")
    return (
        "PHÁT TRIỂN TỪ CÂU GỐC để học sinh tham khảo. Không chép lại nguyên văn câu cũ.\n"
        f"Giữ đúng loại {kind} và cùng dạng kiến thức.\n"
        "Đổi các số liệu (khối lượng, thể tích, nhiệt độ, thời gian, công suất, hiệu suất, tiền điện...) sang số mới hợp lí, khác rõ số cũ.\n"
        "Có thể đổi một vài từ (tên chất, tên vật, tình huống) nhưng vẫn đúng vật lí của dạng này.\n"
        "Tính lại lời giải từ đầu theo số mới. Đáp án đúng phải là kết quả của phép tính mới.\n"
        "Cấm giữ nguyên đáp án cũ khi số đã đổi.\n"
        + kind_structure_text(kind)
        + "CẤM dòng comment %, \\begin{ex}, \\end{ex}, \\loigiai, \\True trong stem/options/solution.\n"
        "Lời giải TN/ĐS chỉ gọi A/B/C/D, không chép lại nguyên văn từng phương án.\n"
        "JSON một object: "
        '{"stem":"...","options":[{"text":"...","correct":true}],"answer":"...","solution":"...","note":""}\n'
        "TN: options đúng 4 phương án, đúng một ý correct true theo kết quả mới. "
        "DS: options đúng 4 mệnh đề, mỗi ý có correct true/false theo số mới. "
        "TLN: options=[], answer chỉ là số mới. TL: options=[].\n"
        "Trong JSON mỗi backslash LaTeX viết hai lần. Xuống dòng bằng \\n.\n"
        "Lặp lại giữa các mốc ===STEM=== ===SOLUTION=== ===ANSWER=== ===NOTE===\n\n"
        f"Loại: {kind}\n"
        f"Câu gốc (chỉ để lấy dạng, không được chép số):\n{pack.get('text') or ''}\n"
        + ("Phương án gốc:\n" + "\n".join(opt_lines) + "\n" if opt_lines else "")
        + (f"Đáp án số cũ (phải đổi): {pack.get('answer')}\n" if pack.get("answer") else "")
        + f"Lời giải cũ (phải tính lại):\n{pack.get('solution') or ''}\n"
    )


def _prompt_recalc(pack, data):
    letters = "ABCD"
    kind = str(pack.get("kind") or "TL").upper()
    stem = _clean_tex(str((data or {}).get("stem") or ""))
    raw_opts = (data or {}).get("options") if isinstance((data or {}).get("options"), list) else []
    lines = []
    for i, o in enumerate(raw_opts):
        txt = o.get("text") if isinstance(o, dict) else o
        lab = letters[i] if kind == "TN" else str(i + 1)
        lines.append(f"{lab}. {txt or ''}")
    return (
        "ADMIN vừa sửa số hoặc từ trong đề. Giữ NGUYÊN stem dưới đây, không viết lại câu chữ của đề.\n"
        "Tính lại lời giải từ đầu cho khớp đúng bản ADMIN đã sửa.\n"
        "Đáp án đúng phải là kết quả của số liệu đang có trong stem. Cấm giữ đáp án cũ nếu số đã khác.\n"
        "TN: sửa các phương án là số để một phương án bằng kết quả mới, ba phương án là nhiễu gần kết quả; đúng một correct true.\n"
        "DS: nếu mệnh đề chứa số kết quả thì sửa số đó cho khớp phép tính mới; cập nhật correct true/false theo bản đã sửa.\n"
        "TLN: answer chỉ là số mới. TL: options=[].\n"
        + kind_structure_text(kind)
        + "CẤM %, \\begin{ex}, \\loigiai, \\True trong các trường.\n"
        "JSON: {\"stem\":\"...\",\"options\":[{\"text\":\"...\",\"correct\":true}],\"answer\":\"...\",\"solution\":\"...\",\"note\":\"\"}\n"
        "stem trong JSON phải là đúng stem ADMIN, không đổi.\n"
        "Trong JSON mỗi backslash LaTeX viết hai lần.\n"
        "Lặp lại ===STEM=== ===SOLUTION=== ===ANSWER=== ===NOTE===\n\n"
        f"Loại: {kind}\nSTEM ADMIN:\n{stem}\n"
        + ("Phương án hiện có:\n" + "\n".join(lines) + "\n" if lines else "")
    )


def _prompt(pack, retry=False):
    letters = "ABCD"
    kind = str(pack.get("kind") or "TL").upper()
    opt_lines = []
    for i, o in enumerate(pack.get("options") or []):
        mark = " [ĐÚNG]" if o.get("correct") else ""
        lab = letters[i] if kind == "TN" else str(i + 1)
        opt_lines.append(f"{lab}.{mark} {o.get('text') or ''}")
    extra = ""
    if retry:
        extra = (
            "LẦN 2 — bản trước SAI CẤU TRÚC hoặc SAI $ LaTeX (tách $\\vec{A}$ rồi = rồi $\\vec{B}$). "
            "BẮT BUỘC đề đầy đủ, lời giải đủ bước, MỖI công thức một cặp $ duy nhất. Copy nguyên công thức đề cũ.\n"
        )
    if stem_incomplete(pack.get("text") or ""):
        extra += (
            "Đề cũ THIẾU hoặc gần như trống (học viên chỉ thấy ô nhập đáp án). "
            "BẮT BUỘC viết BỔ SUNG đề đầy đủ: đủ giả thiết, số liệu, câu hỏi. "
            "Dùng lời giải + đáp án để khôi phục đề. "
            "Nếu số liệu trong lời giải không khớp đáp án thì SỬA số liệu cho khớp (ví dụ đáp án 20 thì chọn S, ρ, l sao cho ra 20), "
            "KHÔNG viết «đề có lỗi đánh máy». "
            "TLN: đề nêu rõ đơn vị cần ghi (ví dụ mΩ), answer/solution chỉ là số (20).\n"
        )
    if kind == "DS" and len(pack.get("options") or []) < 4:
        extra += (
            "FILE ĐS đang thiếu 4 mệnh đề \\choiceTF (lệnh trống). "
            "BẮT BUỘC tách từ lời giải ra đúng 4 options: chỉ khẳng định, không chữ Đúng/Sai. "
            'JSON: "options":[{"text":"...","correct":true}, ...] đúng 4 phần A–D. '
            "solution GIỮ lời giải đủ a/b/c/d (đúng/sai vì sao) — không được để trống.\n"
        )
    opt_json = (
        'DS: options đúng 4 chuỗi mệnh đề. TN: options đúng 4 phương án. '
        'TLN/TL: options = [].'
        if kind in {"DS", "TN"}
        else "options = [] (không bịa A–D)."
    )
    return (
        extra
        + _formula_keep_block(pack)
        + "Bạn là giáo viên THPT soạn đề. VIẾT LẠI chữ tiếng Việt cho gọn, GIỮ NGUYÊN công thức LaTeX. "
        "Chỉ bổ sung đề khi đề cũ thiếu. Không đổi ý toán, không đổi đáp án đúng.\n"
        f"Loại câu này là {kind} — không đổi sang loại khác.\n"
        + kind_structure_text(kind)
        + "CẤM trong stem/options/solution/answer: dòng comment LaTeX (bắt đầu %), % ID:, % Mức:, %=== Câu, \\begin{ex}, \\end{ex}, \\loigiai, \\True.\n"
        "Không gán ID hay mức độ — đó là việc công cụ phân dạng, không phải form này.\n"
        "Lời giải TN/ĐS: chỉ gọi phương án A/B/C/D (hoặc a/b/c/d), KHÔNG chép lại nguyên văn nội dung từng phương án — phần đó đã nằm ở options.\n"
        "Nếu Loại là TLN: answer CHỈ là số (vd 12 hoặc 25,12 hoặc 3/2). "
        "solution là lời giải đủ bước, khớp answer. "
        "CẤM đơn vị trong answer, CẤM A/B/C/D, CẤM dạng ngày Excel kiểu 15/01/1900 hay 15/1/1900 "
        "(Excel hay đổi phân số 15/1 thành ngày — hãy ghi 15). Không nhầm số với ngày tháng.\n"
        "LaTeX BẮT BUỘC:\n"
        "- Copy nguyên $...$ của đề cũ. Mỗi công thức một cặp $...$, không lồng $.\n"
        "- Mọi \\vec \\frac \\pi \\Rightarrow \\cos phải nằm trong đúng một $...$.\n"
        "- Không gõ \\ trước chữ tiếng Việt (sai: \\Để). Viết: Để.\n"
        "- Trong JSON, mỗi backslash LaTeX phải viết HAI lần: \\\\frac \\\\vec \\\\pi.\n"
        "- Xuống dòng bằng \\n trong JSON.\n"
        "JSON một object: "
        '{"stem":"...","options":["..."],"answer":"...","solution":"...","note":""}\n'
        + opt_json
        + "\nĐồng thời lặp lại lời giải thuần LaTeX giữa các mốc:\n"
        "===STEM===\n...===SOLUTION===\n...===ANSWER===\n...===NOTE===\n"
        "options không chứa \\True. solution không bọc \\loigiai / \\begin{ex}.\n\n"
        f"Loại: {kind}\n"
        f"Đề cũ (nếu trống/thiếu thì phải viết mới cho đủ; nếu đã có thì viết lại diễn đạt):\n{pack['text'] or '(TRỐNG — hãy viết đầy đủ đề)'}\n"
        + ("Phương án/mệnh đề cũ (viết lại diễn đạt, cùng thứ tự đúng/sai):\n" + "\n".join(opt_lines) + "\n" if opt_lines else "")
        + (f"Đáp án shortans cũ: {pack['answer']}\n" if pack.get("answer") else "")
        + f"Lời giải cũ:\n{pack['solution'] or '(trống)'}\n"
    )


def _ex_inner(tex, file_idx):
    try:
        want = int(file_idx)
    except (TypeError, ValueError):
        return None
    for i, m in enumerate(base.EX_RE.finditer(tex or "")):
        if i == want:
            return m.group(1)
    return None


def _raw_parts(q, tex=None, file_idx=None):
    raw = ""
    if tex is not None and file_idx is not None:
        raw = _ex_inner(tex, file_idx) or ""
    if not raw:
        raw = q.get("raw") or ""
        wrapped = raw if re.search(r"\\begin\s*\{\s*(?:ex|bt)\s*\}", raw, re.I) else (
            "\\begin{ex}\n" + raw + "\n\\end{ex}\n"
        )
        m = base.EX_RE.search(wrapped)
        if m:
            raw = m.group(1)
    head, _tail = _split_head_tail(raw)
    _comments, stem = _split_comments(head)
    sol = base.solution_of("\\begin{ex}\n" + (raw or "") + "\n\\end{ex}\n") or (q.get("solution") or "")
    return _clean_tex(stem), _clean_tex(sol)


def _fig_key(name):
    return str(name or "").replace("\\", "/").strip().rsplit("/", 1)[-1].lower()


def _figure_names(text):
    return re.findall(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^}]*)\}", text or "", re.I)


def _fig_gap(gap):
    return re.fullmatch(r"(?:\s|\\hfill|\\\\(?:\[[^\]]*\])?)*", gap or "") is not None


def _figure_pieces(text):
    """Khối ảnh của đề: ưu tiên \\begin{center}...\\includegraphics, rồi lệnh trần liền nhau."""
    text = text or ""
    pieces = []
    covered = set()
    spans = []
    center_re = re.compile(
        r"\\begin\s*\{\s*center\s*\}(?:(?!\\end\s*\{\s*center\s*\}).)*?\\includegraphics"
        r"(?:(?!\\end\s*\{\s*center\s*\}).)*?\\end\s*\{\s*center\s*\}",
        re.I | re.S,
    )
    for m in center_re.finditer(text):
        piece = m.group(0).strip()
        keys = [_fig_key(n) for n in _figure_names(piece)]
        keys = [k for k in keys if k]
        if not keys:
            continue
        spans.append((m.start(), m.end()))
        pieces.append(piece)
        covered.update(keys)
    bare_re = re.compile(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^}]*)\}", re.I)
    bares = []
    for m in bare_re.finditer(text):
        if any(a <= m.start() and m.end() <= b for a, b in spans):
            continue
        key = _fig_key(m.group(1))
        if not key or key in covered:
            continue
        bares.append((m.start(), m.end(), key))
        covered.add(key)
    groups = []
    for item in bares:
        if groups and _fig_gap(text[groups[-1][-1][1] : item[0]]):
            groups[-1].append(item)
        else:
            groups.append([item])
    for group in groups:
        pieces.append(text[group[0][0] : group[-1][1]].strip())
    return pieces


def _restore_figures(old, new):
    """Gắn lại ảnh câu gốc nếu bản mới làm rơi. Bản đã có ảnh riêng thì giữ bản đó."""
    new = new or ""
    add = []
    if not _figure_names(new):
        have = set()
        for piece in _figure_pieces(old):
            keys = [k for k in (_fig_key(n) for n in _figure_names(piece)) if k]
            if not keys or any(k in have for k in keys):
                continue
            add.append(piece)
            have.update(keys)
    if "tikzpicture" not in new.lower():
        tikz = re.findall(
            r"\\begin\s*\{\s*tikzpicture\b.*?\\end\s*\{\s*tikzpicture\s*\}",
            old or "",
            re.I | re.S,
        )
        add.extend(b.strip() for b in tikz if b.strip())
    if not add:
        return new
    prefix = "\n".join(add).strip()
    body = new.strip()
    return prefix if not body else prefix + "\n" + body


def _pack_payload(src, fi, kind, stem, solution, answer, options, note="", develop=False, keep_stem="", keep_sol=""):
    stem = _clean_tex(stem)
    options = [
        {
            "text": _clean_tex(o.get("text") if isinstance(o, dict) else o),
            "correct": bool(o.get("correct")) if isinstance(o, dict) else False,
        }
        for o in (options or [])
    ]
    solution = _compact_solution(solution, options)
    answer = _clean_tex(answer)
    stem_had = {_fig_key(n) for n in _figure_names(stem)}
    sol_had = {_fig_key(n) for n in _figure_names(solution)}
    stem = _restore_figures(keep_stem, stem)
    solution = _restore_figures(keep_sol, solution)
    if ({_fig_key(n) for n in _figure_names(stem)} - stem_had) or ({_fig_key(n) for n in _figure_names(solution)} - sol_had):
        note = ((note + " ") if note else "") + "Ảnh của câu gốc được giữ."
    opt_html = ""
    if options and kind == "TN":
        bits = []
        for i, o in enumerate(options[:4]):
            mark = " <span class='okmark'>Đáp án đúng</span>" if o.get("correct") else ""
            bits.append(
                f"<div class='opt{' ok' if o.get('correct') else ''}'><b>{'ABCD'[i]}.</b> {base.html_question(o.get('text',''), src)}{mark}</div>"
            )
        opt_html = "<div class='opts'>" + "".join(bits) + "</div>"
    elif options and kind == "DS":
        bits = ['<div class="tf-colhead"><span></span><span></span><span class="tf-h yes">Đúng</span><span class="tf-h no">Sai</span></div>']
        labs = "ABCD"
        for i, o in enumerate(options):
            yes = bool(o.get("correct"))
            lab = labs[i] if i < 4 else str(i + 1)
            cls = " ok" if yes else " noans"
            y_on = " on" if yes else ""
            n_on = " on" if not yes else ""
            bits.append(
                f"<div class='tf{cls}'><span class='tflab'>{lab}</span><div class='tf-text'>{base.html_question(o.get('text',''), src)}</div><span class='tf-box yes{y_on}'></span><span class='tf-box no{n_on}'></span></div>"
            )
        opt_html = "<div class='tfgrid'>" + "".join(bits) + "</div>"
    return {
        "ok": True,
        "src": src,
        "file_idx": fi,
        "kind": kind,
        "note": note,
        "stem": stem,
        "solution": solution,
        "answer": answer,
        "options": options,
        "stem_html": base.html_question(stem, src),
        "sol_html": base.html_question(solution, src),
        "opt_html": opt_html,
        "answer_html": base.html_question(answer or "", src),
        "develop": bool(develop),
    }


@base.app.post("/api/admin/tex-preview")
def api_tex_preview():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    tex = _clean_tex(data.get("tex") or data.get("latex") or "")
    src = str(data.get("src") or data.get("path") or "")
    return jsonify(ok=True, html=base.html_question(tex, src))


@base.app.post("/api/admin/rewrite-question")
def api_rewrite_question():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới viết lại đề/lời giải."), 403
    data = request.get_json(silent=True) or {}
    src = str(data.get("src") or data.get("path") or "").replace("\\", "/").strip()
    try:
        fi = int(data.get("file_idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu file_idx."), 400
    if not src.startswith("ngan-hang/"):
        return jsonify(ok=False, error="File không hợp lệ."), 400
    q, _tex = _load_q(src, fi)
    if not q:
        return jsonify(ok=False, error="Không tìm thấy câu trong file."), 400
    pack = _q_plain_pack(q)
    raw_stem, raw_sol = _raw_parts(q, _tex, fi)
    mode = str(data.get("mode") or "ai").strip().lower()
    if mode in {"current", "edit"}:
        return jsonify(
            _pack_payload(
                src,
                fi,
                pack["kind"],
                raw_stem or pack["text"],
                raw_sol or pack["solution"],
                pack.get("answer") or "",
                pack["options"],
                "Sửa trực tiếp — chưa ghi file. Ảnh trong đề được giữ.",
                keep_stem=raw_stem,
                keep_sol=raw_sol,
            )
        )
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error="Thiếu Gemini API key."), 400
    from admin_classify import _gemini_once

    variant = mode in {"similar", "recalc"}
    develop = mode == "similar" or bool(data.get("develop"))

    def fields_from(raw):
        obj = _extract_ai_fields(raw)
        stem = _clean_tex(obj.get("stem") or "")
        solution = _clean_tex(obj.get("solution") or "")
        answer = _clean_tex(obj.get("answer") or "")
        raw_opts = obj.get("options") if isinstance(obj.get("options"), list) else []
        new_opts = []
        old_opts = pack["options"] or []
        kind = pack["kind"]
        if kind == "DS" and len(raw_opts) != 4:
            rec = base.ds_statements_from_solution(solution)
            if len(rec) == 4:
                raw_opts = rec
        need = 4 if kind in ("TN", "DS") else len(old_opts)
        if kind in ("TN", "DS") and len(raw_opts) == 4:
            need = 4
        if raw_opts and need and len(raw_opts) == need:
            for i in range(need):
                item = raw_opts[i]
                txt = item.get("text") if isinstance(item, dict) else item
                if isinstance(item, dict) and "correct" in item:
                    correct = bool(item.get("correct"))
                elif variant:
                    correct = False
                elif i < len(old_opts):
                    correct = bool(old_opts[i].get("correct"))
                else:
                    correct = False
                new_opts.append({"text": _clean_tex(txt), "correct": correct})
        if kind == "TN" and new_opts and not any(o.get("correct") for o in new_opts):
            hit = re.search(r"\b([A-D])\b", answer or "", re.I)
            if hit:
                ix = ord(hit.group(1).upper()) - 65
                if 0 <= ix < len(new_opts):
                    new_opts[ix]["correct"] = True
        note = str(obj.get("note") or "").strip()[:300]
        if pack["kind"] == "TLN":
            answer, solution = _coerce_tln(answer, solution)
        return stem, solution, answer, new_opts, note

    if variant and mode == "similar":
        prompt = _prompt_similar(pack)
    elif variant:
        prompt = _prompt_recalc(pack, data)
    else:
        prompt = _prompt(pack)
    raw, err = _gemini_once(keys, prompt, 6000)
    if not raw:
        return jsonify(ok=False, error=err or "Gemini không trả lời."), 400
    stem, solution, answer, new_opts, note = fields_from(raw)
    if variant:
        if mode == "recalc":
            kept = _clean_tex(str(data.get("stem") or ""))
            if kept:
                stem = kept
        if stem_incomplete(stem) or not solution or _rewrite_bad_structure(pack["kind"], stem, new_opts, answer, solution):
            raw2, err2 = _gemini_once(keys, prompt + "\nLẦN 2: bản trước thiếu đề, thiếu lời giải hoặc sai đáp án. Tính lại cho khớp số trong đề.\n", 6000)
            if raw2:
                s2, sol2, a2, o2, n2 = fields_from(raw2)
                if s2 or sol2:
                    stem, solution, answer, new_opts, note = s2, sol2, a2, o2, n2
                    if mode == "recalc":
                        kept = _clean_tex(str(data.get("stem") or ""))
                        if kept:
                            stem = kept
            elif not solution:
                return jsonify(ok=False, error=err2 or "Chưa tính lại được lời giải."), 400
        if stem_incomplete(stem) or not solution:
            return jsonify(ok=False, error="Chưa ra đủ đề và lời giải khớp số mới. Bấm lại."), 400
        if pack["kind"] in ("TN", "DS") and _rewrite_bad_structure(pack["kind"], stem, new_opts, answer, solution):
            return jsonify(ok=False, error="Đáp án mới chưa đủ 4 ý hoặc chưa có ý đúng. Bấm lại."), 400
        tag = "Phát triển từ câu — số liệu và đáp án đã tính lại, để học sinh tham khảo." if mode == "similar" else "Đã tính lại lời giải và đáp án theo số hoặc từ vừa sửa."
        note = (tag + (" " + note if note else "")).strip()
        return jsonify(_pack_payload(src, fi, pack["kind"], stem, solution, answer, new_opts, note, develop=develop, keep_stem=raw_stem, keep_sol=raw_sol))
    copied = _copied_stem_or_opts(pack, stem, new_opts)
    bad_struct = _rewrite_bad_structure(pack["kind"], stem, new_opts, answer, solution)
    if copied or bad_struct:
        raw2, err2 = _gemini_once(keys, _prompt(pack, retry=True), 5000)
        if raw2:
            s2, sol2, a2, o2, n2 = fields_from(raw2)
            if s2 or sol2 or o2:
                stem, solution, answer, new_opts, note = s2, sol2, a2, o2, n2
                if _copied_stem_or_opts(pack, stem, new_opts):
                    note = ((note + " ") if note else "") + "AI vẫn gần đề cũ — hãy sửa tay trước khi ghi."
                copied = False
            else:
                note = ((note + " ") if note else "") + (err2 or "Lần 2 trống — giữ bản đầu.")
        else:
            note = ((note + " ") if note else "") + (err2 or "Không gọi được lần 2 — giữ bản đầu.")
        if copied:
            note = ((note + " ") if note else "") + "AI gần như copy đề cũ — hãy sửa tay trước khi ghi."
    if not stem and not solution:
        return jsonify(ok=False, error="AI không viết được đề/lời giải."), 400
    if stem_incomplete(stem) and not stem_incomplete(raw_stem or pack["text"]):
        stem = raw_stem or pack["text"]
        note = ((note + " ") if note else "") + "Thiếu đề mới — đang hiện đề cũ."
    if stem_incomplete(stem):
        return jsonify(
            ok=False,
            error="AI chưa viết đủ đề. Bấm lại «AI viết lại đề + lời giải» — hệ thống sẽ bổ sung đề từ lời giải và đáp án.",
        ), 400
    if not solution:
        solution = raw_sol or pack["solution"]
    if pack["kind"] == "TLN":
        answer, sol_keep = _coerce_tln(answer, solution or "")
        if not answer:
            answer, _ignored = _coerce_tln(pack.get("answer") or "", raw_sol or pack.get("solution") or "")
        if _sol_too_thin(sol_keep):
            if not _sol_too_thin(raw_sol or pack.get("solution") or ""):
                solution = raw_sol or pack.get("solution") or ""
                note = ((note + " ") if note else "") + "AI chỉ ghi số ở lời giải — đang hiện lời giải cũ. Sửa cho khớp đề rồi ghi."
            else:
                return jsonify(
                    ok=False,
                    error="AI chưa viết lời giải đủ bước (không được chỉ ghi 20). Bấm lại «AI viết lại đề + lời giải».",
                ), 400
        else:
            solution = sol_keep
    old_ok = not stem_incomplete(raw_stem or pack["text"]) and (
        pack["kind"] not in ("DS", "TN") or len(pack["options"] or []) == 4
    )
    if _rewrite_bad_structure(pack["kind"], stem, new_opts, answer, solution) and pack["kind"] in ("DS", "TN"):
        if old_ok:
            stem = raw_stem or pack["text"]
            new_opts = pack["options"]
            note = (
                ((note + " ") if note else "")
                + "AI sai dạng câu (ĐS = 4 mệnh đề, không hỏi «nào sau đây»; TN = 4 phương án). Đang hiện đề cũ — sửa tay hoặc bấm viết lại."
            )
        else:
            return jsonify(
                ok=False,
                error="Câu đang thiếu đề/phương án. AI chưa bổ sung đủ (ĐS/TN cần 4 ý). Bấm viết lại lần nữa.",
            ), 400
    elif pack["options"] and not new_opts:
        new_opts = pack["options"]
    return jsonify(
        _pack_payload(
            src,
            fi,
            pack["kind"],
            stem,
            solution,
            answer or pack.get("answer") or "",
            new_opts,
            note,
            keep_stem=raw_stem,
            keep_sol=raw_sol,
        )
    )


@base.app.post("/api/admin/rewrite-question-save")
def api_rewrite_question_save():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới ghi đề/lời giải."), 403
    data = request.get_json(silent=True) or {}
    src = str(data.get("src") or "").replace("\\", "/").strip()
    try:
        fi = int(data.get("file_idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu file_idx."), 400
    if not src.startswith("ngan-hang/"):
        return jsonify(ok=False, error="File không hợp lệ."), 400
    flags = {
        "stem": bool(data.get("apply_stem", True)),
        "opts": bool(data.get("apply_opts", True)),
        "sol": bool(data.get("apply_sol", True)),
        "answer": bool(data.get("apply_answer", True)),
    }
    if not any(flags.values()):
        return jsonify(ok=False, error="Chưa chọn phần nào để ghi."), 400
    q, tex = _load_q(src, fi)
    if not q:
        return jsonify(ok=False, error="Không tìm thấy câu trong file."), 400
    inner = None
    for i, m in enumerate(base.EX_RE.finditer(tex)):
        if i == fi:
            inner = m.group(1)
            break
    if inner is None:
        return jsonify(ok=False, error="Không khớp khối \\begin{ex}."), 400
    opts_in = data.get("options") if isinstance(data.get("options"), list) else []
    merged_opts = []
    old = _q_plain_pack(q)["options"]
    kind = str(q.get("kind") or "TL")
    if kind in ("TN", "DS"):
        src_opts = opts_in if len(opts_in) == 4 else old
        for i, item in enumerate(src_opts[:4]):
            t = item.get("text") if isinstance(item, dict) else item
            if isinstance(item, dict) and "correct" in item:
                correct = bool(item.get("correct"))
            elif i < len(old):
                correct = bool(old[i].get("correct"))
            else:
                correct = False
            merged_opts.append({"text": _clean_tex(t), "correct": correct})
    elif opts_in and len(opts_in) == len(old):
        for i, o in enumerate(old):
            t = opts_in[i]
            t = t.get("text") if isinstance(t, dict) else t
            merged_opts.append({"text": _clean_tex(t), "correct": bool(o.get("correct"))})
    orig_stem, orig_sol = _raw_parts(q, tex, fi)
    sol_in = data.get("solution") or ""
    ans_in = data.get("answer") or ""
    if kind == "TLN":
        ans_in, sol_in = _coerce_tln(ans_in, sol_in)
    stem_in = _restore_figures(orig_stem, _clean_tex(data.get("stem") or ""))
    sol_in = _restore_figures(orig_sol, sol_in)
    develop_save = str(data.get("save_as") or "").strip().lower() == "develop"
    if develop_save:
        parent_mark = str(q.get("id") or "").strip() or f"idx:{fi}"
        meta = []
        head, _tail = _split_head_tail(inner)
        comments, _old_stem = _split_comments(head)
        for ln in comments.splitlines():
            if re.search(r"mức", ln, re.I):
                meta.append(ln.strip())
        new_inner = _build_develop_inner(
            kind,
            stem_in,
            _compact_solution(sol_in, merged_opts),
            merged_opts,
            _clean_tex(ans_in),
            parent_mark,
            meta,
        )
        new_tex = _insert_after_ex(tex, fi, new_inner)
        if new_tex is None:
            return jsonify(ok=False, error="Không thêm được câu phát triển."), 400
        try:
            sha, _ = base.read_tex(src, need_sha=True)
            from admin_classify import _write_tex

            _write_tex(src, new_tex, "ADMIN phát triển từ câu " + src, sha)
            try:
                from dang_routes import _STATS_CACHE, _QID_CACHE

                _STATS_CACHE.clear()
                _QID_CACHE.clear()
            except Exception:
                pass
        except Exception as e:
            return jsonify(ok=False, error=str(e)), 500
        return jsonify(ok=True, added=True)
    new_inner = _apply_inner(
        inner,
        kind,
        stem_in,
        _compact_solution(sol_in, merged_opts),
        merged_opts,
        _clean_tex(ans_in),
        flags,
    )
    new_tex = _replace_ex(tex, fi, new_inner)
    if new_tex is None:
        return jsonify(ok=False, error="Không ghi được khối câu."), 400
    try:
        sha, _ = base.read_tex(src, need_sha=True)
        from admin_classify import _write_tex

        _write_tex(src, new_tex, "ADMIN viết lại đề/lời giải " + src, sha)
        try:
            from dang_routes import _STATS_CACHE, _QID_CACHE

            _STATS_CACHE.clear()
            _QID_CACHE.clear()
        except Exception:
            pass
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    return jsonify(ok=True)


@base.app.get("/api/admin/question-card")
def api_question_card():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    src = str(request.args.get("src") or "").replace("\\", "/").strip()
    try:
        fi = int(request.args.get("file_idx"))
        seq = int(request.args.get("seq") or fi + 1)
        total = int(request.args.get("total") or seq)
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Thiếu vị trí câu."), 400
    if not src.startswith("ngan-hang/"):
        return jsonify(ok=False, error="File không hợp lệ."), 400
    try:
        _, tex = base.read_tex(src)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    raw = base.parse_questions(tex)
    for q in raw:
        q["src"] = src
        q["file_idx"] = int(q.get("idx") or 0)
    qs = base.nest_developments(raw)
    q = next((x for x in qs if int(x.get("file_idx") if x.get("file_idx") is not None else -1) == fi), None)
    if not q:
        return jsonify(ok=False, error="Không tìm thấy câu vừa ghi."), 404
    from dang_routes import _question_card

    return jsonify(ok=True, html=_question_card(q, seq, total, src, show_solution=True))


_IMG_FILE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.(?:png|jpe?g|gif|webp)\Z", re.I)
_IMG_REL_RE = re.compile(
    r"(?:images|Images|ImagesGPT)/[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.(?:png|jpe?g|gif|webp)\Z",
    re.I,
)


def _lesson_image_rows(src, file_idx=None):
    src = str(src or "").replace("\\", "/").strip()
    if not src.startswith("ngan-hang/") or not src.lower().endswith(".tex"):
        raise ValueError("File không hợp lệ.")
    folder = base.lesson_folder(src)
    if not str(folder).startswith("ngan-hang/"):
        raise ValueError("Bài không hợp lệ.")
    items = []
    seen = set()
    for dname in base.LESSON_IMAGE_DIRS:
        rel_dir = folder.rstrip("/") + "/" + dname
        try:
            _p, local = base._safe_repo_file(rel_dir)
        except Exception:
            continue
        if not local.is_dir():
            continue
        try:
            children = sorted(local.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for child in children:
            if not child.is_file() or child.suffix.lower() not in base.IMG_EXTS:
                continue
            if not _IMG_FILE_RE.fullmatch(child.name):
                continue
            try:
                if child.stat().st_size < 40:
                    continue
            except OSError:
                continue
            file_rel = dname + "/" + child.name
            if file_rel.lower() in seen:
                continue
            seen.add(file_rel.lower())
            web = "/bank-img/" + urllib.parse.quote(
                folder[len("ngan-hang/") :].rstrip("/") + "/" + file_rel,
                safe="/",
            )
            items.append({"file": file_rel, "name": child.name, "url": web})
            if len(items) >= 80:
                break
        if len(items) >= 80:
            break
    used = []
    if file_idx is not None:
        try:
            q, tex = _load_q(src, int(file_idx))
        except Exception:
            q, tex = None, ""
        if q:
            stem, _sol = _raw_parts(q, tex, int(file_idx))
            for name in _figure_names(stem):
                key = _fig_key(name)
                for it in items:
                    if _fig_key(it["file"]) == key and it["file"] not in used:
                        used.append(it["file"])
    return items, used


def _check_image_rel(src, file_rel):
    file_rel = str(file_rel or "").replace("\\", "/").strip().lstrip("/")
    if not _IMG_REL_RE.fullmatch(file_rel):
        raise ValueError("Tên ảnh không hợp lệ.")
    folder = base.lesson_folder(src).rstrip("/")
    if not folder.startswith("ngan-hang/"):
        raise ValueError("Bài không hợp lệ.")
    rel = folder + "/" + file_rel
    p, local = base._safe_repo_file(rel)
    if not p.startswith(folder + "/"):
        raise ValueError("Ảnh không thuộc thư mục bài.")
    return p, local, file_rel


def _strip_inc_text(text):
    t = text or ""
    t = re.sub(
        r"\\begin\s*\{\s*center\s*\}(?:(?!\\end\s*\{\s*center\s*\}).)*?\\includegraphics"
        r"(?:(?!\\end\s*\{\s*center\s*\}).)*?\\end\s*\{\s*center\s*\}\s*",
        "",
        t,
        flags=re.I | re.S,
    )
    t = re.sub(
        r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{[^}]*\}(?:\s*\\hfill|\s*\\\\(?:\[[^\]]*\])?)?\s*",
        "",
        t,
        flags=re.I,
    )
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _image_kind(blob):
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if blob.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if blob.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(blob) >= 12 and blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "webp"
    return ""


def _decode_image_b64(raw):
    s = str(raw or "").strip()
    if s.startswith("data:"):
        s = s.split(",", 1)[-1]
    s = re.sub(r"\s+", "", s)
    if not s:
        raise ValueError("Chưa có ảnh.")
    try:
        blob = base64.b64decode(s, validate=True)
    except Exception:
        raise ValueError("Dữ liệu ảnh không hợp lệ.")
    return blob


def _save_uploaded_image(src, blob):
    ext = _image_kind(blob)
    if not ext:
        raise ValueError("Chỉ nhận png, jpg, gif, webp.")
    if len(blob) > 4_000_000:
        raise ValueError("Ảnh quá lớn (dưới 4MB).")
    if len(blob) < 40:
        raise ValueError("Ảnh trống.")
    folder = base.lesson_folder(src)
    if not str(folder).startswith("ngan-hang/"):
        raise ValueError("Bài không hợp lệ.")
    name = "w-" + hashlib.sha1(blob).hexdigest()[:10] + "." + ext
    rel = folder.rstrip("/") + "/images/" + name
    sha = None
    try:
        sha = base.github_file_sha(rel) or None
    except Exception:
        sha = None
    base.github_put_bytes(rel, blob, "ADMIN thêm ảnh " + name, sha)
    web = "/bank-img/" + urllib.parse.quote(rel[len("ngan-hang/") :], safe="/")
    return {"file": "images/" + name, "name": name, "url": web}


def _write_question_figure(src, fi, mode, file_rel=""):
    q, tex = _load_q(src, fi)
    if not q:
        raise ValueError("Không tìm thấy câu.")
    if mode == "set":
        _p, local, file_rel = _check_image_rel(src, file_rel)
        if not local.is_file():
            raise ValueError("Không thấy file ảnh trong thư mục bài.")
    elif mode != "clear":
        raise ValueError("Không rõ thao tác ảnh.")
    new_tex = None
    for i, m in enumerate(base.EX_RE.finditer(tex)):
        if i != fi:
            continue
        inner = m.group(1)
        head, tail = _split_head_tail(inner)
        comments, stem = _split_comments(head)
        stem = _strip_inc_text(stem)
        if mode == "set":
            stem = (
                "\\begin{center}\\includegraphics[width=0.55\\linewidth]{"
                + file_rel
                + "}\\end{center}\n"
                + stem
            )
        head_out = ((comments.rstrip() + "\n") if comments.strip() else "") + stem.strip() + "\n"
        new_tex = _replace_ex(tex, fi, head_out + (tail or ""))
        break
    if new_tex is None:
        raise ValueError("Không ghi được ảnh vào câu.")
    sha, _ = base.read_tex(src, need_sha=True)
    from admin_classify import _write_tex

    note = _write_tex(src, new_tex, "ADMIN gắn ảnh câu " + src, sha) or ""
    try:
        from dang_routes import _STATS_CACHE, _QID_CACHE

        _STATS_CACHE.clear()
        _QID_CACHE.clear()
    except Exception:
        pass
    return note


@base.app.get("/api/admin/lesson-images")
def api_lesson_images():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    src = str(request.args.get("src") or "").replace("\\", "/").strip()
    raw_fi = request.args.get("file_idx")
    fi = None
    if raw_fi not in (None, ""):
        try:
            fi = int(raw_fi)
        except (TypeError, ValueError):
            return jsonify(ok=False, error="Vị trí câu không hợp lệ."), 400
    try:
        images, used = _lesson_image_rows(src, fi)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    return jsonify(ok=True, images=images, used=used)


@base.app.post("/api/admin/lesson-image")
def api_lesson_image():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    src = str(data.get("src") or "").replace("\\", "/").strip()
    action = str(data.get("action") or "").strip().lower()
    if not src.startswith("ngan-hang/"):
        return jsonify(ok=False, error="File không hợp lệ."), 400
    try:
        if action == "upload":
            image = _save_uploaded_image(src, _decode_image_b64(data.get("data") or ""))
            return jsonify(ok=True, image=image)
        fi = int(data.get("file_idx"))
        note = _write_question_figure(src, fi, action, str(data.get("file") or ""))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    return jsonify(ok=True, note=note)


def _clean_tikz_code(raw):
    code = str(raw or "").strip()
    if len(code) > 20000:
        raise ValueError("Mã TikZ quá dài.")
    if not re.search(r"\\begin\s*\{\s*tikzpicture\b", code, re.I):
        raise ValueError("Chưa thấy \\begin{tikzpicture}.")
    if re.search(r"\\(?:begin|end)\s*\{\s*(?:ex|bt|document)\s*\}", code, re.I):
        raise ValueError("Mã TikZ không được bọc cả câu.")
    return code


def _lesson_tikz_items(src):
    src = str(src or "").replace("\\", "/").strip()
    if not src.startswith("ngan-hang/") or not src.lower().endswith(".tex"):
        raise ValueError("File không hợp lệ.")
    folder = base.lesson_folder(src)
    _p, local = base._safe_repo_file(folder)
    if not str(_p).startswith("ngan-hang/"):
        raise ValueError("Bài không hợp lệ.")
    items = []
    seen = set()

    def add(code, name, stored):
        if len(items) >= 24:
            return
        try:
            code = _clean_tikz_code(code)
        except ValueError:
            return
        hid = base.tikz_hash(code)
        if hid in seen:
            return
        seen.add(hid)
        base.tikz_remember(code)
        items.append(
            {
                "hid": hid,
                "name": str(name or "TikZ")[:48],
                "url": "/tikz/" + hid + ".png",
                "code": code,
                "stored": bool(stored),
            }
        )

    if local.is_dir():
        tikz_dir = local / "tikz"
        if tikz_dir.is_dir():
            for child in sorted(tikz_dir.glob("*.tex"), key=lambda p: p.name.lower()):
                try:
                    if child.stat().st_size > 30000:
                        continue
                    add(child.read_text(encoding="utf-8", errors="replace"), child.stem, True)
                except OSError:
                    continue
        for child in sorted(local.glob("*.tex"), key=lambda p: p.name.lower()):
            try:
                if child.stat().st_size > 800000:
                    continue
                text = child.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            n = 0
            for m in base.TIKZ_RE.finditer(text):
                n += 1
                add(m.group(0), child.stem + " · " + str(n), False)
                if len(items) >= 24:
                    break
            if len(items) >= 24:
                break
    return items


def _insert_question_tikz(src, fi, code):
    code = _clean_tikz_code(code)
    q, tex = _load_q(src, fi)
    if not q:
        raise ValueError("Không tìm thấy câu.")
    new_tex = None
    for i, m in enumerate(base.EX_RE.finditer(tex)):
        if i != fi:
            continue
        inner = m.group(1)
        head, tail = _split_head_tail(inner)
        comments, stem = _split_comments(head)
        if code in stem:
            base.tikz_remember(code)
            return "Câu đã có mã TikZ này."
        stem = code + "\n" + stem.strip()
        head_out = ((comments.rstrip() + "\n") if comments.strip() else "") + stem.strip() + "\n"
        new_tex = _replace_ex(tex, fi, head_out + (tail or ""))
        break
    if new_tex is None:
        raise ValueError("Không chèn được mã TikZ.")
    sha, _ = base.read_tex(src, need_sha=True)
    from admin_classify import _write_tex

    note = _write_tex(src, new_tex, "ADMIN chèn TikZ " + src, sha) or ""
    base.tikz_remember(code)
    try:
        from dang_routes import _STATS_CACHE, _QID_CACHE

        _STATS_CACHE.clear()
        _QID_CACHE.clear()
    except Exception:
        pass
    return note


def _store_lesson_tikz(src, code):
    code = _clean_tikz_code(code)
    folder = base.lesson_folder(src).rstrip("/")
    if not folder.startswith("ngan-hang/"):
        raise ValueError("Bài không hợp lệ.")
    name = "t-" + base.tikz_hash(code)[:10] + ".tex"
    rel = folder + "/tikz/" + name
    sha = None
    try:
        sha = base.github_file_sha(rel) or None
    except Exception:
        sha = None
    from admin_classify import _write_tex

    note = _write_tex(rel, code + "\n", "ADMIN cất mã TikZ " + name, sha) or ""
    base.tikz_remember(code)
    return {"file": "tikz/" + name, "name": name[:-4], "note": note}


@base.app.get("/api/admin/lesson-tikz")
def api_lesson_tikz():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    src = str(request.args.get("src") or "").replace("\\", "/").strip()
    try:
        items = _lesson_tikz_items(src)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    return jsonify(ok=True, items=items)


@base.app.post("/api/admin/lesson-tikz")
def api_lesson_tikz_act():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    src = str(data.get("src") or "").replace("\\", "/").strip()
    action = str(data.get("action") or "").strip().lower()
    if not src.startswith("ngan-hang/"):
        return jsonify(ok=False, error="File không hợp lệ."), 400
    try:
        if action == "store":
            saved = _store_lesson_tikz(src, data.get("code") or "")
            return jsonify(ok=True, **saved)
        fi = int(data.get("file_idx"))
        note = _insert_question_tikz(src, fi, data.get("code") or "")
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    return jsonify(ok=True, note=note)


REWRITE_CLIENT_JS = r"""
<style>.rwbar{margin:10px 0 0;padding:8px 10px;border:1px dashed #7dd3fc;border-radius:9px;background:#f0f9ff;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.rwout{width:100%}.rwprev{margin-top:8px;padding:10px;border:1px solid #bae6fd;border-radius:9px;background:#fff}.rwprev label{display:flex;gap:8px;align-items:center;font-weight:800;margin:8px 0 4px}.rwta{width:100%;min-height:120px;font:13px/1.45 Consolas,ui-monospace,monospace;padding:8px;border:1px solid #7dd3fc;border-radius:8px;margin:4px 0 8px}.rwta.sm{min-height:72px}.rwlook{margin:8px 0;padding:10px;border:1px dashed #bae6fd;border-radius:8px;background:#f8fbff}.rwquick{position:sticky;top:6px;z-index:3;display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:6px 8px;margin:6px 0 8px;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px}.rwquick .btn{padding:4px 8px;font-size:12px}.rwquick .muted{font-size:12px}.qcard.qhit{outline:3px solid #15803d;scroll-margin:88px}.rwimgsbox,.rwtikzbox{flex:1 1 100%;margin-top:8px;padding:8px;border:1px solid #bae6fd;border-radius:8px;background:#fff}.rwimggrid{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}.rwimgpick,.rwtikzpick{width:96px;border:2px solid #dbe7f3;border-radius:8px;background:#f8fbff;padding:4px;cursor:pointer;text-align:center}.rwimgpick img,.rwtikzpick img{width:88px;height:68px;object-fit:contain;display:block;background:#fff}.rwimgpick.on{border-color:#15803d;background:#f0fdf4}.rwimgpick small,.rwtikzpick small{display:block;font-size:10px;line-height:1.2;color:#475569;word-break:break-all;margin-top:3px}.rwtikzpick{width:128px}.rwtikzpick img{width:120px;height:84px}</style>
<script>
(function(){
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}
function stripMeta(s){
  return String(s||'').replace(/\\\\begin\s*\{\s*(?:ex|bt)\s*\}/gi,'').replace(/\\\\end\s*\{\s*(?:ex|bt)\s*\}/gi,'').split(/\r?\n/).filter(function(l){
    var t=l.replace(/^\uFEFF/,'').trim();
    if(!t) return false;
    var c=t.charAt(0);
    return c!=='%' && c!=='\uFF05';
  }).join('\n').replace(/\n{3,}/g,'\n\n').trim();
}
function keys(){return (window.ldvlFilledKeys&&ldvlFilledKeys())||[];}
var aiShots=[];
var aiDocs=[];
var aiPdfs=[];
var aiTexNames=[];
function bagSlots(){return aiDocs.length+aiPdfs.length;}
function bagChars(){
  var n=0;
  aiDocs.forEach(function(x){n+=(x.b64||'').length;});
  aiPdfs.forEach(function(x){n+=(x.b64||'').length;});
  return n;
}
function renderIntake(){
  var box=document.getElementById('aiShots');
  if(!box) return;
  var h='';
  aiDocs.forEach(function(x,i){
    h+='<span class="ai-chip">'+esc(x.name)+'<button type="button" data-clear-docx="'+i+'" title="Bỏ Word">×</button></span>';
  });
  aiPdfs.forEach(function(x,i){
    h+='<span class="ai-chip">'+esc(x.name)+'<button type="button" data-clear-pdf="'+i+'" title="Bỏ PDF">×</button></span>';
  });
  aiTexNames.forEach(function(name){
    h+='<span class="ai-chip">'+esc(name)+'</span>';
  });
  aiShots.forEach(function(s,i){
    h+='<span class="ai-shot"><img alt="" src="'+s.url+'"><button type="button" data-shot="'+i+'" title="Bỏ ảnh">×</button></span>';
  });
  box.innerHTML=h;
}
function addImageFile(file){
  if(aiShots.length>=12){alert('Tối đa 12 ảnh.');return;}
  if(file.size>8000000){alert('Ảnh quá lớn.');return;}
  var img=new Image();
  var url=URL.createObjectURL(file);
  img.onload=function(){
    var max=1400,w=img.width||1,h=img.height||1,sc=Math.min(1,max/Math.max(w,h));
    w=Math.max(1,Math.round(w*sc)); h=Math.max(1,Math.round(h*sc));
    var c=document.createElement('canvas'); c.width=w; c.height=h;
    c.getContext('2d').drawImage(img,0,0,w,h);
    URL.revokeObjectURL(url);
    var dataUrl=c.toDataURL('image/jpeg',0.82);
    var b64=(dataUrl.split(',')[1]||'');
    if(b64.length>1800000){alert('Ảnh vẫn quá nặng sau khi thu nhỏ.');return;}
    aiShots.push({url:dataUrl,mime:'image/jpeg',data:b64});
    renderIntake();
  };
  img.onerror=function(){URL.revokeObjectURL(url);};
  img.src=url;
}
function addDocxFile(file){
  var name=file.name||'tai-lieu.doc';
  var isDocx=/\.docx$/i.test(name)||/wordprocessingml/i.test(file.type||'');
  var isDoc=/\.doc$/i.test(name)||/msword/i.test(file.type||'')||isDocx;
  if(!isDoc){alert('Chỉ nhận file Word .doc hoặc .docx.');return;}
  if(file.size>6000000){alert('File Word quá lớn (dưới 6MB).');return;}
  if(bagSlots()>=6){alert('Tối đa 6 file Word/PDF một lần.');return;}
  var r=new FileReader();
  r.onload=function(){
    var dataUrl=String(r.result||'');
    var b64=dataUrl.split(',')[1]||'';
    if(bagChars()+b64.length>12000000){alert('Tổng các file quá nặng (dưới khoảng 9MB).');return;}
    aiDocs.push({name:name||'de.doc', b64:b64});
    var n=showWordImages(b64);
    renderIntake();
    if(n) aiStatus('Thấy '+n+' ảnh trong file Word. Đang lưu lên GitHub…','wait');
    else aiStatus('Chưa thấy ảnh nhúng trong file. Thả đúng file .doc/.docx, không cần Save As.','err');
    pushDocxImages(b64);
  };
  r.readAsDataURL(file);
}
function u32be(s,i){
  return ((s.charCodeAt(i)<<24)|(s.charCodeAt(i+1)<<16)|(s.charCodeAt(i+2)<<8)|s.charCodeAt(i+3))>>>0;
}
function addShotB64(b64, mime){
  if(!b64||aiShots.length>=12) return false;
  var head=b64.slice(0,80);
  if(aiShots.some(function(s){return (s.data||'').slice(0,80)===head;})) return false;
  aiShots.push({url:'data:'+mime+';base64,'+b64, mime:mime, data:b64});
  return true;
}
function showWordImages(b64){
  var bin='';
  try{ bin=atob(b64); }catch(e){ return 0; }
  var n=0, i=0, sig='\x89PNG\r\n\x1a\n';
  while(n<12){
    var j=bin.indexOf(sig,i);
    if(j<0) break;
    var k=bin.indexOf('IEND', j+8);
    if(k<0){ i=j+8; continue; }
    var slice=bin.slice(j, k+8);
    var w=slice.length>=24?u32be(slice,16):0;
    var h=slice.length>=24?u32be(slice,20):0;
    if(slice.length>=2500 && (!w||!h||(w>=64&&h>=64))){
      try{ if(addShotB64(btoa(slice),'image/png')) n++; }catch(e){}
    }
    i=k+8;
  }
  i=0;
  sig='\xff\xd8\xff';
  while(n<12){
    j=bin.indexOf(sig,i);
    if(j<0) break;
    k=bin.indexOf('\xff\xd9', j+3);
    if(k<0) break;
    slice=bin.slice(j, k+2);
    if(slice.length>=2500 && slice.length<=400000){
      try{ if(addShotB64(btoa(slice),'image/jpeg')) n++; }catch(e){}
    }
    i=k+2;
  }
  return n;
}
async function pushDocxImages(b64){
  var bar=document.querySelector('.admindang');
  var path=bar? (bar.getAttribute('data-path')||'') : '';
  if(!b64) return;
  if(!aiShots.length) aiStatus('Đang tách ảnh trong Word…','wait');
  try{
    var r=await fetch('/api/admin/docx-images',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:path, docx:b64})});
    var d=await r.json();
    if(!d.ok){
      if(aiShots.length) aiStatus('Đã hiện '+aiShots.length+' ảnh. Lưu GitHub chưa xong: '+(d.error||'lỗi')+'.','err');
      else aiStatus(d.error||'Không tách được ảnh Word.','err');
      return;
    }
    var n=0;
    (d.images||[]).forEach(function(im){
      if(im.data && addShotB64(im.data, im.mime||'image/png')) n++;
      if(!im.file) return;
      var head=(im.data||'').slice(0,80);
      aiShots.forEach(function(s){
        if(head && (s.data||'').slice(0,80)===head) s.file=im.file;
      });
    });
    renderIntake();
    if(!aiShots.length) aiStatus('Word không có ảnh đủ lớn để tách (bỏ icon nhỏ).','ok');
    else aiStatus('Đã hiện '+aiShots.length+' ảnh từ Word'+(n?' , đã lưu GitHub.':' .')+' Không cần Save As.','ok');
  }catch(err){
    if(aiShots.length) aiStatus('Đã hiện '+aiShots.length+' ảnh trong khung. '+String(err&&err.message||err),'err');
    else aiStatus(String(err&&err.message||err),'err');
  }
}
function addPdfFile(file){
  var name=file.name||'de.pdf';
  if(!/\.pdf$/i.test(name)&&file.type!=='application/pdf'){alert('Chỉ nhận file PDF.');return;}
  if(file.size>8000000){alert('File PDF quá lớn (dưới 8MB).');return;}
  if(bagSlots()>=6){alert('Tối đa 6 file Word/PDF một lần.');return;}
  var r=new FileReader();
  r.onload=function(){
    var b64=String(r.result||'').split(',')[1]||'';
    if(bagChars()+b64.length>12000000){alert('Tổng các file quá nặng (dưới khoảng 9MB).');return;}
    aiPdfs.push({name:name, b64:b64});
    renderIntake();
  };
  r.readAsDataURL(file);
}
function addTexFile(file){
  if(file.size>900000){alert('File chữ quá lớn (dưới 900KB).');return;}
  var r=new FileReader();
  r.onload=function(){
    var ta=document.getElementById('aiPaste');
    if(!ta) return;
    var t=String(r.result||'').replace(/^\uFEFF/,'');
    ta.value=(ta.value&&ta.value.trim())?(ta.value.replace(/\s+$/,'')+'\n\n'+t):t;
    aiTexNames.push(file.name||'de.tex');
    renderIntake();
    ta.focus();
  };
  r.readAsText(file,'UTF-8');
}
function takeFiles(files){
  Array.prototype.forEach.call(files||[], function(file){
    var name=file.name||'';
    if(/^image\//.test(file.type)||/\.(png|jpe?g|webp|gif)$/i.test(name)) addImageFile(file);
    else if(/\.docx?$/i.test(name)||/wordprocessingml/i.test(file.type||'')) addDocxFile(file);
    else if(/\.pdf$/i.test(name)||file.type==='application/pdf') addPdfFile(file);
    else if(/\.(tex|ltx|txt)$/i.test(name)||file.type==='text/plain') addTexFile(file);
    else alert('Chỉ nhận ảnh, Word .docx, PDF hoặc file .tex/.txt.');
  });
}
function readAiSrcFile(){
  return new Promise(function(resolve,reject){
    const inp=document.getElementById('aiSrcFile');
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
  var t=e.target;
  if(!t||(t.id!=='aiSrcFile'&&t.id!=='aiImgFile')) return;
  takeFiles(t.files);
  t.value='';
});
document.addEventListener('click',function(e){
  var btn=e.target&&e.target.closest&&e.target.closest('#aiShots button');
  if(!btn) return;
  e.preventDefault();
  if(btn.getAttribute('data-clear-docx')!=null){aiDocs.splice(+btn.getAttribute('data-clear-docx'),1);renderIntake();return;}
  if(btn.getAttribute('data-clear-pdf')!=null){aiPdfs.splice(+btn.getAttribute('data-clear-pdf'),1);renderIntake();return;}
  var i=btn.getAttribute('data-shot');
  if(i!=null){aiShots.splice(+i,1);renderIntake();}
});
document.addEventListener('paste',function(e){
  var tray=document.getElementById('aiIntake');
  if(!tray||!e.clipboardData) return;
  var ae=document.activeElement;
  if(ae!==tray&&!tray.contains(ae)) return;
  var files=[];
  var items=e.clipboardData.items||[];
  for(var i=0;i<items.length;i++){
    if(items[i].kind==='file'){
      var f=items[i].getAsFile();
      if(!f) continue;
      var fname=f.name||'';
      if(/^image\//.test(f.type||'')||/\.docx$/i.test(fname)||/wordprocessingml/i.test(f.type||'')) files.push(f);
    }
  }
  if(!files.length) return;
  e.preventDefault();
  takeFiles(files);
});
document.addEventListener('dragover',function(e){
  var tray=e.target&&e.target.closest&&e.target.closest('#aiIntake');
  if(!tray) return;
  e.preventDefault();
  tray.classList.add('over');
});
document.addEventListener('dragleave',function(e){
  var tray=e.target&&e.target.closest&&e.target.closest('#aiIntake');
  if(tray) tray.classList.remove('over');
});
document.addEventListener('drop',function(e){
  var tray=e.target&&e.target.closest&&e.target.closest('#aiIntake');
  if(!tray) return;
  e.preventDefault();
  tray.classList.remove('over');
  takeFiles(e.dataTransfer&&e.dataTransfer.files);
});
function dropOf(btn){
  const raw=btn.getAttribute('data-drop')||'';
  const i=raw.lastIndexOf('||');
  if(i<0) return null;
  return {src:raw.slice(0,i), fi:+raw.slice(i+2)};
}
function outBox(btn){
  let box=btn.parentElement&&btn.parentElement.querySelector('.rwout');
  if(!box){box=document.createElement('div');box.className='rwout';btn.parentElement.appendChild(box);}
  return box;
}
function readDraft(box, d){
  const stem=stripMeta((box.querySelector('[data-ta=stem]')||{}).value);
  const solution=stripMeta((box.querySelector('[data-ta=sol]')||{}).value);
  const answer=stripMeta((box.querySelector('[data-ta=ans]')||{}).value);
  const flags={};
  box.querySelectorAll('.rwf').forEach(function(x){flags[x.getAttribute('data-k')]=x.checked});
  const opts=(d.options||[]).map(function(o,i){
    const el=box.querySelector('[data-ta=opt-'+i+']');
    return {text:stripMeta(el?el.value:(o.text||'')), correct:!!o.correct};
  });
  return {stem:stem||d.stem, solution:solution||d.solution, answer:answer||d.answer, options:opts, flags:flags};
}
function rwField(box){
  const a=box._rwTa;
  if(a&&box.contains(a)) return a;
  return box.querySelector('.rwta');
}
function rwPut(ta, text, cursorFromEnd){
  const v=ta.value, a=ta.selectionStart||0, b=ta.selectionEnd||0;
  ta.value=v.slice(0,a)+text+v.slice(b);
  const p=a+text.length-(cursorFromEnd||0);
  ta.focus();
  ta.selectionStart=ta.selectionEnd=p;
}
function rwWrap(ta, open, close){
  const v=ta.value, a=ta.selectionStart||0, b=ta.selectionEnd||0;
  const sel=v.slice(a,b);
  if(sel.length>=open.length+close.length && sel.indexOf(open)===0 && sel.slice(-close.length)===close){
    const inner=sel.slice(open.length, sel.length-close.length);
    ta.value=v.slice(0,a)+inner+v.slice(b);
    ta.focus();
    ta.selectionStart=a;
    ta.selectionEnd=a+inner.length;
    return;
  }
  ta.value=v.slice(0,a)+open+sel+close+v.slice(b);
  ta.focus();
  if(!sel){ta.selectionStart=ta.selectionEnd=a+open.length;}
  else{ta.selectionStart=a+open.length;ta.selectionEnd=a+open.length+sel.length;}
}
function rwGlue(s){
  if(String(s||'').indexOf('\n')>=0) return false;
  const raw=String(s||'');
  let u=raw.replace(/\\(?:times|cdot|pm|mp|left|right|quad|Rightarrow|to)\b/g,'');
  u=u.replace(/\s+/g,'');
  if(!u) return /\\(?:times|cdot|pm|mp)\b|[+\-=≈≡×·]/.test(raw);
  if(u===')'||u===').'||u===');') return false;
  return /^[+\-=≈≡×·(),.]+$/.test(u);
}
function rwFixDollars(t){
  const ms=[];
  const re=/\$([^$]*)\$/g;
  let m;
  while((m=re.exec(t))) ms.push({s:m.index,e:m.index+m[0].length,inner:m[1]});
  let out='', last=0, i=0;
  if(ms.length>=2){
    while(i<ms.length){
      const cur=ms[i];
      out+=t.slice(last, cur.s);
      const buf=[cur.inner];
      let end=cur.e;
      i++;
      while(i<ms.length && rwGlue(t.slice(end, ms[i].s))){
        buf.push(t.slice(end, ms[i].s));
        buf.push(ms[i].inner);
        end=ms[i].e;
        i++;
      }
      out+='$'+buf.join('').replace(/\$/g,'')+'$';
      last=end;
    }
    out+=t.slice(last);
    t=out;
  }
  return t.replace(/\$\s*\$/g,'');
}
function rwNormUnit(unit){
  if(unit==='°C' || /^\\circ\s*C$/.test(unit)) return '^{\\circ}\\mathrm{C}';
  return '\\mathrm{'+unit+'}';
}
function rwCommaInner(inner){
  const parts=String(inner||'').split(/(\\(?:text|mathrm|textbf|textit)\{[^{}]*\})/g);
  return parts.map(function(part,i){
    if(i%2) return part;
    return part.replace(/(\d),(\d)/g,'$1{,}$2');
  }).join('');
}
function rwFixCommas(t){
  return String(t||'').replace(/\$([^$]+)\$|\\\(([\s\S]*?)\\\)|\\\[([\s\S]*?)\\\]/g, function(all, a, b, c){
    const open=a!=null?'$':(b!=null?'\\(':'\\[');
    const close=a!=null?'$':(b!=null?'\\)':'\\]');
    const inner=a!=null?a:(b!=null?b:c);
    return open+rwCommaInner(inner)+close;
  });
}
function rwFixUnits(t){
  const u='(?:m/s\\^\\{2\\}|m/s\\^2|kg/m\\^\\{3\\}|kg/m\\^3|J/kg\\.K|J/kg|rad/s|m/s|kWh|°C|\\\\circ\\s*C|kPa|MPa|kHz|kJ|MJ|mJ|kW|MW|kN|kg|mg|km|cm|mm|dm|ms|kV|mV|mol|eV|Pa|Hz|rad|atm|cal|min|J|W|N|V|A|K|g|m|s|h)';
  const after=new RegExp('\\$([^$]+?)\\$\\s*('+u+')(?![A-Za-zÀ-ỹ0-9\\\\{])','g');
  t=String(t||'').replace(after, function(all, inner, unit){
    const inn=inner.replace(/\s+$/,'');
    if(!/[\d})]$/.test(inn)) return all;
    if(/\\mathrm\s*\{[^}]*\}\s*$/.test(inn) || /\^\{?\\circ\}?\s*\\mathrm\{C\}\s*$/.test(inn)) return all;
    return '$'+inn+'\\,'+rwNormUnit(unit)+'$';
  });
  const inside=new RegExp('\\$([^$]*\\d)\\s+('+u+')\\s*\\$','g');
  t=t.replace(inside, function(all, inner, unit){
    if(/\\mathrm\s*\{/.test(all)) return all;
    return '$'+inner+'\\,'+rwNormUnit(unit)+'$';
  });
  return rwFixCommas(t);
}
function rwSteps(text){
  let s=String(text||'').trim();
  if(!s) return s;
  s=s.replace(/\s*=\s*/g,' \\\\\n= ');
  if(s.indexOf('\\[')<0 && s.indexOf('\\]')<0) s='\\[\n'+s+'\n\\]';
  return s;
}
async function rwShowSaved(box, note){
  const card=box.closest&&box.closest('.qcard');
  if(!card){
    box.innerHTML='<div class="success">'+note+'</div>';
    const q=document.getElementById('q');
    if(q) q.scrollIntoView({block:'start'});
    location.reload();
    return;
  }
  const lab=card.querySelector('.qcheck span');
  const m=(lab&&lab.textContent||'').match(/(\d+)\s*\/\s*(\d+)/);
  const seq=m?m[1]:'1';
  const total=m?m[2]:seq;
  const drop=card.getAttribute('data-drop')||'';
  const cut=drop.lastIndexOf('||');
  const src=cut>=0?drop.slice(0,cut):'';
  const fi=cut>=0?drop.slice(cut+2):'';
  box.innerHTML='<div class="success">'+note+'</div>';
  try{
    const r=await fetch('/api/admin/question-card?src='+encodeURIComponent(src)+'&file_idx='+encodeURIComponent(fi)+'&seq='+encodeURIComponent(seq)+'&total='+encodeURIComponent(total),{credentials:'same-origin'});
    const d=await r.json();
    if(!d.ok||!d.html){card.classList.add('qhit');card.scrollIntoView({block:'center'});return;}
    const hold=document.createElement('div');
    hold.innerHTML=d.html;
    const neu=hold.querySelector('.qcard')||hold.firstElementChild;
    if(!neu){card.classList.add('qhit');card.scrollIntoView({block:'center'});return;}
    neu.classList.add('qhit');
    neu.insertAdjacentHTML('afterbegin','<div class="success">'+note+'</div>');
    card.replaceWith(neu);
    neu.scrollIntoView({block:'center'});
    if(window.ldvlTypeset) ldvlTypeset(neu);
    if(window.ldvlSplitPics) ldvlSplitPics(neu);
  }catch(err){
    card.classList.add('qhit');
    card.scrollIntoView({block:'center'});
  }
}
function rwQuick(box, kind){
  const ta=rwField(box);
  if(!ta) return;
  if(kind==='dollar') rwWrap(ta,'$','$');
  else if(kind==='display') rwWrap(ta,'\\[\n','\n\\]');
  else if(kind==='lbr') rwPut(ta,'\\\\\n');
  else if(kind==='nl') rwPut(ta,'\n');
  else if(kind==='frac') rwPut(ta,'\\frac{}{}',3);
  else if(kind==='cdot') rwPut(ta,'\\cdot ');
  else if(kind==='delta') rwPut(ta,'\\Delta ');
  else if(kind==='unit'){
    const a=ta.selectionStart||0;
    ta.value=rwFixUnits(ta.value);
    ta.focus();
    const p=Math.min(a, ta.value.length);
    ta.selectionStart=ta.selectionEnd=p;
  }else if(kind==='fix'){
    const a=ta.selectionStart||0;
    ta.value=rwFixDollars(ta.value);
    ta.focus();
    const p=Math.min(a, ta.value.length);
    ta.selectionStart=ta.selectionEnd=p;
  }else if(kind==='steps'){
    const v=ta.value;
    let a=ta.selectionStart||0, b=ta.selectionEnd||0;
    if(a===b){
      a=v.lastIndexOf('\n', Math.max(0,a-1))+1;
      b=v.indexOf('\n', ta.selectionStart||0);
      if(b<0) b=v.length;
    }
    const next=rwSteps(v.slice(a,b));
    ta.value=v.slice(0,a)+next+v.slice(b);
    ta.focus();
    ta.selectionStart=a;
    ta.selectionEnd=a+next.length;
  }
}
async function previewBox(box){
  const tas=box.querySelectorAll('.rwta');
  const look=box.querySelector('.rwlook');
  if(!look) return;
  look.innerHTML='⏳ Đang xem trước...';
  const parts=[];
  try{
    for(const ta of tas){
      const lab=ta.getAttribute('data-lab')||'';
      const r=await fetch('/api/admin/tex-preview',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({tex:ta.value||'',src:box._rwSrc||''})});
      const raw=await r.text();
      let d={};
      try{d=JSON.parse(raw);}catch(err){throw new Error('Máy chủ không trả xem trước (HTTP '+r.status+').');}
      parts.push('<div class="muted">'+esc(lab)+'</div><div>'+(d.html||'')+'</div>');
    }
  }catch(err){
    look.innerHTML='<div class="err">'+esc(err&&err.message||err)+'</div>';
    return;
  }
  look.innerHTML=parts.join('');
  if(window.ldvlArmTikz) ldvlArmTikz(look);
  if(window.ldvlTypeset) ldvlTypeset(look);
}
function showEditor(box, d){
  d.stem=stripMeta(d.stem||'');
  d.solution=stripMeta(d.solution||'');
  d.answer=stripMeta(d.answer||'');
  (d.options||[]).forEach(function(o){o.text=stripMeta(o.text||'')});
  const develop=!!d.develop;
  const verb=develop?'Ghi':'Thay';
  let h='<div class="rwprev"><div class="success">'+(develop?'Phát triển từ câu — chưa ghi. Sửa số hoặc từ, bấm Tính lại lời giải và đáp án, rồi thêm để học sinh tham khảo. Câu gốc giữ nguyên.':'Chưa ghi file. Sửa LaTeX trong ô, bấm Xem trước, rồi Chấp nhận.')+'</div>';
  if(d.note) h+='<p class="muted">'+esc(d.note)+'</p>';
  h+='<div class="rwquick"><b>Nhanh</b>'
    +'<button type="button" class="btn mini" data-q="dollar" title="Bọc đoạn bôi đen bằng $...$">$…$</button>'
    +'<button type="button" class="btn mini" data-q="display" title="Bọc bằng \\\\[ \\\\]">\\[ \\]</button>'
    +'<button type="button" class="btn mini" data-q="lbr" title="Chèn \\\\\\\\ để xuống dòng trong công thức">\\\\ xuống dòng</button>'
    +'<button type="button" class="btn mini" data-q="nl" title="Xuống dòng trong ô soạn">Xuống dòng</button>'
    +'<button type="button" class="btn mini" data-q="steps" title="Mỗi dấu = một dòng, bọc \\\\[ \\\\]">Tách bước =</button>'
    +'<button type="button" class="btn mini" data-q="fix" title="Gộp $a$ + $b$ thành $a+b$">Sửa $</button>'
    +'<button type="button" class="btn mini" data-q="unit" title="Số và đơn vị thành $x=4{,}5\\\\,\\\\mathrm{cm}$">Sửa đơn vị</button>'
    +'<button type="button" class="btn mini" data-q="frac">\\frac</button>'
    +'<button type="button" class="btn mini" data-q="cdot">\\cdot</button>'
    +'<button type="button" class="btn mini" data-q="delta">\\Delta</button>'
    +'<span class="muted">Bôi đen trong ô đang gõ, rồi bấm.</span></div>';
  h+='<label><input type="checkbox" class="rwf" data-k="stem" checked> '+verb+' đề</label>';
  h+='<textarea class="rwta" data-ta="stem" data-lab="Đề" spellcheck="false">'+esc(d.stem||'')+'</textarea>';
  (d.options||[]).forEach(function(o,i){
    if(!i) h+='<label><input type="checkbox" class="rwf" data-k="opts" checked> '+verb+' phương án và đáp án đúng</label>';
    h+='<textarea class="rwta sm" data-ta="opt-'+i+'" data-lab="PA '+(d.kind==='TN'?'ABCD'[i]:(i+1))+'" spellcheck="false">'+esc(o.text||'')+'</textarea>';
  });
  if(d.kind==='TLN'){
    h+='<label><input type="checkbox" class="rwf" data-k="answer" checked> '+verb+' đáp án TLN</label>';
    h+='<textarea class="rwta sm" data-ta="ans" data-lab="Đáp án" spellcheck="false">'+esc(d.answer||'')+'</textarea>';
  }
  h+='<label><input type="checkbox" class="rwf" data-k="sol" checked> '+verb+' lời giải</label>';
  h+='<textarea class="rwta" data-ta="sol" data-lab="Lời giải" style="min-height:180px" spellcheck="false">'+esc(d.solution||'')+'</textarea>';
  h+='<p><button type="button" class="btn rwPrev">👁 Xem trước</button> <button type="button" class="btn rwRecalc">🔁 Tính lại lời giải và đáp án</button> <button type="button" class="btn green rwSave">'+(develop?'✅ Thêm Phát triển từ câu':'✅ Chấp nhận và ghi TEX')+'</button> <button type="button" class="btn rwCancel">Hủy</button></p>';
  h+='<div class="rwlook"></div></div>';
  box._rwSrc=d.src||box._rwSrc||'';
  box.innerHTML=h;
  box.addEventListener('focusin',function(e){
    if(e.target&&e.target.classList&&e.target.classList.contains('rwta')) box._rwTa=e.target;
  });
  box.querySelectorAll('[data-q]').forEach(function(b){
    b.addEventListener('mousedown',function(e){e.preventDefault();});
    b.onclick=function(){rwQuick(box, b.getAttribute('data-q'));};
  });
  box.querySelector('.rwCancel').onclick=function(){box.innerHTML='';};
  box.querySelector('.rwPrev').onclick=function(){previewBox(box)};
  box.querySelector('.rwRecalc').onclick=async function(){
    const btn=this;
    const look=box.querySelector('.rwlook');
    const ks=keys();
    if(!ks.length){alert('Nạp key Gemini (trang 🤖 Gemini) rồi thử lại.');return;}
    btn.disabled=true;
    if(look) look.innerHTML='⏳ Đang tính lại lời giải và đáp án theo số hoặc từ vừa sửa...';
    try{
      const x=readDraft(box,d);
      const r=await fetch('/api/admin/rewrite-question',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({src:d.src,file_idx:d.file_idx,mode:'recalc',develop:develop,api_keys:ks,stem:x.stem,options:x.options,solution:x.solution,answer:x.answer})});
      const back=await r.json();
      if(!back.ok){if(look) look.innerHTML='<div class="err">'+(back.error||'Lỗi')+'</div>';btn.disabled=false;return;}
      showEditor(box, back);
    }catch(err){if(look) look.innerHTML='<div class="err">'+esc(err)+'</div>';btn.disabled=false;}
  };
  box.querySelector('.rwSave').onclick=async function(){
    const btn=this;
    if(!confirm(develop?'Thêm vào mục Phát triển từ câu để học sinh tham khảo? Câu gốc không đổi.':'Ghi đề/lời giải vào TEX + GitHub?'))return;
    btn.disabled=true;
    try{
      const x=readDraft(box,d);
      const s=await fetch('/api/admin/rewrite-question-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({src:d.src,file_idx:d.file_idx,stem:x.stem,solution:x.solution,answer:x.answer,options:x.options,
          apply_stem:!!x.flags.stem,apply_opts:!!x.flags.opts,apply_sol:!!x.flags.sol,apply_answer:!!x.flags.answer,save_as:develop?'develop':''})});
      const txt=await s.text();
      let sd={};
      try{sd=JSON.parse(txt)}catch(err){
        alert('Máy chủ không trả kết quả (HTTP '+s.status+'). Thử lại.');
        btn.disabled=false;return;
      }
      if(!sd.ok){alert(sd.error||'Không ghi được');btn.disabled=false;return;}
      rwShowSaved(box, develop?'✅ Đã thêm Phát triển từ câu.':'✅ Đã ghi câu này.');
    }catch(err){alert('Không ghi được: '+err);btn.disabled=false;}
  };
  previewBox(box);
}
async function loadRewrite(src, fi, box, mode){
  box.innerHTML=mode==='edit'?'⏳ Đang tải lời giải hiện tại...':(mode==='similar'?'⏳ Đang phát triển từ câu và tính lời giải, đáp án mới...':'⏳ AI đang viết lại đề và lời giải...');
  try{
    const body={src:src,file_idx:fi,mode:mode||'ai'};
    if(mode!=='edit') body.api_keys=keys();
    if(mode!=='edit'&&!(body.api_keys||[]).length){alert('Nạp key Gemini (trang 🤖 Gemini) rồi thử lại.');box.innerHTML='';return;}
    const r=await fetch('/api/admin/rewrite-question',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    const d=await r.json();
    if(!d.ok){box.innerHTML='<div class="err">'+(d.error||'Lỗi')+'</div>';return;}
    showEditor(box,d);
  }catch(e){box.innerHTML='<div class="err">'+e+'</div>';}
}
function rwFigLine(file){
  return '\\begin{center}\\includegraphics[width=0.55\\linewidth]{'+file+'}\\end{center}\n';
}
function rwStripFigs(text){
  return String(text||'')
    .replace(/\\begin\{center\}[\s\S]*?\\includegraphics[\s\S]*?\\end\{center\}\s*/gi,'')
    .replace(/\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}(?:\s*\\hfill|\s*\\\\(?:\[[^\]]*\])?)?\s*/gi,'');
}
async function rwLoadImgs(box){
  box.innerHTML='<div class="muted">Đang mở ảnh trong thư mục bài...</div>';
  try{
    const r=await fetch('/api/admin/lesson-images?src='+encodeURIComponent(box.getAttribute('data-src')||'')+'&file_idx='+encodeURIComponent(box.getAttribute('data-fi')||''),{credentials:'same-origin'});
    const d=await r.json();
    if(!d.ok){box.innerHTML='<div class="err">'+esc(d.error||'Không mở được thư mục ảnh.')+'</div>';return;}
    const used=d.used||[];
    let h='<div class="muted">Ảnh trong thư mục bài. Bấm một ảnh để gắn vào câu. Bấm ảnh viền xanh để bỏ.</div><div class="rwimggrid">';
    (d.images||[]).forEach(function(im){
      const on=used.indexOf(im.file)>=0?' on':'';
      h+='<button type="button" class="rwimgpick'+on+'" data-file="'+esc(im.file)+'"><img alt="" src="'+esc(im.url)+'"><small>'+esc(im.name)+'</small></button>';
    });
    h+='</div>';
    if(!(d.images||[]).length) h+='<div class="muted">Thư mục images/ của bài chưa có ảnh.</div>';
    h+='<label class="btn mini">Tải ảnh mới vào thư mục<input class="rwimgfile" type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden></label>';
    box.innerHTML=h;
  }catch(err){box.innerHTML='<div class="err">'+esc(err)+'</div>';}
}
async function rwApplyImg(box, file, action){
  const bar=box.closest('.rwbar');
  const out=bar&&bar.querySelector('.rwout');
  const ta=out&&out.querySelector('[data-ta=stem]');
  const editor=out&&out.querySelector('.rwprev');
  let msg=action==='clear'?'Bỏ ảnh khỏi câu này và ghi TEX?':'Gắn ảnh này vào câu và ghi TEX?';
  if(editor) msg+=' Ô sửa đề đang mở sẽ đóng.';
  if(!confirm(msg)) return;
  try{
    const r=await fetch('/api/admin/lesson-image',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({src:box.getAttribute('data-src')||'',file_idx:+(box.getAttribute('data-fi')||0),action:action,file:file||''})});
    const d=await r.json();
    if(!d.ok){alert(d.error||'Không ghi được ảnh');return;}
    if(ta){
      let v=rwStripFigs(ta.value).replace(/^\s+/,'');
      if(action==='set') v=rwFigLine(file)+v;
      ta.value=v;
    }
    rwShowSaved(out||box, action==='clear'?'✅ Đã bỏ ảnh khỏi câu.':'✅ Đã gắn ảnh vào câu.');
  }catch(err){alert(String(err&&err.message||err));}
}
async function rwUploadImg(box, file){
  if(!file) return;
  if(file.size>4000000){alert('Ảnh quá lớn (dưới 4MB).');return;}
  const reader=new FileReader();
  reader.onload=async function(){
    const b64=String(reader.result||'').split(',')[1]||'';
    box.insertAdjacentHTML('afterbegin','<div class="muted">Đang lưu ảnh vào thư mục...</div>');
    try{
      const r=await fetch('/api/admin/lesson-image',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({src:box.getAttribute('data-src')||'',action:'upload',data:b64})});
      const d=await r.json();
      if(!d.ok){alert(d.error||'Không lưu được ảnh');rwLoadImgs(box);return;}
      rwLoadImgs(box);
    }catch(err){alert(String(err&&err.message||err));}
  };
  reader.readAsDataURL(file);
}
window.ldvlAdminRewrite=function(src,fi,box){loadRewrite(src,fi,box,'ai')};
window.ldvlAdminSimilar=function(src,fi,box){loadRewrite(src,fi,box,'similar')};
window.ldvlAdminEdit=function(src,fi,box){loadRewrite(src,fi,box,'edit')};
document.addEventListener('click',function(e){
  const go=e.target.closest&&e.target.closest('.rwgo');
  const sim=e.target.closest&&e.target.closest('.rwsim');
  const ed=e.target.closest&&e.target.closest('.rwedit');
  const btn=go||sim||ed;
  if(!btn) return;
  e.preventDefault();
  const p=dropOf(btn);
  if(!p) return;
  loadRewrite(p.src,p.fi,outBox(btn),ed?'edit':(sim?'similar':'ai'));
});
document.addEventListener('click',function(e){
  const openBtn=e.target.closest&&e.target.closest('.rwimgs');
  if(openBtn){
    e.preventDefault();
    const bar=openBtn.closest('.rwbar');
    if(!bar) return;
    const old=bar.querySelector('.rwimgsbox');
    if(old){old.remove();return;}
    const p=dropOf(openBtn);
    if(!p) return;
    const box=document.createElement('div');
    box.className='rwimgsbox';
    box.setAttribute('data-src', p.src);
    box.setAttribute('data-fi', String(p.fi));
    const out=bar.querySelector('.rwout');
    if(out) out.insertAdjacentElement('afterend', box);
    else bar.appendChild(box);
    rwLoadImgs(box);
    return;
  }
  const pick=e.target.closest&&e.target.closest('.rwimgpick');
  if(!pick) return;
  e.preventDefault();
  const box=pick.closest('.rwimgsbox');
  if(!box) return;
  rwApplyImg(box, pick.getAttribute('data-file')||'', pick.classList.contains('on')?'clear':'set');
});
document.addEventListener('change',function(e){
  const inp=e.target;
  if(!inp||!inp.classList||!inp.classList.contains('rwimgfile')) return;
  const box=inp.closest('.rwimgsbox');
  const f=inp.files&&inp.files[0];
  inp.value='';
  if(box&&f) rwUploadImg(box, f);
});
async function rwLoadTikz(box){
  box.innerHTML='<div class="muted">Đang mở mã TikZ đã vẽ trong bài...</div>';
  try{
    const r=await fetch('/api/admin/lesson-tikz?src='+encodeURIComponent(box.getAttribute('data-src')||''),{credentials:'same-origin'});
    const d=await r.json();
    if(!d.ok){box.innerHTML='<div class="err">'+esc(d.error||'Không mở được mã TikZ.')+'</div>';return;}
    box._tikz={};
    let h='<div class="muted">Mã TikZ trong thư mục tikz/ của bài và mã đã có trong file TEX. Bấm hình để chèn vào câu. Cất để giữ mã vào thư mục.</div><div class="rwimggrid">';
    (d.items||[]).forEach(function(im){
      box._tikz[im.hid]=im.code||'';
      h+='<div class="rwtikzpick" data-hid="'+esc(im.hid)+'"><img alt="" src="'+esc(im.url)+'" loading="lazy"><small>'+esc(im.name)+'</small>';
      if(!im.stored) h+='<button type="button" class="btn mini rwtikzsave" data-hid="'+esc(im.hid)+'">Cất</button>';
      h+='</div>';
    });
    h+='</div>';
    if(!(d.items||[]).length) h+='<div class="muted">Bài này chưa có mã TikZ. Vẽ trong đề bằng \\begin{tikzpicture}...\\end{tikzpicture} rồi mở lại.</div>';
    box.innerHTML=h;
  }catch(err){box.innerHTML='<div class="err">'+esc(err)+'</div>';}
}
async function rwUseTikz(box, hid, store){
  const code=(box._tikz&&box._tikz[hid])||'';
  if(!code){alert('Không thấy mã TikZ.');return;}
  if(store){
    try{
      const r=await fetch('/api/admin/lesson-tikz',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({src:box.getAttribute('data-src')||'',action:'store',code:code})});
      const d=await r.json();
      if(!d.ok){alert(d.error||'Không cất được');return;}
      rwLoadTikz(box);
    }catch(err){alert(String(err&&err.message||err));}
    return;
  }
  const bar=box.closest('.rwbar');
  const out=bar&&bar.querySelector('.rwout');
  const ta=out&&out.querySelector('[data-ta=stem]');
  if(ta){
    if(ta.value.indexOf(code)>=0){alert('Ô đề đã có mã này.');return;}
    rwPut(ta, code+'\n');
    return;
  }
  if(!confirm('Chèn mã TikZ này vào câu và ghi TEX?')) return;
  try{
    const r=await fetch('/api/admin/lesson-tikz',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({src:box.getAttribute('data-src')||'',file_idx:+(box.getAttribute('data-fi')||0),action:'insert',code:code})});
    const d=await r.json();
    if(!d.ok){alert(d.error||'Không chèn được');return;}
    rwShowSaved(out||box, '✅ Đã chèn mã TikZ vào câu.');
  }catch(err){alert(String(err&&err.message||err));}
}
document.addEventListener('click',function(e){
  const save=e.target.closest&&e.target.closest('.rwtikzsave');
  if(save){
    e.preventDefault();
    e.stopPropagation();
    const box=save.closest('.rwtikzbox');
    if(box) rwUseTikz(box, save.getAttribute('data-hid')||'', true);
    return;
  }
  const openBtn=e.target.closest&&e.target.closest('.rwtikzbtn');
  if(openBtn){
    e.preventDefault();
    const bar=openBtn.closest('.rwbar');
    if(!bar) return;
    const old=bar.querySelector('.rwtikzbox');
    if(old){old.remove();return;}
    const p=dropOf(openBtn);
    if(!p) return;
    const box=document.createElement('div');
    box.className='rwtikzbox';
    box.setAttribute('data-src', p.src);
    box.setAttribute('data-fi', String(p.fi));
    const out=bar.querySelector('.rwout');
    if(out) out.insertAdjacentElement('afterend', box);
    else bar.appendChild(box);
    rwLoadTikz(box);
    return;
  }
  const pick=e.target.closest&&e.target.closest('.rwtikzpick');
  if(!pick) return;
  e.preventDefault();
  const box=pick.closest('.rwtikzbox');
  if(box) rwUseTikz(box, pick.getAttribute('data-hid')||'', false);
});
document.addEventListener('click',async function(e){
  const go=e.target.closest&&e.target.closest('#aiMuc');
  const save=e.target.closest&&e.target.closest('#aiMucSave');
  if(!go&&!save) return;
  e.preventDefault();
  const bar=document.querySelector('.admindang');
  const nav=document.querySelector('.lvltabs');
  let box=document.getElementById('aiMucOut');
  if(!box){
    box=document.createElement('div');
    box.id='aiMucOut';
    box.style.cssText='margin:8px 10px;padding:10px;border:1px solid #86efac;border-radius:8px;background:#f0fdf4';
    if(nav&&nav.parentNode) nav.parentNode.insertBefore(box, nav.nextSibling);
    else if(bar) bar.appendChild(box);
  }
  if(!bar||!box) return;
  const path=bar.getAttribute('data-path')||'';
  const dang=bar.getAttribute('data-dang')||'';
  if(save){
    const rows=[...document.querySelectorAll('#aiMucTable tr[data-src]')].map(function(tr){
      const sel=tr.querySelector('select.aimuc');
      return {src:tr.getAttribute('data-src')||'', file_idx:+tr.getAttribute('data-fi'), muc:sel?sel.value:'TH'};
    });
    if(!rows.length){alert('Chưa có gợi ý mức.');return;}
    if(!confirm('Ghi mức độ '+rows.length+' câu vào TEX? Không đổi dạng, không đổi đề. Danh sách sẽ xếp NB → TH → VD → VDC.'))return;
    save.disabled=true;
    try{
      const r=await fetch('/api/admin/ai-levels-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({path:path,assignments:rows})});
      const d=await r.json();
      if(!d.ok){box.insertAdjacentHTML('afterbegin','<div class="err">'+esc(d.error||'Không ghi được')+'</div>');save.disabled=false;return;}
      box.innerHTML='<div class="success">✅ Đã ghi mức '+ (d.changed||rows.length) +' câu. Đang tải lại...</div>';
      location.reload();
    }catch(err){box.insertAdjacentHTML('afterbegin','<div class="err">'+esc(err)+'</div>');save.disabled=false;}
    return;
  }
  const ks=keys();
  if(!ks.length){alert('Nạp key Gemini (nút 🤖 Gemini trên thanh menu) rồi bấm lại.');return;}
  go.disabled=true;
  box.innerHTML='⏳ Đang gợi ý mức độ từng câu...';
  try{
    const r=await fetch('/api/admin/ai-levels',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:path,dang:dang,api_keys:ks,background:true})});
    let d={};
    try{d=await r.json();}catch(err){throw new Error('Máy chủ không trả kết quả (HTTP '+r.status+').');}
    if(d.pending&&d.job){
      const t0=Date.now();
      const job=d.job;
      d=null;
      while(Date.now()-t0<240000){
        await new Promise(function(res){setTimeout(res,2500);});
        try{
          const pr=await fetch('/api/admin/ai-levels-job?job='+encodeURIComponent(job),{credentials:'same-origin'});
          const pd=await pr.json();
          if(pd&&pd.pending){
            box.innerHTML='⏳ Đang gợi ý mức... '+(pd.done||0)+'/'+(pd.total||'?')+' câu. Cứ để trang mở.';
            continue;
          }
          d=pd;
          break;
        }catch(err){}
      }
      if(!d) throw new Error('Quá 4 phút chưa có gợi ý mức. Bấm lại.');
    }
    if(!d.ok){box.innerHTML='<div class="err">'+esc(d.error||'Lỗi')+'</div>';return;}
    const rows=d.assignments||[];
    const opts=['NB','TH','VD','VDC'];
    const body=rows.map(function(a){
      const sel=opts.map(function(m){return '<option'+(m===a.muc?' selected':'')+'>'+m+'</option>';}).join('');
      const cau=(a.develop?'PT ':'')+(a.cau||'');
      return '<tr data-src="'+esc(a.src)+'" data-fi="'+a.file_idx+'"><td>'+esc(cau)+'</td><td>'+esc(a.id||'—')+'</td><td>'+esc(a.old||'—')+'</td><td><select class="aimuc">'+sel+'</select></td><td>'+esc(a.why||'')+'</td></tr>';
    }).join('');
    const scope=dang?('dạng «'+esc(dang)+'»'):'cả bài';
    box.innerHTML='<div class="success">Gợi ý mức cho <b>'+rows.length+'</b> câu ('+scope+'). Sửa ô nếu cần rồi ghi. Không đổi dạng. Sau khi ghi, danh sách xếp NB → TH → VD → VDC.</div>'
      +'<div class="selectwrap"><table class="selectgrid" id="aiMucTable"><tr><th>Câu</th><th>ID</th><th>Đang có</th><th>Gợi ý</th><th>Vì sao</th></tr>'+body+'</table></div>'
      +'<p><button type="button" class="btn green" id="aiMucSave">💾 Ghi mức vào TEX</button></p>';
    if(box.scrollIntoView) box.scrollIntoView({block:'nearest'});
  }catch(err){
    box.innerHTML='<div class="err">'+esc(err)+'</div>';
  }finally{go.disabled=false;}
});
document.addEventListener('click',async function(e){
  const go=e.target.closest&&e.target.closest('#aiGom');
  const save=e.target.closest&&e.target.closest('#aiGomSave');
  if(!go&&!save) return;
  e.preventDefault();
  const form=document.getElementById('examMatrix');
  const pathInp=form&&form.querySelector('input[name=path]');
  const path=pathInp?pathInp.value:'';
  const box=document.getElementById('aiGomOut');
  if(!box||!path) return;
  if(save){
    const picked=[...box.querySelectorAll('input.aigom:checked')].map(function(x){
      const tr=x.closest('tr');
      return {from:tr.getAttribute('data-from')||'', to:tr.getAttribute('data-to')||''};
    }).filter(function(m){return m.from&&m.to&&m.from!==m.to;});
    if(!picked.length){alert('Chưa tick dạng nào để gom.');return;}
    if(!confirm('Gom '+picked.length+' tên dạng vào TEX? Câu giữ nguyên, chỉ đổi tên dạng.'))return;
    save.disabled=true;
    box.insertAdjacentHTML('afterbegin','<div class="muted">⏳ Đang ghi gom dạng...</div>');
    try{
      const r=await fetch('/api/admin/merge-dang-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({path:path,merges:picked})});
      let d={};
      try{d=await r.json();}catch(err){throw new Error('Máy chủ không trả kết quả (HTTP '+r.status+').');}
      if(!d.ok){box.insertAdjacentHTML('afterbegin','<div class="err">'+esc(d.error||'Không gom được')+'</div>');save.disabled=false;return;}
      box.innerHTML='<div class="success">✅ Đã gom '+(d.changed||picked.length)+' câu. Đang tải lại...</div>';
      location.reload();
    }catch(err){box.insertAdjacentHTML('afterbegin','<div class="err">'+esc(err)+'</div>');save.disabled=false;}
    return;
  }
  const ks=keys();
  if(!ks.length){alert('Nạp key Gemini (nút 🤖 Gemini trên thanh menu) rồi bấm lại.');return;}
  go.disabled=true;
  box.innerHTML='⏳ Đang gợi ý gom các dạng ít câu, cùng kỹ năng...';
  try{
    const r=await fetch('/api/admin/merge-dang',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:path,api_keys:ks})});
    let d={};
    try{d=await r.json();}catch(err){throw new Error('Máy chủ không trả kết quả (HTTP '+r.status+').');}
    if(!d.ok){box.innerHTML='<div class="err">'+esc(d.error||'Lỗi gom dạng')+'</div>';return;}
    const rows=d.merges||[];
    if(!rows.length){box.innerHTML='<div class="muted">'+esc(d.message||'Không thấy dạng cùng kỹ năng để gom.')+'</div>';return;}
    const body=rows.map(function(m){
      return '<tr data-from="'+esc(m.from)+'" data-to="'+esc(m.to)+'"><td><input class="aigom" type="checkbox" checked></td><td>'+esc(m.from)+'<div class="muted">'+esc(m.n||0)+' câu</div></td><td><b>'+esc(m.to)+'</b><div class="muted">sau gom khoảng '+esc(m.after||m.n||0)+' câu</div></td><td>'+esc(m.why||'')+'</td></tr>';
    }).join('');
    box.innerHTML='<div class="success">Đang <b>'+esc(d.n_before||'')+'</b> dạng → còn khoảng <b>'+esc(d.n_after||'')+'</b> dạng. Bỏ tick dòng muốn giữ riêng. Chưa ghi cho đến khi Đồng ý.</div>'
      +'<div class="selectwrap"><table class="selectgrid"><tr><th></th><th>Dạng đang rải</th><th>Gom thành</th><th>Vì sao</th></tr>'+body+'</table></div>'
      +'<p><button type="button" class="btn green" id="aiGomSave">✅ Đồng ý gom các dòng đã tick</button></p>';
    if(box.scrollIntoView) box.scrollIntoView({block:'nearest'});
  }catch(err){
    box.innerHTML='<div class="err">'+esc(err)+'</div>';
  }finally{go.disabled=false;}
});
document.addEventListener('click',async function(e){
  const btn=e.target.closest&&e.target.closest('#aiGap');
  if(!btn) return;
  e.preventDefault();
  const bar=btn.closest('.admindang');
  const out=document.getElementById('aiGapOut');
  if(out) out.innerHTML='⏳ Đang soát từng dạng (thiếu/thừa + câu gần trùng)...';
  const ks=keys();
  try{
    const r=await fetch('/api/admin/dang-gaps',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:bar&&bar.getAttribute('data-path')||'',dang:bar&&bar.getAttribute('data-dang')||'',api_keys:ks})});
    const d=await r.json();
    if(!d.ok){if(out) out.innerHTML='<div class="err">'+(d.error||'Lỗi')+'</div>';return;}
    if(out) out.innerHTML='<div class="success">'+esc(d.summary||'')+'</div>'+(d.note?'<div class="muted">'+esc(d.note)+'</div>':'')+(d.review_html||'');
    if(bar&&d.add) bar.setAttribute('data-add', JSON.stringify(d.add));
  }catch(err){if(out) out.innerHTML='<div class="err">'+esc(err)+'</div>';}
});
document.addEventListener('click',async function(e){
  const btn=e.target.closest&&e.target.closest('#aiNb');
  if(!btn) return;
  e.preventDefault();
  const bar=btn.closest('.admindang')||document.querySelector('.admindang');
  const out=document.getElementById('aiGapOut');
  if(!bar||!out) return;
  out.innerHTML='⏳ Đang soạn prompt NotebookLM theo bài/lớp/dạng đang thiếu...';
  try{
    const r=await fetch('/api/admin/notebooklm-prompt',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:bar.getAttribute('data-path')||'',dang:bar.getAttribute('data-dang')||''})});
    const d=await r.json();
    if(!d.ok){out.innerHTML='<div class="err">'+(d.error||'Lỗi')+'</div>';return;}
    const p=d.prompt||'';
    out.innerHTML='<div class="success">Prompt NotebookLM: tải SGK/SBT KNTT đúng môn-lớp-bài vào NotebookLM, dán prompt, lấy LaTeX rồi dán vào ô hoặc bấm Lấy từ link.</div>'
      +'<textarea id="aiNbTex" class="rwta" style="min-height:280px">'+esc(p)+'</textarea>'
      +'<p><button type="button" class="btn green" id="aiNbCopy">📋 Sao chép prompt</button></p>';
    const ta=document.getElementById('aiNbTex');
    if(ta){ta.focus();ta.select();}
    if(navigator.clipboard&&p){
      try{await navigator.clipboard.writeText(p);}catch(err){}
    }
  }catch(err){out.innerHTML='<div class="err">'+esc(err)+'</div>';}
});
document.addEventListener('click',function(e){
  const btn=e.target.closest&&e.target.closest('#aiNbCopy');
  if(!btn) return;
  e.preventDefault();
  const ta=document.getElementById('aiNbTex');
  const p=ta?ta.value:'';
  if(!p) return;
  if(navigator.clipboard) navigator.clipboard.writeText(p).then(function(){btn.textContent='✅ Đã sao chép';}).catch(function(){ta.select();document.execCommand('copy');});
  else {ta.select();document.execCommand('copy');}
});
document.addEventListener('click',async function(e){
  const fill=e.target.closest&&e.target.closest('#aiFill');
  const save=e.target.closest&&e.target.closest('#aiFillSave');
  const imp=e.target.closest&&e.target.closest('#aiImport');
  if(!fill&&!save&&!imp) return;
  e.preventDefault();
  const bar=document.querySelector('.admindang');
  const out=document.getElementById('aiGapOut');
  if(!bar||!out) return;
  const path=bar.getAttribute('data-path')||'';
  const dang=bar.getAttribute('data-dang')||'';
  if(save){
    const ta=document.getElementById('aiFillTex');
    if(!ta||!(ta.value||'').trim()){alert('Chưa có LaTeX để ghi.');return;}
    if(!confirm('Ghi các câu mới vào file TEX + GitHub?'))return;
    save.disabled=true;
    try{
      const r=await fetch('/api/admin/dang-fill-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
        body:JSON.stringify({path:path,dang:dang,latex:ta.value,source_url:(document.getElementById('aiSrcUrl')||{}).value||''})});
      const d=await r.json();
      if(!d.ok){out.insertAdjacentHTML('afterbegin','<div class="err">'+(d.error||'Không ghi được')+'</div>');save.disabled=false;return;}
      out.innerHTML='<div class="success">✅ Đã ghi. Đang tải lại...</div>';
      location.reload();
    }catch(err){out.insertAdjacentHTML('afterbegin','<div class="err">'+esc(err)+'</div>');save.disabled=false;}
    return;
  }
  const ks=keys();
  if(!ks.length){alert('Nạp key Gemini (nút 🤖 Gemini trên thanh menu) rồi bấm lại.');return;}
  const pasteEl=document.getElementById('aiPaste');
  const urlEl=document.getElementById('aiSrcUrl');
  let sourceUrl=urlEl?String(urlEl.value||'').trim():'';
  let sourceTex=pasteEl?String(pasteEl.value||''):'';
  try{
    const fileTex=await readAiSrcFile();
    if(fileTex && sourceTex.indexOf(fileTex.slice(0,120))<0) sourceTex=(sourceTex.trim()?sourceTex.replace(/\s+$/,'')+'\n\n':'')+fileTex;
  }catch(err){out.innerHTML='<div class="err">'+esc(err)+'</div>';return;}
  const imageFiles=aiShots.map(function(s){return s.file||'';}).filter(Boolean);
  const sourceDocxs=aiDocs.map(function(x){return {name:x.name, b64:x.b64};});
  const sourcePdfs=aiPdfs.map(function(x){return {name:x.name, b64:x.b64};});
  const sourceImages=sourceDocxs.length?[]:aiShots.filter(function(s){return !s.file;}).slice(0,4).map(function(s){return {mime:s.mime||'image/jpeg', data:s.data};});
  const hasBag=!!(sourceTex.trim()||sourceImages.length||sourceDocxs.length||sourcePdfs.length);
  const sourceCount=sourceDocxs.length+sourcePdfs.length+aiTexNames.length+(sourceUrl?1:0);
  if(sourceUrl && !/^https?:\/\//i.test(sourceUrl)){
    if(hasBag){sourceUrl='';}
    else{
      alert('Không dán đường dẫn ổ đĩa (G:\\...). Hãy dán ảnh, Word .docx, PDF, TEX, hoặc link http/https.');
      return;
    }
  }
  if(imp && !sourceUrl && !hasBag){alert('Dán ảnh, Word .docx, PDF, TEX hoặc chữ vào khung Nhận đề. Link http là tuỳ chọn.');return;}
  if(fill && !dang && !sourceUrl && !hasBag){alert('Đang ở Cả bài: dán nguồn vào khung Nhận đề, hoặc mở một dạng rồi bấm AI viết các câu còn thiếu.');return;}
  const nBag=sourceDocxs.length+sourcePdfs.length+aiTexNames.length;
  const waitLabel=(nBag>1)?('Đang đọc '+nBag+' file, AI chuyển sang TEX rồi lọc trùng'):((sourcePdfs.length)?'Đang đọc PDF, AI chuyển sang TEX':((sourceDocxs.length||sourceImages.length)?'Đang đọc Word/ảnh, AI chuyển sang TEX':(sourceTex.trim()?'Đang đọc chữ/TEX, AI chuyển sang TEX':(sourceUrl?'Đang tải trang, AI chuyển sang TEX':'AI đang viết các câu còn thiếu'))));
  const btnRun=document.getElementById('aiImport');
  if(btnRun) btnRun.disabled=true;
  const t0=Date.now();
  const srcChars=(sourceTex||'').trim().length;
  const srcImgs=sourceImages.length;
  const srcBytes=Math.round(bagChars()*0.75);
  const expectSec=Math.min(200, 80+nBag*30);
  function srcLabel(){
    const bits=[];
    if(srcChars) bits.push(srcChars.toLocaleString('vi-VN')+' chữ');
    if(srcBytes) bits.push((srcBytes/1024).toFixed(srcBytes>=102400?0:1).replace('.',',')+' KB');
    if(srcImgs) bits.push(srcImgs+' ảnh');
    return bits.join(' · ')||'đang gửi';
  }
  function rateLabel(sec){
    const s=Math.max(1,sec);
    if(srcChars) return Math.round(srcChars/s).toLocaleString('vi-VN')+' chữ/s';
    if(srcBytes) return (srcBytes/s/1024).toFixed(1).replace('.',',')+' KB/s';
    return (Math.round((Math.min(92,s/expectSec*100)/s)*10)/10).toString().replace('.',',')+' %/s';
  }
  if(window._aiWaitTimer) clearInterval(window._aiWaitTimer);
  function paintWait(){
    const s=Math.max(0,Math.round((Date.now()-t0)/1000));
    const pct=Math.min(92,Math.round(s/expectSec*100));
    const remain=Math.max(0,expectSec-s);
    aiMeter({
      kind:'wait',
      caption:waitLabel+'. Đã chờ '+s+'s.',
      time:(s||0)+'s',
      src:srcLabel(),
      rate:s?rateLabel(s):'…',
      pct:pct,
      hint:remain?('ước lượng còn khoảng '+remain+'s'):'vẫn đang chạy — cứ để trang mở'
    });
  }
  paintWait();
  window._aiWaitTimer=setInterval(paintWait,1000);
  function stopWait(){
    if(window._aiWaitTimer){clearInterval(window._aiWaitTimer);window._aiWaitTimer=null;}
    if(btnRun) btnRun.disabled=false;
  }
  let add=null;
  try{add=JSON.parse(bar.getAttribute('data-add')||'null')}catch(err){add=null}
  try{
    const r=await fetch('/api/admin/dang-fill',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:path,dang:dang,add:add,api_keys:ks,source_url:sourceUrl,source_tex:sourceTex,source_images:sourceImages,image_files:imageFiles,source_docxs:sourceDocxs,source_pdfs:sourcePdfs,source_count:sourceCount,background:true})});
    const raw=await r.text();
    let d={};
    try{d=JSON.parse(raw);}catch(err){throw new Error('Máy chủ không trả kết quả (HTTP '+r.status+').');}
    if(d.pending&&d.job){
      const job=d.job;
      d=null;
      let missed=0;
      while(Date.now()-t0<300000){
        await new Promise(function(res){setTimeout(res,2500);});
        let pr,praw,pd;
        try{
          pr=await fetch('/api/admin/dang-fill-job?job='+encodeURIComponent(job),{credentials:'same-origin'});
          praw=await pr.text();
          pd=JSON.parse(praw);
        }catch(err){continue;}
        const waited=Math.max(0,Math.round((Date.now()-t0)/1000));
        if(pd&&pd.pending){
          missed=0;
          const el=Math.max(waited, Number(pd.elapsed)||0);
          const left=Math.max(0,expectSec-el);
          aiMeter({
            kind:'wait',
            caption:waitLabel+'. Đã chờ '+el+'s.',
            time:el+'s',
            src:srcLabel(),
            rate:rateLabel(el),
            pct:Math.min(92,Math.round(el/expectSec*100)),
            hint:left?('ước lượng còn khoảng '+left+'s'):'vẫn đang chạy — cứ để trang mở'
          });
          continue;
        }
        if(pd&&pd.ok===false&&/phiên đang chạy/i.test(String(pd.error||''))){
          missed++;
          aiMeter({
            kind:'wait',
            caption:'Đang nối lại phiên AI. Đã chờ '+waited+'s.',
            time:waited+'s',
            src:srcLabel(),
            rate:'…',
            pct:Math.min(92,Math.round(waited/expectSec*100)),
            hint:'cứ để trang mở'
          });
          if(missed<12) continue;
          throw new Error('Không thấy phiên sau '+waited+'s. Bấm AI phân tích lại.');
        }
        d=pd;
        break;
      }
      if(!d) throw new Error('Quá 5 phút chưa có kết quả. Bấm AI phân tích lại.');
    }
    if(!d.ok){stopWait();aiStatus(d.error||'Lỗi','err');out.innerHTML='<div class="err">'+esc(d.error||'Lỗi')+'</div>';return;}
    if(!String(d.latex||'').trim()){
      const sec0=Math.max(1,Math.round((Date.now()-t0)/1000));
      stopWait();
      aiMeter({kind:'ok', caption:d.summary||'Đã lọc, không còn câu mới.', time:sec0+'s', src:srcLabel(), rate:'0 câu', pct:100, hint:'không có câu để ghi'});
      out.innerHTML='<div class="success">'+esc(d.summary||'Đã lọc, không còn câu mới.')+'</div>';
      return;
    }
    const sec=Math.max(1,Math.round((Date.now()-t0)/1000));
    stopWait();
    const nQ=Number(d.n)||nTikz(d.latex)||((d.latex||'').split(/\\begin\s*\{\s*ex\s*\}/i).length-1);
    const perMin=Math.max(1,Math.round(nQ/sec*60));
    aiMeter({
      kind:'ok',
      caption:nTikz(d.latex)?('Xong sau '+sec+'s. Có hình TikZ — xem trước rồi mới bấm duyệt.'):('Xong sau '+sec+'s. LaTeX nằm ngay dưới — xem rồi bấm Chấp nhận ghi TEX.'),
      time:sec+'s',
      src:srcLabel(),
      rate:nQ?((nQ+' câu · '+perMin+' câu/phút')):rateLabel(sec),
      pct:100,
      hint:(d.latex||'').length.toLocaleString('vi-VN')+' ký tự TEX'
    });
    out.innerHTML='<div class="success">'+esc(d.summary||'Đã soạn. Xem LaTeX rồi bấm Chấp nhận.')+'</div>'
      +(d.note?'<div>'+esc(d.note)+'</div>':'')
      +'<div id="aiTikzPrev" class="ai-tikz"></div>'
      +'<textarea id="aiFillTex" class="rwta" style="min-height:220px">'+esc(d.latex||'')+'</textarea>'
      +'<p><button type="button" class="btn" id="aiTikzReload">Xem trước TikZ</button> <button type="button" class="btn green" id="aiFillSave">3. ✅ Chấp nhận ghi TEX</button></p>';
    showTikzPreview(d.latex||'');
    if(out.scrollIntoView) out.scrollIntoView({block:'nearest'});
  }catch(err){
    stopWait();
    const msg=(err&&err.name==='AbortError')?'Quá 3,5 phút chưa có kết quả. Bấm AI phân tích lại.':String(err);
    aiStatus(msg,'err');
    out.innerHTML='<div class="err">'+esc(msg)+'</div>';
  }
});
function nTikz(tex){
  var re=/\\begin\s*\{\s*tikzpicture\s*\}/gi;
  var n=0, m;
  while((m=re.exec(tex||''))) n++;
  return n;
}
function tikzOnly(tex){
  var re=/\\begin\s*\{\s*tikzpicture[\s\S]*?\\end\s*\{\s*tikzpicture\s*\}/gi;
  var m, bits=[];
  while((m=re.exec(tex||''))) bits.push(m[0]);
  return bits;
}
async function showTikzPreview(tex){
  var box=document.getElementById('aiTikzPrev');
  if(!box) return;
  var bits=tikzOnly(tex);
  if(!bits.length){
    box.innerHTML='<div class="ai-tikz-k">Chưa có hình TikZ</div><div>Nếu ảnh gốc có đồ thị hoặc trục số, sửa LaTeX rồi bấm Xem trước TikZ.</div>';
    return;
  }
  box.innerHTML='<div class="ai-tikz-k">Đang vẽ '+bits.length+' hình…</div>';
  try{
    var r=await fetch('/api/admin/tex-preview',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({tex:bits.join('\n\n')})});
    var d=await r.json();
    if(!d.ok&&d.error){box.innerHTML='<div class="err">'+esc(d.error)+'</div>';return;}
    box.innerHTML='<div class="ai-tikz-k">Xem trước hình TikZ — đối chiếu với ảnh gốc rồi mới duyệt</div>'+(d.html||'');
    if(window.ldvlArmTikz) ldvlArmTikz(box);
    if(window.ldvlTypeset) ldvlTypeset(box);
  }catch(err){
    box.innerHTML='<div class="err">'+esc(err)+'</div>';
  }
}
document.addEventListener('click',function(e){
  var b=e.target&&e.target.closest&&e.target.closest('#aiTikzReload');
  if(!b) return;
  e.preventDefault();
  var ta=document.getElementById('aiFillTex');
  showTikzPreview(ta?ta.value:'');
});
function aiStatus(msg, kind){
  const el=document.getElementById('aiStatus');
  if(!el) return;
  el.hidden=!msg;
  el.className='ai-status'+(kind?(' is-'+kind):'');
  el.textContent=msg||'';
}
function aiMeter(o){
  const el=document.getElementById('aiStatus');
  if(!el) return;
  o=o||{};
  el.hidden=false;
  el.className='ai-status is-'+(o.kind||'wait');
  const pct=Math.max(0,Math.min(100,Number(o.pct)||0));
  el.innerHTML='<div class="ai-cap">'+esc(o.caption||'')+'</div>'
    +'<div class="ai-meter">'
    +'<div class="ai-col"><b>Thời gian</b><strong>'+esc(o.time||'0s')+'</strong></div>'
    +'<div class="ai-col"><b>Dữ liệu</b><strong>'+esc(o.src||'')+'</strong></div>'
    +'<div class="ai-col"><b>Tốc độ</b><strong>'+esc(o.rate||'…')+'</strong></div>'
    +'<div class="ai-col"><b>Hoàn thành</b><strong>'+pct+'%</strong><em>'+esc(o.hint||'')+'</em>'
    +'<div class="ai-bar"><i style="width:'+pct+'%"></i></div></div>'
    +'</div>';
}
})();
</script>
"""
