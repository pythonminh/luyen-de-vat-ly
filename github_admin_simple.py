# -*- coding: utf-8 -*-
"""Standalone GitHub admin bank. No app.py, no Google Sheet."""
from __future__ import annotations
import base64, json, os, re, urllib.parse, urllib.request
from pathlib import Path
from flask import Flask, Response, jsonify, request, redirect

app = Flask(__name__)
REPO = (os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').strip()
BRANCH = (os.getenv('GITHUB_BRANCH') or 'main').strip() or 'main'
TOKEN = (os.getenv('GITHUB_TOKEN') or '').strip()
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'bank_index.json'
API = 'https://api.github.com'
RAW = 'https://raw.githubusercontent.com'

def github_api(path, method='GET', payload=None):
    if not TOKEN:
        raise RuntimeError('Thiếu GITHUB_TOKEN trên Render')
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(API + path, data=body, method=method, headers={
        'Authorization': 'Bearer ' + TOKEN,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'luyen-de-vat-ly-admin',
        'Content-Type': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))

def load_index():
    if INDEX.exists():
        try:
            return json.loads(INDEX.read_text(encoding='utf-8'))
        except Exception:
            pass
    owner, repo = REPO.split('/', 1)
    url = f'{RAW}/{owner}/{repo}/{urllib.parse.quote(BRANCH)}/bank_index.json'
    with urllib.request.urlopen(url, timeout=12) as r:
        return json.loads(r.read().decode('utf-8'))

def safe_tex(path):
    return isinstance(path, str) and path.startswith('ngan-hang/') and path.lower().endswith('.tex') and '..' not in path

def read_tex(path):
    if not safe_tex(path):
        raise ValueError('Đường dẫn .tex không hợp lệ')
    owner, repo = REPO.split('/', 1)
    api_path = f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe="/")}?ref={urllib.parse.quote(BRANCH)}'
    obj = github_api(api_path)
    text = base64.b64decode((obj.get('content') or '').replace('\n', '')).decode('utf-8', 'replace')
    return obj.get('sha', ''), text

def classify(block):
    if re.search(r'\\choiceTF\b', block, re.I): return 'B. Đúng sai'
    if re.search(r'\\shortans\b', block, re.I): return 'C. Trả lời ngắn'
    if re.search(r'\\choice\b', block, re.I): return 'A. Trắc nghiệm'
    return 'D. Tự luận'

def parse_questions(text):
    blocks = list(re.finditer(r'\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}', text or '', re.I))
    marks = list(re.finditer(r'\\dangbt\s*\{([^{}]*)\}', text or '', re.I))
    out=[]
    for i,m in enumerate(blocks,1):
        b=m.group(0); prior=[x for x in marks if x.start()<m.start()]
        dang=prior[-1].group(1).strip() if prior else 'Chưa phân dạng'
        if dang.casefold() in {'','chưa có dạng','chua co dang','chưa phân dạng','chua phan dang'}: dang='Chưa phân dạng'
        im=re.search(r'%\s*ID\s*:\s*([^\r\n%]+)',b,re.I); lm=re.search(r'%\s*Mức\s*:\s*([^\r\n%]+)',b,re.I)
        out.append({'index':i,'id':im.group(1).strip() if im else '','level':lm.group(1).strip().upper() if lm else '','dang':dang,'kind':classify(b),'text':b})
    return out

def lessons():
    data=load_index(); out=[]
    for x in data.get('lessons') or []:
        if not isinstance(x,dict): continue
        p=(x.get('path') or x.get('file') or '').strip()
        if not safe_tex(p): continue
        out.append({'Mon':x.get('Mon',''),'Lop':x.get('Lop',''),'Chuong':x.get('Chuong',''),'BaiHoc':x.get('BaiHoc') or x.get('De') or Path(p).parent.name,'path':p,'count':int(x.get('count') or x.get('questions') or 0),'dang':x.get('dang') or {}})
    return data, out

