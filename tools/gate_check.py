"""Check the fixed-cage gate and battery records from their CSV logs (docs/25-test-records.md).

Gate before P1B (user decision 2026-10-07), all three required:
  1. ten consecutive low-energy contacts with no damage and no prop strike;
  2. at least three minutes of usable caged flight;
  3. repeatable manual recovery. Proposed rule, pending the team's confirmation: every contact in the
     counted run of ten was recovered by the pilot without landing or help.
A prop strike, any damage or a repair resets the consecutive count.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

YES = {'y', 'yes', 'true', '1'}
NO = {'n', 'no', 'false', '0'}
USABLE_FLIGHT_S = 180
CELL_FULL_MAX_V, CELL_LOW_V = 4.22, 3.3      # 4.2 V/cell stop-charge per both OVONIC listings; 3.3 V/cell floor


def flag(value, field, line, problems):
    text = (value or '').strip().lower()
    if text in YES: return True
    if text in NO: return False
    problems.append(f'line {line}: {field} must be y or n, not "{value}"')
    return None


def contacts(rows):
    problems, streak, best, best_rows, run = [], 0, 0, [], []
    for line, row in enumerate(rows, start=2):
        strike = flag(row.get('prop_strike'), 'prop_strike', line, problems)
        damage = flag(row.get('damage'), 'damage', line, problems)
        repair = flag(row.get('repair'), 'repair', line, problems)
        recovered = flag(row.get('recovered'), 'recovered', line, problems)
        if None in (strike, damage, repair, recovered):
            streak, run = 0, []; continue
        if strike or damage or repair:
            streak, run = 0, []; continue
        streak += 1; run.append({'contact': row.get('contact_no'), 'recovered': recovered, 'cage': row.get('cage_revision')})
        if streak > best: best, best_rows = streak, list(run)
    tail = best_rows[-10:]
    revisions = {r['cage'] for r in tail}
    if len(revisions) > 1: problems.append('the counted run mixes cage revisions; restart the count after any cage change')
    return {'best_consecutive_clean': best, 'contacts_logged': len(rows),
            'ten_consecutive': best >= 10 and len(revisions) <= 1,
            'recovery_all_in_run': len(tail) == 10 and all(r['recovered'] for r in tail),
            'problems': problems}


def flights(rows):
    problems, caged, best = [], [], 0.0
    for line, row in enumerate(rows, start=2):
        try:
            cells = int(row.get('cells') or 2)
            start_v, end_v, seconds = float(row['start_v']), float(row['end_v']), float(row['flight_s'])
        except (KeyError, ValueError):
            problems.append(f'line {line}: start_v, end_v and flight_s must be numbers'); continue
        if start_v / cells > CELL_FULL_MAX_V: problems.append(f'line {line}: pack {row.get("pack_id")} started at {start_v / cells:.2f} V/cell (over 4.2 V/cell)')
        if end_v / cells < CELL_LOW_V: problems.append(f'line {line}: pack {row.get("pack_id")} ended at {end_v / cells:.2f} V/cell (below 3.3 V/cell: over-discharged)')
        if (row.get('configuration') or '').upper() in ('P1A', 'P1B'):
            usable = seconds if end_v / cells >= CELL_LOW_V else 0
            caged.append(usable); best = max(best, usable)
    return {'caged_flights': len(caged), 'best_usable_caged_s': best, 'three_minutes': best >= USABLE_FLIGHT_S, 'problems': problems}


def gate(contact_rows, flight_rows):
    c, f = contacts(contact_rows), flights(flight_rows)
    passed = c['ten_consecutive'] and c['recovery_all_in_run'] and f['three_minutes'] and not c['problems'] and not f['problems']
    return {'contacts': c, 'flights': f, 'gate_passed': passed,
            'recovery_rule': 'proposed: all ten counted contacts recovered by the pilot without landing or help'}


def read(path):
    with Path(path).open(newline='') as handle: return list(csv.DictReader(handle))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--contacts', type=Path, required=True)
    parser.add_argument('--flights', type=Path, required=True)
    args = parser.parse_args()
    result = gate(read(args.contacts), read(args.flights))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['gate_passed'] else 1)
