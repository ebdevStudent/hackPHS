// Particle effects for the ball-drone simulator: sparks, grit, dust, smoke, steam, fire, embers, drifting motes.
// Two THREE.Points draw calls: an additive pass (fire, sparks, embers, glow) and an alpha-blended pass (smoke, dust,
// steam, grit, motes). Sprites: soft disc, noisy puff (procedural canvas texture, per-particle rotation) and
// velocity-stretched streaks. Colour and alpha evolve over life; cheap curl-ish turbulence; scene fog applied.
import * as THREE from "three";

const DISC = 0, PUFF = 1, STREAK = 2;

const VERT = /* glsl */`
uniform float uScale; uniform vec2 uViewport;
attribute float aSize, aAlpha, aKind, aRot;
attribute vec3 aColor, aVel;
varying float vAlpha, vKind, vRot, vStretch, vDepth;
varying vec3 vColor; varying vec2 vDir;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  float ps = aSize * uScale / max(0.05, -mv.z);
  vStretch = 1.0; vDir = vec2(1.0, 0.0);
  if (aKind > 1.5) {                                   // streak: stretch along the screen-space velocity
    vec4 p2 = projectionMatrix * (modelViewMatrix * vec4(position - aVel * 0.035, 1.0));
    vec2 d = (gl_Position.xy / gl_Position.w - p2.xy / max(1e-4, p2.w)) * uViewport * 0.5;
    float len = length(d);
    if (len > 1e-3) vDir = d / len;
    float l = max(ps, len + ps);
    vStretch = clamp(l / max(ps, 1.0), 1.0, 12.0);
    ps = l;
  }
  gl_PointSize = clamp(ps, 1.0, 320.0);
  vAlpha = aAlpha; vKind = aKind; vRot = aRot; vColor = aColor; vDepth = -mv.z;
}`;

const FRAG = /* glsl */`
uniform sampler2D uPuff; uniform vec3 fogColor; uniform float fogNear, fogFar, uAdditive;
varying float vAlpha, vKind, vRot, vStretch, vDepth;
varying vec3 vColor; varying vec2 vDir;
void main() {
  vec2 c = gl_PointCoord - 0.5; c.y = -c.y;
  float a;
  if (vKind > 1.5) {
    float along = dot(c, vDir), across = dot(c, vec2(-vDir.y, vDir.x)) * vStretch;
    float r = along * along * 4.0 + across * across * 4.0;
    if (r > 1.0) discard;
    a = (1.0 - r) * (0.6 + 0.4 * smoothstep(-0.5, 0.5, along));   // brighter head
  } else if (vKind > 0.5) {
    float s = sin(vRot), co = cos(vRot);
    vec2 uv = vec2(co * c.x - s * c.y, s * c.x + co * c.y) + 0.5;
    a = texture2D(uPuff, uv).r;
  } else {
    float r = dot(c, c) * 4.0;
    if (r > 1.0) discard;
    a = exp(-r * 3.0) * (1.0 - r);
  }
  a *= vAlpha;
  if (a < 0.003) discard;
  float fog = smoothstep(fogNear, fogFar, vDepth);
  if (uAdditive > 0.5) gl_FragColor = vec4(vColor * a * (1.0 - fog), 1.0);
  else gl_FragColor = vec4(mix(vColor, fogColor, fog), a);
}`;

// Soft, noisy smoke puff (grey value used as alpha), generated once on a canvas.
function puffTexture() {
  const N = 128, c = document.createElement("canvas"); c.width = c.height = N;
  const g = c.getContext("2d"), img = g.createImageData(N, N);
  const rnd = mulberry(7);
  const blobs = Array.from({ length: 14 }, () => ({ x: 0.5 + (rnd() - 0.5) * 0.4, y: 0.5 + (rnd() - 0.5) * 0.4, r: 0.18 + rnd() * 0.22, w: 0.5 + rnd() * 0.5 }));
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const u = x / N, v = y / N;
    let s = 0;
    for (const b of blobs) { const d = ((u - b.x) ** 2 + (v - b.y) ** 2) / (b.r * b.r); s += b.w * Math.exp(-d * 2.2); }
    const rr = Math.hypot(u - 0.5, v - 0.5) * 2;
    const edge = Math.max(0, 1 - rr) ** 1.6;
    const fine = 0.88 + 0.12 * Math.sin(u * 13 + Math.sin(v * 9) * 2) * Math.sin(v * 11 + Math.sin(u * 7) * 2);
    const val = Math.min(1, s * 0.42) * edge * fine;
    const i = (y * N + x) * 4;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = Math.round(val * 255); img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true;
  return t;
}

