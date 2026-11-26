/* AegisTrace 3D scene: a shield core, seven agent nodes and a particle field.
   One fixed WebGL canvas sits behind the page. Scrolling flies the camera and
   re-forms the agents (ring, helix, lattice), so the page moves through
   dimensions. Falls back silently when WebGL or motion is unavailable. */
import * as THREE from 'three';

const canvas = document.getElementById('scene3d');
const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function webglOK() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch (e) { return false; }
}

if (canvas && webglOK()) { try { start(); } catch (e) { fail(e); } } else { fail(); }

function fail(e) {
  if (e && window.console) console.warn('3D scene disabled:', e);
  if (canvas) canvas.remove();
  document.documentElement.classList.add('no-3d');
}

function start() {
  const isMobile = () => window.innerWidth < 900;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: !isMobile(), alpha: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x08080d, 0.045);
  const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 100);

  /* lights */
  scene.add(new THREE.AmbientLight(0x8877ff, 0.9));
  const key = new THREE.PointLight(0x9b7bff, 60, 30); key.position.set(4, 4, 6); scene.add(key);
  const rim = new THREE.PointLight(0x22d3ee, 45, 30); rim.position.set(-5, -2, 3); scene.add(rim);

  /* glow sprite texture */
  function glowTex(r, g, b) {
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const x = c.getContext('2d'); const gr = x.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, `rgba(${r},${g},${b},1)`); gr.addColorStop(0.35, `rgba(${r},${g},${b},0.35)`); gr.addColorStop(1, `rgba(${r},${g},${b},0)`);
    x.fillStyle = gr; x.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  }
  const violetGlow = glowTex(139, 92, 246), cyanGlow = glowTex(34, 211, 238);
  function sprite(tex, size, opacity) {
    const m = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending });
    const s = new THREE.Sprite(m); s.scale.set(size, size, 1); return s;
  }

  /* world group that scroll moves around */
  const world = new THREE.Group(); scene.add(world);

  /* shield core */
  const core = new THREE.Group(); world.add(core);
  const sh = new THREE.Shape();
  sh.moveTo(0, 1.4);
  sh.lineTo(1.0, 1.0); sh.lineTo(1.0, 0.15);
  sh.bezierCurveTo(1.0, -0.75, 0.45, -1.2, 0, -1.5);
  sh.bezierCurveTo(-0.45, -1.2, -1.0, -0.75, -1.0, 0.15);
  sh.lineTo(-1.0, 1.0); sh.closePath();
  const shGeo = new THREE.ExtrudeGeometry(sh, { depth: 0.34, bevelEnabled: true, bevelThickness: 0.07, bevelSize: 0.06, bevelSegments: 3, curveSegments: isMobile() ? 14 : 28 });
  shGeo.center();
  const shMesh = new THREE.Mesh(shGeo, new THREE.MeshStandardMaterial({ color: 0x1b1738, metalness: 0.85, roughness: 0.3, emissive: 0x2a1a70, emissiveIntensity: 0.55 }));
  core.add(shMesh);
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(shGeo, 25), new THREE.LineBasicMaterial({ color: 0xb7a5ff, transparent: true, opacity: 0.95 }));
  core.add(edges);
  /* inner wire crystal */
  const crystal = new THREE.Mesh(new THREE.IcosahedronGeometry(0.5, 1), new THREE.MeshBasicMaterial({ color: 0x22d3ee, wireframe: true, transparent: true, opacity: 0.9 }));
  crystal.position.z = 0.32; core.add(crystal);
  const crystalCore = new THREE.Mesh(new THREE.IcosahedronGeometry(0.22, 0), new THREE.MeshBasicMaterial({ color: 0xe9e4ff }));
  crystalCore.position.z = 0.32; core.add(crystalCore);
  const coreGlow = sprite(violetGlow, 6.5, 0.55); core.add(coreGlow);

  /* orbit rings */
  function ring(radius, color, op) {
    const pts = []; for (let i = 0; i <= 128; i++) { const a = i / 128 * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * radius, 0, Math.sin(a) * radius)); }
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color, transparent: true, opacity: op }));
  }
  const ringA = ring(3.7, 0x8b5cf6, 0.5); ringA.rotation.x = 0.35; world.add(ringA);
  const ringB = ring(4.5, 0x22d3ee, 0.22); ringB.rotation.x = -0.5; ringB.rotation.z = 0.4; world.add(ringB);

  /* seven agents */
  const NAMES = ['Orchestrator', 'Code Intelligence', 'Recon', 'Vulnerability Research', 'Dynamic Testing', 'Verification', 'Remediation'];
  const COLORS = [0x8b5cf6, 0x6d8bff, 0x22d3ee, 0xc084fc, 0xf59e0b, 0x10b981, 0xf472b6];
  const agents = [];
  const linkGeo = new THREE.BufferGeometry();
  const linkPos = new Float32Array(NAMES.length * 6);
  linkGeo.setAttribute('position', new THREE.BufferAttribute(linkPos, 3));
  const links = new THREE.LineSegments(linkGeo, new THREE.LineBasicMaterial({ color: 0x9382ff, transparent: true, opacity: 0.45 }));
  links.frustumCulled = false; world.add(links);
  NAMES.forEach((n, i) => {
    const g = new THREE.Group();
    const mesh = new THREE.Mesh(new THREE.OctahedronGeometry(0.2, 0), new THREE.MeshStandardMaterial({ color: COLORS[i], emissive: COLORS[i], emissiveIntensity: 0.9, metalness: 0.4, roughness: 0.3 }));
    const wire = new THREE.Mesh(new THREE.OctahedronGeometry(0.31, 0), new THREE.MeshBasicMaterial({ color: COLORS[i], wireframe: true, transparent: true, opacity: 0.6 }));
    const glow = sprite(i % 2 ? cyanGlow : violetGlow, 1.3, 0.7);
    g.add(mesh, wire, glow);
    const pulse = sprite(cyanGlow, 0.5, 0.95); world.add(pulse);
    world.add(g);
    agents.push({ g, mesh, wire, pulse, phase: i / NAMES.length, pos: new THREE.Vector3(Math.cos(i) * 3, 0, Math.sin(i) * 3) });
  });

  /* formations: where each agent wants to be */
  const FORMS = 3;
  function target(i, form, t, out) {
    const n = NAMES.length;
    if (form === 0) { /* ring */
      const a = i / n * Math.PI * 2 + t * 0.35, R = 3.7;
      out.set(Math.cos(a) * R, Math.sin(a) * 1.1, Math.sin(a) * R * 0.9);
      out.applyAxisAngle(new THREE.Vector3(1, 0, 0), 0.35);
    } else if (form === 1) { /* helix */
      const a = i * 0.95 + t * 0.55;
      out.set(Math.cos(a) * 2.9, (i - 3) * 0.75, Math.sin(a) * 2.0);
    } else { /* lattice */
      const cx = (i % 4) - 1.5, cy = Math.floor(i / 4) - 0.5;
      out.set(cx * 1.25, cy * -1.5 + Math.sin(t + i) * 0.12, Math.cos(t * 0.6 + i) * 0.5 - 0.5);
    }
  }

  /* particle field in depth */
  const COUNT = isMobile() ? 700 : 1800;
  const pg = new THREE.BufferGeometry(); const pp = new Float32Array(COUNT * 3);
  for (let i = 0; i < COUNT; i++) { pp[i * 3] = (Math.random() - 0.5) * 40; pp[i * 3 + 1] = (Math.random() - 0.5) * 60; pp[i * 3 + 2] = (Math.random() - 0.5) * 40; }
  pg.setAttribute('position', new THREE.BufferAttribute(pp, 3));
  const stars = new THREE.Points(pg, new THREE.PointsMaterial({ color: 0xbdb2ff, size: 0.045, transparent: true, opacity: 0.85, depthWrite: false, sizeAttenuation: true }));
  scene.add(stars);

  /* perspective floor grid that streams past as you scroll */
  const grid = new THREE.GridHelper(60, 60, 0x6d4bd8, 0x2a2350);
  grid.position.y = -4.2; grid.material.transparent = true; grid.material.opacity = 0.35; scene.add(grid);

  /* sizing */
  let pr = Math.min(window.devicePixelRatio || 1, isMobile() ? 1.5 : 1.75), slow = 0;
  let W = 0, H = 0;
  function resize() {
    W = window.innerWidth; H = window.innerHeight;
    renderer.setPixelRatio(pr);
    renderer.setSize(W, H, false);
    camera.aspect = W / H; camera.updateProjectionMatrix();
  }
  resize(); window.addEventListener('resize', resize);

  /* input + scroll */
  const mouse = { x: 0, y: 0, sx: 0, sy: 0 };
  window.addEventListener('pointermove', (e) => { mouse.x = e.clientX / W - 0.5; mouse.y = e.clientY / H - 0.5; }, { passive: true });
  let scrollP = 0, scrollSm = 0, form = 0, lastScrollY = 0, scrollVel = 0;
  function readScroll() {
    const h = document.documentElement; const max = Math.max(1, h.scrollHeight - h.clientHeight);
    scrollP = Math.min(1, Math.max(0, h.scrollTop / max));
  }
  window.addEventListener('scroll', readScroll, { passive: true }); readScroll();

  world.position.set(isMobile() ? 0 : 3.2, isMobile() ? -0.6 : 0.2, 0);
  const tmp = new THREE.Vector3(); const clock = new THREE.Clock();
  const lookAt = new THREE.Vector3();

  function update(t, dt) {
    scrollSm += (scrollP - scrollSm) * Math.min(1, dt * 3.2);
    const p = scrollSm;
    const kk = 1 - Math.exp(-dt * 4);
    scrollVel = (window.scrollY - lastScrollY); lastScrollY = window.scrollY;
    mouse.sx += (mouse.x - mouse.sx) * kk; mouse.sy += (mouse.y - mouse.sy) * kk;

    /* formation by scroll */
    const f = p < 0.2 ? 0 : p < 0.55 ? 1 : 2;
    form = f;

    /* world drifts left and right as sections change, centred on mobile */
    const side = isMobile() ? 0 : Math.cos(p * Math.PI * 3.2) * 2.5 + (p < 0.12 ? (0.12 - p) * 6 : 0);
    const targetX = isMobile() ? 0 : side;
    world.position.x += (targetX - world.position.x) * kk;
    const targetY = isMobile() ? -0.6 - p * 3 : 0.2 - p * 1.2;
    world.position.y += (targetY - world.position.y) * kk;
    world.rotation.y = p * Math.PI * 2.2 + mouse.sx * 0.6;
    world.rotation.x = mouse.sy * 0.35 + Math.sin(p * 6.0) * 0.12;
    const s = (isMobile() ? 0.78 : 1) * (1 + Math.max(0, 0.12 - p) * 1.5); world.scale.setScalar(s);

    /* camera flight: pulls back, dives in, banks */
    const z = 9.2 - Math.sin(Math.min(1, p * 1.6) * Math.PI) * 2.6 + (p > 0.8 ? (p - 0.8) * 8 : 0);
    camera.position.set(Math.sin(p * 4.0) * 1.4 + mouse.sx * 0.8, 0.6 + Math.cos(p * 5.0) * 0.5 - mouse.sy * 0.5, z);
    camera.rotation.z = Math.sin(p * 7.0) * 0.05;
    lookAt.set(world.position.x * 0.4, world.position.y * 0.6, 0); camera.lookAt(lookAt);
    camera.rotation.z += Math.sin(p * 7.0) * 0.05;

    /* core */
    shMesh.rotation.y = Math.sin(t * 0.6) * 0.35; edges.rotation.y = shMesh.rotation.y;
    core.rotation.y = t * 0.25;
    core.position.y = Math.sin(t * 0.9) * 0.08;
    crystal.rotation.x = t * 0.9; crystal.rotation.y = t * 1.3;
    const beat = 1 + Math.sin(t * 2.2) * 0.06 + Math.min(0.25, Math.abs(scrollVel) * 0.004);
    coreGlow.scale.set(6.5 * beat, 6.5 * beat, 1);
    ringA.rotation.y = t * 0.12; ringB.rotation.y = -t * 0.08;
    ringA.material.opacity = form === 0 ? 0.55 : 0.12; ringB.material.opacity = form === 0 ? 0.25 : 0.06;

    /* agents */
    agents.forEach((a, i) => {
      target(i, form, t, tmp);
      a.pos.lerp(tmp, 1 - Math.exp(-dt * 3));
      a.g.position.copy(a.pos);
      a.mesh.rotation.x = t * 0.8 + i; a.mesh.rotation.y = t * 1.1 + i;
      a.wire.rotation.x = -t * 0.6; a.wire.rotation.y = t * 0.5;
      const k = i * 6; const c = core.position;
      linkPos[k] = c.x; linkPos[k + 1] = c.y; linkPos[k + 2] = c.z + 0.3;
      linkPos[k + 3] = a.pos.x; linkPos[k + 4] = a.pos.y; linkPos[k + 5] = a.pos.z;
      const u = (t * 0.35 + a.phase) % 1;
      const q = u < 0.5 ? u * 2 : 2 - u * 2; /* core -> agent -> core */
      a.pulse.position.set(c.x + (a.pos.x - c.x) * q, c.y + (a.pos.y - c.y) * q, c.z + 0.3 + (a.pos.z - c.z - 0.3) * q);
    });
    linkGeo.attributes.position.needsUpdate = true;

    /* depth field and floor stream with scroll */
    stars.rotation.y = t * 0.012 + p * 1.2; stars.position.y = p * 8;
    grid.position.z = (p * 40) % 1; grid.position.y = -4.2 - p * 0.6;
    key.position.x = Math.sin(t * 0.5) * 5; rim.position.y = Math.cos(t * 0.4) * 3;
  }

  let running = true;
  document.addEventListener('visibilitychange', () => { running = !document.hidden; if (running) { clock.getDelta(); loop(); } });
  function loop() {
    if (!running) return;
    const dt = Math.min(0.05, clock.getDelta());
    update(clock.elapsedTime, dt);
    renderer.render(scene, camera);
    /* adaptive quality: step the pixel ratio down on slow devices */
        if (dt > 0.034) slow++; else if (slow > 0) slow--;
    if (slow > 40 && pr > 0.7) { pr = Math.max(0.65, pr - 0.35); renderer.setPixelRatio(pr); renderer.setSize(W, H, false); slow = 0; }
    if (!reduce) requestAnimationFrame(loop);
  }
  if (reduce) { /* one still frame, redrawn on scroll */
    update(1.5, 5); renderer.render(scene, camera);
    window.addEventListener('scroll', () => { scrollSm = scrollP; update(1.5, 5); renderer.render(scene, camera); }, { passive: true });
    window.addEventListener('resize', () => renderer.render(scene, camera));
  } else { clock.start(); loop(); }

  document.documentElement.classList.add('has-3d');
  window.__aegisScene = { setProgress(v) { scrollP = scrollSm = v; }, get form() { return form; } };
}
