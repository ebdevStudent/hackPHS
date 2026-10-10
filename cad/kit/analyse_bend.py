"""Evaluate a rod/hub bend-test log against the acceptance limits in README.md.

CSV columns: specimen,load_g,deflection_mm,phase,slip_mm,notes
  phase: load (increasing), hold (after 30 s at the top load), unload (back at zero load)
  deflection_mm: mid-span reading on the jig scale relative to the zero-load reading
  slip_mm: movement of the pen mark at either socket mouth (largest of the two)
"""
import argparse
import csv
import json
import sys
from pathlib import Path

RESIDUAL_LIMIT_MM = 0.25    # scale resolution: any visible permanent set fails
SLIP_LIMIT_MM = 0.5
TOP_LOAD_G = 200.0


def analyse(rows):
    specimens = {}
    for row in rows:
        specimens.setdefault(row['specimen'], []).append(row)
    results = []
    for name, data in specimens.items():
        problems = []
        try:
            loads = [(float(r['load_g']), float(r['deflection_mm'])) for r in data if r['phase'] == 'load']
            unload = [float(r['deflection_mm']) for r in data if r['phase'] == 'unload']
            slip = max(float(r.get('slip_mm') or 0) for r in data)
        except (KeyError, ValueError) as error:
            results.append({'specimen': name, 'pass': False, 'problems': [f'unreadable row: {error}']}); continue
        if len(loads) < 3: problems.append('need at least three load steps')
        if not loads or max(l for l, _ in loads) < TOP_LOAD_G: problems.append(f'top load below {TOP_LOAD_G:g} g')
        if not unload: problems.append('no unloaded (residual) reading')
        stiffness = None
        if len(loads) >= 2:
            mean_l = sum(l for l, _ in loads) / len(loads); mean_d = sum(d for _, d in loads) / len(loads)
            sxx = sum((d - mean_d) ** 2 for _, d in loads)
            if sxx > 0:
                slope = sum((d - mean_d) * (l - mean_l) for l, d in loads) / sxx
                stiffness = round(slope, 1)       # grams per mm of mid-span deflection
        residual = abs(unload[-1]) if unload else None
        if residual is not None and residual > RESIDUAL_LIMIT_MM: problems.append(f'residual {residual:.2f} mm > {RESIDUAL_LIMIT_MM} mm')
        if slip > SLIP_LIMIT_MM: problems.append(f'joint slip {slip:.2f} mm > {SLIP_LIMIT_MM} mm')
        if any(r.get('notes', '').lower().startswith(('crack', 'whiten', 'pullout', 'pull-out')) for r in data):
            problems.append('visible damage noted')
        top = max(loads) if loads else None
        results.append({'specimen': name, 'pass': not problems, 'problems': problems, 'stiffness_g_per_mm': stiffness,
                        'deflection_at_top_load_mm': top[1] if top else None, 'residual_mm': residual, 'max_slip_mm': slip})
    return {'specimens': results, 'pass': bool(results) and all(r['pass'] for r in results),
            'limits': {'residual_mm': RESIDUAL_LIMIT_MM, 'slip_mm': SLIP_LIMIT_MM, 'top_load_g': TOP_LOAD_G}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    with args.log.open(newline='') as handle:
        result = analyse(list(csv.DictReader(handle)))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['pass'] else 1)
