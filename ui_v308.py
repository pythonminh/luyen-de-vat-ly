"""V308 visual layer for the existing Flask application."""
from __future__ import annotations

import re
from flask import make_response
from app import app as app

_V308_HEAD = r'''
<style id="v308-status-style">
#v308BuildStatus{position:fixed;right:12px;bottom:12px;z-index:2147483647;padding:8px 11px;border-radius:10px;font:700 12px/1.35 Arial,sans-serif;background:#1d4ed8;color:#fff;box-shadow:0 2px 12px rgba(0,0,0,.22);max-width:720px;white-space:pre-wrap}
#v308BuildStatus.ok{background:#15803d}#v308BuildStatus.err{background:#b91c1c}
</style>
<script>
(function(){
 function boot(){
  if(!document.body)return;
  var b=document.getElementById('v308BuildStatus');
  if(!b){b=document.createElement('div');b.id='v308BuildStatus';b.textContent='🔧 V315: đang kiểm tra JavaScript…';document.body.appendChild(b)}
  var bad=[];
  var ss=document.querySelectorAll('script:not([src])');
  for(var i=0;i<ss.length;i++){
   var s=ss[i].textContent||''; if(!s.trim())continue;
   try{new Function(s)}catch(e){bad.push('script #'+(i+1)+': '+(e&&e.message?e.message:String(e)))}
  }
  var aa=document.querySelectorAll('[onclick],[onchange],[oninput],[onkeydown],[onsubmit]');
  var attrs=['onclick','onchange','oninput','onkeydown','onsubmit'];
  for(var j=0;j<aa.length;j++)for(var k=0;k<attrs.length;k++){
   var a=aa[j].getAttribute(attrs[k]);if(!a)continue;
   try{new Function('event',a)}catch(e2){bad.push(attrs[k]+' #'+(j+1)+': '+(e2&&e2.message?e2.message:String(e2)))}
  }
  if(bad.length){b.className='err';b.textContent='❌ V315 JS lỗi: '+bad[0];console.error('[V315]',bad)}
  else{b.className='ok';b.textContent='✅ V315: JavaScript hợp lệ';setTimeout(function(){if(b.parentNode)b.parentNode.removeChild(b)},5000)}
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else setTimeout(boot,0);
})();
</script>
<link rel="stylesheet" href="/static/v308.css?v=315">
<script defer src="/static/v308.js?v=315"></script>
'''


def _repair_inline_js(html: str) -> str:
    """Fix JS emitted by the large APP_HTML raw string.

    A backslash immediately followed by a physical newline is illegal inside
    a JavaScript regex literal. The app historically contains several such
    sequences (for example /\\s*\\ followed by a line break). Convert only
    inline script bodies; leave normal HTML/text untouched.
    """
    def repl(m):
        body = m.group(1)
        body = body.replace('\\\n', '\\n')
        return '<script' + m.group(0).split('<script',1)[1].split('>',1)[0] + '>' + body + '</script>'

    # Keep attributes and script tags intact; only repair script contents.
    return re.sub(r'<script(?![^>]*\bsrc\s*=)[^>]*>([\\s\\S]*?)</script>', repl, html, flags=re.I)


@app.after_request
def _inject_v308(response):
    try:
        resp = make_response(response)
        if 'text/html' not in (resp.headers.get('Content-Type') or '').lower():
            return resp
        body = resp.get_data(as_text=True)
        body = _repair_inline_js(body)
        if '/static/v308.css?v=315' not in body:
            marker='</head>'
            low=body.lower()
            if marker in low:
                i=low.find(marker)
                body=body[:i]+_V308_HEAD+body[i:]
            else:
                body=_V308_HEAD+body
        resp.set_data(body)
        return resp
    except Exception:
        return response


@app.route('/ui-v308-preview')
def ui_v308_preview():
    return '''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Luyện đề Vật lý - V315 Preview</title><link rel="stylesheet" href="/static/v308.css?v=315"><script defer src="/static/v308.js?v=315"></script></head><body class="v308-preview"><main class="v308-preview-shell"><section class="v308-hero"><div class="v308-brand-mark">V</div><div><p class="v308-eyebrow">LOP HOC THAY MINH</p><h1>LUYEN DE VAT LY</h1><p class="v308-subtitle">Giao dien V315.</p></div></section></main></body></html>'''
