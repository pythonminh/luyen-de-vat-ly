(() => {
  'use strict';
  const cfg = window.RACE_CONFIG, $ = id => document.getElementById(id);
  let lastHostShown;
  let state, questions = [], answers = {}, pos = 0, loaded = false, rendered = '', queue = Promise.resolve(), serverOffset = 0, submitting = false, saveTimer, controlsKey = '', gradingKey = '', resultsKey = '', joinName = cfg.name || '';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clock = seconds => { seconds = Math.max(0, Math.floor(seconds)); return String(Math.floor(seconds / 60)).padStart(2, '0') + ':' + String(seconds % 60).padStart(2, '0'); };
  const note = text => { $('raceNotice').textContent = text; };
  const raceRoot = document.querySelector?.('.wrap.race');
  document.body?.classList.add('race-page');
  let fitPending = false, mathSizes = new WeakMap();
  function fitMath() {
    if (!raceRoot?.querySelectorAll) return;
    raceRoot.querySelectorAll('mjx-container').forEach(math => {
      const parent = math.parentElement, formula = math.querySelector('mjx-math') || math;
      if (!parent || !formula.getBoundingClientRect) return;
      const available = Math.min(parent.clientWidth || 0, raceRoot.clientWidth - 20);
      if (available <= 0 || mathSizes.get(math) === available) return;
      mathSizes.set(math, available);
      math.style.fontSize = '100%';
      const width = formula.getBoundingClientRect().width;
      if (available > 0 && width > available) math.style.fontSize = Math.max(1, Math.floor(available / width * 99)) + '%';
    });
  }
  function scheduleFit() {
    if (fitPending) return;
    fitPending = true;
    const next = window.requestAnimationFrame ? fn => window.requestAnimationFrame(fn) : fn => setTimeout(fn, 0);
    next(() => { fitPending = false; fitMath(); });
  }
  if (raceRoot) {
    if (window.MutationObserver) new MutationObserver(scheduleFit).observe(raceRoot, {childList:true, subtree:true});
    raceRoot.addEventListener('toggle', scheduleFit, true);
    window.addEventListener('resize', scheduleFit);
    window.addEventListener('load', scheduleFit);
    window.addEventListener('orientationchange', scheduleFit);
    document.fonts?.addEventListener('loadingdone', () => { mathSizes = new WeakMap(); scheduleFit(); });
    scheduleFit();
  }
  function typeset() {
    if (window.ldvlArmTikz) window.ldvlArmTikz($('raceQuestion'));
    if (window.ldvlSplitPics) window.ldvlSplitPics($('raceQuestion'));
    if (window.ldvlTypeset) window.ldvlTypeset($('raceQuestion'));
    else if (window.MathJax?.typesetPromise) window.MathJax.typesetPromise([$('raceQuestion')]).catch(() => {});
  }
  async function api(payload) {
    const options = payload ? {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-Race-CSRF':cfg.csrf}, body:JSON.stringify(payload)} : {credentials:'same-origin', cache:'no-store'};
    const r = await fetch('/api/race/' + encodeURIComponent(cfg.code), options);
    if (!r.ok) { let d; try { d = await r.json(); } catch (_) {} throw Error(d?.error || 'Không kết nối được. Kiểm tra đăng nhập và thử lại.'); }
    return r.json();
  }
  function enqueue(payload) {
    const task = queue.catch(() => {}).then(() => api(payload));
    queue = task;
    return task;
  }
  function button(label, run, parent) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'btn'; b.textContent = label;
    b.onclick = async () => { b.disabled = true; try { await run(); } catch (e) { note(e.message); } finally { b.disabled = false; } };
    parent.append(b); return b;
  }
  function controls() {
    const key = [state.state, state.joined, cfg.host ? state.ranking.length : '', state.capacity, state.storage?.state, state.storage?.saved_at, state.next_room_url].join(':');
    if (key === controlsKey) return;
    controlsKey = key;
    const el = $('raceControls'); el.replaceChildren();
    const status = document.createElement('div'); status.className = 'race-room-status ' + state.state; status.setAttribute('role', 'status');
    status.textContent = state.state === 'waiting' ? 'CHƯA BẮT ĐẦU · Nhập tên để nhận chỗ, chờ ADMIN bắt đầu.' : state.state === 'running' ? 'ĐANG DIỄN RA · Đồng hồ tính theo thời gian chung của lớp.' : 'ĐÃ KẾT THÚC · Bài đã nộp được giữ lại để xem kết quả.'; el.append(status);
    if (!cfg.host && state.next_room_url) { const link = document.createElement('a'); link.className = 'btn primary'; link.href = state.next_room_url; link.textContent = '→ Vào lượt mới của lớp'; el.append(link); }
    if (cfg.host) {
      const link = location.origin + '/member/race/' + cfg.code;
      const code = document.createElement('strong'); code.textContent = 'Mã phòng: ' + cfg.code + ' · ' + state.ranking.length + '/' + state.capacity + ' người · ' + state.total + ' câu'; el.append(code);
      if (state.history_url) { const history = document.createElement('a'); history.className = 'btn'; history.href = state.history_url; history.textContent = '📚 Xem / tải lịch sử bài làm'; el.append(history); }
      if (state.storage) { const saved = document.createElement('span'); saved.textContent = ({saved:'☁ Đã lưu lâu dài',pending:'☁ Đang lưu lâu dài…',error:'⚠ Chưa đồng bộ lâu dài · mở lịch sử để tải sao lưu',local:'Đã lưu trên máy chủ · tải sao lưu trong Lịch sử'})[state.storage.state] || ''; el.append(saved); }
      button('Sao chép link tham gia', async () => { try { await navigator.clipboard.writeText(link); note('Đã sao chép link.'); } catch (_) { window.prompt('Link tham gia', link); } }, el);
      if (state.mode === 'numeric') button('🎲 Đổi số đề minh họa', async () => update(await enqueue({action:'variant'})), el);
      if (state.state === 'closed') button('Tạo phòng mới · Đổi số', async () => { const d = await enqueue({action:'new_round'}); location.href = d.redirect; }, el);
      if (state.state === 'waiting') button('▶ Bắt đầu đồng loạt', async () => update(await enqueue({action:'start'})), el);
      if (state.state !== 'closed') button('■ Kết thúc phòng', async () => { if (confirm('Kết thúc và chấm bài tất cả thành viên?')) update(await enqueue({action:'close'})); }, el);
    } else if (!state.joined && state.state !== 'closed') {
      const label = document.createElement('label'), input = document.createElement('input');
      label.textContent = 'Tên học sinh: ';
      input.type = 'text'; input.id = 'racePlayerName'; input.maxLength = 80; input.minLength = 2; input.autocomplete = 'name'; input.placeholder = 'Nhập họ tên để tham gia'; input.value = joinName;
      input.oninput = () => { joinName = input.value; }; label.append(input); el.append(label);
      button('🏁 Vào làm bài · Nhận đề riêng', async () => {
        if (joinName.trim().length < 2) { input.focus(); throw Error('Em hãy nhập họ tên trước khi tham gia.'); }
        update(await enqueue({action:'join', name:joinName.trim()}));
      }, el);
    }
  }
  function drawRanks() {
    let rank = 0;
    $('raceRanks').innerHTML = '<table><thead><tr><th>Hạng</th><th>Người chơi</th><th>Đúng</th><th>Thời gian</th></tr></thead><tbody>' + state.ranking.map(p => {
      const place = p.done ? ++rank : '—';
      return '<tr class="' + (p.me ? 'me' : '') + '"><td class="medal">' + (place === 1 ? '🥇 ' : place === 2 ? '🥈 ' : place === 3 ? '🥉 ' : '') + place + '</td><td>' + esc(p.name) + (p.me ? ' (bạn)' : '') + '</td><td>' + (p.pending ? 'Chờ ADMIN chấm ' + p.pending + ' câu' : p.done ? p.correct + '/' + state.total : p.answered + '/' + state.total + ' đã làm') + '</td><td>' + ((p.submitted || p.done) ? clock(p.elapsed) + '.' + String(Math.floor((p.elapsed % 1) * 100)).padStart(2, '0') : 'Đang chờ/làm') + '</td></tr>';
    }).join('') + '</tbody></table>';
  }
  function adviceHTML(tips) {
    return tips?.length ? '<aside class="race-advice"><strong>Gợi ý để em làm tốt hơn</strong><ul>' + tips.map(tip => '<li>' + esc(tip) + '</li>').join('') + '</ul></aside>' : '';
  }
  function drawQuestion(force = false) {
    const key = [state.state, state.joined, state.next_room_url, pos, !!state.finished, questions.length, cfg.host, JSON.stringify(state.review?.map(x=>x.correct))].join(':');
    if (!force && key === rendered) return;
    rendered = key;
    const panel = $('raceQuestion'), nav = $('raceNav'), actions = $('raceActions');
    panel.replaceChildren(); nav.replaceChildren(); actions.replaceChildren();
    if (state.state === 'waiting' && !cfg.host) { panel.textContent = state.joined ? 'Đã nhận chỗ. Chờ ADMIN bắt đầu; đề sẽ hiện khi đồng hồ chạy.' : 'Bấm Tham gia để nhận một đề riêng.'; return; }
    if (!questions.length) { panel.textContent = state.state === 'closed' ? (state.next_room_url ? 'Lượt này đã kết thúc. Bấm Vào lượt mới của lớp ở phía trên để tiếp tục.' : 'Lượt này đã kết thúc. Em chưa có bài làm trong lượt này; hãy chờ ADMIN tạo lượt mới.') : 'Phòng đang làm bài. Nhập tên và bấm Vào làm bài ở phía trên để nhận đề; em sẽ làm trong thời gian còn lại của lớp.'; return; }
    const editable = !cfg.host && state.state === 'running' && !state.finished && !submitting;
    questions.forEach((q, i) => { const b = button((i === pos ? '▶ ' : '') + (i + 1) + (answers[i] !== undefined ? ' ✓' : ''), async () => {
      pos = i; if (cfg.host) update(await enqueue({action:'show', pos})); else drawQuestion(true);
    }, nav); b.setAttribute('aria-label', 'Câu ' + (i + 1)); });
    const q = questions[pos], answerPos = pos;
    panel.innerHTML = '<h3>' + (cfg.host ? '📺 Đề minh họa · ' : '') + 'Câu ' + (pos + 1) + '/' + questions.length + '</h3><div>' + q.text + '</div>';
    if (q.kind === 'TN') {
      q.options.forEach((text, i) => {
        const label = document.createElement('label'), input = document.createElement('input'), span = document.createElement('span');
        input.type = 'radio'; input.name = 'raceAnswer'; input.value = String(i); input.checked = answers[pos] === i; input.disabled = !editable;
        span.innerHTML = '<b>' + 'ABCD'[i] + '.</b> ' + text;
        input.onchange = () => changed(i, answerPos); label.append(input, span); panel.append(label);
      });
    } else if (q.kind === 'DS') {
      q.statements.forEach((text, i) => {
        const label = document.createElement('label'), span = document.createElement('span'), select = document.createElement('select');
        span.innerHTML = '<b>' + 'abcd'[i] + ')</b> ' + text;
        select.innerHTML = '<option value="">Chọn</option><option value="1">Đúng</option><option value="0">Sai</option>';
        select.value = Array.isArray(answers[pos]) && typeof answers[pos][i] === 'boolean' ? (answers[pos][i] ? '1' : '0') : ''; select.disabled = !editable;
        select.onchange = () => { const a = Array.isArray(answers[answerPos]) ? [...answers[answerPos]] : [null,null,null,null]; a[i] = select.value === '' ? null : select.value === '1'; changed(a, answerPos); };
        label.append(span, select); panel.append(label);
      });
    } else if (!q.manual && q.components > 1) {
      const fields = document.createElement('div'); fields.className = 'race-component-fields';
      const values = String(answers[answerPos] ?? '').split(';');
      const inputs = [];
      const collect = () => inputs.map(input => input.value.trim()).join(';');
      for (let i = 0; i < q.components; i++) {
        const label = document.createElement('label'), caption = document.createElement('span'), input = document.createElement('input');
        caption.textContent = (q.component_labels || [])[i] || 'Kết quả ' + (i + 1);
        input.type = 'text'; input.id = 'raceAnswerPart' + i; input.maxLength = 300;
        input.placeholder = q.decimal_places === 2 ? 'Ví dụ: 8,19' : 'Nhập kết quả';
        input.value = values[i] || ''; input.disabled = !editable;
        input.setAttribute('aria-label', 'Câu ' + (pos + 1) + ' · ' + caption.textContent);
        inputs.push(input);
        input.oninput = () => { answers[answerPos] = collect(); clearTimeout(saveTimer); saveTimer = setTimeout(saveAnswers, 400); };
        input.onchange = () => changed(collect(), answerPos);
        label.append(caption, input); fields.append(label);
      }
      panel.append(fields);
    } else {
      const input = document.createElement(q.manual ? 'textarea' : 'input'); if (!q.manual) input.type = 'text'; input.maxLength = q.manual ? 5000 : q.numeric ? 1500 : 100; input.rows = 5; input.style = 'width:100%;padding:12px;box-sizing:border-box'; input.placeholder = q.manual ? 'Nhập bài làm hoặc kết quả. ADMIN sẽ chấm câu này.' : q.decimal_places === 2 ? 'Dùng dấu phẩy: 8,19; nhiều kết quả ngăn bằng ;' : 'Nhập đáp án'; input.value = answers[pos] ?? ''; input.disabled = !editable;
      input.setAttribute('aria-label', 'Đáp án câu ' + (pos + 1)); input.onchange = () => changed(input.value, answerPos); input.oninput = () => { answers[answerPos] = input.value; clearTimeout(saveTimer); saveTimer = setTimeout(saveAnswers, 400); }; input.id = 'raceTextAnswer'; panel.append(input);
    }
    if (state.state === 'closed' && state.review?.[pos]) {
      const item = state.review[pos], review = document.createElement('div'); review.className = 'race-student-review ' + (item.correct === true ? 'is-correct' : item.correct === false ? 'is-incorrect' : 'is-pending');
      const comparison = item.parts?.length ? '<div class="race-review-scroll"><table><thead><tr><th>Kết quả</th><th>Em đã nhập</th><th>Đáp án đúng</th></tr></thead><tbody>' + item.parts.map(part => '<tr><th>' + esc(part.label) + '</th><td>' + esc(part.answer) + '</td><td>' + part.expected + '</td></tr>').join('') + '</tbody></table></div>' : '<div class="race-review-pair"><div class="race-review-answer"><b>Em đã chọn / nhập</b><div>' + (item.answer || '(Chưa trả lời)') + '</div></div><div class="race-review-expected"><b>Đáp án đúng của đề em</b><div>' + (item.expected || 'Xem lời giải') + '</div></div></div>';
      review.innerHTML = '<h3>' + (item.correct === null ? '⏳ Chờ ADMIN chấm' : item.correct ? '✅ Đúng' : '❌ Chưa đúng') + '</h3>' + comparison + adviceHTML(item.advice) + '<details class="race-solution"><summary>Xem lời giải từng bước</summary><div>' + item.solution + '</div></details>'; panel.append(review);
    }
    if (pos > 0) button('← Câu trước', async () => { pos--; if (cfg.host) update(await enqueue({action:'show', pos})); else drawQuestion(true); }, actions);
    if (pos + 1 < questions.length) button('Câu tiếp →', async () => { pos++; if (cfg.host) update(await enqueue({action:'show', pos})); else drawQuestion(true); }, actions);
    if (!cfg.host && state.state === 'running') { const message = document.createElement('p'); message.textContent = 'Em có thể tự chuyển câu. Khi ADMIN chuyển câu chiếu, màn hình sẽ chuyển theo; đáp án đã nhập được giữ lại.'; actions.append(message); }
    if (editable) {
      button('💾 Lưu lại', saveAnswers, actions);
      button('🏁 Nộp bài', submit, actions).classList.add('primary');
    }
    if (state.finished) { const p = document.createElement('p'); p.textContent = 'Đã nộp bài. Kết quả được ghi trên bảng xếp hạng; lời giải mở khi phòng kết thúc.'; actions.append(p); }
    typeset(); scheduleFit();
  }
  function changed(value, index = pos) {
    answers[index] = value;
    saveAnswers();
    // Keep focus on the current input; refresh only navigation status next time.
  }
  function drawGrading() {
    const el = $('raceGrading'); if (!cfg.host || !el) return;
    const rows = state.grading || [], key = JSON.stringify(rows);
    if (key === gradingKey) return;
    gradingKey = key;
    const wasOpen = el.firstElementChild?.open || false;
    el.replaceChildren();
    if (!rows.length) return;
    const fold = document.createElement('details'), summary = document.createElement('summary');
    fold.open = wasOpen; summary.textContent = '✍ ADMIN chấm bài · ' + rows.filter(r=>r.correct===null).length + ' câu chờ chấm'; fold.append(summary);
    rows.forEach(r => {
      const card = document.createElement('section'); card.style = 'border:1px solid #cbd5e1;padding:12px;margin:10px 0;border-radius:8px';
      const text = document.createElement('div'); text.innerHTML = '<h3>' + esc(r.name) + ' · Câu ' + (r.pos+1) + '</h3>' + r.text + '<h4>Bài làm học sinh</h4><pre style="white-space:pre-wrap">' + esc(r.answer || '(Chưa trả lời)') + '</pre><details><summary>Lời giải tham khảo</summary>' + r.solution + '</details><p>' + (r.correct===null ? 'Chưa chấm' : r.correct ? 'Đã chấm: Đúng' : 'Đã chấm: Sai') + '</p>';
      card.append(text);
      button('✅ Đúng', async()=>update(await enqueue({action:'grade', player:r.player, pos:r.pos, correct:true})), card);
      button('✕ Sai', async()=>update(await enqueue({action:'grade', player:r.player, pos:r.pos, correct:false})), card);
      fold.append(card);
    });
    el.append(fold);
    if (window.ldvlTypeset) window.ldvlTypeset(el);
    scheduleFit();
  }
  let resultFold, resultSummary;
  const resultCards = new Map();
  function drawResults() {
    const el = $('raceResults'); if (!cfg.host || !el) return;
    const rows = state.results || [], key = JSON.stringify(rows);
    if (key === resultsKey) return;
    resultsKey = key;
    if (!rows.length) { el.replaceChildren(); resultFold = null; resultCards.clear(); return; }
    if (!resultFold) {
      resultFold = document.createElement('details'); resultSummary = document.createElement('summary');
      resultFold.append(resultSummary); el.append(resultFold);
    }
    resultSummary.textContent = '📋 Kết quả từng học sinh · ' + rows.length + ' bài đã nộp';
    rows.forEach(row => {
      const id = row.player || row.name, signature = JSON.stringify(row), previous = resultCards.get(id);
      if (previous?.signature === signature) return;
      const card = document.createElement('details'), heading = document.createElement('summary');
      heading.textContent = row.name + ' · ' + row.score + '/' + row.questions.length + ' đúng · ' + clock(row.elapsed) + (row.pending ? ' · ' + row.pending + ' câu chờ chấm' : '');
      card.append(heading);
      row.questions.forEach((item, i) => {
        const part = document.createElement('section'); part.className = 'race-report-question';
        const q = item.question;
        const options = (q.options || q.statements || []).map((t,j) => '<p><b>' + (q.options ? 'ABCD'[j] : 'abcd'[j]) + '.</b> ' + t + '</p>').join('');
        part.innerHTML = '<h4>Câu ' + (i+1) + ' · ' + (item.correct === null ? '⏳ Chờ chấm' : item.correct ? '✅ Đúng' : '❌ Sai') + '</h4><div>' + q.text + '</div>' + options + '<div class="race-review-pair"><div class="race-review-answer"><b>Học sinh trả lời</b><div>' + esc(item.answer) + '</div></div><div class="race-review-expected"><b>Đáp án của đề này</b><div>' + item.expected + '</div></div></div>' + adviceHTML(item.advice) + '<details class="race-solution"><summary>Xem lời giải từng bước</summary><div>' + item.solution + '</div></details>';
        card.append(part);
      });
      card.open = previous?.card.open || false;
      if (previous) previous.card.replaceWith(card); else resultFold.append(card);
      resultCards.set(id, {card, signature});
      if (window.ldvlArmTikz) window.ldvlArmTikz(card);
      if (window.ldvlSplitPics) window.ldvlSplitPics(card);
      if (window.ldvlTypeset) window.ldvlTypeset(card);
      else if (window.MathJax?.typesetPromise) window.MathJax.typesetPromise([card]).then(scheduleFit).catch(() => {});
    });
    scheduleFit();
  }
  function saveAnswers() {
    if (submitting || state?.finished || state?.state !== 'running') return Promise.resolve();
    return enqueue({action:'save', answers:JSON.parse(JSON.stringify(answers))}).then(() => note('Đã lưu câu trả lời.')).catch(e => note('Chưa lưu: ' + e.message + ' Bấm Lưu lại hoặc Nộp bài để thử lại.'));
  }
  async function submit() {
    if (submitting) return;
    if (!confirm('Nộp bài và chốt thời gian hoàn thành?')) return;
    submitting = true;
    try { update(await enqueue({action:'submit', answers:{...answers}})); } finally { submitting = false; drawQuestion(true); }
  }
  function update(d) {
    if (!d.ok) throw Error(d.error || 'Không đọc được phòng.');
    state = d; serverOffset = d.now * 1000 - Date.now();
    const qr = $('raceQR'); if (qr) qr.hidden = d.state !== 'waiting';
    if (cfg.host) { if (JSON.stringify(questions) !== JSON.stringify(d.reference || [])) rendered = ''; questions = d.reference || []; pos = d.shown; }
    else if (d.questions) { questions = d.questions; if (d.state === 'running' && Number.isInteger(d.shown) && d.shown >= 0 && d.shown < questions.length) { if (lastHostShown !== d.shown) pos = d.shown; lastHostShown = d.shown; } if (!loaded || d.finished || d.state === 'closed') { answers = d.answers || {}; loaded = true; } }
    controls(); drawRanks(); drawQuestion(); drawGrading(); drawResults(); tick();
  }
  function tick() {
    if (!state) return;
    if (state.state === 'waiting') $('raceClock').textContent = 'Chờ bắt đầu · ' + clock(state.duration);
    else if (state.state === 'closed') $('raceClock').textContent = 'Đã kết thúc';
    else {
      const remaining = state.started + state.duration - (Date.now() + serverOffset) / 1000;
      $('raceClock').textContent = '⏱ Còn lại ' + clock(remaining);
    }
  }
  $('raceFull').onclick = async () => { try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); } catch (_) { note('Trình duyệt chưa hỗ trợ toàn màn hình.'); } };
  document.addEventListener('fullscreenchange', () => { $('raceFull').textContent = document.fullscreenElement ? '⛶ Thoát toàn màn hình' : '⛶ Toàn màn hình'; });
  let polling = false;
  async function poll() { if (polling) return; polling = true; try { update(await api()); } catch (e) { note(e.message); } finally { polling = false; } }
  setInterval(poll, 3000); setInterval(tick, 250); poll();
  // Save text while typing, including before clicking navigation or submit.
  setInterval(() => { if (!cfg.host && loaded && state?.state === 'running' && !state.finished && !submitting) enqueue({action:'save', answers:{...answers}}).catch(e => note('Chưa lưu: ' + e.message)); }, 5000);
})();
