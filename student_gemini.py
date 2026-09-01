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
from app import app, member_current


def _model_name(s: str) -> str:
    s = (s or "gemini-2.5-flash").strip()
    s = re.sub(r"^models/", "", s)
    return s or "gemini-2.5-flash"


def _build_prompt(data: dict) -> str:
    options = data.get('options') or []
    statements = data.get('statements') or []
    option_text = '\n'.join(
        f"{chr(65+i)}. {o.get('text','')} {'[ĐÚNG]' if o.get('correct') else '[SAI]'}"
        for i, o in enumerate(options) if isinstance(o, dict)
    )
    statement_text = '\n'.join(
        f"{i+1}. {s.get('text','')} {'[ĐÚNG]' if s.get('correct') else '[SAI]'}"
        for i, s in enumerate(statements) if isinstance(s, dict)
    )
    return f"""Bạn là AI trợ giảng Toán/Vật lý THPT. Nhiệm vụ của bạn là PHẢN BIỆN CHÍNH XÁC MỘT CÂU HỎI dựa trên toàn bộ dữ liệu được cung cấp: câu hỏi, các phương án/nhận định, đáp án chuẩn, lời giải chuẩn và bài làm của học sinh.

Dạng bài: {data.get('dang','')}
Loại câu: {data.get('kind','')}
Mức độ: {data.get('level','')}

=== CÂU HỎI ===
{data.get('text','')}

=== CÁC PHƯƠNG ÁN TRẮC NGHIỆM (NẾU CÓ) ===
{option_text}

=== CÁC NHẬN ĐỊNH ĐÚNG/SAI (NẾU CÓ) ===
{statement_text}

=== ĐÁP ÁN CHUẨN ===
{data.get('answer','')}

=== TRẢ LỜI CỦA HỌC SINH ===
{data.get('student','')}

=== LỜI GIẢI CHUẨN ===
{data.get('solution','')}

Hãy tạo một KỊCH BẢN GIẢI THÍCH hoàn chỉnh, giống nhận xét trực tiếp của một giáo viên, theo đúng thứ tự:
1. PHÂN TÍCH ĐỀ: xác định dữ kiện, đại lượng cần tìm, điều kiện và ý tưởng/công thức cần dùng.
2. ĐÁP ÁN VÀ ĐỐI CHIẾU: nêu đáp án chuẩn; đối chiếu chính xác với bài làm của học sinh.
3. NHẬN ĐỊNH ĐÚNG/SAI: kết luận rõ RÀNG ĐÚNG, SAI hoặc ĐÚNG MỘT PHẦN. Nếu là câu Đúng/Sai, phải nhận xét từng nhận định.
4. GIẢI THÍCH: trình bày suy luận và các bước giải cần thiết, không bỏ qua bước quan trọng. Nếu học sinh sai, chỉ đúng vị trí sai và cách sửa.
5. KẾT QUẢ: viết lại kết quả cuối cùng thật rõ. Trắc nghiệm: nêu chữ cái và nội dung phương án đúng. Đúng/Sai: nêu từng nhận định Đúng/Sai. Trả lời ngắn: nêu giá trị cuối cùng và đơn vị.
6. LỖI DỄ NHẦM: chỉ ra 1-3 lỗi/bẫy phù hợp với chính câu hỏi.

QUY TẮC BẮT BUỘC:
- Chỉ dùng dữ kiện được cung cấp; tuyệt đối không tự bịa dữ kiện.
- Lời giải chuẩn và đáp án chuẩn là nguồn đối chiếu chính. Nếu có mâu thuẫn giữa câu hỏi, đáp án và lời giải, phải nói rõ mâu thuẫn thay vì đoán.
- Không được tự đổi đáp án chuẩn.
- Không chỉ trả lời "đúng" hoặc "sai"; phải giải thích nguyên nhân.
- Công thức Toán/Vật lý phải viết bằng LaTeX tương thích MathJax: công thức trong dòng dùng \\( ... \\), công thức riêng dòng dùng \\[ ... \\].
- Không đặt công thức trong code block Markdown.
- Ưu tiên các lệnh LaTeX đơn giản, chuẩn và dễ đọc: \\frac, \\sqrt, ^{{ }}, _{{ }}, \\mathrm{{ }}, \\vec{{ }}. Không dùng ký hiệu Unicode thay cho công thức nếu LaTeX phù hợp.
- Số, đơn vị, số mũ, phân số, căn, vectơ và ký hiệu vật lý phải rõ ràng để MathJax hiển thị tốt và có thể dùng cho công cụ đọc công thức.
- Văn bản tiếng Việt tự nhiên, ngắn gọn nhưng đủ bước; không dùng bảng Markdown.
- Không tiết lộ API key trong câu trả lời.

Chỉ dùng các tiêu đề sau:
PHÂN TÍCH ĐỀ
ĐÁP ÁN VÀ ĐỐI CHIẾU
NHẬN ĐỊNH ĐÚNG/SAI
GIẢI THÍCH
KẾT QUẢ
LỖI DỄ NHẦM"""


