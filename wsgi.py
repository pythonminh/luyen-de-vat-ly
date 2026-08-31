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

# Easy per-question LaTeX editor
try:
    from github_question_editor import bp as github_question_editor_bp
    app.register_blueprint(github_question_editor_bp)
    app.config['GITHUB_QUESTION_EDITOR'] = True
except Exception as e:
    github_question_editor_bp = None
    app.config['GITHUB_QUESTION_EDITOR'] = False
    app.config['GITHUB_QUESTION_EDITOR_ERROR'] = str(e)

# GitHub-only content source: Mục lục / Ra đề / GitHub editor do GitHub cung cấp.
try:
    import github_source_mode  # noqa: F401 — blocks accidental Google Sheet calls on content pages
    app.config['GITHUB_SOURCE_ONLY'] = True
except Exception as e:
    app.config['GITHUB_SOURCE_ONLY'] = False
    app.config['GITHUB_SOURCE_ONLY_ERROR'] = str(e)


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
            if 'data-ldvl-github-first="2"' not in text:
                fallback = r'''
<script data-ldvl-github-first="2">
(function(){
  let catalogVersion='3';
  function esc(v){return String(v??'').replace(/[&<>\\"]/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\"':'&quot;'}[s]));}
  function data(){return window.__LDVL_BANK_INDEX__ || null;}
  function build(d){
    const lessons=Array.isArray(d.lessons)?d.lessons:[];
    const groups={};
    for(const x of lessons){
      const mon=x.Mon||'Khác', lop=x.Lop||'', chuong=x.Chuong||'Chưa phân chương';
      const key=mon+'|'+lop+'|'+chuong;
      (groups[key]??=[]).push(x);
    }
    const rows=Object.entries(groups).map(([key,items])=>{
      const [mon,lop,chuong]=key.split('|');
      const total=items.reduce((s,x)=>s+Number(x.questions||x.count||0),0);
      const lis=items.map(x=>{
        const p=x.path||x.file||'';
        const title=x.BaiHoc||x.De||p;
        return '<li style="margin:6px 0"><a href="/github/questions?branch=main&path='+encodeURIComponent(p)+'" target="_blank" rel="noopener" style="color:#1967d2;text-decoration:none;font-weight:600">'+esc(title)+'</a> <small style="color:#666">('+Number(x.questions||x.count||0)+' câu)</small></li>';
      }).join('');
      return '<details open style="margin:7px 0;padding:9px 12px;border:1px solid #d7e3f4;border-radius:10px;background:#fff"><summary style="cursor:pointer"><b>'+esc(mon)+'</b> · Lớp '+esc(lop)+' · '+esc(chuong)+' <small style="color:#666">— '+total+' câu</small></summary><ul style="margin:7px 0 0 18px">'+lis+'</ul></details>';
    }).join('');
    return '<div data-ldvl-catalog="'+catalogVersion+'" style="margin-top:10px;border:1px solid #cfe0f5;border-radius:12px;background:#f8fbff;padding:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px"><b style="font-size:16px">📚 Mục lục đề GitHub</b><span style="padding:4px 8px;border-radius:999px;background:#e8f1ff;color:#1769aa;font-weight:700">'+Number(d.total_files||lessons.length)+' file</span><span style="padding:4px 8px;border-radius:999px;background:#eaf7ef;color:#16833b;font-weight:700">'+Number(d.total_questions||0)+' câu</span><span style="color:#16833b;font-weight:700">✓ Dữ liệu GitHub</span></div>'+(rows||'<i>Không tìm thấy file .tex trong ngân hàng.</i>')+'</div>';
  }
  function findShell(){
    const all=[...document.querySelectorAll('body *')];
    for(const el of all){
      const t=(el.textContent||'').trim();
      if(t.includes('Mục lục kiểu sách')) return el;
    }
    return null;
  }
  function mount(){
    const d=data(); if(!d) return false;
    let host=document.getElementById('publicCatalogContent')||document.getElementById('deCatalogContent');
    if(host){host.innerHTML=build(d); host.dataset.ldvlMounted=catalogVersion; return true;}
    const shell=findShell();
    if(!shell) return false;
    if(shell.dataset.ldvlMounted===catalogVersion && shell.nextElementSibling?.querySelector?.('[data-ldvl-catalog="3"]')) return true;
    let block=shell.nextElementSibling;
    if(block && block.querySelector && block.querySelector('[data-ldvl-catalog="3"]')) return true;
    const wrap=document.createElement('div');
    wrap.innerHTML=build(d);
    const node=wrap.firstElementChild;
    shell.parentNode.insertBefore(node,shell.nextSibling);
    shell.dataset.ldvlMounted=catalogVersion;
    return true;
  }
  function start(){
    mount();
    let tries=0;
    const timer=setInterval(()=>{mount(); if(++tries>40) clearInterval(timer);},250);
    const obs=new MutationObserver(()=>mount());
    obs.observe(document.body,{childList:true,subtree:true});
    setTimeout(()=>obs.disconnect(),15000);
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
