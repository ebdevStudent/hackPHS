"""GO / NO-GO preflight logic used by the laptop motor dashboard (tools/preflight_checks.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import preflight_checks as pf  # noqa: E402

READY = dict(firmware=[4, 4, 2], voltage=8.3, arming_blocked=['MSP'], rc=[1500, 1500, 1500, 990, 1000],
             mode_ranges=[(0, 0, 1800, 2100), (1, 0, 900, 2100)], level_limit=35, board_alignment=[0, 0, 0],
             failsafe=dict(delay_s=1.5, off_delay_s=1, throttle=1000, procedure='DROP'),
             vtx=dict(freq=5917, pit=False), config=dict(motor_protocol='DSHOT300', dshot_idle_value=1000))


def by_name(checks):
    return {c['name']: c for c in checks}


def test_ready_fc_has_no_failures_or_warnings():
    checks = pf.fc_checks(READY)
    assert {c['status'] for c in checks} <= {'ok', 'manual'}
    assert pf.summary(checks) == 'GO'


def test_parked_angle_mode_and_missing_battery_are_no_go():
    fc = dict(READY, voltage=2.1, mode_ranges=[(0, 0, 1800, 2100)])
    checks = by_name(pf.fc_checks(fc))
    assert checks['Battery']['status'] == 'fail' and checks['ANGLE (self-level) mode']['status'] == 'fail'
    assert pf.summary(list(checks.values())) == 'NO-GO'


def test_radio_loss_suppresses_stick_checks_and_fails():
    checks = by_name(pf.fc_checks(dict(READY, arming_blocked=['RXLOSS', 'MSP'])))
    assert checks['Radio link (ELRS)']['status'] == 'fail' and 'Throttle at minimum' not in checks


def test_warnings_for_high_throttle_switch_on_pit_mode_and_low_charge():
    fc = dict(READY, voltage=7.4, rc=[1500, 1500, 1500, 1300, 2000], vtx=dict(freq=5917, pit=True),
              arming_blocked=['ANGLE', 'MSP'])
    checks = by_name(pf.fc_checks(fc))
    for name in ('Battery', 'Throttle at minimum', 'ARM switch off', 'Video transmitter', 'Other arming blockers'):
        assert checks[name]['status'] == 'warn', name
    assert 'tilted' in checks['Other arming blockers']['detail']
    assert pf.summary(list(checks.values())) == 'CHECK'


def test_pi_modes():
    assert pf.pi_checks({'fpv': {'signal': 'PICTURE'}})[1]['status'] == 'ok'
    track = {'source': {'kind': 'camera'}, 'bridge': 'MOCK / no physical output', 'settings': {'target_mode': 'tag'},
             'state': 'MANUAL', 'fault': None}
    checks = by_name(pf.pi_checks({'track': track, 'fpv': None}))
    assert checks['Pi bridge']['status'] == 'warn' and 'TRACK' in checks['Pi']['detail']
    assert pf.pi_checks({'error': 'unreachable'})[0]['status'] == 'warn'
