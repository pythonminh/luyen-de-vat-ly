# -*- coding: utf-8 -*-
"""Compatibility API for the safe per-question editor."""
from __future__ import annotations
import base64, json, os, urllib.request, urllib.error, urllib.parse
from github_safe_editor import bp

API = 'https://api.github.com'

def gh(path: str, method: str = 'GET', body=None):
    token = os.getenv('GITHUB_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Chưa có GITHUB_TOKEN trên Render.')
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'luyen-de-vat-ly',
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode('utf-8')).get('message', str(e))
        except Exception:
            msg = str(e)
        raise RuntimeError(f'GitHub API {e.code}: {msg}')

def repo():
    return (os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').split('/', 1)

def fetch_file(path: str, branch: str = 'main'):
    owner, name = repo()
    q = f'/repos/{owner}/{name}/contents/{urllib.parse.quote(path, safe="/")}?ref={urllib.parse.quote(branch)}'
    d = gh(q)
    content = base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')
    return d, content

__all__ = ['bp', 'gh', 'repo', 'fetch_file']
