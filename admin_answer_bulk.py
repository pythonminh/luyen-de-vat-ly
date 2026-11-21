# -*- coding: utf-8 -*-
"""Read-only quality audit and review-first AI completion of missing answer/solution."""
from __future__ import annotations
import hashlib
import html
import json
import re
import secrets
import threading
import time
import urllib.parse
from flask import jsonify, request, redirect
import app as base

_BLOCK = re.compile(r"\\begin\s*\{\s*(?:ex|bt)\s*\}[\s\S]*?\\end\s*\{\s*(?:ex|bt)\s*\}", re.I)
_JOBS = {}
_LOCK = threading.RLock()
_TTL = 1200


def _authorized_path(path):
    path = str(path or "").replace("\\", "/").strip()
    if not path.startswith("ngan-hang/") or ".." in path.split("/"):
        raise ValueError("Đường dẫn bài không hợp lệ")
    return path


def _filename(q, lesson):
    return str(q.get("src") or lesson).replace("\\", "/")


def _file_index(q):
    return int(q.get("file_idx") if q.get("file_idx") is not None else q.get("idx"))


def _inner_solution(raw):
    match = re.search(r"\\loigiai\s*\{", raw, re.I)
    if match:
        content, _ = base.get_braced(raw, match.end() - 1)
        return (content or "").strip() if content is not None else ""
    match = re.search(r"\\begin\s*\{\s*loigiai\s*\}([\s\S]*?)\\end\s*\{\s*loigiai\s*\}", raw, re.I)
    return match.group(1).strip() if match else ""


def _answer_state(raw, kind):
    if kind == "TN":
        return bool(re.search(r"\\True\b", raw))
    if kind == "TLN":
        match = re.search(r"\\shortans\s*(?:\[[^\]]*\])?\s*\{", raw, re.I)
        if not match:
            return False
        value, _ = base.get_braced(raw, match.end() - 1)
        return bool((value or "").strip())
    # Đ/S can legitimately have all four statements false; do not mark absent True as missing.
    return True


def _scan(path):
    questions = base.parse_lesson_questions(path)
    file_cache = {}
    items = []
    for q in questions:
        src = _filename(q, path)
        if not src.startswith("ngan-hang/") or not src.endswith(".tex"):
            continue
        if src not in file_cache:
            sha, tex = base.read_tex(src, need_sha=True)
            blocks = list(_BLOCK.finditer(tex))
            parsed = base.parse_questions(tex)
            if len(blocks) != len(parsed):
                raise ValueError("Không khớp số câu trong " + src)
            file_cache[src] = dict(sha=sha, tex=tex, blocks=blocks)
        rec = file_cache[src]
        idx = _file_index(q)
        if idx < 0 or idx >= len(rec["blocks"]):
            continue
        raw = rec["blocks"][idx].group()
        kind = str(q.get("kind") or "")
        missing_answer = not _answer_state(raw, kind)
        missing_solution = not bool(_inner_solution(raw))
        if missing_answer or missing_solution:
            items.append(dict(key=src+"||"+str(idx), src=src, idx=idx,
                id=str(q.get("id") or ""), kind=kind,
                text=str(q.get("text") or "")[:1800],
                options=q.get("options") or [],
                missing_answer=missing_answer, missing_solution=missing_solution,
                fingerprint=hashlib.sha256(raw.encode("utf-8")).hexdigest()))
    return items, file_cache


def _prompt(items):
    lines = []
    for i, q in enumerate(items):
        opts = q.get("options") or []
        if isinstance(opts, list):
            opts = json.dumps(opts, ensure_ascii=False, default=str)[:1900]
        lines.append(
            "n="+str(i)+"; loại="+q["kind"]+"; ID="+q["id"]+
            "; cần đáp án="+str(q["missing_answer"])+
            "; cần lời giải="+str(q["missing_solution"])+
            "; đề="+q["text"]+"; lựa chọn="+str(opts)
        )
    return (
        "Bạn là giáo viên Toán/Vật lí THPT. CHỈ BỔ SUNG phần còn thiếu cho câu sau; "
        "không sửa đề, phương án, dạng, mức độ, hình và dữ kiện. "
        "Tự giải độc lập, không đoán nếu câu thiếu dữ kiện hoặc nhiều đáp án. "
        "Nếu không chắc thì bỏ câu khỏi kết quả. "
        "TN: answer là A/B/C/D; TLN: answer chỉ số tối đa 4 ký tự, dùng dấu phẩy thập phân; "
        "DS: nếu cần, answer là chuỗi bốn kí tự Đ/S (có thể toàn S). "
        "Lời giải dùng LaTeX hợp lệ trong \\loigiai, không viết \\begin{ex}, \\end{ex}, "
        "không thêm \\loigiai lồng và không dùng Markdown. "
        "Trả JSON duy nhất {\"items\":[{\"n\":0,\"answer\":\"B\",\"solution\":\"...\"}]}, "
        "escape đúng backslash LaTeX theo JSON. Không bịa dữ kiện. "
        "Mỗi lời giải nêu công thức hoặc lập luận cụ thể, không chép lời giải chung.\n"
        + "\n".join(lines)
    )


