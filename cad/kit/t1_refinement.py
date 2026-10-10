"""Generate an independent T1B refinement coupon; never change main-part fits.

Run: cad/kit/.venv/bin/python cad/kit/t1_refinement.py
Socket construction follows build_p1a.stage4_fit_strip (horizontal bore,
full-width supporting keel, axis height, arm OD and blind depth). The seven
diameters bracket the user's tentative three-dot preference. Screw pilots
retain the original 7 mm block height and 5 mm blind depth.
"""
import argparse
import json
from pathlib import Path

import manifold3d as mf
import numpy as np

import cage_model
from test_pieces import box, cylinder_y, cylinder_z, read_mesh_stl, write_stl

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'cad/apex2-cage/print_now'
SOCKET_DIAMETERS = (1.25, 1.275, 1.30, 1.325, 1.35, 1.375, 1.40)
PILOT_DIAMETERS = (1.80, 1.85, 1.90, 1.95, 2.00, 2.10, 2.20)


def mark(body, x, y, top, count):
    """One to seven dimples, three per row, on the top face."""
    for index in range(count):
        body -= cylinder_z(x - 2.4 + (index % 3) * 2.4,
                           y - (index // 3) * 2.4, top - 0.4, top + 1, 0.9)
    return body


def verify_mesh(path, expected_bodies=2):
    """Check the actual exported STL for closed, consistently oriented shells."""
    triangles = read_mesh_stl(path)
    vertices, indices = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = indices.reshape(-1, 3)
    edges = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    _, counts = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    assert np.all(counts == 2), 'Open or nonmanifold exported STL edge'
    # Each undirected edge must be traversed once in each direction.
    _, directed_counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(directed_counts == 1), 'Inconsistent face winding'
    mesh = mf.Mesh(vertices.astype(np.float32), faces.astype(np.uint32))
    rebuilt = mf.Manifold(mesh)
    assert rebuilt.status() == mf.Error.NoError, str(rebuilt.status())
    assert len(rebuilt.decompose()) == expected_bodies
    assert all(part.volume() > 0 for part in rebuilt.decompose())
    return {'triangles': len(triangles), 'watertight': True,
            'consistently_oriented': True, 'bodies': expected_bodies}


def build(output=OUTPUT):
    p = cage_model.parameters('p1a')
    z = p['hub_core_r']
    top = z + p['hub_arm_od'] / 2
    tip = p['hub_arm_len']
    depth = p['socket_depth']
    width = 8 * len(SOCKET_DIAMETERS) + 2
    sockets = box((0, -10, 0), (width, 0, top))
    socket_info = []
    for k, diameter in enumerate(SOCKET_DIAMETERS):
        x = 5 + k * 8
        sockets += cylinder_y(x, -1, tip, z, p['hub_arm_od'])
        sockets += box((x - p['hub_arm_od'] / 2, -1, 0),
                       (x + p['hub_arm_od'] / 2, tip, z))
        sockets -= cylinder_y(x, tip - depth, tip + 1, z, diameter)
        sockets = mark(sockets, x, -3, top, k + 1)
        socket_info.append({'dots': k + 1, 'diameter_mm': diameter,
                            'axis_mm': [x, z], 'mouth_y_mm': tip,
                            'depth_mm': depth})
    # Separate strip, positioned with a 6 mm gap behind the socket mouths.
    # Seven larger pilot candidates; a nominal 2.20 mm hole is a clearance
    # diagnostic and must not be assumed to retain an M2 thread.
    pilot_y0 = tip + 6
    pilots = box((0, pilot_y0, 0), (width, pilot_y0 + 12, 7))
    pilot_info = []
    for k, diameter in enumerate(PILOT_DIAMETERS):
        x, y = 5 + k * 8, pilot_y0 + 2.5
        pilots -= cylinder_z(x, y, 2, 8, diameter)
        pilots = mark(pilots, x, pilot_y0 + 10, 7, k + 1)
        pilot_info.append({'dots': k + 1, 'diameter_mm': diameter,
                           'centre_mm': [x, y], 'depth_mm': 5})
    for part in (sockets, pilots):
        assert part.status() == mf.Error.NoError
        assert len(part.decompose()) == 1

    # Probe bores and blind floors, independently of export triangulation.
    for item in socket_info:
        x, axis_z = item['axis_mm']
        bore = cylinder_y(x, tip - depth + 0.1, tip + 0.5, axis_z,
                          item['diameter_mm'] * 0.98)
        floor = cylinder_y(x, tip - depth - 0.3, tip - depth - 0.1,
                           axis_z, item['diameter_mm'] * 0.8)
        assert (sockets ^ bore).volume() < 1e-6, 'Obstructed socket'
        assert (sockets ^ floor).volume() > 0.01, 'Missing socket floor'
    for item in pilot_info:
        x, y = item['centre_mm']
        bore = cylinder_z(x, y, 2.1, 7.5, item['diameter_mm'] * 0.98)
        floor = cylinder_z(x, y, 1.7, 1.9, item['diameter_mm'] * 0.8)
        assert (pilots ^ bore).volume() < 1e-6, 'Obstructed pilot'
        assert (pilots ^ floor).volume() > 0.01, 'Missing pilot floor'
    combined = sockets + pilots
    bounds = combined.bounding_box()
    size = [round(bounds[i + 3] - bounds[i], 3) for i in range(3)]
    assert abs(bounds[2]) < 1e-6 and abs(bounds[5] - 7) < 1e-6
    assert all(length + 10 < 140 for length in size[:2]), 'No 5 mm brim clearance'
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'T1B_socket_and_screw_refinement.stl'
    sha = write_stl(combined, path)
    checks = verify_mesh(path)
    # Confirm the bore rims' dimensions in the float32 STL, independently
    # of the analytical Boolean probes above.
    vertices = read_mesh_stl(path).reshape(-1, 3)
    for item in socket_info:
        x, axis_z = item['axis_mm']
        radii = np.hypot(vertices[:, 0] - x, vertices[:, 2] - axis_z)
        rim = radii[(np.abs(vertices[:, 1] - tip) < 1e-5) & (radii < 1)]
        assert len(rim) >= 64
        assert np.max(np.abs(2 * rim - item['diameter_mm'])) < 1e-4
    for item in pilot_info:
        x, y = item['centre_mm']
        radii = np.hypot(vertices[:, 0] - x, vertices[:, 1] - y)
        rim = radii[(np.abs(vertices[:, 2] - 7) < 1e-5) & (radii < 1.3)]
        assert len(rim) >= 64
        assert np.max(np.abs(2 * rim - item['diameter_mm'])) < 1e-4
    manifest = {
        'source': 'cad/kit/t1_refinement.py',
        'status': 'Untested refinement coupon; main cage parameters unchanged',
        'basis': 'T1 snug socket tentatively identified as three dots; M2 screws would not start when turned',
        'hardware': {'rod_diameter_mm': p['rod_dia'], 'rod_status': 'baseline, not measured',
                     'screw': 'M2 x 4 mm socket head, hand-driven'},
        'socket_parameters': {key: p[key] for key in ('hub_core_r', 'hub_arm_od', 'hub_arm_len', 'socket_depth')},
        'socket_holes': socket_info, 'screw_pilots': pilot_info,
        'size_mm': size, 'volume_mm3': round(combined.volume(), 3),
        'solid_petg_mass_g_estimate': round(combined.volume() / 1000 * p['petg_density'], 2),
        'file': path.name, 'sha256': sha,
        'checks': {**checks, 'all_bores_open': True, 'blind_floors_present': True,
                   'exported_bore_diameters_match': True,
                   'both_strips_flat_at_z0': True, 'fits_140mm_bed_with_5mm_brim': True},
    }
    (output / 'T1B_refinement_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    checksum_file = output / 'SHA256SUMS'
    lines = checksum_file.read_text().splitlines() if checksum_file.exists() else []
    lines = [line for line in lines if not line.endswith('  ' + path.name)]
    checksum_file.write_text('\n'.join(lines + [sha + '  ' + path.name]) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({key: result[key] for key in ('file', 'size_mm', 'solid_petg_mass_g_estimate', 'checks')}, indent=2))
