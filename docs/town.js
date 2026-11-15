// The town in 3D: a building for each family, a window for each local, in the window's own order
// (town/ui/Skyline.qml). Flat colours only. It draws when something changes and rests otherwise.
(function () {
  "use strict";
  const COL = {
    night: 0x0c0e13, ground: 0x090b0f, front: 0x10131a, side: 0x0d1016, roof: 0x161a24,
    dark: 0x1d2231, light: 0xffc94d, waiting: 0x6e5c2f, good: 0x8fcf7a, bad: 0xd9826e, ink: 0xebe7dc,
  };
  const STATE = { dark: COL.dark, work: COL.light, out: COL.waiting, DONE: COL.good, "GAVE UP": COL.bad, light: COL.light };
  const STRINGS = {
    ganesh: [0xff7a45, 0xffc94d, 0xe85d5d],
    diwali: [0xffc94d, 0xff9f43, 0xffe08a],
  };
  const PARTY = [0xffc94d, 0x8fcf7a, 0x5b8def, 0xe06c75, 0xc678dd, 0xebe7dc, 0x56b6c2];
  // Two rows so the town fits a tall frame; the taller families stand at the back.
  const BACK = ["Law", "Media", "Engineering", "Finance", "Health"];
  const FRONT = ["Ring one", "Education", "Business", "Students"];
  const CELL = 0.9, WIN = 0.58, WIDE = 3 * CELL + 0.8, DEEP = 3.2, GROUND = 1.5, TOP = 0.5;
  const reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  function Town(canvas, families, hooks) {
    const T = THREE;
    const renderer = new T.WebGLRenderer({ canvas, antialias: true, powerPreference: "low-power" });
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(ratio);
    renderer.setClearColor(COL.night, 1);
    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(34, 1, 0.5, 1200);
    // The frame is the top part of a taller one, so the town stands low with the sky above it.
    const SHIFT = 1.4;

    // ground: one flat plane to the horizon, and the street in front of the town
    const ground = new T.Mesh(new T.PlaneGeometry(3000, 3000), new T.MeshBasicMaterial({ color: COL.ground }));
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);
    const street = new T.Mesh(new T.PlaneGeometry(60, 3.2), new T.MeshBasicMaterial({ color: COL.front }));
    street.rotation.x = -Math.PI / 2;
    street.position.set(0, 0.01, 8.2);
    scene.add(street);

    // stars: flat squares of one size, as in the window's sky
    {
      const n = 420, pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
      const greys = [0x3a4152, 0x5a6070, 0x8a8f9c].map((h) => new T.Color(h));
      let seed = 7;
      const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      for (let i = 0; i < n; i++) {
        const az = (rnd() - 0.5) * 2.9 + Math.PI, el = 0.015 + Math.pow(rnd(), 1.4) * 0.42, r = 600;
        pos[i * 3] = r * Math.cos(el) * Math.sin(az);
        pos[i * 3 + 1] = r * Math.sin(el);
        pos[i * 3 + 2] = r * Math.cos(el) * Math.cos(az);
        const c = greys[Math.floor(rnd() * 3)];
        col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
      }
      const g = new T.BufferGeometry();
      g.setAttribute("position", new T.BufferAttribute(pos, 3));
      g.setAttribute("color", new T.BufferAttribute(col, 3));
      scene.add(new T.Points(g, new T.PointsMaterial({ size: 2 * ratio, sizeAttenuation: false, vertexColors: true })));
    }

    // buildings and windows
    const mats = [COL.side, COL.side, COL.roof, COL.ground, COL.front, COL.side].map((c) => new T.MeshBasicMaterial({ color: c }));
    const houses = [], blocks = [], slots = [];
    const byName = {};
    families.forEach((f) => (byName[f.family] = f));
    const place = (list, z) => list.forEach((name, i) => {
      const f = byName[name];
      if (!f) return;
      const people = f.jobs.flatMap((j) => j.people);
      const rows = Math.ceil(people.length / 3);
      const h = GROUND + rows * CELL + TOP;
      const x = (i - (list.length - 1) / 2) * 6; // the front row stands in the gaps of the back row
      const mesh = new T.Mesh(new T.BoxGeometry(WIDE, h, DEEP), mats);
      mesh.position.set(x, h / 2, z);
      scene.add(mesh);
      blocks.push(mesh);
      const house = { name, x, z, h, people, first: slots.length };
      people.forEach((p, k) => {
        const r = Math.floor(k / 3), c = k % 3;
        slots.push({ p, house, x: x + (c - 1) * CELL, y: h - TOP - CELL / 2 - r * CELL, z: z + DEEP / 2 + 0.02 });
      });
      houses.push(house);
    });
    place(BACK, -3.5);
    place(FRONT, 3.5);
    // anyone in a family the layout does not know still gets a window, in a building of their own
    families.forEach((f) => { if (!BACK.includes(f.family) && !FRONT.includes(f.family)) place([f.family], 13); });

    const count = slots.length;
    const winGeo = new T.PlaneGeometry(WIN, WIN);
    const windows = new T.InstancedMesh(winGeo, new T.MeshBasicMaterial({ color: 0xffffff }), count);
    const m4 = new T.Matrix4(), tmp = new T.Color();
    const cur = new Float32Array(count * 3), tgt = new Float32Array(count * 3);
    const scale = new Float32Array(count).fill(1);
    slots.forEach((s, i) => {
      m4.makeTranslation(s.x, s.y, s.z);
      windows.setMatrixAt(i, m4);
      tmp.setHex(COL.dark);
      cur[i * 3] = tgt[i * 3] = tmp.r; cur[i * 3 + 1] = tgt[i * 3 + 1] = tmp.g; cur[i * 3 + 2] = tgt[i * 3 + 2] = tmp.b;
      windows.setColorAt(i, tmp);
    });
    scene.add(windows);
    const index = {};
    slots.forEach((s, i) => (index[s.p.id] = i));

    // festival lights strung from roof to roof (only on a day that has them)
    let strings = null;
    function setLights(name) {
      if (strings) { scene.remove(strings); strings.geometry.dispose(); strings = null; }
      const palette = STRINGS[name];
      if (palette) {
        const pos = [], col = [];
        const rows = [houses.filter((h) => BACK.includes(h.name)), houses.filter((h) => FRONT.includes(h.name))];
        let k = 0;
        rows.forEach((row) => {
          for (let i = 0; i < row.length - 1; i++) {
            const a = row[i], b = row[i + 1];
            const ax = a.x + WIDE / 2, bx = b.x - WIDE / 2, az = a.z + DEEP / 2, n = 16;
            for (let j = 0; j <= n; j++) {
              const t = j / n;
              const y = a.h + (b.h - a.h) * t - Math.sin(Math.PI * t) * 0.9;
              pos.push(ax + (bx - ax) * t, y, az);
              tmp.setHex(palette[k++ % palette.length]);
              col.push(tmp.r, tmp.g, tmp.b);
            }
          }
          // and across each roof
          row.forEach((h) => {
            for (let j = 0; j <= 8; j++) {
              pos.push(h.x - WIDE / 2 + (WIDE * j) / 8, h.h + 0.02, h.z + DEEP / 2);
              tmp.setHex(palette[k++ % palette.length]);
              col.push(tmp.r, tmp.g, tmp.b);
            }
          });
        });
        const g = new T.BufferGeometry();
        g.setAttribute("position", new T.Float32BufferAttribute(pos, 3));
        g.setAttribute("color", new T.Float32BufferAttribute(col, 3));
        strings = new T.Points(g, new T.PointsMaterial({ size: 3 * ratio, sizeAttenuation: false, vertexColors: true }));
        scene.add(strings);
      }
      draw();
    }

    // ---- camera: drag to turn around the town ----
    const view = { az: -0.36, el: 0.13, dist: 60, target: new T.Vector3(0, 4, 0) };
    let goal = null; // { dist, target, from, t0 }
    let focusOn = null;
    function fit(names) {
      const hs = names && names.length ? houses.filter((h) => names.includes(h.name)) : houses;
      let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity, top = 0;
      hs.forEach((h) => { x0 = Math.min(x0, h.x - WIDE / 2); x1 = Math.max(x1, h.x + WIDE / 2); z0 = Math.min(z0, h.z); z1 = Math.max(z1, h.z); top = Math.max(top, h.h); });
      // the turned camera brings one end of the town nearer, so leave room on both sides
      const w = (x1 - x0) * 1.1 + (hs.length < houses.length ? 9 : 4), ht = top + (hs.length < houses.length ? 4 : 2);
      const v = (camera.fov * Math.PI) / 360, hz = Math.atan(Math.tan(v) * camera.aspect);
      // the target sits at the middle of the taller frame, so below it only (SHIFT - 1) / SHIFT of a half shows
      const below = (SHIFT - 1) / SHIFT * 2 * 0.86;
      const dist = Math.max((w / 2) / Math.tan(hz), (ht / 2) / (Math.tan(v) * below));
      return { dist: Math.min(Math.max(dist, 16), 160), target: new T.Vector3((x0 + x1) / 2, top * 0.5, (z0 + z1) / 2) };
    }
    function focus(names) {
      focusOn = names && names.length ? names : null;
      const f = fit(focusOn);
      if (reduced) { view.dist = f.dist; view.target.copy(f.target); draw(); return; }
      goal = { dist: f.dist, target: f.target, from: { dist: view.dist, target: view.target.clone() }, t0: performance.now() };
      loop();
    }
    function placeCamera() {
      const c = Math.cos(view.el);
      camera.position.set(
        view.target.x + view.dist * c * Math.sin(view.az),
        view.target.y + view.dist * Math.sin(view.el),
        view.target.z + view.dist * c * Math.cos(view.az));
      camera.lookAt(view.target);
    }

    // ---- states ----
    let lerping = false;
    function setStates(fn) {
      for (let i = 0; i < count; i++) {
        tmp.setHex(STATE[fn(slots[i].p, i)] || COL.dark);
        tgt[i * 3] = tmp.r; tgt[i * 3 + 1] = tmp.g; tgt[i * 3 + 2] = tmp.b;
      }
      if (reduced) { cur.set(tgt); pushColors(); draw(); return; }
      lerping = true;
      loop();
    }
    function pushColors() {
      for (let i = 0; i < count; i++) {
        // the window you are looking at wakes up
        if (i === hovered && tgt[i * 3] === darkRGB.r && tgt[i * 3 + 1] === darkRGB.g) tmp.setHex(COL.light);
        else tmp.setRGB(cur[i * 3], cur[i * 3 + 1], cur[i * 3 + 2]);
        windows.setColorAt(i, tmp);
      }
      windows.instanceColor.needsUpdate = true;
    }
    const darkRGB = new T.Color(COL.dark);
    function stepColors() {
      let moving = false;
      for (let i = 0; i < cur.length; i++) {
        const d = tgt[i] - cur[i];
        if (Math.abs(d) > 0.004) { cur[i] += d * 0.16; moving = true; } else cur[i] = tgt[i];
      }
      pushColors();
      return moving;
    }

    // ---- fireworks, when the whole town is up ----
    const bursts = [];
    function celebrate() {
      if (reduced) return;
      [0, 650, 1300, 2100].forEach((ms, n) => setTimeout(() => {
        const N = 90, pos = new Float32Array(N * 3), col = new Float32Array(N * 3), vel = [];
        const ox = (n % 2 ? 1 : -1) * (3 + Math.random() * 8), oy = 15 + Math.random() * 6, oz = -3 + Math.random() * 4;
        const base = PARTY[Math.floor(Math.random() * PARTY.length)];
        for (let i = 0; i < N; i++) {
          pos[i * 3] = ox; pos[i * 3 + 1] = oy; pos[i * 3 + 2] = oz;
          const u = Math.random() * 2 - 1, a = Math.random() * Math.PI * 2, s = 4 + Math.random() * 2.4, q = Math.sqrt(1 - u * u);
          vel.push(q * Math.cos(a) * s, u * s, q * Math.sin(a) * s);
          tmp.setHex(i % 4 ? base : COL.ink);
          col[i * 3] = tmp.r; col[i * 3 + 1] = tmp.g; col[i * 3 + 2] = tmp.b;
        }
        const g = new T.BufferGeometry();
        g.setAttribute("position", new T.BufferAttribute(pos, 3));
        g.setAttribute("color", new T.BufferAttribute(col, 3));
        const pts = new T.Points(g, new T.PointsMaterial({ size: 3 * ratio, sizeAttenuation: false, vertexColors: true, transparent: true }));
        scene.add(pts);
        bursts.push({ pts, vel, t0: performance.now(), last: performance.now() });
        loop();
      }, ms));
    }
    function stepBursts(now) {
      for (let b = bursts.length - 1; b >= 0; b--) {
        const B = bursts[b], dt = Math.min((now - B.last) / 1000, 0.05), age = (now - B.t0) / 1000;
        B.last = now;
        const p = B.pts.geometry.attributes.position;
        for (let i = 0; i < B.vel.length / 3; i++) {
          B.vel[i * 3 + 1] -= 3.2 * dt;
          for (let k = 0; k < 3; k++) { B.vel[i * 3 + k] *= 0.985; p.array[i * 3 + k] += B.vel[i * 3 + k] * dt; }
        }
        p.needsUpdate = true;
        B.pts.material.opacity = Math.max(0, 1 - Math.max(0, age - 1.4) / 1.2);
        if (age > 2.6) { scene.remove(B.pts); B.pts.geometry.dispose(); B.pts.material.dispose(); bursts.splice(b, 1); }
      }
      return bursts.length > 0;
    }

    // ---- hover and tap ----
    const ray = new T.Raycaster(), ndc = new T.Vector2();
    let hovered = -1, pinned = false;
    function pick(clientX, clientY) {
      const r = canvas.getBoundingClientRect();
      ndc.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(ndc, camera);
      const hit = ray.intersectObjects([windows, ...blocks], false)[0];
      return hit && hit.object === windows ? hit.instanceId : -1;
    }
    function hover(i, x, y) {
      if (i !== hovered) {
        if (hovered >= 0) scale[hovered] = 1;
        hovered = i;
        if (i >= 0) scale[i] = 1.4;
        slots.forEach((s, k) => { m4.makeScale(scale[k], scale[k], 1).setPosition(s.x, s.y, s.z); windows.setMatrixAt(k, m4); });
        windows.instanceMatrix.needsUpdate = true;
        pushColors();
        draw();
      }
      canvas.style.cursor = i >= 0 ? "pointer" : "";
      hooks.hover && hooks.hover(i >= 0 ? slots[i].p : null, x, y, i >= 0 ? slots[i].house.name : "");
    }
    let drag = null;
    canvas.addEventListener("pointerdown", (e) => {
      drag = { x: e.clientX, y: e.clientY, az: view.az, el: view.el, moved: false, id: e.pointerId };
    });
    window.addEventListener("pointermove", (e) => {
      if (drag && drag.id === e.pointerId) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (!drag.moved && Math.hypot(dx, dy) > 5) { drag.moved = true; canvas.classList.add("dragging"); try { canvas.setPointerCapture(e.pointerId); } catch (_) {} }
        if (drag.moved) {
          view.az = Math.max(-1.05, Math.min(1.05, drag.az - dx * 0.006));
          view.el = Math.max(0.03, Math.min(0.75, drag.el + dy * 0.004));
          draw();
        }
        return;
      }
      if (e.target === canvas && e.pointerType === "mouse" && !pinned) hover(pick(e.clientX, e.clientY), e.clientX, e.clientY);
    });
    window.addEventListener("pointerup", (e) => {
      if (!drag || drag.id !== e.pointerId) return;
      const tap = !drag.moved;
      drag = null;
      canvas.classList.remove("dragging");
      if (tap && e.target === canvas) {
        const i = pick(e.clientX, e.clientY);
        pinned = i >= 0 && e.pointerType !== "mouse";
        hover(i, e.clientX, e.clientY);
      }
    });
    window.addEventListener("pointercancel", () => { drag = null; canvas.classList.remove("dragging"); });
    canvas.addEventListener("pointerleave", (e) => { if (!pinned && !drag && e.pointerType === "mouse") hover(-1); });

    // ---- labels over each roof ----
    const tagBox = hooks.tags;
    const tags = houses.map((h) => {
      const el = document.createElement("div");
      el.className = "tag";
      el.innerHTML = `${h.name}<b>${h.people.length}</b>`;
      tagBox.appendChild(el);
      return el;
    });
    const v3 = new T.Vector3();
    function placeTags() {
      const w = canvas.clientWidth, ht = canvas.clientHeight;
      houses.forEach((h, i) => {
        v3.set(h.x, h.h + 0.55, h.z + DEEP / 2).project(camera);
        const on = v3.z < 1;
        tags[i].style.display = on ? "" : "none";
        tags[i].style.transform = `translate(${((v3.x + 1) / 2) * w}px, ${((1 - v3.y) / 2) * ht}px) translate(-50%, -100%)`;
        tags[i].classList.toggle("lit", !focusOn || focusOn.includes(h.name));
      });
    }

    // ---- drawing ----
    let raf = 0, visible = true;
    function frame(now) {
      raf = 0;
      let busy = false;
      if (goal) {
        const t = Math.min(1, (now - goal.t0) / 900), e = 1 - Math.pow(1 - t, 3);
        view.dist = goal.from.dist + (goal.dist - goal.from.dist) * e;
        view.target.lerpVectors(goal.from.target, goal.target, e);
        if (t >= 1) goal = null; else busy = true;
      }
      if (lerping) { lerping = stepColors(); busy = busy || lerping; }
      if (bursts.length) busy = stepBursts(now) || busy;
      placeCamera();
      renderer.render(scene, camera);
      placeTags();
      if (busy && visible) loop();
    }
    function loop() { if (!raf) raf = requestAnimationFrame(frame); }
    function draw() { loop(); }

    function resize() {
      const w = canvas.clientWidth, h = canvas.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      camera.aspect = w / (h * SHIFT);
      camera.setViewOffset(w, h * SHIFT, 0, 0, w, h);
      const f = fit(focusOn);
      view.dist = f.dist; view.target.copy(f.target);
      draw();
    }
    new ResizeObserver(resize).observe(canvas);
    new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible) draw(); }).observe(canvas);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) draw(); });
    resize();

    return {
      count, setStates, setLights, focus, celebrate,
      people: slots.map((s) => s.p),
      houseOf: (id) => (index[id] !== undefined ? slots[index[id]].house.name : null),
      unpin() { pinned = false; hover(-1); },
    };
  }

  window.LocalsTown = Town;
})();
