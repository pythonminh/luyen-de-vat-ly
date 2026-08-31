# -*- coding: utf-8 -*-
from __future__ import annotations

import base64, json, os, re, urllib.error, urllib.parse, urllib.request
from flask import Blueprint, request, session, redirect, url_for, render_template_string, jsonify

bp = Blueprint('github_manager', __name__)
API='https://api.github.com'

CSS='''<style>
body{font-family:Arial,sans-serif;background:#f4f7fb;color:#17324d;margin:0}.wrap{max-width:1500px;margin:14px auto;padding:0 16px}.top{background:linear-gradient(135deg,#0f6fcf,#2a86df);color:#fff;padding:18px 20px;border-radius:14px;margin-bottom:12px}.top h1{margin:0;font-size:25px}.top p{margin:5px 0 0;opacity:.9}.grid{display:grid;grid-template-columns:300px 1fr;gap:12px}.card{background:#fff;border:1px solid #dbe3ee;border-radius:12px;box-shadow:0 2px 10px rgba(20,50,90,.06)}.sidebar{padding:12px;max-height:calc(100vh - 160px);overflow:auto}.main{padding:14px}.toolbar{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px}.btn{border:1px solid #c8d4e2;background:#fff;color:#125da7;padding:8px 11px;border-radius:9px;font-weight:700;cursor:pointer}.btn.primary{background:#1976d2;color:#fff;border-color:#1976d2}.btn.green{background:#188038;color:#fff;border-color:#188038}.btn.red{background:#fff2f2;color:#ba1b1b;border-color:#efb3b3}.search{width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:9px}.tree{list-style:none;padding:0;margin:0}.tree li{margin:3px 0}.node{display:block;padding:8px 9px;border-radius:8px;cursor:pointer}.node:hover,.node.active{background:#eaf3ff;color:#0759a6}.indent{margin-left:13px}.muted{font-size:12px;color:#64748b}.chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 12px}.chip{padding:4px 8px;border-radius:999px;background:#edf4ff;color:#145aa2;font-size:11px;font-weight:700}.filter{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}.filter select,.filter input{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:8px;border-bottom:1px solid #e6ebf2;text-align:left;vertical-align:top}.rowbtn{display:flex;gap:5px;flex-wrap:wrap}.small{font-size:11px}.editor{display:none;padding:12px;margin-top:12px}.editor textarea{width:100%;min-height:420px;font:13px/1.5 Consolas,monospace;padding:10px;border:1px solid #c4cfdd;border-radius:9px;box-sizing:border-box}.status{padding:9px 11px;border-radius:8px;background:#f1f5f9;margin:8px 0}.ok{background:#eaf8ef;border:1px solid #a8d5b5;color:#166534}.err{background:#fff0f0;border:1px solid #efb1b1;color:#b91c1c}.stats{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.stat{background:#f7fbff;border:1px solid #d6e5f7;padding:8px 11px;border-radius:9px}.count{font-weight:800;color:#1557a6}@media(max-width:950px){.grid{grid-template-columns:1fr}.sidebar{max-height:330px}.filter{grid-template-columns:1fr 1fr}}
</style>'''

