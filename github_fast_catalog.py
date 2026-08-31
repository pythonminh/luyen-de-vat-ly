# -*- coding: utf-8 -*-
"""Fast GitHub-only catalog for the home/Mục lục page.
The catalog is rendered from local bank_index.json and never waits for Google Sheet.
"""
from __future__ import annotations
import json, os, html
from app import app


def _load_index():
    p = os.path.join(app.root_path, "bank_index.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"total_files": 0, "total_questions": 0, "lessons": []}


def _catalog_html(data):
    lessons = data.get("lessons") or []
    groups = {}
    for x in lessons:
        key = (x.get("Mon") or "Khác", x.get("Lop") or "", x.get("Chuong") or "Chưa phân chương")
        groups.setdefault(key, []).append(x)
    parts = []
    for (mon, lop, chuong), items in sorted(groups.items(), key=lambda z: tuple(str(v) for v in z[0])):
        total = sum(int(x.get("questions") or x.get("count") or 0) for x in items)
        rows = []
        for x in items:
            p = x.get("path") or x.get("file") or ""
            title = x.get("BaiHoc") or x.get("De") or os.path.basename(p) or "Bài chưa đặt tên"
            n = int(x.get("questions") or x.get("count") or 0)
            rows.append(f'<li><a href="/github/quan-ly?path={html.escape(p, quote=True)}">{html.escape(title)}</a> <span>({n} câu)</span></li>')
        parts.append(
            '<details class="ldvl-node">'
            f'<summary><b>{html.escape(mon)}</b> · Lớp {html.escape(lop)} · {html.escape(chuong)} <span>— {total} câu</span></summary>'
            '<ul>' + ''.join(rows) + '</ul></details>'
        )
    return ''.join(parts)


CATALOG_JS = r'''<script data-ldvl-fast-github="1">
(function(){
  if(window.__LDVL_FAST_GITHUB__) return; window.__LDVL_FAST_GITHUB__=true;
  var INDEX=__INDEX__;
  function esc(s){return String(s==null?'':s).replace(/[&<>\"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]||c;});}
  function render(){
    var box=document.getElementById('ldvlFastGithubCatalog');
    var groups={};
    (INDEX.lessons||[]).forEach(function(x){var k=(x.Mon||'Khác')+'|'+(x.Lop||'')+'|'+(x.Chuong||'Chưa phân chương');(groups[k]||(groups[k]=[])).push(x);});
    var h='<div class="ldvl-fast-head"><b>📚 MỤC LỤC ĐỀ — GITHUB</b><span>'+Number(INDEX.total_files||0)+' file</span><span>'+Number(INDEX.total_questions||0)+' câu</span><em>✓ Dữ liệu GitHub</em></div>';
    Object.keys(groups).sort(function(a,b){return a.localeCompare(b,'vi')}).forEach(function(k){var a=k.split('|'),items=groups[k],total=0,lis='';items.forEach(function(x){var n=Number(x.questions||x.count||0);total+=n;var p=x.path||x.file||'',t=x.BaiHoc||x.De||p;lis+='<li><a href="/github/quan-ly?path='+encodeURIComponent(p)+'">'+esc(t)+'</a> <span>('+n+' câu)</span></li>';});h+='<details class="ldvl-node"><summary><b>'+esc(a[0])+'</b> · Lớp '+esc(a[1])+' · '+esc(a[2])+' <span>— '+total+' câu</span></summary><ul>'+lis+'</ul></details>';});
    box.innerHTML=h;
  }
  function install(){
    var all=document.querySelectorAll('body *'), target=null;
    for(var i=0;i<all.length;i++){var t=(all[i].textContent||'').trim();if(t==='Đang tải mục lục đề...' || t==='Đang tải mục lục đề…'){target=all[i];break;}}
    if(!target){target=document.querySelector('[id*=mucLuc],[id*=catalog],[class*=catalog]');}
    if(target){var host=target.parentElement||target;host.innerHTML='<section id="ldvlFastGithubCatalog"></section>';render();return true;}
    var main=document.querySelector('main')||document.body;var s=document.createElement('section');s.id='ldvlFastGithubCatalog';s.style='margin:14px 16px;padding:12px;border:1px solid #c8dbef;border-radius:12px;background:#f8fbff;font-family:Arial,sans-serif';main.appendChild(s);render();return true;
  }
  function clean(){
    var all=document.querySelectorAll('*'); for(var i=0;i<all.length;i++){var e=all[i],t=(e.textContent||'').trim();if(t==='Đang tải dữ liệu Sheet...'||t.indexOf('Đang tải dữ liệu Sheet')===0||t.indexOf('Đang kết nối máy chủ')===0)e.textContent='✓ Dữ liệu GitHub sẵn sàng';}
  }
  function blockGoogle(){
    function isG(u){try{var h=new URL(String(u||''),location.href).hostname.toLowerCase();return h.indexOf('google.com')>=0||h.indexOf('googleusercontent.com')>=0;}catch(e){return false;}}
    var f=window.fetch;if(f&&!f.__ldvl){var nf=function(i,o){var u=typeof i==='string'?i:(i&&i.url)||'';if(isG(u))return Promise.reject(new Error('GitHub-only: Google disabled'));return f.apply(this,arguments)};nf.__ldvl=true;window.fetch=nf;}
    var xo=XMLHttpRequest.prototype.open;if(xo&&!xo.__ldvl){XMLHttpRequest.prototype.open=function(m,u){if(isG(u)){this.__ldvlBlocked=true;return;}return xo.apply(this,arguments)};XMLHttpRequest.prototype.open.__ldvl=true;}
  }
  function start(){blockGoogle();clean();install();setTimeout(function(){clean();install();},100);setTimeout(function(){clean();install();},500);setTimeout(function(){clean();install();},1500);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  try{new MutationObserver(function(){clean();if(!document.getElementById('ldvlFastGithubCatalog'))install();}).observe(document.documentElement,{childList:true,subtree:true});}catch(e){}
})();
</script>'''


@app.after_request
def inject_fast_catalog(response):
    try:
        if response.content_type and 'text/html' in response.content_type:
            data = _load_index()
            payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</','<\\/')
            script = CATALOG_JS.replace('__INDEX__', payload)
            text = response.get_data(as_text=True)
            if 'data-ldvl-fast-github="1"' not in text:
                low = text.lower(); i = low.find('</head>')
                if i >= 0: text = text[:i] + script + text[i:]
                else: text = script + text
                response.set_data(text)
    except Exception:
        pass
    return response
