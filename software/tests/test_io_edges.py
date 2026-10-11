"""Failures at software IO boundaries; all camera and serial devices are doubles."""
import asyncio
import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ball_demo import api, cli, engine as engine_module
from ball_demo.api import create_app
from ball_demo.bridge import MockBridge, SerialBridge
from ball_demo.config import Settings
from ball_demo.engine import Engine
from ball_demo.sources import OpenCVSource, synthetic
from ball_demo.vision import Detector
from test_core import wait_for


class Camera:
    def __init__(self, opened=True): self.opened, self.released, self.properties, self.reads = opened, False, [], 0
    def isOpened(self): return self.opened
    def set(self, key, value): self.properties.append((key, value)); return True
    def get(self, key):
        return {cv2.CAP_PROP_FOURCC: cv2.VideoWriter_fourcc(*'YUYV'), cv2.CAP_PROP_FRAME_WIDTH: 720,
                cv2.CAP_PROP_FRAME_HEIGHT: 480, cv2.CAP_PROP_FPS: 30}.get(key, 0)
    def read(self):
        self.reads += 1
        return (True, np.zeros((240, 320, 3), dtype=np.uint8)) if self.reads == 1 else (False, None)
    def release(self): self.released = True


def test_camera_adapter_requests_dimensions_and_does_not_call_loss_eof(monkeypatch):
    device = Camera(); monkeypatch.setattr(cv2, 'VideoCapture', lambda identifier: device)
    source = OpenCVSource(2, Settings(), recorded=False)
    assert device.properties == [(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV')), (cv2.CAP_PROP_FRAME_WIDTH, 720),
                                 (cv2.CAP_PROP_FRAME_HEIGHT, 480), (cv2.CAP_PROP_FPS, 30), (cv2.CAP_PROP_BUFFERSIZE, 1)]
    assert source.read().image.shape == (480, 640, 3)
    assert source.read() is None and not source.eof
    source.close(); assert device.released


def test_failed_camera_open_releases_adapter(monkeypatch):
    device = Camera(False); monkeypatch.setattr(cv2, 'VideoCapture', lambda identifier: device)
    with pytest.raises(ValueError, match='Cannot open'): OpenCVSource(0, Settings())
    assert device.released


@pytest.mark.parametrize('failure', ['open', 'read'])
def test_source_adapter_failure_faults_and_refuses_enable(tmp_path, monkeypatch, failure):
    closes = []
    class BrokenSource:
        label = 'CAMERA'
        def __init__(self, *args):
            if failure == 'open': raise OSError('mock device absent')
        def read(self): raise OSError('mock capture disconnected')
        def close(self): closes.append(True)
    monkeypatch.setattr(engine_module, 'OpenCVSource', BrokenSource)
    engine = Engine(tmp_path, source={'kind': 'camera', 'device': 0})
    engine.start()
    try:
        status = wait_for(engine, lambda s: s['state'] == 'FAULT')
        assert status['yaw'] == 0 and not status['enabled'] and status['fault'].startswith('source:')
        with pytest.raises(ValueError): engine.assist(True)
    finally: engine.stop()
    assert (engine.session.path / 'summary.json').exists()
    if failure == 'read': assert closes


@pytest.mark.parametrize('outcome', ['old_frame', 'old_error'])
def test_switch_source_ignores_late_old_generation(tmp_path, monkeypatch, outcome):
    entered, release = threading.Event(), threading.Event()
    class BlockingSource:
        label = 'CAMERA'
        def __init__(self, *args): pass
        def read(self):
            entered.set(); assert release.wait(3)
            if outcome == 'old_error': raise OSError('previous source failed late')
            from ball_demo.sources import Frame
            return Frame(synthetic(0, Settings())[0], time.monotonic(), 999, {})
        def close(self): pass
    monkeypatch.setattr(engine_module, 'OpenCVSource', BlockingSource)
    engine = Engine(tmp_path, source={'kind': 'camera', 'device': 0})
    engine.start()
    try:
        assert entered.wait(2)
        engine.set_source({'kind': 'synthetic', 'scenario': 'centered'})
        release.set()
        status = wait_for(engine, lambda s: s['frames'] >= 4)
        assert engine.source_error is None and status['state'] == 'MANUAL' and status['yaw'] == 0
        assert engine.frame.index != 999
    finally: release.set(); engine.stop()


def test_bridge_poll_exception_neutralizes_and_is_logged(tmp_path, monkeypatch):
    engine = Engine(tmp_path); engine.start()
    try:
        wait_for(engine, lambda s: s['frames'] > 3)
        engine.assist(True); wait_for(engine, lambda s: s['state'] == 'LOCKED')
        def broken(now): raise OSError('mock poll unplug')
        monkeypatch.setattr(engine.bridge, 'poll', broken)
        status = wait_for(engine, lambda s: s['state'] == 'FAULT')
        assert not status['enabled'] and status['yaw'] == 0
    finally: engine.stop()
    events = [json.loads(line) for line in (engine.session.path / 'events.jsonl').read_text().splitlines()]
    assert any(event['type'] == 'fault' and 'mock poll unplug' in event['data']['reason'] for event in events)


def test_mock_bridge_injection_is_rejected_for_nonmock_transport(tmp_path):
    bridge = SimpleNamespace(transport='TEST', accepted_yaw=0, seq=0, last_ack=time.monotonic(), fault='none',
                             send=lambda *args: None, close=lambda: None)
    engine = Engine(tmp_path, bridge=bridge)
    try:
        with TestClient(create_app(engine, 'token')) as client:
            auth = {'Authorization': 'Bearer token'}
            response = client.post('/api/operator/fault', json={'fault': 'disconnect'}, headers=auth)
            assert response.status_code == 409 and 'mock bridge only' in response.json()['detail']
            assert client.post('/api/operator/reset', json={}, headers=auth).json()['state'] == 'MANUAL'
    finally:
        if not (engine.session.path / 'summary.json').exists(): engine.stop()


def test_source_and_fault_validation_are_structured(tmp_path):
    engine = Engine(tmp_path); app = create_app(engine, 'token')
    try:
        with TestClient(app) as client:
            auth = {'Authorization': 'Bearer token'}
            for body in [{'kind': 'file'}, {'kind': 'recorded'}, {'kind': 'recorded', 'path': str(tmp_path/'missing.avi')}]:
                response = client.post('/api/operator/source', json=body, headers=auth)
                assert response.status_code == 422 and response.json()['detail']
            assert client.post('/api/operator/fault', json={'fault': 'unknown'}, headers=auth).status_code == 422
            assert client.get('/api/scenarios').json()
            assert client.get('/api/sandbox/unknown').status_code == 404
            first = client.get('/api/sandbox/centered').json()
            assert first == client.get('/api/sandbox/centered').json()
    finally:
        if not (engine.session.path / 'summary.json').exists(): engine.stop()


def test_sse_and_mjpeg_stream_current_data_and_stop_without_backlog(tmp_path, monkeypatch):
    engine = Engine(tmp_path); app = create_app(engine, 'token')
    async def exercise():
        async def noop(seconds): pass
        monkeypatch.setattr(api.asyncio, 'sleep', noop)
        engine.running = True
        endpoint = next(r.endpoint for r in app.routes if getattr(r, 'path', '') == '/api/events')
        response = await endpoint(); stream = response.body_iterator
        event = await anext(stream)
        assert event.startswith('data: ') and json.loads(event[6:].strip())['yaw'] == 0
        engine.running = False
        with pytest.raises(StopAsyncIteration): await anext(stream)
        engine.preview, engine.preview_index, engine.running = b'jpeg-one', 1, True
        endpoint = next(r.endpoint for r in app.routes if getattr(r, 'path', '') == '/api/preview')
        response = await endpoint(); stream = response.body_iterator
        one = await anext(stream)
        assert b'Content-Length: 8\r\n\r\njpeg-one\r\n' in one
        ticks = []
        async def change_frame(seconds):
            ticks.append(seconds)
            if len(ticks) == 2: engine.preview, engine.preview_index = b'jpeg-two', 2
        monkeypatch.setattr(api.asyncio, 'sleep', change_frame)
        two = await anext(stream)
        assert two.endswith(b'jpeg-two\r\n') and len(ticks) == 2  # duplicate frame dropped
        engine.running = False
        with pytest.raises(StopAsyncIteration): await anext(stream)
    try: asyncio.run(exercise())
    finally: engine.stop()


def test_detector_reacquires_after_far_target_and_rejects_degenerate_contour(monkeypatch):
    settings, detector = Settings(), Detector()
    image, _ = synthetic(0, settings, 'centered'); first = detector.detect(image, settings)
    image, _ = synthetic(120, settings, 'reappear'); second = detector.detect(image, settings)
    assert abs(second['x'] - first['x']) > settings.width * .2
    monkeypatch.setattr(cv2, 'moments', lambda contour: {'m00': 0})
    assert Detector().detect(image, settings) is None


@pytest.mark.parametrize('recorded,serial_device,trainer', [
    (False, False, False), (True, False, False), (False, True, False), (False, True, True)])
def test_serve_cli_wiring_private_token_and_exit_neutral(tmp_path, monkeypatch, recorded, serial_device, trainer):
    values = []; servers = []
    monkeypatch.setenv('BALL_OPERATOR_TOKEN', 'known-token')
    monkeypatch.setattr(cli, 'SerialBridge', lambda identifier, **options: values.append((identifier, options)) or SimpleNamespace(transport='TEST'))
    class DemoEngine:
        def __init__(self, data, bridge=None, source=None, **navigation):
            self.data, self.bridge, self.source, self.running, self.disabled = data, bridge, source, True, False
        def assist(self, value): self.disabled = not value
    monkeypatch.setattr(cli, 'Engine', DemoEngine)
    monkeypatch.setattr(cli, 'create_app', lambda engine, token: (engine, token))
    class Server:
        def __init__(self, config): self.config = config; servers.append(self)
        def handle_exit(self, sig, frame): self.exited = True
        def run(self): self.handle_exit(2, None)
    monkeypatch.setattr(cli.uvicorn, 'Server', Server)
    monkeypatch.setattr(cli.uvicorn, 'Config', lambda app, **kwargs: SimpleNamespace(app=app, **kwargs))
    args = ['ball-demo', 'serve', '--data', str(tmp_path), '--host', '127.0.0.1', '--port', '8181']
    if recorded: args += ['--recorded', '/mock/input.avi']
    if serial_device: args += ['--serial', 'virtual-only']
    if trainer: args += ['--trainer-output']
    monkeypatch.setattr(sys, 'argv', args); cli.main()
    server = servers[0]; engine, token = server.config.app
    assert engine.disabled and not engine.running and server.exited and token == 'known-token'
    assert server.config.host == '127.0.0.1' and server.config.port == 8181
    assert engine.source == ({'kind': 'recorded', 'path': '/mock/input.avi'} if recorded else None)
    options = {'baud': 115200, 'trainer_output': trainer}
    assert values == ([('virtual-only', options)] if serial_device else [])
    path = tmp_path / 'operator-token'
    assert path.read_text().strip() == 'known-token' and path.stat().st_mode & 0o777 == 0o600


def test_trainer_output_without_serial_device_is_cli_error(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, 'SerialBridge', lambda *args, **kwargs: pytest.fail('bridge opened'))
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'serve', '--data', str(tmp_path), '--trainer-output'])
    with pytest.raises(SystemExit) as error: cli.main()
    assert error.value.code == 2 and not (tmp_path / 'operator-token').exists()


