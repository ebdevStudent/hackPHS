"""Can an outside object get through a cage opening and reach a prop before the cage stops it?

Model: a round object of diameter D (ball, pole end, a rounded corner) is pushed straight in through each
opening of the truncated-icosahedron cage until it rests on the rods. Rods are cylinders of the measured
diameter between hub centres; hub bodies are ignored, which makes openings look larger, so results err
toward more intrusion. For every resting position on a lateral grid over the opening, the object's
clearance to the props is computed:
  P1A  four prop-disk cylinders, each grown by the full X/Y balancing travel;
  P1B  the sphere swept by the free-turning aircraft (generator's own aircraft_radius), plus the outer
       gimbal ring band, whose contact is a jam risk rather than a prop strike.
Only vendor/provisional dimensions until measurements.json is filled. Straight edges and flat walls
cannot pass a convex opening; small corners and thin poles behave like small D.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

import cage_model

def finite(value):
    return None if not math.isfinite(value) else round(float(value), 2)


DIAMETERS = [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150]
GRID_MM = 1.0
P1B_DZ = 3.25          # aircraft raised so the estimated 450 mAh CG sits on the pivots (generator report)


def faces(points, edges):
    """Faces of the convex cage graph, outward normals, by walking a planar embedding."""
    neighbours = {i: [] for i in range(len(points))}
    for i, j in edges:
        neighbours[i].append(j); neighbours[j].append(i)
    order = {}
    for v, around in neighbours.items():
        n = points[v] / np.linalg.norm(points[v])
        a = np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < .9 else [1.0, 0.0, 0.0]); a /= np.linalg.norm(a)
        b = np.cross(n, a)
        order[v] = sorted(around, key=lambda u: math.atan2(np.dot(points[u] - points[v], b), np.dot(points[u] - points[v], a)))
    seen, result = set(), []
    for i, j in edges:
        for start in ((i, j), (j, i)):
            if start in seen: continue
            cycle, (u, v) = [], start
            while (u, v) not in seen:
                seen.add((u, v)); cycle.append(u)
                ring = order[v]
                w = ring[(ring.index(u) - 1) % len(ring)]
                u, v = v, w
            result.append(cycle)
    # The outer walk of a convex polyhedron graph has as many vertices as the largest face only if
    # mis-oriented; keep faces whose vertices are coplanar.
    out = []
    for cycle in result:
        poly = points[cycle]
        centre = poly.mean(axis=0)
        normal = np.cross(poly[1] - poly[0], poly[2] - poly[0]); normal /= np.linalg.norm(normal)
        if np.dot(normal, centre) < 0: normal = -normal
        if np.max(np.abs((poly - centre) @ normal)) < 1e-6 and len(cycle) <= 6:
            out.append({'vertices': cycle, 'centre': centre, 'normal': normal})
    return out


def segment_distance(centres, a, b):
    """Distance from many points (N,3) to segment ab."""
    ab = b - a
    t = np.clip(((centres - a) @ ab) / np.dot(ab, ab), 0, 1)
    return np.linalg.norm(centres - (a + t[:, None] * ab), axis=1)


def resting_centres(face, points, radius, rod_r):
    """Where the object first rests on this opening's rods, for each lateral grid position.

    The opening's rods lie in its plane, so a centre at in-plane distance d from a rod axis touches it at
    height h = sqrt(reach^2 - d^2) above the plane (reach = radius + rod radius). Pushed straight in, the
    object stops at the largest such h; where every d >= reach it passes through. Exact for this rod
    model; adjacent openings' rods and hub bodies are ignored (conservative: more intrusion)."""
    poly = points[face['vertices']]
    n, c = face['normal'], face['centre']
    u = poly[0] - c; u -= np.dot(u, n) * n; u /= np.linalg.norm(u)
    w = np.cross(n, u)
    local = np.stack([(poly - c) @ u, (poly - c) @ w], axis=1)
    span = np.abs(local).max()
    xs = np.arange(-span, span + GRID_MM, GRID_MM)
    # The deepest rest of a round object on a convex opening is at its incentre (the centroid for these
    # regular faces), so include that point exactly in addition to the grid.
    grid = np.array([(0.0, 0.0)] + [(x, y) for x in xs for y in xs])
    orientation = np.sign((local[1, 0] - local[0, 0]) * (local[2, 1] - local[1, 1]) - (local[1, 1] - local[0, 1]) * (local[2, 0] - local[1, 0]))
    inside = np.ones(len(grid), bool)
    for k in range(len(local)):           # convex polygon test (vertices are ordered)
        p, q = local[k], local[(k + 1) % len(local)]
        inside &= ((q[0] - p[0]) * (grid[:, 1] - p[1]) - (q[1] - p[1]) * (grid[:, 0] - p[0])) * orientation >= 0
    grid = grid[inside]
    flat = np.column_stack([grid, np.zeros(len(grid))])
    reach = radius + rod_r
    heights = np.full(len(grid), -np.inf)
    for k in range(len(local)):
        a = np.append(local[k], 0.0); b = np.append(local[(k + 1) % len(local)], 0.0)
        d = segment_distance(flat, a, b)
        heights = np.maximum(heights, np.where(d < reach, np.sqrt(np.maximum(0, reach ** 2 - d ** 2)), -np.inf))
    passes = ~np.isfinite(heights)
    resting = heights[~passes]
    lateral = c + grid[~passes, :1] * u + grid[~passes, 1:] * w
    return lateral + resting[:, None] * n, passes


