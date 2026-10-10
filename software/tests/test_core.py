import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ball_demo.api import create_app
from ball_demo.config import Settings
from ball_demo.control import Controller
from ball_demo.engine import Engine
from ball_demo.fixtures import trace
from ball_demo.protocol import BridgeCore, parse
from ball_demo.sources import SCENARIOS, OpenCVSource, synthetic
from ball_demo.vision import Detector


@pytest.mark.parametrize('scenario', ['centered', 'moving', 'approach', 'edges', 'loss', 'reappear'])
def test_clear_ground_truth(scenario):
    detector, settings = Detector(), Settings()
    for index in range(160):
        image, truth = synthetic(index, settings, scenario)
        detection = detector.detect(image, settings)
        if truth['visible']:
            assert detection
            assert abs(detection['x'] - truth['x']) <= 5
            assert abs(detection['y'] - truth['y']) <= 5
        else: assert detection is None


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_all_scenarios_bounded(scenario):
    result = trace(scenario, 100)
    for sample in result['samples']:
        assert abs(sample['yaw']) <= result['settings']['max_yaw']
        if sample['state'] != 'LOCKED': assert sample['yaw'] == 0


def test_selection_and_small_blobs():
    settings, detector = Settings(), Detector()
    for i in range(35):
        image, truth = synthetic(i, settings, 'distractions')
        d = detector.detect(image, settings)
        assert abs(d['x'] - truth['x']) <= 5
    image, _ = synthetic(0, settings, 'small')
    assert Detector().detect(image, settings) is None


def test_state_loss_disable_fault_and_slew():
    settings, c = Settings(), Controller()
    d = {'error': 1}
    assert c.frame(d, settings, .05) == 0
    c.enable(True)
    assert c.frame(d, settings, .05) == 0
    assert c.frame(d, settings, .05) == 0
    assert c.frame(d, settings, .05) == 90
    for _ in range(100): c.frame(d, settings, .05)
    assert c.yaw == settings.max_yaw
    c.frame(None, settings, .05)
    assert c.yaw == 0 and c.state == 'SEARCHING'
    c.fail('test')
    assert not c.enabled and c.yaw == 0 and c.state == 'FAULT'
    for _ in range(10): c.frame(d, settings, .05)
    assert c.yaw == 0
    c.enable(False)
    assert c.state == 'MANUAL'


def test_deadband_direction_response():
    c, s = Controller(), Settings(direction=-1)
    c.enable(True)
    for _ in range(20): c.frame({'error': .01}, s, .05)
    assert c.yaw == 0
    for _ in range(20): c.frame({'error': .8}, s, .05)
    assert c.yaw < 0
    result = trace('response', 200)
    assert abs(result['samples'][-1]['detection']['error']) < abs(result['samples'][0]['detection']['error'])


def test_protocol_watchdog_duplicates_invalid_session():
    core = BridgeCore()
    assert core.receive('HELLO 1 session\n', 0) == 'READY 1 session NO_OUTPUT\n'
    core.receive('CMD 1 session 1 1 500\n', .01)
    assert core.yaw == 500
    core.receive('CMD 1 session 1 1 900\n', .2)
    core.receive('CMD 1 wrong 2 1 200\n', .22)
    core.receive('CMD 1 session 2 1 1001\n', .23)
    core.tick(.261)
    assert core.yaw == 0 and not core.enabled
    assert core.fault == 'WATCHDOG'
    core.receive('HELLO 1 next\n', .3)
    assert core.yaw == 0 and core.seq == 0


@pytest.mark.parametrize('line', ['CMD 2 a 1 1 4', 'CMD 1 a 1 0 4', 'CMD 1 a 0 1 4', 'CMD 1 a 1 2 4', 'CMD 1 a 1 1 2.3', 'CMD 1 a 1 1 1001', 'CMD 1 a 1 1 0 EXTRA', 'X' * 129, 'CMD 1 é 1 1 0', 'CMD 1 a 01 1 0', 'CMD 1 a 1 1 -0'])
def test_protocol_rejects(line):
    with pytest.raises(ValueError): parse(line)


