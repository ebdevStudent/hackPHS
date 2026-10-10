"""CAD kit: parameter resolution, measurement checks, test-piece geometry, opening and mass analyses."""
import csv
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
import analyse_bend, apply_measurements, cage_model, opening_probe, p1b_mass_options, test_pieces  # noqa: E402
from measurement_schema import MASSES, PARAMETERS  # noqa: E402

MAIN_CAD = ['build_p1a.py', 'build_p1b.py', 'validation.py', 'make_plates.py', 'vendor_specs.json', 'measurements.json']


@pytest.fixture(scope='module', autouse=True)
def main_cad_untouched():
    """Every kit tool must leave the main CAD files byte-identical."""
    before = {name: hashlib.sha256((cage_model.CAGE_DIR / name).read_bytes()).hexdigest() for name in MAIN_CAD}
    yield
    after = {name: hashlib.sha256((cage_model.CAGE_DIR / name).read_bytes()).hexdigest() for name in MAIN_CAD}
    assert before == after


# ---------------------------------------------------------------- parameter resolution
def test_resolved_parameters_reproduce_the_recorded_cage():
    p = cage_model.parameters()
    # 2026-10-08: the generator now drives the cage from a 44.50 mm edge-rod cut length.
    assert round(p['rod_cut_len'], 2) == 44.50 and round(p['cage_edge'], 2) == 49.00
    assert round(p['pole_rod_cut_len'], 2) == 37.83 and 245 <= p['cage_outer_dia'] <= 250
    assert p['prop_z'] == 8.9 and p['stack_w'] == 33 and math.isclose(math.degrees(p['cam_hfov']), 160)
    points, edges, poles = cage_model.cage_geometry(p)
    assert (len(points), len(edges), len(poles)) == (62, 90, 10)


def test_p1b_overrides_and_swept_radius_match_the_generator_report():
    p = cage_model.parameters('p1b')
    assert (p['adj_x'], p['adj_y'], p['cg_slot'], p['carrier_core_w']) == (3, 2, 5, 48)
    swept = cage_model.load_generator('build_p1b.py')['aircraft_radius'](p, opening_probe.P1B_DZ)
    assert round(swept, 2) == 79.61


def test_measured_values_override_vendor_values():
    assert cage_model.parameters('p1a', {'prop_dia': '50 mm'})['prop_dia'] == 50
    assert cage_model.parameters('p1a', {'cam_tilt': '15 deg'})['cam_tilt'] == pytest.approx(math.radians(15))


@pytest.mark.parametrize('expression,expected', [('2 mm', 2), ('49 mm / (2 * sin(36 deg))', 49 / (2 * math.sin(math.radians(36)))),
                                                 ('3 ^ 2', 9), ('sqrt(16)', 4)])
def test_expression_evaluation(expression, expected):
    assert cage_model.evaluate(expression, {}) == pytest.approx(expected)


def test_loading_the_generator_does_not_leave_the_stub_installed():
    cage_model.load_generator('build_p1a.py')
    assert 'adsk' not in sys.modules or not isinstance(sys.modules['adsk'].core, cage_model._Anything)


# ---------------------------------------------------------------- measurement form
def test_schema_names_exist_in_the_generators():
    p1a = {n for n, *_ in cage_model.load_generator('build_p1a.py')['PARAMS']}
    p1b = {n for n, *_ in cage_model.load_generator('build_p1b.py')['P1B_PARAMS']}
    for name, (_, _, _, design, _) in PARAMETERS.items():
        assert name in (p1b if design == 'p1b' else p1a), name
    template = json.loads((cage_model.CAGE_DIR / 'measurements.json').read_text())
    assert set(template['parameters']) <= set(PARAMETERS) and set(template['masses_g']) <= set(MASSES)


def rows(**values):
    return [{'name': k, 'value': str(v[0]), 'unit': v[1]} for k, v in values.items()]


def test_valid_form_is_accepted():
    params, masses, errors, warnings = apply_measurements.check(rows(prop_dia=(51.2, 'mm'), cam_tilt=(18, 'deg'), pack_450_g=(27.1, 'g')))
    assert not errors and params == {'prop_dia': '51.2 mm', 'cam_tilt': '18 deg'} and masses == {'pack_450_g': 27.1}


@pytest.mark.parametrize('row,message', [
    (('prop_diam', 51, 'mm'), 'unknown name'), (('prop_dia', 51, 'in'), 'unit must be'), (('prop_dia', 'fifty', 'mm'), 'not a number'),
    (('prop_dia', 508, 'mm'), 'outside'), (('pack_450_g', 2.6, 'g'), 'outside'), (('prop_dia', 'nan', 'mm'), 'not a number')])
