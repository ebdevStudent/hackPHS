// HackPHS ball drone (V1 per the project document): 85 mm Meteor85 whoop — 1103 11000KV, Gemfan 2015 2-blade, F411 AIO,
// Caddx Ant, 2S LiHV — in a ~225 mm ICOSAHEDRAL cage (12 TPU 5-way hubs + 30 × 1 mm carbon rods) on a 2-ring gimbal.
//
// Physics (SI): one translating rigid body (all-up mass from spec.js) + a freely rotating cage (gimbal-decoupled) whose
// contacts are its real hubs and rods. Each contact gets a rigid-body impulse with its lever arm (normal: speed-dependent
// restitution; tangential: Coulomb friction μ = 0.75 TPU hub / 0.30 carbon rod), so the cage tips over edges and
// vertices like a real icosahedron instead of rolling like a perfect ball. Thrust is limited by the 2S LiHV pack:
// open-circuit voltage vs charge, internal-resistance sag under load, thrust ∝ V².
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { buildSpec, CAGE, MOTOR, motorPower, cellOCV, INSTALL_LOSS, AVIONICS_W, INSPECTION_LED_W } from "./spec.js";

export const P = {
  R: CAGE.circumradius + CAGE.hubRadius, g: 9.81, rho: 1.225,
  motorTau: 0.02, attTau: 0.05, maxTilt: THREE.MathUtils.degToRad(35),   // Betaflight-tuned whoop, indoor angle limit
  vMax: 3.0, climbMax: 1.6, yawRateMax: 2.2,
  CdA: 0.0045, rotorDrag: 0.03,
  gimbalFric: 3e-6, cageAirDrag: 4e-7,
};
const UP = new THREE.Vector3(0, 1, 0);

// ---------------------------------------------------------------- cage geometry (cage-local, Y = pole axis)
export function icosahedronGeometry(R = CAGE.circumradius) {
  const phi = (1 + Math.sqrt(5)) / 2;
  let v = [];
  for (const a of [-1, 1]) for (const b of [-1, 1]) v.push(new THREE.Vector3(0, a, b * phi), new THREE.Vector3(a, b * phi, 0), new THREE.Vector3(b * phi, 0, a));
  const q = new THREE.Quaternion().setFromUnitVectors(v[0].clone().normalize(), UP);     // a vertex on the pole axis
  v = v.map(p => p.applyQuaternion(q).setLength(R));
  return v;
}
export function cageContactPoints(hubs) {
  let edge = Infinity;
  for (let j = 1; j < hubs.length; j++) edge = Math.min(edge, hubs[0].distanceTo(hubs[j]));
  const rods = [];
  for (let i = 0; i < hubs.length; i++) for (let j = i + 1; j < hubs.length; j++) if (Math.abs(hubs[i].distanceTo(hubs[j]) - edge) < edge * 0.05) rods.push([i, j]);
  const pts = hubs.map(h => ({ p: h.clone(), r: CAGE.hubRadius, mu: CAGE.muHub, kind: "hub" }));
  for (const [i, j] of rods) for (const t of [0.25, 0.5, 0.75]) pts.push({ p: hubs[i].clone().lerp(hubs[j], t), r: CAGE.rodRadius, mu: CAGE.muRod, kind: "rod" });
  return { pts, rods };
}

// ---------------------------------------------------------------- model
export class DroneModel {
  constructor() {
    this.root = new THREE.Group(); this.ready = false; this.props = []; this.hubs = null;
    this.quad = new THREE.Group(); this.cage = new THREE.Group(); this.bigRing = new THREE.Group(); this.smallRing = new THREE.Group();
    this.root.add(this.cage, this.bigRing, this.smallRing, this.quad);
    // Caddx Ant (1.8 mm lens, very wide) — repositioned onto the model's camera mount after loading
    this.fpv = new THREE.PerspectiveCamera(105, 16 / 9, 0.005, 150);
    this.fpv.position.set(0, 0.012, -0.03); this.fpv.rotation.x = THREE.MathUtils.degToRad(12);
    this.light = new THREE.SpotLight(0xf4f6ff, 0, 10, THREE.MathUtils.degToRad(38), 0.6, 1.8);   // switchable inspection LEDs
    this.light.position.set(0, 0.008, -0.035); this.light.target.position.set(0, 0.25, -2.5);
    this.quad.add(this.fpv, this.light, this.light.target);
  }

