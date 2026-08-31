# -*- coding: utf-8 -*-
"""Startup patches: fast catalog + per-question classification UI."""

# 1) Add editable A/B/C/D + Mức độ + Dạng + ID to the question editor.
try:
    import github_question_editor as m
    if not getattr(m, "_CLASSIFY_PATCH", False) and "</script>" in m.TPL:
        js = r'''<script data-ldvl-classify="1">
(function(){
  function val(id){var e=document.getElementById(id);return e?e.value:''}
  function grab(b,re){var m=String(b||'').match(re);return m?m[1].trim():''}
  function kind(b){if(/\\choiceTF\b/i.test(b))return 'B';if(/\\shortans\b/i.test(b))return 'C';if(/\\choice\b/i.test(b))return 'A';return 'D'}
  function ensure(){
    if(document.getElementById('qmetaBox'))return;
    var a=document.querySelector('.editorHead,.editor-head'); if(!a)return;
    var x=document.createElement('div'); x.id='qmetaBox';
    x.style='margin:10px 0;padding:12px;border:1px solid #cbd5e1;border-radius:10px;background:#f8fbff';
    x.innerHTML='<b>🏷 Phân loại câu</b>'+
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">'+
      '<label>Loại câu<select id="qmetaKind" style="width:100%;padding:7px"><option>A</option><option>B</option><option>C</option><option>D</option></select></label>'+
      '<label>Mức độ<select id="qmetaLevel" style="width:100%;padding:7px"><option value="">—</option><option>NB</option><option>TH</option><option>VD</option><option>VDC</option></select></label></div>'+
      '<label style="display:block;margin-top:8px">Dạng bài<input id="qmetaDang" style="width:100%;padding:7px;box-sizing:border-box"></label>'+
      '<label style="display:block;margin-top:8px">ID<input id="qmetaId" style="width:100%;padding:7px;box-sizing:border-box"></label>'+
      '<button id="qmetaApply" type="button" style="margin-top:9px;padding:8px 12px;background:#1565c0;color:white;border:0;border-radius:8px;font-weight:700">↻ Ghi phân loại</button>';
    a.insertAdjacentElement('afterend',x);
    document.getElementById('qmetaApply').onclick=apply;
  }
  function sync(){
    ensure(); var ta=document.getElementById('qeditor'); if(!ta)return; var b=ta.value||'';
    var e=document.getElementById('qmetaKind'); if(e)e.value=kind(b);
    e=document.getElementById('qmetaLevel'); if(e)e.value=grab(b,/%\s*Mức\s*:\s*([^\r\n]+)/i);
    e=document.getElementById('qmetaDang'); if(e)e.value=grab(b,/\\dangbt\s*\{([^{}]*)\}/i);
    e=document.getElementById('qmetaId'); if(e)e.value=grab(b,/%\s*ID\s*:\s*([^\r\n]+)/i);
  }
  function apply(){
    var ta=document.getElementById('qeditor'); if(!ta)return; var b=ta.value||'';
    var id=val('qmetaId').trim(), lv=val('qmetaLevel').trim(), dg=val('qmetaDang').trim(), k=val('qmetaKind');
    b=b.replace(/%\s*ID\s*:[^\r\n]*\r?\n?/i,'').replace(/%\s*Mức\s*:[^\r\n]*\r?\n?/i,'').replace(/\\dangbt\s*\{[^{}]*\}\s*/ig,'');
    var bm=b.match(/\\begin\s*\{(?:ex|bt)\s*\}/i);
    if(bm){var lines=[];if(id)lines.push('% ID: '+id);if(lv)lines.push('% Mức: '+lv);b=b.slice(0,bm.index+bm[0].length)+'\n'+lines.join('\n')+'\n'+b.slice(bm.index+bm[0].length);if(dg)b=b.slice(0,bm.index)+'\\dangbt{'+dg+'}\n'+b.slice(bm.index)}
    var cm=b.match(/\\choiceTF\b|\\choice\b|\\shortans\b/i), want={A:'\\choice',B:'\\choiceTF',C:'\\shortans',D:''}[k];
    if(cm&&want)b=b.slice(0,cm.index)+want+b.slice(cm.index+cm[0].length);else if(cm&&k==='D')b=b.slice(0,cm.index)+b.slice(cm.index+cm[0].length);
    ta.value=b; ta.dispatchEvent(new Event('input',{bubbles:true})); sync();
  }
  function hook(){ensure();sync()}
  document.addEventListener('DOMContentLoaded',hook); setTimeout(hook,200);setTimeout(hook,700);setTimeout(hook,1500);
})();
</script>'''
        m.TPL = m.TPL.replace("</script>", js + "</script>", 1)
        m._CLASSIFY_PATCH = True
