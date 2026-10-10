"""Apex-2 ball cage, P1A fixed cage: generator for Autodesk Fusion (stages 1-6).

1  User parameters (Modify > Change Parameters). Comments say where each value must come from.
2  Aircraft keep-out envelope: frame, motors, four full prop disks, stack, camera + view cone, batteries.
3  Cage skeleton scaled from kert's Thingiverse 408519 (CC BY-NC): truncated icosahedron, pentagon at +-Z,
   90 edge rods + 10 pole rods.
4  Printable hubs (one part per unique arm layout) placed at all 62 nodes, plus a socket fit strip.
5  Aircraft carrier (Y-slotted frame screws, X-slotted support joints, battery-strap slots), two support
   arms and two X brackets that screw to bosses on the four hubs of the +X and -X equator edges.
6  Measured values from measurements.json override parameters; the report re-checks span, prop and
   battery clearance, hubs in the camera view and the mass budget.

Run in the "Apex2 Ball Cage P1A" design (Scripts and Add-Ins, or the Fusion MCP loader that sets
__file__). Re-running keeps edited parameter values and rebuilds only the generated components.
STL exports go to ./exports. Fusion's API works in centimetres; values here are millimetres.
"""
import hashlib
import itertools
import json
import math
import os
import traceback

import adsk.core
import adsk.fusion

HERE = os.path.dirname(os.path.abspath(globals().get('__file__', '/Users/devk/Documents/HackPHS26/cad/apex2-cage/build_p1a.py')))
REFERENCE_DIR = os.path.expanduser('~/Downloads/Spherical Drone - 408519 - part 1 of 2/files')
REFERENCE_HUBS = ['Croisillon_Y3_Bouclier.STL', 'Croisillon_Y4_Bouclier.STL', 'Croisillon_toile5_Bouclier.STL']

PARAMS = [
    # cage
    ('rod_dia', '1.0 mm', 'mm', 'MEASURE: actual carbon rod diameter (1 mm prototype baseline)'),
    ('rod_bore_clear', '0.15 mm', 'mm', 'FIT COUPON: socket clearance per side (strip prints 0.05-0.30)'),
    ('hub_core_r', '2.5 mm', 'mm', 'DESIGN: hub centre to flat outer face (sets outer span; bed face when printing)'),
    ('hub_body_r', '2.2 mm', 'mm', 'DESIGN: hub core cylinder radius'),
    ('hub_arm_len', '7 mm', 'mm', 'DESIGN: hub centre to socket mouth (original ~10 mm for 3 mm rod)'),
    ('hub_arm_od', '3.2 mm', 'mm', 'DESIGN: socket tube OD (original ~5 mm for 3 mm rod)'),
    ('hub_keel_w', '1.6 mm', 'mm', 'DESIGN: keel width under each hub arm (support-free printing; narrower than the tube to save mass)'),
    ('socket_depth', '5 mm', 'mm', 'FIT COUPON: rod insertion depth (original ~7.8 mm)'),
    ('rod_end_gap', '0.25 mm', 'mm', 'DESIGN: gap between rod end and socket floor'),
    # Rod length drives the cage (user, 2026-10-08: a round number on the jig). 44.50 mm gives a 247.85 mm cage (target 245-250).
    ('rod_cut_len', '44.5 mm', 'mm', 'DESIGN: cut length of the 90 edge rods; drives the cage size'),
    ('cage_edge', 'rod_cut_len + 2 * (hub_arm_len - socket_depth) + 2 * rod_end_gap', 'mm', 'DERIVED: hub centre-to-centre distance'),
    ('cage_vertex_r', 'cage_edge * 2.4780186591', 'mm', 'DERIVED: hub centre radius'),
    ('cage_outer_dia', '2 * (cage_vertex_r + hub_core_r)', 'mm', 'DERIVED (target 245-250): maximum assembled outside span including hubs'),
    ('pent_r', 'cage_edge / (2 * sin(36 deg))', 'mm', 'DERIVED: pentagon circumradius'),
    ('pole_rise', 'cage_vertex_r - sqrt(cage_vertex_r ^ 2 - pent_r ^ 2)', 'mm', 'DERIVED: pole hub height above its pentagon'),
    ('pole_edge', 'sqrt(pent_r ^ 2 + pole_rise ^ 2)', 'mm', 'DERIVED: pole hub to four-way hub distance'),
    ('pole_rod_cut_len', 'pole_edge - 2 * (hub_arm_len - socket_depth) - 2 * rod_end_gap', 'mm', 'DERIVED: cut length of the 10 pole rods'),
    # aircraft
    ('motor_diag', '95 mm', 'mm', 'MEASURE: diagonal motor-centre distance (Apex-2 ~95)'),
    ('prop_dia', '50.8 mm', 'mm', 'MEASURE: actual prop diameter (Gemfan 2015)'),
    ('prop_z', '13 mm', 'mm', 'MEASURE: prop disk bottom above frame top'),
    ('prop_disk_h', '5 mm', 'mm', 'DESIGN: prop swept-disk thickness'),
    ('motor_od', '15.5 mm', 'mm', 'MEASURE: motor bell OD'),
    ('motor_h', '12 mm', 'mm', 'MEASURE: motor height above frame top'),
    ('frame_t', '2.5 mm', 'mm', 'MEASURE: frame plate thickness'),
    ('arm_w', '8 mm', 'mm', 'MEASURE: frame arm width'),
    ('stack_w', '32 mm', 'mm', 'MEASURE: frame centre plate width'),
    ('stack_h', '14 mm', 'mm', 'MEASURE: stack height above frame top'),
    ('frame_hole_pitch', '25.5 mm', 'mm', 'MEASURE: frame/AIO square mounting-hole pitch'),
    ('cam_size', '14 mm', 'mm', 'MEASURE: camera body (14 x 14 class)'),
    ('cam_y', '22 mm', 'mm', 'MEASURE: camera centre forward (+Y) of frame centre'),
    ('cam_z', '9 mm', 'mm', 'MEASURE: camera centre above frame top'),
    ('cam_tilt', '20 deg', 'deg', 'SETUP: camera uptilt'),
    ('cam_hfov', '120 deg', 'deg', 'MEASURE: lens horizontal field of view (cone approximation)'),
    ('batt450_l', '60 mm', 'mm', 'MEASURE: OVONIC 450 mAh pack length'),
    ('batt450_w', '18 mm', 'mm', 'MEASURE: 450 mAh pack width'),
    ('batt450_h', '13 mm', 'mm', 'MEASURE: 450 mAh pack height'),
    ('batt1100_l', '70 mm', 'mm', 'MEASURE: OVONIC 1100 mAh pack length'),
    ('batt1100_w', '32 mm', 'mm', 'MEASURE: 1100 mAh pack width'),
    ('batt1100_h', '16 mm', 'mm', 'MEASURE: 1100 mAh pack height'),
    # carrier and supports
    ('carrier_t', '2.5 mm', 'mm', 'DESIGN: carrier plate thickness'),
    ('carrier_len', '40 mm', 'mm', 'DESIGN: carrier centre length (Y)'),
    ('carrier_core_w', '44 mm', 'mm', 'DESIGN: carrier centre width (X)'),
    ('carrier_span', '80 mm', 'mm', 'DESIGN: carrier tip-to-tip span along X'),
    ('carrier_bar_w', '12 mm', 'mm', 'DESIGN: carrier side-bar width'),
    ('adj_y', '5 mm', 'mm', 'DESIGN: frame-on-carrier slot travel each way, perpendicular to the support arms (P1A: fore-aft)'),
    ('adj_x', '4 mm', 'mm', 'DESIGN: carrier-on-arm slot travel each way, along the support arms (P1A: lateral)'),
    ('strap_w', '10 mm', 'mm', 'MEASURE: battery strap width'),
    ('strap_slot_t', '2.2 mm', 'mm', 'MEASURE: battery strap thickness + clearance'),
    ('support_w', '6 mm', 'mm', 'DESIGN: support arm width'),
    ('support_h', '4 mm', 'mm', 'DESIGN: support arm height'),
    ('flange_h', '16 mm', 'mm', 'DESIGN: support end flange height'),
    ('flange_t', '3 mm', 'mm', 'DESIGN: support end flange thickness'),
    ('bracket_t', '3 mm', 'mm', 'DESIGN: X bracket thickness'),
    ('bracket_bar_w', '7 mm', 'mm', 'DESIGN: X bracket bar width'),
    ('mount_boss_len', '6 mm', 'mm', 'DESIGN: boss length inward from mount-hub centre'),
    ('mount_boss_od', '5 mm', 'mm', 'DESIGN: mount boss OD'),
    ('m2_clear', '2.3 mm', 'mm', 'DESIGN: M2 clearance hole / slot width'),
    ('m2_tap', '1.7 mm', 'mm', 'FIT COUPON: M2 self-tapping pilot (strip prints 1.6/1.7/1.8)'),
    ('rod_density', '1.55', '', 'ASSUMED: carbon rod g/cm^3'),
    ('petg_density', '1.27', '', 'ASSUMED: PETG g/cm^3 (solid volume; slicer infill lowers this)'),
    ('print_wall', '1.2 mm', 'mm', 'ASSUMED: slicer wall/skin thickness for the print-mass estimate (3 x 0.4 mm)'),
    ('print_infill', '0.25', '', 'ASSUMED: slicer infill fraction for the print-mass estimate'),
    ('battery_gap', '3 mm', 'mm', 'DESIGN: foam pad between carrier underside and pack; clears the M2 nuts (1.6 mm) and screw tails'),
    ('battery_shield_t', '0.8 mm', 'mm', 'DESIGN: printed PETG shield under the foam pad; nuts can never reach the LiPo pouch even if the foam compresses'),
    ('frame_column_h', '20 mm', 'mm', 'MEASURE: Apex-2 column height (top plate underside above bottom plate top); listing 20 mm'),
    ('antenna_len', '30 mm', 'mm', 'MEASURE: exposed VTX antenna element (listing: 70 mm overall incl. coax)'),
    ('antenna_d', '5 mm', 'mm', 'MEASURE: VTX antenna element diameter'),
]
GENERATED = ['Aircraft envelope (PLACEHOLDER)', 'Cage skeleton (scaled 408519)', 'Cage hubs (stage 4)',
             'Socket fit strip (print first)', 'Carrier and supports (stage 5)', 'Rod cutting jig',
             'REFERENCE Thingiverse 408519 hubs (kert, CC BY-NC)']
