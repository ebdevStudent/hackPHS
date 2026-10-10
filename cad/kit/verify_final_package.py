"""Verify source identity, every plate placement, inventory and saved settings.

Run with software/.venv/bin/python (Qt + numpy). Does not contact a printer.
"""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from PySide6.QtCore import QSettings

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT/'cad/apex2-cage'
OUT = CAD/'print_ready_p1b'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('plate_tools', CAD/'make_plates.py')
    tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools)
    manifest = json.loads((OUT/'manifest.json').read_text())
    slices = {r['plate']: r for r in json.loads((OUT/'slice-verification.json').read_text())['plates']}
    profiles = {r['name']: r for r in json.loads((OUT/'profiles/manifest.json').read_text())['profiles']}
    for name, expected in manifest['generator_sources'].items():
        assert digest(CAD/name) == expected
    totals = collections.Counter()
    verified = []
    for plate in manifest['plates']:
        path = OUT/plate['file']
        assert digest(path) == plate['sha256'] == slices[plate['name']]['stl_sha256']
        assert slices[plate['name']]['first_layer_parts'] == plate['part_count']
        assert all(slices[plate['name']]['checks'].values())
        assert slices[plate['name']]['min_path_edge_clearance_mm'] > 7
        actual = tools.read(path)
        index = 0
        for placement in plate['placements']:
            name = placement['part']
            if plate['name'] == 'T3':
                source = CAD/'print_now/T3_hub_socket_2_native.stl'
            elif plate['purpose'] == 'fixture; not aircraft':
                source = OUT/'fixtures'/(name+'.stl')
            else:
                source = OUT/'parts'/(name+'.stl')
            triangles = tools.read(source)
            delta = np.array(placement['min_mm']) - triangles.reshape(-1,3).min(0)
            moved = triangles + delta
            chunk = actual[index:index+len(triangles)]
            assert np.allclose(chunk, moved.astype(np.float32), atol=1e-5, rtol=0), (plate['name'],name)
            index += len(triangles)
        assert index == len(actual)
        row = profiles[plate['profile']]
        profile = OUT/'profiles'/row['file']
        assert digest(profile) == row['sha256']
        assert digest(Path(row['installed'])) == row['sha256']
        q = QSettings(str(profile), QSettings.IniFormat)
        for key, value in row['qt_readback'].items():
            actual_value = q.value(key, type=type(value))
            assert abs(actual_value-value)<1e-5 if isinstance(value,float) else actual_value==value
        assert q.value('firstMaxSpeed',type=float) == 10.
        assert q.value('brimSpeed',type=float) == 25.
        if plate['purpose'] == 'production':
            totals.update(plate['contents'])
        verified.append(plate['name'])
    assert dict(totals) == manifest['production_quantities']
    assert sum(totals.values()) == 84
    report = {'status': 'PASS', 'scope': 'Digital source, STL placement, bed-path, quantity and native Qt profile checks; no physical certification',
              'plates': verified, 'production_plates': sum(r['purpose']=='production' for r in manifest['plates']),
              'production_parts': 84, 'unique_production_parts': len(totals),
              'min_path_edge_clearance_mm': min(r['min_path_edge_clearance_mm'] for r in slices.values()),
              'all_plate_parts_equal_sources_after_rigid_placement': True,
              'profiles_installed_and_backups_match': True}
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
