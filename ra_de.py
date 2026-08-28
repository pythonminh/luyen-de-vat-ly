import os, re, random, base64, urllib.parse
from flask import Blueprint, request, render_template_string

try:
    from github_integration import gh
except Exception:
    gh = None

bp = Blueprint('ra_de', __name__)

ROOT = 'ngan-hang/Vật lý'
CSS = '''
<style>
*{box-sizing:border-box}body{font-family:Arial,sans-serif;background:#f4f8fc;color:#17324d;margin:0}
.wrap{max-width:1400px;margin:18px auto;padding:0 18px}.top{background:linear-gradient(135deg,#1769d5,#2d8be8);color:#fff;border-radius:16px;padding:20px 24px;box-shadow:0 6px 20px #0001}
.top h1{margin:0 0 6px;font-size:26px}.top p{margin:0;opacity:.92}.crumb{margin:14px 0;color:#52708f}.crumb a{color:#1769d5;text-decoration:none}
.card{background:#fff;border:1px solid #d9e5f1;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 3px 12px #0000000b}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}.item{display:block;border:1px solid #dbe7f2;border-radius:12px;padding:16px;text-decoration:none;color:#17324d;background:#fff}.item:hover{border-color:#2383e2;box-shadow:0 4px 14px #2383e220}.item b{display:block;margin-bottom:6px}.muted{color:#71869b;font-size:13px}
.row{display:flex;gap:14px;flex-wrap:wrap;align-items:end}.field{min-width:170px;flex:1}.field label{display:block;font-weight:700;margin-bottom:7px}.field input,.field select{width:100%;padding:10px;border:1px solid #cbd9e6;border-radius:9px;background:#fff}
.btn{display:inline-block;border:0;border-radius:10px;padding:11px 18px;background:#1976d2;color:#fff;font-weight:700;cursor:pointer;text-decoration:none}.btn.green{background:#159447}.btn.gray{background:#edf3f8;color:#24435f}.stats{display:flex;gap:8px;flex-wrap:wrap}.pill{padding:6px 10px;border-radius:999px;background:#edf5ff;border:1px solid #cfe3fb;color:#1769d5;font-size:13px;font-weight:700}
.q{border:1px solid #d9e5f1;border-radius:12px;padding:16px;margin:12px 0;background:#fff}.qhead{font-weight:700;color:#1769d5;margin-bottom:8px}.qtext{line-height:1.55;white-space:pre-wrap}.opts{margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:8px}.opt{padding:8px 10px;border:1px solid #e0e8ef;border-radius:8px}.notice{padding:12px;border-radius:10px;background:#fff7df;border:1px solid #f0d48a;color:#775400}
@media(max-width:700px){.opts{grid-template-columns:1fr}.wrap{padding:0 10px}}
</style>'''

TPL = CSS + '''
<div class="wrap">
  <div class="top"><h1>📝 Ra đề</h1><p>Chọn Khối → Chương → Bài → số lượng câu. Câu hỏi lấy trực tiếp từ ngân hàng GitHub.</p></div>
  <div class="crumb"><a href="/">Trang chủ</a> &nbsp;›&nbsp; <a href="/ra-de">Vật lý</a>{% for c in crumbs %} &nbsp;›&nbsp; {{c}}{% endfor %}</div>
  {% if error %}<div class="notice">{{error}}</div>{% endif %}

  {% if folders %}
  <div class="card"><h2>Chọn nội dung</h2><div class="grid">
    {% for f in folders %}<a class="item" href="/ra-de?path={{f.path|urlencode}}"><b>📁 {{f.name}}</b><span class="muted">Mở ngân hàng câu hỏi</span></a>{% endfor %}
  </div></div>
  {% endif %}

  {% if texpath %}
  <div class="card">
    <h2>🎯 {{lesson}}</h2>
    <div class="stats">
      <span class="pill">{{counts.TN}} câu 4 đáp án</span><span class="pill">{{counts.TF}} câu Đúng/Sai</span><span class="pill">{{counts.TLN}} câu trả lời ngắn</span>
    </div>
    <form method="post" action="/ra-de/generate" style="margin-top:16px">
      <input type="hidden" name="path" value="{{path}}">
      <div class="row">
        <div class="field"><label>Trắc nghiệm 4 đáp án</label><input name="tn" type="number" min="0" max="{{counts.TN}}" value="10"></div>
        <div class="field"><label>Đúng / Sai</label><input name="tf" type="number" min="0" max="{{counts.TF}}" value="2"></div>
        <div class="field"><label>Trả lời ngắn</label><input name="tln" type="number" min="0" max="{{counts.TLN}}" value="2"></div>
        <div class="field"><label>Mức độ</label><select name="muc"><option value="all">Tất cả</option><option value="NB">Nhận biết</option><option value="TH">Thông hiểu</option><option value="VD">Vận dụng</option></select></div>
        <div class="field"><label>Thời gian (phút)</label><input name="time" type="number" min="1" value="45"></div>
        <div><button class="btn green">🚀 Tạo đề</button></div>
      </div>
    </form>
  </div>
  {% endif %}
</div>'''

