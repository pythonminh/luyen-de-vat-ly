import json
import os
from flask import send_file
from app import app

try:
    from github_integration import bp as github_bp
    app.register_blueprint(github_bp)
except Exception as e:
    app.config['GITHUB_IMPORT_ERROR'] = str(e)

try:
    from ra_de_fixed import bp as ra_de_bp
    app.register_blueprint(ra_de_bp)
except Exception as e:
    app.config['RA_DE_IMPORT_ERROR'] = str(e)

try:
    import question_save_fix  # noqa: F401
    app.config['QUESTION_SAVE_FIX'] = True
except Exception as e:
    app.config['QUESTION_SAVE_FIX'] = False
    app.config['QUESTION_SAVE_FIX_ERROR'] = str(e)

try:
    from github_question_editor import bp as github_question_editor_bp
    app.register_blueprint(github_question_editor_bp)
    app.config['GITHUB_QUESTION_EDITOR'] = True
except Exception as e:
    app.config['GITHUB_QUESTION_EDITOR'] = False
    app.config['GITHUB_QUESTION_EDITOR_ERROR'] = str(e)

try:
    import github_source_mode  # noqa: F401
    app.config['GITHUB_SOURCE_ONLY'] = True
except Exception as e:
    app.config['GITHUB_SOURCE_ONLY'] = False
    app.config['GITHUB_SOURCE_ONLY_ERROR'] = str(e)


@app.get('/bank_index.json')
def serve_bank_index():
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
    try:
        if not (response.content_type and 'text/html' in response.content_type):
            return response

        text = response.get_data(as_text=True)
        low = text.lower()

        if 'data-ldvl-tools="1"' not in text:
            widget = '''
<div data-ldvl-tools="1" style="position:fixed;right:14px;bottom:14px;z-index:99999;display:flex;gap:8px">
<a href="/ra-de" style="display:inline-block;padding:10px 15px;border-radius:10px;background:#1976d2;color:#fff;text-decoration:none;font:700 14px Arial,sans-serif">📝 Ra đề</a>
<a href="/github" style="display:inline-block;padding:10px 15px;border-radius:10px;background:#24292f;color:#fff;text-decoration:none;font:600 14px Arial,sans-serif">🐙 GitHub</a>
</div>'''
            i = low.rfind('</body>')
            text = text[:i] + widget + text[i:] if i >= 0 else text + widget
            low = text.lower()

        data = _load_bank_index()
        if data and 'data-ldvl-inline-bank-index="1"' not in text:
            payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
            inline = '<script data-ldvl-inline-bank-index="1">window.__LDVL_BANK_INDEX__=' + payload + ';</script>\n'
            i = low.rfind('</body>')
            text = text[:i] + inline + text[i:] if i >= 0 else text + inline
            low = text.lower()

        if 'data-ldvl-github-catalog="4"' not in text and data:
            # Standalone GitHub catalog. It does not depend on the old catalog's
            # element IDs or its Google-Sheet renderer, so it remains visible even
            # when the legacy Mục lục code renders "0 môn / 0 câu".
            script = r'''<script data-ldvl-github-catalog="4">
(function(){
  function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function render(){
    var d=window.__LDVL_BANK_INDEX__; if(!d || document.getElementById('ldvlGithubCatalog')) return;
    var lessons=Array.isArray(d.lessons)?d.lessons:[];
    var groups={};
    lessons.forEach(function(x){
      var mon=x.Mon||'Khác', lop=x.Lop||'', chuong=x.Chuong||'Chưa phân chương';
      var key=mon+'|'+lop+'|'+chuong;
      if(!groups[key]) groups[key]=[];
      groups[key].push(x);
    });
    var html='';
    Object.keys(groups).forEach(function(key){
      var a=key.split('|'), items=groups[key], total=0, lis='';
      items.forEach(function(x){
        var n=Number(x.questions||x.count||0); total+=n;
        var p=x.path||x.file||'';
        var title=x.BaiHoc||x.De||p;
        lis+='<li style="margin:6px 0"><a href="/github/questions?branch=main&path='+encodeURIComponent(p)+'" target="_blank" rel="noopener" style="color:#1769aa;font-weight:600;text-decoration:none">'+esc(title)+'</a> <span style="color:#666">('+n+' câu)</span></li>';
      });
      html+='<details style="margin:7px 0;border:1px solid #d5e4f5;border-radius:10px;background:#fff;padding:9px 12px"><summary style="cursor:pointer"><b>'+esc(a[0])+'</b> · Lớp '+esc(a[1])+' · '+esc(a[2])+' <span style="color:#666">— '+total+' câu</span></summary><ul style="margin:7px 0 0 18px">'+lis+'</ul></details>';
    });
    var box=document.createElement('section');
    box.id='ldvlGithubCatalog';
    box.style.cssText='margin:18px 16px 40px;padding:14px;border:1px solid #bcd6f3;border-radius:14px;background:#f8fbff;box-shadow:0 2px 10px rgba(0,0,0,.08);font-family:Arial,sans-serif;position:relative;z-index:9998';
    box.innerHTML='<div style="display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-bottom:10px"><b style="font-size:18px">📚 MỤC LỤC ĐỀ — GITHUB</b><span style="background:#e8f1ff;padding:5px 9px;border-radius:999px;color:#1769aa;font-weight:700">'+Number(d.total_files||lessons.length)+' file</span><span style="background:#eaf7ef;padding:5px 9px;border-radius:999px;color:#16833b;font-weight:700">'+Number(d.total_questions||0)+' câu</span><span style="color:#16833b;font-weight:700">✓ Dữ liệu GitHub</span></div>'+html;
    var anchor=null;
    var all=document.querySelectorAll('body *');
    for(var i=0;i<all.length;i++){
      var t=(all[i].textContent||'').trim();
      if(t==='Mục lục kiểu sách'){anchor=all[i];break;}
    }
    if(anchor && anchor.parentNode){anchor.parentNode.parentNode ? anchor.parentNode.parentNode.appendChild(box) : anchor.parentNode.appendChild(box);}
    else if(document.body.firstElementChild) document.body.appendChild(box); else document.body.appendChild(box);
  }
  function start(){render();setTimeout(render,100);setTimeout(render,500);setTimeout(render,1500);setTimeout(render,3000);}
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start); else start();
})();
</script>'''
            i = low.rfind('</body>')
            text = text[:i] + script + text[i:] if i >= 0 else text + script

        response.set_data(text)
    except Exception:
        pass
    return response
