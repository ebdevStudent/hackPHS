// HackPHS ball drone: 85 mm Meteor85 whoop — 1103 11000KV, Gemfan 2015 2-blade, F411 AIO, Caddx Ant, 2S LiHV — on the
// P1B two-ring gimbal, with no outer cage. The outer ring (R 96.5 mm) is the outermost part and takes the contacts.
//
// Gimbal chain (docs/22 §3, CAD cage →Z→ outer →X→ inner →Y→ aircraft, here in three.js axes with Y up): a virtual,
// freely rotating support frame →Y (yaw)→ outer ring →X→ inner ring →Z (fore-aft)→ aircraft. Ø2 mm steel pins turn in
// MR52ZZ bearings at every pivot. The aircraft stays level under its flight controller while the rings swing round it.
//
// Physics (SI): one translating rigid body (all-up mass from spec.js) + the freely rotating gimbal (decoupled from the
// aircraft by the bearings). Contacts use the outer ring's envelope, a sphere of the ring radius: each contact gets a
// rigid-body impulse with its lever arm (normal: speed-dependent restitution; tangential: Coulomb friction, PETG μ 0.3;
// a small rolling resistance), so the drone bumps, slides and rolls on walls and floors and the rings spin up.
// Thrust is limited by the 2S LiHV pack: open-circuit voltage vs charge, internal-resistance sag, thrust ∝ V².
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { buildSpec, GIMBAL, MOTOR, motorPower, cellOCV, INSTALL_LOSS, AVIONICS_W, INSPECTION_LED_W } from "./spec.js";

export const P = {
  R: GIMBAL.envelope, g: 9.81, rho: 1.225,
  motorTau: 0.02, attTau: 0.05, maxTilt: THREE.MathUtils.degToRad(35),   // Betaflight-tuned whoop, indoor angle limit
  vMax: 3.0, climbMax: 1.6, yawRateMax: 2.2,
  CdA: 0.0045, rotorDrag: 0.03,
  gimbalFric: 3e-6, ringAirDrag: 4e-7,
};
const UP = new THREE.Vector3(0, 1, 0), AX = new THREE.Vector3(1, 0, 0), AZ = new THREE.Vector3(0, 0, 1);

// ---------------------------------------------------------------- gimbal geometry (procedural, built along +Y)
// A flat ring band: outer and inner cylinder faces plus the two flat edges (double-sided material lights the inside).
function bandGeometry(rOut, band, width, seg = 96) {
  const rIn = rOut - band;
  const faces = [new THREE.CylinderGeometry(rOut, rOut, width, seg, 1, true), new THREE.CylinderGeometry(rIn, rIn, width, seg, 1, true)];
  for (const s of [1, -1]) { const e = new THREE.RingGeometry(rIn, rOut, seg); e.rotateX(-s * Math.PI / 2); e.translate(0, s * width / 2, 0); faces.push(e); }
  return mergeGeometries(faces);
}
// Cylinder of radius r and length len along an axis ("x" | "y" | "z"), centred at c.
function rodGeometry(r, len, axis, c, seg = 12) {
  const g = new THREE.CylinderGeometry(r, r, len, seg);
  if (axis === "x") g.rotateZ(Math.PI / 2); else if (axis === "z") g.rotateX(Math.PI / 2);
  return g.translate(c[0], c[1], c[2]);
}
function boxGeometry(sx, sy, sz, c) { return new THREE.BoxGeometry(sx, sy, sz).translate(c[0], c[1], c[2]); }

// Rings in contrasting colours (outer orange, inner blue) with dark bearing blocks and bright steel pins/bearings.
function gimbalMaterials() {
  const ring = color => new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.22, roughness: 0.45, metalness: 0.05, side: THREE.DoubleSide });
  return {
    outer: ring(0xff6a13), inner: ring(0x1f6fff),
    block: new THREE.MeshStandardMaterial({ color: 0x26292e, roughness: 0.55, metalness: 0.25 }),
    steel: new THREE.MeshStandardMaterial({ color: 0xdfe3e8, roughness: 0.22, metalness: 1 }),
    arm: new THREE.MeshStandardMaterial({ color: 0x141414, roughness: 0.45, metalness: 0.3 }),
    tab: new THREE.MeshStandardMaterial({ color: 0xf2f2f2, emissive: 0xffffff, emissiveIntensity: 0.15, roughness: 0.5 }),
  };
}

