// Headless checks of the HackPHS ball-drone physics (85 mm whoop in a 225 mm icosahedral cage):
//   node --import ./register.mjs physics_test.mjs
import * as THREE from "three";
import { Colliders } from "../../static/js/physics.js";
import { Drone, P } from "../../static/js/drone.js";

const W = new Colliders();
W.box(new THREE.Vector3(0, -0.5, 0), new THREE.Vector3(50, 0.5, 50), null, "concrete");          // floor, top at y = 0
W.box(new THREE.Vector3(0, 5, -10.25), new THREE.Vector3(50, 5, 0.25), null, "concrete");        // wall, face at z = -10
const dt = 1 / 240, none = { fwd: 0, strafe: 0, turn: 0, lift: 0 };
let t = 0;
const failures = [];
function check(name, ok, detail = "") { if (!ok) failures.push(`${name} ${detail}`); console.log(`  ${ok ? "PASS" : "FAIL"} ${name} ${detail}`); }
function run(d, secs, input = none, every = 0, tag = "") {
  const rows = [];
  for (let i = 0; i < secs / dt; i++) {
    const hit = d.step(dt, input, W, t); t += dt;
    if (hit && tag) rows.push(`  impact ${hit.speed.toFixed(2)} m/s (${hit.mat}), peak ${d.t.peakG.toFixed(0)} g`);
    if (every && i % Math.round(every / dt) === 0) rows.push(`  t=${(i * dt).toFixed(2)} y=${d.pos.y.toFixed(3)} v=${d.vel.length().toFixed(2)} cage ω=${d.w.length().toFixed(1)} rad/s ${d.t.contact} pts=${d.t.points} T=${d.thrust.toFixed(2)} N`);
  }
  if (rows.length) console.log(rows.slice(0, 12).join("\n"));
}
const d = new Drone();
for (const cap of [450, 550, 650, 850]) {
  d.setBattery(cap); const s = d.spec;
  console.log(`spec ${cap} mAh: AUW ${s.auw_g.toFixed(1)} g, max thrust ${(s.thrustMax_N / 9.81 * 1000).toFixed(0)} g, T/W ${s.tw.toFixed(2)}, hover ${s.hoverW.toFixed(1)} W, ~${s.hoverMin.toFixed(1)} min`);
}
d.setBattery(550);

console.log("\n1. hover 3 s at 1 m");
d.reset(new THREE.Vector3(0, 1, 0), 0); run(d, 3);
console.log(`  y=${d.pos.y.toFixed(3)} thrust ${d.thrust.toFixed(3)} N (weight ${(d.mass * 9.81).toFixed(3)} N), pack ${d.voltage.toFixed(2)} V @ ${d.current.toFixed(2)} A, ${d.t.power.toFixed(1)} W`);
check("hover holds 1 m", Math.abs(d.pos.y - 1) < 0.05, `y=${d.pos.y.toFixed(3)}`);
check("hover thrust equals weight", Math.abs(d.thrust - d.mass * 9.81) < 0.02 * d.mass * 9.81);

console.log("2. full forward 3 s");
d.reset(new THREE.Vector3(0, 1, 0), 0); run(d, 3, { ...none, fwd: 1 }, 0.75);

console.log("3. into the wall at full speed");
d.reset(new THREE.Vector3(0, 1, -2), 0); run(d, 4, { ...none, fwd: 1 }, 0, "impact");
console.log(`  after: z=${d.pos.z.toFixed(3)} contact=${d.t.contact}, cage spin ${d.w.length().toFixed(1)} rad/s`);
check("cage stops at the wall", d.pos.z >= -10 + 0.0944 - 0.005, `z=${d.pos.z.toFixed(3)}`);
check("wall contact was counted", d.t.contacts >= 1);

console.log("4. land, then drive along the floor — the icosahedron should tip from face to face (bumpy, not smooth)");
d.reset(new THREE.Vector3(0, 0.6, 0), 0); run(d, 2, { ...none, lift: -1 });
run(d, 2.5, { ...none, lift: -1, fwd: 0.6 }, 0.25);

console.log("5. power OFF at 2 m, then ON");
d.reset(new THREE.Vector3(5, 2, 0), 0); run(d, 0.3); d.setArmed(false); run(d, 2.5, none, 0, "impact");
console.log(`  resting y=${d.pos.y.toFixed(4)} (expect a face or edge on the floor: inradius ${(0.7558 * 0.1183 + 0.005).toFixed(4)}–${(0.1125 + 0.005).toFixed(4)})`);
const restY = d.pos.y;
check("resting height is a face or edge on the floor", restY >= 0.7558 * 0.1183 + 0.005 - 0.002 && restY <= 0.1125 + 0.005 + 0.002, `y=${restY.toFixed(4)}`);
d.setArmed(true); run(d, 0.6); run(d, 1.5, { ...none, lift: 1 }); console.log(`  power on + 1.5 s climb: y=${d.pos.y.toFixed(2)} m`);
check("re-armed drone climbs", d.pos.y > 1.5, `y=${d.pos.y.toFixed(2)}`);

console.log("6. battery sag: full throttle climb at 100% vs 20% charge");
const sag = {};
for (const soc of [1, 0.2]) {
  d.reset(new THREE.Vector3(0, 1, 0), 0); d.soc = soc; d.mAh = (1 - soc) * d.spec.capacityMah; run(d, 0.6, { ...none, lift: 1 });
  sag[soc] = { v: d.voltage, thrust: d.thrustMax() };
  console.log(`  soc ${soc}: pack ${d.voltage.toFixed(2)} V under ${d.current.toFixed(1)} A, max thrust now ${(d.thrustMax() / 9.81 * 1000).toFixed(0)} g`);
}

check("a discharged pack sags and loses thrust", sag[0.2].v < sag[1].v && sag[0.2].thrust < sag[1].thrust);

console.log("7. endurance: hover until the low-voltage auto-land (550 mAh)");
d.reset(new THREE.Vector3(0, 1, 0), 0); let secs = 0;
while (!d.landing && secs < 900) { run(d, 1); secs++; }
console.log(`  auto-land after ${(secs / 60).toFixed(1)} min, ${d.mAh.toFixed(0)} mAh used, pack ${d.voltage.toFixed(2)} V`);
check("auto-land happens within a plausible hover time", d.landing && secs >= 120 && secs < 900, `${(secs / 60).toFixed(1)} min`);

if (failures.length) { console.error(`\nPHYSICS CHECKS FAILED (${failures.length}):\n  ` + failures.join("\n  ")); process.exit(1); }
console.log("\nPHYSICS CHECKS PASSED");
