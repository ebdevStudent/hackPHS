// Ball Drone flight simulator — renderer, post-processing, cameras, input, loop. Free flight, no objectives.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { SMAAPass } from "three/addons/postprocessing/SMAAPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { Colliders } from "./physics.js";
import { Drone, P } from "./drone.js";
import { Particles } from "./fx.js";
import { Hud } from "./hud.js";
import { Sfx } from "./audio.js";
import { api } from "./api.js";
import { environment, setAnisotropy } from "./assets.js";

export const BUILD = "realism-v2";
const $ = id => document.getElementById(id);
// levels load lazily, so one broken/unfinished level never takes the whole simulator down
const LEVELS = {
  industrial: a => import("./levels/industrial.js").then(m => m.buildIndustrial(a)),
  rescue: a => import("./levels/rescue.js").then(m => m.buildRescue(a)),
  lab: a => import("./levels/lab.js").then(m => m.buildLab(a)),
};
const PHYS_DT = 1 / 240;
const params = new URLSearchParams(location.search);

// ---------------- graphics quality ----------------
// Low (default) runs on integrated laptop graphics: no post-processing, pixel ratio 1, one 1024² shadow map (the sun or
// moon), hard-edged PCF shadows, fewer particles. High restores the original look: GTAO + bloom + SMAA, pixel
// ratio up to 1.5, soft shadows at full size from every shadow-casting light, full particle rates. G cycles them.
const QUALITY = {
  low: { label: "Low", pixelRatio: 1, post: false, softShadows: false, shadowMap: 1024, extraShadows: false, particles: 0.6 },
  high: { label: "High", pixelRatio: 1.5, post: true, softShadows: true, shadowMap: Infinity, extraShadows: true, particles: 1 },
};
function loadQuality() {
  const q = params.get("quality"); if (QUALITY[q]) return q;
  try { const s = localStorage.getItem("bdQuality"); if (QUALITY[s]) return s; } catch { /* storage blocked */ }
  return "low";
}

// ---------------- renderer ----------------
const renderer = new THREE.WebGLRenderer({ canvas: $("view"), antialias: true, powerPreference: "high-performance" });
renderer.shadowMap.enabled = true;
renderer.shadowMap.autoUpdate = false;           // shadow maps are drawn once per frame, not again for the FPV inset
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.outputColorSpace = THREE.SRGBColorSpace;
setAnisotropy(Math.min(4, renderer.capabilities.getMaxAnisotropy()));
const scene = new THREE.Scene();
const colliders = new Colliders();
const fx = new Particles(scene, 3000);
const drone = new Drone(); scene.add(drone.model.root);
const hud = new Hud();
const sfx = new Sfx();

const chaseCam = new THREE.PerspectiveCamera(70, 1, 0.03, 300); chaseCam.layers.enable(1);
const orbitCam = new THREE.PerspectiveCamera(50, 1, 0.03, 300); orbitCam.layers.enable(1);
const fpvCam = drone.model.fpv;

// post-processing (High only, built on first use): render → GTAO (ambient occlusion) → bloom → SMAA → output
let composer = null, renderPass = null, gtao = null;
function ensureComposer() {
  if (composer) return;
  composer = new EffectComposer(renderer);
  renderPass = new RenderPass(scene, chaseCam);
  gtao = new GTAOPass(scene, chaseCam, innerWidth, innerHeight);
  gtao.updateGtaoMaterial({ radius: 0.45, distanceExponent: 1.5, thickness: 1.2, scale: 1.0, samples: 12 });
  gtao.blendIntensity = 0.85;
  const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.18, 0.4, 1.05);   // only real light sources bloom
  const smaa = new SMAAPass(innerWidth * renderer.getPixelRatio(), innerHeight * renderer.getPixelRatio());
  composer.addPass(renderPass); composer.addPass(gtao); composer.addPass(bloom); composer.addPass(smaa); composer.addPass(new OutputPass());
  composer.setSize(innerWidth, innerHeight);
}