GEN_TPL = CSS + '''
<div class="wrap"><div class="top"><h1>📄 Đề vừa tạo</h1><p>{{lesson}} · {{time}} phút · {{total}} câu</p></div>
<div class="card"><a class="btn gray" href="/ra-de?path={{path|urlencode}}">← Đổi cấu hình</a> <button class="btn" onclick="window.print()">🖨 In đề</button></div>
{% for title, items in sections %}<div class="card"><h2>{{title}}</h2>{% for q in items %}<div class="q"><div class="qhead">Câu {{loop.index}}</div><div class="qtext">{{q.text}}</div>{% if q.options %}<div class="opts">{% for o in q.options %}<div class="opt">{{o}}</div>{% endfor %}</div>{% endif %}</div>{% endfor %}</div>{% endfor %}
</div>'''

def gh_json(path, ref='main'):
    if gh is None:
        raise RuntimeError('Không tải được mô-đun GitHub.')
    q = path
    if '?' not in q:
        q += '?ref=' + urllib.parse.quote(ref)
    return gh(q)

def list_dirs(path, ref='main'):
    data = gh_json('/repos/%s/contents/%s' % ((os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly'), urllib.parse.quote(path, safe='/')), ref)
    if isinstance(data, dict): data = [data]
    return [{'name':x.get('name',''), 'path':x.get('path',''), 'type':x.get('type')} for x in data if x.get('type') == 'dir']

def get_tex(path, ref='main'):
    data = gh_json('/repos/%s/contents/%s' % ((os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly'), urllib.parse.quote(path, safe='/')), ref)
    raw = base64.b64decode((data.get('content') or '').replace('\n','')).decode('utf-8','replace')
    return raw

def parse_questions(tex):
    out=[]
    for block in re.findall(r'\\begin\{ex\}(.*?)\\end\{ex\}', tex, flags=re.S):
        mid = re.search(r'%\s*ID:\s*([^\s\n]+)', block)
        mm = re.search(r'%\s*Mức:\s*(NB|TH|VD|N|H|V)', block, flags=re.I)
        qid = mid.group(1) if mid else ''
        muc = (mm.group(1).upper() if mm else '')
        typ = 'TN'
        if '\\choiceTF' in block: typ='TF'
        elif '\\shortans' in block: typ='TLN'
        elif '\\choice' in block: typ='TN'
        body = re.split(r'\\(?:choiceTF|choice|shortans)', block, maxsplit=1)[0]
        body = re.sub(r'%[^\n]*','',body)
        body = re.sub(r'\\dangbt\{.*?\}','',body,flags=re.S)
        body = re.sub(r'\\nguon\{.*?\}','',body,flags=re.S)
        body = re.sub(r'\\loigiai\{.*','',body,flags=re.S)
        body = re.sub(r'\\label\{.*?\}','',body)
        text = re.sub(r'\n\s*\n+','\n',body).strip()
        opts=[]
        if typ == 'TN':
            rest = block.split('\\choice',1)[1]
            rest = re.split(r'\\loigiai\{|\\end\{ex\}',rest,1)[0]
            opts = [re.sub(r'\\True\s*','',x).strip() for x in re.findall(r'\{((?:[^{}]|\{[^{}]*\})*)\}',rest)]
            opts = opts[:4]
        elif typ == 'TF':
            rest = block.split('\\choiceTF',1)[1]
            rest = re.split(r'\\loigiai\{|\\end\{ex\}',rest,1)[0]
            opts = [re.sub(r'\\True\s*','',x).strip() for x in re.findall(r'\{((?:[^{}]|\{[^{}]*\})*)\}',rest)]
            opts = opts[:4]
        out.append({'id':qid,'muc':muc,'type':typ,'text':text,'options':opts})
    return out

def breadcrumbs(path):
    parts = path.split('/') if path else []
    return parts[2:] if len(parts)>=3 else parts

@bp.route('/ra-de')
def home():
    path = request.args.get('path','').strip('/')
    try:
        if not path:
            folders = list_dirs(ROOT)
            return render_template_string(TPL, folders=folders, path='', crumbs=[], texpath=False, lesson='', counts={'TN':0,'TF':0,'TLN':0}, error=None)
        items = gh_json('/repos/%s/contents/%s' % ((os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly'), urllib.parse.quote(path,safe='/')))
        if isinstance(items, dict): items=[items]
        tex = next((x for x in items if x.get('name') == 'de.tex'), None)
        if tex:
            raw = get_tex(tex['path']); qs=parse_questions(raw)
            counts={'TN':sum(q['type']=='TN' for q in qs),'TF':sum(q['type']=='TF' for q in qs),'TLN':sum(q['type']=='TLN' for q in qs)}
            return render_template_string(TPL, folders=[], path=path, crumbs=breadcrumbs(path), texpath=True, lesson=path.split('/')[-1], counts=counts, error=None)
        folders=[{'name':x.get('name'), 'path':x.get('path')} for x in items if x.get('type')=='dir']
        return render_template_string(TPL, folders=folders, path=path, crumbs=breadcrumbs(path), texpath=False, lesson='', counts={'TN':0,'TF':0,'TLN':0}, error=None)
    except Exception as e:
        return render_template_string(TPL, folders=[], path=path, crumbs=breadcrumbs(path), texpath=False, lesson='', counts={'TN':0,'TF':0,'TLN':0}, error=str(e))

@bp.route('/ra-de/generate', methods=['POST'])
def generate():
    path=request.form.get('path','').strip('/')
    try:
        raw=get_tex(path+'/de.tex'); qs=parse_questions(raw)
        muc=request.form.get('muc','all')
        if muc!='all': qs=[q for q in qs if q['muc'] in (muc, {'NB':'N','TH':'H','VD':'V'}.get(muc,muc))]
        random.shuffle(qs)
        tn=int(request.form.get('tn',10)); tf=int(request.form.get('tf',2)); tln=int(request.form.get('tln',2)); time=request.form.get('time','45')
        pools={k:[q for q in qs if q['type']==k] for k in ('TN','TF','TLN')}
        sections=[('PHẦN A — TRẮC NGHIỆM 4 ĐÁP ÁN',pools['TN'][:tn]),('PHẦN B — ĐÚNG / SAI',pools['TF'][:tf]),('PHẦN C — TRẢ LỜI NGẮN',pools['TLN'][:tln])]
        total=sum(len(x[1]) for x in sections)
        return render_template_string(GEN_TPL, lesson=path.split('/')[-1], path=path, time=time, total=total, sections=sections)
    except Exception as e:
        return render_template_string(CSS+'<div class="wrap"><div class="notice">Lỗi tạo đề: {{e}}</div><a class="btn" href="/ra-de?path={{path|urlencode}}">Quay lại</a></div>', e=str(e), path=path)
''