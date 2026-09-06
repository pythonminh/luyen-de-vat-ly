# -*- coding: utf-8 -*-
"""ADMIN: AI viết lại đề + lời giải; chỉ ghi TEX khi ADMIN chấp nhận."""
from __future__ import annotations

import json
import re

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
            "LẦN 2 — bản trước SAI CẤU TRÚC (thiếu đề, lời giải chỉ là một số, lẫn TN/ĐS, thiếu 4 mệnh đề). "
            "BẮT BUỘC đề đầy đủ VÀ lời giải đủ bước (công thức, đổi đơn vị, tính ra đáp án). CẤM solution chỉ ghi 20.\n"
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
        +         "Bạn là giáo viên THPT soạn đề. VIẾT LẠI (hoặc BỔ SUNG nếu đề cũ thiếu) ĐỀ và LỜI GIẢI cho ĐẦY ĐỦ, đúng, gọn, giọng giáo viên.\n"
        "Không được để stem trống. Không copy nguyên văn nếu đề cũ đã đủ. Giữ ý toán khi đề cũ đủ; nếu đề cũ thiếu thì dựng đề khớp lời giải/đáp án. Tính lại cho khớp.\n"
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
        "- Mọi công thức (kể cả \\pi, \\frac, \\Rightarrow, \\cos, \\left\\right) phải nằm trong $...$.\n"
        "- Không gõ \\ trước chữ tiếng Việt (sai: \\Để  .\\Để  :\\-3). Viết: Để  : -3.\n"
        "- Trong JSON, mỗi backslash LaTeX phải viết HAI lần: \\\\frac \\\\pi \\\\Rightarrow \\\\left \\\\right.\n"
        "- Xuống dòng bằng \\n trong JSON, không dùng \\\\ rồi xuống dòng lung tung.\n"
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


def _raw_parts(q):
    raw = q.get("raw") or ""
    head, _tail = _split_head_tail(raw)
    _comments, stem = _split_comments(head)
    sol = base.solution_of(raw) or (q.get("solution") or "")
    return _clean_tex(stem), _clean_tex(sol)


def _pack_payload(src, fi, kind, stem, solution, answer, options, note=""):
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
    opt_html = ""
    if options and kind == "TN":
        bits = []
        for i, o in enumerate(options[:4]):
            mark = " <span class='okmark'>Đáp án đúng</span>" if o.get("correct") else ""
            bits.append(
                f"<div class='opt{' ok' if o.get('correct') else ''}'><b>{'ABCD'[i]}.</b> {base.html_question(o.get('text',''))}{mark}</div>"
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
                f"<div class='tf{cls}'><span class='tflab'>{lab}</span><div class='tf-text'>{base.html_question(o.get('text',''))}</div><span class='tf-box yes{y_on}'></span><span class='tf-box no{n_on}'></span></div>"
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
        "stem_html": base.html_question(stem),
        "sol_html": base.html_question(solution),
        "opt_html": opt_html,
        "answer_html": base.html_question(answer or ""),
    }


