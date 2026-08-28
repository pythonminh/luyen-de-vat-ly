from app import app

# GitHub integration: fail loudly only on the GitHub page, never break the main app.
try:
    from github_integration import bp
    app.register_blueprint(bp)
except Exception:
    bp = None

@app.after_request
def add_github_source_link(response):
    """Expose GitHub directly in the Nguồn đề menu.

    The app UI is generated dynamically, so server-side HTML markers are not
    reliable. This middleware injects a tiny client-side helper into every
    HTML response. It adds a GitHub item to the existing Nguồn đề dropdown
    when possible, and keeps a small fallback button if the menu cannot be
    located. It never changes the main app logic.
    """
    try:
        if response.content_type and 'text/html' in response.content_type:
            text = response.get_data(as_text=True)

            helper = r'''
<script>
(function () {
  function addGitHubToSourceMenu() {
    try {
      // Do not duplicate the entry.
      if (document.querySelector('[data-ldvl-github="1"]')) return true;

      var all = document.querySelectorAll('a,button,[role="button"],div,span');
      var source = null;
      for (var i = 0; i < all.length; i++) {
        var t = (all[i].textContent || '').trim();
        if (t === 'Nguồn đề' || t === 'Nguồn đề ▾' || t === 'Nguồn đề ▼') {
          source = all[i];
          break;
        }
      }
      if (!source) return false;

      // The dropdown is normally a parent/nearby element containing the
      // existing Sheet Online / JSON Offline / Tạo JSON entries.
      var root = source.parentElement;
      for (var level = 0; level < 5 && root; level++, root = root.parentElement) {
        var links = root.querySelectorAll('a,button');
        var dropdown = null;
        for (var j = 0; j < links.length; j++) {
          var tx = (links[j].textContent || '').trim();
          if (tx.indexOf('Sheet Online') >= 0 || tx.indexOf('JSON Offline') >= 0 || tx.indexOf('Tạo JSON') >= 0) {
            dropdown = links[j].parentElement;
            break;
          }
        }
        if (dropdown) {
          var item = document.createElement('a');
          item.href = '/github';
          item.setAttribute('data-ldvl-github', '1');
          item.title = 'Đọc và quản lý dữ liệu trực tiếp từ GitHub';
          item.textContent = '🐙 GitHub';
          item.style.cssText = 'display:block;padding:10px 14px;text-decoration:none;color:inherit;cursor:pointer;';
          dropdown.insertBefore(item, dropdown.firstChild);
          return true;
        }
      }

      // Fallback: attach the link immediately after the source control.
      var item2 = document.createElement('a');
      item2.href = '/github';
      item2.setAttribute('data-ldvl-github', '1');
      item2.textContent = '🐙 GitHub';
      item2.title = 'Đọc và quản lý dữ liệu trực tiếp từ GitHub';
      item2.style.cssText = 'margin-left:6px;padding:8px 12px;border-radius:8px;background:#24292f;color:#fff;text-decoration:none;font:600 14px Arial,sans-serif;';
      if (source.parentElement) source.parentElement.appendChild(item2);
      return true;
    } catch (e) {
      return false;
    }
  }

  function run() {
    if (addGitHubToSourceMenu()) return;
    setTimeout(addGitHubToSourceMenu, 300);
    setTimeout(addGitHubToSourceMenu, 1000);
    setTimeout(addGitHubToSourceMenu, 2500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
</script>
'''

            # Keep the fixed fallback button too, so GitHub remains reachable
            # even if a future UI redesign changes the dropdown structure.
            widget = '''
<div id="ldvl-github-link" style="position:fixed;right:14px;bottom:14px;z-index:99999">
  <a href="/github" title="Đọc và quản lý dữ liệu trực tiếp từ GitHub"
     style="display:inline-block;padding:9px 14px;border-radius:10px;background:#24292f;color:#fff;text-decoration:none;font:600 14px Arial,sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.22)">
     🐙 GitHub
  </a>
</div>
'''

            if 'data-ldvl-github="1"' not in text:
                if '</body>' in text.lower():
                    idx = text.lower().rfind('</body>')
                    text = text[:idx] + helper + widget + text[idx:]
                else:
                    text += helper + widget
                response.set_data(text)
    except Exception:
        pass
    return response
