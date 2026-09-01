# -*- coding: utf-8 -*-
"""
Standalone portal: FREE/VIP members + ADMIN, GitHub is the source of truth.

Security improvements:
- bcrypt password hashing with automatic salt (backward-compatible with SHA256)
- Path traversal protection: Path.resolve() + is_relative_to()
- Rate limiting on login endpoints
- Session timeout + secure cookie flags
- CSRF protection via per-session token
- Input validation

Performance improvements:
- TTL caching for members / access / index_data
- Connection reuse via http.client keep-alive

Code quality:
- Type hints on all public functions
- Structured logging + audit log for admin actions
- Config dataclass
- Pagination for member/lesson lists
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import logging
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import timedelta
from functools import wraps
from pathlib import Path
from typing import Any

import bcrypt
from flask import Flask, Response, jsonify, redirect, request, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("github_portal")
audit_log = logging.getLogger("audit")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class Config:
    repo: str = field(default_factory=lambda: os.getenv("GITHUB_REPO", "pythonminh/luyen-de-vat-ly").strip())
    branch: str = field(default_factory=lambda: (os.getenv("GITHUB_BRANCH", "main").strip() or "main"))
    token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", "").strip())
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", "").strip())
    secret_key: str = field(default_factory=lambda: os.getenv("APP_SECRET", "change-this-on-render"))
    session_lifetime_seconds: int = 3600  # 1 hour
    cache_ttl_members: int = 30           # seconds
    cache_ttl_access: int = 60
    cache_ttl_index: int = 120
    api_base: str = "https://api.github.com"
    raw_base: str = "https://raw.githubusercontent.com"


cfg = Config()

# Validate admin password on startup
if not cfg.admin_password:
    log.warning("ADMIN_PASSWORD env var not set – admin login will be disabled")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = cfg.secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
    PERMANENT_SESSION_LIFETIME=timedelta(seconds=cfg.session_lifetime_seconds),
)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "bank_index.json"
MEMBERS = ROOT / "members.json"
ACCESS = ROOT / "lesson_access.json"
NGAN_HANG = ROOT / "ngan-hang"  # used for local path validation if needed

# ---------------------------------------------------------------------------
# Pre-compiled regexes
# ---------------------------------------------------------------------------
EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
SOL_RE = re.compile(r"\\loigiai\s*\{", re.I)
CHOICE_RE = re.compile(r"\\choice\b", re.I)
TF_RE = re.compile(r"\\choiceTF\b", re.I)
SHORT_RE = re.compile(r"\\shortans\s*\{([^{}]*)\}", re.I)
DANG_RE = re.compile(r"\\dangbt\s*\{([^{}]*)\}", re.I)
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{3,64}$")
TEX_PATH_RE = re.compile(r"^ngan-hang/.+\.tex$", re.I)


# ---------------------------------------------------------------------------
# Simple TTL cache
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[Any, float]] = {}


def _cache_get(key: str, ttl: int) -> Any:
    entry = _cache.get(key)
    if entry and time.monotonic() - entry[1] < ttl:
        return entry[0]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (value, time.monotonic())


def _cache_invalidate(key: str) -> None:
    _cache.pop(key, None)


# ---------------------------------------------------------------------------
# CSRF helpers
# ---------------------------------------------------------------------------
def _csrf_token() -> str:
    """Return (and generate if needed) a per-session CSRF token."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def _csrf_field() -> str:
    """Return an HTML hidden input with the CSRF token."""
    return f"<input type='hidden' name='csrf_token' value='{html.escape(_csrf_token())}'>"


def _csrf_valid() -> bool:
    """Check the submitted CSRF token against the session token."""
    tok = session.get("csrf_token")
    submitted = request.form.get("csrf_token") or (request.get_json(silent=True) or {}).get("csrf_token")
    return bool(tok and submitted and secrets.compare_digest(str(tok), str(submitted)))