def test_bad_rows_are_errors(row, message):
    _, _, errors, _ = apply_measurements.check([{'name': row[0], 'value': str(row[1]), 'unit': row[2]}])
    assert errors and message in errors[0]


def test_duplicates_overlap_and_rod_gate_are_reported():
    _, _, errors, _ = apply_measurements.check(rows(prop_dia=(50, 'mm')) * 2)
    assert 'twice' in errors[0]
    _, _, errors, _ = apply_measurements.check(rows(prop_dia=(55.9, 'mm'), motor_diag=(78, 'mm'))[:1] + rows(motor_diag=(86, 'mm')))
    assert not any('overlap' in e for e in errors)
    _, _, errors, _ = apply_measurements.check(rows(prop_dia=(55, 'mm'), motor_diag=(85, 'mm')))
    assert not errors
    _, _, _, warnings = apply_measurements.check(rows(rod_dia=(1.05, 'mm')))
    assert any('validation.py' in w for w in warnings)


def test_vendor_deviation_and_thrust_warnings():
    _, _, _, warnings = apply_measurements.check(rows(motor_diag=(85, 'mm'), thrust_total_g=(140, 'g'), bare_aircraft_g=(60, 'g'), pack_1100_g=(50, 'g')))
    assert any('differs from the vendor' in w for w in warnings) and any('below the 2:1' in w for w in warnings)


def test_write_keeps_a_backup_and_never_runs_on_errors(tmp_path):
    target = tmp_path / 'measurements.json'
    target.write_text(json.dumps({'parameters': {'prop_dia': None}, 'masses_g': {}}))
    good, bad = tmp_path / 'good.csv', tmp_path / 'bad.csv'
    for path, value in ((good, '50.5'), (bad, '5000')):
        with path.open('w', newline='') as handle:
            writer = csv.writer(handle); writer.writerow(['name', 'value', 'unit', 'notes']); writer.writerow(['prop_dia', value, 'mm', ''])
    assert apply_measurements.main([str(bad), '--write', '--target', str(target)]) == 1
    assert json.loads(target.read_text())['parameters']['prop_dia'] is None
    assert apply_measurements.main([str(good), '--target', str(target)]) == 0
    assert json.loads(target.read_text())['parameters']['prop_dia'] is None          # check-only
    assert apply_measurements.main([str(good), '--write', '--target', str(target)]) == 0
    assert json.loads(target.read_text())['parameters']['prop_dia'] == '50.5 mm'
    assert len(list(tmp_path.glob('measurements.backup-*.json'))) == 1


def test_blank_form_lists_every_field(tmp_path):
    path = tmp_path / 'form.csv'
    apply_measurements.main(['--blank', str(path)])
    with path.open(newline='') as handle:
        names = [r['name'] for r in csv.DictReader(handle)]
    assert names == list(PARAMETERS) + list(MASSES)


# ---------------------------------------------------------------- test pieces
def read_stl(path):
    data = path.read_bytes()
    count = struct.unpack('<I', data[80:84])[0]
    assert len(data) == 84 + 50 * count
    return np.frombuffer(data[84:], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))['v'].reshape(-1, 3, 3)


@pytest.fixture(scope='module')
def pieces(tmp_path_factory):
    out = tmp_path_factory.mktemp('pieces')
    return out, test_pieces.build(out)


def test_test_pieces_are_single_closed_printable_bodies(pieces):
    out, manifest = pieces
    for part in manifest['parts']:
        assert part['bodies'] == 1 and part['volume_mm3'] > 0, part
        assert max(part['size_mm'][:2]) <= 140 and part['size_mm'][2] <= 140   # Voxel plate
        triangles = read_stl(out / f"{part['name']}.stl")
        edges = {}
        for tri in triangles.round(5):
            for a, b in zip(map(tuple, tri), map(tuple, np.roll(tri, -1, axis=0))):
                key = tuple(sorted((a, b))); edges[key] = edges.get(key, 0) + 1
        assert set(edges.values()) == {2}, part['name']                     # watertight
        assert hashlib.sha256((out / f"{part['name']}.stl").read_bytes()).hexdigest() == part['sha256']


def test_jig_reproduces_the_cage_span_and_socket(pieces):
    _, manifest = pieces
    p = cage_model.parameters()
    assert manifest['exposed_rod_span_mm'] == pytest.approx(p['cage_edge'] - 2 * p['hub_arm_len'], abs=1e-3) == pytest.approx(35.0, abs=1e-3)
    assert manifest['jig']['tip_gap_pushed_inward_mm'] == pytest.approx(manifest['exposed_rod_span_mm'], abs=1e-3)
    assert manifest['rod_cut_for_test_mm'] == pytest.approx(manifest['exposed_rod_span_mm'] + 2 * (p['socket_depth'] - p['rod_end_gap']), abs=1e-3)
    assert manifest['pin_cut_length_mm'] == 11.0  # 6 mm press + 1 mm gap + 2.5 mm bearing + 1.5 mm tail


