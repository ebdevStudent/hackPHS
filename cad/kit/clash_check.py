"""Solid clash check: cage (exported hub meshes + rod cylinders) against prop volumes and outside objects.

Builds the P1A cage from cad/apex2-cage/exports hub STLs placed exactly as build_p1a.py places them, plus
every edge and pole rod as a cylinder. Prop volumes:
  P1A  the convex hull of each prop disk at every corner of the balancing travel (adj_x, adj_y);
  P1B  the sphere swept by the free-turning aircraft (generator's aircraft_radius) and the outer ring band.
Checks:
  1. the cage itself never intersects any prop volume;
  2. for each object diameter and each opening, a solid ball is pushed in along the opening's normal (at the
     opening centre and at the analytic worst-case position from opening_probe) until it first touches real
     hub/rod material, or passes through the opening; at that point its intersection volume and gap to the
     prop volumes are measured with Manifold Booleans.
Vendor/provisional dimensions; rigid, no rod deflection.
"""
import argparse
import json
import math
from pathlib import Path

import manifold3d as mf
import numpy as np

import cage_model
import opening_probe
from test_pieces import read_mesh_stl

EPS = 1e-4            # mm^3: Boolean volume treated as contact
SPHERE_SEGMENTS = 48
STEP = 1.0            # mm descent step before bisection
DIAMETERS = [10, 30, 60, 80, 84, 90, 100, 120, 150]


def to_manifold(triangles):
    vertices, index = np.unique(triangles.reshape(-1, 3).round(5), axis=0, return_inverse=True)
    mesh = mf.Mesh(vert_properties=vertices.astype(np.float32), tri_verts=index.reshape(-1, 3).astype(np.uint32))
    solid = mf.Manifold(mesh)
    if solid.status() != mf.Error.NoError: raise ValueError('Hub mesh is not a closed manifold')
    return solid


def placed(solid, frame):
    x, y, z, o = (np.asarray(frame[k], float) for k in ('x', 'y', 'z', 'origin'))
    return solid.transform(np.column_stack([x, y, z, o]).tolist())


def cylinder_between(a, b, radius, segments=16):
    a, b = np.asarray(a, float), np.asarray(b, float)
    axis = b - a; length = np.linalg.norm(axis); z = axis / length
    x = np.cross(z, [0, 0, 1.0] if abs(z[2]) < .9 else [1.0, 0, 0]); x /= np.linalg.norm(x); y = np.cross(z, x)
    return mf.Manifold.cylinder(length, radius, radius, segments).transform(np.column_stack([x, y, z, a]).tolist())


def build_cage(values):
    p1a = cage_model.load_generator('build_p1a.py')
    graph = p1a['cage_graph'](values)
    points, edges, pole_edges, _ = graph
    frames = p1a['hub_frames'](values, graph)
    groups = {}
    for frame in frames: groups.setdefault(frame['key'], []).append(frame)
    exports = cage_model.CAGE_DIR / 'exports'
    letters, used, hubs = iter('ABCD'), set(), []
    for key, members in sorted(groups.items(), key=lambda kv: (len(kv[0][0]), kv[0][1] is not None, -len(kv[1]))):
        arms, boss = key
        name = f'hub_{len(arms)}way_mount_{next(letters)}' if boss else {3: 'hub_3way', 4: 'hub_4way', 5: 'hub_pole_5way'}[len(arms)]
        if name in used: name += f'_variant{len(used)}'
        used.add(name)
        solid = to_manifold(read_mesh_stl(exports / f'{name}.stl'))
        hubs += [(frame['origin'], placed(solid, frame)) for frame in members]
    inset = values['hub_arm_len'] - values['socket_depth'] + values['rod_end_gap']
    rods = []
    for i, j in edges + pole_edges:
        a, b = np.asarray(points[i], float), np.asarray(points[j], float)
        u = (b - a) / np.linalg.norm(b - a)
        rods.append(((a + b) / 2, cylinder_between(a + u * inset, b - u * inset, values['rod_dia'] / 2)))
    return np.asarray(points, float), edges + pole_edges, hubs, rods


def p1a_props(values):
    half = values['motor_diag'] / 2 / math.sqrt(2)
    r, z0, h = values['prop_dia'] / 2, values['prop_z'], values['prop_disk_h']
    volumes = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            corners = [mf.Manifold.cylinder(h, r, r, 64).translate((sx * half + dx, sy * half + dy, z0))
                       for dx in (-values['adj_x'], values['adj_x']) for dy in (-values['adj_y'], values['adj_y'])]
            volumes.append(mf.Manifold.batch_hull(corners))
    return mf.Manifold.batch_boolean(volumes, mf.OpType.Add)


