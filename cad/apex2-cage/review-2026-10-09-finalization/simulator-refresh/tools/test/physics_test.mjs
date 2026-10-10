// Headless checks of the P1B demo physics (CAD model static/assets/p1b.json):
//   node tools/test/physics_test.mjs
import { readFileSync } from "node:fs";
import path from "node:path";
import { World } from "../../static/js/physics.js";
import { Drone, DEMO } from "../../static/js/drone.js";

const model = JSON.parse(readFileSync(path.resolve(import.meta.dirname, "../../static/assets/p1b.json"), "utf8"));
const W = new World();
const dt = 1 / 240, failures = [], R = model.params_mm.cage_outer_dia / 2000;
const deg = r => r * 180 / Math.PI;
function check(name, ok, detail = "") { if (!ok) failures.push(name); console.log(`  ${ok ? "PASS" : "FAIL"} ${name} ${detail}`); }
function run(d, secs, input, each) { for (let i = 0; i < secs / dt; i++) { d.step(dt, input, W); each?.(d); } }
const go = (o = {}) => ({ fwd: 0, strafe: 0, turn: 0, lift: 0, ...o });
const tilt = d => Math.max(Math.abs(deg(d.roll)), Math.abs(deg(d.pitch)));

const d = new Drone(model);
for (const pack of ["450", "1100"]) {
  d.configure(pack);
  console.log(`P1B + ${pack} mAh: ${(d.mass * 1000).toFixed(2)} g, T:W ${(d.thrustMaxN / (d.mass * 9.81)).toFixed(2)}, hover ~${d.hoverMinutes().toFixed(1)} min`);
}
d.configure("450");

console.log("1. motors off: drops and settles on the cage");
d.reset(0, 1, 0, 0); d.armed = false;
let lowest = 9; run(d, 5, go(), x => { lowest = Math.min(lowest, x.p[1]); });
check("rests on the hubs", d.p[1] > 0.105 && d.p[1] < R + 0.002, `centre ${(d.p[1] * 1000).toFixed(1)} mm`);
check("never sinks into the floor", lowest > 0.1, `lowest ${(lowest * 1000).toFixed(1)} mm`);
check("comes to rest", Math.hypot(...d.v) < 0.02 && d.t.spin < 0.2, `${d.t.state}`);

console.log("2. take off, then let go: holds height");
d.armed = true; run(d, 1.5, go({ lift: 1 }));
const y0 = d.p[1]; run(d, 2, go());
check("climbs", y0 > 1, `height ${y0.toFixed(2)} m`);
check("brakes and hovers after letting go", Math.abs(d.p[1] - y0) < 0.5 && Math.hypot(...d.v) < 0.05, `drift ${(d.p[1] - y0).toFixed(2)} m, v ${Math.hypot(...d.v).toFixed(3)} m/s`);

console.log("3. forward: smooth, limited speed and tilt");
let maxTilt = 0, maxStep = 0, prev = d.pitch;
run(d, 3, go({ fwd: 1 }), x => { maxTilt = Math.max(maxTilt, tilt(x)); maxStep = Math.max(maxStep, Math.abs(x.pitch - prev)); prev = x.pitch; });
check("reaches top speed toward -Z", d.v[2] < -0.9 * DEMO.speed && Math.hypot(d.v[0], d.v[2]) < DEMO.speed * 1.05, `v ${d.v.map(x => x.toFixed(2)).join(", ")}`);
check("tilt within the limit, changes smoothly", maxTilt <= deg(DEMO.maxTilt) + 0.1 && deg(maxStep) < 1, `max ${maxTilt.toFixed(1)} deg, max ${deg(maxStep).toFixed(2)} deg per step`);
run(d, 3, go());
check("stops when released", Math.hypot(d.v[0], d.v[2]) < 0.05, `${Math.hypot(d.v[0], d.v[2]).toFixed(3)} m/s`);

console.log("4. turn");
const h0 = d.heading; run(d, 1, go({ turn: 1 }));
check("turns left at about the set rate", Math.abs(deg(d.heading - h0) - deg(DEMO.yawRate) * 0.85) < 15, `${deg(d.heading - h0).toFixed(0)} deg in 1 s`);

console.log("5. into the wall at full speed");
W.box(0, 1.5, -5.1, 10, 1.5, 0.1, 0, 0.3);                  // wall only for the collision case; free-speed test above needs open space
d.reset(0, 1.2, -3, 0);
let closest = 9, airTilt = 0;
run(d, 3, go({ fwd: 1 }), x => { closest = Math.min(closest, x.p[2] + 5); airTilt = Math.max(airTilt, tilt(x)); });
check("cage stops at the wall", closest > 0.11, `closest centre ${(closest * 1000).toFixed(0)} mm (hexagon face 113.6 mm)`);
check("impact recorded, cage spun, aircraft unaffected", d.t.impacts >= 1 && airTilt <= deg(DEMO.maxTilt) + 0.1, `${d.t.impacts} impact(s), ${(d.t.impactJ * 1000).toFixed(0)} mJ, cage ${d.t.spin.toFixed(1)} rad/s`);

console.log("6. rolls along the floor");
d.reset(0, R, 2, 0); d.armed = false; run(d, 1, go()); d.armed = true;
const z0 = d.p[2]; let maxY = 0; run(d, 2, go({ fwd: 1, lift: -1 }), x => { maxY = Math.max(maxY, x.p[1]); });
check("moves forward, cage rolls, stays down", z0 - d.p[2] > 0.5 && maxY < 0.2, `moved ${(z0 - d.p[2]).toFixed(2)} m, cage ${d.t.spin.toFixed(1)} rad/s, ${d.t.state}`);

console.log("7. battery");
d.reset(0, 2, 0, 0); run(d, 0.5, go());
const a0 = d.current, v0 = d.voltage; d.mAh = 0.97 * d.capacityAh * 1000; d.soc = 0.03; run(d, 1, go());
check("hover draw and sag", a0 > 2 && a0 < 10 && d.voltage < v0, `${a0.toFixed(1)} A at ${v0.toFixed(2)} V fresh, ${d.voltage.toFixed(2)} V nearly flat`);
for (const pack of ["450", "1100"]) {                        // demo battery: both packs keep flying when flat
  d.configure(pack); d.reset(0, 2, 0, 0); run(d, 0.5, go()); d.mAh = d.capacityAh * 1000; d.soc = 0; const y = d.p[1];
  run(d, 3, go({ fwd: 1 }));
  check(`${pack} mAh flat pack still holds height`, Math.abs(d.p[1] - y) < 0.1, `dy ${(d.p[1] - y).toFixed(2)} m at ${(d.voltage / 2).toFixed(2)} V/cell`);
}
d.configure("450");

console.log("8. cost per physics step");
d.reset(0, 0.2, 0, 0);
const t0 = performance.now(); run(d, 20, go({ fwd: 0.5 })); const us = (performance.now() - t0) / (20 / dt) * 1000;
check("under 20 us per step (240 Hz)", us < 20, `${us.toFixed(1)} us`);

console.log(failures.length ? `\n${failures.length} FAILED: ${failures.join(", ")}` : "\nALL PASSED");
process.exit(failures.length ? 1 : 0);
