# -*- coding: utf-8 -*-
"""Restyle lớp giao diện GitHub để đồng bộ với giao diện luyện đề chính.
Chỉ tác động /github/quan-ly, không đụng giao diện học sinh.
Nguồn dữ liệu vẫn là GitHub bank_index.json + ngan-hang/*.tex.
"""
from flask import request
from app import app

STYLE = r'''
<style id="LDVL_GITHUB_RESTYLE_V1">
:root{--ld-blue:#1769d2;--ld-blue2:#edf5ff;--ld-ink:#17324d;--ld-line:#d9e3ee;--ld-bg:#f4f7fb;--ld-muted:#64748b}
body{background:var(--ld-bg)!important;color:var(--ld-ink)!important;font-family:Inter,Segoe UI,Arial,sans-serif!important}
.page{max-width:1500px!important;margin:0 auto!important;padding:0 14px 46px!important}
.top{position:sticky!important;top:0!important;z-index:100!important;background:linear-gradient(90deg,#1769d2,#2588df)!important;border-radius:0 0 12px 12px!important;box-shadow:0 4px 16px #0d4f9d33!important}
.topRow{min-height:64px!important;padding:9px 16px!important;gap:14px!important}
.brand{font-size:21px!important;font-weight:900!important}.brandSub{font-size:11px!important}
.subjects{display:flex!important;gap:6px!important}.subject{border:1px solid #ffffff55!important;background:#ffffff15!important;color:#fff!important;border-radius:14px!important;padding:8px 15px!important;font-weight:900!important}.subject.active{background:#fff!important;color:#1557a6!important}
.right{margin-left:auto!important;display:flex!important;gap:6px!important}.topBtn{border:1px solid #ffffff44!important;background:#ffffff12!important;color:#fff!important;border-radius:9px!important;padding:8px 10px!important}
.strip{background:#eaf3ff!important;color:#17558f!important;border-bottom:1px solid #c6dcf5!important;padding:8px 16px!important;font-size:12px!important}
.card{background:#fff!important;border:1px solid var(--ld-line)!important;border-radius:16px!important;box-shadow:0 3px 14px #17324d0b!important}
.filters{padding:13px!important;grid-template-columns:1.55fr repeat(6,1fr)!important;gap:8px!important}
.field label{font-size:11px!important;font-weight:900!important;color:#526174!important}.field input,.field select{padding:9px!important;border-radius:9px!important}
.intro{margin:11px 0!important;padding:12px 14px!important;border:1px solid #c8def9!important;border-radius:16px!important;background:linear-gradient(180deg,#eff6ff,#fff)!important}
.introTitle{font-size:16px!important;font-weight:950!important;color:#1d4386!important}.stat{padding:4px 9px!important;border:1px solid #bdd7f7!important;background:#fff!important;color:#1d4ed8!important;border-radius:999px!important;font-size:11px!important;font-weight:900!important}
.subjectBlock{margin:12px 0 16px!important}.subjectHead{padding:11px 13px!important;border-radius:14px!important;background:linear-gradient(90deg,#1d4ed8,#60a5fa)!important;color:#fff!important;font-size:17px!important;font-weight:950!important}
.grade{margin:10px 0!important;border:1px solid #cbd7e4!important;border-radius:15px!important;overflow:hidden!important}.gradeHead{padding:9px 12px!important;background:#f1f5f9!important;font-weight:950!important}
.chapter{margin:9px!important;border:1px solid #bdd9fa!important;border-radius:13px!important;background:#f8fbff!important}.chapterHead{padding:9px 11px!important;background:#dbeafe!important;color:#1e3a8a!important;font-weight:950!important}
.lessonGrid{padding:9px!important;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))!important;gap:9px!important}.lesson{border:1px solid #e0e8ef!important;border-radius:13px!important;padding:10px!important;background:#fff!important;box-shadow:0 1px 3px #0f172a0b!important}
.lessonTitle{font-weight:950!important;color:#0f172a!important}.lesson .sub{font-size:11px!important;color:#64748b!important}.chip{font-size:10px!important;padding:4px 7px!important;border-radius:999px!important}.actions{margin-top:8px!important}.mini{border:1px solid #93c5fd!important;background:#eff6ff!important;color:#1d4ed8!important;border-radius:8px!important;padding:6px 9px!important;font-size:11px!important;font-weight:900!important}.mini.green{background:#eaf8ef!important;color:#166534!important;border-color:#86efac!important}
.split{grid-template-columns:340px minmax(0,1fr)!important;gap:11px!important}.sidebar{border-radius:16px!important}.panelTitle{padding:12px 14px!important;background:#f8fbff!important}.qItem{border:1px solid #dfe7ef!important;border-radius:10px!important;padding:9px!important;margin:6px 0!important}.qItem.active,.qItem:hover{background:#edf5ff!important;border-color:#83b6e9!important}
.editor{padding:15px!important}.editorTitle{font-size:20px!important;font-weight:950!important}.meta{gap:8px!important}.code{min-height:570px!important;border-radius:10px!important;background:#fcfdff!important}
@media(max-width:1050px){.filters{grid-template-columns:1fr 1fr!important}.filters .searchWide{grid-column:1/-1!important}.split{grid-template-columns:1fr!important}.sidebar{max-height:360px!important}.lessonGrid{grid-template-columns:1fr!important}}
@media(max-width:640px){.brand{font-size:17px!important}.brandSub,.right{display:none!important}.subjects{margin-left:auto!important}.filters{grid-template-columns:1fr!important}.meta{grid-template-columns:1fr!important}}
</style>'''


def inject(response):
    try:
        if not request.path.startswith('/github/quan-ly'):
            return response
        if not (response.content_type and 'text/html' in response.content_type):
            return response
        text=response.get_data(as_text=True)
        if 'LDVL_GITHUB_RESTYLE_V1' in text:
            return response
        low=text.lower(); i=low.rfind('</head>')
        if i>=0:
            text=text[:i]+STYLE+text[i:]
            response.set_data(text)
    except Exception:
        pass
    return response

app.after_request(inject)
