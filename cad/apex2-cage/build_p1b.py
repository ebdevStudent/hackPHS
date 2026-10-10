"""Apex-2 ball cage, P1B two-ring gimbal: generator for a separate Fusion design.

Two-ring gimbal after kert's Thingiverse 408519, with the axes assigned so neither ring sits in the camera's
straight-ahead view at the nominal pose: cage --(Z, cage poles)-- outer ring (XZ plane) --(X)-- inner ring
(XY plane) --(Y, fore-aft)-- aircraft. All three pivot axes pass through the cage centre. Each ring is printed as four flat quarter arcs
joined by junction blocks at its four pivots (the original Quart_* / Jonction_* layout). Pivots use MR52ZZ
bearings (5 x 2 x 2.5 mm) on 2 mm dowel pins: the pin is pressed into one part, the bearing seated in the other.

Reuses build_p1a.py for parameters, the 247.85 mm cage (44.50 mm rods), hubs and carrier. P1B differences:
  - pole hubs get an inward pin boss (hub_pole_5way_pivot); everything else in the cage is shared with P1A;
  - the aircraft, carrier and support arms are raised by aircraft_z so the estimated CG sits at the pivot
    centre; the arm-end pivot blocks have vertical slots for +-cg_slot of physical CG adjustment;
  - ring radii are derived from the aircraft's swept radius at every allowed balancing position
    (adj_y across, adj_x along the arms, cg_slot vertical) plus gimbal_clear;
  - the support arms run fore-aft (Y); the VTX antenna mounts on the frame top.

Verification: radial (sphere) clearances for every rotating pair, plus sampled solid-intersection checks of
each relative joint motion. Run in the "Apex2 Ball Cage P1B Gimbal" design; STLs go to exports_p1b/.
"""
import math
import os
import random
import traceback

import adsk.core
import adsk.fusion

HERE = os.path.dirname(os.path.abspath(globals().get('__file__', '/Users/devk/Documents/HackPHS26/cad/apex2-cage/build_p1b.py')))
A = {'__name__': 'build_p1a', '__file__': os.path.join(HERE, 'build_p1a.py')}
exec(compile(open(A['__file__']).read(), A['__file__'], 'exec'), A)
add, sub, mul, dot, cross, norm, unit, P, D = (A[k] for k in ('add', 'sub', 'mul', 'dot', 'cross', 'norm', 'unit', 'P', 'D'))
new_component, add_bodies, frame_matrix = A['new_component'], A['add_bodies'], A['frame_matrix']

P1B_PARAMS = [
    ('gimbal_clear', '4 mm', 'mm', 'DESIGN: aircraft-envelope reserve to inner ring (not the local pivot running gap)'),
    ('ring_w', '5 mm', 'mm', 'DESIGN: ring band radial width (lightened from 6)'),
    ('ring_t', '3 mm', 'mm', 'DESIGN: ring band thickness (axial, lightened from 3.5)'),
    ('ring_gap', '5 mm', 'mm', 'DESIGN: radial gap between inner ring outside and outer ring inside'),
    ('junction_len', '14 mm', 'mm', 'DESIGN: junction block length along the ring'),
    ('junction_t', '8 mm', 'mm', 'DESIGN: junction block thickness (holds the 5 mm bearing)'),
    ('splice_len', '14 mm', 'mm', 'DESIGN: splice plate overlap onto each quarter end'),
    ('splice_t', '2 mm', 'mm', 'DESIGN: splice plate thickness'),
    ('lighten_w', '2.6 mm', 'mm', 'DESIGN: lightening slot width in ring quarters'),
    ('bearing_od', '5 mm', 'mm', 'MEASURE: MR52ZZ outer diameter'),
    ('bearing_w', '2.5 mm', 'mm', 'MEASURE: MR52ZZ width'),
    ('bearing_seat_clear', '0.05 mm', 'mm', 'FIT COUPON: bearing seat diametral allowance; +0.05 mm is nominal clearance, qualify retention on the coupon'),
    ('pin_d', '2 mm', 'mm', 'MEASURE: dowel pin diameter (2 x 16 mm)'),
    ('pin_press_d', '1.9 mm', 'mm', 'FIT COUPON: pin press-fit hole diameter'),
    ('pin_press_horizontal_d', '2.15 mm', 'mm', 'T2 #4: hole diameter when printed horizontally; CAD print compensation, not measured pin OD'),
    ('pin_press_vertical_d', '2.25 mm', 'mm', 'T2 #5: hole diameter when printed vertically; CAD print compensation, not measured pin OD'),
    ('pin_press_depth', '6 mm', 'mm', 'DESIGN: pin press depth'),
    ('pin_len', '16 mm', 'mm', 'MEASURE: dowel pin length'),
    ('pivot_gap', '0.5 mm', 'mm', 'DESIGN: axial running gap at each pivot'),
    ('pole_boss_len', '8 mm', 'mm', 'DESIGN: pole hub pin boss length (inward)'),
    ('pole_boss_od', '6 mm', 'mm', 'DESIGN: pole hub pin boss OD'),
    ('pivot_boss_od', '7 mm', 'mm', 'DESIGN: arm-end pivot boss OD'),
    ('pivot_boss_len', '12 mm', 'mm', 'DESIGN: arm-end pivot boss length (keeps the slotted plate inboard of the ring sweep)'),
    ('pivot_plate_t', '4 mm', 'mm', 'DESIGN: arm-end pivot plate thickness'),
    ('cg_slot', '5 mm', 'mm', 'DESIGN: vertical CG adjustment each way at the arm-end pivot plate'),
    ('junction_screws_per_side', '1', '', 'DESIGN: M2 screws through each splice into each quarter end (1 or 2; lightened from 2)'),
]
GENERATED = ['Cage (P1A cage, pivot pole hubs)', 'Outer ring (Z to cage, X to inner)', 'Inner ring (X to outer, Y to aircraft)',
             'Aircraft side (rotates on Y pivots)', 'Pivot hardware (MR52ZZ + 2 mm pins)', 'Gimbal test fixtures']
