/* Shared LaTeX rendering for the portal and isolated exercise documents. */
(function () {
  'use strict';
  if (window.__ldvlMathRenderer) return;
  window.__ldvlMathRenderer = true;
  var main = !!(document.currentScript && document.currentScript.hasAttribute('data-ldvl-math-main'));
  var skip = 'script,style,noscript,textarea,pre,code,input,select,option,[contenteditable],mjx-container,.MathJax,.katex,math,svg,.no-mathjax,.tex2jax_ignore';
  var raw = /\$\$[\s\S]+?\$\$|(?:^|[^\\])\$[^$]+\$|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\]/;
  var engine, queue = Promise.resolve(), timer;
  function hasMath(root) {
    if (!root) return false;
    if (root.nodeType === 3) return !!(root.parentElement && !root.parentElement.closest(skip) && raw.test(root.nodeValue || ''));
    if (root.nodeType !== 1 || root.closest(skip)) return false;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        return node.parentElement && !node.parentElement.closest(skip) && raw.test(node.nodeValue || '') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    return !!walker.nextNode();
  }
  function configure() {
    if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) return;
    var cfg = window.MathJax || {};
    cfg.tex = Object.assign({inlineMath: [['$', '$'], ['\\(', '\\)']], displayMath: [['$$', '$$'], ['\\[', '\\]']], processEscapes: true, macros: {heva: ['\\begin{cases}#1\\end{cases}', 1], hoac: ['\\left[\\begin{aligned}#1\\end{aligned}\\right.', 1]}}, cfg.tex || {});
    cfg.options = Object.assign({skipHtmlTags: ['script','noscript','style','textarea','pre','code','input','select','option'], ignoreHtmlClass: 'no-mathjax|tex2jax_ignore|katex'}, cfg.options || {});
    cfg.startup = Object.assign({}, cfg.startup || {}, {typeset: false});
    window.MathJax = cfg;
  }
  function waitReady(ms) {
    return new Promise(function (resolve, reject) {
      var start = Date.now();
      function poll() {
        var mj = window.MathJax;
        if (mj && mj.typesetPromise && mj.startup && mj.startup.promise) {
          Promise.resolve(mj.startup.promise).then(function () { resolve(mj); }, reject);
        } else if (mj && mj.typesetPromise) resolve(mj);
        else if (Date.now() - start >= ms) reject(new Error('MathJax chưa sẵn sàng'));
        else setTimeout(poll, 80);
      }
      poll();
    });
  }
  function load(url) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script'), finished = false;
      var timeout = setTimeout(function () { finish(new Error('MathJax tải quá lâu')); }, 20000);
      function finish(err) {
        if (finished) return;
        finished = true;
        clearTimeout(timeout);
        if (err) { s.remove(); reject(err); } else resolve();
      }
      s.src = url; s.async = true;
      s.onload = function () { finish(); };
      s.onerror = function () { finish(new Error('Không tải được MathJax')); };
      document.head.appendChild(s);
    }).then(function () { return waitReady(20000); });
  }
  function ensure() {
    if (engine) return engine;
    var existing = document.querySelector('script[src*="mathjax" i],script[src*="tex-mml-chtml" i],script[src*="tex-chtml" i]');
    if (window.MathJax && window.MathJax.typesetPromise) engine = waitReady(20000);
    else if (existing) engine = waitReady(20000);
    else {
      configure();
      engine = load('https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js').catch(function () {
        return load('https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.min.js');
      });
    }
    engine = engine.catch(function (e) { engine = null; throw e; });
    return engine;
  }
  window.ldvlTypeset = function (root) {
    root = root === document ? document.body : (root || document.body);
    if (!root) return Promise.resolve(false);
    queue = queue.catch(function () {}).then(function () {
      if (!root.isConnected) return false;
      if (!hasMath(root)) return true;
      return ensure().then(function (mj) {
        if (!root.isConnected) return false;
        return mj.typesetPromise([root]).then(function () { return true; });
      });
    }).then(function (ok) {
      if (window.ldvlFitFigs && root.isConnected) window.ldvlFitFigs(root);
      return ok;
    }).catch(function (e) { console.warn('[LDVL] LaTeX:', e); return false; });
    return queue;
  };
  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(function () { window.ldvlTypeset(document.body); }, 100);
  }
  function start() {
    if (!document.body) return;
    if (main || hasMath(document.body)) window.ldvlTypeset(document.body);
    new MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var record = records[i];
        if (record.type === 'characterData' && hasMath(record.target)) { schedule(); return; }
        for (var j = 0; j < record.addedNodes.length; j++) {
          if (hasMath(record.addedNodes[j])) { schedule(); return; }
        }
      }
    }).observe(document.body, {childList: true, subtree: true, characterData: true});
  }
  if (main) ensure().catch(function (e) { console.warn('[LDVL] MathJax:', e); });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
