(() => {
  'use strict';
  const cfg = window.RACE_CONFIG, $ = id => document.getElementById(id);
  let state, questions = [], answers = {}, pos = 0, loaded = false, rendered = '', queue = Promise.resolve(), serverOffset = 0, submitting = false, saveTimer;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clock = seconds => { seconds = Math.max(0, Math.floor(seconds)); return String(Math.floor(seconds / 60)).padStart(2, '0') + ':' + String(seconds % 60).padStart(2, '0'); };
  const note = text => { $('raceNotice').textContent = text; };
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
    const el = $('raceControls'); el.replaceChildren();
    if (cfg.host) {
      const link = location.origin + '/member/race/' + cfg.code;
      const code = document.createElement('strong'); code.textContent = 'Mã phòng: ' + cfg.code + ' · ' + state.ranking.length + '/' + state.capacity + ' người · ' + state.total + ' câu'; el.append(code);
      button('Sao chép link tham gia', async () => { try { await navigator.clipboard.writeText(link); note('Đã sao chép link.'); } catch (_) { window.prompt('Link tham gia', link); } }, el);
      if (state.state === 'waiting') button('▶ Bắt đầu đồng loạt', async () => update(await enqueue({action:'start'})), el);
      if (state.state !== 'closed') button('■ Kết thúc phòng', async () => { if (confirm('Kết thúc và chấm bài tất cả thành viên?')) update(await enqueue({action:'close'})); }, el);
    } else if (!state.joined && state.state === 'waiting') {
      button('🏁 Tham gia · Nhận đề riêng', async () => update(await enqueue({action:'join'})), el);
    }
  }
  function drawRanks() {
    let rank = 0;
    $('raceRanks').innerHTML = '<table><thead><tr><th>Hạng</th><th>Người chơi</th><th>Đúng</th><th>Thời gian</th></tr></thead><tbody>' + state.ranking.map(p => {
      const place = p.done ? ++rank : '—';
      return '<tr class="' + (p.me ? 'me' : '') + '"><td class="medal">' + (place === 1 ? '🥇 ' : place === 2 ? '🥈 ' : place === 3 ? '🥉 ' : '') + place + '</td><td>' + esc(p.name) + (p.me ? ' (bạn)' : '') + '</td><td>' + (p.done ? p.correct + '/' + state.total : p.answered + '/' + state.total + ' đã làm') + '</td><td>' + (p.done ? clock(p.elapsed) + '.' + String(Math.floor((p.elapsed % 1) * 100)).padStart(2, '0') : 'Đang chờ/làm') + '</td></tr>';
    }).join('') + '</tbody></table>';
  }
  function drawQuestion(force = false) {
    const key = [state.state, pos, !!state.finished, questions.length, cfg.host].join(':');
    if (!force && key === rendered) return;
    rendered = key;
    const panel = $('raceQuestion'), nav = $('raceNav'), actions = $('raceActions');
    panel.replaceChildren(); nav.replaceChildren(); actions.replaceChildren();
    if (state.state === 'waiting' && !cfg.host) { panel.textContent = state.joined ? 'Đã nhận chỗ. Chờ ADMIN bắt đầu; đề sẽ hiện khi đồng hồ chạy.' : 'Bấm Tham gia để nhận một đề riêng.'; return; }
    if (!questions.length) { panel.textContent = 'Phòng đã bắt đầu hoặc kết thúc. Chỉ thành viên đã tham gia mới có bài làm.'; return; }
    const editable = !cfg.host && state.state === 'running' && !state.finished && !submitting;
    questions.forEach((q, i) => { const b = button((i === pos ? '▶ ' : '') + (i + 1) + (answers[i] !== undefined ? ' ✓' : ''), async () => {
      pos = i; if (cfg.host) update(await enqueue({action:'show', pos})); else drawQuestion(true);
    }, nav); b.setAttribute('aria-label', 'Câu ' + (i + 1)); });
    const q = questions[pos];
    panel.innerHTML = '<h3>' + (cfg.host ? '📺 Đề minh họa · ' : '') + 'Câu ' + (pos + 1) + '/' + questions.length + '</h3><div>' + q.text + '</div>';
    if (q.kind === 'TN') {
      q.options.forEach((text, i) => {
        const label = document.createElement('label'), input = document.createElement('input'), span = document.createElement('span');
        input.type = 'radio'; input.name = 'raceAnswer'; input.value = String(i); input.checked = answers[pos] === i; input.disabled = !editable;
        span.innerHTML = '<b>' + 'ABCD'[i] + '.</b> ' + text;
        input.onchange = () => changed(i); label.append(input, span); panel.append(label);
      });
    } else if (q.kind === 'DS') {
      q.statements.forEach((text, i) => {
        const label = document.createElement('label'), span = document.createElement('span'), select = document.createElement('select');
        span.innerHTML = '<b>' + 'abcd'[i] + ')</b> ' + text;
        select.innerHTML = '<option value="">Chọn</option><option value="1">Đúng</option><option value="0">Sai</option>';
        select.value = Array.isArray(answers[pos]) && typeof answers[pos][i] === 'boolean' ? (answers[pos][i] ? '1' : '0') : ''; select.disabled = !editable;
        select.onchange = () => { const a = Array.isArray(answers[pos]) ? [...answers[pos]] : [null,null,null,null]; a[i] = select.value === '' ? null : select.value === '1'; changed(a); };
        label.append(span, select); panel.append(label);
      });
    } else {
      const input = document.createElement('input'); input.type = 'text'; input.maxLength = 100; input.placeholder = 'Nhập đáp án'; input.value = answers[pos] ?? ''; input.disabled = !editable;
      input.setAttribute('aria-label', 'Đáp án câu ' + (pos + 1)); input.onchange = () => changed(input.value); input.oninput = () => { answers[pos] = input.value; clearTimeout(saveTimer); saveTimer = setTimeout(saveAnswers, 400); }; input.id = 'raceTextAnswer'; panel.append(input);
    }
    if (state.state === 'closed' && state.review?.[pos]) {
      const review = document.createElement('div'); review.innerHTML = '<h3>' + (state.review[pos].correct ? '✅ Đúng' : 'Chưa đúng') + '</h3>' + state.review[pos].solution; panel.append(review);
    }
    if (pos > 0) button('← Câu trước', async () => { pos--; if (cfg.host) update(await enqueue({action:'show', pos})); else drawQuestion(true); }, actions);
    if (pos + 1 < questions.length) button('Câu tiếp →', async () => { pos++; if (cfg.host) update(await enqueue({action:'show', pos})); else drawQuestion(true); }, actions);
    if (editable) {
      button('💾 Lưu lại', saveAnswers, actions);
      button('🏁 Nộp bài', submit, actions).classList.add('primary');
    }
    if (state.finished) { const p = document.createElement('p'); p.textContent = 'Đã nộp bài. Kết quả được ghi trên bảng xếp hạng; lời giải mở khi phòng kết thúc.'; actions.append(p); }
    typeset();
  }
  function changed(value) {
    answers[pos] = value;
    saveAnswers();
    // Keep focus on the current input; refresh only navigation status next time.
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
    if (cfg.host) { questions = d.reference || []; pos = d.shown; }
    else if (d.questions) { questions = d.questions; if (!loaded || d.finished || d.state === 'closed') { answers = d.answers || {}; loaded = true; } }
    controls(); drawRanks(); drawQuestion(); tick();
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