function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// One pool of particles rendered with one blending mode.
class Pool {
  constructor(scene, n, additive, puffTex) {
    this.n = n; this.next = 0; this.additive = additive;
    const f = k => new Float32Array(n * k);
    Object.assign(this, {
      pos: f(3), vel: f(3), life: f(1), max: f(1), size0: f(1), grow: f(1), alpha0: f(1), c0: f(3), c1: f(3),
      grav: f(1), drag: f(1), turb: f(1), rot: f(1), rotV: f(1), kind: f(1), fade: f(1),
    });
    const g = new THREE.BufferGeometry();
    const dyn = (arr, k) => new THREE.BufferAttribute(arr, k).setUsage(THREE.DynamicDrawUsage);
    this.aPos = dyn(this.pos, 3); this.aVel = dyn(this.vel, 3);
    this.aSize = dyn(f(1), 1); this.aAlpha = dyn(f(1), 1); this.aColor = dyn(f(3), 3); this.aKind = dyn(this.kind, 1); this.aRot = dyn(this.rot, 1);
    g.setAttribute("position", this.aPos); g.setAttribute("aVel", this.aVel); g.setAttribute("aSize", this.aSize);
    g.setAttribute("aAlpha", this.aAlpha); g.setAttribute("aColor", this.aColor); g.setAttribute("aKind", this.aKind); g.setAttribute("aRot", this.aRot);
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e6);
    this.uniforms = {
      uScale: { value: 400 }, uViewport: { value: new THREE.Vector2(1, 1) }, uPuff: { value: puffTex },
      fogColor: { value: new THREE.Color(0x000000) }, fogNear: { value: 1e5 }, fogFar: { value: 2e5 }, uAdditive: { value: additive ? 1 : 0 },
    };
    this.points = new THREE.Points(g, new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, uniforms: this.uniforms, transparent: true, depthWrite: false,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    }));
    this.points.frustumCulled = false;
    this.points.renderOrder = additive ? 3 : 2;
    scene.add(this.points);
  }

  // o: {life, size, grow, alpha, color, color1, gravity, drag, turb, kind, rot, fade}
  spawn(px, py, pz, vx, vy, vz, o) {
    const i = this.next; this.next = (this.next + 1) % this.n;
    const j = i * 3;
    this.pos[j] = px; this.pos[j + 1] = py; this.pos[j + 2] = pz;
    this.vel[j] = vx; this.vel[j + 1] = vy; this.vel[j + 2] = vz;
    this.life[i] = this.max[i] = o.life ?? 1;
    this.size0[i] = o.size ?? 0.05; this.grow[i] = o.grow ?? 0; this.alpha0[i] = o.alpha ?? 0.8;
    const c0 = o.color || [1, 1, 1], c1 = o.color1 || c0;
    this.c0[j] = c0[0]; this.c0[j + 1] = c0[1]; this.c0[j + 2] = c0[2];
    this.c1[j] = c1[0]; this.c1[j + 1] = c1[1]; this.c1[j + 2] = c1[2];
    this.grav[i] = o.gravity ?? 0; this.drag[i] = o.drag ?? 0.5; this.turb[i] = o.turb ?? 0;
    this.kind[i] = o.kind ?? DISC; this.rot[i] = Math.random() * 6.283; this.rotV[i] = (Math.random() - 0.5) * (o.spin ?? 1);
    this.fade[i] = o.fade ?? 0.15;                              // fraction of life used to fade in
  }

  update(dt, time) {
    const sz = this.aSize.array, al = this.aAlpha.array, col = this.aColor.array;
    const P = this.pos, V = this.vel;
    for (let i = 0; i < this.n; i++) {
      if (this.life[i] <= 0) { if (al[i] !== 0) al[i] = 0; continue; }
      this.life[i] -= dt;
      const j = i * 3, k = Math.exp(-this.drag[i] * dt), tb = this.turb[i];
      let vx = V[j] * k, vy = V[j + 1] * k - this.grav[i] * dt, vz = V[j + 2] * k;
      if (tb > 0) {                                             // cheap curl-ish swirl field
        const x = P[j], y = P[j + 1], z = P[j + 2];
        vx += tb * dt * (Math.sin(y * 3.1 + time * 1.3) - Math.sin(z * 2.7 + time * 0.9));
        vy += tb * dt * 0.5 * (Math.sin(z * 2.3 + time * 1.1) - Math.sin(x * 3.3 + time * 0.7));
        vz += tb * dt * (Math.sin(x * 2.9 + time * 1.7) - Math.sin(y * 2.1 + time * 1.2));
      }
      V[j] = vx; V[j + 1] = vy; V[j + 2] = vz;
      P[j] += vx * dt; P[j + 1] += vy * dt; P[j + 2] += vz * dt;
      this.rot[i] += this.rotV[i] * dt;
      const t = 1 - Math.max(0, this.life[i]) / this.max[i];
      sz[i] = Math.max(0, this.size0[i] + this.grow[i] * t);
      const fin = this.fade[i] > 0 ? Math.min(1, t / this.fade[i]) : 1;
      al[i] = this.alpha0[i] * fin * (1 - t) * (1 - t * 0.3);
      col[j] = this.c0[j] + (this.c1[j] - this.c0[j]) * t;
      col[j + 1] = this.c0[j + 1] + (this.c1[j + 1] - this.c0[j + 1]) * t;
      col[j + 2] = this.c0[j + 2] + (this.c1[j + 2] - this.c0[j + 2]) * t;
    }
    this.aPos.needsUpdate = this.aVel.needsUpdate = this.aSize.needsUpdate = this.aAlpha.needsUpdate = this.aColor.needsUpdate = this.aKind.needsUpdate = this.aRot.needsUpdate = true;
  }

  clear() { this.life.fill(0); this.aAlpha.array.fill(0); this.aAlpha.needsUpdate = true; }
}

