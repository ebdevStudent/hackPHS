// Industrial bay — compact free-flight environment (no objectives).
// One 22 x 16 m steel-framed bay, 6.6 m eaves. Deliberately few features, all on a grid:
//   • one pallet-racking aisle (two runs, fully loaded, one empty bay to fly through)
//   • one roller conveyor across the floor (fly under it)
//   • two CNC machining centres
//   • one pipe run on the north wall with a steam leak
// Palette: grey concrete, light-grey cladding and steel, orange rack beams as the only accent, safety yellow where a
// real plant uses it. Units: metres, floor top y = 0. Spawn inside the roller door (south, +Z) facing north (-Z).
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { Level, pbr } from "./common.js";
import { uvBox, uvCylinder } from "../assets.js";

const HX = 11, HZ = 8, EAVE = 6.6, ROOF = 6.85;
const glbLoader = new GLTFLoader();
const glbCache = new Map();
function loadGLB(name) {
  if (!glbCache.has(name)) glbCache.set(name, glbLoader.loadAsync(`assets/blender/${name}.glb`).then(g => {
    g.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    g.scene.updateMatrixWorld(true);
    return g.scene;
  }));
  return glbCache.get(name);
}

export async function buildIndustrial({ scene, colliders, fx }) {
  const L = new Level(scene, colliders);
  L.bounds = { minX: -HX, maxX: HX, minZ: -HZ, maxZ: HZ };
  const C = colliders;
  const V = (x, y, z) => new THREE.Vector3(x, y, z);

  // ------------------------------------------------------------------ materials
  // painted sheet steel: neutral grey set derived from Poly Haven blue_metal_plate (assets/blender/painted_steel), tinted
  const tl = new THREE.TextureLoader(), pst = {};
  for (const [k, srgb] of [["diff", true], ["nor", false], ["arm", false]]) {
    const t = tl.load(`assets/blender/painted_steel/${k}.jpg`); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; pst[k] = t;
  }
  const painted = (tint, size = 2, { roughness = 1, metalness = 0.25 } = {}) => {
    const rep = t => { const c = t.clone(); c.repeat.set(1 / size, 1 / size); c.needsUpdate = true; return c; };
    return new THREE.MeshStandardMaterial({ color: tint, map: rep(pst.diff), normalMap: rep(pst.nor), roughnessMap: rep(pst.arm), aoMap: rep(pst.arm),
      roughness, metalness, normalScale: new THREE.Vector2(0.5, 0.5) });
  };
  // light painted profiled panels: corrugation from the Poly Haven normal map, flat factory-painted colour
  const corrNor = tl.load("assets/textures/corrugated_iron_02/nor.jpg"); corrNor.wrapS = corrNor.wrapT = THREE.RepeatWrapping; corrNor.anisotropy = 8;
  const panelMat = (color, size, rough = 0.55) => { const n = corrNor.clone(); n.repeat.set(1 / size, 1 / size); n.needsUpdate = true;
    return new THREE.MeshStandardMaterial({ color, normalMap: n, normalScale: new THREE.Vector2(0.9, 0.9), roughness: rough, metalness: 0.15 }); };
  const M = {
    floor: pbr("concrete_floor_worn_001", { size: 5.5, normalScale: 0.7 }),
    plinth: pbr("concrete_wall_008", { size: 3, tint: 0xc9c6bf }),
    clad: panelMat(0xd9dde0, 2.4),
    roof: panelMat(0xb9bec2, 2.4, 0.7),
    door: panelMat(0xc3c9ce, 1.2, 0.5),
    frame: painted(0xb8c0c8, 2.5),
    upright: painted(0x9aa3ab, 1.5),
    beam: painted(0xff6a1a, 1.5),
    enamel: painted(0xeef0ec, 2.5),
    dark: painted(0x55595f, 2.0),
    steel: new THREE.MeshStandardMaterial({ color: 0xb8bdc3, metalness: 1, roughness: 0.38 }),
    alu: new THREE.MeshStandardMaterial({ color: 0xd3d7db, metalness: 1, roughness: 0.42 }),
    bandGreen: new THREE.MeshStandardMaterial({ color: 0x2f8a4c, roughness: 0.55 }),
    bandBlue: new THREE.MeshStandardMaterial({ color: 0x2c6fb8, roughness: 0.55 }),
    bandRed: new THREE.MeshStandardMaterial({ color: 0xc0302a, roughness: 0.55 }),
    yellow: new THREE.MeshStandardMaterial({ color: 0xf0c419, roughness: 0.6 }),
    glass: new THREE.MeshStandardMaterial({ color: 0x0e171c, roughness: 0.04, metalness: 0.3, transparent: true, opacity: 0.62 }),
    screen: new THREE.MeshStandardMaterial({ color: 0x050a12, emissive: 0x3d8fff, emissiveIntensity: 0.9, roughness: 0.2 }),
    lampGlow: new THREE.MeshBasicMaterial({ color: 0xfff2d8 }),
    green: new THREE.MeshStandardMaterial({ color: 0x06280e, emissive: 0x22ff55, emissiveIntensity: 2.2 }),
    off: new THREE.MeshStandardMaterial({ color: 0x3a3a38, roughness: 0.3 }),
  };
  const hazard = hazardMaterial();

  // ------------------------------------------------------------------ batching (one mesh per material) + helpers
  const batches = new Map();
  const put = (mat, geo) => { (batches.get(mat) || batches.set(mat, []).get(mat)).push(geo.index ? geo.toNonIndexed() : geo); };
  const _M = new THREE.Matrix4(), _Q = new THREE.Quaternion(), _S = new THREE.Vector3(1, 1, 1);
  function sbox(mat, x, y, z, w, h, d, { rot = null, collide = true, map = true } = {}) {
    const g = uvBox(w, h, d);
    if (rot) { _Q.setFromEuler(new THREE.Euler(...rot)); g.applyMatrix4(_M.compose(V(0, 0, 0), _Q, _S)); }
    g.translate(x, y, z); put(mat, g);
    if (collide) C.box(V(x, y, z), V(w / 2, h / 2, d / 2), rot ? _Q.clone() : null, "metal");
    if (collide && map && y - h / 2 < 2.2 && h > 0.2) L.minimap.push({ x, z, w, d, rot: rot ? rot[1] : 0 });
  }
  function rbox(mat, x, y, z, w, h, d, r = 0.05, { collide = true } = {}) {
    const g = new RoundedBoxGeometry(w, h, d, 3, r);
    const uv = g.attributes.uv, n = g.attributes.normal, p = g.attributes.position;
    for (let i = 0; i < uv.count; i++) {
      const ax = Math.abs(n.getX(i)), ay = Math.abs(n.getY(i)), az = Math.abs(n.getZ(i));
      if (ax >= ay && ax >= az) uv.setXY(i, p.getZ(i), p.getY(i)); else if (ay >= az) uv.setXY(i, p.getX(i), p.getZ(i)); else uv.setXY(i, p.getX(i), p.getY(i));
    }
    g.translate(x, y, z); put(mat, g);
    if (collide) { C.box(V(x, y, z), V(w / 2, h / 2, d / 2), null, "metal"); L.minimap.push({ x, z, w, d, rot: 0 }); }
  }
  function scyl(mat, a, b, r, { seg = 20, collide = true } = {}) {
    a = V(...a); b = V(...b);
    const dir = b.clone().sub(a), len = dir.length();
    const g = uvCylinder(r, len, seg);
    g.applyMatrix4(_M.compose(a.clone().add(b).multiplyScalar(0.5), _Q.setFromUnitVectors(V(0, 1, 0), dir.normalize()), _S));
    put(mat, g);
    if (collide) C.capsule(a, b, r, "metal");
  }
  function sgeo(mat, geo, pos, quat = new THREE.Quaternion()) { geo.applyMatrix4(_M.compose(pos, quat, _S)); put(mat, geo); }
  function flange(mat, p, r) {                                     // flange on an X-axis pipe: ring + 8 bolts
    const q = new THREE.Quaternion().setFromUnitVectors(V(0, 1, 0), V(1, 0, 0));
    sgeo(mat, uvCylinder(r * 1.55, r * 0.4, 28), V(...p), q);
    for (let i = 0; i < 8; i++) {
      const a = (i + 0.5) / 8 * Math.PI * 2;
      sgeo(M.steel, new THREE.CylinderGeometry(r * 0.09, r * 0.09, r * 0.7, 6), V(p[0], p[1] + Math.cos(a) * r * 1.3, p[2] + Math.sin(a) * r * 1.3), q);
    }
  }
  async function glbInstances(name, items) {
    if (!items.length) return;
    const src = await loadGLB(name);
    const tmp = new THREE.Object3D(), parts = [];
    src.traverse(o => { if (o.isMesh) parts.push(o); });
    for (const part of parts) {
      const im = new THREE.InstancedMesh(part.geometry, part.material, items.length);
      im.castShadow = true; im.receiveShadow = true;
      items.forEach((it, i) => {
        tmp.position.set(...it.p); tmp.rotation.set(0, it.rotY || 0, 0); tmp.updateMatrix();
        im.setMatrixAt(i, new THREE.Matrix4().multiplyMatrices(tmp.matrix, part.matrixWorld));
      });
      im.computeBoundingSphere(); L.add(im);
    }
    const bb = new THREE.Box3().setFromObject(src), size = bb.getSize(V()), ctr = bb.getCenter(V());
    for (const it of items) {
      if (it.collide === false) continue;
      const q = new THREE.Quaternion().setFromAxisAngle(V(0, 1, 0), it.rotY || 0);
      C.box(ctr.clone().applyQuaternion(q).add(V(...it.p)), size.clone().multiplyScalar(0.5).subScalar(0.01), q, "wood");
    }
  }

  // ------------------------------------------------------------------ shell
  L.box(0, -0.15, 0, 2 * HX + 1, 0.3, 2 * HZ + 1, M.floor, { map: false, cast: false });
  const PL = 1.2;
  const DOOR_X = 2.75, PDOOR_X = -2.75;
  const holesS = [{ at: DOOR_X + HX, width: 3.6, y0: 0, y1: 4.2 }, { at: PDOOR_X + HX, width: 1.0, y0: 0, y1: 2.15 }];
  for (const [x0, z0, x1, z1, holes] of [[-HX, HZ, HX, HZ, holesS], [-HX, -HZ, HX, -HZ, []], [-HX, HZ, -HX, -HZ, []], [HX, -HZ, HX, HZ, []]]) {
    const nx = Math.sign(x0 === x1 ? x0 : 0), nz = Math.sign(z0 === z1 ? z0 : 0);
    L.wall(x0 + nx * 0.12, z0 + nz * 0.12, x1 + nx * 0.12, z1 + nz * 0.12, PL, 0.24, M.plinth, holes);
    L.wall(x0 + nx * 0.22, z0 + nz * 0.22, x1 + nx * 0.22, z1 + nz * 0.22, ROOF + 0.1, 0.1, M.clad, holes);
  }
  // roller door (closed) with guard posts, personnel door with the one exit sign
  sbox(M.door, DOOR_X, 2.1, HZ + 0.3, 3.6, 4.2, 0.05, { map: false });
  for (let i = 1; i < 10; i++) sbox(M.dark, DOOR_X, i * 0.42, HZ + 0.27, 3.6, 0.02, 0.015, { collide: false });
  sbox(M.dark, DOOR_X, 4.35, HZ + 0.08, 4.0, 0.3, 0.26, { collide: false });
  for (const s of [-1, 1]) scyl(hazard, [DOOR_X + s * 2.05, 0, HZ - 0.22], [DOOR_X + s * 2.05, 1.1, HZ - 0.22], 0.075);
  sbox(M.dark, PDOOR_X, 1.075, HZ + 0.18, 1.0, 2.15, 0.05);
  L.sign(["EXIT"], PDOOR_X, 2.45, HZ + 0.12, Math.PI, { w: 0.5, h: 0.2, icon: null });

  // portal frames every 5.5 m (columns on the long walls, rafters spanning Z), purlins along X, gable posts
  const frameX = [-5.5, 0, 5.5];
  for (const x of frameX) {
    for (const s of [-1, 1]) {
      L.ibeam([x, 0, s * (HZ - 0.19)], [x, EAVE, s * (HZ - 0.19)], 0.34, 0.17, M.frame);
      L.ibeam([x, EAVE - 0.5, s * (HZ - 0.19)], [x, EAVE - 0.06, s * (HZ - 1.4)], 0.22, 0.11, M.frame, { collide: false });
    }
    L.ibeam([x, EAVE + 0.02, -HZ], [x, EAVE + 0.02, HZ], 0.42, 0.18, M.frame);
  }
  for (const s of [-1, 1]) {
    for (const z of [-4, 0, 4]) L.ibeam([s * (HX - 0.1), 0, z], [s * (HX - 0.1), EAVE, z], 0.2, 0.1, M.frame);
    L.ibeam([s * (HX - 0.1), EAVE + 0.02, -HZ], [s * (HX - 0.1), EAVE + 0.02, HZ], 0.3, 0.14, M.frame);
  }
  for (let z = -HZ + 0.6; z <= HZ - 0.5; z += 1.85) L.ibeam([-HX, ROOF - 0.08, z], [HX, ROOF - 0.08, z], 0.14, 0.065, M.frame, { collide: false });
  // roof sheets with one skylight strip along the ridge line (z = 0); sun comes through it
  const SK = 0.85;
  for (const [z0, z1] of [[-HZ - 0.4, -SK], [SK, HZ + 0.4]]) L.box(0, ROOF + 0.06, (z0 + z1) / 2, 2 * HX + 1, 0.12, z1 - z0, M.roof, { collide: false, map: false });
  for (const x of [-8.25, -2.75, 2.75, 8.25]) L.panel(x, ROOF + 0.02, 0, 5.3, 2 * SK, 0xdfeaf8, 1.4);
  C.box(V(0, ROOF + 0.3, 0), V(HX + 1, 0.3, HZ + 1), null, "metal");

  // ------------------------------------------------------------------ floor markings (pedestrian route + door zone only)
  for (const x of [-5.25, -3.85]) L.paint(x, 0.45, 0.1, 14.9, 0xf0c419);
  hatch(L, DOOR_X, HZ - 0.95, 4.0, 1.5);

  // ------------------------------------------------------------------ pallet racking: one aisle, two runs (west)
  const runs = [-10.3, -6.45], DEPTH = 1.1, UPR = 5.6;
  const bayZ = [-6.9, -4.15, -1.4, 1.35, 4.1];
  const levels = [0, 1.55, 3.1, 4.65];
  const EMPTY = { run: 1, bay: 2 };                          // fly-through bay on the aisle-to-floor run
  for (const x of runs) {
    for (const z of bayZ) {
      for (const s of [-1, 1]) sbox(M.upright, x + s * (DEPTH / 2 - 0.045), UPR / 2, z, 0.09, UPR, 0.07);
      for (let y = 0.35; y < UPR - 0.6; y += 1.0) {                          // frame bracing
        const g = uvBox(0.03, 1.12, 0.025); g.rotateZ((Math.round(y) % 2 ? 1 : -1) * 0.72); g.translate(x, y + 0.5, z); put(M.upright, g);
      }
      sbox(M.dark, x, 0.008, z, DEPTH + 0.08, 0.016, 0.16, { collide: false });
    }
    for (let b = 0; b < bayZ.length - 1; b++) {
      const zc = (bayZ[b] + bayZ[b + 1]) / 2, len = bayZ[b + 1] - bayZ[b] - 0.07;
      for (const y of levels.slice(1)) for (const s of [-1, 1]) sbox(M.beam, x + s * (DEPTH / 2 - 0.03), y - 0.06, zc, 0.05, 0.12, len, { map: false });
    }
    sbox(hazard, x, 0.2, bayZ[bayZ.length - 1] + 0.32, DEPTH, 0.4, 0.1);   // rack-end guard facing the door
  }
  const full = [], low = [];
  runs.forEach((x, ri) => {
    for (let b = 0; b < bayZ.length - 1; b++) {
      if (ri === EMPTY.run && b === EMPTY.bay) continue;
      const z0 = bayZ[b] + 0.035, span = bayZ[b + 1] - bayZ[b] - 0.07;
      for (const [li, y] of levels.entries()) for (let k = 0; k < 3; k++)
        (li === 3 ? low : full).push({ p: [x, y, z0 + span * (k + 0.5) / 3], rotY: Math.PI / 2 });
    }
  });
  await glbInstances("pallet_cartons", full);
  await glbInstances("pallet_cartons_low", low);

  // ------------------------------------------------------------------ two CNC machining centres (north-east, facing the door)
  cnc(4.0, -4.5, 1); cnc(7.6, -4.5, 2);

  // ------------------------------------------------------------------ roller conveyor across the floor (fly under it)
  const CZ = 1.2, CX0 = 0.4, CX1 = 10.4, CW = 0.72, CY = 0.86;
  for (const s of [-1, 1]) sbox(M.dark, (CX0 + CX1) / 2, CY - 0.07, CZ + s * CW / 2, CX1 - CX0, 0.14, 0.05);
  C.box(V((CX0 + CX1) / 2, CY - 0.04, CZ), V((CX1 - CX0) / 2, 0.07, CW / 2), null, "metal");
  for (let x = CX0 + 0.25; x < CX1; x += 2.0) for (const s of [-1, 1]) {
    sbox(M.dark, x, (CY - 0.14) / 2, CZ + s * (CW / 2 - 0.03), 0.06, CY - 0.14, 0.06);
    if (s > 0) sbox(M.dark, x, 0.62, CZ, 0.04, 0.04, CW);
  }
  for (const s of [-1, 1]) sbox(M.dark, CX0 - 0.03, CY - 0.07, CZ, 0.06, 0.14, CW + 0.05, { collide: s > 0 });
  const rollers = new THREE.InstancedMesh(uvCylinder(0.03, CW - 0.06, 16), M.steel, Math.floor((CX1 - CX0) / 0.1));
  for (let i = 0; i < rollers.count; i++) rollers.setMatrixAt(i, _M.compose(V(CX0 + 0.05 + i * 0.1, CY - 0.02, CZ), _Q.setFromAxisAngle(V(1, 0, 0), Math.PI / 2), _S));
  rollers.castShadow = rollers.receiveShadow = true; L.add(rollers);
  await glbInstances("carton", [2.4, 5.4, 8.4].map(x => ({ p: [x, CY + 0.01, CZ], rotY: 0 })));

  // ------------------------------------------------------------------ pipe run on the north wall, with the steam leak
  const PZ = [[-7.45, 0.13, M.alu, null], [-7.1, 0.09, M.alu, M.bandGreen], [-6.82, 0.07, M.alu, M.bandBlue]];
  const PY = 3.6, PX0 = -4.4, PX1 = HX;
  for (let x = -2.75; x <= 8.25; x += 2.75) {                                 // wall brackets
    sbox(M.frame, x, PY - 0.18, -7.3, 0.08, 0.12, 1.4);
    sbox(M.frame, x, PY - 0.58, -7.85, 0.08, 0.7, 0.1);
    const g = uvBox(0.05, 1.2, 0.05); g.rotateX(0.985); g.translate(x, PY - 0.57, -7.4); put(M.frame, g);   // brace: wall plate → arm
  }
  for (const [z, r, mat, band] of PZ) {
    scyl(mat, [PX0, PY + r - 0.12, z], [PX1, PY + r - 0.12, z], r, { seg: 28 });
    sgeo(mat, new THREE.SphereGeometry(r, 20, 12), V(PX0, PY + r - 0.12, z));                    // end cap
    for (let x = -1.375; x <= 9.7; x += 2.75) {
      flange(mat, [x, PY + r - 0.12, z], r);
      if (band) for (const dx of [-0.4, 0.4]) { const g = uvCylinder(r * 1.04, 0.22, 28); g.rotateZ(Math.PI / 2); g.translate(x + dx, PY + r - 0.12, z); put(band, g); }
    }
  }
  L.sign(["STEAM"], 3.2, PY + 0.45, -HZ + 0.02, 0, { w: 0.45, h: 0.16, bg: "#ffffff", fg: "#222" });
  const leakP = V(1.375 + 0.12, PY + 0.01, -7.45 + 0.05), leakD = V(0.25, 0.3, 0.92).normalize();
  L.updaters.push(dt => fx?.steam?.(leakP, leakD, 55, dt));

  // ------------------------------------------------------------------ inspection points (visual only; free flight, no objectives)
  // The three markers the simulation brief names (leak, overheat, blockage), numbered as a judge route:
  // 1 steam leak on the pipe run -> 2 overheating CNC 2 (pulsing red beacon) -> 3 carton jammed at the conveyor end.
  const tag = { w: 0.62, h: 0.2, bg: "#f0c419", fg: "#1a1a1a" };
  L.sign(["INSPECT 1 · LEAK"], leakP.x, PY + 0.95, -HZ + 0.02, 0, tag);
  L.sign(["INSPECT 2 · OVERHEAT"], 7.6 + 0.35, 2.2, -4.5 + 1.122, 0, tag);
  const beacon = new THREE.MeshStandardMaterial({ color: 0x3a0705, emissive: 0xff2a14, emissiveIntensity: 2.5 });
  sgeo(beacon, new THREE.CylinderGeometry(0.04, 0.04, 0.09, 20), V(7.6 - 1.25, 3.04, -4.5 - 0.9));
  let beat = 0;
  L.updaters.push(dt => { beat += dt; beacon.emissiveIntensity = Math.sin(beat * 7) > 0 ? 3.0 : 0.25; });
  await glbInstances("carton", [{ p: [CX1 - 0.35, CY + 0.01, CZ + 0.12], rotY: 0.55 }]);
  sbox(M.dark, CX1 - 0.6, 1.0, CZ + CW / 2 + 0.03, 0.03, 0.3, 0.03, { collide: false });
  L.sign(["INSPECT 3 · BLOCKAGE"], CX1 - 0.6, 1.25, CZ + CW / 2 + 0.05, 0, tag);

  // ------------------------------------------------------------------ lighting
  const sun = new THREE.DirectionalLight(0xfff1dc, 3.0);
  sun.position.set(-8, 30, 7); sun.target.position.set(0, 0, 0);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -16, right: 16, top: 14, bottom: -14, near: 5, far: 60 });
  sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.03;
  L.add(sun); L.add(sun.target);
  const lamps = [];
  for (const x of [-8.4, -1.5, 5.5]) for (const z of [-3.6, 3.6]) lamps.push([x, z]);
  const lampModel = await import("../assets.js").then(m => m.model("hanging_industrial_lamp"));
  const lampParts = []; lampModel.updateMatrixWorld(true); lampModel.traverse(o => { if (o.isMesh) lampParts.push(o); });
  for (const part of lampParts) {
    const im = new THREE.InstancedMesh(part.geometry, part.material, lamps.length);
    lamps.forEach(([x, z], i) => im.setMatrixAt(i, new THREE.Matrix4().makeTranslation(x, ROOF - 0.12, z).multiply(part.matrixWorld)));
    im.castShadow = true; im.computeBoundingSphere(); L.add(im);
  }
  const glowGeo = new THREE.CircleGeometry(0.2, 28); glowGeo.rotateX(Math.PI / 2);
  lamps.forEach(([x, z], i) => {
    const yb = ROOF - 0.12 - 1.3;
    const glow = new THREE.Mesh(glowGeo, M.lampGlow); glow.position.set(x, yb, z); L.add(glow);
    L.spot(x, yb - 0.05, z, x, 0, z, { intensity: 120, angle: 74, penumbra: 0.8, decay: 2, shadow: i === 2 || i === 5, mapSize: 1024 });
  });

  // ------------------------------------------------------------------ flush batches
  for (const [mat, geos] of batches) {
    const m = new THREE.Mesh(mergeGeometries(geos), mat);
    m.castShadow = true; m.receiveShadow = true; L.add(m);
  }

  return {
    level: L, id: "industrial", title: "Industrial bay",
    subtitle: "Compact production bay: racking aisle, conveyor, two CNC machines. Inspect 1 leak, 2 overheat, 3 blockage.",
    spawn: { pos: V(DOOR_X, 1.2, 5.7), yaw: 0 },
    env: { hdri: "empty_warehouse_01_1k", envIntensity: 0.8, background: 0xd3e0ec, backgroundIntensity: 1,
           fog: null, exposure: 1.0, droneLight: 35 },
    ambient: (dt, p) => fx?.motes?.(p, 3.5, dt),
  };

  // ================================================================== local builders (hoisted)
  function cnc(x, z, n) {
    rbox(M.dark, x, 0.12, z, 2.9, 0.24, 2.3, 0.02);
    rbox(M.enamel, x, 1.32, z, 2.8, 2.16, 2.2, 0.07);
    rbox(M.dark, x, 0.42, z + 1.1, 2.82, 0.3, 0.04, 0.015, { collide: false });
    sbox(M.glass, x - 0.25, 1.55, z + 1.115, 1.15, 0.8, 0.02, { collide: false });
    sbox(M.dark, x - 0.25, 1.98, z + 1.12, 1.25, 0.05, 0.03, { collide: false });
    sbox(M.dark, x + 0.62, 1.4, z + 1.13, 0.05, 0.4, 0.05, { collide: false });
    sbox(M.dark, x + 1.25, 2.0, z + 1.25, 0.06, 0.06, 0.4, { collide: false });
    rbox(M.dark, x + 1.25, 1.65, z + 1.45, 0.48, 0.62, 0.12, 0.02, { collide: false });
    sgeo(M.screen, new THREE.PlaneGeometry(0.34, 0.24), V(x + 1.25, 1.78, z + 1.512));
    scyl(M.dark, [x - 1.25, 2.4, z - 0.9], [x - 1.25, 2.75, z - 0.9], 0.015, { collide: false });
    [[M.off, 2.95], [M.off, 2.87], [M.green, 2.79]].forEach(([m, y]) => scyl(m, [x - 1.25, y - 0.04, z - 0.9], [x - 1.25, y + 0.04, z - 0.9], 0.035, { collide: false }));
    rbox(M.dark, x + 0.6, 0.55, z - 1.4, 0.55, 1.1, 0.6, 0.03);
    L.sign(["CNC " + n], x - 1.0, 2.15, z + 1.112, 0, { w: 0.32, h: 0.14, bg: "#2a3138" });
  }
}

