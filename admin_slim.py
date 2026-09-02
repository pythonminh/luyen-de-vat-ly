# -*- coding: utf-8 -*-
"""ADMIN: lọc câu gần giống trong một dạng để cô gọn ngân hàng."""
from __future__ import annotations

import json
import re
import urllib.parse
from difflib import SequenceMatcher

from flask import jsonify, request, redirect

import app as base
from student_gemini import _keys_from_payload


def _norm(s):
    return base._dup_norm(s)


def _opts(q):
    kind = str(q.get("kind") or "TL")
    if kind == "TN":
        rows = q.get("options") or []
    elif kind == "DS":
        rows = q.get("statements") or []
    else:
        rows = []
    out = []
    for o in rows:
        t = _norm(o.get("text") if isinstance(o, dict) else o)
        if t:
            out.append(t)
    return out


def _stem(q):
    return _norm(q.get("text") or "")


def _ratio(a, b):
    a, b = str(a or ""), str(b or "")
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if min(la, lb) < 8:
        return 1.0 if a == b else 0.0
    if max(la, lb) > 12 and (min(la, lb) / max(la, lb) < 0.35):
        ta, tb = set(a.split()), set(b.split())
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)
    return SequenceMatcher(None, a[:900], b[:900]).ratio()


def _opt_ratio(a, b):
    sa, sb = set(a or []), set(b or [])
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _snip(q, n=220):
    t = re.sub(r"\s+", " ", str(q.get("text") or "")).strip()
    if len(t) > n:
        t = t[: n - 1] + "…"
    return t


def _drop_key(q, path):
    src = str(q.get("src") or path or "").replace("\\", "/")
    try:
        fi = int(q.get("file_idx") if q.get("file_idx") is not None else q.get("idx") or 0)
    except (TypeError, ValueError):
        fi = int(q.get("idx") or 0)
    return src, fi, f"{src}||{fi}"


def _keep_score(q):
    sol = str(q.get("solution") or "")
    qid = str(q.get("id") or "").strip()
    return (len(sol), 1 if qid else 0, -int(q.get("idx") or 0))


def _pair_scores(a, b):
    ask = _ratio(_stem(a), _stem(b))
    opt = _opt_ratio(_opts(a), _opts(b))
    return ask, opt, max(ask, opt)


def cluster_similar(questions, threshold=0.75):
    qs = list(questions or [])
    n = len(qs)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    edges = {}
    for i in range(n):
        for j in range(i + 1, n):
            if str(qs[i].get("kind") or "") != str(qs[j].get("kind") or ""):
                continue
            ask, opt, overall = _pair_scores(qs[i], qs[j])
            if overall + 1e-9 < threshold:
                continue
            union(i, j)
            edges[(i, j)] = {"ask": round(ask * 100), "opt": round(opt * 100), "sim": round(overall * 100)}

    buckets = {}
    for i in range(n):
        buckets.setdefault(find(i), []).append(i)
    groups = []
    for members in buckets.values():
        if len(members) < 2:
            continue
        arr = [qs[i] for i in members]
        keep_q = max(arr, key=_keep_score)
        pairs = []
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                e = edges.get((members[a], members[b])) or edges.get((members[b], members[a]))
                if e:
                    pairs.append(e)
        sim = max((p["sim"] for p in pairs), default=int(threshold * 100))
        why_ask = max((p["ask"] for p in pairs), default=0)
        why_opt = max((p["opt"] for p in pairs), default=0)
        if why_ask >= why_opt and why_ask >= int(threshold * 100):
            kind = "cách hỏi"
        elif why_opt >= int(threshold * 100):
            kind = "phương án"
        else:
            kind = "cách hỏi hoặc phương án"
        extras = [q for q in arr if q is not keep_q]
        groups.append(
            {
                "sim": sim,
                "ask": why_ask,
                "opt": why_opt,
                "kind": kind,
                "keep": keep_q,
                "extras": extras,
                "members": arr,
            }
        )
    groups.sort(key=lambda g: (-int(g["sim"]), -len(g["members"])))
    return groups


