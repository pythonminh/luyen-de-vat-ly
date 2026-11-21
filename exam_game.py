# -*- coding: utf-8 -*-
"""Full-length game exams by subject, level mix and question format.

The browser only reports focus/window violations; the server owns the deadline,
question selection, attempt status and answer submission permissions.
"""
from __future__ import annotations

import collections
import html
import json
import random
import secrets
import time
import unicodedata
import urllib.parse

from flask import jsonify, redirect, request, session
import app as base
import game_levels

app = base.app
LEVELS = ("N", "H", "V", "C")
KINDS = ("TN", "DS", "TLN")
NAMES = {"N":"NB","H":"TH","V":"VD","C":"VDC"}
FORM_NAMES = {"TN":"Trắc nghiệm","DS":"Đúng/Sai","TLN":"Trả lời ngắn"}
EXAMS = {
    "toan": {"label":"Toán","minutes":90,"kinds":{"TN":12,"DS":4,"TLN":6}},
    "ly": {"label":"Vật lí","minutes":45,"kinds":{"TN":18,"DS":4,"TLN":6}},
}
MAX_EXTRA = 8


def normalize(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ","d").strip()


def subject_of(s):
    s = normalize(s)
    if "toan" in s:
        return "toan"
    if "vat li" in s or "vat ly" in s:
        return "ly"
    return ""


def lesson_index():
    return [l for l in (base.index_data().get("lessons") or [])
            if isinstance(l,dict) and l.get("path")]


def context_for(path):
    found = next((l for l in lesson_index() if str(l.get("path"))==path), None)
    if not found:
        return None
    subject = subject_of(found.get("Mon"))
    if subject not in EXAMS:
        return None
    return found, subject, str(found.get("Lop") or "").strip()


def extra_lessons(path, member, lesson, subject, grade):
    out=[]
    for entry in lesson_index():
        p=str(entry.get("path") or "")
        if not p or p==path or str(entry.get("Lop") or "").strip()!=grade:
            continue
        if subject_of(entry.get("Mon"))!=subject or not base.can_practice(member,p):
            continue
        if not base.is_bank_question_tex(p):
            continue
        n=int(entry.get("questions") or entry.get("count") or 0)
        if n<=0:
            continue
        out.append(entry)
    chapter=str(lesson.get("Chuong") or "")
    out.sort(key=lambda e:(str(e.get("Chuong") or "")!=chapter,
                            -int(e.get("questions") or e.get("count") or 0),
                            str(e.get("BaiHoc") or "")))
    return out


def question_rows(paths):
    result=[]
    for path in paths:
        for q in base.load_lesson_questions(path):
            kind=str(q.get("kind") or "")
            if kind not in KINDS:
                continue
            try: idx=int(q.get("idx"))
            except (TypeError, ValueError): continue
            result.append((path,idx,kind,base.norm_muc(q.get("level")) or "H"))
    return result


def level_targets(tier, total):
    if tier not in game_levels.GAME_TIERS:
        raise ValueError("Cấp độ game không hợp lệ.")
    weights=game_levels.GAME_TIERS[tier]["units"]
    floors={lv:int(total*w//10) for lv,w in weights.items()}
    remain=total-sum(floors.values())
    ranks=sorted(weights,key=lambda lv:(-(total*weights[lv]%10),LEVELS.index(lv)))
    for lv in ranks[:remain]:
        floors[lv]+=1
    return {lv:floors.get(lv,0) for lv in LEVELS}


def _flow(rows, kind_target, level_target):
    """Small bipartite max flow: category and Bloom difficulty quotas must BOTH fit."""
    sizes=collections.Counter((r[2],r[3]) for r in rows)
    source="s"; sink="t"
    capacity=collections.defaultdict(int)
    adj=collections.defaultdict(list)
    def edge(u,v,n):
        if v not in adj[u]: adj[u].append(v)
        if u not in adj[v]: adj[v].append(u)
        capacity[u,v]+=n
    for k,n in kind_target.items(): edge(source,"k"+k,n)
    for k in KINDS:
        for lv in LEVELS:
            if sizes[k,lv]: edge("k"+k,"l"+lv,sizes[k,lv])
    for lv,n in level_target.items(): edge("l"+lv,sink,n)
    flow=0
    while True:
        parent={source:None}
        todo=collections.deque([source])
        while todo and sink not in parent:
            u=todo.popleft()
            for v in adj[u]:
                if v not in parent and capacity[u,v]>0:
                    parent[v]=u
                    todo.append(v)
        if sink not in parent: break
        delta=10**9
        v=sink
        while v!=source:
            u=parent[v];delta=min(delta,capacity[u,v]);v=u
        v=sink
        while v!=source:
            u=parent[v]
            capacity[u,v]-=delta
            capacity[v,u]+=delta
            v=u
        flow+=delta
    assigned={(k,lv):capacity["l"+lv,"k"+k] for k in KINDS for lv in LEVELS}
    return flow,assigned


def shortages(rows, tier, cfg):
    kinds=cfg["kinds"]
    levels=level_targets(tier,sum(kinds.values()))
    counts=collections.Counter(row[2] for row in rows)
    lc=collections.Counter(row[3] for row in rows)
    missing=[]
    for k,n in kinds.items():
        if counts[k]<n: missing.append(f"{FORM_NAMES[k]} thiếu {n-counts[k]} câu")
    for lv,n in levels.items():
        if lc[lv]<n: missing.append(f"{NAMES[lv]} thiếu {n-lc[lv]} câu")
    n,_=_flow(rows,kinds,levels)
    if n<sum(kinds.values()) and not missing:
        missing.append("Phân bố loại câu và mức độ chưa khớp (cần bổ sung câu ở các nhóm TN/ĐS/TLN theo mức)")
    return missing


def select_rows(rows,tier,cfg,previous=None):
    kind_targets=cfg["kinds"]
    level_targets=globals()["level_targets"](tier,sum(kind_targets.values()))
    amount, allocation=_flow(rows,kind_targets,level_targets)
    if amount!=sum(kind_targets.values()):
        raise ValueError("Ngân hàng chưa đủ cơ cấu đề: "+"; ".join(shortages(rows,tier,cfg)))
    rng=random.SystemRandom()
    prev_set=set(tuple(x) for x in previous or ())
    groups=collections.defaultdict(list)
    for row in rows:
        groups[row[2],row[3]].append(row)
    chosen=[]
    for (kind,level),count in allocation.items():
        if count<=0: continue
        pool=groups[kind,level]
        fresh=[r for r in pool if (r[0],r[1]) not in prev_set]
        old=[r for r in pool if (r[0],r[1]) in prev_set]
        rng.shuffle(fresh);rng.shuffle(old)
        chosen.extend((fresh+old)[:count])
    rng.shuffle(chosen)
    ordered=[(row[0],row[1]) for row in chosen]
    if previous and ordered==[tuple(x) for x in previous] and len(ordered)>1:
        ordered=ordered[1:]+ordered[:1]
    return ordered


def begin_attempt(path, extra_paths, tier, member):
    ctx=context_for(path)
    if not ctx:
        raise ValueError("Bài chưa xác định được môn hoặc khối.")
    lesson, subject, grade=ctx
    if tier not in game_levels.GAME_TIERS:
        raise ValueError("Vui lòng chọn Dễ, Trung bình hoặc Khó.")
    allowed={str(l.get("path")) for l in extra_lessons(path,member,lesson,subject,grade)}
    if len(extra_paths)>MAX_EXTRA or len(set(extra_paths))!=len(extra_paths):
        raise ValueError(f"Chỉ được chọn tối đa {MAX_EXTRA} bài bổ sung.")
    if any(p not in allowed for p in extra_paths):
        raise ValueError("Có bài bổ sung không thuộc cùng môn, cùng khối hoặc chưa có quyền.")
    selected_paths=[path]+list(extra_paths)
    cfg=EXAMS[subject]
    rows=question_rows(selected_paths)
    prior=session.get("practice_game_last") or []
    prev=[tuple(x) for x in prior if isinstance(x,list) and len(x)==2]
    selected=select_rows(rows,tier,cfg,prev)
    # Keep cookies small: store unique path table and 28/22 small index pairs.
    paths=list(dict.fromkeys(p for p,_ in selected))
    path_index={p:i for i,p in enumerate(paths)}
    ids=list(range(len(selected)))
    source_pairs=[[path_index[p],idx] for p,idx in selected]
    started=time.time()
    session.update(
        practice_path=path,practice_dang="",practice_kind="",practice_muc="",
        practice_ids=ids,practice_pos=0,practice_right=0,
        practice_streak=0,practice_best=0,practice_done=[],
        practice_ai=True,
        practice_started_at=started,practice_attempt_id=secrets.token_hex(16),
        practice_game_level=tier,practice_game_count=len(ids),
        practice_game_mix=level_targets(tier,len(ids)),
        practice_game_kinds=cfg["kinds"],
        practice_game_subject=subject,
        practice_game_minutes=cfg["minutes"],
        practice_game_deadline=started+cfg["minutes"]*60,
        practice_game_status="active",practice_game_reason="",
        practice_game_paths=paths,practice_game_sources=source_pairs,
        practice_game_selected_paths=selected_paths,
        practice_game_last=[[p,i] for p,i in selected],
    )
    return len(ids)


def game_question_map(sess):
    paths=list(sess.get("practice_game_paths") or [])
    sources=list(sess.get("practice_game_sources") or [])
    bypath={}
    for p in paths:
        rows=base.load_lesson_questions(p)
        bypath[p]={int(q["idx"]):q for q in rows}
    out={}
    for j,pair in enumerate(sources):
        if not isinstance(pair,(list,tuple)) or len(pair)!=2:continue
        try:
            p=paths[int(pair[0])]
            q=bypath[p][int(pair[1])]
        except (IndexError,KeyError,ValueError,TypeError):
            continue
        out[j]=dict(q,idx=j)
    return out


def guard(sess):
    """Return a reason when the active game may no longer be answered."""
    if not sess.get("practice_game_level"):
        return ""
    status=str(sess.get("practice_game_status") or "")
    if status=="ended":
        return str(sess.get("practice_game_reason") or "Lượt chơi đã kết thúc.")
    if status=="done":
        return "" if int(sess.get("practice_pos") or 0)>=len(sess.get("practice_ids") or []) else "Lượt đã hoàn thành."
    if status!="active":
        return "Lượt chơi không còn hoạt động."
    if time.time()>=float(sess.get("practice_game_deadline") or 0):
        sess["practice_game_status"]="ended"
        sess["practice_game_reason"]="Hết thời gian làm bài."
        return "Hết thời gian làm bài."
    return ""


def end_current(reason, attempt=None):
    if not session.get("practice_game_level"):
        return False
    if attempt and str(attempt)!=str(session.get("practice_attempt_id") or ""):
        return False
    if session.get("practice_game_status")!="active":
        return False
    allowed={
        "hidden":"Đã rời khỏi màn hình làm bài.",
        "blur":"Màn hình game mất tiêu điểm.",
        "split":"Phát hiện cửa sổ bị chia nhỏ.",
        "pagehide":"Đã thoát hoặc tải lại màn hình game.",
        "timeout":"Hết thời gian làm bài.",
    }
    session["practice_game_status"]="ended"
    session["practice_game_reason"]=allowed.get(str(reason),"Lượt chơi bị gián đoạn.")
    session["practice_game_ended_at"]=time.time()
    return True


@app.post("/member/game/violation")
def exam_violation():
    if not base.member_current():
        return jsonify(ok=False),401
    data=request.get_json(silent=True) or {}
    changed=end_current(data.get("reason"),data.get("attempt"))
    return jsonify(ok=bool(changed),ended=session.get("practice_game_status")=="ended")


@app.get("/member/game/ended")
def exam_ended():
    m=base.member_current()
    if not m:return redirect(base.login_url("/member"))
    reason=html.escape(str(session.get("practice_game_reason") or "Lượt đã dừng."))
    path=str(session.get("practice_path") or "")
    if session.get("practice_game_status")!="ended":
        return redirect("/member/game?path="+urllib.parse.quote(path,safe="") if path else "/member")
    body=(
        '<main class="wrap game-select"><div class="game-top">'
        '<h1>⏹ Lượt game đã kết thúc</h1>'
        '<p>Không lưu kỷ lục cho lượt bị gián đoạn.</p></div>'
        '<section class="game-panel"><p class="game-warning">'
        + reason +
        '</p><p>Muốn chơi lại, hệ thống sẽ bốc câu hỏi và xáo thứ tự mới theo đúng cấp độ.</p>'
        '<form method="post" action="/member/game/retry">'
        '<button type="submit" class="btn primary">↻ Làm lại với đề mới</button> '
        '<a class="btn" href="/member/game?path='
        + urllib.parse.quote(path,safe="") +
        '">Đổi cấp độ / bổ sung bài</a></form></section></main>'
    )
    return base.page("Lượt game đã kết thúc", game_levels.STYLE+body)


@app.post("/member/game/retry")
def exam_retry():
    member=base.member_current()
    if not member:return redirect(base.login_url("/member"))
    path=str(session.get("practice_path") or "")
    tier=str(session.get("practice_game_level") or "")
    extras=list(session.get("practice_game_selected_paths") or [])[1:]
    if not path or not base.can_practice(member,path):
        return redirect("/member")
    try:begin_attempt(path,extras,tier,member)
    except ValueError:
        return redirect("/member/game?path="+urllib.parse.quote(path,safe="")+"&retry_error=1")
    return redirect("/member/practice")


def tier_card(tier, cfg, rows):
    name=game_levels.GAME_TIERS[tier]["name"]
    icon=game_levels.GAME_TIERS[tier]["icon"]
    levels=level_targets(tier,sum(cfg["kinds"].values()))
    mix=" · ".join(f'{NAMES[k]} {v}' for k,v in levels.items() if v)
    missing=shortages(rows,tier,cfg)
    status='Đủ cơ cấu đề' if not missing else 'Cần bổ sung thêm câu'
    return (
       f'<button type="submit" class="game-tier game-tier-{tier}" name="level" value="{tier}">'
       f'<span class="game-tier-icon" aria-hidden="true">{icon}</span>'
       f'<span class="game-tier-main"><strong>{name}</strong>'
       f'<small>{game_levels.GAME_TIERS[tier]["subtitle"]}</small>'
       f'<span class="game-tier-mix">{html.escape(mix)}</span>'
       f'<em class="game-tier-hint">{status}</em></span>'
       '<span class="game-tier-arrow">›</span></button>'
    )


def _supplement_form(extras, selected):
    cards=[]
    for l in extras:
        p=str(l.get("path") or "")
        name=str(l.get("BaiHoc") or l.get("De") or p.split("/")[-2])
        chapter=str(l.get("Chuong") or "")
        count=int(l.get("questions") or l.get("count") or 0)
        checked=' checked' if p in selected else ''
        cards.append(
            '<label class="game-more-item">'
            '<input type="checkbox" name="more" value="'+html.escape(p,quote=True)+'"'+checked+'>'
            '<span><strong>'+html.escape(name)+'</strong><small>'+html.escape(chapter)+
            ' · '+str(count)+' câu</small></span></label>'
        )
    if not cards:
        return '<p class="game-warning">Không tìm thấy bài bổ sung cùng môn, cùng khối mà tài khoản có quyền học.</p>'
    return (
        '<details class="game-more" open><summary>📚 Chọn thêm bài cùng môn, cùng khối '
        f'({len(cards)} bài có thể chọn)</summary>'
        '<p>Chọn tối đa '+str(MAX_EXTRA)+' bài. Ưu tiên các bài có đủ câu TN, Đ/S và TLN.</p>'
        '<div class="game-more-list">'+''.join(cards)+'</div></details>'
    )


def game_level_picker():
    member=base.member_current()
    path=str(request.values.get("path") or "").strip()
    if not member:
        return redirect(base.login_url("/member/game?path="+urllib.parse.quote(path,safe="")))
    if not path or not base.can_practice(member,path):
        return redirect("/member")
    ctx=context_for(path)
    if not ctx:
        return base.page("Chọn game",'<div class="wrap"><div class="err">Bài chưa xác định đúng môn Toán/Vật lí và khối lớp.</div></div>')
    lesson,subject,grade=ctx
    cfg=EXAMS[subject]
    candidates=extra_lessons(path,member,lesson,subject,grade)
    allowed={str(e.get("path")) for e in candidates}
    selected=list(dict.fromkeys(str(p) for p in request.form.getlist("more") if str(p) in allowed))
    if len(selected)>MAX_EXTRA:
        selected=selected[:MAX_EXTRA]
    try:rows=question_rows([path]+selected)
    except Exception:rows=[]
    error=""
    if request.method=="POST":
        tier=str(request.form.get("level") or "")
        try:
            begin_attempt(path,selected,tier,member)
            return redirect("/member/practice")
        except (ValueError,TypeError) as exc:
            error=str(exc)
    if request.args.get("retry_error"):
        error="Nguồn câu hỏi đã thay đổi. Vui lòng chọn lại các bài để đủ cơ cấu."
    lack=shortages(rows,"medium",cfg)
    counts=collections.Counter(r[2] for r in rows)
    title=str(lesson.get("BaiHoc") or lesson.get("De") or path)
    qty=sum(cfg["kinds"].values())
    kind_text=" · ".join(f"{FORM_NAMES[k]} {v}" for k,v in cfg["kinds"].items())
    notice=(
        '<p class="game-warning" role="alert">'+html.escape(error)+'</p>' if error else ""
    )
    style="""
<style>
.game-select .game-panel{max-width:100%}
.game-select .game-tier{min-height:172px}
.game-more{margin:14px 0;border:1px solid #c6d7ec;border-radius:12px;background:#f8fbff;overflow:hidden}
.game-more>summary{padding:13px 14px;cursor:pointer;font-weight:850;color:#184777;background:#eff6ff}
.game-more>p{padding:0 14px;font-size:12px;color:#526985}
.game-more-list{max-height:360px;overflow-y:auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;padding:10px}
.game-more-item{display:flex;align-items:center;gap:9px;padding:9px 10px;border:1px solid #dce5ef;border-radius:9px;background:#fff;cursor:pointer}
.game-more-item:has(input:checked){background:#e7f2ff;border-color:#4c8bd4}
.game-more-item input{flex:0 0 auto;accent-color:#1968c5;width:18px;height:18px}
.game-more-item span{min-width:0}
.game-more-item strong{display:block;font-size:12px;line-height:1.4;color:#173c62;overflow-wrap:anywhere}
.game-more-item small{display:block;font-size:11px;line-height:1.4;color:#607d96;overflow-wrap:anywhere}
.game-exam-details{margin:12px 0;display:flex;flex-wrap:wrap;gap:7px}
.game-exam-details span{border-radius:9px;padding:8px 10px;background:#eaf3ff;color:#1c5389;font-size:12px;font-weight:800}
.game-exam-check{margin:8px 0 14px;background:#f7faff;border:1px solid #d7e4ef;border-radius:9px;padding:10px 12px}
.game-exam-check p{margin:4px 0;font-size:12px;color:#526b83}
@media(max-width:700px){.game-more-list{grid-template-columns:1fr;max-height:320px}}
</style>
"""
    body=(
        game_levels.STYLE+style+
        '<main class="wrap game-select"><div class="game-top">'
        '<a class="game-back" href="/member">‹ Danh sách bài học</a>'
        '<h1>🎮 Chọn cấp độ game</h1>'
        '<p>'+html.escape(title)+' · '+html.escape(cfg["label"])+
        ' lớp '+html.escape(grade)+'</p></div>'
        '<section class="game-panel">'
        '<div class="game-exam-details"><span>⏱ '+str(cfg["minutes"])+' phút</span>'
        '<span>📝 '+str(qty)+' câu</span><span>'+html.escape(kind_text)+'</span></div>'
        +notice+
        '<form method="post" action="/member/game">'
        '<input type="hidden" name="path" value="'+html.escape(path,quote=True)+'">'
        '<h2>Chọn bộ bài để tạo đủ đề</h2>'
        '<div class="game-exam-check"><p>Bộ bài đang chọn có: '+
        " · ".join(f"{FORM_NAMES[k]} {counts[k]}/{v}" for k,v in cfg["kinds"].items())+
        '</p><p>Ở cấp Trung bình: '+html.escape("; ".join(lack) if lack else "Đã đủ cơ cấu")+
        '</p></div>'
        +_supplement_form(candidates,selected)+
        '<h2>Chọn độ khó (kiểm tra đủ tỷ lệ khi bắt đầu)</h2>'
        '<div class="game-grid">'+''.join(tier_card(t,cfg,rows) for t in game_levels.GAME_TIERS)+'</div>'
        '</form>'
        '<p class="game-footer">Mỗi lượt chỉ tạo đề khi đủ TN/ĐS/TLN và tỷ lệ NB/TH/VD/VDC.'
        ' Rời màn hình hoặc chia đôi màn hình sẽ kết thúc lượt; làm lại sẽ bốc và xáo câu mới nếu ngân hàng có câu thay thế.</p>'
        '</section></main>'
    )
    return base.page("Chọn cấp độ game",body)
