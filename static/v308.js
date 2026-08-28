(() => {
  "use strict";

  function addClass(el, className) {
    if (el) el.classList.add(className);
  }

  function setSubjectSelect(subject) {
    const selects = [...document.querySelectorAll("select")];
    const select = selects.find((el) => {
      const meta = `${el.id || ""} ${el.name || ""} ${el.getAttribute("aria-label") || ""}`.toLowerCase();
      if (/môn|mon|subject/.test(meta)) return true;
      const parentText = (el.parentElement?.innerText || "").trim().toLowerCase();
      return /^môn\b|^mon\b/.test(parentText);
    });

    if (!select) return false;

    const wanted = String(subject || "").trim().toLowerCase();
    const option = [...select.options].find((opt) => {
      const text = (opt.textContent || "").trim().toLowerCase();
      const value = String(opt.value || "").trim().toLowerCase();
      return text === wanted || value === wanted || text.includes(wanted) || value.includes(wanted);
    });

    if (!option) return false;
    select.value = option.value;
    select.dispatchEvent(new Event("input", { bubbles: true }));
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  // Compatibility shim for the older V253 subject tabs.
  // The V308 redesign may still receive inline onclick="v253SelectSubject(...)" calls.
  window.v253SelectSubject = function v253SelectSubject(subject) {
    const value = String(subject || "").trim();
    if (!value) return;

    try { localStorage.setItem("LDVL_SELECTED_SUBJECT", value); } catch (_) {}

    const tabs = document.getElementById("topSubjectTabsV253");
    if (tabs) {
      tabs.querySelectorAll("button,[role='button'],a").forEach((el) => {
        const text = (el.textContent || "").trim();
        el.classList.toggle("v253-subject-active", text.toLowerCase() === value.toLowerCase());
      });
    }

    // "Ẩn môn" is a UI action, not a subject filter.
    if (/^ẩn\s*môn$/i.test(value)) {
      if (tabs) tabs.classList.add("subjectTabsHiddenV253");
      return;
    }

    if (tabs) tabs.classList.remove("subjectTabsHiddenV253");

    // Prefer the real Môn filter so the existing application logic remains in charge.
    const changed = setSubjectSelect(value);

    // If the page exposes its normal filter button, let it perform the existing filtering.
    if (changed) {
      const filterButton = [...document.querySelectorAll("button")].find((button) =>
        /lọc đề/i.test(button.textContent || "")
      );
      if (filterButton) filterButton.click();
    }

    document.dispatchEvent(new CustomEvent("ldvl:subject-change", {
      detail: { subject: value },
      bubbles: true
    }));
  };

  function initV308() {
    const html = document.documentElement;
    const body = document.body;
    if (!body) return;

    html.classList.add("v308-ready");
    body.classList.add("v308-app");

    const path = window.location.pathname.replace(/\/$/, "") || "/";
    if (path === "/login" || path.includes("login")) {
      body.classList.add("v308-login");

      const accountInput = document.querySelector(
        'input[placeholder*="HS001" i], input[placeholder*="TRIAL" i]'
      );
      const passwordInput = document.querySelector('input[type="password"]');
      const form = accountInput?.closest("form") || passwordInput?.closest("form");
      addClass(form, "v308-login-form");

      const card = form?.closest(".card, .panel, .box, .login-card, div") || form?.parentElement;
      if (card) addClass(card, "v308-login-card");

      const title = [...document.querySelectorAll("h1,h2,h3,h4,strong")].find((el) =>
        /đăng nhập học viên/i.test(el.textContent || "")
      );
      addClass(title, "v308-login-title");

      document.querySelectorAll("button").forEach((button) => {
        if (/đăng nhập/i.test(button.textContent || "")) addClass(button, "v308-login-submit");
      });
    }

    document.querySelectorAll("button").forEach((button) => {
      if (!button.getAttribute("aria-label") && !button.textContent.trim()) {
        const title = button.getAttribute("title");
        if (title) button.setAttribute("aria-label", title);
      }
    });

    document.querySelectorAll("a[href]").forEach((link) => {
      try {
        const url = new URL(link.href, window.location.origin);
        const linkPath = url.pathname.replace(/\/$/, "") || "/";
        if (linkPath === path) link.classList.add("v308-active-link");
      } catch (_) {}
    });

    // Restore the last selected subject when the redesigned page is opened.
    try {
      const saved = localStorage.getItem("LDVL_SELECTED_SUBJECT");
      if (saved && !/^ẩn\s*môn$/i.test(saved)) setSubjectSelect(saved);
    } catch (_) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initV308, { once: true });
  } else {
    initV308();
  }
})();
