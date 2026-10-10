"""Arrange exported STLs into Monoprice Voxel plates (150 x 150 mm bed, 140 mm used).

Run with numpy:  python make_plates.py        (P1A: exports/ -> plates/)
                 python make_plates.py p1b    (P1B gimbal: exports_p1b/ + shared P1A parts -> plates_p1b/)
Each part is re-oriented for printing, centred on its footprint, dropped to Z = 0 and row-packed. Nested
entries (ring quarters) keep their shared arc centre so an inner quarter sits inside an outer one.
Plates are a starting layout: check brim/skirt overlap in the slicer.
"""
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
    'plate_4_carrier_supports': [('carrier_plate', 1), ('support_arm', 2), ('x_bracket', 2)],
}
LAYOUT_P1B = {
    # Print this plate 4 times: one outer + one inner quarter, nested on their common arc centre.
    'p1b_plate_ring_quarters_PRINT_4X': [(('outer_ring_quarter', 'inner_ring_quarter'), 1)],
    'p1b_plate_0_gimbal_fit_coupon_PRINT_FIRST': [('gimbal_fit_coupon', 1)],
    'p1b_plate_junctions_pivots': [('outer_junction_Z_bearing', 2), ('outer_junction_X_bearing', 2), ('inner_junction_X_pin', 2),
                                   ('inner_junction_Y_bearing', 2), ('arm_pivot_block', 2), ('hub_pole_5way_pivot', 2)],
    'p1b_plate_carrier_arms': [('carrier_plate', 1), ('support_arm_p1b', 2)],
}
LAY_FLAT = {'x_bracket': np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float),  # X thickness -> Z
            'arm_pivot_block': X_UP,
            'outer_junction_Z_bearing': FLIP_X, 'outer_junction_X_bearing': FLIP_X,
            'inner_junction_X_pin': FLIP_X, 'inner_junction_Y_bearing': FLIP_X}
SOURCES = [HERE / 'exports_p1b', HERE / 'exports']


def read(path):
    data = path.read_bytes()
    count = struct.unpack('<I', data[80:84])[0]
    if 84 + count * 50 == len(data):
        return np.frombuffer(data[84:], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))['v'].reshape(-1, 3, 3).astype(float)
    lines = [l.split()[1:] for l in data.decode().splitlines() if l.strip().startswith('vertex')]
    return np.array(lines, float).reshape(-1, 3, 3)


def write(path, triangles):
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    record = np.zeros(len(triangles), dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
    record['n'], record['v'] = normals, triangles.reshape(-1, 9)
    path.write_bytes(b'Ball Drone P1A plate'.ljust(80, b' ') + struct.pack('<I', len(triangles)) + record.tobytes())


def source(name):
    for folder in SOURCES:
        if (folder / f'{name}.stl').exists():
            return folder / f'{name}.stl'
    raise FileNotFoundError(name)


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
    if not p1b:
        SOURCES.reverse()          # P1A plates read exports/ first
    plates.mkdir(exist_ok=True)
    for plate, contents in layout.items():
        items = []
        for name, qty in contents:
            triangles, size = normalised(name)
            items += [(triangles, size)] * qty
        merged, depth = shelf_pack(items)
        write(plates / f'{plate}.stl', merged)
        extent = merged.reshape(-1, 3).max(0) - merged.reshape(-1, 3).min(0)
        print(f'{plate}: {sum(q for _, q in contents)} parts, footprint {extent[0]:.1f} x {extent[1]:.1f} mm, height {extent[2]:.1f} mm')


if __name__ == '__main__':
    main()
