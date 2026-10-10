"""Simulated rod/hub bend test: jig assembly fit with solids, then beam-theory predictions of the readings.

1. Assembly (Manifold Booleans): two bend_test_blocks seated in the jig pockets (pushed toward the middle),
   a cut rod in both sockets, and the load hook at mid-span. Checks the rod clears every bore and the jig,
   seats with the generator's end gap at each socket floor, the blocks fit their pockets, and the rod can
   deflect down to the bottom of the scale without touching the channel floor.
2. Predictions: mid-span deflection of a 1 mm solid round rod over the exposed span under the logged loads,
   bounded by pinned ends (loose sockets) and fixed ends (tight sockets), using the 28-40 GPa lengthwise
   modulus that Easy Composites publishes for its own pultruded rods. These are expected-reading ranges,
   not properties of the ordered rods. The predicted log is run through analyse_bend to show the pipeline.
"""
import json
import math
from pathlib import Path

import manifold3d as mf
import numpy as np

import analyse_bend
import cage_model
import test_pieces

MODULUS_MPA = (28000, 40000)       # Easy Composites pultruded rod, lengthwise (not the ordered rods)
STRENGTH_MPA = (400, 500)
LOADS_G = [20, 50, 100, 200]
G = 9.81 / 1000                    # N per gram


def assembly(values):
    p1b = cage_model.parameters('p1b')
    block, axis_z, arm_out, span, _ = test_pieces.dimensions(values, p1b)
    jig, info = test_pieces.bend_test_jig(values, block, axis_z, arm_out, span)
    body, tip = test_pieces.bend_test_block(values, block, axis_z, arm_out)
    clearance, wall, base_t = 0.3, 3.0, 4.0
    pocket_l = block['length'] + 2 * clearance
    length = info['jig_length_mm']
    y0 = wall + clearance                                       # block centred in its pocket across Y
    # Left block pushed toward the middle: its far face meets the inner pocket end.
    left = body.translate((wall + pocket_l - block['length'], y0, base_t))
    # Right block: mirror about X, pushed toward the middle.
    right = body.mirror((1, 0, 0)).translate((length - wall - pocket_l + block['length'], y0, base_t))
    tips = (wall + pocket_l + arm_out, length - wall - pocket_l - arm_out)
    rod_y, rod_z = y0 + block['width'] / 2, base_t + axis_z
    socket_floor = (tips[0] - values['socket_depth'], tips[1] + values['socket_depth'])
    rod_ends = (socket_floor[0] + values['rod_end_gap'], socket_floor[1] - values['rod_end_gap'])
    rod = test_pieces.cylinder_x(rod_ends[0], rod_ends[1], rod_y, rod_z, values['rod_dia'])
    mid = (tips[0] + tips[1]) / 2
    h = test_pieces.HOOK
    hook = test_pieces.load_hook(values).translate((mid - h['thick'] / 2, rod_y - h['width'] / 2, rod_z - h['rod_z']))
    floor_gap = rod_z - values['rod_dia'] / 2 - test_pieces.CHANNEL_FLOOR
    hook_room = rod_z - h['rod_z'] - test_pieces.CHANNEL_FLOOR      # hook bottom above the channel floor, unloaded
    sag = test_pieces.cylinder_x(tips[0], tips[1], rod_y, rod_z - (floor_gap - .2), values['rod_dia'])
    checks = {
        'rod_length_mm': round(rod_ends[1] - rod_ends[0], 3),
        'rod_cut_len_mm': round(values['rod_cut_len'], 3),
        'rod_x_blocks_mm3': round((rod ^ (left + right)).volume(), 6),
        'rod_x_jig_mm3': round((rod ^ jig).volume(), 6),
        'blocks_x_jig_mm3': round(((left + right) ^ jig).volume(), 6),
        'blocks_overlap_mm3': round((left ^ right).volume(), 6),
        'rod_end_gap_each_mm': values['rod_end_gap'],
        'room_to_deflect_mm': round(floor_gap, 3),
        'deflected_rod_x_jig_mm3': round((sag ^ jig).volume(), 6),
        'hook_x_jig_mm3': round((hook ^ jig).volume(), 6),
        'hook_x_rod_mm3': round((hook ^ rod).volume(), 6),
        'hook_room_above_floor_mm': round(hook_room, 3),
    }
    checks['pass'] = (abs(checks['rod_length_mm'] - checks['rod_cut_len_mm']) < 1e-3 and checks['rod_x_blocks_mm3'] < 1e-4
                      and checks['rod_x_jig_mm3'] < 1e-4 and checks['blocks_x_jig_mm3'] < 1e-4 and checks['blocks_overlap_mm3'] < 1e-4
                      and checks['deflected_rod_x_jig_mm3'] < 1e-4 and checks['hook_x_jig_mm3'] < 1e-4 and checks['hook_x_rod_mm3'] < 1e-4
                      and hook_room > 2.0)
    return checks, span


def predictions(values, span):
    d = values['rod_dia']
    inertia = math.pi * d ** 4 / 64
    rows = []
    for grams in LOADS_G:
        force = grams * G
        pinned = [force * span ** 3 / (48 * e * inertia) for e in MODULUS_MPA]
        fixed = [x / 4 for x in pinned]
        stress = force * span / 4 * (d / 2) / inertia             # pinned, worst case
        rows.append({'load_g': grams, 'pinned_mm': [round(min(pinned), 3), round(max(pinned), 3)],
                     'fixed_mm': [round(min(fixed), 3), round(max(fixed), 3)], 'max_stress_mpa_pinned': round(stress, 1),
                     'stress_fraction_of_typical_strength': round(stress / STRENGTH_MPA[0], 2)})
    return {'span_mm': round(span, 3), 'rod_diameter_mm': d, 'second_moment_mm4': round(inertia, 5), 'loads': rows}


def predicted_log(prediction):
    """A log a correct joint would produce (pinned, stiffest modulus); used to exercise analyse_bend."""
    rows = [{'specimen': 'SIM', 'load_g': '0', 'deflection_mm': '0', 'phase': 'load', 'slip_mm': '0', 'notes': ''}]
    for row in prediction['loads']:
        rows.append({'specimen': 'SIM', 'load_g': str(row['load_g']), 'deflection_mm': str(row['pinned_mm'][0]), 'phase': 'load', 'slip_mm': '0', 'notes': ''})
    top = prediction['loads'][-1]
    rows.append({'specimen': 'SIM', 'load_g': str(top['load_g']), 'deflection_mm': str(top['pinned_mm'][0]), 'phase': 'hold', 'slip_mm': '0', 'notes': ''})
    rows.append({'specimen': 'SIM', 'load_g': '0', 'deflection_mm': '0', 'phase': 'unload', 'slip_mm': '0', 'notes': ''})
    return rows


def run():
    values = cage_model.parameters('p1a')
    fit, span = assembly(values)
    prediction = predictions(values, span)
    verdict = analyse_bend.analyse(predicted_log(prediction))
    return {'assembly': fit, 'predictions': prediction, 'predicted_log_verdict': verdict,
            'scope': __doc__.strip()}


if __name__ == '__main__':
    out = Path(__file__).parent / 'reports' / 'bend-simulation.json'
    out.parent.mkdir(exist_ok=True)
    result = run()
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'assembly': result['assembly'], 'loads': result['predictions']['loads'],
                      'predicted_log_pass': result['predicted_log_verdict']['pass']}, indent=2))
