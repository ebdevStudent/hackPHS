"""Check a filled measurement form and, on request, write cad/apex2-cage/measurements.json.

  python apply_measurements.py form.csv            # check only, print what would change
  python apply_measurements.py form.csv --write    # also write measurements.json (backup kept)
  python apply_measurements.py --blank form.csv    # create an empty form with methods and vendor values

The form is a CSV with columns name,value,unit,notes. Blank values are ignored. Unknown names, wrong
units, non-numbers and values outside the plausible range stop the run; nothing is written unless every
row is valid. After writing, regenerate both designs in Fusion (P1A and P1B) and re-run make_plates.py.
"""
import argparse
import csv
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

import cage_model
from measurement_schema import MASSES, PARAMETERS

TARGET = cage_model.CAGE_DIR / 'measurements.json'
ROD_BASELINE = 1.0


def vendor_value(name):
    params, masses = cage_model.overrides('vendor_specs.json')
    raw = params.get(name, masses.get(name))
    return raw


def blank_form(path):
    with Path(path).open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['name', 'value', 'unit', 'notes', 'design', 'how_to_measure', 'vendor_or_placeholder'])
        for name, (unit, low, high, design, how) in PARAMETERS.items():
            writer.writerow([name, '', unit, '', design, how, vendor_value(name) or ''])
        for name, (low, high, how) in MASSES.items():
            writer.writerow([name, '', 'g', '', 'mass', how, vendor_value(name) or ''])


def number(text):
    value = float(text)
    if not math.isfinite(value): raise ValueError('not finite')
    return value


def check(rows, existing=None):
    """Return (parameters, masses, errors, warnings) from form rows."""
    params, masses, errors, warnings = {}, {}, [], []
    seen = set()
    for line, row in enumerate(rows, start=2):
        name = (row.get('name') or '').strip()
        text = (row.get('value') or '').strip()
        unit = (row.get('unit') or '').strip()
        if not name and not text: continue
        if name in seen: errors.append(f'line {line}: {name} appears twice'); continue
        seen.add(name)
        if not text: continue
        if name not in PARAMETERS and name not in MASSES:
            errors.append(f'line {line}: unknown name "{name}" (it would be ignored by the generators)'); continue
        try: value = number(text)
        except ValueError: errors.append(f'line {line}: {name} value "{text}" is not a number'); continue
        if name in PARAMETERS:
            expected, low, high = PARAMETERS[name][:3]
            if unit != expected: errors.append(f'line {line}: {name} unit must be "{expected}", not "{unit}"'); continue
            if not low <= value <= high: errors.append(f'line {line}: {name} = {value} {unit} is outside {low}-{high}; check for a typing error'); continue
            params[name] = f'{value:g} {unit}'
        else:
            low, high = MASSES[name][:2]
            if unit != 'g': errors.append(f'line {line}: {name} unit must be "g"'); continue
            if not low <= value <= high: errors.append(f'line {line}: {name} = {value} g is outside {low}-{high}'); continue
            masses[name] = value
        vendor = vendor_value(name)
        if vendor is not None:
            reference = float(str(vendor).split()[0]) if isinstance(vendor, str) else float(vendor) if not isinstance(vendor, list) else None
            if reference and abs(value - reference) > .1 * abs(reference):
                warnings.append(f'{name}: measured {value:g} differs from the vendor/placeholder {reference:g} by more than 10 %')
    values = {k: float(v.split()[0]) for k, v in params.items()}
    if 'rod_dia' in values and abs(values['rod_dia'] - ROD_BASELINE) > 1e-5:
        warnings.append(f'rod_dia {values["rod_dia"]:g} mm: cad/apex2-cage/validation.py currently accepts only {ROD_BASELINE} mm, '
                        'so regeneration will stop until that gate is reviewed (adopted 1 mm baseline).')
    full = cage_model.parameters('p1a', {**(existing or {}), **params})
    adjacent = full['motor_diag'] / math.sqrt(2)
    if full['prop_dia'] >= adjacent:
        errors.append(f'prop_dia {full["prop_dia"]:g} mm would overlap the neighbouring prop ({adjacent:.1f} mm between adjacent motors)')
    for pack in ('450', '1100'):
        if full[f'batt{pack}_w'] / 2 + full['strap_slot_t'] > full['carrier_core_w'] / 2:
            warnings.append(f'{pack} mAh pack plus strap is wider than the carrier centre; the generator will stop')
    if 'thrust_total_g' in masses and 'bare_aircraft_g' in masses:
        for pack in ('pack_450_g', 'pack_1100_g'):
            if pack in masses:
                ratio = masses['thrust_total_g'] / (masses['bare_aircraft_g'] + masses[pack])
                if ratio < 2: warnings.append(f'{pack[5:-2]} mAh: thrust/weight {ratio:.2f} before any cage is below the 2:1 target')
    return params, masses, errors, warnings


def merged_document(params, masses, target=TARGET):
    document = json.loads(target.read_text()) if target.exists() else {'parameters': {}, 'masses_g': {}}
    document.setdefault('parameters', {}).update(params)
    document.setdefault('masses_g', {}).update(masses)
    document['_instructions'] = ('Filled by cad/kit/apply_measurements.py from a checked measurement form. '
                                 'Regenerate both Fusion designs (P1A and P1B), then run make_plates.py for each.')
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('form', type=Path)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--blank', action='store_true', help='create an empty form at FORM')
    parser.add_argument('--target', type=Path, default=TARGET)
    args = parser.parse_args(argv)
    target = args.target
    if args.blank:
        blank_form(args.form); print(f'Blank form written to {args.form}'); return 0
    with args.form.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    existing = {k: v for k, v in (json.loads(target.read_text()).get('parameters') or {}).items() if v} if target.exists() else {}
    params, masses, errors, warnings = check(rows, existing)
    for message in warnings: print('WARNING', message)
    if errors:
        for message in errors: print('ERROR', message)
        print('No changes written.'); return 1
    document = merged_document(params, masses, target)
    print(json.dumps({'parameters': params, 'masses_g': masses}, indent=2))
    if not args.write:
        print('Check only. Re-run with --write to update', target); return 0
    if target.exists():
        backup = target.with_name(f'measurements.backup-{datetime.now():%Y%m%dT%H%M%S}.json')
        shutil.copy2(target, backup); print('Backup:', backup)
    target.write_text(json.dumps(document, indent=2) + '\n')
    print('Wrote', target); return 0


if __name__ == '__main__':
    sys.exit(main())
