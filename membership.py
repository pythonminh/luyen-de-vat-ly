# -*- coding: utf-8 -*-
"""Gói thành viên: 1/2/3 lớp hoặc 1/2 môn. Học viên đăng ký, ADMIN duyệt/cấp."""
from __future__ import annotations

import html
import re
from datetime import datetime

GRADES = ("10", "11", "12")
SUBJECTS = ("Toán", "Vật lý")

PACKAGES = {
    "lop1": {"label": "1 lớp", "need_grades": 1, "need_subjects": 0},
    "lop2": {"label": "2 lớp", "need_grades": 2, "need_subjects": 0},
    "lop3": {"label": "3 lớp", "need_grades": 3, "need_subjects": 0},
    "mon1": {"label": "1 môn", "need_grades": 0, "need_subjects": 1},
    "mon2": {"label": "2 môn", "need_grades": 0, "need_subjects": 2},
    "all": {"label": "Toàn bộ", "need_grades": 0, "need_subjects": 0},
}

STUDENT_PACKAGES = ("lop1", "lop2", "lop3", "mon1", "mon2")


def _grade(value) -> str:
    m = re.search(r"(?<!\d)(10|11|12)(?!\d)", str(value or "").upper())
    return m.group(1) if m else ""


def _subject(value) -> str:
    s = str(value or "").strip().casefold()
    s = s.replace("á", "a").replace("à", "a").replace("ả", "a").replace("ã", "a").replace("ạ", "a")
    s = s.replace("ă", "a").replace("ắ", "a").replace("ấ", "a")
    s = s.replace("ậ", "a").replace("ầ", "a")
    compact = re.sub(r"[^a-z]", "", s)
    if compact in {"toan", "toanhoc", "math"}:
        return "Toán"
    if compact in {"ly", "vatly", "vatli", "physics", "vl"}:
        return "Vật lý"
    raw = str(value or "").strip()
    if raw in SUBJECTS:
        return raw
    return ""


def _uniq_grades(values) -> list[str]:
    out = []
    for v in values or []:
        g = _grade(v)
        if g and g not in out:
            out.append(g)
    return [g for g in GRADES if g in out]


def _uniq_subjects(values) -> list[str]:
    out = []
    for v in values or []:
        s = _subject(v)
        if s and s not in out:
            out.append(s)
    return [s for s in SUBJECTS if s in out]


def _norm_type(v) -> str:
    s = str(v or "FREE").strip().upper().replace(".", "").replace("-", "")
    return {"SVIP": "SVIP", "VIP": "VIP", "FREE": "FREE", "ADMIN": "ADMIN", "MEMBER": "VIP"}.get(s, "FREE")


def parse_package(kind, grades, subjects, student=False):
    kind = str(kind or "").strip().lower()
    if student and kind == "all":
        return None, "Học viên chỉ chọn 1 lớp, 2 lớp, 3 lớp, 1 môn hoặc 2 môn."
    if kind not in PACKAGES:
        return None, "Chưa chọn gói thành viên."
    grades = _uniq_grades(grades)
    subjects = _uniq_subjects(subjects)
    spec = PACKAGES[kind]
    if kind == "all":
        return {"kind": "all", "grades": list(GRADES), "subjects": list(SUBJECTS)}, ""
    if spec["need_grades"]:
        if kind == "lop3":
            grades = list(GRADES)
        elif len(grades) != spec["need_grades"]:
            return None, f"Gói {spec['label']} cần chọn đúng {spec['need_grades']} lớp."
        subjects = list(SUBJECTS)
    else:
        if kind == "mon2":
            subjects = list(SUBJECTS)
        elif len(subjects) != spec["need_subjects"]:
            return None, f"Gói {spec['label']} cần chọn đúng {spec['need_subjects']} môn."
        grades = list(GRADES)
    return {"kind": kind, "grades": grades, "subjects": subjects}, ""


def package_from_form(form, prefix="", student=False):
    p = f"{prefix}_" if prefix else ""
    kind = form.get(p + "package") or form.get("package")
    grades = form.getlist(p + "grades") or form.getlist("grades")
    subjects = form.getlist(p + "subjects") or form.getlist("subjects")
    return parse_package(kind, grades, subjects, student=student)