  async load(url) {
    const gltf = await new GLTFLoader().loadAsync(url);
    const byName = n => gltf.scene.getObjectByName(n);
    for (const [src, dst] of [["cage", this.cage], ["ring_big", this.bigRing], ["ring_small", this.smallRing], ["quad", this.quad]]) {
      const node = byName(src); if (node) [...node.children].forEach(c => dst.add(c));
    }
    const cam = this.quad.getObjectByName("fpv_cam");
    if (cam) { this.fpv.position.copy(cam.position); this.fpv.quaternion.copy(cam.quaternion); }
    const led = this.quad.getObjectByName("inspection_light");
    if (led) { this.light.position.copy(led.position); const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(led.quaternion); this.light.target.position.copy(led.position).addScaledVector(dir, 2.5); }
    for (let k = 0; k < 4; k++) {
      const p = this.quad.getObjectByName("prop_" + k); if (!p) continue;
      const disc = new THREE.Mesh(new THREE.CircleGeometry(0.0254, 40), new THREE.MeshBasicMaterial({ color: k < 2 ? 0x2a6cc8 : 0x6a7078, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
      disc.rotation.x = -Math.PI / 2; p.add(disc);
      p.userData = { dir: k % 2 ? -1 : 1, disc, blades: p.children.filter(c => c !== disc) };
      this.props.push(p);
    }
    this.root.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = false; o.layers.set(1); } });
    this.cage.traverse(o => { if (o.isMesh) o.layers.enable(2); });      // cage bars are visible in the FPV video
    this.fpv.layers.enable(2);
    this.hubs = extractHubs(this.cage);
    this.ready = true;
  }

  pose(pos, qd, qc, thrustFrac, dt) {
    this.root.position.copy(pos);
    this.quad.quaternion.copy(qd); this.cage.quaternion.copy(qc);
    const e = new THREE.Euler().setFromQuaternion(qd.clone().invert().multiply(qc), "XZY");
    const qa = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), e.x);
    const qb = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), e.z);
    this.smallRing.quaternion.copy(qd).multiply(qa);
    this.bigRing.quaternion.copy(qd).multiply(qa).multiply(qb);
    const spin = thrustFrac > 0.01 ? 40 + 30 * thrustFrac : 0;
    for (const p of this.props) {
      p.rotation.y += p.userData.dir * spin * dt;
      p.userData.disc.material.opacity = Math.min(0.3, thrustFrac * 0.55);
      for (const b of p.userData.blades) b.visible = thrustFrac < 0.12 || Math.random() < 0.55;
    }
  }
}

// Hub centres from the cage mesh: cluster outer vertices by direction (12 clusters for an icosahedron).
function extractHubs(cage) {
  const dirs = [];
  cage.updateMatrixWorld(true);
  const inv = new THREE.Matrix4().copy(cage.matrixWorld).invert(), v = new THREE.Vector3();
  cage.traverse(o => {
    if (!o.isMesh) return;
    const pos = o.geometry.attributes.position, M = new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld);
    for (let i = 0; i < pos.count; i += 3) { v.fromBufferAttribute(pos, i).applyMatrix4(M); if (v.length() > CAGE.circumradius * 0.95) dirs.push(v.clone().normalize()); }
  });
  const clusters = [];
  for (const d of dirs) {
    const c = clusters.find(c => c.sum.clone().normalize().dot(d) > Math.cos(THREE.MathUtils.degToRad(12)));
    if (c) { c.sum.add(d); c.n++; } else clusters.push({ sum: d.clone(), n: 1 });
  }
  clusters.sort((a, b) => b.n - a.n);
  if (clusters.length < 12 || clusters.length > 14) return null;     // not an icosahedral cage → keep the analytic hubs
  return clusters.slice(0, 12).map(c => c.sum.normalize().multiplyScalar(CAGE.circumradius));
}