CLEARANCES = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
TAP_PILOTS = [1.6, 1.7, 1.8]
UNION, CUT = adsk.fusion.BooleanTypes.UnionBooleanType, adsk.fusion.BooleanTypes.DifferenceBooleanType


# ---------------------------------------------------------------- small vector helpers (mm tuples)
def add(a, b): return tuple(a[i] + b[i] for i in range(3))
def sub(a, b): return tuple(a[i] - b[i] for i in range(3))
def mul(a, s): return tuple(c * s for c in a)
def dot(a, b): return sum(a[i] * b[i] for i in range(3))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a): return mul(a, 1 / norm(a))
def P(a): return adsk.core.Point3D.create(a[0] / 10, a[1] / 10, a[2] / 10)
def D(a): return adsk.core.Vector3D.create(*a)


class Solids:
    def __init__(self):
        self.tbm = adsk.fusion.TemporaryBRepManager.get()

    def cyl(self, a, b, d):
        return self.tbm.createCylinderOrCone(P(a), d / 20, P(b), d / 20)

    def cone(self, apex, base, r):
        return self.tbm.createCylinderOrCone(P(apex), 0.0001, P(base), r / 10)

    def box(self, centre, length_dir, width_dir, length, width, height):
        return self.tbm.createBox(adsk.core.OrientedBoundingBox3D.create(
            P(centre), D(unit(length_dir)), D(unit(width_dir)), length / 10, width / 10, height / 10))

    def aabox(self, lo, hi):
        centre = mul(add(lo, hi), 0.5)
        return self.box(centre, (1, 0, 0), (0, 1, 0), hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])

    def slot(self, a, b, width, z0, z1):
        """Vertical-walled slot between points a and b (z ignored), from z0 to z1."""
        a0, b0 = (a[0], a[1], z0), (b[0], b[1], z0)
        body = self.cyl(a0, (a[0], a[1], z1), width)
        self.join(body, self.cyl(b0, (b[0], b[1], z1), width))
        if norm(sub(b0, a0)) > 1e-6:
            along = sub(b0, a0)
            self.join(body, self.box(add(mul(add(a0, b0), 0.5), (0, 0, (z1 - z0) / 2)), along, cross((0, 0, 1), unit(along)),
                                     norm(along), width, z1 - z0))
        return body

    def join(self, target, tool):
        if not self.tbm.booleanOperation(target, tool, UNION):
            raise RuntimeError('Solid union failed')
        return target

    def cut(self, target, tool):
        if not self.tbm.booleanOperation(target, tool, CUT):
            raise RuntimeError('Solid cut failed')
        return target

    def union(self, bodies):
        total = bodies[0]
        for body in bodies[1:]:
            self.join(total, body)
        return total

    def copy(self, body):
        return self.tbm.copy(body)


# ---------------------------------------------------------------- Fusion helpers
def new_component(parent, name, transform=None):
    occurrence = parent.occurrences.addNewComponent(transform or adsk.core.Matrix3D.create())
    occurrence.component.name = name
    return occurrence


def add_bodies(component, named_bodies):
    base = component.features.baseFeatures.add()
    base.startEdit()
    for name, body in named_bodies:
        component.bRepBodies.add(body, base).name = name
    base.finishEdit()
    base.name = 'generated'
    return {body.name: body for body in component.bRepBodies}


def frame_matrix(origin, x, y, z):
    matrix = adsk.core.Matrix3D.create()
    matrix.setWithCoordinateSystem(P(origin), D(x), D(y), D(z))
    return matrix


def proxies(occurrence, prefix=''):
    found = [b.createForAssemblyContext(occurrence) for b in occurrence.component.bRepBodies
             if b.name.startswith(prefix) and b.isLightBulbOn]
    for child in occurrence.childOccurrences:
        found += [b.createForAssemblyContext(child) for b in child.component.bRepBodies if b.name.startswith(prefix)]
    return found


