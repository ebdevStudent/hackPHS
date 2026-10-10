"""Read-only geometry and fit audit of the existing T4 print plate.

Checks current manifests, exported meshes, packing, modeled M2 screw paths,
arm-to-carrier alignment, strap passages and nominal battery hardware clearance.
Does not establish physical fit or strength and never writes CAD/print files.
Run: cad/kit/.venv/bin/python cad/kit/audit_t4.py
"""
import importlib.util
import json
import hashlib
from pathlib import Path

import manifold3d as mf
import numpy as np

import cage_model
from test_pieces import box, cylinder_x, cylinder_z

CAD = cage_model.CAGE_DIR
NAME = 'p1b_plate_carrier_arms'


def load_plate_module():
    spec = importlib.util.spec_from_file_location('t4_plate_tools', CAD / 'make_plates.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SOURCE_FOLDER = CAD / 'exports_p1b'
    return module


def solid(triangles):
    vertices, indices = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    result = mf.Manifold(mf.Mesh(vertices.astype(np.float32), indices.reshape(-1, 3).astype(np.uint32)))
    assert result.status() == mf.Error.NoError, str(result.status())
    assert result.volume() > 0
    return result


def audit():
    tools = load_plate_module()
    p = cage_model.parameters('p1b')
    exports = json.loads((CAD / 'exports_p1b/manifest.json').read_text())
    packing = json.loads((CAD / 'plates_p1b/manifest.json').read_text())
    entry = next(row for row in packing['plates'] if row['name'] == NAME)
    for name, digest in exports['sources'].items():
        assert hashlib.sha256((CAD / name).read_bytes()).hexdigest() == digest, 'Stale export source: ' + name
    assert packing['generator_sources'] == exports['sources']
    parts, part_rows = {}, []
    names = ('carrier_plate', 'nut_shield_plate', 'support_arm_p1b')
    for name in names:
        row = next(row for row in exports['parts'] if row['name'] == name)
        path = CAD / 'exports_p1b' / (name + '.stl')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
        triangles = tools.read(path)  # includes watertightness and winding checks
        part = solid(triangles)
        assert len(part.decompose()) == 1
        assert abs(part.volume() - row['native_volume_mm3']) < row['native_volume_mm3'] * 0.001
        parts[name] = part
        bounds = part.bounding_box()
        part_rows.append({'name': name, 'native_volume_mm3': row['native_volume_mm3'],
                          'mesh_volume_mm3': round(part.volume(), 5),
                          'size_mm': [round(bounds[i+3] - bounds[i], 4) for i in range(3)],
                          'watertight_consistently_wound': True, 'connected_bodies': 1})
    inspection_path = Path(__file__).resolve().parent/'reports/t4-fusion-inspection-2026-10-09.json'
    live = json.loads(inspection_path.read_text())
    assert live['document'] == 'Apex2 Ball Cage P1B Gimbal'
    for row in live['bodies']:
        if row['name'] in names:
            source_row = next(item for item in part_rows if item['name'] == row['name'])
            assert row['solid']
            assert abs(row['volume_mm3'] - source_row['native_volume_mm3']) < 1e-6
    for name, row in live['parameters'].items():
        assert abs(row['value_mm'] - p[name]) < 1e-6
    plate_path = CAD / 'plates_p1b' / (NAME + '.stl')
    assert hashlib.sha256(plate_path.read_bytes()).hexdigest() == entry['sha256']
    actual = tools.read(plate_path)
    items = []
    for name, quantity in tools.LAYOUT_P1B[NAME]:
        triangles, size = tools.normalised(name)
        items.extend([(triangles, size)] * quantity)
    expected, _ = tools.shelf_pack(items)
    assert np.allclose(actual, expected.astype(np.float32), atol=1e-5, rtol=0), 'Plate differs from expected exports'
    bodies = solid(actual).decompose()
    assert len(bodies) == 4
    assert all(abs(part.bounding_box()[2]) < 1e-5 for part in bodies)
    footprint = actual.reshape(-1, 3)
    low, high = footprint.min(axis=0), footprint.max(axis=0)
    size = high - low
    brim = 5
    centered_margin = ((150 - size[:2]) / 2 - brim).tolist()
    assert min(centered_margin) > 0
    carrier, arm, shield = (parts[name] for name in ('carrier_plate', 'support_arm_p1b', 'nut_shield_plate'))
    top, bottom = -p['frame_t'], -p['frame_t'] - p['carrier_t']
    # Four nominal M2 paths at the center and both extremes of lateral travel.
    paths = []
    q = p['frame_hole_pitch'] / 2
    for dx in (-p['adj_y'], 0, p['adj_y']):
        for sx in (-1, 1):
            for sy in (-1, 1):
                probe = cylinder_z(sx*q + dx, sy*q, bottom-1, top+1, 2)
                overlap = (carrier ^ probe).volume()
                assert overlap < 1e-5, 'Blocked frame screw path'
                paths.append({'frame_shift_x_mm': dx, 'xy_mm': [sx*q+dx, sy*q], 'overlap_mm3': overlap})
    # Native support arm lies along +X; rotate into its installed +Y position.
    arm_alignment = []
    hx = (p['carrier_span']/2 - 16 + 5, p['carrier_span']/2 - 16 + 10)
    for sign in (-1, 1):
        fitted_arm = arm.rotate((0, 0, sign*90))
        for shift in (-p['adj_x'], 0, p['adj_x']):
            placed = fitted_arm.translate((0, shift, 0))
            assert (carrier ^ placed).volume() < 1e-5, 'Arm intersects carrier'
            for y in hx:
                probe = cylinder_z(0, sign*y+shift, bottom-1, top+p['support_h']+1, 2)
                overlap = ((carrier + placed) ^ probe).volume()
                assert overlap < 1e-5, 'Misaligned arm fastener path'
                arm_alignment.append({'arm_side':sign, 'arm_shift_y_mm':shift,
                                      'xy_mm':[0,sign*y+shift], 'overlap_mm3':overlap})
    # Nominal M2 clearance through the flange's two horizontal holes.
    end = arm.bounding_box()[3]
    flange_checks = []
    for z in (top+5, top+p['flange_h']-4):
        probe = cylinder_x(end-p['flange_t']-1, end+1, 0, z, 2)
        overlap = (arm ^ probe).volume()
        assert overlap < 1e-5
        flange_checks.append({'axis_z_mm': z, 'overlap_mm3': overlap})
    # Verify a thin nominal strap can pass the rectangular strap openings.
    reach = q + p['adj_y']
    strap_x = max(max(p['batt450_w'], p['batt1100_w'])/2+p['strap_slot_t']/2+1,
                  reach+p['m2_clear']/2+p['strap_slot_t']/2+1.5)
    for sign in (-1, 1):
        x = sign * strap_x
        probe = box((x-1, -p['strap_w']/2, bottom-1), (x+1, p['strap_w']/2, top+1))
        assert (carrier ^ probe).volume() < 1e-5
    # Conservative round envelopes around nut corners + screw tail, as in CAD.
    nut_od = 4/np.cos(np.radians(30))
    pad_half = q - nut_od/2 - p['adj_y'] - 0.5
    pack_l = max(p['batt450_l'], p['batt1100_l'])
    foam = box((-pad_half,-pack_l/2,bottom-p['battery_gap']), (pad_half,pack_l/2,bottom))
    for dx in (-p['adj_y'], 0, p['adj_y']):
        for sx in (-1,1):
            for sy in (-1,1):
                nut = cylinder_z(sx*q+dx,sy*q,bottom-2.6,bottom,nut_od)
                assert (nut ^ foam).volume() < 1e-5
                assert (nut ^ shield).volume() < 1e-5
    arm_nut_checks = []
    for sign in (-1,1):
        for shift in (-p['adj_x'],0,p['adj_x']):
            for y in hx:
                centre_y = sign*y+shift
                nut = cylinder_z(0,centre_y,bottom-2.6,bottom,nut_od)
                foam_overlap = (nut ^ foam).volume()
                shield_overlap = (nut ^ shield).volume()
                assert shield_overlap < 1e-5
                arm_nut_checks.append({'arm_side':sign,'arm_shift_mm':shift,
                                       'xy_mm':[0,centre_y],
                                       'foam_overlap_mm3':round(foam_overlap,5),
                                       'shield_overlap_mm3':round(shield_overlap,5)})
    # Foam must be cut around the inner arm nuts. Model two reliefs spanning
    # the complete +/-3 mm arm adjustment so foam cannot bind adjustment.
    relief_radius = nut_od/2 + 0.5
    relieved_foam = foam
    for sign in (-1,1):
        relieved_foam -= box((-relief_radius,sign*hx[0]-p['adj_x']-relief_radius,bottom-p['battery_gap']-1),
                             (relief_radius,sign*hx[0]+p['adj_x']+relief_radius,bottom+1))
    for row in arm_nut_checks:
        x,y = row['xy_mm']
        nut = cylinder_z(x,y,bottom-2.6,bottom,nut_od)
        assert (nut ^ relieved_foam).volume() < 1e-5
    return {
        'date': '2026-10-09', 'environment': 'Mac, manifold3d; current exported STL geometry',
        'status': 'Mesh and alignment checks pass; foam relief required around arm nuts; physical fit and strength remain unverified',
        'physical_measurements_present': {key: value for key,value in json.loads((CAD/'measurements.json').read_text())['parameters'].items() if value is not None},
        'source_sha256': exports['sources'], 'parts': part_rows,
        'fusion_inspection': {'file':inspection_path.name, 'document':live['document'],
                              'model_modified':live['modified'],
                              'recorded_parameters_match':True, 'recorded_t4_native_volumes_match':True},
        'plate': {'file':str(plate_path.relative_to(CAD)), 'sha256':entry['sha256'],
                  'matches_exported_parts':True, 'part_count':4, 'all_bases_at_z0':True,
                  'size_mm':size.tolist(), 'as_packed_min_mm':low.tolist(), 'as_packed_max_mm':high.tolist(),
                  'brim_mm':brim, 'center_in_slicer':True, 'centered_brim_edge_margin_xy_mm':centered_margin},
        'interfaces': {'frame_pattern_mm':[p['frame_hole_pitch']]*2, 'm2_clearance_diameter_mm':p['m2_clear'],
                       'frame_screw_path_checks':paths, 'arm_fastener_alignment_checks':arm_alignment,
                       'flange_screw_path_checks':flange_checks, 'strap_passage_checked_mm':[p['strap_w'],2],
                       'frame_lateral_travel_each_way_mm':p['adj_y'], 'arm_travel_each_way_mm':p['adj_x'],
                       'foam_pad_size_mm':[2*pad_half,pack_l,p['battery_gap']],
                       'shield_size_mm':[max(p['batt450_w'],p['batt1100_w'])+1,pack_l+1,p['battery_shield_t']],
                       'nut_tail_protrusion_assumption_mm':2.6, 'nut_to_shield_vertical_gap_mm':p['battery_gap']-2.6,
                       'frame_nut_foam_shield_intersections_mm3':0,
                       'arm_nut_clearance_checks':arm_nut_checks,
                       'foam_relief_required':True,
                       'foam_relief_slot_centres_xy_mm':[[0,hx[0]],[0,-hx[0]]],
                       'foam_relief_slot_size_xy_mm':[2*relief_radius,2*p['adj_x']+2*relief_radius],
                       'arm_nut_relieved_foam_intersections_mm3':0,
                       'frame_carrier_stack_before_washers_nut_mm':p['frame_t']+p['carrier_t'],
                       'arm_carrier_stack_before_washers_nut_mm':p['support_h']+p['carrier_t']},
        'remaining_checks':['Actual accessible frame mounting-hole pattern and bottom thickness',
                            'Printed M2 clearance, arm alignment and retention',
                            'Actual screw/washer/nut stack and underside protrusion',
                            'Actual strap and both battery dimensions, leads and access',
                            'Arm stiffness, cracks, loaded joint slip and final gimbal motion/prop clearance'],
    }


if __name__ == '__main__':
    result = audit()
    path = Path(__file__).resolve().parent/'reports/t4-audit-2026-10-09.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('status','parts','plate','remaining_checks')},indent=2))
