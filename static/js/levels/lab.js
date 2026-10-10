// Physics test bay: a clean hangar-like room to show the cage physics in isolation —
// a ramp to roll down, a wall to climb, a pipe to roll along, a low gap to crawl through, a pole to spin off.
import * as THREE from "three";
import { Level, pbr } from "./common.js";

export async function buildLab({ scene, colliders }) {
  const L = new Level(scene, colliders);
  L.bounds = { minX: -10, maxX: 10, minZ: -10, maxZ: 10 };
  const floor = pbr("concrete_floor_worn_001", { size: 4 });
  const wall = pbr("concrete_wall_008", { size: 3, tint: 0xcfd3d6 });
  const steel = pbr("metal_plate", { size: 1.5, tint: 0x9aa4ad });
  const yellow = pbr("metal_plate", { size: 1.5, tint: 0xe2b21c, metalness: 0.3 });

  L.box(0, -0.1, 0, 20, 0.2, 20, floor, { map: false, cast: false });
  L.box(0, 6.1, 0, 20, 0.2, 20, wall, { map: false, cast: false });
  L.box(0, 3, -10.1, 20.4, 6, 0.2, wall); L.box(0, 3, 10.1, 20.4, 6, 0.2, wall);
  L.box(-10.1, 3, 0, 0.2, 6, 20, wall); L.box(10.1, 3, 0, 0.2, 6, 20, wall);
  // 20° ramp (roll down it with motors throttled back)
  L.box(-5, 0.75, -4, 3, 0.12, 4.4, steel, { rot: [Math.atan2(1.5, 4.2), 0, 0], mat: "metal" });
  // horizontal pipe to roll along, pole to hit off-centre, low slab to crawl under
  L.pipe([2, 1.2, -6], [8, 1.2, -6], 0.15, yellow);
  L.pipe([4, 0, 2], [4, 4, 2], 0.08, yellow);
  L.box(-4, 0.62, 5, 3, 0.1, 3, steel, { mat: "metal" });
  for (const [x, z] of [[-5.45, 3.55], [-2.55, 3.55], [-5.45, 6.45], [-2.55, 6.45]]) L.box(x, 0.29, z, 0.1, 0.58, 0.1, steel, { mat: "metal" });
  for (let i = 0; i < 5; i++) L.paint(-8 + i * 4, 9.2, 0.12, 1.2, 0xe2b21c);

  L.add(new THREE.HemisphereLight(0xdfe8f0, 0x3a3836, 0.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2); sun.position.set(-6, 14, 8); sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 40 });
  sun.shadow.bias = -0.0005; L.add(sun);
  for (const [x, z] of [[-5, -5], [5, -5], [-5, 5], [5, 5]]) { L.spot(x, 5.9, z, x, 0, z, { intensity: 60, angle: 60, shadow: false }); L.panel(x, 5.98, z, 1.2, 0.4, 0xffffff, 4); }

  return {
    level: L, id: "lab", title: "Physics test bay", subtitle: "Ramp, wall, pipe, pole and crawl gap for testing the cage contact physics",
    spawn: { pos: new THREE.Vector3(0, 1, 7), yaw: 0 },
    env: { hdri: "empty_warehouse_01_1k", envIntensity: 0.35, background: 0x22262a, exposure: 0.85, droneLight: 8 },
  };
}