const G = {
  state: "menu", level: null, id: null, cam: "chase", quality: loadQuality(), post: false, debug: false,
  acc: 0, time: 0, shake: 0, chaseDist: 0.8, battery: loadPref("bdBattery", 550), orbitA: 0, envCache: new Map(), loading: false, impacts: 0,
};

// ---------------- input ----------------
const keys = new Set();
addEventListener("keydown", e => {
  keys.add(e.code);
  if (["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Tab"].includes(e.code)) e.preventDefault();
  if (e.repeat) return;
  switch (e.code) {
    case "Digit1": case "Numpad1": start("industrial"); break;
    case "Digit2": case "Numpad2": start("rescue"); break;
    case "Digit3": case "Numpad3": start("lab"); break;
    case "KeyR": if (G.level) resetDrone(); break;
    case "KeyC": if (G.state === "play") G.cam = { chase: "fpv", fpv: "orbit", orbit: "chase" }[G.cam]; break;
    case "KeyV": if (G.state === "play") swapView(); break;
    case "KeyP": if (G.state === "play") togglePower(); break;
    case "KeyL": if (G.state === "play") { drone.leds = !drone.leds; hud.toast(drone.leds ? "Inspection LEDs on (+0.6 W)" : "Inspection LEDs off", 1.0); } break;
    case "KeyB": if (G.state === "play") { const caps = [450, 550, 650, 850]; setBattery(caps[(caps.indexOf(G.battery) + 1) % caps.length], true); } break;
    case "F11": e.preventDefault(); toggleFullscreen(); break;
    case "KeyT": G.debug = !G.debug; break;
    case "KeyG": setQuality(G.quality === "low" ? "high" : "low", true); break;
    case "KeyN": hud.toggleMap(); break;
    case "KeyH": hud.toggleHelp(); break;
    case "KeyI": hud.toggleTelemetry(); break;
    case "KeyM": sfx.setMute(!sfx.muted); break;
    case "Escape": if (G.state === "play") pause(true); else if (G.state === "paused") pause(false); break;
    case "Enter": if (G.state === "menu") start("industrial"); break;
  }
});
addEventListener("keyup", e => keys.delete(e.code));

// FPV video ⇄ normal (chase) view: V, or click the small inset
function swapView() { G.cam = G.cam === "fpv" ? "chase" : "fpv"; hud.toast(G.cam === "fpv" ? "Onboard FPV camera" : "Chase view", 1.0); }
$("pip-frame").addEventListener("click", () => { if (G.state === "play") swapView(); });

// motor power: P or the PWR button on the HUD
function togglePower() {
  drone.setArmed(!drone.armed);
  hud.toast(drone.armed ? "Motors armed — props spooling up" : "Motors off — the drone is now a passive ball", 1.6);
}
$("s-pwr").addEventListener("click", e => { e.currentTarget.blur(); if (G.state === "play") togglePower(); });
function toggleFullscreen() {
  if (window.pywebview?.api?.toggle_fullscreen) window.pywebview.api.toggle_fullscreen();       // desktop app window
  else if (!document.fullscreenElement) document.documentElement.requestFullscreen?.(); else document.exitFullscreen?.();
}
addEventListener("blur", () => keys.clear());
addEventListener("wheel", e => { G.chaseDist = THREE.MathUtils.clamp(G.chaseDist * (e.deltaY > 0 ? 1.1 : 0.9), 0.35, 3); }, { passive: true });

