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


@app.post('/api/gemini/review_student')
def gemini_review_student():
    m = member_current()
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
        'generationConfig': {'temperature': 0.15, 'maxOutputTokens': 2200},
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