# ---------------------------------------------------------------- stage 1 + 6 parameters
def stage1_parameters(design):
    user = design.userParameters
    for name, expression, units, comment in PARAMS:
        if user.itemByName(name) is None:
            user.add(name, adsk.core.ValueInput.createByString(expression), units, comment)
    migrate_parameters(user)
    applied, extra = stage6_measurements(user)
    values = {}
    for name, _, units, _ in PARAMS:
        value = user.itemByName(name).value
        values[name] = value * 10 if units == 'mm' else value
    return values, applied, extra


# Existing documents keep their stored expressions; restructured chains are rewritten here, in an order that never
# creates a circular reference (rod_cut_len becomes a constant before cage_edge starts to depend on it).
MIGRATIONS = ('rod_cut_len', 'cage_edge', 'cage_vertex_r', 'cage_outer_dia')


def migrate_parameters(user):
    spec = {name: (expression, comment) for name, expression, _, comment in PARAMS}
    for name in MIGRATIONS:
        prm = user.itemByName(name)
        expression, comment = spec[name]
        if prm.expression != expression:
            prm.expression = expression
        prm.comment = comment


def stage6_measurements(user):
    """vendor_specs.json, then measurements.json (measured values win):
    {"parameters": {"name": "value with units" | null}, "masses_g": {...}}."""
    expressions, masses, origin = {}, {}, {}
    for label, filename in (('vendor', 'vendor_specs.json'), ('measured', 'measurements.json'), ('coupon-selected', 'fit_results.json')):
        path = os.path.join(HERE, filename)
        if not os.path.exists(path):
            continue
        data = json.load(open(path))
        for name, expression in (data.get('parameters') or {}).items():
            if expression not in (None, ''):
                expressions[name], origin[name] = expression, label
        for name, value in (data.get('masses_g') or {}).items():
            if value not in (None, ''):
                masses[name], origin[name] = value, label
    applied = []
    for name, expression in expressions.items():
        parameter = user.itemByName(name)
        if parameter is None:
            continue
        if parameter.expression != expression:
            parameter.expression = expression
        applied.append(f'{name}={expression} [{origin[name]}]')
    masses['_origin'] = origin
    return applied, masses


# ---------------------------------------------------------------- stage 2 aircraft envelope
def stage2_aircraft(root, s, p):
    occurrence = new_component(root, GENERATED[0])
    half = p['motor_diag'] / 2
    motors = [(half * math.cos(math.radians(a)), half * math.sin(math.radians(a)), label)
              for a, label in [(45, 'FR'), (135, 'FL'), (225, 'RL'), (315, 'RR')]]
    frame = [s.aabox((-p['stack_w'] / 2, -p['stack_w'] / 2, -p['frame_t']), (p['stack_w'] / 2, p['stack_w'] / 2, 0))]
    for x, y, _ in motors:
        along = unit((x, y, 0))
        frame.append(s.box((x / 2, y / 2, -p['frame_t'] / 2), along, cross((0, 0, 1), along), half + p['arm_w'], p['arm_w'], p['frame_t']))
    bodies = [('frame_plate_PLACEHOLDER', s.union(frame)),
              ('motors_x4_PLACEHOLDER', s.union([s.cyl((x, y, 0), (x, y, p['motor_h']), p['motor_od']) for x, y, _ in motors]))]
    for x, y, label in motors:
        bodies.append((f'PROP_DISK_{label}_keepout', s.cyl((x, y, p['prop_z']), (x, y, p['prop_z'] + p['prop_disk_h']), p['prop_dia'])))
    inner = p['stack_w'] - 4
    bodies.append(('stack_AIO_PLACEHOLDER', s.aabox((-inner / 2, -inner / 2, 0), (inner / 2, inner / 2, p['stack_h']))))
    c = p['cam_size'] / 2
    bodies.append(('camera_PLACEHOLDER', s.aabox((-c, p['cam_y'] - c, p['cam_z'] - c), (c, p['cam_y'] + c, p['cam_z'] + c))))
    apex, axis = camera_axis(p)
    length = p['cage_vertex_r'] - p['cam_y']
    # Field-of-view marker, clipped to the cage sphere so the wide (160 deg) cone never extends past the cage.
    # Analysis only: hidden by default, massless, never exported.
    view = s.cone(apex, add(apex, mul(axis, length)), length * math.tan(p['cam_hfov'] / 2))
    s.tbm.booleanOperation(view, s.tbm.createSphere(P((0, 0, 0)), (p['cage_vertex_r'] - 6) / 10), adsk.fusion.BooleanTypes.IntersectionBooleanType)
    bodies.append(('CAMERA_VIEW_cone', view))
    for x, y, z, h in antenna_envelope(p):
        bodies.append(('ANTENNA_element_PLACEHOLDER', s.cyl((x, y, z), (x, y, z + h), p['antenna_d'])))
    carrier_bottom = -p['frame_t'] - p['carrier_t']
    q = p['frame_hole_pitch'] / 2
    nut = 4.0 / math.cos(math.radians(30))                # M2 nut across corners (ISO 4032, 4 mm AF)
    bodies.append(('M2_nut_and_tail_x4_envelope', s.union([s.cyl((sx * q, sy * q, carrier_bottom - 2.6), (sx * q, sy * q, carrier_bottom), nut)
                                                           for sx in (-1, 1) for sy in (-1, 1)])))
    top = carrier_bottom - p['battery_gap'] - p['battery_shield_t']   # pack sits under pad + shield
    # Nuts move with the frame; the foam pad stays on the carrier. Include lateral slot travel.
    nut_travel_x = p['adj_y'] if p.get('arm_axis', 'x') == 'y' else 0
    pad_w = 2 * (q - nut / 2 - nut_travel_x - 0.5)
    if pad_w <= 0:
        raise RuntimeError('No foam-pad width remains after frame/nut adjustment travel')
    pad = s.aabox((-pad_w / 2, -max(p['batt450_l'], p['batt1100_l']) / 2, carrier_bottom - p['battery_gap']), (pad_w / 2, max(p['batt450_l'], p['batt1100_l']) / 2, carrier_bottom))
    if p.get('arm_axis') == 'y':
        # The arm nuts also live below the carrier. Model their full adjustment
        # envelope and hand-cut foam notches instead of omitting them from fit checks.
        arm_holes = (p['carrier_span']/2-16+5, p['carrier_span']/2-16+10)
        bodies.append(('M2_nut_arm_x4_envelope', s.union([
            s.cyl((0, sign*y, carrier_bottom-2.6), (0, sign*y, carrier_bottom), nut)
            for sign in (-1,1) for y in arm_holes])))
        relief_half_width = nut/2+.5
        for sign in (-1,1):
            y0 = min(sign*y for y in arm_holes)-p['adj_x']-relief_half_width
            y1 = max(sign*y for y in arm_holes)+p['adj_x']+relief_half_width
            s.cut(pad, s.aabox((-relief_half_width,y0,carrier_bottom-p['battery_gap']-1),
                              (relief_half_width,y1,carrier_bottom+1)))
    bodies.append(('BATTERY_PAD_foam', pad))
    for tag in ('450', '1100'):
        l, w, h = p[f'batt{tag}_l'], p[f'batt{tag}_w'], p[f'batt{tag}_h']
        bodies.append((f'battery_{tag}mAh_PLACEHOLDER', s.aabox((-w / 2, -l / 2, top - h), (w / 2, l / 2, top))))
    result = add_bodies(occurrence.component, bodies)
    result['battery_1100mAh_PLACEHOLDER'].isLightBulbOn = False
    result['CAMERA_VIEW_cone'].opacity = 0.12
    result['CAMERA_VIEW_cone'].isLightBulbOn = False   # show it from the browser when checking the view
    for name, body in result.items():
        if name.startswith('PROP_DISK'):
            body.opacity = 0.45
    return occurrence


