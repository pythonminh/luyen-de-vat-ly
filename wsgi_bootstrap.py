# -*- coding: utf-8 -*-
"""Single Render bootstrap: load the stable app, then all required extensions."""
import re
import wsgi
import student_gemini_ui
import gemini_ui_fix
import member_auth_fix
import gemini_header
import admin_manager

from flask import request, session

app = wsgi.app


@app.after_request
def branding_and_admin_github(response):
    """Apply public branding and expose Gemini/GitHub controls by role."""
    ctype = response.headers.get("Content-Type", "")
    if "text/html" not in ctype:
        return response

    try:
        text = response.get_data(as_text=True)
    except Exception:
        return response

    # Public branding used on laptop, tablet and phone.
    text = text.replace(
        "📚 Ngân hàng câu hỏi GitHub",
        "📚 Luyện Đề Toán Lý <span class='zalo-brand'>Zalo thầy Minh 0946111107</span>",
    )

    is_admin = session.get("role") == "admin"
    is_member = session.get("role") == "member"
    is_practice = request.path == "/member/practice"

    # GitHub is an administration/editing entry point, not a student feature.
    if not is_admin:
        text = re.sub(
            r"<a\s+href=['\"]https://github\.com/[^>]*>\s*🐙\s*GitHub\s*</a>",
            "",
            text,
            flags=re.I,
        )

    # On the practice page, put Gemini controls in the TOP navigation.
    # The API key stays in this browser's localStorage; it is not written to GitHub.
    if is_member and is_practice and "id='topGeminiKeyBtn'" not in text:
        gemini_top = """
        <button type='button' id='topGeminiKeyBtn' class='top-gemini-btn' onclick='openStudentGeminiKey()'>🔑 Gemini</button>
        <button type='button' id='topGeminiReviewBtn' class='top-ai-btn' onclick='askGemini()'>🤖 AI Phản biện</button>
        <script>
        (function(){
          const K='student_gemini_api_key';
          function sync(){
            const has=!!localStorage.getItem(K);
            const b=document.getElementById('topGeminiKeyBtn');
            if(b)b.textContent=has?'🔑 Gemini ✓':'🔑 Gemini';
          }
          window.addEventListener('storage',sync);
          document.addEventListener('DOMContentLoaded',sync);
          setTimeout(sync,500);
        })();
        </script>
        """
        # Put controls immediately before the first ADMIN/GitHub link.
        text = text.replace("<a href='/admin/login'>🔐 ADMIN</a>", gemini_top + "<a href='/admin/login'>🔐 ADMIN</a>", 1)

    responsive_css = """
    <style>
      .zalo-brand{color:#ffd21f;margin-left:6px;font-weight:900;white-space:nowrap}
      .topin{width:100%;max-width:1500px;margin:auto;display:flex;align-items:center;gap:14px;flex-wrap:nowrap}
      .brand{line-height:1.2;white-space:normal}
      .sub{line-height:1.25}
      .nav{margin-left:auto;display:flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:wrap}
      .nav a,.nav button{white-space:nowrap}
      .nav button{font:inherit;color:#fff;border:1px solid #ffffff55;background:#ffffff15;padding:7px 10px;border-radius:8px;font-weight:800;cursor:pointer}
      .nav .top-gemini-btn{border-color:#ffe28a;background:#ffffff1c}
      .nav .top-ai-btn{border-color:#8fe1b0;background:#ffffff1c}
      @media (max-width:900px){
        .topin{align-items:flex-start;flex-wrap:wrap;padding:8px 10px;gap:8px}
        .topin>div:first-child{min-width:0;flex:1 1 100%}
        .brand{font-size:18px}
        .zalo-brand{display:inline}
        .sub{font-size:10px}
        .nav{width:100%;margin-left:0;justify-content:flex-start}
      }
      @media (max-width:480px){
        .brand{font-size:16px}
        .zalo-brand{display:block;margin-left:0;margin-top:2px;font-size:14px}
        .sub{font-size:9px}
        .nav{gap:4px}
        .nav a,.nav button{padding:6px 8px;font-size:12px}
        .wrap{padding:8px}
        .panel{border-radius:10px}
        .qtext{font-size:17px}
      }
      @media (min-width:901px){
        .nav{flex-wrap:nowrap}
      }
    </style>
    """
    text = text.replace("</head>", responsive_css + "</head>", 1)
    response.set_data(text)
    return response
