"""Build centered P1B production plates from checked native Fusion exports.

Keep part dimensions/orientations; split crowded batches instead of scaling.
Run with cad/kit/.venv/bin/python. Physical acceptance remains a separate gate.
"""
import collections
import hashlib
import itertools
import json
import math
import shutil
from pathlib import Path

import numpy as np
import audit_t4
import test_pieces

CAD = audit_t4.CAD
OUT = CAD / 'print_ready_p1b'
USED = 128.
GAP = 12.


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack(items):
    """Stable shelf packing returning multiple plates with their placements."""
    batches, current = [], []
    x = y = row_h = 0.
    for name, triangles, size in sorted(items, key=lambda row: -row[2][1]):
        assert max(size[:2]) <= USED
        if x + size[0] > USED:
            x, y, row_h = 0., y + row_h + GAP, 0.
        if y + size[1] > USED:
            batches.append(current)
            current, x, y, row_h = [], 0., 0., 0.
        delta = np.array([x + size[0]/2, y + size[1]/2, 0.])
        current.append((name, triangles + delta))
        x += size[0] + GAP
        row_h = max(row_h, size[1])
    if current:
        batches.append(current)
    return batches


def build():
    tools = audit_t4.load_plate_module()
    exports = json.loads((CAD / 'exports_p1b/manifest.json').read_text())
    for name, digest in exports['sources'].items():
        assert sha(CAD / name) == digest, 'Stale CAD export: ' + name
    for row in exports['parts']:
        assert sha(CAD / 'exports_p1b' / (row['name'] + '.stl')) == row['sha256']
    OUT.mkdir(exist_ok=True)
    for folder in ('plates', 'parts', 'checks', 'profiles'):
        (OUT / folder).mkdir(exist_ok=True)
    fixtures = test_pieces.build(OUT / 'fixtures')
    assert fixtures['pin_cut_length_mm'] == 11.
    manifest = {'design': 'P1B two-ring gimbal', 'date': '2026-10-09',
                'scope': 'Digital print preparation; actual hardware fit, strength and flight pending',
                'bed_mm': [150, 150, 150], 'packing_area_mm': USED, 'gap_mm': GAP,
                'brim_mm': 5, 'generator_sources': exports['sources'],
                'fits': json.loads((CAD / 'fit_results.json').read_text()), 'parts': [], 'plates': []}
    source_rows = {r['name']: r for r in exports['parts']}
    for row in exports['parts']:
        if row['name'] == 'gimbal_fit_coupon':
            continue
        triangles, size = tools.normalised(row['name'])
        body = audit_t4.solid(triangles)
        assert len(body.decompose()) == 1 and row['native_lumps'] == 1
        assert abs(body.volume() / row['native_volume_mm3'] - 1) < .001
        target = OUT / 'parts' / (row['name'] + '.stl')
        tools.write(target, triangles)
        manifest['parts'].append({**row, 'file': str(target.relative_to(OUT)),
                                  'print_sha256': sha(target), 'size_mm': size.tolist(),
                                  'rotation': tools.LAY_FLAT.get(row['name'], np.eye(3)).tolist(),
                                  'mesh_volume_mm3': body.volume()})

    def store(name, placed, purpose='production'):
        joined = np.concatenate([triangles for _, triangles in placed])
        low, high = joined.reshape(-1, 3).min(0), joined.reshape(-1, 3).max(0)
        shift = -np.array([(low[0]+high[0])/2, (low[1]+high[1])/2, low[2]])
        joined += shift
        path = OUT / 'plates' / (name + '.stl')
        tools.write(path, joined)
        written = tools.read(path)
        body = audit_t4.solid(written)
        pieces = body.decompose()
        assert len(pieces) == len(placed), (name, len(pieces), len(placed))
        for part in pieces:
            assert abs(part.bounding_box()[2]) < 1e-5
        for a, b in itertools.combinations(pieces, 2):
            assert (a ^ b).volume() < 1e-5
        contact = test_pieces.box((-75, -75, 0), (75, 75, .01))
        areas = [(part ^ contact).volume()/.01 for part in pieces]
        assert min(areas) > 1.
        bounds = np.array(body.bounding_box())
        size = bounds[3:] - bounds[:3]
        assert max(size[:2]) <= USED + .001
        assert size[2] < 150
        positions = []
        for part_name, triangles in placed:
            lo, hi = (triangles + shift).reshape(-1, 3).min(0), (triangles + shift).reshape(-1, 3).max(0)
            positions.append({'part': part_name, 'min_mm': lo.tolist(), 'max_mm': hi.tolist()})
        row = {'name': name, 'purpose': purpose, 'file': str(path.relative_to(OUT)),
               'sha256': sha(path), 'part_count': len(placed),
               'contents': dict(collections.Counter(n for n, _ in placed)),
               'size_mm': size.tolist(), 'base_contact_min_mm2': min(areas),
               'centered_at_xy0': True, 'parts_flat_at_z0': True,
               'no_intersections': True, 'placements': positions,
               'profile': 'Voxel PETG FINAL ' + name}
        manifest['plates'].append(row)
        print(name, row['part_count'], [round(v, 2) for v in size], flush=True)

    batches = [
        ('H1', [('hub_3way', 36)]),
        ('H2', [('hub_3way', 10), ('hub_3way_mount_A', 4), ('hub_4way', 10)]),
        ('G2', [('outer_junction_Z_bearing', 2), ('outer_junction_X_bearing', 2),
                ('inner_junction_X_pin', 2), ('inner_junction_Y_bearing', 2),
                ('arm_pivot_block', 2), ('hub_pole_5way_pivot', 2)]),
        ('T4', [('carrier_plate', 1), ('nut_shield_plate', 1), ('support_arm_p1b', 2)]),
    ]
    for label, contents in batches:
        items = []
        for name, quantity in contents:
            triangles, size = tools.normalised(name)
            items.extend([(name, triangles, size)] * quantity)
        packed = pack(items)
        for number, plate in enumerate(packed, 1):
            store(label + ('-%02d' % number if len(packed) > 1 else ''), plate)
    for label, name in (('G1a', 'inner_ring_quarter'), ('G1b', 'outer_ring_quarter')):
        triangles, _ = tools.normalised(name)
        step = 13 / math.sqrt(2)
        store(label, [(name, triangles + np.array([k*step, k*step, 0])) for k in range(4)])
    # Keep the fine-mesh T3 candidate and its established layout exactly.
    native = json.loads((CAD/'print_now/T3_native_hub_manifest.json').read_text())
    fine = tools.read(CAD / 'print_now' / native['file'])
    lo, hi = fine.reshape(-1,3).min(0), fine.reshape(-1,3).max(0)
    fine -= np.array([(lo[0]+hi[0])/2, (lo[1]+hi[1])/2, lo[2]])
    size = hi-lo
    store('T3', [('hub_3way', fine + np.array([(col-2)*(size[0]+GAP), (row-.5)*(size[1]+GAP), 0]))
                 for row in range(2) for col in range(5)], 'section test; ten extra hubs, reusable')
    for row in fixtures['parts']:
        triangles = tools.read(OUT / 'fixtures' / (row['name']+'.stl'))
        lo, hi = triangles.reshape(-1,3).min(0), triangles.reshape(-1,3).max(0)
        triangles -= np.array([(lo[0]+hi[0])/2, (lo[1]+hi[1])/2, lo[2]])
        for number, placed in enumerate(pack([(row['name'], triangles, hi-lo)] * row['qty']), 1):
            store('KIT-' + row['name'] + ('-%02d' % number if number > 1 else ''), placed, 'fixture; not aircraft')
    totals = collections.Counter()
    for row in manifest['plates']:
        if row['purpose'] == 'production':
            totals.update(row['contents'])
    expected = {row['name']: row['qty'] for row in exports['parts'] if row['name'] != 'gimbal_fit_coupon'}
    assert dict(totals) == expected, (totals, expected)
    assert sum(totals.values()) == 84
    manifest['production_quantities'] = dict(totals)
    manifest['production_part_count'] = sum(totals.values())
    current = {row['name']+'.stl' for row in manifest['plates']}
    assert {p.name for p in (OUT/'plates').glob('*.stl')} == current, 'Stale plates require review'
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    build()
