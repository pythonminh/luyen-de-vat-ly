# -*- coding: utf-8 -*-
"""Student-provided Gemini key endpoint.
The student's key is sent from the browser for one request only; it is not stored on the server.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

from flask import request, jsonify
from app import app, practice_current


def _model_name(s: str) -> str:
    s = (s or "gemini-2.5-flash").strip()
    s = re.sub(r"^models/", "", s)
    return s or "gemini-2.5-flash"


def _build_prompt(data: dict) -> str:
    return f"""Bạn là trợ giảng Vật lý/Toán trung học phổ thông. Hãy phản biện bài làm của học sinh dựa đúng vào dữ liệu được cung cấp.

Dạng bài: {data.get('dang','')}
Loại câu: {data.get('kind','')}
Mức độ: {data.get('level','')}

CÂU HỎI:
{data.get('text','')}

TRẢ LỜI CỦA HỌC SINH:
{data.get('student','')}

LỜI GIẢI GỐC TRONG TEX:
{data.get('solution','')}

Yêu cầu phản biện:
1. Kết luận học sinh đúng hay sai hoặc phần nào đúng/sai.
2. Chỉ ra chính xác chỗ sai nếu có.
3. Giải thích ngắn gọn, dễ hiểu.
4. Nêu cách làm đúng.
5. Không tự thay đổi nội dung câu hỏi.
Trả lời bằng tiếng Việt, trình bày rõ ràng."""


@app.post('/api/gemini/review_student')
def gemini_review_student():
    m = practice_current()
    if not m:
        return jsonify(ok=False, error='Chưa đăng nhập'), 401

    data = request.get_json(silent=True) or {}
    api_key = str(data.get('api_key') or '').strip()
    if not api_key:
        return jsonify(ok=False, error='Chưa nhập Gemini API key.'), 400
    if len(api_key) < 20:
        return jsonify(ok=False, error='Gemini API key có vẻ không hợp lệ.'), 400

    model = _model_name(str(data.get('model') or 'gemini-2.5-flash'))
    url = 'https://generativelanguage.googleapis.com/v1beta/models/' + urllib.parse.quote(model, safe='-_.') + ':generateContent?key=' + urllib.parse.quote(api_key, safe='')
    payload = {
        'contents': [{'parts': [{'text': _build_prompt(data)}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 1200},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        method='POST',
        headers={'Content-Type': 'application/json', 'User-Agent': 'luyen-de-vat-ly-student-gemini'},
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            obj = json.loads(r.read().decode('utf-8'))
        text = ''.join(p.get('text', '') for c in obj.get('candidates', []) for p in c.get('content', {}).get('parts', []) if isinstance(p, dict)).strip()
        if not text:
            return jsonify(ok=False, error='Gemini không trả về nội dung phản biện.'), 502
        return jsonify(ok=True, text=text)
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            msg = json.loads(raw).get('error', {}).get('message', raw)
        except Exception:
            msg = raw
        return jsonify(ok=False, error=f'Gemini {e.code}: {msg}'), 400 if e.code in (400,401,403) else 502
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 502
