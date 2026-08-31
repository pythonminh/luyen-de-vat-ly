# -*- coding: utf-8 -*-
"""Force the lightweight GitHub bank UI for /github/quan-ly.
Removes conflicting legacy rules registered by app.py/older modules.
"""
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request, urllib.error
from flask import Response, jsonify, request, session
from app import app

REPO=(os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').strip()
BRANCH=(os.getenv('GITHUB_BRANCH') or 'main').strip() or 'main'
TOKEN=(os.getenv('GITHUB_TOKEN') or '').strip()
RAW='https://raw.githubusercontent.com'
API='https://api.github.com'


def gh(path, method='GET', payload=None):
    if not TOKEN:
        raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(API+path,data=data,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl-bank-force','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=18) as r:
        return json.loads(r.read().decode('utf-8'))


def raw(path):
    o,r=REPO.split('/',1)
    u=f'{RAW}/{o}/{r}/{urllib.parse.quote(BRANCH)}/{urllib.parse.quote(path,safe="/")}'
    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'ldvl-bank-force'}),timeout=12) as q:
        return q.read().decode('utf-8','replace')


def index():
    return json.loads(raw('bank_index.json'))


def valid(p):
    return p.startswith('ngan-hang/') and p.lower().endswith('.tex') and '..' not in p


def tex(p):
    if not valid(p): raise ValueError('Đường dẫn .tex không hợp lệ')
    o,r=REPO.split('/',1)
    q=f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(BRANCH)}'
    d=gh(q)
    return d.get('sha',''),base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')


def blocks(s):
    pat=re.compile(r'\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}',re.I)
    out=[]
    for n,m in enumerate(pat.finditer(s or ''),1):
        b=m.group(0); pm=list(re.finditer(r'\\dangbt\s*\{([^{}]*)\}',s[:m.start()],re.I)); d=(pm[-1].group(1).strip() if pm else 'Chưa phân dạng')
        if not d or d.casefold() in {'chưa có dạng','chua co dang','chưa phân dạng','chua phan dang'}: d='Chưa phân dạng'
        if re.search(r'\\choiceTF\b',b,re.I): k='B'
        elif re.search(r'\\shortans\b',b,re.I): k='C'
        elif re.search(r'\\choice\b',b,re.I): k='A'
        else: k='D'
        lm=re.search(r'%\s*Mức\s*:\s*([^\r\n%]+)',b,re.I); lv=(lm.group(1).strip().upper() if lm else '')
        im=re.search(r'%\s*ID\s*:\s*([^\r\n%]+)',b,re.I); qid=(im.group(1).strip() if im else '')
        out.append({'n':n,'id':qid,'level':lv,'dang':d,'kind':k,'text':b})
    return out


def catalog():
    rows=[]
    for x in index().get('lessons') or []:
        p=(x.get('github') or x.get('path') or x.get('file') or '').strip()
        if not p: continue
        if not p.startswith('ngan-hang/'): p='ngan-hang/'+p.lstrip('/')
        rows.append({'Mon':x.get('Mon',''),'Lop':x.get('Lop',''),'Chuong':x.get('Chuong',''),'BaiHoc':x.get('BaiHoc') or x.get('De') or p,'path':p,'count':int(x.get('count_questions') or x.get('questions') or x.get('count') or 0),'dang':x.get('dang') or {}})
    return rows


def remove_path(path):
    # Remove all existing rules for an exact URL path, then rebuild matcher.
    removed=[]
    for rule in list(app.url_map.iter_rules()):
        if rule.rule==path:
            try:
                app.url_map._rules.remove(rule); removed.append(rule.endpoint)
            except Exception:
                pass
    app.url_map._rules_by_endpoint={k:[r for r in v if r in app.url_map._rules] for k,v in app.url_map._rules_by_endpoint.items()}
    app.url_map._remap=True
    return removed

# The legacy app and earlier GitHub modules already registered /github/quan-ly.
# Remove every conflicting handler before installing this one.
remove_path('/github/quan-ly')

