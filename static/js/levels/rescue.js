// Collapse site at night — compact free-flight environment (no objectives).
// One single-storey brick building, 14 x 10 m: a corridor along the west wall and three rooms.
//   Room A (south-west): part of the roof came down — a slab fell onto a desk, leaving a low void with a mannequin.
//   Room B (north-west): its doorway is plugged with rubble; the only way in is a ~0.65 m gap over the pile.
//   Room C (east):       a small fire smoulders in the back corner; smoke vents through the front window.
// Outside: responders' barrier with a light bar and a searchlight on the entrance.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { Level, pbr } from "./common.js";

const dummyCache = new Map();
async function dummy(pose) {
  if (!dummyCache.has(pose)) dummyCache.set(pose, new GLTFLoader().loadAsync(`assets/blender/dummy_${pose}.glb`).then(g => g.scene));
  const o = (await dummyCache.get(pose)).clone(true);
  o.traverse(c => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; } });
  return o;
}

export async function buildRescue({ scene, colliders, fx }) {
  const L = new Level(scene, colliders);
  L.bounds = { minX: -12, maxX: 12, minZ: -8, maxZ: 13 };
  const H = 3.2, ROOF = 0.25, EXT = 0.3, INT = 0.15;
  const jobs = [];

  // ---------------- materials (one palette, large tiles) ----------------
  const M = {
    street: pbr("asphalt_02", { size: 6, tint: 0x7d7d7d }),
    kerb: pbr("concrete_wall_008", { size: 3, tint: 0x9c9890 }),
    brick: pbr("factory_brick", { size: 3.2, tint: 0xb4a89c }),
    plaster: pbr("damaged_plaster", { size: 3.5, tint: 0xc9c2b6 }),
    floor: pbr("concrete_floor_damaged_01", { size: 6, tint: 0xa9a49a }),
    slab: pbr("dirty_concrete", { size: 4, tint: 0x9d9a93 }),
    debris: pbr("concrete_debris", { size: 1.4, tint: 0x9d9a93 }),
    rebar: pbr("rusty_metal_02", { size: 0.5 }),
    invisible: new THREE.MeshBasicMaterial({ visible: false }),
  };

  // ---------------- ground, street, boundaries ----------------
  L.box(0, -0.15, 2.5, 24, 0.3, 21, M.street, { map: false, cast: false, mat: "asphalt" });
  L.box(0, 0.06, 5.9, 18, 0.12, 1.5, M.kerb, { cast: false, map: false });
  L.box(0, 0.004, 0, 14, 0.008, 10, M.floor, { collide: false, cast: false, map: false });
  for (const [x, z, w, d] of [[-12.5, 2.5, 1, 21], [12.5, 2.5, 1, 21], [0, -8.5, 24, 1], [0, 13.5, 24, 1]])
    L.box(x, 4, z, w, 8, d, M.invisible, { cast: false, map: false });
  L.box(0, 8.5, 2.5, 24, 1, 21, M.invisible, { cast: false, map: false });

  // ---------------- shell ----------------
  const win = (at, width = 1.5) => ({ at, width, y0: 0.95, y1: 2.15 });
  L.wall(7, 5, -7, 5, H + ROOF, EXT, M.brick, [{ at: 13.1, width: 1.3, y0: 0, y1: 2.3 }, win(8.8), win(2.7)], 0, { mat: "brick" });
  L.wall(-7, -5, 7, -5, H + ROOF, EXT, M.brick, [], 0, { mat: "brick" });
  L.wall(-7, 5, -7, -5, H + ROOF, EXT, M.brick, [], 0, { mat: "brick" });
  L.wall(7, -5, 7, 5, H + ROOF, EXT, M.brick, [], 0, { mat: "brick" });
  for (const [x, z, w, d] of [[0, 5, 14.3, 0.3], [0, -5, 14.3, 0.3], [-7, 0, 0.3, 10.3], [7, 0, 0.3, 10.3]])
    L.box(x, H + ROOF + 0.2, z, w, 0.4, d, M.brick, { map: false });                       // parapet
  for (const x of [-1.8, 4.3]) L.box(x, 0.92, 5.2, 1.7, 0.06, 0.4, M.kerb, { map: false });   // window sills

  // interior partitions
  L.wall(-5.2, 5, -5.2, -5, H, INT, M.plaster, [{ at: 2.2, width: 1.0, y0: 0, y1: 2.1 }, { at: 7.2, width: 1.0, y0: 0, y1: 2.1 }]);
  L.wall(-5.2, 0.6, 1.5, 0.6, H, INT, M.plaster);
  L.wall(1.5, 5, 1.5, -5, H, INT, M.plaster, [{ at: 2.2, width: 1.0, y0: 0, y1: 2.1 }]);

  // roof slab with the collapse hole over room A (x -3.2..-0.4, z 1.6..4.2)
  const roof = (x0, x1, z0, z1) => L.box((x0 + x1) / 2, H + ROOF / 2, (z0 + z1) / 2, x1 - x0, ROOF, z1 - z0, M.slab, { map: false });
  roof(-7, 7, -5, 1.6); roof(-7, -3.2, 1.6, 4.2); roof(-0.4, 7, 1.6, 4.2); roof(-7, 7, 4.2, 5);

  // ---------------- room A: the collapse ----------------
  // the fallen roof section rests on a desk at one end and on the floor at the other; the void under it is ~0.5–0.7 m
  jobs.push(L.prop("metal_office_desk", -3.6, 0, 2.95, { rotY: Math.PI / 2, collide: "parts" }));
  L.box(-1.95, 0.5, 2.9, 2.85, 0.22, 2.45, M.slab, { rot: [0, 0, -0.281], map: false });
  // broken edge of the hole: a few jagged pieces + bent rebar hanging into the room
  for (const [x, z, s, r] of [[-3.05, 2.2, 0.32, 0.4], [-0.55, 3.8, 0.28, 1.2], [-1.6, 1.68, 0.3, 2.1], [-2.6, 4.1, 0.26, 0.7]])
    L.box(x, H + 0.02, z, s * 1.4, 0.24, s, M.slab, { rot: [0.35, r, 0.25], collide: false, map: false });
  for (const [a, b] of [[[-3.15, 3.15, 2.0], [-2.95, 2.45, 2.15]], [[-3.15, 3.15, 3.0], [-2.9, 2.6, 3.1]], [[-0.45, 3.15, 2.6], [-0.7, 2.35, 2.5]], [[-1.4, 3.15, 1.65], [-1.5, 2.55, 1.9]]])
    L.pipe(a, b, 0.008, M.rebar, { collide: false });
  for (const [a, b] of [[[-0.62, 0.15, 2.0], [-0.25, 0.35, 1.7]], [[-0.62, 0.15, 3.6], [-0.2, 0.45, 3.9]]]) L.pipe(a, b, 0.008, M.rebar, { collide: false });
  // debris lies where the slab hit the floor and under the hole — one coherent pile, nothing elsewhere
  L.rubble(-0.35, 2.9, 0.75, 16, M.debris, { seed: 3, minR: 0.07, maxR: 0.3 });
  L.rubble(-1.5, 4.4, 0.45, 7, M.debris, { seed: 4, minR: 0.05, maxR: 0.18, collide: false });

  // ---------------- room B: sealed off — doorway plugged by rubble, a gap remains over the top ----------------
  L.box(-5.2, 0.7, -2.2, 0.5, 1.4, 1.0, M.debris, { rot: [0.04, 0, 0], map: false });
  L.rubble(-5.75, -2.2, 0.75, 12, M.debris, { seed: 7, minR: 0.1, maxR: 0.34 });
  L.rubble(-4.75, -2.25, 0.5, 6, M.debris, { seed: 8, minR: 0.08, maxR: 0.26 });
  jobs.push(L.prop("SchoolChair_01", -0.6, 0, -3.6, { rotY: 2.3 }));

  // ---------------- room C: smouldering corner ----------------
  const char = o => o.then(obj => obj.traverse(c => { if (c.isMesh) { c.material = c.material.clone(); c.material.color.setRGB(0.03, 0.028, 0.025); c.material.roughness = 1; c.material.metalness = 0; } }));
  jobs.push(char(L.prop("painted_wooden_cabinet", 6.3, 0, -3.9, { rotY: -Math.PI / 2 })));
  jobs.push(char(L.prop("WoodenTable_01", 4.9, 0, -4.3, { rotY: 0.25 })));
  const fireAt = new THREE.Vector3(5.6, 0.25, -3.75);
  const fire = L.point(5.6, 0.8, -3.6, { color: 0xff7a2a, intensity: 38, distance: 12 });
  L.updaters.push(dt => {
    const f = 0.8 + 0.2 * Math.sin(performance.now() * 0.017) * Math.sin(performance.now() * 0.0053) + 0.08 * Math.random();
    fire.intensity = 38 * f;
    if (fx.fire) fx.fire(fireAt, 0.9, 0.6, dt);
    if (fx.smoke) { fx.smoke(fireAt.clone().setY(1.2), 6, dt); fx.smoke(new THREE.Vector3(4.3, 2.05, 5.2), 3, dt); }
  });

  // ---------------- mannequins ----------------
  const D = async (pose, x, z, rotY) => { const o = await dummy(pose); o.position.set(x, 0, z); o.rotation.y = rotY; L.add(o); L.collideObject(o, "box", "fabric", 0.04); };
  jobs.push(D("supine", -2.55, 2.95, 0.05));           // in the void under the fallen slab
  jobs.push(D("side", -2.2, -2.3, 0.55));              // room B

  // ---------------- outside: responders ----------------
  jobs.push(L.prop("concrete_road_barrier", -4.6, 0, 8.4, { rotY: 0.08, mat: "concrete" }));
  jobs.push(L.prop("concrete_road_barrier", 0.6, 0, 8.7, { rotY: -0.12, mat: "concrete" }));
  jobs.push(L.prop("portable_searchlight", 0.6, 0.83, 8.65, { rotY: Math.PI * 0.82, collide: false }));
  const bar = (x, c) => { const m = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.07, 0.09), new THREE.MeshStandardMaterial({ color: 0x111111, emissive: c, emissiveIntensity: 0 })); m.position.set(x, 0.875, 8.42); L.add(m); return m; };
  const redM = bar(-4.75, 0xff1010), blueM = bar(-4.45, 0x2050ff);
  const red = L.point(-4.75, 1.0, 8.3, { color: 0xff1a1a, intensity: 0, distance: 14 }), blue = L.point(-4.45, 1.0, 8.3, { color: 0x2a5cff, intensity: 0, distance: 14 });
  let et = 0;
  L.updaters.push(dt => {
    et += dt; const ph = Math.floor(et * 5) % 4, strobe = (et * 10 % 1) < 0.5;
    const onR = ph === 0 || (ph === 1 && strobe), onB = ph === 2 || (ph === 3 && strobe);
    red.intensity = onR ? 7 : 0; blue.intensity = onB ? 9 : 0; redM.material.emissiveIntensity = onR ? 8 : 0.1; blueM.material.emissiveIntensity = onB ? 8 : 0.1;
  });

  // ---------------- light: moon + searchlight (shadows), fire and light bar as practicals ----------------
  const moon = new THREE.DirectionalLight(0xa9bcff, 0.6);
  moon.position.set(-9, 22, 9); moon.target.position.set(-1.8, 0, 2.9);
  moon.castShadow = true; moon.shadow.mapSize.set(2048, 2048); moon.shadow.bias = -0.0005; moon.shadow.normalBias = 0.03;
  Object.assign(moon.shadow.camera, { left: -14, right: 14, top: 14, bottom: -14, near: 1, far: 60 });
  L.add(moon); L.add(moon.target);
  L.spot(0.55, 1.05, 8.55, -6.1, 1.0, 5.0, { color: 0xf2f4ff, intensity: 150, angle: 16, penumbra: 0.55, shadow: true, mapSize: 1024 });

  await Promise.all(jobs);
  return {
    level: L, id: "rescue", title: "Collapse site",
    subtitle: "Night — a single-storey building with a roof collapse, a sealed room and a smouldering fire",
    spawn: { pos: new THREE.Vector3(-1.4, 1.5, 12.4), yaw: 0.18 },
    env: { hdri: "rogland_moonlit_night_2k", envIntensity: 0.22, background: "hdri", backgroundIntensity: 0.07,
           fog: { color: 0x0b0e14, near: 8, far: 40 }, exposure: 1.15, droneLight: 70 },
    ambient(dt, p) { if (fx.motes) fx.motes(p, 3, dt); },
  };
}