def test_invalid_connection_card_scheme_is_cli_error(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'connection-card', '--url', 'file:///tmp/private', '--output', str(tmp_path/'card')])
    with pytest.raises(SystemExit) as error: cli.main()
    assert error.value.code == 2 and not (tmp_path/'card').exists()


def test_assistance_enable_without_fresh_frame_returns_conflict(tmp_path, monkeypatch):
    engine = Engine(tmp_path)
    monkeypatch.setattr(engine, 'start', lambda: setattr(engine, 'running', True))
    with TestClient(create_app(engine, 'token')) as client:
        response = client.post('/api/operator/assist', json={'enabled': True}, headers={'Authorization': 'Bearer token'})
        assert response.status_code == 409 and 'Resolve' in response.json()['detail']
        assert engine.snapshot()['yaw'] == 0 and not engine.controller.enabled


@pytest.mark.parametrize('outcome', ['frame', 'error', 'eof'])
def test_shutdown_during_blocked_capture_closes_without_late_samples(tmp_path, monkeypatch, outcome):
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()
    class BlockingSource:
        label = 'CAMERA'
        eof = False
        def __init__(self, *args): pass
        def read(self):
            entered.set(); assert release.wait(3)
            if outcome == 'error': raise OSError('late shutdown read failure')
            if outcome == 'eof': self.eof = True; return None
            from ball_demo.sources import Frame
            return Frame(synthetic(0, Settings())[0], time.monotonic(), 0, {})
        def close(self): closed.set()
    monkeypatch.setattr(engine_module, 'OpenCVSource', BlockingSource)
    engine = Engine(tmp_path, source={'kind': 'camera', 'device': 0}); engine.start()
    errors = []
    def stop():
        try: engine.stop()
        except Exception as error: errors.append(error)
    stopper = threading.Thread(target=stop)
    try:
        assert entered.wait(2); stopper.start()
        wait_for(engine, lambda snapshot: not engine.running)
        release.set(); stopper.join(3)
        assert not stopper.is_alive() and not errors and closed.is_set()
        summary = json.loads((engine.session.path/'summary.json').read_text())
        assert summary['frames'] == 0 and summary['physical_output'] is False
        events = [json.loads(line) for line in (engine.session.path/'events.jsonl').read_text().splitlines()]
        assert events[-1]['type'] == 'shutdown' and not any(e['type'] == 'eof' for e in events)
        assert engine.snapshot()['yaw'] == 0 and not engine.controller.enabled
    finally:
        release.set()
        if stopper.ident is not None: stopper.join(3)
        elif engine.running: engine.stop()


@pytest.mark.parametrize('outcome', ['open_error', 'eof'])
def test_late_source_open_error_or_eof_cannot_affect_replacement(tmp_path, monkeypatch, outcome):
    entered, release = threading.Event(), threading.Event()
    class LateSource:
        label = 'RECORDED'
        eof = True
        def __init__(self, *args):
            if outcome == 'open_error':
                entered.set(); assert release.wait(3); raise OSError('old opener failed late')
        def read(self): entered.set(); assert release.wait(3); return None
        def close(self): pass
    monkeypatch.setattr(engine_module, 'OpenCVSource', LateSource)
    engine = Engine(tmp_path, source={'kind': 'recorded', 'path': 'fake-only'})
    engine.start()
    try:
        assert entered.wait(2)
        engine.set_source({'kind': 'synthetic', 'scenario': 'centered'}); release.set()
        status = wait_for(engine, lambda s: s['frames'] >= 3)
        assert not engine.eof and engine.source_error is None
        assert status['state'] == 'MANUAL' and status['yaw'] == 0
    finally: release.set(); engine.stop()
