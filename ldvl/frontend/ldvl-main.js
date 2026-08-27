

function v253SetSubjectTabsVisible(show){let box=document.getElementById('topSubjectTabsV253');if(box)box.classList.remove('subjectTabsHiddenV253')}
document.addEventListener('DOMContentLoaded',function(){
  v253SetSubjectTabsVisible(true);
  document.body.classList.add('homeTopCompact');
  if(typeof ldvlUpdateStickyTopVar==='function')ldvlUpdateStickyTopVar();
  if(typeof ldvlQuickNavSyncVisibility==='function')ldvlQuickNavSyncVisibility();
  window.addEventListener('resize',function(){if(typeof ldvlUpdateStickyTopVar==='function')ldvlUpdateStickyTopVar();});
});

/* ==========================================================================
 * [JS-VARS] Biến toàn cục — trạng thái làm bài & học liệu
 * --------------------------------------------------------------------------
 * LEARNING_OPEN_KIND   '' | 'theory' | 'method' | 'assistant' | 'translate' — panel #hintBox
 * LEARNING_PANEL_COLLAPSED  true = panel Phương pháp đang thu (chỉ còn tiêu đề)
 * LEARNING_CACHE       cache API /api/learning/method theo Mon|Lop|…|DangBaiTap
 * HINT_BY_Q[CUR]       kết quả Soát đề GPT / Gợi ý AI cho từng câu
 * ========================================================================== */
let META=null,CATALOG=[],USER={},SID='',QUESTIONS=[],CUR=0,ANSWERS={},SUBMITTED=false,RESULTS={},CHECKED={},LOCKED_Q={},CURRENT_MADE='',CURRENT_LEVEL='',CURRENT_DANG='',CURRENT_DANGBAITAP='',DBT_UNCLASSIFIED='__CHUA_PHAN_LOAI__',DBT_UNCLASSIFIED_LABEL='Chưa phân loại',START_IS_RETRY=false,EXAM_MODE=false,GROUP_BY_DANG=true,RANDOM_PRACTICE=false,RP_SCOPE_LOCKED=false,QUIZ_ELAPSED=0,QUIZ_TIMER=null,FS_ANS_FORCE=null,FS_EXP_FORCE=null,FULLDE_ON=false,FS_NAV_HIDDEN=false,COMPLETED_NOTICE=false,CORRECT_STREAK=0,STREAK_TOAST_TIMER=null,HINT_BY_Q={},HINT_LOADING=false,HINT_LOADING_Q=null,HINT_LOADING_TICK=null,HINT_LOADING_SINCE=0,HINT_ABORT_CTRL=null,HINT_WATCHDOG=null,SIMILAR_BY_Q={},SIMILAR_LOADING=false,SIMILAR_LOADING_Q=null,MOBILE_QUIZ_TOOLS_OPEN=false,MOBILE_NAV_OPEN=false,MINI_CALC_OPEN=false,MINI_CALC_BY_Q={},QUIZ_SCROLL_Y=0,VIP_Q_SHOW_ANS={},VIP_Q_SHOW_EXP={},AI_LG_BY_Q={},ADMIN_LG_DRAFT_BY_Q={},AI_LG_LOADING=-1,AI_LG_ABORT_CTRL=null,QUIZ_TTS_ON=false,QUIZ_TTS_KIND="",QUIZ_TTS_CHUNKS=[],QUIZ_TTS_IDX=0,QUIZ_TALK_BY_Q={},QUIZ_TALK_LOADING=-1,QUIZ_TALK_ABORT_CTRL=null,QUIZ_DEBATE_BY_Q={},QUIZ_DEBATE_LOADING=-1,QUIZ_DEBATE_ABORT_CTRL=null,ADMIN_LG_SAVE_BUSY=false,ADMIN_LG_SAVED_AT=0,ADMIN_LG_SAVED_TOAST_TIMER=null,QUESTION_MODAL_MODE='edit',ADMIN_HINT_SAVED={},ADMIN_SIMILAR_EDIT_TIPS=null,LEARNING_OPEN_KIND='',LEARNING_CACHE={},LEARNING_LOADING=false,LEARNING_PANEL_COLLAPSED=false,TRANSLATE_BY_Q={},TRANSLATE_KIND='CauHoi',TRANSLATE_LOADING=false,TRANSLATE_SIDE_LOADING={},TRANSLATE_AUTO_QUEUE=[],TRANSLATE_SPEECH_CHUNKS=[],TRANSLATE_SPEECH_CHUNK_IDX=0,TRANSLATE_SPEECH_REPEAT=false,TRANSLATE_TTS_ACTIVE_BTN='',TRANSLATE_SPEECH_ACTIVE=false,TRANSLATE_SPEECH_AUTO_PLAY=false,TRANSLATE_SPEECH_RATE=0.92,FLAGGED={},FLAGGED_SID=null,PED_FORMULA_CACHE={},PED_FORMULA_LOADING={};
let ADMIN_REVIEW_MODE='fast';
function initAdminReviewMode(){try{ADMIN_REVIEW_MODE=localStorage.getItem('adminReviewMode')||'fast'}catch(e){ADMIN_REVIEW_MODE='fast'}if(ADMIN_REVIEW_MODE!=='full')ADMIN_REVIEW_MODE='fast';if(typeof onAdminReviewModeChange==='function')onAdminReviewModeChange(ADMIN_REVIEW_MODE);else try{localStorage.setItem('adminReviewMode',ADMIN_REVIEW_MODE);['adminReviewMode','adminReviewModeFs'].forEach(function(id){let el=document.getElementById(id);if(el)el.value=ADMIN_REVIEW_MODE})}catch(e2){}}
const THEME_KEY='LDVL_THEME';
function applyTheme(mode){let dark=mode==='dark';document.documentElement.setAttribute('data-theme',dark?'dark':'light');try{localStorage.setItem(THEME_KEY,dark?'dark':'light')}catch(e){}let b=document.getElementById('btnTheme');if(b){if(b.classList.contains('thbtn')){b.innerHTML=dark?'<i class="ti ti-sun"></i>':'<i class="ti ti-moon"></i>';b.title=dark?'Chuyển giao diện sáng':'Chuyển giao diện tối'}else{b.textContent=dark?'☀️':'🌙';b.title=dark?'Chuyển giao diện sáng':'Chuyển giao diện tối'}}let bf=document.getElementById('btnFsTheme');if(bf)bf.textContent=dark?'☀️ Sáng':'🌙 Tối';if(window.MathJax&&MathJax.config&&MathJax.config.svg){MathJax.config.svg.color=dark?'#e2e8f0':'#0f172a';if(MathJax.typesetPromise)MathJax.typesetPromise().catch(()=>{})}}
function toggleTheme(){let cur=document.documentElement.getAttribute('data-theme')||'light';applyTheme(cur==='dark'?'light':'dark')}
function initTheme(){let t='light';try{t=localStorage.getItem(THEME_KEY)||'light'}catch(e){}applyTheme(t==='dark'?'dark':'light')}
function enhanceHomeColors(){
    if(document.getElementById('LDVL_HOME_COLORS'))return;
    let st=document.createElement('style');
    st.id='LDVL_HOME_COLORS';
    st.textContent=
        ".card{border:1px solid #bfdbfe;border-radius:14px;background:linear-gradient(180deg,#ffffff,#f8fbff);box-shadow:0 8px 22px #1d4ed81a}"+
        ".card h3{color:#1e40af;font-size:30px;font-weight:900;letter-spacing:.2px}"+
        ".tag{background:linear-gradient(135deg,#dbeafe,#bfdbfe);color:#1d4ed8;border:1px solid #93c5fd;padding:4px 10px;font-weight:900}"+
        ".btnStartStrong{box-shadow:0 10px 22px #4338ca55,0 2px 6px #1e40af55;transform:translateZ(0)}"+
        ".btnStartStrong:hover{filter:brightness(1.08);transform:translateY(-1px)}"+
        "html[data-theme='dark'] .card{background:linear-gradient(180deg,#1e293b,#182236);border-color:#334155;box-shadow:0 10px 24px #0005}"+
        "html[data-theme='dark'] .card h3{color:#93c5fd}"+
        "html[data-theme='dark'] .tag{background:linear-gradient(135deg,#1e3a5f,#1d4ed8);color:#e0ecff;border-color:#3b82f6}"+
        ".shareRow{margin-top:8px;padding:6px 8px;border:1px dashed #93c5fd;border-radius:10px;background:#f8fbff;display:flex;flex-wrap:nowrap;gap:6px;align-items:center;justify-content:space-between;overflow:hidden}"+
        ".shareUrl{font-size:11px;color:#64748b;flex:1 1 auto;min-width:0;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"+
        ".shareBtns{display:flex;gap:6px;flex:0 0 auto;white-space:nowrap}"+
        ".btnShare{font-size:11px;padding:5px 8px;border-radius:8px;border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;font-weight:800;white-space:nowrap}"+
        ".btnShare:hover{filter:brightness(1.03)}"+
        ".card.shareTarget{outline:3px solid #60a5fa;box-shadow:0 0 0 4px #dbeafe}"+
        "html[data-theme='dark'] .shareRow{background:#1e293b;border-color:#3b82f6}"+
        "html[data-theme='dark'] .shareUrl{color:#94a3b8}"+
        "html[data-theme='dark'] .btnShare{background:#1e3a5f;color:#bfdbfe;border-color:#3b82f6}"+
        ".shortAnsFb{padding:8px 10px;border-radius:8px;margin-top:8px;font-weight:800;line-height:1.45}"+
        ".shortAnsFb.ok{background:#dcfce7;color:#166534;border:1px solid #86efac}"+
        ".shortAnsFb.bad{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}"+
        ".shortAnsBox.correct{border-color:#86efac!important;box-shadow:0 0 0 2px #dcfce7}"+
        ".shortAnsBox.wrong{border-color:#fecaca!important;box-shadow:0 0 0 2px #fee2e2}"+
        ".adminTlnAns{margin-top:8px;padding:8px 10px;border-radius:8px;background:#dcfce7;border:1px solid #86efac;color:#166534;font-weight:800;line-height:1.45}"+
        ".adminTlnAnsWarn{background:#fff7ed;border-color:#fed7aa;color:#9a3412;font-weight:700}"+
        ".mucdoBadge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:900;letter-spacing:.4px;border:2px solid transparent;vertical-align:middle;line-height:1.35;margin:0 2px}"+
        ".mucdo-nb{background:#dcfce7;color:#166534;border-color:#86efac}"+
        ".mucdo-th{background:#dbeafe;color:#1d4ed8;border-color:#93c5fd}"+
        ".mucdo-vd{background:#ffedd5;color:#c2410c;border-color:#fdba74}"+
        ".mucdo-vdc{background:#fee2e2;color:#991b1b;border-color:#fca5a5}"+
        ".mucdo-other{background:#f1f5f9;color:#334155;border-color:#cbd5e1}"+
        ".mucdo-empty{background:#f8fafc;color:#94a3b8;border-color:#e2e8f0;font-weight:700}.mucdoBadge{display:inline-flex;align-items:center;gap:4px}.mucdoIcon{font-size:13px;line-height:1}.mucdoFull{font-size:10px;opacity:.88;font-weight:800}.navNums .num{position:relative!important;overflow:visible!important}.navNums .num .navLvIcon{display:none!important}.navNums .num .navNumText{position:relative;z-index:1}.navNums .num .navLvBadge{position:absolute!important;top:0!important;right:0!important;transform:translate(18%,-22%)!important;font-size:8px!important;line-height:1.05!important;padding:1px 4px!important;border-radius:5px!important;font-weight:900!important;letter-spacing:.25px!important;border:1px solid transparent!important;z-index:3!important;pointer-events:none!important;box-shadow:0 1px 2px #00000022!important}.navNums .num.ok .navLvBadge,.navNums .num.bad .navLvBadge{display:none!important}.navMucDoLegend{display:flex!important;flex-wrap:wrap!important;gap:4px!important;margin:4px 0 6px!important}.navMucDoLegend .navLvBadge{position:static!important;transform:none!important;font-size:9px!important;padding:2px 5px!important;box-shadow:none!important}.navNums .num.nav-mucdo-nb{border-color:#86efac!important;background:#f0fdf4!important;color:#166534!important}.navNums .num.nav-mucdo-th{border-color:#93c5fd!important;background:#eff6ff!important;color:#1d4ed8!important}.navNums .num.nav-mucdo-vd{border-color:#fdba74!important;background:#fff7ed!important;color:#c2410c!important}.navNums .num.nav-mucdo-vdc{border-color:#fca5a5!important;background:#fef2f2!important;color:#991b1b!important}.navNums .num.active{outline:3px solid #1d4ed855;transform:translateY(-1px)}.navNums .num.ok,.navNums .num.bad{color:#fff!important}.navNums .num.ok .navLvIcon,.navNums .num.bad .navLvIcon{display:none!important}"+
        ".editLearningBox textarea{font-size:13px;line-height:1.45}.editLearningBox .editGrid{grid-template-columns:repeat(2,minmax(0,1fr))}@media(max-width:700px){.editLearningBox .editGrid{grid-template-columns:1fr!important}.editLearningBox textarea{font-size:15px;line-height:1.6}.editLearningBox h3{font-size:17px}.editLearningBox button{font-size:13px;padding:8px 10px}}"+
        ".qidDang{font-weight:800;color:var(--heading)}"+
        "html[data-theme='dark'] .mucdo-nb{background:#14532d;color:#bbf7d0;border-color:#22c55e}"+
        "html[data-theme='dark'] .mucdo-th{background:#1e3a5f;color:#bfdbfe;border-color:#3b82f6}"+
        "html[data-theme='dark'] .mucdo-vd{background:#7c2d12;color:#fed7aa;border-color:#ea580c}"+
        "html[data-theme='dark'] .mucdo-vdc{background:#450a0a;color:#fecaca;border-color:#ef4444}html[data-theme='dark'] .quizQuestionPanel.mucdoPanel-nb{box-shadow:0 0 0 2px #14532d,0 1px 4px #0004}html[data-theme='dark'] .quizQuestionPanel.mucdoPanel-th{box-shadow:0 0 0 2px #1e3a5f,0 1px 4px #0004}html[data-theme='dark'] .quizQuestionPanel.mucdoPanel-vd{box-shadow:0 0 0 2px #7c2d12,0 1px 4px #0004}html[data-theme='dark'] .quizQuestionPanel.mucdoPanel-vdc{box-shadow:0 0 0 2px #450a0a,0 1px 4px #0004}html[data-theme='dark'] .navNums .num.nav-mucdo-nb{background:#14532d;color:#bbf7d0}html[data-theme='dark'] .navNums .num.nav-mucdo-th{background:#1e3a5f;color:#bfdbfe}html[data-theme='dark'] .navNums .num.nav-mucdo-vd{background:#7c2d12;color:#fed7aa}html[data-theme='dark'] .navNums .num.nav-mucdo-vdc{background:#450a0a;color:#fecaca}"+
        ".adminAnalysisCard{margin-bottom:10px}"+
        ".adminAnalysisOk{padding:8px 10px;border-radius:8px;background:#dcfce7;border:1px solid #86efac;color:#166534;font-weight:800}"+
        ".adminAnalysisWarn{padding:8px 10px;border-radius:8px;background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;font-weight:800;line-height:1.45}"+
        ".adminAnalysisTbl{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px}"+
        ".adminAnalysisTbl th,.adminAnalysisTbl td{border:1px solid var(--border);padding:5px 7px;text-align:center}"+
        ".adminAnalysisTbl th{background:#f1f5f9;font-weight:800}"+
        ".adminAnalysisBadRow td{background:#fee2e2}"+
        ".adminAnalysisOkRow td{background:#f0fdf4}"+
        ".aiProfileBadge{display:inline-block;margin-left:6px;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:900;vertical-align:middle;white-space:nowrap}"+
        ".aiProfileOwn{background:#dcfce7;color:#166534;border:1px solid #86efac}"+
        ".aiProfilePool{background:#fff7ed;color:#9a3412;border:1px solid #fed7aa}"+
        ".aiProfileWarn{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}"+
        ".aiProfileFree{background:#f1f5f9;color:#64748b;border:1px solid #cbd5e1}"+
        ".aiProfileBanner{margin:0 0 12px;padding:12px 14px;border-radius:12px;border:1px solid var(--border);background:var(--surface);line-height:1.5}"+
        ".aiProfileBannerOk{border-color:#86efac;background:#f0fdf4}"+
        ".aiProfileBannerNudge{border-color:#fed7aa;background:#fff7ed}"+
        ".aiProfileBannerErr{border-color:#fca5a5;background:#fef2f2}"+
        ".aiProfileBannerTxt{margin-top:4px;font-size:13px;color:var(--muted)}"+
        ".aiProfileBannerBtn{margin-top:8px}"+
        ".topUserChip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:#ffffff22;border:1px solid #ffffff55;font-size:12px;font-weight:800;max-width:min(320px,42vw);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;vertical-align:middle}"+
        ".topRolePill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:900;letter-spacing:.03em;flex-shrink:0}"+
        ".topRolePill.roleADMIN{background:#7c3aed;color:#fff}"+
        ".topRolePill.roleSVIP{background:linear-gradient(135deg,#f59e0b,#ea580c);color:#fff}"+
        ".topRolePill.roleVIP{background:#2563eb;color:#fff}"+
        ".topRolePill.roleTRIAL{background:#ea580c;color:#fff}"+
        ".topRolePill.roleFREE{background:#64748b;color:#fff}"+
        ".userAccountCard{margin:0 0 14px;padding:16px 18px;border-radius:16px;border:2px solid var(--border);background:linear-gradient(135deg,#ffffff,#f8fbff);box-shadow:0 10px 28px #1d4ed81a;line-height:1.45}"+
        ".userAccountCard.roleADMIN{border-color:#a78bfa;background:linear-gradient(135deg,#faf5ff,#f3e8ff)}"+
        ".userAccountCard.roleSVIP{border-color:#fdba74;background:linear-gradient(135deg,#fff7ed,#ffedd5)}"+
        ".userAccountCard.roleVIP{border-color:#93c5fd;background:linear-gradient(135deg,#eff6ff,#dbeafe)}"+
        ".userAccountCard.roleTRIAL{border-color:#fdba74;background:linear-gradient(135deg,#fff7ed,#fef3c7)}"+
        ".userAccountCard.roleFREE{border-color:#cbd5e1;background:linear-gradient(135deg,#f8fafc,#f1f5f9)}"+
        ".userAccountHead{display:flex;flex-wrap:wrap;align-items:center;gap:12px 16px}"+
        ".userAccountAvatar{width:52px;height:52px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:900;flex-shrink:0;background:linear-gradient(135deg,#1d4ed8,#7c3aed);color:#fff;box-shadow:0 4px 14px #1d4ed833}"+
        ".userAccountCard.roleADMIN .userAccountAvatar{background:linear-gradient(135deg,#7c3aed,#5b21b6)}"+
        ".userAccountCard.roleSVIP .userAccountAvatar{background:linear-gradient(135deg,#f59e0b,#ea580c)}"+
        ".userAccountCard.roleVIP .userAccountAvatar{background:linear-gradient(135deg,#2563eb,#1d4ed8)}"+
        ".userAccountCard.roleTRIAL .userAccountAvatar{background:linear-gradient(135deg,#ea580c,#c2410c)}"+
        ".userAccountCard.roleFREE .userAccountAvatar{background:linear-gradient(135deg,#64748b,#475569)}"+
        ".userAccountMain{flex:1;min-width:200px}"+
        ".userAccountName{font-size:22px;font-weight:900;color:var(--heading);letter-spacing:.01em}"+
        ".userAccountMeta{margin-top:4px;font-size:13px;color:var(--muted);font-weight:700}"+
        ".userRoleBadge{display:inline-flex;align-items:center;padding:8px 16px;border-radius:999px;font-size:15px;font-weight:900;letter-spacing:.04em;flex-shrink:0;box-shadow:0 4px 12px #00000014}"+
        ".userRoleBadge.roleADMIN{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff}"+
        ".userRoleBadge.roleSVIP{background:linear-gradient(135deg,#f59e0b,#ea580c);color:#fff}"+
        ".userRoleBadge.roleVIP{background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff}"+
        ".userRoleBadge.roleTRIAL{background:linear-gradient(135deg,#fb923c,#ea580c);color:#fff}"+
        ".userRoleBadge.roleFREE{background:linear-gradient(135deg,#94a3b8,#64748b);color:#fff}"+
        ".userBenefitsTitle{margin:14px 0 8px;font-size:13px;font-weight:900;color:var(--heading);text-transform:uppercase;letter-spacing:.06em}"+
        ".userBenefits{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px 12px}"+
        ".userBenefitItem{display:flex;gap:8px;align-items:flex-start;font-size:14px;font-weight:700;padding:8px 10px;border-radius:10px;background:#ffffffaa;border:1px solid #ffffffcc}"+
        ".userBenefitItem::before{content:'✓';color:#16a34a;font-weight:900;flex-shrink:0}"+
        ".userAccountExpiry{margin-top:10px;font-size:12px;font-weight:800;color:#9a3412}"+
        ".userAccountCard.compactHomeAccount{margin:0 0 8px!important;padding:8px 12px!important;border-width:1px!important;border-radius:12px!important;box-shadow:0 2px 8px #1d4ed812!important}"+
        ".compactHomeAccount .userAccountHead{gap:8px!important;flex-wrap:nowrap!important}.compactHomeAccount .userAccountAvatar{width:34px!important;height:34px!important;border-radius:10px!important;font-size:18px!important}.compactHomeAccount .userAccountName{font-size:17px!important;line-height:1.2!important}.compactHomeAccount .userAccountMeta{margin-top:1px!important;font-size:12px!important}.compactHomeAccount .userRoleBadge{padding:5px 10px!important;font-size:12px!important;box-shadow:none!important}.compactHomeAccount .userBenefitsTitle,.compactHomeAccount .userBenefits{display:none!important}.compactHomeAccount .userAccountExpiry{margin-top:4px!important;font-size:11px!important}"+
        ".aiProfileBanner.aiProfileBannerCompact{display:flex!important;align-items:center!important;gap:8px!important;flex-wrap:wrap!important;margin:0 0 8px!important;padding:7px 10px!important;border-radius:10px!important;line-height:1.25!important;font-size:12px!important}.aiProfileBannerCompact .aiProfileBannerTxt{margin:0!important;font-size:12px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;max-width:min(720px,70vw)!important}.aiProfileBannerCompact .aiProfileBannerBtn{margin:0!important;padding:5px 8px!important;font-size:12px!important}"+
        ".compactKeyCard.aiKeyCollapsed .aiProfileBanner,.compactKeyCard.aiKeyCollapsed p,.compactKeyCard.aiKeyCollapsed textarea,.compactKeyCard.aiKeyCollapsed .row,.compactKeyCard.aiKeyCollapsed #aiKeyStatus{display:none!important}.compactKeyCard.aiKeyCollapsed{min-height:0!important}.aiKeyMiniToggle{float:right;font-size:11px!important;padding:4px 8px!important;margin-left:8px!important;border-radius:999px!important}"+
        "@media(max-width:760px){.compactHomeAccount .userAccountHead{flex-wrap:wrap!important}.compactHomeAccount .userRoleBadge{margin-left:auto}.aiProfileBannerCompact .aiProfileBannerTxt{max-width:100%!important;white-space:normal!important}.aiKeyMiniToggle{float:none;margin-top:4px!important}}"+
        "html[data-theme='dark'] .userAccountCard{background:linear-gradient(135deg,#1e293b,#172033);border-color:#334155}"+
        "html[data-theme='dark'] .userAccountCard.roleADMIN{background:linear-gradient(135deg,#2e1065,#1e1b4b);border-color:#7c3aed}"+
        "html[data-theme='dark'] .userAccountCard.roleSVIP{background:linear-gradient(135deg,#422006,#3b1f0a);border-color:#c2410c}"+
        "html[data-theme='dark'] .userAccountCard.roleVIP{background:linear-gradient(135deg,#1e3a5f,#172554);border-color:#3b82f6}"+
        "html[data-theme='dark'] .userBenefitItem{background:#0f172a88;border-color:#334155}"+
        ".adminChipRow{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}"+
        ".adminChip{border:1px solid var(--border);background:var(--surface);color:var(--text);padding:7px 12px;border-radius:999px;font-size:13px;font-weight:800;cursor:pointer;line-height:1.2}"+
        ".adminChip:hover{border-color:#93c5fd;background:#eff6ff}"+
        ".adminChipOn{background:linear-gradient(135deg,#1d4ed8,#2563eb);color:#fff;border-color:#1d4ed8;box-shadow:0 2px 8px #1d4ed844}"+
        ".adminChip.mucdo-nb.adminChipOn{background:linear-gradient(135deg,#22c55e,#16a34a);border-color:#22c55e}"+
        ".adminChip.mucdo-th.adminChipOn{background:linear-gradient(135deg,#3b82f6,#2563eb);border-color:#3b82f6}"+
        ".adminChip.mucdo-vd.adminChipOn{background:linear-gradient(135deg,#f59e0b,#ea580c);border-color:#f59e0b}"+
        ".adminChip.mucdo-vdc.adminChipOn{background:linear-gradient(135deg,#dc2626,#b91c1c);border-color:#dc2626}"+
        ".adminChipFree.adminChipOn{background:linear-gradient(135deg,#64748b,#475569);border-color:#64748b}"+
        ".adminChipVip.adminChipOn{background:linear-gradient(135deg,#7c3aed,#6d28d9);border-color:#7c3aed}"+
        ".adminChip.reviewChipOk.adminChipOn{background:linear-gradient(135deg,#22c55e,#16a34a);border-color:#22c55e}"+
        ".adminChip.reviewChipPending.adminChipOn{background:linear-gradient(135deg,#f97316,#ea580c);border-color:#f97316}"+
        ".adminQuickField{margin-bottom:12px}"+
        ".adminDapAnUi{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 8px}"+
        ".adminMcqDapAnUi .adminChip{min-width:44px;font-size:15px;font-weight:800;padding:8px 14px}"+
        ".adminDsDapAnUi{flex-direction:column;gap:6px}"+
        ".adminDsDapRow{display:flex;align-items:center;gap:8px;flex-wrap:wrap}"+
        ".adminDsDapLbl{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:#e2e8f0;font-weight:800;font-size:13px;flex-shrink:0}"+
        ".adminDsDapRow .adminChip{min-width:64px;padding:6px 12px}"+
        ".adminDsDapRow .adminChip.dsVerdictDung.adminChipOn{background:linear-gradient(135deg,#22c55e,#16a34a);border-color:#22c55e;color:#fff}"+
        ".adminDsDapRow .adminChip.dsVerdictSai.adminChipOn{background:linear-gradient(135deg,#ef4444,#dc2626);border-color:#ef4444;color:#fff}"+
        ".adminDapAnRaw{width:100%;min-height:52px;font-size:13px;line-height:1.4}"+
        ".adminQuickField input[type=hidden]{display:none}"+
        ".adminDbtSelect{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:8px;font:inherit;font-weight:700;margin-bottom:6px;background:var(--surface)}"+
        ".adminDbtInput{width:100%;padding:8px 10px;border:1px solid #fde68a;border-radius:8px;font:inherit;background:#fffbeb;box-sizing:border-box}"+
        ".adminDbtInput.hide{display:none}"+
        ".adminDbtHint{font-size:11px;margin-top:4px;line-height:1.35}"+
        ".adminDbtScope{font-size:11px;color:#1d4ed8;font-weight:850;margin:0 0 6px;line-height:1.35}"+
        ".adminDbtDup{font-size:11px;margin-top:4px;color:#92400e;font-weight:800;line-height:1.35}"+
        ".solFullTag{background:#dcfce7!important;color:#166534!important;border:1px solid #86efac!important}"+
        ".solPartTag{background:#fff7ed!important;color:#9a3412!important;border:1px solid #fed7aa!important}"+
        ".quizSectionHead{margin:12px 0 8px;padding:10px 12px;border-radius:10px;background:linear-gradient(135deg,#eff6ff,#dbeafe);border:1px solid #93c5fd;font-weight:900;color:#1e3a8a}"+
        ".navSectionLbl{grid-column:1/-1;font-size:11px;font-weight:900;color:#1d4ed8;padding:4px 2px 0;text-align:center;justify-content:center}"+
        ".practiceRandomPanel{border:1px solid #93c5fd;background:linear-gradient(135deg,#eff6ff,#f0fdf4)}"+
        ".rpChuongList{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}"+
        ".rpChuongList label{display:flex;gap:6px;align-items:center;padding:6px 10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--surface);cursor:pointer}"+
        ".rpChuongList label.rpChOn{border-color:#3b82f6;background:#eff6ff;font-weight:800}"+
        ".practiceRandomPanel.rpLocked select.rpLockable{background:#f1f5f9;opacity:.92}";
    document.head.appendChild(st);
}
function shortAnswerFeedbackHtml(q){let r=RESULTS[CUR]||CHECKED[CUR];if(!r||!(r.ok===true||r.ok===false))return '';let chosen=esc(String(r.chosen||ANSWERS[CUR]||'').trim());if(r.ok===true)return `<div class="shortAnsFb ok">✅ <b>Đúng!</b>${chosen?` Bạn nhập: <b>${chosen}</b>`:''}</div>`;let extra='';if(canViewSolutionLive()||USER.is_admin){let cor=esc(String(r.correct||r.DapAn||q.DapAn||'').trim());if(cor)extra=`<div style="margin-top:4px;font-size:13px">Đáp án đúng: <b>${cor}</b></div>`}else extra='<div style="margin-top:4px;font-size:12px;font-weight:600">Nâng VIP để xem đáp án đúng ngay sau khi kiểm tra.</div>';return `<div class="shortAnsFb bad">❌ <b>Chưa đúng.</b> Bạn nhập: <b>${chosen||'—'}</b></div>${extra}`}
function examDisplayTitle(item){item=item||{};let mon=String(item.Mon||'').trim();let lop=String(item.Lop||'').trim();let bai=String(item.BaiHoc||item.De||'Đề luyện tập').trim();if(mon){let head=lop?mon+' - Lớp '+lop:mon;return head+' | '+bai}if(lop)return'Lớp '+lop+' | '+bai;return bai}
function getShareParams(){let p=new URLSearchParams(location.search);let de=(p.get('de')||p.get('made')||'').trim();if(!de){let m=location.pathname.match(/^\/d\/([^/]+)/i);if(m)de=decodeURIComponent(m[1])}let fromShort=/^\/d\//i.test(location.pathname);let open=p.get('open')==='1';let exam=(p.get('exam')||p.get('exam_code')||'').trim().toUpperCase();return{de,exam,level:(p.get('level')||'').trim().toUpperCase(),dang:(p.get('dang')||'').trim(),start:p.get('start')==='1'||(fromShort&&!open)||!!exam,open:!fromShort&&!exam?p.get('start')!=='1'&&(p.get('open')||'1')!=='0':open,sq:p.get('sq')==='1',sa:p.get('sa')==='1'}}
function buildExamShareUrl(item,extra){item=item||{};extra=extra||{};if(extra.exam){let u=new URL(location.origin+'/');u.searchParams.set('exam',String(extra.exam).toUpperCase());u.searchParams.set('start','1');return u.toString()}let de=extra.de||item.MaDe||'';if(!de)return location.origin+'/';let auto=extra.start!==0&&extra.start!=='0';let u=new URL(location.origin+'/d/'+de);if(!auto)u.searchParams.set('open','1');if(extra.sq)u.searchParams.set('sq','1');if(extra.sa)u.searchParams.set('sa','1');let lv=extra.level||val('fMucDo')||'';let dg=extra.dang||val('fDang')||'';if(lv)u.searchParams.set('level',lv);if(dg)u.searchParams.set('dang',dg);return u.toString()}
function clearShareQuery(){let p=new URLSearchParams(location.search);if(!p.get('de')&&!p.get('made')&&!p.get('exam')&&!p.get('exam_code'))return;['de','made','mon','lop','chuong','baihoc','bode','level','dang','open','start','sq','sa','exam','exam_code'].forEach(k=>p.delete(k));let q=p.toString();history.replaceState(null,'',location.pathname+(q?'?'+q:''))}
function setSel(id,v){let el=document.getElementById(id);if(!el||!v)return;for(let o of el.options){if(o.value===v){el.value=v;return}}let opt=document.createElement('option');opt.value=v;opt.textContent=v;el.appendChild(opt);el.value=v}
async function copyTextToClipboard(text){try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(text);return true}}catch(e){}let ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();try{document.execCommand('copy');document.body.removeChild(ta);return true}catch(e){document.body.removeChild(ta);return false}}
async function copyExamShareLink(made,withModal){let item=CATALOG.find(x=>x.MaDe===made);if(!item){alert('Không tìm thấy đề.');return}let url=buildExamShareUrl(item,withModal?{start:0,open:1}:{start:1});let ok=await copyTextToClipboard(url);let ten=examDisplayTitle(item);let socau=item.SoCau?(item.SoCau+' câu'):'';let note=withModal?'Học viên mở link sẽ chọn xáo trộn trước khi làm.':'Học viên mở link sẽ vào làm bài luôn.';alert(ok?'✅ Đã chép link gửi Zalo/Messenger.\n\n'+ten+(socau?'\n'+socau:'')+'\n'+note:'Không chép được. Hãy bấm lại nút Chép link.')}
const LDVL_OFFLINE_CACHE_KEY='LDVL_OFFLINE_CACHE_V1';
let LDVL_OFFLINE_SESSIONS={};
function readOfflineCache(){try{let o=JSON.parse(localStorage.getItem(LDVL_OFFLINE_CACHE_KEY)||'{}');return o&&typeof o==='object'?o:{decks:{},saved_at:{}}}catch(e){return{decks:{},saved_at:{}}}}
function writeOfflineCache(c){try{localStorage.setItem(LDVL_OFFLINE_CACHE_KEY,JSON.stringify(c));return true}catch(e){return false}}
function offlineNormLetter(v){let s=String(v||'').trim().toUpperCase().replace(/\u0110/g,'D');return /^[ABCD]$/.test(s)?s:''}
function offlineParseFloatVn(v){let s=String(v||'').trim().replace(/\s/g,'').replace(',','.');if(!s)return null;let n=parseFloat(s);return isNaN(n)?null:n}
function offlineCacheDeck(made){made=String(made||'').trim();let c=readOfflineCache();return c.decks&&c.decks[made]?c.decks[made]:null}
function clearOfflineDeckForMade(made){made=String(made||'').trim();if(!made)return;try{let c=readOfflineCache();if(c.decks&&c.decks[made]){delete c.decks[made]}if(c.saved_at&&c.saved_at[made])delete c.saved_at[made];writeOfflineCache(c)}catch(e){}}
function clearOfflineDecksContainingIds(ids){let set=new Set((ids||[]).map(x=>String(x||'').trim()).filter(Boolean));if(!set.size)return;try{let c=readOfflineCache();let decks=c.decks||{};for(let made of Object.keys(decks)){let qs=(decks[made]&&decks[made].deck&&decks[made].deck.questions)||[];if(qs.some(q=>set.has(String(q.ID||'')))){delete decks[made];if(c.saved_at)delete c.saved_at[made]}}writeOfflineCache(c)}catch(e){}}
function offlineGradeOne(q,ans){let dang=typeof resolveDang==='function'?resolveDang(q):String((q&&q.Dang)||'Trắc nghiệm');let cor=String((q&&q.DapAn)||'').trim(),chosen=String(ans==null?'':ans).trim();if(dang==='Trắc nghiệm'){let c=offlineNormLetter(cor),ch=offlineNormLetter(chosen);return{ok:!!(c&&ch&&c===ch),correct:c,chosen:ch,DapAn:q.DapAn||'',LoiGiai:q.LoiGiai||''}}if(dang==='Đúng sai'){let corr=parseTfClient(cor),sel=parseTfClient(ans),bitsC=[],bitsS=[];for(let i=0;i<4;i++){let L='ABCD'[i];if(!String(q[L]||'').trim())continue;bitsC.push(corr[i]||'');bitsS.push(sel[i]||'')}let ok=bitsC.length>=2&&bitsC.every(Boolean)&&bitsS.every(Boolean)&&bitsC.join(',')===bitsS.join(',');return{ok,correct:cor,chosen:bitsS.join(','),DapAn:q.DapAn||'',LoiGiai:q.LoiGiai||''}}if(dang==='Trả lời ngắn'){let cn=offlineParseFloatVn(cor),un=offlineParseFloatVn(chosen),tol=offlineParseFloatVn(q.SaiSo);if(tol==null)tol=0;if(cn!=null&&un!=null)return{ok:Math.abs(cn-un)<=tol+1e-12,correct:cor,chosen,DapAn:q.DapAn||'',LoiGiai:q.LoiGiai||''};return{ok:normText(cor)===normText(chosen),correct:cor,chosen,DapAn:q.DapAn||'',LoiGiai:q.LoiGiai||''}}return{ok:false,correct:cor,chosen,DapAn:q.DapAn||'',LoiGiai:q.LoiGiai||''}}
function routeCachedApi(url,opts){if(window.LDVL_OFFLINE)return null;let method=String((opts&&opts.method)||'GET').toUpperCase();let path=String(url||'').split('?')[0];let body={};try{body=JSON.parse((opts&&opts.body)||'{}')}catch(e){}if(path==='/api/start'&&method==='POST'){let made=String(body.made||body.MaDe||'').trim();let hit=offlineCacheDeck(made);if(!hit||!hit.deck)return{error:'Đề «'+made+'» chưa lưu offline. Khi có mạng, bấm 📴 Lưu offline ở mục lục.'};let deck=Object.assign({},hit.deck);let sid=deck.sid||('off_'+made);LDVL_OFFLINE_SESSIONS[sid]=deck;return Object.assign({},deck,{sid})}if(path==='/api/check-one'&&method==='POST'){let ses=LDVL_OFFLINE_SESSIONS[body.sid];if(!ses)return{error:'Phiên làm bài hết hạn — mở lại đề.'};let idx=parseInt(body.index,10)||0,qs=ses.questions||[],q=qs[idx];if(!q)return{error:'Câu không hợp lệ'};let g=offlineGradeOne(q,body.answer);return{index:idx,ID:q.ID,Dang:q.Dang,ok:g.ok,correct:g.correct,chosen:g.chosen,DapAn:g.DapAn,LoiGiai:g.LoiGiai}}if(path==='/api/submit'&&method==='POST'){let ses=LDVL_OFFLINE_SESSIONS[body.sid];if(!ses)return{error:'Phiên làm bài hết hạn.'};let qs=ses.questions||[],answers=body.answers||{},results=[],correct=0,auto=0;for(let i=0;i<qs.length;i++){let q=qs[i],dang=typeof resolveDang==='function'?resolveDang(q):String(q.Dang||'');if(dang==='Tự luận')continue;auto++;let g=offlineGradeOne(q,answers[i]);if(g.ok)correct++;results.push({index:i,ok:g.ok,correct:g.correct,chosen:g.chosen})}return{score:auto?Math.round(correct/auto*100)/10:0,correct_count:correct,auto_count:auto,results}}return null}
async function saveExamOffline(made){made=String(made||'').trim();if(!made)return;let item=CATALOG.find(x=>x.MaDe===made);if(!item){alert('Không tìm thấy đề.');return}if(!confirm('Lưu đề «'+examDisplayTitle(item)+'» vào máy để luyện khi mất mạng?\n\nCó thể lưu nhiều đề — app tự dùng bản đã lưu.'))return;let btn=window.event&&window.event.target;if(btn&&btn.tagName==='BUTTON'){btn.disabled=true;btn.textContent='⏳ Đang lưu...'}try{let j=await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({made,shuffle_questions:false,shuffle_options:false,group_by_dang:true})});let cache=readOfflineCache();cache.decks=cache.decks||{};cache.decks[made]={deck:j,item:item,saved_at:new Date().toISOString()};cache.saved_at=cache.saved_at||{};cache.saved_at[made]=cache.decks[made].saved_at;if(!writeOfflineCache(cache))throw new Error('Bộ nhớ máy đầy — hãy xóa bớt đề offline cũ.');alert('✅ Đã lưu offline:\n'+examDisplayTitle(item)+'\n\nKhi mất mạng, mở lại đề này — app dùng bản đã lưu.')}catch(e){alert('Lưu offline thất bại: '+(e.message||e))}finally{if(btn&&btn.tagName==='BUTTON'){btn.disabled=false;btn.textContent='📴 Lưu offline'}}}
async function downloadOfflinePack(){if(!USER||!USER.is_admin){alert('Chỉ ADMIN được tải gói offline APK.');return}if(!confirm('Tải ZIP gói offline (toàn bộ đề + JSON bank)?\n\nNên chạy trên máy mạnh / hoặc python build_offline_pack.py nếu Sheet rất lớn.\nCó thể chờ vài phút.'))return;try{let r=await fetch('/api/admin/offline-pack',{method:'POST'});if(!r.ok){let j={};try{j=await r.json()}catch(e){}throw new Error(j.error||('HTTP '+r.status))}let blob=await r.blob();let fn='luyen-de-offline.zip';let cd=r.headers.get('Content-Disposition')||'';let m=cd.match(/filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)/i);if(m)fn=decodeURIComponent(m[1]||m[2]||fn);let url=URL.createObjectURL(blob);let a=document.createElement('a');a.href=url;a.download=fn;a.click();URL.revokeObjectURL(url);alert('✅ Đã tải gói offline ZIP.\n\n• www/ → nhét vào APK (Capacitor/Android assets)\n• pack/bank.json = toàn bộ câu JSON\n• Xem README.txt trong ZIP')}catch(e){alert('Tải gói offline thất bại: '+(e.message||e))}}
async function downloadBankJson(){if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return}if(!confirm('Xuất JSON toàn bộ câu hỏi đang nạp từ Google Sheet?\n\nDùng để nhét APK hoặc đặt QUESTION_SOURCE=JSON_ONLY (đọc mượt, không lag Sheet).'))return;try{let r=await fetch('/api/admin/export-bank-json',{method:'POST'});if(!r.ok){let j={};try{j=await r.json()}catch(e){}throw new Error(j.error||('HTTP '+r.status))}let blob=await r.blob();let fn='bank_full.json';let cd=r.headers.get('Content-Disposition')||'';let m=cd.match(/filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)/i);if(m)fn=decodeURIComponent(m[1]||m[2]||fn);let url=URL.createObjectURL(blob);let a=document.createElement('a');a.href=url;a.download=fn;a.click();URL.revokeObjectURL(url);alert('✅ Đã tải '+fn+'.\n\nCopy vào data/json_questions/bank_full.json rồi đặt QUESTION_SOURCE=JSON_ONLY nếu muốn server đọc JSON thay Sheet.')}catch(e){alert('Xuất JSON thất bại: '+(e.message||e))}}
window.downloadBankJson=downloadBankJson;
function v246ShareToolsHtml(item,madeEsc){if(!madeEsc||!item)return '';let shareLabel=esc(examDisplayTitle(item));let latexBtn=(USER&&USER.is_admin)?`<button type="button" class="btnShare" onclick="downloadExamLatex('${madeEsc}')" title="Tải file .tex (\\begin{ex}...\\choiceTF...\\loigiai)">📄 Xuất LaTeX</button>`:'';return `<div class="shareRow"><span class="shareUrl" title="${shareLabel}">🔗 ${shareLabel}</span><span class="shareBtns"><button type="button" class="btnShare" onclick="copyExamShareLink('${madeEsc}')">📋 Chép link</button><button type="button" class="btnShare" onclick="copyExamShareLink('${madeEsc}',1)" title="Học viên tự chọn xáo trộn">⚙️ Link xáo</button><button type="button" class="btnShare" onclick="saveExamOffline('${madeEsc}')" title="Lưu vào máy — luyện khi mất mạng">📴 Lưu offline</button>${latexBtn}</span></div>`}
function latexExportDownloadUrl(params){let p=new URLSearchParams();Object.keys(params||{}).forEach(function(k){let v=params[k];if(v!=null&&String(v).trim()!=='')p.set(k,String(v))});p.set('download','1');return '/api/latex/export?'+p.toString()}
function downloadExamLatex(made){if(!USER||!USER.is_admin){alert('Chỉ ADMIN xuất LaTeX.');return}made=String(made||'').trim();if(!made){alert('Không có mã đề.');return}let item=CATALOG.find(function(x){return x.MaDe===made||x.GroupKey===made});let name=item?examDisplayTitle(item):made;window.location=latexExportDownloadUrl({made:made,name:name})}
function exportRpScopeLatex(){if(!USER||!USER.is_admin){alert('Chỉ ADMIN xuất LaTeX.');return}if(typeof syncRpFromMainFilters==='function')syncRpFromMainFilters();syncRpKhoiFromLop();let mon=val('rpMon'),lop=val('rpLop');if(!mon||!lop){alert('Chọn Môn và Lớp ở «Lọc đề» trước.');return}let chuongs=getRpSelectedChuongs();let params={mon:mon,lop:lop,chuong:val('rpChuong'),baihoc:val('rpBaiHoc'),level:(val('fMucDo')||'').trim().toUpperCase(),sol_full_only:(document.getElementById('fSolFullOnly')&&document.getElementById('fSolFullOnly').checked)?1:0,name:[mon,'Lop'+lop,val('rpChuong'),val('rpBaiHoc')].filter(Boolean).join('_')};if(chuongs.length)params.chuongs=chuongs.join(',');window.location=latexExportDownloadUrl(params)}
function syncRpExportLatexBtn(){let b=document.getElementById('btnRpExportLatex');if(b)b.classList.toggle('hide',!(USER&&USER.is_admin))}
let ID_LOOKUP_MATCHES=[];
function setVal(id,v){let el=document.getElementById(id);if(el)el.value=v==null?'':String(v)}
function findQuestionIndexById(id){let u=String(id||'').trim().toUpperCase();if(!u)return -1;for(let i=0;i<QUESTIONS.length;i++){let qid=String(QUESTIONS[i].ID||'').trim().toUpperCase();if(qid===u)return i}return -1}
async function lookupQuestionById(){let raw=String(val('fIdLookup')||'').trim();if(!raw){alert('Nhập ID câu.');return}let box=document.getElementById('idLookupResult');if(box)box.innerHTML='<span class="muted">Đang tìm…</span>';try{let j=await api('/api/question/lookup?id='+encodeURIComponent(raw));if(j.loading){if(box)box.innerHTML='<span class="muted">'+esc(j.message||j.error||'Đang nạp Sheet…')+'</span>';setTimeout(lookupQuestionById,2500);return}renderIdLookupResult(j);if(j.from_sheet&&j.message){let note=document.createElement('div');note.className='muted';note.style.cssText='margin-top:6px;font-size:12px;color:#1d4ed8';note.textContent=j.message;if(box)box.appendChild(note)}}catch(e){if(box)box.innerHTML='<span style="color:#991b1b">'+esc(e.message)+'</span>'}}
function renderIdLookupResult(j){let box=document.getElementById('idLookupResult');if(!box)return;let matches=j.matches||[];ID_LOOKUP_MATCHES=matches;if(!matches.length){let hint=j.hint?('<br><span class="muted" style="font-size:12px">'+esc(j.hint)+'</span>'):'';let syncHint=(USER&&USER.is_admin)?'<br><span class="muted" style="font-size:12px">Nếu vừa thêm trên Sheet: bấm <b>Đồng bộ</b> rồi tìm lại.</span>':'';box.innerHTML='<span class="muted">Không tìm thấy ID «'+esc(j.id||val('fIdLookup')||'')+'».</span>'+hint+syncHint;return}let admin=!!USER.is_admin;box.innerHTML=matches.map((m,i)=>{let openBtn=`<button class="btn" type="button" onclick="openQuestionByIdMatch(${i},false)">🚀 Mở đề</button>`;let editBtn=admin?`<button class="btn2" type="button" onclick="openQuestionByIdMatch(${i},true)">✏️ Mở & sửa</button>`:'';let copyBtn=m.ID?`<button class="btn2" type="button" onclick="copyIdFromLookup('${escAttr(m.ID)}')">📋 Chép ID</button>`:'';return `<div class="idLookupCard"><h4>ID: ${esc(m.ID)} · Câu ${m.question_no||'?'} · ${esc(m.MaDe)}</h4><div class="idLookupMeta"><span class="tag">${esc(m.Mon)}</span> Lớp ${esc(m.Lop)} · ${esc(m.Chuong||'')} · ${esc(m.BaiHoc||'')}</div><div class="idLookupMeta">${esc(m.Dang||'')} · ${esc(m.MucDo||'')} · ${esc(m.QuyenTruyCap||'VIP')}</div><div class="idLookupPreview">${esc(m.preview||'')}</div><div class="row" style="margin-top:8px;flex-wrap:wrap;gap:6px">${openBtn}${editBtn}${copyBtn}</div></div>`}).join('')}
async function copyIdFromLookup(id){let ok=await copyTextToClipboard(id);alert(ok?'✅ Đã chép ID: '+id:'Không chép được.')}
async function openQuestionByIdMatch(idx,doEdit){let m=ID_LOOKUP_MATCHES[idx];if(!m||!m.MaDe){alert('Không có mã đề.');return}if(USER.is_trial&&(m.QuyenTruyCap||'VIP')!=='FREE'){alert('Tài khoản dùng thử chỉ mở đề FREE.');return}await startQuiz(m.MaDe,false,false,'','');let qIdx=findQuestionIndexById(m.ID);if(qIdx<0)qIdx=Math.max(0,parseInt(m.index_in_de,10)||0);saveCurrent();CUR=qIdx;renderQuestion();if(doEdit&&USER.is_admin)openEdit()}
async function copyQuestionId(){let q=QUESTIONS[CUR];let id=String(q&&q.ID||'').trim();if(!id){alert('Câu này chưa có ID.');return}let ok=await copyTextToClipboard(id);alert(ok?'✅ Đã chép ID: '+id:'Không chép được. Hãy chọn và chép thủ công.')}
function jumpToIdInQuiz(){let raw=String(val('quizIdJump')||'').trim();if(!raw){alert('Nhập ID câu.');return}let idx=findQuestionIndexById(raw);if(idx<0){alert('Không thấy ID «'+raw+'» trong đề này.');return}saveCurrent();CUR=idx;renderQuestion();if(USER.is_admin)openEdit()}
function toggleHomeFilterCollapse(force){let panel=document.getElementById('homePracticeSetupPanel');if(!panel)return;let collapsed=force==null?!panel.classList.contains('filterCollapsed'):!!force;panel.classList.toggle('filterCollapsed',collapsed);let btn=document.getElementById('homeFilterToggleBtn');if(btn){btn.textContent=collapsed?'▼ Mở rộng':'▲ Thu gọn';btn.setAttribute('aria-expanded',collapsed?'false':'true')}try{localStorage.setItem('LDVL_HOME_FILTER_COLLAPSED',collapsed?'1':'0')}catch(e){}}
document.addEventListener('DOMContentLoaded',function(){try{if(localStorage.getItem('LDVL_HOME_FILTER_COLLAPSED')==='1')toggleHomeFilterCollapse(true)}catch(e){}});
const LDVL_COLLAPSE_DEFAULTS={idLookupPanel:true,kwSearchPanel:true,catalogScopeBox:false,catalogBody:false,chuongBaiBody:false,advFilterBody:true};
function collapseStorageKey(id){return 'LDVL_COLLAPSE_'+id}
function isBlockCollapsed(id){try{let v=localStorage.getItem(collapseStorageKey(id));if(v==='1')return true;if(v==='0')return false}catch(e){}return !!LDVL_COLLAPSE_DEFAULTS[id]}
function toggleCollapseBlock(id,force){let body=document.getElementById(id);if(!body)return;let collapsed=force==null?!body.classList.contains('collapsedBlock'):!!force;body.classList.toggle('collapsedBlock',collapsed);let btn=document.querySelector('[data-collapse-btn="'+id+'"]');if(btn){btn.textContent=collapsed?'▶':'▼';btn.setAttribute('aria-expanded',collapsed?'false':'true');let lbl=collapsed?'Mở rộng':'Thu gọn';btn.setAttribute('aria-label',lbl);btn.setAttribute('title',lbl);let head=btn.closest('.homeSectionHead');if(head)head.classList.toggle('groupCollapsed',collapsed)}try{localStorage.setItem(collapseStorageKey(id),collapsed?'1':'0')}catch(e){}if(typeof syncFilterGroupSummaries==='function')syncFilterGroupSummaries()}
function filterFieldLabel(id){let el=document.getElementById(id);if(!el)return '';if(el.tagName==='SELECT'){let opt=el.options[el.selectedIndex];return opt?String(opt.textContent||opt.value||'').trim():''}return String(el.value||'').trim()}
function syncFilterGroupSummaries(){
  let cbParts=[filterFieldLabel('fChuong'),filterFieldLabel('fBaiHoc')].filter(Boolean);
  let cbSummary=document.getElementById('chuongBaiSummary');
  if(cbSummary)cbSummary.textContent=cbParts.length?cbParts.join(' · '):'Tất cả';
  let advParts=[];
  let dbt=filterFieldLabel('fDangBaiTap');if(dbt)advParts.push(dbt);
  let mucdo=filterFieldLabel('fMucDo');if(mucdo)advParts.push(mucdo);
  let dang=filterFieldLabel('fDang');if(dang)advParts.push(dang);
  let solChk=document.getElementById('fSolFullOnly');if(solChk&&solChk.checked)advParts.push('Có lời giải');
  let bode=filterFieldLabel('fBoDe');if(bode)advParts.push(bode);
  let kw=filterFieldLabel('fSearch');if(kw)advParts.push('"'+kw+'"');
  let advSummary=document.getElementById('advFilterSummary');
  if(advSummary)advSummary.textContent=advParts.length?advParts.join(' · '):'Chưa áp dụng';
}
function clearHomeFilters(){setVal('fChuong','');setVal('fBaiHoc','');setVal('fBoDe','');setVal('fDangBaiTap','');setVal('fMucDo','');setVal('fDang','');setVal('fSearch','');let chk=document.getElementById('fSolFullOnly');if(chk)chk.checked=false;refreshFilterOptions();renderCatalog();syncFilterGroupSummaries()}
function initCollapseBlocks(){Object.keys(LDVL_COLLAPSE_DEFAULTS).forEach(function(id){toggleCollapseBlock(id,isBlockCollapsed(id))});try{syncAiKeyCompactPanel()}catch(e){}try{syncFilterGroupSummaries()}catch(e){}try{ldvlToolsTabSync()}catch(e){}}
document.addEventListener('DOMContentLoaded',initCollapseBlocks);

// [PANEL-COLLAPSE-V1] Các khối ADMIN dài vốn không có nút thu gọn — bọc thân khối lại và gắn nút ▶/▼.
// Làm bằng JS để khỏi phải sửa các chuỗi HTML rất dài; mặc định đóng cho đỡ chiếm màn hình.
const LDVL_AUTOCOLLAPSE_PANELS=[
  {id:'adminComposePanel',hint:'Ghép đề theo ma trận'},
  {id:'adminAiGeneratePanel',hint:'Sinh câu bằng AI'}
];
function ldvlAutoCollapseOne(cfg){
  let p=document.getElementById(cfg.id);
  if(!p||p.getAttribute('data-autocollapse')==='1')return;
  let title=p.querySelector(':scope > b');
  if(!title)return;
  p.setAttribute('data-autocollapse','1');
  let bodyId=cfg.id+'Body';
  let body=document.createElement('div');
  body.id=bodyId;body.className='collapsibleBody';
  // Dồn mọi thứ sau tiêu đề vào thân khối để đóng/mở một lần.
  let n=title.nextSibling;
  while(n){let nx=n.nextSibling;body.appendChild(n);n=nx}
  let head=document.createElement('div');
  head.className='adminPanelHead';
  p.insertBefore(head,null);
  head.appendChild(title);
  if(cfg.hint){let s=document.createElement('span');s.className='adminPanelHint';s.textContent=cfg.hint;head.appendChild(s)}
  let btn=document.createElement('button');
  btn.type='button';btn.className='btn2 collapseToggleBtn';
  btn.setAttribute('data-collapse-btn',bodyId);
  head.appendChild(btn);
  p.appendChild(body);
  head.addEventListener('click',function(ev){
    if(ev.target.closest('a,input,select,textarea'))return;
    toggleCollapseBlock(bodyId);
  });
  if(typeof LDVL_COLLAPSE_DEFAULTS==='object')LDVL_COLLAPSE_DEFAULTS[bodyId]=true;
  toggleCollapseBlock(bodyId,typeof isBlockCollapsed==='function'?isBlockCollapsed(bodyId):true);
}
function ldvlAutoCollapseInit(){LDVL_AUTOCOLLAPSE_PANELS.forEach(function(c){try{ldvlAutoCollapseOne(c)}catch(e){}})}
document.addEventListener('DOMContentLoaded',ldvlAutoCollapseInit);

// [MODAL-DRAG-V1] Kéo tiêu đề để di chuyển bảng phụ, kéo góc dưới-phải để co giãn.
// Chỉ bật trên máy tính (>768px); điện thoại giữ nguyên bảng căn giữa để không vướng thao tác chạm.
const LDVL_MODAL_POS_KEY='LDVL_MODAL_POS_V1';
function ldvlModalPosStore(){try{return JSON.parse(localStorage.getItem(LDVL_MODAL_POS_KEY)||'{}')||{}}catch(e){return {}}}
function ldvlModalPosSave(id,pos){if(!id)return;try{let all=ldvlModalPosStore();all[id]=pos;localStorage.setItem(LDVL_MODAL_POS_KEY,JSON.stringify(all))}catch(e){}}
function ldvlModalDesktop(){return window.innerWidth>768}
function ldvlModalClamp(box,left,top){
  let w=box.offsetWidth||360,h=box.offsetHeight||200;
  let maxL=Math.max(0,window.innerWidth-Math.min(w,window.innerWidth)),maxT=Math.max(0,window.innerHeight-56);
  return {left:Math.min(Math.max(0,left),maxL),top:Math.min(Math.max(0,top),maxT)};
}
function ldvlModalApplyPos(box,left,top){
  let p=ldvlModalClamp(box,left,top);
  box.classList.add('modalDragged');
  box.style.left=p.left+'px';box.style.top=p.top+'px';
  box.style.right='auto';box.style.bottom='auto';
  return p;
}
function ldvlModalRestore(box){
  if(!box||!ldvlModalDesktop())return;
  let id=box.getAttribute('data-modal-id');if(!id)return;
  let pos=ldvlModalPosStore()[id];if(!pos)return;
  if(pos.w)box.style.width=pos.w+'px';
  if(pos.h)box.style.height=pos.h+'px';
  if(typeof pos.left==='number'&&typeof pos.top==='number')ldvlModalApplyPos(box,pos.left,pos.top);
}
function ldvlModalResetPos(box){
  if(!box)return;
  box.classList.remove('modalDragged');
  box.style.left='';box.style.top='';box.style.width='';box.style.height='';
  let id=box.getAttribute('data-modal-id');
  if(id)ldvlModalPosSave(id,{});
}
function ldvlModalStartDrag(ev,box){
  if(!ldvlModalDesktop())return;
  if(ev.button!=null&&ev.button!==0)return;
  let r=box.getBoundingClientRect();
  let dx=ev.clientX-r.left,dy=ev.clientY-r.top;
  // Chốt kích thước hiện tại trước khi bỏ căn giữa, tránh bảng nhảy size khi bắt đầu kéo.
  box.style.width=r.width+'px';
  ldvlModalApplyPos(box,r.left,r.top);
  let last={left:r.left,top:r.top};
  function move(e){e.preventDefault();last=ldvlModalApplyPos(box,e.clientX-dx,e.clientY-dy)}
  function up(){
    document.removeEventListener('pointermove',move);
    document.removeEventListener('pointerup',up);
    document.body.style.userSelect='';
    let id=box.getAttribute('data-modal-id');
    if(id)ldvlModalPosSave(id,{left:last.left,top:last.top,w:box.offsetWidth,h:box.offsetHeight});
  }
  document.body.style.userSelect='none';
  document.addEventListener('pointermove',move);
  document.addEventListener('pointerup',up);
  ev.preventDefault();
}
function ldvlModalInitDrag(root){
  let scope=root&&root.querySelectorAll?root:document;
  scope.querySelectorAll('.modalBox').forEach(function(box){
    if(box.getAttribute('data-drag-ready')==='1')return;
    let h=box.querySelector(':scope > h3');
    if(!h)return;
    let id=(box.parentElement&&box.parentElement.id)||h.textContent.trim().slice(0,40);
    box.setAttribute('data-modal-id',id);
    box.setAttribute('data-drag-ready','1');
    box.classList.add('modalDraggable');
    h.setAttribute('title','Kéo để di chuyển · nhấp đúp để đưa về giữa');
    h.addEventListener('pointerdown',function(ev){ldvlModalStartDrag(ev,box)});
    h.addEventListener('dblclick',function(){ldvlModalResetPos(box)});
    ldvlModalRestore(box);
  });
}
document.addEventListener('DOMContentLoaded',function(){ldvlModalInitDrag(document)});
window.addEventListener('resize',function(){
  if(ldvlModalDesktop())return;
  document.querySelectorAll('.modalBox.modalDragged').forEach(function(b){
    b.classList.remove('modalDragged');b.style.left='';b.style.top='';b.style.width='';b.style.height='';
  });
});

// [TOOLS-TABS-V1] Ba nhóm Tìm ID / Từ khóa / Key AI dùng chung 1 hàng tab — mỗi lúc chỉ mở 1 nhóm.
const LDVL_TOOLS_TABS=['idLookupPanel','kwSearchPanel','aiKeyPanel'];
const LDVL_TOOLS_TAB_NAMES={idLookupPanel:'Tìm theo ID câu',kwSearchPanel:'Lọc câu theo từ khóa',aiKeyPanel:'Key AI'};
function ldvlToolsTabIsOpen(id){let el=document.getElementById(id);return !!el&&!el.classList.contains('collapsedBlock')}
function ldvlToolsTabSet(id,open){
  if(id==='aiKeyPanel'){if(typeof setAiKeyPanelOpen==='function')setAiKeyPanelOpen(!!open);return}
  if(typeof toggleCollapseBlock==='function')toggleCollapseBlock(id,!open);
}
function ldvlToolsTab(id){
  let willOpen=!ldvlToolsTabIsOpen(id);
  LDVL_TOOLS_TABS.forEach(function(x){ldvlToolsTabSet(x,x===id?willOpen:false)});
  ldvlToolsTabSync();
  if(willOpen){
    let panel=document.getElementById(id);
    if(panel){
      let inp=panel.querySelector('input,textarea');
      if(inp&&window.innerWidth>768){try{inp.focus()}catch(e){}}
    }
  }
}
function ldvlToolsTabSync(){
  let opened='';
  LDVL_TOOLS_TABS.forEach(function(x){
    let btn=document.getElementById('toolsTabBtn-'+x),panel=document.getElementById(x);
    if(!btn)return;
    // Nhóm nào bị ẩn theo quyền (vd Key AI với tài khoản thường) thì giấu luôn tab.
    let hidden=!panel||panel.classList.contains('hide');
    btn.classList.toggle('hide',hidden);
    if(hidden)return;
    let on=ldvlToolsTabIsOpen(x);
    btn.classList.toggle('active',on);
    btn.setAttribute('aria-selected',on?'true':'false');
    if(on)opened=x;
  });
  let st=document.getElementById('toolsTabStatus');
  if(st)st.textContent=opened?('Đang mở: '+LDVL_TOOLS_TAB_NAMES[opened]):'Bấm một nhóm để mở';
}
let KEYWORD_SEARCH_MATCHES=[];
function collectKeywordSearchFilters(){return{mon:val('fMon'),lop:val('fLop'),chuong:val('fChuong'),baihoc:val('fBaiHoc'),bode:val('fBoDe'),dang:val('fDang'),dangbaitap:val('fDangBaiTap'),level:(val('fMucDo')||'').trim().toUpperCase(),sol_full_only:(document.getElementById('fSolFullOnly')&&document.getElementById('fSolFullOnly').checked)?1:0}}
async function searchQuestionsByKeyword(){let raw=String(val('fKeywordSearch')||'').trim();let cbox=document.getElementById('kwSearchCount');let box=document.getElementById('kwSearchResult');if(!raw){if(cbox)cbox.textContent='';if(box)box.innerHTML='';KEYWORD_SEARCH_MATCHES=[];return}if(box)box.innerHTML='<span class="muted">Đang tìm…</span>';if(cbox)cbox.textContent='';try{let payload=Object.assign({keyword:raw},collectKeywordSearchFilters());let j=await api('/api/question/keyword-search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(j.loading){if(box)box.innerHTML='<span class="muted">'+esc(j.message||j.error||'Đang nạp Sheet…')+'</span>';setTimeout(searchQuestionsByKeyword,2500);return}renderKeywordSearchResult(j)}catch(e){if(box)box.innerHTML='<span style="color:#991b1b">'+esc(e.message)+'</span>'}}
function renderKeywordSearchResult(j){let box=document.getElementById('kwSearchResult');let cbox=document.getElementById('kwSearchCount');if(!box)return;let matches=j.matches||[];KEYWORD_SEARCH_MATCHES=matches;let count=parseInt(j.count,10)||0;if(cbox)cbox.textContent='Tìm thấy '+count+' câu phù hợp.'+(count>matches.length?(' (hiển thị '+matches.length+' câu đầu)'):'');if(!count){box.innerHTML='<span class="muted">Không tìm thấy câu nào khớp từ khóa «'+esc(j.keyword||val('fKeywordSearch')||'')+'».</span>';return}let admin=!!USER.is_admin;box.innerHTML=matches.map((m,i)=>{let openBtn=`<button class="btn" type="button" onclick="openQuestionByKeywordMatch(${i},false)">🚀 Mở đề</button>`;let editBtn=admin?`<button class="btn2" type="button" onclick="openQuestionByKeywordMatch(${i},true)">✏️ Mở & sửa</button>`:'';let copyBtn=m.ID?`<button class="btn2" type="button" onclick="copyIdFromLookup('${escAttr(m.ID)}')">📋 Chép ID</button>`:'';return `<div class="idLookupCard"><h4>ID: ${esc(m.ID)} · Câu ${m.question_no||'?'} · ${esc(m.MaDe)}</h4><div class="idLookupMeta"><span class="tag">${esc(m.Mon)}</span> Lớp ${esc(m.Lop)} · ${esc(m.Chuong||'')} · ${esc(m.BaiHoc||'')}</div><div class="idLookupMeta">${esc(m.Dang||'')} · ${esc(m.MucDo||'')} · ${esc(m.QuyenTruyCap||'VIP')}</div><div class="idLookupPreview">${esc(m.preview||'')}</div><div class="row" style="margin-top:8px;flex-wrap:wrap;gap:6px">${openBtn}${editBtn}${copyBtn}</div></div>`}).join('')}
async function openQuestionByKeywordMatch(idx,doEdit){let m=KEYWORD_SEARCH_MATCHES[idx];if(!m||!m.MaDe){alert('Không có mã đề.');return}if(USER.is_trial&&(m.QuyenTruyCap||'VIP')!=='FREE'){alert('Tài khoản dùng thử chỉ mở đề FREE.');return}await startQuiz(m.MaDe,false,false,'','');let qIdx=findQuestionIndexById(m.ID);if(qIdx<0)qIdx=Math.max(0,parseInt(m.index_in_de,10)||0);saveCurrent();CUR=qIdx;renderQuestion();if(doEdit&&USER.is_admin)openEdit()}
function clearKeywordSearch(){setVal('fKeywordSearch','');KEYWORD_SEARCH_MATCHES=[];let box=document.getElementById('kwSearchResult');if(box)box.innerHTML='';let cbox=document.getElementById('kwSearchCount');if(cbox)cbox.textContent=''}
function handleQidDeepLink(){let p=new URLSearchParams(location.search);let qid=(p.get('qid')||p.get('question_id')||'').trim();if(!qid)return;setVal('fIdLookup',qid);setTimeout(()=>lookupQuestionById(),400);p.delete('qid');p.delete('question_id');let q=p.toString();history.replaceState(null,'',location.pathname+(q?'?'+q:''))}
function clearShareTarget(){document.querySelectorAll('.card.shareTarget,.bookLessonCard.shareTarget').forEach(el=>el.classList.remove('shareTarget'))}
function markShareTarget(made){clearShareTarget();let el=document.getElementById('shareCard_'+made);if(el){el.classList.add('shareTarget');setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'nearest'}),120)}}
function handleShareDeepLink(){let sp=getShareParams();if(sp.exam){setTimeout(()=>startExamByCode(sp.exam),280);return}if(!sp.de)return;let item=CATALOG.find(x=>x.MaDe===sp.de);if(!item){alert('Không tìm thấy đề trong link. Có thể đề đã đổi hoặc cần Đồng bộ Sheet.');return}if(item.Mon)setSel('fMon',item.Mon);refreshFilterOptions();if(item.Lop)setSel('fLop',item.Lop);refreshFilterOptions();if(item.Chuong)setSel('fChuong',item.Chuong);refreshFilterOptions();if(item.BaiHoc)setSel('fBaiHoc',item.BaiHoc);refreshFilterOptions();if(item.BoDe)setSel('fBoDe',item.BoDe);if(sp.level)setSel('fMucDo',sp.level);if(sp.dang)setSel('fDang',sp.dang);renderCatalog();let lv=sp.level||val('fMucDo');let dg=sp.dang||val('fDang');if(sp.start){if(USER.is_trial&&(item.QuyenTruyCap||'FREE')!=='FREE'){markShareTarget(sp.de);alert('Tài khoản dùng thử chỉ mở đề FREE.');return}setTimeout(()=>startQuiz(sp.de,sp.sq,sp.sa,lv,dg),280)}else if(sp.open){markShareTarget(sp.de);setTimeout(()=>openStartModal(sp.de),280)}}
async function startExamByCode(code){
  code=String(code||'').trim().toUpperCase();if(!code)return;
  try{
    let meta=await api('/api/exam-assign/'+encodeURIComponent(code));
    let made=meta.made||'';
    if(made){let item=CATALOG.find(x=>x.MaDe===made);if(item){if(item.Mon)setSel('fMon',item.Mon);refreshFilterOptions();if(item.Lop)setSel('fLop',item.Lop);refreshFilterOptions();if(item.Chuong)setSel('fChuong',item.Chuong);refreshFilterOptions();if(item.BaiHoc)setSel('fBaiHoc',item.BaiHoc);refreshFilterOptions()}}
    let j=await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({exam_code:code,exam_mode:1})});
    enterQuizSession(j,j.made||made||'',meta.level||'','','',false,meta.dangbaitap||'');
    alert('🧪 Đã vào bài kiểm tra'+(meta.title?(' «'+meta.title+'»'):'')+'.\nKhông xem đáp án/lời giải đến khi nộp bài.');
  }catch(e){alert('Không mở được bài kiểm tra: '+(e.message||e))}
}
function esc(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])).replace(/\n/g,'<br>')}
function escapeHtmlInMathChunk(chunk){return String(chunk||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function findLatexMathSpan(s,from){let n=String(s||'').length,depth=0;for(let i=from;i<n;i++){let c=s[i];if(c==='\\'){if(i+1<n&&(s[i+1]==='{'||s[i+1]==='}')){i+=2;continue}i++;continue}if(c==='{')depth++;else if(c==='}'&&depth>0)depth--;else if(c==='$'&&depth===0){if(i+1<n&&s[i+1]==='$'){let close=s.indexOf('$$',i+2);if(close<0)return{start:i,end:-1};return{start:i,end:close+1}}let close=s.indexOf('$',i+1);if(close<0)return{start:i,end:-1};return{start:i,end:close}}}return null}
function escHtmlKeepMath(s){let out='',i=0,n=String(s||'').length;while(i<n){let span=findLatexMathSpan(s,i);if(!span){out+=esc(s.slice(i));break}if(span.end<0){out+=esc(s.slice(i));break}out+=esc(s.slice(i,span.start));out+=escapeHtmlInMathChunk(s.slice(span.start,span.end+1));i=span.end+1}return out}
function stripLatexCenterEnv(s){s=String(s||'');let re=/\\begin\s*\{\s*center\s*\}([\s\S]*?)\\end\s*\{\s*center\s*\}/gi;for(let i=0;i<8;i++){let n=s.replace(re,'$1');if(n===s)break;s=n;re.lastIndex=0}return s}
function stripLatexListMarkup(s){s=String(s||'');s=s.replace(/\\begin\s*\{\s*enumerate\s*\}/gi,'');s=s.replace(/\\end\s*\{\s*enumerate\s*\}/gi,'');s=s.replace(/\\begin\s*\{\s*itemize\s*\}/gi,'');s=s.replace(/\\end\s*\{\s*itemize\s*\}/gi,'');s=s.replace(/\\begin\s*\{\s*itemchoice\s*\}/gi,'');s=s.replace(/\\end\s*\{\s*itemchoice\s*\}/gi,'');s=s.replace(/(?:^|\n)\s*•\s*ch\s+/gi,'\n• ');s=s.replace(/•\s*ch\s+/gi,'• ');s=s.replace(/\\item\s*/gi,'\n• ');s=s.replace(/\\item(?=[A-Za-zÀ-ỹĐđ])/gi,'\n• ');return s}
function mergeBrokenDfracSqrt(s){if(String(s||'').indexOf('$')<0)return String(s||'');let t=String(s||''),prev=null;while(prev!==t){prev=t;t=t.replace(/(\$[^$\n]*?-?)\\dfrac\{(\d+)\}\$\s*\$\(\\sqrt\{([^}]+)\}\)\$/g,function(_,pre,n,rt){return pre+'\\dfrac{'+n+'}{\\sqrt{'+rt+'}}$'})}return t.replace(/\$\(\s*\\/g,'$\\')}
function mergeUnitBetweenMath(s){let units='rad|deg|m|km|cm|mm|s|ms|kg|g|N|J|W|Pa|kPa|Hz|V|A';return String(s||'').replace(new RegExp('(\\\\$[^$\\n]+?\\\\$)\\\\s*('+units+')\\\\s*(\\\\$[^$\\n]*=[^$\\n]*\\\\$)','gi'),function(m,g1,u,g3){let a=g1.slice(1,-1).trim(),b=g3.slice(1,-1).trim();if(!b.startsWith('='))return m;return '$'+fixOneMathInner(a+'\\,\\mathrm{'+u+'}'+b)+'$'})}
function trimInlineMathSpaces(t){if(String(t||'').indexOf('$')<0)return String(t||'');return String(t||'').replace(/\$([^$\n]+?)\$/g,function(_,inner){return '$'+String(inner).trim()+'$'})}
function mergeAdjacentInlineMath(t){t=String(t||'');if(t.indexOf('$')<0)return t;let prev=null;while(prev!==t){prev=t;t=t.replace(/(\$[^$\n]+?\$)(\s+)(\$[^$\n]+?\$)/g,function(m,g1,gap,g3){if(/[A-Za-zÀ-ỹĐđ]/.test(gap))return m;let a=g1.slice(1,-1).trim(),b=g3.slice(1,-1).trim();return '$'+a+(gap.trim()?' ':'')+b+'$'})}return t}
function fixPlainTextGaps(s){return String(s||'').replace(/(\d)([Nn]ên|[Đđ]iểm)/g,'$1 $2').replace(/(\))([A-Za-zÀ-ỹĐđ])/g,'$1 $2')}
function latexPlainLinebreaks(s){return String(s||'').replace(/\\{2,}\s*/g,'\n')}
function applyPlainLinebreaksOutsideMath(s){return applyFmtOutsideMath(s,latexPlainLinebreaks)}
function fixOneMathInner(inner){if(!inner)return inner;inner=inner.replace(/\)\s*\((\d[\d;\s,.\-]*)\)/g,')$ $( $1)$');inner=inner.replace(/\$\(([^)]+)\)(thuộc|mặt|phẳng|nên|điểm)/gi,'$( $1)$ $2');inner=inner.replace(/\(([^)]+)\)(thỏa|mãn|phương|trình|nên|điểm|thuộc|mặt|phẳng|khẳng|tọa|độ)/gi,'($1)$ $2');inner=inner.replace(/(=[\d.\-+]+)\s*(nên|điểm|thuộc|mặt|phẳng|khẳng|tọa)/gi,'$1$ $2');inner=inner.replace(/\)(thỏa|mãn|nên|điểm|thuộc|mặt|phẳng)/gi,') $1');inner=inner.replace(/(\d)([A-Za-zÀ-ỹĐđ][a-zà-ỹà-ỹ]{2,})/g,'$1 $2');inner=inner.replace(/(\))([A-Za-zÀ-ỹĐđ][a-zà-ỹà-ỹ]{2,})/g,'$1 $2');inner=inner.replace(/\(\((\\?[a-zA-Z]+)\)\)/g,'$1');inner=inner.replace(/(\\(?:dfrac|tfrac|frac)\{[^{}]*\})\{(\d+)\^\{([^{}]+)\}\s*=/g,function(_,a,n,d){return a+'{'+n+'^{'+d+'}} ='});return inner}
function latexDollarCount(s){s=String(s||'');let n=0;for(let i=0;i<s.length;i++){if(s[i]==='$'&&s[i+1]==='$'){i++;continue}if(s[i]==='$')n++}return n}
function latexStructureOk(s){s=String(s||'');if(latexDollarCount(s)%2)return false;let plain=s.replace(/\$\$[^$]*\$\$/g,'').replace(/\$[^$]*\$/g,'');return !/\\[a-zA-Z]/.test(plain)}
function fixSurplusDollars(s){s=String(s||'');if(s.indexOf('$')<0)return s;s=mergeAdjacentInlineMath(s);s=trimInlineMathSpaces(s);s=s.replace(/\${3,}/g,'$$');s=s.replace(/\$\$([^$\n]{1,160}?)\$\$/g,'$$$1$');s=s.replace(/\$\$([^$\n]+?)\$(?!\$)/g,'$$$1$');s=s.replace(/\$([^$\n]+?)\$\$(?!\$)/g,'$$$1$');s=s.replace(/(\$[^$\n]+?\$)\$+/g,'$1');s=s.replace(/\$\s+\$(?=[^$\n])/g,'$');s=s.replace(/\$\s+\$(?=\s|$)/g,' ');s=s.replace(/\$\s*\$/g,' ');s=s.replace(/(\$[^$\n]+?\$)\.(\$)(?=\s|$|[A-Za-zÀ-ỹĐđ])/g,'$1.');if(s.endsWith('$')&&latexDollarCount(s)%2===1)s=s.slice(0,-1);return s}
function fixMergedInlineMath(t){t=String(t||'');if(t.indexOf('$')<0)return fixPlainTextGaps(t);let out='',i=0,n=t.length;while(i<n){if(t[i]!=='$'){let d1=t.indexOf('$',i);if(d1<0){out+=fixPlainTextGaps(t.slice(i));break}out+=fixPlainTextGaps(t.slice(i,d1));i=d1;continue}if(i+1<n&&t[i+1]==='$'){let end=t.indexOf('$$',i+2);if(end>=0){out+=t.slice(i,end+2);i=end+2;continue}}let d2=t.indexOf('$',i+1);if(d2<0){let rest=t.slice(i+1);if(String(rest).trim()&&(rest.indexOf('\\')>=0||rest.indexOf('{')>=0))out+='$'+fixOneMathInner(rest)+'$';else out+=fixPlainTextGaps(rest);break}let inner=t.slice(i+1,d2);if(!String(inner).trim()){i=d2+1;continue}while(d2+1<n&&t[d2+1]==='$'&&(d2+2>=n||t[d2+2]!=='$'))d2++;out+='$'+fixOneMathInner(t.slice(i+1,d2))+'$';i=d2+1}return out}
function convertHevaInner(inner){inner=String(inner||'').trim();if(!inner)return '\\left\\{\\right.';inner=inner.replace(/\\\\/g,'\n');inner=inner.replace(/\s\\&/g,'\n');let parts=inner.split(/\n|\s+(?=\\?&[a-zA-Z0-9\\(_])/);let lines=parts.map(p=>p.replace(/^\&\s*/,'').trim()).filter(Boolean);if(!lines.length)lines=[inner.replace(/^\&\s*/,'')];let body=lines.map(line=>{if(line.indexOf('&')<0&&/[^=<>!]=[^=]/.test(line))return line.replace(/([^=<>!])=/,'$1 &=');return line}).join(' \\newline ');return '\\left\\{ \\begin{aligned} '+body+' \\end{aligned} \\right.'}
function fixHevaLatex(s){s=String(s||'');if(!/\\heva/i.test(s))return s;let out='',i=0;while(i<s.length){let tail=s.slice(i),m=tail.match(/\\heva/i);if(!m){out+=tail;break}let hit=i+m.index;out+=s.slice(i,hit);let brace=s.indexOf('{',hit+5);if(brace<0){out+=s.slice(hit);break}let got=readLatexBracedContent(s,brace);if(!got){out+=s.slice(hit,brace+1);i=brace+1;continue}out+=convertHevaInner(got.content);i=got.end+1}return out}
function sanitizeLatexMathInner(inner){inner=fixHevaLatex(String(inner||''));while(inner.indexOf('\\\\\\\\')>=0)inner=inner.replace(/\\\\\\\\/g,'\\\\');inner=inner.replace(/\\text\s*\{\s*(sin|cos|tan|cot|ln|log)\s*\}/gi,'\\$1');inner=inner.replace(/(^|[^\\A-Za-z])([0-9]+)\s*pi\b/gi,'$1$2\\pi');inner=inner.replace(/(^|[^\\A-Za-z])pi\b/gi,'$1\\pi');let lc=(inner.match(/\\left\b/g)||[]).length,rc=(inner.match(/\\right\b/g)||[]).length;if(lc!==rc){inner=inner.replace(/\\left\s*/g,'').replace(/\\right\s*/g,'')}return inner}
function spaceAroundInlineMathInProse(t){t=String(t||'');t=t.replace(/\$\s*•\s*\$/g,'•');if(t.indexOf('$')<0)return t;let out=[],i=0,n=t.length;while(i<n){if(t[i]!=='$'){let d=t.indexOf('$',i);if(d<0){out.push(t.slice(i));break}out.push(t.slice(i,d));i=d;continue}let d=t.indexOf('$',i+1);if(d<0){out.push(t.slice(i));break}let inner=t.slice(i+1,d).trim();let chunk='$'+inner+'$';if(out.length&&out[out.length-1]&&!/\s$/.test(out[out.length-1])&&!/[«(]$/.test(out[out.length-1]))out.push(' ');out.push(chunk);i=d+1;if(i<n&&!/\s/.test(t[i])&&!/[«»$,.;:!?)]/.test(t[i]))out.push(' ')}return out.join('')}function wrapVnContextNumbersInMath(t){return String(t||'').replace(/\b(tháng|thang|năm|nam|ngày|ngay)\s+(\d{1,4})\b/gi,function(_,w,n){return w+' $'+n+'$'})}function fixBareTrigLatex(s){s=String(s||'');s=s.replace(/\(sin\^2\)/gi,'\\sin^2');s=s.replace(/\(cos\^2\)/gi,'\\cos^2');s=s.replace(/\(tan\^2\)/gi,'\\tan^2');s=s.replace(/\(cot\^2\)/gi,'\\cot^2');s=s.replace(/\{\\?(cos|sin|tan|cot)\s*\^2\s*\}2\\alpha/gi,(m,c)=>'\\'+c.toLowerCase()+'^2\\alpha');s=s.replace(/\{\s*\\?(sin|cos|tan|cot)\s+\^?\s*2\s*\}/gi,(m,c)=>'\\'+c.toLowerCase()+'^2');s=s.replace(/\\(cos|sin|tan|cot)\^22\\alpha/gi,(m,c)=>'\\'+c.toLowerCase()+'^2\\alpha');return s}function hasVietnameseText(s){return /[À-ỹà-ỹăâêôơưđĂÂÊÔƠƯĐ]/.test(String(s||''))}function isLatexProseContent(s){s=String(s||'');if(hasVietnameseText(s))return true;if(/\\(?:begin|end|item)\b/i.test(s))return true;if(/(?:^|\n)\s*•\s+/.test(s))return true;return (s.match(/[A-Za-z]{2,}/g)||[]).length>=6&&s.indexOf(' ')>=0}function latexParenToDollar(s){s=String(s||'');if(!s||s.indexOf('\\(')<0&&s.indexOf('\\[')<0)return s;s=s.replace(/\\\((.+?)\\\)/g,function(_,x){return '$'+String(x).trim()+'$'});s=s.replace(/\\\[(.+?)\\\]/gs,function(_,x){x=String(x).trim();return x.indexOf('\n')>=0?'$$'+x+'$$':'$'+x+'$'});return s}function wrapBareLatexMath(s){s=String(s||'').trim();if(!s||s.indexOf('$')>=0)return s;if(isLatexProseContent(s))return s;if(!(/\\[a-zA-Z]|[\^_=]|\((?:sin|cos|tan|cot)/i.test(s)))return s;return '$'+fixBareTrigLatex(s)+'$'}function normalizeLatexDelimiters(s){s=String(s||'');s=applyPlainLinebreaksOutsideMath(s);s=fixHevaLatex(s);s=latexParenToDollar(s);if(/\\(?:begin\s*\{|\\item\b)/i.test(s))s=stripLatexListMarkup(s);s=wrapBareLatexMath(s);s=stripLatexListMarkup(s);s=mergeBrokenDfracSqrt(s);s=mergeUnitBetweenMath(s);s=mergeAdjacentInlineMath(s);s=trimInlineMathSpaces(s);s=fixSurplusDollars(s);let heavy=/\\(?:item|begin\s*\{enumerate|begin\s*\{itemize|begin\s*\{itemchoice|acute)|•\s*ch\s+|\$\{|\$\$[^$]|\$\s+\$(?=[^$\n])|(?:rad|deg|m|s)\s*\$[^$\n]*=/.test(s)||!latexStructureOk(s);if(heavy){s=s.replace(/\$\{\s*([^}$\n]+?)\s*\}\s*\$/g,'$( $1 )$');s=s.replace(/\$\{\s*([^}$\n]+?)\s*\}/g,'$( $1 )$');s=s.replace(/\{\s*\(\s*([^}]+?)\s*\)\s*\}/g,function(m,g1,off,full){if(off>0&&full[off-1]==='$')return m;if(off+m.length<full.length&&full[off+m.length]==='$')return m;return '$( '+g1+' )$'});s=s.replace(/\$\(\((\\?[a-zA-Z]+)\)\)\$\.?/g,'$$$1$.');s=s.replace(/\$\(\((\\?[a-zA-Z]+)\)\)(?!\$)/g,'$$$1$');s=mergeAdjacentInlineMath(s);s=trimInlineMathSpaces(s);s=fixMergedInlineMath(s);s=fixSurplusDollars(s);s=s.replace(/(\$[^$\n]+?\$)\$+/g,'$1');s=s.replace(/\$\s*\$/g,' ')}s=s.replace(/\$([^$]*)\$/g,function(_,inner){return '$'+sanitizeLatexMathInner(inner)+'$'});s=wrapVnContextNumbersInMath(s);s=spaceAroundInlineMathInProse(s);return trimInlineMathSpaces(s)}
function readLatexBracedContent(s,bracePos){if(bracePos<0||bracePos>=s.length||s[bracePos]!=='{')return null;let depth=0;for(let i=bracePos;i<s.length;i++){let c=s[i];if(c==='{')depth++;else if(c==='}'){depth--;if(depth===0)return{content:s.slice(bracePos+1,i),end:i}}}return null}
function normalizeLatexTextCmds(s){s=String(s||'');s=s.replace(/\\{2,}(textbf|textit|emph|underline)\s*\{/gi,'\\$1{');s=s.replace(/(^|[^\\$])(textbf|textit|emph|underline)\s*\{/gi,'$1\\$2{');return s}
function replaceLatexFmtInPlain(s){s=normalizeLatexTextCmds(s);let cmds=[{re:/\\textbf\s*\{/gi,o:'@@B@@',c:'@@/B@@'},{re:/\\textit\s*\{/gi,o:'@@I@@',c:'@@/I@@'},{re:/\\emph\s*\{/gi,o:'@@I@@',c:'@@/I@@'},{re:/\\underline\s*\{/gi,o:'@@U@@',c:'@@/U@@'}];let loop=true;while(loop){loop=false;for(let cmd of cmds){cmd.re.lastIndex=0;let m=cmd.re.exec(s);if(!m)continue;let idx=m.index,bracePos=idx+m[0].length-1,got=readLatexBracedContent(s,bracePos);if(!got)continue;let inner=replaceLatexFmtInPlain(got.content);s=s.slice(0,idx)+cmd.o+inner+cmd.c+s.slice(got.end+1);loop=true;break}}return s}
function applyFmtOutsideMath(s,fn){let out='',i=0,n=String(s||'').length;while(i<n){let span=findLatexMathSpan(s,i);if(!span){out+=fn(s.slice(i));break}if(span.end<0){out+=fn(s.slice(i));break}out+=fn(s.slice(i,span.start));out+=s.slice(span.start,span.end+1);i=span.end+1}return out}
function applyLatexTextFmtOutsideMath(s){return applyFmtOutsideMath(s,replaceLatexFmtInPlain)}
function applyMarkdownBoldOutsideMath(s){return applyFmtOutsideMath(s,x=>x.replace(/\*\*([^*\n]+)\*\*/g,'@@B@@$1@@/B@@'))}
function splitTabularRows(body){body=String(body||'').replace(/\r/g,'').trim();if(/\\\\/.test(body)){return body.replace(/\\\\\s*\n?/g,'@@ROW@@').split('@@ROW@@')}return body.split(/\n+/).filter(Boolean)}
let LATEX_TAB_HTML=[];
function convertLatexTabular(s){LATEX_TAB_HTML=[];return String(s||'').replace(/\\begin\s*\{tabular\*?\}\s*(\{[^}]*\})?\s*([\s\S]*?)\\end\s*\{tabular\*?\}/gi,function(_,colSpec,body){let spec=(colSpec||'').replace(/^\{|\}$/g,'');let aligns=[];for(let i=0;i<spec.length;i++){let c=spec[i];if(c==='c'||c==='l'||c==='r')aligns.push(c)}let html='<div class="latex-tabular-wrap"><table class="latex-tabular"><tbody>';let borderNext=false;for(let row of splitTabularRows(body)){row=row.trim();if(!row)continue;if(/^\\hline\s*$/i.test(row)){borderNext=true;continue}if(/^\\hline/i.test(row))row=row.replace(/^\\hline\s*/i,'');row=row.replace(/\\hline/g,'').trim();if(!row)continue;if(!row.includes('&'))continue;let cells=row.split('&').map(c=>c.trim());let trCls=borderNext?' class="hline-top"':'';borderNext=false;html+=`<tr${trCls}>`;for(let i=0;i<cells.length;i++){let al=aligns[i]||'c';let st=al==='r'?'text-align:right':(al==='l'?'text-align:left':'text-align:center');html+=`<td style="${st}">${cells[i]}</td>`}html+='</tr>'}html+='</tbody></table></div>';let id=LATEX_TAB_HTML.length;LATEX_TAB_HTML.push(html);return `@@LTXTAB${id}@@`})}
function restoreLatexTabular(s){return String(s||'').replace(/@@LTXTAB(\d+)@@/g,function(_,i){return LATEX_TAB_HTML[+i]||''})}
function normalizeDisplayBreaks(s){return String(s||'').replace(/\\r\\n/g,'\\n').replace(/\\n(?=\s*(?:[0-9A-ZÀ-ỸĐ]|[-•]))/g,'\n')}
function finalizeRichTokens(s){s=s.replace(/@@OL@@/g,'<ol class="latex-list">').replace(/@@\/OL@@/g,'</ol>').replace(/@@UL@@/g,'<ul class="latex-list">').replace(/@@\/UL@@/g,'</ul>').replace(/@@LI@@/g,'<li>').replace(/@@\/LI@@/g,'</li>').replace(/@@B@@/g,'<b>').replace(/@@\/B@@/g,'</b>').replace(/@@I@@/g,'<i>').replace(/@@\/I@@/g,'</i>').replace(/@@U@@/g,'<u>').replace(/@@\/U@@/g,'</u>');return applyFmtOutsideMath(s,function(x){return x.replace(/\n{2,}/g,'<br><br>').replace(/\n/g,'<br>')})}
function renderRichText(s){s=normalizeDisplayBreaks(String(s||'').trim());s=s.replace(/\?\?\s*/g,'');s=stripLatexCenterEnv(s);s=convertLatexTabular(s);s=stripLatexListMarkup(s);s=normalizeLatexDelimiters(s);s=s.replace(/\\begin\{enumerate\}([\s\S]*?)\\end\{enumerate\}/gi,function(_,b){let items=b.split(/\\item\s*/i).map(x=>x.trim()).filter(Boolean);return '@@OL@@'+items.map(it=>'@@LI@@'+it+'@@/LI@@').join('')+'@@/OL@@'});s=s.replace(/\\begin\{itemize\}([\s\S]*?)\\end\{itemize\}/gi,function(_,b){let items=b.split(/\\item\s*/i).map(x=>x.trim()).filter(Boolean);return '@@UL@@'+items.map(it=>'@@LI@@'+it+'@@/LI@@').join('')+'@@/UL@@'});s=s.replace(/\\item\s*/gi,'<br>• ');s=s.replace(/\\item(?=[A-Za-zÀ-ỹĐđ])/gi,'<br>• ');s=applyLatexTextFmtOutsideMath(s);s=applyMarkdownBoldOutsideMath(s);s=escHtmlKeepMath(s);s=restoreLatexTabular(s);return finalizeRichTokens(s)}
function oneLineText(s){return String(s||'').replace(/[\r\n\u00a0]+/g,' ').replace(/\s+/g,' ').trim()}
function escAttr(s){return String(s||'').replace(/[&<>"'\n\r]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','\n':' ','\r':' '}[m]))}
function shortText(s,n=90){s=oneLineText(s);return s.length>n?s.slice(0,n-1)+'…':s}
function normText(s){return oneLineText(String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'d'))}
function normDangClient(s){let t=String(s||'').replace(/[/\\]+/g,' ');let k=normText(t).replace(/[\/\\-]/g,' ');let k2=k.replace(/\s+/g,'');if(/dung\s*sai|dungsai|d\/s|true\s*false|truefalse/.test(k)||k2.includes('ds')||/\b(ds|tf)\b/.test(k))return 'Đúng sai';if(/tra\s*loi\s*ngan|short|tln|shortans/.test(k))return 'Trả lời ngắn';if(/tu\s*luan|essay/.test(k)||k==='tl')return 'Tự luận';if(/trac\s*nghiem|tracnghiem|mcq|multiple\s*choice/.test(k)||k==='tn'||k==='tn4')return 'Trắc nghiệm';return 'Trắc nghiệm'}
function tfTokenClient(p){let t=normText(p);if(!String(p||'').trim())return '';if(String(p).trim()==='Đ'||String(p).trim()==='D'||t==='d'||t==='dung'||t==='true')return 'Đ';if(String(p).trim()==='S'||t==='s'||t==='sai'||t==='false')return 'S';return ''}
function parseTfClient(v){let raw=String(v||'').trim();if(!raw)return [];let parts=raw.split(/[,;|/\n]+/).map(x=>x.trim()).filter(Boolean);if(parts.length>=2){let out=parts.map(tfTokenClient);if(out.filter(x=>x==='Đ'||x==='S').length>=2)return out}let s=raw.toUpperCase().replace(/\u0110/g,'D').replace(/\u0111/g,'D').replace(/DUNG/g,'D').replace(/TRUE/g,'D').replace(/SAI/g,'S').replace(/FALSE/g,'S');return (s.match(/[DSĐ]/g)||[]).map(c=>(c==='S'?'S':'Đ')).slice(0,4)}
function hasOptsClient(q){return ['A','B','C','D'].filter(L=>String((q||{})[L]||'').trim()).length>=2}
function looksDsAnswer(v){let raw=String(v||'').trim();if(!raw)return false;if(/^[ABCD]$/i.test(raw.replace(/\s/g,'')))return false;return parseTfClient(raw).filter(x=>x==='Đ'||x==='S').length>=2}
function isMcqLetter(v){let raw=String(v||'').trim().toUpperCase().replace(/\u0110/g,'D');return /^[ABCD]$/.test(raw)}
function looksShortAnswerClient(q){let d=String((q&&q.DapAn)||'').trim();if(!d)return false;if(isMcqLetter(q.DapAn))return false;if(looksDsAnswer(q.DapAn))return false;let n=d.replace(/\s/g,'').replace(',','.');if(/^-?\d+(\.\d+)?$/.test(n))return true;return d.length<=200}
function dangMetaRaw(q){if(!q)return '';for(let k of ['_DangCol','Dang']){let v=String(q[k]||'').trim();if(v)return v}return ''}
const DANG_GROUP_ORDER_CLIENT=['Trắc nghiệm','Đúng sai','Trả lời ngắn','Tự luận'];
function resolveDang(q){
  if(!q)return 'Trắc nghiệm';
  if(isMcqLetter(q.DapAn)&&hasOptsClient(q))return 'Trắc nghiệm';
  if(looksDsAnswer(q.DapAn))return 'Đúng sai';
  let rawCol=dangMetaRaw(q);
  let dc=normDangClient(rawCol);
  if(rawCol&&DANG_GROUP_ORDER_CLIENT.includes(dc))return dc;
  if(looksShortAnswerClient(q))return 'Trả lời ngắn';
  return 'Trắc nghiệm';
}
function applyResolvedDang(q){if(!q)return q;q.Dang=resolveDang(q);return q}
function dangSame(a,b){return normDangClient(a)===normDangClient(b)}
function questionLevelMatch(q,lv){if(!lv)return true;let u=String(q.MucDo||'').toUpperCase();let parts=u.split(/[,;/|]+/).map(x=>x.trim()).filter(Boolean);return parts.includes(lv)||u.includes(lv)}
function mucdoNorm(lv){let u=String(lv||'').trim().toUpperCase();if(!u)return'';if(u==='NB'||/\bNB\b/.test(u))return'NB';if(u==='TH'||/\bTH\b/.test(u))return'TH';if(u==='VDC'||u.includes('VDC'))return'VDC';if(u==='VD'||/\bVD\b/.test(u))return'VD';return''}
function mucdoBadgeClass(lv){let n=mucdoNorm(lv);if(n==='NB')return'mucdo-nb';if(n==='TH')return'mucdo-th';if(n==='VD')return'mucdo-vd';if(n==='VDC')return'mucdo-vdc';return String(lv||'').trim()?'mucdo-other':'mucdo-empty'}
function mucdoIcon(lv){let n=mucdoNorm(lv);if(n==='NB')return'🌱';if(n==='TH')return'💡';if(n==='VD')return'🔥';if(n==='VDC')return'🚀';return'▫️'}
function mucdoLabel(lv){let n=mucdoNorm(lv);if(n==='NB')return'Nhận biết';if(n==='TH')return'Thông hiểu';if(n==='VD')return'Vận dụng';if(n==='VDC')return'Vận dụng cao';return String(lv||'Chưa ghi mức độ').trim()}
function mucdoPrimary(mucdo){let raw=String(mucdo||'').trim();if(!raw)return'';let parts=raw.split(/[,;/|]+/).map(x=>x.trim()).filter(Boolean);for(let p of parts){let n=mucdoNorm(p);if(n)return n}return mucdoNorm(raw)}
function navMucDoClass(mucdo){let n=mucdoPrimary(mucdo);return n?'nav-'+mucdoBadgeClass(n):'nav-mucdo-empty'}
function navLvBadgeHtml(mucdo){let n=mucdoPrimary(mucdo);if(!n)return'';return`<span class="navLvBadge ${mucdoBadgeClass(n)}" title="${escAttr(mucdoLabel(n))}">${esc(n)}</span>`}
function navSectionClass(sec){let t=String(sec||'').toUpperCase();let n='';if(/\bVDC\b|MỨC\s*VDC|MUC\s*VDC/.test(t))n='VDC';else if(/\bVD\b|MỨC\s*VD|MUC\s*VD/.test(t))n='VD';else if(/\bTH\b|MỨC\s*TH|MUC\s*TH/.test(t))n='TH';else if(/\bNB\b|MỨC\s*NB|MUC\s*NB/.test(t))n='NB';return n?('navSection-'+mucdoBadgeClass(n).replace('mucdo-','')):''}
function navSectionIcon(sec){let t=String(sec||'').toUpperCase();if(/\bVDC\b|MỨC\s*VDC|MUC\s*VDC/.test(t))return mucdoIcon('VDC');if(/\bVD\b|MỨC\s*VD|MUC\s*VD/.test(t))return mucdoIcon('VD');if(/\bTH\b|MỨC\s*TH|MUC\s*TH/.test(t))return mucdoIcon('TH');if(/\bNB\b|MỨC\s*NB|MUC\s*NB/.test(t))return mucdoIcon('NB');return '📂'}
function syncQuestionMucDoChrome(q){let panel=document.querySelector('.quizQuestionPanel');if(!panel)return;panel.classList.remove('mucdoPanel-nb','mucdoPanel-th','mucdoPanel-vd','mucdoPanel-vdc','mucdoPanel-empty');let n=mucdoPrimary(q&&q.MucDo);let cls=n?('mucdoPanel-'+mucdoBadgeClass(n).replace('mucdo-','')):'mucdoPanel-empty';panel.classList.add(cls);panel.setAttribute('data-level-label',n||'');panel.setAttribute('title',n?('Mức độ '+n+' — '+mucdoLabel(n)):'');panel.removeAttribute('data-level-full');let dbt=String((q&&q.DangBaiTap)||'').trim();panel.setAttribute('data-dbt-label',dbt);// Render DangBaiTap label element next to NB badge
let existing=panel.querySelector('.quizDbtLabel');if(existing)existing.remove();if(dbt){let lbl=document.createElement('div');lbl.className='quizDbtLabel';lbl.innerHTML=`<span class="quizDbtText" title="${dbt.replace(/"/g,'&quot;')}">🏷️ ${dbt.replace(/</g,'&lt;')}</span>`;panel.appendChild(lbl)}}
function formatMucDoBadges(mucdo){let raw=String(mucdo||'').trim();if(!raw)return'';let parts=raw.split(/[,;/|]+/).map(x=>x.trim()).filter(Boolean);if(!parts.length)parts=[raw];return parts.map(p=>{let n=mucdoNorm(p)||p;return `<span class="mucdoBadge ${mucdoBadgeClass(p)}" title="Mức độ (cột I): ${escAttr(p)} · ${escAttr(mucdoLabel(p))}"><span class="mucdoIcon">${mucdoIcon(p)}</span><span class="mucdoShort">${esc(n)}</span><span class="mucdoFull">${esc(mucdoLabel(p))}</span></span>`}).join(' ')}
function filterQuestionsByDang(qs,dang){dang=String(dang||'').trim();if(!dang)return qs||[];let want=normDangClient(dang);return (qs||[]).filter(q=>normDangClient(applyResolvedDang(q).Dang)===want)}
function filterQuestionsByLevel(qs,lv){lv=(lv||'').trim().toUpperCase();if(!lv)return qs||[];return (qs||[]).filter(q=>questionLevelMatch(q,lv))}
function applyQuizFilters(qs,lv,dg){return filterQuestionsByDang(filterQuestionsByLevel(qs||[],lv),dg)}
function updateFilterBadge(lv,dg,count,dbt){let el=document.getElementById('filterBadge');if(!el)return;dbt=String(dbt||CURRENT_DANGBAITAP||'').trim();if(!lv&&!dg&&!dbt){el.textContent='';el.classList.add('hide');return}let parts=[];if(dbt){parts.push('BT: '+dbtFilterLabel(dbt));if(isDbtUnclassifiedFilter(dbt)&&USER.is_admin)parts.push('→ 🏷️ Gợi ý Dạng BT')}if(dg)parts.push(dg);if(lv)parts.push('mức '+lv);el.textContent='🎯 Lọc: '+parts.join(' · ')+(count!=null?' ('+count+' câu)':'');el.classList.remove('hide')}
function isDbtUnclassifiedFilter(v){v=String(v||'');return v===DBT_UNCLASSIFIED||normText(v)==='chua phan loai'||normText(v)==='chua gan'}
function dbtFilterLabel(v){return isDbtUnclassifiedFilter(v)?DBT_UNCLASSIFIED_LABEL:String(v||'')}
function isQuestionDone(i){let q=QUESTIONS[i];if(!q)return false;q=applyResolvedDang(q);let a=ANSWERS[i];if(q.Dang=='Trắc nghiệm')return !!String(a||'').trim();if(q.Dang=='Đúng sai'){if(!Array.isArray(a))return false;let req=0;for(let L of ['A','B','C','D'])if(q[L])req++;let filled=a.filter(v=>!!String(v||'').trim()).length;return req>0&&filled>=req}return !!String(a||'').trim()}
function countDone(){let n=0;for(let i=0;i<QUESTIONS.length;i++)if(isQuestionDone(i))n++;return n}
function notifyDoneIfNeeded(){if(SUBMITTED||COMPLETED_NOTICE||!QUESTIONS.length)return;let done=countDone();if(done>=QUESTIONS.length){COMPLETED_NOTICE=true;alert('✅ Đã làm hết đề. Thầy/các em có thể xem lại các câu.')}} 
function val(id){let el=document.getElementById(id);return el?el.value:''}
function mathJaxIsUsable(){let mj=window.MathJax;return !!(mj&&(mj.typesetPromise||mj.typeset||(mj.startup&&mj.startup.promise)))}
function ensureMathJaxCdnFallback(){if(mathJaxIsUsable()||document.getElementById('LDVL_MATHJAX_FALLBACK'))return;let s=document.createElement('script');s.id='LDVL_MATHJAX_FALLBACK';s.defer=true;s.crossOrigin='anonymous';s.src='https://unpkg.com/mathjax@3/es5/tex-svg.js';document.head.appendChild(s)}
function waitForMathJaxReady(timeoutMs){timeoutMs=timeoutMs||15000;return new Promise(resolve=>{let t0=Date.now();let fbAt=t0+3500;(function tick(){let mj=window.MathJax;if(mathJaxIsUsable()){if(mj.startup&&mj.startup.promise){mj.startup.promise.then(()=>resolve(true)).catch(()=>resolve(false));return}resolve(true);return}if(Date.now()>=fbAt)ensureMathJaxCdnFallback();if(Date.now()-t0>=timeoutMs){resolve(false);return}setTimeout(tick,80)})()})}
let QUIZ_MATH_GEN=0;
let _mjTypesetChain=Promise.resolve();
function enqueueMathJax(job){_mjTypesetChain=_mjTypesetChain.catch(function(){}).then(job);return _mjTypesetChain}
function invalidateQuizMath(){QUIZ_MATH_GEN++}
function nodeMathJaxBroken(el){if(!el||!el.querySelectorAll)return false;let mjx=el.querySelectorAll('mjx-container');if(!mjx.length)return false;for(let n of mjx){let t=String(n.textContent||'').trim();if(t)return false;try{if(n.getBoundingClientRect&&n.getBoundingClientRect().height>6)return false}catch(e){}}return true}
function latexFallbackPlain(inner){let s=String(inner||'');s=s.replace(/\\(?:left|right)\s*/g,'');s=s.replace(/\\dfrac\s*\{([^{}]+)\}\s*\{([^{}]+)\}/g,'($1)/($2)');s=s.replace(/\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}/g,'($1)/($2)');s=s.replace(/\\sqrt\s*\{([^{}]+)\}/g,'√($1)');s=s.replace(/\\text\s*\{([^{}]*)\}/g,' $1');s=s.replace(/\\mathrm\s*\{([^{}]*)\}/g,' $1');let map={omega:'ω',varphi:'φ',phi:'φ',pi:'π',theta:'θ',alpha:'α',beta:'β',Delta:'Δ',delta:'δ',pm:'±',cdot:'·',times:'×',leq:'≤',geq:'≥',neq:'≠',approx:'≈',cos:'cos',sin:'sin',tan:'tan',cot:'cot'};s=s.replace(/\\([A-Za-z]+)/g,(m,k)=>map[k]||k);let sub={'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉','+':'₊','-':'₋'};let sup={'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹','+':'⁺','-':'⁻'};s=s.replace(/_\{([^{}]{1,4})\}/g,(m,a)=>a.split('').map(ch=>sub[ch]||ch).join(''));s=s.replace(/\^\{([^{}]{1,4})\}/g,(m,a)=>a.split('').map(ch=>sup[ch]||ch).join(''));s=s.replace(/_/g,'');s=s.replace(/\^/g,'');s=s.replace(/[{}]/g,'');return s.trim()}
function applyLatexFallback(root){let list=root?(Array.isArray(root)?root:[root]).filter(Boolean):[document.body];for(let el of list){if(!el||!el.innerHTML)continue;if(el.querySelector&&el.querySelector('mjx-container')&&!nodeMathJaxBroken(el))continue;el.innerHTML=el.innerHTML.replace(/\$([^$<]{1,800})\$/g,function(_,inner){return '<span class="mjFallback">'+esc(latexFallbackPlain(inner))+'</span>'})}}
function typesetNow(els){let list=els?(Array.isArray(els)?els:[els]).filter(Boolean):[];if(!list.length)return Promise.resolve();return enqueueMathJax(function(){return waitForMathJaxReady(15000).then(ok=>{if(!ok){applyLatexFallback(list);return}try{if(window.MathJax&&MathJax.typesetClear)MathJax.typesetClear(list)}catch(e){}if(MathJax.typesetPromise)return MathJax.typesetPromise(list).then(function(){if(list.some(nodeMathJaxBroken))applyLatexFallback(list)}).catch(function(){applyLatexFallback(list)});if(MathJax.typeset){try{MathJax.typeset(list);if(list.some(nodeMathJaxBroken))applyLatexFallback(list)}catch(e2){applyLatexFallback(list)}}})})}
function typesetDebateMath(){let els=['quizDebateClaude','quizDebateGemini','quizDebateFinal','quizDebateChatLog'].map(function(id){return document.getElementById(id)}).filter(Boolean);return typesetNow(els)}
function typeset(els){let gen=QUIZ_MATH_GEN;let list=els?(Array.isArray(els)?els:[els]).filter(Boolean):null;return enqueueMathJax(function(){return waitForMathJaxReady(15000).then(ok=>{if(gen!==QUIZ_MATH_GEN)return Promise.resolve();if(!ok){applyLatexFallback(list);return Promise.resolve()}let run=()=>{if(gen!==QUIZ_MATH_GEN)return Promise.resolve();try{if(list&&list.length&&MathJax.typesetClear)MathJax.typesetClear(list)}catch(e){}if(MathJax.typesetPromise)return MathJax.typesetPromise(list&&list.length?list:undefined).then(()=>{if(gen!==QUIZ_MATH_GEN)return;if(list&&list.some(nodeMathJaxBroken))applyLatexFallback(list)}).catch(()=>{if(gen===QUIZ_MATH_GEN)applyLatexFallback(list)});if(MathJax.typeset){try{MathJax.typeset(list&&list.length?list:undefined);if(list&&list.some(nodeMathJaxBroken))applyLatexFallback(list)}catch(e){applyLatexFallback(list)}}return Promise.resolve()};if(MathJax.startup&&MathJax.startup.promise)return MathJax.startup.promise.then(run).catch(()=>applyLatexFallback(list));return run()})})}
let _theoryTypesetTimer=0;
function typesetTheoryMath(){
  return new Promise(resolve=>{
    if(_theoryTypesetTimer)clearTimeout(_theoryTypesetTimer);
    _theoryTypesetTimer=setTimeout(()=>{
      _theoryTypesetTimer=0;
      let els=[...document.querySelectorAll('.theoryEnvContent,.learningMethodLatex,.learningTheoryLatex')];
      let ep=document.getElementById('theoryEditorPreview');if(ep)els.push(ep);
      els=[...new Set(els.filter(Boolean))];
      requestAnimationFrame(()=>{typeset(els).then(resolve).catch(()=>resolve())});
    },48);
  });
}
function quizMathTypesetEls(){return [document.getElementById('qtext'),document.getElementById('options'),document.getElementById('solution'),document.getElementById('hintBox')].filter(Boolean)}
function typesetQuizMath(){return typeset(quizMathTypesetEls()).then(()=>typesetTheoryMath())}
function typesetQuizMathWithRetry(tries,delay){let gen=++QUIZ_MATH_GEN;tries=(tries==null?2:Math.max(1,parseInt(tries,10)||1));delay=delay||0;return new Promise(resolve=>{setTimeout(()=>{if(gen!==QUIZ_MATH_GEN){resolve();return}typesetQuizMath().then(()=>{if(gen!==QUIZ_MATH_GEN){resolve();return}let els=quizMathTypesetEls();let broken=els.some(nodeMathJaxBroken);if(broken&&tries>1)return typesetQuizMathWithRetry(tries-1,280).then(resolve);if(broken)applyLatexFallback(els);resolve()}).catch(()=>{if(gen!==QUIZ_MATH_GEN){resolve();return}if(tries>1)typesetQuizMathWithRetry(tries-1,280).then(resolve);else resolve()})},delay)})}
function safeInsertBefore(parent,node,ref){if(!parent||!node)return;if(ref&&ref.parentNode===parent)parent.insertBefore(node,ref);else parent.appendChild(node)}
function safeInsertAfter(parent,node,ref){if(!parent||!node)return;if(ref&&ref.parentNode===parent)safeInsertBefore(parent,node,ref.nextSibling);else parent.appendChild(node)}
function syncFulldeNavChrome(){if(!FULLDE_ON)return;ensureNavInfo();ensureNavLegend();if(isMobileQuizUI())return;let panel=document.querySelector('.fsNavPanel');if(panel){panel.style.display='flex';panel.style.flexDirection='column';panel.style.height='100%';panel.style.minHeight='0'}let body=document.querySelector('.fsNavPanel .mobileNavBody');if(body){body.style.display='flex';body.style.flexDirection='column';body.style.flex='1';body.style.minHeight='0';body.style.overflow='hidden';body.style.width='100%'}let nav=document.getElementById('navNums');if(nav){nav.style.display='grid';nav.style.width='100%';nav.style.flex='1';nav.style.minHeight='140px';nav.style.overflowY='auto';nav.style.overflowX='hidden'}}
function cleanAiDisplayText(s){s=String(s||'').replace(/\r/g,'').trim();if(!s)return '';s=s.replace(/```[a-zA-Z]*\n?/g,'').replace(/```/g,'');s=s.replace(/^#{1,6}\s+(.+)$/gm,'$1');s=s.replace(/\*\*([^*\n]+?)\*\*/g,'$1');s=s.replace(/(^|[^\*])__([^_\n]+?)__/g,'$1$2');s=s.replace(/^[ \t]*[*•]\s+/gm,'');s=s.replace(/([^\n])\s+(Bước\s*\d+\s*[:.])/gi,'$1\n\n$2');s=s.replace(/([^\n])\s+(Đáp án\s*:)/gi,'$1\n\n$2');s=s.replace(/([^\n])\s+(Kết luận\s*:)/gi,'$1\n\n$2');s=s.replace(/([^\n])\s+(Trong đó\s*:)/gi,'$1\n\n$2');s=s.replace(/\n{3,}/g,'\n\n');return s.trim()}
function normalizeTikzBlockForRender(tz){tz=String(tz||'').trim();if(!tz)return '';if(/\\begin\s*\{\s*tikzpicture\s*\}/i.test(tz)&&!/\\end\s*\{\s*tikzpicture\s*\}/i.test(tz))tz+='\n\\end{tikzpicture}';return tz}
function theorySplitTikzSegments(s){s=String(s||'');let re=/\\begin\s*\{\s*tikzpicture\s*\}[\s\S]*?\\end\s*\{\s*tikzpicture\s*\}/gi;let segs=[],blocks=[],last=0,m,uid=(Date.now().toString(36)+Math.random().toString(36).slice(2,6));while((m=re.exec(s))){if(m.index>last)segs.push({type:'text',content:s.slice(last,m.index)});blocks.push(m[0]);segs.push({type:'tikz',idx:blocks.length-1,uid:uid+'_'+blocks.length});last=m.index+m[0].length}if(last<s.length)segs.push({type:'text',content:s.slice(last)});if(!blocks.length){let open=s.search(/\\begin\s*\{\s*tikzpicture\s*\}/i);if(open>=0){segs=[];if(open>0)segs.push({type:'text',content:s.slice(0,open)});blocks.push(s.slice(open));segs.push({type:'tikz',idx:0,uid:uid+'_1'});return {segs,blocks}}segs=[{type:'text',content:s}]}return {segs,blocks}}
function stripQuizSourceLeak(s){s=String(s||'');s=s.replace(/\\color\s*\{[^}]*\}\s*\{\s*\\text\s*\{\s*\\?nguonly[^}]*\}\s*\}/gi,'');s=s.replace(/\\textcolor\s*\{[^}]*\}\s*\{\s*\\text\s*\{\s*\\?nguonly[^}]*\}\s*\}/gi,'');s=s.replace(/\\text\s*\{\s*\\?nguonly[^}]*\}/gi,'');s=s.replace(/\\nguonly[^\s{}\\]*/gi,'');s=s.replace(/[A-Za-z0-9_\-]*nguonly[A-Za-z0-9_\-]*\.pdf\b/gi,'');return s}
function formatHintDisplay(s){s=stripQuizSourceLeak(cleanAiDisplayText(s));if(!s)return '';s=s.replace(/\$\$\s*/g,'$');s=s.replace(/\s*\$\$/g,'$');s=s.replace(/\$\s*\n+\s*\$/g,'');s=s.replace(/\$\s*\n+\s*([^$\n]+?)\s*\n+\s*\$/g,'$( $1 )$');s=s.replace(/\$\s*\n+([^$\n]+?)\s*\$/g,'$( $1 )$');s=s.replace(/\$\s*\$/g,'');s=s.replace(/^###\s+(.+)$/gm,'@@B@@$1@@/B@@');if(/\\begin\s*\{\s*tikzpicture\s*\}/i.test(s))return renderTextWithTikzBlocks(s);return renderRichText(s)}
function renderQuizFieldHtml(s){return formatHintDisplay(s)}
function fieldHasInlineTikz(s){return /\\begin\s*\{\s*tikzpicture/i.test(String(s||''))}
function renderTextWithTikzBlocks(s){let split=theorySplitTikzSegments(String(s||'')),html='';for(let seg of split.segs){if(seg.type==='text'){let t=String(seg.content||'');if(!t.trim())continue;html+=renderRichText(t);continue}let tz=normalizeTikzBlockForRender(split.blocks[seg.idx]||'');if(!tz)continue;let id='inlineTikz_'+seg.uid;let enc=encodeTikzRawClient(tz);html+=`<div class="lgTikzSlot qimgWrap tikzRawWrap" id="${escAttr(id)}"><div class="muted" style="font-size:12px;padding:12px;text-align:center">⏳ Đang vẽ biểu đồ…</div></div>`;setTimeout(()=>renderTikzRawToImg(enc,id),0)}return html}
function dsCircleHtml(L){return `<span class="dsCircle" aria-label="Ý ${L}">${L}</span>`}
function stripOptionPrefix(text,L){text=String(text||'').trim();if(!text)return text;let m=text.match(new RegExp('^\\s*'+L+'\\s*[\\.\\)\\:]\\s*','i'));if(m)return text.slice(m[0].length).trim();let any=text.match(/^\s*[ABCD]\s*[\.\)\:]\s*/i);if(any)return text.slice(any[0].length).trim();return text}
function stripImmini(text){text=String(text||'').trim();let m=text.match(/\\immini\s*\{([\s\S]*)\}\s*$/i);if(m)return m[1].trim();return text.replace(/^\\immini\s*\{/i,'').replace(/\}\s*$/,'').trim()}
function tikzRawCodeFallback(src,msg){try{let b=src.replace(/^tikzraw:/i,'').trim().replace(/-/g,'+').replace(/_/g,'/');while(b.length%4)b+='=';let code=decodeURIComponent(escape(atob(b)));let note=msg?`<div class="muted" style="font-size:12px;color:#b45309;margin-bottom:6px">${esc(msg)}</div>`:'';return `<div class="qimgWrap tikzRawWrap">${note}<div class="muted" style="font-size:12px;margin-bottom:6px;font-weight:800">📐 TikZ</div><pre class="tikzRawCode" style="white-space:pre-wrap;font-size:11px;max-height:280px;overflow:auto;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px">${esc(code)}</pre></div>`}catch(e){return `<div class="qimgErr">Không đọc được mã TikZ.</div>`}}
function decodeTikzRawClient(src){try{let b=String(src||'').replace(/^tikzraw:/i,'').trim().replace(/-/g,'+').replace(/_/g,'/');while(b.length%4)b+='=';return decodeURIComponent(escape(atob(b)))}catch(e){return ''}}
function encodeTikzRawClient(code){if(!String(code||'').trim())return '';try{return 'tikzraw:'+btoa(unescape(encodeURIComponent(String(code)))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')}catch(e){return ''}}
function extractTikzBlocksClient(text){let s=String(text||'');if(!s)return {cleaned:'',tikz:''};let re=/\\begin\s*\{\s*tikzpicture\s*\}[\s\S]*?\\end\s*\{\s*tikzpicture\s*\}/gi;let blocks=[];let m;while((m=re.exec(s)))blocks.push(m[0]);let cleaned=s.replace(re,' ').replace(/[ \t]+\n/g,'\n').replace(/\n{3,}/g,'\n\n').replace(/  +/g,' ').trim();return {cleaned,tikz:blocks.join('\n\n')}}
function adminMergeTikzIntoField(tzEl,fragment){if(!fragment||!tzEl)return;let cur=String(tzEl.value||'').trim();if(!cur)tzEl.value=fragment;else if(!cur.includes(fragment.slice(0,Math.min(48,fragment.length))))tzEl.value=cur+'\n\n'+fragment}
function adminExtractTikzFromFormFields(){return false}
function parseHinhanhCellClient(raw){let s=String(raw||'').trim();if(!s)return {img:'',tikz:''};let lines=s.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);let img='',tikz='';for(let ln of lines){if(/^tikzraw:/i.test(ln))tikz=decodeTikzRawClient(ln)||tikz;else if(!img&&(extractDriveFidClient(ln)||/^https?:\/\//i.test(ln)||/^\/static\//i.test(ln)||/^static\//i.test(ln)))img=ln}if(!tikz&&lines.length===1&&/^tikzraw:/i.test(lines[0])){tikz=decodeTikzRawClient(lines[0]);return {img:lines[0],tikz}}if(!img&&tikz)return {img:encodeTikzRawClient(tikz),tikz};return {img,tikz}}
function buildHinhanhCellClient(img,tikz){let parts=[];let i=String(img||'').trim();let t=String(tikz||'').trim();if(i&&!/^tikzraw:/i.test(i))parts.push(i);if(t){let tr=encodeTikzRawClient(t);if(tr)parts.push(tr)}return parts.join('\n')}
function adminMergedHinhAnhFromForm(){let imgEl=document.getElementById('edit_HinhAnh');let tzEl=document.getElementById('edit_Tikz');return buildHinhanhCellClient(imgEl?imgEl.value:'',tzEl?tzEl.value:'')}
function adminPreviewHinhAnhSrc(){let merged=adminMergedHinhAnhFromForm();if(!merged)return '';let parsed=parseHinhanhCellClient(merged);if(parsed.tikz)return encodeTikzRawClient(parsed.tikz);return normalizeImageSrcClient(merged)}
function tikzCacheStorageKey(src){let h=0,s=String(src||'');for(let i=0;i<s.length;i++)h=((h<<5)-h+s.charCodeAt(i))|0;return 'ldvl_tikz_'+Math.abs(h).toString(36)}
function tikzImgFromCacheClient(src){if(!src)return '';let m=window.TIKZ_IMG_CACHE;if(m&&m.has(src))return m.get(src);try{let u=sessionStorage.getItem(tikzCacheStorageKey(src));if(u){if(!m)window.TIKZ_IMG_CACHE=new Map();window.TIKZ_IMG_CACHE.set(src,u);return u}}catch(e){}return ''}
function tikzCacheRememberClient(src,url){if(!src||!url)return;try{let m=window.TIKZ_IMG_CACHE||(window.TIKZ_IMG_CACHE=new Map());m.set(src,url);sessionStorage.setItem(tikzCacheStorageKey(src),url)}catch(e){}}
function tikzRenderFetch(src){if(!src)return Promise.resolve(null);let cached=tikzImgFromCacheClient(src);if(cached)return Promise.resolve({ok:true,url:cached,cached:true});let inflight=window.TIKZ_RENDER_INFLIGHT||(window.TIKZ_RENDER_INFLIGHT=new Map());if(inflight.has(src))return inflight.get(src);let p=api('/api/tikz/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({src})}).then(j=>{if(j&&j.ok&&j.url)tikzCacheRememberClient(src,j.url);return j}).finally(()=>inflight.delete(src));inflight.set(src,p);return p}
function tikzImgHtmlFromUrl(url,alt){return `<div class="qimgWrap"><img class="qimg" src="${esc(normalizeImageSrcClient(url))}" alt="${esc(alt||'Đồ thị TikZ')}"${qimgOnErrorAttr()}></div>`}
async function renderTikzRawToImg(src,boxId){let box=document.getElementById(boxId);if(!box)return;try{let j=await tikzRenderFetch(src);if(j&&j.ok&&j.url){let wrap=document.createElement('div');wrap.innerHTML=tikzImgHtmlFromUrl(j.url);let node=wrap.firstElementChild;if(node)box.replaceWith(node);if(typeof typeset==='function')typeset((node&&node.parentElement)||document.body);return}box.outerHTML=tikzRawCodeFallback(src,(j&&j.error)||'Chưa vẽ được PNG')}catch(e){box.outerHTML=tikzRawCodeFallback(src,e.message||'Lỗi mạng')}}
function isDriveFolderUrl(s){s=String(s||'').toLowerCase();return s.includes('drive.google.com')&&(s.includes('/folders/')||s.includes('/fold'))}
function driveThumbUrl(fid){return 'https://drive.google.com/thumbnail?id='+String(fid||'').trim()+'&sz=w1600'}
function extractDriveFidClient(s){s=String(s||'').trim();if(!s||isDriveFolderUrl(s))return '';let m=s.match(/=\s*IMAGE\s*\(\s*["']([^"']+)["']/i);if(m)s=m[1].trim();let dm=s.match(/thumbnail\?id=([^&]+)/i)||s.match(/drive\.google\.com\/file\/d\/([^/]+)/i)||s.match(/googleusercontent\.com\/d\/([^=/?]+)/i)||s.match(/\/api\/img\/drive\/([^/?]+)/i)||s.match(/[?&]id=([^&]+)/i)||s.match(/\/d\/([^/]+)/i);return dm?dm[1].trim():''}
function normalizeImageSrcClient(v){let s=String(v||'').trim();if(!s)return '';if(/[\r\n]/.test(s)){let parsed=parseHinhanhCellClient(s);if(parsed.img&&!/^tikzraw:/i.test(parsed.img))return normalizeImageSrcClient(parsed.img);if(parsed.tikz)return encodeTikzRawClient(parsed.tikz);return ''}if(/^tikzraw:/i.test(s))return s;if(isDriveFolderUrl(s))return '';let fid=extractDriveFidClient(s);if(fid)return driveThumbUrl(fid);if(/^https?:\/\//i.test(s))return s;if(s.startsWith('/static/'))return s;if(/^static\//i.test(s))return '/'+s;if(/^images\//i.test(s))return '/static/'+s;return s}
function qimgOnErrorAttr(){return ' onerror="if(!this.dataset.fbk){let fid=extractDriveFidClient(this.src);if(fid){this.dataset.fbk=\'1\';this.src=driveThumbUrl(fid);return}this.parentElement.outerHTML=\'<div class=\\\'qimgErr\\\'>Không tải được hình. File Drive cần quyền Anyone with link.</div>\'}"'}
function buildQimgHtml(src){let raw=String(src||'').trim();if(isDriveFolderUrl(raw))return '<div class="qimgErr" style="background:#f0fdf4;border-color:#86efac;color:#166534;padding:10px;border-radius:8px;font-size:13px">Đây là <b>link thư mục</b> Drive — sửa câu, <b>để trống cột T</b>, bấm Lưu (TikZ tự điền link ảnh).</div>';if(/[\r\n]/.test(raw)){let parsed=parseHinhanhCellClient(raw);if(parsed.img&&!/^tikzraw:/i.test(parsed.img))return tikzImgHtmlFromUrl(normalizeImageSrcClient(parsed.img),'Hình minh họa')}src=normalizeImageSrcClient(raw);if(!src)return '';if(/^tikzraw:/i.test(src)){let cached=tikzImgFromCacheClient(src);if(cached)return tikzImgHtmlFromUrl(cached);let boxId='tikz_'+Date.now().toString(36)+Math.random().toString(36).slice(2,7);setTimeout(()=>renderTikzRawToImg(src,boxId),0);return `<div class="qimgWrap tikzRawWrap" id="${boxId}"><div class="muted" style="font-size:12px;padding:12px;text-align:center">⏳ Đang vẽ đồ thị TikZ…</div></div>`}return tikzImgHtmlFromUrl(src,'Hình minh họa')}
function questionStemNeedsFigure(q){if(!q)return false;let scan=String(q.CauHoi||'');for(let L of ['A','B','C','D'])scan+='\n'+String(q[L]||'');if(/(?:hình\s*(?:vẽ|bên|sau|minh\s*họa)|xét\s+hình|trong\s+hình|như\s+hình|theo\s+hình|minh\s+họa)/i.test(scan))return true;return /\\begin\s*\{\s*tikzpicture|\\includegraphics|\\immini|\[IMG\]|<img\b|tikzraw:/i.test(scan)}
function loigiaiForceSolutionOnly(lg){return /\[\s*LG-ONLY\s*\]/i.test(String(lg||''))}
function stripLoigiaiLayoutMarkers(s){return String(s||'').replace(/\[\s*LG-ONLY\s*\]/gi,'').trim()}
function hinhanhIsSolutionFigure(q){if(!q||!String(q.HinhAnh||'').trim())return false;let lg=String(q.LoiGiai||'').trim();if(loigiaiForceSolutionOnly(lg))return true;return /\[(?:HINH|IMG|T)(?:-LG)?\]/i.test(lg)}
function buildHinhAnhSolutionFigHtml(q){if(!q||!String(q.HinhAnh||'').trim())return '';return buildQimgHtml(q.HinhAnh)}
function appendSolutionFigureIfNeeded(html,q,rawLg){return html||''}
function usesImgSplit(q){if(!q||!String(q.HinhAnh||'').trim())return false;if(fieldHasInlineTikz(q.CauHoi))return false;if(hinhanhIsSolutionFigure(q))return false;if(!questionStemNeedsFigure(q))return false;let parsed=parseHinhanhCellClient(q.HinhAnh);if(parsed.tikz&&!parsed.img)return false;return q.Dang==='Trắc nghiệm'||q.Dang==='Đúng sai'||q.Dang==='Trả lời ngắn'}
function isTlnImgSplit(q){return !!(q&&q.Dang==='Trả lời ngắn'&&String(q.HinhAnh||'').trim()&&!hinhanhIsSolutionFigure(q))}
function mcqUsesSplit(q){return usesImgSplit(q)}
function adminTlnSheetAnswerHtml(q){if(!USER.is_admin||!q)return '';let da=String(q.DapAn||'').trim();if(!da)return '<div class="adminTlnAns adminTlnAnsWarn">⚠ ADMIN: cột P (Đáp án) đang trống.</div>';let ss=String(q.SaiSo||'').trim();let ssNote=ss?` <span class="muted">· sai số ±${esc(ss)}</span>`:'';return `<div class="adminTlnAns">📋 ADMIN — Đáp án Sheet (P): <b>${renderRichText(da)}</b>${ssNote}</div>`}
function buildShortAnsHtml(q,opts){opts=opts||{};let compact=opts.compact!==false;let withQ=!!opts.withQuestion;let cr=RESULTS[CUR]||CHECKED[CUR];let checked=!!(cr&&(cr.ok===true||cr.ok===false));let saDis=(SUBMITTED||LOCKED_Q[CUR]||checked)?'disabled':'';let saCls='shortAnsBox';if(cr&&cr.ok===true)saCls+=' correct';else if(cr&&cr.ok===false)saCls+=' wrong';if(compact)saCls+=' shortAnsCompact';let saFb=shortAnswerFeedbackHtml(q);let qBlock=withQ?`<div class="shortAnsQtext">${renderQuizFieldHtml(q.CauHoi||'')}</div>`:'';let adminBlock=adminTlnSheetAnswerHtml(q);if(USER.is_admin){return `<div class="${saCls}">${qBlock}${adminBlock}<div class="muted shortAnsNote">ADMIN xem đáp án/lời giải ngay — không cần nhập hay chấm.</div></div>`}let chkDis=saDis;let note=checked?'Đã chấm — xem kết quả phía trên. VIP có thể mở ĐA/LG.':'Nhập đáp án rồi bấm <b>✓ Kiểm tra</b> (hoặc Enter) để xem đúng/sai ngay.';let inp=`<input id="shortAnsInput" class="shortAnsInput${compact?'':' shortAnsInputWide'}" type="text" maxlength="80" inputmode="text" enterkeyhint="go" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="${compact?'Nhập đáp án…':'Nhập số, chữ hoặc kết quả…'}" value="${escAttr(ANSWERS[CUR]||'')}" ${saDis} oninput="saveShortAnswer()" onfocus="shortAnsOnFocus(this)" onblur="shortAnsBlurCleanup(this)" ontouchstart="shortAnsTouchFocus(event,this)" onclick="focusShortAnsInput(this)" onkeydown="if(event.key==='Enter'){commitShortAnswer();event.preventDefault()}">`;let btn=`<button type="button" class="shortAnsBtn btnStartStrong" ${chkDis} onclick="commitShortAnswer()" title="Kiểm tra đáp án ngay">✓ Kiểm tra</button>`;if(compact)return `<div class="${saCls}">${qBlock}<div class="shortAnsFieldRow"><span class="shortAnsLbl">Đáp án</span>${inp}${btn}</div>${saFb}<div class="muted shortAnsNote">${note}</div></div>`;return `<div class="${saCls}"><label style="display:block;font-weight:800;margin-bottom:8px">✏️ Điền đáp án (trả lời ngắn)</label><div class="shortAnsFieldRow">${inp}${btn}</div>${saFb}<div class="muted shortAnsNote">${note}</div></div>`}
function dsVerdictLabel(v){let t=String(v||'').trim();if(!t)return '';if(/^s(ai)?$/i.test(t)||t==='S')return 'Sai';return 'Đúng'}
function currentQuestion(){let q=QUESTIONS[CUR];return q?applyResolvedDang(q):null}
function isCurrentQuestionDs(){let q=currentQuestion();return !!(q&&q.Dang==='Đúng sai')}
function isCurrentQuestionTn(){let q=currentQuestion();return !!(q&&q.Dang==='Trắc nghiệm')}
function parseDsAnswerTokens(text){let t=String(text||'').trim();if(!t)return [];let tagged=[...t.matchAll(/([ABCD])\s*[=:\-]\s*(Đúng|Sai|Đ|S|D)/gi)];if(tagged.length>=2)return tagged.map(x=>({letter:x[1].toUpperCase(),verdict:dsVerdictLabel(x[2])}));let parts=t.split(/[,;|/\s]+/).map(x=>x.trim()).filter(Boolean);if(parts.length>=2&&parts.every(p=>/^[ĐDSđds]$/i.test(p.replace(/\u0110/g,'D')))){return parts.slice(0,4).map((p,i)=>({letter:['A','B','C','D'][i],verdict:dsVerdictLabel(p)}))}let compact=t.toUpperCase().replace(/\u0110/g,'D').replace(/[^DS]/g,'');if(compact.length>=2&&compact.length<=4){return compact.split('').map((c,i)=>({letter:['A','B','C','D'][i],verdict:c==='S'?'Sai':'Đúng'}))}return []}
function formatDsAnswerBadges(text){let parts=parseDsAnswerTokens(text);if(!parts.length)return formatHintDisplay(text);return `<div class="dsAnswerRow">${parts.map(p=>`<div class="dsAnswerItem">${dsCircleHtml(p.letter)} <b class="${p.verdict==='Sai'?'dsVerdictSai':'dsVerdictDung'}">${esc(p.verdict)}</b></div>`).join('')}</div>`}
function dsTokenLabel(v){let t=String(v||'').trim();if(!t)return '?';if(/^s$/i.test(t)||t==='S')return 'Sai';return 'Đúng'}
function isQuestionChecked(qIdx){if(SUBMITTED){let r=RESULTS[qIdx];return !!(r&&(r.ok===true||r.ok===false))}return !!CHECKED[qIdx]}
function getDsCheckRows(q,r,ans){if(r&&Array.isArray(r.rows)&&r.rows.length)return r.rows;let vMap={};parseDsAnswerTokens(String(q.DapAn||'')).forEach(t=>vMap[t.letter]=t.verdict==='Sai'?'S':'Đ');if(!Object.keys(vMap).length){let c=String(q.DapAn||'').toUpperCase().replace(/\u0110/g,'D').replace(/[^DS]/g,'');c.split('').forEach((x,i)=>{let L=['A','B','C','D'][i];if(L&&q[L])vMap[L]=x==='S'?'S':'Đ'})}let old=Array.isArray(ans)?ans.slice():[];while(old.length<4)old.push('');let rows=[];['A','B','C','D'].forEach((L,i)=>{if(!q[L])return;let c=vMap[L]||'';let ch=String(old[i]||'').trim();if(ch==='D'||ch==='d')ch='Đ';rows.push({letter:L,correct:c,chosen:ch,ok:ch?!!(c&&ch===c):null})});return rows}
function formatDsCheckResultBox(qIdx,j,q,ans){let rows=getDsCheckRows(q,j,ans);if(!rows.length)return `<span>Câu ${qIdx+1}: ${j.ok?'✅ Đúng':'❌ Sai'}</span>`;let okN=rows.filter(x=>x.ok===true).length,tot=rows.length;let head=j.ok?`✅ Đúng (${tot}/${tot} ý)`: `❌ Sai (${okN}/${tot} ý đúng)`;let badges=rows.map(r=>{let cls=r.ok===true?'dsCheckOk':(r.ok===false?'dsCheckBad':'');let mark=r.ok===true?'✓':(r.ok===false?'✗':'?');let title='';if(r.ok===false){title=` title="Bạn: ${dsTokenLabel(r.chosen)}`;if(canViewSolutionLive()||USER.is_admin)title+=` · Đáp án: ${dsTokenLabel(r.correct)}`;title+='"' }return `<span class="dsCheckItem ${cls}"${title}>${r.letter} ${mark}</span>`}).join('');return `<div class="dsCheckBox"><div class="dsCheckHead">Câu ${qIdx+1}: ${head}</div><div class="dsCheckRow">${badges}</div></div>`}
function pedagogyAnswerText(q,a){if(a==null||a==='')return '';if(q&&q.Dang==='Trắc nghiệm')return 'Phương án '+a;return String(a)}
/* Kho công thức dựng sẵn trong app — dùng khi Sheet Phương pháp/Lý thuyết chưa có dữ liệu.
   Ánh xạ theo TỪ KHÓA trong Dạng bài tập / Bài học (KHÔNG theo ID câu cụ thể). */
let PED_BUILTIN_FORMULAS=[
  {
    test:function(q){let s=normText([q.DangBaiTap,q.BaiHoc,q.Chuong].join(' '));return /sai\s*so/.test(s)&&(/do\b|do\s*luong|phep\s*do|do\s*dac|do\s*truc\s*tiep/.test(s)||/sai\s*so\s*phep\s*do/.test(s))},
    item:{
      TenPhuongPhap:'Sai số phép đo trực tiếp',
      CongThucSuDung:'Giá trị trung bình: $\\overline{x}=\\dfrac{x_1+x_2+\\cdots+x_n}{n}$<br>Sai số tuyệt đối trung bình: $\\overline{\\Delta x}=\\dfrac{|x_1-\\overline{x}|+|x_2-\\overline{x}|+\\cdots+|x_n-\\overline{x}|}{n}$<br>Sai số tuyệt đối: $\\Delta x=\\overline{\\Delta x}+\\Delta x_{dc}$ (bỏ qua sai số dụng cụ thì $\\Delta x=\\overline{\\Delta x}$)<br>Kết quả phép đo: $x=\\overline{x}\\pm\\Delta x$<br>Sai số tương đối: $\\delta x=\\dfrac{\\Delta x}{\\overline{x}}\\cdot100\\%$',
      DauHieuNhanBiet:'Đề cho nhiều lần đo cùng một đại lượng, yêu cầu tính giá trị trung bình và/hoặc sai số.',
      DonVi:'Δx cùng đơn vị với x; δx không có đơn vị (tính theo %).',
      MeoNhanh:'Δx_dc (sai số dụng cụ) thường là nửa độ chia nhỏ nhất của dụng cụ đo — chỉ cộng vào khi đề cho hoặc yêu cầu.'
    }
  }
];
function pedagogyBuiltinFormula(q){for(let e of PED_BUILTIN_FORMULAS){try{if(e.test(q))return e.item}catch(err){}}return null}

/* ===== Trích công thức tổng quát từ LoiGiai (không fetch, không gọi AI) =====
   Nhận diện $...$, $$...$$, \(...\), \[...\] và các dòng có \frac/\sqrt/\Delta/\overline/dấu "=";
   loại bỏ đoạn thay số cụ thể ("...=30+20=50 km/h" -> giữ lại phần ký hiệu trước dấu "="). */
function pedagogyNormalizeMathOps(seg){
  return String(seg||'').replace(/\\pm/g,'±').replace(/\\mp/g,'∓').replace(/\\times/g,'×').replace(/\\cdot/g,'·').replace(/\\approx/g,'≈').replace(/\\sim/g,'~');
}
let PED_UNIT_WORD_RE=/^(km\/h|m\/s\^?2?|cm|mm|km|kg|g|N|J|W|V|A|Hz|Pa|s|h|min|°c|°|%|ω|đơn|vị|và|đến|hoặc|cm2|cm3|m2|m3)$/i;
/* Chấm từng "token" trong đoạn — chỉ coi là "thay số" khi MỌI token đều là số/toán tử/đơn vị đã biết;
   còn sót 1 ký hiệu biến số nào (x, \Delta, v_A...) thì KHÔNG phải đoạn thay số thuần. */
function pedagogyLooksNumericSegment(seg){
  seg=pedagogyNormalizeMathOps(String(seg||'').trim());
  if(!seg)return true;
  let tokens=seg.replace(/[(),.;:]/g,' ').split(/\s+/).filter(Boolean);
  if(!tokens.length)return true;
  if(tokens.length===1){
    // 1 token đứng một mình: KHÔNG tự ý coi 1 chữ cái (a, v, t, s...) là đơn vị — nhiều khả năng đó là ký hiệu biến số.
    let tok=tokens[0];
    return /^[0-9+\-*/±∓×·≈~^]+$/.test(tok)||/^[0-9][0-9+\-*/±∓×·≈~^]*[a-zA-Zà-ỹÀ-Ỹ°%Ω²³\/]{1,8}$/.test(tok);
  }
  for(let tok of tokens){
    if(/^[0-9+\-*/±∓×·≈~^]+$/.test(tok))continue;
    if(PED_UNIT_WORD_RE.test(tok))continue;
    if(/^[0-9][0-9+\-*/±∓×·≈~^]*[a-zA-Zà-ỹÀ-Ỹ°%Ω²³\/]{1,8}$/.test(tok))continue;
    return false;
  }
  return true;
}
/* Bỏ tiền tố dẫn dắt kiểu "Ta có: ", "Suy ra ", "Áp dụng công thức: " trước khi lấy công thức hiển thị,
   để không lộ nguyên câu dẫn dắt lẫn vào công thức. */
function pedagogyStripLeadingLabel(raw){
  let s=String(raw||'');
  s=s.replace(/^[^:=]{0,40}:\s*/,'');
  s=s.replace(/^(công thức|ta có|áp dụng|suy ra|vì)\s+/i,'');
  return s.trim();
}
function pedagogyStripNumericSubstitution(expr){
  let segs=String(expr||'').split('=').map(function(s){return s.trim()}).filter(Boolean);
  if(segs.length<=1)return String(expr||'').trim()||null;
  let kept=segs.filter(function(s){return !pedagogyLooksNumericSegment(s)});
  if(!kept.length)return null;
  return kept.join('=');
}
/* Thư viện nhận diện MẪU công thức đã trích được, để gắn thêm điều kiện/ký hiệu/đơn vị đã biết trước
   (không đoán mò — chỉ áp dụng khi công thức trích ra khớp đúng dạng quen thuộc). */
let PED_KNOWN_FORMULA_PATTERNS=[
  {re:/v_\{?AB\}?=v_A\+v_B/i,meta:{DauHieuNhanBiet:'Hai vật chuyển động ngược chiều nhau.',symbols:['v_{AB}: vận tốc của A đối với B','v_A, v_B: vận tốc của hai vật'],DonVi:'km/h hoặc m/s'}},
  {re:/v_\{?AB\}?=v_A-v_B/i,meta:{DauHieuNhanBiet:'Hai vật chuyển động cùng chiều nhau.',symbols:['v_{AB}: vận tốc của A đối với B','v_A, v_B: vận tốc của hai vật'],DonVi:'km/h hoặc m/s'}}
];
function pedagogyMatchKnownFormulaMeta(formula){
  let norm=String(formula||'').replace(/\s+/g,'');
  for(let p of PED_KNOWN_FORMULA_PATTERNS){try{if(p.re.test(norm))return p.meta}catch(e){}}
  return null;
}
/* Gom TẤT CẢ ứng viên công thức trong LoiGiai, giữ "before" (ngữ cảnh trước đó) để chấm điểm cụm kích hoạt. */
function pedagogyCollectFormulaCandidates(text){
  let out=[];
  let latexBlockRe=/\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\]|\$([^$\n]+?)\$|\\\(([\s\S]*?)\\\)/g;
  let m;
  while((m=latexBlockRe.exec(text))){
    let inner=(m[1]||m[2]||m[3]||m[4]||'').trim();
    if(inner)out.push({raw:inner,before:text.slice(Math.max(0,m.index-60),m.index)});
  }
  let lines=text.split(/\n+/);
  for(let i=0;i<lines.length;i++){
    let l=lines[i].replace(/^[•\-\*\d\.\)]+\s*/,'').trim();
    if(!l)continue;
    if(/\\frac|\\sqrt|\\Delta|\\overline/.test(l)||/[A-Za-z\\][A-Za-z0-9_{}\\]*\s*=/.test(l)){
      out.push({raw:l,before:(i>0?lines[i-1]:'')});
    }
  }
  return out;
}
let PED_FORMULA_TRIGGER_RE=/(công thức|ta có|áp dụng|suy ra|vì)/i;
let PED_FORMULA_ANSWER_RE=/đáp\s*án|dap\s*an|\bchọn\s*(đáp\s*án)?\s*[ABCD]\b/i;
let PED_UNIT_HINT_RE=/km\/h|m\/s\^?2?|m\/s2|\bN\b|\bkg\b|\bcm\b|\bmm\b|°C|Ω|\bV\b|\bW\b|\bJ\b|\bHz\b|%|\bs\b/;
function pedagogyFormulaKnownSymbolsInText(problemText){
  let set=new Set();
  let re=/[A-Za-zΔδ][A-Za-z0-9_]{0,4}/g;let m;
  while((m=re.exec(String(problemText||''))))if(m[0].length<=5)set.add(m[0].toLowerCase());
  return set;
}
function pedagogyFormulaSharedSymbolCount(expr,knownSet){
  let re=/[A-Za-zΔδ][A-Za-z0-9_]{0,4}/g;let m,count=0,seen=new Set();
  while((m=re.exec(expr))){let tok=m[0].toLowerCase();if(seen.has(tok))continue;seen.add(tok);if(knownSet.has(tok))count++}
  return count;
}
function pedagogyFormulaLhs(expr){let i=String(expr||'').indexOf('=');let lhs=i>=0?expr.slice(0,i):expr;return lhs.replace(/\s+/g,'').toLowerCase()}
/* Chấm điểm 1 ứng viên: +5 cụm kích hoạt ("công thức/ta có/áp dụng/suy ra/vì"), +4 ký hiệu trùng đề bài,
   +3 công thức tổng quát hoàn toàn (không đoạn nào thay số), +2 có đơn vị vật lý liên quan;
   -3/-4/-5 cho thay số / kết quả cuối / chỉ chứa đáp án (các trường hợp này bị loại khỏi hiển thị). */
function pedagogyScoreFormulaCandidate(cand,knownSymSet){
  let raw=cand.raw;
  if(PED_FORMULA_ANSWER_RE.test(cand.before+' '+raw)||/^[A-Za-zĐđ\/\.]{0,4}\s*=\s*[ABCD]$/i.test(raw)){
    return {raw:raw,stripped:null,score:-5,cls:'ketqua',lhs:null,len:raw.length};
  }
  let triggered=PED_FORMULA_TRIGGER_RE.test((cand.before||'')+' '+raw.slice(0,30));
  let rawLbl=pedagogyStripLeadingLabel(raw);
  let segs=rawLbl.split('=').map(function(s){return s.trim()}).filter(Boolean);
  let numericFlags=segs.map(pedagogyLooksNumericSegment);
  let allNumeric=numericFlags.length>0&&numericFlags.every(Boolean);
  if((!/=/.test(rawLbl)&&pedagogyLooksNumericSegment(rawLbl))||allNumeric){
    return {raw:raw,stripped:null,score:-5,cls:'ketqua',lhs:null,len:raw.length};
  }
  let stripped=pedagogyStripNumericSubstitution(rawLbl);
  if(!stripped)return {raw:raw,stripped:null,score:-5,cls:'ketqua',lhs:null,len:raw.length};
  let allButFirstNumeric=segs.length>1&&numericFlags.slice(1).every(Boolean);
  if(allButFirstNumeric&&/^[A-Za-z\\][A-Za-z0-9_{}\\ ]*$/.test(segs[0])){
    return {raw:raw,stripped:stripped,score:-4,cls:'ketqua',lhs:pedagogyFormulaLhs(stripped),len:raw.length};
  }
  let hasNumeric=numericFlags.some(Boolean);
  let score=0;
  if(triggered)score+=5;
  if(pedagogyFormulaSharedSymbolCount(stripped,knownSymSet)>0)score+=4;
  if(!hasNumeric)score+=3;else score-=1;
  if(PED_UNIT_HINT_RE.test(raw))score+=2;
  return {raw:raw,stripped:stripped,score:score,cls:'tongquat',lhs:pedagogyFormulaLhs(stripped),len:stripped.length};
}
/* Chọn tối đa 4 công thức "chính/phụ" cần thiết (loại thay số + kết quả cuối), gộp trùng theo vế trái (LHS)
   để tránh cùng 1 công thức bị đếm nhiều lần khi nó chỉ đang được thay số dần trong 1 dòng. */
function pedagogyBuildFormulaChain(text,q){
  let cands=pedagogyCollectFormulaCandidates(text);
  if(!cands.length)return null;
  let knownSet=pedagogyFormulaKnownSymbolsInText([q&&q.CauHoi,q&&q.A,q&&q.B,q&&q.C,q&&q.D].filter(Boolean).join(' '));
  let scored=cands.map(function(c,idx){let s=pedagogyScoreFormulaCandidate(c,knownSet);s._order=idx;return s});
  let general=scored.filter(function(s){return s.cls==='tongquat'&&s.stripped});
  if(!general.length)return null;
  let byLhs={};
  general.forEach(function(g){let key=g.lhs||g.stripped;if(!byLhs[key]||g.score>byLhs[key].score)byLhs[key]=g});
  let uniq=Object.keys(byLhs).map(function(k){return byLhs[k]});
  uniq.sort(function(a,b){if(b.score!==a.score)return b.score-a.score;if(a.len!==b.len)return a.len-b.len;return a._order-b._order});
  let top=uniq.slice(0,4);
  top.sort(function(a,b){return a._order-b._order}); // hiển thị theo thứ tự xuất hiện gốc — đọc như 1 chuỗi suy luận
  return top;
}
function pedagogyExtractFormulaFromLoigiai(loigiai,q){
  let text=String(loigiai||'');
  if(!text.trim())return null;
  let chain=pedagogyBuildFormulaChain(text,q);
  if(!chain||!chain.length)return null;
  if(chain.length===1){
    let best=chain[0].stripped;
    return {formula:best,meta:pedagogyMatchKnownFormulaMeta(best)};
  }
  return {chain:chain.map(function(c){return {formula:c.stripped,meta:pedagogyMatchKnownFormulaMeta(c.stripped)}})};
}
async function getFormulaForCurrentQuestion(qIdx){
  let q=applyResolvedDang(QUESTIONS[qIdx]);
  if(!q)return null;
  let key=dangTheoryKey(q);
  if(PED_FORMULA_CACHE[key]!==undefined)return PED_FORMULA_CACHE[key];
  if(PED_FORMULA_LOADING[key])return undefined;
  PED_FORMULA_LOADING[key]=true;
  let found=null;
  try{
    if(String(q.DangBaiTap||'').trim()){
      try{
        let body={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',DangBaiTap:q.DangBaiTap||''};
        let j=await api('/api/learning/method',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        found=(typeof exactDangTheoryItem==='function')?exactDangTheoryItem(j.items||[],q):null;
      }catch(e){}
    }
    if(!found&&String(q.BaiHoc||'').trim()){
      try{
        let body={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||''};
        let j=await api('/api/learning/theory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        let it=(j.items||[])[0];
        if(it&&String(it.CongThuc||'').trim())found=it;
      }catch(e){}
    }
    if(!found&&typeof canViewSolutionLive==='function'&&canViewSolutionLive()&&String(q.LoiGiai||'').trim()){
      try{
        let ext=pedagogyExtractFormulaFromLoigiai(q.LoiGiai,q);
        if(ext&&Array.isArray(ext.chain)&&ext.chain.length>1){
          found={
            _fromLoigiai:true,
            Chain:ext.chain.map(function(c,i){
              return {
                label:'Công thức '+(i+1),
                CongThucSuDung:c.formula,
                DieuKien:(c.meta&&c.meta.DauHieuNhanBiet)||'',
                KyHieu:(c.meta&&c.meta.symbols)||null,
                DonVi:(c.meta&&c.meta.DonVi)||''
              };
            })
          };
        }else if(ext&&ext.formula){
          found={
            CongThucSuDung:ext.formula,
            DieuKien:(ext.meta&&ext.meta.DauHieuNhanBiet)||'',
            KyHieu:(ext.meta&&ext.meta.symbols)||null,
            DonVi:(ext.meta&&ext.meta.DonVi)||'',
            _fromLoigiai:true
          };
        }
      }catch(e){}
    }
    if(!found)found=pedagogyBuiltinFormula(q);
  }finally{
    delete PED_FORMULA_LOADING[key];
  }
  PED_FORMULA_CACHE[key]=found||null;
  return PED_FORMULA_CACHE[key];
}
function pedagogyFormulaEntryBlockHtml(entry,label){let g=function(k){return String(entry[k]||'').trim()};let parts=[];let formula=g('CongThucSuDung')||g('CongThuc');if(formula)parts.push('<div class="pedFbLine"><b>'+esc(label||'Công thức cần nhớ')+'</b><div class="pedFormulaBlock">'+(typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(formula):esc(formula))+'</div></div>');let dieukien=g('DieuKien')||g('DauHieuNhanBiet');if(dieukien)parts.push('<div class="pedFbLine pedFbSub">Điều kiện áp dụng: '+(typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(dieukien):esc(dieukien))+'</div>');if(Array.isArray(entry.KyHieu)&&entry.KyHieu.length)parts.push('<div class="pedFbLine pedFbSub">Ký hiệu:<br>'+entry.KyHieu.map(function(s){return esc(s)}).join('<br>')+'</div>');let dv=g('DonVi');if(dv)parts.push('<div class="pedFbLine pedFbSub">Đơn vị: '+esc(dv)+'</div>');let luuy=g('MeoNhanh')||g('LuuY')||g('SaiLamThuongGap');if(luuy)parts.push('<div class="pedFbLine pedFbSub">Lưu ý: '+(typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(luuy):esc(luuy))+'</div>');return parts.join('')}
function pedagogyFormulaSectionHtml(entry,canAi,q){if(entry===undefined)return '<div class="muted">Đang tải công thức…</div>';if(!entry){let hasLoigiai=!!(q&&String(q.LoiGiai||'').trim());let canSol=typeof canViewSolutionLive==='function'&&canViewSolutionLive();if(hasLoigiai&&canSol)return '<div class="muted">Chưa trích được công thức tự động cho dạng bài này.</div><button type="button" class="btn2 pedFbActBtn" style="margin-top:6px" onclick="toggleQuestionExplain(event)">📄 Xem lời giải</button>';return '<div class="muted">Chưa có công thức cho dạng bài này.</div>'}if(Array.isArray(entry.Chain)&&entry.Chain.length){let blocks=entry.Chain.map(function(c,i){return pedagogyFormulaEntryBlockHtml(c,c.label||('Công thức '+(i+1)))});return blocks.join('<hr class="pedFormulaChainSep">')}let body=pedagogyFormulaEntryBlockHtml(entry,'Công thức cần nhớ');if(!body)return '<div class="muted">Chưa có công thức lưu sẵn cho dạng bài này.</div>';return body}
function updateResultBox(qIdx){let rb=document.getElementById('resultBox');if(!rb)return;let q=applyResolvedDang(QUESTIONS[qIdx]);if(!q)return;let r=RESULTS[qIdx]||CHECKED[qIdx];let clear=function(){rb.textContent='';rb.removeAttribute('style');rb.classList.remove('dsResultRich');rb.classList.remove('pedResultRich')};if(!r||!(r.ok===true||r.ok===false)){clear();return}if(q.Dang==='Đúng sai'&&SUBMITTED){rb.innerHTML=formatDsCheckResultBox(qIdx,r,q,ANSWERS[qIdx]);rb.classList.add('dsResultRich');rb.classList.remove('pedResultRich');rb.style.color=r.ok?'#166534':'#991b1b';return}if(q.Dang==='Đúng sai'&&EXAM_MODE&&!SUBMITTED){rb.classList.remove('dsResultRich');rb.classList.add('pedResultRich');rb.innerHTML=r.ok?'<span class="pedFeedback pedFeedback-ok"><span class="pedFbHead">✅ Đúng</span></span>':'<span class="pedFeedback pedFeedback-bad"><span class="pedFbHead">❌ Sai</span></span>';rb.style.color=r.ok?'#166534':'#991b1b';return}if(q.Dang==='Đúng sai'&&isQuestionChecked(qIdx)){rb.innerHTML=formatDsCheckResultBox(qIdx,r,q,ANSWERS[qIdx]);rb.classList.add('dsResultRich');rb.classList.remove('pedResultRich');rb.style.color=r.ok?'#166534':'#991b1b';return}rb.classList.remove('dsResultRich');rb.classList.add('pedResultRich');if(r.ok===true){rb.innerHTML='<span class="pedFeedback pedFeedback-ok"><span class="pedFbHead">✅ Đúng</span></span>';rb.style.color='#166534'}else{rb.innerHTML='<span class="pedFeedback pedFeedback-bad"><span class="pedFbHead">❌ Sai</span></span>';rb.style.color='#991b1b'}}
function formatMcqAnswerBadge(text){let raw=String(text||'').trim();let m=raw.toUpperCase().match(/^([ABCD])$/);if(!m){let lm=raw.match(/(?:đáp án|chọn|kết luận|phương án)[^ABCD]*([ABCD])/i);if(lm)m=[null,lm[1].toUpperCase()]}if(m&&m[1])return `<div class="dsAnswerRow"><div class="dsAnswerItem">${dsCircleHtml(m[1])} <b class="dsVerdictDung">đáp án đúng</b></div></div>`;return formatHintDisplay(raw)}
function loigiaiAbcdTagRx(){return /(?:^|\n|[•\-\*]\s*|\(\s*)(?:\*\*)?([ABCD])\s*[\.\):]\s*(?:(Đúng|Sai)\s*[\-—:–]\s*)?/gi}
function dsLoigiaiLooksCanonical(t){t=String(t||'');let tagged=[...t.matchAll(loigiaiAbcdTagRx())];if(tagged.length<2)return false;let pre=t.slice(0,tagged[0].index);let leg=/(?:^|\n|[•●▪▫◦]\s*)(?:ch\s+)?(?:\\textbf\s*\{\s*)?(?:Đúng|Sai)\s*[\.\-—:–]\s*/gi;return [...pre.matchAll(leg)].length<2}
function stripDsLoigiaiLegacyBlocks(t){t=String(t||'').trim();if(!t)return '';let leg=/(?:^|\n|[•●▪▫◦]\s*)(?:ch\s+)?(?:\\textbf\s*\{\s*)?(?:Đúng|Sai)\s*[\.\-—:–]\s*/gi;let ms=[...t.matchAll(leg)];if(ms.length>=2)return t.slice(0,ms[0].index).trim();if(ms.length===1){let head=t.slice(0,ms[0].index).trim();if(head&&!leg.test(head))return head;return ''}return t}
function splitLoigiaiPreamble(text){let t=String(text||'').replace(/\r/g,'').trim();if(!t)return '';let tagged=[...t.matchAll(loigiaiAbcdTagRx())];if(tagged.length>=1){let pre=t.slice(0,tagged[0].index).trim();return dsLoigiaiLooksCanonical(t)?pre:stripDsLoigiaiLegacyBlocks(pre)}let lineTagged=[...t.matchAll(/(?:^|\n)\s*(?:\*\*)?([ABCD])(?!\s*[\.\):])/gim)];if(lineTagged.length>=1)return stripDsLoigiaiLegacyBlocks(t.slice(0,lineTagged[0].index).trim());return stripDsLoigiaiLegacyBlocks(t)}
function formatLoigiaiPreambleHtml(preamble){let p=String(preamble||'').trim();if(!p)return '';return `<div class="loigiaiPreamble" style="margin-bottom:12px;line-height:1.55">${formatHintDisplay(p)}</div>`}
function extractAbcdSolutionChunks(text){let t=String(text||'').replace(/\r/g,'');let tagged=[...t.matchAll(loigiaiAbcdTagRx())];if(tagged.length>=1){let out=[];for(let i=0;i<tagged.length;i++){let start=tagged[i].index+tagged[i][0].length;let end=i+1<tagged.length?tagged[i+1].index:t.length;out.push({letter:tagged[i][1].toUpperCase(),verdict:tagged[i][2]?dsVerdictLabel(tagged[i][2]):'',body:t.slice(start,end).trim().replace(/^[\)\s.,]+|[\(\s.,]+$/g,'')})}return out.slice(0,4)}let lineTagged=[...t.matchAll(/(?:^|\n)\s*(?:\*\*)?([ABCD])(?!\s*[\.\):])(?:\s+(?:(Đúng|Sai)\s*[\-—:–]\s*)?(.+))?$/gim)];if(lineTagged.length>=1){return lineTagged.slice(0,4).map(m=>({letter:m[1].toUpperCase(),verdict:m[2]?dsVerdictLabel(m[2]):'',body:(m[3]||'').trim().replace(/^[\)\s.,]+|[\(\s.,]+$/g,'')}))}t=t.replace(/\(\s*•\s*/g,'\n• ').replace(/\s*•\s*/g,'\n• ');let choiceRx=/(?:^|\n)\s*[•●▪▫◦]\s*(?:ch\s+)?(?:\\textbf\s*\{\s*)?(Đúng|Sai)(?:\s*\})?\s*[\.\-—:–]\s*/gi;let choiceMk=[];let cm;while((cm=choiceRx.exec(t))!==null)choiceMk.push({verdict:cm[1],start:cm.index+cm[0].length,head:cm.index});if(choiceMk.length>=2){return choiceMk.map((mk,i)=>{let end=i+1<choiceMk.length?choiceMk[i+1].head:t.length;return {letter:['A','B','C','D'][i]||String(i+1),verdict:dsVerdictLabel(mk.verdict),body:t.slice(mk.start,end).trim().replace(/^[\)\s.,]+|[\(\s.,]+$/g,'')}}).slice(0,4)}let markers=[];let rx=/(?:^|\n|[•\-\*]\s*)(Đúng|Sai)\.\s*/gi,m;while((m=rx.exec(t))!==null)markers.push({verdict:m[1],start:m.index+m[0].length,head:m.index});if(markers.length>=1){return markers.map((mk,i)=>{let end=i+1<markers.length?markers[i+1].head:t.length;return {letter:['A','B','C','D'][i]||String(i+1),verdict:dsVerdictLabel(mk.verdict),body:t.slice(mk.start,end).trim().replace(/^[\)\s.,]+|[\(\s.,]+$/g,'')}}).slice(0,4)}return []}
function finalizeAbcdSolutionChunks(chunks,q,isDs,skipSheet){if(!q)return chunks||[];let letters=['A','B','C','D'].filter(L=>q[L]);if(!letters.length)return chunks||[];let byL={};(chunks||[]).forEach(c=>{byL[c.letter]=c});let tokens=isDs&&!skipSheet?parseDsAnswerTokens(q.DapAn||''):[];let vMap={};tokens.forEach(t=>vMap[t.letter]=t.verdict);let corrMcq=String(q.DapAn||'').trim().toUpperCase().match(/^([ABCD])$/)?.[1];return letters.map(L=>{if(byL[L]){let c=byL[L];if(isDs&&!skipSheet&&!c.verdict&&vMap[L])return Object.assign({},c,{verdict:vMap[L]});return c}return {letter:L,verdict:isDs&&!skipSheet?(vMap[L]||''):'',body:''}})}
function formatAbcdSolutionList(chunks,q,isDs){q=q||{};if(!isDs&&(q.Dang==='Trắc nghiệm'||(isMcqLetter(q.DapAn)&&hasOptsClient(q)))){let lines=(chunks||[]).map(c=>buildDsSolutionPlainLine(c,true)).filter(Boolean);return formatMcqSolutionRows(lines.join('\n'),q)}chunks=finalizeAbcdSolutionChunks(chunks,q,isDs);if(!chunks.length)return '';let corrMcq=String(q.DapAn||'').trim().toUpperCase().match(/^([ABCD])$/)?.[1];let stacked=needsAbcdStackedLayout(q,chunks);let listCls='dsSolutionList dsSolutionCompact'+(stacked?' dsSolutionRows':(isDs?' dsSolutionDs':' dsSolutionTn'));return `<div class="${listCls}">${chunks.map(c=>{let headVerdict='';if(c.verdict)headVerdict=`<b class="${c.verdict==='Sai'?'dsVerdictSai':'dsVerdictDung'}">${esc(c.verdict)}</b>`;else if(!isDs&&c.letter===corrMcq)headVerdict=`<b class="dsVerdictDung">✓ Đúng</b>`;else if(!isDs&&corrMcq)headVerdict=`<span class="muted">sai</span>`;let stmt='';if(q[c.letter]&&!c.body){let st=renderQuizFieldHtml(stripOptionPrefix(q[c.letter],c.letter));stmt=stacked?`<div class="dsStmtBlock">${st}</div>`:`<span class="dsStmtInline">${st}</span>`}let body=c.body?`<div class="dsSolutionBody">${formatHintDisplay(c.body)}</div>`:'';if(stacked&&stmt)return `<div class="dsSolutionItem"><div class="dsSolutionHead">${dsCircleHtml(c.letter)} ${headVerdict}</div>${stmt}${body}</div>`;return `<div class="dsSolutionItem"><div class="dsSolutionHead">${dsCircleHtml(c.letter)} ${headVerdict}${stmt}</div>${body}</div>`}).join('')}</div>`}
function stripLoigiaiMarkdown(s){return String(s||'').replace(/\*\*/g,'').replace(/^#+\s+/gm,'').trim()}function stripDsBodyLeadingVerdict(body,v){body=String(body||'').trim();if(!body)return '';let m=body.match(/^(?:\*\*)?(Đúng|Sai|Đ|D|S|True|False)\b\s*[\-—:–\.\)]*\s*/i);if(!m)return body;let got=dsVerdictLabel(m[1]);if(v&&got&&got!==v)return body;return body.slice(m[0].length).trim()||body}function buildDsSolutionPlainLine(c,keepBreaks){let v=c.verdict||'';let body=stripLoigiaiMarkdown(c.body||'');if(!keepBreaks)body=body.replace(/\s+/g,' ').trim();else body=body.trim();if(v)body=stripDsBodyLeadingVerdict(body,v);if(!v&&!body)return '';return v?(body?`${c.letter}. ${v} — ${body}`:`${c.letter}. ${v}`):(body?`${c.letter}. — ${body}`:`${c.letter}.`)}function buildDsSolutionCopyText(text,q,forAi){q=q||currentQuestion();let t=String(text||'').trim();if(!t)return '';if(forAi&&dsLoigiaiLooksCanonical(t))return t;let pre=splitLoigiaiPreamble(t);let chunks=extractAbcdSolutionChunks(t);if(forAi){let letters=['A','B','C','D'].filter(L=>q[L]);let byL={};chunks.forEach(c=>{byL[c.letter]=c});chunks=letters.map(L=>byL[L]||{letter:L,verdict:'',body:''});chunks=finalizeAbcdSolutionChunks(chunks,q,true,false)}else chunks=finalizeAbcdSolutionChunks(chunks,q,true,false);let lines=chunks.map(c=>buildDsSolutionPlainLine(c,!!forAi)).filter(Boolean).join('\n');if(pre&&lines)return pre+'\n\n'+lines;return lines||pre}function formatDsSolutionPlainList(text,q,fromAi){q=q||currentQuestion();let t=String(text||'').trim();let pre=splitLoigiaiPreamble(t);let chunks=extractAbcdSolutionChunks(t);chunks=finalizeAbcdSolutionChunks(chunks,q,true,!!fromAi);if(!chunks.length)return pre?formatLoigiaiPreambleHtml(pre):formatHintDisplay(t);let rows=chunks.map(c=>{let v=c.verdict||'';let rawBody=stripLoigiaiMarkdown(c.body||'');if(!v&&!rawBody)return '';let vCls=v==='Sai'?'dsVerdictSai':'dsVerdictDung';let head=v?`<span class="dsPlainHead"><b class="${vCls}">${esc(c.letter)}. ${esc(v)}</b> — </span>`:`<span class="dsPlainHead"><b>${esc(c.letter)}.</b> </span>`;let body=rawBody?`<span class="dsPlainBody">${formatHintDisplay(rawBody)}</span>`:'';return `<div class="dsSolutionPlainRow">${head}${body}</div>`}).filter(Boolean);let list=rows.length?`<div class="dsSolutionPlainList">${rows.join('')}</div>`:'';if(pre&&list)return formatLoigiaiPreambleHtml(pre)+list;if(list)return list;if(pre)return formatLoigiaiPreambleHtml(pre);return formatHintDisplay(t)}function formatDsSolutionRows(text,q,fromAi){let t=String(text||'').trim();q=q||currentQuestion();if(q&&(q.Dang==='Trắc nghiệm'||(isMcqLetter(q.DapAn)&&hasOptsClient(q))))return formatMcqSolutionRows(t,q);let pre=splitLoigiaiPreamble(t);if(q&&q.Dang==='Đúng sai')return formatDsSolutionPlainList(t,q,!!fromAi);if(!t&&isCurrentQuestionDs())return formatDsSolutionPlainList('',q,!!fromAi);let chunks=extractAbcdSolutionChunks(t);let list='';if(chunks.length>=1)list=formatAbcdSolutionList(chunks,q,true);else if(!pre&&q&&['A','B','C','D'].some(L=>q[L]))list=formatAbcdSolutionList(chunks,q,true);if(pre&&list)return formatLoigiaiPreambleHtml(pre)+list;if(list)return list;if(pre)return formatLoigiaiPreambleHtml(pre);return formatHintDisplay(t)}
function loigiaiStripAbcdTail(text){let t=String(text||'').trim();if(!t)return '';let tagged=[...t.matchAll(loigiaiAbcdTagRx())];if(!tagged.length)return t;return t.slice(0,tagged[0].index).trim()}
function mcqCorrectLetter(q){return String((q&&q.DapAn)||'').trim().toUpperCase().match(/^([ABCD])$/)?.[1]||''}
function mcqTnBodyIsTrivial(body){let b=String(body||'').trim();if(!b)return true;b=b.replace(/[\*#]/g,'').trim().toLowerCase();b=b.normalize('NFD').replace(/[\u0300-\u036f]/g,'');return /^(sai|dung|d|a|b|c)$/.test(b)||b.length<12}
function normalizeTnLoigiaiPlain(text,q){text=String(text||'').trim();if(!text)return '';q=q||currentQuestion();let pre=splitLoigiaiPreamble(text);let chunks=extractAbcdSolutionChunks(text);if(chunks.length>=1){let corr=mcqCorrectLetter(q);let hit=corr?chunks.find(c=>c.letter===corr):null;let body=hit&&String(hit.body||'').trim()&&!mcqTnBodyIsTrivial(hit.body)?hit.body:'';if(body)return pre?(pre+'\n\n'+body):body;let stripped=loigiaiStripAbcdTail(text);if(stripped&&stripped!==text)return stripped;return pre||''}return text}
function formatLoigiaiByDang(text,q,dang){text=String(text||'').trim();q=q||currentQuestion();dang=normDangClient(dang||(q&&q.Dang)||'Trắc nghiệm');if(isMcqLetter(q.DapAn)&&hasOptsClient(q))dang='Trắc nghiệm';let rawLg=text;text=stripLoigiaiLayoutMarkers(text);let body='';if(text){if(/\[(?:HINH|IMG|T)(?:-LG)?\]/i.test(text)){let fig=buildHinhAnhSolutionFigHtml(q),figHtml=fig?'<div class="lgSolutionFig">'+fig+'</div>':'',parts=text.split(/\[(?:HINH|IMG|T)(?:-LG)?\]/i),chunks=[];for(let i=0;i<parts.length;i++){let p=parts[i].trim();if(p){let h='';if(dang==='Đúng sai')h=formatDsSolutionRows(p,q,false);else if(dang==='Trắc nghiệm')h=formatMcqSolutionRows(p,q);else h=formatHintDisplay(p);if(h)chunks.push(h)}if(i<parts.length-1&&figHtml)chunks.push(figHtml)}body=chunks.join('')}else{if(dang==='Đúng sai')body=formatDsSolutionRows(text,q,false);else if(dang==='Trắc nghiệm')body=formatMcqSolutionRows(text,q);else body=formatHintDisplay(text)}}return appendSolutionFigureIfNeeded(body,q,rawLg)}
function formatMcqSolutionRows(text,q){q=q||currentQuestion();let raw=String(text||'').trim();if(!raw)return '';let t=normalizeTnLoigiaiPlain(raw,q);if(!t)return '';let pre=splitLoigiaiPreamble(t);if(pre&&t.length>pre.length+1){let rest=t.slice(pre.length).trim();return formatLoigiaiPreambleHtml(pre)+(rest?formatHintDisplay(rest):'')}return formatHintDisplay(t)}
function formatDsHintText(text,isSolution,fromAi){text=String(text||'').trim();if(!text)return '';let q=currentQuestion();return isSolution?formatDsSolutionRows(text,q,fromAi):formatDsAnswerBadges(text)}
function formatTnHintText(text,isSolution){text=String(text||'').trim();if(!text)return '';return isSolution?formatMcqSolutionRows(text,currentQuestion()):formatMcqAnswerBadge(text)}
function applyAuto5050(hide){if(!hide||!hide.length)return;for(let L of hide){let el=document.getElementById('opt_'+L);if(el)el.classList.add('hidden5050')}let b=document.getElementById('btn5050');if(b)b.disabled=true;let bf=document.getElementById('btnFs5050');if(bf)bf.disabled=true;let rb=document.getElementById('resultBox');if(rb){rb.textContent='🎯 Đã loại 2 đáp án sai: '+hide.join(', ');rb.style.color='#1d4ed8'}}
function hintRawText(){let j=HINT_BY_Q[CUR];return j?String(j.hint||''):''}
function quizRestorePayload(){return{made:CURRENT_MADE||'',questions:QUESTIONS||[],level_filter:CURRENT_LEVEL||'',dang_filter:CURRENT_DANG||'',dangbaitap_filter:CURRENT_DANGBAITAP||''}}
function quizDebateQuestionSlim(){let q=currentQuestion()||{};let o={};for(let k of ['ID','CauHoi','A','B','C','D','DapAn','LoiGiai','Dang','Mon','Lop','Chuong','BaiHoc','MucDo','DangBaiTap'])o[k]=q[k]||'';return o}
function quizDebateRequestBody(extra){let lg='';try{lg=currentQuizLoiGiaiText()||''}catch(e){lg=String((currentQuestion()||{}).LoiGiai||'')}let body=Object.assign({sid:SID,index:CUR,answer:ANSWERS[CUR],loigiai:lg,made:CURRENT_MADE||'',question:quizDebateQuestionSlim()},extra||{});quizAttachAiKeys(body);return body}
function optionHasHeavyMath(text){text=String(text||'');return text.length>48||/\$|\\frac|\\sqrt|\\begin|\\\[|\\\(/.test(text)}function mcqOptIsShort(text){text=String(text||'').trim();if(!text)return true;if(/\[IMG\]|<img\b|\\includegraphics|tikz/i.test(text))return false;if(/\n/.test(text))return false;if(text.length>90)return false;let plain=text.replace(/\$\$/g,'').replace(/\$/g,'');plain=plain.replace(/\\[a-zA-Z]+(\{[^}]*\})?/g,'m');plain=plain.replace(/[{}^_\\]/g,'').replace(/\s+/g,' ').trim();return plain.length<=32}function mcqOptsUse2Col(q){if(!q||q.Dang!=='Trắc nghiệm')return false;if(usesImgSplit(q))return false;let n=0;for(let L of ['A','B','C','D']){if(!q[L])continue;n++;if(!mcqOptIsShort(q[L]))return false}return n>=2}
function mcqOptsUseSplitCol1(q){if(!q||q.Dang!=='Trắc nghiệm')return false;if(!usesImgSplit(q))return false;let n=0;for(let L of ['A','B','C','D']){if(!q[L])continue;n++;if(!mcqOptIsShort(q[L]))return false}return n>=2}
function needsAbcdStackedLayout(q,chunks){q=q||{};for(let L of ['A','B','C','D']){if(q[L]&&optionHasHeavyMath(q[L]))return true;let c=(chunks||[]).find(x=>x.letter===L);if(c&&c.body&&optionHasHeavyMath(c.body))return true}return false}
function isQuizVisible(){let q=document.getElementById('quiz');return !!(q&&!q.classList.contains('hide'))}
function ldvlIsAndroidMobile(){try{let mob=window.matchMedia('(max-width:768px)').matches||window.matchMedia('(orientation:landscape) and (max-height:520px)').matches;if(!mob)return false}catch(e){return false}let ua=navigator.userAgent||'';return /Android/i.test(ua)||/SamsungBrowser/i.test(ua)}
function ldvlApplyTouchScrollFix(){let on=ldvlIsAndroidMobile();document.documentElement.classList.toggle('ldvlAndroidScroll',on);document.body.classList.toggle('ldvlAndroidScroll',on)}
function ldvlFixMainScrollContainer(){let body=document.body;if(!body||!body.classList.contains('ldvlDashV324'))return;if(body.classList.contains('fullde-mode')||body.classList.contains('mini-calc-open')||body.classList.contains('theoryEditorOpen'))return;let home=document.getElementById('home');let quiz=document.getElementById('quiz');let homeOn=!!(home&&!home.classList.contains('hide'));let quizOn=!!(quiz&&!quiz.classList.contains('hide'));let wrap=document.querySelector('.ldvlDashWrap');let main=document.querySelector('.ldvlMain');if(wrap){wrap.style.setProperty('min-height','0','important');wrap.style.setProperty('overflow','hidden','important');wrap.style.setProperty('flex','1 1 auto','important')}if(main){main.style.setProperty('min-height','0','important');main.style.setProperty('overflow-y','scroll','important');main.style.setProperty('-webkit-overflow-scrolling','touch','important');main.style.setProperty('touch-action','pan-y','important')}if(homeOn&&!quizOn){body.style.setProperty('overflow','hidden','important');body.style.setProperty('height','100dvh','important');body.style.setProperty('max-height','100dvh','important');document.documentElement.style.setProperty('overflow','hidden','important')}}
function lockQuizPageScroll(){if(!isMobileQuizUI()||!isQuizVisible())return;ldvlApplyTouchScrollFix();if(document.body.classList.contains('ldvlAndroidScroll')){ldvlFixMainScrollContainer();return}document.body.classList.add('quiz-scroll-lock')}
function unlockQuizPageScroll(){document.body.classList.remove('quiz-scroll-lock');document.documentElement.classList.remove('quiz-scroll-lock');document.body.style.top='';document.body.style.removeProperty('overflow');document.body.style.removeProperty('height');document.body.style.removeProperty('position');document.documentElement.style.removeProperty('overflow');document.documentElement.style.removeProperty('height')}
function toggleMobileNavBoard(e){if(e&&e.stopPropagation)e.stopPropagation();if(!isMobileQuizUI())return;MOBILE_NAV_OPEN=!MOBILE_NAV_OPEN;syncMobileQuizChrome()}
function syncMobileQuizChrome(){let mobile=isMobileQuizUI();let inQuiz=isQuizVisible();ldvlApplyTouchScrollFix();document.documentElement.classList.toggle('mobile-quiz-ui',mobile);document.documentElement.classList.toggle('quiz-session-active',inQuiz);document.body.classList.toggle('mobile-nav-open',mobile&&MOBILE_NAV_OPEN);document.body.classList.toggle('quiz-session-active',inQuiz);document.body.classList.toggle('quiz-mobile-score',mobile&&inQuiz&&!!SUBMITTED);let nb=document.getElementById('btnMobileNavToggle');if(nb){nb.textContent=MOBILE_NAV_OPEN?'▴ Đóng bảng':'▾ Bảng câu';nb.setAttribute('aria-expanded',MOBILE_NAV_OPEN?'true':'false')}syncMobileQuizToolbar();syncVipSolutionButtons();syncInfographicButtons();syncHintButtons(USER.can_ai_hint!==false);syncAdminResultBox();if(mobile&&isQuizVisible())lockQuizPageScroll();else unlockQuizPageScroll();if(mobile)ldvlFixMainScrollContainer();}
function isMobileQuizUI(){return window.matchMedia('(max-width:768px)').matches||window.matchMedia('(orientation:landscape) and (max-height:520px)').matches}
function syncMobileQuizToolbar(){let mobile=isMobileQuizUI();document.body.classList.toggle('mobile-quiz-ui',mobile);document.body.classList.toggle('mobile-quiz-tools-open',mobile&&MOBILE_QUIZ_TOOLS_OPEN);let tbtn=document.getElementById('btnQuizToolsToggle');if(tbtn){tbtn.classList.toggle('hide',!(mobile&&!FULLDE_ON));tbtn.textContent=MOBILE_QUIZ_TOOLS_OPEN?'✕':'☰';tbtn.setAttribute('aria-expanded',MOBILE_QUIZ_TOOLS_OPEN?'true':'false')}let fsTbtn=document.getElementById('btnFsToolsToggle');if(fsTbtn){fsTbtn.classList.toggle('hide',!(mobile&&FULLDE_ON));fsTbtn.textContent=MOBILE_QUIZ_TOOLS_OPEN?'✕':'☰';fsTbtn.setAttribute('aria-expanded',MOBILE_QUIZ_TOOLS_OPEN?'true':'false')}}
function toggleQuizTools(e){if(e&&e.stopPropagation)e.stopPropagation();if(!isMobileQuizUI())return;MOBILE_QUIZ_TOOLS_OPEN=!MOBILE_QUIZ_TOOLS_OPEN;syncMobileQuizToolbar()}

function forceMobileHomeScroll(){
  try{
    ldvlApplyTouchScrollFix();
    let mobile=isMobileQuizUI();
    let home=document.getElementById('home');
    let quiz=document.getElementById('quiz');
    let homeVisible=!!(home&&!home.classList.contains('hide'));
    let quizVisible=!!(quiz&&!quiz.classList.contains('hide'));
    if(!mobile||!homeVisible||quizVisible)return;
    document.body.classList.remove(
      'quiz-scroll-lock','quiz-session-active',
      'mobile-nav-open','fullde-mode'
    );
    document.documentElement.classList.remove(
      'quiz-scroll-lock','quiz-session-active'
    );
    document.documentElement.style.setProperty('height','100dvh','important');
    document.documentElement.style.setProperty('max-height','100dvh','important');
    document.documentElement.style.setProperty('overflow','hidden','important');
    document.documentElement.style.setProperty('touch-action','auto','important');
    document.body.style.setProperty('height','100dvh','important');
    document.body.style.setProperty('max-height','100dvh','important');
    document.body.style.setProperty('min-height','100dvh','important');
    document.body.style.setProperty('overflow','hidden','important');
    document.body.style.setProperty('overflow-x','hidden','important');
    document.body.style.setProperty('position','static','important');
    document.body.style.setProperty('touch-action','auto','important');
    let wrap=document.querySelector('.ldvlDashWrap');
    let main=document.querySelector('.ldvlMain');
    [wrap,home].forEach(function(el){
      if(!el)return;
      if(el===wrap){
        el.style.setProperty('flex','1 1 auto','important');
        el.style.setProperty('min-height','0','important');
        el.style.setProperty('overflow','hidden','important');
        return;
      }
      el.style.setProperty('height','auto','important');
      el.style.setProperty('max-height','none','important');
      el.style.setProperty('overflow','visible','important');
      el.style.setProperty('touch-action','auto','important');
    });
    if(main){
      main.style.setProperty('flex','1 1 auto','important');
      main.style.setProperty('min-height','0','important');
      main.style.setProperty('overflow-y','scroll','important');
      main.style.setProperty('-webkit-overflow-scrolling','touch','important');
      main.style.setProperty('touch-action','pan-y','important');
    }
  }catch(e){}
}
window.addEventListener('pageshow',function(){setTimeout(forceMobileHomeScroll,0)});
window.addEventListener('resize',function(){setTimeout(forceMobileHomeScroll,0)});
window.addEventListener('orientationchange',function(){setTimeout(forceMobileHomeScroll,160)});
document.addEventListener('DOMContentLoaded',function(){
  setTimeout(function(){ldvlApplyTouchScrollFix();forceMobileHomeScroll();ldvlFixMainScrollContainer()},0);
  let home=document.getElementById('home');
  let quiz=document.getElementById('quiz');
  if(window.MutationObserver){
    let mo=new MutationObserver(function(){setTimeout(forceMobileHomeScroll,0)});
    if(home)mo.observe(home,{attributes:true,attributeFilter:['class']});
    if(quiz)mo.observe(quiz,{attributes:true,attributeFilter:['class']});
  }
});

function initMobileQuizToolbar(){syncMobileQuizChrome();if(window._mobileQuizToolbarInited)return;window._mobileQuizToolbarInited=true;window.addEventListener('resize',function(){syncMobileQuizChrome();if(!isQuizVisible())return;if(typeof CUR!=='undefined'&&QUESTIONS.length)renderQuestion()});window.addEventListener('orientationchange',function(){setTimeout(function(){syncMobileQuizChrome();if(!isQuizVisible())return;if(typeof CUR!=='undefined'&&QUESTIONS.length)renderQuestion()},120)})}
function fmtTime(sec){sec=Math.max(0,parseInt(sec,10)||0);let h=Math.floor(sec/3600);sec%=3600;let m=Math.floor(sec/60);let s=sec%60;let p=n=>String(n).padStart(2,'0');return h>0?`${p(h)}:${p(m)}:${p(s)}`:`${p(m)}:${p(s)}`}
function syncQuizTimerText(){let v=fmtTime(QUIZ_ELAPSED);let x=document.getElementById('quizTimerText');if(x)x.textContent=v;let fx=document.getElementById('fsQuizTimerText');if(fx)fx.textContent=v;let mx=document.getElementById('mobileQuizTimerText');if(mx)mx.textContent=v}
function startQuizTimer(){stopQuizTimer();QUIZ_ELAPSED=0;syncQuizTimerText();QUIZ_TIMER=setInterval(()=>{QUIZ_ELAPSED++;syncQuizTimerText()},1000)}
function stopQuizTimer(){if(QUIZ_TIMER){clearInterval(QUIZ_TIMER);QUIZ_TIMER=null}}
function sleepMs(ms){return new Promise(res=>setTimeout(res,ms))}
async function api(url,opts={},tries=2){
  let method=String((opts&&opts.method)||'GET').toUpperCase();
  if(!window.LDVL_OFFLINE&&!navigator.onLine){let cached=routeCachedApi(url,opts);if(cached!==null){if(cached.error)throw new Error(cached.error);return cached}}
  let timeoutMs=parseInt(opts.timeoutMs||((method==='GET')?25000:52000),10)||52000;
  for(let attempt=0;attempt<=tries;attempt++){
    let ctrl=new AbortController();
    let timer=setTimeout(()=>ctrl.abort(),timeoutMs);
    try{
      let fetchOpts=Object.assign({},opts||{});delete fetchOpts.timeoutMs;delete fetchOpts.skipLoginRedirect;delete fetchOpts.signal;let r=await fetch(url,{...fetchOpts,signal:opts.signal||ctrl.signal});
      let txt=await r.text();
      let j;
      try{j=txt?JSON.parse(txt):{};}
      catch(e){j={error:'Không đọc được phản hồi từ máy chủ. Có thể Render đang timeout hoặc trả về HTML. Mã HTTP: '+r.status+'. Nội dung đầu: '+txt.slice(0,120)}}
      let retryStatus=[429,500,502,503,504].includes(r.status);
      let retryMsg=/(quota|rate|timeout|temporarily|service unavailable|backend|deadline)/i.test(String((j&&j.error)||''));
      if((retryStatus||retryMsg)&&attempt<tries){await sleepMs(850*(attempt+1));continue}
      if(!r.ok||j.error){if(r.status==401&&!opts.skipLoginRedirect){let next=encodeURIComponent(location.pathname+location.search);location='/login?next='+next}throw new Error(j.error||'Lỗi API')}
      return j;
    }catch(e){
      let canRetry=(e&&e.name==='AbortError')||/Failed to fetch|NetworkError|timeout|aborted/i.test(String(e&&e.message||e));
      if(canRetry&&attempt>=tries&&!window.LDVL_OFFLINE){let cached=routeCachedApi(url,opts);if(cached!==null){if(cached.error)throw new Error(cached.error);return cached}}
      if(canRetry&&attempt<tries){await sleepMs(850*(attempt+1));continue}
      throw new Error((e&&e.name==='AbortError')?'Máy chủ phản hồi quá lâu. Đợi vài giây rồi bấm lưu lại.':(e.message||e));
    }finally{clearTimeout(timer)}
  }
}
function setOptions(id,arr){document.getElementById(id).innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option>${esc(x)}</option>`).join('')}
function lessonNum(s){s=normText(s||'');let m=s.match(/\bbai\s*(\d+)/);if(m)return parseInt(m[1],10);m=s.match(/^(\d+)/);return m?parseInt(m[1],10):9999}
function chapterNum(s){s=normText(s||'');let m=s.match(/\bchuong\s*(viii|vii|vi|iv|iii|ii|v|ix|x|i|\d+)\b/);if(m){let t=m[1];if(/^\d+$/.test(t))return parseInt(t,10);let rom={i:1,ii:2,iii:3,iv:4,v:5,vi:6,vii:7,viii:8,ix:9,x:10};return rom[t]||9999}m=s.match(/^(\d+)[\.\)]/);if(m)return parseInt(m[1],10);return 9999}
function catalogSortKey(x){return [normText(x.Mon||''),normText(x.Lop||''),chapterNum(x.Chuong||''),normText(x.Chuong||''),lessonNum(x.BaiHoc||x.De||''),normText(x.BaiHoc||x.De||''),normText(x.BoDe||'')]}
function compareCatalog(a,b){let ka=catalogSortKey(a),kb=catalogSortKey(b);for(let i=0;i<ka.length;i++){if(ka[i]<kb[i])return -1;if(ka[i]>kb[i])return 1}return 0}
function uniqField(list,field){let seen=new Set(),out=[];for(let x of list||[]){let v=String((x||{})[field]||'').trim();if(!v||seen.has(v))continue;seen.add(v);out.push(v)}if(field==='BaiHoc')return out.sort((a,b)=>lessonNum(a)-lessonNum(b)||normText(a).localeCompare(normText(b),'vi'));if(field==='Chuong')return out.sort((a,b)=>chapterNum(a)-chapterNum(b)||normText(a).localeCompare(normText(b),'vi'));return out.sort((a,b)=>normText(a).localeCompare(normText(b),'vi'))}
function filterBaseCatalog(){let mon=val('fMon')||'';if(!mon)return CATALOG.slice();return CATALOG.filter(x=>x.Mon==mon)}
function filterCatalogUpTo(stopBefore){let list=filterBaseCatalog();let lop=val('fLop');if(lop)list=list.filter(x=>x.Lop==lop);if(stopBefore==='lop')return list;let chuong=val('fChuong');if(chuong)list=list.filter(x=>x.Chuong==chuong);if(stopBefore==='chuong')return list;let bai=val('fBaiHoc');if(bai)list=list.filter(x=>x.BaiHoc==bai);if(stopBefore==='baihoc')return list;let bode=val('fBoDe');if(bode)list=list.filter(x=>x.BoDe==bode);return list}
function setOptionsKeep(id,arr,keep){let el=document.getElementById(id);if(!el)return;keep=String(keep||'');if(keep&&!arr.includes(keep))keep='';el.innerHTML='<option value="">Tất cả</option>'+arr.map(x=>`<option${x===keep?' selected':''}>${esc(x)}</option>`).join('');el.value=keep}
function updateExamStrip(){const el=document.getElementById('examStrip');const msg=document.getElementById('examMsg');const tm=document.getElementById('examTimer');if(!el||!msg)return;msg.textContent='🎉 Chào mừng bạn đến ứng dụng luyện đề của Thầy Minh';if(tm){tm.textContent='';tm.classList.add('hide')}el.classList.remove('hide');el.classList.remove('exam-active')}
function mergeUserAiProfile(src){src=src||{};if(src.ai_profile!==undefined)USER.ai_profile=src.ai_profile;if(src.ai_profile_label!==undefined)USER.ai_profile_label=src.ai_profile_label;if(src.ai_profile_hint!==undefined)USER.ai_profile_hint=src.ai_profile_hint;if(src.ai_profile_action!==undefined)USER.ai_profile_action=src.ai_profile_action;if(src.ai_key_source!==undefined)USER.ai_key_source=src.ai_key_source;if(src.ai_show_key_panel!==undefined)USER.ai_show_key_panel=src.ai_show_key_panel;if(src.ai_nudge_key!==undefined)USER.ai_nudge_key=src.ai_nudge_key;if(src.ai_server_key_count!==undefined)USER.ai_server_key_count=src.ai_server_key_count;if(src.using_user_keys!==undefined)USER.ai_using_user_keys=!!src.using_user_keys;if(src.user_gemini_keys!==undefined)USER.ai_user_gemini_keys=src.user_gemini_keys;if(src.user_anthropic_keys!==undefined)USER.ai_user_anthropic_keys=src.user_anthropic_keys;if(src.has_keys!==undefined)USER.ai_has_keys=!!src.has_keys}
function aiProfileBadgeClass(code){if(!code)return'hide';if(String(code).endsWith('_OWN'))return'aiProfileOwn';if(String(code).endsWith('_POOL'))return'aiProfilePool';if(String(code)==='FREE')return'aiProfileFree';return'aiProfileWarn'}
function userRoleCssClass(u){u=u||USER||{};if(u.is_admin||String(u.role||'').toUpperCase()==='ADMIN')return'roleADMIN';if(u.is_svip||String(u.role||'').toUpperCase()==='S.VIP')return'roleSVIP';if(u.is_vip||String(u.role||'').toUpperCase()==='VIP')return'roleVIP';if(u.is_trial||String(u.role||'').toUpperCase()==='TRIAL')return'roleTRIAL';return'roleFREE'}
function userRoleDisplayLabel(u){u=u||USER||{};if(u.role_label)return String(u.role_label);let r=String(u.role||'').toUpperCase();if(r==='S.VIP')return'SVIP';if(r==='ADMIN')return'ADMIN';if(r==='VIP')return'VIP';if(r==='TRIAL')return'DÙNG THỬ';if(r==='FREE')return'FREE';return r||'Học viên'}
function userInitialLetter(u){let n=String((u&&u.hoten)||'').trim();if(n)return n.charAt(0).toUpperCase();let m=String((u&&u.mahs)||'').trim();return m?m.charAt(0).toUpperCase():'?'}
function userBenefitsList(u){u=u||USER||{};if(Array.isArray(u.benefits)&&u.benefits.length)return u.benefits;if(u.is_admin)return['Xem đáp án & lời giải ngay','Soát đề GPT','Sửa Sheet'];if(u.is_svip)return['Xem ĐA/LG','Nộp bài','Infographic'];if(u.is_vip)return['Xem ĐA/LG','50-50','Nộp bài'];if(u.is_trial)return['Chỉ đề FREE','Không chấm điểm'];return['Làm đề FREE']}
function renderUserAccountCard(u){u=u||USER||{};let card=document.getElementById('userAccountCard');let chip=document.getElementById('topUserChip');let name=String(u.hoten||u.mahs||'').trim();if(!name){if(card)card.classList.add('hide');if(chip)chip.classList.add('hide');return}let roleCls=userRoleCssClass(u);let roleLbl=userRoleDisplayLabel(u);let meta=[];if(u.lop)meta.push('Lớp '+u.lop);if(u.mahs)meta.push('Mã HS: '+u.mahs);let expiry='';if(u.trial_until)expiry='Hết dùng thử: '+u.trial_until;else if(u.account_until)expiry='Hết hạn tài khoản: '+u.account_until;if(card){card.classList.remove('hide');card.className='userAccountCard compactHomeAccount '+roleCls;card.innerHTML='<div class="userAccountHead"><div class="userAccountAvatar">'+esc(userInitialLetter(u))+'</div><div class="userAccountMain"><div class="userAccountName">'+esc(name)+'</div><div class="userAccountMeta">'+esc(meta.join(' · ')||'Đã đăng nhập')+'</div></div><span class="userRoleBadge '+roleCls+'">'+esc(roleLbl)+'</span></div>'+(expiry?'<div class="userAccountExpiry">⏳ '+esc(expiry)+'</div>':'')}if(chip){chip.classList.remove('hide');chip.innerHTML='<span class="topRolePill '+roleCls+'">'+esc(roleLbl)+'</span><span>'+esc(name)+'</span>'}}
function isAiKeyPanelOpen(){try{return localStorage.getItem('LDVL_AI_KEY_PANEL_OPEN_V257')==='1'}catch(e){return false}}
function setAiKeyPanelOpen(open){try{localStorage.setItem('LDVL_AI_KEY_PANEL_OPEN_V257',open?'1':'0')}catch(e){}syncAiKeyCompactPanel()}
function toggleAiKeyPanelCompact(){setAiKeyPanelOpen(!isAiKeyPanelOpen())}
function syncAiKeyCompactPanel(){let panel=document.getElementById('aiKeyPanel');if(!panel)return;let open=isAiKeyPanelOpen();panel.classList.toggle('aiKeyCollapsed',!open);panel.classList.toggle('collapsedBlock',!open);let btn=document.getElementById('aiKeyMiniToggle');if(btn){btn.textContent=open?'▼':'▶';btn.setAttribute('aria-expanded',open?'true':'false');let lbl=open?'Thu gọn':'Mở rộng';btn.setAttribute('aria-label',lbl);btn.setAttribute('title',lbl)}let mini=document.getElementById('aiKeyMiniStatus');if(mini){let ta=document.getElementById('myApiKeys');let hasTyped=!!(ta&&ta.value&&ta.value.trim());let hasSaved=!!(window.USER&&USER.ai_has_keys);mini.textContent=(hasTyped||hasSaved)?'✅ Đã có key':'⚠️ Chưa có key';mini.classList.toggle('hide',open)}if(typeof ldvlToolsTabSync==='function')ldvlToolsTabSync()}
function renderUserAiProfile(u){u=u||USER||{};renderUserAccountCard(u);let badge=document.getElementById('aiProfileBadge');if(badge){if(u.ai_profile&&u.ai_profile!=='FREE'&&u.can_ai_hint!==false){badge.textContent=u.ai_profile_label||'';badge.className='aiProfileBadge '+aiProfileBadgeClass(u.ai_profile)}else badge.className='aiProfileBadge hide'}let banner=document.getElementById('aiProfileBanner');if(banner){if(u.can_ai_hint&&u.ai_profile_hint){let cls='aiProfileBanner aiProfileBannerCompact ';if(u.ai_profile&&String(u.ai_profile).endsWith('_NO_KEY'))cls+='aiProfileBannerErr';else if(u.ai_nudge_key)cls+='aiProfileBannerNudge';else cls+='aiProfileBannerOk';banner.className=cls;banner.title=String(u.ai_profile_hint||'');banner.innerHTML=`<b>${esc(u.ai_profile_label||'AI')}</b><div class="aiProfileBannerTxt">${esc(u.ai_profile_hint||'')}</div>`+(u.ai_nudge_key?'<button type="button" class="btn2 aiProfileBannerBtn" onclick="scrollToAiKeyPanel()">Nạp key</button>':'')}else banner.className='aiProfileBanner hide'}let detail=document.getElementById('aiProfileDetail');if(detail){if(u.can_ai_hint&&u.ai_profile_hint){let dcls='aiProfileBanner aiProfileBannerCompact ';dcls+=u.ai_profile&&String(u.ai_profile).endsWith('_OWN')?'aiProfileBannerOk':(u.ai_nudge_key?'aiProfileBannerNudge':'aiProfileBannerOk');detail.className=dcls;detail.style.margin='6px 0 8px';detail.title=String(u.ai_profile_hint||'');detail.innerHTML=`<b>${esc(u.ai_profile_label||'')}</b><div class="aiProfileBannerTxt">${esc(u.ai_profile_hint||'')}</div>`}else detail.className='aiProfileBanner aiProfileBannerOk hide'}let panel=document.getElementById('aiKeyPanel');if(panel){if(u.ai_show_key_panel===false||u.can_save_own_ai_key===false)panel.classList.add('hide');else if(u.can_ai_hint)panel.classList.remove('hide');syncAiKeyCompactPanel();let antRow=document.getElementById('anthropicKeyRow');if(antRow&&u.can_ai_hint&&u.can_save_own_ai_key!==false){antRow.classList.remove('hide');let antEl=document.getElementById('myAnthropicKey');if(antEl&&!antEl.value){let saved=typeof _loadAnthropicKey==='function'?_loadAnthropicKey():'';if(saved)antEl.value=saved}}}}
function scrollToAiKeyPanel(){let p=document.getElementById('aiKeyPanel');if(!p)return;p.classList.remove('hide');setAiKeyPanelOpen(true);p.scrollIntoView({behavior:'smooth',block:'start'})}
async function loadAiKeyPanel(){
  let panel=document.getElementById('aiKeyPanel');
  let st=document.getElementById('aiKeyStatus');
  if(!panel)return;
  let canOwn=!!(USER.can_save_own_ai_key||USER.can_ai_hint||USER.is_admin);
  let antRow=document.getElementById('anthropicKeyRow');
  let antEl=document.getElementById('myAnthropicKey');
  if(canOwn){
    if(antRow)antRow.classList.remove('hide');
    if(antEl&&!antEl.value){
      let saved=_loadAnthropicKey();
      if(saved)antEl.value=saved;
    }
  }
  if(USER.is_admin){
    let provRow=document.getElementById('adminAiProviderRow');
    if(provRow)provRow.classList.remove('hide');
    panel.classList.remove('hide');
  }
  if(USER.can_save_own_ai_key===false&&!USER.is_admin){panel.classList.add('hide');renderUserAiProfile(USER);return}
  try{
    let j=await api('/api/ai-config');
    mergeUserAiProfile(j);
    if(j.ai_show_key_panel!==false||USER.is_admin)panel.classList.remove('hide');
    else panel.classList.add('hide');
    renderUserAiProfile(USER);
    let parts=[];
    if(j.using_user_keys)parts.push(`Đã lưu ${j.user_gemini_keys||0} key Gemini`);
    else parts.push('Chưa lưu key Gemini');
    if(j.has_server_keys)parts.push(`Server có ${j.ai_server_key_count||0} key Gemini dự phòng`);
    if(j.has_keys)parts.push('✅ Có thể dùng Gợi ý AI');
    else parts.push('⚠️ Chưa có key Gemini');
    let savedAnt=_loadAnthropicKey();
    if((j.user_anthropic_keys||0)>0||savedAnt)parts.push('✨ Claude key đã nạp');
    else parts.push('⚠️ Chưa có Claude key');
    if(st)st.textContent=parts.join(' · ');
    syncAdminAiProviderChrome();
  }catch(e){if(st)st.textContent='Không tải trạng thái key: '+e.message}
}
function _loadAnthropicKey(){try{return localStorage.getItem('LDVL_ANTHROPIC_KEY')||''}catch(e){return ''}}
function _saveAnthropicKey(k){try{if(k)localStorage.setItem('LDVL_ANTHROPIC_KEY',k);else localStorage.removeItem('LDVL_ANTHROPIC_KEY')}catch(e){}}
function _loadGeminiKey(){try{return localStorage.getItem('LDVL_GEMINI_KEY')||''}catch(e){return ''}}
function _saveGeminiKey(k){try{if(k)localStorage.setItem('LDVL_GEMINI_KEY',k);else localStorage.removeItem('LDVL_GEMINI_KEY')}catch(e){}}
function _pickGeminiKeyRaw(raw){raw=String(raw||'').trim();if(!raw)return'';let parts=raw.split(/[\s,;\n]+/).map(x=>String(x||'').trim()).filter(Boolean);let hit=parts.find(x=>/^AIza/i.test(x)||/^AQ\./.test(x));return hit||''}
function hasOwnGeminiKey(){if(_pickGeminiKeyRaw((document.getElementById('quizDebateGeminiKey')||{}).value||''))return true;if(_pickGeminiKeyRaw((document.getElementById('myApiKeys')||{}).value||''))return true;if(_pickGeminiKeyRaw(_loadGeminiKey()))return true;return !!(USER&&(parseInt(USER.ai_user_gemini_keys,10)||0)>0)}
function quizAttachGeminiKey(body){body=body||{};let el=document.getElementById('myApiKeys');let qk=document.getElementById('quizDebateGeminiKey');let g=_pickGeminiKeyRaw((qk&&qk.value)||'')||_pickGeminiKeyRaw((el&&el.value)||'')||_pickGeminiKeyRaw(_loadGeminiKey());if(g)body.gemini_key=g;return body}
function hasOwnClaudeKey(){let el=document.getElementById('myAnthropicKey');let v=String((el&&el.value)||(typeof _loadAnthropicKey==='function'?_loadAnthropicKey():'')||'').trim();if(v.indexOf('sk-ant-')===0)return true;return !!(USER&&(parseInt(USER.ai_user_anthropic_keys,10)||0)>0)}
function showClaudeDebate(){return !!isAdminViewer()}
function quizAttachAnthropicKey(body){body=body||{};return body}
function quizAttachAiKeys(body){quizAttachAnthropicKey(body);quizAttachGeminiKey(body);return body}
function quizDebateKeyBoxHtml(){return '<div id="quizDebateKeyBox" class="quizDebateKeyBox hide"><b>Nhập Gemini key ngay tại đây</b><p>Lấy key miễn phí: <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a> → Create API key → copy → dán ô dưới.</p><input id="quizDebateGeminiKey" autocomplete="off" placeholder="AIza... hoặc AQ..."><div class="quizDebateKeyRow"><button type="button" class="btnGreen btnSmall" onclick="saveQuizDebateGeminiKey()">💾 Lưu key rồi phản biện</button><button type="button" class="btn2 btnSmall" onclick="openGeminiKeyPage()">↗ Mở trang lấy key</button><button type="button" class="btn2 btnSmall" onclick="continueDebateWithClassKey()">Dùng key lớp</button></div></div>'}
let DEBATE_ALLOW_POOL=false,DEBATE_RESUME='';
function openGeminiKeyPage(){try{window.open('https://aistudio.google.com/apikey','_blank','noopener')}catch(e){location.href='https://aistudio.google.com/apikey'}}
function ensureQuizDebateKeyBox(){let panel=document.getElementById('quizDebatePanel');if(!panel)return;if(document.getElementById('quizDebateKeyBox'))return;let head=panel.querySelector('.quizDebateHead');if(head)head.insertAdjacentHTML('afterend',quizDebateKeyBoxHtml());else panel.insertAdjacentHTML('afterbegin',quizDebateKeyBoxHtml())}
function showQuizDebateKeyBox(){VIP_Q_SHOW_EXP[CUR]=true;let sol=document.getElementById('solution');if(sol)sol.classList.remove('hide');let panel=ensureQuizDebatePanel();ensureQuizDebateKeyBox();if(panel){panel.classList.remove('hide');try{panel.scrollIntoView({behavior:'smooth',block:'start'})}catch(e){}}let box=document.getElementById('quizDebateKeyBox');if(box)box.classList.remove('hide');let inp=document.getElementById('quizDebateGeminiKey');if(inp&&!String(inp.value||'').trim()){let saved=_loadGeminiKey();if(saved)inp.value=saved}if(inp){if(!inp._debateEnterBound){inp._debateEnterBound=true;inp.addEventListener('keydown',function(ev){if(ev.key==='Enter'){ev.preventDefault();saveQuizDebateGeminiKey()}})}try{inp.focus()}catch(e){}}}
function hideQuizDebateKeyBox(){let box=document.getElementById('quizDebateKeyBox');if(box)box.classList.add('hide')}
function needQuizDebateGeminiKey(resume){if(hasOwnGeminiKey()||DEBATE_ALLOW_POOL)return false;DEBATE_RESUME=resume||'debate';showQuizDebateKeyBox();return true}
async function saveQuizDebateGeminiKey(){let inp=document.getElementById('quizDebateGeminiKey');let g=_pickGeminiKeyRaw(inp&&inp.value||'');if(!g){alert('Dán Gemini key bắt đầu bằng AIza... hoặc AQ...');openGeminiKeyPage();if(inp)try{inp.focus()}catch(e){}return}_saveGeminiKey(g);let home=document.getElementById('myApiKeys');if(home&&!String(home.value||'').trim())home.value=g;try{await api('/api/ai-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_keys:g,provider:'GEMINI'})});if(USER)USER.ai_user_gemini_keys=Math.max(1,parseInt(USER.ai_user_gemini_keys,10)||0)}catch(e){}hideQuizDebateKeyBox();let resume=DEBATE_RESUME;DEBATE_RESUME='';if(resume==='followup')sendQuizDebateFollowup();else toggleQuizDebate()}
function continueDebateWithClassKey(){DEBATE_ALLOW_POOL=true;hideQuizDebateKeyBox();let resume=DEBATE_RESUME;DEBATE_RESUME='';if(resume==='followup')sendQuizDebateFollowup();else toggleQuizDebate()}
async function testClaudeKey(){
  let el=document.getElementById('myAnthropicKey');
  let key=el?String(el.value||'').trim():_loadAnthropicKey();
  if(!key){alert('Dán sk-ant-... vào ô Anthropic key rồi bấm Test.');return}
  let btn=document.querySelector('[onclick="testClaudeKey()"]');
  let old=btn?btn.textContent:'';
  if(btn){btn.disabled=true;btn.textContent='⏳ Đang test…'}
  try{
    let j=await api('/api/admin/claude-fix-latex',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:'$x^2$',anthropic_key:key})
    });
    if(j&&!j.error)alert('✅ Claude key hợp lệ! Sẵn sàng dùng nút ✨ Claude.');
    else alert('❌ Claude key lỗi: '+(j&&j.error||'Không kết nối được'));
  }catch(e){alert('❌ Lỗi: '+(e.message||e));}
  finally{if(btn){btn.disabled=false;btn.textContent=old}}
}
async function saveMyAiKey(){
  if(!USER.can_ai_hint){alert('Key AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}
  let raw=(document.getElementById('myApiKeys').value||'').trim();
  let antEl=document.getElementById('myAnthropicKey');
  let antKey=antEl?String(antEl.value||'').trim():'';
  if(antKey){
    if(!antKey.startsWith('sk-ant-')){alert('Claude key phải bắt đầu bằng sk-ant-\nLấy tại: https://console.anthropic.com/settings/keys');return}
    _saveAnthropicKey(antKey);
  }
  if(raw){
    let g=_pickGeminiKeyRaw(raw);
    if(g)_saveGeminiKey(g);
  }
  if(!raw&&!antKey){alert('Dán ít nhất một key:\n• Gemini: AIza... hoặc AQ... (AI Studio)\n• Claude: sk-ant-... (console.anthropic.com)');return}
  try{
    let payload={};
    if(raw){payload.api_keys=raw;payload.provider='GEMINI'}
    if(antKey)payload.anthropic_keys=antKey;
    let j=await api('/api/ai-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    let bits=[];
    if(raw)bits.push(j.message||'Đã lưu key Gemini.');
    if(antKey)bits.push('Đã lưu Claude key (sk-ant-…).');
    alert(bits.join('\n')||'Đã lưu key AI.');
  }catch(e){alert('Không lưu được key: '+e.message);return}
  await loadAiKeyPanel();
}
async function clearMyAiKey(){
  if(!confirm('Xóa key AI đã lưu?\n• Gemini: xóa trên server\n• Claude: xóa trên server và trình duyệt'))return;
  _saveAnthropicKey('');
  _saveGeminiKey('');
  let antEl=document.getElementById('myAnthropicKey');
  if(antEl)antEl.value='';
  try{
    let j=await api('/api/ai-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clear_keys:true})});
    document.getElementById('myApiKeys').value='';
    alert(j.message||'Đã xóa key.');
    await loadAiKeyPanel();
  }catch(e){alert(e.message)}
}
function formatAiKeyCheckAlert(j){j=j||{};let msg=(j.ok?'✅ ':'❌ ')+(j.message||'');if(j.details&&j.details.length){let extra=[];for(let d of j.details){let lab=d.label||(d.key_hint?('Key #'+d.index+' ('+d.key_hint+')'):('Key #'+d.index));if(d.source&&!String(lab).includes(d.source))lab+=' — '+d.source;extra.push((d.ok?'✅':'❌')+' '+lab+': '+(d.message||''))}if(extra.length&&!String(msg).includes('Key #'))msg+='\n\n'+extra.join('\n')}return msg}
let TEST_KEY_BUSY=false;function apiNetworkErrorMsg(e){let m=String((e&&e.message)||e||'');if(/Failed to fetch|NetworkError|Load failed|ERR_CONNECTION/i.test(m))return 'Không kết nối được máy chủ. Kiểm tra app Python đang chạy (TRINH_CHAY_APP / port 8000) rồi Ctrl+F5.';return m||'Lỗi không xác định'}async function testMyAiKey(){if(!USER.can_ai_hint){alert('Key AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}let raw=document.getElementById('myApiKeys').value.trim();let body={provider:'GEMINI'};if(raw)body.api_keys=raw;try{let j=await api('/api/ai-key-check',{method:'POST',headers:{'Content-Type':'application/json'},timeoutMs:90000,body:JSON.stringify(body)});let ver=j.version?`\n\nPhiên bản server: ${j.version}`:'';alert(formatAiKeyCheckAlert(j)+ver)}catch(e){alert(apiNetworkErrorMsg(e))}}

/* ==========================================================================
 * [JS-ADMIN-CHROME] Nút ADMIN khi đang làm bài (#quiz)
 * --------------------------------------------------------------------------
 * HTML:
 *   btnQuizEdit      — ✏️ Sửa câu (quizToolsRow, luôn thấy — sửa tại đây trước)
 *   quizAdminTools   — btnQuizEdit, duyệt, btnAdd, btnLatexImport, btnInfographic, btnQuizAdminAiInternet
 *   quizIdJumpWrap   — nhảy theo ID câu trong đề
 *   btnFsEdit/btnFsAdd — Full màn hình (fullde-mode)
 * CSS: body.user-is-admin + [CSS-ADMIN-QUIZ] (~dòng 9709)
 * Gọi: renderQuestion() cuối hàm, enterQuizSession(), toggleQuizFullscreen()
 * ========================================================================== */
const ADMIN_QUIZ_HEAD_TOOL_IDS=['btnAdd','btnLatexImport','btnInfographic'];
function toggleQuizElHide(id,hide){let el=document.getElementById(id);if(el)el.classList.toggle('hide',!!hide)}
function syncUserQuizChrome(){
  document.body.classList.toggle('user-is-admin',isAdminViewer());
  let can5050=!!USER.can_5050;
  for(let id of ['btn5050','btnFs5050']){let b=document.getElementById(id);if(b)b.classList.toggle('hide',!can5050)}
  let canAi=USER.can_ai_hint!==false;
  let adm=isAdminViewer();
  let canSim=!!USER.can_quiz_similar&&!(EXAM_MODE&&!SUBMITTED);
  for(let id of ['btnHint','btnFsHint','btnSimilar','btnFsSimilar']){
    let b=document.getElementById(id);if(!b)continue;
    let mob=isMobileQuizUI();
    if(id.indexOf('Similar')>=0)b.classList.toggle('hide',!canSim);
    else if(id.indexOf('Hint')>=0)b.classList.toggle('hide',!canAi||(adm&&!mob));
    else b.classList.toggle('hide',!canAi);
  }
  let retry=document.getElementById('btnRetry');
  if(retry)retry.classList.toggle('hide',adm);
}
function updateAdminChrome(){
  let adm=isAdminViewer();
  document.body.classList.toggle('user-is-admin',adm);
  let inQuiz=!!(document.getElementById('quiz')&&!document.getElementById('quiz').classList.contains('hide'));
  let showInQuiz=adm&&inQuiz;
  // Thanh trên cùng (home vs quiz)
  toggleQuizElHide('quizTopBar',!inQuiz);
  toggleQuizElHide('adminBar',!adm);
  toggleQuizElHide('adminComposePanel',!adm);
  toggleQuizElHide('adminAiGeneratePanel',!adm);
  // Full màn hình
  toggleQuizElHide('btnFsSync',!(showInQuiz&&FULLDE_ON));
  toggleQuizElHide('btnFsEdit',!showInQuiz);
  toggleQuizElHide('btnFsAdd',!showInQuiz);
  // Trong đề: Sửa câu chính + cụm nút metadata
  toggleQuizElHide('quizAdminTools',!showInQuiz);
  toggleQuizElHide('quizToolbarRowAdmin',!showInQuiz);
  toggleQuizElHide('quizIdJumpWrap',!showInQuiz);
  toggleQuizElHide('btnQuizEdit',!showInQuiz);
  ADMIN_QUIZ_HEAD_TOOL_IDS.forEach(id=>toggleQuizElHide(id,!showInQuiz));
  syncAdminReviewModeUI();
  syncAdminAiProviderChrome();
  ensureAdminAiProviderUi();
  syncInfographicButtons();
  syncAdminLearningBoard();
  syncUserQuizChrome();
  if(typeof syncAdminLoiGiaiEditBtn==='function')syncAdminLoiGiaiEditBtn();
  
  if(adm){ensureQuizAdminAiInternetButton();syncAdminComposeChrome();bindAdminNavContextMenu();try{initAdminAiGenerator()}catch(e){}}
  if(typeof ldvlApplyAdminHomeLayout==='function')ldvlApplyAdminHomeLayout();
  if(typeof ldvlPdfAdminPanelSync==='function')ldvlPdfAdminPanelSync();
  try{if(typeof ldvlStudentProgressSyncNav==='function')ldvlStudentProgressSyncNav()}catch(e){}
}
function closeAdminMoreMenu(){let m=document.getElementById('adminMoreMenu');if(m)m.classList.add('hide')}
function toggleAdminMoreMenu(ev){if(ev)ev.stopPropagation();let m=document.getElementById('adminMoreMenu');if(!m)return;let willOpen=m.classList.contains('hide');closeAdminMoreMenu();if(willOpen)m.classList.remove('hide')}
if(!window.__ADMIN_MORE_MENU_BOUND){window.__ADMIN_MORE_MENU_BOUND=1;document.addEventListener('click',closeAdminMoreMenu)}
function reindexQuizMaps(removedIdx){function shift(obj){let out={};for(let k in obj){let i=parseInt(k,10);if(isNaN(i))continue;if(i<removedIdx)out[i]=obj[k];else if(i>removedIdx)out[i-1]=obj[k]}return out}ANSWERS=shift(ANSWERS);RESULTS=shift(RESULTS);CHECKED=shift(CHECKED);LOCKED_Q=shift(LOCKED_Q);HINT_BY_Q=shift(HINT_BY_Q);SIMILAR_BY_Q=shift(SIMILAR_BY_Q);AI_LG_BY_Q=shift(AI_LG_BY_Q);ADMIN_LG_DRAFT_BY_Q=shift(ADMIN_LG_DRAFT_BY_Q)}
function insertQuizMaps(insertIdx){function shiftInsert(obj){let out={};for(let k in obj){let i=parseInt(k,10);if(isNaN(i))continue;if(i<insertIdx)out[i]=obj[k];else out[i+1]=obj[k]}return out}ANSWERS=shiftInsert(ANSWERS);RESULTS=shiftInsert(RESULTS);CHECKED=shiftInsert(CHECKED);LOCKED_Q=shiftInsert(LOCKED_Q);HINT_BY_Q=shiftInsert(HINT_BY_Q);SIMILAR_BY_Q=shiftInsert(SIMILAR_BY_Q);AI_LG_BY_Q=shiftInsert(AI_LG_BY_Q);ADMIN_LG_DRAFT_BY_Q=shiftInsert(ADMIN_LG_DRAFT_BY_Q)}
function remapQuizMapsByPerm(perm){function remap(obj){let out={};for(let ni=0;ni<perm.length;ni++){let oi=perm[ni];if(obj[oi]!==undefined)out[ni]=obj[oi];else if(obj[String(oi)]!==undefined)out[ni]=obj[String(oi)]}return out}ANSWERS=remap(ANSWERS);RESULTS=remap(RESULTS);CHECKED=remap(CHECKED);LOCKED_Q=remap(LOCKED_Q);HINT_BY_Q=remap(HINT_BY_Q);SIMILAR_BY_Q=remap(SIMILAR_BY_Q);VIP_Q_SHOW_ANS=remap(VIP_Q_SHOW_ANS);VIP_Q_SHOW_EXP=remap(VIP_Q_SHOW_EXP);AI_LG_BY_Q=remap(AI_LG_BY_Q);ADMIN_LG_DRAFT_BY_Q=remap(ADMIN_LG_DRAFT_BY_Q);ADMIN_HINT_SAVED=remap(ADMIN_HINT_SAVED)}
function regroupQuestionsByDang(anchorRow){if(!GROUP_BY_DANG||!QUESTIONS.length)return CUR;let tagged=QUESTIONS.map((q,i)=>({q:applyResolvedDang(Object.assign({},q)),oi:i}));let buckets={};for(let d of DANG_GROUP_ORDER_CLIENT)buckets[d]=[];let other=[];for(let t of tagged){let d=t.q.Dang||'Trắc nghiệm';if(buckets[d])buckets[d].push(t);else other.push(t)}let merged=[];for(let d of DANG_GROUP_ORDER_CLIENT)merged=merged.concat(buckets[d]);merged=merged.concat(other);let perm=merged.map(t=>t.oi);QUESTIONS=merged.map(t=>QUESTIONS[t.oi]);remapQuizMapsByPerm(perm);if(anchorRow){let ni=QUESTIONS.findIndex(q=>q._row===anchorRow);if(ni>=0)return ni}let ni=perm.indexOf(CUR);return ni>=0?ni:0}
function catalogFingerprint(cat){
  try{
    return (cat||[]).map(function(x){
      let fc=x&&x.FilterCounts||{};
      let dbt=fc.dangbaitap||{};
      let det=fc.dbt_detail||{};
      let dbtPart=Object.keys(dbt).sort().map(function(k){return k+':'+(dbt[k]||0)}).join(',');
      let mini=Object.keys(det).sort().map(function(k){let d=(det[k]&&det[k].dang)||{};return k+':'+(d['Trắc nghiệm']||0)+','+(d['Đúng sai']||0)+','+(d['Trả lời ngắn']||0)+','+(d['Tự luận']||0)}).join('/');
      return [x.MaDe||'',x.SoCau||0,dbtPart,mini].join('|');
    }).join(';');
  }catch(e){return String((cat||[]).length)}
}
function ldvlCatalogScrollSnapshot(){
  let main=document.querySelector('.ldvlMain')||document.scrollingElement||document.documentElement;
  let rows={};
  document.querySelectorAll('.bookDbtRow[id]').forEach(function(el){rows[el.id]=el.scrollTop||0});
  return {main:main?main.scrollTop:0,rows:rows};
}
function ldvlCatalogScrollRestore(sc){
  if(!sc)return;
  try{
    let main=document.querySelector('.ldvlMain')||document.scrollingElement||document.documentElement;
    if(main&&sc.main)main.scrollTop=sc.main;
    let rows=sc.rows||{};
    Object.keys(rows).forEach(function(id){let el=document.getElementById(id);if(el)el.scrollTop=rows[id]||0});
  }catch(e){}
}
async function refreshCatalogFromMeta(opts){opts=opts||{};try{let m=await api('/api/meta',{timeoutMs:60000},3);if(m.loading)return false;META=META||{};Object.assign(META,m);if(m.user){USER=m.user;renderUserAiProfile(USER)}let next=m.catalog||[];let fp=catalogFingerprint(next);let same=fp===window.__LDVL_CATALOG_FP;CATALOG=next;window.__LDVL_CATALOG_FP=fp;try{mergeStudentProgressFromLocal()}catch(e){}ldvlPdfSyncFromMeta();if(typeof ldvlYtSyncFromMeta==='function')ldvlYtSyncFromMeta();if(typeof ldvlMhSyncFromMeta==='function')ldvlMhSyncFromMeta();if(typeof ldvlStudentPdfRender==='function')ldvlStudentPdfRender();if(typeof ldvlStudentYtRender==='function')ldvlStudentYtRender();if(typeof ldvlStudentMhRender==='function')ldvlStudentMhRender();if(USER&&USER.is_admin&&typeof ldvlPdfMaybeMigrateLocal==='function'&&!window.__LDVL_PDF_MIGRATE_QUEUED){window.__LDVL_PDF_MIGRATE_QUEUED=1;setTimeout(function(){ldvlPdfMaybeMigrateLocal()},800)}let info=document.getElementById('info');if(info)info.textContent=`${m.count_questions} câu hỏi | ${m.count_catalog} đề/thẻ đề | Nạp: ${m.loaded_at}`;let homeEl=document.getElementById('home');if(homeEl&&!homeEl.classList.contains('hide')){if(!same||opts.force){let sc=ldvlCatalogScrollSnapshot();refreshFilterOptions();renderCatalog();ldvlCatalogScrollRestore(sc)}if(!opts.quiet){initRpPracticePanel();initAdminComposePanel();initAdminAiGenerator()}}if(typeof ldvlRefreshAdminDashboard==='function')ldvlRefreshAdminDashboard();showAdminDuplicateSheetNotice();return true}catch(e){return false}}
if(!window.__LDVL_GITHUB_CATALOG_POLL){window.__LDVL_GITHUB_CATALOG_POLL=1;window.__LDVL_GITHUB_CATALOG_AT=0;setInterval(function(){if(!(META&&META.question_source==='GITHUB'))return;let home=document.getElementById('home');if(home&&home.classList.contains('hide'))return;let empty=!(CATALOG&&CATALOG.length);let now=Date.now();if(!empty&&now-(window.__LDVL_GITHUB_CATALOG_AT||0)<90000)return;window.__LDVL_GITHUB_CATALOG_AT=now;refreshCatalogFromMeta({quiet:true});},8000);}
let INIT_POLL_COUNT=0;
const INIT_POLL_MAX=60;
let INIT_CONNECT_FAILS=0;
const INIT_CONNECT_MAX=15;
function resetHomeFilterPlaceholders(loading){
  try{
    let mon=document.getElementById('fMon');
    if(mon){
      if(loading)mon.innerHTML='<option value="">⏳ Đang nạp Sheet…</option>';
      else mon.innerHTML='<option value="">Tất cả</option>';
    }
  }catch(e){}
}
async function init(){
  ensureChapterDbtClickBindings();
  INIT_POLL_COUNT++;
  updateExamStrip();
  let info=document.getElementById('info');
  let cat=document.getElementById('catalog');
  let cnt=document.getElementById('countCat');
  if(!(CATALOG&&CATALOG.length)){
    if(info)info.textContent='Đang nạp đề (GitHub / ngan-hang)…';
    if(cat&&!cat.innerHTML.trim())cat.innerHTML='<div class="muted">Đang tải mục lục đề...</div>';
    resetHomeFilterPlaceholders(true);
  }
  try{
    // V265: /api/meta là dữ liệu chính. Render Free vừa thức dậy có thể >30s — tăng timeout + retry.
    META=await api('/api/meta',{timeoutMs:60000},4);
    INIT_CONNECT_FAILS=0;
  }catch(e){
    INIT_CONNECT_FAILS++;
    let retryable=/AbortError|phản hồi quá lâu|Failed to fetch|NetworkError|timeout|502|503|504/i.test(String(e&&e.message||e));
    if(retryable&&INIT_CONNECT_FAILS<INIT_CONNECT_MAX){
      let waitSec=Math.min(4+INIT_CONNECT_FAILS,12);
      if(info)info.textContent='Đang kết nối server… thử lại sau '+waitSec+'s ('+INIT_CONNECT_FAILS+'/'+INIT_CONNECT_MAX+')';
      if(cat)cat.innerHTML=`<div class="card loadCard"><h3>⏳ Đang kết nối máy chủ</h3><p><b>Render Free vừa «thức dậy» có thể chờ 30–90 giây.</b></p><p class="muted">${esc(e.message||e)}</p><p class="muted">Tự thử lại sau ${waitSec}s — không cần bấm liên tục.</p></div>`;
      resetHomeFilterPlaceholders(true);
      setTimeout(init,waitSec*1000);
      return;
    }
    if(info)info.textContent='Chưa nạp được dữ liệu';
    resetHomeFilterPlaceholders(false);
    if(cat)cat.innerHTML='<div class="card loadWarn"><h3>Không nạp được Google Sheet</h3><p>'+esc(e.message||e)+'</p><p class="muted">Bấm nút bên dưới để thử lại. Nếu Render mới thức dậy, đợi 10–60 giây rồi thử lại.</p><button class="btn" onclick="INIT_POLL_COUNT=0;INIT_CONNECT_FAILS=0;init()">Tải lại dữ liệu</button></div>';
    if(cnt)cnt.textContent='';
    return;
  }
  USER=META.user||{};
  renderUserAiProfile(USER);
  try{mergeStudentProgressFromLocal()}catch(e){}
  try{initAdminReviewMode()}catch(e){console.error('initAdminReviewMode',e)}
  try{initAdminChosenAiProvider()}catch(e){console.error('initAdminChosenAiProvider',e)}
  updateAdminChrome();
  if(META.loading && !((META.catalog||[]).length)){
    let waited=INIT_POLL_COUNT*3;
    let errHint=META.load_error?(' · '+META.load_error):'';
    if(info)info.textContent='Đang nạp đề… '+waited+'s'+errHint;
    resetHomeFilterPlaceholders(true);
    if(cat)cat.innerHTML=`<div class="card loadCard"><h3>⏳ Hệ thống đang khởi động</h3><p><b>Vui lòng chờ, không cần bấm lại nhiều lần.</b></p><p>${esc(META.loading_message||'Đang nạp mục lục đề…')}</p><div class="loadWarn"><b>Lưu ý:</b> Render Free ngủ sau ~15 phút không ai vào. Lần mở đầu tiên chỉ chờ máy thức dậy (khoảng <b>30–90 giây</b>), không nạp hết ngân hàng câu hỏi.</div>${META.load_error?'<p class="loadErr"><b>Lỗi:</b> '+esc(META.load_error)+'</p>':''}<p class="muted">Đã chờ ${waited}s — tự thử lại sau 3 giây.</p></div>`;
    if(cnt)cnt.textContent='';
    if(INIT_POLL_COUNT>=INIT_POLL_MAX){
      if(info)info.textContent='Không nạp được Sheet sau '+waited+'s';
      if(cat)cat.innerHTML='<div class="card loadWarn"><h3>Không nạp được Google Sheet</h3><p>'+esc(META.load_error||'Server không phản hồi kịp hoặc thiếu cấu hình Google trên Render.')+'</p><p class="muted">Kiểm tra Environment: <b>GOOGLE_SHEET_ID</b>, <b>GOOGLE_CREDENTIALS_JSON</b>. Render Free vừa ngủ có thể cần chờ 1–2 phút.</p><button class="btn" onclick="INIT_POLL_COUNT=0;INIT_CONNECT_FAILS=0;init()">Thử lại</button></div>';
      resetHomeFilterPlaceholders(false);
      return;
    }
    setTimeout(init,3000);
    return;
  }
  INIT_POLL_COUNT=0;
  INIT_CONNECT_FAILS=0;
  CATALOG=META.catalog||[];
  if(info)info.textContent=`${META.count_questions} câu hỏi | ${META.count_catalog} đề/thẻ đề | Nạp: ${META.loaded_at}`;
  try{refreshFilterOptions();renderCatalog();}catch(e){console.error('renderCatalog',e);if(cat)cat.innerHTML='<div class="card loadErr"><b>Lỗi hiển thị mục lục:</b> '+esc(e.message||e)+'</div>'}
  try{initRpPracticePanel()}catch(e){console.error('initRpPracticePanel',e)}
  try{initAdminComposePanel();initAdminAiGenerator()}catch(e){console.error('initAdminComposePanel',e)}
  showAdminDuplicateSheetNotice();
  if(USER&&USER.is_admin){
    LDVL_ADMIN_STUDENT_MODE=true;
    if(typeof ldvlApplyAdminHomeLayout==='function')ldvlApplyAdminHomeLayout();
  }
  handleShareDeepLink();
  handleQidDeepLink();
  // API cấu hình AI chạy nền, không được chặn giao diện chính.
  loadAiKeyPanel().catch(function(e){let st=document.getElementById('aiKeyStatus');if(st)st.textContent='Không tải trạng thái key: '+(e&&e.message?e.message:e)});
  if(typeof ldvlQuickNavSyncVisibility==='function')ldvlQuickNavSyncVisibility();
  try{if(typeof ldvlStudentProgressSyncNav==='function')ldvlStudentProgressSyncNav()}catch(e){}
  if(typeof window.ldvlApplyHomeTab==='function')window.ldvlApplyHomeTab(localStorage.getItem('LDVL_HOME_TAB')||'catalog');
}
function dangCountLookup(fc,dang){if(!fc||!fc.dang)return 0;let nd=normDangClient(dang);if(fc.dang[nd]!=null)return fc.dang[nd];let n=0;for(let k in fc.dang)if(normDangClient(k)===nd)n+=fc.dang[k]||0;return n}
function comboCountLookup(fc,lv,dang){if(!fc||!fc.combo)return 0;lv=(lv||'').trim().toUpperCase();let nd=normDangClient(dang);let k1=lv+'|'+nd,k2=lv+'|'+dang;if(fc.combo[k1]!=null)return fc.combo[k1];if(fc.combo[k2]!=null)return fc.combo[k2];let n=0;for(let k in fc.combo){let p=k.split('|');if(p[0]===lv&&normDangClient(p[1]||'')===nd)n+=fc.combo[k]||0}return n}
function filterMatchCount(x,lv,dang){let fc=x&&x.FilterCounts;if(!fc)return null;lv=(lv||'').trim().toUpperCase();dang=(dang||'').trim();if(lv&&dang)return comboCountLookup(fc,lv,dang);if(dang)return dangCountLookup(fc,dang);if(lv)return fc.level[lv]||0;return null}
async function syncData(){if(!confirm('Đồng bộ lại dữ liệu từ Google Sheet?\n\n• Chuẩn hóa Lop/Môn/Chương/Bài học từ DANH_MUC_BAI_HOC → Cau_Hoi\n• Cài dropdown trên Cau_Hoi tham chiếu DANH_MUC_BAI_HOC'))return;let j=await api('/api/sync',{method:'POST'});alert(j.message||'Đã bắt đầu đồng bộ.');await init();if(USER.is_admin){try{let lj=await api('/api/admin/sync-lesson-catalog',{method:'POST',timeoutMs:120000});let msg=[];if(lj.message)msg.push(lj.message);if(lj.dropdowns&&lj.dropdowns.message)msg.push(lj.dropdowns.message);if(lj.dropdown_error)msg.push('⚠ Dropdown: '+lj.dropdown_error);if(msg.length)alert(msg.join('\n\n'));if((lj.updated||0)>0||(lj.cells||0)>0)await refreshCatalogFromMeta()}catch(e){console.warn('sync lesson catalog',e)}}if(USER.is_admin&&META&&META.duplicate_report)alertDuplicateSheetReport(META.duplicate_report)}
async function syncGithubTex(){if(!confirm('Tải file .tex từ GitHub (pythonminh/luyen-de-vat-ly → ngan-hang) rồi nạp vào app?\n\nFile local cùng đường dẫn sẽ bị ghi đè. Không ghi vào Google Sheet.'))return;let st=document.getElementById('ldvlGithubTexStatus');if(st)st.textContent='⏳ Đang tải .tex từ GitHub…';try{let j=await api('/api/github-tex/sync',{method:'POST',timeoutMs:180000});if(st)st.textContent=j.message||('Đã nạp '+(j.count_questions||0)+' câu từ GitHub.');alert(j.message||'Đã đồng bộ GitHub .tex.');await init();if(typeof refreshCatalogFromMeta==='function')await refreshCatalogFromMeta()}catch(e){let msg=e.message||e;if(st)st.textContent='⚠ '+msg;alert('Đồng bộ GitHub thất bại: '+msg)}}
async function dedupeSheetDuplicates(made){
  // Chỉ ADMIN — server /api/question/dedupe cũng chặn 403 nếu không phải ADMIN.
  if(!USER||!USER.is_admin){alert('Chức năng Xóa trùng chỉ dành cho ADMIN.');return}
  // Xóa trùng Sheet theo lô nhỏ; made='' = cả Sheet, made=CURRENT_MADE = chỉ đề đang mở.
  made=String(made||'').trim();
  try{
    const btn=document.getElementById(made?'btnQuizDedupe':'dedupeBtn')||document.getElementById('dedupeBtn')||document.getElementById('btnQuizDedupe');
    if(btn){btn.disabled=true;btn.textContent='⏳ Đang kiểm tra trùng...'}
    let preview=await api('/api/question/dedupe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:true,made:made})});
    let n=parseInt(preview.would_delete||((preview.plan||{}).delete_count),10)||0;
    if(n<=0){
      alert((preview.message||'Không có dòng trùng trên Sheet.')+'\n\nĐã kiểm theo nội dung (bỏ qua khác ID/MaDe). Chỉ còn câu khác đề/đáp án/A–D hoặc khác bài học thì không xóa.');
      return;
    }
    let lines=((preview.plan||{}).samples||[]).slice(0,10);
    let msg='Phát hiện '+n+' dòng TRÙNG trên tab Cau_Hoi.\n\nQuy tắc: cùng nội dung (dù khác ID) → giữ bản đã duyệt/có lời giải, xóa bản sao.\nNút này KHÔNG dùng AI, chỉ xóa dòng trên Google Sheet.\n\n'+(lines.length?('Ví dụ:\n'+lines.join('\n')+'\n\n'):'')+'Tiếp tục xóa theo từng lô 40 dòng để tránh treo/quota?';
    if(!confirm(msg))return;
    let totalDeleted=0;
    let round=0;
    while(true){
      round++;
      if(btn){btn.disabled=true;btn.textContent='🧹 Xóa trùng '+totalDeleted+'/'+n}
      let j=await api('/api/question/dedupe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:false,max_delete:40,made:made})});
      let del=parseInt(j.deleted||j.batch_deleted||0,10)||0;
      totalDeleted+=del;
      await refreshCatalogFromMeta();
      let remain=0;
      try{
        let again=await api('/api/question/dedupe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:true,made:made})});
        remain=parseInt(again.would_delete||((again.plan||{}).delete_count),10)||0;
      }catch(e){remain=parseInt(j.remaining_before_refresh||0,10)||0;}
      if(del<=0||remain<=0)break;
      if(round>=30){
        alert('Đã xóa '+totalDeleted+' dòng. Còn khoảng '+remain+' dòng, bấm 🧹 Xóa trùng Sheet lần nữa để chạy tiếp.');
        break;
      }
      await new Promise(r=>setTimeout(r,900));
    }
    alert('✅ Đã xóa trùng xong: '+totalDeleted+' dòng.\n\nMục lục đã tự cập nhật.');
    await refreshCatalogFromMeta();
  }catch(e){
    let m=e.message||String(e||'');
    if(/429|quota|write requests|rate/i.test(m)) alert('Google Sheet đang giới hạn ghi (429/quota).\n\nĐợi khoảng 1 phút rồi bấm lại 🧹 Xóa trùng Sheet.\nChức năng này không dùng AI.');
    else alert('Không xóa trùng được: '+m+'\n\nMở Console nếu cần xem lỗi JS/API.');
  }finally{
    const btn=document.getElementById('dedupeBtn');
    if(btn){btn.disabled=false;btn.textContent='🧹 Xóa trùng Sheet'}
    const qb=document.getElementById('btnQuizDedupe');
    if(qb){qb.disabled=false;qb.textContent='🧹 Xóa trùng đề'}
  }
}
async function dedupeCurrentQuizDuplicates(){
  if(!USER||!USER.is_admin){alert('Chức năng Xóa trùng đề chỉ dành cho ADMIN.');return}
  if(!CURRENT_MADE){alert('Chưa mở đề — hãy vào một bài rồi bấm «Xóa trùng đề».');return}
  await dedupeSheetDuplicates(CURRENT_MADE);
  // Làm mới phiên đang mở
  try{
    if(SID&&CURRENT_MADE){
      let lv=CURRENT_LEVEL||'',dg=CURRENT_DANG||'';
      await startQuiz(CURRENT_MADE,false,false,lv,dg,GROUP_BY_DANG,CURRENT_DANGBAITAP||'');
    }
  }catch(e){console.warn('reload after dedupe',e)}
}
async function dedupeHinhAnhImages(){
  try{
    const btn=document.getElementById('dedupeImgBtn');
    if(btn){btn.disabled=true;btn.textContent='⏳ Đang quét ảnh...'}
    let preview=await api('/api/admin/dedupe-hinhanh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:true}),timeoutMs:120000});
    let n=parseInt(preview.total_row_updates,10)||0;
    if(n<=0){
      alert((preview.message||'Không có ảnh trùng nội dung cần gộp.')+'\n\nChỉ gộp ảnh GIỐNG HỆT (cùng file ảnh). Ảnh «gần giống» nhưng khác pixel sẽ không gộp tự động.');
      return;
    }
    let lines=(preview.samples||[]).slice(0,8);
    let msg='Phát hiện '+preview.group_count+' nhóm ảnh trùng — sẽ cập nhật '+n+' dòng cột T.\n\n'
      +'Giữ 1 link Drive chuẩn (file_id) — link cũ trỏ về ảnh giống hệt sẽ đổi sang link chuẩn.\n'
      +'Đổi tên file trên Drive KHÔNG làm mất link (chỉ đổi tên hiển thị).\n\n'
      +(lines.length?('Ví dụ:\n'+lines.join('\n')+'\n\n'):'')
      +'Tiếp tục gộp và cập nhật Sheet?';
    if(!confirm(msg))return;
    let rename=confirm('Đổi tên file ảnh chuẩn trên Drive thành img_<hash>.png?\n\nOK = đổi tên · Hủy = chỉ cập nhật cột T');
    if(btn)btn.textContent='⏳ Đang gộp...';
    let j=await api('/api/admin/dedupe-hinhanh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:false,rename}),timeoutMs:120000});
    alert('✅ '+(j.message||'Đã gộp ảnh trùng.')+'\n\nSau khi gộp, có thể xóa file ảnh thừa trên Drive (file_id trong báo cáo) — chỉ xóa khi chắc không còn dòng Sheet nào trỏ tới.');
    await refreshCatalogFromMeta();
  }catch(e){
    alert('Không gộp ảnh được: '+(e.message||e));
  }finally{
    const btn=document.getElementById('dedupeImgBtn');
    if(btn){btn.disabled=false;btn.textContent='🖼 Gộp ảnh trùng'}
  }
}

function alertDuplicateSheetReport(dr){if(!dr||!USER.is_admin)return;let extra=parseInt(dr.extra_duplicate_rows,10)||0;if(extra<=0)return;let lines=(dr.samples||[]).slice(0,6);alert('⚠ Phát hiện câu TRÙNG trên Google Sheet (Cau_Hoi):\n\n≈ '+extra+' dòng thừa (thường do bấm Thêm câu 2 lần hoặc copy/dán).\n\n'+(lines.length?('Ví dụ:\n'+lines.join('\n')+'\n\n'):'')+'Bấm nút 🧹 Xóa trùng Sheet trên thanh ADMIN để tự xóa (giữ 1 bản / câu).')}
function showAdminDuplicateSheetNotice(){if(!USER.is_admin||!META||!META.duplicate_report)return;let dr=META.duplicate_report;let extra=parseInt(dr.extra_duplicate_rows,10)||0;if(extra<=0)return;let info=document.getElementById('info');if(info&&!String(info.textContent||'').includes('dòng trùng')){info.textContent+=` | ⚠ ${extra} dòng trùng Sheet`;if(dr.samples&&dr.samples.length)info.title=dr.samples.join('\n')}}
async function testServerAiKey(){if(TEST_KEY_BUSY){alert('Đang test key… vui lòng đợi.');return}TEST_KEY_BUSY=true;let info=document.getElementById('info');let oldInfo=info?info.textContent:'';if(info)info.textContent='🧪 Đang test key AI…';try{let parts=[],ver='',opts={method:'POST',headers:{'Content-Type':'application/json'},timeoutMs:90000};if(USER.is_admin){let j=await api('/api/ai-key-check-admin',Object.assign({},opts,{body:JSON.stringify({})}));if(j.version)ver=`\n\nPhiên bản server: ${j.version}`;if(j.openai)parts.push('— OPENAI (ADMIN) —\n'+formatAiKeyCheckAlert(j.openai));if(j.gemini)parts.push('— GEMINI —\n'+formatAiKeyCheckAlert(j.gemini));if(!parts.length)throw new Error('Server không trả kết quả test key.');}else{let jG=await api('/api/ai-key-check',Object.assign({},opts,{body:JSON.stringify({provider:'GEMINI'})}));if(jG.version)ver=`\n\nPhiên bản server: ${jG.version}`;parts.push('— GEMINI —\n'+formatAiKeyCheckAlert(jG));}alert(parts.join('\n\n')+ver)}catch(e){alert(apiNetworkErrorMsg(e))}finally{TEST_KEY_BUSY=false;if(info&&oldInfo)info.textContent=oldInfo}}
async function checkAiConnectivity(){if(!USER||!USER.can_ai_hint){alert('Kiểm tra kết nối AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}if(TEST_KEY_BUSY){alert('Đang kiểm tra… vui lòng đợi.');return}TEST_KEY_BUSY=true;let box=document.getElementById('aiKeyStatus');if(box)box.textContent='🧪 Đang kiểm tra kết nối AI…';try{let opts={method:'POST',headers:{'Content-Type':'application/json'},timeoutMs:90000};let results=[];if(USER.is_admin){let j=await api('/api/ai-key-check-admin',Object.assign({},opts,{body:JSON.stringify({})}));if(j.gemini)results.push({label:'Gemini',ok:!!j.gemini.ok,detail:formatAiKeyCheckAlert(j.gemini)});if(j.openai)results.push({label:'GPT',ok:!!j.openai.ok,detail:formatAiKeyCheckAlert(j.openai)});let antEl=document.getElementById('myAnthropicKey');let antKey=(antEl&&antEl.value.trim())||(typeof _loadAnthropicKey==='function'?_loadAnthropicKey():'');if(antKey){try{let jc=await api('/api/admin/claude-fix-latex',Object.assign({},opts,{body:JSON.stringify({text:'$x^2$',anthropic_key:antKey})}));results.push({label:'Claude',ok:!(jc&&jc.error),detail:(jc&&jc.error)?('❌ '+jc.error):'✅ Key hợp lệ.'})}catch(e){results.push({label:'Claude',ok:false,detail:'❌ '+(e.message||e)})}}}else{let jG=await api('/api/ai-key-check',Object.assign({},opts,{body:JSON.stringify({provider:'GEMINI'})}));results.push({label:'Gemini',ok:!!jG.ok,detail:formatAiKeyCheckAlert(jG)});let antEl=document.getElementById('myAnthropicKey');let antKey=(antEl&&antEl.value.trim())||(typeof _loadAnthropicKey==='function'?_loadAnthropicKey():'');if(antKey){try{let jc=await api('/api/ai-key-check',Object.assign({},opts,{body:JSON.stringify({provider:'ANTHROPIC',anthropic_keys:antKey})}));results.push({label:'Claude',ok:!!jc.ok,detail:formatAiKeyCheckAlert(jc)})}catch(e){results.push({label:'Claude',ok:false,detail:'❌ '+(e.message||e)})}}}renderAiConnCheckResult(results)}catch(e){if(box)box.textContent='❌ '+apiNetworkErrorMsg(e)}finally{TEST_KEY_BUSY=false}}
function renderAiConnCheckResult(results){let box=document.getElementById('aiKeyStatus');if(!box)return;if(!results||!results.length){box.textContent='Chưa có nhà cung cấp AI nào để kiểm tra.';return}box.innerHTML=results.map(function(r){return '<div>'+(r.ok?'✅':'❌')+' <b>'+esc(r.label)+'</b>: '+esc(r.detail||'')+'</div>'}).join('')}
function openAiKeyPanelAndCheck(){let panel=document.getElementById('aiKeyPanel');if(panel&&typeof ldvlToolsTabIsOpen==='function'&&!ldvlToolsTabIsOpen('aiKeyPanel'))ldvlToolsTab('aiKeyPanel');if(panel&&panel.scrollIntoView)panel.scrollIntoView({behavior:'smooth',block:'start'});checkAiConnectivity()}
function catalogDbtCounts(item){
  item=item||{};
  let fc=(item.FilterCounts||{}).dangbaitap||{};
  let pairs;
  if(fc&&typeof fc==='object'&&!Array.isArray(fc)&&Object.keys(fc).length){
    let mp={};
    Object.entries(fc).forEach(([k,v])=>{
      let name=oneLineText(k);
      if(!name||name===DBT_UNCLASSIFIED)return;
      mp[name]=(mp[name]||0)+(parseInt(v,10)||0);
    });
    pairs=Object.entries(mp);
  }else{
    let mp={};
    v246UniqTextFromEntries([item],'DangBaiTap',99).forEach(d=>{
      let name=oneLineText(d);
      if(name)mp[name]=mp[name]||0;
    });
    pairs=Object.entries(mp);
  }
  return sortDbtPairs(pairs,item.MaDe||'',item);
}
function getDbtOrderList(made,item){
  item=item||(CATALOG.find(x=>String(x.MaDe||'')===String(made||''))||{});
  let mo=(META&&META.dbt_orders)||{};
  if(made&&mo[made]&&mo[made].length)return mo[made].slice();
  let ord=item.DbtOrder||item.dbt_order;
  if(Array.isArray(ord)&&ord.length)return ord.slice();
  return [];
}
function getLessonDbtOrderList(entries){
  for(let x of entries||[]){
    let ord=getDbtOrderList(x.MaDe,x);
    if(ord.length)return ord;
  }
  return [];
}
function sortDbtPairs(pairs,made,item){
  pairs=(pairs||[]).filter(x=>x&&x[0]);
  let ord=getDbtOrderList(made,item);
  if(!ord.length)return pairs.slice().sort((a,b)=>(b[1]-a[1])||String(a[0]).localeCompare(String(b[0]),'vi'));
  let mp={};
  pairs.forEach(([k,v])=>{mp[normText(k)]=[k,v]});
  let out=[],seen=new Set();
  for(let name of ord){
    let kn=normText(name);
    if(mp[kn]&&!seen.has(kn)){out.push(mp[kn]);seen.add(kn)}
  }
  for(let pr of pairs){let kn=normText(pr[0]);if(!seen.has(kn)){out.push(pr);seen.add(kn)}}
  return out;
}
function patchCatalogDbtOrderLocal(made,order){
  made=String(made||'').trim();if(!made||!Array.isArray(order))return null;
  let scope=null;
  for(let x of CATALOG||[]){
    if(String(x.MaDe||'')===made){x.DbtOrder=order.slice();x.DangBaiTap=order.join(', ');scope=scope||x}
  }
  if(!META)META={};
  if(!META.dbt_orders)META.dbt_orders={};
  META.dbt_orders[made]=order.slice();
  return scope;
}
function catalogUnclassifiedCount(item){item=item||{};let fc=(item.FilterCounts||{}).dangbaitap||{};let keys=fc&&typeof fc==='object'?Object.keys(fc):[];if(!keys.length)return 0;return parseInt(fc[DBT_UNCLASSIFIED],10)||0}
function v246MergeDbtCounts(entries){let mp={};let uncls=0;for(let x of entries||[]){let fc=(x.FilterCounts||{}).dangbaitap||{};if(fc&&typeof fc==='object'&&Object.keys(fc).length)uncls+=parseInt(fc[DBT_UNCLASSIFIED],10)||0;for(let [k,v] of catalogDbtCounts(x)){mp[k]=(mp[k]||0)+(parseInt(v,10)||0)}}let primary=entries[0]||{};let lessonOrd=getLessonDbtOrderList(entries);let sortItem=lessonOrd.length?Object.assign({},primary,{DbtOrder:lessonOrd}):primary;return {pairs:sortDbtPairs(Object.entries(mp).filter(x=>x[0]),primary.MaDe||'',sortItem),unclassified:uncls}}
function catalogLessonMadeForPractice(entries){entries=entries||[];let ids=entries.map(x=>String(x.MaDe||x.GroupKey||'').trim()).filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i);if(!ids.length)return '';return ids.length===1?ids[0]:ids.join('|')}
function getStartModalDangBaiTap(){let el=document.querySelector('input[name="startDbtPick"]:checked');return el?String(el.value||''):''}
function renderStartDangBaiTapPicker(made,preselect){
  let box=document.getElementById('startDangBaiTapBox');let list=document.getElementById('startDangBaiTapList');if(!box||!list)return;
  let item=CATALOG.find(x=>x.MaDe===made)||{};
  let dbts=catalogDbtCounts(item);
  let uncls=catalogUnclassifiedCount(item);
  let total=parseInt(item.SoCau,10)||dbts.reduce((a,x)=>a+(x[1]||0),0)+uncls;
  preselect=String(preselect||val('fDangBaiTap')||'').trim();
  if(isDbtUnclassifiedFilter(preselect))preselect=DBT_UNCLASSIFIED;
  if(!dbts.length&&!uncls){box.classList.add('hide');list.innerHTML='';return}
  box.classList.remove('hide');
  let hint=document.querySelector('#startDangBaiTapBox .muted');
  if(hint)hint.innerHTML='Làm một dạng cụ thể, <b>chưa phân loại</b> (AI gán nhanh), hoặc <b>tất cả</b> câu trong chuyên đề.';
  let html='';
  let allOn=!preselect?' checked':'';
  html+=`<label class="startDbtOpt"><input type="radio" name="startDbtPick" value=""${allOn}> <span><b>Tất cả dạng</b> — ${total} câu trong chuyên đề</span></label>`;
  if(uncls>0){
    let on=preselect===DBT_UNCLASSIFIED?' checked':'';
    let adminHint=USER.is_admin?' <span class="muted">· ADMIN: vào đề → 🏷️ Gợi ý Dạng BT</span>':'';
    html+=`<label class="startDbtOpt startDbtUncls"><input type="radio" name="startDbtPick" value="${escAttr(DBT_UNCLASSIFIED)}"${on}> <span><b>❓ ${esc(DBT_UNCLASSIFIED_LABEL)}</b> — ${uncls} câu${adminHint}</span></label>`;
  }
  for(let [d,n] of dbts){let cnt=n||'';let dName=oneLineText(d);let on=preselect&&normText(preselect)===normText(dName)?' checked':'';let upd=catalogDbtUpdated(item,d);html+=`<label class="startDbtOpt"><input type="radio" name="startDbtPick" value="${escAttr(dName)}"${on}> <span class="startDbtBody"><b class="startDbtName">${esc(dName)}</b><span class="startDbtMeta">${cnt?('<span>'+cnt+' câu</span>'):''}${upd?('<span class="startDbtUpdated" title="Cập nhật dạng">'+esc(upd)+'</span>'):''}</span></span></label>`}
  list.innerHTML=html;
  let mbar=document.getElementById('startDbtMergeBar');
  if(mbar)mbar.classList.toggle('hide',!(USER.is_admin&&dbts.length>=1));

  try{
    let box=document.getElementById('startDangBaiTapBox');
    let empty=document.getElementById('startDbtEmptyHint');
    let pane=document.getElementById('startPaneDbt');
    if(empty&&pane&&!pane.classList.contains('hide')){
      empty.classList.toggle('hide',!(box&&box.classList.contains('hide')));
    }
  }catch(e){}
}

function setStartModalTab(tab){
  tab=(tab===2)?2:1;
  let p1=document.getElementById('startPaneDbt'),p2=document.getElementById('startPaneOpts');
  let b1=document.getElementById('startTabDbtBtn'),b2=document.getElementById('startTabOptsBtn');
  if(p1)p1.classList.toggle('hide',tab!==1);
  if(p2)p2.classList.toggle('hide',tab!==2);
  if(b1)b1.classList.toggle('isActive',tab===1);
  if(b2)b2.classList.toggle('isActive',tab===2);
  try{document.body.classList.toggle('start-tab-opts',tab===2)}catch(e){}
  let box=document.getElementById('startDangBaiTapBox');
  let empty=document.getElementById('startDbtEmptyHint');
  if(empty){
    let noDbt=!box||box.classList.contains('hide');
    empty.classList.toggle('hide',!(tab===1&&noDbt));
  }
  let body=document.querySelector('#startModal .startModalBody');
  if(body)try{body.scrollTop=0}catch(e){}
}
function closeStartModal(){try{document.body.classList.remove('start-tab-opts','start-exam-open')}catch(e){}let m=document.getElementById('startModal');if(m)m.classList.add('hide')}
let EXAM_PICK_TAB='preset',EXAM_PICK_ALL=false,EXAM_PICK_IDS=[],EXAM_POOL_CACHE=null;
function setExamPickTab(tab){
  EXAM_PICK_TAB=tab||'preset';
  ['preset','bytype','pick'].forEach(t=>{
    let box=document.getElementById(t==='preset'?'examTabPreset':(t==='bytype'?'examTabByType':'examTabPick'));
    if(box)box.classList.toggle('hide',EXAM_PICK_TAB!==t);
  });
  document.querySelectorAll('.startExamTab').forEach(b=>{
    let on=b.getAttribute('data-exam-tab')===EXAM_PICK_TAB;
    b.style.fontWeight=on?'900':'600';
    b.style.borderColor=on?'var(--primary)':'';
    b.style.background=on?'var(--primary-bg)':'';
  });
  if(EXAM_PICK_TAB==='pick'||EXAM_PICK_TAB==='bytype')loadExamPoolList(false);
  updateExamPickSummary();
}
function setExamPreset(n){
  EXAM_PICK_TAB='preset';EXAM_PICK_IDS=[];
  setExamPickTab('preset');
  let nq=document.getElementById('startNumQuestions');
  if(n==='all'){EXAM_PICK_ALL=true;if(nq)nq.value='';}
  else{EXAM_PICK_ALL=false;if(nq)nq.value=String(n);}
  updateExamPickSummary();
}
function setExamSpecPreset(tn,ds,tln){
  EXAM_PICK_TAB='bytype';EXAM_PICK_ALL=false;EXAM_PICK_IDS=[];
  setExamPickTab('bytype');
  let a=document.getElementById('examSpecTn'),b=document.getElementById('examSpecDs'),c=document.getElementById('examSpecTln');
  if(a)a.value=String(tn||0);if(b)b.value=String(ds||0);if(c)c.value=String(tln||0);
  updateExamPickSummary();
}
function collectExamSpec(){
  let tn=parseInt((document.getElementById('examSpecTn')||{}).value,10)||0;
  let ds=parseInt((document.getElementById('examSpecDs')||{}).value,10)||0;
  let tln=parseInt((document.getElementById('examSpecTln')||{}).value,10)||0;
  let spec={};if(tn>0)spec.tn=tn;if(ds>0)spec.ds=ds;if(tln>0)spec.tln=tln;return spec;
}
function updateExamPickSummary(){
  let el=document.getElementById('examPickSummary');if(!el)return;
  let txt='';
  if(EXAM_PICK_TAB==='pick'){
    let n=EXAM_PICK_IDS.length;txt='Đã tick: <b>'+n+'</b> câu';
  }else if(EXAM_PICK_TAB==='bytype'){
    let s=collectExamSpec();let n=(s.tn||0)+(s.ds||0)+(s.tln||0);
    txt='Theo dạng: <b>'+(s.tn||0)+'</b> TN + <b>'+(s.ds||0)+'</b> Đ/S + <b>'+(s.tln||0)+'</b> TLN = <b>'+n+'</b> câu';
    let c=EXAM_POOL_CACHE&&EXAM_POOL_CACHE.counts||{};
    let info=document.getElementById('examByTypeCounts');
    if(info)info.textContent='Có trong đề (đã duyệt): TN '+(c['Trắc nghiệm']||0)+' · Đ/S '+(c['Đúng sai']||0)+' · TLN '+(c['Trả lời ngắn']||0)+(c['Tự luận']?(' · TL '+c['Tự luận']):'');
  }else{
    if(EXAM_PICK_ALL)txt='Nút sẵn: <b>Tất cả</b> câu đã duyệt';
    else{let n=parseInt((document.getElementById('startNumQuestions')||{}).value,10)||0;txt=n?('Nút sẵn / số câu: <b>'+n+'</b> câu (bốc ngẫu nhiên)'):'Chưa chọn số câu';}
  }
  el.innerHTML=txt;
}
async function loadExamPoolList(force){
  if(!CURRENT_MADE)return;
  if(!force&&EXAM_POOL_CACHE&&EXAM_POOL_CACHE.made===CURRENT_MADE){renderExamPickList();updateExamPickSummary();return}
  let box=document.getElementById('examPickList');if(box)box.innerHTML='<div class="muted" style="padding:8px">Đang tải danh sách câu đã duyệt…</div>';
  try{
    let lv=(val('fMucDo')||CURRENT_LEVEL||'').trim().toUpperCase();
    let dg=(val('fDang')||CURRENT_DANG||'').trim();
    let dbt=getStartModalDangBaiTap?getStartModalDangBaiTap():(CURRENT_DANGBAITAP||'');
    let j=await api('/api/exam-pool',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({made:CURRENT_MADE,level:lv,dang:dg,dangbaitap:dbt})});
    EXAM_POOL_CACHE=Object.assign({made:CURRENT_MADE},j||{});
    renderExamPickList();updateExamPickSummary();
  }catch(e){if(box)box.innerHTML='<div class="muted" style="padding:8px;color:#991b1b">'+esc(e.message||e)+'</div>';}
}
function renderExamPickList(){
  let box=document.getElementById('examPickList');if(!box)return;
  let items=(EXAM_POOL_CACHE&&EXAM_POOL_CACHE.items)||[];
  if(!items.length){box.innerHTML='<div class="muted" style="padding:8px">Không có câu đã duyệt trong phạm vi.</div>';return}
  let sel=new Set(EXAM_PICK_IDS);
  box.innerHTML=items.map((it,i)=>{
    let id=String(it.ID||'');let on=sel.has(id);
    return `<label style="display:flex;gap:8px;align-items:flex-start;padding:6px 4px;border-bottom:1px solid var(--border);font-size:12px;line-height:1.35;cursor:pointer"><input type="checkbox" data-exam-id="${escAttr(id)}" ${on?'checked':''} onchange="toggleExamPickId(this.getAttribute('data-exam-id'),this.checked)"><span><b>${i+1}.</b> <span class="tag">${esc(it.Dang||'')}</span> ${it.MucDo?('<span class="tag">'+esc(it.MucDo)+'</span> '):''}<span class="muted">${esc(id)}</span><br>${esc(it.stem||'')}</span></label>`;
  }).join('');
}
function toggleExamPickId(id,on){
  id=String(id||'');if(!id)return;
  EXAM_PICK_ALL=false;EXAM_PICK_TAB='pick';
  let set=new Set(EXAM_PICK_IDS);
  if(on)set.add(id);else set.delete(id);
  EXAM_PICK_IDS=[...set];
  updateExamPickSummary();
}
function examPickSelectAll(on){
  let items=(EXAM_POOL_CACHE&&EXAM_POOL_CACHE.items)||[];
  EXAM_PICK_TAB='pick';EXAM_PICK_ALL=false;
  EXAM_PICK_IDS=on?items.map(x=>String(x.ID||'')).filter(Boolean):[];
  renderExamPickList();updateExamPickSummary();
}
function syncStartExamUi(){
  let exam=!!(document.getElementById('chkExamMode')&&document.getElementById('chkExamMode').checked);try{document.body.classList.toggle('start-exam-open',exam)}catch(e){}
  let panel=document.getElementById('startExamPanel');if(panel)panel.classList.toggle('hide',!exam);
  let hint=document.getElementById('startExamHint');if(hint)hint.classList.toggle('hide',!exam);
  let pend=document.getElementById('startIncludePendingWrap');
  if(pend){pend.classList.toggle('hide',!(USER&&USER.is_admin&&!exam));pend.style.display=(USER&&USER.is_admin&&!exam)?'flex':'none'}
  let linkBtn=document.getElementById('btnCreateExamLink');if(linkBtn)linkBtn.classList.toggle('hide',!(USER&&USER.is_admin&&exam));
  let gd=document.getElementById('chkGroupDang');if(gd&&exam)gd.checked=false;
  if(exam){
    setExamPickTab(EXAM_PICK_TAB||'preset');
    if(EXAM_PICK_TAB==='preset'&&!EXAM_PICK_ALL&&!(document.getElementById('startNumQuestions')||{}).value)setExamPreset(20);
  }
  updateExamPickSummary();
}
function collectExamAssignPayload(){
  if(!CURRENT_MADE)throw new Error('Chưa chọn đề.');
  if(!(document.getElementById('chkExamMode')&&document.getElementById('chkExamMode').checked))throw new Error('Hãy bật «Làm bài kiểm tra» trước.');
  let item=CATALOG.find(x=>x.MaDe===CURRENT_MADE)||{};
  let payload={made:CURRENT_MADE,title:examDisplayTitle(item),level:(val('fMucDo')||CURRENT_LEVEL||'').trim().toUpperCase(),dang:(val('fDang')||CURRENT_DANG||'').trim(),dangbaitap:getStartModalDangBaiTap?getStartModalDangBaiTap():(CURRENT_DANGBAITAP||''),shuffle_a:document.getElementById('chkShuffleA')&&document.getElementById('chkShuffleA').checked?1:0};
  if(EXAM_PICK_TAB==='pick'){
    if(!EXAM_PICK_IDS.length)throw new Error('Tick chọn ít nhất 1 câu.');
    payload.question_ids=EXAM_PICK_IDS.slice();
  }else if(EXAM_PICK_TAB==='bytype'){
    payload.exam_spec=collectExamSpec();
    if(!((payload.exam_spec.tn||0)+(payload.exam_spec.ds||0)+(payload.exam_spec.tln||0)))throw new Error('Nhập số câu theo dạng TN/ĐS/TLN.');
  }else{
    payload.exam_all=EXAM_PICK_ALL?1:0;
    payload.num_questions=parseInt((document.getElementById('startNumQuestions')||{}).value,10)||0;
    if(!payload.exam_all&&payload.num_questions<=0)throw new Error('Chọn nút 10/20/28/Tất cả hoặc nhập số câu.');
  }
  return payload;
}
async function createAndCopyExamLink(){
  if(!(USER&&USER.is_admin)){alert('Chỉ ADMIN tạo link gửi học sinh.');return}
  try{
    let payload=collectExamAssignPayload();
    let j=await api('/api/exam-assign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    let url=j.url||(location.origin+(j.path||('/?exam='+j.code+'&start=1')));
    let ok=await copyTextToClipboard(url);
    alert((ok?'✅ Đã chép link bài kiểm tra.\n\n':'⚠ Không chép được — hãy copy thủ công:\n\n')+url+'\n\nMã: '+(j.code||'')+'\nGửi Zalo/Messenger cho học sinh.\nCác em đăng nhập → mở link → làm bài (không xem đáp án đến khi nộp).');
  }catch(e){alert('Không tạo được link: '+(e.message||e))}
}
function resetExamPickState(){
  EXAM_PICK_TAB='preset';EXAM_PICK_ALL=false;EXAM_PICK_IDS=[];EXAM_POOL_CACHE=null;
  let nq=document.getElementById('startNumQuestions');if(nq)nq.value='';
  let a=document.getElementById('examSpecTn'),b=document.getElementById('examSpecDs'),c=document.getElementById('examSpecTln');
  if(a)a.value='10';if(b)b.value='4';if(c)c.value='6';
  let box=document.getElementById('examPickList');if(box)box.innerHTML='';
}
function openStartModal(made,dbtPref){CURRENT_MADE=made;CURRENT_LEVEL=(val('fMucDo')||'').trim().toUpperCase();CURRENT_DANG=(val('fDang')||'').trim();CURRENT_DANGBAITAP=String(dbtPref!=null?dbtPref:(val('fDangBaiTap')||'')).trim();START_IS_RETRY=false;document.getElementById('startModalTitle').textContent='Thiết lập làm bài';document.getElementById('chkShuffleQ').checked=false;document.getElementById('chkShuffleA').checked=false;let gd=document.getElementById('chkGroupDang');if(gd)gd.checked=true;let ex=document.getElementById('chkExamMode');if(ex)ex.checked=false;resetExamPickState();let ip=document.getElementById('chkIncludePending');if(ip)ip.checked=adminIncludePendingDefault();syncStartExamUi();let note=document.getElementById('startFilterNote');if(note){let item=CATALOG.find(x=>x.MaDe===made)||{};let lv=CURRENT_LEVEL;let dg=CURRENT_DANG;let mc=filterMatchCount(item,lv,dg);let parts=[];if(dg)parts.push('dạng <b>'+esc(dg)+'</b>'+(mc!=null?' — <b>'+mc+'</b> câu':''));if(lv)parts.push('mức <b>'+esc(lv)+'</b>');let base=parts.length?'🎯 Chỉ làm câu '+parts.join(' · ')+'.':'';if(USER&&USER.is_admin)base+=(base?' ':'')+'⚠ Mặc định <b>gồm cả chưa duyệt</b> — bỏ tick nếu chỉ xem đã duyệt.';note.innerHTML=base;note.classList.toggle('hide',!base)}renderStartDangBaiTapPicker(made,CURRENT_DANGBAITAP);let sm=document.getElementById('startModal');if(sm)sm.classList.remove('hide')}
function openRetryModal(){if(USER.can_quiz_retry===false)return;if(!CURRENT_MADE){alert('Chưa xác định được mã đề.');return}CURRENT_LEVEL=(val('fMucDo')||CURRENT_LEVEL||'').trim().toUpperCase();CURRENT_DANG=(val('fDang')||CURRENT_DANG||'').trim();START_IS_RETRY=true;document.getElementById('startModalTitle').textContent='Làm lại đề';let ex=document.getElementById('chkExamMode');if(ex)ex.checked=false;resetExamPickState();syncStartExamUi();let note=document.getElementById('startFilterNote');if(note){let item=CATALOG.find(x=>x.MaDe===CURRENT_MADE)||{};let mc=filterMatchCount(item,CURRENT_LEVEL,CURRENT_DANG);if(CURRENT_DANG||CURRENT_LEVEL){let parts=[];if(CURRENT_DANG)parts.push('dạng <b>'+esc(CURRENT_DANG)+'</b>'+(mc!=null?' — <b>'+mc+'</b> câu':''));if(CURRENT_LEVEL)parts.push('mức <b>'+esc(CURRENT_LEVEL)+'</b>');note.innerHTML='🎯 Chỉ làm câu '+parts.join(' · ')+'.';note.classList.remove('hide')}else{note.innerHTML='';note.classList.add('hide')}}renderStartDangBaiTapPicker(CURRENT_MADE,CURRENT_DANGBAITAP);let sm2=document.getElementById('startModal');if(sm2)sm2.classList.remove('hide')}
async function confirmStartQuiz(){
  let made=CURRENT_MADE;if(!made)return;
  let sq=document.getElementById('chkShuffleQ').checked;let sa=document.getElementById('chkShuffleA').checked;
  let gd=document.getElementById('chkGroupDang');let groupBy=gd?gd.checked:true;
  let exam=!!(document.getElementById('chkExamMode')&&document.getElementById('chkExamMode').checked);
  let includePending=!!(USER&&USER.is_admin&&document.getElementById('chkIncludePending')&&document.getElementById('chkIncludePending').checked&&!exam);
  let numQ=0,examAll=false,ids=[],spec={};
  if(exam){
    if(EXAM_PICK_TAB==='pick'){
      ids=EXAM_PICK_IDS.slice();
      if(!ids.length){alert('Hãy tick chọn ít nhất 1 câu trong danh sách.');return}
    }else if(EXAM_PICK_TAB==='bytype'){
      spec=collectExamSpec();
      if(!((spec.tn||0)+(spec.ds||0)+(spec.tln||0))){alert('Nhập số câu theo dạng (TN / Đ/S / TLN).');return}
    }else{
      examAll=!!EXAM_PICK_ALL;
      numQ=parseInt((document.getElementById('startNumQuestions')||{}).value,10)||0;
      if(!examAll&&numQ<=0){alert('Chọn nút 10/20/28/Tất cả hoặc nhập số câu.');return}
    }
  }
  let lv=(val('fMucDo')||'').trim().toUpperCase();let dg=(val('fDang')||'').trim();
  CURRENT_LEVEL=lv;CURRENT_DANG=dg;CURRENT_DANGBAITAP=getStartModalDangBaiTap();
  closeStartModal();
  if(START_IS_RETRY&&!SUBMITTED&&Object.keys(ANSWERS).length){if(!confirm('Làm lại sẽ xóa bài đang làm. Tiếp tục?'))return}
  await startQuiz(made,sq,sa,lv,dg,groupBy,CURRENT_DANGBAITAP,exam,numQ,includePending,ids,spec,examAll);
}
function pickShufflePreset(kind){document.getElementById('chkShuffleQ').checked=kind==='q'||kind==='both';document.getElementById('chkShuffleA').checked=kind==='a'||kind==='both';if(kind==='none'){document.getElementById('chkShuffleQ').checked=false;document.getElementById('chkShuffleA').checked=false}confirmStartQuiz()}
function updateShuffleBadge(j){let el=document.getElementById('shuffleBadge');if(!el)return;let parts=[];if(j&&j.shuffle_questions)parts.push('Xáo câu');if(j&&j.shuffle_options)parts.push('Xáo đáp án');if(parts.length){el.textContent=parts.join(' + ');el.classList.remove('hide')}else{el.textContent='';el.classList.add('hide')}}
function deriveKhoi(lop){let s=String(lop||'').trim();if(!s)return '';let m=s.match(/^(\d{1,2})/);if(m)return m[1];let m2=s.match(/\b(10|11|12)\b/);return m2?m2[1]:''}
function rpCatalogBase(){return(CATALOG||[]).filter(x=>x.Mon&&x.Lop)}
function rpFilterCatalog(){let mon=val('rpMon'),khoi=val('rpKhoi'),lop=val('rpLop');return rpCatalogBase().filter(x=>{if(mon&&x.Mon!==mon)return false;if(khoi&&deriveKhoi(x.Lop)!==khoi)return false;if(lop&&x.Lop!==lop)return false;return true})}
function rpScopeSummary(){let mon=val('rpMon'),lop=val('rpLop'),ch=val('rpChuong'),bai=val('rpBaiHoc');let parts=[mon,lop?'Lớp '+lop:'',ch,bai].filter(Boolean);return parts.join(' · ')}
function syncRpKhoiFromLop(){let lop=val('rpLop'),khoiEl=document.getElementById('rpKhoi');if(!khoiEl)return;let dk=lop?deriveKhoi(lop):'';if(dk)khoiEl.innerHTML=`<option value="${escAttr(dk)}" selected>${esc(dk)}</option>`;else khoiEl.innerHTML='<option value=""></option>'}
function refreshRpChuongBaiOptions(){let lop=val('rpLop');let chEl=document.getElementById('rpChuong'),baiEl=document.getElementById('rpBaiHoc');if(chEl){chEl.disabled=!lop;if(!lop){chEl.innerHTML='<option value="">Tất cả</option>'}else{let chuongs=uniqField(rpFilterCatalog(),'Chuong');setRpSelectOptions('rpChuong',chuongs,val('rpChuong'),'<option value="">Tất cả</option>')}}if(baiEl){baiEl.disabled=!lop;if(!lop){baiEl.innerHTML='<option value="">Tất cả</option>'}else{let ch=val('rpChuong');let baiBase=ch?rpFilterCatalog().filter(x=>x.Chuong===ch):rpFilterCatalog();setRpSelectOptions('rpBaiHoc',uniqField(baiBase,'BaiHoc'),val('rpBaiHoc'),'<option value="">Tất cả</option>')}}}
function setRpSelectOptions(selId,opts,cur,ph){let el=document.getElementById(selId);if(!el)return;let keep=cur||el.value;el.innerHTML=(ph||'<option value="">—</option>')+opts.map(v=>`<option value="${escAttr(v)}">${esc(v)}</option>`).join('');if(keep&&opts.includes(keep))el.value=keep}
function refreshRpScopeOptions(){if(RP_SCOPE_LOCKED){refreshRpChuongBaiOptions();return}let mon=val('rpMon');let base=rpCatalogBase();setRpSelectOptions('rpMon',uniqField(base,'Mon'),mon,'<option value="">— Môn —</option>');let k1=mon?base.filter(x=>x.Mon===mon):[];let lopEl=document.getElementById('rpLop');if(lopEl){lopEl.disabled=!mon;lopEl.classList.toggle('rpLockable',true);setRpSelectOptions('rpLop',uniqField(k1,'Lop'),val('rpLop'),'<option value="">— Lớp —</option>')}syncRpKhoiFromLop();refreshRpChuongBaiOptions()}
function onRpScopeChange(level){if(RP_SCOPE_LOCKED)return;if(level==='mon'){setVal('rpKhoi','');setVal('rpLop','');setVal('rpChuong','');setVal('rpBaiHoc','')}else if(level==='lop'){syncRpKhoiFromLop();setVal('rpChuong','');setVal('rpBaiHoc','')}else if(level==='chuong')setVal('rpBaiHoc','');refreshRpScopeOptions();if(USER&&USER.is_admin)syncAdminComposeChrome()}
function maybeLockRpScope(){let mon=val('rpMon'),lop=val('rpLop');syncRpKhoiFromLop();let khoi=val('rpKhoi');if(!mon||!lop||!khoi)return;RP_SCOPE_LOCKED=true;let wrap=document.querySelector('.practiceRandomPanel');if(wrap)wrap.classList.add('rpLocked');['rpMon','rpLop','rpChuong','rpBaiHoc'].forEach(id=>{let e=document.getElementById(id);if(e)e.disabled=true});let bu=document.getElementById('btnRpUnlock');if(bu)bu.style.display='';let note=document.getElementById('rpScopeNote');if(note){note.innerHTML=`🔒 ${esc(rpScopeSummary())}`;note.classList.remove('hide')}if(USER&&USER.is_admin)syncAdminComposeChrome()}
function unlockRpScope(){RP_SCOPE_LOCKED=false;let wrap=document.querySelector('.practiceRandomPanel');if(wrap)wrap.classList.remove('rpLocked');let bu=document.getElementById('btnRpUnlock');if(bu)bu.style.display='none';let note=document.getElementById('rpScopeNote');if(note){note.innerHTML='';note.classList.add('hide')}refreshRpScopeOptions();if(USER&&USER.is_admin)syncAdminComposeChrome()}
function getRpSelectedChuongs(){let ch=val('rpChuong');return ch?[ch]:[]}
function syncRpFromMainFilters(){if(RP_SCOPE_LOCKED)return;let m=val('fMon'),l=val('fLop'),ch=val('fChuong'),bai=val('fBaiHoc');if(m)setVal('rpMon',m);refreshRpScopeOptions();if(l&&deriveKhoi(l)){setVal('rpKhoi',deriveKhoi(l));refreshRpScopeOptions();setVal('rpLop',l);refreshRpScopeOptions()}if(ch)setVal('rpChuong',ch);if(bai)setVal('rpBaiHoc',bai);refreshRpScopeOptions()}
function initRpPracticePanel(){syncRpFromMainFilters();if(!RP_SCOPE_LOCKED)refreshRpScopeOptions();syncRpExportLatexBtn()}
async function startRandomPractice(){try{if(typeof syncRpFromMainFilters==='function')syncRpFromMainFilters();let mon=val('rpMon'),lop=val('rpLop');syncRpKhoiFromLop();let khoi=val('rpKhoi');if(!mon||!lop||!khoi){alert('Hãy chọn đủ Môn và Lớp ở «Lọc đề» trước.');return}if(!RP_SCOPE_LOCKED)maybeLockRpScope();let chuongs=getRpSelectedChuongs();let bai=val('rpBaiHoc');let solOnly=!!(document.getElementById('fSolFullOnly')&&document.getElementById('fSolFullOnly').checked);let lv=(val('fMucDo')||'').trim().toUpperCase();let j=await api('/api/start-random',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mon,khoi,lop,chuongs,chuong:val('rpChuong'),bai_hoc:bai,level:lv,sol_full_only:solOnly?1:0,shuffle_a:1})});if(!j||!j.questions||!j.questions.length){alert(j&&j.error?j.error:'Không đủ câu trong phạm vi đã chọn để ghép đề (cần 18 TN + 4 Đ/S + 6 TLN).');return}enterQuizSession(j,j.made||'',lv,'','',false)}catch(e){alert('Không tạo được đề ngẫu nhiên: '+(e.message||e))}}
const AC_MATRIX_DANGS=['Trắc nghiệm','Đúng sai','Trả lời ngắn','Tự luận'];
const AC_MATRIX_LEVELS=['NB','TH','VD','VDC'];
let AC_MATRIX_DATA=null;
function acComposePayloadBase(){syncRpKhoiFromLop();let mon=val('rpMon'),khoi=val('rpKhoi'),lop=val('rpLop');let chuongs=getRpSelectedChuongs();let solOnly=!!(document.getElementById('fSolFullOnly')&&document.getElementById('fSolFullOnly').checked);let lv=(val('acLevelFilter')||'').trim().toUpperCase();let bai=(val('rpBaiHoc')||val('acBaiHoc')||'').trim();return{mon,khoi,lop,chuongs,chuong:val('rpChuong'),level:lv,bai_hoc:bai,sol_full_only:solOnly?1:0}}
function isAdminComposeOpen(){try{return localStorage.getItem('LDVL_ADMIN_COMPOSE_OPEN_V257')==='1'}catch(e){return false}}
function setAdminComposeOpen(open){try{localStorage.setItem('LDVL_ADMIN_COMPOSE_OPEN_V257',open?'1':'0')}catch(e){}syncAdminComposeChrome();if(open)refreshAdminComposeMatrix()}
function toggleAdminComposeCompact(){setAdminComposeOpen(!isAdminComposeOpen())}
function syncAdminComposeChrome(){if(!USER||!USER.is_admin)return;let panel=document.getElementById('adminComposePanel');let open=isAdminComposeOpen();if(panel){panel.classList.toggle('acCollapsed',!open);let title=panel.querySelector('b');if(title&&!document.getElementById('adminComposeToggle'))title.insertAdjacentHTML('afterend',' <button type="button" id="adminComposeToggle" class="btn2 adminComposeToggle" onclick="toggleAdminComposeCompact()">Mở ghép đề</button>');let btn=document.getElementById('adminComposeToggle');if(btn)btn.textContent=open?'Thu gọn':'Mở ghép đề'}let note=document.getElementById('acScopeNote');let mon=val('rpMon'),lop=val('rpLop');syncRpKhoiFromLop();if(note){if(mon&&lop){note.innerHTML=`📌 ${esc(rpScopeSummary())}`;note.classList.remove('hide')}else{note.innerHTML='⚠️ Chọn Môn · Lớp ở «Lọc đề».';note.classList.remove('hide')}}let bh=document.getElementById('acBaiHoc');if(bh&&mon&&lop){let ch=val('rpChuong');let baiBase=ch?rpFilterCatalog().filter(x=>x.Chuong===ch):rpFilterCatalog();let list=uniqField(baiBase,'BaiHoc');let cur=val('acBaiHoc')||val('rpBaiHoc');bh.innerHTML='<option value="">Tất cả bài</option>'+list.map(x=>`<option${x===cur?' selected':''}>${esc(x)}</option>`).join('')}}
function renderAdminComposeMatrix(j){AC_MATRIX_DATA=j||null;let wrap=document.getElementById('acMatrixWrap');let st=document.getElementById('acComposeStatus');if(!wrap)return;if(!j||!j.matrix){wrap.innerHTML='<div class="muted" style="padding:12px">Chưa có dữ liệu ma trận.</div>';return}let levels=j.levels||AC_MATRIX_LEVELS;let dangs=j.dangs||AC_MATRIX_DANGS;let hdr='<tr><th>Dạng \\ Mức</th>'+levels.map(lv=>'<th>'+esc(lv)+'</th>').join('')+'<th>Mọi mức</th></tr>';let body=dangs.map(d=>{let row=j.matrix[d]||{};let any=j.row_any&&j.row_any[d]!=null?j.row_any[d]:0;let cells=levels.map(lv=>{let av=row[lv]||0;let id='ac_'+d.replace(/\s+/g,'_')+'_'+lv;return '<td><span class="acAvail">'+av+'</span><input type="number" min="0" max="99" class="acNeed" id="'+id+'" data-dang="'+escAttr(d)+'" data-level="'+escAttr(lv)+'" placeholder="0"></td>'}).join('');let idAny='ac_'+d.replace(/\s+/g,'_')+'_ANY';return '<tr><td class="acDang">'+esc(d)+'</td>'+cells+'<td><span class="acAvail">'+any+'</span><input type="number" min="0" max="99" class="acNeed" id="'+idAny+'" data-dang="'+escAttr(d)+'" data-level="" placeholder="0"></td></tr>'}).join('');wrap.innerHTML='<table class="acMatrix"><thead>'+hdr+'</thead><tbody>'+body+'</tbody></table>';if(st)st.textContent='Có '+((j.pool_size!=null?j.pool_size:j.total)||0)+' câu trong phạm vi đã chọn.'}
async function refreshAdminComposeMatrix(){if(!USER||!USER.is_admin)return;if(typeof syncRpFromMainFilters==='function')syncRpFromMainFilters();syncAdminComposeChrome();if(!isAdminComposeOpen())return;let mon=val('rpMon'),lop=val('rpLop');syncRpKhoiFromLop();let khoi=val('rpKhoi');let wrap=document.getElementById('acMatrixWrap');let st=document.getElementById('acComposeStatus');if(!mon||!lop||!khoi){if(wrap)wrap.innerHTML='<div class="muted" style="padding:10px">Chọn Môn · Lớp ở «Lọc đề» rồi quay lại đây.</div>';if(st)st.textContent='';return}if(!RP_SCOPE_LOCKED)maybeLockRpScope();if(st)st.textContent='Đang tải ma trận…';try{let body=acComposePayloadBase();let j=await api('/api/admin/pool-matrix',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});renderAdminComposeMatrix(j)}catch(e){if(wrap)wrap.innerHTML='<div class="muted" style="padding:12px;color:#991b1b">'+esc(e.message||e)+'</div>';if(st)st.textContent=''}}
function acClearMatrixInputs(){document.querySelectorAll('.acNeed').forEach(inp=>{inp.value=''})}
function acPresetStandard28(){acClearMatrixInputs();let set=(d,n)=>{let el=document.querySelector('.acNeed[data-dang="'+d+'"][data-level=""]');if(el)el.value=String(n)};set('Trắc nghiệm',18);set('Đúng sai',4);set('Trả lời ngắn',6);let st=document.getElementById('acComposeStatus');if(st)st.textContent='Đã điền đề chuẩn 28 câu (cột «Mọi mức»). Bấm «Ghép đề ADMIN».'}
function collectAdminComposeSpec(){let spec=[];document.querySelectorAll('.acNeed').forEach(inp=>{let n=parseInt(inp.value,10);if(!n||n<=0)return;let d=inp.getAttribute('data-dang')||'';let lv=(inp.getAttribute('data-level')||'').trim().toUpperCase();spec.push({dang:d,level:lv,count:n})});return spec}
async function startAdminComposeExam(){if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return}if(typeof syncRpFromMainFilters==='function')syncRpFromMainFilters();let mon=val('rpMon'),lop=val('rpLop');syncRpKhoiFromLop();let khoi=val('rpKhoi');if(!mon||!lop||!khoi){alert('Chọn đủ Môn và Lớp ở khối «Lọc đề».');return}if(!RP_SCOPE_LOCKED)maybeLockRpScope();let spec=collectAdminComposeSpec();if(!spec.length){alert('Nhập số câu cần lấy trong ma trận (hoặc bấm «Đề chuẩn 28»).');return}let st=document.getElementById('acComposeStatus');if(st)st.textContent='Đang ghép đề…';try{let body=Object.assign(acComposePayloadBase(),{spec,shuffle_a:1});let j=await api('/api/admin/start-compose',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!j||!j.questions||!j.questions.length){alert(j&&j.error?j.error:'Không ghép được đề.');if(st)st.textContent='';return}let lv=(val('acLevelFilter')||'').trim().toUpperCase();if(st)st.textContent='Đã ghép '+j.questions.length+' câu.'+(j.random_shortages&&j.random_shortages.length?'\nThiếu: '+j.random_shortages.join('; '):'');enterQuizSession(j,j.made||'',lv,'','',false)}catch(e){if(st)st.textContent='';alert('Không ghép được đề: '+(e.message||e))}}
function initAdminComposePanel(){syncAdminComposeChrome();if(USER&&USER.is_admin&&isAdminComposeOpen())refreshAdminComposeMatrix()}

let AI_GEN_QUESTIONS=[],AI_GEN_BUSY=false,AI_GEN_SAVED=false,AI_GEN_REQUEST_ID='';
function agUniqueKeep(items){let seen=new Set(),out=[];for(let x of items||[]){let v=String(x||'').trim();if(!v)continue;let k=normText(v);if(seen.has(k))continue;seen.add(k);out.push(v)}return out}
function agSetOptions(id,items,keep,placeholder){let el=document.getElementById(id);if(!el)return;let vals=agUniqueKeep(items);let cur=keep!==undefined?String(keep||''):String(el.value||'');el.innerHTML=`<option value="">${esc(placeholder||'— Chọn —')}</option>`+vals.map(x=>`<option value="${escAttr(x)}">${esc(x)}</option>`).join('');let hit=vals.find(x=>normText(x)===normText(cur));el.value=hit||(vals.includes(cur)?cur:'')}
function agSetCombo(inputId,listId,items,keep){let el=document.getElementById(inputId);let dl=document.getElementById(listId);let vals=agUniqueKeep(items);if(dl)dl.innerHTML=vals.map(x=>`<option value="${escAttr(x)}"></option>`).join('');if(el){let cur=keep!==undefined&&keep!==null?String(keep):String(el.value||'');let hit=vals.find(x=>normText(x)===normText(cur));el.value=hit||cur}}
function agScopeRows(){let lc=((META&&META.lesson_catalog)||[]).slice();return lc.length?lc:(CATALOG||[])}
function agEq(a,b){return normText(a)===normText(b)}
function agFilterRows(rows,mon,lop,chuong,bai){return (rows||[]).filter(x=>(!mon||agEq(x.Mon,mon))&&(!lop||agEq(x.Lop,lop))&&(!chuong||agEq(x.Chuong,chuong))&&(!bai||agEq(x.BaiHoc,bai)))}
function agFilteredCatalog(stage){return agFilterRows(agScopeRows(),val('agMon'),val('agLop'),val('agChuong'),val('agBaiHoc'))}
function agParseDbtCell(raw){raw=String(raw||'').trim();if(!raw)return[];if(raw.charAt(0)==='['){try{let arr=JSON.parse(raw);if(Array.isArray(arr))return arr.map(x=>oneLineText(x)).filter(Boolean)}catch(e){let quoted=raw.match(/"([^"]+)"/g);if(quoted&&quoted.length)return quoted.map(x=>oneLineText(x.slice(1,-1))).filter(Boolean)}}return raw.split(/[\n;|]+/).map(x=>oneLineText(x)).filter(Boolean)}
function agDbtValues(list){let out=[],seen=new Set();for(let x of (list||[])){let parts=agParseDbtCell(x&&x.DangBaiTap);if(!parts.length){try{for(let pair of catalogDbtCounts(x))parts.push(String(pair&&pair[0]||'').trim())}catch(e){}}for(let d of parts){d=oneLineText(d);if(!d)continue;let k=normText(d);if(seen.has(k))continue;seen.add(k);out.push(d)}}return out}
function agRefreshScopeOptions(){if(!USER||!USER.is_admin)return;let rows=agScopeRows();let mon=val('agMon'),lop=val('agLop'),chuong=val('agChuong'),bai=val('agBaiHoc');agSetOptions('agMon',uniqField(rows,'Mon'),mon,'— Chọn môn —');let byMon=agFilterRows(rows,val('agMon'),'','','');agSetOptions('agLop',uniqField(byMon,'Lop'),lop,'— Chọn lớp —');let byLop=agFilterRows(rows,val('agMon'),val('agLop'),'','');agSetCombo('agChuong','agChuongList',uniqField(byLop,'Chuong'),chuong);let byCh=agFilterRows(rows,val('agMon'),val('agLop'),val('agChuong'),'');agSetCombo('agBaiHoc','agBaiHocList',uniqField(byCh,'BaiHoc'),bai);let dl=document.getElementById('agDangBaiTapList');if(dl){let scoped=agFilterRows(rows,val('agMon'),val('agLop'),val('agChuong'),val('agBaiHoc'));dl.innerHTML=agDbtValues(scoped).map(x=>`<option value="${escAttr(x)}"></option>`).join('')}}
function agScopeChange(stage){if(stage==='mon'){setVal('agLop','');setVal('agChuong','');setVal('agBaiHoc','');setVal('agDangBaiTap','')}else if(stage==='lop'){setVal('agChuong','');setVal('agBaiHoc','');setVal('agDangBaiTap','')}else if(stage==='chuong'){setVal('agBaiHoc','');setVal('agDangBaiTap','')}else if(stage==='baihoc'){setVal('agDangBaiTap','')}agRefreshScopeOptions()}
function initAdminAiGenerator(){let p=document.getElementById('adminAiGeneratePanel');if(!p)return;if(!USER||!USER.is_admin){p.classList.add('hide');return}p.classList.remove('hide');let first=!document.getElementById('agMon').options.length||document.getElementById('agMon').options.length<=1;agRefreshScopeOptions();if(first){let fm=val('fMon'),fl=val('fLop'),fc=val('fChuong'),fb=val('fBaiHoc');if(fm)setVal('agMon',fm);agRefreshScopeOptions();if(fl)setVal('agLop',fl);agRefreshScopeOptions();if(fc)setVal('agChuong',fc);agRefreshScopeOptions();if(fb)setVal('agBaiHoc',fb);agRefreshScopeOptions()}try{syncAdminAiProviderChrome()}catch(e){}renderAiGenPreview()}
function openAdminAiGenFromEl(el){if(!el)return;openAdminAiGenForDbt({Mon:el.getAttribute('data-mon')||'',Lop:el.getAttribute('data-lop')||'',Chuong:el.getAttribute('data-chuong')||'',BaiHoc:el.getAttribute('data-bai')||'',DangBaiTap:el.getAttribute('data-dbt')||'',Dang:el.getAttribute('data-dang')||''})}
function openAdminAiGenForDbt(scope){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return}
  scope=scope||{};
  try{if(typeof ldvlOpenPracticeView==='function')ldvlOpenPracticeView('adminAiGeneratePanel',scope.Mon||'')}catch(e){}
  let p=document.getElementById('adminAiGeneratePanel');
  if(p){p.classList.remove('hide');try{p.scrollIntoView({behavior:'smooth',block:'start'})}catch(e){}}
  try{initAdminAiGenerator()}catch(e){}
  let mon=String(scope.Mon||'').trim(),lop=String(scope.Lop||'').trim(),chuong=String(scope.Chuong||'').trim(),bai=String(scope.BaiHoc||'').trim(),dbt=String(scope.DangBaiTap||'').trim();
  if(mon){setVal('agMon',mon);agRefreshScopeOptions()}
  if(lop){setVal('agLop',lop);agRefreshScopeOptions()}
  if(chuong){setVal('agChuong',chuong);agRefreshScopeOptions()}
  if(bai){setVal('agBaiHoc',bai);agRefreshScopeOptions()}
  if(dbt)setVal('agDangBaiTap',dbt);
  if(scope.Dang)setVal('agDang',scope.Dang);
  let deBits=[bai,dbt].filter(Boolean);if(deBits.length&&!String(val('agDe')||'').trim())setVal('agDe',deBits.join(' · '));
  try{syncAdminAiProviderChrome()}catch(e){}
  let st=document.getElementById('agStatus');
  if(st)st.textContent='Đã chọn dạng «'+(dbt||'—')+'»'+(bai?(' · '+bai):'')+'. Chọn AI (Gemini / Claude) rồi bấm Tạo câu hỏi.';
  try{let md=document.getElementById('chapterDbtModal');if(md)md.classList.add('hide')}catch(e){}
}
window.openAdminAiGenForDbt=openAdminAiGenForDbt;window.openAdminAiGenFromEl=openAdminAiGenFromEl;
function aiGenPayload(count,offset){let antKey=_loadAnthropicKey();let p={Mon:val('agMon').trim(),Lop:val('agLop').trim(),Chuong:val('agChuong').trim(),BaiHoc:val('agBaiHoc').trim(),DangBaiTap:val('agDangBaiTap').trim(),Dang:val('agDang'),MucDo:val('agMucDo'),count,offset,BoDe:val('agBoDe').trim(),De:val('agDe').trim(),QuyenTruyCap:val('agQuyen'),Diem:val('agDiem').trim(),extra_instruction:val('agExtra').trim(),request_id:AI_GEN_REQUEST_ID,avoid_stems:AI_GEN_QUESTIONS.map(q=>String(q.CauHoi||'').slice(0,220))};if(antKey)p.anthropic_key=antKey;for(let k of ['Mon','Lop','Chuong','BaiHoc','DangBaiTap'])if(!p[k])throw new Error('Chưa nhập '+({Mon:'Môn',Lop:'Lớp',Chuong:'Chương',BaiHoc:'Bài học',DangBaiTap:'Dạng bài tập'}[k]));return p}
function setAiGenBusy(on){AI_GEN_BUSY=!!on;let b=document.getElementById('agGenerateBtn');if(b){b.disabled=!!on;b.textContent=on?'⏳ Đang tạo từng đợt…':'🤖 Tạo câu hỏi'}let s=document.getElementById('agSaveBtn');if(s)s.disabled=!!on||AI_GEN_SAVED||!AI_GEN_QUESTIONS.length}
function syncAiGenJson(){let ta=document.getElementById('agJson');if(ta)ta.value=JSON.stringify({questions:AI_GEN_QUESTIONS},null,2);let sb=document.getElementById('agSaveBtn');if(sb)sb.disabled=AI_GEN_BUSY||AI_GEN_SAVED||!AI_GEN_QUESTIONS.length}
function renderAiGenPreview(){let box=document.getElementById('agPreview');if(!box)return;if(!AI_GEN_QUESTIONS.length){box.innerHTML='';syncAiGenJson();return}box.innerHTML=AI_GEN_QUESTIONS.map((q,i)=>{let opts='';for(let L of ['A','B','C','D'])if(q[L])opts+=`<div class="aiGenOpt"><b>${L}.</b> ${renderQuizFieldHtml(q[L])}</div>`;let parsed=parseHinhanhCellClient(q.HinhAnh||'');let tikzCode=parsed.tikz||q.Tikz||'';let img=q.HinhAnh?`<div class="aiGenCardImg">${buildQimgHtml(adminPreviewHinhAnhSrcFromCell(q.HinhAnh))}</div>`:'';let tikzEdit=tikzCode?`<div class="aiGenTikzEdit" style="margin:8px 0"><div style="font-size:12px;font-weight:800;margin-bottom:4px">📐 TikZ (sửa được)</div><textarea class="aiGenTikzTa" data-idx="${i}" rows="7" style="width:100%;font-family:monospace;font-size:11px" oninput="aiGenTikzInput(${i},this)">${escFormVal(tikzCode)}</textarea><button type="button" class="btnSmall btn2" style="margin-top:4px" onclick="aiGenRerenderTikz(${i})">🔄 Vẽ lại xem trước</button></div>`:'';let warn=q._ai_tikz_warning?`<div class="aiGenTikzWarn muted" style="font-size:12px;color:#b45309;margin:6px 0">${esc(q._ai_tikz_warning)}</div>`:'';return `<div class="aiGenCard"><div class="aiGenCardHead"><div><b>Câu ${i+1}</b><div class="aiGenCardMeta">${esc(q.Dang||'')} · ${esc(q.MucDo||'')} · ${esc(q.DangBaiTap||'')}</div></div><button type="button" class="btnRed aiGenRemove" onclick="removeAiGenQuestion(${i})">Xóa</button></div><div class="aiGenCardStem">${renderRichText(q.CauHoi||'')}</div>${img}${tikzEdit}${warn}${opts}<div class="aiGenAnswer">Đáp án: ${renderRichText(q.DapAn||'')}</div><div class="aiGenSolution"><b>Lời giải:</b><br>${renderRichText(q.LoiGiai||'')}</div></div>`}).join('');syncAiGenJson();typeset(box)}
function adminPreviewHinhAnhSrcFromCell(cell){let parsed=parseHinhanhCellClient(cell||'');if(parsed.tikz)return encodeTikzRawClient(parsed.tikz);return normalizeImageSrcClient(cell||'')}
function aiGenTikzInput(i,el){let q=AI_GEN_QUESTIONS[i];if(!q||!el)return;let parsed=parseHinhanhCellClient(q.HinhAnh||'');let img=parsed.img&&!/^tikzraw:/i.test(parsed.img)?parsed.img:'';q.HinhAnh=buildHinhanhCellClient(img,el.value);syncAiGenJson()}
async function aiGenRerenderTikz(i){let ta=document.querySelector('.aiGenTikzTa[data-idx="'+i+'"]');if(ta)aiGenTikzInput(i,ta);renderAiGenPreview()}
function removeAiGenQuestion(i){if(AI_GEN_BUSY)return;AI_GEN_QUESTIONS.splice(i,1);AI_GEN_SAVED=false;renderAiGenPreview();let st=document.getElementById('agStatus');if(st)st.textContent=`Còn ${AI_GEN_QUESTIONS.length} câu trong bản xem trước.`}
function clearAiGeneratedQuestions(){if(AI_GEN_BUSY)return;if(AI_GEN_QUESTIONS.length&&!confirm('Xóa toàn bộ bản xem trước hiện tại?'))return;AI_GEN_QUESTIONS=[];AI_GEN_SAVED=false;AI_GEN_REQUEST_ID='';renderAiGenPreview();let st=document.getElementById('agStatus');if(st)st.textContent='Chưa tạo câu. Điền đủ các trường có dấu *.'}
function applyAiGenJsonEdit(){if(AI_GEN_BUSY)return false;let raw=String((document.getElementById('agJson')||{}).value||'').trim();if(!raw){alert('JSON đang trống.');return false}try{let obj=JSON.parse(raw),arr=Array.isArray(obj)?obj:obj.questions;if(!Array.isArray(arr))throw new Error('JSON phải có questions: [...]');AI_GEN_QUESTIONS=arr.filter(x=>x&&typeof x==='object');AI_GEN_SAVED=false;renderAiGenPreview();let st=document.getElementById('agStatus');if(st)st.textContent=`Đã áp dụng JSON: ${AI_GEN_QUESTIONS.length} câu. Kiểm tra lại rồi bấm Lưu.`;return true}catch(e){alert('JSON không hợp lệ: '+e.message);return false}}
async function generateAiQuestionBank(){
  if(AI_GEN_BUSY)return;
  if(typeof adminEnsureAiReady==='function'&&!adminEnsureAiReady())return;
  let total=Math.max(1,Math.min(30,parseInt(val('agCount'),10)||1));
  if(AI_GEN_QUESTIONS.length&&!confirm('Tạo mới sẽ thay bản xem trước hiện tại. Tiếp tục?'))return;
  AI_GEN_QUESTIONS=[];AI_GEN_SAVED=false;
  AI_GEN_REQUEST_ID='AG_'+Date.now()+'_'+Math.random().toString(36).slice(2,9);
  let st=document.getElementById('agStatus'),warnings=[];
  setAiGenBusy(true);renderAiGenPreview();
  function agBatchSize(remaining,forceOne){
    if(forceOne)return 1;
    let p=adminChosenAiProvider();
    let cap=(p==='ANTHROPIC')?1:2;
    return Math.min(cap,remaining);
  }
  async function agFetchBatch(batch){
    let body=aiGenPayload(batch,AI_GEN_QUESTIONS.length);
    return await adminAiFetch('/api/admin/ai-generate-questions',body,{timeoutMs:100000});
  }
  function agMergeQuestions(list){
    let before=AI_GEN_QUESTIONS.length;
    let seen=new Set(AI_GEN_QUESTIONS.map(q=>String(q.CauHoi||'').toLowerCase().replace(/\s+/g,' ').trim()));
    for(let q of (list||[])){
      let k=String(q.CauHoi||'').toLowerCase().replace(/\s+/g,' ').trim();
      if(k&&!seen.has(k)){
        seen.add(k);AI_GEN_QUESTIONS.push(q);
        if(AI_GEN_QUESTIONS.length>=total)break;
      }
    }
    return AI_GEN_QUESTIONS.length-before;
  }
  try{
    let attempts=0,maxAttempts=Math.max(10,total*3+4),failStreak=0;
    while(AI_GEN_QUESTIONS.length<total&&attempts<maxAttempts){
      attempts++;
      let remaining=total-AI_GEN_QUESTIONS.length;
      let forceOne=failStreak>0;
      let batch=agBatchSize(remaining,forceOne);
      if(st)st.textContent=`Đang tạo đợt ${attempts} (${adminAiProviderShort(adminChosenAiProvider())}): ${batch} câu/lần — cần thêm ${remaining} (đã có ${AI_GEN_QUESTIONS.length}/${total})…`;
      try{
        let j=await agFetchBatch(batch);
        if(j.warnings&&j.warnings.length)warnings.push(...j.warnings);
        let added=agMergeQuestions(j.questions||[]);
        renderAiGenPreview();
        if(added>0){failStreak=0;continue;}
        if(batch>1){
          warnings.push('Đợt '+attempts+' không đủ câu — thử lại 1 câu…');
          failStreak++;
          continue;
        }
        failStreak++;
        if(failStreak>=3){warnings.push('Nhiều đợt liên tiếp không nhận câu mới; dừng.');break;}
      }catch(err){
        let msg=String((err&&err.message)||err||'');
        warnings.push('Đợt '+attempts+': '+msg.slice(0,180));
        failStreak++;
        if(st)st.textContent=`⚠ Lỗi đợt ${attempts}, đang thử lại với 1 câu… (đã có ${AI_GEN_QUESTIONS.length}/${total})\n`+msg.slice(0,220);
        if(failStreak>=5)throw err;
        await new Promise(r=>setTimeout(r,900));
      }
    }
    let done=AI_GEN_QUESTIONS.length;
    if(st)st.textContent=`Đã tạo ${done}/${total} câu.`+(warnings.length?'\n⚠ '+warnings.slice(-8).join('\n⚠ '):'')+(done<total?'\nCó thể bấm Tạo câu hỏi lần nữa để bổ sung.':'\nHãy xem trước, sửa JSON nếu cần rồi bấm Lưu tất cả.');
    if(!done)throw new Error(warnings.slice(-1)[0]||'AI chưa trả được câu hợp lệ. Thử Gemini + 2 câu/lần.');
  }catch(e){
    if(st)st.textContent=`Đã giữ ${AI_GEN_QUESTIONS.length} câu tạo được.\nLỗi: ${e.message||e}`;
    if(!AI_GEN_QUESTIONS.length)alert('Không tạo được câu: '+(e.message||e));
  }finally{setAiGenBusy(false);renderAiGenPreview()}
}

async function saveAiGeneratedQuestions(){
  if(AI_GEN_BUSY||AI_GEN_SAVED)return;
  // Đồng bộ JSON nếu có; không chặn lưu khi textarea trống nếu đã có bản xem trước trong RAM
  try{
    let ta=document.getElementById('agJson');
    let raw=String((ta&&ta.value)||'').trim();
    if(raw){
      if(!applyAiGenJsonEdit())return;
    }else if(AI_GEN_QUESTIONS.length){
      syncAiGenJson();
    }
  }catch(e){}
  if(!AI_GEN_QUESTIONS.length){alert('Chưa có câu trong bản xem trước để lưu.');return}
  if(!confirm('Lưu '+AI_GEN_QUESTIONS.length+' câu vào Google Sheet Cau_Hoi?\n\n• Trạng thái: CHƯA DUYỆT (ADMIN soát rồi mới duyệt)\n• App bỏ qua câu trùng nội dung.'))return;
  let st=document.getElementById('agStatus'),sb=document.getElementById('agSaveBtn');
  let created=0,skipped=[],warns=[],startRow=0,endRow=0,groupKey='';
  if(sb){sb.disabled=true;sb.textContent='⏳ Đang lưu…'}
  try{
    let n=AI_GEN_QUESTIONS.length;
    for(let i=0;i<n;i++){
      if(st)st.textContent='⏳ Đang lưu câu '+(i+1)+'/'+n+' lên Google Sheet…';
      if(sb)sb.textContent='⏳ '+(i+1)+'/'+n;
      let j=null,lastErr='';
      for(let attempt=0;attempt<3;attempt++){
        try{
          j=await api('/api/admin/ai-generate-save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({questions:[AI_GEN_QUESTIONS[i]]}),timeoutMs:25000},0);
          lastErr='';
          break;
        }catch(err){
          lastErr=String(err&&err.message||err||'');
          if(!/500|503|502|504|Internal Server|timeout|quá lâu|chưa nạp xong|loading/i.test(lastErr)||attempt>=2)throw err;
          if(st)st.textContent='⏳ Câu '+(i+1)+'/'+n+' — máy chủ bận, thử lại '+(attempt+2)+'/3…';
          await sleepMs(1400*(attempt+1));
        }
      }
      if(!j)throw new Error(lastErr||'Không lưu được câu.');
      created+=parseInt(j.created,10)||0;
      if(Array.isArray(j.skipped)&&j.skipped.length)skipped=skipped.concat(j.skipped);
      if(Array.isArray(j.hinhanh_warnings)&&j.hinhanh_warnings.length)warns=warns.concat(j.hinhanh_warnings);
      if(j.start_row){if(!startRow)startRow=j.start_row;endRow=j.end_row||j.start_row}
      if(j.group_key)groupKey=j.group_key;
    }
    let j={created:created,skipped:skipped,hinhanh_warnings:warns,start_row:startRow,end_row:endRow,group_key:groupKey};
    let skipN=skipped.length;
    if(created>0){
      AI_GEN_SAVED=true;
      let made=j.group_key||(AI_GEN_QUESTIONS[0]&&AI_GEN_QUESTIONS[0].MaDe)||'';
      let mon=val('agMon'),lop=val('agLop'),chuong=val('agChuong'),bai=val('agBaiHoc');
      if(st)st.textContent='✅ Đã lưu '+created+' câu vào Google Sheet'+(j.start_row?(' từ dòng '+j.start_row+' đến '+j.end_row):'')+(skipN?('\nBỏ qua '+skipN+' câu trùng/không hợp lệ.'):'')+(j.hinhanh_warnings&&j.hinhanh_warnings.length?('\n⚠ Ảnh: '+j.hinhanh_warnings.join(' · ')):'')+'\n📌 Câu mới = CHƯA DUYỆT — mở đề sẽ thấy ngay (viền cam + nhãn ⚠).';
      try{await refreshCatalogFromMeta()}catch(e){}
      try{
        if(mon)setSel('fMon',mon);refreshFilterOptions();
        if(lop)setSel('fLop',lop);refreshFilterOptions();
        if(chuong)setSel('fChuong',chuong);refreshFilterOptions();
        if(bai)setSel('fBaiHoc',bai);refreshFilterOptions();
        if(typeof renderCatalog==='function')renderCatalog();
      }catch(e2){}
      let go=confirm('Đã lưu '+created+' câu (CHƯA DUYỆT).\n\nBấm OK để mở đề và xem luôn câu vừa tạo (gồm chưa duyệt).');
      if(go){
        let item=null;
        if(made)item=CATALOG.find(x=>x.MaDe===made||x.GroupKey===made)||null;
        if(!item)item=CATALOG.find(x=>String(x.Mon||'').toLowerCase().replace(/\s+/g,' ').trim()===String(mon||'').toLowerCase().replace(/\s+/g,' ').trim()&&String(x.Lop||'').toLowerCase().replace(/\s+/g,' ').trim()===String(lop||'').toLowerCase().replace(/\s+/g,' ').trim()&&String(x.Chuong||'').toLowerCase().replace(/\s+/g,' ').trim()===String(chuong||'').toLowerCase().replace(/\s+/g,' ').trim()&&String(x.BaiHoc||'').toLowerCase().replace(/\s+/g,' ').trim()===String(bai||'').toLowerCase().replace(/\s+/g,' ').trim())||null;
        let openMade=item?(item.MaDe||item.GroupKey):made;
        if(openMade&&typeof openStartModal==='function'){
          openStartModal(openMade,'');
          setTimeout(function(){
            let ip=document.getElementById('chkIncludePending');
            if(ip){ip.checked=true;}
            if(typeof syncStartExamUi==='function')syncStartExamUi();
          },80);
        }else{
          alert('Đã lưu. Mở thẻ bài tương ứng → Bắt đầu (mặc định đã gồm câu chưa duyệt).');
        }
      }
    }else{
      AI_GEN_SAVED=false;
      let reason=(j.message||'')||(skipN?('Bỏ qua '+skipN+' câu (trùng nội dung?).'):'Không chèn được câu nào.');
      if(st)st.textContent='⚠ '+reason;
      alert('Không lưu được câu mới.\n'+reason);
    }
  }catch(e){
    AI_GEN_SAVED=false;
    let extra=created?('Đã ghi được '+created+' câu. Bấm lưu lại — câu trùng sẽ bỏ qua. '):'';
    if(st)st.textContent='❌ Không lưu được: '+extra+(e.message||e);
    alert('Không lưu được: '+extra+(e.message||e));
  }finally{
    if(sb){sb.textContent='💾 Lưu tất cả vào Google Sheet';sb.disabled=AI_GEN_SAVED||!AI_GEN_QUESTIONS.length}
  }
}


function quizLevelPrimary(q){let u=String((q&&q.MucDo)||'').toUpperCase();if(/\bVDC\b/.test(u))return'VDC';if(/\bVD\b/.test(u))return'VD';if(/\bTH\b/.test(u))return'TH';if(/\bNB\b/.test(u))return'NB';return''}
function quizSectionKey(q){q=applyResolvedDang(q||{});return String(q.Dang||'').trim()||'Câu hỏi'}
function quizSectionTitle(q){q=applyResolvedDang(q||{});return String(q.Dang||'').trim()||'Câu hỏi'}
function quizSectionLabel(i){if(!GROUP_BY_DANG||!QUESTIONS.length)return null;let q=applyResolvedDang(QUESTIONS[i]);if(i===0)return quizSectionTitle(q);let prev=applyResolvedDang(QUESTIONS[i-1]);return quizSectionKey(q)!==quizSectionKey(prev)?quizSectionTitle(q):null}
function enterQuizSession(j,made,lv,dgNorm,dg,applyClientFilter,dbtPref){if(getShareParams().de)clearShareQuery();SID=j.sid;GROUP_BY_DANG=j.group_by_dang!==false;RANDOM_PRACTICE=!!j.random_practice;EXAM_MODE=!!j.exam_mode;if(typeof j.admin==='boolean')USER.is_admin=j.admin;if(typeof j.can_view_solution_live==='boolean')USER.can_view_solution_live=j.can_view_solution_live;if(EXAM_MODE)USER.can_view_solution_live=false;if(typeof j.review_strict==='boolean'){META=META||{};META.strict_question_review=j.review_strict}QUESTIONS=(j.questions||[]).map(q=>applyResolvedDang(q));if(applyClientFilter&&(lv||dgNorm||dg)){QUESTIONS=applyQuizFilters(QUESTIONS,lv,dgNorm||dg)}if(!QUESTIONS.length){let item=CATALOG.find(x=>x.MaDe==made)||{};let mc=filterMatchCount(item,lv,dgNorm||dg);let msg=RANDOM_PRACTICE?'Không ghép được đề ngẫu nhiên.':'Không có câu';if(lv&&dg)msg+=` mức ${lv} dạng ${dgNorm||dg}`;else if(dg)msg+=` dạng ${dgNorm||dg}`;else if(lv)msg+=` mức ${lv}`;msg+=' trong đề này.';if(mc)msg+=`\n\nMục lục báo có ${mc} câu — bấm 🔄 Đồng bộ Sheet, Ctrl+F5, thử lại.`;else if(lv&&dg)msg+='\n\nThử bỏ Mức độ hoặc Dạng câu về Tất cả.';alert(msg);return}CURRENT_MADE=made;CURRENT_LEVEL=lv;CURRENT_DANG=dgNorm||dg||j.dang_filter||'';CURRENT_DANGBAITAP=String(dbtPref||j.dangbaitap_filter||'').trim();CUR=0;ANSWERS={};SUBMITTED=!!USER.is_admin&&!EXAM_MODE;RESULTS={};CHECKED={};LOCKED_Q={};COMPLETED_NOTICE=false;CORRECT_STREAK=0;hideStreakToast(true);HINT_BY_Q={};SIMILAR_BY_Q={};SIMILAR_LOADING=false;SIMILAR_LOADING_Q=null;FS_ANS_FORCE=null;FS_EXP_FORCE=null;VIP_Q_SHOW_ANS={};VIP_Q_SHOW_EXP={};LEARNING_OPEN_KIND='';LEARNING_CACHE={};DANG_SIMILARITY_CACHE={};LEARNING_LOADING=false;TRANSLATE_BY_Q={};TRANSLATE_KIND='CauHoi';TRANSLATE_LOADING=false;MINI_CALC_BY_Q={};document.getElementById('home').classList.add('hide');document.getElementById('quiz').classList.remove('hide');document.getElementById('resultBox').textContent=adminQuizStatusLine()||(USER.is_trial?'DÙNG THỬ: chỉ luyện đề FREE, không chấm điểm':'');let c=CATALOG.find(x=>x.MaDe==made)||{};let lvTag=lv?` | Mức: ${lv}`:'';let n=QUESTIONS.length;let dgShow=CURRENT_DANG||j.dang_filter||'';let dgTag=dgShow?` | Loại câu: ${dgShow}`:'';let dbtShow=CURRENT_DANGBAITAP||j.dangbaitap_filter||'';let dbtTag=dbtShow?` | Dạng BT: ${dbtFilterLabel(dbtShow)} (${n} câu)`:'';if(isDbtUnclassifiedFilter(dbtShow))dbtTag+=USER.is_admin?' · ADMIN: 🏷️ Gợi ý Dạng BT':'';let examTag=EXAM_MODE?' | 🧪 Kiểm tra':'';if(RANDOM_PRACTICE||j.random_title){document.getElementById('quizTitle').textContent=`🎲 ${j.random_title||'Tự luyện ngẫu nhiên'} | ${n} câu${lvTag}${examTag}`}else{document.getElementById('quizTitle').textContent=`${c.Mon||''} ${c.Lop?'- Lớp '+c.Lop:''} | ${c.De||c.BaiHoc||''}${lvTag}${dgTag}${dbtTag}${examTag}`}updateFilterBadge(lv,dgShow,n,dbtShow);updateShuffleBadge(j);startQuizTimer();updateAdminChrome();renderNav();renderQuestion();MOBILE_NAV_OPEN=false;syncMobileQuizChrome();if(j.trial_message)alert(j.trial_message)}
async function startQuiz(made,shuffleQ=false,shuffleA=false,level='',dang='',groupByDang=true,dangbaitap='',examMode=false,numQuestions=0,includePending,questionIds=null,examSpec=null,examAll=false){try{let lv=(level||val('fMucDo')||CURRENT_LEVEL||'').trim().toUpperCase();let dg=(dang||val('fDang')||CURRENT_DANG||'').trim();let dgNorm=dg?normDangClient(dg):'';let dbt=String(dangbaitap!=null?dangbaitap:(CURRENT_DANGBAITAP||val('fDangBaiTap')||'')).trim();let body={made,shuffle_q:shuffleQ?1:0,shuffle_a:shuffleA?1:0,level:lv,dang:dgNorm||dg,dangbaitap:dbt,group_by_dang:groupByDang?1:0,exam_mode:examMode?1:0,num_questions:numQuestions||0,exam_all:examAll?1:0,question_ids:questionIds||[],exam_spec:examSpec||{}};if(includePending===true||includePending===1)body.include_pending=1;else if(includePending===false||includePending===0)body.include_pending=0;else if(USER&&USER.is_admin&&!examMode)body.include_pending=1;let j=await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});enterQuizSession(j,made,lv,dgNorm,dg,true,dbt)}catch(e){alert('Không mở được đề: '+e.message)}}
function backHome(){stopQuizTimer();EXAM_MODE=false;FS_ANS_FORCE=null;FS_EXP_FORCE=null;MOBILE_NAV_OPEN=false;MOBILE_QUIZ_TOOLS_OPEN=false;MINI_CALC_OPEN=false;MINI_CALC_BY_Q={};VIP_Q_SHOW_ANS={};VIP_Q_SHOW_EXP={};AI_LG_BY_Q={};ADMIN_LG_DRAFT_BY_Q={};AI_LG_LOADING=-1;QUIZ_TTS_ON=false;stopQuizQuestionSpeech();LEARNING_OPEN_KIND='';LEARNING_CACHE={};LEARNING_LOADING=false;LEARNING_PANEL_COLLAPSED=false;TRANSLATE_BY_Q={};TRANSLATE_KIND='CauHoi';TRANSLATE_LOADING=false;TRANSLATE_SIDE_LOADING={};TRANSLATE_AUTO_QUEUE=[];TRANSLATE_SPEECH_CHUNKS=[];TRANSLATE_SPEECH_CHUNK_IDX=0;TRANSLATE_SPEECH_REPEAT=false;TRANSLATE_TTS_ACTIVE_BTN='';stopTranslateEnSpeech();unlockQuizPageScroll();document.body.classList.remove('mini-calc-open');let mcb=document.getElementById('miniCalcBackdrop');if(mcb)mcb.classList.add('hide');updateFilterBadge('','',null,'');document.getElementById('quiz').classList.add('hide');document.getElementById('home').classList.remove('hide');if(USER&&USER.is_admin){LDVL_ADMIN_STUDENT_MODE=false;if(typeof ldvlAdminNav==='function')ldvlAdminNav(document.getElementById('ldvlNavDash'),'ap-dash');}syncMobileQuizChrome();setTimeout(forceMobileHomeScroll,0);updateAdminChrome();try{mergeStudentProgressFromLocal();renderCatalog();if(window.__CATALOG_FLASH_SCOPE){flashCatalogLesson(window.__CATALOG_FLASH_SCOPE);window.__CATALOG_FLASH_SCOPE=null}}catch(e){}}
function ensureFullModeOverrides(){
    let fsId='LDVL_FS_OVR_V334';
    let prev=document.getElementById(fsId);
    if(prev) prev.remove();
    let legacy=document.getElementById('LDVL_FS_OVR');
    if(legacy) legacy.remove();
    let legacy2=document.getElementById('LDVL_FS_OVR_V329');
    if(legacy2) legacy2.remove();
    let legacy3=document.getElementById('LDVL_FS_OVR_V330');
    if(legacy3) legacy3.remove();
    let legacy4=document.getElementById('LDVL_FS_OVR_V331');
    if(legacy4) legacy4.remove();
    let legacy5=document.getElementById('LDVL_FS_OVR_V332');
    if(legacy5) legacy5.remove();
    let st=document.createElement('style');
    st.id=fsId;
    st.textContent=
        "@keyframes navActiveFlash{0%,100%{box-shadow:0 0 0 3px #2563eb,0 0 16px #3b82f699;transform:scale(1)}50%{box-shadow:0 0 0 7px #2563eb,0 0 26px #3b82f6dd;transform:scale(1.07)}}"+
        "@keyframes navOkActiveFlash{0%,100%{box-shadow:0 0 0 3px #fbbf24,0 0 14px #16a34a99;transform:scale(1)}50%{box-shadow:0 0 0 7px #fbbf24,0 0 22px #16a34acc;transform:scale(1.07)}}"+
        "@keyframes navBadActiveFlash{0%,100%{box-shadow:0 0 0 3px #fbbf24,0 0 14px #dc262699;transform:scale(1)}50%{box-shadow:0 0 0 7px #fbbf24,0 0 22px #dc2626cc;transform:scale(1.07)}}"+
        "@keyframes navRingBlink{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.15;transform:scale(1.14)}}"+
        "body.fullde-mode #navNums .num.ok{background:#16a34a!important;border-color:#15803d!important;color:#fff!important}"+
        "body.fullde-mode #navNums .num.bad{background:#dc2626!important;border-color:#b91c1c!important;color:#fff!important}"+
        "body.fullde-mode #navNums .num.active.ok{background:#16a34a!important;border-color:#15803d!important;color:#fff!important;animation:navOkActiveFlash 0.75s ease-in-out infinite!important}"+
        "body.fullde-mode #navNums .num.active.bad{background:#dc2626!important;border-color:#b91c1c!important;color:#fff!important;animation:navBadActiveFlash 0.75s ease-in-out infinite!important}"+
        "body.fullde-mode #navNums .num.active:not(.ok):not(.bad){animation:navActiveFlash 0.75s ease-in-out infinite!important;outline:none!important;border-color:#1d4ed8!important;border-width:3px!important}"+
        "body.fullde-mode #quiz .quizLayout{grid-template-columns:minmax(0,1fr) 220px!important;gap:8px!important;padding:0 8px 8px!important}"+
        "body.fullde-mode #qtext{flex:0 0 auto!important;min-height:0!important;padding:12px!important;overflow:visible!important;font-size:clamp(16px,2.4vw,22px)!important}"+
        "body.fullde-mode #options{flex:0 0 auto!important;margin-top:8px!important;position:relative!important;z-index:2!important;background:var(--bg)!important}"+
        "body.fullde-mode .mcqSplit,body.fullde-mode .mcqSplitDs,body.fullde-mode .mcqSplitTln{grid-template-columns:minmax(0,2fr) minmax(0,3fr)!important;gap:16px!important}"+
        "body.fullde-mode .mcqSplitDs{grid-template-columns:minmax(0,2fr) minmax(0,3fr)!important}"+
        "body.fullde-mode .mcqSplitTln{grid-template-columns:minmax(0,2fr) minmax(0,3fr)!important}"+
        "body.fullde-mode .mcqSplitImg .qimg{max-height:min(58vh,480px)!important}"+
        "body.fullde-mode .mcqSplitDs .mcqSplitImg .qimg{max-height:min(60vh,500px)!important}"+
        "body.fullde-mode .mcqSplitTln .mcqSplitImg .qimg{max-height:min(62vh,520px)!important}"+
        "body.fullde-mode .shortAnsInput{font-size:18px!important;width:auto!important;max-width:none!important;min-width:10em!important;flex:1 1 200px!important;text-align:left!important}"+
        "body.fullde-mode #solution .dsSolutionTn:not(.dsSolutionRows){grid-template-columns:1fr!important}"+
        "body.fullde-mode #solution .dsSolutionList,body.fullde-mode #solution .dsSolutionBody,body.fullde-mode #solution .loigiaiPreamble,body.fullde-mode #solution .solution{width:100%!important;max-width:100%!important;box-sizing:border-box!important}"+
        "@media(min-width:1200px){body.fullde-mode .dsSolutionDs:not(.dsSolutionRows){grid-template-columns:repeat(2,minmax(0,1fr))!important}body.fullde-mode .mcqSplit{grid-template-columns:minmax(0,2fr) minmax(0,3fr)!important}body.fullde-mode .mcqSplitDs{grid-template-columns:minmax(0,2fr) minmax(0,3fr)!important}body.fullde-mode .mcqSplitTln{grid-template-columns:minmax(0,2fr) minmax(0,3fr)!important}}"+
        "body.fullde-mode #qtext .qimg{max-height:min(42vh,280px)!important;display:block!important;margin:10px auto 12px!important}"+
        "body.fullde-mode #fsOnlyTools button{font-size:11px!important;padding:4px 7px!important}"+
        "body.fullde-mode{overflow:hidden!important;background:var(--bg)!important}"+
        "body.fullde-mode #quiz{height:100dvh!important;max-height:100dvh!important;overflow:hidden!important;display:flex!important;flex-direction:column!important;padding:0!important}"+
        "body.fullde-mode #quiz>.panel.row{display:none!important}"+
        "body.fullde-mode .quizToolbarStrip{flex:0 0 auto!important;margin:0!important;padding:0 6px 2px!important;background:var(--bg)!important}"+
        "body.fullde-mode .quizToolbarHead{margin:0!important;min-height:0!important;flex-direction:column!important;align-items:stretch!important;gap:3px!important}"+
        "body.fullde-mode #qid{font-size:15px!important;line-height:1.15!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}"+
        "body.fullde-mode .qidIdBadge,body.fullde-mode #qid .tag,body.fullde-mode #qid .mucdoBadge{font-size:11px!important;padding:1px 6px!important;line-height:1.15!important}"+
        "body.fullde-mode .quizToolsRow{display:none!important}"+
        "body.fullde-mode #fsOnlyTools{display:flex!important;flex:0 0 auto!important;justify-content:flex-end!important;align-items:center!important;gap:4px!important;margin:0!important;padding:3px 6px!important;border-radius:0!important;border-bottom:1px solid var(--border)!important;background:var(--surface)!important;overflow-x:auto!important;white-space:nowrap!important}"+
        "body.fullde-mode #fsOnlyTools button{font-size:10px!important;padding:3px 6px!important;min-height:25px!important;border-radius:7px!important;line-height:1.05!important;margin:0!important}"+
        "body.fullde-mode #fsQuizTimer{font-size:10px!important;padding:2px 6px!important;min-height:24px!important}"+
        "body.fullde-mode #quiz .quizLayout{flex:1 1 auto!important;min-height:0!important;grid-template-columns:minmax(0,1fr) minmax(260px,300px)!important;gap:8px!important;padding:0 8px 8px!important;overflow:hidden!important}"+
        "body.fullde-mode .quizQuestionPanel{height:100%!important;min-height:0!important;margin:0!important;padding:8px 10px!important;overflow:auto!important;border-radius:8px!important;width:100%!important;max-width:none!important;box-sizing:border-box!important}"+
        "body.fullde-mode #qtext{font-size:clamp(15px,1.65vw,20px)!important;line-height:1.38!important;padding:8px 10px!important;margin:0 0 6px!important;width:100%!important;max-width:none!important;word-break:break-word!important;overflow-wrap:anywhere!important}"+
        "body.fullde-mode #options{width:100%!important;max-width:none!important}"+
        "body.fullde-mode .quizSectionHead{font-size:20px!important;line-height:1.2!important;padding:8px 12px!important;margin:0 0 8px!important;border-radius:8px!important}"+
        "body.fullde-mode #options{margin-top:4px!important;background:transparent!important}"+
        "body.fullde-mode .mcqSplit,body.fullde-mode .mcqSplitDs,body.fullde-mode .mcqSplitTln{gap:8px!important;align-items:start!important}"+
        "body.fullde-mode .mcqSplitImg .qimg,body.fullde-mode .mcqSplitDs .mcqSplitImg .qimg,body.fullde-mode .mcqSplitTln .mcqSplitImg .qimg{max-height:min(54vh,430px)!important}"+
        "body.fullde-mode .mcqSplitOpts{min-height:0!important;overflow:visible!important}"+
        "body.fullde-mode .tfrow{padding:6px 8px!important;margin:4px 0!important;border-radius:8px!important}"+
        "body.fullde-mode .tfStmt{font-size:14px!important;line-height:1.28!important}"+
        "body.fullde-mode .tfOpt{font-size:11px!important;padding:3px 7px!important;min-width:52px!important;border-radius:7px!important}"+
        "body.fullde-mode #solution{max-height:none!important;overflow:visible!important;margin-top:8px!important;padding:10px 12px!important;width:100%!important;max-width:100%!important;box-sizing:border-box!important;flex-shrink:0!important;line-height:1.5!important;font-size:clamp(14px,1.5vw,17px)!important}"+
        "body.fullde-mode .fsNavPanel{margin:0!important;padding:8px!important;border-radius:8px!important;min-height:0!important;overflow:hidden!important;min-width:260px!important;display:flex!important;flex-direction:column!important;height:100%!important}"+
        "body.fullde-mode:not(.mobile-quiz-ui) .mobileNavDock{display:none!important}"+
        "body.fullde-mode:not(.mobile-quiz-ui) .mobileNavBody{display:flex!important;flex-direction:column!important;flex:1 1 auto!important;min-height:0!important;overflow:hidden!important;width:100%!important}"+
        "body.fullde-mode:not(.mobile-quiz-ui) #quiz .quizLayout>div:last-child{max-height:none!important;height:100%!important;min-width:260px!important}"+
        "body.fullde-mode #quiz .quizLayout>div:last-child{overflow:auto!important;min-width:0!important}"+
        "body.fullde-mode #quiz .quizLayout>div:last-child>.panel{overflow:hidden!important;width:100%!important;display:flex!important;flex-direction:column!important;min-height:0!important;height:100%!important}"+
        "body.fullde-mode #navMucDoLegend{flex:0 0 auto!important;margin:0 0 8px!important;width:100%!important}"+
        "body.fullde-mode #navNums{display:grid!important;grid-template-columns:repeat(4,minmax(44px,1fr))!important;gap:6px!important;overflow-x:hidden!important;overflow-y:auto!important;align-content:start!important;width:100%!important;flex:1 1 auto!important;min-height:140px!important}"+
        "body.fullde-mode #navNums .num{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;position:relative!important;visibility:visible!important;opacity:1!important;min-height:42px!important;font-size:13px!important;font-weight:700!important;padding:6px 4px!important;line-height:1.15!important;overflow:visible!important}"+
        "body.fullde-mode #navNums .num .navNumText{display:block!important;font-size:15px!important;font-weight:900!important;line-height:1.1!important;color:inherit!important;position:relative!important;z-index:2!important}"+
        "body.fullde-mode #navNums .num.active:not(.ok):not(.bad){animation:navActiveFlash 0.75s ease-in-out infinite!important;outline:none!important;border-color:#1d4ed8!important;border-width:3px!important;z-index:8!important;cursor:pointer!important}"+
        "body.fullde-mode #navNums .num.active.ok{background:#16a34a!important;border-color:#15803d!important;color:#fff!important;animation:navOkActiveFlash 0.75s ease-in-out infinite!important;z-index:8!important;cursor:pointer!important}"+
        "body.fullde-mode #navNums .num.active.bad{background:#dc2626!important;border-color:#b91c1c!important;color:#fff!important;animation:navBadActiveFlash 0.75s ease-in-out infinite!important;z-index:8!important;cursor:pointer!important}"+
        "body.fullde-mode #navNums .num.active::before{content:''!important;position:absolute!important;inset:-5px!important;border:3px solid #2563eb!important;border-radius:10px!important;animation:navRingBlink 0.75s ease-in-out infinite!important;pointer-events:none!important;z-index:0!important}"+
        "body.fullde-mode #navNums .num.active.ok::before,body.fullde-mode #navNums .num.active.bad::before{border-color:#fbbf24!important}"+
        "body.fullde-mode #navNums .num.active.ok .navNumText,body.fullde-mode #navNums .num.active.bad .navNumText{color:#fff!important}"+
        "body.fullde-mode #navNums .num.active:not(.ok):not(.bad) .navNumText{font-size:17px!important;color:#1e3a8a!important}"+
        "body.fullde-mode #navNums .num{cursor:pointer!important;pointer-events:auto!important}"+
        "body.fullde-mode.fsnav-hidden #quiz .quizLayout{grid-template-columns:1fr 0px!important}"+
        "body.fullde-mode.fsnav-hidden #quiz .quizLayout>div:last-child{display:none!important}"+
        "@media(max-width:900px){body.fullde-mode #quiz .quizLayout{grid-template-columns:minmax(0,1fr) 150px!important}body.fullde-mode #navNums{grid-template-columns:repeat(3,minmax(0,1fr))!important}}"+
        "@media(max-width:768px) and (orientation:portrait){body.fullde-mode .mcqSplit,body.fullde-mode .mcqSplitDs,body.fullde-mode .mcqSplitTln{grid-template-columns:1fr!important}body.fullde-mode .mcqSplitImg .qimg,body.fullde-mode .mcqSplitDs .mcqSplitImg .qimg,body.fullde-mode .mcqSplitTln .mcqSplitImg .qimg{max-height:min(52vh,420px)!important}body.fullde-mode #qtext .qimg{max-height:min(50vh,400px)!important}}"+
        "@media(orientation:landscape) and (max-height:520px){body.fullde-mode .mcqSplit,body.fullde-mode .mcqSplitDs,body.fullde-mode .mcqSplitTln{grid-template-columns:minmax(0,40%) minmax(0,60%)!important;gap:8px!important}body.fullde-mode .mcqSplitImg .qimg,body.fullde-mode .mcqSplitDs .mcqSplitImg .qimg,body.fullde-mode .mcqSplitTln .mcqSplitImg .qimg{max-height:min(calc(100dvh - 120px),240px)!important}body.fullde-mode .mcqSplitOpts{max-height:none!important;overflow:visible!important}body.fullde-mode .shortAnsCompact .shortAnsQtext{max-height:none!important;overflow:visible!important}body.fullde-mode .shortAnsFieldRow{position:sticky!important;bottom:0!important;background:var(--surface)!important;z-index:5!important}}"+
        "@media(max-width:760px){body.fullde-mode #quiz .quizLayout{grid-template-columns:1fr!important;grid-template-rows:minmax(0,1fr) auto!important;padding:0 4px 4px!important}body.fullde-mode #quiz .quizLayout>div:last-child{max-height:92px!important}body.fullde-mode #navNums{grid-template-columns:repeat(8,minmax(32px,1fr))!important;overflow-x:auto!important;overflow-y:hidden!important}body.fullde-mode #navNums .num{padding:3px 0!important;font-size:10px!important}body.fullde-mode #fsOnlyTools{gap:3px!important;padding:3px 4px!important}body.fullde-mode #fsOnlyTools button{font-size:9px!important;padding:3px 5px!important}body.fullde-mode #qtext{font-size:14px!important;padding:8px!important}body.fullde-mode #qtext .qimg{max-height:min(34vh,200px)!important}body.fullde-mode .opt{padding:6px 7px!important;font-size:13px!important;margin:3px 0!important}body.fullde-mode .tfrow{grid-template-columns:28px minmax(0,1fr) 34px!important;grid-template-areas:'lbl stmt opts'!important}body.fullde-mode .tfrow .dsCircle{grid-area:lbl!important;justify-self:center!important}body.fullde-mode .tfOpts{flex-direction:column!important;justify-content:flex-start!important;padding-left:0!important;width:34px!important}body.fullde-mode .tfLblFull{display:none!important}body.fullde-mode .tfLblShort{display:inline!important}body.fullde-mode .tfOpt{flex:0!important;width:100%!important;max-width:none!important;min-width:0!important;padding:5px 2px!important;font-size:11px!important;text-align:center!important}body.fullde-mode .tfOpt input{position:absolute!important;opacity:0!important;width:0!important;height:0!important}}";
    document.head.appendChild(st);
}
function syncFsNavBtn(){
    let btn=document.getElementById('btnFsNav');
    if(btn)btn.textContent=FS_NAV_HIDDEN?'☰ Hiện bảng':'☰ Ẩn bảng';
}
function ensureFsNavBtn(){
    let box=document.getElementById('fsOnlyTools');
    if(!box)return;
    let btn=document.getElementById('btnFsNav');
    if(!btn){
        btn=document.createElement('button');
        btn.type='button';
        btn.id='btnFsNav';
        btn.className='btn2';
        btn.onclick=toggleFsNav;
        box.appendChild(btn);
    }
    syncFsNavBtn();
}
function ensureNavInfo(){
    let panel=document.querySelector('.fsNavPanel');
    if(!panel) return null;
    let title=panel.querySelector('.fsNavTitle');
    if(title) title.textContent='Bảng câu hỏi';
    let nav=document.getElementById('navNums');
    let mount=(nav&&nav.parentElement)||panel.querySelector('.mobileNavBody')||panel;
    let info=document.getElementById('navInfo');
    if(!info){
        info=document.createElement('div');
        info.id='navInfo';
        info.className='fsNavInfo';
        info.style.cssText='display:block!important;color:var(--muted)!important;font-size:11px;line-height:1.35;margin:2px 0 8px;padding:6px;border:1px solid var(--border);border-radius:8px;max-height:72px;overflow:auto';
        safeInsertBefore(mount,info,nav);
    }else if(mount&&info.parentNode!==mount){
        safeInsertBefore(mount,info,nav);
    }
    return info;
}
function ensureNavLegend(){
    let nav=document.getElementById('navNums');
    if(!nav)return;
    let leg=document.getElementById('navMucDoLegend');
    if(!leg){
        leg=document.createElement('div');
        leg.id='navMucDoLegend';
        leg.className='navMucDoLegend';
        if(nav.parentElement) safeInsertBefore(nav.parentElement,leg,nav);
    }
    let statusLeg='<div class="navStatusLegend">'
      +'<span><i style="background:#f1f5f9;border:1px solid #e2e8f0"></i>Chưa làm</span>'
      +'<span><i style="background:var(--primary-bg);border:1px solid var(--primary)"></i>Đã chọn</span>'
      +'<span><i style="background:var(--pedu-correct)"></i>Đúng</span>'
      +'<span><i style="background:var(--pedu-incorrect)"></i>Sai</span>'
      +'<span><i style="background:#fff;box-shadow:inset 0 0 0 2px var(--pedu-warn)"></i>Đánh dấu xem lại</span>'
      +'</div>';
    leg.innerHTML=statusLeg+['NB','TH','VD','VDC'].map(n=>`<span class="navLvBadge ${mucdoBadgeClass(n)}" title="${escAttr(mucdoLabel(n))}">${n}</span>`).join('')+(isAdminViewer()?'<span class="navReviewLegend"><span class="navReviewMark ok">✓</span>đã duyệt</span><span class="navReviewLegend"><span class="navReviewMark no">!</span>chưa duyệt</span>':'');
}
function toggleFsNav(){
    if(!FULLDE_ON)return;
    FS_NAV_HIDDEN=!FS_NAV_HIDDEN;
    document.body.classList.toggle('fsnav-hidden',FS_NAV_HIDDEN);
    syncFsNavBtn();
    renderQuestion();
}
async function toggleQuizFullscreen(){let btn=document.getElementById('btnPresent');if(!FULLDE_ON){ensureFullModeOverrides();FULLDE_ON=true;FS_ANS_FORCE=null;FS_EXP_FORCE=null;FS_NAV_HIDDEN=false;MOBILE_QUIZ_TOOLS_OPEN=false;MOBILE_NAV_OPEN=false;document.body.classList.remove('fsnav-hidden');document.body.classList.add('fullde-mode');ensureFsNavBtn();syncFsNavBtn();updateAdminChrome();if(btn)btn.textContent='⤢ Thoát full đề';try{if(!document.fullscreenElement&&document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen()}catch(e){}syncMobileQuizChrome();renderQuestion();setTimeout(()=>{syncFulldeNavChrome();typesetQuizMathWithRetry(3,120)},180);return}FULLDE_ON=false;FS_ANS_FORCE=null;FS_EXP_FORCE=null;FS_NAV_HIDDEN=false;MOBILE_QUIZ_TOOLS_OPEN=false;MOBILE_NAV_OPEN=false;document.body.classList.remove('fsnav-hidden');document.body.classList.remove('fullde-mode');syncFsNavBtn();updateAdminChrome();if(btn)btn.textContent='📽 Full màn hình';try{if(document.fullscreenElement&&document.exitFullscreen)await document.exitFullscreen()}catch(e){}syncMobileQuizChrome();renderQuestion()}
function isAdminViewer(){return !!(USER.is_admin||String(USER.role||'').toUpperCase()==='ADMIN')} /* dùng cho nút Sửa câu, xem ĐA/LG ngay */
function isGithubBank(){return !!(META&&String(META.question_source||'')==='GITHUB')}
function canViewSolutionLive(){if(EXAM_MODE&&!SUBMITTED)return false;return !!(isAdminViewer()||USER.can_view_solution_live===true||['ADMIN','VIP','S.VIP'].includes(String(USER.role||'').toUpperCase()))}
function hasAttemptedQuestion(qIdx){qIdx=(qIdx==null||qIdx===undefined)?CUR:qIdx;if(LOCKED_Q[qIdx]||CHECKED[qIdx]||RESULTS[qIdx])return true;let q=applyResolvedDang(QUESTIONS[qIdx]);if(!q)return false;if(q.Dang==='Tự luận')return isQuestionDone(qIdx);return isQuestionChecked(qIdx)}
function canShowSolutionNow(){if(!canViewSolutionLive())return false;if(isAdminViewer())return true;return hasAttemptedQuestion(CUR)}
function canUseInfographicRole(){return !!(USER.is_admin||canViewSolutionLive())}
function isQuestionCorrect(qIdx){qIdx=(qIdx==null||qIdx===undefined)?CUR:qIdx;let r=SUBMITTED?RESULTS[qIdx]:(RESULTS[qIdx]||CHECKED[qIdx]);return !!(r&&r.ok===true)}
function canUnlockInfographic(qIdx){if(!canUseInfographicRole())return false;if(USER.is_admin)return true;return isQuestionCorrect(qIdx)}
function syncInfographicButtons(){let inQuiz=!!(document.getElementById('quiz')&&!document.getElementById('quiz').classList.contains('hide'));let roleOk=canUseInfographicRole()&&inQuiz;let ready=canUnlockInfographic(CUR);let lockTip='Trả lời đúng câu này mới mở khóa infographic.';for(let spec of [['btnFsInfographic',false],['btnInfographic',true]]){let b=document.getElementById(spec[0]);if(!b)continue;if(spec[1]&&!USER.is_admin){b.classList.add('hide');continue}b.classList.toggle('hide',!roleOk);if(!USER.is_admin||!spec[1]){b.disabled=!ready;b.title=ready?'Tạo prompt ảnh Gemini (poster hoặc trang vở) từ Sheet':lockTip;b.classList.toggle('vipSolLocked',!ready)}else{b.disabled=false;b.title='Tạo prompt ảnh Gemini — poster hoặc trang vở (ADMIN — không cần làm bài)'}}}
function syncExamSubmitButton(){let b=document.getElementById('btnExamSubmit');if(!b)return;let show=!!EXAM_MODE&&!SUBMITTED&&!(USER&&USER.is_trial);b.classList.toggle('hide',!show);b.disabled=!show}
function syncVipSolutionButtons(){syncExamSubmitButton();let roleOk=canViewSolutionLive()&&!(EXAM_MODE&&!SUBMITTED);let ready=canShowSolutionNow();let on=ready&&!!VIP_Q_SHOW_ANS[CUR],ex=ready&&!!VIP_Q_SHOW_EXP[CUR];let mobile=isMobileQuizUI();let lockTip='Làm và chấm câu này trước khi xem đáp án / lời giải.';let mv=document.getElementById('mobileDockVipBtns');if(mv)mv.classList.toggle('hide',!roleOk);let vt=document.getElementById('vipSolBtnsTop');if(vt)vt.classList.toggle('hide',!roleOk||mobile);for(let id of ['btnQuizShowAns','btnQuizShowExp']){let b=document.getElementById(id);if(b)b.classList.toggle('hide',!roleOk||mobile)}for(let id of ['btnFsShowAns','btnFsShowExp']){let b=document.getElementById(id);if(b)b.classList.toggle('hide',!roleOk||mobile)}for(let spec of [['btnMobileShowAns',on,'Ẩn ĐA','Đáp án'],['btnMobileShowExp',ex,'Ẩn LG','Lời giải'],['btnTopShowAns',on,'Ẩn ĐA','Đáp án'],['btnTopShowExp',ex,'Ẩn LG','Lời giải'],['btnQuizShowAns',on,'Ẩn ĐA','Đáp án'],['btnQuizShowExp',ex,'Ẩn LG','Lời giải'],['btnFsShowAns',on,'Ẩn ĐA','Đáp án'],['btnFsShowExp',ex,'Ẩn LG','Lời giải']]){let b=document.getElementById(spec[0]);if(!b)continue;b.classList.toggle('active',spec[1]);b.textContent=spec[1]?spec[2]:spec[3];if(!isAdminViewer()){b.disabled=!ready;b.title=ready?(spec[1]?'Ẩn':'Xem/ẩn')+(spec[0].includes('Exp')?' lời giải':' đáp án'):lockTip;b.classList.toggle('vipSolLocked',!ready)}}}
function toggleQuestionAnswer(e){if(e&&e.stopPropagation)e.stopPropagation();if(!canViewSolutionLive()){alert('Chỉ VIP / SVIP / ADMIN được xem đáp án khi làm bài.');return}if(!canShowSolutionNow()){alert('Hãy làm và chấm câu này trước khi xem đáp án.');return}VIP_Q_SHOW_ANS[CUR]=!VIP_Q_SHOW_ANS[CUR];renderQuestion()}
function toggleQuestionExplain(e){if(e&&e.stopPropagation)e.stopPropagation();if(!canViewSolutionLive()){alert('Chỉ VIP / SVIP / ADMIN được xem lời giải khi làm bài.');return}if(!canShowSolutionNow()){alert('Hãy làm và chấm câu này trước khi xem lời giải.');return}VIP_Q_SHOW_EXP[CUR]=!VIP_Q_SHOW_EXP[CUR];renderQuestion()}
function toggleAnswerInFullscreen(){toggleQuestionAnswer()}
function toggleExplainInFullscreen(){toggleQuestionExplain()}
function formatDsAnswerLine(q,r){if(r&&r.correct_display)return formatDsAnswerBadges(r.correct_display);if(r&&Array.isArray(r.rows)&&r.rows.length)return formatDsAnswerBadges(r.rows.map(x=>`${x.letter}=${x.correct==='Đ'?'Đúng':'Sai'}`).join(' · '));if(q.Dang==='Đúng sai'){let bits=[];for(let i=0;i<4;i++){let L=['A','B','C','D'][i];if(!q[L])continue;let v=String(q.DapAn||'').replace(/\u0110/g,'D').replace(/đ/g,'d');let parsed=(v.match(/[DSĐ]/gi)||[]);let c=parsed[i];if(c)c=c.toUpperCase()==='S'?'Sai':(c==='Đ'||c==='D'?'Đúng':c);bits.push(`${L}=${c||'?'}`)}return formatDsAnswerBadges(bits.join(' · '))}return formatHintDisplay(r.correct||q.DapAn||'')}
function saveShortAnswer(){let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||USER.is_admin||q.Dang!='Trả lời ngắn')return;if(SUBMITTED)return;let el=document.getElementById('shortAnsInput');if(!el)return;ANSWERS[CUR]=el.value;renderNav();notifyDoneIfNeeded();if(MINI_CALC_OPEN)syncMiniCalcDisplay()}
function focusShortAnsInput(el){if(!el||el.disabled||el.readOnly)return;if(document.activeElement===el)return;try{el.focus({preventScroll:true})}catch(e){try{el.focus()}catch(e2){}}}
function shortAnsTouchFocus(ev,el){if(!el||el.disabled)return;if(ev)ev.stopPropagation()}
function shortAnsOnFocus(el){if(!el)return;let panel=el.closest('.panel');if(panel)panel.classList.add('shortAnsInputActive')}
function shortAnsBlurCleanup(el){if(!el)return;setTimeout(function(){let panel=el.closest('.panel');if(panel&&!panel.contains(document.activeElement))panel.classList.remove('shortAnsInputActive')},120)}
function bindShortAnsInputMobile(el){if(!el||el._shortAnsMobileBound)return;el._shortAnsMobileBound=1;if(!isMobileQuizUI())return;el.addEventListener('touchend',function(e){e.stopPropagation()},{passive:true})}
function saveCurrent(){let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||USER.is_admin)return;if(LOCKED_Q[CUR]&&q.Dang!='Trả lời ngắn')return;let ready=false;if(q.Dang=='Trắc nghiệm'){let r=document.querySelector(`input[name="ans_${CUR}"]:checked`);if(r){ANSWERS[CUR]=r.value;ready=true}}else if(q.Dang=='Đúng sai'){let arr=[];let req=0,got=0;for(let L of ['A','B','C','D']){if(q[L])req++;let r=document.querySelector(`input[name="tf_${CUR}_${L}"]:checked`);if(q[L]&&r)got++;arr.push(r?r.value:'')}ANSWERS[CUR]=arr;ready=(req>0&&got===req)}else if(q.Dang=='Trả lời ngắn'){saveShortAnswer()}else{let el=document.getElementById('essayAns');if(el)ANSWERS[CUR]=el.value}renderNav();notifyDoneIfNeeded();if(ready)autoCheckCurrentQuestion()}
function commitShortAnswer(){saveShortAnswer();autoCheckCurrentQuestion()}
async function maybeCommitShortAnswerBeforeLeave(){let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||q.Dang!=='Trả lời ngắn'||USER.is_admin||USER.is_trial||SUBMITTED)return;if(CHECKED[CUR]||RESULTS[CUR]||LOCKED_Q[CUR])return;saveShortAnswer();let ans=ANSWERS[CUR];if(ans==null||String(ans).trim()==='')return;await autoCheckCurrentQuestion()}
function currentQuizWorkTitle(){let item=CATALOG.find(x=>x.MaDe===CURRENT_MADE)||{};if(item&&(item.Mon||item.BaiHoc||item.De))return examDisplayTitle(item);let q=QUESTIONS[0]||{};let de=String((q.De||q.BaiHoc||CURRENT_MADE||'Bài luyện tập')).trim();return de||'Bài luyện tập'}
function formatChosenAnswerBrief(q,ans){q=q||{};if(q.Dang==='Trắc nghiệm')return 'Chọn '+String(ans||'—');if(q.Dang==='Đúng sai'){let arr=Array.isArray(ans)?ans:[];let bits=[];for(let i=0;i<4;i++){if(!q[['A','B','C','D'][i]])continue;bits.push((['A','B','C','D'][i])+'='+(arr[i]||'?'))}return bits.join(' · ')||'Đã chọn Đúng/Sai'}if(q.Dang==='Trả lời ngắn')return 'TLN: '+String(ans||'').trim();return String(ans||'').trim()||'Đã trả lời'}
function hideStreakToast(instant){let el=document.getElementById('streakToast');if(!el)return;if(STREAK_TOAST_TIMER){clearTimeout(STREAK_TOAST_TIMER);STREAK_TOAST_TIMER=null}if(instant){el.classList.remove('show','hideDown');el.innerHTML='';return}el.classList.add('hideDown');el.classList.remove('show');STREAK_TOAST_TIMER=setTimeout(function(){el.classList.remove('show','hideDown');el.innerHTML='';STREAK_TOAST_TIMER=null},420)}
function showAdminLoiGiaiSavedToast(msg){msg=String(msg||'Lời giải đã được lưu').trim();let el=document.getElementById('streakToast');if(!el)return;if(STREAK_TOAST_TIMER){clearTimeout(STREAK_TOAST_TIMER);STREAK_TOAST_TIMER=null}if(ADMIN_LG_SAVED_TOAST_TIMER){clearTimeout(ADMIN_LG_SAVED_TOAST_TIMER);ADMIN_LG_SAVED_TOAST_TIMER=null}hideStreakToast(true);el.innerHTML='<div class="streakToastInner"><div class="streakToastCheer">✅ Đã lưu</div><div class="streakToastHead"><div class="streakToastBadge">💾</div><div><div class="streakToastTitle">'+esc(msg)+'</div><div class="streakToastSub">Đã ghi lên Google Sheet (cột R)</div></div></div><div class="streakToastBar" aria-hidden="true"><i></i></div></div>';el.classList.remove('hideDown');requestAnimationFrame(function(){el.classList.add('show')});ADMIN_LG_SAVED_TOAST_TIMER=setTimeout(function(){hideStreakToast(false);ADMIN_LG_SAVED_TOAST_TIMER=null},2600)}
function streakCheerText(streak){streak=parseInt(streak,10)||0;if(streak>=10)return'Xuất sắc! Chuỗi vàng '+streak+' câu';if(streak>=7)return'Quá đỉnh! Giữ đà nào';if(streak>=5)return'Tuyệt vời! Đang bùng nổ';if(streak>=3)return'Giỏi lắm! Tiếp tục nhé';return'Khởi đầu đẹp! Cố lên'}
function streakCheerIcon(streak){streak=parseInt(streak,10)||0;if(streak>=10)return'🏆';if(streak>=7)return'⚡';if(streak>=5)return'🔥';if(streak>=3)return'🌟';return'🎯'}
function formatStreakNow(){try{let d=new Date();let pad=n=>String(n).padStart(2,'0');return pad(d.getDate())+'/'+pad(d.getMonth()+1)+'/'+d.getFullYear()+' · '+pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds());}catch(e){return ''}}
function countCorrectAnswersNow(){let n=0;for(let i=0;i<(QUESTIONS||[]).length;i++){let r=RESULTS[i]||CHECKED[i];if(r&&r.ok===true)n++}return n}
function avgSecPerCorrectNow(){let n=countCorrectAnswersNow();if(n<=0)return 0;return Math.max(1,Math.round((QUIZ_ELAPSED||0)/n))}
function showStreakToast(streak,qIdx){if(!(USER&&USER.hoten)&&!(USER&&USER.mahs))return;if(streak<2)return;let el=document.getElementById('streakToast');if(!el)return;let name=String((USER&&USER.hoten)||(USER&&USER.mahs)||'Học sinh').trim();let lop=String((USER&&USER.lop)||'').trim();let q=applyResolvedDang(QUESTIONS[qIdx]||{});let work=currentQuizWorkTitle();let chosen=formatChosenAnswerBrief(q,ANSWERS[qIdx]);let cheer=streakCheerText(streak);let icon=streakCheerIcon(streak);let who=esc(name)+(lop?(' · Lớp '+esc(lop)):'');let when=formatStreakNow();let avgOk=avgSecPerCorrectNow();let avgOkTxt=avgOk?fmtTime(avgOk):'';let meta='Đúng liên tiếp <b>'+streak+'</b> câu · Câu '+(qIdx+1);let workHtml='<div><b>Bài làm:</b> '+esc(work)+'</div><div style="margin-top:3px">'+esc(chosen)+'</div>'+(avgOkTxt?('<div style="margin-top:4px">⚡ TB thời gian / câu đúng: <b>'+esc(avgOkTxt)+'</b></div>'):'');el.innerHTML='<div class="streakToastInner"><div class="streakToastCheer">'+icon+' '+esc(cheer)+'</div><div class="streakToastHead"><div class="streakToastBadge">'+icon+'</div><div><div class="streakToastTitle">'+who+'</div><div class="streakToastSub">Chuỗi đúng đang tăng — đừng dừng lại!</div></div></div><div class="streakToastMeta">'+meta+'</div><div class="streakToastWork">'+workHtml+'</div><div class="streakToastTime">🕒 Làm bài: '+esc(when||'—')+(avgOkTxt?(' · TB/câu đúng '+esc(avgOkTxt)):'')+'</div><div class="streakToastAd"><strong>📚 Lớp học Thầy Minh</strong>Zalo: <a href="https://zalo.me/0946111107" target="_blank" rel="noopener">0946.111.107</a></div><div class="streakToastBar" aria-hidden="true"><i></i></div></div>';el.classList.remove('hideDown','show');void el.offsetWidth;el.classList.add('show');if(STREAK_TOAST_TIMER){clearTimeout(STREAK_TOAST_TIMER);STREAK_TOAST_TIMER=null}STREAK_TOAST_TIMER=setTimeout(function(){hideStreakToast(false)},3000)}

function longestCorrectStreakFromResults(resultsMap){
  let best=0,cur=0;
  for(let i=0;i<QUESTIONS.length;i++){
    let r=resultsMap[i];
    if(r&&r.ok===true){cur++;if(cur>best)best=cur}else{cur=0}
  }
  return best;
}
function showExamFinishToast(j){
  if(USER&&(USER.is_admin||USER.is_trial))return;
  let el=document.getElementById('streakToast');if(!el)return;
  let name=String((USER&&USER.hoten)||(USER&&USER.mahs)||'Học sinh').trim();
  let lop=String((USER&&USER.lop)||'').trim();
  let work=currentQuizWorkTitle();
  let when=formatStreakNow();
  let score=(j&&j.score!=null)?j.score:'—';
  let ok=parseInt(j&&j.correct_count,10)||0;
  let tot=parseInt(j&&j.auto_count,10)||QUESTIONS.length||0;
  let streak=longestCorrectStreakFromResults(RESULTS);
  let cheer=streak>=5?'Hoàn thành xuất sắc!':(ok>=Math.ceil(tot*0.7)?'Nộp bài tốt lắm!':'Đã nộp bài kiểm tra');
  let icon=streak>=5?'🏆':'📝';
  let who=esc(name)+(lop?(' · Lớp '+esc(lop)):'');
  let meta='Điểm <b>'+esc(String(score))+'/10</b> · Đúng <b>'+ok+'</b>/'+tot+(streak>=2?(' · Chuỗi đúng dài nhất <b>'+streak+'</b>'):'');
  let ts=(j&&j.time_stats)||{};let avgTxt=ts.avg_text||'';let avgN=parseInt(ts.count,10)||0;let avgOkSec=parseInt(j&&j.avg_sec_per_correct,10)||0;if(!avgOkSec&&ok>0)avgOkSec=Math.max(1,Math.round((QUIZ_ELAPSED||0)/ok));let avgOkTxt=avgOkSec?fmtTime(avgOkSec):'';let histOk=ts.avg_per_correct_text||'';let histOkN=parseInt(ts.correct_sample_count,10)||0;let workHtml='<div><b>Bài kiểm tra:</b> '+esc(work)+'</div><div style="margin-top:3px">⏱ Thời gian làm: <b>'+esc(fmtTime(QUIZ_ELAPSED||0))+'</b>'+(avgOkTxt?(' · <b>TB / câu đúng: '+esc(avgOkTxt)+'</b>'):'')+'</div>'+(histOk&&histOkN?('<div style="margin-top:3px">📊 TB câu đúng các lượt trước: <b>'+esc(histOk)+'</b> ('+histOkN+' lượt)</div>'):'')+(avgTxt&&avgN?('<div style="margin-top:3px">TB cả bài: '+esc(avgTxt)+' ('+avgN+' lượt)</div>'):'');
  el.innerHTML='<div class="streakToastInner"><div class="streakToastCheer">'+icon+' '+esc(cheer)+'</div><div class="streakToastHead"><div class="streakToastBadge">'+icon+'</div><div><div class="streakToastTitle">'+who+'</div><div class="streakToastSub">Kết quả sau khi nộp bài</div></div></div><div class="streakToastMeta">'+meta+'</div><div class="streakToastWork">'+workHtml+'</div><div class="streakToastTime">🕒 Nộp bài: '+esc(when||'—')+'</div><div class="streakToastAd"><strong>📚 Lớp học Thầy Minh</strong>Zalo: <a href="https://zalo.me/0946111107" target="_blank" rel="noopener">0946.111.107</a></div><div class="streakToastBar" aria-hidden="true"><i></i></div></div>';
  el.classList.remove('hideDown','show');void el.offsetWidth;el.classList.add('show');
  if(STREAK_TOAST_TIMER){clearTimeout(STREAK_TOAST_TIMER);STREAK_TOAST_TIMER=null}
  STREAK_TOAST_TIMER=setTimeout(function(){hideStreakToast(false)},3500);
}
function noteAnswerStreak(ok,qIdx){if(USER&&(USER.is_admin||USER.is_trial))return;if(EXAM_MODE&&!SUBMITTED)return;if(ok===true){CORRECT_STREAK=(CORRECT_STREAK||0)+1;if(CORRECT_STREAK>=2)showStreakToast(CORRECT_STREAK,qIdx)}else if(ok===false){CORRECT_STREAK=0}}
async function autoCheckCurrentQuestion(){if(SUBMITTED||USER.is_admin||USER.is_trial)return;if(LOCKED_Q[CUR]||CHECKED[CUR]||RESULTS[CUR])return;let q=applyResolvedDang(QUESTIONS[CUR]);if(!q||q.Dang=='Tự luận')return;let ans=ANSWERS[CUR];if(ans==null)return;if(Array.isArray(ans)?ans.every(v=>!v):String(ans).trim()==='')return;LOCKED_Q[CUR]=true;let qIdx=CUR;try{let j=await api('/api/check-one',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:qIdx,answer:ans,...quizRestorePayload()})});CHECKED[qIdx]=j;RESULTS[qIdx]=j;if(QUESTIONS[qIdx]){if(j&&j.LoiGiai&&!String(QUESTIONS[qIdx].LoiGiai||'').trim())QUESTIONS[qIdx].LoiGiai=j.LoiGiai;if(j&&j.DapAn&&!String(QUESTIONS[qIdx].DapAn||'').trim())QUESTIONS[qIdx].DapAn=j.DapAn}noteAnswerStreak(j&&j.ok===true,qIdx);updateResultBox(qIdx);if(CUR===qIdx)renderQuestion()}catch(e){LOCKED_Q[qIdx]=false;if(CUR===qIdx)renderQuestion();alert(e.message||'Không kiểm tra được câu này.')}}
function ensureNavClickDelegation(){}
function bindNavNumClicks(){let nav=document.getElementById('navNums');if(!nav)return;nav.querySelectorAll('button.num[data-nav-idx]').forEach(btn=>{let idx=parseInt(btn.getAttribute('data-nav-idx'),10);if(!Number.isFinite(idx))return;btn.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}goQ(idx);return false}})}
function scrollNavActiveIntoView(smooth){let nav=document.getElementById('navNums');if(!nav)return;let btn=nav.querySelector('button.num.active');if(btn&&btn.scrollIntoView)btn.scrollIntoView({block:'nearest',inline:'nearest',behavior:smooth?'smooth':'auto'})}
function syncNavButtons(){let af=CUR<=0,al=CUR>=QUESTIONS.length-1;let p=document.getElementById('btnMobilePrev');if(p)p.disabled=af;let n=document.getElementById('btnMobileNext');if(n)n.disabled=al;document.querySelectorAll('.quizNavRowBelow button[onclick*="prevQ"]').forEach(b=>{b.disabled=af});document.querySelectorAll('.quizNavRowBelow button[onclick*="nextQ"]').forEach(b=>{b.disabled=al})}
function strictQuestionReviewEnabled(){return !!(META&&META.strict_question_review)}
function questionIsGithubSource(q){q=q||{};if(String(q._tex_rel||'').trim())return true;let src=String(q._source||'').toUpperCase().replace(/-/g,'_').replace(/\s+/g,'');if(['GITHUB','TEX','GITHUB_TEX','LOCAL_TEX','NGAN_HANG','NGANHANG'].indexOf(src)>=0)return true;try{if(typeof ldvlActiveQuestionSource==='function'&&ldvlActiveQuestionSource()==='GITHUB')return true}catch(e){}return false}
function questionIsReviewedForAdmin(q){if(questionIsGithubSource(q))return true;q=q||{};let st=normText(q.TrangThai||'');if(/da duyet|approved|^ok$|^1$|yes|true|xong|done/.test(st))return true;if(/chua duyet|pending|^no$|^0$|false|can duyet/.test(st))return false;if(typeof q.reviewed_sheet==='boolean')return q.reviewed_sheet;return false}
function questionIsReviewed(q){if(questionIsGithubSource(q))return true;if(isAdminViewer())return questionIsReviewedForAdmin(q);if(typeof q.reviewed==='boolean')return q.reviewed;let st=normText(q.TrangThai||'');if(/da duyet|approved|^ok$|^1$|yes|true|xong|done/.test(st))return true;if(/chua duyet|pending|^no$|^0$|false|can duyet/.test(st))return false;return !strictQuestionReviewEnabled()}
function navReviewMarkHtml(q){if(!isAdminViewer())return '';return questionIsReviewedForAdmin(q)?'<span class="navReviewMark ok" title="Đã duyệt — HS được làm">✓</span>':'<span class="navReviewMark no" title="⚠ CHƯA DUYỆT — học sinh không thấy">!</span>'}
function syncNavReviewMarks(){if(!isAdminViewer())return;let nav=document.getElementById('navNums');if(!nav)return;nav.querySelectorAll('button.num[data-nav-idx]').forEach(btn=>{let i=parseInt(btn.getAttribute('data-nav-idx'),10);if(!Number.isFinite(i))return;let q=QUESTIONS[i]||{};let wantOk=questionIsReviewedForAdmin(q);let mark=btn.querySelector('.navReviewMark');if(!mark){btn.insertAdjacentHTML('afterbegin',navReviewMarkHtml(q));return}mark.classList.toggle('ok',wantOk);mark.classList.toggle('no',!wantOk);mark.textContent=wantOk?'✓':'!';mark.title=wantOk?'Đã duyệt — HS được làm':'⚠ CHƯA DUYỆT — học sinh không thấy';btn.classList.toggle('q-reviewed',wantOk);btn.classList.toggle('q-unreviewed',!wantOk)})}
function syncPendingBannerForCurrent(){if(!isAdminViewer())return;let q=QUESTIONS[CUR]||{};let qtext=document.getElementById('qtext');if(!qtext)return;let old=qtext.querySelector('.qPendingBanner');let html=questionPendingBannerHtml(q);if(!html){if(old)old.remove();return}if(old)return;let head=qtext.querySelector('.quizSectionHead');if(head)head.insertAdjacentHTML('afterend',html);else qtext.insertAdjacentHTML('afterbegin',html)}
function questionReviewBadgeHtml(q){if(!isAdminViewer())return '';return questionIsReviewedForAdmin(q)?'<span class="qReviewBadge ok" title="Học sinh được làm">✓ Đã duyệt</span>':'<span class="qReviewBadge pending" title="Chưa duyệt — bấm «✅ Duyệt câu»">⚠ CHƯA DUYỆT</span>'}
function questionPendingBannerHtml(q){if(!isAdminViewer()||questionIsReviewedForAdmin(q))return '';return '<div class="qPendingBanner" role="status">⚠ <span>Câu này <b>CHƯA DUYỆT</b> — học sinh không làm được (STRICT). Soát xong bấm <b>✅ Duyệt câu</b>.</span></div>'}
function adminIncludePendingDefault(){return !!(USER&&USER.is_admin)}
function quizReviewCounts(){let ok=0,all=QUESTIONS.length;for(let i=0;i<all;i++)if(questionIsReviewedForAdmin(QUESTIONS[i]))ok++;return {ok,all,pending:all-ok}}
function syncNavReviewSummary(){if(!isAdminViewer())return;let c=quizReviewCounts();let el=document.getElementById('navReviewSummary');if(!el){let t=document.querySelector('.fsNavTitle');if(!t)return;el=document.createElement('div');el.id='navReviewSummary';el.className='navReviewSummary';t.insertAdjacentElement('afterend',el)}el.classList.toggle('hasPending',c.pending>0);el.textContent='Duyệt: ✓ '+c.ok+' / '+c.all+(c.pending?(' · ⚠ '+c.pending+' CHƯA DUYỆT'):' · đủ cả đề')}
function syncQuestionReviewToolbar(){if(!isAdminViewer())return;let q=QUESTIONS[CUR]||{};let btn=document.getElementById('btnQuestionReview');if(btn){let on=questionIsReviewedForAdmin(q);btn.textContent=on?'↩ Bỏ duyệt':'✅ Duyệt câu';btn.classList.toggle('btnReviewOn',on);btn.classList.toggle('btnReviewOff',!on);btn.title=on?'Bấm để đổi thành CHƯA DUYỆT trên Sheet':'Ghi cột TrangThai = ĐÃ DUYỆT'}let stat=document.getElementById('quizReviewStat');if(stat){let c=quizReviewCounts();stat.classList.remove('hide');stat.textContent='Duyệt: '+c.ok+'/'+c.all+(c.pending?(' · ⚠ '+c.pending+' CHƯA DUYỆT'):' · OK')+(strictQuestionReviewEnabled()?' · STRICT':'')}syncNavReviewSummary();syncNavReviewMarks();syncPendingBannerForCurrent();let qidEl=document.getElementById('qid');if(qidEl){let old=qidEl.querySelector('.qReviewBadge');if(old)old.remove();qidEl.insertAdjacentHTML('beforeend',questionReviewBadgeHtml(q))}let qPanel=document.querySelector('.quizQuestionPanel');if(qPanel)qPanel.classList.toggle('qPendingReview',!questionIsReviewedForAdmin(q));let editTr=document.getElementById('edit_TrangThai');if(editTr&&!document.getElementById('modal').classList.contains('hide')){editTr.value=normReviewFormVal(q.TrangThai||'');syncAdminChipGroup('TrangThai')}}
async function toggleQuestionReviewAtIndex(idx){if(!isAdminViewer())return;idx=parseInt(idx,10);if(!Number.isFinite(idx)||idx<0||idx>=QUESTIONS.length)return;let q=QUESTIONS[idx];if(!q||!(q._row||q.ID)){alert('Không xác định câu để duyệt.');return}let next=!questionIsReviewedForAdmin(q);try{let j=await api('/api/question/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row||0,id:q.ID||'',reviewed:next?1:0})});q.TrangThai=j.TrangThai||'';q.reviewed=!!j.reviewed;q.reviewed_sheet=!!j.reviewed;renderNav();syncQuestionReviewToolbar()}catch(e){alert('Không cập nhật duyệt: '+e.message)}}
async function toggleQuestionReview(){if(!isAdminViewer())return;let btn=document.getElementById('btnQuestionReview');if(btn){btn.disabled=true;btn.textContent='⏳…'}try{await toggleQuestionReviewAtIndex(CUR)}catch(e){}finally{if(btn){btn.disabled=false;syncQuestionReviewToolbar()}}}
async function approveAllQuestionsInQuiz(){if(!isAdminViewer())return;if(!QUESTIONS.length)return;let c=quizReviewCounts();if(!c.pending){alert('Tất cả '+c.all+' câu đã duyệt.');return}if(!confirm('Đánh dấu ĐÃ DUYỆT cho '+c.pending+' câu còn lại?\n\n'+(META&&META.question_source==='GITHUB'?'Lưu trên máy (ngân hàng .tex), không ghi Google Sheet.':'Ghi cột TrangThai trên Google Sheet.')))return;let btn=document.getElementById('btnQuestionReviewAll');if(btn){btn.disabled=true;btn.textContent='⏳…'}try{let items=QUESTIONS.filter(q=>(q._row||q.ID)&&!questionIsReviewedForAdmin(q)).map(q=>({row:q._row||0,ID:q.ID||''}));let j=await api('/api/question/review-bulk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items,reviewed:1,made:CURRENT_MADE||''})});let val=j.TrangThai||'ĐÃ DUYỆT';for(let q of QUESTIONS){q.TrangThai=val;q.reviewed=true;q.reviewed_sheet=true}renderNav();syncQuestionReviewToolbar();alert('Đã duyệt '+j.updated+' câu.')}catch(e){alert('Không duyệt hàng loạt: '+e.message)}finally{if(btn){btn.disabled=false;btn.textContent='✅ Duyệt cả đề'}}}
async function unapproveAllQuestionsInQuiz(){if(!isAdminViewer())return;if(!QUESTIONS.length)return;let c=quizReviewCounts();if(!c.ok){alert('Không có câu nào đang ở trạng thái đã duyệt.');return}if(!confirm('Đổi TẤT CẢ '+c.ok+' câu đã duyệt thành CHƯA DUYỆT?\n\nHọc sinh sẽ không làm được (khi bật STRICT).'))return;let btn=document.getElementById('btnQuestionUnreviewAll');if(btn){btn.disabled=true;btn.textContent='⏳…'}try{let items=QUESTIONS.filter(q=>(q._row||q.ID)&&questionIsReviewedForAdmin(q)).map(q=>({row:q._row||0,ID:q.ID||''}));let j=await api('/api/question/review-bulk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items,reviewed:0,made:CURRENT_MADE||''})});let val=j.TrangThai||'CHƯA DUYỆT';for(let q of QUESTIONS){if(questionIsReviewedForAdmin(q)){q.TrangThai=val;q.reviewed=false;q.reviewed_sheet=false}}renderNav();syncQuestionReviewToolbar();alert('Đã bỏ duyệt '+j.updated+' câu.')}catch(e){alert('Không cập nhật: '+e.message)}finally{if(btn){btn.disabled=false;btn.textContent='↩ Bỏ cả đề'}}}
function ensureFlaggedLoaded(){if(typeof SID==='undefined')return;if(FLAGGED_SID===SID)return;FLAGGED_SID=SID;try{let raw=localStorage.getItem('LDVL_FLAGGED_'+(SID||''));FLAGGED=raw?JSON.parse(raw):{}}catch(e){FLAGGED={}}}
function saveFlagged(){try{localStorage.setItem('LDVL_FLAGGED_'+(SID||''),JSON.stringify(FLAGGED))}catch(e){}}
function toggleFlagCurrent(){ensureFlaggedLoaded();FLAGGED[CUR]=!FLAGGED[CUR];saveFlagged();syncFlagBtn();renderNav()}
function syncFlagBtn(){ensureFlaggedLoaded();let on=!!FLAGGED[CUR];for(let id of ['btnFlagReview','btnFsFlagReview']){let b=document.getElementById(id);if(!b)continue;b.classList.toggle('flagOn',on);b.setAttribute('aria-pressed',on?'true':'false');b.title=on?'Bỏ đánh dấu xem lại':'Đánh dấu câu này để xem lại sau'}}
let QDESC_PINNED=false;
function toggleQuestionPin(){QDESC_PINNED=!QDESC_PINNED;let qt=document.getElementById('qtext');if(qt)qt.classList.toggle('qtextPinned',QDESC_PINNED);let b=document.getElementById('btnPinQuestion');if(b){b.classList.toggle('pinOn',QDESC_PINNED);b.setAttribute('aria-pressed',QDESC_PINNED?'true':'false');b.title=QDESC_PINNED?'Bỏ ghim đề':'Ghim đề (thu gọn phần đề khi cuộn)'}}
function renderNav(){ensureFlaggedLoaded();let html='';for(let i=0;i<QUESTIONS.length;i++){let q=QUESTIONS[i]||{};let sec=quizSectionLabel(i);if(sec&&!isMobileQuizUI()){let secCls='navSectionLbl';let sc=navSectionClass(sec);if(sc)secCls+=' '+sc;html+=`<div class="${secCls}">${esc(sec)}</div>`}let cls='num '+navMucDoClass(q.MucDo);if(isAdminViewer())cls+=questionIsReviewedForAdmin(q)?' q-reviewed':' q-unreviewed';if(i==CUR)cls+=' active';if(ANSWERS[i]!=null&&String(ANSWERS[i]).length)cls+=' answered';if((SUBMITTED||CHECKED[i])&&RESULTS[i])cls+=RESULTS[i].ok?' ok':' bad';if(FLAGGED[i])cls+=' flagged';let lv=mucdoPrimary(q.MucDo);let lvTip=lv?(mucdoIcon(lv)+' '+lv+' · '+mucdoLabel(lv)):'';let revTip=isAdminViewer()?(questionIsReviewedForAdmin(q)?' · Đã duyệt':' · Chưa duyệt · nhấp phải = menu'):'';let tip=(lvTip?(lvTip+' · '):'')+shortText(q.CauHoi||'',100)+revTip;html+=`<button type="button" class="${cls.trim()}" title="${escAttr(tip)}" data-nav-idx="${i}" aria-current="${i==CUR?'true':'false'}" onclick="goQ(${i});return false;">${navLvBadgeHtml(q.MucDo)}${navReviewMarkHtml(q)}<span class="navNumText">${i+1}</span></button>`}let nav=document.getElementById('navNums');nav.innerHTML=html;ensureNavLegend();bindNavNumClicks();if(isAdminViewer()){syncQuestionReviewToolbar();bindAdminNavContextMenu()}if(typeof normalizeNavSectionsByDangOnlyV264==='function')normalizeNavSectionsByDangOnlyV264();if(FULLDE_ON){syncFulldeNavChrome()}scrollNavActiveIntoView(!!FULLDE_ON);syncNavButtons()}
let ADMIN_NAV_CTX_IDX=-1;
function hideAdminNavCtxMenu(){let m=document.getElementById('adminNavCtxMenu');if(m)m.classList.add('hide');ADMIN_NAV_CTX_IDX=-1}
function ensureAdminNavCtxMenu(){let m=document.getElementById('adminNavCtxMenu');if(m)return m;m=document.createElement('div');m.id='adminNavCtxMenu';m.className='adminNavCtxMenu hide';m.innerHTML='<div id="adminNavCtxHead" class="adminNavCtxHead">Câu —</div><button type="button" class="adminNavCtxItem" id="adminNavCtxOpen" onclick="adminNavCtxGo()">📂 Mở câu</button><button type="button" class="adminNavCtxItem" id="adminNavCtxReview" onclick="adminNavCtxReview()">✅ Duyệt câu</button><button type="button" class="adminNavCtxItem" onclick="adminNavCtxEdit()">✏️ Sửa câu</button><button type="button" class="adminNavCtxItem danger" onclick="adminNavCtxDelete()">🗑 Xóa câu</button>';document.body.appendChild(m);if(!window.__ADMIN_NAV_CTX_BOUND){window.__ADMIN_NAV_CTX_BOUND=1;document.addEventListener('click',function(e){let m2=document.getElementById('adminNavCtxMenu');if(m2&&!m2.contains(e.target))hideAdminNavCtxMenu()});document.addEventListener('keydown',function(e){if(e.key==='Escape')hideAdminNavCtxMenu()});document.addEventListener('scroll',hideAdminNavCtxMenu,true)}return m}
function showAdminNavCtxMenu(e,idx){if(!isAdminViewer())return;idx=parseInt(idx,10);if(!Number.isFinite(idx)||idx<0||idx>=QUESTIONS.length)return;e.preventDefault();e.stopPropagation();hideAdminNavCtxMenu();let q=QUESTIONS[idx]||{};ADMIN_NAV_CTX_IDX=idx;let m=ensureAdminNavCtxMenu();let head=document.getElementById('adminNavCtxHead');if(head)head.textContent='Câu '+(idx+1)+' · '+(q.ID||'—')+' · dòng '+(q._row||'?');let openBtn=document.getElementById('adminNavCtxOpen');if(openBtn)openBtn.textContent='📂 Mở câu '+(idx+1);let revBtn=document.getElementById('adminNavCtxReview');if(revBtn)revBtn.textContent=questionIsReviewedForAdmin(q)?'↩ Bỏ duyệt':'✅ Duyệt câu';let x=Math.min(e.clientX,window.innerWidth-220);let y=Math.min(e.clientY,window.innerHeight-190);m.style.left=x+'px';m.style.top=y+'px';m.classList.remove('hide')}
function bindAdminNavContextMenu(){if(!isAdminViewer())return;let nav=document.getElementById('navNums');if(!nav||nav._adminCtxBound)return;nav._adminCtxBound=1;nav.addEventListener('contextmenu',function(e){if(!isAdminViewer())return;let btn=e.target.closest('button.num');if(!btn||!nav.contains(btn))return;let idx=parseInt(btn.getAttribute('data-nav-idx'),10);if(!Number.isFinite(idx))idx=[...nav.querySelectorAll('button.num')].indexOf(btn);if(idx<0)return;showAdminNavCtxMenu(e,idx)});ensureAdminNavCtxMenu()}
function adminNavCtxGo(){let idx=ADMIN_NAV_CTX_IDX;hideAdminNavCtxMenu();if(idx>=0)goQ(idx)}
function adminNavCtxEdit(){let idx=ADMIN_NAV_CTX_IDX;hideAdminNavCtxMenu();if(idx<0)return;goQ(idx);openEdit()}
async function adminNavCtxReview(){let idx=ADMIN_NAV_CTX_IDX;hideAdminNavCtxMenu();if(idx>=0)await toggleQuestionReviewAtIndex(idx)}
async function adminNavCtxDelete(){let idx=ADMIN_NAV_CTX_IDX;hideAdminNavCtxMenu();if(idx>=0)await deleteQuestionAtIndex(idx)}
async function goQ(i){i=parseInt(i,10);if(!Number.isFinite(i)||i<0||i>=QUESTIONS.length)return;if(i!==CUR&&LEARNING_OPEN_KIND==='translate'){stopTranslateEnSpeech();TRANSLATE_SPEECH_CHUNK_IDX=0;TRANSLATE_SPEECH_CHUNKS=[];LEARNING_OPEN_KIND=''}if(i!==CUR){await maybeCommitShortAnswerBeforeLeave();saveCurrent();CUR=i;renderQuestion();scrollNavActiveIntoView(true)}}
async function prevQ(){if(CUR>0){await maybeCommitShortAnswerBeforeLeave();saveCurrent();CUR--;renderQuestion()}else{alert('Đang ở câu đầu tiên của đề.')}}
async function nextQ(){if(CUR<QUESTIONS.length-1){await maybeCommitShortAnswerBeforeLeave();saveCurrent();CUR++;renderQuestion()}else{await maybeCommitShortAnswerBeforeLeave();saveCurrent();alert('✅ Đã hết đề. Thầy/các em có thể xem lại các câu.')}}

function finishHintRequest(qIdx,j){stopHintLoadingTimer();HINT_LOADING_SINCE=0;setHintLoading(false);if(CUR===qIdx){renderHintBox(j||HINT_BY_Q[qIdx]||{});if(j&&j.hide_5050&&j.hide_5050.length)applyAuto5050(j.hide_5050);let scrollEl=isAdminViewer()?document.getElementById('solution'):document.getElementById('hintBox');if(scrollEl&&!scrollEl.classList.contains('hide'))scrollEl.scrollIntoView({behavior:'smooth',block:'nearest'})}else{let hb=document.getElementById('hintBox');if(hb&&USER.can_quiz_ai_hint===false&&!HINT_BY_Q[CUR]&&!SIMILAR_BY_Q[CUR]){hb.classList.add('hide','hintBoxQuizDisabled');hb.innerHTML=''}if(hb){hb.classList.add('hide');hb.classList.remove('hintBoxLoading');hb.innerHTML=''}}let rb=document.getElementById('resultBox');if(rb&&CUR===qIdx){if(USER.is_admin){rb.textContent=isMobileQuizUI()?'ADMIN':'ADMIN: đang xem đáp án/lời giải';syncAdminResultBox()}else if(USER.is_trial)rb.textContent='DÙNG THỬ: chỉ luyện đề FREE, không chấm điểm';else rb.textContent=''}syncHintButtons(USER.can_ai_hint!==false)}
function renderQuestion(){invalidateQuizMath();if(window._QUIZ_TTS_CUR!==CUR){stopQuizQuestionSpeech();window._QUIZ_TTS_CUR=CUR}let q=applyResolvedDang(QUESTIONS[CUR]||{});if(!QUESTIONS.length){return}if(q.Dang=='Trắc nghiệm'){let hasOpt=false;for(let L of ['A','B','C','D'])if(q[L])hasOpt=true;if(!hasOpt&&looksShortAnswerClient(q))q.Dang='Trả lời ngắn'}renderNav();let canAi=(USER&&USER.can_ai_hint)!==false;try{ensureLearningQuickBar()}catch(e){console.warn('ensureLearningQuickBar',e)}syncLearningToggleUI();syncMiniCalcUI();let hb=document.getElementById('hintBox');if(hb){if(LEARNING_OPEN_KIND==='assistant'||LEARNING_OPEN_KIND==='openclaw'){LEARNING_OPEN_KIND='';hb.classList.add('hide');hb.classList.remove('aiAssistOpen','learningOpen');hb.innerHTML=''}else if(LEARNING_OPEN_KIND==='translate'){LEARNING_OPEN_KIND=''}else if(LEARNING_OPEN_KIND==='pdf'){try{renderLearningPdfPanel()}catch(e){console.warn('renderLearningPdfPanel',e)}}else if(LEARNING_OPEN_KIND==='theory'){loadLearningPanelContent('theory',false)}else if(LEARNING_OPEN_KIND==='method'){loadLearningPanelContent('method',false)}else if(HINT_LOADING&&HINT_LOADING_Q===CUR&&!HINT_BY_Q[CUR]){hb.classList.remove('learningOpen');showHintLoadingBox()}else if(canAi&&(HINT_BY_Q[CUR]||SIMILAR_BY_Q[CUR])){hb.classList.remove('learningOpen');hb.classList.remove('hintBoxLoading');renderHintBox(HINT_BY_Q[CUR]||{})}else if(canAi&&SIMILAR_LOADING&&SIMILAR_LOADING_Q===CUR){hb.classList.remove('learningOpen');hb.classList.remove('hide');hb.classList.remove('hintBoxLoading');hb.innerHTML='<b>📝 Tạo câu tương tự</b><div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang gọi AI…</b><div class="muted" style="margin-top:6px;font-size:13px">Soạn câu mới cùng dạng, có đáp án và lời giải…</div></div></div>'}else{hb.classList.add('hide');hb.classList.remove('hintBoxLoading');hb.classList.remove('learningOpen');hb.innerHTML=''}}let who=(USER&&USER.hoten||USER&&USER.mahs||'').trim();let prefix=who?`${who} | `:'';let idHtml=q.ID?`<button type="button" class="qidIdBadge" onclick="copyQuestionId()" title="Bấm để chép ID câu">ID: ${esc(q.ID)}</button>`:`<span class="qidIdBadge qidIdEmpty">ID: —</span>`;let solTag=q.has_full_solution?'<span class="tag solFullTag" style="font-size:11px;padding:2px 6px">📗 LG đầy đủ</span>':(q.sol_status==='partial'?'<span class="tag solPartTag" style="font-size:11px;padding:2px 6px">📝 LG một phần</span>':'');document.getElementById('qid').innerHTML=isMobileQuizUI()?`Câu ${CUR+1}/${QUESTIONS.length} · ${idHtml}${formatMucDoBadges(q.MucDo)?' · '+formatMucDoBadges(q.MucDo):''}${questionReviewBadgeHtml(q)}`:`${prefix?esc(prefix):''}Câu ${CUR+1}/${QUESTIONS.length} | ${idHtml} | ${formatMucDoBadges(q.MucDo)||'<span class="mucdoBadge mucdo-empty" title="Chưa ghi cột I">—</span>'} · <span class="qidDang">${esc(q.Dang||'')}</span>${q.NangLucVatLy?' · <span class="tag" title="Năng lực vật lí">'+esc(q.NangLucVatLy)+'</span>':''}${solTag?' · '+solTag:''}`;let solFigOnly=hinhanhIsSolutionFigure(q);let qImgHtml=(q.HinhAnh&&!solFigOnly)?buildQimgHtml(q.HinhAnh):'';let splitImg=usesImgSplit(q);let splitTln=isTlnImgSplit(q);let secLbl=quizSectionLabel(CUR);let secHead=(secLbl&&!isMobileQuizUI())?`<div class="quizSectionHead">📂 Phần: ${esc(secLbl)}</div>`:'';let qtextEl=document.getElementById('qtext');if(splitTln){if(qtextEl){qtextEl.innerHTML=secHead+questionPendingBannerHtml(q);qtextEl.classList.toggle('hide',!secHead&&!questionPendingBannerHtml(q))}}else{if(qtextEl){qtextEl.classList.remove('hide');qtextEl.innerHTML=secHead+questionPendingBannerHtml(q)+renderQuizFieldHtml(q.CauHoi||'')+(splitImg?'':qImgHtml)}};let b50El=document.getElementById('btn5050');if(b50El)b50El.disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!(USER&&USER.can_5050)||LOCKED_Q[CUR];let bfs=document.getElementById('btnFs5050');if(bfs)bfs.disabled=SUBMITTED||q.Dang!='Trắc nghiệm'||!(USER&&USER.can_5050)||LOCKED_Q[CUR];syncHintButtons(canAi);let html='';if(q.Dang=='Trắc nghiệm'){for(let L of ['A','B','C','D']){if(!q[L])continue;let checked=ANSWERS[CUR]==L?'checked':'';let cls='opt';let correct=(q.DapAn||'').toUpperCase().match(/[ABCD]/)?.[0]||'';if(isAdminViewer()&&!EXAM_MODE&&correct==L)cls+=' correct';let fb=RESULTS[CUR]||CHECKED[CUR];if((SUBMITTED||fb)&&fb){if(fb.chosen==L&&fb.ok===true)cls+=' correct';else if(fb.chosen==L&&fb.ok===false)cls+=' wrong';else if((SUBMITTED||!EXAM_MODE)&&fb.correct==L)cls+=' correct'}html+=`<label id="opt_${L}" class="${cls}"><input type="radio" name="ans_${CUR}" value="${L}" ${checked} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()">${dsCircleHtml(L)}<span>${renderQuizFieldHtml(stripOptionPrefix(q[L],L))}</span></label>`}if(mcqOptsUse2Col(q))html=`<div class="mcqOptsGrid2">${html}</div>`}else if(q.Dang=='Đúng sai'){let old=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:['','','',''];let crFb=RESULTS[CUR]||CHECKED[CUR];let rows=getDsCheckRows(q,crFb,old);let tfHead=`<div class="tfOptsHead"><span></span><span></span><span class="tfColHead"><span class="tfLblFull">Đúng · Sai</span><span class="tfLblShort">Đ<br>S</span></span></div>`;let tfRows='';for(let idx=0;idx<4;idx++){let L=['A','B','C','D'][idx];if(!q[L])continue;let cls='tfrow';let rr=rows.find(x=>x.letter===L);if((SUBMITTED||(!EXAM_MODE&&isQuestionChecked(CUR)))&&rr){if(rr.ok===true)cls+=' correct';else if(rr.ok===false)cls+=' wrong'}tfRows+=`<div class="${cls}">${dsCircleHtml(L)}<div class="tfStmt">${renderQuizFieldHtml(q[L])}</div><div class="tfOpts"><label class="tfOpt tfD" title="Đúng"><input type="radio" name="tf_${CUR}_${L}" value="Đ" ${old[idx]=='Đ'?'checked':''} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()"><span class="tfLbl tfLblFull">Đúng</span><span class="tfLbl tfLblShort">Đ</span></label><label class="tfOpt tfS" title="Sai"><input type="radio" name="tf_${CUR}_${L}" value="S" ${old[idx]=='S'?'checked':''} ${(SUBMITTED||LOCKED_Q[CUR])?'disabled':''} onchange="saveCurrent()"><span class="tfLbl tfLblFull">Sai</span><span class="tfLbl tfLblShort">S</span></label></div></div>`}html=tfHead+tfRows}else if(q.Dang=='Trả lời ngắn'){html=buildShortAnsHtml(q,{compact:true,withQuestion:splitTln})}else{html=`<div style="margin-top:10px"><label style="display:block;font-weight:800;margin-bottom:8px">✏️ Bài làm tự luận</label><textarea id="essayAns" style="width:100%;min-height:120px;padding:10px;border:1px solid var(--border);border-radius:8px" placeholder="Nhập bài làm tự luận..." ${SUBMITTED?'disabled':''} oninput="saveCurrent()">${esc(ANSWERS[CUR]||'')}</textarea></div>`}let optEl=document.getElementById('options');if(optEl){optEl.classList.toggle('mcqSplitWrap',splitImg);let splitCls='mcqSplit'+(q.Dang==='Đúng sai'?' mcqSplitDs':(splitTln?' mcqSplitTln':''));let splitOptsCls='mcqSplitOpts'+(mcqOptsUseSplitCol1(q)?' mcqSplitOptsCol1':'');optEl.innerHTML=splitImg?`<div class="${splitCls}"><div class="mcqSplitImg">${qImgHtml}</div><div class="${splitOptsCls}">${html}</div></div>`:html}if(!canShowSolutionNow()){VIP_Q_SHOW_ANS[CUR]=false;VIP_Q_SHOW_EXP[CUR]=false}else if(isAdminViewer()){VIP_Q_SHOW_ANS[CUR]=true;VIP_Q_SHOW_EXP[CUR]=true}let canShowAns=canShowSolutionNow(),canShowExp=canShowSolutionNow();let showAns=canShowAns&&!!VIP_Q_SHOW_ANS[CUR],showExp=canShowExp&&!!VIP_Q_SHOW_EXP[CUR];let showBox=showAns||showExp;document.getElementById('solution').classList.toggle('hide',!showBox);if(showBox){let r=RESULTS[CUR]||{};let parts=[];if(showAns){let ansLine=q.Dang==='Đúng sai'?formatDsAnswerLine(q,null):(q.Dang==='Trắc nghiệm'?formatMcqAnswerBadge(q.DapAn||''):renderRichText(q.DapAn||''));parts.push(`<b>Đáp án:</b> ${ansLine}`)}if(showExp)parts.push(buildQuizLoiGiaiHtml(q,r));let solEl=document.getElementById('solution');solEl.innerHTML=parts.join('<br>');solEl.setAttribute('data-lg-qid',String(q.ID||CUR));try{if(window.MathJax&&MathJax.typesetClear)MathJax.typesetClear([solEl])}catch(e){}}syncQuestionMucDoChrome(q);syncAdminLearningBoard();if(USER&&USER.is_admin&&String(q.DangBaiTap||'').trim())loadDangSimilarityReport(q,false,false);updateAdminChrome();try{syncQuizDebateBtn();syncQuizDebatePanel()}catch(e0){}typesetQuizMathWithRetry(FULLDE_ON?3:2,60);syncMobileQuizToolbar();syncVipSolutionButtons();syncInfographicButtons();syncQuizReadBtn();syncAdminLoiGiaiEditBtn();try{bindQuizTtsVoices();fillQuizTtsVoiceSelect();syncQuizAiTalkBtn();syncQuizDebateBtn()}catch(e){};syncAdminLoiGiaiPanel();updateResultBox(CUR);if(MINI_CALC_OPEN)syncMiniCalcDisplay();syncQuestionReviewToolbar();bindShortAnsInputMobile(document.getElementById('shortAnsInput'));}
async function use5050(){saveCurrent();try{let j=await api('/api/fifty',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:CUR,...quizRestorePayload()})});for(let L of j.hide||[]){let el=document.getElementById('opt_'+L);if(el)el.classList.add('hidden5050')}let b50=document.getElementById('btn5050');if(b50)b50.disabled=true;let bfs=document.getElementById('btnFs5050');if(bfs)bfs.disabled=true;let msg=`50-50: đã loại ${((j.hide||[]).join(', ')||'2 đáp án sai')}`;document.getElementById('resultBox').textContent=msg;document.getElementById('resultBox').style.color='#1d4ed8';if(j.message&&!String(j.message).toLowerCase().includes('đã loại'))alert(j.message)}catch(e){alert(e.message)}}
function adminAiProviderLabel(p){p=String(p||'').toUpperCase();if(p==='ANTHROPIC'||p==='CLAUDE')return 'Claude';if(p==='OPENAI'||p==='GPT')return 'GPT';return 'Gemini'}
function adminAiProviderShort(p){p=String(p||'').toUpperCase();if(p==='ANTHROPIC')return '✨ Claude';if(p==='OPENAI')return '✅ GPT';return '⚡ Gemini'}
const LDVL_ADMIN_AI_LS='LDVL_ADMIN_AI_PROVIDER';
function adminChosenAiProvider(){try{let p=localStorage.getItem(LDVL_ADMIN_AI_LS)||localStorage.getItem('LDVL_EDIT_LATEX_AI')||localStorage.getItem('LDVL_BULK_DBT_AI')||String((USER&&USER.admin_ai_provider)||'GEMINI');p=String(p||'GEMINI').toUpperCase();return ['GEMINI','ANTHROPIC','OPENAI'].includes(p)?p:'GEMINI'}catch(e){return 'GEMINI'}}
function adminSaveChosenAiProvider(p){p=String(p||'GEMINI').toUpperCase();if(!['GEMINI','ANTHROPIC','OPENAI'].includes(p))p='GEMINI';try{localStorage.setItem(LDVL_ADMIN_AI_LS,p);localStorage.setItem('LDVL_EDIT_LATEX_AI',p);localStorage.setItem('LDVL_BULK_DBT_AI',p)}catch(e){}document.querySelectorAll('.adminAiProviderSelect,.editLatexAiSelect').forEach(s=>{if(s)s.value=p});if(typeof bulkDbtSyncAiBadge==='function')bulkDbtSyncAiBadge();if(typeof bulkLevelSyncAiBadge==='function')bulkLevelSyncAiBadge();syncAdminAiProviderChrome();syncHintButtons(USER&&USER.can_ai_hint!==false);syncEditHintButtonLabel();syncAdminResultBox();try{if(typeof syncQuizAiTalkBtn==='function')syncQuizAiTalkBtn()}catch(e){}return p}
function syncAdminAiProviderChrome(){if(!isAdminViewer())return;let p=adminChosenAiProvider();document.querySelectorAll('.adminAiProviderSelect,.editLatexAiSelect').forEach(s=>{if(s)s.value=p});let st=document.getElementById('adminAiProviderStatus');if(st){let bits=['Đang chọn: '+adminAiProviderShort(p)];if(p==='ANTHROPIC'&&!_loadAnthropicKey())bits.push('⚠ Cần nạp Claude key (sk-ant-…)');if(p==='OPENAI'&&USER.admin_openai_ready===false)bits.push('⚠ Chưa có OPENAI_API_KEY trên server');st.textContent=bits.join(' · ')}document.querySelectorAll('[id^="btn_ai_fix_"]').forEach(btn=>{let f=String(btn.id||'').replace('btn_ai_fix_','');if(f)btn.textContent='🤖 '+adminAiProviderShort(p)})}
function ensureAdminAiProviderUi(){if(!isAdminViewer())return;let row=document.getElementById('adminAiProviderRow');if(row)row.classList.remove('hide');if(!document.getElementById('adminAiProviderQuizWrap')){let host=document.querySelector('.quizToolbarRowAdmin')||document.querySelector('.quizAdminTools');if(host){let wrap=document.createElement('span');wrap.id='adminAiProviderQuizWrap';wrap.className='adminAiProviderWrap';wrap.innerHTML='<label class="adminReviewModeWrap adminAiProviderWrap" title="Chọn AI ADMIN"><span class="muted">AI</span> <select id="adminAiProviderSelectQuiz" class="adminAiProviderSelect" onchange="adminSaveChosenAiProvider(this.value)"><option value="GEMINI">⚡ Gemini</option><option value="ANTHROPIC">✨ Claude</option><option value="OPENAI">✅ GPT</option></select></label>';host.insertBefore(wrap,host.firstChild)}}syncAdminAiProviderChrome()}
function initAdminChosenAiProvider(){try{adminSaveChosenAiProvider(adminChosenAiProvider())}catch(e){}ensureAdminAiProviderUi()}
function adminEnsureAiReady(prov){prov=String(prov||adminChosenAiProvider()).toUpperCase();if(prov==='ANTHROPIC'){let k=_loadAnthropicKey();if(!k||!k.startsWith('sk-ant-')){alert('⚠️ Chọn Claude nhưng chưa có Anthropic key.\n\nVào 🔑 Key AI → dán sk-ant-... → Lưu → 🧪 Kiểm tra kết nối AI.');return false}}if(prov==='OPENAI'&&USER.admin_openai_ready===false){alert('⚠️ Chọn GPT nhưng server chưa có OPENAI_API_KEY trong .env.\nRestart CHAY_UNG_DUNG.bat sau khi thêm key.');return false}if(prov==='GEMINI'&&USER.ai_has_keys===false&&!USER.is_admin){alert('⚠️ Chưa có Gemini key.');return false}return true}
function adminSetEditAiStatus(html){let el=document.getElementById('editAiStatusLine');if(!el){el=document.createElement('div');el.id='editAiStatusLine';el.style.cssText='font-size:12px;margin:4px 0 8px;line-height:1.45';let soat=document.getElementById('editAdminSoatBar');if(soat&&soat.parentNode)soat.parentNode.insertBefore(el,soat.nextSibling)}if(!html){el.classList.add('hide');el.innerHTML='';return}el.classList.remove('hide');el.innerHTML=html}
function adminAiProvider(){return adminChosenAiProvider()}
function ensureAdminQuotaModal(){let m=document.getElementById('adminQuotaModal');if(m)return m;m=document.createElement('div');m.id='adminQuotaModal';m.className='modal hide';m.innerHTML='<div class="modalBox" style="max-width:480px"><h3>⚠️ Hết quota GEMINI</h3><p id="adminQuotaMsg" class="muted" style="margin:10px 0;line-height:1.5">Đã hết quota Gemini. Bạn muốn chạy GPT để tiếp tục không?</p><div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap"><button type="button" id="adminQuotaUseGpt" class="btn">✅ Chạy GPT</button><button type="button" id="adminQuotaWait" class="btn2">⏳ Đợi quota hồi</button></div></div>';document.body.appendChild(m);return m}
async function adminApiPost(url,body,opts){
  opts=opts||{};
  if(isAdminViewer()){
    if(!opts.admin_ai_provider)opts.admin_ai_provider=adminChosenAiProvider();
    if(opts.admin_ai_allow_gpt_fallback==null)opts.admin_ai_allow_gpt_fallback=true;
  }
  let bulk=!!opts.bulk;
  let maxTry=bulk?4:1;
  if(opts.tries!=null){maxTry=Math.max(1,(parseInt(opts.tries,10)||0)+1)}
  if(isAdminViewer()){
    let lastErr=null;
    for(let attempt=0;attempt<maxTry;attempt++){
      try{
        return await adminAiFetch(url,body||{},{signal:opts.signal,timeoutMs:opts.timeoutMs,admin_ai_provider:opts.admin_ai_provider,admin_ai_allow_gpt_fallback:opts.admin_ai_allow_gpt_fallback});
      }catch(e){
        lastErr=e;
        let msg=String(e&&e.message||e);
        let billing=/billing|not active|payment|402|account has been/i.test(msg);
        if(billing&&isAdminViewer()){
          let cur=String(opts.admin_ai_provider||'').toUpperCase();
          let alts=cur==='OPENAI'?['GEMINI','ANTHROPIC']:cur==='ANTHROPIC'?['GEMINI','OPENAI']:['ANTHROPIC','OPENAI'];
          for(let alt of alts){
            if(alt===cur)continue;
            try{
              return await adminAiFetch(url,body||{},{signal:opts.signal,admin_ai_provider:alt,admin_ai_allow_gpt_fallback:true});
            }catch(e2){lastErr=e2}
          }
        }
        let retryable=/429|quota|rate|timeout|HTTP 5|temporarily|service unavailable|deadline|billing|not active/i.test(msg);
        if(retryable&&attempt+1<maxTry){
          await sleepMs(1100*(attempt+1)+Math.floor(Math.random()*500));
          continue;
        }
        throw e;
      }
    }
    throw lastErr||new Error('AI request failed');
  }
  return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{}),signal:opts.signal,timeoutMs:opts.timeoutMs||0},bulk?3:2);
}
function editQuestionAiInternetLatex(){let q=(typeof readQuestionFormData==='function')?readQuestionFormData():(currentQuestion?currentQuestion():{});return ['CauHoi: '+(q.CauHoi||''),'A: '+(q.A||''),'B: '+(q.B||''),'C: '+(q.C||''),'D: '+(q.D||''),'DapAn: '+(q.DapAn||''),'LoiGiai: '+(q.LoiGiai||'')].join('\n')}
function buildAdminAiInternetPrompt(kind,body,url){body=body||{};let q=(typeof readQuestionFormData==='function')?readQuestionFormData():(currentQuestion?currentQuestion():{});let field=body.field||kind||'LoiGiai';let text=body.text||q[field]||q.LoiGiai||q.CauHoi||'';let mode=body.format_mode||'';return 'Bạn là trợ lý sửa LaTeX đề Toán/Vật lí. Hãy sửa nội dung sau cho MathJax hiển thị đúng, trình bày gọn, mỗi bước xuống dòng riêng. Không dùng dấu * markdown. Chỉ trả về NỘI DUNG ĐÃ SỬA để tôi dán lại vào ô '+field+'.\n\nDạng sửa: '+(mode||field)+'\nAPI app vừa hết quota nên tôi dùng AI Internet thủ công.\n\nNGỮ CẢNH CÂU HỎI:\n'+editQuestionAiInternetLatex()+'\n\nNỘI DUNG CẦN SỬA:\n'+text}
function openAdminAiInternetFallback(body,url){openGoogleAiModeCustom(buildAdminAiInternetPrompt('quota',body,url),editQuestionAiInternetLatex())}
function showAdminGeminiQuotaDialog(openaiAvailable){return new Promise(resolve=>{let m=ensureAdminQuotaModal();let box=m.querySelector('.modalBox');let gptBtn=document.getElementById('adminQuotaUseGpt');if(box&&!document.getElementById('adminQuotaUseInternet')){let b=document.createElement('button');b.type='button';b.id='adminQuotaUseInternet';b.className='btnGreen';b.textContent='🌐 AI Internet';let wrap=gptBtn&&gptBtn.parentElement;if(wrap)wrap.insertBefore(b,gptBtn);else box.appendChild(b)}let msg=document.getElementById('adminQuotaMsg');if(msg)msg.textContent=openaiAvailable?'Hết quota Gemini. Chọn AI Internet để không tốn quota app, hoặc chạy GPT nếu muốn tự điền ngay.':'Hết quota Gemini. Chọn AI Internet để sửa thủ công ngoài app, hoặc đợi quota hồi rồi thử lại.';if(gptBtn)gptBtn.classList.toggle('hide',!openaiAvailable);let done=choice=>{m.classList.add('hide');resolve(choice)};m.classList.remove('hide');let internetBtn=document.getElementById('adminQuotaUseInternet');if(internetBtn)internetBtn.onclick=()=>done('internet');if(gptBtn)gptBtn.onclick=()=>done('gpt');let waitBtn=document.getElementById('adminQuotaWait');if(waitBtn)waitBtn.onclick=()=>done('wait');m.onclick=e=>{if(e.target===m)done('wait')}})}
async function adminAiFetch(url,body,opts){opts=opts||{};let timeoutMs=parseInt(opts.timeoutMs||48000,10)||48000;if(/ai-generate-questions|ai-generate-model/.test(String(url||''))&&timeoutMs<90000)timeoutMs=90000;let abortTimer=null;let ownCtrl=null;if(!opts.signal){ownCtrl=new AbortController();opts=Object.assign({},opts,{signal:ownCtrl.signal});abortTimer=setTimeout(()=>{try{ownCtrl.abort()}catch(e){}},timeoutMs)}let payload=Object.assign({},body||{});if(isAdminViewer()){if(!payload.admin_ai_provider&&!opts.admin_ai_provider)payload.admin_ai_provider=adminChosenAiProvider();else if(opts.admin_ai_provider)payload.admin_ai_provider=opts.admin_ai_provider;if(opts.admin_ai_allow_gpt_fallback||payload.admin_ai_allow_gpt_fallback==null)payload.admin_ai_allow_gpt_fallback=true}
// Luôn đính kèm Anthropic key từ localStorage nếu có (server cần để dùng Claude)
let _antKey=_loadAnthropicKey();if(_antKey)payload.anthropic_key=_antKey;
let method=opts.method||'POST';let headers=Object.assign({'Content-Type':'application/json'},opts.headers||{});let r,j,txt;try{r=await fetch(url,{method,headers,body:JSON.stringify(payload),signal:opts.signal});txt=await r.text();j={};try{j=txt?JSON.parse(txt):{}}catch(e){j={error:adminFriendlyHttpError(txt,r&&r.status)}}}catch(fetchErr){if(fetchErr&&fetchErr.name==='AbortError')throw new Error('Quá '+Math.round(timeoutMs/1000)+'s — AI không phản hồi. Thử lại, giảm số câu mỗi lần, hoặc đổi Gemini.');throw new Error(typeof apiNetworkErrorMsg==='function'?apiNetworkErrorMsg(fetchErr):(fetchErr&&fetchErr.message||'Failed to fetch'))}finally{if(abortTimer)clearTimeout(abortTimer)}
function adminFriendlyHttpError(txt,status){
  let s=String(txt||'').replace(/\s+/g,' ').trim();
  if(/Internal Server Error|502 Bad Gateway|504 Gateway|Cloudflare|gunicorn|Worker|timeout/i.test(s)||(status>=500)){
    return 'Server lỗi tạm thời (HTTP '+(status||500)+') khi gọi AI.\nThường do request quá lâu trên Render (worker bị cắt).\n\nApp sẽ tự thử lại với ít câu hơn. Hoặc giảm còn 2 câu/lần rồi bấm Tạo lại.';
  }
  if(s.startsWith('<')||/<html/i.test(s))return 'Server trả HTML lỗi (HTTP '+(status||'?')+') — không phải JSON. Thử lại (app tự giảm số câu).';
  return s.slice(0,280)||('HTTP '+(status||'?'));
}
// Bắt lỗi billing/account inactive — tự chuyển Gemini/Claude
let errLow=String(j.error||'').toLowerCase();let isBillingErr=errLow.includes('billing')||errLow.includes('not active')||errLow.includes('payment')||errLow.includes('402')||errLow.includes('account has been');
if(isBillingErr){
  let cur=String(opts.admin_ai_provider||'').toUpperCase();
  let alts=cur==='OPENAI'?['GEMINI','ANTHROPIC']:cur==='ANTHROPIC'?['GEMINI','OPENAI']:['_ANTHROPIC','OPENAI'];
  for(let alt of alts){
    if(alt.startsWith('_'))alt=_loadAnthropicKey()?'ANTHROPIC':'';
    if(!alt||alt===cur)continue;
    let st=document.getElementById('bulkDbtStatus')||document.getElementById('bulkLevelStatus');
    if(st)st.textContent='⚠ Lỗi billing AI → thử '+alt+'…';
    try{return adminAiFetch(url,body,{...opts,admin_ai_provider:alt,admin_ai_allow_gpt_fallback:true})}catch(e2){}
  }
}
if(j.gemini_quota_exhausted){
  let antKey=_loadAnthropicKey();
  if(antKey){
    try{
      let st=document.getElementById('bulkDbtStatus')||document.getElementById('bulkLevelStatus');
      if(st)st.textContent='⚡ Gemini hết quota → tự chuyển Claude...';
      return adminAiFetch(url,body,{...opts,admin_ai_provider:'ANTHROPIC',admin_ai_allow_gpt_fallback:true});
    }catch(e2){}
  }
  if(j.openai_available){
    try{return adminAiFetch(url,body,{...opts,admin_ai_provider:'OPENAI',admin_ai_allow_gpt_fallback:true})}catch(e2){}
  }
  let choice=await showAdminGeminiQuotaDialog(!!j.openai_available);
  if(choice==='internet'){openAdminAiInternetFallback(body,url);throw new Error('Đã mở AI Internet.')}
  if(choice==='gpt'&&j.openai_available)return adminAiFetch(url,body,{...opts,admin_ai_provider:'OPENAI',admin_ai_allow_gpt_fallback:true});
  throw new Error('Hết quota GEMINI — chưa có key dự phòng.');
}
if(!r.ok||j.error)throw new Error(j.error||('HTTP '+r.status));return j}
async function adminAiFetchForm(url,buildFd,opts){opts=opts||{};async function run(useGpt){let fd=buildFd(!!useGpt);if(useGpt){fd.set('admin_ai_provider','OPENAI');fd.set('admin_ai_allow_gpt_fallback','true')}let r=await fetch(url,{method:'POST',body:fd,signal:opts.signal});let txt=await r.text();let j={};try{j=txt?JSON.parse(txt):{}}catch(e){j={error:txt.slice(0,220)}}if(j.gemini_quota_exhausted){let antKey=_loadAnthropicKey();if(antKey){try{return run('claude')}catch(e2){}}if(j.openai_available)return run(true);let choice=await showAdminGeminiQuotaDialog(!!j.openai_available);if(choice==='internet'){openAdminAiInternetFallback({},url);throw new Error('Đã mở AI Internet.')}if(choice==='gpt'&&j.openai_available)return run(true);throw new Error('Hết quota GEMINI.')}if(!r.ok||j.error)throw new Error(j.error||('HTTP '+r.status));return j}return run(false)}
function adminUsesGpt(){return isAdminViewer()&&adminAiProvider()==='OPENAI'}
function adminAiModelLabel(){let m=String(USER.openai_admin_model||'gpt-4o').trim();return m||'gpt-4o'}
function isSvipViewer(){return !!(USER.is_svip||String(USER.role||'').toUpperCase()==='S.VIP')}
function svipAiProvider(){return 'GEMINI'}
function svipUsesGpt(){return false}
function svipAiModelLabel(){let m=String(USER.openai_hint_model||'gpt-4.1-mini').trim();return m||'gpt-4.1-mini'}
function getAdminReviewMode(){let el=document.getElementById('adminReviewModeEdit')||document.getElementById('adminReviewMode')||document.getElementById('adminReviewModeFs');return (el&&el.value)||ADMIN_REVIEW_MODE||'fast'}
function adminReviewIsFast(){return getAdminReviewMode()==='fast'}
function adminReviewLoadingNote(){return adminReviewIsFast()?'~8–20 giây (2 mục)':'~20–26 giây (3 mục + DIỄN GIẢI)'}
function onAdminReviewModeChange(val){ADMIN_REVIEW_MODE=(val==='fast')?'fast':'full';try{localStorage.setItem('adminReviewMode',ADMIN_REVIEW_MODE)}catch(e){}['adminReviewMode','adminReviewModeFs','adminReviewModeEdit'].forEach(id=>{let el=document.getElementById(id);if(el)el.value=ADMIN_REVIEW_MODE});syncHintButtons(USER.can_ai_hint!==false);syncEditHintButtonLabel();syncAdminResultBox()}
function syncAdminReviewModeUI(){let adm=!!isAdminViewer();let mob=isMobileQuizUI();['adminReviewModeWrap','adminReviewModeFsWrap'].forEach(id=>{let w=document.getElementById(id);if(w)w.classList.toggle('hide',!adm||!mob)});let editSel=document.getElementById('adminReviewModeEdit');if(editSel)editSel.value=ADMIN_REVIEW_MODE||'fast'}
function syncEditHintButtonLabel(){let btn=document.getElementById('btnEditHint');if(!btn)return;let lbl=hintButtonDisplayLabel();btn.textContent=lbl;btn.title=hintButtonTitle();btn.classList.toggle('hintBtnIconOnly',isMobileQuizUI()&&isAdminViewer());btn.disabled=HINT_LOADING||SIMILAR_LOADING}
function hintButtonIcon(){if(isAdminViewer())return adminReviewIsFast()?'⚡':'🔍';return '💡'}
function hintButtonLabel(){if(isAdminViewer()){let fast=adminReviewIsFast();let prov=adminChosenAiProvider();if(prov==='OPENAI')return fast?'⚡ Soát nhanh GPT':'🔍 Soát đề GPT';if(prov==='ANTHROPIC')return fast?'⚡ Soát nhanh Claude':'🔍 Soát đề Claude';return fast?'⚡ Soát nhanh Gemini':'🔍 Soát đề Gemini'}return USER.is_vip?'💡 AI Gemini':'💡 Gợi ý AI'}
function hintButtonDisplayLabel(){return isMobileQuizUI()&&isAdminViewer()?hintButtonIcon():hintButtonLabel()}
function hintButtonTitle(){return hintButtonLabel()}
function adminQuizStatusLine(){if(!isAdminViewer())return '';if(isMobileQuizUI())return 'ADMIN · '+adminAiProviderShort(adminChosenAiProvider());let mode=adminReviewIsFast()?'Nhanh':'Kỹ';let prov=adminChosenAiProvider();if(prov==='OPENAI'){let ok=USER.admin_openai_ready!==false;return ok?`ADMIN · Soát ${mode} GPT (${adminReviewIsFast()?'gpt-4.1-mini':adminAiModelLabel()})`:`ADMIN · GPT chưa có key`}if(prov==='ANTHROPIC'){let ok=!!_loadAnthropicKey();return ok?`ADMIN · Soát ${mode} Claude`:`ADMIN · Claude chưa có key`}return `ADMIN · Soát ${mode} Gemini`}
function syncAdminResultBox(){let rb=document.getElementById('resultBox');if(!rb)return;let st=adminQuizStatusLine();rb.classList.toggle('adminStatusCompact',!!st&&isMobileQuizUI());if(st&&!rb.dataset.userResult)rb.textContent=st}
function syncHintButtons(canAi){let lbl=hintButtonDisplayLabel();let full=hintButtonTitle();let mob=isMobileQuizUI();syncAdminReviewModeUI();let adm=isAdminViewer();for(let id of ['btnHint','btnFsHint']){let b=document.getElementById(id);if(!b)continue;b.classList.toggle('hide',!adm||!mob);if(HINT_LOADING)continue;b.classList.remove('btnHintLoading');b.textContent=lbl;b.title=full;b.classList.toggle('hintBtnIconOnly',mob&&adm);b.disabled=SIMILAR_LOADING}syncEditHintButtonLabel();let canSim=!!USER.can_quiz_similar&&!(EXAM_MODE&&!SUBMITTED);for(let id of ['btnSimilar','btnFsSimilar']){let b=document.getElementById(id);if(!b)continue;b.classList.toggle('hide',!canSim);if(SIMILAR_LOADING&&SIMILAR_LOADING_Q===CUR){b.disabled=true;b.textContent='⏳ Đang tạo…'}else{b.disabled=HINT_LOADING||!canSim;b.textContent=id==='btnFsSimilar'?'📝 tương tự':'📝 Tạo câu tương tự'}}}
function setHintLoading(on,qIndex){HINT_LOADING=!!on;HINT_LOADING_Q=on?qIndex:null;let lbl=hintButtonDisplayLabel();let full=hintButtonTitle();for(let id of ['btnHint','btnFsHint','btnEditHint']){let b=document.getElementById(id);if(!b)continue;if(on){if(!b.dataset.hintLabel)b.dataset.hintLabel=b.textContent||lbl;if(!b.dataset.hintTitle)b.dataset.hintTitle=b.title||full;b.disabled=true;if(id==='btnEditHint'){b.classList.add('btnHintLoading');b.innerHTML=isMobileQuizUI()&&isAdminViewer()?'<span class="hintSpin"></span>':'<span class="hintSpin"></span> Đang soát…'}else{b.classList.add('btnHintLoading');b.innerHTML='<span class="hintSpin"></span> AI đang xử lý…'}}else{b.classList.remove('btnHintLoading');b.textContent=b.dataset.hintLabel||lbl;b.title=b.dataset.hintTitle||full;delete b.dataset.hintLabel;delete b.dataset.hintTitle;b.classList.toggle('hintBtnIconOnly',isMobileQuizUI()&&isAdminViewer()&&(id==='btnEditHint'||id==='btnHint'||id==='btnFsHint'));b.disabled=SIMILAR_LOADING}}syncHintButtons(USER.can_ai_hint!==false)}
function setSimilarLoading(on,qIndex){SIMILAR_LOADING=!!on;SIMILAR_LOADING_Q=on?qIndex:null;syncHintButtons(USER.can_ai_hint!==false)}
function adminHintNeedsSave(qIdx){qIdx=qIdx==null?CUR:qIdx;let j=HINT_BY_Q[qIdx];return !!(j&&j.admin_review&&!ADMIN_HINT_SAVED[qIdx])}
function markAdminHintSaved(qIdx){qIdx=qIdx==null?CUR:qIdx;ADMIN_HINT_SAVED[qIdx]=true;if(HINT_BY_Q[qIdx])HINT_BY_Q[qIdx].admin_sheet_confirmed=true}
function dsDapAnFromSolutionText(text,q){q=q||currentQuestion();let chunks=extractAbcdSolutionChunks(String(text||''));let m={};chunks.forEach(c=>{if(c.verdict)m[c.letter]=c.verdict});let letters=['A','B','C','D'].filter(L=>q[L]);let bits=letters.filter(L=>m[L]).map(L=>`${L}=${m[L]}`);return bits.length?bits.join(' · '):''}
function hintSectionDiengiaiRaw(){let t=hintRawText().split('📋 Tham chiếu Sheet')[0];let m=t.match(/1\.\s*DIỄN GIẢI[^\n]*\n([\s\S]*?)(?=2\.\s*GIẢI TỪNG Ý|\Z)/i);return m?m[1].trim():''}
function hintSectionTungYRaw(){let t=hintRawText().split('📋 Tham chiếu Sheet')[0];let m3=t.match(/2\.\s*(?:GIẢI TỪNG Ý|KẾT LUẬN PHƯƠNG ÁN ĐÚNG|LỜI GIẢI|GIẢI CHI TIẾT)[^\n]*\n([\s\S]*?)(?=3\.\s*CHỐT ĐÁP ÁN|\Z)/i);if(m3)return m3[1].trim();let m2=t.match(/1\.\s*(?:GIẢI TỪNG Ý|LỜI GIẢI|KẾT LUẬN PHƯƠNG ÁN)[^\n]*\n([\s\S]*?)(?=2\.\s*CHỐT ĐÁP ÁN|\Z)/i);return m2?m2[1].trim():''}
function hintSection1Raw(){return hintSectionTungYRaw()}
function hintAiLoigiaiCombined(){let dg=hintSectionDiengiaiRaw();let ty=hintSectionTungYRaw();if(dg&&ty)return dg+'\n\n'+ty;return ty||dg||''}
function hintLoigiaiFromHintBody(){let t=hintRawText();let m=t.match(/Lời giải Sheet \(cột R\):\s*\n([\s\S]*?)(?=\n\n📋 Tham chiếu Sheet|$)/i);return m?m[1].trim():''}
function hintAiLoigiaiRaw(){let j=HINT_BY_Q[CUR]||{};let q=QUESTIONS[CUR]||{};if(j.admin_review){let combined=hintAiLoigiaiCombined();if(combined)return combined;let sug=String(j.suggested_loigiai||'').trim();if(sug)return sug}let cand=[String(j.suggested_loigiai||'').trim(),hintAiLoigiaiCombined(),hintSection1Raw(),hintLoigiaiFromHintBody(),String(j.sheet_loigiai||'').trim(),String(q.LoiGiai||'').trim()].filter(Boolean);cand.sort((a,b)=>b.length-a.length);return cand[0]||''}
function hintAiDapAn(){if(isCurrentQuestionDs()){let fromLg=dsDapAnFromSolutionText(hintAiLoigiaiRaw(),currentQuestion());if(fromLg)return fromLg}let j=HINT_BY_Q[CUR]||{};return String(j.suggested_dapan||'').trim()}
function hintAiLoigiai(){let v=hintAiLoigiaiRaw();return v?stripLoigiaiMarkdown(v).replace(/\r/g,''):''}
function adminLoigiaiMissingLetters(text,q){q=q||currentQuestion();if(!q||q.Dang!=='Đúng sai')return [];let need=['A','B','C','D'].filter(L=>!!q[L]);let found=new Set();String(text||'').split(/\n/).forEach(line=>{let m=line.match(/^\s*([ABCD])\s*[\.\):]/i);if(m)found.add(m[1].toUpperCase())});return need.filter(L=>!found.has(L))}
function buildAdminAnalysisCard(j){if(!isAdminViewer()||!j||!j.admin_review)return '';let a=j.admin_analysis;if(!a)return '';let head=a.all_ok?`<div class="adminAnalysisOk">${esc(a.summary||'Sheet khớp AI')}</div>`:`<div class="adminAnalysisWarn">${esc(a.summary||'Có điểm cần sửa')}</div>`;let table='';if(a.rows&&a.rows.length){let trs=a.rows.map(r=>{let cls=r.ok?'adminAnalysisOkRow':'adminAnalysisBadRow';let mark=r.ok?'✓':'✗';let note=r.note?`<div class="muted" style="font-size:11px;margin-top:2px">${esc(r.note)}</div>`:'';return `<tr class="${cls}"><td><b>${esc(r.letter)}</b></td><td>${esc(r.sheet_p||'—')}</td><td>${esc(r.ai||'—')}</td><td>${esc(r.sheet_r||'—')}</td><td>${mark}${note}</td></tr>`}).join('');table=`<table class="adminAnalysisTbl"><thead><tr><th>Ý</th><th>Sheet P</th><th>AI</th><th>Sheet R</th><th></th></tr></thead><tbody>${trs}</tbody></table>`}let fixes='';if(!a.all_ok&&(a.fix_dapan||a.fix_loigiai))fixes=`<div class="hintAiActions" style="margin-top:8px"><button type="button" class="btnGreen" onclick="applyAdminFixAll()">✏️ Sửa Sheet (điền gợi ý AI)</button></div>`;else if(a.all_ok&&adminHintNeedsSave())fixes=`<div class="muted" style="margin-top:8px;font-size:12px">Sheet đã khớp AI — vẫn có thể bấm <b>Lưu</b> nếu vừa chỉnh tay.</div>`;return `<div class="hintAnswerCard adminAnalysisCard"><div class="hintAnswerTitle">🔬 Phân tích Đúng/Sai (ADMIN)</div>${head}${table}${fixes}</div>`}
function applyAdminFixAll(){if(!USER.is_admin)return;let j=HINT_BY_Q[CUR]||{};let a=j.admin_analysis||{};openEditWithHint(String(a.fix_dapan||'').trim(),String(a.fix_loigiai||'').trim())}
function buildHintAnswerCard(j){if(!j)return '';if(j.admin_review&&!isAdminViewer())return '';if(!j.show_answer&&!j.vip_detailed&&!j.exact&&!j.admin_review)return '';if((j.vip_detailed||j.show_answer)&&!j.admin_review&&!isAdminViewer()&&!canShowSolutionNow())return `<div class="hintAnswerCard hintAnswerPending"><div class="hintAnswerTitle">🔒 Chưa làm câu</div><div class="muted" style="font-size:13px;line-height:1.45;margin-top:6px">VIP/SVIP: chọn đáp án và <b>chấm câu này</b> (TN/ĐS tự chấm; TLN bấm ✓) trước khi xem <b>Đáp án</b> và <b>Lời giải</b> từ Sheet.</div></div>`;let q=currentQuestion();let aiDa=String(j.suggested_dapan||j.correct||'').trim();let sheetDa=String(j.sheet_dapan||'').trim();let aiLg=String(j.suggested_loigiai||'').trim();let sheetLg=String(j.sheet_loigiai||'').trim();if(j.admin_review&&isCurrentQuestionDs()){let daFromLg=dsDapAnFromSolutionText(aiLg||hintSection1Raw(),q);if(daFromLg)aiDa=daFromLg}if(!sheetDa&&q)sheetDa=String(q.DapAn||'').trim();if(!sheetLg&&q)sheetLg=String(q.LoiGiai||'').trim();if(j.admin_review&&ADMIN_HINT_SAVED[CUR]){sheetDa=String(q.DapAn||sheetDa||'').trim();sheetLg=String(q.LoiGiai||sheetLg||'').trim()}if(!aiDa&&sheetDa)aiDa=sheetDa;if(!aiLg&&sheetLg)aiLg=sheetLg;if(!aiDa&&!sheetDa&&!aiLg&&!sheetLg)return '';let isDs=isCurrentQuestionDs();let isTn=isCurrentQuestionTn();let vipShort=!!(j.vip_detailed&&!j.admin_review);function fmtAns(t){if(isDs)return formatDsHintText(t,false);if(isTn)return formatTnHintText(t,false);return formatHintDisplay(t)}function fmtSol(t,fromAi){if(vipShort)return formatHintDisplay(t);if(isDs)return formatDsHintText(t,true,fromAi);if(isTn)return formatTnHintText(t,true);return formatHintDisplay(t)}let rows='';if(sheetDa||aiDa){rows+=`<div class="hintAnswerRow"><b>📌 Đáp án:</b> <span class="hintMath hintAnswerMain">${fmtAns(sheetDa||aiDa)}</span></div>`;if(j.admin_review&&sheetDa&&aiDa&&sheetDa.replace(/\s/g,'')!==aiDa.replace(/\s/g,''))rows+=`<div class="hintAnswerRow muted" style="font-size:13px"><b>Sheet (P):</b> <span class="hintMath">${fmtAns(sheetDa)}</span> · <b>AI đề xuất:</b> <span class="hintMath">${fmtAns(aiDa)}</span></div>`;else if(j.admin_review&&sheetDa&&aiDa&&sheetDa.replace(/\s/g,'')===aiDa.replace(/\s/g,''))rows+=`<div class="hintAnswerRow" style="font-size:13px;color:#166534"><b>✓ Đáp án Sheet khớp AI</b></div>`}let aiLgRaw=j.admin_review?hintAiLoigiaiRaw():'';let lgShow=j.admin_review?(adminHintNeedsSave()?aiLgRaw:(sheetLg||String(q.LoiGiai||''))):(sheetLg||aiLg);if(lgShow){let lgLabel=j.admin_review?(adminHintNeedsSave()?'📝 Lời giải AI (diễn giải + từng ý):':'📝 Lời giải (Sheet R):'):(vipShort?'📝 Phương hướng:':'📝 Lời giải:');rows+=`<div class="hintAnswerRow" style="margin-top:8px"><b>${lgLabel}</b> <span class="hintMath">${fmtSol(lgShow,j.admin_review&&adminHintNeedsSave())}</span></div>`;if(j.admin_review&&adminHintNeedsSave()&&sheetLg&&aiLgRaw&&sheetLg.trim()!==aiLgRaw.trim())rows+=`<div class="hintAnswerRow muted" style="font-size:13px"><b>Sheet (R) hiện tại:</b> <span class="hintMath">${fmtSol(sheetLg,false)}</span></div>`;else if(j.admin_review&&!adminHintNeedsSave()&&aiLgRaw&&sheetLg&&sheetLg.trim()!==aiLgRaw.trim())rows+=`<div class="hintAnswerRow muted" style="font-size:13px"><b>AI đề xuất (mục 1):</b> <span class="hintMath">${fmtSol(aiLgRaw,true)}</span></div>`}if(!rows)return '';let cardTitle=j.admin_review?(adminHintNeedsSave()?'📋 Đáp án &amp; lời giải (ADMIN — đề xuất lưu Sheet)':'✅ Đã lưu Sheet — so khớp P/R với AI'):(vipShort?'✅ Kết quả &amp; phương hướng':'✅ Đáp án &amp; lời giải — so sánh ôn tập');let saveNote=(j.admin_review&&adminHintNeedsSave())?`<div class="muted" style="font-size:12px;margin-top:8px;line-height:1.45">So bảng phân tích phía trên → <b>✏️ Sửa Sheet</b> nếu lệch → <b>Lưu vào Google Sheet</b>.</div>`:'';return `<div class="hintAnswerCard"><div class="hintAnswerTitle">${cardTitle}</div>${rows}${saveNote}</div>`}
function buildSheetPreviewCard(){if(!canViewSolutionLive()||USER.is_admin||!canShowSolutionNow())return '';let q=currentQuestion();if(!q)return '';return buildHintAnswerCard({show_answer:true,vip_detailed:true,sheet_dapan:q.DapAn||'',sheet_loigiai:q.LoiGiai||'',suggested_dapan:q.DapAn||'',suggested_loigiai:q.LoiGiai||''})}
function buildAdminVariantTipsHtml(tips){if(!isAdminViewer()||!tips)return '';let rows='';if(tips.original_find)rows+=`<div class="adminVariantRow"><b>Đang tìm (gốc):</b> ${esc(tips.original_find)}</div>`;if(tips.suggest_find&&tips.suggest_find.length)rows+=`<div class="adminVariantRow"><b>Có thể đổi sang tìm:</b><ul>${tips.suggest_find.map(x=>'<li>'+esc(x)+'</li>').join('')}</ul></div>`;if(tips.suggest_change&&tips.suggest_change.length)rows+=`<div class="adminVariantRow"><b>Nên đổi số liệu / đại lượng:</b><ul>${tips.suggest_change.map(x=>'<li>'+esc(x)+'</li>').join('')}</ul></div>`;if(tips.ideas&&tips.ideas.length)rows+=`<div class="adminVariantRow"><b>Ý tưởng câu tránh trùng:</b><ul>${tips.ideas.map(x=>'<li>'+esc(x)+'</li>').join('')}</ul></div>`;if(!rows&&tips.raw)rows=`<div class="adminVariantRow hintMath">${formatHintDisplay(tips.raw)}</div>`;if(!rows)return '';return `<div class="adminVariantTips" id="adminVariantTips"><div class="adminVariantTitle">🧭 Gợi ý biến thể (ADMIN — tránh trùng)</div><div class="muted" style="font-size:12px;margin-bottom:4px">Dùng để viết câu mới trong Sheet: đổi đại lượng cần tìm hoặc số liệu đã cho.</div>${rows}</div>`}
function buildHintSimilarSection(){if(!USER.can_quiz_similar||(EXAM_MODE&&!SUBMITTED))return '';let sim=SIMILAR_BY_Q[CUR];let loading=SIMILAR_LOADING&&SIMILAR_LOADING_Q===CUR;let html=`<div class="hintAiActions"><button type="button" class="btn2" id="btnSimilarInline" onclick="requestSimilarQuestion()" ${loading?'disabled':''}>${loading?'⏳ Đang tạo câu tương tự…':'📝 Tạo câu tương tự'}</button></div>`;if(sim&&sim.similar){let warn='';if(sim.similar_warning&&sim.similar_warning.message)warn=`<div class="dangSimWarn" style="margin-top:8px"><b>⚠️ Quá giống</b><div>${esc(sim.similar_warning.message)}</div></div>`;let tipsHtml=buildAdminVariantTipsHtml(sim.admin_variant_tips);html+=`<div class="hintSimilarBox" id="hintSimilarBox"><div class="hintSimilarTitle">📝 Câu tương tự (AI)</div>${warn}${tipsHtml}<div class="hintSimilarBody hintMath" id="hintSimilarBody">${formatHintDisplay(sim.similar)}</div></div>`}return html}
function hintClientTimeoutMs(){if(isAdminViewer())return adminReviewIsFast()?32000:35000;return 30000}
function hintLoadingSeconds(){return HINT_LOADING_SINCE?Math.max(0,Math.floor((Date.now()-HINT_LOADING_SINCE)/1000)):0}
function updateHintLoadingElapsed(){let s=hintLoadingSeconds();let el=document.getElementById('hintLoadingElapsed');if(el){el.textContent='Đã chờ '+s+' giây…';el.style.color=s>=28?'#9a3412':''}let rb=document.getElementById('resultBox');if(rb&&HINT_LOADING)rb.textContent='⏳ AI đang làm… ('+s+'s)'}
function abortHintFetch(){if(HINT_ABORT_CTRL){try{HINT_ABORT_CTRL.abort()}catch(e){}HINT_ABORT_CTRL=null}}
function stopHintLoadingTimer(){if(HINT_WATCHDOG){clearTimeout(HINT_WATCHDOG);HINT_WATCHDOG=null}if(HINT_LOADING_TICK){clearInterval(HINT_LOADING_TICK);HINT_LOADING_TICK=null}}
function ensureHintWatchdog(){if(HINT_WATCHDOG||!HINT_LOADING_SINCE)return;let remain=Math.max(500,35000-(Date.now()-HINT_LOADING_SINCE));HINT_WATCHDOG=setTimeout(()=>{if(!HINT_LOADING)return;cancelHintRequest('Quá 35 giây — bấm Hủy hoặc Ctrl+F5 rồi thử lại.')},remain)}
function beginHintLoadingTimer(){stopHintLoadingTimer();HINT_LOADING_SINCE=Date.now();HINT_LOADING_TICK=setInterval(updateHintLoadingElapsed,500);ensureHintWatchdog();updateHintLoadingElapsed()}
function cancelHintRequest(msg){let qIdx=HINT_LOADING_Q;stopHintLoadingTimer();abortHintFetch();if(qIdx!=null){setHintLoading(false);if(CUR===qIdx){let hb=document.getElementById('hintBox');if(hb){hb.classList.remove('hintBoxLoading');hb.classList.remove('hide');hb.innerHTML='<b>⏹ Đã dừng soát AI</b><div class="muted" style="margin-top:8px">'+esc(msg||'Đã hủy yêu cầu AI.')+'</div><div style="margin-top:8px"><button type="button" class="btn2" onclick="requestHint()">Thử lại</button></div>'}}let rb=document.getElementById('resultBox');if(rb&&USER.is_admin){rb.textContent=isMobileQuizUI()?'ADMIN':'ADMIN: đang xem đáp án/lời giải';syncAdminResultBox()}}}
function showHintLoadingBox(){let hb=document.getElementById('hintBox');if(!hb)return;hb.classList.remove('hide');hb.classList.add('hintBoxLoading');let adminFast=isAdminViewer()&&adminReviewIsFast();let title=isAdminViewer()?(adminFast?(adminUsesGpt()?'⚡ Soát nhanh GPT:':'⚡ Soát nhanh:'):(adminUsesGpt()?'🔍 Soát đề GPT (ChatGPT):':'🔍 AI soát đề (ADMIN):')):(isSvipViewer()?'💡 SVIP — AI Gemini:':(USER.is_vip?'💡 AI Gemini:':'💡 Gợi ý AI:'));let renderNote=isAdminViewer()?'<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">Tối đa ~30s/request. Nếu quay &gt;35s → bấm <b>Hủy</b> hoặc <b>Ctrl+F5</b>.</div>':'';let sub=isAdminViewer()?(adminFast?`2 mục — gpt-4.1-mini — ${adminReviewLoadingNote()}…`:(adminUsesGpt()?`3 mục + DIỄN GIẢI — ${adminAiModelLabel()} — ${adminReviewLoadingNote()}…`:`Phân tích Đúng/Sai — ${adminReviewLoadingNote()}…`)):(isSvipViewer()?`Gemini: thay số + kiểm tra từng A/B/C/D, không chốt đáp án — thường 10–25 giây…`:(USER.is_vip?'Gemini: phương hướng + tự kiểm tra, không chốt đáp án — thường 10–25 giây…':'Đang phân tích câu hỏi…'));let preview=(isAdminViewer()?'':((USER.is_vip||USER.can_view_solution_live)?buildSheetPreviewCard():''));let qImg=String((QUESTIONS[CUR]||{}).HinhAnh||'').trim();let visionNote=(!isAdminViewer()&&qImg)?'<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">📷 Câu có hình — AI sẽ đọc ảnh minh họa.</div>':(isAdminViewer()&&qImg?'<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">📷 Có ảnh cột T — GPT/Gemini đọc hình khi soát.</div>':'');let elapsed=hintLoadingSeconds();hb.innerHTML=`<b>${title}</b>${preview}<div class="hintLoadingPanel"><div class="hintSpinBig"></div><div style="flex:1"><b>Đang gọi AI…</b><div id="hintLoadingElapsed" class="muted" style="margin-top:4px;font-size:12px">Đã chờ ${elapsed} giây…</div><div class="muted" style="margin-top:6px;font-size:13px;line-height:1.45">${esc(sub)}</div>${visionNote}${renderNote}<div style="margin-top:10px"><button type="button" class="btn2" onclick="cancelHintRequest()">⏹ Hủy</button></div></div></div>`;if(preview)typesetQuizMath();updateHintLoadingElapsed()}
function renderHintBox(j){let hb=document.getElementById('hintBox');if(!hb)return;j=j||{};hb.classList.remove('hide');hb.classList.remove('hintBoxLoading');hb.classList.remove('learningOpen');let title=j.admin_review?(String(j.provider_mode||'').toUpperCase()==='OPENAI'||String(j.provider_used||'').toUpperCase()==='OPENAI'?'🔍 Soát đề GPT (ChatGPT):':'🔍 AI soát đề (ADMIN):'):(j.vip_detailed?(isSvipViewer()?'💡 SVIP — AI Gemini:':'💡 AI VIP:'):'💡 Gợi ý AI:');if(!j.hint&&!j.admin_review&&!j.vip_detailed&&SIMILAR_BY_Q[CUR])title='📝 Câu tương tự (AI)';let extra='';if(j.admin_review){let modeLbl=esc(j.admin_review_mode_label||(j.admin_review_mode==='fast'?'Nhanh':'Kỹ'));extra=`<div class="muted" style="margin-top:6px;font-size:12px">ADMIN · chế độ <b>${modeLbl}</b>: ${isCurrentQuestionDs()?'bảng <b>Phân tích Đúng/Sai</b> từng ý A–D':(isCurrentQuestionTn()?'<b>Lời giải TN</b> — chỉ giải phương án đúng':'<b>Soát P/R</b>')} so Sheet → <b>Sửa Sheet</b> nếu lệch → <b>Lưu</b></div>`;if(j.provider_mode)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">Cấu hình ADMIN: <b>${esc(j.provider_mode)}</b>${String(j.provider_mode||'').toUpperCase()==='OPENAI'?' · model '+esc(j.admin_review_mode==='fast'?'gpt-4.1-mini':adminAiModelLabel()):''}</div>`;if(j.key_index){let provLine=`AI: ${esc(j.provider_used||'')} | key #${j.key_index}`;if(j.provider_mode&&j.provider_used&&j.provider_mode!==j.provider_used)provLine+=` (dự phòng — GPT lỗi/quota)`;else if(String(j.provider_used||'').toUpperCase()==='OPENAI')provLine+=` · ${esc(adminAiModelLabel())}`;extra+=`<div class="muted" style="margin-top:4px;font-size:12px"><b>${provLine}</b></div>`}else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Cần OPENAI_API_KEY hoặc GEMINI_API_KEY trên Render</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ AI lỗi/quota — vẫn chép được lời giải Sheet/AI bên dưới vào cột R qua <b>Sửa câu</b>.</div>`;if(j.hint_truncated)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ AI có thể chưa đủ 3 mục (Diễn giải / Giải từng ý / Chốt đáp án) — bấm lại <b>AI kiểm tra</b>.</div>`;if(j.vision_used)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">📷 Đã đọc ảnh minh họa${j.vision_model?' · '+esc(j.vision_model):''}</div>`;else if(j.has_question_image&&j.image_fetch_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ Có link ảnh nhưng không tải được: ${esc(j.image_fetch_error)}</div>`;extra+=`<div class="hintAdminActions"><button type="button" class="btnGreen" onclick="openEditWithHint()">✏️ Sửa câu (điền AI)</button><button type="button" class="btn2" onclick="copyHintLoigiai()">📋 Chép lời giải</button><button type="button" class="btn2" onclick="copyHintAll()">📋 Chép toàn bộ</button><button type="button" class="btn2" onclick="applyHintField('DapAn')">→ Chỉ đáp án (P)</button><button type="button" class="btn2" onclick="applyHintField('LoiGiai')">→ Chỉ lời giải (R)</button><button type="button" class="btn2" onclick="openInfographicPrompt()">📊 Prompt infographic</button></div>`}else if(j.vip_detailed){let svipMode=isSvipViewer();extra=`<div class="muted" style="margin-top:6px;font-size:12px">${svipMode?'SVIP: Gemini — thay số vào công thức + kiểm tra từng A/B/C/D, không chốt đáp án.':'VIP: Gemini — phương hướng và công thức, không chốt đáp án.'}</div>`;if(j.provider_mode)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">Cấu hình: <b>${esc(j.provider_mode)}</b></div>`;if(j.key_index){let provLine=`AI: ${esc(j.provider_used||'')} | key #${j.key_index}`;if(j.provider_mode&&j.provider_used&&j.provider_mode!==j.provider_used)provLine+=' (dự phòng)';extra+=`<div class="muted" style="margin-top:4px;font-size:12px"><b>${provLine}</b></div>`}else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Chưa có key — nạp tại 🔑 Key AI của tôi</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`;if(j.hint_truncated)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ ${j.svip_substitution_check?'AI có thể chưa kiểm tra đủ 4 phương án A/B/C/D':'AI có thể chưa đủ mục'} — bấm lại <b>Gợi ý AI</b>.</div>`;if(j.hide_5050&&j.hide_5050.length)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">Đã loại: ${esc(j.hide_5050.join(', '))}</div>`;if(j.vision_used)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">📷 Đã đọc ảnh minh họa${j.vision_model?' · '+esc(j.vision_model):''}</div>`;else if(j.has_question_image&&j.image_fetch_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#9a3412">⚠️ Có link ảnh nhưng không tải được: ${esc(j.image_fetch_error)}</div>`;if(canUnlockInfographic(CUR))extra+=`<div class="hintAiActions"><button type="button" class="btn2" onclick="openInfographicPrompt()">📊 Prompt infographic</button></div>`}else if(j.vip_formula_only){extra=`<div class="muted" style="margin-top:6px;font-size:12px">VIP: công thức đã thay số từ đề + tự loại 2 đáp án sai (trắc nghiệm)</div>`;if(j.hide_5050&&j.hide_5050.length)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#1d4ed8">Đã loại: ${esc(j.hide_5050.join(', '))}</div>`;if(j.provider_used==='FALLBACK')extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">AI lỗi hoặc chưa có key — <a href="#" onclick="backHome();return false">🔑 Key AI của tôi</a></div>`;else if(!j.ai_configured)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">Chưa có key — nạp tại 🔑 Key AI của tôi</div>`}else if(j.key_index){extra=`<div class="muted" style="margin-top:6px;font-size:12px">AI: ${esc(j.provider_used||'')} | key #${j.key_index}</div>`}else if(j.hint){extra=`<div class="muted" style="margin-top:6px;font-size:12px">AI fallback${j.ai_configured?' (key lỗi hoặc hết quota)':' (chưa có key)'}</div>`;if(j.ai_error)extra+=`<div class="muted" style="margin-top:4px;font-size:12px;color:#991b1b">${esc(j.ai_error)}</div>`}if(j.message)extra+=`<div class="muted" style="margin-top:4px;font-size:12px">${esc(j.message)}</div>`;let analysisCard=j.admin_review?buildAdminAnalysisCard(j):'';let answerCard=buildHintAnswerCard(j);let similarSec=buildHintSimilarSection();let body=j.hint?formatHintDisplay(j.hint):'';let bodyHtml=body?`<div id="hintAdminBody" class="hintAdminBody">${body}</div>`:'';hb.innerHTML=`<b>${title}</b>${analysisCard}${answerCard}${extra}${bodyHtml}${similarSec}`;typesetQuizMath()}
function copyHintLoigiai(){let t=hintFieldValue('LoiGiai');if(!t){alert('Chưa có lời giải đề xuất (mục 1).');return}navigator.clipboard.writeText(t).then(()=>alert('Đã chép lời giải (đúng mẫu A. Đúng — …).')).catch(()=>alert('Không chép được — thử bấm → Lời giải (R) rồi Ctrl+C.'))}
function copyHintAll(){let t=hintRawText();if(!t){alert('Chưa có nội dung.');return}navigator.clipboard.writeText(t).then(()=>alert('Đã chép vào clipboard (text gốc có $...$).')).catch(()=>{let el=document.getElementById('hintAdminBody');if(el){let r=document.createRange();r.selectNodeContents(el);let sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);try{document.execCommand('copy');alert('Đã chép vùng hiển thị (Ctrl+C).')}catch(e){alert('Chọn text trong ô gợi ý rồi Ctrl+C.')}}})}
function hintFieldValue(field){let j=HINT_BY_Q[CUR]||{};let a=j.admin_analysis||{};if(field==='DapAn')return String(a.fix_dapan||'').trim()||hintAiDapAn();if(field==='LoiGiai')return String(a.fix_loigiai||'').trim()||hintAiLoigiai();return ''}
function applyHintField(field){if(!USER.is_admin){alert('Chỉ ADMIN.');return}let v=hintFieldValue(field);if(!v){alert(field==='DapAn'?'Chưa tách được đáp án AI (mục 2).':'Chưa có lời giải đề xuất (mục 1).');return}openEditWithHint(field==='DapAn'?v:'',field==='LoiGiai'?v:'')}
function openEditWithHint(dapan='',loigiai=''){let j=HINT_BY_Q[CUR]||{};let a=j.admin_analysis||{};if(!dapan)dapan=String(a.fix_dapan||'').trim()||hintAiDapAn();if(!loigiai)loigiai=String(a.fix_loigiai||'').trim()||hintAiLoigiai();if(isCurrentQuestionDs()&&loigiai){let sync=dsDapAnFromSolutionText(loigiai,QUESTIONS[CUR]);if(sync)dapan=sync}if(isCurrentQuestionTn()&&loigiai)loigiai=normalizeTnLoigiaiPlain(loigiai,QUESTIONS[CUR]);openEdit();syncQuestionModalChrome();if(dapan)adminSyncDapAnDom(dapan);if(loigiai){let el=document.getElementById('edit_LoiGiai');if(el)el.value=loigiai}}
async function saveHintField(field){alert('ADMIN: hãy bấm ✏️ Sửa câu (điền AI), kiểm tra đủ Đáp án + Lời giải, rồi Lưu vào Google Sheet — không lưu thẳng từ AI.')}

/* ==========================================================================
 * [JS-LEARNING-PANEL] 🧭 Phương pháp — hiển thị trong #hintBox (không dùng accordion cũ)
 * --------------------------------------------------------------------------
 * Luồng: learningQuickBar → openLearningPanel('method') → loadLearningPanelContent
 *        → renderLearningPanel → methodLearningLatexHtml → renderTheoryLatexBlocks
 * Dữ liệu: Sheet Phuong_Phap, cột NoiDungLaTeX (\\begin{dn}, note, vidu)
 * API: POST /api/learning/method  {Mon,Lop,Chuong,BaiHoc,DangBaiTap}
 * CSS: [CSS-LEARNING-PANEL]  #hintBox.learningOpen, .learningPanelBody
 * ========================================================================== */
function learningCacheKey(kind,q){q=q||{};return kind+'|'+[q.Mon||'',q.Lop||'',q.Chuong||'',q.BaiHoc||'',kind==='method'?(q.DangBaiTap||''):''].join('|')}
function currentQuestionTikzCode(q){
  q=q||QUESTIONS[CUR]||{};
  let parsed={tikz:'',img:''};
  try{if(typeof parseHinhanhCellClient==='function')parsed=parseHinhanhCellClient(q.HinhAnh||'')||parsed}catch(e){}
  return String(q.Tikz||parsed.tikz||'').trim();
}
function currentQuestionImageUrl(q){
  q=q||QUESTIONS[CUR]||{};
  let parsed={tikz:'',img:''};
  try{if(typeof parseHinhanhCellClient==='function')parsed=parseHinhanhCellClient(q.HinhAnh||'')||parsed}catch(e){}
  let img=String(parsed.img||q.HinhAnh||'').trim();
  if(/^tikzraw:/i.test(img))return '';
  return img;
}
function currentQuestionLoiGiaiForLatex(q){
  q=q||QUESTIONS[CUR]||{};
  let lg='';
  try{if(typeof currentQuizLoiGiaiText==='function')lg=String(currentQuizLoiGiaiText(q)||'').trim()}catch(e){}
  return lg||String(q.LoiGiai||'').trim();
}
function currentQuestionLatexText(){
  let q=applyResolvedDang(QUESTIONS[CUR]||{});
  let dang=normDangClient(q.Dang||'');
  let out=['\\begin{ex}'];
  let id=String(q.ID||'').trim();
  if(id)out.push('% Mã câu: '+id);
  let correctMcq=(String(q.DapAn||'').trim().toUpperCase().match(/^([ABCD])$/)||[])[1]||'';
  let dsMap={};
  String(q.DapAn||'').replace(/([ABCD])\s*[=:\-]\s*(Đúng|Sai|Đ|D|S)/gi,function(_,L,V){dsMap[L.toUpperCase()]=/^đ|^d/i.test(V)?'Đ':'S';return _});
  if(!Object.keys(dsMap).length){
    let compact=String(q.DapAn||'').toUpperCase().replace(/\u0110/g,'D').replace(/[^DS]/g,'');
    compact.split('').forEach(function(v,i){let L=['A','B','C','D'][i];if(L)dsMap[L]=v==='D'?'Đ':'S'});
  }
  let stem=String(q.CauHoi||'').trim();
  let tikz=currentQuestionTikzCode(q);
  let stemHasFig=/\\begin\s*\{\s*tikzpicture/i.test(stem)||/\\immini\b/i.test(stem);
  if(tikz&&!stemHasFig){
    out.push('\\immini{');
    out.push(tikz);
    out.push('}{');
    if(stem)out.push(stem);
    out.push('}');
  }else if(stem)out.push(stem);
  if(dang==='Đúng sai'){
    out.push('\\choiceTF');
    ['A','B','C','D'].forEach(function(L){if(String(q[L]||'').trim()){let mark=dsMap[L]==='Đ'?'\\True ':'';out.push('{'+mark+String(q[L]).trim()+'}')}});
  }else if(dang==='Trả lời ngắn'){
    if(String(q.DapAn||'').trim())out.push('\\shortans{'+String(q.DapAn).trim()+'}');
  }else if(['A','B','C','D'].some(function(L){return String(q[L]||'').trim()})){
    out.push('\\choice');
    ['A','B','C','D'].forEach(function(L){if(String(q[L]||'').trim()){let mark=L===correctMcq?'\\True ':'';out.push('{'+mark+stripOptionPrefix(String(q[L]).trim(),L)+'}')}});
  }
  let lg=currentQuestionLoiGiaiForLatex(q);
  if(lg)out.push('\\loigiai{'+lg+'}');
  out.push('\\end{ex}');
  let img=currentQuestionImageUrl(q);
  if(img&&!tikz)out.push('% Hình minh họa: '+img);
  return out.filter(function(x){return String(x||'').trim()!==''}).join('\n');
}
function currentQuestionAiModePrompt(){
  let q=QUESTIONS[CUR]||{};
  let latex=currentQuestionLatexText();
  let lines=[
    'Hãy hỗ trợ giải câu hỏi sau theo cách giáo viên THPT.',
    'Bắt buộc trình bày theo thứ tự:',
    '1. Ghi lại ĐỀ BÀI đầy đủ.',
    '2. Giải ngắn gọn, có các bước rõ ràng; mỗi Bước 1, Bước 2, Bước 3 xuống một dòng riêng.',
    '3. Chốt đáp án/kết quả.',
    '4. Xuất lại câu hỏi ở dạng LaTeX trong một khối code.',
    'Không dùng markdown dấu * hoặc ** trong phần giải thích. Nếu có mục "Trong đó", mỗi đại lượng xuống một dòng riêng.',
    'Nếu là trắc nghiệm thì phân tích và chốt phương án; nếu là đúng/sai thì xét từng ý; nếu là trả lời ngắn thì nêu kết quả và đơn vị.',
    '',
    'Môn: '+(q.Mon||''),
    'Lớp: '+(q.Lop||''),
    'Chương/Bài: '+[q.Chuong,q.BaiHoc].filter(Boolean).join(' - '),
    'Dạng: '+(q.Dang||''),
    'Câu hỏi: '+(q.CauHoi||'')
  ];
  ['A','B','C','D'].forEach(function(L){if(String(q[L]||'').trim())lines.push(L+'. '+q[L])});
  if(String(q.HinhAnh||'').trim())lines.push('Hình minh họa/link ảnh: '+q.HinhAnh);
  if(latex)lines.push('', 'LaTeX nguồn từ app:', latex);
  return lines.filter(function(x){return String(x||'').trim()!==''}).join('\n');
}
function copyTextBestEffort(txt){
  txt=String(txt||'');
  if(navigator.clipboard&&navigator.clipboard.writeText)return navigator.clipboard.writeText(txt).then(function(){return true}).catch(function(){return false});
  try{
    let ta=document.createElement('textarea');
    ta.value=txt;ta.setAttribute('readonly','');ta.style.position='fixed';ta.style.left='-9999px';
    document.body.appendChild(ta);ta.select();let ok=document.execCommand('copy');ta.remove();return Promise.resolve(!!ok);
  }catch(e){return Promise.resolve(false)}
}
function ensureGoogleAiModeModal(){
  let modal=document.getElementById('googleAiModeModal');
  if(modal)return modal;
  modal=document.createElement('div');
  modal.id='googleAiModeModal';
  modal.className='googleAiModeModal hide';
  modal.innerHTML='<div class="googleAiModeCard" role="dialog" aria-modal="true" aria-labelledby="googleAiModeTitle">'
    +'<div class="googleAiModeHead"><span id="googleAiModeTitle">AI Internet</span><button type="button" onclick="closeGoogleAiModeModal()" title="Đóng">×</button></div>'
    +'<p class="googleAiModeHelp">Bấm <b>Chép & mở Google</b>: app chép prompt trước, rồi trên điện thoại mở Google cùng tab để bấm Back là quay lại app.</p>'
    +'<textarea id="googleAiModePromptText" class="googleAiModeText" spellcheck="false"></textarea>'
    +'<p class="googleAiModeHelp"><b>LaTeX câu hiện tại</b> — dùng để chép nhanh về Word/LaTeX hoặc dán lại cho AI.</p>'
    +'<textarea id="googleAiModeLatexText" class="googleAiModeText googleAiModeLatexText" spellcheck="false"></textarea>'
    +'<div class="googleAiModeActions"><button type="button" class="btn2" onclick="copyGoogleAiModeLatexFromModal()">📄 Chép LaTeX</button><button type="button" class="btn2 googleAiCopyPrimary" onclick="copyGoogleAiModePromptFromModal()">📋 Chép prompt</button><button type="button" class="btn googleAiCopyOpenPrimary" onclick="copyAndOpenGoogleAiMode()">↗ Chép & mở Google</button><button type="button" class="btn2 googleAiOpenExternalBtn" onclick="openGoogleAiModeTab()">↗ Mở Google</button></div>'
    +'</div>';
  modal.addEventListener('click',function(ev){if(ev.target===modal)closeGoogleAiModeModal()});
  document.body.appendChild(modal);
  return modal;
}
function closeGoogleAiModeModal(){
  let modal=document.getElementById('googleAiModeModal');
  if(modal)modal.classList.add('hide');
}
async function copyGoogleAiModePromptFromModal(){
  let ta=document.getElementById('googleAiModePromptText');
  let txt=ta?ta.value:'';
  let ok=await copyTextBestEffort(txt);
  if(!ok&&ta){ta.focus();ta.select()}
  alert(ok?'Đã chép prompt.':'Trình duyệt chặn copy tự động. Hãy chọn nội dung trong ô rồi Ctrl+C.');
}
async function copyGoogleAiModeLatexFromModal(){
  let ta=document.getElementById('googleAiModeLatexText');
  let txt=ta?ta.value:'';
  let ok=await copyTextBestEffort(txt);
  if(!ok&&ta){ta.focus();ta.select()}
  alert(ok?'Đã chép LaTeX của câu hiện tại.':'Trình duyệt chặn copy tự động. Hãy chọn nội dung trong ô LaTeX rồi Ctrl+C.');
}
function googleAiModeSearchUrl(prompt){
  return 'https://www.google.com/search?udm=50&q='+encodeURIComponent(prompt||'');
}
function openGoogleAiModeTab(prompt){
  if(!prompt){
    let ta=document.getElementById('googleAiModePromptText');
    prompt=ta?ta.value:'';
  }
  try{if(typeof saveCurrent==='function')saveCurrent()}catch(e){}
  let url=googleAiModeSearchUrl(prompt);
  if(typeof isMobileQuizUI==='function'&&isMobileQuizUI()){
    window.location.assign(url);
    return;
  }
  window.open(url,'_blank','noopener');
}
async function copyAndOpenGoogleAiMode(){
  let ta=document.getElementById('googleAiModePromptText');
  let txt=ta?ta.value:'';
  let ok=await copyTextBestEffort(txt);
  if(!ok&&ta){
    ta.focus();ta.select();
    alert('Trình duyệt chặn chép tự động. Hãy bấm Chép prompt hoặc chọn nội dung rồi copy thủ công.');
    return;
  }
  openGoogleAiModeTab(txt);
}
async function openGoogleAiMode(){
  let prompt=currentQuestionAiModePrompt();
  let latex=currentQuestionLatexText();
  openGoogleAiModeCustom(prompt,latex,'AI Internet — Giải bài');
}
function buildTranslateEnSourceText(loai){
  loai=normTranslateKind(loai||'CauHoi');
  let q=applyResolvedDang(QUESTIONS[CUR]||{});
  if(loai==='CauHoi'){
    let stem=String(q.CauHoi||'').trim();
    let opts=[];
    ['A','B','C','D'].forEach(function(L){let v=String(q[L]||'').trim();if(v)opts.push(L+'. '+v)});
    if(!opts.length)return stem;
    return stem+'\n\nPhương án:\n'+opts.join('\n');
  }
  if(loai==='DapAn'){
    let da=String(q.DapAn||'').trim();
    if(!da)return '';
    if(q.Dang==='Trắc nghiệm'){
      let L=String(da).trim().toUpperCase().match(/^([ABCD])$/);
      let bits=[L?'Correct answer: '+L[1]:'Answer: '+da];
      if(L&&String(q[L[1]]||'').trim())bits.push(L[1]+'. '+String(q[L[1]]).trim());
      return bits.join('\n');
    }
    if(q.Dang==='Đúng sai'){
      let bits=[];
      ['A','B','C','D'].forEach(function(L){let s=String(q[L]||'').trim();if(s)bits.push(L+'. '+s)});
      return 'Answer key: '+da+(bits.length?'\n'+bits.join('\n'):'');
    }
    return 'Answer: '+da;
  }
  return String(q.LoiGiai||'').trim();
}
function buildTranslateEnAiModePrompt(loai){
  loai=normTranslateKind(loai||'CauHoi');
  let q=QUESTIONS[CUR]||{};
  let text=buildTranslateEnSourceText(loai);
  let meta=[q.Mon,q.Lop,q.Chuong,q.BaiHoc,q.DangBaiTap].filter(Boolean).join(' · ');
  let abcdRule='';
  if(loai==='CauHoi'&&['A','B','C','D'].some(function(L){return String(q[L]||'').trim()})){
    abcdRule='QUAN TRỌNG — Câu có phương án A/B/C/D: phần English phải giữ đúng nhãn A. B. C. D. (mỗi phương án một dòng).\n';
  }
  return [
    'Bạn là trợ lý tiếng Anh học thuật cho học sinh THPT Việt Nam.',
    'Nhiệm vụ: chuyển nội dung sau sang tiếng Anh rõ, đúng thuật ngữ Toán/Lý, giữ LaTeX trong $...$ nếu có.',
    'Không giải bài, không chốt đáp án, không thêm lời giải. Chỉ dịch và giải thích từ vựng cần thiết.',
    abcdRule,
    'Trả lời đúng cấu trúc:',
    'English:',
    '<bản dịch tiếng Anh>',
    '',
    'Vocabulary:',
    '- term: nghĩa tiếng Việt ngắn',
    '',
    'Notes:',
    '- lưu ý cách đọc/đơn vị nếu có',
    '',
    'Loại nội dung: '+loai,
    'Ngữ cảnh: '+meta,
    'Nội dung cần dịch:',
    text
  ].filter(Boolean).join('\n');
}
function openTranslateAiMode(loai){
  if(LEARNING_OPEN_KIND==='translate')closeLearningPanel();
  loai=normTranslateKind(loai||'CauHoi');
  let text=buildTranslateEnSourceText(loai);
  if(!text.trim()){alert('Chưa có nội dung để dịch ở mục này.');return}
  openGoogleAiModeCustom(buildTranslateEnAiModePrompt(loai),currentQuestionLatexText(),'🇬🇧 Dịch EN — AI Internet');
}
function toggleTranslatePanel(){openTranslateAiMode('CauHoi')}
function openGoogleAiModeCustom(prompt,latex,title){
  let modal=ensureGoogleAiModeModal();
  let titleEl=document.getElementById('googleAiModeTitle');
  if(titleEl)titleEl.textContent=title||'AI Internet';
  let ta=document.getElementById('googleAiModePromptText');
  if(ta){ta.value=prompt||'';setTimeout(function(){try{ta.focus()}catch(e){}},60)}
  let lta=document.getElementById('googleAiModeLatexText');
  if(lta)lta.value=latex||'';
  modal.classList.remove('hide');
}
// Thanh công cụ dưới đáp án đã gỡ bỏ; hàm này chỉ dọn thanh cũ nếu còn sót trong DOM.
function ensureLearningQuickBar(){
  let bar=document.getElementById('learningQuickBar');
  if(bar&&bar.parentNode)bar.parentNode.removeChild(bar);
}
function miniCalcVars(){return ['A','B','C','D','E','F','G','H']}
function miniCalcSubstMem(s,mem){s=String(s||'');if(!s||!mem)return s;miniCalcVars().forEach(function(L){let mv=String(mem[L]||'').trim();if(!mv)return;let sub=miniCalcNormExpr(mv);if(!sub)return;s=s.replace(new RegExp('(^|[^a-zA-Z$])'+L+'(?![a-zA-Z])','g'),'$1('+sub+')')});return s}
function miniCalcUseVar(st,ln,L){ln=ln|0;let mv=String(st.mem[L]||'').trim();if(st.mode==='STO'){let v=String(st.results[ln]||st.lines[ln]||'').trim(),dec=String(st.decExtras[ln]||'').trim();if(dec)st.mem[L]=dec;else{let num=miniCalcEvalExpr(v);st.mem[L]=num!=null?miniCalcFmtNum(num):(v||'0')}st.mode='';st._memMsg='Đã lưu '+L+' = '+st.mem[L]}else{if(miniCalcHasResult(st,ln))miniCalcMaybeNewEntry(st,'0');if(st.mode==='ALPHA'){if(mv){miniCalcInsertInLine(st,mv);renderMiniCalcTape();st._memMsg='Gọi '+L}else st._memMsg='Ô '+L+' trống — STO trước';st.mode=''}else if(mv){miniCalcInsertInLine(st,mv);renderMiniCalcTape();st._memMsg='Gọi '+L}else st._memMsg='STO→'+L+' lưu · ALPHA→'+L+' gọi'}}
function miniCalcFracTok(){return '⟦|⟧'}
function miniCalcLegacyFrac(s){return String(s||'').replace(/\(([^()]*)\)\/\(([^()]*)\)/g,function(_m,a,b){return '⟦'+a+'|'+b+'⟧'}).replace(/(\d+)\/(\d+)/g,function(_m,a,b){return '⟦'+a+'|'+b+'⟧'})}
function miniCalcGcd(a,b){a=Math.abs(a|0);b=Math.abs(b|0);while(b){let t=b;b=a%b;a=t}return a||1}
function miniCalcParseFracTok(s){let m=String(s||'').trim().match(/^(-?)⟦(\-?\d+)\|(\d+)⟧$/);if(!m)return null;return {sign:m[1],num:m[2],den:m[3]}}
function miniCalcReduceTok(n,d){n=Number(n);d=Number(d);if(!isFinite(n)||!isFinite(d)||!d)return '⟦'+n+'|'+d+'⟧';let sign=n<0?'-':'';n=Math.abs(n|0);d=Math.abs(d|0);let g=miniCalcGcd(n,d);return (sign||'')+'⟦'+(n/g)+'|'+(d/g)+'⟧'}
function miniCalcFmtRecurring(n,d){n=Number(n);d=Number(d);if(!isFinite(n)||!isFinite(d)||!d)return '';let sign=(n*d<0)?'-':'';n=Math.abs(n|0);d=Math.abs(d|0);let whole=Math.floor(n/d),rem=n%d;if(!rem)return sign+whole;let digits='',seen={},pos=0;while(rem&&seen[rem]===undefined&&pos<24){seen[rem]=pos;rem*=10;digits+=Math.floor(rem/d);rem%=d;pos++}if(!rem){digits=digits.replace(/0+$/,'');return sign+whole+(digits?'.'+digits:'')}let rs=seen[rem],non=digits.slice(0,rs),rep=digits.slice(rs);return sign+whole+'.'+non+'('+rep+')'}
function miniCalcFmtDecHtml(s){return esc(String(s||'')).replace(/\(([^)]+)\)/g,'<span class="miniCalcRep">($1)</span>')}
function miniCalcNormFracLine(v){let m=String(v||'').trim().match(/^(-?)⟦(\-?\d+)\|(\d+)⟧$/);if(!m)return null;let n=Number(m[2]),d=Number(m[3]);if(m[1]==='-')n=-Math.abs(n);if(!d)return null;let g=miniCalcGcd(Math.abs(n),d);n=Math.trunc(n/g);d=Math.trunc(d/g);if(d<0){n=-n;d=-d}return (n<0?'-':'')+'⟦'+Math.abs(n)+'|'+d+'⟧'}
function miniCalcFracValue(p){if(!p)return null;return Number((p.sign||'')+p.num)/Number(p.den)}
function miniCalcEnsureDec(st){if(!st.decLines||st.decLines.length<4)st.decLines=['','','',''];return st.decLines}
function miniCalcEnsureArr4(a){if(!a||a.length<4)return ['','','',''];return a}
function miniCalcHasResult(st,ln){return !!String((st.results||[])[ln|0]||'').trim()}
function miniCalcClearResult(st,ln){miniCalcEnsureArr4(st.results);miniCalcEnsureArr4(st.decExtras);st.results[ln|0]='';st.decExtras[ln|0]=''}
function miniCalcClearShow(st){st.results=['','','',''];st.decExtras=['','','','']}
function miniCalcClearDec(st,ln){miniCalcEnsureDec(st);st.decLines[ln|0]='';miniCalcEnsureArr4(st.decExtras);st.decExtras[ln|0]=''}
function miniCalcRestoreEdit(st){let ln=st.line|0;if(!miniCalcHasResult(st,ln))return false;miniCalcClearResult(st,ln);st.cursor=String(st.lines[ln]||'').length;return true}
function miniCalcSpaceNum(s){s=String(s||'');let neg=s[0]==='-';if(neg)s=s.slice(1);if(!/^\d/.test(s))return esc(String((neg?'-':'')+s));let parts=s.split('.');parts[0]=parts[0].replace(/\B(?=(\d{3})+(?!\d))/g,' ');return esc((neg?'-':'')+parts.join('.'))}
function miniCalcFmtDisplay(s){s=String(s||'').trim();if(!s)return '';if(/^x=/i.test(s)){let p=s.split('=');return 'x='+miniCalcSpaceNum(p.slice(1).join('='))}if(/⟦|√/.test(s))return miniCalcVisualLine(s,false,0,'');return miniCalcSpaceNum(s)}
function miniCalcShouldChain(key){return miniCalcBreakOp(key)||key==='='||key==='^'||key==='^2'||key==='^3'||key==='10^'||key==='RECIP'||key==='NEG'||key==='('}
function miniCalcMaybeNewEntry(st,key){let ln=st.line|0;if(!miniCalcHasResult(st,ln))return;if(miniCalcShouldChain(key)){let res=String(st.results[ln]||'').trim();if(res){if(/^x=/i.test(res))st.lines[ln]=res.replace(/^x\s*=\s*/i,'');else if(/^(-?)⟦/.test(res)||/√/.test(res))st.lines[ln]=res;else{let n=miniCalcEvalExpr(res);st.lines[ln]=n!=null?miniCalcFmtNum(n):res}st.cursor=st.lines[ln].length}miniCalcClearResult(st,ln);return}miniCalcClearResult(st,ln);st.lines[ln]='';st.cursor=0}
function miniCalcSetResult(st,ln,expr,out,decExtra){ln=ln|0;st.lines[ln]=String(expr||'').trim();miniCalcEnsureArr4(st.results);miniCalcEnsureArr4(st.decExtras);st.results[ln]=String(out||'').trim();st.decExtras[ln]=decExtra||'';st.line=ln;st.cursor=st.lines[ln].length}
function miniCalcApplyEquals(st,ln){ln=ln|0;let v=String(st.lines[ln]||'').trim();if(!v)return;if(/[xX]/.test(v)){st._memMsg='Có x — gõ = trong PT rồi bấm SOLVE';return}miniCalcEnsureDec(st);let norm=miniCalcNormFracLine(v);if(norm){let p=miniCalcParseFracTok(norm);miniCalcSetResult(st,ln,v,norm,p?miniCalcFmtRecurring(Number((p.sign||'')+p.num),Number(p.den)):'');return}let exact=miniCalcExactTrig(v,st.angMode),r=null;if(!exact){r=miniCalcEvalExpr(v);if(r==null)return;exact=miniCalcMatchRadical(r)}if(exact){miniCalcSetResult(st,ln,v,exact,'');return}let f=miniCalcToFraction(r),isInt=Math.abs(r-Math.round(r))<1e-10;if(f&&!isInt){let nf=miniCalcNormFracLine(f)||f,p=miniCalcParseFracTok(nf);miniCalcSetResult(st,ln,v,nf,p?miniCalcFmtRecurring(Number((p.sign||'')+p.num),Number(p.den)):miniCalcFmtNum(r))}else miniCalcSetResult(st,ln,v,miniCalcFmtNum(r),'')}
function miniCalcFracAt(txt,pos){txt=String(txt||'');pos=pos|0;let i=0;while(i<txt.length){if(txt.charAt(i)==='⟦'){let end=txt.indexOf('⟧',i);if(end<0)break;if(pos>=i&&pos<=end+1){let inner=txt.slice(i+1,end),pipe=inner.indexOf('|'),num=pipe>=0?inner.slice(0,pipe):inner,den=pipe>=0?inner.slice(pipe+1):'',rel=Math.max(0,pos-i-1),slot=rel<=num.length?'num':'den';return {start:i,end,num,den,slot,pipeAt:i+1+num.length}}i=end+1}else i++}return null}
function miniCalcFracHtml(num,den,slot,active){let n=String(num||''),d=String(den||''),nShow=n?esc(n):(active&&slot==='num'?'<span class="miniCalcFracPh"><span class="miniCalcCaret"></span></span>':'<span class="miniCalcFracPh">□</span>');let dShow=d?esc(d):(active&&slot==='den'?'<span class="miniCalcFracPh"><span class="miniCalcCaret"></span></span>':'<span class="miniCalcFracPh">□</span>');if(active&&slot==='num'&&n) nShow=esc(n)+'<span class="miniCalcCaret"></span>';if(active&&slot==='den'&&d) dShow=esc(d)+'<span class="miniCalcCaret"></span>';return '<span class="miniCalcFrac"><span class="miniCalcFracNum'+(active&&slot==='num'?' miniCalcFracSlotOn':'')+'">'+nShow+'</span><span class="miniCalcFracBar"></span><span class="miniCalcFracDen'+(active&&slot==='den'?' miniCalcFracSlotOn':'')+'">'+dShow+'</span></span>'}
function miniCalcFmtChar(ch){ch=String(ch||'');if(ch==='*')return '×';if(ch==='-')return '−';if(ch==='π')return 'π';if(ch==='√')return '√';return esc(ch)}
function miniCalcVisualLine(txt,active,cursor,decResult){txt=miniCalcLegacyFrac(txt);cursor=cursor|0;if(!txt&&!decResult)return active?'<span class="miniCalcCaret"></span>':'·';let html='',i=0;while(i<txt.length){if(txt.charAt(i)==='⟦'){let end=txt.indexOf('⟧',i);if(end<0){html+=esc(txt.slice(i));break}let inner=txt.slice(i+1,end),pipe=inner.indexOf('|'),num=pipe>=0?inner.slice(0,pipe):inner,den=pipe>=0?inner.slice(pipe+1):'',inTok=!!(active&&cursor>=i&&cursor<=end+1),slot='num';if(inTok){let rel=cursor-i-1;slot=rel<=num.length?'num':'den'}html+=miniCalcFracHtml(num,den,slot,inTok);i=end+1;continue}if(active&&cursor===i)html+='<span class="miniCalcCaret"></span>';let ch=txt[i];if(ch==='^'&&/[0-9+\-(]/.test(txt[i+1]||'')){let m=txt.slice(i).match(/^\^(\([^)]*\)|[0-9+\-.]+)/);if(m){html+='<sup>'+esc(m[1])+'</sup>';i+=m[0].length;continue}}html+=miniCalcFmtChar(ch);i++}if(active&&cursor>=txt.length)html+='<span class="miniCalcCaret"></span>';let main=html||'·';if(decResult)return '<span class="miniCalcLineInner"><span class="miniCalcLineMain">'+main+'</span><span class="miniCalcLineDec">'+miniCalcFmtDecHtml(decResult)+'</span></span>';return main}
function miniCalcSetFrac(st,frac,num,den){let ln=st.line|0,v=String(st.lines[ln]||''),tok='⟦'+String(num||'')+'|'+String(den||'')+'⟧';st.lines[ln]=v.slice(0,frac.start)+tok+v.slice(frac.end+1);st.cursor=frac.start+1+String(num||'').length}
function miniCalcBreakOp(ch){ch=String(ch||'');return'+-*/=)('.includes(ch)||ch==='−'||ch==='×'||ch==='÷'}
function miniCalcInsertInLine(st,ch){miniCalcClearDec(st,st.line|0);let ln=st.line|0,v=String(st.lines[ln]||''),c=miniCalcGetCursor(st),frac=miniCalcFracAt(v,c);if(frac&&miniCalcBreakOp(ch)){st.cursor=frac.end+1;miniCalcInsertAt(st,ch);return}if(frac){if(frac.slot==='num'){let n=frac.num+ch;st.lines[ln]=v.slice(0,frac.start)+'⟦'+n+'|'+frac.den+'⟧'+v.slice(frac.end+1);st.cursor=frac.start+1+n.length}else{let d=frac.den+ch;st.lines[ln]=v.slice(0,frac.start)+'⟦'+frac.num+'|'+d+'⟧'+v.slice(frac.end+1);st.cursor=frac.start+1+frac.num.length+1+d.length}return}miniCalcInsertAt(st,ch)}
function miniCalcDelInLine(st){miniCalcClearDec(st,st.line|0);let ln=st.line|0,v=String(st.lines[ln]||''),c=miniCalcGetCursor(st),frac=miniCalcFracAt(v,c);if(frac){if(frac.slot==='num'&&frac.num.length){let n=frac.num.slice(0,-1);st.lines[ln]=v.slice(0,frac.start)+'⟦'+n+'|'+frac.den+'⟧'+v.slice(frac.end+1);st.cursor=frac.start+1+n.length;return}if(frac.slot==='den'&&frac.den.length){let d=frac.den.slice(0,-1);st.lines[ln]=v.slice(0,frac.start)+'⟦'+frac.num+'|'+d+'⟧'+v.slice(frac.end+1);st.cursor=frac.start+1+frac.num.length+1+d.length;return}st.lines[ln]=v.slice(0,frac.start)+v.slice(frac.end+1);st.cursor=frac.start;return}miniCalcDelBefore(st)}
function miniCalcMoveCursor(st,key){let ln=st.line|0,v=String(st.lines[ln]||''),c=miniCalcGetCursor(st),frac=miniCalcFracAt(v,c);if(frac){if(key==='DOWN'||key==='RIGHT'&&frac.slot==='num'&&c>=frac.pipeAt){st.cursor=frac.pipeAt+1;return}if(key==='UP'||key==='LEFT'&&frac.slot==='den'&&c<=frac.pipeAt+1){st.cursor=frac.start+1+frac.num.length;return}if(key==='RIGHT'&&frac.slot==='den'){st.cursor=frac.end+1;return}if(key==='LEFT'&&frac.slot==='num'){st.cursor=frac.start;return}}if(key==='LEFT'){st.cursor=Math.max(0,c-1);return}if(key==='RIGHT'){st.cursor=Math.min(v.length,c+1);return}if(key==='DOWN'){st.cursor=Math.min(v.length,c+1);return}if(key==='UP'){st.cursor=Math.max(0,c-1)}}
function miniCalcPanelHtml(){let tape='';for(let i=0;i<4;i++)tape+='<div class="miniCalcLine miniCalcRow miniCalcLineEmpty" data-ln="'+i+'"><span class="miniCalcRowL">·</span><span class="miniCalcRowR">·</span></div>';let mem='';miniCalcVars().forEach(L=>{mem+='<button type="button" class="miniCalcMemLbl miniCalcMemLblBtn" id="miniCalcMem'+L+'" data-k="V'+L+'" title="STO '+L+' / ALPHA '+L+'">'+L+'</button>'});let top='<div class="miniCalcTopRow"><button type="button" class="miniCalcTopBtn miniCalcAlphaBtn" data-k="ALPHA" id="miniCalcBtnALPHA">ALPHA</button><div class="miniCalcDpad"><button type="button" class="miniCalcDpadBtn" data-k="LEFT">◀</button><button type="button" class="miniCalcDpadBtn" data-k="UP">▲</button><button type="button" class="miniCalcDpadBtn" data-k="DOWN">▼</button><button type="button" class="miniCalcDpadBtn" data-k="RIGHT">▶</button></div><button type="button" class="miniCalcTopBtn miniCalcAng" data-k="ANG" id="miniCalcBtnANG">DEG</button></div>';let s2='<div class="miniCalcGrid miniCalcSciRow"><button type="button" class="miniCalcSolveKey" data-k="SOLVE" title="Giải phương trình theo x">SOLVE</button><button type="button" data-k="SD">S⇔D</button><button type="button" class="miniCalcFracKey" data-k="FRAC" title="Phân số"><span class="miniCalcKeyFrac"><span></span><span class="miniCalcKeyFracBar"></span><span></span></span></button><button type="button" data-k="x">x</button><button type="button" data-k="PI">π</button><button type="button" data-k="E">×10ˣ</button></div>';let s3='<div class="miniCalcGrid miniCalcSciRow"><button type="button" data-k="SQRT">√</button><button type="button" data-k="^2">x²</button><button type="button" data-k="^3">x³</button><button type="button" data-k="^">x^</button><button type="button" data-k="10^">10ˣ</button><button type="button" data-k="RECIP">x⁻¹</button></div>';let s4='<div class="miniCalcGrid miniCalcSciRow"><button type="button" data-k="NEG">(−)</button><button type="button" data-k="sin">sin</button><button type="button" data-k="cos">cos</button><button type="button" data-k="tan">tan</button><button type="button" data-k="LOG">log</button><button type="button" data-k="LN">ln</button></div>';let s5='<div class="miniCalcGrid miniCalcSciRow"><button type="button" class="miniCalcMem" data-k="STO" id="miniCalcBtnSTO">STO</button><button type="button" data-k="ENG" title="Ký hiệu khoa học">ENG</button><button type="button" data-k="(">(</button><button type="button" data-k=")">)</button><button type="button" data-k="SD">S⇔D</button><button type="button" data-k="C">C</button></div>';let n1='<div class="miniCalcGrid miniCalcNumRow"><button type="button" data-k="7">7</button><button type="button" data-k="8">8</button><button type="button" data-k="9">9</button><button type="button" class="miniCalcDelKey" data-k="BS">DEL</button><button type="button" class="miniCalcAcKey" data-k="AC">AC</button></div>';let n2='<div class="miniCalcGrid miniCalcNumRow"><button type="button" data-k="4">4</button><button type="button" data-k="5">5</button><button type="button" data-k="6">6</button><button type="button" class="miniCalcOp" data-k="*">×</button><button type="button" class="miniCalcOp" data-k="/">÷</button></div>';let n3='<div class="miniCalcGrid miniCalcNumRow"><button type="button" data-k="1">1</button><button type="button" data-k="2">2</button><button type="button" data-k="3">3</button><button type="button" class="miniCalcOp" data-k="+">+</button><button type="button" class="miniCalcOp" data-k="-">−</button></div>';let n4='<div class="miniCalcGrid miniCalcNumRow"><button type="button" data-k="0">0</button><button type="button" data-k=".">.</button><button type="button" data-k="E">×10ˣ</button><button type="button" class="miniCalcAnsKey" data-k="INS" title="Ans">Ans</button><button type="button" class="miniCalcEq" data-k="=">=</button></div>';return '<div class="miniCalcHead"><div><b>▦ Máy tính khoa học</b><span>DEG/RAD · phân số · SOLVE x</span></div><button type="button" class="miniCalcCloseBtn" data-k="CLOSE" title="Ẩn máy tính">Đóng</button></div><div class="miniCalcShell"><div class="miniCalcDisplayZone"><div class="miniCalcTape miniCalcScreen" id="miniCalcTape">'+tape+'</div><div class="miniCalcHint" id="miniCalcHint">Bấm dòng để sửa · = tính · Ans chèn đáp án</div><div class="miniCalcMemBar">'+mem+'</div></div><div class="miniCalcKeysZone">'+top+s2+s3+s4+s5+n1+n2+n3+n4+'<button type="button" class="miniCalcIns" data-k="INS">→ Chèn vào ô đáp án</button></div></div>'}
function miniCalcGetCursor(st){let ln=st.line|0,v=String(st.lines[ln]||'');return Math.max(0,Math.min(v.length,st.cursor|0))}
function miniCalcInsertAt(st,text){miniCalcClearDec(st,st.line|0);let ln=st.line|0,v=String(st.lines[ln]||''),c=miniCalcGetCursor(st),t=String(text||'');if(!t)return;st.lines[ln]=v.slice(0,c)+t+v.slice(c);st.cursor=c+t.length}
function miniCalcDelBefore(st){miniCalcClearDec(st,st.line|0);let ln=st.line|0,v=String(st.lines[ln]||''),c=miniCalcGetCursor(st);if(c<=0)return;st.lines[ln]=v.slice(0,c-1)+v.slice(c);st.cursor=c-1}
function miniCalcTapLine(row,e){let st=miniCalcState();let ln=parseInt(row.getAttribute('data-ln'),10)||0;if(miniCalcHasResult(st,ln))miniCalcClearResult(st,ln);st.line=ln;let txt=String(st.lines[ln]||'');if(!txt){st.cursor=0;renderMiniCalcTape();syncMiniCalcDisplay();return}let tgt=e&&e.target;if(tgt){let fracEl=tgt.closest('.miniCalcFrac');if(fracEl){let fracs=[],i=0;while(i<txt.length){if(txt.charAt(i)==='⟦'){let end=txt.indexOf('⟧',i);if(end<0)break;let inner=txt.slice(i+1,end),pipe=inner.indexOf('|');fracs.push({start:i,end,num:pipe>=0?inner.slice(0,pipe):inner,den:pipe>=0?inner.slice(pipe+1):''});i=end+1}else i++}let all=row.querySelectorAll('.miniCalcFrac'),idx=Array.from(all).indexOf(fracEl);if(idx>=0&&fracs[idx]){let f=fracs[idx],den=tgt.closest('.miniCalcFracDen');st.cursor=den?f.start+1+f.num.length+1+f.den.length:f.start+1+f.num.length;renderMiniCalcTape();syncMiniCalcDisplay();return}}}let rect=row.getBoundingClientRect(),x=(e&&e.clientX!=null?e.clientX:rect.left)-rect.left,probe=document.createElement('span');probe.style.cssText='position:fixed;visibility:hidden;font:700 13.5px ui-monospace,Consolas,monospace;white-space:pre';document.body.appendChild(probe);let best=txt.length;for(let i=0;i<=txt.length;i++){probe.textContent=miniCalcToExpr(txt.slice(0,i))||' ';let w=probe.getBoundingClientRect().width;if(w<=x+2)best=i}document.body.removeChild(probe);st.cursor=best;renderMiniCalcTape();syncMiniCalcDisplay()}
function bindMiniCalcPanel(panel){if(!panel)return;if(panel._miniCalcClickFn)panel.removeEventListener('click',panel._miniCalcClickFn);panel._miniCalcClickFn=function(e){let row=e.target.closest('[data-ln]');if(row&&!e.target.closest('[data-k]')){miniCalcTapLine(row,e);return}let b=e.target.closest('[data-k]');if(b)miniCalcTap(b.getAttribute('data-k'),e)};panel.addEventListener('click',panel._miniCalcClickFn);panel._miniCalcBound=true}
function ensureMiniCalcBackdrop(){let bd=document.getElementById('miniCalcBackdrop');if(!bd){bd=document.createElement('div');bd.id='miniCalcBackdrop';bd.className='miniCalcBackdrop hide';bd.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();toggleMiniCalc()});document.body.appendChild(bd)}return bd}
function ensureMiniCalcPanel(){let bar=document.getElementById('learningQuickBar');if(!bar||!bar.parentNode)return;ensureMiniCalcBackdrop();let host=bar.parentNode,panel=document.getElementById('miniCalcPanel');if(!panel){panel=document.createElement('div');panel.id='miniCalcPanel';panel.className='miniCalcPanel hide';safeInsertAfter(host,panel,bar)}if(!panel.querySelector('#miniCalcTape')||panel.getAttribute('data-calc-v')!=='311'){panel.setAttribute('data-calc-v','311');panel.innerHTML=miniCalcPanelHtml();bindMiniCalcPanel(panel)}else if(!panel._miniCalcBound)bindMiniCalcPanel(panel);syncMiniCalcUI()}
function toggleMiniCalc(){MINI_CALC_OPEN=!MINI_CALC_OPEN;ensureMiniCalcPanel();syncMiniCalcUI()}
function miniCalcEmptyMem(){let m={};miniCalcVars().forEach(L=>{m[L]=''});return m}
function miniCalcState(qIdx){qIdx=qIdx==null?CUR:qIdx;if(!MINI_CALC_BY_Q[qIdx])MINI_CALC_BY_Q[qIdx]={lines:['','','',''],results:['','','',''],decLines:['','','',''],decExtras:['','','',''],line:0,cursor:0,mode:'',angMode:'DEG',xGuess:0,mem:miniCalcEmptyMem()};let st=MINI_CALC_BY_Q[qIdx];if(!st.mem)st.mem=miniCalcEmptyMem();if(!st.lines||st.lines.length<4)st.lines=['','','',''];if(!st.results||st.results.length<4)st.results=['','','',''];if(!st.decLines||st.decLines.length<4)st.decLines=['','','',''];if(!st.decExtras||st.decExtras.length<4)st.decExtras=['','','',''];if(st.lastExpr){st.lines[0]=st.lastExpr;st.lastExpr=''}if(st.resultDisp){st.results[0]=st.resultDisp;st.resultDisp=''}if(st.decExtra){st.decExtras[0]=st.decExtra;st.decExtra=''}if(!st.angMode)st.angMode='DEG';if(st.xGuess==null)st.xGuess=0;return st}
function miniCalcMountPanel(){let panel=document.getElementById('miniCalcPanel'),bar=document.getElementById('learningQuickBar');if(!panel||!bar||!bar.parentNode)return;if(MINI_CALC_OPEN){if(!panel._calcAnchor){panel._calcAnchor=document.createComment('miniCalcAnchor');safeInsertAfter(bar.parentNode,panel._calcAnchor,bar)}if(panel.parentNode!==document.body)document.body.appendChild(panel)}else if(panel._calcAnchor&&panel._calcAnchor.parentNode&&panel.parentNode===document.body)safeInsertBefore(panel._calcAnchor.parentNode,panel,panel._calcAnchor)}
function syncMiniCalcUI(){let mob=isMobileQuizUI();let btn=document.querySelector('.miniCalcBtn');if(btn){btn.classList.toggle('miniCalcActive',!!MINI_CALC_OPEN);btn.textContent=MINI_CALC_OPEN?'✕ Máy tính':'▦ Máy tính';btn.title=MINI_CALC_OPEN?'Ẩn máy tính':'Mở máy tính khoa học'}miniCalcMountPanel();let panel=document.getElementById('miniCalcPanel'),bd=document.getElementById('miniCalcBackdrop');if(panel)panel.classList.toggle('hide',!MINI_CALC_OPEN);if(bd)bd.classList.toggle('hide',!MINI_CALC_OPEN||mob);document.body.classList.toggle('mini-calc-open',!!MINI_CALC_OPEN);if(MINI_CALC_OPEN){if(mob)lockQuizPageScroll();syncMiniCalcDisplay()}else unlockQuizPageScroll()}
function renderMiniCalcTape(){let st=miniCalcState();miniCalcEnsureDec(st);let tape=document.getElementById('miniCalcTape');if(!tape)return;for(let i=0;i<4;i++){let row=tape.querySelector('[data-ln="'+i+'"]');if(!row)continue;let buf=String(st.lines[i]||''),res=String(st.results[i]||''),dec=String(st.decExtras[i]||''),on=i===(st.line|0),left='',right='';if(res){left='<span class="miniCalcExprShow">'+miniCalcVisualLine(buf,false,0,'')+'</span>';if(/^(-?)⟦/.test(res)||/√/.test(res))right=miniCalcVisualLine(res,false,0,'');else right='<span class="miniCalcResultBig">'+miniCalcFmtDisplay(res)+'</span>';if(dec)right+='<span class="miniCalcLineDec">'+miniCalcFmtDecHtml(dec)+'</span>'}else{left=on?miniCalcVisualLine(buf,true,on?st.cursor:0,''):(buf?miniCalcVisualLine(buf,false,0,''):'·');right='·'}row.innerHTML='<span class="miniCalcRowL">'+left+'</span><span class="miniCalcRowR">'+right+'</span>';row.classList.toggle('miniCalcLineEmpty',!buf&&!res);row.classList.toggle('miniCalcLineOn',on)}miniCalcVars().forEach(L=>{let el=document.getElementById('miniCalcMem'+L);if(el){let v=String(st.mem[L]||'').trim();el.classList.toggle('hasVal',!!v);el.classList.toggle('miniCalcMemPick',st.mode==='STO'||st.mode==='ALPHA');el.title=v?(L+': '+v+' · STO lưu / ALPHA gọi'):('STO lưu vào '+L+' / ALPHA gọi '+L)}});let bs=document.getElementById('miniCalcBtnSTO'),ba=document.getElementById('miniCalcBtnALPHA'),ang=document.getElementById('miniCalcBtnANG');if(bs)bs.classList.toggle('miniCalcModeOn',st.mode==='STO');if(ba)ba.classList.toggle('miniCalcModeOn',st.mode==='ALPHA');if(ang){ang.textContent=st.angMode||'DEG';ang.classList.toggle('miniCalcModeOn',true);ang.title='Bấm đổi DEG ↔ RAD'}}
function syncMiniCalcDisplay(){renderMiniCalcTape();let hint=document.getElementById('miniCalcHint'),st=miniCalcState(),el=document.getElementById('shortAnsInput');if(!hint)return;let mode=st.mode==='STO'?' · STO → bấm A–H để lưu':(st.mode==='ALPHA'?' · ALPHA → bấm A–H để gọi':'');let frac=miniCalcFracAt(st.lines[st.line]||'',miniCalcGetCursor(st)),fs=frac?(frac.slot==='num'?' · TỬ':' · MẪU'):'';let ang=' · '+(st.angMode||'DEG');let msg=st._memMsg||'';if(!el)hint.textContent='▥ phân số · DEG/RAD · STO/ALPHA A–H'+mode;else if(SUBMITTED||el.disabled)hint.textContent='Đã nộp bài.';else hint.textContent=(msg||ang+fs+mode+' · SOLVE: 12+3x hoặc 2*x+3=7 · ▲▼ đổi dòng')}
function miniCalcToExpr(s){s=miniCalcLegacyFrac(String(s||''));return s.replace(/(-?)⟦([^|⟦⟧]*)\|([^⟧]*)\⟧/g,function(_m,sg,a,b){return sg+'('+a+')/('+b+')'})}
function miniCalcFmtForAns(s){s=String(s||'').trim();let rm=s.match(/^(-?)√(\d+)(?:\/(\d+))?$/);if(rm)return rm[1]+'sqrt('+rm[2]+')'+(rm[3]?'/'+rm[3]:'');return miniCalcToExpr(s).replace(/\((\-?\d+)\)\/\((\d+)\)/g,function(_m,a,b){return a+'/'+b}).replace(/\s+/g,'')}
function miniCalcBalanceParens(s){s=String(s||'');let n=0;for(let i=0;i<s.length;i++){if(s[i]==='(')n++;else if(s[i]===')')n=Math.max(0,n-1)}while(n>0){s+=')';n--}return s}
function miniCalcPrepExpr(s){s=miniCalcBalanceParens(String(s||'').trim());return s}
function miniCalcNormExpr(s){s=miniCalcPrepExpr(miniCalcToExpr(s)).replace(/,/g,'.').replace(/×/g,'*').replace(/÷/g,'/').replace(/−/g,'-').replace(/²/g,'**2').replace(/³/g,'**3').replace(/(\d)([xX])/g,'$1*$2').replace(/([xX])(\()/g,'$1*$2').replace(/(\))([xX])/g,'$1*$2').replace(/\^(\()/g,'**$1').replace(/\^(\d+(?:\.\d+)?)/g,'**$1').replace(/\^/g,'**').replace(/√(\d+)/g,'Math.sqrt($1)');return s.replace(/(\d+(?:\.\d+)?)E([+\-]?\d+)/gi,'$1e$2')}
function miniCalcEvalCore(s,angMode){if(!s)return null;let rad=angMode==='RAD',S=function(x){x=Number(x);return Math.sin(rad?x:x*Math.PI/180)},C=function(x){x=Number(x);return Math.cos(rad?x:x*Math.PI/180)},T=function(x){x=Number(x);return Math.tan(rad?x:x*Math.PI/180)};s=s.replace(/π/g,'(Math.PI)').replace(/\bsin\s*\(/gi,'$S(').replace(/\bcos\s*\(/gi,'$C(').replace(/\btan\s*\(/gi,'$T(').replace(/\bln\s*\(/gi,'Math.log(').replace(/\blog\s*\(/gi,'Math.log10(').replace(/\bsqrt\s*\(/gi,'Math.sqrt(');try{let v=Function('$S','$C','$T','"use strict";return ('+s+')')(S,C,T);if(typeof v!=='number'||!isFinite(v))return null;return v}catch(e){return null}}
function miniCalcEvalAtX(raw,xVal,angMode){if(angMode==null){try{angMode=miniCalcState().angMode||'DEG'}catch(e){angMode='DEG'}}let mem=null;try{mem=miniCalcState().mem}catch(e){}let s=miniCalcNormExpr(raw);if(mem)s=miniCalcSubstMem(s,mem);if(!s)return null;s=s.replace(/(?:^|[^a-zA-Z$])x(?![a-zA-Z])/gi,function(m){return m.slice(0,-1)+'('+xVal+')'});return miniCalcEvalCore(s,angMode)}
function miniCalcSplitEq(s){s=String(s||'').trim().replace(/−/g,'-');let i=-1,d=0;for(let j=0;j<s.length;j++){let c=s[j];if(c==='(')d++;else if(c===')')d=Math.max(0,d-1);else if(c==='='&&d===0){i=j;break}}if(i<0)return {lhs:s,rhs:'0'};return {lhs:s.slice(0,i).trim(),rhs:s.slice(i+1).trim()||'0'}}
function miniCalcSolveForX(line,guess,angMode){line=String(line||'').trim();if(!/[xX]/.test(line))return null;let p=miniCalcSplitEq(line),f=function(x){let a=miniCalcEvalAtX(p.lhs,x,angMode),b=miniCalcEvalAtX(p.rhs,x,angMode);if(a==null||b==null)return null;return a-b},snap=function(x){return miniCalcSnapNum(x)};let seeds=[Number(guess)||0,-10,-5,-4,-3,-2,-1,1,2,3,4,5,10,0.5,-0.5];for(let si=0;si<seeds.length;si++){let x=seeds[si],fx=f(x);if(fx==null)continue;if(Math.abs(fx)<1e-9)return snap(x);for(let it=0;it<32;it++){let h=1e-4,df=(f(x+h)-f(x-h))/(2*h);if(!isFinite(df)||Math.abs(df)<1e-12)break;x=x-fx/df;if(!isFinite(x))break;fx=f(x);if(fx==null)break;if(Math.abs(fx)<1e-9)return snap(x);if(Math.abs(x)>1e6)break}}for(let a=-20;a<=20;a+=0.25){let fa=f(a),fb=f(a+0.25);if(fa==null||fb==null)continue;if(fa*fb<=0){let lo=a,hi=a+0.25;for(let it=0;it<48;it++){let mid=(lo+hi)/2,fm=f(mid);if(fm==null)break;if(Math.abs(fm)<1e-9||hi-lo<1e-10)return snap(mid);if(fa*fm<=0){hi=mid;fb=fm}else{lo=mid;fa=fm}}return snap((lo+hi)/2)}}return null}
function miniCalcApplySolve(st,ln){ln=ln|0;let v=String(st.lines[ln]||'').trim();if(!v||!/[xX]/.test(v)){st._memMsg='Gõ PT có x: 12+3x hoặc 2*x+3=7';return false}let x=miniCalcSolveForX(v,st.xGuess==null?0:st.xGuess,st.angMode);if(x==null){st._memMsg='Không tìm được nghiệm x';return false}x=miniCalcSnapNum(x);st.xGuess=x;miniCalcSetResult(st,ln,v,'x='+miniCalcFmtNum(x),'');st._memMsg='SOLVE: x='+miniCalcFmtNum(x);return true}
function miniCalcExactTrig(s,angMode){s=String(s||'').trim().replace(/−/g,'-');let m=s.match(/^(sin|cos|tan)\s*\(\s*(-?\d+(?:\.\d+)?)\s*\)$/i);if(!m)return null;let fn=m[1].toLowerCase(),a=Number(m[2]);if(!isFinite(a))return null;if(angMode==='RAD')return null;let deg=((Math.round(a)%360)+360)%360,tab={sin:{0:'0',30:'1/2',45:'√2/2',60:'√3/2',90:'1',120:'√3/2',135:'√2/2',150:'1/2',180:'0',210:'-1/2',225:'-√2/2',240:'-√3/2',270:'-1',300:'-√3/2',315:'-√2/2',330:'-1/2'},cos:{0:'1',30:'√3/2',45:'√2/2',60:'1/2',90:'0',120:'-1/2',135:'-√2/2',150:'-√3/2',180:'-1',210:'-√3/2',225:'-√2/2',240:'-1/2',270:'0',300:'1/2',315:'√2/2',330:'√3/2'},tan:{0:'0',30:'√3/3',45:'1',60:'√3',90:null,120:'-√3',135:'-1',150:'-√3/3',180:'0',210:'√3/3',225:'1',240:'√3',270:null,300:'-√3',315:'-1',330:'-√3/3'}};let v=(tab[fn]||{})[String(deg)];return v==null?null:v}
function miniCalcMatchRadical(v){if(v==null||!isFinite(v))return null;let t=[[Math.sqrt(3)/2,'√3/2'],[Math.sqrt(3),'√3'],[Math.sqrt(2)/2,'√2/2'],[Math.sqrt(2),'√2'],[Math.sqrt(3)/3,'√3/3'],[1/2,'1/2'],[1/3,'1/3'],[2/3,'2/3'],[-Math.sqrt(3)/2,'-√3/2'],[-Math.sqrt(3),'-√3'],[-Math.sqrt(2)/2,'-√2/2'],[-Math.sqrt(3)/3,'-√3/3'],[-1/2,'-1/2']];for(let i=0;i<t.length;i++)if(Math.abs(v-t[i][0])<1e-9)return t[i][1];return null}
function miniCalcToFraction(dec,maxDen){dec=Number(dec);if(!isFinite(dec))return null;maxDen=maxDen||10000;let sign=dec<0?'-':'';dec=Math.abs(dec);let whole=Math.floor(dec),frac=dec-whole,best={n:0,d:1,err:frac};for(let d=1;d<=maxDen;d++){let n=Math.round(frac*d),err=Math.abs(frac-n/d);if(err<best.err){best={n,d,err};if(err<1e-9)break}}if(!best.n&&!whole)return sign+'0';let n=whole*best.d+best.n;return sign+'⟦'+n+'|'+best.d+'⟧'}
function miniCalcEvalExpr(s,angMode){if(angMode==null){try{angMode=miniCalcState().angMode||'DEG'}catch(e){angMode='DEG'}}let mem=null;try{mem=miniCalcState().mem}catch(e){}s=miniCalcNormExpr(s);if(mem)s=miniCalcSubstMem(s,mem);if(!s)return null;if(/(?:^|[^a-zA-Z$])[xX](?![a-zA-Z])/.test(s))return null;return miniCalcEvalCore(s,angMode)}
function miniCalcSnapNum(v){if(v==null||!isFinite(v))return v;let r=Math.round(v);if(Math.abs(v-r)<1e-9)return r;let h=Math.round(v*2)/2;if(Math.abs(v-h)<1e-9)return h;let fr=miniCalcNormFracLine(miniCalcToFraction(v,10000)||'');if(fr){let p=miniCalcParseFracTok(fr);if(p){let n=Number((p.sign||'')+p.num),d=Number(p.den);if(d&&Math.abs(n/d-v)<1e-8)return n/d}}return v}
function miniCalcFmtNum(v){v=miniCalcSnapNum(v);if(v==null||!isFinite(v))return '';let s=String(v);if(s.includes('e')||s.includes('E'))s=Number(v).toPrecision(12);if(s.includes('.'))s=s.replace(/\.?0+$/,'');return s.slice(0,16)}
function miniCalcInsertAnswer(){let st=miniCalcState(),ln=st.line|0,v='',dec='';if(miniCalcHasResult(st,ln)){v=String(st.results[ln]||'').trim();dec=String(st.decExtras[ln]||'').trim()}else{for(let i=3;i>=0;i--){if(String(st.results[i]||'').trim()||String(st.decExtras[i]||'').trim()){v=String(st.results[i]||'').trim();dec=String(st.decExtras[i]||'').trim();break}}}if(!v&&!dec)return;let out='';if(v&&/^(-?)⟦(\-?\d+)\|(\d+)⟧$/.test(v.trim()))out=miniCalcFmtForAns(v);else if(dec)out=dec;else if(/^x=/i.test(v))out=miniCalcFmtForAns(v);else{let num=miniCalcEvalExpr(v);out=num!=null?miniCalcFmtNum(num):miniCalcFmtForAns(v)}if(!out)return;let el=document.getElementById('shortAnsInput');if(!el||SUBMITTED||el.disabled)return;el.value=String(out).slice(0,80);saveShortAnswer()}
function miniCalcTap(key,e){if(e){e.preventDefault();e.stopPropagation()}if(key==='CLOSE'){toggleMiniCalc();return}if(SUBMITTED&&!USER.is_admin)return;let st=miniCalcState(),ln=st.line|0;if(key!=='STO'&&key!=='ALPHA'&&!/^V[A-H]$/.test(key))st._memMsg='';if(key==='INS'){miniCalcInsertAnswer();return}if(key==='STO'){st._memMsg='';st.mode=st.mode==='STO'?'':'STO';syncMiniCalcDisplay();return}if(key==='ALPHA'){st._memMsg='';st.mode=st.mode==='ALPHA'?'':'ALPHA';syncMiniCalcDisplay();return}if(key==='ANG'){st.angMode=st.angMode==='RAD'?'DEG':'RAD';syncMiniCalcDisplay();return}if(/^V[A-H]$/.test(key)){miniCalcUseVar(st,ln,key.slice(1));syncMiniCalcDisplay();return}if(key==='SOLVE'){if(miniCalcHasResult(st,ln))miniCalcRestoreEdit(st);miniCalcApplySolve(st,ln);renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='UP'){miniCalcRestoreEdit(st);st.line=ln<=0?3:ln-1;if(!st.lines[st.line]&&!miniCalcHasResult(st,st.line))st.cursor=0;else st.cursor=String(st.lines[st.line]||'').length;renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='DOWN'){miniCalcRestoreEdit(st);st.line=ln>=3?0:ln+1;if(!st.lines[st.line]&&!miniCalcHasResult(st,st.line))st.cursor=0;else st.cursor=String(st.lines[st.line]||'').length;renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='LEFT'||key==='RIGHT'){miniCalcRestoreEdit(st);miniCalcMoveCursor(st,key);renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='AC'){st.lines=['','','',''];st.results=['','','',''];st.decLines=['','','',''];st.decExtras=['','','',''];st.line=0;st.cursor=0;st.mode='';renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='C'){if(miniCalcHasResult(st,ln))miniCalcRestoreEdit(st);st.lines[ln]='';miniCalcClearDec(st,ln);st.cursor=0;renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='BS'){if(miniCalcHasResult(st,ln))miniCalcRestoreEdit(st);miniCalcDelInLine(st);renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='SD'){if(miniCalcHasResult(st,ln))miniCalcRestoreEdit(st);miniCalcEnsureDec(st);let v=String(st.lines[ln]||'').trim(),pf=miniCalcParseFracTok(v);if(pf){let n=Number((pf.sign||'')+pf.num),d=Number(pf.den);if(st.decExtras[ln]){st.lines[ln]=st.decExtras[ln];st.decExtras[ln]='';st.cursor=st.lines[ln].length}else{st.decExtras[ln]=miniCalcFmtRecurring(n,d)}}else{let r=miniCalcEvalExpr(v);if(r!=null){let f=miniCalcNormFracLine(miniCalcToFraction(r)||'');if(f){st.lines[ln]=f;st.decExtras[ln]='';st.cursor=f.length}}}renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='='){if(/[xX]/.test(String(st.lines[ln]||''))){miniCalcMaybeNewEntry(st,key);miniCalcInsertInLine(st,'=');renderMiniCalcTape();syncMiniCalcDisplay();return}if(miniCalcHasResult(st,ln))miniCalcRestoreEdit(st);miniCalcApplyEquals(st,ln);renderMiniCalcTape();syncMiniCalcDisplay();return}if(key==='FRAC'){miniCalcMaybeNewEntry(st,key);miniCalcClearDec(st,ln);let c=miniCalcGetCursor(st),v=String(st.lines[ln]||''),ins=miniCalcFracTok();st.lines[ln]=v.slice(0,c)+ins+v.slice(c);st.cursor=c+1;renderMiniCalcTape();syncMiniCalcDisplay();return}if(String(st.lines[ln]||'').length>=56)return;miniCalcMaybeNewEntry(st,key);let ch=key;if(key==='sin')ch='sin(';else if(key==='cos')ch='cos(';else if(key==='tan')ch='tan(';else if(key==='SQRT')ch='sqrt(';else if(key==='LN')ch='ln(';else if(key==='LOG')ch='log(';else if(key==='PI')ch='π';else if(key==='NEG')ch='(-';else if(key==='RECIP')ch='^(-1)';else if(key==='ENG')ch='E';else if(key==='^')ch='^(';else if(key==='10^')ch='*10^(';else if(key==='*'||key==='/')ch=key;else if(key==='^2'||key==='^3')ch=key;miniCalcInsertInLine(st,ch);renderMiniCalcTape();syncMiniCalcDisplay()}
function syncLearningChrome(){ensureLearningQuickBar();syncLearningToggleUI();syncMiniCalcUI()}
function syncLearningToggleUI(){let kind=LEARNING_OPEN_KIND||'';document.querySelectorAll('[data-learning-toggle]').forEach(btn=>{let k=btn.getAttribute('data-learning-toggle')||'';btn.classList.toggle('learningActive',!!kind&&k===kind)})}
/** Nhãn nút thu/mở panel Phương pháp */
function learningCollapseBtnLabel(){return LEARNING_PANEL_COLLAPSED?'▼ Mở':'▲ Thu'}
/** HTML hàng tiêu đề panel — bấm tiêu đề hoặc ▲ Thu để gập/mở */
function learningPanelTitleHtml(title){return '<div class="learningTitleRow" onclick="toggleLearningPanelCollapse(event)"><b>'+title+'</b><div class="learningTitleBtns"><button type="button" class="learningCollapseBtn" onclick="toggleLearningPanelCollapse(event)">'+learningCollapseBtnLabel()+'</button><button type="button" class="learningCloseBtn" onclick="closeLearningPanel(event)">✕</button></div></div>'}
function toggleLearningPanelCollapse(e){if(e)e.stopPropagation();LEARNING_PANEL_COLLAPSED=!LEARNING_PANEL_COLLAPSED;let hb=document.getElementById('hintBox');if(!hb||!hb.classList.contains('learningOpen'))return;hb.classList.toggle('learningCollapsed',LEARNING_PANEL_COLLAPSED);let btn=hb.querySelector('.learningCollapseBtn');if(btn)btn.textContent=learningCollapseBtnLabel()}
function closeLearningPanel(e){if(e&&e.stopPropagation)e.stopPropagation();if(LEARNING_OPEN_KIND==='translate')stopTranslateEnSpeech();LEARNING_OPEN_KIND='';LEARNING_PANEL_COLLAPSED=false;syncLearningToggleUI();let hb=document.getElementById('hintBox');if(!hb)return;hb.classList.remove('learningOpen','learningCollapsed','aiAssistOpen','openclawOpen','ldvlFloatChatPanel','ldvlChatCollapsed','ldvlChatMax','ldvlChatCustomPos');let canAi=USER.can_ai_hint!==false;if(HINT_LOADING&&HINT_LOADING_Q===CUR&&!HINT_BY_Q[CUR]){showHintLoadingBox();return}if(canAi&&(HINT_BY_Q[CUR]||SIMILAR_BY_Q[CUR])){renderHintBox(HINT_BY_Q[CUR]||{});return}if(canAi&&SIMILAR_LOADING&&SIMILAR_LOADING_Q===CUR){hb.classList.remove('hide');hb.innerHTML='<b>📝 Tạo câu tương tự</b><div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang gọi AI…</b></div></div>';return}hb.classList.add('hide');hb.innerHTML=''}
function ldvlLsGet(key,dflt){try{let v=localStorage.getItem(key);return v==null?dflt:v==='1'}catch(e){return dflt}}
function ldvlLsSet(key,val){try{localStorage.setItem(key,val?'1':'0')}catch(e){}}
function openLearningPanel(kind){
  kind=(kind==='theory')?'theory':'method';
  if(LEARNING_OPEN_KIND===kind){closeLearningPanel();return;}
  LEARNING_PANEL_COLLAPSED=false;
  LEARNING_OPEN_KIND=kind;
  loadLearningPanelContent(kind);
}
function renderLearningField(label,val){if(!String(val||'').trim())return '';return '<div style="margin-top:8px"><b>'+esc(label)+'</b><div class="learningItem hintMath">'+formatHintDisplay(val)+'</div></div>'}
function renderLearningItem(kind,it){it=it||{};let head=kind==='method'?esc(it.TenPhuongPhap||it.DangBaiTap||'Phương pháp'):esc(it.TieuDe||'Lý thuyết');let body='';if(kind==='theory'){body=[renderLearningField('Lý thuyết SGK',it.LyThuyet),renderLearningField('Tóm tắt',it.NoiDungTomTat),renderLearningField('Kiến thức trọng tâm',it.KienThucTrongTam),renderLearningField('Công thức',it.CongThuc),renderLearningField('Đơn vị',it.DonVi),renderLearningField('Lưu ý',it.LuuY),renderLearningField('Sai lầm thường gặp',it.SaiLamThuongGap),renderLearningField('Ví dụ mẫu',it.ViDuMau)].join('')}else{body=[renderLearningField('Dấu hiệu nhận biết',it.DauHieuNhanBiet),renderLearningField('Các bước giải',it.CacBuocGiai),renderLearningField('Công thức sử dụng',it.CongThucSuDung),renderLearningField('Mẹo nhanh',it.MeoNhanh),renderLearningField('Lỗi sai thường gặp',it.LoiSaiThuongGap),renderLearningField('Ví dụ mẫu',it.ViDuMau)].join('')}return '<div class="learningItem" style="margin-top:10px;padding:10px;border:1px solid var(--border);border-radius:10px;background:var(--surface)"><b>'+head+'</b>'+body+'</div>'}
function theoryLearningLatexHtml(q,items){let item=exactTheoryLearningItem(items||[],q);let src='';if(item){src=normalizeTheoryLatexSourceClient(item.NoiDungLaTeX||'');if(!src&&/\\begin\s*\{\s*(dn|note|vidu)/i.test(String(item.LyThuyet||'')))src=normalizeTheoryLatexSourceClient(item.LyThuyet);if(!src)src=normalizeTheoryLatexSourceClient(theorySourceFromLegacyTheoryItem(item))}if(!src)return '';let actions=USER.is_admin?'<div class="dangTheoryActions" style="margin:0 0 10px"></div>':'';return actions+'<div class="learningTheoryLatex">'+renderTheoryLatexBlocks(src)+'</div>'}function methodLearningLatexHtml(q,entry){
  let item=entry&&entry.item;
  let src=item?normalizeTheoryLatexSourceClient(item.NoiDungLaTeX||theorySourceFromLegacyItem(item)):'';
  if(!src)return '';
  let actions=USER.is_admin?'<div class="dangTheoryActions" style="margin:0 0 10px"></div>':'';
  return actions+'<div class="learningMethodLatex">'+renderTheoryLatexBlocks(src)+'</div>';
}
/** Vẽ nội dung panel vào #hintBox — gọi sau loadLearningPanelContent */
function renderLearningPanel(kind,items,meta){
  let hb=document.getElementById('hintBox');
  if(!hb||LEARNING_OPEN_KIND!==kind)return;
  let q=applyResolvedDang(QUESTIONS[CUR]||{});
  let title=kind==='method'?'🧭 Phương pháp giải':'📚 Lý thuyết';
  let scope=[q.Mon,q.Lop,q.Chuong,q.BaiHoc].filter(x=>String(x||'').trim()).join(' · ');
  if(kind==='method'&&q.DangBaiTap)scope+=(scope?' · ':'')+q.DangBaiTap;
  let body='';
  if(kind==='method'){
    let latex=methodLearningLatexHtml(q,DANG_THEORY_CACHE[dangTheoryKey(q)]||{item:exactDangTheoryItem(items||[],q)});
    if(latex)body=latex;
    else if(!items||!items.length){
      body='<div class="muted" style="margin-top:8px;line-height:1.5">Chưa có phương pháp cho dạng này.'
        +(meta&&meta.learning_error?'<br><span style="color:#991b1b">'+esc(meta.learning_error)+'</span>':'')
        +(USER.is_admin?'<br>ADMIN: bấm <b>📘 Soạn khung dạng</b> hoặc <b>🤖 Tạo PP + lưu GGS</b> ở panel bên phải.':'')
        +'</div>';
    }else body=items.map(it=>renderLearningItem(kind,it)).join('');
  }else{
    let latex=theoryLearningLatexHtml(q,items||[]);
    if(latex)body=latex;
    else if(!items||!items.length){
      body='<div class="muted" style="margin-top:8px;line-height:1.5">Chưa có lý thuyết trong Sheet cho phạm vi này.'
        +(meta&&meta.learning_error?'<br><span style="color:#991b1b">'+esc(meta.learning_error)+'</span>':'')
        +(USER.is_admin?'<br>ADMIN: bấm <b>📚 Soạn khung lý thuyết</b> ở panel bên phải.':'')
        +'</div>';
    }else body=items.map(it=>renderLearningItem(kind,it)).join('');
  }
  hb.classList.remove('hide');
  hb.classList.add('learningOpen');
  hb.classList.toggle('learningCollapsed',!!LEARNING_PANEL_COLLAPSED);
  let simHtml=(kind==='method'&&USER.is_admin)?renderDangSimilarityWarnHtml(DANG_SIMILARITY_CACHE[dangSimilarityCacheKey(q)]||null,q):'';
  hb.innerHTML='<div class="learningPanelShell">'
    +learningPanelTitleHtml(title)
    +(scope?'<div class="muted learningPanelMeta">'+esc(scope)+'</div>':'')
    +'<div class="learningPanelBody">'+simHtml+body+'</div></div>';
  syncLearningToggleUI();
  typesetQuizMath().then(()=>{let b=document.querySelector('#hintBox .learningPanelBody');if(b)b.scrollTop=0});
}
async function loadLearningPanelContent(kind,force){kind=(kind==='theory')?'theory':'method';let hb=document.getElementById('hintBox');if(!hb||LEARNING_OPEN_KIND!==kind)return;let q=applyResolvedDang(QUESTIONS[CUR]||{});let cacheKey=learningCacheKey(kind,q);let title=kind==='method'?'🧭 Phương pháp giải':'📚 Lý thuyết';if(!force&&LEARNING_CACHE[cacheKey]){let cached=LEARNING_CACHE[cacheKey];if(kind==='method'){let items=cached.items||[];if(!DANG_THEORY_CACHE[dangTheoryKey(q)])DANG_THEORY_CACHE[dangTheoryKey(q)]={item:exactDangTheoryItem(items,q),meta:cached.meta||{}};afterDangTheoryPrefetch(q,DANG_THEORY_CACHE[dangTheoryKey(q)],cached.meta||cached)}else afterBaiTheoryPrefetch(q,cached.meta||cached,cached.meta||cached);renderLearningPanel(kind,cached.items||[],cached.meta||{});return}if(LEARNING_LOADING)return;LEARNING_LOADING=kind;hb.classList.remove('hide');hb.classList.add('learningOpen');hb.classList.remove('hintBoxLoading');hb.classList.toggle('learningCollapsed',false);hb.innerHTML='<div class="learningPanelShell">'+learningPanelTitleHtml(title)+'<div class="learningPanelBody"><div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang tải học liệu…</b></div></div></div></div>';try{let body={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||''};if(kind==='method')body.DangBaiTap=q.DangBaiTap||'';let url=kind==='method'?'/api/learning/method':'/api/learning/theory';let j=await api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});LEARNING_CACHE[cacheKey]={items:j.items||[],meta:j};if(kind==='method'){let entry={item:exactDangTheoryItem(j.items||[],q),meta:j};DANG_THEORY_CACHE[dangTheoryKey(q)]=entry;if(j.similarity_report)DANG_SIMILARITY_CACHE[dangSimilarityCacheKey(q)]=j.similarity_report;afterDangTheoryPrefetch(q,entry,j)}else afterBaiTheoryPrefetch(q,j,j);if(LEARNING_OPEN_KIND===kind)renderLearningPanel(kind,j.items||[],j)}catch(e){if(LEARNING_OPEN_KIND===kind)hb.innerHTML='<div class="learningPanelShell">'+learningPanelTitleHtml(title)+'<div class="learningPanelBody"><div class="muted" style="margin-top:8px">Không tải được học liệu: '+esc(e.message||e)+'</div></div></div>'}finally{LEARNING_LOADING=false}}
function dangSimilarityCacheKey(q){q=q||{};return [q.Mon,q.Lop,q.Chuong,q.BaiHoc,q.DangBaiTap].map(x=>normText(String(x||''))).join('|')}
async function loadDangSimilarityReport(q,force,withAi){if(!USER.is_admin||!q||!String(q.DangBaiTap||'').trim())return null;let key=dangSimilarityCacheKey(q);if(!force&&DANG_SIMILARITY_CACHE[key]&&!withAi)return DANG_SIMILARITY_CACHE[key];if(DANG_SIMILARITY_LOADING&&!force)return DANG_SIMILARITY_CACHE[key]||null;DANG_SIMILARITY_LOADING=true;try{let body={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',DangBaiTap:q.DangBaiTap||'',MaDe:q.MaDe||CURRENT_MADE||'',ID:q.ID||'',with_ai:!!withAi};let j=withAi?await adminApiPost('/api/admin/dang-similarity',body):await api('/api/admin/dang-similarity',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});DANG_SIMILARITY_CACHE[key]=j;return j}catch(e){return {ok:false,error:e.message||String(e),summary:'Không phân tích được: '+(e.message||e)}}finally{DANG_SIMILARITY_LOADING=false}}
function renderDangSimilarityWarnHtml(report,q){if(!report||!USER.is_admin)return '';let warns=(report.current_warnings&&report.current_warnings.length)?report.current_warnings:[];if(!warns.length&&report.pair_count>0){warns=(report.pairs||[]).slice(0,4).map(p=>p.suggestion||'')}if(!warns.length&&!report.pair_count)return '';let head=report.pair_count?('<b>⚠️ Trùng lặp trong dạng ≥70%</b><div class="muted" style="font-size:12px;margin-top:4px">'+esc(report.summary||'')+'</div>'):('<b>✅ Đa dạng trong dạng</b><div class="muted" style="font-size:12px;margin-top:4px">'+esc(report.summary||'')+'</div>');let list=warns.length?('<ul>'+warns.slice(0,5).map(w=>'<li>'+esc(w)+'</li>').join('')+'</ul>'):'';let ai=report.ai_advice?('<div class="dangSimAi"><b>🤖 Gợi ý AI:</b><br>'+formatHintDisplay(report.ai_advice)+'</div>'):'';let btn=report.pair_count?'<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap"><button type="button" class="btnGreen" onclick="adminAnalyzeDangSimilarity(false)">🗑️ Xóa/gộp trùng</button><button type="button" class="btn2" onclick="adminAnalyzeDangSimilarity(true)">🤖 Gợi ý AI</button></div>':'';return '<div class="dangSimWarn">'+head+list+ai+btn+'</div>'}
function dangSimDefaultDeleteRow(pair){let ra=parseInt(pair.row_a,10)||0,rb=parseInt(pair.row_b,10)||0;if(pair.kind!=='question_question')return 0;if(ra&&rb)return ra>=rb?ra:rb;return rb||ra}
function ensureDangSimModal(){let m=document.getElementById('dangSimModal');if(m)return m;m=document.createElement('div');m.id='dangSimModal';m.className='modal hide';m.innerHTML='<div class="modalBox"><h3 id="dangSimTitle">⚠️ Trùng lặp trong dạng</h3><div id="dangSimSummary" class="muted" style="font-size:13px;line-height:1.45"></div><div id="dangSimAiBox" class="dangSimAi hide"></div><div id="dangSimList"></div><div id="dangSimStatus" class="muted" style="font-size:12px;margin-top:8px"></div><div class="row" style="justify-content:flex-end;gap:8px;margin-top:12px;flex-wrap:wrap"><button type="button" class="btn2" onclick="closeDangSimilarityModal()">Đóng</button><button type="button" class="btn2" id="dangSimAiBtn" onclick="adminAnalyzeDangSimilarity(true)">🤖 Gợi ý AI</button><button type="button" class="btnGreen" id="dangSimDeleteBtn" onclick="executeDangSimilarityDelete()">🗑️ Xóa các câu đã chọn</button></div></div>';document.body.appendChild(m);return m}
function closeDangSimilarityModal(){let m=document.getElementById('dangSimModal');if(m)m.classList.add('hide')}
function renderDangSimilarityModal(rep){window.DANG_SIM_MODAL_REPORT=rep||null;ensureDangSimModal();let m=document.getElementById('dangSimModal');let sum=document.getElementById('dangSimSummary');let list=document.getElementById('dangSimList');let aiBox=document.getElementById('dangSimAiBox');let st=document.getElementById('dangSimStatus');if(!m||!sum||!list)return;if(sum)sum.textContent=rep.summary||'';if(aiBox){if(rep.ai_advice){aiBox.classList.remove('hide');aiBox.innerHTML='<b>🤖 Gợi ý AI:</b><br>'+formatHintDisplay(rep.ai_advice)}else{aiBox.classList.add('hide');aiBox.innerHTML=''}}if(st)st.textContent='Tick câu sẽ xóa (mặc định giữ dòng nhỏ hơn — câu cũ hơn). Có thể bấm «Xem» để mở câu trước khi xóa.';let pairs=(rep.pairs||[]).filter(p=>p.kind==='question_question');if(!pairs.length){list.innerHTML='<div class="muted">Không có cặp câu–câu để xóa tự động. Cặp câu–khung PP cần sửa khung Phương pháp thủ công.</div>'}else{list.innerHTML=pairs.map((p,i)=>{let pct=Math.round(parseFloat(p.similarity||0)*100);let delRow=dangSimDefaultDeleteRow(p);let keepRow=delRow===(parseInt(p.row_a,10)||0)?(parseInt(p.row_b,10)||0):(parseInt(p.row_a,10)||0);let delId=delRow===(parseInt(p.row_a,10)||0)?(p.id_a||''):(p.id_b||'');let snip=esc(shortText(p.snippet_a||'',90));return `<div class="dangSimPair" data-pair="${i}"><div class="dangSimPairHead">${pct}% · ${esc(p.id_a||'?')} (dòng ${p.row_a||'?'}) ↔ ${esc(p.id_b||'?')} (dòng ${p.row_b||'?'})</div><div class="dangSimPairSnip">${snip}</div><div class="dangSimPairActs"><label><input type="checkbox" class="dangSimDelChk" data-del-row="${delRow}" data-del-id="${escAttr(delId)}" checked> Xóa dòng ${delRow} · ${esc(delId||'—')} (giữ dòng ${keepRow})</label><button type="button" class="btn2 btnSmall" onclick="jumpDangSimQuestion(${parseInt(p.row_a,10)||0})">👁 A</button><button type="button" class="btn2 btnSmall" onclick="jumpDangSimQuestion(${parseInt(p.row_b,10)||0})">👁 B</button></div></div>`}).join('')}m.classList.remove('hide');try{typesetQuizMath()}catch(e){}}
function jumpDangSimQuestion(row){row=parseInt(row,10)||0;if(!row)return;let idx=QUESTIONS.findIndex(q=>parseInt(q._row,10)===row);if(idx<0){alert('Câu dòng '+row+' không có trong phiên làm bài hiện tại.\nMở đề chứa câu này hoặc tìm trên Google Sheet.');return}saveCurrent();CUR=idx;renderNav();renderQuestion();closeDangSimilarityModal()}
function collectDangSimDeleteRows(){let rows=[];document.querySelectorAll('#dangSimList .dangSimDelChk:checked').forEach(ch=>{let r=parseInt(ch.getAttribute('data-del-row'),10)||0;if(r>1)rows.push(r)});return [...new Set(rows)]}
function purgeLocalQuestionsAfterDeletes(rows,ids){let dels=new Set(rows.map(r=>parseInt(r,10)).filter(r=>r>1));if(!dels.size&&!(ids&&ids.length))return;if(ids&&ids.length)clearOfflineDecksContainingIds(ids);else{let idList=[];for(let qq of QUESTIONS){if(dels.has(parseInt(qq._row,10)||0))idList.push(qq.ID||'')}clearOfflineDecksContainingIds(idList)}clearOfflineDeckForMade(CURRENT_MADE);if(!dels.size)return;let removedIdx=[];for(let i=QUESTIONS.length-1;i>=0;i--){if(dels.has(parseInt(QUESTIONS[i]._row,10)||0))removedIdx.push(i)}removedIdx.sort((a,b)=>b-a);for(let i of removedIdx){QUESTIONS.splice(i,1);reindexQuizMaps(i)}for(let qq of QUESTIONS){let r=parseInt(qq._row,10)||0;let shift=[...dels].filter(d=>d<r).length;if(shift)qq._row=r-shift}if(CUR>=QUESTIONS.length)CUR=Math.max(0,QUESTIONS.length-1)}
async function executeDangSimilarityDelete(){if(!USER.is_admin)return;let rows=collectDangSimDeleteRows();if(!rows.length){alert('Chưa tick câu nào để xóa.');return}if(!confirm('Xóa '+rows.length+' câu khỏi Google Sheet?\n\nDòng: '+rows.sort((a,b)=>a-b).join(', ')+'\n\nHành động không hoàn tác.'))return;if(!confirm('Xác nhận lần 2: chắc chắn xóa '+rows.length+' câu?'))return;let btn=document.getElementById('dangSimDeleteBtn');let st=document.getElementById('dangSimStatus');if(btn){btn.disabled=true;btn.textContent='⏳ Đang xóa…'}if(st)st.textContent='⏳ Đang xóa '+rows.length+' dòng trên Google Sheet…';try{let j=await api('/api/admin/dang-similarity-delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows})});purgeLocalQuestionsAfterDeletes(j.rows||rows);DANG_SIMILARITY_CACHE={};if(st)st.textContent='✅ '+(j.message||('Đã xóa '+(j.deleted||0)+' câu.'));renderNav();renderQuestion();refreshCatalogFromMeta();let q=QUESTIONS[CUR]||{};if(String(q.DangBaiTap||'').trim()){let rep=await loadDangSimilarityReport(q,true,false);if(rep&&rep.pair_count)renderDangSimilarityModal(rep);else closeDangSimilarityModal()}else closeDangSimilarityModal();alert(j.message||('Đã xóa '+(j.deleted||0)+' câu.'))}catch(e){if(st)st.textContent='❌ '+(e.message||e);alert('Không xóa được: '+(e.message||e))}finally{if(btn){btn.disabled=false;btn.textContent='🗑️ Xóa các câu đã chọn'}}}
async function adminAnalyzeDangSimilarity(withAi){if(!USER.is_admin)return;let q=QUESTIONS[CUR]||{};if(!String(q.DangBaiTap||'').trim()){alert('Câu chưa có Dạng bài tập (cột H).');return}let rep=await loadDangSimilarityReport(q,true,!!withAi);if(!rep){alert('Không phân tích được.');return}if(LEARNING_OPEN_KIND==='method'){let hb=document.getElementById('hintBox');if(hb&&hb.classList.contains('learningOpen')){let items=(LEARNING_CACHE[learningCacheKey('method',q)]||{}).items||[];renderLearningPanel('method',items,(LEARNING_CACHE[learningCacheKey('method',q)]||{}).meta||{})}}renderDangSimilarityModal(rep)}
function syncAdminLearningBoard(){let board=document.getElementById('adminLearningBoard');if(!board)return;let inQuiz=!!(document.getElementById('quiz')&&!document.getElementById('quiz').classList.contains('hide'));board.classList.toggle('hide',!USER.is_admin||!inQuiz);let scope=document.getElementById('adminLearningScope');if(scope){let q=QUESTIONS[CUR]||{};let dbt=String(q.DangBaiTap||'').trim();let meta=[q.Mon,q.Lop?'Lớp '+q.Lop:'',q.Chuong,q.BaiHoc].filter(x=>String(x||'').trim()).join(' · ');let trangThai=String(q.TrangThai||'').trim();let isDuyet=(()=>{let kn=trangThai.toLowerCase().replace(/\s/g,'');return kn==='đãduyệt'||kn==='dadduyet'||kn==='approved'||kn==='daduyệt'||kn==='duyet'||kn==='ok'||kn==='✓'||trangThai==='ĐÃ DUYỆT'})();let reviewBadge=trangThai?`<span style="display:inline-block;margin-top:4px;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:800;${isDuyet?'background:#dcfce7;color:#166534;border:1px solid #86efac':'background:#ffedd5;color:#9a3412;border:1px solid #fdba74'}">` +(isDuyet?'✅ Đã duyệt':'⏳ Chưa duyệt')+'</span>':'';scope.innerHTML=(dbt?`<div style="margin-bottom:5px"><span style="display:inline-block;padding:3px 10px;border-radius:7px;background:#fef3c7;color:#92400e;border:1px solid #fbbf24;font-size:12px;font-weight:900;max-width:100%;word-break:break-word">🏷️ ${esc(dbt)}</span></div>`:`<div style="margin-bottom:5px"><span style="display:inline-block;padding:3px 10px;border-radius:7px;background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;font-size:11px;font-weight:800">⚠ Chưa có Dạng BT</span></div>`)+(meta?`<div style="font-size:11px;color:var(--muted);line-height:1.4">${esc(meta)}</div>`:'') +reviewBadge}}
async function adminDetectDangBaiTapAndSave(autoOnly){if(!USER.is_admin)return;let q=QUESTIONS[CUR]||{};if(!q._row&&!autoOnly){alert('Câu chưa có dòng Sheet — không lưu được Dạng bài tập.');return}if(!confirm('GPT gán Dạng bài tập cho câu này và lưu Sheet?'))return;try{let j=await adminApiPost('/api/ai/detect-dangbaitap-update',{row:q._row,id:q.ID||'',question:q,dangbaitap_suggestions:adminDangBaiTapSuggestionsForQuestion(q)});if(j.DangBaiTap){q.DangBaiTap=j.DangBaiTap;LEARNING_CACHE={};renderQuestion();let sync=j.matched_existing?' (đồng bộ dạng có sẵn)':'';alert('Đã gán Dạng bài tập: '+j.DangBaiTap+sync+(j.reason?'\n'+j.reason:''))}}catch(e){alert('Không gán được: '+(e.message||e))}}
async function adminGenerateAndSyncLearning(kind){if(!USER.is_admin)return;kind=(kind==='method')?'method':'theory';if(kind==='theory'){alert('Lý thuyết SGK phải do ADMIN nhập tay vào sheet Ly_Thuyet; GPT chỉ tạo Phương pháp giải.');return}let q=QUESTIONS[CUR]||{};if(!confirm('GPT tạo Phương pháp giải và lưu Google Sheet?'))return;try{let j=await adminApiPost('/api/learning/generate-save',{kind:'method',question:q});LEARNING_CACHE={};if(j.DangBaiTap&&q){q.DangBaiTap=j.DangBaiTap;renderQuestion()}let extra=j.question_dangbaitap_updated?('\nĐã gán Dạng bài tập cột H: '+j.DangBaiTap):'';alert('Đã lưu học liệu'+(j.row?(' dòng '+j.row):'')+'.'+extra);if(LEARNING_OPEN_KIND==='method')loadLearningPanelContent('method',true)}catch(e){alert('Không tạo/lưu được: '+(e.message||e))}}
function translateEnStore(qIdx){qIdx=qIdx==null?CUR:qIdx;if(!TRANSLATE_BY_Q[qIdx])TRANSLATE_BY_Q[qIdx]={};return TRANSLATE_BY_Q[qIdx]}
function parseTranslateEnParts(raw,vocab,notes){let t=String(raw||'').trim();let english=t,vocabulary=String(vocab||'').trim(),notesOut=String(notes||'').trim();if(!vocabulary&&!notesOut){let m=t.match(/English:\s*\n?([\s\S]*?)(?=\n\s*Vocabulary:|\n\s*Notes:|\Z)/i);if(m)english=m[1].trim();m=t.match(/Vocabulary:\s*\n?([\s\S]*?)(?=\n\s*Notes:|\Z)/i);if(m)vocabulary=m[1].trim();m=t.match(/Notes:\s*\n?([\s\S]*)$/i);if(m)notesOut=m[1].trim()}return {english:english||t,vocabulary,notes:notesOut}}
function questionHasTranslateOpts(q){q=q||{};return['A','B','C','D'].some(L=>String(q[L]||'').trim())}
function parseTranslateEnAbcd(text){let t=String(text||'').trim();if(!t)return{stem:'',opts:{}};t=t.replace(/\(\s*([ABCD])\s*[.)]\s*\)/gi,'\n$1. ');t=t.replace(/([^\n\r])([BCD])[.)]\s+/g,function(a,b,L){return b+'\n'+L+'. '});let markers=[],re=/(?:^|\n)\s*([ABCD])[.)]\s*/gi,m;while((m=re.exec(t))!==null){let letter=m[1].toUpperCase();if(markers.some(x=>x.letter===letter))continue;markers.push({letter:letter,start:m.index,contentStart:m.index+m[0].length})}let opts={},stem='';if(!markers.length)return{stem:t,opts:{}};if(markers[0].letter!=='A'){let before=t.slice(0,markers[0].start).trim();let sm=before.match(/^([\s\S]*?)(?:\n\s*\n|(?:^|\n)\s*(?:Phương án|Options)\s*:?\s*\n)([\s\S]+)$/i);if(sm){stem=sm[1].trim();opts['A']=sm[2].trim()}else{let qm=before.match(/^([\s\S]*?\?)\s+([\s\S]+)$/);if(qm&&qm[2].trim()){stem=qm[1].trim();opts['A']=qm[2].trim()}else stem=before}}else stem=t.slice(0,markers[0].start).replace(/\n*(?:Phương án|Options)\s*:?\s*$/i,'').trim();for(let i=0;i<markers.length;i++){let end=i+1<markers.length?markers[i+1].start:t.length;opts[markers[i].letter]=t.slice(markers[i].contentStart,end).trim()}let a=opts['A']||'';if(a&&/(?:^|[\s(])([BCD])[.)]\s*/i.test(a)){let subs=[],re2=/(?:^|[\s(])([BCD])[.)]\s*/gi,mm;while((mm=re2.exec(a))!==null){subs.push({letter:mm[1].toUpperCase(),start:mm.index+(mm[0].search(/[BCD]/i)),contentStart:mm.index+mm[0].length})}if(subs.length){opts['A']=a.slice(0,subs[0].start).trim();for(let j=0;j<subs.length;j++){let e=j+1<subs.length?subs[j+1].start:a.length;opts[subs[j].letter]=a.slice(subs[j].contentStart,e).trim()}}}return{stem,opts}}
function resolveTranslateEnAbcd(text,q){let parsed=parseTranslateEnAbcd(text);q=q||{};let letters=['A','B','C','D'].filter(L=>String(q[L]||'').trim()||String(parsed.opts[L]||'').trim());return{stem:parsed.stem,opts:parsed.opts,letters}}
function translateTtsChunkHtml(inner,idx,activeIdx){if(activeIdx==null||activeIdx<0)activeIdx=TRANSLATE_SPEECH_ACTIVE?TRANSLATE_SPEECH_CHUNK_IDX:-1;let on=(idx|0)===activeIdx;return '<span class="ttsChunk'+(on?' ttsChunkActive':'')+'" data-tts-idx="'+idx+'" onclick="translateTtsChunkClick('+idx+')" title="Bấm để nghe đoạn này">'+inner+'</span>'}
function translateTtsChunkClick(idx){TRANSLATE_SPEECH_AUTO_PLAY=false;speakTranslateEnChunkAt(idx|0)}
function planTranslateEnSpeechChunkTexts(text,q,loai){loai=normTranslateKind(loai||TRANSLATE_KIND);q=q||{};text=String(text||'').trim();if(!text)return[];if(loai==='CauHoi'&&questionHasTranslateOpts(q)){let parsed=resolveTranslateEnAbcd(text,q);let letters=parsed.letters;if(letters.length){let out=[];if(parsed.stem)splitTranslateEnChunks(parsed.stem).forEach(s=>{if(s)out.push(s)});letters.forEach(L=>{let ot=parsed.opts[L]||'';let plain=translateEnSpeechPlain(ot);if(plain)out.push('Option '+L+'. '+plain);else if(String(q[L]||'').trim())out.push('Option '+L)});if(out.length)return out}}return splitTranslateEnChunks(text)}
function formatTranslateEnCauHoiHtml(text,q,activeIdx){q=applyResolvedDang(q||currentQuestion()||{});let parsed=resolveTranslateEnAbcd(text,q);let letters=parsed.letters;if(!letters.length)return buildTranslateEnChunkedHtml(text,activeIdx);if(activeIdx==null||activeIdx<0)activeIdx=TRANSLATE_SPEECH_ACTIVE?TRANSLATE_SPEECH_CHUNK_IDX:-1;let idx=0;let stemHtml='';if(parsed.stem){let parts=splitTranslateEnChunks(parsed.stem);if(!parts.length)parts=[parsed.stem];stemHtml='<div class="translateEnStem">'+parts.map(s=>{let h=translateTtsChunkHtml(formatHintDisplay(s),idx,activeIdx);idx++;return h}).join(' ')+'</div>'}let optsHtml='<div class="translateEnOpts">'+letters.map(L=>{let ot=parsed.opts[L]||'';let ci=idx++;let active=ci===activeIdx;let optCls='translateEnOpt'+(active?' ttsOptActive':'');let body=ot?translateTtsChunkHtml(formatHintDisplay(ot),ci,activeIdx):'<span class="muted">—</span>';return '<div class="'+optCls+'" data-tts-idx="'+ci+'"><span class="translateEnOptLbl">'+dsCircleHtml(L)+'</span><span class="translateEnOptTxt">'+body+'</span></div>'}).join('')+'</div>';return stemHtml+optsHtml}
function translateEnSpeechPlain(text){let t=String(text||'');try{let el=document.createElement('div');el.innerHTML=t;t=el.textContent||el.innerText||t}catch(e){}t=t.replace(/\$\$[\s\S]*?\$\$/g,' formula ').replace(/\$[^$]*\$/g,' ');t=t.replace(/<[^>]+>/g,' ').replace(/&nbsp;/gi,' ').replace(/&[a-z]+;/gi,' ');t=t.replace(/[\\{}_^]/g,' ');return t.replace(/\s+/g,' ').trim()}
function isTranslateViSpeechVoice(v){if(!v)return false;let lang=String(v.lang||'').replace(/_/g,'-').toLowerCase();let name=String(v.name||'').toLowerCase();if(/^vi(-|$)/.test(lang))return true;if(/\b(vietnam|vietnamese|tieng viet|tiếng việt)\b/.test(name))return true;if(/(hoai my|nam minh|mai linh|duc quang)/.test(name))return true;return false}
function isTranslateEnSpeechVoice(v){if(!v||isTranslateViSpeechVoice(v))return false;let lang=String(v.lang||'').replace(/_/g,'-').toLowerCase();if(/^en(-|$)/.test(lang))return true;let name=String(v.name||'').toLowerCase();return /\b(english|en-us|en-gb|en-au|zira|david|mark|samantha|google uk english|google us english)\b/.test(name)}
function pickTranslateEnVoice(){if(typeof speechSynthesis==='undefined')return null;let voices=speechSynthesis.getVoices?speechSynthesis.getVoices():[];if(!voices.length)return null;let en=voices.filter(isTranslateEnSpeechVoice);if(!en.length)return null;for(let p of ['en-US','en-GB','en-AU','en']){let v=en.find(x=>String(x.lang||'').replace(/_/g,'-').toLowerCase().indexOf(p.toLowerCase())===0);if(v)return v}return en[0]}
function ensureTranslateEnVoices(cb){if(typeof speechSynthesis==='undefined'){cb();return}let voices=speechSynthesis.getVoices?speechSynthesis.getVoices():[];if(voices.length){cb();return}let done=false;let finish=()=>{if(done)return;done=true;try{cb()}catch(e){}};if(speechSynthesis.onvoiceschanged!==undefined)speechSynthesis.onvoiceschanged=()=>{speechSynthesis.onvoiceschanged=null;finish()};setTimeout(finish,600)}
function warmTranslateEnSpeech(){ensureTranslateEnVoices(()=>{try{if(speechSynthesis.paused)speechSynthesis.resume()}catch(e){}})}
function getTranslateEnReadableText(loai){loai=normTranslateKind(loai||TRANSLATE_KIND);let st=translateEnStore(CUR);let d=st[loai]||{};return String(d.english||d.translation||'').trim()}
function buildTranslateEnChunkedHtml(text,activeIdx){let chunks=splitTranslateEnChunks(text);TRANSLATE_SPEECH_CHUNKS=chunks;if(activeIdx==null||activeIdx<0)activeIdx=TRANSLATE_SPEECH_ACTIVE?TRANSLATE_SPEECH_CHUNK_IDX:-1;if(!chunks.length)return esc(translateEnSpeechPlain(text)||'');return chunks.map((c,i)=>translateTtsChunkHtml(esc(c),i,activeIdx)).join(' ')}
function highlightTranslateEnChunk(idx){idx=(idx==null||idx<0)?-1:(idx|0);if(idx>=0)TRANSLATE_SPEECH_CHUNK_IDX=idx;let box=document.getElementById('translateEnReadText');if(!box)return;box.querySelectorAll('.ttsChunk').forEach(el=>{let i=parseInt(el.getAttribute('data-tts-idx')||'-1',10);el.classList.toggle('ttsChunkActive',idx>=0&&i===idx)});box.querySelectorAll('.translateEnOpt').forEach(el=>{let i=parseInt(el.getAttribute('data-tts-idx')||'-1',10);el.classList.toggle('ttsOptActive',idx>=0&&i===idx)});if(idx>=0){let act=box.querySelector('.ttsChunkActive')||box.querySelector('.translateEnOpt.ttsOptActive');if(act&&act.scrollIntoView)act.scrollIntoView({behavior:'smooth',block:'nearest',inline:'nearest'})}syncTranslateSpeechBtn()}
function clearTranslateEnChunkHighlight(){document.querySelectorAll('.ttsChunk').forEach(el=>el.classList.remove('ttsChunkActive'));document.querySelectorAll('.translateEnOpt').forEach(el=>el.classList.remove('ttsOptActive'))}
function splitTranslateEnChunks(text){let plain=translateEnSpeechPlain(text);if(!plain)return [];let parts=plain.split(/(?<=[.!?…])\s+/).map(s=>s.trim()).filter(Boolean);if(!parts.length)parts=[plain];if(parts.length===1&&plain.length>100){parts=[];let words=plain.split(/\s+/),buf=[];for(let w of words){buf.push(w);let line=buf.join(' ');if(line.length>=85&&/[.!?]$/.test(w)||line.length>=115){parts.push(line);buf=[]}}if(buf.length)parts.push(buf.join(' '))}return parts}
function prepareTranslateEnChunks(loai){loai=normTranslateKind(loai||TRANSLATE_KIND);let st=translateEnStore(CUR);let d=st[loai]||{};let text=String(d.english||d.translation||'').trim();let q=QUESTIONS[CUR]||{};TRANSLATE_SPEECH_CHUNKS=planTranslateEnSpeechChunkTexts(text,q,loai);if(TRANSLATE_SPEECH_CHUNK_IDX<0)TRANSLATE_SPEECH_CHUNK_IDX=0;if(TRANSLATE_SPEECH_CHUNK_IDX>=TRANSLATE_SPEECH_CHUNKS.length)TRANSLATE_SPEECH_CHUNK_IDX=0;return TRANSLATE_SPEECH_CHUNKS}
function setTranslateTtsBtnActive(btn){TRANSLATE_TTS_ACTIVE_BTN=btn||'';syncTranslateSpeechBtn()}
function stopTranslateEnSpeech(keepBtn){if(!keepBtn)TRANSLATE_SPEECH_AUTO_PLAY=false;if(typeof speechSynthesis!=='undefined'){try{speechSynthesis.cancel()}catch(e){}}TRANSLATE_SPEECH_ACTIVE=false;if(!keepBtn&&!TRANSLATE_SPEECH_REPEAT)TRANSLATE_TTS_ACTIVE_BTN='';if(!keepBtn)clearTranslateEnChunkHighlight();syncTranslateSpeechBtn()}
function syncTranslateSpeechBtn(){document.querySelectorAll('.translateEnPlayerBtn').forEach(btn=>{let id=btn.getAttribute('data-tts')||'';btn.classList.toggle('ttsBtnOn',id===TRANSLATE_TTS_ACTIVE_BTN);btn.classList.toggle('ttsBtnPlayOn',id==='play'&&!!TRANSLATE_SPEECH_ACTIVE);if(id==='play')btn.textContent=TRANSLATE_SPEECH_ACTIVE?'⏸':'▶'});let rateEl=document.getElementById('ttsRateLbl');if(rateEl)rateEl.textContent='x'+(TRANSLATE_SPEECH_RATE||0.92).toFixed(2).replace(/\.00$/,'');let chunkEl=document.getElementById('ttsChunkLbl');if(chunkEl){let n=TRANSLATE_SPEECH_CHUNKS.length||0;chunkEl.textContent=n?((TRANSLATE_SPEECH_CHUNK_IDX+1)+'/'+n):'—'}}
function speakTranslateEn(text,force){if(typeof speechSynthesis==='undefined'||typeof SpeechSynthesisUtterance==='undefined'){alert('Trình duyệt không hỗ trợ đọc tiếng Anh (Text-to-Speech).');return}let plain=translateEnSpeechPlain(text);if(!plain){alert('Không có văn bản tiếng Anh để đọc.');return}if(TRANSLATE_SPEECH_ACTIVE&&!force)return;let wasSpeaking=!!(speechSynthesis.speaking||speechSynthesis.pending);stopTranslateEnSpeech(true);let run=()=>{try{let started=false;let u=new SpeechSynthesisUtterance(plain);u.lang='en-US';u.rate=TRANSLATE_SPEECH_RATE||0.92;let v=pickTranslateEnVoice();if(v){u.voice=v;u.lang=v.lang||'en-US'}else if(force)setTimeout(()=>{if(!started&&!speechSynthesis.speaking&&!speechSynthesis.pending)alert('Không tìm thấy giọng tiếng Anh — cài thêm giọng EN (Settings → Speech) hoặc dùng Chrome/Edge.')},900);u.onstart=()=>{started=true;TRANSLATE_SPEECH_ACTIVE=true;setTranslateTtsBtnActive('play');highlightTranslateEnChunk(TRANSLATE_SPEECH_CHUNK_IDX);syncTranslateSpeechBtn()};u.onend=()=>{TRANSLATE_SPEECH_ACTIVE=false;if(TRANSLATE_SPEECH_REPEAT){setTranslateTtsBtnActive('repeat');setTimeout(()=>speakTranslateEnChunkAt(TRANSLATE_SPEECH_CHUNK_IDX),180)}else if(TRANSLATE_SPEECH_AUTO_PLAY&&TRANSLATE_SPEECH_CHUNK_IDX<TRANSLATE_SPEECH_CHUNKS.length-1){setTimeout(()=>speakTranslateEnChunkAt(TRANSLATE_SPEECH_CHUNK_IDX+1),280)}else{TRANSLATE_SPEECH_AUTO_PLAY=false;syncTranslateSpeechBtn()}};u.onerror=()=>{TRANSLATE_SPEECH_ACTIVE=false;TRANSLATE_SPEECH_AUTO_PLAY=false;if(!TRANSLATE_SPEECH_REPEAT)TRANSLATE_TTS_ACTIVE_BTN='';syncTranslateSpeechBtn();if(force)alert('Trình duyệt không đọc được. Thử Chrome/Edge hoặc bấm ▶ lại.')};speechSynthesis.speak(u);if(speechSynthesis.paused)speechSynthesis.resume();setTimeout(()=>{if(force&&!started&&!speechSynthesis.speaking&&!speechSynthesis.pending)alert('Chưa phát âm — bấm ▶ Đọc lại.')},1000)}catch(e){TRANSLATE_SPEECH_ACTIVE=false;TRANSLATE_SPEECH_AUTO_PLAY=false;TRANSLATE_TTS_ACTIVE_BTN='';syncTranslateSpeechBtn();alert('Không đọc được: '+(e.message||e))}};ensureTranslateEnVoices(()=>{setTimeout(run,wasSpeaking?150:40)})}
function speakTranslateEnChunkAt(idx){prepareTranslateEnChunks();if(!TRANSLATE_SPEECH_CHUNKS.length){alert('Không có văn bản tiếng Anh để đọc.');return}idx=Math.max(0,Math.min(TRANSLATE_SPEECH_CHUNKS.length-1,idx|0));TRANSLATE_SPEECH_CHUNK_IDX=idx;highlightTranslateEnChunk(idx);speakTranslateEn(TRANSLATE_SPEECH_CHUNKS[idx],true)}
function translateTtsPlay(){if(TRANSLATE_SPEECH_ACTIVE){translateTtsStop();return}TRANSLATE_SPEECH_AUTO_PLAY=true;setTranslateTtsBtnActive('play');speakTranslateEnChunkAt(TRANSLATE_SPEECH_CHUNK_IDX)}
function translateTtsStop(){TRANSLATE_SPEECH_AUTO_PLAY=false;setTranslateTtsBtnActive('stop');TRANSLATE_SPEECH_REPEAT=false;stopTranslateEnSpeech();setTimeout(()=>setTranslateTtsBtnActive(''),350)}
function translateTtsPrev(){TRANSLATE_SPEECH_AUTO_PLAY=false;setTranslateTtsBtnActive('prev');speakTranslateEnChunkAt(TRANSLATE_SPEECH_CHUNK_IDX-1)}
function translateTtsNext(){TRANSLATE_SPEECH_AUTO_PLAY=false;setTranslateTtsBtnActive('next');speakTranslateEnChunkAt(TRANSLATE_SPEECH_CHUNK_IDX+1)}
function translateTtsRepeat(){TRANSLATE_SPEECH_REPEAT=!TRANSLATE_SPEECH_REPEAT;setTranslateTtsBtnActive(TRANSLATE_SPEECH_REPEAT?'repeat':'');syncTranslateSpeechBtn()}
function translateTtsSlower(){setTranslateTtsBtnActive('slower');TRANSLATE_SPEECH_RATE=Math.max(0.55,Math.round(((TRANSLATE_SPEECH_RATE||0.92)-0.08)*100)/100);syncTranslateSpeechBtn();setTimeout(()=>{if(TRANSLATE_TTS_ACTIVE_BTN==='slower')setTranslateTtsBtnActive('')},450)}
function translateTtsFaster(){setTranslateTtsBtnActive('faster');TRANSLATE_SPEECH_RATE=Math.min(1.55,Math.round(((TRANSLATE_SPEECH_RATE||0.92)+0.08)*100)/100);syncTranslateSpeechBtn();setTimeout(()=>{if(TRANSLATE_TTS_ACTIVE_BTN==='faster')setTranslateTtsBtnActive('')},450)}
function buildTranslateEnPlayerBar(){let rate=(TRANSLATE_SPEECH_RATE||0.92).toFixed(2).replace(/\.00$/,'');let n=TRANSLATE_SPEECH_CHUNKS.length||0;let chunkLbl=n?((TRANSLATE_SPEECH_CHUNK_IDX+1)+'/'+n):'—';return '<div class="translateEnPlayer"><div class="translateEnPlayerCore"><button type="button" class="translateEnPlayerBtn" data-tts="prev" onclick="translateTtsPrev()" title="Đoạn trước">⏮</button><button type="button" class="translateEnPlayerBtn" data-tts="slower" onclick="translateTtsSlower()" title="Chậm hơn">−</button><button type="button" class="translateEnPlayerBtn translateEnPlayerBtnMain" data-tts="play" id="btnTranslateRead" onclick="translateTtsPlay()" title="Đọc / tạm dừng">'+(TRANSLATE_SPEECH_ACTIVE?'⏸':'▶')+'</button><button type="button" class="translateEnPlayerBtn" data-tts="faster" onclick="translateTtsFaster()" title="Nhanh hơn">+</button><button type="button" class="translateEnPlayerBtn" data-tts="next" onclick="translateTtsNext()" title="Đoạn sau">⏭</button></div><div class="translateEnPlayerExtras"><button type="button" class="translateEnPlayerBtn" data-tts="stop" onclick="translateTtsStop()" title="Dừng hẳn">⏹</button><button type="button" class="translateEnPlayerBtn'+(TRANSLATE_SPEECH_REPEAT?' ttsBtnOn':'')+'" data-tts="repeat" onclick="translateTtsRepeat()" title="Lặp đoạn đang đọc">🔁</button><span class="translateEnPlayerMeta" id="ttsRateLbl">x'+rate+'</span><span class="translateEnPlayerMeta" id="ttsChunkLbl">'+chunkLbl+'</span></div></div>'}
function normTranslateKind(loai){loai=String(loai||'').trim();if(loai==='DapAn'||loai==='LoiGiai')return loai;return 'CauHoi'}
function canTranslateDapAn(qIdx){qIdx=(qIdx==null||qIdx===undefined)?CUR:qIdx;if(!canShowSolutionNow())return false;let q=QUESTIONS[qIdx]||{};return !!String(q.DapAn||'').trim()}
function canTranslateLoiGiai(qIdx){qIdx=(qIdx==null||qIdx===undefined)?CUR:qIdx;if(!canShowSolutionNow())return false;let q=QUESTIONS[qIdx]||{};return !!String(q.LoiGiai||'').trim()}
function scheduleTranslateEnExtras(){}
function queueTranslateEnKind(loai,silent){}
async function pumpTranslateEnQueue(){TRANSLATE_AUTO_QUEUE=[]}
function buildTranslateEnAnswerInline(qIdx,st){return ''}
function setTranslateKind(loai){openTranslateAiMode(normTranslateKind(loai))}
function renderTranslatePanel(){}
async function requestTranslateEn(loai){openTranslateAiMode(normTranslateKind(loai||'CauHoi'))}
async function requestSimilarQuestion(){if(!USER.can_quiz_similar){alert('Tạo câu tương tự chỉ dành tài khoản VIP / SVIP / ADMIN.');return}if(EXAM_MODE&&!SUBMITTED){alert('Chế độ kiểm tra: nộp bài xong mới tạo câu tương tự.');return}if(SIMILAR_LOADING||HINT_LOADING)return;LEARNING_OPEN_KIND='';saveCurrent();let qIdx=CUR;setSimilarLoading(true,qIdx);if(HINT_BY_Q[qIdx])renderHintBox(HINT_BY_Q[qIdx]);else{let hb=document.getElementById('hintBox');if(hb){hb.classList.remove('hide');hb.innerHTML='<b>📝 Tạo câu tương tự</b><div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang gọi AI…</b></div></div>'}}try{let j=await api('/api/hint/similar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,index:qIdx,...quizRestorePayload()})});SIMILAR_BY_Q[qIdx]=j;if(CUR===qIdx)renderHintBox(HINT_BY_Q[qIdx]||{});let hb=document.getElementById('hintBox');if(hb&&!hb.classList.contains('hide'))hb.scrollIntoView({behavior:'smooth',block:'nearest'})}catch(e){alert('Không tạo được câu tương tự: '+e.message)}finally{if(SIMILAR_LOADING_Q===qIdx){setSimilarLoading(false);if(CUR===qIdx&&(HINT_BY_Q[qIdx]||SIMILAR_BY_Q[qIdx]))renderHintBox(HINT_BY_Q[qIdx]||{})}}}
async function requestHint(){if(USER.can_quiz_ai_hint===false&&!isAdminViewer())return;if(!USER.can_quiz_ai_hint&&!isAdminViewer()){alert('Gợi ý AI đã tắt.');return}if(!USER.can_ai_hint){alert('Gợi ý AI chỉ dành tài khoản VIP / SVIP / ADMIN.');return}if(HINT_LOADING||SIMILAR_LOADING){return}LEARNING_OPEN_KIND='';saveCurrent();let qIdx=CUR;delete HINT_BY_Q[qIdx];setHintLoading(true,qIdx);beginHintLoadingTimer();showHintLoadingBox();let rb=document.getElementById('resultBox');if(rb)rb.style.color='#1d4ed8';let hintTimer=null;let hintDone=false;try{let ans=ANSWERS[qIdx];let hintBody={sid:SID,index:qIdx,answer:ans,...quizRestorePayload()};if(isAdminViewer())hintBody.admin_review_mode=getAdminReviewMode();HINT_ABORT_CTRL=new AbortController();let tms=hintClientTimeoutMs();hintTimer=setTimeout(()=>{abortHintFetch()},tms);let j=isAdminViewer()?await adminAiFetch('/api/hint',hintBody,{signal:HINT_ABORT_CTRL.signal}):await api('/api/hint',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(hintBody),signal:HINT_ABORT_CTRL.signal});HINT_BY_Q[qIdx]=j;if(j.admin_review)ADMIN_HINT_SAVED[qIdx]=false;hintDone=true;if(hintTimer){clearTimeout(hintTimer);hintTimer=null}finishHintRequest(qIdx,j)}catch(e){let msg=(e&&e.name==='AbortError')?'Quá thời gian chờ. Render Free giới hạn ~30 giây/request — chọn ⚡ Soát nhanh hoặc thử lại.':String(e.message||e);if(CUR===qIdx){let hb=document.getElementById('hintBox');if(hb){hb.classList.remove('hintBoxLoading');hb.classList.remove('hide');hb.innerHTML='<b>❌ Không lấy được gợi ý AI</b><div class="muted" style="margin-top:8px">'+esc(msg)+'</div><div style="margin-top:8px"><button type="button" class="btn2" onclick="requestHint()">Thử lại</button></div>'}}alert('Không lấy được gợi ý: '+msg)}finally{if(!hintDone){if(hintTimer)clearTimeout(hintTimer);stopHintLoadingTimer();HINT_LOADING_SINCE=0;if(HINT_LOADING_Q===qIdx)setHintLoading(false);syncHintButtons(USER.can_ai_hint!==false);if(CUR===qIdx&&rb){if(USER.is_admin)rb.textContent='ADMIN: đang xem đáp án/lời giải';else if(USER.is_trial)rb.textContent='DÙNG THỬ: chỉ luyện đề FREE, không chấm điểm';else rb.textContent=''}}}}
async function submitQuiz(){if(USER.is_trial){alert('Tài khoản dùng thử không được nộp/chấm điểm.');return;}saveCurrent();if(!confirm(EXAM_MODE?'Nộp bài kiểm tra? Sau khi nộp mới xem đáp án/lời giải.':'Nộp bài?'))return;let j=await api('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:SID,answers:ANSWERS,elapsed_sec:QUIZ_ELAPSED||0,...quizRestorePayload()})});SUBMITTED=true;stopQuizTimer();RESULTS={};for(let r of j.results)RESULTS[r.index]=r;if(EXAM_MODE){USER.can_view_solution_live=true;for(let i=0;i<QUESTIONS.length;i++){let rr=RESULTS[i];if(rr){if(rr.DapAn!=null&&QUESTIONS[i])QUESTIONS[i].DapAn=rr.DapAn;if(rr.LoiGiai!=null&&QUESTIONS[i])QUESTIONS[i].LoiGiai=rr.LoiGiai}}}let avgOk=j.avg_per_correct_text||(j.avg_sec_per_correct?fmtTime(j.avg_sec_per_correct):'');let avgBit=avgOk?(` | TB/câu đúng ${avgOk}`):'';if(j.time_stats&&j.time_stats.avg_per_correct_text&&j.time_stats.correct_sample_count)avgBit+=` | TB chung ${j.time_stats.avg_per_correct_text}`;document.getElementById('resultBox').textContent=`Điểm: ${j.score}/10 | Đúng ${j.correct_count}/${j.auto_count} | ⏱ ${fmtTime(QUIZ_ELAPSED)}${avgBit}`;syncExamSubmitButton();syncMobileQuizChrome();renderQuestion();renderNav();try{recordPracticeProgressFromSubmit(j)}catch(e){}if(EXAM_MODE){try{showExamFinishToast(j)}catch(e){console.warn('exam toast',e)}}}
const QUESTION_FORM_FIELDS=['MaDe','ID','Mon','Lop','Chuong','BaiHoc','DangBaiTap','NangLucVatLy','QuyenTruyCap','TrangThai','MucDo','Dang','CauHoi','A','B','C','D','DapAn','SaiSo','LoiGiai','HinhAnh'];
const QUESTION_EDIT_SAVE_FIELDS=['Mon','Lop','Chuong','BaiHoc','DangBaiTap','NangLucVatLy','CauHoi','A','B','C','D','DapAn','SaiSo','MucDo','Dang','QuyenTruyCap','TrangThai','LoiGiai','HinhAnh'];
const QUESTION_FORM_LABELS={MaDe:'Mã đề (MaDe)',ID:'ID câu (để trống = tự tạo)',Mon:'Môn',Lop:'Lớp',Chuong:'Chương',BaiHoc:'Bài học',DangBaiTap:'Dạng bài tập - cột H',NangLucVatLy:'Năng lực vật lí - cột V',QuyenTruyCap:'Quyền (FREE/VIP)',TrangThai:'Trạng thái duyệt - cột TrangThai',MucDo:'Mức độ - cột I',Dang:'Dạng - cột J',CauHoi:'Câu hỏi / Nội dung - cột K',DapAn:'Đáp án - cột P',SaiSo:'Sai số - cột Q',LoiGiai:'Lời giải - cột R',HinhAnh:'Hình ảnh - cột T',A:'A - cột L',B:'B - cột M',C:'C - cột N',D:'D - cột O'};
const ADMIN_REVIEW_OPTS=[{v:'CHƯA DUYỆT',l:'⚠ Chưa duyệt',cls:'reviewChipPending'},{v:'ĐÃ DUYỆT',l:'✓ Đã duyệt',cls:'reviewChipOk'}];
function normReviewFormVal(s){return questionIsReviewedForAdmin({TrangThai:s})?'ĐÃ DUYỆT':'CHƯA DUYỆT'}
const ADMIN_MUCDO_OPTS=['NB','TH','VD','VDC'];
const ADMIN_DANG_OPTS=['Trắc nghiệm','Đúng sai','Trả lời ngắn','Tự luận'];
const ADMIN_NLVL_OPTS=[{v:'NLVL01',l:'NLVL01'},{v:'NLVL02',l:'NLVL02'},{v:'NLVL03',l:'NLVL03'},{v:'NLVL04',l:'NLVL04'},{v:'NLVL05',l:'NLVL05'},{v:'NLVL06',l:'NLVL06'}];
const ADMIN_QUYEN_OPTS=[{v:'FREE',l:'FREE',cls:'adminChipFree'},{v:'VIP',l:'VIP',cls:'adminChipVip'}];
function normQuyenFormVal(s){let t=normText(s);if(!t)return'FREE';if(/vip|paid|premium|co phi|tra phi|thu phi|svip/.test(t))return'VIP';return'FREE'}
function normNangLucVatLyFormVal(s){let m=String(s||'').toUpperCase().replace(/\s+/g,'').match(/NLVL0?([1-6])/);return m?('NLVL0'+m[1]):''}
function normMucDoFormVal(s){let u=String(s||'').trim().toUpperCase();if(ADMIN_MUCDO_OPTS.includes(u))return u;if(/\bNB\b/.test(u))return'NB';if(/\bTH\b/.test(u))return'TH';if(/\bVDC\b/.test(u))return'VDC';if(/\bVD\b/.test(u))return'VD';return''}
function normDangFormVal(s){let d=normDangClient(s);if(ADMIN_DANG_OPTS.includes(d))return d;return d||'Trắc nghiệm'}
function escFormVal(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}
const ADMIN_META_PICK_FIELDS=['Mon','Lop','Chuong','BaiHoc'];
function hasLessonCatalog(){return !!((META&&META.lesson_catalog)||[]).length}
function adminMetaCatalogRows(field,q){q=q||{};let rows=(META.lesson_catalog||[]).slice();if(field!=='Mon'&&q.Mon)rows=rows.filter(x=>normText(x.Mon||'')===normText(q.Mon));if(!['Mon','Lop'].includes(field)&&q.Lop)rows=rows.filter(x=>normText(x.Lop||'')===normText(q.Lop));if(!['Mon','Lop','Chuong'].includes(field)&&q.Chuong)rows=rows.filter(x=>normText(x.Chuong||'')===normText(q.Chuong));return rows}
function adminMetaFilteredRows(field,q){if(hasLessonCatalog())return adminMetaCatalogRows(field,q);q=q||{};let rows=[];for(let c of (CATALOG||[]))rows.push(c);for(let qq of (QUESTIONS||[]))rows.push(qq);for(let lc of ((META&&META.lesson_catalog)||[]))rows.push(lc);return rows.filter(it=>{if(field!=='Mon'&&q.Mon&&normText(it.Mon||'')!==normText(q.Mon))return false;if(!['Mon','Lop'].includes(field)&&q.Lop&&normText(it.Lop||'')!==normText(q.Lop))return false;if(!['Mon','Lop','Chuong'].includes(field)&&q.Chuong&&normText(it.Chuong||'')!==normText(q.Chuong))return false;return true})}
function adminMetaPickOptions(field,q){let opts=uniqField(adminMetaFilteredRows(field,q||{}),field);let cur=String((q&&q[field])||'').trim();if(cur&&!opts.some(x=>normText(x)===normText(cur)))opts.unshift(cur);if(field==='Mon'){if(!hasLessonCatalog()){for(let v of ((META&&META.filters&&META.filters.Mon)||[])){v=String(v||'').trim();if(v&&!opts.some(x=>normText(x)===normText(v)))opts.push(v)}}opts.sort((a,b)=>normText(a).localeCompare(normText(b),'vi'))}else{if(field==='BaiHoc')opts.sort((a,b)=>lessonNum(a)-lessonNum(b)||normText(a).localeCompare(normText(b),'vi'));else if(field==='Chuong')opts.sort((a,b)=>chapterNum(a)-chapterNum(b)||normText(a).localeCompare(normText(b),'vi'));else opts.sort((a,b)=>normText(a).localeCompare(normText(b),'vi'))}return opts}
function adminMetaRebuildPick(raw,opts){let match=adminDbtFindMatch(raw,opts);let pickVal=match||(raw&&!hasLessonCatalog()?'__custom__':'');let optHtml='<option value="">— Chọn —</option>';for(let v of opts){optHtml+=`<option value="${escAttr(v)}"${pickVal===v?' selected':''}>${esc(v)}</option>`}if(!hasLessonCatalog())optHtml+=`<option value="__custom__"${pickVal==='__custom__'?' selected':''}>✏️ Nhập khác…</option>`;return{optHtml,match,pickVal}}
function adminMetaRefreshCascade(changedField){let order=ADMIN_META_PICK_FIELDS;let idx=order.indexOf(changedField);if(idx<0)return;let form=readQuestionFormData();for(let i=idx+1;i<order.length;i++){let f=order[i];let sel=document.getElementById('edit_'+f+'_pick');let inp=document.getElementById('edit_'+f);if(!sel||!inp)continue;let cur=String(inp.value||'').trim();let opts=adminMetaPickOptions(f,form);let built=adminMetaRebuildPick(cur,opts);sel.innerHTML=built.optHtml;if(hasLessonCatalog()){sel.value=built.match||'';inp.value=built.match||''}else if(built.match){sel.value=built.match;inp.value=built.match;inp.classList.add('hide')}else if(cur){sel.value='__custom__';inp.classList.remove('hide')}else{sel.value='';inp.classList.remove('hide')}}adminDbtRefreshFromScope()}
function adminMetaPickChange(field){let sel=document.getElementById('edit_'+field+'_pick');let inp=document.getElementById('edit_'+field);if(!sel||!inp)return;let v=String(sel.value||'');if(hasLessonCatalog()){inp.value=v;adminMetaRefreshCascade(field);return}if(v==='__custom__'){inp.classList.remove('hide');inp.focus()}else{inp.value=v;if(v)inp.classList.add('hide');else inp.classList.remove('hide')}adminMetaRefreshCascade(field)}
function adminMetaInputChange(field){let inp=document.getElementById('edit_'+field);let sel=document.getElementById('edit_'+field+'_pick');if(!inp||!sel)return;let opts=[];for(let i=0;i<sel.options.length;i++){let v=sel.options[i].value;if(v&&v!=='__custom__')opts.push(v)}let m=adminDbtFindMatch(inp.value,opts);if(m&&normText(inp.value)===normText(m)){sel.value=m;inp.classList.add('hide')}else if(String(inp.value||'').trim()){sel.value='__custom__';inp.classList.remove('hide')}else{sel.value='';inp.classList.remove('hide')}adminMetaRefreshCascade(field)}
function adminMetaSyncAll(){adminMetaRefreshCascade('Mon')}
function renderAdminMetaPickField(field,q){let raw=String((q&&q[field])||'').trim();let opts=adminMetaPickOptions(field,q);let built=adminMetaRebuildPick(raw,opts);let catalogOnly=hasLessonCatalog();let hideInp=catalogOnly||(built.pickVal&&built.pickVal!=='__custom__');let hideCls=hideInp?' hide':'';let inpHtml=catalogOnly?'':`<input type="text" id="edit_${field}" class="adminDbtInput${hideCls}" value="${escAttr(raw)}" placeholder="Hoặc gõ ${esc(QUESTION_FORM_LABELS[field]||field)} mới" oninput="adminMetaInputChange('${field}')" />`;if(catalogOnly)inpHtml+=`<input type="hidden" id="edit_${field}" value="${escAttr(built.match||raw||'')}" />`;return `<div class="adminQuickField adminMetaPickField"><label><b>${QUESTION_FORM_LABELS[field]||field}</b>${catalogOnly?` <span class="muted" style="font-size:11px">(danh mục)</span>`:''}</label><select id="edit_${field}_pick" class="adminDbtSelect" onchange="adminMetaPickChange('${field}')">${built.optHtml}</select>${inpHtml}</div>`}

function questionPreviewShort(q){let t=String((q&&q.CauHoi)||'').replace(/\s+/g,' ').trim();return t.length>150?t.slice(0,147)+'…':t}

let ADMIN_DBT_REVIEW_ITEMS=[];
let BULK_DBT_BUSY=false;
let ADMIN_LEVEL_REVIEW_ITEMS=[];
let BULK_LEVEL_BUSY=false;
let BULK_DBT_DUP_FILTER='all';
let BULK_DBT_HIDE_SAVED=false;
let BULK_DBT_DUP_READY=false;
const DBT_MAX_PER_LESSON=6;
function bulkDbtApplyDupMarks(marks){
  marks=marks||{};
  let rowToIdx={};
  ADMIN_DBT_REVIEW_ITEMS.forEach((it,pos)=>{let r=parseInt(it.row,10)||0;if(r>1)rowToIdx[r]=pos});
  ADMIN_DBT_REVIEW_ITEMS.forEach(it=>{it.dup_type='';it.dup_keep=true;it.dup_mates=[];it.dup_delete=false});
  for(let [rs,m] of Object.entries(marks)){
    let r=parseInt(rs,10)||0,pos=rowToIdx[r];
    if(pos==null||!ADMIN_DBT_REVIEW_ITEMS[pos])continue;
    let it=ADMIN_DBT_REVIEW_ITEMS[pos];
    it.dup_type=String(m.dup_type||'content');
    it.dup_keep=!!m.dup_keep;
    it.dup_mates=(m.dup_rows||[]).filter(x=>x!==r).map(x=>{let p=rowToIdx[x];return p!=null?(ADMIN_DBT_REVIEW_ITEMS[p].index+1):x});
  }
}
function ensureBulkDbtDupBar(){
  let rerun=document.getElementById('bulkDbtRerunBtn');if(!rerun||!rerun.parentNode)return;
  if(!document.getElementById('bulkDbtDupScanBtn')){
    let wrap=document.createElement('span');wrap.id='bulkDbtDupBar';wrap.style.cssText='display:inline-flex;gap:6px;flex-wrap:wrap;align-items:center;margin-left:4px';
    function mkBtn(id,txt,fn,style){let b=document.createElement('button');b.type='button';b.className='btn2';b.id=id;b.textContent=txt;if(style)b.style.cssText=style;b.onclick=fn;return b}
    wrap.appendChild(mkBtn('bulkDbtDupScanBtn','🔍 Quét trùng',()=>bulkDbtRunDupScan()));
    wrap.appendChild(mkBtn('bulkDbtDupFilterBtn','Chỉ trùng',()=>bulkDbtSetDupFilter('dup')));
    wrap.appendChild(mkBtn('bulkDbtDupAllBtn','📋 Tất cả',()=>bulkDbtSetDupFilter('all')));
    wrap.appendChild(mkBtn('bulkDbtDupTickBtn','✓ Tick bản trùng',()=>bulkDbtTickDupCopies()));
    wrap.appendChild(mkBtn('bulkDbtDupDelBtn','🗑️ Xóa trùng đã tick',()=>bulkDbtDeleteDupTicked(),'border-color:#fca5a5;color:#991b1b'));
    let mergeBtn=rerun.nextElementSibling;
    if(mergeBtn)mergeBtn.parentNode.insertBefore(wrap,mergeBtn.nextSibling);else rerun.parentNode.appendChild(wrap);
  }
  if(!document.getElementById('bulkDbtDupStatus')){
    let st=document.getElementById('bulkDbtStatus'),el=document.createElement('div');el.id='bulkDbtDupStatus';el.className='hide';
    el.style.cssText='font-size:12px;margin:6px 0;padding:6px 10px;border-radius:8px;background:#fff7ed;border:1px solid #fdba74;color:#9a3412;font-weight:700';
    if(st&&st.parentNode)st.parentNode.insertBefore(el,st.nextSibling);else{let list=document.getElementById('bulkDbtList');if(list&&list.parentNode)list.parentNode.insertBefore(el,list)}
  }
}
async function bulkDbtRunDupScan(){
  if(BULK_DBT_BUSY){alert('Đợi GPT gợi ý xong rồi mới quét trùng.');return}
  if(!ADMIN_DBT_REVIEW_ITEMS.length)return;
  let rows=ADMIN_DBT_REVIEW_ITEMS.map(it=>parseInt(it.row,10)).filter(r=>r>1);
  if(!rows.length){alert('Chưa có dòng Sheet — bấm 🔄 Đồng bộ Sheet trước.');return}
  let el=document.getElementById('bulkDbtDupStatus'),btn=document.getElementById('bulkDbtDupScanBtn');
  if(el){el.classList.remove('hide');el.textContent='⏳ Đang quét trùng…'}
  if(btn)btn.disabled=true;
  try{
    let j=await api('/api/admin/dbt-review-dup-scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows})});
    BULK_DBT_DUP_READY=true;
    bulkDbtApplyDupMarks(j.marks||{});
    if(el)el.textContent=(j.copy_count?('🔁 '+j.copy_count+' bản trùng · '+j.group_count+' nhóm — tick «Xóa trùng» rồi 🗑️'):'✅ Không có trùng trong '+rows.length+' câu đang xem.');
    renderBulkDbtList();
  }catch(e){
    BULK_DBT_DUP_READY=false;
    if(el)el.textContent='❌ '+(e.message||e);
    alert('Quét trùng lỗi: '+(e.message||e));
  }finally{if(btn)btn.disabled=false}
}
function bulkDbtSetDupFilter(mode){
  BULK_DBT_DUP_FILTER=(mode==='dup'||mode==='all')?mode:'all';
  if(mode==='dup'&&!BULK_DBT_DUP_READY){alert('Bấm «🔍 Quét trùng» trước khi lọc.');BULK_DBT_DUP_FILTER='all'}
  let f=document.getElementById('bulkDbtDupFilterBtn'),a=document.getElementById('bulkDbtDupAllBtn');
  if(f)f.style.fontWeight=BULK_DBT_DUP_FILTER==='dup'?'800':'';
  if(a)a.style.fontWeight=BULK_DBT_DUP_FILTER==='all'?'800':'';
  renderBulkDbtList();
}
function bulkDbtToggleDupDelete(pos,on){if(!ADMIN_DBT_REVIEW_ITEMS[pos])return;ADMIN_DBT_REVIEW_ITEMS[pos].dup_delete=!!on}
async function bulkDbtTickDupCopies(){
  if(BULK_DBT_BUSY){alert('Đợi GPT xong rồi thử lại.');return}
  if(!BULK_DBT_DUP_READY)await bulkDbtRunDupScan();
  if(!BULK_DBT_DUP_READY)return;
  let n=0;
  for(let it of ADMIN_DBT_REVIEW_ITEMS){if(it.dup_type&&!it.dup_keep){it.dup_delete=true;n++}}
  if(!n){alert('Không có bản trùng cần xóa.');return}
  BULK_DBT_DUP_FILTER='dup';
  let f=document.getElementById('bulkDbtDupFilterBtn');if(f)f.style.fontWeight='800';
  renderBulkDbtList();
}
let DBT_LESSON_CANONICAL={};
function bulkDbtListEntries(){return ADMIN_DBT_REVIEW_ITEMS.map((it,pos)=>({it,pos})).filter(({it})=>(BULK_DBT_DUP_FILTER!=='dup'||!!it.dup_type)&&(!BULK_DBT_HIDE_SAVED||(!it.saved&&!it.locked)))}
function bulkDbtGuideStorageKey(){
  let scopes={};
  for(let q of (QUESTIONS||[]))scopes[bulkDbtScopeKey(q||{})]=1;
  let top=Object.keys(scopes).sort();
  return 'bulkDbtAdminGuide_v1|'+(top[0]||'all');
}
function bulkDbtParseAdminTypes(text){
  text=String(text||'').trim();
  if(!text)return [];
  let out=[],seen={};
  for(let chunk of text.replace(/;/g,'\n').replace(/\|/g,'\n').split('\n')){
    let line=String(chunk||'').trim();
    if(!line)continue;
    line=line.replace(/^[\-\*•\d]+[\.\)\:]\s*/,'').trim();
    if(!line)continue;
    if(line.indexOf(':')>=0){
      let head=line.split(':')[0].trim();
      if(head&&head.length>=3&&head.length<80)line=head;
    }
    if(adminDbtIsBadValue(line))continue;
    let k=normText(line);
    if(!k||seen[k])continue;
    seen[k]=1;
    out.push(line);
    if(out.length>=DBT_MAX_PER_LESSON)break;
  }
  return out;
}
function bulkDbtAdminTypesByScope(){
  let guideEl=document.getElementById('bulkDbtAdminGuide');
  let text=guideEl?String(guideEl.value||''):'';
  let types=bulkDbtParseAdminTypes(text);
  let scopes={};
  for(let q of (QUESTIONS||[]))scopes[bulkDbtScopeKey(q)]=1;
  let byScope={};
  if(types.length){
    for(let sk of Object.keys(scopes))byScope[sk]=types.slice();
    if(!Object.keys(scopes).length)byScope._all_=types.slice();
  }
  return {guide:text,byScope};
}
function bulkDbtAdminTypesForItem(it){
  let pack=bulkDbtAdminTypesByScope();
  let sk=bulkDbtScopeKey(it||{});
  return (pack.byScope[sk]||pack.byScope._all_||[]).slice(0,DBT_MAX_PER_LESSON);
}
function bulkDbtLoadAdminGuide(){
  let el=document.getElementById('bulkDbtAdminGuide');
  let hint=document.getElementById('bulkDbtGuideHint');
  if(!el)return;
  try{
    let saved=localStorage.getItem(bulkDbtGuideStorageKey())||'';
    if(saved&&!String(el.value||'').trim())el.value=saved;
    if(hint&&saved)hint.textContent='Đã lưu ('+bulkDbtParseAdminTypes(el.value).length+' dạng). Bấm «Chạy AI gợi ý» để AI phân bổ theo tóm tắt.';
  }catch(e){}
}
function bulkDbtSaveAdminGuide(){
  let el=document.getElementById('bulkDbtAdminGuide');
  let hint=document.getElementById('bulkDbtGuideHint');
  if(!el)return;
  try{
    localStorage.setItem(bulkDbtGuideStorageKey(),String(el.value||''));
    let n=bulkDbtParseAdminTypes(el.value).length;
    if(hint)hint.textContent='✅ Đã lưu ('+n+' dạng). Bấm «Chạy AI gợi ý» để AI phân bổ theo tóm tắt.';
  }catch(e){if(hint)hint.textContent='Không lưu được tóm tắt.'}
}
function bulkDbtLoadCatalogGuide(){
  let el=document.getElementById('bulkDbtAdminGuide');
  let hint=document.getElementById('bulkDbtGuideHint');
  if(!el)return;
  let scopes={};
  for(let q of (QUESTIONS||[]))scopes[bulkDbtScopeKey(q)]=(scopes[bulkDbtScopeKey(q)]||0)+1;
  let top=Object.entries(scopes).sort((a,b)=>b[1]-a[1])[0];
  let lines=[],seen={};
  function add(v){v=String(v||'').trim();if(!v||adminDbtIsBadValue(v))return;let k=normText(v);if(seen[k])return;seen[k]=1;lines.push(v)}
  if(top){
    for(let q of (QUESTIONS||[])){
      if(bulkDbtScopeKey(q)!==top[0])continue;
      for(let s of adminDangBaiTapSuggestionsForQuestion(q))add(s);
    }
    for(let c of (CATALOG||[])){
      let fc=((c.FilterCounts||{}).dangbaitap)||{};
      if(typeof fc==='object')for(let k of Object.keys(fc))add(k);
    }
  }
  el.value=lines.slice(0,DBT_MAX_PER_LESSON).join('\n');
  if(hint)hint.textContent='📋 Đã lấy '+lines.length+' dạng — bấm Lưu hoặc Chạy AI gợi ý.';
}
function bulkDbtScopeKey(it){return [normText(it.Mon||''),normText(it.Chuong||''),normText(it.BaiHoc||'')].join('|')}
function bulkDbtSimilarity(a,b){
  a=normText(a);b=normText(b);
  if(!a||!b)return 0;
  if(a===b||a.indexOf(b)>=0||b.indexOf(a)>=0)return 0.9;
  let ta=a.split(/\s+/),tb=b.split(/\s+/),ov=0;
  for(let w of ta)if(tb.includes(w))ov++;
  return ov/Math.min(ta.length,tb.length)||0;
}
function bulkDbtNearestCanonical(name,canonicals){
  canonicals=(canonicals||[]).filter(Boolean);
  if(!canonicals.length)return String(name||'').trim();
  let best=canonicals[0],bestSc=-1;
  for(let c of canonicals){
    let sc=bulkDbtSimilarity(name,c);
    if(sc>bestSc){bestSc=sc;best=c}
  }
  return bestSc>=0.35?best:canonicals[0];
}
function bulkDbtConsolidateItems(items){
  items=(items||[]).slice();
  let merged=0;
  let byLesson={};
  items.forEach(it=>{(byLesson[bulkDbtScopeKey(it)]=byLesson[bulkDbtScopeKey(it)]||[]).push(it)});
  for(let sk of Object.keys(byLesson)){
    let group=byLesson[sk];
    let buckets={};
    group.forEach(it=>{
      let v=String(it.ai_dbt||'').trim();
      if(!v||adminDbtIsBadValue(v))return;
      let k=normText(v);
      if(!buckets[k])buckets[k]={display:v,count:0};
      buckets[k].count++;
    });
    let keys=Object.keys(buckets);
    if(keys.length<=DBT_MAX_PER_LESSON)continue;
    let remap={};
    keys.forEach(k=>{remap[k]=buckets[k].display});
    function distNames(){
      let seen={},out=[];
      for(let k of Object.keys(remap)){
        let dn=normText(remap[k]);
        if(!seen[dn]){seen[dn]=1;out.push(remap[k])}
      }
      return out;
    }
    while(distNames().length>DBT_MAX_PER_LESSON){
      let agg={};
      for(let k of Object.keys(remap))agg[normText(remap[k])]=(agg[normText(remap[k])]||0)+1;
      let ranked=Object.entries(agg).sort((a,b)=>(a[1]-b[1])||(a[0].length-b[0].length));
      let victimN=ranked[0][0];
      let victimDisplay=remap[Object.keys(remap).find(k=>normText(remap[k])===victimN)];
      let others=[];
      let seenO={};
      for(let k of Object.keys(remap)){
        if(normText(remap[k])===victimN)continue;
        let ko=normText(remap[k]);
        if(!seenO[ko]){seenO[ko]=1;others.push(remap[k])}
      }
      let target=bulkDbtNearestCanonical(victimDisplay,others);
      for(let k of Object.keys(remap)){
        if(normText(remap[k])===victimN)remap[k]=target;
      }
    }
    group.forEach(it=>{
      let v=String(it.ai_dbt||'').trim();
      let kn=normText(v);
      if(!kn||!remap[kn])return;
      let nv=remap[kn];
      if(normText(nv)===kn)return;
      if(it.matched_existing===false)return;
      it.ai_dbt=nv;
      it.reason=String(it.reason||'')+(' (gộp về «'+nv+'» — tối đa '+DBT_MAX_PER_LESSON+' dạng/bài)').trim().slice(0,180);
      it.matched_existing=true;
      merged++;
    });
  }
  return {items,merged};
}
function bulkDbtRebuildLessonCanonical(items){
  DBT_LESSON_CANONICAL={};
  (items||[]).forEach(it=>{
    let sk=bulkDbtScopeKey(it);
    let v=String(it.ai_dbt||it.current_dbt||'').trim();
    if(!v||adminDbtIsBadValue(v))return;
    let bucket=DBT_LESSON_CANONICAL[sk]||{};
    let k=normText(v);
    if(!bucket[k])bucket[k]={display:v,count:0};
    bucket[k].count++;
    DBT_LESSON_CANONICAL[sk]=bucket;
  });
  let out={};
  for(let sk of Object.keys(DBT_LESSON_CANONICAL)){
    let ordered=Object.keys(DBT_LESSON_CANONICAL[sk]).sort((a,b)=>DBT_LESSON_CANONICAL[sk][b].count-DBT_LESSON_CANONICAL[sk][a].count||(DBT_LESSON_CANONICAL[sk][a].display.localeCompare(DBT_LESSON_CANONICAL[sk][b].display)));
    out[sk]=ordered.slice(0,DBT_MAX_PER_LESSON).map(k=>DBT_LESSON_CANONICAL[sk][k].display);
  }
  DBT_LESSON_CANONICAL=out;
}
function bulkDbtLessonCanonicalForItem(it){
  let sk=bulkDbtScopeKey(it);
  return (DBT_LESSON_CANONICAL[sk]||[]).slice();
}
function bulkDbtMergeLessonContext(ctx,items){
  ctx=Object.assign({},ctx||{});
  (items||[]).forEach(it=>{
    let sk=bulkDbtScopeKey(it);
    let v=String(it.ai_dbt||'').trim();
    if(!v)return;
    let lst=ctx[sk]||[];
    if(!lst.some(x=>normText(x)===normText(v)))lst.push(v);
    ctx[sk]=lst.slice(0,DBT_MAX_PER_LESSON);
  });
  return ctx;
}
function bulkDbtChosen(it){return String((it&&it.ai_dbt)||'').trim()}
function bulkDbtHasChange(it){
  let cur=String((it&&it.current_dbt)||'').trim();
  let ai=bulkDbtChosen(it);
  if(!ai)return false;
  if(!cur)return true;
  return normText(cur)!==normText(ai);
}
function bulkDbtAcceptLabel(it){return (bulkDbtHasChange(it)||String(it.prev_ai_dbt||'').trim())?'Chấp nhận đổi':'Chấp nhận'}
function bulkDbtSyncRowFromDom(pos){
  let it=ADMIN_DBT_REVIEW_ITEMS[pos];if(!it)return;
  let sel=document.querySelector('[data-bulk-dbt="'+pos+'"]');
  if(sel){
    let v=String(sel.value||'').trim();
    if(sel.tagName==='INPUT'){it.ai_dbt=v;it.matched_existing=false}
    else if(v&&v!=='__custom__'){it.ai_dbt=v;it.matched_existing=!!it.matched_existing}
  }
  let cb=document.querySelector('[data-bulk-dbt-check="'+pos+'"]');
  if(cb)it.selected=!!cb.checked;
}
function bulkDbtSyncAllFromDom(){for(let i=0;i<ADMIN_DBT_REVIEW_ITEMS.length;i++)bulkDbtSyncRowFromDom(i)}
function bulkDbtSetBusy(on){
  BULK_DBT_BUSY=!!on;
  ['bulkDbtRerunBtn','bulkDbtSelectAllBtn','bulkDbtApplyBtnTop','bulkDbtApplyBtnBot','bulkDbtDupScanBtn','bulkDbtDupFilterBtn','bulkDbtDupAllBtn','bulkDbtDupTickBtn','bulkDbtDupDelBtn'].forEach(id=>{let b=document.getElementById(id);if(b)b.disabled=!!on});
}
function bulkDbtOptSelected(ai,cur,v){let pick=String(ai||cur||'').trim();if(!pick||!v)return false;return pick===v||normText(pick)===normText(v)}
function bulkDbtLoadAiProvider(){return adminChosenAiProvider()}
function bulkDbtSaveAiProvider(p){return adminSaveChosenAiProvider(p)}
function bulkDbtAiProvider(){return bulkDbtLoadAiProvider()}
function bulkDbtCycleAiProvider(){let order=['GEMINI','ANTHROPIC','OPENAI'];let cur=bulkDbtAiProvider();return bulkDbtSaveAiProvider(order[(order.indexOf(cur)+1)%order.length])}
function bulkDbtSyncAiBadge(){let p=bulkDbtAiProvider();let sel=document.getElementById('bulkDbtAiSelect');if(sel)sel.value=p;let badge=document.getElementById('bulkDbtAiBadge');if(!badge)return;badge.classList.remove('hide','claude','gemini','openai');if(p==='ANTHROPIC'){badge.classList.add('claude');badge.textContent='✨ Claude'}else if(p==='OPENAI'){badge.classList.add('openai');badge.textContent='✅ GPT'}else{badge.classList.add('gemini');badge.textContent='⚡ Gemini'}}
function bulkDbtAiProviderLabel(p){p=String(p||'').toUpperCase();if(p.includes('ANTHROPIC')||p.includes('CLAUDE'))return 'Claude';if(p.includes('OPENAI')||p.includes('GPT'))return 'GPT';return 'Gemini'}
function bulkLevelSyncAiBadge(){let p=bulkDbtAiProvider();let sel=document.getElementById('bulkLevelAiSelect');if(sel)sel.value=p;let badge=document.getElementById('bulkLevelAiBadge');if(!badge)return;badge.classList.remove('hide','claude','gemini','openai');if(p==='ANTHROPIC'){badge.classList.add('claude');badge.textContent='✨ Claude'}else if(p==='OPENAI'){badge.classList.add('openai');badge.textContent='✅ GPT'}else{badge.classList.add('gemini');badge.textContent='⚡ Gemini'}}
function bulkDbtBatchLooksBillingFail(j){if(!j||parseInt(j.detected||0,10)>0)return false;let txt=String(j.warning||'')+((j.items||[]).map(it=>it.reason||'').join(' '));return /billing|not active|payment|402|account has been/i.test(txt)}
function closeBulkDbtReview(){let m=document.getElementById('bulkDbtModal');if(m)m.classList.add('hide')}
function openBulkDbtReview(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(!Array.isArray(QUESTIONS)||!QUESTIONS.length){alert('Hãy mở một đề/chuyên đề trước. Nút này gợi ý Dạng bài tập cho các câu đang xem.');return}
  let m=document.getElementById('bulkDbtModal');if(m)m.classList.remove('hide');
  BULK_DBT_DUP_FILTER='all';
  BULK_DBT_DUP_READY=false;
  BULK_DBT_HIDE_SAVED=false;
  let hideSavedBtn=document.getElementById('bulkDbtHideSavedBtn');
  if(hideSavedBtn){hideSavedBtn.textContent='🙈 Ẩn đã lưu';hideSavedBtn.style.fontWeight='';hideSavedBtn.style.background='';hideSavedBtn.style.borderColor='';hideSavedBtn.style.color=''}
  ensureBulkDbtDupBar();
  bulkDbtLoadAdminGuide();
  bulkDbtSyncAiBadge();
  ADMIN_DBT_REVIEW_ITEMS=QUESTIONS.map((q,i)=>({index:i,row:q._row||'',ID:q.ID||'',Dang:q.Dang||resolveDang(q),Mon:q.Mon||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',current_dbt:String(q.DangBaiTap||'').trim(),prev_ai_dbt:'',ai_dbt:'',matched_existing:false,suggestions:adminDangBaiTapSuggestionsForQuestion(q),reason:'',preview:questionPreviewShort(q),selected:false,saved:false,dup_delete:false}));
  renderBulkDbtList();
  let st=document.getElementById('bulkDbtStatus');
  let aiLbl=bulkDbtAiProviderLabel(bulkDbtAiProvider());
  if(st)st.innerHTML='<span class="muted">AI: <b>'+aiLbl+'</b> · Bấm <b>🤖 Chạy AI gợi ý</b> để phân loại '+QUESTIONS.length+' câu.</span>';
}
function bulkDbtOptsHtml(it,pos){
  let ai=String(it.ai_dbt||'').trim();
  let cur=String(it.current_dbt||'').trim();
  let prevAi=String(it.prev_ai_dbt||'').trim();
  let seen={},opts=[];
  function add(v){v=String(v||'').trim();if(!v)return;let k=normText(v);if(seen[k])return;seen[k]=1;opts.push(v)}
  for(let s of bulkDbtAdminTypesForItem(it))add(s);
  add(ai);add(prevAi);add(cur);
  for(let s of bulkDbtLessonCanonicalForItem(it))add(s);
  for(let s of (it.suggestions||[]))add(s);
  if(opts.length>DBT_MAX_PER_LESSON+2)opts=opts.slice(0,DBT_MAX_PER_LESSON+2);
  if(!opts.length)return `<input type="text" data-bulk-dbt="${pos}" value="${escAttr(ai||cur)}" style="flex:1;min-width:180px;padding:6px 8px;border-radius:8px;border:1px solid var(--border)" oninput="bulkDbtInput(${pos},this.value)" />`;
  let selPick=ai||cur;
  let optHtml=opts.map(v=>`<option value="${escAttr(v)}"${bulkDbtOptSelected(ai,cur,v)?' selected':''}>${esc(v)}</option>`).join('');
  if(selPick&&!opts.some(v=>bulkDbtOptSelected(selPick,'',v)))optHtml=`<option value="${escAttr(selPick)}" selected>${esc(selPick)}</option>`+optHtml;
  return `<select data-bulk-dbt="${pos}" onchange="bulkDbtSet(${pos},this.value)" style="flex:1;min-width:180px;padding:6px 8px;border-radius:8px;border:1px solid var(--border)">${optHtml}<option value="__custom__">✏️ Nhập khác…</option></select>`;
}
function renderBulkDbtList(){
  let box=document.getElementById('bulkDbtList');if(!box)return;
  if(BULK_DBT_BUSY&&!ADMIN_DBT_REVIEW_ITEMS.length){box.innerHTML='<div class="muted" style="padding:20px;text-align:center">⏳ Đang chờ AI...</div>';return}
  if(!ADMIN_DBT_REVIEW_ITEMS.length){box.innerHTML='<div class="muted">Chưa có dữ liệu.</div>';return}
  let entries=bulkDbtListEntries();
  if(BULK_DBT_DUP_FILTER==='dup'&&!entries.length){
    box.innerHTML='<div class="muted" style="padding:16px;line-height:1.5">'+(BULK_DBT_DUP_READY?'Không có câu trùng trong đề này.':'Chưa quét trùng — bấm «🔍 Quét trùng» trước.<br>Hoặc bấm «📋 Tất cả» để xem lại toàn bộ.')+'</div>';
    return;
  }
  box.innerHTML=entries.map(({it,pos})=>{
    let ai=String(it.ai_dbt||'').trim();
    let cur=String(it.current_dbt||'').trim();
    let prevAi=String(it.prev_ai_dbt||'').trim();
    let changed=bulkDbtHasChange(it);
    let isLocked=!!it.locked;
    let checked=(!isLocked&&it.selected)?'checked':'';
    let ok='';
    if(isLocked){
      ok=`<span class="tag" style="background:#e0e7ef;color:#64748b">🔒 Đã duyệt — khoá</span>`;
    }else if(ai){
      if(prevAi&&normText(prevAi)!==normText(ai)){
        ok=`<span class="muted">Gợi ý cũ:</span> <span class="tag" style="background:#fef3c7;color:#92400e">${esc(prevAi)}</span> <span style="font-weight:800">→</span> <span class="tag" style="background:#dbeafe;color:#1e40af">Mới: ${esc(ai)}</span>`;
      }else if(changed){
        ok=`<span class="muted">Sheet:</span> <b style="color:#166534">${esc(cur)}</b> <span style="font-weight:800">→</span> <span class="tag" style="background:#dbeafe;color:#1e40af">AI: ${esc(ai)}</span>`;
      }else{
        ok=`<span class="tag" style="background:#dcfce7;color:#166534">AI: ${esc(ai)}</span>${it.matched_existing?' <span class="muted">(dạng có sẵn)</span>':''}`;
      }
    }else{
      ok='<span class="muted">AI chưa gợi ý</span>';
    }
    let saved=it.saved?` <span class="tag" style="background:#bbf7d0;color:#14532d">✅ ${isGithubBank()?'Đã lưu':'Đã lưu Sheet'}</span>`:'';
    let dupBox='';
    if(BULK_DBT_DUP_READY&&it.dup_type){
      dupBox=it.dup_keep?` <span class="tag" style="background:#fef3c7;color:#92400e">⚠️ Trùng (giữ · dòng ${esc(it.row||'?')})</span>`:` <span class="tag" style="background:#fee2e2;color:#991b1b">🔁 Trùng câu ${it.dup_mates.join(', ')}</span>`;
      if(!it.dup_keep&&!isLocked)dupBox+=` <label style="display:inline-flex;gap:4px;align-items:center;font-weight:800;cursor:pointer;color:#991b1b"><input type="checkbox" data-bulk-dbt-dupdel="${pos}" ${it.dup_delete?'checked':''} ${BULK_DBT_BUSY?'disabled':''} onchange="bulkDbtToggleDupDelete(${pos},this.checked)"> Xóa trùng</label>`;
    }
    // Border: locked = xám, còn lại như cũ
    let border=isLocked?'border:1px solid #cbd5e1;background:#f8fafc;opacity:.7':
      (it.saved?'border:2px solid #86efac;background:#f0fdf4':
      (BULK_DBT_DUP_READY&&it.dup_type&&!it.dup_keep?'border:2px solid #fca5a5;background:#fff7f7':
      ((changed||prevAi)?'border:2px solid #fbbf24;background:#fffbeb':
      (it.selected?'border:2px solid #93c5fd;background:#eff6ff':'border:1px solid var(--border);background:var(--bg)'))));
    let acceptLbl=isLocked?'🔒 Đã duyệt':bulkDbtAcceptLabel(it);
    let chkDisabled=(BULK_DBT_BUSY||isLocked)?'disabled':'';
    // Ẩn ô Chốt dạng và nút Chấp nhận nếu đã khoá
    let actionRow=isLocked
      ?`<div style="margin-top:6px;font-size:12px;color:#94a3b8">Câu đã duyệt — không thể thay đổi Dạng BT. Bỏ duyệt trước nếu muốn chỉnh.</div>`
      :`<div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span>Chốt dạng:</span>${bulkDbtOptsHtml(it,pos)}<button type="button" class="btnSmall" onclick="bulkDbtAcceptOne(${pos})" ${BULK_DBT_BUSY?'disabled':''}>💾 Chấp nhận câu này</button></div>`;
    return `<div class="latexQCard" style="margin:0 0 10px;padding:10px;${border};border-radius:10px">
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:space-between">
        <div><b>Câu ${it.index+1}</b> · ${esc(it.Dang||'')} · hiện tại Sheet: ${cur?`<b style="color:#166534">${esc(cur)}</b>`:'<span class="muted">—</span>'} · ${ok}${saved}${dupBox}</div>
        <label style="display:flex;gap:6px;align-items:center;font-weight:800;${isLocked?'opacity:.4;cursor:not-allowed':'cursor:pointer'}"><input type="checkbox" data-bulk-dbt-check="${pos}" ${checked} ${chkDisabled} onchange="bulkDbtToggle(${pos},this.checked)"> ${esc(acceptLbl)}</label>
      </div>
      <div class="muted" style="font-size:12px;margin-top:4px">ID: ${esc(it.ID||'—')} · dòng Sheet: ${esc(it.row||'—')}${it.Mon?' · '+esc(it.Mon):''}${it.BaiHoc?' · '+esc(it.BaiHoc):''}</div>
      <div style="margin-top:6px;line-height:1.45">${esc(it.preview||'')}</div>
      <div class="muted" style="margin-top:6px">${it.reason?'Lý do: '+esc(it.reason):'AI sẽ ghi lý do ngắn tại đây.'}</div>
      ${actionRow}
    </div>`;
  }).join('');
}
function bulkDbtEnsureValue(it){
  if(bulkDbtChosen(it))return bulkDbtChosen(it);
  let sug=(it.suggestions||[]).find(x=>String(x||'').trim());
  if(sug){it.ai_dbt=String(sug).trim();return it.ai_dbt}
  return '';
}
function bulkDbtToggle(pos,on){
  if(BULK_DBT_BUSY)return;
  if(!ADMIN_DBT_REVIEW_ITEMS[pos])return;
  if(ADMIN_DBT_REVIEW_ITEMS[pos].locked){
    let cb=document.querySelector('[data-bulk-dbt-check="'+pos+'"]');
    if(cb)cb.checked=false;
    return;
  }
  bulkDbtSyncRowFromDom(pos);
  let it=ADMIN_DBT_REVIEW_ITEMS[pos];
  if(on){
    let v=bulkDbtEnsureValue(it);
    if(!v){
      alert('Câu '+(it.index+1)+': chưa có Dạng BT.\n\n• Đợi dòng ⏳ AI xong\n• Hoặc chọn/gõ ở ô «Chốt dạng» rồi tick lại');
      let cb=document.querySelector('[data-bulk-dbt-check="'+pos+'"]');
      if(cb)cb.checked=false;
      it.selected=false;
      return;
    }
    let cur=String(it.current_dbt||'').trim();
    if(cur&&normText(cur)!==normText(v)){
      if(!confirm('Câu '+(it.index+1)+': đổi dạng Sheet «'+cur+'» → «'+v+'»?')){let cb=document.querySelector('[data-bulk-dbt-check="'+pos+'"]');if(cb)cb.checked=false;it.selected=false;return}
    }
  }
  it.selected=!!on;
}
function bulkDbtSet(pos,v){
  if(BULK_DBT_BUSY)return;
  if(!ADMIN_DBT_REVIEW_ITEMS[pos])return;
  if(v==='__custom__'){let nv=prompt('Nhập Dạng bài tập:',ADMIN_DBT_REVIEW_ITEMS[pos].ai_dbt||ADMIN_DBT_REVIEW_ITEMS[pos].current_dbt||'');if(nv===null)return;v=String(nv).trim()}
  ADMIN_DBT_REVIEW_ITEMS[pos].ai_dbt=String(v||'').trim();
  ADMIN_DBT_REVIEW_ITEMS[pos].matched_existing=false;
  ADMIN_DBT_REVIEW_ITEMS[pos].selected=false;
  ADMIN_DBT_REVIEW_ITEMS[pos].saved=false;
  renderBulkDbtList();
}
function bulkDbtInput(pos,v){
  if(!ADMIN_DBT_REVIEW_ITEMS[pos])return;
  ADMIN_DBT_REVIEW_ITEMS[pos].ai_dbt=String(v||'').trim();
  ADMIN_DBT_REVIEW_ITEMS[pos].matched_existing=false;
  ADMIN_DBT_REVIEW_ITEMS[pos].selected=false;
  ADMIN_DBT_REVIEW_ITEMS[pos].saved=false;
}
function bulkDbtSelectAllAi(){
  if(BULK_DBT_BUSY){alert('Đang chờ AI gợi ý — đợi dòng trạng thái ⏳ xong rồi bấm lại.');return}
  bulkDbtSyncAllFromDom();
  let n=0;
  for(let it of ADMIN_DBT_REVIEW_ITEMS){
    bulkDbtEnsureValue(it);
    it.selected=!!bulkDbtChosen(it);
    if(it.selected)n++;
  }
  renderBulkDbtList();
  if(!n)alert('Chưa có gợi ý nào để tick.\n\n• Đợi AI chạy xong\n• Hoặc bấm «🤖 Chạy AI gợi ý»\n• Hoặc chọn Dạng BT ở ô «Chốt dạng» từng câu');
}
function bulkDbtSelectNone(){for(let it of ADMIN_DBT_REVIEW_ITEMS)it.selected=false;renderBulkDbtList()}
function bulkDbtToggleHideSaved(){
  BULK_DBT_HIDE_SAVED=!BULK_DBT_HIDE_SAVED;
  let btn=document.getElementById('bulkDbtHideSavedBtn');
  if(btn){
    btn.textContent=BULK_DBT_HIDE_SAVED?'👁 Hiện tất cả':'🙈 Ẩn đã xong';
    btn.style.fontWeight=BULK_DBT_HIDE_SAVED?'800':'';
    btn.style.background=BULK_DBT_HIDE_SAVED?'#dbeafe':'';
    btn.style.borderColor=BULK_DBT_HIDE_SAVED?'#3b82f6':'';
    btn.style.color=BULK_DBT_HIDE_SAVED?'#1e40af':'';
  }
  let savedCount=ADMIN_DBT_REVIEW_ITEMS.filter(it=>it.saved||it.locked).length;
  let st=document.getElementById('bulkDbtStatus');
  if(st&&savedCount>0)st.textContent=(BULK_DBT_HIDE_SAVED?`Đang ẩn ${savedCount} câu đã xong/duyệt.`:`Hiện tất cả (${savedCount} câu đã xong).`);
  renderBulkDbtList();
}
function bulkDbtQuestionPayload(q,i){
  return {index:i,row:q._row||'',ID:q.ID||'',MaDe:q.MaDe||'',Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',DangBaiTap:q.DangBaiTap||'',Dang:q.Dang||resolveDang(q),MucDo:q.MucDo||'',CauHoi:q.CauHoi||'',A:q.A||'',B:q.B||'',C:q.C||'',D:q.D||''};
}
async function bulkDbtDetectCurrent(){
  if(!USER.is_admin)return;
  if(!QUESTIONS.length){alert('Chưa mở đề.');return}

  // ── Lọc câu cần AI phân loại: bỏ qua câu đã duyệt (khoá) thôi ──
  let needAI=QUESTIONS.filter(q=>{
    let approved=String(q.TrangThai||'').trim();
    let kn=approved.toLowerCase().replace(/\s/g,'');
    let isApproved=(kn==='đãduyệt'||kn==='dadduyet'||kn==='approved'||kn==='daduyệt'||kn==='duyet'||kn==='ok'||kn==='✓'||approved==='ĐÃ DUYỆT');
    return !isApproved;
  });
  let skipApproved=QUESTIONS.filter(q=>{
    let kn=String(q.TrangThai||'').trim().toLowerCase().replace(/\s/g,'');
    return kn==='đãduyệt'||kn==='dadduyet'||kn==='approved'||kn==='daduyệt'||kn==='duyet'||kn==='ok'||kn==='✓'||String(q.TrangThai||'').trim()==='ĐÃ DUYỆT';
  });

  let hasExisting=ADMIN_DBT_REVIEW_ITEMS&&ADMIN_DBT_REVIEW_ITEMS.some(it=>String(it.ai_dbt||'').trim());
  let prevSnap={};
  (ADMIN_DBT_REVIEW_ITEMS||[]).forEach(it=>{prevSnap[parseInt(it.index,10)]=Object.assign({},it)});
  let total=needAI.length;
  let chosenAi=bulkDbtAiProvider();
  let aiInfo=bulkDbtAiProviderLabel(chosenAi);
  if(chosenAi==='GEMINI'&&_loadAnthropicKey())aiInfo+=' (tự chuyển Claude nếu hết quota)';

  let skipMsg='';
  if(skipApproved.length)skipMsg+=`\n• Bỏ qua ${skipApproved.length} câu đã duyệt (khoá, không đổi được)`;
  if(!total){alert('Không có câu nào cần phân loại.\n'+skipMsg.trim());return}

  let msg=hasExisting
    ?`Chạy lại AI gợi ý cho ${total} câu chưa phân loại?\n\nAI: ${aiInfo}${skipMsg}\n\n• Dạng trên Sheet vẫn giữ\n• Không tự ghi Sheet — tick «Chấp nhận đổi» từng câu muốn lưu\n\nBấm OK để tiếp tục.`
    :`Chạy AI gợi ý Dạng BT cho ${total} câu?\n\nAI: ${aiInfo}${skipMsg}\nApp chạy từng lô 12 câu, nghỉ 2s giữa lô.\nSau khi xong, tick «Chấp nhận» rồi «Lưu đã tick».\n\nBấm OK để bắt đầu.`;
  if(!confirm(msg))return;
  let st=document.getElementById('bulkDbtStatus');
  let btn=document.getElementById('bulkDbtBtn');let old=btn?btn.textContent:'';
  let badge=document.getElementById('bulkDbtAiBadge');
  let progWrap=document.getElementById('bulkDbtProgressWrap');
  let progBar=document.getElementById('bulkDbtProgressBar');
  let progText=document.getElementById('bulkDbtProgressText');
  if(progWrap)progWrap.classList.remove('hide');
  if(progBar)progBar.style.width='0%';
  bulkDbtSyncAiBadge();
  bulkDbtSetBusy(true);
  renderBulkDbtList();
  const BATCH=12;
  const BATCH_PAUSE_MS=2000;
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳ AI Dạng BT...'}
    let allItems=[],detected=0,warnings=[],mergedTotal=0,lessonCtx={},batchFails=[];
    let aiCounts={Gemini:0,Claude:0,GPT:0,loi:0};
    function _providerLabel(p){
      p=String(p||'').toUpperCase();
      if(p.includes('ANTHROPIC')||p.includes('CLAUDE'))return 'Claude';
      if(p.includes('OPENAI')||p.includes('GPT'))return 'GPT';
      if(p.includes('GEMINI'))return 'Gemini';
      return 'Gemini';
    }
    // Chỉ gửi needAI lên server — tiết kiệm quota tối đa
    for(let s=0;s<needAI.length;s+=BATCH){
      let end=Math.min(s+BATCH,needAI.length);
      let batchIdx=Math.floor(s/BATCH)+1;
      let pct=Math.round(s/needAI.length*100);
      if(progBar)progBar.style.width=pct+'%';
      if(progText)progText.textContent='Lô '+batchIdx+'/'+Math.ceil(needAI.length/BATCH)+' · câu '+(s+1)+'–'+end+' / '+needAI.length;
      let aiSummary=Object.entries(aiCounts).filter(([k,v])=>k!=='loi'&&v>0).map(([k,v])=>k+' '+v).join(' · ');
      if(st)st.textContent='⏳ Lô '+batchIdx+'/'+Math.ceil(needAI.length/BATCH)+' · câu '+(s+1)+'–'+end+' / '+needAI.length+(aiSummary?' | '+aiSummary:'')+(aiCounts.loi?' | ❌ lỗi '+aiCounts.loi:'');
      let adminGuidePack=bulkDbtAdminTypesByScope();
      let payload={questions:needAI.slice(s,end).map((q,j)=>bulkDbtQuestionPayload(q,s+j)),lesson_dbt_context:lessonCtx,admin_dbt_guide:adminGuidePack.guide||'',admin_dbt_types_by_scope:adminGuidePack.byScope||{}};
      let batchProv=chosenAi;
      try{
        let j=await adminApiPost('/api/ai/detect-dangbaitap-bulk',payload,{timeoutMs:85000,bulk:true,admin_ai_provider:batchProv,admin_ai_allow_gpt_fallback:true});
        if(bulkDbtBatchLooksBillingFail(j)){
          let fallbacks={GEMINI:['ANTHROPIC','OPENAI'],ANTHROPIC:['GEMINI','OPENAI'],OPENAI:['GEMINI','ANTHROPIC']};
          for(let alt of (fallbacks[batchProv]||[])){
            if(st)st.textContent='⚠ '+bulkDbtAiProviderLabel(batchProv)+' lỗi billing → thử '+bulkDbtAiProviderLabel(alt)+'…';
            try{
              j=await adminApiPost('/api/ai/detect-dangbaitap-bulk',payload,{timeoutMs:85000,bulk:true,admin_ai_provider:alt,admin_ai_allow_gpt_fallback:true});
              if(!bulkDbtBatchLooksBillingFail(j)&&parseInt(j.detected||0,10)>0){batchProv=alt;break}
            }catch(e2){}
          }
        }
        let prov=_providerLabel(j.provider_used||j.ai_provider);
        aiCounts[prov]=(aiCounts[prov]||0)+parseInt(j.detected||0,10)||0;
        if(j.provider_used&&badge){
          badge.classList.remove('claude','gemini','openai');
          if(prov==='Claude'){badge.classList.add('claude');badge.textContent='✨ Claude'}
          else if(prov==='GPT'){badge.classList.add('openai');badge.textContent='✅ GPT'}
          else{badge.classList.add('gemini');badge.textContent='⚡ Gemini'}
        }
        (j.items||[]).forEach(it=>allItems.push(it));
        detected+=parseInt(j.detected||0,10)||0;
        mergedTotal+=parseInt(j.dbt_merged||0,10)||0;
        lessonCtx=bulkDbtMergeLessonContext(lessonCtx,j.items||[]);
        if(j.warning)warnings.push(String(j.warning));
      }catch(e){
        batchFails.push((s+1)+'–'+end);
        aiCounts.loi+=(end-s);
        warnings.push('Lô '+(s+1)+'–'+end+': '+(e.message||e));
        if(st)st.textContent='⚠ Lô '+batchIdx+' lỗi — thử lô tiếp sau '+Math.round(BATCH_PAUSE_MS/1000)+'s…';
      }
      if(s+BATCH<needAI.length)await sleepMs(BATCH_PAUSE_MS);
    }
    if(progBar)progBar.style.width='100%';
    if(progText)progText.textContent='✅ Hoàn thành';
    let cons=bulkDbtConsolidateItems(allItems);
    allItems=cons.items||allItems;
    mergedTotal+=parseInt(cons.merged||0,10)||0;
    bulkDbtRebuildLessonCanonical(allItems);
    // Map kết quả AI theo ID câu (needAI có thể không liên tục index)
    let byId={};allItems.forEach(it=>{byId[String(it.ID||'').trim()]=it});
    let needAiIdSet=new Set(needAI.map(q=>String(q.ID||'').trim()));
    ADMIN_DBT_REVIEW_ITEMS=QUESTIONS.map((q,i)=>{
      let qId=String(q.ID||'').trim();
      let it=byId[qId]||{};
      let old=prevSnap[i]||{};
      let oldAi=String(old.ai_dbt||'').trim();
      let newAi=String(it.ai_dbt||'').trim();
      let ai=newAi||oldAi;
      let prevAi='';
      if(hasExisting&&oldAi&&newAi&&normText(oldAi)!==normText(newAi))prevAi=oldAi;
      let canon=bulkDbtLessonCanonicalForItem({Mon:q.Mon||it.Mon||'',Chuong:q.Chuong||it.Chuong||'',BaiHoc:q.BaiHoc||it.BaiHoc||''});
      let adminSug=bulkDbtAdminTypesForItem({Mon:q.Mon||it.Mon||'',Chuong:q.Chuong||it.Chuong||'',BaiHoc:q.BaiHoc||it.BaiHoc||''});
      let baseSug=(canon&&canon.length)?canon:((it.suggestions&&it.suggestions.length)?it.suggestions.slice(0,DBT_MAX_PER_LESSON):adminDangBaiTapSuggestionsForQuestion(q));
      let sug=adminSug.slice();
      for(let v of baseSug){if(!sug.some(x=>normText(x)===normText(v)))sug.push(v)}
      if(prevAi&&!sug.some(x=>normText(x)===normText(prevAi)))sug.unshift(prevAi);
      sug=sug.slice(0,DBT_MAX_PER_LESSON+1);
      let curDbt=String(q.DangBaiTap||old.current_dbt||'').trim();

      // Câu đã duyệt: khoá hoàn toàn
      let kn=String(q.TrangThai||'').trim().toLowerCase().replace(/\s/g,'');
      let isApproved=(kn==='đãduyệt'||kn==='dadduyet'||kn==='approved'||kn==='daduyệt'||kn==='duyet'||kn==='ok'||kn==='✓'||String(q.TrangThai||'').trim()==='ĐÃ DUYỆT');

      let autoTick=!isApproved&&!!ai&&!hasExisting&&(!curDbt||normText(curDbt)===normText(ai));
      return {
        index:i,row:q._row||it.row||old.row||'',
        ID:qId,Dang:q.Dang||it.Dang||old.Dang||resolveDang(q),
        Mon:q.Mon||it.Mon||old.Mon||'',Chuong:q.Chuong||it.Chuong||old.Chuong||'',BaiHoc:q.BaiHoc||it.BaiHoc||old.BaiHoc||'',
        current_dbt:curDbt,prev_ai_dbt:prevAi,ai_dbt:ai,
        matched_existing:!!it.matched_existing,suggestions:sug,
        reason:String(it.reason||old.reason||''),
        preview:it.preview||old.preview||questionPreviewShort(q),
        selected:autoTick,
        saved:!!old.saved&&normText(old.current_dbt||'')===normText(curDbt)&&!newAi,
        locked:isApproved,   // khoá — không tick, không đổi
        dup_type:old.dup_type||'',dup_keep:old.dup_keep!==false,dup_mates:old.dup_mates||[],dup_delete:!!old.dup_delete
      };
    });
    let tick=ADMIN_DBT_REVIEW_ITEMS.filter(x=>x.selected).length;
    let changedN=ADMIN_DBT_REVIEW_ITEMS.filter(x=>!x.locked&&(bulkDbtHasChange(x)||String(x.prev_ai_dbt||'').trim())).length;
    let aiDetail=Object.entries(aiCounts).filter(([k,v])=>k!=='loi'&&v>0).map(([k,v])=>{
      let icon=k==='Claude'?'✨':k==='GPT'?'✅':'⚡';
      return icon+' '+k+': '+v+' câu';
    }).join(' · ');
    let failDetail=aiCounts.loi?(' · ❌ lỗi '+aiCounts.loi+' câu'):'';
    let warnTxt=warnings.filter(Boolean).join(' · ');
    let skipInfo=skipApproved.length?
      '<br><span style="font-size:11px;color:var(--muted)">🔒 '+skipApproved.length+' câu đã duyệt (khoá, không đổi được)</span>':'';
    if(st)st.innerHTML=(batchFails.length?'<b>⚠ Một phần lỗi — lô: '+batchFails.join(', ')+'</b><br>':'')
      +'✅ <b>Xong '+detected+'/'+total+' câu</b>'
      +(hasExisting&&changedN?' · <b style="color:#b45309">'+changedN+' câu có gợi ý đổi — tick «Chấp nhận đổi» rồi Lưu</b>':' · tick sẵn '+tick+' câu')
      +(mergedTotal?' · gộp '+mergedTotal:'')
      +'<br><span style="font-size:11px;color:var(--muted)">'+(aiDetail||'(chưa rõ AI)')
      +failDetail+'</span>'
      +skipInfo
      +(warnTxt?'<br><span style="color:#b45309;font-size:11px">⚠ '+warnTxt+'</span>':'');
    renderBulkDbtList();
  }catch(e){if(st)st.textContent='❌ Không gợi ý được: '+(e.message||e);alert('Lỗi: '+(e.message||e))}
  finally{
    bulkDbtSetBusy(false);
    if(btn){btn.disabled=false;btn.textContent=old||'🤖 Chạy AI gợi ý'}
    renderBulkDbtList();
    setTimeout(()=>{if(progWrap)progWrap.classList.add('hide')},3000);
  }
}
async function bulkDbtDeleteDupTicked(){
  if(!USER.is_admin)return;
  if(BULK_DBT_BUSY){alert('Đợi GPT xong rồi mới xóa.');return}
  if(!BULK_DBT_DUP_READY)await bulkDbtRunDupScan();
  let rows=ADMIN_DBT_REVIEW_ITEMS.filter(it=>it.dup_delete&&it.dup_type&&!it.dup_keep&&(parseInt(it.row,10)||0)>1).map(it=>parseInt(it.row,10));
  if(!rows.length){alert('Chưa tick câu trùng.\n\nBấm «✓ Tick bản trùng» hoặc tick «Xóa trùng» trên card đỏ.');return}
  rows=[...new Set(rows)].sort((a,b)=>a-b);
  if(!confirm('Xóa '+rows.length+' bản trùng khỏi Google Sheet?\n\nDòng: '+rows.join(', ')+'\n\nGiữ bản có dòng Sheet nhỏ nhất.'))return;
  if(!confirm('Xác nhận lần 2: chắc chắn xóa '+rows.length+' câu?'))return;
  let btn=document.getElementById('bulkDbtDupDelBtn'),st=document.getElementById('bulkDbtStatus');
  let oldById={};ADMIN_DBT_REVIEW_ITEMS.forEach(it=>{let k=String(it.ID||'').trim()||('_i'+it.index);oldById[k]=it});
  if(btn){btn.disabled=true;btn.textContent='⏳ Đang xóa…'}
  try{
    if(st)st.textContent='⏳ Đang xóa '+rows.length+' bản trùng…';
    let j=await api('/api/admin/dang-similarity-delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows})});
    purgeLocalQuestionsAfterDeletes(j.rows||rows);
    BULK_DBT_DUP_FILTER='all';BULK_DBT_DUP_READY=false;
    ADMIN_DBT_REVIEW_ITEMS=QUESTIONS.map((q,i)=>{let old=oldById[String(q.ID||'').trim()||('_i'+i)]||{};return {index:i,row:q._row||'',ID:q.ID||'',Dang:q.Dang||resolveDang(q),Mon:q.Mon||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',current_dbt:String(q.DangBaiTap||'').trim(),prev_ai_dbt:String(old.prev_ai_dbt||'').trim(),ai_dbt:String(old.ai_dbt||q.DangBaiTap||'').trim(),matched_existing:!!old.matched_existing,suggestions:old.suggestions||adminDangBaiTapSuggestionsForQuestion(q),reason:String(old.reason||''),preview:questionPreviewShort(q),selected:!!old.selected&&!!String(old.ai_dbt||q.DangBaiTap||'').trim(),saved:!!old.saved,dup_delete:false}});
    renderNav();renderQuestion();refreshCatalogFromMeta();
    if(st)st.textContent='✅ '+(j.message||('Đã xóa '+(j.deleted||rows.length)+' bản trùng.'));
    let el=document.getElementById('bulkDbtDupStatus');if(el){el.textContent='Đã xóa trùng — bấm «🔍 Quét trùng» lại nếu cần.';el.classList.remove('hide')}
    renderBulkDbtList();
  }catch(e){if(st)st.textContent='❌ '+(e.message||e);alert('Xóa trùng lỗi: '+(e.message||e))}
  finally{if(btn){btn.disabled=false;btn.textContent='🗑️ Xóa trùng đã tick'}}
}
function bulkDbtAcceptOne(pos){
  if(!ADMIN_DBT_REVIEW_ITEMS[pos])return;
  let it=ADMIN_DBT_REVIEW_ITEMS[pos];
  bulkDbtSyncRowFromDom(pos);
  let v=bulkDbtChosen(it);
  if(!v){alert('Chưa có dạng để chấp nhận.');return}
  let cur=String(it.current_dbt||'').trim();
  if(cur&&normText(cur)!==normText(v)){
    if(!confirm('Câu '+(it.index+1)+': ghi Sheet «'+cur+'» → «'+v+'»?'))return;
  }
  ADMIN_DBT_REVIEW_ITEMS.forEach((x,i)=>x.selected=i===pos);
  bulkDbtApplySelected();
}
async function bulkDbtApplySelected(){
  if(BULK_DBT_BUSY){alert('Đang chờ GPT gợi ý — đợi xong rồi mới lưu.');return}
  bulkDbtSyncAllFromDom();
  let selected=ADMIN_DBT_REVIEW_ITEMS.filter(it=>it.selected&&bulkDbtChosen(it));
  if(!selected.length){alert('Chưa tick câu nào có Dạng bài tập.\n\nTick ô «Chấp nhận» hoặc bấm «✅ Tick tất cả gợi ý» sau khi GPT xong.');return}
  let noRow=selected.filter(it=>(!it.row||parseInt(it.row,10)<2)&&!String(it.ID||'').trim());
  if(noRow.length){alert('Có '+noRow.length+' câu chưa có dòng Sheet lẫn ID. Bấm 🔄 Đồng bộ Sheet rồi thử lại.');return}
  if(!confirm(isGithubBank()
    ? ('Ghi Dạng bài tập cho '+selected.length+' câu vào ngân hàng GitHub (lưu trên máy, không ghi Google Sheet)?')
    : ('Ghi Dạng bài tập cho '+selected.length+' câu vào cột H Google Sheet?')))return;
  let updates=selected.map(it=>({index:it.index,row:parseInt(it.row,10),ID:it.ID,DangBaiTap:bulkDbtChosen(it)}));
  let st=document.getElementById('bulkDbtStatus');
  try{
    if(st)st.textContent=isGithubBank()
      ? ('⏳ Đang ghi '+updates.length+' Dạng bài tập vào ngân hàng GitHub...')
      : ('⏳ Đang ghi '+updates.length+' Dạng bài tập vào Google Sheet...');
    let j=await api('/api/ai/apply-dangbaitap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({updates})});
    for(let up of updates){
      let q=QUESTIONS[up.index];
      if(q)q.DangBaiTap=up.DangBaiTap;
      let it=ADMIN_DBT_REVIEW_ITEMS.find(x=>x.index===up.index);
      if(it){it.current_dbt=up.DangBaiTap;it.ai_dbt=up.DangBaiTap;it.prev_ai_dbt='';it.saved=true;it.selected=false;it.matched_existing=false}
    }
    LEARNING_CACHE={};
    renderBulkDbtList();renderNav();renderQuestion();
    let scope=patchCatalogDbtAssignLocal(updates);
    renderCatalog();
    flashCatalogLesson(scope);
    await refreshCatalogFromMeta();
    flashCatalogLesson(scope||patchCatalogScopeFromQuestions());
    syncAdminLearningBoard();
    if(st)st.textContent=isGithubBank()
      ? ('✅ Đã cập nhật '+(j.updated||updates.length)+' câu. Các dòng có viền xanh «✅ Đã lưu» — đóng modal để xem câu đang mở.')
      : ('✅ Đã cập nhật '+(j.updated||updates.length)+' câu (cột H). Các dòng có viền xanh «✅ Đã lưu Sheet» — đóng modal để xem câu đang mở.');
  }catch(e){if(st)st.textContent='❌ Không ghi được: '+(e.message||e);alert('Không ghi Dạng bài tập được: '+(e.message||e))}
}

function closeBulkLevelReview(){let m=document.getElementById('bulkLevelModal');if(m)m.classList.add('hide')}
function openBulkLevelReview(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(!Array.isArray(QUESTIONS)||!QUESTIONS.length){alert('Hãy mở một đề/chuyên đề trước. Nút này gợi ý mức độ cho các câu đang xem.');return}
  let m=document.getElementById('bulkLevelModal');if(m)m.classList.remove('hide');
  bulkLevelSyncAiBadge();
  ADMIN_LEVEL_REVIEW_ITEMS=QUESTIONS.map((q,i)=>({index:i,row:q._row||'',ID:q.ID||'',Dang:q.Dang||resolveDang(q),Mon:q.Mon||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',current_md:normMucDoFormVal(q.MucDo||''),ai_md:'',confidence:'',reason:'',preview:questionPreviewShort(q),selected:false,saved:false}));
  renderBulkLevelList();
  bulkLevelDetectCurrent();
}
function bulkLevelSetBusy(on){
  BULK_LEVEL_BUSY=!!on;
  ['bulkLevelRerunBtn','bulkLevelSelectAllBtn','bulkLevelApplyBtnTop','bulkLevelApplyBtnBot','bulkLevelBtn'].forEach(id=>{let b=document.getElementById(id);if(b)b.disabled=!!on});
}
function bulkLevelQuestionPayload(q,i){
  return {index:i,row:q._row||'',ID:q.ID||'',MaDe:q.MaDe||'',Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',DangBaiTap:q.DangBaiTap||'',Dang:q.Dang||resolveDang(q),MucDo:'',CauHoi:q.CauHoi||'',A:q.A||'',B:q.B||'',C:q.C||'',D:q.D||''};
}
function bulkLevelChosen(it){return normMucDoFormVal(String((it&&it.ai_md)||'').trim())}
function bulkLevelOptsHtml(it,pos){
  let ai=normMucDoFormVal(it.ai_md||'');
  let cur=normMucDoFormVal(it.current_md||'');
  let pick=ai||cur||'TH';
  if(!ADMIN_MUCDO_OPTS.includes(pick))pick='TH';
  let optHtml=ADMIN_MUCDO_OPTS.map(v=>`<option value="${v}"${pick===v?' selected':''}>${v} · ${esc(mucdoLabel(v))}</option>`).join('');
  return `<select data-bulk-level="${pos}" onchange="bulkLevelSet(${pos},this.value)" style="flex:0 0 auto;min-width:148px;padding:6px 8px;border-radius:8px;border:1px solid var(--border);font-weight:800">${optHtml}</select>`;
}
function renderBulkLevelList(){
  let box=document.getElementById('bulkLevelList');if(!box)return;
  if(BULK_LEVEL_BUSY&&!ADMIN_LEVEL_REVIEW_ITEMS.length){box.innerHTML='<div class="muted" style="padding:20px;text-align:center">⏳ Đang chờ GPT...</div>';return}
  if(!ADMIN_LEVEL_REVIEW_ITEMS.length){box.innerHTML='<div class="muted">Chưa có dữ liệu.</div>';return}
  box.innerHTML=ADMIN_LEVEL_REVIEW_ITEMS.map((it,pos)=>{
    let ai=normMucDoFormVal(it.ai_md||'');
    let cur=normMucDoFormVal(it.current_md||'');
    let checked=it.selected?'checked':'';
    let aiBadge=ai?`<span class="mucdoBadge ${mucdoBadgeClass(ai)}">AI: ${esc(ai)}</span>`:'<span class="muted">AI chưa gợi ý</span>';
    let saved=it.saved?` <span class="tag" style="background:#bbf7d0;color:#14532d">✅ ${isGithubBank()?'Đã lưu':'Đã lưu Sheet'}</span>`:'';
    let border=it.saved?'border:2px solid #86efac;background:#f0fdf4':(it.selected?'border:2px solid #93c5fd;background:#eff6ff':'border:1px solid var(--border);background:var(--bg)');
    return `<div class="latexQCard" style="margin:0 0 10px;padding:10px;${border};border-radius:10px">
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:space-between">
        <div><b>Câu ${it.index+1}</b> · ${esc(it.Dang||'')} · hiện tại: ${cur?`<span class="mucdoBadge ${mucdoBadgeClass(cur)}">${esc(cur)}</span>`:'<span class="muted">—</span>'} · ${aiBadge}${saved}</div>
        <label style="display:flex;gap:6px;align-items:center;font-weight:800;cursor:pointer"><input type="checkbox" data-bulk-level-check="${pos}" ${checked} ${BULK_LEVEL_BUSY?'disabled':''} onchange="bulkLevelToggle(${pos},this.checked)"> Chấp nhận</label>
      </div>
      <div class="muted" style="font-size:12px;margin-top:4px">ID: ${esc(it.ID||'—')} · dòng Sheet: ${esc(it.row||'—')}${it.Mon?' · '+esc(it.Mon):''}${it.BaiHoc?' · '+esc(it.BaiHoc):''}</div>
      <div style="margin-top:6px;line-height:1.45">${esc(it.preview||'')}</div>
      <div class="muted" style="margin-top:6px">${it.reason?'Lý do: '+esc(it.reason):(it.confidence?'Tin cậy: '+esc(it.confidence):'GPT sẽ ghi lý do ngắn tại đây.')}</div>
      <div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span>Chốt mức:</span>${bulkLevelOptsHtml(it,pos)}<button type="button" class="btnSmall" onclick="bulkLevelAcceptOne(${pos})" ${BULK_LEVEL_BUSY?'disabled':''}>💾 Chấp nhận câu này</button></div>
    </div>`;
  }).join('');
}
function bulkLevelSyncRowFromDom(pos){
  let it=ADMIN_LEVEL_REVIEW_ITEMS[pos];if(!it)return;
  let sel=document.querySelector('[data-bulk-level="'+pos+'"]');
  if(sel){let v=normMucDoFormVal(sel.value||'');if(v){it.ai_md=v;it.selected=!!it.selected}}
  let cb=document.querySelector('[data-bulk-level-check="'+pos+'"]');
  if(cb)it.selected=!!cb.checked;
}
function bulkLevelSyncAllFromDom(){for(let i=0;i<ADMIN_LEVEL_REVIEW_ITEMS.length;i++)bulkLevelSyncRowFromDom(i)}
function bulkLevelToggle(pos,on){
  if(BULK_LEVEL_BUSY)return;
  if(!ADMIN_LEVEL_REVIEW_ITEMS[pos])return;
  bulkLevelSyncRowFromDom(pos);
  let it=ADMIN_LEVEL_REVIEW_ITEMS[pos];
  if(on){
    let v=bulkLevelChosen(it);
    if(!v){
      alert('Câu '+(it.index+1)+': chưa có mức độ.\n\n• Đợi GPT xong\n• Hoặc chọn NB/TH/VD/VDC ở ô «Chốt mức» rồi tick lại');
      let cb=document.querySelector('[data-bulk-level-check="'+pos+'"]');
      if(cb)cb.checked=false;
      it.selected=false;
      return;
    }
    it.ai_md=v;
  }
  it.selected=!!on;
}
function bulkLevelSet(pos,v){
  if(BULK_LEVEL_BUSY)return;
  if(!ADMIN_LEVEL_REVIEW_ITEMS[pos])return;
  v=normMucDoFormVal(v||'');
  if(!v)return;
  ADMIN_LEVEL_REVIEW_ITEMS[pos].ai_md=v;
  ADMIN_LEVEL_REVIEW_ITEMS[pos].selected=true;
  ADMIN_LEVEL_REVIEW_ITEMS[pos].saved=false;
  renderBulkLevelList();
}
function bulkLevelSelectAllAi(){
  if(BULK_LEVEL_BUSY){alert('Đang chờ GPT gợi ý — đợi dòng trạng thái ⏳ xong rồi bấm lại.');return}
  bulkLevelSyncAllFromDom();
  let n=0;
  for(let it of ADMIN_LEVEL_REVIEW_ITEMS){
    if(bulkLevelChosen(it)){it.selected=true;n++}
  }
  renderBulkLevelList();
  if(!n)alert('Chưa có gợi ý nào để tick.\n\n• Đợi AI chạy xong\n• Hoặc bấm «🤖 Chạy AI gợi ý»');
}
function bulkLevelSelectNone(){for(let it of ADMIN_LEVEL_REVIEW_ITEMS)it.selected=false;renderBulkLevelList()}
async function bulkLevelDetectCurrent(){
  if(!USER.is_admin)return;
  if(!QUESTIONS.length){alert('Chưa mở đề.');return}
  let chosenAi=bulkDbtAiProvider();
  let aiLbl=bulkDbtAiProviderLabel(chosenAi);
  let st=document.getElementById('bulkLevelStatus');
  let btn=document.getElementById('bulkLevelBtn');let old=btn?btn.textContent:'';
  bulkLevelSyncAiBadge();
  bulkLevelSetBusy(true);
  renderBulkLevelList();
  const BATCH=20;
  const BATCH_PAUSE_MS=1500;
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳ AI mức độ...'}
    let allItems=[],detected=0,warnings=[],batchFails=[],aiCounts={Gemini:0,Claude:0,GPT:0,loi:0};
    function _provLbl(p){return bulkDbtAiProviderLabel(p)}
    for(let s=0;s<QUESTIONS.length;s+=BATCH){
      let end=Math.min(s+BATCH,QUESTIONS.length);
      let batchIdx=Math.floor(s/BATCH)+1;
      let aiSummary=Object.entries(aiCounts).filter(([k,v])=>k!=='loi'&&v>0).map(([k,v])=>k+' '+v).join(' · ');
      if(st)st.textContent='⏳ '+aiLbl+' gợi ý mức độ: câu '+(s+1)+'–'+end+' / '+QUESTIONS.length+' (lô '+batchIdx+'/'+Math.ceil(QUESTIONS.length/BATCH)+')'+(aiSummary?' | '+aiSummary:'');
      let payload={questions:QUESTIONS.slice(s,end).map((q,j)=>bulkLevelQuestionPayload(q,s+j))};
      let batchProv=chosenAi;
      try{
        let j=await adminApiPost('/api/ai/detect-level-bulk',payload,{timeoutMs:90000,bulk:true,admin_ai_provider:batchProv,admin_ai_allow_gpt_fallback:true});
        if(bulkDbtBatchLooksBillingFail(j)){
          let fallbacks={GEMINI:['ANTHROPIC','OPENAI'],ANTHROPIC:['GEMINI','OPENAI'],OPENAI:['GEMINI','ANTHROPIC']};
          for(let alt of (fallbacks[batchProv]||[])){
            if(st)st.textContent='⚠ '+_provLbl(batchProv)+' lỗi billing → thử '+_provLbl(alt)+'…';
            try{
              j=await adminApiPost('/api/ai/detect-level-bulk',payload,{timeoutMs:90000,bulk:true,admin_ai_provider:alt,admin_ai_allow_gpt_fallback:true});
              if(!bulkDbtBatchLooksBillingFail(j)&&parseInt(j.detected||0,10)>0){batchProv=alt;break}
            }catch(e2){}
          }
        }
        let prov=_provLbl(j.provider_used||j.ai_provider||batchProv);
        aiCounts[prov]=(aiCounts[prov]||0)+parseInt(j.detected||0,10)||0;
        (j.items||[]).forEach(it=>allItems.push(it));
        detected+=parseInt(j.detected||0,10)||0;
        if(j.warning)warnings.push(String(j.warning));
      }catch(e){
        batchFails.push((s+1)+'–'+end);
        aiCounts.loi+=(end-s);
        warnings.push('Lô câu '+(s+1)+'–'+end+': '+(e.message||e));
      }
      if(s+BATCH<QUESTIONS.length)await sleepMs(BATCH_PAUSE_MS);
    }
    let byIndex={};allItems.forEach(it=>{byIndex[parseInt(it.index,10)]=it});
    ADMIN_LEVEL_REVIEW_ITEMS=QUESTIONS.map((q,i)=>{
      let it=byIndex[i]||{};
      let ai=normMucDoFormVal(it.ai_mucdo||it.MucDo||'');
      return {index:i,row:q._row||it.row||'',ID:q.ID||it.ID||'',Dang:q.Dang||it.Dang||resolveDang(q),Mon:q.Mon||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',current_md:normMucDoFormVal(q.MucDo||''),ai_md:ai,confidence:String(it.confidence||''),reason:String(it.reason||''),preview:it.preview||questionPreviewShort(q),selected:!!ai,saved:false};
    });
    let tick=ADMIN_LEVEL_REVIEW_ITEMS.filter(x=>x.selected).length;
    let aiDetail=Object.entries(aiCounts).filter(([k,v])=>k!=='loi'&&v>0).map(([k,v])=>{
      let icon=k==='Claude'?'✨':k==='GPT'?'✅':'⚡';
      return icon+' '+k+': '+v+' câu';
    }).join(' · ');
    let warn=warnings.filter(Boolean).join(' · ');
    if(st)st.textContent=(batchFails.length?'⚠ Hoàn thành một phần — lô lỗi: '+batchFails.join(', ')+'\n':'')+'✅ AI gợi ý xong '+detected+'/'+QUESTIONS.length+' câu · đã tick '+tick+' câu.'+(aiDetail?'\n'+aiDetail:'')+(aiCounts.loi?'\n❌ lỗi '+aiCounts.loi+' câu':'')+(warn?'\n⚠ '+warn:'');
    renderBulkLevelList();
  }catch(e){
    if(st)st.textContent='❌ Không gợi ý được: '+(e.message||e);
    alert('Không gợi ý mức độ hàng loạt được: '+(e.message||e)+'\n\nThử chọn ⚡ Gemini hoặc ✨ Claude ở góc phải modal.');
  }finally{
    bulkLevelSetBusy(false);
    if(btn){btn.disabled=false;btn.textContent=old||'🎯 Mức độ'}
    renderBulkLevelList();
  }
}
function bulkLevelAcceptOne(pos){if(!ADMIN_LEVEL_REVIEW_ITEMS[pos])return;ADMIN_LEVEL_REVIEW_ITEMS.forEach((it,i)=>it.selected=i===pos);bulkLevelApplySelected()}
async function bulkLevelApplySelected(){
  if(BULK_LEVEL_BUSY){alert('Đang chờ GPT gợi ý — đợi xong rồi mới lưu.');return}
  bulkLevelSyncAllFromDom();
  let selected=ADMIN_LEVEL_REVIEW_ITEMS.filter(it=>it.selected&&bulkLevelChosen(it));
  if(!selected.length){alert('Chưa tick câu nào có mức độ.\n\nTick ô «Chấp nhận» hoặc bấm «✅ Tick tất cả gợi ý» sau khi GPT xong.');return}
  let noRow=selected.filter(it=>(!it.row||parseInt(it.row,10)<2)&&!String(it.ID||'').trim());
  if(noRow.length){alert('Có '+noRow.length+' câu chưa có dòng Sheet lẫn ID. Bấm 🔄 Đồng bộ Sheet rồi thử lại.');return}
  if(!confirm(isGithubBank()
    ? ('Ghi mức độ cho '+selected.length+' câu vào ngân hàng GitHub (lưu trên máy, không ghi Google Sheet)?')
    : ('Ghi mức độ cho '+selected.length+' câu vào cột I Google Sheet?')))return;
  let updates=selected.map(it=>({index:it.index,row:parseInt(it.row,10),ID:it.ID,MucDo:bulkLevelChosen(it)}));
  let st=document.getElementById('bulkLevelStatus');
  try{
    if(st)st.textContent=isGithubBank()
      ? ('⏳ Đang ghi '+updates.length+' mức độ vào ngân hàng GitHub...')
      : ('⏳ Đang ghi '+updates.length+' mức độ vào Google Sheet...');
    let j=await api('/api/ai/apply-levels',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({updates})});
    for(let up of updates){
      let q=QUESTIONS[up.index];
      if(q)q.MucDo=up.MucDo;
      let it=ADMIN_LEVEL_REVIEW_ITEMS.find(x=>x.index===up.index);
      if(it){it.current_md=up.MucDo;it.ai_md=up.MucDo;it.saved=true;it.selected=false}
    }
    renderBulkLevelList();renderNav();renderQuestion();
    if(st)st.textContent=isGithubBank()
      ? ('✅ Đã cập nhật '+(j.updated||updates.length)+' câu. Các dòng có viền xanh «✅ Đã lưu» — đóng modal để xem nav màu mức độ.')
      : ('✅ Đã cập nhật '+(j.updated||updates.length)+' câu (cột I). Các dòng có viền xanh «✅ Đã lưu Sheet» — đóng modal để xem nav màu mức độ.');
  }catch(e){
    if(st)st.textContent='❌ Không ghi được: '+(e.message||e);
    alert('Không ghi mức độ được: '+(e.message||e));
  }
}


let DBT_MERGE_MADE='';
let DBT_MERGE_ITEMS=[];
function patchCatalogDbtMergeLocal(made,oldNames,newName){
  made=String(made||'').trim();newName=String(newName||'').trim();if(!newName)return null;
  let keys=new Set((oldNames||[]).map(n=>normText(String(n||''))).filter(Boolean));if(!keys.size)return null;
  let scope=null;
  for(let x of CATALOG||[]){
    if(made&&String(x.MaDe||'')!==made)continue;
    let fc=((x.FilterCounts||{}).dangbaitap)||{};if(typeof fc!=='object')continue;
    let add=0,nc=Object.assign({},fc);
    for(let [k,v] of Object.entries(fc)){if(keys.has(normText(k))){add+=parseInt(v,10)||0;delete nc[k]}}
    if(!add&&keys.has(normText(x.DangBaiTap||'')))add=1;
    if(!add)continue;
    nc[newName]=(parseInt(nc[newName],10)||0)+add;
    x.FilterCounts=Object.assign({},x.FilterCounts||{},{dangbaitap:nc});
    if(x.DangBaiTap&&keys.has(normText(x.DangBaiTap)))x.DangBaiTap=newName;
    scope=scope||x;
  }
  for(let q of QUESTIONS||[]){if(keys.has(normText(q.DangBaiTap||'')))q.DangBaiTap=newName}
  return scope;
}
function patchCatalogDbtAssignLocal(updates){
  updates=updates||[];let scope=null;
  for(let up of updates){
    let q=QUESTIONS[up.index];if(!q)continue;
    let it=ADMIN_DBT_REVIEW_ITEMS.find(x=>x.index===up.index)||{};
    let oldN=normText(String(it.current_dbt||q.DangBaiTap||''));
    let newN=String(up.DangBaiTap||'').trim();if(!newN||oldN===normText(newN))continue;
    q.DangBaiTap=newN;
    for(let x of CATALOG||[]){
      if(String(x.MaDe||'')!==String(q.MaDe||''))continue;
      let fc=Object.assign({},((x.FilterCounts||{}).dangbaitap)||{});
      if(oldN){for(let k of Object.keys(fc)){if(normText(k)===oldN){fc[k]=Math.max(0,(parseInt(fc[k],10)||0)-1);if(fc[k]<=0)delete fc[k];break}}}
      fc[newN]=(parseInt(fc[newN],10)||0)+1;
      x.FilterCounts=Object.assign({},x.FilterCounts||{},{dangbaitap:fc});
      if(x.DangBaiTap&&normText(x.DangBaiTap)===oldN)x.DangBaiTap=newN;
      scope=scope||x;
    }
  }
  return scope;
}
function patchCatalogScopeFromQuestions(){
  let q=QUESTIONS[CUR]||QUESTIONS[0];if(!q)return null;
  return CATALOG.find(x=>String(x.MaDe||'')===String(q.MaDe||''))||{Mon:q.Mon,Lop:q.Lop,Chuong:q.Chuong,BaiHoc:q.BaiHoc,De:q.De};
}
function flashCatalogLesson(scope){
  if(!scope)return;
  let home=document.getElementById('home');if(!home||home.classList.contains('hide'))return;
  let bai=String(scope.BaiHoc||scope.De||'').trim();if(!bai)return;
  requestAnimationFrame(()=>{
    let cards=document.querySelectorAll('.bookLessonCard[data-bai]');
    for(let c of cards){
      if(normText(c.getAttribute('data-bai')||'')===normText(bai)){
        c.classList.add('catalogFlash');
        try{c.scrollIntoView({behavior:'smooth',block:'center'})}catch(e){c.scrollIntoView(true)}
        setTimeout(()=>c.classList.remove('catalogFlash'),2800);
        break;
      }
    }
  });
}
async function refreshAdminCatalogLive(scope){
  try{if(scope)window.__CATALOG_FLASH_SCOPE=scope;if(typeof renderCatalog==='function')renderCatalog();flashCatalogLesson(scope);await refreshCatalogFromMeta();flashCatalogLesson(scope||patchCatalogScopeFromQuestions())}catch(e){console.error('refreshAdminCatalogLive',e)}
}
function closeDbtMergeModal(){let m=document.getElementById('dbtMergeModal');if(m)m.classList.add('hide')}
let DBT_ORDER_MADE='';
let DBT_ORDER_NAMES=[];
function closeDbtOrderModal(){let m=document.getElementById('dbtOrderModal');if(m)m.classList.add('hide')}
function openDbtOrderModal(made){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  made=String(made||CURRENT_MADE||'').trim();
  if(!made){alert('Chưa xác định chuyên đề. Mở từ thẻ Bài hoặc modal làm bài.');return}
  DBT_ORDER_MADE=made;
  let item=CATALOG.find(x=>x.MaDe===made)||{};
  let pairs=catalogDbtCounts(item);
  let ord=getDbtOrderList(made,item);
  let seen={},names=[];
  for(let n of ord){let k=normText(n);if(!seen[k]){seen[k]=1;names.push(n)}}
  for(let [d] of pairs){let k=normText(d);if(!seen[k]){seen[k]=1;names.push(d)}}
  DBT_ORDER_NAMES=names;
  renderDbtOrderModal(item);
  document.getElementById('dbtOrderModal').classList.remove('hide');
}
function renderDbtOrderModal(item){
  item=item||{};
  let scope=document.getElementById('dbtOrderScope');
  if(scope)scope.innerHTML='Phạm vi: <b>'+esc([item.Mon,item.Lop,item.Chuong,item.BaiHoc||item.De].filter(Boolean).join(' · ')||item.MaDe||DBT_ORDER_MADE)+'</b> · kéo thứ tự bằng nút ↑↓';
  let box=document.getElementById('dbtOrderList');
  if(!box)return;
  if(!DBT_ORDER_NAMES.length){box.innerHTML='<div class="muted">Chưa có dạng BT nào trong chuyên đề này.</div>';return}
  let itemFull=CATALOG.find(x=>x.MaDe===DBT_ORDER_MADE)||{};
  let counts={};
  for(let [k,v] of catalogDbtCounts(itemFull))counts[normText(k)]=v;
  box.innerHTML=DBT_ORDER_NAMES.map((name,i)=>{
    let cnt=counts[normText(name)]||0;
    return `<div class="dbtOrderRow"><span class="dbtOrderNum">${i+1}</span><span class="dbtOrderName"><b>${esc(name)}</b>${cnt?(' · '+cnt+' câu'):''}</span><span class="dbtOrderBtns"><button type="button" class="btnSmall" onclick="dbtOrderMove(${i},-1)" ${i===0?'disabled':''}>↑</button><button type="button" class="btnSmall" onclick="dbtOrderMove(${i},1)" ${i===DBT_ORDER_NAMES.length-1?'disabled':''}>↓</button></span></div>`;
  }).join('');
  let st=document.getElementById('dbtOrderStatus');
  if(st)st.textContent='Thứ tự này áp dụng cho mục lục sách và modal «Chọn dạng bài tập».';
}
function dbtOrderMove(pos,dir){
  pos=parseInt(pos,10)||0;dir=parseInt(dir,10)||0;
  if(!DBT_ORDER_NAMES[pos])return;
  let j=pos+dir;
  if(j<0||j>=DBT_ORDER_NAMES.length)return;
  let t=DBT_ORDER_NAMES[pos];
  DBT_ORDER_NAMES[pos]=DBT_ORDER_NAMES[j];
  DBT_ORDER_NAMES[j]=t;
  renderDbtOrderModal(CATALOG.find(x=>x.MaDe===DBT_ORDER_MADE)||{});
}
async function saveDbtOrder(){
  if(!USER.is_admin||!DBT_ORDER_MADE)return;
  let st=document.getElementById('dbtOrderStatus');
  try{
    if(st)st.textContent='⏳ Đang lưu thứ tự...';
    let j=await api('/api/admin/dbt-order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({made:DBT_ORDER_MADE,order:DBT_ORDER_NAMES})});
    let order=j.order||DBT_ORDER_NAMES;
    let scope=patchCatalogDbtOrderLocal(DBT_ORDER_MADE,order);
    await refreshAdminCatalogLive(scope);
    if(document.getElementById('startModal')&&!document.getElementById('startModal').classList.contains('hide'))renderStartDangBaiTapPicker(DBT_ORDER_MADE,CURRENT_DANGBAITAP);
    if(st)st.textContent='✅ Đã lưu thứ tự '+order.length+' dạng.';
    setTimeout(closeDbtOrderModal,600);
  }catch(e){if(st)st.textContent='❌ '+(e.message||e);alert('Không lưu được thứ tự: '+(e.message||e))}
}
function dbtMergeTokens(s){return normText(s).split(/\s+/).filter(w=>w.length>1)}
function dbtSimilarity(a,b){
  let A=dbtMergeTokens(a),B=dbtMergeTokens(b);
  if(!A.length||!B.length){let na=normText(a),nb=normText(b);if(!na||!nb)return 0;return na.includes(nb)||nb.includes(na)?0.82:0}
  let setB=new Set(B),ov=A.filter(x=>setB.has(x)).length;
  return ov/Math.min(A.length,B.length);
}
function dbtSuggestMergeGroups(names){
  names=(names||[]).slice().sort((a,b)=>String(b).length-String(a).length);
  let used=new Set(),groups=[];
  for(let i=0;i<names.length;i++){
    let seed=names[i];if(used.has(seed))continue;
    let grp=[seed];used.add(seed);
    for(let j=0;j<names.length;j++){
      let other=names[j];if(used.has(other))continue;
      if(grp.some(g=>dbtSimilarity(g,other)>=0.42)){grp.push(other);used.add(other)}
    }
    if(grp.length>=2)groups.push(grp);
  }
  return groups;
}
function openDbtMergeModal(made){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  made=String(made||CURRENT_MADE||'').trim();
  if(!made){alert('Chưa xác định chuyên đề. Mở modal từ thẻ Bài hoặc khi đang chọn dạng BT.');return}
  DBT_MERGE_MADE=made;
  let item=CATALOG.find(x=>x.MaDe===made)||{};
  renderDbtMergeModal(item);
  document.getElementById('dbtMergeModal').classList.remove('hide');
}
function renderDbtMergeModal(item){
  item=item||{};
  DBT_MERGE_ITEMS=catalogDbtCounts(item);
  let scope=document.getElementById('dbtMergeScope');
  if(scope)scope.innerHTML='Phạm vi: <b>'+esc([item.Mon,item.Lop,item.Chuong,item.BaiHoc||item.De].filter(Boolean).join(' · ')||item.MaDe||DBT_MERGE_MADE)+'</b> · '+DBT_MERGE_ITEMS.length+' dạng đã phân loại';
  let sug=document.getElementById('dbtMergeSuggest');
  if(sug){
    let groups=dbtSuggestMergeGroups(DBT_MERGE_ITEMS.map(x=>x[0]));
    if(!groups.length)sug.innerHTML='<span class="muted" style="font-size:12px">Chưa thấy nhóm gần giống — tick tay ≥2 tên bên dưới.</span>';
    else sug.innerHTML='<div style="font-size:12px;font-weight:800;margin-bottom:4px">Gợi ý nhóm giống nhau:</div>'+groups.map((g,gi)=>`<button type="button" class="btnSmall dbtMergeGroupBtn" onclick="dbtMergeApplyGroup(${gi})">${esc(g.slice(0,2).join(' + '))}${g.length>2?' +…':''} (${g.length})</button>`).join(' ');
    sug._groups=groups;
  }
  let box=document.getElementById('dbtMergeList');
  if(box){
    if(!DBT_MERGE_ITEMS.length){box.innerHTML='<div class="muted">Chưa có dạng nào để gộp trong chuyên đề này.</div>';return}
    box.innerHTML=DBT_MERGE_ITEMS.map(([d,n],i)=>`<label class="startDbtOpt dbtMergePickRow"><input type="checkbox" class="dbtMergePick" value="${escAttr(oneLineText(d))}" data-count="${n||0}" onchange="dbtMergePreview()"> <span class="startDbtBody"><b class="startDbtName">${esc(oneLineText(d))}</b><span class="startDbtMeta">${n||0} câu</span></span></label>`).join('');
  }
  let nn=document.getElementById('dbtMergeNewName');if(nn&&!nn.value)nn.value='';
  dbtMergePreview();
}
function dbtMergeApplyGroup(gi){
  let groups=(document.getElementById('dbtMergeSuggest')||{})._groups||[];
  let g=groups[gi];if(!g||!g.length)return;
  document.querySelectorAll('.dbtMergePick').forEach(cb=>{cb.checked=g.includes(cb.value)});
  dbtMergePickLongestName();
  dbtMergePreview();
}
function dbtMergeSelectedNames(){return [...document.querySelectorAll('.dbtMergePick:checked')].map(cb=>String(cb.value||'').trim()).filter(Boolean)}
function dbtMergePreview(){
  let st=document.getElementById('dbtMergeStatus');if(!st)return;
  let sel=dbtMergeSelectedNames();
  let cnt=0;document.querySelectorAll('.dbtMergePick:checked').forEach(cb=>{cnt+=parseInt(cb.getAttribute('data-count')||0,10)||0});
  if(sel.length<2){st.textContent=sel.length?'Chọn thêm ít nhất 1 tên nữa để gộp.':'Tick ≥2 tên dạng cần hợp nhất.';return}
  let nn=String(val('dbtMergeNewName')||'').trim();
  st.textContent='Sẽ gộp '+sel.length+' tên → '+(cnt||'?')+' câu'+(nn?(' thành «'+nn+'»'):' (chưa gõ tên mới)');
}
function dbtMergePickLongestName(){
  let sel=dbtMergeSelectedNames();
  if(!sel.length)sel=DBT_MERGE_ITEMS.map(x=>x[0]);
  if(!sel.length)return;
  sel.sort((a,b)=>String(b).length-String(a).length);
  let el=document.getElementById('dbtMergeNewName');if(el){el.value=sel[0];dbtMergePreview()}
}
async function applyDbtMerge(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  let sel=dbtMergeSelectedNames();
  if(!sel.length){alert('Tick ít nhất 1 tên dạng cần gộp hoặc đổi tên.');return}
  let newName=String(val('dbtMergeNewName')||'').trim();
  if(!newName){alert('Gõ tên mới thống nhất (cột H).');return}
  if(adminDbtIsBadValue(newName)){alert('Tên mới không hợp lệ (tránh TN/ĐS/TLN hoặc «chưa gán»).');return}
  if(sel.length===1&&normText(sel[0])===normText(newName)){alert('Tên mới trùng tên cũ.');return}
  if(!confirm((sel.length===1?'Đổi tên «'+sel[0]+'»':'Gộp '+sel.length+' tên dạng')+' thành «'+newName+'» và lưu cột H cho mọi câu trong chuyên đề?'))return;
  let st=document.getElementById('dbtMergeStatus');
  try{
    if(st)st.textContent='⏳ Đang gộp & ghi Google Sheet...';
    let j=await api('/api/admin/merge-dangbaitap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({made:DBT_MERGE_MADE,old_names:sel,new_name:newName})});
    LEARNING_CACHE={};
    let scope=patchCatalogDbtMergeLocal(DBT_MERGE_MADE,sel,j.new_name||newName);
    if(document.getElementById('startModal')&&!document.getElementById('startModal').classList.contains('hide'))renderStartDangBaiTapPicker(DBT_MERGE_MADE,j.new_name||newName);
    let item=CATALOG.find(x=>x.MaDe===DBT_MERGE_MADE)||scope||{};
    renderDbtMergeModal(item);
    await refreshAdminCatalogLive(scope||item);
    if(st)st.textContent='✅ Đã gộp '+(j.updated||0)+' câu → «'+(j.new_name||newName)+'». Mục lục đã nhảy tới thẻ Bài.';
    alert('Đã gộp '+(j.updated||0)+' câu thành: '+(j.new_name||newName)+'\n\nMục lục sách đã cập nhật — xem thẻ Bài được tô xanh.');
  }catch(e){if(st)st.textContent='❌ '+e.message;alert('Không gộp được: '+(e.message||e))}
}

let CHAPTER_DBT_BOARD={mon:'',khoi:'',chuong:'',lessons:[]};
function ensureChapterDbtClickBindings(){
  if(window.__CHAPTER_DBT_CLICK_BOUND)return;
  window.__CHAPTER_DBT_CLICK_BOUND=true;
  document.addEventListener('click',function(e){
    let chBtn=e.target.closest('.bookChapterDbtBtn');
    if(chBtn){
      e.preventDefault();
      openChapterDbtBoard(chBtn.getAttribute('data-mon')||'',chBtn.getAttribute('data-khoi')||'',chBtn.getAttribute('data-chuong')||'');
      return;
    }
    let gptBtn=e.target.closest('.chapterDbtGptBtn');
    if(gptBtn){
      e.preventDefault();
      chapterDbtOpenLessonGpt(gptBtn.getAttribute('data-made')||'');
    }
  });
}
function closeChapterDbtBoard(){let m=document.getElementById('chapterDbtModal');if(m)m.classList.add('hide')}
function chapterDbtLessonPack(entries){
  entries=entries||[];
  let mp={};
  function add(name,cnt){
    name=String(name||'').trim();
    if(!name||name===DBT_UNCLASSIFIED||adminDbtIsBadValue(name))return;
    let k=normText(name);
    if(!mp[k])mp[k]={name:name,count:0,variants:{}};
    mp[k].count+=(parseInt(cnt,10)||0);
    mp[k].variants[name]=(mp[k].variants[name]||0)+(parseInt(cnt,10)||0);
    if(String(name).length>String(mp[k].name).length)mp[k].name=name;
  }
  for(let x of entries){
    try{for(let [n,c] of catalogDbtCounts(x))add(n,c)}catch(e){}
    for(let part of String(x.DangBaiTap||'').split(/[,;|]+/))add(part.trim(),0);
    for(let n of getDbtOrderList(x.MaDe,x))add(n,0);
  }
  let merged=v246MergeDbtCounts(entries);
  let uncls=merged.unclassified||0;
  let primary=entries[0]||{};
  let ord=[];
  let seenOrd=new Set();
  for(let x of entries){
    for(let n of getDbtOrderList(x.MaDe,x)){
      let k=normText(n);
      if(!seenOrd.has(k)){seenOrd.add(k);ord.push(n)}
    }
  }
  for(let [name,cnt] of (merged.pairs||[]))add(name,cnt);
  let names=[];
  let seen={};
  for(let n of ord){
    let k=normText(n);
    if(mp[k]&&!seen[k]){seen[k]=1;names.push(mp[k].name)}
  }
  for(let k of Object.keys(mp)){
    if(!seen[k]){seen[k]=1;names.push(mp[k].name)}
  }
  if(!names.length){
    names=(merged.pairs||[]).map(x=>String(x[0]||'').trim()).filter(Boolean);
  }
  let counts={};
  for(let k of Object.keys(mp))counts[k]=mp[k].count;
  let variants={};
  for(let k of Object.keys(mp))variants[k]=Object.keys(mp[k].variants||{});
  return {
    names,
    counts,
    variants,
    unclassified:uncls,
    soCau:entries.reduce((a,x)=>a+(parseInt(x.SoCau,10)||0),0),
  };
}
function chapterDbtLessonNames(entries,made){
  return chapterDbtLessonPack(entries);
}
function chapterDbtBuildLessons(mon,khoi,chuong){
  let list=(CATALOG||[]).filter(x=>x.Mon===mon&&String(deriveKhoi(x.Lop)||'')===String(khoi||'')&&x.Chuong===chuong);
  let byBai=v246GroupBy(list,x=>x.BaiHoc||x.De||'Chưa rõ bài');
  let lessons=[];
  for(let [bai,entries] of byBai){
    let primary=entries[0]||{};
    let made=String(primary.MaDe||'').trim();
    let pack=chapterDbtLessonPack(entries);
    lessons.push({made,baiHoc:bai,entries,mades:[...new Set((entries||[]).map(x=>String(x.MaDe||'').trim()).filter(Boolean))],soCau:pack.soCau,unclassified:pack.unclassified,names:pack.names.slice(),counts:pack.counts,variants:pack.variants,picks:{}});
  }
  lessons.sort((a,b)=>String(a.baiHoc).localeCompare(String(b.baiHoc),'vi'));
  return lessons;
}
function chapterDbtAllNames(lessons){
  let out=[];(lessons||[]).forEach(L=>{(L.names||[]).forEach(n=>out.push(n))});return out;
}
function chapterDbtMoveSelectHtml(li,kind,ni){
  let lessons=CHAPTER_DBT_BOARD.lessons||[];
  let opts=lessons.filter((_,i)=>i!==li).map(L=>{
    let b=String(L.baiHoc||'').trim();
    if(!b)return '';
    return `<option value="${escAttr(b)}">${esc(shortText(b,34))}</option>`;
  }).filter(Boolean).join('');
  if(!opts)return '';
  let onchg=kind==='uncls'?`chapterDbtMoveUnclassified(${li},this)`:`chapterDbtMoveToLesson(${li},${ni},this)`;
  return `<select class="chapterDbtMoveSel" onchange="${onchg};this.selectedIndex=0" title="Chuyển sang bài khác (cột Bài học)"><option value="">→ Bài</option>${opts}</select>`;
}
function openChapterDbtBoard(mon,khoi,chuong){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  mon=String(mon||'').trim();khoi=String(khoi||'').trim();chuong=String(chuong||'').trim();
  if(!chuong){alert('Chưa xác định chương.');return}
  CHAPTER_DBT_BOARD={mon,khoi,chuong,lessons:chapterDbtBuildLessons(mon,khoi,chuong)};
  renderChapterDbtBoard();
  document.getElementById('chapterDbtModal').classList.remove('hide');
}
function renderChapterDbtBoard(){
  let scope=document.getElementById('chapterDbtScope');
  if(scope)scope.innerHTML='<span class="cdbtScopeTag">'+esc(CHAPTER_DBT_BOARD.mon)+'</span><span class="cdbtScopeTag">Khối '+esc(CHAPTER_DBT_BOARD.khoi)+'</span><span class="cdbtScopeTag">'+esc(CHAPTER_DBT_BOARD.chuong)+'</span><span class="cdbtScopeTag muted">'+CHAPTER_DBT_BOARD.lessons.length+' bài</span>';
  let sug=document.getElementById('chapterDbtSuggest');
  if(sug){
    let groups=dbtSuggestMergeGroups(chapterDbtAllNames(CHAPTER_DBT_BOARD.lessons));
    if(!groups.length){sug.classList.add('hide');sug.innerHTML=''}
    else{sug.classList.remove('hide');sug.innerHTML='<b>💡 Tên gần giống trong chương:</b> '+groups.slice(0,6).map(g=>`<span class="cdbtSugTag">${esc(g.slice(0,3).join(' · '))}${g.length>3?'…':''}</span>`).join('')+'<span class="muted" style="font-size:11px"> — tick & gộp trong từng bài bên dưới.</span>'}
  }
  let body=document.getElementById('chapterDbtBody');
  if(!body)return;
  if(!CHAPTER_DBT_BOARD.lessons.length){body.innerHTML='<div class="muted cdbtEmpty">Không có bài nào trong chương này.</div>';return}
  body.innerHTML=CHAPTER_DBT_BOARD.lessons.map((L,li)=>{
    let rows=(L.names||[]).map((name,ni)=>{
      let nk=normText(name);
      let cnt=L.counts[normText(name)]||0;
      let alts=(L.variants&&L.variants[nk]||[]).filter(v=>normText(v)!==nk);
      let altNote=alts.length>1?`<span class="cdbtAltNote">${alts.length} tên biến thể</span>`:'';
      let picked=!!(L.picks&&L.picks[nk]);
      let rowMove=chapterDbtMoveSelectHtml(li,'name',ni);
      return `<div class="cdbtDangRow" draggable="true"
        data-li="${li}" data-ni="${ni}"
        ondragstart="cdbtDragStart(event,${li},${ni})"
        ondragover="cdbtDragOver(event)"
        ondrop="cdbtDrop(event,${li},${ni})"
        ondragend="cdbtDragEnd(event)">
        <span class="cdbtDragHandle" title="Kéo để sắp xếp">⠿</span>
        <span class="cdbtDangNum">${ni+1}</span>
        <label class="cdbtDangLabel">
          <input type="checkbox" ${picked?'checked':''} onchange="chapterDbtTogglePick(${li},${ni},this.checked)">
          <span class="cdbtDangName">${esc(oneLineText(name))}</span>
          ${cnt?`<span class="cdbtDangCount">${cnt} câu</span>`:''}
          ${altNote}
        </label>
        <span class="cdbtDangTools">
          ${rowMove}
          <button type="button" class="cdbtMoveBtn cdbtAiGenBtn" data-mon="${escAttr(CHAPTER_DBT_BOARD.mon||'')}" data-lop="${escAttr(CHAPTER_DBT_BOARD.khoi||'')}" data-chuong="${escAttr(CHAPTER_DBT_BOARD.chuong||'')}" data-bai="${escAttr(L.baiHoc||'')}" data-dbt="${escAttr(name||'')}" onclick="event.stopPropagation();openAdminAiGenFromEl(this)" title="ADMIN: Tạo thêm câu AI (Gemini/Claude) cho dạng này">🤖</button>
          <button type="button" class="cdbtMoveBtn" onclick="chapterDbtMove(${li},${ni},-1)" ${ni===0?'disabled':''} title="Lên">↑</button>
          <button type="button" class="cdbtMoveBtn" onclick="chapterDbtMove(${li},${ni},1)" ${ni===L.names.length-1?'disabled':''} title="Xuống">↓</button>
        </span>
      </div>`;
    }).join('');
    let unclsRow='';
    if(L.unclassified>0){
      let unMove=chapterDbtMoveSelectHtml(li,'uncls',0);
      unclsRow=`<div class="cdbtDangRow cdbtUnclsRow"><span class="cdbtDragHandle" style="opacity:.3">⠿</span><span class="cdbtDangNum">?</span><span class="cdbtDangLabel"><span class="cdbtDangName">❓ Chưa phân loại</span><span class="cdbtDangCount" style="background:#fde68a;color:#92400e">${L.unclassified} câu</span></span><span class="cdbtDangTools">${unMove}</span></div>`;
    }
    let hasPicks=L.picks&&Object.keys(L.picks).length>0;
    let uncls=L.unclassified?`<span class="cdbtUnclsBadge">❗${L.unclassified} chưa PL</span>`:'';
    return `<div class="cdbtLesson" id="cdbtLesson_${li}">
      <div class="cdbtLessonHead">
        <div class="cdbtLessonInfo">
          <span class="cdbtLessonNum">${li+1}</span>
          <div>
            <div class="cdbtLessonName">${esc(L.baiHoc)}</div>
            <div class="cdbtLessonMeta">${L.soCau||0} câu · ${(L.names||[]).length} dạng ${uncls}</div>
          </div>
        </div>
        <div class="cdbtLessonTools">
          <button type="button" class="cdbtToolBtn cdbtToolBtnGpt chapterDbtGptBtn" data-made="${escAttr(L.made)}" title="AI gợi ý dạng BT cho bài này">🤖 AI gợi ý</button>
          <button type="button" class="cdbtToolBtn" onclick="chapterDbtSaveLessonOrder(${li})" title="Lưu thứ tự dạng BT">💾 Lưu thứ tự</button>
          <button type="button" class="cdbtToolBtn cdbtToolBtnOpen" onclick="openStartModal('${String(L.made||'').replace(/'/g,"\\'")}','')" title="Mở đề làm bài">📂 Mở đề</button>
        </div>
      </div>
      <div class="cdbtRows" id="cdbtRows_${li}">${rows}${unclsRow||''}${!rows&&!unclsRow?'<div class="cdbtEmpty">Chưa có dạng BT — bấm 🤖 AI gợi ý</div>':''}</div>
      <div class="cdbtMergeBar ${hasPicks?'cdbtMergeActive':''}">
        <span class="cdbtMergeLabel">✂️ Gộp/đổi tên tick:</span>
        <input type="text" class="cdbtMergeInput" id="chapterDbtMergeName_${li}" placeholder="Tên mới sau khi gộp..." oninput="chapterDbtMergePreview(${li})">
        <button type="button" class="cdbtToolBtn" onclick="chapterDbtPickLongest(${li})" title="Dùng tên dài nhất">📏 Tên dài nhất</button>
        <button type="button" class="cdbtToolBtn cdbtToolBtnSave" onclick="chapterDbtApplyMerge(${li})">💾 Gộp & lưu</button>
        <span class="muted" id="chapterDbtMergeHint_${li}" style="font-size:11px"></span>
      </div>
    </div>`;
  }).join('');
  let st=document.getElementById('chapterDbtStatus');if(st)st.innerHTML='<span class="muted" style="font-size:12px">⠿ Kéo thả để sắp xếp dạng BT · ↑↓ di chuyển · «→ Bài» chuyển sang bài khác · tick ≥2 để gộp</span>';
  // Khởi tạo drag-drop
  cdbtInitDragDrop();
}

// ── Drag & Drop cho chapterDbt ────────────────────────────────────────────
let _cdbtDrag={li:-1,ni:-1,el:null};
function cdbtDragStart(e,li,ni){
  _cdbtDrag={li,ni,el:e.currentTarget};
  e.currentTarget.classList.add('cdbtDragging');
  e.dataTransfer.effectAllowed='move';
  e.dataTransfer.setData('text/plain',li+','+ni);
}
function cdbtDragOver(e){
  e.preventDefault();
  e.dataTransfer.dropEffect='move';
  let row=e.currentTarget;
  if(row===_cdbtDrag.el)return;
  row.classList.add('cdbtDragOver');
}
function cdbtDrop(e,li,ni){
  e.preventDefault();
  document.querySelectorAll('.cdbtDragOver').forEach(x=>x.classList.remove('cdbtDragOver'));
  if(_cdbtDrag.li<0||_cdbtDrag.li!==li)return; // chỉ kéo trong cùng bài
  let from=_cdbtDrag.ni,to=ni;
  if(from===to)return;
  let L=CHAPTER_DBT_BOARD.lessons[li];if(!L||!L.names)return;
  let item=L.names.splice(from,1)[0];
  L.names.splice(to,0,item);
  renderChapterDbtBoard();
}
function cdbtDragEnd(e){
  document.querySelectorAll('.cdbtDragging,.cdbtDragOver').forEach(x=>{x.classList.remove('cdbtDragging');x.classList.remove('cdbtDragOver')});
  _cdbtDrag={li:-1,ni:-1,el:null};
}
function cdbtInitDragDrop(){
  document.querySelectorAll('.cdbtDangRow[draggable]').forEach(row=>{
    row.addEventListener('dragenter',e=>{e.preventDefault();row.classList.add('cdbtDragOver')});
    row.addEventListener('dragleave',e=>{if(!row.contains(e.relatedTarget))row.classList.remove('cdbtDragOver')});
  });
}
function chapterDbtTogglePick(li,ni,on){
  let L=CHAPTER_DBT_BOARD.lessons[li];if(!L||!L.names[ni])return;
  if(!L.picks)L.picks={};
  let name=L.names[ni];
  let k=normText(name);
  if(on)L.picks[k]=name;else delete L.picks[k];
  chapterDbtMergePreview(li);
}
function chapterDbtPickedNames(li){
  let L=CHAPTER_DBT_BOARD.lessons[li];if(!L||!L.picks)return [];
  let out=[];
  for(let name of (L.names||[])){
    let k=normText(name);
    if(L.picks[k]){
      let vars=(L.variants&&L.variants[k])||[];
      for(let v of vars)if(v&&!out.includes(v))out.push(v);
      if(!out.includes(L.picks[k]))out.push(L.picks[k]);
    }
  }
  return out;
}
function chapterDbtMove(li,ni,dir){
  let L=CHAPTER_DBT_BOARD.lessons[li];if(!L||!L.names)return;
  let j=ni+(parseInt(dir,10)||0);if(j<0||j>=L.names.length)return;
  let t=L.names[ni];L.names[ni]=L.names[j];L.names[j]=t;
  renderChapterDbtBoard();
}
async function chapterDbtMoveToLesson(li,ni,selEl){
  let targetBai=String(selEl&&selEl.value||'').trim();
  if(!targetBai)return;
  let L=CHAPTER_DBT_BOARD.lessons[li];if(!L||!L.names[ni])return;
  await chapterDbtDoMoveLesson(li,{dangName:L.names[ni],unclassified:false},targetBai);
}
async function chapterDbtMoveUnclassified(li,selEl){
  let targetBai=String(selEl&&selEl.value||'').trim();
  if(!targetBai)return;
  await chapterDbtDoMoveLesson(li,{unclassified:true},targetBai);
}
async function chapterDbtDoMoveLesson(li,payload,targetBai){
  let L=CHAPTER_DBT_BOARD.lessons[li];if(!L)return;
  let fromBai=L.baiHoc;
  let dangNames=[];
  if(payload.unclassified){
    if(!confirm('Chuyển '+L.unclassified+' câu chưa phân loại\nTừ: «'+fromBai+'»\nSang: «'+targetBai+'»?\n\nGhi cột Bài học trên Google Sheet.'))return;
  }else{
    let name=payload.dangName;
    let cnt=L.counts[normText(name)]||0;
    let vars=(L.variants&&L.variants[normText(name)])||[];
    dangNames=vars.length?vars.slice():[name];
    if(!confirm('Chuyển dạng «'+name+'» ('+cnt+' câu)\nTừ: «'+fromBai+'»\nSang: «'+targetBai+'»?\n\nGhi cột Bài học trên Google Sheet.'))return;
  }
  let st=document.getElementById('chapterDbtStatus');
  try{
    if(st)st.textContent='⏳ Chuyển sang «'+targetBai+'»…';
    let body={
      mon:CHAPTER_DBT_BOARD.mon,
      chuong:CHAPTER_DBT_BOARD.chuong,
      khoi:CHAPTER_DBT_BOARD.khoi,
      from_bai_hoc:fromBai,
      to_bai_hoc:targetBai,
      unclassified:!!payload.unclassified,
      dangbaitap_names:payload.unclassified?[]:dangNames
    };
    let j=await api('/api/admin/chapter-dbt-move-lesson',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    CHAPTER_DBT_BOARD.lessons=chapterDbtBuildLessons(CHAPTER_DBT_BOARD.mon,CHAPTER_DBT_BOARD.khoi,CHAPTER_DBT_BOARD.chuong);
    await refreshAdminCatalogLive({Mon:CHAPTER_DBT_BOARD.mon,Chuong:CHAPTER_DBT_BOARD.chuong,BaiHoc:''});
    renderChapterDbtBoard();
    if(st)st.textContent='✅ Đã chuyển '+(parseInt(j.updated||0,10)||0)+' câu → «'+targetBai+'».';
  }catch(e){if(st)st.textContent='❌ '+(e.message||e);alert('Không chuyển được: '+(e.message||e))}
}
function chapterDbtMergePreview(li){
  let el=document.getElementById('chapterDbtMergeHint_'+li);if(!el)return;
  let sel=chapterDbtPickedNames(li);
  if(!sel.length){el.textContent='Tick tên cần gộp/đổi.';return}
  el.textContent=sel.length===1?('Đổi tên «'+sel[0]+'» → tên mới'):('Gộp '+sel.length+' tên → tên mới');
}
function chapterDbtPickLongest(li){
  let sel=chapterDbtPickedNames(li);
  if(!sel.length)sel=(CHAPTER_DBT_BOARD.lessons[li]||{}).names||[];
  sel=sel.slice().sort((a,b)=>String(b).length-String(a).length);
  let inp=document.getElementById('chapterDbtMergeName_'+li);if(inp&&sel[0])inp.value=sel[0];
  chapterDbtMergePreview(li);
}
async function chapterDbtSaveLessonOrder(li){
  let L=CHAPTER_DBT_BOARD.lessons[li];if(!L)return;
  let mades=(L.mades&&L.mades.length)?L.mades:[L.made].filter(Boolean);
  let st=document.getElementById('chapterDbtStatus');
  try{
    if(st)st.textContent='⏳ Lưu thứ tự «'+L.baiHoc+'»…';
    for(let made of mades){
      await api('/api/admin/dbt-order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({made,order:L.names})});
      patchCatalogDbtOrderLocal(made,L.names);
    }
    if(st)st.textContent='✅ Đã lưu thứ tự dạng — '+L.baiHoc;
  }catch(e){if(st)st.textContent='❌ '+(e.message||e);alert('Không lưu thứ tự: '+(e.message||e))}
}
async function chapterDbtSaveAllOrders(){
  let st=document.getElementById('chapterDbtStatus');
  try{
    for(let i=0;i<CHAPTER_DBT_BOARD.lessons.length;i++)await chapterDbtSaveLessonOrder(i);
    await refreshAdminCatalogLive({Mon:CHAPTER_DBT_BOARD.mon,Chuong:CHAPTER_DBT_BOARD.chuong,BaiHoc:''});
    if(st)st.textContent='✅ Đã lưu thứ tự tất cả bài trong chương.';
    renderChapterDbtBoard();
  }catch(e){}
}
async function chapterDbtApplyMerge(li){
  let L=CHAPTER_DBT_BOARD.lessons[li];if(!L)return;
  let mades=(L.mades&&L.mades.length)?L.mades:[L.made].filter(Boolean);
  if(!mades.length)return;
  let sel=chapterDbtPickedNames(li);
  if(!sel.length){alert('Tick ít nhất 1 tên dạng.');return}
  let newName=String((document.getElementById('chapterDbtMergeName_'+li)||{}).value||'').trim();
  if(!newName){alert('Gõ tên mới thống nhất.');return}
  if(adminDbtIsBadValue(newName)){alert('Tên mới không hợp lệ.');return}
  if(sel.length===1&&normText(sel[0])===normText(newName)){alert('Tên mới trùng tên cũ.');return}
  if(!confirm((sel.length===1?'Đổi tên «'+sel[0]+'»':'Gộp '+sel.length+' tên')+' → «'+newName+'»?\n\nGhi cột H cho mọi câu trong bài «'+L.baiHoc+'».'))return;
  let st=document.getElementById('chapterDbtStatus');
  try{
    if(st)st.textContent='⏳ Đang gộp & ghi Sheet…';
    let total=0;
    for(let made of mades){
      let j=await api('/api/admin/merge-dangbaitap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({made,old_names:sel,new_name:newName})});
      patchCatalogDbtMergeLocal(made,sel,j.new_name||newName);
      total+=parseInt(j.updated||0,10)||0;
    }
    CHAPTER_DBT_BOARD.lessons=chapterDbtBuildLessons(CHAPTER_DBT_BOARD.mon,CHAPTER_DBT_BOARD.khoi,CHAPTER_DBT_BOARD.chuong);
    await refreshAdminCatalogLive({Mon:CHAPTER_DBT_BOARD.mon,Chuong:CHAPTER_DBT_BOARD.chuong,BaiHoc:L.baiHoc});
    renderChapterDbtBoard();
    if(st)st.textContent='✅ Đã cập nhật '+total+' câu → «'+newName+'».';
  }catch(e){if(st)st.textContent='❌ '+(e.message||e);alert('Không gộp được: '+(e.message||e))}
}
async function chapterDbtOpenLessonGpt(made){
  if(!USER.is_admin||!made)return;
  closeChapterDbtBoard();
  try{
    await startQuiz(String(made),false,false,'','',true,'');
    setTimeout(()=>{try{openBulkDbtReview()}catch(e){}},500);
  }catch(e){alert('Không mở được đề: '+(e.message||e))}
}

function adminDbtScopeFromForm(q){q=q||readQuestionFormData()||{};return{mon:String(q.Mon||'').trim(),lop:String(q.Lop||'').trim(),chuong:String(q.Chuong||'').trim(),bai:String(q.BaiHoc||'').trim()}}
function adminDbtIsBadValue(v){let t=normText(v);if(!t)return true;if(t.includes('chua gan')||t.includes('chua phan loai')||t.includes('chua co'))return true;return['chua','none','null','khac','khong ro','trac nghiem','dung sai','tra loi ngan','tu luan','tn','ds','tln','tl'].includes(t)}
function adminDbtScopeMatches(item,scope,level){if(scope.mon&&normText(item.Mon||'')!==normText(scope.mon))return false;if(level==='mon')return true;if(scope.chuong&&normText(item.Chuong||'')!==normText(scope.chuong))return false;if(level==='chuong')return true;if(scope.bai&&normText(item.BaiHoc||'')!==normText(scope.bai))return false;return true}
function adminDbtScopeLabel(scope,level){scope=scope||{};let parts=[];if(scope.mon)parts.push(scope.mon);if(scope.chuong)parts.push(shortText(scope.chuong,40));if(scope.bai)parts.push(shortText(scope.bai,40));if(!parts.length)return'Chọn Môn / Chương / Bài học ở trên để gợi ý dạng chính xác.';let lvl=level==='bai'?'đúng bài này':(level==='chuong'?'cùng chương':(level==='mon'?'cùng môn':'—'));return'📍 Gợi ý theo '+parts.join(' · ')+' ('+lvl+')'}
function adminDangBaiTapOptions(q){let scope=adminDbtScopeFromForm(q);let curVal=String((q&&q.DangBaiTap)||'').trim();let seen={},counts={};function bump(v,n){v=String(v||'').trim();if(!v||adminDbtIsBadValue(v))return;let k=normText(v);counts[k]=(counts[k]||0)+(n||1);if(!seen[k]){seen[k]=v}}function collectItem(item,level){if(!adminDbtScopeMatches(item,scope,level))return;let fc=(item.FilterCounts||{}).dangbaitap||{};if(fc&&typeof fc==='object'&&!Array.isArray(fc)){for(let [k,c] of Object.entries(fc))bump(k,parseInt(c,10)||1)}let raw=String(item.DangBaiTap||'');if(raw)for(let part of raw.split(/[,;|]+/))bump(part.trim(),1)}let level='none';for(let c of (CATALOG||[]))collectItem(c,'bai');if(Object.keys(seen).length){level='bai'}else if(scope.chuong){for(let c of (CATALOG||[]))collectItem(c,'chuong');if(Object.keys(seen).length)level='chuong'}if(!Object.keys(seen).length&&scope.mon){for(let c of (CATALOG||[]))collectItem(c,'mon');if(Object.keys(seen).length)level='mon'}for(let qq of (QUESTIONS||[])){if(adminDbtScopeMatches(qq,scope,'bai'))bump(qq.DangBaiTap,1);else if(scope.chuong&&adminDbtScopeMatches(qq,scope,'chuong'))bump(qq.DangBaiTap,1);else if(scope.mon&&adminDbtScopeMatches(qq,scope,'mon'))bump(qq.DangBaiTap,1)}if(curVal&&!seen[normText(curVal)])bump(curVal,0);let opts=Object.values(seen).sort((a,b)=>{let ca=counts[normText(a)]||0,cb=counts[normText(b)]||0;if(cb!==ca)return cb-ca;return a.localeCompare(b,'vi')});if(level==='bai')opts=opts.slice(0,DBT_MAX_PER_LESSON);return{opts,scopeLabel:adminDbtScopeLabel(scope,level),scopeLevel:level}}
function adminDangBaiTapSuggestions(){try{let pack=adminDangBaiTapOptions(readQuestionFormData());return(pack.opts||[]).slice(0,pack.scopeLevel==='bai'?DBT_MAX_PER_LESSON:50)}catch(e){return []}}
function adminDangBaiTapSuggestionsForQuestion(q){try{let pack=adminDangBaiTapOptions(q||{});return(pack.opts||[]).slice(0,pack.scopeLevel==='bai'?DBT_MAX_PER_LESSON:50)}catch(e){return []}}
function adminDbtAiSyncNote(j){j=j||{};let dbt=String(j.DangBaiTap||'').trim();let raw=String(j.ai_raw||'').trim();if(j.matched_existing&&raw&&raw!==dbt)return '<br><span class="muted">🔗 Đồng bộ về dạng có sẵn: <b>'+esc(dbt)+'</b>'+(raw!==dbt?' (GPT gợi ý: '+esc(raw)+')':'')+'</span>';if(!j.matched_existing&&dbt)return '<br><span class="muted">🆕 Dạng mới — chưa có trong danh sách phạm vi này.</span>';return ''}
function adminDbtFindMatch(val,opts){val=String(val||'').trim();if(!val)return null;for(let x of opts||[]){if(normText(x)===normText(val))return x}return null}
function adminDbtCheckDuplicateHint(){let inp=document.getElementById('edit_DangBaiTap');let hint=document.getElementById('edit_DangBaiTap_dup');if(!inp||!hint)return;let raw=String(inp.value||'').trim();if(!raw){hint.textContent='';hint.classList.add('hide');return}let sel=document.getElementById('edit_DangBaiTap_pick');let near='';if(sel){for(let i=0;i<sel.options.length;i++){let v=sel.options[i].value;if(!v||v==='__custom__'||normText(v)===normText(raw))continue;if(normText(v).includes(normText(raw))||normText(raw).includes(normText(v))){near=v;break}}}if(near){hint.innerHTML='⚠ Có thể trùng với «'+esc(near)+'» — nên chọn dạng có sẵn.';hint.classList.remove('hide')}else{hint.textContent='';hint.classList.add('hide')}}
function adminDbtPickChange(){let sel=document.getElementById('edit_DangBaiTap_pick');let inp=document.getElementById('edit_DangBaiTap');let note=document.getElementById('edit_DangBaiTap_hint');if(!sel||!inp)return;let v=String(sel.value||'');if(v==='__custom__'){inp.classList.remove('hide');inp.focus();if(note)note.textContent='Gõ tên dạng mới — tránh trùng hoặc gần giống tên đã có.';adminDbtCheckDuplicateHint();return}if(v){inp.value=v;inp.classList.add('hide');if(note)note.textContent='Đã chọn dạng có sẵn — tên thống nhất, không trùng.'}else{inp.value='';inp.classList.remove('hide');if(note)note.textContent='Chọn dạng có sẵn hoặc gõ mới bên dưới.'}adminDbtCheckDuplicateHint()}
function adminDbtInputChange(){let inp=document.getElementById('edit_DangBaiTap');let sel=document.getElementById('edit_DangBaiTap_pick');if(!inp||!sel)return;let opts=[];for(let i=0;i<sel.options.length;i++){let v=sel.options[i].value;if(v&&v!=='__custom__')opts.push(v)}let m=adminDbtFindMatch(inp.value,opts);if(m&&normText(inp.value)===normText(m)){sel.value=m;inp.classList.add('hide')}else if(String(inp.value||'').trim()){sel.value='__custom__';inp.classList.remove('hide')}else{sel.value='';inp.classList.remove('hide')}adminDbtCheckDuplicateHint()}
function adminDbtSyncSelectFromInput(){adminDbtRefreshFromScope()}
function adminDbtRebuildSelect(pack,cur){let opts=(pack&&pack.opts)||[];let match=adminDbtFindMatch(cur,opts);let pickVal=match||(cur?'__custom__':'');let optHtml='<option value="">— Chọn dạng có sẵn —</option>';for(let v of opts){let selOn=(pickVal===v)?' selected':'';optHtml+=`<option value="${escAttr(v)}"${selOn}>${esc(v)}</option>`}optHtml+=`<option value="__custom__"${pickVal==='__custom__'?' selected':''}>✏️ Nhập / sửa dạng khác…</option>`;return{optHtml,match,pickVal,opts}}
function adminDbtRefreshFromScope(){let sel=document.getElementById('edit_DangBaiTap_pick');if(!sel)return;let inp=document.getElementById('edit_DangBaiTap');let cur=inp?String(inp.value||'').trim():'';let pack=adminDangBaiTapOptions(Object.assign({},readQuestionFormData(),{DangBaiTap:cur}));let built=adminDbtRebuildSelect(pack,cur);sel.innerHTML=built.optHtml;if(built.match){sel.value=built.match;if(inp){inp.value=built.match;inp.classList.add('hide')}}else if(cur){sel.value='__custom__';if(inp)inp.classList.remove('hide')}else{sel.value='';if(inp)inp.classList.remove('hide')}let scopeEl=document.getElementById('edit_DangBaiTap_scope');if(scopeEl)scopeEl.textContent=pack.scopeLabel||'';let hint=document.getElementById('edit_DangBaiTap_hint');if(hint){if(!pack.opts||!pack.opts.length)hint.textContent='Chưa có dạng trong phạm vi này — gõ tên mới hoặc điền đủ Chương/Bài.';else if(built.match)hint.textContent='Đã chọn dạng có sẵn — tên thống nhất.';else hint.textContent='Chọn trong danh sách hoặc gõ tên mới.'}adminDbtCheckDuplicateHint()}
function renderAdminDangBaiTapField(q){let raw=String((q&&q.DangBaiTap)||'').trim();let pack=adminDangBaiTapOptions(q);let built=adminDbtRebuildSelect(pack,raw);let hideInp=(built.pickVal&&built.pickVal!=='__custom__')?' hide':'';let hintTxt=!pack.opts||!pack.opts.length?'Chưa có dạng trong phạm vi — gõ tên mới hoặc điền Chương/Bài.':(built.match?'Đã chọn dạng có sẵn — tên thống nhất.':'Chọn trong danh sách hoặc gõ tên mới.');return `<div class="adminQuickField adminDbtField"><label><b>${QUESTION_FORM_LABELS.DangBaiTap}</b></label><div id="edit_DangBaiTap_scope" class="adminDbtScope">${esc(pack.scopeLabel||'')}</div><select id="edit_DangBaiTap_pick" class="adminDbtSelect" onchange="adminDbtPickChange()">${built.optHtml}</select><input type="text" id="edit_DangBaiTap" class="adminDbtInput${hideInp}" value="${escAttr(raw)}" placeholder="Gõ dạng bài tập mới (tránh trùng tên gần giống)" oninput="adminDbtInputChange()" /><div id="edit_DangBaiTap_hint" class="muted adminDbtHint">${hintTxt}</div><div id="edit_DangBaiTap_dup" class="adminDbtDup hide"></div></div>`}
async function aiDetectCurrentQuestionDangBaiTap(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(QUESTION_SAVE_BUSY){return}
  let btn=document.getElementById('btnAiDetectDangBaiTap');
  let oldBtn=btn?btn.textContent:'';
  let note=document.getElementById('editModalNote');
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳ GPT nhận Dạng BT...'}
    let q=readQuestionFormData();
    q.Dang=normDangFormVal(q.Dang||'');
    let j=await adminApiPost('/api/ai/detect-dangbaitap-update',{question:q,dangbaitap_suggestions:adminDangBaiTapSuggestions(),save:false});
    let dbt=String(j.DangBaiTap||'').trim();
    if(!dbt){throw new Error(j.error||'GPT chưa trả Dạng bài tập hợp lệ')}
    let el=document.getElementById('edit_DangBaiTap');
    if(el)el.value=dbt;
    adminDbtSyncSelectFromInput();
    let conf=String(j.confidence||'').trim();
    let reason=String(j.reason||'').trim();
    if(note){
      note.innerHTML='🏷️ GPT ADMIN gợi ý Dạng bài tập: <b>'+esc(dbt)+'</b>'+(reason?'<br><span class="muted">Lý do: '+esc(reason)+'</span>':'')+adminDbtAiSyncNote(j)+'<br><b>Chưa lưu Sheet.</b> Kiểm tra rồi bấm <b>Lưu vào Google Sheet</b>.';
    }
  }catch(e){
    alert('AI chưa nhận Dạng bài tập: '+e.message);
    if(note)note.textContent='AI nhận Dạng bài tập lỗi hoặc thiếu OPENAI_API_KEY. Có thể gõ tay cột H rồi lưu.';
  }finally{
    if(btn){btn.disabled=false;btn.textContent=oldBtn||'🏷️ AI gợi ý Dạng bài tập'}
  }
}
async function aiDetectAndSaveCurrentQuestionDangBaiTap(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(QUESTION_SAVE_BUSY){return}
  if(QUESTION_MODAL_MODE==='add'){
    alert('Câu mới chưa có dòng Sheet. Hãy thêm câu trước, rồi mới AI nhận & lưu Dạng bài tập.');
    return;
  }
  let q0=QUESTIONS[CUR]||{};
  if(!q0._row){alert('Không xác định dòng Sheet của câu này.');return}
  let btn=document.getElementById('btnAiDetectSaveDangBaiTap');
  let btn2=document.getElementById('btnAiDetectDangBaiTap');
  let oldBtn=btn?btn.textContent:'';
  let note=document.getElementById('editModalNote');
  try{
    QUESTION_SAVE_BUSY=true;
    if(btn){btn.disabled=true;btn.textContent='⏳ GPT nhận & lưu H...'}
    if(btn2){btn2.disabled=true}
    let q=readQuestionFormData();
    q.Dang=normDangFormVal(q.Dang||'');
    let j=await adminApiPost('/api/ai/detect-dangbaitap-update',{row:q0._row,id:q0.ID||'',question:q,dangbaitap_suggestions:adminDangBaiTapSuggestions()});
    let dbt=String(j.DangBaiTap||'').trim();
    if(!dbt){throw new Error(j.error||'GPT chưa trả Dạng bài tập hợp lệ')}
    let el=document.getElementById('edit_DangBaiTap');
    if(el)el.value=dbt;
    adminDbtSyncSelectFromInput();
    q0.DangBaiTap=dbt;
    LEARNING_CACHE={};
    let reason=String(j.reason||'').trim();
    if(note){
      note.innerHTML='✅ Đã lưu Dạng bài tập <b>'+esc(dbt)+'</b> vào Google Sheet dòng <b>'+esc(j.row||q0._row)+'</b> (cột H).'+adminDbtAiSyncNote(j)+(reason?'<br><span class="muted">Lý do: '+esc(reason)+'</span>':'')+'<br><span class="muted">Chỉ cập nhật cột H. Các ô khác chưa bị thay đổi.</span>';
    }
    renderNav();
  }catch(e){
    alert('Không nhận & lưu Dạng bài tập: '+e.message);
    if(note)note.textContent='AI nhận/lưu Dạng bài tập lỗi. Có thể gõ tay cột H rồi bấm Lưu.';
  }finally{
    QUESTION_SAVE_BUSY=false;
    if(btn){btn.disabled=false;btn.textContent=oldBtn||'✅ AI Dạng BT &amp; lưu H'}
    if(btn2){btn2.disabled=false}
  }
}

function adminApplyMucDoChip(lv){
  lv=normMucDoFormVal(lv||'');
  if(!lv)return false;
  setAdminChip('MucDo',lv);
  return true;
}
async function aiDetectCurrentQuestionLevel(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(QUESTION_SAVE_BUSY)return;
  let btn=document.getElementById('btnAiDetectLevel');
  let oldBtn=btn?btn.textContent:'';
  let note=document.getElementById('editModalNote');
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳ GPT nhận mức độ...'}
    let q=readQuestionFormData();
    q.Dang=normDangFormVal(q.Dang||'');
    let j=await adminApiPost('/api/ai/detect-level',{question:q});
    let lv=normMucDoFormVal(j.MucDo||j.ai_mucdo||'');
    if(!lv)throw new Error(j.error||j.ai_level_error||'GPT chưa phân mức được câu này.');
    adminApplyMucDoChip(lv);
    let conf=String(j.confidence||'').trim();
    let reason=String(j.reason||'').trim();
    if(note){
      note.innerHTML='🎯 GPT ADMIN gợi ý mức độ: <span class="mucdoBadge '+mucdoBadgeClass(lv)+'">'+esc(lv)+'</span>'+(conf?' · tin cậy '+esc(conf):'')+(reason?'<br><span class="muted">Lý do: '+esc(reason)+'</span>':'')+'<br><b>Chưa lưu Sheet.</b> Kiểm tra rồi bấm <b>Lưu vào Google Sheet</b> hoặc <b>💾 Lưu mức độ</b>.';
    }
  }catch(e){
    alert('AI chưa nhận mức độ: '+e.message);
    if(note)note.textContent='AI nhận mức độ lỗi. Có thể chọn chip NB/TH/VD/VDC tay rồi lưu.';
  }finally{
    if(btn){btn.disabled=false;btn.textContent=oldBtn||'🎯 Gợi ý mức độ'}
  }
}
async function aiDetectAndSaveCurrentQuestionLevel(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(QUESTION_SAVE_BUSY)return;
  if(QUESTION_MODAL_MODE==='add'){
    alert('Câu mới chưa có dòng Sheet. Hãy thêm câu trước, rồi mới AI nhận & lưu mức độ.');
    return;
  }
  let q0=QUESTIONS[CUR]||{};
  if(!q0._row){alert('Không xác định dòng Sheet của câu này.');return}
  let btn=document.getElementById('btnAiDetectSaveLevel');
  let btn2=document.getElementById('btnAiDetectLevel');
  let oldBtn=btn?btn.textContent:'';
  let note=document.getElementById('editModalNote');
  try{
    QUESTION_SAVE_BUSY=true;
    if(btn){btn.disabled=true;btn.textContent='⏳ GPT nhận & lưu I...'}
    if(btn2){btn2.disabled=true}
    let q=readQuestionFormData();
    q.Dang=normDangFormVal(q.Dang||'');
    let j=await adminApiPost('/api/ai/detect-level-update',{row:q0._row,id:q0.ID||'',question:q});
    let lv=normMucDoFormVal(j.MucDo||j.ai_mucdo||'');
    if(!lv)throw new Error(j.error||j.ai_level_error||'GPT chưa phân mức được câu này.');
    adminApplyMucDoChip(lv);
    q0.MucDo=lv;
    let reason=String(j.reason||'').trim();
    if(note){
      note.innerHTML='✅ Đã lưu mức độ <span class="mucdoBadge '+mucdoBadgeClass(lv)+'">'+esc(lv)+'</span> vào Google Sheet dòng <b>'+esc(j.row||q0._row)+'</b> (cột I).'+ (reason?'<br><span class="muted">Lý do: '+esc(reason)+'</span>':'')+'<br><span class="muted">Chỉ cập nhật cột I. Các ô khác chưa bị thay đổi.</span>';
    }
    renderNav();
    syncQuestionMucDoChrome(q0);
  }catch(e){
    alert('Không nhận & lưu mức độ: '+e.message);
    if(note)note.textContent='AI nhận/lưu mức độ lỗi. Có thể chọn chip NB/TH/VD/VDC tay rồi bấm Lưu.';
  }finally{
    QUESTION_SAVE_BUSY=false;
    if(btn){btn.disabled=false;btn.textContent=oldBtn||'💾 Lưu mức độ'}
    if(btn2){btn2.disabled=false}
  }
}

async function aiRepairCurrentQuestion(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(QUESTION_SAVE_BUSY){return}
  if(!adminEnsureAiReady())return
  saveCurrent();
  let q=QUESTIONS[CUR]||{};
  let target=(typeof resolveDang==='function'?resolveDang(q):(q.Dang||''))||'';
  adminSetEditAiStatus('<span class="hintSpin"></span> <b>AI đang khôi phục câu thiếu…</b><span class="muted" style="font-size:12px"> ('+esc(adminAiProviderLabel(adminChosenAiProvider()))+') · Không tự lưu Sheet.</span>');
  try{
    let j=await adminApiPost('/api/ai/repair-question',{sid:SID,index:CUR,target_dang:target,mode:'repair',...quizRestorePayload()},{timeoutMs:95000});
    let rq=j.question||{};
    openEdit();
    for(let f of QUESTION_FORM_FIELDS){
      let el=document.getElementById('edit_'+f);
      if(!el)continue;
      if(Object.prototype.hasOwnProperty.call(rq,f))el.value=rq[f]||'';
    }
    ['QuyenTruyCap','MucDo','Dang','NangLucVatLy'].forEach(syncAdminChipGroup);
    adminMetaSyncAll();
    adminDbtSyncSelectFromInput();
    syncQuestionModalChrome();
    showEditQuestionPreview();
    let note=document.getElementById('editModalNote');
    if(note){
      let warn=String(j.warning||'').trim();
      note.innerHTML='🧩 AI đã khôi phục/bổ sung câu. <b>ADMIN cần kiểm tra lại đáp án và lời giải trước khi lưu.</b>'+(warn?'<br><span style="color:#991b1b">⚠️ '+esc(warn)+'</span>':'');
    }
    let hb=document.getElementById('hintBox');
    if(hb){
      hb.classList.remove('hide');
      hb.classList.remove('hintBoxLoading');
      let miss=(j.missing_before&&j.missing_before.missing)?j.missing_before.missing.join(', '):'';
      hb.innerHTML='<b>🧩 AI khôi phục câu thiếu</b><div class="muted" style="margin-top:6px">Dạng mục tiêu: <b>'+esc(j.target_dang||target)+'</b>'+(miss?' · Thiếu trước khi sửa: '+esc(miss):'')+'</div>'+(j.warning?'<div class="muted" style="margin-top:6px;color:#991b1b">⚠️ '+esc(j.warning)+'</div>':'')+'<div class="muted" style="margin-top:6px">Đã điền vào form sửa. Kiểm tra rồi bấm <b>Lưu vào Google Sheet</b>.</div>';
    }
  }catch(e){
    alert('AI chưa khôi phục được: '+(typeof apiNetworkErrorMsg==='function'?apiNetworkErrorMsg(e):(e.message||e)));
  }finally{
    adminSetEditAiStatus('');
  }
}
async function aiRewriteDsStatements(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(QUESTION_SAVE_BUSY)return;
  if(!adminEnsureAiReady())return;
  let form=readQuestionFormData();
  if(normDangFormVal(form.Dang)!=='Đúng sai'){alert('Chỉ dùng cho câu Đúng/Sai.');return}
  if(!['A','B','C','D'].some(L=>String(form[L]||'').trim())){alert('Chưa có mệnh đề A–D.');return}
  if(!confirm('AI sẽ viết lại CauHoi + 4 mệnh đề A–D cho đúng dạng Đ/S.\n\nKhông đổi Đáp án (P) và Lời giải (R). Chưa lưu Sheet. Tiếp tục?'))return;
  let btn=document.getElementById('btnAiRewriteDsStatements');
  let oldBtn=btn?btn.textContent:'';
  adminSetEditAiStatus('<span class="hintSpin"></span> <b>AI đang viết lại mệnh đề Đ/S…</b><span class="muted" style="font-size:12px"> ('+esc(adminAiProviderLabel(adminEditAiProvider()))+') · Không đổi P/R.</span>');
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳ Viết lại…'}
    let payload={question:form,admin_ai_allow_gpt_fallback:true};
    let j=await adminApiPost('/api/ai/rewrite-ds-statements',payload,{timeoutMs:65000,admin_ai_provider:adminEditAiProvider(),admin_ai_allow_gpt_fallback:true});
    for(let f of ['CauHoi','A','B','C','D']){
      let el=document.getElementById('edit_'+f);
      if(el&&Object.prototype.hasOwnProperty.call(j,f))el.value=j[f]||'';
    }
    showEditQuestionPreview();
    let warn=String(j.warning||'').trim();
    let note=document.getElementById('editModalNote');
    if(note){
      note.innerHTML='📐 AI đã viết lại câu dẫn + mệnh đề A–D. <b>Kiểm tra P/R rồi bấm Lưu Sheet.</b>'+(warn?'<br><span style="color:#991b1b">⚠️ '+esc(warn)+'</span>':'');
    }
    alert('✅ Đã viết lại mệnh đề Đ/S ('+(j.provider||adminAiProviderLabel(adminEditAiProvider()))+').'+(warn?'\n\n⚠ '+warn:'')+'\n\nĐã bật xem trước — kiểm tra rồi Lưu Sheet.');
  }catch(e){
    alert('AI chưa viết lại được: '+(typeof apiNetworkErrorMsg==='function'?apiNetworkErrorMsg(e):(e.message||e)));
  }finally{
    if(btn){btn.disabled=false;btn.textContent=oldBtn||'📐 Viết lại mệnh đề Đ/S'}
    adminSetEditAiStatus('');
  }
}
function syncEditDsRewriteButton(){
  let btn=document.getElementById('btnAiRewriteDsStatements');
  if(!btn)return;
  let dang='';
  try{dang=normDangFormVal(readQuestionFormData().Dang)}catch(e){}
  if(!dang){let q=QUESTIONS[CUR]||{};dang=normDangFormVal(q.Dang)}
  btn.classList.toggle('hide',QUESTION_MODAL_MODE==='add'||dang!=='Đúng sai');
}
async function adminCreateSimilarForSave(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(QUESTION_SAVE_BUSY)return;
  if(typeof adminEnsureAiReady==='function'&&!adminEnsureAiReady())return;
  let modal=document.getElementById('modal');
  if(!modal||modal.classList.contains('hide')){
    if(typeof openEdit==='function')openEdit();
  }
  let src={};
  try{src=Object.assign({},QUESTIONS[CUR]||{},readQuestionFormData())}catch(e){src=Object.assign({},QUESTIONS[CUR]||{})}
  if(!String(src.CauHoi||'').trim()){alert('Câu gốc chưa có nội dung — mở Sửa câu hoặc nhập Câu hỏi trước.');return}
  if(!confirm('AI tạo câu tương tự từ câu này và điền vào form Thêm câu mới?\n\nBạn kiểm tra đáp án/lời giải rồi bấm «Thêm vào Google Sheet» để lưu.'))return;
  let btn=document.getElementById('btnAdminSimilarSave');
  let oldBtn=btn?btn.textContent:'';
  if(btn){btn.disabled=true;btn.textContent='⏳ Đang tạo…'}
  if(typeof adminSetEditAiStatus==='function')adminSetEditAiStatus('<span class="hintSpin"></span> <b>AI đang tạo câu tương tự để lưu…</b><span class="muted" style="font-size:12px"> Không tự lưu Sheet.</span>');
  try{
    let dbt=String(src.DangBaiTap||'').trim();
    let peers=[];
    if(dbt){
      for(let i=0;i<QUESTIONS.length;i++){
        let oq=QUESTIONS[i]||{};
        if(i===CUR)continue;
        if(String(oq.DangBaiTap||'').trim()!==dbt)continue;
        let t=String(oq.CauHoi||'').trim();
        if(t)peers.push(t.slice(0,220));
        if(peers.length>=5)break;
      }
    }
    let j=await adminApiPost('/api/admin/question-similar',{question:src,peer_briefs:peers},{timeoutMs:95000});
    let fields=j.fields||{};
    if(j.similar&&typeof adminParsePastedQuestion==='function'){
      let parsed=adminParsePastedQuestion(j.similar);
      if(parsed){
        if(!String(fields.CauHoi||'').trim()&&parsed.CauHoi)fields.CauHoi=parsed.CauHoi;
        for(let L of ['A','B','C','D']){if(!String(fields[L]||'').trim()&&parsed[L])fields[L]=parsed[L]}
        if(!String(fields.DapAn||'').trim()&&parsed.DapAn)fields.DapAn=parsed.DapAn;
        if(!String(fields.LoiGiai||'').trim()&&parsed.LoiGiai)fields.LoiGiai=parsed.LoiGiai;
        if(!String(fields.Dang||'').trim()&&parsed.Dang)fields.Dang=parsed.Dang;
      }
    }
    if(!String(fields.CauHoi||'').trim()){alert('AI chưa tách được câu hỏi. Thử lại hoặc dán thủ công.');return}
    QUESTION_MODAL_MODE='add';
    ADMIN_SIMILAR_EDIT_TIPS=j.admin_variant_tips||null;
    let seed={
      MaDe:src.MaDe||CURRENT_MADE||'',
      Mon:src.Mon||'',
      Lop:src.Lop||'',
      Chuong:src.Chuong||'',
      BaiHoc:src.BaiHoc||src.De||'',
      DangBaiTap:src.DangBaiTap||'',
      NangLucVatLy:src.NangLucVatLy||'',
      QuyenTruyCap:src.QuyenTruyCap||'VIP',
      MucDo:fields.MucDo||src.MucDo||'',
      Dang:fields.Dang||src.Dang||'Trắc nghiệm',
      CauHoi:fields.CauHoi||'',
      A:fields.A||'',
      B:fields.B||'',
      C:fields.C||'',
      D:fields.D||'',
      DapAn:fields.DapAn||'',
      SaiSo:fields.SaiSo||'',
      LoiGiai:fields.LoiGiai||'',
      HinhAnh:'',
      ID:''
    };
    seed=adminAutoSplitAbcdFields(seed);
    renderQuestionForm(seed);
    ['QuyenTruyCap','MucDo','Dang','NangLucVatLy'].forEach(syncAdminChipGroup);
    if(typeof adminSyncDapAnDom==='function')adminSyncDapAnDom(seed.DapAn||'');
    let lgEl=document.getElementById('edit_LoiGiai');if(lgEl)lgEl.value=seed.LoiGiai||'';
    if(typeof adminMetaSyncAll==='function')adminMetaSyncAll();
    if(typeof adminDbtSyncSelectFromInput==='function')adminDbtSyncSelectFromInput();
    syncQuestionModalChrome();
    if(typeof refreshEditHinhAnhPreview==='function')refreshEditHinhAnhPreview();
    if(typeof renderEditQuestionPreview==='function')renderEditQuestionPreview();
    document.getElementById('modal').classList.remove('hide');
    let tipBits=[];
    let tips=j.admin_variant_tips||{};
    if(tips.suggest_find&&tips.suggest_find.length)tipBits.push('Đổi sang tìm: '+tips.suggest_find.join('; '));
    if(tips.suggest_change&&tips.suggest_change.length)tipBits.push('Đổi số liệu: '+tips.suggest_change.join('; '));
    let miss=[];
    if((seed.Dang==='Trắc nghiệm'||seed.Dang==='Đúng sai')&&!(seed.A&&seed.B))miss.push('phương án A–D');
    if(!String(seed.DapAn||'').trim())miss.push('đáp án (P)');
    if(!String(seed.LoiGiai||'').trim())miss.push('lời giải (R)');
    let missMsg=miss.length?('\n\n⚠️ Chưa tách được '+miss.join(' · ')+' — bấm lại «Tạo câu tương tự» hoặc điền tay trước khi Lưu.\n(Gemini hay bọc tiêu đề bằng ** — app đã hỗ trợ tách lại.)'):'';
    alert('Đã điền câu tương tự vào form Thêm mới.\nKiểm tra rồi bấm «➕ Thêm vào Google Sheet».'+missMsg+(tipBits.length?'\n\n'+tipBits.join('\n'):''));
  }catch(e){
    alert('Không tạo được câu tương tự: '+(typeof apiNetworkErrorMsg==='function'?apiNetworkErrorMsg(e):(e.message||e)));
  }finally{
    if(btn){btn.disabled=false;btn.textContent=oldBtn||'📝 Tạo câu tương tự'}
    if(typeof adminSetEditAiStatus==='function')adminSetEditAiStatus('');
  }
}
function setAdminChip(field,value){let el=document.getElementById('edit_'+field);if(el)el.value=value;syncAdminChipGroup(field);if(field==='Dang'){if(normDangFormVal(value)==='Đúng sai')syncDsEditFormFields(Object.assign({},QUESTIONS[CUR]||{},readQuestionFormData()));if(typeof adminRerenderDapAnField==='function')adminRerenderDapAnField();if(typeof renderEditQuestionPreview==='function')renderEditQuestionPreview();if(typeof syncEditDsRewriteButton==='function')syncEditDsRewriteButton()}}
function refreshEditHinhAnhPreview(){let box=document.getElementById('edit_HinhAnhPreview');let el=document.getElementById('edit_HinhAnh');if(!box)return;let raw=adminMergedHinhAnhFromForm();if(isDriveFolderUrl(el?el.value:'')){box.innerHTML='<div style="padding:10px;border-radius:8px;background:#dcfce7;border:1px solid #86efac;color:#166534;font-size:13px">✅ Đã nhận thư mục <b>Anh_Luyen_De</b>.<br><b>Để trống cột T</b> — câu có TikZ sẽ tự có link ảnh khi Lưu.<br><span class="muted" style="font-size:12px">Link thư mục không ghi vào Sheet.</span></div>';syncAdminSolutionFigHint();return}let src=adminPreviewHinhAnhSrc();if(!src){box.innerHTML='<span class="muted" style="font-size:12px">'+(String(raw||'').trim()?'':'<b>Sửa TikZ bên dưới</b> hoặc dán link <b>file ảnh</b> Drive vào ô trên.')+'</span>';syncAdminSolutionFigHint();return}box.innerHTML=buildQimgHtml(src);syncAdminSolutionFigHint()}
function adminEditFormQuestion(){let q=readQuestionFormData();q.Dang=normDangFormVal(q.Dang||'');let merged=adminMergedHinhAnhFromForm();if(merged)q.HinhAnh=merged;return applyResolvedDang(q)}
function adminInsertHinhToLoigiai(){let lgEl=document.getElementById('edit_LoiGiai');if(!lgEl){alert('Không tìm thấy ô Lời giải.');return}if(!adminMergedHinhAnhFromForm().trim()){alert('Chưa có TikZ hoặc link ảnh ở cột T.');return}let v=String(lgEl.value||'');if(/\[LG-ONLY\]/i.test(v)){if(/\[HINH\]|\[T\]|\[IMG-LG\]/i.test(v)){alert('Đã có [HINH] trong lời giải.');return}lgEl.value=(v.trim()?v.trim()+'\n\n':'')+'[HINH]';renderEditQuestionPreview();syncAdminSolutionFigHint();return}if(/\[HINH\]|\[T\]|\[IMG-LG\]/i.test(v)){if(!/\[LG-ONLY\]/i.test(v))lgEl.value=v.trim()+'\n[LG-ONLY]';alert('Đã có [HINH]. Thêm [LG-ONLY] để chắc chắn không hiện trên đề.');renderEditQuestionPreview();syncAdminSolutionFigHint();return}lgEl.value=(v.trim()?v.trim()+'\n\n':'')+'[LG-ONLY]\n[HINH]';renderEditQuestionPreview();syncAdminSolutionFigHint()}
function syncAdminSolutionFigHint(){let box=document.getElementById('editSolutionFigHint');if(!box)return;let q=adminEditFormQuestion();box.innerHTML='<div style="margin-top:6px;padding:8px 10px;border-radius:8px;background:#f0f9ff;border:1px solid #bae6fd;color:#0c4a6e;font-size:12px;line-height:1.5"><b>📐 TikZ/hình — hiện đúng chỗ ghi:</b><br>• Trong <b>K / A–D / R</b> → vẽ ngay tại ô đó khi làm bài.<br>• <b>Cột T</b> = kho lưu Sheet; muốn hiện trong LG thì gõ <code>[HINH]</code> trong R (hoặc dán TikZ thẳng vào R).<br>• <code>[LG-ONLY]</code> = không kéo ảnh T lên đề.</div>'}
function renderEditQuestionPreview(){
  let box=document.getElementById('editQuestionPreview');
  if(!box||box.classList.contains('hide'))return;
  let q=adminEditFormQuestion();
  let dang=q.Dang||'Trắc nghiệm';
  let head='<div style="font-weight:800;margin-bottom:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">👁 Xem trước câu <span class="tag">'+esc(dang)+'</span></div>';
  let img=q.HinhAnh?buildQimgHtml(q.HinhAnh):'';
  let splitImg=usesImgSplit(q);
  let qImg=hinhanhIsSolutionFigure(q)?'':img;
  let body=renderQuizFieldHtml(q.CauHoi||'')||'<span class="muted">(Chưa có nội dung câu hỏi)</span>';
  let opts='';
  if(dang==='Trắc nghiệm'){
    for(let L of ['A','B','C','D']){
      if(!q[L])continue;
      opts+='<div class="opt"><span>'+dsCircleHtml(L)+'</span><span>'+renderQuizFieldHtml(stripOptionPrefix(q[L],L))+'</span></div>';
    }
    if(mcqOptsUse2Col(q))opts=`<div class="mcqOptsGrid2">${opts}</div>`;
  }else if(dang==='Đúng sai'){
    for(let L of ['A','B','C','D']){
      if(!q[L])continue;
      opts+='<div class="tfrow">'+dsCircleHtml(L)+'<div class="tfStmt">'+renderQuizFieldHtml(q[L])+'</div></div>';
    }
  }else if(dang==='Trả lời ngắn'){
    opts='<div class="shortAnsBox shortAnsCompact"><div class="muted">Đáp số P: <b>'+(renderRichText(q.DapAn||'—'))+'</b>'+(q.SaiSo?' · ±'+esc(q.SaiSo):'')+'</div></div>';
  }
  let sol='';
  if(q.DapAn||q.LoiGiai){
    let daPart='';
    if(q.DapAn){
      if(dang==='Trắc nghiệm')daPart='<div><b>Đáp án:</b> '+formatMcqAnswerBadge(q.DapAn)+'</div>';
      else if(dang==='Đúng sai')daPart='<div><b>Đáp án:</b> '+formatDsAnswerBadges(q.DapAn)+'</div>';
      else daPart='<div><b>P:</b> '+renderRichText(q.DapAn)+'</div>';
    }
    let lgPart='';
    if(q.LoiGiai){
      let lgBody=formatLoigiaiByDang(q.LoiGiai,q,dang);
      lgPart='<div style="margin-top:6px"><b>Lời giải:</b><br>'+lgBody+'</div>';
    }
    sol='<div class="solution" style="margin-top:10px;font-size:13px">'+daPart+lgPart+'</div>';
  }
  box.innerHTML=head+'<div class="qbox adminEditPreviewQ">'+body+(splitImg?'':qImg)+'</div>'+(splitImg?'<div class="adminEditPreviewImg">'+img+'</div>':'')+opts+sol;
  typeset([box]);
}
let EDIT_PREVIEW_TIMER=null;
const EDIT_PREVIEW_DEBOUNCE_MS=360;
function scheduleEditQuestionPreview(){
  if(EDIT_PREVIEW_TIMER)clearTimeout(EDIT_PREVIEW_TIMER);
  EDIT_PREVIEW_TIMER=setTimeout(function(){
    EDIT_PREVIEW_TIMER=null;
    renderEditQuestionPreview();
  },EDIT_PREVIEW_DEBOUNCE_MS);
}
function showEditQuestionPreview(){
  let box=document.getElementById('editQuestionPreview');
  if(!box)return;
  box.classList.remove('hide');
  let btn=document.getElementById('btnEditTogglePreview');
  if(btn)btn.textContent='👁 Ẩn xem trước';
  renderEditQuestionPreview();
}
function toggleEditQuestionPreview(){
  let box=document.getElementById('editQuestionPreview');
  if(!box)return;
  box.classList.toggle('hide');
  let btn=document.getElementById('btnEditTogglePreview');
  if(btn)btn.textContent=box.classList.contains('hide')?'👁 Bật xem trước':'👁 Ẩn xem trước';
  if(!box.classList.contains('hide'))renderEditQuestionPreview();
}
function setEditDangQuick(dang){setAdminChip('Dang',dang);renderEditQuestionPreview()}
function bindEditFormLivePreview(){
  document.querySelectorAll('#editForm textarea, #editForm input').forEach(el=>{
    el.oninput=function(){
      let fid=String(el.id||'');
      if(fid==='edit_HinhAnh'||/tikz/i.test(fid))refreshEditHinhAnhPreview();
      scheduleEditQuestionPreview();
    };
  });
}
function ensureEditAdminPreviewBar(){let form=document.getElementById('editForm');if(!form)return;if(!document.getElementById('editAdminPreviewBar')){let bar=document.createElement('div');bar.id='editAdminPreviewBar';bar.className='editAdminPreviewBar';bar.innerHTML='<div style="font-weight:800;margin-bottom:6px">📋 Dán câu & xem trước</div><p class="muted" style="font-size:12px;margin:0 0 8px;line-height:1.45">Máy tính: <b>Ctrl+V</b> vào ô dưới hoặc bấm «Dán clipboard». Hỗ trợ <b>Word</b> (A. B. C. D.) và <b>LaTeX</b> (<code>\\begin{ex}</code>, <code>\\choiceTF</code>, <code>\\loigiai</code>). App tự tách Câu hỏi / A–D / P / R.</p><textarea id="editPasteBuffer" class="editAdminPasteBox" placeholder="Dán cả câu từ Word hoặc LaTeX…&#10;LaTeX: \\begin{ex} … \\choiceTF {\\True …} … \\loigiai{…} \\end{ex}&#10;Word: Một vật dao động… / A. 2 Hz / Đáp án: B"></textarea><div class="row" style="margin-bottom:8px"><button type="button" class="btn2 btnSmall" onclick="adminApplyPasteBuffer()">↪ Tách vào form</button><button type="button" class="btn2 btnSmall" onclick="adminPasteFromClipboard()">📋 Dán clipboard</button><button type="button" class="btn2 btnSmall" id="btnEditTogglePreview" onclick="toggleEditQuestionPreview()">👁 Bật xem trước</button></div><div class="row"><span class="muted" style="font-size:12px;font-weight:800">Dạng nhanh:</span><button type="button" class="adminChip mucdo-th btnSmall" onclick="setEditDangQuick(\'Trắc nghiệm\')">TN</button><button type="button" class="adminChip btnSmall" onclick="setEditDangQuick(\'Đúng sai\')">Đ/S</button><button type="button" class="adminChip btnSmall" onclick="setEditDangQuick(\'Trả lời ngắn\')">TLN</button></div>';form.parentNode.insertBefore(bar,form)}if(!document.getElementById('editQuestionPreview')){let prev=document.createElement('div');prev.id='editQuestionPreview';prev.className='editQuestionPreview hide';form.parentNode.insertBefore(prev,form)}}
function adminSplitInlineAbcdOptions(text){
  text=String(text||'').trim();if(!text)return null;
  let re=/(?:^|[\s;|·•]|(?<=[\]\)\}]))(?:\*\*|__|\*)?\(?([ABCD])\)?(?:\*\*|__|\*)?\s*[\.\)\:：]\s*/gi;
  let matches=[],m;while((m=re.exec(text))){matches.push({L:m[1].toUpperCase(),start:m.index,end:m.index+m[0].length})}
  if(matches.length<2){
    re=/(?:^|\s)(?:\*\*|__|\*)?\(?([ABCD])\)?(?:\*\*|__|\*)?\s*[\.\)\:：]\s*/gi;
    matches=[];while((m=re.exec(text))){matches.push({L:m[1].toUpperCase(),start:m.index,end:m.index+m[0].length})}
  }
  if(matches.length<2)return null;
  let out={};
  if(matches[0].L!=='A'&&matches[0].start>0){let lead=text.slice(0,matches[0].start).trim().replace(/^\*+\s*|\s*\*+$/g,'');if(lead)out.A=lead}
  for(let i=0;i<matches.length;i++){let L=matches[i].L;if(!'ABCD'.includes(L)||out[L])continue;let chunk=text.slice(matches[i].end,i+1<matches.length?matches[i+1].start:text.length).trim().replace(/^\*+\s*|\s*\*+$/g,'').replace(/[\s;|·•,]+$/,'');chunk=chunk.replace(new RegExp('^\\s*'+L+'\\s*[\\.\\)\\:：]\\s*','i'),'');if(chunk)out[L]=chunk}
  return (Object.keys(out).length>=2)?out:null;
}
function adminAutoSplitAbcdFields(data){
  data=data||{};
  let blob=[data.A,data.B,data.C,data.D].map(x=>String(x||'').trim()).filter(Boolean).join(' ');
  if(!blob)return data;
  let need=!(data.A&&data.B&&data.C)||(/[BCD]\s*[\.\)\:：]/i.test(String(data.A||''))&&!String(data.B||'').trim());
  if(!need&&data.A&&data.B)return data;
  let src=String(data.A||'').trim();
  if(data.B||data.C||data.D)src=['A','B','C','D'].filter(L=>data[L]).map(L=>{let v=String(data[L]||'').trim();return /^[ABCD]\s*[\.\)\:：]/i.test(v)?v:(L+'. '+v)}).join(' ');
  else if(src&&!/^\s*A\s*[\.\)\:：]/i.test(src)&&/[BCD]\s*[\.\)\:：]/i.test(src))src='A. '+src;
  let split=adminSplitInlineAbcdOptions(src||blob);
  if(!split)return data;
  let out=Object.assign({},data);for(let L of ['A','B','C','D'])if(split[L])out[L]=split[L];
  return out;
}
function adminSplitAbcdFromForm(){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return}
  let data={A:val('edit_A'),B:val('edit_B'),C:val('edit_C'),D:val('edit_D')};
  let next=adminAutoSplitAbcdFields(data);
  if(!(next.A&&next.B)){alert('Không tách được A–D. Dán dạng:\nA. … B. … C. … D. …');return}
  for(let L of ['A','B','C','D']){let el=document.getElementById('edit_'+L);if(el)el.value=next[L]||''}
  if(typeof renderEditQuestionPreview==='function')renderEditQuestionPreview();
  alert('Đã tách thành 4 phương án A–D.');
}
window.adminSplitAbcdFromForm=adminSplitAbcdFromForm;
function adminFillQuestionForm(data){if(!data)return;data=adminAutoSplitAbcdFields(data);for(let f of ['CauHoi','A','B','C','D','DapAn','SaiSo','LoiGiai']){if(data[f]==null)continue;let el=document.getElementById('edit_'+f);if(el)el.value=data[f]}if(data.Tikz){let tzEl=document.getElementById('edit_Tikz');adminMergeTikzIntoField(tzEl,data.Tikz)}if(data.HinhAnh!=null){let parsed=parseHinhanhCellClient(data.HinhAnh);let imgEl=document.getElementById('edit_HinhAnh');let tzEl=document.getElementById('edit_Tikz');if(imgEl)imgEl.value=parsed.img&&!/^tikzraw:/i.test(parsed.img)?parsed.img:'';if(tzEl&&parsed.tikz)adminMergeTikzIntoField(tzEl,parsed.tikz)}adminExtractTikzFromFormFields();if(data.Dang)setAdminChip('Dang',normDangFormVal(data.Dang))}
function adminLooksLikeLatexBlock(s){return /\\begin\s*\{\s*(?:ex|bt)\s*\}|\\choiceTF\b|\\choice\b|\\loigiai\b|\\shortans\b/i.test(String(s||''))}
function adminReadLatexBraced(s,pos){if(pos<0||s[pos]!=='{')return null;let depth=0;for(let i=pos;i<s.length;i++){if(s[i]==='\\'&&i+1<s.length){i++;continue}if(s[i]==='{')depth++;else if(s[i]==='}'){depth--;if(depth===0)return{text:s.slice(pos+1,i),end:i+1}}}return null}
function adminReadLatexCmdArgs(s,cmd,maxArgs){let re=new RegExp('\\\\'+cmd+'\\b','i'),m=re.exec(s);if(!m)return null;let pos=m.index+m[0].length,args=[];while(args.length<maxArgs){while(pos<s.length&&/\s/.test(s[pos]))pos++;if(s[pos]!=='{')break;let b=adminReadLatexBraced(s,pos);if(!b)break;args.push(b.text);pos=b.end}return args.length?{start:m.index,end:pos,args}:null}
function adminParsePastedLatexBlock(raw){raw=String(raw||'').replace(/\r/g,'').trim();if(!raw||!adminLooksLikeLatexBlock(raw))return null;let tex=raw;if(!/\\begin\s*\{\s*(?:ex|bt)\s*\}/i.test(tex))tex='\\begin{ex}\n'+tex+'\n\\end{ex}';let bm=/\\begin\s*\{\s*(ex|bt)\s*\}([\s\S]*?)\\end\s*\{\s*\1\s*\}/i.exec(tex);let t=(bm?bm[2]:tex).trim();let out={CauHoi:'',A:'',B:'',C:'',D:'',DapAn:'',SaiSo:'',LoiGiai:'',HinhAnh:'',Tikz:'',Dang:''};let lo=adminReadLatexCmdArgs(t,'loigiai',1);if(lo){out.LoiGiai=stripLatexListMarkup(lo.args[0].replace(/\\True\b/gi,'').trim());t=(t.slice(0,lo.start)+t.slice(lo.end)).trim()}let sh=adminReadLatexCmdArgs(t,'shortans',1);if(sh){out.DapAn=sh.args[0].replace(/\\True\b/gi,'').trim();t=(t.slice(0,sh.start)+t.slice(sh.end)).trim();out.Dang='Trả lời ngắn'}else{let tf=adminReadLatexCmdArgs(t,'choiceTF',4);if(tf&&tf.args.length>=2){let vals=[];['A','B','C','D'].forEach((L,k)=>{let v=tf.args[k]||'';vals.push(/\\True\b/i.test(v)?'Đ':'S');out[L]=v.replace(/\\True\b/gi,'').trim()});out.DapAn=vals.join(',');t=(t.slice(0,tf.start)+t.slice(tf.end)).trim();out.Dang='Đúng sai'}else{let ch=adminReadLatexCmdArgs(t,'choice',4);if(ch&&ch.args.length>=2){['A','B','C','D'].forEach((L,k)=>{let v=ch.args[k]||'';if(/\\True\b/i.test(v))out.DapAn=L;out[L]=v.replace(/\\True\b/gi,'').trim()});t=(t.slice(0,ch.start)+t.slice(ch.end)).trim();out.Dang='Trắc nghiệm'}}}out.CauHoi=t.replace(/^\s*\[(?:TTN|TDS|TLN|TL|TN|DS)\]\s*/gim,'').replace(/^\s*Câu\s*\d+\s*[.:]/i,'').trim();if(!out.CauHoi&&!out.A&&!out.B&&!out.C&&!out.D)return null;return out}
function adminParsePastedQuestion(raw){raw=String(raw||'').replace(/\r/g,'').trim();if(!raw)return null;let latex=adminParsePastedLatexBlock(raw);if(latex)return latex;let work=raw,out={CauHoi:'',A:'',B:'',C:'',D:'',DapAn:'',SaiSo:'',LoiGiai:'',HinhAnh:'',Tikz:'',Dang:''};let loiM=work.match(/(?:^|\n)\s*(?:\*\*|__)?\s*(?:4[\.\)]\s*)?(?:Lời giải|LoiGiai|LG|Giải|Hướng dẫn giải)\s*(?:\*\*|__)?\s*[:：]?\s*\n([\s\S]*)$/i);if(loiM){out.LoiGiai=loiM[1].trim();work=work.slice(0,loiM.index).trim()}let imgM=work.match(/(?:Hình(?: ảnh)?|HinhAnh|Image|Link\s*ảnh|Cột T)\s*[:：]?\s*(https?:\S+|drive[^\s]+)/i);if(imgM){out.HinhAnh=imgM[1].trim();work=work.replace(imgM[0],'').trim()}let ssM=work.match(/(?:Sai số|SaiSo|±)\s*[:：]?\s*([0-9.,]+)/i);if(ssM)out.SaiSo=ssM[1].trim();let daM=work.match(/(?:^|\n)\s*(?:\*\*|__)?\s*(?:3[\.\)]\s*)?(?:Đáp án(?:\s*đúng)?|DapAn|ĐA|Answer|Chọn|Đ\/S|P\s*[:=])\s*(?:\*\*|__)?\s*[:：]?\s*([^\n]+)/i);if(daM){out.DapAn=daM[1].trim().replace(/^[.:]\s*/,'').replace(/^\*+\s*|\s*\*+$/g,'');work=work.replace(daM[0],'').trim()}let opts={};let optRe=/^[ \t]*(?:\*\*|__|\*)?\s*([ABCD])\s*(?:\*\*|__|\*)?\s*[.)\:：]\s*(?:\*\*|__)?\s*(.+?)\s*(?:\*\*|__)?\s*$/gim,m;while((m=optRe.exec(work))){let L=m[1].toUpperCase(),t=String(m[2]||'').trim().replace(/^\*+\s*|\s*\*+$/g,'');opts[L]=opts[L]?(opts[L]+'\n'+t):t}work=work.replace(/^[ \t]*(?:\*\*|__|\*)?\s*[ABCD]\s*(?:\*\*|__|\*)?\s*[.)\:：]\s*.+$/gim,'').trim();work=work.replace(/(?:^|\n)\s*(?:\*\*|__)?\s*(?:2[\.\)]\s*)?(?:CÁC\s+LỰA\s+CHỌN|LỰA\s+CHỌN|PHƯƠNG\s+ÁN)\s*(?:\*\*|__)?\s*[:：]?\s*/gi,'\n').trim();work=work.replace(/(?:^|\n)\s*(?:\*\*|__)?\s*(?:1[\.\)]\s*)?(?:Câu hỏi(?:\s*mới)?|CauHoi|Nội dung|Đề bài)\s*(?:\*\*|__)?\s*[:：.\-—]?\s*/i,'').trim();out.CauHoi=work;out.A=opts.A||'';out.B=opts.B||'';out.C=opts.C||'';out.D=opts.D||'';out=adminAutoSplitAbcdFields(out);let tikzParts=[];function pullTikz(key,val){let ex=extractTikzBlocksClient(val);if(ex.tikz)tikzParts.push(ex.tikz);out[key]=ex.cleaned}pullTikz('LoiGiai',out.LoiGiai);pullTikz('CauHoi',out.CauHoi);for(let L of ['A','B','C','D'])pullTikz(L,out[L]);if(tikzParts.length)out.Tikz=tikzParts.join('\n\n');if(looksDsAnswer(out.DapAn))out.Dang='Đúng sai';else if(isMcqLetter(out.DapAn)&&hasOptsClient(out))out.Dang='Trắc nghiệm';else if(out.DapAn&&String(out.DapAn).trim()&&!hasOptsClient(out))out.Dang='Trả lời ngắn';else if(hasOptsClient(out))out.Dang='Trắc nghiệm';else out.Dang='Trắc nghiệm';if(!out.CauHoi&&!out.A&&!out.B&&!out.C&&!out.D&&!out.Tikz)return null;return out}
async function adminApplyPasteBuffer(){let ta=document.getElementById('editPasteBuffer');let raw=String(ta?.value||'').trim();if(!raw){alert('Chưa có nội dung để tách — dán câu vào ô trên.');return}let parsed=null;if(adminLooksLikeLatexBlock(raw)&&USER&&USER.is_admin){try{let tex=raw;if(!/\\begin\s*\{\s*(?:ex|bt)\s*\}/i.test(tex))tex='\\begin{ex}\n'+tex+'\n\\end{ex}';let j=await api('/api/latex/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tex,commit:false})});let qs=j&&j.questions?j.questions:[];if(qs.length)parsed=qs[0]}catch(e){}}if(!parsed)parsed=adminParsePastedQuestion(raw);if(!parsed){alert('Không tách được — thử định dạng Word (A. B. C. D.) hoặc LaTeX:\n\\begin{ex}...\\choiceTF{...}\\loigiai{...}\\end{ex}');return}adminFillQuestionForm(parsed);refreshEditHinhAnhPreview();renderEditQuestionPreview();let tzNote=parsed.Tikz?' (đã tách TikZ vào ô 📐)':'';let srcNote=adminLooksLikeLatexBlock(raw)?' (LaTeX ex/choiceTF)':'';alert('Đã tách vào form ('+(parsed.Dang||'TN')+')'+srcNote+tzNote+'. Kiểm tra LaTeX và bấm Lưu.')}
async function adminPasteFromClipboard(){try{let txt=await navigator.clipboard.readText();if(!String(txt||'').trim()){alert('Clipboard trống.');return}let ta=document.getElementById('editPasteBuffer');if(ta)ta.value=txt;await adminApplyPasteBuffer()}catch(e){alert('Không đọc clipboard tự động — bấm vào ô «Dán cả câu» rồi Ctrl+V, sau đó «Tách vào form».')}}
function syncAdminChipGroup(field){let el=document.getElementById('edit_'+field);let val=el?String(el.value||''):'';document.querySelectorAll('[data-chip-field="'+field+'"]').forEach(btn=>{btn.classList.toggle('adminChipOn',btn.getAttribute('data-chip-value')===val)})}
function renderAdminChipGroup(field,options,current,normFn){let cur=normFn?normFn(current):String(current||'');let chips='';for(let opt of options){let v=typeof opt==='string'?opt:opt.v;let lab=typeof opt==='string'?opt:opt.l;let cls=typeof opt==='string'?(field==='MucDo'?mucdoBadgeClass(v):''):(opt.cls||'');let on=cur===v?' adminChipOn':'';chips+=`<button type="button" class="adminChip ${cls}${on}" data-chip-field="${field}" data-chip-value="${escAttr(v)}" onclick="setAdminChip('${field}','${escAttr(v)}')">${esc(lab)}</button>`}return `<div class="adminQuickField"><label><b>${QUESTION_FORM_LABELS[field]||field}</b></label><input type="hidden" id="edit_${field}" value="${escAttr(cur)}"><div class="adminChipRow">${chips}</div></div>`}
const LATEX_NORM_ACTIONS=[{id:'full',label:'⚡ Tất cả (chuẩn hóa đầy đủ)',group:'Tổng hợp'},{id:'light',label:'Chuẩn hóa nhẹ (không gộp khối $)',group:'Tổng hợp'},{id:'loigiai_abcd',label:'📋 LG TN/Đ-S → A B C D từng ý',group:'Lời giải'},{id:'wrap_long_lines',label:'↵ Cắt dòng câu / công thức dài',group:'Dòng & khoảng trắng'},{id:'strip_mathpix_space',label:'Xóa khoảng trắng Mathpix',group:'Dòng & khoảng trắng'},{id:'separate_dollar_text',label:'Tách $ dính văn bản',group:'Dòng & khoảng trắng'},{id:'fix_surplus_dollars',label:'Rút gọn dấu $ thừa',group:'Dấu $'},{id:'add_dollar_suitable',label:'Thêm $ phù hợp (LaTeX / điểm / đơn vị)',group:'Dấu $'},{id:'add_dollar_math',label:'Thêm $ vào \\frac, \\sqrt, (sin²)…',group:'Dấu $'},{id:'add_dollar_points',label:'Thêm $ vào tên điểm / số+đơn vị',group:'Dấu $'},{id:'close_formulas',label:'Đóng công thức ($ lệch)',group:'Dấu $'},{id:'display_dollar_to_bracket',label:'Chuyển $$...$$ → \\[...\\]',group:'Dấu $'},{id:'inline_dollar_to_paren',label:'Chuyển $...$ → \\(...\\)',group:'Dấu $'},{id:'display_bracket_to_dollar',label:'Chuyển \\[...\\] → $$...$$',group:'Dấu $'},{id:'merge_display_math',label:'Gộp nhiều \\[...\\] liền nhau',group:'Dấu $'},{id:'heva_to_tex',label:'Chuyển \\heva → aligned + {',group:'Hệ PT / macro'},{id:'strip_left_right',label:'Xóa \\left \\right dư',group:'Sửa cú pháp'},{id:'fix_degree_zero',label:'Sửa ^0 → ^\\circ',group:'Sửa cú pháp'},{id:'wrap_comma_braces',label:"Đưa dấu ',' vào '{}'",group:'Sửa cú pháp'},{id:'fix_redundant_rm',label:'Sửa lỗi dư \\rm',group:'Sửa cú pháp'},{id:'normalize_frac_vector',label:'Chuẩn hóa \\frac và vector',group:'Sửa cú pháp'},{id:'trim_brace_pairs',label:'Rút gọn cặp {}',group:'Sửa cú pháp'},{id:'dot_to_cdot',label:"Chuyển '.' thành \\cdot (trong số)",group:'Dấu câu'},{id:'cdot_to_dot',label:"Chuyển \\cdot thành '.'",group:'Dấu câu'},{id:'split_comma_points',label:"Tách dấu ',' trong tên điểm",group:'Dấu câu'},{id:'split_semicolon_formula',label:"Tách dấu ';' trong công thức",group:'Dấu câu'}];
function buildLatexNormMenuHtml(field){let groups={};LATEX_NORM_ACTIONS.forEach(a=>{(groups[a.group]=groups[a.group]||[]).push(a)});return Object.keys(groups).map(g=>'<div class="latexNormGroup"><div class="latexNormGroupTitle">'+esc(g)+'</div>'+groups[g].map(a=>'<button type="button" class="latexNormItem" onclick="normalizeLatexField(\''+field+'\',\''+a.id+'\');closeLatexNormMenu(\''+field+'\')">'+esc(a.label)+'</button>').join('')+'</div>').join('')}
function adminEditAiProvider(){return adminChosenAiProvider()}
function adminSaveEditAiProvider(p){return adminSaveChosenAiProvider(p)}
function renderEditLatexAiSelect(){let p=adminChosenAiProvider();return '<select class="editLatexAiSelect adminAiProviderSelect btnSmall btnClaudeFix" style="padding:4px 8px;max-width:108px" onchange="adminSaveChosenAiProvider(this.value)" title="Chọn AI viết lại LaTeX"><option value="GEMINI"'+(p==='GEMINI'?' selected':'')+'>⚡ Gemini</option><option value="ANTHROPIC"'+(p==='ANTHROPIC'?' selected':'')+'>✨ Claude</option><option value="OPENAI"'+(p==='OPENAI'?' selected':'')+'>✅ GPT</option></select>'}
function renderLatexNormToolbar(field){let mid='latexNormMenu_'+field;let aiLbl=adminAiProviderShort(adminChosenAiProvider());return '<div class="latexNormWrap"><button type="button" id="btn_ai_fix_'+field+'" class="btnSmall btnClaudeFix" onclick="claudeFixLatexField(\''+field+'\')" title="AI ('+adminAiProviderLabel(adminChosenAiProvider())+') sửa LaTeX trong ô này">🤖 '+aiLbl+'</button><button type="button" id="btn_norm_'+field+'" class="btnSmall btn2" onclick="normalizeLatexField(\''+field+'\',\'full\')">⚡ Chuẩn hóa</button><button type="button" class="btnSmall btn2 latexNormMore" onclick="toggleLatexNormMenu(\''+field+'\');event.stopPropagation()" title="Từng bước — không cần AI">▾</button><div id="'+mid+'" class="latexNormMenu hide" onclick="event.stopPropagation()">'+buildLatexNormMenuHtml(field)+'</div></div>'}
async function claudeFixLatexField(field){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  let el=document.getElementById('edit_'+field);
  if(!el){alert('Không tìm thấy ô.');return}
  let oldText=String(el.value||'').trim();
  if(!oldText){alert('Ô đang trống.');return}
  let btn=document.getElementById('btn_ai_fix_'+field)||document.getElementById('btn_claude_'+field);
  let prov=adminChosenAiProvider();
  let provLbl=adminAiProviderLabel(prov);
  let oldBtnHtml=btn?btn.innerHTML:('🤖 '+adminAiProviderShort(prov));

  try{
    if(btn){btn.disabled=true;btn.innerHTML='⚡ Đang chuẩn hóa…'}
    let j=await api('/api/admin/normalize-latex',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({field,text:oldText,action:'full',context:readQuestionFormData()})});
    if(j&&j.text!=null&&j.text!==oldText){
      el.value=j.text;
      oldText=j.text;
      if(['CauHoi','A','B','C','D','LoiGiai','HinhAnh'].includes(field)){
        refreshEditHinhAnhPreview();renderEditQuestionPreview();
      }
    }
  }catch(e){}

  let textAfterNorm=String(el.value||'').trim();
  let stillBroken=_clientLatexStillBroken(textAfterNorm);
  if(!stillBroken){
    if(btn){btn.disabled=false;btn.innerHTML=oldBtnHtml}
    alert('✅ Chuẩn hóa tự động xong — LaTeX đã đúng, không cần gọi AI.');
    return;
  }

  if(prov==='ANTHROPIC'){
    let antKey=_loadAnthropicKey();
    if(!antKey||!antKey.startsWith('sk-ant-')){
      if(btn){btn.disabled=false;btn.innerHTML=oldBtnHtml}
      alert('⚠️ Chọn Claude nhưng chưa có Anthropic key.\n\nVào 🔑 Key AI → sk-ant-... → Lưu.');
      return;
    }
  }

  try{
    if(btn){btn.innerHTML='🤖 '+provLbl+' đang sửa…'}
    let payload={field:field,text:textAfterNorm,context:readQuestionFormData(),admin_ai_allow_gpt_fallback:true};
    let j=await adminApiPost('/api/ai/rewrite-latex',payload,{timeoutMs:50000,admin_ai_provider:prov});
    if(j&&j.error)throw new Error(j.error);
    let fixed=(j&&j.text)||'';
    if(!fixed||fixed===textAfterNorm){
      alert('✅ '+provLbl+' kiểm tra — không sửa thêm được.');
      return;
    }
    el.value=fixed;
    if(['CauHoi','A','B','C','D','LoiGiai','HinhAnh'].includes(field)){
      refreshEditHinhAnhPreview();renderEditQuestionPreview();
    }
    alert('✅ '+provLbl+' đã sửa xong ('+(j.provider||provLbl)+'). Kiểm tra rồi bấm Lưu Sheet.');
  }catch(e){
    alert(provLbl+' lỗi: '+(e.message||e));
  }finally{
    if(btn){btn.disabled=false;btn.innerHTML=oldBtnHtml}
  }
}

// Kiểm tra client-side xem LaTeX còn lỗi rõ ràng không
function _clientLatexStillBroken(t){
  if(!t)return false;
  // Double brace tu Word - dung split tranh Jinja
  if(t.split('{').length>t.split('}').length+2)return true;
  if(/\{[<>=!]\}/.test(t))return true;
  if(/(?<!\\)\bmathrm\{/.test(t))return true;
  if(/(?<!\\)\btext\{/.test(t))return true;
  if(/\\newline/.test(t)&&/\\begin\{(aligned|array|cases)/.test(t))return true;
  if(/\$\\(?:cdot|Rightarrow|Leftrightarrow|rightarrow|to)\$/.test(t))return true;
  // Backslash + space trong math: $10\ kg$ — sai
  if(/\$[^$]*\\ [^$]*\$/.test(t))return true;
  // \J \kg \km \Pa \W \N trong $ — không phải lệnh LaTeX hợp lệ
  // Cho phép: \Delta \Sigma \Omega \Gamma \Lambda \Theta \Phi \Psi v.v.
  let greekUpper=/\\(?:Delta|Sigma|Omega|Gamma|Lambda|Theta|Pi|Phi|Psi|Xi|Upsilon|Rightarrow|Leftrightarrow)/;
  if(!greekUpper.test(t)&&/\$[^$]*\\[A-Z][a-z]{0,2}\b[^{][^$]*\$/.test(t))return true;
  return false;
}
function toggleLatexNormMenu(field){let m=document.getElementById('latexNormMenu_'+field);if(!m)return;document.querySelectorAll('.latexNormMenu').forEach(x=>{if(x!==m)x.classList.add('hide')});m.classList.toggle('hide')}
function closeLatexNormMenu(field){let m=document.getElementById('latexNormMenu_'+field);if(m)m.classList.add('hide')}
if(!window._latexNormDocClick){window._latexNormDocClick=true;document.addEventListener('click',()=>document.querySelectorAll('.latexNormMenu').forEach(m=>m.classList.add('hide')))}
function adminDapAnLettersFromForm(q){q=q||{};try{q=Object.assign({},q,readQuestionFormData())}catch(e){}let letters=['A','B','C','D'].filter(L=>String(q[L]||'').trim());return letters.length?letters:['A','B','C','D']}
function adminDsVerdictMapFromRaw(raw,q){let m={};parseDsAnswerTokens(raw||'').forEach(t=>{m[t.letter]=t.verdict});let letters=adminDapAnLettersFromForm(q);let compact=String(raw||'').toUpperCase().replace(/\u0110/g,'D').replace(/[^DS]/g,'');letters.forEach((L,i)=>{if(!m[L]&&compact[i])m[L]=compact[i]==='S'?'Sai':'Đúng'});return m}
function adminDsDapAnSerialize(map,q){return adminDapAnLettersFromForm(q).filter(L=>map[L]).map(L=>L+'='+map[L]).join(' · ')}
function adminSyncDapAnDom(v){let val=String(v||'');let el=document.getElementById('edit_DapAn');if(el)el.value=val;let raw=document.getElementById('edit_DapAnRaw');if(raw&&document.activeElement!==raw)raw.value=val;if(typeof adminRefreshDapAnUi==='function')adminRefreshDapAnUi();if(typeof renderEditQuestionPreview==='function')renderEditQuestionPreview()}
function adminSetMcqDapAnPick(letter){letter=String(letter||'').toUpperCase();if(!/^[ABCD]$/.test(letter))return;adminSyncDapAnDom(letter)}
function adminSetDsDapAnVerdict(letter,verdict){let form=readQuestionFormData();let map=adminDsVerdictMapFromRaw(val('edit_DapAn')||form.DapAn,form);map[letter]=verdict;adminSyncDapAnDom(adminDsDapAnSerialize(map,form))}
function adminRefreshDapAnUi(){let form=readQuestionFormData();let dang=normDangFormVal(form.Dang);let raw=val('edit_DapAn')||'';let box=document.getElementById('editDapAnUi');if(!box)return;if(dang==='Đúng sai'){let map=adminDsVerdictMapFromRaw(raw,form);box.innerHTML=adminDapAnLettersFromForm(form).map(L=>{let d=map[L]==='Đúng'?' adminChipOn':'';let s=map[L]==='Sai'?' adminChipOn':'';return `<div class="adminDsDapRow"><span class="adminDsDapLbl">${L}</span><button type="button" class="adminChip dsVerdictDung${d}" onclick="adminSetDsDapAnVerdict('${L}','Đúng')">Đúng</button><button type="button" class="adminChip dsVerdictSai${s}" onclick="adminSetDsDapAnVerdict('${L}','Sai')">Sai</button></div>`}).join('')}else if(dang==='Trắc nghiệm'){let cur=String(raw||'').trim().toUpperCase().match(/^([ABCD])$/)?.[1]||'';box.innerHTML=['A','B','C','D'].map(L=>{let on=cur===L?' adminChipOn':'';let dis=!String(form[L]||'').trim();return `<button type="button" class="adminChip${on}"${dis?' disabled style="opacity:.35;pointer-events:none"':''} onclick="adminSetMcqDapAnPick('${L}')">${L}</button>`}).join('')}else{box.innerHTML=''}let rawEl=document.getElementById('edit_DapAnRaw');if(rawEl&&document.activeElement!==rawEl)rawEl.value=raw}
function renderAdminDapAnField(q){q=q||{};let raw=String(q.DapAn||'').trim();let dang=normDangFormVal(q.Dang);let tools='';if(dang==='Đúng sai'){tools=`<div style="display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 5px 0"><button type="button" class="btnSmall btn2" onclick="adminSyncDapanFromLoigiai()">↳ P từ LG</button><button type="button" class="btnSmall btn2" onclick="adminFormatDsDapanEdit()">📋 Chuẩn hóa P</button></div><div id="editDapAnUi" class="adminDapAnUi adminDsDapAnUi"></div><p class="muted" style="font-size:11px;margin:4px 0 6px">Bấm <b>Đúng</b> / <b>Sai</b> từng ý A–D — hoặc gõ trực tiếp ô dưới.</p>`}else if(dang==='Trắc nghiệm'){tools=`<div id="editDapAnUi" class="adminDapAnUi adminMcqDapAnUi"></div><p class="muted" style="font-size:11px;margin:4px 0 6px">Chọn đáp án đúng <b>A / B / C / D</b>.</p>`}return `<div class="adminQuickField adminDapAnField"><label><b>${QUESTION_FORM_LABELS.DapAn}</b></label>${tools}<input type="hidden" id="edit_DapAn" value="${escAttr(raw)}"><textarea id="edit_DapAnRaw" class="adminDapAnRaw" placeholder="${dang==='Đúng sai'?'A=Đúng · B=Sai · C=Đúng · D=Sai':(dang==='Trắc nghiệm'?'A hoặc B hoặc C hoặc D':'Đáp án (TLN: số hoặc biểu thức)')}" oninput="adminSyncDapAnDom(this.value)">${escFormVal(raw)}</textarea></div>`}
function adminRerenderDapAnField(){let old=document.querySelector('.adminDapAnField');if(!old)return;let form=Object.assign({},QUESTIONS[CUR]||{},readQuestionFormData());form.DapAn=val('edit_DapAn')||form.DapAn;let tmp=document.createElement('div');tmp.innerHTML=renderAdminDapAnField(form);old.replaceWith(tmp.firstElementChild);adminRefreshDapAnUi()}
function renderQuestionFormField(f,q){let raw=String((q&&q[f])||'');if(f==='TrangThai')return renderAdminChipGroup(f,ADMIN_REVIEW_OPTS,raw,normReviewFormVal);if(f==='QuyenTruyCap')return renderAdminChipGroup(f,ADMIN_QUYEN_OPTS,raw,normQuyenFormVal);if(f==='MucDo'){let chips=ADMIN_MUCDO_OPTS.map(v=>{let on=normMucDoFormVal(raw)===v?' adminChipOn':'';return `<button type="button" class="adminChip ${mucdoBadgeClass(v)}${on}" data-chip-field="MucDo" data-chip-value="${v}" onclick="setAdminChip('MucDo','${v}')">${v}</button>`}).join('');let cur=normMucDoFormVal(raw);return `<div class="adminQuickField"><label><b>${QUESTION_FORM_LABELS.MucDo}</b></label><input type="hidden" id="edit_MucDo" value="${escAttr(cur)}"><div class="adminChipRow">${chips}<button type="button" class="adminChip${cur?'':' adminChipOn'}" data-chip-field="MucDo" data-chip-value="" onclick="setAdminChip('MucDo','')">—</button></div></div>`}if(f==='Dang')return renderAdminChipGroup(f,ADMIN_DANG_OPTS,raw,normDangFormVal);if(f==='NangLucVatLy')return renderAdminChipGroup(f,ADMIN_NLVL_OPTS,raw,normNangLucVatLyFormVal);if(ADMIN_META_PICK_FIELDS.includes(f))return renderAdminMetaPickField(f,q);if(f==='DangBaiTap')return renderAdminDangBaiTapField(q);if(f==='DapAn')return renderAdminDapAnField(q);if(f==='HinhAnh'){let parsed=parseHinhanhCellClient(raw);let imgShow=parsed.img&&!/^tikzraw:/i.test(parsed.img)?parsed.img:'';let tikzShow=parsed.tikz||'';return `<div class="adminImgField"><label><b>${QUESTION_FORM_LABELS.HinhAnh}</b></label><div style="font-size:11px;color:#64748b;margin:4px 0 6px">📐 <b>TikZ/hình hiện đúng chỗ ghi</b> (K, A–D, R). Cột T = lưu Sheet + preview; trong R gõ <code>[HINH]</code> để chèn ảnh T. <code>[LG-ONLY]</code> = không hiện T trên đề.</div><textarea style="min-height:120px;font-family:monospace;font-size:11px" id="edit_Tikz" oninput="refreshEditHinhAnhPreview();renderEditQuestionPreview()" placeholder="\\begin{tikzpicture}...\\end{tikzpicture}">${escFormVal(tikzShow)}</textarea><div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 5px 0"><button type="button" id="btn_ai_generate_tikz" class="btnSmall" style="background:#7c3aed!important;color:#fff!important" onclick="adminAiGenerateTikz()" title="Gemini/GPT tạo mã TikZ minh họa từ đề + LG">🤖 AI vẽ TikZ</button><button type="button" class="btnSmall btn2" onclick="adminRerenderTikz()">🔄 Vẽ lại</button><button type="button" class="btnSmall" style="background:#059669!important;color:#fff!important" onclick="adminInsertHinhToLoigiai()">➡ Chỉ LG</button><button type="button" class="btnSmall btn2" onclick="adminDownloadHinhAnh()">💾 Lưu ảnh (img)</button><button type="button" class="btnSmall btn2" onclick="adminPasteImageUrl()">📋 Dán link Drive</button><span class="muted" style="font-size:11px;align-self:center">Tải img → upload Anh_Luyen_De → dán link</span></div><textarea style="min-height:56px" id="edit_HinhAnh" oninput="refreshEditHinhAnhPreview();renderEditQuestionPreview()" placeholder="Link thumbnail Drive (tùy chọn — mã TikZ vẫn giữ ở dòng trên)">${escFormVal(imgShow)}</textarea><div id="edit_HinhAnhPreview" class="adminImgPreview"></div><div id="editSolutionFigHint"></div></div>`}let h=(f=='CauHoi'||f=='LoiGiai')?'150px':((f=='MaDe'||f=='ID'||f=='DapAn'||f=='SaiSo')?'56px':'78px');let aiTools=''; if(f==='LoiGiai'){aiTools=`<div class="adminLgAiTools"><div style="font-size:11px;color:#64748b;margin-bottom:4px">AI chỉnh LG (Gemini trước): TN = chỉ giải phương án đúng · Đ/S = giải từng ý A–D</div><div style="display:flex;gap:6px;flex-wrap:wrap;margin:0 0 4px 0"><button type="button" id="btn_ai_lg_tn" class="btnSmall" onclick="aiAdminFixLoigiai('tn')">📝 LG Trắc nghiệm</button><button type="button" id="btn_ai_lg_ds" class="btnSmall" onclick="aiAdminFixLoigiai('ds')">📝 LG Đúng/Sai</button><button type="button" id="btn_ai_lg_tln" class="btnSmall" onclick="aiAdminFixLoigiai('tln')">📝 LG Trả lời ngắn</button><button type="button" class="btnSmall btn2" onclick="normalizeLatexField('LoiGiai','loigiai_abcd')" title="Chuẩn hóa R thành A. Đúng — / B. Sai — từng ý (TN &amp; Đ/S)">📋 LG → ABCD</button><button type="button" id="btn_ai_rewrite_LoiGiai" class="btnSmall" onclick="aiRewriteLatexField('LoiGiai')">🔤 Sửa LaTeX (AI)</button>${renderEditLatexAiSelect()}${renderLatexNormToolbar('LoiGiai')}</div><span style="font-size:11px;color:#64748b">Bôi đen đoạn → ▾ từng bước · chưa lưu Sheet</span></div>`}else if(['CauHoi','A','B','C','D'].includes(f)){let rectxBtn=`<button type="button" id="btn_ai_recontext_${f}" class="btnSmall" style="background:#0d9488!important;color:#fff!important" onclick="aiRecontextDebaiField('${f}')" title="Đổi ngữ liệu ${f==='CauHoi'?'đề bài':'phương án '+f} — giữ số liệu & công thức">🎭 Đổi ngữ liệu</button>`;let splitBtn=f==='A'?`<button type="button" class="btnSmall btn2" onclick="adminSplitAbcdFromForm()" title="Tách chuỗi A. … B. … C. … D. … thành 4 ô riêng">✂ Tách A–D</button>`:'';aiTools=`<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:4px 0 5px 0">${rectxBtn}${splitBtn}<button type="button" id="btn_ai_rewrite_${f}" class="btnSmall" onclick="aiRewriteLatexField('${f}')">🤖 AI viết lại LaTeX</button>${renderEditLatexAiSelect()}${renderLatexNormToolbar(f)}<span style="font-size:11px;color:#64748b">🎭 đổi ngữ cảnh · Bôi đen → ▾ từng bước</span></div>`} return `<div><label><b>${QUESTION_FORM_LABELS[f]||f}</b></label>${aiTools}<textarea style="min-height:${h}" id="edit_${f}">${escFormVal(raw)}</textarea></div>`}
function renderQuestionForm(q){ensureEditAdminPreviewBar();document.getElementById('editForm').innerHTML=QUESTION_FORM_FIELDS.map(f=>renderQuestionFormField(f,q)).join('');['QuyenTruyCap','TrangThai','MucDo','Dang','NangLucVatLy'].forEach(syncAdminChipGroup);syncDsEditFormFields(q);adminExtractTikzFromFormFields();refreshEditHinhAnhPreview();bindEditFormLivePreview();adminRefreshDapAnUi();syncAdminSolutionFigHint();if(typeof syncEditDsRewriteButton==='function')syncEditDsRewriteButton()}
async function adminRerenderTikz(){refreshEditHinhAnhPreview();renderEditQuestionPreview()}
async function adminAiGenerateTikz(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  let ctx=readQuestionFormData();
  if(!String(ctx.CauHoi||'').trim()&&!String(ctx.LoiGiai||'').trim()){alert('Cần có đề bài hoặc lời giải để AI vẽ hình.');return}
  let tzEl=document.getElementById('edit_Tikz');
  let existing=tzEl?String(tzEl.value||'').trim():'';
  let extra=prompt('Yêu cầu thêm (tùy chọn):\nVD: đồ thị v–t, sơ đồ lực, mạch điện, hình tam giác…','')||'';
  if(existing){if(!confirm('Đã có TikZ — AI sẽ tạo/sửa lại mã.\n\nChưa lưu Sheet. Tiếp tục?'))return}
  else if(!confirm('AI ('+adminAiProviderLabel(adminChosenAiProvider())+') sẽ tạo mã TikZ minh họa câu này.\n\nChưa lưu Sheet. Tiếp tục?'))return
  let btn=document.getElementById('btn_ai_generate_tikz');
  let oldBtn=btn?btn.textContent:'';
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳ AI vẽ...'}
    let j=await adminAiFetch('/api/admin/ai-generate-tikz',{context:ctx,extra_hint:extra,existing_tikz:existing,mode:existing?'rewrite':'new'},{timeoutMs:65000,admin_ai_provider:adminChosenAiProvider(),admin_ai_allow_gpt_fallback:true});
    if(j.tikz&&tzEl){
      tzEl.value=j.tikz;
      refreshEditHinhAnhPreview();renderEditQuestionPreview();
      let warn=j.compile_warning?('\n\n⚠ '+j.compile_warning):'';
      alert('✅ AI đã tạo TikZ ('+(j.provider||'AI')+'). Bấm 🔄 Vẽ lại để xem preview.'+warn);
    }else alert('AI chưa trả TikZ hợp lệ.');
  }catch(e){alert('AI vẽ TikZ lỗi: '+(e.message||e))}
  finally{if(btn){btn.disabled=false;btn.textContent=oldBtn||'🤖 AI vẽ TikZ'}}
}
async function adminDownloadHinhAnh(){let raw=adminMergedHinhAnhFromForm();let src=adminPreviewHinhAnhSrc();if(!src){alert('Chưa có ảnh.\n\nNhập mã TikZ hoặc dán link ảnh vào ô Hình ảnh.');return}if(/^tikzraw:/i.test(src)){try{let j=await tikzRenderFetch(src);if(j&&j.ok&&j.url)src=normalizeImageSrcClient(j.url);else{alert('Chưa vẽ được TikZ: '+(j&&j.error||''));return}}catch(e){alert('Lỗi vẽ TikZ: '+(e.message||e));return}}let url=src;if(url.startsWith('/'))url=location.origin+url;let fname='img.png';let m=String(raw||src).match(/([A-Za-z0-9_.-]+\.(png|jpe?g|gif|webp))$/i);if(m)fname=m[1].replace(/[^\w.\-]+/g,'_');if(!/^img/i.test(fname))fname='img_'+fname;try{let resp=await fetch(url,{credentials:'same-origin'});if(!resp.ok)throw new Error('HTTP '+resp.status);let blob=await resp.blob();let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=fname;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),500);alert('Đã tải '+fname+'\n\n1. Kéo file lên folder Anh_Luyen_De trên Drive\n2. Chuột phải → Lấy liên kết\n3. Dán vào ô link Drive (giữ mã TikZ ở trên) → Lưu Sheet')}catch(e){window.open(url,'_blank');alert('Mở ảnh tab mới — chuột phải → Lưu ảnh thành img.png\n\nRồi upload Drive và dán link cột T.')}}
async function adminPasteImageUrl(){try{let txt=await navigator.clipboard.readText();if(!String(txt||'').trim()){alert('Clipboard trống.');return}let el=document.getElementById('edit_HinhAnh');if(el){el.value=String(txt).trim();refreshEditHinhAnhPreview();renderEditQuestionPreview()}}catch(e){let el=document.getElementById('edit_HinhAnh');if(el){el.focus();alert('Bấm vào ô Hình ảnh rồi Ctrl+V dán link.')}}}
function readQuestionFormData(){adminExtractTikzFromFormFields();let data={};for(let f of QUESTION_FORM_FIELDS){let el=document.getElementById('edit_'+f);data[f]=el?(el.value||''):''}data.HinhAnh=adminMergedHinhAnhFromForm();return data}
function formatDsDapanForEdit(text,q){let tokens=parseDsAnswerTokens(text||'');let letters=['A','B','C','D'].filter(L=>q&&q[L]);if(tokens.length>=2)return tokens.filter(t=>!letters.length||letters.includes(t.letter)).map(t=>`${t.letter}=${t.verdict}`).join(' · ');return String(text||'')}
function adminFormatDsDapanEdit(){let form=Object.assign({},QUESTIONS[CUR]||{},readQuestionFormData());let cur=val('edit_DapAn')||'';let fmt=formatDsDapanForEdit(cur,form);if(fmt&&fmt!==cur){adminSyncDapAnDom(fmt);alert('✅ Đã chuẩn hóa cột P (A=Đúng · B=Sai …).');return true}return false}
function adminSyncDapanFromLoigiai(){let lgEl=document.getElementById('edit_LoiGiai');if(!lgEl)return;let form=Object.assign({},QUESTIONS[CUR]||{},readQuestionFormData());let sync=dsDapAnFromSolutionText(lgEl.value,form);if(sync){adminSyncDapAnDom(sync);if(adminFormatDsDapanEdit())return;adminSyncDapAnDom(sync);alert('✅ Đã lấy P từ lời giải R.');return}alert('Chưa đọc được Đúng/Sai từng ý A–D trong R.');}
function syncDsEditFormFields(q){q=q||{};if(normDangFormVal(q.Dang)!=='Đúng sai')return;let merged=Object.assign({},q);try{merged=Object.assign(merged,readQuestionFormData())}catch(e){}let daEl=document.getElementById('edit_DapAn');let lgEl=document.getElementById('edit_LoiGiai');if(daEl){let fmt=formatDsDapanForEdit(daEl.value||merged.DapAn,merged);if(fmt){adminSyncDapAnDom(fmt);merged.DapAn=fmt}}if(lgEl){let lg=String(lgEl.value||'').trim();if(lg){let fixed=buildDsSolutionCopyText(lg,merged,true);if(fixed)lgEl.value=fixed}}}
function autoSyncDsLoigiaiAbcd(updates,q){try{q=Object.assign({},q||{},updates||{});if(normDangFormVal(q.Dang)!=='Đúng sai')return updates;let da=String((updates&&updates.DapAn)!=null?updates.DapAn:(q.DapAn||'')).trim();if(da){let fmt=formatDsDapanForEdit(da,q);if(fmt)updates.DapAn=fmt}let lg=String((updates&&updates.LoiGiai)||'').trim();if(!lg.trim()){if(updates.DapAn)adminSyncDapAnDom(updates.DapAn);return updates}q=Object.assign({},q,updates);let fixed=buildDsSolutionCopyText(lg,q,true);if(fixed)updates.LoiGiai=fixed;if(updates.DapAn)adminSyncDapAnDom(updates.DapAn);let le=document.getElementById('edit_LoiGiai');if(le&&updates.LoiGiai)le.value=updates.LoiGiai;}catch(e){}return updates}
async function normalizeLatexField(field,action){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  action=String(action||'full');
  let el=document.getElementById('edit_'+field);
  if(!el){alert('Không tìm thấy ô.');return}
  let oldText=String(el.value||'');
  if(!oldText.trim()){alert('Ô đang trống.');return}
  let selStart=el.selectionStart,selEnd=el.selectionEnd;
  let useSel=(selStart!=null&&selEnd!=null&&selEnd>selStart);
  let btn=document.getElementById('btn_norm_'+field);
  let oldBtn=btn?btn.textContent:'';
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳...'}
    let payload={field,text:useSel?oldText.substring(selStart,selEnd):oldText,action,context:readQuestionFormData()};
    if(useSel)payload.selection={start:selStart,end:selEnd,full:oldText};
    let j=await api('/api/admin/normalize-latex',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(j&&j.text!=null){
      el.value=j.text;
      if(field==='LoiGiai'){
        let form=Object.assign({},QUESTIONS[CUR]||{},readQuestionFormData(),{LoiGiai:el.value});
        if(normDangFormVal(form.Dang)==='Đúng sai'||action==='loigiai_abcd')syncDsEditFormFields(form);
      }
      if(['CauHoi','A','B','C','D','LoiGiai','HinhAnh'].includes(field)){
        refreshEditHinhAnhPreview();
        renderEditQuestionPreview();
      }
      let step=j.action_label||action;
      let seg=j.segment_only?' (chỉ đoạn bôi đen)':'';
      alert(j.still_broken?'⚠ '+step+seg+' — vẫn còn LaTeX lệch.':(j.changed?'✅ '+step+seg:'✓ '+step+seg+' — không cần sửa.'))
    }
  }catch(e){alert('Chuẩn hóa lỗi: '+(e.message||e))}
  finally{if(btn){btn.disabled=false;btn.textContent=oldBtn||'⚡ Chuẩn hóa'}}
}
async function aiRewriteLatexField(field){
  if(!USER.is_admin){
    alert('Chỉ ADMIN được dùng AI viết lại nội dung đề.');
    return;
  }

  let el=document.getElementById('edit_'+field);
  if(!el){
    alert('Không tìm thấy ô cần sửa.');
    return;
  }

  let oldText=String(el.value||'');
  if(!oldText.trim()){
    alert('Ô này đang trống.');
    return;
  }

  let btn=document.getElementById('btn_ai_rewrite_'+field);
  let oldBtn=btn?btn.textContent:'';
  let prov=adminEditAiProvider();
  let provLbl=prov==='ANTHROPIC'?'Claude':(prov==='OPENAI'?'GPT':'Gemini');

  if(!confirm('AI ('+provLbl+') sẽ viết lại nội dung ô '+field+' cho đúng LaTeX.\n\nNội dung chỉ thay trong ô nhập, chưa lưu Google Sheet. Tiếp tục?')) return;

  try{
    if(btn){
      btn.disabled=true;
      btn.textContent='⏳ AI đang sửa...';
    }

    let payload={
      field:field,
      text:oldText,
      context:readQuestionFormData(),
      admin_ai_provider:prov,
      admin_ai_allow_gpt_fallback:true
    };
    let antKey=_loadAnthropicKey();
    if(antKey)payload.anthropic_key=antKey;

    let j=await adminApiPost('/api/ai/rewrite-latex',payload,{timeoutMs:50000,admin_ai_provider:prov,admin_ai_allow_gpt_fallback:true});

    if(j.text){
      el.value=j.text;
      if(['CauHoi','A','B','C','D','LoiGiai','HinhAnh'].includes(field)){
        refreshEditHinhAnhPreview();renderEditQuestionPreview();
      }
      alert('Đã viết lại bằng '+(j.provider||provLbl)+'.\nThầy kiểm tra lại rồi bấm Lưu vào Google Sheet.');
    }else{
      alert('AI không trả về nội dung.');
    }
  }catch(e){
    alert('AI sửa LaTeX lỗi: '+(e.message||e));
  }finally{
    if(btn){
      btn.disabled=false;
      btn.textContent=oldBtn||'🤖 AI viết lại LaTeX';
    }
  }
}
async function aiRecontextDebaiField(field){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  if(!adminEnsureAiReady())return
  field=String(field||'CauHoi');
  if(!['CauHoi','A','B','C','D'].includes(field)){alert('Chỉ dùng cho K hoặc phương án A–D.');return}
  let fieldLbl=field==='CauHoi'?'đề bài (K)':'phương án '+field;
  let el=document.getElementById('edit_'+field);
  if(!el){alert('Không tìm thấy ô '+fieldLbl+'.');return}
  let oldText=String(el.value||'').trim();
  if(!oldText){alert('Ô '+fieldLbl+' đang trống.');return}
  let selStart=el.selectionStart,selEnd=el.selectionEnd;
  let useSel=(selStart!=null&&selEnd!=null&&selEnd>selStart);
  let workText=useSel?oldText.substring(selStart,selEnd):oldText;
  let prov=adminEditAiProvider();
  let provLbl=adminAiProviderLabel(prov);
  let themeHint=field==='CauHoi'?'':' (cùng ngữ liệu với đề bài)';
  let theme=prompt('Gợi ý ngữ liệu/bối cảnh mới'+themeHint+' (tùy chọn — Enter để AI tự chọn):\n\nVD: vật rơi tự do, xe đạp, mạch điện, thể thao…','')||'';
  if(theme==null)return
  if(!confirm('AI ('+provLbl+') sẽ đổi NGỮ LIỆU '+fieldLbl+(useSel?' (đoạn bôi đen)':'')+' — GIỮ NGUYÊN số liệu & công thức.\n\nChưa lưu Sheet. Tiếp tục?'))return
  let btn=document.getElementById('btn_ai_recontext_'+field);
  let oldBtn=btn?btn.textContent:'';
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳ Đổi ngữ liệu…'}
    let payload={field:field,text:workText,context:readQuestionFormData(),theme_hint:theme,admin_ai_allow_gpt_fallback:true};
    let j=await adminApiPost('/api/ai/recontext-debai',payload,{timeoutMs:55000,admin_ai_provider:prov,admin_ai_allow_gpt_fallback:true});
    if(j.text){
      if(useSel){
        el.value=oldText.substring(0,selStart)+j.text+oldText.substring(selEnd);
      }else{
        el.value=j.text;
      }
      refreshEditHinhAnhPreview();renderEditQuestionPreview();
      let warn=(j.numeric_warnings&&j.numeric_warnings.length)?('\n\n⚠ Kiểm tra số liệu: '+j.numeric_warnings.join(', ')):'';
      alert('✅ Đã đổi ngữ liệu '+fieldLbl+' ('+(j.provider||provLbl)+').'+warn+'\n\nXem lại rồi bấm Lưu Sheet.');
    }else{
      alert('AI không trả về nội dung mới.');
    }
  }catch(e){
    alert('Đổi ngữ liệu lỗi: '+(typeof apiNetworkErrorMsg==='function'?apiNetworkErrorMsg(e):(e.message||e)));
  }finally{
    if(btn){btn.disabled=false;btn.textContent=oldBtn||'🎭 Đổi ngữ liệu'}
  }
}
async function aiAdminFixLoigiai(formatMode){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  let el=document.getElementById('edit_LoiGiai');
  if(!el){alert('Không tìm thấy ô Lời giải.');return}
  let oldText=String(el.value||'');
  if(!oldText.trim()){alert('Lời giải đang trống.');return}
  formatMode=String(formatMode||'auto').toLowerCase();
  let labels={tn:'Trắc nghiệm',ds:'Đúng/Sai',tln:'Trả lời ngắn',auto:'tự động'};
  let btnId='btn_ai_lg_'+formatMode;
  let btn=document.getElementById(btnId);
  let oldBtn=btn?btn.textContent:'';
  if(!confirm('AI (Gemini trước) sẽ chỉnh lời giải theo định dạng '+ (labels[formatMode]||formatMode)+'.\n\nChỉ thay trong ô nhập, chưa lưu Sheet. Tiếp tục?'))return;
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳...'}
    let payload={text:oldText,context:readQuestionFormData(),format_mode:formatMode};
    let j=await adminAiFetch('/api/admin/ai-fix-loigiai',payload);
    if(j.text){
      el.value=j.text;
      if(formatMode==='ds'||normDangFormVal(readQuestionFormData().Dang)==='Đúng sai'){
        let updates=autoSyncDsLoigiaiAbcd({LoiGiai:j.text},readQuestionFormData());
        if(updates&&updates.LoiGiai)el.value=updates.LoiGiai;
      }
      refreshEditHinhAnhPreview();renderEditQuestionPreview();
      alert('Đã chỉnh LG ('+(labels[formatMode]||formatMode)+') bằng '+(j.provider||'AI')+'.\nKiểm tra rồi bấm Lưu.');
    }
  }catch(e){alert('AI chỉnh lời giải lỗi: '+e.message)}
  finally{if(btn){btn.disabled=false;btn.textContent=oldBtn||('📝 LG '+(labels[formatMode]||''))}}
}
function renderEditHintResult(j){
  let box=document.getElementById('editHintResult');
  if(!box)return;
  j=j||HINT_BY_Q[CUR]||{};
  if(!j.hint&&!j.admin_review){box.classList.add('hide');box.innerHTML='';return}
  box.classList.remove('hide');
  let prov=j.provider_used||j.provider_mode||'';
  let head='<div style="font-weight:800;margin-bottom:6px">Kết quả soát đề'+(prov?(' · '+esc(prov)):'')+'</div>';
  let body=j.hint?('<div style="white-space:pre-wrap">'+esc(String(j.hint).split('📋 Tham chiếu Sheet')[0].trim().slice(0,4000))+'</div>'):'<div class="muted">Chưa có nội dung.</div>';
  box.innerHTML=head+body+renderEditHintDbtSuggest(j);
}
function renderEditHintDbtSuggest(j){
  j=j||{};
  if(j.dbt_suggest_loading)return '<div class="muted" style="margin-top:8px;padding-top:8px;border-top:1px dashed var(--border)">🏷️ Đang lấy gợi ý Dạng bài tập…</div>';
  let dj=j.dbt_suggest;
  if(!dj)return '';
  let dbt=String(dj.DangBaiTap||'').trim();
  if(!dbt)return dj.error?('<div class="muted" style="margin-top:8px;padding-top:8px;border-top:1px dashed var(--border)">🏷️ Gợi ý Dạng bài tập: chưa nhận được ('+esc(dj.error)+')</div>'):'';
  let cur=String(dj.from||'').trim();
  let reason=String(dj.reason||'').trim();
  let conf=String(dj.confidence||'').trim();
  let sameAsCur=cur&&normText(cur)===normText(dbt);
  let fromToLine=sameAsCur
    ?'✓ Dạng hiện tại «'+esc(dbt)+'» đã khớp AI — không cần đổi.'
    :(cur?('Hiện tại: «'+esc(cur)+'»  →  AI gợi ý: «'+esc(dbt)+'»'):('AI gợi ý (câu chưa có Dạng): «'+esc(dbt)+'»'));
  return '<div class="muted" style="margin-top:8px;padding-top:8px;border-top:1px dashed var(--border)">🏷️ Gợi ý Dạng bài tập (AI)'+(conf?' · tin cậy '+esc(conf):'')+':<br><b>'+fromToLine+'</b>'+(reason?'<br>Lý do: '+esc(reason):'')+adminDbtAiSyncNote(dj)+'<br><span style="font-size:11px">Chỉ hiển thị — chưa ghi cột H. Xem ô «Dạng bài tập» ở form bên dưới rồi tự chọn/lưu như hiện tại.</span></div>';
}
function applyEditHintField(field){
  if(!USER.is_admin)return;
  let v=hintFieldValue(field);
  if(!v){alert(field==='DapAn'?'Chưa tách được đáp án AI.':'Chưa có lời giải AI.');return}
  if(field==='DapAn'){adminSyncDapAnDom(v);return}
  let el=document.getElementById('edit_'+field);
  if(el){
    el.value=v;
    if(field==='LoiGiai'){
      let updates=autoSyncDsLoigiaiAbcd({LoiGiai:v},readQuestionFormData());
      if(updates&&updates.LoiGiai)el.value=updates.LoiGiai;
    }
  }
}
function applyEditHintAll(){
  if(!USER.is_admin)return;
  let da=hintFieldValue('DapAn');
  let lg=hintFieldValue('LoiGiai');
  if(!da&&!lg){alert('Chưa có kết quả soát đề — bấm 🔍 Soát đề trước.');return}
  if(da)adminSyncDapAnDom(da);
  if(lg){
    let el=document.getElementById('edit_LoiGiai');
    if(el){
      el.value=lg;
      let updates=autoSyncDsLoigiaiAbcd({LoiGiai:lg},readQuestionFormData());
      if(updates&&updates.LoiGiai)el.value=updates.LoiGiai;
    }
  }
}
async function requestHintFromEditModal(){
  if(!isAdminViewer())return;
  if(HINT_LOADING||SIMILAR_LOADING)return;
  if(!adminEnsureAiReady())return
  saveCurrent();
  let qIdx=CUR;
  setHintLoading(true,qIdx);
  let box=document.getElementById('editHintResult');
  if(box){box.classList.remove('hide');box.innerHTML='<div class="hintLoadingPanel"><div class="hintSpinBig"></div><div><b>Đang soát đề AI ('+esc(adminAiProviderLabel(adminChosenAiProvider()))+')…</b><div class="muted" style="margin-top:4px;font-size:12px">'+esc(adminReviewLoadingNote())+'</div></div></div>'}
  try{
    let hintBody={sid:SID,index:qIdx,answer:ANSWERS[qIdx],...quizRestorePayload(),admin_review_mode:getAdminReviewMode()};
    let j=await adminAiFetch('/api/hint',hintBody,{timeoutMs:85000});
    HINT_BY_Q[qIdx]=j;
    if(j.admin_review)ADMIN_HINT_SAVED[qIdx]=false;
    renderEditHintResult(j);
    syncQuestionModalChrome();
    if(j.admin_review)fetchDbtSuggestForEditHint(qIdx);
  }catch(e){
    if(box){box.innerHTML='<div class="muted">❌ '+esc(e.message||e)+'</div>'}
  }finally{
    setHintLoading(false,qIdx);
    syncEditHintButtonLabel();
  }
}
async function fetchDbtSuggestForEditHint(qIdx){
  let j=HINT_BY_Q[qIdx];
  if(!j||!j.admin_review)return;
  j.dbt_suggest_loading=true;
  if(CUR===qIdx)renderEditHintResult(j);
  try{
    let q=readQuestionFormData();
    q.Dang=normDangFormVal(q.Dang||'');
    let curDbt=String(q.DangBaiTap||'').trim();
    let dj=await adminApiPost('/api/ai/detect-dangbaitap-update',{question:q,dangbaitap_suggestions:adminDangBaiTapSuggestions(),save:false});
    dj.from=curDbt;
    j.dbt_suggest=dj;
  }catch(e){
    j.dbt_suggest={error:String((e&&e.message)||e)};
  }finally{
    j.dbt_suggest_loading=false;
    HINT_BY_Q[qIdx]=j;
    if(CUR===qIdx)renderEditHintResult(j);
  }
}
function syncQuestionModalChrome(){let isAdd=QUESTION_MODAL_MODE==='add';let t=document.getElementById('editModalTitle');if(t)t.textContent=isAdd?'ADMIN: Thêm câu hỏi mới':'ADMIN: Sửa câu hỏi';let del=document.getElementById('btnDeleteQuestion');if(del)del.classList.toggle('hide',isAdd);let save=document.getElementById('btnSaveQuestion');if(save)save.textContent=isAdd?'➕ Thêm vào Google Sheet':'✅ Lưu vào Google Sheet (sau khi kiểm tra)';let soat=document.getElementById('editAdminSoatBar');if(soat)soat.classList.toggle('hide',isAdd||!isAdminViewer());syncAdminReviewModeUI();syncEditHintButtonLabel();if(typeof syncEditDsRewriteButton==='function')syncEditDsRewriteButton();if(isAdd&&ADMIN_SIMILAR_EDIT_TIPS){let er=document.getElementById('editHintResult');if(er){er.classList.remove('hide');er.innerHTML=(typeof buildAdminVariantTipsHtml==='function'?buildAdminVariantTipsHtml(ADMIN_SIMILAR_EDIT_TIPS):'')+'<div class="muted" style="margin-top:8px;font-size:12px">Đã điền câu tương tự vào form <b>Thêm mới</b>. Kiểm tra rồi bấm <b>➕ Thêm vào Google Sheet</b>.</div>'}}else if(!isAdd&&isAdminViewer())renderEditHintResult(HINT_BY_Q[CUR]);let note=document.getElementById('editModalNote');if(note){if(isAdd&&ADMIN_SIMILAR_EDIT_TIPS)note.innerHTML='📝 Câu tương tự AI đã điền sẵn. Kiểm tra đáp án/lời giải → bấm <b>➕ Thêm vào Google Sheet</b>.';else if(isAdd)note.textContent='Dán cả câu (Ctrl+V) ở khung trên → Tách vào form → chọn TN/Đ/S/TLN → xem trước + ảnh → Lưu Sheet.';else if(adminHintNeedsSave())note.textContent='Soát đề ở trên → kiểm tra P/R → bấm → P / → R hoặc 📋 Điền P/R → Lưu Sheet.';else note.textContent='Soát đề AI nằm ngay trên form. Xóa liên tiếp được — chỉ Đồng bộ khi sửa trực tiếp trên Google Sheet.'}}

/* ==========================================================================
 * [JS-ADMIN-EDIT] Sửa / thêm câu hỏi → Google Sheet Cau_Hoi
 * --------------------------------------------------------------------------
 * Mở form:  openEdit()           — từ btnQuizEdit / btnEdit / jumpToIdInQuiz
 *           openEditWithHint()   — sau Soát đề GPT, điền sẵn P/R từ AI
 *           openAddQuestion()    — thêm câu mới cùng đề
 * Lưu:      saveEdit() / saveAddQuestion()  — API /api/admin/save-question
 * HTML:     #modal, #edit_* fields, #btnSaveQuestion
 * ========================================================================== */
function ensureQuizAdminAiInternetButton(){if(!isAdminViewer())return;let parent=document.getElementById('quizAdminTools');if(!parent||document.getElementById('btnQuizAdminAiInternet'))return;let mob=typeof isMobileQuizUI==='function'&&isMobileQuizUI();let b=document.createElement('button');b.type='button';b.id='btnQuizAdminAiInternet';b.className='btn2 googleAiModeBtn';b.textContent=mob?'🌐 Net':'🌐 AI Internet';b.title='AI Internet — xem prompt/LaTeX câu hiện tại, không tốn quota Gemini/GPT của app';b.onclick=function(){if(typeof openGoogleAiMode==='function')openGoogleAiMode();else if(typeof openAdminAiInternetFallback==='function')openAdminAiInternetFallback({field:'LoiGiai'},'/manual-ai-internet')};parent.appendChild(b)}
function ensureEditAiInternetButton(){let bar=document.getElementById('editAiRepairBar');if(!bar||document.getElementById('btnEditAiInternetRepair'))return;let b=document.createElement('button');b.type='button';b.id='btnEditAiInternetRepair';b.className='btnGreen';b.textContent='🌐 AI Internet sửa';b.title='Mở prompt Google AI Mode, không tốn quota Gemini/GPT của app';b.onclick=function(){openAdminAiInternetFallback({field:'LoiGiai'},'/manual-ai-internet')};bar.insertBefore(b,bar.firstChild)}
function openEdit(){if(!USER.is_admin){alert('Chỉ ADMIN.');return}QUESTION_MODAL_MODE='edit';ADMIN_SIMILAR_EDIT_TIPS=null;renderQuestionForm(QUESTIONS[CUR]||{});syncQuestionModalChrome();ensureEditAiInternetButton();syncEditDsRewriteButton();document.getElementById('modal').classList.remove('hide')}

function currentLatexDefaults(){
  let q=(QUESTIONS&&QUESTIONS.length)?(QUESTIONS[CUR]||{}):{};
  return {
    MaDe:q.MaDe||CURRENT_MADE||'',
    Mon:val('latexDefMon')||q.Mon||'',
    Lop:val('latexDefLop')||q.Lop||'',
    Chuong:val('latexDefChuong')||q.Chuong||'',
    BaiHoc:val('latexDefBaiHoc')||q.BaiHoc||q.De||'',
    DangBaiTap:val('latexDefDangBaiTap')||q.DangBaiTap||'',
    BoDe:val('latexDefBoDe')||q.BoDe||'',
    De:val('latexDefDe')||q.De||'',
    MucDo:val('latexDefMucDo')||q.MucDo||'',
    QuyenTruyCap:val('latexDefQuyen')||q.QuyenTruyCap||'VIP',
    Diem:'1'
  };
}
function setLatexImportStatus(msg,err=false){
  let el=document.getElementById('latexImportStatus');
  if(el){el.textContent=msg||'';el.style.color=err?'#991b1b':''}
}
function latexImportScopeData(){
  return {
    Mon:val('latexDefMon')||'',
    Lop:val('latexDefLop')||'',
    Chuong:val('latexDefChuong')||'',
    BaiHoc:val('latexDefBaiHoc')||'',
    BoDe:val('latexDefBoDe')||'',
    De:val('latexDefDe')||'',
    DangBaiTap:val('latexDefDangBaiTap')||''
  };
}
function latexImportRefreshDbtList(){
  let sel=document.getElementById('latexDefDangBaiTap_pick');
  let inp=document.getElementById('latexDefDangBaiTap');
  if(!sel||!inp||typeof adminDangBaiTapOptions!=='function'||typeof adminDbtRebuildSelect!=='function')return;
  let cur=String(inp.value||'').trim();
  let pack=adminDangBaiTapOptions(Object.assign({},latexImportScopeData(),{DangBaiTap:cur}));
  let built=adminDbtRebuildSelect(pack,cur);
  sel.innerHTML=built.optHtml;
  if(built.match){sel.value=built.match;inp.value=built.match;}
  else if(cur){sel.value='__custom__';}
  else{sel.value='';}
  let scopeEl=document.getElementById('latexDefDangBaiTap_scope');
  if(scopeEl)scopeEl.textContent=pack.scopeLabel||'';
}
function latexImportDbtPickChange(){
  let sel=document.getElementById('latexDefDangBaiTap_pick');
  let inp=document.getElementById('latexDefDangBaiTap');
  if(!sel||!inp)return;
  let v=String(sel.value||'');
  if(v==='__custom__'){inp.focus();return;}
  if(v)inp.value=v;else inp.value='';
}
function latexImportDbtInputChange(){
  let sel=document.getElementById('latexDefDangBaiTap_pick');
  let inp=document.getElementById('latexDefDangBaiTap');
  if(!sel||!inp)return;
  let cur=String(inp.value||'').trim();
  if(!cur){sel.value='';return;}
  let opts=[];
  for(let i=0;i<sel.options.length;i++){let v=sel.options[i].value;if(v&&v!=='__custom__')opts.push(v);}
  let m=typeof adminDbtFindMatch==='function'?adminDbtFindMatch(cur,opts):'';
  if(m&&normText(cur)===normText(m))sel.value=m;else sel.value='__custom__';
}
window.latexImportRefreshDbtList=latexImportRefreshDbtList;
function openLatexImportModal(){
  if(!USER.is_admin){alert('Chỉ ADMIN.');return}
  let inQuiz=!!(document.getElementById('quiz')&&!document.getElementById('quiz').classList.contains('hide'));
  let q=(inQuiz&&QUESTIONS&&QUESTIONS.length)?(QUESTIONS[CUR]||{}):{};
  let scope={Mon:q.Mon||val('fMon')||val('latexDefMon'),Lop:q.Lop||val('fLop')||val('latexDefLop'),Chuong:q.Chuong||val('fChuong')||val('latexDefChuong'),BaiHoc:q.BaiHoc||q.De||val('fBaiHoc')||val('latexDefBaiHoc'),BoDe:q.BoDe||val('fBoDe')||val('latexDefBoDe'),De:q.De||val('latexDefDe'),DangBaiTap:q.DangBaiTap||val('fDangBaiTap')||val('latexDefDangBaiTap')};
  let m=document.getElementById('latexImportModal');
  if(!m){alert('Không tìm thấy modal nhập LaTeX.');return}
  let set=(id,v)=>{let e=document.getElementById(id);if(e&&!e.value)e.value=v||''};
  set('latexDefMon',scope.Mon);
  set('latexDefLop',scope.Lop);
  set('latexDefChuong',scope.Chuong);
  set('latexDefBaiHoc',scope.BaiHoc);
  set('latexDefBoDe',scope.BoDe);
  set('latexDefDe',scope.De);
  let dbtInp=document.getElementById('latexDefDangBaiTap');
  if(dbtInp&&scope.DangBaiTap&&!dbtInp.value)dbtInp.value=scope.DangBaiTap;
  latexImportRefreshDbtList();
  let mq=document.getElementById('latexDefMucDo');if(mq&&!mq.value)mq.value='';
  let qu=document.getElementById('latexDefQuyen');if(qu&&!qu.value)qu.value=q.QuyenTruyCap||'VIP';
  syncLatexImportGithubUi();
  setLatexImportStatus(isGithubBank()?'Dán .tex rồi Đọc thử. Chèn sẽ ghi vào de.tex của bài (trên máy), không ghi Google Sheet.':'Dán file .tex hoặc bấm chọn file. Nên bấm “Đọc thử” trước khi chèn.');
  m.classList.remove('hide');
  closeAdminMoreMenu();
}
function syncLatexImportGithubUi(){
  let gh=typeof isGithubBank==='function'&&isGithubBank();
  let t=document.getElementById('latexImportTitle');
  if(t)t.textContent=gh?'Nhập đề LaTeX vào bài .tex':'Nhập đề LaTeX vào Google Sheet';
  let b=document.getElementById('latexImportCommitBtn');
  if(b)b.textContent=gh?'✅ Chèn vào bài .tex':'✅ Chèn vào Google Sheet';
}
function closeLatexImportModal(){
  let m=document.getElementById('latexImportModal');if(m)m.classList.add('hide');
}
function readLatexImportFile(inp){
  let f=inp&&inp.files&&inp.files[0];if(!f)return;
  let rd=new FileReader();
  rd.onload=()=>{let ta=document.getElementById('latexImportText');if(ta)ta.value=String(rd.result||'');setLatexImportStatus('Đã đọc file: '+f.name+' ('+Math.round(f.size/1024)+' KB). Bấm “Đọc thử”.')};
  rd.onerror=()=>setLatexImportStatus('Không đọc được file.',true);
  rd.readAsText(f,'utf-8');
}
async function latexImportCall(commit,levelOverrides,extra){
  extra=extra||{};
  let ta=document.getElementById('latexImportText');
  let tex=ta?String(ta.value||''):'';
  if(!tex.trim()){alert('Chưa có nội dung LaTeX.');return null}
  let zipInp=document.getElementById('latexAssetZipInput');
  let zipFile=zipInp&&zipInp.files&&zipInp.files[0]?zipInp.files[0]:null;
  if(extra.skip_questions)zipFile=null;
  let aiLevel=!extra.skip_questions&&(val('latexDefMucDo')==='AI');
  levelOverrides=Array.isArray(levelOverrides)?levelOverrides:[];
  setLatexImportStatus(commit?(extra.skip_questions?'⏳ Đang lưu khung lý thuyết…':(isGithubBank()?'⏳ Đang chèn vào bài .tex...':'⏳ Đang chèn vào Google Sheet...')):'⏳ Đang parse LaTeX'+(aiLevel?' + GPT ADMIN nhận diện mức độ...':'...'));
  let j;
  if(zipFile){
    let buildFd=useGpt=>{
      let fd=new FormData();
      fd.append('tex',tex);
      fd.append('defaults',JSON.stringify(currentLatexDefaults()));
      fd.append('commit',commit?'true':'false');
      fd.append('ai_level',aiLevel?'true':'false');
      if(levelOverrides.length)fd.append('level_overrides',JSON.stringify(levelOverrides));
      fd.append('assets_zip',zipFile);
      if(useGpt){fd.set('admin_ai_provider','OPENAI');fd.set('admin_ai_allow_gpt_fallback','true')}
      return fd;
    };
    if(aiLevel)j=await adminAiFetchForm('/api/latex/import',buildFd,{timeoutMs:90000});
    else j=await api('/api/latex/import',{method:'POST',body:buildFd(false),timeoutMs:90000});
  }else{
    let payload={tex:tex,defaults:currentLatexDefaults(),commit:!!commit,ai_level:aiLevel,level_overrides:levelOverrides};
    if(extra&&extra.skip_questions)payload.skip_questions=true;
    if(aiLevel)j=await adminAiFetch('/api/latex/import',payload,{timeoutMs:90000});
    else j=await api('/api/latex/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),timeoutMs:90000});
  }
  return j;
}
function latexImportSummary(j){
  let c=j.counts||{};
  let lines=[];
  lines.push('Tìm thấy block ex: '+(j.total_blocks||0));
  lines.push('Đọc được: '+(j.parsed||0)+' câu');
  if(j.skipped_count!=null&&j.skipped_count>0)lines.push('Bỏ qua (lỗi): '+j.skipped_count+' câu');
  lines.push('TN: '+(c['Trắc nghiệm']||0)+' · Đ/S: '+(c['Đúng sai']||0)+' · TLN: '+(c['Trả lời ngắn']||0)+' · TL: '+(c['Tự luận']||0));
  if(j.ai_level)lines.push('GPT ADMIN mức độ: '+(j.ai_level_done?'đã nhận diện':'chưa nhận diện')+(j.ai_model?' · '+j.ai_model:''));
  if(j.ai_level_error)lines.push('Lỗi AI mức độ: '+j.ai_level_error);
  if(j.created!=null)lines.push('Đã chèn mới: '+j.created+' câu'+(j.start_row?' · dòng '+j.start_row+' → '+j.end_row:''));
  if(j.message)lines.push(String(j.message));
  if(j.theory_groups_count)lines.push('Khung Dạng bài tập: '+j.theory_groups_count+' khung dn/note/vidu');
  if(j.theory_lessons_count)lines.push('Lý thuyết bài học: '+j.theory_lessons_count+' mục (chapter/section → Ly_Thuyet)');
  if(j.theory_saved&&j.theory_saved.length)lines.push('Đã lưu Phuong_Phap: '+j.theory_saved.length+' khung');
  if(j.theory_lessons_saved&&j.theory_lessons_saved.length)lines.push('Đã lưu Ly_Thuyet: '+j.theory_lessons_saved.length+' bài');
  if(j.theory_errors&&j.theory_errors.length)lines.push('Lỗi khung PP: '+j.theory_errors.slice(0,5).join(' | '));
  if(j.theory_lessons_errors&&j.theory_lessons_errors.length)lines.push('Lỗi Ly_Thuyet: '+j.theory_lessons_errors.slice(0,5).join(' | '));
  if(j.skipped&&j.skipped.length)lines.push('Chi tiết bỏ qua: '+j.skipped.slice(0,12).map(x=>'#'+(x.index||'?')+' '+(x.reason||x.warning||x.id||'')).join(' | '));
  if(j.media){lines.push('Media: includegraphics='+((j.media&&j.media.includegraphics)||0)+' · TikZ='+((j.media&&j.media.tikz)||0)+' · đã xử lý='+((j.media&&j.media.resolved)||0));}
  let warns=(j.warnings||[]).filter(w=>!/storage quota|service accounts do not have storage/i.test(String(w.warning||w.reason||'')));
  if(warns.length)lines.push('Cảnh báo: '+warns.slice(0,8).map(w=>'#'+(w.index||'?')+' '+(w.warning||w.reason||'')).join(' | '));
  if((j.media&&j.media.tikz)||(j.questions||[]).some(q=>parseHinhanhCellClient((q&&q.HinhAnh)||'').tikz))lines.push('Mã TikZ sẽ lưu cột T (dòng tikzraw) — sửa được sau khi chèn. Drive quota không chặn chèn.');
  let dupN=(j.questions||[]).filter(q=>q&&(q.dup||q.dup_id)).length;
  if(dupN)lines.push('⚠ '+dupN+' câu có thể trùng Sheet — vẫn hiện đủ để ADMIN xem, quyết định khi chèn.');
  if((j.dup_hits||[]).length)lines.push('Sau khi chèn: '+(j.dup_hits.length)+' câu trùng — ADMIN chọn giữ cả hai hoặc xóa bản mới.');
  return lines.join('\n');
}
function latexImportDangShort(d){d=String(d||'');if(d==='Trắc nghiệm')return 'TN';if(d==='Đúng sai')return 'Đ/S';if(d==='Trả lời ngắn')return 'TLN';if(d==='Tự luận')return 'TL';return d||'—'}
function latexLevelOptions(selected){
  selected=String(selected||'').toUpperCase();
  return ['NB','TH','VD','VDC'].map(x=>`<option value="${x}" ${selected===x?'selected':''}>${x}</option>`).join('');
}
function collectLatexLevelOverrides(){
  let arr=[];
  document.querySelectorAll('#latexImportPreview select[data-level-index]').forEach(sel=>{
    let idx=parseInt(sel.getAttribute('data-level-index')||'0');
    let lv=String(sel.value||'').toUpperCase();
    if(idx&&['NB','TH','VD','VDC'].includes(lv))arr.push({index:idx,MucDo:lv});
  });
  return arr;
}
function applyAllLatexAiLevels(){
  let n=0;
  document.querySelectorAll('#latexImportPreview select[data-ai-level]').forEach(sel=>{
    let lv=String(sel.getAttribute('data-ai-level')||'').toUpperCase();
    if(['NB','TH','VD','VDC'].includes(lv)){sel.value=lv;n++;}
  });
  setLatexImportStatus((document.getElementById('latexImportStatus')?.textContent||'')+'\nĐã áp dụng '+n+' mức AI gợi ý vào ô chọn.');
}
function setAllLatexLevelsFromDefault(){
  let lv=String(val('latexDefMucDo')||'').toUpperCase();
  if(!['NB','TH','VD','VDC'].includes(lv)){alert('Ô Mức độ đang là AI/để trống, không có mức chung để áp dụng.');return;}
  document.querySelectorAll('#latexImportPreview select[data-level-index]').forEach(sel=>{sel.value=lv});
  setLatexImportStatus((document.getElementById('latexImportStatus')?.textContent||'')+'\nĐã gán mức '+lv+' cho tất cả câu trong preview.');
}
function latexPreviewFieldHtml(s){
  try{if(typeof renderQuizFieldHtml==='function')return renderQuizFieldHtml(s||'')}catch(e){}
  return escHtmlKeepMath(s||'');
}
function latexQuestionsFromPreview(pre){
  let defs=currentLatexDefaults();
  let ov={};
  collectLatexLevelOverrides().forEach(o=>{ov[o.index]=o.MucDo});
  let qs=(pre&&(pre.questions||pre.sample))||[];
  let allow=['NB','TH','VD','VDC'];
  return qs.map(function(q,i){
    q=q||{};
    let idx=q.index||(i+1);
    let lv=String(ov[idx]||q.MucDo||defs.MucDo||'TH').toUpperCase();
    if(allow.indexOf(lv)<0)lv='TH';
    return {
      ID:q.ID||'',
      MaDe:q.MaDe||defs.MaDe||'',
      Mon:q.Mon||defs.Mon||'',
      Lop:q.Lop||defs.Lop||'',
      Chuong:q.Chuong||defs.Chuong||'',
      BaiHoc:q.BaiHoc||defs.BaiHoc||'',
      DangBaiTap:q.DangBaiTap||defs.DangBaiTap||'',
      BoDe:q.BoDe||defs.BoDe||'',
      De:q.De||defs.De||'',
      MucDo:lv,
      Dang:q.Dang||'Trắc nghiệm',
      CauHoi:q.CauHoi||'',
      A:q.A||'',B:q.B||'',C:q.C||'',D:q.D||'',
      DapAn:q.DapAn||'',
      SaiSo:q.SaiSo||'',
      LoiGiai:q.LoiGiai||'',
      HinhAnh:(function(){let p=parseHinhanhCellClient(q.HinhAnh||'');let img=p.img&&!/^tikzraw:/i.test(p.img)?p.img:'';return buildHinhanhCellClient(img,p.tikz||q.Tikz||'')||q.HinhAnh||''})(),
      Tikz:q.Tikz||'',
      QuyenTruyCap:q.QuyenTruyCap||defs.QuyenTruyCap||'VIP',
      Diem:defs.Diem||'1',
      TrangThai:'CHƯA DUYỆT'
    };
  });
}
function latexImportQuestionCard(q,i){
  q=q||{};
  let idx=q.index||i+1;
  let opts='';
  for(let L of ['A','B','C','D']){
    if(String(q[L]||'').trim()) opts+=`<div style="margin:4px 0"><b>${L}.</b> ${latexPreviewFieldHtml(q[L])}</div>`;
  }
  let aiLv=String(q._AiMucDo||q.AiMucDo||'').toUpperCase();
  let aiConf=String(q._AiConfidence||q.AiConfidence||'').trim();
  let aiReason=String(q._AiReason||q.AiReason||'').trim();
  let chosen=String(q.MucDo||aiLv||'TH').toUpperCase();
  if(!['NB','TH','VD','VDC'].includes(chosen)) chosen=aiLv||'TH';
  let aiBox=aiLv?`<div style="margin-top:6px;padding:7px 9px;border-radius:10px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a;font-size:12px"><b>🤖 GPT ADMIN gợi ý:</b> ${esc(aiLv)}${aiConf?' · tin cậy '+esc(aiConf):''}${aiReason?' · '+esc(aiReason):''}</div>`:'';
  let levelSelect=`<label style="display:flex;align-items:center;gap:6px;font-size:12px"><b>Mức chèn Sheet:</b><select data-level-index="${idx}" data-ai-level="${esc(aiLv)}" style="padding:5px 8px;border:1px solid var(--border);border-radius:8px">${latexLevelOptions(chosen)}</select></label>`;
  let parsedHa=parseHinhanhCellClient(q.HinhAnh||'');
  let imgUrl=parsedHa.img&&!/^tikzraw:/i.test(parsedHa.img)?parsedHa.img:'';
  let hasTz=!!(parsedHa.tikz||q.Tikz);
  let img=(imgUrl||hasTz)?`<div style="margin-top:8px">${imgUrl?buildQimgHtml(imgUrl):''}<div class="muted" style="font-size:12px;margin-top:4px">${imgUrl?'🖼 '+esc(imgUrl):'🖼 TikZ'}${hasTz?' · mã TikZ sẽ lưu cột T.':''}</div></div>`:'';
  let lg=q.LoiGiai?`<details style="margin-top:7px"><summary style="cursor:pointer;font-weight:800;color:#1d4ed8">Xem lời giải</summary><div style="margin-top:5px;line-height:1.45">${latexPreviewFieldHtml(q.LoiGiai)}</div></details>`:'';
  let warnMsg=String(q.warning||'');
  if(/storage quota|service accounts do not have storage|Apps Script upload/i.test(warnMsg))warnMsg='';
  let warn=warnMsg?`<div style="margin-top:6px;color:#991b1b;font-size:12px">⚠ ${esc(warnMsg)}</div>`:'';
  let isIdDup=q.dup_kind==='id'||(q.dup_id&&q.ID&&String(q.dup_id)===String(q.ID));
  let dupTxt=isIdDup
    ?('Câu '+idx+' trùng ID với Sheet: '+esc(q.dup_id||q.ID||'')+(q.dup_row?(' · dòng '+esc(q.dup_row)):''))
    :('Câu '+idx+' gần giống nội dung Sheet'+(q.dup_id?(': ID '+esc(q.dup_id)):'')+(q.dup_row?(' · dòng '+esc(q.dup_row)):'')+(q.ID&&q.dup_id&&String(q.ID)!==String(q.dup_id)?('. ID câu này: '+esc(q.ID)):'') );
  let dupBox=(q.dup||q.dup_id)?`<div style="margin:0 0 8px;padding:7px 9px;border-radius:10px;background:#fff7ed;border:1px solid #fdba74;color:#9a3412;font-size:12px;line-height:1.4"><b>⚠ ${dupTxt}</b><div style="font-weight:500;margin-top:3px">Vẫn hiện đủ. Khi chèn ADMIN chọn giữ cả hai hoặc xóa bản mới.</div></div>`:'';
  return `<div class="latexQCard" style="margin:12px 0;padding:12px;border:1px solid ${q.dup||q.dup_id?'#fdba74':'var(--border)'};border-left:5px solid ${q.dup||q.dup_id?'#ea580c':'transparent'};border-radius:14px;background:rgba(248,250,252,.88);box-shadow:0 1px 3px rgba(15,23,42,.08)">
    <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
      <b style="color:#0f172a">Câu ${idx}</b>
      ${q.dup||q.dup_id?'<span class="tag" style="background:#fff7ed;color:#9a3412;border:1px solid #fdba74">TRÙNG</span>':''}
      <span class="tag">${esc(latexImportDangShort(q.Dang))}</span>
      <span class="mucdoBadge ${mucdoBadgeClass(chosen)}">${esc(chosen||'—')}</span>
      ${levelSelect}
      <span class="muted" style="font-size:11px">ID: ${esc(q.ID||'AUTO')}</span>
    </div>
    ${dupBox}
    ${aiBox}
    <div style="white-space:normal;line-height:1.5;margin-top:8px"><b>Đề:</b> ${latexPreviewFieldHtml(q.CauHoi||'')}</div>
    ${opts?`<div style="margin-top:7px;padding-left:4px">${opts}</div>`:''}
    <div style="margin-top:7px"><b>Đáp án:</b> <span style="font-weight:800;color:#166534">${esc(q.DapAn||'—')}</span>${q.SaiSo?` <span class="muted"> · Sai số: ${esc(q.SaiSo)}</span>`:''}</div>
    ${img}${lg}${warn}
  </div>`;
}
function renderLatexImportPreview(j,commitDone=false){
  let box=document.getElementById('latexImportPreview');
  if(!box)return;
  let qs=j.questions||j.sample||[];
  let groups=commitDone?(j.theory_saved||[]):(j.theory_groups||[]);
  let lessons=commitDone?(j.theory_lessons_saved||[]):(j.theory_lessons||[]);
  if(!qs.length&&!groups.length&&!lessons.length){box.classList.add('hide');box.innerHTML='';return;}
  box.classList.remove('hide');
  let title=commitDone?'✅ Nội dung vừa chèn — xem nhanh':'👁️ Đọc thử — câu hỏi và học liệu';
  let buttons=commitDone?(qs.length?`<button type="button" class="btn2" onclick="jumpToLastInsertedLatexQuestions()">👁️ Xem câu vừa chèn</button>`:''):(qs.length?`<button type="button" class="btnGreen" onclick="applyAllLatexAiLevels()">🤖 Áp dụng tất cả AI gợi ý</button><button type="button" class="btn2" onclick="setAllLatexLevelsFromDefault()">↩️ Gán mức chung đang chọn</button>`:'');
  let theoryHtml='';
  if(lessons.length){theoryHtml+='<div style="margin:8px 0 12px;padding:10px;border:1px solid #67e8f9;border-radius:10px;background:#ecfeff"><b>📚 Lý thuyết bài học ('+lessons.length+')</b><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:7px">'+lessons.map(g=>'<span class="tag">'+esc((g.Chuong?g.Chuong+' · ':'')+(g.BaiHoc||g.TieuDe||'Bài học'))+(g.action?' · '+esc(g.action):'')+'</span>').join('')+'</div></div>'}
  if(groups.length){theoryHtml+='<div style="margin:8px 0 12px;padding:10px;border:1px solid #93c5fd;border-radius:10px;background:var(--btn2-bg)"><b>📘 Khung Dạng bài tập ('+groups.length+')</b><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:7px">'+groups.map(g=>'<span class="tag">'+esc(g.DangBaiTap||'Dạng chưa tên')+(g.action?' · '+esc(g.action):'')+'</span>').join('')+'</div></div>'}
  box.innerHTML=`<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px"><b>${title}</b><span class="muted">${qs.length} câu · ${lessons.length} LT · ${groups.length} khung</span><div style="display:flex;gap:6px;flex-wrap:wrap">${buttons}</div></div>`+theoryHtml+qs.map((q,i)=>latexImportQuestionCard(q,i)).join('');
  try{if(typeof typesetNow==='function')typesetNow([box]);else typesetQuizMath()}catch(e){}
}
function appendLatexInsertedQuestions(j){
  let qs=(j&&j.questions)||[];
  if(!qs.length)return;
  let start=QUESTIONS.length;
  for(let q of qs){QUESTIONS.push(applyResolvedDang(q));}
  if(!CURRENT_MADE&&qs[0]&&qs[0].MaDe)CURRENT_MADE=qs[0].MaDe;
  if(!ANSWERS)ANSWERS={};
  if(!RESULTS)RESULTS={};
  if(!CHECKED)CHECKED={};
  window.LAST_LATEX_INSERT_START=start;
  window.LAST_LATEX_INSERT_COUNT=qs.length;
  renderNav();
  updateAdminChrome();
}
function jumpToLastInsertedLatexQuestions(){
  let st=window.LAST_LATEX_INSERT_START;
  if(typeof st==='number'&&st>=0&&QUESTIONS[st]){CUR=st;renderNav();renderQuestion();closeLatexImportModal();}
}
async function previewLatexImport(){
  try{
    let j=await latexImportCall(false);
    if(j){window.LAST_LATEX_PREVIEW_DATA=j;setLatexImportStatus(latexImportSummary(j));renderLatexImportPreview(j,false)}
  }catch(e){setLatexImportStatus('Lỗi đọc LaTeX: '+e.message,true)}
}
async function commitLatexImport(){
  let created=0;
  try{
    let pre=window.LAST_LATEX_PREVIEW_DATA;
    if(!pre||(!((pre.questions||pre.sample||[]).length)&&!((pre.theory_groups||[]).length)&&!((pre.theory_lessons||[]).length))){
      pre=await latexImportCall(false);
      if(!pre)return;
      window.LAST_LATEX_PREVIEW_DATA=pre;
      setLatexImportStatus(latexImportSummary(pre)+'\n\nĐã đọc thử. Thầy kiểm tra từng câu/mức độ rồi bấm Chèn lần nữa.');
      renderLatexImportPreview(pre,false);
      return;
    }
    let items=latexQuestionsFromPreview(pre);
    let theoryN=((pre.theory_groups||[]).length)+((pre.theory_lessons||[]).length);
    if(!items.length&&!theoryN){alert('Chưa có câu hoặc học liệu để chèn.');return}
    let msg=latexImportSummary(pre)+'\n\nChèn HẾT '+items.length+' câu'+(isGithubBank()?' vào file de.tex của bài (trên máy, không ghi Google Sheet).':' (câu trùng vẫn chèn). Sau đó ADMIN chọn: giữ cả hai hoặc xóa bản mới trùng.')+'\n\nApp chèn từng nhóm 8 câu.';
    if(!confirm(msg)) {setLatexImportStatus(latexImportSummary(pre));return}
    async function pushLatexChunks(){
      let out={created:0,skipped:[],warns:[],startRow:0,endRow:0,inserted:[],dupHits:[]};
      const CHUNK=8;
      for(let i=0;i<items.length;i+=CHUNK){
        let chunk=items.slice(i,i+CHUNK);
        let a=i+1,b=i+chunk.length;
        setLatexImportStatus('⏳ Đang chèn câu '+a+'–'+b+'/'+items.length+(isGithubBank()?' vào bài .tex…':' lên Google Sheet…'));
        let payload={questions:chunk,defaults:currentLatexDefaults(),index_base:i,allow_duplicates:true};
        let j=await api('/api/latex/save-questions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),timeoutMs:45000},0);
        out.created+=parseInt(j.created,10)||0;
        if(Array.isArray(j.skipped)&&j.skipped.length)out.skipped=out.skipped.concat(j.skipped);
        if(Array.isArray(j.dup_hits)&&j.dup_hits.length)out.dupHits=out.dupHits.concat(j.dup_hits);
        if(Array.isArray(j.hinhanh_warnings)&&j.hinhanh_warnings.length)out.warns=out.warns.concat(j.hinhanh_warnings);
        if((parseInt(j.created,10)||0)>0&&j.start_row){if(!out.startRow)out.startRow=j.start_row;out.endRow=j.end_row||j.start_row}
        let skipIdx={};
        (j.skipped||[]).forEach(s=>{skipIdx[parseInt(s.index,10)||0]=1});
        let k=0;
        chunk.forEach(function(q,ci){
          let idx=i+ci+1;
          if(skipIdx[idx])return;
          q._latexIdx=idx;
          let inf=(j.inserted||[]).find(x=>parseInt(x.index,10)===idx);
          if(inf){
            if(inf.row)q._row=parseInt(inf.row,10);
            if(inf.id)q.ID=inf.id;
          }else if(parseInt(j.start_row,10)){
            q._row=parseInt(j.start_row,10)+k;
            if((j.ids||[])[k])q.ID=j.ids[k];
          }
          k++;
          out.inserted.push(q);
        });
      }
      return out;
    }
    let pack=await pushLatexChunks();
    created=pack.created;
    let skipped=pack.skipped,warns=pack.warns,startRow=pack.startRow,endRow=pack.endRow,inserted=pack.inserted,dupHits=pack.dupHits||[];
    let dupKept=0,dupDropped=0;
    if(dupHits.length && !isGithubBank()){
      let lines=dupHits.slice(0,14).map(d=>{
        let n='#'+(d.index||'?');
        let old=(d.existing_id?('ID '+d.existing_id):'')+(d.existing_row?(' dòng '+d.existing_row):'');
        let neu=d.new_row?('bản mới dòng '+d.new_row):'';
        return n+' '+(d.kind==='id'?'cùng ID':'gần giống')+(old?(' với '+old):'')+(neu?(' → '+neu):'')+(d.cau?(' · '+String(d.cau).slice(0,50)): '');
      });
      let drop=confirm('Đã chèn hết '+created+' câu lên Sheet.\n\n'+dupHits.length+' câu TRÙNG (đã hiện đủ khi Đọc thử, vẫn đã chèn):\n'+lines.join('\n')+(dupHits.length>14?'\n…':'')+'\n\nOK = XÓA bản mới trùng (giữ câu cũ trên Sheet).\nCancel = GIỮ CẢ HAI.');
      if(drop){
        let rows=dupHits.map(d=>parseInt(d.new_row,10)).filter(n=>n>1);
        if(rows.length){
          setLatexImportStatus('⏳ Đang xóa '+rows.length+' bản mới trùng theo quyết định ADMIN…');
          try{
            await api('/api/admin/dang-similarity-delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows:rows}),timeoutMs:60000},0);
            let dropIdx={};
            dupHits.forEach(d=>{dropIdx[parseInt(d.index,10)||0]=1});
            inserted=inserted.filter(function(q){return !dropIdx[q._latexIdx]});
            let dels=rows.slice().sort((a,b)=>a-b);
            inserted.forEach(function(q){
              let r=parseInt(q._row,10)||0;
              let shift=dels.filter(d=>d<r).length;
              if(shift)q._row=r-shift;
            });
            created=Math.max(0,created-rows.length);
            skipped=skipped.concat(dupHits.map(d=>({index:d.index,id:d.existing_id,reason:'ADMIN xóa bản mới trùng'})));
            dupDropped=rows.length;
            dupHits=[];
          }catch(delErr){alert('Đã chèn nhưng xóa bản trùng lỗi: '+(delErr.message||delErr)+'\nCâu mới vẫn còn trên Sheet.');}
        }
      }else{
        dupKept=dupHits.length;
        let byIdx={};
        dupHits.forEach(d=>{byIdx[parseInt(d.index,10)||0]=d});
        inserted.forEach(function(q){
          let d=byIdx[q._latexIdx];
          if(d){q.dup=true;q.dup_kind=d.kind;q.dup_id=d.existing_id;q.dup_row=d.existing_row}
        });
      }
    }
    let theorySaved=[],lessonSaved=[],theoryErrors=[],lessonErrors=[];
    if(theoryN){
      setLatexImportStatus('⏳ Đang lưu khung lý thuyết… (đã chèn '+created+' câu)');
      let tj=await latexImportCall(true,[],{skip_questions:true});
      if(tj){
        theorySaved=tj.theory_saved||[];
        lessonSaved=tj.theory_lessons_saved||[];
        theoryErrors=tj.theory_errors||[];
        lessonErrors=tj.theory_lessons_errors||[];
      }
    }
    let j={
      created:created,skipped:skipped,hinhanh_warnings:warns,start_row:startRow,end_row:endRow,
      questions:inserted,parsed:pre.parsed,total_blocks:pre.total_blocks,counts:pre.counts,
      warnings:(pre.warnings||[]).concat(warns.map(w=>({index:0,warning:w}))),
      media:pre.media,message:'',dup_hits:dupHits,
      theory_saved:theorySaved,theory_lessons_saved:lessonSaved,
      theory_errors:theoryErrors,theory_lessons_errors:lessonErrors,
      theory_groups_count:(pre.theory_groups||[]).length,
      theory_lessons_count:(pre.theory_lessons||[]).length
    };
    if(!created&&skipped.length){
      if(skipped.every(x=>/trung noi dung|trùng nội dung/i.test(String(x.reason||'')))){
        let ids=skipped.map(x=>x.existing_id||x.id).filter(Boolean).slice(0,5);
        j.message='Các câu đã có trên Sheet — không chèn lần 2. Mở mục lục, lọc Chưa duyệt.'+(ids.length?(' ID: '+ids.join(', ')):'');
        j.already_exists=true;
      }else{
        j.message='Không chèn được câu mới. '+skipped.slice(0,6).map(x=>x.reason||x.id||('#'+x.index)).join(' | ');
      }
    }
    setLatexImportStatus(latexImportSummary(j)+(created?('\nĐã chèn '+created+' câu'+(startRow?(' · dòng '+startRow+' → '+endRow):'')):'')+(skipped.length?('\nBỏ qua '+skipped.length+' câu.'):''));
    if(created>0||theorySaved.length||lessonSaved.length){
      if(created>0)appendLatexInsertedQuestions(j);
      DANG_THEORY_CACHE={};
      LEARNING_CACHE={};
      renderLatexImportPreview(j,true);
      window.LAST_LATEX_PREVIEW_DATA=null;
      try{await refreshCatalogFromMeta()}catch(e2){}
      let dupNote=dupDropped?('\nĐã xóa '+dupDropped+' bản mới trùng (giữ câu cũ).'):(dupKept?('\nGiữ cả hai: '+dupKept+' câu trùng vẫn nằm trên Sheet.'):'');
      alert('Đã chèn '+(created||0)+' câu, lưu '+(lessonSaved.length)+' lý thuyết (Ly_Thuyet) và '+(theorySaved.length)+' khung dạng (Phuong_Phap).'+dupNote+(skipped.length&&!dupDropped?('\nBỏ qua '+skipped.length+' câu không hợp lệ.'):'')+'\n\n⚠ Cảnh báo Drive quota không chặn chèn câu — TikZ giữ trong cột T. Nếu thiếu ảnh: upload tay rồi dán link cột T.');
    }else{
      let why=j.message||'';
      if(!why&&skipped.length)why='Bỏ qua '+skipped.length+' câu: '+skipped.slice(0,4).map(x=>x.reason||x.id||('#'+x.index)).join('; ');
      alert(why||'Không chèn được câu nào. Kiểm tra ô trạng thái bên dưới.');
    }
  }catch(e){
    let msg=String(e&&e.message||e||'');
    if(/exceeds grid limits|Max rows/i.test(msg))msg='Sheet Cau_Hoi hết hàng trống — app sẽ tự nới lưới; hãy bấm Chèn lại. Chi tiết: '+msg;
    if(typeof created==='number'&&created>0)msg='Đã ghi được '+created+' câu. Bấm Chèn lại — câu trùng sẽ bỏ qua. '+msg;
    setLatexImportStatus('Lỗi chèn LaTeX: '+msg,true);
  }
}



function openAddQuestion(){if(!USER.is_admin){alert('Chỉ ADMIN.');return}if(!QUESTIONS.length){alert('Hãy mở một đề trước khi thêm câu.');return}QUESTION_MODAL_MODE='add';ADMIN_SIMILAR_EDIT_TIPS=null;let tpl=QUESTIONS[CUR]||{};let seed={MaDe:tpl.MaDe||CURRENT_MADE||'',Mon:tpl.Mon||'',Lop:tpl.Lop||'',Chuong:tpl.Chuong||'',BaiHoc:tpl.BaiHoc||tpl.De||'',DangBaiTap:tpl.DangBaiTap||'',NangLucVatLy:tpl.NangLucVatLy||'',QuyenTruyCap:tpl.QuyenTruyCap||'VIP',MucDo:tpl.MucDo||'',Dang:tpl.Dang||'Trắc nghiệm',CauHoi:'',A:'',B:'',C:'',D:'',DapAn:'',SaiSo:'',LoiGiai:'',HinhAnh:'',ID:''};renderQuestionForm(seed);syncQuestionModalChrome();document.getElementById('modal').classList.remove('hide')}
function closeEdit(){ADMIN_SIMILAR_EDIT_TIPS=null;document.getElementById('modal').classList.add('hide')}
function closeInfographicModal(){let m=document.getElementById('infographicModal');if(m)m.classList.add('hide')}
function quizViSpeakUnits(t){
  t=String(t||'');
  t=t.replace(/\\mathrm\s*\{([^}]*)\}/g,'$1');
  t=t.replace(/\\text\s*\{([^}]*)\}/g,'$1');
  t=t.replace(/\\left|\\right/g,'');
  t=t.replace(/\\sin/gi,' sin ');
  t=t.replace(/\\cos/gi,' côsin ');
  t=t.replace(/\\tan/gi,' tang ');
  t=t.replace(/\\cot/gi,' côtang ');
  t=t.replace(/\\log/gi,' lôga ');
  t=t.replace(/\\ln/gi,' lôga nêpe ');
  t=t.replace(/\\infty/g,' vô cùng ');
  t=t.replace(/\\pm/g,' cộng trừ ');
  t=t.replace(/\\leq|\\le/g,' nhỏ hơn hoặc bằng ');
  t=t.replace(/\\geq|\\ge/g,' lớn hơn hoặc bằng ');
  t=t.replace(/\\neq|\\ne/g,' khác ');
  t=t.replace(/\\approx/g,' xấp xỉ ');
  t=t.replace(/\\times|\\cdot|\\ast/g,' nhân ');
  t=t.replace(/\\div/g,' chia ');
  t=t.replace(/\\circ/g,' độ ');
  t=t.replace(/\\omega/gi,' ômêga ');
  t=t.replace(/\\alpha/gi,' anpha ');
  t=t.replace(/\\beta/gi,' bêta ');
  t=t.replace(/\\gamma/gi,' gamma ');
  t=t.replace(/\\delta/gi,' đen ta ');
  t=t.replace(/\\theta/gi,' têta ');
  t=t.replace(/\\lambda/gi,' lam đa ');
  t=t.replace(/\\mu/gi,' muy ');
  t=t.replace(/\\nu/gi,' nu ');
  t=t.replace(/\\rho/gi,' rô ');
  t=t.replace(/\\sigma/gi,' sigma ');
  t=t.replace(/\\phi/gi,' phi ');
  t=t.replace(/\\psi/gi,' pxi ');
  t=t.replace(/\\pi/gi,' pi ');
  t=t.replace(/\\Delta/g,' đen ta ');
  t=t.replace(/ω/g,' ômêga ');
  t=t.replace(/α/g,' anpha ');
  t=t.replace(/β/g,' bêta ');
  t=t.replace(/γ/g,' gamma ');
  t=t.replace(/δ/g,' đen ta ');
  t=t.replace(/θ/g,' têta ');
  t=t.replace(/λ/g,' lam đa ');
  t=t.replace(/μ/g,' muy ');
  t=t.replace(/π/g,' pi ');
  t=t.replace(/Δ/g,' đen ta ');
  t=t.replace(/\\frac\s*\{([^}]*)\}\s*\{([^}]*)\}/g,' $1 trên $2 ');
  t=t.replace(/\\sqrt\s*\{([^}]*)\}/g,' căn $1 ');
  t=t.replace(/\^\{2\}|\^2/g,' bình phương ');
  t=t.replace(/\^\{3\}|\^3/g,' lập phương ');
  t=t.replace(/rad\s*\/\s*s/gi,' radian trên giây ');
  t=t.replace(/m\s*\/\s*s\^?2|m\s*\/\s*s²/gi,' mét trên giây bình phương ');
  t=t.replace(/m\s*\/\s*s/gi,' mét trên giây ');
  t=t.replace(/\bkHz\b/g,' ki lô héc ');
  t=t.replace(/\bMHz\b/g,' mê ga héc ');
  t=t.replace(/\bHz\b/g,' héc ');
  t=t.replace(/\brpm\b/gi,' vòng trên phút ');
  t=t.replace(/=/g,' bằng ');
  t=t.replace(/\\,|~|\\;|\\!/g,' ');
  t=t.replace(/[{}\\]/g,' ');
  return t;
}
function quizSpeechPlain(s){
  s=stripQuizSourceLeak(String(s||''));
  s=s.replace(/<[^>]+>/g,' ');
  s=s.replace(/\\(?:source|nguon)[^\s{}]*/gi,' ');
  s=s.replace(/\\textcolor\s*\{[^}]*\}\s*\{([\s\S]*?)\}/g,'$1');
  s=s.replace(/\\color\s*\{[^}]*\}\s*\{?/g,' ');
  s=s.replace(/[A-Za-z0-9_\-]+\.pdf\b/gi,' ');
  s=s.replace(/\$\$([\s\S]*?)\$\$/g,function(_m,t){return ' '+quizViSpeakUnits(t)+' '});
  s=s.replace(/\$([^$\n]+)\$/g,function(_m,t){return ' '+quizViSpeakUnits(t)+' '});
  s=s.replace(/\\\(([\s\S]*?)\\\)/g,function(_m,t){return ' '+quizViSpeakUnits(t)+' '});
  s=s.replace(/\\\[([\s\S]*?)\\\]/g,function(_m,t){return ' '+quizViSpeakUnits(t)+' '});
  s=quizViSpeakUnits(s);
  s=s.replace(/\\[a-zA-Z]+\{([^}]*)\}/g,'$1');
  s=s.replace(/\\[a-zA-Z]+/g,' ');
  s=s.replace(/[{}_^]/g,' ');
  s=s.replace(/điều hoà/g,'điều hòa ');
  s=s.replace(/\bomega\b/gi,' ômêga ');
  return s.replace(/\s+/g,' ').trim();
}
function quizSpeakChoiceLetter(L){return ({A:'a',B:'bê',C:'xê',D:'đê'}[String(L||'').toUpperCase()]||L)}
function buildQuizReadAloudText(){let q=currentQuestion()||{};let parts=[];let stem=quizSpeechPlain(q.CauHoi||'');if(stem)parts.push('Câu hỏi. '+stem);for(let L of ['A','B','C','D']){let v=quizSpeechPlain(q[L]||'');if(v)parts.push('Phương án '+quizSpeakChoiceLetter(L)+'. '+v)}return parts.join(' ')}
function isQuizViSpeechVoice(v){if(!v)return false;let lang=String(v.lang||'').replace(/_/g,'-').toLowerCase();if(lang==='vi-vn'||lang==='vi'||lang.indexOf('vi-')===0)return true;let name=String(v.name||'').toLowerCase();return /vietnamese|tiếng việt|tieng viet|\(việt|\(viet|vi-vn|việt nam|viet nam|hoai\s*my|hoaimy|nam\s*minh|namminh|google.*việt|google.*viet/.test(name)}
function quizTtsVoiceGender(v){let name=String(v.name||'').toLowerCase();let uri=String(v.voiceURI||'').toLowerCase();let compact=name.replace(/\s/g,'');let blob=name+' '+uri;if(/hoai\s*my|hoaimy|linh\s*san|\bfemale\b|nữ|woman|girl|\bvif\b|-vif-|wavenet-a|wavenet-c|neural2-a|neural2-c/.test(blob))return 'Nữ';if(/nam\s*minh|namminh|\bmale\b|\bman\b|boy|-vic-|-vid-|wavenet-b|wavenet-d|neural2-b|neural2-d/.test(blob)||/namminh/.test(compact))return 'Nam';if(/google/.test(name)&&(/việt|viet|\bvi\b/.test(name)||String(v.lang||'').toLowerCase().indexOf('vi')===0))return 'Nữ';return ''}
function quizTtsVoiceDisplayLabel(v){let raw=String(v.name||'Giọng Việt');let g=quizTtsVoiceGender(v);let short=raw;if(/hoai\s*my|hoaimy/i.test(raw))short='Hoài My';else if(/nam\s*minh|namminh/i.test(raw))short='Nam Minh';else if(/google/i.test(raw)&&/vi/i.test(raw))short='Google Tiếng Việt';else if(/microsoft/i.test(raw))short=raw.replace(/^Microsoft\s+/i,'').replace(/\s*Online.*$/i,'').trim();return g?(short+' ('+g+')'):short}
function quizTtsVoiceScore(v){if(!isQuizViSpeechVoice(v))return -999;let lang=String(v.lang||'').replace(/_/g,'-').toLowerCase();let name=String(v.name||'').toLowerCase();let n=0;if(lang==='vi-vn'||lang==='vi')n+=120;else if(lang.indexOf('vi-')===0)n+=100;if(/tiếng việt|tieng viet|vietnamese/.test(name))n+=110;if(/google.*(việt|viet)/.test(name))n+=95;if(/hoai\s*my|hoaimy/.test(name))n+=92;if(/nam\s*minh|namminh/.test(name))n+=90;if(/natural/.test(name))n+=8;if(/online/.test(name))n+=4;return n}
function quizTtsListViVoices(){if(typeof speechSynthesis==='undefined')return [];let voices=speechSynthesis.getVoices?speechSynthesis.getVoices():[];return voices.filter(isQuizViSpeechVoice).slice().sort(function(a,b){return quizTtsVoiceScore(b)-quizTtsVoiceScore(a)})}
function quizTtsSavedVoiceURI(){try{return String(localStorage.getItem('LDVL_QUIZ_TTS_VOICE')||'')}catch(e){return ''}}
function quizTtsRate(){try{let r=parseFloat(localStorage.getItem('LDVL_QUIZ_TTS_RATE')||'0.9');if(!(r>=0.55&&r<=1.35))r=0.9;return r}catch(e){return 0.9}}
function pickQuizViVoice(){if(typeof speechSynthesis==='undefined')return null;let voices=quizTtsListViVoices();if(!voices.length)return null;let want=quizTtsSavedVoiceURI();if(want){for(let i=0;i<voices.length;i++){let v=voices[i];if(v.voiceURI===want||v.name===want)return v}}return voices[0]}
function quizTtsOptEsc(s){return String(s||'').replace(/[&<>"]/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]})}
function fillQuizTtsVoiceSelect(){let sel=document.getElementById('quizTtsVoice');if(!sel||typeof speechSynthesis==='undefined')return;let all=speechSynthesis.getVoices?speechSynthesis.getVoices():[];let viVoices=quizTtsListViVoices();let rateSel=document.getElementById('quizTtsRate');if(rateSel){let rv=String(quizTtsRate());if(!rateSel.querySelector('option[value="'+rv+'"]'))rv='0.9';rateSel.value=rv}if(!all.length){if(!sel.options.length||sel.getAttribute('data-n')!=='0'){sel.innerHTML='<option value="">Đang tải giọng…</option>';sel.setAttribute('data-n','0')}return}if(sel.getAttribute('data-n')===String(viVoices.length)&&sel.options.length>0)return;let want=quizTtsSavedVoiceURI();let html='';if(!viVoices.length){html='<option value="">Chưa có giọng Việt</option>'}else{html='<option value="">'+(viVoices.length<2?'1 giọng máy (lớp học đổi cao độ)':'Tự chọn (Nam/Nữ)')+'</option>';for(let i=0;i<viVoices.length;i++){let v=viVoices[i];let uri=v.voiceURI||v.name||'';let lab=quizTtsVoiceDisplayLabel(v);html+='<option value="'+quizTtsOptEsc(uri)+'"'+(want&&(want===uri||want===v.name)?' selected':'')+'>'+quizTtsOptEsc(lab)+'</option>'}}sel.innerHTML=html;sel.setAttribute('data-n',String(viVoices.length))}
function bindQuizTtsVoices(){if(window._LDVL_QUIZ_TTS_VOICES_BOUND)return;window._LDVL_QUIZ_TTS_VOICES_BOUND=1;try{if(typeof speechSynthesis!=='undefined'&&speechSynthesis.addEventListener)speechSynthesis.addEventListener('voiceschanged',function(){let sel=document.getElementById('quizTtsVoice');if(sel)sel.removeAttribute('data-n');fillQuizTtsVoiceSelect()})}catch(e){}fillQuizTtsVoiceSelect()}
function onQuizTtsVoiceChange(){let sel=document.getElementById('quizTtsVoice');try{localStorage.setItem('LDVL_QUIZ_TTS_VOICE',sel?String(sel.value||''):'')}catch(e){}}
function onQuizTtsRateChange(el){let r=parseFloat(el&&el.value||'0.9');if(!(r>=0.55&&r<=1.35))r=0.9;try{localStorage.setItem('LDVL_QUIZ_TTS_RATE',String(r))}catch(e){}}
function canUseQuizAiTalk(){if(!(USER&&USER.can_ai_hint!==false))return false;if(EXAM_MODE&&!SUBMITTED)return false;return true}
function quizAiTalkSpoil(){return !!(isAdminViewer()||(typeof canShowSolutionNow==='function'&&canShowSolutionNow())||CHECKED[CUR]||RESULTS[CUR])}
function quizTtsChunks(plain,maxLen){maxLen=maxLen||900;plain=String(plain||'').replace(/\s+/g,' ').trim();if(!plain)return [];if(plain.length<=maxLen)return [plain];let parts=[],i=0;while(i<plain.length){let end=Math.min(i+maxLen,plain.length);if(end<plain.length){let cut=plain.lastIndexOf('. ',end);if(cut<=i+120)cut=plain.lastIndexOf(' ',end);if(cut>i)end=cut+1}let bit=plain.slice(i,end).trim();if(bit)parts.push(bit);i=end}return parts}
function buildQuizReadLoiGiaiText(){let q=currentQuestion()||{};let parts=[];let da=quizSpeechPlain(q.DapAn||'');if(da)parts.push('Đáp án. '+da);let raw='';try{raw=currentQuizLoiGiaiText(q)||''}catch(e){}if(!raw)raw=String((q.LoiGiai||'')||(ADMIN_LG_DRAFT_BY_Q[CUR]!=null?ADMIN_LG_DRAFT_BY_Q[CUR]:'')||((AI_LG_BY_Q[CUR]||{}).text||''));let lg=quizSpeechPlain(raw);if(lg)parts.push('Lời giải. '+lg);return parts.join(' ')}
function syncQuizReadBtn(){let deOn=!!(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='de');let lgOn=!!(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='lg');let talkOn=!!(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='talk');let b=document.getElementById('btnReadQuestion');if(b){b.classList.toggle('ttsBtnOn',deOn);b.textContent=deOn?'⏸ Dừng đọc':'🔊 Đọc đề'}for(let id of ['btnReadLoiGiai','btnFsReadLoiGiai','btnPanelReadLoiGiai']){let x=document.getElementById(id);if(!x)continue;x.classList.toggle('ttsBtnOn',lgOn);x.textContent=lgOn?'⏸ Dừng đọc LG':'🔊 Đọc lời giải'}syncQuizAiTalkBtn(talkOn);try{syncQuizDebateBtn()}catch(e){}}function syncQuizAiTalkBtn(talkOn){talkOn=!!(talkOn||(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='talk'));let busy=QUIZ_TALK_LOADING===CUR;let allow=canUseQuizAiTalk();let idle=quizAiTalkIdleLabel(false);let idleFs=quizAiTalkIdleLabel(true);for(let id of ['btnAiTalk','btnFsAiTalk']){let x=document.getElementById(id);if(!x)continue;x.classList.toggle('hide',!allow);x.classList.toggle('ttsBtnOn',talkOn);x.classList.toggle('ttsBusy',busy&&!talkOn);x.disabled=busy&&!talkOn;if(busy&&!talkOn)x.textContent=(id==='btnFsAiTalk'?'⏳ AI…':'⏳ Đang soạn…');else if(talkOn)x.textContent=(id==='btnFsAiTalk'?'⏸ Dừng':'⏸ Dừng thảo luận');else x.textContent=(id==='btnFsAiTalk'?idleFs:idle)}}
function quizAiTalkIdleLabel(fs){if(isAdminViewer()&&typeof adminChosenAiProvider==='function'){let p=adminChosenAiProvider();if(p==='ANTHROPIC')return fs?'🎙 Claude':'🎙 Claude thảo luận';if(p==='OPENAI')return fs?'🎙 GPT':'🎙 GPT thảo luận'}return fs?'🎙 Thảo luận':'🎙 AI thảo luận'}
function stopQuizQuestionSpeech(){QUIZ_CR_STOP=true;QUIZ_CR_PLAY=-1;QUIZ_TTS_ON=false;QUIZ_TTS_KIND='';QUIZ_TTS_CHUNKS=[];QUIZ_TTS_IDX=0;if(typeof speechSynthesis!=='undefined'){try{speechSynthesis.cancel()}catch(e){}}try{document.querySelectorAll('.quizCrMsg.active').forEach(function(n){n.classList.remove('active')})}catch(e2){}syncQuizReadBtn()}
function speakNextQuizChunk(){if(!QUIZ_TTS_ON||!QUIZ_TTS_CHUNKS.length||QUIZ_TTS_IDX>=QUIZ_TTS_CHUNKS.length){let kind=QUIZ_TTS_KIND;QUIZ_TTS_ON=false;QUIZ_TTS_KIND='';QUIZ_TTS_CHUNKS=[];QUIZ_TTS_IDX=0;syncQuizReadBtn();if(kind==='debate'){let ta=debateAskEl();if(ta)try{ta.focus()}catch(e){}}return}try{let u=new SpeechSynthesisUtterance(QUIZ_TTS_CHUNKS[QUIZ_TTS_IDX++]);u.lang='vi-VN';u.rate=quizTtsRate();let v=pickQuizViVoice();if(v){u.voice=v;u.lang=v.lang&&String(v.lang).toLowerCase().indexOf('vi')===0?v.lang:'vi-VN'}u.onend=function(){speakNextQuizChunk()};u.onerror=function(){stopQuizQuestionSpeech()};speechSynthesis.speak(u)}catch(e){stopQuizQuestionSpeech();alert('Không đọc được: '+(e.message||e))}}
function startQuizViSpeech(plain,kind,emptyMsg){if(typeof speechSynthesis==='undefined'||typeof SpeechSynthesisUtterance==='undefined'){alert('Trình duyệt không hỗ trợ đọc (Text-to-Speech). Dùng Chrome hoặc Edge.');return}plain=String(plain||'').trim();if(!plain){alert(emptyMsg||'Không có nội dung để đọc.');return}stopQuizQuestionSpeech();let chunks=quizTtsChunks(plain,900);if(!chunks.length){alert(emptyMsg||'Không có nội dung để đọc.');return}let run=function(){try{stopTranslateEnSpeech();if(!window._LDVL_TTS_VI_WARN&&!pickQuizViVoice()){window._LDVL_TTS_VI_WARN=1;alert('Chưa có giọng tiếng Việt trên máy.\n\nWindows: Cài đặt → Thời gian và ngôn ngữ → Giọng nói → thêm Tiếng Việt.\nHoặc dùng Chrome (giọng Google Tiếng Việt).\n\nVẫn thử đọc bằng tiếng Việt.')}QUIZ_TTS_CHUNKS=chunks;QUIZ_TTS_IDX=0;QUIZ_TTS_KIND=kind;QUIZ_TTS_ON=true;syncQuizReadBtn();speakNextQuizChunk()}catch(e){stopQuizQuestionSpeech();alert('Không đọc được: '+(e.message||e))}};let voices=speechSynthesis.getVoices?speechSynthesis.getVoices():[];let kick=function(){setTimeout(run,80)};if(!voices.length){let done=false;let wait=function(){if(done)return;done=true;try{speechSynthesis.onvoiceschanged=null}catch(e2){}kick()};if(speechSynthesis.onvoiceschanged!==undefined)speechSynthesis.onvoiceschanged=wait;setTimeout(wait,700)}else kick()}
function toggleReadQuestion(){if(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='de'){stopQuizQuestionSpeech();return}startQuizViSpeech(buildQuizReadAloudText(),'de','Không có nội dung đề để đọc.')}
function toggleReadLoiGiai(){if(!canAdminEditLoiGiaiInline()&&!(typeof canShowSolutionNow==='function'&&canShowSolutionNow())){alert('Chỉ ADMIN đọc lời giải tại đây.');return}if(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='lg'){stopQuizQuestionSpeech();return}VIP_Q_SHOW_EXP[CUR]=true;let sol=document.getElementById('solution');if(sol)sol.classList.remove('hide');try{syncAdminLoiGiaiPanel()}catch(e){}startQuizViSpeech(buildQuizReadLoiGiaiText(),'lg','Chưa có lời giải / đáp án để đọc.')}
function canUseQuizDebate(){if(!(USER&&USER.can_ai_hint!==false))return false;if(EXAM_MODE&&!SUBMITTED)return false;if(isAdminViewer())return true;return !!(typeof canShowSolutionNow==='function'&&canShowSolutionNow())}
let QUIZ_CR_WANT=false,QUIZ_CR_PLAY=-1,QUIZ_CR_STOP=true,QUIZ_CR_LINES=[];
function debateAskEl(){let a=document.getElementById('quizCrAsk');if(a&&QUIZ_CR_WANT)return a;return document.getElementById('quizDebateAsk')||a}
function parseQuizClassScript(txt){
  txt=String(txt||'').replace(/\r\n/g,'\n').trim();
  if(!txt)return [];
  let re=/^\s*(An|Bình|Binh|Chi|Dũng|Dung|Thầy Minh|Thay Minh|Trợ lý|Tro ly|Em)\s*[:：]\s*/i;
  let out=[],cur=null;
  txt.split('\n').forEach(function(line){
    let m=String(line||'').match(re);
    if(m){
      if(cur&&String(cur.text||'').trim())out.push(cur);
      cur={who:quizCrNormWho(m[1]),text:String(line).slice(m[0].length).trim()};
    }else if(cur){
      let extra=String(line||'').trim();
      if(extra)cur.text+=(cur.text?' ':'')+extra;
    }
  });
  if(cur&&String(cur.text||'').trim())out.push(cur);
  return out;
}
function quizCrNormWho(w){
  w=String(w||'').trim();
  let t=w.normalize?w.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase():w.toLowerCase();
  if(t.indexOf('thay')>=0)return 'Thầy Minh';
  if(t.indexOf('tro ly')>=0||t.indexOf('troly')>=0)return 'Trợ lý';
  if(t==='em')return 'Em';
  if(t==='binh')return 'Bình';
  if(t==='dung')return 'Dũng';
  if(t==='chi')return 'Chi';
  if(t==='an')return 'An';
  return w;
}
function quizCrMeta(who){
  who=quizCrNormWho(who);
  if(who==='Thầy Minh')return {who:who,role:'teacher',av:'👨‍🏫',right:false};
  if(who==='Trợ lý')return {who:who,role:'teacher',av:'⚡',right:false};
  if(who==='Em')return {who:who,role:'user',av:'🧑',right:true};
  if(who==='An')return {who:who,role:'student',av:'🟦',right:false};
  if(who==='Bình')return {who:who,role:'student',av:'🟩',right:true};
  if(who==='Chi')return {who:who,role:'student',av:'🟪',right:false};
  if(who==='Dũng')return {who:who,role:'student',av:'🟧',right:true};
  return {who:who,role:'student',av:'💬',right:false};
}
function quizCrLetterCorrect(q,L){
  q=q||{};L=String(L||'').toUpperCase();
  if(String(q.Dang||'')==='Đúng sai')return false;
  let da=String(q.DapAn||'').trim();
  if(!da)return false;
  let up=da.toUpperCase().replace(/\s+/g,'');
  if(up===L||up.charAt(0)===L)return true;
  let only=up.replace(/[^A-D]/g,'');
  if(only===L)return true;
  try{if(typeof normText==='function'&&normText(da)===normText(q[L]||''))return true}catch(e){}
  return false;
}
function quizCrHeard(){let d=QUIZ_DEBATE_BY_Q[CUR]||{};return !!d.heard}
function quizCrStudentName(){return String((USER&&(USER.hoten||USER.mahs))||'em').trim()||'em'}
function quizCrHasChoice(q){
  q=q||currentQuestion()||{};
  let ans=ANSWERS[CUR];
  if(q.Dang==='Đúng sai'){
    let arr=Array.isArray(ans)?ans:[];
    return arr.some(function(x){return String(x||'').trim()});
  }
  return String(ans==null?'':ans).trim()!=='';
}
function quizCrChoiceState(){
  let q=currentQuestion()||{};
  if(!quizCrHasChoice(q))return {kind:'none',label:'chưa chọn'};
  let r=RESULTS[CUR]||CHECKED[CUR];
  if(r&&r.ok===true)return {kind:'ok',label:'đúng'};
  return {kind:'bad',label:'chưa đúng'};
}
function quizCrDsLabel(v){
  v=String(v||'').trim();
  if(v==='S'||/^sai$/i.test(v))return 'Sai';
  if(v==='Đ'||v==='D'||v==='d'||/^dung$/i.test(v)||/^đúng$/i.test(v))return 'Đúng';
  return '';
}
function quizCrDsRows(q){
  q=q||currentQuestion()||{};
  if(String(q.Dang||'')!=='Đúng sai')return [];
  try{return getDsCheckRows(q,RESULTS[CUR]||CHECKED[CUR],ANSWERS[CUR])||[]}catch(e){return []}
}
function quizCrDsCompareHtml(){
  let rows=quizCrDsRows();
  if(!rows.length)return '';
  return '<div class="quizCrDsRow">'+rows.map(function(r){
    let key=quizCrDsLabel(r.correct)||'?';
    let em=quizCrDsLabel(r.chosen)||'chưa chọn';
    let cls=r.ok===true?'ok':(r.ok===false?'bad':'none');
    let mark=r.ok===true?'✓ đúng':(r.ok===false?'✗ chưa đúng':'? chưa chọn');
    return '<span class="quizCrDsChip '+cls+'"><b>Ý '+esc(r.letter)+' · '+mark+'</b><small>Em chọn '+esc(em)+' · Đáp án '+esc(key)+'</small></span>';
  }).join('')+'</div>';
}
function quizCrPickedLetter(q){
  q=q||{};
  if(String(q.Dang||'')!=='Trắc nghiệm')return '';
  let a=String(ANSWERS[CUR]==null?'':ANSWERS[CUR]).trim().toUpperCase();
  if(/^[A-D]/.test(a))return a.charAt(0);
  return '';
}
function quizCrLoiGiaiHtml(){
  let q=currentQuestion()||{};
  let lg='';
  try{lg=currentQuizLoiGiaiText(q)||''}catch(e){lg=String(q.LoiGiai||'')}
  if(!String(lg||'').trim())return '<span class="muted">Chưa có lời giải trên Sheet.</span>';
  try{if(typeof formatLoigiaiByDang==='function')return formatLoigiaiByDang(lg,q,q.Dang)}catch(e2){}
  return typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(lg):esc(lg);
}
function quizCrVerdictHtml(){
  let st=quizCrChoiceState();
  let q=currentQuestion()||{};
  let name=esc(quizCrStudentName());
  let chosen='';
  try{chosen=formatChosenAnswerBrief(q,ANSWERS[CUR])}catch(e){chosen=String(ANSWERS[CUR]==null?'':ANSWERS[CUR])}
  let ds=String(q.Dang||'')==='Đúng sai';
  let html='<div class="quizCrVerdict '+st.kind+'">';
  if(st.kind==='ok'){
    html+='<div class="quizCrBadge"><div class="quizCrBadgeIcon">🏅</div><div><b>Huy hiệu «Chọn đúng»</b><div>Khen <b>'+name+'</b> đã chọn đúng. Giữ đà này và luyện thêm để học tốt hơn nữa nhé!</div></div></div>';
    html+='Nhận xét: kết quả em đã chọn là <b>đúng</b>'+(ds?' (đủ cả các ý).':(chosen?(' · '+esc(chosen)):''))+'.';
  }else if(st.kind==='bad'){
    html+='<b>Nhận xét:</b> kết quả em đã chọn là <b>chưa đúng</b>. ';
    if(ds)html+='Xem từng ý A–D bên dưới: ý nào ✓ là khớp đáp án, ý nào ✗ là lệch.';
    else html+=(chosen?('Em chọn '+esc(chosen)+'. '):'')+'Đối chiếu lời giải để hiểu chỗ lệch, rồi luyện tiếp.';
  }else{
    html+='<b>Nhận xét:</b> em <b>chưa chọn</b> đáp án. Đọc lời giải để nắm cách làm; lần sau nhớ chọn trước khi vào thảo luận.';
  }
  if(ds)html+=quizCrDsCompareHtml();
  html+='</div>';
  return html;
}
function quizCrAfterListenHtml(solId){
  return quizCrVerdictHtml()+'<div class="quizCrSol" id="'+esc(solId||'')+'"><h3>📗 Lời giải</h3>'+quizCrLoiGiaiHtml()+'</div>';
}
function quizCrOnPlayAllDone(){
  QUIZ_TTS_ON=false;QUIZ_TTS_KIND='';QUIZ_CR_PLAY=-1;
  try{syncQuizReadBtn()}catch(e){}
  let d=QUIZ_DEBATE_BY_Q[CUR]||{};
  d.heard=true;QUIZ_DEBATE_BY_Q[CUR]=d;
  let st=document.getElementById('quizCrStatus');if(st)st.textContent='Đã nghe xong — xem lời giải';
  renderQuizClassRoom();
  try{
    if(quizCrPhone())quizCrSetTab('lg');
    else{
      let sol=document.getElementById('quizCrSolLeft')||document.getElementById('quizCrSolChat');
      if(sol)sol.scrollIntoView({behavior:'smooth',block:'nearest'});
    }
  }catch(e2){}
}
function quizCrProblemHtml(){
  let q=currentQuestion()||{};
  let id=String(q.ID||'').trim();
  let heard=quizCrHeard();
  let html='<div class="quizCrCard"><h2>📘 Câu hỏi'+(id?(' · '+esc(id)):'')+'</h2>';
  html+='<div class="quizCrStem">'+(typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(q.CauHoi||''):esc(q.CauHoi||''))+'</div>';
  try{
    if(String(q.HinhAnh||'').trim()&&typeof hinhanhIsSolutionFigure==='function'&&!hinhanhIsSolutionFigure(q)&&typeof buildQimgHtml==='function'){
      html+='<div class="quizCrFig">'+buildQimgHtml(q.HinhAnh)+'</div>';
    }
  }catch(e){}
  let opts=[];
  for(let L of ['A','B','C','D']){if(String(q[L]||'').trim())opts.push(L)}
  let picked=quizCrPickedLetter(q);
  if(opts.length){
    html+='<div class="quizCrAnswers">';
    let isDs=String(q.Dang||'')==='Đúng sai';
    let dsRows=heard&&isDs?quizCrDsRows(q):[];
    for(let i=0;i<opts.length;i++){
      let L=opts[i];
      let body=typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(isDs?q[L]:(stripOptionPrefix?stripOptionPrefix(q[L],L):q[L])):esc(q[L]);
      if(isDs){
        let rr=dsRows.filter(function(x){return x.letter===L})[0]||null;
        let idx='ABCD'.indexOf(L);
        let chArr=Array.isArray(ANSWERS[CUR])?ANSWERS[CUR]:[];
        let rawPick=String((rr&&rr.chosen)||(idx>=0?chArr[idx]:'')||'').trim();
        if(rawPick==='D'||rawPick==='d')rawPick='Đ';
        let emLab=quizCrDsLabel(rawPick);
        let cls='quizCrAnswer';
        let meta='';
        if(heard&&rr){
          if(rr.ok===true)cls+=' correct';
          else if(rr.ok===false)cls+=' wrong';
          else cls+=' nonepick';
          let key=quizCrDsLabel(rr.correct)||'?';
          let em=emLab||'chưa chọn';
          let mark=rr.ok===true?' · ✓ em đúng ý này':(rr.ok===false?' · ✗ em chưa đúng ý này':' · em chưa chọn ý này');
          meta='<div class="quizCrDsMeta">Đáp án: <b>'+esc(key)+'</b> · Em chọn: <b>'+esc(em)+'</b>'+mark+'</div>';
        }else if(emLab){
          cls+=' picked';
          meta='<div class="quizCrDsMeta">Em chọn: <b>'+esc(emLab)+'</b></div>';
        }
        html+='<div class="'+cls+'"><div><b>'+esc(L)+'.</b> '+body+'</div>'+meta+'</div>';
      }else{
        let ok=heard&&quizCrLetterCorrect(q,L);
        let mine=picked===L;
        let cls='quizCrAnswer'+(ok?' correct':'')+(mine&&heard&&!ok?' wrong':'')+(mine?' picked':'');
        html+='<div class="'+cls+'">'+(ok?'<b>':'')+esc(L)+'. '+(ok?'</b>':'')+body+(ok?' ✓':'')+(mine&&!heard?' · em chọn':'')+(mine&&heard&&ok?' · em chọn đúng':'')+(mine&&heard&&!ok?' · em chọn':'')+'</div>';
      }
    }
    html+='</div>';
  }
  if(heard)html+='<button type="button" class="quizCrOpenLg" onclick="quizCrSetTab(\'lg\')">📗 Xem lời giải và nhận xét</button>'+quizCrAfterListenHtml('quizCrSolLeft');
  else html+='<div class="quizCrWait">🎧 Nghe hết thảo luận (bấm <b>Phát toàn bộ</b>) để xem lời giải và nhận xét bài làm của em: đúng, chưa đúng, hoặc chưa chọn.</div>';
  html+='</div>';
  return html;
}
function quizCrScriptText(){
  let d=QUIZ_DEBATE_BY_Q[CUR]||{};
  let ta=document.getElementById('quizScriptText');
  let txt=String((ta&&ta.value)||d.script||'').trim();
  if(txt)return txt;
  try{return localQuizClassScript()}catch(e){return ''}
}
function ensureQuizClassRoom(){
  let el=document.getElementById('quizClassRoom');
  if(el&&document.getElementById('quizCrTabs')&&document.getElementById('quizCrLgPane')&&document.getElementById('quizCrEditor'))return el;
  if(el)el.remove();
  el=document.createElement('div');
  el.id='quizClassRoom';
  el.className='quizClassRoom hide cr-tab-chat';
  el.innerHTML='<div class="quizCrBar"><div><div class="quizCrBrand">🎓 Classroom</div><div class="quizCrSub">Lớp Học Thầy Minh · nghe hết mới xem lời giải</div></div><div class="quizCrBtns"><button type="button" class="quizCrBtn" onclick="stopQuizCrPlay()">⏹ Dừng</button><button type="button" class="quizCrBtn primary" id="btnCrPlayAll" onclick="playQuizCrAll()">▶ Phát</button><button type="button" class="quizCrBtn ghost quizCrDeskOnly" onclick="makeQuizClassScript({auto:false})">✨ Tạo kịch bản</button><button type="button" class="quizCrBtn" onclick="closeQuizClassRoom()">✕ Đóng</button></div></div><div class="quizCrTabs" id="quizCrTabs"><button type="button" class="quizCrTab" data-tab="de" onclick="quizCrSetTab(\'de\')">📘 Đề</button><button type="button" class="quizCrTab on" data-tab="chat" onclick="quizCrSetTab(\'chat\')">💬 Thảo luận</button><button type="button" class="quizCrTab" data-tab="lg" id="quizCrTabLg" onclick="quizCrSetTab(\'lg\')">📗 Lời giải</button></div><div class="quizCrMain"><section class="quizCrProblem" id="quizCrProblem"></section><section class="quizCrLgPane" id="quizCrLgPane"></section><section class="quizCrChat"><div class="quizCrHead"><b>💬 Thảo luận</b><span class="quizCrStatus" id="quizCrStatus">Sẵn sàng</span></div><div id="quizCrEditor" class="quizCrEditor hide"></div><div class="quizCrMsgs" id="quizCrMsgs"></div><div class="quizCrFoot"><div class="quizCrNow" id="quizCrNow">Phát toàn bộ — lời giải hiện sau khi nghe hết</div><div class="quizCrProg"><div class="quizCrBarFill" id="quizCrBarFill"></div></div><div class="quizCrTools"><span>Tốc độ</span><select id="quizCrSpeed"><option value="0.85">0.85</option><option value="0.95" selected>0.95</option><option value="1.05">1.05</option><option value="1.15">1.15</option></select><span>×</span><button type="button" class="quizCrBtn ghost quizCrDeskOnly" onclick="downloadQuizClassScript()">Tải TXT</button><button type="button" class="quizCrBtn ghost quizCrDeskOnly" onclick="showQuizDebateKeyBox();closeQuizClassRoom()">🔑 Key</button></div><div class="quizCrAskRow"><button type="button" class="btn2 btnSmall" id="btnCrListen" onclick="toggleDebateListen()" title="Nói ý kiến">🎤 Nói</button><textarea id="quizCrAsk" rows="2" placeholder="Nói hoặc gõ ý kiến…" onkeydown="if(event.key===\'Enter\'&&!event.shiftKey){event.preventDefault();sendQuizDebateFollowup()}"></textarea><button type="button" class="btnStartStrong btnSmall" id="btnCrAsk" onclick="sendQuizDebateFollowup()">Gửi</button></div></div></section></div>';
  document.body.appendChild(el);
  if(!window._quizCrEsc){
    window._quizCrEsc=true;
    document.addEventListener('keydown',function(ev){if(ev.key==='Escape'&&QUIZ_CR_WANT)closeQuizClassRoom()});
  }
  return el;
}
function quizCrPhone(){try{return window.matchMedia&&window.matchMedia('(max-width:850px)').matches}catch(e){return false}}
function quizCrSetTab(tab){
  tab=String(tab||'chat');
  if(tab==='lg'&&!quizCrHeard()){tab='chat';let st=document.getElementById('quizCrStatus');if(st)st.textContent='Nghe hết thảo luận rồi mới mở lời giải'}
  let el=ensureQuizClassRoom();
  el.classList.remove('cr-tab-de','cr-tab-chat','cr-tab-lg');
  el.classList.add('cr-tab-'+tab);
  el.querySelectorAll('.quizCrTab').forEach(function(b){
    let t=b.getAttribute('data-tab');
    b.classList.toggle('on',t===tab);
    if(t==='lg')b.disabled=!quizCrHeard();
  });
  if(tab==='lg'){
    let pane=document.getElementById('quizCrLgPane');
    if(pane){pane.innerHTML='<div class="quizCrCard"><h2>📗 Sau thảo luận</h2>'+quizCrAfterListenHtml('quizCrSolPhone')+'</div>';try{typesetNow([pane])}catch(e){}}
  }
}
function openQuizClassRoom(){
  QUIZ_CR_WANT=true;
  let el=ensureQuizClassRoom();
  el.classList.remove('hide');
  document.body.classList.add('quiz-classroom-open');
  window._QUIZ_CR_CUR=CUR;
  renderQuizClassRoom();
  if(quizCrPhone())quizCrSetTab(quizCrHeard()?'lg':'chat');
}
function closeQuizClassRoom(){
  QUIZ_CR_WANT=false;
  stopQuizCrPlay();
  document.body.classList.remove('quiz-classroom-open');
  let el=document.getElementById('quizClassRoom');
  if(el)el.classList.add('hide');
}
function quizCrRate(){
  let el=document.getElementById('quizCrSpeed');
  let r=parseFloat(el&&el.value);
  if(r>=0.7&&r<=1.35)return r;
  return quizTtsRate();
}
function quizCrHasSplitVoices(){
  let list=typeof quizTtsListViVoices==='function'?quizTtsListViVoices():[];
  let hasF=false,hasM=false;
  for(let i=0;i<list.length;i++){
    let g=quizTtsVoiceGender(list[i]);
    if(g==='Nữ')hasF=true;
    if(g==='Nam')hasM=true;
  }
  return !!(hasF&&hasM);
}
function quizCrVoiceFor(who){
  let list=typeof quizTtsListViVoices==='function'?quizTtsListViVoices():[];
  if(!list.length)return pickQuizViVoice();
  who=quizCrNormWho(who);
  let female=/^(An|Chi)$/.test(who);
  let teacher=/Thầy|Trợ/.test(who);
  if(female){
    for(let i=0;i<list.length;i++){if(quizTtsVoiceGender(list[i])==='Nữ'||/hoai|female|nữ|my|linh/i.test(list[i].name||''))return list[i]}
  }
  if(teacher||!female){
    for(let i=0;i<list.length;i++){if(quizTtsVoiceGender(list[i])==='Nam'||/nam\s*minh|namminh|\bmale\b/i.test(list[i].name||''))return list[i]}
  }
  return list[0]||pickQuizViVoice();
}
function quizCrVoiceStyle(who){
  who=quizCrNormWho(who);
  let voice=quizCrVoiceFor(who);
  let pitch=1,rateMul=1;
  if(who==='Thầy Minh'){pitch=0.72;rateMul=0.93}
  else if(who==='Trợ lý'){pitch=0.86;rateMul=0.98}
  else if(who==='Dũng'){pitch=0.66;rateMul=0.95}
  else if(who==='Bình'){pitch=0.8;rateMul=0.97}
  else if(who==='An'){pitch=1.22;rateMul=1.02}
  else if(who==='Chi'){pitch=1.38;rateMul=1.05}
  else if(who==='Em'){pitch=1.1;rateMul=1}
  return {voice:voice,pitch:pitch,rateMul:rateMul};
}
function canEditQuizClassScript(){try{return typeof isAdminViewer==='function'&&isAdminViewer()}catch(e){return false}}
function quizCrCastList(){return ['An','Bình','Chi','Dũng','Thầy Minh','Trợ lý']}
function quizCrLineIsBlank(t){t=String(t||'').trim();return !t||t==='…'||t==='(gõ ý kiến)'}
function quizCrLinesToScript(lines){return (lines||[]).map(function(r){return quizCrNormWho(r.who||'An')+': '+(String(r.text||'').replace(/\s+/g,' ').trim()||'(gõ ý kiến)')}).join('\n')}
function quizCrReadEditorLines(){let host=document.getElementById('quizCrEditor');if(!host)return null;let rows=[];host.querySelectorAll('.quizCrEditRow').forEach(function(row){rows.push({who:quizCrNormWho((row.querySelector('.quizCrEditWho')||{}).value||'An'),text:String((row.querySelector('.quizCrEditText')||{}).value||'').trim()})});return rows}
function quizCrBriefValue(){let el=document.getElementById('quizCrBrief');if(el)return String(el.value||'').trim();return String((QUIZ_DEBATE_BY_Q[CUR]||{}).brief||'').trim()}
function quizCrSaveEditorToScript(){if(!canEditQuizClassScript())return;let rows=quizCrReadEditorLines();if(!rows)return;let d=QUIZ_DEBATE_BY_Q[CUR]||{};d.brief=quizCrBriefValue();d.script=quizCrLinesToScript(rows);QUIZ_DEBATE_BY_Q[CUR]=d;let ta=document.getElementById('quizScriptText');if(ta)ta.value=d.script||''}
function quizCrOnBriefInput(){let d=QUIZ_DEBATE_BY_Q[CUR]||{};d.brief=quizCrBriefValue();QUIZ_DEBATE_BY_Q[CUR]=d}
function quizCrOnEditText(){quizCrSaveEditorToScript()}
function quizCrOnEditWho(){quizCrSaveEditorToScript()}
function quizCrFillEditor(force){
  let host=document.getElementById('quizCrEditor');if(!host)return;
  if(!canEditQuizClassScript()){host.classList.add('hide');host.innerHTML='';return}
  host.classList.remove('hide');
  if(!force&&host.getAttribute('data-qcur')===String(CUR)&&host.querySelector('.quizCrBrief'))return;
  let d=QUIZ_DEBATE_BY_Q[CUR]||{};let lines=parseQuizClassScript(d.script||'');let brief=String(d.brief||'');
  let html='<div class="quizCrEditorHead"><b>ADMIN soạn kịch bản</b><span class="muted">Gán nhân vật · sửa ý kiến · Tạo kịch bản · rồi mới Phát</span></div>';
  html+='<textarea id="quizCrBrief" class="quizCrBrief" rows="2" placeholder="Góp ý / yêu cầu: An nêu dữ kiện. Bình phản biện A. Thầy Minh chốt đáp án…" oninput="quizCrOnBriefInput()">'+esc(brief)+'</textarea>';
  html+='<div class="quizCrEditorActs"><button type="button" class="quizCrBtn ghost" onclick="makeQuizClassScript({auto:false})">✨ Tạo kịch bản</button><select id="quizCrAddWho">'+quizCrCastList().map(function(n){return '<option value="'+n+'">'+n+'</option>'}).join('')+'</select><button type="button" class="quizCrBtn ghost" onclick="quizCrAddEditLine()">➕ Thêm lời</button><button type="button" class="quizCrBtn ghost" onclick="quizCrApplyEditor(true)">💾 Cập nhật thoại</button></div>';
  if(!lines.length)html+='<div class="muted" style="margin:0 0 8px">Chưa có lời. Viết yêu cầu rồi Tạo kịch bản, hoặc Thêm lời rồi gõ tay.</div>';
  lines.forEach(function(row,i){let who=quizCrNormWho(row.who);let body=quizCrLineIsBlank(row.text)?'':String(row.text||'');html+='<div class="quizCrEditRow"><select class="quizCrEditWho" onchange="quizCrOnEditWho()">'+quizCrCastList().map(function(n){return '<option value="'+n+'"'+(n===who?' selected':'')+'>'+n+'</option>'}).join('')+'</select><textarea class="quizCrEditText" rows="2" placeholder="Ý kiến nhân vật này phát biểu…" oninput="quizCrOnEditText()">'+esc(body)+'</textarea><div class="quizCrEditActs"><button type="button" onclick="quizCrMoveEditLine('+i+',-1)">↑</button><button type="button" onclick="quizCrMoveEditLine('+i+',1)">↓</button><button type="button" onclick="quizCrDelEditLine('+i+')">✕</button></div></div>'});
  host.innerHTML=html;host.setAttribute('data-qcur',String(CUR));
}
function quizCrApplyEditor(rerender){quizCrSaveEditorToScript();if(rerender){quizCrFillEditor(true);if(QUIZ_CR_WANT)renderQuizClassRoom()}}
function quizCrAddEditLine(){quizCrSaveEditorToScript();let who=quizCrNormWho((document.getElementById('quizCrAddWho')||{}).value||'An');let d=QUIZ_DEBATE_BY_Q[CUR]||{};let lines=parseQuizClassScript(d.script||'');lines.push({who:who,text:''});d.script=quizCrLinesToScript(lines);QUIZ_DEBATE_BY_Q[CUR]=d;quizCrFillEditor(true)}
function quizCrDelEditLine(i){quizCrSaveEditorToScript();let d=QUIZ_DEBATE_BY_Q[CUR]||{};let lines=parseQuizClassScript(d.script||'');lines.splice(i,1);d.script=quizCrLinesToScript(lines);QUIZ_DEBATE_BY_Q[CUR]=d;quizCrFillEditor(true);if(QUIZ_CR_WANT)renderQuizClassRoom()}
function quizCrMoveEditLine(i,dir){quizCrSaveEditorToScript();let d=QUIZ_DEBATE_BY_Q[CUR]||{};let lines=parseQuizClassScript(d.script||'');let j=i+dir;if(j<0||j>=lines.length)return;let t=lines[i];lines[i]=lines[j];lines[j]=t;d.script=quizCrLinesToScript(lines);QUIZ_DEBATE_BY_Q[CUR]=d;quizCrFillEditor(true)}
function renderQuizClassRoom(){
  if(!QUIZ_CR_WANT)return;
  let el=ensureQuizClassRoom();
  let prob=document.getElementById('quizCrProblem');
  if(prob)prob.innerHTML=quizCrProblemHtml();
  let box=document.getElementById('quizCrMsgs');
  if(!box)return;
  let d=QUIZ_DEBATE_BY_Q[CUR]||{};
  let busy=QUIZ_DEBATE_LOADING===CUR;
  let lines=parseQuizClassScript(quizCrScriptText());
  if(!lines.length&&!busy)lines=parseQuizClassScript(localQuizClassScript());
  QUIZ_CR_LINES=[];
  let html='';
  let analysis=String(d.final||d.gemini||d.claude||'').trim();
  if(analysis){
    html+='<div class="quizCrMsg teacher quizCrAiNote"><div class="quizCrAv">⚡</div><div class="quizCrBubble"><details><summary class="quizCrName" style="cursor:pointer">Trợ lý Thầy Minh · nhận xét 1 bước</summary><div style="margin-top:8px">'+(typeof quizDebateCardHtml==='function'?quizDebateCardHtml(analysis,''):esc(analysis))+'</div></details></div></div>';
  }
  if(busy)html+='<div class="quizCrSplit">ĐANG PHẢN BIỆN LỜI GIẢI…</div>';
  else html+='<div class="quizCrSplit">THẢO LUẬN CỦA LỚP</div>';
  lines.forEach(function(row,i){
    let meta=quizCrMeta(row.who);
    let speak=typeof quizSpeechPlain==='function'?quizSpeechPlain(row.text):String(row.text||'');
    QUIZ_CR_LINES.push({who:meta.who,text:speak,html:typeof prepareDebateLatex==='function'?prepareDebateLatex(row.text):row.text,kind:'script'});
    let idx=QUIZ_CR_LINES.length-1;
    html+='<div class="quizCrMsg '+meta.role+(meta.right?' right':'')+'" id="quizCrMsg'+idx+'"><div class="quizCrAv">'+meta.av+'</div><div class="quizCrBubble"><div class="quizCrName">'+esc(meta.who)+' <button type="button" class="quizCrPlay" onclick="playQuizCrLine('+idx+',false)" title="Đọc câu này">🔊</button></div><div>'+(typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(QUIZ_CR_LINES[idx].html):esc(row.text))+'</div></div></div>';
  });
  let chat=d.chat||[];
  if(chat.length){
    html+='<div class="quizCrSplit">EM HỎI THÊM</div>';
    chat.forEach(function(m){
      let isUser=m.role==='user';
      let who=isUser?'Em':'Trợ lý';
      let meta=quizCrMeta(who);
      let raw=String(m.text||'');
      let speak=typeof quizSpeechPlain==='function'?quizSpeechPlain(raw):raw;
      QUIZ_CR_LINES.push({who:meta.who,text:speak,html:typeof prepareDebateLatex==='function'?prepareDebateLatex(raw):raw,kind:'follow'});
      let idx=QUIZ_CR_LINES.length-1;
      html+='<div class="quizCrMsg '+meta.role+(meta.right?' right':'')+'" id="quizCrMsg'+idx+'"><div class="quizCrAv">'+meta.av+'</div><div class="quizCrBubble"><div class="quizCrName">'+esc(meta.who)+' <button type="button" class="quizCrPlay" onclick="playQuizCrLine('+idx+',false)" title="Đọc câu này">🔊</button></div><div>'+(typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(QUIZ_CR_LINES[idx].html):esc(raw))+'</div></div></div>';
    });
  }
  box.innerHTML=html||'<div class="muted">Chưa có thoại. Bấm Tạo kịch bản.</div>';
  if(quizCrHeard()){
    let extra=document.createElement('div');
    extra.className='quizCrRevealChat';
    extra.innerHTML='<div class="quizCrSplit">SAU THẢO LUẬN</div>'+quizCrAfterListenHtml('quizCrSolChat');
    box.appendChild(extra);
  }
  let st=document.getElementById('quizCrStatus');
  if(st)st.textContent=busy?'Đang phản biện…':(quizCrHeard()?'Đã nghe xong — xem lời giải':(analysis?'Nghe hết để xem lời giải':'Sẵn sàng'));
  try{quizCrFillEditor(false)}catch(eEd){}
  try{
    let el=document.getElementById('quizClassRoom');
    let tab='chat';
    if(el){if(el.classList.contains('cr-tab-de'))tab='de';else if(el.classList.contains('cr-tab-lg'))tab='lg'}
    quizCrSetTab(tab);
  }catch(eTab){}
  try{requestAnimationFrame(function(){typesetNow([prob,box]);setTimeout(function(){typesetNow([prob,box])},160)})}catch(e){}
  if(!quizCrHeard()||(d.chat&&d.chat.length)){
    try{box.scrollTop=box.scrollHeight}catch(e3){}
  }
}
function stopQuizCrPlay(){
  QUIZ_CR_STOP=true;QUIZ_CR_PLAY=-1;
  try{if(typeof speechSynthesis!=='undefined')speechSynthesis.cancel()}catch(e){}
  QUIZ_TTS_ON=false;QUIZ_TTS_KIND='';QUIZ_TTS_CHUNKS=[];QUIZ_TTS_IDX=0;
  document.querySelectorAll('.quizCrMsg.active').forEach(function(n){n.classList.remove('active')});
  let st=document.getElementById('quizCrStatus');if(st&&QUIZ_CR_WANT)st.textContent='Đã dừng';
  try{syncQuizReadBtn()}catch(e3){}
}
function playQuizCrLine(i,auto){
  i=parseInt(i,10)||0;
  if(i<0||i>=QUIZ_CR_LINES.length){if(auto)quizCrOnPlayAllDone();return}
  if(auto&&QUIZ_CR_LINES[i]&&QUIZ_CR_LINES[i].kind==='follow'){
    let n=i;while(n<QUIZ_CR_LINES.length&&QUIZ_CR_LINES[n].kind==='follow')n++;
    if(n<QUIZ_CR_LINES.length){playQuizCrLine(n,true);return}
    quizCrOnPlayAllDone();return;
  }
  if(typeof speechSynthesis==='undefined'){alert('Trình duyệt không hỗ trợ đọc. Dùng Chrome hoặc Edge.');return}
  QUIZ_CR_STOP=false;QUIZ_CR_PLAY=i;
  if(quizCrPhone())quizCrSetTab('chat');
  try{speechSynthesis.cancel()}catch(e){}
  document.querySelectorAll('.quizCrMsg.active').forEach(function(n){n.classList.remove('active')});
  let node=document.getElementById('quizCrMsg'+i);
  if(node){node.classList.add('active');try{node.scrollIntoView({behavior:'smooth',block:'center'})}catch(e2){}}
  let row=QUIZ_CR_LINES[i];
  let st=document.getElementById('quizCrStatus');if(st)st.textContent='Đang đọc: '+row.who;
  let now=document.getElementById('quizCrNow');if(now)now.textContent=(i+1)+'/'+QUIZ_CR_LINES.length+' · '+row.who;
  let bar=document.getElementById('quizCrBarFill');if(bar)bar.style.width=(((i+1)/Math.max(1,QUIZ_CR_LINES.length))*100)+'%';
  let body=String(row.text||'').trim()||row.who;
  let speak=quizCrHasSplitVoices()?body:(row.who+'. '+body);
  let u=new SpeechSynthesisUtterance(speak);
  let style=quizCrVoiceStyle(row.who);
  u.lang='vi-VN';
  u.rate=Math.max(0.7,Math.min(1.35,(quizCrRate()||0.95)*(style.rateMul||1)));
  u.pitch=Math.max(0.5,Math.min(1.6,style.pitch||1));
  let v=style.voice;if(v){u.voice=v;u.lang=v.lang&&String(v.lang).toLowerCase().indexOf('vi')===0?v.lang:'vi-VN'}
  QUIZ_TTS_ON=true;QUIZ_TTS_KIND='classroom';
  try{syncQuizReadBtn()}catch(e4){}
  u.onend=function(){
    if(auto&&!QUIZ_CR_STOP){
      let n=i+1;
      while(n<QUIZ_CR_LINES.length&&QUIZ_CR_LINES[n].kind==='follow')n++;
      if(n<QUIZ_CR_LINES.length)setTimeout(function(){playQuizCrLine(n,true)},220);
      else quizCrOnPlayAllDone();
    }
  };
  u.onerror=function(){stopQuizCrPlay()};
  try{speechSynthesis.speak(u)}catch(e5){stopQuizCrPlay();alert('Không đọc được: '+(e5.message||e5))}
}
function playQuizCrAll(){
  try{if(canEditQuizClassScript())quizCrSaveEditorToScript()}catch(eSv){}
  if(!QUIZ_CR_LINES.length)renderQuizClassRoom();
  if(!QUIZ_CR_LINES.length){alert('Chưa có kịch bản. Bấm Tạo kịch bản.');return}
  if(quizCrPhone())quizCrSetTab('chat');
  let start=0;
  while(start<QUIZ_CR_LINES.length&&QUIZ_CR_LINES[start].kind==='follow')start++;
  playQuizCrLine(start,true);
}
function quizDebateChatInnerHtml(){return '<div class="quizDebateChatHint muted">Bấm <b>🎤 Nói</b> để trợ lý nghe ý kiến em, rồi phán <b>đúng / sai</b>, nêu công thức $...$ và nhận xét bám sát đề. Cũng có thể gõ.</div><div id="quizDebateChatLog" class="quizDebateChatLog"></div><div class="quizDebateChatRow"><button type="button" class="btn2 btnSmall" id="btnDebateListen" onclick="toggleDebateListen()" title="Nói ý kiến — AI nghe rồi phản biện">🎤 Nói</button><textarea id="quizDebateAsk" rows="2" placeholder="Nói hoặc gõ ý kiến — trợ lý nêu công thức, bám sát đề…" onkeydown="if(event.key===\'Enter\'&&!event.shiftKey){event.preventDefault();sendQuizDebateFollowup()}"></textarea><button type="button" class="btnStartStrong btnSmall" id="btnDebateAsk" onclick="sendQuizDebateFollowup()">Gửi</button></div>'}
let DEBATE_SR=null,DEBATE_SR_ON=false,DEBATE_SR_FINAL='';
function debateSpeechEngine(){let SR=window.SpeechRecognition||window.webkitSpeechRecognition;return SR?new SR():null}
function debateListenBtnSet(on){for(let id of ['btnDebateListen','btnCrListen']){let b=document.getElementById(id);if(!b)continue;b.classList.toggle('listening',!!on);b.textContent=on?'⏹ Dừng':'🎤 Nói';b.disabled=false}}
function stopDebateListen(andSend){DEBATE_SR_ON=false;try{if(DEBATE_SR)DEBATE_SR.stop()}catch(e){}DEBATE_SR=null;debateListenBtnSet(false);if(andSend){let ta=debateAskEl();let msg=String((ta&&ta.value)||DEBATE_SR_FINAL||'').trim();if(msg)sendQuizDebateFollowup(true)}}
function toggleDebateListen(){if(DEBATE_SR_ON){stopDebateListen(true);return}if(!canUseQuizDebate()){alert('Hãy làm và chấm câu này trước.');return}stopQuizQuestionSpeech();let rec=debateSpeechEngine();if(!rec){alert('Trình duyệt không hỗ trợ nghe giọng nói.\nDùng Chrome hoặc Edge (có mic), hoặc gõ vào ô.');return}DEBATE_SR_FINAL='';DEBATE_SR=rec;DEBATE_SR_ON=true;rec.lang='vi-VN';rec.continuous=true;rec.interimResults=true;rec.maxAlternatives=1;rec.onresult=function(ev){let final='',interim='';for(let i=0;i<ev.results.length;i++){let t=String(ev.results[i][0]&&ev.results[i][0].transcript||'');if(ev.results[i].isFinal)final+=t+' ';else interim+=t}if(final)DEBATE_SR_FINAL=String(final).replace(/\s+/g,' ').trim();let ta=debateAskEl();if(ta)ta.value=String(DEBATE_SR_FINAL+(interim?(' '+interim):'')).replace(/\s+/g,' ').trim()};rec.onerror=function(ev){let err=String((ev&&ev.error)||'');if(err==='not-allowed'||err==='service-not-allowed')alert('Chưa cho phép mic. Hãy cho phép microphone rồi bấm 🎤 Nói lại.');else if(err==='no-speech'){let st=document.getElementById('quizDebateStatus');if(st)st.textContent='Chưa nghe thấy. Nói lại gần mic.'}DEBATE_SR_ON=false;debateListenBtnSet(false)};rec.onend=function(){if(!DEBATE_SR_ON)return;DEBATE_SR_ON=false;debateListenBtnSet(false);let ta=debateAskEl();let msg=String((ta&&ta.value)||DEBATE_SR_FINAL||'').trim();if(msg)sendQuizDebateFollowup(true)};try{rec.start();debateListenBtnSet(true);let st=document.getElementById('quizDebateStatus');if(st)st.textContent='Đang nghe… hãy nói ý kiến của em.'}catch(e){DEBATE_SR_ON=false;debateListenBtnSet(false);alert('Không bật mic được: '+(e.message||e))}}
function syncQuizDebateBtn(){let on=!!(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='debate');let busy=QUIZ_DEBATE_LOADING===CUR;let allow=canUseQuizDebate();for(let id of ['btnDebateLoiGiai','btnFsDebateLoiGiai','btnPanelDebate']){let x=document.getElementById(id);if(!x)continue;x.classList.toggle('hide',!allow);x.classList.toggle('ttsBusy',busy);x.disabled=busy;if(busy)x.textContent=(id==='btnFsDebateLoiGiai'?'⏳ …':'⏳ Đang phản biện…');else x.textContent=(id==='btnFsDebateLoiGiai'?'⚖ Phản biện':'⚖ Phản biện')}let rd=document.getElementById('btnReadDebate');if(rd){rd.classList.toggle('ttsBtnOn',on);rd.textContent=on?'⏸ Dừng phản biện':'🔊 Đọc phản biện'}}

function quizScriptAnalysisFrom(d){
  d=d||QUIZ_DEBATE_BY_Q[CUR]||{};
  let mode=String((document.getElementById('quizScriptSource')||{}).value||'final');
  if(mode==='gemini')return d.gemini||'';
  if(mode==='claude')return d.claude||'';
  if(mode==='source')return '';
  return d.final||d.gemini||d.claude||'';
}
function localQuizClassScript(){
  let q=currentQuestion()||{};
  let names=['An','Bình','Chi','Dũng'];
  let de=quizSpeechPlain(q.CauHoi||'Đề đang trống.');
  let dang=String(q.Dang||q.Chuong||'bài này').trim();
  let lines=['An: Đề này cho: '+de,'Bình: Khoan chọn vội. Dễ bị bẫy nếu áp sai công thức, không khớp số liệu đề.'];
  let opts=[];
  for(let L of ['A','B','C','D']){if(String(q[L]||'').trim())opts.push([L,quizSpeechPlain(q[L])])}
  if(opts.length){
    lines.push(names[0]+': Mình nghiêng '+opts[0][0]+': '+opts[0][1]);
    if(opts[1])lines.push(names[1]+': Không đồng ý ngay. '+opts[1][0]+' cũng nghe có lý: '+opts[1][1]);
    if(opts[2])lines.push(names[2]+': Hai hướng đó xung đột. '+opts[2][0]+': '+opts[2][1]+' — đề đang hỏi gì, công thức nào mới khớp dữ kiện?');
    if(opts[3])lines.push(names[3]+': Còn '+opts[3][0]+': '+opts[3][1]+'. Có thể là nhiễu nếu quên điều kiện trên đề.');
  }else{
    lines.push('Chi: Tách dữ kiện đề: cái nào cho sẵn, cái nào cần tìm.');
    lines.push('Dũng: Rồi mới nêu công thức, thay đúng số trên đề.');
  }
  lines.push('Chi: Dạng '+dang+' thì công thức xương sống là gì? Đừng nhớ máy móc.');
  let da=String(q.DapAn||'').trim();
  lines.push('Thầy Minh: Tranh luận tốt. Bám sát đề, nêu đúng công thức của bài, thay đúng số liệu rồi mới kết luận. Theo nguồn, đáp án là '+(da||'cần đối chiếu lại Sheet')+'. Nếu nguồn lệch đề thì nói thẳng. Đây là draft máy, chưa ghi Sheet.');
  return lines.join('\n');
}
async function makeQuizClassScript(opts){
  opts=opts||{};
  if(!canUseQuizDebate()){if(!opts.auto)alert('Hãy làm và chấm câu này trước.');return}
  let d=QUIZ_DEBATE_BY_Q[CUR]||{};
  if(opts.auto&&d.scriptAi){if(QUIZ_CR_WANT)renderQuizClassRoom();return}
  let st=document.getElementById('quizScriptStatus');
  let ta=document.getElementById('quizScriptText');
  let cr=document.getElementById('quizCrStatus');
  let prov=String((document.getElementById('quizScriptProvider')||{}).value||'gemini');
  if(prov==='local'){
    let txt=localQuizClassScript();
    if(ta)ta.value=txt;
    d.script=txt;QUIZ_DEBATE_BY_Q[CUR]=d;
    if(st)st.textContent='Đã tạo mẫu local. Draft máy — không ghi Sheet.';
    openQuizClassRoom();
    try{quizCrFillEditor(true)}catch(eEd){}
    return;
  }
  if(st)st.textContent='Đang viết kịch bản…';
  if(cr)cr.textContent='Đang viết kịch bản lớp…';
  try{
    let lg='';try{lg=currentQuizLoiGiaiText()||''}catch(e){lg=String((currentQuestion()||{}).LoiGiai||'')}
    try{if(canEditQuizClassScript())quizCrSaveEditorToScript()}catch(eSv){}
    let body=quizDebateRequestBody({sid:SID,index:CUR,answer:ANSWERS[CUR],loigiai:lg,analysis:quizScriptAnalysisFrom(d),provider:prov});
    let brief=typeof quizCrBriefValue==='function'?quizCrBriefValue():'';
    if(brief)body.brief=brief;
    let j=await api('/api/quiz/debate-script',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),timeoutMs:28000,skipLoginRedirect:true},0);
    let txt=String((j&&j.text)||'').trim()||localQuizClassScript();
    if(ta)ta.value=txt;
    d.script=txt;d.scriptAi=!(j&&j.provider==='LOCAL');QUIZ_DEBATE_BY_Q[CUR]=d;
    if(st)st.textContent='Đã tạo kịch bản ('+(j.provider||prov)+'). Draft máy — không ghi Sheet.'+(j.warning?(' · '+j.warning):'');
    if(cr)cr.textContent='Đã có kịch bản lớp';
    openQuizClassRoom();
    try{quizCrFillEditor(true)}catch(eEd){}
  }catch(e){
    let txt=localQuizClassScript();
    if(ta)ta.value=txt;
    d.script=txt;QUIZ_DEBATE_BY_Q[CUR]=d;
    if(st)st.textContent='AI lỗi, đã dùng mẫu local. '+(e.message||e);
    if(cr)cr.textContent='Dùng kịch bản nháp';
    openQuizClassRoom();
    try{quizCrFillEditor(true)}catch(eEd){}
  }
}
function readQuizClassScript(){
  if(QUIZ_CR_WANT){playQuizCrAll();return}
  let ta=document.getElementById('quizScriptText');
  let txt=String((ta&&ta.value)||'').trim();
  if(!txt){alert('Chưa có kịch bản. Bấm Tạo kịch bản trước.');return}
  startQuizViSpeech(quizSpeechPlain(txt),'debate','Chưa có kịch bản để đọc.');
}
function downloadQuizClassScript(){
  let ta=document.getElementById('quizScriptText');
  let txt=String((ta&&ta.value)||'').trim();
  if(!txt){alert('Chưa có kịch bản để tải.');return}
  let q=currentQuestion()||{};
  let name='kich_ban_'+(q.ID||('cau'+(CUR+1)))+'.txt';
  let b=new Blob([txt],{type:'text/plain;charset=utf-8'}),u=URL.createObjectURL(b),a=document.createElement('a');
  a.href=u;a.download=name;a.click();setTimeout(function(){URL.revokeObjectURL(u)},500);
  let st=document.getElementById('quizScriptStatus');if(st)st.textContent='Đã tải '+name+' — không ghi Sheet.';
}
function cancelQuizDebate(){let ctrl=QUIZ_DEBATE_ABORT_CTRL;QUIZ_DEBATE_LOADING=-1;QUIZ_DEBATE_ABORT_CTRL=null;if(ctrl){try{ctrl.abort()}catch(e){}}syncQuizDebateBtn()}
function ensureQuizDebateStudioBox(){
  let panel=document.getElementById('quizDebatePanel');if(!panel)return panel;
  panel.classList.add('oneAi');
  let fin=document.getElementById('quizDebateFinal');
  if(fin){let card=fin.closest('.quizDebateCard');if(card)card.style.display='none';else fin.style.display='none'}
  if(!document.getElementById('quizScriptBox')){
    let box=document.createElement('div');
    box.id='quizScriptBox';box.className='quizScriptBox';
    box.innerHTML='<b>Kịch bản lớp học (draft máy — không ghi Sheet)</b><p class="note">Kịch bản kích thích: học sinh tranh luận, nêu công thức bằng lời, bám số liệu đề. Tạo kịch bản, đọc thử hoặc tải TXT. Không lưu Sheet.</p><div class="quizLgGenRow"><button type="button" class="btn2 btnSmall" onclick="openQuizClassRoom()">🎓 Mở lớp học</button><button type="button" class="btn2 btnSmall" onclick="makeQuizClassScript()">Tạo kịch bản</button><button type="button" class="btn2 btnSmall" onclick="readQuizClassScript()">Đọc thử</button><button type="button" class="btn2 btnSmall" onclick="stopQuizQuestionSpeech()">Dừng</button><button type="button" class="btn2 btnSmall" onclick="downloadQuizClassScript()">Tải TXT</button></div><label class="muted" style="font-size:13px">Nguồn </label><select id="quizScriptSource"><option value="final">Phản biện 1 bước</option><option value="source">Lời giải nguồn</option></select> <select id="quizScriptProvider"><option value="gemini">Gemini viết</option><option value="local">Mẫu local, không API</option></select><textarea id="quizScriptText" placeholder="Kịch bản An / Bình / Chi / Dũng / Thầy Minh…"></textarea><div id="quizScriptStatus" class="muted" style="margin-top:6px;font-size:13px"></div>';
    let chat=document.getElementById('quizDebateChat');
    if(chat)panel.insertBefore(box,chat);else panel.appendChild(box);
  }
  return panel;
}
function ensureQuizDebatePanel(){let panel=document.getElementById('quizDebatePanel');if(panel){if(!document.getElementById('quizDebateChat')){let chat=document.createElement('div');chat.id='quizDebateChat';chat.className='quizDebateChat';chat.innerHTML=quizDebateChatInnerHtml();panel.appendChild(chat)}else if(!document.getElementById('btnDebateListen')){let row=panel.querySelector('.quizDebateChatRow');if(row){let b=document.createElement('button');b.type='button';b.className='btn2 btnSmall';b.id='btnDebateListen';b.title='Nói ý kiến — AI nghe rồi phản biện';b.setAttribute('onclick','toggleDebateListen()');b.textContent='🎤 Nói';row.insertBefore(b,row.firstChild)}let hint=panel.querySelector('.quizDebateChatHint');if(hint)hint.innerHTML='Bấm <b>🎤 Nói</b> để trợ lý nghe ý kiến em, rồi phán <b>đúng / sai</b>, nêu công thức $...$ và nhận xét bám sát đề. Cũng có thể gõ.'}ensureQuizDebateKeyBox();ensureQuizDebateStudioBox();return panel}let host=document.getElementById('adminLoiGiaiPanel')||document.getElementById('solution');if(!host||!host.parentNode)return null;panel=document.createElement('div');panel.id='quizDebatePanel';panel.className='quizDebatePanel hide';panel.innerHTML='<div class="quizDebateHead"><span>⚖ Trợ lý AI của Thầy Minh Vật Lý · nghe ý kiến · phán đúng/sai kèm dẫn chứng</span><span id="quizDebateStatus" class="muted"></span></div>'+quizDebateKeyBoxHtml()+'<div class="quizDebateGrid"><div class="quizDebateCard gemini"><h4>⚡ Phản biện (1 bước)</h4><div id="quizDebateGemini" class="quizDebateBody muted">Chưa phản biện.</div></div></div><div class="quizLgGenRow"><button type="button" class="btn2 btnSmall" id="btnReadDebate" onclick="toggleReadDebate()">🔊 Đọc phản biện</button><button type="button" class="btn2 btnSmall" onclick="showQuizDebateKeyBox()">🔑 Key Gemini</button><button type="button" class="btnRed btnSmall hide" id="btnCancelDebate" onclick="cancelQuizDebate()">⏹ Hủy</button></div><div id="quizDebateChat" class="quizDebateChat">'+quizDebateChatInnerHtml()+'</div>';host.parentNode.insertBefore(panel,host.nextSibling);ensureQuizDebateStudioBox();return panel}
function dedupeDebateMath(s){s=String(s||'');s=s.replace(/\$([^$]{1,160})\$\s*\$\1\$/g,function(_,a){return '$'+a+'$'});s=s.replace(/\$([^$]{1,160})\$\1/g,function(_,a){return '$'+a+'$'});return s}
function wrapBareTexCommandsInProse(s){return applyFmtOutsideMath(String(s||''),function(plain){return plain.replace(/\\([A-Za-z]+)(?:\s*(?:\[[^\]]*\]|\{[^{}]*\})){0,6}(?:\s*[_\^](?:\{[^{}]*\}|[^\s{])){0,4}/g,function(m,cmd){if(/^(begin|end|item|textbf|textit|emph|underline|newline|qquad|quad|enspace|hspace|vspace|color|textcolor|includegraphics)$/i.test(cmd))return m;return '$'+m+'$'})})}
function prepareDebateLatex(s){s=dedupeDebateMath(String(s||''));s=s.replace(/\\\[([\s\S]*?)\\\]/g,function(_,x){return '$'+String(x).replace(/\s+/g,' ').trim()+'$'});s=s.replace(/\\\(([\s\S]*?)\\\)/g,function(_,x){return '$'+String(x).replace(/\s+/g,' ').trim()+'$'});s=s.replace(/\$\$([\s\S]*?)\$\$/g,function(_,x){return '$'+String(x).replace(/\s+/g,' ').trim()+'$'});s=s.replace(/\$([^$]+)\$/g,function(_,x){return '$'+String(x).replace(/\s+/g,' ').trim()+'$'});return wrapBareTexCommandsInProse(s)}
function quizDebateCardHtml(text,err){text=prepareDebateLatex(String(text||'').trim());err=String(err||'').trim();if(text)return (typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(text):(typeof formatHintDisplay==='function'?formatHintDisplay(text):String(text).replace(/\n/g,'<br>')));if(err)return '<span class="muted">'+esc(err)+'</span>';return '<span class="muted">Chưa có phản hồi.</span>'}
function syncQuizDebatePanel(){let panel=ensureQuizDebatePanel();if(!panel)return;ensureQuizDebateKeyBox();let allow=canUseQuizDebate();let d=QUIZ_DEBATE_BY_Q[CUR];let busy=QUIZ_DEBATE_LOADING===CUR;let keyBox=document.getElementById('quizDebateKeyBox');let keyOpen=!!(keyBox&&!keyBox.classList.contains('hide'));let show=allow&&(busy||!!d||keyOpen);panel.classList.toggle('hide',!show);panel.classList.add('oneAi');let showC=false;let c=document.getElementById('quizDebateClaude');let g=document.getElementById('quizDebateGemini');let st=document.getElementById('quizDebateStatus');let cancel=document.getElementById('btnCancelDebate');if(cancel)cancel.classList.toggle('hide',!busy);if(busy){if(st)st.textContent='Đang phản biện 1 bước…';if(c)c.innerHTML='';if(g)g.innerHTML='<span class="muted">Đang phản biện lời giải…</span>';let ch=document.getElementById('quizDebateChat');if(ch)ch.classList.add('hide');syncQuizDebateBtn();return}if(d){if(st)st.textContent=(d.final||d.gemini||d.claude)?'Đã phản biện 1 bước — hỏi tiếp hoặc tạo kịch bản (không lưu Sheet)':'Bấm Phản biện (1 bước)';if(c)c.innerHTML='';if(g){g.classList.remove('muted');g.innerHTML=quizDebateCardHtml(d.final||d.gemini||d.claude,d.gemini_error||d.claude_error)}let sta=document.getElementById('quizScriptStatus');if(sta&&!String((document.getElementById('quizScriptText')||{}).value||'').trim())sta.textContent='Draft máy. Bấm Tạo kịch bản để Gemini viết thoại kích thích (nêu công thức, bám đề).';if(d.script){let taS=document.getElementById('quizScriptText');if(taS&&!taS.value)taS.value=d.script}else{let taS=document.getElementById('quizScriptText');if(taS&&!String(taS.value||'').trim()){let seed=localQuizClassScript();taS.value=seed;d.script=seed;QUIZ_DEBATE_BY_Q[CUR]=d}}try{requestAnimationFrame(function(){typesetDebateMath();setTimeout(function(){typesetDebateMath()},160)})}catch(e){}}try{renderQuizDebateChat()}catch(e3){}if(QUIZ_CR_WANT)try{renderQuizClassRoom()}catch(e4){}syncQuizDebateBtn()}
function debateSpeechHasBrand(s){let t=normText(String(s||'')).replace(/\s+/g,' ');return t.indexOf('thay minh')>=0}
function debateSpeechHasAsk(s){let t=normText(String(s||'')).replace(/\s+/g,' ');return t.indexOf('thac mac')>=0}
function wrapQuizDebateSpeech(body){let t=quizSpeechPlain(body||'');if(!t)return'';if(!debateSpeechHasBrand(t.slice(0,180)))t='Xin chào em. Mình là trợ lý AI của Thầy Minh Vật Lý. '+t;if(!debateSpeechHasAsk(t.slice(-160)))t=t+' Em còn thắc mắc gì không? Nếu có, hãy gõ câu hỏi ở ô bên dưới để mình trao đổi tiếp.';return t}
function stripDebateSpeechIntro(t){t=String(t||'').trim();t=t.replace(/^Xin chào em\.?\s*/i,'');t=t.replace(/^Mình là trợ lý AI của Thầy Minh Vật Lý\.?\s*/i,'');return t.trim()}
function buildQuizReadDebateText(){let d=QUIZ_DEBATE_BY_Q[CUR]||{};let body=d.final||d.gemini||d.claude||'';let debate=wrapQuizDebateSpeech(body);if(!debate)return'';let rest=stripDebateSpeechIntro(debate);let de='';try{de=buildQuizReadAloudText()}catch(e){}let parts=['Xin chào em. Mình là trợ lý AI của Thầy Minh Vật Lý.'];if(de){parts.push('Mình đọc lại đề.');parts.push(de);parts.push('Bây giờ mình phản biện.')}if(rest)parts.push(rest);return parts.join(' ')}
function toggleReadDebate(){if(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='debate'){stopQuizQuestionSpeech();return}startQuizViSpeech(buildQuizReadDebateText(),'debate','Chưa có phản biện để đọc. Bấm «Phản biện» trước.')}
let QUIZ_DEBATE_CHAT_LOADING=-1;
function renderQuizDebateChat(){let wrap=document.getElementById('quizDebateChat');let log=document.getElementById('quizDebateChatLog');let d=QUIZ_DEBATE_BY_Q[CUR];let busy=QUIZ_DEBATE_LOADING===CUR;if(wrap)wrap.classList.toggle('hide',busy||!d);if(!log)return;let chat=(d&&d.chat)||[];if(!chat.length){log.innerHTML='';return}log.innerHTML=chat.map(function(m){let who=m.role==='user'?'Em':'Trợ lý Thầy Minh';let cls=m.role==='user'?'user':'ai';let html=typeof renderQuizFieldHtml==='function'?renderQuizFieldHtml(typeof prepareDebateLatex==='function'?prepareDebateLatex(m.text||''):(m.text||'')):(String(m.text||'').replace(/\n/g,'<br>'));return '<div class="quizDebateChatMsg '+cls+'"><div class="who">'+esc(who)+'</div>'+html+'</div>'}).join('');try{setTimeout(function(){typesetNow([log])},80)}catch(e){}try{log.scrollTop=log.scrollHeight}catch(e2){}}
async function sendQuizDebateFollowup(fromSpeech){if(QUIZ_DEBATE_CHAT_LOADING===CUR||QUIZ_DEBATE_LOADING===CUR)return;if(DEBATE_SR_ON){DEBATE_SR_ON=false;try{if(DEBATE_SR)DEBATE_SR.stop()}catch(e){}DEBATE_SR=null;debateListenBtnSet(false)}if(!canUseQuizDebate()){alert('Hãy làm và chấm câu này trước.');return}if(!SID||!QUESTIONS.length)return;if(needQuizDebateGeminiKey('followup'))return;let ta=debateAskEl();let msg=String((ta&&ta.value)||DEBATE_SR_FINAL||'').trim();if(!msg){if(fromSpeech)alert('Chưa nghe rõ. Bấm 🎤 Nói rồi nói lại gần mic.');else if(ta)ta.focus();return}let qIdx=CUR;let d=QUIZ_DEBATE_BY_Q[qIdx];if(!d){d={claude:'',gemini:'',chat:[],lg:'',fmt:'abcd'};QUIZ_DEBATE_BY_Q[qIdx]=d;try{ensureQuizDebatePanel();syncQuizDebatePanel()}catch(e){}}d.chat=d.chat||[];d.chat.push({role:'user',text:(fromSpeech?'🎤 ':'')+msg,spoken:!!fromSpeech});if(ta)ta.value='';DEBATE_SR_FINAL='';QUIZ_DEBATE_CHAT_LOADING=qIdx;let btn=document.getElementById('btnDebateAsk');let btn2=document.getElementById('btnCrAsk');if(btn){btn.disabled=true;btn.textContent='⏳ …'}if(btn2){btn2.disabled=true;btn2.textContent='⏳ …'}renderQuizDebateChat();if(QUIZ_CR_WANT)renderQuizClassRoom();try{let lg='';try{lg=currentQuizLoiGiaiText()||''}catch(e){lg=String((currentQuestion()||{}).LoiGiai||'')}let body=quizDebateRequestBody({sid:SID,index:qIdx,answer:ANSWERS[qIdx],loigiai:lg,message:msg,spoken:fromSpeech?1:0,debate_text:d.final||d.gemini||d.claude||'',history:(d.chat||[]).slice(-8)});let j=await api('/api/quiz/debate-followup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),timeoutMs:28000,skipLoginRedirect:true},0);if(CUR!==qIdx)return;let text=String((j&&j.text)||'').trim();if(!text)throw new Error('Trợ lý chưa trả lời.');d.chat.push({role:'ai',text:text});renderQuizDebateChat();if(QUIZ_CR_WANT)renderQuizClassRoom();try{startQuizViSpeech(quizSpeechPlain(text)+(debateSpeechHasAsk(text)?'':' Em còn thắc mắc gì không? Có thể nói tiếp vào mic.'),'debate')}catch(e2){}}catch(e){if(CUR===qIdx&&d&&d.chat&&d.chat.length&&d.chat[d.chat.length-1].role==='user')d.chat.pop();renderQuizDebateChat();if(QUIZ_CR_WANT)renderQuizClassRoom();alert('Không trao đổi được: '+(e.message||e))}finally{if(QUIZ_DEBATE_CHAT_LOADING===qIdx)QUIZ_DEBATE_CHAT_LOADING=-1;if(btn){btn.disabled=false;btn.textContent='Gửi'}if(btn2){btn2.disabled=false;btn2.textContent='Gửi'}}}
async function toggleQuizDebate(){if(QUIZ_DEBATE_LOADING===CUR){cancelQuizDebate();return}if(!canUseQuizDebate()){if(EXAM_MODE&&!SUBMITTED)alert('Chế độ kiểm tra: nộp bài xong mới phản biện.');else if(!(typeof canShowSolutionNow==='function'&&canShowSolutionNow())&&!isAdminViewer())alert('Hãy làm và chấm câu này trước, rồi mới phản biện lời giải.');else alert('Phản biện lời giải dành VIP / SVIP / ADMIN.');return}if(!SID||!QUESTIONS.length)return;let lg='';try{lg=currentQuizLoiGiaiText()||''}catch(e){lg=String((currentQuestion()||{}).LoiGiai||'')}if(!String(lg||'').trim()){alert('Chưa có lời giải để phản biện.\nMở lời giải hoặc bấm «Viết lại bằng AI» trước.');return}if(needQuizDebateGeminiKey('debate'))return;let qIdx=CUR;let cached=QUIZ_DEBATE_BY_Q[qIdx];if(cached&&(cached.claude||cached.gemini)&&cached.lg===String(lg).slice(0,80)&&cached.fmt==='hook'){VIP_Q_SHOW_EXP[CUR]=true;let sol=document.getElementById('solution');if(sol)sol.classList.remove('hide');syncQuizDebatePanel();openQuizClassRoom();try{makeQuizClassScript({auto:true})}catch(e){}return}saveCurrent();VIP_Q_SHOW_EXP[CUR]=true;let sol=document.getElementById('solution');if(sol)sol.classList.remove('hide');QUIZ_DEBATE_ABORT_CTRL=new AbortController();QUIZ_DEBATE_LOADING=qIdx;syncQuizDebatePanel();openQuizClassRoom();try{let body=quizDebateRequestBody({sid:SID,index:qIdx,answer:ANSWERS[qIdx],loigiai:lg});if(isAdminViewer()){body.admin_ai_provider='ANTHROPIC';body.admin_ai_allow_gpt_fallback=true}let j=isAdminViewer()&&typeof adminAiFetch==='function'?await adminAiFetch('/api/quiz/debate-loigiai',body,{signal:QUIZ_DEBATE_ABORT_CTRL.signal,timeoutMs:28000,admin_ai_provider:'ANTHROPIC'}):await api('/api/quiz/debate-loigiai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:QUIZ_DEBATE_ABORT_CTRL.signal,timeoutMs:28000,skipLoginRedirect:true},0);if(QUIZ_DEBATE_LOADING!==qIdx)return;let prevD=QUIZ_DEBATE_BY_Q[qIdx]||{};QUIZ_DEBATE_BY_Q[qIdx]={claude:j.claude||'',gemini:j.gemini||'',final:j.final||j.gemini||j.claude||'',claude_error:j.claude_error||'',gemini_error:j.gemini_error||'',lg:String(lg).slice(0,80),fmt:'hook',chat:prevD.chat||[],script:prevD.script||'',scriptAi:!!prevD.scriptAi,heard:!!prevD.heard};if(CUR!==qIdx)return;syncQuizDebatePanel();openQuizClassRoom();try{makeQuizClassScript({auto:true})}catch(eS){}let box=document.getElementById('quizDebatePanel');if(box)box.scrollIntoView({behavior:'smooth',block:'nearest'})}catch(e){if(QUIZ_DEBATE_LOADING!==qIdx)return;let msg=String(e&&e.message||e||'');if(/abort|hủy|quá lâu/i.test(msg))return;alert('Không phản biện được: '+msg)}finally{if(QUIZ_DEBATE_LOADING===qIdx){QUIZ_DEBATE_LOADING=-1;QUIZ_DEBATE_ABORT_CTRL=null;syncQuizDebatePanel();if(QUIZ_CR_WANT)renderQuizClassRoom()}}}
function cancelQuizAiTalk(){let ctrl=QUIZ_TALK_ABORT_CTRL;QUIZ_TALK_LOADING=-1;QUIZ_TALK_ABORT_CTRL=null;if(ctrl){try{ctrl.abort()}catch(e){}}syncQuizAiTalkBtn()}
async function toggleQuizAiTalk(){if(QUIZ_TTS_ON&&QUIZ_TTS_KIND==='talk'){stopQuizQuestionSpeech();return}if(QUIZ_TALK_LOADING===CUR){cancelQuizAiTalk();return}if(!canUseQuizAiTalk()){if(EXAM_MODE&&!SUBMITTED)alert('Chế độ kiểm tra: nộp bài xong mới dùng AI thảo luận.');else alert('AI thảo luận dành VIP / SVIP / ADMIN.');return}if(!SID||!QUESTIONS.length)return;if(isAdminViewer()&&typeof adminEnsureAiReady==='function'&&!adminEnsureAiReady())return;let qIdx=CUR;let spoil=quizAiTalkSpoil();let prov=isAdminViewer()&&typeof adminChosenAiProvider==='function'?adminChosenAiProvider():'GEMINI';let cached=QUIZ_TALK_BY_Q[qIdx];if(cached&&cached.text&&cached.spoil===spoil&&String(cached.provider||'')===String(prov||'')){startQuizViSpeech(quizSpeechPlain(cached.text),'talk','AI chưa soạn đoạn thảo luận.');return}saveCurrent();QUIZ_TALK_ABORT_CTRL=new AbortController();QUIZ_TALK_LOADING=qIdx;syncQuizAiTalkBtn();try{let body={sid:SID,index:qIdx,answer:ANSWERS[qIdx],spoil:spoil,...quizRestorePayload()};quizAttachAnthropicKey(body);if(isAdminViewer()){body.admin_ai_provider=prov;body.admin_ai_allow_gpt_fallback=true}let j=isAdminViewer()&&typeof adminAiFetch==='function'?await adminAiFetch('/api/quiz/speak-talk',body,{signal:QUIZ_TALK_ABORT_CTRL.signal,timeoutMs:28000}):await api('/api/quiz/speak-talk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:QUIZ_TALK_ABORT_CTRL.signal,timeoutMs:28000},0);if(QUIZ_TALK_LOADING!==qIdx)return;let text=String(j.text||'').trim();if(!text)throw new Error('AI chưa viết đoạn thảo luận.');QUIZ_TALK_BY_Q[qIdx]={text:text,spoil:spoil,provider:j.provider||prov||''};if(CUR!==qIdx)return;startQuizViSpeech(quizSpeechPlain(text),'talk','AI chưa soạn đoạn thảo luận.')}catch(e){if(QUIZ_TALK_LOADING!==qIdx)return;let msg=String(e&&e.message||e||'');if(/abort|hủy|quá lâu/i.test(msg))return;alert('Không thảo luận được: '+msg)}finally{if(QUIZ_TALK_LOADING===qIdx){QUIZ_TALK_LOADING=-1;QUIZ_TALK_ABORT_CTRL=null;syncQuizAiTalkBtn()}}}

function canGenerateQuizLoiGiai(){if(EXAM_MODE&&!SUBMITTED)return false;if(!USER||!(USER.can_ai_hint!==false))return false;return !!(isAdminViewer()||canViewSolutionLive())}
function canAdminEditLoiGiaiInline(){return !!isAdminViewer()}
function syncAdminLoiGiaiEditBtn(){let on=canAdminEditLoiGiaiInline();for(let id of ['btnEditLoiGiai','btnFsEditLoiGiai','btnReadLoiGiai','btnFsReadLoiGiai']){let b=document.getElementById(id);if(!b)continue;b.classList.toggle('hide',!on)}}
function syncAdminLoiGiaiPanel(){let panel=document.getElementById('adminLoiGiaiPanel');let sol=document.getElementById('solution');let adm=canAdminEditLoiGiaiInline();if(!panel&&adm&&sol&&sol.parentNode){panel=document.createElement('div');panel.id='adminLoiGiaiPanel';panel.className='adminLoiGiaiEdit';panel.innerHTML='<div class="adminLoiGiaiEditHead"><span>✏️ Chỉnh sửa lời giải (cột R) — soát xong bấm Lưu</span><span id="adminLgSaveStatus" class="adminLgSaveStatus">Sheet</span></div><textarea id="adminLoiGiaiTa" class="adminLoiGiaiTa" rows="8" spellcheck="false" placeholder="Sửa lời giải tại đây (LaTeX $...$). Có lời giải vẫn sửa được." oninput="onAdminLoiGiaiDraftInput(this)"></textarea><div class="quizLgGenRow"><button type="button" class="btnGreen btnSmall" id="btnSaveAdminLoiGiai" onclick="saveAdminLoiGiaiInline()">💾 Lưu lời giải</button><button type="button" class="btn2 btnSmall" onclick="previewAdminLoiGiaiInline()">👁 Xem trước</button><button type="button" class="btn2 btnSmall" id="btnPanelReadLoiGiai" onclick="toggleReadLoiGiai()">🔊 Đọc lời giải</button><button type="button" class="btn2 btnSmall" id="btnPanelDebate" onclick="toggleQuizDebate()">⚖ Phản biện</button><button type="button" class="btn2 btnSmall" id="btnGenLoiGiai" onclick="generateQuizLoiGiai()">✨ Viết lại bằng AI</button><button type="button" class="btnRed btnSmall hide" id="btnCancelLoiGiai" onclick="cancelGenerateQuizLoiGiai()">⏹ Hủy AI</button></div>';sol.parentNode.insertBefore(panel,sol.nextSibling)}if(!panel)return;let show=adm&&sol&&!sol.classList.contains('hide');panel.classList.toggle('hide',!show);if(!show)return;let ta=document.getElementById('adminLoiGiaiTa');if(ta&&AI_LG_LOADING!==CUR){let sameQ=String(ta.getAttribute('data-lg-qidx')||'')===String(CUR);if(!sameQ||document.activeElement!==ta){ta.value=adminLoiGiaiDraftText();ta.setAttribute('data-lg-qidx',String(CUR))}if(!ta._lgBound){ta._lgBound=1;ta.addEventListener('input',function(){onAdminLoiGiaiDraftInput(ta)})}}let st=document.getElementById('adminLgSaveStatus');if(st&&ADMIN_LG_DRAFT_BY_Q[CUR]==null&&AI_LG_LOADING!==CUR){if(ADMIN_LG_SAVED_AT&&Date.now()-ADMIN_LG_SAVED_AT<6000){st.textContent='Lời giải đã được lưu';st.className='adminLgSaveStatus'}else{st.textContent=String((currentQuestion()||{}).LoiGiai||'').trim()?'Đã khớp Sheet':'Chưa có trên Sheet';st.className='adminLgSaveStatus'}}syncAdminLoiGiaiGenBtn()}
function syncAdminLoiGiaiGenBtn(){let busy=AI_LG_LOADING===CUR;let btn=document.getElementById('btnGenLoiGiai');if(btn){btn.disabled=busy;btn.textContent=busy?'⏳ Đang gọi AI…':'✨ Viết lại bằng AI'}let cancel=document.getElementById('btnCancelLoiGiai');if(cancel)cancel.classList.toggle('hide',!busy)}
function cancelGenerateQuizLoiGiai(){let ctrl=AI_LG_ABORT_CTRL;AI_LG_LOADING=-1;AI_LG_ABORT_CTRL=null;if(ctrl){try{ctrl.abort()}catch(e){}}syncAdminLoiGiaiGenBtn();let st=document.getElementById('adminLgSaveStatus');if(st){st.textContent='Đã hủy AI — sửa tay rồi Lưu';st.className='adminLgSaveStatus dirty'}}
function startAdminLoiGiaiEdit(){if(!canAdminEditLoiGiaiInline()){alert('Chỉ ADMIN sửa lời giải tại đây.');return}if(AI_LG_LOADING===CUR)cancelGenerateQuizLoiGiai();VIP_Q_SHOW_EXP[CUR]=true;VIP_Q_SHOW_ANS[CUR]=true;renderQuestion();setTimeout(function(){let box=document.getElementById('adminLoiGiaiPanel')||document.getElementById('solution');if(box)box.scrollIntoView({behavior:'smooth',block:'center'});let ta=document.getElementById('adminLoiGiaiTa');if(ta){try{ta.focus()}catch(e){}}},80)}
function adminLoiGiaiDraftText(q){q=q||currentQuestion()||{};if(ADMIN_LG_DRAFT_BY_Q[CUR]!=null)return String(ADMIN_LG_DRAFT_BY_Q[CUR]);let sheet=String(q.LoiGiai||'').trim();if(sheet)return sheet;return String((AI_LG_BY_Q[CUR]||{}).text||'')}
function onAdminLoiGiaiDraftInput(el){ADMIN_LG_DRAFT_BY_Q[CUR]=String(el&&el.value||'');let st=document.getElementById('adminLgSaveStatus');if(st){st.textContent='Chưa lưu';st.className='adminLgSaveStatus dirty'}}
function previewAdminLoiGiaiInline(){let ta=document.getElementById('adminLoiGiaiTa');if(ta)ADMIN_LG_DRAFT_BY_Q[CUR]=ta.value;let q=currentQuestion()||{};let box=document.getElementById('adminLoiGiaiPreview');if(!box){renderQuestion();return}let text=String(ADMIN_LG_DRAFT_BY_Q[CUR]!=null?ADMIN_LG_DRAFT_BY_Q[CUR]:(q.LoiGiai||'')).trim();box.innerHTML=text?formatLoigiaiByDang(text,q,q.Dang):'<span class="muted">Chưa có lời giải.</span>';typesetQuizMathWithRetry(2,40)}
function buildQuizLoiGiaiHtml(q,r){q=q||currentQuestion()||{};r=r||RESULTS[CUR]||CHECKED[CUR]||{};let sheetLg=String(q.LoiGiai||(r&&(r.LoiGiai||r.loigiai))||'').trim();let aiLg=String((AI_LG_BY_Q[CUR]||{}).text||'').trim();let draftStored=ADMIN_LG_DRAFT_BY_Q[CUR]!=null?String(ADMIN_LG_DRAFT_BY_Q[CUR]||''):'';let lg=String(draftStored||sheetLg||aiLg||'').trim();let busy=AI_LG_LOADING===CUR;if(!lg&&LOCKED_Q[CUR]&&!CHECKED[CUR]&&!RESULTS[CUR])return '<b>Lời giải:</b><br><span class="muted">Đang lấy lời giải của câu này…</span>';let lgHtml=lg?formatLoigiaiByDang(lg,q,q.Dang):'<span class="muted">Chưa có lời giải trên Sheet.</span>';if(!canAdminEditLoiGiaiInline()){let genBtn='';if(canGenerateQuizLoiGiai()&&!sheetLg)genBtn=`<div class="quizLgGenRow"><button type="button" class="btn2 btnSmall" id="btnGenLoiGiai" onclick="generateQuizLoiGiai()" ${busy?'disabled':''}>${busy?'⏳ Đang viết lời giải…':'✨ Tự thêm lời giải'}</button></div>`;return `<b>Lời giải:</b><br>${lgHtml}${genBtn}`}return `<div class="adminLgHeadRow"><b>Lời giải:</b></div><div id="adminLoiGiaiPreview" class="adminLoiGiaiPreview">${lgHtml}</div>`}
function currentQuizLoiGiaiText(q){q=q||currentQuestion()||{};let ta=document.getElementById('adminLoiGiaiTa');let taOk=ta&&String(ta.getAttribute('data-lg-qidx')||'')===String(CUR);let fromTa=taOk?String(ta.value||'').trim():'';if(fromTa)return fromTa;if(ADMIN_LG_DRAFT_BY_Q[CUR]!=null){let d=String(ADMIN_LG_DRAFT_BY_Q[CUR]||'').trim();if(d)return d}let sheet=String(q.LoiGiai||'').trim();if(sheet)return sheet;let r=RESULTS[CUR]||CHECKED[CUR]||{};let fromR=String((r&&(r.LoiGiai||r.loigiai))||'').trim();if(fromR)return fromR;let h=HINT_BY_Q[CUR]||{};let fromH=String(h.sheet_loigiai||h.suggested_loigiai||'').trim();if(fromH)return fromH;let ai=AI_LG_BY_Q[CUR]||{};return String(ai.text||'').trim()}
async function generateQuizLoiGiai(){if(AI_LG_LOADING===CUR){cancelGenerateQuizLoiGiai();return}if(!canGenerateQuizLoiGiai()){alert('Tự thêm lời giải dành VIP / SVIP / ADMIN.');return}if(!canShowSolutionNow()&&!isAdminViewer()){alert('Hãy làm và chấm câu này trước.');return}if(!SID||!QUESTIONS.length)return;if(isAdminViewer()&&typeof adminEnsureAiReady==='function'&&!adminEnsureAiReady())return;let qIdx=CUR;let q=QUESTIONS[qIdx]||{};if(canAdminEditLoiGiaiInline()&&String(q.LoiGiai||'').trim()&&!confirm('AI viết lại lời giải vào ô bên dưới — chưa lưu Sheet.\n\nKhông cần đợi AI: sửa tay trong ô rồi bấm «Lưu lời giải».\n\nVẫn gọi AI?'))return;saveCurrent();AI_LG_ABORT_CTRL=new AbortController();AI_LG_LOADING=qIdx;syncAdminLoiGiaiGenBtn();try{let body={sid:SID,index:qIdx,answer:ANSWERS[qIdx],save:false,...quizRestorePayload()};quizAttachAnthropicKey(body);if(isAdminViewer()){body.admin_ai_provider=typeof adminChosenAiProvider==='function'?adminChosenAiProvider():'GEMINI';body.admin_ai_allow_gpt_fallback=true}let j=isAdminViewer()&&typeof adminAiFetch==='function'?await adminAiFetch('/api/quiz/generate-loigiai',body,{signal:AI_LG_ABORT_CTRL.signal,timeoutMs:28000}):await api('/api/quiz/generate-loigiai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AI_LG_ABORT_CTRL.signal,timeoutMs:28000},0);if(AI_LG_LOADING!==qIdx)return;let text=String(j.text||'').trim();if(!text)throw new Error('AI chưa trả lời giải.');AI_LG_BY_Q[qIdx]={text:text,provider:j.provider||''};if(canAdminEditLoiGiaiInline()){ADMIN_LG_DRAFT_BY_Q[qIdx]=text;let ta=document.getElementById('adminLoiGiaiTa');if(ta)ta.value=text;let st=document.getElementById('adminLgSaveStatus');if(st){st.textContent=(j.provider==='ANTHROPIC'?'Claude':'AI')+' đã viết — chưa lưu Sheet';st.className='adminLgSaveStatus dirty'}if(typeof previewAdminLoiGiaiInline==='function')previewAdminLoiGiaiInline();VIP_Q_SHOW_EXP[CUR]=true}else if(CUR===qIdx){VIP_Q_SHOW_EXP[CUR]=true;renderQuestion()}}catch(e){if(AI_LG_LOADING!==qIdx)return;let msg=String(e&&e.message||e||'');if(/abort|hủy|quá lâu/i.test(msg)){let st=document.getElementById('adminLgSaveStatus');if(st){st.textContent='AI chậm — sửa tay rồi Lưu';st.className='adminLgSaveStatus dirty'}return}alert('Không viết được lời giải: '+msg+'\n\nSửa tay trong ô rồi bấm «Lưu lời giải».')}finally{if(AI_LG_LOADING===qIdx){AI_LG_LOADING=-1;AI_LG_ABORT_CTRL=null;syncAdminLoiGiaiGenBtn()}}}
async function saveAdminLoiGiaiInline(){if(!canAdminEditLoiGiaiInline()){alert('Chỉ ADMIN sửa lời giải tại đây.');return}if(AI_LG_LOADING===CUR)cancelGenerateQuizLoiGiai();if(ADMIN_LG_SAVE_BUSY)return;let q=QUESTIONS[CUR];if(!q)return;let text=currentQuizLoiGiaiText(q);if(!q._row&&!String(q.ID||'').trim()){alert('Không xác định dòng Sheet.');return}let patch={LoiGiai:text};try{patch=autoSyncDsLoigiaiAbcd(patch,q);text=String(patch.LoiGiai!=null?patch.LoiGiai:text)}catch(e){}let miss=adminLoigiaiMissingLetters(text,q);if(miss.length&&!confirm('Lời giải thiếu ý '+miss.join(', ')+'.\n\nVẫn lưu Sheet?'))return;ADMIN_LG_SAVE_BUSY=true;let btn=document.getElementById('btnSaveAdminLoiGiai');if(btn){btn.disabled=true;btn.textContent='⏳ Đang lưu…'}try{let saveUpdates={LoiGiai:text};if(patch.DapAn!=null&&String(patch.DapAn).trim())saveUpdates.DapAn=patch.DapAn;let j=await api('/api/question/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row||0,id:q.ID||'',updates:saveUpdates,fast:1}),timeoutMs:28000},1);q.LoiGiai=text;if(saveUpdates.DapAn)q.DapAn=saveUpdates.DapAn;if(j.row)q._row=parseInt(j.row,10)||q._row;delete ADMIN_LG_DRAFT_BY_Q[CUR];AI_LG_BY_Q[CUR]={text:text,saved:true};if(HINT_BY_Q[CUR])HINT_BY_Q[CUR].sheet_loigiai=text;ADMIN_LG_SAVED_AT=Date.now();let st=document.getElementById('adminLgSaveStatus');if(st){st.textContent='Lời giải đã được lưu';st.className='adminLgSaveStatus'}let rb=document.getElementById('resultBox');if(rb){rb.textContent='Lời giải đã được lưu'+(j.row?(' · dòng '+j.row):'');rb.style.color='#166534'}showAdminLoiGiaiSavedToast('Lời giải đã được lưu');try{previewAdminLoiGiaiInline()}catch(e){}syncAdminLoiGiaiPanel()}catch(e){alert('Không lưu được: '+(e.message||e))}finally{ADMIN_LG_SAVE_BUSY=false;let b=document.getElementById('btnSaveAdminLoiGiai');if(b){b.disabled=false;b.textContent='💾 Lưu lời giải'}}}
async function saveGeneratedLoiGiai(){return saveAdminLoiGiaiInline()}
let INFOGRAPHIC_STYLE='poster';
let INFOGRAPHIC_GEN_BUSY=false;
function currentInfographicStyle(){let el=document.querySelector('input[name="infographicStyle"]:checked');let v=String((el&&el.value)||INFOGRAPHIC_STYLE||'poster').toLowerCase();INFOGRAPHIC_STYLE=(v==='notebook'||v==='vo')?'notebook':'poster';return INFOGRAPHIC_STYLE}
function syncInfographicStyleUI(){let style=currentInfographicStyle();document.querySelectorAll('#infographicStylePicker label').forEach(function(lb){let inp=lb.querySelector('input');let on=!!(inp&&inp.checked);lb.style.borderColor=on?'#1d4ed8':'var(--border)';lb.style.background=on?'#eff6ff':'var(--surface)';lb.style.color=on?'#1e3a8a':''});let desc=document.getElementById('infographicModalDesc');if(desc)desc.innerHTML=style==='notebook'?'Gemini vẽ <b>một trang vở ghi bài</b> — giấy kẻ, lề đỏ, chữ viết tay sạch, công thức chuẩn. Góc trái: tên bài + ID · Góc phải: <b>Lớp Học Thầy Minh</b> + zalo <b>0946111107</b>. VIP/SVIP: mở khóa sau khi <b>trả lời đúng</b>.':'Gemini vẽ <b>poster hiện đại đầy màu</b> — 4 card gradient (Đề → Phương án → Hình → Lời giải). Có ảnh cột T → AI đọc ảnh gốc rồi vẽ lại đẹp hơn. VIP/SVIP: mở khóa sau khi <b>trả lời đúng</b>.';let btn=document.getElementById('btnGenerateInfographic');if(btn&&!INFOGRAPHIC_GEN_BUSY)btn.textContent=style==='notebook'?'📓 Vẽ trang vở (Gemini)':'🎨 Vẽ poster (Gemini)';let img=document.getElementById('infographicGeneratedImg');if(img)img.alt=style==='notebook'?'Trang vở Gemini':'Poster Gemini'}
function onInfographicStyleChange(){syncInfographicStyleUI();let modal=document.getElementById('infographicModal');if(modal&&!modal.classList.contains('hide'))refreshInfographicPrompt(true)}
function infographicStyleApiBody(){return {sid:SID,index:CUR,answer:ANSWERS[CUR],style:currentInfographicStyle(),...quizRestorePayload()}}
async function openInfographicPrompt(){if(!canUseInfographicRole()){alert('Infographic chỉ dành VIP / SVIP / ADMIN.');return}if(!canUnlockInfographic(CUR)){alert('Phải trả lời đúng câu này mới mở khóa infographic.');return}if(!SID||!QUESTIONS.length){alert('Hãy mở một đề và chọn câu trước.');return}saveCurrent();let ta=document.getElementById('infographicPromptText');let title=document.getElementById('infographicModalTitle');let modal=document.getElementById('infographicModal');let wrap=document.getElementById('infographicImageWrap');let status=document.getElementById('infographicGenStatus');if(wrap)wrap.classList.add('hide');if(status){status.classList.add('hide');status.textContent=''}if(!ta||!modal){alert('Không tìm thấy hộp prompt.');return}ta.value='Đang tạo prompt từ Sheet (câu hiện tại)…';syncInfographicStyleUI();if(title){let q=QUESTIONS[CUR]||{};let md=String(q.MucDo||'').trim();let kind=currentInfographicStyle()==='notebook'?'📓 Trang vở':'📊 Infographic';title.textContent=kind+' · Câu '+(CUR+1)+(q.ID?' · ID '+q.ID:'')+(md?' · Mức độ '+md:'')}modal.classList.remove('hide');await refreshInfographicPrompt()}
async function refreshInfographicPrompt(quiet){let ta=document.getElementById('infographicPromptText');let title=document.getElementById('infographicModalTitle');if(!ta)return;ta.value='Đang tạo prompt từ Sheet (câu hiện tại)…';try{let j=await api('/api/infographic-prompt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(infographicStyleApiBody())});ta.value=j.prompt||'';if(!ta.value)ta.value='Không tạo được prompt.';if(title){let q=QUESTIONS[CUR]||{};let kind=(j.style==='notebook'||currentInfographicStyle()==='notebook')?'📓 Trang vở':'📊 Infographic';let parts=[kind+' · Câu '+(CUR+1)];if(q.ID)parts.push('ID '+q.ID);let md=String(j.mucdo||q.MucDo||'').trim();if(md)parts.push('Mức độ '+md);if(j.dang_title)parts.push(j.dang_title);title.textContent=parts.join(' · ')}if(!quiet&&j.warnings&&j.warnings.length)alert('⚠️ Kiểm tra Sheet:\n'+j.warnings.join('\n'))}catch(e){ta.value='';alert('Không tạo được prompt: '+(e.message||e))}}
function copyInfographicPrompt(){let ta=document.getElementById('infographicPromptText');if(!ta||!String(ta.value||'').trim()){alert('Chưa có prompt.');return}let notebook=currentInfographicStyle()==='notebook';navigator.clipboard.writeText(ta.value).then(()=>alert(notebook?'Đã chép prompt.\n\nDán Gemini — trang vở ghi bài, lề đỏ, chữ viết tay, header Lớp Học Thầy Minh.':'Đã chép prompt.\n\nDán Gemini — poster hiện đại đầy màu, 4 card gradient, không chữ Khối.')).catch(()=>{ta.focus();ta.select();try{document.execCommand('copy');alert('Đã chép (Ctrl+C).')}catch(e){alert('Chọn text trong ô rồi Ctrl+C.')}})}
async function generateInfographicImage(){if(INFOGRAPHIC_GEN_BUSY)return;if(!canUseInfographicRole()){alert('Infographic chỉ dành VIP / SVIP / ADMIN.');return}if(!canUnlockInfographic(CUR)){alert('Phải trả lời đúng câu này mới mở khóa infographic.');return}if(!SID||!QUESTIONS.length){alert('Hãy mở một đề và chọn câu trước.');return}saveCurrent();let btn=document.getElementById('btnGenerateInfographic');let status=document.getElementById('infographicGenStatus');let wrap=document.getElementById('infographicImageWrap');let img=document.getElementById('infographicGeneratedImg');let notebook=currentInfographicStyle()==='notebook';INFOGRAPHIC_GEN_BUSY=true;if(btn){btn.disabled=true;btn.textContent='⏳ Đang vẽ…'}if(status){status.classList.remove('hide');status.textContent=notebook?'Đang gọi Gemini vẽ trang vở — thường 30–60 giây…':'Đang gọi Gemini vẽ poster — thường 30–60 giây…'}try{let j=await api('/api/infographic-generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(infographicStyleApiBody())});if(img&&j.image_data_url){img.src=j.image_data_url;if(wrap)wrap.classList.remove('hide')}let doneStyle=(j.style==='notebook'||notebook)?'trang vở':'poster';if(status)status.textContent='✅ Đã vẽ '+doneStyle+(j.model?' · '+j.model:'')+(j.has_reference_image?' · có ảnh tham chiếu cột T':'')}catch(e){if(status)status.textContent='❌ '+esc(e.message||e);alert('Không vẽ được ảnh: '+(e.message||e)+'\n\nVẫn có thể «Chép prompt» và dán Gemini thủ công.')}finally{INFOGRAPHIC_GEN_BUSY=false;if(btn){btn.disabled=false;btn.textContent=currentInfographicStyle()==='notebook'?'📓 Vẽ trang vở (Gemini)':'🎨 Vẽ poster (Gemini)'}}}
let QUESTION_SAVE_BUSY=false;
async function saveQuestionModal(){if(QUESTION_SAVE_BUSY)return;if(QUESTION_MODAL_MODE==='add')return saveAddQuestion();return saveEdit()}
async function saveEdit(){if(QUESTION_SAVE_BUSY)return;let saveBtn=document.getElementById('btnSaveQuestion');try{let q=QUESTIONS[CUR];if(!q){alert('Không có câu hiện tại.');return}if(!q._row&&!String(q.ID||'').trim()){alert('Không xác định dòng Sheet. Hãy bấm Đồng bộ Sheet rồi mở lại câu.');return}let form=readQuestionFormData();let updates={};for(let f of QUESTION_EDIT_SAVE_FIELDS)updates[f]=form[f]!=null?form[f]:(q[f]||'');updates=autoSyncDsLoigiaiAbcd(updates,q);let miss=adminLoigiaiMissingLetters(updates.LoiGiai,Object.assign({},q,updates));if(miss.length&&!confirm('Lời giải thiếu ý '+miss.join(', ')+'.\n\nVẫn lưu Sheet?'))return;if(!String(updates.DapAn||'').trim()&&!confirm('Đáp án (P) đang trống.\n\nVẫn lưu Sheet?'))return;QUESTION_SAVE_BUSY=true;if(saveBtn){saveBtn.disabled=true;saveBtn.textContent='⏳ Đang lưu…'}let j=await api('/api/question/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row||0,id:q.ID||'',updates})});let savedRow=parseInt(j.row,10)||q._row;q._row=savedRow;if(j.hinhanh){updates.HinhAnh=j.hinhanh}Object.assign(q,updates);q.reviewed_sheet=questionIsReviewedForAdmin(q);q.reviewed=q.reviewed_sheet;applyResolvedDang(q);if(HINT_BY_Q[CUR]&&HINT_BY_Q[CUR].admin_review){markAdminHintSaved(CUR);HINT_BY_Q[CUR].sheet_dapan=updates.DapAn||'';HINT_BY_Q[CUR].sheet_loigiai=updates.LoiGiai||''}if(CHECKED[CUR]){delete CHECKED[CUR].LoiGiai;delete CHECKED[CUR].DapAn;if(updates.DapAn)delete CHECKED[CUR].rows}if(RESULTS[CUR]){delete RESULTS[CUR].LoiGiai;delete RESULTS[CUR].DapAn;if(updates.DapAn)delete RESULTS[CUR].rows}CUR=regroupQuestionsByDang(savedRow);closeEdit();renderQuestion();if(HINT_BY_Q[CUR]&&!document.getElementById('hintBox').classList.contains('hide'))renderHintBox(HINT_BY_Q[CUR]);alert('Đã lưu vào Google Sheet dòng '+j.row+'\nĐã cập nhật: '+(j.fields||[]).join(', ')+(j.hinhanh_warning?('\n\n⚠ '+j.hinhanh_warning):'')+(adminHintNeedsSave(CUR)?'':'\\n\\n✅ Có thể so khớp ĐA/LG với AI ở trên.'))}catch(e){alert('Không lưu được: '+(e.message||e))}finally{QUESTION_SAVE_BUSY=false;syncQuestionModalChrome();if(saveBtn)saveBtn.disabled=false}}
async function saveAddQuestion(){if(QUESTION_SAVE_BUSY)return;let data=readQuestionFormData();if(!String(data.CauHoi||'').trim()){alert('Phải nhập nội dung câu hỏi.');return}QUESTION_SAVE_BUSY=true;let saveBtn=document.getElementById('btnSaveQuestion');if(saveBtn){saveBtn.disabled=true;saveBtn.textContent='⏳ Đang thêm…'}try{let j=await api('/api/question/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data})});let nq=applyResolvedDang(j.question||{});if(!nq._row)nq._row=j.row;let insertAt=Math.min(CUR+1,QUESTIONS.length);QUESTIONS.splice(insertAt,0,nq);insertQuizMaps(insertAt);CUR=regroupQuestionsByDang(nq._row);closeEdit();renderNav();renderQuestion();refreshCatalogFromMeta();alert('Đã thêm câu mới vào Google Sheet dòng '+j.row+(j.id?('\nID: '+j.id):''))}catch(e){alert('Không thêm được: '+e.message)}finally{QUESTION_SAVE_BUSY=false;syncQuestionModalChrome();let sb=document.getElementById('btnSaveQuestion');if(sb)sb.disabled=false}}
async function deleteQuestionAtIndex(idx){if(!USER.is_admin)return;idx=parseInt(idx,10);if(!Number.isFinite(idx)||idx<0||idx>=QUESTIONS.length)return;let q=QUESTIONS[idx];if(!q||!q._row){alert('Không xác định được dòng Google Sheet của câu này.');return}let msg='Xóa vĩnh viễn câu '+(idx+1)+' khỏi Google Sheet?\n\nID: '+(q.ID||'')+'\nDòng: '+q._row+'\n\nApp tự cập nhật — không cần bấm Đồng bộ Sheet sau mỗi lần xóa.';if(!confirm(msg))return;if(!confirm('Xác nhận lần 2: chắc chắn xóa câu này?'))return;try{let j=await api('/api/question/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row:q._row,id:q.ID||''})});clearOfflineDecksContainingIds([q.ID||j.id||'']);clearOfflineDeckForMade(CURRENT_MADE);let deletedRow=parseInt(j.row,10)||0;let removedIdx=idx;QUESTIONS.splice(removedIdx,1);for(let qq of QUESTIONS){let r=parseInt(qq._row,10)||0;if(r>deletedRow)qq._row=r-1}reindexQuizMaps(removedIdx);refreshCatalogFromMeta();if(QUESTIONS.length===0){closeEdit();backHome();alert('Đã xóa câu cuối trong phiên này.\nMục lục đã tự cập nhật — không cần Đồng bộ Sheet.');return}if(CUR===removedIdx){if(CUR>=QUESTIONS.length)CUR=QUESTIONS.length-1}else if(CUR>removedIdx)CUR--;closeEdit();renderNav();renderQuestion();syncQuestionReviewToolbar();document.getElementById('resultBox').textContent='Đã xóa câu '+(removedIdx+1)+' (dòng '+deletedRow+') — còn '+QUESTIONS.length+' câu';document.getElementById('resultBox').style.color='#166534'}catch(e){alert('Không xóa được: '+e.message)}}
async function deleteQuestion(){return deleteQuestionAtIndex(CUR)}
setInterval(updateExamStrip,1000);
document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement&&FULLDE_ON){document.body.classList.add('fullde-mode')}if(!document.fullscreenElement){FS_ANS_FORCE=null;FS_EXP_FORCE=null;renderQuestion()}else if(FULLDE_ON){setTimeout(()=>{syncFulldeNavChrome();typesetQuizMathWithRetry(2,100)},120)}});


/* ===== V245: Mục lục tách MÔN → KHỐI → CHƯƠNG → BÀI ===== */
window.CATALOG_SELECTED_KHOI = window.CATALOG_SELECTED_KHOI || '';
function v245EnsureCatalogScopeCss(){
  if(document.getElementById('LDVL_CATALOG_SCOPE_V245'))return;
  let st=document.createElement('style'); st.id='LDVL_CATALOG_SCOPE_V245';
  st.textContent=`
  .catalogScopeBox{margin-top:10px;margin-bottom:10px;border:1px solid #bfdbfe;background:linear-gradient(180deg,#eff6ff,#ffffff);border-radius:14px;padding:10px;box-shadow:0 1px 5px #1d4ed811}
  html[data-theme='dark'] .catalogScopeBox{background:linear-gradient(180deg,#172554,#111827);border-color:#1d4ed8}
  .catalogScopeTitle{font-weight:900;color:#1e3a8a;margin-bottom:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  html[data-theme='dark'] .catalogScopeTitle{color:#bfdbfe}
  .catalogScopeRow{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:7px 0}
  .catalogScopeLabel{font-size:12px;font-weight:900;color:#475569;min-width:58px}
  html[data-theme='dark'] .catalogScopeLabel{color:#cbd5e1}
  .catalogChip{border:1px solid #cbd5e1;background:#fff;color:#1e3a8a;border-radius:999px;padding:6px 10px;font-weight:900;font-size:12px;cursor:pointer;min-height:30px;line-height:1.1;box-shadow:0 1px 2px #0000000b}
  .catalogChip:hover{filter:brightness(1.03);transform:translateY(-1px)}
  .catalogChip.active{background:#1d4ed8;border-color:#1d4ed8;color:#fff;box-shadow:0 0 0 3px #bfdbfe}
  .catalogChip.khoi{min-width:48px;text-align:center}
  .catalogChip.chapter{border-radius:10px;max-width:260px;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .catalogChip.lesson{border-radius:10px;max-width:280px;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .catalogAdvancedHint{font-size:12px;color:#64748b;margin-top:7px;line-height:1.35}
  html[data-theme='dark'] .catalogChip{background:#0f172a;border-color:#475569;color:#dbeafe} html[data-theme='dark'] .catalogChip.active{background:#2563eb;color:#fff;border-color:#60a5fa}
  .catalogSection{grid-column:1/-1;margin:6px 0 0;padding:9px 10px;border-radius:10px;background:#e0f2fe;border:1px solid #7dd3fc;color:#075985;font-weight:900}
  html[data-theme='dark'] .catalogSection{background:#082f49;border-color:#0369a1;color:#bae6fd}
  .catalogGroupGrid{grid-column:1/-1;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin:2px 0 8px}
  @media(max-width:760px){.catalogScopeBox{padding:8px;border-radius:12px}.catalogScopeRow{gap:5px;margin:6px 0}.catalogScopeLabel{width:100%;min-width:0}.catalogChip{font-size:11px;padding:5px 8px;min-height:28px}.catalogChip.chapter,.catalogChip.lesson{max-width:100%}.catalogAdvancedHint{font-size:11px}.catalogGroupGrid{grid-template-columns:1fr}.catalogSection{font-size:13px;padding:8px}}
  `;
  document.head.appendChild(st);
}
function v245EnsureCatalogScopeBox(){
  v245EnsureCatalogScopeCss();
  let home=document.getElementById('home'); if(!home)return null;
  if(document.getElementById('catalogScopeBox'))return document.getElementById('catalogScopeBox');
  let firstPanel=home.querySelector('.panel'); if(!firstPanel)return null;
  let box=document.createElement('div');
  box.id='catalogScopeBox'; box.className='catalogScopeBox';
  box.innerHTML=`<div class="catalogScopeTitle">🧭 Lọc nhanh theo Môn → Khối → Chương → Bài</div><div id="catalogMonTabs" class="catalogScopeRow"></div><div id="catalogKhoiTabs" class="catalogScopeRow"></div><div id="catalogChuongTabs" class="catalogScopeRow"></div><div id="catalogBaiTabs" class="catalogScopeRow"></div><div class="catalogAdvancedHint">Bên dưới vẫn giữ bộ lọc chi tiết: Lớp, Bộ đề, Mức độ, Dạng câu, Tìm nhanh.</div>`;
  let row=firstPanel.querySelector('.row');
  if(row)firstPanel.insertBefore(box,row); else firstPanel.appendChild(box);
  return box;
}
/* ===== V246: Giao diện sách trong từng tab + bộ lọc Dạng bài tập ===== */
function v246EnsureBookCss(){
  if(document.getElementById('LDVL_BOOK_TABS_V246'))return;
  let st=document.createElement('style');st.id='LDVL_BOOK_TABS_V246';
  st.textContent=`
  .catalogScopeBox{border-color:#dbeafe!important;background:linear-gradient(180deg,#f8fbff,#ffffff)!important}
  .bookFilterHint{margin-top:8px;padding:8px 10px;border-radius:10px;background:#f8fafc;border:1px dashed #cbd5e1;color:#475569;font-size:12px;line-height:1.45}
  .bookIntroV246{margin:10px 0 12px;padding:12px;border:1px solid #dbeafe;border-radius:16px;background:linear-gradient(180deg,#eff6ff,#ffffff);box-shadow:0 1px 5px #1d4ed811}
  .bookIntroTitle{font-size:15px;font-weight:950;color:#1e3a8a;margin-bottom:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .bookIntroStats{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}.bookStat{display:inline-flex;align-items:center;gap:4px;border:1px solid #bfdbfe;background:#fff;border-radius:999px;padding:4px 9px;font-size:12px;font-weight:850;color:#1e40af}
  .bookShelfV246{display:block}.bookSubjectBlock{margin:12px 0 16px}.bookSubjectTitle{padding:11px 12px;border-radius:14px;background:linear-gradient(90deg,#1d4ed8,#60a5fa);color:#fff;font-weight:950;font-size:17px;box-shadow:0 2px 8px #1d4ed833;display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap}.bookSubjectTitle small{font-size:12px;opacity:.95;font-weight:800}
  .bookGradeBlock{margin:10px 0 12px;border:1px solid #cbd5e1;border-radius:16px;background:#fff;overflow:hidden;box-shadow:0 1px 4px #0f172a0f}.bookGradeHead{padding:10px 12px;background:#f1f5f9;color:#0f172a;font-weight:950;display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap}.bookGradeHead .bookMini{font-size:12px;color:#64748b;font-weight:800}
  .bookChapterBlock{margin:10px;border:1px solid #bfdbfe;border-radius:14px;overflow:hidden;background:#f8fbff}.bookChapterHead{padding:9px 11px;background:#dbeafe;color:#1e3a8a;font-weight:950;display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;position:relative;z-index:2}.bookChapterHead .bookChapterDbtBtn{flex-shrink:0;cursor:pointer;position:relative;z-index:3}.bookChapterHead small{font-size:12px;font-weight:800;color:#475569}.bookLessonList{padding:9px;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:9px}
  .bookLessonCard{border:1px solid #e2e8f0;border-radius:14px;background:#fff;padding:10px;box-shadow:0 1px 3px #0f172a0d;display:flex;flex-direction:column;gap:7px;overflow-anchor:none}.bookLessonTitle{font-weight:950;color:#0f172a;line-height:1.3}.bookLessonSub{font-size:12px;color:#64748b;line-height:1.35}.bookLessonTags{display:flex;flex-wrap:wrap;gap:5px}.bookTag{border:1px solid #cbd5e1;background:#f8fafc;border-radius:999px;padding:3px 7px;font-size:11px;font-weight:850;color:#334155}.bookTag.nb{background:#f0fdf4;border-color:#86efac;color:#166534}.bookTag.th{background:#eff6ff;border-color:#93c5fd;color:#1d4ed8}.bookTag.vd{background:#fff7ed;border-color:#fdba74;color:#c2410c}.bookTag.vdc{background:#fef2f2;border-color:#fca5a5;color:#991b1b}.bookTag.dang-tn{background:#dbeafe;border-color:#93c5fd;color:#1d4ed8}.bookTag.dang-ds{background:#f0fdf4;border-color:#86efac;color:#166534}.bookTag.dang-tln{background:#faf5ff;border-color:#d8b4fe;color:#7e22ce}.bookTag.dang-tl{background:#fff7ed;border-color:#fdba74;color:#c2410c}.bookTag.dang-other{background:#f1f5f9;border-color:#cbd5e1;color:#475569}.bookTag.bookTagDone{background:#fef9c3;border-color:#facc15;color:#854d0e}.bookTag.bookTagComplete{background:#dcfce7;border-color:#22c55e;color:#166534}.bookLessonProg,.bookChapterProg{display:inline-flex;flex-wrap:wrap;gap:4px;margin-left:6px;vertical-align:middle}.bookLessonCard.lessonDone{border-color:#fde68a;background:#fffbeb}.bookLessonCard.lessonComplete{border-color:#86efac;background:#f0fdf4}.bookChapterBlock.isChapterComplete .bookChapterHead{background:#dcfce7;border-color:#86efac}.bookDbtBtn.isPracticeDone{border-color:#fde68a;background:#fffbeb}.bookDbtBtn.isPracticeComplete{border-color:#86efac;background:#f0fdf4}.bookDbtProg{font-size:10px;font-weight:950;margin-right:3px}.bookDbtProgDone{color:#ca8a04}.bookDbtProgComplete{color:#16a34a}.bookExamRow{display:flex;flex-wrap:wrap;gap:5px;margin-top:2px}.bookExamBtn{border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;border-radius:9px;padding:5px 8px;font-size:12px;font-weight:900;cursor:pointer}.dbtOrderList{display:flex;flex-direction:column;gap:6px;max-height:420px;overflow:auto;margin-top:8px}.dbtOrderRow{display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--border);border-radius:10px;background:var(--bg)}.dbtOrderNum{font-weight:900;color:#64748b;min-width:1.5em}.dbtOrderName{flex:1;line-height:1.35}.dbtOrderBtns{display:flex;gap:4px}.bookDbtRow{display:flex;flex-direction:column;gap:4px;margin-top:4px;max-height:280px;overflow:auto;overflow-anchor:none;padding:6px;border:1px solid #fde68a;border-radius:10px;background:#fffbeb66}.bookDbtMoreHint{margin-top:4px;font-size:11px;font-weight:800;color:#92400e;text-align:center;opacity:.95}.bookDbtRow.isExpanded{max-height:none}.bookDbtBtn{display:grid;grid-template-columns:20px minmax(0,1fr) auto;align-items:flex-start;gap:5px;width:100%;border:1px solid #fde68a;background:#fffdf5;color:#92400e;border-radius:8px;padding:5px 7px;font-size:10.5px;font-weight:850;cursor:pointer;line-height:1.25;text-align:left}.bookDbtBtn:hover{filter:brightness(1.03)}.bookDbtNum{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:999px;background:#fef3c7;border:1px solid #fcd34d;color:#92400e;font-size:10px;font-weight:950;margin-top:1px}.bookDbtBody{min-width:0;display:flex;flex-direction:column;gap:2px}.bookDbtText{min-width:0;overflow:visible;text-overflow:unset;white-space:normal;word-break:break-word;line-height:1.35}.bookDbtMiniRow{display:flex;flex-wrap:wrap;gap:3px}.bookDbtMini{font-size:8.5px;font-weight:850;padding:1px 4px;border-radius:999px;border:1px solid #cbd5e1;line-height:1.2;white-space:nowrap}.bookDbtMini-tn{background:#dbeafe;color:#1d4ed8;border-color:#93c5fd}.bookDbtMini-ds{background:#f0fdf4;color:#166534;border-color:#86efac}.bookDbtMini-tln{background:#faf5ff;color:#7e22ce;border-color:#d8b4fe}.bookDbtMini-tl{background:#fff7ed;color:#c2410c;border-color:#fdba74}.bookDbtCount{font-size:10px;font-weight:950;color:#9a3412;white-space:nowrap;margin-top:1px}.bookDbtItem{display:flex;align-items:stretch;gap:4px;width:100%}.bookDbtItem .bookDbtBtn{flex:1;min-width:0}.bookDbtAiBtn{flex:0 0 auto;align-self:stretch;border:1px solid #c4b5fd;background:#f5f3ff;color:#5b21b6;border-radius:8px;padding:4px 8px;font-size:11px;font-weight:900;cursor:pointer;white-space:nowrap}.bookDbtAiBtn:hover{filter:brightness(.97);background:#ede9fe}.cdbtAiGenBtn{background:#f5f3ff!important;border-color:#c4b5fd!important;color:#5b21b6!important}.aiGenProvLbl{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:800;margin:0}.aiGenProvLbl select{font-size:12px;padding:5px 8px;border-radius:8px}.startDbtList{display:flex;flex-direction:column;gap:6px}.startDbtOpt{display:flex;gap:8px;align-items:flex-start;padding:8px 10px;border:1px solid var(--border);border-radius:10px;cursor:pointer;background:var(--surface)}.startDbtOpt:hover{background:var(--bg)}.startDbtOpt.startDbtUncls{border-color:#fdba74;background:#fff7ed}.bookDbtUncls{border-color:#fdba74!important;background:#fff7ed!important;color:#9a3412!important}.dbtMergeList{display:flex;flex-direction:column;gap:6px;max-height:320px;overflow:auto;margin-top:8px;padding:8px;border:1px solid var(--border);border-radius:10px;background:var(--surface)}.dbtMergeSuggestRow{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}.dbtMergeGroupBtn{font-size:11px!important;padding:4px 8px!important}.dbtMergePickRow{margin:0!important}.chapterDbtModalBox{max-width:980px!important}.chapterDbtBody{max-height:min(72vh,680px);overflow:auto;display:flex;flex-direction:column;gap:10px;margin-top:8px;padding-right:4px}.chapterDbtLesson{border:1px solid #93c5fd;border-radius:12px;background:var(--surface);overflow:visible}.chapterDbtRows{max-height:none;overflow:visible}.chapterDbtLesson{border:1px solid #93c5fd;border-radius:12px;background:var(--surface);overflow:hidden}.chapterDbtLessonHead{padding:10px 12px;background:#eff6ff;display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;font-weight:900;color:#1e3a8a}.chapterDbtLessonHead small{font-weight:800;color:#64748b;font-size:12px}.chapterDbtLessonTools{display:flex;flex-wrap:wrap;gap:6px}.chapterDbtRows{padding:8px 10px;display:flex;flex-direction:column;gap:6px}.chapterDbtRow{display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--border);border-radius:10px;background:var(--bg);flex-wrap:wrap}.chapterDbtRowTools{display:flex;align-items:center;gap:4px;flex-shrink:0}.chapterDbtMoveSel{font-size:11px;font-weight:800;padding:4px 6px;border:1px solid #93c5fd;border-radius:8px;background:#eff6ff;color:#1d4ed8;max-width:132px;cursor:pointer}.chapterDbtRowNum{color:#64748b;font-weight:900;min-width:1.4em}.chapterDbtRowName{flex:1;min-width:140px;line-height:1.35}.chapterDbtMergeBar{padding:8px 10px 10px;border-top:1px dashed #bfdbfe;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.chapterDbtMergeBar input{flex:1;min-width:160px;padding:7px 9px;border:1px solid #fde68a;border-radius:8px;background:#fffbeb}.chapterDbtSuggest{padding:8px 10px;border:1px solid #fde68a;border-radius:10px;background:#fffbeb;font-size:12px;line-height:1.45;margin-bottom:4px}.bookExamBtnAll{font-weight:950}.bookExamBtn:hover{filter:brightness(1.03);transform:translateY(-1px)}
  .bookLessonCard.selectedLesson{outline:2px solid #1d4ed8;background:#f8fbff}.bookLessonCard.shareTarget{outline:3px solid #60a5fa;box-shadow:0 0 0 4px #dbeafe}.bookLessonCard.catalogFlash{outline:3px solid #22c55e!important;box-shadow:0 0 0 4px #bbf7d088!important;animation:catalogFlashPulse .85s ease-in-out 2}@keyframes catalogFlashPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.012)}}.bookLessonCard .shareRow{margin-top:6px;flex-wrap:wrap}.bookLessonCard .shareBtns{flex-wrap:wrap}.bookEmpty{padding:14px;border:1px dashed #cbd5e1;border-radius:12px;color:#64748b;background:#f8fafc}
  html[data-theme='dark'] .bookIntroV246{background:linear-gradient(180deg,#172554,#0f172a);border-color:#1d4ed8}html[data-theme='dark'] .bookIntroTitle{color:#bfdbfe}html[data-theme='dark'] .bookStat{background:#0f172a;border-color:#334155;color:#bfdbfe}html[data-theme='dark'] .bookGradeBlock,html[data-theme='dark'] .bookLessonCard{background:#111827;border-color:#334155}html[data-theme='dark'] .bookGradeHead{background:#1e293b;color:#e5e7eb}html[data-theme='dark'] .bookChapterBlock{background:#0f172a;border-color:#1d4ed8}html[data-theme='dark'] .bookChapterHead{background:#1e3a5f;color:#bfdbfe}html[data-theme='dark'] .bookLessonTitle{color:#e5e7eb}html[data-theme='dark'] .bookTag{background:#1e293b;border-color:#475569;color:#cbd5e1}html[data-theme='dark'] .bookTag.bookTagDang{background:#0f172a;border-color:#475569;color:#94a3b8}
  .bookLessonTags.bookLessonTagsCompact{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;gap:4px;padding-bottom:1px}.bookLessonTags.bookLessonTagsCompact::-webkit-scrollbar{display:none}.bookTag.bookTagDang{color:#475569;border-color:#cbd5e1;background:#f1f5f9;letter-spacing:-.02em}
  @media(max-width:760px){.bookIntroV246{padding:10px;border-radius:13px}.bookSubjectTitle{font-size:15px;padding:9px 10px}.bookGradeHead{padding:9px 10px}.bookChapterBlock{margin:8px}.bookChapterHead{padding:8px 9px}.bookLessonList{grid-template-columns:1fr;padding:7px}.bookLessonCard{padding:9px;border-radius:12px}.bookExamBtn{font-size:11px;padding:5px 7px}.bookFilterHint{font-size:11px}.bookSubjectTitle small,.bookGradeHead .bookMini,.bookChapterHead small{font-size:11px}.bookLessonTags.bookLessonTagsCompact{gap:3px!important}.bookLessonTags.bookLessonTagsCompact .bookTag{font-size:9.5px!important;padding:2px 5px!important;font-weight:800!important;flex-shrink:0!important;white-space:nowrap!important;line-height:1.25!important}}
  `;
  document.head.appendChild(st);
}
function v256EnsureCatalogCollapseCss(){
  if(document.getElementById('LDVL_CATALOG_COLLAPSE_V256'))return;
  let st=document.createElement('style');st.id='LDVL_CATALOG_COLLAPSE_V256';
  st.textContent=`
  .bookHeadTitle{display:inline-flex;align-items:center;gap:7px;min-width:0;line-height:1.3}
  .bookHeadTools{display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap;justify-content:flex-end;margin-left:auto}
  .bookCollapseBtn{border:1px solid #93c5fd!important;background:#eff6ff!important;color:#1d4ed8!important;border-radius:999px!important;padding:4px 9px!important;font-size:11px!important;font-weight:950!important;line-height:1.2!important;cursor:pointer!important;white-space:nowrap!important;width:auto!important;min-height:28px!important}
  .bookCollapseBtn:hover{filter:brightness(1.03);transform:translateY(-1px)}
  .bookGradeBlock.isCollapsed .bookGradeBody,.bookChapterBlock.isCollapsed .bookLessonList{display:none!important}
  .bookGradeBlock.isCollapsed .bookGradeHead,.bookChapterBlock.isCollapsed .bookChapterHead{border-bottom:0}
  html[data-theme='dark'] .bookCollapseBtn{background:#0f172a!important;color:#bfdbfe!important;border-color:#3b82f6!important}
  @media(max-width:760px){.bookHeadTools{width:100%;justify-content:flex-start;margin-left:0}.bookCollapseBtn{font-size:10.5px!important;padding:4px 8px!important;min-height:27px!important}.bookHeadTitle{font-size:13px}}
  `;
  document.head.appendChild(st);
}
function v246EnsureDangBaiTapFilter(){
  v246EnsureBookCss();
  let fDang=document.getElementById('fDang');
  if(fDang&&!document.getElementById('fDangBaiTap')){
    let wrap=fDang.closest('.field');
    let field=document.createElement('div');field.className='field';
    field.innerHTML='<label>Dạng bài tập</label><select id="fDangBaiTap" onchange="onFilterChange(\'dangbaitap\')"><option value="">Tất cả</option></select>';
    if(wrap&&wrap.parentNode)wrap.parentNode.insertBefore(field,wrap.nextSibling);
  }
  let box=document.getElementById('catalogScopeBox');
  if(box&&!document.getElementById('bookFilterHintV246')){
    let hint=document.createElement('div');hint.id='bookFilterHintV246';hint.className='bookFilterHint';
    hint.innerHTML='<b>📚 Giao diện sách:</b> chọn <b>Môn</b> rồi xem lần lượt theo <b>Khối → Chương → Bài</b>. Bộ lọc chi tiết bên dưới gồm: Lớp, Chương, Bài, Mức độ, Loại câu hỏi, Dạng bài tập.';
    box.appendChild(hint);
  }
}
function v246LessonCatalogAsCatalog(){return ((META&&META.lesson_catalog)||[]).map(x=>({Mon:x.Mon||'',Lop:x.Lop||'',Chuong:x.Chuong||'',BaiHoc:x.BaiHoc||'',DangBaiTap:x.DangBaiTap||'',BoDe:'',De:x.BaiHoc||'',SoCau:0}))}
function v246ListForOptions(stage){
  let list=(CATALOG||[]).slice().concat(v246LessonCatalogAsCatalog());
  let mon=val('fMon')||'', khoi=window.CATALOG_SELECTED_KHOI||'', lop=val('fLop')||'', chuong=val('fChuong')||'', bai=val('fBaiHoc')||'', dbt=val('fDangBaiTap')||'';
  if(mon)list=list.filter(x=>x.Mon===mon);
  if(khoi)list=list.filter(x=>deriveKhoi(x.Lop)===khoi);
  if(stage==='lop')return list;
  if(lop)list=list.filter(x=>x.Lop===lop);
  if(stage==='chuong')return list;
  if(chuong)list=list.filter(x=>x.Chuong===chuong);
  if(stage==='baihoc')return list;
  if(bai)list=list.filter(x=>x.BaiHoc===bai);
  if(stage==='dangbaitap')return list;
  if(dbt)list=list.filter(x=>normText(x.DangBaiTap||'').includes(normText(dbt)));
  return list;
}
function refreshFilterOptions(){
  v246EnsureDangBaiTapFilter();
  // Dùng META.filters.Mon nếu CATALOG không có Mon (câu hỏi thiếu cột Mon)
  let monList=uniqField(CATALOG,'Mon');
  if(!monList.length&&META&&META.filters&&META.filters.Mon&&META.filters.Mon.length)monList=META.filters.Mon.filter(Boolean);
  setOptionsKeep('fMon',monList,val('fMon'));
  setOptionsKeep('fLop',uniqField(v246ListForOptions('lop'),'Lop'),val('fLop'));
  setOptionsKeep('fChuong',uniqField(v246ListForOptions('chuong'),'Chuong'),val('fChuong'));
  setOptionsKeep('fBaiHoc',uniqField(v246ListForOptions('baihoc'),'BaiHoc'),val('fBaiHoc'));
  setOptionsKeep('fDangBaiTap',uniqField(v246ListForOptions('dangbaitap'),'DangBaiTap'),val('fDangBaiTap'));
  setOptionsKeep('fBoDe',uniqField(v246ListForOptions('bode'),'BoDe'),val('fBoDe'));
  v245RenderCatalogScopeTabs();
  v246EnsureDangBaiTapFilter();
  if(typeof syncFilterGroupSummaries==='function')syncFilterGroupSummaries();
}
function onFilterChange(level){
  v246EnsureDangBaiTapFilter();
  if(level==='mon'){window.CATALOG_SELECTED_KHOI='';setVal('fLop','');setVal('fChuong','');setVal('fBaiHoc','');setVal('fDangBaiTap','');setVal('fBoDe','')}
  else if(level==='lop'){window.CATALOG_SELECTED_KHOI='';setVal('fChuong','');setVal('fBaiHoc','');setVal('fDangBaiTap','');setVal('fBoDe','')}
  else if(level==='chuong'){setVal('fBaiHoc','');setVal('fDangBaiTap','');setVal('fBoDe','')}
  else if(level==='baihoc'){setVal('fDangBaiTap','');setVal('fBoDe','')}
  else if(level==='dangbaitap'){setVal('fBoDe','')}
  if(level!=='extra')refreshFilterOptions(); else {v245RenderCatalogScopeTabs();v246EnsureDangBaiTapFilter();}
  renderCatalog();
  if(typeof syncRpFromMainFilters==='function')syncRpFromMainFilters();
  if(typeof syncFilterGroupSummaries==='function')syncFilterGroupSummaries();
}
function v246ItemMatchesFilter(x){
  let s=normText(val('fSearch'));let lv=(val('fMucDo')||'').trim().toUpperCase();let dg=(val('fDang')||'').trim();let dbt=(val('fDangBaiTap')||'').trim();let mc=filterMatchCount(x,lv,dg);if(mc!==null&&mc===0)return false;let solOnly=document.getElementById('fSolFullOnly')&&document.getElementById('fSolFullOnly').checked;if(solOnly&&(parseInt(x.SolFull,10)||0)<=0)return false;let blob=normText([x.Mon,x.Lop,x.Chuong,x.BaiHoc,x.DangBaiTap,x.BoDe,x.De,x.MucDo,x.Dang].join(' '));let levelOk=!lv||mc!==null||normText(x.MucDo||'').includes(normText(lv));let dangOk=!dg||mc!==null||normText(x.Dang||'').includes(normText(dg));let dbtOk=!dbt||normText(x.DangBaiTap||'').includes(normText(dbt));
  return(!val('fMon')||x.Mon==val('fMon'))&&(!window.CATALOG_SELECTED_KHOI||deriveKhoi(x.Lop)===window.CATALOG_SELECTED_KHOI)&&(!val('fLop')||x.Lop==val('fLop'))&&(!val('fChuong')||x.Chuong==val('fChuong'))&&(!val('fBaiHoc')||x.BaiHoc==val('fBaiHoc'))&&(!val('fBoDe')||x.BoDe==val('fBoDe'))&&dbtOk&&levelOk&&dangOk&&(!s||blob.includes(s));
}
function okFilter(x){return v246ItemMatchesFilter(x)}
function v246UniqTextFromEntries(entries,field,limit){let seen={},out=[];for(let x of entries||[]){let raw=String(x[field]||'').trim();if(!raw)continue;for(let part of raw.split(/[,;|]+/)){part=part.trim();if(!part)continue;let k=normText(part);if(seen[k])continue;seen[k]=1;out.push(part);if(limit&&out.length>=limit)return out}}return out}
function v246ShortDangLabel(d){let t=String(d||'').trim();if(t==='Trắc nghiệm')return 'TN';if(t==='Đúng sai')return 'Đ/S';if(t==='Trả lời ngắn')return 'TLN';if(t==='Tự luận')return 'TL';return shortText(t,10)}
function v246DangCssClass(d){if(d==='Trắc nghiệm')return 'dang-tn';if(d==='Đúng sai')return 'dang-ds';if(d==='Trả lời ngắn')return 'dang-tln';if(d==='Tự luận')return 'dang-tl';return 'dang-other'}
function v246SumFilterDangs(entries){let totals={};for(let x of entries||[]){let fc=x&&x.FilterCounts;if(fc&&fc.dang){for(let k in fc.dang){let nd=normDangClient(k);totals[nd]=(totals[nd]||0)+(parseInt(fc.dang[k],10)||0)}continue}let sc=parseInt(x.SoCau,10)||0;if(!sc)continue;let parts=String(x.Dang||'').split(/[,;|]+/).map(s=>s.trim()).filter(Boolean);if(parts.length===1)totals[normDangClient(parts[0])]=(totals[normDangClient(parts[0])]||0)+sc;else if(parts.length>1)parts.forEach(p=>{let nd=normDangClient(p);totals[nd]=(totals[nd]||0)+Math.round(sc/parts.length)})}return totals}
function v246DangCountTags(entries){let totals=v246SumFilterDangs(entries);let order=['Trắc nghiệm','Đúng sai','Trả lời ngắn','Tự luận'];let out=[];for(let d of order){let n=totals[d]||0;if(n)out.push(`<span class="bookTag ${v246DangCssClass(d)}" title="${escAttr(d)}: ${n} câu">${v246ShortDangLabel(d)}·${n}</span>`)}for(let d in totals){if(!order.includes(d)&&(totals[d]||0))out.push(`<span class="bookTag ${v246DangCssClass(d)}" title="${escAttr(d)}: ${totals[d]} câu">${esc(v246ShortDangLabel(d))}·${totals[d]}</span>`)}return out.join('')}
function v246FmtDbtDate(u){u=String(u||'').trim();if(!u)return '';let m=u.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);if(!m)return u.slice(0,8);let yy=m[3].length===4?m[3].slice(2):m[3];return m[1].padStart(2,'0')+'/'+m[2].padStart(2,'0')+'/'+yy}
function v246MergeDbtDetail(entries,dbtKey){let dang={},level={},updated='';for(let x of entries||[]){let block=x&&x.FilterCounts&&x.FilterCounts.dbt_detail&&x.FilterCounts.dbt_detail[dbtKey];if(!block)continue;if(block.dang)for(let k in block.dang){let nd=normDangClient(k);dang[nd]=(dang[nd]||0)+(parseInt(block.dang[k],10)||0)}if(block.level)for(let k in block.level){level[k]=(level[k]||0)+(parseInt(block.level[k],10)||0)}if(block.updated){if(!updated)updated=String(block.updated);else{let a=String(block.updated),b=updated;let pa=a.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/),pb=b.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);if(pa&&pb){let da=new Date((pa[3].length===2?2000+parseInt(pa[3],10):parseInt(pa[3],10)),parseInt(pa[2],10)-1,parseInt(pa[1],10));let db=new Date((pb[3].length===2?2000+parseInt(pb[3],10):parseInt(pb[3],10)),parseInt(pb[2],10)-1,parseInt(pb[1],10));if(da>=db)updated=a}else if(a>b)updated=a}}}return {dang,level,updated}}
function v246DbtUpdatedNote(dbtKey,entries){if(!dbtKey||dbtKey===DBT_UNCLASSIFIED)return '';let u=(v246MergeDbtDetail(entries,dbtKey).updated||'').trim();if(!u)return '';let short=v246FmtDbtDate(u);return `<span class="bookDbtUpdated" title="Ngày cập nhật dạng: ${escAttr(u)}">${esc(short)}</span>`}
function catalogDbtUpdated(item,dbtKey){item=item||{};let block=((item.FilterCounts||{}).dbt_detail||{})[dbtKey];let u=block&&block.updated?String(block.updated).trim():'';return u?v246FmtDbtDate(u):''}
function v246DbtDangTipText(dbtKey,entries){let det=v246MergeDbtDetail(entries,dbtKey);let order=['Trắc nghiệm','Đúng sai','Trả lời ngắn','Tự luận'];let bits=order.filter(d=>(det.dang[d]||0)>0).map(d=>v246ShortDangLabel(d)+': '+det.dang[d]);return bits.join(' · ')}
function v246DbtDangMiniHtml(dbtKey,entries){let det=v246MergeDbtDetail(entries,dbtKey);let order=['Trắc nghiệm','Đúng sai','Trả lời ngắn','Tự luận'];let out=[];for(let d of order){let n=det.dang[d]||0;if(n)out.push(`<span class="bookDbtMini bookDbtMini-${v246DangCssClass(d).replace('dang-','')}">${v246ShortDangLabel(d)}·${n}</span>`)}return out.length?`<span class="bookDbtMiniRow">${out.join('')}</span>`:''}
function v246SumFilterLevels(entries){let levels=['NB','TH','VD','VDC'];let totals={NB:0,TH:0,VD:0,VDC:0};for(let x of entries||[]){let fc=x&&x.FilterCounts;if(fc&&fc.level){for(let lv of levels)totals[lv]+=parseInt(fc.level[lv],10)||0;continue}let sc=parseInt(x.SoCau,10)||0;if(!sc)continue;let md=String(x.MucDo||'').trim().toUpperCase();let parts=md.split(/[,;|/]+/).map(s=>s.trim()).filter(Boolean);let hit=parts.filter(p=>levels.includes(p));if(hit.length===1)totals[hit[0]]+=sc;else if(hit.length>1)hit.forEach(lv=>{totals[lv]+=Math.round(sc/hit.length)})}return totals}
function v246LevelTags(entries){let levels=['NB','TH','VD','VDC'];let totals=v246SumFilterLevels(entries);let out=[];for(let lv of levels){let n=totals[lv]||0;if(n)out.push(`<span class="bookTag ${lv.toLowerCase()}" title="${lv}: ${n} câu">${lv}·${n}</span>`)}return out.join('')}
const STUDENT_PROGRESS_COMPLETE_PCT=70;
function studentProgressEnabled(){return !!(USER&&USER.mahs&&(!USER.is_admin||window.LDVL_ADMIN_STUDENT_MODE))}
function lessonProgressKeyFromParts(mon,khoi,chuong,bai){return [normText(mon||''),normText(khoi||''),normText(chuong||''),normText(bai||'')].join('|')}
function chapterProgressKeyFromParts(mon,khoi,chuong){return [normText(mon||''),normText(khoi||''),normText(chuong||'')].join('|')}
function practiceProgressKey(made,dbt){made=String(made||'').trim();dbt=String(dbt||'').trim();return made+(dbt?'|'+normText(dbt):'')}
function localPracticeProgressStorageKey(){return 'LDVL_PRACTICE_PROGRESS_V1|'+(USER&&USER.mahs?String(USER.mahs).trim():'')}
function loadLocalPracticeProgress(){if(!studentProgressEnabled())return null;try{let raw=localStorage.getItem(localPracticeProgressStorageKey());if(!raw)return null;let j=JSON.parse(raw);return j&&typeof j==='object'?j:null}catch(e){return null}}
function saveLocalPracticeProgress(data){if(!studentProgressEnabled())return;try{localStorage.setItem(localPracticeProgressStorageKey(),JSON.stringify(data||{}))}catch(e){}}
function mergeProgressEntryClient(cur,pct){cur=cur||{};let attempts=(parseInt(cur.attempts,10)||0)+1;let best=parseFloat(cur.best_pct)||0;let p=parseFloat(pct)||0;if(p>best)best=p;let done=!!cur.done||attempts>0;let complete=!!cur.complete||best>=STUDENT_PROGRESS_COMPLETE_PCT;return {attempts,best_pct:Math.round(best*10)/10,last_pct:Math.round(p*10)/10,done,complete}}
function mergeProgressMaps(dst,src){dst=dst||{};src=src||{};for(let k in src){if(!Object.prototype.hasOwnProperty.call(src,k))continue;let s=src[k]||{};let d=dst[k]||{};let best=Math.max(parseFloat(d.best_pct)||0,parseFloat(s.best_pct)||0);dst[k]={attempts:(parseInt(d.attempts,10)||0)+(parseInt(s.attempts,10)||0),best_pct:Math.round(best*10)/10,last_pct:Math.round((parseFloat(s.last_pct)||parseFloat(d.last_pct)||0)*10)/10,done:!!(d.done||s.done),complete:!!(d.complete||s.complete||best>=STUDENT_PROGRESS_COMPLETE_PCT)};if((parseInt(dst[k].attempts,10)||0)<1&&(dst[k].done||dst[k].complete))dst[k].attempts=1}return dst}
function mergeStudentProgressFromLocal(){if(!studentProgressEnabled())return;let local=loadLocalPracticeProgress();let server=(META&&META.student_progress)||{};if(!local&&!server)return;META=META||{};let merged={complete_pct:STUDENT_PROGRESS_COMPLETE_PCT,lessons:{},chapters:{},practices:{},made_map:server.made_map||{}};mergeProgressMaps(merged.lessons,server.lessons||{});mergeProgressMaps(merged.chapters,server.chapters||{});mergeProgressMaps(merged.practices,server.practices||{});if(local){mergeProgressMaps(merged.lessons,local.lessons||{});mergeProgressMaps(merged.chapters,local.chapters||{});mergeProgressMaps(merged.practices,local.practices||{})}META.student_progress=merged}
function getMergedStudentProgress(){mergeStudentProgressFromLocal();return (META&&META.student_progress)||{lessons:{},chapters:{},practices:{}}}
function progressLookup(map,key){if(!map||!key)return null;return map[key]||null}
function progressStatusTags(entry){if(!studentProgressEnabled()||!entry)return '';if(entry.complete)return `<span class="bookTag bookTagComplete" title="Đạt ${Math.round(entry.best_pct||STUDENT_PROGRESS_COMPLETE_PCT)}% trở lên">✓ Hoàn thành</span>`;if(entry.done)return `<span class="bookTag bookTagDone" title="Đã nộp bài luyện tập">Đã làm</span>`;return ''}
function lessonProgressForCard(mon,khoi,chuong,bai,entries){if(!studentProgressEnabled())return null;let p=(entries&&entries[0])||{};let lop=String(p.Lop||khoi||'').trim();let key=lessonProgressKeyFromParts(mon,lop,chuong,bai);let sp=getMergedStudentProgress();return progressLookup(sp.lessons,key)}
function chapterProgressForCard(mon,khoi,chuong,chList){if(!studentProgressEnabled())return null;let p=(chList&&chList[0])||{};let lop=String(p.Lop||khoi||'').trim();let key=chapterProgressKeyFromParts(mon,lop,chuong);let sp=getMergedStudentProgress();return progressLookup(sp.chapters,key)}
function practiceProgressForSession(made,dbt){if(!studentProgressEnabled())return null;let sp=getMergedStudentProgress();return progressLookup(sp.practices,practiceProgressKey(made,dbt))||progressLookup(sp.practices,practiceProgressKey(made,''))}
function resultAttemptPctFromSubmit(j){j=j||{};let auto=parseInt(j.auto_count,10)||0;let correct=parseInt(j.correct_count,10)||0;if(auto>0)return Math.round(1000*correct/auto)/10;let sc=parseFloat(j.score)||0;if(sc>0)return Math.min(100,Math.round(sc*100)/10);return 0}
function recordPracticeProgressFromSubmit(j){if(!studentProgressEnabled()||!CURRENT_MADE)return;let pct=resultAttemptPctFromSubmit(j);let made=String(CURRENT_MADE||'').trim();let dbt=String(CURRENT_DANGBAITAP||'').trim();let item=CATALOG.find(x=>x.MaDe===made)||QUESTIONS[0]||{};let mon=item.Mon||'';let lop=item.Lop||'';let chuong=item.Chuong||'';let bai=item.BaiHoc||item.De||'';let lk=lessonProgressKeyFromParts(mon,lop,chuong,bai);let ck=chapterProgressKeyFromParts(mon,lop,chuong);let pk=practiceProgressKey(made,dbt);let local=loadLocalPracticeProgress()||{complete_pct:STUDENT_PROGRESS_COMPLETE_PCT,lessons:{},chapters:{},practices:{}};local.lessons=local.lessons||{};local.chapters=local.chapters||{};local.practices=local.practices||{};local.lessons[lk]=mergeProgressEntryClient(local.lessons[lk],pct);local.chapters[ck]=mergeProgressEntryClient(local.chapters[ck],pct);local.practices[pk]=mergeProgressEntryClient(local.practices[pk],pct);if(!dbt)local.practices[practiceProgressKey(made,'')]=mergeProgressEntryClient(local.practices[practiceProgressKey(made,'')],pct);saveLocalPracticeProgress(local);if(META){META.student_progress=META.student_progress||{lessons:{},chapters:{},practices:{}};META.student_progress.lessons=mergeProgressMaps(META.student_progress.lessons||{},local.lessons);META.student_progress.chapters=mergeProgressMaps(META.student_progress.chapters||{},local.chapters);META.student_progress.practices=mergeProgressMaps(META.student_progress.practices||{},local.practices)}try{ldvlStudentProgressPushLocalAttempt(j,item,pct)}catch(e){}try{if(window.__LDVL_PROGRESS_TAB_OPEN)ldvlStudentProgressLoad(true)}catch(e){}}
let LDVL_PRACTICE_LOG_CACHE=null;
let LDVL_PRACTICE_LOG_LOADING=false;
function ldvlStudentProgressSyncNav(){let btn=document.getElementById('ldvlQnavProgress');if(!btn)return;let show=!!(USER&&USER.mahs&&(!USER.is_admin||window.LDVL_ADMIN_STUDENT_MODE)&&!USER.is_trial);btn.classList.toggle('hide',!show)}
function ldvlProgressPctLabel(pct){return Math.round(parseFloat(pct)||STUDENT_PROGRESS_COMPLETE_PCT)}
function ldvlStudentProgressPushLocalAttempt(j,item,pct){if(!studentProgressEnabled())return;item=item||{};j=j||{};let made=String(CURRENT_MADE||'').trim();let dbt=String(CURRENT_DANGBAITAP||'').trim();let lv=String(CURRENT_LEVEL||'').trim();let att={time:new Date().toISOString().slice(0,19).replace('T',' '),time_sort:new Date().toISOString(),made,title:String(item.De||item.BaiHoc||made||'').trim(),mon:item.Mon||'',lop:item.Lop||'',chuong:item.Chuong||'',bai_hoc:item.BaiHoc||item.De||'',level:lv,dangbaitap:dbt,score:parseFloat(j.score)||0,correct:parseInt(j.correct_count,10)||0,total:parseInt(j.auto_count,10)||0,pct:pct,complete:pct>=STUDENT_PROGRESS_COMPLETE_PCT,done:true,elapsed_text:fmtTime(QUIZ_ELAPSED||0),exam_mode:!!EXAM_MODE,_local:1};let key=localPracticeProgressStorageKey()+'|log';let arr=[];try{arr=JSON.parse(localStorage.getItem(key)||'[]')}catch(e){arr=[]}if(!Array.isArray(arr))arr=[];arr.unshift(att);if(arr.length>80)arr=arr.slice(0,80);try{localStorage.setItem(key,JSON.stringify(arr))}catch(e){}}
function ldvlStudentProgressMergeLocalLog(serverLog){serverLog=serverLog||{attempts:[],groups:[],summary:{}};let key=localPracticeProgressStorageKey()+'|log';let local=[];try{local=JSON.parse(localStorage.getItem(key)||'[]')}catch(e){local=[]}if(!Array.isArray(local)||!local.length)return serverLog;let attempts=(serverLog.attempts||[]).slice();let seen=new Set(attempts.map(a=>[a.time,a.made,a.score,a.pct].join('|')));for(let a of local){let sig=[a.time,a.made,a.score,a.pct].join('|');if(seen.has(sig))continue;seen.add(sig);attempts.unshift(a)}attempts.sort((a,b)=>String(b.time_sort||b.time||'').localeCompare(String(a.time_sort||a.time||'')));let out=Object.assign({},serverLog,{attempts});out.summary=Object.assign({},serverLog.summary||{},{total_attempts:attempts.length});return out}
function ldvlProgressFormatStudentCard(data){data=data||{};let st=data.student||{};let u=USER||{};let hoten=String(st.hoten||u.hoten||'').trim()||'Học viên';let mahs=String(st.mahs||u.mahs||'').trim();let lop=String(st.lop||u.lop||'').trim();let role=String(st.role_label||u.role_label||'').trim();let card=document.getElementById('ldvlProgressStudentCard');let av=document.getElementById('ldvlProgressStudentAvatar');let nm=document.getElementById('ldvlProgressStudentName');let meta=document.getElementById('ldvlProgressStudentMeta');let cnt=document.getElementById('ldvlProgressStudentAttemptCount');if(!card)return;card.classList.remove('hide');if(av)av.textContent=(hoten.charAt(0)||'?').toUpperCase();if(nm)nm.textContent=hoten;let bits=[];if(mahs)bits.push('Mã HS: '+mahs);if(lop)bits.push('Lớp '+lop);if(role)bits.push(role);if(meta)meta.textContent=bits.join(' · ')||'Đang theo dõi tiến độ rèn luyện';let total=(data.summary&&data.summary.total_attempts)||0;if(cnt)cnt.textContent=String(total)}
function ldvlProgressAnnotateAttempts(attempts){attempts=(attempts||[]).slice();let asc=attempts.slice().sort((a,b)=>String(a.time_sort||a.time||'').localeCompare(String(b.time_sort||b.time||'')));let nth={},totals={};for(let a of asc){let pk=practiceProgressKey(a.made,a.dangbaitap);nth[pk]=(nth[pk]||0)+1;a.attempt_no=nth[pk];totals[pk]=nth[pk]}for(let a of attempts){let pk=practiceProgressKey(a.made,a.dangbaitap);a.attempt_total=totals[pk]||a.attempt_no||1}return attempts.sort((a,b)=>String(b.time_sort||b.time||'').localeCompare(String(a.time_sort||a.time||'')))}
function ldvlStudentProgressRender(data){data=data||{};ldvlProgressFormatStudentCard(data);let pctLbl=document.getElementById('ldvlProgressPctLabel');if(pctLbl)pctLbl.textContent=String(ldvlProgressPctLabel(data.complete_pct));let sumEl=document.getElementById('ldvlProgressSummary');let grpEl=document.getElementById('ldvlProgressGroups');let logEl=document.getElementById('ldvlProgressLog');if(!sumEl||!grpEl||!logEl)return;let sm=data.summary||{};sumEl.innerHTML=[{v:sm.total_attempts||0,l:'Tổng lần làm'},{v:sm.unique_practices||0,l:'Chủ đề / dạng BT'},{v:sm.complete_count||0,l:'Đã hoàn thành'},{v:ldvlProgressPctLabel(data.complete_pct)+'%',l:'Ngưỡng HT'}].map(x=>`<div class="ldvlProgressStat"><b>${esc(String(x.v))}</b><span>${esc(x.l)}</span></div>`).join('');let groups=data.groups||[];if(!groups.length)grpEl.innerHTML='<div class="ldvlProgressEmpty">Chưa có bài nào được ghi nhận. Hãy vào <b>Mục lục</b>, chọn dạng BT và bấm <b>Nộp bài</b> sau khi làm xong.</div>';else grpEl.innerHTML=groups.map(g=>{let tags=progressStatusTags({done:!!g.done,complete:!!g.complete,best_pct:g.best_pct});let scope=[g.mon,g.lop?('Lớp '+g.lop):'',g.chuong,g.bai_hoc].filter(Boolean).join(' · ');let dbt=g.dangbaitap?('<span class="bookTag bookTagDang">'+esc(oneLineText(g.dangbaitap))+'</span>'):'';let lv=g.level?('<span class="bookTag '+String(g.level).toLowerCase()+'">'+esc(g.level)+'</span>'):'';let attN=parseInt(g.attempts,10)||0;let attBadge=attN?`<span class="ldvlProgressGroupAttempts" title="Đã làm bài này">🔁 ${attN} lần</span>`:'';return `<div class="ldvlProgressGroup"><div class="ldvlProgressGroupHead"><div class="ldvlProgressGroupTitle">${esc(g.title||g.made||'Bài luyện')}</div><div class="ldvlProgressGroupTags">${attBadge}${tags}${dbt}${lv}</div></div><div class="ldvlProgressGroupMeta">${esc(scope)}${g.last_time?(' · Lần cuối: '+esc(g.last_time)):''} · Đã làm <b>${esc(String(attN||0))}</b> lần · Điểm cao nhất: <b>${esc(String(Math.round((g.best_pct||0)*10)/10))}%</b> · Lần gần nhất: <b>${esc(String(g.last_score||0))}/10</b></div></div>`}).join('');let attempts=ldvlProgressAnnotateAttempts((data.attempts||[]).slice());if(!attempts.length)logEl.innerHTML='<div class="ldvlProgressEmpty">Chưa có lịch sử chi tiết.</div>';else logEl.innerHTML=attempts.map(a=>{let tags=a.complete?'<span class="bookTag bookTagComplete">✓ HT</span>':(a.done?'<span class="bookTag bookTagDone">Đã làm</span>':'');let attemptBit=(a.attempt_no?`<span class="ldvlProgressAttemptBadge">Lần ${esc(String(a.attempt_no))}${(a.attempt_total||0)>1?'/'+esc(String(a.attempt_total)):''}</span>`:'');let bits=[a.mon,a.chuong,a.bai_hoc,a.level?('Mức '+a.level):'',a.dangbaitap?oneLineText(a.dangbaitap):''].filter(Boolean);return `<div class="ldvlProgressRow"><div class="ldvlProgressRowTime">${esc(a.time||'—')}</div><div><div class="ldvlProgressRowTitle">${esc(a.title||a.made||'Bài luyện')}${attemptBit} ${tags}</div><div class="ldvlProgressRowSub">${esc(bits.join(' · '))}${a.elapsed_text?(' · ⏱ '+esc(a.elapsed_text)):''}${a.exam_mode?' · 🧪 Kiểm tra':''}</div></div><div class="ldvlProgressRowScore">${esc(String(a.score!=null?a.score:''))}/10<small>${esc(String(a.correct||0))}/${esc(String(a.total||0))} · ${esc(String(a.pct||0))}%</small></div></div>`}).join('')}
async function ldvlStudentProgressLoad(force){if(!studentProgressEnabled()){ldvlStudentProgressRender({attempts:[],groups:[],summary:{},student:{hoten:(USER&&USER.hoten)||'',mahs:(USER&&USER.mahs)||'',lop:(USER&&USER.lop)||'',role_label:(USER&&USER.role_label)||''},complete_pct:STUDENT_PROGRESS_COMPLETE_PCT});return}let panel=document.getElementById('ldvlStudentProgressPanel');if(panel&&!force&&LDVL_PRACTICE_LOG_CACHE){ldvlStudentProgressRender(LDVL_PRACTICE_LOG_CACHE);return}if(LDVL_PRACTICE_LOG_LOADING)return;LDVL_PRACTICE_LOG_LOADING=true;let sumEl=document.getElementById('ldvlProgressSummary');if(sumEl&&!LDVL_PRACTICE_LOG_CACHE)sumEl.innerHTML='<div class="muted" style="grid-column:1/-1">⏳ Đang tải nhật ký rèn luyện…</div>';try{let j=await api('/api/student-practice-log',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({}),timeoutMs:60000});j=ldvlStudentProgressMergeLocalLog(j);LDVL_PRACTICE_LOG_CACHE=j;ldvlStudentProgressRender(j)}catch(e){let msg=String(e&&e.message||e||'Không tải được');ldvlStudentProgressRender({attempts:[],groups:[],summary:{},complete_pct:STUDENT_PROGRESS_COMPLETE_PCT});let logEl=document.getElementById('ldvlProgressLog');if(logEl)logEl.innerHTML='<div class="ldvlProgressEmpty">⚠ '+esc(msg)+'</div>'}finally{LDVL_PRACTICE_LOG_LOADING=false}}
window.ldvlStudentProgressLoad=ldvlStudentProgressLoad;
window.ldvlStudentProgressSyncNav=ldvlStudentProgressSyncNav;
(function(){let sh=document.getElementById('ldvlStudentHome');if(!sh)return;let obs=new MutationObserver(function(){window.__LDVL_PROGRESS_TAB_OPEN=sh.classList.contains('homeTab-progress')});obs.observe(sh,{attributes:true,attributeFilter:['class']})})();
function v246LessonCard(mon,khoi,chuong,bai,entries){
  entries=entries||[];let qs=entries.reduce((a,x)=>a+(parseInt(x.SoCau,10)||0),0);let dbtMerge=v246MergeDbtCounts(entries);let dbtPairs=dbtMerge.pairs||[];let uncls=dbtMerge.unclassified||0;let primary=entries[0]||{};let lessonMade=catalogLessonMadeForPractice(entries);let made=String(lessonMade||primary.MaDe||'').replace(/'/g,"\\'");let lessonProg=lessonProgressForCard(mon,khoi,chuong,bai,entries);let progTags=progressStatusTags(lessonProg);let dbtItems=[];if(uncls>0)dbtItems.push({d:DBT_UNCLASSIFIED,n:uncls,label:'Chưa phân loại',uncls:true});dbtPairs.forEach(([d,n])=>dbtItems.push({d,n,label:d,uncls:false}));let monAi=String(mon||primary.Mon||'');let lopAi=String(primary.Lop||khoi||'');let chuongAi=String(chuong||primary.Chuong||'');let baiAi=String(bai||primary.BaiHoc||'');let dbtBtns=dbtItems.map((it,i)=>{let dd=String(it.d||'').replace(/'/g,"\\'");let cls=it.uncls?' bookDbtUncls':'';let pp=practiceProgressForSession(lessonMade||primary.MaDe||'',it.d||'');if(pp&&pp.complete)cls+=' isPracticeComplete';else if(pp&&pp.done)cls+=' isPracticeDone';let tipBase=it.uncls?'Câu chưa có Dạng BT — ADMIN dùng AI phân loại':('Luyện: '+it.label);let tipDang=v246DbtDangTipText(it.d,entries);let title=tipDang?(tipBase+' — '+tipDang):tipBase;if(pp&&pp.complete)title+=' · Hoàn thành '+Math.round(pp.best_pct||0)+'%';else if(pp&&pp.done)title+=' · Đã làm';let mini=v246DbtDangMiniHtml(it.d,entries);let updNote=v246DbtUpdatedNote(it.d,entries);let progMini=(pp&&pp.complete)?'<span class="bookDbtProg bookDbtProgComplete">✓</span>':((pp&&pp.done)?'<span class="bookDbtProg bookDbtProgDone">✓</span>':'');let practiceBtn=`<button type="button" class="bookDbtBtn${cls}" data-made="${escAttr(lessonMade||primary.MaDe||'')}" data-dbt="${escAttr(oneLineText(it.d||''))}" onclick="openStartModal(this.dataset.made,this.dataset.dbt)" title="${escAttr(title)}"><span class="bookDbtNum">${i+1}</span><span class="bookDbtBody"><span class="bookDbtText">${esc(oneLineText(it.label))}</span>${mini}</span><span class="bookDbtMeta">${progMini}${it.n?`<b class="bookDbtCount">${it.n}</b>`:''}${updNote}</span></button>`;let aiBtn=(USER&&USER.is_admin&&!it.uncls)?`<button type="button" class="bookDbtAiBtn" data-mon="${escAttr(monAi)}" data-lop="${escAttr(lopAi)}" data-chuong="${escAttr(chuongAi)}" data-bai="${escAttr(baiAi)}" data-dbt="${escAttr(it.d||'')}" onclick="event.stopPropagation();openAdminAiGenFromEl(this)" title="ADMIN: Tạo thêm câu bằng Gemini/Claude cho dạng này">🤖 AI</button>`:'';return `<div class="bookDbtItem">${practiceBtn}${aiBtn}</div>`}).join('');let allBtn=made?`<button type="button" class="bookExamBtn bookExamBtnAll" onclick="openStartModal('${made}','')">📂 Chuyên đề · ${qs} câu</button>`:'';let selected=(val('fBaiHoc')&&entries.some(x=>x.BaiHoc===val('fBaiHoc')))?' selectedLesson':'';
  let orderBtn=(USER&&USER.is_admin&&made&&dbtPairs.length)?`<button type="button" class="bookExamBtn" onclick="openDbtOrderModal('${made}')" title="ADMIN: sắp xếp thứ tự dạng BT">↕ Thứ tự dạng</button>`:'';
  let madeRaw=String(primary.MaDe||'');let shareTools=madeRaw?v246ShareToolsHtml(primary,made):'';
  let cardCompleteCls=(lessonProg&&lessonProg.complete)?' lessonComplete':'';
  let cardDoneCls=(lessonProg&&lessonProg.done&&!lessonProg.complete)?' lessonDone':'';
  return `<div class="bookLessonCard${selected}${cardCompleteCls}${cardDoneCls}" id="shareCard_${escAttr(madeRaw)}" data-bai="${escAttr(bai||'')}" data-chuong="${escAttr(chuong||'')}"><div class="bookLessonTitle">${esc(bai||'Chưa rõ bài')}${progTags?`<span class="bookLessonProg">${progTags}</span>`:''}</div><div class="bookLessonSub">${esc(mon||'')} · Khối ${esc(khoi||'')} · ${esc(chuong||'Chưa rõ chương')}</div><div class="bookLessonTags bookLessonTagsCompact"><span class="bookTag" title="${qs} câu"><b>${qs}</b>c</span>${dbtPairs.length?`<span class="bookTag" title="${dbtPairs.length} dạng bài tập">${dbtPairs.length}dbt</span>`:`<span class="bookTag" title="${entries.length} thẻ đề">${entries.length} thẻ</span>`}${v246LevelTags(entries)}${v246DangCountTags(entries)}</div>${dbtBtns?`<div class="bookDbtRow" id="bookDbtRow_${escAttr(madeRaw)}">${dbtBtns}${dbtItems.length>5?`<div class="bookDbtMoreHint">↕ ${dbtItems.length} dạng — kéo xuống để xem hết (Sheet có đủ)</div>`:''}</div>`:''}<div class="bookExamRow">${allBtn}${orderBtn}</div>${shareTools}</div>`;
}
function v246GroupBy(list,fn){let mp=new Map();for(let x of list){let k=fn(x)||'Chưa rõ';if(!mp.has(k))mp.set(k,[]);mp.get(k).push(x)}return mp}
function catalogCollapseKey(kind,parts){return 'LDVL_CAT_COLLAPSE_V256|'+kind+'|'+(parts||[]).map(x=>normText(x||'')).join('|')}
function isCatalogCollapsedKey(key){try{var v=localStorage.getItem(key);if(v===null||v==='')return true;return v==='1'}catch(e){return true}}
function catalogCollapseBtnHtml(kind,key,collapsed,label){
  return `<button type="button" class="bookCollapseBtn" data-collapse-kind="${escAttr(kind)}" data-collapse-key="${escAttr(key)}" aria-expanded="${collapsed?'false':'true'}" onclick="toggleCatalogCollapseKey(this,event)">${collapsed?'▼ Mở':'▲ Thu'} ${esc(label||'')}</button>`;
}
function toggleCatalogCollapseKey(btn,ev){
  if(ev){ev.preventDefault();ev.stopPropagation()}
  let key=btn&&btn.getAttribute?btn.getAttribute('data-collapse-key'):'';
  if(!key)return false;
  let collapsed=!isCatalogCollapsedKey(key);
  try{localStorage.setItem(key,collapsed?'1':'0')}catch(e){}
  renderCatalog();
  return false;
}
function expandAllCatalogSections(){
  try{
    let rm=[];
    for(let i=0;i<localStorage.length;i++){let k=localStorage.key(i);if(k&&k.indexOf('LDVL_CAT_COLLAPSE_V256|')===0)rm.push(k)}
    rm.forEach(k=>localStorage.removeItem(k));
  }catch(e){}
  renderCatalog();
}
function v246BookHtml(list){
  if(!list.length)return '<div class="bookEmpty">Không có đề phù hợp với bộ lọc hiện tại.</div>';
  let html='<div class="bookShelfV246">';
  let byMon=v246GroupBy(list,x=>x.Mon||'Chưa rõ môn');
  for(let [mon,monList] of byMon){let monQ=monList.reduce((a,x)=>a+(parseInt(x.SoCau,10)||0),0);html+=`<section class="bookSubjectBlock"><div class="bookSubjectTitle"><span>${esc(mon)}</span><small>${monList.length} thẻ · ${monQ} câu</small></div>`;let byKhoi=v246GroupBy(monList,x=>{let k=deriveKhoi(x.Lop);if(k)return 'Khối '+k;let lop=String(x.Lop||'').trim();return lop?'Lớp '+lop:'Lớp khác';});
    for(let [khoiLabel,khoiList] of byKhoi){let khoi=khoiLabel.replace(/^(?:Khối|Lớp)\s*/,'');let gradeWord=khoiLabel.startsWith('Lớp')?'lớp':'khối';let kQ=khoiList.reduce((a,x)=>a+(parseInt(x.SoCau,10)||0),0);let gKey=catalogCollapseKey('grade',[mon,khoiLabel]);let gCollapsed=isCatalogCollapsedKey(gKey);html+=`<div class="bookGradeBlock${gCollapsed?' isCollapsed':''}"><div class="bookGradeHead"><span class="bookHeadTitle">${esc(khoiLabel)}</span><span class="bookHeadTools"><span class="bookMini">${khoiList.length} thẻ · ${kQ} câu</span>${catalogCollapseBtnHtml('grade',gKey,gCollapsed,gradeWord)}</span></div><div class="bookGradeBody">`;let byChuong=v246GroupBy(khoiList,x=>x.Chuong||'Chưa rõ chương');
      if(!gCollapsed)for(let [chuong,chList] of byChuong){let chQ=chList.reduce((a,x)=>a+(parseInt(x.SoCau,10)||0),0);let chKey=catalogCollapseKey('chapter',[mon,khoiLabel,chuong]);let chCollapsed=isCatalogCollapsedKey(chKey);let chProg=chapterProgressForCard(mon,khoi,chuong,chList);let chProgTags=progressStatusTags(chProg);let chCompleteCls=(chProg&&chProg.complete)?' isChapterComplete':'';let chAdminBtn=(USER&&USER.is_admin)?`<button type="button" class="bookExamBtn bookChapterDbtBtn" data-mon="${escAttr(mon)}" data-khoi="${escAttr(khoi)}" data-chuong="${escAttr(chuong)}" title="ADMIN: gom, gộp, sắp thứ tự dạng BT cả chương">🏷️ Quản lý dạng BT</button>`:'';html+=`<div class="bookChapterBlock${chCollapsed?' isCollapsed':''}${chCompleteCls}"><div class="bookChapterHead"><span class="bookHeadTitle">${esc(chuong)}${chProgTags?`<span class="bookChapterProg">${chProgTags}</span>`:''}</span><span class="bookHeadTools"><small>${chList.length} thẻ · ${chQ} câu</small>${catalogCollapseBtnHtml('chapter',chKey,chCollapsed,'chương')}${chAdminBtn}</span></div><div class="bookLessonList">`;let byBai=v246GroupBy(chList,x=>x.BaiHoc||x.De||'Chưa rõ bài');
        if(!chCollapsed)for(let [bai,baiList] of byBai){html+=v246LessonCard(mon,khoi,chuong,bai,baiList)}
        html+='</div></div>';
      }
      html+='</div></div>';
    }
    html+='</section>';
  }
  html+='</div>';return html;
}
function v246IntroHtml(list){let qs=list.reduce((a,x)=>a+(parseInt(x.SoCau,10)||0),0);let mons=uniqField(list,'Mon').length;let khois=new Set(list.map(x=>deriveKhoi(x.Lop)).filter(Boolean)).size;let chuongs=uniqField(list,'Chuong').length;let bais=uniqField(list,'BaiHoc').length;let dbt=uniqField(list,'DangBaiTap').length;let scope=[val('fMon')||'Tất cả môn',window.CATALOG_SELECTED_KHOI?('Khối '+window.CATALOG_SELECTED_KHOI):'',val('fChuong')||'',val('fBaiHoc')||''].filter(Boolean).join(' · ');
  return `<div class="bookIntroV246"><div class="bookIntroTitle">📚 Mục lục kiểu sách ${scope?`<span class="tag">${esc(scope)}</span>`:''}</div><div class="muted" style="font-size:13px;line-height:1.45">Trong từng tab, app gom đề theo <b>Môn → Khối/Lớp → Chương → Bài</b>. Có thể lọc tiếp theo <b>Lớp, Chương, Bài, Mức độ, Loại câu hỏi, Dạng bài tập</b>.</div><div class="bookIntroStats"><span class="bookStat">${mons} môn</span><span class="bookStat">${khois} khối</span><span class="bookStat">${chuongs} chương</span><span class="bookStat">${bais} bài</span><span class="bookStat">${dbt} dạng BT</span><span class="bookStat">${qs} câu</span></div></div>`;
}
function renderCatalog(){
  ensureChapterDbtClickBindings();
  v256EnsureCatalogCollapseCss();
  v246EnsureDangBaiTapFilter();
  v245RenderCatalogScopeTabs();
  let list=(CATALOG||[]).filter(v246ItemMatchesFilter).sort(compareCatalog);let c=document.getElementById('countCat');if(c)c.textContent=`(${list.length} mục)`;let target=document.getElementById('catalog');if(!target)return;
  target.className='';
  target.style.marginTop='10px';
  let emptyMsg='<div class="card loadWarn" style="margin-top:10px"><h3>Chưa có mục lục đề</h3><p>Đang nạp ngân hàng LaTeX từ thư mục <code>ngan-hang</code> rồi mới kéo GitHub nền. Nếu máy đã có file .tex mà vẫn trống, bấm <b>Ctrl+F5</b>.</p>'+(META&&META.load_error?('<p class="muted">Lỗi: '+esc(String(META.load_error))+'</p>'):'')+'<p class="muted">Đổi môn Toán / Vật lý trên thanh trên, hoặc menu <b>Đồng bộ</b> → tải GitHub .tex.</p></div>';
  target.innerHTML=v246IntroHtml(list)+(list.length?v246BookHtml(list):emptyMsg);
  try{typeset()}catch(e){}
}



/* ===== V248 FIXLOAD: 2 trang riêng Toán / Vật lí, giữ lõi V246 ổn định ===== */
function v248EnsureSubjectPageCss(){
  if(document.getElementById('LDVL_TWO_SUBJECT_PAGES_V248'))return;
  let st=document.createElement('style');st.id='LDVL_TWO_SUBJECT_PAGES_V248';
  st.textContent=`
  .subjectPagesV248{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:2px 0 10px}
  .subjectPageBtnV248{border:2px solid #bfdbfe;background:#fff;color:#1e40af;border-radius:16px;padding:10px 12px;font-weight:950;font-size:16px;cursor:pointer;box-shadow:0 1px 4px #1d4ed811;text-align:center;min-height:56px}
  .subjectPageBtnV248.active{background:linear-gradient(90deg,#1d4ed8,#2563eb);color:#fff;border-color:#1d4ed8;box-shadow:0 4px 12px #1d4ed833;transform:translateY(-1px)}
  .subjectPageBtnV248.math.active{background:linear-gradient(90deg,#7c3aed,#2563eb);border-color:#7c3aed}
  .subjectPageBtnV248.physics.active{background:linear-gradient(90deg,#0f766e,#2563eb);border-color:#0f766e}
  .subjectPageSubV248{font-size:11px;opacity:.9;font-weight:800;margin-top:2px}.subjectPageTitleV248{font-weight:950;color:#1e3a8a;margin-bottom:8px}.catalogScopeBox.subjectV248{border:1px solid #bfdbfe!important;background:linear-gradient(180deg,#eff6ff,#fff)!important;border-radius:18px!important;padding:12px!important}
  @media(max-width:760px){.subjectPagesV248{gap:6px}.subjectPageBtnV248{font-size:14px;padding:8px 6px;border-radius:13px;min-height:50px}.catalogScopeBox.subjectV248{padding:9px!important}.subjectPageTitleV248{font-size:13px}.catalogScopeRow{gap:5px}.catalogChip{font-size:11px;padding:5px 7px}}
  html[data-theme='dark'] .subjectPageBtnV248{background:#111827;color:#bfdbfe;border-color:#334155}html[data-theme='dark'] .subjectPageTitleV248{color:#bfdbfe}html[data-theme='dark'] .catalogScopeBox.subjectV248{background:linear-gradient(180deg,#172554,#0f172a)!important;border-color:#1d4ed8!important}
  `;
  document.head.appendChild(st);
}
function v248SubjectKind(mon){let k=normText(mon||''); if(k.includes('toan')||k.includes('math'))return 'math'; if(k.includes('vat li')||k.includes('vat ly')||k.includes('physics')||k==='ly')return 'physics'; return 'other'}
function v248SubjectLabel(mon){let kind=v248SubjectKind(mon); if(kind==='math')return '📐 Toán'; if(kind==='physics')return '⚛️ Vật lí'; return '📘 '+(mon||'Môn khác')}
function v248Subjects(){let arr=uniqField(CATALOG||[],'Mon').filter(Boolean);if(!arr.length&&META&&META.filters&&META.filters.Mon)arr=(META.filters.Mon||[]).filter(Boolean);arr.sort((a,b)=>{let ka=v248SubjectKind(a),kb=v248SubjectKind(b);let pa=ka==='math'?0:ka==='physics'?1:2;let pb=kb==='math'?0:kb==='physics'?1:2;if(pa!==pb)return pa-pb;return normText(a).localeCompare(normText(b),'vi')});return arr}
function v248DefaultSubject(){let s=v248Subjects();let saved='';try{saved=localStorage.getItem('LDVL_SUBJECT_PAGE_V248')||localStorage.getItem('LDVL_SUBJECT_PAGE_V247')||''}catch(e){};if(saved&&s.includes(saved))return saved;let math=s.find(x=>v248SubjectKind(x)==='math');if(math)return math;let phys=s.find(x=>v248SubjectKind(x)==='physics');if(phys)return phys;return s[0]||''}
function v248EnsureSubject(){let subjects=v248Subjects();let cur=val('fMon')||'';if(!cur||!subjects.includes(cur)){let d=v248DefaultSubject();if(d)setVal('fMon',d)}try{if(val('fMon'))localStorage.setItem('LDVL_SUBJECT_PAGE_V248',val('fMon'))}catch(e){};return val('fMon')||''}
function v248ClearSubjectFilters(){window.CATALOG_SELECTED_KHOI='';setVal('fLop','');setVal('fChuong','');setVal('fBaiHoc','');setVal('fDangBaiTap','');setVal('fBoDe','');setVal('fMucDo','');setVal('fDang','');setVal('fSearch','')}
function v248SelectSubject(mon){
  // V249: đổi Trang Toán/Vật lí thật sự, không bị refreshFilterOptions kéo về Trang Toán.
  mon=String(mon||'').trim();
  try{localStorage.setItem('LDVL_SUBJECT_PAGE_V248',mon)}catch(e){}
  // Xóa bộ lọc con trước, rồi mới đặt lại fMon để tránh reset nhầm.
  window.CATALOG_SELECTED_KHOI='';
  setVal('fLop','');
  setVal('fChuong','');
  setVal('fBaiHoc','');
  setVal('fDangBaiTap','');
  setVal('fBoDe','');
  setVal('fMucDo','');
  setVal('fDang','');
  setVal('fSearch','');
  setVal('fMon',mon);
  refreshFilterOptions();
  setVal('fMon',mon); // khóa lại môn sau khi dropdown được nạp lại
  try{localStorage.setItem('LDVL_SUBJECT_PAGE_V248',mon)}catch(e){}
  renderCatalog();
  try{syncRpFromMainFilters&&syncRpFromMainFilters()}catch(e){}
}
var V248_ORIG_REFRESH_FILTER_OPTIONS = refreshFilterOptions;
refreshFilterOptions = function(){v248EnsureSubject();V248_ORIG_REFRESH_FILTER_OPTIONS();v248EnsureSubject();v245RenderCatalogScopeTabs();};
v245SelectMon = function(v){v248SelectSubject(v)};
var V248_ORIG_RENDER_CATALOG = renderCatalog;
renderCatalog = function(){v248EnsureSubject();V248_ORIG_RENDER_CATALOG();};
// V249: bắt click bằng delegation phòng trường hợp inline onclick bị PWA/cache chặn.
document.addEventListener('click',function(ev){
  let btn=ev.target&&ev.target.closest?ev.target.closest('[data-subject-v249]'):null;
  if(!btn)return;
  ev.preventDefault();
  v248SelectSubject(btn.getAttribute('data-subject-v249')||'');
});



/* ===== V250: chỉ giữ 2 tab môn lớn; bỏ dải Khối/Chương/Bài phía trên vì đã có bộ lọc bên dưới ===== */
function v250RenderSubjectOnlyTabs(){
  v248EnsureSubjectPageCss();
  v245EnsureCatalogScopeBox();
  let box=document.getElementById('catalogScopeBox'); if(!box)return;
  box.classList.add('subjectV248');
  let curMon=v248EnsureSubject();
  let subjects=v248Subjects();
  let tabs=subjects.map(m=>{
    let kind=v248SubjectKind(m);
    let active=m===curMon?' active':'';
    let count=(CATALOG||[]).filter(x=>x.Mon===m).length;
    let qs=(CATALOG||[]).filter(x=>x.Mon===m).reduce((a,x)=>a+(parseInt(x.SoCau,10)||0),0);
    return `<button type="button" class="subjectPageBtnV248 ${kind}${active}" data-subject-v249="${escAttr(m)}" onclick="v248SelectSubject(${JSON.stringify(m)})"><div>${esc(v248SubjectLabel(m))}</div><div class="subjectPageSubV248">${count} mục · ${qs} câu</div></button>`;
  }).join('');
  box.innerHTML=`<div class="subjectPagesV248">${tabs}</div><div class="catalogAdvancedHint">Chọn <b>Trang Toán</b> hoặc <b>Trang Vật lí</b>. Lọc chi tiết bằng các ô bên dưới: Lớp, Chương, Bài học, Mức độ, Loại câu hỏi, Dạng bài tập, Bộ đề, Tìm nhanh.</div>`;
}
v245RenderCatalogScopeTabs = v250RenderSubjectOnlyTabs;



/* ===== V255: ép nút Toán/Vật lí trên thanh xanh đổi đúng Môn =====
   Lỗi cũ: V248 giữ localStorage LDVL_SUBJECT_PAGE_V248 nên nút trên thanh xanh bị kéo lại môn cũ.
   Cách sửa: nút trên thanh xanh gọi thẳng v248SelectSubject(mon) và cập nhật cả fMon + rpMon. */
function v255SubjectNorm(s){
  try{return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/\s+/g,' ').trim()}catch(e){return String(s||'').toLowerCase().trim()}
}
function v255KindOfSubject(s){
  let n=v255SubjectNorm(s);
  if(n.includes('toan')||n.includes('math'))return 'math';
  if(n.includes('vat li')||n.includes('vat ly')||n.includes('vatli')||n.includes('vatly')||n==='ly'||n.includes('physics'))return 'physics';
  return '';
}
function v255FindSubjectByKind(kind){
  let arr=[];
  try{let sel=document.getElementById('fMon'); if(sel){for(let o of sel.options){let v=String(o.value||'').trim(); if(v)arr.push(v);}}}catch(e){}
  try{for(let x of (CATALOG||[])){let v=String((x&&x.Mon)||'').trim(); if(v&&!arr.some(a=>v255SubjectNorm(a)===v255SubjectNorm(v)))arr.push(v);}}catch(e){}
  for(let v of arr){ if(v255KindOfSubject(v)===kind)return v; }
  return kind==='math'?'Toán':(kind==='physics'?'Vật lí':'');
}
function v255SetSelectByText(id, text){
  let el=document.getElementById(id); if(!el)return false;
  let target=v255SubjectNorm(text); let found='';
  for(let o of el.options){
    if(v255SubjectNorm(o.value)===target || v255SubjectNorm(o.textContent)===target || v255KindOfSubject(o.value)===v255KindOfSubject(text)) {found=o.value;break;}
  }
  el.value=found || text || '';
  try{el.dispatchEvent(new Event('change',{bubbles:true}))}catch(e){}
  return !!found;
}
function v255SelectTopSubject(kind){
  let mon=v255FindSubjectByKind(kind);
  if(!mon){try{localStorage.setItem('LDVL_PENDING_SUBJECT_V255',kind)}catch(e){};return false;}
  try{
    localStorage.setItem('LDVL_TOP_SUBJECT_V255',kind);
    localStorage.setItem('LDVL_TOP_SUBJECT_V254',kind);
    localStorage.setItem('LDVL_TOP_SUBJECT_V253',kind);
    localStorage.setItem('LDVL_SUBJECT_PAGE_V248',mon); // khóa lõi V248 không kéo lại Toán
  }catch(e){}
  function applyNow(){
    try{window.CATALOG_SELECTED_KHOI=''}catch(e){}
    ['fLop','fChuong','fBaiHoc','fBoDe','fDangBaiTap','fMucDo','fDang','fSearch'].forEach(id=>{let el=document.getElementById(id); if(el)el.value='';});
    v255SetSelectByText('fMon',mon);
    try{ if(typeof v248SelectSubject==='function') v248SelectSubject(mon); else { if(typeof refreshFilterOptions==='function')refreshFilterOptions(); v255SetSelectByText('fMon',mon); if(typeof renderCatalog==='function')renderCatalog(); } }catch(e){try{v255SetSelectByText('fMon',mon); if(typeof renderCatalog==='function')renderCatalog();}catch(_){}}
    try{v255SetSelectByText('rpMon',mon); if(typeof onRpScopeChange==='function')onRpScopeChange('mon');}catch(e){}
    v255SyncTopSubject();
  }
  let quiz=document.getElementById('quiz');
  let inQuiz=quiz&&!quiz.classList.contains('hide');
  if(inQuiz&&typeof backHome==='function'){backHome();setTimeout(applyNow,160);} else applyNow();
  return false;
}
// Ghi đè hàm cũ để inline onclick hiện tại vẫn chạy đúng.
function v253SelectSubject(kind){return v255SelectTopSubject(kind)}
function v254ApplySubject(kind){return v255SelectTopSubject(kind)}
function v255SyncTopSubject(){
  try{
    let cur=(document.getElementById('fMon')&&document.getElementById('fMon').value)||'';
    let kind=v255KindOfSubject(cur);
    if(!kind){try{kind=localStorage.getItem('LDVL_TOP_SUBJECT_V255')||localStorage.getItem('LDVL_TOP_SUBJECT_V254')||localStorage.getItem('LDVL_TOP_SUBJECT_V253')||''}catch(e){}}
    let bm=document.getElementById('topSubjectMathV253'),bp=document.getElementById('topSubjectPhysicsV253');
    if(bm)bm.classList.toggle('active',kind==='math');
    if(bp)bp.classList.toggle('active',kind==='physics');
  }catch(e){}
}
document.addEventListener('click',function(ev){
  let btn=ev.target&&ev.target.closest?ev.target.closest('#topSubjectMathV253,#topSubjectPhysicsV253'):null;
  if(!btn)return;
  ev.preventDefault(); ev.stopPropagation();
  v255SelectTopSubject(btn.id==='topSubjectMathV253'?'math':'physics');
},true);
(function(){
  let oldRender=window.renderCatalog;
  if(typeof oldRender==='function')window.renderCatalog=function(){let r=oldRender.apply(this,arguments);setTimeout(v255SyncTopSubject,0);return r};
  document.addEventListener('DOMContentLoaded',function(){v253SetSubjectTabsVisible(true);setTimeout(v255SyncTopSubject,300);setTimeout(v255SyncTopSubject,1300)});
  setTimeout(function(){v255SyncTopSubject();let p='';try{p=localStorage.getItem('LDVL_PENDING_SUBJECT_V255')||''}catch(e){};if(p&&document.getElementById('fMon')){try{localStorage.removeItem('LDVL_PENDING_SUBJECT_V255')}catch(e){};v255SelectTopSubject(p)}},1200);
})();

/* ===== V233 PWA: cài app lên điện thoại ===== */
let PWA_DEFERRED_PROMPT=null;
function isStandalonePwa(){try{return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone===true}catch(e){return false}}
function showPwaInstallBtn(show){let b=document.getElementById('pwaInstallBtn');if(!b)return;if(show && !isStandalonePwa())b.classList.add('show');else b.classList.remove('show')}
window.addEventListener('beforeinstallprompt',function(e){try{e.preventDefault();PWA_DEFERRED_PROMPT=e;showPwaInstallBtn(true)}catch(err){}});
window.addEventListener('appinstalled',function(){PWA_DEFERRED_PROMPT=null;showPwaInstallBtn(false);try{localStorage.setItem('LDVL_PWA_INSTALLED','1')}catch(e){}});
async function installPwaApp(){
  try{
    if(PWA_DEFERRED_PROMPT){
      PWA_DEFERRED_PROMPT.prompt();
      await PWA_DEFERRED_PROMPT.userChoice;
      PWA_DEFERRED_PROMPT=null;
      showPwaInstallBtn(false);
      return;
    }
    alert('Nếu nút cài chưa hiện: trên Android mở Chrome → dấu 3 chấm → Thêm vào màn hình chính. Trên iPhone mở Safari → Chia sẻ → Thêm vào Màn hình chính.');
  }catch(e){alert('Mở menu trình duyệt → Thêm vào màn hình chính để cài app.');}
}
(function initPwa(){
  try{
    if('serviceWorker' in navigator){
      window.addEventListener('load',function(){
        navigator.serviceWorker.register('/service-worker.js?v='+encodeURIComponent(String(window.__LDVL_V||''))).then(function(reg){
          if(reg&&reg.waiting)reg.waiting.postMessage({type:'SKIP_WAITING'});
          reg&&reg.update&&reg.update();
        }).catch(function(){});
      });
    }
    showPwaInstallBtn(false);
  }catch(e){}
})();


/* ===== V264: Bảng câu hỏi nhóm theo DẠNG - không setInterval, không MutationObserver ===== */
(function(){
  function stripLevelFromSectionTextV264(txt){
    txt=String(txt||'').replace(/^[\s📂🌱💡🔥🚀▫️]+/g,'').trim();
    txt=txt.replace(/\s*[·\-–—|]\s*(mức|muc)\s*(NB|TH|VD|VDC)\b.*$/i,'').trim();
    txt=txt.replace(/\s*\((mức|muc)\s*(NB|TH|VD|VDC)\).*$/i,'').trim();
    return txt || 'Dạng câu';
  }
  function keyV264(t){
    return String(t||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/\s+/g,' ').trim();
  }
  function normalizeNavSectionsByDangOnlyV264(){
    try{
      const box=document.getElementById('navNums');
      if(!box)return;
      const labels=Array.from(box.querySelectorAll('.navSectionLbl'));
      if(!labels.length)return;
      const seen={};
      labels.forEach(lb=>{
        const base=stripLevelFromSectionTextV264(lb.textContent||'');
        const k=keyV264(base);
        lb.classList.remove('navSection-nb','navSection-th','navSection-vd','navSection-vdc');
        if(seen[k]){
          lb.style.display='none';
          lb.dataset.v264Hidden='1';
        }else{
          seen[k]=true;
          lb.style.display='';
          if((lb.textContent||'')!==base) lb.textContent=base;
          lb.dataset.v264DangOnly='1';
        }
      });
    }catch(e){}
  }
  window.normalizeNavSectionsByDangOnlyV260=normalizeNavSectionsByDangOnlyV264;
  window.normalizeNavSectionsByDangOnlyV264=normalizeNavSectionsByDangOnlyV264;

  function runV264(){ setTimeout(normalizeNavSectionsByDangOnlyV264,0); }

  document.addEventListener('DOMContentLoaded',function(){
    runV264();
    setTimeout(normalizeNavSectionsByDangOnlyV264,700);
  });

  ['renderQuestion','renderNav','renderNavNums','updateNav'].forEach(function(fn){
    try{
      const old=window[fn];
      if(typeof old==='function' && !old.__v264Wrapped){
        const wrap=function(){
          const r=old.apply(this,arguments);
          runV264();
          return r;
        };
        wrap.__v264Wrapped=true;
        window[fn]=wrap;
      }
    }catch(e){}
  });
})();



/* ===== V303: Khung lý thuyết theo DangBaiTap ===== */
let DANG_THEORY_CACHE={},DANG_SIMILARITY_CACHE={},DANG_SIMILARITY_LOADING=false;
let DANG_THEORY_LOADING={},BAI_THEORY_LOADING={};
function ensureTheoryHosts(){
  let qtext=document.getElementById('qtext');if(!qtext||!qtext.parentNode)return {bai:null,dang:null};
  let parent=qtext.parentNode,bai=document.getElementById('baiTheoryHost');
  if(!bai){bai=document.createElement('div');bai.id='baiTheoryHost';bai.className='dangTheoryHost hide';parent.insertBefore(bai,qtext)}
  let dang=document.getElementById('dangTheoryHost');
  if(!dang){dang=document.createElement('div');dang.id='dangTheoryHost';dang.className='dangTheoryHost hide';parent.insertBefore(dang,qtext)}
  return {bai,dang};
}
function ensureDangTheoryHost(){return ensureTheoryHosts().dang}
function theoryCardAdminBarHtml(kind){
  if(!USER||!USER.is_admin)return '';
  let openFn=kind==='theory'?'openTheoryLearningEditor(event)':'openDangTheoryEditor(event)';
  let delFn=kind==='theory'?'deleteBaiTheoryFromSheet(event)':'deleteDangTheoryFromSheet(event)';
  return '<span class="theoryCardAdminBar" onclick="event.stopPropagation()"><button type="button" class="btn2 theoryCardAdminBtn" title="Soạn / sửa khung" onclick="'+openFn+';return false;">✏️ Sửa</button><button type="button" class="btn2 theoryCardAdminBtn theoryCardDelBtn" title="Xóa khỏi Google Sheet" onclick="'+delFn+';return false;">🗑 Xóa</button></span>';
}
function buildInlineTheoryCardHtml(cardId,label,body,isOpen,adminKind){
  if(!body)return '';
  let adminBar=adminKind?theoryCardAdminBarHtml(adminKind):'';
  return '<div id="'+escAttr(cardId)+'" class="dangTheoryCard'+(isOpen?' isOpen':'')+'"><div class="dangTheorySummaryRow"><button type="button" class="dangTheorySummary" onclick="toggleInlineTheoryCard(\''+escAttr(cardId)+'\')"><span class="dangTheorySummaryText">'+esc(label)+'</span><span class="dangTheoryChevron">▼</span></button>'+adminBar+'</div><div class="dangTheoryBody">'+body+'</div></div>';
}
function baiTheoryCardOpenKey(q){return 'LDVL_BAI_THEORY_OPEN|'+theoryLearningKey(q)}
function getBaiTheoryCardOpen(q){
  try{let v=localStorage.getItem(baiTheoryCardOpenKey(q));if(v!==null)return v==='1'}catch(e){}
  if(window.matchMedia&&window.matchMedia('(max-width:760px)').matches)return false;
  let prev=CUR>0?(QUESTIONS[CUR-1]||{}):null;return !prev||theoryLearningKey(prev)!==theoryLearningKey(q);
}
function setBaiTheoryCardOpen(open){let q=QUESTIONS[CUR]||{};try{localStorage.setItem(baiTheoryCardOpenKey(q),open?'1':'0')}catch(e){}let card=document.getElementById('baiTheoryCard');if(card)card.classList.toggle('isOpen',!!open)}
function theoryCardOpenKey(q){return 'LDVL_THEORY_OPEN|'+dangTheoryKey(q)}
function getTheoryCardOpen(q){
  try{let v=localStorage.getItem(theoryCardOpenKey(q));if(v!==null)return v==='1'}catch(e){}
  if(window.matchMedia&&window.matchMedia('(max-width:760px)').matches)return false;
  let prev=CUR>0?(QUESTIONS[CUR-1]||{}):null;return !prev||dangTheoryKey(prev)!==dangTheoryKey(q);
}
function setTheoryCardOpen(open){let q=QUESTIONS[CUR]||{};try{localStorage.setItem(theoryCardOpenKey(q),open?'1':'0')}catch(e){}let card=document.getElementById('dangTheoryCard');if(card)card.classList.toggle('isOpen',!!open)}
function toggleInlineTheoryCard(cardId){
  let card=document.getElementById(cardId);if(!card)return;
  let open=!card.classList.contains('isOpen');
  if(cardId==='baiTheoryCard')setBaiTheoryCardOpen(open);else if(cardId==='dangTheoryCard')setTheoryCardOpen(open);
  card.classList.toggle('isOpen',open);if(open)typesetTheoryMath();
}
function toggleDangTheoryCard(){toggleInlineTheoryCard('dangTheoryCard')}
function hideLessonTheoryHosts(){let hosts=ensureTheoryHosts();['bai','dang'].forEach(k=>{let h=hosts[k];if(h){h.classList.add('hide');h.innerHTML=''}})}
function hideDangTheoryHost(){let h=document.getElementById('dangTheoryHost');if(h){h.classList.add('hide');h.innerHTML=''}}
function afterBaiTheoryPrefetch(q,jOrCached){
  let key=theoryLearningKey(q),cacheKey=learningCacheKey('theory',q),hosts=ensureTheoryHosts(),host=hosts.bai;
  if(!host)return;
  let items=(jOrCached&&jOrCached.items)||(LEARNING_CACHE[cacheKey]&&LEARNING_CACHE[cacheKey].items)||[];
  if(jOrCached&&jOrCached.items)LEARNING_CACHE[cacheKey]={items:jOrCached.items||[],meta:jOrCached};
  if(theoryLearningKey(QUESTIONS[CUR]||{})!==key)return;
  let body=theoryLearningLatexHtml(q,items);
  if(!body){host.classList.add('hide');host.innerHTML='';return}
  let label='📚 Lý thuyết bài: '+String(q.BaiHoc||q.Chuong||'Bài học').trim();
  host.innerHTML=buildInlineTheoryCardHtml('baiTheoryCard',label,body,getBaiTheoryCardOpen(q),'theory');
  host.classList.remove('hide');
  typesetTheoryMath().catch(()=>{});
}
function afterDangTheoryPrefetch(q,entry,j){
  let key=dangTheoryKey(q),cacheKey=learningCacheKey('method',q);
  if(j){LEARNING_CACHE[cacheKey]={items:j.items||[],meta:j};if(j.similarity_report)DANG_SIMILARITY_CACHE[dangSimilarityCacheKey(q)]=j.similarity_report}
  if(LEARNING_OPEN_KIND==='method'&&dangTheoryKey(QUESTIONS[CUR]||{})===key){
    renderLearningPanel('method',(j&&j.items)||(LEARNING_CACHE[cacheKey]&&LEARNING_CACHE[cacheKey].items)||[],(j||(LEARNING_CACHE[cacheKey]&&LEARNING_CACHE[cacheKey].meta)||{}));
  }
  let host=ensureTheoryHosts().dang;if(!host||dangTheoryKey(QUESTIONS[CUR]||{})!==key)return;
  let body=methodLearningLatexHtml(q,entry||DANG_THEORY_CACHE[key]||{item:exactDangTheoryItem((j&&j.items)||[],q)});
  if(!body){host.classList.add('hide');host.innerHTML='';return}
  let label='📘 Khung dạng: '+String(q.DangBaiTap||'').trim();
  host.innerHTML=buildInlineTheoryCardHtml('dangTheoryCard',label,body,getTheoryCardOpen(q),'method');
  host.classList.remove('hide');
  typesetTheoryMath().catch(()=>{});
}
async function syncBaiTheoryCard(force){
  let hosts=ensureTheoryHosts(),host=hosts.bai,q=QUESTIONS[CUR]||{};if(!host)return;
  if(!String(q.BaiHoc||'').trim()){host.classList.add('hide');host.innerHTML='';return}
  let key=theoryLearningKey(q),cacheKey=learningCacheKey('theory',q);
  if(!force&&LEARNING_CACHE[cacheKey]){afterBaiTheoryPrefetch(q,LEARNING_CACHE[cacheKey]);return}
  if(BAI_THEORY_LOADING[key])return;BAI_THEORY_LOADING[key]=true;
  try{
    let body={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||''};
    let j=await api('/api/learning/theory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(theoryLearningKey(QUESTIONS[CUR]||{})===key)afterBaiTheoryPrefetch(q,j);
  }catch(e){if(host)host.classList.add('hide')}finally{delete BAI_THEORY_LOADING[key]}
}
async function syncDangTheoryCard(force){
  let host=ensureTheoryHosts().dang,q=QUESTIONS[CUR]||{};if(!host)return;
  if(!String(q.DangBaiTap||'').trim()){host.classList.add('hide');host.innerHTML='';return}
  let key=dangTheoryKey(q);
  if(!force&&DANG_THEORY_CACHE[key]){afterDangTheoryPrefetch(q,DANG_THEORY_CACHE[key]);return}
  if(DANG_THEORY_LOADING[key])return;DANG_THEORY_LOADING[key]=true;
  try{
    let body={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',DangBaiTap:q.DangBaiTap||''};
    let j=await api('/api/learning/method',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    let entry={item:exactDangTheoryItem(j.items||[],q),meta:j};DANG_THEORY_CACHE[key]=entry;
    if(dangTheoryKey(QUESTIONS[CUR]||{})===key)afterDangTheoryPrefetch(QUESTIONS[CUR]||{},entry,j);
  }catch(e){hideDangTheoryHost()}finally{delete DANG_THEORY_LOADING[key]}
}
async function syncLessonTheoryCards(force){hideDangTheoryHost();let b=document.getElementById('baiTheoryHost');if(b){b.classList.add('hide');b.innerHTML=''}}
let THEORY_EDITOR_ITEM=null;
let THEORY_EDITOR_Q=null;
let THEORY_EDITOR_KIND='method';
let THEORY_EDITOR_DIRTY=false;
let THEORY_EDITOR_DRAFT_TIMER=null;
let THEORY_EDITOR_TAB='edit';

function syncTheoryViewportHeight(){
  try{
    let h=window.visualViewport?window.visualViewport.height:window.innerHeight;
    document.documentElement.style.setProperty('--app-vh',Math.max(260,Math.round(h))+'px');
  }catch(e){}
}
syncTheoryViewportHeight();
window.addEventListener('resize',syncTheoryViewportHeight);
if(window.visualViewport){window.visualViewport.addEventListener('resize',syncTheoryViewportHeight);window.visualViewport.addEventListener('scroll',syncTheoryViewportHeight)}

function normalizeTheoryLatexSourceClient(src){
  let t=String(src||'').replace(/\r\n?/g,'\n');
  t=t.replace(/\\begin\s*\{\s*node\s*\}/gi,'\\begin{note}')
     .replace(/\\end\s*\{\s*node\s*\}/gi,'\\end{note}')
     .replace(/\\begin\s*\{\s*kttrongtam\s*\}/gi,'\\begin{dn}')
     .replace(/\\end\s*\{\s*kttrongtam\s*\}/gi,'\\end{dn}')
     .replace(/\\begin\s*\{\s*vd\s*\}/gi,'\\begin{vidu}')
     .replace(/\\end\s*\{\s*vd\s*\}/gi,'\\end{vidu}')
     .replace(/\\begin\s*\{\s*dinhnghia\s*\}/gi,'\\begin{dn}')
     .replace(/\\end\s*\{\s*dinhnghia\s*\}/gi,'\\end{dn}');
  return t.replace(/[ \t]+\n/g,'\n').replace(/\n{4,}/g,'\n\n\n').trim();
}
function foldLoigiaiClient(s){
  s=String(s||'');let out='',i=0,n=s.length;
  while(i<n){
    let rest=s.slice(i),m=rest.match(/\\loigiai\b/i);
    if(!m){out+=s.slice(i);break}
    let idx=i+m.index;
    out+=s.slice(i,idx);
    let bracePos=idx+m[0].length;
    while(bracePos<n&&/\s/.test(s[bracePos]))bracePos++;
    let got=readLatexBracedContent(s,bracePos);
    if(!got){out+=s.slice(idx,bracePos);i=bracePos;continue}
    out+='\n\n@@B@@Lời giải:@@/B@@\n'+got.content;
    i=got.end+1;
  }
  return out;
}
function preprocessTheoryBody(s){
  s=String(s||'').trim();
  s=s.replace(/^\s*%\[[^\]]*\]\s*/gm,'');
  s=s.replace(/%\[[0-9A-Za-z]+[^\]]*\]/g,'');
  s=foldLoigiaiClient(s);
  s=s.replace(/\\begin\s*\{\s*(center|figure|minipage)\s*\}/gi,'');
  s=s.replace(/\\end\s*\{\s*(center|figure|minipage)\s*\}/gi,'');
  s=applyFmtOutsideMath(s,function(seg){
    seg=seg.replace(/\\hfill\b/g,'');
    seg=seg.replace(/\\lq\s*\\lq/gi,'«').replace(/\\rq\s*\\rq/gi,'»');
    seg=seg.replace(/\\lq\b/gi,'«').replace(/\\rq\b/gi,'»');
    seg=seg.replace(/\\,/g,' ');
    seg=seg.replace(/\{,\}/g,',');
    seg=seg.replace(/\\indam\s*\{/gi,'\\textbf{');
    seg=seg.replace(/\\\\\s*/g,'\n');
    return seg;
  });
  return s;
}
function theoryRenderTextChunk(t){
  t=String(t||'');
  t=t.replace(/\\begin\s*\{\s*(enumerate|itemize)\s*\}(?:\[[^\]]*\])?/gi,'')
     .replace(/\\end\s*\{\s*(enumerate|itemize)\s*\}/gi,'')
     .replace(/\\item\s*/gi,'\n• ');
  if(!t.trim())return '';
  if(typeof renderRichText==='function')return renderRichText(t);
  if(typeof formatHintDisplay==='function')return formatHintDisplay(t);
  return esc(t).replace(/\n/g,'<br>');
}
function theoryDisplayText(s){
  let split=theorySplitTikzSegments(preprocessTheoryBody(s)),html='';
  for(let seg of split.segs){
    if(seg.type==='text'){html+=theoryRenderTextChunk(seg.content);continue}
    let tz=normalizeTikzBlockForRender(split.blocks[seg.idx]||'');
    if(!tz)continue;
    let id='theoryTikz_'+seg.uid;
    let enc=encodeTikzRawClient(tz);
    html+=`<div class="theoryTikzSlot qimgWrap tikzRawWrap" id="${escAttr(id)}"><div class="muted" style="font-size:12px;padding:12px;text-align:center">⏳ Đang vẽ biểu đồ…</div></div>`;
    setTimeout(()=>renderTikzRawToImg(enc,id),0);
  }
  return html;
}
function parseTheoryLatexBlocks(src){
  let t=normalizeTheoryLatexSourceClient(src),out=[];
  let re=/\\begin\s*\{\s*(dn|note|vidu)\s*\}(?:\s*\[([^\]]*)\])?([\s\S]*?)\\end\s*\{\s*\1\s*\}/gi,m;
  while((m=re.exec(t))){out.push({type:String(m[1]||'note').toLowerCase(),customTitle:String(m[2]||'').trim(),content:String(m[3]||'').trim()})}
  if(!out.length&&t)out.push({type:'note',customTitle:'Nội dung',content:t});
  return out;
}
function renderTheoryLatexBlocks(src){
  let blocks=parseTheoryLatexBlocks(src);
  if(!blocks.length)return '<div class="muted" style="padding:8px">Chưa có nội dung.</div>';
  let meta={dn:['📘','Định nghĩa · Kiến thức cốt lõi'],kttrongtam:['📘','Kiến thức trọng tâm'],note:['⭐','Ghi nhớ · Phương pháp · Lưu ý'],vidu:['🧩','Ví dụ mẫu']};
  return blocks.map(b=>{let typ=b.type==='kttrongtam'?'dn':b.type;let x=meta[b.type]||meta[typ]||meta.note;let title=b.customTitle||x[1];return '<section class="theoryEnvCard theoryEnv-'+escAttr(typ)+'"><div class="theoryEnvTitle"><span>'+x[0]+'</span><span>'+esc(title)+'</span></div><div class="theoryEnvContent hintMath">'+theoryDisplayText(b.content)+'</div></section>'}).join('');
}
function theorySourceFromLegacyItem(it){
  it=it||{};let p=[];
  let dn=[it.DauHieuNhanBiet,it.CongThucSuDung].filter(Boolean).join('\n\n');
  let note=[it.CacBuocGiai,it.MeoNhanh,it.LoiSaiThuongGap].filter(Boolean).join('\n\n');
  if(dn)p.push('\\begin{dn}\n'+dn+'\n\\end{dn}');
  if(note)p.push('\\begin{note}\n'+note+'\n\\end{note}');
  if(it.ViDuMau)p.push('\\begin{vidu}\n'+it.ViDuMau+'\n\\end{vidu}');
  return p.join('\n\n');
}
function theorySourceFromLegacyTheoryItem(it){
  it=it||{};let p=[];
  let dn=[it.LyThuyet,it.KienThucTrongTam,it.CongThuc,it.DonVi].filter(Boolean).join('\n\n');
  let note=[it.NoiDungTomTat,it.LuuY,it.SaiLamThuongGap].filter(Boolean).join('\n\n');
  if(dn)p.push('\\begin{dn}\n'+dn+'\n\\end{dn}');
  if(note)p.push('\\begin{note}\n'+note+'\n\\end{note}');
  if(it.ViDuMau)p.push('\\begin{vidu}\n'+it.ViDuMau+'\n\\end{vidu}');
  return p.join('\n\n');
}
function theoryLearningKey(q){q=q||{};return [q.Mon,q.Lop,q.Chuong,q.BaiHoc].map(x=>normText(String(x||''))).join('|')}
function theoryLearningDraftKey(q){return 'LDVL_THEORY_LATEX_DRAFT|'+theoryLearningKey(q)}
function exactTheoryLearningItem(items,q){items=items||[];if(!items.length)return null;let withLatex=items.find(x=>String(x.NoiDungLaTeX||'').trim());return withLatex||items[0]}
function dangTheoryKey(q){q=q||{};return [q.Mon,q.Lop,q.Chuong,q.BaiHoc,q.DangBaiTap].map(x=>normText(String(x||''))).join('|')}
function dangTheoryDraftKey(q){return 'LDVL_DANG_THEORY_DRAFT|'+dangTheoryKey(q)}
function exactDangTheoryItem(items,q){let target=normText((q&&q.DangBaiTap)||'');if(!target)return null;return (items||[]).find(x=>normText(x.DangBaiTap||'')===target)||null}
function editorTemplate(){return '\\begin{dn}\nNhập kiến thức, định nghĩa hoặc công thức cốt lõi.\n\\end{dn}\n\n\\begin{note}\nNhập dấu hiệu nhận biết, các bước giải, lưu ý và lỗi thường gặp.\n\\end{note}\n\n\\begin{vidu}\nNhập một ví dụ mẫu ngắn gọn.\n\\end{vidu}'}
function editorTheoryTemplate(){return '\\begin{dn}\nNhập lý thuyết SGK, kiến thức trọng tâm, công thức.\n\\end{dn}\n\n\\begin{note}\nNhập tóm tắt, lưu ý, sai lầm thường gặp.\n\\end{note}\n\n\\begin{vidu}\nNhập ví dụ mẫu minh họa.\n\\end{vidu}'}
function learningLatexDraftKey(q){return (THEORY_EDITOR_KIND==='theory'?theoryLearningDraftKey(q):dangTheoryDraftKey(q))}
function syncTheoryEditorChrome(){
  let kind=THEORY_EDITOR_KIND==='theory'?'theory':'method';
  let head=document.getElementById('theoryEditorHeaderLabel');
  if(head)head.textContent=kind==='theory'?'📚 Khung lý thuyết theo Bài học':'📘 Khung kiến thức theo Dạng bài tập';
  let dangWrap=document.getElementById('theoryEditorDangWrap');if(dangWrap)dangWrap.style.display=kind==='method'?'':'none';
  let titleInp=document.getElementById('theoryEditorTitle');if(titleInp)titleInp.placeholder=kind==='theory'?'Tiêu đề lý thuyết / bài học':'Tên dạng bài tập';
}
function setTheoryEditorStatus(msg,isError){let el=document.getElementById('theoryEditorStatus');if(el){el.textContent=String(msg||'');el.style.color=isError?'#dc2626':''}}
function switchDangTheoryTab(tab){
  THEORY_EDITOR_TAB=tab==='preview'?'preview':'edit';
  let ep=document.getElementById('theoryEditPanel'),pp=document.getElementById('theoryPreviewPanel');
  if(ep)ep.classList.toggle('hide',THEORY_EDITOR_TAB!=='edit');if(pp)pp.classList.toggle('hide',THEORY_EDITOR_TAB!=='preview');
  let a=document.getElementById('theoryTabEdit'),b=document.getElementById('theoryTabPreview');if(a)a.classList.toggle('active',THEORY_EDITOR_TAB==='edit');if(b)b.classList.toggle('active',THEORY_EDITOR_TAB==='preview');
  if(THEORY_EDITOR_TAB==='preview')previewDangTheoryEditor();
}
function previewDangTheoryEditor(){let inp=document.getElementById('theoryLatexInput'),box=document.getElementById('theoryEditorPreview');if(!box)return;let src=normalizeTheoryLatexSourceClient(inp?inp.value:'');try{if(window.MathJax&&MathJax.typesetClear)MathJax.typesetClear([box])}catch(e){}box.innerHTML=renderTheoryLatexBlocks(src);typesetTheoryMath()}
function insertTheoryEnvironment(type){
  let el=document.getElementById('theoryLatexInput');if(!el)return;let templates={dn:'\\begin{dn}\nNhập nội dung định nghĩa hoặc kiến thức trọng tâm.\n\\end{dn}',kttrongtam:'\\begin{kttrongtam}\nNhập kiến thức trọng tâm.\n\\end{kttrongtam}',note:'\\begin{note}\nNhập công thức, phương pháp hoặc lưu ý.\n\\end{note}',vidu:'\\begin{vidu}\nNhập ví dụ mẫu và lời giải ngắn.\n\\end{vidu}',vd:'\\begin{vd}\nNhập ví dụ mẫu.\n\\loigiai{\nLời giải...\n}\n\\end{vd}'};let t=templates[type]||'';let s=el.selectionStart||0,e=el.selectionEnd||s,prefix=(s>0&&el.value.slice(0,s).trim()?'\n\n':'');el.value=el.value.slice(0,s)+prefix+t+el.value.slice(e);let pos=s+prefix.length+t.length;el.focus();el.setSelectionRange(pos,pos);onDangTheoryInput();setTimeout(()=>el.scrollIntoView({block:'center',behavior:'smooth'}),220)
}
function onDangTheoryInput(){THEORY_EDITOR_DIRTY=true;clearTimeout(THEORY_EDITOR_DRAFT_TIMER);THEORY_EDITOR_DRAFT_TIMER=setTimeout(saveDangTheoryDraftSilent,500);setTheoryEditorStatus('Đang soạn — chưa lưu Google Sheet.',false);if(THEORY_EDITOR_TAB==='preview')previewDangTheoryEditor()}
function saveDangTheoryDraftSilent(){try{if(!THEORY_EDITOR_Q)return;let el=document.getElementById('theoryLatexInput');localStorage.setItem(learningLatexDraftKey(THEORY_EDITOR_Q),String(el?el.value:''));setTheoryEditorStatus('Đã tự lưu nháp trên thiết bị · chưa lưu Google Sheet.',false)}catch(e){}}
function saveDangTheoryDraftNow(){saveDangTheoryDraftSilent();setTheoryEditorStatus('Đã lưu nháp trên thiết bị này.',false)}
async function openDangTheoryEditor(ev){
  if(ev){if(ev.preventDefault)ev.preventDefault();if(ev.stopPropagation)ev.stopPropagation()}
  if(!USER.is_admin){alert('Chỉ ADMIN được soạn khung Dạng bài tập.');return}
  let q=QUESTIONS[CUR]||{};if(!q||!String(q.DangBaiTap||'').trim()){alert('Hãy mở một câu đã có Dạng bài tập (cột H) trước.');return}
  THEORY_EDITOR_KIND='method';THEORY_EDITOR_Q=Object.assign({},q);THEORY_EDITOR_ITEM=null;THEORY_EDITOR_DIRTY=false;syncTheoryViewportHeight();syncTheoryEditorChrome();
  let overlay=document.getElementById('dangTheoryEditor');overlay.classList.remove('hide');overlay.setAttribute('aria-hidden','false');document.body.classList.add('theoryEditorOpen');
  document.getElementById('theoryEditorScope').textContent=[q.Mon,q.Lop,q.Chuong,q.BaiHoc,q.DangBaiTap].filter(Boolean).join(' · ');
  document.getElementById('theoryEditorDang').value=q.DangBaiTap||'';document.getElementById('theoryEditorTitle').value=q.DangBaiTap||'';
  let inp=document.getElementById('theoryLatexInput');inp.value='';switchDangTheoryTab('edit');setTheoryEditorStatus('Đang tải nội dung từ Google Sheet…',false);
  try{
    let body={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||'',DangBaiTap:q.DangBaiTap||''};
    let j=await api('/api/learning/method',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let it=exactDangTheoryItem(j.items||[],q);THEORY_EDITOR_ITEM=it?Object.assign({},it):{};
    let sheetSrc=it?normalizeTheoryLatexSourceClient(it.NoiDungLaTeX||theorySourceFromLegacyItem(it)):'';let draft='';try{draft=localStorage.getItem(learningLatexDraftKey(q))||''}catch(e){}
    inp.value=draft||sheetSrc||editorTemplate();document.getElementById('theoryEditorTitle').value=(it&&(it.TenPhuongPhap||it.DangBaiTap))||q.DangBaiTap||'';
    THEORY_EDITOR_DIRTY=!!draft&&draft!==sheetSrc;setTheoryEditorStatus(draft?'Đã khôi phục nháp trên thiết bị. Bấm Lưu Google Sheet khi hoàn tất.':(sheetSrc?'Đã tải nội dung từ Google Sheet.':'Chưa có khung; đã tạo mẫu để nhập.'),false);
  }catch(e){inp.value=editorTemplate();setTheoryEditorStatus('Không tải được Sheet: '+(e.message||e),true)}
  setTimeout(()=>{inp.focus();inp.scrollIntoView({block:'center'})},220)
}
async function openTheoryLearningEditor(ev){
  if(ev){if(ev.preventDefault)ev.preventDefault();if(ev.stopPropagation)ev.stopPropagation()}
  if(!USER.is_admin){alert('Chỉ ADMIN được soạn khung Lý thuyết.');return}
  let q=QUESTIONS[CUR]||{};if(!q||!String(q.BaiHoc||'').trim()){alert('Hãy mở câu đã có Bài học (metadata Mon/Lớp/Chương/Bài học).');return}
  THEORY_EDITOR_KIND='theory';THEORY_EDITOR_Q=Object.assign({},q);THEORY_EDITOR_ITEM=null;THEORY_EDITOR_DIRTY=false;syncTheoryViewportHeight();syncTheoryEditorChrome();
  let overlay=document.getElementById('dangTheoryEditor');overlay.classList.remove('hide');overlay.setAttribute('aria-hidden','false');document.body.classList.add('theoryEditorOpen');
  document.getElementById('theoryEditorScope').textContent=[q.Mon,q.Lop,q.Chuong,q.BaiHoc].filter(Boolean).join(' · ');
  document.getElementById('theoryEditorDang').value='';document.getElementById('theoryEditorTitle').value=q.BaiHoc||'';
  let inp=document.getElementById('theoryLatexInput');inp.value='';switchDangTheoryTab('edit');setTheoryEditorStatus('Đang tải lý thuyết từ Google Sheet…',false);
  try{
    let body={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||''};
    let j=await api('/api/learning/theory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let it=exactTheoryLearningItem(j.items||[],q);THEORY_EDITOR_ITEM=it?Object.assign({},it):{};
    let sheetSrc=it?normalizeTheoryLatexSourceClient(it.NoiDungLaTeX||theorySourceFromLegacyTheoryItem(it)):'';let draft='';try{draft=localStorage.getItem(learningLatexDraftKey(q))||''}catch(e){}
    inp.value=draft||sheetSrc||editorTheoryTemplate();document.getElementById('theoryEditorTitle').value=(it&&(it.TieuDe||it.BaiHoc))||q.BaiHoc||'';
    THEORY_EDITOR_DIRTY=!!draft&&draft!==sheetSrc;setTheoryEditorStatus(draft?'Đã khôi phục nháp trên thiết bị. Bấm Lưu Google Sheet khi hoàn tất.':(sheetSrc?'Đã tải nội dung từ Google Sheet.':'Chưa có khung; đã tạo mẫu để nhập.'),false);
  }catch(e){inp.value=editorTheoryTemplate();setTheoryEditorStatus('Không tải được Sheet: '+(e.message||e),true)}
  setTimeout(()=>{inp.focus();inp.scrollIntoView({block:'center'})},220)
}
function closeDangTheoryEditor(force){
  if(!force&&THEORY_EDITOR_DIRTY&&!confirm('Nội dung đang soạn chưa lưu Google Sheet. Đóng nhưng vẫn giữ bản nháp trên thiết bị?'))return;
  saveDangTheoryDraftSilent();let overlay=document.getElementById('dangTheoryEditor');if(overlay){overlay.classList.add('hide');overlay.setAttribute('aria-hidden','true')}document.body.classList.remove('theoryEditorOpen');THEORY_EDITOR_Q=null;THEORY_EDITOR_ITEM=null;THEORY_EDITOR_KIND='method';THEORY_EDITOR_DIRTY=false
}
async function deleteLearningFromSheet(kind,ev,qOverride){
  if(ev){if(ev.preventDefault)ev.preventDefault();if(ev.stopPropagation)ev.stopPropagation()}
  if(!USER.is_admin)return;
  let q=qOverride||QUESTIONS[CUR]||{};
  kind=kind==='method'?'method':'theory';
  let label=kind==='theory'?('Lý thuyết bài «'+(q.BaiHoc||'')+'»'):('Khung dạng «'+(q.DangBaiTap||'')+'»');
  if(!confirm('Xóa '+label+' khỏi Google Sheet?'))return;
  if(!confirm('Xác nhận lần 2: xóa vĩnh viễn dòng Ly_Thuyet/Phuong_Phap?'))return;
  let it={Mon:q.Mon||'',Lop:q.Lop||'',Chuong:q.Chuong||'',BaiHoc:q.BaiHoc||''};
  if(kind==='method')it.DangBaiTap=q.DangBaiTap||'';
  try{
    let j=await api('/api/learning/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:kind,item:it})});
    if(typeof LEARNING_CACHE!=='undefined')LEARNING_CACHE={};
    DANG_THEORY_CACHE={};
    try{localStorage.removeItem(learningLatexDraftKey(q))}catch(e){}
    if(kind==='method')await syncDangTheoryCard(true);else await syncBaiTheoryCard(true);
    if(LEARNING_OPEN_KIND===kind)loadLearningPanelContent(kind,true);
    alert('Đã xóa dòng '+(j.row||'?')+' trên sheet.');
    return j;
  }catch(e){alert('Không xóa được: '+(e.message||e));throw e}
}
function deleteBaiTheoryFromSheet(ev){return deleteLearningFromSheet('theory',ev)}
function deleteDangTheoryFromSheet(ev){return deleteLearningFromSheet('method',ev)}
async function deleteLearningEditorSheet(){
  if(!USER.is_admin||!THEORY_EDITOR_Q)return;
  let kind=THEORY_EDITOR_KIND==='theory'?'theory':'method';
  try{await deleteLearningFromSheet(kind,null,THEORY_EDITOR_Q);closeDangTheoryEditor(true)}catch(e){}
}
async function saveDangTheoryToSheet(){
  if(!USER.is_admin||!THEORY_EDITOR_Q)return;let btn=document.getElementById('theoryEditorSaveBtn'),inp=document.getElementById('theoryLatexInput');let src=normalizeTheoryLatexSourceClient(inp?inp.value:'');
  let q=THEORY_EDITOR_Q,kind=THEORY_EDITOR_KIND==='theory'?'theory':'method';
  if(!String(src||'').trim()){
    if(!confirm('Khung đang trống. Xóa học liệu này khỏi Google Sheet?'))return;
    try{await deleteLearningFromSheet(kind,null,q);closeDangTheoryEditor(true)}catch(e){}
    return;
  }
  let blocks=parseTheoryLatexBlocks(src);if(!blocks.length){alert('Chưa tìm thấy môi trường dn, note hoặc vidu.');return}
  it.Mon=q.Mon||'';it.Lop=q.Lop||'';it.Chuong=q.Chuong||'';it.BaiHoc=q.BaiHoc||'';it.NoiDungLaTeX=src;it.TrangThai='OK';
  if(kind==='theory'){it.TieuDe=(document.getElementById('theoryEditorTitle').value||q.BaiHoc||'').trim()}else{it.DangBaiTap=q.DangBaiTap||'';it.TenPhuongPhap=(document.getElementById('theoryEditorTitle').value||q.DangBaiTap||'').trim()}
  let sheetName=kind==='theory'?'Ly_Thuyet':'Phuong_Phap';
  try{btn.disabled=true;btn.textContent='⏳ Đang lưu…';setTheoryEditorStatus('Đang ghi vào sheet '+sheetName+'…',false);let j=await api('/api/learning/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:kind,item:it})});THEORY_EDITOR_ITEM=Object.assign({},it,j.item||{});THEORY_EDITOR_DIRTY=false;try{localStorage.removeItem(learningLatexDraftKey(q))}catch(e){}if(kind==='method'){DANG_THEORY_CACHE={}}if(typeof LEARNING_CACHE!=='undefined')LEARNING_CACHE={};setTheoryEditorStatus('✅ Đã '+(j.action==='updated'?'cập nhật':'tạo')+' khung tại dòng '+(j.row||'')+' của sheet '+sheetName+'.',false);if(kind==='method')await syncDangTheoryCard(true);else await syncBaiTheoryCard(true);if(LEARNING_OPEN_KIND===kind)loadLearningPanelContent(kind,true);previewDangTheoryEditor()}catch(e){setTheoryEditorStatus('Không lưu được: '+(e.message||e),true);alert('Không lưu được khung: '+(e.message||e))}finally{btn.disabled=false;btn.textContent='✅ Lưu Google Sheet'}
}
document.addEventListener('keydown',function(e){
  if(e.key==='Escape'){
    let mh=document.getElementById('mh-fs-scr');
    if(mh&&mh.classList.contains('on')){closeMhFs();return;}
    let yt=document.getElementById('yt-fs-scr');
    if(yt&&yt.classList.contains('on')){closeYtFs();return;}
    let pdf=document.getElementById('pdf-fs-scr');
    if(pdf&&pdf.classList.contains('on')){closePdfFs();return;}
    let ov=document.getElementById('dangTheoryEditor');
    if(ov&&!ov.classList.contains('hide'))closeDangTheoryEditor();
    return;
  }
  let yt=document.getElementById('yt-fs-scr');
  if(yt&&yt.classList.contains('on')){
    if(e.key==='ArrowLeft'){e.preventDefault();ldvlYtFsNav(-1);}
    else if(e.key==='ArrowRight'){e.preventDefault();ldvlYtFsNav(1);}
    return;
  }
  let pdf=document.getElementById('pdf-fs-scr');
  if(!pdf||!pdf.classList.contains('on'))return;
  if(e.key==='ArrowLeft'){e.preventDefault();ldvlPdfFsNav(-1);}
  else if(e.key==='ArrowRight'){e.preventDefault();ldvlPdfFsNav(1);}
});
function drivePdfPreviewUrl(url){
  url=String(url||'').trim();
  let m=url.match(/\/d\/([a-zA-Z0-9_-]+)/);
  return m?('https://drive.google.com/file/d/'+m[1]+'/preview'):url.replace('/view','/preview');
}
function openPdfFs(url,title,ctx){
  ctx=ctx||{};
  try{if(typeof closeYtFs==='function')closeYtFs();}catch(e){}
  if(ctx.items&&ctx.items.length){
    window.LDVL_PDF_FS_CTX={sub:ctx.sub||'',idx:ctx.idx|0,items:ctx.items};
  }
  let scr=document.getElementById('pdf-fs-scr');
  if(!scr)return;
  let frame=document.getElementById('pdf-fs-frame');
  let previewUrl=drivePdfPreviewUrl(url);
  let m=String(url||'').match(/\/d\/([a-zA-Z0-9_-]+)/);
  let viewUrl=m?('https://drive.google.com/file/d/'+m[1]+'/view'):url;
  if(frame)frame.src=previewUrl;
  let t=document.getElementById('pdf-fs-title');
  if(t)t.textContent=title||'Đề PDF';
  let nt=document.getElementById('pdf-fs-newt');
  if(nt)nt.onclick=function(){window.open(viewUrl,'_blank');};
  ldvlPdfFsUpdateNav();
  scr.classList.add('on');
  try{document.documentElement.requestFullscreen?.();}catch(err){}
}
function closePdfFs(){
  let scr=document.getElementById('pdf-fs-scr');
  if(scr)scr.classList.remove('on');
  let frame=document.getElementById('pdf-fs-frame');
  if(frame)frame.src='about:blank';
  window.LDVL_PDF_FS_CTX={sub:'',idx:0,items:[]};
  try{document.exitFullscreen?.();}catch(err){}
}
function ldvlPdfFsUpdateNav(){
  let c=window.LDVL_PDF_FS_CTX||{items:[],idx:0};
  let items=c.items||[];
  let idx=c.idx|0;
  let counter=document.getElementById('pdf-fs-counter');
  if(counter)counter.textContent=items.length?(idx+1)+' / '+items.length:'';
  let prev=document.getElementById('pdf-fs-prev');
  let next=document.getElementById('pdf-fs-next');
  if(prev)prev.disabled=!items.length||idx<=0;
  if(next)next.disabled=!items.length||idx>=items.length-1;
}
function ldvlPdfFsNav(delta){
  let c=window.LDVL_PDF_FS_CTX||{};
  let items=c.items||[];
  if(!items.length)return;
  let ni=(c.idx|0)+(delta|0);
  if(ni<0||ni>=items.length)return;
  let it=items[ni];
  if(!it)return;
  openPdfFs(it.url,it.name||'Đề PDF',{sub:c.sub,idx:ni,items:items});
}
function ldvlPdfCanOpen(it){
  it=it||{};
  let q=String(it.quyen||'FREE').trim().toUpperCase();
  if(!USER||!USER.mahs)return q==='FREE';
  if(USER.is_admin||USER.is_svip)return true;
  if(USER.is_vip)return q!=='SVIP';
  if(USER.is_trial)return q==='FREE';
  return q==='FREE';
}
function ldvlPdfAllItems(sub){
  let srv=(META&&META.pdf_links&&META.pdf_links[sub])||[];
  let serverArr=Array.isArray(srv)?srv.slice():[];
  let local=[];
  try{local=JSON.parse(localStorage.getItem(ldvlPdfStorageKey(sub))||'[]')}catch(e){}
  if(!Array.isArray(local))local=[];
  if(USER&&USER.is_admin){
    if(local.length)return local;
    return serverArr;
  }
  if(serverArr.length)return serverArr;
  return local;
}
function ldvlPdfSubFromMon(mon){
  let k=String(mon||'').toLowerCase().replace(/\s/g,'');
  if((/vat|phys|ly|lí|lý/.test(k)||k==='l')&&!/(toan|math|tin)/.test(k))return 'phys';
  return 'math';
}
function openLearningPdfPanel(){
  try{
    if(LEARNING_OPEN_KIND==='pdf'){closeLearningPanel();return;}
    LEARNING_PANEL_COLLAPSED=false;
    LEARNING_OPEN_KIND='pdf';
    renderLearningPdfPanel();
  }catch(e){console.warn('openLearningPdfPanel',e);alert('Không mở được PDF: '+(e.message||e));}
}
function renderLearningPdfPanel(){
  let hb=document.getElementById('hintBox');
  if(!hb||LEARNING_OPEN_KIND!=='pdf')return;
  let q=QUESTIONS[CUR]||{};
  let sub=ldvlPdfSubFromMon(q.Mon);
  let monLabel=sub==='phys'?'Vật lý':'Toán';
  let all=[];
  try{all=ldvlPdfAllItems(sub)}catch(e){all=[];}
  let items=all.filter(function(it){try{return ldvlPdfCanOpen(it)}catch(e2){return false}});
  let body='';
  if(!items.length){
    body='<div class="muted" style="margin-top:8px;line-height:1.5">'+(all.length?('Có '+all.length+' PDF nhưng tài khoản chưa đủ quyền (VIP/SVIP).'):('Chưa có PDF môn '+monLabel+' — ADMIN thêm ở Dashboard → PDF '+monLabel+'.'))+'</div>';
  }else{
    body='<p class="muted" style="margin:0 0 8px;font-size:12px;line-height:1.45">Bấm tên file để xem toàn màn hình · <b>← Trước</b> / <b>Sau →</b> chuyển PDF.</p>';
    body+=items.map(function(it,i){
      let nm=esc(it.name||'PDF');
      let qtag=esc(it.quyen||'FREE');
      return '<div class="pdf-list-row" onclick="ldvlPdfOpen(\''+sub+'\','+i+')"><div class="pdf-list-ico"><i class="ti ti-file-type-pdf"></i></div><div class="pdf-list-body"><div class="pdf-list-name">'+nm+'</div><div class="pdf-list-meta"><span class="tag">'+qtag+'</span></div></div><div class="pdf-list-act"><span class="muted" style="font-size:11px">'+(i+1)+'/'+items.length+'</span></div></div>';
    }).join('');
  }
  if(USER&&USER.is_admin){
    body+='<div style="margin-top:10px"><button type="button" class="btn2" onclick="ldvlAdminOpenPdfPanel(\''+sub+'\')">⚙ Quản lý PDF '+monLabel+'</button></div>';
  }
  hb.classList.remove('hide');
  hb.classList.add('learningOpen');
  hb.classList.toggle('learningCollapsed',!!LEARNING_PANEL_COLLAPSED);
  hb.innerHTML='<div class="learningPanelShell">'+learningPanelTitleHtml('📄 PDF · '+monLabel)+'<div class="learningPanelBody">'+body+'</div></div>';
  syncLearningToggleUI();
}
function ldvlAdminOpenPdfPanel(sub){
  sub=(sub==='phys')?'phys':'math';
  let btn=document.querySelector('#ldvlSidebar [onclick*=\'ap-pdf-'+sub+'\']');
  if(typeof ldvlAdminNav==='function')ldvlAdminNav(btn,'ap-pdf-'+sub);
}
window.openLearningPdfPanel=openLearningPdfPanel;
function ldvlPdfSyncFromMeta(force){
  if(!META||!META.pdf_links)return;
  try{
    ['math','phys'].forEach(function(sub){
      let rows=META.pdf_links[sub];
      if(!Array.isArray(rows)||!rows.length)return;
      if(force){
        localStorage.setItem(ldvlPdfStorageKey(sub),JSON.stringify(rows));
        return;
      }
      if(USER&&USER.is_admin){
        if(window.LDVL_PDF_EDIT_ID&&window.LDVL_PDF_EDIT_SUB===sub)return;
        let local=ldvlPdfLoad(sub);
        if(Array.isArray(local)&&local.length)return;
      }
      localStorage.setItem(ldvlPdfStorageKey(sub),JSON.stringify(rows));
    });
  }catch(e){}
}
async function ldvlPdfSaveServer(){
  if(!USER||!USER.is_admin)return true;
  let info=document.getElementById('info');
  let oldInfo=info?info.textContent:'';
  if(info)info.textContent='💾 Đang lưu PDF…';
  try{
    let payload={math:ldvlPdfAllItems('math'),phys:ldvlPdfAllItems('phys')};
    let j=await api('/api/admin/pdf-links',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),timeoutMs:12000});
    if(j&&j.pdf_links){
      META=META||{};
      META.pdf_links=j.pdf_links;
      ldvlPdfSyncFromMeta(true);
      if(typeof ldvlPdfRenderList==='function'){ldvlPdfRenderList('math');ldvlPdfRenderList('phys');}
    }
    if(typeof ldvlStudentPdfRender==='function')ldvlStudentPdfRender();
    if(info)info.textContent=oldInfo||('Đã lưu PDF · '+new Date().toLocaleTimeString('vi-VN'));
    return true;
  }catch(e){
    console.warn('ldvlPdfSaveServer',e);
    if(info)info.textContent=oldInfo;
    alert('Lưu server thất bại: '+(e.message||e));
    return false;
  }
}
async function ldvlPdfMaybeMigrateLocal(){
  if(!USER||!USER.is_admin)return;
  try{if(sessionStorage.getItem('LDVL_PDF_MIGRATED_V1')==='1')return}catch(e){}
  let sm=(META&&META.pdf_links&&META.pdf_links.math)||[];
  let sp=(META&&META.pdf_links&&META.pdf_links.phys)||[];
  if(sm.length||sp.length){try{sessionStorage.setItem('LDVL_PDF_MIGRATED_V1','1')}catch(e){}return;}
  if(!ldvlPdfLoad('math').length&&!ldvlPdfLoad('phys').length)return;
  let ok=await ldvlPdfSaveServer();
  if(ok){try{sessionStorage.setItem('LDVL_PDF_MIGRATED_V1','1')}catch(e){}}
}
window.LDVL_STUDENT_PDF_SUB='math';
function ldvlPdfAdminPanelSync(){
  let adm=!!(USER&&USER.is_admin);
  let wrap=document.getElementById('ldvlPdfAdminPanel');
  if(wrap)wrap.classList.toggle('hide',!adm);
  if(!adm)return;
  let sub=window.LDVL_STUDENT_PDF_SUB||'math';
  let m=document.getElementById('ldvlPdfAdminMath');
  let p=document.getElementById('ldvlPdfAdminPhys');
  if(m)m.classList.toggle('hide',sub!=='math');
  if(p)p.classList.toggle('hide',sub!=='phys');
  ldvlPdfRenderList(sub);
  ldvlPdfSyncEditUi(sub);
}
function ldvlStudentPdfTab(sub){
  window.LDVL_STUDENT_PDF_SUB=sub||'math';
  let tm=document.getElementById('ldvlPdfTabMath');
  let tp=document.getElementById('ldvlPdfTabPhys');
  if(tm)tm.className=(sub==='math'?'btn':'btn2')+' ldvlPdfStab'+(sub==='math'?' on':'');
  if(tp)tp.className=(sub==='phys'?'btn':'btn2')+' ldvlPdfStab'+(sub==='phys'?' on':'');
  ldvlStudentPdfRender();
  ldvlPdfAdminPanelSync();
}
function ldvlStudentPdfRender(){
  let box=document.getElementById('ldvlStudentPdfList');
  if(!box)return;
  let sub=window.LDVL_STUDENT_PDF_SUB||'math';
  let all=ldvlPdfAllItems(sub);
  let items=all.filter(ldvlPdfCanOpen);
  if(!items.length){
    box.innerHTML='<div class="muted" style="padding:12px">'+(all.length?('Có '+all.length+' đề nhưng tài khoản chưa đủ quyền (VIP/SVIP).'):('Chưa có đề PDF môn '+(sub==='phys'?'Vật lý':'Toán')+(USER&&USER.is_admin?' — thêm link Drive ở khối ADMIN bên dưới.':'.')))+'</div>';
    return;
  }
  box.innerHTML=items.map(function(it,i){
    let nm=esc(it.name||'Đề PDF');
    let q=esc(it.quyen||'FREE');
    return '<div class="pdf-list-row" onclick="ldvlPdfOpen(\''+sub+'\','+i+')"><div class="pdf-list-ico"><i class="ti ti-file-type-pdf"></i></div><div class="pdf-list-body"><div class="pdf-list-name">'+nm+'</div><div class="pdf-list-meta"><span class="tag">'+q+'</span></div></div><div class="pdf-list-act"><span class="muted" style="font-size:11px">'+(i+1)+'/'+items.length+'</span></div></div>';
  }).join('');
}
window.ldvlStudentPdfTab=ldvlStudentPdfTab;
window.ldvlPdfAdminPanelSync=ldvlPdfAdminPanelSync;
window.ldvlPdfFsNav=ldvlPdfFsNav;
function previewDrivePdf(urlId,frameId,prevId){
  let url=(document.getElementById(urlId)||{}).value||'';
  if(!String(url).trim()){alert('Dán link Google Drive trước.');return;}
  let frame=document.getElementById(frameId);
  let prev=document.getElementById(prevId);
  if(frame)frame.src=drivePdfPreviewUrl(url);
  if(prev)prev.classList.remove('hide');
}
function ldvlPdfStorageKey(sub){return 'ldvl_pdf_links_'+sub;}
function ldvlPdfLoad(sub){try{return JSON.parse(localStorage.getItem(ldvlPdfStorageKey(sub))||'[]')}catch(e){return[]}}
function ldvlPdfPersist(sub,items){try{localStorage.setItem(ldvlPdfStorageKey(sub),JSON.stringify(items||[]))}catch(e){}}
function ldvlPdfSyncEditUi(sub){
  let pfx=sub==='phys'?'pdf-p':'pdf-m';
  let editing=!!(window.LDVL_PDF_EDIT_ID&&window.LDVL_PDF_EDIT_SUB===sub);
  let btn=document.getElementById(pfx+'-add-btn');
  let cancel=document.getElementById(pfx+'-cancel-btn');
  let hint=document.getElementById(pfx+'-edit-hint');
  if(btn)btn.textContent=editing?'💾 Cập nhật & lưu server':'➕ Thêm đề';
  if(cancel)cancel.classList.toggle('hide',!editing);
  if(hint){
    if(editing){
      hint.classList.remove('hide');
      hint.innerHTML='✏️ Đang sửa: <b>'+esc(String(window.LDVL_PDF_EDIT_NAME||''))+'</b> — sửa ô trên rồi bấm <b>Cập nhật</b>, hoặc <b>Hủy sửa</b>.';
    }else hint.classList.add('hide');
  }
}
function ldvlPdfSameId(a,b){return Number(a)===Number(b);}
function ldvlPdfEdit(sub,id){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return;}
  let items=ldvlPdfAllItems(sub);
  let it=items.find(function(x){return ldvlPdfSameId(x.id,id);});
  if(!it){alert('Không tìm thấy đề.');return;}
  let pfx=sub==='phys'?'pdf-p':'pdf-m';
  window.LDVL_PDF_EDIT_SUB=sub;
  window.LDVL_PDF_EDIT_ID=id;
  window.LDVL_PDF_EDIT_NAME=it.name||'';
  let ni=document.getElementById(pfx+'-name');
  let ui=document.getElementById(pfx+'-url');
  let qi=document.getElementById(pfx+'-quyen');
  if(ni)ni.value=it.name||'';
  if(ui)ui.value=it.url||'';
  if(qi)qi.value=it.quyen||'FREE';
  ldvlPdfSyncEditUi(sub);
  if(ni)ni.focus();
  if(typeof window.ldvlApplyHomeTab==='function')window.ldvlApplyHomeTab('pdf');
  ldvlStudentPdfTab(sub);
  let panel=document.getElementById('ldvlPdfAdminPanel');
  if(panel){
    panel.classList.remove('homeNavFlash');
    void panel.offsetWidth;
    panel.classList.add('homeNavFlash');
  }
}
function ldvlPdfCancelEdit(sub){
  let pfx=sub==='phys'?'pdf-p':'pdf-m';
  window.LDVL_PDF_EDIT_ID=0;
  window.LDVL_PDF_EDIT_SUB='';
  window.LDVL_PDF_EDIT_NAME='';
  ['name','url'].forEach(function(k){let el=document.getElementById(pfx+'-'+k);if(el)el.value='';});
  ldvlPdfSyncEditUi(sub);
}
function ldvlPdfMove(sub,id){
  if(!USER||!USER.is_admin)return;
  let toSub=sub==='phys'?'math':'phys';
  let label=toSub==='phys'?'Vật lý':'Toán';
  if(!confirm('Chuyển đề này sang môn '+label+'?'))return;
  let items=ldvlPdfAllItems(sub).slice();
  let i=items.findIndex(function(x){return ldvlPdfSameId(x.id,id);});
  if(i<0){alert('Không tìm thấy đề.');return;}
  let it=items.splice(i,1)[0];
  let other=ldvlPdfAllItems(toSub).slice();
  other.unshift(it);
  ldvlPdfPersist(sub,items);
  ldvlPdfPersist(toSub,other);
  ldvlPdfRenderList(sub);
  ldvlPdfRenderList(toSub);
  ldvlPdfSaveServer();
  ldvlStudentPdfRender();
  alert('Đã chuyển sang môn '+label+'.');
}
function ldvlPdfAdd(sub){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return;}
  let pfx=sub==='phys'?'pdf-p':'pdf-m';
  let name=String((document.getElementById(pfx+'-name')||{}).value||'').trim();
  let url=String((document.getElementById(pfx+'-url')||{}).value||'').trim();
  let quyen=String((document.getElementById(pfx+'-quyen')||{}).value||'FREE').trim();
  if(!name||!url){alert('Nhập tên đề và link Drive.');return;}
  let items=ldvlPdfAllItems(sub).slice();
  let editId=window.LDVL_PDF_EDIT_ID|0;
  if(editId&&window.LDVL_PDF_EDIT_SUB===sub){
    let i=items.findIndex(function(x){return ldvlPdfSameId(x.id,editId);});
    let row={id:editId,name,url,quyen,at:new Date().toISOString()};
    if(i>=0)items[i]=Object.assign({},items[i],row);
    else items.unshift(row);
    ldvlPdfCancelEdit(sub);
  }else{
    items.unshift({id:Date.now(),name,url,quyen,at:new Date().toISOString()});
    let ni=document.getElementById(pfx+'-name'),ui=document.getElementById(pfx+'-url');
    if(ni)ni.value='';if(ui)ui.value='';
  }
  ldvlPdfPersist(sub,items);
  ldvlPdfRenderList(sub);
  let btn=document.getElementById(pfx+'-add-btn');
  if(btn){btn.disabled=true;btn.textContent='💾 Đang lưu…';}
  ldvlPdfSaveServer().then(function(ok){
    if(btn){btn.disabled=false;ldvlPdfSyncEditUi(sub);}
    if(typeof ldvlStudentPdfRender==='function')ldvlStudentPdfRender();
    if(editId){
      if(ok)alert('✅ Đã cập nhật tên/link và lưu server.');
      else alert('⚠ Đã sửa trên máy nhưng lưu server thất bại — bấm Cập nhật lại hoặc kiểm tra kết nối.');
    }else{
      alert(ok?'✅ Đã thêm đề PDF.':'⚠ Đã thêm trên máy nhưng lưu server thất bại — thử lại.');
    }
  });
}
function ldvlPdfDelete(sub,id){
  if(!confirm('Xóa đề PDF này khỏi danh sách?'))return;
  let items=ldvlPdfAllItems(sub).filter(function(x){return !ldvlPdfSameId(x.id,id);});
  ldvlPdfPersist(sub,items);
  ldvlPdfRenderList(sub);
  ldvlPdfSaveServer();
  if(typeof ldvlStudentPdfRender==='function')ldvlStudentPdfRender();
}
function ldvlPdfEnsureSynced(sub){
  let local=ldvlPdfLoad(sub);
  if(Array.isArray(local)&&local.length)return;
  let fromMeta=(META&&META.pdf_links&&META.pdf_links[sub])||[];
  if(fromMeta&&fromMeta.length)ldvlPdfPersist(sub,fromMeta);
}
function ldvlPdfRenderList(sub){
  ldvlPdfEnsureSynced(sub);
  let listId=sub==='phys'?'pdf-p-list':'pdf-m-list';
  let box=document.getElementById(listId);
  if(!box)return;
  let items=ldvlPdfAllItems(sub);
  if(!items.length){
    box.innerHTML='<div class="pdf-list-empty"><b>Chưa có đề trong danh sách.</b><br><span style="font-size:12px">① Điền <b>Tên</b> + <b>link Drive</b> → <b>Xem trước</b><br>② Bấm <b>➕ Thêm đề</b> (xem trước ≠ đã lưu)<br>③ Mỗi dòng sẽ có nút <b style="color:#1d4ed8">Sửa</b> · <b style="color:#991b1b">Xóa</b> bên phải</span></div>';
    return;
  }
  let moveLbl=sub==='phys'?'→ Toán':'→ Lý';
  box.innerHTML='<div class="pdf-list-head"><span>Đề PDF ('+items.length+')</span><span class="pdf-list-act-h">Sửa · Chuyển · Xóa</span></div>'+items.map(function(it,i){
    let nm=esc(it.name||'Đề PDF');
    let q=esc(it.quyen||'FREE');
    return '<div class="pdf-list-row" onclick="ldvlPdfOpen(\''+sub+'\','+i+')"><div class="pdf-list-ico"><i class="ti ti-file-type-pdf"></i></div><div class="pdf-list-body"><div class="pdf-list-name">'+nm+'</div><div class="pdf-list-meta"><span class="tag">'+q+'</span> · bấm tên để xem</div></div><div class="pdf-list-act"><button type="button" class="pdfBtnEdit" onclick="event.stopPropagation();ldvlPdfEdit(\''+sub+'\','+it.id+')">Sửa</button><button type="button" class="pdfBtnMove" onclick="event.stopPropagation();ldvlPdfMove(\''+sub+'\','+it.id+')">'+moveLbl+'</button><button type="button" class="pdfBtnDel" onclick="event.stopPropagation();ldvlPdfDelete(\''+sub+'\','+it.id+')">Xóa</button></div></div>';
  }).join('');
}
function ldvlPdfOpen(sub,idx){
  let items=ldvlPdfAllItems(sub).filter(ldvlPdfCanOpen);
  let it=items[idx|0];
  if(!it){alert('Không mở được đề này (quyền hoặc danh sách trống).');return;}
  openPdfFs(it.url,it.name||'Đề PDF',{sub:sub,idx:idx|0,items:items});
}
async function ldvlPdfCopy(sub,idx){
  let it=(ldvlPdfAllItems(sub)||[])[idx|0];
  if(!it)return;
  let ok=await copyTextToClipboard(it.url||'');
  alert(ok?'Đã chép link':'Không chép được');
}

/* ── YouTube bài mẫu (nhúng xem trong app) ── */
function ldvlYtExtractId(url){
  url=String(url||'').trim();
  if(!url)return '';
  let m=url.match(/(?:youtube\.com\/watch\?(?:[^#]*&)?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/|youtube\.com\/live\/)([A-Za-z0-9_-]{6,})/i)
    ||url.match(/[?&]v=([A-Za-z0-9_-]{6,})/i);
  return m?m[1]:(/^[A-Za-z0-9_-]{6,}$/.test(url)?url:'');
}
function ldvlYtEmbed(vid){
  if(!vid)return '';
  /* youtube.com/embed ổn định hơn nocookie trên mobile / một số mạng */
  return 'https://www.youtube.com/embed/'+encodeURIComponent(vid)+'?rel=0&modestbranding=1&playsinline=1&fs=1';
}
function ldvlYtThumb(vid){return vid?('https://i.ytimg.com/vi/'+vid+'/hqdefault.jpg'):'';}
function ldvlYtCanOpen(it){return ldvlPdfCanOpen(it);}
function ldvlYtStorageKey(sub){return 'ldvl_yt_links_'+sub;}
function ldvlYtLoad(sub){
  try{let a=JSON.parse(localStorage.getItem(ldvlYtStorageKey(sub))||'[]');return Array.isArray(a)?a:[];}catch(e){return [];}
}
function ldvlYtPersist(sub,items){
  try{localStorage.setItem(ldvlYtStorageKey(sub),JSON.stringify(items||[]));}catch(e){}
}
function ldvlYtSameId(a,b){return String(a||'')===String(b||'');}
function ldvlYtNormItem(it){
  it=it||{};
  let vid=String(it.video_id||'').trim()||ldvlYtExtractId(it.url||'');
  let url=String(it.url||'').trim()||(vid?('https://www.youtube.com/watch?v='+vid):'');
  return {
    id:it.id||Date.now(),
    name:String(it.name||'').trim(),
    url:url,
    video_id:vid,
    embed:it.embed||ldvlYtEmbed(vid),
    thumb:it.thumb||ldvlYtThumb(vid),
    quyen:String(it.quyen||'FREE').trim()||'FREE',
    lop:String(it.lop||it.Lop||'').trim(),
    note:String(it.note||'').trim(),
    at:it.at||''
  };
}
function ldvlYtMonLabel(sub){return sub==='phys'?'Vật lý':'Toán';}
function ldvlYtMatchMon(rowMon,sub){
  let m=String(rowMon||'');
  if(sub==='phys')return /v[aậ]t\s*l[ií]y|v[aậ]t\s*l[yý]/i.test(m)||/^VL$/i.test(m);
  return /to[aá]n/i.test(m)||/^T$/i.test(m);
}
function ldvlYtLopSortKey(lop){
  let s=String(lop||'').trim();
  if(!s)return [9999,''];
  let m=s.match(/(\d{1,2})/);
  return [m?parseInt(m[1],10):500,s.toLowerCase()];
}
function ldvlYtLopOptions(sub){
  let set={};
  function add(l){l=String(l||'').trim();if(l)set[l]=1;}
  ['10','11','12'].forEach(add);
  (CATALOG||[]).forEach(function(c){if(ldvlYtMatchMon(c.Mon,sub))add(c.Lop);});
  ((META&&META.lesson_catalog)||[]).forEach(function(c){if(ldvlYtMatchMon(c.Mon,sub))add(c.Lop);});
  ldvlYtAllItems(sub).forEach(function(it){add(it.lop);});
  let fl=typeof val==='function'?val('fLop'):'';
  if(fl)add(fl);
  return Object.keys(set).sort(function(a,b){
    let ka=ldvlYtLopSortKey(a),kb=ldvlYtLopSortKey(b);
    return ka[0]-kb[0]||(ka[1]<kb[1]?-1:ka[1]>kb[1]?1:0);
  });
}
function ldvlYtFillLopSelect(sub){
  let pfx=sub==='phys'?'yt-p':'yt-m';
  let sel=document.getElementById(pfx+'-lop');
  if(!sel)return;
  let cur=sel.value||window.LDVL_STUDENT_YT_LOP||'';
  let opts=ldvlYtLopOptions(sub);
  if(cur&&opts.indexOf(cur)<0)opts=opts.concat([cur]);
  sel.innerHTML=opts.map(function(l){return '<option value="'+escAttr(l)+'">'+esc(l)+'</option>';}).join('');
  if(cur&&opts.indexOf(cur)>=0)sel.value=cur;
  else if(opts.length)sel.value=opts[0];
}
function ldvlYtLopDisplay(lop){
  lop=String(lop||'').trim();
  if(!lop)return 'Chưa gán lớp';
  return /^l[oớ]p\s+/i.test(lop)?lop:('Lớp '+lop);
}
function ldvlYtFilterByLop(items,lop){
  lop=String(lop||'').trim();
  if(!lop)return items.slice();
  return items.filter(function(it){return String(it.lop||'').trim()===lop;});
}
function ldvlYtGroupByLop(items){
  let map={},order=[];
  items.forEach(function(it){
    let k=String(it.lop||'').trim()||'__none__';
    if(!map[k]){map[k]=[];order.push(k);}
    map[k].push(it);
  });
  order.sort(function(a,b){
    if(a==='__none__')return 1;
    if(b==='__none__')return -1;
    let ka=ldvlYtLopSortKey(a),kb=ldvlYtLopSortKey(b);
    return ka[0]-kb[0]||(ka[1]<kb[1]?-1:ka[1]>kb[1]?1:0);
  });
  return order.map(function(k){return {lop:k==='__none__'?'':k,items:map[k]};});
}
function ldvlYtRenderLopTabs(sub){
  let box=document.getElementById('ldvlYtLopTabs');
  if(!box)return;
  let all=ldvlYtAllItems(sub);
  let used={};
  all.forEach(function(it){let l=String(it.lop||'').trim();if(l)used[l]=1;});
  let lops=Object.keys(used).sort(function(a,b){
    let ka=ldvlYtLopSortKey(a),kb=ldvlYtLopSortKey(b);
    return ka[0]-kb[0]||(ka[1]<kb[1]?-1:ka[1]>kb[1]?1:0);
  });
  if(!lops.length)lops=ldvlYtLopOptions(sub).slice(0,6);
  let cur=String(window.LDVL_STUDENT_YT_LOP||'');
  if(cur&&lops.indexOf(cur)<0)lops=lops.concat([cur]);
  let html='<button type="button" class="btn2 ldvlYtLopBtn'+(cur?'':' on')+'" onclick="ldvlStudentYtLop(\'\')">Tất cả lớp</button>';
  html+=lops.map(function(l){
    return '<button type="button" class="btn2 ldvlYtLopBtn'+(cur===l?' on':'')+'" onclick="ldvlStudentYtLop(\''+String(l).replace(/'/g,"\\'")+'\')">'+esc(ldvlYtLopDisplay(l))+'</button>';
  }).join('');
  box.innerHTML=html;
}
function ldvlStudentYtLop(lop){
  window.LDVL_STUDENT_YT_LOP=String(lop||'');
  try{localStorage.setItem('LDVL_YT_LOP',window.LDVL_STUDENT_YT_LOP);}catch(e){}
  ldvlStudentYtRender();
}
function ldvlYtAllItems(sub){
  let srv=(META&&META.youtube_links&&META.youtube_links[sub])||[];
  let serverArr=Array.isArray(srv)?srv.map(ldvlYtNormItem).filter(function(x){return x.video_id&&x.name;}):[];
  let local=ldvlYtLoad(sub).map(ldvlYtNormItem).filter(function(x){return x.video_id&&x.name;});
  if(USER&&USER.is_admin){
    if(local.length)return local;
    return serverArr;
  }
  if(serverArr.length)return serverArr;
  return local;
}
function ldvlYtSyncFromMeta(force){
  if(!META||!META.youtube_links)return;
  try{
    ['math','phys'].forEach(function(sub){
      let rows=META.youtube_links[sub];
      if(!Array.isArray(rows)||!rows.length)return;
      if(force){
        localStorage.setItem(ldvlYtStorageKey(sub),JSON.stringify(rows));
        return;
      }
      if(USER&&USER.is_admin){
        if(window.LDVL_YT_EDIT_ID&&window.LDVL_YT_EDIT_SUB===sub)return;
        let local=ldvlYtLoad(sub);
        if(Array.isArray(local)&&local.length)return;
      }
      localStorage.setItem(ldvlYtStorageKey(sub),JSON.stringify(rows));
    });
  }catch(e){}
}
async function ldvlYtSaveServer(){
  if(!USER||!USER.is_admin)return true;
  let info=document.getElementById('info');
  let oldInfo=info?info.textContent:'';
  if(info)info.textContent='💾 Đang lưu video…';
  try{
    let payload={math:ldvlYtAllItems('math'),phys:ldvlYtAllItems('phys')};
    let j=await api('/api/admin/youtube-links',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),timeoutMs:12000});
    if(j&&j.youtube_links){
      META=META||{};
      META.youtube_links=j.youtube_links;
      ldvlYtSyncFromMeta(true);
      if(typeof ldvlYtRenderList==='function'){ldvlYtRenderList('math');ldvlYtRenderList('phys');}
    }
    if(typeof ldvlStudentYtRender==='function')ldvlStudentYtRender();
    if(info)info.textContent=oldInfo||('Đã lưu video · '+new Date().toLocaleTimeString('vi-VN'));
    return true;
  }catch(e){
    console.warn('ldvlYtSaveServer',e);
    if(info)info.textContent=oldInfo;
    alert('Lưu video thất bại: '+(e.message||e));
    return false;
  }
}
window.LDVL_STUDENT_YT_SUB='math';
window.LDVL_STUDENT_YT_LOP='';
try{window.LDVL_STUDENT_YT_LOP=localStorage.getItem('LDVL_YT_LOP')||'';}catch(e){}
window.LDVL_YT_EDIT_ID=0;
window.LDVL_YT_EDIT_SUB='';
window.LDVL_YT_FS={items:[],idx:0,url:''};
function ldvlYtSyncEditUi(sub){
  let pfx=sub==='phys'?'yt-p':'yt-m';
  let editing=!!(window.LDVL_YT_EDIT_ID&&window.LDVL_YT_EDIT_SUB===sub);
  let add=document.getElementById(pfx+'-add-btn');
  let cancel=document.getElementById(pfx+'-cancel-btn');
  let hint=document.getElementById(pfx+'-edit-hint');
  if(add)add.textContent=editing?'💾 Cập nhật video':'➕ Thêm video';
  if(cancel)cancel.classList.toggle('hide',!editing);
  if(hint){
    hint.classList.toggle('hide',!editing);
    if(editing)hint.innerHTML='Đang sửa: <b>'+esc(window.LDVL_YT_EDIT_NAME||'')+'</b> — đổi tên/link/lớp rồi bấm Cập nhật.';
  }
}
function ldvlYtAdminPanelSync(){
  let adm=!!(USER&&USER.is_admin);
  let wrap=document.getElementById('ldvlYtAdminPanel');
  if(wrap)wrap.classList.toggle('hide',!adm);
  if(!adm)return;
  let sub=window.LDVL_STUDENT_YT_SUB||'math';
  let m=document.getElementById('ldvlYtAdminMath');
  let p=document.getElementById('ldvlYtAdminPhys');
  if(m)m.classList.toggle('hide',sub!=='math');
  if(p)p.classList.toggle('hide',sub!=='phys');
  ldvlYtFillLopSelect(sub);
  ldvlYtRenderList(sub);
  ldvlYtSyncEditUi(sub);
}
function ldvlStudentYtTab(sub){
  window.LDVL_STUDENT_YT_SUB=sub||'math';
  let tm=document.getElementById('ldvlYtTabMath');
  let tp=document.getElementById('ldvlYtTabPhys');
  if(tm)tm.className=(sub==='math'?'btn':'btn2')+' ldvlYtStab'+(sub==='math'?' on':'');
  if(tp)tp.className=(sub==='phys'?'btn':'btn2')+' ldvlYtStab'+(sub==='phys'?' on':'');
  ldvlStudentYtRender();
  ldvlYtAdminPanelSync();
}
function ldvlYtCardHtml(sub,it){
  let nm=esc(it.name||'Video');
  let q=esc(it.quyen||'FREE');
  let lop=esc(ldvlYtLopDisplay(it.lop));
  let th=esc(it.thumb||ldvlYtThumb(it.video_id));
  let idAttr=escAttr(String(it.id));
  return '<div class="ldvlYtCard" data-yt-sub="'+escAttr(sub)+'" data-yt-id="'+idAttr+'" role="button" tabindex="0"><div class="ldvlYtPlayBadge"><img class="ldvlYtThumb" src="'+th+'" alt="" loading="lazy" onerror="this.style.opacity=.3"></div><div style="min-width:0;flex:1"><div class="ldvlYtName">'+nm+'</div><div class="ldvlYtMeta"><span class="tag">'+lop+'</span> · <span class="tag">'+q+'</span> · bấm để xem</div></div></div>';
}
function ldvlStudentYtRender(){
  let box=document.getElementById('ldvlStudentYtList');
  if(!box)return;
  let sub=window.LDVL_STUDENT_YT_SUB||'math';
  ldvlYtRenderLopTabs(sub);
  let all=ldvlYtAllItems(sub);
  let openable=all.filter(ldvlYtCanOpen);
  let items=ldvlYtFilterByLop(openable,window.LDVL_STUDENT_YT_LOP);
  if(!items.length){
    let msg='';
    if(!all.length)msg='Chưa có video môn '+ldvlYtMonLabel(sub)+(USER&&USER.is_admin?' — chọn lớp rồi dán link ở khối ADMIN bên dưới.':'.');
    else if(!openable.length)msg='Có '+all.length+' video nhưng tài khoản chưa đủ quyền (VIP/SVIP).';
    else msg='Chưa có video '+ldvlYtLopDisplay(window.LDVL_STUDENT_YT_LOP)+' môn '+ldvlYtMonLabel(sub)+'.';
    box.innerHTML='<div class="muted" style="padding:12px">'+msg+'</div>';
    return;
  }
  let groups=ldvlYtGroupByLop(items);
  box.innerHTML=groups.map(function(g){
    let head='<div class="ldvlYtLopHead"><span>'+esc(ldvlYtLopDisplay(g.lop))+' · '+ldvlYtMonLabel(sub)+'</span><span class="muted" style="font-weight:700">'+g.items.length+' video</span></div>';
    return head+g.items.map(function(it){return ldvlYtCardHtml(sub,it);}).join('');
  }).join('');
}
function ldvlYtEnsureSynced(sub){
  let local=ldvlYtLoad(sub);
  if(Array.isArray(local)&&local.length)return;
  let fromMeta=(META&&META.youtube_links&&META.youtube_links[sub])||[];
  if(fromMeta&&fromMeta.length)ldvlYtPersist(sub,fromMeta);
}
function ldvlYtRenderList(sub){
  ldvlYtEnsureSynced(sub);
  ldvlYtFillLopSelect(sub);
  let listId=sub==='phys'?'yt-p-list':'yt-m-list';
  let box=document.getElementById(listId);
  if(!box)return;
  let items=ldvlYtAllItems(sub);
  if(!items.length){
    box.innerHTML='<div class="muted" style="padding:10px">Chưa có video.</div>';
    return;
  }
  let moveLbl=sub==='phys'?'→ Toán':'→ Lý';
  let groups=ldvlYtGroupByLop(items);
  let html='<div class="pdf-list-head"><span>Video theo lớp ('+items.length+')</span><span class="pdf-list-act-h">Sửa · Chuyển · Xóa</span></div>';
  html+=groups.map(function(g){
    let head='<div class="ldvlYtLopHead"><span>'+esc(ldvlYtLopDisplay(g.lop))+'</span><span class="muted" style="font-weight:700">'+g.items.length+'</span></div>';
    let rows=g.items.map(function(it){
      let nm=esc(it.name||'Video');
      let q=esc(it.quyen||'FREE');
      let lop=esc(it.lop||'—');
      return '<div class="pdf-list-row" data-yt-sub="'+escAttr(sub)+'" data-yt-id="'+escAttr(String(it.id))+'" role="button" tabindex="0"><div class="pdf-list-ico"><i class="ti ti-brand-youtube"></i></div><div class="pdf-list-body"><div class="pdf-list-name">'+nm+'</div><div class="pdf-list-meta"><span class="tag">'+lop+'</span> · <span class="tag">'+q+'</span> · bấm để xem</div></div><div class="pdf-list-act"><button type="button" class="pdfBtnEdit" data-yt-act="edit" data-yt-sub="'+escAttr(sub)+'" data-yt-id="'+escAttr(String(it.id))+'">Sửa</button><button type="button" class="pdfBtnMove" data-yt-act="move" data-yt-sub="'+escAttr(sub)+'" data-yt-id="'+escAttr(String(it.id))+'">'+moveLbl+'</button><button type="button" class="pdfBtnDel" data-yt-act="del" data-yt-sub="'+escAttr(sub)+'" data-yt-id="'+escAttr(String(it.id))+'">Xóa</button></div></div>';
    }).join('');
    return head+rows;
  }).join('');
  box.innerHTML=html;
}
function ldvlYtEdit(sub,id){
  if(!USER||!USER.is_admin)return;
  let items=ldvlYtAllItems(sub);
  let it=items.find(function(x){return ldvlYtSameId(x.id,id);});
  if(!it)return;
  let pfx=sub==='phys'?'yt-p':'yt-m';
  window.LDVL_YT_EDIT_SUB=sub;
  window.LDVL_YT_EDIT_ID=id;
  window.LDVL_YT_EDIT_NAME=it.name||'';
  ldvlYtFillLopSelect(sub);
  let ni=document.getElementById(pfx+'-name');
  let ui=document.getElementById(pfx+'-url');
  let qi=document.getElementById(pfx+'-quyen');
  let li=document.getElementById(pfx+'-lop');
  if(ni)ni.value=it.name||'';
  if(ui)ui.value=it.url||'';
  if(qi)qi.value=it.quyen||'FREE';
  if(li){
    let lop=String(it.lop||'').trim();
    if(lop){
      if(![].some.call(li.options,function(o){return o.value===lop;})){
        let opt=document.createElement('option');opt.value=lop;opt.textContent=lop;li.appendChild(opt);
      }
      li.value=lop;
    }
  }
  ldvlYtSyncEditUi(sub);
  if(ni)ni.focus();
  if(typeof window.ldvlApplyHomeTab==='function')window.ldvlApplyHomeTab('video');
  ldvlStudentYtTab(sub);
  let panel=document.getElementById('ldvlYtAdminPanel');
  if(panel){
    panel.classList.remove('homeNavFlash');
    void panel.offsetWidth;
    panel.classList.add('homeNavFlash');
  }
}
function ldvlYtCancelEdit(sub){
  let pfx=sub==='phys'?'yt-p':'yt-m';
  window.LDVL_YT_EDIT_ID=0;
  window.LDVL_YT_EDIT_SUB='';
  window.LDVL_YT_EDIT_NAME='';
  ['name','url'].forEach(function(k){let el=document.getElementById(pfx+'-'+k);if(el)el.value='';});
  ldvlYtSyncEditUi(sub);
}
function ldvlYtMove(sub,id){
  if(!USER||!USER.is_admin)return;
  let toSub=sub==='phys'?'math':'phys';
  let label=toSub==='phys'?'Vật lý':'Toán';
  if(!confirm('Chuyển video này sang môn '+label+'?'))return;
  let items=ldvlYtAllItems(sub).slice();
  let i=items.findIndex(function(x){return ldvlYtSameId(x.id,id);});
  if(i<0){alert('Không tìm thấy video.');return;}
  let it=items.splice(i,1)[0];
  let other=ldvlYtAllItems(toSub).slice();
  other.unshift(it);
  ldvlYtPersist(sub,items);
  ldvlYtPersist(toSub,other);
  ldvlYtRenderList(sub);
  ldvlYtRenderList(toSub);
  ldvlYtSaveServer();
  ldvlStudentYtRender();
  alert('Đã chuyển sang môn '+label+'.');
}
function ldvlYtAdd(sub){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return;}
  let pfx=sub==='phys'?'yt-p':'yt-m';
  let name=String((document.getElementById(pfx+'-name')||{}).value||'').trim();
  let url=String((document.getElementById(pfx+'-url')||{}).value||'').trim();
  let quyen=String((document.getElementById(pfx+'-quyen')||{}).value||'FREE').trim();
  let lop=String((document.getElementById(pfx+'-lop')||{}).value||'').trim();
  /* Nếu chỉ dán link vào ô tên (màn hẹp / cũ), tự nhận là URL */
  if(!url&&ldvlYtExtractId(name)){url=name;name='';}
  if(!url&&name&&/^https?:\/\//i.test(name)){url=name;name='';}
  let vid=ldvlYtExtractId(url);
  if(!vid){alert('Dán link YouTube vào ô «Link YouTube» (watch / youtu.be / shorts).');let ue=document.getElementById(pfx+'-url');if(ue)ue.focus();return;}
  if(!name)name='Video '+vid;
  if(!lop){alert('Chọn lớp cho video.');return;}
  let row=ldvlYtNormItem({id:Date.now(),name,url,video_id:vid,quyen,lop,at:new Date().toISOString()});
  let items=ldvlYtAllItems(sub).slice();
  let editId=window.LDVL_YT_EDIT_ID|0;
  if(editId&&window.LDVL_YT_EDIT_SUB===sub){
    let i=items.findIndex(function(x){return ldvlYtSameId(x.id,editId);});
    row.id=editId;
    if(i>=0)items[i]=Object.assign({},items[i],row);
    else items.unshift(row);
    ldvlYtCancelEdit(sub);
  }else{
    items.unshift(row);
    let ni=document.getElementById(pfx+'-name'),ui=document.getElementById(pfx+'-url');
    if(ni)ni.value='';if(ui)ui.value='';
  }
  window.LDVL_STUDENT_YT_LOP=lop;
  try{localStorage.setItem('LDVL_YT_LOP',lop);}catch(e){}
  ldvlYtPersist(sub,items);
  ldvlYtRenderList(sub);
  let btn=document.getElementById(pfx+'-add-btn');
  if(btn){btn.disabled=true;btn.textContent='💾 Đang lưu…';}
  ldvlYtSaveServer().then(function(ok){
    if(btn){btn.disabled=false;ldvlYtSyncEditUi(sub);}
    if(typeof ldvlStudentYtRender==='function')ldvlStudentYtRender();
    if(editId)alert(ok?'✅ Đã cập nhật video.':'⚠ Đã sửa trên máy nhưng lưu server thất bại.');
    else alert(ok?'✅ Đã thêm video YouTube.':'⚠ Đã thêm trên máy nhưng lưu server thất bại.');
  });
}
function ldvlYtDelete(sub,id){
  if(!confirm('Xóa video này khỏi danh sách?'))return;
  let items=ldvlYtAllItems(sub).filter(function(x){return !ldvlYtSameId(x.id,id);});
  ldvlYtPersist(sub,items);
  ldvlYtRenderList(sub);
  ldvlYtSaveServer();
  if(typeof ldvlStudentYtRender==='function')ldvlStudentYtRender();
}
function openYtFs(embedUrl,title,ctx){
  ctx=ctx||{};
  try{if(typeof closePdfFs==='function')closePdfFs();}catch(e){}
  let watchUrl=ctx.watchUrl||'';
  let vid=ctx.video_id||ldvlYtExtractId(watchUrl)||ldvlYtExtractId(embedUrl);
  if(!embedUrl&&vid)embedUrl=ldvlYtEmbed(vid);
  if(!watchUrl&&vid)watchUrl='https://www.youtube.com/watch?v='+vid;
  window.LDVL_YT_FS={items:ctx.items||[],idx:ctx.idx|0,url:watchUrl,sub:ctx.sub||'',video_id:vid||''};
  let scr=document.getElementById('yt-fs-scr');
  let fr=document.getElementById('yt-fs-frame');
  let tt=document.getElementById('yt-fs-title');
  let ct=document.getElementById('yt-fs-counter');
  let newt=document.getElementById('yt-fs-newt');
  if(!scr){
    if(watchUrl)window.open(watchUrl,'_blank','noopener');
    else alert('Không tìm thấy khung phát video.');
    return;
  }
  if(tt)tt.textContent=title||'Video YouTube';
  if(fr){
    fr.removeAttribute('srcdoc');
    fr.src=embedUrl||'about:blank';
  }
  scr.classList.add('on');
  try{document.body.appendChild(scr);}catch(e){}
  document.body.style.overflow='hidden';
  document.documentElement.style.overflow='hidden';
  let items=window.LDVL_YT_FS.items||[];
  let idx=window.LDVL_YT_FS.idx|0;
  if(ct)ct.textContent=items.length?(idx+1)+'/'+items.length:'';
  let prev=document.getElementById('yt-fs-prev');
  let next=document.getElementById('yt-fs-next');
  if(prev)prev.disabled=!items.length||idx<=0;
  if(next)next.disabled=!items.length||idx>=items.length-1;
  function openExternal(){
    let u=window.LDVL_YT_FS.url||watchUrl||'';
    if(u)window.open(u,'_blank','noopener');
    else alert('Không có link YouTube.');
  }
  if(newt)newt.onclick=openExternal;
  /* Một số video (mix/radio/chặn nhúng) iframe trắng — nhắc mở tab YouTube */
  try{
    clearTimeout(window.__LDVL_YT_EMBED_TIP);
    window.__LDVL_YT_EMBED_TIP=setTimeout(function(){
      if(!document.getElementById('yt-fs-scr')||!document.getElementById('yt-fs-scr').classList.contains('on'))return;
    },800);
  }catch(e){}
}
function closeYtFs(){
  let scr=document.getElementById('yt-fs-scr');
  let fr=document.getElementById('yt-fs-frame');
  if(fr){fr.src='about:blank';fr.removeAttribute('srcdoc');}
  if(scr)scr.classList.remove('on');
  document.body.style.overflow='';
  document.documentElement.style.overflow='';
  window.LDVL_YT_FS={items:[],idx:0,url:'',sub:'',video_id:''};
}
function ldvlYtFsNav(dir){
  let st=window.LDVL_YT_FS||{};
  let items=st.items||[];
  let ni=(st.idx|0)+(dir|0);
  if(ni<0||ni>=items.length)return;
  let it=items[ni];
  if(!it)return;
  openYtFs(ldvlYtEmbed(it.video_id)||it.embed,it.name||'Video YouTube',{sub:st.sub,idx:ni,items:items,watchUrl:it.url,video_id:it.video_id});
}
function ldvlYtOpen(sub,idx){
  let items=ldvlYtAllItems(sub).filter(ldvlYtCanOpen);
  let it=items[idx|0];
  if(!it||!it.video_id){alert('Không mở được video này (quyền hoặc link lỗi).');return;}
  openYtFs(ldvlYtEmbed(it.video_id),it.name||'Video YouTube',{sub:sub,idx:idx|0,items:items,watchUrl:it.url,video_id:it.video_id});
}
function ldvlYtOpenById(sub,id){
  try{
    sub=String(sub||'math');
    id=String(id==null?'':id);
    let all=ldvlYtAllItems(sub);
    let it=all.find(function(x){return ldvlYtSameId(x.id,id);});
    if(!it){alert('Không tìm thấy video.');return;}
    if(!ldvlYtCanOpen(it)){alert('Video này cần quyền VIP/SVIP.');return;}
    let vid=String(it.video_id||'').trim()||ldvlYtExtractId(it.url||'');
    if(!vid){alert('Link YouTube không hợp lệ — bấm Sửa và dán lại link.');return;}
    /* Playlist theo cùng lớp với video đang mở (không bị kẹt vì bộ lọc tab lớp) */
    let playlist=all.filter(function(x){
      if(!ldvlYtCanOpen(x))return false;
      if(!it.lop)return true;
      return String(x.lop||'')===String(it.lop||'');
    });
    if(!playlist.length)playlist=all.filter(ldvlYtCanOpen);
    let idx=playlist.findIndex(function(x){return ldvlYtSameId(x.id,id);});
    if(idx<0){playlist=[it];idx=0;}
    openYtFs(ldvlYtEmbed(vid),it.name||'Video YouTube',{sub:sub,idx:idx,items:playlist,watchUrl:it.url||('https://www.youtube.com/watch?v='+vid),video_id:vid});
  }catch(e){
    console.warn('ldvlYtOpenById',e);
    alert('Lỗi mở video: '+(e.message||e));
  }
}
window.ldvlYtOpenById=ldvlYtOpenById;
window.ldvlYtOpen=ldvlYtOpen;
window.openYtFs=openYtFs;
window.closeYtFs=closeYtFs;
window.ldvlYtFsNav=ldvlYtFsNav;
if(!window.__LDVL_YT_CLICK_BOUND){
  window.__LDVL_YT_CLICK_BOUND=1;
  document.addEventListener('click',function(ev){
    let t=ev.target;
    if(!t||!t.closest)return;
    let actBtn=t.closest('[data-yt-act]');
    if(actBtn){
      ev.preventDefault();
      ev.stopPropagation();
      let act=actBtn.getAttribute('data-yt-act');
      let sub=actBtn.getAttribute('data-yt-sub')||'math';
      let id=actBtn.getAttribute('data-yt-id');
      if(act==='edit')ldvlYtEdit(sub,id);
      else if(act==='move')ldvlYtMove(sub,id);
      else if(act==='del')ldvlYtDelete(sub,id);
      return;
    }
    let card=t.closest('[data-yt-id][data-yt-sub]');
    if(!card||card.closest('[data-yt-act]'))return;
    if(card.getAttribute('data-yt-act'))return;
    let sub=card.getAttribute('data-yt-sub')||'math';
    let id=card.getAttribute('data-yt-id');
    if(!id)return;
    ev.preventDefault();
    ldvlYtOpenById(sub,id);
  },true);
}

/* ── Mô hình hóa (Python Pyodide / link nhúng) ── */
window.LDVL_STUDENT_MH_SUB='math';
window.LDVL_STUDENT_MH_LOP='';
try{window.LDVL_STUDENT_MH_LOP=localStorage.getItem('LDVL_MH_LOP')||'';}catch(e){}
window.LDVL_MH_EDIT_ID=0;
window.LDVL_MH_EDIT_SUB='';
window.LDVL_MH_CUR=null;
window.LDVL_PYODIDE=null;
window.LDVL_PYODIDE_LOADING=null;
function ldvlMhCanOpen(it){return ldvlPdfCanOpen(it);}
function ldvlMhStorageKey(sub){return 'ldvl_model_apps_'+sub;}
function ldvlMhLoad(sub){
  try{let a=JSON.parse(localStorage.getItem(ldvlMhStorageKey(sub))||'[]');return Array.isArray(a)?a:[];}catch(e){return [];}
}
function ldvlMhPersist(sub,items){
  try{localStorage.setItem(ldvlMhStorageKey(sub),JSON.stringify(items||[]));}catch(e){}
}
function ldvlMhSameId(a,b){return String(a||'')===String(b||'');}
function ldvlMhNormItem(it){
  it=it||{};
  let kind=String(it.kind||'python').toLowerCase();
  if(kind==='py')kind='python';
  if(kind==='url')kind='embed';
  if(kind!=='embed')kind='python';
  return {
    id:it.id||Date.now(),
    name:String(it.name||'').trim(),
    lop:String(it.lop||it.Lop||'').trim(),
    quyen:String(it.quyen||'FREE').trim()||'FREE',
    kind:kind,
    desc:String(it.desc||'').trim(),
    formula:String(it.formula||it.cong_thuc||'').trim(),
    code:kind==='python'?String(it.code||''):'',
    url:kind==='embed'?String(it.url||'').trim():'',
    note:String(it.note||'').trim(),
    at:it.at||''
  };
}
function ldvlMhAllItems(sub){
  let srv=(META&&META.model_apps&&META.model_apps[sub])||[];
  let serverArr=Array.isArray(srv)?srv.map(ldvlMhNormItem).filter(function(x){return x.name&&((x.kind==='python'&&x.code)||(x.kind==='embed'&&x.url));}):[];
  let local=ldvlMhLoad(sub).map(ldvlMhNormItem).filter(function(x){return x.name&&((x.kind==='python'&&x.code)||(x.kind==='embed'&&x.url));});
  if(USER&&USER.is_admin){if(local.length)return local;return serverArr;}
  if(serverArr.length)return serverArr;
  return local;
}
function ldvlMhSyncFromMeta(force){
  if(!META||!META.model_apps)return;
  try{
    ['math','phys'].forEach(function(sub){
      let rows=META.model_apps[sub];
      if(!Array.isArray(rows)||!rows.length)return;
      if(force){localStorage.setItem(ldvlMhStorageKey(sub),JSON.stringify(rows));return;}
      if(USER&&USER.is_admin){
        if(window.LDVL_MH_EDIT_ID&&window.LDVL_MH_EDIT_SUB===sub)return;
        let local=ldvlMhLoad(sub);
        if(Array.isArray(local)&&local.length)return;
      }
      localStorage.setItem(ldvlMhStorageKey(sub),JSON.stringify(rows));
    });
  }catch(e){}
}
async function ldvlMhSaveServer(){
  if(!USER||!USER.is_admin)return true;
  try{
    let payload={math:ldvlMhAllItems('math'),phys:ldvlMhAllItems('phys')};
    let j=await api('/api/admin/model-apps',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),timeoutMs:20000});
    if(j&&j.model_apps){
      META=META||{};
      META.model_apps=j.model_apps;
      ldvlMhSyncFromMeta(true);
      ldvlMhRenderList('math');ldvlMhRenderList('phys');
    }
    if(typeof ldvlStudentMhRender==='function')ldvlStudentMhRender();
    return true;
  }catch(e){
    console.warn('ldvlMhSaveServer',e);
    alert('Lưu mô hình thất bại: '+(e.message||e));
    return false;
  }
}
function ldvlMhKindUi(sub){
  let pfx=sub==='phys'?'mh-p':'mh-m';
  let kind=String((document.getElementById(pfx+'-kind')||{}).value||'python');
  let cw=document.getElementById(pfx+'-code-wrap');
  let uw=document.getElementById(pfx+'-url-wrap');
  if(cw)cw.classList.toggle('hide',kind!=='python');
  if(uw)uw.classList.toggle('hide',kind!=='embed');
}
function ldvlMhFillLopSelect(sub){
  let pfx=sub==='phys'?'mh-p':'mh-m';
  let sel=document.getElementById(pfx+'-lop');
  if(!sel)return;
  let cur=sel.value||window.LDVL_STUDENT_MH_LOP||'';
  let opts=(typeof ldvlYtLopOptions==='function')?ldvlYtLopOptions(sub):['10','11','12'];
  ldvlMhAllItems(sub).forEach(function(it){if(it.lop&&opts.indexOf(it.lop)<0)opts.push(it.lop);});
  if(cur&&opts.indexOf(cur)<0)opts=opts.concat([cur]);
  sel.innerHTML=opts.map(function(l){return '<option value="'+escAttr(l)+'">'+esc(l)+'</option>';}).join('');
  if(cur&&opts.indexOf(cur)>=0)sel.value=cur;else if(opts.length)sel.value=opts[0];
}
function ldvlMhSyncEditUi(sub){
  let pfx=sub==='phys'?'mh-p':'mh-m';
  let editing=!!(window.LDVL_MH_EDIT_ID&&window.LDVL_MH_EDIT_SUB===sub);
  let add=document.getElementById(pfx+'-add-btn');
  let cancel=document.getElementById(pfx+'-cancel-btn');
  let hint=document.getElementById(pfx+'-edit-hint');
  if(add)add.textContent=editing?'💾 Cập nhật & lưu':'💾 Lưu mô hình';
  if(cancel)cancel.classList.toggle('hide',!editing);
  if(hint){
    hint.classList.toggle('hide',!editing);
    if(editing)hint.innerHTML='Đang sửa: <b>'+esc(window.LDVL_MH_EDIT_NAME||'')+'</b>';
  }
  ldvlMhKindUi(sub);
}
function ldvlMhAdminPanelSync(){
  let adm=!!(USER&&USER.is_admin);
  let wrap=document.getElementById('ldvlMhAdminPanel');
  if(wrap)wrap.classList.toggle('hide',!adm);
  if(!adm)return;
  try{syncAdminAiProviderChrome();}catch(e){}
  let sub=window.LDVL_STUDENT_MH_SUB||'math';
  let m=document.getElementById('ldvlMhAdminMath');
  let p=document.getElementById('ldvlMhAdminPhys');
  if(m)m.classList.toggle('hide',sub!=='math');
  if(p)p.classList.toggle('hide',sub!=='phys');
  ldvlMhFillLopSelect(sub);
  ldvlMhRenderList(sub);
  ldvlMhSyncEditUi(sub);
}
function ldvlStudentMhTab(sub){
  window.LDVL_STUDENT_MH_SUB=sub||'math';
  let tm=document.getElementById('ldvlMhTabMath');
  let tp=document.getElementById('ldvlMhTabPhys');
  if(tm)tm.className=(sub==='math'?'btn':'btn2')+' ldvlMhStab'+(sub==='math'?' on':'');
  if(tp)tp.className=(sub==='phys'?'btn':'btn2')+' ldvlMhStab'+(sub==='phys'?' on':'');
  ldvlStudentMhRender();
  ldvlMhAdminPanelSync();
}
function ldvlStudentMhLop(lop){
  window.LDVL_STUDENT_MH_LOP=String(lop||'');
  try{localStorage.setItem('LDVL_MH_LOP',window.LDVL_STUDENT_MH_LOP);}catch(e){}
  ldvlStudentMhRender();
}
function ldvlMhRenderLopTabs(sub){
  let box=document.getElementById('ldvlMhLopTabs');
  if(!box)return;
  let used={};
  ldvlMhAllItems(sub).forEach(function(it){let l=String(it.lop||'').trim();if(l)used[l]=1;});
  let lops=Object.keys(used).sort(function(a,b){
    let ka=ldvlYtLopSortKey(a),kb=ldvlYtLopSortKey(b);
    return ka[0]-kb[0]||(ka[1]<kb[1]?-1:1);
  });
  if(!lops.length)lops=(typeof ldvlYtLopOptions==='function'?ldvlYtLopOptions(sub):['10','11','12']).slice(0,6);
  let cur=String(window.LDVL_STUDENT_MH_LOP||'');
  let html='<button type="button" class="btn2 ldvlYtLopBtn'+(cur?'':' on')+'" onclick="ldvlStudentMhLop(\'\')">Tất cả lớp</button>';
  html+=lops.map(function(l){
    return '<button type="button" class="btn2 ldvlYtLopBtn'+(cur===l?' on':'')+'" onclick="ldvlStudentMhLop(\''+String(l).replace(/'/g,"\\'")+'\')">'+esc(ldvlYtLopDisplay(l))+'</button>';
  }).join('');
  box.innerHTML=html;
}
function ldvlMhCardHtml(sub,it){
  let kind=it.kind==='embed'?'Link nhúng':'Python';
  let fml=it.formula?('<div class="ldvlMhFormula">'+renderRichText(it.formula)+'</div>'):'';
  return '<div class="ldvlMhCard" data-mh-sub="'+escAttr(sub)+'" data-mh-id="'+escAttr(String(it.id))+'" role="button" tabindex="0"><div class="ldvlMhIco"><i class="ti ti-atom"></i></div><div style="min-width:0;flex:1"><div class="ldvlMhName">'+esc(it.name||'Mô hình')+'</div><div class="ldvlMhMeta"><span class="tag">'+esc(ldvlYtLopDisplay(it.lop))+'</span> · <span class="tag">'+esc(kind)+'</span> · <span class="tag">'+esc(it.quyen||'FREE')+'</span></div>'+(it.desc?('<div class="ldvlMhDesc">'+esc(it.desc)+'</div>'):'')+fml+'</div></div>';
}
function ldvlStudentMhRender(){
  let box=document.getElementById('ldvlStudentMhList');
  if(!box)return;
  let sub=window.LDVL_STUDENT_MH_SUB||'math';
  ldvlMhRenderLopTabs(sub);
  let all=ldvlMhAllItems(sub);
  let openable=all.filter(ldvlMhCanOpen);
  let items=ldvlYtFilterByLop(openable,window.LDVL_STUDENT_MH_LOP);
  if(!items.length){
    let msg=!all.length?('Chưa có mô hình môn '+ldvlYtMonLabel(sub)+(USER&&USER.is_admin?' — thêm ở khối ADMIN bên dưới.':'.')):(!openable.length?('Có mô hình nhưng cần VIP/SVIP.'):('Chưa có mô hình '+ldvlYtLopDisplay(window.LDVL_STUDENT_MH_LOP)+'.'));
    box.innerHTML='<div class="muted" style="padding:12px">'+msg+'</div>';
    return;
  }
  let groups=ldvlYtGroupByLop(items);
  box.innerHTML=groups.map(function(g){
    return '<div class="ldvlYtLopHead"><span>'+esc(ldvlYtLopDisplay(g.lop))+' · '+ldvlYtMonLabel(sub)+'</span><span class="muted" style="font-weight:700">'+g.items.length+'</span></div>'+g.items.map(function(it){return ldvlMhCardHtml(sub,it);}).join('');
  }).join('');
}
function ldvlMhRenderList(sub){
  ldvlMhFillLopSelect(sub);
  let box=document.getElementById(sub==='phys'?'mh-p-list':'mh-m-list');
  if(!box)return;
  let items=ldvlMhAllItems(sub);
  if(!items.length){box.innerHTML='<div class="muted" style="padding:10px">Chưa có mô hình.</div>';return;}
  let groups=ldvlYtGroupByLop(items);
  box.innerHTML='<div class="pdf-list-head"><span>Mô hình ('+items.length+')</span><span class="pdf-list-act-h">Sửa · Xóa</span></div>'+groups.map(function(g){
    return '<div class="ldvlYtLopHead"><span>'+esc(ldvlYtLopDisplay(g.lop))+'</span><span class="muted" style="font-weight:700">'+g.items.length+'</span></div>'+g.items.map(function(it){
      return '<div class="pdf-list-row" data-mh-sub="'+escAttr(sub)+'" data-mh-id="'+escAttr(String(it.id))+'"><div class="pdf-list-ico"><i class="ti ti-atom"></i></div><div class="pdf-list-body"><div class="pdf-list-name">'+esc(it.name||'')+'</div><div class="pdf-list-meta"><span class="tag">'+esc(it.lop||'—')+'</span> · <span class="tag">'+(it.kind==='embed'?'Link':'Python')+'</span></div></div><div class="pdf-list-act"><button type="button" class="pdfBtnEdit" data-mh-act="edit" data-mh-sub="'+escAttr(sub)+'" data-mh-id="'+escAttr(String(it.id))+'">Sửa</button><button type="button" class="pdfBtnDel" data-mh-act="del" data-mh-sub="'+escAttr(sub)+'" data-mh-id="'+escAttr(String(it.id))+'">Xóa</button></div></div>';
    }).join('');
  }).join('');
}
function ldvlMhEdit(sub,id){
  if(!USER||!USER.is_admin)return;
  let it=ldvlMhAllItems(sub).find(function(x){return ldvlMhSameId(x.id,id);});
  if(!it)return;
  let pfx=sub==='phys'?'mh-p':'mh-m';
  window.LDVL_MH_EDIT_SUB=sub;window.LDVL_MH_EDIT_ID=id;window.LDVL_MH_EDIT_NAME=it.name||'';
  ldvlMhFillLopSelect(sub);
  let set=function(k,v){let el=document.getElementById(pfx+'-'+k);if(el)el.value=v;};
  set('name',it.name||'');set('desc',it.desc||'');set('formula',it.formula||'');set('kind',it.kind||'python');set('code',it.code||'');set('url',it.url||'');set('quyen',it.quyen||'FREE');
  let topic=document.getElementById(pfx+'-ai-topic');if(topic)topic.value=it.name||'';
  let li=document.getElementById(pfx+'-lop');
  if(li&&it.lop){
    if(![].some.call(li.options,function(o){return o.value===it.lop;})){let o=document.createElement('option');o.value=it.lop;o.textContent=it.lop;li.appendChild(o);}
    li.value=it.lop;
  }
  ldvlMhSyncEditUi(sub);
  if(typeof ldvlApplyHomeTab==='function')ldvlApplyHomeTab('model');
  ldvlStudentMhTab(sub);
}
function ldvlMhCancelEdit(sub){
  let pfx=sub==='phys'?'mh-p':'mh-m';
  window.LDVL_MH_EDIT_ID=0;window.LDVL_MH_EDIT_SUB='';window.LDVL_MH_EDIT_NAME='';
  ['name','desc','formula','code','url','ai-topic'].forEach(function(k){let el=document.getElementById(pfx+'-'+k);if(el)el.value='';});
  let kind=document.getElementById(pfx+'-kind');if(kind)kind.value='python';
  ldvlMhSyncEditUi(sub);
}
function ldvlMhAdd(sub){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return;}
  let pfx=sub==='phys'?'mh-p':'mh-m';
  let name=String((document.getElementById(pfx+'-name')||{}).value||'').trim();
  let desc=String((document.getElementById(pfx+'-desc')||{}).value||'').trim();
  let formula=String((document.getElementById(pfx+'-formula')||{}).value||'').trim();
  let kind=String((document.getElementById(pfx+'-kind')||{}).value||'python');
  let code=String((document.getElementById(pfx+'-code')||{}).value||'');
  let url=String((document.getElementById(pfx+'-url')||{}).value||'').trim();
  let quyen=String((document.getElementById(pfx+'-quyen')||{}).value||'FREE').trim();
  let lop=String((document.getElementById(pfx+'-lop')||{}).value||'').trim();
  if(!name){alert('Nhập tên ứng dụng.');return;}
  if(!lop){alert('Chọn lớp.');return;}
  if(kind==='python'&&!code.trim()){alert('Dán mã Python (hoặc bấm AI tạo mô hình).');return;}
  if(kind==='embed'&&!url){alert('Dán link nhúng.');return;}
  let row=ldvlMhNormItem({id:Date.now(),name,desc,formula,kind,code,url,quyen,lop,at:new Date().toISOString()});
  let items=ldvlMhAllItems(sub).slice();
  let editId=window.LDVL_MH_EDIT_ID|0;
  if(editId&&window.LDVL_MH_EDIT_SUB===sub){
    let i=items.findIndex(function(x){return ldvlMhSameId(x.id,editId);});
    row.id=editId;
    if(i>=0)items[i]=Object.assign({},items[i],row);else items.unshift(row);
    ldvlMhCancelEdit(sub);
  }else{
    items.unshift(row);
    ldvlMhCancelEdit(sub);
  }
  window.LDVL_STUDENT_MH_LOP=lop;
  try{localStorage.setItem('LDVL_MH_LOP',lop);}catch(e){}
  ldvlMhPersist(sub,items);
  ldvlMhRenderList(sub);
  ldvlMhSaveServer().then(function(ok){
    ldvlStudentMhRender();
    alert(ok?'✅ Đã lưu mô hình + công thức lên server.':'⚠ Đã lưu trên máy nhưng server lỗi.');
  });
}
async function ldvlMhAiGenerate(sub,alsoSave){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return;}
  if(typeof adminEnsureAiReady==='function'&&!adminEnsureAiReady())return;
  let pfx=sub==='phys'?'mh-p':'mh-m';
  let topicEl=document.getElementById(pfx+'-ai-topic');
  let nameEl=document.getElementById(pfx+'-name');
  let topic=String((topicEl&&topicEl.value)||(nameEl&&nameEl.value)||'').trim();
  if(!topic){alert('Nhập chủ đề AI tạo (ô trên cùng).');if(topicEl)topicEl.focus();return;}
  let lop=String((document.getElementById(pfx+'-lop')||{}).value||'').trim();
  let quyen=String((document.getElementById(pfx+'-quyen')||{}).value||'FREE').trim();
  let btn=document.getElementById(pfx+(alsoSave?'-ai-save-btn':'-ai-btn'));
  let old=btn?btn.textContent:'';
  try{
    if(btn){btn.disabled=true;btn.textContent='⏳ AI đang tạo…';}
    let body={sub:sub,topic:topic,lop:lop,quyen:quyen};
    let j=await adminAiFetch('/api/admin/ai-generate-model',body,{timeoutMs:100000});
    let it=ldvlMhNormItem(Object.assign({kind:'python',quyen:quyen},j.item||{}));
    it.code=ldvlMhSanitizeCode(it.code||'');
    if(!it.code){alert('AI chưa trả mã Python.\n'+(j.raw?('Gợi ý raw: '+String(j.raw).slice(0,180)):'Thử lại hoặc đổi Gemini/Claude.'));return;}
    let set=function(k,v){let el=document.getElementById(pfx+'-'+k);if(el)el.value=v;};
    set('name',it.name||topic);set('desc',it.desc||'');set('formula',it.formula||'');set('kind','python');set('code',it.code||'');set('url','');
    if(topicEl&&!topicEl.value.trim())topicEl.value=it.name||topic;
    ldvlMhKindUi(sub);
    if(it.lop){
      ldvlMhFillLopSelect(sub);
      let li=document.getElementById(pfx+'-lop');
      if(li){
        if(![].some.call(li.options,function(o){return o.value===it.lop;})){let o=document.createElement('option');o.value=it.lop;o.textContent=it.lop;li.appendChild(o);}
        li.value=it.lop;
      }
    }
    try{syncAdminAiProviderChrome();}catch(e){}
    if(alsoSave){
      ldvlMhAdd(sub);
    }else{
      alert('✅ AI ('+(j.provider_used||adminAiProviderShort(adminChosenAiProvider()))+') đã điền tên / công thức / mã Python.\nXem lại rồi bấm «💾 Lưu mô hình» — sau đó mở để chạy trong app.');
    }
  }catch(e){
    let msg=typeof apiNetworkErrorMsg==='function'?apiNetworkErrorMsg(e):(e.message||e);
    alert('AI tạo mô hình lỗi: '+msg+'\n\nGợi ý:\n• Kiểm tra Key AI (Gemini/Claude)\n• Đổi nhà AI rồi thử lại\n• Chủ đề ngắn gọn hơn (vd: Ném xiên lớp 10)');
  }finally{
    if(btn){btn.disabled=false;btn.textContent=old||(alsoSave?'🤖 AI tạo & lưu':'🤖 AI tạo mô hình');}
  }
}
async function ldvlMhSaveCurrentCode(){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return;}
  let cur=window.LDVL_MH_CUR;if(!cur||!cur.id){alert('Chưa mở mô hình.');return;}
  let sub=window.LDVL_MH_CUR_SUB||window.LDVL_STUDENT_MH_SUB||'math';
  let codeEl=document.getElementById('mh-fs-code');
  let code=String(codeEl?codeEl.value:cur.code||'');
  if(!String(code||'').trim()){alert('Mã Python trống.');return;}
  let items=ldvlMhAllItems(sub).slice();
  let i=items.findIndex(function(x){return ldvlMhSameId(x.id,cur.id);});
  if(i<0){alert('Không tìm thấy mô hình trong danh sách.');return;}
  items[i]=Object.assign({},items[i],{code:code,at:new Date().toISOString()});
  window.LDVL_MH_CUR=items[i];
  ldvlMhPersist(sub,items);
  let ok=await ldvlMhSaveServer();
  alert(ok?'✅ Đã lưu mã Python lên server.':'⚠ Lưu máy OK, server lỗi.');
}
function ldvlMhDelete(sub,id){
  if(!confirm('Xóa mô hình này?'))return;
  ldvlMhPersist(sub,ldvlMhAllItems(sub).filter(function(x){return !ldvlMhSameId(x.id,id);}));
  ldvlMhRenderList(sub);
  ldvlMhSaveServer();
  ldvlStudentMhRender();
}
function closeMhFs(){
  let scr=document.getElementById('mh-fs-scr');
  let fr=document.getElementById('mh-fs-frame');
  if(fr)fr.src='about:blank';
  if(scr)scr.classList.remove('on');
  document.body.style.overflow='';
  document.documentElement.style.overflow='';
  window.LDVL_MH_CUR=null;
}
function ldvlMhIsMobile(){
  try{return window.matchMedia&&window.matchMedia('(max-width:760px)').matches;}catch(e){return /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent||'');}
}
function ldvlMhSetStatus(el,msg,isErr){
  if(!el)return;
  el.textContent=msg||'';
  el.style.color=isErr?'#fca5a5':'#93c5fd';
}
function ldvlMhLoadScript(src,timeoutMs){
  timeoutMs=timeoutMs||45000;
  return new Promise(function(resolve,reject){
    let done=false;
    let s=document.createElement('script');
    s.src=src;
    s.async=true;
    s.crossOrigin='anonymous';
    let t=setTimeout(function(){
      if(done)return;done=true;
      try{s.remove();}catch(e){}
      reject(new Error('Hết thời gian tải '+src));
    },timeoutMs);
    s.onload=function(){if(done)return;done=true;clearTimeout(t);resolve();};
    s.onerror=function(){if(done)return;done=true;clearTimeout(t);try{s.remove();}catch(e){}reject(new Error('Lỗi mạng khi tải '+src));};
    document.head.appendChild(s);
  });
}
async function ldvlMhEnsurePyodide(statusEl){
  if(window.LDVL_PYODIDE)return window.LDVL_PYODIDE;
  if(window.LDVL_PYODIDE_LOADING)return window.LDVL_PYODIDE_LOADING;
  window.LDVL_PYODIDE_LOADING=(async function(){
    if(typeof WebAssembly!=='object'){
      throw new Error('Máy/trình duyệt không hỗ trợ WebAssembly — hãy mở bằng Chrome hoặc Safari (không dùng trình duyệt trong Zalo/Facebook).');
    }
    if(!navigator.onLine){
      throw new Error('Điện thoại đang offline — cần mạng để tải Python lần đầu.');
    }
    let cdns=[
      {js:'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js', index:'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/'},
      {js:'https://unpkg.com/pyodide@0.26.4/pyodide.js', index:'https://unpkg.com/pyodide@0.26.4/'},
      {js:'https://cdn.jsdelivr.net/pyodide/v0.25.1/full/pyodide.js', index:'https://cdn.jsdelivr.net/pyodide/v0.25.1/full/'}
    ];
    let lastErr=null;
    for(let i=0;i<cdns.length;i++){
      let c=cdns[i];
      try{
        ldvlMhSetStatus(statusEl,'⏳ Đang tải Python ('+(i+1)+'/'+cdns.length+') — lần đầu trên ĐT có thể 20–60s, giữ màn hình sáng…');
        if(typeof loadPyodide!=='function'){
          await ldvlMhLoadScript(c.js,50000);
        }
        if(typeof loadPyodide!=='function')throw new Error('loadPyodide chưa sẵn sàng');
        let py=await Promise.race([
          loadPyodide({indexURL:c.index}),
          new Promise(function(_,rej){setTimeout(function(){rej(new Error('Hết thời gian khởi tạo Python'));},70000);})
        ]);
        ldvlMhSetStatus(statusEl,'⏳ Đang nạp numpy + matplotlib…');
        await Promise.race([
          py.loadPackage(['numpy','matplotlib']),
          new Promise(function(_,rej){setTimeout(function(){rej(new Error('Hết thời gian nạp thư viện vẽ'));},120000);})
        ]);
        window.LDVL_PYODIDE=py;
        window.LDVL_PYODIDE_CDN=c.index;
        ldvlMhSetStatus(statusEl,'✅ Đã sẵn sàng Python.');
        return py;
      }catch(e){
        lastErr=e;
        console.warn('Pyodide CDN fail',c.js,e);
        try{delete window.loadPyodide;}catch(err){}
      }
    }
    throw lastErr||new Error('Không tải được Python trên điện thoại.');
  })();
  try{
    return await window.LDVL_PYODIDE_LOADING;
  }catch(e){
    window.LDVL_PYODIDE_LOADING=null;
    throw e;
  }finally{
    if(window.LDVL_PYODIDE)window.LDVL_PYODIDE_LOADING=null;
  }
}
function ldvlMhNormExpr(expr){
  return String(expr||'').trim()
    .replace(/,/g,'.')
    .replace(/π/g,'pi')
    .replace(/np\.pi/gi,'pi')
    .replace(/math\.pi/gi,'pi')
    .replace(/\s+/g,'');
}
function ldvlMhIsSafeExpr(expr){
  let e=ldvlMhNormExpr(expr);
  if(!e)return false;
  if(/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(e))return true;
  /* Cho phép số, pi, + - * / ( ) */
  if(!/^[0-9+\-*/().pi]+$/i.test(e))return false;
  if(/pi{2,}/i.test(e))return false;
  try{
    let js=e.replace(/pi/gi,'('+Math.PI+')');
    let n=Function('"use strict";return ('+js+')')();
    return typeof n==='number'&&isFinite(n);
  }catch(err){return false;}
}
function ldvlMhEvalExpr(expr){
  let e=ldvlMhNormExpr(expr);
  if(/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(e))return Number(e);
  let js=e.replace(/pi/gi,'('+Math.PI+')');
  return Function('"use strict";return ('+js+')')();
}
function ldvlMhToPyExpr(expr){
  let e=String(expr||'').trim().replace(/,/g,'.').replace(/π/g,'pi');
  e=e.replace(/np\.pi/gi,'pi').replace(/math\.pi/gi,'pi');
  e=e.replace(/\s+/g,' ');
  if(/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(e.replace(/\s/g,'')))return e.replace(/\s/g,'');
  /* giữ dạng đẹp: pi/2 → np.pi/2 */
  e=e.replace(/\bpi\b/gi,'np.pi').replace(/\s+/g,'');
  return e;
}
function ldvlMhDisplayExpr(raw){
  let e=String(raw||'').trim();
  e=e.replace(/np\.pi/gi,'pi').replace(/math\.pi/gi,'pi').replace(/π/g,'pi');
  return e;
}
function ldvlMhInsertPi(inputId){
  let el=document.getElementById(inputId);
  if(!el)return;
  let start=el.selectionStart|0, end=el.selectionEnd|0;
  let v=String(el.value||'');
  let ins='pi';
  /* nếu đang trống → pi ; nếu vừa gõ số → *pi */
  if(v&&/[0-9)]$/.test(v.slice(0,start).replace(/\s/g,''))&&!/pi$/i.test(v.slice(0,start).replace(/\s/g,'')))ins='*pi';
  el.value=v.slice(0,start)+ins+v.slice(end);
  let pos=start+ins.length;
  try{el.setSelectionRange(pos,pos);}catch(e){}
  el.focus();
}
function ldvlMhParseParams(code){
  code=String(code||'');
  let params=[], seen={};
  let exprTok='(?:-?\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?|np\\.pi|math\\.pi|pi|π)';
  let exprPart='(?:'+exprTok+')(?:\\s*[+\\-*/]\\s*(?:'+exprTok+'|\\([^)]*\\)|-?\\d+(?:\\.\\d+)?))*';
  function add(name,val,lineIdx,mode,extra){
    name=String(name||'').trim();
    if(!name||seen[name])return;
    if(!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name))return;
    if(['np','plt','numpy','matplotlib','math','True','False','None','pi'].indexOf(name)>=0)return;
    let raw=String(val||'').trim();
    if(!ldvlMhIsSafeExpr(raw))return;
    let n=ldvlMhEvalExpr(raw);
    seen[name]=1;
    params.push({name:name,value:n,raw:ldvlMhDisplayExpr(raw),lineIdx:lineIdx,mode:mode||'single',type:'number',extra:extra||null});
  }
  function addBool(name,val,lineIdx){
    name=String(name||'').trim();
    if(!name||seen[name])return;
    if(!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name))return;
    let checked=String(val||'').trim()==='True';
    seen[name]=1;
    params.push({name:name,value:checked,raw:checked?'True':'False',lineIdx:lineIdx,mode:'single',type:'boolean',extra:null});
  }
  let lines=code.split(/\r?\n/), allowBool=true;
  lines.forEach(function(line,idx){
    /* Chỉ nhận biến cấu hình ở đầu dòng. Bỏ qua keyword thụt vào
       như linewidth=2, fontsize=10, alpha=0.3 trong lệnh vẽ. */
    if(/^\s+/.test(line))return;
    let t=line.replace(/#.*$/,'').trim();
    if(!t)return;
    if(/^def\s+/.test(t))allowBool=false;
    let mb=t.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(True|False)\s*$/);
    if(mb){if(allowBool)addBool(mb[1],mb[2],idx);return;}
    let m=t.match(new RegExp('^([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*('+exprPart+')\\s*$','i'));
    if(m){add(m[1],m[2],idx,'single');return;}
    /* dạng a, b, c = ... (số hoặc pi) */
    let m2=t.match(/^([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)+)\s*=\s*(.+)\s*$/);
    if(m2){
      let names=m2[1].split(',').map(function(s){return s.trim();});
      let vals=m2[2].split(',').map(function(s){return s.trim();});
      if(names.length===vals.length&&vals.every(ldvlMhIsSafeExpr)){
        names.forEach(function(nm,i){add(nm,vals[i],idx,'tuple',{names:names,vals:vals.map(ldvlMhDisplayExpr)});});
      }
    }
  });
  return params;
}
function ldvlMhApplyParamsToCode(code,params){
  let lines=String(code||'').split(/\r?\n/);
  let byLine={};
  (params||[]).forEach(function(p){
    let el=document.getElementById('mh-param-'+p.name);
    if(!el)return;
    if(p.type==='boolean'){
      byLine[p.lineIdx]={mode:'single',name:p.name,val:el.checked?'True':'False'};
      return;
    }
    let typed=String(el.value||'').trim();
    if(!typed||!ldvlMhIsSafeExpr(typed))return;
    let v=ldvlMhToPyExpr(typed);
    if(!byLine[p.lineIdx])byLine[p.lineIdx]={mode:p.mode,names:[],vals:[]};
    if(p.mode==='tuple'&&p.extra){
      byLine[p.lineIdx].mode='tuple';
      byLine[p.lineIdx].names=p.extra.names.slice();
      byLine[p.lineIdx].vals=(byLine[p.lineIdx].vals.length?byLine[p.lineIdx].vals:p.extra.vals.slice());
      let ix=p.extra.names.indexOf(p.name);
      if(ix>=0)byLine[p.lineIdx].vals[ix]=v;
    }else{
      byLine[p.lineIdx]={mode:'single',name:p.name,val:v};
    }
  });
  Object.keys(byLine).forEach(function(k){
    let i=parseInt(k,10), info=byLine[k];
    if(!lines[i])return;
    let indent=(lines[i].match(/^\s*/)||[''])[0];
    if(info.mode==='tuple')lines[i]=indent+info.names.join(', ')+' = '+info.vals.join(', ');
    else lines[i]=indent+info.name+' = '+info.val;
  });
  return lines.join('\n');
}
function ldvlMhBuildParamUi(code){
  let box=document.getElementById('mh-fs-params');
  if(!box)return [];
  let params=ldvlMhParseParams(code);
  if(!params.length){
    box.classList.add('hide');
    box.innerHTML='';
    return [];
  }
  box.classList.remove('hide');
  let html='<p id="mh-fs-paramsHint">Đổi số (hoặc gõ <b>π</b>: <code>pi/2</code>, <code>2*pi</code>) rồi bấm <b>Chạy</b>.</p>';
  html+=params.map(function(p){
    let id='mh-param-'+p.name;
    if(p.type==='boolean'){
      let checked=p.value?' checked':'';
      let boolLabels={hien_x:'Li độ x',hien_v:'Vận tốc v',hien_a:'Gia tốc a'};
      let boolLabel=boolLabels[p.name]||p.name;
      return '<div class="mhParam mhParamBool"><label for="'+escAttr(id)+'">Lựa chọn</label><label class="mhParamCheckRow" for="'+escAttr(id)+'"><input id="'+escAttr(id)+'" type="checkbox"'+checked+'><span>'+esc(boolLabel)+'</span></label></div>';
    }
    return '<div class="mhParam"><label for="'+escAttr(id)+'">'+esc(p.name)+'</label><div class="mhParamRow"><input id="'+escAttr(id)+'" type="text" inputmode="text" value="'+escAttr(p.raw)+'" placeholder="vd: pi/2" autocomplete="off"><button type="button" class="mhPiBtn" title="Chèn π (pi)" onclick="ldvlMhInsertPi(\''+escAttr(id)+'\')">π</button></div></div>';
  }).join('');
  if(!ldvlMhIsMobile())html+='<button type="button" class="pdf-fs-btn" style="margin-left:auto" onclick="ldvlMhRunCurrent()"><i class="ti ti-player-play"></i> Chạy lại</button>';
  box.innerHTML=html;
  params.forEach(function(p){
    let el=document.getElementById('mh-param-'+p.name);
    if(!el)return;
    if(p.type==='boolean'){
      el.addEventListener('change',function(){ldvlMhRunCurrent();});
      return;
    }
    el.addEventListener('keydown',function(ev){if(ev.key==='Enter'){ev.preventDefault();ldvlMhRunCurrent();}});
  });
  return params;
}
window.ldvlMhInsertPi=ldvlMhInsertPi;
function ldvlMhSanitizeCode(code){
  let s=String(code||'').replace(/\r\n/g,'\n').replace(/\r/g,'\n').trim();
  if(!s)return '';
  s=s.replace(/^```(?:python|py)?\s*\n?/i,'').replace(/\n?```\s*$/,'');
  let banned=/^\s*(import|from)\s+(scipy|pandas|sympy|sklearn|tensorflow|torch|pygame|tkinter|PIL|cv2|requests|seaborn|plotly|manim|numba|jax)\b/i;
  let lines=s.split('\n').map(function(line){
    if(banned.test(line))return '# '+line+'  # không hỗ trợ trên app';
    line=line.replace(/\bplt\.show\s*\(\s*\)/g,'pass  # app tự hiện đồ thị');
    line=line.replace(/\bpyplot\.show\s*\(\s*\)/g,'pass  # app tự hiện đồ thị');
    if(/\b(input|open|exec|eval|__import__)\s*\(/.test(line))return '# '+line+'  # đã chặn';
    return line;
  });
  return lines.join('\n').trim();
}
async function ldvlMhRunCurrent(){
  let cur=window.LDVL_MH_CUR;
  if(!cur)return;
  if(cur.kind==='embed'){
    let fr=document.getElementById('mh-fs-frame');
    if(fr&&cur.url)fr.src=cur.url;
    return;
  }
  let codeEl=document.getElementById('mh-fs-code');
  let outEl=document.getElementById('mh-fs-out');
  let plotEl=document.getElementById('mh-fs-plot');
  let statusEl=document.getElementById('mh-fs-status');
  let isAdmin=!!(USER&&USER.is_admin);
  /* Học sinh không xem code — chỉ chạy bản trong bộ nhớ + tham số */
  let code=isAdmin&&codeEl?codeEl.value:(cur.code||'');
  code=ldvlMhSanitizeCode(code);
  let params=ldvlMhParseParams(code);
  if(params.length){
    code=ldvlMhApplyParamsToCode(code,params);
    cur.code=code;
    window.LDVL_MH_CUR=cur;
    if(isAdmin&&codeEl)codeEl.value=code;
    ldvlMhBuildParamUi(code);
  }
  if(outEl)outEl.textContent='';
  if(outEl)outEl.classList.add('hide');
  if(plotEl)plotEl.innerHTML='<div style="padding:18px;text-align:center;color:#64748b;font-size:13px">⏳ Đang vẽ…</div>';
  let mobile=ldvlMhIsMobile();
  let dpi=mobile?90:120;
  let figw=mobile?5.2:7;
  let figh=mobile?3.2:3.8;
  try{
    let py=await ldvlMhEnsurePyodide(statusEl);
    ldvlMhSetStatus(statusEl,'▶️ Đang chạy…');
    py.setStdout({batched:function(s){if(outEl&&String(s||'').trim()){outEl.classList.remove('hide');outEl.textContent+=(outEl.textContent?'\n':'')+s;}}});
    py.setStderr({batched:function(s){
      let msg=String(s||'').trim();
      if(!msg||/Matplotlib is currently using agg.*cannot show the figure/i.test(msg))return;
      if(outEl){outEl.classList.remove('hide');outEl.textContent+=(outEl.textContent?'\n':'')+'⚠ '+msg;}
    }});
    await py.runPythonAsync(`
import sys, io, base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
pi = float(np.pi)
plt.close('all')
plt.rcParams.update({'figure.figsize': (${figw}, ${figh}), 'figure.dpi': ${dpi}, 'savefig.dpi': ${dpi}})
`);
    try{
      await py.runPythonAsync(code);
    }catch(runErr){
      let em=String((runErr&&runErr.message)||runErr||'');
      if(/ModuleNotFoundError|No module named/i.test(em)){
        throw new Error(em+'\n\nApp chỉ hỗ trợ numpy + matplotlib. Sửa lại mã (bỏ scipy/pandas/…) rồi Chạy lại.');
      }
      throw runErr;
    }
    let figs=py.runPython(`
import io, base64, matplotlib.pyplot as plt
_out=[]
for _num in list(plt.get_fignums()):
    _fig=plt.figure(_num)
    _buf=io.BytesIO()
    _fig.savefig(_buf, format='png', dpi=${dpi}, bbox_inches='tight')
    _out.append(base64.b64encode(_buf.getvalue()).decode('ascii'))
_out
`);
    let arr=figs&&figs.toJs?figs.toJs():(figs||[]);
    if(plotEl)plotEl.innerHTML='';
    if(arr&&arr.length&&plotEl){
      arr.forEach(function(b64){
        let img=document.createElement('img');
        img.src='data:image/png;base64,'+b64;
        img.alt='Đồ thị';
        img.loading='eager';
        plotEl.appendChild(img);
      });
      try{plotEl.scrollIntoView({behavior:'smooth',block:'nearest'});}catch(e){}
    }
    ldvlMhSetStatus(statusEl,'✅ Đã chạy xong — đổi số rồi bấm Chạy lại.');
    if(outEl&&!outEl.textContent.trim()&&!(arr&&arr.length)){
      outEl.textContent='(Không có đồ thị — kiểm tra plt.plot / plt.figure trong mã)';
      outEl.classList.remove('hide');
    }
    if(outEl&&outEl.textContent.trim())outEl.classList.remove('hide');
    else if(outEl)outEl.classList.add('hide');
  }catch(e){
    console.warn('ldvlMhRunCurrent',e);
    let msg=String((e&&e.message)||e||'Lỗi');
    ldvlMhSetStatus(statusEl,'❌ Không chạy được trên máy này',true);
    if(plotEl)plotEl.innerHTML='';
    if(outEl){
      outEl.classList.remove('hide');
      outEl.textContent=msg+'\n\nGợi ý:\n• Mở Chrome/Safari (không mở trong Zalo/FB)\n• Giữ Wi‑Fi, lần đầu chờ 20–60s tải Python\n• Mã chỉ dùng numpy + matplotlib\n• ADMIN: mở mã → bỏ import lạ → Chạy lại';
    }
  }
}
function openMhFs(it,sub){
  it=ldvlMhNormItem(it||{});
  window.LDVL_MH_CUR_SUB=sub||window.LDVL_STUDENT_MH_SUB||'math';
  try{if(typeof closeYtFs==='function')closeYtFs();}catch(e){}
  try{if(typeof closePdfFs==='function')closePdfFs();}catch(e){}
  window.LDVL_MH_CUR=it;
  let scr=document.getElementById('mh-fs-scr');
  let fr=document.getElementById('mh-fs-frame');
  let py=document.getElementById('mh-fs-py');
  let tt=document.getElementById('mh-fs-title');
  let run=document.getElementById('mh-fs-run');
  let newt=document.getElementById('mh-fs-newt');
  let codeEl=document.getElementById('mh-fs-code');
  let codeDet=document.getElementById('mh-code-details');
  let outEl=document.getElementById('mh-fs-out');
  let plotEl=document.getElementById('mh-fs-plot');
  let statusEl=document.getElementById('mh-fs-status');
  let fmlEl=document.getElementById('mh-fs-formula');
  let mobile=ldvlMhIsMobile();
  if(tt)tt.textContent=it.name||'Mô hình hóa';
  if(outEl){outEl.textContent='';outEl.classList.add('hide');}
  if(plotEl)plotEl.innerHTML='';
  if(fmlEl){
    if(it.formula){fmlEl.classList.remove('hide');fmlEl.innerHTML='<b style="color:#93c5fd">Công thức:</b> '+renderRichText(it.formula);try{typeset([fmlEl]);}catch(e){}}
    else{fmlEl.classList.add('hide');fmlEl.innerHTML='';}
  }
  if(it.kind==='embed'){
    if(py)py.classList.add('hide');
    if(fr){fr.classList.remove('hide');fr.src=it.url||'about:blank';}
    if(run)run.classList.add('hide');
    if(newt){newt.classList.remove('hide');newt.onclick=function(){if(it.url)window.open(it.url,'_blank','noopener');};}
  }else{
    if(fr){fr.classList.add('hide');fr.src='about:blank';}
    if(py)py.classList.remove('hide');
    let isAdmin=!!(USER&&USER.is_admin);
    if(codeDet){
      codeDet.classList.toggle('hide',!isAdmin);
      codeDet.open=!!(isAdmin&&!mobile);
    }
    if(codeEl){
      if(isAdmin){
        codeEl.value=it.code||'';
        codeEl.readOnly=false;
        codeEl.removeAttribute('readonly');
        codeEl.oninput=function(){ldvlMhBuildParamUi(codeEl.value);};
      }else{
        codeEl.value='';
        codeEl.readOnly=true;
        codeEl.oninput=null;
      }
    }
    ldvlMhBuildParamUi(it.code||'');
    if(run)run.classList.toggle('hide',mobile);
    if(newt)newt.classList.add('hide');
    ldvlMhSetStatus(statusEl, mobile
      ? 'Đổi số → bấm Chạy (nút dưới). Lần đầu cần mạng để tải Python.'
      : 'Đổi số rồi bấm Chạy.');
  }
  if(scr){
    scr.classList.add('on');
    try{document.body.appendChild(scr);}catch(e){}
  }
  document.body.style.overflow='hidden';
  document.documentElement.style.overflow='hidden';
  if(it.kind==='python'){
    /* Mobile: chờ chút để UI hiện rồi mới tải Python (tránh đơ cảm giác “không mở”) */
    setTimeout(function(){ldvlMhRunCurrent();}, mobile?220:80);
  }
}
function ldvlMhOpenById(sub,id){
  let it=ldvlMhAllItems(sub).find(function(x){return ldvlMhSameId(x.id,id);});
  if(!it){alert('Không tìm thấy mô hình.');return;}
  if(!ldvlMhCanOpen(it)){alert('Mô hình này cần quyền VIP/SVIP.');return;}
  openMhFs(it,sub);
}
window.ldvlMhOpenById=ldvlMhOpenById;
window.openMhFs=openMhFs;
window.closeMhFs=closeMhFs;
window.ldvlMhRunCurrent=ldvlMhRunCurrent;
window.ldvlMhAdminPanelSync=ldvlMhAdminPanelSync;
window.ldvlMhAiGenerate=ldvlMhAiGenerate;
window.ldvlMhSaveCurrentCode=ldvlMhSaveCurrentCode;
window.ldvlMhAdd=ldvlMhAdd;
if(!window.__LDVL_MH_CLICK_BOUND){
  window.__LDVL_MH_CLICK_BOUND=1;
  window.__LDVL_MH_TOUCH={x:0,y:0,moved:0};
  document.addEventListener('touchstart',function(ev){
    let t=ev.touches&&ev.touches[0];
    if(!t)return;
    window.__LDVL_MH_TOUCH={x:t.clientX,y:t.clientY,moved:0};
  },{passive:true});
  document.addEventListener('touchmove',function(ev){
    let t=ev.touches&&ev.touches[0];
    if(!t||!window.__LDVL_MH_TOUCH)return;
    if(Math.abs(t.clientX-window.__LDVL_MH_TOUCH.x)>12||Math.abs(t.clientY-window.__LDVL_MH_TOUCH.y)>12)window.__LDVL_MH_TOUCH.moved=1;
  },{passive:true});
  function ldvlMhOnCardActivate(ev){
    let t=ev.target;if(!t||!t.closest)return;
    if(t.closest('#mh-fs-scr'))return;
    let act=t.closest('[data-mh-act]');
    if(act){
      ev.preventDefault();ev.stopPropagation();
      let a=act.getAttribute('data-mh-act');
      let sub=act.getAttribute('data-mh-sub')||'math';
      let id=act.getAttribute('data-mh-id');
      if(a==='edit')ldvlMhEdit(sub,id);
      else if(a==='del')ldvlMhDelete(sub,id);
      return;
    }
    let card=t.closest('[data-mh-id][data-mh-sub]');
    if(!card)return;
    if(ev.type==='touchend'){
      if(window.__LDVL_MH_TOUCH&&window.__LDVL_MH_TOUCH.moved)return;
      if(window.__LDVL_MH_TOUCH_LOCK)return;
      window.__LDVL_MH_TOUCH_LOCK=1;
      setTimeout(function(){window.__LDVL_MH_TOUCH_LOCK=0;},450);
    }else if(ev.type==='click'&&window.__LDVL_MH_TOUCH_LOCK){
      return;
    }
    let sub=card.getAttribute('data-mh-sub')||'math';
    let id=card.getAttribute('data-mh-id');
    if(!id)return;
    ev.preventDefault();
    ldvlMhOpenById(sub,id);
  }
  document.addEventListener('click',ldvlMhOnCardActivate,true);
  document.addEventListener('touchend',ldvlMhOnCardActivate,{capture:true,passive:false});
}
function ldvlShowAdminPanel(id){ldvlAdminNav(null,'ap-'+(String(id||'').replace(/^/,'')||'dash'));}
window.LDVL_ADMIN_STUDENT_MODE=false;
function ldvlApplyAdminHomeLayout(){
  let adm=USER&&USER.is_admin;
  let inQuiz=!!(document.getElementById('quiz')&&!document.getElementById('quiz').classList.contains('hide'));
  let adminArea=document.getElementById('ldvlAdminArea');
  let studentHome=document.getElementById('ldvlStudentHome');
  let viewBar=document.getElementById('ldvlAdminViewBar');
  let hdrSub=document.getElementById('ldvlHdrSub');
  if(hdrSub)hdrSub.textContent=adm?'Quản trị · ADMIN':'Toán & Vật lý';
  if(!adm||inQuiz){
    if(adminArea){adminArea.classList.add('hide');adminArea.style.display='none';}
    if(studentHome){studentHome.classList.remove('hide');studentHome.style.display='';}
    if(viewBar)viewBar.classList.add('hide');
    if(typeof ldvlQuickNavSyncVisibility==='function')ldvlQuickNavSyncVisibility();
    if(typeof ldvlUpdateStickyTopVar==='function')ldvlUpdateStickyTopVar();
    return;
  }
  if(LDVL_ADMIN_STUDENT_MODE){
    if(adminArea){adminArea.classList.add('hide');adminArea.style.display='none';}
    if(studentHome){studentHome.classList.remove('hide');studentHome.style.display='';}
  }else{
    if(adminArea){adminArea.classList.remove('hide');adminArea.style.display='';}
    if(studentHome){studentHome.classList.add('hide');studentHome.style.display='none';}
  }
  if(viewBar)viewBar.classList.add('hide');
  if(typeof ldvlAdminSubNavUpdate==='function')ldvlAdminSubNavUpdate(window.LDVL_ADMIN_PID||'ap-dash');
  if(typeof ldvlQuickNavSyncVisibility==='function')ldvlQuickNavSyncVisibility();
  if(typeof ldvlUpdateStickyTopVar==='function')ldvlUpdateStickyTopVar();
}
/* V355-FIX: KHÔNG khai báo lại các hàm ldvlStickyTopOffset / ldvlUpdateStickyTopVar /
   ldvlQuickNavSetActive / ldvlQuickNavSyncVisibility / ldvlQuickNavGo bằng "function ..."
   ở đây nữa — bản chạy thật đã được gán vào window ở IIFE phía header (ldvlQuickNavBootstrap).
   Khai báo trùng tên trước đây khiến window.<ten_ham> bị ghi đè bằng chính nó,
   dẫn tới gọi hàm là tự gọi lại chính nó vô hạn (Maximum call stack size exceeded)
   và làm các nút Trang chủ/PDF/Lọc đề/Tự luyện/Mục lục ngừng phản hồi khi bấm. */
if(typeof window.ldvlStickyTopOffset!=='function'){
  window.ldvlStickyTopOffset=function(){
    var hdr=document.getElementById('ldvlDashHdr');
    return hdr?hdr.offsetHeight:96;
  };
}
if(typeof window.ldvlUpdateStickyTopVar!=='function'){
  window.ldvlUpdateStickyTopVar=function(){
    document.documentElement.style.setProperty('--ldvl-sticky-top',window.ldvlStickyTopOffset()+'px');
  };
}
if(typeof window.ldvlQuickNavSetActive!=='function'){
  window.ldvlQuickNavSetActive=function(target){
    document.querySelectorAll('.ldvlQnavBtn').forEach(function(b){
      b.classList.toggle('on',b.getAttribute('data-ldvl-nav')===target);
    });
  };
}
if(typeof window.ldvlQuickNavSyncVisibility!=='function'){
  window.ldvlQuickNavSyncVisibility=function(){};
}
if(typeof window.ldvlQuickNavGo!=='function'){
  window.ldvlQuickNavGo=function(){};
}
if(typeof window.ldvlQnavClick!=='function'){
  window.ldvlQnavClick=window.ldvlQuickNavGo;
}
function ldvlOpenPracticeView(scrollId,monFilter){
  LDVL_ADMIN_STUDENT_MODE=true;
  ldvlApplyAdminHomeLayout();
  try{
    if(monFilter)ldvlAdminFilterMon(monFilter);
    else{refreshFilterOptions();renderCatalog();}
  }catch(e){console.warn('ldvlOpenPracticeView',e);}
  var tabMap={random:'filter',homeFilterSection:'filter',homeRandomSection:'filter',homeCatalogSection:'catalog',ldvlStudentPdfSection:'pdf',ldvlStudentYtSection:'video',ldvlStudentMhSection:'model',catalog:'catalog',adminAiGeneratePanel:'catalog'};
  var tab=tabMap[scrollId]||'catalog';
  setTimeout(function(){
    if(typeof window.ldvlApplyHomeTab==='function')window.ldvlApplyHomeTab(tab);
  },80);
}
function ldvlRefreshAdminDashboard(){
  if(!USER||!USER.is_admin)return;
  let math=0,phys=0;
  (CATALOG||[]).forEach(function(c){
    let n=parseInt(c.SoCau,10)||0;
    let m=String(c.Mon||'');
    if(/to[aá]n/i.test(m))math+=n;
    else if(/v[aậ]t|l[ií]/i.test(m))phys+=n;
  });
  let set=function(id,t){let el=document.getElementById(id);if(el)el.textContent=t;};
  let total=(META&&META.count_questions)||(math+phys);
  set('ldvlStatMath',math||'0');
  set('ldvlStatPhys',phys||'0');
  set('ldvlStatCatalog',(META&&META.count_catalog)||(CATALOG||[]).length||'0');
  set('ldvlStatAll',total||'0');
  set('ldvlStatTotal','tổng '+total);
  set('ldvlStatLoaded',META&&META.loaded_at?('Nạp: '+META.loaded_at):'');
  set('ldvlNbMath',String(math||0));
  set('ldvlNbPhys',String(phys||0));
  ldvlRenderDashSyncPanel();
  ldvlLoadAvgTimeStats(false);
}
async function ldvlLoadAvgTimeStats(force){
  if(!USER||!USER.is_admin)return;
  let box=document.getElementById('ldvlAvgTimeBox');
  let stAvg=document.getElementById('ldvlStatAvgTime');
  let stSub=document.getElementById('ldvlStatAvgTimeSub');
  if(!force&&window.__LDVL_AVG_TIME_LOADED)return;
  if(box)box.textContent='Đang đọc Ket_Qua…';
  try{
    let j=await api('/api/result-time-stats',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({}),timeoutMs:60000});
    window.__LDVL_AVG_TIME_LOADED=1;
    let n=parseInt(j.count,10)||0;
    if(stAvg)stAvg.textContent=n?(j.avg_per_correct_text&&j.avg_per_correct_text!=='—'?(j.avg_per_correct_text):(j.avg_text||'—')):'—';
    if(stSub)stSub.textContent=n?('TB/câu đúng '+(j.avg_per_correct_text||'—')+' · '+n+' lượt'):'chưa có dữ liệu thời gian';
    if(box){
      if(!n){box.innerHTML='Chưa có lượt nộp nào ghi <b>thời gian làm bài</b>. Từ lần nộp sau (luyện/kiểm tra), app sẽ tự lưu rồi tính TB.';return}
      let lines=[];
      lines.push('<div style="margin-bottom:8px"><b>TB cả bài:</b> '+esc(j.avg_text||'—')+' · <b>TB / câu đúng:</b> '+esc(j.avg_per_correct_text||'—')+' · nhanh nhất '+esc(j.min_text||'—')+' · chậm nhất '+esc(j.max_text||'—')+' · <b>'+n+'</b> lượt</div>');
      let bm=j.by_made||{};
      let keys=Object.keys(bm);
      if(keys.length){
        keys.sort(function(a,b){return (bm[b].count||0)-(bm[a].count||0)});
        lines.push('<div style="font-weight:800;margin:6px 0 4px">Theo đề (top)</div><ul style="margin:0;padding-left:18px">');
        keys.slice(0,12).forEach(function(k){
          let it=bm[k]||{};
          let title=(CATALOG.find(function(x){return x.MaDe===k})||{});
          let label=title.BaiHoc||title.De||k;
          lines.push('<li><b>'+esc(label)+'</b>: TB bài '+esc(it.avg_text||'—')+(it.avg_per_correct_text&&it.avg_per_correct_text!=='—'?(' · TB/câu đúng '+esc(it.avg_per_correct_text)):'')+' ('+(it.count||0)+' lượt)</li>');
        });
        lines.push('</ul>');
      }
      let samples=j.samples||[];
      if(samples.length){
        lines.push('<div style="font-weight:800;margin:10px 0 4px">Lượt gần đây</div><ul style="margin:0;padding-left:18px">');
        samples.slice().reverse().slice(0,8).forEach(function(s){
          lines.push('<li>'+esc(s.hoten||s.mahs||'?')+' · '+esc(s.elapsed_text||'')+' · '+esc(s.ten_de||s.made||'')+' · '+esc(s.thoi_gian||'')+'</li>');
        });
        lines.push('</ul>');
      }
      box.innerHTML=lines.join('');
    }
  }catch(e){
    if(stSub)stSub.textContent='không đọc được Ket_Qua';
    if(box)box.textContent='Không tải được TB thời gian: '+(e.message||e);
  }
}
window.LDVL_DASH_SYNC={mon:'',lop:'',chuong:'',bai:''};
function ldvlMonKind(mon){
  mon=String(mon||'').toLowerCase();
  if(/to[aá]n/.test(mon))return 'math';
  if(/v[aậ]t|l[ií]|physics/.test(mon))return 'phys';
  return '';
}
function ldvlDashScopeSources(){
  let rows=(CATALOG||[]).slice();
  try{
    if(typeof v246LessonCatalogAsCatalog==='function')rows=rows.concat(v246LessonCatalogAsCatalog());
    else if(META&&META.lesson_catalog&&META.lesson_catalog.length){
      rows=rows.concat((META.lesson_catalog||[]).map(function(x){
        return {Mon:x.Mon||'',Lop:x.Lop||'',Chuong:x.Chuong||'',BaiHoc:x.BaiHoc||''};
      }));
    }
  }catch(e){}
  return rows;
}
function ldvlBuildDashScopeTree(){
  let tree={};
  ldvlDashScopeSources().forEach(function(c){
    let mon=String(c.Mon||'').trim();
    let lop=String(c.Lop||'').trim();
    let chuong=String(c.Chuong||'').trim();
    let bai=String(c.BaiHoc||c.De||'').trim();
    if(!mon)return;
    if(!tree[mon])tree[mon]={};
    if(!lop)return;
    if(!tree[mon][lop])tree[mon][lop]={};
    if(!chuong)return;
    if(!tree[mon][lop][chuong])tree[mon][lop][chuong]={};
    if(bai&&!tree[mon][lop][chuong][bai])tree[mon][lop][chuong][bai]=1;
  });
  return tree;
}
function ldvlDashCmpKey(ka,kb){
  for(let i=0;i<Math.max(ka.length,kb.length);i++){
    let a=ka[i]!==undefined?ka[i]:'';
    let b=kb[i]!==undefined?kb[i]:'';
    if(a<b)return -1;if(a>b)return 1;
  }
  return 0;
}
function ldvlLopSortKey(lop){
  let s=normText(lop||'');
  let g=s.match(/\blop\s*(9|10|11|12)\b/)||s.match(/\b(9|10|11|12)\b/);
  if(g)return [0,parseInt(g[1],10),s];
  if(/thptqg|thpt/.test(s))return [1,0,s];
  if(/bo de|bode|de 20/.test(s)){let y=s.match(/(20\d{2})/);return [2,y?parseInt(y[1],10):0,s];}
  let lead=s.match(/^(\d{1,2})/);
  if(lead)return [0,parseInt(lead[1],10),s];
  return [3,0,s];
}
function ldvlChapterSortKey(label){
  let t=normText(label||'');
  let n=chapterNum(label);
  if(n<9999)return [0,n,t];
  if(/\bchuyen\s*de\b/.test(t))return [1,0,t];
  if(/\bung\s*dung\b/.test(t))return [2,0,t];
  return [3,0,t];
}
function ldvlLessonSortKey(label){
  let t=normText(label||'');
  let n=lessonNum(label);
  if(n<9999)return [0,n,t];
  return [1,0,t];
}
function ldvlDashSortChuong(a,b){return ldvlDashCmpKey(ldvlChapterSortKey(a),ldvlChapterSortKey(b));}
function ldvlDashSortBai(a,b){return ldvlDashCmpKey(ldvlLessonSortKey(a),ldvlLessonSortKey(b));}
function ldvlDashSetColHead(id,label,n){
  let el=document.getElementById(id);
  if(!el)return;
  el.innerHTML=label+(n>0?' <b>('+n+')</b>':'');
}
function ldvlDashSortLop(a,b){return ldvlDashCmpKey(ldvlLopSortKey(a),ldvlLopSortKey(b));}
function ldvlDashLopLabel(l){
  l=String(l||'').trim();
  let m=l.match(/l[oớ]p\s*(.+)/i);
  if(m)return m[1].trim();
  return l;
}
function ldvlDashPickBtn(level,label,selected,onclickAttr,idx){
  let cls='ldvlSyncPick ldvlSyncPick'+level+(selected?' on':'');
  let num=(idx>0)?('<span class="ldvlSyncIdx">'+idx+'</span>'):'';
  return '<button type="button" class="'+cls+'" '+onclickAttr+'>'+num+'<span class="ldvlSyncTxt">'+esc(label)+'</span></button>';
}
function ldvlDashPickMon(mon,openCatalog){
  window.LDVL_DASH_SYNC={mon:mon||'',lop:'',chuong:'',bai:''};
  ldvlRenderDashSyncPanel();
  if(openCatalog)ldvlDashOpenCatalog();
}
function ldvlDashPickLop(lop,openCatalog){
  let st=window.LDVL_DASH_SYNC||{};
  st.lop=String(lop||'');
  st.chuong='';
  st.bai='';
  window.LDVL_DASH_SYNC=st;
  ldvlRenderDashSyncPanel();
  if(openCatalog)ldvlDashOpenCatalog();
}
function ldvlDashPickChuong(chuong,openCatalog){
  let st=window.LDVL_DASH_SYNC||{};
  st.chuong=String(chuong||'');
  st.bai='';
  window.LDVL_DASH_SYNC=st;
  ldvlRenderDashSyncPanel();
  if(openCatalog)ldvlDashOpenCatalog();
}
function ldvlDashPickBai(bai){
  let st=window.LDVL_DASH_SYNC||{};
  st.bai=String(bai||'');
  window.LDVL_DASH_SYNC=st;
  ldvlRenderDashSyncPanel();
  ldvlDashOpenCatalog();
}
function ldvlDashOpenCatalog(){
  let st=window.LDVL_DASH_SYNC||{};
  if(!st.mon){alert('Chọn môn Toán hoặc Vật lý trước.');return;}
  ldvlOpenPracticeView('catalog',st.mon);
  setTimeout(function(){
    try{
      if(st.lop){setSel('fLop',st.lop);onFilterChange('lop');}
      if(st.chuong){setSel('fChuong',st.chuong);onFilterChange('chuong');}
      if(st.bai){setSel('fBaiHoc',st.bai);onFilterChange('baihoc');}
      renderCatalog();
    }catch(e){console.warn(e);}
  },350);
}
function ldvlRenderDashSyncPanel(){
  let tree=ldvlBuildDashScopeTree();
  let mons=Object.keys(tree);
  try{
    let extra=((META&&META.filters&&META.filters.Mon)||[]).filter(Boolean);
    extra.forEach(function(m){
      m=String(m||'').trim();
      if(m&&!tree[m])tree[m]={};
    });
    mons=Object.keys(tree);
  }catch(e){}
  mons.sort(function(a,b){
    let ka=ldvlMonKind(a),kb=ldvlMonKind(b);
    if(ka==='math'&&kb!=='math')return -1;
    if(ka==='phys'&&kb!=='phys'&&kb!=='math')return -1;
    if(ka==='phys'&&kb==='math')return 1;
    return String(a).localeCompare(String(b),'vi');
  });
  let st=window.LDVL_DASH_SYNC||{mon:'',lop:'',chuong:'',bai:''};
  if(!st.mon||!tree[st.mon]){
    st.mon=mons.find(function(m){return ldvlMonKind(m)==='math';})||mons.find(function(m){return ldvlMonKind(m)==='phys';})||mons[0]||'';
    st.lop='';st.chuong='';st.bai='';
    window.LDVL_DASH_SYNC=st;
  }
  let syncRow=document.getElementById('ldvlSyncRow');
  if(syncRow){
    syncRow.classList.remove('ldvlSyncMath','ldvlSyncPhys');
    let mk=ldvlMonKind(st.mon);
    if(mk==='math')syncRow.classList.add('ldvlSyncMath');
    else if(mk==='phys')syncRow.classList.add('ldvlSyncPhys');
  }
  let monCol=document.getElementById('ldvlSyncMonCol');
  if(monCol){
    if(!mons.length)monCol.innerHTML='<div class="muted" style="font-size:12px">Đang nạp đề từ GitHub / ngan-hang…</div>';
    else monCol.innerHTML=mons.map(function(m){
      let k=ldvlMonKind(m);
      let cls='ldvlSyncMonBtn tag '+(k==='phys'?'tp':'tm')+(st.mon===m?' on':'');
      return '<button type="button" class="'+cls+'" onclick="ldvlDashPickMon(\''+escAttr(m)+'\',false)"><span class="ldvlMonIco">'+(k==='phys'?'🔭':'📐')+'</span>'+esc(m)+'</button>';
    }).join('');
  }
  let lops=st.mon&&tree[st.mon]?Object.keys(tree[st.mon]).sort(ldvlDashSortLop):[];
  if(st.lop&&!lops.includes(st.lop)){st.lop='';st.chuong='';st.bai='';}
  ldvlDashSetColHead('ldvlSyncLopHead','② Lớp',lops.length);
  let lopCol=document.getElementById('ldvlSyncLopCol');
  if(lopCol){
    if(!lops.length)lopCol.innerHTML='<div class="muted">—</div>';
    else lopCol.innerHTML=lops.map(function(l,i){
      return ldvlDashPickBtn('Lop',ldvlDashLopLabel(l),st.lop===l,'onclick="ldvlDashPickLop(\''+escAttr(l)+'\',false)"',i+1);
    }).join('');
  }
  let chuongs=(st.mon&&st.lop&&tree[st.mon]&&tree[st.mon][st.lop])?Object.keys(tree[st.mon][st.lop]).sort(ldvlDashSortChuong):[];
  if(st.chuong&&!chuongs.includes(st.chuong)){st.chuong='';st.bai='';}
  ldvlDashSetColHead('ldvlSyncChuongHead','③ Chương',chuongs.length);
  let chCol=document.getElementById('ldvlSyncChuongCol');
  if(chCol){
    if(!chuongs.length)chCol.innerHTML='<div class="muted">'+(st.lop?'Không có chương':'Chọn lớp')+'</div>';
    else chCol.innerHTML=chuongs.map(function(ch,i){
      return ldvlDashPickBtn('Chuong',ch,st.chuong===ch,'onclick="ldvlDashPickChuong(\''+escAttr(ch)+'\',false)"',i+1);
    }).join('');
  }
  let bais=(st.mon&&st.lop&&st.chuong&&tree[st.mon]&&tree[st.mon][st.lop]&&tree[st.mon][st.lop][st.chuong])?Object.keys(tree[st.mon][st.lop][st.chuong]).sort(ldvlDashSortBai):[];
  if(st.bai&&!bais.includes(st.bai))st.bai='';
  window.LDVL_DASH_SYNC=st;
  ldvlDashSetColHead('ldvlSyncBaiHead','④ Bài học',bais.length);
  let baiCol=document.getElementById('ldvlSyncBaiCol');
  if(baiCol){
    if(!bais.length)baiCol.innerHTML='<div class="muted">'+(st.chuong?'Không có bài':'Chọn chương')+'</div>';
    else baiCol.innerHTML=bais.map(function(b,i){
      return ldvlDashPickBtn('Bai',b,st.bai===b,'onclick="ldvlDashPickBai(\''+escAttr(b)+'\')"',i+1);
    }).join('');
  }
  let hint=document.getElementById('ldvlDashSyncHint');
  if(hint){
    let parts=[st.mon,st.lop?('Lớp '+st.lop):'',st.chuong,st.bai].filter(Boolean);
    hint.textContent=parts.length?('Đang lọc: '+parts.join(' · ')):'Chọn môn Toán hoặc Vật lý';
  }
}
window.ldvlDashPickMon=ldvlDashPickMon;
window.ldvlDashOpenCatalog=ldvlDashOpenCatalog;
window.ldvlRenderDashSyncPanel=ldvlRenderDashSyncPanel;
function ldvlAdminFilterMon(mon){
  try{refreshFilterOptions();setSel('fMon',mon);onFilterChange('mon');renderCatalog();}catch(e){console.warn('ldvlAdminFilterMon',e);}
}
var LDVL_ADMIN_PANEL_TITLES={'ap-pdf-math':'PDF · Toán','ap-pdf-phys':'PDF · Vật lý','ap-users':'Học viên','ap-stats':'Thống kê điểm','ap-sync':'Đồng bộ Sheet','ap-tools':'Công cụ & AI Keys'};
function ldvlAdminSubNavUpdate(pid){
  window.LDVL_ADMIN_PID=pid||'';
  let bar=document.getElementById('ldvlAdminSubNav');
  if(!bar)return;
  let show=!LDVL_ADMIN_STUDENT_MODE&&pid&&pid!=='ap-dash';
  bar.classList.toggle('hide',!show);
  let t=document.getElementById('ldvlAdminSubNavTitle');
  if(t)t.textContent=LDVL_ADMIN_PANEL_TITLES[pid]||'';
  let stuBtn=document.getElementById('ldvlAdminSubNavStudentBtn');
  if(stuBtn){
    if(/^ap-pdf/.test(pid))stuBtn.innerHTML='<i class="ti ti-eye"></i> Xem PDF học sinh';
    else stuBtn.innerHTML='<i class="ti ti-eye"></i> Xem học sinh';
  }
}
function ldvlToggleAdminSidebar(){
  let sb=document.getElementById('ldvlSidebar');
  let bd=document.getElementById('ldvlSbBackdrop');
  if(!sb)return;
  let open=!sb.classList.contains('ldvlSbOpen');
  sb.classList.toggle('ldvlSbOpen',open);
  if(bd)bd.classList.toggle('on',open);
}
function ldvlCloseAdminSidebar(){
  let sb=document.getElementById('ldvlSidebar');
  let bd=document.getElementById('ldvlSbBackdrop');
  if(sb)sb.classList.remove('ldvlSbOpen');
  if(bd)bd.classList.remove('on');
}
function ldvlAdminPreviewStudent(){
  let pid=window.LDVL_ADMIN_PID||'';
  if(/^ap-pdf/.test(pid)){
    ldvlOpenPracticeView('ldvlStudentPdfSection','');
    setTimeout(function(){
      if(pid==='ap-pdf-phys')ldvlStudentPdfTab('phys');
      else ldvlStudentPdfTab('math');
      let el=document.getElementById('ldvlStudentPdfSection');
      if(el)el.scrollIntoView({behavior:'smooth',block:'start'});
    },320);
    return;
  }
  ldvlAdminNav(document.getElementById('ldvlNavPractice'),'ap-practice');
}
window.ldvlToggleAdminSidebar=ldvlToggleAdminSidebar;
window.ldvlCloseAdminSidebar=ldvlCloseAdminSidebar;
document.addEventListener('click', function(e){
  var d = document.getElementById('hdrSrcDrop');
  if(d && d.hasAttribute('open') && !d.contains(e.target)) d.removeAttribute('open');
});
window.ldvlAdminPreviewStudent=ldvlAdminPreviewStudent;
function ldvlAdminNav(btn,pid){
  if(!USER||!USER.is_admin){alert('Chỉ ADMIN.');return;}
  let home=document.getElementById('home');
  let quiz=document.getElementById('quiz');
  if(home)home.classList.remove('hide');
  if(quiz)quiz.classList.add('hide');
  if(btn){
    document.querySelectorAll('#ldvlSidebar .nb').forEach(function(b){b.classList.remove('aa');});
    btn.classList.add('aa');
  }
  pid=String(pid||'ap-dash');
  if(pid==='ap-practice'){
    window.LDVL_ADMIN_PID='ap-practice';
    ldvlOpenPracticeView('catalog','');
    return;
  }
  if(pid==='ap-random'){
    window.LDVL_ADMIN_PID='ap-random';
    ldvlOpenPracticeView('random','');
    return;
  }
  if(pid==='ap-q-math'||pid==='ap-ai-math'){
    ldvlOpenPracticeView(pid==='ap-ai-math'?'adminAiGeneratePanel':'catalog','Toán');
    if(pid==='ap-ai-math'){let p=document.getElementById('adminAiGeneratePanel');if(p)p.classList.remove('hide');try{initAdminAiGenerator();}catch(e){}}
    return;
  }
  if(pid==='ap-q-phys'||pid==='ap-ai-phys'){
    ldvlOpenPracticeView(pid==='ap-ai-phys'?'adminAiGeneratePanel':'catalog','Vật lí');
    if(pid==='ap-ai-phys'){let p=document.getElementById('adminAiGeneratePanel');if(p)p.classList.remove('hide');try{initAdminAiGenerator();}catch(e){}}
    return;
  }
  if(pid==='ap-tools'){
    window.LDVL_ADMIN_PID='ap-tools';
    LDVL_ADMIN_STUDENT_MODE=true;
    ldvlApplyAdminHomeLayout();
    let kp=document.getElementById('aiKeyPanel');
    if(kp)kp.classList.remove('hide');
    setTimeout(function(){
      if(typeof window.ldvlApplyHomeTab==='function')window.ldvlApplyHomeTab('home');
    },80);
    return;
  }
  if(pid==='ap-pdf-math'||pid==='ap-pdf-phys'){
    window.LDVL_ADMIN_PID=pid;
    LDVL_ADMIN_STUDENT_MODE=true;
    ldvlApplyAdminHomeLayout();
    ldvlCloseAdminSidebar();
    setTimeout(function(){
      if(typeof window.ldvlApplyHomeTab==='function')window.ldvlApplyHomeTab('pdf');
      ldvlStudentPdfTab(pid==='ap-pdf-phys'?'phys':'math');
    },80);
    return;
  }
  LDVL_ADMIN_STUDENT_MODE=false;
  ldvlApplyAdminHomeLayout();
  window.scrollTo({top:0,behavior:'smooth'});
  document.querySelectorAll('#am>div').forEach(function(d){
    if(!d.id)return;
    d.style.display=(d.id===pid)?'':'none';
  });
  if(pid==='ap-dash')ldvlRefreshAdminDashboard();
  if(pid==='ap-sync'){let st=document.getElementById('ldvlSyncStatus');if(st)st.textContent=META&&META.loaded_at?('Lần nạp gần nhất: '+META.loaded_at):'';}
  ldvlAdminSubNavUpdate(pid);
  ldvlCloseAdminSidebar();
  setTimeout(function(){let el=document.getElementById(pid);if(el)el.scrollIntoView({behavior:'smooth',block:'start'});},80);
}
window.ldvlAdminNav=ldvlAdminNav;
window.ldvlOpenPracticeView=ldvlOpenPracticeView;
if(window.__LDVL_NAV_PENDING){var _p=window.__LDVL_NAV_PENDING;window.__LDVL_NAV_PENDING=null;ldvlAdminNav(_p[0],_p[1]);}
window.ldvlRefreshAdminDashboard=ldvlRefreshAdminDashboard;

(function wrapRenderQuestionForDangTheory(){
  try{let old=window.renderQuestion;if(typeof old==='function'&&!old.__v303TheoryWrapped){let wrap=function(){let r=old.apply(this,arguments);setTimeout(()=>syncLessonTheoryCards(false),0);return r};wrap.__v303TheoryWrapped=true;window.renderQuestion=wrap}}catch(e){}
})();


(function ldvlDashboardUiBridge(){
  function userInitial(name){return String(name||'?').trim().charAt(0).toUpperCase()||'?';}
  function roleLabel(u){
    if(!u)return 'Học viên';
    if(u.is_admin)return 'ADMIN';
    if(u.is_svip)return 'S.VIP';
    if(u.is_vip)return 'VIP';
    if(u.is_trial)return 'Dùng thử';
    return 'FREE';
  }
  function syncDashUser(){
    try{
      let u=window.USER||{};
      let nm=String(u.hoten||u.ten||u.mahs||'').trim()||'Học viên';
      let chip=document.getElementById('ldvlUserChip');
      let iniEl=document.getElementById('ldvlUserIni');
      let nmEl=document.getElementById('ldvlUserName');
      let roleEl=document.getElementById('ldvlUserRole');
      let sb=document.getElementById('ldvlSidebar');
      if(chip)chip.classList.toggle('hide',!String(u.mahs||u.hoten||'').trim());
      if(iniEl)iniEl.textContent=userInitial(nm);
      if(nmEl)nmEl.textContent=nm;
      if(roleEl)roleEl.textContent=roleLabel(u);
      let sav=document.getElementById('ldvlSbAv');
      let sbn=document.getElementById('ldvlSbName');
      let sbr=document.getElementById('ldvlSbRole');
      if(sav)sav.textContent=userInitial(nm);
      if(sbn)sbn.textContent=nm;
      if(sbr)sbr.textContent=roleLabel(u);
      if(sb)sb.classList.toggle('hide',!u.is_admin);
      if(typeof ldvlApplyAdminHomeLayout==='function')ldvlApplyAdminHomeLayout();
      if(u.is_admin&&typeof ldvlRefreshAdminDashboard==='function')ldvlRefreshAdminDashboard();
      let themeBtn=document.getElementById('btnTheme');
      if(themeBtn){
        let dark=(document.documentElement.getAttribute('data-theme')||'')==='dark';
        themeBtn.innerHTML=dark?'<i class="ti ti-sun"></i>':'<i class="ti ti-moon"></i>';
      }
    }catch(e){console.warn('ldvlDashboardUiBridge',e);}
  }
  window.ldvlSyncDashboardUser=syncDashUser;
  let oldUpd=window.updateAdminChrome;
  window.updateAdminChrome=function(){
    if(typeof oldUpd==='function')try{oldUpd.apply(this,arguments);}catch(e){}
    syncDashUser();
  };
  let oldProf=window.renderUserAiProfile;
  window.renderUserAiProfile=function(){
    if(typeof oldProf==='function')try{oldProf.apply(this,arguments);}catch(e){}
    syncDashUser();
  };
  document.addEventListener('DOMContentLoaded',function(){setTimeout(syncDashUser,100);setTimeout(syncDashUser,1200);});
})();



/* ===== V14: Bóng chat AI nổi + ẩn thanh Công cụ AI cũ dưới câu hỏi ===== */
(function(){
  var oldRenderQuestionPedu=window.renderQuestion;
  if(typeof oldRenderQuestionPedu==='function'){
    window.renderQuestion=function(){
      var r=oldRenderQuestionPedu.apply(this,arguments);
      try{if(typeof syncFlagBtn==='function')syncFlagBtn()}catch(e){}
      try{if(typeof canViewSolutionLive==='function'&&!canViewSolutionLive()){let solEl=document.getElementById('solution');if(solEl)solEl.classList.add('hide')}}catch(e){}
      return r;
    };
  }
})();

(function bootApp(){
  try{let i=document.getElementById('info');if(i)i.textContent='Đang kết nối server…'}catch(e){}
  try{enhanceHomeColors();initTheme();initMobileQuizToolbar();if(typeof warmTranslateEnSpeech==='function')warmTranslateEnSpeech()}catch(e){console.error(e)}
  init().catch(function(e){
    let info=document.getElementById('info');if(info)info.textContent='Lỗi tải giao diện';
    let cat=document.getElementById('catalog');if(cat)cat.innerHTML='<div class="card loadErr"><b>Lỗi:</b> '+esc(e.message||e)+'</div>';
  }).finally(function(){try{sessionStorage.removeItem('LDVL_SYNTAX_RELOAD')}catch(e){}});
})();
window.__LDVL_MAIN_JS_LOADED=true;

