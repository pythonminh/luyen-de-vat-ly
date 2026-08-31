# -*- coding: utf-8 -*-
"""Small add-on routes for opening one exercise type at a time.
Loaded by wsgi.py so the stable app.py remains untouched.
"""
from __future__ import annotations

import html
import urllib.parse

from flask import request

from app import app, can_access, member_current, page, parse_questions, read_tex


def _esc_attr(s: str) -> str:
    return html.escape(str(s), quote=True)


@app.get('/member/dang')
def member_dang():
    m = member_current()
    if not m:
        return __import__('flask').redirect('/member/login')

    path = request.args.get('path', '')
    dang = request.args.get('dang', '').strip()
    if not path or not dang:
        return __import__('flask').redirect('/member')
    if not can_access(m, path):
        return page('Bài VIP', "<div class='wrap'><div class='panel'><div class='body'><div class='err'>🔒 Bài này dành cho VIP.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")

    try:
        _, tex = read_tex(path)
        qs = parse_questions(tex)
    except Exception as exc:
        return page('Lỗi', "<div class='wrap'><div class='panel'><div class='body'><div class='err'>" + html.escape(str(exc)) + "</div></div></div></div>")

    selected = [q for q in qs if q.get('dang') == dang]
    if not selected:
        return page('Dạng bài', "<div class='wrap'><div class='panel'><div class='body'><div class='err'>Không tìm thấy dạng bài này trong TEX.</div><a class='btn' href='/member'>← Mục lục</a></div></div></div>")

    # Keep the original question-index used by /member/start.
    dang_names = []
    seen = set()
    for q in qs:
        name = q.get('dang') or 'Chưa phân dạng'
        if name not in seen:
            seen.add(name)
            dang_names.append(name)
    di = dang_names.index(dang)

    rows = []
    for kind, label in [('TN', 'Trắc nghiệm'), ('DS', 'Đúng / Sai'), ('TLN', 'Trả lời ngắn'), ('TL', 'Tự luận')]:
        counts = {lev: sum(1 for q in selected if q.get('kind') == kind and q.get('level') == lev) for lev in 'NHVC'}
        inputs = ''.join(
            f"<input class='n' type='number' min='0' max='{counts[z]}' value='0' name='pick:{di}:{kind}:{z}' title='Tối đa {counts[z]} câu'>"
            for z in 'NHVC'
        )
        rows.append(
            '<tr>'
            f'<td><b>{html.escape(dang)}</b></td>'
            f'<td>{label}</td>'
            f"<td class='stock'>{counts['N']}/{counts['H']}/{counts['V']}/{counts['C']}</td>"
            f'<td>{inputs}</td>'
            f"<td><span class='tag'>{sum(counts.values())} câu</span></td>"
            '</tr>'
        )

    title = str(path.rsplit('/', 1)[-2] if '/' in path else path)
    body = (
        "<div class='wrap'><div class='panel'>"
        "<div class='head'>📌 Dạng bài đang chọn</div>"
        "<div class='body'>"
        f"<div class='notice'><b>{html.escape(title)}</b> · {html.escape(dang)} · <b>{len(selected)} câu</b></div>"
        "<form method='post' action='/member/start'>"
        f"<input type='hidden' name='path' value='{_esc_attr(path)}'>"
        "<div class='selectwrap'><table class='selectgrid'>"
        "<tr><th>Dạng bài</th><th>Loại</th><th>Kho N/H/V/C</th><th>Chọn N/H/V/C</th><th>Tổng</th></tr>"
        + ''.join(rows)
        + "</table></div>"
        "<div id='sum' class='notice' style='margin-top:10px'>TỔNG CHỌN: 0 câu</div>"
        "<button class='btn primary' type='submit'>▶ Làm dạng này</button> "
        "<a class='btn' href='/member'>← Mục lục</a>"
        "</form></div></div></div>"
        "<script>function upd(){let t=0;document.querySelectorAll('.n').forEach(x=>{let m=Number(x.max)||0,v=Math.max(0,Math.min(m,Number(x.value)||0));x.value=v;t+=v});document.getElementById('sum').textContent='TỔNG CHỌN: '+t+' câu'}document.querySelectorAll('.n').forEach(x=>x.addEventListener('input',upd));upd()</script>"
    )
    return page('Chọn dạng bài', body)


@app.after_request
def make_dang_rows_clickable(response):
    # Only enhance the member catalog HTML. The existing backend remains unchanged.
    content_type = response.headers.get('Content-Type', '')
    if '/member' not in request.path or 'text/html' not in content_type:
        return response
    try:
        body = response.get_data(as_text=True)
        if "class='dangrow'" not in body or '/member/select?path=' not in body:
            return response
        script = r'''<script>
document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.card').forEach(function(card){
    const open = card.querySelector("a[href^='/member/select?path=']");
    if(!open) return;
    const u = new URL(open.href, location.origin);
    const path = u.searchParams.get('path') || '';
    card.querySelectorAll('.dangrow').forEach(function(row){
      const nameEl = row.querySelector('span');
      if(!nameEl) return;
      const name = nameEl.textContent.trim();
      const a = document.createElement('a');
      a.className = 'dangrow danglink';
      a.href = '/member/dang?path=' + encodeURIComponent(path) + '&dang=' + encodeURIComponent(name);
      a.innerHTML = row.innerHTML;
      row.replaceWith(a);
    });
  });
  const st = document.createElement('style');
  st.textContent = '.danglink{color:inherit;text-decoration:none!important;cursor:pointer}.danglink:hover{background:#eef7ff}.danglink:after{content:"  ›";color:#176bd3;font-weight:900}';
  document.head.appendChild(st);
});
</script>'''
        response.set_data(body.replace('</body>', script + '</body>'))
    except Exception:
        pass
    return response