// Builds the two rings and the aircraft's own pivot arms. Each pivot: a bearing block on the ring that carries the
// MR52ZZ bearing (steel race facing the pin) and the Ø2 mm pin from the neighbouring part, on the rotation axis.
function buildGimbal(outer, inner, quad, support) {
  const M = gimbalMaterials(), O = GIMBAL.outer, I = GIMBAL.inner, pin = GIMBAL.pin, br = GIMBAL.bearing.od / 2, bw = GIMBAL.bearing.w;
  const mesh = (geos, mat, parent) => { const m = new THREE.Mesh(mergeGeometries(geos), mat); parent.add(m); return m; };
  const iMid = I.r - I.band / 2, oMid = O.r - O.band / 2, iIn = I.r - I.band, oIn = O.r - O.band;

  // inner ring: horizontal at rest (axis Y); aircraft pivots on ±Z, outer-ring pivots on ±X
  mesh([bandGeometry(I.r, I.band, I.width)], M.inner, inner);
  const ib = [], is = [];
  for (const s of [1, -1]) {
    ib.push(boxGeometry(0.012, I.width + 0.003, 0.010, [0, 0, s * iMid]));                    // aircraft-pivot bearing block
    is.push(rodGeometry(br, bw, "z", [0, 0, s * (iIn - 0.0022)], 16));                       // its bearing, facing the aircraft pin
    ib.push(boxGeometry(0.007, I.width + 0.002, 0.012, [s * iMid, 0, 0]));                    // collar holding the outer-ring pin
    is.push(rodGeometry(pin, oIn - iMid + 0.004, "x", [s * (iMid + oIn + 0.004) / 2, 0, 0])); // pin bridging into the outer ring
  }
  mesh(ib, M.block, inner); mesh(is, M.steel, inner);

  // outer ring: vertical at rest, facing the chase camera (axis Z); inner-ring pivots on ±X, yaw pivots on ±Y
  const band = bandGeometry(O.r, O.band, O.width); band.rotateX(Math.PI / 2);
  mesh([band], M.outer, outer);
  const ob = [], os = [];
  for (const s of [1, -1]) {
    ob.push(boxGeometry(0.010, 0.012, O.width + 0.003, [s * oMid, 0, 0]));                    // inner-pivot bearing block
    os.push(rodGeometry(br, bw, "x", [s * (oIn - 0.0006), 0, 0], 16));                       // its bearing, facing the inner ring
    ob.push(boxGeometry(0.012, 0.008, O.width + 0.003, [0, s * (oMid + 0.0005), 0]));         // yaw-pivot bearing block
    os.push(rodGeometry(br, bw, "y", [0, s * (oMid + 0.0045 + bw / 2 - 0.0003), 0], 16));     // yaw bearing on its outer face
    os.push(rodGeometry(pin, 0.012, "y", [0, s * (oMid + 0.008), 0]));                        // yaw pin on the vertical axis
  }
  mesh(ob, M.block, outer); mesh(os, M.steel, outer);

  // yaw hubs: what is left of the outer support at the yaw pins (no cage). They turn with the free support frame, and
  // the white index tab shows the yaw rotation that the rings themselves cannot show.
  const hb = [], ht = [];
  for (const s of [1, -1]) {
    hb.push(rodGeometry(0.0045, 0.003, "y", [0, s * (GIMBAL.envelope - 0.002), 0], 20));
    ht.push(boxGeometry(0.010, 0.0022, 0.003, [0.006, s * (GIMBAL.envelope - 0.002), 0]));
  }
  mesh(hb, M.block, support); mesh(ht, M.tab, support);

  // aircraft: carbon arms out along ±Z (under the props, clear of the disks) ending in the pins of the inner ring
  const qa = [], qp = [];
  for (const s of [1, -1]) {
    qa.push(rodGeometry(0.0012, iIn - 0.016, "z", [0, 0.001, s * (0.012 + iIn - 0.004) / 2]));
    qa.push(boxGeometry(0.006, 0.006, 0.005, [0, 0.001, s * (iIn - 0.006)]));                // TPU pin clamp
    qp.push(rodGeometry(pin, 0.012, "z", [0, 0, s * (iIn + 0.002)]));
  }
  mesh(qa, M.arm, quad); mesh(qp, M.steel, quad);
}

