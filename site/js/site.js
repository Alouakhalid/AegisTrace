/* =====================================================================
   AegisTrace marketing site
   - renders the agent topology and pipeline stages from the same
     vocabulary the backend uses
   - the live scanner talks to the real API; nothing here is mocked
   ===================================================================== */
(function () {
  'use strict';

  var API = '/api/v1';

  /* ------------------------------------------------------ agent topology */
  var AGENTS = [
    {
      key: 'orchestrator',
      code: 'OR',
      name: 'Orchestrator',
      note: 'Validates scope, builds the engagement manifest, routes 19 hunting skills to the agents that matter for this codebase.',
      out: 'scope manifest · work plan · skill routing'
    },
    {
      key: 'code_intelligence',
      code: 'CI',
      name: 'Code Intelligence',
      note: 'Walks the AST to recover HTTP routes, path parameters, ORM models and the ownership invariants each resource route implies.',
      out: 'routes · models · candidate invariants'
    },
    {
      key: 'recon',
      code: 'RC',
      name: 'Recon',
      note: 'Triages the attack surface through the scope gate, correlates advisories and maps which hosts are actually reachable.',
      out: 'attack surface · threat intel · scope verdict'
    },
    {
      key: 'vulnerability_research',
      code: 'VR',
      name: 'Vulnerability Research',
      note: 'Turns routes and invariants into testable hypotheses, each paired with a multi-identity probe plan and a priority.',
      out: 'hypotheses · test plans · priorities'
    },
    {
      key: 'dynamic_testing',
      code: 'DT',
      name: 'Dynamic Testing',
      note: 'Replays each plan against the running target as owner and as attacker, then diffs the database state to see what actually moved.',
      out: 'state diffs · evidence · probe results'
    },
    {
      key: 'verification',
      code: 'VF',
      name: 'Verification',
      note: 'Adjudicates every claim against the evidence chain. Three reproductions with a state mutation or it is not a finding.',
      out: 'CONFIRMED · UNCONFIRMED · REJECTED'
    },
    {
      key: 'remediation',
      code: 'RM',
      name: 'Remediation',
      note: 'Synthesises a patch on its own branch with a diff and a commit, then stops and waits for a human to approve it.',
      out: 'patch · diff · approval request'
    }
  ];

  var CHIP = {
    orchestrator: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg>',
    code_intelligence: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6l-5 6 5 6M16 6l5 6-5 6M14 4l-4 16"/></svg>',
    recon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 010 18M12 3a15 15 0 000 18"/></svg>',
    vulnerability_research: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 00-3.5 10.9c.5.4.8 1 .9 1.6h5.2c.1-.6.4-1.2.9-1.6A6 6 0 0012 3z"/></svg>',
    dynamic_testing: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/></svg>',
    verification: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l8 4v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V6l8-4z"/><path d="M9 12l2 2 4-4"/></svg>',
    remediation: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 7.5l-11 11a2.1 2.1 0 01-3-3l11-11a2.1 2.1 0 013 3z"/><path d="M14.5 5.5l4 4"/></svg>'
  };

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function renderAgents() {
    var grid = document.getElementById('agentGrid');
    if (!grid) return;
    // The agent cards ship as static markup so the page still reads without
    // JavaScript; only build them when that fallback is missing.
    if (grid.querySelector('.agent-card')) return;
    AGENTS.forEach(function (a, i) {
      var card = el('article', 'agent-card reveal');
      card.appendChild(el('div', 'agent-index', String(i + 1).padStart(2, '0') + ' / 07'));
      var chip = el('div', 'agent-chip', CHIP[a.key]);
      card.appendChild(chip);
      card.appendChild(el('h3', null, a.name));
      card.appendChild(el('p', null, a.note));
      card.appendChild(el('div', 'agent-out', '→ ' + a.out));
      grid.appendChild(card);
    });
  }

  /* ------------------------------------------------------ pipeline stages */
  var STAGES = [
    {
      n: 'Stage 01', h: 'Scope & manifest',
      p: 'The URL is validated, the repository is cloned at a pinned commit and every allowed host is recorded in a signed scope manifest.',
      bar: 100
    },
    {
      n: 'Stage 02', h: 'Architecture extraction',
      p: 'An AST pass recovers routes, path parameters, ORM models and the invariants those routes imply. Tests and examples are excluded.',
      bar: 92
    },
    {
      n: 'Stage 03', h: 'Hypothesis formulation',
      p: 'Routes and invariants are correlated into testable, prioritised hypotheses and paired with multi-identity probe plans.',
      bar: 84
    },
    {
      n: 'Stage 04', h: 'Exploit & reproduce',
      p: 'Each plan is replayed against the running target as two identities, with database state snapshots hashed between runs.',
      bar: 70
    },
    {
      n: 'Stage 05', h: 'Verdict & patch',
      p: 'Only three reproductions with a state mutation earn CONFIRMED. Verified findings get a patch on a branch and a human approval.',
      bar: 100
    }
  ];

  function renderStages() {
    var host = document.getElementById('flowSteps');
    if (!host) return;
    if (host.querySelector('.flow-step')) {
      // Static fallback already present - just animate its progress bars.
      animateBars(host);
      return;
    }
    STAGES.forEach(function (s) {
      var step = el('div', 'flow-step');
      step.appendChild(el('div', 'flow-num', s.n));
      step.appendChild(el('h3', null, s.h));
      step.appendChild(el('p', null, s.p));
      var bar = el('div', 'flow-bar', '<i></i>');
      step.appendChild(bar);
      host.appendChild(step);
      requestAnimationFrame(function () {
        setTimeout(function () {
          bar.firstChild.style.width = s.bar + '%';
        }, 120);
      });
    });
  }

  function animateBars(host) {
    var bars = host.querySelectorAll('.flow-bar');
    for (var i = 0; i < bars.length; i++) {
      (function (bar, pct) {
        requestAnimationFrame(function () {
          setTimeout(function () {
            var fill = bar.querySelector('i');
            if (fill) fill.style.width = pct + '%';
          }, 120);
        });
      })(bars[i], STAGES[i] ? STAGES[i].bar : 100);
    }
  }

  /* ---------------------------------------------------------- code blocks */
  var CODE_AST_HTML =
    '<span class="c"># CodeIntelligenceAgent \u00b7 AST extraction</span>\n' +
    '<span class="k">routes</span>      <span class="n">24</span>\n' +
    '<span class="k">models</span>      <span class="n">17</span>\n' +
    '<span class="k">invariants</span>  <span class="n">14</span>\n' +
    '\n' +
    '<span class="k">def</span> <span class="n">patch_order</span>(\n' +
    '    <span class="n">order_id</span>: <span class="a">int</span>,\n' +
    '    <span class="n">db</span>: <span class="a">Session</span>,\n' +
    ')\n' +
    '\n' +
    '<span class="c"># route + owner invariant recovered</span>\n' +
    '<span class="k">PATCH</span> <span class="n">/api/v1/orders/{order_id}</span>\n' +
    '    <span class="n">auth_required</span> = <span class="a">True</span>\n' +
    '    <span class="n">owner_field</span>   = <span class="a">order.user_id</span>\n' +
    '\n' +
    '<span class="c"># excluded: tests/ and examples/ are not deployed code</span>';

  var CODE_PROBE_HTML =
    '<span class="c"># DynamicTestingAgent \u00b7 paired identity probe</span>\n' +
    '<span class="k">plan</span>    <span class="s">tpl_idor_orders_order_id_patch</span>\n' +
    '\n' +
    '<span class="k">identity A</span> <span class="n">owner</span>    <span class="s">X-Testing-Identity: buyer_a</span>\n' +
    '<span class="k">identity B</span> <span class="n">attacker</span> <span class="s">X-Testing-Identity: buyer_b</span>\n' +
    '\n' +
    '<span class="k">PATCH</span> <span class="n">/api/v1/orders/1024</span>  <span class="s">\u2192 200  state_diff: shipping_address</span>\n' +
    '<span class="k">PATCH</span> <span class="n">/api/v1/orders/1024</span>  <span class="s">\u2192 200  state_diff: shipping_address</span>\n' +
    '<span class="k">PATCH</span> <span class="n">/api/v1/orders/1024</span>  <span class="s">\u2192 200  state_diff: shipping_address</span>\n' +
    '\n' +
    '<span class="k">VERDICT</span> <span class="s">CONFIRMED</span>  <span class="n">reproduced 3/3 \u00b7 invariant violated</span>';

  function renderCode() {
    var host = document.getElementById('codeAst');
    if (host && !host.innerHTML.trim()) host.innerHTML = CODE_AST_HTML;
    var probe = document.getElementById('codeProbe');
    if (probe && !probe.innerHTML.trim()) probe.innerHTML = CODE_PROBE_HTML;
  }

  /* ------------------------------------------------------------------ faq */
  var FAQ = [
    {
      q: 'What exactly counts as a confirmed vulnerability?',
      a: 'Three separate reproductions of the same exploit against a running target, each one producing an observable state mutation, with the request, the response and the state snapshot attached to the finding. Anything short of that is recorded as UNCONFIRMED. A scan of source code with no running target will never manufacture a confirmation.'
    },
    {
      q: 'Does it need access to a running application?',
      a: 'For static work, no — it clones the repository and reads the AST. To confirm an access-control flaw it needs a reachable target, which you can point at locally with web_target_url. Without one, AegisTrace still derives real routes, models and invariants, and honestly labels every result as unconfirmed.'
    },
    {
      q: 'Which languages and frameworks are supported today?',
      a: 'Python is the primary target: FastAPI, Flask, Django, SQLAlchemy and SQLModel are all parsed down to route level, and any Python web framework with standard decorators is covered. When a repository has no server-side routes at all, AegisTrace reports zero rather than inventing some.'
    },
    {
      q: 'How are the patches produced and reviewed?',
      a: 'The remediation agent writes the fix on a dedicated fix/aegistrace-* branch, commits it with a diff, and raises an approval request. Nothing merges into your working branch on its own — a human accepts or rejects it in the Approval Center.'
    },
    {
      q: 'Will it touch my repository?',
      a: 'A scan clones into a separate cache directory and is read-only against your checkout. The only writes are the remediation branch, and only after a finding is confirmed in the sandbox.'
    },
    {
      q: 'What does the evidence vault actually guarantee?',
      a: 'Evidence rows and state snapshots are protected by database-level immutability triggers: update and delete statements are rejected by SQLite itself. Findings reference the exact hypothesis, endpoint, invariant and evidence identifiers that produced them, so the whole chain can be replayed.'
    },
    {
      q: 'Can I use it in CI?',
      a: 'Yes. Scans are exposed over a small REST surface, and every verdict stays machine-readable: scan status, findings, hypotheses, patches and approvals can all be consumed by a pipeline or a ticket system.'
    },
    {
      q: 'What happens if the target is unreachable?',
      a: 'The dynamic stage records the failure, the hypotheses remain proposed, and the scan finishes with an honest unconfirmed count. No stage reports success it did not achieve.'
    }
  ];

  function renderFaq() {
    var host = document.getElementById('faqList');
    if (!host) return;
    if (host.querySelector('.faq-item')) {
      // Static fallback already present - wire the accordion onto it.
      wireFaq(host);
      return;
    }
    FAQ.forEach(function (item, i) {
      var wrap = el('div', 'faq-item');
      wrap.setAttribute('data-open', i === 0 ? 'true' : 'false');

      var btn = el('button', 'faq-q');
      btn.type = 'button';
      btn.setAttribute('aria-expanded', i === 0 ? 'true' : 'false');
      btn.innerHTML = '<span>' + esc(item.q) + '</span>' +
        '<span class="faq-chev"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6l5 5 5-5"/></svg></span>';
      btn.addEventListener('click', function () {
        var open = wrap.getAttribute('data-open') === 'true';
        wrap.setAttribute('data-open', open ? 'false' : 'true');
        btn.setAttribute('aria-expanded', open ? 'false' : 'true');
      });
      wrap.appendChild(btn);

      var ans = el('div', 'faq-a', '<div><p>' + esc(item.a) + '</p></div>');
      wrap.appendChild(ans);
      host.appendChild(wrap);
    });
  }

  function wireFaq(host) {
    host.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('.faq-q') : null;
      if (!btn) return;
      var wrap = btn.parentNode;
      var open = wrap.getAttribute('data-open') === 'true';
      wrap.setAttribute('data-open', open ? 'false' : 'true');
      btn.setAttribute('aria-expanded', open ? 'false' : 'true');
    });
  }

  /* ------------------------------------------------------ hero pipe preview */
  function renderPipe() {
    var host = document.getElementById('pipeDemo');
    if (!host) return;
    // The pipe rows ship as static markup; the animation below drives them.
    if (host.querySelector('.pipe-row')) return;
    AGENTS.forEach(function (a, i) {
      var row = el('div', 'pipe-row');
      row.setAttribute('data-state', 'idle');
      row.appendChild(el('div', 'pipe-ico', a.code));
      var mid = el('div');
      mid.appendChild(el('div', 'pipe-name', a.name));
      mid.appendChild(el('div', 'pipe-note', a.out));
      row.appendChild(mid);
      row.appendChild(el('div', 'pipe-state', 'queued'));
      host.appendChild(row);
    });
  }

  function playPipe() {
    var host = document.getElementById('pipeDemo');
    if (!host) return;
    var rows = host.querySelectorAll('.pipe-row');
    var i = 0;
    var clock = document.getElementById('pipeClock');
    // The static markup shows the finished pipeline so it reads correctly
    // without scripting; rewind it before replaying the run.
    for (var r = 0; r < rows.length; r++) {
      rows[r].setAttribute('data-state', 'idle');
      var state = rows[r].querySelector('.pipe-state');
      if (state) state.textContent = 'queued';
    }
    function step() {
      if (i > 0) {
        rows[i - 1].setAttribute('data-state', 'done');
        rows[i - 1].querySelector('.pipe-state').textContent = 'succeeded';
      }
      if (i >= rows.length) {
        if (clock) clock.textContent = '7/7 agents · audit complete';
        return;
      }
      rows[i].setAttribute('data-state', 'running');
      rows[i].querySelector('.pipe-state').textContent = 'running';
      if (clock) clock.textContent = 'agent ' + (i + 1) + ' of 7';
      i += 1;
      setTimeout(step, 700);
    }
    setTimeout(step, 900);
  }

  /* --------------------------------------------------------------- reveal */
  function initReveal() {
    var items = document.querySelectorAll('.reveal');
    if (!('IntersectionObserver' in window)) {
      items.forEach(function (n) { n.classList.add('in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var n = entry.target;
        var delay = parseInt(n.getAttribute('data-delay') || '0', 10);
        setTimeout(function () { n.classList.add('in'); }, delay);
        io.unobserve(n);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (n, i) {
      if (!n.getAttribute('data-delay')) n.setAttribute('data-delay', String((i % 4) * 70));
      io.observe(n);
    });
  }

  /* ----------------------------------------------------------- live stats */
  function loadStats() {
    fetch(API + '/stats/overview')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        var el = document.querySelector('[data-metric="scans"]');
        if (!el) return;
        var n = d.total_scans != null ? d.total_scans : (d.scans != null ? d.scans : null);
        el.textContent = n == null ? '—' : String(n);
      })
      .catch(function () { /* offline: the metric stays honest with a dash */ });
  }

  /* ---------------------------------------------------------- live scanner */
  function initScanner() {
    var form = document.getElementById('scanForm');
    if (!form) return;

    var input = document.getElementById('scanInput');
    var btn = document.getElementById('scanBtn');
    var btnLabel = document.getElementById('scanBtnLabel');
    var box = document.getElementById('scanStatus');
    var scanId = document.getElementById('scanId');
    var state = document.getElementById('scanState');
    var log = document.getElementById('scanLog');
    var result = document.getElementById('scanResult');
    var timer = null;

    document.getElementById('scanPresets').addEventListener('click', function (e) {
      var chip = e.target.closest('.chip');
      if (!chip) return;
      input.value = 'https://github.com/' + chip.getAttribute('data-repo');
      input.focus();
    });

    function line(text, cls) {
      var d = document.createElement('div');
      if (cls) d.className = cls;
      d.textContent = text;
      log.appendChild(d);
      log.scrollTop = log.scrollHeight;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var url = input.value.trim();
      if (!/^https?:\/\/github\.com\/[^/]+\/[^/]+/.test(url)) {
        line('Enter a GitHub repository URL, for example https://github.com/owner/repo', 'err');
        box.setAttribute('data-visible', 'true');
        return;
      }
      if (timer) clearInterval(timer);

      log.innerHTML = '';
      result.setAttribute('data-visible', 'false');
      box.setAttribute('data-visible', 'true');
      btn.disabled = true;
      btnLabel.textContent = 'Scanning…';
      state.textContent = 'queued';

      fetch(API + '/scans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: 'Site scan · ' + url.split('/').pop(),
          target_type: 'repository',
          assessment_mode: 'full',
          github_url: url,
          github_branch: 'main',
          allowed_hosts: ['github.com', 'static-source-analysis'],
          active_testing_consented: false
        })
      }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function (d) {
        scanId.textContent = d.scan_id;
        line('> ' + d.scan_id + ' queued', 't');
        poll(d.scan_id);
      }).catch(function (err) {
        line('Could not start the scan: ' + err.message, 'err');
        btn.disabled = false;
        btnLabel.textContent = 'Start Assessment';
      });
    });

    function poll(id) {
      timer = setInterval(function () {
        fetch(API + '/scans/' + id)
          .then(function (r) { return r.json(); })
          .then(function (d) {
            state.textContent = d.status + ' · ' + (d.progress_percentage || 0) + '%';
            var agents = d.agent_states || {};
            Object.keys(agents).forEach(function (k) {
              var a = agents[k];
              var existing = log.querySelector('[data-agent="' + k + '"]');
              var text = a.agent + ' — ' + a.status + (a.message ? ' · ' + a.message : '');
              if (!existing) {
                var d2 = document.createElement('div');
                d2.setAttribute('data-agent', k);
                d2.textContent = '  ' + text;
                d2.className = a.status === 'succeeded' ? 'ok' : (a.status === 'failed' ? 'err' : '');
                log.appendChild(d2);
              } else {
                existing.textContent = '  ' + text;
              }
            });
            log.scrollTop = log.scrollHeight;

            if (d.status === 'completed' || d.status === 'failed') {
              clearInterval(timer);
              btn.disabled = false;
              btnLabel.textContent = 'Scan another repository';
              line('> assessment ' + d.status, d.status === 'completed' ? 'ok' : 'err');
              loadIntel(id, d);
            }
          })
          .catch(function () { /* transient poll failure, retry */ });
      }, 1200);
    }

    function loadIntel(id, scan) {
      Promise.all([
        fetch(API + '/code-intel/' + id).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
        fetch(API + '/findings?scan_id=' + id).then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; })
      ]).then(function (parts) {
        var intel = parts[0] || {};
        var findings = parts[1] || [];
        var mine = findings.filter(function (f) { return f.scan_id === id; });
        var confirmed = mine.filter(function (f) {
          return String(f.verification_verdict || '').toUpperCase() === 'CONFIRMED';
        }).length;

        result.innerHTML = '';
        var stats = [
          ['routes', (intel.endpoints || []).length],
          ['models', (intel.models || []).length],
          ['invariants', (intel.invariants || []).length],
          ['findings', mine.length],
          ['confirmed', confirmed],
          ['agents', Object.keys(scan.agent_states || {}).length]
        ];
        stats.forEach(function (s) {
          var p = document.createElement('span');
          p.className = 'stat-pill';
          p.innerHTML = '<b>' + s[1] + '</b>' + s[0];
          result.appendChild(p);
        });
        result.setAttribute('data-visible', 'true');
      });
    }
  }

  /* ------------------------------------------------------------- gallery */
  function initGallery() {
    // The product screenshots swap on a slow cycle once the hero is in view.
    var frames = document.querySelectorAll('[data-shot]');
    if (!frames.length) return;
  }

  /* ----------------------------------------------------------------- boot */
  function boot() {
    // The page ships with class="no-js" so CSS can keep every section visible
    // when scripting is unavailable; swap it the moment we take over.
    var root = document.documentElement;
    if (root && root.classList) {
      root.classList.remove('no-js');
      root.classList.add('js');
    }

    renderPipe();
    renderAgents();
    renderStages();
    renderCode();
    renderFaq();
    initReveal();
    loadStats();
    initScanner();
    initGallery();

    var toggle = document.getElementById('navToggle');
    var drawer = document.getElementById('navDrawer');
    if (toggle && drawer) {
      toggle.addEventListener('click', function () {
        var open = drawer.getAttribute('data-open') === 'true';
        drawer.setAttribute('data-open', open ? 'false' : 'true');
        toggle.setAttribute('aria-expanded', open ? 'false' : 'true');
      });
      drawer.addEventListener('click', function (e) {
        if (e.target.tagName !== 'A') return;
        drawer.setAttribute('data-open', 'false');
        toggle.setAttribute('aria-expanded', 'false');
      });
    }

    var hero = document.querySelector('#pipeline') || document.querySelector('.hero');
    if (hero && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          playPipe();
          obs.disconnect();
        });
      }, { threshold: 0.25 }).observe(hero);
    } else {
      playPipe();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