// ---------------- graphics quality switch ----------------
function setQuality(q, announce = false) {
  const Q = QUALITY[q] || QUALITY.low;
  G.quality = QUALITY[q] ? q : "low"; try { localStorage.setItem("bdQuality", G.quality); } catch { /* storage blocked */ }
  G.post = Q.post && !params.get("nopost");
  if (G.post) ensureComposer();
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, Q.pixelRatio));
  const type = Q.softShadows ? THREE.PCFSoftShadowMap : THREE.PCFShadowMap;
  if (renderer.shadowMap.type !== type) { renderer.shadowMap.type = type; scene.traverse(o => { if (o.material) [].concat(o.material).forEach(m => { m.needsUpdate = true; }); }); }
  applyLightQuality();
  fx.density = Q.particles;
  resize();
  if (announce) hud.toast(G.quality === "high" ? "Graphics: High (GTAO · bloom · SMAA, soft shadows)" : "Graphics: Low (fast: no post-processing, one shadow)", 1.6);
}
// Shadow casters per quality. The level's own settings are remembered so High can restore them.
function applyLightQuality() {
  const Q = QUALITY[G.quality];
  scene.traverse(o => {
    if (!o.isLight || !o.shadow) return;
    if (!o.userData.shadowOrig) o.userData.shadowOrig = { cast: o.castShadow, size: o.shadow.mapSize.x };
    const orig = o.userData.shadowOrig;
    o.castShadow = orig.cast && (Q.extraShadows || o.isDirectionalLight);
    const size = Math.min(orig.size, Q.shadowMap);
    if (o.shadow.mapSize.x !== size) { o.shadow.mapSize.set(size, size); if (o.shadow.map) { o.shadow.map.dispose(); o.shadow.map = null; } }
  });
}

// ---------------- battery test set (450 / 550 / 650 / 850 mAh 2S LiHV, per the project document) ----------------
function loadPref(k, d) { try { return +(localStorage.getItem(k) || d); } catch { return d; } }
function setBattery(mah, swap = false) {
  G.battery = mah; try { localStorage.setItem("bdBattery", mah); } catch { /* storage blocked */ }
  drone.setBattery(mah);
  document.querySelectorAll(".battery-pick button").forEach(b => b.classList.toggle("on", +b.dataset.mah === mah));
  const s = drone.spec;
  $("bat-spec").textContent = `AUW ${s.auw_g.toFixed(0)} g · T/W ${s.tw.toFixed(2)} · ~${s.hoverMin.toFixed(1)} min hover`;
  if (swap && G.level) { resetDrone(); hud.toast(`Pack swapped: ${s.battery.name} — AUW ${s.auw_g.toFixed(1)} g, T/W ${s.tw.toFixed(2)}`, 2.2); }
}
document.querySelectorAll(".battery-pick button").forEach(b => b.addEventListener("click", () => setBattery(+b.dataset.mah)));
setBattery(G.battery);

function readInput() {
  const k = c => keys.has(c) ? 1 : 0;
  return {
    fwd: k("KeyW") + k("ArrowUp") - k("KeyS") - k("ArrowDown"),
    turn: k("KeyA") + k("ArrowLeft") - k("KeyD") - k("ArrowRight"),
    strafe: k("KeyE") - k("KeyQ"),
    lift: k("Space") - k("ShiftLeft") - k("ShiftRight"),
  };
}

document.querySelectorAll(".card").forEach(c => c.addEventListener("click", () => start(c.dataset.level)));
$("b-resume").onclick = () => pause(false);
$("b-menu").onclick = () => toMenu();
api.health().then(r => { $("backend-state").textContent = r ? "Backend connected · live telemetry link available" : "Backend offline — running standalone"; });

function toMenu() { G.state = "menu"; hud.show(false); $("menu").classList.remove("hidden"); $("pause").classList.add("hidden"); sfx.engine?.(0, false); }
function pause(on) { if (on && G.state !== "play") return; G.state = on ? "paused" : "play"; $("pause").classList.toggle("hidden", !on); }

// ---------------- levels ----------------
async function loadEnv(name) {
  if (!G.envCache.has(name)) G.envCache.set(name, environment(renderer, name));
  return G.envCache.get(name);
}

