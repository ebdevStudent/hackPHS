"""Pi preflight and deployment scripts, run against fake system roots (no Pi, no sudo)."""
import os
import subprocess
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[1] / 'deploy'


def fake_root(tmp_path, model='Raspberry Pi 5 Model B Rev 1.0', codename='trixie', memory_kb=4000000, devices=()):
    root = tmp_path / 'root'
    (root / 'proc' / 'device-tree').mkdir(parents=True)
    (root / 'etc').mkdir()
    (root / 'dev').mkdir()
    if model is not None:
        (root / 'proc' / 'device-tree' / 'model').write_bytes(model.encode() + b'\0')
    if codename is not None:
        (root / 'etc' / 'os-release').write_text(f'ID=debian\nVERSION_CODENAME={codename}\n')
    (root / 'proc' / 'meminfo').write_text(f'MemTotal:       {memory_kb} kB\n')
    for device in devices: (root / 'dev' / device).touch()
    return root


def preflight(root, arch='aarch64', python='3.13'):
    env = {**os.environ, 'BALL_PREFLIGHT_ROOT': str(root), 'BALL_PREFLIGHT_ARCH': arch, 'BALL_PREFLIGHT_PYTHON': python}
    result = subprocess.run(['bash', str(DEPLOY / 'pi-preflight.sh')], env=env, capture_output=True, text=True, timeout=20)
    return result.returncode, result.stdout


@pytest.mark.parametrize('model,advice', [('Raspberry Pi 5 Model B Rev 1.0', 'active cooler'),
                                          ('Raspberry Pi 4 Model B Rev 1.5', 'heatsink')])
def test_pi4_and_pi5_on_trixie_pass(tmp_path, model, advice):
    code, out = preflight(fake_root(tmp_path, model=model, devices=['video0', 'ttyACM0']))
    assert code == 0 and 'Preflight passed.' in out and advice in out
    assert 'PASS  Video devices: /dev/video0' in out and 'PASS  Serial devices: /dev/ttyACM0' in out


def test_bookworm_is_refused_with_reflash_advice(tmp_path):
    code, out = preflight(fake_root(tmp_path, codename='bookworm'), python='3.11')
    assert code == 1 and 'reflash with Raspberry Pi OS (64-bit) based on Trixie' in out
    assert 'Preflight failed with 2 problem(s)' in out


def test_32_bit_os_is_refused(tmp_path):
    code, out = preflight(fake_root(tmp_path), arch='armv7l')
    assert code == 1 and 'FAIL  Architecture armv7l' in out


@pytest.mark.parametrize('python,code', [('3.13', 0), ('3.14', 0), ('3.12', 1), ('3.11', 1)])
def test_python_version_gate(tmp_path, python, code):
    assert preflight(fake_root(tmp_path), python=python)[0] == code


def test_missing_python_on_trixie_is_only_a_warning(tmp_path):
    code, out = preflight(fake_root(tmp_path), python='none')
    assert code == 0 and "installer adds Trixie's Python 3.13" in out
    code, out = preflight(fake_root(tmp_path / 'b', codename='forky'), python='none')
    assert code == 1 and "untested" in out


def test_small_memory_unknown_board_and_absent_devices_warn_only(tmp_path):
    code, out = preflight(fake_root(tmp_path, model=None, memory_kb=900000))
    assert code == 0
    assert 'WARN  Board model not readable' in out and 'WARN  Memory 878 MB' in out
    assert "run 'ball-demo cameras'" in out and '/dev/ttyACM0 when connected' in out


def test_other_board_warns(tmp_path):
    code, out = preflight(fake_root(tmp_path, model='Raspberry Pi 3 Model B'))
    assert code == 0 and 'not a Pi 4/5' in out


def test_installers_run_preflight_before_changing_the_system():
    for name in ('install-pi.sh', 'install-desktop-pi.sh'):
        text = (DEPLOY / name).read_text()
        assert text.index('pi-preflight.sh') < text.index('sudo apt-get')
        assert text.index('sudo apt-get install') < text.index('sys.version_info >= (3, 13)')


def test_service_has_device_groups_and_installer_adds_them():
    service = (DEPLOY / 'ball-demo.service').read_text()
    assert 'SupplementaryGroups=video dialout' in service and 'ProtectHome=true' in service
    installer = (DEPLOY / 'install-pi.sh').read_text()
    assert 'usermod -a -G video,dialout ball-demo' in installer and '/var/lib/ball-drone/recordings' in installer


