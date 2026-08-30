import json
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

# Ra de integration
try:
    from ra_de_fixed import bp as ra_de_bp
    app.register_blueprint(ra_de_bp)
except Exception as e:
    ra_de_bp = None
    app.config['RA_DE_IMPORT_ERROR'] = str(e)

# Robust ADMIN add-question save
try:
    import question_save_fix  # noqa: F401 — registers API route + browser save interceptor
    app.config['QUESTION_SAVE_FIX'] = True
except Exception as e:
    app.config['QUESTION_SAVE_FIX'] = False
    app.config['QUESTION_SAVE_FIX_ERROR'] = str(e)


@app.get('/bank_index.json')
def serve_bank_index():
    """Serve the GitHub-generated question-bank index locally."""
    path = os.path.join(app.root_path, 'bank_index.json')
    return send_file(path, mimetype='application/json', max_age=300, conditional=True)


def _load_bank_index():
    path = os.path.join(app.root_path, 'bank_index.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


@app.after_request
def add_source_links(response):
    """Keep GitHub/Ra de reachable and make the catalog GitHub-first."""
    try:
        if response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)
            low = text.lower()

            if 'data-ldvl-tools="1"' not in text:
                widget = '''
<div data-ldvl-tools="1" style="position:fixed;right:14px;bottom:14px;z-index:99999;display:flex;gap:8px">
  <a href="/ra-de" title="Ra de tu ngan hang GitHub"
     style="display:inline-block;padding:10px 15px;border-radius:10px;background:#1976d2;color:#fff;text-decoration:none;font:700 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">📝 Ra đề</a>
  <a href="/github" title="Doc va quan ly du lieu truc tiep tu GitHub"
     style="display:inline-block;padding:10px 15px;border-radius:10px;background:#24292f;color:#fff;text-decoration:none;font:600 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">🐙 GitHub</a>
</div>
'''
                i = low.rfind('</body>')
                text = text[:i] + widget + text[i:] if i >= 0 else text + widget
                low = text.lower()

            # Put the already-generated index directly into the HTML. This removes
            # the first-load dependency on Google Apps Script / Google Sheets.
            if 'data-ldvl-inline-bank-index="1"' not in text:
                data = _load_bank_index()
                if data:
                    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
                    inline = '<script data-ldvl-inline-bank-index="1">window.__LDVL_BANK_INDEX__=' + payload + ';</script>\n'
                    i = low.rfind('</body>')
                    text = text[:i] + inline + text[i:] if i >= 0 else text + inline
                    low = text.lower()

            # Render the catalog immediately from the local GitHub-generated index.
            # A MutationObserver keeps an old Google-Sheet loader from overwriting it.
            if 'data-ldvl-github-first="2"' not in text:
                fallback = r'''
<script data-ldvl-github-first="2">
(function(){
  const IDS=['publicCatalogContent','deCatalogContent'];
  let rendered=false;
  function esc(v){return String(v??'').replace(/[&<>\\"]/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\"':'&quot;'}[s]));}
  function host(){
    for(const id of IDS){const e=document.getElementById(id); if(e) return e;}
    const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    let n; while(n=w.nextNode()) if((n.nodeValue||'').includes('Đang tải mục lục đề')) return n.parentElement;
    return null;
  }
  function render(h,data){
    if(!h||!data||rendered)return;
    const lessons=Array.isArray(data.lessons)?data.lessons:[];
    const groups={};
    for(const x of lessons){
      const mon=x.Mon||'Khác', lop=x.Lop||'', chuong=x.Chuong||'';
      const key=mon+'|'+lop+'|'+chuong;
      (groups[key]??=[]).push(x);
    }
    const rows=Object.entries(groups).map(([key,items])=>{
      const [mon,lop,chuong]=key.split('|');
      const total=items.reduce((s,x)=>s+Number(x.questions||x.count||0),0);
      const lis=items.map(x=>{
        const p=x.path||x.file||'';
        return '<li style="margin:5px 0"><a href="/github/file?branch=main&path='+encodeURIComponent(p)+'" target="_blank" rel="noopener">'+esc(x.BaiHoc||x.De||p)+'</a> <small>('+Number(x.questions||x.count||0)+' câu)</small></li>';
      }).join('');
      return '<details style="margin:6px 0;padding:8px;border:1px solid #ddd;border-radius:8px"><summary><b>'+esc(mon)+'</b> · Lớp '+esc(lop)+' · '+esc(chuong)+' <small>— '+total+' câu</small></summary><ul>'+lis+'</ul></details>';
    }).join('');
    h.innerHTML='<div style="padding:10px"><div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><b>📚 Mục lục GitHub</b><span>'+Number(data.total_files||lessons.length)+' file · '+Number(data.total_questions||0)+' câu</span><span style="color:#159447;font-weight:700">✓ Tải từ GitHub index</span></div><div style="margin-top:10px">'+(rows||'<i>Chưa có file .tex trong ngan-hang.</i>')+'</div></div>';
    rendered=true;
  }
  function run(){
    const h=host();
    const data=window.__LDVL_BANK_INDEX__;
    if(h&&data)render(h,data);
  }
  function start(){
    run();
    const obs=new MutationObserver(()=>{if(!rendered)run();});
    obs.observe(document.body,{childList:true,subtree:true});
    setTimeout(run,100); setTimeout(run,500); setTimeout(run,1500);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>
'''
                i = low.rfind('</body>')
                text = text[:i] + fallback + text[i:] if i >= 0 else text + fallback

            response.set_data(text)
    except Exception:
        pass
    return response
