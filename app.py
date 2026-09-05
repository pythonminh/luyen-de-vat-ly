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
:root{--blue:#176bd3;--blue2:#0f57b4;--line:#d7e2ee;--bg:#f3f7fc;--green:#159447;--red:#cf2d38;--gold:#c98600;--figh:320px;--header-h:72px}
*{box-sizing:border-box}html{height:100%;scroll-padding-top:var(--header-h)}body{margin:0;min-height:100dvh;background:var(--bg);color:#19324d;font:14px/1.45 Segoe UI,Arial,sans-serif;overflow-x:hidden;padding-bottom:env(safe-area-inset-bottom,0px)}img,svg,video{max-width:100%;height:auto}
a{text-decoration:none;color:#145bb0}.top{position:sticky;top:0;z-index:2147483000;background:var(--blue);color:#fff;box-shadow:0 2px 12px #0004}.topin{max-width:none;width:100%;margin:0;padding:calc(8px + env(safe-area-inset-top,0px)) calc(14px + env(safe-area-inset-right,0px)) 8px calc(14px + env(safe-area-inset-left,0px));display:flex;align-items:center;gap:10px;flex-wrap:wrap;min-width:0}.brand{font-weight:900;font-size:20px}.brandbai{display:inline-block;margin-left:6px;padding:1px 7px;border:1px solid #ffffff66;border-radius:6px;font-size:13px;font-weight:800;vertical-align:middle}.brandbox{appearance:none;-webkit-appearance:none;background:none;border:0;color:inherit;text-align:left;padding:0;cursor:pointer;font:inherit;min-width:0;max-width:100%}.sub{font-size:11px;opacity:.9}.clock{margin-left:auto;font:700 12px/1.25 ui-monospace,Consolas,monospace;white-space:nowrap;background:#ffffff22;border:1px solid #ffffff55;border-radius:8px;padding:6px 9px;min-width:0;text-align:center;flex:0 0 auto}.clock .clockday,.clock .clocktime{display:inline}.clock .clockday::after{content:' · '}.nav{display:none;gap:6px;flex-wrap:wrap;align-items:center;min-width:0;flex-basis:100%;width:100%}.top.nav-open .nav{display:flex}.nav a,.nav button,.who{color:#fff;border:1px solid #ffffff55;background:#ffffff15;padding:7px 10px;border-radius:8px;font-weight:800;cursor:pointer;font:inherit;font-weight:800}.who{background:#ffffff28;font-size:14px;white-space:nowrap;max-width:min(22rem,40vw);overflow:hidden;text-overflow:ellipsis}.nav .who{display:none}.whobar{display:inline-flex;align-items:center;min-width:0;max-width:min(22rem,36vw)}.whobar .who{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fsbtn{white-space:nowrap}.navtoggle{display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto;color:#fff;border:1px solid #ffffff55;background:#ffffff15;border-radius:8px;padding:6px 10px;font:800 18px/1 sans-serif;cursor:pointer}.baimenu{display:inline-flex;align-items:center;color:#fff;border:1px solid #ffffff55;background:#ffffff15;border-radius:8px;padding:6px 10px;font:800 13px/1.2 inherit;cursor:pointer;white-space:nowrap}.drawer{position:fixed;inset:0;z-index:2147483602;pointer-events:none;visibility:hidden}.drawer.open{pointer-events:auto;visibility:visible}.drawer-back{position:absolute;inset:0;background:#08142888;opacity:0;transition:opacity .2s}.drawer.open .drawer-back{opacity:1}.drawer-panel{position:absolute;left:0;top:0;bottom:0;width:min(92vw,400px);background:#fff;color:#19324d;box-shadow:8px 0 28px #0004;transform:translateX(-105%);transition:transform .22s ease;display:flex;flex-direction:column;padding-top:env(safe-area-inset-top,0px)}.drawer.open .drawer-panel{transform:none}.drawer-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 12px 8px;border-bottom:1px solid #e5edf5}.drawer-head b{font-weight:400;font-size:14px}.drawer-hint{margin:0;padding:8px 12px;font-size:12px;color:#6c7d90}.drawer-tree{overflow:auto;padding:0 8px 16px;-webkit-overflow-scrolling:touch;flex:1}.drawer-tree details{border-bottom:1px solid #edf2f7}.drawer-tree summary{cursor:pointer;padding:7px 8px;font-weight:400;font-size:12px;list-style:none}.drawer-tree summary::-webkit-details-marker{display:none}.drawer-tree summary::before{content:'▸ ';color:#145bb0}.drawer-tree details[open]>summary::before{content:'▾ '}.drawnest{padding:0 0 6px 10px}.drawbais{display:flex;flex-direction:column;gap:4px;padding:0 0 8px}.drawbai{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 8px;border:1px solid #d7e2ee;border-radius:8px;background:#f8fbff;color:#173a5e;font-weight:400;font-size:12px;line-height:1.35;text-align:left}.drawname{flex:1;min-width:0;text-align:left}.drawn{flex:0 0 auto;margin-left:auto;text-align:right}.drawbai.on{background:#145bb0;color:#fff;border-color:#145bb0}.drawbaiwrap{border-bottom:0}.drawbaiwrap>summary.drawbai{display:flex;justify-content:space-between;align-items:center;gap:8px;list-style:none}.drawer-tree .drawbaiwrap>summary::before{content:none!important}.drawdangs{display:flex;flex-direction:column;gap:4px;padding:4px 0 10px}.drawdang{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 8px;border:1px solid #fdba74;border-radius:8px;background:#fff7ed;color:#9a3412;font-weight:400;font-size:11px;line-height:1.35}.drawdang.on{background:#c2410c;border-color:#c2410c;color:#fff}.drawer-lock{overflow:hidden}.pwatip{position:fixed;z-index:2147483600;left:12px;right:12px;bottom:12px;max-width:440px;margin:auto;background:#fff;color:#19324d;border:1px solid #b8d5f6;border-radius:12px;padding:12px 14px;box-shadow:0 10px 32px #0005;font-weight:400}.pwatip b{color:#145bb0}.pwatip p{margin:6px 0;line-height:1.45}.pwatip .btn{margin-top:6px}@media(display-mode:standalone){#ldvlInstall{display:none!important}}@media(max-width:1024px){html{scroll-padding-top:var(--header-h)}.brand{font-size:15px;line-height:1.2}.brandbox{flex:1 1 8rem;min-width:0;order:1}.sub{display:none}.topin{padding:calc(4px + env(safe-area-inset-top,0px)) 8px 4px;gap:5px 6px;flex-wrap:wrap;align-items:center}.clock{display:none}.whobar{display:inline-flex;order:2;flex:0 1 11rem;max-width:42%;margin:0;min-width:0}.whobar .who{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;font-weight:700;padding:4px 8px}.regline{font-size:10px;padding:0 8px 4px}.navtoggle{display:inline-flex;align-items:center;justify-content:center;margin-left:0;order:3}.nav{display:none;flex-basis:100%;width:100%;padding:4px 0 6px;gap:5px;order:4;min-width:0}.top.nav-open .nav{display:flex}.nav .who{display:none}.nav a,.nav button,.who{padding:5px 8px;font-size:12px}.wrap{padding:8px}.head{padding:7px 8px}.body{padding:8px}.head.quiztop{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;font-size:12px;font-weight:600;line-height:1.35}.quizdang{display:none}.qid{padding:1px 6px;font-size:11px}.qzoombar{margin-left:0;gap:3px}.qzoombar .btn,#pStart{padding:4px 7px;font-size:12px}.qzoombar b{min-width:2.6em;font-size:11px}.palette{margin-bottom:6px;padding:6px 8px;gap:4px}.pitems{flex-wrap:wrap;overflow:visible}.pdang{font-size:11px;font-weight:600;min-width:0}.pitem{padding:3px 6px;font-size:10px;flex-shrink:0}.quizstat{font-size:11px;font-weight:600}.subnav{top:var(--header-h);margin-bottom:8px}.dangtabs{padding:6px 8px}.dtab{padding:5px 8px;font-size:11px;max-width:min(14rem,62vw)}.kindtabs{padding:5px 6px;gap:3px;flex-wrap:wrap}.kindtabs .ktab{padding:4px 6px;font-size:10px;flex:1 1 auto}}@media(orientation:landscape) and (max-height:500px){.brand{font-size:16px}.sub{display:none}.topin{padding-top:calc(4px + env(safe-area-inset-top,0px));padding-bottom:4px}}
.wrap{max-width:none;width:100%;margin:0;padding:12px 16px}.panel{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;max-width:100%}.subnav{position:sticky;z-index:40;top:var(--header-h);margin:0 0 8px;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#fff;box-shadow:0 2px 10px #1b4d8a10}.dangtabs{display:flex;flex-wrap:nowrap;gap:6px;align-items:center;padding:8px;overflow-x:auto;-webkit-overflow-scrolling:touch;background:#fff7ed;border-bottom:1px solid #fed7aa}.dtab{flex:0 0 auto;max-width:min(18rem,70vw);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:1px solid #fdba74;background:#fff;color:#9a3412;border-radius:8px;padding:6px 10px;font-weight:700;font-size:12px}.dtab.on{background:#c2410c;border-color:#c2410c;color:#fff}.kindtabs{display:flex;flex-wrap:wrap;gap:4px;align-items:stretch;padding:6px 8px;background:#eef6ff;border-bottom:1px solid var(--line)}.subnav .kindtabs{position:static;top:auto;border-bottom:0;z-index:auto}.kindtabs .ktab{display:inline-flex;flex:1 1 auto;min-width:0;align-items:center;justify-content:center;border:1px solid #b8d5f6;background:#fff;color:#145bb0;border-radius:7px;padding:5px 4px;font-weight:800;font-size:11px;cursor:pointer;white-space:nowrap}.kindtabs .ktab.on{background:var(--blue);border-color:var(--blue);color:#fff}.kindtabs .ktab.off{opacity:.4;cursor:not-allowed;pointer-events:none}.head{padding:11px 13px;background:#f8fbff;border-bottom:1px solid var(--line);font-weight:900}.body{padding:12px}.btn{display:inline-block;border:1px solid #b8d5f6;background:#fff;color:#145bb0;border-radius:8px;padding:8px 11px;font-weight:800;cursor:pointer}.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}.btn.green{background:#179b55;border-color:#179b55;color:#fff}.btn.red{background:#fff1f1;border-color:#efb1b1;color:#b5222b}.btn:disabled{opacity:.45;cursor:not-allowed;filter:grayscale(.3)}.muted{color:#6c7d90}
.layout{display:grid;grid-template-columns:300px 1fr;gap:10px}.tree{max-height:78vh;overflow:auto}.tree details{border-bottom:1px solid #e8eef5}.tree summary{cursor:pointer;padding:8px 5px;font-weight:900}.tree a{display:block;padding:6px 8px;border-radius:6px}.tree a:hover{background:#eef6ff}.filters{display:grid;gap:8px}.field label{display:block;font-size:11px;color:#66778a;font-weight:800;margin-bottom:3px}.field input,.field select{width:100%;padding:9px;border:1px solid #cbd8e6;border-radius:7px;background:#fff}
.catsearch{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch;margin-top:10px}.catsearch input[name=q]{flex:1 1 100%;min-width:0;padding:10px 12px;border:1px solid #cbd8e6;border-radius:8px;font:inherit}.catsearch select{flex:1 1 180px;min-width:140px;padding:10px 12px;border:1px solid #cbd8e6;border-radius:8px;background:#fff;font:inherit}.catsearch .btn{flex:0 0 auto;align-self:stretch}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,260px),1fr));gap:9px}.card{border:1px solid #d8e3ee;border-radius:10px;padding:11px;background:#fff}.titlebar{padding:10px 12px;border-radius:10px;background:linear-gradient(90deg,#1c61ce,#5798e7);color:#fff;font-weight:900}.meta{font-size:11px;color:#6a7d90}.tag{display:inline-block;border:1px solid #cbd9e7;border-radius:999px;padding:3px 8px;font-size:11px;margin:2px}.free{background:#eefbf2;border-color:#83d39e;color:#14743a}.vip{background:#fff0f7;border-color:#eaa3c9;color:#a2175f}.tag.had{background:#eefbf2;border-color:#83d39e;color:#14743a}.tag.miss{background:#fff8df;border-color:#efca73;color:#855a00}.dang{margin-top:8px;border:1px solid #d9e5f0;background:#fbfdff;border-radius:8px;padding:7px}.dangrow{display:flex;flex-direction:column;align-items:stretch;gap:4px;padding:7px 0;border-bottom:1px solid #edf2f7}.dangrow:last-child{border-bottom:0}.danglink{color:#1a6bb8}.dangname{font-weight:400;line-height:1.45;color:#1a6bb8}.dangno{font-weight:400;color:#1a6bb8;margin-right:.35em}.dangkinds{display:flex;flex-wrap:wrap;gap:4px}.kind{display:inline-block;border:1px solid #d3dfeb;border-radius:999px;padding:2px 7px;font-size:11px;font-weight:800;background:#fff}.ktotal{background:#e9f2ff;border-color:#b8d5f6;color:#145bb0}
.selectwrap{overflow:auto;max-width:100%;-webkit-overflow-scrolling:touch}.selectgrid{width:100%;border-collapse:collapse;font-size:12px}.selectgrid th,.selectgrid td{border:1px solid #dfe7ef;padding:7px}.selectgrid thead th{position:sticky;top:0;z-index:4;background:#e9f2ff;box-shadow:0 1px 0 #c5d4e6}.selectgrid th{background:#e9f2ff;text-align:center}.n{width:52px;padding:6px;border:1px solid #cbd8e6;border-radius:6px;text-align:center}
.bankwrap{max-height:62vh;overflow:auto;border:1px solid var(--line);border-radius:8px}.bankwrap .selectgrid{border-collapse:separate;border-spacing:0}.addbank{display:grid;grid-template-columns:1.1fr 90px 1.3fr 1.3fr auto;gap:7px;align-items:end;margin:10px 0;padding:10px;border:1px dashed #b8d5f6;border-radius:9px;background:#f8fbff}.addbank .field{margin:0}
.qzoombar{display:inline-flex;align-items:center;gap:6px;margin-left:8px;flex-wrap:wrap}.qzoombar .btn{padding:6px 10px;font-size:13px}.qzoombar b{min-width:3.4em;text-align:center}.qid{display:inline-block;border:1px solid #efca73;border-radius:999px;padding:3px 8px;font-size:12px;font-weight:800;background:#fff7dc;color:#7a5300;font-family:Consolas,monospace}.nguonrow{margin:0 0 8px}.nguon{display:inline-block;border:1px solid #7dd3fc;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;background:#f0f9ff;color:#0369a1}.palette{display:flex;flex-direction:column;align-items:stretch;gap:6px;padding:8px;background:#f8fbff;border:1px solid var(--line);border-radius:9px;margin-bottom:10px}.pitems{display:flex;flex-wrap:wrap;gap:5px;width:100%}.pdang{order:-1;font-weight:600;font-size:12px;line-height:1.35;color:#173a5e}.pitem{padding:5px 8px;border:1px solid #cad7e6;border-radius:7px;background:#fff;font-size:11px}.pcur{border:2px solid var(--blue);font-weight:900}.pdone{background:#eaf9ef;border-color:#82c99b}.pwrong{background:#fff0f1;border-color:#eca0a7}.qbox{border:1px solid #d4c4f0;border-radius:11px;padding:16px;font-size:calc(19px * var(--qzoom,1));--qzoom:1;font-family:'Times New Roman',Times,serif;overflow-x:auto;max-width:100%}.qtext,.tf-text,.opt,.solution{line-height:1.75}mjx-container[jax="CHTML"]:not([display="true"]){display:inline!important;vertical-align:baseline!important;margin:0 .12em 0 0!important;padding:0!important;text-indent:0}mjx-container[jax="CHTML"][display="true"]{display:block;margin:.55em 0;max-width:100%;overflow-x:auto}.qtext{font-size:1em;line-height:1.75;margin-bottom:10px;overflow-x:auto;max-width:100%}.tikzfig,.tikz-live{display:flex;align-items:center;justify-content:center;overflow:hidden;height:var(--figh);margin:12px 0;padding:8px;border:1px solid #e2e8f0;border-radius:8px;background:#fff}.qbox .tikzfig,.qbox .tikz-live{height:calc(var(--figh) * var(--qzoom,1))}.tikz-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,170px),1fr));gap:10px;margin:12px 0;align-items:start}.tikz-row .tikzfig,.tikz-row .tikz-live{margin:0;height:calc(var(--figh) * .7)}.tikzfig svg,.tikz-live svg,.tikzfig img,.tikz-img{max-width:100%;max-height:100%;width:auto;height:auto;display:block;margin:0 auto;object-fit:contain}@media(max-width:700px){.tikzfig,.tikz-live{height:calc(var(--figh) * .68)}}.tikz-live:has(svg) .tikz-wait{display:none}.ytbox{margin:12px 0;max-width:min(100%,620px)}.ytplay{display:flex;align-items:center;justify-content:center;gap:12px;width:100%;aspect-ratio:16/9;padding:0;border:1px solid #cfddeb;border-radius:11px;background:#0b1220 center/cover no-repeat;color:#fff;font-weight:900;font-size:15px;cursor:pointer;text-shadow:0 1px 4px #000c;box-shadow:inset 0 0 0 300px #0b122059}.ytplay:hover .ytplay-ico{background:#f00}.ytplay-ico{display:inline-flex;align-items:center;justify-content:center;width:56px;height:39px;border-radius:9px;background:#e60000cc;font-size:18px;text-shadow:none}.ytframe{display:block;width:100%;aspect-ratio:16/9;border:0;border-radius:11px}.ytlink{display:inline-block;margin-top:5px;font-size:12px;font-weight:800}.exlink{display:inline-block;margin:6px 0;font-weight:800}.tex-table{border-collapse:collapse;margin:10px auto;font-size:15px;background:#fff;max-width:100%}.tex-table td,.tex-table th{border:1px solid #334155;padding:6px 10px;text-align:center}.tex-list{margin:8px 0;padding:0;line-height:1.75}ul.tex-list{padding-left:1.35em}ol.tex-list{list-style:none;counter-reset:ltn;padding:0}ol.tex-list>li{position:relative;margin:8px 0;padding:2px 0 2px 2.45em}ol.tex-list>li::before{content:counter(ltn);counter-increment:ltn;position:absolute;left:0;top:.12em;width:1.65em;height:1.65em;border:1.5px solid #145bb0;border-radius:50%;background:#fff;color:#145bb0;font:800 12px/1.65em Segoe UI,Arial,sans-serif;text-align:center;box-sizing:border-box}.immini{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;margin:10px 0}@media(max-width:700px){.immini{grid-template-columns:1fr}}.opt{display:block;border:2px solid #d8e4f0;border-radius:9px;padding:.55em .7em;margin:.45em 0;cursor:pointer;font-size:1em}.opt:hover{background:#f8fbff}.opt:has(input:checked){border-color:var(--blue);background:#f1f7ff;box-shadow:0 0 0 3px #176bd322}.quizacts{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}.hintline{margin-top:8px;font-size:13px;color:#6c7d90;font-weight:700}.practice-split.is-ai{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(280px,.9fr);gap:12px;align-items:start}.practice-q{min-width:0}.practice-ai{position:sticky;top:calc(var(--header-h) + 8px);max-height:calc(100dvh - var(--header-h) - 16px);overflow-y:auto;-webkit-overflow-scrolling:touch;border:1px solid #cab9f0;background:#faf8ff;border-radius:12px;padding:12px;box-shadow:0 4px 18px #1b4d8a14}.practice-ai .review{margin-top:0}.modebar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}.modebar .btn.primary{min-width:160px}@media(max-width:900px){.practice-split.is-ai{grid-template-columns:1fr}.practice-ai{position:relative;top:auto;max-height:min(52dvh,520px)}}.tfgrid{margin:8px 0 4px;display:flex;flex-direction:column;gap:0}.qheadline{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px}.qbadge{display:inline-block;background:#5b21b6;color:#fff;border-radius:8px;padding:.28em .8em;font:400 1em 'Times New Roman',Times,serif;flex-shrink:0;line-height:1.3}.qstem{flex:1 1 100%;min-width:100%;width:100%}.qbody.ds.hassplit{display:grid;grid-template-columns:minmax(210px,.9fr) minmax(250px,1.2fr);gap:18px;align-items:start}.qfig .tikzfig,.qfig .tikz-live{height:auto;max-height:min(68vh,540px);margin:0;width:100%}.qfig .tex-table{margin:0 auto}.tflab{display:inline-flex;align-items:center;justify-content:center;min-width:1.75em;height:1.55em;padding:0 .3em;border:1px solid #c4b5fd;border-radius:6px;background:#f5f3ff;color:#5b21b6;margin:0;font:400 .95em 'Times New Roman',Times,serif;flex-shrink:0}.tf-colhead,.tfgrid .tf{display:grid;grid-template-columns:2.2em minmax(0,1fr) 3.1em 3.1em;column-gap:4px;align-items:center}.tf-colhead{padding:0 2px 2px}.tf-h{text-align:center;font-weight:400;font-size:.95em;line-height:1.15}.tf-h.yes{color:#5b21b6}.tf-h.no{color:#e11d48}.tfgrid .tf{border:0;border-radius:0;padding:7px 2px;margin:0;background:transparent}.tf-text{min-width:0;font-size:1em;line-height:1.7}.tf-box{width:1.2em;height:1.2em;border:2px solid #475569;border-radius:3px;background:#fff;justify-self:center;display:inline-flex;align-items:center;justify-content:center;padding:0;margin:0;cursor:pointer;position:relative}.tf-box input{appearance:none;-webkit-appearance:none;position:absolute;inset:0;margin:0;opacity:0;cursor:pointer}.tf-box:has(input:checked),.tf-box.on,.tf-box.pick{background:#fff;border-color:#475569}.tf-box:has(input:checked)::after,.tf-box.on::after,.tf-box.pick::after{content:"";width:.48em;height:.48em;border-radius:1px;background:#1d4ed8}.tfgrid .tf.correct,.tfgrid .tf.ok{background:#f7fbf8!important;border:0!important;box-shadow:none;border-radius:6px}.tfgrid .tf.wrong,.tfgrid .tf.noans{background:#fdf8f8!important;border:0!important;box-shadow:none;border-radius:6px}.tfgrid .tf.correct .tf-text,.tfgrid .tf.ok .tf-text{color:#2f4a38;font-weight:400}.tfgrid .tf.wrong .tf-text,.tfgrid .tf.noans .tf-text{color:#6a3a3a;font-weight:400}.tfgrid .tf.correct .tf-box:has(input:checked)::after,.tfgrid .tf.ok .tf-box.on::after,.tfgrid .tf.correct .tf-box.on::after,.tfgrid .tf.noans .tf-box.on::after{background:#15803d}.tfgrid .tf.wrong .tf-box:has(input:checked)::after,.tfgrid .tf.wrong .tf-box.pick::after{background:#b91c1c}@media(max-width:700px){.tf-colhead,.tfgrid .tf{grid-template-columns:1.9em minmax(0,1fr) 2.6em 2.6em}.tf-h{font-size:.82em}.qbody.ds.hassplit{grid-template-columns:1fr}}.correct{background:#f7fbf8!important;border-color:#c5ddd0!important}.wrong{background:#fdf8f8!important;border-color:#e6d0d0!important}.solution{margin-top:11px;padding:12px;border:1px solid #bad5f2;border-radius:9px;background:#f7fbff}.result{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;padding:8px 10px;border-radius:9px;margin-top:10px;font-weight:400;font-family:'Times New Roman',Times,serif}.result .keyline,.result .vres{margin:0;font-size:.95em;font-weight:400;line-height:1.5}.result .keygrid{display:inline-flex;flex-wrap:wrap;align-items:center;gap:4px 14px;margin:0 0 0 8px;vertical-align:middle}.result .keyrow{display:inline-flex;align-items:center;gap:6px}.result .keylab{font-weight:400;opacity:.9;margin-right:2px}.result .keycell{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;font-weight:400;white-space:nowrap}.result .klet{font-size:.78em;color:#64748b;line-height:1}.result .kcirc{display:inline-flex;width:2.15em;height:2.15em;border:0;border-radius:50%;align-items:center;justify-content:center;font-weight:400;font-size:1.05em;font-family:'Times New Roman',Times,serif;flex-shrink:0}.result .kcirc.d{background:#f8f1c8;color:#1e4b8c}.result .kcirc.s{background:#d8eedd;color:#b42318}.result .kcirc.tn{background:#e8f0f8;color:#1e4b8c}.result .keycell.ok{color:inherit}.result .keycell.bad .kcirc{box-shadow:0 0 0 1px #c98a8a}.good{background:#f7fbf8;color:#2f4a38;border:1px solid #d5e6db}.bad{background:#fdf8f8;color:#6a3a3a;border:1px solid #ead4d4}.praise{margin:10px 0;padding:11px;border-radius:9px;background:#fff8df;border:1px solid #efca73;color:#855a00;font-size:16px;font-weight:900}.review{margin-top:12px;padding:12px;border:1px solid #cab9f0;background:#faf8ff;border-radius:9px}.reviewout{margin-top:10px;white-space:pre-wrap;line-height:1.7}.reviewout .ai-y{display:block;white-space:pre-wrap;margin:8px 0;padding:9px 11px;border-radius:8px;border-left:5px solid #cbd8e6;background:#fff}.reviewout .ai-y.ok{color:#116a32;background:#eaf8ef;border-color:#42ae6b}.reviewout .ai-y.bad{color:#a41f28;background:#fff0f1;border-color:#e04d56}.reviewout .ai-y .ai-tag{font-weight:900}.gkeyrow{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;align-items:center}.gkeygrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:8px 0}.gkeycell label{display:block;font-size:11px;font-weight:800;color:#66778a;margin-bottom:4px}.gkey-input{width:100%;min-width:0;padding:11px 12px;border:1px solid #cbd8e6;border-radius:8px;font-size:15px}.gkeylink{display:inline-flex;align-items:center;gap:6px;font-weight:900;font-size:16px}.gkeylink:hover{text-decoration:underline}.gkeyhead{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px}.gkeyhead b{margin:0}.gkeyfold{padding:5px 10px;font-size:12px;white-space:nowrap}.review.gkey-collapsed .gkeybody{display:none}@media(max-width:800px){.gkeygrid{grid-template-columns:1fr}}.adminbox{display:grid;grid-template-columns:1fr 1fr;gap:10px}.code{width:100%;height:70vh;font:12px/1.5 Consolas,monospace;padding:10px;border:1px solid #cbd8e6;border-radius:8px}.notice{padding:10px;border:1px solid #b6d3ef;background:#f4f9ff;border-radius:8px}.err{color:#b42318;font-weight:800}.success{color:#0d7b35;font-weight:800}
@media(max-width:900px){.layout{grid-template-columns:1fr}.adminbox{grid-template-columns:1fr}.tree{max-height:38vh}.addbank{grid-template-columns:1fr}}
.dtab{display:flex;flex-direction:column;align-items:flex-start;gap:4px;max-width:min(22rem,86vw);white-space:normal;overflow:visible;text-overflow:unset;line-height:1.3}
.dtab .dname{font-weight:800}
.dkinds{display:flex;flex-wrap:wrap;gap:3px}
.dk{display:inline-block;border:1px solid #fdba74;border-radius:999px;padding:1px 6px;font-size:10px;font-weight:800;background:#fff;color:#9a3412}
.dk.z{opacity:.42;font-weight:700}
.dtab.on .dk{border-color:#ffffff99;background:#ffffff22;color:#fff}
.drawdang{flex-wrap:wrap}
.drawdang .dkinds{flex:1 1 100%}
.drawdang.on .dk{border-color:#ffffff99;background:#ffffff22;color:#fff}
@media(max-width:1024px){.dtab{max-width:min(20rem,90vw);white-space:normal}}
.admindang{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:8px 10px;background:#f8fbff;border-top:1px solid #d7e2ee}
.admindang .simrev{flex:1 1 100%;margin-top:6px;padding:10px;border:1px solid #fdba74;border-radius:9px;background:#fff7ed}
.admindang .simrev h4{margin:10px 0 4px;font-size:13px}
.admindang .simbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0;padding:8px;border:1px solid #fdba74;border-radius:8px;background:#fff;position:sticky;top:0;z-index:2}
.admindang .simx{display:inline-flex;align-items:center;gap:8px;cursor:pointer;font-weight:800;color:#fff;background:#9f1239;border-radius:999px;padding:4px 12px 4px 8px}
.admindang .simx input[type=checkbox]{-webkit-appearance:checkbox;appearance:checkbox;width:22px;height:22px;min-width:22px;min-height:22px;margin:0;accent-color:#fff;flex:0 0 auto}
.admindang .gapnote{font-size:13px;font-weight:700;color:#9a3412}
.admindang #aiGapOut{flex:1 1 100%;font-size:13px;line-height:1.45}
html:has(body.cinema){scroll-padding-top:0}
body.cinema{background:#fff;padding:0}
body.cinema .cinemahud{position:fixed;top:calc(6px + env(safe-area-inset-top,0px));right:calc(6px + env(safe-area-inset-right,0px));z-index:20;display:flex;gap:6px}
body.cinema .cinemahud a,body.cinema .cinemahud button{width:40px;height:40px;border-radius:999px;border:1px solid #c5d6ea;background:#ffffffee;color:#145bb0;font-weight:900;font-size:18px;display:flex;align-items:center;justify-content:center;padding:0;box-shadow:0 2px 10px #0002}
body.cinema .cinema-q{min-height:100dvh;padding:10px 12px calc(16px + env(safe-area-inset-bottom,0px));padding-top:calc(10px + env(safe-area-inset-top,0px))}
body.cinema .qbox{border:0;border-radius:0;padding:4px 12px 24px;font-size:calc(21px * var(--qzoom,1));max-width:none;width:100%;margin:0}
body.cinema .qid,.cinema-wait .qid{display:none}
body.cinema .nguonrow{display:none}
body.cinema .opt{cursor:default;display:flex;align-items:center;gap:10px}
body.cinema .opt.picked{border-color:var(--blue);background:#eef6ff;box-shadow:0 0 0 3px #176bd322}
body.cinema .opt.correct,body.cinema .tf.correct{background:#f3faf5!important;border:2px solid #86c99a!important;box-shadow:none}
body.cinema .opt.correct .okmark,body.cinema .okmark{display:inline-block;margin-left:.4em;padding:.12em .55em;border-radius:999px;background:#15803d;color:#fff;font-size:.78em;font-weight:900;vertical-align:middle;white-space:nowrap}
body.cinema .opt.wrong,body.cinema .tf.wrong{background:#fecaca!important;border:3px solid #b91c1c!important}
body.cinema .tfgrid .tf.correct{background:#f7fbf8!important;border:0!important}
body.cinema .tfgrid .tf.wrong{background:#fdf8f8!important;border:0!important}
body.cinema .tfgrid .tf.correct .tf-text,body.cinema .tfgrid .tf.ok .tf-text{color:#2f4a38!important}
body.cinema .tfgrid .tf.wrong .tf-text,body.cinema .tfgrid .tf.noans .tf-text{color:#6a3a3a!important}
body.cinema .tfgrid .tf{display:grid;align-items:center}
body.cinema .tf-text{min-width:0;padding-right:8px}
body.cinema .tf-flags{display:none}
body.cinema .tf-flags .okmark{margin-left:0;min-width:4.6em;text-align:center}
body.cinema .tf-flags .pickmark{margin-left:0;font-size:.7em}
body.cinema .pickmark{display:inline-block;margin-left:.4em;font-size:.78em;font-weight:900;color:#145bb0}
body.cinema .err{padding:18px 12px;max-width:36rem;margin:20vh auto 0;text-align:center}
"""

GEMINI_CLIENT_JS = r"""<script>
window.LDVL_GKEY='ldvlGeminiKey';
window.LDVL_GKEYS='ldvlGeminiKeys';
window.LDVL_GKEYFOLD='ldvlGeminiKeysFolded';
function ldvlGetGeminiKeys(){var arr=['','',''];try{var raw=localStorage.getItem(LDVL_GKEYS);if(raw){var j=JSON.parse(raw);if(Array.isArray(j)){for(var i=0;i<3;i++)arr[i]=String(j[i]||'').trim()}}if(!arr[0]){var old=(localStorage.getItem(LDVL_GKEY)||'').trim();if(old)arr[0]=old}}catch(e){}return arr}
function ldvlFilledKeys(arr){arr=arr||ldvlGetGeminiKeys();return arr.filter(function(k){return String(k||'').trim().length>=20})}
function ldvlKeysWantFold(){try{var v=localStorage.getItem(LDVL_GKEYFOLD);if(v==='0')return false;if(v==='1')return true}catch(e){}return ldvlFilledKeys().length>0}
function ldvlApplyKeyFold(){var fold=ldvlKeysWantFold();document.querySelectorAll('#gemini-key').forEach(function(box){box.classList.toggle('gkey-collapsed',fold);var btn=box.querySelector('.gkeyfold');if(btn)btn.textContent=fold?'▶ Mở rộng':'▼ Thu nhỏ'})}
function ldvlToggleGeminiKeys(){var box=document.getElementById('gemini-key');if(!box)return;var next=!box.classList.contains('gkey-collapsed');try{localStorage.setItem(LDVL_GKEYFOLD,next?'1':'0')}catch(e){}ldvlApplyKeyFold()}
function ldvlReadKeyInputs(){var arr=ldvlGetGeminiKeys();document.querySelectorAll('.gkey-input').forEach(function(el){var i=parseInt(el.getAttribute('data-i'),10);if(i>=0&&i<3)arr[i]=String(el.value||'').trim()});return arr}
function ldvlFillGeminiInputs(){var arr=ldvlGetGeminiKeys();document.querySelectorAll('.gkey-input').forEach(function(el){var i=parseInt(el.getAttribute('data-i'),10);if(!(i>=0&&i<3))i=0;if(!String(el.value||'').trim())el.value=arr[i]||''});var n=ldvlFilledKeys(arr).length;var st=document.getElementById('gkey-status');if(st)st.textContent=n?('✅ Đã có '+n+'/3 key trên máy này.'):'⚠️ Chưa có key — dán 1–3 ô rồi bấm Lưu.';ldvlApplyKeyFold()}
function ldvlSaveGeminiKey(){var arr=ldvlReadKeyInputs();var n=ldvlFilledKeys(arr).length;if(!n){alert('Dán ít nhất 1 Gemini API key (thường bắt đầu bằng AIza) vào các ô Key 1–3.');return false}try{localStorage.setItem(LDVL_GKEYS,JSON.stringify(arr));if(arr[0])localStorage.setItem(LDVL_GKEY,arr[0]);localStorage.setItem(LDVL_GKEYFOLD,'1')}catch(e){}ldvlFillGeminiInputs();alert('Đã lưu '+n+' key Gemini trên trình duyệt này.');return true}
function ldvlEscAi(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function ldvlAiNl(s){return ldvlEscAi(s).replace(/\n/g,'<br>')}
function ldvlAiVerdict(chunk){
  var head=String(chunk||'').split(/Lý do/i)[0]||'';
  var m=head.match(/học sinh chọn[\s\S]{0,80}?[:：]\s*(đúng|sai)\b/i);
  if(!m) m=head.match(/[:：]\s*(đúng|sai)\s*[\.!]?\s*$/i);
  if(!m) return '';
  return m[1].toLowerCase()==='đúng'?'ok':'bad';
}
function ldvlFmtAi(t){
  t=String(t||'').replace(/\r\n/g,'\n');
  var re=/Ý\s*\d+\s*[).]/g, idx=[], m;
  while((m=re.exec(t))) idx.push(m.index);
  if(!idx.length) return ldvlAiNl(t);
  var html=ldvlAiNl(t.slice(0,idx[0]));
  for(var i=0;i<idx.length;i++){
    var start=idx[i], end=i+1<idx.length?idx[i+1]:t.length, chunk=t.slice(start,end), after='';
    var stop=chunk.search(/\n(?=ĐÁP ÁN ĐÚNG:|KẾT QUẢ|LỖI DỄ NHẦM|PHÂN TÍCH ĐỀ|GIẢI THÍCH|ĐÁP ÁN VÀ ĐỐI CHIẾU)/);
    if(stop>0){after=chunk.slice(stop);chunk=chunk.slice(0,stop)}
    var cls=ldvlAiVerdict(chunk);
    var inner=ldvlAiNl(chunk).replace(/^(<br>)+/,'').replace(/(<br>)+$/,'');
    if(cls==='ok') inner=inner.replace(/^Ý\s*\d+\s*[).]/,function(x){return '<span class="ai-tag">✅ '+x+'</span>'});
    else if(cls==='bad') inner=inner.replace(/^Ý\s*\d+\s*[).]/,function(x){return '<span class="ai-tag">❌ '+x+'</span>'});
    html+='<div class="ai-y'+(cls?' '+cls:'')+'">'+inner+'</div>';
    if(after) html+=ldvlAiNl(after);
  }
  return html;
}
function ldvlGeminiMiniHtml(title){title=title||'🤖 Nạp Key Gemini';return '<div class="review" id="gemini-key"><div class="gkeyhead"><b>'+title+'</b><button type="button" class="btn gkeyfold" onclick="ldvlToggleGeminiKeys()">▼ Thu nhỏ</button></div><div class="muted" id="gkey-status"></div><div class="gkeybody"><p><a class="gkeylink" href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">🔗 Lấy key miễn phí tại Google AI Studio</a></p><p class="muted">Tạo tối đa 3 key rồi dán vào 3 ô cạnh nhau. Key chỉ lưu trên trình duyệt này.</p><div class="gkeygrid"><div class="gkeycell"><label>Key 1</label><input class="gkey-input" data-i="0" type="password" autocomplete="off" placeholder="AIza... key 1"></div><div class="gkeycell"><label>Key 2</label><input class="gkey-input" data-i="1" type="password" autocomplete="off" placeholder="AIza... key 2"></div><div class="gkeycell"><label>Key 3</label><input class="gkey-input" data-i="2" type="password" autocomplete="off" placeholder="AIza... key 3"></div></div><div class="gkeyrow"><button type="button" class="btn primary" onclick="ldvlSaveGeminiKey()">💾 Lưu 3 key</button><button type="button" class="btn" onclick="ldvlPingGemini()">🧪 Thử key</button></div><div id="gkey-ping" class="reviewout"></div></div></div>'}
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
        "<div class='review' id='gemini-key'>"
        "<div class='gkeyhead'><b>🤖 Nạp Key Gemini</b>"
        "<button type='button' class='btn gkeyfold' onclick='ldvlToggleGeminiKeys()'>▼ Thu nhỏ</button></div>"
        "<div class='muted' id='gkey-status'></div>"
        "<div class='gkeybody'>"
        "<p><a class='gkeylink' href='https://aistudio.google.com/apikey' target='_blank' rel='noopener'>🔗 Lấy key miễn phí tại Google AI Studio</a></p>"
        "<p class='muted'>Mở link trên → Create API key → dán vào 3 ô cạnh nhau (có thể chỉ điền 1 ô). Key chỉ lưu trên trình duyệt này.</p>"
        "<div class='gkeygrid'>"
        "<div class='gkeycell'><label>Key 1</label><input class='gkey-input' data-i='0' type='password' autocomplete='off' placeholder='AIza... key 1'></div>"
        "<div class='gkeycell'><label>Key 2</label><input class='gkey-input' data-i='1' type='password' autocomplete='off' placeholder='AIza... key 2'></div>"
        "<div class='gkeycell'><label>Key 3</label><input class='gkey-input' data-i='2' type='password' autocomplete='off' placeholder='AIza... key 3'></div>"
        "</div>"
        "<div class='gkeyrow'><button type='button' class='btn primary' onclick='ldvlSaveGeminiKey()'>💾 Lưu 3 key</button>"
        "<button type='button' class='btn' onclick='ldvlPingGemini()'>🧪 Thử key</button></div>"
        "<div id='gkey-ping' class='reviewout'></div></div>" + extra + "</div>"
    )

def _class_label(m) -> str:
    try:
        import membership as _pkg
        return _pkg.scope_label(m)
    except Exception:
        pass
    raw = str((m or {}).get("class") or (m or {}).get("grade") or "").strip()
    if not raw:
        return ""
    low = raw.casefold()
    if low.startswith("lớp") or low.startswith("lop"):
        return raw
    return "Lớp " + raw

def _who_chip(text: str, extra: str = "") -> str:
    label = text + (f" · {extra}" if extra else "")
    return (
        f"<span class='who' title='{html.escape(label, quote=True)}'>"
        f"{html.escape(label)}</span>"
    )

def page(title: str, body: str, cinema: bool = False) -> Response:
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
            who = _who_chip("👤 " + nm, _class_label(m))
        nav.append("<a href='/member/goi'>🎫 Gói</a>")
        nav.append("<a href='/member/ai'>🤖 Gemini</a>")
        nav.append("<a href='/member/logout'>🚪 Thoát</a>")
    elif role == "admin":
        who = _who_chip("🔐 ADMIN", _class_label(member_current()))
        nav += [
            "<a href='/xem'>📺 Xem chiếu</a>",
            "<a href='/admin'>📂 ngan-hang</a>",
            f"<a href='{html.escape(github_folder_url(), quote=True)}' target='_blank' rel='noopener'>🐙 GitHub</a>",
            "<a href='/admin/members'>👥 Thành viên</a>",
            "<a href='/admin/ly-thuyet'>📖 Duyệt LT</a>",
            "<a href='/admin/logout'>🚪 Thoát</a>",
        ]
    else:
        nav += [
            "<a href='/xem'>📺 Xem chiếu</a>",
            "<a href='/member/login'>🔑 Đăng nhập</a>",
            "<a href='/member/register'>📝 Đăng ký</a>",
        ]
    top = (
        "<div class='top'><div class='topin'><button type='button' class='brandbox' id='ldvlBaiBtn' aria-controls='ldvlDrawer' title='Chọn lớp, chương, bài'>"
        "<div class='brand'>📚 Luyện Đề Toán Lý <span class='brandbai'>Bài ▾</span></div>"
        "<div class='sub'>Zalo thầy Minh 0946111107</div></button>"
        "<time class='clock' id='ldvlClock' datetime=''>…</time>"
        + (f"<span class='whobar'>{who}</span>" if who else "")
        + "<button type='button' class='navtoggle' id='ldvlNavToggle' aria-expanded='false' aria-controls='ldvlNav' title='Thu / mở menu'>☰</button>"
        + "<div class='nav' id='ldvlNav'>" + who + "".join(nav)
        + "<button type='button' class='fsbtn' id='ldvlInstall' onclick='ldvlInstallApp()' title='Lưu ra màn hình chính'>📲 Cài app</button>"
        + "<button type='button' class='fsbtn' id='ldvlFs' onclick='ldvlToggleFs()' title='Toàn màn hình'>⛶ Toàn màn hình</button>"
        + "</div></div>"
        "<div class='regline'>Đăng ký dùng: liên hệ thầy Minh 0357991010 (Zalo)</div>"
        "</div>"
    )
    try:
        cur_path = str(request.args.get("path") or session.get("practice_path") or "").strip()
        cur_dang = str(request.args.get("dang") or session.get("practice_dang") or "").strip()
    except Exception:
        cur_path = ""
        cur_dang = ""
    drawer = lesson_drawer_html(member_current() if role in ("member", "admin") else None, cur_path, cur_dang)
    mj = (
        "<script>"
        "window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']],processEscapes:true,packages:{'[+]':['base','ams']}},"
        "chtml:{displayAlign:'left',displayIndent:'0'},"
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
        "var day=d+' '+p(n.getDate())+'/'+p(n.getMonth()+1)+'/'+n.getFullYear();"
        "var tm=p(n.getHours())+':'+p(n.getMinutes())+':'+p(n.getSeconds());"
        "if(!el.querySelector('.clockday'))el.innerHTML='<span class=\"clockday\"></span> <span class=\"clocktime\"></span>';"
        "el.querySelector('.clockday').textContent=day;el.querySelector('.clocktime').textContent=tm;"
        "el.dateTime=n.toISOString()};"
        "window.ldvlToggleFs=function(){var d=document,el=d.documentElement;"
        "if(d.fullscreenElement||d.webkitFullscreenElement){(d.exitFullscreen||d.webkitExitFullscreen).call(d);}"
        "else if(el.requestFullscreen)el.requestFullscreen().catch(function(){});"
        "else if(el.webkitRequestFullscreen)el.webkitRequestFullscreen();};"
        "window.ldvlPwaStandalone=function(){return window.matchMedia('(display-mode: standalone)').matches||!!window.navigator.standalone};"
        "window.ldvlDeferredPrompt=null;"
        "window.addEventListener('beforeinstallprompt',function(e){e.preventDefault();window.ldvlDeferredPrompt=e;var b=document.getElementById('ldvlInstall');if(b)b.style.display='';});"
        "window.ldvlInstallApp=function(){"
        "if(ldvlPwaStandalone())return;"
        "var ev=window.ldvlDeferredPrompt,tip=document.getElementById('ldvlPwaTip');"
        "if(ev){ev.prompt();ev.userChoice.finally(function(){window.ldvlDeferredPrompt=null;});return;}"
        "if(tip)tip.hidden=!tip.hidden;"
        "};"
        "window.ldvlSyncHeaderH=function(){var t=document.querySelector('.top');if(!t)return;document.documentElement.style.setProperty('--header-h',Math.ceil(t.getBoundingClientRect().height)+'px')};"
        "document.addEventListener('DOMContentLoaded',function(){ldvlTickClock();setInterval(ldvlTickClock,1000);ldvlSyncHeaderH();"
        "var topEl=document.querySelector('.top');"
        "if(topEl&&window.ResizeObserver){try{new ResizeObserver(function(){ldvlSyncHeaderH()}).observe(topEl)}catch(e){}}"
        "window.addEventListener('resize',ldvlSyncHeaderH);"
        "var tb=document.getElementById('ldvlNavToggle'),nv=document.getElementById('ldvlNav');"
        "window.ldvlNavApply=function(on){var top=document.querySelector('.top');if(!top||!tb)return;"
        "top.classList.toggle('nav-open',!!on);tb.setAttribute('aria-expanded',on?'true':'false');tb.textContent=on?'✕':'☰';"
        "try{localStorage.setItem('ldvlNavOpen',on?'1':'0')}catch(e){}ldvlSyncHeaderH();};"
        "if(tb&&nv){var want=false;try{var v=localStorage.getItem('ldvlNavOpen');if(v==='1')want=true;else if(v==='0')want=false;else want=window.innerWidth>1024;}catch(e){want=window.innerWidth>1024}"
        "ldvlNavApply(want);tb.onclick=function(){ldvlNavApply(!document.querySelector('.top').classList.contains('nav-open'));};}"
        "var db=document.getElementById('ldvlBaiBtn'),dr=document.getElementById('ldvlDrawer');"
        "function ldvlDrawerOpen(on){if(!dr)return;dr.classList.toggle('open',!!on);dr.setAttribute('aria-hidden',on?'false':'true');document.body.classList.toggle('drawer-lock',!!on);}"
        "if(db&&dr){db.onclick=function(){ldvlDrawerOpen(!dr.classList.contains('open'));};"
        "var bk=document.getElementById('ldvlDrawerBack'),cl=document.getElementById('ldvlDrawerClose');"
        "if(bk)bk.onclick=function(){ldvlDrawerOpen(false)};if(cl)cl.onclick=function(){ldvlDrawerOpen(false)};"
        "document.addEventListener('keydown',function(e){if(e.key==='Escape')ldvlDrawerOpen(false)});"
        "}"
        "if(ldvlPwaStandalone()){var b=document.getElementById('ldvlInstall');if(b)b.style.display='none';}"
        "if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js',{scope:'/'}).catch(function(){});}"
        "});"
        "document.addEventListener('fullscreenchange',function(){var b=document.getElementById('ldvlFs');if(b)b.textContent=document.fullscreenElement?'⛶ Thu nhỏ':'⛶ Toàn màn hình'});"
        "</script>"
        "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js' onerror=\"this.onerror=null;this.src='https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.min.js'\"></script>"
    )
    pwa_tip = (
        "<div id='ldvlPwaTip' class='pwatip' hidden>"
        "<b>📲 Lưu ra màn hình chính</b>"
        "<p><b>Android / máy tính (Chrome):</b> bấm <b>Cài app</b> trên thanh trên, hoặc menu <b>⋮</b> → <b>Cài đặt ứng dụng</b>.</p>"
        "<p><b>iPhone / iPad:</b> bấm nút <b>Chia sẻ</b> (ô vuông có mũi tên) → <b>Thêm vào Màn hình chính</b>.</p>"
        "<button type='button' class='btn primary' onclick=\"document.getElementById('ldvlPwaTip').hidden=true\">Đã hiểu</button>"
        "</div>"
    )
    head = (
        "<meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#176bd3'><meta name='mobile-web-app-capable' content='yes'>"
        "<meta name='apple-mobile-web-app-capable' content='yes'><meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>"
        "<meta name='apple-mobile-web-app-title' content='Luyện Đề'><meta name='application-name' content='Luyện Đề'>"
        "<link rel='manifest' href='/manifest.webmanifest'><link rel='apple-touch-icon' href='/static/pwa/apple-touch-icon.png'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style>{mj}"
    )
    cls = " class='cinema'" if cinema else ""
    chrome = "" if cinema else (top + drawer)
    extra = "" if cinema else (pwa_tip + GEMINI_CLIENT_JS)
    return Response(f"<!doctype html><html lang='vi'><head>{head}</head><body{cls}>{chrome}{body}{extra}</body></html>", mimetype='text/html')

def load_json(path: Path, default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def index_data():return load_json(INDEX_FILE, {"lessons": [], "total_files": 0, "total_questions": 0})
def members_data():return load_json(MEMBERS_FILE, {"members": []})

def _password_key():
    return hashlib.sha256((app.secret_key or "ldvl").encode("utf-8")).digest()

def seal_password(plain):
    raw = str(plain or "").encode("utf-8")
    if not raw:
        return ""
    key = _password_key()
    mixed = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return "v1:" + base64.urlsafe_b64encode(mixed).decode("ascii")

def unseal_password(token):
    t = str(token or "")
    if t.startswith("v1:"):
        try:
            mixed = base64.urlsafe_b64decode(t[3:].encode("ascii"))
            key = _password_key()
            return bytes(b ^ key[i % len(key)] for i, b in enumerate(mixed)).decode("utf-8")
        except Exception:
            return ""
    if t and len(t) < 80 and not re.fullmatch(r"[0-9a-fA-F]{64}", t):
        return t
    return ""

def set_member_password(member, plain):
    plain = str(plain or "")
    member["password_sha256"] = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    member["password_enc"] = seal_password(plain)
    return member

def member_password_plain(member):
    if not member:
        return ""
    return unseal_password(member.get("password_enc") or member.get("password") or "")

def persist_member_password_on_login(data, member, plain):
    """Sau đăng nhập đúng: lưu bản xem được cho ADMIN nếu chưa có (hoặc SECRET_KEY đã đổi)."""
    if not member or not str(plain or ""):
        return
    if member_password_plain(member) == str(plain):
        return
    set_member_password(member, plain)
    try:
        save_json_github(MEMBERS_FILE, data, "members.json", "Remember student password for ADMIN")
    except Exception:
        pass

def access_data():
    d=load_json(ACCESS_FILE, {"default":"FREE","lessons":{}}); d.setdefault('default','FREE'); d.setdefault('lessons',{}); return d

def _admin_member_record():
    u = str(session.get('username') or ADMIN_USER or 'ADMIN').strip().casefold()
    found = next((m for m in members_data().get('members', []) if str(m.get('username') or '').strip().casefold() == u), None)
    if found:
        return found
    return {'username': ADMIN_USER or 'ADMIN', 'name': 'ADMIN', 'account_type': 'ADMIN', 'status': 'ON', 'class': ''}

def member_current():
    role = session.get('role')
    if role == 'admin':
        return _admin_member_record()
    if role != 'member':
        return None
    u=str(session.get('username') or '').strip().casefold()
    return next((m for m in members_data().get('members',[]) if str(m.get('username') or '').strip().casefold()==u and str(m.get('status','ON')).upper()=='ON'),None)
def admin_current():return session.get('role')=='admin'
def account_type_of(m):
    s=str((m or {}).get('account_type','FREE')).strip().upper().replace('.','').replace('-','')
    return {'SVIP':'SVIP','VIP':'VIP','ADMIN':'ADMIN'}.get(s,'FREE')
def is_admin_member(m):
    if not m:
        return False
    if account_type_of(m) == 'ADMIN':
        return True
    u = str(m.get('username') or '').strip()
    return bool(u) and u.casefold() == str(ADMIN_USER or 'ADMIN').casefold()
def has_full_bank_access(m=None):
    """ADMIN (phiên /admin hoặc tài khoản ADMIN) xem toàn bộ bài, mọi khối, VIP lẫn FREE."""
    try:
        if session.get('role') == 'admin':
            return True
    except Exception:
        pass
    return is_admin_member(m if m is not None else member_current())
def can_manage_bank():
    """ADMIN đăng nhập /admin, hoặc thành viên quyền ADMIN / username ADMIN."""
    return has_full_bank_access()
def is_vip(m):return account_type_of(m) in {'VIP','SVIP','ADMIN'}
def lesson_level(path):
    d=access_data(); return str(d['lessons'].get(path,d['default'])).upper()
def can_access(m,path):
    if has_full_bank_access(m if m is not None else None):
        return True
    if is_admin_member(m):
        return True
    if not m:return False
    try:
        import membership as _pkg
        return _pkg.can_access_path(m, path)
    except Exception:
        typ=account_type_of(m)
        if typ in {'SVIP','VIP'}:return True
        return lesson_level(path)=='FREE'

def can_view(m, path):
    """Xem đề: khách xem bài FREE; thành viên theo gói đã duyệt."""
    if has_full_bank_access(m if m is not None else None) or is_admin_member(m):
        return True
    if m:
        try:
            import membership as _pkg
            return _pkg.can_access_path(m, path)
        except Exception:
            return can_access(m, path)
    return str(lesson_level(path) or 'FREE').upper() != 'VIP'

def is_logged_in():
    return bool(member_current())

def safe_next_url(raw=None):
    u = str(raw if raw is not None else (request.values.get('next') or '')).strip()
    if not u.startswith('/') or u.startswith('//') or '\\' in u:
        return '/member'
    if not (u == '/member' or u.startswith('/member/') or u.startswith('/practice/')):
        return '/member'
    return u[:500]

def login_url(next_path=None):
    nxt = safe_next_url(next_path)
    if nxt == '/member':
        return '/member/login'
    return '/member/login?next=' + urllib.parse.quote(nxt, safe='')

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

def lesson_folder(path):
    p = str(path or "").replace("\\", "/").rstrip("/")
    if p.lower().endswith(".tex"):
        return p.rsplit("/", 1)[0]
    return p


COMPANION_TEX = {"lt.tex", "pp.tex"}


def is_bank_question_tex(path):
    """de.tex / dang-*.tex — không tính lý thuyết, dạng mẫu, file lệnh."""
    p = str(path or "").replace("\\", "/")
    if not p.lower().endswith(".tex"):
        return False
    parts = p.split("/")
    if "_lenh" in parts:
        return False
    name = parts[-1].lower()
    return name not in COMPANION_TEX


def _tex_name_key(path):
    name = str(path or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name == "de.tex":
        return (0, name)
    if name == "update.tex":
        return (1, name)
    return (2, name)


def lesson_tex_paths(path):
    """Mọi file .tex cùng thư mục bài (de / update / dang-...)."""
    folder = lesson_folder(path)
    found = []
    for x in index_data().get("lessons") or []:
        p = str(x.get("path") or x.get("file") or "").replace("\\", "/")
        if is_bank_question_tex(p) and lesson_folder(p) == folder:
            found.append(p)
    p0 = str(path or "").replace("\\", "/")
    if is_bank_question_tex(p0) and p0 not in found:
        found.append(p0)
    try:
        dummy = folder + "/de.tex"
        _, local = _safe_repo_file(dummy)
        parent = local.parent
        if parent.is_dir():
            for f in sorted(parent.glob("*.tex")):
                rel = str(f.relative_to(ROOT)).replace("\\", "/")
                if is_bank_question_tex(rel) and rel not in found:
                    found.append(rel)
    except Exception:
        pass
    return sorted(set(found), key=_tex_name_key)


def lesson_card_title(folder, arr):
    name = str(folder or "").replace("\\", "/").rsplit("/", 1)[-1]
    for x in arr or []:
        p = str(x.get("path") or x.get("file") or "").replace("\\", "/")
        if p.endswith("/de.tex"):
            t = str(x.get("BaiHoc") or x.get("De") or "").strip()
            if t:
                return t.split(" · ")[0].strip() or name
    for x in arr or []:
        t = str(x.get("BaiHoc") or x.get("De") or "").strip()
        if t:
            return t.split(" · ")[0].strip() or name
    return name


def merge_catalog_lessons(items):
    """Gộp mọi .tex cùng thư mục thành một thẻ bài."""
    buckets = {}
    for x in items or []:
        if not isinstance(x, dict):
            continue
        p = str(x.get("path") or x.get("file") or "").replace("\\", "/")
        if not p or not is_bank_question_tex(p):
            continue
        buckets.setdefault(lesson_folder(p), []).append(x)
    out = []
    for folder, arr in buckets.items():
        arr = sorted(arr, key=lambda z: _tex_name_key(str(z.get("path") or z.get("file") or "")))
        canon = dict(arr[0])
        path = str(canon.get("path") or canon.get("file") or "")
        dang, kinds, n = {}, {}, 0
        for x in arr:
            n += int(x.get("questions") or x.get("count") or 0)
            for k, v in (x.get("dang") or {}).items():
                name = str(k)
                dang[name] = dang.get(name, 0) + int(v or 0)
            for dname, bucket in (x.get("dang_kinds") or {}).items():
                dst = kinds.setdefault(str(dname), {"TN": 0, "DS": 0, "TLN": 0, "TL": 0})
                if isinstance(bucket, dict):
                    for kk, vv in bucket.items():
                        dst[kk] = dst.get(kk, 0) + int(vv or 0)
        canon["path"] = path
        canon["file"] = path
        canon["id"] = path
        title = lesson_card_title(folder, arr)
        canon["BaiHoc"] = title
        canon["De"] = title
        canon["questions"] = n
        canon["count"] = n
        canon["dang"] = dang
        canon["dang_kinds"] = kinds
        out.append(canon)
    return out


def chapter_lessons_for(path, items=None):
    """Các bài đã gộp file, cùng môn/lớp/chương với path."""
    if items is None:
        raw = [
            x
            for x in (index_data().get("lessons") or [])
            if isinstance(x, dict) and str(x.get("path") or x.get("file") or "").startswith("ngan-hang/")
        ]
        items = merge_catalog_lessons(raw)
    folder = lesson_folder(path)
    cur = next((x for x in items if lesson_folder(str(x.get("path") or x.get("file") or "")) == folder), None)
    if not cur:
        return [], None
    key = (str(cur.get("Mon") or ""), str(cur.get("Lop") or ""), str(cur.get("Chuong") or ""))
    sibs = [
        x
        for x in items
        if (str(x.get("Mon") or ""), str(x.get("Lop") or ""), str(x.get("Chuong") or "")) == key
    ]
    sibs.sort(key=lambda z: str(z.get("BaiHoc") or z.get("De") or ""))
    return sibs, cur


def chapter_nav_html(path):
    sibs, cur = chapter_lessons_for(path)
    if not sibs:
        return ""
    mon = html.escape(str((cur or {}).get("Mon") or ""))
    lop = html.escape(str((cur or {}).get("Lop") or ""))
    chuong = html.escape(str((cur or {}).get("Chuong") or ""))
    cur_folder = lesson_folder(path)
    tabs = []
    for x in sibs:
        p = str(x.get("path") or x.get("file") or "")
        href = urllib.parse.quote(p, safe="")
        title = html.escape(str(x.get("BaiHoc") or x.get("De") or ""))
        n = int(x.get("questions") or x.get("count") or 0)
        cls = "baitab on" if lesson_folder(p) == cur_folder else "baitab"
        tabs.append(f"<a class='{cls}' href='/member/select?path={href}'>{title}<span class='tag'>{n}</span></a>")
    return (
        f"<div class='chaptree'><div class='titlebar'>{mon} · Lớp {lop} · {chuong}</div>"
        "<p class='muted' style='margin:8px 0 6px'>Cùng một chương: mỗi bài một lần. Dạng nằm trong bài, không liệt kê từng file .tex.</p>"
        f"<div class='bairow'>{''.join(tabs)}</div></div>"
        "<style>.chaptree{margin-bottom:14px}.bairow{display:flex;flex-wrap:wrap;gap:8px}"
        ".baitab{display:inline-flex;align-items:center;gap:6px;max-width:100%;padding:8px 10px;border:1px solid #c9d8e8;border-radius:9px;background:#fff;text-decoration:none;color:#173a5e;font-weight:700;font-size:13px;line-height:1.35}"
        ".baitab.on{background:#145bb0;color:#fff;border-color:#145bb0}.baitab.on .tag{background:#fff;color:#145bb0}</style>"
    )


def catalog_items_for(m=None):
    raw = [
        x
        for x in (index_data().get("lessons") or [])
        if isinstance(x, dict) and str(x.get("path") or x.get("file") or "").startswith("ngan-hang/")
    ]
    items = merge_catalog_lessons(raw)
    if m:
        items = [x for x in items if can_view(m, str(x.get("path") or x.get("file") or ""))]
    else:
        items = [x for x in items if str(lesson_level(str(x.get("path") or x.get("file") or ""))).upper() != "VIP"]
    return items


def lesson_drawer_html(m=None, current_path="", current_dang=""):
    items = catalog_items_for(m)
    cur_folder = lesson_folder(current_path) if current_path else ""
    current_dang = str(current_dang or "").strip()
    guest = not m
    tree = {}
    for x in items:
        mon = str(x.get("Mon") or "Khác").strip() or "Khác"
        lop = str(x.get("Lop") or "?").strip() or "?"
        chuong = str(x.get("Chuong") or "Chưa xác định").strip() or "Chưa xác định"
        tree.setdefault(mon, {}).setdefault(lop, {}).setdefault(chuong, []).append(x)

    def lop_key(s):
        return (0, int(s)) if str(s).isdigit() else (1, str(s))

    blocks = []
    for mon in sorted(tree):
        lop_bits = []
        open_mon = False
        for lop in sorted(tree[mon], key=lop_key):
            chuong_bits = []
            open_lop = False
            for chuong in sorted(tree[mon][lop]):
                bais = []
                open_ch = False
                arr = sorted(tree[mon][lop][chuong], key=lambda z: str(z.get("BaiHoc") or z.get("De") or ""))
                for x in arr:
                    p = str(x.get("path") or x.get("file") or "")
                    on = bool(cur_folder) and lesson_folder(p) == cur_folder
                    if on:
                        open_ch = True
                    n = int(x.get("questions") or x.get("count") or 0)
                    title = html.escape(str(x.get("BaiHoc") or x.get("De") or "Bài"))
                    dang_map = x.get("dang") or {}
                    pairs = []
                    for k, v in dang_map.items():
                        try:
                            cnt = int(v or 0)
                        except (TypeError, ValueError):
                            continue
                        if cnt <= 0:
                            continue
                        pairs.append((str(k), cnt))
                    pairs.sort(key=lambda t: t[0])
                    dang_kinds = x.get("dang_kinds") or {}
                    all_kinds = {k: 0 for k in KIND_ORDER}
                    for bucket in dang_kinds.values():
                        if not isinstance(bucket, dict):
                            continue
                        for kk, vv in bucket.items():
                            if kk in all_kinds:
                                try:
                                    all_kinds[kk] += int(vv or 0)
                                except (TypeError, ValueError):
                                    pass
                    dlinks = []
                    try:
                        import lythuyet as _lt
                        admin_see = (not guest) and base.has_full_bank_access()
                        for kind, meta in _lt.TRACKS.items():
                            if not _lt.companion_visible(p, kind, for_admin=admin_see):
                                continue
                            href = meta["route"] + "?path=" + urllib.parse.quote(p, safe="")
                            if guest:
                                href = login_url(href)
                            on_k = on and str(request.path or "").rstrip("/") == meta["route"]
                            dlinks.append(
                                f"<a class='drawdang{' on' if on_k else ''}' href='{html.escape(href, quote=True)}'><span class='drawname'>{html.escape(meta['icon'] + ' ' + meta['label'])}</span><span class='drawn'></span></a>"
                            )
                    except Exception:
                        pass
                    dlinks.append(
                        f"<a class='drawdang{' on' if on and not current_dang else ''}' href='{html.escape(_go_kind_href(p, '', '', guest), quote=True)}'><span class='drawname'>Cả bài</span><span class='drawn'>{n}</span>{kind_chips_html(all_kinds)}</a>"
                    )
                    for i, (dname, cnt) in enumerate(pairs, 1):
                        short = dname if len(dname) <= 48 else dname[:47] + "…"
                        on_d = on and current_dang == dname
                        dlinks.append(
                            f"<a class='drawdang{' on' if on_d else ''}' href='{html.escape(_go_kind_href(p, dname, '', guest), quote=True)}' title='{html.escape(dname, quote=True)}'><span class='drawname'>{i}. {html.escape(short)}</span><span class='drawn'>{cnt}</span>{kind_chips_html(dang_kinds.get(dname))}</a>"
                        )
                    bais.append(
                        f"<details class='drawbaiwrap'{' open' if on else ''}>"
                        f"<summary class='drawbai{' on' if on else ''}'><span class='drawname'>{title}</span><span class='drawn'>{n}</span></summary>"
                        f"<div class='drawdangs'>{''.join(dlinks)}</div></details>"
                    )
                if open_ch:
                    open_lop = True
                chuong_bits.append(
                    f"<details class='drawchuong'{' open' if open_ch else ''}>"
                    f"<summary>{html.escape(chuong)}</summary>"
                    f"<div class='drawbais'>{''.join(bais)}</div></details>"
                )
            if open_lop:
                open_mon = True
            lop_bits.append(
                f"<details class='drawlop'{' open' if open_lop else ''}>"
                f"<summary>Lớp {html.escape(lop)}</summary>"
                f"<div class='drawnest'>{''.join(chuong_bits)}</div></details>"
            )
        blocks.append(
            f"<details class='drawmon'{' open' if open_mon or len(tree)==1 else ''}>"
            f"<summary>{html.escape(mon)}</summary>"
            f"<div class='drawnest'>{''.join(lop_bits)}</div></details>"
        )
    inner = "".join(blocks) or "<p class='muted' style='padding:12px'>Chưa có bài.</p>"
    return (
        "<div id='ldvlDrawer' class='drawer' aria-hidden='true'>"
        "<div class='drawer-back' id='ldvlDrawerBack'></div>"
        "<aside class='drawer-panel' role='dialog' aria-label='Chọn bài'>"
        "<div class='drawer-head'><b>📚 Chọn bài</b>"
        "<button type='button' class='btn' id='ldvlDrawerClose'>✕</button></div>"
        "<p class='drawer-hint'>Bấm lớp → chương → bài → dạng. Dạng / bài đang làm được tô.</p>"
        f"<div class='drawer-tree'>{inner}</div></aside></div>"
    )


def admin_tex_select_html(path):
    files = lesson_tex_paths(path)
    if len(files) <= 1:
        return ""
    cur = str(path or "").replace("\\", "/")
    opts = []
    for fp in files:
        name = fp.rsplit("/", 1)[-1]
        sel = " selected" if fp.replace("\\", "/") == cur else ""
        opts.append(f"<option value='{html.escape(fp, quote=True)}'{sel}>{html.escape(name)}</option>")
    return (
        "<div class='notice' style='margin-bottom:10px'><b>ADMIN · file TEX đang sửa</b> "
        "<span class='muted'>(chỉ khi gán ID / AI / tách / gom — học viên không thấy danh sách file)</span><br>"
        "<select id='adminTex' style='margin-top:6px;max-width:min(100%,460px);padding:7px 8px'>"
        + "".join(opts)
        + "</select></div>"
        "<script>(function(){var s=document.getElementById('adminTex');if(s)s.addEventListener('change',function(){location.href='/member/select?path='+encodeURIComponent(this.value)})})()</script>"
    )


def theory_catalog_html(path, guest=False):
    """Dòng + nút Lý thuyết / Dạng mẫu trên mục lục (khi có lt.tex / pp.tex)."""
    rows, btns = [], []
    try:
        import lythuyet as _lt
    except Exception:
        return "", ""
    admin_see = (not guest) and has_full_bank_access()
    for kind, meta in _lt.TRACKS.items():
        if not _lt.companion_visible(path, kind, for_admin=admin_see):
            continue
        href = meta["route"] + "?path=" + urllib.parse.quote(str(path or ""), safe="")
        if guest:
            href = login_url(href)
        safe = html.escape(href, quote=True)
        cls = "ltrow" if kind == "lt" else "pprow"
        btncls = "ltbtn" if kind == "lt" else "ppbtn"
        label = html.escape(meta["icon"] + " " + meta["label"])
        rows.append(
            f"<a class='dangrow danglink {cls}' href='{safe}'>"
            f"<span class='dangname'>{label}</span>"
            f"<span class='dangkinds'><span class='kind ktotal'>Đọc</span></span></a>"
        )
        btns.append(f"<a class='btn {btncls}' href='{safe}'>{label}</a>")
    return "".join(rows), "".join(btns)


def catalog_chapter_html(mon, lop, chuong, arr, dang_link=True):
    """Một chương: danh sách bài xổ dạng, không tách thẻ theo file."""
    bits = []
    guest = not member_current()
    for x in sorted(arr, key=lambda z: str(z.get("BaiHoc") or z.get("De") or "")):
        path = str(x.get("path") or x.get("file") or "")
        title = str(x.get("BaiHoc") or x.get("De") or path.rsplit("/", 1)[-1])
        cnt = int(x.get("questions") or x.get("count") or 0)
        href = urllib.parse.quote(path, safe="")
        dangs = x.get("dang") or {}
        kinds = x.get("dang_kinds") or {}
        lt_row, lt_btn = theory_catalog_html(path, guest=guest)
        dh = lt_row
        if dang_link:
            dh += "".join(
                dang_link_html(path, k, v, kinds.get(str(k)), n=i)
                for i, (k, v) in enumerate(
                    ((k, v) for k, v in dangs.items() if str(v).isdigit() or isinstance(v, (int, float))),
                    1,
                )
            )
        bits.append(
            "<div class='baiacc'><div class='baiacc-top'>"
            f"<details><summary><b>{html.escape(title)}</b> <span class='tag'>{cnt} câu</span></summary>"
            f"<div class='dang'><b>📌 Dạng trong bài này</b>{dh or '<div class=muted>Chưa có dạng</div>'}</div>"
            "</details>"
            f"<div class='baiacc-btns'>{lt_btn}<a class='btn primary' href='/member/select?path={href}'>Mở bài</a></div></div></div>"
        )
    return (
        f"<section class='chapterbox' style='margin-top:10px'><div class='titlebar'>{html.escape(str(mon))} · Lớp {html.escape(str(lop))} · {html.escape(str(chuong))}</div>"
        "<div class='chlist' style='display:grid;gap:8px;margin-top:8px;padding:8px;border:1px solid #d8e3ee;border-radius:10px;background:#f7fbff'>"
        + "".join(bits)
        + "</div></section>"
        "<style>.baiacc-top{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start}.baiacc-top details{flex:1 1 min(100%,36rem);min-width:0}"
        ".baiacc-top summary{cursor:pointer;padding:8px 4px}.baiacc-btns{display:flex;flex-direction:row;flex-wrap:wrap;gap:6px;flex:1 1 12rem;margin-top:6px}"
        ".ltrow{background:#f5f3ff;border:1px solid #ddd6fe;border-radius:10px;padding:8px 10px;margin:8px 0 6px}"
        ".ltrow .dangname{font-weight:700;color:#5b21b6}.ltbtn{background:#f5f3ff;border-color:#c4b5fd;color:#5b21b6}"
        ".pprow{background:#ecfeff;border:1px solid #a5f3fc;border-radius:10px;padding:8px 10px;margin:0 0 6px}"
        ".pprow .dangname{font-weight:700;color:#0e7490}.ppbtn{background:#ecfeff;border-color:#67e8f9;color:#0e7490}</style>"
    )


def parse_lesson_questions(path):
    """Mọi câu trong các .tex cùng bài; idx không trùng giữa file."""
    out = []
    n = 0
    for fp in lesson_tex_paths(path):
        try:
            _, tex = read_tex(fp)
        except Exception:
            continue
        for q in parse_questions(tex):
            q = dict(q)
            q["src"] = fp
            try:
                q["file_idx"] = int(q.get("idx") or 0)
            except (TypeError, ValueError):
                q["file_idx"] = 0
            q["idx"] = n
            n += 1
            out.append(q)
    return out


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

def split_true_mark(s):
    """\\True có thể dính khoảng trắng: { \\True $99$ ... } — web vẫn nhận đáp án đúng."""
    t = str(s or '').strip()
    ok = bool(re.match(r'^\\True\b', t, re.I))
    if ok:
        t = re.sub(r'^\\True\b\s*', '', t, flags=re.I)
    return t, ok

def peel_tex_breaks(s):
    """TeX: \\ cuối dòng là nối dòng, không in ra web."""
    s = re.sub(r'\\\s*\r?\n', ' ', str(s or ''))
    s = re.sub(r'\\\s*$', '', s)
    return s

def solution_of(block):
    m=re.search(r'\\loigiai\s*\{',block,re.I)
    if not m:return ''
    v,_=get_braced(block,m.end()-1);return v or ''

def strip_loigiai(s):
    """Gỡ \\loigiai{...} khỏi đề — lời giải chỉ nằm ở trường solution."""
    s=s or ''
    s=re.sub(r'\\begin\s*\{\s*loigiai\s*\}.*?\\end\s*\{\s*loigiai\s*\}','',s,flags=re.I|re.S)
    while True:
        m=re.search(r'\\loigiai\s*\{',s,re.I)
        if not m:break
        val,end=get_braced(s,m.end()-1)
        if val is None:
            s=s[:m.start()];break
        s=s[:m.start()]+s[end:]
    return re.sub(r'\\loigiai\b','',s,flags=re.I)

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

def dang_link_html(path, dang, total, kinds=None, n=0):
    """Một dòng dạng bài trên mục lục: số thứ tự + tên thường màu xanh + 4 loại."""
    href=urllib.parse.quote(str(path or ''), safe='')
    name=str(dang or 'Chưa phân dạng')
    s=kinds if isinstance(kinds, dict) else {}
    tn=int(s.get('TN') or 0); ds=int(s.get('DS') or 0); tln=int(s.get('TLN') or 0); tl=int(s.get('TL') or 0)
    tot=int(total or 0) or (tn+ds+tln+tl)
    try: seq=int(n or 0)
    except Exception: seq=0
    no=f"<span class='dangno'>{seq}.</span>" if seq else ""
    return (
        f"<a class='dangrow danglink' data-dang='{html.escape(name, quote=True)}' href='/member/dang?path={href}&dang={urllib.parse.quote(name)}'>"
        f"<span class='dangname'>{no}{html.escape(name)}</span>"
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
    s=strip_loigiai(peel_immini(s or ''))
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
        stem=re.split(r'\\choiceTF\b|\\choice\b|\\shortans\b|\\loigiai\b',b,1,flags=re.I)[0]
        stem=peel_tex_breaks(strip_loigiai(stem))
        q={'idx':idx,'stt':idx+1,'id':qid,'cau':int(heads[-1].group(1)) if heads else idx+1,'line':tex[:m.start()].count('\n')+1,'dang':dang_for_pos(tex,m.start()),'level':level_of(b),'kind':kind,'nguon':nguon,'text':clean_latex_web(stem),'solution':clean_latex_web(solution_of(b)),'raw':b}
        if kind=='TN':
            opts=[]
            for x in command_args(b,'\\choice')[:4]:
                t,ok=split_true_mark(x)
                opts.append({'text':clean_latex_web(t),'correct':ok})
            q['options']=opts
        elif kind=='DS':
            stmts=[]
            for x in command_args(b,'\\choiceTF'):
                t,ok=split_true_mark(x)
                stmts.append({'text':clean_latex_web(t),'correct':ok})
            q['statements']=stmts
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
KIND_CHIP_LABS = (('TN', 'TN'), ('DS', 'ĐS'), ('TLN', 'TLN'), ('TL', 'TL'))
KIND_AIM = {'TN': 9, 'DS': 2, 'TLN': 3, 'TL': 4}
KIND_MAX = {'TN': 18, 'DS': 4, 'TLN': 6, 'TL': 8}

def kind_chips_html(counts):
    """Báo nhỏ 4 loại câu trên một dạng (TN / ĐS / TLN / TL)."""
    s = counts if isinstance(counts, dict) else {}
    bits = []
    for k, lab in KIND_CHIP_LABS:
        try:
            n = int(s.get(k) or 0)
        except (TypeError, ValueError):
            n = 0
        bits.append(f"<span class='dk{' z' if n==0 else ''}'>{html.escape(lab)} {n}</span>")
    return "<span class='dkinds'>" + ''.join(bits) + "</span>"

def sort_questions_by_kind(questions):
    """TN → Đúng/Sai → Trả lời ngắn → Tự luận. Trong mỗi loại giữ idx tăng dần."""
    rank = {k: i for i, k in enumerate(KIND_ORDER)}
    def key(q):
        k = str((q or {}).get('kind') or 'TL')
        try:
            idx = int((q or {}).get('idx') or 0)
        except (TypeError, ValueError):
            idx = 0
        return (rank.get(k, 99), idx)
    return sorted(list(questions or []), key=key)

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

KIND_TABS = (
    ('', 'Tất cả', 'Tất cả loại'),
    ('TN', 'TN', 'Chỉ trắc nghiệm'),
    ('DS', 'ĐS', 'Chỉ đúng/sai'),
    ('TLN', 'TLN', 'Chỉ trả lời ngắn'),
    ('TL', 'TL', 'Chỉ tự luận'),
)

def norm_kind_tab(kind):
    k = str(kind or '').strip().upper()
    return k if k in KIND_ORDER else ''

def load_lesson_questions(path):
    qs = parse_lesson_questions(path)
    if not qs:
        _, tex = read_tex(path)
        qs = parse_questions(tex)
    return qs

def questions_in_scope(qs, dang=''):
    dang = str(dang or '').strip()
    if not dang:
        return list(qs or [])
    hit = [q for q in (qs or []) if str(q.get('dang') or '').strip() == dang]
    if not hit and dang == 'Chưa phân dạng':
        hit = [q for q in (qs or []) if not str(q.get('dang') or '').strip()]
    return hit

def kind_counts_for(qs):
    c = {'': 0, 'TN': 0, 'DS': 0, 'TLN': 0, 'TL': 0}
    for q in qs or []:
        k = str(q.get('kind') or 'TL')
        if k not in KIND_ORDER:
            k = 'TL'
        c[k] = c.get(k, 0) + 1
        c[''] += 1
    return c

def ids_of_kind(qs, kind=''):
    kind = norm_kind_tab(kind)
    ids = []
    for q in qs or []:
        if kind and str(q.get('kind') or '') != kind:
            continue
        try:
            ids.append(int(q['idx']))
        except (TypeError, ValueError, KeyError):
            continue
    return sort_ids_by_kind(qs, ids, shuffle_within=False)

def kind_tabs_html(path, dang='', current='', counts=None, guest=False):
    counts = counts or {'': 0, 'TN': 0, 'DS': 0, 'TLN': 0, 'TL': 0}
    current = norm_kind_tab(current)
    base = '/member/go-kind?path=' + urllib.parse.quote(str(path or ''), safe='')
    if dang:
        base += '&dang=' + urllib.parse.quote(str(dang), safe='')
    bits = []
    for k, lab, tip in KIND_TABS:
        n = int(counts.get(k, 0) if k else counts.get('', 0))
        label = f'{lab} · {n}'
        on = ' on' if current == k else ''
        title = tip if n else 'Không có câu loại này'
        if n <= 0:
            bits.append(f"<span class='ktab{on} off' title='{html.escape(title, quote=True)}'>{html.escape(label)}</span>")
            continue
        href = base + '&kind=' + urllib.parse.quote(k, safe='')
        if guest:
            href = login_url(href)
        bits.append(f"<a class='ktab{on}' href='{html.escape(href, quote=True)}' title='{html.escape(tip, quote=True)}'>{html.escape(label)}</a>")
    return "<nav class='kindtabs' aria-label='Loại câu'>" + ''.join(bits) + "</nav>"

def _dang_name(q):
    return str((q or {}).get('dang') or '').strip() or 'Chưa phân dạng'

def dang_names_of(qs):
    names, counts = [], {}
    seen = set()
    for q in qs or []:
        d = _dang_name(q)
        if d not in seen:
            seen.add(d)
            names.append(d)
        counts[d] = counts.get(d, 0) + 1
    return names, counts

def dang_kind_counts_of(qs):
    per, allc = {}, {k: 0 for k in KIND_ORDER}
    for q in qs or []:
        d = _dang_name(q)
        k = str(q.get('kind') or 'TL')
        if k not in KIND_ORDER:
            k = 'TL'
        b = per.setdefault(d, {x: 0 for x in KIND_ORDER})
        b[k] = b.get(k, 0) + 1
        allc[k] = allc.get(k, 0) + 1
    return per, allc

def dang_tex_anchor(path, dang, qs=None):
    """File + dòng \\dangbt{tên dạng} để ADMIN mở thẳng TEX của dạng."""
    dang = str(dang or '').strip()
    files, seen = [], set()
    for fp in (lesson_tex_paths(path) or [path]):
        fp = str(fp or '').replace('\\', '/')
        if fp and fp not in seen:
            seen.add(fp)
            files.append(fp)
    if dang:
        for fp in files:
            try:
                _, tex = read_tex(fp)
            except Exception:
                continue
            for m in DANG_RE.finditer(tex or ''):
                if (m.group(1) or '').strip() == dang:
                    return fp, tex[:m.start()].count('\n') + 1
        if qs is None:
            try:
                qs = load_lesson_questions(path)
            except Exception:
                qs = []
        scoped = questions_in_scope(qs, dang)
        if scoped:
            q = scoped[0]
            try:
                line = int(q.get('line') or 0)
            except (TypeError, ValueError):
                line = 0
            return str(q.get('src') or path or '').replace('\\', '/'), line
    p0 = str(path or '').replace('\\', '/')
    return p0, 1

def kind_gap_heuristic(counts):
    """Số câu nên thêm để đạt mức cố gắng; không thêm khi đã chạm trần."""
    add = {}
    for k in KIND_ORDER:
        try:
            n = int((counts or {}).get(k) or 0)
        except (TypeError, ValueError):
            n = 0
        if n >= int(KIND_MAX[k]):
            add[k] = 0
        else:
            add[k] = max(0, int(KIND_AIM[k]) - n)
    return add

def kind_over_max(counts):
    over = {}
    for k in KIND_ORDER:
        try:
            n = int((counts or {}).get(k) or 0)
        except (TypeError, ValueError):
            n = 0
        over[k] = max(0, n - int(KIND_MAX[k]))
    return over

def kind_quota_line(counts):
    labs = dict(KIND_CHIP_LABS)
    add = kind_gap_heuristic(counts)
    over = kind_over_max(counts)
    have = ' · '.join(f"{lab} {int((counts or {}).get(k) or 0)}/{KIND_AIM[k]}" for k, lab in KIND_CHIP_LABS)
    miss = ' · '.join(f"{labs[k]} +{add[k]}" for k in KIND_ORDER if add.get(k))
    extra = ' · '.join(f"{labs[k]} thừa {over[k]}" for k in KIND_ORDER if over.get(k))
    bits = [have]
    if miss:
        bits.append('cần thêm ' + miss)
    if extra:
        bits.append('vượt trần (nên bớt câu tương tự): ' + extra)
    if not miss and not extra:
        bits.append('đã đạt mức cố gắng, chưa vượt trần')
    return ' · '.join(bits)

def lesson_catalog_of(path):
    _sibs, cur = chapter_lessons_for(path)
    if cur:
        return cur
    folder = Path(str(path or '').replace('\\', '/')).as_posix()
    parts = [p for p in folder.split('/') if p]
    # ngan-hang / Mon / Lớp x / Chương / Bài / de.tex
    mon = parts[1] if len(parts) > 1 else ''
    lop = parts[2] if len(parts) > 2 else ''
    chuong = parts[3] if len(parts) > 3 else ''
    bai = parts[4] if len(parts) > 4 else Path(folder).parent.name
    return {'Mon': mon, 'Lop': lop, 'Chuong': chuong, 'BaiHoc': bai, 'path': path}

def notebooklm_prompt_text(path, qs, dang=''):
    """Prompt dán vào NotebookLM: chép bài KNTT, đúng LaTeX ngân hàng, đúng chỗ đang thiếu."""
    meta = lesson_catalog_of(path) or {}
    mon = str(meta.get('Mon') or '').strip() or 'Toán / Vật lý'
    lop = str(meta.get('Lop') or '').strip()
    if lop and not lop.lower().startswith('lớp'):
        lop = 'Lớp ' + lop
    chuong = str(meta.get('Chuong') or '').strip()
    bai = str(meta.get('BaiHoc') or meta.get('De') or '').strip()
    bm = re.search(r'Bài\s*(\d+(?:\.\d+)?)', bai, re.I)
    bai_so = bm.group(1) if bm else ''
    dang = str(dang or '').strip()
    per, _allc = dang_kind_counts_of(qs)
    names, _cnts = dang_names_of(qs)
    focus = [dang] if dang else list(names)
    if not focus:
        focus = ['Chưa phân dạng']
    labs = dict(KIND_CHIP_LABS)
    kind_long = {'TN': 'trắc nghiệm 4 phương án', 'DS': 'đúng/sai 4 mệnh đề', 'TLN': 'trả lời ngắn', 'TL': 'tự luận'}
    need_lines, have_lines, skip_lines = [], [], []
    for name in focus:
        counts = {k: int((per.get(name) or {}).get(k) or 0) for k in KIND_ORDER}
        add = kind_gap_heuristic(counts)
        over = kind_over_max(counts)
        have_lines.append(
            '- Dạng «' + name + '»: đang có ' + ', '.join(f"{labs[k]} {counts[k]}" for k in KIND_ORDER)
            + f' (mục tiêu {KIND_AIM["TN"]} TN / {KIND_AIM["DS"]} ĐS / {KIND_AIM["TLN"]} TLN / {KIND_AIM["TL"]} TL; trần {KIND_MAX["TN"]}/{KIND_MAX["DS"]}/{KIND_MAX["TLN"]}/{KIND_MAX["TL"]}).'
        )
        bits = [f"{kind_long[k]}: cần thêm {add[k]} câu (không vượt trần {KIND_MAX[k]})" for k in KIND_ORDER if add.get(k)]
        if bits:
            need_lines.append('- Dạng «' + name + '» — ' + '; '.join(bits) + '.')
        extra = [f"{labs[k]} đang thừa {over[k]} so với trần" for k in KIND_ORDER if over.get(k)]
        if extra:
            skip_lines.append('- Dạng «' + name + '»: ' + '; '.join(extra) + ' — KHÔNG chép thêm loại đó.')
        scoped = questions_in_scope(qs, name) if name else []
        stems = []
        for q in scoped[:8]:
            t = re.sub(r'\s+', ' ', str(q.get('text') or '')).strip()
            t = re.sub(r'<[^>]+>', '', t)
            if t:
                stems.append('  · [' + str(q.get('kind') or '') + '] ' + (t[:110] + '…' if len(t) > 110 else t))
        if stems:
            have_lines.append('  Đã có (cấm chép trùng / cùng ý):\n' + '\n'.join(stems))
    if not need_lines:
        need_lines.append('- Mọi dạng đang xét đã đạt mức cố gắng. Chỉ chép câu SBT/SGK KHÁC Ý hẳn, không vượt trần từng loại.')
    sach = 'bộ sách giáo khoa và sách bài tập Kết nối tri thức với cuộc sống'
    where = ', '.join(x for x in (mon, lop, chuong, bai) if x)
    return '\n'.join([
        'Bạn là trợ lý soạn ngân hàng câu hỏi. Chỉ dùng nội dung trong tài liệu tôi đã tải lên NotebookLM (SGK/SBT ' + sach + ').',
        'Không bịa đề, không lấy sách Cánh Diều / Chân trời / KNTT năm khác nếu không có trong nguồn.',
        '',
        'BÀI CẦN BỔ SUNG',
        '- Môn: ' + mon,
        '- Khối: ' + (lop or '(ghi đúng lớp trong sách)'),
        '- Chương: ' + (chuong or '(đúng tên chương SGK KNTT)'),
        '- Bài học: ' + (bai or '(đúng số bài SGK)'),
        ('- Số bài SGK/SBT cần mở: Bài ' + bai_so + ' (và bài luyện tập / bài tập cuối bài tương ứng trong SBT).') if bai_so else '- Mở đúng bài học trùng tên ở SGK rồi sang SBT cùng bài.',
        '- Sách: ' + sach + ' — môn ' + mon + (', ' + lop if lop else '') + '.',
        '- Nơi ghi trên đề: ' + where + '.',
        '',
        'CẦN BỔ SUNG (theo dạng đang thiếu trên web)',
        *need_lines,
        '',
        'HIỆN TRẠNG NGÂN HÀNG (để khỏi trùng)',
        *have_lines,
        *(['', 'KHÔNG THÊM (đã đầy/vượt trần)'] + skip_lines if skip_lines else []),
        '',
        'VIỆC CẦN LÀM',
        '1) Trong SGK + SBT KNTT, tìm bài tập đúng bài/lớp/chương trên, thuộc các dạng đã liệt kê.',
        '2) Chép nguyên đề (và lời giải/đáp án nếu sách có). Ghi rõ lấy từ SGK hay SBT, bài mấy, câu mấy.',
        '3) Mỗi câu một ý; bỏ biến thể cùng số liệu. Đủ mục tiêu thì dừng loại đó.',
        '4) Trả về ĐÚNG LaTeX ngân hàng dưới đây — không markdown, không lời dẫn dài.',
        '',
        'ĐỊNH DẠNG LATEX (bắt buộc)',
        'Trước mỗi câu: \\dangbt{Tên dạng} — dùng đúng tên dạng ở trên, không đặt tên mới trừ khi sách ra dạng khác hẳn.',
        'Khối câu: \\begin{ex} ... \\end{ex}',
        'Trong mỗi câu có \\nguon{SGK KNTT ' + mon + ' ' + (lop or '') + ' Bài ' + (bai_so or '…') + ' câu …} hoặc \\nguon{SBT KNTT … Bài … câu …}',
        'Công thức toán trong $...$. Có \\loigiai{...} (nếu sách không có lời giải thì giải ngắn đúng đáp án).',
        'Không bọc ```latex. Không % ID.',
        '',
        'Trắc nghiệm (TN):',
        '\\dangbt{Tên dạng}',
        '\\begin{ex}',
        'Đề...',
        '\\choice',
        '{A}',
        '{B}',
        '{\\True C đúng}',
        '{D}',
        '\\loigiai{...}',
        '\\nguon{SBT KNTT ...}',
        '\\end{ex}',
        '',
        'Đúng sai (ĐS) — đúng 4 mệnh đề:',
        '\\begin{ex}',
        'Đề...',
        '\\choiceTF',
        '{\\True mệnh đề đúng}',
        '{mệnh đề sai}',
        '{...}',
        '{...}',
        '\\loigiai{...}',
        '\\nguon{...}',
        '\\end{ex}',
        '',
        'Trả lời ngắn (TLN):',
        '\\begin{ex}',
        'Đề...',
        '\\shortans{đáp án}',
        '\\loigiai{...}',
        '\\nguon{...}',
        '\\end{ex}',
        '',
        'Tự luận (TL): không \\choice / \\choiceTF / \\shortans; có \\loigiai{...}.',
        '',
        'Nếu trong tài liệu NotebookLM không có SGK/SBT KNTT đúng môn-lớp-bài: trả lời một câu «Thiếu sách …» và không bịa đề.',
    ])

def admin_dang_bar_html(path, qs, dang=''):
    if not can_manage_bank():
        return ''
    per, allc = dang_kind_counts_of(qs)
    dang = str(dang or '').strip()
    counts = per.get(dang) if dang else allc
    counts = counts or {k: 0 for k in KIND_ORDER}
    src, line = dang_tex_anchor(path, dang, qs=qs)
    href = '/admin/edit?path=' + urllib.parse.quote(src, safe='')
    if line:
        href += '&line=' + str(int(line))
    missing = [lab for k, lab in KIND_CHIP_LABS if int(counts.get(k) or 0) == 0]
    over = kind_over_max(counts) if dang else {}
    over_labs = [lab for k, lab in KIND_CHIP_LABS if over.get(k)]
    if not dang:
        miss = 'Cả bài: soát từng dạng (không cộng chung các dạng).'
        heur_txt = 'Mỗi dạng cố gắng 9 TN / 2 ĐS / 3 TLN / 4 TL · trần 18 / 4 / 6 / 8.'
    elif over_labs:
        miss = 'Vượt trần: ' + ', '.join(over_labs) + ' — soát câu gần trùng rồi xóa bớt.'
        heur_txt = kind_quota_line(counts)
    elif missing:
        miss = 'Còn thiếu loại: ' + ', '.join(missing)
        heur_txt = kind_quota_line(counts)
    else:
        miss = 'Đã có đủ 4 loại.'
        heur_txt = kind_quota_line(counts)
    title = html.escape(dang or 'Cả bài')
    tex_lab = '✏️ TEX dạng này' if dang else '✏️ TEX cả bài'
    url_ph = 'Dán link đề — không cần chọn dạng, AI tự gán dạng'
    hint = 'Mỗi dạng cố gắng <b>9 TN · 2 ĐS · 3 TLN · 4 TL</b>, trần <b>18 · 4 · 6 · 8</b>. Nút Prompt NotebookLM: dán vào NotebookLM (SGK/SBT KNTT) để chép bài đúng LaTeX.'
    return (
        "<div class='admindang' data-path='"+html.escape(str(path or ''), quote=True)+"' data-dang='"+html.escape(dang, quote=True)+"'>"
        "<a class='btn' href='"+html.escape(href, quote=True)+"'>"+tex_lab+"</a>"
        "<span class='muted'>«"+title+"»</span>"
        + kind_chips_html(counts)
        + "<span class='gapnote'>"+html.escape(miss)+"</span>"
        "<span class='muted'>"+html.escape(heur_txt)+"</span>"
        "<button type='button' class='btn' id='aiGap'>1. 🤖 Soát dạng · đếm thiếu</button>"
        "<button type='button' class='btn green' id='aiFill'>2. ✍️ AI viết các câu còn thiếu</button>"
        "<input id='aiSrcUrl' type='url' placeholder='"+html.escape(url_ph, quote=True)+"' style='flex:1;min-width:16rem;padding:8px;border:1px solid #cbd8e6;border-radius:7px'>"
        "<button type='button' class='btn' id='aiImport'>📥 Lấy từ link → TEX</button>"
        "<button type='button' class='btn' id='aiNb'>📋 Prompt NotebookLM</button>"
        "<span class='muted'>"+hint+"</span>"
        "<div id='aiGapOut'></div></div>"
    )

def lesson_switch_html(path, qs, dang='', kind='', guest=False):
    scoped = questions_in_scope(qs, dang)
    return (
        "<div class='subnav'>"
        + dang_tabs_html(path, qs, current_dang=dang, kind=kind, guest=guest)
        + kind_tabs_html(path, dang=dang, current=kind, counts=kind_counts_for(scoped), guest=guest)
        + admin_dang_bar_html(path, qs, dang=dang)
        + "</div>"
    )

def _go_kind_href(path, dang, kind, guest=False):
    href = '/member/go-kind?path=' + urllib.parse.quote(str(path or ''), safe='') + '&kind=' + urllib.parse.quote(str(kind or ''), safe='')
    if dang:
        href += '&dang=' + urllib.parse.quote(str(dang), safe='')
    if guest:
        href = login_url(href)
    return href

def dang_tabs_html(path, qs, current_dang='', kind='', guest=False):
    names, counts = dang_names_of(qs)
    per, allc = dang_kind_counts_of(qs)
    current_dang = str(current_dang or '').strip()
    kind = norm_kind_tab(kind)
    total = sum(counts.values())
    bits = [
        f"<a class='dtab{' on' if not current_dang else ''}' href='{html.escape(_go_kind_href(path, '', kind, guest), quote=True)}' title='Mọi dạng trong bài'><span class='dname'>Cả bài · {total}</span>{kind_chips_html(allc)}</a>"
    ]
    for i, name in enumerate(names, 1):
        n = int(counts.get(name) or 0)
        short = name if len(name) <= 42 else name[:41] + '…'
        lab = f'{i}. {short} · {n}'
        on = ' on' if current_dang == name else ''
        bits.append(
            f"<a class='dtab{on}' href='{html.escape(_go_kind_href(path, name, kind, guest), quote=True)}' title='{html.escape(name, quote=True)}'><span class='dname'>{html.escape(lab)}</span>{kind_chips_html(per.get(name))}</a>"
        )
    return "<nav class='dangtabs' aria-label='Dạng bài tập'>" + ''.join(bits) + "</nav>"


def begin_kind_practice(path, kind='', dang=''):
    m = member_current()
    if not m:
        return redirect(login_url(request.full_path if request.query_string else '/member'))
    path = str(path or '').strip()
    dang = str(dang or '').strip()
    kind = norm_kind_tab(kind)
    if not path or not can_access(m, path):
        return redirect('/member')
    try:
        qs = load_lesson_questions(path)
    except Exception as e:
        return page('Lỗi', f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    scoped = questions_in_scope(qs, dang)
    ids = ids_of_kind(scoped, kind)
    if not ids and kind:
        kind = ''
        ids = ids_of_kind(scoped, '')
    if not ids:
        if dang:
            return redirect('/member/dang?path=' + urllib.parse.quote(path, safe='') + '&dang=' + urllib.parse.quote(dang, safe=''))
        return redirect('/member/select?path=' + urllib.parse.quote(path, safe=''))
    session.update(
        practice_path=path,
        practice_dang=dang,
        practice_kind=kind,
        practice_ids=ids,
        practice_pos=0,
        practice_right=0,
        practice_streak=0,
        practice_best=max(int(session.get('practice_best') or 0), 0),
        practice_done=[],
        practice_ai=True,
    )
    return redirect('/member/practice')

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

@app.get('/manifest.webmanifest')
def pwa_manifest():
    data = {
        "id": "/",
        "name": "Luyện Đề Toán Lý",
        "short_name": "Luyện Đề",
        "description": "Luyện đề Toán · Lý — Zalo thầy Minh 0946111107",
        "start_url": "/member",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#176bd3",
        "theme_color": "#176bd3",
        "lang": "vi",
        "icons": [
            {"src": "/static/pwa/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/pwa/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/static/pwa/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/manifest+json")

@app.get('/sw.js')
def pwa_sw():
    js = (
        "const C='ldvl-pwa-v1';"
        "self.addEventListener('install',e=>{self.skipWaiting()});"
        "self.addEventListener('activate',e=>{e.waitUntil(self.clients.claim())});"
        "self.addEventListener('fetch',e=>{"
        "const u=new URL(e.request.url);"
        "if(e.request.method!=='GET'||u.origin!==location.origin||!u.pathname.startsWith('/static/pwa/'))return;"
        "e.respondWith(caches.open(C).then(c=>c.match(e.request).then(r=>r||fetch(e.request).then(res=>{if(res.ok)c.put(e.request,res.clone());return res}))));"
        "});"
    )
    resp = Response(js, mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp

@app.get('/static/pwa/<name>')
def pwa_icon(name):
    allowed = {"icon-192.png", "icon-512.png", "apple-touch-icon.png"}
    if name not in allowed:
        abort(404)
    p = ROOT / "static" / "pwa" / name
    if not p.is_file():
        abort(404)
    return send_file(p, mimetype="image/png")
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
        d=members_data();found=None
        for m in d.get('members',[]):
            if str(m.get('username') or '').strip().casefold()==u.casefold() and str(m.get('status','ON')).upper()=='ON' and m.get('password_sha256')==h:
                found=m;break
        if found:
            persist_member_password_on_login(d, found, p)
            session.clear();session.permanent=True;session.update(role='member',username=found.get('username'),name=found.get('name') or found.get('username'));return redirect(safe_next_url())
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
            rec={'username':u,'name':n or u,'class':'','account_type':'FREE','status':'ON'}
            set_member_password(rec, p)
            d.setdefault('members',[]).append(rec)
            try:save_json_github(MEMBERS_FILE,d,'members.json','Add member')
            except Exception as e:msg='Không ghi được tài khoản: '+str(e)
            else:
                session.clear();session.permanent=True;session.update(role='member',username=u,name=n or u);return redirect('/member')
    body=f"<div class='wrap'><div class='panel' style='max-width:430px;margin:60px auto'><div class='head'>📝 Đăng ký thành viên FREE</div><div class='body'><form method='post' action='/member/register'><div class='field'><label>Họ tên</label><input name='name' autocomplete='name'></div><div class='field'><label>Tài khoản</label><input name='username' autocomplete='username' required></div><div class='field'><label>Mật khẩu</label><input name='password' type='password' autocomplete='new-password' required></div><button class='btn primary' type='submit'>Tạo tài khoản</button> <a class='btn' href='/member/login'>Đã có tài khoản</a><div class='err'>{html.escape(msg)}</div></form></div></div></div>";return page('Đăng ký',body)

@app.get('/member/logout')
def member_logout():session.clear();return redirect('/member')

@app.get('/member/ai')
def member_ai():
    m=member_current()
    if not m:return redirect('/member/login')
    extra="<p class='muted'>Key dùng khi chọn chế độ <b>Làm bài + phản biện AI</b>. Sau khi xác nhận đáp án, màn hình chia đôi: bên trái là đề và lời giải, bên phải là Gemini (cuộn riêng).</p>"
    body=("<div class='wrap'><div class='panel'><div class='head'>🤖 Gemini — nạp key và phản biện</div><div class='body'>"
          +gemini_panel_html(extra)+
          "<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>")
    return page('Key Gemini',body)

@app.get('/member')
def member_index():
    m=member_current()
    idx=index_data();items=[x for x in idx.get('lessons',[]) if isinstance(x,dict) and str(x.get('path','')).startswith('ngan-hang/') and is_bank_question_tex(str(x.get('path') or ''))]
    if m:
        items=[x for x in items if can_view(m, str(x.get('path') or ''))]
    else:
        items=[x for x in items if str(lesson_level(str(x.get('path') or ''))).upper()!='VIP']
    q=request.args.get('q','').strip().lower();sm=request.args.get('mon','');cl=request.args.get('lop','')
    id_block=''
    if q:
        import dang_routes as _dang
        id_block=_dang.qid_results_html(q,m)
    def keep(x):
        t=' '.join(str(x.get(k) or '') for k in ('Mon','Lop','Chuong','BaiHoc','De')).lower();return (not q or q in t) and (not sm or str(x.get('Mon'))==sm) and (not cl or str(x.get('Lop'))==cl)
    items=[x for x in items if keep(x)]
    items=merge_catalog_lessons(items)
    groups={}
    for x in items:groups.setdefault((str(x.get('Mon') or 'Khác'),str(x.get('Lop') or ''),str(x.get('Chuong') or 'Chưa xác định')),[]).append(x)
    sections=[]
    for (mon,lop,chuong),arr in sorted(groups.items()):
        sections.append(catalog_chapter_html(mon,lop,chuong,arr))
    subjopts=''.join("<option value='"+html.escape(s,quote=True)+"'"+(" selected" if sm==s else "")+">"+html.escape(s)+"</option>" for s in subjects);classopts=''.join("<option value='"+html.escape(c,quote=True)+"'"+(" selected" if cl==c else "")+">"+html.escape(c)+"</option>" for c in classes)
    if m:
        who="<div class='notice'>👤 <b>"+html.escape(str(m.get('name') or m.get('username')))+"</b> · Tài khoản <b>"+html.escape(str(m.get('username')))+"</b> · Quyền <b>"+html.escape(str(m.get('account_type','FREE')))+"</b></div>"
    else:
        who="<div class='notice'>👁 <b>Xem đề không cần đăng nhập.</b> Để làm bài và dùng Gemini phản biện, hãy <a href='/member/login'>đăng nhập</a> hoặc <a href='/member/register'>đăng ký</a>.</div>"
    body=("<div class='wrap'><div class='panel'><div class='head'>📚 MỤC LỤC <span class='tag'>"+str(len(items))+" bài</span><span class='tag'>"+str(idx.get('total_questions',0))+" câu</span></div><div class='body'>"+who+"<form method='get' class='catsearch'><input name='q' placeholder='Tìm ID câu, bài, chương...' value='"+html.escape(q)+"'><select name='mon'><option value=''>Tất cả môn</option>"+subjopts+"</select><select name='lop'><option value=''>Tất cả lớp</option>"+classopts+"</select><button class='btn'>Tìm</button></form></div></div>"+id_block+(''.join(sections) or ('' if id_block else "<div class='panel' style='margin-top:10px'><div class='body muted'>Không có bài phù hợp.</div></div>"))+"</div>")
    return page('Mục lục',body)

@app.get('/member/select')
def select_page():
    m=member_current()
    p=request.args.get('path','')
    if not can_view(m,p):
        if not m: return redirect(login_url(request.full_path if request.query_string else '/member/select?path='+urllib.parse.quote(p,safe='')))
        return page('Bài VIP',"<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")
    try:
        qs=parse_lesson_questions(p)
        if not qs:
            _,tex=read_tex(p); qs=parse_questions(tex)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    guest = not m
    admin_pick = can_manage_bank()
    pick_html=''
    if admin_pick:
        dang_names=[];seen=set()
        for q in qs:
            if q['dang'] not in seen:seen.add(q['dang']);dang_names.append(q['dang'])
        kind_rows=[('TN','Trắc nghiệm'),('DS','Đúng / Sai'),('TLN','Trả lời ngắn'),('TL','Tự luận')]
        rows=[]
        for di,dang in enumerate(dang_names):
            arr=[q for q in qs if q['dang']==dang]
            uncat=dang in ('','Chưa phân dạng')
            mark=("<span class='tag miss'>Chưa có</span>" if uncat else "<span class='tag had'>Đã có</span>")
            dang_cell=f"<td rowspan='{len(kind_rows)}'>{html.escape(dang)} {mark}</td>"
            for ki,(kind,label) in enumerate(kind_rows):
                c={z:sum(1 for q in arr if q['kind']==kind and q['level']==z) for z in 'NHVC'};inputs=''.join(f"<input class='n' type='number' min='0' max='{c[z]}' value='0' name='pick:{di}:{kind}:{z}'>" for z in 'NHVC');total=sum(c.values())
                tr=f"<tr class='{'uncat' if uncat else 'had'}'>"
                if ki==0: tr+=dang_cell
                rows.append(tr+f"<td>{label}</td><td>{c['N']}/{c['H']}/{c['V']}/{c['C']}</td><td>{inputs}</td><td>{total}</td></tr>")
        pick_html=(
            "<form method='post' action='/member/start'><input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'>"
            "<div class='selectwrap'><table class='selectgrid'><tr><th>Dạng bài</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>"
            +''.join(rows)+"</table></div>"
            "<div id='sum' class='notice' style='margin-top:10px'>TỔNG CHỌN: 0 câu</div>"
            "<div class='modebar'><button class='btn primary' type='submit' name='ai_review' value='0'>▶ Làm bài (không phản biện)</button>"
            "<button class='btn' type='submit' name='ai_review' value='1'>🤖 Làm bài + phản biện AI</button></div></form>"
            "<script>function upd(){let t=0;document.querySelectorAll('.n').forEach(x=>{let m=Number(x.max)||0,v=Math.max(0,Math.min(m,Number(x.value)||0));x.value=v;t+=v});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu'}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',upd));upd();</script>"
        )
    admin_box=''
    if admin_pick:
        import admin_classify as _ac
        names_one=[];seen_one=set()
        for q in qs:
            if q['dang'] not in seen_one:seen_one.add(q['dang']);names_one.append(q['dang'])
        admin_box=admin_tex_select_html(p)+_ac.select_admin_panel(p, qs, names_one)
    guest_note=''
    if guest:
        guest_note=f"<div class='notice'>👁 Đăng nhập rồi bấm dạng / loại ở trên để làm bài. <a class='btn primary' href='{html.escape(login_url('/member/select?path='+urllib.parse.quote(p,safe='')), quote=True)}'>Đăng nhập</a></div>"
    chap=chapter_nav_html(p)
    _, cur_lesson = chapter_lessons_for(p)
    bai_name=html.escape(str((cur_lesson or {}).get('BaiHoc') or Path(p).parent.name))
    tabs=lesson_switch_html(p, qs, dang='', kind='', guest=guest)
    body=f"<div class='wrap'>{tabs}<div class='panel'><div class='head'>🧩 {bai_name} <span class='tag'>{len(qs)} câu trong bài</span></div><div class='body'>{chap}{admin_box}{guest_note}{pick_html}<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>"
    extra=''
    if admin_pick:
        from admin_rewrite import REWRITE_CLIENT_JS
        extra=REWRITE_CLIENT_JS
    return page('Chọn câu',body+extra)

@app.post('/member/start')
def start_practice():
    m=member_current();
    if not m:return redirect(login_url('/member/practice'))
    if request.form.getlist('qid'):
        import dang_routes as _dang
        return _dang.start_selected_questions()
    p=request.form.get('path','')
    if not can_access(m,p):return redirect('/member')
    try:
        qs=parse_lesson_questions(p)
        if not qs:
            _,tex=read_tex(p); qs=parse_questions(tex)
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
    wanted=sort_ids_by_kind(qs, wanted, shuffle_within=False)
    kinds=set(str((next((q for q in qs if q.get('idx')==i),{}) or {}).get('kind') or '') for i in wanted)
    kinds={k for k in kinds if k}
    session.update(practice_path=p,practice_dang='',practice_kind=(next(iter(kinds)) if len(kinds)==1 else ''),practice_ids=wanted,practice_pos=0,practice_right=0,practice_streak=0,practice_best=0,practice_done=[],practice_ai=True);return redirect('/member/practice')

@app.get('/member/go-kind')
def go_kind():
    path = (request.args.get('path') or '').strip() or str(session.get('practice_path') or '')
    if 'path' in request.args:
        dang = request.args.get('dang') or ''
    else:
        dang = str(session.get('practice_dang') or '')
    return begin_kind_practice(path, request.args.get('kind') or '', dang)

def question_payload(q):
    """Toàn bộ dữ liệu một câu cho trang làm bài và cho AI phản biện."""
    try:
        fi=int(q.get('file_idx') if q.get('file_idx') is not None else q.get('idx') or 0)
    except (TypeError, ValueError):
        fi=0
    p={'kind':q['kind'],'id':q.get('id') or '','cau':q.get('cau') or '','nguon':q.get('nguon') or '','text':html_question(q['text']),'solution':html_question(q['solution']),'dang':q['dang'],'level':q['level'],'src':str(q.get('src') or ''),'file_idx':fi,'line':int(q.get('line') or 0)}
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
    if not m:return redirect(login_url('/member/practice'))
    p=str(session.get('practice_path') or '');ids=list(session.get('practice_ids') or []);pos=int(session.get('practice_pos') or 0);right=int(session.get('practice_right') or 0);streak=int(session.get('practice_streak') or 0);best=int(session.get('practice_best') or 0);done=list(session.get('practice_done') or [])
    ai=True
    if not p or not ids:return redirect('/member')
    try:
        allq={q['idx']:q for q in parse_lesson_questions(p)}
        if not allq:
            _,tex=read_tex(p); allq={q['idx']:q for q in parse_questions(tex)}
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    if pos>=len(ids):
        score=right/len(ids)*10 if ids else 0
        gem=''
        if ai:
            opts=''.join(f"<option value='{i}'>Câu {d.get('question') or i+1} · {'Đúng' if d.get('ok') else 'Sai'}</option>" for i,d in enumerate(done))
            review=[review_payload(allq.get(ids[int(d.get('question') or 0)-1]) if 0<int(d.get('question') or 0)<=len(ids) else None,d) for d in done]
            gem=(gemini_panel_html()
                 + f"<div class='review'><b>🤖 Gemini phản biện 1 câu</b><div class='gkeyrow'><select id='pick'>{opts}</select> <button type='button' class='btn primary' onclick='rv()'>🤖 Phản biện</button></div><div id='out' class='reviewout'></div></div>"
                 + f"<script>const D={json.dumps(review,ensure_ascii=False)};function rv(){{ldvlGeminiReview(D[+document.getElementById('pick').value],document.getElementById('out'))}}</script>")
        body=(
            f"<div class='wrap'>{lesson_switch_html(p, list(allq.values()), dang=str(session.get('practice_dang') or ''), kind=session.get('practice_kind') or '', guest=False)}<div class='panel'><div class='head'>🎉 Kết quả <span class='tag'>Đúng {right}/{len(ids)}</span> <span class='tag'>{score:.2f}/10</span>"
            f"<span class='tag'>{'🤖 Có phản biện' if ai else 'Không phản biện'}</span></div>"
            f"<div class='body'><div class='result good'>Chuỗi tốt nhất: {best}</div>"
            + gem
            + "<p><a class='btn' href='/member'>← Mục lục</a></p></div></div></div>"
        )
        return page('Kết quả',body)
    q=allq.get(ids[pos]);
    if not q:return redirect('/member')
    palette=''.join(f"<a class='pitem {'pcur' if j==pos else ('pdone' if j<len(done) and done[j].get('ok') else ('pwrong' if j<len(done) else ''))}' href='/practice/jump/{j}' title='{html.escape(str(allq.get(qid,{}).get('id') or ''), quote=True)}'>{j+1} · {allq.get(qid,{}).get('kind','?')}</a>" for j,qid in enumerate(ids))
    payload=question_payload(q)
    is_admin=has_full_bank_access(m)
    mode_tag='🤖 Có phản biện AI' if ai else 'Không phản biện'
    if is_admin: mode_tag='🔐 ADMIN · xem lời giải không cần làm bài'+((' · '+mode_tag) if ai else '')
    dang=str(session.get('practice_dang') or '')
    tabs=lesson_switch_html(p, list(allq.values()), dang=dang, kind=session.get('practice_kind') or '', guest=False)
    body=(f"<div class='wrap'>{tabs}<div class='panel'><div class='head quiztop'><span>📝 Câu {pos+1}/{len(ids)} · <span class='qid'>{html.escape(str(q.get('id') or '—'))}</span><span class='quizdang'> · {html.escape(q['dang'])} · {q['kind']}</span></span>"
          f"<span class='qzoombar'><button type='button' class='btn' id='qZmOut' title='Thu nhỏ chữ'>A−</button>"
          f"<button type='button' class='btn' id='qZmFit' title='Chữ to tối đa, vẫn vừa màn hình'>Vừa màn</button>"
          f"<b id='qzoomlab'>100%</b>"
          f"<button type='button' class='btn' id='qZmIn' title='Phóng to chữ'>A+</button></span>"
          f"<span class='quizstat'>Đúng {right} · Chuỗi {streak}<span class='quizdang'> · {html.escape(mode_tag)}</span></span></div><div class='body'><div class='palette'><div class='pdang'>{html.escape(str(q.get('dang') or session.get('practice_dang') or ''))}</div><div class='pitems'>{palette}</div></div><div id='praise'></div>"
          f"<div class='practice-split' id='psplit'><div class='practice-q'><div id='q' class='qbox'></div></div><aside class='practice-ai' id='aipane' hidden></aside></div></div></div></div>")
    js=r'''<script>
const Q=__DATA__;const AI=__AI__;const IS_ADMIN=__ADMIN__;let checked=false;
function E(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function typeset(el){if(window.ldvlTypeset)return window.ldvlTypeset(el||document.getElementById('q'));el=el||document.getElementById('q');if(window.MathJax&&MathJax.typesetPromise){try{if(MathJax.typesetClear)MathJax.typesetClear([el]);}catch(e){}MathJax.typesetPromise([el]).catch(function(){});}}
const QZKEY='ldvlQZoom';
let qZoom=(function(){try{var v=parseFloat(localStorage.getItem(QZKEY)||'1');return (v>=0.8&&v<=2.6)?v:1}catch(e){return 1}})();
function ldvlApplyQZoom(){
  const box=document.getElementById('q');
  if(box) box.style.setProperty('--qzoom', String(qZoom));
  const lab=document.getElementById('qzoomlab');
  if(lab) lab.textContent=Math.round(qZoom*100)+'%';
  try{localStorage.setItem(QZKEY,String(qZoom))}catch(e){}
  typeset(document.getElementById('q'));
}
function ldvlQZoom(dir){
  qZoom=Math.round((qZoom+dir*0.1)*10)/10;
  qZoom=Math.max(0.8,Math.min(2.6,qZoom));
  ldvlApplyQZoom();
}
function ldvlQFit(){
  const box=document.getElementById('q');
  if(!box) return;
  const top=box.getBoundingClientRect().top;
  const availH=Math.max(180, window.innerHeight-top-18);
  const host=document.querySelector('.practice-q')||box.parentElement;
  const availW=Math.max(280,(host&&host.clientWidth)||box.clientWidth);
  let lo=0.8, hi=2.6, best=0.8;
  for(let i=0;i<14;i++){
    const mid=(lo+hi)/2;
    box.style.setProperty('--qzoom', String(mid));
    void box.offsetHeight;
    if(box.scrollHeight<=availH+2 && box.scrollWidth<=availW+2){best=mid;lo=mid;}
    else hi=mid;
  }
  qZoom=Math.max(0.8, Math.min(2.6, Math.round(best*0.97*10)/10));
  ldvlApplyQZoom();
}
function ldvlBindQZoom(){
  const a=document.getElementById('qZmOut'), b=document.getElementById('qZmIn'), f=document.getElementById('qZmFit');
  if(a) a.onclick=function(){ldvlQZoom(-1)};
  if(b) b.onclick=function(){ldvlQZoom(1)};
  if(f) f.onclick=ldvlQFit;
}
document.addEventListener('keydown',function(e){
  const t=e.target;
  if(t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.isContentEditable)) return;
  if(e.key==='-'||e.key==='_'){e.preventDefault();ldvlQZoom(-1)}
  else if(e.key==='='||e.key==='+'){e.preventDefault();ldvlQZoom(1)}
  else if(e.key==='0'&&!e.ctrlKey){e.preventDefault();ldvlQFit()}
});
function lockInputs(){document.querySelectorAll('#q input,#q textarea').forEach(function(el){el.disabled=true});let b=document.getElementById('chkbtn');if(b)b.style.display='none';let hint=document.getElementById('hint');if(hint)hint.remove()}
function ldvlPlaceFigs(root){
  root=root||document.getElementById('q');
  if(!root) return;
  const stem=root.querySelector('.qstem');
  const fig=root.querySelector('.qfig');
  const body=root.querySelector('.qbody.ds');
  if(!stem||!fig||!body) return;
  const bits=[];
  stem.querySelectorAll('.immini,.tikz-row,.tikzfig,.tikz-live,.ytbox,table.tex-table').forEach(function(el){
    if(el.closest('.immini,.tikz-row')&&!el.matches('.immini,.tikz-row')) return;
    bits.push(el);
  });
  if(!bits.length){fig.remove();return;}
  bits.forEach(function(el){fig.appendChild(el)});
  fig.hidden=false;
  body.classList.add('hassplit');
}
function draw(){let q=Q,h=(q.nguon?'<div class="nguonrow"><span class="nguon">Nguồn: '+E(q.nguon)+'</span></div>':'')+'<div class="qheadline"><span class="qbadge">Câu __POS__</span>'+(q.id?'<span class="qid">'+E(q.id)+'</span> ':'')+'<div class="qstem">'+q.text+'</div></div>';
if(q.kind==='TN')q.options.forEach((o,i)=>h+='<label class="opt" id="o'+i+'"><input type="radio" name="a" value="'+i+'"> <span class="tflab">'+String.fromCharCode(65+i)+'</span> '+o.text+'</label>');
else if(q.kind==='DS'){h+='<div class="qbody ds"><div class="qfig" hidden></div><div class="qtf"><div class="tfgrid"><div class="tf-colhead"><span></span><span></span><span class="tf-h yes">Đúng</span><span class="tf-h no">Sai</span></div>';q.statements.forEach((s,i)=>{const lab='ABCD'.charAt(i)||(i+1);h+='<div class="tf" id="t'+i+'"><span class="tflab">'+lab+'</span><div class="tf-text">'+s.text+'</div><label class="tf-box yes"><input type="radio" name="t'+i+'" value="1"></label><label class="tf-box no"><input type="radio" name="t'+i+'" value="0"></label></div>'});h+='</div></div></div>'}
else if(q.kind==='TLN')h+='<input id="ans" class="answerbox" style="width:100%;padding:10px;border:1px solid #cbd8e6;border-radius:7px" placeholder="Nhập đáp án rồi bấm Xác nhận (hoặc Enter)">';
else h+='<textarea id="ans" class="answerbox" style="width:100%;height:190px;padding:10px;border:1px solid #cbd8e6;border-radius:7px" placeholder="Nhập bài làm"></textarea>';
h+='<div class="quizacts"><button class="btn primary" id="chkbtn" onclick="check()" disabled>✅ Xác nhận</button><button id="solbtn" class="btn" style="display:'+(IS_ADMIN?'inline-block':'none')+'" onclick="openSolution()">📖 Xem lời giải</button><button id="next" class="btn" style="display:none" onclick="location.href=\'/member/practice\'">→ Câu tiếp</button></div><div id="hint" class="hintline">'+(IS_ADMIN?'🔐 ADMIN: có thể xem lời giải không cần làm bài.':'Chọn đáp án rồi bấm <b>Xác nhận</b> — lời giải chỉ mở sau khi xác nhận.')+'</div><div id="r">'+(IS_ADMIN?'<div id="solbox" class="solution" style="display:none"><b>📖 Lời giải</b><div>'+(q.solution||'Chưa có lời giải trong file TEX.')+'</div></div>':'')+'</div>';document.getElementById('q').innerHTML=h;ldvlPlaceFigs();ldvlBindQZoom();ldvlApplyQZoom();bind();if(IS_ADMIN)ldvlMountPracticeRewrite();typeset(document.getElementById('q'))}
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
function openSolution(){if(!IS_ADMIN&&!checked)return alert('Hãy chọn đáp án và bấm Xác nhận trước.');let box=document.getElementById('solbox');if(!box){let r=document.getElementById('r');if(!r)return;r.insertAdjacentHTML('beforeend','<div id="solbox" class="solution" style="display:none"><b>📖 Lời giải</b><div>'+(Q.solution||'Chưa có lời giải trong file TEX.')+'</div></div>');box=document.getElementById('solbox')}box.style.display='block';typeset(box);let b=document.getElementById('solbtn');if(b)b.style.display='none';if(IS_ADMIN)ldvlMountPracticeRewrite()}
function ldvlMountPracticeRewrite(){if(!IS_ADMIN||!Q.src||Q.file_idx==null)return;if(document.getElementById('rwPractice'))return;let r=document.getElementById('r');if(!r)return;let texHref='/admin/edit?path='+encodeURIComponent(Q.src)+(Q.line?('&line='+Q.line):'');r.insertAdjacentHTML('afterend','<div class="rwbar" id="rwPractice"><a class="btn mini" href="'+texHref+'">✏️ TEX câu này</a> <button type="button" class="btn mini" id="rwPrGo">✍️ AI viết lại đề + lời giải</button> <button type="button" class="btn mini" id="rwPrEdit">✏️ Sửa đề / lời giải</button><div class="rwout" id="rwPrOut"></div></div>');document.getElementById('rwPrGo').onclick=function(){if(window.ldvlAdminRewrite)ldvlAdminRewrite(Q.src,Q.file_idx,document.getElementById('rwPrOut'))};document.getElementById('rwPrEdit').onclick=function(){if(window.ldvlAdminEdit)ldvlAdminEdit(Q.src,Q.file_idx,document.getElementById('rwPrOut'))}}
function showAiPane(){let pane=document.getElementById('aipane'),split=document.getElementById('psplit');if(!pane||!split)return;split.classList.add('is-ai');pane.hidden=false;
pane.innerHTML=ldvlGeminiMiniHtml('🤖 Phản biện AI')+'<p style="margin-top:10px"><button type="button" class="btn primary" onclick="reviewNow()">🤖 Phản biện câu này</button></p><div id="aiout" class="reviewout"></div>';
if(window.ldvlFillGeminiInputs)ldvlFillGeminiInputs();pane.scrollTop=0;if(window.LAST_REVIEW&&typeof ldvlFilledKeys==='function'&&ldvlFilledKeys().length)reviewNow()}
function verdictHtml(q, student, ok){
  const labs='ABCD';
  let head=q.kind==='TL'?'Đã nộp bài tự luận — chờ chấm.':(ok?'Đúng':'Sai');
  function circ(letter, cls){return '<span class="keycell '+(cls||'')+'"><span class="kcirc tn">'+letter+'</span></span>';}
  function row(label, items){
    const cells=items.map(function(it){
      const ds=it.mark||'';
      if(!ds) return circ(it.letter, it.cls);
      const kind=ds==='Đ'?'d':(ds==='S'?'s':'');
      return '<span class="keycell '+(it.cls||'')+'"><span class="klet">'+it.letter+'</span><span class="kcirc '+kind+'">'+ds+'</span></span>';
    }).join('');
    return '<span class="keyrow"><span class="keylab">'+label+'</span>'+cells+'</span>';
  }
  if(q.kind==='TN'){
    const key=(q.options||[]).map(function(o,i){return o.correct?labs.charAt(i):''}).filter(Boolean).join('')||'?';
    const pick=student||'?';
    const same=pick===key;
    return '<span class="vres">'+head+'</span><span class="keygrid">'+row('Đáp án đúng',[{letter:key,mark:'',cls:'ok'}])+row('Bạn chọn',[{letter:pick,mark:'',cls:same?'ok':'bad'}])+'</span>';
  }
  if(q.kind==='DS'){
    const keys=(q.statements||[]).map(function(s){return s.correct?'Đ':'S'});
    const marks=String(student||'').split('').filter(function(c){return c==='Đ'||c==='S'});
    const ans=keys.map(function(m,i){return {letter:labs.charAt(i),mark:m,cls:'ok'}});
    const you=keys.map(function(m,i){const p=marks[i]||'?';return {letter:labs.charAt(i),mark:p,cls:p===m?'ok':'bad'}});
    return '<span class="vres">'+head+'</span><span class="keygrid">'+row('Đáp án đúng',ans)+row('Bạn chọn',you)+'</span>';
  }
  if(q.kind==='TLN'){
    return '<span class="vres">'+head+' · Đáp án đúng: '+(q.answer||'—')+' · Bạn chọn: '+(student||'—')+'</span>';
  }
  return head;
}
function check(){if(checked)return;let q=Q,ok=false,student='';
if(q.kind==='TN'){let z=document.querySelector('input[name=a]:checked');if(!z)return alert('Hãy chọn đáp án.');let i=+z.value;student=String.fromCharCode(65+i);q.options.forEach((o,j)=>{if(o.correct)document.getElementById('o'+j).classList.add('correct');if(j===i&&!o.correct)document.getElementById('o'+j).classList.add('wrong')});ok=!!q.options[i].correct}
else if(q.kind==='DS'){ok=true;let a=[];for(let i=0;i<q.statements.length;i++){let z=document.querySelector('input[name=t'+i+']:checked');if(!z)return alert('Chọn đủ Đúng/Sai.');let v=z.value==='1';a.push(v?'Đ':'S');document.getElementById('t'+i).classList.add(v===q.statements[i].correct?'correct':'wrong');if(v!==q.statements[i].correct)ok=false}student=a.join('')}
else{let z=document.getElementById('ans');if(!z||!z.value.trim())return alert('Hãy nhập câu trả lời.');student=z.value.trim();ok=q.kind==='TLN'&&norm(student)===norm(q.answer);}
let note=verdictHtml(q,student,ok);let sol=q.solution||'Chưa có lời giải trong file TEX.';document.getElementById('r').innerHTML='<div class="result '+(ok?'good':'bad')+'">'+note+'</div><div id="solbox" class="solution" style="display:none"><b>📖 Lời giải</b><div>'+sol+'</div></div>';typeset(document.getElementById('q'));checked=true;lockInputs();document.getElementById('next').style.display='inline-block';window.LAST_REVIEW=Object.assign({},q,{student:student,ok:ok});
if(true){openSolution();showAiPane()}else{let sb=document.getElementById('solbtn');if(sb)sb.style.display='inline-block'}
fetch('/member/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ok:ok,student:student,text:q.text,solution:sol,kind:q.kind,dang:q.dang})}).then(r=>r.json()).then(d=>{if(d.praise)document.getElementById('praise').innerHTML='<div class="praise">'+E(d.praise)+'</div>'})}
function reviewNow(){ldvlGeminiReview(window.LAST_REVIEW,document.getElementById('aiout'))}
function norm(s){return String(s??'').replace(/\$+/g,'').replace(/\s+/g,'').replace(/,/g,'.').toLowerCase()}
draw();</script>'''.replace('__DATA__',json.dumps(payload,ensure_ascii=False)).replace('__POS__',str(pos+1)).replace('__AI__','true').replace('__ADMIN__','true' if is_admin else 'false')
    extra=''
    if is_admin:
        from admin_rewrite import REWRITE_CLIENT_JS
        from live_present import PRESENT_HOST_JS
        extra=REWRITE_CLIENT_JS + PRESENT_HOST_JS
    return page('Làm bài',body+js+extra)

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
    return redirect('/member/login')

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
        "<a class='btn' href='/admin/ly-thuyet'>📖 Lý thuyết / dạng mẫu</a>"
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
    try:
        qs=parse_lesson_questions(p)
        if not qs:
            sha,tex=read_tex(p, need_sha=True); qs=parse_questions(tex)
            for q in qs:
                q['src']=p; q['file_idx']=int(q.get('idx') or 0)
        else:
            sha=''
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    groups=find_duplicate_groups(qs)
    extra_keys=set()
    for g in groups:
        extras=set(g.get('extras') or [])
        for q in g.get('members') or []:
            if q.get('idx') not in extras:
                continue
            src=str(q.get('src') or p).replace('\\','/')
            try: fi=int(q.get('file_idx') if q.get('file_idx') is not None else q.get('idx') or 0)
            except (TypeError, ValueError):
                continue
            extra_keys.add((src, fi))
    if request.method=='POST':
        if request.form.get('confirm')!='yes':
            return _dup_after(p, nxt, 'err', 'Phải xác nhận trước khi xóa trùng.')
        drops_by={}
        for raw in request.form.getlist('drop'):
            raw=str(raw or '').strip()
            src, fi = p, None
            if '||' in raw:
                src, _, idx_s = raw.replace('\\','/').rpartition('||')
                try: fi=int(idx_s)
                except Exception: continue
            else:
                try: fi=int(raw)
                except Exception: continue
                src=p
            src=src.replace('\\','/')
            if (src, fi) not in extra_keys:
                continue
            drops_by.setdefault(src, []).append(fi)
        if not drops_by:
            return _dup_after(p, nxt, 'err', 'Chưa chọn câu trùng để xóa.')
        total=0
        try:
            for src, idxs in drops_by.items():
                idxs=sorted(set(idxs))
                fsha, tex = read_tex(src, need_sha=True)
                new=tex_without_questions(tex, idxs)
                local=_safe_repo_file(src)[1]
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_text(new, encoding='utf-8')
                if TOKEN:
                    github_put_text(src, new, 'ADMIN xóa '+str(len(idxs))+' câu trùng trong '+src, fsha or None)
                total += len(idxs)
            try:
                from dang_routes import _STATS_CACHE, _QID_CACHE
                _STATS_CACHE.clear(); _QID_CACHE.clear()
            except Exception:
                pass
            return _dup_after(p, nxt, 'ok', 'Đã xóa '+str(total)+' câu trùng, giữ bản đầu mỗi nhóm.')
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
                src=str(q.get('src') or p).replace('\\','/')
                try: fi=int(q.get('file_idx') if q.get('file_idx') is not None else q.get('idx') or 0)
                except (TypeError, ValueError): fi=int(q.get('idx') or 0)
                chk=f"<label><input type='checkbox' name='drop' value='{html.escape(src+'||'+str(fi), quote=True)}'{auto}> Xóa bản này</label>"
            fn=html.escape(str(q.get('src') or p).replace('\\','/').rsplit('/',1)[-1])
            rows.append(
                "<tr><td>"+chk+"</td><td>"+str(q.get('stt'))+"</td><td><code>"+html.escape(str(q.get('id') or '—'))+"</code></td>"
                "<td>"+html.escape(str(q.get('kind')))+"</td><td>"+fn+" · dòng "+str(q.get('line') or '')+"</td>"
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
        "<div class='wrap'><div class='panel'><div class='head'>🔎 Câu trùng · cả bài</div><div class='body'>"
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
def admin_logout():session.clear();return redirect('/member/login')

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


@app.route('/admin/edit', methods=['GET', 'POST'])
def admin_edit():
    if not can_manage_bank():return redirect('/admin/login')
    def _edit_path(raw):
        p=str(raw or '').replace('\\','/').strip().lstrip('/')
        if not p: raise ValueError('Thiếu đường dẫn file .tex')
        if p.lower().endswith('.tex'): return p
        folder=p.rstrip('/')
        for name in ('de.tex','lt.tex','pp.tex'):
            cand=folder+'/'+name
            try:
                _, local=_safe_repo_file(cand)
                if local.is_file(): return cand
            except Exception:
                continue
        return folder+'/de.tex'
    p=request.args.get('path','')
    if request.method=='POST':
        p=request.form.get('path','')
    try:
        p=_edit_path(p)
    except Exception as e:
        return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    if request.method=='POST':
        new=request.form.get('content','')
        msg=(request.form.get('message') or 'ADMIN cập nhật TEX').strip() or 'ADMIN cập nhật TEX'
        try:
            _, local=_safe_repo_file(p)
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(new, encoding='utf-8')
        except Exception as e:
            return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>Không ghi được máy: {html.escape(str(e))}</div></div></div>")
        gh_err=''
        if TOKEN:
            try:
                sha=str(request.form.get('sha') or '').strip() or github_file_sha(p)
                github_put_text(p, new, msg, sha=sha or None)
            except Exception as e:
                try:
                    github_put_text(p, new, msg, sha=github_file_sha(p) or None)
                except Exception as e2:
                    gh_err=str(e2 or e)
        try:
            import lythuyet as _lt
            kn=str(p or '').replace('\\','/').rsplit('/',1)[-1].lower()
            if kn in ('lt.tex','pp.tex'):
                _lt.set_status(p, _lt._kind_of_file(p), False)
        except Exception:
            pass
        q='saved=1' if not gh_err else 'saved=1&gher='+urllib.parse.quote(gh_err[:180])
        if not TOKEN:
            q='saved=1&gher='+urllib.parse.quote('Chưa có GITHUB_TOKEN trên Render — đã lưu máy, chưa lên GitHub.')
        return redirect('/admin/edit?path='+urllib.parse.quote(p,safe='')+'&'+q)
    try:sha,txt=read_tex(p, need_sha=True)
    except Exception as e:return page('Lỗi',f"<div class='wrap'><div class='panel'><div class='body err'>{html.escape(str(e))}</div></div></div>")
    saved=request.args.get('saved')=='1';gher=request.args.get('gher') or ''
    try: jump=int(request.args.get('line') or 0)
    except (TypeError, ValueError): jump=0
    if jump<1: jump=0
    notice="<div class='success'>✅ Đã lưu. Sửa tiếp trong ô bên dưới rồi bấm <b>Lưu</b>.</div>" if saved else ''
    if gher: notice += "<div class='err'>"+html.escape(gher)+"</div>"
    if jump: notice += "<div class='notice'>Đang mở <b>dòng "+str(jump)+"</b> trong file (từ thẻ câu ngân hàng).</div>"
    companion_bar=''
    try:
        import lythuyet as _lt
        kn=str(p or '').replace('\\','/').rsplit('/',1)[-1].lower()
        if kn in ('lt.tex','pp.tex'):
            kind=_lt._kind_of_file(p)
            ok=_lt.is_approved(p, kind)
            st='Đã duyệt — học viên thấy' if ok else 'Chưa duyệt — học viên không thấy'
            notice += "<div class='notice'><b>Lý thuyết / dạng mẫu:</b> "+html.escape(st)+". Bấm <b>Lưu</b> sẽ gỡ duyệt; xong thì Duyệt lại.</div>"
            companion_bar=(
                "<form method='post' action='/admin/companion/status' style='display:flex;gap:8px;flex-wrap:wrap;margin:8px 0'>"
                "<input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'>"
                "<input type='hidden' name='kind' value='"+html.escape(kind)+"'>"
                "<input type='hidden' name='next' value='/admin/edit?path="+urllib.parse.quote(p,safe='')+"'>"
                +("<button class='btn green' name='status' value='approved' type='submit'>✅ Duyệt cho học viên</button>" if not ok else "")
                +("<button class='btn red' name='status' value='pending' type='submit'>↩ Gỡ duyệt</button>" if ok else "")
                +"<a class='btn' href='/admin/ly-thuyet'>📋 Danh sách duyệt</a></form>"
            )
    except Exception:
        companion_bar=''
    body=(
        "<div class='wrap'><div class='panel'><div class='head'>✏️ ADMIN · Sửa TEX ngay trên trang này</div><div class='body'>"
        "<div class='meta'><code>"+html.escape(p)+"</code></div>"+notice+companion_bar
        +"<p class='notice'><b>Gõ sửa trong ô đen dưới đây</b> (không cần sang GitHub), rồi bấm <b>💾 Lưu</b>.</p>"
        "<form method='post' class='edittex'>"
        "<input type='hidden' name='path' value='"+html.escape(p,quote=True)+"'>"
        "<input type='hidden' name='sha' value='"+html.escape(sha,quote=True)+"'>"
        "<div class='editbar'><input name='message' value='ADMIN cập nhật TEX' style='flex:1;min-width:12rem;padding:9px;border:1px solid #cbd8e6;border-radius:7px'>"
        "<button class='btn green' type='submit'>💾 Lưu</button> "
        "<a class='btn' href='/admin/ly-thuyet'>← Duyệt LT</a></div>"
        "<label class='muted' style='display:block;margin:8px 0 4px'>Nội dung file</label>"
        "<textarea name='content' class='code' id='texsrc' spellcheck='false' autocomplete='off'>"+html.escape(txt)+"</textarea>"
        "</form>"
        "<p class='muted' style='margin-top:10px'><a href='"+html.escape(github_web_edit_url(p),quote=True)+"' target='_blank' rel='noopener'>Sửa trên github.com</a> · "
        "<a href='"+html.escape(github_blob_url(p),quote=True)+"' target='_blank' rel='noopener'>Xem GitHub</a></p>"
        "</div></div></div>"
        "<style>.editbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;position:sticky;top:calc(76px + env(safe-area-inset-top,0px));z-index:8;background:#fff;padding:8px 0 10px}"
        ".code{display:block;width:100%;min-height:min(62vh,720px);height:62vh;padding:12px;border:2px solid #145bb0;border-radius:8px;background:#fffef8;font:13px/1.45 Consolas,ui-monospace,monospace;color:#19324d}</style>"
        + ("" if not jump else (
            "<script>(function(){var ta=document.getElementById('texsrc');if(!ta)return;var line="+str(jump)+";"
            "var lines=(ta.value||'').split('\\n');var n=Math.min(Math.max(1,line),Math.max(1,lines.length));"
            "var pos=0;for(var i=0;i<n-1;i++)pos+=lines[i].length+1;"
            "var end=pos+((lines[n-1]||'').length);"
            "try{ta.focus();ta.setSelectionRange(pos,end);}catch(e){}"
            "var cs=getComputedStyle(ta);var lh=parseFloat(cs.lineHeight);if(!lh||lh!==lh)lh=parseFloat(cs.fontSize)*1.45||20;"
            "ta.scrollTop=Math.max(0,(n-4)*lh);})();</script>"
        ))
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
import lythuyet  # noqa: E402,F401
import student_gemini  # noqa: E402,F401
import admin_classify  # noqa: E402,F401
import admin_slim  # noqa: E402,F401
import admin_rewrite  # noqa: E402,F401
import live_present  # noqa: E402,F401
try:
    import membership as _membership  # noqa: F401
    _membership.attach_routes()
    import admin_overrides as _admin_overrides  # noqa: F401
    import student_overrides as _student_overrides  # noqa: F401
    import security_patch as _security_patch  # noqa: F401
except Exception:
    pass

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