async function start(id) {
  if (G.loading || !LEVELS[id]) return;
  G.loading = true; sfx.init();
  const previous = G.id, before = new Set(scene.children);
  $("menu").classList.add("hidden"); $("pause").classList.add("hidden");
  hud.loading(true, "Loading " + ({ rescue: "collapsed building", industrial: "industrial plant", lab: "physics test bay" }[id] || id) + "…");
  try {
    if (G.level) G.level.level.dispose();
    G.level = null; G.id = null;
    colliders.clear(); fx.clear();
    const [lv] = await Promise.all([LEVELS[id]({ scene, colliders, fx, renderer }), droneReady]);
    const env = lv.env;
    const { env: envMap, background } = await loadEnv(env.hdri);
    scene.environment = envMap; scene.environmentIntensity = env.envIntensity ?? 1;
    if (env.background === "hdri") { scene.background = background; scene.backgroundIntensity = env.backgroundIntensity ?? 1; }
    else scene.background = new THREE.Color(env.background ?? 0x000000);
    scene.fog = env.fog ? new THREE.Fog(env.fog.color, env.fog.near, env.fog.far) : null;
    renderer.toneMappingExposure = env.exposure ?? 1;
    G.ledIntensity = env.droneLight ?? 20;
    scene.traverse(o => { if (o.isLight && o.shadow) o.shadow.camera.layers.enable(1); });   // the drone casts shadows too
    applyLightQuality();
    G.level = lv; G.id = id;
    resetDrone();
    hud.setLevel(lv); hud.show(true);
    sfx.ambience?.(id);
    G.state = "play";
    renderer.compile(scene, chaseCam);
  } catch (err) {
    console.error(err); hud.toast("Failed to load level: " + err.message, 5);
    // Remove whatever the failed level added, then return to the level that was working.
    for (const child of [...scene.children]) if (!before.has(child)) scene.remove(child);
    colliders.clear(); fx.clear();
    G.loading = false; hud.loading(false);
    if (previous && previous !== id) { setTimeout(() => start(previous), 0); return; }   // after finally clears the flag
    G.state = "menu"; $("menu").classList.remove("hidden");
    return;
  } finally { G.loading = false; hud.loading(false); }
}

function resetDrone() {
  drone.reset(G.level.spawn.pos, G.level.spawn.yaw);
  drone.leds = (G.level.env.droneLight ?? 0) >= 10;              // dark environments start with the inspection LEDs on
  hud.flightTime = 0;
  G.acc = 0; G.impacts = 0;
  snapChase();
}

// ---------------- simulation ----------------
let scrapeT = 0;
function simulate(dt) {
  G.time += dt;
  if (drone.armed) hud.flightTime = (hud.flightTime || 0) + dt;
  const input = readInput();
  G.acc += dt;
  let hit = null;
  while (G.acc >= PHYS_DT) {
    G.acc -= PHYS_DT;
    const h = drone.step(PHYS_DT, input, colliders, G.time);
    if (h && (!hit || h.speed > hit.speed)) hit = h;
  }
  if (hit) {
    G.impacts++;
    const fxSpeed = hit.speed * (drone.mass / 0.6);                 // effects scale with impact energy: a ~100 g drone barely disturbs dust
    if (fx.impact) fx.impact(hit.point, hit.normal, fxSpeed, hit.mat);
    else if (hit.mat === "metal") fx.sparks(hit.point, hit.normal, hit.speed * 0.5); else fx.dust(hit.point, hit.normal, hit.speed);
    if (sfx.impact) sfx.impact(hit.speed, hit.mat); else sfx.hit(hit.speed);
    G.shake = Math.min(1, G.shake + hit.speed * 0.25);
  }
  const T = drone.t;
  if (T.contact === "SLIDING" && T.slip > 0.15 && T.touchPoint && (scrapeT -= dt) <= 0) { fx.scrape?.(T.touchPoint, T.touchNormal, T.slip * 0.4, T.mat); scrapeT = 0.15; }
  sfx.scrape?.(T.contact === "SLIDING" ? T.slip : 0, T.mat || "concrete", T.contact === "ROLLING" || T.contact === "SLIDING" ? drone.vel.length() : 0);
  if (sfx.motors) sfx.motors(drone.thrustFrac(), drone.vel.length()); else sfx.engine?.(drone.thrustFrac(), true);
  G.shake = Math.max(0, G.shake - dt * 3);
  for (const u of G.level.level.updaters) u(dt);
  G.level.ambient?.(dt, drone.pos);
  fx.update(dt);
}

