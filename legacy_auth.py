# -*- coding: utf-8 -*-
"""Legacy password compatibility layer.

Keeps passwords from the old member sheet working after migration to
members.json/SHA-256. Only SHA-256 hashes are stored here.
"""
from __future__ import annotations

import hashlib
from flask import redirect, request, session
import app as base
import admin_overrides as admin

# SHA-256 hashes only; no plaintext passwords are stored in source control.
LEGACY = {
    "Duong0811": "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4",
    "Khang1234": "a237b5bfa24c61969a2e37e64881077f6b9ddc17494781b8d420f83f425af49e",
    "Hung1234": "3de59c5be18b41226d6aeddd11bab5412e683e29d6374e86b77fe0318d025e04",
    "Phat1234": "e7ae7fc94d511c59da1c2b5424d22e702b23573fbc242cb1a2b40c4f02fc7907",
    "Lam123456": "131985ba950d75367b309ca31970190c3107bf3675bab562b0f9302bfbedaa6d",
    "Thinh123456": "1d71fbd63effc7bfd3080eeb03fb290d684f5213bdb2623f5a6567768096dcd6",
    "Nhan12345": "9296e47940ad245bd7f0e385fd87d564bad674677f83a818329f5d4d487841bf",
    "Huy123": "f6f1bf7196a6d50dc890315517465f2e703101a0215e0b8b0d8ff4344ecc77a2",
    "GHung123": "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4",
    "HNam1110": "e4fbbff8510dbe02d4f1edfb987d858bfbfae5dd2b364369dc543d050c631435",
    "TLam1406": "5994471abb01112afcc18159f6cc74b4f511b9989982a734458604190b7c0a2f8",
    "TKhang2004": "34d128f5b3dede622e107438fbefabdf0519ebab21ac7b6f2075f974d09ce524",
    "PKhang2008": "5570b8fffb53088e058bb8676e9ff407906055343b2aeb12877b68e971f2bedd",
    "Tin123456": "a1370551469cf4296733ae78695ed60bff1d1e40ac6d8e55cdaf1960dc765d46",
    "Anh1224": "aac13c7a011ea4121cf4e3e22a87bce276cdcc0bc44d7e82ca55c68386400459",
    "HBinh1234": "7612800a586ff9341f8c928b1b7aab540de8fdaea56c4ee656a46d2a94a62ef6",
    "Long1234": "9ef6cd2cb09116d7d9a05bf159158974c1789989982a734458604190b7c0a2f8",
    "ADMIN0": "4f9f10b304cfe9b2b11fcb1387f694e18f08ea358c7e9f567434d3ad6cbd7fc4",
    "ADMIN1": "e0bc60c82713f64ef8a57c0c40d02ce24fd0141d5cc3086259c19b1e62a62bea",
    "admin": "91b4d142823f7d20c5f08df69122de43f35f057a988d9619f6d3138485c9a203",
    "ThayHieu": "5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5",
    "MinhBao": "ec351e24af73a8d6f9c6ac57fa77be9f24ae014b24a259a6ad708fca1b6605ab",
}


def _hash(password: str) -> str:
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()


def _legacy_member(username: str, password: str):
    if LEGACY.get(username) != _hash(password):
        return None
    for m in base.members_data().get("members", []):
        if str(m.get("username", "")) == username and str(m.get("status", "ON")).upper() == "ON":
            return m
    return None


_original_member_login = base.app.view_functions.get("member_login")


def _member_login_legacy(*args, **kwargs):
    if request.method == "POST" and (request.form.get("action") or "login").strip().lower() == "login":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        m = _legacy_member(username, password)
        if m:
            session.clear()
            session.update(role="member", username=username, name=str(m.get("name") or username))
            session.permanent = request.form.get("remember") == "on"
            return redirect("/member")
    return _original_member_login(*args, **kwargs) if _original_member_login else redirect("/member/login")


if _original_member_login:
    base.app.view_functions["member_login"] = _member_login_legacy


_original_admin_record = admin._admin_record


def _admin_record_legacy(d=None):
    found = _original_admin_record(d)
    if found:
        return found
    d = d or admin._members()
    row = {
        "username": "admin",
        "name": "Quản trị viên",
        "class": "",
        "account_type": "ADMIN",
        "status": "ON",
        "password_sha256": LEGACY["admin"],
    }
    d.setdefault("members", []).append(row)
    return row


admin._admin_record = _admin_record_legacy


def _admin_login_legacy():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        h = _hash(password)
        d = admin._members()
        a = _original_admin_record(d)
        normalized = username.casefold()
        if a and str(a.get("status", "ON")).upper() == "ON" and h == str(a.get("password_sha256", "")) and normalized in {"admin", "admin0", "admin1"}:
            session.clear()
            session.update(role="admin", username="ADMIN", name="ADMIN")
            session.permanent = request.form.get("remember") == "on"
            return redirect("/admin/members")
        key = username if username in {"ADMIN0", "ADMIN1", "admin"} else ("admin" if normalized == "admin" else "")
        if key and LEGACY.get(key) == h:
            session.clear()
            session.update(role="admin", username="ADMIN", name="ADMIN")
            session.permanent = request.form.get("remember") == "on"
            return redirect("/admin/members")
        return admin._admin_login_page("Sai tài khoản hoặc mật khẩu ADMIN.")
    return admin._admin_login_page("")


base.app.view_functions["admin_login"] = _admin_login_legacy
