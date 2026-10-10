"""tools/thrust_log.py and tools/gate_check.py on hand-made logs (no hardware)."""
import csv
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
import gate_check  # noqa: E402
import thrust_log  # noqa: E402


def steps(*pairs):
    return [{'step': i + 1, 'throttle_pct': t, 'reading_g': r, 'voltage_v': v, 'current_a': ''} for i, (t, r, v) in enumerate(pairs)]


def test_lift_setup_subtracts_readings_and_rates_each_configuration():
    rows = steps((25, 900, 8.2), (50, 820, 8.0), (75, 720, 7.7), (100, 650, 7.4))
    summary = thrust_log.summarise(rows, 1000.0, 'lift', {'bare_aircraft_g': 50, 'pack_450_g': 26, 'pack_1100_g': 48})
    assert summary['peak_thrust_g'] == 350 and [s['thrust_g'] for s in summary['steps']] == [100, 180, 280, 350]
    by = {c['configuration']: c for c in summary['configurations']}
    assert by['P1A + 450 mAh']['all_up_g'] == pytest.approx(120.7) and by['P1A + 450 mAh']['verdict'] == 'meets 2:1'
    assert by['P1B + 1100 mAh']['thrust_to_weight'] == pytest.approx(350 / (50 + 48 + 74.1), abs=.01)
    assert not summary['warnings']


def test_push_setup_and_verdict_bands():
    rows = steps((100, 400, 7.2))
    summary = thrust_log.summarise(rows, 200.0, 'push', {'bare_aircraft_g': 60, 'pack_450_g': 26, 'pack_1100_g': 48})
    assert summary['peak_thrust_g'] == 200
    verdicts = {c['configuration']: c['verdict'] for c in summary['configurations']}
    assert verdicts['P1A + 450 mAh'] == 'below 2:1' and verdicts['P1B + 1100 mAh'] == 'REDESIGN (< 1.5:1)'


def test_warnings_for_missing_full_throttle_drop_and_sag():
    summary = thrust_log.summarise(steps((50, 800, 7.0), (75, 830, 6.5)), 1000.0, 'lift', {})
    text = ' '.join(summary['warnings'])
    assert 'No 100 %' in text and 'fell' in text and summary['configurations'] == []
    sag = thrust_log.summarise(steps((100, 700, 6.4)), 1000.0, 'lift', {})
    assert any('sagged' in w for w in sag['warnings'])


def test_thrust_cli_from_csv_writes_log_and_summary(tmp_path):
    log = tmp_path / 'log.csv'
    with log.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=thrust_log.FIELDS); writer.writeheader()
        for row in steps((50, 820, 8.0), (100, 650, 7.5)): writer.writerow({**row, 'note': ''})
    assert thrust_log.main(['--from-csv', str(log), '--tare', '1000', '--setup', 'lift', '--bare', '50', '--pack450', '26',
                            '--output', str(tmp_path / 'out'), '--label', 'bench']) == 0
    summary = json.loads(next((tmp_path / 'out').glob('bench-*.json')).read_text())
    assert summary['peak_thrust_g'] == 350 and len(summary['configurations']) == 2


def test_thrust_cli_needs_a_tare_for_csv(tmp_path):
    with pytest.raises(SystemExit):
        thrust_log.main(['--from-csv', str(tmp_path / 'x.csv'), '--setup', 'lift'])


def test_manual_collection(monkeypatch):
    answers = iter(['', '1000', '', '700', '7.6', '', ])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(answers))
    args = type('A', (), {'serial': None, 'steps': [100]})()
    tare, rows = thrust_log.collect(args)
    assert tare == 1000 and rows[0]['reading_g'] == 700 and rows[0]['voltage_v'] == 7.6 and rows[0]['current_a'] == ''


def test_serial_reading_averages_numeric_lines(monkeypatch):
    lines = iter([b'HX711 ready\n', b'500.0\n', b'502.0 g\n', b'noise\n', b'504\n'] + [b''] * 50)
    class Port:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def readline(self): return next(lines)
    monkeypatch.setattr('serial.Serial', Port)
    assert thrust_log.read_serial_value('/dev/fake', timeout=.2, samples=3) == pytest.approx(502)


def contact(n, strike='n', damage='n', repair='n', recovered='y', cage='A1'):
    return {'contact_no': str(n), 'cage_revision': cage, 'prop_strike': strike, 'damage': damage, 'repair': repair, 'recovered': recovered}


def flight(start=8.3, end=7.2, seconds=200, config='P1A', cells='2', pack='450-1'):
    return {'pack_id': pack, 'cells': cells, 'configuration': config, 'start_v': str(start), 'end_v': str(end), 'flight_s': str(seconds)}


def test_gate_passes_with_ten_clean_recovered_contacts_and_a_three_minute_flight():
    result = gate_check.gate([contact(i) for i in range(10)], [flight()])
    assert result['gate_passed'] and result['contacts']['best_consecutive_clean'] == 10


@pytest.mark.parametrize('field', ['strike', 'damage', 'repair'])
def test_any_strike_damage_or_repair_resets_the_count(field):
    rows = [contact(i) for i in range(6)] + [contact(6, **{field: 'y'})] + [contact(i) for i in range(7, 16)]
    result = gate_check.gate(rows, [flight()])
    assert result['contacts']['best_consecutive_clean'] == 9 and not result['gate_passed']


def test_unrecovered_contact_or_mixed_cage_fails_the_gate():
    rows = [contact(i) for i in range(9)] + [contact(9, recovered='n')]
    assert not gate_check.gate(rows, [flight()])['gate_passed']
    mixed = [contact(i) for i in range(5)] + [contact(i, cage='A2') for i in range(5, 10)]
    result = gate_check.gate(mixed, [flight()])
    assert not result['gate_passed'] and 'mixes cage revisions' in result['contacts']['problems'][0]


def test_flight_rules_and_battery_flags():
    assert not gate_check.gate([contact(i) for i in range(10)], [flight(seconds=170)])['gate_passed']
    assert not gate_check.gate([contact(i) for i in range(10)], [flight(config='bare')])['gate_passed']
    over = gate_check.flights([flight(start=8.7)])
    under = gate_check.flights([flight(end=6.4)])
    assert 'over 4.2 V/cell' in over['problems'][0] and 'over-discharged' in under['problems'][0]
    assert under['best_usable_caged_s'] == 0


def test_bad_values_are_reported():
    result = gate_check.gate([contact(1, strike='maybe')], [{'pack_id': 'x', 'start_v': 'full'}])
    assert result['contacts']['problems'] and result['flights']['problems'] and not result['gate_passed']


def test_templates_have_the_columns_the_tools_read():
    forms = Path(__file__).resolve().parents[2] / 'docs' / 'forms'
    contact_header = (forms / 'contact-log.csv').read_text().splitlines()[0].split(',')
    battery_header = (forms / 'battery-log.csv').read_text().splitlines()[0].split(',')
    thrust_header = (forms / 'thrust-log.csv').read_text().splitlines()[0].split(',')
    assert {'contact_no', 'cage_revision', 'prop_strike', 'damage', 'repair', 'recovered'} <= set(contact_header)
    assert {'pack_id', 'cells', 'configuration', 'start_v', 'end_v', 'flight_s'} <= set(battery_header)
    assert thrust_header == thrust_log.FIELDS
