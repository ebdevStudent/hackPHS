"""Build static/assets/drone/ball_drone85.glb — the HackPHS 2026 ball drone as specified in the project document
(BOM p.3, hardware p.10, CAD rules p.6, review p.20-21). Run headless:
    blender -b --factory-startup --python tools/blender/build_drone85.py [-- --preview]

  Cage   : regular icosahedron, circumradius 112.5 mm (225 mm OD to hub centres), two opposite vertices on the pole (Z)
           axis; 12 five-way TPU 95A hubs, 30 x 1.0 mm carbon-fibre rods (edge 118.3 mm).
  Gimbal : P1B two-ring gimbal, printed PETG, 5 mm (radial) x 3 mm section, steel pins + MR52 bearings.
           ring_big  R 87-92 mm, Y-Z plane, pivots on the pole hubs (Z) and carries ring_small on Y.
           ring_small R 80-85 mm, X-Y plane, carries the quad on X.
  Quad   : BetaFPV Meteor85-style 85 mm whoop (87.7 mm wheelbase, PP frame, ducts), F411 AIO 26x26 (ELRS + VTX),
           4x EX1103 11000KV (13.5 x 15.5 mm), Gemfan 2015 2-blade props (50.8 mm, 1.5" pitch), Caddx Ant 14x14 camera
           tilted 15 deg up, 2S LiHV long pack 62.5 x 16.2 x 14.7 mm strapped underneath.

Blender is Z-up with +Y forward; the glTF export (+Y up) turns that into Y-up, forward = -Z.
Output nodes: ball_drone > cage, ring_big, ring_small, quad > prop_0..prop_3 (origin on motor axis), fpv_cam, inspection_light
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector

GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(GAME, "static", "assets", "drone", "ball_drone85.glb")
PREVIEW = os.path.join(GAME, "tools", "blender", "drone85_preview.png")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
mm = 0.001

# ---------------------------------------------------------------- spec
CAGE_R = 112.5 * mm                       # icosahedron circumradius (hub centres)
EDGE = CAGE_R / math.sin(2 * math.pi / 5)  # 118.3 mm
ROD_R = 0.5 * mm                          # 1.0 mm carbon rod
HUB_CORE_R = 3.4 * mm
SOCKET_R = 0.8 * mm                       # 1.6 mm OD socket
SOCKET_LEN = 6.5 * mm                     # hub centre -> socket mouth
ROD_INSERT = 5.0 * mm                     # rod end sits this far from the hub centre (1.5 mm inside the socket)
RING_T = 3.0 * mm                         # ring thickness
BIG_IN, BIG_OUT = 87 * mm, 92 * mm
SMALL_IN, SMALL_OUT = 80 * mm, 85 * mm
WHEELBASE = 87.7 * mm
R_MOTOR = WHEELBASE / 2                   # 43.85 mm, motors on the 45 deg diagonals
PROP_R = 25.4 * mm                        # Gemfan 2015: 2.0" diameter
PROP_PITCH = 1.5 * 25.4 * mm              # 1.5" pitch
DUCT_IN, DUCT_WALL, DUCT_Z0, DUCT_Z1 = 27.0 * mm, 0.8 * mm, -3.0 * mm, 10.0 * mm
MOUNT_Z = -2.25 * mm                      # motor mount plate centre (1.5 mm thick)
MOTOR_BASE_Z = -1.5 * mm
PROP_Z = 8.5 * mm                         # prop plane (inside the duct)
BATT = (16.2 * mm, 62.5 * mm, 14.7 * mm)  # x (width), y (length, along forward), z (height)


# ---------------------------------------------------------------- materials
def mat(name, color, rough, metal=0.0, coat=0.0, coat_rough=0.05, emission=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    if emission:
        b.inputs["Emission Color"].default_value = (*emission[0], 1); b.inputs["Emission Strength"].default_value = emission[1]
    return m


M = {
    "tpu": mat("TPU95A_blue", (0.012, 0.11, 0.55), 0.62, coat=0.05, coat_rough=0.5),
    "carbon": mat("Carbon_rod_1mm", (0.010, 0.010, 0.012), 0.28, coat=0.9, coat_rough=0.05),
    "petg": mat("PETG_ring_graphite", (0.085, 0.09, 0.10), 0.42, coat=0.2, coat_rough=0.3),
    "steel": mat("Steel_pin", (0.66, 0.67, 0.69), 0.22, metal=1.0),
    "bearing_seal": mat("Bearing_seal", (0.03, 0.03, 0.035), 0.5),
    "pp": mat("PP_frame_grey", (0.045, 0.047, 0.052), 0.48, coat=0.2, coat_rough=0.4),
    "pcb": mat("PCB_black", (0.015, 0.02, 0.03), 0.42, coat=0.4, coat_rough=0.2),
    "chip": mat("IC_black", (0.012, 0.012, 0.012), 0.5),
    "gold": mat("Gold_pads", (0.85, 0.62, 0.25), 0.28, metal=1.0),
    "ceramic": mat("Ceramic_antenna", (0.85, 0.84, 0.80), 0.45),
    "smd": mat("SMD_caps", (0.55, 0.42, 0.25), 0.5),
    "bell": mat("Motor_bell_black", (0.025, 0.025, 0.028), 0.3, metal=0.9),
    "bell_cap": mat("Motor_cap_alu", (0.55, 0.56, 0.58), 0.3, metal=1.0),
    "stator": mat("Copper_windings", (0.70, 0.35, 0.15), 0.32, metal=1.0),
    "prop_blue": mat("PC_prop_blue", (0.02, 0.18, 0.72), 0.16, coat=0.6, coat_rough=0.05),
    "prop_grey": mat("PC_prop_grey", (0.30, 0.31, 0.33), 0.18, coat=0.6, coat_rough=0.05),
    "battery": mat("LiHV_wrap", (0.035, 0.035, 0.04), 0.35, coat=0.7, coat_rough=0.08),
    "label": mat("LiHV_label", (0.75, 0.55, 0.06), 0.35, coat=0.5),
    "strap": mat("Velcro_strap", (0.02, 0.02, 0.02), 0.95),
    "xt30": mat("XT30_nylon", (0.88, 0.66, 0.06), 0.45),
    "cam": mat("Caddx_body", (0.03, 0.03, 0.034), 0.45),
    "lens": mat("Lens_glass", (0.01, 0.015, 0.03), 0.04, coat=1.0, coat_rough=0.02),
    "tpu_black": mat("TPU_black", (0.02, 0.02, 0.022), 0.7),
    "wire_r": mat("Wire_red", (0.55, 0.02, 0.02), 0.5),
    "wire_k": mat("Wire_black", (0.02, 0.02, 0.02), 0.5),
    "heatshrink": mat("Heatshrink_black", (0.015, 0.015, 0.015), 0.6),
    "led_w": mat("LED_white", (1, 1, 1), 0.3, emission=((1, 0.97, 0.92), 5)),
    "led_r": mat("LED_red", (1, 0.05, 0.03), 0.3, emission=((1, 0.05, 0.02), 5)),
}


# ---------------------------------------------------------------- geometry helpers
def bm_cyl(r1, h, seg=16, r2=None, caps=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=seg, radius1=r1, radius2=r1 if r2 is None else r2, depth=h)
    return bm


def bm_box(sx, sy, sz):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, sz)), verts=bm.verts)
    return bm


def bm_sphere(r, subdiv=2):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
    return bm


def bm_annulus(rin, rout, thick, seg=128, z0=None):
    """Flat ring in the XY plane, rectangular section (radial rout-rin, thickness along Z)."""
    bm = bmesh.new()
    z0 = -thick / 2 if z0 is None else z0
    rings = []
    for (r, z) in ((rin, z0), (rout, z0), (rout, z0 + thick), (rin, z0 + thick)):
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
    for k in range(4):
        a, b = rings[k], rings[(k + 1) % 4]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def bevel_bm(bm, width, segs=2):
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=width, segments=segs, affect="EDGES", profile=0.5, clamp_overlap=True)
    return bm


def along(p0, p1):
    """Matrix placing a Z-axis primitive (centred at origin) on the segment p0-p1; returns (matrix, length)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4(), d.length


