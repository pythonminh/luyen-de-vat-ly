# -*- coding: utf-8 -*-
"""Giao diện GitHub duy nhất cho ngân hàng câu hỏi.
Nguồn dữ liệu: bank_index.json + ngan-hang/*.tex trên GitHub.
Không dùng Google Sheet cho ngân hàng câu hỏi.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error
from flask import Blueprint, request, session, redirect, url_for, Response
from app import app

bp = Blueprint("github_manager_ui", __name__)
API = "https://api.github.com"
REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()


def admin_ok():
    if not session.get("mahs"):
        return False
    try:
        from app import is_admin
        return bool(is_admin())
    except Exception:
        return True


def gh(path, method="GET", payload=None):
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Thiếu GITHUB_TOKEN trên Render.")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "ldvl-github-bank"}
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("message", str(e))
        except Exception:
            msg = str(e)
        raise RuntimeError(f"GitHub API {e.code}: {msg}")


def load_index():
    p = os.path.join(app.root_path, "bank_index.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def valid_path(p):
    p = (p or "").strip("/")
    return p.startswith("ngan-hang/") and p.lower().endswith(".tex") and ".." not in p


def split_tex(text):
    pat = re.compile(r"\\begin\s*\{\s*ex\s*\}[\s\S]*?\\end\s*\{\s*ex\s*\}", re.I)
    ms = list(pat.finditer(text or ""))
    if not ms:
        return text or "", [], ""
    return text[:ms[0].start()], [m.group(0) for m in ms], text[ms[-1].end():]


def fetch_tex(path):
    owner, repo = REPO.split("/", 1)
    u = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref=main"
    d = gh(u)
    raw = base64.b64decode((d.get("content") or "").replace("\n", "")).decode("utf-8", "replace")
    return d.get("sha", ""), raw


def meta(block, n):
    def one(p):
        m = re.search(p, block or "", re.I)
        return m.group(1).strip() if m else ""
    kind = "A"
    if re.search(r"\\choiceTF\b", block): kind = "B"
    elif re.search(r"\\shortans\b", block): kind = "C"
    elif not re.search(r"\\choice\b", block): kind = "D"
    title = ""
    m = re.search(r"\\begin\s*\{ex\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{ex\})", block, re.S|re.I)
    if m:
        title = re.sub(r"%[^\r\n]*", "", m.group(1))
        title = re.sub(r"\\dangbt\s*\{[^{}]*\}", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()[:180]
    return {
        "n": n, "id": one(r"%\s*ID\s*:\s*([^\r\n]+)"),
        "level": one(r"%\s*Mức\s*:\s*([^\r\n]+)"),
        "dang": one(r"\\dangbt\s*\{([^{}]*)\}"),
        "kind": kind, "title": title,
    }


def edit_html(path, sha, head, blocks, tail, msg="", error=""):
    payload = {
        "path": path, "sha": sha, "head": head, "blocks": blocks, "tail": tail,
        "meta": [meta(b, i+1) for i,b in enumerate(blocks)]
    }
    j = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    note = (f'<div class="note ok">{html_escape(msg)}</div>' if msg else '') + (f'<div class="note err">{html_escape(error)}</div>' if error else '')
    html = r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ngân hàng GitHub</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#17324d;font-family:Arial,sans-serif}.wrap{max-width:1450px;margin:14px auto;padding:0 12px}.top{display:flex;justify-content:space-between;gap:12px;align-items:center;background:#fff;border:1px solid #d9e2eb;border-radius:14px;padding:13px 16px}.brand{font-weight:800;font-size:19px}.sub{font-size:11px;color:#64748b;margin-top:4px;word-break:break-all}.ok{color:#188038;font-weight:700}.note{margin:10px 0;padding:10px 12px;border-radius:9px;font-size:12px}.note.ok{background:#eaf8ef;border:1px solid #a9d7b4}.note.err{background:#fff0f0;border:1px solid #efb1b1;color:#b42318}.bar{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0}.btn{display:inline-block;border:1px solid #cbd5e1;background:#fff;color:#174a84;padding:8px 11px;border-radius:8px;text-decoration:none;font-weight:700;font-size:12px;cursor:pointer}.primary{background:#1769d1;color:#fff;border-color:#1769d1}.green{background:#188038;color:#fff;border-color:#188038}.red{background:#fff3f3;color:#b42318;border-color:#efb0b0}.layout{display:grid;grid-template-columns:360px 1fr;gap:12px}.panel{background:#fff;border:1px solid #d9e2eb;border-radius:14px;overflow:hidden}.left{max-height:calc(100vh - 165px);overflow:auto}.left h3{margin:0;padding:12px 14px;border-bottom:1px solid #e7edf3;font-size:14px}.tree{padding:9px}.node{border:1px solid #e0e6ed;border-radius:8px;margin:5px 0}.node summary{padding:8px;cursor:pointer}.child{padding:0 8px 8px 17px}.lesson{padding:7px 8px;border-radius:7px;cursor:pointer;display:flex;justify-content:space-between;gap:6px}.lesson:hover,.lesson.active{background:#eaf3ff}.count{color:#64748b;font-size:11px}.right{padding:14px;min-height:600px}.filters{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin:10px 0}.filters label{font-size:11px;font-weight:700;color:#475569}.filters select,.search{width:100%;margin-top:4px;padding:8px;border:1px solid #cbd5e1;border-radius:7px;background:#fff}.search{margin-top:0;font-size:13px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.stat{border:1px solid #dde5ed;border-radius:8px;padding:9px}.stat b{display:block;font-size:18px}.stat span{font-size:10px;color:#64748b}.chips{display:flex;gap:5px;flex-wrap:wrap;margin:9px 0}.chip{padding:4px 7px;border-radius:99px;background:#eef5ff;color:#175ca5;border:1px solid #c8ddfb;font-size:10px;font-weight:700}.row{display:flex;gap:10px;align-items:flex-start;border:1px solid #e0e6ed;border-radius:9px;padding:9px;margin:7px 0}.rowmain{flex:1}.small{font-size:11px;color:#64748b;line-height:1.4;word-break:break-all}.question-list{margin-top:12px;border-top:1px solid #e5ebf1;padding-top:10px}.qitem{border:1px solid #dbe4ec;border-radius:9px;margin:6px 0;padding:9px;cursor:pointer}.qitem.active{background:#eaf3ff;border-color:#72a9e8}.badge{display:inline-block;padding:3px 6px;border-radius:99px;background:#f1f5f9;font-size:10px;font-weight:700;margin-right:3px}.empty{text-align:center;padding:40px;color:#718096}.editor{padding:12px}.edhead{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;flex-wrap:wrap}.qtitle{font-size:18px;font-weight:800}.textarea{width:100%;min-height:510px;margin-top:10px;padding:11px;border:1px solid #bdcad8;border-radius:9px;background:#fcfdff;font:13px/1.55 Consolas,monospace;resize:vertical}.metabox{margin:10px 0;padding:10px;border:1px solid #cfdeed;border-radius:9px;background:#f8fbff}.metagrid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.metagrid label{font-size:11px;font-weight:700;color:#475569}.metagrid input,.metagrid select{width:100%;margin-top:4px;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.preview{margin-top:9px;padding:9px;border:1px dashed #b9cde1;border-radius:9px;background:#fbfdff}.hidden{display:none!important}@media(max-width:950px){.layout{grid-template-columns:1fr}.left{max-height:330px}.filters{grid-template-columns:1fr 1fr}.stats{grid-template-columns:1fr 1fr}}
</style></head><body><div class="wrap">
<div class="top"><div><div class="brand">🐙 NGÂN HÀNG GITHUB — QUẢN LÝ & BIÊN TẬP</div><div class="sub">Nguồn chính: GitHub / ngan-hang/*.tex → bank_index.json → không dùng Google Sheet</div></div><div class="ok">✓ GitHub</div></div>
''' + note + r'''
<div id="managerView">
<div class="bar"><a class="btn" href="/">← Ứng dụng</a><a class="btn primary" href="/ra-de">📝 Ra đề</a><button class="btn" onclick="addQuestion()">➕ Thêm câu</button></div>
<div class="layout"><div class="panel left"><h3>📚 MỤC LỤC</h3><div style="padding:9px"><input id="searchLesson" class="search" placeholder="🔎 Tìm bài / dạng / từ khóa..." oninput="renderManager()"></div><div class="filters" style="padding:0 9px 9px"><label>Môn<select id="fMon" onchange="renderManager()"></select></label><label>Lớp<select id="fLop" onchange="renderManager()"></select></label><label>Chương<select id="fChu" onchange="renderManager()"></select></label><label>Bài<select id="fBai" onchange="renderManager()"></select></label><label>Dạng<select id="fDang" onchange="renderManager()"></select></label></div><div id="tree" class="tree"></div></div>
<div class="panel right"><div id="detail"><div class="empty">Chọn Bài trong mục lục.</div></div></div></div></div>
<div id="editorView" class="hidden"><div class="bar"><button class="btn" onclick="backManager()">← Mục lục</button><button class="btn" onclick="prevQ()">← Câu trước</button><button class="btn" onclick="nextQ()">Câu sau →</button><button class="btn" onclick="duplicateQ()">⧉ Nhân bản</button><button class="btn red" onclick="deleteQ()">🗑 Xóa</button><button class="btn green" onclick="saveFile()">💾 Lưu GitHub</button><button class="btn" onclick="toggleRaw()">🔧 Mã toàn file</button></div><div class="panel editor"><div id="eHead" class="edhead"></div><div id="metaBox" class="metabox"></div><textarea id="qEditor" class="textarea" spellcheck="false"></textarea><div id="preview" class="preview"></div><textarea id="rawEditor" class="textarea hidden" spellcheck="false"></textarea></div></div>
</div><script>
const P=__PAYLOAD__;let S={mon:'',lop:'',chuong:'',bai:'',dang:''},selLesson=null,cur=0;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const uniq=a=>[...new Set(a.filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b),'vi'));
function setSel(id,a,v,label){let e=document.getElementById(id);e.innerHTML='<option value="">'+label+'</option>'+uniq(a).map(x=>'<option value="'+esc(x)+'" '+(x===v?'selected':'')+'>'+esc(x)+'</option>').join('')}
function lessonFiltered(){let q=(document.getElementById('searchLesson').value||'').toLowerCase();return P.meta.filter(x=>{let ok=(!S.mon||x.Mon===S.mon)&&(!S.lop||x.Lop===S.lop)&&(!S.chuong||x.Chuong===S.chuong)&&(!S.bai||x.BaiHoc===S.bai)&&(!S.dang||Object.keys(x.dang||{}).includes(S.dang));let text=(x.BaiHoc+' '+x.De+' '+Object.keys(x.dang||{}).join(' ')).toLowerCase();return ok&&(!q||text.includes(q))})}
function renderManager(){let all=P.meta;let lm=all.filter(x=>!S.mon||x.Mon===S.mon);setSel('fMon',all.map(x=>x.Mon),S.mon,'Tất cả');setSel('fLop',lm.map(x=>x.Lop),S.lop,'Tất cả');let lc=lm.filter(x=>!S.lop||x.Lop===S.lop);setSel('fChu',lc.map(x=>x.Chuong),S.chuong,'Tất cả');let lb=lc.filter(x=>!S.chuong||x.Chuong===S.chuong);setSel('fBai',lb.map(x=>x.BaiHoc),S.bai,'Tất cả');let lf=lb.filter(x=>!S.bai||x.BaiHoc===S.bai),ds=[];lf.forEach(x=>Object.keys(x.dang||{}).forEach(k=>ds.push(k)));setSel('fDang',ds,S.dang,'Tất cả dạng');
let list=lessonFiltered(),g={};list.forEach(x=>{let m=x.Mon||'Khác',l=x.Lop||'?',c=x.Chuong||'Chưa phân chương';g[m]??={};g[m][l]??={};g[m][l][c]??=[];g[m][l][c].push(x)});let h='';for(const m of Object.keys(g)){h+='<details class="node" open><summary><b>'+esc(m)+'</b></summary><div class="child">';for(const l of Object.keys(g[m])){h+='<details class="node" open><summary>Lớp '+esc(l)+'</summary><div class="child">';for(const c of Object.keys(g[m][l])){h+='<details class="node"><summary>'+esc(c)+'</summary><div class="child">';g[m][l][c].forEach(x=>{h+='<div class="lesson '+(selLesson&&selLesson.path===x.path?'active':'')+'" onclick="pickLesson('+JSON.stringify(x.path)+')"><span>'+esc(x.BaiHoc||x.De||x.file)+'</span><span class="count">'+Number(x.questions||x.count||0)+'</span></div>'});h+='</div></details>'}h+='</div></details>'}h+='</div></details>'}document.getElementById('tree').innerHTML=h||'<div class="empty">Không có dữ liệu phù hợp.</div>';renderDetail()}
function pickLesson(p){selLesson=P.meta.find(x=>x.path===p)||null;S={mon:selLesson?.Mon||'',lop:selLesson?.Lop||'',chuong:selLesson?.Chuong||'',bai:selLesson?.BaiHoc||'',dang:''};renderManager()}
function renderDetail(){let a=lessonFiltered(),total=a.reduce((s,x)=>s+Number(x.questions||x.count||0),0),dm={};a.forEach(x=>Object.entries(x.dang||{}).forEach(([k,v])=>dm[k]=(dm[k]||0)+Number(v||0)));if(!selLesson){document.getElementById('detail').innerHTML='<div class="empty">Chọn một Bài để xem dạng và mở câu.</div>';return}let x=selLesson;let h='<h2 style="margin:0">'+esc(x.BaiHoc||x.De||x.file)+'</h2><div class="small">'+esc(x.path||'')+'</div><div class="stats" style="margin-top:10px"><div class="stat"><b>'+Number(x.questions||x.count||0)+'</b><span>câu</span></div><div class="stat"><b>'+Object.keys(x.dang||{}).length+'</b><span>dạng</span></div><div class="stat"><b>'+esc(x.Lop||'')+'</b><span>lớp</span></div><div class="stat"><b>GitHub</b><span>nguồn</span></div></div><div class="chips">';Object.entries(x.dang||{}).forEach(([k,v])=>h+='<span class="chip" onclick="setDang('+JSON.stringify(k)+')" style="cursor:pointer">'+esc(k)+' · '+v+'</span>');h+='</div><div class="bar"><button class="btn primary" onclick="openEditor(0)">✏️ Mở danh sách câu</button><button class="btn" onclick="addQuestion()">➕ Thêm câu</button></div><div class="hint">Bấm một dạng ở trên để lọc khi quản lý câu. Mọi chỉnh sửa đều lưu về đúng file <b>de.tex</b> trên GitHub.</div>';document.getElementById('detail').innerHTML=h}
function setDang(d){S.dang=d;renderManager();openEditor(0)}
function openEditor(n){if(!selLesson){alert('Hãy chọn Bài trước.');return}window.editorPayload=P.editorData||null;document.getElementById('managerView').classList.add('hidden');document.getElementById('editorView').classList.remove('hidden');loadFile(selLesson.path,n)}
async function loadFile(path,n){try{let u='/github/manager-data?path='+encodeURIComponent(path);let r=await fetch(u,{credentials:'same-origin'});let d=await r.json();P.editor=d;cur=Math.max(0,Math.min(n,(d.blocks.length-1)));showQ()}catch(e){alert('Không đọc được file GitHub: '+e.message)}}
function metaBlock(b,i){let m=(re=>{let z=b.match(re);return z?z[1].trim():''});let kind=/\\choiceTF\b/i.test(b)?'B':/\\shortans\b/i.test(b)?'C':/\\choice\b/i.test(b)?'A':'D';let tm=b.match(/\\begin\s*\{ex\}(.*?)(?=\\(?:choiceTF|choice|shortans)\b|\\loigiai\b|\\end\s*\{ex\})/is);let title=tm?tm[1].replace(/%[^\r\n]*/g,'').replace(/\\dangbt\s*\{[^{}]*\}/ig,'').replace(/\s+/g,' ').trim().slice(0,150):'';return {n:i+1,id:m(/%\s*ID\s*:\s*([^\r\n]+)/i),level:m(/%\s*Mức\s*:\s*([^\r\n]+)/i),dang:m(/\\dangbt\s*\{([^{}]*)\}/i),kind,title}}
function showQ(){let b=P.editor.blocks[cur]||'',m=metaBlock(b,cur);document.getElementById('eHead').innerHTML='<div><div class="qtitle">Câu '+(cur+1)+(m.title?' · '+esc(m.title):'')+'</div><div class="small">'+cur+' / '+P.editor.blocks.length+'</div></div><button class="btn" onclick="addQuestion()">➕ Thêm câu</button>';document.getElementById('metaBox').innerHTML='<b>🏷 Phân loại</b><div class="metagrid" style="margin-top:7px"><label>Loại câu<select id="mk"><option value="A">A — Trắc nghiệm</option><option value="B">B — Đúng/Sai</option><option value="C">C — Trả lời ngắn</option><option value="D">D — Tự luận</option></select></label><label>Mức độ<select id="ml"><option value="">—</option><option>NB</option><option>TH</option><option>VD</option><option>VDC</option></select></label><label>Dạng bài<input id="md" value="'+esc(m.dang)+'"></label><label>ID<input id="mi" value="'+esc(m.id)+'"></label></div><div style="margin-top:7px"><button class="btn" onclick="applyMeta()">↻ Ghi phân loại vào câu</button></div>';document.getElementById('mk').value=m.kind;document.getElementById('ml').value=m.level;document.getElementById('qEditor').value=b;let tikz=(b.match(/\\begin\s*\{tikzpicture\}[\s\S]*?\\end\s*\{tikzpicture\}/i)||[])[0];document.getElementById('preview').innerHTML=tikz?'<b>🖼 TikZ/Hình của câu</b><div class="small" style="margin-top:5px">Hình đã nằm trong mã câu và sẽ được giữ khi lưu. Có '+(tikz.match(/\\draw|\\path|\\node/g)||[]).length+' lệnh vẽ.</div>':'<span class="small">Câu này không có TikZ.</span>';document.getElementById('rawEditor').classList.add('hidden')}
function syncCurrent(){if(!P.editor?.blocks?.length)return;P.editor.blocks[cur]=document.getElementById('qEditor').value}
function applyMeta(){syncCurrent();let b=P.editor.blocks[cur],id=document.getElementById('mi').value.trim(),lv=document.getElementById('ml').value.trim(),dg=document.getElementById('md').value.trim(),k=document.getElementById('mk').value;b=b.replace(/%\s*ID\s*:[^\r\n]*\r?\n?/i,'').replace(/%\s*Mức\s*:[^\r\n]*\r?\n?/i,'').replace(/\\dangbt\s*\{[^{}]*\}\s*/ig,'');let bm=b.match(/\\begin\s*\{ex\}/i);if(bm){let lines=[];if(id)lines.push('% ID: '+id);if(lv)lines.push('% Mức: '+lv);b=b.slice(0,bm.index+bm[0].length)+'\n'+lines.join('\n')+'\n'+b.slice(bm.index+bm[0].length);if(dg)b=b.slice(0,bm.index)+'\\dangbt{'+dg+'}\n'+b.slice(bm.index)}let cm=b.match(/\\choiceTF\b|\\choice\b|\\shortans\b/i),want={A:'\\choice',B:'\\choiceTF',C:'\\shortans',D:''}[k];if(cm&&want)b=b.slice(0,cm.index)+want+b.slice(cm.index+cm[0].length);else if(cm&&k==='D')b=b.slice(0,cm.index)+b.slice(cm.index+cm[0].length);P.editor.blocks[cur]=b;showQ()}
function prevQ(){syncCurrent();if(cur>0){cur--;showQ()}}function nextQ(){syncCurrent();if(cur<P.editor.blocks.length-1){cur++;showQ()}}
function addQuestion(){if(!P.editor){if(selLesson)openEditor(0);else alert('Hãy chọn Bài trước.');return}syncCurrent();P.editor.blocks.push('\\begin{ex}\n% ID: NEW-'+Date.now()+'\n% Mức: NB\n\\dangbt{Chưa phân dạng}\nNội dung câu hỏi mới.\n\\choice\n{\\True Phương án A}\n{Phương án B}\n{Phương án C}\n{Phương án D}\n\\loigiai{\n\n}\n\\end{ex}');cur=P.editor.blocks.length-1;showQ()}
function duplicateQ(){syncCurrent();let b=P.editor.blocks[cur].replace(/%\s*ID\s*:[^\r\n]*/i,'% ID: NEW-'+Date.now());P.editor.blocks.splice(cur+1,0,b);cur++;showQ()}
function deleteQ(){if(P.editor.blocks.length<=1)return alert('File phải còn ít nhất một câu.');if(!confirm('Xóa Câu '+(cur+1)+'?'))return;syncCurrent();P.editor.blocks.splice(cur,1);cur=Math.min(cur,P.editor.blocks.length-1);showQ()}
function toggleRaw(){syncCurrent();let r=document.getElementById('rawEditor');if(r.classList.contains('hidden')){r.value=P.editor.head+P.editor.blocks.join('\n\n')+P.editor.tail;r.classList.remove('hidden');document.getElementById('qEditor').classList.add('hidden')}else{let x=r.value,m=x.match(/\\begin\s*\{ex\}[\s\S]*?\\end\s*\{ex\}/ig);if(m){P.editor.blocks=m;P.editor.head=x.slice(0,x.indexOf(m[0]));let end=x.lastIndexOf(m[m.length-1]);P.editor.tail=x.slice(end+m[m.length-1].length)}r.classList.add('hidden');document.getElementById('qEditor').classList.remove('hidden');showQ()}}
async function saveFile(){syncCurrent();let content=P.editor.head+P.editor.blocks.join('\n\n')+P.editor.tail;let fd=new FormData();fd.append('path',P.editor.path);fd.append('sha',P.editor.sha);fd.append('content',content);fd.append('message','ADMIN cập nhật '+P.editor.path);try{let r=await fetch('/github/manager-save',{method:'POST',body:fd,credentials:'same-origin'});let t=await r.text();if(!r.ok)throw new Error(t);document.body.innerHTML=t}catch(e){alert('❌ Lưu thất bại: '+e.message)}}
function backManager(){syncCurrent();document.getElementById('editorView').classList.add('hidden');document.getElementById('managerView').classList.remove('hidden');renderManager()}
renderManager();
</script></body></html>'''
    return html.replace("__PAYLOAD__", j)


def html_escape(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


@bp.get("/github/quan-ly")
def manager():
    if not admin_ok():
        return redirect(url_for("login", next=request.full_path.rstrip("?")))
    data = load_index()
    meta = []
    for x in data.get("lessons", []):
        meta.append({k: x.get(k, "") for k in ("path","file","Mon","Lop","Chuong","BaiHoc","De","questions","count","dang")})
    # data used by browser is small metadata only; full tex is fetched only when a file is opened.
    payload = {"meta": meta}
    return Response(edit_html("", "", "", [], "").replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False)), mimetype="text/html; charset=utf-8")


@bp.get("/github/manager-data")
def manager_data():
    if not admin_ok(): return ("forbidden", 403)
    path = request.args.get("path", "").strip("/")
    if not valid_path(path): return (json.dumps({"error":"path không hợp lệ"}), 400, {"Content-Type":"application/json"})
    sha, raw = fetch_tex(path); head, blocks, tail = split_tex(raw)
    return {"path":path,"sha":sha,"head":head,"blocks":blocks,"tail":tail}


@bp.post("/github/manager-save")
def manager_save():
    if not admin_ok(): return ("forbidden", 403)
    path = request.form.get("path", "").strip("/")
    if not valid_path(path): return ("path không hợp lệ", 400)
    content = request.form.get("content", "")
    posted = request.form.get("sha", "")
    message = request.form.get("message") or f"ADMIN cập nhật {path}"
    owner, repo = REPO.split("/", 1)
    base = f"/repos/{owner}/{repo}/contents/{urllib.parse.quote(path, safe='/')}"
    try:
        current = gh(base + "?ref=main")
        current_sha = current.get("sha", "")
        if posted and posted != current_sha:
            return ("File đã thay đổi trên GitHub. Hãy mở lại file để lấy bản mới nhất.", 409)
        result = gh(base, "PUT", {"message":message,"content":base64.b64encode(content.encode("utf-8")).decode("ascii"),"sha":current_sha,"branch":"main"})
        commit = result.get("commit",{}).get("sha","")[:12]
        return f'<div style="font:16px Arial;padding:30px"><b style="color:#188038">✅ Đã lưu GitHub</b><p>Commit: {html_escape(commit)}</p><a href="/github/quan-ly">← Quay lại quản lý ngân hàng</a></div>'
    except Exception as e:
        return (f"Lưu thất bại: {html_escape(e)}", 500)


# Compatibility: all GitHub bank links use the same new interface.
@bp.get("/github/open")
def open_file():
    p = request.args.get("path", "").strip("/")
    if not valid_path(p): return ("path không hợp lệ", 400)
    return redirect(url_for("github_manager_ui.manager") + "?open=" + urllib.parse.quote(p))


app.register_blueprint(bp)
