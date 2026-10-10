"""Rescue-training mannequin (~1.75 m, 70 kg class) in three poses, exported to static/assets/blender/dummy_<pose>.glb.
    blender -b --factory-startup --python tools/blender/build_dummy.py [-- --preview]

Body = a joint graph with a Skin modifier + Subdivision (smooth organic limbs), separate head/hands/boots, hi-vis
reflective bands on the limbs and a black chest/shoulder harness, like real SAR training dummies (e.g. Ruth Lee style).
Each GLB: origin at the floor below the pelvis, Y-up, metres; the body's head points to -Z for the lying poses.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix, Euler

GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(GAME, "static", "assets", "blender")
os.makedirs(OUT, exist_ok=True)


def mat(name, color, rough, sheen=0.0, metal=0.0, coat=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Coat Weight"].default_value = coat
    return m


def fabric_material():
    """Hi-vis orange canvas: generated weave colour + normal map (exported into the GLB)."""
    import numpy as np
    if bpy.data.materials.get("Dummy_canvas_orange"): return bpy.data.materials["Dummy_canvas_orange"]
    N = 512; rng = np.random.default_rng(7)
    u, v = np.meshgrid(np.arange(N), np.arange(N))
    weave = np.sin(u * 2 * np.pi / 6) * np.sin(v * 2 * np.pi / 6)
    dirt = np.zeros((N, N))
    for _ in range(18):
        fx, fy, ph = rng.uniform(1, 6, 2).tolist() + [rng.uniform(0, 6.28)]
        dirt += np.sin(u / N * 2 * np.pi * fx + ph) * np.sin(v / N * 2 * np.pi * fy + ph * 1.7)
    dirt = np.clip((dirt - dirt.min()) / (dirt.max() - dirt.min()), 0, 1) ** 2.2
    base = np.array([0.80, 0.20, 0.025])
    col = base[None, None, :] * (0.9 + 0.08 * weave)[..., None] * (1 - 0.35 * dirt)[..., None] + (0.05 * dirt)[..., None] * np.array([0.35, 0.3, 0.25])
    h = 0.5 + 0.5 * weave
    gx, gy = np.gradient(h)
    nrm = np.stack([-gx * 0.9, -gy * 0.9, np.ones_like(h)], -1); nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    def img(name, rgb, srgb):
        im = bpy.data.images.new(name, N, N, alpha=False, float_buffer=False)
        px = np.concatenate([rgb, np.ones((N, N, 1))], -1).astype(np.float32)
        im.pixels[:] = px.ravel().tolist()
        path = os.path.join(OUT, "textures", name + ".png"); os.makedirs(os.path.dirname(path), exist_ok=True)
        im.filepath_raw = path; im.file_format = "PNG"; im.save()
        bpy.data.images.remove(im)
        im = bpy.data.images.load(path); im.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
        return im
    cimg = img("canvas_col", np.clip(col, 0, 1) ** (1 / 1.0), True)
    nimg = img("canvas_nor", nrm * 0.5 + 0.5, False)
    m = bpy.data.materials.new("Dummy_canvas_orange"); m.use_nodes = True
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = cimg
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = nimg
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.8
    nt.links.new(tc.outputs["Color"], b.inputs["Base Color"]); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.9; b.inputs["Sheen Weight"].default_value = 0.35
    return m


# ---------------- skeleton: (name, parent, length, radius at joint (x, y)) ----------------
BONES = [
    ("pelvis", None, 0.0, (0.165, 0.115)),
    ("spine", "pelvis", 0.17, (0.145, 0.105)),
    ("chest", "spine", 0.18, (0.175, 0.12)),
    ("neck", "chest", 0.12, (0.055, 0.055)),
    ("l_clav", "chest", 0.17, (0.075, 0.07)), ("r_clav", "chest", 0.17, (0.075, 0.07)),
    ("l_uarm", "l_clav", 0.29, (0.05, 0.05)), ("r_uarm", "r_clav", 0.29, (0.05, 0.05)),
    ("l_farm", "l_uarm", 0.26, (0.038, 0.036)), ("r_farm", "r_uarm", 0.26, (0.038, 0.036)),
    ("l_hip", "pelvis", 0.105, (0.10, 0.10)), ("r_hip", "pelvis", 0.105, (0.10, 0.10)),
    ("l_thigh", "l_hip", 0.44, (0.062, 0.062)), ("r_thigh", "r_hip", 0.44, (0.062, 0.062)),
    ("l_shin", "l_thigh", 0.42, (0.046, 0.046)), ("r_shin", "r_thigh", 0.42, (0.046, 0.046)),
]
# body frame: x = body's left, y = body's front, z = up (standing)
STAND = {
    "spine": (0, 0.02, 1), "chest": (0, -0.03, 1), "neck": (0, 0.12, 1),
    "l_clav": (1, -0.05, 0.12), "r_clav": (-1, -0.05, 0.12),
    "l_uarm": (0.22, 0, -1), "r_uarm": (-0.22, 0, -1), "l_farm": (0.05, 0.12, -1), "r_farm": (-0.05, 0.12, -1),
    "l_hip": (1, 0, -0.15), "r_hip": (-1, 0, -0.15),
    "l_thigh": (0.06, 0, -1), "r_thigh": (-0.06, 0, -1), "l_shin": (0, -0.03, -1), "r_shin": (0, -0.03, -1),
}
POSES = {
    # on its back, arms loosely out, one knee raised a little, head rolled to the side
    "supine": dict(STAND, **{"l_uarm": (0.75, 0.05, -0.65), "r_uarm": (-0.55, 0.1, -0.85), "l_farm": (0.5, 0.45, -0.75), "r_farm": (-0.2, 0.5, -0.85),
                             "l_thigh": (0.12, 0.35, -1), "l_shin": (0.05, -0.25, -1), "r_thigh": (-0.1, 0, -1), "neck": (0.25, 0.1, 1)}),
    # on its side, top leg drawn up, arms in front (recovery-like)
    "side": dict(STAND, **{"l_uarm": (0.15, 0.8, -0.55), "r_uarm": (-0.1, 0.9, -0.4), "l_farm": (0.0, 1, 0.1), "r_farm": (0.0, 1, 0.25),
                           "l_thigh": (0.05, 0.9, -0.6), "l_shin": (0, -0.1, -1), "r_thigh": (-0.02, 0.35, -1), "r_shin": (0, -0.4, -1),
                           "spine": (0, 0.15, 1), "neck": (0, 0.35, 1)}),
    # sitting on the floor slumped against a wall, knees up, head dropped forward
    "sitting": dict(STAND, **{"spine": (0, -0.28, 1), "chest": (0, -0.1, 1), "neck": (0, 0.55, 1),
                              "l_thigh": (0.15, 1, 0.8), "r_thigh": (-0.25, 1, 0.12), "l_shin": (0.05, 0.2, -1), "r_shin": (-0.1, 0.9, -0.35),
                              "l_uarm": (0.3, 0.15, -1), "r_uarm": (-0.35, 0.05, -1), "l_farm": (0.15, 0.9, -0.3), "r_farm": (-0.25, 0.6, -0.6)}),
}
PELVIS_STAND = Vector((0, 0, 0.98))


def joints(pose):
    d = POSES[pose]; pos = {"pelvis": PELVIS_STAND.copy()}
    for name, parent, length, _ in BONES[1:]:
        pos[name] = pos[parent] + Vector(d[name]).normalized() * length
    return pos


def build(pose):
    for o in list(bpy.context.scene.objects): bpy.data.objects.remove(o)
    P = joints(pose)
    radii = {n: r for n, _, _, r in BONES}
    # ---- skinned body ----
    bm = bmesh.new(); vmap = {}
    for name, parent, _, _ in BONES:
        vmap[name] = bm.verts.new(P[name])
    for name, parent, _, _ in BONES:
        if parent: bm.edges.new((vmap[parent], vmap[name]))
    # extra mid-bone verts for limb shape (calf/forearm/thigh bulge)
    me = bpy.data.meshes.new("body"); bm.to_mesh(me); bm.free()
    body = bpy.data.objects.new("body", me); bpy.context.scene.collection.objects.link(body)
    sk = body.modifiers.new("skin", "SKIN"); sk.use_smooth_shade = True
    body.data.skin_vertices[0].data[0].use_root = True
    for i, (name, *_rest) in enumerate(BONES):
        body.data.skin_vertices[0].data[i].radius = radii[name]
    # subdivide limbs so the skin can taper realistically: insert midpoints with blended radii
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.subdivide(number_cuts=2); bpy.ops.object.mode_set(mode="OBJECT")
    # radii after subdivide: interpolate along each edge chain by nearest original joints
    jp = [(P[n], Vector(radii[n])) for n, *_ in BONES]
    bulge = {"l_thigh": 1.15, "r_thigh": 1.15, "l_uarm": 1.08, "r_uarm": 1.08, "l_shin": 1.12, "r_shin": 1.12}
    for i, v in enumerate(body.data.vertices):
        ds = sorted(((v.co - p).length, r) for p, r in jp)
        (d0, r0), (d1, r1) = ds[0], ds[1]
        w = d1 / max(1e-6, d0 + d1)
        body.data.skin_vertices[0].data[i].radius = tuple(r0 * w + r1 * (1 - w))
    sub = body.modifiers.new("sub", "SUBSURF"); sub.levels = 2; sub.render_levels = 2
    suit = fabric_material()
    body.data.materials.append(suit)
    bpy.ops.object.select_all(action="DESELECT"); body.select_set(True)
    bpy.ops.object.convert(target="MESH")
    parts = [body]

    def prim(kind, loc, size, rotq=None, material=suit, name="part"):
        if kind == "sphere": bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=loc)
        elif kind == "cyl": bpy.ops.mesh.primitive_cylinder_add(vertices=24, location=loc)
        elif kind == "cube": bpy.ops.mesh.primitive_cube_add(location=loc)
        o = bpy.context.active_object; o.name = name; o.scale = size
        if rotq: o.rotation_mode = "QUATERNION"; o.rotation_quaternion = rotq
        o.data.materials.append(material)
        bpy.ops.object.shade_smooth(); parts.append(o); return o

    def along(a, b):
        return Vector((0, 0, 1)).rotation_difference((b - a).normalized())

    # ---- head (slightly egg shaped, canvas hood seam) ----
    head_dir = (P["neck"] - P["chest"]).normalized()
    hc = P["neck"] + head_dir * 0.11
    h = prim("sphere", hc, (0.088, 0.1, 0.112), along(P["chest"], P["neck"]), name="head")
    b = h.modifiers.new("sub", "SUBSURF"); b.levels = 1
    # ---- mitten hands + boots ----
    dark = mat("Dummy_canvas_dark", (0.06, 0.06, 0.065), 0.9, sheen=0.3)
    for s in ("l", "r"):
        a, e = P[f"{s}_uarm"], P[f"{s}_farm"]
        hd = (e - a).normalized()
        prim("sphere", e + hd * 0.075, (0.045, 0.028, 0.085), along(a, e), dark, name=f"{s}_hand")
        k, an = P[f"{s}_thigh"], P[f"{s}_shin"]
        legd = (an - k).normalized()
        # boot: points along the body's "front" relative to the shin
        fwd = Vector(POSES[pose].get("_fwd", (0, 1, 0)))
        toe_dir = (fwd - legd * fwd.dot(legd)).normalized()
        if toe_dir.length < 0.1: toe_dir = Vector((0, 1, 0))
        boot_c = an + legd * 0.045 + toe_dir * 0.07
        prim("sphere", boot_c, (0.052, 0.125, 0.058), Vector((0, 1, 0)).rotation_difference(toe_dir), dark, name=f"{s}_boot")
    # ---- hi-vis reflective bands (forearms, shins) ----
    refl = mat("Retroreflective_band", (0.75, 0.76, 0.74), 0.25, metal=0.6)
    for s in ("l", "r"):
        for jA, jB, t, rr in ((f"{s}_uarm", f"{s}_farm", 0.55, 0.043), (f"{s}_thigh", f"{s}_shin", 0.7, 0.052)):
            a, e = P[jA], P[jB]
            prim("cyl", a.lerp(e, t), (rr, rr, 0.022), along(a, e), refl, name="band")
    # ---- harness: chest strap + two shoulder straps + lifting loop ----
    strap = mat("Harness_webbing", (0.02, 0.02, 0.02), 0.7)
    ch = P["spine"].lerp(P["chest"], 0.55)
    prim("cyl", ch, (0.188, 0.135, 0.03), along(P["spine"], P["chest"]), strap, name="chest_strap")
    prim("cyl", P["pelvis"].lerp(P["spine"], 0.45), (0.172, 0.122, 0.028), along(P["pelvis"], P["spine"]), strap, name="belt")
    buckle = mat("Buckle_steel", (0.6, 0.6, 0.62), 0.3, metal=1.0)
    fwd = (P["spine"] - P["pelvis"]).cross(P["l_hip"] - P["r_hip"]).normalized()
    prim("cube", P["pelvis"].lerp(P["spine"], 0.45) - fwd * 0.125, (0.03, 0.006, 0.022), along(P["pelvis"], P["spine"]), buckle, name="buckle")

    # ---- join, orient into the pose's resting position, drop to the floor ----
    for o in parts:
        for m in list(o.modifiers):
            bpy.context.view_layer.objects.active = o
            try: bpy.ops.object.modifier_apply(modifier=m.name)
            except RuntimeError: pass
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    dummy = bpy.context.active_object; dummy.name = f"dummy_{pose}"
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.01, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    uvl = dummy.data.uv_layers.active.data
    for d in uvl: d.uv = d.uv * 5.0                          # ~6 mm weave on a 512 px tile
    if pose == "supine":   R = Euler((math.radians(90), 0, 0)).to_matrix().to_4x4()           # on its back: front -> +Z, head -> -Y
    elif pose == "side":   R = Euler((0, math.radians(90), 0)).to_matrix().to_4x4() @ Euler((math.radians(90), 0, 0)).to_matrix().to_4x4()
    else:                  R = Matrix.Identity(4)
    dummy.data.transform(R)
    dummy.data.update()
    zs = [v.co.z for v in dummy.data.vertices]; xs = [v.co.x for v in dummy.data.vertices]; ys = [v.co.y for v in dummy.data.vertices]
    dummy.data.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs) + 0.002)))
    for p in dummy.data.polygons: p.use_smooth = True
    return dummy


def export(pose, obj):
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
    path = os.path.join(OUT, f"dummy_{pose}.glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, use_selection=True, export_apply=True)
    dims = obj.dimensions
    print(f"DUMMY {pose}: {path}  dims x{dims.x:.2f} y{dims.y:.2f} z{dims.z:.2f}  faces {len(obj.data.polygons)}")


def preview(objs, path):
    scene = bpy.context.scene
    w = bpy.data.worlds.new("w"); scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.4, 0.42, 0.45, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    floor = bpy.context.active_object; floor.data.materials.append(mat("floor", (0.35, 0.34, 0.32), 0.9))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam)
    cam.location = (1.0, 3.6, 2.1); cam.rotation_euler = (math.radians(62), 0, math.radians(172)); scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 3.5; sun.rotation_euler = (0.8, 0.3, 0.5); scene.collection.objects.link(sun)
    eng = [e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in eng else "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1300, 800
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    built = []
    for i, pose in enumerate(("supine", "side", "sitting")):
        o = build(pose); export(pose, o)
        # keep a copy for the preview, laid side by side
        c = o.copy(); c.data = o.data.copy(); c.location = (-1.6 + i * 1.6, 0, 0); built.append(c)
    if "--preview" in sys.argv:
        for o in list(bpy.context.scene.objects): bpy.data.objects.remove(o)
        for c in built: bpy.context.scene.collection.objects.link(c)
        preview(built, os.path.join(GAME, "tools", "blender", "dummy_preview.png"))
