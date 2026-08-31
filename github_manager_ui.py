# -*- coding: utf-8 -*-
"""Admin GitHub bank manager: tree view Môn > Lớp > Chương > Bài > Dạng."""
from flask import Blueprint, request, session, redirect, url_for, render_template_string
from app import app
import json, os

bp = Blueprint('github_manager_ui', __name__)

CSS = '''<style>
body{margin:0;background:#f3f6fa;color:#17324d;font-family:Arial,sans-serif}.wrap{max-width:1200px;margin:16px auto;padding:0 12px}.box{background:#fff;border:1px solid #d8e1eb;border-radius:14px;box-shadow:0 3px 14px #0001}.head{padding:16px}.title{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #e7edf3;padding-bottom:10px}.mono{font-family:Consolas,monospace}.ok{color:#198754;font-weight:700}.search{width:100%;padding:11px;margin-top:12px;border:1px solid #cbd5e1;border-radius:9px}.filters{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:10px}.filters select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:7px}.body{display:grid;grid-template-columns:430px 1fr;min-height:650px}.left{padding:12px;border-right:1px solid #e5ebf1}.right{padding:14px}.node{border:1px solid #dce4ec;border-radius:9px;margin:6px 0}.node summary{padding:8px;cursor:pointer}.child{padding:0 8px 8px 18px}.lesson{padding:7px;border-radius:7px;cursor:pointer;margin:4px 0}.lesson:hover,.lesson.active{background:#eaf3ff}.count{float:right;color:#64748b}.btn{display:inline-block;padding:8px 11px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;color:#165b9f;text-decoration:none;font-weight:700;font-size:12px}.primary{background:#1769d1;color:#fff;border-color:#1769d1}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.stat{border:1px solid #dde5ed;border-radius:9px;padding:10px}.stat b{display:block;font:700 18px Consolas,monospace}.stat span{font-size:11px;color:#64748b}.chips{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}.chip{padding:5px 8px;border-radius:999px;background:#eef5ff;color:#175ca5;border:1px solid #c8ddfb;font-size:11px;font-weight:700}.row{border:1px solid #e1e7ee;border-radius:9px;padding:10px;margin:7px 0;display:flex;justify-content:space-between;gap:10px}.small{font-size:11px;color:#64748b;line-height:1.35}.empty{text-align:center;color:#718096;padding:40px 10px}.danger{color:#b42318}.toplinks{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}
@media(max-width:900px){.filters{grid-template-columns:1fr 1fr}.body{grid-template-columns:1fr}.left{border-right:0;border-bottom:1px solid #e5ebf1}.stats{grid-template-columns:1fr 1fr}}
</style>'''

