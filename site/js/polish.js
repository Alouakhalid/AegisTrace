/* AegisTrace site polish: mesh canvas, progress bar, tilt, spotlight, counters, marquee. */
(function () {
  'use strict';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* scroll progress */
  var bar = document.querySelector('.scroll-progress span');
  function onScroll() {
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    if (bar) bar.style.transform = 'scaleX(' + (max > 0 ? h.scrollTop / max : 0) + ')';
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* hero mesh: nodes drift, near nodes link, a pulse travels along links */
  var cv = document.getElementById('heroMesh');
  if (cv && !reduce) {
    var ctx = cv.getContext('2d');
    var W = 0, H = 0, nodes = [], pulses = [], dpr = Math.min(window.devicePixelRatio || 1, 2);
    var running = true;
    function size() {
      var r = cv.getBoundingClientRect();
      W = r.width; H = r.height;
      cv.width = W * dpr; cv.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = Math.max(28, Math.min(70, Math.round(W * H / 22000)));
      nodes = [];
      for (var i = 0; i < n; i++) nodes.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * .25, vy: (Math.random() - .5) * .25, r: Math.random() * 1.8 + 1.2 });
    }
    function frame() {
      if (!running) return;
      ctx.clearRect(0, 0, W, H);
      var i, j, a, b, d, link = 150;
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i]; a.x += a.vx; a.y += a.vy;
        if (a.x < 0 || a.x > W) a.vx *= -1;
        if (a.y < 0 || a.y > H) a.vy *= -1;
      }
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        for (j = i + 1; j < nodes.length; j++) {
          b = nodes[j]; d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < link) {
            ctx.strokeStyle = 'rgba(147,130,255,' + (0.5 * (1 - d / link)).toFixed(3) + ')';
            ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
            if (Math.random() < 0.0009 && pulses.length < 14) pulses.push({ a: a, b: b, t: 0 });
          }
        }
      }
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i]; ctx.fillStyle = 'rgba(205,198,255,.95)';
        ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, 6.283); ctx.fill();
      }
      for (i = pulses.length - 1; i >= 0; i--) {
        var p = pulses[i]; p.t += 0.02;
        if (p.t >= 1) { pulses.splice(i, 1); continue; }
        var x = p.a.x + (p.b.x - p.a.x) * p.t, y = p.a.y + (p.b.y - p.a.y) * p.t;
        var g = ctx.createRadialGradient(x, y, 0, x, y, 12);
        g.addColorStop(0, 'rgba(34,211,238,.95)'); g.addColorStop(1, 'rgba(34,211,238,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 12, 0, 6.283); ctx.fill();
      }
      requestAnimationFrame(frame);
    }
    size();
    window.addEventListener('resize', size);
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (en) {
        var vis = en[0].isIntersecting;
        if (vis && !running) { running = true; requestAnimationFrame(frame); }
        running = vis;
      }).observe(cv);
    }
    requestAnimationFrame(frame);
  }

  /* console card tilt (pointer devices only) */
  var card = document.querySelector('.console-card');
  if (card && !reduce && window.matchMedia('(hover: hover)').matches) {
    var host = card.parentNode;
    host.addEventListener('mousemove', function (e) {
      var r = card.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      card.style.transform = 'perspective(1100px) rotateY(' + (x * 7).toFixed(2) + 'deg) rotateX(' + (-y * 7).toFixed(2) + 'deg)';
    });
    host.addEventListener('mouseleave', function () { card.style.transform = ''; });
  }

  /* cursor spotlight on cards */
  document.addEventListener('mousemove', function (e) {
    var t = e.target && e.target.closest ? e.target.closest('.agent-card, .gate') : null;
    if (!t) return;
    var r = t.getBoundingClientRect();
    t.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    t.style.setProperty('--my', (e.clientY - r.top) + 'px');
  }, { passive: true });

  /* marquee: two identical strips in one track, so the loop is seamless */
  var items = document.querySelector('.trust-items');
  if (items && !items.querySelector('.marquee-track')) {
    var strip = document.createElement('div');
    strip.className = 'marquee-strip';
    while (items.firstChild) strip.appendChild(items.firstChild);
    var copy = strip.cloneNode(true);
    copy.setAttribute('aria-hidden', 'true');
    var track = document.createElement('div');
    track.className = 'marquee-track';
    track.appendChild(strip); track.appendChild(copy);
    items.appendChild(track);
  }

  /* gate counters */
  function countUp(el) {
    var txt = el.getAttribute('data-text');
    if (txt) { el.textContent = txt; return; }
    var to = parseFloat(el.getAttribute('data-count')) || 0, suf = el.getAttribute('data-suffix') || '';
    if (reduce) { el.textContent = to + suf; return; }
    var t0 = null;
    (function step(ts) {
      if (!t0) t0 = ts;
      var k = Math.min(1, (ts - t0) / 900);
      el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))) + suf;
      if (k < 1) requestAnimationFrame(step);
    })(performance.now());
  }
  var nums = document.querySelectorAll('.gate-num');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (en, o) {
      en.forEach(function (x) { if (x.isIntersecting) { countUp(x.target); o.unobserve(x.target); } });
    }, { threshold: .6 });
    nums.forEach(function (n) { io.observe(n); });
  } else nums.forEach(countUp);

  /* 3D tilt on cards with depth layers */
  if (!reduce && window.matchMedia('(hover: hover)').matches) {
    var tiltSel = '.agent-card, .gate, .feature-card, .vl';
    document.querySelectorAll(tiltSel).forEach(function (el) { el.classList.add('t3d'); });
    document.addEventListener('pointermove', function (e) {
      var el = e.target && e.target.closest ? e.target.closest('.t3d') : null;
      if (!el) return;
      var r = el.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      el.classList.add('is-tilting');
      el.style.transform = 'perspective(900px) rotateY(' + (x * 16).toFixed(2) + 'deg) rotateX(' + (-y * 16).toFixed(2) + 'deg) translateZ(14px)';
    }, { passive: true });
    document.addEventListener('pointerout', function (e) {
      var el = e.target && e.target.closest ? e.target.closest('.t3d') : null;
      if (el && !el.contains(e.relatedTarget)) { el.classList.remove('is-tilting'); el.style.transform = ''; }
    });
  }
})();