def p1a_clearance(centres, radius, values):
    half = values['motor_diag'] / 2 / math.sqrt(2)
    grow = math.hypot(values['adj_x'], values['adj_y'])
    disk_r = values['prop_dia'] / 2 + grow
    z0, z1 = values['prop_z'], values['prop_z'] + values['prop_disk_h']
    best = np.full(len(centres), np.inf)
    for sx in (-1, 1):
        for sy in (-1, 1):
            radial = np.maximum(0, np.hypot(centres[:, 0] - sx * half, centres[:, 1] - sy * half) - disk_r)
            axial = np.maximum(0, np.maximum(z0 - centres[:, 2], centres[:, 2] - z1))
            best = np.minimum(best, np.hypot(radial, axial) - radius)
    return best


def analyse(diameters=DIAMETERS, measurements=None):
    values = cage_model.parameters('p1a', measurements)
    p1b = cage_model.parameters('p1b', measurements)
    points, edges, pole_edges = cage_model.cage_geometry(values)
    points = np.array(points, float)
    face_list = faces(points, edges + pole_edges)
    rod_r = values['rod_dia'] / 2
    swept = cage_model.load_generator('build_p1b.py')['aircraft_radius'](p1b, P1B_DZ)
    ring_inner = math.ceil(swept + p1b['gimbal_clear'])
    ring_outer = ring_inner + 2 * p1b['ring_w'] + p1b['ring_gap']
    shapes = {}
    for f in face_list: shapes[len(f['vertices'])] = shapes.get(len(f['vertices']), 0) + 1
    rows = []
    for d in diameters:
        r = d / 2
        worst = {'p1a': (np.inf, None), 'p1b_prop': (np.inf, None), 'p1b_ring': (np.inf, None)}
        through, deepest = [], 0.0
        for index, face in enumerate(face_list):
            centres, passes = resting_centres(face, points, r, rod_r)
            if passes.any():
                # Passing through an opening means it can reach anything inside the cage.
                through.append(len(face['vertices']))
                worst = {key: (-np.inf, len(face['vertices'])) for key in worst}
                deepest = np.inf
                continue
            if worst['p1a'][0] == -np.inf: continue
            plane = np.dot(face['centre'], face['normal'])
            depth = float(np.max(plane - (centres @ face['normal'] - r)))
            deepest = max(deepest, depth)
            radius_from_centre = np.linalg.norm(centres, axis=1) - r
            for key, value in (('p1a', p1a_clearance(centres, r, values).min()),
                               ('p1b_prop', (radius_from_centre - swept).min()),
                               ('p1b_ring', (radius_from_centre - ring_outer).min())):
                if value < worst[key][0]: worst[key] = (float(value), len(face['vertices']))
        rows.append({'diameter_mm': d, 'passes_through_openings': sorted(set(through)),
                     'max_intrusion_below_rod_plane_mm': None if deepest == np.inf else round(deepest, 2),
                     # None: the object passes straight through an opening (unbounded intrusion).
                     'p1a_min_prop_clearance_mm': finite(worst['p1a'][0]),
                     'p1b_min_swept_prop_clearance_mm': finite(worst['p1b_prop'][0]),
                     'p1b_min_outer_ring_clearance_mm': finite(worst['p1b_ring'][0]),
                     'p1a_reaches_prop': worst['p1a'][0] <= 0,
                     'p1b_can_reach_prop': worst['p1b_prop'][0] <= 0,
                     'p1b_can_touch_ring': worst['p1b_ring'][0] <= 0})
    def opening(sides):
        f = next(f for f in face_list if len(f['vertices']) == sides)
        poly = points[f['vertices']]
        inradius = min(segment_distance(f['centre'][None], poly[k], poly[(k + 1) % sides])[0] for k in range(sides))
        return {'count': shapes[sides], 'clear_circle_diameter_mm': round(2 * (inradius - rod_r), 2),
                'vertex_to_vertex_mm': round(float(np.max(np.linalg.norm(poly[:, None] - poly[None], axis=2))), 2)}
    return {'openings': {name: opening(sides) for sides, name in ((6, 'hexagon'), (5, 'pentagon'), (3, 'pole_triangle')) if sides in shapes},
            'face_count': len(face_list), 'p1b_swept_aircraft_radius_mm': round(swept, 2),
            'p1b_outer_ring_radius_mm': ring_outer, 'rod_diameter_mm': values['rod_dia'],
            'p1a_prop_travel_allowance_mm': round(math.hypot(values['adj_x'], values['adj_y']), 2),
            'probes': rows, 'scope': __doc__.strip()}


def markdown(result):
    lines = ['| Object diameter | Passes an opening | Intrusion below rods | P1A prop clearance | P1B swept-prop clearance | P1B ring clearance |',
             '| --- | --- | --- | --- | --- | --- |']
    for r in result['probes']:
        names = ', '.join({6: 'hexagon', 5: 'pentagon', 3: 'pole triangle'}[s] for s in r['passes_through_openings'] if s in (3, 5, 6)) or 'no'
        def fmt(v, hit): return ('**REACHES**' if hit or v is None else f'{v:.1f} mm')
        intrusion = 'passes through' if r['max_intrusion_below_rod_plane_mm'] is None else f"{r['max_intrusion_below_rod_plane_mm']:.1f} mm"
        lines.append(f"| {r['diameter_mm']} mm | {names} | {intrusion} | "
                     f"{fmt(r['p1a_min_prop_clearance_mm'], r['p1a_reaches_prop'])} | "
                     f"{fmt(r['p1b_min_swept_prop_clearance_mm'], r['p1b_can_reach_prop'])} | "
                     f"{fmt(r['p1b_min_outer_ring_clearance_mm'], r['p1b_can_touch_ring'])} |")
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'reports' / 'opening-probe.json')
    args = parser.parse_args()
    result = analyse()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=float))
    args.output.with_suffix('.md').write_text(markdown(result) + '\n')
    print(json.dumps(result['openings'], indent=2))
    print(markdown(result))