def test_connection_card_port_is_validated(tmp_path):
    bin_dir = tmp_path / 'bin'; bin_dir.mkdir()
    (bin_dir / 'nmcli').write_text('#!/bin/sh\ncase "$*" in *IP4.ADDRESS*) echo 192.168.4.1/24 ;; *) echo BallDrone-Demo ;; esac\n')
    (bin_dir / 'fakepython').write_text('#!/bin/sh\necho "$@" > "$CARD_ARGS"\n')
    for f in bin_dir.iterdir(): f.chmod(0o755)
    env = {**os.environ, 'PATH': f'{bin_dir}:{os.environ["PATH"]}', 'BALL_PYTHON': str(bin_dir / 'fakepython'), 'CARD_ARGS': str(tmp_path / 'args')}
    script = str(DEPLOY / 'connection-card.sh')
    assert subprocess.run(['bash', script, str(tmp_path / 'card'), '8083'], env=env, timeout=20).returncode == 0
    assert '--url http://192.168.4.1:8083/' in (tmp_path / 'args').read_text()
    assert subprocess.run(['bash', script, str(tmp_path / 'card')], env=env, timeout=20).returncode == 0
    assert '--url http://192.168.4.1:8080/' in (tmp_path / 'args').read_text()
    bad = subprocess.run(['bash', script, str(tmp_path / 'card'), '80;rm'], env=env, capture_output=True, text=True, timeout=20)
    assert bad.returncode == 1 and 'Port must be a number' in bad.stdout


@pytest.mark.parametrize('script', sorted(p.name for p in DEPLOY.glob('*.sh')))
def test_deploy_scripts_parse(script):
    assert subprocess.run(['bash', '-n', str(DEPLOY / script)]).returncode == 0


# ---------------------------------------------------------------- on-device acceptance (fake Pi tools)
def fake_pi(tmp_path, health='{"ok": true, "state": "MANUAL", "physical_output": false}', active=True, temp="61.2", throttled="0x0",
            groups="uid=989(ball-demo) gid=989(ball-demo) groups=989(ball-demo),20(dialout),44(video)", frames=(100, 700)):
    bin_dir = tmp_path / 'bin'; bin_dir.mkdir(exist_ok=True)
    count = tmp_path / 'count'; count.write_text('0')
    state = '{"frames": %d, "state": "MANUAL", "source_label": "CAMERA", "decision_ms": 12.5, "processing_ms": 4.1}'
    scripts = {
        'systemctl': f'#!/bin/sh\nexit {0 if active else 3}\n',
        'id': f'#!/bin/sh\necho "{groups}"\n',
        'vcgencmd': f'#!/bin/sh\ncase "$1" in measure_temp) echo "temp={temp}\'C";; get_throttled) echo "throttled={throttled}";; esac\n',
        'sleep': '#!/bin/sh\nexit 0\n',
        'curl': ('#!/bin/sh\nfor a in "$@"; do last="$a"; done\n'
                 f'case "$last" in *health) echo \'{health}\';; *fallback) echo "Manual steering — computer steering unavailable";; '
                 f'*state) n=$(cat {count}); echo $((n+1)) > {count}; if [ "$n" = 0 ]; then echo \'{state % frames[0]}\'; else echo \'{state % frames[1]}\'; fi;; esac\n'),
    }
    for name, body in scripts.items():
        (bin_dir / name).write_text(body); (bin_dir / name).chmod(0o755)
    root = fake_root(tmp_path, devices=['video0', 'ttyACM0'])
    return {**os.environ, 'PATH': f'{bin_dir}:{os.environ["PATH"]}', 'BALL_ROOT': str(root), 'BALL_PREFLIGHT_ROOT': str(root),
            'BALL_PREFLIGHT_ARCH': 'aarch64', 'BALL_PREFLIGHT_PYTHON': '3.13'}


def acceptance(tmp_path, env, seconds='30'):
    report = tmp_path / 'report.txt'
    result = subprocess.run(['bash', str(DEPLOY / 'pi-acceptance.sh'), str(report), seconds], env=env, capture_output=True, text=True, timeout=60)
    return result.returncode, report.read_text()


def test_acceptance_passes_on_a_healthy_pi(tmp_path):
    code, text = acceptance(tmp_path, fake_pi(tmp_path))
    assert code == 0 and 'Pi acceptance passed' in text
    assert 'processing 20.0 frames/s' in text and 'CPU 61.2 °C' in text and 'decision_ms 12.5' in text
    assert 'video devices: /dev/video0' in text and 'serial devices: /dev/ttyACM0' in text


@pytest.mark.parametrize('kwargs,message', [
    ({'active': False}, 'service not active'),
    ({'groups': 'uid=989(ball-demo) groups=989(ball-demo)'}, 'service account groups'),
    ({'health': '{"ok": false, "state": "MANUAL", "physical_output": false}'}, 'FAIL  health'),
    ({'health': '{"ok": true, "state": "LOCKED", "physical_output": false}'}, 'FAIL  health'),
])
def test_acceptance_failures(tmp_path, kwargs, message):
    code, text = acceptance(tmp_path, fake_pi(tmp_path, **kwargs))
    assert code == 1 and message in text


def test_acceptance_warns_on_slow_processing_heat_and_throttling(tmp_path):
    code, text = acceptance(tmp_path, fake_pi(tmp_path, temp='81.0', throttled='0x50005', frames=(100, 400)))
    assert code == 0 and 'below the 20 Hz target' in text and 'add cooling' in text and 'get_throttled=0x50005' in text