@app.get('/')
def home(): return redirect('/github/quan-ly')
@app.get('/github/repo')
def repo(): return redirect('https://github.com/pythonminh/luyen-de-vat-ly', code=302)
@app.get('/bank_index.json')
def bank_index(): return Response(json.dumps(load_index(),ensure_ascii=False),mimetype='application/json')
@app.get('/github/api/catalog')
def api_catalog():
    try:
        data, rows=lessons(); return jsonify({'ok':True,'source':'GitHub','total_files':int(data.get('total_files') or len(rows)),'total_questions':int(data.get('total_questions') or sum(x['count'] for x in rows)),'lessons':rows})
    except Exception as e: return jsonify({'ok':False,'error':str(e)}),500
@app.get('/github/api/file')
def api_file():
    try:
        p=request.args.get('path',''); sha,text=read_tex(p); return jsonify({'ok':True,'path':p,'sha':sha,'text':text,'questions':parse_questions(text)})
    except Exception as e: return jsonify({'ok':False,'error':str(e)}),400
@app.post('/github/api/save')
def api_save():
    try:
        d=request.get_json(silent=True) or {}; p=d.get('path',''); text=d.get('text'); sha=d.get('sha')
        if not safe_tex(p) or not isinstance(text,str) or not sha: return jsonify({'ok':False,'error':'Thiếu path/text/sha'}),400
        owner,repo=REPO.split('/',1); q=f'/repos/{owner}/{repo}/contents/{urllib.parse.quote(p,safe="/")}'
        res=github_api(q,'PUT',{'message':d.get('message') or 'Admin cập nhật file .tex','content':base64.b64encode(text.encode('utf-8')).decode('ascii'),'branch':BRANCH,'sha':sha})
        commit=((res.get('commit') or {}).get('sha') or '')
        return jsonify({'ok':True,'commit':commit[:12]})
    except Exception as e: return jsonify({'ok':False,'error':str(e)}),409