def local_cage(centre, hubs, rods, radius):
    near = [s for o, s in hubs if np.linalg.norm(np.asarray(o) - centre) < radius] + \
           [s for m, s in rods if np.linalg.norm(m - centre) < radius]
    return mf.Manifold.batch_boolean(near, mf.OpType.Add) if near else mf.Manifold()


def touches(a, b):
    return (a ^ b).volume() > EPS


def descend(lateral, normal, radius, cage, floor):
    """Push a ball along -normal from outside; return (centre height, passed_through)."""
    ball = mf.Manifold.sphere(radius, SPHERE_SEGMENTS)
    def at(h): return ball.translate(tuple(lateral + h * normal))
    h = radius + 6.0
    if touches(at(h), cage): return h, False
    while h > floor:
        lower = h - STEP
        if touches(at(lower), cage):
            hi, lo = h, lower
            for _ in range(20):
                mid = (hi + lo) / 2
                if touches(at(mid), cage): lo = mid
                else: hi = mid
            return hi, False
        h = lower
    return floor, True


def analyse(diameters=DIAMETERS):
    values = cage_model.parameters('p1a')
    p1b = cage_model.parameters('p1b')
    points, edges, hubs, rods = build_cage(values)
    cage = mf.Manifold.batch_boolean([s for _, s in hubs] + [s for _, s in rods], mf.OpType.Add)
    props = p1a_props(values)
    swept = cage_model.load_generator('build_p1b.py')['aircraft_radius'](p1b, opening_probe.P1B_DZ)
    ring_outer = math.ceil(swept + p1b['gimbal_clear']) + 2 * p1b['ring_w'] + p1b['ring_gap']
    swept_sphere = mf.Manifold.sphere(swept, 96)
    bounds = cage.bounding_box()
    result = {'cage': {'span_mm': [round(bounds[i + 3] - bounds[i], 2) for i in range(3)], 'hubs': len(hubs), 'rods': len(rods),
                       'volume_mm3': round(cage.volume(), 1), 'genus': cage.genus()},
              'self_clash': {'cage_x_p1a_props_mm3': round((cage ^ props).volume(), 6),
                             'cage_to_p1a_props_gap_mm': round(cage.min_gap(props, 60), 3),
                             'cage_x_p1b_swept_mm3': round((cage ^ swept_sphere).volume(), 6)},
              'p1b_swept_radius_mm': round(swept, 2), 'p1b_outer_ring_mm': ring_outer, 'probes': []}
    faces = opening_probe.faces(points, [tuple(e) for e in edges])
    rod_r = values['rod_dia'] / 2
    for d in diameters:
        r = d / 2
        row = {'diameter_mm': d, 'passes_through': [], 'p1a_prop_contact': False, 'p1a_min_gap_mm': None,
               'p1b_swept_contact': False, 'p1b_ring_contact': False, 'max_ball_cage_overlap_mm3': 0.0}
        gaps = []
        for face in faces:
            centres, passes = opening_probe.resting_centres(face, points, r, rod_r)
            n = face['normal']; plane = float(np.dot(face['centre'], n))
            laterals = [face['centre']]
            if len(centres):
                worst = centres[int(np.argmin(opening_probe.p1a_clearance(centres, r, values)))]
                laterals.append(worst - (np.dot(worst, n) - plane) * n)
            local = local_cage(face['centre'], hubs, rods, max(70.0, r + 60))
            for lateral in laterals:
                h, through = descend(lateral, n, r, local, -plane)
                ball = mf.Manifold.sphere(r, SPHERE_SEGMENTS).translate(tuple(lateral + h * n))
                if through:
                    row['passes_through'].append(len(face['vertices']))
                    row['p1a_prop_contact'] = row['p1b_swept_contact'] = row['p1b_ring_contact'] = True
                    continue
                row['max_ball_cage_overlap_mm3'] = max(row['max_ball_cage_overlap_mm3'], round((ball ^ local).volume(), 6))
                if touches(ball, props): row['p1a_prop_contact'] = True
                else: gaps.append(ball.min_gap(props, 40))
                centre_r = float(np.linalg.norm(lateral + h * n))
                if centre_r - r <= swept: row['p1b_swept_contact'] = True
                if centre_r - r <= ring_outer: row['p1b_ring_contact'] = True
        row['passes_through'] = sorted(set(row['passes_through']))
        if gaps and not row['p1a_prop_contact']: row['p1a_min_gap_mm'] = round(min(gaps), 2)
        result['probes'].append(row)
    result['scope'] = __doc__.strip()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'reports' / 'clash-check.json')
    args = parser.parse_args()
    report = analyse()
    args.output.parent.mkdir(exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=float) + '\n')
    print(json.dumps({k: report[k] for k in ('cage', 'self_clash')}, indent=2))
    for row in report['probes']: print(row)