PAGE='''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ngân hàng câu hỏi GitHub</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Segoe UI,Arial,sans-serif}.top{background:#1769d2;color:#fff;padding:9px 16px;position:sticky;top:0;z-index:20}.toprow{display:flex;align-items:center;gap:10px}.brand{font-size:20px;font-weight:950}.sub{font-size:11px;opacity:.9}.nav{display:flex;gap:5px;margin-left:8px}.nav a{color:#fff;text-decoration:none;border:1px solid #fff5;border-radius:10px;padding:7px 12px;font-weight:900}.nav a.on{background:#fff;color:#1558a6}.source{margin-left:auto;font-size:11px;font-weight:900}.wrap{max-width:1500px;margin:auto;padding:10px}.status{padding:8px 11px;background:#eaf3ff;border:1px solid #c8ddf5;border-radius:10px;color:#18558f;font-size:11px;margin-bottom:8px}.tools{display:flex;gap:6px;margin-bottom:8px}.btn{border:1px solid #bcd2e9;background:#fff;color:#174a84;border-radius:8px;padding:7px 10px;font-weight:850;font-size:11px;cursor:pointer}.layout{display:grid;grid-template-columns:290px 1fr;gap:9px}.side,.main{background:#fff;border:1px solid #d4dfe9;border-radius:13px}.side{position:sticky;top:103px;align-self:start;overflow:hidden}.head{padding:10px 12px;background:#f8fbff;border-bottom:1px solid #dfe7ef;font-weight:950}.body{padding:9px}.field{margin-bottom:7px}.field label{display:block;font-size:10px;font-weight:900;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px}.tree{border-top:1px solid #e5eaf0;margin:8px -9px -9px;padding:7px 9px}.tree div{padding:4px 0;font-size:11px;font-weight:850}.mainhead{display:flex;justify-content:space-between;padding:10px 12px;border-bottom:1px solid #dfe7ef;background:#f8fbff;font-weight:950}.book{padding:8px}.subject{margin-bottom:10px}.subjecthead{padding:9px 12px;color:#fff;font-weight:950;border-radius:11px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);display:flex;justify-content:space-between}.grade{margin-top:7px;border:1px solid #cfd9e3;border-radius:11px;overflow:hidden}.gradehead{padding:8px 10px;background:#f1f5f9;font-weight:950}.chapter{margin:7px;border:1px solid #c6ddf6;border-radius:10px;overflow:hidden;background:#f8fbff}.chapterhead{padding:7px 10px;background:#dbeafe;color:#1e3a8a;font-weight:950}.grid{padding:7px;display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:7px}.lesson{border:1px solid #dce5ed;border-radius:11px;background:#fff;padding:9px}.lt{font-weight:950;line-height:1.3}.ls{font-size:10px;color:#64748b}.tags{display:flex;gap:4px;flex-wrap:wrap;margin:5px 0}.tag{border:1px solid #d6e0e8;background:#f8fafc;border-radius:999px;padding:3px 6px;font-size:9px;font-weight:900}.dbt{margin-top:5px;padding:5px;border:1px solid #d4e5f8;border-radius:8px;background:#f8fbff}.dbthead{font-size:9.5px;font-weight:950;color:#1e3a8a}.dbtrow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px;align-items:center;background:#fff;border:1px solid #dbeafe;border-radius:6px;padding:4px 5px;margin:3px 0;cursor:pointer}.dbtrow:hover{background:#eff6ff}.dn{font-size:9.5px;font-weight:850;line-height:1.25}.ct{font-size:8.5px;font-weight:950;padding:2px 5px;border-radius:999px;background:#eaf2ff;border:1px solid #bfdbfe;color:#1e3a8a}.actions{display:flex;gap:4px;margin-top:6px;flex-wrap:wrap}.mini{border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:7px;padding:5px 7px;font-size:9px;font-weight:900;cursor:pointer}.empty{padding:30px;text-align:center;color:#64748b}.modal{position:fixed;inset:0;background:#0f172a99;z-index:50;display:flex;align-items:center;justify-content:center;padding:12px}.hide{display:none}.box{width:min(1450px,98vw);height:min(92vh,930px);background:#fff;border-radius:14px;display:flex;flex-direction:column;overflow:hidden}.mh{padding:9px 12px;background:#eef6ff;border-bottom:1px solid #d2e1f0;display:flex;justify-content:space-between;align-items:center}.mb{display:grid;grid-template-columns:310px 1fr;min-height:0;flex:1}.ql{overflow:auto;padding:7px;border-right:1px solid #dde6ee}.qi{padding:7px;border:1px solid #e0e7ef;border-radius:8px;margin:4px 0;cursor:pointer}.qi:hover,.qi.on{background:#eff6ff;border-color:#8bb8e8}.qn{font-size:10px;font-weight:950;color:#145bb0}.qt{font-size:10px;line-height:1.35}.qm{font-size:9px;color:#64748b}.ed{padding:9px;display:flex;flex-direction:column;min-width:0}.meta{display:grid;grid-template-columns:1fr 1fr;gap:6px}.meta input{padding:7px;border:1px solid #cbd5e1;border-radius:7px}.code{flex:1;min-height:0;margin-top:7px;resize:none;border:1px solid #cbd5e1;border-radius:8px;padding:10px;font:12px/1.5 Consolas,monospace}.foot{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.msg{font-size:11px;padding:7px 9px;border-radius:8px}.ok{background:#ecfdf5;border:1px solid #86efac;color:#166534}.err{background:#fff1f2;border:1px solid #fecaca;color:#b42318}@media(max-width:850px){.layout{grid-template-columns:1fr}.side{position:static}.grid{grid-template-columns:1fr}.mb{grid-template-columns:1fr}.ql{max-height:240px;border-right:0;border-bottom:1px solid #dde6ee}.meta{grid-template-columns:1fr}}
</style></head><body><div class="top"><div class="toprow"><div><div class="brand">📚 Ngân hàng câu hỏi GitHub</div><div class="sub">Nguồn chính: bank_index.json + ngan-hang/*.tex</div></div><div class="nav"><a class="on" href="/github/quan-ly">Mục lục</a><a href="/">Ứng dụng</a></div><div class="source">✓ GitHub</div></div></div><div class="wrap"><div class="status">✓ GitHub là nguồn chính · Google Sheet không được gọi · Chỉ đọc .tex khi mở bài</div><div class="tools"><button class="btn" onclick="loadCatalog()">↻ Tải mục lục</button><button class="btn" onclick="document.getElementById('q').focus()">🔎 Tìm</button></div><div class="layout"><aside class="side"><div class="head">🔎 Tìm nhanh</div><div class="body"><div class="field"><label>Từ khóa</label><input id="q" placeholder="Bài, chương, dạng..." oninput="render()"></div><div class="field"><label>Môn</label><select id="mon" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="lop" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="chuong" onchange="render()"><option value="">Tất cả</option></select></div><div class="tree" id="tree"></div></div></aside><main class="main"><div class="mainhead"><span>📖 Mục lục kiểu sách</span><span id="totals">Đang tải...</span></div><div class="book" id="book"><div class="empty">Đang tải Mục lục GitHub...</div></div></main></div></div><div id="modal" class="modal hide"><div class="box"><div class="mh"><b id="mTitle">Sửa file .tex</b><button class="btn" onclick="closeEdit()">Đóng</button></div><div class="mb"><div class="ql" id="ql"></div><div class="ed"><div class="meta"><input id="mid" placeholder="ID"><input id="mlv" placeholder="Mức"></div><textarea id="code" class="code" spellcheck="false"></textarea><div class="foot"><button class="btn primary" onclick="saveEdit()">💾 Lưu GitHub</button><button class="btn" onclick="closeEdit()">Hủy</button><span id="msg"></span></div></div></div></div></div><script>
let DATA=[],CUR=null,QS=[];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function loadCatalog(){let r=await fetch('/github/force-catalog');let j=await r.json();if(!j.ok){document.getElementById('book').innerHTML='<div class="empty">'+esc(j.error)+'</div>';return}DATA=j.lessons||[];fillFilters();render()}
function fillFilters(){for(const [id,key] of [['mon','Mon'],['lop','Lop'],['chuong','Chuong']]){let s=document.getElementById(id),old=s.value,vals=[...new Set(DATA.map(x=>x[key]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'vi'));s.innerHTML='<option value="">Tất cả</option>'+vals.map(v=>'<option>'+esc(v)+'</option>').join('');s.value=old}}
function render(){let q=(document.getElementById('q').value||'').toLowerCase(),m=document.getElementById('mon').value,l=document.getElementById('lop').value,c=document.getElementById('chuong').value;let rows=DATA.filter(x=>(!m||x.Mon===m)&&(!l||x.Lop===l)&&(!c||x.Chuong===c)&&(!q||[x.BaiHoc,x.Chuong,x.Mon,x.Lop].join(' ').toLowerCase().includes(q)));document.getElementById('totals').textContent=DATA.length+' bài · '+DATA.reduce((a,x)=>a+x.count,0)+' câu';let tree={};rows.forEach(x=>(tree[x.Mon]??=[]).push(x));document.getElementById('tree').innerHTML=Object.entries(tree).map(([mon,arr])=>'<div>▾ '+esc(mon)+' · '+arr.length+' bài</div>').join('');let html='';for(const [mon,arr] of Object.entries(tree)){html+='<section class="subject"><div class="subjecthead"><span>'+esc(mon)+'</span><span>'+arr.reduce((a,x)=>a+x.count,0)+' câu</span></div>';let grades={};arr.forEach(x=>(grades[x.Lop]??=[]).push(x));for(const [lop,les] of Object.entries(grades)){html+='<div class="grade"><div class="gradehead">Khối '+esc(lop)+'</div>';let ch={};les.forEach(x=>(ch[x.Chuong]??=[]).push(x));for(const [cc,ls] of Object.entries(ch)){html+='<div class="chapter"><div class="chapterhead">'+esc(cc)+'</div><div class="grid">';for(const x of ls){let d=x.dang||{};html+='<div class="lesson"><div class="lt">'+esc(x.BaiHoc)+'</div><div class="ls">'+esc(x.Mon)+' · Lớp '+esc(x.Lop)+' · '+esc(x.Chuong)+'</div><div class="tags"><span class="tag">'+x.count+' câu</span><span class="tag">.tex</span></div><div class="dbt"><div class="dbthead">🏷️ Dạng bài tập</div><div data-path="'+encodeURIComponent(x.path)+'" class="dbtwrap">';let names=Object.entries(d).filter(([_,n])=>Number(n)>0);if(!names.length){html+='<div class="dbtrow" onclick="openLesson(\''+encodeURIComponent(x.path)+'\')"><span class="dn">Chưa phân dạng</span><span class="ct">'+x.count+'</span></div>'}else{for(const [n,num] of names)html+='<div class="dbtrow" onclick="openLesson(\''+encodeURIComponent(x.path)+'\')"><span class="dn">'+esc(n)+'</span><span class="ct">'+num+'</span></div>'}html+='</div></div><div class="actions"><button class="mini" onclick="openLesson(\''+encodeURIComponent(x.path)+'\')">📂 Mở bài</button></div></div>'}html+='</div></div>'}html+='</div>'}html+='</div>'}document.getElementById('book').innerHTML=html}
async function openLesson(ep){let p=decodeURIComponent(ep);document.getElementById('modal').classList.remove('hide');document.getElementById('mTitle').textContent='Đọc file .tex';document.getElementById('ql').innerHTML='<div class="empty">Đang đọc .tex...</div>';let r=await fetch('/github/force-tex?path='+encodeURIComponent(p));let j=await r.json();if(!j.ok){document.getElementById('ql').innerHTML='<div class="empty">'+esc(j.error)+'</div>';return}CUR=j;QS=j.questions||[];document.getElementById('ql').innerHTML=QS.map((q,i)=>'<div class="qi '+(i===0?'on':'')+'" onclick="selectQ('+i+')"><div class="qn">Câu '+q.n+' · '+q.kind+'</div><div class="qt">'+esc(q.dang)+'</div><div class="qm">'+esc(q.level)+' '+(q.image?'· 🖼':'')+'</div></div>').join('');if(QS.length)selectQ(0)}
function selectQ(i){document.querySelectorAll('.qi').forEach((e,k)=>e.classList.toggle('on',k===i));let q=QS[i];document.getElementById('mid').value=q.id||'';document.getElementById('mlv').value=q.level||'';document.getElementById('code').value=q.text||'';document.getElementById('mTitle').textContent='Câu '+q.n+' · '+q.kind+' · '+(q.dang||'Chưa phân dạng')}
async function saveEdit(){if(!CUR)return;let t=document.getElementById('code').value,r=await fetch('/github/force-save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:CUR.path,text:t,sha:CUR.sha,message:'Cập nhật câu hỏi từ Ngân hàng GitHub'})});let j=await r.json();document.getElementById('msg').innerHTML='<span class="msg '+(j.ok?'ok':'err')+'">'+esc(j.ok?'✅ Đã lưu GitHub · '+(j.commit||''):(j.error||'Lỗi'))+'</span>';if(j.ok){setTimeout(()=>{closeEdit();loadCatalog()},700)}}
function closeEdit(){document.getElementById('modal').classList.add('hide')}
loadCatalog();
</script></body></html>'''