@base.app.post("/api/admin/tex-preview")
def api_tex_preview():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN."), 403
    data = request.get_json(silent=True) or {}
    tex = _clean_tex(data.get("tex") or data.get("latex") or "")
    return jsonify(ok=True, html=base.html_question(tex))


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
    raw_stem, raw_sol = _raw_parts(q)
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
                "Sửa trực tiếp — chưa ghi file.",
            )
        )
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error="Thiếu Gemini API key."), 400
    from admin_classify import _gemini_once

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
                elif i < len(old_opts):
                    correct = bool(old_opts[i].get("correct"))
                else:
                    correct = False
                new_opts.append({"text": _clean_tex(txt), "correct": correct})
        note = str(obj.get("note") or "").strip()[:300]
        if pack["kind"] == "TLN":
            answer, solution = _coerce_tln(answer, solution)
        return stem, solution, answer, new_opts, note

    raw, err = _gemini_once(keys, _prompt(pack), 5000)
    if not raw:
        return jsonify(ok=False, error=err or "Gemini không trả lời."), 400
    stem, solution, answer, new_opts, note = fields_from(raw)
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
    sol_in = data.get("solution") or ""
    ans_in = data.get("answer") or ""
    if kind == "TLN":
        ans_in, sol_in = _coerce_tln(ans_in, sol_in)
    new_inner = _apply_inner(
        inner,
        kind,
        _clean_tex(data.get("stem") or ""),
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


REWRITE_CLIENT_JS = r"""
<style>.rwbar{margin:10px 0 0;padding:8px 10px;border:1px dashed #7dd3fc;border-radius:9px;background:#f0f9ff;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.rwout{width:100%}.rwprev{margin-top:8px;padding:10px;border:1px solid #bae6fd;border-radius:9px;background:#fff}.rwprev label{display:flex;gap:8px;align-items:center;font-weight:800;margin:8px 0 4px}.rwta{width:100%;min-height:120px;font:13px/1.45 Consolas,ui-monospace,monospace;padding:8px;border:1px solid #7dd3fc;border-radius:8px;margin:4px 0 8px}.rwta.sm{min-height:72px}.rwlook{margin:8px 0;padding:10px;border:1px dashed #bae6fd;border-radius:8px;background:#f8fbff}</style>
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
async function previewBox(box){
  const tas=box.querySelectorAll('.rwta');
  const look=box.querySelector('.rwlook');
  if(!look) return;
  look.innerHTML='⏳ Đang xem trước...';
  const parts=[];
  for(const ta of tas){
    const lab=ta.getAttribute('data-lab')||'';
    const r=await fetch('/api/admin/tex-preview',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({tex:ta.value||''})});
    const d=await r.json();
    parts.push('<div class="muted">'+esc(lab)+'</div><div>'+(d.html||'')+'</div>');
  }
  look.innerHTML=parts.join('');
  if(window.ldvlTypeset)ldvlTypeset(look);
}
function showEditor(box, d){
  d.stem=stripMeta(d.stem||'');
  d.solution=stripMeta(d.solution||'');
  d.answer=stripMeta(d.answer||'');
  (d.options||[]).forEach(function(o){o.text=stripMeta(o.text||'')});
  let h='<div class="rwprev"><div class="success">Chưa ghi file. Sửa LaTeX trong ô, bấm Xem trước, rồi Chấp nhận.</div>';
  if(d.note) h+='<p class="muted">'+esc(d.note)+'</p>';
  h+='<label><input type="checkbox" class="rwf" data-k="stem" checked> Thay đề</label>';
  h+='<textarea class="rwta" data-ta="stem" data-lab="Đề">'+esc(d.stem||'')+'</textarea>';
  (d.options||[]).forEach(function(o,i){
    if(!i) h+='<label><input type="checkbox" class="rwf" data-k="opts" checked> Thay cách diễn đạt phương án (không đổi đáp án đúng)</label>';
    h+='<textarea class="rwta sm" data-ta="opt-'+i+'" data-lab="PA '+(d.kind==='TN'?'ABCD'[i]:(i+1))+'">'+esc(o.text||'')+'</textarea>';
  });
  if(d.kind==='TLN'){
    h+='<label><input type="checkbox" class="rwf" data-k="answer" checked> Thay đáp án TLN</label>';
    h+='<textarea class="rwta sm" data-ta="ans" data-lab="Đáp án">'+esc(d.answer||'')+'</textarea>';
  }
  h+='<label><input type="checkbox" class="rwf" data-k="sol" checked> Thay lời giải</label>';
  h+='<textarea class="rwta" data-ta="sol" data-lab="Lời giải" style="min-height:180px">'+esc(d.solution||'')+'</textarea>';
  h+='<p><button type="button" class="btn rwPrev">👁 Xem trước</button> <button type="button" class="btn green rwSave">✅ Chấp nhận và ghi TEX</button> <button type="button" class="btn rwCancel">Hủy</button></p>';
  h+='<div class="rwlook"></div></div>';
  box.innerHTML=h;
  box.querySelector('.rwCancel').onclick=function(){box.innerHTML='';};
  box.querySelector('.rwPrev').onclick=function(){previewBox(box)};
  box.querySelector('.rwSave').onclick=async function(){
    if(!confirm('Ghi đề/lời giải vào TEX + GitHub?'))return;
    const x=readDraft(box,d);
    const s=await fetch('/api/admin/rewrite-question-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({src:d.src,file_idx:d.file_idx,stem:x.stem,solution:x.solution,answer:x.answer,options:x.options,
        apply_stem:!!x.flags.stem,apply_opts:!!x.flags.opts,apply_sol:!!x.flags.sol,apply_answer:!!x.flags.answer})});
    const sd=await s.json();
    if(!sd.ok){alert(sd.error||'Không ghi được');return;}
    box.innerHTML='<div class="success">✅ Đã ghi. Đang tải lại...</div>';
    location.reload();
  };
  previewBox(box);
}
async function loadRewrite(src, fi, box, mode){
  box.innerHTML=mode==='edit'?'⏳ Đang tải lời giải hiện tại...':'⏳ AI đang viết lại đề và lời giải...';
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
window.ldvlAdminRewrite=function(src,fi,box){loadRewrite(src,fi,box,'ai')};
window.ldvlAdminEdit=function(src,fi,box){loadRewrite(src,fi,box,'edit')};
document.addEventListener('click',function(e){
  const go=e.target.closest&&e.target.closest('.rwgo');
  const ed=e.target.closest&&e.target.closest('.rwedit');
  const btn=go||ed;
  if(!btn) return;
  e.preventDefault();
  const p=dropOf(btn);
  if(!p) return;
  loadRewrite(p.src,p.fi,outBox(btn),ed?'edit':'ai');
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
  const urlEl=document.getElementById('aiSrcUrl');
  const sourceUrl=urlEl?String(urlEl.value||'').trim():'';
  if(imp && !sourceUrl){alert('Dán link http/https vào ô rồi bấm Lấy từ link. Không cần chọn dạng — để Cả bài.');return;}
  if(fill && !dang && !sourceUrl){alert('Đang ở Cả bài: dán link rồi bấm Lấy từ link. Nút AI viết thiếu dùng khi đã mở một dạng.');return;}
  out.innerHTML=sourceUrl?'⏳ Đang tải trang rồi AI chuyển sang TEX...':'⏳ AI đang viết các câu còn thiếu (mỗi lần tối đa vài câu). Cứ để nguyên tab...';
  let add=null;
  try{add=JSON.parse(bar.getAttribute('data-add')||'null')}catch(err){add=null}
  try{
    const r=await fetch('/api/admin/dang-fill',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:path,dang:dang,add:add,api_keys:ks,source_url:sourceUrl})});
    const d=await r.json();
    if(!d.ok){out.innerHTML='<div class="err">'+(d.error||'Lỗi')+'</div>';return;}
    out.innerHTML='<div class="success">'+esc(d.summary||'Đã soạn. Xem LaTeX rồi bấm Chấp nhận.')+'</div>'
      +(d.note?'<div class="muted">'+esc(d.note)+'</div>':'')
      +'<textarea id="aiFillTex" class="rwta" style="min-height:220px">'+esc(d.latex||'')+'</textarea>'
      +'<p><button type="button" class="btn green" id="aiFillSave">3. ✅ Chấp nhận ghi TEX</button></p>';
  }catch(err){out.innerHTML='<div class="err">'+esc(err)+'</div>';}
});
})();
</script>
"""