const R = Math.random;
const rs = s => (R() - 0.5) * 2 * s;

export class Particles {
  constructor(scene, capacity = 6000) {
    const tex = puffTexture();
    capacity = Math.min(6000, capacity);
    this.add = new Pool(scene, Math.round(capacity * 0.4), true, tex);    // fire, sparks, embers, glow
    this.blend = new Pool(scene, capacity - this.add.n, false, tex);      // smoke, dust, steam, grit, motes
    this.scene = scene; this.time = 0; this.dt = 1 / 60;
    this._acc = { fire: 0, smoke: 0, motes: 0, steam: 0, heat: 0, ember: 0 };
    if (typeof window !== "undefined") {
      const d = Math.min(window.devicePixelRatio || 1, 2);
      this.setViewport(window.innerWidth * d, window.innerHeight * d, { fov: 68 });
    }
  }

  // Generic emitter (kept for compatibility). opts: {life,size,grow,alpha,color,color1,gravity,drag,turb,kind,additive}
  emit(p, v, opts = {}) {
    const pool = opts.additive ? this.add : this.blend;
    pool.spawn(p.x, p.y, p.z, v.x, v.y, v.z, opts);
  }

  // Bright metal sparks: short streaks thrown off the surface, gravity, fast cooling (white → orange → dark red).
  sparks(point, normal, strength = 1) {
    const n = Math.min(60, Math.round(8 + strength * 22));
    for (let k = 0; k < n; k++) {
      const s = (1.5 + R() * 4.5) * Math.min(1.6, 0.5 + strength);
      const vx = normal.x * s * 0.6 + rs(s * 0.8), vy = normal.y * s * 0.6 + rs(s * 0.6) + s * 0.25, vz = normal.z * s * 0.6 + rs(s * 0.8);
      this.add.spawn(point.x, point.y, point.z, vx, vy, vz, {
        life: 0.18 + R() * 0.45, size: 0.012 + R() * 0.008, alpha: 1.6, kind: STREAK, color: [1, 0.95, 0.75], color1: [1, 0.25, 0.02],
        gravity: 9.81, drag: 0.8, fade: 0,
      });
    }
    // a tiny flash at the contact
    this.add.spawn(point.x, point.y, point.z, 0, 0, 0, { life: 0.08, size: 0.12 * Math.min(1.5, strength + 0.3), alpha: 0.9, color: [1, 0.85, 0.55], color1: [1, 0.4, 0.1], fade: 0 });
  }