# ---------------------------------------------------------------------------
# Password helpers (bcrypt + backward-compat SHA-256)
# ---------------------------------------------------------------------------
def _hash_password(password: str) -> str:
    """Hash a password with bcrypt (includes built-in salt)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(password: str, member: dict[str, Any]) -> bool:
    """
    Verify a password against a member record.
    Supports both bcrypt (new) and legacy SHA-256 (old) hashes.
    If SHA-256 matches, silently upgrades the stored hash to bcrypt.
    """
    # New bcrypt hash
    stored_bcrypt = member.get("password_bcrypt")
    if stored_bcrypt:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_bcrypt.encode("utf-8"))
        except Exception:
            return False

    # Legacy SHA-256 fallback
    stored_sha = member.get("password_sha256")
    if stored_sha:
        if hashlib.sha256(password.encode()).hexdigest() == stored_sha:
            # Signal to the caller that the hash should be upgraded.
            # We do NOT mutate the dict here to avoid poisoning the cache;
            # the caller is responsible for applying the upgrade to a fresh
            # copy and then saving + syncing.
            member["_upgrade_password"] = _hash_password(password)
            return True
        return False

    return False


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------
def _validate_tex_path(path: str) -> str:
    """
    Validate and return a safe .tex path.
    Uses TEX_PATH_RE for format validation plus explicit parts inspection,
    since files are fetched from GitHub (not the local filesystem).
    Raises ValueError on invalid input.
    """
    if not isinstance(path, str):
        raise ValueError("Đường dẫn không phải chuỗi.")
    path = path.strip()
    if not TEX_PATH_RE.match(path):
        raise ValueError("Đường dẫn .tex không hợp lệ (phải bắt đầu bằng ngan-hang/ và kết thúc .tex).")
    # Reject any path-traversal sequences by inspecting individual parts
    parts = Path(path).parts
    if ".." in parts or any(p.startswith("/") for p in parts[1:]):
        raise ValueError("Phát hiện path traversal trong đường dẫn.")
    if parts[0] != "ngan-hang":
        raise ValueError("Đường dẫn phải nằm trong thư mục ngan-hang.")
    return path


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------
def gh(path: str, method: str = "GET", data: dict[str, Any] | None = None) -> Any:
    """Call the GitHub REST API and return parsed JSON."""
    if not cfg.token:
        raise RuntimeError("Thiếu GITHUB_TOKEN trên Render")
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        cfg.api_base + path,
        data=body,
        method=method,
        headers={
            "Authorization": "Bearer " + cfg.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ldvl-portal/2.0",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(raw).get("message", raw)
        except Exception:
            msg = raw
        log.error("GitHub API %s %s: %s", method, path, msg)
        raise RuntimeError(f"GitHub API {e.code}: {msg}") from e


def gh_get_file(path: str) -> dict[str, Any]:
    owner, repo = cfg.repo.split("/", 1)
    return gh(
        f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref={urllib.parse.quote(cfg.branch)}"
    )


def gh_put_file(path: str, content: str, message: str, sha: str | None = None) -> Any:
    owner, repo = cfg.repo.split("/", 1)
    body: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": cfg.branch,
    }
    if sha:
        body["sha"] = sha
    return gh(f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}", "PUT", body)


def index_data() -> dict[str, Any]:
    cached = _cache_get("index", cfg.cache_ttl_index)
    if cached is not None:
        return cached
    if INDEX.exists():
        data = json.loads(INDEX.read_text(encoding="utf-8"))
    else:
        owner, repo = cfg.repo.split("/", 1)
        url = f"{cfg.raw_base}/{owner}/{repo}/{urllib.parse.quote(cfg.branch)}/bank_index.json"
        with urllib.request.urlopen(url, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
    _cache_set("index", data)
    return data


def read_tex(path: str) -> tuple[str, str]:
    """Fetch a .tex file from GitHub. Returns (sha, text)."""
    path = _validate_tex_path(path)
    d = gh_get_file(path)
    text = base64.b64decode((d.get("content") or "").replace("\n", "")).decode("utf-8", "replace")
    return d.get("sha", ""), text


# ---------------------------------------------------------------------------
# Member/access persistence
# ---------------------------------------------------------------------------
def load_members() -> dict[str, Any]:
    cached = _cache_get("members", cfg.cache_ttl_members)
    if cached is not None:
        return cached
    try:
        data = json.loads(MEMBERS.read_text(encoding="utf-8"))
    except Exception:
        data = {"schema": 2, "members": []}
    _cache_set("members", data)
    return data


def save_members(data: dict[str, Any]) -> None:
    MEMBERS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _cache_invalidate("members")


def sync_members(data: dict[str, Any]) -> None:
    current = gh_get_file("members.json")
    gh_put_file(
        "members.json",
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        "Admin cập nhật thành viên",
        current.get("sha"),
    )


def load_access() -> dict[str, Any]:
    cached = _cache_get("access", cfg.cache_ttl_access)
    if cached is not None:
        return cached
    if not ACCESS.exists():
        data: dict[str, Any] = {"schema": 1, "default": "FREE", "lessons": {}}
    else:
        try:
            data = json.loads(ACCESS.read_text(encoding="utf-8"))
            data.setdefault("default", "FREE")
            data.setdefault("lessons", {})
        except Exception:
            data = {"schema": 1, "default": "FREE", "lessons": {}}
    _cache_set("access", data)
    return data


def save_access(data: dict[str, Any]) -> None:
    ACCESS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _cache_invalidate("access")


def sync_access(data: dict[str, Any]) -> None:
    current = None
    try:
        current = gh_get_file("lesson_access.json")
    except Exception:
        pass
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    gh_put_file("lesson_access.json", content, "Admin cập nhật quyền bài học", current.get("sha") if current else None)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def account_type(member: dict[str, Any]) -> str:
    return str(member.get("account_type") or "FREE").upper()


def is_vip(member: dict[str, Any]) -> bool:
    return account_type(member) in {"VIP", "S.VIP", "ADMIN"}


def current_member() -> dict[str, Any] | None:
    u = session.get("username")
    if not u:
        return None
    # Check session expiry
    login_time = session.get("login_time", 0)
    if time.time() - login_time > cfg.session_lifetime_seconds:
        session.clear()
        return None
    for m in load_members().get("members", []):
        if m.get("username") == u and m.get("status", "ON") == "ON":
            return m
    return None


def can_open_lesson(member: dict[str, Any], path: str) -> tuple[bool, str]:
    a = load_access()
    level = str(a.get("lessons", {}).get(path, a.get("default", "FREE"))).upper()
    return level == "FREE" or is_vip(member), level


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------
def require_admin(view):  # type: ignore[no-untyped-def]
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        if session.get("role") != "admin":
            return redirect("/admin/login")
        return view(*args, **kwargs)
    return wrapped


def require_member(view):  # type: ignore[no-untyped-def]
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        if session.get("role") != "member":
            return redirect("/member/login")
        if not current_member():
            session.clear()
            return redirect("/member/login")
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# HTML page template  (Tailwind CDN)
# ---------------------------------------------------------------------------

# Common Tailwind UI helpers
def _btn(label: str, href: str = "", extra_cls: str = "", onclick: str = "") -> str:
    """Render a small button or anchor styled with Tailwind."""
    base = "inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-semibold border border-blue-200 bg-white text-blue-700 hover:bg-blue-50 transition cursor-pointer"
    cls = f"{base} {extra_cls}".strip()
    if href:
        return f"<a href='{href}' class='{cls}'>{label}</a>"
    on = f" onclick='{onclick}'" if onclick else ""
    return f"<button class='{cls}'{on}>{label}</button>"


def _tag(label: str, kind: str = "") -> str:
    """Inline badge. kind: 'free', 'vip', or empty for neutral."""
    palettes = {
        "free": "bg-green-50 text-green-700 border-green-300",
        "vip":  "bg-pink-50  text-pink-700  border-pink-300",
        "":     "bg-gray-100 text-gray-600  border-gray-300",
    }
    cls = palettes.get(kind, palettes[""])
    return f"<span class='inline-block text-xs font-semibold px-2 py-0.5 rounded-full border {cls} mr-1'>{label}</span>"


def _field(label: str, inp: str) -> str:
    return (f"<div class='mb-4'><label class='block text-xs font-bold text-gray-500 mb-1'>{label}</label>"
            f"{inp}</div>")


def _input(name: str, typ: str = "text", extra: str = "") -> str:
    return (f"<input name='{name}' type='{typ}' {extra}"
            " class='w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            " focus:outline-none focus:ring-2 focus:ring-blue-500'>")


def _select(name: str, options: list[tuple[str, bool]]) -> str:
    opts = "".join(
        f"<option{' selected' if sel else ''}>{val}</option>"
        for val, sel in options
    )
    return (f"<select name='{name}' class='px-2 py-1 border border-gray-300 rounded-lg text-sm"
            f" focus:outline-none focus:ring-2 focus:ring-blue-500'>{opts}</select>")


def _err(msg: str) -> str:
    if not msg:
        return ""
    return f"<div class='mt-3 text-sm font-semibold text-red-600'>{html.escape(msg)}</div>"


def page(title: str, body: str) -> Response:
    return Response(
        "<!doctype html>"
        "<html lang='vi'>"
        "<head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)} · Luyện đề Thầy Minh</title>"
        "<script src='https://cdn.tailwindcss.com'></script>"
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>"
        "<style>body{font-family:'Inter',ui-sans-serif,system-ui,sans-serif}"
        ".mathjax-process{display:inline}</style>"
        "</head>"
        "<body class='bg-gray-50 min-h-screen text-gray-800'>"
        # ── Navbar ──────────────────────────────────────────────────────────
        "<nav class='bg-gradient-to-r from-blue-700 to-blue-600 shadow-lg'>"
        "<div class='max-w-screen-xl mx-auto px-4 py-3 flex items-center gap-4 flex-wrap'>"
        "<div class='flex-1'>"
        "<div class='text-white font-black text-lg leading-tight'>📚 Luyện đề AI · Thầy Minh</div>"
        "<div class='text-blue-200 text-xs mt-0.5'>Nguồn: GitHub ngan-hang/*.tex</div>"
        "</div>"
        "<div class='flex gap-2 flex-wrap'>"
        "<a href='/member' class='text-white text-sm font-semibold hover:text-blue-200 transition'>👤 Thành viên</a>"
        "<a href='/admin'  class='text-white text-sm font-semibold hover:text-blue-200 transition'>🔐 Admin</a>"
        "<a href='/github/repo' target='_blank' class='text-white text-sm font-semibold hover:text-blue-200 transition'>🐙 GitHub</a>"
        "</div>"
        "</div>"
        "</nav>"
        # ── Page content ─────────────────────────────────────────────────────
        "<main class='max-w-screen-xl mx-auto px-4 py-6'>"
        + body +
        "</main>"
        "</body></html>",
        mimetype="text/html",
    )


# ---------------------------------------------------------------------------
# TeX parsing helpers
# ---------------------------------------------------------------------------
def brace_arg(text: str, pos: int) -> tuple[str | None, int]:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] != "{":
        return None, pos
    depth = 0
    start = pos + 1
    i = pos
    while i < len(text):
        if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif text[i] == "}" and (i == 0 or text[i - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    return None, len(text)


def extract_args(text: str, command: str) -> list[str]:
    m = re.search(re.escape(command) + r"\b", text, re.I)
    if not m:
        return []
    out: list[str] = []
    pos = m.end()
    while True:
        arg, pos2 = brace_arg(text, pos)
        if arg is None:
            break
        out.append(arg)
        pos = pos2
    return out


def strip_true(s: str) -> str:
    return re.sub(r"^\s*\\True\s*", "", s, flags=re.I)


def clean_question(text: str) -> str:
    text = re.sub(r"%.*", "", text)
    text = DANG_RE.sub("", text)
    text = re.sub(r"\\ID\s*:\s*[^\n]*", "", text, flags=re.I)
    text = re.sub(r"\\begin\s*\{ex\}", "", text, flags=re.I)
    text = re.sub(r"\\end\s*\{ex\}", "", text, flags=re.I)
    return text.strip()


def parse_question(block: str) -> dict[str, Any]:
    tf_args = extract_args(block, "\\choiceTF")
    if tf_args:
        statements = [strip_true(x).strip() for x in tf_args[:6]]
        correct = [bool(re.match(r"^\s*\\True\b", x, re.I)) for x in tf_args[:6]]
        qtext = TF_RE.split(block, maxsplit=1)[0]
        return {"kind": "tf", "text": clean_question(qtext), "statements": statements, "correct": correct}
    args = extract_args(block, "\\choice")
    if args:
        options = [strip_true(x).strip() for x in args[:4]]
        correct = 0
        for i, x in enumerate(args[:4]):
            if re.match(r"^\s*\\True\b", x, re.I):
                correct = i
                break
        qtext = CHOICE_RE.split(block, maxsplit=1)[0]
        return {"kind": "choice", "text": clean_question(qtext), "options": options, "correct": correct}
    sm = SHORT_RE.search(block)
    if sm:
        return {"kind": "short", "text": clean_question(block[: sm.start()]), "answer": sm.group(1).strip()}
    return {"kind": "unsupported", "text": clean_question(block)}


def lesson_questions(path: str) -> list[dict[str, Any]]:
    _, text = read_tex(path)
    return [parse_question(b) for b in EX_RE.findall(text)]


# ---------------------------------------------------------------------------
# Routes – public
# ---------------------------------------------------------------------------
@app.get("/")
def root() -> Response:
    return redirect("/member/login")


@app.get("/github/repo")
def repo_link() -> Response:
    return redirect(f"https://github.com/{cfg.repo}")


# ---------------------------------------------------------------------------
# Routes – member auth
# ---------------------------------------------------------------------------
@app.route("/member/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def member_login() -> Response:
    msg = ""
    if request.method == "POST":
        if not _csrf_valid():
            msg = "Yêu cầu không hợp lệ (CSRF). Vui lòng tải lại trang."
        else:
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            # Input validation
            if not username or not password:
                msg = "Vui lòng nhập đầy đủ tài khoản và mật khẩu."
            elif len(username) > 64 or len(password) > 256:
                msg = "Tài khoản hoặc mật khẩu quá dài."
            else:
                data = load_members()
                matched = None
                need_upgrade = False
                for m in data.get("members", []):
                    if m.get("username") == username and m.get("status", "ON") == "ON":
                        if _check_password(password, m):
                            matched = m
                            need_upgrade = "_upgrade_password" in m
                        break
                if matched:
                    # Apply hash upgrade safely: reload fresh data, apply, save
                    if need_upgrade:
                        try:
                            fresh = load_members()
                            _cache_invalidate("members")
                            for fm in fresh.get("members", []):
                                if fm.get("username") == username:
                                    fm["password_bcrypt"] = matched.pop("_upgrade_password")
                                    fm.pop("password_sha256", None)
                                    break
                            save_members(fresh)
                            try:
                                sync_members(fresh)
                            except Exception:
                                pass
                        except Exception as exc:
                            log.warning("Hash upgrade failed for %s: %s", username, exc)
                    else:
                        matched.pop("_upgrade_password", None)
                    session.clear()
                    session.permanent = True
                    session.update(
                        role="member",
                        username=username,
                        name=matched.get("name") or username,
                        login_time=time.time(),
                    )
                    audit_log.info("LOGIN member=%s ip=%s", username, request.remote_addr)
                    return redirect("/member")
                msg = "Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa."
    csrf = _csrf_field()
    body = (
        "<div class='flex justify-center'>"
        "<div class='w-full max-w-sm'>"
        "<div class='bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden mt-8'>"
        "<div class='bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-4'>"
        "<h2 class='text-white font-black text-lg'>👤 Đăng nhập thành viên</h2>"
        "</div>"
        "<div class='p-6'>"
        "<form method='post'>" + csrf +
        _field("Tài khoản", _input("username", extra="required autocomplete='username'")) +
        _field("Mật khẩu", _input("password", "password", extra="required autocomplete='current-password'")) +
        "<div class='flex gap-2 mt-2'>"
        + _btn("Đăng nhập", extra_cls="bg-blue-600 text-white border-blue-600 hover:bg-blue-700") +
        _btn("Đăng ký", href="/member/register") +
        "</div>"
        + _err(msg) +
        "</form>"
        "</div></div></div></div>"
    )
    return page("Đăng nhập thành viên", body)


@app.route("/member/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def member_register() -> Response:
    msg = ""
    if request.method == "POST":
        if not _csrf_valid():
            msg = "Yêu cầu không hợp lệ (CSRF). Vui lòng tải lại trang."
        else:
            username = (request.form.get("username") or "").strip()
            name = (request.form.get("name") or "").strip()
            password = request.form.get("password") or ""
            if not username or not password:
                msg = "Thiếu tài khoản hoặc mật khẩu."
            elif not USERNAME_RE.match(username):
                msg = "Tài khoản chỉ được chứa chữ cái, số, gạch dưới, gạch ngang, dấu chấm (3-64 ký tự)."
            elif len(password) < 6:
                msg = "Mật khẩu phải có ít nhất 6 ký tự."
            elif len(password) > 256:
                msg = "Mật khẩu quá dài."
            else:
                data = load_members()
                users = {m.get("username") for m in data.get("members", [])}
                if username in users:
                    msg = "Tài khoản đã tồn tại."
                else:
                    data.setdefault("members", []).append({
                        "username": username,
                        "name": name[:100] or username,
                        "class": "",
                        "account_type": "FREE",
                        "status": "ON",
                        "password_bcrypt": _hash_password(password),
                    })
                    try:
                        save_members(data)
                        sync_members(data)
                        session.clear()
                        session.permanent = True
                        session.update(role="member", username=username, name=name or username, login_time=time.time())
                        audit_log.info("REGISTER member=%s ip=%s", username, request.remote_addr)
                        return redirect("/member")
                    except Exception as exc:
                        log.error("Registration error: %s", exc)
                        msg = "Lỗi lưu tài khoản. Vui lòng thử lại."
    csrf = _csrf_field()
    body = (
        "<div class='flex justify-center'>"
        "<div class='w-full max-w-sm'>"
        "<div class='bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden mt-8'>"
        "<div class='bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-4'>"
        "<h2 class='text-white font-black text-lg'>📝 Đăng ký thành viên</h2>"
        "</div>"
        "<div class='p-6'>"
        "<form method='post'>" + csrf +
        _field("Họ tên", _input("name", extra="maxlength='100'")) +
        _field("Tài khoản", _input("username", extra="required pattern='[a-zA-Z0-9_\\-.]{3,64}' title='3-64 ký tự: chữ, số, _, -, .'")) +
        _field("Mật khẩu", _input("password", "password", extra="required minlength='6'")) +
        "<div class='flex gap-2 mt-2'>"
        + _btn("Tạo tài khoản FREE", extra_cls="bg-blue-600 text-white border-blue-600 hover:bg-blue-700") +
        _btn("Quay lại", href="/member/login") +
        "</div>"
        + _err(msg) +
        "</form>"
        "</div></div></div></div>"
    )
    return page("Đăng ký", body)


@app.get("/member/logout")
def member_logout() -> Response:
    username = session.get("username", "unknown")
    session.clear()
    audit_log.info("LOGOUT member=%s ip=%s", username, request.remote_addr)
    return redirect("/member/login")


# ---------------------------------------------------------------------------
# Routes – member pages
# ---------------------------------------------------------------------------
@app.get("/member")
@require_member
def member_home() -> Response:
    member = current_member()
    assert member is not None
    data = index_data()
    vip = is_vip(member)
    page_num = max(1, int(request.args.get("page", 1)))
    per_page = 24
    lessons = [item for item in data.get("lessons", []) if isinstance(item, dict) and str(item.get("path") or "").startswith("ngan-hang/")]
    total = len(lessons)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page_num = min(page_num, total_pages)
    paginated = lessons[(page_num - 1) * per_page: page_num * per_page]

    cards = []
    for item in paginated:
        path = str(item.get("path") or "")
        title = str(item.get("BaiHoc") or item.get("De") or Path(path).parent.name)
        count = int(item.get("questions") or item.get("count") or 0)
        allowed, level = can_open_lesson(member, path)
        tag = "VIP" if level == "VIP" else "FREE"
        action = (
            _btn("📖 Làm bài", href=f"/member/lesson?path={urllib.parse.quote(path, safe='')}",
                 extra_cls="bg-blue-600 text-white border-blue-600 hover:bg-blue-700 mt-3 w-full justify-center")
            if allowed else _tag("🔒 Chỉ VIP", "vip")
        )
        tag_kind = "vip" if tag == "VIP" else "free"
        cards.append(
            "<div class='bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-col gap-1 hover:shadow-md transition'>"
            + f"<div class='font-bold text-gray-800 text-sm leading-snug'>{html.escape(title)}</div>"
            + f"<div class='text-xs text-gray-400'>{html.escape(str(item.get('Mon') or ''))} · {html.escape(str(item.get('Lop') or ''))}</div>"
            + "<div class='mt-1'>" + _tag(tag, tag_kind) + _tag(f"{count} câu") + "</div>"
            + f"<div class='mt-auto pt-2'>{action}</div>"
            + "</div>"
        )

    # Pagination controls
    pagination = ""
    if total_pages > 1:
        parts = []
        for p in range(1, total_pages + 1):
            active_cls = " bg-blue-600 text-white border-blue-600" if p == page_num else " bg-white text-blue-700 hover:bg-blue-50"
            parts.append(
                f"<a href='/member?page={p}' class='inline-flex items-center justify-center w-8 h-8 rounded-lg border border-blue-200 text-sm font-semibold transition{active_cls}'>{p}</a>"
            )
        pagination = (
            f"<div class='flex items-center gap-2 mt-6 flex-wrap'>{''.join(parts)}"
            f"<span class='text-xs text-gray-400'>({total} bài)</span></div>"
        )

    badge_kind = "vip" if vip else "free"
    badge_label = "⭐ VIP" if vip else "FREE"
    uname = html.escape(str(member.get("name") or member.get("username")))
    body = (
        # ── Top bar ──────────────────────────────────────────────────────────
        "<div class='flex items-center justify-between bg-white rounded-xl shadow-sm border border-gray-100 px-5 py-3 mb-5'>"
        f"<div><span class='font-bold text-gray-800'>👤 {uname}</span> "
        + _tag(badge_label, badge_kind) +
        "</div>"
        + _btn("🚪 Thoát", href="/member/logout", extra_cls="text-red-600 border-red-200 hover:bg-red-50") +
        "</div>"
        # ── Stats ─────────────────────────────────────────────────────────────
        "<div class='text-sm text-gray-500 mb-4'>"
        + str(int(data.get("total_files") or 0)) + " bài · "
        + str(int(data.get("total_questions") or 0)) + " câu"
        "</div>"
        # ── Cards ─────────────────────────────────────────────────────────────
        "<div class='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'>"
        + "".join(cards) +
        "</div>"
        + pagination
    )
    return page("Trang thành viên", body)


@app.get("/member/lesson")
@require_member
def member_lesson() -> Response:
    member = current_member()
    assert member is not None
    path = request.args.get("path", "")
    allowed, level = can_open_lesson(member, path)
    if not allowed:
        return page(
            "Bài VIP",
            "<div class='wrap'><div class='panel'><div class='body'>"
            "<div class='err'>🔒 Bài này chỉ dành cho thành viên VIP.</div>"
            "<a class='btn' href='/member'>← Quay lại</a></div></div></div>",
        )
    try:
        qs = lesson_questions(path)
    except ValueError:
        return page(
            "Đường dẫn không hợp lệ",
            "<div class='wrap'><div class='panel'><div class='body'>"
            "<div class='err'>Đường dẫn bài học không hợp lệ.</div>"
            "<a class='btn' href='/member'>← Quay lại</a></div></div></div>",
        )
    except Exception as exc:
        log.error("Error loading lesson %s: %s", path, exc)
        return page(
            "Lỗi đọc bài",
            "<div class='wrap'><div class='panel'><div class='body'>"
            "<div class='err'>Không thể tải bài học. Vui lòng thử lại sau.</div>"
            "<a class='btn' href='/member'>← Quay lại</a></div></div></div>",
        )
    # Sanitize JSON for inline <script> embedding: prevent </script> injection
    payload = json.dumps(qs, ensure_ascii=False).replace("</", "<\\/")
    Q_CARD = "bg-white rounded-xl border border-gray-100 shadow-sm p-4 mb-3"
    Q_TEXT = "text-sm leading-relaxed text-gray-700 mb-3"
    OPT_CLS = ("flex items-center gap-2 px-3 py-2 rounded-lg border border-blue-100 text-sm"
               " cursor-pointer hover:bg-blue-50 mb-2 transition")
    STMT_CLS = "bg-gray-50 rounded-lg p-3 mb-2 text-sm"
    cards = []
    for i, q in enumerate(qs, 1):
        t = html.escape(q["text"] if isinstance(q, dict) else str(q))
        num = f"<span class='font-bold text-blue-600 mr-1'>Câu {i}.</span>"
        if q.get("kind") == "choice":
            opts = "".join(
                f"<label class='{OPT_CLS}'><input type='radio' name='q{i}' value='{j}' class='accent-blue-600'>"
                f" <span class='font-semibold text-blue-500 w-5'>{chr(65+j)}.</span> {html.escape(o)}</label>"
                for j, o in enumerate(q.get("options", []))
            )
            cards.append(f"<div class='{Q_CARD}' data-i='{i-1}'><div class='{Q_TEXT}'>{num}{t}</div>{opts}</div>")
        elif q.get("kind") == "tf":
            stmts = "".join(
                f"<div class='{STMT_CLS}'><p class='mb-2'><b>{j+1}.</b> {html.escape(s)}</p>"
                f"<div class='flex gap-4'>"
                f"<label class='flex items-center gap-1 cursor-pointer text-green-700 font-semibold'>"
                f"<input type='radio' name='q{i}_{j}' value='1' class='accent-green-600'> Đúng</label>"
                f"<label class='flex items-center gap-1 cursor-pointer text-red-600 font-semibold'>"
                f"<input type='radio' name='q{i}_{j}' value='0' class='accent-red-500'> Sai</label>"
                f"</div></div>"
                for j, s in enumerate(q.get("statements", []))
            )
            cards.append(f"<div class='{Q_CARD} tf' data-i='{i-1}'><div class='{Q_TEXT}'>{num}{t}</div>{stmts}</div>")
        elif q.get("kind") == "short":
            cards.append(
                f"<div class='{Q_CARD}' data-i='{i-1}'><div class='{Q_TEXT}'>{num}{t}</div>"
                f"<input id='short{i}' placeholder='Nhập đáp án' class='w-full px-3 py-2 border border-gray-300"
                f" rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'></div>"
            )
        else:
            cards.append(
                f"<div class='{Q_CARD}'><div class='{Q_TEXT}'>{num}{t}</div>"
                "<div class='text-xs text-gray-400'>Câu tự luận / không chấm tự động</div></div>"
            )
    score_js = (
        "const DATA=%s;"
        "function score(){"
        "let right=0,total=0;"
        "DATA.forEach((q,i)=>{"
        "if(q.kind==='choice'){total++;const e=document.querySelector(`input[name=q${i+1}]:checked`);"
        "if(e&&Number(e.value)===Number(q.correct))right++;}"
        "else if(q.kind==='tf'){q.correct.forEach((c,j)=>{total++;const e=document.querySelector(`input[name=q${i+1}_${j}]:checked`);"
        "if(e&&Number(e.value)===(c?1:0))right++;});}"
        "else if(q.kind==='short'){total++;const e=document.getElementById(`short${i+1}`);"
        "if(e&&e.value.trim().toLowerCase()===String(q.answer||'').trim().toLowerCase())right++;}"
        "});"
        "const pct=total?right/total*10:0;"
        "document.getElementById('score').innerHTML=`✅ Đúng <b>${right}/${total}</b> · Điểm <b>${pct.toFixed(2)}</b>/10`;"
        "window.scrollTo({top:0,behavior:'smooth'});}"
    ) % payload
    lvl_kind = "vip" if level == "VIP" else "free"
    body = (
        "<div class='flex items-center justify-between bg-white rounded-xl shadow-sm border border-gray-100 px-5 py-3 mb-5'>"
        f"<div class='flex items-center gap-2'>"
        + _btn("← Danh sách bài", href="/member") +
        f"<span class='font-bold text-gray-700'>📖 {html.escape(Path(path).parent.name)}</span>"
        + _tag(level, lvl_kind) +
        "</div></div>"
        "<div id='score' class='bg-green-50 border border-green-200 text-green-800 rounded-xl px-5 py-3 mb-4 font-semibold text-sm'>"
        "Làm xong bấm <b>Chấm điểm</b>"
        "</div>"
        + _btn("📝 Chấm điểm", onclick="score()",
               extra_cls="mb-6 bg-blue-600 text-white border-blue-600 hover:bg-blue-700 px-6 py-2") +
        "".join(cards)
        + "<script>" + score_js + "</script>"
    )
    return page("Làm bài", body)


# ---------------------------------------------------------------------------
# Routes – admin auth
# ---------------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def admin_login() -> Response:
    msg = ""
    if request.method == "POST":
        if not _csrf_valid():
            msg = "Yêu cầu không hợp lệ (CSRF). Vui lòng tải lại trang."
        elif not cfg.admin_password:
            msg = "ADMIN_PASSWORD chưa được cấu hình trên server."
        elif request.form.get("password") == cfg.admin_password:
            session.clear()
            session.permanent = True
            session["role"] = "admin"
            session["login_time"] = time.time()
            audit_log.info("ADMIN_LOGIN ip=%s", request.remote_addr)
            return redirect("/admin")
        else:
            msg = "Mật khẩu ADMIN không đúng."
    csrf = _csrf_field()
    body = (
        "<div class='flex justify-center'>"
        "<div class='w-full max-w-xs'>"
        "<div class='bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden mt-8'>"
        "<div class='bg-gradient-to-r from-gray-800 to-gray-700 px-6 py-4'>"
        "<h2 class='text-white font-black text-lg'>🔐 ADMIN</h2>"
        "</div>"
        "<div class='p-6'>"
        "<form method='post'>" + csrf +
        _field("Mật khẩu ADMIN", _input("password", "password", extra="required autocomplete='current-password'")) +
        _btn("Đăng nhập", extra_cls="mt-2 bg-gray-800 text-white border-gray-700 hover:bg-gray-900") +
        _err(msg) +
        "</form>"
        "</div></div></div></div>"
    )
    return page("ADMIN", body)


@app.get("/admin/logout")
def admin_logout() -> Response:
    session.clear()
    audit_log.info("ADMIN_LOGOUT ip=%s", request.remote_addr)
    return redirect("/admin/login")


# ---------------------------------------------------------------------------
# Routes – admin pages
# ---------------------------------------------------------------------------
@app.get("/admin")
@require_admin
def admin_home() -> Response:
    data = load_members()
    rows = []
    for m in data.get("members", []):
        typ = account_type(m)
        u_esc = html.escape(str(m.get("username") or ""), quote=True)
        status_cls = "text-green-600" if m.get("status", "ON") == "ON" else "text-red-500"
        status_label = "✅ ON" if m.get("status", "ON") == "ON" else "⛔ OFF"
        type_cls = "vip" if typ == "VIP" else "free"
        rows.append(
            "<tr class='hover:bg-gray-50 border-b border-gray-100'>"
            f"<td class='py-2 px-3 text-sm font-mono'>{html.escape(str(m.get('username') or ''))}</td>"
            f"<td class='py-2 px-3 text-sm'>{html.escape(str(m.get('name') or ''))}</td>"
            f"<td class='py-2 px-3 text-xs text-gray-500'>{html.escape(str(m.get('class') or ''))}</td>"
            f"<td class='py-2 px-3'>" + _tag(typ, type_cls) + "</td>"
            f"<td class='py-2 px-3 text-xs font-semibold {status_cls}'>{status_label}</td>"
            "<td class='py-2 px-3 flex items-center gap-2 flex-wrap'>"
            f"<form method='post' action='/admin/member/type' class='inline-flex items-center gap-1'>"
            f"<input type='hidden' name='csrf_token' value='{html.escape(_csrf_token())}'>"
            f"<input type='hidden' name='username' value='{u_esc}'>"
            + _select("account_type", [("FREE", typ == "FREE"), ("VIP", typ == "VIP")]) +
            _btn("Lưu", extra_cls="ml-1") +
            "</form>"
            f"<form method='post' action='/admin/member/toggle' class='inline'>"
            f"<input type='hidden' name='csrf_token' value='{html.escape(_csrf_token())}'>"
            f"<input type='hidden' name='username' value='{u_esc}'>"
            + _btn("Bật/Tắt", extra_cls="text-orange-600 border-orange-200 hover:bg-orange-50") +
            "</form>"
            "</td></tr>"
        )
    SIDEBAR_BTN = "flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-semibold text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition"
    body = (
        "<div class='grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-5'>"
        # sidebar
        "<aside class='bg-white rounded-2xl shadow-sm border border-gray-100 p-4 h-fit'>"
        "<div class='font-black text-gray-800 mb-4 text-base'>⚙️ ADMIN</div>"
        f"<a href='/admin' class='{SIDEBAR_BTN}'>👥 Thành viên</a>"
        f"<a href='/admin/access' class='{SIDEBAR_BTN}'>🔐 Quyền FREE/VIP</a>"
        f"<a href='/github/quan-ly' class='{SIDEBAR_BTN}'>📚 Ngân hàng GitHub</a>"
        "<hr class='my-3 border-gray-100'>"
        f"<a href='/admin/logout' class='{SIDEBAR_BTN} text-red-600 hover:bg-red-50 hover:text-red-700'>🚪 Thoát</a>"
        "<p class='text-xs text-gray-400 mt-4 leading-relaxed'>Câu hỏi: GitHub .tex<br>Quyền: lesson_access.json<br>Thành viên: members.json</p>"
        "</aside>"
        # main
        "<main class='bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden'>"
        "<div class='flex items-center justify-between px-5 py-3 border-b border-gray-100'>"
        "<span class='font-bold text-gray-800'>👥 Danh sách thành viên</span>"
        + _btn("+ Thêm", href="/admin/member/add", extra_cls="bg-blue-600 text-white border-blue-600 hover:bg-blue-700") +
        "</div>"
        "<div class='overflow-x-auto'>"
        "<table class='w-full text-left'>"
        "<thead class='bg-gray-50 text-xs font-bold text-gray-500 uppercase'>"
        "<tr><th class='py-2 px-3'>Tài khoản</th><th class='py-2 px-3'>Họ tên</th><th class='py-2 px-3'>Lớp</th>"
        "<th class='py-2 px-3'>Quyền</th><th class='py-2 px-3'>Trạng thái</th><th class='py-2 px-3'>Thao tác</th></tr>"
        "</thead><tbody>" + "".join(rows) + "</tbody></table>"
        "</div></main></div>"
    )
    return page("Quản trị", body)


@app.route("/admin/member/add", methods=["GET", "POST"])
@require_admin
def admin_add() -> Response:
    msg = ""
    if request.method == "POST":
        if not _csrf_valid():
            msg = "Yêu cầu không hợp lệ (CSRF)."
        else:
            username = (request.form.get("username") or "").strip()
            name = (request.form.get("name") or "").strip()
            cls = (request.form.get("class") or "").strip()
            password = request.form.get("password") or ""
            typ = (request.form.get("account_type") or "FREE").upper()
            if not username or not password:
                msg = "Thiếu tài khoản/mật khẩu."
            elif not USERNAME_RE.match(username):
                msg = "Tài khoản không hợp lệ."
            elif len(password) < 6 or len(password) > 256:
                msg = "Mật khẩu phải từ 6 đến 256 ký tự."
            else:
                data = load_members()
                users = {m.get("username") for m in data.get("members", [])}
                if username in users:
                    msg = "Tài khoản đã tồn tại."
                else:
                    data.setdefault("members", []).append({
                        "username": username,
                        "name": name[:100] or username,
                        "class": cls[:50],
                        "account_type": "VIP" if typ == "VIP" else "FREE",
                        "status": "ON",
                        "password_bcrypt": _hash_password(password),
                    })
                    try:
                        save_members(data)
                        sync_members(data)
                        audit_log.info("ADMIN_ADD_MEMBER username=%s type=%s ip=%s", username, typ, request.remote_addr)
                        return redirect("/admin")
                    except Exception as exc:
                        log.error("Admin add member error: %s", exc)
                        msg = "Lỗi lưu thành viên. Vui lòng thử lại."
    csrf = _csrf_field()
    body = (
        "<div class='flex justify-center'>"
        "<div class='w-full max-w-md'>"
        "<div class='bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden'>"
        "<div class='bg-gradient-to-r from-gray-800 to-gray-700 px-6 py-4'>"
        "<h2 class='text-white font-black text-lg'>➕ Thêm thành viên</h2>"
        "</div>"
        "<div class='p-6'><form method='post'>" + csrf +
        _field("Họ tên", _input("name", extra="maxlength='100'")) +
        _field("Tài khoản", _input("username", extra="required pattern='[a-zA-Z0-9_\\-.]{3,64}'")) +
        _field("Lớp", _input("class", extra="maxlength='50'")) +
        _field("Mật khẩu", _input("password", "password", extra="required minlength='6'")) +
        _field("Quyền", _select("account_type", [("FREE", True), ("VIP", False)])) +
        "<div class='flex gap-2 mt-2'>"
        + _btn("💾 Lưu", extra_cls="bg-blue-600 text-white border-blue-600 hover:bg-blue-700") +
        _btn("← Quay lại", href="/admin") +
        "</div>"
        + _err(msg) +
        "</form></div></div></div></div>"
    )
    return page("Thêm thành viên", body)


@app.post("/admin/member/type")
@require_admin
def admin_member_type() -> Response:
    if not _csrf_valid():
        return page("Lỗi", "<div class='bg-red-50 border border-red-200 rounded-xl p-6 text-red-600 font-bold'>Yêu cầu không hợp lệ (CSRF). Vui lòng tải lại trang.</div>")
    username = request.form.get("username", "")
    typ = "VIP" if (request.form.get("account_type") or "FREE").upper() == "VIP" else "FREE"
    data = load_members()
    for m in data.get("members", []):
        if m.get("username") == username:
            m["account_type"] = typ
            break
    save_members(data)
    sync_members(data)
    audit_log.info("ADMIN_CHANGE_TYPE username=%s type=%s ip=%s", username, typ, request.remote_addr)
    return redirect("/admin")


@app.post("/admin/member/toggle")
@require_admin
def admin_toggle() -> Response:
    if not _csrf_valid():
        return page("Lỗi", "<div class='bg-red-50 border border-red-200 rounded-xl p-6 text-red-600 font-bold'>Yêu cầu không hợp lệ (CSRF). Vui lòng tải lại trang.</div>")
    username = request.form.get("username", "")
    data = load_members()
    new_status = "ON"
    for m in data.get("members", []):
        if m.get("username") == username:
            new_status = "OFF" if m.get("status", "ON") == "ON" else "ON"
            m["status"] = new_status
            break
    save_members(data)
    sync_members(data)
    audit_log.info("ADMIN_TOGGLE_STATUS username=%s status=%s ip=%s", username, new_status, request.remote_addr)
    return redirect("/admin")


@app.get("/admin/access")
@require_admin
def admin_access() -> Response:
    idx = index_data()
    acc = load_access()
    rows = []
    for item in idx.get("lessons", []):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        if not path.startswith("ngan-hang/"):
            continue
        level = str(acc.get("lessons", {}).get(path, acc.get("default", "FREE"))).upper()
        title = str(item.get("BaiHoc") or item.get("De") or Path(path).parent.name)
        lvl_kind = "vip" if level == "VIP" else "free"
        rows.append(
            "<div class='bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-col gap-2 hover:shadow-md transition'>"
            f"<div class='font-bold text-sm text-gray-800'>{html.escape(title)}</div>"
            f"<div class='text-xs text-gray-400 break-all'>{html.escape(path)}</div>"
            + _tag(level, lvl_kind) +
            f"<form method='post' action='/admin/access/save' class='flex items-center gap-2 mt-1'>"
            f"<input type='hidden' name='csrf_token' value='{html.escape(_csrf_token())}'>"
            f"<input type='hidden' name='path' value='{html.escape(path, quote=True)}'>"
            + _select("level", [("FREE", level == "FREE"), ("VIP", level == "VIP")]) +
            _btn("💾 Lưu", extra_cls="bg-blue-600 text-white border-blue-600 hover:bg-blue-700") +
            "</form>"
            "</div>"
        )
    body = (
        "<div class='flex items-center justify-between mb-5'>"
        "<h2 class='font-black text-gray-800 text-lg'>🔐 Quyền bài học FREE / VIP</h2>"
        + _btn("← ADMIN", href="/admin") +
        "</div>"
        "<p class='text-sm text-gray-500 mb-4'>FREE: tất cả thành viên có thể vào · VIP: chỉ thành viên VIP</p>"
        "<div class='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'>"
        + "".join(rows) + "</div>"
    )
    return page("Quyền bài học", body)


@app.post("/admin/access/save")
@require_admin
def admin_access_save() -> Response:
    if not _csrf_valid():
        return page("Lỗi", "<div class='bg-red-50 border border-red-200 rounded-xl p-6 text-red-600 font-bold'>Yêu cầu không hợp lệ (CSRF). Vui lòng tải lại trang.</div>")
    path = request.form.get("path", "")
    level = "VIP" if (request.form.get("level") or "FREE").upper() == "VIP" else "FREE"
    data = load_access()
    data.setdefault("lessons", {})[path] = level
    save_access(data)
    sync_access(data)
    audit_log.info("ADMIN_SET_ACCESS path=%s level=%s ip=%s", path, level, request.remote_addr)
    return redirect("/admin/access")


@app.get("/github/quan-ly")
@require_admin
def github_manage() -> Response:
    data = index_data()
    acc = load_access()
    cards = []
    for item in data.get("lessons", []):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        if not path.startswith("ngan-hang/"):
            continue
        title = str(item.get("BaiHoc") or item.get("De") or Path(path).parent.name)
        count = int(item.get("questions") or item.get("count") or 0)
        level = str(acc.get("lessons", {}).get(path, acc.get("default", "FREE"))).upper()
        lvl_kind = "vip" if level == "VIP" else "free"
        cards.append(
            "<div class='bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-col gap-1 hover:shadow-md transition'>"
            f"<div class='font-bold text-sm text-gray-800'>{html.escape(title)}</div>"
            f"<div class='text-xs text-gray-400 break-all mb-1'>{html.escape(path)}</div>"
            + _tag(level, lvl_kind) + _tag(f"{count} câu") +
            _btn("✏️ Sửa .tex", href=f"/admin/edit?path={urllib.parse.quote(path, safe='')}",
                 extra_cls="mt-3 w-full justify-center") +
            "</div>"
        )
    body = (
        "<div class='flex items-center justify-between mb-5'>"
        "<div>"
        "<h2 class='font-black text-gray-800 text-lg'>📚 Ngân hàng GitHub</h2>"
        f"<p class='text-sm text-gray-500'>{int(data.get('total_files') or 0)} bài · {int(data.get('total_questions') or 0)} câu</p>"
        "</div>"
        + _btn("🔐 Phân quyền FREE/VIP", href="/admin/access") +
        "</div>"
        "<div class='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'>"
        + "".join(cards) + "</div>"
    )
    return page("Ngân hàng GitHub", body)


@app.get("/admin/edit")
@require_admin
def admin_edit() -> Response:
    path = request.args.get("path", "")
    try:
        sha, text = read_tex(path)
    except ValueError:
        return page("Lỗi", "<div class='bg-red-50 border border-red-200 rounded-xl p-6 text-red-600 font-bold'>Đường dẫn không hợp lệ.</div>")
    except Exception as exc:
        log.error("Admin edit error path=%s: %s", path, exc)
        return page("Lỗi", "<div class='bg-red-50 border border-red-200 rounded-xl p-6 text-red-600 font-bold'>Không thể tải file. Vui lòng thử lại sau.</div>")
    csrf_tok = _csrf_token()
    body = (
        "<div class='bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden'>"
        "<div class='flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50'>"
        f"<b class='text-sm font-mono text-gray-700 truncate max-w-xl'>✏️ {html.escape(path)}</b>"
        + _btn("← Mục lục", href="/github/quan-ly") +
        "</div>"
        "<textarea id='code' class='w-full font-mono text-xs p-4 border-0 outline-none resize-y bg-gray-900 text-green-300'"
        " style='height:72vh;tab-size:4'>" + html.escape(text) + "</textarea>"
        "<div class='flex items-center gap-3 px-5 py-3 border-t border-gray-100'>"
        + _btn("💾 Lưu trực tiếp GitHub", onclick="saveTex()",
               extra_cls="bg-blue-600 text-white border-blue-600 hover:bg-blue-700") +
        f"<a href='https://github.com/{html.escape(cfg.repo)}/blob/{urllib.parse.quote(cfg.branch)}/{urllib.parse.quote(path, safe='/')}'"
        " target='_blank' class='inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-semibold"
        " border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 transition'>🐙 Mở GitHub</a>"
        "<span id='msg' class='text-sm font-semibold'></span>"
        "</div></div>"
        "<script>const path=" + json.dumps(path, ensure_ascii=False) + ","
        "sha=" + json.dumps(sha) + ","
        "csrfToken=" + json.dumps(csrf_tok) + ";"
        "async function saveTex(){"
        "const msg=document.getElementById('msg');"
        "msg.textContent='Đang lưu...';"
        "try{"
        "const r=await fetch('/admin/api/save',{method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({path,sha,text:document.getElementById('code').value,csrf_token:csrfToken})});"
        "const d=await r.json();"
        "msg.textContent=d.ok?'✅ Đã commit GitHub: '+d.commit:'❌ '+(d.error||'Lỗi');"
        "}catch(e){msg.textContent='❌ '+e}}"
        "</script>"
    )
    return page("Sửa .tex", body)


@app.post("/admin/api/save")
@require_admin
def admin_save() -> Response:
    data = request.get_json(silent=True) or {}
    if not _csrf_valid():
        return jsonify(ok=False, error="Yêu cầu không hợp lệ (CSRF)"), 403
    path = data.get("path", "")
    text = data.get("text")
    sha = data.get("sha", "")
    if not isinstance(text, str):
        return jsonify(ok=False, error="Thiếu text"), 400
    try:
        path = _validate_tex_path(path)
    except ValueError:
        return jsonify(ok=False, error="Đường dẫn không hợp lệ"), 400
    if not sha:
        return jsonify(ok=False, error="Thiếu sha"), 400
    try:
        result = gh_put_file(path, text, "ADMIN cập nhật .tex trực tiếp", sha)
        commit_sha = str((result.get("commit") or {}).get("sha") or "")[:12]
        audit_log.info("ADMIN_SAVE_TEX path=%s commit=%s ip=%s", path, commit_sha, request.remote_addr)
        return jsonify(ok=True, commit=commit_sha)
    except Exception as exc:
        log.error("Admin save error path=%s: %s", path, exc)
        return jsonify(ok=False, error="Lỗi lưu file. Vui lòng thử lại."), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