HTML = CSS + r'''<div class="wrap"><div class="box"><div class="head"><div class="title"><div class="mono">🐙 NGÂN HÀNG GITHUB</div><div class="ok">✓ GitHub đang hoạt động</div></div><div class="toplinks"><a class="btn" href="/">← Ứng dụng</a><a class="btn primary" href="/ra-de">📝 Ra đề</a></div><input id="search" class="search" placeholder="🔎 Tìm câu hỏi, ID, dạng bài, bài học..." oninput="render()"><div class="filters"><label>Môn<select id="mon" onchange="render()"></select></label><label>Lớp<select id="lop" onchange="render()"></select></label><label>Chương<select id="chuong" onchange="render()"></select></label><label>Bài<select id="bai" onchange="render()"></select></label><label>Dạng<select id="dang" onchange="render()"></select></label></div></div><div class="body"><div class="left"><b class="mono">📚 MỤC LỤC</b><div id="tree"></div></div><div class="right"><div id="detail"><div class="empty">Chọn Môn → Lớp → Chương → Bài.</div></div></div></div></div></div>
<script>
const D={{data}};let L=Array.isArray(D.lessons)?D.lessons:[];let S={mon:'',lop:'',chuong:'',bai:'',dang:''};
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
function vals(a){return [...new Set(a.filter(Boolean))].sort((x,y)=>String(x).localeCompare(String(y),'vi'))}
function set(id,a,v,first){let e=document.getElementById(id);e.innerHTML='<option value="">'+first+'</option>'+vals(a).map(x=>'<option value="'+esc(x)+'" '+(x===v?'selected':'')+'>'+esc(x)+'</option>').join('')}
function base(){return L.filter(x=>(!S.mon||x.Mon===S.mon)&&(!S.lop||x.Lop===S.lop)&&(!S.chuong||x.Chuong===S.chuong)&&(!S.bai||x.BaiHoc===S.bai)&&(!S.dang||Object.prototype.hasOwnProperty.call(x.dang||{},S.dang)))}
function render(){
 let lm=L.filter(x=>!S.mon||x.Mon===S.mon);set('mon',L.map(x=>x.Mon),S.mon,'Tất cả');set('lop',lm.map(x=>x.Lop),S.lop,'Tất cả');let lc=lm.filter(x=>!S.lop||x.Lop===S.lop);set('chuong',lc.map(x=>x.Chuong),S.chuong,'Tất cả');let lb=lc.filter(x=>!S.chuong||x.Chuong===S.chuong);set('bai',lb.map(x=>x.BaiHoc),S.bai,'Tất cả');let ls=base(), ds=[];ls.forEach(x=>Object.keys(x.dang||{}).forEach(k=>ds.push(k)));set('dang',ds,S.dang,'Tất cả dạng');
 let q=(document.getElementById('search').value||'').toLowerCase();renderTree(lm,q);renderDetail(ls,q)
}
function renderTree(list,q){let g={};list.forEach(x=>{let m=x.Mon||'Khác',l=x.Lop||'?',c=x.Chuong||'Chưa phân chương';(g[m]??={});(g[m][l]??={});(g[m][l][c]??=[]).push(x)});let h='';for(const m of Object.keys(g).sort()){h+='<details class="node" open><summary><b>'+esc(m)+'</b></summary><div class="child">';for(const l of Object.keys(g[m]).sort()){h+='<details class="node" open><summary>Lớp '+esc(l)+'</summary><div class="child">';for(const c of Object.keys(g[m][l]).sort()){h+='<details class="node"><summary>'+esc(c)+'</summary><div class="child">';g[m][l][c].forEach(x=>{if(q&&!(x.BaiHoc+' '+x.De+' '+Object.keys(x.dang||{}).join(' ')).toLowerCase().includes(q))return;h+='<div class="lesson" onclick="pick('+JSON.stringify(x.Mon)+','+JSON.stringify(x.Lop)+','+JSON.stringify(x.Chuong)+','+JSON.stringify(x.BaiHoc)+')">'+esc(x.BaiHoc||x.De||x.file)+'<span class="count">'+Number(x.questions||x.count||0)+'</span></div>'});h+='</div></details>'}h+='</div></details>'}h+='</div></details>'}document.getElementById('tree').innerHTML=h||'<div class="empty">Không có dữ liệu.</div>'}
function pick(mon,lop,chuong,bai){S={mon,lop,chuong,bai,dang:''};render()}
function renderDetail(ls,q){let a=ls.filter(x=>{let s=(x.BaiHoc+' '+x.De+' '+Object.keys(x.dang||{}).join(' ')+' '+x.file).toLowerCase();return !q||s.includes(q)});let total=a.reduce((s,x)=>s+Number(x.questions||x.count||0),0),dm={};a.forEach(x=>Object.entries(x.dang||{}).forEach(([k,v])=>dm[k]=(dm[k]||0)+Number(v||0)));let h='<h2 class="mono">'+esc(S.bai||'Ngân hàng câu hỏi')+'</h2><div class="stats"><div class="stat"><b>'+a.length+'</b><span>file</span></div><div class="stat"><b>'+total+'</b><span>câu</span></div><div class="stat"><b>'+Object.keys(dm).length+'</b><span>dạng</span></div><div class="stat"><b>GitHub</b><span>nguồn chính</span></div></div><div class="chips">';Object.entries(dm).forEach(([k,v])=>h+='<span class="chip">'+esc(k)+' · '+v+'</span>');h+='</div>';a.forEach(x=>{let p=x.path||x.file||'',u='/github/questions?branch=main&path='+encodeURIComponent(p);h+='<div class="row"><div><b>'+esc(x.BaiHoc||x.De||x.file)+'</b><div class="small">'+esc(p)+'</div></div><a class="btn" href="'+u+'">✏️ Sửa câu</a></div>'});document.getElementById('detail').innerHTML=h||'<div class="empty">Không tìm thấy.</div>'}
render();
</script>'''

@bp.get('/github/quan-ly')
def manager():
    if not session.get('mahs'):
        return redirect(url_for('login', next=request.full_path.rstrip('?')))
    try:
        from app import is_admin
        if not is_admin():
            return ('<h3>403 — Chỉ ADMIN được dùng chức năng này.</h3>',403)
    except Exception:
        pass
    with open(os.path.join(app.root_path,'bank_index.json'),'r',encoding='utf-8') as f:
        data=json.load(f)
    return render_template_string(HTML,data=json.dumps(data,ensure_ascii=False))

app.register_blueprint(bp)
