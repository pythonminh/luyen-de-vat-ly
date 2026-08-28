(function () {
  "use strict";

  function addClass(el, name) {
    if (el && el.classList) {
      el.classList.add(name);
    }
  }

  function textOf(el) {
    return el && el.textContent ? el.textContent.trim() : "";
  }

  function findSubjectSelect() {
    var list = document.querySelectorAll("select");
    var i;
    for (i = 0; i < list.length; i += 1) {
      var el = list[i];
      var meta = ((el.id || "") + " " + (el.name || "") + " " + (el.getAttribute("aria-label") || "")).toLowerCase();
      if (meta.indexOf("mon") >= 0 || meta.indexOf("subject") >= 0) {
        return el;
      }
      var parent = el.parentElement;
      var parentText = parent ? textOf(parent).toLowerCase() : "";
      if (parentText.indexOf("môn") === 0 || parentText.indexOf("mon") === 0) {
        return el;
      }
    }
    return null;
  }

  function setSubject(subject) {
    var select = findSubjectSelect();
    if (!select || !select.options) {
      return false;
    }

    var wanted = String(subject || "").trim().toLowerCase();
    var i;
    for (i = 0; i < select.options.length; i += 1) {
      var option = select.options[i];
      var label = textOf(option).toLowerCase();
      var value = String(option.value || "").trim().toLowerCase();
      if (label === wanted || value === wanted || label.indexOf(wanted) >= 0 || value.indexOf(wanted) >= 0) {
        select.value = option.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      }
    }
    return false;
  }

  window.v253SelectSubject = function (subject) {
    var value = String(subject || "").trim();
    if (!value) {
      return;
    }

    try {
      localStorage.setItem("LDVL_SELECTED_SUBJECT", value);
    } catch (ignore) {}

    var tabs = document.getElementById("topSubjectTabsV253");
    if (tabs) {
      var controls = tabs.querySelectorAll("button,a,[role='button']");
      var i;
      for (i = 0; i < controls.length; i += 1) {
        var active = textOf(controls[i]).toLowerCase() === value.toLowerCase();
        if (active) {
          addClass(controls[i], "v253-subject-active");
        } else if (controls[i].classList) {
          controls[i].classList.remove("v253-subject-active");
        }
      }
    }

    if (value.toLowerCase() === "ẩn môn" || value.toLowerCase() === "an mon") {
      if (tabs) {
        addClass(tabs, "subjectTabsHiddenV253");
      }
      return;
    }

    if (tabs && tabs.classList) {
      tabs.classList.remove("subjectTabsHiddenV253");
    }

    if (setSubject(value)) {
      var buttons = document.querySelectorAll("button");
      for (var b = 0; b < buttons.length; b += 1) {
        if (textOf(buttons[b]).toLowerCase().indexOf("lọc đề") >= 0 || textOf(buttons[b]).toLowerCase().indexOf("loc de") >= 0) {
          buttons[b].click();
          break;
        }
      }
    }
  };

  function markLayout() {
    var nodes = document.querySelectorAll("section,article,div");
    var i;
    for (i = 0; i < nodes.length; i += 1) {
      var text = textOf(nodes[i]);
      if (!text || text.length > 900) {
        continue;
      }
      if (text.indexOf("Thiết lập luyện tập") >= 0) addClass(nodes[i], "v308-filter-panel");
      if (text.indexOf("Tìm theo ID câu") >= 0) addClass(nodes[i], "v308-id-panel");
      if (text.indexOf("Tự luyện ngẫu nhiên") >= 0) addClass(nodes[i], "v308-random-panel");
      if (text === "Mục lục đề") addClass(nodes[i], "v308-outline-panel");
    }
  }

  function init() {
    if (!document.body) return;
    addClass(document.documentElement, "v308-ready");
    addClass(document.body, "v308-app");
    markLayout();

    var path = window.location.pathname || "/";
    if (path.indexOf("/login") === 0) {
      addClass(document.body, "v308-login");
    }

    try {
      var saved = localStorage.getItem("LDVL_SELECTED_SUBJECT");
      if (saved) setSubject(saved);
    } catch (ignore2) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, false);
  } else {
    init();
  }
}());
