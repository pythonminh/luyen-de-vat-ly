# -*- coding: utf-8 -*-
"""Ngân hàng đề GitHub: một module, đọc .tex cục bộ, ghi thẳng GitHub."""
from __future__ import annotations
import base64, html, json, os, re, time, urllib.error, urllib.parse, urllib.request
from flask import Blueprint, Response, jsonify, request
from app import app

bp=Blueprint('github_bank_fast',__name__)
ROOT=os.path.dirname(os.path.abspath(__file__))
REPO=(os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').strip()
BRANCH=(os.getenv('GITHUB_BRANCH') or 'main').strip() or 'main'
TOKEN=(os.getenv('GITHUB_TOKEN') or '').strip()
CACHE={'at':0.0,'rows':None}
TTL=60

TYPES={'A':'Trắc nghiệm','B':'Đúng / Sai','C':'Trả lời ngắn','D':'Tự luận'}

def clean(v): return str(v or '').strip()
def esc(v): return html.escape(str(v or ''),quote=True)
def valid_path(p): return p.startswith('ngan-hang/') and p.endswith('.tex') and '..' not in p

def index_data():
    p=os.path.join(ROOT,'bank_index.json')
    try:
        with open(p,'r',encoding='utf-8') as f:return json.load(f)
    except Exception:return {'total_files':0,'total_questions':0,'lessons':[]}

def local_tex(path):
    if not valid_path(path): raise ValueError('Đường dẫn .tex không hợp lệ')
    p=os.path.join(ROOT,path)
    with open(p,'r',encoding='utf-8') as f:return f.read()

def blocks(text):
    pat=re.compile(r'\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}',re.I)
    ms=list(pat.finditer(text or '')); out=[]; prev=0
    for m in ms:
        b=m.group(0); pre=text[prev:m.start()]
        dm=list(re.finditer(r'\\dangbt\s*\{([^{}]*)\}',pre,re.I))
        d=clean(dm[-1].group(1)) if dm else 'Chưa phân dạng'
        if not d or d.lower() in ('chưa có dạng','chua co dang','chưa phân dạng','chua phan dang'): d='Chưa phân dạng'
        tm='B'
        if re.search(r'\\shortans\b',b,re.I): tm='C'
        elif re.search(r'\\choiceTF\b',b,re.I): tm='B'
        elif re.search(r'\\choice\b',b,re.I): tm='A'
        else: tm='D'
        lm=re.search(r'%\s*Mức\s*:\s*([^\r\n%]+)',b,re.I)
        lv=clean(lm.group(1)).upper() if lm else ''
        im=re.search(r'%\s*ID\s*:\s*([^\r\n%]+)',b,re.I)
        qid=clean(im.group(1)) if im else ''
        title=''
        xm=re.search(r'\\begin\s*\{\s*ex\s*\}([\s\S]*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{\s*ex\s*\})',b,re.I)
        if xm:
            title=re.sub(r'%[^\r\n]*','',xm.group(1)); title=re.sub(r'\s+',' ',title).strip()
        out.append({'text':b,'dang':d,'kind':tm,'level':lv,'id':qid,'title':title[:260],'image':bool(re.search(r'\\begin\s*\{\s*tikzpicture|\\includegraphics',b,re.I)),'start':m.start(),'end':m.end()})
        prev=m.end()
    return out

def parse(path):
    text=local_tex(path); qs=blocks(text); dm={}; total={k:0 for k in 'ABCD'}
    levels={k:0 for k in ('NB','TH','VD','VDC')}
    for q in qs:
        total[q['kind']]+=1; dm.setdefault(q['dang'],{'total':0,'A':0,'B':0,'C':0,'D':0}); dm[q['dang']]['total']+=1; dm[q['dang']][q['kind']]+=1
        for lv in levels:
            if re.search(r'\b'+lv+r'\b',q['level']): levels[lv]+=1
    return text,qs,{'types':total,'levels':{k:v for k,v in levels.items() if v},'dang':dm}

def catalog():
    now=time.time()
    if CACHE['rows'] is not None and now-CACHE['at']<TTL:return CACHE['rows']
    idx=index_data(); rows=[]
    for x in idx.get('lessons') or []:
        path=clean(x.get('github') or x.get('path') or x.get('file'))
        if not valid_path(path):continue
        try:
            text,qs,stats=parse(path)
        except Exception:
            text,qs,stats='',[],{'types':{'A':0,'B':0,'C':0,'D':0},'levels':{},'dang':{}}
        rows.append({'Mon':clean(x.get('Mon')),'Lop':clean(x.get('Lop')),'Chuong':clean(x.get('Chuong')),'BaiHoc':clean(x.get('BaiHoc') or x.get('De')),'path':path,'count':len(qs) or int(x.get('questions') or x.get('count_questions') or x.get('count') or 0),'types':stats['types'],'levels':stats['levels'],'dang':stats['dang'],'Nguon':'GitHub'})
    CACHE['rows']=rows;CACHE['at']=now;return rows

def gh_json(path,method='GET',payload=None):
    if not TOKEN:raise RuntimeError('Render chưa có GITHUB_TOKEN')
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    req=urllib.request.Request('https://api.github.com'+path,data=data,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl-bank-fast','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:m=json.loads(e.read().decode()).get('message',str(e))
        except Exception:m=str(e)
        raise RuntimeError(f'GitHub API {e.code}: {m}')

def get_sha(path):
    owner,repo=REPO.split('/',1)
    p=f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe="/")}?ref={urllib.parse.quote(BRANCH)}'
    return clean(gh_json(p).get('sha'))