def test_socket_bore_is_cut_with_the_generator_clearance():
    p = cage_model.parameters()
    block, axis_z, arm_out, _, _ = test_pieces.dimensions(p, cage_model.parameters('p1b'))
    body, tip = test_pieces.bend_test_block(p, block, axis_z, arm_out)
    bore = p['rod_dia'] + 2 * p['rod_bore_clear']
    hole = test_pieces.cylinder_x(tip - p['socket_depth'] + .2, tip - .2, block['width'] / 2, axis_z, bore * .95)
    assert (body ^ hole).volume() < 1e-6                              # socket is empty
    wall = test_pieces.cylinder_x(tip - 3, tip - 1, block['width'] / 2, axis_z, p['hub_arm_od'] * .98)
    assert (body ^ wall).volume() > 0.8 * (wall.volume() - test_pieces.cylinder_x(tip - 3, tip - 1, 0, 0, bore).volume())


# ---------------------------------------------------------------- bend analysis
def bend_rows(residual=0.1, slip=0.1, top=200, notes=''):
    data = [('A', 0, 0, 'load'), ('A', 50, .4, 'load'), ('A', 100, .8, 'load'), ('A', top, 1.6, 'load'), ('A', top, 1.7, 'hold'), ('A', 0, residual, 'unload')]
    return [{'specimen': s, 'load_g': str(l), 'deflection_mm': str(d), 'phase': ph, 'slip_mm': str(slip), 'notes': notes} for s, l, d, ph in data]


def test_bend_pass_and_stiffness():
    result = analyse_bend.analyse(bend_rows())
    assert result['pass'] and result['specimens'][0]['stiffness_g_per_mm'] == pytest.approx(125, rel=.01)


@pytest.mark.parametrize('kwargs,problem', [({'residual': .4}, 'residual'), ({'slip': .8}, 'slip'), ({'top': 150}, 'top load'),
                                            ({'notes': 'cracked at socket'}, 'damage')])
def test_bend_failures(kwargs, problem):
    result = analyse_bend.analyse(bend_rows(**kwargs))
    assert not result['pass'] and problem in ' '.join(result['specimens'][0]['problems'])


def test_bend_unreadable_and_empty_logs_fail():
    bad = bend_rows(); bad[2]['deflection_mm'] = 'x'
    assert not analyse_bend.analyse(bad)['pass'] and not analyse_bend.analyse([])['pass']


# ---------------------------------------------------------------- opening probe
@pytest.fixture(scope='module')
def openings():
    return opening_probe.analyse([10, 60, 70, 80, 90, 150])


def test_opening_inventory_matches_the_cage(openings):
    assert openings['face_count'] == 40
    o = openings['openings']
    assert (o['hexagon']['count'], o['pentagon']['count'], o['pole_triangle']['count']) == (20, 10, 10)
    p = cage_model.parameters()
    edge = p['cage_edge']
    assert o['hexagon']['clear_circle_diameter_mm'] == pytest.approx(2 * (edge * math.sqrt(3) / 2 - p['rod_dia'] / 2), abs=.05)
    assert o['pentagon']['clear_circle_diameter_mm'] == pytest.approx(2 * (edge / (2 * math.tan(math.pi / 5)) - p['rod_dia'] / 2), abs=.05)


def test_small_objects_pass_and_large_objects_rest_outside_the_props(openings):
    by = {r['diameter_mm']: r for r in openings['probes']}
    assert by[10]['passes_through_openings'] == [3, 5, 6] and by[10]['p1a_reaches_prop']
    assert by[60]['passes_through_openings'] == [5, 6] and by[70]['passes_through_openings'] == [6]
    assert by[90]['passes_through_openings'] == [] and not by[90]['p1a_reaches_prop'] and not by[90]['p1b_can_reach_prop']
    assert by[90]['p1a_min_prop_clearance_mm'] < by[150]['p1a_min_prop_clearance_mm']
    assert by[150]['max_intrusion_below_rod_plane_mm'] < by[90]['max_intrusion_below_rod_plane_mm']