def _pack_group(g, path):
    def row(q, role):
        src, fi, key = _drop_key(q, path)
        return {
            "idx": int(q.get("idx") or 0),
            "id": str(q.get("id") or "").strip() or "—",
            "kind": str(q.get("kind") or ""),
            "src": src,
            "file_idx": fi,
            "drop": key,
            "role": role,
            "snip": _snip(q),
        }

    keep = g["keep"]
    items = [row(keep, "keep")] + [row(q, "drop") for q in g["extras"]]
    return {
        "sim": int(g.get("sim") or 0),
        "ask": int(g.get("ask") or 0),
        "opt": int(g.get("opt") or 0),
        "kind": g.get("kind") or "",
        "why": g.get("why") or "",
        "keep_drop": _drop_key(keep, path)[2],
        "items": items,
    }


def _parse_ai_json(text):
    s = str(text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    if m:
        s = m.group(1).strip()
    a, b = s.find("["), s.rfind("]")
    if a < 0 or b <= a:
        return []
    data = json.loads(s[a : b + 1])
    return data if isinstance(data, list) else []


def _ai_refine(groups, keys, threshold_pct):
    from admin_classify import _gemini_once

    lines = []
    by_idx = {}
    for gi, g in enumerate(groups[:18]):
        lines.append(f"Nhóm {gi}: giống ~{g['sim']}% ({g['kind']})")
        for q in g["members"]:
            idx = int(q.get("idx") or 0)
            by_idx[idx] = q
            opts = "; ".join(_opts(q)[:4])
            lines.append(f"  idx={idx} id={q.get('id') or '—'} loại={q.get('kind')}: {_snip(q, 320)}")
            if opts:
                lines.append(f"    PA: {opts[:400]}")
    prompt = (
        "Bạn là giáo viên ra đề THPT. Cô gọn ngân hàng: trong mỗi nhóm, giữ 1 câu đủ dùng, "
        "gợi ý XÓA các câu cùng ý / cùng cách hỏi / cùng bộ phương án (chỉ đổi số liệu nhỏ hoặc đảo A–D).\n"
        f"Ngưỡng ADMIN chọn: {threshold_pct}%. Không đổi tên dạng. Không bịa idx.\n"
        "Nếu hai câu khác hẳn kỹ năng hoặc dữ kiện, để drop=[].\n"
        'JSON: [{"group":0,"keep":idx,"drop":[idx,...],"sim":85,"why":"ngắn"}]\n'
        + "\n".join(lines)
    )
    raw, err = _gemini_once(keys, prompt, 5000)
    if not raw:
        return groups, err
    try:
        rows = _parse_ai_json(raw)
    except Exception as e:
        return groups, str(e)
    out = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            gi = int(row.get("group"))
            g = groups[gi]
        except Exception:
            continue
        keep_idx = row.get("keep")
        drop_idxs = row.get("drop") or []
        try:
            keep_idx = int(keep_idx)
            drop_idxs = [int(x) for x in drop_idxs]
        except (TypeError, ValueError):
            continue
        members = {int(q.get("idx") or 0): q for q in g["members"]}
        if keep_idx not in members:
            continue
        extras = [members[i] for i in drop_idxs if i in members and i != keep_idx]
        if not extras:
            continue
        key = (keep_idx, tuple(sorted(int(q.get("idx") or 0) for q in extras)))
        if key in seen:
            continue
        seen.add(key)
        sim = row.get("sim")
        try:
            sim = int(sim)
        except (TypeError, ValueError):
            sim = g["sim"]
        out.append(
            {
                "sim": sim,
                "ask": g["ask"],
                "opt": g["opt"],
                "kind": g["kind"],
                "why": str(row.get("why") or "AI: gần nội dung, nên bỏ bản thừa.").strip()[:220],
                "keep": members[keep_idx],
                "extras": extras,
                "members": [members[keep_idx]] + extras,
            }
        )
    return (out or groups), ""


def _load_dang(path, dang):
    qs = base.parse_lesson_questions(path)
    if not qs:
        _, tex = base.read_tex(path)
        qs = base.parse_questions(tex)
        for q in qs:
            q["src"] = path
            q["file_idx"] = int(q.get("idx") or 0)
    dang = str(dang or "").strip()
    selected = [q for q in qs if str(q.get("dang") or "").strip() == dang]
    if not selected and dang == "Chưa phân dạng":
        selected = [q for q in qs if not str(q.get("dang") or "").strip() or str(q.get("dang") or "").strip() == dang]
    return selected


@base.app.post("/api/admin/similar-questions")
def api_similar_questions():
    if not base.can_manage_bank():
        return jsonify(ok=False, error="Chỉ ADMIN mới lọc câu gần giống."), 403
    data = request.get_json(silent=True) or {}
    path = str(data.get("path") or "").replace("\\", "/").strip()
    dang = str(data.get("dang") or "").strip()
    try:
        pct = int(data.get("percent") or 75)
    except (TypeError, ValueError):
        pct = 75
    pct = max(50, min(98, pct))
    use_ai = bool(data.get("use_ai", True))
    if not path or not dang:
        return jsonify(ok=False, error="Thiếu path hoặc dạng."), 400
    try:
        selected = _load_dang(path, dang)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    if len(selected) < 2:
        return jsonify(ok=True, groups=[], n=len(selected), percent=pct, message="Dạng này chưa đủ 2 câu để so.")
    groups = cluster_similar(selected, pct / 100.0)
    ai_note = ""
    keys = _keys_from_payload(data)
    if use_ai and keys and groups:
        groups, ai_note = _ai_refine(groups, keys, pct)
    packed = [_pack_group(g, path) for g in groups]
    extras = sum(max(0, len(g["items"]) - 1) for g in packed)
    msg = (
        f"Ngưỡng ≥ {pct}%. {len(selected)} câu → {len(packed)} nhóm gần giống, gợi ý xóa {extras} câu."
        + (" AI đã rà lại các nhóm." if keys and use_ai else " (chưa dùng AI — chỉ so chữ/phương án).")
    )
    return jsonify(ok=True, groups=packed, n=len(selected), percent=pct, extras=extras, message=msg, ai_note=ai_note or "")


@base.app.post("/admin/slim-delete")
def admin_slim_delete():
    if not base.can_manage_bank():
        return redirect("/admin/login")
    path = str(request.form.get("path") or "").replace("\\", "/").strip()
    dang = str(request.form.get("dang") or "").strip()
    nxt = str(request.form.get("next") or "")
    if not nxt.startswith("/member/dang?"):
        nxt = "/member/dang?path=" + path + "&dang=" + dang

    def back(key, msg):
        sep = "&" if "?" in nxt else "?"
        return redirect(nxt + sep + key + "=" + urllib.parse.quote(msg))

    if request.form.get("confirm") != "yes":
        return back("err", "Phải xác nhận trước khi xóa câu gần giống.")
    try:
        selected = _load_dang(path, dang)
    except Exception as e:
        return back("err", str(e))
    allowed = set()
    for q in selected:
        src, fi, key = _drop_key(q, path)
        allowed.add((src, fi))
    drops_by = {}
    for raw in request.form.getlist("drop"):
        raw = str(raw or "").strip()
        if "||" not in raw:
            continue
        src, _, idx_s = raw.replace("\\", "/").rpartition("||")
        try:
            fi = int(idx_s)
        except Exception:
            continue
        src = src.replace("\\", "/")
        if (src, fi) not in allowed:
            continue
        drops_by.setdefault(src, []).append(fi)
    if not drops_by:
        return back("err", "Chưa tick câu nào để xóa.")
    total = 0
    try:
        for src, idxs in drops_by.items():
            idxs = sorted(set(idxs))
            fsha, tex = base.read_tex(src, need_sha=True)
            new = base.tex_without_questions(tex, idxs)
            local = base._safe_repo_file(src)[1]
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(new, encoding="utf-8")
            if base.TOKEN:
                base.github_put_text(src, new, "ADMIN cô gọn dạng: xóa " + str(len(idxs)) + " câu gần giống trong " + src, fsha or None)
            total += len(idxs)
        try:
            from dang_routes import _STATS_CACHE, _QID_CACHE

            _STATS_CACHE.clear()
            _QID_CACHE.clear()
        except Exception:
            pass
        return back("ok", "Đã xóa " + str(total) + " câu gần giống, giữ bản ADMIN không tick.")
    except Exception as e:
        return back("err", str(e))


def slim_bar_html(path, dang, next_url):
    p = json.dumps(path, ensure_ascii=False)
    d = json.dumps(dang, ensure_ascii=False)
    n = json.dumps(next_url, ensure_ascii=False)
    return (
        "<div class='slimbar' id='slimBar'><b>Cô gọn dạng</b>"
        "<label>Giống ≥ <input id='simPct' type='number' min='50' max='98' value='75'> %</label>"
        "<label><input id='simAi' type='checkbox' checked> Dùng AI rà nhóm</label>"
        "<button type='button' class='btn' id='simGo'>🤖 Lọc câu gần nội dung</button>"
        "<span class='muted'>So cách hỏi hoặc phương án. Tick câu thừa rồi xóa — bản GIỮ không tick.</span></div>"
        "<div id='slimOut'></div>"
        + f"<script>(function(){{const PATH={p},DANG={d},NEXT={n};"
        r"""
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}
function markDrops(keys){
  const set=new Set(keys||[]);
  document.querySelectorAll('.qcard[data-drop]').forEach(function(c){
    const k=c.getAttribute('data-drop');
    c.classList.toggle('slimhit',set.has(k));
  });
}
document.getElementById('simGo').addEventListener('click',async function(){
  const out=document.getElementById('slimOut');
  const pct=Math.max(50,Math.min(98,Number(document.getElementById('simPct').value)||75));
  const useAi=!!document.getElementById('simAi').checked;
  const keys=(window.ldvlFilledKeys&&ldvlFilledKeys())||[];
  if(useAi&&!keys.length){alert('Nạp key Gemini (trang 🤖 Gemini) hoặc bỏ tick «Dùng AI rà nhóm» để lọc theo chữ.');return;}
  out.innerHTML='⏳ Đang so '+pct+'% trong dạng này...';
  markDrops([]);
  try{
    const r=await fetch('/api/admin/similar-questions',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({path:PATH,dang:DANG,percent:pct,use_ai:useAi,api_keys:keys})});
    const d=await r.json();
    if(!d.ok){out.innerHTML='<div class="err">'+(d.error||'Lỗi lọc')+'</div>';return;}
    const gs=d.groups||[];
    if(!gs.length){out.innerHTML='<div class="muted">'+(d.message||'Không thấy câu gần giống ở ngưỡng này. Hạ % rồi thử lại.')+'</div>';return;}
    const drops=[];
    let html='<form method="post" action="/admin/slim-delete" class="slimform" onsubmit="return confirm(\'Xóa các câu đã tick? Nên giữ 1 câu/nhóm.\')">';
    html+='<input type="hidden" name="path" value="'+esc(PATH)+'"><input type="hidden" name="dang" value="'+esc(DANG)+'">';
    html+='<input type="hidden" name="next" value="'+esc(NEXT)+'">';
    html+='<div class="success">'+(d.message||'')+(d.ai_note?' · '+esc(d.ai_note):'')+'</div>';
    gs.forEach(function(g,i){
      html+='<div class="slimgrp"><div class="slimh">Nhóm '+(i+1)+' · <b>'+esc(g.sim)+'%</b> · '+esc(g.kind)+' (hỏi '+esc(g.ask)+'% · PA '+esc(g.opt)+'%)'+(g.why?'<div class="muted">'+esc(g.why)+'</div>':'')+'</div>';
      (g.items||[]).forEach(function(it){
        if(it.role==='keep'){
          html+='<div class="slimrow keep"><span class="tag">GIỮ</span> <span class="qid">'+esc(it.id)+'</span> '+esc(it.snip)+'</div>';
        }else{
          drops.push(it.drop);
          html+='<div class="slimrow drop"><label><input type="checkbox" name="drop" value="'+esc(it.drop)+'" checked> Xóa</label> <span class="qid">'+esc(it.id)+'</span> '+esc(it.snip)+'</div>';
        }
      });
      html+='</div>';
    });
    html+='<p><label class="dupok"><input type="checkbox" name="confirm" value="yes" required> Tôi xác nhận xóa các câu đã tick</label> ';
    html+='<button class="btn red" type="submit">🗑 Xóa câu gần giống đã tick</button></p></form>';
    out.innerHTML=html;
    markDrops(drops);
  }catch(e){out.innerHTML='<div class="err">'+e+'</div>';}
});
})();</script>"""
    )