def save(path,text,sha,msg):
    owner,repo=REPO.split('/',1)
    p=f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path,safe="/")}'
    body={'message':msg or 'Cập nhật file .tex','content':base64.b64encode(text.encode()).decode(),'branch':BRANCH,'sha':sha}
    return gh_json(p,'PUT',body)

@bp.get('/github/quan-ly')
def page():return Response(PAGE,mimetype='text/html')

@bp.get('/github/api/catalog-fast')
def api_catalog():
    r=catalog();idx=index_data();return jsonify({'ok':True,'source':'GitHub','total_files':int(idx.get('total_files') or len(r)),'total_questions':sum(x['count'] for x in r),'lessons':r})

@bp.get('/github/api/tex-fast')
def api_tex():
    p=clean(request.args.get('path'))
    try:
        text,qs,stats=parse(p);sha=get_sha(p)
        return jsonify({'ok':True,'path':p,'sha':sha,'text':text,'questions':qs,'stats':stats})
    except Exception as e:return jsonify({'ok':False,'error':str(e)}),400

@bp.post('/github/api/save-tex-fast')
def api_save():
    d=request.get_json(silent=True) or {};p=clean(d.get('path'));text=d.get('text');sha=clean(d.get('sha'))
    if not valid_path(p) or not isinstance(text,str) or not sha:return jsonify({'ok':False,'error':'Thiếu path/text/sha'}),400
    try:
        r=save(p,text,sha,clean(d.get('message')));CACHE['at']=0
        # Cập nhật file cục bộ ngay để lần mở tiếp theo thấy dữ liệu mới.
        try:
            fp=os.path.join(ROOT,p);os.makedirs(os.path.dirname(fp),exist_ok=True)
            with open(fp,'w',encoding='utf-8') as f:f.write(text)
        except Exception:pass
        return jsonify({'ok':True,'commit':clean((r.get('commit') or {}).get('sha'))})
    except Exception as e:return jsonify({'ok':False,'error':str(e)}),409

app.register_blueprint(bp)

