# -*- coding: utf-8 -*-
"""Gói thành viên: 1/2/3 lớp hoặc 1/2 môn. Học viên đăng ký, ADMIN duyệt/cấp."""
from __future__ import annotations

import html
import re
import unicodedata
from calendar import monthrange
from datetime import datetime, timedelta
from urllib.parse import unquote

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

DURATIONS = (
    ("3d", "3 ngày"),
    ("1m", "1 tháng"),
    ("3m", "3 tháng"),
    ("1y", "1 năm"),
)


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


def _norm_person_name(s) -> str:
    t = unicodedata.normalize("NFC", str(s or "")).casefold()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _norm_phone(s) -> str:
    d = re.sub(r"\D", "", str(s or ""))
    if d.startswith("84") and len(d) >= 11:
        d = "0" + d[2:]
    if len(d) < 9:
        return ""
    return d[-10:] if len(d) >= 10 else d


def _merge_score(m) -> tuple:
    st = package_status(m)
    typ = _norm_type(m.get("account_type"))
    return (
        1 if vip_active(m) else 0,
        1 if st == "approved" else 0,
        2 if typ == "SVIP" else (1 if typ == "VIP" else 0),
        1 if str(m.get("status", "ON")).upper() == "ON" else 0,
        1 if _norm_phone(m.get("phone")) else 0,
        1 if str(m.get("name") or "").strip() else 0,
    )


def duplicate_groups(members):
    people = [
        m for m in (members or [])
        if str(m.get("username") or "").strip() and str(m.get("username") or "").strip().casefold() != "admin"
    ]
    if len(people) < 2:
        return []
    parent = {id(m): id(m) for m in people}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(id(a)), find(id(b))
        if ra != rb:
            parent[rb] = ra

    by_name, by_phone = {}, {}
    for m in people:
        n = _norm_person_name(m.get("name"))
        if len(n) >= 6:
            by_name.setdefault(n, []).append(m)
        ph = _norm_phone(m.get("phone"))
        if ph:
            by_phone.setdefault(ph, []).append(m)
    for arr in list(by_name.values()) + list(by_phone.values()):
        if len(arr) < 2:
            continue
        for extra in arr[1:]:
            union(arr[0], extra)
    buckets = {}
    for m in people:
        buckets.setdefault(find(id(m)), []).append(m)
    groups = [sorted(g, key=_merge_score, reverse=True) for g in buckets.values() if len(g) >= 2]
    groups.sort(key=len, reverse=True)
    return groups


def merge_members(keep, extras):
    extras = [x for x in extras if x is not keep]
    if not extras:
        return keep
    aliases = list(keep.get("also_usernames") or [])
    for other in extras:
        aliases.append(str(other.get("username") or "").strip())
        aliases.extend(str(x).strip() for x in (other.get("also_usernames") or []) if x)
        if not str(keep.get("name") or "").strip() and other.get("name"):
            keep["name"] = other.get("name")
        if not _norm_phone(keep.get("phone")) and other.get("phone"):
            keep["phone"] = other.get("phone")
        og = granted_package(other)
        kg = granted_package(keep)
        if og and (not kg or _merge_score(other) > _merge_score(keep)):
            keep["package"] = dict(og)
            keep["grades"] = list(og.get("grades") or [])
            keep["subjects"] = list(og.get("subjects") or [])
            keep["account_type"] = other.get("account_type") or keep.get("account_type")
            keep["package_status"] = "approved"
        oe, ke = vip_expire_dt(other), vip_expire_dt(keep)
        if oe and (not ke or oe > ke):
            keep["vip_expires_at"] = other.get("vip_expires_at")
            keep["vip_plan"] = other.get("vip_plan") or keep.get("vip_plan")
            keep["vip_started_at"] = other.get("vip_started_at") or keep.get("vip_started_at")
        if str(other.get("status", "ON")).upper() == "ON":
            keep["status"] = "ON"
    seen = set()
    out = []
    ku = str(keep.get("username") or "").strip().casefold()
    for a in aliases:
        k = a.casefold()
        if a and k != ku and k not in seen:
            seen.add(k)
            out.append(a)
    keep["also_usernames"] = out
    return keep


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
        if kind == "lop3" and not grades:
            grades = list(GRADES)
        if len(grades) != spec["need_grades"]:
            return None, f"Gói {spec['label']}: hãy tick đúng {spec['need_grades']} lớp ở dòng Chọn lớp."
        if not subjects:
            subjects = list(SUBJECTS)
    else:
        if kind == "mon2" and not subjects:
            subjects = list(SUBJECTS)
        if len(subjects) != spec["need_subjects"]:
            return None, f"Gói {spec['label']}: hãy tick đúng {spec['need_subjects']} môn ở dòng Chọn môn."
        if not grades:
            grades = list(GRADES)
    if not grades:
        return None, "Hãy tick lớp (10, 11, 12) ở dòng Chọn lớp."
    if not subjects:
        return None, "Hãy tick môn (Toán, Vật lý) ở dòng Chọn môn."
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
        return "FREE · chưa VIP"
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


