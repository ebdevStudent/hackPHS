"""ESP32-S3 bridge sketch: shared-source integrity, baud agreement, serial headroom, PPM host simulation."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ball_demo import bridge as module
from ball_demo.config import Settings

FIRMWARE = Path(__file__).resolve().parents[2] / 'firmware'
SKETCH_DIR = FIRMWARE / 'esp32' / 'ball_bridge_esp32'
SKETCH = SKETCH_DIR / 'ball_bridge_esp32.ino'
LONGEST_SESSION = 'x' * 32  # protocol.SESSION allows 1-32 characters; the host uses uuid4().hex (32)
BITS_PER_BYTE = 10  # 8N1: start + 8 data + stop
MAX_LINK_SHARE = .5  # each direction may use at most half the control period


def sketch_baud():
    code = re.sub(r'//.*', '', SKETCH.read_text())
    match = re.search(r'Serial0?\.begin\((\d+)\)', code)
    assert match, 'ESP32 sketch must open Serial at a literal baud rate'
    return int(match.group(1))


@pytest.mark.parametrize('name', ['core.c', 'core.h', 'line_reader.c', 'line_reader.h'])
def test_sketch_sources_are_identical_to_the_tested_firmware(name):
    assert (SKETCH_DIR / 'src' / name).read_bytes() == (FIRMWARE / name).read_bytes(), \
        f'Copy firmware/{name} to the ESP32 sketch src/ folder after editing it'


def test_sketch_uses_uart0_and_arms_output_only_for_a_ppm_session():
    code = re.sub(r'//.*', '', SKETCH.read_text())
    assert 'Serial0.begin(' in code and not re.search(r'\bSerial\.', code)
    assert 'ball_set_output_mode' in code and 'session_output' in code
    assert 'ppm_update(session_armed, core.enabled, core.yaw)' in code


def test_ppm_generator_passes_the_host_simulation(tmp_path):
    compiler = shutil.which('clang++') or shutil.which('c++')
    assert compiler, 'ESP32 PPM simulation requires a host C++ compiler'
    test = FIRMWARE / 'esp32' / 'test'
    binary = tmp_path / 'ppm_sim'
    build = subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(test / 'stubs'),
                            '-I', str(SKETCH_DIR), str(test / 'test_ppm.cpp'), '-o', str(binary)],
                           capture_output=True, text=True, timeout=120)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and 'PASS' in run.stdout, run.stdout + run.stderr


def test_esp32_sketch_baud_matches_the_host_default():
    assert sketch_baud() == module.DEFAULT_BAUD


def test_host_default_baud_carries_worst_case_frames_at_the_control_rate():
    period_s = 1 / Settings().control_hz
    worst = [f'CMD 1 {LONGEST_SESSION} 4294967295 1 -1000\n',
             f'ACK 1 {LONGEST_SESSION} 4294967295 1 -1000 SEQUENCE\n']
    for frame in worst:
        wire_s = len(frame) * BITS_PER_BYTE / module.DEFAULT_BAUD
        assert wire_s <= MAX_LINK_SHARE * period_s, (frame.split()[0], round(wire_s * 1000, 1))


def test_9600_baud_cannot_carry_the_control_rate():
    """Documents why the ESP32 sketch left 9600: one CMD takes longer than a 50 ms control period."""
    frame = f'CMD 1 {LONGEST_SESSION} 12345 1 -1000\n'
    assert len(frame) * BITS_PER_BYTE / 9600 > 1 / Settings().control_hz