PAGE=r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ngân hàng đề GitHub</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f8fc;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#1769d2;color:#fff;padding:12px 18px}.brand{font-weight:950;font-size:20px}.sub{font-size:11px;opacity:.9}.wrap{max-width:1550px;margin:auto;padding:12px}.tools{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:9px}.btn{border:1px solid #cbd7e4;background:#fff;color:#174a84;padding:8px 11px;border-radius:9px;font-weight:850;cursor:pointer}.primary{background:#1769d2;color:#fff;border-color:#1769d2}.filters{display:grid;grid-template-columns:1.7fr repeat(4,1fr);gap:8px;background:#fff;border:1px solid #d7e1eb;border-radius:14px;padding:10px}.field label{font-size:10px;font-weight:900;color:#64748b;display:block;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px}.intro{margin-top:9px;padding:10px 12px;border:1px solid #c7defa;background:linear-gradient(#eff6ff,#fff);border-radius:14px}.pill{display:inline-block;border:1px solid #bfdbfe;background:#fff;color:#1d4ed8;border-radius:999px;padding:4px 7px;font-size:10px;font-weight:900;margin:2px}.subject{margin-top:10px}.subjectHead{padding:10px 12px;border-radius:12px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:950;display:flex;justify-content:space-between}.grade{margin-top:8px;border:1px solid #d0dae5;border-radius:13px;background:#fff;overflow:hidden}.gradeHead{padding:8px 11px;background:#f1f5f9;font-weight:900}.chapter{margin:8px;border:1px solid #c8ddf6;border-radius:11px;overflow:hidden;background:#f8fbff}.chapterHead{padding:8px 10px;background:#dbeafe;color:#1e3a8a;font-weight:950}.grid{padding:8px;display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:8px}.lesson{border:1px solid #dce5ee;border-radius:12px;background:#fff;padding:9px}.title{font-weight:950;line-height:1.3}.muted{font-size:11px;color:#64748b}.tags{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0}.tag{padding:3px 6px;border:1px solid #d7e0e8;border-radius:999px;background:#f8fafc;font-size:9.5px;font-weight:900}.dbt{margin-top:5px;border:1px solid #d3e4f8;border-radius:9px;background:#f8fbff;padding:6px}.dbtHead{font-size:10px;font-weight:950;color:#1e3a8a;margin-bottom:4px}.dbtRow{display:flex;justify-content:space-between;gap:7px;align-items:center;padding:5px 6px;border:1px solid #dbeafe;background:#fff;border-radius:7px;margin:3px 0;cursor:pointer}.dbtRow:hover{background:#eff6ff;border-color:#60a5fa}.dbtName{font-size:10px;font-weight:850;line-height:1.3}.counts{display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end}.c{font-size:8.5px;padding:2px 4px;border-radius:999px;border:1px solid #d1d9e2;font-weight:900}.a{background:#eff6ff;color:#1d4ed8;border-color:#93c5fd}.b{background:#f5f3ff;color:#6d28d9;border-color:#c4b5fd}.cc{background:#ecfdf5;color:#15803d;border-color:#86efac}.d{background:#fff7ed;color:#c2410c;border-color:#fdba74}.sum{background:#eaf2ff;color:#1e3a8a;border-color:#bfdbfe}.actions{display:flex;gap:5px;margin-top:7px;flex-wrap:wrap}.empty{text-align:center;padding:30px;color:#64748b}.modal{position:fixed;inset:0;background:#0f172a99;display:flex;align-items:center;justify-content:center;padding:14px;z-index:99}.hide{display:none}.box{width:min(1450px,97vw);height:min(91vh,920px);background:#fff;border-radius:14px;overflow:hidden;display:flex;flex-direction:column}.mh{padding:10px 13px;background:#eef6ff;border-bottom:1px solid #d2e1f0;display:flex;justify-content:space-between;gap:8px}.mb{display:grid;grid-template-columns:330px 1fr;min-height:0;flex:1}.ql{overflow:auto;padding:7px;border-right:1px solid #dbe4ed}.qi{padding:7px;border:1px solid #e0e7ef;border-radius:8px;margin:4px 0;cursor:pointer}.qi:hover,.qi.on{background:#eff6ff;border-color:#8bb8e8}.qn{font-weight:950;font-size:10px;color:#145bb0}.qt{font-size:10px;line-height:1.35}.qm{font-size:9px;color:#64748b;margin-top:2px}.ed{padding:10px;display:flex;flex-direction:column;min-width:0}.meta{display:grid;grid-template-columns:1fr 1fr;gap:6px}.meta input{padding:7px;border:1px solid #cbd5e1;border-radius:7px}.code{margin-top:7px;flex:1;min-height:0;resize:none;border:1px solid #cbd5e1;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.foot{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.ok{padding:7px 9px;background:#ecfdf5;border:1px solid #86efac;color:#166534;border-radius:8px;font-size:11px}.err{padding:7px 9px;background:#fff1f2;border:1px solid #fecaca;color:#b42318;border-radius:8px;font-size:11px}@media(max-width:850px){.filters{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}.mb{grid-template-columns:1fr}.ql{max-height:230px;border-right:0;border-bottom:1px solid #dbe4ed}.meta{grid-template-columns:1fr}}
</style></head><body><div class="top"><div class="brand">📚 Ngân hàng đề — GitHub</div><div class="sub">Nguồn chính: bank_index.json + ngan-hang/*.tex · Google Sheet không dùng</div></div><div class="wrap"><div class="tools"><button class="btn primary" onclick="load()">↻ Làm mới</button><button class="btn" onclick="location.href='/'">⌂ Trang chính</button><span id="status" class="muted"></span></div><div class="filters"><div class="field"><label>Tìm bài / chương / dạng</label><input id="s" oninput="render()" placeholder="Tìm nhanh..."></div><div class="field"><label>Môn</label><select id="m" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="l" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="ch" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Dạng câu</label><select id="typ" onchange="render()"><option value="">A/B/C/D</option><option value="A">A · Trắc nghiệm</option><option value="B">B · Đúng/Sai</option><option value="C">C · Trả lời ngắn</option><option value="D">D · Tự luận</option></select></div></div><div id="intro" class="intro"></div><div id="cat"></div></div><div id="modal" class="modal hide"><div class="box"><div class="mh"><div><b id="mt"></b><div id="ms" class="muted"></div></div><button class="btn" onclick="closeM()">Đóng</button></div><div class="mb"><div id="ql" class="ql"></div><div class="ed"><div class="meta"><input id="qid" placeholder="ID"><input id="qlevel" placeholder="Mức độ"></div><textarea id="code" class="code" spellcheck="false"></textarea><div class="foot"><button class="btn" onclick="saveQ()">💾 Lưu trực tiếp GitHub</button><button class="btn" onclick="reloadQ()">↻ Đọc lại</button><button class="btn" onclick="closeM()">Hủy</button></div><div id="es" class="hide"></div></div></div></div></div><script>
let D=[],DET=null,PATH='',SHA='',ACTIVE=0;const $=id=>document.getElementById(id);function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function api(u,o){return fetch(u,o).then(async r=>{let j=await r.json();if(!r.ok||j.ok===false)throw Error(j.error||'Lỗi');return j})}function setOpts(id,vals){let e=$(id),old=e.value;let a=[...new Set(vals.filter(Boolean))].sort((x,y)=>x.localeCompare(y,'vi'));e.innerHTML='<option value="">Tất cả</option>'+a.map(x=>'<option>'+esc(x)+'</option>').join('');if(a.includes(old))e.value=old}function load(){ $('status').textContent='⏳ Đọc GitHub .tex…';api('/github/api/catalog-fast?t='+Date.now()).then(j=>{D=j.lessons||[];setOpts('m',D.map(x=>x.Mon));setOpts('l',D.map(x=>x.Lop));setOpts('ch',D.map(x=>x.Chuong));$('intro').innerHTML='<b>📚 Mục lục kiểu sách</b> <span class="pill">'+j.total_files+' file</span><span class="pill">'+j.total_questions+' câu</span><span class="pill">✓ GitHub</span>';render();$('status').textContent='✓ Đã nạp từ GitHub'}).catch(e=>$('status').textContent='❌ '+e.message)}function render(){let q=($('s').value||'').toLowerCase(),m=$('m').value,l=$('l').value,ch=$('ch').value,typ=$('typ').value;let list=D.filter(x=>(!m||x.Mon===m)&&(!l||x.Lop===l)&&(!ch||x.Chuong===ch)&&(!typ||x.types[typ]>0)&&(!q||(x.BaiHoc+' '+x.Chuong+' '+Object.keys(x.dang).join(' ')).toLowerCase().includes(q)));if(!list.length){$('cat').innerHTML='<div class="empty">Không có bài phù hợp.</div>';return}let H='';let mons=[...new Map(list.map(x=>[x.Mon,1])).keys()];for(let mon of mons){let ml=list.filter(x=>x.Mon===mon);H+='<section class="subject"><div class="subjectHead"><span>'+esc(mon)+'</span><span>'+ml.reduce((a,x)=>a+x.count,0)+' câu</span></div>';let ls=[...new Set(ml.map(x=>x.Lop))];for(let lop of ls){let ll=ml.filter(x=>x.Lop===lop);H+='<div class="grade"><div class="gradeHead">Khối '+esc(lop)+'</div>';let cs=[...new Set(ll.map(x=>x.Chuong))];for(let c of cs){let cl=ll.filter(x=>x.Chuong===c);H+='<div class="chapter"><div class="chapterHead">'+esc(c)+'</div><div class="grid">';for(let x of cl){let rows=Object.entries(x.dang).filter(([n])=>!q||n.toLowerCase().includes(q));if(typ)rows=rows.filter(([n,v])=>{let t=v;return !!t[typ]});let db=rows.map(([n,v])=>'<div class="dbtRow" onclick="openD('+JSON.stringify(x.path)+','+JSON.stringify(x.BaiHoc||'')+')"><div class="dbtName">'+esc(n)+'</div><div class="counts"><span class="c a">A '+v.A+'</span><span class="c b">B '+v.B+'</span><span class="c cc">C '+v.C+'</span><span class="c d">D '+v.D+'</span><span class="c sum">Σ '+v.total+'</span></div></div>').join('');H+='<div class="lesson"><div class="title">'+esc(x.BaiHoc||'Chưa rõ bài')+'</div><div class="muted">'+esc(x.Mon)+' · Lớp '+esc(x.Lop)+' · GitHub .tex</div><div class="tags"><span class="tag">'+x.count+' câu</span><span class="tag">A '+x.types.A+'</span><span class="tag">B '+x.types.B+'</span><span class="tag">C '+x.types.C+'</span><span class="tag">D '+x.types.D+'</span></div><div class="dbt"><div class="dbtHead">🏷️ Dạng bài tập · '+Object.keys(x.dang).length+' dạng</div>'+ (db||'<div class="muted">Chưa phân dạng</div>')+'</div><div class="actions"><button class="btn primary" onclick="openD('+JSON.stringify(x.path)+','+JSON.stringify(x.BaiHoc||'')+')">📖 Mở & sửa .tex</button></div></div>'}H+='</div></div>'}H+='</div></div>'}H+='</section>'}$('cat').innerHTML=H}async function openD(path,title){PATH=path;$('modal').classList.remove('hide');$('mt').textContent='📖 '+title;$('ms').textContent=path;$('ql').innerHTML='<div class="muted">⏳ Đọc .tex…</div>';$('code').value='';try{DET=await api('/github/api/tex-fast?path='+encodeURIComponent(path));SHA=DET.sha;$('ql').innerHTML=DET.questions.map(q=>'<div class="qi" id="q'+q.n+'" onclick="pick('+q.n+')"><div class="qn">Câu '+q.n+' · '+q.kind+' · '+esc(q.level||'')+(q.image?' · 🖼':'')+'</div><div class="qt">'+esc(q.title)+'</div><div class="qm">'+esc(q.dang)+'</div></div>').join('');if(DET.questions.length)pick(1)}catch(e){$('ql').innerHTML='<div class="muted">❌ '+esc(e.message)+'</div>'}}function pick(n){ACTIVE=n;let q=DET.questions[n-1];if(!q)return;document.querySelectorAll('.qi').forEach(e=>e.classList.remove('on'));$('q'+n).classList.add('on');$('qid').value=q.id||'';$('qlevel').value=q.level||'';$('code').value=q.text||''}function closeM(){$('modal').classList.add('hide');DET=null;PATH='';SHA='';ACTIVE=0}async function reloadQ(){if(PATH)await openD(PATH,$('mt').textContent.replace(/^📖\s*/,''))}async function saveQ(){if(!DET||!PATH)return;let code=$('code').value||'',all=DET.text,q=DET.questions[ACTIVE-1];if(!q)return;all=all.slice(0,q.start)+code+all.slice(q.end);try{setES('⏳ Đang lưu GitHub...',false);let j=await api('/github/api/save-tex-fast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:PATH,text:all,sha:SHA,message:'Sửa '+PATH})});setES('✅ Đã commit GitHub · '+(j.commit||'').slice(0,8),false);DET=await api('/github/api/tex-fast?path='+encodeURIComponent(PATH));SHA=DET.sha;renderQ();pick(Math.min(ACTIVE,DET.questions.length));}catch(e){setES('❌ '+e.message,true)}}function renderQ(){ $('ql').innerHTML=DET.questions.map(q=>'<div class="qi" id="q'+q.n+'" onclick="pick('+q.n+')"><div class="qn">Câu '+q.n+' · '+q.kind+' · '+esc(q.level||'')+(q.image?' · 🖼':'')+'</div><div class="qt">'+esc(q.title)+'</div><div class="qm">'+esc(q.dang)+'</div></div>').join('')}function setES(t,err){let e=$('es');e.className=err?'err':'ok';e.textContent=t;e.classList.remove('hide')}load();
</script></body></html>'''