// The CAD aircraft carries pivot arms/pins along X for the old cage gimbal; drop those triangles (they would point
// into nothing now that the aircraft pivots about Z).
function stripTriangles(mesh, drop) {
  const g = mesh.geometry, pos = g.attributes.position, idx = g.index; if (!idx) return;
  const keep = [], v = new THREE.Vector3();
  for (let t = 0; t < idx.count; t += 3) {
    let out = true;
    for (let k = 0; k < 3; k++) { v.fromBufferAttribute(pos, idx.getX(t + k)); if (!drop(v)) { out = false; break; } }
    if (!out) keep.push(idx.getX(t), idx.getX(t + 1), idx.getX(t + 2));
  }
  g.setIndex(keep);
}

// ---------------------------------------------------------------- model
const _q = new THREE.Quaternion(), _qa = new THREE.Quaternion(), _e = new THREE.Euler();
export class DroneModel {
  constructor() {
    this.root = new THREE.Group(); this.ready = false; this.props = [];
    this.quad = new THREE.Group(); this.outerRing = new THREE.Group(); this.innerRing = new THREE.Group(); this.support = new THREE.Group();
    this.root.add(this.support, this.outerRing, this.innerRing, this.quad);
    this.gimbalAngles = { yaw: 0, outer: 0, inner: 0 };
    // Caddx Ant (1.8 mm lens, very wide) — repositioned onto the model's camera mount after loading
    this.fpv = new THREE.PerspectiveCamera(105, 16 / 9, 0.005, 150);
    this.fpv.position.set(0, 0.012, -0.03); this.fpv.rotation.x = THREE.MathUtils.degToRad(12);
    this.light = new THREE.SpotLight(0xf4f6ff, 0, 10, THREE.MathUtils.degToRad(38), 0.6, 1.8);   // switchable inspection LEDs
    this.light.position.set(0, 0.008, -0.035); this.light.target.position.set(0, 0.25, -2.5);
    this.quad.add(this.fpv, this.light, this.light.target);
  }

  async load(url) {
    const gltf = await new GLTFLoader().loadAsync(url);
    const quad = gltf.scene.getObjectByName("quad");                     // the cage and CAD rings are not used any more
    if (quad) [...quad.children].forEach(c => this.quad.add(c));
    const xMount = v => Math.abs(v.x) > 0.04 && Math.abs(v.z) < 0.02;     // the old X-axis pivot arms, pins and collars
    this.quad.traverse(o => {
      if (!o.isMesh) return;
      if (o.name === "quad_Carbon_rod_1mm") o.visible = false;
      else if (o.name === "quad_Steel_pin" || o.name === "quad_TPU_black") stripTriangles(o, xMount);
    });
    buildGimbal(this.outerRing, this.innerRing, this.quad, this.support);
    const cam = this.quad.getObjectByName("fpv_cam");
    if (cam) { this.fpv.position.copy(cam.position); this.fpv.quaternion.copy(cam.quaternion); }
    const led = this.quad.getObjectByName("inspection_light");
    if (led) { this.light.position.copy(led.position); const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(led.quaternion); this.light.target.position.copy(led.position).addScaledVector(dir, 2.5); }
    for (let k = 0; k < 4; k++) {
      const p = this.quad.getObjectByName("prop_" + k); if (!p) continue;
      const disc = new THREE.Mesh(new THREE.CircleGeometry(0.0254, 24), new THREE.MeshBasicMaterial({ color: k < 2 ? 0x2a6cc8 : 0x6a7078, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
      disc.rotation.x = -Math.PI / 2; p.add(disc);
      p.userData = { dir: k % 2 ? -1 : 1, disc, blades: p.children.filter(c => c !== disc) };
      this.props.push(p);
    }
    this.root.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = false; o.layers.set(1); } });
    for (const ring of [this.outerRing, this.innerRing, this.support]) ring.traverse(o => { if (o.isMesh) o.layers.enable(2); });   // rings swing through the FPV video
    this.fpv.layers.enable(2);
    this.ready = true;
  }

