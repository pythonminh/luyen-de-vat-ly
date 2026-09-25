# -*- coding: utf-8 -*-
"""ADMIN: tạo đề / in đề / trộn đề với số câu tùy chọn."""
from __future__ import annotations

import html
import random
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

from flask import redirect, request, session

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
        qs = parse_questions(tex)
    return qs


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
    ids = []
    for raw in (form.getlist("qid") if hasattr(form, "getlist") else []):
        try:
            i = int(raw)
        except (TypeError, ValueError):
            continue
        if i in valid and i not in ids:
            ids.append(i)
    return ids


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
    if max(_opt_span(o.get("text") or "") for o in opts) <= 36:
        return "grid2"
    return "stack"


def _rules_html(kind):
    n = 6 if kind == "TL" else 4
    return f"<div class='exrules' style='height:{n * 1.15:.2f}em' aria-hidden='true'></div>"


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
            lab = "ABCD"[i] if i < 4 else str(i + 1)
            mark = ""
            if show_key:
                mark = " <b class='exmark'>" + ("Đúng" if s.get("correct") else "Sai") + "</b>"
            bits.append(
                f"<div class='exopt'><span class='exlab'>{lab}.</span> "
                f"<span class='exoptxt'>{html_question(s.get('text') or '', src)}{mark}</span></div>"
            )
        body = "<div class='exopts stack'>" + "".join(bits) + "</div>"
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
        f"<article class='exq'><div class='exhead'><b>Câu {seq}.</b></div>"
        f"<div class='exstem'>{stem}</div>{body}</article>"
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
    seq = 0
    key_rows = []
    for kind in KIND_ORDER:
        arr = groups.get(kind) or []
        if not arr:
            continue
        parts.append(f"<h3 class='expart'>{html.escape(KIND_LABEL[kind])}</h3>")
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
    key = (
        f"<section class='exanswer'><h3>ĐÁP ÁN · Mã đề {code}</h3>"
        f"<div class='exkgrid'>{''.join(key_rows)}</div></section>"
    )
    return "<section class='excopy'>" + "".join(parts) + (key if show_key else "") + "</section>", key


