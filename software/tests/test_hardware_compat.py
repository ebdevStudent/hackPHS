"""Audit fixes: capture-mode read-back, synthetic fallback flagging, DTR/RTS-safe serial open. No real devices."""
import argparse
import logging

import cv2
import numpy as np
import pytest

from ball_demo import bridge as bridge_module
from ball_demo import cli
from ball_demo.bridge import SerialBridge
from ball_demo.config import Settings
from ball_demo.engine import Engine
from ball_demo.sources import OpenCVSource

YUYV = cv2.VideoWriter_fourcc(*'YUYV')
MJPG = cv2.VideoWriter_fourcc(*'MJPG')


class Camera:
    def __init__(self, width=720, height=480, fps=30., fourcc=YUYV):
        self.props = {cv2.CAP_PROP_FRAME_WIDTH: width, cv2.CAP_PROP_FRAME_HEIGHT: height,
                      cv2.CAP_PROP_FPS: fps, cv2.CAP_PROP_FOURCC: fourcc}
        self.released = False
    def isOpened(self): return True
    def set(self, key, value): return True
    def get(self, key): return self.props.get(key, 0)
    def read(self): return True, np.zeros((480, 720, 3), np.uint8)
    def release(self): self.released = True


def open_source(monkeypatch, camera):
    monkeypatch.setattr(cv2, 'VideoCapture', lambda identifier, *a: camera)
    return OpenCVSource('/dev/video0', Settings(), backend='v4l2')


def test_default_capture_mode_is_ntsc_yuyv():
    settings = Settings()
    assert (settings.capture_width, settings.capture_height, settings.capture_fps, settings.capture_fourcc) == (720, 480, 30, 'YUYV')


def test_matching_mode_is_read_back_and_logged(monkeypatch, caplog):
    caplog.set_level(logging.INFO, 'ball_demo.sources')
    source = open_source(monkeypatch, Camera())
    assert source.mode == {'width': 720, 'height': 480, 'fps': 30., 'fourcc': 'YUYV'}
    assert 'capture opened: 720x480 @ 30.00 fps YUYV' in caplog.text


@pytest.mark.parametrize('camera', [Camera(width=640, height=480), Camera(width=720, height=576, fps=25.), Camera(fourcc=MJPG)])
def test_size_or_format_mismatch_fails_and_releases_the_device(monkeypatch, camera):
    with pytest.raises(ValueError, match='Capture mode mismatch: requested 720x480 YUYV'):
        open_source(monkeypatch, camera)
    assert camera.released


def test_fps_mismatch_warns_but_still_opens(monkeypatch, caplog):
    open_source(monkeypatch, Camera(fps=10.))
    assert 'CAPTURE FPS MISMATCH' in caplog.text


def test_ntsc_29_97_and_unreported_fps_are_not_mismatches(monkeypatch, caplog):
    open_source(monkeypatch, Camera(fps=29.97)); open_source(monkeypatch, Camera(fps=0.))
    assert 'MISMATCH' not in caplog.text


def test_capture_mode_is_configurable(monkeypatch):
    monkeypatch.setattr(cv2, 'VideoCapture', lambda identifier, *a: Camera(720, 576, 25.))
    settings = Settings(capture_width=720, capture_height=576, capture_fps=25)
    assert OpenCVSource(0, settings).mode['height'] == 576


def test_cli_capture_mode_parsing():
    assert cli.capture_mode('720x576@25') == (720, 576, 25.)
    with pytest.raises(argparse.ArgumentTypeError): cli.capture_mode('720x480')


def namespace(**values):
    return argparse.Namespace(**{'portable_demo': False, 'camera': None, 'recorded': None, 'serial': None, **values})


def test_startup_warnings_name_every_fallback():
    both = cli.startup_warnings(namespace())
    assert any('NO CAMERA' in w and 'SYNTHETIC' in w for w in both) and any('NO SERIAL' in w for w in both)
    assert cli.startup_warnings(namespace(camera='/dev/video0', serial='/dev/ttyACM0')) == []
    assert [w for w in cli.startup_warnings(namespace(camera='0')) if 'CAMERA' in w] == []
    assert cli.startup_warnings(namespace(portable_demo=True)) == []


def test_default_engine_is_flagged_synthetic_fallback_and_explicit_synthetic_is_not(tmp_path):
    engine = Engine(tmp_path / 'a')
    state = engine.snapshot()
    assert state['synthetic_fallback'] is True and state['mock_bridge'] is True
    engine.set_source({'kind': 'synthetic', 'scenario': 'moving'})
    assert engine.snapshot()['synthetic_fallback'] is False
    configured = Engine(tmp_path / 'b', source={'kind': 'camera', 'device': 0})
    assert configured.snapshot()['synthetic_fallback'] is False
    engine.session.close(0); configured.session.close(0)


def test_fallback_banner_is_drawn_on_preview_frames(tmp_path):
    import time
    engine = Engine(tmp_path / 'c')
    engine.start()
    try:
        deadline = time.monotonic() + 5
        while engine.preview is None and time.monotonic() < deadline: time.sleep(.05)
        image = cv2.imdecode(np.frombuffer(engine.preview, np.uint8), cv2.IMREAD_COLOR)
        banner = image[-30:, :].reshape(-1, 3).mean(axis=0)  # BGR; the banner bar is red
        assert banner[2] > 120 and banner[0] < 80
    finally:
        engine.stop()


class RecordingSerial:
    events = []
    def __init__(self, port=None, baudrate=9600, **kwargs):
        RecordingSerial.events.append(('init', port))
        self._dtr = self._rts = True   # pyserial default: asserted
    def __setattr__(self, name, value):
        if name in ('dtr', 'rts', 'port'): RecordingSerial.events.append((name, value))
        object.__setattr__(self, name, value)
    def open(self): RecordingSerial.events.append(('open', self.dtr, self.rts, self.port))
    def write(self, data): return len(data)
    def close(self): pass


def test_bridge_deasserts_dtr_rts_before_opening_the_port(monkeypatch):
    RecordingSerial.events = []
    monkeypatch.setattr(bridge_module.serial, 'Serial', RecordingSerial)
    SerialBridge('/dev/ttyACM0').close()
    events = RecordingSerial.events
    assert events[0] == ('init', None)
    assert events.index(('dtr', False)) < events.index(('port', '/dev/ttyACM0')) < [e[0] for e in events].index('open')
    assert events.index(('rts', False)) < events.index(('port', '/dev/ttyACM0'))
    assert events[-1] == ('open', False, False, '/dev/ttyACM0')


def test_service_passes_real_camera_and_serial_arguments():
    from pathlib import Path
    service = (Path(cli.__file__).parents[1] / 'deploy' / 'ball-demo.service').read_text()
    exec_line = next(line for line in service.splitlines() if line.startswith('ExecStart='))
    for argument in ('--camera /dev/video0', '--camera-backend v4l2', '--capture-mode 720x480@30', '--serial /dev/serial/by-id/'):
        assert argument in exec_line
