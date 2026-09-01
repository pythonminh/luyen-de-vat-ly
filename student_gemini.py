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
    return f"""Bạn là AI trợ giảng Toán/Vật lý THPT, có nhiệm vụ PHẢN BIỆN MỘT CÂU HỎI dựa chính xác vào câu hỏi, đáp án chuẩn, lời giải chuẩn và bài làm của học sinh được cung cấp.

Dạng bài: {data.get('dang','')}
Loại câu: {data.get('kind','')}
Mức độ: {data.get('level','')}

=== CÂU HỎI ===
{data.get('text','')}

=== ĐÁP ÁN CHUẨN ===
{data.get('answer','')}

=== TRẢ LỜI CỦA HỌC SINH ===
{data.get('student','')}

=== LỜI GIẢI CHUẨN ===
{data.get('solution','')}

Hãy tạo một KỊCH BẢN GIẢI THÍCH hoàn chỉnh, dễ nghe và dễ hiểu cho học sinh, theo đúng thứ tự:
1. PHÂN TÍCH ĐỀ: xác định dữ kiện, đại lượng cần tìm và ý tưởng/công thức cần dùng.
2. ĐỐI CHIẾU ĐÁP ÁN: nêu rõ đáp án chuẩn và đối chiếu với câu trả lời của học sinh.
3. NHẬN ĐỊNH: kết luận rõ RÀNG ĐÚNG, SAI hoặc ĐÚNG MỘT PHẦN. Nếu sai, chỉ chính xác sai ở đâu và vì sao.
4. GIẢI THÍCH: trình bày cách suy luận và các bước giải cần thiết, không bỏ qua bước quan trọng.
5. KẾT QUẢ: viết lại kết quả cuối cùng thật rõ ràng; với câu trắc nghiệm phải nêu chữ cái/phương án đúng nếu có; với đúng-sai phải nêu từng nhận định Đúng/Sai; với trả lời ngắn phải nêu giá trị cuối cùng và đơn vị nếu có.
6. LỖI DỄ NHẦM: chỉ ra 1-3 lỗi hoặc bẫy mà học sinh dễ mắc nếu phù hợp.

QUY TẮC QUAN TRỌNG:
- Chỉ sử dụng thông tin của đúng câu hỏi được gửi; không tự bịa dữ kiện.
- Lời giải chuẩn là nguồn tham chiếu chính. Nếu dữ liệu mâu thuẫn, hãy nói rõ điểm mâu thuẫn thay vì đoán.
- Không thay đổi đáp án chuẩn.
- Không chỉ nói "đúng/sai"; phải giải thích nguyên nhân.
- Công thức toán và vật lý PHẢI viết bằng LaTeX chuẩn để MathJax hiển thị tốt: dùng \\( ... \\) cho công thức trong dòng và \\[ ... \\] cho công thức riêng dòng. Không dùng Markdown code block cho công thức.
- Không viết công thức bằng Unicode thay cho LaTeX khi có thể dùng LaTeX.
- Đơn vị, số mũ, phân số, căn, vectơ và ký hiệu vật lý phải dùng LaTeX chuẩn.
- Văn bản tiếng Việt rõ ràng, ngắn gọn nhưng đủ bước để có thể dùng làm lời đọc AI.
- Không dùng bảng Markdown.

Trả lời theo các tiêu đề: PHÂN TÍCH ĐỀ; ĐÁP ÁN VÀ ĐỐI CHIẾU; NHẬN ĐỊNH ĐÚNG/SAI; GIẢI THÍCH; KẾT QUẢ; LỖI DỄ NHẦM."""


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
        'generationConfig': {'temperature': 0.15, 'maxOutputTokens': 1800},
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
