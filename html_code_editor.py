"""ADMIN-only source editing of saved HTML exercises, with optimistic locking."""
import json
import re
import secrets

from flask import request, session, jsonify
from app import app


@app.post('/member/html-code')
def html_code():
    import dang_routes as dr
    from app import github_file_sha, github_put_text, _fetch_bytes_remote
    if not dr.can_manage_bank():
        return jsonify(ok=False, error='Chỉ ADMIN được sửa mã HTML.'), 403
    data = request.get_json(silent=True) or {}
    token = session.get('html_practice_csrf')
    if not token or not secrets.compare_digest(str(data.get('csrf') or ''), token):
        return jsonify(ok=False, error='Phiên hết hạn. Tải lại trang.'), 403
    try:
        path = str(data.get('path') or '').strip()
        legacy = dr._html_practice_location(path, str(data.get('dang') or '').strip())
        if not dr.can_view(dr.member_current(), path):
            return jsonify(ok=False, error='Không có quyền xem bài.'), 403
        item = str(data.get('item') or '').strip()
        if item and ('/' in item or '\\' in item or '..' in item or not item.endswith('.html')):
            raise ValueError('Bài HTML không hợp lệ.')
        rel = legacy[:-5] + '/' + item if item else legacy
        action = data.get('action')
        if action not in ('load', 'save'):
            raise ValueError('Thao tác không hợp lệ.')
        sha = github_file_sha(rel)
        if not sha:
            return jsonify(ok=False, error='Không tìm thấy bài HTML.'), 404
        if action == 'load':
            # Read the same immutable Git blob used for the concurrency token.
            import base64
            from app import gh_api
            blob = gh_api('git/blobs/' + sha)
            source = base64.b64decode(blob['content']).decode('utf-8-sig')
            response = jsonify(ok=True, source=source, sha=sha)
        else:
            if not data.get('sha') or not secrets.compare_digest(str(data['sha']), sha):
                return jsonify(ok=False, error='Bài đã được sửa ở nơi khác. Sao chép mã đang sửa rồi tải lại bản mới; chưa ghi đè.'), 409
            source = str(data.get('source') or '')
            if not source.strip() or len(source.encode('utf-8')) > 2 * 1024 * 1024:
                raise ValueError('HTML phải có nội dung và không quá 2 MB.')
            if not re.search(r'<html\b', source, re.I) or not re.search(r'</html\s*>', source, re.I):
                raise ValueError('Cần mã HTML đầy đủ, có thẻ mở và đóng html.')
            github_put_text(rel, source, 'ADMIN chỉnh mã HTML: ' + item[:100], sha)
            _, local = dr._safe_repo_file(rel)
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(source, encoding='utf-8')
            dr._HTML_TITLE_CACHE.clear()
            dr._HTML_LIST_CACHE.clear()
            if hasattr(dr, '_SAVED_HTML_CACHE'):
                dr._SAVED_HTML_CACHE = (0, [])
            response = jsonify(ok=True, message='Đã lưu HTML vào đúng bài hiện tại.')
        response.headers['Cache-Control'] = 'no-store'
        return response
    except ValueError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    except Exception:
        return jsonify(ok=False, error='Không đọc/lưu được GitHub. Mã đang sửa vẫn còn trong ô; hãy sao chép trước khi tải lại.'), 502


