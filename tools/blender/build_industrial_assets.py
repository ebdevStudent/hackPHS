"""Build instancing-friendly pallet loads for the industrial level (run headless):
    blender -b --factory-startup --python tools/blender/build_industrial_assets.py

Real Poly Haven models (CC0) are decimated (UVs + photo textures kept) and composed onto a modelled Euro pallet
(1.2 x 0.8 x 0.144 m, planks PBR). Each output GLB is one mesh per material so the game can instance it cheaply.
Outputs in static/assets/blender/: pallet_cartons.glb, pallet_cartons_low.glb, pallet_drums.glb, pallet_crate.glb,
pallet_containers.glb, pallet_empty_stack.glb, carton.glb
Blender axes: X = pallet width (0.8), Y = pallet length (1.2), Z = up.  (glTF: Y-up, Blender Y -> glTF -Z)
"""
import bpy, bmesh, os, math, random
from mathutils import Vector, Matrix

GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MOD = os.path.join(GAME, "static", "assets", "models")
TEX = os.path.join(GAME, "static", "assets", "textures")
OUT = os.path.join(GAME, "static", "assets", "blender")
os.makedirs(OUT, exist_ok=True)
random.seed(7)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def pbr_material(name, tex, tile=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    def img(fn, color):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(os.path.join(TEX, tex, fn), check_existing=True)
        if not color: n.image.colorspace_settings.name = "Non-Color"
        return n
    d = img("diff.jpg", True); nt.links.new(d.outputs["Color"], b.inputs["Base Color"])
    a = img("arm.jpg", False); sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(a.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"]); nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nn = img("nor.jpg", False); nt.links.new(nn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


def metre_box(bm, size, center, tile):
    """Add a box to bm with UVs in metres / tile on every face (dominant-axis planar projection)."""
    geom = bmesh.ops.create_cube(bm, size=1.0)
    vs = geom["verts"]
    bmesh.ops.scale(bm, vec=Vector(size), verts=vs); bmesh.ops.translate(bm, vec=Vector(center), verts=vs)
    uv = bm.loops.layers.uv.verify()
    faces = {f for v in vs for f in v.link_faces}
    for f in faces:
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        u, v = [(1, 2), (0, 2), (0, 1)][ax]
        for l in f.loops:
            l[uv].uv = (l.vert.co[u] / tile, l.vert.co[v] / tile)


def pallet_object(name="pallet", z0=0.0):
    bm = bmesh.new()
    T = 1.6
    for i in range(5):                                   # top deck boards (along X, the 0.8 width)
        w = 0.145 if i in (0, 4) else 0.1
        metre_box(bm, (0.8, w, 0.022), (0, -0.6 + w / 2 + i * (1.2 - w) / 4, z0 + 0.133), T)
    for y in (-0.53, 0, 0.53):                            # blocks
        for x in (-0.35, 0, 0.35):
            metre_box(bm, (0.1, 0.145, 0.078), (x, y, z0 + 0.083), T)
    for x in (-0.35, 0, 0.35):                            # stringer boards
        metre_box(bm, (0.1, 1.2, 0.022), (x, 0, z0 + 0.033), T)
    for y in (-0.53, 0, 0.53):                            # bottom boards
        metre_box(bm, (0.8, 0.145, 0.022), (0, y, z0 + 0.011), T)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(bpy.data.materials.get("pallet_planks") or pbr_material("pallet_planks", "old_planks_02"))
    return o


def import_decimated(name, ratio):
    """Import a Poly Haven glTF, join it into one mesh with transforms applied, decimate. Returns the object."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MOD, name, f"{name}_1k.gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    others = [o.name for o in new if o.type != "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1: bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    for n in others:
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])
    if ratio < 1:
        d = obj.modifiers.new("dec", "DECIMATE"); d.ratio = ratio; d.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=d.name)
    obj.name = name
    return obj


def bbox(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs))), Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))


def place_copy(src, loc_min_corner_xyz, rot_z=0.0):
    """Linked copy of src placed so its bbox-min corner (after rotation) lands at loc."""
    o = src.copy(); o.hide_render = False; bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (0, 0, rot_z); bpy.context.view_layer.update()
    lo, hi = bbox(o)
    o.location += Vector(loc_min_corner_xyz) - lo
    return o


def finish(objs, fname):
    """Join objects (make single user first), set origin at pallet base centre, export GLB."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = fname
    for p in o.data.polygons: p.use_smooth = True
    o.data.set_sharp_from_angle(angle=math.radians(40))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, fname + ".glb"), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_image_format="JPEG", export_jpeg_quality=85)
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    print(f"ASSET {fname}: {tris} tris")
    bpy.data.objects.remove(o)


def build():
    reset()
    carton = import_decimated("cardboard_box_01", 0.012)
    drum = import_decimated("Barrel_02", 0.3)
    crate = import_decimated("wooden_crate_02", 0.22)
    cont = import_decimated("industrial_pastic_container", 0.18)
    for t in (carton, drum, crate, cont): t.hide_set(True); t.hide_render = True
    clo, chi = bbox(carton); cs = chi - clo                  # carton ~0.39 x 0.52 x 0.34

    # cartons: 2 across (X) x 2 along (Y) x layers, with small random offsets / 180° flips
    def carton_stack(layers):
        objs = [pallet_object()]
        for k in range(layers):
            for i in range(2):
                for j in range(2):
                    x = -0.4 + i * (0.8 - cs.x) + random.uniform(-0.01, 0.01)
                    y = -0.6 + 0.04 + j * (1.12 - cs.y) + random.uniform(-0.01, 0.01)
                    objs.append(place_copy(carton, (x, y, 0.144 + k * cs.z), math.pi * random.randint(0, 1)))
        return objs
    finish(carton_stack(3), "pallet_cartons")
    finish(carton_stack(2), "pallet_cartons_low")
    finish([place_copy(carton, (-cs.x / 2, -cs.y / 2, 0))], "carton")

    dlo, dhi = bbox(drum); ds = dhi - dlo
    objs = [pallet_object()]
    for j in range(2):
        objs.append(place_copy(drum, (-ds.x / 2, -0.58 + j * (1.16 - ds.y), 0.144), random.uniform(0, 6)))
    finish(objs, "pallet_drums")

    rlo, rhi = bbox(crate); rs = rhi - rlo
    finish([pallet_object(), place_copy(crate, (-rs.x / 2, -rs.y / 2, 0.144))], "pallet_crate")

    olo, ohi = bbox(cont); os_ = ohi - olo
    objs = [pallet_object()]
    for i in range(2):
        for j in range(2):
            objs.append(place_copy(cont, (-0.4 - 0.03 + i * (0.86 - os_.x), -0.6 + j * (1.2 - os_.y), 0.144), 0))
    finish(objs, "pallet_containers")

    stack = [pallet_object(f"p{i}", z0=i * 0.144) for i in range(7)]
    for i, p in enumerate(stack): p.rotation_euler = (0, 0, random.uniform(-0.04, 0.04))
    finish(stack, "pallet_empty_stack")


build()
print("BUILD_OK")
