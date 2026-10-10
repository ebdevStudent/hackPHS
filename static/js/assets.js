// Asset loading: Poly Haven PBR texture sets (diffuse / normal / ARM), glTF models, HDR environments.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RGBELoader } from "three/addons/loaders/RGBELoader.js";

const texLoader = new THREE.TextureLoader();
const gltfLoader = new GLTFLoader();
const texCache = new Map(), modelCache = new Map();
let maxAniso = 8;
export function setAnisotropy(n) { maxAniso = n; }

function tex(url, srgb) {
  if (!texCache.has(url)) {
    const t = texLoader.load(url);
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = maxAniso;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    texCache.set(url, t);
  }
  return texCache.get(url);
}

// PBR material from a Poly Haven texture set. `size` = metres covered by one texture tile (UVs are in metres, see uvBox).
// ARM packs AO (R), roughness (G), metalness (B) — exactly the channels three.js reads from each map.
export function pbr(name, { size = 2, tint = 0xffffff, roughness = 1, metalness = 1, normalScale = 1, envIntensity = 1, side } = {}) {
  const base = `assets/textures/${name}/`;
  const scale = (t) => { const c = t.clone(); c.repeat.set(1 / size, 1 / size); c.needsUpdate = true; return c; };
  const m = new THREE.MeshStandardMaterial({
    map: scale(tex(base + "diff.jpg", true)), normalMap: scale(tex(base + "nor.jpg")),
    aoMap: scale(tex(base + "arm.jpg")), roughnessMap: scale(tex(base + "arm.jpg")), metalnessMap: scale(tex(base + "arm.jpg")),
    color: tint, roughness, metalness, normalScale: new THREE.Vector2(normalScale, normalScale), envMapIntensity: envIntensity,
  });
  if (side) m.side = side;
  return m;
}

// Box geometry whose UVs are in metres on every face (so one material tiles at the same scale on any size of box).
export function uvBox(w, h, d) {
  const g = new THREE.BoxGeometry(w, h, d);
  const uv = g.attributes.uv, n = g.attributes.normal;
  for (let i = 0; i < uv.count; i++) {
    const ax = Math.abs(n.getX(i)), ay = Math.abs(n.getY(i));
    const [su, sv] = ax > 0.5 ? [d, h] : ay > 0.5 ? [w, d] : [w, h];
    uv.setXY(i, uv.getX(i) * su, uv.getY(i) * sv);
  }
  return g;
}

// Cylinder with UVs in metres (u around the circumference, v along the axis).
export function uvCylinder(r, len, seg = 24, rTop = r) {
  const g = new THREE.CylinderGeometry(rTop, r, len, seg, 1, false);
  const uv = g.attributes.uv, circ = 2 * Math.PI * r;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * circ, uv.getY(i) * len);
  return g;
}

export async function model(name) {
  if (!modelCache.has(name)) {
    modelCache.set(name, (async () => {
      const g = await gltfLoader.loadAsync(`assets/models/${name}/${name}_1k.gltf`);
      g.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
      return g.scene;
    })());
  }
  return (await modelCache.get(name)).clone(true);
}

export async function environment(renderer, name) {
  const hdr = await new RGBELoader().loadAsync(`assets/hdri/${name}.hdr`);
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  const pm = new THREE.PMREMGenerator(renderer);
  const env = pm.fromEquirectangular(hdr).texture;
  pm.dispose();
  return { env, background: hdr };
}
