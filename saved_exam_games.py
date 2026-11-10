# -*- coding: utf-8 -*-
"""Game sessions from an existing saved exam, with no AI regeneration."""
import html
import json
import re
from flask import request, redirect
import exam_paper as exam
from app import app, page, can_manage_bank

MODES = {
    'millionaire': ('🏆 Triệu phú', 'TN', 'Trả lời đúng để lên bậc thưởng; chỉ dùng trắc nghiệm'),
    'fish': ('🎣 Câu cá', 'TN,DS,TLN', 'Trả lời đúng để câu cá, sai thì cá thoát'),
    'tug': ('🪢 Kéo co', 'TN,DS', 'Hai đội thi lần lượt; trả lời đúng để kéo dây về phía mình'),
    'draw': ('🎲 Bốc thăm', 'TN,DS,TLN', 'Xáo câu hỏi, bốc ngẫu nhiên và công bố kết quả'),
    'present': ('📺 Chiếu tương tác', 'TN,DS,TLN', 'Chiếu từng câu, học sinh trả lời rồi giáo viên công bố'),
}
def eligible(q):
    k=q.get('kind')
    if not str(q.get('text') or '').strip(): return False
    if k=='TN':
        xs=q.get('options') or []
        return len(xs)==4 and sum(bool(x.get('correct')) for x in xs)==1 and all(str(x.get('text') or '').strip() for x in xs)
    if k=='DS':
        xs=q.get('statements') or []
        return len(xs)==4 and all(isinstance(x,dict) and 'correct' in x and str(x.get('text') or '').strip() for x in xs)
    if k=='TLN':
        return bool(str(q.get('answer') or '').strip())
    return False
def pack(q):
    return {'kind':q['kind'],'text':str(q.get('text') or ''),'solution':str(q.get('solution') or ''),
            'options':[{'text':str(x.get('text') or ''),'correct':bool(x.get('correct'))} for x in q.get('options') or []],
            'statements':[{'text':str(x.get('text') or ''),'correct':bool(x.get('correct'))} for x in q.get('statements') or []],
            'answer':str(q.get('answer') or '')}

