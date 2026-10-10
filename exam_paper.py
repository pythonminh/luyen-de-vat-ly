# -*- coding: utf-8 -*-
"""ADMIN: tạo đề / in đề / trộn đề với số câu tùy chọn."""
from __future__ import annotations

import html
import base64
import secrets
from app import gh_api, BRANCH
import io
import json
import random
import secrets
import base64
import re
import urllib.parse
import zipfile
from datetime import datetime
from pathlib import Path

from flask import jsonify, redirect, request, send_file, session

from app import (
    KIND_ORDER,
    app,
    can_manage_bank,
    can_practice,
    html_question,
    index_data,
    login_url,
    member_current,
    page,
    nest_developments,
    parse_lesson_questions,
    parse_questions,
    read_tex,
    sort_ids_by_kind,
)

KIND_LABEL = {
    "TN": "PHẦN I. TRẮC NGHIỆM",
    "DS": "PHẦN II. ĐÚNG / SAI",
    "TLN": "PHẦN III. TRẢ LỜI NGẮN",
    "TL": "PHẦN IV. TỰ LUẬN",
}


def _esc(s):
    return html.escape(str(s or ""), quote=True)


def _copies(raw, default=1):
    try:
        n = int(raw or default)
    except (TypeError, ValueError):
        n = default
    return max(1, min(20, n))


def load_qs(path):
    qs = parse_lesson_questions(path)
    if not qs:
        _, tex = read_tex(path)
        qs = nest_developments(parse_questions(tex))
    return qs


def load_exam_qs(exam):
    """Câu của đề đang lưu. Đề cả chương lấy từng bài theo qmap, idx là vị trí trong đề."""
    exam = exam or {}
    _hydrate_variants(exam)
    snapshot = exam.get("snapshot_qs")
    if isinstance(snapshot, list) and snapshot:
        return snapshot
    if exam.get("saved_code"):
        saved, _ = _saved_load(exam["saved_code"])
        frozen_qs = saved.get("exam", {}).get("snapshot_qs")
        if isinstance(frozen_qs, list) and frozen_qs:
            return frozen_qs
    qmap = exam.get("qmap") or []
    if not qmap:
        return load_qs(str(exam.get("path") or ""))
    cache = {}
    out = []
    for i, item in enumerate(qmap):
        if not isinstance(item, dict):
            continue
        p = str(item.get("path") or "").replace("\\", "/")
        try:
            old = int(item.get("idx"))
        except (TypeError, ValueError):
            continue
        if p not in cache:
            try:
                cache[p] = {int(q.get("idx")): q for q in load_qs(p) if str(q.get("idx", "")).isdigit() or isinstance(q.get("idx"), int)}
            except Exception:
                cache[p] = {}
        srcq = cache[p].get(old)
        if not srcq:
            continue
        q = dict(srcq)
        q["idx"] = i
        out.append(q)
    return out


def lesson_title(path):
    p = str(path or "").replace("\\", "/")
    folder = p.rsplit("/", 1)[0] if "/" in p else p
    name = folder.rsplit("/", 1)[-1] if "/" in folder else folder
    for x in (index_data().get("lessons") or []):
        xp = str((x or {}).get("path") or (x or {}).get("file") or "").replace("\\", "/")
        if xp == p or xp.startswith(folder + "/"):
            t = str(x.get("BaiHoc") or x.get("De") or "").strip()
            if t:
                return t.split(" · ")[0].strip() or name
    return name or Path(p).stem


def ids_from_pick_form(qs, form):
    dang_names, seen = [], set()
    for q in qs or []:
        d = q.get("dang")
        if d not in seen:
            seen.add(d)
            dang_names.append(d)
    wanted = []
    for key, raw in (form or {}).items():
        if not str(key).startswith("pick:"):
            continue
        try:
            n = max(0, int(raw or 0))
        except (TypeError, ValueError):
            n = 0
        if n <= 0:
            continue
        try:
            _, di_s, kind, lev = str(key).split(":", 3)
            di = int(di_s)
        except Exception:
            continue
        if not (0 <= di < len(dang_names)):
            continue
        pool = [
            q
            for q in qs
            if q.get("dang") == dang_names[di] and q.get("kind") == kind and q.get("level") == lev
        ]
        wanted.extend(int(q["idx"]) for q in random.sample(pool, min(n, len(pool))))
    return wanted


def ids_from_qid_form(qs, form, dang=""):
    dang = str(dang or "").strip()
    if dang:
        valid = {
            int(q.get("idx"))
            for q in qs
            if str(q.get("idx", "")).isdigit() and str(q.get("dang") or "").strip() == dang
        }
        if not valid and dang == "Chưa phân dạng":
            valid = {
                int(q.get("idx"))
                for q in qs
                if str(q.get("idx", "")).isdigit() and not str(q.get("dang") or "").strip()
            }
    else:
        valid = {int(q.get("idx")) for q in qs if str(q.get("idx", "")).isdigit()}
    posted = []
    for raw in (form.getlist("qid") if hasattr(form, "getlist") else []):
        try:
            i = int(raw)
        except (TypeError, ValueError):
            continue
        if i not in posted:
            posted.append(i)
    if not posted:
        return []
    picked = [i for i in posted if i in valid]
    if picked:
        return picked
    any_ids = {int(q.get("idx")) for q in qs if str(q.get("idx", "")).isdigit()}
    return [i for i in posted if i in any_ids]


def new_code(used=None):
    used = set(used or [])
    for _ in range(80):
        code = f"{random.randint(101, 989):03d}"
        if code not in used:
            return code
    return f"{random.randint(101, 989):03d}"


def shuffle_copy(qs, ids, shuffle_opts=True):
    ids = sort_ids_by_kind(qs, list(ids), shuffle_within=True)
    by = {int(q.get("idx")): q for q in qs}
    tn_perm, ds_perm = {}, {}
    if shuffle_opts:
        for i in ids:
            q = by.get(int(i)) or {}
            kind = str(q.get("kind") or "")
            if kind == "TN":
                n = len(q.get("options") or [])
                if n >= 2:
                    order = list(range(n))
                    random.shuffle(order)
                    tn_perm[str(i)] = order
            elif kind == "DS":
                n = len(q.get("statements") or [])
                if n >= 2:
                    order = list(range(n))
                    random.shuffle(order)
                    ds_perm[str(i)] = order
    return {"ids": ids, "tn_perm": tn_perm, "ds_perm": ds_perm, "code": new_code()}


def apply_perm(q, copy):
    q = dict(q or {})
    idx = str(q.get("idx"))
    variant = (copy.get("overrides") or {}).get(idx)
    if isinstance(variant, dict):
        q.update({k: variant[k] for k in ("text", "solution", "answer", "options", "statements") if k in variant})
    kind = str(q.get("kind") or "")
    if kind == "TN":
        opts = list(q.get("options") or [])
        order = (copy.get("tn_perm") or {}).get(idx)
        if order and opts:
            q["options"] = [opts[i] for i in order if 0 <= i < len(opts)]
    elif kind == "DS":
        stmts = list(q.get("statements") or [])
        order = (copy.get("ds_perm") or {}).get(idx)
        if order and stmts:
            q["statements"] = [stmts[i] for i in order if 0 <= i < len(stmts)]
    return q


def _tn_letter(q):
    labs = "ABCD"
    for i, o in enumerate(q.get("options") or []):
        if o.get("correct"):
            return labs[i] if i < len(labs) else str(i + 1)
    return "—"


def _ds_mask(q):
    return "".join("Đ" if (s or {}).get("correct") else "S" for s in (q.get("statements") or [])) or "—"


def _copy_answer_rows(qs, copy):
    """Đáp án đúng của một mã đề, sau khi đã trộn phương án."""
    by = {int(q.get("idx")): q for q in qs}
    groups = {k: [] for k in KIND_ORDER}
    for i in list(copy.get("ids") or []):
        q = by.get(int(i))
        if not q:
            continue
        k = str(q.get("kind") or "TL")
        (groups[k] if k in groups else groups.setdefault("TL", [])).append(q)
    rows = []
    for kind in KIND_ORDER:
        seq = 0
        for q in groups.get(kind) or []:
            seq += 1
            qq = apply_perm(q, copy)
            if kind == "TN":
                ans = _tn_letter(qq)
            elif kind == "DS":
                ans = _ds_mask(qq)
            elif kind == "TLN":
                ans = str(qq.get("answer") or "").strip()
            else:
                ans = ""
            rows.append({"n": seq, "kind": kind, "answer": ans})
    return rows


