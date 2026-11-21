/* Lớp Học Thầy Minh | compact exam HUD, question map and answer area.
   Visual navigation only; answer grading and completion remain server-managed. */
(function () {
  'use strict';
  function mount() {
    const root = document.querySelector('.vip-practice-wrap > .panel');
    if (!root || root.querySelector('.practice-three-zone')) return;
    const head = root.querySelector('.quiztop');
    const body = root.querySelector(':scope > .body');
    const source = root.querySelector('.practice-questions .pitems');
    if (!head || !body || !source) return;
    const anchors = Array.from(source.querySelectorAll('a[href^="/practice/jump/"]'));
    if (!anchors.length) return;

    const zone = document.createElement('div');
    zone.className = 'practice-three-zone';
    const aside = document.createElement('aside');
    aside.className = 'practice-index-panel';
    aside.setAttribute('aria-label', 'Mục lục câu hỏi');
    aside.dataset.expanded = 'false';
    aside.innerHTML =
      '<div class="practice-index-heading">' +
        '<h2>☷ Mục lục <small class="pidx-count"></small></h2>' +
        '<button type="button" class="practice-index-expand" aria-expanded="false" aria-controls="practiceIndexGrid" title="Mở rộng mục lục">Tất cả ⌄</button>' +
        '<button type="button" class="practice-index-collapse" aria-label="Thu gọn thanh câu hỏi" title="Thu gọn thanh câu hỏi">‹</button>' +
      '</div>' +
      '<div class="practice-index-progress" aria-hidden="true"><span></span></div>' +
      '<nav class="practice-index-grid" id="practiceIndexGrid" aria-label="Chọn câu hỏi"></nav>' +
      '<div class="practice-index-summary" aria-live="polite"></div>' +
      '<div class="practice-index-legend" aria-label="Chú thích màu câu hỏi">' +
        '<span><i></i>Chưa làm</span>' +
        '<span class="pidx-wait"><i></i>Đã chọn</span>' +
        '<span class="pidx-ok"><i></i>Đúng</span>' +
        '<span class="pidx-bad"><i></i>Sai</span>' +
      '</div>' +
      '<div class="pidx-options"></div>';

    const nav = aside.querySelector('.practice-index-grid');
    const keys = [];
    anchors.forEach(function (original, index) {
      const link = original;
      link.classList.add('pidx-link');
      link.textContent = String(index + 1);
      link.setAttribute('aria-label', 'Câu ' + (index + 1));
      link.dataset.questionIndex = String(index);
      link.title = 'Câu ' + (index + 1);
      if (link.classList.contains('pcur')) link.setAttribute('aria-current', 'step');
      nav.appendChild(link);
      keys.push({src: link, view: link});
    });

    // Use the server-rendered links as the only question-navigation controls.
    // Remove the old expandable copy after moving its links into this index.
    const oldQuestionMenu = root.querySelector('.practice-questions');
    if (oldQuestionMenu) oldQuestionMenu.remove();
    root.insertBefore(zone, body);
    zone.appendChild(aside);
    zone.appendChild(body);

    // Keep the existing timing/record controls and original zoom callbacks.
    const hud = document.createElement('section');
    hud.className = 'practice-game-hud';
    hud.setAttribute('aria-label', 'Trạng thái bài làm');
    hud.innerHTML =
      '<strong class="ph-current" aria-live="polite"></strong>' +
      '<span class="ph-done" aria-live="polite"></span>' +
      '<span class="ph-correct"></span>' +
      '<div class="ph-meters"></div>' +
      '<div class="ph-tools"></div>' +
      '<div class="ph-progress" aria-hidden="true"><span></span></div>';
    root.insertBefore(hud, zone);
    const stats = root.querySelector(':scope > .practice-mini-stats');
    if (stats) hud.querySelector('.ph-meters').appendChild(stats);
    const zoom = head.querySelector('.qzoombar');
    if (zoom) {
      zoom.setAttribute('aria-label', 'Cỡ chữ câu hỏi');
      hud.querySelector('.ph-tools').appendChild(zoom);
    }
    const filter = head.querySelector('details.practice-filters');
    // Teachers retain advanced lesson controls; students see only the question navigator.
    if (filter) {
      if (document.body.classList.contains('admin-ui')) aside.querySelector('.pidx-options').appendChild(filter);
      else filter.remove();
    }

    function refresh() {
      const done = keys.filter(x => x.view.classList.contains('pdone') || x.view.classList.contains('pwrong')).length;
      const correct = keys.filter(x => x.view.classList.contains('pdone')).length;
      const current = keys.findIndex(x => x.view.classList.contains('pcur'));
      const count = keys.length;
      aside.querySelector('.pidx-count').textContent = done + '/' + count;
      aside.querySelector('.practice-index-progress > span').style.width = (count ? 100 * done / count : 0) + '%';
      aside.querySelector('.practice-index-summary').textContent =
        'Đã làm ' + done + '/' + count + ' · Đúng ' + correct;
      hud.querySelector('.ph-current').textContent = 'Câu ' + (current >= 0 ? current + 1 : 1) + '/' + count;
      hud.querySelector('.ph-done').textContent = 'Đã làm ' + done + '/' + count;
      hud.querySelector('.ph-correct').textContent = '✓ ' + correct;
      hud.querySelector('.ph-progress > span').style.width = (count ? 100 * done / count : 0) + '%';
      keys.forEach((item, i) => {
        const status = item.view.classList.contains('pdone') ? 'Đã đúng' :
          item.view.classList.contains('pwrong') ? 'Đã sai' :
          item.view.classList.contains('pready') ? 'Đã chọn, chưa xác nhận' : 'Chưa làm';
        const on = item.view.classList.contains('pcur');
        item.view.setAttribute('aria-label', 'Câu ' + (i + 1) + ' — ' + status + (on ? ', đang xem' : ''));
        item.view.title = 'Câu ' + (i + 1) + ' · ' + status;
      });
    }
    function currentItem() {
      return keys.find(x => x.view.classList.contains('pcur'));
    }
    function getReady() {
      const q = document.getElementById('q');
      if (!q) return false;
      const type = window.practiceKind || '';
      if (type === 'TN') return !!q.querySelector('input[name="a"]:checked');
      if (type === 'DS') {
        const names = Array.from(new Set(Array.from(q.querySelectorAll('.tf input[type="radio"]'), x => x.name)));
        return names.length > 0 && names.every(n => !!q.querySelector('input[name="' + n + '"]:checked'));
      }
      const input = q.querySelector('#ans');
      return !!(input && input.value.trim());
    }
    function markPending(ready) {
      const item = currentItem();
      if (item && !item.view.classList.contains('pdone') && !item.view.classList.contains('pwrong')) {
        [item.src, item.view].forEach(a => a.classList.toggle('pready', !!ready));
        refresh();
      }
    }
    const question = document.getElementById('q');
    if (question) {
      question.addEventListener('change', () => markPending(getReady()));
      question.addEventListener('input', () => markPending(getReady()));
    }
    window.practiceMarkAnswered = function(ok) {
      const item = currentItem();
      if (!item) return;
      [item.src, item.view].forEach(a => {
        a.classList.remove('pready', 'pdone', 'pwrong');
        a.classList.add(ok ? 'pdone' : 'pwrong');
      });
      refresh();
    };

    const expand = aside.querySelector('.practice-index-expand');
    function setExpanded(open) {
      aside.dataset.expanded = open ? 'true' : 'false';
      expand.setAttribute('aria-expanded', open ? 'true' : 'false');
      expand.textContent = open ? 'Thu gọn ⌃' : 'Tất cả ⌄';
      expand.title = open ? 'Thu gọn mục lục' : 'Hiển thị toàn bộ mục lục';
    }
    expand.addEventListener('click', () => setExpanded(aside.dataset.expanded !== 'true'));
    const collapse = aside.querySelector('.practice-index-collapse');
    collapse.addEventListener('click', () => {
      const isCollapsed = zone.classList.toggle('is-index-collapsed');
      collapse.textContent = isCollapsed ? '›' : '‹';
      collapse.title = isCollapsed ? 'Mở thanh câu hỏi' : 'Thu gọn thanh câu hỏi';
      collapse.setAttribute('aria-label', collapse.title);
    });

    // Only this question index remains; no duplicate mobile modal or bottom navigation.
    document.body.classList.add('practice-compact-ready');
    refresh();

    const active = currentItem();
    if (active) requestAnimationFrame(function () {
      const grid = aside.querySelector('.practice-index-grid');
      if (!grid || aside.dataset.expanded === 'true') return;
      const b = active.view.getBoundingClientRect();
      const g = grid.getBoundingClientRect();
      if (window.matchMedia('(max-width:799px)').matches && (b.left < g.left || b.right > g.right)) {
        grid.scrollLeft += b.left - g.left - (g.width - b.width) / 2;
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
