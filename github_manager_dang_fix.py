# -*- coding: utf-8 -*-
"""GitHub manager UI enhancement: show all Dạng bài tập from bank_index.json.
Runs only on /github/quan-ly and leaves the main app/học sinh UI untouched.
"""
from __future__ import annotations
import json, os, html
from flask import request
from app import app


def _load_index():
    p=os.path.join(app.root_path,'bank_index.json')
    try:
        with open(p,'r',encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'lessons':[],'total_files':0,'total_questions':0}


def _payload():
    data=_load_index()
    out=[]
    for x in data.get('lessons') or []:
        dang=x.get('dang') or {}
        if isinstance(dang,dict):
            rows=[]
            for name,n in dang.items():
                try: nn=int(n or 0)
                except Exception: nn=0
                rows.append({'name':str(name or 'Chưa phân dạng'),'count':nn})
            rows.sort(key=lambda z:(str(z['name'])=='Chưa phân dạng', -z['count'], str(z['name']).lower()))
        else:
            rows=[]
        out.append({
            'path':str(x.get('path') or x.get('file') or ''),
            'mon':str(x.get('Mon') or ''),
            'lop':str(x.get('Lop') or ''),
            'chuong':str(x.get('Chuong') or ''),
            'baihoc':str(x.get('BaiHoc') or x.get('De') or ''),
            'questions':int(x.get('questions') or x.get('count') or 0),
            'dang':rows,
        })
    return out

JS = r'''<script data-ldvl-dang-fix="1">
(function(){
if(window.__LDVL_DANG_FIX__)return;window.__LDVL_DANG_FIX__=1;
const DATA=__DATA__;
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/gi,'d').replace(/\s+/g,' ').trim().toLowerCase();
function addCss(){if(document.getElementById('LDVL_DANG_FIX_CSS'))return;const st=document.createElement('style');st.id='LDVL_DANG_FIX_CSS';st.textContent=`
.ldvlDangFix{margin-top:4px;padding:7px 8px;border:1px solid #bfdbfe;border-radius:10px;background:#f8fbff}
.ldvlDangFixTitle{font-size:11px;font-weight:950;color:#1e3a8a;margin-bottom:6px;display:flex;align-items:center;gap:5px}
.ldvlDangFixList{display:flex;flex-wrap:wrap;gap:5px}
.ldvlDangFixBtn{border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:999px;padding:4px 8px;font-size:10.5px;font-weight:850;cursor:pointer;line-height:1.25}
.ldvlDangFixBtn:hover{background:#dbeafe}
.ldvlDangFixBtn.uncls{border-color:#fdba74;background:#fff7ed;color:#9a3412}
.ldvlDangFixBtn b{margin-left:3px}
`;
document.head.appendChild(st)}
function getPathHint(){try{return new URL(location.href).searchParams.get('path')||''}catch(e){return''}}
function install(){
 addCss();
 const cards=[...document.querySelectorAll('.lessonCard,.bookLessonCard')];
 if(!cards.length)return false;
 cards.forEach(card=>{
   if(card.querySelector('.ldvlDangFix'))return;
   const title=(card.querySelector('.lessonTitle,.bookLessonTitle')?.textContent||'').trim();
   const sub=(card.querySelector('.lessonSub,.bookLessonSub')?.textContent||'').trim();
   const hit=DATA.find(x=>norm(x.baihoc)===norm(title))||DATA.find(x=>norm(x.baihoc)===norm(title.replace(/^\S+\s+/,'')));
   if(!hit||!hit.dang||!hit.dang.length)return;
   const visible=hit.dang.filter(d=>d.count>0);
   if(!visible.length)return;
   const box=document.createElement('div');box.className='ldvlDangFix';
   box.innerHTML='<div class="ldvlDangFixTitle">🏷️ Dạng bài tập <span style="opacity:.7">('+visible.length+' dạng)</span></div><div class="ldvlDangFixList">'+
      visible.map(d=>'<button type="button" class="ldvlDangFixBtn '+(norm(d.name)==='chua phan dang'?'uncls':'')+'" data-path="'+esc(hit.path)+'" data-dang="'+esc(d.name)+'">'+esc(d.name)+' <b>'+d.count+'</b></button>').join('')+
      '</div>';
   card.appendChild(box);
 });
 return true;
}
document.addEventListener('click',e=>{const b=e.target.closest('.ldvlDangFixBtn');if(!b)return;e.preventDefault();e.stopPropagation();const p=b.getAttribute('data-path')||'';const d=b.getAttribute('data-dang')||'';if(p){location.href='/github/quan-ly?path='+encodeURIComponent(p)+'&dang='+encodeURIComponent(d)}});
function start(){install();setTimeout(install,120);setTimeout(install,500);setTimeout(install,1200)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
try{new MutationObserver(install).observe(document.documentElement,{childList:true,subtree:true})}catch(e){}
})();
</script>'''

@app.after_request
def inject_dang_fix(response):
    try:
        if request.path.startswith('/github/quan-ly') and response.content_type and 'text/html' in response.content_type:
            text=response.get_data(as_text=True)
            if 'data-ldvl-dang-fix="1"' not in text:
                payload=json.dumps(_payload(),ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
                script=JS.replace('__DATA__',payload)
                i=text.lower().find('</head>')
                if i>=0:text=text[:i]+script+text[i:]
                else:text=script+text
                response.set_data(text)
    except Exception:
        pass
    return response
