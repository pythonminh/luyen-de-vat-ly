(() => {
  "use strict";

  function addClass(el, className) {
    if (el) el.classList.add(className);
  }

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
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initV308, { once: true });
  } else {
    initV308();
  }
})();
