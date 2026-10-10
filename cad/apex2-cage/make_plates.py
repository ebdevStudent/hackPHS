"""Arrange exported STLs into Monoprice Voxel plates (150 x 150 mm bed, 140 mm used).

Run with numpy:  python make_plates.py        (P1A: exports/ -> plates/)
                 python make_plates.py p1b    (P1B gimbal: exports_p1b/ + shared P1A parts -> plates_p1b/)
Each part is re-oriented for printing, centred on its footprint, dropped to Z = 0 and row-packed. Nested
entries (ring quarters) keep their shared arc centre so an inner quarter sits inside an outer one.
Plates are a starting layout: check brim/skirt overlap in the slicer.
"""
import hashlib
import json
import math
import collections
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BED_USED = 140.0
FLIP_X = np.diag([1.0, -1.0, -1.0])                         # face-down (rotate 180 deg about X)
X_UP = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float)  # part's +X axis becomes +Z

LAYOUT = {
    'plate_1_fit_strip_and_rod_jig': [('socket_fit_strip', 1), ('rod_cutting_jig', 1)],
    'plate_2_hubs_3way_a': [('hub_3way', 36)],
    'plate_3_hubs_mixed': [('hub_3way', 10), ('hub_3way_mount_A', 4), ('hub_4way', 10), ('hub_pole_5way', 2)],
    'plate_4_carrier_supports': [('carrier_plate', 1), ('nut_shield_plate', 1), ('support_arm', 2), ('x_bracket', 2)],
    # Test before the full hub batch: assemble one hexagon + one pentagon; the hubs are reusable in the cage.
    'plate_T_cage_section_test': [('hub_3way', 10)],
}
LAYOUT_P1B = {
    # Only P1B is built (user decision, 2026-10-08): its own hub plates. The pivot pole hubs are on the junctions plate.
    'p1b_plate_T_cage_section_test': [('hub_3way', 10)],
    'p1b_plate_hubs_3way_a': [('hub_3way', 36)],
    'p1b_plate_hubs_mixed': [('hub_3way', 10), ('hub_3way_mount_A', 4), ('hub_4way', 10)],
    # One complete ring per plate: four identical quarters stacked diagonally (see DIAGONAL).
    'p1b_plate_inner_ring_4_quarters': [('inner_ring_quarter', 4)],
    'p1b_plate_outer_ring_4_quarters': [('outer_ring_quarter', 4)],
    'p1b_plate_0_gimbal_fit_coupon_PRINT_FIRST': [('gimbal_fit_coupon', 1)],
    'p1b_plate_junctions_pivots': [('outer_junction_Z_bearing', 2), ('outer_junction_X_bearing', 2), ('inner_junction_X_pin', 2),
                                   ('inner_junction_Y_bearing', 2), ('arm_pivot_block', 2), ('hub_pole_5way_pivot', 2)],
    'p1b_plate_carrier_arms': [('carrier_plate', 1), ('nut_shield_plate', 1), ('support_arm_p1b', 2)],
}
LAY_FLAT = {'x_bracket': np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float),  # X thickness -> Z
            'arm_pivot_block': X_UP,
            'outer_junction_Z_bearing': FLIP_X, 'outer_junction_X_bearing': FLIP_X,
            'inner_junction_X_pin': FLIP_X, 'inner_junction_Y_bearing': FLIP_X}
SOURCE_FOLDER = HERE / 'exports'

def validate_mesh(triangles, label):
    if not len(triangles) or not np.isfinite(triangles).all():
        raise ValueError('Empty/nonfinite mesh: ' + label)
    edges = collections.Counter()
    directed = collections.Counter()
    for tri in triangles:
        pts = [tuple(p) for p in tri]
        for a,b in zip(pts, pts[1:] + pts[:1]):
            if a == b: raise ValueError('Degenerate edge: ' + label)
            edges[tuple(sorted((a,b)))] += 1
            directed[(a,b)] += 1
    if any(n != 2 for n in edges.values()) or any(directed[(a,b)] != directed[(b,a)] for a,b in edges):
        raise ValueError('Open/nonmanifold/inconsistently wound mesh: ' + label)



def read(path):
    data = path.read_bytes()
    count = struct.unpack('<I', data[80:84])[0]
    if 84 + count * 50 == len(data):
        result = np.frombuffer(data[84:], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))['v'].reshape(-1, 3, 3).astype(float)
        validate_mesh(result, str(path))
        return result
    lines = [l.split()[1:] for l in data.decode().splitlines() if l.strip().startswith('vertex')]
    result = np.array(lines, float).reshape(-1, 3, 3)
    validate_mesh(result, str(path))
    return result


