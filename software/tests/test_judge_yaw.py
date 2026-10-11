"""Judge yaw slider: PIN-gated, yaw-only, operator-enabled, leased, and neutral on every failure."""
import time

import pytest
from fastapi.testclient import TestClient

from ball_demo import engine as engine_module
from ball_demo.api import create_app
from ball_demo.engine import JUDGE_LEASE_S, Engine


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv('BALL_JUDGE_PIN', '4321')
    engine = Engine(tmp_path)
    client = TestClient(create_app(engine, 'op-token'))
    yield client, engine, {'Authorization': 'Bearer op-token'}
    client.close(); engine.stop()


def wait_for(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate(): return True
        time.sleep(.02)
    return False


def test_judge_page_and_public_status_never_reveal_the_pin(api):
    client, engine, _ = api
    assert client.get('/judge').status_code == 200
    status = client.get('/api/judge/status').json()
    assert status == {'active': False, 'yaw': 0, 'max_yaw': 300, 'lease_ms': int(JUDGE_LEASE_S * 1000)}
    assert '4321' not in client.get('/api/state').text and '4321' not in client.get('/judge').text


def test_only_the_operator_can_turn_judge_mode_on_and_see_the_pin(api):
    client, engine, auth = api
    assert client.get('/api/operator/judge').status_code == 401
    assert client.post('/api/operator/judge', json={'enabled': True}).status_code == 401
    assert client.post('/api/operator/judge', json={'enabled': True}, headers={'Authorization': 'Bearer 4321'}).status_code == 401
    reply = client.post('/api/operator/judge', json={'enabled': True, 'max_yaw': 200}, headers=auth)
    assert reply.status_code == 200 and reply.json()['pin'] == '4321' and reply.json()['active']
    assert engine.judge['max_yaw'] == 200
    for bad in [{'enabled': 'yes'}, {'enabled': 1}, {'enabled': True, 'max_yaw': 1001}, {'enabled': True, 'extra': 1}]:
        assert client.post('/api/operator/judge', json=bad, headers=auth).status_code == 422


def test_judge_yaw_requires_pin_and_active_mode_and_is_clamped_to_the_limit(api):
    client, engine, auth = api
    assert client.post('/api/judge/yaw', json={'pin': '4321', 'yaw_pct': 50}).status_code == 409   # mode off
    client.post('/api/operator/judge', json={'enabled': True, 'max_yaw': 200}, headers=auth)
    assert client.post('/api/judge/yaw', json={'pin': '0000', 'yaw_pct': 50}).status_code == 403
    assert client.post('/api/judge/yaw', json={'pin': 'op-token', 'yaw_pct': 50}).status_code == 403
    reply = client.post('/api/judge/yaw', json={'pin': '4321', 'yaw_pct': 50})
    assert reply.status_code == 200 and reply.json()['yaw'] == 100
    assert client.post('/api/judge/yaw', json={'pin': '4321', 'yaw_pct': -100}).json()['yaw'] == -200
    for bad in [{'pin': '4321', 'yaw_pct': 101}, {'pin': '4321', 'yaw_pct': '50'}, {'pin': '4321', 'yaw_pct': 50.5},
                {'pin': '4321', 'yaw_pct': True}, {'pin': '4321', 'yaw_pct': 5, 'gain': 9}]:
        assert client.post('/api/judge/yaw', json=bad).status_code == 422


def test_judges_cannot_change_anything_else(api):
    client, engine, _ = api
    judge = {'Authorization': 'Bearer 4321'}
    for path, body in [('/api/operator/settings', {'gain': 1}), ('/api/operator/assist', {'enabled': True}),
                       ('/api/operator/source', {'kind': 'synthetic'}), ('/api/operator/roster/reload', None)]:
        assert client.post(path, json=body, headers=judge).status_code == 401


def test_wrong_pin_lockout(api):
    client, engine, auth = api
    client.post('/api/operator/judge', json={'enabled': True}, headers=auth)
    codes = [client.post('/api/judge/yaw', json={'pin': '9999', 'yaw_pct': 10}).status_code for _ in range(21)]
    assert codes[:20] == [403] * 20 and codes[20] == 429
    assert client.post('/api/judge/yaw', json={'pin': '4321', 'yaw_pct': 10}).status_code == 429


def test_lease_expiry_sends_zero_and_turning_off_sends_neutral(api):
    client, engine, auth = api
    client.post('/api/operator/judge', json={'enabled': True, 'max_yaw': 300}, headers=auth)
    engine.judge_command('4321', 100)
    now = time.monotonic()
    with engine.lock:
        engine.bridge.last_ack = now
        assert engine.judge_output(now) == 300
        engine.bridge.last_ack = now + JUDGE_LEASE_S          # bridge still answering; only the judge went quiet
        assert engine.judge_output(now + JUDGE_LEASE_S + .01) == 0
    assert engine.judge_snapshot(now + JUDGE_LEASE_S + .01)['yaw'] == 0
    engine.set_judge_mode(False)
    with engine.lock:
        assert engine.judge_output(time.monotonic()) is None


def test_bridge_fault_turns_judge_mode_off_and_blocks_enabling(api):
    client, engine, auth = api
    client.post('/api/operator/judge', json={'enabled': True}, headers=auth)
    engine.judge_command('4321', 100)
    engine.bridge.fault = 'disconnect'
    with engine.lock:
        assert engine.judge_output(time.monotonic()) is None
    assert not engine.judge['active']
    reply = client.post('/api/operator/judge', json={'enabled': True}, headers=auth)
    assert reply.status_code == 409 and 'bridge' in reply.json()['detail']


def test_vision_assist_and_judge_mode_are_mutually_exclusive(api):
    client, engine, auth = api
    from ball_demo.sources import Frame
    now = engine_module.time.monotonic()
    engine.frame = Frame(None, now, 1, {}); engine.bridge.last_ack = now
    engine.assist(True)
    engine.set_judge_mode(True)
    assert engine.judge['active'] and not engine.controller.enabled
    engine.frame = Frame(None, engine_module.time.monotonic(), 2, {}); engine.bridge.last_ack = engine_module.time.monotonic()
    engine.assist(True)
    assert engine.controller.enabled and not engine.judge['active']


def test_running_engine_sends_judge_yaw_to_the_bridge_and_zero_after_release(tmp_path, monkeypatch):
    monkeypatch.setenv('BALL_JUDGE_PIN', '4321')
    engine = Engine(tmp_path)
    engine.start()
    try:
        assert wait_for(lambda: engine.judge_blocked(time.monotonic()) is None)
        engine.set_judge_mode(True, 400)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and engine.bridge.accepted_yaw != 200:
            engine.judge_command('4321', 50)          # judge holds the slider at +50 %
            time.sleep(.05)
        assert engine.bridge.accepted_yaw == 200
        assert wait_for(lambda: engine.bridge.accepted_yaw == 0, JUDGE_LEASE_S + 1)   # page closed / released
        assert engine.snapshot()['judge']['active'] and engine.snapshot()['yaw'] == 0
    finally:
        engine.stop()
    assert not engine.judge['active']
