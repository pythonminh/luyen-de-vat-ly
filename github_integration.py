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
 except Exception:pass

def get_repo():
 return (os.getenv('GITHUB_REPO') or 'pythonminh/luyen-de-vat-ly').split('/',1)

def getbs(o,r):
 a=gh(f'/repos/{o}/{r}/branches?per_page=100');return [x['name'] for x in a]

def is_tex_bank_path(p):
 p=(p or '').strip('/')
 return p.startswith('ngan-hang/') and p.lower().endswith('.tex') and '..' not in p

CSS='''<style>body{font-family:Arial;background:#f6f8fa;color:#172b4d;margin:0}.w{max-width:1400px;margin:20px auto;padding:0 16px}.c{background:white;border:1px solid #d0d7de;border-radius:12px;padding:16px;margin:12px 0}a,button{padding:8px 12px;border:1px solid #ccd6e0;border-radius:8px;background:white;color:#0969da;text-decoration:none;cursor:pointer}button.save{background:#1f883d;color:#fff;border-color:#1f883d}select,input,textarea{padding:9px;width:100%;box-sizing:border-box}textarea.code{min-height:680px;white-space:pre;font-family:Consolas,monospace;font-size:14px;line-height:1.45}.ok{background:#dafbe1;border:1px solid #1a7f37;padding:10px;border-radius:8px}.err{background:#ffebe9;border:1px solid #cf222e;padding:10px;border-radius:8px}.muted{color:#57606a;font-size:13px}</style>'''

TPL=CSS+'''<div class=w><h1>🐙 GitHub — {{repo}}</h1><div class=c><b>ADMIN</b> · Ngân hàng câu hỏi đọc trực tiếp từ GitHub · <span class=muted>Không dùng Google Sheet cho .tex.</span><form style="margin-top:12px"><label>Branch</label><select name=branch onchange="this.form.submit()">{%for b in bs%}<option {{'selected' if b==branch else ''}}>{{b}}</option>{%endfor%}</select><label>Đường dẫn</label><input name=path value="{{path}}" placeholder="ngan-hang/Vật lý/Lớp 11"><button>🔄 Đọc GitHub</button> <a href="/">Ứng dụng</a></form></div><div class=c><h2>📂 {{path or '/'}}</h2>{%if path%}<a href="{{url_for('github_source.files',branch=branch,path=parent)}}">↩️ Lên một cấp</a>{%endif%}{%if error%}<div class=err>{{error}}</div>{%endif%}<table width=100%>{%for f in files%}<tr><td style="padding:10px">{%if f.type=='dir'%}📁 <b>{{f.name}}</b>{%else%}📄 {{f.name}}{%endif%}</td><td>{%if f.type=='dir'%}<a href="{{url_for('github_source.files',branch=branch,path=f.path)}}">Mở</a>{%else%}{%if f.path.startswith('ngan-hang/') and f.path.lower().endswith('.tex')%}<a href="{{url_for('github_source.edit',branch=branch,path=f.path)}}">✏️ Sửa .tex</a>{%else%}<a href="{{url_for('github_source.read',branch=branch,path=f.path)}}">Đọc</a>{%endif%}{%endif%}</td></tr>{%endfor%}</table></div></div>'''

READ=CSS+'''<div class=w><h1>📄 {{path}}</h1><div class=c><a href="{{url_for('github_source.files',branch=branch,path=parent)}}">← Quay lại</a> · {%if editable%}<a href="{{url_for('github_source.edit',branch=branch,path=path)}}">✏️ Sửa .tex</a> · {%endif%}<a href="/">Ứng dụng</a></div><div class=c><pre style="white-space:pre-wrap;background:#f6f8fa;padding:14px;overflow:auto">{{content}}</pre></div></div>'''

EDIT=CSS+'''<div class=w><h1>✏️ Sửa trực tiếp GitHub</h1><div class=c><b>{{path}}</b><p class=muted>ADMIN sửa trực tiếp file LaTeX trong <b>ngan-hang/</b>. Bấm Lưu để tạo commit trên GitHub.</p>{%if msg%}<div class=ok>{{msg}}</div>{%endif%}{%if error%}<div class=err>{{error}}</div>{%endif%}<form method=post action="{{url_for('github_source.save')}}"><input type=hidden name=branch value="{{branch}}"><input type=hidden name=path value="{{path}}"><input type=hidden name=sha value="{{sha}}"><textarea class=code name=content spellcheck=false>{{content}}</textarea><br><label>Nội dung commit</label><input name=message value="ADMIN sửa {{path}}"><br><br><button class=save type=submit>💾 Lưu → GitHub</button> <a href="{{url_for('github_source.files',branch=branch,path=parent)}}">Hủy</a></form><p class=muted>⚡ Sau khi lưu: GitHub commit → Actions tự tạo/cập nhật <b>bank_index.json</b> → app dùng dữ liệu mới.</p></div></div>'''