def T(x, y, z): return Matrix.Translation((x, y, z))
def Rx(a): return Matrix.Rotation(a, 4, "X")
def Ry(a): return Matrix.Rotation(a, 4, "Y")
def Rz(a): return Matrix.Rotation(a, 4, "Z")


class Group:
    """Collects primitives into one merged mesh per material, parented to an empty."""
    def __init__(self, name, parent=None, loc=(0, 0, 0)):
        self.node = bpy.data.objects.new(name, None); scene.collection.objects.link(self.node)
        if parent is not None: self.node.parent = parent.node if isinstance(parent, Group) else parent
        self.node.location = loc
        self.parts = {}

    def add(self, bm_src, matrix, material, smooth=True):
        if material.name not in self.parts: self.parts[material.name] = (bmesh.new(), material)
        tgt = self.parts[material.name][0]
        bmesh.ops.transform(bm_src, matrix=matrix, verts=bm_src.verts)
        for f in bm_src.faces: f.smooth = smooth
        me = bpy.data.meshes.new("tmp"); bm_src.to_mesh(me); bm_src.free()
        tgt.from_mesh(me); bpy.data.meshes.remove(me)

    def build(self, sharp_deg=38):
        objs = []
        for mname, (bm, material) in self.parts.items():
            me = bpy.data.meshes.new(f"{self.node.name}_{mname}"); bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(me.name, me); scene.collection.objects.link(o)
            o.parent = self.node; me.materials.append(material)
            me.set_sharp_from_angle(angle=math.radians(sharp_deg))
            objs.append(o)
        self.parts = {}
        return objs


