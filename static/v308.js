(() => {
  "use strict";

  function initV308() {
    if (document.documentElement.classList.contains("v308-ready")) return;
    document.documentElement.classList.add("v308-ready");

    // Mark the existing application without replacing its DOM. This keeps all
    // current Flask routes, forms, APIs, timers and question logic intact.
    document.body.classList.add("v308-app");

    // Give buttons a consistent accessible label when they only contain an icon.
    document.querySelectorAll("button").forEach((button) => {
      if (!button.getAttribute("aria-label") && !button.textContent.trim()) {
        const title = button.getAttribute("title");
        if (title) button.setAttribute("aria-label", title);
      }
    });

    // Add a small visual cue to the active navigation item when a nav link
    // points to the current URL. Existing navigation remains untouched.
    const current = window.location.pathname.replace(/\\/$/, "") || "/";
    document.querySelectorAll("a[href]").forEach((link) => {
      try {
        const url = new URL(link.href, window.location.origin);
        const path = url.pathname.replace(/\\/$/, "") || "/";
        if (path === current) link.classList.add("v308-active-link");
      } catch (_) {
        // Ignore malformed/non-navigation links from the legacy page.
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initV308, { once: true });
  } else {
    initV308();
  }
})();