  // Grey-brown dust puff kicked off a surface.
  dust(point, normal, strength = 1, color = [0.42, 0.39, 0.35]) {
    const n = Math.min(26, Math.round(5 + strength * 10));
    for (let k = 0; k < n; k++) {
      const s = 0.25 + R() * 0.7 * Math.min(1.5, strength);
      this.blend.spawn(point.x + rs(0.05), point.y + rs(0.05), point.z + rs(0.05),
        normal.x * s + rs(0.5) * strength, normal.y * s + R() * 0.3, normal.z * s + rs(0.5) * strength, {
          life: 1.4 + R() * 1.6, size: 0.06 + R() * 0.08, grow: 0.35 + R() * 0.4, alpha: 0.38, kind: PUFF,
          color, color1: [color[0] * 1.1, color[1] * 1.1, color[2] * 1.1], gravity: -0.03, drag: 2.2, turb: 0.25, spin: 0.8, fade: 0.08,
        });
    }
  }

  // Small dark chips of grit thrown off concrete / brick / wood.
  grit(point, normal, strength, color) {
    const n = Math.min(30, Math.round(4 + strength * 12));
    for (let k = 0; k < n; k++) {
      const s = 0.8 + R() * 2.2 * Math.min(1.5, strength);
      this.blend.spawn(point.x, point.y, point.z, normal.x * s + rs(s * 0.7), normal.y * s + R() * s * 0.6, normal.z * s + rs(s * 0.7), {
        life: 0.4 + R() * 0.6, size: 0.008 + R() * 0.01, alpha: 0.95, kind: STREAK, color, color1: color, gravity: 9.81, drag: 0.4, fade: 0,
      });
    }
  }

  // Steam jet from a leak: fast white core that slows, widens and fades.
  steam(p, dir, rate, dt) {
    this._acc.steam += rate * dt;
    while (this._acc.steam >= 1) {
      this._acc.steam -= 1;
      const s = 2.2 + R() * 1.4;
      this.blend.spawn(p.x, p.y, p.z, dir.x * s + rs(0.25), dir.y * s + rs(0.25), dir.z * s + rs(0.25), {
        life: 1.2 + R() * 0.9, size: 0.04, grow: 0.9 + R() * 0.5, alpha: 0.32, kind: PUFF, color: [0.86, 0.88, 0.9], color1: [0.7, 0.72, 0.75],
        gravity: -0.35, drag: 1.9, turb: 0.6, spin: 1.2, fade: 0.05,
      });
    }
  }

  // Overheating machine: faint rising heat wisps and the odd glowing fleck.
  heat(p, rate, dt) {
    this._acc.heat += rate * dt;
    while (this._acc.heat >= 1) {
      this._acc.heat -= 1;
      this.blend.spawn(p.x + rs(0.5), p.y, p.z + rs(0.35), rs(0.05), 0.35 + R() * 0.3, rs(0.05), {
        life: 1.6 + R(), size: 0.08, grow: 0.5, alpha: 0.09, kind: PUFF, color: [0.35, 0.33, 0.31], color1: [0.3, 0.29, 0.28], turb: 0.4, gravity: -0.1, drag: 0.6,
      });
      if (R() < 0.15) this.add.spawn(p.x + rs(0.4), p.y, p.z + rs(0.3), rs(0.05), 0.4 + R() * 0.3, rs(0.05), {
        life: 0.9, size: 0.012, alpha: 0.8, color: [1, 0.5, 0.15], color1: [0.6, 0.1, 0.02], turb: 0.5, gravity: -0.15, drag: 0.4,
      });
    }
  }

