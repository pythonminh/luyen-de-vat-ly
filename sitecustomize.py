# -*- coding: utf-8 -*-
# Inject a compact editable classification panel into the existing GitHub question editor.
try:
    import github_question_editor as m
    if not getattr(m, '_CLASSIFY_PATCH', False) and '</script>' in m.TPL:
        js = r'''<script>
(function(){
 function v(id){var e=document.getElementById(id);return e?e.value:''}
 function grab(b,re){var m=String(b||'').match(re);return m?m[1].trim():''}
 function sync(){
   var ta=document.getElementById('qeditor');if(!ta)return;
   var b=ta.value||'';
   var kind=/\\choiceTF\b/i.test(b)?'B':(/\\shortans\b/i.test(b)?'C':(/\\choice\b/i.test(b)?'A':'D'));
   var k=document.getElementById('qmetaKind'),l=document.getElementById('qmetaLevel'),d=document.getElementById('qmetaDang'),i=document.getElementById('qmetaId');
   if(k)k.value=kind;if(l)l.value=grab(b,/%\\s*Mức\\s*:\\s*([^\\r\\n]+)/i);if(d)d.value=grab(b,/\\\\dangbt\\s*\{([^{}]*)\}/i);if(i)i.value=grab(b,/%\\s*ID\\s*:\\s*([^\\r\\n]+)/i);
 }
 function ensure(){
   if(document.getElementById('qmetaBox'))return;
   var a=document.querySelector('.editorHead');if(!a)return;
   var x=document.createElement('div');x.id='qmetaBox';x.style='margin:10px 0;padding:10px;border:1px solid #ccd6e0;border-radius:10px;background:#f8fbff';
   x.innerHTML='<b>🏷 Phân loại câu</b><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">'+
   '<label>Loại câu<select id=qmetaKind style="width:100%;padding:7px"><option>A</option><option>B</option><option>C</option><option>D</option></select></label>'+ '<label>Mức độ<select id=qmetaLevel style="width:100%;padding:7px"><option value="">—</option><option>NB</option><option>TH</option><option>VD</option><option>VDC</option></select></label></div>'+ '<label style="display:block;margin-top:8px">Dạng bài<input id=qmetaDang style="width:100%;padding:7px;box-sizing:border-box"></label>'+ '<label style="display:block;margin-top:8px">ID<input id=qmetaId style="width:100%;padding:7px;box-sizing:border-box"></label>'+ '<button id=qmetaApply type="button" style="margin-top:8px;padding:8px 12px;background:#1565c0;color:#fff;border:0;border-radius:8px;font-weight:700">↻ Ghi phân loại</button>';
   a.insertAdjacentElement('afterend',x);document.getElementById('qmetaApply').onclick=apply;
 }
 function apply(){
   var ta=document.getElementById('qeditor');if(!ta)return;var b=ta.value||'',id=v('qmetaId').trim(),lv=v('qmetaLevel').trim(),dg=v('qmetaDang').trim();
   b=b.replace(/%\\s*ID\\s*:[^\\r\\n]*\\r?\\n?/i,'').replace(/%\\s*Mức\\s*:[^\\r\\n]*\\r?\\n?/i,'').replace(/\\\\dangbt\\s*\{[^{}]*\}\\s*/ig,'');
   var p=b.search(/\\\\begin\\s*\{(?:ex|bt)\\s*\}/i),m=b.match(/\\\\begin\\s*\{(?:ex|bt)\\s*\}/i);if(p>=0){var z=[];if(id)z.push('% ID: '+id);if(lv)z.push('% Mức: '+lv);b=b.slice(0,p+m[0].length)+'\\n'+z.join('\\n')+'\\n'+b.slice(p+m[0].length);if(dg)b=b.slice(0,p)+'\\\\dangbt{'+dg+'}\\n'+b.slice(p)}
   var k=v('qmetaKind'),cm=b.match(/\\\\choiceTF\\b|\\\\choice\\b|\\\\shortans\\b/i),want={A:'\\\\choice',B:'\\\\choiceTF',C:'\\\\shortans',D:''}[k];if(cm&&want)b=b.slice(0,cm.index)+want+b.slice(cm.index+cm[0].length);if(cm&&k==='D')b=b.slice(0,cm.index)+b.slice(cm.index+cm[0].length);ta.value=b;ta.dispatchEvent(new Event('input',{bubbles:true}));sync();alert('Đã ghi phân loại vào câu. Nhấn Lưu GitHub.');
 }
 function hook(){ensure();sync();}
 document.addEventListener('DOMContentLoaded',hook);setTimeout(hook,200);setTimeout(hook,700);setTimeout(hook,1500);
})();
</script>'''
        m.TPL=m.TPL.replace('</script>',js+'</script>',1)
        m._CLASSIFY_PATCH=True
except Exception:
    pass
