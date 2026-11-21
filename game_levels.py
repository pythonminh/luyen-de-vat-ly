# -*- coding: utf-8 -*-
"""Game-like practice tiers with exact, inventory-checked NB/TH/VD/VDC mixes."""
from __future__ import annotations

import html
import random
import secrets
import time
import urllib.parse
from collections import Counter

from flask import redirect, request, session
import app as base

app = base.app

# Each mix is for 10 questions; 20 questions doubles the counts exactly.
GAME_TIERS = {
    "easy":   {"name": "Dễ",        "icon": "🌱", "subtitle": "Khởi động",    "units": {"N": 7, "H": 3}},
    "medium": {"name": "Trung bình", "icon": "⚡", "subtitle": "Tăng tốc",      "units": {"N": 2, "H": 3, "V": 5}},
    "hard":   {"name": "Khó",        "icon": "🔥", "subtitle": "Thử thách",     "units": {"N": 1, "H": 2, "V": 3, "C": 4}},
}
LEVEL_LABELS = {"N": "NB", "H": "TH", "V": "VD", "C": "VDC"}
LEVEL_ORDER = ("N", "H", "V", "C")


def game_pools(questions):
    """A question index can only be present once; unknown levels behave as TH."""
    result = {name: [] for name in LEVEL_ORDER}
    used = set()
    for q in questions or []:
        try:
            idx = int(q.get("idx"))
        except (ValueError, TypeError, AttributeError):
            continue
        if idx in used:
            continue
        used.add(idx)
        level = base.norm_muc(q.get("level")) or "H"
        result[level].append(idx)
    return result