def exam_css():
    return """
<style>
.examwrap{max-width:980px;margin:auto}
.exambar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px;padding:10px;border:1px solid #d7e2ee;border-radius:10px;background:#f8fbff}
.exambar label{font-weight:800;font-size:13px;display:inline-flex;align-items:center;gap:6px}
.exambar input[type=number]{width:64px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}
.exambar select{padding:6px;border:1px solid #cbd8e6;border-radius:6px;background:#fff}
.exambar .muted{font-size:12px;font-weight:700;color:#64748b}
.exampaper{background:#fff;border:1px solid #d7e2ee;border-radius:12px;padding:18px 22px;font-family:'Times New Roman',Times,serif;font-size:16px;line-height:1.55;color:#111}
.excopy{break-after:page;page-break-after:always}
.excopy:last-child{break-after:auto;page-break-after:auto}
.exheadblock{display:grid;grid-template-columns:1fr 1.4fr 1fr;gap:10px;align-items:start;border-bottom:2px solid #111;padding-bottom:10px;margin-bottom:12px}
.exschool,.exmeta{font-size:13px}.extitle{text-align:center;font-size:18px}
.exnote{margin:8px 0 14px}
.expart{margin:18px 0 8px;font-size:15px;border-bottom:1px solid #bbb;padding-bottom:4px}
.exq{margin:0 0 14px;break-inside:avoid;page-break-inside:avoid}
.exstem{margin:4px 0 8px}
.exopts{display:grid;gap:3px 16px;padding-left:8px}
.exopts.stack{grid-template-columns:1fr}
.exopts.grid2{grid-template-columns:1fr 1fr}
.exopt{display:flex;gap:6px;align-items:flex-start;min-width:0}
.exoptxt{min-width:0}
.exrules{margin:8px 0 2px;background-image:repeating-linear-gradient(to bottom,transparent,transparent calc(1.15em - 1px),#334155 calc(1.15em - 1px),#334155 1.15em);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.exopt.ok{background:#e8f8ee;border-radius:6px;padding:2px 6px}
.exlab{font-weight:700;min-width:1.4em}
.exblank{margin:8px 0;color:#444}
.exkeyline{margin-top:8px;padding:8px;border:1px dashed #7dd3fc;border-radius:8px;background:#f0f9ff;font-size:14px}
.exanswer{margin-top:18px;padding-top:12px;border-top:2px solid #111}
.exkgrid{display:flex;flex-wrap:wrap;gap:8px 16px}
.exk{min-width:6.5rem}
@media print{
  .top,.nav,.drawer,.exambar,.subnav,.regline,.navtoggle,.clock,.whobar{display:none!important}
  body{background:#fff}
  .wrap,.examwrap{max-width:none;margin:0;padding:0}
  .exampaper{border:0;border-radius:0;padding:0}
  .excopy{page-break-after:always}
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
        qs = load_qs(path)
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
    back = "/member/select?path=" + urllib.parse.quote(path, safe="")
    dang = str(exam.get("dang") or "")
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
        + "<span class='muted'>Đáp án ngắn xếp 2 cột; đáp án dài xếp 4 dòng.</span>"
        "<button class='btn' name='exam_action' value='shuffle'>🔀 Trộn đề</button>"
        "<button class='btn primary' name='exam_action' value='print' formaction='/member/exam/print'>🖨 In đề</button>"
        f"<button class='btn' name='exam_action' value='key' formaction='/member/exam/key'>{html.escape(key_lab)}</button>"
        "<button class='btn' name='exam_action' value='practice'>▶ Làm bài với đề này</button>"
        f"<a class='btn' href='{_esc(back)}'>← Chọn lại số câu</a>"
        "</form>"
    )
    print_js = (
        "<script>window.addEventListener('load',function(){if(window.ldvlTypeset)ldvlTypeset(document.body);"
        + ("setTimeout(function(){window.print()},600);" if auto_print else "")
        + "})</script>"
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


def _save_exam(path, qs, ids, copies_n, shuffle, dang="", show_key=None, ruled=None):
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
        "title": lesson_title(path),
        "copies": copies,
        "show_key": bool(session.get("exam", {}).get("show_key") if show_key is None else show_key),
        "ruled": bool(session.get("exam", {}).get("ruled") if ruled is None else ruled),
        "base_ids": list(ids),
    }
    session["exam"] = exam
    session.modified = True
    return exam


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
    if action == "practice":
        exam = session.get("exam") or {}
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
            practice_ids=ids,
            practice_pos=0,
            practice_right=0,
            practice_streak=0,
            practice_best=0,
            practice_done=[],
            practice_ai=True,
        )
        return redirect("/member/practice")

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
        if p and ids:
            try:
                qs = load_qs(p)
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
                )
            return render_exam(auto_print=auto_print)

    if not path or not ids or qs is None:
        if (session.get("exam") or {}).get("copies"):
            return render_exam(auto_print=auto_print)
        return _redirect_select(path, dang) if path else redirect("/member")
    _save_exam(path, qs, ids, copies_n, shuffle=shuffle or action == "shuffle", dang=dang, ruled=ruled)
    return render_exam(auto_print=auto_print)


@app.route("/member/exam", methods=["GET", "POST"])
def member_exam():
    if request.method == "GET":
        return render_exam(auto_print=False)
    action = (request.form.get("exam_action") or "").strip().lower()
    return build_from_request(shuffle=(action == "shuffle"), auto_print=(action == "print"))


@app.route("/member/exam/print", methods=["GET", "POST"])
def member_exam_print():
    if request.method == "POST":
        return build_from_request(shuffle=False, auto_print=True)
    return render_exam(auto_print=True)


@app.post("/member/exam/key")
def member_exam_key():
    return build_from_request()


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
