"""V308 visual layer for the existing Flask application.

The backend/routes remain in app.py. This module only injects the V308
CSS/JS into HTML responses so the existing application keeps its behavior.
"""

from __future__ import annotations

from flask import make_response

from app import app as app

_V308_HEAD = """
<style id="v308-status-style">
#v308BuildStatus{position:fixed;right:12px;bottom:12px;z-index:2147483647;padding:7px 11px;border-radius:999px;font:700 12px/1.2 Arial,sans-serif;background:#1d4ed8;color:#fff;box-shadow:0 2px 10px rgba(0,0,0,.2)}
#v308BuildStatus.ok{background:#15803d}
#v308BuildStatus.err{background:#b91c1c;max-width:520px;border-radius:10px}
</style>
<script>
(function(){
  function addStatus(){
    if(document.getElementById("v308BuildStatus")) return;
    var b=document.createElement("div");
    b.id="v308BuildStatus";
    b.textContent="🔧 V308: đang kiểm tra JavaScript…";
    document.body.appendChild(b);
    return b;
  }
  function check(){
    var b=addStatus();
    if(!b) return;
    var bad=[];
    var scripts=document.querySelectorAll("script:not([src])");
    for(var i=0;i<scripts.length;i++){
      var s=scripts[i].textContent||"";
      if(!s.trim()) continue;
      try{ new Function(s); }catch(e){ bad.push("script #"+(i+1)+": "+(e&&e.message?e.message:String(e))); }
    }
    var els=document.querySelectorAll("[onclick],[onchange],[oninput],[onkeydown],[onsubmit]");
    for(var j=0;j<els.length;j++){
      var attrs=["onclick","onchange","oninput","onkeydown","onsubmit"];
      for(var k=0;k<attrs.length;k++){
        var a=els[j].getAttribute(attrs[k]);
        if(!a) continue;
        try{ new Function("event",a); }catch(e2){ bad.push(attrs[k]+" ở #"+(j+1)+": "+(e2&&e2.message?e2.message:String(e2))); }
      }
    }
    if(bad.length){
      b.className="err";
      b.textContent="❌ V308 JS lỗi: "+bad[0];
      console.error("[V308 DIAGNOSTIC]",bad);
    }else{
      b.className="ok";
      b.textContent="✅ V308: JavaScript hợp lệ";
      setTimeout(function(){ if(b&&b.parentNode)b.parentNode.removeChild(b); },5000);
    }
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",check,false);
  else setTimeout(check,0);
})();
</script>
<link rel="stylesheet" href="/static/v308.css?v=313">
<script defer src="/static/v308.js?v=313"></script>
"""


@app.after_request
def _inject_v308(response):
    """Add V308 assets to every HTML response; never touch JSON/API data."""
    try:
        resp = make_response(response)
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type:
            return resp

        body = resp.get_data(as_text=True)
        if "v308.css?v=313" in body:
            return resp

        lower = body.lower()
        marker = "</head>"
        if marker in lower:
            idx = lower.find(marker)
            body = body[:idx] + _V308_HEAD + body[idx:]
        else:
            body = _V308_HEAD + body

        resp.set_data(body)
        return resp
    except Exception:
        return response


@app.route("/ui-v308-preview")
def ui_v308_preview():
    """Standalone visual preview; safe to remove after UI approval."""
    return """<!doctype html>
<html lang='vi'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Luyen De Vat Ly - V313 Preview</title>
<link rel='stylesheet' href='/static/v308.css?v=313'>
<script defer src='/static/v308.js?v=313'></script>
</head>
<body class='v308-preview'>
<main class='v308-preview-shell'>
  <section class='v308-hero'>
    <div class='v308-brand-mark'>V</div>
    <div>
      <p class='v308-eyebrow'>LOP HOC THAY MINH</p>
      <h1>LUYEN DE VAT LY</h1>
      <p class='v308-subtitle'>Giao dien V313 - hien dai, ro rang, toi uu cho hoc sinh va giao vien.</p>
    </div>
  </section>
  <section class='v308-grid'>
    <article class='v308-card v308-card-accent'><span>01</span><strong>Kho de</strong><small>De luyen tap theo lop, chuong va muc do.</small><button type='button'>Xem kho de</button></article>
    <article class='v308-card'><span>02</span><strong>Luyen de</strong><small>Giao dien lam bai tap trung, dong ho va bang cau hoi.</small><button type='button'>Bat dau</button></article>
    <article class='v308-card'><span>03</span><strong>Ket qua</strong><small>Theo doi diem so, tien do va cac chu de can on.</small><button type='button'>Xem ket qua</button></article>
    <article class='v308-card'><span>04</span><strong>Tro ly AI</strong><small>Goi y phuong phap va ho tro giai bai.</small><button type='button'>Mo AI</button></article>
  </section>
</main>
</body>
</html>"""