def write(path, triangles):
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    record = np.zeros(len(triangles), dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
    record['n'], record['v'] = normals, triangles.reshape(-1, 9)
    path.write_bytes(b'Ball Drone P1A plate'.ljust(80, b' ') + struct.pack('<I', len(triangles)) + record.tobytes())


def source(name):
    path = SOURCE_FOLDER / f'{name}.stl'
    if not path.exists():
        raise FileNotFoundError('Missing export for selected design: ' + str(path))
    return path


def normalised(name):
    if isinstance(name, tuple):   # nested group: keep shared coordinates
        triangles = np.concatenate([read(source(n)) for n in name])
    else:
        triangles = read(source(name))
        if name in LAY_FLAT:
            triangles = triangles @ LAY_FLAT[name].T
    low, high = triangles.reshape(-1, 3).min(0), triangles.reshape(-1, 3).max(0)
    triangles = triangles - np.array([(low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2]])
    return triangles, high - low


# Ring quarters are thin arcs: copies stacked along the arc bisector nest inside each other. Value = step in mm
# (11.2 mm is the minimum for a 4 mm part gap, measured on the exported quarters; 13 mm leaves ~5.6 mm).
DIAGONAL = {'p1b_plate_inner_ring_4_quarters': 13.0, 'p1b_plate_outer_ring_4_quarters': 13.0}


# Hub plates need room for a 3 mm brim around every small part without brims merging.
GAPS = {'plate_2_hubs_3way_a': 7.0, 'plate_3_hubs_mixed': 7.0, 'plate_T_cage_section_test': 7.0,
        'p1b_plate_T_cage_section_test': 7.0, 'p1b_plate_hubs_3way_a': 7.0, 'p1b_plate_hubs_mixed': 7.0}


def shelf_pack(items, gap=4.0):
    """Simple row packing, largest first; raises if the plate overflows."""
    items = sorted(items, key=lambda item: -item[1][1])
    placed, x, y, row_h = [], 0.0, 0.0, 0.0
    for triangles, size in items:
        if x + size[0] > BED_USED:
            x, y, row_h = 0.0, y + row_h + gap, 0.0
        if y + size[1] > BED_USED or size[0] > BED_USED:
            raise ValueError('plate overflow')
        placed.append(triangles + np.array([x + size[0] / 2 - BED_USED / 2, y + size[1] / 2 - BED_USED / 2, 0]))
        x, row_h = x + size[0] + gap, max(row_h, size[1])
    return np.concatenate(placed), y + row_h


def main():
    p1b = len(sys.argv) > 1 and sys.argv[1] == 'p1b'
    layout, plates = (LAYOUT_P1B, HERE / 'plates_p1b') if p1b else (LAYOUT, HERE / 'plates')
    global SOURCE_FOLDER
    SOURCE_FOLDER = HERE / ('exports_p1b' if p1b else 'exports')
    plates.mkdir(exist_ok=True)
    manifest = {'configuration': 'P1B' if p1b else 'P1A', 'bed_used_mm': BED_USED, 'plates': []}
    expected = {name for contents in layout.values() for names,qty in contents for name in (names if isinstance(names,tuple) else (names,))}
    export_manifest=json.loads((SOURCE_FOLDER / 'manifest.json').read_text())
    for filename,digest in export_manifest['sources'].items():
        if hashlib.sha256((HERE / filename).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Generator/input changed; regenerate this design: '+filename)
    for part in export_manifest['parts']:
        path=SOURCE_FOLDER / (part['name']+'.stl')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=part['sha256']:
            raise RuntimeError('Export changed after generation: '+str(path))
    present={p.stem for p in SOURCE_FOLDER.glob('*.stl')}
    if present!={p['name'] for p in export_manifest['parts']}:
        raise RuntimeError('Export file set differs from generated manifest')
    manifest['generator_sources']=export_manifest['sources']
    manifest['sources'] = {name: {'path':str(source(name).relative_to(HERE)), 'sha256':hashlib.sha256(source(name).read_bytes()).hexdigest(), 'rotation':LAY_FLAT.get(name,np.eye(3)).tolist()} for name in sorted(expected)}
    for plate, contents in layout.items():
        items = []
        for name, qty in contents:
            triangles, size = normalised(name)
            if plate in DIAGONAL:
                step = DIAGONAL[plate] / math.sqrt(2)
                stack = np.concatenate([triangles + np.array([k * step, k * step, 0]) for k in range(qty)])
                low, high = stack.reshape(-1, 3).min(0), stack.reshape(-1, 3).max(0)
                items.append((stack - np.array([(low[0] + high[0]) / 2, (low[1] + high[1]) / 2, 0]), high - low))
            else:
                items += [(triangles, size)] * qty
        merged, depth = shelf_pack(items, GAPS.get(plate, 4.0))
        validate_mesh(merged, plate)
        if np.min(merged[:,:,2]) < -1e-5 or np.max(merged[:,:,2]) > 140:
            raise ValueError('Plate outside Z limits')
        write(plates / f'{plate}.stl', merged)
        extent = merged.reshape(-1, 3).max(0) - merged.reshape(-1, 3).min(0)
        part_count=sum(q * (len(names) if isinstance(names,tuple) else 1) for names,q in contents)
        manifest['plates'].append({'name':plate, 'part_count':part_count, 'contents':contents, 'extent_mm':extent.tolist(), 'sha256':hashlib.sha256((plates / f'{plate}.stl').read_bytes()).hexdigest()})
        print(f'{plate}: {part_count} parts, footprint {extent[0]:.1f} x {extent[1]:.1f} mm, height {extent[2]:.1f} mm')

    stale = sorted(p.name for p in plates.glob('*.stl') if p.stem not in layout)
    if stale: raise RuntimeError('Stale print plates require explicit review: ' + str(stale))
    (plates / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    main()
