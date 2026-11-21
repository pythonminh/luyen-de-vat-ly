/* Fullscreen / mobile toolbar: keeps the exit button accessible. */
(function(){
  "use strict";
  function setup(){
    var button=document.getElementById("ldvlFs");
    var nav=document.getElementById("ldvlNav");
    if(!button||!nav||!document.body)return;
    // Originally the fullscreen button was hidden inside the collapsed mobile menu.
    nav.insertAdjacentElement("afterend",button);
    button.setAttribute("aria-label","Toàn màn hình");
    function isNativeFull(){
      return !!(document.fullscreenElement||document.webkitFullscreenElement);
    }
    function sync(){
      var active=isNativeFull()||document.body.classList.contains("ldvl-focus-view");
      button.setAttribute("aria-pressed",active?"true":"false");
      button.textContent=active?"⤢":"⛶";
      button.title=active?"Thoát toàn màn hình":"Toàn màn hình";
      button.setAttribute("aria-label",button.title);
      if(window.ldvlSyncHeaderH)window.ldvlSyncHeaderH();
    }
    function fallback(){
      document.body.classList.add("ldvl-focus-view");
      sync();
    }
    window.ldvlToggleFs=function(){
      var el=document.documentElement;
      if(isNativeFull()){
        var quit=document.exitFullscreen||document.webkitExitFullscreen;
        if(quit){
          try{var p=quit.call(document);if(p&&p.catch)p.catch(sync);}
          catch(err){sync();}
        }
        return;
      }
      if(document.body.classList.contains("ldvl-focus-view")){
        document.body.classList.remove("ldvl-focus-view");
        sync();return;
      }
      var enter=el.requestFullscreen||el.webkitRequestFullscreen;
      if(!enter){fallback();return;}
      try{
        var result=enter.call(el);
        if(result&&result.catch)result.catch(fallback);
        else window.setTimeout(sync,50);
      }catch(err){fallback();}
    };
    document.addEventListener("fullscreenchange",sync);
    document.addEventListener("webkitfullscreenchange",sync);
    sync();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",setup);
  else setup();
})();
