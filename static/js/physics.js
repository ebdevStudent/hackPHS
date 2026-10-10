// Collision world for the ball drone: oriented boxes + capsules, with sphere contact queries and analytic raycasts
// (used by the chase camera and the altitude sensor, so they never have to test the high-poly render meshes).
import * as THREE from "three";

const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _o = new THREE.Vector3(), _d = new THREE.Vector3();

export class Colliders {
  constructor() { this.list = []; }
  clear() { this.list.length = 0; }

  box(center, half, quat = null, mat = "concrete") {
    const c = { kind: "box", c: center.clone(), h: half.clone(), q: quat ? quat.clone() : null, qi: quat ? quat.clone().invert() : null, mat };
    c.r = half.length(); this.list.push(c); return c;
  }

  capsule(a, b, r, mat = "metal") {
    const c = { kind: "capsule", a: a.clone(), b: b.clone(), rad: r, mat };
    c.mid = a.clone().add(b).multiplyScalar(0.5); c.r = a.distanceTo(b) / 2 + r; this.list.push(c); return c;
  }

  // Oriented box from a mesh/group's local bounding box (handles rotated, scaled models).
  fromObject(obj, mat = "metal", shrink = 0) {
    obj.updateWorldMatrix(true, true);
    const box = new THREE.Box3();
    const inv = new THREE.Matrix4().copy(obj.matrixWorld).invert();
    obj.traverse(o => {
      if (!o.isMesh) return;
      o.geometry.computeBoundingBox();
      const b = o.geometry.boundingBox.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
      box.union(b);
    });
    const pos = new THREE.Vector3(), quat = new THREE.Quaternion(), scl = new THREE.Vector3();
    obj.matrixWorld.decompose(pos, quat, scl);
    const half = box.getSize(new THREE.Vector3()).multiply(scl).multiplyScalar(0.5).subScalar(shrink).max(new THREE.Vector3(0.005, 0.005, 0.005));
    const centre = box.getCenter(new THREE.Vector3()).applyMatrix4(obj.matrixWorld);
    return this.box(centre, half, quat, mat);
  }

  // Sphere contacts: [{n (unit, out of the obstacle), depth, point, mat}]
  sphereContacts(p, radius, out = []) {
    out.length = 0;
    for (const c of this.list) {
      const centre = c.kind === "box" ? c.c : c.mid;
      if (centre.distanceToSquared(p) > (c.r + radius) ** 2) continue;
      const hit = c.kind === "box" ? sphereBox(p, radius, c) : sphereCapsule(p, radius, c);
      if (hit) { hit.mat = c.mat; out.push(hit); }
    }
    return out;
  }

  // Colliders whose bounding sphere overlaps a sphere (broad phase for multi-point bodies like the cage).
  near(p, radius, out = []) {
    out.length = 0;
    for (const c of this.list) { const centre = c.kind === "box" ? c.c : c.mid; if (centre.distanceToSquared(p) <= (c.r + radius) ** 2) out.push(c); }
    return out;
  }

  // Contacts of a small sphere against a pre-filtered candidate list.
  contactsIn(cands, p, radius, out = []) {
    out.length = 0;
    for (const c of cands) {
      const hit = c.kind === "box" ? sphereBox(p, radius, c) : sphereCapsule(p, radius, c);
      if (hit) { hit.mat = c.mat; out.push(hit); }
    }
    return out;
  }

  // Nearest hit distance along a ray (or Infinity). Optional `skipInside` ignores colliders that contain the origin.
  raycast(origin, dir, far = Infinity) {
    let best = far;
    for (const c of this.list) {
      const t = c.kind === "box" ? rayBox(origin, dir, c, best) : rayCapsule(origin, dir, c, best);
      if (t < best) best = t;
    }
    return best;
  }
}