LEGACY = ['Outer ring (Z to cage, Y to inner)', 'Inner ring (Y to outer, X to aircraft)', 'Aircraft side (rotates on X pivots)']
# P1B design values that differ from P1A; applied once (marked [P1B]) so later manual edits persist.
P1B_OVERRIDES = {
    'adj_x': ('3 mm', 'carrier travel each way along the fore-aft arms (limited so the rings stay compact)'),
    'adj_y': ('2 mm', 'frame travel each way across the arms (lateral)'),
    'cg_slot': ('5 mm', 'vertical CG travel each way at the arm-end pivot plates'),
    'carrier_core_w': ('48 mm', 'carrier centre width (strap slots clear the lateral frame slots)'),
    'pivot_gap': ('1 mm', 'running gap increased from 0.5 mm to improve printed pivot-region radial reserves'),
}
HARDWARE = ('pin_', 'MR52ZZ')


def parameters(design):
    user = design.userParameters
    for name, expression, units, comment in A['PARAMS'] + P1B_PARAMS:
        if user.itemByName(name) is None:
            user.add(name, adsk.core.ValueInput.createByString(expression), units, comment)
    for name, (expression, why) in P1B_OVERRIDES.items():
        prm = user.itemByName(name)
        if '[P1B]' not in prm.comment:
            prm.expression = expression
            prm.comment = '[P1B] DESIGN: ' + why
    user.itemByName('bearing_seat_clear').comment = 'T2 #4: selected 5.30 mm drawn seat, compensating print shrinkage; user-reported fit, load retention pending'
    user.itemByName('pin_press_d').comment = 'Legacy shared diameter; final P1B uses orientation-specific pin_press_horizontal_d and pin_press_vertical_d'
    user.itemByName('gimbal_clear').comment = 'DESIGN: aircraft-envelope reserve to inner ring; local pivot running gaps are reported separately'
    p, applied, masses = A['stage1_parameters'](design)
    for name, _, units, _ in P1B_PARAMS:
        p[name] = user.itemByName(name).value * (10 if units == 'mm' else 1)
    return p, applied, masses


def pin_print_diameter(p, part_name):
    """Match the qualified coupon axis to the final STL's print orientation.

    inner junction X stays horizontal under FLIP_X. Arm block X becomes vertical
    under X_UP; pole hub Z stays vertical. Assembly axes do not select this fit.
    """
    if part_name == 'inner_junction_X_pin':
        return p['pin_press_horizontal_d']
    if part_name in ('arm_pivot_block','hub_pole_5way_pivot'):
        return p['pin_press_vertical_d']
    raise ValueError('Unknown pressed-pin part: '+part_name)


# ---------------------------------------------------------------- CG and radii
def cg_offset(p, masses, carrier_g, arms_g, pack):
    """Estimated CG height relative to the frame top (z=0 in the aircraft frame)."""
    h = p[f'batt{pack}_h']
    items = [(masses.get('frame_g', 18), -0.5), (masses.get('aio_g', 4.9), 8.0), (masses.get('motors_x4_g', 17.9), p['motor_h'] / 2),
             (masses.get('props_x4_g', 2), p['prop_z'] + p['prop_disk_h'] / 2), (masses.get('camera_g', 2), p['cam_z']),
             (masses.get(f'pack_{pack}_g', 30), -p['frame_t'] - p['carrier_t'] - p['battery_gap'] - p['battery_shield_t'] - h / 2),
             (carrier_g, -p['frame_t'] - p['carrier_t'] / 2), (arms_g, -p['frame_t'] + p['support_h'] / 2)]
    total = sum(m for m, _ in items)
    return sum(m * z for m, z in items) / total, total


def travel(p):
    """Balancing travel each way: (X across the arms, Y along the arms, Z vertical)."""
    return p['adj_y'], p['adj_x'], p['cg_slot']


def aircraft_radius(p, dz):
    """Largest distance from the pivot centre of off-axis aircraft parts at any allowed balancing position."""
    tx, ty, tz = travel(p)
    half = p['motor_diag'] / 2 / math.sqrt(2)
    tip = math.hypot(half + tx, half + ty) + p['prop_dia'] / 2
    r = math.hypot(tip, dz + tz + p['prop_z'] + p['prop_disk_h'])
    under = -p['frame_t'] - p['carrier_t'] - p['battery_gap'] - p['battery_shield_t']
    for pack in ('450', '1100'):
        l, w, h = p[f'batt{pack}_l'], p[f'batt{pack}_w'], p[f'batt{pack}_h']
        r = max(r, math.sqrt((w / 2 + tx) ** 2 + (l / 2 + ty) ** 2 + (dz - tz + under - h) ** 2))
    r = max(r, math.sqrt((p['carrier_core_w'] / 2 + tx) ** 2 + (p['carrier_len'] / 2 + ty) ** 2 + (dz + tz) ** 2))
    for x, y, z, h in A['antenna_envelope'](p):
        r = max(r, math.sqrt((abs(x) + tx + p['antenna_d'] / 2) ** 2 + (abs(y) + ty + p['antenna_d'] / 2) ** 2 + (dz + tz + z + h) ** 2))
    return r