@bp.route('/github')
def home():
 g=gate()
 if g:return g
 o,r=get_repo();bs=getbs(o,r);return redirect(url_for('github_source.files',branch='main' if 'main' in bs else bs[0]))

@bp.route('/github/files')
def files():
 g=gate()
 if g:return g
 o,r=get_repo();branch=request.args.get('branch','main');path=request.args.get('path','').strip('/')
 try:
  bs=getbs(o,r);q=f'/repos/{o}/{r}/contents/{urllib.parse.quote(path,safe="/")}?ref={urllib.parse.quote(branch)}';d=gh(q);d=[d] if isinstance(d,dict) else d;fs=[{'name':x.get('name'),'type':x.get('type'),'path':x.get('path')} for x in d];return render_template_string(TPL,repo=f'{o}/{r}',bs=bs,branch=branch,path=path,parent='/'.join(path.split('/')[:-1]),files=fs,error='')
 except Exception as e:return render_template_string(TPL,repo=f'{o}/{r}',bs=locals().get('bs',[]),branch=branch,path=path,parent='',files=[],error=str(e))

@bp.route('/github/file')
def read():
 g=gate()
 if g:return g
 o,r=get_repo();b=request.args.get('branch','main');p=request.args.get('path','').strip('/')
 try:
  d=gh(f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(b)}');c=base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace');return render_template_string(READ,branch=b,path=p,parent='/'.join(p.split('/')[:-1]),content=c,editable=is_tex_bank_path(p))
 except Exception as e:return render_template_string(READ,branch=b,path=p,parent='/'.join(p.split('/')[:-1]),content='LỖI: '+str(e),editable=False)

@bp.route('/github/edit')
def edit():
 g=gate()
 if g:return g
 o,r=get_repo();b=request.args.get('branch','main');p=request.args.get('path','').strip('/')
 if b!='main':return ('<h3>Chỉ sửa ngân hàng chính trên main.</h3>',400)
 if not is_tex_bank_path(p):return ('<h3>Chỉ được sửa file .tex trong ngan-hang/.</h3>',403)
 try:
  d=gh(f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(b)}');c=base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace');return render_template_string(EDIT,branch=b,path=p,parent='/'.join(p.split('/')[:-1]),sha=d.get('sha',''),content=c,msg='',error='')
 except Exception as e:return ('<h3>Lỗi đọc GitHub</h3><pre>'+str(e)+'</pre>',500)

@bp.route('/github/save',methods=['POST'])
def save():
 g=gate()
 if g:return g
 o,r=get_repo();b=request.form.get('branch','main');p=request.form.get('path','').strip('/');content=request.form.get('content','');message=request.form.get('message') or f'ADMIN sửa {p}'
 if b!='main':return ('<h3>Chỉ lưu ngân hàng chính trên main.</h3>',400)
 if not is_tex_bank_path(p):return ('<h3>Chỉ được sửa file .tex trong ngan-hang/.</h3>',403)
 try:
  base=f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}';old=gh(base+'?ref='+urllib.parse.quote(b));old_sha=old.get('sha','');posted_sha=request.form.get('sha','')
  if posted_sha and posted_sha!=old_sha:
   latest=base64.b64decode((old.get('content') or '').replace('\n','')).decode('utf-8','replace')
   return render_template_string(EDIT,branch=b,path=p,parent='/'.join(p.split('/')[:-1]),sha=old_sha,content=latest,msg='',error='File đã thay đổi trên GitHub. Đã tải bản mới; kiểm tra lại rồi Lưu.')
  result=gh(base,'PUT',{'message':message,'content':base64.b64encode(content.encode('utf-8')).decode('ascii'),'sha':old_sha,'branch':b})
  commit=result.get('commit',{}).get('sha','')[:12]
  return render_template_string(EDIT,branch=b,path=p,parent='/'.join(p.split('/')[:-1]),sha=result.get('content',{}).get('sha',old_sha),content=content,msg=f'✅ Đã cập nhật GitHub. Commit {commit}',error='')
 except Exception as e:return render_template_string(EDIT,branch=b,path=p,parent='/'.join(p.split('/')[:-1]),sha=request.form.get('sha',''),content=content,msg='',error='Lưu GitHub thất bại: '+str(e))

@bp.route('/github/delete',methods=['POST'])
def delete():
 g=gate()
 if g:return g
 o,r=get_repo();b=request.form['branch'];p=request.form['path'];parent='/'.join(p.split('/')[:-1])
 try:
  if b=='main':raise RuntimeError('Không cho xóa trực tiếp trên main.')
  base=f'/repos/{o}/{r}/contents/{urllib.parse.quote(p,safe="/")}';d=gh(base+'?ref='+urllib.parse.quote(b));gh(base,'DELETE',{'message':f'Delete {p} via app','sha':d['sha'],'branch':b})
 except Exception:pass
 return redirect(url_for('github_source.files',branch=b,path=parent))