function sphereBox(p, radius, c) {
  _v.copy(p).sub(c.c); if (c.qi) _v.applyQuaternion(c.qi);
  const cx = Math.max(-c.h.x, Math.min(c.h.x, _v.x)), cy = Math.max(-c.h.y, Math.min(c.h.y, _v.y)), cz = Math.max(-c.h.z, Math.min(c.h.z, _v.z));
  _w.set(_v.x - cx, _v.y - cy, _v.z - cz);
  const d2 = _w.lengthSq();
  let n, depth;
  if (d2 > 1e-12) {
    if (d2 >= radius * radius) return null;
    const d = Math.sqrt(d2); n = _w.clone().divideScalar(d); depth = radius - d;
  } else {
    const dx = c.h.x - Math.abs(_v.x), dy = c.h.y - Math.abs(_v.y), dz = c.h.z - Math.abs(_v.z);
    if (dx <= dy && dx <= dz) { n = new THREE.Vector3(Math.sign(_v.x) || 1, 0, 0); depth = dx + radius; }
    else if (dy <= dz) { n = new THREE.Vector3(0, Math.sign(_v.y) || 1, 0); depth = dy + radius; }
    else { n = new THREE.Vector3(0, 0, Math.sign(_v.z) || 1); depth = dz + radius; }
  }
  const point = new THREE.Vector3(cx, cy, cz);
  if (c.q) { n.applyQuaternion(c.q); point.applyQuaternion(c.q); }
  point.add(c.c);
  return { n, depth, point };
}

function sphereCapsule(p, radius, c) {
  const ab = _v.copy(c.b).sub(c.a), L2 = ab.lengthSq();
  const t = L2 < 1e-12 ? 0 : Math.max(0, Math.min(1, _w.copy(p).sub(c.a).dot(ab) / L2));   // a == b → sphere
  const closest = c.a.clone().addScaledVector(ab, t);
  const d = closest.distanceTo(p), lim = radius + c.rad;
  if (d >= lim) return null;
  const n = d > 1e-9 ? p.clone().sub(closest).divideScalar(d) : new THREE.Vector3(0, 1, 0);
  return { n, depth: lim - d, point: closest.addScaledVector(n, c.rad) };
}

function rayBox(o, d, c, far) {
  _o.copy(o).sub(c.c); _d.copy(d);
  if (c.qi) { _o.applyQuaternion(c.qi); _d.applyQuaternion(c.qi); }
  let t0 = 0, t1 = far;
  for (const ax of ["x", "y", "z"]) {
    const h = c.h[ax];
    if (Math.abs(_d[ax]) < 1e-9) { if (_o[ax] < -h || _o[ax] > h) return Infinity; continue; }
    let a = (-h - _o[ax]) / _d[ax], b = (h - _o[ax]) / _d[ax];
    if (a > b) [a, b] = [b, a];
    t0 = Math.max(t0, a); t1 = Math.min(t1, b);
    if (t0 > t1) return Infinity;
  }
  return t0 > 0 ? t0 : Infinity;            // origin inside the box: ignore (camera/drone overlap)
}

function rayCapsule(o, d, c, far) {
  // march-free analytic: closest approach between ray and segment, then refine with sphere test at that segment point
  const u = _v.copy(c.b).sub(c.a), w0 = _w.copy(o).sub(c.a);
  const a = d.dot(d), b = d.dot(u), cc = u.dot(u), dd = d.dot(w0), e = u.dot(w0);
  const den = a * cc - b * b;
  let t = cc < 1e-12 ? 0 : den > 1e-9 ? (a * e - b * dd) / den : e / cc;
  t = Math.max(0, Math.min(1, t)); const s = Math.max(0, (b * t - dd) / a);
  if (s > far) return Infinity;
  const q = c.a.clone().addScaledVector(u, t);
  // ray vs sphere at q
  const m = o.clone().sub(q), B = m.dot(d), C = m.lengthSq() - c.rad * c.rad;
  if (C > 0 && B > 0) return Infinity;
  const disc = B * B - C;
  if (disc < 0) return Infinity;
  const hit = -B - Math.sqrt(disc);
  return hit > 0 && hit < far ? hit : Infinity;
}
