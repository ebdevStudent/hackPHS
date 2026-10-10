"""P1B mass budget against the 175 g all-up limit, and what each lightening option would buy.

Reads the current P1B export manifest (native solid volumes, written by build_p1b.py), the rod geometry
from the generator parameters and the vendor/measured masses. Nothing in cad/apex2-cage is changed: the
options are estimates for a decision, to be applied in the generators and re-verified in Fusion.
"""
import json
import math
from pathlib import Path

import cage_model

LIMIT_G = 175.0
UNWEIGHED_EXTRAS_G = (8.0, 10.0)        # antenna, receiver wiring, XT30 lead, screws not modelled (CAD README)
STEEL_M2_G, NYLON_M2_G = 0.20, 0.04      # M2 x 6 socket cap: stainless ~0.2 g, nylon ~0.04 g (typical, weigh yours)


def current():
    manifest = json.loads((cage_model.CAGE_DIR / 'exports_p1b' / 'manifest.json').read_text())
    values = cage_model.parameters('p1b')
    parts = {p['name']: (p['qty'], p['native_volume_mm3'] * values['petg_density'] / 1000) for p in manifest['parts']
             if p['name'] != 'gimbal_fit_coupon'}
    printed = sum(q * g for q, g in parts.values())
    points, edges, pole_edges = cage_model.cage_geometry(values)
    inset = values['hub_arm_len'] - values['socket_depth'] + values['rod_end_gap']
    rod_mm = sum(math.dist(points[i], points[j]) - 2 * inset for i, j in edges + pole_edges)
    rods = rod_mm * math.pi * (values['rod_dia'] / 2) ** 2 * values['rod_density'] / 1000
    screws = int(16 * round(values['junction_screws_per_side'])) + 12
    hardware = 6 * 0.2 + 6 * 0.26 + screws * STEEL_M2_G
    masses = cage_model.masses()
    bare = masses.get('bare_aircraft_g') or sum(masses[k] for k in ('frame_g', 'aio_g', 'motors_x4_g', 'props_x4_g', 'camera_g'))
    return {'parts_g': {k: (q, round(g, 3)) for k, (q, g) in parts.items()}, 'printed_g': printed, 'rods_g': rods,
            'hardware_g': hardware, 'screws': screws, 'bare_g': bare,
            'packs_g': {'450': masses['pack_450_g'], '1100': masses['pack_1100_g']}}


def options(state):
    parts = state['parts_g']
    def part(name): return parts.get(name, (0, 0))[0] * parts.get(name, (0, 0))[1]
    rings = part('outer_ring_quarter') + part('inner_ring_quarter')
    return [
        {'option': 'Fly P1B with the 450 mAh pack only (keep 1100 mAh for P1A)', 'saving_g': state['packs_g']['1100'] - state['packs_g']['450'],
         'cost': 'Shorter endurance; no CAD change', 'risk': 'none structural'},
        {'option': 'Nylon M2 screws for the 16 ring splices (steel kept at the carrier/arms)', 'saving_g': 16 * (STEEL_M2_G - NYLON_M2_G),
         'cost': 'Buy nylon M2 x 6 (within contingency)', 'risk': 'Lower clamp force; check splice slip with the coupon'},
        {'option': 'Ring band thickness 3.0 -> 2.5 mm (ring_t)', 'saving_g': rings * (1 - 2.5 / 3.0),
         'cost': 'Regenerate P1B, re-run sweep/validation', 'risk': 'Out-of-plane ring stiffness falls ~42 % (t^3); load-test a quarter first'},
        {'option': 'Pocket the two arm pivot blocks and Z junction posts (~30 % of their volume)', 'saving_g': .3 * (part('arm_pivot_block') + part('outer_junction_Z_bearing')),
         'cost': 'Generator change', 'risk': 'Pivot alignment; keep material around pins and bearing seats'},
        {'option': 'Larger carrier window (~20 % of carrier volume)', 'saving_g': .2 * part('carrier_plate'),
         'cost': 'Generator change', 'risk': 'Carrier twist with the 1100 mAh pack'},
    ]


def report():
    state = current()
    added = state['printed_g'] + state['rods_g'] + state['hardware_g']
    rows = []
    for pack, mass in state['packs_g'].items():
        accounted = state['bare_g'] + mass + added
        rows.append({'pack': pack, 'accounted_g': round(accounted, 2),
                     'with_extras_g': [round(accounted + e, 2) for e in UNWEIGHED_EXTRAS_G],
                     'margin_after_extras_g': [round(LIMIT_G - accounted - e, 2) for e in reversed(UNWEIGHED_EXTRAS_G)]})
    opts = options(state)
    for item in opts: item['saving_g'] = round(item['saving_g'], 2)
    return {'added_structure_g': round(added, 2), 'printed_g': round(state['printed_g'], 2), 'rods_g': round(state['rods_g'], 2),
            'hardware_g': round(state['hardware_g'], 2), 'bare_aircraft_g': round(state['bare_g'], 2), 'configurations': rows,
            'options': opts, 'basis': 'Native solid volumes x 1.27 g/cm3 PETG (thin parts print essentially solid), '
            'rods 1.55 g/cm3, hardware as in build_p1b.py, vendor component sums; estimates, not weighed parts.'}


if __name__ == '__main__':
    out = Path(__file__).parent / 'reports' / 'p1b-mass-options.json'
    out.parent.mkdir(exist_ok=True)
    result = report()
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