def _opt_span(tex):
    """Độ dài nhìn thấy của một phương án. Hình hoặc công thức trưng bày thì xếp một cột."""
    s = str(tex or "")
    if re.search(r"\\begin\s*\{|\\includegraphics|\\\[|\\\\", s):
        return 999

    def inner(m):
        t = re.sub(r"\\[a-zA-Z]+\*?", "", m.group(0))
        return re.sub(r"[{}$\\]", "", t)

    s = re.sub(r"\$\$[\s\S]*?\$\$|\$[^$]*\$|\\\([\s\S]*?\\\)", inner, s)
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s)
    s = re.sub(r"[{}\\]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return len(s)


def _choice_class(options):
    """Bốn đáp án ngắn: 2 dòng × 2 cột. Đáp án dài: 4 dòng."""
    opts = list(options or [])
    if len(opts) != 4:
        return "stack"
    if max(_opt_span(o.get("text") or "") for o in opts) <= 14:
        return "grid4"
    return "grid2"


def _rules_html(kind):
    n = 6 if kind == "TL" else 4
    return f"<div class='exrules' style='height:{n * 1.15:.2f}em' aria-hidden='true'></div>"


def _bub():
    return "<span class='bub'></span>"


def _tn_sheet(seqs):
    cols = []
    for i in range(0, len(seqs), 10):
        body = "<tr><td></td>" + "".join(f"<th>{x}</th>" for x in "ABCD") + "</tr>"
        for seq in seqs[i : i + 10]:
            body += f"<tr><th>{seq}</th>" + "".join(f"<td>{_bub()}</td>" for _ in range(4)) + "</tr>"
        cols.append(f"<table class='phtn'>{body}</table>")
    return "<div class='phrow'>" + "".join(cols) + "</div>"


def _ds_sheet(items):
    labs = "abcd"
    boxes = []
    for seq, n in items:
        n = max(1, min(int(n or 4), 8))
        body = (
            f"<tr><th colspan='3'>Câu {seq}</th></tr>"
            "<tr><td></td><th>Đúng</th><th>Sai</th></tr>"
        )
        for i in range(n):
            lab = (labs[i] + ")") if i < 4 else str(i + 1)
            body += f"<tr><th>{lab}</th><td>{_bub()}</td><td>{_bub()}</td></tr>"
        boxes.append(f"<table class='phds'>{body}</table>")
    return "<div class='phrow'>" + "".join(boxes) + "</div>"


def _tln_sheet(seqs):
    marks = ["−", ","] + [str(d) for d in range(10)]
    boxes = []
    for seq in seqs:
        body = f"<tr><th colspan='5'>Câu {seq}</th></tr>"
        for mark in marks:
            body += (
                "<tr><th>"
                + html.escape(mark)
                + "</th>"
                + "".join(f"<td>{_bub()}</td>" for _ in range(4))
                + "</tr>"
            )
        boxes.append(f"<table class='phtln'>{body}</table>")
    return "<div class='phrow'>" + "".join(boxes) + "</div>"


def _phieu_html(rows, code, title):
    tn = [seq for kind, seq, _n in rows if kind == "TN"]
    ds = [(seq, n) for kind, seq, n in rows if kind == "DS"]
    tln = [seq for kind, seq, _n in rows if kind == "TLN"]
    tl = [seq for kind, seq, _n in rows if kind == "TL"]
    if not (tn or ds or tln or tl):
        return ""
    blocks = [
        "<section class='exphieu'>",
        "<h2 class='phtitle'>PHIẾU TRẢ LỜI TRẮC NGHIỆM</h2>",
        "<div class='phmeta'>",
        f"<div class='phwho'><div>Bài thi: <b>{_esc(title)}</b></div>",
        "<div>Họ và tên: ………………………………&nbsp;&nbsp; Lớp: ………&nbsp;&nbsp; SBD: …………</div>",
        f"<div>Ngày thi: {datetime.now().strftime('%d/%m/%Y')}</div></div>",
        f"<div class='phcode'>Mã đề<br><b>{_esc(code)}</b></div>",
        "<div class='phdiem'>Điểm</div>",
        "</div>",
    ]
    if tn:
        blocks.append("<h3>PHẦN I. Trắc nghiệm</h3>" + _tn_sheet(tn))
    if ds:
        blocks.append("<h3>PHẦN II. Đúng / Sai</h3>" + _ds_sheet(ds))
    if tln:
        blocks.append(
            "<h3>PHẦN III. Trả lời ngắn</h3>"
            "<p class='phhint'>Tô từng chữ số. Hàng đầu là dấu trừ, hàng sau là dấu phẩy.</p>"
            + _tln_sheet(tln)
        )
    if tl:
        lines = "".join(
            f"<div class='phtl'><b>Câu {seq}.</b> ……………………………………………………</div>" for seq in tl
        )
        blocks.append(
            "<h3>PHẦN IV. Tự luận</h3>"
            "<p class='phhint'>Ghi đáp án vào dòng. Bài làm viết trên đề.</p>"
            + lines
        )
    blocks.append("</section>")
    return "".join(blocks)


def _q_html(q, seq, src, show_key=False, ruled=False):
    kind = str(q.get("kind") or "TL")
    stem = html_question(q.get("text") or "", src)
    body = ""
    if kind == "TN":
        opts = list(q.get("options") or [])
        bits = []
        for i, o in enumerate(opts):
            lab = "ABCD"[i] if i < 4 else str(i + 1)
            ok = " ok" if show_key and o.get("correct") else ""
            bits.append(
                f"<div class='exopt{ok}'><span class='exlab'>{lab}.</span> "
                f"<span class='exoptxt'>{html_question(o.get('text') or '', src)}</span></div>"
            )
        body = f"<div class='exopts {_choice_class(opts)}'>" + "".join(bits) + "</div>"
    elif kind == "DS":
        bits = []
        for i, s in enumerate(q.get("statements") or []):
            lab = ("abcd"[i] + ")") if i < 4 else str(i + 1)
            mark = ""
            if show_key:
                mark = " <b class='exmark'>" + ("Đúng" if s.get("correct") else "Sai") + "</b>"
            bits.append(
                f"<div class='exopt'><span class='exlab'>{lab}.</span> "
                f"<span class='exoptxt'>{html_question(s.get('text') or '', src)}{mark}</span></div>"
            )
        cols = "grid2" if len(bits) >= 2 else "stack"
        body = f"<div class='exopts {cols}'>" + "".join(bits) + "</div>"
    elif kind == "TLN":
        if not ruled:
            body = "<div class='exblank'>Đáp án: …………………………</div>"
        if show_key:
            ans = str(q.get("answer") or "").strip()
            body += f"<div class='exkeyline'><b>Đáp án:</b> {html_question(ans, src) if ans else '—'}</div>"
    else:
        if not ruled:
            body = "<div class='exblank'>Đáp án: …………………………</div>"
        if show_key and str(q.get("solution") or "").strip():
            body += (
                "<div class='exkeyline'><b>Lời giải:</b> "
                + html_question(q.get("solution") or "", src)
                + "</div>"
            )
    if ruled:
        body += _rules_html(kind)
    return (
        f"<article class='exq'><div class='exstem'><b class='exno'>Câu {seq}.</b> {stem}</div>{body}</article>"
    )


def _copy_html(qs, copy, title, show_key=False, ruled=False):
    by = {int(q.get("idx")): q for q in qs}
    ids = list(copy.get("ids") or [])
    code = _esc(copy.get("code") or "")
    groups = {k: [] for k in KIND_ORDER}
    other = []
    for i in ids:
        q = by.get(int(i))
        if not q:
            continue
        k = str(q.get("kind") or "TL")
        (groups[k] if k in groups else other).append(q)
    parts = [
        "<header class='exheadblock'>"
        "<div class='exschool'>SỞ GD&ĐT …………………<br>TRƯỜNG …………………</div>"
        f"<div class='extitle'><b>ĐỀ KIỂM TRA</b><br>{_esc(title)}</div>"
        f"<div class='exmeta'>Mã đề: <b>{code}</b><br>Số câu: {len(ids)}"
        f"<br>Ngày: {datetime.now().strftime('%d/%m/%Y')}</div>"
        "</header>"
        "<p class='exnote'>Họ tên: ……………………………… Lớp: ………… SBD: …………</p>"
    ]
    key_rows = []
    sheet = []
    for kind in KIND_ORDER:
        arr = groups.get(kind) or []
        if not arr:
            continue
        parts.append(f"<h3 class='expart'>{html.escape(KIND_LABEL[kind])}</h3>")
        key_rows.append(f"<span class='exkpart'>{html.escape(KIND_LABEL[kind])}</span>")
        seq = 0
        for q in arr:
            seq += 1
            src = str(q.get("src") or "")
            qq = apply_perm(q, copy)
            parts.append(_q_html(qq, seq, src, show_key=show_key, ruled=ruled))
            if kind == "TN":
                ans = _tn_letter(qq)
            elif kind == "DS":
                ans = _ds_mask(qq)
            elif kind == "TLN":
                ans = str(qq.get("answer") or "").strip() or "—"
            else:
                ans = "TL"
            key_rows.append(f"<span class='exk'><b>{seq}.</b> {html.escape(ans)}</span>")
            nopt = len(qq.get("statements") or []) if kind == "DS" else 0
            sheet.append((kind, seq, nopt))
    key = (
        f"<section class='exanswer'><h3>ĐÁP ÁN · Mã đề {code}</h3>"
        f"<div class='exkgrid'>{''.join(key_rows)}</div></section>"
    )
    phieu = _phieu_html(sheet, str(copy.get("code") or ""), title)
    return (
        f"<section class='excopy' data-code='{code}'>"
        + "".join(parts)
        + phieu
        + (key if show_key else "")
        + "</section>"
    ), key


def exam_css():
    return """
<style>
.examwrap{max-width:none;width:100%;margin:0;padding:0}
.exambar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px;padding:10px;border:1px solid #d7e2ee;border-radius:10px;background:#f8fbff}
.exambar label{font-weight:800;font-size:13px;display:inline-flex;align-items:center;gap:6px}
.exambar input[type=number]{width:64px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}
.exambar select{padding:6px;border:1px solid #cbd8e6;border-radius:6px;background:#fff}
.exambar .muted{font-size:12px;font-weight:700;color:#64748b}
.gradebox{margin:0 0 12px;padding:10px 12px;border:1px solid #fecdd3;border-radius:10px;background:#fff7f7}
.gradebox .muted{display:block;margin-top:6px;font-size:12px;font-weight:700;color:#64748b}
.gradesum{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:baseline;font-size:20px;margin-top:8px}
.gradesum span{font-size:14px;font-weight:700}
.grademeta{font-size:12px;color:#64748b;margin:4px 0 8px}
.gradewrong{font-size:14px;line-height:1.5}
.gradecode{font-weight:800}
.exampaper{width:100%;max-width:none;margin:0;background:#fff;border:0;border-radius:0;padding:0 4px;font-family:'Times New Roman',Times,serif;font-size:12pt;line-height:1.2;color:#111}
.excopy{width:100%}
.excopy + .excopy{margin-top:18px;padding-top:10px;border-top:2px dashed #94a3b8}
.expage{position:relative;box-sizing:border-box;width:100%;min-height:0;height:auto;margin:0 0 14px;padding:0 0 8mm;background:#fff;outline:0}
.expagefoot{position:absolute;left:0;right:0;bottom:2mm;text-align:center;font:700 11pt/1.2 'Times New Roman',Times,serif;color:#111}
.exheadblock{display:grid;grid-template-columns:1fr 1.6fr 1fr;gap:6px;align-items:start;border-bottom:1.5px solid #111;padding-bottom:2px;margin-bottom:3px}
.exschool,.exmeta{font-size:11pt;line-height:1.2}.extitle{text-align:center;font-size:14pt;line-height:1.2}
.exnote{margin:1px 0 3px}
.expart{margin:6px 0 2px;font-size:12.5pt;border-bottom:1px solid #bbb;padding-bottom:1px}
.exq{margin:0 0 3px;break-inside:avoid;page-break-inside:avoid}
.exstem{margin:0}
.exstem p{margin:0}
.exno{float:left;margin-right:.35em}
.exq img{max-width:100%;max-height:40mm;height:auto}
.exopts{display:grid;gap:1px 14px;padding-left:1.15em}
.exopts.stack{grid-template-columns:1fr}
.exopts.grid2{grid-template-columns:1fr 1fr}
.exopts.grid4{grid-template-columns:1fr 1fr 1fr 1fr}
.exopt{display:flex;gap:6px;align-items:flex-start;min-width:0}
.exoptxt{min-width:0}
.exrules{margin:8px 0 2px;background-image:repeating-linear-gradient(to bottom,transparent,transparent calc(1.15em - 1px),#334155 calc(1.15em - 1px),#334155 1.15em);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.exopt.ok{background:#e8f8ee;border-radius:6px;padding:2px 6px}
.exlab{font-weight:700;min-width:1.4em}
.exblank{margin:8px 0;color:#444}
.exkeyline{margin-top:8px;padding:8px;border:1px dashed #7dd3fc;border-radius:8px;background:#f0f9ff;font-size:14px}
.exanswer{margin-top:18px;padding-top:12px;border-top:2px solid #111}
.exkgrid{display:flex;flex-wrap:wrap;gap:4px 16px}
.exkpart{flex-basis:100%;font-weight:800;margin-top:6px}
.exk{min-width:4.2rem}
.exphieu{margin-top:18px;padding:12px 14px;border:2px solid #e11d48;border-radius:8px;background:#fff}
.phtitle{margin:0 0 8px;text-align:center;font-size:18px;letter-spacing:.03em}
.phmeta{display:flex;gap:10px;align-items:stretch;margin-bottom:8px}
.phwho{flex:1;font-size:14px;line-height:1.7}
.phcode,.phdiem{border:2px solid #e11d48;min-width:78px;text-align:center;padding:6px 8px;font-size:13px}
.phcode b{display:block;font-size:26px;line-height:1.1}
.phdiem{min-width:64px}
.exphieu h3{margin:10px 0 6px;font-size:13px}
.phhint{margin:0 0 6px;font-size:12px}
.phrow{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start}
.phtn,.phds,.phtln{border-collapse:collapse;font-size:11px;background:#fff}
.phtn th,.phtn td,.phds th,.phds td,.phtln th,.phtln td{border:1px solid #fb7185;padding:1px 4px;text-align:center}
.bub{display:inline-block;width:12px;height:12px;border:1.5px solid #e11d48;border-radius:50%;vertical-align:middle}
.phtl{margin:3px 0;font-size:14px}
@media print{
  @page{size:A4;margin:10mm 10mm 12mm 10mm}
  .top,.nav,.drawer,.exambar,.gradebox,.subnav,.regline,.navtoggle,.clock,.whobar{display:none!important}
  body{background:#fff}
  .wrap,.examwrap,.exampaper{max-width:none;width:auto;margin:0;padding:0;overflow:visible}
  .exampaper{border:0;border-radius:0}
  .excopy,.expage{width:auto}
  .excopy + .excopy{margin:0;padding:0;border:0;break-before:auto;page-break-before:auto}
  .expage{outline:0;margin:0;min-height:252mm;height:262mm;padding:0 0 12mm;break-after:page;page-break-after:always}
  .exampaper .excopy:last-child .expage:last-child{break-after:auto;page-break-after:auto}
  .expage .exphieu,.expage .exanswer{break-before:auto;page-break-before:auto;margin-top:0}
  .exphieu{break-before:page;page-break-before:always;margin:0;border-color:#e11d48}
  .exanswer{break-before:page;page-break-before:always}
  .bub,.phtn th,.phtn td,.phds th,.phds td,.phtln th,.phtln td,.phcode,.phdiem{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
</style>
"""


def render_exam(auto_print=False):
    if not can_manage_bank():
        return redirect("/member/login")
    exam = session.get("exam") or {}
    path = str(exam.get("path") or "")
    copies = list(exam.get("copies") or [])
    if not path or not copies:
        return page(
            "Tạo đề",
            "<div class='wrap'><div class='panel'><div class='body'><div class='err'>Chưa có đề. Chọn số câu rồi bấm <b>Tạo đề</b> hoặc <b>Trộn đề</b>.</div>"
            "<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>",
        )
    try:
        qs = load_exam_qs(exam)
    except Exception as e:
        return page("Lỗi", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    title = exam.get("title") or lesson_title(path)
    show_key = bool(exam.get("show_key"))
    ruled = bool(exam.get("ruled"))
    papers, keys = [], []
    for copy in copies:
        html_copy, key = _copy_html(qs, copy, title, show_key=show_key, ruled=ruled)
        papers.append(html_copy)
        keys.append(key)
    dang = str(exam.get("dang") or "")
    back = str(exam.get("back") or "")
    if not back:
        back = "/member/select?path=" + urllib.parse.quote(path, safe="")
        if dang:
            back = "/member/dang?path=" + urllib.parse.quote(path, safe="") + "&dang=" + urllib.parse.quote(dang, safe="")
    codes = ", ".join(str(c.get("code") or "") for c in copies)
    key_toggle = "1" if not show_key else "0"
    key_lab = "Ẩn đáp án" if show_key else "Hiện đáp án (trang giáo viên)"
    bar = (
        "<form method='post' action='/member/exam' class='exambar noprint'>"
        f"<input type='hidden' name='path' value='{_esc(path)}'>"
        f"<input type='hidden' name='dang' value='{_esc(dang)}'>"
        f"<input type='hidden' name='keep' value='1'>"
        "<span><b>Đề đã tạo</b> · Mã: " + html.escape(codes) + f" · {sum(len(c.get('ids') or []) for c in copies[:1])} câu</span>"
        "<label>Số bản trộn <input name='exam_copies' type='number' min='1' max='20' value='"
        + str(len(copies))
        + "'></label>"
        + "<label>Ghi bài <select name='exam_ruled' onchange='this.form.submit()'>"
        + "<option value='0'" + ("" if ruled else " selected") + ">Không dòng kẻ</option>"
        + "<option value='1'" + (" selected" if ruled else "") + ">Có dòng kẻ</option>"
        + "</select></label>"
        + "<span class='muted'>Word Azota: tải .docx rồi trên Azota chọn Tạo đề thi và tải file Word lên. Azota không nhận file TEX.</span>"
        "<button class='btn' name='exam_action' value='shuffle'>🔀 Trộn đề</button>"
        "<button class='btn primary' name='exam_action' value='print' formaction='/member/exam/print'>🖨 In đề</button>"
        "<button class='btn' name='exam_action' value='azota' formaction='/member/exam/azota'>⬇ Word Azota</button>"
        "<button class='btn' name='exam_action' value='xlsx' formaction='/member/exam/xlsx'>⬇ Excel đáp án</button>"
        "<button class='btn' name='exam_action' value='save'>💾 Lưu đề và đáp án</button>"
        "<a class='btn' href='/member/exams/saved'>📚 Đề đã lưu</a>"
        f"<button class='btn' name='exam_action' value='key' formaction='/member/exam/key'>{html.escape(key_lab)}</button>"
        + ("" if exam.get("qmap") else "<button class='btn' name='exam_action' value='practice'>▶ Làm bài với đề này</button>")
        + f"<a class='btn' href='{_esc(back)}'>← Chọn lại số câu</a>"
        + "</form>"
        "<div class='gradebox noprint'>"
        "<button type='button' class='btn' id='gradeCam'>📷 Chụp phiếu chấm điểm</button>"
        "<input id='gradeFile' type='file' accept='image/*' capture='environment' hidden>"
        "<span class='muted'>Chụp phiếu học sinh đã tô, thấy rõ mã đề và các ô. Đừng chụp trang đáp án.</span>"
        "<div id='gradeOut'></div>"
        "</div>"
    )
    print_js = (
        "<script>function paginateExams(){if(document.body.getAttribute('data-expage')==='1')return;"
        "var ruler=document.createElement('div');ruler.style.cssText='position:absolute;left:0;top:0;height:248mm;width:190mm;visibility:hidden';"
        "document.body.appendChild(ruler);var limit=ruler.offsetHeight||900;ruler.remove();"
        "document.querySelectorAll('.excopy').forEach(function(copy){copy.style.width='190mm';});"
        "document.querySelectorAll('.excopy').forEach(function(copy){"
        "var code=copy.getAttribute('data-code')||'';"
        "var blocks=Array.prototype.filter.call(copy.children,function(el){return el.nodeType===1&&!el.classList.contains('expagefoot');});"
        "var heights=blocks.map(function(el){var st=getComputedStyle(el);return el.offsetHeight+(parseFloat(st.marginTop)||0)+(parseFloat(st.marginBottom)||0);});"
        "var groups=[],cur=[],h=0;function flush(){if(cur.length){groups.push(cur);cur=[];h=0;}}"
        "blocks.forEach(function(el,idx){var force=el.classList.contains('exphieu')||el.classList.contains('exanswer');"
        "if(force){flush();groups.push([el]);return;}var bh=heights[idx]||0;if(cur.length&&h+bh>limit)flush();cur.push(el);h+=bh;});flush();"
        "var n=groups.length;groups.forEach(function(group,i){var page=document.createElement('section');page.className='expage';"
        "group.forEach(function(el){page.appendChild(el);});var foot=document.createElement('div');foot.className='expagefoot';"
        "foot.textContent='Mã đề '+code+' · Trang '+(i+1)+'/'+n;page.appendChild(foot);copy.appendChild(page);});"
        "copy.style.width='';});document.body.setAttribute('data-expage','1');}"
        "window.addEventListener('load',function(){function done(){try{paginateExams();}catch(err){}"
        + ("setTimeout(function(){window.print();},250);" if auto_print else "")
        + "}if(window.MathJax&&MathJax.startup&&MathJax.startup.promise){MathJax.startup.promise.then(function(){"
        "return MathJax.typesetPromise?MathJax.typesetPromise([document.body]):null;}).then(done).catch(done);}"
        "else{if(window.ldvlTypeset)ldvlTypeset(document.body);setTimeout(done,900);}});"
        "var cam=document.getElementById('gradeCam'),file=document.getElementById('gradeFile'),out=document.getElementById('gradeOut');"
        "if(cam&&file){cam.onclick=function(){file.click();};"
        "file.onchange=function(){var f=file.files&&file.files[0];if(!f)return;"
        "var img=new Image(),url=URL.createObjectURL(f);"
        "img.onload=function(){var w=img.naturalWidth,h=img.naturalHeight,max=1600;"
        "if(w>max){h=Math.round(h*max/w);w=max;}if(h>max){w=Math.round(w*max/h);h=max;}"
        "var c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(img,0,0,w,h);"
        "URL.revokeObjectURL(url);var b64=(c.toDataURL('image/jpeg',0.82).split(',')[1]||'');"
        "var keys=[];try{keys=(window.ldvlGetGeminiKeys?ldvlGetGeminiKeys():[]).filter(function(k){return String(k||'').trim().length>=20});}catch(e){}"
        "out.textContent='Đang đọc phiếu...';"
        "fetch('/api/exam/grade-photo',{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({mime:'image/jpeg',data:b64,api_keys:keys})}).then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})"
        ".then(function(x){if(!x.j||!x.j.ok){out.textContent=(x.j&&x.j.error)||'Không chấm được.';return;}out.innerHTML=x.j.html||'';})"
        ".catch(function(){out.textContent='Lỗi mạng khi gửi ảnh phiếu.';});file.value='';};img.src=url;};}</script>"
    )
    body = (
        "<div class='wrap examwrap'>"
        + bar
        + "<div class='exampaper'>"
        + "".join(papers)
        + "</div></div>"
        + exam_css()
        + print_js
    )
    return page("Đề thi · " + title, body)


def _ruled_flag(exam=None):
    raw = request.form.get("exam_ruled")
    if raw is None:
        raw = request.args.get("exam_ruled")
    if raw is None:
        return bool((exam or session.get("exam") or {}).get("ruled"))
    return str(raw).strip().lower() in {"1", "true", "on", "yes", "co"}


def _save_exam(path, qs, ids, copies_n, shuffle, dang="", show_key=None, ruled=None, title="", back="", qmap=None):
    ids = [int(i) for i in ids if str(i).isdigit() or isinstance(i, int)]
    if not ids:
        return None
    if not shuffle:
        ids = sort_ids_by_kind(qs, ids, shuffle_within=False)
    copies = []
    used = set()
    for i in range(copies_n):
        if shuffle or i > 0:
            copy = shuffle_copy(qs, ids, shuffle_opts=True)
        else:
            copy = {"ids": list(ids), "tn_perm": {}, "ds_perm": {}, "code": new_code(used)}
        used.add(copy["code"])
        copies.append(copy)
    exam = {
        "path": path,
        "dang": dang or "",
        "title": title or lesson_title(path),
        "back": back or "",
        "copies": copies,
        "show_key": bool(session.get("exam", {}).get("show_key") if show_key is None else show_key),
        "ruled": bool(session.get("exam", {}).get("ruled") if ruled is None else ruled),
        "base_ids": list(ids),
        "variant_id": secrets.token_hex(12),
    }
    if qmap:
        exam["qmap"] = [dict(x) for x in qmap if isinstance(x, dict)]
    session["exam"] = exam
    session.modified = True
    return exam


_TEX_SYM = {
    "rightarrow": "→", "leftarrow": "←", "infty": "∞", "degree": "°", "alpha": "α",
    "beta": "β", "gamma": "γ", "delta": "δ", "Delta": "Δ", "theta": "θ", "pi": "π",
    "omega": "ω", "Omega": "Ω", "mu": "μ", "lambda": "λ", "sigma": "σ", "phi": "φ",
    "leq": "≤", "geq": "≥", "neq": "≠", "approx": "≈", "times": "×", "cdot": "·",
    "pm": "±", "div": "÷", "circ": "°", "le": "≤", "ge": "≥", "ne": "≠", "to": "→",
}


def _brace_body(s, i):
    if i >= len(s) or s[i] != "{":
        return "", i
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1 : j], j + 1
    return s[i + 1 :], len(s)


def latex_plain(src):
    """Đưa công thức về chữ Azota đọc được. Giữ [hình] nếu đề có TikZ hoặc ảnh."""
    s = str(src or "")
    s = re.sub(r"\\begin\s*\{tikzpicture\}[\s\S]*?\\end\s*\{tikzpicture\}", " [hình] ", s, flags=re.I)
    s = re.sub(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}", " [hình] ", s)
    s = s.replace("\\%", "%").replace("\\&", "&").replace("\\_", "_")
    for _ in range(12):
        nxt = s
        for name in ("text", "mathrm", "mathbf", "textbf", "textit", "textrm", "operatorname"):
            nxt = re.sub(r"\\" + name + r"\s*\{([^{}]*)\}", r"\1", nxt)
        nxt2 = []
        i = 0
        changed = False
        while i < len(nxt):
            m = re.match(r"\\(frac|sqrt)\s*", nxt[i:])
            if m and i + m.end() < len(nxt) and nxt[i + m.end()] == "{":
                a, j = _brace_body(nxt, i + m.end())
                if m.group(1) == "frac" and j < len(nxt) and nxt[j] == "{":
                    b, j = _brace_body(nxt, j)
                    nxt2.append("(" + a + ")/(" + b + ")")
                else:
                    nxt2.append("√(" + a + ")")
                i = j
                changed = True
                continue
            nxt2.append(nxt[i])
            i += 1
        nxt = "".join(nxt2)
        nxt = re.sub(r"\^\{([^{}])\}", r"^\1", nxt)
        nxt = re.sub(r"_\{([^{}])\}", r"_\1", nxt)
        nxt = re.sub(r"\^\{([^{}]*)\}", r"^(\1)", nxt)
        nxt = re.sub(r"_\{([^{}]*)\}", r"_(\1)", nxt)
        if nxt == s and not changed:
            s = nxt
            break
        s = nxt
    for name in sorted(_TEX_SYM, key=len, reverse=True):
        s = re.sub(r"\\" + re.escape(name) + r"(?![A-Za-z])", _TEX_SYM[name], s)
    s = re.sub(r"\$\$|\$|\\\(|\\\)|\\\[|\\\]", "", s)
    s = re.sub(r"\\[A-Za-z]+\*?", "", s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{2,}", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def _xml(s):
    return html.escape(str(s or ""), quote=False)


def _w_p(text, bold=False):
    b = "<w:b/>" if bold else ""
    return (
        "<w:p><w:r><w:rPr><w:rFonts w:ascii='Times New Roman' w:hAnsi='Times New Roman' "
        "w:cs='Times New Roman'/>"
        + b
        + "</w:rPr><w:t xml:space='preserve'>"
        + _xml(text)
        + "</w:t></w:r></w:p>"
    )


def _w_cell(text, bold=False):
    return "<w:tc>" + _w_p(text, bold) + "</w:tc>"


def _w_table(rows):
    borders = "".join(
        f"<w:{edge} w:val='single' w:sz='4' w:space='0' w:color='666666'/>"
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    body = "".join("<w:tr>" + "".join(_w_cell(c, i == 0) for c in row) + "</w:tr>" for i, row in enumerate(rows))
    return "<w:tbl><w:tblPr><w:tblBorders>" + borders + "</w:tblBorders></w:tblPr>" + body + "</w:tbl>"


def _azota_lines(qs, copy):
    """Một mã đề thành các đoạn Word đúng cấu trúc Azota nhận diện."""
    by = {int(q.get("idx")): q for q in qs}
    groups = {k: [] for k in KIND_ORDER}
    for i in list(copy.get("ids") or []):
        q = by.get(int(i))
        if not q:
            continue
        k = str(q.get("kind") or "TL")
        if k not in groups:
            k = "TL"
        groups[k].append(q)
    titles = {
        "TN": "PHẦN I. Câu trắc nghiệm nhiều phương án",
        "DS": "PHẦN II. Câu trắc nghiệm đúng sai",
        "TLN": "PHẦN III. Câu trắc nghiệm trả lời ngắn",
        "TL": "PHẦN IV. Tự luận",
    }
    blocks = []
    keys = {k: [] for k in KIND_ORDER}
    solutions = []
    for kind in KIND_ORDER:
        arr = groups.get(kind) or []
        if not arr:
            continue
        blocks.append(("p", titles[kind], True))
        seq = 0
        for q in arr:
            seq += 1
            srcq = apply_perm(q, copy)
            stem = latex_plain(srcq.get("text") or "")
            blocks.append(("p", f"Câu {seq}. {stem}", False))
            if kind == "TN":
                letter = "A"
                for i, o in enumerate(srcq.get("options") or []):
                    lab = "ABCD"[i] if i < 4 else str(i + 1)
                    if o.get("correct"):
                        letter = lab if i < 4 else "A"
                    blocks.append(("p", f"{lab}. {latex_plain(o.get('text') or '')}", False))
                keys[kind].append((seq, letter))
            elif kind == "DS":
                marks = []
                for i, st in enumerate(srcq.get("statements") or []):
                    lab = "abcd"[i] if i < 4 else str(i + 1)
                    blocks.append(("p", f"{lab}) {latex_plain(st.get('text') or '')}", False))
                    marks.append((lab, "Đúng" if st.get("correct") else "Sai"))
                keys[kind].append((seq, marks))
            elif kind == "TLN":
                ans = latex_plain(srcq.get("answer") or "") or "—"
                blocks.append(("p", f"Đáp án: {ans}", False))
                keys[kind].append((seq, ans))
            else:
                keys[kind].append((seq, "tự luận"))
            sol = latex_plain(srcq.get("solution") or "")
            if sol:
                solutions.append(f"{titles[kind]} — Câu {seq}. {sol}")
    code = str(copy.get("code") or "")
    head = [
        ("p", f"Mã đề {code}. File này tải lên Azota: Đề thi → Tạo đề thi → chọn file Word.", True),
    ]
    tail = [("p", "HẾT", True), ("p", "BẢNG ĐÁP ÁN", True)]
    if keys["TN"]:
        tail.append(("p", "PHẦN I", True))
        for chunk in _azota_chunks(keys["TN"], 10):
            tail.append(("t", [["Câu"] + [str(n) for n, _a in chunk], ["Chọn"] + [a for _n, a in chunk]]))
    if keys["DS"]:
        tail.append(("p", "PHẦN II", True))
        header = ["Câu", "a", "b", "c", "d"]
        rows = [header]
        for seq, marks in keys["DS"]:
            bym = {lab: val for lab, val in marks}
            rows.append([str(seq)] + [bym.get(lab, "") for lab in "abcd"])
        tail.append(("t", rows))
    if keys["TLN"]:
        tail.append(("p", "PHẦN III", True))
        tail.append(("t", [["Câu", "Đáp án"]] + [[str(n), a] for n, a in keys["TLN"]]))
    if solutions:
        tail.append(("p", "Lời giải", True))
        for line in solutions:
            tail.append(("p", line, False))
    return head + blocks + tail


def _azota_chunks(items, n):
    for i in range(0, len(items), n):
        yield items[i : i + n]


def _docx_bytes(blocks):
    parts = []
    for block in blocks:
        if block[0] == "p":
            parts.append(_w_p(block[1], bold=bool(block[2]) if len(block) > 2 else False))
        else:
            parts.append(_w_table(block[1]))
    document = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
        "<w:body>" + "".join(parts) + "<w:sectPr><w:pgSz w:w='11906' w:h='16838'/>"
        "<w:pgMar w:top='851' w:right='851' w:bottom='851' w:left='851'/></w:sectPr></w:body></w:document>"
    )
    content_types = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        "<Override PartName='/word/document.xml' "
        "ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/>"
        "</Types>"
    )
    rels = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
        "<Relationship Id='rId1' "
        "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' "
        "Target='word/document.xml'/></Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document.encode("utf-8"))
    buf.seek(0)
    return buf


def _azota_download():
    if not can_manage_bank():
        return redirect("/member")
    exam = session.get("exam") or {}
    path = str(exam.get("path") or "")
    copies = list(exam.get("copies") or [])
    if not path or not copies:
        return page(
            "Azota",
            "<div class='wrap'><div class='panel'><div class='body'><div class='err'>"
            "Chưa có đề. Hãy tạo đề rồi bấm <b>Word Azota</b>.</div>"
            "<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>",
        )
    try:
        qs = load_exam_qs(exam)
    except Exception as e:
        return page("Lỗi", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    title = exam.get("title") or lesson_title(path)
    files = []
    for copy in copies:
        code = str(copy.get("code") or "de")
        blocks = [("p", latex_plain(title) or "Đề kiểm tra", True)] + _azota_lines(qs, copy)
        files.append((f"azota-ma-{code}.docx", _docx_bytes(blocks).getvalue()))
    if len(files) == 1:
        name, raw = files[0]
        buf = io.BytesIO(raw)
        return send_file(
            buf,
            as_attachment=True,
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    pack = io.BytesIO()
    with zipfile.ZipFile(pack, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, raw in files:
            zf.writestr(name, raw)
    pack.seek(0)
    return send_file(pack, as_attachment=True, download_name="azota-de.zip", mimetype="application/zip")


def _xlsx_col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _xlsx_text(s):
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(s or ""))
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _xlsx_sheet(rows):
    width = max((len(row) for row in rows), default=1)
    body = []
    for r, row in enumerate(rows, 1):
        cells = []
        for c in range(1, width + 1):
            val = row[c - 1] if c - 1 < len(row) else ""
            style = 2 if c == 1 and r > 1 else 1
            ref = f"{_xlsx_col(c)}{r}"
            cells.append(
                f'<c r="{ref}" t="inlineStr" s="{style}"><is><t>{_xlsx_text(val)}</t></is></c>'
            )
        body.append(f'<row r="{r}">' + "".join(cells) + "</row>")
    return (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>"
        f"<cols><col min='1' max='{width}' width='9' customWidth='1'/></cols>"
        "<sheetData>" + "".join(body) + "</sheetData></worksheet>"
    )


def _xlsx_bytes(sheets):
    """sheets: [(tên sheet, các hàng)]. Hàng đầu là tiêu đề."""
    overrides = [
        "<Override PartName='/xl/workbook.xml' "
        "ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'/>",
        "<Override PartName='/xl/styles.xml' "
        "ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml'/>",
    ]
    wb_sheets = []
    rels = []
    files = {}
    for i, (name, rows) in enumerate(sheets, 1):
        safe = re.sub(r"[:\\/?*\[\]]", " ", str(name))[:31] or f"Sheet{i}"
        overrides.append(
            f"<Override PartName='/xl/worksheets/sheet{i}.xml' "
            "ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'/>"
        )
        wb_sheets.append(f"<sheet name='{_xlsx_text(safe)}' sheetId='{i}' r:id='rId{i}'/>")
        rels.append(
            f"<Relationship Id='rId{i}' "
            "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet' "
            f"Target='worksheets/sheet{i}.xml'/>"
        )
        files[f"xl/worksheets/sheet{i}.xml"] = _xlsx_sheet(rows)
    style_id = len(sheets) + 1
    rels.append(
        f"<Relationship Id='rId{style_id}' "
        "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles' "
        "Target='styles.xml'/>"
    )
    content_types = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        + "".join(overrides)
        + "</Types>"
    )
    workbook = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<workbook xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main' "
        "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
        "<sheets>" + "".join(wb_sheets) + "</sheets></workbook>"
    )
    styles = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<styleSheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>"
        "<fonts count='3'><font><sz val='11'/><name val='Calibri'/></font>"
        "<font><sz val='13'/><name val='Times New Roman'/></font>"
        "<font><b/><sz val='13'/><name val='Times New Roman'/></font></fonts>"
        "<fills count='2'><fill><patternFill patternType='none'/></fill>"
        "<fill><patternFill patternType='gray125'/></fill></fills>"
        "<borders count='2'><border><left/><right/><top/><bottom/><diagonal/></border>"
        "<border><left style='thin'><color auto='1'/></left><right style='thin'><color auto='1'/></right>"
        "<top style='thin'><color auto='1'/></top><bottom style='thin'><color auto='1'/></bottom><diagonal/></border></borders>"
        "<cellStyleXfs count='1'><xf numFmtId='0' fontId='0' fillId='0' borderId='0'/></cellStyleXfs>"
        "<cellXfs count='3'><xf numFmtId='0' fontId='0' fillId='0' borderId='0' xfId='0'/>"
        "<xf numFmtId='0' fontId='1' fillId='0' borderId='1' xfId='0' applyFont='1' applyBorder='1' applyAlignment='1'>"
        "<alignment horizontal='center' vertical='center'/></xf>"
        "<xf numFmtId='0' fontId='2' fillId='0' borderId='1' xfId='0' applyFont='1' applyBorder='1' applyAlignment='1'>"
        "<alignment horizontal='center' vertical='center'/></xf></cellXfs>"
        "</styleSheet>"
    )
    pkg_rels = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
        "<Relationship Id='rId1' "
        "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' "
        "Target='xl/workbook.xml'/></Relationships>"
    )
    wb_rels = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
        + "".join(rels)
        + "</Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", pkg_rels)
        zf.writestr("xl/workbook.xml", workbook.encode("utf-8"))
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/styles.xml", styles)
        for path, xml in files.items():
            zf.writestr(path, xml.encode("utf-8"))
    buf.seek(0)
    return buf


