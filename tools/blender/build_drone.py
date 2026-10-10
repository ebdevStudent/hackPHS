"""Build static/assets/drone/ball_drone.glb from the real CAD parts (run headless):
    blender -b --factory-startup --python tools/blender/build_drone.py

Geometry: printed parts are the actual STLs (Thingiverse 408519 cage joints + gimbal hoops, our Quad_Frame), placed with
the transforms from Spherical_Drone_408519/assembly/assembly_quad.json. Motors, props, FC stack, battery, camera and
rods are modelled here. Output nodes (glTF, Y-up, metres, forward = -Z):
    cage, ring_big, ring_small, quad, prop_0..prop_3 (children of quad, origin on the motor axis)
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector

SRC = r"C:\Users\wasim\Downloads\Spherical_Drone_408519"
FILES = os.path.join(SRC, "files")
GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(GAME, "static", "assets", "drone", "ball_drone.glb")
PREVIEW = os.path.join(GAME, "tools", "blender", "drone_preview.png")
data = json.load(open(os.path.join(SRC, "assembly", "assembly_quad.json")))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ---------------- materials ----------------
def mat(name, color, rough, metal=0.0, coat=0.0, coat_rough=0.05, transmission=0.0, emission=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    if transmission: b.inputs["Transmission Weight"].default_value = transmission
    if emission:
        b.inputs["Emission Color"].default_value = (*emission[0], 1); b.inputs["Emission Strength"].default_value = emission[1]
    return m


M = {
    "petg": mat("PETG_blue", (0.012, 0.13, 0.36), 0.38, coat=0.12, coat_rough=0.3),
    "petg_dark": mat("PETG_blue_dark", (0.008, 0.09, 0.27), 0.45, coat=0.1, coat_rough=0.35),
    "carbon": mat("Carbon_rod", (0.012, 0.012, 0.014), 0.3, coat=0.8, coat_rough=0.06),
    "bell": mat("Motor_bell_anodised", (0.55, 0.04, 0.03), 0.28, metal=1.0),
    "stator": mat("Copper_windings", (0.72, 0.36, 0.16), 0.32, metal=1.0),
    "steel": mat("Steel", (0.62, 0.63, 0.65), 0.22, metal=1.0),
    "black_al": mat("Black_aluminium", (0.03, 0.03, 0.035), 0.35, metal=0.9),
    "prop_red": mat("Prop_red_PC", (0.65, 0.04, 0.03), 0.18, coat=0.5),
    "prop_black": mat("Prop_black_PC", (0.02, 0.02, 0.025), 0.2, coat=0.5),
    "pcb": mat("PCB_green", (0.02, 0.16, 0.06), 0.45, coat=0.3),
    "chip": mat("Chip_black", (0.015, 0.015, 0.015), 0.4),
    "gold": mat("Gold_pads", (0.9, 0.65, 0.25), 0.25, metal=1.0),
    "battery": mat("Battery_wrap", (0.85, 0.62, 0.05), 0.4, coat=0.6, coat_rough=0.1),
    "battery_dark": mat("Battery_wrap_black", (0.02, 0.02, 0.02), 0.35, coat=0.6),
    "strap": mat("Velcro_strap", (0.03, 0.03, 0.03), 0.9),
    "lens": mat("Camera_lens_glass", (0.01, 0.02, 0.04), 0.03, coat=1.0),
    "cam": mat("Camera_body", (0.04, 0.04, 0.045), 0.5),
    "led_w": mat("LED_white", (1, 1, 1), 0.3, emission=((1, 0.97, 0.9), 6)),
    "led_r": mat("LED_red", (1, 0.05, 0.03), 0.3, emission=((1, 0.05, 0.02), 6)),
    "wire_r": mat("Wire_red", (0.6, 0.02, 0.02), 0.5),
    "wire_k": mat("Wire_black", (0.02, 0.02, 0.02), 0.5),
}


# ---------------- helpers ----------------
def new_obj(name, me, parent=None, material=None):
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
    if material: me.materials.append(material)
    if parent: o.parent = parent
    return o


def empty(name, parent=None):
    o = bpy.data.objects.new(name, None); scene.collection.objects.link(o)
    if parent: o.parent = parent
    return o


def import_stl(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    return [o for o in bpy.data.objects if o not in before][0]


stl_cache = {}


def stl_mesh(fname, body=None):
    """Mesh datablock of an STL in its own (mm) coordinates; body='top'/'bottom' picks one junction plate."""
    key = (fname, body)
    if key in stl_cache: return stl_cache[key]
    o = import_stl(os.path.join(FILES, fname))
    me = o.data
    if body:
        bm = bmesh.new(); bm.from_mesh(me)
        islands, seen = [], set()
        for f in bm.faces:
            if f.index in seen: continue
            stack, isl = [f], []
            seen.add(f.index)
            while stack:
                g = stack.pop(); isl.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen: seen.add(h.index); stack.append(h)
            islands.append(isl)
        keep = [isl for isl in islands if (max(v.co.z for f in isl for v in f.verts) > -17) == (body == "top")][0]
        drop = [f for isl in islands if isl is not keep for f in isl]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.to_mesh(me); bm.free()
    bpy.data.objects.remove(o)
    stl_cache[key] = me
    return me


def merged(name, parts, material, parent):
    """Join (mesh, 4x4 matrix in mm) parts into one object in metres, smooth-shaded by angle."""
    bm = bmesh.new()
    for me, M4 in parts:
        tmp = bmesh.new(); tmp.from_mesh(me)
        bmesh.ops.transform(tmp, matrix=Matrix.Scale(0.001, 4) @ Matrix(M4), verts=tmp.verts)
        tmp_me = bpy.data.meshes.new("tmp"); tmp.to_mesh(tmp_me); tmp.free()
        bm.from_mesh(tmp_me); bpy.data.meshes.remove(tmp_me)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = new_obj(name, me, parent, material)
    for p in me.polygons: p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(35))
    return o


def cylinder(name, r, h, seg=24, parent=None, material=None, loc=(0, 0, 0), rot=None, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = new_obj(name, me, parent, material); o.location = loc
    if rot: o.rotation_euler = rot
    for p in me.polygons: p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(40))
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = 2; b.limit_method = "ANGLE"
    return o


def box(name, size, parent=None, material=None, loc=(0, 0, 0), bevel=0.0, rot=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = new_obj(name, me, parent, material); o.location = loc
    if rot: o.rotation_euler = rot
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = 3; b.limit_method = "ANGLE"
        for p in me.polygons: p.use_smooth = True
    return o


# ---------------- printed parts from the CAD assembly ----------------
root = empty("ball_drone")
cage, ring_big, ring_small, quad = (empty(n, root) for n in ("cage", "ring_big", "ring_small", "quad"))
groups = {"Cage joints": cage, "Big hoop": ring_big, "Small hoop": ring_small, "Quad frame & chassis": quad}
buckets, rods = {}, []
for it in data["items"]:
    g = it["group"]
    if g == "Carbon rods (3 mm, not printed)":
        rods.append(it); continue
    if g not in groups: continue
    if it.get("path"):
        me = stl_cache.get(it["path"]) or import_stl(it["path"]).data
        stl_cache[it["path"]] = me
    else:
        me = stl_mesh(it["file"], it.get("body"))
    material = M["petg_dark"] if "junction" in it["name"] else M["petg"]
    buckets.setdefault((g, material.name), []).append((me, it["M"]))
for (g, mname), parts in buckets.items():
    merged(g.split()[0].lower() + "_" + mname, parts, bpy.data.materials[mname], groups[g])
for o in list(bpy.data.objects):          # drop the raw STL import objects that are still linked
    if o.type == "MESH" and o.parent is None and o.name not in ("ball_drone",): bpy.data.objects.remove(o)

# carbon rods: one merged mesh of 8-sided cylinders
bm = bmesh.new()
for it in rods:
    r, h = it["dims"]["r"], it["dims"]["h"]
    tmp = bmesh.new(); bmesh.ops.create_cone(tmp, cap_ends=True, segments=10, radius1=r, radius2=r, depth=h)
    bmesh.ops.translate(tmp, vec=Vector((0, 0, h / 2)), verts=tmp.verts)
    bmesh.ops.transform(tmp, matrix=Matrix.Scale(0.001, 4) @ Matrix(it["M"]), verts=tmp.verts)
    tm = bpy.data.meshes.new("t"); tmp.to_mesh(tm); tmp.free(); bm.from_mesh(tm); bpy.data.meshes.remove(tm)
me = bpy.data.meshes.new("cage_rods"); bm.to_mesh(me); bm.free()
o = new_obj("cage_rods", me, cage, M["carbon"])
for p in me.polygons: p.use_smooth = True
me.set_sharp_from_angle(angle=math.radians(50))

# ---------------- modelled electronics (metres, CAD frame: X right, Y forward, Z up) ----------------
R_MOTOR, TF = 0.076, 0.005
for k in range(4):
    a = math.radians(45 + 90 * k); mx, my = R_MOTOR * math.cos(a), R_MOTOR * math.sin(a)
    front = my > 0
    base = cylinder(f"motor{k}_base", 0.0095, 0.004, 32, quad, M["black_al"], (mx, my, TF / 2 + 0.002), bevel=0.0006)
    stator = cylinder(f"motor{k}_stator", 0.0078, 0.006, 24, quad, M["stator"], (mx, my, TF / 2 + 0.007))
    bell = cylinder(f"motor{k}_bell", 0.0102, 0.0095, 40, quad, M["bell"], (mx, my, TF / 2 + 0.0115), bevel=0.0008)
    # cooling windows in the bell skirt
    for j in range(6):
        b = math.radians(j * 60)
        cut = box(f"m{k}_cut{j}", (0.006, 0.006, 0.005), None, None, (mx + 0.0102 * math.cos(b), my + 0.0102 * math.sin(b), TF / 2 + 0.0095))
        cut.rotation_euler = (0, 0, b)
        mod = bell.modifiers.new(f"win{j}", "BOOLEAN"); mod.object = cut; mod.operation = "DIFFERENCE"; mod.solver = "EXACT"
        cut.hide_render = True; cut.hide_viewport = True
        cut.parent = None
    cylinder(f"motor{k}_shaft", 0.0025, 0.012, 16, quad, M["steel"], (mx, my, TF / 2 + 0.019))
    # 4" tri-blade prop: origin on the motor axis so the game can spin it
    prop = empty(f"prop_{k}", quad); prop.location = (mx, my, TF / 2 + 0.0215)
    cylinder(f"prop{k}_hub", 0.0055, 0.0055, 24, prop, M["prop_red"] if front else M["prop_black"], (0, 0, 0), bevel=0.0007)
    cylinder(f"prop{k}_nut", 0.0032, 0.004, 6, prop, M["steel"], (0, 0, 0.0045))
    spin = 1 if k % 2 == 0 else -1
    for bl in range(3):
        bmb = bmesh.new()
        n_sec, L = 10, 0.0508
        rows = []
        for i in range(n_sec + 1):
            t = i / n_sec; rr = 0.005 + (L - 0.005) * t
            chord = 0.0105 * (1 - 0.45 * t) * (0.75 + 0.25 * math.sin(math.pi * min(1, t * 1.6)))
            pitch = math.radians(26 - 14 * t) * spin
            ring = []
            for s in (-0.5, -0.15, 0.25, 0.5):
                x = s * chord; z = 0.0011 * (1 - (2 * s) ** 2)         # cambered thin section
                ring.append(Vector((rr, x * math.cos(pitch) - z * math.sin(pitch), x * math.sin(pitch) + z * math.cos(pitch))))
            rows.append([bmb.verts.new(v) for v in ring])
        for i in range(n_sec):
            for j in range(3):
                bmb.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
        bmesh.ops.solidify(bmb, geom=bmb.faces[:], thickness=0.0008)
        meb = bpy.data.meshes.new(f"prop{k}_blade{bl}"); bmb.to_mesh(meb); bmb.free()
        blade = new_obj(f"prop{k}_blade{bl}", meb, prop, M["prop_red"] if front else M["prop_black"])
        blade.rotation_euler = (0, 0, math.radians(120 * bl))
        for p in meb.polygons: p.use_smooth = True
    # arm LED + motor wires
    cylinder(f"led{k}", 0.0022, 0.002, 12, quad, M["led_w"] if front else M["led_r"], (mx * 1.18, my * 1.18, -TF / 2 - 0.001))
    for w, (dx, mt) in enumerate(((-0.0015, M["wire_r"]), (0.0015, M["wire_k"]))):
        wire = cylinder(f"wire{k}{w}", 0.0007, R_MOTOR - 0.03, 8, quad, mt, (mx * 0.55 + dx * math.sin(a), my * 0.55 - dx * math.cos(a), TF / 2 + 0.0009))
        wire.rotation_euler = (0, math.pi / 2, a)

# flight controller + ESC stack (30.5 mm)
for z, nm in ((0.0045, "esc"), (0.0115, "fc")):
    box(f"{nm}_pcb", (0.036, 0.036, 0.0016), quad, M["pcb"], (0, 0, TF / 2 + z), bevel=0.0004)
    box(f"{nm}_chip", (0.010, 0.010, 0.0014), quad, M["chip"], (0.004, -0.003, TF / 2 + z + 0.0015))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cylinder(f"{nm}_pad{sx}{sy}", 0.0022, 0.0004, 16, quad, M["gold"], (sx * 0.01525, sy * 0.01525, TF / 2 + z + 0.0009))
for sx in (-1, 1):
    for sy in (-1, 1):
        cylinder(f"standoff{sx}{sy}", 0.0018, 0.014, 6, quad, M["black_al"], (sx * 0.01525, sy * 0.01525, TF / 2 + 0.007))
box("esc_caps", (0.008, 0.012, 0.008), quad, M["chip"], (-0.011, 0.0, TF / 2 + 0.0085), bevel=0.001)
# FPV camera on the front of the body
box("cam_body", (0.0142, 0.012, 0.0142), quad, M["cam"], (0, 0.026, TF / 2 + 0.0085), bevel=0.0012)
lens = cylinder("cam_lens", 0.0045, 0.006, 32, quad, M["black_al"], (0, 0.0345, TF / 2 + 0.0085), rot=(math.pi / 2, 0, 0), bevel=0.0005)
cylinder("cam_glass", 0.0033, 0.001, 32, quad, M["lens"], (0, 0.0378, TF / 2 + 0.0085), rot=(math.pi / 2, 0, 0))
# 4S 850 mAh pack strapped underneath
box("battery", (0.057, 0.031, 0.027), quad, M["battery"], (0, 0, -TF / 2 - 0.0135), bevel=0.002)
box("battery_label", (0.0575, 0.0315, 0.009), quad, M["battery_dark"], (0, 0, -TF / 2 - 0.0135), bevel=0.0015)
for sx in (-1, 1):
    box(f"strap{sx}", (0.01, 0.0325, 0.0285), quad, M["strap"], (sx * 0.018, 0, -TF / 2 - 0.0135))
cylinder("xt30_lead", 0.0015, 0.03, 8, quad, M["wire_r"], (0.03, 0.006, -0.008), rot=(0, math.pi / 2, 0))

# apply modifiers so the exporter sees final geometry
for o in list(scene.objects):
    if o.type == "MESH" and o.modifiers and o.visible_get():
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        for m in list(o.modifiers):
            try: bpy.ops.object.modifier_apply(modifier=m.name)
            except RuntimeError: pass
        o.select_set(False)
for o in list(scene.objects):
    if o.name.startswith("m") and "_cut" in o.name: bpy.data.objects.remove(o)

# ---------------- preview render (Eevee) ----------------
if "--preview" in sys.argv:
    world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.38, 0.42, 1); world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam)
    cam.location = (0.42, -0.5, 0.3); cam.rotation_euler = (math.radians(66), 0, math.radians(40)); scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4; sun.rotation_euler = (0.7, 0.2, 0.6); scene.collection.objects.link(sun)
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 900
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)

# ---------------- export ----------------
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True, export_apply=True, use_selection=False,
                          export_materials="EXPORT", export_cameras=False, export_lights=False)
tris = sum(len(o.data.polygons) for o in scene.objects if o.type == "MESH")
print("BUILD_OK", OUT, "objects", len([o for o in scene.objects if o.type == "MESH"]), "faces", tris)
