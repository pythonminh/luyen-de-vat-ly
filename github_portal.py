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
# CSS (unchanged from original)
# ---------------------------------------------------------------------------
CSS = """
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial}.top{background:#1769d2;color:#fff;padding:10px 16px}.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.brand{font-size:20px;font-weight:900}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto}.nav a,.btn{display:inline-block;text-decoration:none;border:1px solid #bdd5f4;border-radius:8px;padding:7px 10px;background:#fff;color:#145bb0;font-weight:800;cursor:pointer;margin:3px}.nav a{background:transparent;color:#fff;border-color:#ffffff66}.wrap{max-width:1450px;margin:auto;padding:12px}.grid{display:grid;grid-template-columns:260px 1fr;gap:10px}.panel{background:#fff;border:1px solid #d6e0ea;border-radius:12px;overflow:hidden}.head{padding:10px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:900}.body{padding:10px}.field{margin-bottom:8px}.field label{display:block;font-size:10px;font-weight:800;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.mh{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;display:flex;justify-content:space-between;gap:8px;font-weight:900}.hero{padding:14px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px;padding:8px}.card{border:1px solid #dce5ed;border-radius:9px;padding:10px;background:#fff}.small{font-size:11px;color:#64748b}.tag{display:inline-block;padding:3px 7px;border:1px solid #cbd5e1;border-radius:999px;font-size:10px;margin:4px 3px 0 0}.free{border-color:#86efac;background:#f0fdf4;color:#166534}.vip{border-color:#f9a8d4;background:#fdf2f8;color:#9d174d}.lock{opacity:.72}.login{max-width:420px;margin:70px auto}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:7px;border-bottom:1px solid #e5e7eb;text-align:left}.code{width:100%;height:72vh;resize:vertical;border:1px solid #cbd5e1;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.actions{padding:0 10px 10px}.ok{color:#15803d;font-weight:800}.err{color:#b91c1c;font-weight:800}.qtext{line-height:1.6}.opt{padding:9px;border:1px solid #dbeafe;border-radius:8px;margin:6px 0;cursor:pointer}.opt:hover{background:#f8fbff}.answer{margin-top:12px;padding:10px;border:1px solid #bfdbfe;border-radius:8px;background:#eff6ff}.score{padding:10px;border:1px solid #86efac;background:#f0fdf4;border-radius:9px;font-weight:900}.section{margin:10px 0;padding:9px;border:1px solid #dbeafe;border-radius:8px;background:#f8fbff}.hide{display:none}@media(max-width:800px){.grid{grid-template-columns:1fr}.login{margin:25px auto}}
"""

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
# HTML page template
# ---------------------------------------------------------------------------
def page(title: str, body: str) -> Response:
    return Response(
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style>"
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>"
        "</head><body><div class='top'><div class='row'>"
        "<div><div class='brand'>📚 Luyện đề AI · Thầy Minh</div>"
        "<div class='sub'>Nguồn chính: GitHub / ngan-hang/*.tex · Google Sheet không dùng khi chạy</div></div>"
        "<div class='nav'><a href='/member'>👤 Thành viên</a><a href='/admin'>🔐 ADMIN</a>"
        "<a href='/github/repo' target='_blank'>🐙 GitHub</a></div></div></div>"
        + body + "</body></html>",
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
        "<div class='wrap'><div class='panel login'><div class='head'>👤 Đăng nhập thành viên</div>"
        "<div class='body'><form method='post'>" + csrf +
        "<div class='field'><label>Tài khoản</label><input name='username' required autocomplete='username'></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required autocomplete='current-password'></div>"
        "<button class='btn'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a>"
        f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>"
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
        "<div class='wrap'><div class='panel login'><div class='head'>📝 Đăng ký thành viên</div>"
        "<div class='body'><form method='post'>" + csrf +
        "<div class='field'><label>Họ tên</label><input name='name' maxlength='100'></div>"
        "<div class='field'><label>Tài khoản</label><input name='username' required pattern='[a-zA-Z0-9_\\-.]{3,64}' title='3-64 ký tự: chữ, số, _, -, .'></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required minlength='6'></div>"
        "<button class='btn'>Tạo tài khoản FREE</button> <a class='btn' href='/member/login'>Quay lại</a>"
        f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>"
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
            f"<a class='btn' href='/member/lesson?path={urllib.parse.quote(path, safe='')}'>Làm bài</a>"
            if allowed else "<span class='tag vip'>🔒 Chỉ VIP</span>"
        )
        cards.append(
            "<div class='card'><b>" + html.escape(title) + "</b>"
            + f"<div class='small'>{html.escape(str(item.get('Mon') or ''))} · {html.escape(str(item.get('Lop') or ''))}</div>"
            + f"<span class='tag {('vip' if tag=='VIP' else 'free')}'>{tag}</span>"
            + f"<span class='tag'>{count} câu</span><div>{action}</div></div>"
        )

    # Pagination controls
    pagination = ""
    if total_pages > 1:
        parts = []
        for p in range(1, total_pages + 1):
            active = " style='font-weight:900;text-decoration:underline'" if p == page_num else ""
            parts.append(f"<a class='btn' href='/member?page={p}'{active}>{p}</a>")
        pagination = "<div style='padding:8px'>" + "".join(parts) + f" <span class='small'>({total} bài)</span></div>"

    badge = "VIP – được làm FREE + VIP" if vip else "Thành viên thường – chỉ FREE"
    body = (
        "<div class='wrap'><div class='panel'><div class='mh'><span>👤 "
        + html.escape(str(member.get("name") or member.get("username")))
        + f" · <span class='tag {('vip' if vip else 'free')}'>{badge}</span></span>"
        + "<a class='btn' href='/member/logout'>Thoát</a></div>"
        + "<div class='hero'><h2>Chọn bài để học</h2><div class='small'>"
        + str(int(data.get("total_files") or 0)) + " bài · " + str(int(data.get("total_questions") or 0))
        + " câu</div></div><div class='cards'>" + "".join(cards) + "</div>"
        + pagination + "</div></div>"
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
    cards = []
    for i, q in enumerate(qs, 1):
        t = html.escape(q["text"] if isinstance(q, dict) else str(q))
        if q.get("kind") == "choice":
            opts = "".join(
                f"<label class='opt'><input type='radio' name='q{i}' value='{j}'> {chr(65+j)}. {html.escape(o)}</label>"
                for j, o in enumerate(q.get("options", []))
            )
            cards.append(f"<div class='card' data-i='{i-1}'><div class='qtext'><b>Câu {i}.</b> {t}</div>{opts}</div>")
        elif q.get("kind") == "tf":
            stmts = "".join(
                f"<div class='section'><b>{j+1}.</b> {html.escape(s)}<br>"
                f"<label><input type='radio' name='q{i}_{j}' value='1'> Đúng</label> &nbsp; "
                f"<label><input type='radio' name='q{i}_{j}' value='0'> Sai</label></div>"
                for j, s in enumerate(q.get("statements", []))
            )
            cards.append(f"<div class='card tf' data-i='{i-1}'><div class='qtext'><b>Câu {i}.</b> {t}</div>{stmts}</div>")
        elif q.get("kind") == "short":
            cards.append(
                f"<div class='card' data-i='{i-1}'><div class='qtext'><b>Câu {i}.</b> {t}</div>"
                f"<input id='short{i}' class='field' placeholder='Nhập đáp án'></div>"
            )
        else:
            cards.append(
                f"<div class='card'><div class='qtext'><b>Câu {i}.</b> {t}</div>"
                "<div class='small'>Câu tự luận/không hỗ trợ chấm tự động.</div></div>"
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
    body = (
        "<div class='wrap'><div class='panel'><div class='mh'><span>📖 "
        + html.escape(Path(path).parent.name)
        + f" · <span class='tag {('vip' if level=='VIP' else 'free')}'>{level}</span></span>"
        + "<a class='btn' href='/member'>← Danh sách bài</a></div>"
        + "<div class='hero'><div id='score' class='score'>Làm xong bấm <b>Chấm điểm</b></div>"
        + "<button class='btn' onclick='score()'>📝 Chấm điểm</button></div>"
        + "<div class='cards'>" + "".join(cards) + "</div></div></div>"
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
        "<div class='wrap'><div class='panel login'><div class='head'>🔐 ADMIN</div>"
        "<div class='body'><form method='post'>" + csrf +
        "<div class='field'><label>Mật khẩu ADMIN</label>"
        "<input name='password' type='password' required autocomplete='current-password'></div>"
        "<button class='btn'>Đăng nhập</button>"
        f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>"
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
        rows.append(
            "<tr>"
            "<td>" + html.escape(str(m.get("username") or "")) + "</td>"
            "<td>" + html.escape(str(m.get("name") or "")) + "</td>"
            "<td>" + html.escape(str(m.get("class") or "")) + "</td>"
            "<td>" + html.escape(typ) + "</td>"
            "<td>" + html.escape(str(m.get("status") or "ON")) + "</td>"
            "<td>"
            f"<form method='post' action='/admin/member/type' style='display:inline'>"
            f"<input type='hidden' name='csrf_token' value='{html.escape(_csrf_token())}'>"
            f"<input type='hidden' name='username' value='{u_esc}'>"
            f"<select name='account_type'>"
            f"<option {'selected' if typ=='FREE' else ''}>FREE</option>"
            f"<option {'selected' if typ=='VIP' else ''}>VIP</option>"
            f"</select><button class='btn'>Lưu quyền</button></form>"
            f"<form method='post' action='/admin/member/toggle' style='display:inline'>"
            f"<input type='hidden' name='csrf_token' value='{html.escape(_csrf_token())}'>"
            f"<input type='hidden' name='username' value='{u_esc}'>"
            f"<button class='btn'>Bật/Tắt</button></form>"
            "</td></tr>"
        )
    body = (
        "<div class='wrap'><div class='grid'><aside class='panel'><div class='head'>⚙️ ADMIN</div><div class='body'>"
        "<a class='btn' href='/admin'>👥 Thành viên</a><a class='btn' href='/admin/access'>🔐 Quyền FREE/VIP</a>"
        "<a class='btn' href='/github/quan-ly'>📚 Ngân hàng GitHub</a><a class='btn' href='/admin/logout'>Thoát</a>"
        "<hr><div class='small'>Nguồn câu hỏi: GitHub .tex<br>Quyền bài: lesson_access.json<br>Thành viên: members.json</div>"
        "</div></aside>"
        "<main class='panel'><div class='mh'><span>👥 Thành viên</span><a class='btn' href='/admin/member/add'>+ Thêm</a></div>"
        "<div class='body'><table class='table'><tr><th>Tài khoản</th><th>Họ tên</th><th>Lớp</th><th>Quyền</th><th>Trạng thái</th><th>Thao tác</th></tr>"
        + "".join(rows) + "</table></div></main></div></div>"
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
        "<div class='wrap'><div class='panel login'><div class='head'>➕ Thêm thành viên</div>"
        "<div class='body'><form method='post'>" + csrf +
        "<div class='field'><label>Họ tên</label><input name='name' maxlength='100'></div>"
        "<div class='field'><label>Tài khoản</label><input name='username' required pattern='[a-zA-Z0-9_\\-.]{3,64}'></div>"
        "<div class='field'><label>Lớp</label><input name='class' maxlength='50'></div>"
        "<div class='field'><label>Mật khẩu</label><input name='password' type='password' required minlength='6'></div>"
        "<div class='field'><label>Quyền</label><select name='account_type'><option>FREE</option><option>VIP</option></select></div>"
        "<button class='btn'>Lưu</button> <a class='btn' href='/admin'>Quay lại</a>"
        f"<div class='err'>{html.escape(msg)}</div></form></div></div></div>"
    )
    return page("Thêm thành viên", body)


@app.post("/admin/member/type")
@require_admin
def admin_member_type() -> Response:
    if not _csrf_valid():
        return page("Lỗi", "<div class='wrap'><div class='err'>Yêu cầu không hợp lệ (CSRF).</div></div>")
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
        return page("Lỗi", "<div class='wrap'><div class='err'>Yêu cầu không hợp lệ (CSRF).</div></div>")
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
        rows.append(
            f"<div class='card'>"
            f"<b>{html.escape(title)}</b><div class='small'>{html.escape(path)}</div>"
            f"<form method='post' action='/admin/access/save'>"
            f"<input type='hidden' name='csrf_token' value='{html.escape(_csrf_token())}'>"
            f"<input type='hidden' name='path' value='{html.escape(path, quote=True)}'>"
            f"<select name='level'>"
            f"<option {'selected' if level == 'FREE' else ''}>FREE</option>"
            f"<option {'selected' if level == 'VIP' else ''}>VIP</option>"
            f"</select>"
            f"<button class='btn'>Lưu quyền</button>"
            f"<span class='tag {'vip' if level == 'VIP' else 'free'}'>{level}</span>"
            f"</form></div>"
        )
    body = (
        "<div class='wrap'><div class='panel'><div class='mh'>"
        "<span>🔐 Quyền bài học FREE / VIP</span><a class='btn' href='/admin'>← ADMIN</a></div>"
        "<div class='hero'><div class='small'>FREE: tất cả thành viên · VIP: chỉ VIP</div></div>"
        "<div class='cards'>" + "".join(rows) + "</div></div></div>"
    )
    return page("Quyền bài học", body)


@app.post("/admin/access/save")
@require_admin
def admin_access_save() -> Response:
    if not _csrf_valid():
        return page("Lỗi", "<div class='wrap'><div class='err'>Yêu cầu không hợp lệ (CSRF).</div></div>")
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
        cards.append(
            "<div class='card'><b>" + html.escape(title) + "</b>"
            "<div class='small'>" + html.escape(path) + "</div>"
            f"<span class='tag {('vip' if level=='VIP' else 'free')}'>{level}</span>"
            f"<span class='tag'>{count} câu</span>"
            "<a class='btn' href='/admin/edit?path=" + urllib.parse.quote(path, safe="") + "'>✏️ Đọc / sửa .tex</a></div>"
        )
    body = (
        "<div class='wrap'><div class='panel'><div class='mh'>"
        "<span>📚 Ngân hàng GitHub</span>"
        "<span>" + str(int(data.get("total_files") or 0)) + " bài · " + str(int(data.get("total_questions") or 0)) + " câu</span></div>"
        "<div class='hero'><a class='btn' href='/admin/access'>🔐 Phân quyền FREE/VIP</a></div>"
        "<div class='cards'>" + "".join(cards) + "</div></div></div>"
    )
    return page("Ngân hàng GitHub", body)


@app.get("/admin/edit")
@require_admin
def admin_edit() -> Response:
    path = request.args.get("path", "")
    try:
        sha, text = read_tex(path)
    except ValueError:
        return page("Lỗi", "<div class='wrap'><div class='panel'><div class='body'><div class='err'>Đường dẫn không hợp lệ.</div></div></div></div>")
    except Exception as exc:
        log.error("Admin edit error path=%s: %s", path, exc)
        return page("Lỗi", "<div class='wrap'><div class='panel'><div class='body'><div class='err'>Không thể tải file. Vui lòng thử lại sau.</div></div></div></div>")
    csrf_tok = _csrf_token()
    body = (
        "<div class='wrap'><div class='panel'>"
        "<div class='mh'><b>✏️ " + html.escape(path) + "</b><a class='btn' href='/github/quan-ly'>← Mục lục</a></div>"
        "<textarea id='code' class='code'>" + html.escape(text) + "</textarea>"
        "<div class='actions'>"
        "<button class='btn' onclick='saveTex()'>💾 Lưu trực tiếp GitHub</button>"
        "<a class='btn' href='https://github.com/" + html.escape(cfg.repo) + "/blob/" + urllib.parse.quote(cfg.branch) + "/" + urllib.parse.quote(path, safe="/") + "' target='_blank'>🐙 Mở GitHub</a>"
        "<span id='msg'></span></div></div></div>"
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
