"""Static thrust test logger: record throttle steps from a scale and report thrust-to-weight.

Setups (docs/25-test-records.md#static-thrust):
  lift  aircraft upright on the scale, props blowing down past it, weighted base: thrust = tare - reading
  push  aircraft inverted on a stand on the scale, props pushing down onto it:   thrust = reading - tare
Readings come from typed entry (--manual), a load-cell board printing one number per line (--serial),
or an existing CSV (--from-csv). Writes a CSV log and a JSON summary with thrust-to-weight for each
configuration whose mass is known. Targets: >= 2:1 static; below 1.5:1 the build needs redesign.
"""
import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ['step', 'throttle_pct', 'reading_g', 'voltage_v', 'current_a', 'note']
# A reading line is only a number, optionally followed by g; banners like 'HX711 ready' are ignored.
NUMBER = re.compile(r'\s*(-?\d+(?:\.\d+)?)\s*(?:g|grams)?\s*')
TARGET, REDESIGN = 2.0, 1.5
# Accounted CAD estimates (cad/apex2-cage README, 2026-10-08) used only when no weighed totals are given.
DEFAULT_ADDED_G = {'P1A': 44.7, 'P1B': 74.1}


def thrust_g(reading, tare, setup):
    return tare - reading if setup == 'lift' else reading - tare


def summarise(rows, tare, setup, masses):
    steps = []
    for row in rows:
        reading = float(row['reading_g'])
        steps.append({'step': int(row['step']), 'throttle_pct': float(row['throttle_pct']),
                      'thrust_g': round(thrust_g(reading, tare, setup), 1),
                      'voltage_v': float(row['voltage_v']) if row.get('voltage_v') not in (None, '') else None,
                      'current_a': float(row['current_a']) if row.get('current_a') not in (None, '') else None})
    full = [s for s in steps if s['throttle_pct'] >= 99]
    peak = max((s['thrust_g'] for s in (full or steps)), default=None)
    sag = [s['voltage_v'] for s in full if s['voltage_v'] is not None]
    configurations = []
    bare = masses.get('bare_aircraft_g')
    for config, added in (('P1A', masses.get('p1a_added_g', DEFAULT_ADDED_G['P1A'])), ('P1B', masses.get('p1b_added_g', DEFAULT_ADDED_G['P1B']))):
        for pack in ('450', '1100'):
            pack_g = masses.get(f'pack_{pack}_g')
            if peak is None or bare is None or pack_g is None:
                continue
            all_up = bare + pack_g + added
            ratio = peak / all_up
            configurations.append({'configuration': f'{config} + {pack} mAh', 'all_up_g': round(all_up, 1), 'thrust_to_weight': round(ratio, 2),
                                   'verdict': 'meets 2:1' if ratio >= TARGET else 'below 2:1' if ratio >= REDESIGN else 'REDESIGN (< 1.5:1)',
                                   'within_175_g': all_up <= 175})
    monotonic = all(b['thrust_g'] >= a['thrust_g'] - 5 for a, b in zip(steps, steps[1:]) if b['throttle_pct'] > a['throttle_pct'])
    warnings = []
    if not full: warnings.append('No 100 % throttle step: peak thrust is from a lower setting')
    if not monotonic: warnings.append('Thrust fell as throttle rose: check the mount, scale creep or voltage sag')
    if sag and min(sag) < 6.6: warnings.append(f'Pack sagged to {min(sag):.2f} V under full throttle (below 3.3 V/cell)')
    return {'setup': setup, 'tare_g': tare, 'peak_thrust_g': peak, 'full_throttle_voltage_v': min(sag) if sag else None,
            'steps': steps, 'configurations': configurations, 'warnings': warnings,
            'targets': {'thrust_to_weight': TARGET, 'redesign_below': REDESIGN},
            'scope': 'Static bench thrust of this motor/prop/pack combination; not flight endurance or caged performance.'}


def read_serial_value(port, timeout=3.0, samples=10):
    """Average the next numeric lines from a load-cell board (one reading in grams per line)."""
    import serial
    values, deadline = [], time.monotonic() + timeout
    with serial.Serial(port, 115200, timeout=.2) as link:
        while len(values) < samples and time.monotonic() < deadline:
            match = NUMBER.fullmatch(link.readline().decode('ascii', errors='ignore'))
            if match: values.append(float(match.group(1)))
    if not values: raise RuntimeError('No numeric readings from the load cell')
    return sum(values) / len(values)


def prompt_float(label, allow_blank=False):
    while True:
        text = input(label).strip()
        if allow_blank and not text: return ''
        try: return float(text)
        except ValueError: print('Enter a number')


def collect(args):
    reader = (lambda: read_serial_value(args.serial)) if args.serial else (lambda: prompt_float('  scale reading (g): '))
    print('Props OFF or motors disarmed for the tare. Press Enter when the scale is steady.'); input()
    tare = reader()
    rows = []
    for step, throttle in enumerate(args.steps, start=1):
        print(f'Step {step}: set {throttle:g} % throttle, wait 3 s for a steady reading, then press Enter'); input()
        reading = reader()
        voltage = prompt_float('  pack voltage under load (V, blank if unknown): ', True)
        current = prompt_float('  current (A, blank if unknown): ', True)
        rows.append({'step': step, 'throttle_pct': throttle, 'reading_g': reading, 'voltage_v': voltage, 'current_a': current, 'note': ''})
        print('  Throttle to zero and let the motors cool for 10 s.')
    return tare, rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--manual', action='store_true')
    source.add_argument('--serial', help='load-cell serial port printing grams per line')
    source.add_argument('--from-csv', type=Path, help='analyse an existing log (needs --tare)')
    parser.add_argument('--setup', choices=['lift', 'push'], required=True)
    parser.add_argument('--tare', type=float)
    parser.add_argument('--steps', type=float, nargs='+', default=[25, 50, 75, 100])
    parser.add_argument('--bare', type=float, help='weighed bare aircraft (g)')
    parser.add_argument('--pack450', type=float)
    parser.add_argument('--pack1100', type=float)
    parser.add_argument('--p1a-added', type=float)
    parser.add_argument('--p1b-added', type=float)
    parser.add_argument('--label', default='thrust')
    parser.add_argument('--output', type=Path, default=Path('evidence/physical'))
    args = parser.parse_args(argv)
    if args.from_csv:
        if args.tare is None: parser.error('--from-csv needs --tare')
        with args.from_csv.open(newline='') as handle: rows = list(csv.DictReader(handle))
        tare = args.tare
    else:
        tare, rows = collect(args)
    masses = {k: v for k, v in {'bare_aircraft_g': args.bare, 'pack_450_g': args.pack450, 'pack_1100_g': args.pack1100,
                                'p1a_added_g': args.p1a_added, 'p1b_added_g': args.p1b_added}.items() if v is not None}
    summary = summarise(rows, tare, args.setup, masses)
    summary['recorded_utc'] = datetime.now(timezone.utc).isoformat()
    args.output.mkdir(parents=True, exist_ok=True)
    stem = args.output / f'{args.label}-{datetime.now():%Y%m%dT%H%M%S}'
    with stem.with_suffix('.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader()
        for row in rows: writer.writerow({k: row.get(k, '') for k in FIELDS})
    stem.with_suffix('.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ('peak_thrust_g', 'configurations', 'warnings')}, indent=2))
    print('Saved', stem.with_suffix('.csv'), 'and', stem.with_suffix('.json'))
    print('Enter the peak as thrust_total_g in the CAD measurement form (cad/kit/measurement-form.csv).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