def quota(tier, count):
    count = int(count)
    if tier not in GAME_TIERS or count not in (10, 20):
        raise ValueError("Cấp độ hoặc số câu không hợp lệ.")
    return {level: amount * (count // 10) for level, amount in GAME_TIERS[tier]["units"].items()}


def shortages(pools, tier, count):
    planned = quota(tier, count)
    return {level: need - len(pools.get(level, ())) for level, need in planned.items()
            if len(pools.get(level, ())) < need}


def select_questions(questions, tier, count, rng=None):
    """Select exactly the configured mix without replacements or fake ratios."""
    pools = game_pools(questions)
    missing = shortages(pools, tier, count)
    if missing:
        details = ", ".join(f"{LEVEL_LABELS[lv]} thiếu {amount} câu" for lv, amount in missing.items())
        raise ValueError("Ngân hàng chưa đủ câu cho cấp này: " + details + ".")
    rng = rng or random.SystemRandom()
    selected = []
    for level, need in quota(tier, count).items():
        selected.extend(rng.sample(pools[level], need))
    rng.shuffle(selected)
    return selected


def _mix_label(tier, count):
    return " · ".join(
        f"{LEVEL_LABELS[level]} {need}/{count}"
        for level, need in quota(tier, count).items()
    )


def _tier_button(tier, pools):
    config = GAME_TIERS[tier]
    valid10 = not shortages(pools, tier, 10)
    valid20 = not shortages(pools, tier, 20)
    missing10 = shortages(pools, tier, 10)
    missing20 = shortages(pools, tier, 20)
    def missing_text(m):
        if not m:
            return "Đủ câu"
        return "Thiếu " + ", ".join(f"{LEVEL_LABELS[k]} {v}" for k, v in m.items())
    return (
        f'<button type="submit" class="game-tier game-tier-{tier}" name="level" value="{tier}"'
        f' data-valid10="{int(valid10)}" data-valid20="{int(valid20)}"'
        f' data-note10="{html.escape(missing_text(missing10), quote=True)}"'
        f' data-note20="{html.escape(missing_text(missing20), quote=True)}"'
        f' {"disabled" if not valid10 else ""}>'
        f'<span class="game-tier-icon" aria-hidden="true">{config["icon"]}</span>'
        f'<span class="game-tier-main"><strong>{config["name"]}</strong>'
        f'<small>{config["subtitle"]}</small>'
        f'<span class="game-tier-mix">{html.escape(_mix_label(tier, 10))}</span>'
        f'<em class="game-tier-hint">{html.escape(missing_text(missing10))}</em></span>'
        '<span class="game-tier-arrow" aria-hidden="true">›</span></button>'
    )


STYLE = """
<style id="ldvl-game-levels">
.game-select{max-width:900px!important;width:100%;padding:12px clamp(9px,2vw,20px) 36px!important;margin:0 auto}
.game-select .game-top{background:linear-gradient(120deg,#102b4e,#174b86);color:#fff;border-radius:16px;padding:19px clamp(14px,3vw,26px);margin-bottom:12px}
.game-select .game-top h1{margin:5px 0;font:900 clamp(21px,2.5vw,30px)/1.25 Segoe UI,Arial,sans-serif;color:#fff}
.game-select .game-top p{margin:7px 0 0;font:500 13px/1.5 Segoe UI,Arial,sans-serif;color:#d8e9ff}
.game-select .game-back{display:inline-flex;color:#e5f1ff;text-decoration:none;font-weight:750;font-size:12px}
.game-select .game-panel{background:#fff;border:1px solid #d8e2ef;border-radius:15px;padding:17px}
.game-select .game-panel h2{margin:0 0 10px;color:#153b64;font-size:16px}
.game-select .game-counts{display:flex;flex-wrap:wrap;gap:7px;align-items:center;padding:9px 0 13px;margin-bottom:13px;border-bottom:1px solid #e5edf6}
.game-select .game-counts b{font-size:12px;color:#4d6884;margin-right:5px}
.game-select .game-counts label{display:inline-flex;align-items:center;gap:7px;border:1px solid #bfd0e4;border-radius:9px;background:#f6f9fd;padding:9px 14px;min-height:43px;font-size:13px;font-weight:800;cursor:pointer}
.game-select .game-counts label:has(input:checked){border-color:#2366c5;background:#e9f2ff;color:#1456a8}
.game-select .game-counts input{accent-color:#2366c5;min-width:17px;min-height:17px}
.game-select .game-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.game-select .game-tier{position:relative;display:flex;flex-direction:column;align-items:flex-start;gap:8px;text-align:left;min-width:0;min-height:196px;padding:15px;border:1.5px solid #d4dfeb;border-radius:14px;background:#fbfdff;color:#173b63;cursor:pointer;transition:transform .12s,border-color .12s,box-shadow .12s}
.game-select .game-tier:hover:not(:disabled){border-color:#3174ce;box-shadow:0 5px 15px #1e4e8522;transform:translateY(-2px)}
.game-select .game-tier:focus-visible{outline:3px solid #f4b340;outline-offset:3px}
.game-select .game-tier:disabled{cursor:not-allowed;opacity:.55;transform:none}
.game-select .game-tier-easy{border-top:4px solid #22a06b}
.game-select .game-tier-medium{border-top:4px solid #e5a129}
.game-select .game-tier-hard{border-top:4px solid #ce5b4f}
.game-select .game-tier-icon{display:grid;place-items:center;width:40px;height:40px;border-radius:12px;background:#e9f2fc;font-size:22px}
.game-select .game-tier-main{display:flex;flex-direction:column;gap:7px;min-width:0;width:100%}
.game-select .game-tier-main strong{font-size:19px;line-height:1.15}
.game-select .game-tier-main small{font-size:12px;font-weight:750;color:#60758f}
.game-select .game-tier-mix{font:700 12px/1.6 Segoe UI,Arial,sans-serif;color:#244d77;overflow-wrap:break-word}
.game-select .game-tier-hint{font:600 11px/1.4 Segoe UI,Arial,sans-serif;color:#64748b;font-style:normal}
.game-select .game-tier:disabled .game-tier-hint{color:#a83a35}
.game-select .game-tier-arrow{position:absolute;top:16px;right:16px;font-size:26px;font-weight:800;color:#7594b6}
.game-select .game-stock{margin:14px 0 0;font:600 12px/1.55 Segoe UI,Arial,sans-serif;color:#526e8a}
.game-select .game-warning{margin:10px 0;border:1px solid #edc580;background:#fff9e9;color:#89550a;padding:10px 12px;border-radius:9px;font-size:13px;font-weight:650}
.game-select .game-footer{font-size:12px;color:#60748b;line-height:1.5;margin:13px 2px}
@media(max-width:660px){.game-select{padding:6px 7px 24px!important}.game-select .game-panel{padding:11px}.game-select .game-grid{grid-template-columns:1fr;gap:8px}.game-select .game-tier{min-height:0;flex-direction:row;align-items:center;gap:10px;padding:12px;border-radius:11px}.game-select .game-tier-icon{flex:0 0 39px}.game-select .game-tier-main{gap:4px}.game-select .game-tier-main strong{font-size:16px}.game-select .game-tier-arrow{position:static;margin-left:auto}.game-select .game-top{padding:14px}.game-select .game-counts label{flex:1 1 auto;justify-content:center}.game-select .game-tier-hint{font-size:10px}}
</style>
"""


@app.route("/member/game", methods=["GET", "POST"])
def game_level_picker():
    """Full 22/28-question subject games; see exam_game for quotas and safeguards."""
    from exam_game import game_level_picker as full_exam_picker
    return full_exam_picker()