def code_editor_html(path, dang, item, csrf):
    config = json.dumps(dict(path=path, dang=dang, item=item, csrf=csrf), ensure_ascii=True).replace('<', '\\u003c')
    return r'''<p><button type="button" id="hpEditCode">✎ Sửa mã HTML</button></p>
<script>(function(){const cfg=CONFIG;let modal,code,preview,status,save,sha='',original='',busy=false;
async function api(action,extra={}){const r=await fetch('/member/html-code',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...cfg,action,...extra})});let d;try{d=await r.json()}catch(e){throw Error('Máy chủ chưa trả về kết quả. Mã đang sửa vẫn được giữ.')}if(!r.ok||!d.ok)throw Error(d.error||'Không thực hiện được');return d}
function dirty(){return code&&code.value!==original}
function close(){if(busy)return;if(dirty()&&!confirm('Đóng và bỏ những thay đổi chưa lưu?'))return;modal.close()}
async function open(){if(!modal){modal=document.createElement('dialog');modal.id='hpCodeModal';modal.innerHTML='<header><strong>Sửa mã HTML · ADMIN</strong><button type="button" data-preview>Chạy thử</button><button type="button" data-save>Lưu vào bài này</button><button type="button" data-close>Đóng</button></header><p role="status" data-status></p><div class="hp-code-panes"><label>Mã HTML<textarea spellcheck="false" autocapitalize="off" autocomplete="off" aria-label="Mã HTML của bài"></textarea></label><iframe title="Chạy thử HTML đang sửa" sandbox="allow-scripts"></iframe></div>';document.body.appendChild(modal);code=modal.querySelector('textarea');preview=modal.querySelector('iframe');status=modal.querySelector('[data-status]');save=modal.querySelector('[data-save]');modal.querySelector('[data-close]').onclick=close;modal.addEventListener('cancel',e=>{e.preventDefault();close()});modal.querySelector('[data-preview]').onclick=()=>{preview.srcdoc=code.value;status.textContent='Đang chạy thử mã trong ô. Chưa lưu.'};save.onclick=async()=>{if(busy||!sha)return;busy=true;save.disabled=true;status.textContent='Đang lưu vào GitHub…';try{await api('save',{sha,source:code.value});original=code.value;status.textContent='Đã lưu. Đang mở lại bài…';location.reload()}catch(e){status.textContent=e.message}finally{busy=false;save.disabled=false}};code.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();save.click()}});modal.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();save.click()}});window.addEventListener('beforeunload',e=>{if(dirty()&&!busy){e.preventDefault();e.returnValue=''}})}
if(!modal.open)modal.showModal();if(sha)return;busy=true;save.disabled=true;status.textContent='Đang lấy mã HTML đã lưu…';try{const d=await api('load');sha=d.sha;original=d.source;code.value=d.source;preview.srcdoc=d.source;status.textContent='Chỉnh mã → Chạy thử → Lưu vào bài này. Lịch sử phiên bản được giữ trên GitHub.'}catch(e){status.textContent=e.message}finally{busy=false;save.disabled=!sha}}
document.getElementById('hpEditCode').onclick=open;const toolbar=document.querySelector('.hp-toolbar');if(toolbar){const b=document.createElement('button');b.type='button';b.textContent='✎ Sửa HTML';b.onclick=open;toolbar.insertBefore(b,document.getElementById('hpManage'))}
})();</script>
<style>#hpCodeModal{position:fixed;inset:0;width:98vw;max-width:none;height:96dvh;max-height:none;padding:0;border:1px solid #cbd5e1;border-radius:12px;background:white;color:#1e293b}#hpCodeModal::backdrop{background:#102746aa}#hpCodeModal header{display:flex;gap:8px;align-items:center;padding:10px;background:#102746;color:white;flex-wrap:wrap}#hpCodeModal header strong{flex:1}#hpCodeModal button{padding:8px 12px;border:1px solid #b9cce0;border-radius:7px;cursor:pointer}#hpCodeModal [data-save]{background:#1761b0;color:white}#hpCodeModal [data-status]{padding:8px 12px;margin:0;font-size:13px;min-height:36px}.hp-code-panes{display:grid;grid-template-columns:1fr 1fr;height:calc(100% - 100px);min-height:0}.hp-code-panes label{display:flex;flex-direction:column;gap:5px;padding:10px;font-size:12px;min-width:0}.hp-code-panes textarea{flex:1;resize:none;min-height:0;width:100%;font:14px/1.5 ui-monospace,Consolas,monospace;white-space:pre;tab-size:2;padding:12px;background:#0f172a;color:#e2e8f0;border:0;border-radius:8px}.hp-code-panes iframe{width:100%;height:100%;border:0;border-left:1px solid #cbd5e1;background:white}@media(max-width:700px){.hp-code-panes{grid-template-columns:1fr;grid-template-rows:1fr 1fr;height:calc(100% - 130px)}#hpCodeModal header strong{flex-basis:100%}.hp-code-panes textarea{font-size:16px}}</style>'''.replace('CONFIG', config)