root = bpy.data.objects.new("ball_drone", None); scene.collection.objects.link(root)
cage, ring_big, ring_small, quad = (Group(n, root) for n in ("cage", "ring_big", "ring_small", "quad"))

# ---------------------------------------------------------------- cage: icosahedron, vertices on the Z (pole) axis
zr = CAGE_R / math.sqrt(5); rr = 2 * CAGE_R / math.sqrt(5)
verts = [Vector((0, 0, CAGE_R)), Vector((0, 0, -CAGE_R))]
verts += [Vector((rr * math.cos(math.radians(72 * k + 90)), rr * math.sin(math.radians(72 * k + 90)), zr)) for k in range(5)]
verts += [Vector((rr * math.cos(math.radians(72 * k + 126)), rr * math.sin(math.radians(72 * k + 126)), -zr)) for k in range(5)]
edges = [(i, j) for i in range(12) for j in range(i + 1, 12) if abs((verts[i] - verts[j]).length - EDGE) < 1e-6]
assert len(edges) == 30, len(edges)
nbr = {i: [j for (a, b) in edges for (i2, j) in ((a, b), (b, a)) if i2 == i] for i in range(12)}

for i, v in enumerate(verts):
    # hub: rounded core (slightly flattened along the radial direction, like a printed node) + 5 sockets with chamfered mouths
    radial = v.normalized()
    q = Vector((0, 0, 1)).rotation_difference(radial).to_matrix().to_4x4()
    core = bm_sphere(HUB_CORE_R, 2)
    bmesh.ops.scale(core, vec=Vector((1, 1, 0.78)), verts=core.verts)
    cage.add(core, T(*v) @ q, M["tpu"])
    for j in nbr[i]:
        d = (verts[j] - v).normalized()
        mtx, L = along(v + d * 1.0 * mm, v + d * SOCKET_LEN)
        cage.add(bm_cyl(SOCKET_R, L, 12, r2=SOCKET_R * 0.92), mtx, M["tpu"])
        m2, L2 = along(v + d * (SOCKET_LEN - 0.4 * mm), v + d * SOCKET_LEN)
        cage.add(bm_cyl(SOCKET_R * 1.12, L2, 12), m2, M["tpu"])        # lip at the socket mouth
    # tiny flat on the outside of the hub (print bed face), reads as a real printed part
    cap = bm_cyl(HUB_CORE_R * 0.62, 0.5 * mm, 16)
    cage.add(cap, T(*(v + radial * HUB_CORE_R * 0.72)) @ q, M["tpu"])
for (i, j) in edges:
    d = (verts[j] - verts[i]).normalized()
    mtx, L = along(verts[i] + d * ROD_INSERT, verts[j] - d * ROD_INSERT)
    cage.add(bm_cyl(ROD_R, L, 8), mtx, M["carbon"])

# ---------------------------------------------------------------- gimbal rings + pivots
def pivot_boss(group, centre, axis, size_axis, size_other, material):
    """Rectangular printed boss around a bearing seat; axis = 'X'|'Y'|'Z' is the pin axis."""
    s = {"X": (size_axis, size_other, size_other), "Y": (size_other, size_axis, size_other), "Z": (size_other, size_other, size_axis)}[axis]
    group.add(bevel_bm(bm_box(*s), 0.6 * mm), T(*centre), material)


