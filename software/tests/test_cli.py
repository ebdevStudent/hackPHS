import json
import select
import signal
import subprocess
import sys
import time

import cv2
import pytest

from ball_demo import cli
from ball_demo.bridge import SerialBridge
from ball_demo.sources import SCENARIOS


def test_fixture_cli_generates_decodable_video_truth_and_traces(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'fixtures', '--output', str(tmp_path), '--frames', '4'])
    cli.main()
    manifest = json.loads((tmp_path / 'manifest.json').read_text())
    assert manifest['scenarios'] == SCENARIOS and manifest['frames'] == 4
    for name in SCENARIOS:
        assert len(json.loads((tmp_path / f'{name}.json').read_text())['samples']) == 4
        video = cv2.VideoCapture(str(tmp_path / f'{name}.avi'))
        try:
            frames = 0
            while True:
                ok, image = video.read()
                if not ok: break
                assert image.shape == (480, 640, 3); frames += 1
            assert frames == 4
        finally: video.release()
        assert len((tmp_path / f'{name}-truth.csv').read_text().splitlines()) == 5


def test_bridge_check_and_visitor_card_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'bridge-check']); cli.main()
    assert 'WATCHDOG: neutral' in capsys.readouterr().out
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'connection-card', '--url', 'http://127.0.0.1:8080/', '--output', str(tmp_path)])
    cli.main()
    assert (tmp_path / 'visitor-qr.png').read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
    text = (tmp_path / 'visitor.txt').read_text()
    assert 'http://127.0.0.1:8080/' in text and 'Bearer' not in text


@pytest.mark.process
@pytest.mark.parametrize('fault', ['none', 'partial', 'invalid', 'missing_ack', 'delayed_ack', 'disconnect'])
def test_actual_serial_emulator_cli(fault):
    process = subprocess.Popen([sys.executable, '-m', 'ball_demo.serial_emulator', '--fault', fault],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    bridge = None
    try:
        assert select.select([process.stdout], [], [], 5)[0], 'Emulator startup timeout'
        line = process.stdout.readline().strip()
        assert line.startswith('Virtual serial device: ')
        bridge = SerialBridge(line.split(': ', 1)[1])
        deadline = time.monotonic() + 3
        while not bridge.ready and time.monotonic() < deadline:
            bridge.poll(time.monotonic()); time.sleep(.01)
        assert bridge.ready
        before = bridge.last_ack
        bridge.send(True, 350, time.monotonic())
        if fault == 'disconnect':
            process.wait(timeout=3)
            assert process.returncode == 0 and bridge.accepted_yaw == 0
        else:
            deadline = time.monotonic() + .65
            while time.monotonic() < deadline:
                bridge.poll(time.monotonic()); time.sleep(.01)
            if fault in ('none', 'partial'):
                assert bridge.accepted_yaw == 350 and bridge.last_ack > before
            else:
                assert bridge.accepted_yaw == 0 and bridge.last_ack == before
    finally:
        if bridge:
            try: bridge.close()
            except Exception: pass
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
        process.stdout.close(); process.stderr.close()
