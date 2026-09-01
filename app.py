# -*- coding: utf-8 -*-
"""Clean GitHub-only practice portal for Render.
Source of questions: bank_index.json + ngan-hang/**/*.tex
No Google Sheet is used for the question flow.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import random
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, session

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or os.getenv("APP_SECRET") or "dev-change-me"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(os.getenv("RENDER") == "true" or os.getenv("RENDER") == "1"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

REPO = (os.getenv("GITHUB_REPO") or "pythonminh/luyen-de-vat-ly").strip()
BRANCH = (os.getenv("GITHUB_BRANCH") or "main").strip() or "main"
TOKEN = (os.getenv("GITHUB_TOKEN") or "").strip()
ADMIN_USER = (os.getenv("ADMIN_USERNAME") or "ADMIN").strip() or "ADMIN"
ADMIN_PASS = (os.getenv("ADMIN_PASSWORD") or "").strip()
GEMINI_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.getenv("GEMINI_REVIEW_MODEL") or "gemini-2.5-flash").strip()

def github_folder_url(path='ngan-hang'):
    p = str(path or 'ngan-hang').replace('\\', '/').strip('/')
    return f"https://github.com/{REPO}/tree/{urllib.parse.quote(BRANCH, safe='')}/{urllib.parse.quote(p, safe='/')}"

def github_blob_url(path):
    p = str(path or '').replace('\\', '/').strip('/')
    return f"https://github.com/{REPO}/blob/{urllib.parse.quote(BRANCH, safe='')}/{urllib.parse.quote(p, safe='/')}"

def github_web_edit_url(path):
    p = str(path or '').replace('\\', '/').strip('/')
    return f"https://github.com/{REPO}/edit/{urllib.parse.quote(BRANCH, safe='')}/{urllib.parse.quote(p, safe='/')}"

ROOT = Path(__file__).resolve().parent
INDEX_FILE = ROOT / "bank_index.json"
MEMBERS_FILE = ROOT / "members.json"
ACCESS_FILE = ROOT / "lesson_access.json"

EX_RE = re.compile(r"\\begin\s*\{\s*ex\s*\}([\s\S]*?)\\end\s*\{\s*ex\s*\}", re.I)
DANG_RE = re.compile(r"\\dang(?:bt)?\s*\{([^{}]*)\}", re.I)
LEVEL_RE = re.compile(r"%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\r\n%]+)", re.I)
SHORT_RE = re.compile(r"\\shortans\b", re.I)

CSS = r"""
:root{--blue:#176bd3;--blue2:#0f57b4;--line:#d7e2ee;--bg:#f3f7fc;--green:#159447;--red:#cf2d38;--gold:#c98600}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#19324d;font:14px/1.45 Segoe UI,Arial,sans-serif}
a{text-decoration:none;color:#145bb0}.top{background:var(--blue);color:#fff}.topin{max-width:1500px;margin:auto;padding:9px 14px;display:flex;align-items:center;gap:14px}.brand{font-weight:900;font-size:20px}.sub{font-size:11px;opacity:.9}.nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap;align-items:center}.nav a,.who{color:#fff;border:1px solid #ffffff55;background:#ffffff15;padding:7px 10px;border-radius:8px;font-weight:800}.who{background:#ffffff28;font-size:14px;white-space:nowrap}
.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}.head{padding:11px 13px;background:#f8fbff;border-bottom:1px solid var(--line);font-weight:900}.body{padding:12px}.btn{display:inline-block;border:1px solid #b8d5f6;background:#fff;color:#145bb0;border-radius:8px;padding:8px 11px;font-weight:800;cursor:pointer}.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}.btn.green{background:#179b55;border-color:#179b55;color:#fff}.btn.red{background:#fff1f1;border-color:#efb1b1;color:#b5222b}.muted{color:#6c7d90}
.layout{display:grid;grid-template-columns:300px 1fr;gap:10px}.tree{max-height:78vh;overflow:auto}.tree details{border-bottom:1px solid #e8eef5}.tree summary{cursor:pointer;padding:8px 5px;font-weight:900}.tree a{display:block;padding:6px 8px;border-radius:6px}.tree a:hover{background:#eef6ff}.filters{display:grid;gap:8px}.field label{display:block;font-size:11px;color:#66778a;font-weight:800;margin-bottom:3px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd8e6;border-radius:7px;background:#fff}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:9px}.card{border:1px solid #d8e3ee;border-radius:10px;padding:11px;background:#fff}.titlebar{padding:10px 12px;border-radius:10px;background:linear-gradient(90deg,#1c61ce,#5798e7);color:#fff;font-weight:900}.meta{font-size:11px;color:#6a7d90}.tag{display:inline-block;border:1px solid #cbd9e7;border-radius:999px;padding:3px 8px;font-size:11px;margin:2px}.free{background:#eefbf2;border-color:#83d39e;color:#14743a}.vip{background:#fff0f7;border-color:#eaa3c9;color:#a2175f}.dang{margin-top:8px;border:1px solid #d9e5f0;background:#fbfdff;border-radius:8px;padding:7px}.dangrow{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid #edf2f7}.dangrow:last-child{border-bottom:0}
.selectwrap{overflow:auto}.selectgrid{width:100%;border-collapse:collapse;font-size:12px}.selectgrid th,.selectgrid td{border:1px solid #dfe7ef;padding:7px}.selectgrid th{background:#e9f2ff;text-align:center}.n{width:52px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}
.quiztop{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.palette{display:flex;flex-wrap:wrap;gap:5px;padding:9px;background:#f8fbff;border:1px solid var(--line);border-radius:9px;margin-bottom:10px}.pitem{padding:5px 8px;border:1px solid #cad7e6;border-radius:7px;background:#fff;font-size:11px}.pcur{border:2px solid var(--blue);font-weight:900}.pdone{background:#eaf9ef;border-color:#82c99b}.pwrong{background:#fff0f1;border-color:#eca0a7}.qbox{border:1px solid #cfddeb;border-radius:11px;padding:16px}.qtext{font-size:19px;line-height:1.8;margin-bottom:10px}.opt{display:block;border:2px solid #d8e4f0;border-radius:9px;padding:11px;margin:8px 0;cursor:pointer}.opt:hover{background:#f8fbff}.tf{display:flex;align-items:center;gap:12px;border:2px solid #d8e4f0;border-radius:9px;padding:12px 14px;margin:8px 0}.tf-text{flex:1;min-width:0;font-size:18px;line-height:1.7}.tf-picks{display:flex;gap:10px;flex-shrink:0;margin-left:auto}.tf-pick{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-width:118px;padding:12px 18px;border:2px solid #c5d6ea;border-radius:12px;font-size:20px;font-weight:900;cursor:pointer;background:#fff;user-select:none}.tf-pick input{width:22px;height:22px;margin:0;accent-color:var(--blue)}.tf-pick.yes{border-color:#7dbe90;color:#0f6a32;background:#f3fbf6}.tf-pick.no{border-color:#e39aa0;color:#a41f28;background:#fff7f7}.tf-pick:hover{filter:brightness(.97)}.tf-pick:has(input:checked){box-shadow:0 0 0 3px #176bd333;border-width:3px}@media(max-width:700px){.tf{flex-wrap:wrap}.tf-picks{width:100%;margin-left:0}.tf-pick{flex:1}}.correct{background:#e8f8ee!important;border-color:#42ae6b!important}.wrong{background:#fff0f1!important;border-color:#e04d56!important}.solution{margin-top:11px;padding:12px;border:1px solid #bad5f2;border-radius:9px;background:#f7fbff}.result{padding:10px;border-radius:9px;margin-top:10px;font-weight:900}.good{background:#eaf8ef;color:#116a32;border:1px solid #8ed1a2}.bad{background:#fff0f1;color:#a41f28;border:1px solid #efa2a8}.praise{margin:10px 0;padding:11px;border-radius:9px;background:#fff8df;border:1px solid #efca73;color:#855a00;font-size:16px;font-weight:900}.review{margin-top:12px;padding:12px;border:1px solid #cab9f0;background:#faf8ff;border-radius:9px}.reviewout{margin-top:10px;white-space:pre-wrap;line-height:1.7}.gkeyrow{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;align-items:center}.gkeygrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:8px 0}.gkeycell label{display:block;font-size:11px;font-weight:800;color:#66778a;margin-bottom:4px}.gkey-input{width:100%;min-width:0;padding:11px 12px;border:1px solid #cbd8e6;border-radius:8px;font-size:15px}.gkeylink{display:inline-flex;align-items:center;gap:6px;font-weight:900;font-size:16px}.gkeylink:hover{text-decoration:underline}@media(max-width:800px){.gkeygrid{grid-template-columns:1fr}}.adminbox{display:grid;grid-template-columns:1fr 1fr;gap:10px}.code{width:100%;height:70vh;font:12px/1.5 Consolas,monospace;padding:10px;border:1px solid #cbd8e6;border-radius:8px}.notice{padding:10px;border:1px solid #b6d3ef;background:#f4f9ff;border-radius:8px}.err{color:#b42318;font-weight:800}.success{color:#0d7b35;font-weight:800}
@media(max-width:900px){.layout{grid-template-columns:1fr}.adminbox{grid-template-columns:1fr}.tree{max-height:38vh}}
"""

GEMINI_CLIENT_JS = r"""<script>
window.LDVL_GKEY='ldvlGeminiKey';
window.LDVL_GKEYS='ldvlGeminiKeys';
function ldvlGetGeminiKeys(){var arr=['','',''];try{var raw=localStorage.getItem(LDVL_GKEYS);if(raw){var j=JSON.parse(raw);if(Array.isArray(j)){for(var i=0;i<3;i++)arr[i]=String(j[i]||'').trim()}}if(!arr[0]){var old=(localStorage.getItem(LDVL_GKEY)||'').trim();if(old)arr[0]=old}}catch(e){}return arr}
function ldvlFilledKeys(arr){arr=arr||ldvlGetGeminiKeys();return arr.filter(function(k){return String(k||'').trim().length>=20})}
function ldvlReadKeyInputs(){var arr=ldvlGetGeminiKeys();document.querySelectorAll('.gkey-input').forEach(function(el){var i=parseInt(el.getAttribute('data-i'),10);if(i>=0&&i<3)arr[i]=String(el.value||'').trim()});return arr}
function ldvlFillGeminiInputs(){var arr=ldvlGetGeminiKeys();document.querySelectorAll('.gkey-input').forEach(function(el){var i=parseInt(el.getAttribute('data-i'),10);if(!(i>=0&&i<3))i=0;if(!String(el.value||'').trim())el.value=arr[i]||''});var n=ldvlFilledKeys(arr).length;var st=document.getElementById('gkey-status');if(st)st.textContent=n?('✅ Đã có '+n+'/3 key trên máy này.'):'⚠️ Chưa có key — dán 1–3 ô rồi bấm Lưu.';}
function ldvlSaveGeminiKey(){var arr=ldvlReadKeyInputs();var n=ldvlFilledKeys(arr).length;if(!n){alert('Dán ít nhất 1 Gemini API key (thường bắt đầu bằng AIza) vào các ô Key 1–3.');return false}try{localStorage.setItem(LDVL_GKEYS,JSON.stringify(arr));if(arr[0])localStorage.setItem(LDVL_GKEY,arr[0])}catch(e){}ldvlFillGeminiInputs();alert('Đã lưu '+n+' key Gemini trên trình duyệt này.');return true}
function ldvlFmtAi(t){return String(t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>')}
function ldvlGeminiMiniHtml(title){title=title||'🤖 Nạp Key Gemini';return '<div class="review"><b>'+title+'</b><p><a class="gkeylink" href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">🔗 Lấy key miễn phí tại Google AI Studio</a></p><p class="muted">Tạo tối đa 3 key rồi dán vào 3 ô cạnh nhau. Key chỉ lưu trên trình duyệt này.</p><div class="gkeygrid"><div class="gkeycell"><label>Key 1</label><input class="gkey-input" data-i="0" type="password" autocomplete="off" placeholder="AIza... key 1"></div><div class="gkeycell"><label>Key 2</label><input class="gkey-input" data-i="1" type="password" autocomplete="off" placeholder="AIza... key 2"></div><div class="gkeycell"><label>Key 3</label><input class="gkey-input" data-i="2" type="password" autocomplete="off" placeholder="AIza... key 3"></div></div><div class="gkeyrow"><button type="button" class="btn primary" onclick="ldvlSaveGeminiKey()">💾 Lưu 3 key</button><button type="button" class="btn" onclick="ldvlPingGemini()">🧪 Thử key</button></div><div class="muted" id="gkey-status"></div><div id="gkey-ping" class="reviewout"></div></div>'}
async function ldvlGeminiReview(payload,outEl){
  if(!outEl)return;
  var keys=ldvlFilledKeys(ldvlReadKeyInputs());
  if(!keys.length){outEl.innerHTML='<span class="err">Hãy dán Key Gemini vào 1–3 ô rồi bấm Lưu. Link lấy key: <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">Google AI Studio</a>.</span>';return}
  try{localStorage.setItem(LDVL_GKEYS,JSON.stringify(ldvlReadKeyInputs()));localStorage.setItem(LDVL_GKEY,keys[0])}catch(e){}
  outEl.textContent='⏳ Gemini đang phản biện...';
  var body=Object.assign({},payload||{},{api_key:keys[0],api_keys:keys,model:'gemini-2.5-flash'});
  try{
    var r=await fetch('/api/gemini/review_student',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.ok){outEl.innerHTML=ldvlFmtAi(d.text);if(window.ldvlTypeset)ldvlTypeset(outEl);}
    else outEl.innerHTML='<span class="err">'+ldvlFmtAi(d.error||'Lỗi Gemini')+'</span>';
  }catch(e){outEl.innerHTML='<span class="err">'+ldvlFmtAi(e.message||e)+'</span>';}
}
async function ldvlPingGemini(){
  var out=document.getElementById('gkey-ping')||document.getElementById('aiout');
  if(!out)return;
  var keys=ldvlFilledKeys(ldvlReadKeyInputs());
  if(!keys.length){out.innerHTML='<span class="err">Chưa có key. Lấy tại <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">Google AI Studio</a>.</span>';return}
  out.textContent='⏳ Đang thử '+keys.length+' key...';
  try{
    var r=await fetch('/api/gemini/ping',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_keys:keys,api_key:keys[0]})});
    var d=await r.json();
    out.innerHTML=(d.ok?'<span class="success">':'<span class="err">')+ldvlFmtAi(d.text||d.error||'')+'</span>';
  }catch(e){out.innerHTML='<span class="err">'+ldvlFmtAi(e.message||e)+'</span>';}
}
document.addEventListener('DOMContentLoaded',ldvlFillGeminiInputs);
</script>"""

def gemini_panel_html(extra=''):
    return (
        "<div class='review' id='gemini-key'><b>🤖 Nạp Key Gemini</b>"
        "<p><a class='gkeylink' href='https://aistudio.google.com/apikey' target='_blank' rel='noopener'>🔗 Lấy key miễn phí tại Google AI Studio</a></p>"
        "<p class='muted'>Mở link trên → Create API key → dán vào 3 ô cạnh nhau (có thể chỉ điền 1 ô). Key chỉ lưu trên trình duyệt này.</p>"
        "<div class='gkeygrid'>"
        "<div class='gkeycell'><label>Key 1</label><input class='gkey-input' data-i='0' type='password' autocomplete='off' placeholder='AIza... key 1'></div>"
        "<div class='gkeycell'><label>Key 2</label><input class='gkey-input' data-i='1' type='password' autocomplete='off' placeholder='AIza... key 2'></div>"
        "<div class='gkeycell'><label>Key 3</label><input class='gkey-input' data-i='2' type='password' autocomplete='off' placeholder='AIza... key 3'></div>"
        "</div>"
        "<div class='gkeyrow'><button type='button' class='btn primary' onclick='ldvlSaveGeminiKey()'>💾 Lưu 3 key</button>"
        "<button type='button' class='btn' onclick='ldvlPingGemini()'>🧪 Thử key</button></div>"
        "<div class='muted' id='gkey-status'></div>"
        "<div id='gkey-ping' class='reviewout'></div>" + extra + "</div>"
    )

def page(title: str, body: str) -> Response:
    role = session.get("role")
    nav = ["<a href='/member'>📚 Mục lục</a>"]
    who = ""
    if role == "member":
        m = member_current()
        nm = str((m or {}).get("name") or session.get("name") or (m or {}).get("username") or session.get("username") or "").strip()
        if nm:
            who = f"<span class='who'>👤 {html.escape(nm)}</span>"
        nav.append("<a href='/member/ai'>🤖 Gemini</a>")
        nav.append("<a href='/member/logout'>🚪 Thoát</a>")
    elif role == "admin":
        who = "<span class='who'>🔐 ADMIN</span>"
        nav += [
            "<a href='/admin'>📂 ngan-hang</a>",
            f"<a href='{html.escape(github_folder_url(), quote=True)}' target='_blank' rel='noopener'>🐙 GitHub</a>",
            "<a href='/admin/members'>👥 Thành viên</a>",
            "<a href='/admin/logout'>🚪 Thoát</a>",
        ]
    else:
        nav += ["<a href='/member/login'>🔑 Đăng nhập</a>", "<a href='/member/register'>📝 Đăng ký</a>", "<a href='/admin/login'>🔐 ADMIN</a>"]
    top = (
        "<div class='top'><div class='topin'><div><div class='brand'>📚 Luyện Đề Toán Lý</div>"
        "<div class='sub'>Zalo thầy Minh 0946111107</div></div>"
        "<div class='nav'>" + who + "".join(nav) + "</div></div></div>"
    )
    mj = (
        "<script>"
        "window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']],processEscapes:true,packages:{'[+]':['base','ams']}},"
        "options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']},"
        "startup:{typeset:true}};"
        "window.ldvlTypeset=function(el){el=el||document.body;function go(n){"
        "if(window.MathJax&&MathJax.typesetPromise){try{if(MathJax.typesetClear)MathJax.typesetClear([el]);}catch(e){}"
        "return MathJax.typesetPromise([el]).catch(function(){});}"
        "if((n||0)<100)setTimeout(function(){go((n||0)+1);},40);}"
        "go(0);};"
        "</script>"
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js' onerror=\"this.onerror=null;this.src='https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.min.js'\"></script>"
    )
    return Response(f"<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>{CSS}</style>{mj}</head><body>{top}{body}{GEMINI_CLIENT_JS}</body></html>", mimetype='text/html')

def load_json(path: Path, default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def index_data():return load_json(INDEX_FILE, {"lessons": [], "total_files": 0, "total_questions": 0})
def members_data():return load_json(MEMBERS_FILE, {"members": []})
def access_data():
    d=load_json(ACCESS_FILE, {"default":"FREE","lessons":{}}); d.setdefault('default','FREE'); d.setdefault('lessons',{}); return d

def member_current():
    if session.get('role')!='member':return None
    u=str(session.get('username') or '').strip().casefold()
    return next((m for m in members_data().get('members',[]) if str(m.get('username') or '').strip().casefold()==u and str(m.get('status','ON')).upper()=='ON'),None)
def admin_current():return session.get('role')=='admin'
def account_type_of(m):
    s=str((m or {}).get('account_type','FREE')).strip().upper().replace('.','').replace('-','')
    return {'SVIP':'SVIP','VIP':'VIP','ADMIN':'ADMIN'}.get(s,'FREE')
def is_vip(m):return account_type_of(m) in {'VIP','SVIP','ADMIN'}
def lesson_level(path):
    d=access_data(); return str(d['lessons'].get(path,d['default'])).upper()
def can_access(m,path):
    if not m:return False
    typ=account_type_of(m)
    if typ in {'SVIP','ADMIN','VIP'}:return True
    return lesson_level(path)=='FREE'

def _safe_repo_file(path):
    p=str(path or '').replace('\\','/').lstrip('/')
    if not p.startswith('ngan-hang/') or '..' in p.split('/'):raise ValueError('Đường dẫn không hợp lệ.')
    return p, ROOT.joinpath(*p.split('/'))

def gh_api(api_path,method='GET',payload=None):
    if not TOKEN:raise RuntimeError('Thiếu GITHUB_TOKEN trên Render.')
    owner,repo=REPO.split('/',1); body=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(f'https://api.github.com/repos/{owner}/{repo}/{api_path.lstrip("/")}',data=body,method=method,headers={'Authorization':f'Bearer {TOKEN}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'luyen-de-vat-ly-clean'})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        s=e.read().decode('utf-8','replace')
        try:msg=json.loads(s).get('message',s)
        except Exception:msg=s
        raise RuntimeError(f'GitHub API {e.code}: {msg}')

def github_file_sha(path):
    p,_=_safe_repo_file(path)
    d=gh_api(f'contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(BRANCH)}')
    return d.get('sha','')

def _on_render():
    return os.getenv('RENDER') in ('true', '1') or os.getenv('FORCE_GITHUB_TEX') == '1'

def _fetch_tex_remote(path):
    p,_=_safe_repo_file(path)
    if TOKEN:
        d=gh_api(f'contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(BRANCH)}')
        return base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')
    raw_url=f'https://raw.githubusercontent.com/{REPO}/{urllib.parse.quote(BRANCH,safe="")}/{urllib.parse.quote(p,safe="/")}'
    req=urllib.request.Request(raw_url,headers={'User-Agent':'luyen-de-vat-ly-clean','Cache-Control':'no-cache','Pragma':'no-cache'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            return r.read().decode('utf-8','replace')
    except Exception:
        d=gh_api(f'contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(BRANCH)}')
        return base64.b64decode((d.get('content') or '').replace('\n','')).decode('utf-8','replace')

def read_tex(path, need_sha=False):
    if not str(path or '').lower().endswith('.tex'):raise ValueError('Đường dẫn .tex không hợp lệ.')
    p, local=_safe_repo_file(path)
    from_github=_on_render() or need_sha
    text=''
    if from_github:
        try:
            text=_fetch_tex_remote(p)
            try:
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_text(text, encoding='utf-8')
            except Exception:
                pass
        except Exception as e:
            if local.is_file():
                text=local.read_text(encoding='utf-8', errors='replace')
            else:
                raise e
    elif local.is_file():
        text=local.read_text(encoding='utf-8', errors='replace')
    else:
        text=_fetch_tex_remote(p)
        try:
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(text, encoding='utf-8')
        except Exception:
            pass
    sha=''
    if need_sha:
        try:sha=github_file_sha(p)
        except Exception:
            sha=''
    return sha, text

def get_braced(text,pos):
    while pos<len(text) and text[pos].isspace():pos+=1
    if pos>=len(text) or text[pos]!='{':return None,pos
    pos+=1;depth=1;out=[]
    while pos<len(text):
        c=text[pos];prev=text[pos-1] if pos else ''
        if c=='{' and prev!='\\':depth+=1
        elif c=='}' and prev!='\\':
            depth-=1
            if depth==0:return ''.join(out),pos+1
        out.append(c);pos+=1
    return None,pos

def command_args(block,cmd):
    m=re.search(re.escape(cmd)+r'\b',block,re.I)
    if not m:return []
    vals=[];p=m.end()
    while True:
        v,p2=get_braced(block,p)
        if v is None:break
        vals.append(v);p=p2
    return vals

def solution_of(block):
    m=re.search(r'\\loigiai\s*\{',block,re.I)
    if not m:return ''
    v,_=get_braced(block,m.end()-1);return v or ''

def clean_latex_web(s):
    s=re.sub(r'\\begin\s*\{\s*(ex|bt)\s*\}','',s or '',flags=re.I)
    s=re.sub(r'\\end\s*\{\s*(ex|bt)\s*\}','',s,flags=re.I)
    s=re.sub(r'%\s*ID\s*:[^\n]*','',s,flags=re.I)
    s=re.sub(r'%\s*Mức\s*:[^\n]*','',s,flags=re.I)
    s=re.sub(r'\\lq\s*\\lq','«',s,flags=re.I);s=re.sub(r'\\rq\s*\\rq','»',s,flags=re.I)
    s=re.sub(r'\\lq\b','«',s,flags=re.I);s=re.sub(r'\\rq\b','»',s,flags=re.I);s=re.sub(r'\\,',' ',s);return s.strip()

def html_question(s):
    return html.escape(prepare_math(s or '')).replace('\n','<br>\n')

def prepare_math(s):
    """Make LaTeX visible to MathJax: keep $...$ and wrap bare \\overrightarrow{ }."""
    s = clean_latex_web(s or '')
    s = re.sub(r'(?<![\\$])overrightarrow\s*\{([^{}]*)\}', r'\\overrightarrow{\1}', s)
    s = re.sub(r'(?<!\$)\\overrightarrow\s*\{([^{}]*)\}', r'$\\overrightarrow{\1}$', s)
    s = re.sub(r'(?<!\$)\\vec\s*\{([^{}]*)\}', r'$\\vec{\1}$', s)
    s = re.sub(r'\$\$+', '$$', s)
    return s.strip()

def dang_for_pos(tex,pos):
    ms=list(DANG_RE.finditer(tex[:pos]));return ms[-1].group(1).strip() if ms else 'Chưa phân dạng'

def level_of(block):
    vals=[x.strip().upper() for x in LEVEL_RE.findall(block)];s=vals[-1] if vals else 'H'
    if 'VDC' in s or re.search(r'\bC\b',s):return 'C'
    if 'VD' in s:return 'V'
    if 'NB' in s or 'NHAN BIET' in s:return 'N'
    return 'H'

def parse_questions(tex):
    out=[]
    for idx,m in enumerate(EX_RE.finditer(tex)):
        b=m.group(0)
        if re.search(r'\\choiceTF\b',b,re.I):kind='DS'
        elif re.search(r'\\choice\b',b,re.I):kind='TN'
        elif SHORT_RE.search(b):kind='TLN'
        else:kind='TL'
        q={'idx':idx,'dang':dang_for_pos(tex,m.start()),'level':level_of(b),'kind':kind,'text':clean_latex_web(re.split(r'\\choiceTF\b|\\choice\b|\\shortans\b',b,1,flags=re.I)[0]),'solution':clean_latex_web(solution_of(b)),'raw':b}
        if kind=='TN':q['options']=[{'text':clean_latex_web(re.sub(r'^\\True\s*','',x,flags=re.I)),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in command_args(b,'\\choice')[:4]]
        elif kind=='DS':q['statements']=[{'text':clean_latex_web(re.sub(r'^\\True\s*','',x,flags=re.I)),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in command_args(b,'\\choiceTF')]
        elif kind=='TLN':
            sm=re.search(r'\\shortans\s*',b,re.I);ans=''
            if sm:ans,_=get_braced(b,sm.end()-1)
            q['answer']=(ans or '').strip()
        out.append(q)
    return out

KIND_ORDER = ('TN', 'DS', 'TLN', 'TL')

def sort_ids_by_kind(questions, ids, shuffle_within=False):
    """Làm bài: TN → ĐS → TLN → Tự luận. Giữ thứ tự trong từng loại (hoặc xáo trong loại)."""
    by = {q.get('idx'): q for q in (questions or [])}
    buckets = {k: [] for k in KIND_ORDER}
    other = []
    seen = set()
    for i in ids or []:
        try:
            i = int(i)
        except (TypeError, ValueError):
            continue
        if i in seen:
            continue
        seen.add(i)
        k = str((by.get(i) or {}).get('kind') or 'TL')
        if k in buckets:
            buckets[k].append(i)
        else:
            other.append(i)
    if shuffle_within:
        for k in buckets:
            random.shuffle(buckets[k])
        random.shuffle(other)
    out = []
    for k in KIND_ORDER:
        out.extend(buckets[k])
    out.extend(other)
    return out

def norm_answer(s):
    s=clean_latex_web(str(s or ''));s=re.sub(r'\$+','',s).strip().lower();s=s.replace(',','.').replace(' ','');s=re.sub(r'\\text\{([^}]*)\}',r'\1',s);return s
def answer_equal(a,b):
    na,nb=norm_answer(a),norm_answer(b)
    if na==nb:return True
    try:return abs(float(na)-float(nb))<1e-9
    except Exception:return False

def save_json_github(path,data,repo_path,message):
    raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
    path.write_bytes(raw)
    if not TOKEN:
        return
    try:
        cur=gh_api(f'contents/{repo_path}?ref={urllib.parse.quote(BRANCH)}')
        gh_api(f'contents/{repo_path}','PUT',{'message':message,'content':base64.b64encode(raw).decode(),'branch':BRANCH,'sha':cur.get('sha')})
    except Exception:
        pass

@app.get('/health')
def health():return jsonify(ok=True,app='github-bank-clean',repo=REPO,branch=BRANCH)
@app.get('/')
def home():return redirect('/member')
@app.get('/github/repo')
def repo_redirect():return redirect(f'https://github.com/{REPO}')
@app.get('/github/ngan-hang')
def ngan_hang_redirect():return redirect(github_folder_url('ngan-hang'))

@app.route('/member/login',methods=['GET','POST'])
def member_login():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();p=request.form.get('password','');h=hashlib.sha256(p.encode()).hexdigest()
        found=None
        for m in members_data().get('members',[]):
            if str(m.get('username') or '').strip().casefold()==u.casefold() and str(m.get('status','ON')).upper()=='ON' and m.get('password_sha256')==h:
                found=m;break
        if found:
            session.clear();session.permanent=True;session.update(role='member',username=found.get('username'),name=found.get('name') or found.get('username'));return redirect('/member')
        msg='Sai tài khoản hoặc mật khẩu.'
    body=f"<div class='wrap'><div class='panel' style='max-width:430px;margin:60px auto'><div class='head'>👤 Đăng nhập học viên</div><div class='body'><form method='post' action='/member/login'><div class='field'><label>Tài khoản</label><input name='username' autocomplete='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' autocomplete='current-password' required></div><button class='btn primary' type='submit'>Đăng nhập</button> <a class='btn' href='/member/register'>Đăng ký</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>";return page('Đăng nhập',body)

@app.route('/member/register',methods=['GET','POST'])
def member_register():
    msg=''
    if request.method=='POST':
        u=request.form.get('username','').strip();n=request.form.get('name','').strip();p=request.form.get('password','');d=members_data()
        if not u or not p:msg='Nhập tài khoản và mật khẩu.'
        elif len(u)<3:msg='Tài khoản phải từ 3 ký tự.'
        elif len(p)<4:msg='Mật khẩu phải từ 4 ký tự.'
        elif any(str(x.get('username') or '').casefold()==u.casefold() for x in d.get('members',[])):msg='Tài khoản đã tồn tại. Hãy đăng nhập.'
        else:
            d.setdefault('members',[]).append({'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON','password_sha256':hashlib.sha256(p.encode()).hexdigest()})
            try:save_json_github(MEMBERS_FILE,d,'members.json','Add member')
            except Exception as e:msg='Không ghi được tài khoản: '+str(e)
            else:
                session.clear();session.permanent=True;session.update(role='member',username=u,name=n or u);return redirect('/member')
    body=f"<div class='wrap'><div class='panel' style='max-width:430px;margin:60px auto'><div class='head'>📝 Đăng ký thành viên FREE</div><div class='body'><form method='post' action='/member/register'><div class='field'><label>Họ tên</label><input name='name' autocomplete='name'></div><div class='field'><label>Tài khoản</label><input name='username' autocomplete='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' autocomplete='new-password' required></div><button class='btn primary' type='submit'>Tạo tài khoản</button> <a class='btn' href='/member/login'>Đã có tài khoản</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>";return page('Đăng ký',body)

@app.get('/member/logout')
def member_logout():session.clear();return redirect('/member/login')

@app.get('/member/ai')
def member_ai():
    m=member_current()
    if not m:return redirect('/member/login')
    extra="<p class='muted'>Khi làm bài, sau khi chọn đáp án sẽ có nút <b>🤖 Phản biện</b> cho câu đó. Trang kết quả cũng có phản biện từng câu.</p>"
    body=("<div class='wrap'><div class='panel'><div class='head'>🤖 Gemini — nạp key và phản biện</div><div class='body'>"
          +gemini_panel_html(extra)+
          "<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>")
    return page('Key Gemini',body)

@app.get('/member')
def member_index():
    m=member_current()
    if not m:return redirect('/member/login')
    idx=index_data();items=[x for x in idx.get('lessons',[]) if isinstance(x,dict) and str(x.get('path','')).startswith('ngan-hang/')]
    subjects=sorted({str(x.get('Mon') or '') for x in items if x.get('Mon')});classes=sorted({str(x.get('Lop') or '') for x in items if x.get('Lop')});q=request.args.get('q','').strip().lower();sm=request.args.get('mon','');cl=request.args.get('lop','')
    def keep(x):
        t=' '.join(str(x.get(k) or '') for k in ('Mon','Lop','Chuong','BaiHoc','De')).lower();return (not q or q in t) and (not sm or str(x.get('Mon'))==sm) and (not cl or str(x.get('Lop'))==cl)
    items=[x for x in items if keep(x)];groups={}
    for x in items:groups.setdefault((str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or 'Chưa xác định')),[]).append(x)
    sections=[]
    for (mon,lop,chuong),arr in sorted(groups.items()):
        cards=[]
        for x in sorted(arr,key=lambda z:str(z.get('BaiHoc') or z.get('De') or '')):
            path=str(x.get('path'));title=str(x.get('BaiHoc') or x.get('De') or Path(path).parent.name);lvl=lesson_level(path);cnt=int(x.get('questions') or x.get('count') or 0);dangs=x.get('dang') or {};href=urllib.parse.quote(path,safe='');dh=''.join("<a class='dangrow danglink' href='/member/dang?path="+href+"&dang="+urllib.parse.quote(str(k))+"'><span>"+html.escape(str(k))+"</span><span class='tag'>"+str(int(v))+" câu</span></a>" for k,v in dangs.items());lc='vip' if lvl=='VIP' else 'free'
            cards.append("<div class='card'><b>"+html.escape(title)+"</b><div class='meta'>"+html.escape(mon)+" · Lớp "+html.escape(lop)+" · "+html.escape(chuong)+"</div><div><span class='tag "+lc+"'>"+html.escape(lvl)+"</span><span class='tag'>"+str(cnt)+" câu</span></div><div class='dang'><b>📌 Dạng bài</b>"+(dh or "<div class='muted'>Xem trực tiếp từ TEX khi mở bài</div>")+"</div><a class='btn primary' href='/member/select?path="+href+"'>Mở bài</a></div>")
        sections.append("<section style='margin-top:10px'><div class='titlebar'>"+html.escape(mon)+" · Lớp "+html.escape(lop)+" · "+html.escape(chuong)+"</div><div class='cards' style='margin-top:8px'>"+''.join(cards)+"</div></section>")
    subjopts=''.join("<option value='"+html.escape(s,quote=True)+"'"+(" selected" if sm==s else "")+">"+html.escape(s)+"</option>" for s in subjects);classopts=''.join("<option value='"+html.escape(c,quote=True)+"'"+(" selected" if cl==c else "")+">"+html.escape(c)+"</option>" for c in classes)
    body=("<div class='wrap'><div class='panel'><div class='head'>📚 MỤC LỤC · GitHub <span class='tag'>"+str(idx.get('total_files',0))+" file</span><span class='tag'>"+str(idx.get('total_questions',0))+" câu</span></div><div class='body'><div class='notice'>👤 <b>"+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản <b>"+html.escape(str(m.get('username')))+"</b> · Quyền <b>"+html.escape(str(m.get('account_type','FREE')))+"</b></div>"+gemini_panel_html()+"<form method='get' style='display:grid;grid-template-columns:1fr 180px 160px auto;gap:7px;margin-top:10px'><input name='q' placeholder='Tìm bài, chương, dạng...' value='"+html.escape(q)+"'><select name='mon'><option value=''>Tất cả môn</option>"+subjopts+"</select><select name='lop'><option value=''>Tất cả lớp</option>"+classopts+"</select><button class='btn'>Tìm</button></form></div></div>"+(''.join(sections) or "<div class='panel' style='margin-top:10px'><div class='body muted'>Không có bài phù hợp.</div></div>")+"</div>")
    return page('Mục lục',body)

@app.get('/member/select')
def select_page():
    m=member_current();
    if not m:return redirect('/member/login')
    p=request.args.get('path','')
    if not can_access(m,p):return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try:_,tex=read_tex(p);qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    dang_names=[];seen=set()
    for q in qs:
        if q['dang'] not in seen:seen.add(q['dang']);dang_names.append(q['dang'])
    rows=[]
    for di,dang in enumerate(dang_names):
        arr=[q for q in qs if q['dang']==dang]
        for kind,label in [('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]:
            c={z:sum(1 for q in arr if q['kind']==kind and q['level']==z) for z in 'NHVC'};inputs=''.join(f"<input class='n' type='number' min='0' max='{c[z]}' value='0' name='pick:{di}:{kind}:{z}'>" for z in 'NHVC');total=sum(c.values())
            rows.append(f"<tr><td>{html.escape(dang)}</td><td>{label}</td><td>{c['N']}/{c['H']}/{c['V']}/{c['C']}</td><td>{inputs}</td><td>{total}</td></tr>")
    body=f"<div class='wrap'><div class='panel'><div class='head'>🧩 Chọn dạng bài và số câu <span class='tag'>{len(qs)} câu thực tế trong TEX</span></div><div class='body'><form method='post' action='/member/start'><input type='hidden' name='path' value='{html.escape(p,quote=True)}'><div class='selectwrap'><table class='selectgrid'><tr><th>Dạng bài</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>{''.join(rows)}</table></div><div id='sum' class='notice' style='margin-top:10px'>TỔNG CHỌN: 0 câu</div><button class='btn primary'>▶ Tạo bài luyện tập</button> <a class='btn' href='/member'>← Mục lục</a></form></div></div></div><script>function upd(){{let t=0;document.querySelectorAll('.n').forEach(x=>{{let m=Number(x.max)||0,v=Math.max(0,Math.min(m,Number(x.value)||0));x.value=v;t+=v}});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu'}}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',upd));upd();</script>";return page('Chọn câu',body)

@app.post('/member/start')
def start_practice():
    m=member_current();
    if not m:return redirect('/member/login')
    if request.form.getlist('qid'):
        import dang_routes as _dang
        return _dang.start_selected_questions()
    p=request.form.get('path','')
    if not can_access(m,p):return redirect('/member')
    try:_,tex=read_tex(p);qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    picks={}
    for k,v in request.form.items():
        if not k.startswith('pick:'):continue
        try:picks[k]=max(0,int(v or 0))
        except Exception:picks[k]=0
    wanted=[]
    dang_names=[];seen=set()
    for q in qs:
        if q['dang'] not in seen:seen.add(q['dang']);dang_names.append(q['dang'])
    for key,n in picks.items():
        if n<=0:continue
        _,di_s,kind,lev=key.split(':',3);di=int(di_s)
        if 0<=di<len(dang_names):
            pool=[q for q in qs if q['dang']==dang_names[di] and q['kind']==kind and q['level']==lev];wanted.extend(q['idx'] for q in random.sample(pool,min(n,len(pool))))
    if not wanted:return redirect('/member/select?path='+urllib.parse.quote(p,safe=''))
    wanted=sort_ids_by_kind(qs, wanted, shuffle_within=True)
    session.update(practice_path=p,practice_ids=wanted,practice_pos=0,practice_right=0,practice_streak=0,practice_best=0,practice_done=[]);return redirect('/member/practice')

@app.get('/member/practice')
def practice():
    m=member_current();
    if not m:return redirect('/member/login')
    p=str(session.get('practice_path') or '');ids=list(session.get('practice_ids') or []);pos=int(session.get('practice_pos') or 0);right=int(session.get('practice_right') or 0);streak=int(session.get('practice_streak') or 0);best=int(session.get('practice_best') or 0);done=list(session.get('practice_done') or [])
    if not p or not ids:return redirect('/member')
    try:_,tex=read_tex(p);allq={q['idx']:q for q in parse_questions(tex)}
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    if pos>=len(ids):
        score=right/len(ids)*10 if ids else 0
        opts=''.join(f"<option value='{i}'>Câu {i+1} · {'Đúng' if d.get('ok') else 'Sai'}</option>" for i,d in enumerate(done))
        body=(
            f"<div class='wrap'><div class='panel'><div class='head'>🎉 Kết quả <span class='tag'>Đúng {right}/{len(ids)}</span> <span class='tag'>{score:.2f}/10</span></div>"
            f"<div class='body'><div class='result good'>Chuỗi tốt nhất: {best}</div>"
            + gemini_panel_html()
            + f"<div class='review'><b>🤖 Gemini phản biện 1 câu</b><div class='gkeyrow'><select id='pick'>{opts}</select> <button type='button' class='btn primary' onclick='rv()'>🤖 Phản biện</button></div><div id='out' class='reviewout'></div></div>"
            f"<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>"
            f"<script>const D={json.dumps(done,ensure_ascii=False)};function rv(){{ldvlGeminiReview(D[+document.getElementById('pick').value],document.getElementById('out'))}}</script>"
        )
        return page('Kết quả',body)
    q=allq.get(ids[pos]);
    if not q:return redirect('/member')
    palette=''.join(f"<a class='pitem {'pcur' if j==pos else ('pdone' if j<len(done) and done[j].get('ok') else ('pwrong' if j<len(done) else ''))}' href='/practice/jump/{j}'>{j+1} · {allq.get(qid,{}).get('kind','?')}</a>" for j,qid in enumerate(ids))
    payload={'kind':q['kind'],'text':prepare_math(q['text']),'solution':prepare_math(q['solution']),'dang':q['dang'],'level':q['level']}
    if q['kind']=='TN':payload['options']=[{'text':prepare_math(o.get('text','')),'correct':bool(o.get('correct'))} for o in (q.get('options') or [])]
    elif q['kind']=='DS':payload['statements']=[{'text':prepare_math(o.get('text','') if isinstance(o,dict) else o),'correct':bool((o or {}).get('correct') if isinstance(o,dict) else False)} for o in (q.get('statements') or [])]
    elif q['kind']=='TLN':payload['answer']=q.get('answer','')
    body=f"<div class='wrap'><div class='panel'><div class='head quiztop'><span>📝 Câu {pos+1}/{len(ids)} · {html.escape(q['dang'])} · {q['kind']}</span><span>Đúng {right} · Chuỗi {streak}</span></div><div class='body'><div class='palette'>{palette}</div><div id='praise'></div><div id='q' class='qbox'></div><div id='aibox'></div></div></div></div>"
    js=r'''<script>
const Q=__DATA__;let checked=false;
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function typeset(el){if(window.ldvlTypeset)return window.ldvlTypeset(el||document.getElementById('q'));el=el||document.getElementById('q');if(window.MathJax&&MathJax.typesetPromise){try{if(MathJax.typesetClear)MathJax.typesetClear([el]);}catch(e){}MathJax.typesetPromise([el]).catch(function(){});}}
function lockInputs(){document.querySelectorAll('#q input,#q textarea').forEach(function(el){el.disabled=true});let b=document.getElementById('chkbtn');if(b)b.style.display='none'}
function draw(){let q=Q,h='<div class="qtext"><b>Câu __POS__. </b>'+q.text+'</div>';
if(q.kind==='TN')q.options.forEach((o,i)=>h+='<label class="opt" id="o'+i+'"><input type="radio" name="a" value="'+i+'"> <b>'+String.fromCharCode(65+i)+'.</b> '+o.text+'</label>');
else if(q.kind==='DS')q.statements.forEach((s,i)=>h+='<div class="tf" id="t'+i+'"><div class="tf-text"><b>'+(i+1)+'.</b> '+s.text+'</div><div class="tf-picks"><label class="tf-pick yes"><input type="radio" name="t'+i+'" value="1"> Đúng</label><label class="tf-pick no"><input type="radio" name="t'+i+'" value="0"> Sai</label></div></div>');
else if(q.kind==='TLN')h+='<input id="ans" class="answerbox" style="width:100%;padding:10px;border:1px solid #cbd8e6;border-radius:7px" placeholder="Nhập đáp án rồi Enter">';
else h+='<textarea id="ans" class="answerbox" style="width:100%;height:190px;padding:10px;border:1px solid #cbd8e6;border-radius:7px" placeholder="Nhập bài làm"></textarea>';
let needBtn=(q.kind==='TLN'||q.kind==='TL');
h+='<div style="margin-top:10px">'+(needBtn?'<button class="btn primary" id="chkbtn" onclick="check()">✅ Kiểm tra</button>':'')+'<button id="next" class="btn" style="display:none" onclick="location.href=\'/member/practice\'">→ Câu tiếp</button></div><div id="r"></div>';document.getElementById('q').innerHTML=h;typeset(document.getElementById('q'));bind()}
function bind(){let q=Q;if(q.kind==='TN')document.querySelectorAll('input[name=a]').forEach(function(el){el.addEventListener('change',function(){check()})});
else if(q.kind==='DS')document.querySelectorAll('.tf input[type=radio]').forEach(function(el){el.addEventListener('change',dsPick)});
else if(q.kind==='TLN'){let z=document.getElementById('ans');if(z)z.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();check()}})}}
function dsPick(ev){if(checked)return;let i=+String(ev.target.name).slice(1),box=document.getElementById('t'+i);if(!box||box.dataset.done)return;let v=ev.target.value==='1';box.classList.add(v===Q.statements[i].correct?'correct':'wrong');box.dataset.done='1';box.querySelectorAll('input').forEach(function(inp){inp.disabled=true});let all=true;for(let j=0;j<Q.statements.length;j++){if(!document.getElementById('t'+j).dataset.done)all=false}if(all)check()}
function check(){if(checked)return;let q=Q,ok=false,student='';
if(q.kind==='TN'){let z=document.querySelector('input[name=a]:checked');if(!z)return alert('Hãy chọn đáp án.');let i=+z.value;student=String.fromCharCode(65+i);q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')});ok=!!q.options[i].correct}
else if(q.kind==='DS'){ok=true;let a=[];for(let i=0;i<q.statements.length;i++){let z=document.querySelector('input[name=t'+i+']:checked');if(!z)return alert('Chọn đủ Đúng/Sai.');let v=z.value==='1';a.push(v?'Đ':'S');document.getElementById('t'+i).classList.add(v===q.statements[i].correct?'correct':'wrong');if(v!==q.statements[i].correct)ok=false}student=a.join('')}
else{let z=document.getElementById('ans');if(!z||!z.value.trim())return alert('Hãy nhập câu trả lời.');student=z.value.trim();ok=q.kind==='TLN'&&norm(student)===norm(q.answer);}
let note=q.kind==='TL'?'📝 Đã nộp bài tự luận — chờ chấm.':(ok?'✅ ĐÚNG':'❌ SAI');let sol=q.solution||'Chưa có lời giải trong file TEX.';document.getElementById('r').innerHTML='<div class="result '+(ok?'good':'bad')+'">'+note+'</div><div class="solution"><b>📖 Lời giải</b><div>'+sol+'</div></div>';typeset(document.getElementById('q'));checked=true;lockInputs();document.getElementById('next').style.display='inline-block';window.LAST_REVIEW=Object.assign({},q,{student:student,ok:ok});let box=document.getElementById('aibox');if(box){box.innerHTML=ldvlGeminiMiniHtml('🤖 Gemini phản biện câu này')+'<p style="margin-top:10px"><button type="button" class="btn primary" onclick="reviewNow()">🤖 Phản biện</button></p><div id="aiout" class="reviewout"></div>';if(window.ldvlFillGeminiInputs)ldvlFillGeminiInputs()}fetch('/member/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ok:ok,student:student,text:q.text,solution:sol,kind:q.kind,dang:q.dang})}).then(r=>r.json()).then(d=>{if(d.praise)document.getElementById('praise').innerHTML='<div class="praise">'+E(d.praise)+'</div>'})}
function reviewNow(){ldvlGeminiReview(window.LAST_REVIEW,document.getElementById('aiout'))}
function norm(s){return String(s??'').replace(/\$+/g,'').replace(/\s+/g,'').replace(/,/g,'.').toLowerCase()}
draw();</script>'''.replace('__DATA__',json.dumps(payload,ensure_ascii=False)).replace('__POS__',str(pos+1))
    return page('Làm bài',body+js)

@app.post('/member/answer')
def answer():
    m=member_current();
    if not m:return jsonify(ok=False),401
    d=request.get_json(silent=True) or {};ok=bool(d.get('ok'));st=int(session.get('practice_streak') or 0);st=st+1 if ok else 0;best=max(int(session.get('practice_best') or 0),st);right=int(session.get('practice_right') or 0)+(1 if ok else 0);pos=int(session.get('practice_pos') or 0);done=list(session.get('practice_done') or []);praise=''
    if ok:
        if st==3:praise='🎉 Đúng 3 câu liên tiếp! Rất tốt!'
        elif st==5:praise='👏 Đúng 5 câu liên tiếp! Tuyệt vời!'
        elif st==10:praise='🏆 Đúng 10 câu liên tiếp! Xuất sắc!'
    done.append({'question':pos+1,'ok':ok,'student':str(d.get('student') or ''),'text':str(d.get('text') or ''),'solution':str(d.get('solution') or ''),'kind':str(d.get('kind') or ''),'dang':str(d.get('dang') or '')});session.update(practice_streak=st,practice_best=best,practice_right=right,practice_pos=pos+1,practice_done=done);return jsonify(ok=True,praise=praise,streak=st,right=right)

@app.post('/api/gemini/review')
def gemini_review():
    if not member_current():return jsonify(ok=False,error='Chưa đăng nhập'),401
    d=request.get_json(silent=True) or {}
    key=str(d.get('api_key') or '').strip() or GEMINI_KEY
    if not key:return jsonify(ok=False,error='Chưa có key Gemini. Vào mục 🤖 Gemini để nạp key.'),400
    prompt=("Bạn là giáo viên Toán/Vật lý THPT. Phản biện đúng MỘT câu học sinh vừa làm. Trình bày bằng tiếng Việt: câu hỏi, học sinh trả lời gì, đúng/sai, lỗi cụ thể, lời giải đúng từng bước, và kết luận ngắn. Giữ nguyên công thức LaTeX trong $...$.\n\n"+json.dumps(d,ensure_ascii=False))
    url='https://generativelanguage.googleapis.com/v1beta/models/'+urllib.parse.quote(GEMINI_MODEL,safe='')+':generateContent?key='+urllib.parse.quote(key,safe='')
    try:
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=40) as r:x=json.loads(r.read().decode())
        return jsonify(ok=True,text=x['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:return jsonify(ok=False,error=str(e)),500

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    msg=''
    if request.method=='POST':
        if request.form.get('username','').strip()==ADMIN_USER and ADMIN_PASS and request.form.get('password','')==ADMIN_PASS:session.clear();session['role']='admin';return redirect('/admin')
        msg='Sai tài khoản hoặc mật khẩu ADMIN.'
    body=f"<div class='wrap'><div class='panel' style='max-width:430px;margin:60px auto'><div class='head'>🔐 ADMIN</div><div class='body'><form method='post'><div class='field'><label>Tài khoản</label><input name='username' value='{html.escape(ADMIN_USER)}' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' required></div><button class='btn primary'>Đăng nhập</button><div class='err'>{html.escape(msg)}</div></form></div></div></div>";return page('ADMIN',body)

def list_bank_tex():
    items=[];seen=set()
    for x in index_data().get('lessons',[]) or []:
        if not isinstance(x,dict):continue
        p=str(x.get('path') or '').replace('\\','/')
        if not p.startswith('ngan-hang/') or not p.lower().endswith('.tex') or p in seen:continue
        seen.add(p);items.append(x)
    bank=ROOT/'ngan-hang'
    if bank.is_dir():
        for f in sorted(bank.rglob('*.tex')):
            rel=str(f.relative_to(ROOT)).replace('\\','/')
            if rel in seen:continue
            seen.add(rel);items.append({'path':rel,'Mon':'','Lop':'','Chuong':'','BaiHoc':f.parent.name,'De':f.name})
    items.sort(key=lambda z:str(z.get('path') or ''))
    return items

@app.get('/admin')
def admin_home():
    if not admin_current():return redirect('/admin/login')
    gh=github_folder_url('ngan-hang')
    tok='✅ Có GITHUB_TOKEN — có thể commit TEX từ trang này.' if TOKEN else '⚠️ Chưa có GITHUB_TOKEN trên Render. Vẫn mở/sửa được trên GitHub.com; commit từ web sẽ lỗi cho đến khi gắn token.'
    lrows=[]
    for x in list_bank_tex():
        p=str(x.get('path') or '')
        qp=urllib.parse.quote(p,safe='')
        title=str(x.get('BaiHoc') or x.get('De') or Path(p).name)
        lrows.append(
            "<tr><td>"+html.escape(str(x.get('Mon') or ''))+"</td><td>"+html.escape(str(x.get('Lop') or ''))+"</td>"
            "<td>"+html.escape(str(x.get('Chuong') or ''))+"</td><td>"+html.escape(title)+"</td>"
            "<td><code>"+html.escape(p)+"</code></td><td style='white-space:nowrap'>"
            "<a class='btn primary' href='/admin/edit?path="+qp+"'>✏️ Sửa trên web</a> "
            "<a class='btn' href='"+html.escape(github_web_edit_url(p),quote=True)+"' target='_blank' rel='noopener'>🐙 Sửa trên GitHub</a> "
            "<a class='btn' href='"+html.escape(github_blob_url(p),quote=True)+"' target='_blank' rel='noopener'>👁 Xem</a>"
            "</td></tr>"
        )
    body=(
        "<div class='wrap'><div class='panel'><div class='head'>📂 ADMIN · Ngân hàng <code>ngan-hang</code></div><div class='body'>"
        "<div class='notice'><b>Sửa TEX trên GitHub:</b> mở file → tab Edit → sửa → bấm nút xanh <b>Commit changes...</b> → Confirm. "
        "Phải đăng nhập GitHub đúng tài khoản <b>pythonminh</b> (chủ repo). Chỉ mở Edit mà không Commit thì chưa lưu.<br>"
        +html.escape(tok)+" Sau khi Commit, app trên Render đọc bản GitHub ngay (Ctrl+F5), không cần đợi deploy.</div>"
        "<p style='margin:12px 0;display:flex;gap:8px;flex-wrap:wrap'>"
        "<a class='btn primary' href='"+html.escape(gh,quote=True)+"' target='_blank' rel='noopener'>🐙 Mở thư mục ngan-hang trên GitHub</a>"
        "<a class='btn' href='https://github.com/"+html.escape(REPO)+"' target='_blank' rel='noopener'>📦 Repo</a>"
        "<a class='btn' href='/admin/members'>👥 Thành viên</a>"
        "<a class='btn' href='/member'>📚 Mục lục học viên</a>"
        "</p>"
        "<h3>📚 File TEX trong ngan-hang ("+str(len(lrows))+")</h3>"
        "<div style='max-height:62vh;overflow:auto'><table class='selectgrid'><tr><th>Môn</th><th>Lớp</th><th>Chương</th><th>Bài</th><th>Đường dẫn</th><th>Sửa</th></tr>"
        +(''.join(lrows) or "<tr><td colspan='6' class='muted'>Chưa thấy file .tex trong ngan-hang.</td></tr>")
        +"</table></div></div></div></div>"
    )
    return page('ADMIN · ngan-hang',body)

@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')

@app.route('/admin/edit',methods=['GET','POST'])
def admin_edit():
    if not admin_current():return redirect('/admin/login')
    p=request.args.get('path','')
    if request.method=='POST':
        p=request.form.get('path','');new=request.form.get('content','');sha=request.form.get('sha','');msg=request.form.get('message','Cập nhật TEX từ ADMIN')
        if not sha:
            try:sha=github_file_sha(p)
            except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
        try:
            gh_api(f'contents/{urllib.parse.quote(p,safe="/")}?ref={urllib.parse.quote(BRANCH)}','PUT',{'message':msg,'content':base64.b64encode(new.encode()).decode(),'branch':BRANCH,'sha':sha})
            try:
                _, local=_safe_repo_file(p)
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_text(new, encoding='utf-8')
            except Exception:
                pass
            return redirect('/admin/edit?path='+urllib.parse.quote(p,safe='')+'&saved=1')
        except Exception as e:return page('Lỗi commit',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    try:sha,txt=read_tex(p, need_sha=True)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    saved=request.args.get('saved')=='1';notice="<div class='success'>✅ Đã commit lên GitHub.</div>" if saved else ''
    body=(
        "<div class='wrap'><div class='panel'><div class='head'>✏️ ADMIN · Sửa trực tiếp TEX trên GitHub</div><div class='body'>"
        "<div class='meta'><code>"+html.escape(p)+"</code></div>"+notice
        +"<p style='display:flex;gap:8px;flex-wrap:wrap'>"
        "<a class='btn' href='"+html.escape(github_blob_url(p),quote=True)+"' target='_blank' rel='noopener'>👁 Xem trên GitHub</a>"
        "<a class='btn' href='"+html.escape(github_web_edit_url(p),quote=True)+"' target='_blank' rel='noopener'>🐙 Sửa trên github.com</a>"
        "<a class='btn' href='"+html.escape(github_folder_url(),quote=True)+"' target='_blank' rel='noopener'>📂 Thư mục ngan-hang</a>"
        "</p>"
        "<form method='post'><input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'>"
        "<input type='hidden' name='sha' value='"+html.escape(sha,quote=True)+"'>"
        "<textarea name='content' class='code'>"+html.escape(txt)+"</textarea>"
        "<div style='margin-top:8px'><input name='message' value='ADMIN cập nhật TEX' style='width:70%;padding:9px;border:1px solid #cbd8e6;border-radius:7px'>"
        "<button class='btn green'>💾 Commit GitHub</button> <a class='btn' href='/admin'>← Danh sách ngan-hang</a></div></form></div></div></div>"
    )
    return page('Sửa TEX',body)

@app.errorhandler(Exception)
def server_error(exc):
    from werkzeug.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return exc
    return page('Lỗi máy chủ',f"<div class='wrap'><div class='panel'><div class='body'><div class='err'>{html.escape(str(exc))}</div><p><a class='btn' href='/health'>Kiểm tra /health</a></p></div></div></div>"),500

# Always register chọn câu / làm bài, regardless of gunicorn target.
import dang_routes  # noqa: E402,F401
import student_gemini  # noqa: E402,F401
try:
    import admin_overrides as _admin_overrides  # noqa: F401
    import student_overrides as _student_overrides  # noqa: F401
    import security_patch as _security_patch  # noqa: F401
except Exception:
    pass

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
