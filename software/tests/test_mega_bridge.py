"""Arduino Mega bridge sketch: shared-source integrity, no output pins, host line-framing tests."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FIRMWARE = Path(__file__).resolve().parents[2] / 'firmware'
SKETCH = FIRMWARE / 'mega' / 'ball_bridge_mega'


@pytest.mark.parametrize('name', ['core.c', 'core.h', 'line_reader.c', 'line_reader.h'])
def test_sketch_sources_are_identical_to_the_tested_firmware(name):
    assert (SKETCH / 'src' / name).read_bytes() == (FIRMWARE / name).read_bytes(), \
        f'Copy firmware/{name} to the sketch src/ folder after editing it'


def test_sketch_drives_no_pins_and_sends_only_protocol_replies():
    code = re.sub(r'//.*', '', (SKETCH / 'ball_bridge_mega.ino').read_text())
    for forbidden in ('pinMode', 'digitalWrite', 'analogWrite', 'Servo', 'tone(', 'PORT', 'DDR', 'TCCR', 'OCR'):
        assert forbidden not in code, forbidden
    assert 'Serial.begin(115200)' in code and 'ball_line_feed' in code and 'ball_tick' in code
    assert 'NO TRAINER OUTPUT' in (SKETCH / 'ball_bridge_mega.ino').read_text()


def test_line_reader_and_core_pass_on_the_host(tmp_path):
    compiler = shutil.which('clang') or shutil.which('cc')
    assert compiler, 'Mega bridge host tests require a host C compiler'
    binary = tmp_path / 'line_reader'
    build = subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                            *(str(FIRMWARE / f) for f in ('core.c', 'line_reader.c', 'test_line_reader.c')), '-o', str(binary)],
                           capture_output=True, text=True, timeout=60)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0 and 'LINE READER TESTS PASSED' in run.stdout and 'FAIL' not in run.stdout


def test_forced_failure_build_reports_failure(tmp_path):
    compiler = shutil.which('clang') or shutil.which('cc')
    binary = tmp_path / 'line_reader_fail'
    subprocess.run([compiler, '-std=c11', '-DBALL_FORCE_FAILURE',
                    *(str(FIRMWARE / f) for f in ('core.c', 'line_reader.c', 'test_line_reader.c')), '-o', str(binary)],
                   check=True, timeout=60)
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
    assert run.returncode != 0 and 'forced failure' in run.stdout and 'TESTS FAILED' in run.stdout
