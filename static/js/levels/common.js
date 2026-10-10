// Level builder: PBR geometry with metre-scaled UVs, steel sections, pipes, real glTF props (instanced where repeated)
// with matching colliders, rubble, lights and signage.
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { uvBox, uvCylinder, model } from "../assets.js";

export { pbr } from "../assets.js";

const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(1, 1, 1);

export class Level {
  constructor(scene, colliders) {
    this.scene = scene; this.col = colliders;
    this.group = new THREE.Group(); scene.add(this.group);
    this.updaters = []; this.minimap = []; this.pending = [];
    this.bounds = { minX: -10, maxX: 10, minZ: -10, maxZ: 10 };
  }

  add(o) { this.group.add(o); return o; }

  // ---------- primitives ----------
  box(x, y, z, w, h, d, material, { rot = null, collide = true, mat = "concrete", cast = true, map = true, rounded = 0 } = {}) {
    const geo = rounded ? roundedUvBox(w, h, d, rounded) : uvBox(w, h, d);
    const m = new THREE.Mesh(geo, material);
    m.position.set(x, y, z); if (rot) m.rotation.set(rot[0] || 0, rot[1] || 0, rot[2] || 0);
    m.castShadow = cast; m.receiveShadow = true; this.group.add(m);
    if (collide) this.col.box(m.position, new THREE.Vector3(w / 2, h / 2, d / 2), rot ? m.quaternion : null, mat);
    if (map && collide && y - h / 2 < 2.2 && h > 0.25) this.minimap.push({ x, z, w, d, rot: rot ? rot[1] || 0 : 0 });
    return m;
  }

  // Wall from (x0,z0) to (x1,z1) with rectangular openings {at (m along the wall), width, y0, y1}.
  wall(x0, z0, x1, z1, h, thick, material, holes = [], y0 = 0, opts = {}) {
    const along = new THREE.Vector3(x1 - x0, 0, z1 - z0), L = along.length(); along.normalize();
    const rot = Math.atan2(-along.z, along.x);
    const seg = (s0, s1, yb, yt) => {
      if (s1 - s0 < 0.01 || yt - yb < 0.01) return;
      const mid = (s0 + s1) / 2;
      this.box(x0 + along.x * mid, yb + (yt - yb) / 2, z0 + along.z * mid, s1 - s0, yt - yb, thick, material, { rot: [0, rot, 0], ...opts });
    };
    let s = 0;
    for (const hole of [...holes].sort((p, q) => p.at - q.at)) {
      const a = hole.at - hole.width / 2, b = hole.at + hole.width / 2;
      seg(s, a, y0, y0 + h); seg(a, b, y0, y0 + (hole.y0 || 0)); seg(a, b, y0 + (hole.y1 ?? h), y0 + h);
      s = b;
    }
    seg(s, L, y0, y0 + h);
  }

  // Round pipe / bar between two points (capsule collider).
  pipe(a, b, r, material, { collide = true, seg = 20, mat = "metal", cast = true } = {}) {
    a = new THREE.Vector3(...a); b = new THREE.Vector3(...b);
    const dir = b.clone().sub(a), len = dir.length();
    const m = new THREE.Mesh(uvCylinder(r, len, seg), material);
    m.position.copy(a).add(b).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    m.castShadow = cast; m.receiveShadow = true; this.group.add(m);
    if (collide) this.col.capsule(a, b, r, mat);
    return m;
  }

