(function () {
  "use strict";

  function addClass(el, name) {
    if (el && el.classList) el.classList.add(name);
  }

  function textOf(el) {
    return el && el.textContent ? el.textContent.trim() : "";
  }

  function findSelectByLabel(words) {
    var selects = document.querySelectorAll("select");
    var i;
    var j;
    for (i = 0; i < selects.length; i += 1) {
      var el = selects[i];
      var meta = ((el.id || "") + " " + (el.name || "") + " " + (el.getAttribute("aria-label") || "")).toLowerCase();
      for (j = 0; j < words.length; j += 1) {
        if (meta.indexOf(words[j]) >= 0) return el;
      }
      var parent = el.parentElement;
      var ptext = parent ? textOf(parent).toLowerCase() : "";
      for (j = 0; j < words.length; j += 1) {
        if (ptext.indexOf(words[j]) === 0) return el;
      }
    }
    return null;
  }

  function setSelectValue(select, wanted) {
    if (!select || !select.options) return false;
    var value = String(wanted || "").trim().toLowerCase();
    var i;
    for (i = 0; i < select.options.length; i += 1) {
      var option = select.options[i];
      var label = textOf(option).toLowerCase();
      var optionValue = String(option.value || "").trim().toLowerCase();
      if (label === value || optionValue === value || label.indexOf(value) >= 0 || optionValue.indexOf(value) >= 0) {
        select.value = option.value;
        try {
          select.dispatchEvent(new Event("change", { bubbles: true }));
        } catch (e) {
          var evt = document.createEvent("HTMLEvents");
          evt.initEvent("change", true, false);
          select.dispatchEvent(evt);
        }
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
      var controls = tabs.querySelectorAll("button,a,[role='button']");
      var i;
      for (i = 0; i < controls.length; i += 1) {
        var active = textOf(controls[i]).toLowerCase() === value.toLowerCase();
        if (active) addClass(controls[i], "v253-subject-active");
        else if (controls[i].classList) controls[i].classList.remove("v253-subject-active");
      }
    }

    if (value.toLowerCase() === "an mon" || value.toLowerCase() === "ẩn môn") {
      if (tabs) addClass(tabs, "subjectTabsHiddenV253");
      return;
    }
    if (tabs && tabs.classList) tabs.classList.remove("subjectTabsHiddenV253");

    var select = findSelectByLabel(["mon", "subject"]);
    if (setSelectValue(select, value)) {
      var buttons = document.querySelectorAll("button");
      for (var b = 0; b < buttons.length; b += 1) {
        var label = textOf(buttons[b]).toLowerCase();
        if (label.indexOf("loc de") >= 0 || label.indexOf("lọc đề") >= 0) {
          buttons[b].click();
          break;
        }
      }
    }
  };

  function closestPanel(node, className) {
    var current = node;
    var depth = 0;
    while (current && depth < 8) {
      if (current.tagName === "SECTION" || current.tagName === "ARTICLE" || current.tagName === "DIV") {
        addClass(current, className);
        return current;
      }
      current = current.parentElement;
      depth += 1;
    }
    return null;
  }

  function markLayout() {
    var nodes = document.querySelectorAll("h1,h2,h3,h4,p,label,div");
    var i;
    for (i = 0; i < nodes.length; i += 1) {
      var text = textOf(nodes[i]);
      if (!text || text.length > 180) continue;
      if (text.indexOf("Thiết lập luyện tập") >= 0) closestPanel(nodes[i], "v308-filter-panel");
      else if (text.indexOf("Tìm theo ID câu") >= 0) closestPanel(nodes[i], "v308-id-panel");
      else if (text.indexOf("Tự luyện ngẫu nhiên") >= 0) closestPanel(nodes[i], "v308-random-panel");
      else if (text === "Mục lục đề") closestPanel(nodes[i], "v308-outline-panel");
    }
  }

  function init() {
    if (!document.body) return;
    addClass(document.documentElement, "v308-ready");
    addClass(document.body, "v308-app");
    markLayout();

    var path = window.location.pathname || "/";
    if (path.indexOf("/login") === 0) addClass(document.body, "v308-login");

    try {
      var saved = localStorage.getItem("LDVL_SELECTED_SUBJECT");
      if (saved) setSelectValue(findSelectByLabel(["mon", "subject"]), saved);
    } catch (e) {}

    setTimeout(markLayout, 300);
    setTimeout(markLayout, 1200);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, false);
  else init();
}());
