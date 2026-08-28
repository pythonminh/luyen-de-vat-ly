(function () {
  "use strict";

  function addClass(el, name) {
    if (el && el.classList) el.classList.add(name);
  }

  function textOf(el) {
    return el && el.textContent ? el.textContent.trim() : "";
  }

  function findSubjectSelect() {
    var selects = document.querySelectorAll("select");
    var i;
    for (i = 0; i < selects.length; i += 1) {
      var el = selects[i];
      var meta = ((el.id || "") + " " + (el.name || "") + " " + (el.getAttribute("aria-label") || "")).toLowerCase();
      var parentText = el.parentElement ? textOf(el.parentElement).toLowerCase() : "";
      if (meta.indexOf("mon") >= 0 || meta.indexOf("subject") >= 0 || parentText.indexOf("m\u00f4n") === 0 || parentText.indexOf("mon") === 0) {
        return el;
      }
    }
    return null;
  }

  function setSubjectSelect(subject) {
    var select = findSubjectSelect();
    if (!select || !select.options) return false;

    var wanted = String(subject || "").trim().toLowerCase();
    var options = select.options;
    var i;
    for (i = 0; i < options.length; i += 1) {
      var option = options[i];
      var t = textOf(option).toLowerCase();
      var v = String(option.value || "").trim().toLowerCase();
      if (t === wanted || v === wanted || t.indexOf(wanted) >= 0 || v.indexOf(wanted) >= 0) {
        select.value = option.value;
        select.dispatchEvent(new Event("input", { bubbles: true }));
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      }
    }
    return false;
  }

  window.v253SelectSubject = function (subject) {
    var value = String(subject || "").trim();
    if (!value) return;

    try { localStorage.setItem("LDVL_SELECTED_SUBJECT", value); } catch (e) {}

    var tabs = document.getElementById("topSubjectTabsV253");
    if (tabs) {
      var controls = tabs.querySelectorAll("button,[role='button'],a");
      var i;
      for (i = 0; i < controls.length; i += 1) {
        var active = textOf(controls[i]).toLowerCase() === value.toLowerCase();
        if (active) addClass(controls[i], "v253-subject-active");
        else if (controls[i].classList) controls[i].classList.remove("v253-subject-active");
      }
    }

    if (/^\u1ea9n\s*m\u00f4n$/i.test(value)) {
      if (tabs) addClass(tabs, "subjectTabsHiddenV253");
      return;
    }

    if (tabs && tabs.classList) tabs.classList.remove("subjectTabsHiddenV253");

    if (setSubjectSelect(value)) {
      var buttons = document.querySelectorAll("button");
      for (var b = 0; b < buttons.length; b += 1) {
        if (/l\u1ecdc\s*\u0111\u1ec1/i.test(textOf(buttons[b]))) {
          buttons[b].click();
          break;
        }
      }
    }

    try {
      document.dispatchEvent(new CustomEvent("ldvl:subject-change", { detail: { subject: value }, bubbles: true }));
    } catch (e2) {}
  };

  function markHomeLayout() {
    var all = document.querySelectorAll("section,article,div");
    var i;
    for (i = 0; i < all.length; i += 1) {
      var txt = textOf(all[i]);
      if (!txt || txt.length > 900) continue;
      if (txt.indexOf("Thiết lập luyện tập") >= 0) addClass(all[i], "v308-filter-panel");
      if (txt.indexOf("Tìm theo ID câu") >= 0) addClass(all[i], "v308-id-panel");
      if (txt.indexOf("Tự luyện ngẫu nhiên") >= 0) addClass(all[i], "v308-random-panel");
      if (txt === "Mục lục đề") addClass(all[i], "v308-outline-panel");
    }

    var buttons = document.querySelectorAll("button");
    for (i = 0; i < buttons.length; i += 1) {
      var bt = textOf(buttons[i]);
      if (bt.indexOf("Bắt đầu tự luyện ngẫu nhiên") >= 0) addClass(buttons[i], "v308-primary-action");
      if (bt === "Lọc đề") addClass(buttons[i], "v308-filter-action");
      if (bt === "Tìm") addClass(buttons[i], "v308-search-action");
    }
  }

  function initV308() {
    var html = document.documentElement;
    var body = document.body;
    if (!body) return;

    addClass(html, "v308-ready");
    addClass(body, "v308-app");
    markHomeLayout();

    var path = window.location.pathname.replace(/\/$/, "") || "/";
    if (path === "/login" || path.indexOf("login") >= 0) {
      addClass(body, "v308-login");
      var accountInput = document.querySelector('input[placeholder*="HS001" i], input[placeholder*="TRIAL" i]');
      var passwordInput = document.querySelector('input[type="password"]');
      var form = accountInput ? accountInput.closest("form") : null;
      if (!form && passwordInput) form = passwordInput.closest("form");
      addClass(form, "v308-login-form");
      var card = form ? (form.closest(".card, .panel, .box, .login-card") || form.parentElement) : null;
      addClass(card, "v308-login-card");

      var headings = document.querySelectorAll("h1,h2,h3,h4,strong");
      var h;
      for (h = 0; h < headings.length; h += 1) {
        if (/\u0111\u0103ng\s*nh\u1eadp\s*h\u1ecdc\s*vi\u00ean/i.test(textOf(headings[h]))) {
          addClass(headings[h], "v308-login-title");
          break;
        }
      }

      var loginButtons = document.querySelectorAll("button");
      for (var j = 0; j < loginButtons.length; j += 1) {
        if (/\u0111\u0103ng\s*nh\u1eadp/i.test(textOf(loginButtons[j]))) addClass(loginButtons[j], "v308-login-submit");
      }
    }

    var anchors = document.querySelectorAll("a[href]");
    for (var a = 0; a < anchors.length; a += 1) {
      try {
        var url = new URL(anchors[a].href, window.location.origin);
        var linkPath = url.pathname.replace(/\/$/, "") || "/";
        if (linkPath === path) addClass(anchors[a], "v308-active-link");
      } catch (e3) {}
    }

    try {
      var saved = localStorage.getItem("LDVL_SELECTED_SUBJECT");
      if (saved && !/^\u1ea9n\s*m\u00f4n$/i.test(saved)) setSubjectSelect(saved);
    } catch (e4) {}
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initV308, { once: true });
  else initV308();
}());