  flange(p, axis, r, material) {
    const m = new THREE.Mesh(uvCylinder(r * 1.55, r * 0.45, 24), material);
    m.position.set(...p); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...axis).normalize());
    m.castShadow = true; this.group.add(m);
    const bolts = 8;
    for (let i = 0; i < bolts; i++) {
      const bolt = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.09, r * 0.09, r * 0.7, 6), material);
      const a = i / bolts * Math.PI * 2;
      bolt.position.set(Math.cos(a) * r * 1.3, 0, Math.sin(a) * r * 1.3); m.add(bolt);
    }
    return m;
  }

  // Steel I-section from a to b (h = depth, b = flange width). Box collider.
  ibeam(a, b, h, w, material, { collide = true, tf = null, tw = null } = {}) {
    a = new THREE.Vector3(...a); b = new THREE.Vector3(...b);
    tf = tf ?? h * 0.07; tw = tw ?? h * 0.05;
    const s = new THREE.Shape();
    s.moveTo(-w / 2, -h / 2); s.lineTo(w / 2, -h / 2); s.lineTo(w / 2, -h / 2 + tf); s.lineTo(tw / 2, -h / 2 + tf);
    s.lineTo(tw / 2, h / 2 - tf); s.lineTo(w / 2, h / 2 - tf); s.lineTo(w / 2, h / 2); s.lineTo(-w / 2, h / 2);
    s.lineTo(-w / 2, h / 2 - tf); s.lineTo(-tw / 2, h / 2 - tf); s.lineTo(-tw / 2, -h / 2 + tf); s.lineTo(-w / 2, -h / 2 + tf);
    const dir = b.clone().sub(a), len = dir.length();
    const geo = new THREE.ExtrudeGeometry(s, { depth: len, bevelEnabled: false });
    geo.translate(0, 0, -len / 2);
    const m = new THREE.Mesh(geo, material);
    m.position.copy(a).add(b).multiplyScalar(0.5);
    // extrusion axis (local Z) → beam direction; keep the web vertical for horizontal beams
    const zAxis = dir.clone().normalize();
    const upHint = Math.abs(zAxis.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
    const xAxis = new THREE.Vector3().crossVectors(upHint, zAxis).normalize(), yAxis = new THREE.Vector3().crossVectors(zAxis, xAxis);
    m.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(xAxis, yAxis, zAxis));
    m.castShadow = true; m.receiveShadow = true; this.group.add(m);
    if (collide) this.col.box(m.position, new THREE.Vector3(w / 2, h / 2, len / 2), m.quaternion, "metal");
    if (collide && Math.min(a.y, b.y) < 2.2) this.minimap.push({ x: m.position.x, z: m.position.z, w: Math.abs(dir.x) + w, d: Math.abs(dir.z) + w, rot: 0 });
    return m;
  }

  // ---------- real models ----------
  // Single prop. collide: "box" (one OBB), "parts" (OBB per mesh part, for open frames), "cyl" (vertical capsule), false.
  async prop(name, x, y, z, { rotY = 0, rot = null, scale = 1, collide = "box", mat = "metal", shrink = 0.01 } = {}) {
    const o = await model(name);
    o.position.set(x, y, z); o.scale.setScalar(scale);
    if (rot) o.rotation.set(...rot); else o.rotation.y = rotY;
    this.group.add(o); o.updateMatrixWorld(true);
    this.collideObject(o, collide, mat, shrink);
    return o;
  }

  collideObject(o, collide, mat = "metal", shrink = 0.01) {
    if (collide === "box") this.col.fromObject(o, mat, shrink);
    else if (collide === "parts") o.traverse(c => { if (c.isMesh) this.col.fromObject(c, mat, shrink); });
    else if (collide === "cyl") {
      const bb = new THREE.Box3().setFromObject(o), r = Math.min(bb.max.x - bb.min.x, bb.max.z - bb.min.z) / 2;
      const cx = (bb.min.x + bb.max.x) / 2, cz = (bb.min.z + bb.max.z) / 2;
      this.col.capsule(new THREE.Vector3(cx, bb.min.y + r * 0.6, cz), new THREE.Vector3(cx, Math.max(bb.min.y + r * 0.6, bb.max.y - r * 0.6), cz), r, mat);
    }
    if (collide) { const bb = new THREE.Box3().setFromObject(o); if (bb.min.y < 2) this.minimap.push({ x: (bb.min.x + bb.max.x) / 2, z: (bb.min.z + bb.max.z) / 2, w: bb.max.x - bb.min.x, d: bb.max.z - bb.min.z, rot: 0 }); }
  }

  // Many copies of one model as InstancedMeshes (one draw call per model part). items: [{p:[x,y,z], rotY, scale, collide}]
  async instances(name, items, { collide = "box", mat = "metal", shrink = 0.01 } = {}) {
    if (!items.length) return;
    const src = await model(name);
    src.updateMatrixWorld(true);
    const parts = [];
    src.traverse(o => { if (o.isMesh) parts.push(o); });
    const tmp = new THREE.Object3D();
    for (const part of parts) {
      const im = new THREE.InstancedMesh(part.geometry, part.material, items.length);
      im.castShadow = true; im.receiveShadow = true;
      items.forEach((it, i) => {
        tmp.position.set(...it.p); tmp.rotation.set(0, it.rotY || 0, 0); tmp.scale.setScalar(it.scale || 1); tmp.updateMatrix();
        im.setMatrixAt(i, _m.multiplyMatrices(tmp.matrix, part.matrixWorld));
      });
      im.computeBoundingSphere(); this.group.add(im);
    }
    // colliders: transform the source bbox per instance
    const bb = new THREE.Box3().setFromObject(src), size = bb.getSize(new THREE.Vector3()), ctr = bb.getCenter(new THREE.Vector3());
    for (const it of items) {
      const c = it.collide ?? collide; if (!c) continue;
      const s = it.scale || 1, q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), it.rotY || 0);
      const centre = ctr.clone().multiplyScalar(s).applyQuaternion(q).add(new THREE.Vector3(...it.p));
      if (c === "cyl") {
        const r = Math.min(size.x, size.z) / 2 * s;
        this.col.capsule(centre.clone().setY(it.p[1] + r * 0.6), centre.clone().setY(it.p[1] + Math.max(r * 0.6, size.y * s - r * 0.6)), r, mat);
      } else this.col.box(centre, size.clone().multiplyScalar(s / 2).subScalar(shrink), q, mat);
      if (it.p[1] < 2) this.minimap.push({ x: centre.x, z: centre.z, w: size.x * s, d: size.z * s, rot: it.rotY || 0, round: c === "cyl" });
    }
  }

  // ---------- procedural detail ----------
  // Irregular concrete chunks (displaced icosahedra) with sphere colliders.
  rubble(cx, cz, radius, count, material, { y = 0, minR = 0.08, maxR = 0.35, seed = 1, collide = true } = {}) {
    const rnd = mulberry(seed), geos = [];
    for (let i = 0; i < count; i++) {
      const r = minR + (maxR - minR) * rnd() ** 2;
      const a = rnd() * Math.PI * 2, d = Math.sqrt(rnd()) * radius;
      const x = cx + Math.cos(a) * d, z = cz + Math.sin(a) * d;
      const g = new THREE.IcosahedronGeometry(r, 1);
      const pos = g.attributes.position;
      for (let k = 0; k < pos.count; k++) {
        const v = new THREE.Vector3().fromBufferAttribute(pos, k);
        const f = 0.7 + 0.5 * noise3(v.x * 7 + i, v.y * 7, v.z * 7) ; v.multiplyScalar(f); v.y *= 0.55 + rnd() * 0.3;
        pos.setXYZ(k, v.x, v.y, v.z);
      }
      g.computeVertexNormals();
      const uv = g.attributes.uv; for (let k = 0; k < uv.count; k++) uv.setXY(k, uv.getX(k) * r * 6, uv.getY(k) * r * 3);
      const yy = y + r * 0.35;
      g.rotateY(rnd() * 6); g.translate(x, yy, z); geos.push(g);   // icosahedra are already non-indexed
      if (collide && r > 0.12) this.col.capsule(new THREE.Vector3(x, yy, z), new THREE.Vector3(x, yy, z), r * 0.75, "concrete");
    }
    const m = new THREE.Mesh(mergeGeometries(geos), material); m.castShadow = true; m.receiveShadow = true; this.group.add(m);
    return m;
  }

  // Euro pallet (1.2 x 0.8 x 0.144 m) as one merged mesh; returns its geometry for instancing.
  static palletGeometry() {
    const parts = [];
    const add = (w, h, d, x, y, z) => { const g = uvBox(w, h, d); g.translate(x, y, z); parts.push(g); };
    for (let i = 0; i < 5; i++) add(1.2, 0.022, 0.1 + (i % 4 === 0 ? 0.045 : 0), 0, 0.133, -0.35 + i * 0.175);
    for (const z of [-0.35, 0, 0.35]) for (const x of [-0.53, 0, 0.53]) add(0.145, 0.078, 0.1, x, 0.083, z);
    for (const z of [-0.35, 0, 0.35]) add(1.2, 0.022, 0.1, 0, 0.033, z);
    for (const x of [-0.53, 0, 0.53]) add(0.145, 0.022, 0.8, x, 0.011, 0);
    return mergeGeometries(parts);
  }

  // ---------- lights ----------
  spot(x, y, z, tx, ty, tz, { color = 0xfff2dc, intensity = 300, angle = 55, penumbra = 0.6, distance = 0, decay = 2, shadow = false, mapSize = 1024 } = {}) {
    const l = new THREE.SpotLight(color, intensity, distance, THREE.MathUtils.degToRad(angle), penumbra, decay);
    l.position.set(x, y, z); l.target.position.set(tx, ty, tz);
    if (shadow) { l.castShadow = true; l.shadow.mapSize.set(mapSize, mapSize); l.shadow.bias = -0.0004; l.shadow.normalBias = 0.02; l.shadow.camera.near = 0.3; }
    this.group.add(l, l.target); return l;
  }

  point(x, y, z, { color = 0xffffff, intensity = 10, distance = 0, decay = 2 } = {}) {
    const l = new THREE.PointLight(color, intensity, distance, decay); l.position.set(x, y, z); this.group.add(l); return l;
  }

  flicker(light, { strength = 1, base = light.intensity, emissive = null } = {}) {
    let t = Math.random() * 10;
    this.updaters.push(dt => {
      t += dt;
      const on = Math.sin(t * 13.1) + Math.sin(t * 7.3) + Math.sin(t * 2.1) > -1.4 * strength;
      light.intensity = on ? base * (0.85 + 0.15 * Math.sin(t * 50)) : base * 0.05;
      if (emissive) emissive.emissiveIntensity = on ? 1 : 0.05;
    });
  }

  // Emissive panel (light fixture face / skylight).
  panel(x, y, z, w, d, color, intensity = 3, rotX = Math.PI / 2) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ color: 0x111111, emissive: color, emissiveIntensity: intensity }));
    m.rotation.x = rotX; m.position.set(x, y, z); this.group.add(m); return m;
  }

  // Painted floor line / zone (sits a few mm above the floor, polygon offset avoids z-fighting).
  paint(x, z, w, d, color, { y = 0.002, rot = 0, opacity = 0.9 } = {}) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ color, roughness: 0.7, transparent: opacity < 1, opacity, polygonOffset: true, polygonOffsetFactor: -2 }));
    m.rotation.set(-Math.PI / 2, 0, rot); m.position.set(x, y, z); m.receiveShadow = true; this.group.add(m); return m;
  }

  // Safety sign (ISO-style) on a wall.
  sign(lines, x, y, z, rotY, { w = 0.9, h = 0.45, bg = "#1b7f3a", fg = "#ffffff", icon = null } = {}) {
    const c = document.createElement("canvas"); c.width = 512; c.height = Math.round(512 * h / w);
    const g = c.getContext("2d");
    g.fillStyle = bg; g.fillRect(0, 0, c.width, c.height);
    g.strokeStyle = fg; g.lineWidth = 10; g.strokeRect(12, 12, c.width - 24, c.height - 24);
    g.fillStyle = fg; g.textAlign = "center"; g.textBaseline = "middle";
    const ls = [].concat(lines);
    let fs = Math.min(70, (c.height - 60) / ls.length * 0.8);           // fit by height…
    g.font = `700 ${fs}px "Segoe UI", Arial`;
    const avail = c.width - 60 - (icon ? 120 : 0), widest = Math.max(...ls.map(l => g.measureText(l).width));
    if (widest > avail) { fs *= avail / widest; g.font = `700 ${fs}px "Segoe UI", Arial`; }   // …and by width
    ls.forEach((l, i) => g.fillText(l, c.width / 2 + (icon ? 40 : 0), c.height / 2 + (i - (ls.length - 1) / 2) * fs * 1.15));
    if (icon) { g.font = `${c.height * 0.5}px Segoe UI Emoji, Arial`; g.fillText(icon, 70, c.height / 2 + 4); }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: t, roughness: 0.55 }));
    m.position.set(x, y, z); m.rotation.y = rotY; this.group.add(m); return m;
  }

  async ready() { await Promise.all(this.pending); }

  dispose() {
    this.scene.remove(this.group);
    this.group.traverse(o => {
      if (o.isLight && o.shadow && o.shadow.map) o.shadow.map.dispose();
      if (o.geometry && !o.userData.shared) o.geometry.dispose();
    });
  }
}

function roundedUvBox(w, h, d, r) {
  const g = new RoundedBoxGeometry(w, h, d, 3, r);
  const uv = g.attributes.uv, n = g.attributes.normal, p = g.attributes.position;
  for (let i = 0; i < uv.count; i++) {              // planar metre UVs by dominant normal
    const ax = Math.abs(n.getX(i)), ay = Math.abs(n.getY(i)), az = Math.abs(n.getZ(i));
    if (ax >= ay && ax >= az) uv.setXY(i, p.getZ(i), p.getY(i)); else if (ay >= az) uv.setXY(i, p.getX(i), p.getZ(i)); else uv.setXY(i, p.getX(i), p.getY(i));
  }
  return g;
}

export function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function noise3(x, y, z) { return (Math.sin(x * 1.7 + Math.sin(y * 2.3)) + Math.sin(y * 1.9 + Math.sin(z * 1.3)) + Math.sin(z * 2.1 + Math.sin(x * 1.1))) / 3; }
