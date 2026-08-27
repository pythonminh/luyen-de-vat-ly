# -*- coding: utf-8 -*-
"""Gói mã tách từ app.py — mỗi file một việc.

Chỉnh giao diện / quiz JS:
  templates/app.html              HTML + CSS + boot sớm
  ldvl/frontend/ldvl-main.js      JS chính (lớp học, đề, ADMIN…)
  templates/login.html
  templates/register.html
  templates/share.html
  templates/json_admin.html
  templates/json_local.html
  templates/choose_source.html

Chỉnh Python:
  ldvl/version.py                 APP_VERSION (đổi khi sửa HTML/JS)
  ldvl/pages.py                   nạp template
  ldvl/debate_prompts.py          prompt phản biện / kịch bản lớp
  app.py                          Flask, SheetStore, AI, route

Gunicorn vẫn: gunicorn app:app
Sau khi sửa JS/CSS: tăng APP_VERSION, restart, Ctrl+F5.
"""
