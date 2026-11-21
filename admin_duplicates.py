"""ADMIN duplicate overview: filtered lesson review; all writes use existing per-lesson route."""
import html
import urllib.parse
from collections import defaultdict
from flask import request, redirect
from app import app, can_manage_bank, index_data, merge_catalog_lessons, parse_lesson_questions, find_duplicate_groups, page

def esc(s): return html.escape(str(s or ''), quote=True)
def qs_url(**params): return '/admin/duplicates?' + urllib.parse.urlencode({k:v for k,v in params.items() if v})
def select(name, values, chosen, title):
    opts = ["<option value=''>"+esc(title)+"</option>"]
    opts += ["<option value='"+esc(v)+"'"+(" selected" if v == chosen else "")+">"+esc(v)+"</option>" for v in values]
    return "<select name='"+name+"' onchange='this.form.submit()'>"+''.join(opts)+"</select>"
def item_title(r): return str(r.get('BaiHoc') or r.get('De') or '').strip()
def drop_key(q):
    src = str(q.get('src') or '').replace('\\','/')
    idx = q.get('file_idx')
    if idx is None: idx = q.get('idx')
    return src+'||'+str(int(idx or 0))
def card(q):
    parts = ["<strong>"+esc(q.get('id') or 'Câu')+"</strong> · "+esc(q.get('kind'))+" · "+esc(q.get('dang'))]
    for k in ('text', 'options', 'answer', 'solution'):
        v = q.get(k)
        if v:
            if isinstance(v, (tuple, list)): v=' | '.join(map(str,v))
            parts.append("<div><small>"+esc({'text':'Đề','options':'Lựa chọn','answer':'Đáp án','solution':'Lời giải'}[k])+":</small> "+esc(str(v)[:1600])+"</div>")
    parts.append("<div class='muted'>TEX: "+esc(q.get('src'))+"</div>")
    return "<div class='dquestion'>"+''.join(parts)+"</div>"