def _add_months(dt, months):
    months = int(months)
    m0 = dt.month - 1 + months
    y = dt.year + m0 // 12
    mo = m0 % 12 + 1
    d = min(dt.day, monthrange(y, mo)[1])
    return dt.replace(year=y, month=mo, day=d)


def parse_vip_dt(raw):
    s = str(raw or "").strip()
    if not s:
        return None
    s = s.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19] if fmt.endswith("%S") else s[:10], fmt)
        except ValueError:
            continue
    return None


def vip_expire_dt(m):
    if not isinstance(m, dict):
        return None
    return parse_vip_dt(m.get("vip_expires_at"))


def vip_start_dt(m):
    if not isinstance(m, dict):
        return None
    return parse_vip_dt(m.get("vip_started_at"))


def vip_active(m) -> bool:
    if not m:
        return False
    typ = _norm_type(m.get("account_type"))
    if typ == "ADMIN":
        return True
    if typ not in {"VIP", "SVIP"}:
        return False
    exp = vip_expire_dt(m)
    if not exp:
        return True
    return datetime.now() < exp


def vip_expired(m) -> bool:
    typ = _norm_type((m or {}).get("account_type"))
    if typ not in {"VIP", "SVIP"}:
        return False
    exp = vip_expire_dt(m)
    return bool(exp) and datetime.now() >= exp


def duration_from_form(form, prefix=""):
    p = f"{prefix}_" if prefix else ""
    key = str(form.get(p + "vip_duration") or form.get("vip_duration") or "").strip().lower()
    if key in dict(DURATIONS):
        return key
    return ""


def apply_vip_duration(m, key, start=None):
    key = str(key or "").strip().lower()
    if key not in dict(DURATIONS):
        key = "1m"
    start = start or datetime.now()
    end = plan_end_dt(key, start)
    m["vip_plan"] = key
    m["vip_started_at"] = start.strftime("%Y-%m-%d %H:%M:%S")
    m["vip_expires_at"] = end.strftime("%Y-%m-%d %H:%M:%S")
    return end


def plan_end_dt(key, start=None):
    key = str(key or "").strip().lower()
    start = start or datetime.now()
    if key == "3d":
        return start + timedelta(days=3)
    if key == "1m":
        return _add_months(start, 1)
    if key == "3m":
        return _add_months(start, 3)
    return _add_months(start, 12)


def format_vn_date(dt, with_time=False):
    if not dt:
        return ""
    s = dt.strftime("%d/%m/%Y")
    if with_time:
        s += dt.strftime(" lúc %H:%M")
    return s


def vip_period_text(start, end) -> str:
    a = format_vn_date(start) or "—"
    b = format_vn_date(end) or "—"
    return f"Đăng ký {a} — hết hạn {b}"


def vip_remaining_label(m) -> str:
    if not m:
        return ""
    if _norm_type(m.get("account_type")) == "ADMIN":
        return "ADMIN · không hết hạn"
    start = vip_start_dt(m)
    exp = vip_expire_dt(m)
    if _norm_type(m.get("account_type")) not in {"VIP", "SVIP"}:
        return "Chưa cấp VIP"
    if not exp:
        return "VIP chưa đặt ngày hết hạn (chọn 3 ngày / 1 tháng / 3 tháng / 1 năm rồi Lưu)"
    period = vip_period_text(start, exp)
    now = datetime.now()
    if now >= exp:
        return f"{period} · đã hết hạn, chỉ xem đề"
    delta = exp - now
    days = delta.days
    hours = delta.seconds // 3600
    mins = (delta.seconds % 3600) // 60
    if days >= 1:
        return f"{period} · còn {days} ngày {hours} giờ"
    if hours >= 1:
        return f"{period} · còn {hours} giờ {mins} phút"
    return f"{period} · còn {max(1, mins)} phút"