// ---------------------------------------------------------------- physics
const _cands = [], _hits = [];
function gauss() { return Math.sqrt(-2 * Math.log(Math.random() + 1e-12)) * Math.cos(2 * Math.PI * Math.random()); }

export class Drone {
  constructor() {
    this.model = new DroneModel();
    this.setBattery(550);
    this.setCageGeometry(icosahedronGeometry());
    this.reset(new THREE.Vector3(0, 1, 0), 0);
  }

  setBattery(capacityMah) { this.spec = buildSpec(capacityMah); this.mass = this.spec.mass; this.I = this.spec.I; }
  setCageGeometry(hubs) { this.hubs = hubs; this.cagePts = cageContactPoints(hubs).pts; }

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
    const tau = this.w.clone().sub(new THREE.Vector3(0, this.yawRate, 0)).multiplyScalar(-P.gimbalFric).addScaledVector(this.w, -P.cageAirDrag * this.w.length());
    this.w.addScaledVector(tau, dt / this.I);
    this.pos.addScaledVector(this.vel, dt);

    // ---- contacts at the real hubs and rods ----
    const T = this.t, velBefore = this.vel.clone();
    let impact = 0, impactPt = null, impactN = null, impactMat = null, Nsum = 0, slip = 0, touching = 0, touchMat = null, touchPt = null, touchN = null, floor = false;
    world.near(this.pos, P.R + 0.01, _cands);
    if (_cands.length) {
      const R = new THREE.Matrix3().setFromMatrix4(new THREE.Matrix4().makeRotationFromQuaternion(this.qc));
      const contacts = [];
      for (const cp of this.cagePts) {
        const off = cp.p.clone().applyMatrix3(R), wp = off.clone().add(this.pos);
        for (const h of world.contactsIn(_cands, wp, cp.r, _hits)) contacts.push({ n: h.n, depth: h.depth, r: off.clone().addScaledVector(h.n, -cp.r), mu: cp.mu * (h.mat === "metal" ? 0.8 : 1), mat: h.mat, point: h.point, hub: cp.kind === "hub" });
      }
      if (contacts.length) {
        // position: resolve the deepest penetration along each distinct normal
        const push = new THREE.Vector3();
        for (const c of contacts) { const need = c.depth - push.dot(c.n); if (need > 0) push.addScaledVector(c.n, need); }
        this.pos.add(push);
        for (const c of contacts) { touching++; if (c.n.y > 0.7) floor = true; if (!touchMat || c.hub) { touchMat = c.mat; touchPt = c.point; touchN = c.n; } }
        for (let iter = 0; iter < 3; iter++) {
          for (const c of contacts) {
            const vc = this.vel.clone().add(new THREE.Vector3().crossVectors(this.w, c.r));
            const vn = vc.dot(c.n);
            if (vn >= 0) continue;
            const e = iter > 0 ? 0 : (-vn > 0.6 ? CAGE.eHub : -vn > 0.15 ? CAGE.eHub * (-vn - 0.15) / 0.45 : 0);
            const rn = new THREE.Vector3().crossVectors(c.r, c.n);
            const jn = -(1 + e) * vn / (1 / m + rn.lengthSq() / this.I);
            this.vel.addScaledVector(c.n, jn / m); this.w.addScaledVector(rn, jn / this.I);
            if (iter === 0 && -vn > impact) { impact = -vn; impactPt = c.point.clone(); impactN = c.n.clone(); impactMat = c.mat; }
            Nsum += jn / dt;
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
