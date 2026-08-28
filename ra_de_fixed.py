# -*- coding: utf-8 -*-
"""Compatibility wrapper for ra_de.py.
Dua \dangbt{} nam ngay truoc \begin{ex}/\begin{bt} vao trong block truoc khi parse,
de parser nhan dung 'Dang bai tap' tu ngan hang hien tai.
"""
import re
import ra_de as _base

_original_parse = _base._parse_tex

def _parse_tex_fixed(text, path):
    # Trong ngan hang, \dangbt{} thuong nam truoc \begin{ex}; parser cu chi tim trong block.
    text = re.sub(
        r'(\\dangbt\s*\{.*?\})\s*(\\begin\{(?:ex|bt)\})',
        r'\2\n\1',
        text,
        flags=re.S,
    )
    return _original_parse(text, path)

_base._parse_tex = _parse_tex_fixed
_base._load_lesson.cache_clear()

bp = _base.bp
