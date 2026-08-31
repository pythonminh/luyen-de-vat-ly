# -*- coding: utf-8 -*-
from flask import Flask, Response, request, redirect, session, jsonify
import os

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET', 'change-this-on-render')

CSS = '''
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#f4f7fb;color:#17324d}.top{background:#1769d2;color:#fff;padding:14px 20px}.wrap{max-width:1100px;margin:30px auto;padding:0 16px}.card{background:#fff;border:1px solid #d5deea;border-radius:12px;padding:20px;box-shadow:0 2px 8px #0000000d}.btn{display:inline-block;padding:9px 14px;border:1px solid #b8d2f3;border-radius:8px;background:#fff;color:#145bb0;text-decoration:none;font-weight:700;margin:4px 4px 4px 0}.field{margin:10px 0}.field label{display:block;font-size:13px;font-weight:700;margin-bottom:4px}.field input{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px}.ok{color:#15803d}.err{color:#b91c1c;font-weight:700}.muted{color:#64748b;font-size:13px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.lesson{padding:14px;border:1px solid #dbe4ee;border-radius:10px;background:#fbfdff}.tag{display:inline-block;padding:4px 8px;border-radius:999px;border:1px solid #cbd5e1;font-size:12px;margin:3px}.free{color:#15733b;background:#effcf3;border-color:#86d8a2}.vip{color:#9b175f;background:#fff0f8;border-color:#f2a5cd}
@media(max-width:700px){.wrap{margin:15px auto}}
'''

def page(title, body):
    return Response("<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+title+"</title><style>"+CSS+"</style><script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]}};</script><script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script></head><body><div class='top'><b>📚 Luyện đề · Thầy Minh</b></div>"+body+"</body></html>",mimetype='text/html')

@app.get('/health')
def health():
    return jsonify(ok=True, app='clean-stable')

@app.get('/')
def home():
    return redirect('/member/login')

@app.route('/member/login', methods=['GET','POST'])
def member_login():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip(); p=request.form.get('password','')
        if u and p:
            session.clear(); session['role']='member'; session['username']=u
            return redirect('/member')
        msg='Vui lòng nhập đủ tài khoản và mật khẩu.'
    return page('Đăng nhập',"<div class='wrap'><div class='card' style='max-width:430px;margin:auto'><h2>👤 Đăng nhập thành viên</h2><form method='post'><div class='field'><label>Tài khoản</label><input name='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn' type='submit'>Đăng nhập</button><a class='btn' href='/admin/login'>ADMIN</a><div class='err'>"+msg+"</div></form></div></div>")

@app.get('/member')
def member_home():
    if session.get('role')!='member': return redirect('/member/login')
    u=session.get('username','')
    return page('Mục lục',"<div class='wrap'><div class='card'><h2>📚 Mục lục GitHub</h2><p>Xin chào <b>"+u+"</b>.</p><p class='muted'>Nguồn chính: GitHub · file <code>ngan-hang/*.tex</code>.</p><div class='grid'><div class='lesson'><b>Ngân hàng câu hỏi</b><div><span class='tag free'>FREE</span><span class='tag vip'>VIP</span></div></div><div class='lesson'><b>GitHub</b><div><a class='btn' href='https://github.com/pythonminh/luyen-de-vat-ly' target='_blank'>Mở GitHub</a></div></div></div><p><a class='btn' href='/member/logout'>Đăng xuất</a></p></div></div>")

@app.get('/member/logout')
def member_logout():
    session.clear(); return redirect('/member/login')

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    user=os.getenv('ADMIN_USERNAME','ADMIN').strip() or 'ADMIN'
    pwd=os.getenv('ADMIN_PASSWORD','').strip()
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip(); p=request.form.get('password','')
        if u==user and pwd and p==pwd:
            session.clear(); session['role']='admin'; return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    return page('ADMIN',"<div class='wrap'><div class='card' style='max-width:430px;margin:auto'><h2>🔐 ADMIN</h2><p class='muted'>Tài khoản mặc định: ADMIN</p><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='ADMIN' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn'>Đăng nhập</button><a class='btn' href='/member/login'>Thành viên</a><div class='err'>"+msg+"</div></form></div></div>")

@app.get('/admin')
def admin_home():
    if session.get('role')!='admin': return redirect('/admin/login')
    return page('ADMIN',"<div class='wrap'><div class='card'><h2>🔐 Khu vực ADMIN</h2><p class='ok'>Đăng nhập ADMIN thành công.</p><p>Hệ thống nền đã chạy ổn. Các chức năng ngân hàng, FREE/VIP và sửa TEX sẽ được nối vào nền này sau khi xác nhận server ổn định.</p><a class='btn' href='/admin/logout'>Đăng xuất</a><a class='btn' href='https://github.com/pythonminh/luyen-de-vat-ly' target='_blank'>GitHub</a></div></div>")

@app.get('/admin/logout')
def admin_logout():
    session.clear(); return redirect('/admin/login')

@app.errorhandler(Exception)
def on_error(exc):
    return page('Lỗi máy chủ',"<div class='wrap'><div class='card'><h2>⚠️ Lỗi máy chủ</h2><p class='err'>"+str(exc)+"</p><a class='btn' href='/health'>Kiểm tra /health</a></div></div>"),500

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