TPL=CSS+'''<div class="wrap"><div class="top"><h1>🐙 Quản lý ngân hàng GitHub</h1><p>GitHub là nguồn chính · không phụ thuộc Google Sheet · quản lý theo Môn → Lớp → Chương → Bài → Dạng</p></div><div class="toolbar"><a class="btn" href="/">← Ứng dụng</a><a class="btn" href="/ra-de">📝 Ra đề</a><button class="btn" onclick="location.reload()">↻ Làm mới</button><button class="btn green" onclick="showEditor()">➕ Thêm câu vào bài đang chọn</button></div><div id="status" class="status">Đang đọc bank_index.json…</div><div class="grid"><div class="card sidebar"><input id="q" class="search" placeholder="🔎 Tìm môn, lớp, bài, dạng…" oninput="renderTree()"><div id="tree"></div></div><div class="card main"><div class="stats"><div class="stat">📁 <span id="sf" class="count">0</span> file</div><div class="stat">📚 <span id="sq" class="count">0</span> câu</div><div class="stat">🧩 <span id="sd" class="count">0</span> dạng</div></div><div class="filter"><select id="fmon" onchange="renderLessons()"><option value="">Tất cả môn</option></select><select id="flop" onchange="renderLessons()"><option value="">Tất cả lớp</option></select><select id="fchuong" onchange="renderLessons()"><option value="">Tất cả chương</option></select><input id="fdang" placeholder="Lọc dạng bài…" oninput="renderLessons()"></div><div id="lessons"></div><div id="editor" class="card editor"><h3 id="etitle">✏️ Chỉnh câu</h3><div class="muted">Sửa trực tiếp block LaTeX của một câu. Hình/TikZ nằm trong chính block sẽ được giữ nguyên.</div><textarea id="ecode" spellcheck="false"></textarea><div class="toolbar"><button class="btn green" onclick="saveQuestion()">💾 Lưu câu lên GitHub</button><button class="btn" onclick="closeEditor()">Đóng</button></div></div></div></div></div>
<script>
let D=null, lessons=[], selectedPath='', selectedIndex=-1, selectedBlock='', selectedMeta=null;
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function init(){try{let r=await fetch('/bank_index.json?ts='+Date.now());D=await r.json();lessons=D.lessons||[];document.getElementById('sf').textContent=D.total_files||lessons.length;document.getElementById('sq').textContent=D.total_questions||0;let ds=new Set();lessons.forEach(x=>Object.keys(x.dang||{}).forEach(d=>ds.add(d)));document.getElementById('sd').textContent=ds.size;fillFilters();renderTree();renderLessons();status('✓ GitHub index sẵn sàng');}catch(e){status('❌ Không đọc được bank_index.json: '+e,true)}}
function status(s,err=false){let x=document.getElementById('status');x.textContent=s;x.className='status '+(err?'err':'ok')}
function vals(key){return [...new Set(lessons.map(x=>x[key]).filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b),'vi'))}
function fill(id,key){let el=document.getElementById(id);[...el.options].slice(1).forEach(o=>o.remove());vals(key).forEach(v=>{let o=document.createElement('option');o.value=v;o.textContent=v;el.appendChild(o)})}
function fillFilters(){fill('fmon','Mon');fill('flop','Lop');fill('fchuong','Chuong')}
function renderTree(){let term=(document.getElementById('q').value||'').toLowerCase(), ms={}, html='';lessons.forEach(x=>{let s=(x.Mon+' '+x.Lop+' '+x.Chuong+' '+x.BaiHoc+' '+Object.keys(x.dang||{}).join(' ')).toLowerCase();if(term&&!s.includes(term))return;let m=x.Mon||'Khác',l=x.Lop||'',c=x.Chuong||'Chưa phân chương';ms[m]??={};ms[m][l]??={};ms[m][l][c]??=[];ms[m][l][c].push(x)});Object.keys(ms).sort().forEach(m=>{html+='<div class=node><b>📘 '+E(m)+'</b></div>';Object.keys(ms[m]).sort().forEach(l=>{html+='<div class="node indent"><b>🎓 Lớp '+E(l)+'</b></div>';Object.keys(ms[m][l]).sort().forEach(c=>{html+='<div class="node indent" style="margin-left:28px">📂 '+E(c)+'</div>';ms[m][l][c].forEach(x=>{html+='<div class="node indent" style="margin-left:42px" onclick="pick(\''+E(x.path).replace(/'/g,'\\\'')+'\')">📄 '+E(x.BaiHoc||x.De||x.path)+' <span class="muted">('+Number(x.questions||0)+')</span></div>'})})})});document.getElementById('tree').innerHTML=html}
function renderLessons(){let mon=document.getElementById('fmon').value,lop=document.getElementById('flop').value,ch=document.getElementById('fchuong').value,dt=(document.getElementById('fdang').value||'').toLowerCase();let arr=lessons.filter(x=>(!mon||x.Mon===mon)&&(!lop||x.Lop===lop)&&(!ch||x.Chuong===ch)&&(!dt||Object.keys(x.dang||{}).some(d=>d.toLowerCase().includes(dt))));let h='<table class="table"><tr><th>Môn · Lớp · Chương · Bài</th><th>Dạng bài</th><th>Số câu</th><th>Thao tác</th></tr>';arr.forEach(x=>{let ds=Object.entries(x.dang||{}).map(([d,n])=>'<span class="chip">'+E(d)+' · '+n+'</span>').join('');h+='<tr><td><b>'+E(x.Mon)+'</b> · Lớp '+E(x.Lop)+'<br><b>'+E(x.Chuong)+'</b><br><span>'+E(x.BaiHoc||x.De||x.path)+'</span></td><td>'+ds+'</td><td><b>'+Number(x.questions||0)+'</b></td><td><div class="rowbtn"><button class="btn" onclick="openFile(\''+E(x.path).replace(/'/g,'\\\'')+'\')">📖 Xem câu</button><button class="btn primary" onclick="addTo(\''+E(x.path).replace(/'/g,'\\\'')+'\')">➕ Thêm</button></div></td></tr>''});h+='</table>';document.getElementById('lessons').innerHTML=h}
function pick(p){document.getElementById('fmon').value='';document.getElementById('fdang').value='';openFile(p)}
async function openFile(path){let r=await fetch('/github-manager/api/file?path='+encodeURIComponent(path));let d=await r.json();if(!d.ok)return status('❌ '+d.error,true);selectedPath=path;window._blocks=d.blocks||[];let h='<h3>📖 '+E(path)+'</h3>';h+='<div class="hint">Bấm <b>Sửa</b> ở câu cần chỉnh.</div><table class="table"><tr><th>Câu</th><th>ID / Mức / Dạng</th><th>Nội dung</th><th></th></tr>';d.meta.forEach((m,i)=>{h+='<tr><td><b>Câu '+(i+1)+'</b></td><td><div class="chips"><span class="chip">'+E(m.kind)+'</span><span class="chip">'+E(m.level||'')+'</span><span class="chip">'+E(m.dangbt||'Chưa phân dạng')+'</span></div></td><td>'+E(m.title||'').slice(0,280)+'</td><td><button class="btn" onclick="editQ('+i+')">✏️ Sửa</button></td></tr>'});h+='</table>';document.getElementById('lessons').innerHTML=h}
async function editQ(i){let b=window._blocks[i]||'';selectedIndex=i;selectedBlock=b;document.getElementById('ecode').value=b;document.getElementById('etitle').textContent='✏️ Sửa Câu '+(i+1);document.getElementById('editor').style.display='block';document.getElementById('editor').scrollIntoView({behavior:'smooth'})}
function addTo(path){selectedPath=path;window._blocks=[];showEditor()}
function showEditor(){document.getElementById('editor').style.display='block';document.getElementById('etitle').textContent='➕ Thêm câu vào '+(selectedPath||'(chọn Bài trước)');document.getElementById('ecode').value='\\begin{ex}\n% ID: NEW-...\n% Mức: NB\n\\dangbt{Chưa phân dạng}\nNội dung câu hỏi mới.\n\\choice\n{Phương án A}\n{Phương án B}\n{Phương án C}\n{Phương án D}\n\\loigiai{\n}\n\\end{ex}';document.getElementById('editor').scrollIntoView({behavior:'smooth'})}
function closeEditor(){document.getElementById('editor').style.display='none'}
async function saveQuestion(){if(!selectedPath)return status('⚠️ Hãy chọn một Bài trước.',true);let code=document.getElementById('ecode').value;let body={path:selectedPath,index:selectedIndex,block:code};let r=await fetch('/github-manager/api/save-question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let d=await r.json();if(!d.ok)return status('❌ '+d.error,true);status('✅ Đã lưu GitHub · '+d.commit);closeEditor();await init();openFile(selectedPath)}
init();
</script>'''