PAGE=r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ngân hàng câu hỏi GitHub</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font:14px Arial,sans-serif}.top{background:#1769d2;color:white;padding:10px 16px}.row{display:flex;gap:12px;align-items:center}.brand{font-size:20px;font-weight:800}.sub{font-size:11px}.nav{margin-left:auto;display:flex;gap:6px}.nav a{color:#fff;text-decoration:none;border:1px solid #fff6;border-radius:8px;padding:7px 10px;font-weight:700}.wrap{max-width:1500px;margin:auto;padding:10px}.status{background:#eaf3ff;border:1px solid #c7dcf5;padding:8px 10px;border-radius:9px;margin-bottom:8px;font-size:11px}.layout{display:grid;grid-template-columns:280px 1fr;gap:9px}.panel{background:#fff;border:1px solid #d5e0ea;border-radius:12px;overflow:hidden}.head,.mainhead{padding:9px 11px;background:#f8fbff;border-bottom:1px solid #dfe8ef;font-weight:800}.mainhead{display:flex;justify-content:space-between}.body,.book{padding:9px}.field{margin-bottom:7px}.field label{display:block;font-size:10px;font-weight:700;color:#64748b;margin-bottom:3px}.field input,.field select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.subject{margin-bottom:9px}.subject h2{margin:0;padding:8px 10px;color:#fff;background:linear-gradient(90deg,#1d4ed8,#60a5fa);border-radius:9px;font-size:15px}.chapter{margin-top:7px;border:1px solid #cbddec;border-radius:9px;overflow:hidden}.chapter h3{margin:0;padding:7px 9px;background:#dbeafe;color:#1e3a8a;font-size:12px}.grid{padding:7px;display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:7px}.lesson{border:1px solid #d9e3ec;border-radius:9px;padding:8px}.lt{font-weight:800}.meta{font-size:10px;color:#64748b}.tag{display:inline-block;font-size:9px;border:1px solid #d5e1eb;border-radius:999px;padding:3px 6px;background:#f8fafc;margin:4px 3px 4px 0}.dang{border:1px solid #d4e5f7;background:#f7fbff;border-radius:7px;padding:5px}.drow{display:flex;justify-content:space-between;padding:4px 5px;background:#fff;border:1px solid #dbeafe;border-radius:5px;margin:3px 0;cursor:pointer}.drow:hover{background:#eff6ff}.dn{font-size:9px;font-weight:700}.num{font-size:9px;font-weight:800;color:#1d4ed8}.btn{border:1px solid #9fc1df;background:#eff6ff;color:#145ca8;border-radius:7px;padding:5px 8px;font-size:10px;font-weight:800;cursor:pointer}.actions{margin-top:5px}.empty{text-align:center;padding:35px;color:#64748b}.modal{position:fixed;inset:0;background:#0f172a99;display:flex;align-items:center;justify-content:center;padding:12px;z-index:50}.hide{display:none}.box{width:min(1500px,98vw);height:min(92vh,950px);background:#fff;border-radius:12px;display:flex;flex-direction:column;overflow:hidden}.mh{padding:9px 11px;background:#eef6ff;border-bottom:1px solid #d7e4ee;display:flex;justify-content:space-between}.mb{display:grid;grid-template-columns:320px 1fr;min-height:0;flex:1}.ql{overflow:auto;border-right:1px solid #dfe7ee;padding:7px}.qi{border:1px solid #dce5ed;border-radius:7px;padding:7px;margin:4px 0;cursor:pointer}.qi.on{background:#eff6ff;border-color:#8bb9e6}.qn{font-size:10px;font-weight:800}.qm{font-size:9px;color:#64748b}.ed{display:flex;flex-direction:column;padding:8px;min-width:0}.code{flex:1;min-height:0;resize:none;border:1px solid #cbd5e1;border-radius:8px;padding:9px;font:12px/1.5 Consolas,monospace}.foot{display:flex;gap:6px;align-items:center;margin-top:7px}.ok{color:#15803d;font-size:10px;font-weight:700}.err{color:#b91c1c;font-size:10px;font-weight:700}@media(max-width:850px){.layout{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.mb{grid-template-columns:1fr}.ql{max-height:220px;border-right:0;border-bottom:1px solid #dfe7ee}}
</style></head><body><div class="top"><div class="row"><div><div class="brand">📚 Ngân hàng câu hỏi GitHub</div><div class="sub">Nguồn: bank_index.json + ngan-hang/*.tex</div></div><div class="nav"><a href="/github/quan-ly">Mục lục</a><a href="/github/repo">GitHub</a></div></div></div><div class="wrap"><div class="status">✓ GitHub là nguồn chính · Không đọc Google Sheet · File .tex chỉ đọc khi mở bài</div><div class="layout"><aside class="panel"><div class="head">🔎 Tìm nhanh</div><div class="body"><div class="field"><label>Từ khóa</label><input id="q" placeholder="Bài, chương, dạng..." oninput="render()"></div><div class="field"><label>Môn</label><select id="mon" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Lớp</label><select id="lop" onchange="render()"><option value="">Tất cả</option></select></div><div class="field"><label>Chương</label><select id="chuong" onchange="render()"><option value="">Tất cả</option></select></div></div></aside><main class="panel"><div class="mainhead"><span>📖 Mục lục</span><span id="total">Đang tải...</span></div><div id="book" class="book"><div class="empty">Đang tải GitHub...</div></div></main></div></div><div id="modal" class="modal hide"><div class="box"><div class="mh"><b id="mt">Sửa file .tex</b><button class="btn" onclick="closeEdit()">Đóng</button></div><div class="mb"><div id="ql" class="ql"></div><div class="ed"><textarea id="code" class="code" spellcheck="false"></textarea><div class="foot"><button class="btn" onclick="saveFile()">💾 Lưu GitHub</button><button class="btn" onclick="openRaw()">🐙 Mở GitHub</button><span id="msg"></span></div></div></div></div></div><script>
let DATA=[],CUR=null,QS=[];const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function load(){try{let j=await (await fetch('/github/api/catalog',{cache:'no-store'})).json();if(!j.ok)throw Error(j.error);DATA=j.lessons||[];fill();render()}catch(e){$('book').innerHTML='<div class="empty">❌ '+esc(e.message)+'</div>';$('total').textContent='Lỗi'}}
function fill(){for(let [id,key] of [['mon','Mon'],['lop','Lop'],['chuong','Chuong']]){let s=$(id),old=s.value,v=[...new Set(DATA.map(x=>x[key]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'vi'));s.innerHTML='<option value="">Tất cả</option>'+v.map(x=>'<option>'+esc(x)+'</option>').join('');s.value=old}}
function render(){let q=$('q').value.toLowerCase(),m=$('mon').value,l=$('lop').value,c=$('chuong').value,rows=DATA.filter(x=>(!m||x.Mon===m)&&(!l||x.Lop===l)&&(!c||x.Chuong===c)&&(!q||[x.BaiHoc,x.Mon,x.Lop,x.Chuong].join(' ').toLowerCase().includes(q)));$('total').textContent=DATA.length+' bài · '+DATA.reduce((a,x)=>a+x.count,0)+' câu';let byM={};rows.forEach(x=>(byM[x.Mon]??=[]).push(x));let h='';for(let [mn,arr] of Object.entries(byM)){h+='<section class="subject"><h2>'+esc(mn)+' <small>'+arr.reduce((a,x)=>a+x.count,0)+' câu</small></h2>';let byC={};arr.forEach(x=>(byC[x.Chuong]??=[]).push(x));for(let [ch,ls] of Object.entries(byC)){h+='<div class="chapter"><h3>'+esc(ch)+'</h3><div class="grid">';for(let x of ls){let names=Object.entries(x.dang||{}).filter(([_,n])=>Number(n)>0);h+='<article class="lesson"><div class="lt">'+esc(x.BaiHoc)+'</div><div class="meta">Lớp '+esc(x.Lop)+'</div><span class="tag">'+x.count+' câu</span><div class="dang"><b style="font-size:10px;color:#1e3a8a">🏷️ Dạng bài tập</b>';if(!names.length)h+='<div class="drow" onclick="openEdit(\''+encodeURIComponent(x.path)+'\')"><span class="dn">Chưa phân dạng</span><span class="num">'+x.count+'</span></div>';else for(let [n,num] of names)h+='<div class="drow" onclick="openEdit(\''+encodeURIComponent(x.path)+'\')"><span class="dn">'+esc(n)+'</span><span class="num">'+num+'</span></div>';h+='</div><div class="actions"><button class="btn" onclick="openEdit(\''+encodeURIComponent(x.path)+'\')">✏️ Mở & sửa .tex</button></div></article>'}h+='</div></div>'}h+='</section>'}$("book").innerHTML=h||'<div class="empty">Không có dữ liệu.</div>'}
async function openEdit(ep){let p=decodeURIComponent(ep);$('modal').classList.remove('hide');$('ql').innerHTML='<div class="empty">Đang đọc .tex...</div>';try{let j=await (await fetch('/github/api/file?path='+encodeURIComponent(p))).json();if(!j.ok)throw Error(j.error);CUR=j;QS=j.questions||[];$('mt').textContent='✏️ '+p;$('ql').innerHTML=QS.map((x,i)=>'<div class="qi '+(!i?'on':'')+'" onclick="selectQ('+i+')"><div class="qn">Câu '+x.index+' · '+esc(x.kind)+'</div><div class="qm">'+esc(x.dang)+' · '+esc(x.level)+'</div></div>').join('');if(QS.length)selectQ(0)}catch(e){$('ql').innerHTML='<div class="empty">❌ '+esc(e.message)+'</div>'}}
function selectQ(i){document.querySelectorAll('.qi').forEach((e,k)=>e.classList.toggle('on',k===i));$('code').value=QS[i]?.text||'';$('code').dataset.i=i;$('msg').textContent=''}
async function saveFile(){if(!CUR)return;$('msg').className='';$('msg').textContent='Đang lưu GitHub...';try{let j=await (await fetch('/github/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:CUR.path,text:$('code').value,sha:CUR.sha,message:'Admin cập nhật '+CUR.path})})).json();if(!j.ok)throw Error(j.error);$('msg').className='ok';$('msg').textContent='✅ Đã commit GitHub '+j.commit;CUR.sha=(await (await fetch('/github/api/file?path='+encodeURIComponent(CUR.path),{cache:'no-store'})).json()).sha}catch(e){$('msg').className='err';$('msg').textContent='❌ '+e.message}}
function closeEdit(){$('modal').classList.add('hide')}function openRaw(){if(CUR)window.open('https://github.com/pythonminh/luyen-de-vat-ly/blob/main/'+CUR.path,'_blank')}
load();</script></body></html>'''

@app.get('/github/quan-ly')
def admin_page(): return Response(PAGE,mimetype='text/html')