  // qd: aircraft attitude, qs: the gimbal's free support frame. support →Y→ outer →X→ inner →Z→ aircraft, so
  // qd⁻¹·qs = Rz(inner)·Rx(outer)·Ry(yaw) — a "ZXY" Euler split; each ring turns only about its own pivot axis.
  pose(pos, qd, qs, thrustFrac, dt) {
    this.root.position.copy(pos);
    this.quad.quaternion.copy(qd); this.support.quaternion.copy(qs);
    _e.setFromQuaternion(_q.copy(qd).invert().multiply(qs), "ZXY");
    this.innerRing.quaternion.copy(qd).multiply(_qa.setFromAxisAngle(AZ, _e.z));
    this.outerRing.quaternion.copy(this.innerRing.quaternion).multiply(_qa.setFromAxisAngle(AX, _e.x));
    this.gimbalAngles.inner = _e.z; this.gimbalAngles.outer = _e.x; this.gimbalAngles.yaw = _e.y;
    const spin = thrustFrac > 0.01 ? 40 + 30 * thrustFrac : 0;
    for (const p of this.props) {
      p.rotation.y += p.userData.dir * spin * dt;
      p.userData.disc.material.opacity = Math.min(0.3, thrustFrac * 0.55);
      for (const b of p.userData.blades) b.visible = thrustFrac < 0.12 || Math.random() < 0.55;
    }
  }
}

// ---------------------------------------------------------------- physics
const _cands = [], _hits = [];
function gauss() { return Math.sqrt(-2 * Math.log(Math.random() + 1e-12)) * Math.cos(2 * Math.PI * Math.random()); }

export class Drone {
  constructor() {
    this.model = new DroneModel();
    this.setBattery(550);
    this.reset(new THREE.Vector3(0, 1, 0), 0);
  }

  setBattery(capacityMah) { this.spec = buildSpec(capacityMah); this.mass = this.spec.mass; this.I = this.spec.I; }

  reset(pos, yaw) {
    this.pos = pos.clone(); this.vel = new THREE.Vector3();
    this.qc = new THREE.Quaternion(); this.w = new THREE.Vector3();
    this.yaw = yaw; this.yawRate = 0; this.pitch = 0; this.roll = 0;
    this.thrust = this.mass * P.g; this.armed = true; this.spool = 1; this.leds = false;
    this.soc = 1; this.mAh = 0; this.voltage = 2 * cellOCV(1); this.current = 0; this.battery = 1; this.lowV = false; this.landing = false;
    this.turb = new THREE.Vector2(); this.nearSurface = 0;
    this.t = { contact: "FREE", normalForce: 0, slip: 0, impact: 0, impactT: -9, contacts: 0, peakG: 0, power: 0, spinRpm: 0, mat: null, touchPoint: null, touchNormal: null, points: 0 };
    this.lastImpact = null;
  }