def _pkg_dict(m, key="package"):
    raw = m.get(key) if isinstance(m, dict) else None
    if isinstance(raw, dict) and raw.get("kind"):
        pkg, err = parse_package(raw.get("kind"), raw.get("grades"), raw.get("subjects"), student=False)
        return pkg
    kind = str(raw or "").strip().lower()
    if kind in PACKAGES:
        pkg, err = parse_package(kind, m.get("grades") or m.get("classes"), m.get("subjects"), student=False)
        return pkg
    return None


def requested_package(m):
    if not isinstance(m, dict):
        return None
    req = m.get("requested_package")
    if isinstance(req, dict) and req.get("kind"):
        pkg, _ = parse_package(req.get("kind"), req.get("grades"), req.get("subjects"), student=True)
        return pkg
    return None


def granted_package(m):
    """Gói ADMIN đã duyệt/cấp. Tài khoản cũ VIP/SVIP được suy ra để không mất quyền."""
    if not m:
        return None
    if _norm_type(m.get("account_type")) == "ADMIN":
        return {"kind": "all", "grades": list(GRADES), "subjects": list(SUBJECTS)}
    pkg = _pkg_dict(m, "package")
    if pkg:
        return pkg
    typ = _norm_type(m.get("account_type"))
    if typ == "SVIP":
        return {"kind": "all", "grades": list(GRADES), "subjects": list(SUBJECTS)}
    if typ == "VIP":
        g = _grade(m.get("class") or m.get("grade"))
        grades = _uniq_grades(m.get("grades") or ([g] if g else []))
        if not grades:
            grades = list(GRADES)
        return {"kind": "lop1" if len(grades) == 1 else ("lop2" if len(grades) == 2 else "lop3"), "grades": grades, "subjects": list(SUBJECTS)}
    return None


def package_status(m) -> str:
    st = str((m or {}).get("package_status") or "").strip().lower()
    req = requested_package(m)
    granted = granted_package(m)
    if st == "pending" or (req and (not granted or req != granted)):
        if st != "rejected" and req:
            return "pending"
    if granted:
        return "approved"
    if st == "rejected":
        return "rejected"
    return "none"


def scope_label(m) -> str:
    st = package_status(m)
    if st == "pending":
        req = requested_package(m)
        extra = package_label(req) if req else "gói"
        return "Chờ duyệt " + extra
    pkg = granted_package(m)
    if not pkg:
        return "Chưa cấp gói"
    return package_label(pkg)


def package_label(pkg) -> str:
    if not pkg:
        return "Chưa chọn"
    kind = pkg.get("kind")
    if kind == "all":
        return "Toàn bộ 10–12 · Toán + Lý"
    if kind in {"lop1", "lop2", "lop3"}:
        return PACKAGES.get(kind, {}).get("label", "") + " " + "+".join(pkg.get("grades") or [])
    if kind in {"mon1", "mon2"}:
        return PACKAGES.get(kind, {}).get("label", "") + " " + " + ".join(pkg.get("subjects") or [])
    return PACKAGES.get(kind, {}).get("label") or str(kind)


def apply_granted(m, pkg, approved=True):
    if not pkg:
        return
    m["package"] = pkg
    m["grades"] = list(pkg.get("grades") or [])
    m["subjects"] = list(pkg.get("subjects") or [])
    m["package_status"] = "approved" if approved else str(m.get("package_status") or "pending")
    if approved:
        m["account_type"] = "VIP" if pkg.get("kind") != "all" else "SVIP"
        grades = pkg.get("grades") or []
        m["class"] = grades[0] if len(grades) == 1 else "+".join(grades)
        m["grade"] = m["class"]
        m["requested_package"] = None


def apply_request(m, pkg):
    m["requested_package"] = pkg
    m["package_status"] = "pending"
    if not m.get("account_type"):
        m["account_type"] = "FREE"


def lesson_grade(item) -> str:
    return _grade((item or {}).get("Lop") or (item or {}).get("lop") or (item or {}).get("class"))


