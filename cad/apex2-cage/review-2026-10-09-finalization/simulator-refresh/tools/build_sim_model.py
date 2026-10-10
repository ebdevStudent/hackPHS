"""Build the simulator's drone model from the P1B gimbal-cage CAD: static/assets/p1b.json.

Run from the repository root:  python tools/build_sim_model.py

P1B is the only version being built (user decision 2026-10-08). Everything comes from the generators and
their exports, never re-typed:
  * parameters, hub centres, rods, hub frames: cad/apex2-cage/build_p1a.py + build_p1b.py (via cad/kit/cage_model.py)
  * meshes: cad/apex2-cage/exports_p1b/*.stl, placed exactly as build_p1b.build() assembles them
  * part masses and thrust estimate: vendor_specs.json (+ measurements.json once filled in)
  * accounted totals, drag area, efficiency, bearing friction: motion_physics.json
Four rigid bodies share the pivot centre: cage -(Z pole pivot)- outer ring -(X pivot)- inner ring -(Y pivot)- aircraft.
Mass and inertia come from the exported meshes (solid integration) scaled to the accounted masses, plus vendor
masses at their CAD envelope positions. Values are vendor/CAD estimates until measured.

Axes: CAD is Z up, +Y forward, +X right, millimetres. The simulator (three.js) is Y up, -Z forward, +X right,
metres: (x, y, z)_cad -> (x, z, -y) / 1000.
"""
import base64
import hashlib
import json
import math
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# This Mac stores the authoritative CAD beside simulation/. The published
# checkout stores the simulator at the root. Never use an older copied CAD tree.
SOURCE_ROOT = ROOT.parent if (ROOT.parent/'cad/apex2-cage/build_p1b.py').is_file() else ROOT
CAD = SOURCE_ROOT / 'cad' / 'apex2-cage'
EXPORTS = CAD / 'exports_p1b'
OUT = ROOT / 'static' / 'assets' / 'p1b.json'
sys.path.insert(0, str(SOURCE_ROOT / 'cad' / 'kit'))
import cage_model  # noqa: E402

QUANT = 0.01                    # mm per int16 step
HUB_FILES = {(4, False): 'hub_4way', (3, False): 'hub_3way', (3, True): 'hub_3way_mount_A', (5, False): 'hub_pole_5way_pivot'}
AXES = ((1, 0, 0), (0, 0, 1), (0, -1, 0))                     # CAD -> simulator rotation (rows)
IDENTITY = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def mat_vec(m, v): return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))
def mat_mul(a, b): return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
def transpose(m): return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


class Place:
    """Rigid placement x -> R x + t in CAD millimetres."""
    def __init__(self, R=IDENTITY, t=(0, 0, 0)): self.R, self.t = R, tuple(t)
    def __call__(self, v): return tuple(a + b for a, b in zip(mat_vec(self.R, v), self.t))
    def then(self, other): return Place(mat_mul(other.R, self.R), other(self.t))      # apply self, then other

    def sim_matrix(self):
        """Column-major 4x4 for three.js: mesh vertices in local CAD mm (scaled to m), output in simulator axes."""
        R = mat_mul(AXES, self.R)
        t = tuple(c / 1000 for c in mat_vec(AXES, self.t))
        return [round(v, 7) for v in (R[0][0], R[1][0], R[2][0], 0, R[0][1], R[1][1], R[2][1], 0, R[0][2], R[1][2], R[2][2], 0, *t, 1)]


def to_sim(v): return tuple(c / 1000 for c in mat_vec(AXES, v))


_stl = {}
def read_stl(name):
    if name not in _stl:
        data = (EXPORTS / f'{name}.stl').read_bytes()
        count = struct.unpack('<I', data[80:84])[0]
        if len(data) != 84 + 50 * count:
            raise ValueError(f'{name}: not a binary STL')
        _stl[name] = [[struct.unpack_from('<3f', data, 84 + 50 * i + 12 + 12 * k) for k in range(3)] for i in range(count)]
    return _stl[name]