@app.get('/admin/duplicates')
def admin_duplicates_dashboard():
    if not can_manage_bank(): return redirect('/admin/login')
    lessons = merge_catalog_lessons([r for r in index_data().get('lessons',[]) if isinstance(r,dict)])
    lessons = [r for r in lessons if str(r.get('path') or r.get('file') or '').startswith('ngan-hang/') and item_title(r)]
    mon = request.args.get('mon','').strip()
    lop = request.args.get('lop','').strip()
    chuong = request.args.get('chuong','').strip()
    path = request.args.get('path','').strip()
    mons = sorted({str(r.get('Mon') or '') for r in lessons if r.get('Mon')})
    a = [r for r in lessons if not mon or str(r.get('Mon')) == mon]
    lops = sorted({str(r.get('Lop') or '') for r in a if r.get('Lop')})
    b = [r for r in a if not lop or str(r.get('Lop')) == lop]
    chapters = sorted({str(r.get('Chuong') or '') for r in b if r.get('Chuong')})
    c = [r for r in b if not chuong or str(r.get('Chuong')) == chuong]
    allowed = {str(r.get('path') or r.get('file') or ''):r for r in c}
    if path and path not in allowed: path=''
    opts = ["<option value=''>Chọn bài học</option>"]
    opts += ["<option value='"+esc(p)+"'"+(" selected" if p==path else "")+">"+esc(item_title(r))+"</option>" for p,r in sorted(allowed.items(),key=lambda item:item_title(item[1]))]
    form = "<form class='dupfilters' method='get'>"+select('mon',mons,mon,'Tất cả môn')+select('lop',lops,lop,'Tất cả lớp')+select('chuong',chapters,chuong,'Tất cả chương')+"<select name='path' onchange='this.form.submit()'>"+''.join(opts)+"</select><button class='btn primary'>🔎 Kiểm tra bài</button></form>"
    intro = "<h2>🧹 Quản lý câu trùng · Toàn ngân hàng</h2><p>Chọn Lớp → Môn → Chương → Bài để kiểm tra. Danh mục lấy từ ngân hàng hiện hành; chỉ đọc TEX của bài đã chọn (kể cả nhiều file TEX). Câu cùng dạng khác số liệu cần giữ lại để luyện đổi số.</p>"
    main = "<p class='notice'>Chưa chọn bài. Không xóa tự động trên toàn ngân hàng.</p>"
    if path:
        try:
            questions = parse_lesson_questions(path)
            groups = find_duplicate_groups(questions)
            hard = [g for g in groups if g.get('type') == 'dao']
            review = [g for g in groups if g.get('type') != 'dao']
            back = qs_url(mon=mon,lop=lop,chuong=chuong,path=path)
            main = "<div class='notice'>Bài: <b>"+esc(item_title(allowed[path]))+"</b> · "+str(len(questions))+" câu · "+str(len(hard))+" nhóm trùng chắc chắn · "+str(len(review))+" nhóm cùng đề cần xem lại</div>"
            if groups:
                form_start = "<form id='duplicateDeleteForm' method='post' action='/admin/delete-questions' onsubmit=\"var n=this.querySelectorAll('input[name=drop]:checked').length;return n>0&&this.confirm.value==='yes'&&confirm('Xóa '+n+' câu khỏi TEX? Các câu giữ lại sẽ không bị xóa.');\">"
                form_start += "<input type='hidden' name='path' value='"+esc(path)+"'><input type='hidden' name='next' value='"+esc('/member/dang?path='+urllib.parse.quote(path,safe=''))+"'>"
                shown = set()
                blocks=[]
                for i,g in enumerate(hard+review,1):
                    is_exact = g.get('type')=='dao'
                    members = g.get('members') or []
                    keep = g.get('keep')
                    left = next((q for q in members if q.get('idx')==keep),members[0] if members else {})
                    extras = [q for q in members if q.get('idx')!=left.get('idx')]
                    cells = ["<div class='dupgroup'><h3>"+str(i)+". "+('Trùng chắc chắn' if is_exact else 'Cùng đề, cần đối chiếu đáp án')+"</h3><div class='duppair'><div><b>✅ Giữ bản tốt nhất</b>"+card(left)+"</div><div><b>🔍 Bản cần so sánh</b>"]
                    for q in extras:
                        key = drop_key(q)
                        cells.append(card(q))
                        if key not in shown:
                            shown.add(key)
                            cells.append("<label class='dupcheck'><input type='checkbox' name='drop' value='"+esc(key)+"' "+('' if not is_exact else "data-exact='1'")+"> Chọn xóa câu này "+('· trùng chắc chắn' if is_exact else '· cần duyệt thủ công')+"</label>")
                    cells.append("</div></div></div>")
                    blocks.append(''.join(cells))
                main += form_start+"<div class='dupbar'><button type='button' class='btn' onclick=\"document.querySelectorAll('#duplicateDeleteForm input[data-exact]').forEach(x=>x.checked=true)\">✓ Chọn trùng chắc chắn</button><button type='button' class='btn' onclick=\"document.querySelectorAll('#duplicateDeleteForm input[name=drop]').forEach(x=>x.checked=false)\">Bỏ chọn</button><label><input type='checkbox' name='confirm' value='yes'> Tôi đã xem lại danh sách</label><button class='btn red' type='submit'>🗑 Xóa hàng loạt theo bài</button></div>"+''.join(blocks)+"</form>"
            else: main += "<p class='notice'>Chưa phát hiện nhóm trùng có cùng nội dung đề trong bài này. Câu gần giống nhưng khác số liệu vẫn nên kiểm tra thủ công.</p>"
            main += "<p><a class='btn' href='/member/dang?path="+urllib.parse.quote(path,safe='')+"'>Mở bài và kiểm tra câu gần giống →</a></p>"
        except Exception as exc:
            main = "<div class='err'>Không thể đọc dữ liệu của bài đã chọn: "+esc(str(exc))+"</div>"
    style = """<style>.dupfilters{display:flex;flex-wrap:wrap;gap:9px;margin:15px 0}.dupfilters select{min-width:155px;max-width:100%;flex:1;padding:11px;border:1px solid #c4d1e1;border-radius:9px;background:white}.dupbar{position:sticky;top:64px;z-index:2;background:#fff9e9;padding:14px;display:flex;gap:9px;flex-wrap:wrap;align-items:center;border:1px solid #efcf83;border-radius:12px}.dupgroup{margin:15px 0;padding:14px;border:1px solid #cbd8e6;border-radius:13px;background:white}.duppair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.dquestion{border:1px solid #d9e1ea;border-radius:9px;margin:9px 0;padding:11px;overflow-wrap:anywhere;white-space:pre-wrap}.dquestion div{margin-top:6px}.dquestion small{font-weight:700}.dupcheck{display:block;background:#fff7e8;padding:9px;border-radius:7px;margin-bottom:8px}@media(max-width:700px){.duppair{grid-template-columns:1fr}.dupbar{position:static}}</style>"""
    return page('ADMIN · Quản lý câu trùng',"<div class='wrap'><div class='panel'><div class='body'>"+intro+form+main+"</div></div></div>"+style)

@app.after_request
def show_duplicates_admin_entry(response):
    if request.path not in ('/admin','/member') or not can_manage_bank() or 'text/html' not in response.headers.get('Content-Type',''): return response
    try:
        content = response.get_data(as_text=True)
        link = "<div style='margin:12px'><a class='btn primary' href='/admin/duplicates'>🧹 Quản lý câu trùng toàn ngân hàng</a></div>"
        if '/admin/duplicates' not in content:
            pos = content.find('<main')
            if pos >= 0:
                end=content.find('>',pos)
                content=content[:end+1]+link+content[end+1:]
            elif '<body' in content:
                end=content.find('>',content.find('<body'))
                content=content[:end+1]+link+content[end+1:]
            response.set_data(content)
    except Exception: pass
    return response