def bearing(group, centre, axis):
    rot = {"X": Ry(math.pi / 2), "Y": Rx(math.pi / 2), "Z": Matrix.Identity(4)}[axis]
    group.add(bm_cyl(2.5 * mm, 2.5 * mm, 20), T(*centre) @ rot, M["steel"])              # MR52: 5 mm OD x 2.5 mm
    group.add(bm_cyl(1.9 * mm, 2.6 * mm, 20), T(*centre) @ rot, M["bearing_seal"])


def pin(group, p0, p1):
    mtx, L = along(p0, p1)
    group.add(bm_cyl(1.0 * mm, L, 12), mtx, M["steel"])                               # 2 mm steel pin


# ring_big: annulus in Y-Z plane (rotate the XY annulus about Y), pivots to the cage on Z, carries ring_small on Y
ring_big.add(bm_annulus(BIG_IN, BIG_OUT, RING_T, 160), Ry(math.pi / 2), M["petg"])
mid_big = (BIG_IN + BIG_OUT) / 2
for s in (1, -1):
    pivot_boss(ring_big, (0, 0, s * mid_big), "Z", 6.0 * mm, 8.0 * mm, M["petg"])
    bearing(ring_big, (0, 0, s * mid_big), "Z")
    pin(ring_big, (0, 0, s * (mid_big - 1.5 * mm)), (0, 0, s * (CAGE_R - 1.5 * mm)))       # into the pole hub
    pivot_boss(ring_big, (0, s * mid_big, 0), "Y", 6.0 * mm, 8.0 * mm, M["petg"])
    bearing(ring_big, (0, s * mid_big, 0), "Y")

# ring_small: annulus in the X-Y plane, pivots on ring_big at +-Y, carries the quad on X
ring_small.add(bm_annulus(SMALL_IN, SMALL_OUT, RING_T, 160), Matrix.Identity(4), M["petg"])
mid_small = (SMALL_IN + SMALL_OUT) / 2
for s in (1, -1):
    pivot_boss(ring_small, (0, s * mid_small, 0), "Y", 5.4 * mm, 7.0 * mm, M["petg"])
    pin(ring_small, (0, s * (SMALL_IN + 1.0 * mm), 0), (0, s * (BIG_OUT - 0.5 * mm), 0))
    pivot_boss(ring_small, (s * mid_small, 0, 0), "X", 5.4 * mm, 7.0 * mm, M["petg"])
    bearing(ring_small, (s * mid_small, 0, 0), "X")

# ---------------------------------------------------------------- quad: Meteor85-style whoop
motors = []
for k in range(4):
    a = math.radians(45 + 90 * k)
    motors.append(Vector((R_MOTOR * math.cos(a), R_MOTOR * math.sin(a), 0)))

for k, mp in enumerate(motors):
    x, y = mp.x, mp.y
    # duct: thin wall + stiffening lip at the bottom and a rolled top edge
    quad.add(bm_annulus(DUCT_IN, DUCT_IN + DUCT_WALL, DUCT_Z1 - DUCT_Z0, 96, z0=DUCT_Z0), T(x, y, 0), M["pp"])
    quad.add(bm_annulus(DUCT_IN - 1.2 * mm, DUCT_IN + DUCT_WALL + 0.6 * mm, 1.1 * mm, 96, z0=DUCT_Z0), T(x, y, 0), M["pp"])
    quad.add(bm_annulus(DUCT_IN + DUCT_WALL - 0.2 * mm, DUCT_IN + DUCT_WALL + 0.5 * mm, 0.9 * mm, 96, z0=DUCT_Z1 - 0.9 * mm), T(x, y, 0), M["pp"])
    # motor mount: round plate + three spokes out to the duct wall
    quad.add(bm_cyl(7.6 * mm, 1.5 * mm, 32), T(x, y, MOUNT_Z), M["pp"])
    for sp in range(3):
        b = math.atan2(y, x) + math.radians(60 + 120 * sp)
        p0 = Vector((x, y, MOUNT_Z)) + Vector((math.cos(b), math.sin(b), 0)) * 6.5 * mm
        p1 = Vector((x, y, MOUNT_Z)) + Vector((math.cos(b), math.sin(b), 0)) * (DUCT_IN + 0.3 * mm)
        mtx, L = along(p0, p1)
        quad.add(bevel_bm(bm_box(2.2 * mm, 1.5 * mm, L), 0.3 * mm, 1), mtx, M["pp"])
    # EX1103 motor (13.5 mm bell): base + windings + bell + cap + shaft
    quad.add(bm_cyl(5.6 * mm, 1.8 * mm, 32), T(x, y, MOTOR_BASE_Z + 0.9 * mm), M["bell"])
    quad.add(bm_cyl(5.3 * mm, 1.4 * mm, 24), T(x, y, MOTOR_BASE_Z + 2.4 * mm), M["stator"])
    quad.add(bevel_bm(bm_cyl(6.75 * mm, 5.4 * mm, 40), 0.35 * mm, 2), T(x, y, MOTOR_BASE_Z + 5.8 * mm), M["bell"])
    quad.add(bm_cyl(4.2 * mm, 0.5 * mm, 32), T(x, y, MOTOR_BASE_Z + 8.75 * mm), M["bell_cap"])
    quad.add(bm_cyl(0.75 * mm, 6.0 * mm, 12), T(x, y, MOTOR_BASE_Z + 10.5 * mm), M["steel"])