def integrals(tris, place):
    """Volume (mm^3), first moment (mm^4) and second-moment matrix (mm^5) of a closed mesh after placement."""
    V, S, C = 0.0, [0.0] * 3, [[0.0] * 3 for _ in range(3)]
    for tri in tris:
        a, b, c = (place(v) for v in tri)
        det = a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
        V += det / 6
        s = [a[k] + b[k] + c[k] for k in range(3)]
        for k in range(3):
            S[k] += det / 24 * s[k]
        for i in range(3):
            for j in range(3):
                C[i][j] += det / 120 * (a[i] * a[j] + b[i] * b[j] + c[i] * c[j] + s[i] * s[j])
    return V, S, C


class Body:
    """Mass (g), first moment (g mm) and second moment (g mm^2) in CAD coordinates about the pivot centre."""
    def __init__(self): self.m, self.S, self.C = 0.0, [0.0] * 3, [[0.0] * 3 for _ in range(3)]

    def mesh(self, V, S, C, grams):
        rho = grams / V
        self.m += grams
        for k in range(3): self.S[k] += rho * S[k]
        for i in range(3):
            for j in range(3): self.C[i][j] += rho * C[i][j]

    def point(self, grams, r, box=None):
        self.m += grams
        for k in range(3): self.S[k] += grams * r[k]
        for i in range(3):
            for j in range(3): self.C[i][j] += grams * r[i] * r[j]
        if box:                                      # solid box about its own centre
            for k in range(3): self.C[k][k] += grams * box[k] ** 2 / 12

    def export(self):
        """Mass (kg), centre of mass (m) and inertia about the pivot centre (kg m^2), simulator axes."""
        tr = sum(self.C[k][k] for k in range(3))
        inertia = tuple(tuple(((tr if i == j else 0) - self.C[i][j]) for j in range(3)) for i in range(3))
        inertia = mat_mul(mat_mul(AXES, inertia), transpose(AXES))
        com = to_sim([s / self.m for s in self.S])
        return {'mass_kg': round(self.m / 1000, 6), 'com_m': [round(c, 6) for c in com],
                'inertia_kgm2': [[round(v * 1e-9, 10) for v in row] for row in inertia]}


def pack_mesh(tris, place=Place()):
    """Bake a placement, weld, quantise to int16 (0.01 mm) and base64-encode. Vertices stay in CAD axes, mm."""
    lookup, positions, indices = {}, [], []
    for tri in tris:
        for v in tri:
            key = tuple(round(c / QUANT) for c in place(v))
            if max(abs(k) for k in key) > 32767: raise ValueError('mesh exceeds the int16 range')
            if key not in lookup:
                lookup[key] = len(lookup); positions.extend(key)
            indices.append(lookup[key])
    face = [indices[i:i + 3] for i in range(0, len(indices), 3)]
    indices = [i for f in face if len(set(f)) == 3 for i in f]
    kind = 'H' if len(lookup) < 65536 else 'I'
    return {'scale': QUANT / 1000, 'triangles': len(indices) // 3,
            'position': base64.b64encode(struct.pack(f'<{len(positions)}h', *positions)).decode(),
            'index': base64.b64encode(struct.pack(f'<{len(indices)}{kind}', *indices)).decode(), 'index_type': kind}


