# -*- coding: utf-8 -*-
"""Hiển thị Dạng bài tập theo từng loại và thống kê A/B/C/D đọc trực tiếp từ de.tex."""
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import jsonify, request
from app import app

def _load_index():
    p=os.path.join(app.root_path,'bank_index.json')
    try:
        with open(p,'r',encoding='utf-8') as f:return json.load(f)
    except Exception:return {'lessons':[],'total_files':0,'total_questions':0}

def _index_payload():
    out=[]
    for x in (_load_index().get('lessons') or []):
        dang=x.get('dang') or {}; rows=[]
        if isinstance(dang,dict):
            for name,n in dang.items():
                try: nn=int(n or 0)
                except Exception: nn=0
                if nn>0: rows.append({'name':str(name or 'Chưa phân dạng'),'count':nn})
        rows.sort(key=lambda z:(str(z['name'])=='Chưa phân dạng',str(z['name']).lower()))
        out.append({'path':str(x.get('path') or x.get('file') or ''),'baihoc':str(x.get('BaiHoc') or x.get('De') or ''),'questions':int(x.get('questions') or x.get('count') or 0),'dang':rows})
    return out

def _github_get_tex(path:str)->str:
    repo=(os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').strip(); token=os.getenv('GITHUB_TOKEN','').strip()
    if '/' not in repo or not token or not path.startswith('ngan-hang/'): return ''
    owner,name=repo.split('/',1)
    api=f"https://api.github.com/repos/{owner}/{name}/contents/{urllib.parse.quote(path,safe='/')}?ref=main"
    req=urllib.request.Request(api,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'luyen-de-vat-ly-dang-breakdown'})
    with urllib.request.urlopen(req,timeout=15) as r: obj=json.loads(r.read().decode('utf-8'))
    return base64.b64decode((obj.get('content') or '').replace('\n','')).decode('utf-8','replace')

def _split_ex(text):
    pat=re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}",re.I)
    return [m.group(0) for m in pat.finditer(text or '')]

def _kind(block):
    if re.search(r"\\choiceTF\b",block,re.I): return 'B'
    if re.search(r"\\shortans\b",block,re.I): return 'C'
    if re.search(r"\\choice\b",block,re.I): return 'A'
    return 'D'

def _dang(block):
    m=re.search(r"\\dangbt\s*\{([^{}]*)\}",block or '',re.I)
    return (m.group(1).strip() if m else 'Chưa phân dạng') or 'Chưa phân dạng'

def _breakdown_for_path(path):
    result={}
    for block in _split_ex(_github_get_tex(path)):
        d=_dang(block); k=_kind(block)
        result.setdefault(d,{'A':0,'B':0,'C':0,'D':0,'total':0})
        result[d][k]+=1; result[d]['total']+=1
    return result

@app.get('/github/api/dang-breakdown')
def github_dang_breakdown():
    try:
        paths=[x for x in request.args.get('paths','').split('||') if x.strip()][:50]
        items={}
        if paths:
            with ThreadPoolExecutor(max_workers=min(8,len(paths))) as pool:
                fs={pool.submit(_breakdown_for_path,p):p for p in paths}
                for f in as_completed(fs):
                    p=fs[f]
                    try: items[p]=f.result()
                    except Exception: items[p]={}
        return jsonify({'ok':True,'items':items})
    except Exception as e:return jsonify({'ok':False,'error':str(e),'items':{}}),500