def _parse_ai(raw):
    from admin_rewrite import _repair_json_latex
    raw = str(raw or "").strip()
    fenced = re.search(r"\x60\x60\x60(?:json)?\s*([\s\S]*?)\x60\x60\x60", raw, re.I)
    if fenced:
        raw = fenced.group(1)
    a, b = raw.find("{"), raw.rfind("}")
    if a < 0 or b < a:
        return []
    for value in (raw[a:b+1], _repair_json_latex(raw[a:b+1])):
        try:
            obj = json.loads(value)
            if isinstance(obj, dict) and isinstance(obj.get("items"), list):
                return obj["items"]
        except (ValueError, TypeError):
            pass
    return []


def _ai_job(job, items, keys):
    from admin_classify import _gemini_once
    try:
        result = []
        for offset in range(0, len(items), 6):
            group = items[offset:offset+6]
            raw, error = _gemini_once(keys, _prompt(group), max_tokens=6000)
            if not raw:
                raise ValueError(error or "AI không trả nội dung")
            suggestions = _parse_ai(raw)
            for entry in suggestions:
                if not isinstance(entry, dict):
                    continue
                try:
                    n = int(entry["n"])
                except (KeyError, TypeError, ValueError):
                    continue
                if not 0 <= n < len(group):
                    continue
                q = group[n]
                solution = str(entry.get("solution") or "").strip()
                answer = str(entry.get("answer") or "").strip()
                if q["missing_solution"] and not solution:
                    continue
                if q["missing_answer"]:
                    if q["kind"] == "TN" and answer.upper() not in "ABCD":
                        continue
                    if q["kind"] == "TLN" and (not answer or len(answer)>4):
                        continue
                result.append(dict(key=q["key"], id=q["id"], kind=q["kind"],
                    answer=answer if q["missing_answer"] else "",
                    solution=solution if q["missing_solution"] else "",
                    missing_answer=q["missing_answer"], missing_solution=q["missing_solution"]))
            with _LOCK:
                _JOBS[job]["done"] = min(offset + len(group), len(items))
                _JOBS[job]["results"] = result
        with _LOCK:
            _JOBS[job]["state"] = "complete"
    except Exception as exc:
        with _LOCK:
            _JOBS[job]["state"] = "error"
            _JOBS[job]["error"] = str(exc)[:500]
    finally:
        # No credentials are stored in the job record.
        keys.clear()