// ---------------- cameras ----------------
const _d = new THREE.Vector3(), _t = new THREE.Vector3();
function chaseTarget(out) {
  out.copy(drone.pos).addScaledVector(drone.forward, -G.chaseDist).add(_t.set(0, 0.32 * G.chaseDist + 0.05, 0));
  return clampToDrone(out);
}
function clampToDrone(out) {          // keep the camera on the drone's side of any wall (analytic raycast on colliders)
  _d.copy(out).sub(drone.pos); const len = _d.length(); if (len < 1e-4) return out;
  _d.divideScalar(len);
  const hit = colliders.raycast(drone.pos, _d, len + 0.12);
  if (hit < len + 0.12) out.copy(drone.pos).addScaledVector(_d, Math.max(0.24, hit - 0.12));
  return out;
}
function snapChase() { chaseCam.position.copy(chaseTarget(new THREE.Vector3())); chaseCam.lookAt(drone.pos); }
function updateCams(dt) {
  const want = chaseTarget(new THREE.Vector3());
  chaseCam.position.lerp(want, 1 - Math.exp(-7 * dt));
  clampToDrone(chaseCam.position);
  if (G.shake > 0) chaseCam.position.add(new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(G.shake * 0.04));
  chaseCam.lookAt(_t.copy(drone.pos).addScaledVector(drone.forward, 0.8).add(new THREE.Vector3(0, 0.05, 0)));
  G.orbitA += dt * 0.25;
  const o = new THREE.Vector3(Math.cos(G.orbitA) * 1.6, 0.55 + 0.25 * Math.sin(G.orbitA * 0.7), Math.sin(G.orbitA) * 1.6).add(drone.pos);
  orbitCam.position.copy(clampToDrone(o)); orbitCam.lookAt(drone.pos);
}

function pipRect() {
  const w = Math.round(Math.min(340, Math.max(220, innerWidth * 0.2))), h = Math.round(w * 9 / 16);
  return { x: innerWidth - w - 18, y: 18, w, h };
}

const debugGroup = new THREE.Group(); scene.add(debugGroup);
const spinArrow = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(), 0.4, 0xff3b30, 0.08, 0.05);
const velArrow = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(), 0.4, 0x30d158, 0.08, 0.05);
const nArrow = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(), 0.3, 0xffd60a, 0.06, 0.04);
debugGroup.add(spinArrow, velArrow, nArrow);
debugGroup.traverse(o => o.layers.set(1));

function render(dt) {
  const W = innerWidth, H = innerHeight;
  drone.render(dt);
  drone.model.light.intensity = drone.leds ? (G.ledIntensity ?? 20) : 0;
  if (G.level) updateCams(dt);
  // physics debug vectors: gimbal spin axis (red, length ∝ rpm), velocity (green), contact normal (yellow)
  debugGroup.visible = G.debug && !!G.level;
  if (debugGroup.visible) {
    const w = drone.w.length(), v = drone.vel.length();
    spinArrow.position.copy(drone.pos); spinArrow.visible = w > 0.2; if (w > 0.2) { spinArrow.setDirection(drone.w.clone().normalize()); spinArrow.setLength(0.25 + w * 0.03, 0.06, 0.04); }
    velArrow.position.copy(drone.pos); velArrow.visible = v > 0.05; if (v > 0.05) { velArrow.setDirection(drone.vel.clone().normalize()); velArrow.setLength(0.25 + v * 0.15, 0.06, 0.04); }
    nArrow.visible = !!drone.t.touchPoint; if (drone.t.touchPoint) { nArrow.position.copy(drone.t.touchPoint); nArrow.setDirection(drone.t.touchNormal); }
  }
  const main = G.cam === "fpv" ? fpvCam : G.cam === "orbit" ? orbitCam : chaseCam;
  main.aspect = W / H; main.updateProjectionMatrix();
  renderer.setScissorTest(false); renderer.setViewport(0, 0, W, H);
  const pr = renderer.getPixelRatio();
  fx.setViewport(W * pr, H * pr, main);
  renderer.shadowMap.needsUpdate = true;          // once per frame; the inset below reuses the same shadow maps
  if (G.post) { renderPass.camera = main; gtao.camera = main; composer.render(dt); }
  else renderer.render(scene, main);
  if (G.level && (G.state === "play" || G.state === "paused")) {
    const r = pipRect(), pip = G.cam === "fpv" ? chaseCam : fpvCam;
    pip.aspect = 16 / 9; pip.updateProjectionMatrix();
    fx.setViewport(r.w * pr, r.h * pr, pip);
    renderer.setScissorTest(true); renderer.setScissor(r.x, r.y, r.w, r.h); renderer.setViewport(r.x, r.y, r.w, r.h);
    renderer.render(scene, pip);
    renderer.setScissorTest(false); renderer.setViewport(0, 0, W, H);
    if (G.cam === "fpv") { pip.aspect = W / H; }
    hud.pip(r, G.cam === "fpv" ? "CHASE" : "ONBOARD");
  } else hud.pip(null);
  hud.osd(G.cam === "fpv" && G.level ? drone : null, agl(), G.shake);
}