@app.get('/github/quan-ly')
def force_page():
    return Response(PAGE,mimetype='text/html')

@app.get('/github/force-catalog')
def force_catalog():
    try:
        idx=index(); rows=catalog(); return jsonify({'ok':True,'source':'GitHub','total_files':int(idx.get('total_files') or len(rows)),'total_questions':int(idx.get('total_questions') or sum(x['count'] for x in rows)),'lessons':rows})
    except Exception as e:return jsonify({'ok':False,'error':str(e)}),500

@app.get('/github/force-tex')
def force_tex():
    try:
        p=request.args.get('path',''); sha,text=tex(p); return jsonify({'ok':True,'path':p,'sha':sha,'text':text,'questions':blocks(text)})
    except Exception as e:return jsonify({'ok':False,'error':str(e)}),400

@app.post('/github/force-save')
def force_save():
    try:
        d=request.get_json(silent=True) or {};p=d.get('path','');t=d.get('text');sha=d.get('sha')
        if not isinstance(t,str) or not valid(p) or not sha:return jsonify({'ok':False,'error':'Thiếu path/text/sha'}),400
        o,r=REPO.split('/',1);q=f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}'
        res=gh(q,'PUT',{'message':d.get('message') or 'Cập nhật .tex','content':base64.b64encode(t.encode()).decode(),'branch':BRANCH,'sha':sha})
        return jsonify({'ok':True,'commit':((res.get('commit') or {}).get('sha') or '')[:12]})
    except Exception as e:return jsonify({'ok':False,'error':str(e)}),409

app.config['GITHUB_BANK_FORCE']=True