# bridges between neighbouring ducts (frame web)
for k in range(4):
    a = math.radians(90 * k)
    # bridges sit on the X and Y axes, at distance R_MOTOR*cos45 from the centre, spanning the 6 mm gap between ducts
    pos = Vector((math.cos(a), math.sin(a), 0)) * R_MOTOR * math.cos(math.radians(45))
    sx, sy = (5.0 * mm, 9.0 * mm) if abs(math.cos(a)) > 0.5 else (9.0 * mm, 5.0 * mm)
    quad.add(bevel_bm(bm_box(sx, sy, 2.0 * mm), 0.4 * mm, 1), T(pos.x, pos.y, -2.0 * mm), M["pp"])
# central body: square frame around the 26x26 whoop mount + diagonal arms to the motor mounts
for (sx, sy, px, py) in ((32 * mm, 3 * mm, 0, 14.5 * mm), (32 * mm, 3 * mm, 0, -14.5 * mm), (3 * mm, 32 * mm, 14.5 * mm, 0), (3 * mm, 32 * mm, -14.5 * mm, 0)):
    quad.add(bevel_bm(bm_box(sx, sy, 1.8 * mm), 0.4 * mm, 1), T(px, py, -2.1 * mm), M["pp"])
for mp in motors:
    d = mp.normalized()
    mtx, L = along(d * 14 * mm + Vector((0, 0, -2.1 * mm)), mp + Vector((0, 0, MOUNT_Z)) - d * 6 * mm)
    quad.add(bevel_bm(bm_box(5.5 * mm, 1.8 * mm, L), 0.4 * mm, 1), mtx, M["pp"])
for sx in (1, -1):
    for sy in (1, -1):
        quad.add(bm_cyl(1.3 * mm, 5.0 * mm, 10), T(sx * 11.5 * mm, sy * 11.5 * mm, 0.6 * mm), M["tpu_black"])   # soft-mount grommets