except Exception:
    pass

# 2) Fast catalog: consume the bank_index already injected by wsgi.py.
#    It replaces the long Google-Sheet wait on the Mục lục screen.
try:
    from app import app
    FAST_JS = r'''<script data-ldvl-fast-catalog="1">
(function(){
  if(window.__LDVL_FAST_CATALOG__)return;
  window.__LDVL_FAST_CATALOG__=true;
  function esc(v){return String(v==null?'':v).replace(/[&<>\"]/g,function(s){return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[s]})}
  function host(){
    var ids=['publicCatalogContent','deCatalogContent','catalogContent','mucLucContent','deMucLucContent'];
    for(var i=0;i<ids.length;i++){var e=document.getElementById(ids[i]);if(e)return e;}
    var all=document.querySelectorAll('body *');
    for(var j=0;j<all.length;j++){var t=(all[j].textContent||'').trim();if(t.indexOf('Đang tải dữ liệu Sheet')>=0||t.indexOf('Đang tải mục lục đề')>=0)return all[j];}
    return null;
  }
  function render(h,d){
    if(!h||!d||!Array.isArray(d.lessons)||!d.lessons.length)return false;
    var g={}; d.lessons.forEach(function(x){var k=(x.Mon||'Khác')+'|'+(x.Lop||'')+'|'+(x.Chuong||'');(g[k]||(g[k]=[])).push(x)});
    var html='<div style="padding:12px"><div style="font-size:18px;font-weight:800">📚 Mục lục — GitHub</div><div style="font-size:12px;color:#64748b;margin:4px 0 10px">'+Number(d.total_files||d.lessons.length)+' file · '+Number(d.total_questions||0)+' câu</div>';
    Object.keys(g).forEach(function(k){var a=k.split('|'),list='';g[k].forEach(function(x){var p=x.path||'';list+='<div style="margin:4px 0"><a href="/github/questions?branch=main&path='+encodeURIComponent(p)+'" style="text-decoration:none;font-weight:600;color:#174a84">'+esc(x.BaiHoc||x.De||p)+'</a> <span style="font-size:11px;color:#64748b">· '+Number(x.questions||x.count||0)+' câu</span></div>'});html+='<details style="border:1px solid #d7dee8;border-radius:8px;margin:5px 0;padding:6px"><summary><b>'+esc(a[0])+'</b> · Lớp '+esc(a[1])+' · '+esc(a[2])+'</summary><div style="padding:5px 8px">'+list+'</div></details>'});
    html+='</div>'; h.innerHTML=html; return true;
  }
  function run(){var d=window.__LDVL_BANK_INDEX__;if(!d){setTimeout(run,150);return}var h=host();if(!h){setTimeout(run,150);return}render(h,d)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
  setTimeout(run,300);setTimeout(run,1000);setTimeout(run,2500);
})();
</script>'''
    @app.after_request
    def _ldvl_fast_catalog(response):
        try:
            if response.content_type and 'text/html' in response.content_type:
                text=response.get_data(as_text=True)
                if 'data-ldvl-fast-catalog="1"' not in text:
                    low=text.lower(); i=low.rfind('</body>')
                    text=text[:i]+FAST_JS+text[i:] if i>=0 else text+FAST_JS
                    response.set_data(text)
        except Exception:
            pass
        return response
except Exception:
    pass
