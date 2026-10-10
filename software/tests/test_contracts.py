"""Deterministic contracts behind the UI, including every operator write route."""
import json
import random

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ball_demo.api import create_app
from ball_demo.config import Settings
from ball_demo.control import Controller
from ball_demo.engine import Engine
from ball_demo.protocol import BridgeCore

WRITES = [('/api/operator/assist', {'enabled': False}),
          ('/api/operator/source', {'kind': 'synthetic', 'scenario': 'centered'}),
          ('/api/operator/settings', {'gain': 100}),
          ('/api/operator/fault', {'fault': 'disconnect'}),
          ('/api/operator/reset', {})]


@pytest.mark.parametrize('path,body', WRITES)
@pytest.mark.parametrize('authorization', ['', 'Bearer wrong', 'test-token'])
def test_every_operator_route_rejects_missing_or_wrong_auth(tmp_path, path, body, authorization):
    engine = Engine(tmp_path)
    with TestClient(create_app(engine, 'test-token')) as client:
        before = engine.snapshot()
        response = client.post(path, json=body, headers={'Authorization': authorization})
        assert response.status_code == 401
        after = engine.snapshot()
        assert after['source'] == before['source']
        assert after['settings'] == before['settings']
        assert after['bridge_fault'] == before['bridge_fault']
        assert not after['enabled'] and after['yaw'] == 0


@pytest.mark.parametrize('values', [
    {'gain': -1}, {'gain': 2001}, {'smoothing': 0}, {'smoothing': 1.01},
    {'deadband': -.01}, {'deadband': .51}, {'max_yaw': -1}, {'max_yaw': 1001},
    {'slew_per_s': 0}, {'direction': 0}, {'direction': 2}, {'hue_low': -1},
    {'hue_high': 180}, {'saturation_min': 256}, {'value_min': -1},
    {'min_area': 0}, {'max_area': 307201}, {'hue_low': 90, 'hue_high': 80},
    {'min_area': 3000, 'max_area': 2000},
])
def test_invalid_settings_rejected_atomically(tmp_path, values):
    engine = Engine(tmp_path)
    with TestClient(create_app(engine, 'test-token')) as client:
        before = engine.settings.dict()
        response = client.post('/api/operator/settings', json=values,
                               headers={'Authorization': 'Bearer test-token'})
        assert response.status_code == 422
        assert engine.settings.dict() == before


def test_nonfinite_settings_rejected(tmp_path):
    engine = Engine(tmp_path)
    with TestClient(create_app(engine, 'test-token')) as client:
        for value in ['NaN', 'Infinity', '-Infinity']:
            response = client.post('/api/operator/settings', content='{"gain":' + value + '}',
                                   headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'})
            assert response.status_code == 422
        assert engine.settings.gain == Settings().gain


def test_native_preview_is_cached_jpeg_and_no_frame_is_204(tmp_path):
    engine = Engine(tmp_path)
    # Avoid the lifespan here so empty/cache tests have no competing capture thread.
    client = TestClient(create_app(engine, 'test-token'))
    assert client.get('/api/preview.jpg').status_code == 204
    ok, encoded = cv2.imencode('.jpg', np.zeros((480, 640, 3), dtype=np.uint8))
    assert ok
    engine.preview = encoded.tobytes()
    response = client.get('/api/preview.jpg')
    assert response.status_code == 200 and response.content == engine.preview
    assert response.headers['content-type'] == 'image/jpeg'
    assert response.headers['cache-control'] == 'no-store'
    assert cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR).shape == (480, 640, 3)
    engine.session.close(0)


@pytest.mark.parametrize('event', ['loss', 'disable', 'fault'])
def test_neutral_bypasses_even_tiny_slew_limit(event):
    settings = Settings(slew_per_s=1, smoothing=1)
    control = Controller()
    control.enable(True)
    control.yaw, control.filtered = 650, .9
    if event == 'loss': control.frame(None, settings, .001)
    elif event == 'disable': control.enable(False)
    else: control.fail('injected')
    assert control.yaw == control.filtered == control.count == 0
    if event != 'loss': assert not control.enabled


def test_acquisition_must_be_consecutive_after_loss():
    control, settings = Controller(), Settings()
    control.enable(True)
    for _ in range(2): assert control.frame({'error': .8}, settings, .05) == 0
    control.frame(None, settings, .05)
    for _ in range(2):
        assert control.frame({'error': .8}, settings, .05) == 0
        assert control.state == 'SEARCHING'
    assert control.frame({'error': .8}, settings, .05) > 0
    assert control.state == 'LOCKED'


@pytest.mark.parametrize('direction', [-1, 1])
def test_seeded_random_controller_sequences_stay_bounded(direction):
    rng, control = random.Random(20261004), Controller()
    settings = Settings(direction=direction)
    for _ in range(3000):
        operation = rng.randrange(10)
        if operation == 0: control.enable(False)
        elif operation == 1: control.enable(True)
        elif operation == 2: control.fail('injected')
        else: control.frame(None if operation == 3 else {'error': rng.uniform(-1, 1)}, settings, rng.uniform(0, .5))
        assert abs(control.yaw) <= settings.max_yaw
        if not control.enabled or control.state != 'LOCKED': assert control.yaw == 0


def test_duplicate_command_cannot_extend_watchdog_boundary():
    core = BridgeCore(250)
    core.receive('HELLO 1 test\n', 0)
    core.receive('CMD 1 test 1 1 650\n', 0)
    for now in [.1, .2, .249]:
        core.receive('CMD 1 test 1 1 650\n', now)
        assert core.last_valid == 0
    core.tick(.25)
    assert not core.enabled and core.yaw == 0 and core.fault == 'WATCHDOG'


def test_source_settings_and_reset_disable_active_assistance(tmp_path):
    engine = Engine(tmp_path)
    with TestClient(create_app(engine, 'test-token')) as client:
        auth = {'Authorization': 'Bearer test-token'}
        for path, values in WRITES[1:3] + [WRITES[-1]]:
            # Explicitly seed controller output; test mutations rather than acquisition timing.
            with engine.lock:
                engine.controller.enable(True)
                engine.controller.yaw = 350
            response = client.post(path, json=values, headers=auth)
            assert response.status_code == 200
            result = response.json()
            assert result['state'] == 'MANUAL' and not result['enabled'] and result['yaw'] == 0
    events = [json.loads(line) for line in (engine.session.path / 'events.jsonl').read_text().splitlines()]
    assert any(event['type'] == 'settings' for event in events)
    assert events[-1]['type'] == 'shutdown' and events[-1]['data']['yaw'] == 0