def wait_for(engine, condition, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        s = engine.snapshot()
        if condition(s): return s
        time.sleep(.01)
    raise AssertionError(engine.snapshot())


@pytest.mark.parametrize('scenario', ['freeze', 'delay', 'stop'])
def test_live_capture_faults_do_not_block_control(tmp_path, scenario):
    e = Engine(tmp_path, source={'kind': 'synthetic', 'scenario': scenario})
    e.start()
    try:
        wait_for(e, lambda s: s['frames'] > 3)
        e.assist(True)
        wait_for(e, lambda s: s['state'] == 'LOCKED')
        s = wait_for(e, lambda s: s['state'] == 'FAULT')
        assert s['yaw'] == 0 and not s['enabled']
        assert s['frame_age_ms'] <= 350
    finally: e.stop()


@pytest.mark.parametrize('fault', ['disconnect', 'missing_ack', 'delayed_ack'])
def test_bridge_fault_and_recovery(tmp_path, fault):
    e = Engine(tmp_path)
    e.start()
    try:
        wait_for(e, lambda s: s['frames'] > 3)
        e.assist(True)
        wait_for(e, lambda s: s['state'] == 'LOCKED')
        e.inject(fault)
        s = wait_for(e, lambda s: s['state'] == 'FAULT')
        assert s['yaw'] == 0 and not s['enabled']
        assert s['ack_age_ms'] <= 350
        e.inject('none')
        s = wait_for(e, lambda s: s['ack_age_ms'] < 150)
        assert s['state'] == 'MANUAL' and s['yaw'] == 0
    finally: e.stop()


def test_live_loss_first_processed_frame(tmp_path):
    e = Engine(tmp_path, source={'kind': 'synthetic', 'scenario': 'loss'})
    e.start()
    try:
        wait_for(e, lambda s: s['frames'] > 3)
        e.assist(True)
        wait_for(e, lambda s: s['state'] == 'LOCKED')
        s = wait_for(e, lambda s: s['detection'] is None)
        assert s['state'] == 'SEARCHING'
        assert s['yaw'] == 0 and s['detection'] is None
    finally: e.stop()


def test_recorded_eof(tmp_path):
    path = tmp_path / 'clip.avi'
    settings = Settings()
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 20, (640, 480))
    for i in range(20): writer.write(synthetic(i, settings)[0])
    writer.release()
    source = OpenCVSource(str(path), settings, True)
    for _ in range(20): assert source.read() is not None
    assert source.read() is None and source.eof
    source.close()
    e = Engine(tmp_path / 'sessions', source={'kind': 'recorded', 'path': str(path)})
    e.start()
    try:
        wait_for(e, lambda s: s['frames'] > 3)
        e.assist(True)
        wait_for(e, lambda s: s['state'] == 'LOCKED')
        time.sleep(1.1)
        assert e.eof and e.snapshot()['state'] == 'MANUAL' and e.snapshot()['yaw'] == 0
    finally: e.stop()


def test_api_auth_isolation_validation_startup(tmp_path):
    e = Engine(tmp_path)
    with TestClient(create_app(e, 'test-token')) as client:
        assert client.get('/api/health').json()['ok']
        assert client.get('/api/state').json()['state'] == 'MANUAL'
        assert client.post('/api/operator/assist', json={'enabled': True}).status_code == 401
        before = e.source_spec.copy()
        assert client.get('/api/sandbox/loss').status_code == 200
        assert e.source_spec == before and not e.controller.enabled
        auth = {'Authorization': 'Bearer test-token'}
        assert client.post('/api/operator/settings', json={'max_yaw': 1001}, headers=auth).status_code == 422
        assert client.post('/api/operator/settings', json={'hue_low': 90, 'hue_high': 30}, headers=auth).status_code == 422
        assert client.post('/api/operator/source', json={'scenario': 'unknown'}, headers=auth).status_code == 422
        assert client.get('/').status_code == 200
        wait_for(e, lambda s: s['frames'] > 3)
        assert client.post('/api/operator/assist', json={'enabled': True}, headers=auth).status_code == 200
        assert client.post('/api/operator/reset', json={}, headers=auth).json()['state'] == 'MANUAL'
    assert (e.session.path / 'summary.json').exists()


def test_failed_transport_can_disable_shutdown_and_save_summary(tmp_path):
    e = Engine(tmp_path)
    e.start()
    wait_for(e, lambda s: s['frames'] > 3)
    def failed(*args, **kwargs): raise OSError('simulated serial unplug')
    e.bridge.send = failed
    e.bridge.close = failed
    e.assist(False)
    assert e.snapshot()['state'] == 'FAULT' and e.snapshot()['yaw'] == 0
    e.stop()
    assert (e.session.path / 'summary.json').exists()