def lesson_subject(item) -> str:
    return _subject((item or {}).get("Mon") or (item or {}).get("mon") or "")


def can_see_item(m, item) -> bool:
    if not m or str(m.get("status", "ON")).upper() != "ON":
        return False
    if _norm_type(m.get("account_type")) == "ADMIN":
        return True
    pkg = granted_package(m)
    if not pkg:
        try:
            import app as base
            level = str(base.lesson_level(str((item or {}).get("path") or (item or {}).get("file") or ""))).upper()
            return level == "FREE"
        except Exception:
            return False
    g = lesson_grade(item)
    s = lesson_subject(item)
    grades = set(pkg.get("grades") or [])
    subjects = set(pkg.get("subjects") or [])
    if g and grades and g not in grades:
        return False
    if s and subjects and s not in subjects:
        return False
    if not g and not s:
        return True
    return True


def can_access_path(m, path: str) -> bool:
    import app as base
    if getattr(base, "has_full_bank_access", lambda *_: False)(m):
        return True
    try:
        if base.admin_current():
            return True
    except Exception:
        pass
    if not m:
        return False
    for item in base.index_data().get("lessons", []) or []:
        if not isinstance(item, dict):
            continue
        p = str(item.get("path") or item.get("file") or "")
        if p == str(path):
            return can_see_item(m, item)
    return False


def allowed_paths(m) -> set[str]:
    import app as base
    out = set()
    if getattr(base, "has_full_bank_access", lambda *_: False)(m):
        return {
            str(x.get("path") or x.get("file") or "").strip()
            for x in base.index_data().get("lessons", [])
            if isinstance(x, dict) and str(x.get("path") or x.get("file") or "").strip()
        }
    for item in base.index_data().get("lessons", []) or []:
        if not isinstance(item, dict):
            continue
        p = str(item.get("path") or item.get("file") or "").strip()
        if p and can_see_item(m, item):
            out.add(p)
    return out


def picker_html(prefix="", selected=None, student=True, name_package=None):
    selected = selected or {}
    kind = str(selected.get("kind") or "")
    grades = set(selected.get("grades") or [])
    subjects = set(selected.get("subjects") or [])
    p = f"{prefix}_" if prefix else ""
    pname = name_package or (p + "package")
    gname = p + "grades"
    sname = p + "subjects"
    kinds = STUDENT_PACKAGES if student else (STUDENT_PACKAGES + ("all",))
    radios = []
    for k in kinds:
        lab = PACKAGES[k]["label"]
        radios.append(
            f"<label class='pkgopt'><input type='radio' name='{html.escape(pname)}' value='{k}'{' checked' if kind==k else ''} onchange='ldvlPkgSync(this.form)'> {html.escape(lab)}</label>"
        )
    gboxes = "".join(
        f"<label class='pkgchk'><input type='checkbox' name='{html.escape(gname)}' value='{g}'{' checked' if g in grades else ''}> Lớp {g}</label>"
        for g in GRADES
    )
    sboxes = "".join(
        f"<label class='pkgchk'><input type='checkbox' name='{html.escape(sname)}' value='{html.escape(s)}'{' checked' if s in subjects else ''}> {html.escape(s)}</label>"
        for s in SUBJECTS
    )
    return (
        "<div class='pkgbox'>"
        "<div class='pkglabel'>Gói thành viên</div>"
        f"<div class='pkgrads'>{''.join(radios)}</div>"
        f"<div class='pkgrow pkggrades'><span>Chọn lớp</span>{gboxes}</div>"
        f"<div class='pkgrow pkgsubs'><span>Chọn môn</span>{sboxes}</div>"
        "<p class='pkghint muted'>1–3 lớp: học cả Toán và Lý đúng các khối đã chọn. 1–2 môn: học môn đó cho cả 10, 11, 12.</p>"
        "</div>"
        "<script>if(!window.ldvlPkgSync){window.ldvlPkgSync=function(f){if(!f)return;"
        "var k=(f.querySelector('input[type=radio][name*=package]:checked')||{}).value||'';"
        "var g=f.querySelectorAll('.pkggrades');var s=f.querySelectorAll('.pkgsubs');"
        "var showG=k.indexOf('lop')===0;var showS=k.indexOf('mon')===0;"
        "g.forEach(function(x){x.style.display=showG||!k?'flex':'none'});"
        "s.forEach(function(x){x.style.display=showS?'flex':'none'});};"
        "document.querySelectorAll('form').forEach(function(f){if(f.querySelector('.pkgbox'))ldvlPkgSync(f)});"
        "}</script>"
    )