def bake(items):
    """[(stl name, Place)] -> one mesh in the body frame (CAD axes)."""
    return pack_mesh([[place(v) for v in t] for name, place in items for t in read_stl(name)])


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    export_manifest = json.loads((EXPORTS/'manifest.json').read_text())
    for source, digest in export_manifest['sources'].items():
        if sha(CAD/source) != digest:
            raise ValueError('Regenerate CAD before simulation: ' + source)
    for part in export_manifest['parts']:
        if sha(EXPORTS/(part['name']+'.stl')) != part['sha256']:
            raise ValueError('Changed CAD mesh: ' + part['name'])
    p = cage_model.parameters('p1b')
    A = cage_model.load_generator('build_p1a.py')
    B = cage_model.load_generator('build_p1b.py')
    points, edges, pole_edges, mounts = A['cage_graph'](p)
    frames = A['hub_frames'](p, (points, edges, pole_edges, mounts))
    masses = cage_model.masses()
    motion = json.loads((CAD / 'motion_physics.json').read_text())
    inputs = motion['inputs']
    petg = p['petg_density'] / 1000                                                  # g/mm^3

    # ---- aircraft raise (as build_p1b.build): the 450 mAh CG on the pivot centre; the 1100 pack uses the CG slots
    carrier_g = (integrals(read_stl('carrier_plate'), Place())[0] + integrals(read_stl('nut_shield_plate'), Place())[0]) * petg
    arms_g = 2 * integrals(read_stl('support_arm_p1b'), Place())[0] * petg
    cg450, _ = B['cg_offset'](p, masses, carrier_g, arms_g, '450')
    cg1100, _ = B['cg_offset'](p, masses, carrier_g, arms_g, '1100')
    dz = -cg450
    slot = {'450': 0.0, '1100': min(p['cg_slot'], cg450 - cg1100)}

    def radial(name):                                                              # ring radii from the exported quarters
        r = [math.hypot(v[0], v[1]) for t in read_stl(name) for v in t]
        return round(min(r), 2), round(max(r), 2)
    rings = {'inner': radial('inner_ring_quarter'), 'outer': radial('outer_ring_quarter')}

    # ---- placements exactly as build_p1b.build()
    outer_base = Place(((1, 0, 0), (0, 0, -1), (0, 1, 0)))                          # ring-local x->X, y->Z, z->-Y
    ring_parts = {
        'outer': [('outer_ring_quarter', a) for a in (0, 90, 180, 270)] + [('outer_junction_X_bearing', 0), ('outer_junction_X_bearing', 180),
                                                                          ('outer_junction_Z_bearing', 90), ('outer_junction_Z_bearing', 270)],
        'inner': [('inner_ring_quarter', a) for a in (0, 90, 180, 270)] + [('inner_junction_Y_bearing', 90), ('inner_junction_Y_bearing', 270),
                                                                          ('inner_junction_X_pin', 0), ('inner_junction_X_pin', 180)],
    }
    ring_place = {'outer': lambda a: Place(rot_z(a)).then(outer_base), 'inner': lambda a: Place(rot_z(a))}
    printed = {k: [(n, ring_place[k](ang)) for n, ang in v] for k, v in ring_parts.items()}
    lifted = lambda extra=0.0, turn=0: Place(rot_z(turn)).then(Place(t=(0, 0, dz + extra)))     # noqa: E731
    mount_parts = lambda extra: [('carrier_plate', lifted(extra)), ('nut_shield_plate', lifted(extra)),   # noqa: E731
                                 ('support_arm_p1b', lifted(extra, 90)), ('support_arm_p1b', lifted(extra, -90))]
    block_parts = [('arm_pivot_block', Place(rot_z(90))), ('arm_pivot_block', Place(rot_z(-90)))]

    # ---- cage: hubs placed by the generator's hub frames, rods socket to socket
    hubs = []
    for f in frames:
        name = HUB_FILES[(len(f['key'][0]), f['key'][1] is not None)]
        R = tuple(tuple((f['x'], f['y'], f['z'])[c][r] for c in range(3)) for r in range(3))   # columns = hub axes
        hubs.append({'type': name, 'place': Place(R, f['origin'])})
    inset = p['hub_arm_len'] - p['socket_depth'] + p['rod_end_gap']
    rods = []
    for i, j in edges + pole_edges:
        a, b = points[i], points[j]
        length = math.dist(a, b)
        u = [(b[k] - a[k]) / length for k in range(3)]
        rods.append((tuple(a[k] + u[k] * inset for k in range(3)), tuple(b[k] - u[k] * inset for k in range(3))))

    # ---- mass properties per body (accounted totals from motion_physics: cage 24.8, rings 31.3, aircraft side 88.8/110.8)
    cage = Body()
    hub_int = [integrals(read_stl(h['type']), h['place']) for h in hubs]
    hub_volume = sum(V for V, _, _ in hub_int)
    hub_grams = sum(row['native_volume_mm3']*row['qty']*petg for row in export_manifest['parts'] if row['name'].startswith('hub_'))
    for V, S, C in hub_int:
        cage.mesh(V, S, C, hub_grams * V / hub_volume)
    rod_len = sum(math.dist(a, b) for a, b in rods)
    rod_grams = inputs['cage_mass_g'] - hub_grams - .52
    for a, b in rods:                                                              # thin rods: five point masses each
        for k in range(5):
            t = (k + 0.5) / 5
            cage.point(rod_grams * math.dist(a, b) / rod_len / 5, tuple(a[c] + (b[c] - a[c]) * t for c in range(3)))
    for sign in (-1, 1):
        cage.point(.26, (0, 0, sign*(p['cage_vertex_r']-p['pole_boss_len'])))

    ring_body = {'outer': Body(), 'inner': Body()}
    ring_printed_g = inputs['ring_mass_g'] - 3.2 - 1.2 - .52                    # 16 screws, six bearings, two inner pins
    ring_int = {k: [(n, pl, integrals(read_stl(n), pl)) for n, pl in printed[k]] for k in printed}
    ring_volume = sum(I[0] for k in ring_int for _, _, I in ring_int[k])
    for k in ring_int:
        for _, _, (V, S, C) in ring_int[k]:
            ring_body[k].mesh(V, S, C, ring_printed_g * V / ring_volume)
    rm = {k: (rings[k][0] + rings[k][1]) / 2 for k in rings}
    for k in ring_int:                                                            # 16 splice screws (3.2 g), 2 per junction
        for n, pl, _ in ring_int[k]:
            if 'junction' in n:
                ring_body[k].point(0.4, pl((rm[k], 0, 0)))
    for sign in (-1, 1):
        ring_body['inner'].point(.26, (sign*rm['inner'], 0, 0))
    pole_r = p['cage_vertex_r'] - p['pole_boss_len']
    for r in ((rm['outer'], 0, 0), (-rm['outer'], 0, 0), (0, 0, pole_r), (0, 0, -pole_r)):      # MR52ZZ bearings, 0.2 g each
        ring_body['outer'].point(0.2, r)
    for r in ((0, rm['inner'], 0), (0, -rm['inner'], 0)):
        ring_body['inner'].point(0.2, r)

    half = p['motor_diag'] / 2
    motor_xy = [(half * math.cos(math.radians(a)), half * math.sin(math.radians(a))) for a in (45, 135, 225, 315)]
    pack_top = -p['frame_t'] - p['carrier_t'] - p['battery_gap'] - p['battery_shield_t']
    aircraft = {}
    for pack in ('450', '1100'):
        body, up = Body(), dz + slot[pack]
        l, w, h = p[f'batt{pack}_l'], p[f'batt{pack}_w'], p[f'batt{pack}_h']
        body.point(masses['frame_g'], (0, 0, up - p['frame_t'] / 2), (p['motor_diag'] * 0.75, p['motor_diag'] * 0.75, p['frame_t']))
        body.point(masses['aio_g'], (0, 0, up + 8.0))                                # generator's cg_offset places the AIO at 8 mm
        body.point(masses['camera_g'], (0, p['cam_y'], up + p['cam_z']))
        body.point(masses[f'pack_{pack}_g'], (0, 0, up + pack_top - h / 2), (w, l, h))
        for x, y in motor_xy:
            body.point(masses['motors_x4_g'] / 4, (x, y, up + p['motor_h'] / 2))
            body.point(masses['props_x4_g'] / 4, (x, y, up + p['prop_z'] + p['prop_disk_h'] / 2))
        rest = inputs['aircraft_inner_g'][f'P1B + {pack}'] - body.m                 # printed mount + screws + pins
        parts = [(n, pl, integrals(read_stl(n), pl)) for n, pl in mount_parts(slot[pack]) + block_parts]
        volume = sum(I[0] for _, _, I in parts)
        for _, _, (V, S, C) in parts:
            body.mesh(V, S, C, rest * V / volume)
        aircraft[pack] = body.export() | {'slot_raise_mm': round(slot[pack], 2), 'mount_and_hardware_g': round(rest, 2)}

    total = {pack: cage.m + ring_body['outer'].m + ring_body['inner'].m + aircraft[pack]['mass_kg'] * 1000 for pack in aircraft}
    for pack in total:
        assert abs(total[pack]-inputs['mass_g'][f'P1B + {pack}']) < .001
    keep = ['rod_dia', 'hub_core_r', 'hub_arm_len', 'hub_arm_od', 'cage_edge', 'cage_vertex_r', 'cage_outer_dia', 'motor_diag', 'prop_dia',
            'prop_z', 'prop_disk_h', 'motor_od', 'motor_h', 'frame_t', 'arm_w', 'stack_w', 'stack_h', 'cam_size', 'cam_y', 'cam_z', 'cam_tilt',
            'cam_hfov', 'batt450_l', 'batt450_w', 'batt450_h', 'batt1100_l', 'batt1100_w', 'batt1100_h', 'carrier_t', 'battery_gap',
            'battery_shield_t', 'antenna_len', 'antenna_d', 'frame_column_h']
    stl_names = sorted({*HUB_FILES.values(), 'carrier_plate', 'nut_shield_plate', 'support_arm_p1b', 'arm_pivot_block',
                        *(n for v in ring_parts.values() for n, _ in v)})
    sources = ['build_p1a.py', 'build_p1b.py', 'vendor_specs.json', 'measurements.json', 'fit_results.json', 'motion_physics.json', 'exports_p1b/manifest.json'] + [f'exports_p1b/{n}.stl' for n in stl_names]
    model = {
        'design': 'P1B two-ring gimbal cage', 'generated': date.today().isoformat(), 'generator': 'tools/build_sim_model.py',
        'status': 'vendor/provisional CAD and estimates; nothing here is a measured result',
        'sources': {s: sha(CAD / s) for s in sources},
        'params_mm': {k: round(p[k], 4) for k in keep + ['pivot_gap', 'rod_bore_clear', 'm2_tap', 'pin_press_horizontal_d', 'pin_press_vertical_d', 'bearing_seat_clear']} | {'aircraft_raise': round(dz, 3), 'inner_ring': rings['inner'], 'outer_ring': rings['outer']},
        'hub_meshes': {n: pack_mesh(read_stl(n)) for n in sorted({h['type'] for h in hubs})},
        'hubs': [{'type': h['type'], 'matrix': h['place'].sim_matrix()} for h in hubs],
        'hub_radius_m': p['hub_core_r'] / 1000,
        'rods': [[round(c, 6) for c in (*to_sim(a), *to_sim(b))] for a, b in rods],
        'meshes': {'outer': bake(printed['outer']), 'inner': bake(printed['inner']), 'mount': bake(mount_parts(0.0)), 'blocks': bake(block_parts)},
        'bodies': {'cage': cage.export(), 'outer': ring_body['outer'].export(), 'inner': ring_body['inner'].export(), 'aircraft': aircraft},
        'configs': {pack: {'label': f'P1B + {pack} mAh', 'total_g': round(total[pack], 2), 'cda_m2': sum(motion['speed'][f'P1B + {pack}']['cda_m2']) / 2,
                           'pack': {'capacity_ah': inputs['pack'][pack], 'mass_g': masses[f'pack_{pack}_g']}} for pack in aircraft},
        'flight': {'thrust_total_g': inputs['thrust_total_g'], 'throttle_exponent': inputs['throttle_exponent'],
                   'figure_of_merit': inputs['figure_of_merit'], 'drive_efficiency': inputs['drive_efficiency'],
                   'usable_fraction': inputs['usable_fraction'], 'floor_mu': inputs['floor_mu'],
                   'bearing_friction_nmm': inputs['bearing_friction_nmm'], 'cage_capacity_j': motion['impact']['cage_capacity_j']},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(model, separators=(',', ':')))
    print(f'{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1024:.0f} KiB; aircraft raised {dz:.2f} mm (generator report: 3.51); '
          f'rings inner {rings["inner"]}, outer {rings["outer"]} mm (report: 84-89, 94-99)')
    for name, b in [('cage', cage), ('outer', ring_body['outer']), ('inner', ring_body['inner'])]:
        e = b.export()
        print(f'  {name:8s} {b.m:6.2f} g  COM {[round(c * 1000, 2) for c in e["com_m"]]} mm  I diag {[round(e["inertia_kgm2"][k][k] * 1e6, 1) for k in range(3)]} kg m^2 x1e-6')
    for pack, a in aircraft.items():
        print(f'  aircraft {pack:>4s}: {a["mass_kg"] * 1000:6.2f} g  COM {[round(c * 1000, 2) for c in a["com_m"]]} mm  I diag '
              f'{[round(a["inertia_kgm2"][k][k] * 1e6, 1) for k in range(3)]}  slot +{a["slot_raise_mm"]} mm; total {total[pack]:.2f} g '
              f'(motion_physics {inputs["mass_g"][f"P1B + {pack}"]})')


if __name__ == '__main__':
    main()
