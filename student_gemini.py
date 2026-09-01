# -*- coding: utf-8 -*-
"""Student-provided Gemini key endpoint.
The student's key is sent from the browser for one request only; it is not stored on the server.
"""
from __future__ import annotations

import html as html_lib
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


def _plain(s) -> str:
    """Đổi HTML của trang làm bài về văn bản thuần, giữ nguyên công thức LaTeX."""
    t = str(s or '')
    t = re.sub(r'<img[^>]*>', ' [hình vẽ — AI không nhìn thấy] ', t, flags=re.I)
    t = re.sub(r'<br\s*/?>', '\n', t, flags=re.I)
    t = re.sub(r'</(?:p|div|li|tr|table|ul|ol)>', '\n', t, flags=re.I)
    t = re.sub(r'</?t[dh][^>]*>', ' | ', t, flags=re.I)
    t = re.sub(r'<[^>]+>', '', t)
    t = html_lib.unescape(t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    return t.strip()


def _student_picks(kind: str, student: str, count: int) -> list[str]:
    """Tách bài làm thành lựa chọn của từng ý: DS là chuỗi Đ/S, TN là một chữ cái."""
    s = str(student or '').strip()
    if kind == 'DS':
        marks = [c for c in s.upper() if c in 'ĐDS']
        return [('ĐÚNG' if m in 'ĐD' else 'SAI') for m in marks][:count]
    return [s]


def _answer_key(kind: str, statements: list, options: list, answer: str) -> str:
    if kind == 'DS' and statements:
        return ', '.join(f"{i+1}-{'Đ' if s.get('correct') else 'S'}" for i, s in enumerate(statements))
    if kind == 'TN' and options:
        return ', '.join(chr(65 + i) for i, o in enumerate(options) if o.get('correct'))
    return str(answer or '')


def _kind_rules(kind: str, statements: list, options: list, key: str) -> str:
    if kind == 'DS':
        n = len(statements) or 4
        return (
            f"YÊU CẦU RIÊNG CHO CÂU ĐÚNG/SAI (câu này có {n} ý):\n"
            f"- BẮT BUỘC phân tích đủ cả {n} ý theo thứ tự, không được bỏ ý nào, kể cả ý học sinh làm đúng.\n"
            "- Mỗi ý viết thành một đoạn riêng, bắt đầu đúng bằng \"Ý i)\" theo mẫu: \"Ý i) Đáp án: Đúng/Sai — học sinh chọn Đúng/Sai: đúng/sai. Lý do: ...\" kèm lập luận hoặc tính toán cụ thể, không nói chung chung.\n"
            "- Chữ đúng hoặc sai ngay trước \"Lý do\" là kết luận học sinh làm ĐÚNG hay SAI ý đó (không phải đáp án chuẩn). Không gộp nhiều ý trong một đoạn.\n"
            f"- Dòng cuối cùng bắt buộc ghi đúng chuỗi: \"ĐÁP ÁN ĐÚNG: {key}\" kèm số ý học sinh làm đúng trên {n}."
        )
    if kind == 'TN':
        n = len(options) or 4
        return (
            f"YÊU CẦU RIÊNG CHO CÂU TRẮC NGHIỆM ({n} phương án):\n"
            f"- BẮT BUỘC xét lần lượt cả {n} phương án: phương án đúng thì chứng minh vì sao đúng; mỗi phương án sai phải chỉ rõ sai ở đâu (sai công thức, sai đơn vị, nhầm dữ kiện, bẫy thường gặp...).\n"
            "- Nói rõ học sinh đã chọn phương án nào, phương án đó đúng hay sai và vì sao học sinh dễ chọn nhầm như vậy.\n"
            f"- Dòng cuối cùng bắt buộc ghi: \"ĐÁP ÁN ĐÚNG: {key}. <nội dung ngắn gọn của phương án đó>\"."
        )
    if kind == 'TLN':
        return (
            "YÊU CẦU RIÊNG CHO CÂU TRẢ LỜI NGẮN:\n"
            "- Trình bày đủ các bước tính dẫn tới con số cuối cùng, nêu rõ đơn vị và cách làm tròn.\n"
            "- So sánh con số của học sinh với đáp án chuẩn, chỉ rõ sai ở bước nào nếu lệch.\n"
            "- Dòng cuối cùng bắt buộc ghi: \"ĐÁP ÁN ĐÚNG: <giá trị kèm đơn vị>\"."
        )
    return (
        "YÊU CẦU RIÊNG CHO CÂU TỰ LUẬN:\n"
        "- Nêu dàn ý chấm theo từng bước và điểm mấu chốt của mỗi bước.\n"
        "- Đối chiếu bài làm của học sinh với dàn ý đó, chỉ rõ phần thiếu.\n"
        "- Dòng cuối cùng bắt buộc ghi: \"KẾT LUẬN: <kết quả cuối cùng>\"."
    )


def _build_prompt(data: dict) -> str:
    kind = str(data.get('kind') or '').upper()
    options = [o for o in (data.get('options') or []) if isinstance(o, dict)]
    statements = [s for s in (data.get('statements') or []) if isinstance(s, dict)]
    student = str(data.get('student') or '')
    picks = _student_picks(kind, student, len(statements))
    chosen = picks[0].strip().upper() if kind == 'TN' and picks else ''
    option_text = '\n'.join(
        f"{chr(65+i)}. {_plain(o.get('text',''))}"
        f" → Đáp án chuẩn: {'ĐÚNG' if o.get('correct') else 'SAI'}"
        f"{' ← HỌC SINH CHỌN Ý NÀY' if chosen == chr(65+i) else ''}"
        for i, o in enumerate(options)
    )
    statement_text = '\n'.join(
        f"Ý {i+1}) {_plain(s.get('text',''))}"
        f" → Đáp án chuẩn: {'ĐÚNG' if s.get('correct') else 'SAI'}"
        f" | Học sinh chọn: {picks[i] if i < len(picks) else 'chưa chọn'}"
        for i, s in enumerate(statements)
    )
    text = _plain(data.get('text', ''))
    solution = _plain(data.get('solution', ''))
    key = _answer_key(kind, statements, options, data.get('answer', ''))
    figure_note = (
        "\nLƯU Ý: câu này có hình vẽ mà bạn KHÔNG nhìn thấy. Hãy dựa vào lời giải chuẩn và dữ kiện chữ, tuyệt đối không bịa số liệu đọc từ hình.\n"
        if '[hình vẽ' in text or '[hình vẽ' in solution else ''
    )
    return f"""Bạn là AI trợ giảng Toán/Vật lý THPT. Nhiệm vụ của bạn là PHẢN BIỆN CHÍNH XÁC MỘT CÂU HỎI dựa trên toàn bộ dữ liệu được cung cấp: câu hỏi, các phương án/nhận định, đáp án chuẩn, lời giải chuẩn và bài làm của học sinh.
{figure_note}
{_kind_rules(kind, statements, options, key)}

Dạng bài: {data.get('dang','')}
Loại câu: {data.get('kind','')}
Mức độ: {data.get('level','')}

=== CÂU HỎI ===
{text}

=== CÁC PHƯƠNG ÁN TRẮC NGHIỆM (NẾU CÓ) ===
{option_text}

=== CÁC Ý ĐÚNG/SAI (NẾU CÓ) ===
{statement_text}

=== ĐÁP ÁN CHUẨN ===
{key or '(xem lời giải chuẩn bên dưới)'}

=== BÀI LÀM CỦA HỌC SINH ===
{student or '(học sinh chưa trả lời)'}

=== LỜI GIẢI CHUẨN ===
{solution}

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
- PHẢI viết trọn vẹn tới dòng đáp án cuối cùng, không được bỏ dở giữa chừng. Nếu sợ dài thì rút gọn phần PHÂN TÍCH ĐỀ và LỖI DỄ NHẦM, nhưng không được thiếu ý nào cần phân tích.
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


def _gemini_call(api_key: str, prompt: str, max_tokens: int, temperature: float, no_thinking: bool):
    model = _model_name('gemini-2.5-flash')
    url = 'https://generativelanguage.googleapis.com/v1beta/models/' + urllib.parse.quote(model, safe='-_.') + ':generateContent?key=' + urllib.parse.quote(api_key, safe='')
    cfg = {'temperature': temperature, 'maxOutputTokens': max_tokens}
    if no_thinking:
        # Token suy nghĩ của 2.5-flash tính chung vào maxOutputTokens nên dễ ăn hết phần trả lời.
        cfg['thinkingConfig'] = {'thinkingBudget': 0}
    req = urllib.request.Request(
        url,
        data=json.dumps({'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': cfg}, ensure_ascii=False).encode('utf-8'),
        method='POST',
        headers={'Content-Type': 'application/json', 'User-Agent': 'luyen-de-vat-ly-student-gemini'},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        obj = json.loads(r.read().decode('utf-8'))
    cands = obj.get('candidates') or []
    text = ''.join(
        p.get('text', '')
        for c in cands for p in (c.get('content', {}) or {}).get('parts', []) or []
        if isinstance(p, dict)
    ).strip()
    finish = str((cands[0].get('finishReason') if cands else '') or '')
    return text, finish


def _gemini_generate(api_key: str, prompt: str, max_tokens: int = 6000, temperature: float = 0.15) -> str:
    try:
        text, finish = _gemini_call(api_key, prompt, max_tokens, temperature, True)
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        # Model cũ không nhận thinkingConfig thì gọi lại theo cách thường.
        text, finish = _gemini_call(api_key, prompt, max_tokens, temperature, False)
    if finish == 'MAX_TOKENS':
        longer, finish2 = _gemini_call(api_key, prompt, max_tokens * 2, temperature, True)
        if len(longer) > len(text):
            text, finish = longer, finish2
        if finish == 'MAX_TOKENS' and text:
            text += '\n\n(⚠️ Phần phản biện bị cắt vì quá dài — hãy bấm Phản biện lại để xem tiếp.)'
    return text


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
            text = _gemini_generate(api_key, prompt, 6000, 0.15)
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
