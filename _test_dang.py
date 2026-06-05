# Quick test for effective_dang — run: python _test_dang.py
# V78: cột J=Đúng sai + đáp án Đ,S,Đ,S phải ra Đúng sai
import re
import unicodedata
from typing import Any, Dict, List

def strip_accents(s):
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def clean(v):
    return str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()

def key_norm(s):
    s = strip_accents(str(s or "").strip().lower())
    s = re.sub(r"\s+", " ", s)
    return s.replace("_", " ").replace("-", " ").strip()

def norm_dang(s):
    k = key_norm(s)
    k2 = k.replace(" ", "")
    if (
        "dung sai" in k
        or "dungsai" in k2
        or "d/s" in k2
        or re.search(r"\b(ds|tf)\b", k)
        or "true false" in k
        or "truefalse" in k2
    ):
        return "Đúng sai"
    if any(x in k for x in ["tra loi ngan", "short", "tln", "shortans"]):
        return "Trả lời ngắn"
    if any(x in k for x in ["tu luan", "essay"]) or k == "tl":
        return "Tự luận"
    if any(x in k for x in ["trac nghiem", "tracnghiem", "mcq", "multiple choice"]) or k in ("tn", "tn4"):
        return "Trắc nghiệm"
    return "Trắc nghiệm"

def _tf_token_to_ds(token):
    t = clean(token)
    if not t:
        return ""
    if t.upper() in ("Đ", "D"):
        return "Đ"
    if t.upper() == "S":
        return "S"
    k = key_norm(t)
    if k in ["d", "đ", "dung", "đung", "đúng", "true", "t"]:
        return "Đ"
    if k in ["s", "sai", "false", "f"]:
        return "S"
    return ""

def parse_tf_values(value):
    if isinstance(value, list):
        out = [_tf_token_to_ds(v) for v in value]
        while len(out) < 4:
            out.append("")
        return out[:4]
    raw = clean(value)
    if not raw:
        return ["", "", "", ""]
    low = strip_accents(raw).lower()
    letter_hits = re.findall(
        r"(?:^|[\s;,|]+)(?:[\[\(]?\s*([abcd])\s*[\]\)]?\s*[-.:=]?\s*)"
        r"(đúng|dung|d|đ|sai|s|true|false)\b",
        low,
        re.I,
    )
    if len(letter_hits) >= 2:
        mp = {"a": 0, "b": 1, "c": 2, "d": 3}
        out = ["", "", "", ""]
        for letter, word in letter_hits:
            idx = mp.get(clean(letter).lower())
            if idx is None:
                continue
            tok = _tf_token_to_ds(word)
            if tok:
                out[idx] = tok
        if sum(1 for x in out if x) >= 2:
            return out
    parts = re.split(r"[,;|/\n]+", raw)
    if len(parts) >= 2:
        out = [_tf_token_to_ds(p) for p in parts]
        if sum(1 for x in out if x) >= 2:
            while len(out) < 4:
                out.append("")
            return out[:4]
    s = strip_accents(raw).upper()
    s = s.replace("\u0110", "D").replace("\u0111", "D")
    s = s.replace("DUNG", "D").replace("TRUE", "D").replace("SAI", "S").replace("FALSE", "S")
    vals = re.findall(r"[DS]", s)[:4]
    out = ["Đ" if v == "D" else "S" for v in vals]
    while len(out) < 4:
        out.append("")
    return out[:4]

def looks_like_dungsai_answer(value):
    if value is None or not clean(value):
        return False
    raw = strip_accents(clean(value).upper()).strip()
    if re.fullmatch(r"[ABCD]", raw):
        return False
    vals = parse_tf_values(value)
    filled = [v for v in vals if v in ("Đ", "S")]
    return len(filled) >= 2

def has_tf_statements(q):
    return sum(1 for L in "ABCD" if clean(q.get(L))) >= 2

def is_mcq_letter_answer(value):
    raw = strip_accents(clean(value).upper()).strip()
    return bool(re.fullmatch(r"[ABCD]", raw))

def effective_dang(q):
    raw_col = clean(q.get("Dang", ""))
    dang_col = norm_dang(raw_col)
    dapan = q.get("DapAn")
    has_opts = has_tf_statements(q)
    if dang_col == "Đúng sai":
        return "Đúng sai"
    if dang_col == "Trả lời ngắn":
        return "Trả lời ngắn"
    if dang_col == "Tự luận":
        return "Tự luận"
    if looks_like_dungsai_answer(dapan) and has_opts:
        return "Đúng sai"
    if is_mcq_letter_answer(dapan) and has_opts:
        return "Trắc nghiệm"
    if raw_col:
        return dang_col
    return "Trắc nghiệm"

base = {"A": "stmt A", "B": "stmt B", "C": "stmt C", "D": "stmt D"}
cases = [
    ({"Dang": "Trắc nghiệm", "DapAn": "D", **base}, "Trắc nghiệm"),
    ({"Dang": "Trắc nghiệm", "DapAn": "SSĐĐ", **base}, "Đúng sai"),
    ({"Dang": "Trắc nghiệm", "DapAn": "S;S;Đ;Đ", **base}, "Đúng sai"),
    ({"Dang": "Đúng sai", "DapAn": "SSĐĐ", **base}, "Đúng sai"),
    ({"Dang": "", "DapAn": "B", **base}, "Trắc nghiệm"),
    ({"Dang": "", "DapAn": "Đúng,Sai,Sai,Đúng", **base}, "Đúng sai"),
    ({"Dang": "Đúng sai", "DapAn": "Đ,S,Đ,S", **base}, "Đúng sai"),
    ({"Dang": "Trắc nghiệm", "DapAn": "Đ,S,Đ,S", **base}, "Đúng sai"),
]
for q, exp in cases:
    got = effective_dang(q)
    ok = "OK" if got == exp else "FAIL"
    print(ok, q["Dang"], q["DapAn"], "->", got)
