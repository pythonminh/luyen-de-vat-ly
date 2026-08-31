# -*- coding: utf-8 -*-
"""GitHub-only content mode.

Nguồn chính cho nội dung ngân hàng:
  GitHub / ngan-hang/*.tex -> bank_index.json

Các trang nội dung không gọi Google Sheet. Dữ liệu tài khoản/kết quả
không bị thay đổi ở các route riêng của chúng.
"""
from __future__ import annotations

from flask import request
from app import app


# Trang chính của app cũng chứa Mục lục nên phải đưa vào chế độ GitHub-only.
# Không chặn /login, /register và các route tài khoản/kết quả.
_GITHUB_ONLY_PATHS = (
    "/",
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
    return p == "/" or any(p.startswith(x) for x in _GITHUB_ONLY_PATHS if x != "/")


@app.after_request
def inject_github_only_mode(response):
    """Khóa Google Sheet trên các trang nội dung và ưu tiên GitHub index."""
    try:
        if not (response.content_type and "text/html" in response.content_type):
            return response
        if not _github_content_page():
            return response

        text = response.get_data(as_text=True)
        if 'data-ldvl-github-source-only="1"' in text:
            return response

        # Đặt script ở đầu <head>: chạy trước các JS tải dữ liệu của trang.
        script = r'''<script data-ldvl-github-source-only="1">
(function(){
  'use strict';
  window.__LDVL_SOURCE_MODE__='GITHUB';
  window.__LDVL_SOURCE_LABEL__='✓ Dữ liệu GitHub sẵn sàng';
  window.__LDVL_GOOGLE_SHEET_DISABLED__=true;

  function isGoogle(u){
    try{
      var x=new URL(String(u||''),location.href), h=(x.hostname||'').toLowerCase();
      return h.indexOf('script.google.com')>=0 ||
             h.indexOf('sheets.googleapis.com')>=0 ||
             h.indexOf('docs.google.com')>=0;
    }catch(e){ return false; }
  }

  // Chặn fetch Google Sheet.
  var oldFetch=window.fetch;
  if(oldFetch && !oldFetch.__ldvlWrapped){
    function blockedFetch(input,init){
      var u=(typeof input==='string')?input:(input&&input.url)||'';
      if(isGoogle(u)) return Promise.reject(new Error('LDVL_GITHUB_ONLY: Google Sheet disabled'));
      return oldFetch.apply(this,arguments);
    }
    blockedFetch.__ldvlWrapped=true;
    window.fetch=blockedFetch;
  }

  // Chặn XMLHttpRequest Google Sheet.
  var oldOpen=XMLHttpRequest.prototype.open;
  if(!oldOpen.__ldvlWrapped){
    XMLHttpRequest.prototype.open=function(method,url){
      if(isGoogle(url)){ this.__ldvlGoogleBlocked=true; return; }
      return oldOpen.apply(this,arguments);
    };
    XMLHttpRequest.prototype.open.__ldvlWrapped=true;
  }
  var oldSend=XMLHttpRequest.prototype.send;
  if(!oldSend.__ldvlWrapped){
    XMLHttpRequest.prototype.send=function(){
      if(this.__ldvlGoogleBlocked){ try{this.abort();}catch(e){} return; }
      return oldSend.apply(this,arguments);
    };
    XMLHttpRequest.prototype.send.__ldvlWrapped=true;
  }

  // Chặn thẻ script/link/img/iframe được thêm động trỏ tới Google.
  function blockNode(node){
    if(!node || node.nodeType!==1) return;
    var attrs=['src','href','data-src'];
    for(var i=0;i<attrs.length;i++){
      var v=node.getAttribute && node.getAttribute(attrs[i]);
      if(v && isGoogle(v)){
        try{ node.removeAttribute(attrs[i]); }catch(e){}
        try{ node.type='text/plain'; }catch(e){}
        node.setAttribute('data-ldvl-blocked','1');
      }
    }
  }
  function scanScripts(){
    try{ document.querySelectorAll('script[src],link[href],iframe[src],img[src]').forEach(blockNode); }catch(e){}
  }

  // Giữ trạng thái GitHub, không cho JS cũ đổi ngược lại "Đang tải dữ liệu Sheet".
  function cleanStatus(){
    try{
      var all=document.querySelectorAll('*');
      for(var i=0;i<all.length;i++){
        var e=all[i], t=(e.textContent||'').trim();
        if(t==='Đang tải dữ liệu Sheet...' || t.indexOf('Đang tải dữ liệu Sheet')===0 || t.indexOf('Đang kết nối máy chủ')===0){
          e.textContent='✓ Dữ liệu GitHub sẵn sàng';
          e.style.color='#188038';
          e.style.fontWeight='700';
        }
      }
    }catch(e){}
  }

  function start(){
    scanScripts();
    cleanStatus();
    try{
      var mo=new MutationObserver(function(records){
        for(var i=0;i<records.length;i++){
          var r=records[i];
          if(r.type==='childList') r.addedNodes.forEach(blockNode);
        }
        cleanStatus();
      });
      mo.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
      window.__LDVL_GITHUB_OBSERVER__=mo;
    }catch(e){}
    setTimeout(scanScripts,50);
    setTimeout(cleanStatus,50);
    setTimeout(scanScripts,300);
    setTimeout(cleanStatus,300);
    setTimeout(scanScripts,1000);
    setTimeout(cleanStatus,1000);
    setTimeout(scanScripts,2500);
    setTimeout(cleanStatus,2500);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start);
  else start();
})();
</script>'''
        low = text.lower()
        i = low.find('</head>')
        text = text[:i] + script + text[i:] if i >= 0 else script + text
        response.set_data(text)
    except Exception:
        pass
    return response
