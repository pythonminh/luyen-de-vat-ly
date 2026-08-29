import os
from flask import jsonify, send_file
from app import app

# GitHub source integration
try:
    from github_integration import bp as github_bp
    app.register_blueprint(github_bp)
except Exception as e:
    github_bp = None
    app.config['GITHUB_IMPORT_ERROR'] = str(e)

# Ra de integration: wrapper patches the question parser before registering
# the existing Ra de blueprint, so \\dangbt{} outside the ex/bt block is read.
try:
    from ra_de_fixed import bp as ra_de_bp
    app.register_blueprint(ra_de_bp)
except Exception as e:
    ra_de_bp = None
    app.config['RA_DE_IMPORT_ERROR'] = str(e)


@app.get('/bank_index.json')
def serve_bank_index():
    """Serve the GitHub-generated question-bank index with no-cache semantics."""
    path = os.path.join(app.root_path, 'bank_index.json')
    return send_file(path, mimetype='application/json', max_age=0, conditional=False)


@app.after_request
def add_source_links(response):
    """Keep GitHub and Ra de reachable and provide a GitHub index fallback."""
    try:
        if response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)
            if 'data-ldvl-tools="1"' not in text:
                widget = '''
<div data-ldvl-tools="1" style="position:fixed;right:14px;bottom:14px;z-index:99999;display:flex;gap:8px">
  <a href="/ra-de" title="Ra de tu ngan hang GitHub"
     style="display:inline-block;padding:10px 15px;border-radius:10px;background:#1976d2;color:#fff;text-decoration:none;font:700 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">📝 Ra đề</a>
  <a href="/github" title="Doc va quan ly du lieu truc tiep tu GitHub"
     style="display:inline-block;padding:10px 15px;border-radius:10px;background:#24292f;color:#fff;text-decoration:none;font:600 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">🐙 GitHub</a>
</div>
'''
                low = text.lower()
                if '</body>' in low:
                    i = low.rfind('</body>')
                    text = text[:i] + widget + text[i:]
                else:
                    text += widget

            # The legacy UI can leave the catalog on "Đang tải mục lục đề..."
            # while the old data source is unavailable. Keep the legacy UI,
            # but add a small GitHub-backed fallback that reads bank_index.json.
            if 'data-ldvl-github-index-fallback="1"' not in text:
                fallback = r'''
<script data-ldvl-github-index-fallback="1">
(function(){
  const LOADING='Đang tải mục lục đề...';
  const started=Date.now();
  function findLoading(){
    const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    let n;
    while(n=w.nextNode()){
      if((n.nodeValue||'').includes(LOADING)) return n.parentElement;
    }
    return null;
  }
  function esc(v){return String(v??'').replace(/[&<>\"]/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[s]));}
  function render(host,data){
    const lessons=Array.isArray(data.lessons)?data.lessons:[];
    const groups={};
    for(const x of lessons){
      const mon=x.Mon||'Khác', lop=x.Lop||'', chuong=x.Chuong||'', bai=x.BaiHoc||x.De||x.file||'';
      const key=mon+'|'+lop+'|'+chuong;
      (groups[key]??=[]).push(x);
    }
    const rows=Object.entries(groups).map(([key,items])=>{
      const [mon,lop,chuong]=key.split('|');
      const total=items.reduce((s,x)=>s+Number(x.questions||x.count||0),0);
      const lis=items.map(x=>`<li style="margin:4px 0"><a href="/github/file?branch=main&path=${encodeURIComponent(x.path||x.file||'')}" target="_blank" rel="noopener">${esc(x.BaiHoc||x.De||x.file)}</a> <small>(${Number(x.questions||x.count||0)} câu)</small></li>`).join('');
      return `<details style="margin:6px 0;padding:8px;border:1px solid #ddd;border-radius:8px"><summary><b>${esc(mon)}</b> · Lớp ${esc(lop)} · ${esc(chuong)} <small>— ${total} câu</small></summary><ul>${lis}</ul></details>`;
    }).join('');
    host.innerHTML=`<div style="padding:10px"><div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><b>📚 Mục lục từ GitHub</b><span>${Number(data.total_files||lessons.length)} file · ${Number(data.total_questions||0)} câu</span><button type="button" id="ldvl-github-refresh">↻ Tải lại</button></div><div style="margin-top:10px">${rows||'<i>Chưa có file .tex trong ngan-hang.</i>'}</div></div>`;
    const b=host.querySelector('#ldvl-github-refresh'); if(b) b.onclick=()=>location.reload();
  }
  async function run(){
    if(Date.now()-started<2500){setTimeout(run,2500);return;}
    const host=findLoading();
    if(!host) return;
    try{
      const r=await fetch('/bank_index.json?ts='+Date.now(),{cache:'no-store'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      const data=await r.json();
      render(host,data);
    }catch(e){
      host.innerHTML='<b>Không tải được mục lục GitHub.</b><br><small>'+esc(e.message||e)+'</small><br><button onclick="location.reload()">Thử lại</button>';
    }
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',run); else run();
})();
</script>
'''
                low = text.lower()
                if '</body>' in low:
                    i = low.rfind('</body>')
                    text = text[:i] + fallback + text[i:]
                else:
                    text += fallback
                response.set_data(text)
    except Exception:
        pass
    return response
