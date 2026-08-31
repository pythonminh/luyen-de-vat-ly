# -*- coding: utf-8 -*-
"""Safe GitHub question editor.

Designed to avoid embedding JavaScript object literals in Jinja templates.
Uses simple server-rendered HTML forms so /github/questions always opens.
"""
from __future__ import annotations

import base64
import html
import re
from urllib.parse import quote

from flask import Blueprint, request, redirect, url_for, session, render_template_string
from app import app

bp = Blueprint("github_safe_editor", __name__)


def guard():
    if not session.get("mahs"):
        return redirect(url_for("login", next=request.full_path.rstrip("?")))
    try:
        from app import is_admin
        if not is_admin():
            return ("<h3>403 — Chỉ ADMIN được dùng trình biên tập GitHub.</h3>", 403)
    except Exception:
        pass
    return None


def split_tex(text: str):
    pat = re.compile(r"\\begin\s*\{\s*ex\s*\}[\\s\\S]*?\\end\s*\{\s*ex\s*\}", re.I)
    ms = list(pat.finditer(text or ""))
    if not ms:
        return text or "", [], ""
    return text[:ms[0].start()], [m.group(0) for m in ms], text[ms[-1].end():]


def meta(block: str):
    def g(pattern):
        m = re.search(pattern, block or "", re.I)
        return m.group(1).strip() if m else ""
    if re.search(r"\\choiceTF\b", block, re.I):
        kind = "B — Đúng / Sai"
    elif re.search(r"\\shortans\b", block, re.I):
        kind = "C — Trả lời ngắn"
    elif re.search(r"\\choice\b", block, re.I):
        kind = "A — Trắc nghiệm"
    else:
        kind = "D — Tự luận"
    m = re.search(r"\\begin\s*\{ex\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{ex\})", block, re.S | re.I)
    title = ""
    if m:
        title = re.sub(r"%[^\r\n]*", "", m.group(1))
        title = re.sub(r"\\dangbt\s*\{[^{}]*\}", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()
    return {
        "id": g(r"%\s*ID\s*:\s*([^\r\n]+)"),
        "level": g(r"%\s*Mức\s*:\s*([^\r\n]+)"),
        "dang": g(r"\\dangbt\s*\{([^{}]*)\}"),
        "kind": kind,
        "title": title[:180],
    }


def gh(path: str, method="GET", body=None):
    import github_question_editor as qe
    return qe.gh(path, method, body)


def repo_parts():
    import github_question_editor as qe
    return qe.repo()


def fetch(path: str, branch: str):
    import github_question_editor as qe
    return qe.fetch_file(path, branch)


def update_meta(block: str, qid: str, level: str, dang: str):
    b = re.sub(r"%\s*ID\s*:[^\r\n]*\r?\n?", "", block, count=1, flags=re.I)
    b = re.sub(r"%\s*Mức\s*:[^\r\n]*\r?\n?", "", b, count=1, flags=re.I)
    b = re.sub(r"\\dangbt\s*\{[^{}]*\}\s*", "", b, count=1, flags=re.I)
    m = re.search(r"(\\begin\s*\{\s*ex\s*\})", b, re.I)
    if not m:
        return b
    lines = []
    if qid:
        lines.append("% ID: " + qid)
    if level:
        lines.append("% Mức: " + level)
    if lines:
        b = b[:m.end()] + "\n" + "\n".join(lines) + "\n" + b[m.end():]
    if dang:
        b = b[:m.start()] + "\\dangbt{" + dang + "}\n" + b[m.start():]
    return b


STYLE = r"""
<style>
body{margin:0;background:#f4f7fb;color:#19324d;font-family:Arial,sans-serif}.wrap{max-width:1450px;margin:14px auto;padding:0 12px}.top,.card{background:#fff;border:1px solid #d8e1eb;border-radius:12px;box-shadow:0 2px 10px rgba(20,50,80,.05)}.top{padding:13px 15px;margin-bottom:10px}.title{font-size:22px;font-weight:800}.path{font-size:12px;color:#64748b;margin-top:4px;word-break:break-all}.bar{display:flex;gap:7px;flex-wrap:wrap;margin:9px 0}.btn{display:inline-block;padding:8px 11px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;color:#17558f;text-decoration:none;font-weight:700;font-size:12px}.green{background:#188038;color:#fff;border-color:#188038}.blue{background:#1769d1;color:#fff;border-color:#1769d1}.layout{display:grid;grid-template-columns:340px 1fr;gap:10px}.list{padding:10px;max-height:calc(100vh - 190px);overflow:auto}.search{width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px;box-sizing:border-box;margin-bottom:8px}.q{display:block;text-decoration:none;color:#173b63;border:1px solid #dfe6ee;border-radius:8px;padding:8px;margin:5px 0}.q:hover{background:#f5f9ff}.q.active{background:#eaf3ff;border-color:#7eb1eb}.num{font-weight:800;color:#1557a6}.small{font-size:11px;color:#64748b;line-height:1.35;margin-top:3px}.badge{display:inline-block;padding:2px 7px;border-radius:999px;background:#edf4ff;color:#1557a6;font-size:10px;font-weight:700;margin-left:3px}.editor{padding:14px}.meta{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}.field label{display:block;font-size:11px;font-weight:800;color:#475569;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px;box-sizing:border-box}.code{width:100%;min-height:560px;padding:12px;border:1px solid #bbc9d8;border-radius:9px;box-sizing:border-box;font:13px/1.55 Consolas,monospace;resize:vertical}.status{padding:9px 10px;border-radius:8px;margin:8px 0;font-size:12px}.ok{background:#eaf8ef;border:1px solid #a7d8b5;color:#166534}.err{background:#fff0f0;border:1px solid #efb1b1;color:#b91c1c}@media(max-width:850px){.layout{grid-template-columns:1fr}.list{max-height:350px}.meta{grid-template-columns:1fr}}
</style>
"""

PAGE = STYLE + r"""
<div class="wrap">
<div class="top"><div class="title">📝 Biên tập câu hỏi — GitHub</div><div class="path">{{ path }}</div></div>
<div class="bar"><a class="btn" href="{{ back_url }}">← Quản lý ngân hàng</a><a class="btn" href="{{ home_url }}">🏠 Ứng dụng</a><a class="btn blue" href="/ra-de">📝 Ra đề</a><a class="btn" href="{{ prev_url }}">← Câu trước</a><a class="btn" href="{{ next_url }}">Câu sau →</a></div>
{% if msg %}<div class="status ok">{{ msg }}</div>{% endif %}{% if error %}<div class="status err">{{ error }}</div>{% endif %}
<div class="layout">
<div class="card list"><input class="search" placeholder="Tìm câu bằng Ctrl+F">{% for q in questions %}<a class="q{% if q.n==selected %} active{% endif %}" href="{{ q.url }}"><div><span class="num">Câu {{ q.n }}</span>{% if q.id %}<span class="badge">{{ q.id }}</span>{% endif %}</div><div>{{ q.title or '(chưa đọc được nội dung)' }}</div><div class="small">{{ q.kind }}{% if q.level %} · {{ q.level }}{% endif %}{% if q.dang %} · {{ q.dang }}{% endif %}</div></a>{% endfor %}</div>
<div class="card editor"><h2 style="margin:0">Câu {{ selected }}</h2><div style="font-size:12px;color:#64748b">Sửa riêng câu này. LaTeX, TikZ/hình và lời giải của câu được giữ nguyên trong mã.</div>
<form method="post" action="{{ save_url }}"><input type="hidden" name="n" value="{{ selected }}"><input type="hidden" name="sha" value="{{ sha }}"><div class="meta">
<div class="field"><label>Loại câu</label><input value="{{ meta.kind }}" disabled></div>
<div class="field"><label>Mức độ</label><select name="level"><option value="">—</option><option value="NB" {% if meta.level=='NB' %}selected{% endif %}>NB — Nhận biết</option><option value="TH" {% if meta.level=='TH' %}selected{% endif %}>TH — Thông hiểu</option><option value="VD" {% if meta.level=='VD' %}selected{% endif %}>VD — Vận dụng</option><option value="VDC" {% if meta.level=='VDC' %}selected{% endif %}>VDC — Vận dụng cao</option></select></div>
<div class="field"><label>ID</label><input name="qid" value="{{ meta.id }}"></div><div class="field"><label>Dạng bài tập</label><input name="dang" value="{{ meta.dang }}"></div></div>
<div class="field"><label>Mã LaTeX của Câu {{ selected }}</label><textarea class="code" name="content" spellcheck="false">{{ block }}</textarea></div>
<div class="bar"><button class="btn green" type="submit">💾 Lưu câu lên GitHub</button></div></form>
</div></div></div>
"""


@bp.before_request
def redirect_legacy_questions():
    if request.path == "/github/questions":
        return redirect(url_for("github_safe_editor.editor", **request.args))
    return None


@bp.route("/github/questions-safe", methods=["GET", "POST"])
def editor():
    guard_result = guard()
    if guard_result:
        return guard_result
    path = request.values.get("path", "").strip("/")
    branch = request.values.get("branch", "main")
    if not path.startswith("ngan-hang/") or not path.lower().endswith(".tex"):
        return ("<h3>Đường dẫn ngân hàng không hợp lệ.</h3>", 400)
    try:
        d, full = fetch(path, branch)
        head, blocks, tail = split_tex(full)
        if not blocks:
            raise RuntimeError("File không có block \\begin{ex}...\\end{ex}.")

        selected = max(1, min(int(request.values.get("n", "1")), len(blocks)))

        if request.method == "POST":
            idx = selected - 1
            blocks[idx] = update_meta(
                request.form.get("content", blocks[idx]),
                request.form.get("qid", "").strip(),
                request.form.get("level", "").strip(),
                request.form.get("dang", "").strip(),
            )
            content = head + "\n\n".join(blocks) + tail
            owner, name = repo_parts()
            base = f"/repos/{owner}/{name}/contents/{quote(path, safe='/')}"
            old = gh(base + "?ref=" + quote(branch))
            current_sha = old.get("sha", "")
            if request.form.get("sha", "") and request.form.get("sha") != current_sha:
                return redirect(url_for("github_safe_editor.editor", branch=branch, path=path, n=selected, error="File đã thay đổi trên GitHub. Hãy tải lại rồi lưu lại trên bản mới nhất."))
            result = gh(base, "PUT", {"message": f"ADMIN cập nhật Câu {selected} · {path}", "content": base64.b64encode(content.encode("utf-8")).decode("ascii"), "sha": current_sha, "branch": branch})
            commit = result.get("commit", {}).get("sha", "")[:12]
            return redirect(url_for("github_safe_editor.editor", branch=branch, path=path, n=selected, msg=f"✅ Đã lưu Câu {selected} lên GitHub · commit {commit}"))

        qs = []
        for i, b in enumerate(blocks, 1):
            mm = meta(b)
            mm.update({"n": i, "url": url_for("github_safe_editor.editor", branch=branch, path=path, n=i)})
            qs.append(mm)
        mm = meta(blocks[selected - 1])
        prev_url = url_for("github_safe_editor.editor", branch=branch, path=path, n=max(1, selected - 1))
        next_url = url_for("github_safe_editor.editor", branch=branch, path=path, n=min(len(blocks), selected + 1))
        return render_template_string(PAGE, path=path, branch=branch, sha=d.get("sha", ""), selected=selected, questions=qs, meta=mm, block=blocks[selected - 1], msg=request.args.get("msg", ""), error=request.args.get("error", ""), save_url=url_for("github_safe_editor.editor", branch=branch, path=path, n=selected), prev_url=prev_url, next_url=next_url, back_url=url_for("github_manager_ui.manager"), home_url=url_for("home"))
    except Exception as e:
        return "<h3>Lỗi mở trình biên tập</h3><pre>" + html.escape(str(e)) + "</pre>", 500


app.register_blueprint(bp)
