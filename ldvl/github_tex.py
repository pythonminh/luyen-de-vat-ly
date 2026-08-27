# -*- coding: utf-8 -*-
"""Kho LaTeX Môn/Lớp/Chương/Bài — đọc local ngan-hang/ và tải từ GitHub."""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

ILLEGAL_FS = re.compile(r'[<>:"/\\|?*]')
GITHUB_UA = "luyen-de-vat-ly-app"


def github_tex_config(app_dir: str) -> Dict[str, str]:
    repo = (os.environ.get("GITHUB_LATEX_REPO") or "pythonminh/luyen-de-vat-ly").strip().strip("/")
    branch = (os.environ.get("GITHUB_LATEX_BRANCH") or "main").strip() or "main"
    rel_dir = (os.environ.get("GITHUB_LATEX_DIR") or "ngan-hang").strip().strip("/").replace("\\", "/")
    token = (os.environ.get("GITHUB_LATEX_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    local = os.path.join(app_dir, rel_dir.replace("/", os.sep))
    cache = os.path.join(app_dir, "data", "github_tex_cache", rel_dir.replace("/", os.sep))
    return {
        "repo": repo,
        "branch": branch,
        "rel_dir": rel_dir,
        "token": token,
        "local_dir": local,
        "cache_dir": cache,
        "raw_base": f"https://raw.githubusercontent.com/{repo}/{branch}/{rel_dir}",
        "blob_base": f"https://github.com/{repo}/blob/{branch}/{rel_dir}",
    }


def safe_folder_name(name: str) -> str:
    s = ILLEGAL_FS.sub("-", (name or "").strip())
    s = re.sub(r"\s+", " ", s).strip(" .")
    return (s[:120] if s else "Khong_ten")


def lop_folder_name(lop: str) -> str:
    t = (lop or "").strip()
    if t.lower().startswith("lớp") or t.lower().startswith("lop"):
        return safe_folder_name(t)
    return safe_folder_name(f"Lớp {t}") if t else "Chua_phan_lop"


def lesson_rel_path(mon: str, lop: str, chuong: str, bai: str) -> str:
    return "/".join(
        [
            safe_folder_name(mon or "Chua_phan_mon"),
            lop_folder_name(lop),
            safe_folder_name(chuong or "Chua_phan_chuong"),
            safe_folder_name(bai or "Chua_phan_bai"),
            "de.tex",
        ]
    )


def defaults_from_rel_path(rel: str) -> Dict[str, str]:
    parts = [p for p in str(rel or "").replace("\\", "/").split("/") if p and p != "de.tex"]
    mon = parts[0] if parts else ""
    lop_raw = parts[1] if len(parts) > 1 else ""
    chuong = parts[2] if len(parts) > 2 else ""
    bai = parts[3] if len(parts) > 3 else ""
    lop = lop_raw
    m = re.match(r"^(?:Lớp|Lop)\s+(.+)$", lop_raw, re.I)
    if m:
        lop = m.group(1).strip()
    return {"Mon": mon, "Lop": lop, "Chuong": chuong, "BaiHoc": bai, "De": bai}


def _headers(token: str = "") -> Dict[str, str]:
    h = {"User-Agent": GITHUB_UA, "Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def http_get_bytes(url: str, token: str = "", timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_text(url: str, token: str = "", timeout: int = 45) -> str:
    raw = http_get_bytes(url, token=token, timeout=timeout)
    return raw.decode("utf-8", errors="replace")


def _muc_luc_from_local(cfg: Dict[str, str]) -> List[Dict[str, Any]]:
    for root in (cfg.get("local_dir") or "", cfg.get("cache_dir") or ""):
        if not root:
            continue
        path = os.path.join(root, "muc_luc.json")
        if not os.path.isfile(path):
            continue
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            return [x for x in (data.get("lessons") or []) if isinstance(x, dict)]
        except Exception:
            continue
    return []


def load_muc_luc_lessons(cfg: Dict[str, str], prefer_remote: bool = False) -> List[Dict[str, Any]]:
    """Đọc muc_luc.json local trước (Render/cold start). GitHub chỉ khi thiếu file hoặc sync yêu cầu."""
    if not prefer_remote:
        local = _muc_luc_from_local(cfg)
        if local:
            return local
    remote: List[Dict[str, Any]] = []
    url = (cfg.get("raw_base") or "").rstrip("/") + "/muc_luc.json"
    try:
        data = json.loads(http_get_text(url, token=cfg.get("token") or "", timeout=20))
        remote = [x for x in (data.get("lessons") or []) if isinstance(x, dict)]
    except Exception:
        remote = []
    if remote:
        payload = json.dumps({"schema": 1, "lessons": remote}, ensure_ascii=False, indent=2)
        for root in (cfg.get("local_dir") or "", cfg.get("cache_dir") or ""):
            if root:
                write_tex_file(os.path.join(root, "muc_luc.json"), payload)
        return remote
    return _muc_luc_from_local(cfg)


def git_blob_sha(data: bytes) -> str:
    """SHA blob Git — khớp sha trên GitHub tree, để khỏi tải lại file đã có."""
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _local_file_bytes(cfg: Dict[str, str], rel: str) -> bytes:
    rel_n = str(rel or "").replace("\\", "/").lstrip("/")
    for root in (cfg.get("local_dir") or "", cfg.get("cache_dir") or ""):
        if not root:
            continue
        path = os.path.join(root, rel_n.replace("/", os.sep))
        if os.path.isfile(path):
            try:
                return Path(path).read_bytes()
            except Exception:
                return b""
    return b""


_TEX_Q_ENV_RE = re.compile(r"\\begin\s*\{\s*(?:ex|bt)\s*\}", re.I)


def count_tex_question_blocks(text: str) -> int:
    """Đếm \\begin{ex} và \\begin{bt} — không tin dòng % Số câu: ở đầu file."""
    return len(_TEX_Q_ENV_RE.findall(text or ""))


_TEX_HEADER_RE = re.compile(r"%\s*(Môn|Lớp|Chương|Bài)\s*:\s*(.+)", re.I)


def meta_from_tex_header(text: str) -> Dict[str, str]:
    """Đọc % Môn / % Lớp / % Chương / % Bài ở đầu file .tex."""
    out: Dict[str, str] = {}
    key_map = {"môn": "Mon", "lớp": "Lop", "chương": "Chuong", "bài": "BaiHoc"}
    for m in _TEX_HEADER_RE.finditer(text or ""):
        field = key_map.get((m.group(1) or "").strip().lower())
        val = (m.group(2) or "").strip()
        if field and val:
            out[field] = val
            if field == "BaiHoc":
                out["De"] = val
    return out


def _blob_sha_path(cfg: Dict[str, str]) -> str:
    cache = cfg.get("cache_dir") or ""
    parent = os.path.dirname(cache.rstrip("\\/")) if cache else ""
    return os.path.join(parent or cache or ".", "blob_sha.json")


def list_github_tex_blobs(cfg: Dict[str, str]) -> Dict[str, Any]:
    """Cây GitHub: rel path trong ngan-hang → blob sha."""
    repo = cfg["repo"]
    branch = cfg["branch"]
    prefix = cfg["rel_dir"].rstrip("/") + "/"
    token = cfg.get("token") or ""
    url = f"https://api.github.com/repos/{repo}/git/trees/{urllib.parse.quote(branch)}?recursive=1"
    data = json.loads(http_get_text(url, token=token, timeout=45))
    files: Dict[str, str] = {}
    for item in data.get("tree") or []:
        if item.get("type") != "blob":
            continue
        p = str(item.get("path") or "").replace("\\", "/")
        if not p.startswith(prefix):
            continue
        rel = p[len(prefix) :].lstrip("/")
        low = rel.lower()
        if low.endswith(".tex") or low.endswith("muc_luc.json"):
            files[rel] = str(item.get("sha") or "")
    return {"files": files, "tree_sha": str(data.get("sha") or "")}


def sync_github_tex_if_changed(cfg: Dict[str, str], max_workers: int = 8) -> Dict[str, Any]:
    """Tải đúng những file .tex / muc_luc.json GitHub vừa Commit — không cần sửa số câu bằng tay."""
    token = cfg.get("token") or ""
    try:
        listing = list_github_tex_blobs(cfg)
    except Exception as e:
        return {"ok": False, "changed": 0, "error": str(e)[:220], "rels": []}
    files = listing.get("files") or {}
    tree_sha = listing.get("tree_sha") or ""
    sha_path = _blob_sha_path(cfg)
    old: Dict[str, Any] = {}
    if os.path.isfile(sha_path):
        try:
            old = json.loads(Path(sha_path).read_text(encoding="utf-8"))
        except Exception:
            old = {}
    old_files = old.get("files") or {}
    if tree_sha and old.get("tree_sha") == tree_sha:
        return {"ok": True, "changed": 0, "skipped": True, "rels": [], "muc_luc_changed": False}
    changed: List[str] = []
    for rel, sha in files.items():
        if old_files.get(rel) == sha:
            continue
        local = _local_file_bytes(cfg, rel)
        if local and git_blob_sha(local) == str(sha or ""):
            continue
        changed.append(rel)
    raw_base = (cfg.get("raw_base") or "").rstrip("/")
    dests = [d for d in (cfg.get("cache_dir") or "", cfg.get("local_dir") or "") if d]
    errors: List[str] = []
    ok_n = 0

    def one(rel: str) -> Tuple[str, Optional[str]]:
        url = raw_base + "/" + encode_github_path(rel)
        try:
            text = http_get_text(url, token=token, timeout=60)
            for dest in dests:
                write_tex_file(os.path.join(dest, rel.replace("/", os.sep)), text)
            return rel, None
        except Exception as e:
            return rel, str(e)[:220]

    if changed:
        workers = max(1, min(int(max_workers or 8), 12))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(one, rel) for rel in changed]
            for fut in as_completed(futs):
                rel, err = fut.result()
                if err:
                    errors.append(f"{rel}: {err}")
                else:
                    ok_n += 1
    try:
        os.makedirs(os.path.dirname(sha_path) or ".", exist_ok=True)
        Path(sha_path).write_text(
            json.dumps({"tree_sha": tree_sha, "files": files}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass
    return {
        "ok": True,
        "changed": ok_n,
        "rels": [r for r in changed if str(r).lower().endswith(".tex")],
        "muc_luc_changed": any(str(r).lower().endswith("muc_luc.json") for r in changed),
        "listed": len(files),
        "errors": errors[:12],
        "skipped": False,
    }


def read_or_fetch_tex(cfg: Dict[str, str], rel: str) -> str:
    """Đọc 1 file .tex. Có file local thì dùng luôn — không gọi GitHub mỗi lần mở bài."""
    rel = str(rel or "").replace("\\", "/").lstrip("/")
    local_text = ""
    local_path = ""
    for root in (cfg.get("local_dir") or "", cfg.get("cache_dir") or ""):
        if not root:
            continue
        path = os.path.join(root, rel.replace("/", os.sep))
        if os.path.isfile(path):
            local_text = Path(path).read_text(encoding="utf-8", errors="replace")
            local_path = path
            break
    fetch_remote = (os.environ.get("GITHUB_TEX_FETCH_ON_OPEN") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if local_text and not fetch_remote:
        return local_text
    remote_text = ""
    url = (cfg.get("raw_base") or "").rstrip("/") + "/" + encode_github_path(rel)
    try:
        remote_text = http_get_text(url, token=cfg.get("token") or "", timeout=20)
    except Exception:
        remote_text = ""
    n_local = count_tex_question_blocks(local_text)
    n_remote = count_tex_question_blocks(remote_text)
    if remote_text and n_remote > n_local:
        cache_dir = cfg.get("cache_dir") or ""
        if cache_dir:
            write_tex_file(os.path.join(cache_dir, rel.replace("/", os.sep)), remote_text)
        local_dir = cfg.get("local_dir") or ""
        if local_dir:
            write_tex_file(os.path.join(local_dir, rel.replace("/", os.sep)), remote_text)
        return remote_text
    if local_text:
        return local_text
    if remote_text:
        cache_dir = cfg.get("cache_dir") or ""
        if cache_dir:
            write_tex_file(os.path.join(cache_dir, rel.replace("/", os.sep)), remote_text)
        return remote_text
    if local_path:
        return local_text
    raise FileNotFoundError("Không đọc được file .tex: " + rel)


def encode_github_path(path: str) -> str:
    return "/".join(urllib.parse.quote(part, safe="-_.~") for part in path.split("/") if part)


def list_local_tex_files(*roots: str) -> List[Tuple[str, str]]:
    """Trả về [(rel posix path, abs path)], file trùng rel: root đứng trước thắng."""
    seen = set()
    out: List[Tuple[str, str]] = []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        base = Path(root)
        for p in sorted(base.rglob("*.tex")):
            rel = p.relative_to(base).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            out.append((rel, str(p)))
    return out


def read_tex_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def write_tex_file(path: str, text: str) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text or "", encoding="utf-8")


def list_github_tex_paths(cfg: Dict[str, str]) -> List[str]:
    repo = cfg["repo"]
    branch = cfg["branch"]
    prefix = cfg["rel_dir"].rstrip("/") + "/"
    token = cfg.get("token") or ""
    url = f"https://api.github.com/repos/{repo}/git/trees/{urllib.parse.quote(branch)}?recursive=1"
    try:
        data = json.loads(http_get_text(url, token=token, timeout=60))
        paths = []
        for item in data.get("tree") or []:
            p = str(item.get("path") or "").replace("\\", "/")
            if item.get("type") == "blob" and p.startswith(prefix) and p.lower().endswith(".tex"):
                paths.append(p[len(prefix) :].lstrip("/"))
        if paths:
            return sorted(set(paths))
    except Exception:
        pass
    muc_url = cfg["raw_base"].rstrip("/") + "/muc_luc.json"
    try:
        muc = json.loads(http_get_text(muc_url, token=token, timeout=30))
        paths = []
        for item in muc.get("lessons") or []:
            p = str(item.get("path") or "").replace("\\", "/").lstrip("/")
            if p.lower().endswith(".tex"):
                paths.append(p)
        return sorted(set(paths))
    except Exception as e:
        raise RuntimeError(f"Không liệt kê được file .tex trên GitHub: {e}") from e


def download_github_tex(cfg: Dict[str, str], dest_dir: str, max_workers: int = 8) -> Dict[str, Any]:
    os.makedirs(dest_dir, exist_ok=True)
    paths = list_github_tex_paths(cfg)
    token = cfg.get("token") or ""
    raw_base = cfg["raw_base"].rstrip("/")
    ok = 0
    errors: List[str] = []

    def one(rel: str) -> Tuple[str, Optional[str]]:
        url = raw_base + "/" + encode_github_path(rel)
        try:
            text = http_get_text(url, token=token, timeout=60)
            write_tex_file(os.path.join(dest_dir, rel.replace("/", os.sep)), text)
            return rel, None
        except Exception as e:
            return rel, str(e)[:220]

    workers = max(1, min(int(max_workers or 8), 12))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(one, rel) for rel in paths]
        for fut in as_completed(futs):
            rel, err = fut.result()
            if err:
                errors.append(f"{rel}: {err}")
            else:
                ok += 1

    muc_src = raw_base + "/muc_luc.json"
    try:
        write_tex_file(
            os.path.join(dest_dir, "muc_luc.json"),
            http_get_text(muc_src, token=token, timeout=30),
        )
    except Exception:
        pass

    return {
        "ok": True,
        "count_files": ok,
        "count_listed": len(paths),
        "dest": dest_dir,
        "errors": errors[:20],
        "error_count": len(errors),
        "repo": cfg.get("repo", ""),
        "branch": cfg.get("branch", ""),
    }


def copy_cache_into_local(cache_dir: str, local_dir: str) -> int:
    """Ghi đè ngan-hang local bằng bản vừa tải từ GitHub."""
    if not cache_dir or not os.path.isdir(cache_dir):
        return 0
    n = 0
    base = Path(cache_dir)
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(base)
        dest = Path(local_dir) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        n += 1
    return n


def fill_ngan_hang_from_questions(
    questions: Iterable[Dict[str, Any]],
    ngan_hang: str,
    export_fn: Callable[[List[Dict[str, Any]], str], str],
) -> Dict[str, Any]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for q in questions or []:
        if not isinstance(q, dict):
            continue
        mon = str(q.get("Mon") or "").strip()
        lop = str(q.get("Lop") or "").strip()
        chuong = str(q.get("Chuong") or "").strip()
        bai = str(q.get("BaiHoc") or "").strip()
        if not (mon and lop and chuong and bai):
            rel = "_Chua_phan_loai/de.tex"
        else:
            rel = lesson_rel_path(mon, lop, chuong, bai)
        groups.setdefault(rel, []).append(q)

    lessons = []
    ngan = Path(ngan_hang)
    ngan.mkdir(parents=True, exist_ok=True)
    for rel, qs in sorted(groups.items()):
        title = qs[0].get("BaiHoc") or rel
        tex = export_fn(qs, str(title))
        write_tex_file(str(ngan / rel.replace("/", os.sep)), tex)
        d = defaults_from_rel_path(rel)
        lessons.append(
            {
                "Mon": d["Mon"] or qs[0].get("Mon", ""),
                "Lop": d["Lop"] or qs[0].get("Lop", ""),
                "Chuong": d["Chuong"] or qs[0].get("Chuong", ""),
                "BaiHoc": d["BaiHoc"] or qs[0].get("BaiHoc", ""),
                "path": rel,
                "github": f"ngan-hang/{rel}",
                "count_questions": len(qs),
            }
        )
    muc = {"schema": 1, "count": len(lessons), "lessons": lessons}
    (ngan / "muc_luc.json").write_text(json.dumps(muc, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "count_files": len(lessons), "count_questions": sum(len(v) for v in groups.values())}