  setArmed(on) { if (on === this.armed) return; this.armed = on; if (on) { this.spool = 0; this.turb.set(0, 0); } }
  get forward() { return new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw)); }
  get right() { return new THREE.Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw)); }
  thrustMax() { return this.spec.thrustMax_N * (this.voltage / MOTOR.refVolt) ** 2; }       // available thrust follows pack voltage
  thrustFrac() { const tm = this.spec.thrustMax_N; return this.armed ? Math.max(this.thrust / tm, 0.04 * this.spool) : this.thrust / tm; }
  quadQuat() {
    return new THREE.Quaternion().setFromAxisAngle(UP, this.yaw).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(-this.pitch, 0, -this.roll, "XYZ")));
  }

  step(dt, input, world, time) {
    const g = P.g, m = this.mass;
    if (this.landing) input = { fwd: 0, strafe: 0, turn: 0, lift: -0.5 };                 // low-voltage auto-land
    if (!this.armed) input = { fwd: 0, strafe: 0, turn: 0, lift: 0 };
    this.spool = this.armed ? Math.min(1, this.spool + dt / 0.4) : 0;

    // ---- flight controller (velocity + altitude hold on top of Betaflight-style angle control) ----
    const f = this.forward, r = this.right;
    const vCmd = f.clone().multiplyScalar(input.fwd * P.vMax).addScaledVector(r, input.strafe * P.vMax * 0.85);
    const aCmd = vCmd.sub(new THREE.Vector3(this.vel.x, 0, this.vel.z)).multiplyScalar(2.5);
    const aMax = g * Math.tan(P.maxTilt); if (aCmd.length() > aMax) aCmd.setLength(aMax);
    const pitchCmd = this.armed ? Math.atan2(aCmd.dot(f), g) : 0, rollCmd = this.armed ? Math.atan2(aCmd.dot(r), g) : 0;
    const ka = 1 - Math.exp(-dt / (this.armed ? P.attTau : 0.3));
    const sig = THREE.MathUtils.degToRad(0.5 + 1.2 * this.nearSurface) * (this.thrust > 0.2 ? 1 : 0), kick = sig * Math.sqrt(2 * dt / 0.4);
    this.turb.x += -this.turb.x * dt / 0.4 + kick * gauss(); this.turb.y += -this.turb.y * dt / 0.4 + kick * gauss();
    this.pitch += (pitchCmd + this.turb.x - this.pitch) * ka; this.roll += (rollCmd + this.turb.y - this.roll) * ka;
    this.yawRate += (input.turn * P.yawRateMax - this.yawRate) * (1 - Math.exp(-dt / 0.1));
    this.yaw += this.yawRate * dt;
    const azCmd = THREE.MathUtils.clamp(3.2 * (input.lift * P.climbMax - this.vel.y), -7, 12);
    const Tavail = this.thrustMax();
    let Tcmd = THREE.MathUtils.clamp(m * (g + azCmd) / Math.max(0.5, Math.cos(this.pitch) * Math.cos(this.roll)), 0, Tavail);
    if (!this.armed) Tcmd = 0; else if (this.spool < 1) Tcmd = Math.min(Tcmd, Tavail * 0.05 + this.spool * this.spool * Tcmd);
    this.thrust += (Tcmd - this.thrust) * (1 - Math.exp(-dt / P.motorTau));

    // ---- forces ----
    const F = UP.clone().applyQuaternion(this.quadQuat()).multiplyScalar(this.thrust);
    F.y -= m * g;
    F.addScaledVector(this.vel, -0.5 * P.rho * P.CdA * this.vel.length());
    F.x -= P.rotorDrag * this.vel.x; F.z -= P.rotorDrag * this.vel.z;
    this.vel.addScaledVector(F, dt / m);
    const tau = this.w.clone().sub(new THREE.Vector3(0, this.yawRate, 0)).multiplyScalar(-P.gimbalFric).addScaledVector(this.w, -P.ringAirDrag * this.w.length());
    this.w.addScaledVector(tau, dt / this.I);
    this.pos.addScaledVector(this.vel, dt);

    // ---- contacts on the outer ring's envelope (sphere of radius P.R) ----
    const T = this.t, velBefore = this.vel.clone(), Rg = P.R;
    let impact = 0, impactPt = null, impactN = null, impactMat = null, Nsum = 0, slip = 0, touching = 0, touchMat = null, touchPt = null, touchN = null, floor = false;
    world.near(this.pos, Rg + 0.01, _cands);
    if (_cands.length) {
      const contacts = [];
      for (const h of world.contactsIn(_cands, this.pos, Rg, _hits)) contacts.push({ n: h.n, depth: h.depth, r: h.n.clone().multiplyScalar(-Rg), mu: GIMBAL.mu * (h.mat === "metal" ? 0.8 : 1), mat: h.mat, point: h.point });
      if (contacts.length) {
        // position: resolve the deepest penetration along each distinct normal
        const push = new THREE.Vector3();
        for (const c of contacts) { const need = c.depth - push.dot(c.n); if (need > 0) push.addScaledVector(c.n, need); }
        this.pos.add(push);
        let deepest = 0;
        for (const c of contacts) { touching++; if (c.n.y > 0.7) floor = true; if (c.depth >= deepest) { deepest = c.depth; touchMat = c.mat; touchPt = c.point; touchN = c.n; } }
        for (let iter = 0; iter < 3; iter++) {
          for (const c of contacts) {
            const vc = this.vel.clone().add(new THREE.Vector3().crossVectors(this.w, c.r));
            const vn = vc.dot(c.n);
            if (vn >= 0) continue;
            const e = iter > 0 ? 0 : (-vn > 0.6 ? GIMBAL.e : -vn > 0.15 ? GIMBAL.e * (-vn - 0.15) / 0.45 : 0);
            const rn = new THREE.Vector3().crossVectors(c.r, c.n);
            const jn = -(1 + e) * vn / (1 / m + rn.lengthSq() / this.I);
            this.vel.addScaledVector(c.n, jn / m); this.w.addScaledVector(rn, jn / this.I);
            if (iter === 0 && -vn > impact) { impact = -vn; impactPt = c.point.clone(); impactN = c.n.clone(); impactMat = c.mat; }
            Nsum += jn / dt;
            // rolling resistance: the ring band is not a perfect ball, so rolling about the contact loses a little
            const wt = this.w.clone().addScaledVector(c.n, -this.w.dot(c.n)), wtl = wt.length();
            if (wtl > 1e-6) this.w.addScaledVector(wt, -Math.min(wtl, GIMBAL.rollRes * Rg * jn / this.I) / wtl);
            // Coulomb friction at the contact point
            const vc2 = this.vel.clone().add(new THREE.Vector3().crossVectors(this.w, c.r));
            const vt = vc2.addScaledVector(c.n, -vc2.dot(c.n)), vtl = vt.length();
            if (vtl > 1e-6) {
              const t = vt.divideScalar(vtl), rt = new THREE.Vector3().crossVectors(c.r, t);
              const kT = 1 / m + rt.lengthSq() / this.I, jt = Math.min(vtl / kT, c.mu * jn);
              this.vel.addScaledVector(t, -jt / m); this.w.addScaledVector(rt, -jt / this.I);
              slip = Math.max(slip, vtl - jt * kT);
            }
          }
        }
      }
    }
    const wl = this.w.length();
    if (wl > 1e-6) this.qc.premultiply(new THREE.Quaternion().setFromAxisAngle(this.w.clone().divideScalar(wl), wl * dt)).normalize();

    // ---- 2S LiHV battery: OCV(soc) − I·Rint; thrust available ∝ V² ----
    const perMotor_g = this.thrust / 4 / g * 1000;
    const Pw = (this.armed ? 4 * motorPower(perMotor_g) * INSTALL_LOSS : 0) + AVIONICS_W + (this.leds ? INSPECTION_LED_W : 0);
    const ocv = 2 * cellOCV(this.soc), Rint = this.spec.battery.Rint;
    this.current = (ocv - Math.sqrt(Math.max(0, ocv * ocv - 4 * Rint * Pw))) / (2 * Rint);       // solve P = (OCV − I·R)·I
    this.voltage = ocv - this.current * Rint;
    this.mAh += this.current * dt / 3.6;
    this.soc = Math.max(0, 1 - this.mAh / this.spec.capacityMah);
    this.battery = this.soc;
    this.lowV = this.voltage / 2 < 3.5;
    if (this.voltage / 2 < 3.3 || this.soc <= 0.02) this.landing = true;                    // Betaflight-style low-voltage land

    // ---- telemetry ----
    T.power = Pw; T.points = touching; T.normalForce = touching ? Nsum : 0; T.slip = slip; T.mat = touchMat; T.touchPoint = touchPt; T.touchNormal = touchN; T.spinRpm = wl * 60 / (2 * Math.PI);
    T.contact = !touching ? "FREE" : impact > 0.6 ? "IMPACT" : slip > 0.05 ? "SLIDING" : wl > 0.5 ? "ROLLING" : "RESTING";
    if (Math.floor(time * 20) !== this._probeT) { this._probeT = Math.floor(time * 20); this.nearSurface = world.near(this.pos, P.R + 0.2, _cands).length ? 1 : 0; }
    this.landed = floor && this.thrust < m * g;
    if (impact > 0.3) {
      T.contacts++; T.impact = impact; T.impactT = time; T.peakG = velBefore.sub(this.vel).length() / 0.008 / g;
      this.lastImpact = { speed: impact, point: impactPt, normal: impactN, mat: impactMat || "concrete" };
    } else this.lastImpact = null;
    return this.lastImpact;
  }

  render(dt) { if (this.model.ready) this.model.pose(this.pos, this.quadQuat(), this.qc, this.thrustFrac(), dt); }
}