@base.app.get("/admin/answer-audit")
def admin_answer_audit():
    if not base.can_manage_bank():
        return redirect("/admin/login")
    path = str(request.args.get("path") or "").strip()
    if not path:
        return base.page("Kiểm tra đáp án", "<main class='wrap'><p>Hãy mở bài trong ngân hàng và bấm Kiểm tra đáp án/lời giải.</p></main>")
    try:
        path = _authorized_path(path)
        items, _ = _scan(path)
    except Exception as exc:
        return base.page("Lỗi kiểm tra", "<main class='wrap'><div class='err'>"+html.escape(str(exc))+"</div></main>")
    rows = []
    for q in items:
        status = ("Thiếu đáp án · " if q["missing_answer"] else "") + ("Thiếu lời giải" if q["missing_solution"] else "")
        rows.append("<label class='auditrow'><input type='checkbox' class='auditpick' value='"+html.escape(q["key"],quote=True)+"' checked>"
            +"<span><b>"+html.escape(q["id"] or ("Câu "+str(q["idx"]+1)))+"</b> · "+html.escape(q["kind"])+" · <b>"+html.escape(status)+"</b>"
            +"<small>"+html.escape(q["text"][:240])+"</small></span></label>")
    path_json = json.dumps(path,ensure_ascii=False).replace("<","\\u003c")
    script = r"""
<script>
(function(){
 const PATH=__PATH__, $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
 let job='', results=[];
 $('all').onclick=()=>document.querySelectorAll('.auditpick').forEach(x=>x.checked=true);
 $('none').onclick=()=>document.querySelectorAll('.auditpick').forEach(x=>x.checked=false);
 $('generate').onclick=async()=>{
  const selected=[...document.querySelectorAll('.auditpick:checked')].map(x=>x.value);
  if(!selected.length)return alert('Chọn câu cần xử lý.');
  const keys=window.ldvlFilledKeys?window.ldvlFilledKeys():[];
  if(!keys.length)return alert('Nạp Gemini API key trước khi sử dụng AI.');
  $('generate').disabled=true;$('status').textContent='Đang chuẩn bị xử lý '+selected.length+' câu...';
  try{
   const response=await fetch('/api/admin/answer-bulk-start',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({path:PATH,selected,api_keys:keys})});
   const d=await response.json();if(!d.ok)throw Error(d.error||'Không tạo được tác vụ');
   job=d.job;await poll();
  }catch(e){$('status').textContent=e.message||String(e);$('generate').disabled=false;}
 };
 async function poll(){
  try{
   const response=await fetch('/api/admin/answer-bulk-status?job='+encodeURIComponent(job),{credentials:'same-origin'});
   const d=await response.json();if(!d.ok)throw Error(d.error||'Không xem được tiến độ');
   $('status').textContent='AI đã xử lý '+d.done+'/'+d.total+' câu · đề xuất '+d.results.length+' câu.';
   if(d.state==='run'){setTimeout(poll,1700);return;}
   $('generate').disabled=false;
   results=d.results||[];
   if(d.state==='error')$('status').textContent+=' Lỗi: '+(d.error||'Không rõ');
   if(!results.length)return;
   const panel=$('review');panel.innerHTML='';
   const header=document.createElement('p');header.textContent='Kiểm tra đáp án, lời giải từng câu. Chỉ lưu các dòng đã chọn.';panel.append(header);
   results.forEach((r,i)=>{
    const label=document.createElement('label');label.className='auditrow';
    const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.className='approve';checkbox.value=i;
    const box=document.createElement('span'),title=document.createElement('b'),pre=document.createElement('pre');
    title.textContent=(r.id||r.key)+' · '+(r.missing_answer?'Đáp án: '+r.answer+' · ':'')+'Lời giải AI';
    pre.textContent=r.solution||'(Giữ lời giải hiện có)';
    box.append(title,pre);label.append(checkbox,box);panel.append(label);
   });
   $('save').hidden=false;
  }catch(e){$('status').textContent=e.message||String(e);$('generate').disabled=false;}
 }
 $('save').onclick=async()=>{
  const indices=[...document.querySelectorAll('.approve:checked')].map(x=>Number(x.value));
  if(!indices.length)return alert('Chưa duyệt câu nào.');
  if(!confirm('Ghi đáp án/lời giải cho '+indices.length+' câu đã duyệt lên GitHub?'))return;
  $('save').disabled=true;
  try{
   const response=await fetch('/api/admin/answer-bulk-save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify({job,indices})});
   const d=await response.json();if(!d.ok)throw Error(d.error||'Không thể ghi');
   $('status').textContent='Đã lưu '+d.changed+' câu vào '+d.files+' file TEX.';
   $('save').hidden=true;location.reload();
  }catch(e){$('status').textContent=e.message||String(e);$('save').disabled=false;}
 };
})();
</script>""".replace("__PATH__",path_json)
    body=("<main class='wrap'><div class='panel'><div class='body'><h2>Kiểm định đáp án & lời giải · Cả bài</h2>"
        +"<p>Phát hiện <b>"+str(len(items))+"</b> câu thiếu đáp án hoặc lời giải. Chỉ gửi các câu thiếu cho AI; giữ nguyên câu đã đủ."
        +" Đúng/Sai toàn Sai không tự coi là thiếu đáp án. AI chỉ đề xuất, không tự ghi dữ liệu.</p>"
        +"<div class='auditbar'><button id='all' class='btn' type='button'>Chọn tất cả</button> "
        +"<button id='none' class='btn' type='button'>Bỏ chọn</button> "
        +"<button id='generate' class='btn primary' type='button'>AI viết toàn bộ câu đã chọn</button>"
        +"<button id='save' class='btn green' type='button' hidden>Lưu những câu đã duyệt</button></div>"
        +"<p id='status' aria-live='polite'></p><div id='review'></div><div class='audititems'>"+''.join(rows)+"</div>"
        +"</div></div></main>"
        +"<style>.auditbar{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}.audititems{max-height:570px;overflow:auto}"
        +".auditrow{display:flex;gap:10px;align-items:start;border:1px solid #dae3ef;border-radius:9px;padding:11px;margin:7px 0;cursor:pointer}"
        +".auditrow span{min-width:0;flex:1}.auditrow small{display:block;color:#64748b;padding:4px 0}.auditrow pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 monospace;max-height:240px;overflow:auto}</style>"
        +script)
    return base.page("Kiểm định đáp án & lời giải",body)