  // Burning debris pile: layered additive flame puffs (yellow core → orange → deep red), rising embers, some smoke.
  fire(pos, width = 1, depth = 1, dt = 1 / 60) {
    const area = Math.max(0.1, width * depth);
    this._acc.fire += 220 * area * dt;
    while (this._acc.fire >= 1) {
      this._acc.fire -= 1;
      const x = pos.x + rs(width * 0.5) * (0.3 + R() * 0.7), z = pos.z + rs(depth * 0.5) * (0.3 + R() * 0.7);
      const centre = 1 - Math.min(1, Math.hypot((x - pos.x) / (width * 0.5), (z - pos.z) / (depth * 0.5)));
      const hot = 0.55 + 0.45 * centre;
      // flame body: orange tongues that rise, stretch out and cool to deep red
      this.add.spawn(x, pos.y + R() * 0.08, z, rs(0.1), 0.9 + R() * 1.1 * hot, rs(0.1), {
        life: 0.45 + R() * 0.55 * hot, size: 0.26 + R() * 0.24 * hot, grow: -0.16, alpha: 0.75 * hot, kind: PUFF,
        color: [1, 0.55 + 0.3 * hot, 0.18 * hot], color1: [0.5, 0.06, 0.01], gravity: -1.6, drag: 1.3, turb: 1.8, spin: 3, fade: 0.12,
      });
      // hot core near the fuel: small, bright yellow-white, short lived
      if (R() < 0.45) this.add.spawn(x * 0.6 + pos.x * 0.4, pos.y + 0.03, z * 0.6 + pos.z * 0.4, rs(0.05), 0.5 + R() * 0.5, rs(0.05), {
        life: 0.22 + R() * 0.2, size: 0.18 + R() * 0.1, grow: -0.1, alpha: 0.9, kind: PUFF,
        color: [1, 0.92, 0.6], color1: [1, 0.55, 0.12], gravity: -1.0, drag: 1.5, turb: 1.0, spin: 2, fade: 0.05,
      });
    }
    this._acc.ember += 9 * area * dt;
    while (this._acc.ember >= 1) {
      this._acc.ember -= 1;
      this.add.spawn(pos.x + rs(width * 0.4), pos.y + 0.2, pos.z + rs(depth * 0.4), rs(0.4), 1.2 + R() * 1.4, rs(0.4), {
        life: 1.5 + R() * 2, size: 0.01 + R() * 0.008, alpha: 1.4, kind: STREAK, color: [1, 0.7, 0.25], color1: [0.7, 0.12, 0.02],
        gravity: -0.4, drag: 0.7, turb: 2.2, fade: 0,
      });
    }
    this.smoke({ x: pos.x, y: pos.y + 0.7, z: pos.z }, 10 * area, dt);
  }

  // Dark billowing smoke: rises, widens and slows; lit-looking grey-brown, never glowing.
  smoke(pos, rate = 10, dt = 1 / 60) {
    this._acc.smoke += rate * dt;
    while (this._acc.smoke >= 1) {
      this._acc.smoke -= 1;
      const d = R();
      this.blend.spawn(pos.x + rs(0.2), pos.y, pos.z + rs(0.2), rs(0.15), 0.45 + R() * 0.35, rs(0.15), {
        life: 4 + R() * 3, size: 0.25 + R() * 0.15, grow: 1.6 + R() * 1.2, alpha: 0.42 + d * 0.15, kind: PUFF,
        color: [0.07 + d * 0.03, 0.065 + d * 0.03, 0.06 + d * 0.025], color1: [0.16, 0.15, 0.14], gravity: -0.08, drag: 0.55, turb: 0.5, spin: 0.5, fade: 0.08,
      });
    }
  }

  // Slow drifting dust motes around a point (visible in torch beams / sun shafts).
  motes(center, radius = 3, dt = 1 / 60) {
    this._acc.motes += radius * radius * 2.5 * dt;
    while (this._acc.motes >= 1) {
      this._acc.motes -= 1;
      const b = 0.55 + R() * 0.35;
      this.blend.spawn(center.x + rs(radius), center.y + rs(radius * 0.5), center.z + rs(radius), rs(0.03), rs(0.015) - 0.005, rs(0.03), {
        life: 6 + R() * 5, size: 0.006 + R() * 0.006, alpha: 0.55, color: [b, b * 0.95, b * 0.85], turb: 0.03, drag: 0.2, fade: 0.25,
      });
    }
  }

