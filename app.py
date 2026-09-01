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
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

from flask import Flask, Response, abort, jsonify, redirect, request, send_file, session

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

EX_RE = re.compile(r"\\begin\s*\{\s*(?:ex|bt)\s*\}([\s\S]*?)\\end\s*\{\s*(?:ex|bt)\s*\}", re.I)
DANG_RE = re.compile(r"\\dang(?:bt)?\s*\{([^{}]*)\}", re.I)
LEVEL_RE = re.compile(r"%\s*(?:Mức|Muc|Muc do)\s*:\s*([^\r\n%]+)", re.I)
SHORT_RE = re.compile(r"\\shortans\b", re.I)
ID_RE = re.compile(r"%\s*ID\s*:\s*(\S+)", re.I)
CAU_HEAD_RE = re.compile(r"%+\s*[=-]*\s*Câu\s+(\d+)", re.I)

CSS = r"""
:root{--blue:#176bd3;--blue2:#0f57b4;--line:#d7e2ee;--bg:#f3f7fc;--green:#159447;--red:#cf2d38;--gold:#c98600;--figh:320px}
*{box-sizing:border-box}html{height:100%;scroll-padding-top:calc(72px + env(safe-area-inset-top,0px))}body{margin:0;min-height:100dvh;background:var(--bg);color:#19324d;font:14px/1.45 Segoe UI,Arial,sans-serif;overflow-x:hidden;padding-bottom:env(safe-area-inset-bottom,0px)}
a{text-decoration:none;color:#145bb0}.top{position:sticky;top:0;z-index:2147483000;background:var(--blue);color:#fff;box-shadow:0 2px 12px #0004}.topin{max-width:1500px;margin:auto;padding:calc(8px + env(safe-area-inset-top,0px)) calc(14px + env(safe-area-inset-right,0px)) 8px calc(14px + env(safe-area-inset-left,0px));display:flex;align-items:center;gap:10px;flex-wrap:wrap}.brand{font-weight:900;font-size:20px}.sub{font-size:11px;opacity:.9}.clock{margin-left:auto;font:700 12px/1.25 ui-monospace,Consolas,monospace;white-space:nowrap;background:#ffffff22;border:1px solid #ffffff55;border-radius:8px;padding:6px 9px;min-width:12.2em;text-align:center}.nav{display:flex;gap:6px;flex-wrap:wrap;align-items:center}.nav a,.nav button,.who{color:#fff;border:1px solid #ffffff55;background:#ffffff15;padding:7px 10px;border-radius:8px;font-weight:800;cursor:pointer;font:inherit;font-weight:800}.who{background:#ffffff28;font-size:14px;white-space:nowrap}.fsbtn{white-space:nowrap}@media(max-width:700px){.brand{font-size:17px}.clock{font-size:11px;min-width:0;padding:5px 7px}.nav a,.nav button,.who{padding:6px 8px;font-size:13px}}@media(orientation:landscape) and (max-height:500px){.brand{font-size:16px}.sub{display:none}.topin{padding-top:calc(4px + env(safe-area-inset-top,0px));padding-bottom:4px}}
.wrap{max-width:1500px;margin:auto;padding:12px}.panel{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}.head{padding:11px 13px;background:#f8fbff;border-bottom:1px solid var(--line);font-weight:900}.body{padding:12px}.btn{display:inline-block;border:1px solid #b8d5f6;background:#fff;color:#145bb0;border-radius:8px;padding:8px 11px;font-weight:800;cursor:pointer}.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}.btn.green{background:#179b55;border-color:#179b55;color:#fff}.btn.red{background:#fff1f1;border-color:#efb1b1;color:#b5222b}.btn:disabled{opacity:.45;cursor:not-allowed;filter:grayscale(.3)}.muted{color:#6c7d90}
.layout{display:grid;grid-template-columns:300px 1fr;gap:10px}.tree{max-height:78vh;overflow:auto}.tree details{border-bottom:1px solid #e8eef5}.tree summary{cursor:pointer;padding:8px 5px;font-weight:900}.tree a{display:block;padding:6px 8px;border-radius:6px}.tree a:hover{background:#eef6ff}.filters{display:grid;gap:8px}.field label{display:block;font-size:11px;color:#66778a;font-weight:800;margin-bottom:3px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd8e6;border-radius:7px;background:#fff}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:9px}.card{border:1px solid #d8e3ee;border-radius:10px;padding:11px;background:#fff}.titlebar{padding:10px 12px;border-radius:10px;background:linear-gradient(90deg,#1c61ce,#5798e7);color:#fff;font-weight:900}.meta{font-size:11px;color:#6a7d90}.tag{display:inline-block;border:1px solid #cbd9e7;border-radius:999px;padding:3px 8px;font-size:11px;margin:2px}.free{background:#eefbf2;border-color:#83d39e;color:#14743a}.vip{background:#fff0f7;border-color:#eaa3c9;color:#a2175f}.dang{margin-top:8px;border:1px solid #d9e5f0;background:#fbfdff;border-radius:8px;padding:7px}.dangrow{display:flex;flex-direction:column;align-items:stretch;gap:4px;padding:7px 0;border-bottom:1px solid #edf2f7}.dangrow:last-child{border-bottom:0}.danglink{color:inherit}.dangname{font-weight:800;line-height:1.35}.dangkinds{display:flex;flex-wrap:wrap;gap:4px}.kind{display:inline-block;border:1px solid #d3dfeb;border-radius:999px;padding:2px 7px;font-size:11px;font-weight:800;background:#fff}.ktotal{background:#e9f2ff;border-color:#b8d5f6;color:#145bb0}
.selectwrap{overflow:auto}.selectgrid{width:100%;border-collapse:collapse;font-size:12px}.selectgrid th,.selectgrid td{border:1px solid #dfe7ef;padding:7px}.selectgrid thead th{position:sticky;top:0;z-index:4;background:#e9f2ff;box-shadow:0 1px 0 #c5d4e6}.selectgrid th{background:#e9f2ff;text-align:center}.n{width:52px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}
.bankwrap{max-height:62vh;overflow:auto;border:1px solid var(--line);border-radius:8px}.bankwrap .selectgrid{border-collapse:separate;border-spacing:0}.addbank{display:grid;grid-template-columns:1.1fr 90px 1.3fr 1.3fr auto;gap:7px;align-items:end;margin:10px 0;padding:10px;border:1px dashed #b8d5f6;border-radius:9px;background:#f8fbff}.addbank .field{margin:0}
.quiztop{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.qid{display:inline-block;border:1px solid #efca73;border-radius:999px;padding:3px 8px;font-size:12px;font-weight:800;background:#fff7dc;color:#7a5300;font-family:Consolas,monospace}.nguonrow{margin:0 0 8px}.nguon{display:inline-block;border:1px solid #7dd3fc;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;background:#f0f9ff;color:#0369a1}.palette{display:flex;flex-wrap:wrap;gap:5px;padding:9px;background:#f8fbff;border:1px solid var(--line);border-radius:9px;margin-bottom:10px}.pitem{padding:5px 8px;border:1px solid #cad7e6;border-radius:7px;background:#fff;font-size:11px}.pcur{border:2px solid var(--blue);font-weight:900}.pdone{background:#eaf9ef;border-color:#82c99b}.pwrong{background:#fff0f1;border-color:#eca0a7}.qbox{border:1px solid #cfddeb;border-radius:11px;padding:16px}.qtext{font-size:19px;line-height:1.8;margin-bottom:10px}.tikzfig,.tikz-live{display:flex;align-items:center;justify-content:center;overflow:hidden;height:var(--figh);margin:12px 0;padding:8px;border:1px solid #e2e8f0;border-radius:8px;background:#fff}.tikz-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:12px 0;align-items:start}.tikz-row .tikzfig,.tikz-row .tikz-live{margin:0;height:calc(var(--figh) * .7)}.tikzfig svg,.tikz-live svg,.tikzfig img,.tikz-img{max-width:100%;max-height:100%;width:auto;height:auto;display:block;margin:0 auto;object-fit:contain}@media(max-width:700px){.tikzfig,.tikz-live{height:calc(var(--figh) * .68)}}.tikz-live:has(svg) .tikz-wait{display:none}.ytbox{margin:12px 0;max-width:min(100%,620px)}.ytplay{display:flex;align-items:center;justify-content:center;gap:12px;width:100%;aspect-ratio:16/9;padding:0;border:1px solid #cfddeb;border-radius:11px;background:#0b1220 center/cover no-repeat;color:#fff;font-weight:900;font-size:15px;cursor:pointer;text-shadow:0 1px 4px #000c;box-shadow:inset 0 0 0 300px #0b122059}.ytplay:hover .ytplay-ico{background:#f00}.ytplay-ico{display:inline-flex;align-items:center;justify-content:center;width:56px;height:39px;border-radius:9px;background:#e60000cc;font-size:18px;text-shadow:none}.ytframe{display:block;width:100%;aspect-ratio:16/9;border:0;border-radius:11px}.ytlink{display:inline-block;margin-top:5px;font-size:12px;font-weight:800}.exlink{display:inline-block;margin:6px 0;font-weight:800}.tex-table{border-collapse:collapse;margin:10px auto;font-size:15px;background:#fff}.tex-table td,.tex-table th{border:1px solid #334155;padding:6px 10px;text-align:center}.tex-list{margin:8px 0 8px 1.3em;padding:0;line-height:1.75}.immini{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;margin:10px 0}@media(max-width:700px){.immini{grid-template-columns:1fr}}.opt{display:block;border:2px solid #d8e4f0;border-radius:9px;padding:11px;margin:8px 0;cursor:pointer}.opt:hover{background:#f8fbff}.opt:has(input:checked){border-color:var(--blue);background:#f1f7ff;box-shadow:0 0 0 3px #176bd322}.quizacts{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}.hintline{margin-top:8px;font-size:13px;color:#6c7d90;font-weight:700}.tf{display:flex;align-items:center;gap:12px;border:2px solid #d8e4f0;border-radius:9px;padding:12px 14px;margin:8px 0}.tf-text{flex:1;min-width:0;font-size:18px;line-height:1.7}.tf-picks{display:flex;gap:10px;flex-shrink:0;margin-left:auto}.tf-pick{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-width:118px;padding:12px 18px;border:2px solid #c5d6ea;border-radius:12px;font-size:20px;font-weight:900;cursor:pointer;background:#fff;user-select:none}.tf-pick input{width:22px;height:22px;margin:0;accent-color:var(--blue)}.tf-pick.yes{border-color:#7dbe90;color:#0f6a32;background:#f3fbf6}.tf-pick.no{border-color:#e39aa0;color:#a41f28;background:#fff7f7}.tf-pick:hover{filter:brightness(.97)}.tf-pick:has(input:checked){box-shadow:0 0 0 3px #176bd333;border-width:3px}@media(max-width:700px){.tf{flex-wrap:wrap}.tf-picks{width:100%;margin-left:0}.tf-pick{flex:1}}.correct{background:#e8f8ee!important;border-color:#42ae6b!important}.wrong{background:#fff0f1!important;border-color:#e04d56!important}.solution{margin-top:11px;padding:12px;border:1px solid #bad5f2;border-radius:9px;background:#f7fbff}.result{padding:10px;border-radius:9px;margin-top:10px;font-weight:900}.good{background:#eaf8ef;color:#116a32;border:1px solid #8ed1a2}.bad{background:#fff0f1;color:#a41f28;border:1px solid #efa2a8}.praise{margin:10px 0;padding:11px;border-radius:9px;background:#fff8df;border:1px solid #efca73;color:#855a00;font-size:16px;font-weight:900}.review{margin-top:12px;padding:12px;border:1px solid #cab9f0;background:#faf8ff;border-radius:9px}.reviewout{margin-top:10px;white-space:pre-wrap;line-height:1.7}.gkeyrow{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;align-items:center}.gkeygrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:8px 0}.gkeycell label{display:block;font-size:11px;font-weight:800;color:#66778a;margin-bottom:4px}.gkey-input{width:100%;min-width:0;padding:11px 12px;border:1px solid #cbd8e6;border-radius:8px;font-size:15px}.gkeylink{display:inline-flex;align-items:center;gap:6px;font-weight:900;font-size:16px}.gkeylink:hover{text-decoration:underline}@media(max-width:800px){.gkeygrid{grid-template-columns:1fr}}.adminbox{display:grid;grid-template-columns:1fr 1fr;gap:10px}.code{width:100%;height:70vh;font:12px/1.5 Consolas,monospace;padding:10px;border:1px solid #cbd8e6;border-radius:8px}.notice{padding:10px;border:1px solid #b6d3ef;background:#f4f9ff;border-radius:8px}.err{color:#b42318;font-weight:800}.success{color:#0d7b35;font-weight:800}
@media(max-width:900px){.layout{grid-template-columns:1fr}.adminbox{grid-template-columns:1fr}.tree{max-height:38vh}.addbank{grid-template-columns:1fr}}
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
    nav = [
        "<button type='button' class='navback' onclick=\"if(history.length>1)history.back();else location.href='/member'\">← Quay lại</button>",
        "<a href='/member'>📚 MỤC LỤC</a>",
    ]
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
        "<time class='clock' id='ldvlClock' datetime=''>…</time>"
        "<div class='nav'>" + who + "".join(nav)
        + "<button type='button' class='fsbtn' id='ldvlFs' onclick='ldvlToggleFs()' title='Toàn màn hình'>⛶ Toàn màn hình</button>"
        + "</div></div></div>"
    )
    mj = (
        "<script>"
        "window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']],processEscapes:true,packages:{'[+]':['base','ams']}},"
        "options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']},"
        "startup:{typeset:true}};"
        "window.ldvlMountTikz=function(){};"
        "window.ldvlPlayVideo=function(btn,id){var f=document.createElement('iframe');f.className='ytframe';"
        "f.src='https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1&rel=0';"
        "f.allow='accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen';"
        "f.allowFullscreen=true;f.setAttribute('frameborder','0');btn.parentNode.replaceChild(f,btn);};"
        "window.ldvlTypeset=function(el){el=el||document.body;function go(n){"
        "if(window.MathJax&&MathJax.typesetPromise){try{if(MathJax.typesetClear)MathJax.typesetClear([el]);}catch(e){}"
        "return MathJax.typesetPromise([el]).catch(function(){});}"
        "if((n||0)<100)setTimeout(function(){go((n||0)+1);},40);}"
        "go(0);};"
        "window.ldvlTickClock=function(){var el=document.getElementById('ldvlClock');if(!el)return;"
        "var n=new Date(),p=function(x){return String(x).padStart(2,'0')};"
        "var d=['CN','T2','T3','T4','T5','T6','T7'][n.getDay()];"
        "el.textContent=d+' '+p(n.getDate())+'/'+p(n.getMonth()+1)+'/'+n.getFullYear()+' · '+p(n.getHours())+':'+p(n.getMinutes())+':'+p(n.getSeconds());"
        "el.dateTime=n.toISOString()};"
        "window.ldvlToggleFs=function(){var d=document,el=d.documentElement;"
        "if(d.fullscreenElement||d.webkitFullscreenElement){(d.exitFullscreen||d.webkitExitFullscreen).call(d);}"
        "else if(el.requestFullscreen)el.requestFullscreen().catch(function(){});"
        "else if(el.webkitRequestFullscreen)el.webkitRequestFullscreen();};"
        "document.addEventListener('DOMContentLoaded',function(){ldvlTickClock();setInterval(ldvlTickClock,1000)});"
        "document.addEventListener('fullscreenchange',function(){var b=document.getElementById('ldvlFs');if(b)b.textContent=document.fullscreenElement?'⛶ Thu nhỏ':'⛶ Toàn màn hình'});"
        "</script>"
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js' onerror=\"this.onerror=null;this.src='https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.min.js'\"></script>"
    )
    return Response(f"<!doctype html><html lang='vi'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'><meta name='theme-color' content='#176bd3'><meta name='mobile-web-app-capable' content='yes'><title>{html.escape(title)}</title><style>{CSS}</style>{mj}</head><body>{top}{body}{GEMINI_CLIENT_JS}</body></html>", mimetype='text/html')

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
def can_manage_bank():
    """ADMIN đăng nhập /admin, hoặc thành viên quyền ADMIN / username ADMIN."""
    if admin_current(): return True
    m=member_current()
    if account_type_of(m)=='ADMIN': return True
    u=str((m or {}).get('username') or '').strip()
    return bool(u) and u.casefold()==ADMIN_USER.casefold()
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

def github_put_text(path, text, message, sha=None):
    p,_=_safe_repo_file(path)
    payload={'message':message,'content':base64.b64encode(str(text).encode('utf-8')).decode(),'branch':BRANCH}
    if sha: payload['sha']=sha
    return gh_api(f'contents/{urllib.parse.quote(p,safe="/")}','PUT',payload)

def github_delete_path(path, message):
    p,_=_safe_repo_file(path)
    sha=github_file_sha(p)
    return gh_api(f'contents/{urllib.parse.quote(p,safe="/")}','DELETE',{'message':message,'sha':sha,'branch':BRANCH})

def _bank_seg(s):
    s=re.sub(r'[\\/:*?"<>|]+',' ',str(s or '')).strip()
    s=re.sub(r'\s+',' ',s)
    if not s or '..' in s: raise ValueError('Tên môn/chương/bài không hợp lệ.')
    return s[:140]

def bank_new_tex_path(mon,lop,chuong,bai):
    mon=_bank_seg(mon); chuong=_bank_seg(chuong); bai=_bank_seg(bai)
    lop=str(lop or '').strip()
    if lop not in ('10','11','12'): raise ValueError('Lớp phải là 10, 11 hoặc 12.')
    return f'ngan-hang/{mon}/Lớp {lop}/{chuong}/{bai}/de.tex'

def index_upsert_lesson(path, mon, lop, chuong, bai):
    d=index_data(); lessons=d.setdefault('lessons',[])
    rec={'id':path,'file':path,'path':path,'Mon':mon,'Lop':str(lop),'Chuong':chuong,'BaiHoc':bai,'De':bai,'questions':0,'count':0,'dang':{}}
    for x in lessons:
        if str(x.get('path') or x.get('file') or '')==path:
            x.update(rec); break
    else:
        lessons.append(rec)
    d['total_files']=len(lessons)
    save_json_github(INDEX_FILE,d,'bank_index.json','ADMIN cập nhật mục lục ngan-hang')

def index_remove_lesson(path):
    d=index_data()
    d['lessons']=[x for x in d.get('lessons',[]) if str(x.get('path') or x.get('file') or '')!=path]
    d['total_files']=len(d['lessons'])
    save_json_github(INDEX_FILE,d,'bank_index.json','ADMIN xóa bài khỏi mục lục')

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

def extract_nguon(s):
    """Tất cả \\nguon{...} trong khối (giữ thứ tự, bỏ trùng)."""
    found=[]; i=0; s=s or ''
    while True:
        m=re.search(r'\\nguon\s*\{', s[i:], re.I)
        if not m: break
        abs0=i+m.start()
        val,end=get_braced(s, i+m.end()-1)
        if val:
            t=re.sub(r'\s+',' ', val).strip()
            if t and t not in found:
                found.append(t)
        i=(end if end and end>abs0 else abs0+1)
        if i<=abs0: i=abs0+1
    return found

def strip_nguon(s):
    s=s or ''
    while True:
        m=re.search(r'\\nguon\s*\{', s, re.I)
        if not m: break
        _,end=get_braced(s, m.end()-1)
        s=s[:m.start()]+s[end:]
    return re.sub(r'\$\s*\$','',s)

def nguon_html(q):
    n=str((q or {}).get('nguon') or '').strip()
    if not n: return ''
    return f'<span class="nguon">Nguồn: {html.escape(n)}</span>'

def dang_link_html(path, dang, total, kinds=None):
    """Một dòng dạng bài trên mục lục: tên + 4 loại TN/ĐS/TLN/TL + tổng."""
    href=urllib.parse.quote(str(path or ''), safe='')
    name=str(dang or 'Chưa phân dạng')
    s=kinds if isinstance(kinds, dict) else {}
    tn=int(s.get('TN') or 0); ds=int(s.get('DS') or 0); tln=int(s.get('TLN') or 0); tl=int(s.get('TL') or 0)
    tot=int(total or 0) or (tn+ds+tln+tl)
    return (
        f"<a class='dangrow danglink' href='/member/dang?path={href}&dang={urllib.parse.quote(name)}'>"
        f"<span class='dangname'>{html.escape(name)}</span>"
        f"<span class='dangkinds'><span class='kind'>TN {tn}</span><span class='kind'>ĐS {ds}</span>"
        f"<span class='kind'>TLN {tln}</span><span class='kind'>TL {tl}</span>"
        f"<span class='kind ktotal'>{tot} câu</span></span></a>"
    )

def strip_bank_meta(s):
    """Gỡ ID/HienID/begin{ex}, giữ TikZ và tabular để latex_to_web vẽ."""
    s=strip_nguon(s or '')
    s=re.sub(r'\\begin\s*\{\s*(ex|bt)\s*\}','',s,flags=re.I)
    s=re.sub(r'\\end\s*\{\s*(ex|bt)\s*\}','',s,flags=re.I)
    s=re.sub(r'%\s*ID\s*:[^\n]*','',s,flags=re.I)
    s=re.sub(r'%\s*Mức\s*:[^\n]*','',s,flags=re.I)
    s=re.sub(r'%HienID','',s,flags=re.I)
    s=re.sub(r'%\s*\[[^\]]+\]','',s)
    s=re.sub(r'\{[^\}]*\\ttfamily\s*\[[^\]]+\]\}','',s)
    s=re.sub(r'\\color\s*\{\s*red\s*\}','',s,flags=re.I)
    s=re.sub(r'\\(?:footnotesize|ttfamily|par)\b',' ',s,flags=re.I)
    s=re.sub(r'\{\s*\[[A-Za-z0-9._-]+\]\s*\}','',s)
    s=re.sub(r'\[(?=[A-Za-z]{1,4}\d)[A-Za-z0-9._-]{3,}\]','',s)
    s=re.sub(r'\\lq\s*\\lq','«',s,flags=re.I);s=re.sub(r'\\rq\s*\\rq','»',s,flags=re.I)
    s=re.sub(r'\\lq\b','«',s,flags=re.I);s=re.sub(r'\\rq\b','»',s,flags=re.I);s=re.sub(r'\\,',' ',s)
    return s.strip()

def clean_latex_web(s):
    return strip_bank_meta(s or '')

def html_question(s):
    return latex_to_web(s or '')

def prepare_math(s):
    """Make LaTeX visible to MathJax: keep $...$ and wrap bare \\overrightarrow{ }."""
    s = strip_bank_meta(s or '')
    s = re.sub(r'(?<![\\$])overrightarrow\s*\{([^{}]*)\}', r'\\overrightarrow{\1}', s)
    s = re.sub(r'(?<!\$)\\overrightarrow\s*\{([^{}]*)\}', r'$\\overrightarrow{\1}$', s)
    s = re.sub(r'(?<!\$)\\vec\s*\{([^{}]*)\}', r'$\\vec{\1}$', s)
    s = re.sub(r'\$\$+', '$$', s)
    return s.strip()

TIKZ_RE=re.compile(r'\\begin\s*\{\s*tikzpicture\s*\}.*?\\end\s*\{\s*tikzpicture\s*\}',re.I|re.S)
TIKZ_CACHE=ROOT/'data'/'tikz-cache'

def tikz_hash(src):
    return hashlib.sha1((src or '').encode('utf-8')).hexdigest()

def tikz_standalone_document(tikz_code):
    """Giống app cũ: standalone + pgfplots khi có axis — TeX Live hoặc latex.ytotech.com."""
    code=(tikz_code or '').strip()
    uses_axis=bool(re.search(r'\\begin\s*\{\s*axis\s*\}', code, re.I)) or '\\addplot' in code
    lines=[
        r'\documentclass[tikz,border=3pt]{standalone}',
        r'\usepackage[utf8]{inputenc}',
        r'\usepackage[T5]{fontenc}',
        r'\usepackage[vietnamese]{babel}',
        r'\usepackage{amsmath,amssymb,amsfonts}',
        r'\usepackage{tikz,xcolor}',
        r'\usetikzlibrary{arrows,arrows.meta,calc,positioning,patterns,intersections,decorations.pathmorphing,decorations.markings,backgrounds,fit,shapes,shapes.geometric,angles,quotes,shadings,shadows}',
    ]
    if uses_axis:
        lines += [r'\usepackage{pgfplots}', r'\pgfplotsset{compat=1.18}']
    lines += [r'\begin{document}', code, r'\end{document}', '']
    return '\n'.join(lines)

_PDFLATEX_BIN=False

def pdflatex_bin():
    global _PDFLATEX_BIN
    if _PDFLATEX_BIN is not False:
        return _PDFLATEX_BIN or None
    found=shutil.which('pdflatex') or ''
    if not found:
        home=Path.home()
        cands=[]
        for y in range(2026,2018,-1):
            cands.append(Path(rf'C:\texlive\{y}\bin\windows\pdflatex.exe'))
            cands.append(Path(f'/usr/local/texlive/{y}/bin/x86_64-linux/pdflatex'))
        cands += [
            Path('/usr/bin/pdflatex'),
            Path(r'C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe'),
            home/'AppData'/'Local'/'Programs'/'MiKTeX'/'miktex'/'bin'/'x64'/'pdflatex.exe',
        ]
        for c in cands:
            if c.is_file():
                found=str(c); break
    _PDFLATEX_BIN=found or ''
    return _PDFLATEX_BIN or None

def _run_tex(cmd, cwd):
    kw=dict(cwd=str(cwd), capture_output=True, timeout=45)
    if os.name=='nt':
        kw['creationflags']=getattr(subprocess,'CREATE_NO_WINDOW',0)
    return subprocess.run(cmd, **kw)

def compile_tikz_pdf_via_cloud(tex_doc):
    """Biên dịch LaTeX → PDF qua latex.ytotech.com (Render không cần TeX Live)."""
    payload=json.dumps({'compiler':'pdflatex','resources':[{'main':True,'content':tex_doc}]}).encode('utf-8')
    try:
        req=urllib.request.Request(
            'https://latex.ytotech.com/builds/sync',
            data=payload,
            headers={'Content-Type':'application/json','User-Agent':'LDVL-TikZ/1'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=75) as resp:
            data=resp.read()
        if data[:4]==b'%PDF':
            return data,''
        try:
            err=json.loads(data.decode('utf-8','replace'))
            return b'', str(err.get('logs') or err.get('message') or err)[:320]
        except Exception:
            return b'', 'Dịch vụ LaTeX trả lỗi không xác định.'
    except Exception as e:
        return b'', f'Không gọi được dịch vụ biên dịch LaTeX: {str(e)[:200]}'

TIKZ_TARGET_PX=1200

def pdf_bytes_to_png(pdf_bytes):
    """Xuất PNG với cạnh dài quy về ~1200px để mọi hình nét như nhau trong khung cố định."""
    if not pdf_bytes: return None
    try:
        import fitz
        doc=fitz.open(stream=pdf_bytes, filetype='pdf')
        if doc.page_count<1: return None
        page=doc.load_page(0)
        long_side=max(page.rect.width, page.rect.height) or 1
        zoom=max(1.0, min(6.0, TIKZ_TARGET_PX/long_side))
        pix=page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes('png')
    except Exception:
        return None

def compile_tikz_pdf_local(src):
    exe=pdflatex_bin()
    if not exe: return None
    try:
        with tempfile.TemporaryDirectory() as td:
            tdir=Path(td)
            (tdir/'fig.tex').write_text(tikz_standalone_document(src), encoding='utf-8')
            r=_run_tex([exe,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error','fig.tex'], tdir)
            pdf=tdir/'fig.pdf'
            if r.returncode!=0 or not pdf.is_file():
                return None
            return pdf.read_bytes()
    except Exception:
        return None

def pdf_to_png_bytes(pdf):
    blob=pdf_bytes_to_png(pdf)
    if blob: return blob
    cairo=shutil.which('pdftocairo')
    if not cairo: return None
    try:
        with tempfile.TemporaryDirectory() as td:
            tdir=Path(td)
            (tdir/'fig.pdf').write_bytes(pdf)
            _run_tex([cairo,'-png','-f','1','-l','1','-r','160',str(tdir/'fig.pdf'),str(tdir/'fig')], tdir)
            for name in ('fig-1.png','fig.png'):
                alt=tdir/name
                if alt.is_file(): return alt.read_bytes()
    except Exception:
        pass
    return None

def tikz_png_path(hid): return TIKZ_CACHE/f'{hid}.png'
def tikz_src_path(hid): return TIKZ_CACHE/f'{hid}.tex'

def tikz_remember(src):
    """Lưu mã TikZ theo hash để route ảnh vẽ sau — không biên dịch lúc dựng trang."""
    src=(src or '').strip()
    hid=tikz_hash(src)
    try:
        TIKZ_CACHE.mkdir(parents=True, exist_ok=True)
        p=tikz_src_path(hid)
        if not p.is_file():
            p.write_text(src, encoding='utf-8')
    except Exception:
        pass
    return hid

_TIKZ_LOCKS={}
_TIKZ_LOCKS_GUARD=threading.Lock()

def _tikz_lock(hid):
    with _TIKZ_LOCKS_GUARD:
        lock=_TIKZ_LOCKS.get(hid)
        if lock is None:
            lock=_TIKZ_LOCKS[hid]=threading.Lock()
        return lock

def tikz_build_png(hid, src='', allow_cloud=True):
    """Vẽ 1 hình rồi cache. Nhiều request cùng hình chỉ biên dịch một lần."""
    png=tikz_png_path(hid)
    if png.is_file() and png.stat().st_size>80:
        return png, ''
    src=(src or '').strip()
    if not src:
        p=tikz_src_path(hid)
        if p.is_file():
            src=p.read_text(encoding='utf-8', errors='replace').strip()
    if not src or 'tikzpicture' not in src.lower():
        return None, 'Không tìm thấy mã TikZ của hình này.'
    with _tikz_lock(hid):
        if png.is_file() and png.stat().st_size>80:
            return png, ''
        pdf=compile_tikz_pdf_local(src)
        err=''
        if not pdf and allow_cloud:
            pdf, err=compile_tikz_pdf_via_cloud(tikz_standalone_document(src))
        if not pdf:
            return None, err or 'Chưa biên dịch được TikZ.'
        blob=pdf_to_png_bytes(pdf)
        if not blob:
            return None, 'Đã có PDF nhưng chưa chuyển được sang PNG (thiếu PyMuPDF).'
        try:
            TIKZ_CACHE.mkdir(parents=True, exist_ok=True)
            png.write_bytes(blob)
        except Exception as e:
            return None, f'Không ghi được ảnh: {str(e)[:120]}'
    return png, ''

def tikz_error_svg(msg):
    txt=html.escape(str(msg or 'Chưa vẽ được hình')[:110])
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' width='420' height='70'>"
        "<rect width='420' height='70' rx='8' fill='#fff7ed' stroke='#fdba74'/>"
        f"<text x='210' y='32' font-family='Segoe UI,Arial' font-size='13' fill='#9a3412' text-anchor='middle'>Chưa vẽ được hình TikZ</text>"
        f"<text x='210' y='52' font-family='Segoe UI,Arial' font-size='11' fill='#c2410c' text-anchor='middle'>{txt}</text>"
        "</svg>"
    )

def strip_resizebox(s):
    s=s or ''
    while True:
        m=re.search(r'\\resizebox\s*\{', s, re.I)
        if not m: return s
        _,p1=get_braced(s, m.end()-1)
        _,p2=get_braced(s, p1)
        body,p3=get_braced(s, p2)
        if body is None: return s[:m.start()]+s[m.end():]
        s=s[:m.start()]+body+s[p3:]

def skip_braced(s, pos, n=1):
    p=pos
    for _ in range(n):
        q=p
        while q<len(s) and s[q].isspace(): q+=1
        if q<len(s) and s[q]=='{':
            _,p=get_braced(s,q)
        else:
            break
    return p

def strip_wrapfigure(s):
    s=s or ''
    while True:
        m=re.search(r'\\begin\s*\{\s*wrapfigure\s*\}', s, re.I)
        if not m: return s
        p=skip_braced(s, m.end(), 2)
        em=re.search(r'\\end\s*\{\s*wrapfigure\s*\}', s[p:], re.I)
        if not em:
            s=s[:m.start()]+s[p:]
            continue
        s=s[:m.start()]+s[p:p+em.start()]+s[p+em.end():]

def peel_immini(s):
    """Đưa hình \\immini ra cạnh đề, không để TikZ rơi sau \\choice."""
    s=s or ''
    while True:
        m=re.search(r'\\immini\s*(?:\[[^\]]*\])?\s*', s, re.I)
        if not m: return s
        a,p1=get_braced(s, m.end())
        if a is None: return s
        fig,p2=get_braced(s, p1)
        if fig is None:
            fig,p2='',p1
        parts=re.split(r'(\\(?:choiceTF|choice|shortans)\b)', a, 1, flags=re.I)
        if len(parts)>=3:
            rebuilt=parts[0]+'\n'+fig+'\n'+parts[1]+parts[2]
        else:
            rebuilt=a+'\n'+fig
        s=s[:m.start()]+rebuilt+s[p2:]

def tabular_to_html(body):
    body=re.sub(r'\\hline','', body or '')
    rows=re.split(r'\\\\', body)
    parts=['<table class="tex-table">']
    for row in rows:
        row=row.strip()
        if not row: continue
        cells=[c.strip() for c in re.split(r'(?<!\\)&', row)]
        parts.append('<tr>')
        for c in cells:
            c=re.sub(r'\\textbf\s*\{([^{}]*)\}', r'@@B@@\1@@/B@@', c)
            inner=html.escape(prepare_math(c), quote=False)
            inner=inner.replace('@@B@@','<b>').replace('@@/B@@','</b>')
            inner=inner.replace(html.escape('@@B@@', quote=False),'<b>').replace(html.escape('@@/B@@', quote=False),'</b>')
            parts.append(f'<td>{inner}</td>')
        parts.append('</tr>')
    parts.append('</table>')
    return ''.join(parts)

def convert_tabulars(s, tab_stash):
    s=s or ''
    while True:
        m=re.search(r'\\begin\s*\{\s*tabular\s*\}', s, re.I)
        if not m: return s
        p=skip_braced(s, m.end(), 1)
        em=re.search(r'\\end\s*\{\s*tabular\s*\}', s[p:], re.I)
        if not em:
            s=s[:m.start()]+s[p:]
            continue
        body=s[p:p+em.start()]
        rest=s[p+em.end():]
        if re.search(r'@@FIG\d+@@', body):
            figs=re.findall(r'@@FIG\d+@@', body)
            repl=' '.join(figs) if figs else re.sub(r'(?<!\\)&',' ',body)
            s=s[:m.start()]+repl+rest
        else:
            tok=f'@@TAB{len(tab_stash)}@@'
            tab_stash.append(tabular_to_html(body))
            s=s[:m.start()]+tok+rest

def convert_list_env(s, name, tag, stash):
    s=s or ''
    while True:
        m=re.search(r'\\begin\s*\{\s*'+name+r'\s*\}', s, re.I)
        if not m: return s
        em=re.search(r'\\end\s*\{\s*'+name+r'\s*\}', s[m.end():], re.I)
        if not em:
            s=s[:m.start()]+s[m.end():]
            continue
        body=s[m.end():m.end()+em.start()]
        items=re.split(r'\\item\b', body)[1:]
        lis=[]
        for it in items:
            it=it.strip()
            if not it: continue
            it=re.sub(r'\\textbf\s*\{([^{}]*)\}', r'@@B@@\1@@/B@@', it)
            inner=html.escape(prepare_math(it), quote=False).replace('\n','<br>\n')
            inner=inner.replace('@@B@@','<b>').replace('@@/B@@','</b>')
            inner=inner.replace(html.escape('@@B@@', quote=False),'<b>').replace(html.escape('@@/B@@', quote=False),'</b>')
            lis.append(f'<li>{inner}</li>')
        tok=f'@@LST{len(stash)}@@'
        stash.append(f'<{tag} class="tex-list">{"".join(lis)}</{tag}>')
        s=s[:m.start()]+tok+s[m.end()+em.end():]

def id_of(block):
    ids=ID_RE.findall(block or '')
    if ids: return ids[-1].strip()
    m=re.search(r'\\begin\s*\{\s*(?:ex|bt)\s*\}\s*%+\s*\[([^\]]+)\]', block or '', re.I)
    if m:
        t=m.group(1).strip()
        if t: return t
    m=re.search(r'%\s*\[([A-Za-z0-9][A-Za-z0-9._-]{3,})\]', block or '')
    if m: return m.group(1).strip()
    codes=[]
    for x in re.findall(r'\[([^\]]+)\]', block or ''):
        t=x.strip()
        if re.match(r'^[A-Za-z0-9][A-Za-z0-9._-]{3,}$', t) and re.search(r'\d', t):
            codes.append(t)
    return codes[-1] if codes else ''

def tikz_to_html(block):
    """Chỉ ghi mã TikZ + trả thẻ <img>. Ảnh được vẽ ở route /tikz/<hash>.png nên trang mở ngay."""
    hid=tikz_remember(block)
    return (
        f'<div class="tikzfig"><img class="tikz-img" loading="lazy" decoding="async" '
        f'alt="Hình TikZ" src="/tikz/{hid}.png"></div>'
    )

YT_URL_RE=re.compile(r'https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?(?:[^\s"\'<>]*&(?:amp;)?)?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})[^\s<>"\'}\]]*',re.I)
VIDEO_CMD_RE=re.compile(r'\\(?:video|youtube|clip|link|url)\s*(?:\[(?P<title>[^\]]*)\])?\s*\{(?P<url>[^{}]*)\}',re.I)
LINK_RE=re.compile(r'https?://[^\s<>"\']*[^\s<>"\'.,;:)\]]')

def youtube_id(raw):
    t=str(raw or '').strip()
    m=YT_URL_RE.search(t)
    if m: return m.group(1)
    return t if re.fullmatch(r'[A-Za-z0-9_-]{11}',t) else ''

def video_html(vid, title=''):
    """Ảnh nền + nút play; chỉ nạp trình phát YouTube khi học sinh bấm."""
    label=html.escape((title or '').strip() or 'Xem video bài giảng', quote=True)
    return (f'<div class="ytbox"><button type="button" class="ytplay" onclick="ldvlPlayVideo(this,\'{vid}\')"'
            f' style="background-image:url(https://i.ytimg.com/vi/{vid}/hqdefault.jpg)" title="{label}">'
            f'<span class="ytplay-ico">▶</span><span class="ytplay-txt">{label}</span></button>'
            f'<a class="ytlink" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">↗ Mở trên YouTube</a></div>')

def latex_to_web(s):
    """HTML cho web: TikZ → hình, tabular → bảng, list → HTML, còn lại $...$ cho MathJax."""
    figs=[]; bolds=[]; tabs=[]; lists=[]; vids=[]
    def stash_tikz(m):
        figs.append(tikz_to_html(m.group(0)))
        return f'@@FIG{len(figs)-1}@@'
    def stash_video(m):
        g=m.groupdict()
        url=(g.get('url') or m.group(0)).strip()
        title=(g.get('title') or '').strip()
        vid=youtube_id(url)
        if vid:
            vids.append(video_html(vid, title))
        elif re.match(r'https?://', url, re.I):
            vids.append(f'<a class="exlink" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">🔗 {html.escape(title or url, quote=False)}</a>')
        else:
            return url
        return f'@@VID{len(vids)-1}@@'
    s=peel_immini(s or '')
    s=strip_wrapfigure(s)
    s=strip_resizebox(s)
    s=VIDEO_CMD_RE.sub(stash_video, s)
    s=YT_URL_RE.sub(stash_video, s)
    s=TIKZ_RE.sub(stash_tikz, s)
    s=convert_tabulars(s, tabs)
    s=convert_list_env(s, 'itemchoice', 'ul', lists)
    s=convert_list_env(s, 'itemize', 'ul', lists)
    s=convert_list_env(s, 'enumerate', 'ol', lists)
    s=re.sub(r'\\includegraphics(?:\s*\[[^\]]*\])?\s*\{[^}]*\}','@@IMG@@',s,flags=re.I)
    s=re.sub(r'\\begin\s*\{\s*(?:center|minipage|figure)\s*\}(?:\{[^{}]*\})?','',s,flags=re.I)
    s=re.sub(r'\\end\s*\{\s*(?:center|minipage|figure)\s*\}','',s,flags=re.I)
    s=re.sub(r'\\vspace\s*\{[^{}]*\}','',s,flags=re.I)
    s=re.sub(r'\\centering\b','',s,flags=re.I)
    s=re.sub(r'(@@FIG\d+@@)\s*&\s*', r'\1 ', s)
    s=re.sub(r'(?<!\\)&',' ',s)
    s=re.sub(r'((?:@@FIG\d+@@\s*){2,})', lambda m: '@@ROW@@'+m.group(1)+'@@/ROW@@', s)
    def stash_bf(m):
        bolds.append(m.group(1))
        return f'@@BF{len(bolds)-1}@@'
    s=re.sub(r'\\textbf\s*\{([^{}]*)\}', stash_bf, s)
    s=re.sub(r'\\item\b','\n• ',s)
    s=html.escape(prepare_math(s), quote=False).replace('\n','<br>\n')
    s=LINK_RE.sub(lambda m: f'<a href="{m.group(0)}" target="_blank" rel="noopener">{m.group(0)}</a>', s)
    def put(tok, html_val):
        nonlocal s
        s=s.replace(html.escape(tok, quote=False), html_val).replace(tok, html_val)
    for i,t in enumerate(bolds):
        put(f'@@BF{i}@@', f'<b>{html.escape(t, quote=False)}</b>')
    for i,fig in enumerate(figs):
        put(f'@@FIG{i}@@', fig)
    for i,tb in enumerate(tabs):
        put(f'@@TAB{i}@@', tb)
    for i,ls in enumerate(lists):
        put(f'@@LST{i}@@', ls)
    for i,vd in enumerate(vids):
        put(f'@@VID{i}@@', vd)
    put('@@IMG@@', '<span class="muted">[Hình]</span>')
    s=s.replace('@@ROW@@',"<div class='tikz-row'>").replace('@@/ROW@@','</div>')
    s=s.replace(html.escape('@@ROW@@', quote=False),"<div class='tikz-row'>").replace(html.escape('@@/ROW@@', quote=False),'</div>')
    s=re.sub(r'\\begin\s*\{\s*(?:tabular|center|tikzpicture|figure|minipage|itemchoice|itemize|enumerate|wrapfigure)\s*\}(?:\{[^{}]*\})?','',s,flags=re.I)
    s=re.sub(r'\\end\s*\{\s*(?:tabular|center|tikzpicture|figure|minipage|itemchoice|itemize|enumerate|wrapfigure)\s*\}','',s,flags=re.I)
    s=re.sub(r'\\(?:immini|resizebox)(?:\s*\[[^\]]*\])?(?:\s*\{[^{}]*\}){0,3}\s*\{?','',s,flags=re.I)
    s=re.sub(r'%\s*\[[^\]]+\]','',s)
    return s

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
        b=peel_immini(m.group(0))
        if re.search(r'\\choiceTF\b',b,re.I):kind='DS'
        elif re.search(r'\\choice\b',b,re.I):kind='TN'
        elif SHORT_RE.search(b):kind='TLN'
        else:kind='TL'
        heads=list(CAU_HEAD_RE.finditer(tex[:m.start()]))
        qid=id_of(b) or id_of(tex[max(0,m.start()-120):m.end()])
        pre=tex[max(0,m.start()-800):m.start()]
        cut=max(pre.rfind('\\end{ex}'), pre.rfind('\\end{bt}'))
        if cut>=0: pre=pre[cut:]
        nguon=' · '.join(dict.fromkeys(extract_nguon(pre)+extract_nguon(b)))
        q={'idx':idx,'stt':idx+1,'id':qid,'cau':int(heads[-1].group(1)) if heads else idx+1,'line':tex[:m.start()].count('\n')+1,'dang':dang_for_pos(tex,m.start()),'level':level_of(b),'kind':kind,'nguon':nguon,'text':clean_latex_web(re.split(r'\\choiceTF\b|\\choice\b|\\shortans\b',b,1,flags=re.I)[0]),'solution':clean_latex_web(solution_of(b)),'raw':b}
        if kind=='TN':q['options']=[{'text':clean_latex_web(re.sub(r'^\\True\s*','',x,flags=re.I)),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in command_args(b,'\\choice')[:4]]
        elif kind=='DS':q['statements']=[{'text':clean_latex_web(re.sub(r'^\\True\s*','',x,flags=re.I)),'correct':bool(re.match(r'^\\True\b',x,re.I))} for x in command_args(b,'\\choiceTF')]
        elif kind=='TLN':
            sm=re.search(r'\\shortans\s*(?:\[[^\]]*\])?\s*',b,re.I);ans=''
            if sm:ans,_=get_braced(b,sm.end())
            q['answer']=(ans or '').strip()
        out.append(q)
    return out

def _dup_norm(s):
    s=clean_latex_web(s or '')
    s=re.sub(r'\\(?:begin|end)\s*\{[^}]*\}',' ',s,flags=re.I)
    s=re.sub(r'\\[a-zA-Z]+\*?',' ',s)
    s=re.sub(r'[{}\[\]$&~^_\\]',' ',s)
    s=s.casefold()
    s=re.sub(r'\s+',' ',s).strip()
    return s

def question_dup_keys(q):
    stem=_dup_norm(q.get('text') or '')
    kind=str(q.get('kind') or 'TL')
    if kind=='TN':
        opts=tuple(sorted(_dup_norm(o.get('text') if isinstance(o,dict) else o) for o in (q.get('options') or []) if _dup_norm(o.get('text') if isinstance(o,dict) else o)))
        return stem, (kind, stem, opts)
    if kind=='DS':
        stmts=tuple(sorted(_dup_norm(o.get('text') if isinstance(o,dict) else o) for o in (q.get('statements') or []) if _dup_norm(o.get('text') if isinstance(o,dict) else o)))
        return stem, (kind, stem, stmts)
    if kind=='TLN':
        return stem, (kind, stem, _dup_norm(q.get('answer') or ''))
    return stem, (kind, stem, _dup_norm(q.get('solution') or '')[:240])

def find_duplicate_groups(questions):
    from collections import defaultdict
    by_body, by_stem = defaultdict(list), defaultdict(list)
    for q in questions or []:
        stem, body = question_dup_keys(q)
        q['_dup_stem']=stem; q['_dup_body']=body
        if stem and len(stem)>=8: by_stem[stem].append(q)
        if body and stem and len(stem)>=8: by_body[body].append(q)
    groups=[]; covered=set()
    for arr in by_body.values():
        if len(arr)<2: continue
        arr=sorted(arr, key=lambda x: int(x.get('idx') or 0))
        groups.append({'type':'dao','title':'Trùng câu hỏi + đáp án (kể cả đảo A–D / đảo thứ tự mệnh đề Đúng-Sai)','keep':arr[0]['idx'],'extras':[x['idx'] for x in arr[1:]],'members':arr})
        covered.update(x['idx'] for x in arr)
    for arr in by_stem.values():
        if len(arr)<2: continue
        bodies={x.get('_dup_body') for x in arr}
        if len(bodies)<2: continue
        arr=sorted(arr, key=lambda x: int(x.get('idx') or 0))
        groups.append({'type':'cungde','title':'Cùng câu hỏi nhưng đáp án / mệnh đề khác nhau — cần xem lại','keep':arr[0]['idx'],'extras':[x['idx'] for x in arr[1:]],'members':arr})
    return groups

def tex_without_questions(tex, drop_idxs):
    drop={int(x) for x in (drop_idxs or [])}
    chunks=[]; last=0
    for i,m in enumerate(EX_RE.finditer(tex)):
        if i not in drop:
            chunks.append(tex[last:m.end()]); last=m.end(); continue
        pre=tex[last:m.start()]
        pre=re.sub(r'(?:\r?\n)*%\s*=+\s*Câu\s+\d+[^\n]*(?:\r?\n%[^\n]*)*$','',pre,flags=re.I)
        chunks.append(pre); last=m.end()
    chunks.append(tex[last:])
    return re.sub(r'\n{3,}','\n\n',''.join(chunks)).strip()+'\n'

def dup_index_by_question(groups):
    info={}
    for gi,g in enumerate(groups,1):
        for q in g['members']:
            i=q['idx']
            cur=info.setdefault(i, {'n':[], 'label':'', 'extra':False})
            cur['n'].append(gi)
            if g['type']=='dao':
                cur['label']='TRÙNG (đảo đáp án)'
                if i in g.get('extras',[]): cur['extra']=True
            elif not cur['label']:
                cur['label']='CÙNG ĐỀ'
    return info

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
def health():return jsonify(ok=True,app='github-bank-clean',repo=REPO,branch=BRANCH,tikz=bool(pdflatex_bin()))
@app.get('/tikz/<hid>.svg')
def tikz_cached(hid):
    if not re.fullmatch(r'[a-f0-9]{40}', hid or ''):
        return ('', 404)
    p=TIKZ_CACHE/f'{hid}.svg'
    if not p.is_file():
        return ('', 404)
    return Response(p.read_text(encoding='utf-8', errors='replace'), mimetype='image/svg+xml')
@app.get('/')
def home():return redirect('/member')
@app.get('/github/repo')
def repo_redirect():
    if not admin_current():
        return redirect('/member')
    return redirect(f'https://github.com/{REPO}')
@app.get('/github/ngan-hang')
def ngan_hang_redirect():
    if not admin_current():
        return redirect('/member')
    return redirect(github_folder_url('ngan-hang'))

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
            path=str(x.get('path'));title=str(x.get('BaiHoc') or x.get('De') or Path(path).parent.name);lvl=lesson_level(path);cnt=int(x.get('questions') or x.get('count') or 0);dangs=x.get('dang') or {};kinds=x.get('dang_kinds') or {};href=urllib.parse.quote(path,safe='');dh=''.join(dang_link_html(path,k,v,kinds.get(str(k))) for k,v in dangs.items());lc='vip' if lvl=='VIP' else 'free'
            cards.append("<div class='card'><b>"+html.escape(title)+"</b><div class='meta'>"+html.escape(mon)+" · Lớp "+html.escape(lop)+" · "+html.escape(chuong)+"</div><div><span class='tag "+lc+"'>"+html.escape(lvl)+"</span><span class='tag'>"+str(cnt)+" câu</span></div><div class='dang'><b>📌 Dạng bài</b>"+(dh or "<div class='muted'>Xem trực tiếp từ TEX khi mở bài</div>")+"</div><a class='btn primary' href='/member/select?path="+href+"'>Mở bài</a></div>")
        sections.append("<section style='margin-top:10px'><div class='titlebar'>"+html.escape(mon)+" · Lớp "+html.escape(lop)+" · "+html.escape(chuong)+"</div><div class='cards' style='margin-top:8px'>"+''.join(cards)+"</div></section>")
    subjopts=''.join("<option value='"+html.escape(s,quote=True)+"'"+(" selected" if sm==s else "")+">"+html.escape(s)+"</option>" for s in subjects);classopts=''.join("<option value='"+html.escape(c,quote=True)+"'"+(" selected" if cl==c else "")+">"+html.escape(c)+"</option>" for c in classes)
    body=("<div class='wrap'><div class='panel'><div class='head'>📚 MỤC LỤC <span class='tag'>"+str(idx.get('total_files',0))+" file</span><span class='tag'>"+str(idx.get('total_questions',0))+" câu</span></div><div class='body'><div class='notice'>👤 <b>"+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản <b>"+html.escape(str(m.get('username')))+"</b> · Quyền <b>"+html.escape(str(m.get('account_type','FREE')))+"</b></div>"+gemini_panel_html()+"<form method='get' style='display:grid;grid-template-columns:1fr 180px 160px auto;gap:7px;margin-top:10px'><input name='q' placeholder='Tìm bài, chương, dạng...' value='"+html.escape(q)+"'><select name='mon'><option value=''>Tất cả môn</option>"+subjopts+"</select><select name='lop'><option value=''>Tất cả lớp</option>"+classopts+"</select><button class='btn'>Tìm</button></form></div></div>"+(''.join(sections) or "<div class='panel' style='margin-top:10px'><div class='body muted'>Không có bài phù hợp.</div></div>")+"</div>")
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

def question_payload(q):
    """Toàn bộ dữ liệu một câu cho trang làm bài và cho AI phản biện."""
    p={'kind':q['kind'],'id':q.get('id') or '','cau':q.get('cau') or '','nguon':q.get('nguon') or '','text':html_question(q['text']),'solution':html_question(q['solution']),'dang':q['dang'],'level':q['level']}
    if q['kind']=='TN':p['options']=[{'text':html_question(o.get('text','')),'correct':bool(o.get('correct'))} for o in (q.get('options') or [])]
    elif q['kind']=='DS':p['statements']=[{'text':html_question(o.get('text','') if isinstance(o,dict) else o),'correct':bool((o or {}).get('correct') if isinstance(o,dict) else False)} for o in (q.get('statements') or [])]
    elif q['kind']=='TLN':p['answer']=q.get('answer','')
    return p

def review_payload(q,entry):
    """Ghép câu gốc trong ngân hàng với bài làm đã lưu để AI có đủ dữ kiện."""
    entry=entry or {}
    p=question_payload(q) if q else {'kind':str(entry.get('kind') or ''),'dang':str(entry.get('dang') or ''),'text':str(entry.get('text') or ''),'solution':str(entry.get('solution') or '')}
    p.update(question=entry.get('question'),student=str(entry.get('student') or ''),ok=bool(entry.get('ok')))
    return p

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
        opts=''.join(f"<option value='{i}'>Câu {d.get('question') or i+1} · {'Đúng' if d.get('ok') else 'Sai'}</option>" for i,d in enumerate(done))
        review=[review_payload(allq.get(ids[int(d.get('question') or 0)-1]) if 0<int(d.get('question') or 0)<=len(ids) else None,d) for d in done]
        body=(
            f"<div class='wrap'><div class='panel'><div class='head'>🎉 Kết quả <span class='tag'>Đúng {right}/{len(ids)}</span> <span class='tag'>{score:.2f}/10</span></div>"
            f"<div class='body'><div class='result good'>Chuỗi tốt nhất: {best}</div>"
            + gemini_panel_html()
            + f"<div class='review'><b>🤖 Gemini phản biện 1 câu</b><div class='gkeyrow'><select id='pick'>{opts}</select> <button type='button' class='btn primary' onclick='rv()'>🤖 Phản biện</button></div><div id='out' class='reviewout'></div></div>"
            f"<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>"
            f"<script>const D={json.dumps(review,ensure_ascii=False)};function rv(){{ldvlGeminiReview(D[+document.getElementById('pick').value],document.getElementById('out'))}}</script>"
        )
        return page('Kết quả',body)
    q=allq.get(ids[pos]);
    if not q:return redirect('/member')
    palette=''.join(f"<a class='pitem {'pcur' if j==pos else ('pdone' if j<len(done) and done[j].get('ok') else ('pwrong' if j<len(done) else ''))}' href='/practice/jump/{j}' title='{html.escape(str(allq.get(qid,{}).get('id') or ''), quote=True)}'>{j+1} · {allq.get(qid,{}).get('kind','?')}</a>" for j,qid in enumerate(ids))
    payload=question_payload(q)
    body=f"<div class='wrap'><div class='panel'><div class='head quiztop'><span>📝 Câu {pos+1}/{len(ids)} · <span class='qid'>ID {html.escape(str(q.get('id') or '—'))}</span> · {html.escape(q['dang'])} · {q['kind']}</span><span>Đúng {right} · Chuỗi {streak}</span></div><div class='body'><div class='palette'>{palette}</div><div id='praise'></div><div id='q' class='qbox'></div><div id='aibox'></div></div></div></div>"
    js=r'''<script>
const Q=__DATA__;let checked=false;
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function typeset(el){if(window.ldvlTypeset)return window.ldvlTypeset(el||document.getElementById('q'));el=el||document.getElementById('q');if(window.MathJax&&MathJax.typesetPromise){try{if(MathJax.typesetClear)MathJax.typesetClear([el]);}catch(e){}MathJax.typesetPromise([el]).catch(function(){});}}
function lockInputs(){document.querySelectorAll('#q input,#q textarea').forEach(function(el){el.disabled=true});let b=document.getElementById('chkbtn');if(b)b.style.display='none';let hint=document.getElementById('hint');if(hint)hint.remove()}
function draw(){let q=Q,h=(q.nguon?'<div class="nguonrow"><span class="nguon">Nguồn: '+E(q.nguon)+'</span></div>':'')+'<div class="qtext"><b>Câu __POS__. </b>'+(q.id?'<span class="qid">ID '+E(q.id)+'</span> ':'')+q.text+'</div>';
if(q.kind==='TN')q.options.forEach((o,i)=>h+='<label class="opt" id="o'+i+'"><input type="radio" name="a" value="'+i+'"> <b>'+String.fromCharCode(65+i)+'.</b> '+o.text+'</label>');
else if(q.kind==='DS')q.statements.forEach((s,i)=>h+='<div class="tf" id="t'+i+'"><div class="tf-text"><b>'+(i+1)+'.</b> '+s.text+'</div><div class="tf-picks"><label class="tf-pick yes"><input type="radio" name="t'+i+'" value="1"> Đúng</label><label class="tf-pick no"><input type="radio" name="t'+i+'" value="0"> Sai</label></div></div>');
else if(q.kind==='TLN')h+='<input id="ans" class="answerbox" style="width:100%;padding:10px;border:1px solid #cbd8e6;border-radius:7px" placeholder="Nhập đáp án rồi bấm Xác nhận (hoặc Enter)">';
else h+='<textarea id="ans" class="answerbox" style="width:100%;height:190px;padding:10px;border:1px solid #cbd8e6;border-radius:7px" placeholder="Nhập bài làm"></textarea>';
h+='<div class="quizacts"><button class="btn primary" id="chkbtn" onclick="check()" disabled>✅ Xác nhận</button><button id="solbtn" class="btn" style="display:none" onclick="openSolution()">📖 Xem lời giải</button><button id="next" class="btn" style="display:none" onclick="location.href=\'/member/practice\'">→ Câu tiếp</button></div><div id="hint" class="hintline">Chọn đáp án rồi bấm <b>Xác nhận</b> — lời giải chỉ mở sau khi xác nhận.</div><div id="r"></div>';document.getElementById('q').innerHTML=h;typeset(document.getElementById('q'));bind()}
function bind(){let q=Q;
if(q.kind==='TN')document.querySelectorAll('input[name=a]').forEach(function(el){el.addEventListener('change',syncReady)});
else if(q.kind==='DS')document.querySelectorAll('.tf input[type=radio]').forEach(function(el){el.addEventListener('change',syncReady)});
else{let z=document.getElementById('ans');if(z){z.addEventListener('input',syncReady);if(q.kind==='TLN')z.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();check()}})}}
syncReady()}
function answered(){let q=Q;
if(q.kind==='TN')return !!document.querySelector('input[name=a]:checked');
if(q.kind==='DS'){for(let i=0;i<q.statements.length;i++){if(!document.querySelector('input[name=t'+i+']:checked'))return false}return true}
let z=document.getElementById('ans');return !!(z&&z.value.trim())}
function syncReady(){if(checked)return;let b=document.getElementById('chkbtn');if(!b)return;let ready=answered();b.disabled=!ready;b.title=ready?'':'Hãy chọn/nhập đáp án trước khi xác nhận.'}
function openSolution(){if(!checked)return alert('Hãy chọn đáp án và bấm Xác nhận trước.');let box=document.getElementById('solbox');if(!box)return;box.style.display='block';typeset(box);let b=document.getElementById('solbtn');if(b)b.style.display='none'}
function check(){if(checked)return;let q=Q,ok=false,student='';
if(q.kind==='TN'){let z=document.querySelector('input[name=a]:checked');if(!z)return alert('Hãy chọn đáp án.');let i=+z.value;student=String.fromCharCode(65+i);q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')});ok=!!q.options[i].correct}
else if(q.kind==='DS'){ok=true;let a=[];for(let i=0;i<q.statements.length;i++){let z=document.querySelector('input[name=t'+i+']:checked');if(!z)return alert('Chọn đủ Đúng/Sai.');let v=z.value==='1';a.push(v?'Đ':'S');document.getElementById('t'+i).classList.add(v===q.statements[i].correct?'correct':'wrong');if(v!==q.statements[i].correct)ok=false}student=a.join('')}
else{let z=document.getElementById('ans');if(!z||!z.value.trim())return alert('Hãy nhập câu trả lời.');student=z.value.trim();ok=q.kind==='TLN'&&norm(student)===norm(q.answer);}
let note=q.kind==='TL'?'📝 Đã nộp bài tự luận — chờ chấm.':(ok?'✅ ĐÚNG':'❌ SAI');let sol=q.solution||'Chưa có lời giải trong file TEX.';document.getElementById('r').innerHTML='<div class="result '+(ok?'good':'bad')+'">'+note+'</div><div id="solbox" class="solution" style="display:none"><b>📖 Lời giải</b><div>'+sol+'</div></div>';typeset(document.getElementById('q'));checked=true;lockInputs();let sb=document.getElementById('solbtn');if(sb)sb.style.display='inline-block';document.getElementById('next').style.display='inline-block';window.LAST_REVIEW=Object.assign({},q,{student:student,ok:ok});let box=document.getElementById('aibox');if(box){box.innerHTML=ldvlGeminiMiniHtml('🤖 Gemini phản biện câu này')+'<p style="margin-top:10px"><button type="button" class="btn primary" onclick="reviewNow()">🤖 Phản biện</button></p><div id="aiout" class="reviewout"></div>';if(window.ldvlFillGeminiInputs)ldvlFillGeminiInputs()}fetch('/member/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ok:ok,student:student,text:q.text,solution:sol,kind:q.kind,dang:q.dang})}).then(r=>r.json()).then(d=>{if(d.praise)document.getElementById('praise').innerHTML='<div class="praise">'+E(d.praise)+'</div>'})}
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
    done.append({'question':pos+1,'ok':ok,'student':str(d.get('student') or ''),'kind':str(d.get('kind') or ''),'dang':str(d.get('dang') or '')});session.update(practice_streak=st,practice_best=best,practice_right=right,practice_pos=pos+1,practice_done=done);return jsonify(ok=True,praise=praise,streak=st,right=right)

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
    flash=request.args.get('ok') or ''; err=request.args.get('err') or ''
    notice_extra=("<div class='success'>"+html.escape(flash)+"</div>" if flash else "")+("<div class='err'>"+html.escape(err)+"</div>" if err else "")
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
            "<a class='btn' href='/admin/dups?path="+qp+"'>🔎 Trùng</a> "
            "<a class='btn' href='"+html.escape(github_web_edit_url(p),quote=True)+"' target='_blank' rel='noopener'>🐙 Sửa trên GitHub</a> "
            "<a class='btn' href='"+html.escape(github_blob_url(p),quote=True)+"' target='_blank' rel='noopener'>👁 Xem</a> "
            "<form method='post' action='/admin/bank/delete' style='display:inline' onsubmit=\"return confirm('Xóa vĩnh viễn file này trên GitHub?')\">"
            "<input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'>"
            "<button class='btn red' type='submit'>🗑 Xóa</button></form>"
            "</td></tr>"
        )
    body=(
        "<div class='wrap'><div class='panel'><div class='head'>📂 ADMIN · Ngân hàng <code>ngan-hang</code></div><div class='body'>"
        "<div class='notice'><b>Sửa TEX trên GitHub:</b> mở file → tab Edit → sửa → bấm nút xanh <b>Commit changes...</b> → Confirm. "
        "Phải đăng nhập GitHub đúng tài khoản <b>pythonminh</b> (chủ repo). Chỉ mở Edit mà không Commit thì chưa lưu.<br>"
        +html.escape(tok)+" Sau khi Commit, app trên Render đọc bản GitHub ngay (Ctrl+F5), không cần đợi deploy.</div>"
        +notice_extra+
        "<p style='margin:12px 0;display:flex;gap:8px;flex-wrap:wrap'>"
        "<a class='btn primary' href='"+html.escape(gh,quote=True)+"' target='_blank' rel='noopener'>🐙 Mở thư mục ngan-hang trên GitHub</a>"
        "<a class='btn' href='https://github.com/"+html.escape(REPO)+"' target='_blank' rel='noopener'>📦 Repo</a>"
        "<a class='btn' href='/admin/members'>👥 Thành viên</a>"
        "<a class='btn' href='/member'>📚 Mục lục học viên</a>"
        "</p>"
        "<h3>➕ Thêm bài (tạo file de.tex mới)</h3>"
        "<form method='post' action='/admin/bank/add' class='addbank'>"
        "<div class='field'><label>Môn</label><input name='mon' required placeholder='Toán hoặc Vật lý'></div>"
        "<div class='field'><label>Lớp</label><select name='lop'><option>10</option><option>11</option><option>12</option></select></div>"
        "<div class='field'><label>Chương</label><input name='chuong' required placeholder='Chương I. ...'></div>"
        "<div class='field'><label>Bài</label><input name='bai' required placeholder='Bài 1. ...'></div>"
        "<button class='btn green' type='submit'>➕ Thêm hàng</button></form>"
        "<h3>📚 File TEX trong ngan-hang ("+str(len(lrows))+")</h3>"
        "<div class='bankwrap'><table class='selectgrid'><thead><tr><th>Môn</th><th>Lớp</th><th>Chương</th><th>Bài</th><th>Đường dẫn</th><th>Sửa</th></tr></thead><tbody>"
        +(''.join(lrows) or "<tr><td colspan='6' class='muted'>Chưa thấy file .tex trong ngan-hang.</td></tr>")
        +"</tbody></table></div></div></div></div>"
    )
    return page('ADMIN · ngan-hang',body)

@app.post('/admin/bank/add')
def admin_bank_add():
    if not admin_current():return redirect('/admin/login')
    try:
        mon=request.form.get('mon',''); lop=request.form.get('lop',''); chuong=request.form.get('chuong',''); bai=request.form.get('bai','')
        p=bank_new_tex_path(mon,lop,chuong,bai)
        text=(
            f"% Môn: {mon.strip()}\n% Lớp: {str(lop).strip()}\n% Chương: {chuong.strip()}\n% Bài: {bai.strip()}\n% Số câu: 0\n"
            "% App đọc file này trực tiếp — sửa rồi Commit trên GitHub\n"
            "% Ghi nguồn từng câu: \\nguon{SGK} hoặc \\nguon{Bài 1.2 SBT VL 12 KNTT} trong \\begin{ex}...\\end{ex}\n\n"
        )
        _, local=_safe_repo_file(p)
        if local.is_file() or any(str(x.get('path'))==p for x in list_bank_tex()):
            raise ValueError('Bài này đã có: '+p)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding='utf-8')
        if TOKEN:
            github_put_text(p, text, 'ADMIN thêm bài '+p)
        index_upsert_lesson(p, _bank_seg(mon), str(lop).strip(), _bank_seg(chuong), _bank_seg(bai))
        return redirect('/admin?ok='+urllib.parse.quote('Đã thêm '+p))
    except Exception as e:
        return redirect('/admin?err='+urllib.parse.quote(str(e)))

@app.post('/admin/bank/delete')
def admin_bank_delete():
    if not admin_current():return redirect('/admin/login')
    try:
        p=str(request.form.get('path') or '').replace('\\','/')
        _, local=_safe_repo_file(p)
        if TOKEN:
            try: github_delete_path(p, 'ADMIN xóa bài '+p)
            except Exception:
                pass
        try:
            if local.is_file(): local.unlink()
        except Exception:
            pass
        index_remove_lesson(p)
        return redirect('/admin?ok='+urllib.parse.quote('Đã xóa '+p))
    except Exception as e:
        return redirect('/admin?err='+urllib.parse.quote(str(e)))

def _dup_after(p, next_url, key, msg):
    nxt=str(next_url or '')
    if nxt.startswith('/member/dang?'):
        sep='&' if '?' in nxt else '?'
        return redirect(nxt+sep+key+'='+urllib.parse.quote(msg))
    return redirect('/admin/dups?path='+urllib.parse.quote(p,safe='')+'&'+key+'='+urllib.parse.quote(msg))

@app.route('/admin/dups', methods=['GET','POST'])
def admin_dups():
    if not can_manage_bank():return redirect('/admin/login')
    p=str(request.values.get('path') or '').replace('\\','/')
    nxt=str(request.values.get('next') or '')
    try: sha,tex=read_tex(p, need_sha=True); qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    groups=find_duplicate_groups(qs)
    if request.method=='POST':
        if request.form.get('confirm')!='yes':
            return _dup_after(p, nxt, 'err', 'Phải xác nhận trước khi xóa trùng.')
        drop=[]
        extra_ok={i for g in groups for i in g['extras']}
        for raw in request.form.getlist('drop'):
            try: i=int(raw)
            except Exception: continue
            if i in extra_ok: drop.append(i)
        drop=sorted(set(drop))
        if not drop:
            return _dup_after(p, nxt, 'err', 'Chưa chọn câu trùng để xóa.')
        new=tex_without_questions(tex, drop)
        try:
            local=_safe_repo_file(p)[1]
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(new, encoding='utf-8')
            if TOKEN:
                github_put_text(p, new, 'ADMIN xóa '+str(len(drop))+' câu trùng trong '+p, sha or None)
            try:
                from dang_routes import _STATS_CACHE
                _STATS_CACHE.pop(p, None)
            except Exception:
                pass
            return _dup_after(p, nxt, 'ok', 'Đã xóa '+str(len(drop))+' câu trùng, giữ bản đầu mỗi nhóm.')
        except Exception as e:
            return page('Lỗi xóa trùng',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    flash=request.args.get('ok') or ''; err=request.args.get('err') or ''
    blocks=[]
    extra_n=sum(len(g['extras']) for g in groups)
    for gi,g in enumerate(groups,1):
        rows=[]
        for q in g['members']:
            keep=q['idx']==g['keep']
            if keep:
                chk="<span class='tag'>GIỮ</span>"
            else:
                auto=' checked' if g['type']=='dao' else ''
                chk=f"<label><input type='checkbox' name='drop' value='{q['idx']}'{auto}> Xóa bản này</label>"
            rows.append(
                "<tr><td>"+chk+"</td><td>"+str(q.get('stt'))+"</td><td><code>"+html.escape(str(q.get('id') or '—'))+"</code></td>"
                "<td>"+html.escape(str(q.get('kind')))+"</td><td>dòng "+str(q.get('line') or '')+"</td>"
                "<td>"+html.escape((q.get('text') or '')[:180])+"</td></tr>"
            )
        blocks.append(
            "<div class='review'><b>Nhóm "+str(gi)+" · "+html.escape(g['title'])+" · "+str(len(g['members']))+" câu</b>"
            "<table class='selectgrid' style='margin-top:8px'><tr><th></th><th>STT</th><th>ID</th><th>Loại</th><th>Vị trí</th><th>Mở đầu câu</th></tr>"
            +''.join(rows)+"</table></div>"
        )
    if extra_n:
        form_open="<form method='post' action='/admin/dups' onsubmit=\"return confirm('Xóa các câu đã tick? Bản GIỮ không bị xóa.')\">"
        form_close=(
            "<input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'>"
            +(f"<input type='hidden' name='next' value='{html.escape(nxt,quote=True)}'>" if nxt else "")
            +"<p><label><input type='checkbox' name='confirm' value='yes' required> Tôi xác nhận xóa các bản đã tick (giữ câu đầu mỗi nhóm).</label></p>"
            +"<button class='btn red' type='submit'>🗑 Xóa trùng đã chọn</button></form>"
        )
    else:
        form_open="<div>"
        form_close="</div>"
    body=(
        "<div class='wrap'><div class='panel'><div class='head'>🔎 Câu trùng · <code>"+html.escape(p)+"</code></div><div class='body'>"
        +(f"<div class='success'>{html.escape(flash)}</div>" if flash else "")
        +(f"<div class='err'>{html.escape(err)}</div>" if err else "")
        +"<div class='notice'>Trùng <b>đảo đáp án</b>: ô xóa mặc định đã tick. Cùng đề nhưng <b>đáp án khác</b>: ô xóa mặc định trống — xem kỹ rồi mới tick. Bản <b>GIỮ</b> là câu đầu mỗi nhóm, không xóa được từ đây.</div>"
        +("<p class='muted'>Không thấy nhóm trùng.</p>" if extra_n==0 else "")
        +form_open+''.join(blocks or ["<p class='success'>Không có câu trùng.</p>"])+form_close
        +"<p><a class='btn' href='/admin'>← ngan-hang</a> <a class='btn' href='/admin/edit?path="+urllib.parse.quote(p,safe='')+"'>✏️ Sửa TEX</a></p>"
        "</div></div></div>"
    )
    return page('Xóa trùng',body)

@app.get('/admin/logout')
def admin_logout():session.clear();return redirect('/admin/login')

@app.route('/tikz/<hid>.png')
def tikz_png(hid):
    """Ảnh theo hash: có cache thì trả ngay, chưa có thì vẽ rồi cache vĩnh viễn."""
    hid=str(hid or '')
    if not re.fullmatch(r'[a-f0-9]{40}', hid):
        abort(404)
    p, err=tikz_build_png(hid)
    if p:
        resp=send_file(p, mimetype='image/png', conditional=True)
        resp.headers['Cache-Control']='public, max-age=31536000, immutable'
        return resp
    return Response(tikz_error_svg(err), mimetype='image/svg+xml', headers={'Cache-Control':'no-store'})


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
        +"<div class='notice'>Nguồn từng câu: ghi <code>\\nguon{SGK}</code> (hoặc SBT, tên sách…) trong <code>\\begin{ex}</code>. App hiện dòng <b>Nguồn: …</b> trên mỗi câu.</div>"
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