def antenna_envelope(p):
    """(x, y, z_base, height) of the VTX antenna element: rear carrier sleeve (P1A) or frame top (P1B)."""
    if p.get('arm_axis', 'x') == 'x':
        return [(0, -(p['carrier_len'] / 2 + 4), -p['frame_t'], p['antenna_len'])]
    return [(0, -18, p['frame_column_h'], p['antenna_len'])]


def camera_axis(p):
    apex = (0, p['cam_y'] + p['cam_size'] / 2, p['cam_z'])
    return apex, (0, math.cos(p['cam_tilt']), math.sin(p['cam_tilt']))


# ---------------------------------------------------------------- stage 3 cage skeleton
def truncated_icosahedron():
    """60 unit vertices with a pentagon centred on +Z, plus the 90 edges."""
    phi = (1 + 5 ** 0.5) / 2
    ico = []
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            ico += [(0, s1, s2 * phi), (s1, s2 * phi, 0), (s2 * phi, 0, s1)]
    vertices = []
    for i, j in itertools.combinations(range(12), 2):
        if abs(math.dist(ico[i], ico[j]) - 2) < 1e-9:
            for f in (1 / 3, 2 / 3):
                vertices.append(add(ico[i], mul(sub(ico[j], ico[i]), f)))
    a, b = unit(ico[0]), (0, 0, 1)
    k = cross(a, b)
    s, c = norm(k), dot(a, b)
    k = mul(k, 1 / s)
    def rotate(v):
        return add(add(mul(v, c), mul(cross(k, v), s)), mul(k, dot(k, v) * (1 - c)))
    vertices = [rotate(v) for v in vertices]
    edge = min(math.dist(u, v) for u, v in itertools.combinations(vertices, 2))
    edges = [(i, j) for i, j in itertools.combinations(range(60), 2) if abs(math.dist(vertices[i], vertices[j]) - edge) < 1e-6]
    return vertices, edges


def cage_graph(p):
    unit_vertices, edges = truncated_icosahedron()
    scale = p['cage_vertex_r'] / norm(unit_vertices[0])
    hubs = [mul(v, scale) for v in unit_vertices]
    top, bottom = max(v[2] for v in hubs), min(v[2] for v in hubs)
    points = hubs + [(0, 0, p['cage_vertex_r']), (0, 0, -p['cage_vertex_r'])]
    pole_edges = [(60, i) for i, v in enumerate(hubs) if v[2] > top - 1e-6] + [(61, i) for i, v in enumerate(hubs) if v[2] < bottom + 1e-6]
    # Support mounts: the two equator-crossing edges whose midpoints lie on +X and -X.
    mounts = {}
    for i, j in edges:
        mid = mul(add(points[i], points[j]), 0.5)
        if points[i][2] * points[j][2] < 0 and abs(mid[1]) < 1e-6:
            mounts[i] = mounts[j] = 1 if mid[0] > 0 else -1
    if len(mounts) != 4:
        raise RuntimeError(f'Expected four support-mount hubs on the X axis, found {len(mounts)}')
    return points, edges, pole_edges, mounts


def stage3_cage(root, s, p, graph):
    points, edges, pole_edges, _ = graph
    occurrence = new_component(root, GENERATED[1])
    component = occurrence.component
    inset = p['hub_arm_len'] - p['socket_depth'] + p['rod_end_gap']
    def rod(i, j):
        a, b = points[i], points[j]
        u = unit(sub(b, a))
        return s.cyl(add(a, mul(u, inset)), sub(b, mul(u, inset)), p['rod_dia']), math.dist(a, b) - 2 * inset
    edge_rods = [rod(i, j) for i, j in edges]
    pole_rods = [rod(i, j) for i, j in pole_edges]
    bodies = [(f'rods_edge_x{len(edge_rods)}_cut_{edge_rods[0][1]:.2f}mm', s.union([r for r, _ in edge_rods])),
              (f'rods_pole_x{len(pole_rods)}_cut_{pole_rods[0][1]:.2f}mm', s.union([r for r, _ in pole_rods])),
              ('HUB_ENVELOPE_spheres', s.union([s.tbm.createSphere(P(v), p['hub_core_r'] / 10) for v in points]))]
    result = add_bodies(component, bodies)
    result['HUB_ENVELOPE_spheres'].isLightBulbOn = False
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = 'cage_wireframe (hub centre lines)'
    sketch.isComputeDeferred = True
    for i, j in edges + pole_edges:
        sketch.sketchCurves.sketchLines.addByTwoPoints(P(points[i]), P(points[j]))
    sketch.isComputeDeferred = False
    sketch.isVisible = False   # reference only (assembly map); show it from the browser
    return occurrence, {'edge_rods': len(edge_rods), 'edge_rod_cut_mm': round(edge_rods[0][1], 2),
                        'pole_rods': len(pole_rods), 'pole_rod_cut_mm': round(pole_rods[0][1], 2),
                        'total_rod_mm': round(sum(l for _, l in edge_rods + pole_rods), 1)}


# ---------------------------------------------------------------- stage 4 hubs and fit strip
def hub_frames(p, graph):
    """Local frame per node: +Z points to the cage centre, so the flat outer face is the print bed."""
    points, edges, pole_edges, mounts = graph
    neighbours = {i: [] for i in range(len(points))}
    for i, j in edges + pole_edges:
        neighbours[i].append(j)
        neighbours[j].append(i)
    frames = []
    for index, point in enumerate(points):
        z = mul(unit(point), -1)
        arms = [unit(sub(points[j], point)) for j in neighbours[index]]
        if len(arms) == 3:  # hexagon-hexagon edge: 120 degrees to both others
            reference = max(arms, key=lambda a: -max(abs(math.degrees(math.acos(max(-1, min(1, dot(a, b))))) - 120) for b in arms if b is not a))
        elif len(arms) == 4:  # pole arm
            reference = arms[[j >= 60 for j in neighbours[index]].index(True)]
        else:
            reference = arms[0]
        x = unit(sub(reference, mul(z, dot(reference, z))))
        y = cross(z, x)
        local = lambda v: (round(dot(v, x), 3) + 0.0, round(dot(v, y), 3) + 0.0, round(dot(v, z), 3) + 0.0)
        boss = local((-mounts[index], 0, 0)) if index in mounts else None
        key = (tuple(sorted(local(a) for a in arms)), boss)
        frames.append({'index': index, 'origin': point, 'x': x, 'y': y, 'z': z, 'key': key})
    return frames