def duration_html(prefix="", selected="", expire_at="", started_at=""):
    selected = str(selected or "").strip().lower()
    if selected not in dict(DURATIONS):
        selected = "1m"
    p = f"{prefix}_" if prefix else ""
    name = p + "vip_duration"
    radios = [
        f"<label class='pkgchk'><input type='radio' name='{html.escape(name)}' value='{k}'{' checked' if selected==k else ''}> {html.escape(lab)}</label>"
        for k, lab in DURATIONS
    ]
    end = parse_vip_dt(expire_at) or plan_end_dt(selected)
    start = parse_vip_dt(started_at) or (datetime.now() if not parse_vip_dt(expire_at) else None)
    if not start and end:
        start = datetime.now()
    start_txt = html.escape(format_vn_date(start) or "—")
    end_txt = html.escape(format_vn_date(end) or "—")
    return (
        "<div class='pkgrow pkgdur' style='display:flex'><span>Gói · hạn dùng</span>"
        + "".join(radios)
        + "</div>"
        "<div class='pkgexp'><div class='vipdates'>"
        f"<span><span class='vipleg'>Ngày đăng ký</span><b data-vipstart>{start_txt}</b></span>"
        "<span class='vipdash'>—</span>"
        f"<span><span class='vipleg'>Ngày hết hạn</span><b data-vipexp>{end_txt}</b></span>"
        "</div><span class='muted'>Đổi 3 ngày / 1 tháng / … sẽ đổi khoảng này; bấm Lưu mới ghi.</span></div>"
    )


def apply_granted(m, pkg, approved=True, duration=None):
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
        if duration:
            apply_vip_duration(m, duration)
        elif not vip_expire_dt(m) or vip_expired(m):
            apply_vip_duration(m, m.get("vip_plan") or "1m")


def apply_request(m, pkg):
    m["requested_package"] = pkg
    m["package_status"] = "pending"
    if not m.get("account_type"):
        m["account_type"] = "FREE"


def lesson_grade(item) -> str:
    return _grade((item or {}).get("Lop") or (item or {}).get("lop") or (item or {}).get("class"))


def lesson_subject(item) -> str:
    return _subject((item or {}).get("Mon") or (item or {}).get("mon") or "")


def _norm_path(path: str) -> str:
    return unquote(str(path or "")).replace("\\", "/").strip()


def _item_from_path(path: str) -> dict:
    p = _norm_path(path)
    parts = [x for x in p.split("/") if x]
    item = {"path": p, "file": p}
    if len(parts) >= 2:
        item["Mon"] = parts[1]
    if len(parts) >= 3:
        item["Lop"] = parts[2].replace("Lớp", "").replace("Lop", "").strip() or parts[2]
    return item


def package_covers_all(pkg) -> bool:
    if not pkg:
        return False
    if pkg.get("kind") == "all":
        return True
    return set(pkg.get("grades") or []) >= set(GRADES) and set(pkg.get("subjects") or []) >= set(SUBJECTS)


def can_see_item(m, item) -> bool:
    if not m or str(m.get("status", "ON")).upper() != "ON":
        return False
    if _norm_type(m.get("account_type")) == "ADMIN":
        return True
    if not vip_active(m):
        try:
            import app as base
            level = str(base.lesson_level(str((item or {}).get("path") or (item or {}).get("file") or ""))).upper()
            return level != "VIP"
        except Exception:
            return False
    pkg = granted_package(m)
    if not pkg:
        try:
            import app as base
            level = str(base.lesson_level(str((item or {}).get("path") or (item or {}).get("file") or ""))).upper()
            return level == "FREE"
        except Exception:
            return False
    if package_covers_all(pkg):
        return True
    g = lesson_grade(item)
    s = lesson_subject(item)
    grades = set(pkg.get("grades") or [])
    subjects = set(pkg.get("subjects") or [])
    if g and grades and g not in grades:
        return False
    if s and subjects and s not in subjects:
        return False
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
    want = _norm_path(path)
    if not want:
        return False
    for item in base.index_data().get("lessons", []) or []:
        if not isinstance(item, dict):
            continue
        p = _norm_path(item.get("path") or item.get("file") or "")
        if p == want:
            return can_see_item(m, item)
    return can_see_item(m, _item_from_path(want))


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


def picker_html(prefix="", selected=None, student=True, name_package=None, duration="", expire_at="", started_at=""):
    selected = selected or {}
    kind = str(selected.get("kind") or "")
    grades = set(selected.get("grades") or [])
    subjects = set(selected.get("subjects") or [])
    if kind.startswith("lop") and not subjects:
        subjects = set(SUBJECTS)
    if kind.startswith("mon") and not grades:
        grades = set(GRADES)
    if kind == "all":
        grades = set(GRADES)
        subjects = set(SUBJECTS)
    p = f"{prefix}_" if prefix else ""
    pname = name_package or (p + "package")
    gname = p + "grades"
    sname = p + "subjects"
    kinds = STUDENT_PACKAGES if student else (STUDENT_PACKAGES + ("all",))
    radios = []
    for k in kinds:
        lab = PACKAGES[k]["label"]
        radios.append(
            f"<label class='pkgopt'><input type='radio' name='{html.escape(pname)}' value='{k}'{' checked' if kind==k else ''}> {html.escape(lab)}</label>"
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
        "<div class='pkglabel'>Phạm vi lớp / môn</div>"
        f"<div class='pkgrads'>{''.join(radios)}</div>"
        f"<div class='pkgrow pkggrades' style='display:flex'><span>Chọn lớp</span>{gboxes}</div>"
        f"<div class='pkgrow pkgsubs' style='display:flex'><span>Chọn môn</span>{sboxes}</div>"
        "<p class='pkghint muted'>Tick lớp 10/11/12 và môn Toán / Vật lý. Chọn đúng số lớp hoặc số môn.</p>"
        + (
            duration_html(
                prefix,
                duration or (selected.get("vip_plan") if isinstance(selected, dict) else ""),
                expire_at=expire_at,
                started_at=started_at,
            )
            if not student
            else ""
        )
        + "</div>"
    )


