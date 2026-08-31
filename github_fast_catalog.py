# -*- coding: utf-8 -*-
"""GitHub-only catalog overlay.

The catalog is rendered directly from bank_index.json and keeps the visual language
of app1: subject tabs, book-style hierarchy, lesson cards, tags and action buttons.
It does not render the old plain details/summary list.
"""
from __future__ import annotations

import html
import json
import os
from app import app


def _load_index():
    path = os.path.join(app.root_path, "bank_index.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"total_files": 0, "total_questions": 0, "lessons": []}


STYLE = r"""
<style id="LDVL_GITHUB_BOOK_CATALOG_V2">
#ldvlFastGithubCatalog{margin:10px 0 18px}
.ldgv2-intro{margin:10px 0 12px;padding:13px 14px;border:1px solid #dbeafe;border-radius:16px;background:linear-gradient(180deg,#eff6ff,#fff);box-shadow:0 1px 5px #1d4ed811}
.ldgv2-title{font-size:16px;font-weight:950;color:#1e3a8a;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ldgv2-sub{margin-top:6px;color:#475569;font-size:12px;line-height:1.5}
.ldgv2-stats{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}.ldgv2-stat{border:1px solid #bfdbfe;background:#fff;border-radius:999px;padding:4px 9px;font-size:11px;font-weight:900;color:#1e40af}
.ldgv2-tools{display:flex;flex-wrap:wrap;gap:7px;margin:8px 0 12px;align-items:center}.ldgv2-tools input,.ldgv2-tools select{min-height:38px;padding:7px 10px;border:1px solid #bfdbfe;border-radius:10px;background:#fff;color:#0f172a;font-weight:700}.ldgv2-tools input{min-width:260px;flex:1}.ldgv2-tools select{min-width:150px}
.ldgv2-subject{margin:13px 0 17px}.ldgv2-subject-head{padding:11px 13px;border-radius:14px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:950;font-size:17px;display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;box-shadow:0 2px 8px #1d4ed833}.ldgv2-subject-head small{font-size:12px;opacity:.95;font-weight:800}
.ldgv2-grade{margin:10px 0 12px;border:1px solid #cbd5e1;border-radius:16px;background:#fff;overflow:hidden;box-shadow:0 1px 4px #0f172a0f}.ldgv2-grade-head{padding:10px 12px;background:#f1f5f9;color:#0f172a;font-weight:950;display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap}.ldgv2-grade-head small{font-size:12px;color:#64748b}
.ldgv2-chapter{margin:10px;border:1px solid #bfdbfe;border-radius:14px;overflow:hidden;background:#f8fbff}.ldgv2-chapter-head{padding:9px 11px;background:#dbeafe;color:#1e3a8a;font-weight:950;display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap}.ldgv2-chapter-head small{font-size:12px;color:#475569;font-weight:800}
.ldgv2-lessons{padding:9px;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:9px}.ldgv2-lesson{border:1px solid #e2e8f0;border-radius:14px;background:#fff;padding:11px;box-shadow:0 1px 3px #0f172a0d;display:flex;flex-direction:column;gap:7px}.ldgv2-lesson:hover{border-color:#93c5fd;box-shadow:0 4px 14px #1d4ed817;transform:translateY(-1px)}.ldgv2-lesson-title{font-weight:950;color:#0f172a;line-height:1.32}.ldgv2-lesson-sub{font-size:12px;color:#64748b;line-height:1.4}.ldgv2-tags{display:flex;flex-wrap:wrap;gap:5px}.ldgv2-tag{border:1px solid #cbd5e1;background:#f8fafc;border-radius:999px;padding:3px 7px;font-size:11px;font-weight:850;color:#334155}.ldgv2-tag.nb{background:#f0fdf4;border-color:#86efac;color:#166534}.ldgv2-tag.th{background:#eff6ff;border-color:#93c5fd;color:#1d4ed8}.ldgv2-tag.vd{background:#fff7ed;border-color:#fdba74;color:#c2410c}.ldgv2-tag.vdc{background:#fef2f2;border-color:#fca5a5;color:#991b1b}.ldgv2-dbt{display:flex;flex-wrap:wrap;gap:5px}.ldgv2-dbt span{border:1px solid #fde68a;background:#fffbeb;color:#92400e;border-radius:999px;padding:4px 8px;font-size:10px;font-weight:850}
.ldgv2-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:2px}.ldgv2-btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:9px;padding:6px 9px;font-size:11px;font-weight:900;text-decoration:none}.ldgv2-btn.primary{background:#1d4ed8;color:#fff;border-color:#1d4ed8}.ldgv2-btn:hover{filter:brightness(1.03);transform:translateY(-1px)}
.ldgv2-empty{padding:14px;border:1px dashed #cbd5e1;border-radius:12px;color:#64748b;background:#f8fafc}
html[data-theme='dark'] .ldgv2-intro{background:linear-gradient(180deg,#172554,#0f172a);border-color:#1d4ed8}.ldgv2-intro .ldgv2-title{color:#bfdbfe}.ldgv2-stat,.ldgv2-tools input,.ldgv2-tools select{background:#0f172a;color:#dbeafe;border-color:#334155}.ldgv2-grade,.ldgv2-lesson{background:#111827;border-color:#334155}.ldgv2-grade-head{background:#1e293b;color:#e5e7eb}.ldgv2-chapter{background:#0f172a;border-color:#1d4ed8}.ldgv2-chapter-head{background:#1e3a5f;color:#bfdbfe}.ldgv2-lesson-title{color:#e5e7eb}.ldgv2-tag{background:#1e293b;border-color:#475569;color:#cbd5e1}
@media(max-width:760px){.ldgv2-tools input{min-width:0;width:100%}.ldgv2-tools select{flex:1;min-width:130px}.ldgv2-lessons{grid-template-columns:1fr;padding:7px}.ldgv2-lesson{padding:9px}.ldgv2-subject-head{font-size:15px}.ldgv2-grade-head,.ldgv2-chapter-head{padding:8px 10px}}
</style>
"""


JS = r"""
<script id="LDVL_GITHUB_BOOK_CATALOG_V2_JS">
(function(){
  if(window.__LDVL_GITHUB_BOOK_CATALOG_V2__)return;
  window.__LDVL_GITHUB_BOOK_CATALOG_V2__=true;
  const INDEX=__INDEX__;
  const lessons=Array.isArray(INDEX.lessons)?INDEX.lessons:[];
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  function norm(s){try{return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/gi,'d').toLowerCase().trim()}catch(e){return String(s||'').toLowerCase().trim()}}
  function n(x){return Number(x.questions||x.count||0)||0}
  function levelTags(x){
    const fc=x.FilterCounts&&x.FilterCounts.level?x.FilterCounts.level:{};
    return ['NB','TH','VD','VDC'].filter(k=>Number(fc[k]||0)>0).map(k=>'<span class="ldgv2-tag '+k.toLowerCase()+'">'+k+' · '+Number(fc[k]||0)+'</span>').join('');
  }
  function dbtTags(x){
    const d=x.dang&&typeof x.dang==='object'?x.dang:{};
    return Object.keys(d).filter(k=>String(k).trim()).slice(0,5).map(k=>'<span>'+esc(k)+' · '+Number(d[k]||0)+'</span>').join('');
  }
  function group(list,keyfn){const m={};list.forEach(x=>{const k=keyfn(x)||'Chưa rõ';(m[k]||(m[k]=[])).push(x)});return m}
  function lessonCard(x){
    const p=x.path||x.file||''; const title=x.BaiHoc||x.De||'Bài chưa đặt tên'; const q=n(x);
    const url='/github/quan-ly?path='+encodeURIComponent(p);
    const dbt=dbtTags(x); const lev=levelTags(x);
    return '<article class="ldgv2-lesson">'+
      '<div class="ldgv2-lesson-title">'+esc(title)+'</div>'+
      '<div class="ldgv2-lesson-sub">'+esc(x.Mon||'')+' · Lớp '+esc(x.Lop||'')+' · '+esc(x.Chuong||'')+'</div>'+
      '<div class="ldgv2-tags"><span class="ldgv2-tag"><b>'+q+'</b> câu</span>'+(lev||'')+'</div>'+
      (dbt?'<div class="ldgv2-dbt">'+dbt+'</div>':'')+
      '<div class="ldgv2-actions"><a class="ldgv2-btn primary" href="'+url+'">✏️ Mở bài</a><a class="ldgv2-btn" href="'+url+'#questions">👁 Xem câu</a></div>'+
      '</article>';
  }
  function render(list){
    const box=document.getElementById('ldvlFastGithubCatalog'); if(!box)return;
    const q=list.reduce((a,x)=>a+n(x),0), mons=[...new Set(list.map(x=>x.Mon).filter(Boolean))], lops=[...new Set(list.map(x=>x.Lop).filter(Boolean))], ch=[...new Set(list.map(x=>x.Chuong).filter(Boolean))], bai=[...new Set(list.map(x=>x.BaiHoc||x.De).filter(Boolean))];
    let h='<div class="ldgv2-intro"><div class="ldgv2-title">📚 Mục lục kiểu sách <span class="ldgv2-stat">GitHub</span></div><div class="ldgv2-sub">Đọc trực tiếp từ <b>bank_index.json</b> và các file <b>ngan-hang/*.tex</b>. Cấu trúc giống giao diện luyện đề chính: <b>Môn → Lớp → Chương → Bài</b>. Bấm <b>Mở bài</b> để xem/sửa nội dung.</div><div class="ldgv2-stats"><span class="ldgv2-stat">'+mons.length+' môn</span><span class="ldgv2-stat">'+lops.length+' lớp</span><span class="ldgv2-stat">'+ch.length+' chương</span><span class="ldgv2-stat">'+bai.length+' bài</span><span class="ldgv2-stat">'+q+' câu</span></div></div>';
    h+='<div class="ldgv2-tools"><input id="ldgv2Search" placeholder="🔎 Tìm bài, chương, dạng bài..." autocomplete="off"><select id="ldgv2Mon"><option value="">Tất cả môn</option></select><select id="ldgv2Lop"><option value="">Tất cả lớp</option></select></div>';
    const byMon=group(list,x=>x.Mon||'Khác');
    Object.keys(byMon).sort((a,b)=>norm(a).localeCompare(norm(b),'vi')).forEach(mon=>{
      const monList=byMon[mon], mq=monList.reduce((a,x)=>a+n(x),0);
      h+='<section class="ldgv2-subject"><div class="ldgv2-subject-head"><span>'+esc(mon)+'</span><small>'+monList.length+' bài · '+mq+' câu</small></div>';
      const byLop=group(monList,x=>x.Lop||'Không rõ lớp');
      Object.keys(byLop).sort((a,b)=>String(a).localeCompare(String(b),'vi')).forEach(lop=>{
        const ll=byLop[lop], lq=ll.reduce((a,x)=>a+n(x),0);
        h+='<div class="ldgv2-grade"><div class="ldgv2-grade-head"><span>Khối/Lớp '+esc(lop)+'</span><small>'+ll.length+' bài · '+lq+' câu</small></div>';
        const byCh=group(ll,x=>x.Chuong||'Chưa rõ chương');
        Object.keys(byCh).sort((a,b)=>norm(a).localeCompare(norm(b),'vi')).forEach(ch=>{
          const cc=byCh[ch], cq=cc.reduce((a,x)=>a+n(x),0);
          h+='<div class="ldgv2-chapter"><div class="ldgv2-chapter-head"><span>'+esc(ch)+'</span><small>'+cc.length+' bài · '+cq+' câu</small></div><div class="ldgv2-lessons">'+cc.map(lessonCard).join('')+'</div></div>';
        });
        h+='</div>';
      });
      h+='</section>';
    });
    if(!list.length)h+='<div class="ldgv2-empty">Không có bài phù hợp với bộ lọc hiện tại.</div>';
    box.innerHTML=h;
    const monSel=document.getElementById('ldgv2Mon'), lopSel=document.getElementById('ldgv2Lop'), search=document.getElementById('ldgv2Search');
    [...new Set(lessons.map(x=>x.Mon).filter(Boolean))].sort((a,b)=>norm(a).localeCompare(norm(b),'vi')).forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;monSel.appendChild(o)});
    [...new Set(lessons.map(x=>x.Lop).filter(Boolean))].sort().forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent='Lớp '+v;lopSel.appendChild(o)});
    const apply=()=>{const s=norm(search.value),m=monSel.value,l=lopSel.value;const out=lessons.filter(x=>(!m||x.Mon===m)&&(!l||x.Lop===l)&&(!s||(norm((x.Mon||'')+' '+(x.Lop||'')+' '+(x.Chuong||'')+' '+(x.BaiHoc||x.De||'')+' '+Object.keys(x.dang||{}).join(' ')).includes(s))));render(out)};
    monSel.onchange=apply;lopSel.onchange=apply;search.oninput=apply;
  }
  function install(){
    let target=document.getElementById('catalog');
    if(!target){
      const all=document.querySelectorAll('body *');
      for(const e of all){const t=(e.textContent||'').trim();if(t==='Đang tải mục lục đề...'||t==='Đang tải mục lục đề…'){target=e.parentElement||e;break}}
    }
    if(!target)return false;
    if(!document.getElementById('ldvlFastGithubCatalog')){target.innerHTML='<section id="ldvlFastGithubCatalog"></section>';target.insertAdjacentHTML('beforebegin','__STYLE__')}
    render(lessons); return true;
  }
  function start(){
    install();
    setTimeout(install,200);setTimeout(install,800);setTimeout(install,1800);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  try{new MutationObserver(function(){if(!document.getElementById('ldvlFastGithubCatalog'))install()}).observe(document.documentElement,{childList:true,subtree:true})}catch(e){}
})();
</script>
"""


@app.after_request
def inject_fast_catalog(response):
    try:
        if response.content_type and "text/html" in response.content_type:
            text = response.get_data(as_text=True)
            if "LDVL_GITHUB_BOOK_CATALOG_V2_JS" not in text:
                data = _load_index()
                payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
                script = JS.replace("__INDEX__", payload).replace("__STYLE__", STYLE.replace("</style>", "</style>"))
                pos = text.lower().find("</head>")
                if pos >= 0:
                    text = text[:pos] + STYLE + script + text[pos:]
                else:
                    text = STYLE + script + text
                response.set_data(text)
    except Exception:
        pass
    return response