def hub_body(s, p, arms, boss):
    bed = -p['hub_core_r']
    od, length = p['hub_arm_od'], p['hub_arm_len']
    body = s.cyl((0, 0, bed), (0, 0, od / 2), 2 * p['hub_body_r'])
    for d in arms:
        tip = mul(d, length)
        s.join(body, s.cyl((0, 0, 0), tip, od))
        across = unit(cross((0, 0, 1), d))
        down = cross(d, across)  # perpendicular to the arm, pointing toward the bed
        if down[2] > 0:
            down = mul(down, -1)
        s.join(body, s.box(add(mul(tip, 0.5), mul(down, 5)), d, across, length, p['hub_keel_w'], 10))  # keel: axis down to bed
    if boss:
        end = mul(boss, p['mount_boss_len'])
        s.join(body, s.cyl((0, 0, 0), end, p['mount_boss_od']))
        across = unit(cross((0, 0, 1), boss))
        down = cross(boss, across)
        if down[2] > 0:
            down = mul(down, -1)
        s.join(body, s.box(add(mul(end, 0.5), mul(down, 5)), boss, across, p['mount_boss_len'], p['mount_boss_od'], 10))
    for d in arms:
        tip = mul(d, length)
        s.cut(body, s.cyl(sub(tip, mul(d, p['socket_depth'])), add(tip, mul(d, 0.5)), p['rod_dia'] + 2 * p['rod_bore_clear']))
    if boss:
        end = mul(boss, p['mount_boss_len'])
        s.cut(body, s.cyl(sub(end, mul(boss, 5)), add(end, mul(boss, 0.5)), p['m2_tap']))
    s.cut(body, s.aabox((-40, -40, bed - 40), (40, 40, bed)))
    return body


def stage4_hubs(root, s, p, graph, frames):
    holder = new_component(root, GENERATED[2])
    groups = {}
    for frame in frames:
        groups.setdefault(frame['key'], []).append(frame)
    parts = []
    mirror_names = iter('ABCD')
    used = set()
    for key, members in sorted(groups.items(), key=lambda kv: (len(kv[0][0]), kv[0][1] is not None, -len(kv[1]))):
        arms, boss = key
        if boss:
            name = f'hub_{len(arms)}way_mount_{next(mirror_names)}'
        else:
            name = {3: 'hub_3way', 4: 'hub_4way', 5: 'hub_pole_5way'}[len(arms)]
        if name in used:
            name += f'_variant{len(used)}'
        used.add(name)
        body = hub_body(s, p, arms, boss)
        first = members[0]
        occurrence = new_component(holder.component, name, frame_matrix(first['origin'], first['x'], first['y'], first['z']))
        native = add_bodies(occurrence.component, [(name, body)])[name]
        for frame in members[1:]:
            holder.component.occurrences.addExistingComponent(
                occurrence.component, frame_matrix(frame['origin'], frame['x'], frame['y'], frame['z']))
        parts.append({'name': name, 'qty': len(members), 'body': native,
                      'volume_mm3': native.volume * 1000, 'height_mm': (native.boundingBox.maxPoint.z - native.boundingBox.minPoint.z) * 10})
    return holder, parts