# F411 AIO 26x26: PCB, MCU, 4-in-1 ESC FETs, caps, ceramic ELRS antenna, VTX + u.fl dipole
FC_Z = 3.6 * mm
quad.add(bevel_bm(bm_box(26 * mm, 26 * mm, 1.2 * mm), 0.3 * mm, 1), T(0, 0, FC_Z), M["pcb"])
quad.add(bm_box(5 * mm, 5 * mm, 0.9 * mm), T(0, 0, FC_Z + 1.0 * mm) @ Rz(math.radians(45)), M["chip"])              # F411 MCU
for i in range(8):
    a = math.radians(45 + 90 * (i // 2)); off = (i % 2 - 0.5) * 3.2 * mm
    c = Vector((math.cos(a), math.sin(a), 0)) * 9.5 * mm + Vector((-math.sin(a), math.cos(a), 0)) * off
    quad.add(bm_box(2.4 * mm, 2.0 * mm, 0.8 * mm), T(c.x, c.y, FC_Z + 1.0 * mm), M["chip"])
for (px, py) in ((-6, 6), (6, -6), (-7, -2), (7, 3), (2, 8), (-2, -8)):
    quad.add(bm_box(1.6 * mm, 0.8 * mm, 0.7 * mm), T(px * mm, py * mm, FC_Z + 0.95 * mm), M["smd"])
quad.add(bm_box(2.0 * mm, 6.0 * mm, 1.0 * mm), T(10.5 * mm, -4 * mm, FC_Z + 1.1 * mm), M["ceramic"])             # ELRS ceramic antenna
quad.add(bm_box(7.0 * mm, 7.0 * mm, 1.2 * mm), T(-6.5 * mm, -7.0 * mm, FC_Z + 1.2 * mm), M["chip"])              # VTX shield can
for (px, py) in ((-12, -12), (12, -12), (-12, 12), (12, 12)):
    quad.add(bm_cyl(1.0 * mm, 0.15 * mm, 12), T(px * mm, py * mm, FC_Z + 0.68 * mm), M["gold"])
ant0 = Vector((-6.5 * mm, -12.5 * mm, FC_Z + 1.0 * mm)); ant1 = Vector((-6.5 * mm, -24 * mm, 13.5 * mm)); ant2 = Vector((-6.5 * mm, -30 * mm, 26 * mm))
for (p0, p1, r, mt) in ((ant0, ant1, 0.55 * mm, M["wire_k"]), (ant1, ant2, 0.75 * mm, M["heatshrink"])):
    mtx, L = along(p0, p1); quad.add(bm_cyl(r, L, 8), mtx, mt)
# motor leads: 3 thin wires along each arm
for mp in motors:
    d = mp.normalized(); n = Vector((-d.y, d.x, 0))
    for w in (-1, 0, 1):
        mtx, L = along(d * 11 * mm + n * w * 0.7 * mm + Vector((0, 0, FC_Z + 0.4 * mm)), mp - d * 7.5 * mm + n * w * 0.7 * mm + Vector((0, 0, 0.2 * mm)))
        quad.add(bm_cyl(0.28 * mm, L, 6), mtx, M["wire_k"])
# Caddx Ant 14x14 camera in a TPU canopy, tilted 15 deg up, at the front
CAM_C = Vector((0, 12.0 * mm, 18.5 * mm)); TILT = math.radians(15)   # high canopy: camera clears the duct tops
camM = T(*CAM_C) @ Rx(TILT)
quad.add(bevel_bm(bm_box(14 * mm, 11 * mm, 14 * mm), 0.8 * mm, 2), camM, M["cam"])
quad.add(bevel_bm(bm_cyl(4.2 * mm, 5.0 * mm, 32), 0.3 * mm, 1), camM @ T(0, 7.6 * mm, 0) @ Rx(math.pi / 2), M["cam"])
quad.add(bm_cyl(3.1 * mm, 0.6 * mm, 32), camM @ T(0, 10.2 * mm, 0) @ Rx(math.pi / 2), M["lens"])
for sx in (1, -1):   # TPU canopy: side cheeks from the frame up to the camera, plus a rear hoop over the FC
    quad.add(bevel_bm(bm_box(1.6 * mm, 12 * mm, 21 * mm), 0.5 * mm, 1), T(sx * 7.9 * mm, 11.0 * mm, 10.5 * mm) @ Rx(TILT * 0.6), M["tpu_black"])
    quad.add(bevel_bm(bm_box(1.6 * mm, 3.0 * mm, 15 * mm), 0.4 * mm, 1), T(sx * 7.9 * mm, -9.0 * mm, 7.5 * mm), M["tpu_black"])
quad.add(bevel_bm(bm_box(17.4 * mm, 3.0 * mm, 1.6 * mm), 0.4 * mm, 1), T(0, -9.0 * mm, 14.6 * mm), M["tpu_black"])
for sx in (1, -1):
    mtx, L = along((sx * 7.9 * mm, -9.0 * mm, 14.6 * mm), (sx * 7.9 * mm, 6.0 * mm, 19.5 * mm))
    quad.add(bevel_bm(bm_box(1.6 * mm, 2.4 * mm, L), 0.4 * mm, 1), mtx, M["tpu_black"])
# inspection LED next to the lens + red status LED at the rear
quad.add(bm_cyl(1.3 * mm, 1.0 * mm, 16), T(9.4 * mm, 17.6 * mm, 14.5 * mm) @ Rx(math.pi / 2 - TILT), M["led_w"])
quad.add(bm_cyl(1.0 * mm, 0.8 * mm, 12), T(0, -15.5 * mm, FC_Z + 0.9 * mm), M["led_r"])
# 2S LiHV long pack strapped underneath, centred under the gimbal (CG on the pivot axes)
bz = -3.4 * mm - BATT[2] / 2
quad.add(bevel_bm(bm_box(*BATT), 1.6 * mm, 3), T(0, 0, bz), M["battery"])
quad.add(bevel_bm(bm_box(BATT[0] + 0.2 * mm, 34 * mm, BATT[2] + 0.2 * mm), 1.6 * mm, 3), T(0, 3 * mm, bz), M["label"])
for sy in (-14 * mm, 14 * mm):   # velcro straps around battery + frame
    quad.add(bevel_bm(bm_box(BATT[0] + 1.6 * mm, 9 * mm, BATT[2] + 5.6 * mm), 0.8 * mm, 2), T(0, sy, bz + 2.0 * mm), M["strap"])
# XT30 lead at the rear
for (dx, mt) in ((-1.4 * mm, M["wire_r"]), (1.4 * mm, M["wire_k"])):
    mtx, L = along((dx, -BATT[1] / 2 + 1 * mm, bz + 3 * mm), (dx, -BATT[1] / 2 - 7 * mm, bz + 3 * mm))
    quad.add(bm_cyl(0.75 * mm, L, 8), mtx, mt)
    mtx, L = along((dx, -14 * mm, FC_Z - 0.2 * mm), (dx, -BATT[1] / 2 - 9 * mm, bz + 3 * mm))
    quad.add(bm_cyl(0.6 * mm, L, 8), mtx, mt)
quad.add(bevel_bm(bm_box(10 * mm, 6.5 * mm, 5.2 * mm), 0.6 * mm, 2), T(0, -BATT[1] / 2 - 10 * mm, bz + 3 * mm), M["xt30"])
# centre mount: CF brackets from the frame out to the small ring's X pivots (between the front and rear ducts) + pins
for s in (1, -1):
    mtx, L = along((s * 15 * mm, 0, 0.6 * mm), (s * (SMALL_IN - 3.0 * mm), 0, 0.6 * mm))
    quad.add(bevel_bm(bm_box(4.0 * mm, 2.4 * mm, L), 0.4 * mm, 1), mtx, M["carbon"])
    quad.add(bevel_bm(bm_box(5.5 * mm, 6.0 * mm, 4.2 * mm), 0.6 * mm, 2), T(s * (SMALL_IN - 4.0 * mm), 0, 0.6 * mm), M["tpu_black"])
    pin(quad, (s * (SMALL_IN - 6.0 * mm), 0, 0), (s * (SMALL_OUT + 1.2 * mm), 0, 0))
    quad.add(bm_cyl(1.6 * mm, 1.0 * mm, 12), T(s * (SMALL_OUT + 1.0 * mm), 0, 0) @ Ry(math.pi / 2), M["steel"])   # e-clip

# ---------------------------------------------------------------- props: Gemfan 2015 2-blade (own nodes)
def blade_mesh(spin):
    bm = bmesh.new(); n_sec = 12; rows = []
    r0, r1 = 2.6 * mm, PROP_R
    for i in range(n_sec + 1):
        t = i / n_sec; r = r0 + (r1 - r0) * t
        chord = (5.2 + 4.2 * math.sin(math.pi * min(1.0, t * 1.25)) * (1 - 0.35 * t) - 2.6 * max(0, t - 0.85) / 0.15) * mm
        pitch = math.atan(PROP_PITCH / (2 * math.pi * max(r, 4 * mm))) * spin       # geometric pitch angle
        ring = []
        for s in (-0.5, -0.2, 0.2, 0.5):
            xx = s * chord; zz = 0.55 * mm * (1 - (2 * s) ** 2)
            ring.append(Vector((r, xx * math.cos(pitch) - zz * math.sin(pitch), xx * math.sin(pitch) + zz * math.cos(pitch))))
        rows.append([bm.verts.new(v) for v in ring])
    for i in range(n_sec):
        for j in range(3):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.55 * mm)
    return bm


for k, mp in enumerate(motors):
    front = mp.y > 0
    spin = 1 if k % 2 == 0 else -1
    pg = Group(f"prop_{k}", quad, loc=(mp.x, mp.y, PROP_Z))
    mt = M["prop_blue"] if front else M["prop_grey"]
    pg.add(bevel_bm(bm_cyl(2.6 * mm, 3.4 * mm, 24), 0.3 * mm, 1), Matrix.Identity(4), mt)
    for bl in range(2):
        pg.add(blade_mesh(spin), Rz(math.pi * bl), mt)
    pg.build(sharp_deg=50)

objs = [o for g in (cage, ring_big, ring_small, quad) for o in g.build()]

# camera + inspection light anchors (glTF local -Z = view direction after the Y-up conversion; +15 deg tilt up)
for name, loc in (("fpv_cam", CAM_C + Vector((0, 10.5 * mm, 2.8 * mm))), ("inspection_light", Vector((9.4 * mm, 18.2 * mm, 14.6 * mm)))):
    e = bpy.data.objects.new(name, None); scene.collection.objects.link(e)
    e.parent = quad.node; e.location = loc; e.rotation_euler = (TILT, 0, 0)

# ---------------------------------------------------------------- checks
prop_tip = math.hypot(R_MOTOR + PROP_R, PROP_Z)
quad_max = 0.0
for o in [o for o in bpy.data.objects if o.type == "MESH" and (o.parent == quad.node or (o.parent and o.parent.parent == quad.node))]:
    mw = o.matrix_world
    for v in o.data.vertices:
        p = mw @ v.co
        if abs(p.y) < 3.2 * mm and abs(p.z) < 3.2 * mm and abs(p.x) > 60 * mm:
            continue                                   # pivot pins/brackets intentionally reach the ring on the X axis
        quad_max = max(quad_max, p.length)
print("CHECK cage OD (hub centres) %.1f mm, edge %.2f mm, rod length %.1f mm" % (2 * CAGE_R / mm, EDGE / mm, (EDGE - 2 * ROD_INSERT) / mm))
print("CHECK prop tip max distance from centre %.2f mm (limit 72.0, ring_small inner %.1f) -> %s" %
      (prop_tip / mm, SMALL_IN / mm, "OK" if prop_tip < 0.072 else "FAIL"))
print("CHECK quad envelope (excluding X pivot pins) %.2f mm -> clearance to ring_small %.2f mm" % (quad_max / mm, (SMALL_IN - quad_max) / mm))
print("CHECK cage closest rod to centre (edge midradius) %.1f mm vs ring_big outer %.1f mm" % (CAGE_R * math.cos(math.radians(31.7175)) / mm, BIG_OUT / mm))

# ---------------------------------------------------------------- preview render
if "--preview" in sys.argv:
    world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.32, 0.34, 0.37, 1); bg.inputs[1].default_value = 0.9
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam)
    cam.data.lens = 50
    view = "--top" if "--top" in sys.argv else "--close" if "--close" in sys.argv else ""
    cam.location = {"--top": (0.0, 0.0, 0.62), "--close": (0.10, 0.16, 0.085)}.get(view, (0.30, 0.42, 0.24))
    target = Vector((0, 0, 0)) if view != "--close" else Vector((0, 0.004, -0.002))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    for (rot, energy) in (((0.75, 0.15, 0.9), 4.5), ((1.2, -0.4, -2.2), 1.6)):
        s = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); s.data.energy = energy; s.rotation_euler = rot
        scene.collection.objects.link(s)
    floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor")); scene.collection.objects.link(floor)
    fb = bmesh.new(); bmesh.ops.create_grid(fb, x_segments=1, y_segments=1, size=1.5); fb.to_mesh(floor.data); fb.free()
    floor.location = (0, 0, -CAGE_R - 0.004); floor.data.materials.append(mat("floor", (0.42, 0.42, 0.40), 0.8))
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    scene.render.filepath = PREVIEW.replace(".png", view.replace("--", "_") + ".png") if view else PREVIEW
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(floor)

# ---------------------------------------------------------------- export
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True, export_apply=True, use_selection=False,
                          export_materials="EXPORT", export_cameras=False, export_lights=False)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in scene.objects if o.type == "MESH" and o.name != "floor")
print("BUILD_OK", OUT, "mesh objects", len([o for o in scene.objects if o.type == "MESH"]), "triangles", tris)
