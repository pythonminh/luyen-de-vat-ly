import os,json,base64,urllib.parse,urllib.request,urllib.error
from flask import Blueprint,request,redirect,url_for,session,render_template_string
bp=Blueprint('github_source',__name__)
API='https://api.github.com'
def gh(path,method='GET',body=None):
 t=os.getenv('GITHUB_TOKEN','').strip()
 if not t: raise RuntimeError('Chưa có GITHUB_TOKEN trên Render → Environment.')
 d=None if body is None else json.dumps(body).encode()
 r=urllib.request.Request(API+path,data=d,method=method,headers={'Authorization':'Bearer '+t,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'luyen-de-vat-ly'})
 try:
  with urllib.request.urlopen(r,timeout=30) as x:return json.loads(x.read().decode())
 except urllib.error.HTTPError as e:
  try:m=json.loads(e.read().decode()).get('message',str(e))
  except:m=str(e)
  raise RuntimeError(f'GitHub API {e.code}: {m}')
def gate():
 if not session.get('mahs'):return redirect(url_for('login',next=request.full_path.rstrip('?')))
 try:
  from app import is_admin
  if not is_admin():return ('<h3>403 — Chỉ ADMIN được dùng GitHub.</h3>',403)
 except:pass
CSS='<style>body{font-family:Arial;background:#f6f8fa;color:#172b4d;margin:0}.w{max-width:1200px;margin:20px auto;padding:0 16px}.c{background:white;border:1px solid #d0d7de;border-radius:12px;padding:16px;margin:12px 0}a,button{padding:8px 12px;border:1px solid #ccd6e0;border-radius:8px;background:white;color:#0969da;text-decoration:none;cursor:pointer}button.d{color:#c22}select,input{padding:9px;width:100%;box-sizing:border-box}.code{white-space:pre-wrap;background:#f6f8fa;padding:14px;max-height:700px;overflow:auto;font-family:Consolas,monospace}</style>'
TPL=CSS+'''<div class=w><h1>🐙 GitHub — {{repo}}</h1><div class=c><form><label>Branch</label><br><br><select name=branch onchange="this.form.submit()">{%for b in bs%}<option {{'selected' if b==branch else ''}}>{{b}}</option>{%endfor%}</select><br><br><label>Đường dẫn</label><br><br><input name=path value="{{path}}" placeholder="ngan-hang/Vật lý/Lớp 11"><br><br><button>🔄 Đọc GitHub</button> <a href="/">Ứng dụng</a></form></div><div class=c><h2>📂 {{path or '/'}}</h2>{%if path%}<a href="{{url_for('github_source.files',branch=branch,path=parent)}}">↩️ Lên một cấp</a>{%endif%}<table width=100%>{%for f in files%}<tr><td style="padding:10px">{%if f.type=='dir'%}📁 <b>{{f.name}}</b>{%else%}📄 {{f.name}}{%endif%}</td><td>{%if f.type=='dir'%}<a href="{{url_for('github_source.files',branch=branch,path=f.path)}}">Mở</a>{%else%}<a href="{{url_for('github_source.read',branch=branch,path=f.path)}}">Đọc</a>{%if branch!='main'%}<form method=post action="{{url_for('github_source.delete')}}" style="display:inline"><input type=hidden name=branch value="{{branch}}"><input type=hidden name=path value="{{f.path}}"><button class=d onclick="return confirm('Xóa file khỏi GitHub?')">Xóa</button></form>{%endif%}{%endif%}</td></tr>{%endfor%}</table></div></div>'''
READ=CSS+'''<div class=w><h1>📄 {{path}}</h1><div class=c><a href="{{url_for('github_source.files',branch=branch,path=parent)}}">← Quay lại</a> · <a href="/">Ứng dụng</a></div><div class=c><div class=code>{{content}}</div></div></div>'''
def getbs(o,r):
 a=gh(f'/repos/{o}/{r}/branches?per_page=100');return [x['name'] for x in a]
@bp.route('/github')
def home():
 g=gate()
 if g:return g
 o,r=(os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').split('/',1);bs=getbs(o,r);return redirect(url_for('github_source.files',branch=bs[0] if bs else 'main'))
@bp.route('/github/files')
def files():
 g=gate()
 if g:return g
 o,r=(os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').split('/',1);branch=request.args.get('branch','main');path=request.args.get('path','').strip('/')
 try:
  bs=getbs(o,r);q=f'/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe="/")}?ref={urllib.parse.quote(branch)}';d=gh(q);d=[d] if isinstance(d,dict) else d;fs=[{'name':x.get('name'),'type':x.get('type'),'path':x.get('path')} for x in d];return render_template_string(TPL,repo=f'{o}/{r}',bs=bs,branch=branch,path=path,parent='/'.join(path.split('/')[:-1]),files=fs)
 except Exception as e:return render_template_string(TPL,repo=f'{o}/{r}',bs=locals().get('bs',[]),branch=branch,path=path,parent='',files=[],error=str(e))
@bp.route('/github/file')
def read():
 g=gate()
 if g:return g
 o,r=(os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').split('/',1);b=request.args.get('branch','main');p=request.args.get('path','').strip('/')
 try:
  d=gh(f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(b)}');c=base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace');return render_template_string(READ,branch=b,path=p,parent='/'.join(p.split('/')[:-1]),content=c)
 except Exception as e:return render_template_string(READ,branch=b,path=p,parent='/'.join(p.split('/')[:-1]),content='LỖI: '+str(e))
@bp.route('/github/delete',methods=['POST'])
def delete():
 g=gate()
 if g:return g
 o,r=(os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').split('/',1);b=request.form['branch'];p=request.form['path'];parent='/'.join(p.split('/')[:-1])
 try:
  if b=='main':raise RuntimeError('Không cho xóa trực tiếp trên main.')
  base=f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}';d=gh(base+'?ref='+urllib.parse.quote(b));gh(base,'DELETE',{'message':f'Delete {p} via app','sha':d['sha'],'branch':b})
 except Exception:pass
 return redirect(url_for('github_source.files',branch=b,path=parent))