def stage4_fit_strip(root, s, p):
    """Six hub-style socket stubs (0.05-0.30 mm per side, marked with 1-6 dimples) plus three M2 pilot holes."""
    transform = adsk.core.Matrix3D.create()
    transform.translation = D((0, -20, 0))  # 200 mm in front of the cage
    occurrence = new_component(root, GENERATED[3], transform)
    axis_z = p['hub_core_r']
    top = axis_z + p['hub_arm_od'] / 2
    pitch = 8
    width = pitch * len(CLEARANCES) + 2
    body = s.aabox((0, -10, 0), (width, 0, top))
    for k, clearance in enumerate(CLEARANCES):
        x = 5 + k * pitch
        s.join(body, s.cyl((x, -1, axis_z), (x, p['hub_arm_len'], axis_z), p['hub_arm_od']))
        s.join(body, s.aabox((x - p['hub_arm_od'] / 2, -1, 0), (x + p['hub_arm_od'] / 2, p['hub_arm_len'], axis_z)))
    block = (width, -10, 0), (width + 16, 0, 7)
    s.join(body, s.aabox(*block))
    for k, clearance in enumerate(CLEARANCES):
        x = 5 + k * pitch
        s.cut(body, s.cyl((x, p['hub_arm_len'] - p['socket_depth'], axis_z), (x, p['hub_arm_len'] + 0.5, axis_z), p['rod_dia'] + 2 * clearance))
        for dot_index in range(k + 1):
            s.cut(body, s.cyl((x - 2.4 + (dot_index % 3) * 2.4, -3 - (dot_index // 3) * 2.4, top - 0.4), (x - 2.4 + (dot_index % 3) * 2.4, -3 - (dot_index // 3) * 2.4, top + 1), 1.0))
    for k, pilot in enumerate(TAP_PILOTS):
        x = width + 4 + k * 4
        s.cut(body, s.cyl((x, -5, 2), (x, -5, 8), pilot))
    name = 'socket_fit_strip'
    native = add_bodies(occurrence.component, [(name, body)])[name]
    return occurrence, {'name': name, 'qty': 1, 'body': native, 'volume_mm3': native.volume * 1000,
                        'height_mm': (native.boundingBox.maxPoint.z - native.boundingBox.minPoint.z) * 10}


# ---------------------------------------------------------------- stage 5 carrier and supports
def stage4_rod_jig(root, s, p):
    """Two rod grooves with an end stop and a blade slot at each cut length (edge and pole rods)."""
    transform = adsk.core.Matrix3D.create()
    transform.translation = D((0, -24, 0))  # beside the fit strip
    occurrence = new_component(root, GENERATED[5], transform)
    lengths = [p['rod_cut_len'], p['pole_rod_cut_len']]
    stop, tail, height = 4.0, 12.0, 5.0
    width = 8.0 * len(lengths) + 4
    body = s.aabox((-stop, 0, 0), (max(lengths) + tail, width, height))
    groove = p['rod_dia'] + 0.25
    for k, length in enumerate(lengths):
        y = 6 + k * 8
        # Groove from the stop wall (x = 0) to the far end; the rod rests at mid-depth.
        s.cut(body, s.aabox((0, y - groove / 2, height - p['rod_dia'] * 0.75), (max(lengths) + tail + 1, y + groove / 2, height + 1)))
        # Blade slot across this groove at the cut length.
        s.cut(body, s.aabox((length, y - 3, height - 2.5), (length + 0.6, y + 3, height + 1)))
        # Count marks: 1 dimple = edge rods (x90), 2 = pole rods (x10).
        for m in range(k + 1):
            s.cut(body, s.cyl((-stop / 2, y - 1.5 + m * 3, height - 0.4), (-stop / 2, y - 1.5 + m * 3, height + 1), 1.2))
    name = 'rod_cutting_jig'
    native = add_bodies(occurrence.component, [(name, body)])[name]
    return occurrence, {'name': name, 'qty': 1, 'body': native, 'volume_mm3': native.volume * 1000,
                        'height_mm': (native.boundingBox.maxPoint.z - native.boundingBox.minPoint.z) * 10}


def carrier_geometry(s, p, arm_axis='x'):
    """Carrier plate (print flat). arm_axis 'x' (P1A): side bar and arm slots along X, frame slots along Y,
    rear antenna sleeve. arm_axis 'y' (P1B): bar and arm slots along Y, frame slots along X, antenna on the
    frame top instead. Battery-strap slots always sit beside the pack (pack long axis = Y)."""
    def r(pt):   # arm-related features are drawn for X arms and rotated +90 degrees for Y arms
        return pt if arm_axis == 'x' else (-pt[1], pt[0], pt[2])
    top, bottom = -p['frame_t'], -p['frame_t'] - p['carrier_t']
    half_span = p['carrier_span'] / 2
    x0 = half_span - 16                                   # support arm overlaps the carrier tip by 16 mm
    holes_x = (x0 + 5, x0 + 10)
    bar_lo, bar_hi = r((-half_span, -p['carrier_bar_w'] / 2, bottom)), r((half_span, p['carrier_bar_w'] / 2, top))
    carrier = s.union([s.aabox((-p['carrier_core_w'] / 2, -p['carrier_len'] / 2, bottom), (p['carrier_core_w'] / 2, p['carrier_len'] / 2, top)),
                       s.aabox(tuple(min(a, b) for a, b in zip(bar_lo, bar_hi)), tuple(max(a, b) for a, b in zip(bar_lo, bar_hi)))])
    q = p['frame_hole_pitch'] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            if arm_axis == 'x':   # frame slides perpendicular to the arms
                a, b = (sx * q, sy * q - p['adj_y'], 0), (sx * q, sy * q + p['adj_y'], 0)
            else:
                a, b = (sx * q - p['adj_y'], sy * q, 0), (sx * q + p['adj_y'], sy * q, 0)
            s.cut(carrier, s.slot(a, b, p['m2_clear'], bottom - 1, top + 1))
        s.cut(carrier, s.slot(r((sx * (holes_x[0] - p['adj_x']), 0, 0)), r((sx * (holes_x[1] + p['adj_x']), 0, 0)), p['m2_clear'], bottom - 1, top + 1))
        # Beside the widest pack, and outboard of the frame-screw slots (including their travel) with a 1.5 mm web.
        frame_reach = q + (p['adj_y'] if arm_axis == 'y' else 0)
        strap_x = sx * max(max(p['batt450_w'], p['batt1100_w']) / 2 + p['strap_slot_t'] / 2 + 1,
                           frame_reach + p['m2_clear'] / 2 + p['strap_slot_t'] / 2 + 1.5)
        if abs(strap_x) + p['strap_slot_t'] / 2 > p['carrier_core_w'] / 2 - 1.5:
            raise RuntimeError('Strap slots do not fit the carrier; widen carrier_core_w')
        s.cut(carrier, s.aabox((strap_x - p['strap_slot_t'] / 2, -(p['strap_w'] + 1) / 2, bottom - 1), (strap_x + p['strap_slot_t'] / 2, (p['strap_w'] + 1) / 2, top + 1)))
    # Central lightening window inside the frame-screw slots (the frame bottom plate covers it).
    wx = q - p['m2_clear'] / 2 - 2 - (p['adj_y'] if arm_axis == 'y' else 0)
    wy = min(p['carrier_len'] / 2 - 5, q - p['m2_clear'] / 2 - 2 if arm_axis == 'y' else p['carrier_len'] / 2 - 5)
    if wx > 3 and wy > 3:
        s.cut(carrier, s.aabox((-wx, -wy, bottom - 1), (wx, wy, top + 1)))
    if arm_axis == 'x':
        # Rear antenna sleeve: holds the VTX antenna element upright behind the frame, clear of the props.
        ay = p['carrier_len'] / 2 + 4
        sleeve_od = p['antenna_d'] + 2.4
        s.join(carrier, s.aabox((-sleeve_od / 2, -ay, bottom), (sleeve_od / 2, -p['carrier_len'] / 2 + 1, top)))
        s.join(carrier, s.cyl((0, -ay, bottom), (0, -ay, top + 6), sleeve_od))
        s.cut(carrier, s.cyl((0, -ay, bottom - 1), (0, -ay, top + 7), p['antenna_d'] + 0.3))
    return carrier, top, bottom, x0, holes_x


def nut_shield_geometry(s, p):
    """Thin printed plate between the foam pad and the pack, as wide/long as the larger pack + 1 mm. The strap
    wraps pack and shield together. Print flat."""
    carrier_bottom = -p['frame_t'] - p['carrier_t']
    z1 = carrier_bottom - p['battery_gap']
    w = max(p['batt450_w'], p['batt1100_w']) + 1
    l = max(p['batt450_l'], p['batt1100_l']) + 1
    return s.aabox((-w / 2, -l / 2, z1 - p['battery_shield_t']), (w / 2, l / 2, z1))


def support_arm_geometry(s, p, x0, holes_x, top, end_x):
    """+X support arm from the carrier tip to an end flange whose outer face is at end_x. The -X copy is
    the same part rotated 180 degrees about Z. Print with the arm flat and the flange standing."""
    arm_top = top + p['support_h']
    flange_x0 = end_x - p['flange_t']
    w = p['support_w'] / 2
    arm = s.union([s.aabox((x0, -w, top), (end_x, w, arm_top)),
                   s.aabox((flange_x0, -5, top), (end_x, 5, top + p['flange_h']))])
    flange_z = (top + 5, top + p['flange_h'] - 4)
    for hx in holes_x:
        s.cut(arm, s.cyl((hx, 0, top - 1), (hx, 0, arm_top + 1), p['m2_clear']))
    for fz in flange_z:
        s.cut(arm, s.cyl((flange_x0 - 1, 0, fz), (end_x + 1, 0, fz), p['m2_clear']))
    return arm, flange_z, flange_x0


def stage5_carrier(root, s, p, graph):
    points, _, _, mounts = graph
    holder = new_component(root, GENERATED[4])
    plus = [points[i] for i, side in mounts.items() if side > 0]
    hub_x = plus[0][0]
    face_x = hub_x - p['mount_boss_len']                  # outer bracket face meets the boss ends
    y_b, z_b = abs(plus[0][1]), abs(plus[0][2])
    carrier, top, bottom, x0, holes_x = carrier_geometry(s, p)
    arm, flange_z, flange_x0 = support_arm_geometry(s, p, x0, holes_x, top, face_x - p['bracket_t'])

    # X bracket: both edge diagonals, so one part fits the +X and the mirrored -X mount. Print flat.
    x_mid = face_x - p['bracket_t'] / 2
    span = 2 * math.hypot(y_b, z_b) + p['bracket_bar_w']
    bracket = s.union([s.box((x_mid, 0, 0), (0, y_b, z_b), (1, 0, 0), span, p['bracket_t'], p['bracket_bar_w']),
                       s.box((x_mid, 0, 0), (0, -y_b, z_b), (1, 0, 0), span, p['bracket_t'], p['bracket_bar_w']),
                       s.aabox((face_x - p['bracket_t'], -5, top - 1), (face_x, 5, top + p['flange_h']))])
    for sy in (-1, 1):
        for sz in (-1, 1):
            s.cut(bracket, s.cyl((face_x - p['bracket_t'] - 1, sy * y_b, sz * z_b), (face_x + 1, sy * y_b, sz * z_b), p['m2_clear']))
    for fz in flange_z:
        s.cut(bracket, s.cyl((face_x - p['bracket_t'] - 1, 0, fz), (face_x + 1, 0, fz), p['m2_clear']))

    carrier_occ = new_component(holder.component, 'carrier_plate')
    carrier_body = add_bodies(carrier_occ.component, [('carrier_plate', carrier)])['carrier_plate']
    shield_occ = new_component(holder.component, 'nut_shield_plate')
    shield_body = add_bodies(shield_occ.component, [('nut_shield_plate', nut_shield_geometry(s, p))])['nut_shield_plate']
    turn = adsk.core.Matrix3D.create()
    turn.setToRotation(math.pi, D((0, 0, 1)), P((0, 0, 0)))
    arm_occ = new_component(holder.component, 'support_arm')
    arm_body = add_bodies(arm_occ.component, [('support_arm', arm)])['support_arm']
    holder.component.occurrences.addExistingComponent(arm_occ.component, turn)
    bracket_occ = new_component(holder.component, 'x_bracket')
    bracket_body = add_bodies(bracket_occ.component, [('x_bracket', bracket)])['x_bracket']
    # The -X bracket: rotate 180 degrees about Z (the X shape covers both edge diagonals).
    holder.component.occurrences.addExistingComponent(bracket_occ.component, turn)

    def info(name, body, qty):
        return {'name': name, 'qty': qty, 'body': body, 'volume_mm3': body.volume * 1000}
    return holder, [info('carrier_plate', carrier_body, 1), info('nut_shield_plate', shield_body, 1), info('support_arm', arm_body, 2), info('x_bracket', bracket_body, 2)], {
        'mount_hub_x_mm': round(hub_x, 2), 'bracket_face_x_mm': round(face_x, 2),
        'mount_hubs_yz_mm': (round(y_b, 2), round(z_b, 2)), 'support_arm_len_mm': round(face_x - p['bracket_t'] - x0, 1),
        'fore_aft_travel_mm': f'+-{p["adj_y"]:.1f}', 'lateral_travel_mm': f'+-{p["adj_x"]:.1f}',
        'm2_screws': '4 frame-carrier, 4 arm-carrier, 4 arm-bracket, 4 bracket-boss (16 total)'}


# ---------------------------------------------------------------- reference meshes, exports, report
def reference_hubs(root):
    if not os.path.isdir(REFERENCE_DIR):
        return 'skipped (reference folder not found)'
    holder = new_component(root, GENERATED[6])
    for index, name in enumerate(REFERENCE_HUBS):
        child = holder.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        child.component.name = name.replace('.STL', '') + ' (original, 3 mm rod)'
        base = child.component.features.baseFeatures.add()
        base.startEdit()
        mesh = child.component.meshBodies.add(os.path.join(REFERENCE_DIR, name), adsk.fusion.MeshUnits.MillimeterMeshUnit, base).item(0)
        base.finishEdit()
        box = mesh.boundingBox
        transform = adsk.core.Matrix3D.create()
        transform.translation = D((18 + index * 4 - (box.minPoint.x + box.maxPoint.x) / 2,
                                   -(box.minPoint.y + box.maxPoint.y) / 2, -(box.minPoint.z + box.maxPoint.z) / 2))
        # Occurrence transforms only take effect when set at creation in this parametric design.
        holder.component.occurrences.addExistingComponent(child.component, transform)
        child.deleteMe()
    holder.isLightBulbOn = False
    return 'loaded (hidden)'


ENVELOPE_PREFIXES = ('PROP_DISK', 'CAMERA_VIEW', 'battery_', 'frame_plate', 'motors_', 'stack_', 'camera_', 'ANTENNA',
                     'BATTERY_PAD', 'M2_nut', 'HUB_ENVELOPE')


def apply_materials(design, p):
    """PETG for printed parts, carbon for rods, stainless for pins, chrome steel for bearings and a near-massless
    material for analysis envelopes, so Fusion's own mass properties describe the printed structure."""
    app = adsk.core.Application.get()
    library = app.materialLibraries.itemByName('Fusion Material Library')
    def custom(name, base, density_g_cc):
        material = design.materials.itemByName(name)
        if material is None:
            material = design.materials.addByCopy(library.materials.itemByName(base), name)
        prop = material.materialProperties.itemById('structural_Density')
        prop.value = density_g_cc * 1000                   # kg/m^3
        return material
    petg = custom('PETG (project)', 'PET Plastic', p['petg_density'])
    carbon = custom('Carbon rod (project)', 'PET Plastic', p['rod_density'])
    envelope = custom('Analysis envelope (massless)', 'PET Plastic', 0.000001)
    steel = library.materials.itemByName('Stainless Steel AISI 304')
    bearing = library.materials.itemByName('Stainless Steel, 440C')
    counts = {}
    for component in design.allComponents:
        for body in component.bRepBodies:
            name = body.name
            if component.name in ('Socket fit strip (print first)', 'Rod cutting jig', 'Gimbal test fixtures'):
                material = envelope
            elif name.startswith('rods_'):
                material = carbon
            elif name.startswith(ENVELOPE_PREFIXES):
                material = envelope
            elif name.startswith('pin_'):
                material = steel
            elif name.startswith('MR52ZZ'):
                material = bearing
            else:
                material = petg
            if body.material is None or body.material.name != material.name:
                body.material = material
            counts[material.name] = counts.get(material.name, 0) + 1
    # Hidden reference meshes and print fixtures are not aircraft mass. Keep the originals intact.
    for component in design.allComponents:
        for mesh in component.meshBodies:
            if 'original, 3 mm rod' in component.name:
                mesh.material = envelope
        if component.name in ('Socket fit strip (print first)', 'Rod cutting jig', 'Gimbal test fixtures'):
            for body in component.bRepBodies:
                body.material = envelope
    return counts


def color_hubs(design, rgb=(245, 245, 245)):
    """Show every cage hub (the rod joints) in white."""
    library = adsk.core.Application.get().materialLibraries.itemByName('Fusion Appearance Library')
    appearance = design.appearances.itemByName('Hub (white)')
    if appearance is None:
        appearance = design.appearances.addByCopy(library.appearances.itemByName('Plastic - Glossy (Red)'), 'Hub (white)')
        for prop in appearance.appearanceProperties:
            if isinstance(prop, adsk.core.ColorProperty) and prop.value is not None:
                prop.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
    count = 0
    for component in design.allComponents:
        for body in component.bRepBodies:
            if body.name.startswith('hub_'):
                body.appearance = appearance
                count += 1
    return count


def print_mass(part, p):
    """(solid g, estimated printed g): walls/skins of print_wall over the surface plus print_infill inside."""
    volume = part['body'].volume * 1000
    shell = min(volume, part['body'].area * 100 * p['print_wall'])
    return volume / 1000 * p['petg_density'], (shell + p['print_infill'] * (volume - shell)) / 1000 * p['petg_density']


def export_stl(parts, subfolder='exports'):
    folder = os.path.join(HERE, subfolder)
    os.makedirs(folder, exist_ok=True)
    manager = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct).exportManager
    written = []
    for part in parts:
        path = os.path.join(folder, part['name'] + '.stl')
        options = manager.createSTLExportOptions(part['body'], path)
        options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        if part['body'].lumps.count != 1:
            raise RuntimeError('Disconnected printable part: ' + part['name'])
        if not manager.execute(options):
            raise RuntimeError('STL export failed: ' + part['name'])
        written.append(os.path.basename(path))
    expected = set(written)
    stale = sorted(f for f in os.listdir(folder) if f.lower().endswith('.stl') and f not in expected)
    if stale:
        raise RuntimeError('Stale STL exports require explicit review: ' + str(stale))
    manifest = {'document': adsk.core.Application.get().activeDocument.name, 'status': 'vendor/provisional CAD; physical validation pending',
                'sources': {f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('build_p1a.py','build_p1b.py','validation.py','vendor_specs.json','measurements.json','fit_results.json')},
                'parts': [{'name': part['name'], 'qty': part['qty'], 'native_volume_mm3': part['body'].volume * 1000,
                           'native_lumps': part['body'].lumps.count, 'sha256': hashlib.sha256(open(os.path.join(folder, part['name']+'.stl'), 'rb').read()).hexdigest()} for part in parts]}
    with open(os.path.join(folder, 'manifest.json'), 'w') as output:
        json.dump(manifest, output, indent=2)
    return written


def report(p, applied, masses, occ, cage_info, graph, parts, support_info, exported):
    measure = adsk.core.Application.get().measureManager
    aircraft, cage, hubs, supports = occ
    def gap(a, b):
        return min(measure.measureMinimumDistance(x, y).value * 10 for x in a for y in b)
    structure = proxies(cage, 'rods_') + proxies(hubs)
    support_bodies = [b for b in proxies(supports) if 'carrier' not in b.assemblyContext.component.name]
    props = proxies(aircraft, 'PROP_DISK')
    batteries = [b.createForAssemblyContext(aircraft) for b in aircraft.component.bRepBodies if b.name.startswith('battery_')]
    boxes = [b.boundingBox for b in structure]
    span = max(max(b.maxPoint.__getattribute__(a) for b in boxes) - min(b.minPoint.__getattribute__(a) for b in boxes) for a in 'xyz') * 10
    points = graph[0]
    apex, axis = camera_axis(p)
    in_view = sum(1 for v in points if math.acos(max(-1, min(1, dot(unit(sub(v, apex)), axis)))) < p['cam_hfov'] / 2)
    print('Values applied (vendor specs, then measurements):', applied or 'none')
    print('Cage:', cage_info, f'| span {span:.2f} mm (target 245-250)')
    print(f'Clearance (nominal, no flex): prop disks to cage {gap(props, structure):.2f} mm; prop disks to supports {gap(props, support_bodies):.2f} mm')
    print(f'Clearance: batteries (450 and 1100) to cage {gap(batteries, structure):.2f} mm; to support arms/brackets {gap(batteries, support_bodies):.2f} mm')
    print(f'Camera view: {in_view} of {len(points)} hub nodes inside the {math.degrees(p["cam_hfov"]):.0f} deg cone (rods also cross the view)')
    rod_g = sum(b.volume for b in cage.component.bRepBodies if b.name.startswith('rods_')) * p['rod_density']
    print('Printed parts (PETG): solid upper bound / estimated at walls + infill:')
    printed_g = printed_est = 0.0
    for part in parts:
        solid, est = print_mass(part, p)
        if part['name'] not in ('socket_fit_strip', 'rod_cutting_jig'):
            printed_g += solid * part['qty']
            printed_est += est * part['qty']
        extra = f", print height {part['height_mm']:.1f} mm" if 'height_mm' in part else ''
        print(f"  {part['name']}: x{part['qty']}, {solid:.2f} / {est:.2f} g each{extra}")
    hardware_g = 16 * 0.25
    added = rod_g + printed_g + hardware_g
    added_est = rod_g + printed_est + hardware_g
    print(f'P1A added mass (test tools excluded): rods {rod_g:.1f} g + printed {printed_g:.1f} g solid / {printed_est:.1f} g estimated + M2 hardware ~{hardware_g:.0f} g')
    print(f'  = {added:.1f} g solid-PETG scenario / {added_est:.1f} g infill scenario (hardware allowance unweighed)')
    print('Supports:', support_info)
    origin = masses.get('_origin', {})
    thrust, bare = masses.get('thrust_total_g'), masses.get('bare_aircraft_g')
    if not bare:
        parts_g = [masses.get(k) for k in ('frame_g', 'aio_g', 'motors_x4_g', 'props_x4_g', 'camera_g')]
        if all(parts_g):
            bare = sum(parts_g)
            print(f'Bare aircraft: {bare:.1f} g vendor component sum (excludes antenna, wiring, XT30, screws; weigh it)')
    estimate = masses.get('thrust_estimate_total_g')
    planning = masses.get('thrust_planning_total_g')
    for pack in ('pack_450_g', 'pack_1100_g'):
        if not (bare and masses.get(pack)):
            continue
        hi_m, lo_m = bare + masses[pack] + added, bare + masses[pack] + added_est
        line = f'With {pack[5:-2]} mAh ({masses[pack]} g, {origin.get(pack, "?")}): accounted mass {lo_m:.2f}-{hi_m:.2f} g (unweighed extras excluded)'
        if thrust:
            line += f'; measured thrust {thrust} g gives {thrust / hi_m:.2f}-{thrust / lo_m:.2f}:1'
        elif planning:
            line += f'; at {planning} g planning thrust {planning / hi_m:.2f}-{planning / lo_m:.2f}:1'
            if estimate:
                line += f' (estimate range {estimate[0] / hi_m:.2f}-{estimate[1] / lo_m:.2f}:1)'
        line += f'; {175 - hi_m:.2f} g remaining to 175 g for excluded extras/tolerance'
        if hi_m > 175:
            raise RuntimeError('Accounted mass alone exceeds 175 g: ' + line)
        print(line)
    if not thrust:
        print('Thrust: measured value pending (only an estimate is recorded); measure static thrust')
    print('STL exports:', exported)


def run(context):
    app = adsk.core.Application.get()
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if 'P1A' not in app.activeDocument.name:
            raise RuntimeError('Run P1A generator in its P1A document')
        if design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
            raise RuntimeError('Use a parametric design')
        root = design.rootComponent
        for occurrence in [o for o in root.occurrences if o.component.name in GENERATED or o.component.name == 'Cage skeleton (scaled 408519)']:
            occurrence.deleteMe()
        p, applied, masses = stage1_parameters(design)
        p['arm_axis'] = 'x'
        s = Solids()
        graph = cage_graph(p)
        aircraft = stage2_aircraft(root, s, p)
        cage, cage_info = stage3_cage(root, s, p, graph)
        hubs, hub_parts = stage4_hubs(root, s, p, graph, hub_frames(p, graph))
        strip_occ, strip = stage4_fit_strip(root, s, p)
        jig_occ, jig = stage4_rod_jig(root, s, p)
        supports, support_parts, support_info = stage5_carrier(root, s, p, graph)
        print('Reference meshes:', reference_hubs(root))
        parts = [strip, jig] + hub_parts + support_parts
        V = {'__file__': os.path.join(HERE, 'validation.py')}
        exec(compile(open(V['__file__']).read(), V['__file__'], 'exec'), V)
        validation = V['validate_fixed'](design, p, (aircraft, cage, hubs, supports))
        print('Automated validation:', validation)
        exported = export_stl(parts)
        print('Materials:', apply_materials(design, p))
        print('Material validation:', V['validate_materials'](design))
        color_hubs(design)
        report(p, applied, masses, (aircraft, cage, hubs, supports), cage_info, graph, parts, support_info, exported)
    except Exception:
        print('FAILED:\n' + traceback.format_exc())
        raise