@base.app.post("/api/admin/answer-bulk-start")
def answer_bulk_start():
    if not base.can_manage_bank():
        return jsonify(ok=False,error="Chỉ ADMIN."),403
    data=request.get_json(silent=True) or {}
    try:
        path=_authorized_path(data.get("path"))
        items, files=_scan(path)
    except Exception as exc:
        return jsonify(ok=False,error=str(exc)),400
    selected=set(str(x) for x in (data.get("selected") or []))
    items=[q for q in items if q["key"] in selected]
    keys=[str(x) for x in (data.get("api_keys") or []) if str(x).strip()]
    if not items or len(items)>500:
        return jsonify(ok=False,error="Chọn 1–500 câu thiếu để xử lý."),400
    if not keys:
        return jsonify(ok=False,error="Thiếu Gemini API key."),400
    job=secrets.token_hex(16)
    snapshots={src:hashlib.sha256(v["tex"].encode("utf-8")).hexdigest() for src,v in files.items()}
    with _LOCK:
        now=time.time()
        for k in list(_JOBS):
            if now-_JOBS[k]["created"]>_TTL:
                _JOBS.pop(k,None)
        _JOBS[job]=dict(created=now,state="run",done=0,total=len(items),
            items={q["key"]:q for q in items},snapshots=snapshots,
            results=[],error="",owner=str(base.admin_current() or "admin"),path=path)
    threading.Thread(target=_ai_job,args=(job,items,keys),daemon=True).start()
    return jsonify(ok=True,job=job)


def _owned_job(job):
    with _LOCK:
        row=_JOBS.get(str(job or ""))
        if not row or time.time()-row["created"]>_TTL:
            return None
        if row["owner"]!=str(base.admin_current() or "admin"):
            return None
        return row


@base.app.get("/api/admin/answer-bulk-status")
def answer_bulk_status():
    if not base.can_manage_bank():
        return jsonify(ok=False,error="Chỉ ADMIN."),403
    j=_owned_job(request.args.get("job"))
    if not j:
        return jsonify(ok=False,error="Phiên xử lý hết hạn. Hãy chạy lại."),404
    with _LOCK:
        return jsonify(ok=True,state=j["state"],done=j["done"],total=j["total"],
            results=j["results"],error=j["error"])


def _mark_answer(inner, kind, answer):
    from admin_rewrite import _replace_shortans
    if kind=="TLN":
        if not answer or len(answer)>4:
            raise ValueError("Đáp án trả lời ngắn không hợp lệ")
        if not re.search(r"\\shortans\s*(?:\[[^\]]*\])?\s*\{",inner,re.I):
            pos=re.search(r"\\loigiai\s*\{|\\end\s*\{\s*(?:ex|bt)\s*\}",inner,re.I)
            if not pos:
                raise ValueError("Không tìm thấy vị trí chèn trả lời ngắn")
            return inner[:pos.start()]+"\\shortans{"+answer+"}\n"+inner[pos.start():]
        return _replace_shortans(inner,answer)
    if kind!="TN":
        return inner
    if answer not in "ABCD" or len(answer)!=1:
        raise ValueError("Đáp án TN không hợp lệ")
    m=re.search(r"\\choice(?!TF)\b",inner,re.I)
    if not m:
        raise ValueError("Câu TN không có \\choice")
    p=m.end()
    locations=[]
    for _ in range(4):
        while p<len(inner) and inner[p].isspace():p+=1
        if p>=len(inner) or inner[p]!="{":
            raise ValueError("Không đọc được 4 phương án")
        val, end=base.get_braced(inner,p)
        if val is None:
            raise ValueError("Ngoặc lựa chọn không khớp")
        locations.append((p,val))
        p=end
    if any(re.search(r"\\True\b",v) for _,v in locations):
        return inner
    begin=locations["ABCD".index(answer)][0]+1
    return inner[:begin]+"\\True "+inner[begin:]