def _keys_from_payload(data: dict) -> list[str]:
    keys = []
    raw = data.get('api_keys') if isinstance(data.get('api_keys'), list) else []
    for item in raw:
        s = str(item or '').strip()
        if s and len(s) >= 20 and s not in keys:
            keys.append(s)
    one = str(data.get('api_key') or '').strip()
    if one and len(one) >= 20 and one not in keys:
        keys.insert(0, one)
    return keys


def _gemini_generate(api_key: str, prompt: str, max_tokens: int = 2200, temperature: float = 0.15) -> str:
    model = _model_name('gemini-2.5-flash')
    url = 'https://generativelanguage.googleapis.com/v1beta/models/' + urllib.parse.quote(model, safe='-_.') + ':generateContent?key=' + urllib.parse.quote(api_key, safe='')
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        method='POST',
        headers={'Content-Type': 'application/json', 'User-Agent': 'luyen-de-vat-ly-student-gemini'},
    )
    with urllib.request.urlopen(req, timeout=35) as r:
        obj = json.loads(r.read().decode('utf-8'))
    return ''.join(p.get('text', '') for c in obj.get('candidates', []) for p in c.get('content', {}).get('parts', []) if isinstance(p, dict)).strip()


@app.post('/api/gemini/review_student')
def gemini_review_student():
    m = member_current()
    if not m:
        return jsonify(ok=False, error='Chưa đăng nhập'), 401

    data = request.get_json(silent=True) or {}
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error='Chưa nhập Gemini API key. Lấy tại https://aistudio.google.com/apikey'), 400

    prompt = _build_prompt(data)
    last_err = 'Gemini không trả về nội dung phản biện.'
    for i, api_key in enumerate(keys, 1):
        try:
            text = _gemini_generate(api_key, prompt, 2200, 0.15)
            if text:
                return jsonify(ok=True, text=text, used_key=i)
            last_err = f'Key {i}: Gemini không trả về nội dung.'
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', 'replace')
            try:
                msg = json.loads(raw).get('error', {}).get('message', raw)
            except Exception:
                msg = raw
            last_err = f'Key {i}: Gemini {e.code}: {msg}'
            if e.code not in (400, 401, 403, 429) and i == len(keys):
                return jsonify(ok=False, error=last_err), 502
        except Exception as e:
            last_err = f'Key {i}: {e}'
    return jsonify(ok=False, error=last_err), 502

@app.post('/api/gemini/ping')
def gemini_ping():
    m = member_current()
    if not m:
        return jsonify(ok=False, error='Chưa đăng nhập'), 401
    data = request.get_json(silent=True) or {}
    keys = _keys_from_payload(data)
    if not keys:
        return jsonify(ok=False, error='Chưa nhập Gemini API key. Lấy tại https://aistudio.google.com/apikey'), 400
    lines = []
    ok_any = False
    for i, api_key in enumerate(keys, 1):
        try:
            text = _gemini_generate(api_key, 'Trả lời đúng một câu tiếng Việt: Key Gemini hoạt động tốt.', 40, 0)
            if text:
                ok_any = True
                lines.append(f'Key {i}: OK — {text[:80]}')
            else:
                lines.append(f'Key {i}: Gemini không trả lời.')
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', 'replace')
            try:
                msg = json.loads(raw).get('error', {}).get('message', raw)
            except Exception:
                msg = raw
            lines.append(f'Key {i}: lỗi {e.code} — {msg}')
        except Exception as e:
            lines.append(f'Key {i}: {e}')
    return jsonify(ok=ok_any, text='\n'.join(lines))
