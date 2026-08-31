# -*- coding: utf-8 -*-
"""GitHub-only content mode.

Nguồn chính cho nội dung ngân hàng:
  GitHub / ngan-hang/*.tex -> bank_index.json

Module này chỉ áp dụng cho các màn hình nội dung GitHub/Ra đề.
Không thay thế dữ liệu tài khoản/kết quả học viên đang dùng ở phần khác.
"""
from __future__ import annotations

from flask import request
from app import app


_GITHUB_ONLY_PATHS = (
    "/ra-de",
    "/ra-de/",
    "/ra-de/generate",
    "/github",
    "/github/",
    "/github/questions",
    "/github/questions-save",
    "/github/edit",
    "/github/save",
)


def _github_content_page() -> bool:
    p = request.path or "/"
    return p.startswith(_GITHUB_ONLY_PATHS)


@app.after_request
def inject_github_only_mode(response):
    """Mark content pages as GitHub-only and stop accidental Sheet requests there."""
    try:
        if not (response.content_type and "text/html" in response.content_type):
            return response
        if not _github_content_page():
            return response

        text = response.get_data(as_text=True)
        if "data-ldvl-github-source-only=\"1\"" in text:
            return response

        # Insert early in <head>, before the existing page scripts execute.
        script = r'''<script data-ldvl-github-source-only="1">
(function(){
  window.__LDVL_SOURCE_MODE__='GITHUB';
  window.__LDVL_SOURCE_LABEL__='✓ Dữ liệu GitHub';

  function isGoogleSheetUrl(u){
    try{
      var x=new URL(u,location.href), h=(x.hostname||'').toLowerCase();
      return h.indexOf('script.google.com')>=0 ||
             h.indexOf('sheets.googleapis.com')>=0 ||
             h.indexOf('docs.google.com')>=0;
    }catch(e){return false;}
  }

  // Các trang Ra đề/GitHub không được phép gọi Google Sheet.
  var oldFetch=window.fetch;
  window.fetch=function(input,init){
    var u=(typeof input==='string')?input:(input&&input.url)||'';
    if(isGoogleSheetUrl(u)){
      return Promise.reject(new Error('LDVL_GITHUB_ONLY: Google Sheet disabled on this page'));
    }
    return oldFetch.apply(this,arguments);
  };

  var oldOpen=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(method,url){
    if(isGoogleSheetUrl(url)){
      this.__ldvlBlocked=true;
      return;
    }
    return oldOpen.apply(this,arguments);
  };
  var oldSend=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send=function(){
    if(this.__ldvlBlocked){
      try{this.abort()}catch(e){}
      return;
    }
    return oldSend.apply(this,arguments);
  };

  function cleanStatus(){
    var all=document.querySelectorAll('*');
    for(var i=0;i<all.length;i++){
      var t=(all[i].textContent||'').trim();
      if(t.indexOf('Đang tải dữ liệu Sheet')>=0 || t.indexOf('Đang kết nối máy chủ')>=0){
        all[i].textContent='✓ Dữ liệu GitHub sẵn sàng';
        all[i].style.color='#188038';
        all[i].style.fontWeight='700';
      }
    }
  }
  document.addEventListener('DOMContentLoaded',function(){cleanStatus();setTimeout(cleanStatus,200);setTimeout(cleanStatus,800);});
  setTimeout(cleanStatus,1500);
})();
</script>'''
        low = text.lower()
        i = low.find("</head>")
        text = text[:i] + script + text[i:] if i >= 0 else script + text
        response.set_data(text)
    except Exception:
        pass
    return response