def test_resting_height_matches_the_closed_form_for_a_regular_hexagon():
    points = np.array(cage_model.cage_geometry(cage_model.parameters())[0])
    edges = cage_model.cage_geometry(cage_model.parameters())[1]
    face = next(f for f in opening_probe.faces(points, edges) if len(f['vertices']) == 6)
    r, rod_r = 50.0, .5
    centres, passes = opening_probe.resting_centres(face, points, r, rod_r)
    inradius = cage_model.parameters()['cage_edge'] * math.sqrt(3) / 2
    expected_intrusion = r - math.sqrt((r + rod_r) ** 2 - inradius ** 2)
    deepest = max(np.dot(face['centre'], face['normal']) - (c @ face['normal'] - r) for c in centres)
    assert not passes.any() and deepest == pytest.approx(expected_intrusion, abs=.05)


# ---------------------------------------------------------------- mass options
def test_mass_report_is_consistent():
    result = p1b_mass_options.report()
    assert result['added_structure_g'] == pytest.approx(result['printed_g'] + result['rods_g'] + result['hardware_g'], abs=.02)
    by = {r['pack']: r for r in result['configurations']}
    assert by['1100']['accounted_g'] - by['450']['accounted_g'] == pytest.approx(22, abs=.01)
    assert result['options'][0]['saving_g'] == 22 and all(o['saving_g'] > 0 for o in result['options'])
    assert result['rods_g'] == pytest.approx(5.34, abs=.02)


# ---------------------------------------------------------------- solid clash check and bend simulation
import bend_simulation  # noqa: E402
import clash_check  # noqa: E402


@pytest.fixture(scope='module')
def clash():
    return clash_check.analyse([20, 90])


def test_solid_cage_matches_the_generator_and_never_touches_the_props(clash):
    cage = clash['cage']
    assert (cage['hubs'], cage['rods']) == (62, 100)
    assert 245 <= max(cage['span_mm']) <= 250
    assert clash['self_clash']['cage_x_p1a_props_mm3'] == 0 and clash['self_clash']['cage_x_p1b_swept_mm3'] == 0
    assert clash['self_clash']['cage_to_p1a_props_gap_mm'] > 30


def test_solid_balls_agree_with_the_rod_model(clash, openings):
    by = {r['diameter_mm']: r for r in clash['probes']}
    assert by[20]['passes_through'] and by[20]['p1a_prop_contact']
    assert by[90]['passes_through'] == [] and not by[90]['p1a_prop_contact'] and by[90]['p1b_ring_contact']
    rod_model = {r['diameter_mm']: r for r in openings['probes']}[90]['p1a_min_prop_clearance_mm']
    assert rod_model - .05 <= by[90]['p1a_min_gap_mm'] <= rod_model + 1.0     # rod model is conservative
    assert by[90]['max_ball_cage_overlap_mm3'] < 1e-3                         # resting = touching, not buried


def test_descent_stops_at_first_contact():
    import manifold3d as mf
    wall = mf.Manifold.cube((40, 40, 2)).translate((-20, -20, -2))              # top face at z = 0
    h, through = clash_check.descend(np.zeros(3), np.array([0, 0, 1.0]), 5.0, wall, -20)
    assert not through and h == pytest.approx(5.0, abs=.01)
    h, through = clash_check.descend(np.array([100.0, 0, 0]), np.array([0, 0, 1.0]), 5.0, wall, -20)
    assert through


@pytest.fixture(scope='module')
def bend():
    return bend_simulation.run()


def test_bend_jig_assembly_fits(bend):
    fit = bend['assembly']
    assert fit['pass'] and fit['rod_length_mm'] == pytest.approx(cage_model.parameters()['rod_cut_len'], abs=1e-3)
    assert fit['room_to_deflect_mm'] > max(r['pinned_mm'][1] for r in bend['predictions']['loads']) + 3


def test_bend_assembly_detects_a_misplaced_rod():
    values = cage_model.parameters()
    block, axis_z, arm_out, span, _ = test_pieces.dimensions(values, cage_model.parameters('p1b'))
    body, tip = test_pieces.bend_test_block(values, block, axis_z, arm_out)
    rod = test_pieces.cylinder_x(tip - 4, tip + 5, block['width'] / 2 + .5, axis_z, values['rod_dia'])   # 0.5 mm off axis
    assert (rod ^ body).volume() > 0


def test_bend_predictions_follow_beam_theory(bend):
    loads = {r['load_g']: r for r in bend['predictions']['loads']}
    assert loads[200]['pinned_mm'][0] == pytest.approx(4 * loads[200]['fixed_mm'][0], rel=.01)
    assert loads[200]['pinned_mm'][0] == pytest.approx(2 * loads[100]['pinned_mm'][0], rel=.01)
    assert loads[100]['pinned_mm'][1] < 3.0                 # inside T3's provisional 3 mm sag limit
    assert loads[200]['stress_fraction_of_typical_strength'] < .5
    assert bend['predicted_log_verdict']['pass']
