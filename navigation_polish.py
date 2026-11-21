"""Polished, consistent top navigation icons. Presentation only; no route changes."""
from flask import request
from app import app

CSS = r"""
<style id="ldvl-nav-polish">
.top .topin {gap:8px!important;align-items:center}
.top .brandbox {border:0!important;background:transparent!important;box-shadow:none!important;padding:6px 4px!important;min-width:0}
.top .brand {display:flex;align-items:center;gap:8px;font-weight:800;letter-spacing:-.025em}
.top .brandbai {font-size:12px;letter-spacing:0;font-weight:650;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.1);border-radius:8px;padding:5px 8px;margin-left:5px}
.top .nav {display:flex;align-items:center;gap:6px}
.top .nav > a,.top .nav > button,.top .nav > details > summary,
.top #htmlWarehouseQuickLink,.top .examWarehouseQuickLink,.top .view-switch-button {
 display:inline-flex!important;align-items:center;justify-content:center;gap:7px!important;
 border:1px solid rgba(255,255,255,.22)!important;border-radius:10px!important;
 background:rgba(255,255,255,.085)!important;color:#fff!important;
 font-size:13px!important;font-weight:650!important;min-height:36px;
 padding:7px 10px!important;line-height:1.2;text-decoration:none!important;
 box-shadow:none!important;white-space:nowrap;transition:background .16s,border-color .16s;
}
.top .nav > a:hover,.top .nav > button:hover,.top .nav > details > summary:hover,
.top #htmlWarehouseQuickLink:hover,.top .examWarehouseQuickLink:hover,.top .view-switch-button:hover {
 background:rgba(255,255,255,.2)!important;border-color:rgba(255,255,255,.48)!important;
}
.top .ldvl-ui-icon{width:17px;height:17px;flex:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round;fill:none;vertical-align:middle}
.top .brand .ldvl-ui-icon{width:21px;height:21px}
.top .navback,.top .fsbtn{width:36px;min-width:36px;padding:7px!important}
.top .whobar {min-width:0}
.top .who{border:1px solid rgba(255,255,255,.21)!important;border-radius:10px!important;background:rgba(255,255,255,.085)!important;padding:7px 10px!important}
.top .top-tools-list .ldvl-ui-icon{width:16px;height:16px}
.top .top-tools-list a,.top .top-tools-list button{display:flex;align-items:center;gap:8px}
.top .ldvl-icon-ready .ldvl-ui-icon{display:inline-block}
/* Hide mobile-only shortcuts in the desktop top bar; primary Kho links remain above. */
@media(min-width:1025px){
 .top #ldvlNav > a.mobile-nav-only{display:none!important}
 .top #ldvlNav > a[href="/member/exams/saved"],
 .top #ldvlNav > a[href="/member/html-menu"],
 .top #ldvlNav > a.mobile-nav-only[href="/admin/members"]{display:none!important}
}

@media(max-width:950px){.top .brand{font-size:16px}.top #htmlWarehouseQuickLink{font-size:0!important;gap:0!important;min-width:36px;padding:7px!important}.top #htmlWarehouseQuickLink .ldvl-ui-icon{width:18px;height:18px}}
@media(max-width:650px){.top .topin{gap:5px!important}.top .brandbai{padding:4px 6px}.top .nav{gap:4px}.top .nav > a,.top .nav > button,.top .nav > details > summary{padding:7px 8px!important}.top .who{max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}

/* Tight, single-row primary navigation. The window title-bar is controlled by the browser/PWA. */
.top{max-width:100%;width:100%;box-sizing:border-box}
.top .topin{
 display:flex!important;align-items:center!important;flex-wrap:nowrap!important;
 gap:6px!important;max-width:100%!important;min-width:0!important;
 box-sizing:border-box;overflow:visible!important;
}
.top .topin > *{min-width:0}
.top .brandbox{flex:0 1 auto!important;overflow:hidden!important}
.top .brand{white-space:nowrap!important;text-overflow:ellipsis;overflow:hidden}
.top #ldvlNav{min-width:0!important}
.top .nav{min-width:0}
.top .topin > #ldvlFs{flex:0 0 38px!important;width:38px!important;min-width:38px!important;height:38px!important;min-height:38px!important;margin-left:auto!important}
.top #ldvlNavToggle{flex:0 0 38px!important}
.top .top-tools-list{z-index:90}
@media (max-width:1400px){
 .top .topin{padding-inline:8px!important}
 .top .nav{gap:4px!important}
 .top .nav > a,.top .nav > button,.top .nav > details > summary,
 .top #htmlWarehouseQuickLink,.top .examWarehouseQuickLink,.top .view-switch-button{
    padding:6px 7px!important;min-height:36px!important;font-size:12px!important
 }
 .top .brand{font-size:14px!important}
 .top .whobar{max-width:150px}
 .top .sub,.top .regline{display:none!important}
}
@media (max-width:1150px){
 .top .topin{position:relative}
 /* Keep only one library shortcut in the main row; the rest remain in the menu. */
 .top .examWarehouseQuickLink,.top .view-switch-button{display:none!important}
 .top .brandbox{max-width:190px}
 .top #ldvlNav{flex:1 1 auto}
 .top .nav{max-width:100%;overflow-x:auto;scrollbar-width:none}
 .top .nav::-webkit-scrollbar{display:none}
 .top .top-tools{flex:0 0 auto}
}
@media (max-width:1024px){
 .top .topin{height:auto!important;min-height:50px;gap:5px!important}
 .top:not(.nav-open) #ldvlNav{display:none!important}
 .top #ldvlNavToggle{display:inline-flex!important;align-items:center!important;justify-content:center!important;margin-left:auto!important}
 .top.nav-open #ldvlNav{
   display:grid!important;position:absolute!important;top:100%!important;
   left:6px!important;right:6px!important;width:auto!important;max-width:none!important;
   background:#173e75!important;border:1px solid #6184b8!important;
   border-radius:10px!important;box-shadow:0 12px 24px #09274b33!important;
   max-height:min(68dvh,500px)!important;overflow-y:auto!important;
   padding:8px!important;z-index:120!important
 }
 .top .topin > #ldvlFs{order:99!important;margin-left:0!important}
}

@media(prefers-reduced-motion:reduce){.top .nav > a,.top .nav > button{transition:none}}
</style>
"""
JS = r"""
<script id="ldvl-nav-polish-script">
(function(){
const icons={
book:'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
archive:'<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v12h14V8M10 12h4"/>',
arrow:'<path d="m12 19-7-7 7-7M5 12h14"/>',
list:'<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
medal:'<circle cx="12" cy="8" r="5"/><path d="m8.5 12-2 9L12 18l5.5 3-2-9"/>',
sparkles:'<path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3ZM19 17l.7 2.3L22 20l-2.3.7L19 23l-.7-2.3L16 20l2.3-.7L19 17Z"/>',
logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
menu:'<path d="M4 7h16M4 12h16M4 17h16"/>',
monitor:'<rect x="2" y="3" width="20" height="15" rx="2"/><path d="M8 22h8M12 18v4"/>',
expand:'<path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3M21 16v3a2 2 0 0 1-2 2h-3"/>',
phone:'<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2"/>',
home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V10Z"/><path d="M9 21v-8h6v8"/>',
camera:'<path d="M14 4H9L7 7H3v13h18V7h-5l-2-3Z"/><circle cx="12" cy="13" r="3"/>',
ticket:'<path d="M2 9V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a3 3 0 0 0 0 6v4a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-4a3 3 0 0 0 0-6Z"/><path d="M13 5v2m0 4v2m0 4v2"/>'
};
function svg(name){return '<svg class="ldvl-ui-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'+(icons[name]||icons.grid)+'</svg>';}
function apply(el,name){
 if(!el||el.dataset.ldvlIcon)return;
 el.dataset.ldvlIcon='1';
 const nodes=[...el.childNodes].filter(n=>n.nodeType===3);
 let changed=false;
 for(const n of nodes){
   const original=n.nodeValue||'';
   const next=original.replace(/^[\s]*(?:📚|📖|📝|🧩|📦|▦|🏁|🤖|🚪|👤|👨‍🎓|🔐|🏠|📺|🔑|📷|🎫|☰|📲|⛶|←)\s*/u,'');
   if(next!==original){n.nodeValue=next;changed=true;break;}
 }
 if(!changed && el.querySelector('.ldvl-ui-icon'))return;
 el.insertAdjacentHTML('afterbegin',svg(name));
}
function run(){
 const root=document.querySelector('.top');if(!root)return;
 apply(root.querySelector('.brand'),'book');
 apply(root.querySelector('#htmlWarehouseQuickLink'),'grid');
 apply(root.querySelector('.examWarehouseQuickLink'),'archive');
 apply(root.querySelector('.navback'),'arrow');
 apply(root.querySelector('#ldvlNavToggle'),'menu');
 apply(root.querySelector('#ldvlInstall'),'phone');
 apply(root.querySelector('#ldvlFs'),'expand');
 apply(root.querySelector('.top-tools > summary'),'menu');
 apply(root.querySelector('.view-switch-button'),'user');
 root.querySelectorAll('#ldvlNav a, #ldvlNav button, .top-tools-list a, .top-tools-list button').forEach(el=>{
   if(el.dataset.ldvlIcon)return;
   const h=el.getAttribute('href')||'',title=(el.getAttribute('title')||'')+' '+(el.textContent||'');
   let name=/race|thi đua/i.test(h+' '+title)?'medal':/html-menu|Kho HTML/i.test(h+' '+title)?'grid':/exams\/saved|Kho đề/i.test(h+' '+title)?'archive':/member\/ai|Gemini/i.test(h+' '+title)?'sparkles':/logout|thoát/i.test(h+' '+title)?'logout':/camera|chụp/i.test(h+' '+title)?'camera':/\/xem|chiếu/i.test(h+' '+title)?'monitor':/\/admin|quản trị/i.test(h+' '+title)?'home':/\/goi|gói/i.test(h+' '+title)?'ticket':/\/member|mục lục|bài học/i.test(h+' '+title)?'book':'grid';
   apply(el,name);
 });
 root.classList.add('ldvl-icon-ready');
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
</script>
"""

@app.after_request
def polish_top_navigation(response):
    if response.status_code != 200 or response.mimetype != 'text/html' or request.path.startswith('/static/'):
        return response
    try:
        src = response.get_data(as_text=True)
        if "class='top'" not in src or 'ldvl-nav-polish-script' in src:
            return response
        if '</head>' in src: src=src.replace('</head>',CSS+'</head>',1)
        else: src=CSS+src
        if '</body>' in src: src=src.replace('</body>',JS+'</body>',1)
        else: src+=JS
        response.set_data(src)
        response.headers['Cache-Control']='no-cache'
    except Exception:
        pass
    return response
