# -*- coding: utf-8 -*-
"""Robust ADMIN question-save shim.

Keeps the existing SheetStore as the source of truth, but avoids the fragile
create handler on cold-start/slow-store conditions and adds client-side retry.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict

from flask import jsonify

from app import app, get_store, is_admin, require_login_json

try:
    from app import questions_store_ready_or_loading
except Exception:
    questions_store_ready_or_loading = None

try:
    from app import validate_ai_generated_questions_for_save
except Exception:
    validate_ai_generated_questions_for_save = None


_TRANSIENT_WORDS = (
    "loading", "chưa nạp", "đang nạp", "timeout", "timed out",
    "temporarily", "busy", "bận", "503", "502", "504"
)


def _is_transient(exc: Exception) -> bool:
    s = str(exc or "").lower()
    return any(x in s for x in _TRANSIENT_WORDS)


def _normalize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data or {})
    # Chỉ ép các trường cơ bản; không đụng nội dung LaTeX/TikZ của thầy.
    for k in list(out):
        if out[k] is None:
            out[k] = ""
        elif not isinstance(out[k], (str, int, float, bool)):
            out[k] = str(out[k])
    if not str(out.get("Dang") or "").strip():
        out["Dang"] = "Trắc nghiệm"
    if not str(out.get("QuyenTruyCap") or "").strip():
        out["QuyenTruyCap"] = "VIP"
    return out


def _ready_store():
    if questions_store_ready_or_loading is not None:
        st, loading = questions_store_ready_or_loading()
        if loading:
            return None, loading
        return st, None
    st = get_store()
    st.ensure_questions_loaded()
    return st, None


@app.route("/api/question/create-fixed", methods=["POST"])
def api_question_create_fixed():
    bad = require_login_json()
    if bad:
        return bad
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được thêm câu hỏi"}), 403

    body = request_json()
    raw = body.get("data") or body.get("question") or body
    data = _normalize_data(raw if isinstance(raw, dict) else {})

    if not str(data.get("CauHoi") or "").strip():
        return jsonify({"error": "Phải nhập nội dung câu hỏi (CauHoi)."}), 400

    last_error = ""
    for attempt in range(3):
        try:
            st, loading = _ready_store()
            if loading is not None:
                # Frontend sẽ tự retry; giữ 503 để phân biệt với lỗi dữ liệu.
                return loading
            result = st.add_question(data)
            result["save_path"] = "Google Sheet Cau_Hoi"
            result["fixed_handler"] = True
            return jsonify(result)
        except Exception as exc:
            last_error = str(exc)
            if attempt >= 2 or not _is_transient(exc):
                break
            time.sleep(1.0 * (attempt + 1))

    return jsonify({
        "error": last_error or "Không lưu được câu hỏi.",
        "fixed_handler": True,
        "retryable": _is_transient(Exception(last_error)),
    }), 503 if _is_transient(Exception(last_error)) else 400


@app.route("/api/admin/ai-generate-save-fixed", methods=["POST"])
def api_admin_ai_generate_save_fixed():
    bad = require_login_json()
    if bad:
        return bad
    if not is_admin():
        return jsonify({"error": "Chỉ ADMIN được lưu câu hỏi AI."}), 403

    body = request.get_json(silent=True) or {}
    items = body.get("questions") or body.get("items") or []
    if validate_ai_generated_questions_for_save is not None:
        items = validate_ai_generated_questions_for_save(items)

    if not isinstance(items, list) or not items:
        return jsonify({"error": "Không có câu hỏi hợp lệ để lưu."}), 400

    last_error = ""
    for attempt in range(3):
        try:
            st, loading = _ready_store()
            if loading is not None:
                return loading
            result = st.add_questions_bulk(items)
            result["source"] = "AI_GENERATOR"
            result["fixed_handler"] = True
            return jsonify(result)
        except Exception as exc:
            last_error = str(exc)
            if attempt >= 2 or not _is_transient(exc):
                break
            time.sleep(1.0 * (attempt + 1))

    return jsonify({
        "error": last_error or "Không lưu được câu AI.",
        "fixed_handler": True,
        "retryable": _is_transient(Exception(last_error)),
    }), 503 if _is_transient(Exception(last_error)) else 400


def request_json():
    try:
        return globals().get("request").get_json(silent=True) or {}
    except Exception:
        # Import trễ để tránh thay đổi boot-time.
        from flask import request
        return request.get_json(silent=True) or {}


@app.after_request
def inject_question_save_fix(response):
    """Intercept only ADMIN add/save buttons; existing edit path is untouched."""
    try:
        if response.content_type and "text/html" in response.content_type:
            text = response.get_data(as_text=True)
            if "data-ldvl-question-save-fix=\"1\"" not in text:
                script = r'''
<script data-ldvl-question-save-fix="1">
(function(){
  if(window.__LDVL_QUESTION_SAVE_FIX__)return;
  window.__LDVL_QUESTION_SAVE_FIX__=true;
  function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
  async function postJson(url, body){
    let last='';
    for(let i=0;i<5;i++){
      try{
        const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
        const t=await r.text();
        let j={};try{j=JSON.parse(t)}catch(_){j={error:t||('HTTP '+r.status)}}
        if(r.ok)return j;
        last=String(j.error||('HTTP '+r.status));
        if(r.status!==429 && r.status!==502 && r.status!==503 && r.status!==504 && !/loading|chưa nạp|đang nạp|timeout|bận/i.test(last))throw new Error(last);
      }catch(e){
        last=String(e&&e.message||e||'');
        if(i>=4)throw new Error(last);
      }
      await sleep(1200*(i+1));
    }
    throw new Error(last||'Không lưu được.');
  }
  async function fixedAdd(){
    if(window.__LDVL_FIXED_ADD_BUSY__)return;
    if(typeof readQuestionFormData!=='function'){alert('Không đọc được biểu mẫu câu hỏi.');return;}
    const data=readQuestionFormData();
    if(!String(data.CauHoi||'').trim()){alert('Phải nhập nội dung câu hỏi.');return;}
    window.__LDVL_FIXED_ADD_BUSY__=true;
    const btn=document.getElementById('btnSaveQuestion');
    if(btn){btn.disabled=true;btn.textContent='⏳ Đang lưu…';}
    try{
      const j=await postJson('/api/question/create-fixed',{data:data});
      let nq=(typeof applyResolvedDang==='function')?applyResolvedDang(j.question||{}):(j.question||{});
      if(!nq._row)nq._row=j.row;
      if(Array.isArray(QUESTIONS)){
        let at=Math.min((typeof CUR==='number'?CUR:QUESTIONS.length-1)+1,QUESTIONS.length);
        QUESTIONS.splice(Math.max(0,at),0,nq);
        if(typeof insertQuizMaps==='function')insertQuizMaps(Math.max(0,at));
        if(typeof CUR==='number')CUR=typeof regroupQuestionsByDang==='function'?regroupQuestionsByDang(nq._row):Math.min(at,QUESTIONS.length-1);
      }
      if(typeof closeEdit==='function')closeEdit();
      if(typeof renderNav==='function')renderNav();
      if(typeof renderQuestion==='function')renderQuestion();
      if(typeof refreshCatalogFromMeta==='function')await refreshCatalogFromMeta();
      alert('✅ Đã lưu câu mới vào Google Sheet dòng '+(j.row||'?')+(j.id?'\nID: '+j.id:''));
    }catch(e){alert('❌ Không lưu được câu hỏi: '+(e.message||e));}
    finally{window.__LDVL_FIXED_ADD_BUSY__=false;if(btn){btn.disabled=false;btn.textContent='Lưu vào Google Sheet';}}
  }
  async function fixedAiSave(){
    if(window.__LDVL_FIXED_AI_SAVE_BUSY__)return;
    if(typeof AI_GEN_QUESTIONS==='undefined' || !Array.isArray(AI_GEN_QUESTIONS) || !AI_GEN_QUESTIONS.length){alert('Chưa có câu để lưu.');return;}
    window.__LDVL_FIXED_AI_SAVE_BUSY__=true;
    const btn=document.getElementById('agSaveBtn');if(btn){btn.disabled=true;btn.textContent='⏳ Đang lưu…';}
    const st=document.getElementById('agStatus');let created=0,skipped=[];
    try{
      for(let i=0;i<AI_GEN_QUESTIONS.length;i++){
        if(st)st.textContent='⏳ Đang lưu câu '+(i+1)+'/'+AI_GEN_QUESTIONS.length+'…';
        const j=await postJson('/api/admin/ai-generate-save-fixed',{questions:[AI_GEN_QUESTIONS[i]]});
        created+=Number(j.created||0);
        if(Array.isArray(j.skipped))skipped=skipped.concat(j.skipped);
      }
      if(st)st.textContent='✅ Đã lưu '+created+' câu'+(skipped.length?' · bỏ qua '+skipped.length:'')+'.';
      window.AI_GEN_SAVED=true;
      if(typeof refreshCatalogFromMeta==='function')await refreshCatalogFromMeta();
      if(typeof renderCatalog==='function')renderCatalog();
      alert('✅ Đã lưu '+created+' câu vào Google Sheet.'+(skipped.length?'\nBỏ qua '+skipped.length+' câu trùng/không hợp lệ.':''));
    }catch(e){if(st)st.textContent='❌ '+(e.message||e);alert('❌ Lưu câu AI thất bại: '+(e.message||e));}
    finally{window.__LDVL_FIXED_AI_SAVE_BUSY__=false;if(btn){btn.disabled=false;btn.textContent='💾 Lưu tất cả vào Google Sheet';}}
  }
  document.addEventListener('click',function(ev){
    const t=ev.target&&ev.target.closest?ev.target.closest('#btnSaveQuestion'):null;
    if(t && typeof QUESTION_MODAL_MODE!=='undefined' && QUESTION_MODAL_MODE==='add'){
      ev.preventDefault();ev.stopImmediatePropagation();fixedAdd();return;
    }
    const a=ev.target&&ev.target.closest?ev.target.closest('#agSaveBtn'):null;
    if(a){ev.preventDefault();ev.stopImmediatePropagation();fixedAiSave();return;}
  },true);
})();
</script>
'''
                i = text.lower().rfind('</body>')
                text = text[:i] + script + text[i:] if i >= 0 else text + script
                response.set_data(text)
    except Exception:
        pass
    return response
'''}