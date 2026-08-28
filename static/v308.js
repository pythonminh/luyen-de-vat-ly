(() => {
  "use strict";

  function initV308() {
    if (document.documentElement.classList.contains("v308-ready")) return;
    document.documentElement.classList.add("v308-ready");
    document.body.classList.add("v308-app");

    document.querySelectorAll("button").forEach((button) => {
      if (!button.getAttribute("aria-label") && !button.textContent.trim()) {
        const title = button.getAttribute("title");
        if (title) button.setAttribute("aria-label", title);
      }
    });

    const current = window.location.pathname.replace(/\\/$/, "") || "/";
    document.querySelectorAll("a[href]").forEach((link) => {
      try {
        const url = new URL(link.href, window.location.origin);
        const path = url.pathname.replace(/\\/$/, "") || "/";
        if (path === current) link.classList.add("v308-active-link");
      } catch (_) {}
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initV308, { once: true });
  } else {
    initV308();
  }
})();
