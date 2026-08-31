# -*- coding: utf-8 -*-
"""Force GitHub as the catalog source on the existing app UI.

The existing visual UI is preserved. Catalog/meta requests are redirected to
GitHub-derived data, and stale Google Sheet loading labels are neutralized.
Google Sheet remains backup-only and is never used by this bridge.
"""
from __future__ import annotations

import json
import os
import re
from flask import jsonify, request
from app import app

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "bank_index.json")


def load_catalog():
    try:
        with open(INDEX, "r", encoding="utf-8") as f:
            idx = json.load(f)
    except Exception:
        idx = {"source": "GitHub", "total_files": 0, "total_questions": 0, "lessons": []}
    rows = []
    for x in idx.get("lessons") or []:
        path = str(x.get("path") or x.get("file") or "")
        rows.append({
            "Mon": str(x.get("Mon") or ""),
            "Khoi": str(x.get("Lop") or ""),
            "Lop": str(x.get("Lop") or ""),
            "Chuong": str(x.get("Chuong") or ""),
            "Bai": str(x.get("BaiHoc") or x.get("De") or ""),
            "BaiHoc": str(x.get("BaiHoc") or ""),
            "De": str(x.get("De") or x.get("BaiHoc") or path),
            "MaDe": path,
            "File": path,
            "GitHubPath": path,
            "SoCau": int(x.get("questions") or x.get("count") or 0),
            "DangBaiTap": x.get("dang") or {},
            "FilterCounts": {},
            "Nguon": "GitHub",
        })
    return idx, rows


@app.get('/api/github/catalog')
def github_catalog():
    idx, rows = load_catalog()
    return jsonify({
        "loading": False,
        "source": "GitHub",
        "catalog_source": "GitHub / bank_index.json + ngan-hang/*.tex",
        "count_questions": int(idx.get("total_questions") or 0),
        "count_files": int(idx.get("total_files") or 0),
        "catalog": rows,
        "data": rows,
        "items": rows,
        "lessons": rows,
        "user": {},
    })


def _github_meta():
    return github_catalog()


# Replace likely catalog/meta endpoints already registered by the legacy UI.
# This is deliberately conservative: only routes containing meta/catalog are replaced.
for rule in list(app.url_map.iter_rules()):
    r = str(rule.rule).lower()
    ep = str(rule.endpoint).lower()
    if rule.rule in ('/api/github/catalog',):
        continue
    if r.startswith('/api/') and ('meta' in r or 'catalog' in r) and 'github' not in r:
        app.view_functions[rule.endpoint] = _github_meta
    elif r == '/api/meta' or ep in ('api_meta', 'meta_api'):
        app.view_functions[rule.endpoint] = _github_meta


BRIDGE_SCRIPT = r'''<script id="ldvl-github-bridge">
(function(){
  if(window.__LDVL_GITHUB_BRIDGE__) return;
  window.__LDVL_GITHUB_BRIDGE__ = true;
  function cleanLoading(){
    document.querySelectorAll('body *').forEach(function(el){
      if(el.children.length===0){
        var t=(el.textContent||'').trim();
        if(/Đang tải dữ liệu Sheet|Đang tải mục lục đề/i.test(t)){
          el.textContent='✓ Đang tải dữ liệu từ GitHub...';
          el.style.color='#166534';
          el.style.fontWeight='700';
        }
      }
    });
  }
  function patchText(){
    document.querySelectorAll('body *').forEach(function(el){
      if(el.children.length===0 && /Google Sheet/i.test(el.textContent||'')){
        el.textContent=(el.textContent||'').replace(/Google Sheet/gi,'GitHub (backup)');
      }
    });
  }
  cleanLoading(); patchText();
  setTimeout(cleanLoading,500); setTimeout(cleanLoading,1500); setTimeout(patchText,1500);
  try{ new MutationObserver(function(){cleanLoading();patchText();}).observe(document.body,{childList:true,subtree:true}); }catch(e){}
})();
</script>''';


@app.after_request
def inject_github_bridge(response):
    try:
        if request.path == '/' and response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)
            if 'ldvl-github-bridge' not in text:
                i = text.lower().find('</head>')
                text = text[:i] + BRIDGE_SCRIPT + text[i:] if i >= 0 else BRIDGE_SCRIPT + text
                response.set_data(text)
            response.headers['X-LDVL-Source'] = 'GitHub'
    except Exception:
        pass
    return response

app.config['GITHUB_SOURCE_PRIMARY'] = True
app.config['GOOGLE_SHEET_BANK_BACKUP_ONLY'] = True