@base.app.post("/api/admin/answer-bulk-save")
def answer_bulk_save():
    if not base.can_manage_bank():
        return jsonify(ok=False,error="Chỉ ADMIN."),403
    data=request.get_json(silent=True) or {}
    jobid=str(data.get("job") or "")
    job=_owned_job(jobid)
    if not job or job["state"]!="complete":
        return jsonify(ok=False,error="AI chưa hoàn thành hoặc phiên hết hạn."),409
    try:
        indices={int(x) for x in (data.get("indices") or [])}
    except (TypeError,ValueError):
        return jsonify(ok=False,error="Danh sách duyệt không hợp lệ."),400
    selected=[x for i,x in enumerate(job["results"]) if i in indices]
    if not selected:
        return jsonify(ok=False,error="Chưa duyệt câu nào."),400
    if not base.github_token():
        return jsonify(ok=False,error="Thiếu GITHUB_TOKEN; không ghi dữ liệu tạm."),503
    grouped={}
    for x in selected:
        original=job["items"].get(x["key"])
        if not original:
            return jsonify(ok=False,error="Câu không thuộc phiên kiểm định."),400
        grouped.setdefault(original["src"],[]).append((original,x))
    planned=[]
    from admin_rewrite import _replace_loigiai
    try:
        # Validate every file and question before any write.
        for src,pairs in grouped.items():
            sha,tex=base.read_tex(src,need_sha=True)
            digest=hashlib.sha256(tex.encode("utf-8")).hexdigest()
            if digest!=job["snapshots"][src]:
                raise ValueError("File đã được sửa sau khi quét: "+src)
            matches=list(_BLOCK.finditer(tex))
            edits={}
            for original,x in pairs:
                idx=original["idx"]
                if idx<0 or idx>=len(matches):
                    raise ValueError("Câu không còn đúng vị trí")
                block=matches[idx].group()
                if hashlib.sha256(block.encode("utf-8")).hexdigest()!=original["fingerprint"]:
                    raise ValueError("Nội dung câu đã thay đổi")
                if original["missing_answer"] and _answer_state(block,original["kind"]):
                    raise ValueError("Câu đã có đáp án")
                if original["missing_solution"] and _inner_solution(block):
                    raise ValueError("Câu đã có lời giải")
                inner=block
                if original["missing_answer"]:
                    inner=_mark_answer(inner,original["kind"],str(x.get("answer") or "").strip().upper() if original["kind"]=="TN" else str(x.get("answer") or "").strip())
                if original["missing_solution"]:
                    solution=str(x.get("solution") or "").strip()
                    if not solution or re.search(r"\\begin\s*\{\s*(?:ex|bt)\s*\}",solution):
                        raise ValueError("Lời giải AI không hợp lệ")
                    if re.search(r"\\loigiai\s*\{|\\begin\s*\{\s*loigiai\s*\}",inner,re.I):
                        inner=_replace_loigiai(inner,solution)
                    else:
                        endmark=re.search(r"\\end\s*\{\s*(?:ex|bt)\s*\}\s*$",inner,re.I)
                        if not endmark:
                            raise ValueError("Không tìm thấy điểm chèn lời giải")
                        inner=inner[:endmark.start()]+"\\loigiai{\n"+solution+"\n}\n"+inner[endmark.start():]
                if not _inner_solution(inner) or (original["missing_answer"] and not _answer_state(inner,original["kind"])):
                    raise ValueError("Câu chưa đủ đáp án/lời giải sau khi sửa")
                edits[idx]=inner
            out=[];cursor=0
            for idx,m in enumerate(matches):
                out.append(tex[cursor:m.start()])
                out.append(edits.get(idx,m.group()))
                cursor=m.end()
            out.append(tex[cursor:])
            new="".join(out)
            if len(list(_BLOCK.finditer(new)))!=len(matches):
                raise ValueError("Số câu thay đổi bất thường")
            planned.append((src,sha,new))
    except Exception as exc:
        return jsonify(ok=False,error=str(exc)),409
    # One user action; one GitHub contents commit for each changed TEX file.
    saved=[]
    for src,sha,new in planned:
        try:
            base.github_put_text(src,new,"ADMIN AI bổ sung đáp án và lời giải: "+src,sha)
            _,local=base._safe_repo_file(src)
            local.parent.mkdir(parents=True,exist_ok=True)
            local.write_text(new,encoding="utf-8")
            saved.append(src)
        except Exception as exc:
            return jsonify(ok=False,error="Đã ghi "+str(len(saved))+" file, lỗi tại "+src+": "+str(exc)),502
    with _LOCK:
        _JOBS.pop(jobid,None)
    try:
        from dang_routes import _STATS_CACHE,_QID_CACHE
        _STATS_CACHE.clear();_QID_CACHE.clear()
    except Exception:
        pass
    return jsonify(ok=True,changed=len(selected),files=len(saved))