  // Material-aware cage impact.
  impact(point, normal, speed, material = "concrete") {
    const s = Math.min(2, speed / 2.5);
    if (s < 0.05) return;
    switch (material) {
      case "metal":
        if (speed > 0.6) this.sparks(point, normal, s);
        this.dust(point, normal, s * 0.35, [0.36, 0.35, 0.34]);
        break;
      case "wood":
        this.dust(point, normal, s * 0.8, [0.47, 0.38, 0.27]);
        this.grit(point, normal, s * 0.6, [0.33, 0.24, 0.15]);
        break;
      case "brick":
        this.dust(point, normal, s, [0.5, 0.36, 0.29]);
        this.grit(point, normal, s, [0.36, 0.2, 0.15]);
        break;
      case "concrete":
        this.dust(point, normal, s, [0.47, 0.45, 0.42]);
        this.grit(point, normal, s, [0.25, 0.24, 0.23]);
        break;
      default:
        this.dust(point, normal, s * 0.7);
    }
  }

  // Light continuous particles while the cage slides along a surface (call every frame while sliding).
  scrape(point, normal, slipSpeed, material = "concrete") {
    if (slipSpeed < 0.05) return;
    const p = Math.min(1, slipSpeed * this.dt * 18);
    if (R() > p) return;
    if (material === "metal") {
      if (slipSpeed > 0.4) for (let k = 0; k < 3; k++) this.add.spawn(point.x, point.y, point.z,
        normal.x * 1.2 + rs(1.5), normal.y * 1.2 + R(), normal.z * 1.2 + rs(1.5), {
          life: 0.15 + R() * 0.25, size: 0.008, alpha: 1.4, kind: STREAK, color: [1, 0.9, 0.6], color1: [1, 0.3, 0.05], gravity: 9.81, drag: 1, fade: 0,
        });
    } else {
      const col = material === "brick" ? [0.5, 0.37, 0.3] : material === "wood" ? [0.47, 0.39, 0.29] : [0.45, 0.43, 0.4];
      this.blend.spawn(point.x, point.y, point.z, normal.x * 0.2 + rs(0.15), normal.y * 0.2 + R() * 0.1, normal.z * 0.2 + rs(0.15), {
        life: 0.9 + R() * 0.8, size: 0.03, grow: 0.18, alpha: 0.28, kind: PUFF, color: col, gravity: -0.02, drag: 2.5, turb: 0.2, fade: 0.1,
      });
    }
  }

  update(dt, camera = null) {
    this.dt = dt; this.time += dt;
    // keep sprite size and fog in sync with the renderer / scene
    const fog = this.scene.fog;
    for (const pool of [this.add, this.blend]) {
      const u = pool.uniforms;
      if (fog && fog.isFog) { u.fogColor.value.copy(fog.color); u.fogNear.value = fog.near; u.fogFar.value = fog.far; }
      else { u.fogNear.value = 1e5; u.fogFar.value = 2e5; }
      if (camera && camera.isPerspectiveCamera) {
        const h = (typeof window !== "undefined" ? window.innerHeight : 800) * (typeof window !== "undefined" ? Math.min(window.devicePixelRatio || 1, 2) : 1);
        u.uScale.value = h / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));
        u.uViewport.value.set((typeof window !== "undefined" ? window.innerWidth : 1280) * (typeof window !== "undefined" ? Math.min(window.devicePixelRatio || 1, 2) : 1), h);
      }
      pool.update(dt, this.time);
    }
  }

  // Set the sprite scale from the active viewport (call before rendering a viewport of a different size, e.g. PiP).
  setViewport(widthPx, heightPx, camera) {
    for (const pool of [this.add, this.blend]) {
      pool.uniforms.uScale.value = heightPx / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));
      pool.uniforms.uViewport.value.set(widthPx, heightPx);
    }
  }

  clear() { this.add.clear(); this.blend.clear(); for (const k in this._acc) this._acc[k] = 0; }
}