PKG_CSS = """
<style>
.pkgbox{background:#f4f9ff;border:1px solid #c5dcf3;border-radius:10px;padding:10px;margin:8px 0}
.pkglabel{font-size:11px;font-weight:900;color:#4e6a88;margin-bottom:6px}
.pkgrads{display:flex;flex-wrap:wrap;gap:6px}
.pkgopt,.pkgchk{display:inline-flex;align-items:center;gap:5px;background:#fff;border:1px solid #c9dbeb;border-radius:8px;padding:6px 9px;font-weight:800;cursor:pointer}
.pkgrow{display:flex!important;flex-wrap:wrap;gap:6px;align-items:center;margin-top:8px}
.pkgrow>span{font-size:11px;font-weight:900;color:#5b738c;min-width:108px}
.pkghint{margin:8px 0 0;font-size:11px}
.pendcard{background:#fff8e6;border:1px solid #e6c56a;border-radius:10px;padding:10px;margin:8px 0}
.pendcard b.req{color:#8a5a00}
.dupbox{background:#fff7ed;border:1px solid #fdba74;border-radius:12px;padding:10px;margin:10px 0}
.dupbox h3{margin:0 0 8px;font-size:15px;color:#9a3412}
.dupgroup{background:#fff;border:1px solid #fed7aa;border-radius:10px;padding:8px;margin:8px 0}
.dupgroup form{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:6px}
.pkgexp{margin-top:8px;font-size:14px;font-weight:800;color:#9a3412;background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:10px}
.pkgexp .vipdates{display:flex;flex-wrap:wrap;align-items:flex-end;gap:6px 16px}
.pkgexp .vipleg{display:block;font-size:11px;font-weight:800;color:#9a6b3a;margin-bottom:2px}
.pkgexp b{font-size:20px;letter-spacing:.02em;color:#9a3412}
.pkgexp .vipdash{font-size:22px;font-weight:900;color:#c2410c;padding-bottom:2px}
.pkgexp .muted{display:block;margin-top:6px;font-size:11px;font-weight:600;color:#9a6b3a}
</style>
"""

PKG_JS = """
<script>
(function(){
  function addMonths(dt, months){
    var y0=dt.getFullYear(), m0=dt.getMonth()+months;
    var y=y0+Math.floor(m0/12);
    var mo=((m0%12)+12)%12;
    var last=new Date(y, mo+1, 0).getDate();
    var d=Math.min(dt.getDate(), last);
    return new Date(y, mo, d, dt.getHours(), dt.getMinutes(), dt.getSeconds());
  }
  function endFromPlan(key){
    var s=new Date();
    if(key==='3d'){ s.setDate(s.getDate()+3); return s; }
    if(key==='1m') return addMonths(s,1);
    if(key==='3m') return addMonths(s,3);
    return addMonths(s,12);
  }
  function fmt(d){
    var dd=String(d.getDate()).padStart(2,'0');
    var mm=String(d.getMonth()+1).padStart(2,'0');
    return dd+'/'+mm+'/'+d.getFullYear();
  }
  function bind(box){
    var radios=box.querySelectorAll('.pkgdur input[type=radio]');
    var st=box.querySelector('[data-vipstart]');
    var en=box.querySelector('[data-vipexp]');
    if(!en||!radios.length) return;
    radios.forEach(function(r){
      r.addEventListener('change', function(){
        if(!r.checked) return;
        var now=new Date();
        if(st) st.textContent=fmt(now);
        en.textContent=fmt(endFromPlan(r.value));
      });
    });
  }
  document.querySelectorAll('.pkgbox').forEach(bind);
})();
</script>
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
            "approved": f"✅ Đang dùng: <b>{html.escape(package_label(granted))}</b><br>{html.escape(vip_remaining_label(m))}",
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