# ---------------------------------------------------------------- ring geometry (ring-local: ring in XY, axis Z)
def sector(s, ri, ro, z0, z1, a0, a1):
    """Annular sector between angles a0 < a1 (radians, span < pi), thickness z0..z1."""
    body = s.cyl((0, 0, z0), (0, 0, z1), 2 * ro)
    s.cut(body, s.cyl((0, 0, z0 - 1), (0, 0, z1 + 1), 2 * ri))
    big = 4 * ro
    for angle, sign in ((a0, 1), (a1, -1)):
        along = (math.cos(angle), math.sin(angle), 0)
        normal = (-math.sin(angle) * sign, math.cos(angle) * sign, 0)
        half = s.box(add(mul(normal, big / 2), (0, 0, (z0 + z1) / 2)), along, normal, 2 * big, big, (z1 - z0) + 2)
        s.tbm.booleanOperation(body, half, adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return body


def polar(r, a, z=0.0):
    return (r * math.cos(a), r * math.sin(a), z)


def quarter(s, p, ri, ro):
    """Quarter arc between two junction blocks centred at 0 and 90 degrees, with screw pilots and lightening slots."""
    rm = (ri + ro) / 2
    half_block = (p['junction_len'] / 2 + 0.2) / rm
    a0, a1 = half_block, math.pi / 2 - half_block
    t = p['ring_t'] / 2
    body = sector(s, ri, ro, -t, t, a0, a1)
    hole_offsets = (p['splice_len'] * 0.3, p['splice_len'] * 0.75) if round(p['junction_screws_per_side']) >= 2 else (p['splice_len'] * 0.55,)
    for end, direction in ((a0, 1), (a1, -1)):
        for offset in hole_offsets:
            a = end + direction * offset / rm
            s.cut(body, s.cyl(polar(rm, a, -t - 1), polar(rm, a, t + 1), p['m2_tap']))
    clear_from = a0 + (p['splice_len'] + 4) / rm
    clear_to = a1 - (p['splice_len'] + 4) / rm
    slot_len, pitch = 12.0, 16.0
    count = max(0, int(((clear_to - clear_from) * rm + 4) // pitch))
    if count and ro - ri - p['lighten_w'] >= 2.4:
        spare = (clear_to - clear_from) * rm - count * pitch + 4
        for k in range(count):
            mid = clear_from + (spare / 2 + k * pitch + slot_len / 2) / rm
            da = (slot_len / 2 - p['lighten_w'] / 2) / rm
            s.cut(body, s.slot(polar(rm, mid - da), polar(rm, mid + da), p['lighten_w'], -t - 1, t + 1))
    return body


def junction(s, p, ri, ro, r_lo, r_hi, pivot):
    """Junction block at angle 0 joining two quarters, with a radial pivot feature.
    pivot: 'bearing_in' (seat opens at r_lo), 'bearing_out' (seat opens at r_hi) or 'pin_out' (press hole at r_hi)."""
    rm = (ri + ro) / 2
    jb = p['junction_len'] / 2 / rm
    t, jt = p['ring_t'] / 2, p['junction_t'] / 2
    # Block top is flush with the splice plate's outer face so the part prints face-down without supports.
    # A long radial stand-off (outer ring to pole hub) narrows to a bearing-width post to save mass.
    if r_hi > ro + 2:
        body = sector(s, r_lo, ro + 1, -jt, t + p['splice_t'], -jb, jb)
        post = p['bearing_od'] + 3.2
        s.join(body, s.aabox((ro, -post / 2, -jt), (r_hi, post / 2, t + p['splice_t'])))
    else:
        body = sector(s, r_lo, r_hi, -jt, t + p['splice_t'], -jb, jb)
    span = jb + p['splice_len'] / rm
    s.join(body, sector(s, ri, ro, t, t + p['splice_t'], -span, span))
    offsets = (p['splice_len'] * 0.3, p['splice_len'] * 0.75) if round(p['junction_screws_per_side']) >= 2 else (p['splice_len'] * 0.55,)
    for side in (-1, 1):
        for offset in offsets:
            a = side * (jb + 0.2 / rm + offset / rm)
            s.cut(body, s.cyl(polar(rm, a, t - 1), polar(rm, a, t + p['splice_t'] + 1), p['m2_clear']))
    seat = p['bearing_od'] + p['bearing_seat_clear']
    if pivot == 'bearing_in':
        s.cut(body, s.cyl((r_lo - 1, 0, 0), (r_lo + p['bearing_w'], 0, 0), seat))
        s.cut(body, s.cyl((r_lo, 0, 0), (r_hi + 1, 0, 0), p['pin_d'] + 0.4))
    elif pivot == 'bearing_out':
        s.cut(body, s.cyl((r_hi - p['bearing_w'], 0, 0), (r_hi + 1, 0, 0), seat))
        s.cut(body, s.cyl((r_lo - 1, 0, 0), (r_hi, 0, 0), p['pin_d'] + 0.4))
    else:
        s.cut(body, s.cyl((r_hi - p['pin_press_depth'], 0, 0), (r_hi + 1, 0, 0), pin_print_diameter(p,'inner_junction_X_pin')))
    return body


def ring_assembly(root, s, p, name, base_matrix, ri, ro, junction_specs, prefix):
    """junction_specs: list of (angle_deg, part_name, r_lo, r_hi, pivot); quarters fill between them.
    Every occurrence gets its full world transform (ring-local rotation composed with base_matrix) under an
    identity holder: child transforms under a rotated parent were composed inconsistently by Fusion."""
    holder = new_component(root, name)
    parts = []

    def placed(angle_deg):
        m = adsk.core.Matrix3D.create()
        m.setToRotation(math.radians(angle_deg), D((0, 0, 1)), P((0, 0, 0)))
        m.transformBy(base_matrix)
        return m

    quarter_body = quarter(s, p, ri, ro)
    q_name = f'{prefix}_ring_quarter'
    q_occ = None
    for k in range(4):
        m = placed(90 * k)
        if q_occ is None:
            q_occ = new_component(holder.component, q_name, m)
            native = add_bodies(q_occ.component, [(q_name, quarter_body)])[q_name]
            parts.append({'name': q_name, 'qty': 4, 'body': native, 'volume_mm3': native.volume * 1000})
        else:
            holder.component.occurrences.addExistingComponent(q_occ.component, m)
    made = {}
    for angle, part, r_lo, r_hi, pivot in junction_specs:
        m = placed(angle)
        if part not in made:
            occ = new_component(holder.component, part, m)
            native = add_bodies(occ.component, [(part, junction(s, p, ri, ro, r_lo, r_hi, pivot))])[part]
            made[part] = occ
            parts.append({'name': part, 'qty': 0, 'body': native, 'volume_mm3': native.volume * 1000})
        else:
            holder.component.occurrences.addExistingComponent(made[part].component, m)
        next(x for x in parts if x['name'] == part)['qty'] += 1
    return holder, parts


def all_bodies(occurrence):
    """Every body under an occurrence (assembly-context proxies)."""
    found = list(occurrence.bRepBodies)
    for child in occurrence.childOccurrences:
        found += all_bodies(child)
    return found


def connectivity(groups,p):
    """Every ring junction must touch two quarters of its ring; every pin must engage its press part and pass
    through its bearing; every bearing must sit in its seat part. Returns a list of failures."""
    measure = adsk.core.Application.get().measureManager
    def touching(a, b):
        return measure.measureMinimumDistance(a, b).value * 10 < 0.01
    failures = []
    for key in ('outer', 'inner'):
        items = all_bodies(groups[key])
        quarters = [b for b in items if 'quarter' in b.name]
        for j in (b for b in items if 'junction' in b.name):
            n = sum(touching(j, q) for q in quarters)
            if n != 2:
                failures.append(f'{key} {j.name} touches {n} quarters (expected 2)')
    pool = [b for key in groups for b in all_bodies(groups[key])]
    validation={'__file__':os.path.join(HERE,'validation.py')}
    exec(compile(open(validation['__file__']).read(),validation['__file__'],'exec'),validation)
    # Compensation-selected CAD holes can have nominal clearance. Validate
    # exact axes and engaged depth; do not mistake native touching for printed fit.
    validation['pin_engagement'](pool,p)
    validation['bearing_engagement'](pool,p)
    for k in range(6):
        pin = next(b for b in pool if b.name == f'pin_{k}')
        bearing = next(b for b in pool if b.name == f'MR52ZZ_{k}')
        if not touching(pin, bearing):
            failures.append(f'pin_{k} does not pass through MR52ZZ_{k}')
    return failures


def highlight_hardware(design):
    """Orange pins and blue bearings so the pivots are visible inside the junction blocks."""
    library = adsk.core.Application.get().materialLibraries.itemByName('Fusion Appearance Library')
    def look(name, rgb):
        appearance = design.appearances.itemByName(name)
        if appearance is None:
            appearance = design.appearances.addByCopy(library.appearances.itemByName('Plastic - Glossy (Red)'), name)
            for prop in appearance.appearanceProperties:
                if isinstance(prop, adsk.core.ColorProperty) and prop.value is not None:
                    prop.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
        return appearance
    pin, bearing = look('Pin (orange)', (255, 120, 0)), look('Bearing (blue)', (40, 120, 255))
    for component in design.allComponents:
        for body in component.bRepBodies:
            if body.name.startswith('pin_'):
                body.appearance = pin
            elif body.name.startswith('MR52ZZ'):
                body.appearance = bearing


def add_joints(design, groups):
    """Ground the cage, make each group rigid, and add as-built revolute joints through the cage centre:
    cage-outer about Z, outer-inner about X, inner-aircraft about Y. Drag a ring in Fusion to move it."""
    root = design.rootComponent
    groups['cage'].isGrounded = True
    rigid = 0
    for key in ('cage', 'outer', 'inner', 'side'):
        component = groups[key].component
        if component.occurrences.count > 1:
            members = adsk.core.ObjectCollection.create()
            for occ in component.occurrences:
                members.add(occ)
            component.rigidGroups.add(members, True)
            rigid += 1
    origin = adsk.fusion.JointGeometry.createByPoint(root.originConstructionPoint)
    made = []
    for a, b, direction, name in (('cage', 'outer', adsk.fusion.JointDirections.ZAxisJointDirection, 'Z pole pivot (cage - outer ring)'),
                                  ('outer', 'inner', adsk.fusion.JointDirections.XAxisJointDirection, 'X pivot (outer ring - inner ring)'),
                                  ('inner', 'side', adsk.fusion.JointDirections.YAxisJointDirection, 'Y pivot (inner ring - aircraft)')):
        joint_input = root.asBuiltJoints.createInput(groups[a], groups[b], origin)
        joint_input.setAsRevoluteJointMotion(direction)
        joint = root.asBuiltJoints.add(joint_input)
        joint.name = name
        made.append(name)
    return rigid, made


# ---------------------------------------------------------------- build
def gimbal_fit_coupon(s, p):
    """Bearing seats and pin press holes printed in the same orientations as the real parts.
    Row 1 (horizontal, like junctions): bearing seats bearing_od + (0, +0.10, +0.20, +0.30, +0.40) mm, 1-5 dimples.
    Row 2 (horizontal): pin holes 1.85 / 1.95 / 2.05 / 2.15 / 2.25 mm. Row 3 (vertical, like the pole and arm bosses): same pin holes.
    Ranges sit above nominal because FDM prints small holes ~0.1-0.3 mm undersize (Voxel, 0.4 mm nozzle).
    The step is 13 mm tall so each vertical hole ends 2 mm above its horizontal hole: the holes never cross."""
    pitch, n = 9.0, 5
    width = pitch * n + 2
    body = s.aabox((0, 0, 0), (width, 12, 8))
    step_h, horiz_z = 13.0, 4.0
    s.join(body, s.aabox((0, 12, 0), (width, 22, step_h)))
    seats = [p['bearing_od'] + d for d in (0.0, 0.10, 0.20, 0.30, 0.40)]
    pins = [1.85, 1.95, 2.05, 2.15, 2.25]
    for k in range(n):
        x = 5.5 + k * pitch
        s.cut(body, s.cyl((x, -1, 4), (x, p['bearing_w'], 4), seats[k]))            # seat opens on the y=0 face
        s.cut(body, s.cyl((x, p['bearing_w'], 4), (x, 6, 4), p['pin_d'] + 0.4))
        s.cut(body, s.cyl((x, 23, horiz_z), (x, 22 - p['pin_press_depth'], horiz_z), pins[k]))   # horizontal pin hole from the y=22 face
        s.cut(body, s.cyl((x, 17, step_h - p['pin_press_depth']), (x, 17, step_h + 1), pins[k]))  # vertical pin hole from the top
        for m in range(k + 1):
            s.cut(body, s.cyl((x - 3 + m * 1.5, 9, 7.6), (x - 3 + m * 1.5, 9, 9), 0.9))
    return body


def build(design):
    root = design.rootComponent
    for joint in list(root.asBuiltJoints) + list(root.joints):
        joint.deleteMe()
    for occurrence in [o for o in root.occurrences if o.component.name in GENERATED + LEGACY]:
        occurrence.deleteMe()
    p, applied, masses = parameters(design)
    s = A['Solids']()
    graph = A['cage_graph'](p)
    points = graph[0]
    report = {'applied': applied, 'masses': masses}

    # Aircraft-side solids (aircraft frame: frame top at z = 0) to size the CG offset first.
    p['arm_axis'] = 'y'
    carrier, top, bottom, x0, holes_x = A['carrier_geometry'](s, p, 'y')
    carrier_g = (carrier.volume + A['nut_shield_geometry'](s, p).volume) * p['petg_density']   # carrier + nut shield
    # Provisional arm to estimate mass; final end position depends on the ring radius.
    arm_tmp, _, _ = A['support_arm_geometry'](s, p, x0, holes_x, top, 70)
    arms_g = 2 * arm_tmp.volume * p['petg_density']
    cg450, m450 = cg_offset(p, masses, carrier_g, arms_g, '450')
    cg1100, m1100 = cg_offset(p, masses, carrier_g, arms_g, '1100')
    dz = -cg450                                          # raise the aircraft so the 450 mAh CG is at the pivot centre
    report['cg'] = {'cg_450_below_frame_top_mm': round(-cg450, 2), 'cg_1100_below_frame_top_mm': round(-cg1100, 2),
                    'aircraft_z_offset_mm': round(dz, 2), '1100_needs_shift_mm': round(cg450 - cg1100, 2),
                    'within_cg_slot': abs(cg450 - cg1100) <= p['cg_slot']}

    # Ring radii from the swept aircraft radius, including the arm-end pivot plates (iterated: the plates
    # sit a fixed distance inboard of the inner ring).
    def side_layout(ri):
        arm_end = ri - p['pivot_gap']
        plate_x1 = arm_end - p['pivot_boss_len']
        flange_end = plate_x1 - p['pivot_plate_t']
        flange_z = (top + 5, top + p['flange_h'] - 4)
        world_fz = [z + dz for z in flange_z]
        lo = min(world_fz + [0]) - p['cg_slot'] - 4
        hi = max(world_fz + [0]) + p['cg_slot'] + 4
        corners = [(plate_x1, 6, max(abs(lo), abs(hi))), (flange_end, 5, dz + p['cg_slot'] + top + p['flange_h']),
                   (arm_end, p['pivot_boss_od'] / 2, 0)]
        return arm_end, plate_x1, flange_end, lo, hi, max(norm(c) for c in corners[:2])
    base = aircraft_radius(p, dz)
    ri_in = math.ceil(base + p['gimbal_clear'])
    for _ in range(10):
        arm_end, plate_x1, flange_end, lo, hi, r_side = side_layout(ri_in)
        r_air = max(base, r_side)
        if r_air + p['gimbal_clear'] <= ri_in:
            break
        ri_in = math.ceil(r_air + p['gimbal_clear'])
    ro_in = ri_in + p['ring_w']
    ri_out = ro_in + p['ring_gap']
    ro_out = ri_out + p['ring_w']
    meet = ro_in + p['ring_gap'] / 2                    # inner/outer Y pivot interface radius
    pole_tip = p['cage_vertex_r'] - p['pole_boss_len']
    report['travel_mm'] = dict(zip(('across_X', 'along_arms_Y', 'vertical_Z'), travel(p)))
    report['radii'] = {'aircraft_swept_r': round(r_air, 2), 'props_batteries_carrier_r': round(base, 2), 'arm_end_parts_r': round(r_side, 2),
                       'inner_ring': (ri_in, ro_in), 'outer_ring': (ri_out, ro_out), 'pole_boss_tip_r': round(pole_tip, 2),
                       'cage_inner_clear_to_outer_ring': round(p['cage_vertex_r'] - p['hub_core_r'] - 4 - ro_out, 1)}

    # Cage: P1A cage + hubs, pole hubs replaced by pivot hubs.
    cage = new_component(root, GENERATED[0])
    _, cage_info = A['stage3_cage'](cage.component, s, p, graph)
    frames = A['hub_frames'](p, graph)
    hub_holder = new_component(cage.component, 'Hubs')
    groups = {}
    for f in frames:
        groups.setdefault(f['key'], []).append(f)
    hub_parts, used = [], set()
    letters = iter('ABCD')
    for key, members in sorted(groups.items(), key=lambda kv: (len(kv[0][0]), kv[0][1] is not None, -len(kv[1]))):
        arms, boss = key
        name = f'hub_{len(arms)}way_mount_{next(letters)}' if boss else {3: 'hub_3way', 4: 'hub_4way', 5: 'hub_pole_5way_pivot'}[len(arms)]
        if name in used:
            name += f'_variant{len(used)}'
        used.add(name)
        body = A['hub_body'](s, p, arms, boss)
        if len(arms) == 5:   # inward pin boss on the pole axis (local +Z points to the cage centre)
            s.join(body, s.cyl((0, 0, 0), (0, 0, p['pole_boss_len']), p['pole_boss_od']))
            s.cut(body, s.cyl((0, 0, p['pole_boss_len'] - p['pin_press_depth']), (0, 0, p['pole_boss_len'] + 1), pin_print_diameter(p,name)))
            for d in arms:   # re-open the rod sockets the boss overlaps
                tip = mul(d, p['hub_arm_len'])
                s.cut(body, s.cyl(sub(tip, mul(d, p['socket_depth'])), add(tip, mul(d, 0.5)), p['rod_dia'] + 2 * p['rod_bore_clear']))
        first = members[0]
        occ = new_component(hub_holder.component, name, frame_matrix(first['origin'], first['x'], first['y'], first['z']))
        native = add_bodies(occ.component, [(name, body)])[name]
        for f in members[1:]:
            hub_holder.component.occurrences.addExistingComponent(occ.component, frame_matrix(f['origin'], f['x'], f['y'], f['z']))
        hub_parts.append({'name': name, 'qty': len(members), 'body': native, 'volume_mm3': native.volume * 1000})

    # Outer ring: plane XZ (ring local x -> world X, local y -> world Z, local z -> world -Y).
    outer_m = frame_matrix((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))
    outer, outer_parts = ring_assembly(root, s, p, GENERATED[1], outer_m, ri_out, ro_out, [
        (0, 'outer_junction_X_bearing', meet + p['pivot_gap'] / 2, ro_out, 'bearing_in'),
        (180, 'outer_junction_X_bearing', meet + p['pivot_gap'] / 2, ro_out, 'bearing_in'),
        (90, 'outer_junction_Z_bearing', ri_out, pole_tip - p['pivot_gap'], 'bearing_out'),
        (270, 'outer_junction_Z_bearing', ri_out, pole_tip - p['pivot_gap'], 'bearing_out')], 'outer')
    # Inner ring: plane XY (local = world); Y pivots to the aircraft (fore-aft), X pivots to the outer ring.
    inner, inner_parts = ring_assembly(root, s, p, GENERATED[2], adsk.core.Matrix3D.create(), ri_in, ro_in, [
        (90, 'inner_junction_Y_bearing', ri_in, ro_in, 'bearing_in'),
        (270, 'inner_junction_Y_bearing', ri_in, ro_in, 'bearing_in'),
        (0, 'inner_junction_X_pin', ri_in, meet - p['pivot_gap'] / 2, 'pin_out'),
        (180, 'inner_junction_X_pin', ri_in, meet - p['pivot_gap'] / 2, 'pin_out')], 'inner')

    # Aircraft side: envelope, carrier and arms raised by dz; arms and pivot blocks run fore-aft (Y), blocks at z = 0.
    side = new_component(root, GENERATED[3])
    lifted = adsk.core.Matrix3D.create()
    lifted.translation = D((0, 0, dz / 10))
    raised = new_component(side.component, 'aircraft_raised_to_cg', lifted)
    A['stage2_aircraft'](raised.component, s, p)
    arm, flange_z, flange_x0 = A['support_arm_geometry'](s, p, x0, holes_x, top, flange_end)
    holder = new_component(side.component, 'carrier_and_arms', lifted)
    c_occ = new_component(holder.component, 'carrier_plate')
    c_body = add_bodies(c_occ.component, [('carrier_plate', carrier)])['carrier_plate']
    sh_occ = new_component(holder.component, 'nut_shield_plate')
    sh_body = add_bodies(sh_occ.component, [('nut_shield_plate', A['nut_shield_geometry'](s, p))])['nut_shield_plate']
    to_front = adsk.core.Matrix3D.create()
    to_front.setToRotation(math.pi / 2, D((0, 0, 1)), P((0, 0, 0)))
    to_back = adsk.core.Matrix3D.create()
    to_back.setToRotation(-math.pi / 2, D((0, 0, 1)), P((0, 0, 0)))
    a_occ = new_component(holder.component, 'support_arm_p1b', to_front)
    a_body = add_bodies(a_occ.component, [('support_arm_p1b', arm)])['support_arm_p1b']
    holder.component.occurrences.addExistingComponent(a_occ.component, to_back)
    # Pivot block: plate bolted to the arm flange through vertical slots (CG height), pin boss on the X axis.
    world_fz = [z + dz for z in flange_z]
    block = s.aabox((flange_end, -6, lo), (plate_x1, 6, hi))
    s.join(block, s.cyl((plate_x1 - 0.5, 0, 0), (arm_end, 0, 0), p['pivot_boss_od']))
    s.cut(block, s.cyl((arm_end - p['pin_press_depth'], 0, 0), (arm_end + 1, 0, 0), pin_print_diameter(p,'arm_pivot_block')))
    for fz in world_fz:
        s.cut(block, s.box(((flange_end + plate_x1) / 2, 0, fz), (0, 0, 1), (0, 1, 0), 2 * p['cg_slot'] + p['m2_clear'], p['m2_clear'], p['pivot_plate_t'] + 2))
    b_occ = new_component(side.component, 'arm_pivot_block', to_front)
    b_body = add_bodies(b_occ.component, [('arm_pivot_block', block)])['arm_pivot_block']
    side.component.occurrences.addExistingComponent(b_occ.component, to_back)
    side_parts = [{'name': 'carrier_plate', 'qty': 1, 'body': c_body, 'volume_mm3': c_body.volume * 1000},
                  {'name': 'nut_shield_plate', 'qty': 1, 'body': sh_body, 'volume_mm3': sh_body.volume * 1000},
                  {'name': 'support_arm_p1b', 'qty': 2, 'body': a_body, 'volume_mm3': a_body.volume * 1000},
                  {'name': 'arm_pivot_block', 'qty': 2, 'body': b_body, 'volume_mm3': b_body.volume * 1000}]

    # Pivot hardware: each pin lives with the part it is pressed into and each bearing with its seat part, so the
    # hardware moves with the Fusion joints. Excluded from swept-collision checks (coaxial by construction).
    pivots = [((0, 1, 0), arm_end, ri_in, 'side', 'inner'), ((0, -1, 0), arm_end, ri_in, 'side', 'inner'),
              ((1, 0, 0), meet - p['pivot_gap'] / 2, meet + p['pivot_gap'] / 2, 'inner', 'outer'),
              ((-1, 0, 0), meet - p['pivot_gap'] / 2, meet + p['pivot_gap'] / 2, 'inner', 'outer'),
              ((0, 0, 1), pole_tip - p['pivot_gap'], pole_tip, 'cage', 'outer'), ((0, 0, -1), pole_tip - p['pivot_gap'], pole_tip, 'cage', 'outer')]
    owners = {'cage': cage, 'outer': outer, 'inner': inner, 'side': side}
    per_group = {key: [] for key in owners}
    pin_report = []
    pin_cut = p['pin_press_depth'] + p['pivot_gap'] + p['bearing_w'] + 1.5   # 1.5 mm past the bearing
    for k, (axis, gap_lo, gap_hi, pin_group, bearing_group) in enumerate(pivots):
        if k < 4:      # pin pressed in the inner part, bearing in the outer part's inner face
            pin_from, bearing_from, bearing_dir = gap_lo - p['pin_press_depth'], gap_hi, 1
        else:          # pin in the pole boss (outside), bearing at the outer Z junction's outer face
            pin_from, bearing_from, bearing_dir = gap_hi + p['pin_press_depth'], gap_lo, -1
        pin_to = pin_from + bearing_dir * pin_cut
        bearing_to = bearing_from + bearing_dir * p['bearing_w']
        per_group[pin_group].append((f'pin_{k}', s.cyl(mul(axis, pin_from), mul(axis, pin_to), p['pin_d'])))
        ring = s.cyl(mul(axis, bearing_from), mul(axis, bearing_to), p['bearing_od'])
        lo_b, hi_b = sorted((bearing_from, bearing_to))
        s.cut(ring, s.cyl(mul(axis, lo_b - 1), mul(axis, hi_b + 1), p['pin_d']))
        per_group[bearing_group].append((f'MR52ZZ_{k}', ring))
        pin_report.append(round(abs(pin_to - bearing_to) * (1 if bearing_dir * (pin_to - bearing_to) > 0 else -1), 2))
    for key, bodies in per_group.items():
        hw_occ = new_component(owners[key].component, 'pivot_hardware')
        add_bodies(hw_occ.component, bodies)
    report['pin_beyond_bearing_mm'] = pin_report       # positive: pin passes fully through the bearing
    report['pin_cut_len_mm'] = round(pin_cut, 2)

    fixture_m = adsk.core.Matrix3D.create()
    fixture_m.translation = D((0, -20, 0))
    fixtures = new_component(root, GENERATED[5], fixture_m)
    coupon_body = add_bodies(fixtures.component, [('gimbal_fit_coupon', gimbal_fit_coupon(s, p))])['gimbal_fit_coupon']
    parts = hub_parts + outer_parts + inner_parts + side_parts + [{'name': 'gimbal_fit_coupon', 'qty': 1, 'body': coupon_body,
                                                                    'volume_mm3': coupon_body.volume * 1000}]
    structure_g = carrier_g + arms_g                    # counted again with the printed parts
    return p, report, cage_info, parts, {'cage': cage, 'outer': outer, 'inner': inner, 'side': side}, dz, (m450 - structure_g, m1100 - structure_g)


# ---------------------------------------------------------------- verification
def group_temp(s, occurrence, exclude=('CAMERA_VIEW',) + HARDWARE, only=None, skip=()):
    """One temporary body per group in world coordinates at the nominal pose. only/skip filter by component
    name (e.g. the arm parts that stay on the pivot axis versus the adjustable aircraft)."""
    bodies = []
    def walk(occ, matrix):
        name = occ.component.name
        for body in occ.component.bRepBodies:
            if (body.isLightBulbOn or body.name.startswith('battery_')) and not any(body.name.startswith(e) for e in exclude):
                if (only is None or any(name.startswith(o) for o in only)) and not any(name.startswith(k) for k in skip):
                    copy = s.copy(body)
                    s.tbm.transform(copy, matrix)
                    bodies.append(copy)
        for child in occ.component.occurrences:
            m = child.transform.copy()
            m.transformBy(matrix)
            walk(child, m)
    walk(occurrence, occurrence.transform.copy())
    return s.union(bodies)


def translation(offset):
    m = adsk.core.Matrix3D.create()
    m.translation = D(tuple(c / 10 for c in offset))
    return m


def rotation(axis, degrees):
    m = adsk.core.Matrix3D.create()
    m.setToRotation(math.radians(degrees), D(axis), P((0, 0, 0)))
    return m


def collide(s, a, b, ma, mb):
    ca, cb = s.copy(a), s.copy(b)
    s.tbm.transform(ca, ma)
    s.tbm.transform(cb, mb)
    ok = s.tbm.booleanOperation(ca, cb, adsk.fusion.BooleanTypes.IntersectionBooleanType)
    if not ok:
        raise RuntimeError('Intersection boolean failed')
    return ca.volume * 1000 if ca.faces.count else 0.0


ARM_PARTS = ('support_arm_p1b', 'arm_pivot_block')


def pose(a, b, c):
    """World poses for cage-outer angle c (Z), outer-inner angle b (X) and inner-aircraft angle a (Y)."""
    mo = rotation((0, 0, 1), c)
    mi = rotation((1, 0, 0), b)
    mi.transformBy(mo)
    ma = rotation((0, 1, 0), a)
    ma.transformBy(mi)
    return mo, mi, ma


def verify(s, groups, p):
    """Sampled solid-intersection checks of every relative joint motion, with the adjustable aircraft at each
    corner of its balancing travel (arms and pivot blocks stay on the pivot axis; they move only with the
    vertical CG slot)."""
    cage, outer, inner = (group_temp(s, groups[k]) for k in ('cage', 'outer', 'inner'))
    air = group_temp(s, groups['side'], skip=ARM_PARTS)
    arms = group_temp(s, groups['side'], only=ARM_PARTS)
    identity = adsk.core.Matrix3D.create()
    if (collide(s, air, air, identity, identity) > 0, collide(s, air, air, identity, translation((1000, 0, 0))) == 0) != (True, True):
        raise RuntimeError('Collision self-test failed')
    tx, ty, tz = travel(p)
    corners = [(sx * tx, sy * ty, sz * tz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    def moved(offset, ma):
        m = translation(offset)
        m.transformBy(ma)
        return m
    hits, checks = [], 0
    def test(label, x, y, mx, my, angles):
        nonlocal checks
        checks += 1
        v = collide(s, x, y, mx, my)
        if v > 1e-6:
            hits.append((label, angles, round(v, 4)))
    for off in corners:
        for a in range(0, 360, 15):
            _, mi, ma = pose(a, 0, 0)
            test('inner ring vs adjusted aircraft (Y joint)', inner, air, mi, moved(off, ma), (a, 0, 0, off))
    for dzs in (-tz, tz):
        for a in range(0, 360, 15):
            _, mi, ma = pose(a, 0, 0)
            test('inner ring vs arms/pivot blocks (Y joint)', inner, arms, mi, moved((0, 0, dzs), ma), (a, 0, 0, dzs))
    for b in range(0, 360, 15):
        mo, mi, _ = pose(0, b, 0)
        test('outer ring vs inner ring (X joint)', outer, inner, mo, mi, (0, b, 0))
    for c in range(0, 360, 15):
        mo, _, _ = pose(0, 0, c)
        test('cage vs outer ring (Z joint)', cage, outer, identity, mo, (0, 0, c))
    rng = random.Random(408519)
    for _ in range(120):
        a, b = rng.uniform(0, 360), rng.uniform(0, 360)
        off = rng.choice(corners)
        mo, mi, ma = pose(a, b, 0)
        test('outer ring vs adjusted aircraft (Y+X)', outer, air, mo, moved(off, ma), (round(a), round(b), 0, off))
    for b in range(0, 360, 30):
        for c in range(0, 360, 30):
            mo, mi, _ = pose(0, b, c)
            test('cage vs inner ring (X+Z)', cage, inner, identity, mi, (0, b, c))
    for _ in range(60):
        a, b, c = (rng.uniform(0, 360) for _ in range(3))
        off = rng.choice(corners)
        mo, mi, ma = pose(a, b, c)
        test('cage vs adjusted aircraft (Y+X+Z)', cage, air, identity, moved(off, ma), (round(a), round(b), round(c), off))
    return checks, hits


def camera_check(s, groups, p, dz):
    """Is the lens centreline (out to just inside the cage) clear of the rings? Nominal pose, then the fraction
    of sampled ring orientations relative to the aircraft that put a ring on the centreline."""
    outer, inner = group_temp(s, groups['outer']), group_temp(s, groups['inner'])
    apex, axis = A['camera_axis'](p)
    apex = (apex[0], apex[1], apex[2] + dz)
    points = [add(apex, mul(axis, t)) for t in range(3, 115, 3)]
    inside = adsk.fusion.PointContainment.PointInsidePointContainment
    def blocked(body, to_body):
        for pt in points:
            q = P(pt)
            q.transformBy(to_body)
            if body.pointContainment(q) == inside:
                return math.dist(pt, apex)
        return None
    def rel(a, b):
        mo, mi, ma = pose(a, b, 0)
        to_inner, to_outer = ma.copy(), ma.copy()
        inv_i, inv_o = mi.copy(), mo.copy()
        inv_i.invert()
        inv_o.invert()
        to_inner.transformBy(inv_i)
        to_outer.transformBy(inv_o)
        return to_inner, to_outer
    ti, to = rel(0, 0)
    nominal = {'inner': blocked(inner, ti), 'outer': blocked(outer, to)}
    total = hit = 0
    for a in range(0, 360, 20):
        for b in range(0, 360, 20):
            ti, to = rel(a, b)
            total += 1
            if blocked(inner, ti) is not None or blocked(outer, to) is not None:
                hit += 1
    return nominal, hit / total


def run(context):
    app = adsk.core.Application.get()
    try:
        if 'P1B' not in app.activeDocument.name:
            raise RuntimeError('Run P1B generator in its P1B document')
        design = adsk.fusion.Design.cast(app.activeProduct)
        p, report, cage_info, parts, groups, dz, (m450, m1100) = build(design)
        s = A['Solids']()
        checks, hits = verify(s, groups, p)
        nominal_view, occluded = camera_check(s, groups, p, dz)
        if hits:
            raise RuntimeError('Swept-motion collisions: ' + str(hits))
        if any(v is not None for v in nominal_view.values()):
            raise RuntimeError('Nominal camera centreline obstructed: ' + str(nominal_view))
        rigid, joints = add_joints(design, groups)
        materials = A['apply_materials'](design, p)
        highlight_hardware(design)
        A['color_hubs'](design)
        print('Values applied:', report['applied'] or 'none')
        print('CG:', report['cg'])
        print('Balancing travel each way (mm):', report['travel_mm'])
        print('Radii (mm):', report['radii'])
        print(f"Camera centreline at nominal pose: inner ring {'clear' if nominal_view['inner'] is None else 'blocked at %.0f mm' % nominal_view['inner']}, "
              f"outer ring {'clear' if nominal_view['outer'] is None else 'blocked at %.0f mm' % nominal_view['outer']}; "
              f"a ring crosses it in {occluded * 100:.0f}% of sampled ring orientations (free gimbal; orientation varies in flight)")
        print(f'Fusion joints: {joints}; rigid groups: {rigid}; cage grounded')
        print('Materials:', materials)
        print(f"Pins: cut six stock 2 x {p['pin_len']:.0f} mm dowels to {report['pin_cut_len_mm']} mm for this model; full-length stock is not this geometry; past-bearing per pivot Y+,Y-,X+,X-,Z+,Z-:", report['pin_beyond_bearing_mm'])
        print('Cage:', cage_info)
        problems = connectivity(groups,p)
        if problems:
            raise RuntimeError('Connectivity failed: ' + str(problems))
        V = {'__file__': os.path.join(HERE, 'validation.py')}
        exec(compile(open(V['__file__']).read(), V['__file__'], 'exec'), V)
        print('Material validation:', V['validate_materials'](design))
        print('Automated validation:', V['validate_gimbal'](design, p, groups, report, dz))
        print(f'Connectivity: {"all junctions joined, all pins and bearings engaged" if not problems else problems}')
        print(f'Swept-motion checks: {checks} poses, {len(hits)} collisions')
        for h in hits[:15]:
            print('  COLLISION', h)
        printed = printed_est = 0.0
        print('P1B printed parts (PETG): solid upper bound / estimated at walls + infill:')
        for part in parts:
            solid, est = A['print_mass'](part, p)
            if part['name'] != 'gimbal_fit_coupon':
                printed += solid * part['qty']
                printed_est += est * part['qty']
            print(f"  {part['name']}: x{part['qty']}, {solid:.2f} / {est:.2f} g each")
        rods = sum(b.volume for b in groups['cage'].component.occurrences[0].component.bRepBodies if b.name.startswith('rods_')) * p['rod_density'] \
            if groups['cage'].component.occurrences.count else 0
        screws = int(16 * round(p['junction_screws_per_side'])) + 12   # 8 junctions x 2 sides + carrier/arm screws
        hardware = 6 * 0.2 + 6 * 0.26 + screws * 0.2   # 6 MR52ZZ, 6 cut pins, M2 screws
        added, added_est = rods + printed + hardware, rods + printed_est + hardware
        print(f'P1B added mass: rods {rods:.1f} g + printed {printed:.1f} g solid / {printed_est:.1f} g estimated + hardware ~{hardware:.1f} g ({screws} M2 screws)')
        print(f'  = {added:.1f} g solid-PETG scenario / {added_est:.1f} g infill scenario (hardware allowance unweighed)')
        masses = report['masses']
        planning, estimate = masses.get('thrust_planning_total_g'), masses.get('thrust_estimate_total_g')
        for label, base in (('450', m450), ('1100', m1100)):
            if masses.get('bare_aircraft_g') is not None:
                base = masses['bare_aircraft_g'] + masses['pack_' + label + '_g']
            hi_m, lo_m = base + added, base + added_est
            line = f'  with {label} mAh: accounted mass {lo_m:.2f}-{hi_m:.2f} g (unweighed extras excluded)'
            if masses.get('thrust_total_g'):
                thrust = masses['thrust_total_g']
                line += f'; at measured {thrust} g thrust {thrust / hi_m:.2f}-{thrust / lo_m:.2f}:1'
            elif planning:
                line += f'; at {planning} g planning thrust {planning / hi_m:.2f}-{planning / lo_m:.2f}:1'
            if estimate:
                line += f' (estimate range {estimate[0] / hi_m:.2f}-{estimate[1] / lo_m:.2f}:1)'
            line += f'; {175 - hi_m:.2f} g remaining to 175 g for excluded extras/tolerance'
            if hi_m > 175:
                raise RuntimeError('Accounted mass alone exceeds 175 g: ' + line)
            print(line)
        exported = A['export_stl'](parts, 'exports_p1b')
        print('STL exports:', exported)
    except Exception:
        print('FAILED:\n' + traceback.format_exc())
        raise
