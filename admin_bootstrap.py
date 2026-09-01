from flask import redirect, request, session

# Load the real application and all existing routes first.
import access_control as _access_control

app = _access_control.app


@app.before_request
def _admin_members_entrypoint():
    # Do not expose the old read-only /admin member table after ADMIN login.
    # Open the authoritative editable member manager instead.
    if request.path.rstrip('/') == '/admin' and session.get('role') == 'admin':
        return redirect('/admin/members')
    return None


@app.after_request
def _admin_members_password_ui(response):
    # The authoritative member page already contains password editing and save.
    # Add a safe show/hide control without changing the existing manager code.
    if request.path.rstrip('/') != '/admin/members':
        return response
    if 'text/html' not in response.headers.get('Content-Type', ''):
        return response
    try:
        body = response.get_data(as_text=True)
        marker = "<input class='pass' name='new_password' form='row_"
        if marker not in body or 'id="toggleMemberPasswords"' in body:
            return response
        body = body.replace(
            "<input class='pass' name='new_password' form='row_",
            "<span class='passwrap'><input class='pass' name='new_password' form='row_",
        )
        body = body.replace(
            " placeholder='Đổi mật khẩu'>",
            " placeholder='Mật khẩu mới'></span>",
        )
        css = """
        <style>
        .passwrap{display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
        .passwrap .pass{width:140px}
        .pass-toggle{border:1px solid #cbd8e6;background:#fff;border-radius:6px;padding:6px 7px;cursor:pointer;font-weight:800;color:#145bb0}
        .pass-toggle:hover{background:#f4f9ff}
        </style>
        """
        js = """
        <script>
        document.addEventListener('DOMContentLoaded', function(){
          document.querySelectorAll('.passwrap').forEach(function(w){
            var input=w.querySelector('input.pass');
            if(!input) return;
            var b=document.createElement('button');
            b.type='button'; b.className='pass-toggle'; b.title='Hiện/ẩn mật khẩu'; b.textContent='👁';
            b.addEventListener('click',function(){
              input.type=input.type==='password'?'text':'password';
              b.textContent=input.type==='password'?'👁':'🙈';
            });
            w.appendChild(b);
          });
        });
        </script>
        """
        body = body.replace('</head>', css + '</head>', 1)
        body = body.replace('</body>', js + '</body>', 1)
        response.set_data(body)
        return response
    except Exception:
        return response