PKG_CSS = """
<style>
.pkgbox{background:#f4f9ff;border:1px solid #c5dcf3;border-radius:10px;padding:10px;margin:8px 0}
.pkglabel{font-size:11px;font-weight:900;color:#4e6a88;margin-bottom:6px}
.pkgrads{display:flex;flex-wrap:wrap;gap:6px}
.pkgopt,.pkgchk{display:inline-flex;align-items:center;gap:5px;background:#fff;border:1px solid #c9dbeb;border-radius:8px;padding:6px 9px;font-weight:800;cursor:pointer}
.pkgrow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:8px}
.pkgrow>span{font-size:11px;font-weight:900;color:#5b738c;min-width:70px}
.pkghint{margin:8px 0 0;font-size:11px}
.pendcard{background:#fff8e6;border:1px solid #e6c56a;border-radius:10px;padding:10px;margin:8px 0}
.pendcard b.req{color:#8a5a00}
</style>
"""


def attach_routes():
    import app as base
    from flask import redirect, request, session

    app = base.app
    if getattr(app, "_ldvl_pkg_routes", False):
        return True
    app._ldvl_pkg_routes = True

    def _save(d, msg):
        base.save_json_github(base.MEMBERS_FILE, d, "members.json", msg)

    def _find(d, username):
        want = str(username or "").strip().casefold()
        return next((x for x in d.get("members", []) if str(x.get("username") or "").strip().casefold() == want), None)

    @app.get("/member/goi")
    @app.post("/member/goi")
    def member_package_page():
        m = base.member_current()
        if not m:
            return redirect("/member/login")
        msg = ""
        if request.method == "POST":
            pkg, err = package_from_form(request.form, student=True)
            if err:
                msg = err
            else:
                d = base.members_data()
                target = _find(d, m.get("username"))
                if not target:
                    return redirect("/member/login")
                apply_request(target, pkg)
                target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    _save(d, f"Học viên {target.get('username')} đăng ký gói")
                    msg = "Đã gửi đăng ký gói. ADMIN sẽ duyệt rồi mới mở nội dung."
                    m = target
                except Exception as e:
                    msg = str(e)
        granted = granted_package(m)
        req = requested_package(m)
        st = package_status(m)
        notice = {
            "approved": f"✅ Đang dùng: <b>{html.escape(package_label(granted))}</b>",
            "pending": f"⏳ Chờ ADMIN duyệt: <b>{html.escape(package_label(req) if req else 'gói đã chọn')}</b>",
            "rejected": "Gói trước đó chưa được duyệt. Hãy chọn lại gói và gửi.",
            "none": "Chưa có gói. Chọn gói bên dưới rồi gửi để ADMIN duyệt.",
        }.get(st, "")
        err = f"<div class='err'>{html.escape(msg)}</div>" if msg and not msg.startswith("Đã gửi") else (f"<div class='notice'>{html.escape(msg)}</div>" if msg else "")
        body = (
            PKG_CSS
            + "<div class='wrap'><div class='panel' style='max-width:640px;margin:20px auto'><div class='head'>🎫 Gói thành viên</div><div class='body'>"
            + f"<div class='notice'>{notice}</div>"
            + "<form method='post'>"
            + picker_html(selected=req or granted, student=True)
            + "<button class='btn primary' type='submit'>📨 Gửi đăng ký gói</button> <a class='btn' href='/member'>← Mục lục</a>"
            + err
            + "</form><p class='muted'>Đăng ký dùng: liên hệ thầy Minh 0357991010 (Zalo) nếu cần duyệt nhanh.</p></div></div></div>"
        )
        return base.page("Gói thành viên", body)

    return True