@app.get('/member/exams/game/<code>')
def saved_exam_game(code):
    if not can_manage_bank():return redirect('/member/login')
    if not re.fullmatch(r'[0-9a-f]{24}',code):return page('Không tìm thấy đề','<p>Mã đề không hợp lệ.</p>'),404
    try:
        saved,_=exam._saved_load(code)
        frozen=saved.get('exam') or {}
        qs=exam.load_exam_qs(frozen)
        by={int(q.get('idx')):q for q in qs}
        copies=frozen.get('copies') or []
        if not copies:raise ValueError('Đề chưa có mã đề.')
        try:ci=int(request.args.get('copy',0))
        except (TypeError,ValueError):ci=0
        ci=max(0,min(ci,len(copies)-1))
        cp=copies[ci]
        variants=[exam.apply_perm(by[int(i)],cp) for i in cp.get('ids') or [] if str(i).lstrip('-').isdigit() and int(i) in by]
        available=[q for q in variants if eligible(q)]
        if not available:raise ValueError('Không có câu trắc nghiệm, đúng/sai hoặc trả lời ngắn có đáp án hợp lệ.')
        mode=str(request.args.get('mode') or '')
        if mode not in MODES:mode=''
        chooser=[]
        for key,(label,kinds,desc) in MODES.items():
            num=sum(q['kind'] in kinds.split(',') for q in available)
            selected=' chosen' if mode==key else ''
            href='/member/exams/game/'+code+'?copy='+str(ci)+'&mode='+key
            chooser.append('<a class="game-option'+selected+('" aria-disabled="true"' if num==0 else '" href="'+href+'"')+'>'
                           '<b>'+label+'</b><span>'+desc+'</span><strong>'+str(num)+' câu phù hợp</strong></a>')
        copies_html=''.join('<option value="'+str(i)+'"'+(' selected' if i==ci else '')+'>'+html.escape(str(c.get('code') or 'Mã '+str(i+1)))+'</option>' for i,c in enumerate(copies))
        title=html.escape(str(saved.get('title') or 'Đề đã lưu'))
        hero='<div class="game-top"><div><div class="game-kicker">🎮 TRÒ CHƠI TỰ ĐỘNG TỪ ĐỀ ĐÃ LƯU</div><h1>'+title+'</h1><p>Không cần tạo lại câu hỏi. Chọn hình thức chơi, hệ thống tự lọc các câu có đáp án hợp lệ.</p></div><a href="/member/exams/saved" class="game-return">← Kho đề</a></div>'
        controls='<div class="game-choose"><label>Mã đề <select id="gameCopy">'+copies_html+'</select></label><span>'+str(len(available))+' / '+str(len(variants))+' câu đủ điều kiện</span></div>'
        cards='<div class="game-options">'+''.join(chooser)+'</div>'
        game_section=''
        if mode:
            accepted=MODES[mode][1].split(',')
            questions=[pack(q) for q in available if q['kind'] in accepted]
            if questions:
                data=json.dumps({'mode':mode,'questions':questions},ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
                game_section='''<section id="gameStage" class="game-stage" data-game="''' + html.escape(mode) + '''">
<header class="game-playhead"><div><b id="gameModeName"></b><span id="gameProgress"></span></div>
<div class="game-ctrl"><button type="button" id="gameFull">⛶ Toàn màn hình</button><button type="button" id="gameRestart">↻ Chơi lại</button></div></header>
<div id="gameScore" class="game-score"></div>
<div id="gameQuestion" class="game-question"></div>
<div id="gameChoices" class="game-choices"></div>
<div class="game-ctrl bottom"><button type="button" id="gameCheck">Kiểm tra / Công bố</button>
<button type="button" id="gameNext" disabled>Câu tiếp theo →</button></div>
<div id="gameFeedback" role="status" aria-live="polite"></div></section>
<script id="gameData" type="application/json">'''+data+'''</script>'''
        else:
            game_section='<div class="game-hint">Chọn một trò chơi ở trên để tạo phiên chơi ngay từ mã đề này.</div>'
        body=GAME_CSS+hero+controls+cards+game_section+(GAME_JS if mode else '')
        return page('Trò chơi từ đề: '+title,'<main class="game-wrap">'+body+'</main>')
    except Exception as e:
        return page('Trò chơi từ đề','<div class="wrap"><p class="err">Không tạo được trò chơi: '+html.escape(str(e))+'</p><a href="/member/exams/saved">← Quay lại kho đề</a></div>'),400

GAME_CSS='''<style>
.game-wrap{max-width:1250px;margin:10px auto;padding:clamp(10px,2vw,22px);color:#16314f}
.game-top{display:flex;align-items:center;justify-content:space-between;gap:20px;background:linear-gradient(115deg,#102a51,#155b91);color:#fff;border-radius:18px;padding:22px}
.game-top h1{font-size:clamp(23px,3vw,35px);color:#fff;margin:8px 0}.game-top p{color:#e0edff;margin:0}
.game-kicker{font-size:12px;letter-spacing:.08em;font-weight:800}.game-return{color:#fff;text-decoration:none;border:1px solid #ffffff88;border-radius:9px;padding:10px 14px;white-space:nowrap}
.game-choose{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin:17px 0;font-weight:700}
.game-choose select{min-height:43px;border:1px solid #c9d7e8;border-radius:9px;padding:7px;background:#fff;font:inherit}
.game-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:11px}
.game-option{display:flex;flex-direction:column;gap:8px;text-decoration:none;color:#163b60;background:#fff;border:1px solid #ceddec;border-radius:14px;padding:18px;min-height:125px;box-shadow:0 4px 14px #1029470a;transition:border-color .15s}
.game-option b{font-size:18px}.game-option span{color:#526981;font-size:13px;line-height:1.5;flex:1}.game-option strong{font-size:12px;color:#0c6ba7}
.game-option:hover,.game-option.chosen{border:2px solid #236cc8;background:#edf6ff}.game-option[aria-disabled=true]{pointer-events:none;opacity:.45}
.game-hint{text-align:center;margin:22px auto;padding:20px;background:#edf6ff;border-radius:12px}
.game-stage{margin-top:18px;border:1px solid #bfcee1;border-radius:18px;padding:clamp(12px,3vw,28px);background:#fff;min-height:300px;box-shadow:0 6px 30px #16344e15}
.game-playhead,.game-playhead>div,.game-ctrl{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}.game-playhead b{font-size:21px}.game-playhead span{color:#587189}
.game-ctrl button{border-radius:9px;padding:11px 16px;border:1px solid #bfd4e9;background:#f5faff;color:#144a79;font:700 14px Arial;cursor:pointer;min-height:43px}
.game-ctrl.bottom{justify-content:flex-end;margin-top:15px}.game-ctrl button:disabled{opacity:.45;cursor:default}
.game-ctrl #gameCheck{background:#1a5aa3;color:#fff}.game-score{font-size:19px;font-weight:800;margin:14px 0;color:#0b6b91}
.game-question{font-size:clamp(20px,3vw,30px);line-height:1.65;color:#112c48;min-height:80px;padding:18px;background:#f5f9ff;border-radius:12px;white-space:pre-wrap;overflow-wrap:anywhere}
.game-choices{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:16px 0}
.game-choices label{display:flex;align-items:center;gap:10px;background:#fff;border:2px solid #d4e1ef;border-radius:12px;padding:13px;min-height:55px;font-size:18px;line-height:1.5;cursor:pointer;overflow-wrap:anywhere}
.game-choices label:has(input:checked){background:#e7f3ff;border-color:#276ac4}
.game-choices input[type=text]{font:inherit;border:1px solid #b8cce4;border-radius:8px;padding:11px;width:100%;max-width:400px}
.game-choices label:has(input[type=text]){grid-column:1/-1}
.game-choices input[type=radio],.game-choices input[type=checkbox]{width:20px;height:20px;flex-shrink:0}
.game-ds{border:1px solid #d6e3f0;border-radius:10px;padding:12px;grid-column:1/-1}
.game-ds-title{font-size:17px;margin-bottom:9px}.game-ds label{display:inline-flex;margin-right:10px;min-height:40px;padding:5px 10px;font-size:15px}
#gameFeedback{font-size:18px;font-weight:700;line-height:1.55;white-space:pre-wrap}
.game-stage:fullscreen{border-radius:0;overflow-y:auto;max-width:none;padding:3vh 4vw}
.game-stage:fullscreen .game-question{font-size:clamp(27px,4.2vw,56px)}
.game-stage[data-game=tug] .game-score{color:#8d3b18}
.game-stage[data-game=fish] .game-score{color:#027b77}
@media(max-width:650px){.game-top{padding:16px;flex-direction:column;align-items:flex-start}.game-options{grid-template-columns:repeat(2,minmax(0,1fr))}.game-option{padding:12px;min-height:126px}.game-option b{font-size:15px}.game-choices{grid-template-columns:1fr}.game-choices label{font-size:16px}.game-playhead{align-items:flex-start}}
@media(max-width:380px){.game-options{grid-template-columns:1fr}}
</style>'''

GAME_JS='''<script>(function(){
const $=x=>document.getElementById(x),cfg=JSON.parse($('gameData').textContent),mode=cfg.mode;
const names={millionaire:'🏆 Triệu phú',fish:'🎣 Câu cá',tug:'🪢 Kéo co',draw:'🎲 Bốc thăm',present:'📺 Chiếu tương tác'};
let questions=[],pos=0,score=0,done=false,turn=0;
const raw=cfg.questions.slice();$('gameModeName').textContent=names[mode];
$('gameCopy').onchange=function(){const u=new URL(location.href);u.searchParams.set('copy',this.value);location.href=u.href;};
$('gameRestart').onclick=()=>restart();
$('gameFull').onclick=()=>{const e=$('gameStage');if(document.fullscreenElement)document.exitFullscreen();else if(e.requestFullscreen)e.requestFullscreen().catch(()=>{});};
function normal(s){return String(s??'').trim().replace(/\\s+/g,'').replace(/[−–]/g,'-').replace(',','.').replace(/^\\+/, '');}
function shuffle(a){for(let i=a.length-1;i>0;i--){let j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a;}
function restart(){questions=raw.slice();if(mode==='draw'||mode==='fish')shuffle(questions);pos=0;score=0;turn=0;show();}
function node(tag,cl,t){const n=document.createElement(tag);if(cl)n.className=cl;if(t!==undefined)n.textContent=t;return n;}
function label(parent,name,value,type,group){let l=node('label');let inp=document.createElement('input');inp.type=type;inp.name=group;inp.value=value;l.append(inp,node('span','',name));parent.append(l);}
function renderMath(){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise([$('gameStage')]).catch(()=>{});}
function show(){
 done=false;const q=questions[pos],choices=$('gameChoices');choices.replaceChildren();
 $('gameFeedback').textContent='';$('gameNext').disabled=true;$('gameCheck').disabled=false;
 if(!q){$('gameQuestion').textContent='🎉 Hoàn thành!';$('gameScore').textContent='Kết quả: '+score+'/'+questions.length+' câu đúng';$('gameCheck').disabled=true;return;}
 $('gameQuestion').textContent=q.text;
 $('gameProgress').textContent='Câu '+(pos+1)+' / '+questions.length;
 $('gameScore').textContent=mode==='millionaire'?'🏆 Bậc '+(score+1)+' / '+questions.length:
 mode==='fish'?'🐟 Cá đã câu: '+score:mode==='tug'?'🪢 Đội '+(turn%2?'B':'A')+' · Điểm kéo dây: '+score:
 mode==='draw'?'🎲 Lá thăm '+(pos+1)+' / '+questions.length:'✅ Đã đúng '+score+' câu';
 if(q.kind==='TN')q.options.forEach((o,i)=>label(choices,'ABCD'[i]+'. '+o.text,i,'radio','ans'));
 if(q.kind==='DS')q.statements.forEach((o,i)=>{const box=node('div','game-ds');box.append(node('div','game-ds-title','('+('abcd'[i])+') '+o.text));label(box,'Đúng','1','radio','s'+i);label(box,'Sai','0','radio','s'+i);choices.append(box)});
 if(q.kind==='TLN'){let l=node('label');l.append(node('span','', 'Trả lời ngắn: '));let input=document.createElement('input');input.type='text';input.id='gameShort';input.placeholder='Nhập đáp án';input.autocomplete='off';l.append(input);choices.append(l);}
 renderMath();
}
function check(){
 if(done)return;const q=questions[pos];if(!q)return;let ok=false;
 if(q.kind==='TN'){const a=document.querySelector('input[name=ans]:checked');if(!a)return alert('Chọn một đáp án.');ok=!!q.options[+a.value].correct;}
 if(q.kind==='DS'){const values=[0,1,2,3].map(i=>document.querySelector('input[name=s'+i+']:checked'));if(values.some(x=>!x))return alert('Chọn Đúng/Sai cho cả bốn ý.');ok=values.every((x,i)=>(x.value==='1')===!!q.statements[i].correct);}
 if(q.kind==='TLN'){const inp=$('gameShort');if(!inp||!inp.value.trim())return alert('Nhập câu trả lời.');ok=normal(inp.value)===normal(q.answer);}
 if(ok)score++;
 let answer=q.kind==='TN'?'Đáp án: '+('ABCD'[q.options.findIndex(x=>x.correct)]||'?'):
 q.kind==='DS'?'Đáp án: '+q.statements.map(x=>x.correct?'Đ':'S').join(' – '):'Đáp án: '+q.answer;
 let theme=mode==='fish'?(ok?'🐟 Câu được một con cá!':'🌊 Cá đã thoát!'):mode==='tug'?(ok?'💪 Đội kéo được dây!':'⚠️ Lượt này không kéo được dây'):mode==='millionaire'?(ok?'🏆 Lên bậc mới!':'⛔ Chưa qua bậc này'):(ok?'✅ Chính xác!':'❌ Chưa đúng.');
 $('gameFeedback').textContent=theme+'\\n'+answer+(q.solution?'\\nLời giải: '+q.solution:'');
 $('gameNext').disabled=false;$('gameCheck').disabled=true;done=true;turn++;
 renderMath();
}
$('gameCheck').onclick=check;
$('gameNext').onclick=()=>{pos++;show();};
restart();
})();</script>'''