function agl() { return Math.max(0, colliders.raycast(drone.pos, new THREE.Vector3(0, -1, 0), 50) - P.R); }

// ---------------- telemetry link (physical drone) ----------------
setInterval(async () => {
  if (G.state !== "play") return;
  const t = await api.telemetry();
  hud.link(t && t.age != null && t.age < 3 ? t : null);
}, 1000);

// ---------------- loop ----------------
function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  if (composer) { composer.setPixelRatio(renderer.getPixelRatio()); composer.setSize(innerWidth, innerHeight); }
  hud.resize();
}
addEventListener("resize", resize); setQuality(G.quality);

let last = performance.now(), hudT = 0, fps = 60;
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now; fps = fps * 0.95 + (1 / Math.max(dt, 1e-3)) * 0.05;
  if (G.state === "play" && G.level) simulate(dt);
  else if (G.level && G.state === "menu") { for (const u of G.level.level.updaters) u(dt); fx.update(dt); G.orbitA += dt * 0.1; }
  render(dt);
  if (G.level && G.state !== "menu" && (hudT -= dt) <= 0) {
    hudT = 0.1;
    hud.telemetry(drone, { agl: agl(), cam: G.cam, post: G.post, quality: QUALITY[G.quality].label, fps, impacts: G.impacts, debug: G.debug, time: G.time });
    hud.minimap(G.level, drone);
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// the HackPHS V1 aircraft from the project CAD (85 mm whoop); the two-ring gimbal is built procedurally, no cage
const droneReady = drone.model.load("assets/drone/ball_drone85.glb")
  .catch(() => drone.model.load("assets/drone/ball_drone.glb"));
if (params.get("level") && LEVELS[params.get("level")]) start(params.get("level"));

// ---------------- debug / test API ----------------
function fly(codes, seconds, fps = 60) {
  codes.forEach(c => keys.add(c));
  for (let i = 0; i < seconds * fps; i++) { simulate(1 / fps); updateCams(1 / fps); }
  codes.forEach(c => keys.delete(c));
  render(1 / fps);
  return { pos: drone.pos.toArray().map(v => +v.toFixed(2)), vel: +drone.vel.length().toFixed(2), contact: drone.t.contact, spinRpm: +(drone.t.spinRpm || 0).toFixed(0) };
}
function teleport(x, y, z, yaw = drone.yaw) { drone.reset(new THREE.Vector3(x, y, z), yaw); snapChase(); for (let i = 0; i < 10; i++) updateCams(1 / 60); render(1 / 60); }
function setCam(c) { G.cam = c; render(1 / 60); }
window.__game = { G, drone, scene, renderer, colliders, start, fly, teleport, setCam, render, setQuality, P };