def _answer_text(r):
    ans = r["answer"]
    if r["kind"] == "TLN":
        return latex_plain(ans).strip() or "—"
    if r["kind"] == "TL":
        return "TL"
    if r["kind"] == "DS":
        return _norm_ds(ans) or "—"
    return ans or "—"


def _answer_sheets(qs, copies):
    """Một bảng như phiếu đáp án nhà trường: hàng 1 là mã đề, cột A là số câu.

    Số câu đếm lại từ 1 ở mỗi phần. Đúng/sai ghi D và S.
    """
    packed = []
    for copy in copies:
        code = str(copy.get("code") or "").strip() or "de"
        groups = {k: [] for k in KIND_ORDER}
        for r in _copy_answer_rows(qs, copy):
            groups[r["kind"]].append(_answer_text(r))
        packed.append((code, groups))
    rows = [[""] + [code for code, _groups in packed]]
    for kind in KIND_ORDER:
        n = max((len(groups[kind]) for _code, groups in packed), default=0)
        for i in range(n):
            rows.append(
                [str(i + 1)]
                + [groups[kind][i] if i < len(groups[kind]) else "" for _code, groups in packed]
            )
    return [("Đáp án", rows)]


def _answer_xlsx_download():
    if not can_manage_bank():
        return redirect("/member")
    exam = session.get("exam") or {}
    copies = list(exam.get("copies") or [])
    if not copies:
        return page(
            "Excel đáp án",
            "<div class='wrap'><div class='panel'><div class='body'><div class='err'>"
            "Chưa có đề. Hãy tạo đề rồi bấm <b>Excel đáp án</b>.</div>"
            "<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>",
        )
    try:
        qs = load_exam_qs(exam)
    except Exception as e:
        return page("Lỗi", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    sheets = _answer_sheets(qs, copies)
    blob = _xlsx_bytes(sheets)
    codes = [str(c.get("code") or "") for c in copies]
    name = f"dap-an-{codes[0]}.xlsx" if len(codes) == 1 else "dap-an.xlsx"
    return send_file(
        blob,
        as_attachment=True,
        download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _redirect_select(path, dang=""):
    if dang:
        return redirect(
            "/member/dang?path="
            + urllib.parse.quote(path, safe="")
            + "&dang="
            + urllib.parse.quote(dang, safe="")
        )
    return redirect("/member/select?path=" + urllib.parse.quote(path, safe=""))


def build_from_request(shuffle=False, auto_print=False, keep=False):
    m = member_current()
    if not can_manage_bank():
        if not m:
            return redirect(login_url("/member"))
        return redirect("/member")
    path = (request.form.get("path") or request.args.get("path") or "").strip()
    dang = (request.form.get("dang") or request.args.get("dang") or "").strip()
    action = (request.form.get("exam_action") or request.args.get("exam_action") or "").strip().lower()
    copies_n = _copies(request.form.get("exam_copies") or request.args.get("copies") or 1)
    keep = keep or request.form.get("keep") == "1" or action in {"shuffle", "print", "key", "practice", "lines"}
    ruled = _ruled_flag()
    if action == "print":
        auto_print = True
    if action == "shuffle":
        shuffle = True
    if action == "key":
        exam = session.get("exam") or {}
        exam["show_key"] = not bool(exam.get("show_key"))
        exam["ruled"] = ruled
        session["exam"] = exam
        session.modified = True
        return render_exam(auto_print=False)
    if action == "lines":
        exam = session.get("exam") or {}
        exam["ruled"] = ruled
        session["exam"] = exam
        session.modified = True
        return render_exam(auto_print=False)
    if action == "save":
        return save_exam_archive()
    if action == "azota":
        return _azota_download()
    if action == "xlsx":
        return _answer_xlsx_download()
    if action == "practice":
        exam = session.get("exam") or {}
        if exam.get("qmap"):
            back = str(exam.get("back") or "/member")
            return page(
                "Làm bài",
                "<div class='wrap'><div class='panel'><div class='body'><div class='err'>"
                "Đề tạo từ cả chương dùng In đề hoặc Word Azota. Làm bài từng câu mở ma trận của một bài.</div>"
                f"<p><a class='btn' href='{_esc(back)}'>← Về ma trận</a></p></div></div></div>",
            )
        copy = (exam.get("copies") or [{}])[0]
        ids = list(copy.get("ids") or exam.get("base_ids") or [])
        p = str(exam.get("path") or path)
        if not p or not ids or not can_practice(m, p):
            return _redirect_select(path or p, dang)
        qs = load_qs(p)
        kinds = {
            str((next((q for q in qs if q.get("idx") == i), {}) or {}).get("kind") or "")
            for i in ids
        }
        kinds = {k for k in kinds if k}
        session.update(
            practice_path=p,
            practice_dang=str(exam.get("dang") or ""),
            practice_kind=(next(iter(kinds)) if len(kinds) == 1 else ""),
            practice_muc="",
            practice_ids=ids,
            practice_pos=0,
            practice_right=0,
            practice_streak=0,
            practice_best=0,
            practice_done=[],
            practice_ai=True,
        )
        return redirect("/member/practice")

    if str(request.form.get("chapter") or "") == "1" and action in {"create", "shuffle", "print", ""}:
        return build_chapter_exam(
            shuffle=bool(shuffle or action == "shuffle"),
            auto_print=bool(auto_print or action == "print"),
            copies_n=copies_n,
            ruled=ruled,
            mon=str(request.form.get("mon") or "").strip(),
            lop=str(request.form.get("lop") or "").strip(),
            chuong=str(request.form.get("chuong") or "").strip(),
        )

    qs = None
    ids = []
    if path:
        try:
            qs = load_qs(path)
        except Exception as e:
            return page("Lỗi", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
        ids = ids_from_qid_form(qs, request.form, dang)
        if not ids:
            ids = ids_from_pick_form(qs, request.form)

    if not ids and keep and (session.get("exam") or {}).get("copies") and action in {"shuffle", "print", ""}:
        exam = session.get("exam") or {}
        p = str(exam.get("path") or path)
        ids = list(exam.get("base_ids") or (exam.get("copies") or [{}])[0].get("ids") or [])
        if (p or exam.get("qmap")) and ids:
            try:
                qs = load_exam_qs(exam) if exam.get("qmap") else load_qs(p)
            except Exception as e:
                return page("Lỗi", f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
            exam["ruled"] = ruled
            session["exam"] = exam
            session.modified = True
            if action == "shuffle" or shuffle:
                _save_exam(
                    p, qs, ids, copies_n,
                    shuffle=True,
                    dang=exam.get("dang") or dang,
                    ruled=ruled,
                    title=exam.get("title") or "",
                    back=exam.get("back") or "",
                    qmap=exam.get("qmap") or None,
                )
            return render_exam(auto_print=auto_print)

    if not path or not ids or qs is None:
        if request.method == "POST" and action in {"create", "shuffle", "print"}:
            if path and dang:
                back = (
                    "/member/dang?path="
                    + urllib.parse.quote(path, safe="")
                    + "&dang="
                    + urllib.parse.quote(dang, safe="")
                )
            elif path:
                back = "/member/select?path=" + urllib.parse.quote(path, safe="")
            else:
                back = "/member"
            return page(
                "Tạo đề",
                "<div class='wrap'><div class='panel'><div class='body'><div class='err'>"
                "Chưa chọn được câu nào. Điền số câu <b>NB / TH / VD / VDC</b> trong ma trận rồi bấm "
                "<b>Tạo đề</b>, <b>Trộn đề</b> hoặc <b>In đề</b>.</div>"
                f"<p><a class='btn' href='{_esc(back)}'>← Về ma trận</a></p></div></div></div>",
            )
        if (session.get("exam") or {}).get("copies"):
            return render_exam(auto_print=auto_print)
        return _redirect_select(path, dang) if path else redirect("/member")
    _save_exam(
        path,
        qs,
        ids,
        copies_n,
        shuffle=bool(shuffle or action == "shuffle" or copies_n > 1),
        dang=dang,
        ruled=ruled,
    )
    return render_exam(auto_print=auto_print)




# Mỗi phiên đề có kho biến số riêng. Chỉ giữ mã khóa trong session để
# tránh vượt giới hạn cookie khi thay nhiều câu và nhiều mã đề.
def _variant_file_id(code):
    value = str(code or "").lower().strip()
    if not re.fullmatch(r"[0-9a-f]{24}", value):
        raise ValueError("Mã bản nháp biến số không hợp lệ.")
    return value


def _variant_api_path(code):
    return "contents/ngan-hang/_de-da-luu/_bien-so/" + _variant_file_id(code) + ".json"


def _variant_read(code):
    try:
        obj = gh_api(_variant_api_path(code) + "?ref=" + urllib.parse.quote(BRANCH, safe=""))
        raw = base64.b64decode(obj.get("content", "")).decode("utf-8")
        data = json.loads(raw)
        return (data if isinstance(data, dict) else {}), obj.get("sha")
    except Exception as exc:
        if "404" in str(exc):
            return {}, None
        raise


def _hydrate_variants(exam):
    if not isinstance(exam, dict):
        return
    code = exam.get("variant_id")
    if not code or exam.get("_variant_loaded"):
        return
    # Đề mở từ kho lưu có bản chụp riêng, ưu tiên các biến thể đã lưu.
    data, _sha = _variant_read(code)
    copies = exam.get("copies") or []
    for copy in copies:
        extra = data.get(str(copy.get("code") or ""), {})
        if isinstance(extra, dict):
            merged = dict(copy.get("overrides") or {})
            merged.update(extra)
            copy["overrides"] = merged
    exam["_variant_loaded"] = True


@app.post("/api/exam/variant/apply")
def member_exam_variant_apply():
    if not can_manage_bank():
        return jsonify(ok=False, error="Chỉ quản trị viên mới được thay số đề thi."), 403
    data = request.get_json(silent=True) or {}
    exam = session.get("exam") or {}
    code = str(data.get("code") or "")
    copy = next((x for x in (exam.get("copies") or []) if str(x.get("code")) == code), None)
    if not copy:
        return jsonify(ok=False, error="Mã đề không tồn tại."), 400
    try:
        idx = int(data.get("idx"))
        if idx not in copy.get("ids", []):
            raise ValueError("Câu không thuộc mã đề này.")
        qs = load_exam_qs(exam)
        q = next(x for x in qs if int(x.get("idx")) == idx)
        kind = str(q.get("kind") or "")
        if kind not in ("TN", "DS", "TLN", "TL"):
            raise ValueError("Loại câu chưa được hỗ trợ.")
        stem = str(data.get("stem") or "").strip()
        sol = str(data.get("solution") or "").strip()
        ans = str(data.get("answer") or "").strip()
        raw_opts = data.get("options") if isinstance(data.get("options"), list) else []
        if not stem or not sol or len(stem) > 20000 or len(sol) > 30000:
            raise ValueError("Đề và lời giải cần đầy đủ.")
        if stem == str(q.get("text") or "").strip():
            raise ValueError("Đề chưa được thay số hoặc nội dung.")
        variant = {"text": stem, "solution": sol, "answer": ans}
        if kind in ("TN", "DS"):
            if len(raw_opts) != 4:
                raise ValueError("Cần đủ bốn phương án hoặc bốn ý đúng/sai.")
            opts = []
            for x in raw_opts:
                if not isinstance(x, dict) or not isinstance(x.get("correct"), bool):
                    raise ValueError("Định dạng đáp án chưa đúng.")
                t = str(x.get("text") or "").strip()
                if not t or len(t) > 5000:
                    raise ValueError("Phương án hoặc ý đúng/sai không hợp lệ.")
                opts.append({"text": t, "correct": x["correct"]})
            if kind == "TN" and sum(x["correct"] for x in opts) != 1:
                raise ValueError("Trắc nghiệm phải có đúng một đáp án đúng.")
            variant["options" if kind == "TN" else "statements"] = opts
        elif kind == "TLN" and not ans:
            raise ValueError("Câu trả lời ngắn cần có đáp án mới.")
        token = _variant_file_id(exam.get("variant_id"))
        store, sha = _variant_read(token)
        store.setdefault(code, {})[str(idx)] = variant
        encoded = base64.b64encode(json.dumps(store, ensure_ascii=False).encode("utf-8")).decode("ascii")
        payload = {"message": "Save recalculated numeric exam variant",
                   "content": encoded, "branch": BRANCH}
        if sha:
            payload["sha"] = sha
        gh_api(_variant_api_path(token), "PUT", payload)
        return jsonify(ok=True, message="Đã cập nhật đề và đáp án của mã " + code)
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)[:350]), 400


# Kho lưu đề ở GitHub để không mất khi Render khởi động lại.
# Mỗi đề là một tệp JSON; mã đề và hoán vị đáp án được cố định.
_SAVED_PREFIX = "ngan-hang/_de-da-luu/"


def _saved_id(raw):
    value = str(raw or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{24}", value):
        raise ValueError("Mã đề lưu không hợp lệ.")
    return value


def _saved_api_path(code):
    return "contents/" + _SAVED_PREFIX + _saved_id(code) + ".json"


def _saved_load(code):
    raw = gh_api(_saved_api_path(code) + "?ref=" + urllib.parse.quote(BRANCH, safe=""))
    payload = json.loads(base64.b64decode(raw.get("content", "")).decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("exam"), dict):
        raise ValueError("Dữ liệu đề không hợp lệ.")
    return payload, raw.get("sha", "")


def save_exam_archive():
    if not can_manage_bank():
        return redirect("/member/login")
    exam = session.get("exam") or {}
    if not exam.get("copies") or not exam.get("path"):
        return page("Lưu đề", "<p>Chưa có đề để lưu.</p>")
    try:
        qs = load_exam_qs(exam)
        if not qs:
            raise ValueError("Không tìm thấy câu hỏi.")
        frozen = dict(exam)
        frozen["snapshot_qs"] = qs
        frozen["show_key"] = False
        code = secrets.token_hex(12)
        payload = {
            "id": code,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": str(exam.get("title") or lesson_title(exam.get("path")))[:200],
            "exam": frozen,
        }
        gh_api(_saved_api_path(code), "PUT", {
            "message": "Save exam " + code,
            "content": base64.b64encode(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")).decode("ascii"),
            "branch": BRANCH,
        })
    except Exception as exc:
        return page("Lỗi lưu đề", "<div class='wrap'><div class='err'>Không lưu được đề: " + _esc(exc) + "</div><a href='/member/exam'>← Quay lại</a></div>")
    return redirect("/member/exams/saved?new=" + code)


@app.get("/member/exams/saved")
def member_saved_exams():
    if not can_manage_bank():
        return redirect("/member/login")
    try:
        rows = gh_api("contents/" + _SAVED_PREFIX.rstrip("/") + "?ref=" + urllib.parse.quote(BRANCH, safe=""))
        if not isinstance(rows, list):
            rows = []
    except Exception as exc:
        if "404" in str(exc):
            rows = []
        else:
            return page("Đề đã lưu", "<div class='wrap'><div class='err'>Không tải được kho đề: " + _esc(exc) + "</div></div>")
    items = []
    for row in rows:
        name = row.get("name", "")
        if not re.fullmatch(r"[0-9a-f]{24}\.json", name):
            continue
        try:
            saved, _ = _saved_load(name[:-5])
            title = _esc(saved.get("title") or "Đề kiểm tra")
            created = _esc(saved.get("created") or "")
            code = _esc(name[:-5])
            copies = saved.get("exam", {}).get("copies") or []
            n = len((copies[0] if copies else {}).get("ids") or [])
            items.append("<div style='padding:12px;border:1px solid #cbd5e1;border-radius:10px;margin:10px 0'>"
                "<b>" + title + "</b><div style='color:#64748b'>Ngày lưu: " + created + " · " + str(n) + " câu · " + str(len(copies)) + " mã đề</div>"
                "<form method='post' action='/member/exams/open' style='margin-top:8px'>"
                "<input type='hidden' name='id' value='" + code + "'>"
                "<button class='btn primary'>📖 Mở lại đề này</button></form></div>")
        except Exception:
            continue
    note = "<p class='success'>✅ Đã lưu đề và đáp án thành công.</p>" if request.args.get("new") else ""
    return page("Đề đã lưu", "<div class='wrap'><h2>📚 Đề kiểm tra đã lưu</h2>" + note +
                ("".join(items) if items else "<p>Chưa có đề được lưu.</p>") +
                "<p><a class='btn' href='/member/exam'>← Quay lại đề hiện tại</a></p></div>")


@app.post("/member/exams/open")
def member_open_saved_exam():
    if not can_manage_bank():
        return redirect("/member/login")
    try:
        saved, _ = _saved_load(request.form.get("id"))
        exam = saved["exam"]
        if not exam.get("copies") or not exam.get("snapshot_qs"):
            raise ValueError("Đề lưu thiếu dữ liệu.")
        lean = {k: v for k, v in exam.items() if k != "snapshot_qs"}
        lean["saved_code"] = saved["id"]
        session["exam"] = lean
        session.modified = True
    except Exception as exc:
        return page("Mở đề", "<div class='wrap'><div class='err'>Không mở được đề: " + _esc(exc) + "</div></div>")
    return redirect("/member/exam")


@app.route("/member/exam", methods=["GET", "POST"])
def member_exam():
    if request.method == "GET":
        return render_exam(auto_print=False)
    action = (request.form.get("exam_action") or "").strip().lower()
    return build_from_request(shuffle=(action == "shuffle"), auto_print=(action == "print"))


@app.route("/member/exam/azota", methods=["POST"])
def member_exam_azota():
    return build_from_request()


@app.route("/member/exam/xlsx", methods=["POST"])
def member_exam_xlsx():
    return build_from_request()


@app.route("/member/exam/print", methods=["GET", "POST"])
def member_exam_print():
    if request.method == "POST":
        return build_from_request(shuffle=False, auto_print=True)
    return render_exam(auto_print=True)


def _norm_letter(s):
    m = re.search(r"[ABCD]", str(s or "").upper())
    return m.group(0) if m else ""


def _norm_ds(s):
    t = str(s or "").upper().replace("Đ", "D").replace("Ð", "D")
    return re.sub(r"[^DS]", "", t)


def _norm_tln(s):
    t = str(s or "").strip()
    t = t.replace("$", "").replace("\\,", "").replace("\\;", "")
    t = re.sub(r"\\[a-zA-Z]+\*?\{([^{}]*)\}", r"\1", t)
    t = t.replace("{", "").replace("}", "").replace("\\", "")
    t = t.replace(" ", "").replace(",", ".")
    t = t.replace("−", "-").replace("–", "-").replace("—", "-")
    try:
        v = float(t)
    except ValueError:
        return t.lower()
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return "%g" % v


def _ds_points(got, exp):
    n = min(len(got), len(exp))
    hit = sum(1 for i in range(n) if got[i] == exp[i])
    return {1: 0.1, 2: 0.25, 3: 0.5, 4: 1.0}.get(hit, 0)


def _score_sheet(rows, read):
    """Chấm theo ô đã tô. TN và trả lời ngắn 0,25 điểm; đúng/sai theo số ý đúng."""
    tn = read.get("tn") if isinstance(read.get("tn"), dict) else {}
    ds = read.get("ds") if isinstance(read.get("ds"), dict) else {}
    tln = read.get("tln") if isinstance(read.get("tln"), dict) else {}
    total = 0.0
    lines = []
    counts = {"TN": [0, 0], "DS": [0, 0], "TLN": [0, 0]}
    for r in rows:
        if r["kind"] == "TL":
            continue
        n = str(r["n"])
        if r["kind"] == "TN":
            got, exp = _norm_letter(tn.get(n)), _norm_letter(r["answer"])
            ok = bool(got) and got == exp
            pt = 0.25 if ok else 0
            show = got or "—"
        elif r["kind"] == "DS":
            got, exp = _norm_ds(ds.get(n)), _norm_ds(r["answer"])
            ok = bool(got) and got == exp
            pt = _ds_points(got, exp)
            show = got or "—"
        else:
            got, exp = _norm_tln(tln.get(n)), _norm_tln(r["answer"])
            ok = bool(got) and got == exp
            pt = 0.25 if ok else 0
            show = got or "—"
        total += pt
        counts[r["kind"]][0] += 1 if ok else 0
        counts[r["kind"]][1] += 1
        if not ok:
            part = {"TN": "Phần I", "DS": "Phần II", "TLN": "Phần III"}.get(r["kind"], "")
            lines.append(
                f"<div>{part} · Câu {n}: tô <b>{_esc(show)}</b> · đúng <b>{_esc(r['answer'] or '—')}</b></div>"
            )
    def _pair(k):
        a, b = counts[k]
        return f"{a}/{b}"
    summary = (
        f"Trắc nghiệm {_pair('TN')} · Đúng/Sai {_pair('DS')} · Trả lời ngắn {_pair('TLN')}"
    )
    wrong = "".join(lines) or "<div>Không có câu khách quan nào sai.</div>"
    html = (
        f"<div class='gradesum'><b>Điểm: {total:.2f}</b>"
        f"<span>{summary}</span></div>"
        "<div class='grademeta'>TN và trả lời ngắn: 0,25 điểm/câu đúng. "
        "Đúng/Sai: 1 ý 0,1 · 2 ý 0,25 · 3 ý 0,5 · 4 ý 1. Tự luận chưa chấm.</div>"
        f"<div class='gradewrong'><b>Câu chưa đúng</b>{wrong}</div>"
    )
    return {"score": round(total, 2), "html": html}


def _read_sheet_with_gemini(image, outline, api_key):
    from student_gemini import _gemini_generate
    prompt = (
        "Đây là ảnh PHIẾU TRẢ LỜI TRẮC NGHIỆM. Học sinh tô tròn các ô.\n"
        "Chỉ đọc ô đã tô trên phiếu. Nếu ảnh có kèm khối ĐÁP ÁN của giáo viên thì bỏ qua hoàn toàn.\n"
        "Phần I: mỗi hàng là một câu, cột A B C D, một ô được tô.\n"
        "Phần II: mỗi câu có ý a b c d, mỗi ý một cột Đúng và một cột Sai.\n"
        "Phần III: mỗi câu là lưới. Hàng là ký tự − , 0 1 2 3 4 5 6 7 8 9. "
        "Bốn cột là bốn vị trí của số, từ trái sang phải. Ghép các ô tô thành một số, ví dụ − 1 , 5 thành -1.5.\n"
        "Cấu trúc câu của đề này:\n" + outline + "\n"
        "Trả về JSON duy nhất, không markdown:\n"
        '{"code":"402","tn":{"1":"A"},"ds":{"19":"ĐSĐS"},"tln":{"26":"-1.5"}}\n'
        "code là số mã đề in trong ô Mã đề. "
        "tn là một chữ A, B, C hoặc D. "
        "ds là đúng 4 ký tự Đ hoặc S theo thứ tự a b c d. "
        "tln là số đọc từ ô tô. Câu bỏ trống thì không ghi."
    )
    raw = _gemini_generate(
        api_key, prompt, max_tokens=2500, temperature=0,
        images=[{"mime": image.get("mime") or "image/jpeg", "data": image.get("data") or ""}],
    )
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("Không đọc được phiếu. Chụp thẳng, đủ sáng, thấy mã đề và các ô tô.")
    data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("Phiếu trả về không đúng dạng.")
    return data


@app.post("/api/exam/grade-photo")
def member_exam_grade_photo():
    if not can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới chấm phiếu."), 403
    exam = session.get("exam") or {}
    copies = list(exam.get("copies") or [])
    if not copies:
        return jsonify(ok=False, error="Chưa có đề trong phiên này. Tạo hoặc trộn đề rồi chấm."), 400
    body = request.get_json(silent=True) or {}
    raw_img = str(body.get("data") or "")
    if raw_img.strip().startswith("data:") and "," in raw_img[:80]:
        raw_img = raw_img.split(",", 1)[1]
    image = {"mime": body.get("mime") or "image/jpeg", "data": raw_img.strip()}
    if not image["data"] or len(image["data"]) > 6_000_000:
        return jsonify(ok=False, error="Ảnh phiếu không hợp lệ."), 400
    from app import GEMINI_KEY
    api_keys = []
    if str(GEMINI_KEY or "").strip():
        api_keys.append(str(GEMINI_KEY).strip())
    extra = body.get("api_keys") if isinstance(body.get("api_keys"), list) else []
    extra = list(extra) + [body.get("api_key")]
    for item in extra:
        s = str(item or "").strip()
        if len(s) >= 20 and s not in api_keys:
            api_keys.append(s)
    if not api_keys:
        return jsonify(ok=False, error="Chưa có key Gemini. Nạp key ở mục phản biện, hoặc đặt GEMINI_API_KEY trên máy chủ."), 400
    qs = load_exam_qs(exam)
    keys = []
    for c in copies:
        rows = _copy_answer_rows(qs, c)
        keys.append((str(c.get("code") or ""), rows))
    outline = "\n".join(
        {"TN": "Phần I", "DS": "Phần II", "TLN": "Phần III"}.get(r["kind"], "")
        + f" câu {r['n']}: "
        + {"TN": "A/B/C/D", "DS": "Đúng/Sai 4 ý a b c d", "TLN": "số"}.get(r["kind"], "")
        for r in (keys[0][1] if keys else [])
        if r["kind"] != "TL"
    )
    read = None
    last_err = "Gemini không đọc được phiếu."
    for api_key in api_keys:
        try:
            read = _read_sheet_with_gemini(image, outline, api_key)
            break
        except Exception as e:
            last_err = str(e)[:300] or last_err
            if api_key and api_key in last_err:
                last_err = last_err.replace(api_key, "…")
    if not isinstance(read, dict):
        return jsonify(ok=False, error=last_err), 502
    code = re.sub(r"\D", "", str(read.get("code") or ""))
    match = None
    for c, rows in keys:
        if c == code or c.lstrip("0") == code.lstrip("0"):
            match = (c, rows)
            break
    if not match and len(keys) == 1:
        match = keys[0]
        code = match[0]
    if not match:
        return jsonify(ok=False, error=f"Không thấy mã đề {code or '?'} trong các đề đang mở."), 404
    scored = _score_sheet(match[1], read)
    scored["ok"] = True
    scored["code"] = match[0]
    scored["html"] = f"<div class='gradecode'>Mã đề {_esc(match[0])}</div>" + scored["html"]
    return jsonify(scored)


@app.post("/member/exam/key")
def member_exam_key():
    return build_from_request()


_MX_LEVELS = (("N", "NB"), ("H", "TH"), ("V", "VD"), ("C", "VDC"))
_MX_KINDS = (
    ("TN", "Trắc nghiệm"),
    ("DS", "Đúng / Sai"),
    ("TLN", "Trả lời ngắn"),
    ("TL", "Tự luận"),
)


def exam_matrix_html(path, qs, dang="", include_practice=True):
    """Ma trận số câu theo dạng × loại × NB/TH/VD/VDC. Gửi thẳng sang tạo / trộn / in đề."""
    dang = str(dang or "").strip()
    names, seen = [], set()
    for q in qs or []:
        d = q.get("dang")
        if d not in seen:
            seen.add(d)
            names.append(d)
    if dang:
        targets = []
        for i, d in enumerate(names):
            label = str(d or "").strip()
            if label == dang or (dang == "Chưa phân dạng" and not label):
                targets.append((i, d))
        if not targets:
            return ""
    else:
        targets = list(enumerate(names))
    rows = []
    for di, dname in targets:
        arr = [q for q in qs if q.get("dang") == dname]
        uncat = not str(dname or "").strip() or str(dname).strip() == "Chưa phân dạng"
        mark = "<span class='tag miss'>Chưa có</span>" if uncat else "<span class='tag had'>Đã có</span>"
        kind_cells = []
        for kind, label in _MX_KINDS:
            picks = []
            for z, lab in _MX_LEVELS:
                n = sum(1 for q in arr if q.get("kind") == kind and q.get("level") == z)
                off = " off" if n <= 0 else ""
                dis = " disabled" if n <= 0 else ""
                picks.append(
                    f"<span class='mxpick{off}' title='{html.escape(label)} · {html.escape(lab)} · kho {n}'>"
                    f"<b>{n}</b>"
                    f"<input class='n' type='number' min='0' max='{n}' value='0' "
                    f"name='pick:{di}:{kind}:{z}' aria-label='{html.escape(label)} {html.escape(lab)}'{dis}>"
                    f"</span>"
                )
            kind_cells.append("<td class='mxkind'><div class='mxline'>" + "".join(picks) + "</div></td>")
        cls = "uncat" if uncat else "had"
        rows.append(
            f"<tr class='{cls}'><td class='mxname'>{html.escape(str(dname or 'Chưa phân dạng'))} {mark}</td>"
            + "".join(kind_cells)
            + "</tr>"
        )
    if not rows:
        return ""
    practice = ""
    if include_practice:
        practice = (
            "<button class='btn primary' type='submit' name='ai_review' value='0' formaction='/member/start'>▶ Làm bài</button>"
            "<button class='btn' type='submit' name='ai_review' value='1' formaction='/member/start'>🤖 Làm bài + phản biện</button>"
        )
    controls = (
        "<label class='examcopies'>Số bản trộn <input name='exam_copies' type='number' min='1' max='20' value='1'></label>"
        "<label class='examcopies'>Ghi bài <select name='exam_ruled'>"
        "<option value='0'>Không dòng kẻ</option><option value='1'>Có dòng kẻ</option></select></label>"
    )
    submits = (
        "<button class='btn green' type='submit' name='exam_action' value='create'>📝 Tạo đề</button>"
        "<button class='btn' type='submit' name='exam_action' value='shuffle'>🔀 Trộn đề</button>"
        "<button class='btn' type='submit' name='exam_action' value='print'>🖨 In đề</button>"
    )
    top = "<div class='modebar'>" + practice + controls + submits + "</div>"
    bottom = "<div class='modebar'>" + practice + submits + "</div>"
    chapter_btn = _chapter_matrix_btn(path)
    return (
        "<form method='post' action='/member/exam' id='examMatrix' class='exammatrix'>"
        f"<input type='hidden' name='path' value='{_esc(path)}'>"
        f"<input type='hidden' name='dang' value='{_esc(dang)}'>"
        + chapter_btn
        + "<div class='notice'>📝 <b>Ma trận đề</b> — mỗi dạng một dòng. Số xanh là số câu đang có, ô là số câu lấy. "
        "Dạng ít câu thì bấm <b>AI gợi ý gom dạng</b> để gộp dạng cùng kỹ năng. "
        "<b>Tạo đề</b> lấy đúng số đó. <b>Trộn đề</b> và <b>In đề</b> xáo câu trong từng phần, đảo A–D và a)–d), "
        "mỗi bản một mã đề. In thì mỗi mã đề sang trang mới, cuối đề có phiếu tô đáp án.</div>"
        + top
        + "<p style='margin:8px 0'><button type='button' class='btn' id='aiGom' "
        "title='Gợi ý gộp các dạng ít câu, cùng kỹ năng, thành ít dạng hơn. Xem bảng rồi mới ghi.'>"
        "📎 AI gợi ý gom dạng</button></p><div id='aiGomOut'></div>"
        + "<div class='selectwrap'><table class='selectgrid mxone'><tr><th>Dạng bài</th>"
        + "".join(
            "<th>"
            + html.escape(label)
            + "<div class='mxlabs'><span title='Nhận biết'>NB</span><span title='Thông hiểu'>TH</span>"
            "<span title='Vận dụng'>VD</span><span title='Vận dụng cao'>VDC</span></div></th>"
            for _kind, label in _MX_KINDS
        )
        + "</tr>"
        + "".join(rows)
        + "</table></div>"
        "<div id='examSum' class='notice' style='margin-top:10px'>TỔNG CHỌN: 0 câu</div>"
        + bottom
        + "</form>"
        "<style>.exammatrix .modebar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}"
        ".exammatrix .examcopies{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px}"
        ".exammatrix .examcopies input,.exammatrix .examcopies select{padding:6px;border:1px solid #cbd8e6;border-radius:6px;background:#fff}"
        ".exammatrix .examcopies input{width:64px;text-align:center}"
        ".exammatrix table.mxone{width:max-content}"
        ".exammatrix .mxone th,.exammatrix .mxone td{padding:3px 5px;vertical-align:middle}"
        ".exammatrix .mxname{text-align:left;font-weight:700;line-height:1.25;white-space:nowrap}"
        ".exammatrix .mxlabs,.exammatrix .mxline{display:grid;grid-template-columns:repeat(4,48px);gap:2px;justify-content:center;align-items:center}"
        ".exammatrix .mxlabs span{font-size:10px;font-weight:800;color:#334155;text-align:center}"
        ".exammatrix td.mxkind{background:#f0fdf4}"
        ".exammatrix .mxpick{display:flex;flex-direction:row;align-items:center;justify-content:center;gap:2px}"
        ".exammatrix .mxpick b{font-size:11px;line-height:1;font-weight:800;color:#166534;min-width:1.1em;text-align:right}"
        ".exammatrix .mxpick .n{width:26px;padding:1px 0;font-size:12px;font-weight:800}"
        ".exammatrix .mxpick.off{opacity:.38}"
        ".exammatrix tr.uncat .mxname{background:#fff8df}</style>"
        "<script>(function(){var f=document.getElementById('examMatrix');if(!f)return;"
        "function upd(){var t=0;f.querySelectorAll('.n').forEach(function(x){var m=Number(x.max)||0,v=Math.max(0,Math.min(m,Number(x.value)||0));x.value=v;t+=v});"
        "var s=document.getElementById('examSum');if(s)s.textContent='TỔNG CHỌN: '+t+' câu — điền NB/TH/VD/VDC rồi Tạo đề, Trộn đề hoặc In đề.';}"
        "f.querySelectorAll('.n').forEach(function(x){x.addEventListener('input',upd)});upd();"
        "f.addEventListener('submit',function(e){var t=0;f.querySelectorAll('.n').forEach(function(x){t+=Number(x.value)||0});"
        "if(t<=0){e.preventDefault();alert('Hãy điền số câu NB/TH/VD/VDC trong ma trận rồi bấm Tạo đề, Trộn đề hoặc In đề.');}});"
        "})();</script>"
    )


def _chapter_matrix_btn(path):
    """Nút mở ma trận cả chương, gắn ngay trên ma trận của một bài."""
    try:
        from app import chapter_lessons_for
        _sibs, cur = chapter_lessons_for(path)
    except Exception:
        return ""
    cur = cur or {}
    mon = str(cur.get("Mon") or "").strip()
    lop = str(cur.get("Lop") or "").strip()
    chuong = str(cur.get("Chuong") or "").strip()
    if not mon or not chuong:
        return ""
    href = "/member/chapter/matrix?" + _chapter_query(mon, lop, chuong)
    short = chuong if len(chuong) <= 56 else chuong[:55] + "…"
    return (
        "<p style='margin:0 0 8px'><a class='btn green' href='"
        + _esc(href)
        + "'>📝 Tạo đề theo ma trận cả chương</a> <span class='muted'>"
        + html.escape(short)
        + "</span></p>"
    )


def _chapter_query(mon, lop, chuong):
    return (
        "mon="
        + urllib.parse.quote(str(mon or ""), safe="")
        + "&lop="
        + urllib.parse.quote(str(lop or ""), safe="")
        + "&chuong="
        + urllib.parse.quote(str(chuong or ""), safe="")
    )


def _chapter_rows(mon, lop, chuong):
    from dang_routes import _chapter_lessons, _lesson_title

    rows = []
    for item in _chapter_lessons(mon, lop, chuong):
        path = str(item.get("path") or item.get("file") or "").replace("\\", "/")
        title = _lesson_title(item) or (path.rsplit("/", 1)[-1] if path else "Bài")
        if not path.startswith("ngan-hang/"):
            continue
        try:
            qs = load_qs(path)
        except Exception:
            qs = []
        rows.append((title, path, qs))
    return rows


def _plain_snip(text, n=72):
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", str(text or ""))
    t = t.replace("{", " ").replace("}", " ").replace("$", " ")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > n:
        t = t[: n - 1] + "…"
    return t


def _chapter_chosen(rows, form, shuffle):
    """Câu đã tick, hoặc số câu theo loại. None nếu không dùng cách này."""
    index = {}
    for i, (_title, path, qs) in enumerate(rows):
        for q in qs:
            try:
                index[(i, int(q.get("idx")))] = (path, q)
            except (TypeError, ValueError):
                continue
    chosen = []
    seen = set()
    raws = form.getlist("qsel") if hasattr(form, "getlist") else []
    for raw in raws:
        try:
            a, b = str(raw).split(":", 1)
            key = (int(a), int(b))
        except (TypeError, ValueError):
            continue
        if key in index and key not in seen:
            seen.add(key)
            chosen.append(index[key])
    if chosen:
        return chosen
    wants = {}
    any_pick = False
    for kind, _lab in _MX_KINDS:
        try:
            n = max(0, int(form.get(f"kpick:{kind}") or 0))
        except (TypeError, ValueError):
            n = 0
        wants[kind] = n
        if n:
            any_pick = True
    if not any_pick:
        return None
    pools = {k: [] for k, _lab in _MX_KINDS}
    for _title, path, qs in rows:
        for q in qs:
            k = str(q.get("kind") or "")
            if k in pools:
                pools[k].append((path, q))
    chosen = []
    for kind, _lab in _MX_KINDS:
        n = wants.get(kind) or 0
        pool = pools.get(kind) or []
        if n <= 0 or not pool:
            continue
        if shuffle:
            chosen.extend(random.sample(pool, min(n, len(pool))))
        else:
            chosen.extend(pool[: min(n, len(pool))])
    return chosen


def _merge_chosen(chosen):
    picked = []
    merged = []
    for path, q in chosen:
        picked.append({"path": path, "idx": int(q["idx"])})
        qq = dict(q)
        qq["idx"] = len(merged)
        merged.append(qq)
    return picked, merged


def build_chapter_exam(shuffle, auto_print, copies_n, ruled, mon, lop, chuong):
    back = "/member/chapter/matrix?" + _chapter_query(mon, lop, chuong)
    rows = _chapter_rows(mon, lop, chuong)
    form = request.form
    chosen = _chapter_chosen(rows, form, bool(shuffle))
    if chosen is not None:
        if not chosen or not rows:
            return page(
                "Tạo đề",
                "<div class='wrap'><div class='panel'><div class='body'><div class='err'>"
                "Chưa chọn được câu nào. Điền <b>số câu theo loại</b>, tick câu trong từng bài, "
                "hoặc điền ô ma trận rồi bấm <b>Tạo đề</b>, <b>Trộn đề</b> hoặc <b>In đề</b>.</div>"
                f"<p><a class='btn' href='{_esc(back)}'>← Về ma trận</a></p></div></div></div>",
            )
        picked, merged = _merge_chosen(chosen)
        title = " · ".join(x for x in (mon, ("Lớp " + lop) if lop else "", chuong) if x)
        _save_exam(
            rows[0][1],
            merged,
            [q["idx"] for q in merged],
            copies_n,
            shuffle=bool(shuffle or copies_n > 1),
            title=title,
            back=back,
            qmap=picked,
            ruled=ruled,
        )
        return render_exam(auto_print=auto_print)
    picked = []
    merged = []
    for i, (_title, path, qs) in enumerate(rows):
        for kind, _kl in _MX_KINDS:
            for lev, _ll in _MX_LEVELS:
                try:
                    n = max(0, int(form.get(f"cpick:{i}:{kind}:{lev}") or 0))
                except (TypeError, ValueError):
                    n = 0
                if n <= 0:
                    continue
                pool = [q for q in qs if q.get("kind") == kind and q.get("level") == lev]
                if not pool:
                    continue
                for q in random.sample(pool, min(n, len(pool))):
                    picked.append({"path": path, "idx": int(q["idx"])})
                    qq = dict(q)
                    qq["idx"] = len(merged)
                    merged.append(qq)
    if not merged or not rows:
        return page(
            "Tạo đề",
            "<div class='wrap'><div class='panel'><div class='body'><div class='err'>"
            "Chưa chọn được câu nào. Điền số câu <b>NB / TH / VD / VDC</b> theo từng bài rồi bấm "
            "<b>Tạo đề</b>, <b>Trộn đề</b> hoặc <b>In đề</b>.</div>"
            f"<p><a class='btn' href='{_esc(back)}'>← Về ma trận</a></p></div></div></div>",
        )
    title = " · ".join(x for x in (mon, ("Lớp " + lop) if lop else "", chuong) if x)
    _save_exam(
        rows[0][1],
        merged,
        [q["idx"] for q in merged],
        copies_n,
        shuffle=bool(shuffle or copies_n > 1),
        title=title,
        back=back,
        qmap=picked,
        ruled=ruled,
    )
    return render_exam(auto_print=auto_print)


def chapter_matrix_html(mon, lop, chuong):
    rows = _chapter_rows(mon, lop, chuong)
    if not rows:
        return ""
    body_rows = []
    total = 0
    for i, (title, _path, qs) in enumerate(rows):
        total += len(qs)
        kind_cells = []
        for kind, label in _MX_KINDS:
            picks = []
            for z, lab in _MX_LEVELS:
                n = sum(1 for q in qs if q.get("kind") == kind and q.get("level") == z)
                off = " off" if n <= 0 else ""
                dis = " disabled" if n <= 0 else ""
                picks.append(
                    f"<span class='mxpick{off}' title='{html.escape(label)} · {html.escape(lab)} · kho {n}'>"
                    f"<b>{n}</b>"
                    f"<input class='n' type='number' min='0' max='{n}' value='0' "
                    f"name='cpick:{i}:{kind}:{z}' aria-label='{html.escape(title)} {html.escape(label)} {html.escape(lab)}'{dis}>"
                    f"</span>"
                )
            kind_cells.append("<td class='mxkind'><div class='mxline'>" + "".join(picks) + "</div></td>")
        body_rows.append(
            f"<tr><td class='mxname'>{i + 1}. {html.escape(title)} <span class='tag'>{len(qs)}</span></td>"
            + "".join(kind_cells)
            + "</tr>"
        )
    back = "/member/chapter?" + _chapter_query(mon, lop, chuong)
    heading = " · ".join(x for x in (mon, ("Lớp " + lop) if lop else "", chuong) if x)
    levlab = dict(_MX_LEVELS)
    short_kind = {"TN": "TN", "DS": "ĐS", "TLN": "TLN", "TL": "TL"}
    kc = {k: 0 for k, _lab in _MX_KINDS}
    pick_blocks = []
    for i, (title, _path, qs) in enumerate(rows):
        lines = []
        for q in qs:
            k = str(q.get("kind") or "")
            if k in kc:
                kc[k] += 1
            try:
                idx = int(q.get("idx"))
            except (TypeError, ValueError):
                continue
            lab = levlab.get(str(q.get("level") or ""), str(q.get("level") or ""))
            lines.append(
                "<label class='qselrow'>"
                f"<input type='checkbox' name='qsel' value='{i}:{idx}' data-k='{html.escape(k, quote=True)}'>"
                f"<b>{html.escape(short_kind.get(k, k))}</b>"
                f"<span class='tag'>{html.escape(lab)}</span>"
                f"<span class='qid'>{html.escape(str(q.get('id') or ''))}</span>"
                f"{html.escape(_plain_snip(q.get('text') or ''))}"
                "</label>"
            )
        pick_blocks.append(
            f"<details class='chpick'><summary>{i + 1}. {html.escape(title)}"
            f" <span class='tag'>{len(qs)} câu</span></summary>"
            + "".join(lines)
            + "</details>"
        )
    kind_inputs = "".join(
        f"<label>{html.escape(label)} <input class='kpick' data-k='{kind}' name='kpick:{kind}' "
        f"type='number' min='0' max='{kc[kind]}' value='0'> / {kc[kind]}</label>"
        for kind, label in _MX_KINDS
        if kc[kind]
    )
    pick_bar = (
        "<div class='kindbar'><b>Tạo / trộn đề theo số câu, từ câu được chọn</b>"
        + kind_inputs
        + "<button type='button' class='btn primary' id='applyKpick'>Áp dụng số câu</button></div>"
        "<p class='muted'>Điền số câu mỗi loại rồi bấm <b>Tạo đề</b> hoặc <b>Trộn đề</b>. "
        "Muốn đúng từng câu thì mở bài bên dưới, tick câu, rồi bấm tạo đề. "
        "<b>Áp dụng số câu</b> tick sẵn bấy nhiêu câu mỗi loại.</p>"
        + "".join(pick_blocks)
    )
    controls = (
        "<label class='examcopies'>Số bản trộn <input name='exam_copies' type='number' min='1' max='20' value='1'></label>"
        "<label class='examcopies'>Ghi bài <select name='exam_ruled'>"
        "<option value='0'>Không dòng kẻ</option><option value='1'>Có dòng kẻ</option></select></label>"
    )
    submits = (
        "<button class='btn green' type='submit' name='exam_action' value='create'>📝 Tạo đề</button>"
        "<button class='btn' type='submit' name='exam_action' value='shuffle'>🔀 Trộn đề</button>"
        "<button class='btn' type='submit' name='exam_action' value='print'>🖨 In đề</button>"
    )
    return (
        "<form method='post' action='/member/exam' id='examMatrix' class='exammatrix'>"
        "<input type='hidden' name='chapter' value='1'>"
        f"<input type='hidden' name='mon' value='{_esc(mon)}'>"
        f"<input type='hidden' name='lop' value='{_esc(lop)}'>"
        f"<input type='hidden' name='chuong' value='{_esc(chuong)}'>"
        "<div class='notice'>📝 <b>Ma trận cả chương</b> — mỗi dòng là một bài. Số xanh là số câu đang có, ô là số câu lấy. "
        f"Kho cả chương: <b>{total}</b> câu. "
        "Ngay dưới là <b>tạo / trộn theo số câu từ câu được chọn</b>. "
        "Bảng tiếp theo là ma trận từng bài. <b>Trộn đề</b> và <b>In đề</b> xáo câu trong từng phần, đảo A–D và a)–d).</div>"
        + "<div class='modebar'>" + controls + submits + "</div>"
        + pick_bar
        + "<div class='selectwrap'><table class='selectgrid mxone'><tr><th>Bài</th>"
        + "".join(
            "<th>"
            + html.escape(label)
            + "<div class='mxlabs'><span title='Nhận biết'>NB</span><span title='Thông hiểu'>TH</span>"
            "<span title='Vận dụng'>VD</span><span title='Vận dụng cao'>VDC</span></div></th>"
            for _kind, label in _MX_KINDS
        )
        + "</tr>"
        + "".join(body_rows)
        + "</table></div>"
        "<div id='examSum' class='notice' style='margin-top:10px'>TỔNG CHỌN: 0 câu</div>"
        + "<div class='modebar'>" + submits + f"<a class='btn' href='{_esc(back)}'>← Cả chương</a></div>"
        + "</form>"
        "<p class='muted' style='margin-top:8px'>" + html.escape(heading) + "</p>"
        "<style>.exammatrix .modebar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}"
        ".exammatrix .examcopies{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px}"
        ".exammatrix .examcopies input,.exammatrix .examcopies select{padding:6px;border:1px solid #cbd8e6;border-radius:6px;background:#fff}"
        ".exammatrix .examcopies input{width:64px;text-align:center}"
        ".exammatrix table.mxone{width:max-content}"
        ".exammatrix .mxone th,.exammatrix .mxone td{padding:3px 5px;vertical-align:middle}"
        ".exammatrix .mxname{text-align:left;font-weight:700;line-height:1.25;white-space:nowrap}"
        ".exammatrix .mxlabs,.exammatrix .mxline{display:grid;grid-template-columns:repeat(4,48px);gap:2px;justify-content:center;align-items:center}"
        ".exammatrix .mxlabs span{font-size:10px;font-weight:800;color:#334155;text-align:center}"
        ".exammatrix td.mxkind{background:#f0fdf4}"
        ".exammatrix .mxpick{display:flex;flex-direction:row;align-items:center;justify-content:center;gap:2px}"
        ".exammatrix .mxpick b{font-size:11px;line-height:1;font-weight:800;color:#166534;min-width:1.1em;text-align:right}"
        ".exammatrix .mxpick .n{width:26px;padding:1px 0;font-size:12px;font-weight:800}"
        ".exammatrix .mxpick.off{opacity:.38}"
        ".exammatrix .kindbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0;padding:10px;border:2px solid #15803d;border-radius:10px;background:#f0fdf4}"
        ".exammatrix .kindbar label{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px}"
        ".exammatrix .kindbar input{width:58px;padding:6px;border:1px solid #86efac;border-radius:6px;text-align:center}"
        ".exammatrix .chpick{margin:6px 0;border:1px solid #d7e2ee;border-radius:8px;background:#fff;padding:6px 10px}"
        ".exammatrix .chpick summary{cursor:pointer;font-weight:800}"
        ".exammatrix .qselrow{display:flex;gap:8px;align-items:flex-start;padding:4px 0;border-top:1px dashed #e5edf5;font-size:13px;line-height:1.35}"
        ".exammatrix .qselrow input{margin-top:3px}</style>"
        "<script>(function(){var f=document.getElementById('examMatrix');if(!f)return;"
        "function clamp(x){var m=Number(x.max)||0,v=Math.max(0,Math.min(m,Number(x.value)||0));x.value=v;return v;}"
        "function countAll(){var m=0,k=0;f.querySelectorAll('.n').forEach(function(x){m+=clamp(x)});f.querySelectorAll('.kpick').forEach(function(x){k+=clamp(x)});return {m:m,k:k,s:f.querySelectorAll('input[name=qsel]:checked').length};}"
        "function upd(){var c=countAll();var s=document.getElementById('examSum');if(s)s.textContent='Theo loại: '+c.k+' câu · Đã tick: '+c.s+' câu · Ma trận: '+c.m+' câu';}"
        "var apply=document.getElementById('applyKpick');if(apply)apply.addEventListener('click',function(){"
        "f.querySelectorAll('input[name=qsel]').forEach(function(x){x.checked=false});"
        "f.querySelectorAll('.kpick').forEach(function(inp){var k=inp.getAttribute('data-k');var want=clamp(inp);var boxes=f.querySelectorAll('input[name=qsel][data-k=\"'+k+'\"]');for(var i=0;i<boxes.length&&i<want;i++)boxes[i].checked=true;});"
        "upd();});"
        "f.querySelectorAll('.n,.kpick').forEach(function(x){x.addEventListener('input',upd)});"
        "f.querySelectorAll('input[name=qsel]').forEach(function(x){x.addEventListener('change',upd)});"
        "upd();"
        "f.addEventListener('submit',function(e){var c=countAll();"
        "if(c.m+c.k+c.s<=0){e.preventDefault();alert('Điền số câu theo loại, tick câu trong bài, hoặc điền ô ma trận, rồi bấm Tạo đề, Trộn đề hoặc In đề.');}});"
        "})();</script>"
    )


@app.get("/member/chapter/matrix")
def member_chapter_matrix():
    if not can_manage_bank():
        return redirect("/member/login")
    mon = str(request.args.get("mon") or "").strip()
    lop = str(request.args.get("lop") or "").strip()
    chuong = str(request.args.get("chuong") or "").strip()
    if not mon or not chuong:
        return redirect("/member")
    grid = chapter_matrix_html(mon, lop, chuong)
    back = "/member/chapter?" + _chapter_query(mon, lop, chuong)
    if not grid:
        return page(
            "Ma trận",
            "<div class='wrap'><div class='panel'><div class='body'><div class='err'>Không thấy bài trong chương này.</div>"
            f"<p><a class='btn' href='{_esc(back)}'>← Cả chương</a></p></div></div></div>",
        )
    title = " · ".join(x for x in (mon, ("Lớp " + lop) if lop else "", chuong) if x)
    body = (
        "<div class='wrap'><div class='panel'><div class='head'>📝 Tạo đề theo ma trận · "
        + html.escape(title)
        + "</div><div class='body'>"
        + grid
        + "</div></div></div>"
    )
    return page("Tạo đề theo ma trận", body)


def exam_buttons_html(admin=True):
    if not admin:
        return ""
    return (
        "<label class='examcopies' style='display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px'>"
        "Số bản trộn <input name='exam_copies' type='number' min='1' max='20' value='1' "
        "style='width:64px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center'></label>"
        "<label class='examcopies' style='display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:13px'>"
        "Ghi bài <select name='exam_ruled' style='padding:6px;border:1px solid #cbd8e6;border-radius:6px'>"
        "<option value='0'>Không dòng kẻ</option>"
        "<option value='1'>Có dòng kẻ</option>"
        "</select></label>"
        "<button class='btn green' type='submit' name='exam_action' value='create' formaction='/member/exam'>📝 Tạo đề</button>"
        "<button class='btn' type='submit' name='exam_action' value='shuffle' formaction='/member/exam'>🔀 Trộn đề</button>"
        "<button class='btn' type='submit' name='exam_action' value='print' formaction='/member/exam'>🖨 In đề</button>"
    )