// ---------- module-level helpers ----------
function hazardMaterial() {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d");
  g.fillStyle = "#e9b300"; g.fillRect(0, 0, 128, 128); g.fillStyle = "#151515";
  for (let i = -128; i < 256; i += 64) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i + 32, 0); g.lineTo(i + 160, 128); g.lineTo(i + 128, 128); g.fill(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(2.5, 2.5); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return new THREE.MeshStandardMaterial({ map: t, roughness: 0.6, metalness: 0.1 });
}

function hatch(L, x, z, w, d) {
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d"); g.fillStyle = "rgba(240,196,25,0.85)";
  for (let i = -64; i < 128; i += 32) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i + 10, 0); g.lineTo(i + 74, 64); g.lineTo(i + 64, 64); g.fill(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(w / 0.9, d / 0.9); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ map: t, transparent: true, roughness: 0.75, polygonOffset: true, polygonOffsetFactor: -2, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.set(x, 0.003, z); m.receiveShadow = true; L.add(m);
  for (const [px, pz, pw, pd] of [[x, z - d / 2, w, 0.1], [x, z + d / 2, w, 0.1], [x - w / 2, z, 0.1, d], [x + w / 2, z, 0.1, d]]) L.paint(px, pz, pw, pd, 0xf0c419);
}