JS=r'''<script data-ldvl-dang-breakdown="1">
(function(){
if(window.__LDVL_DANG_BREAKDOWN__)return;window.__LDVL_DANG_BREAKDOWN__=1;
const DATA=__DATA__;
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/gi,'d').replace(/\s+/g,' ').trim().toLowerCase();
const findHit=title=>DATA.find(x=>norm(x.baihoc)===norm(title))||DATA.find(x=>norm(x.baihoc)===norm(String(title||'').replace(/^\S+\s+/,'')));
function addCss(){if(document.getElementById('LDVL_DANG_BREAKDOWN_CSS'))return;const st=document.createElement('style');st.id='LDVL_DANG_BREAKDOWN_CSS';st.textContent=`
.ldvlDangBox{margin-top:6px;padding:8px;border:1px solid #93c5fd;border-radius:11px;background:#f8fbff}.ldvlDangHead{font-size:11px;font-weight:950;color:#1e3a8a;margin-bottom:7px}.ldvlDangGrid{display:flex;flex-direction:column;gap:5px}.ldvlDangRow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px;align-items:center;padding:6px 8px;border:1px solid #dbeafe;border-radius:9px;background:#fff;cursor:pointer}.ldvlDangRow:hover{background:#f0f7ff;border-color:#60a5fa}.ldvlDangName{font-size:11px;font-weight:850;color:#174a84;line-height:1.3}.ldvlDangMeta{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:4px}.ldvlType{display:inline-flex;align-items:center;border-radius:999px;padding:3px 6px;font-size:9.5px;font-weight:900;border:1px solid #d7dee7;background:#f8fafc;color:#475569}.ldvlType.A{background:#eff6ff;border-color:#93c5fd;color:#1d4ed8}.ldvlType.B{background:#f5f3ff;border-color:#c4b5fd;color:#6d28d9}.ldvlType.C{background:#ecfdf5;border-color:#86efac;color:#15803d}.ldvlType.D{background:#fff7ed;border-color:#fdba74;color:#c2410c}.ldvlType.total{background:#eaf2ff;border-color:#bfdbfe;color:#1e3a8a}@media(max-width:700px){.ldvlDangRow{grid-template-columns:1fr}.ldvlDangMeta{justify-content:flex-start}}`;
document.head.appendChild(st)}
function decorate(card,hit,br){if(!hit||!hit.dang||!hit.dang.length)return;const box=document.createElement('div');box.className='ldvlDangBox';let h='<div class="ldvlDangHead">🏷️ Dạng bài tập <span style="opacity:.7">— chọn một dạng để ra đề</span></div><div class="ldvlDangGrid">';for(const d of hit.dang.filter(x=>x.count>0)){const b=br[d.name]||{};const A=Number(b.A||0),B=Number(b.B||0),C=Number(b.C||0),D=Number(b.D||0),T=Number(b.total||d.count||0);h+=`<div class="ldvlDangRow" data-path="${esc(hit.path)}" data-dang="${esc(d.name)}"><div class="ldvlDangName">${esc(d.name)}</div><div class="ldvlDangMeta"><span class="ldvlType A">A ${A}</span><span class="ldvlType B">B ${B}</span><span class="ldvlType C">C ${C}</span><span class="ldvlType D">D ${D}</span><span class="ldvlType total">Tổng ${T}</span></div></div>`}h+='</div>';box.innerHTML=h;card.appendChild(box)}
async function run(){addCss();const cards=[...document.querySelectorAll('.lessonCard,.bookLessonCard')];const pairs=[];for(const card of cards){if(card.querySelector('.ldvlDangBox'))continue;const title=(card.querySelector('.lessonTitle,.bookLessonTitle')?.textContent||'').trim();const hit=findHit(title);if(hit)pairs.push([card,hit])}const paths=[...new Set(pairs.map(x=>x[1].path).filter(Boolean))].slice(0,50);if(!paths.length)return;let items={};try{const r=await fetch('/github/api/dang-breakdown?paths='+encodeURIComponent(paths.join('||')),{credentials:'same-origin'});const j=await r.json();items=j.items||{}}catch(e){}for(const [card,hit] of pairs)decorate(card,hit,items[hit.path]||{})}
document.addEventListener('click',e=>{const row=e.target.closest('.ldvlDangRow');if(!row)return;e.preventDefault();e.stopPropagation();const p=row.dataset.path||'',d=row.dataset.dang||'';if(p)location.href='/github/quan-ly?path='+encodeURIComponent(p)+'&dang='+encodeURIComponent(d)});
function start(){run();setTimeout(run,800);setTimeout(run,1800)}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();try{new MutationObserver(()=>{if(!document.querySelector('.ldvlDangBox'))run()}).observe(document.documentElement,{childList:true,subtree:true})}catch(e){}}
)();
</script>'''

@app.after_request
def inject_dang_breakdown(response):
    try:
        if request.path.startswith('/github/quan-ly') and response.content_type and 'text/html' in response.content_type:
            text=response.get_data(as_text=True)
            if 'data-ldvl-dang-breakdown="1"' not in text:
                payload=json.dumps(_index_payload(),ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
                script=JS.replace('__DATA__',payload); i=text.lower().find('</head>')
                text=text[:i]+script+text[i:] if i>=0 else script+text; response.set_data(text)
    except Exception: pass
    return response