def gate():
    if not session.get('mahs'):
        return redirect(url_for('login', next=request.full_path.rstrip('?')))
    try:
        from app import is_admin
        if not is_admin(): return ('<h3>403 — Chỉ ADMIN được dùng.</h3>',403)
    except Exception: pass


def gh(path,method='GET',body=None):
    token=os.getenv('GITHUB_TOKEN','').strip()
    if not token: raise RuntimeError('Thiếu GITHUB_TOKEN trên Render.')
    data=None if body is None else json.dumps(body,ensure_ascii=False).encode()
    req=urllib.request.Request(API+path,data=data,method=method,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ldvl-github-manager','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:msg=json.loads(e.read().decode()).get('message',str(e))
        except Exception:msg=str(e)
        raise RuntimeError(f'GitHub API {e.code}: {msg}')

def repo(): return (os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').split('/',1)

def split_tex(txt):
    ms=list(re.finditer(r'\\begin\s*\{ex\}.*?\\end\s*\{ex\}',txt or '',re.S|re.I))
    if not ms:return txt,[],''
    return txt[:ms[0].start()],[m.group(0) for m in ms],txt[ms[-1].end():]

def meta(b,i):
    g=lambda p:(re.search(p,b,re.I).group(1).strip() if re.search(p,b,re.I) else '')
    kind='Tự luận'
    if re.search(r'\\choiceTF\b',b,re.I):kind='Đúng / Sai'
    elif re.search(r'\\shortans\b',b,re.I):kind='Trả lời ngắn'
    elif re.search(r'\\choice\b',b,re.I):kind='Trắc nghiệm'
    m=re.search(r'\\begin\s*\{ex\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{ex\})',b,re.S|re.I);t=''
    if m:t=re.sub(r'\s+',' ',re.sub(r'%[^\r\n]*','',m.group(1))).strip()
    return {'n':i+1,'id':g(r'%\s*ID\s*:\s*([^\r\n]+)'),'level':g(r'%\s*Mức\s*:\s*([^\r\n]+)'),'dangbt':g(r'\\dangbt\s*\{([^{}]*)\}'),'kind':kind,'title':t[:280]}

@bp.get('/github/quan-ly')
def manager():
    x=gate()
    if x:return x
    return render_template_string(TPL)

@bp.get('/github-manager/api/file')
def api_file():
    x=gate()
    if x:return jsonify(ok=False,error='403'),403
    path=request.args.get('path','').strip('/')
    if not (path.startswith('ngan-hang/') and path.lower().endswith('.tex')):return jsonify(ok=False,error='Path không hợp lệ'),400
    o,r=repo()
    try:
        d=gh(f'/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe="/")}?ref=main');txt=base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace');head,blocks,tail=split_tex(txt)
        return jsonify(ok=True,meta=[meta(b,i) for i,b in enumerate(blocks)],blocks=blocks,sha=d.get('sha',''))
    except Exception as e:return jsonify(ok=False,error=str(e)),500

@bp.post('/github-manager/api/save-question')
def api_save_question():
    x=gate()
    if x:return x
    data=request.get_json(silent=True) or {};path=str(data.get('path','')).strip('/');idx=int(data.get('index',-1));block=str(data.get('block',''))
    if not (path.startswith('ngan-hang/') and path.lower().endswith('.tex')):return jsonify(ok=False,error='Path không hợp lệ'),400
    o,r=repo()
    try:
        q=f'/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe="/")}?ref=main';d=gh(q);txt=base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace');head,blocks,tail=split_tex(txt)
        if idx < 0: blocks.append(block.strip())
        elif idx < len(blocks): blocks[idx]=block
        else:return jsonify(ok=False,error='Chỉ số câu không hợp lệ'),400
        content=head+'\n\n'.join(blocks)+tail
        res=gh(f'/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe="/")}', 'PUT', {'message':f'ADMIN cập nhật câu trong {path}','content':base64.b64encode(content.encode()).decode(),'sha':d.get('sha'),'branch':'main'})
        return jsonify(ok=True,commit=res.get('commit',{}).get('sha','')[:12])
    except Exception as e:return jsonify(ok=False,error=str(e)),500
''