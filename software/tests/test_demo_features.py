"""Manual-fallback status, live-picture checks, operator lease, colour picking, camera CLI and latency tool."""
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ball_demo import cli, color_pick, engine as engine_module, latency
from ball_demo.api import create_app
from ball_demo.bridge import HELLO_RETRY_S, RESYNC_S, MockBridge, SerialBridge
from ball_demo.config import Settings
from ball_demo.engine import BRIDGE_READY_S, STEERING_UNAVAILABLE, Engine
from ball_demo.sources import Frame, OpenCVSource, synthetic
from ball_demo.video_health import BLANK_CONTRAST, FROZEN_DIFFERENCE, VideoHealth
from ball_demo.vision import Detector

AUTH = {'Authorization': 'Bearer token'}
STATIC = Path(__file__).resolve().parents[1] / 'ball_demo' / 'static'


def wait_for(condition, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition(): return
        time.sleep(.01)
    raise AssertionError('condition did not become true')


def noisy(seed, size=(480, 640)):
    rng = np.random.default_rng(seed)
    return rng.integers(30, 220, (*size, 3), dtype=np.uint8)


# ---------------------------------------------------------------- picture health
def test_identical_frames_become_frozen_only_after_the_limit():
    health, image = VideoHealth(), noisy(1)
    health.update(image, 0.0)
    assert health.report(0.0)['difference'] is None and health.issue(0.0, 500) is None
    health.update(image.copy(), .1)
    assert health.frozen_since == .1 and health.issue(.599, 500) is None
    health.update(image.copy(), .6)
    assert health.issue(.6, 500) == 'frozen video'
    assert health.report(.6)['frozen_ms'] == 500.0


def test_changing_picture_clears_frozen_state():
    health = VideoHealth()
    image = noisy(2)
    for t in (0, .1, .2): health.update(image, t)
    health.update(noisy(3), .3)
    assert health.frozen_since is None and health.issue(5, 500) is None
    assert health.report(.3)['difference'] > FROZEN_DIFFERENCE


@pytest.mark.parametrize('colour', [(0, 0, 0), (200, 40, 10), (128, 128, 128)])
def test_uniform_screen_is_reported_as_no_signal(colour):
    health = VideoHealth()
    image = np.full((480, 640, 3), colour, np.uint8)
    health.update(image, 0)
    health.update(image, .5)
    assert health.contrast < BLANK_CONTRAST
    assert health.issue(.5, 500) == 'no video signal (blank picture)'   # blank is reported before frozen


def test_live_noise_and_greyscale_input_have_no_issue():
    health = VideoHealth()
    for index in range(10):
        health.update(noisy(index)[:, :, 0], index * .05)
    assert health.issue(10, 1) is None and health.report(1)['blank_ms'] is None


@pytest.mark.parametrize('sigma', [1.0, 1.5, 6.0])
def test_small_sensor_noise_on_a_static_scene_is_not_frozen(sigma):
    base = noisy(7).astype(np.float64)
    health = VideoHealth()
    rng = np.random.default_rng(8)
    for index in range(6):
        image = np.clip(np.rint(base + rng.normal(0, sigma, base.shape)), 0, 255).astype(np.uint8)
        health.update(image, index * .1)
    assert health.issue(1, 100) is None and health.difference > FROZEN_DIFFERENCE


def test_repeated_jpeg_encoded_buffer_is_frozen():
    encoded = cv2.imencode('.jpg', noisy(9))[1]
    health = VideoHealth()
    for index in range(5):
        health.update(cv2.imdecode(encoded, cv2.IMREAD_COLOR), index * .2)
    assert health.difference == 0 and health.issue(.8, 500) == 'frozen video'


class FakeCamera:
    """OpenCVSource stand-in. mode: 'frozen' repeats one picture, 'live' changes every frame, 'blank' is uniform."""
    def __init__(self, mode, settings):
        self.mode, self.settings, self.index, self.label, self.eof = mode, settings, 0, 'CAMERA', False
        self.image = synthetic(0, settings, 'centered')[0]
    def read(self):
        time.sleep(1 / 40)
        self.index += 1
        if self.mode == 'blank': image = np.zeros_like(self.image)
        elif self.mode == 'frozen': image = self.image.copy()
        else:   # a live camera: moving target plus per-pixel sensor noise
            noise = np.random.default_rng(self.index).normal(0, 2, self.image.shape)
            image = np.clip(synthetic(self.index, self.settings, 'moving')[0] + noise, 0, 255).astype(np.uint8)
        return Frame(image, time.monotonic(), self.index, {})
    def close(self): pass


def camera_engine(tmp_path, monkeypatch, mode, kind='camera'):
    created = []
    def source(identifier, settings, recorded=False, backend=None, paced=False):
        created.append((identifier, recorded, backend, paced))
        return FakeCamera(mode, settings)
    monkeypatch.setattr(engine_module, 'OpenCVSource', source)
    spec = {'kind': kind, 'device': 0} if kind == 'camera' else {'kind': 'recorded', 'path': 'clip.avi'}
    engine = Engine(tmp_path, source=spec)
    return engine, created


@pytest.mark.parametrize('mode,reason', [('frozen', 'source: frozen video'), ('blank', 'source: no video signal (blank picture)')])
def test_frozen_or_blank_live_camera_faults_and_refuses_enable(tmp_path, monkeypatch, mode, reason):
    engine, created = camera_engine(tmp_path, monkeypatch, mode)
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['fault'] == reason)
        state = engine.snapshot()
        assert state['state'] == 'FAULT' and not state['enabled'] and state['yaw'] == 0
        assert state['video_health'] is not None
        with pytest.raises(ValueError):
            engine.assist(True)
        assert created == [(0, False, None, False)]
    finally:
        engine.stop()


def test_live_changing_camera_is_healthy_and_can_be_enabled(tmp_path, monkeypatch):
    engine, _ = camera_engine(tmp_path, monkeypatch, 'live')
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 15)
        assert engine.snapshot()['fault'] is None and engine.video_issue is None
        engine.assist(True)
        wait_for(lambda: engine.snapshot()['state'] == 'LOCKED')
    finally:
        engine.stop()


def test_recorded_video_with_repeated_frames_is_not_judged_frozen(tmp_path, monkeypatch):
    engine, _ = camera_engine(tmp_path, monkeypatch, 'frozen', kind='recorded')
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 30)
        assert engine.snapshot()['video_health'] is None and engine.snapshot()['fault'] is None
    finally:
        engine.stop()


def test_source_change_clears_picture_state(tmp_path, monkeypatch):
    engine, _ = camera_engine(tmp_path, monkeypatch, 'frozen')
    engine.start()
    try:
        wait_for(lambda: engine.video_issue == 'frozen video')
        engine.set_source({'kind': 'synthetic', 'scenario': 'moving'})
        assert engine.video_issue is None and engine.video_report is None
        wait_for(lambda: engine.snapshot()['frames'] > 0 and engine.snapshot()['source_label'] == 'SYNTHETIC')
        assert engine.snapshot()['video_health'] is None
    finally:
        engine.stop()


# ---------------------------------------------------------------- steering status and decision latency
def test_snapshot_reports_manual_steering_for_mock_and_serial_bridges(tmp_path):
    engine = Engine(tmp_path)
    state = engine.snapshot()
    assert state['steering_available'] is False
    assert state['steering_status'] == STEERING_UNAVAILABLE == 'Manual steering — computer steering unavailable'
    assert state['physical_output'] is False
    assert not hasattr(SerialBridge, 'physical_output') or SerialBridge.physical_output is False
    engine.session.close(0)


def test_status_changes_only_for_a_bridge_declaring_physical_output(tmp_path):
    bridge = MockBridge()
    bridge.physical_output = True
    engine = Engine(tmp_path, bridge=bridge)
    assert engine.snapshot()['steering_available'] is True
    assert engine.snapshot()['steering_status'] == 'Computer yaw assistance available'
    engine.session.close(0)


def test_decision_latency_is_recorded_for_processed_frames(tmp_path):
    engine = Engine(tmp_path)
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['decision_ms'] is not None)
        value = engine.snapshot()['decision_ms']
        assert 0 <= value < 1000
    finally:
        engine.stop()


# ---------------------------------------------------------------- operator lease
def test_leased_assistance_lapses_without_heartbeats(tmp_path):
    engine = Engine(tmp_path)
    engine.settings.lease_ms = 300
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 3)
        engine.assist(True, leased=True)
        assert 0 < engine.snapshot()['lease_ms_remaining'] <= 300
        wait_for(lambda: engine.snapshot()['fault'] == 'operator connection lost', timeout=3)
        state = engine.snapshot()
        assert state['state'] == 'FAULT' and not state['enabled'] and state['yaw'] == 0
        assert state['lease_ms_remaining'] is None
        time.sleep(.2)
        assert engine.snapshot()['state'] == 'FAULT'   # recovery never re-enables by itself
        events = (engine.session.path / 'events.jsonl').read_text()
        assert 'operator connection lost' in events
    finally:
        engine.stop()


def test_heartbeats_keep_a_leased_operator_enabled(tmp_path):
    engine = Engine(tmp_path)
    engine.settings.lease_ms = 300
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 3)
        engine.assist(True, leased=True)
        deadline = time.monotonic() + 1.2
        while time.monotonic() < deadline:
            assert engine.heartbeat() is True
            time.sleep(.1)
        assert engine.snapshot()['enabled'] and engine.snapshot()['fault'] is None
        engine.assist(False)
        assert engine.snapshot()['lease_ms_remaining'] is None and engine.heartbeat() is False
    finally:
        engine.stop()


def test_heartbeat_alone_never_enables_and_local_assist_is_unleased(tmp_path):
    engine = Engine(tmp_path)
    engine.settings.lease_ms = 200
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 3)
        assert engine.heartbeat() is False and not engine.snapshot()['enabled']
        engine.assist(True)
        time.sleep(.5)
        assert engine.snapshot()['enabled'] and engine.snapshot()['lease_ms_remaining'] is None
    finally:
        engine.stop()


def test_api_assist_is_leased_and_heartbeat_needs_the_token(tmp_path):
    engine = Engine(tmp_path)
    engine.settings.lease_ms = 400
    with TestClient(create_app(engine, 'token')) as client:
        wait_for(lambda: engine.snapshot()['frames'] > 3)
        assert client.post('/api/operator/heartbeat', json={}).status_code == 401
        assert client.post('/api/operator/heartbeat', json={}, headers={'Authorization': 'Bearer wrong'}).status_code == 401
        assert client.post('/api/operator/heartbeat', json={'extend': True}, headers=AUTH).status_code == 422
        assert client.post('/api/operator/heartbeat', json={}, headers=AUTH).json() == {'leased': False, 'lease_ms': 400}
        state = client.post('/api/operator/assist', json={'enabled': True}, headers=AUTH).json()
        assert state['enabled'] and state['lease_ms_remaining'] is not None
        for _ in range(8):
            assert client.post('/api/operator/heartbeat', json={}, headers=AUTH).json()['leased'] is True
            time.sleep(.1)
        assert engine.snapshot()['enabled']
        wait_for(lambda: engine.snapshot()['fault'] == 'operator connection lost', timeout=3)
        assert client.get('/api/state').json()['yaw'] == 0


# ---------------------------------------------------------------- colour picking
def green_scene():
    return synthetic(0, Settings(), 'centered')[0]


def test_suggestion_from_the_target_tracks_that_target():
    image = green_scene()
    result = color_pick.suggest(image, .5, .5)
    values = result['settings']
    assert result['warnings'] == [] and values['hue_low'] <= result['sample']['hue'] <= values['hue_high']
    settings = Settings(**{**Settings().dict(), **values})
    assert Detector().detect(image, settings) is not None
    assert Detector().detect(np.full_like(image, (24, 30, 33)), settings) is None


def test_grey_patch_warns_about_saturation():
    result = color_pick.suggest(np.full((100, 100, 3), 128, np.uint8), .5, .5)
    assert any('saturated' in warning for warning in result['warnings'])
    assert result['settings']['saturation_min'] >= color_pick.FLOOR


def test_red_target_warns_that_hue_wraps():
    image = np.zeros((100, 100, 3), np.uint8)
    image[:, :50] = (0, 0, 220)        # hue 0
    image[:, 50:] = (40, 0, 220)       # hue near 179
    result = color_pick.suggest(image, .5, .5)
    assert any('wrap' in warning for warning in result['warnings'])
    assert 0 <= result['settings']['hue_low'] <= result['settings']['hue_high'] <= 179


@pytest.mark.parametrize('x,y', [(0, 0), (1, 1), (0, 1), (1, 0)])
def test_picks_at_the_frame_edges_use_a_clipped_patch(x, y):
    result = color_pick.suggest(green_scene(), x, y)
    assert 1 <= result['sample']['pixels'] <= 13 * 13


@pytest.mark.parametrize('x,y', [(-.01, .5), (.5, 1.01)])
def test_picks_outside_the_frame_are_rejected(x, y):
    with pytest.raises(ValueError):
        color_pick.suggest(green_scene(), x, y)


def test_engine_pick_applies_only_on_request_and_disables_assistance(tmp_path):
    engine = Engine(tmp_path)
    with pytest.raises(ValueError):
        engine.pick_color(.5, .5)
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 3 and engine.detection is not None)
        before = engine.settings.dict()
        x, y = engine.detection['x'] / 640, engine.detection['y'] / 480
        preview = engine.pick_color(x, y)
        assert preview['applied'] is False and engine.settings.dict() == before
        engine.assist(True)
        result = engine.pick_color(x, y, apply=True)
        assert result['applied'] and not engine.snapshot()['enabled']
        assert all(engine.settings.dict()[key] == value for key, value in result['settings'].items())
    finally:
        engine.stop()


def test_api_pick_is_authorised_strict_and_returns_a_snapshot(tmp_path):
    engine = Engine(tmp_path)
    with TestClient(create_app(engine, 'token')) as client:
        wait_for(lambda: engine.snapshot()['frames'] > 3 and engine.detection is not None)
        target = {'x': engine.detection['x'] / 640, 'y': engine.detection['y'] / 480}
        assert client.post('/api/operator/pick', json=target).status_code == 401
        assert client.post('/api/operator/pick', json={'x': 1.5, 'y': .5}, headers=AUTH).status_code == 422
        assert client.post('/api/operator/pick', json={'x': '0.5', 'y': .5}, headers=AUTH).status_code == 422
        assert client.post('/api/operator/pick', json={**target, 'apply': 'yes'}, headers=AUTH).status_code == 422
        assert client.post('/api/operator/pick', json={**target, 'radius': 9}, headers=AUTH).status_code == 422
        assert client.post('/api/operator/pick', json={'x': 1, 'y': 0}, headers=AUTH).status_code == 200
        response = client.post('/api/operator/pick', json={**target, 'apply': True}, headers=AUTH)
        assert response.status_code == 200
        body = response.json()
        assert body['applied'] and body['snapshot']['settings']['hue_low'] == body['settings']['hue_low']
        assert body['snapshot']['enabled'] is False


def test_api_pick_without_a_frame_is_a_conflict(tmp_path, monkeypatch):
    engine = Engine(tmp_path)
    monkeypatch.setattr(engine, 'start', lambda: setattr(engine, 'running', True))
    with TestClient(create_app(engine, 'token')) as client:
        response = client.post('/api/operator/pick', json={'x': .5, 'y': .5}, headers=AUTH)
        assert response.status_code == 409 and 'No video frame' in response.json()['detail']


def test_engine_rejects_an_empty_picked_hue_range(tmp_path, monkeypatch):
    engine = Engine(tmp_path)
    engine.frame = Frame(green_scene(), time.monotonic(), 1, {})
    monkeypatch.setattr(color_pick, 'suggest', lambda image, x, y: {'settings': {'hue_low': 90, 'hue_high': 80}, 'sample': {}, 'warnings': []})
    with pytest.raises(ValueError):
        engine.pick_color(.5, .5, apply=True)
    assert engine.settings.hue_low == Settings().hue_low
    engine.session.close(0)


# ---------------------------------------------------------------- fallback pages
def test_fallback_page_and_assets_are_served_locally(tmp_path, monkeypatch):
    engine = Engine(tmp_path)
    monkeypatch.setattr(engine, 'start', lambda: setattr(engine, 'running', True))
    with TestClient(create_app(engine, 'token')) as client:
        page = client.get('/fallback')
        assert page.status_code == 200 and 'Manual steering — computer steering unavailable' in page.text
        for asset in ('fallback.js', 'fallback.css'):
            response = client.get('/assets/' + asset)
            assert response.status_code == 200 and response.text
        assert 'steering-status' in client.get('/').text and 'href="/fallback"' in client.get('/').text


def test_fallback_screen_is_read_only_and_has_no_external_assets():
    script = (STATIC / 'fallback.js').read_text()
    page = (STATIC / 'fallback.html').read_text()
    assert '/api/operator' not in script and 'Authorization' not in script and "method: 'POST'" not in script
    for text in (script, page, (STATIC / 'fallback.css').read_text()):
        assert 'http://' not in text and 'https://' not in text
    for element in ('steering', 'video', 'marker', 'error', 'target'):
        assert f'id="{element}"' in page


def test_monitor_script_sends_heartbeats_and_picks_with_the_token():
    script = (STATIC / 'app.js').read_text()
    assert "'/api/operator/heartbeat'" in script and "'/api/operator/pick'" in script
    assert 'renderFallback(state)' in script


# ---------------------------------------------------------------- camera CLI
@pytest.mark.parametrize('value,expected', [('0', 0), ('3', 3), ('/dev/video0', '/dev/video0'), ('rtsp://cam', 'rtsp://cam')])
def test_camera_device_parsing(value, expected):
    assert cli.camera_device(value) == expected


@pytest.mark.parametrize('backend,platform,expected', [
    ('auto', 'linux', 'v4l2'), ('auto', 'darwin', None), ('v4l2', 'darwin', 'v4l2'), ('default', 'linux', None)])
def test_camera_backend_selection(backend, platform, expected):
    assert cli.camera_spec('0', backend, platform).get('backend') == expected


def run_serve(monkeypatch, tmp_path, extra):
    servers = []
    class DemoEngine:
        def __init__(self, data, bridge=None, source=None, **navigation): self.source, self.running = source, True
        def assist(self, value): pass
    monkeypatch.setattr(cli, 'Engine', DemoEngine)
    monkeypatch.setattr(cli, 'create_app', lambda engine, token: engine)
    class Server:
        def __init__(self, config): self.config = config; servers.append(self)
        def run(self): pass
    monkeypatch.setattr(cli.uvicorn, 'Server', Server)
    monkeypatch.setattr(cli.uvicorn, 'Config', lambda app, **kwargs: SimpleNamespace(app=app, **kwargs))
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'serve', '--data', str(tmp_path)] + extra)
    cli.main()
    return servers[0].config.app.source


def test_serve_camera_option_starts_on_the_camera_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.sys, 'platform', 'linux')
    assert run_serve(monkeypatch, tmp_path, ['--camera', '/dev/video2']) == {'kind': 'camera', 'device': '/dev/video2', 'backend': 'v4l2'}
    monkeypatch.setattr(cli.sys, 'platform', 'darwin')
    assert run_serve(monkeypatch, tmp_path, ['--camera', '1']) == {'kind': 'camera', 'device': 1}


def test_camera_and_recorded_options_are_exclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'serve', '--camera', '0', '--recorded', 'x.avi'])
    with pytest.raises(SystemExit) as error: cli.main()
    assert error.value.code == 2


class FakeCapture:
    def __init__(self, device, *backend):
        self.device, self.backend, self.released = device, backend, False
    def isOpened(self): return self.device in (0, '/dev/video0')
    def get(self, prop): return {cv2.CAP_PROP_FRAME_WIDTH: 720, cv2.CAP_PROP_FRAME_HEIGHT: 480, cv2.CAP_PROP_FPS: 29.97,
                                cv2.CAP_PROP_FOURCC: cv2.VideoWriter_fourcc(*'YUYV')}[prop]
    def set(self, prop, value): return True
    def release(self): self.released = True


def test_camera_probe_lists_openable_devices(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(cv2, 'VideoCapture', lambda device, *a: opened.append(FakeCapture(device, *a)) or opened[-1])
    found = cli.probe_cameras(2, platform='darwin')
    assert found == [{'device': 0, 'width': 720, 'height': 480, 'fps': 29.97}]
    assert [c.device for c in opened] == [0, 1, 2] and all(c.released for c in opened)
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'cameras', '--max-index', '1'])
    monkeypatch.setattr(cli.sys, 'platform', 'darwin')
    cli.main()
    assert '0: 720 x 480 @ 30.0 fps' in capsys.readouterr().out


def test_camera_probe_reports_nothing_found(monkeypatch, capsys):
    monkeypatch.setattr(cv2, 'VideoCapture', lambda device, *a: FakeCapture('none'))
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'cameras', '--max-index', '0'])
    cli.main()
    assert 'No camera opened' in capsys.readouterr().out


def test_camera_probe_prefers_dev_video_on_linux(monkeypatch):
    monkeypatch.setattr(cv2, 'VideoCapture', lambda device, *a: FakeCapture(device))
    monkeypatch.setattr(Path, 'glob', lambda self, pattern: [Path('/dev/video0'), Path('/dev/video1')])
    assert [entry['device'] for entry in cli.probe_cameras(5, platform='linux')] == ['/dev/video0']


def test_v4l2_backend_is_passed_to_opencv(monkeypatch):
    seen = []
    monkeypatch.setattr(cv2, 'VideoCapture', lambda device, *a: seen.append((device, a)) or FakeCapture(0))
    OpenCVSource('/dev/video0', Settings(), backend='v4l2').close()
    OpenCVSource(0, Settings()).close()
    assert seen == [('/dev/video0', (cv2.CAP_V4L2,)), (0, ())]


# ---------------------------------------------------------------- latency tool
class FakeClock:
    def __init__(self): self.t = 100.0
    def __call__(self): return self.t
    def sleep(self, seconds): self.t += seconds


@pytest.mark.parametrize('delay_ms', [0, 40, 80, 150])
def test_latency_matches_the_simulated_camera_to_one_frame(delay_ms):
    clock = FakeClock()
    camera = latency.SimulatedCamera(delay_ms / 1000, frame_s=.02, clock=clock, sleep=clock.sleep)
    result = latency.measure(camera, camera.trigger, trials=4, timeout=1, settle=.05, clock=clock)
    assert result['measured'] == 4 and result['failed'] == 0
    for item in result['results']:
        assert delay_ms - 1e-6 <= item['latency_ms'] <= delay_ms + 20 + 1e-6
    assert result['min_ms'] <= result['median_ms'] <= result['p95_ms'] <= result['max_ms']


def test_latency_reports_a_target_that_never_disappears():
    clock = FakeClock()
    camera = latency.SimulatedCamera(0, frame_s=.02, clock=clock, sleep=clock.sleep)
    result = latency.measure(camera, lambda on: camera.trigger(True), trials=2, timeout=.3, settle=.05, clock=clock)
    assert result['measured'] == 0 and all('still visible' in r['error'] for r in result['results'])
    assert 'median_ms' not in result


def test_latency_reports_a_target_that_never_appears():
    clock = FakeClock()
    camera = latency.SimulatedCamera(0, frame_s=.02, clock=clock, sleep=clock.sleep)
    result = latency.measure(camera, lambda on: camera.trigger(False), trials=2, timeout=.3, settle=.05, clock=clock)
    assert result['failed'] == 2 and all('not detected' in r['error'] for r in result['results'])


def test_latency_ignores_missing_frames():
    clock = FakeClock()
    camera = latency.SimulatedCamera(.03, frame_s=.02, clock=clock, sleep=clock.sleep)
    calls = {'n': 0}
    class Dropping:
        def read(self):
            calls['n'] += 1
            if calls['n'] % 3 == 0:
                clock.sleep(.02)
                return None
            return camera.read()
    result = latency.measure(Dropping(), camera.trigger, trials=3, timeout=1, settle=.05, clock=clock)
    assert result['measured'] == 3


def test_latency_summary_percentiles_and_save(tmp_path):
    summary = latency.summarise([{'trial': i, 'latency_ms': float(v)} for i, v in enumerate([50, 10, 30, 20, 40])] + [{'trial': 9, 'error': 'x'}])
    assert (summary['min_ms'], summary['median_ms'], summary['max_ms'], summary['failed']) == (10, 30, 50, 1)
    assert summary['p95_ms'] == 50 and 'excludes' in summary['scope']
    path = latency.save(summary, tmp_path / 'nested' / 'latency.json')
    assert json.loads(path.read_text())['measured'] == 5


def test_latency_cli_with_simulated_camera(tmp_path, monkeypatch, capsys):
    output = tmp_path / 'latency.json'
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'latency', '--simulated-delay-ms', '30', '--trials', '3', '--output', str(output)])
    cli.main()
    saved = json.loads(output.read_text())
    assert saved['measured'] == 3 and saved['configuration']['trigger'] == 'simulated'
    assert all(r['latency_ms'] >= 30 for r in saved['results'])


def test_latency_cli_with_camera_uses_trigger_and_closes(tmp_path, monkeypatch):
    closed = []
    class Source:
        def __init__(self, device, settings, recorded=False, backend=None): self.device, self.backend = device, backend
        def close(self): closed.append('source')
    class Trigger:
        def __init__(self, *a): pass
        def __call__(self, on): pass
        def close(self): closed.append('trigger')
    monkeypatch.setattr('ball_demo.sources.OpenCVSource', Source)
    monkeypatch.setattr(latency, 'QtFlash', Trigger)
    monkeypatch.setattr(latency, 'GpioLed', Trigger)
    monkeypatch.setattr(latency, 'measure', lambda source, trigger, settings, trials, timeout: latency.summarise([{'trial': 0, 'latency_ms': 70.0}]))
    for trigger in ('screen', 'gpio'):
        monkeypatch.setattr(sys, 'argv', ['ball-demo', 'latency', '--camera', '0', '--trigger', trigger, '--output', str(tmp_path / f'{trigger}.json')])
        cli.main()
        assert json.loads((tmp_path / f'{trigger}.json').read_text())['configuration']['trigger'] == trigger
    assert closed == ['source', 'trigger', 'source', 'trigger']


def test_gpio_led_trigger_uses_gpiozero(monkeypatch):
    states = []
    class LED:
        def __init__(self, pin): states.append(('pin', pin))
        def on(self): states.append('on')
        def off(self): states.append('off')
        def close(self): states.append('closed')
    monkeypatch.setitem(sys.modules, 'gpiozero', SimpleNamespace(LED=LED))
    led = latency.GpioLed(17)
    led(True); led(False); led.close()
    assert states == [('pin', 17), 'on', 'off', 'closed']


# ---------------------------------------------------------------- serial HELLO retry (ESP32-S3 reset on open)
class FakeSerial:
    def __init__(self, *a, **k): self.written, self.incoming, self.in_waiting = [], b'', 0
    def write(self, data): self.written.append(data.decode())
    def read(self, n):
        data, self.incoming = self.incoming[:n], self.incoming[n:]
        self.in_waiting = len(self.incoming)
        return data
    def feed(self, data): self.incoming += data; self.in_waiting = len(self.incoming)
    def open(self): pass
    def close(self): pass


def test_hello_repeats_until_ready_then_stops(monkeypatch):
    monkeypatch.setattr('ball_demo.bridge.serial.Serial', FakeSerial)
    bridge = SerialBridge('/dev/fake')
    start = bridge.last_hello
    hello = f'HELLO 1 {bridge.session}\n'
    bridge.poll(start + HELLO_RETRY_S / 2)
    assert bridge.serial.written == [hello]
    bridge.poll(start + HELLO_RETRY_S)
    bridge.poll(start + HELLO_RETRY_S * 1.5)
    bridge.poll(start + HELLO_RETRY_S * 2)
    assert bridge.serial.written == [hello] * 3
    bridge.serial.feed(f'READY 1 {bridge.session} NO_OUTPUT\n'.encode())
    bridge.poll(start + HELLO_RETRY_S * 2.1)
    assert bridge.ready
    bridge.poll(start + HELLO_RETRY_S * 10)
    assert bridge.serial.written.count(hello) == 3


def test_unanswered_commands_resync_with_a_new_session(monkeypatch):
    # An ESP32-S3 reset or USB drop forgets the session; CMDs are then silently ignored.
    monkeypatch.setattr('ball_demo.bridge.serial.Serial', FakeSerial)
    bridge = SerialBridge('/dev/fake')
    start = bridge.last_hello
    old = bridge.session
    bridge.serial.feed(f'READY 1 {old} NO_OUTPUT\n'.encode())
    bridge.poll(start + .1)
    bridge.send(True, 200, start + .1)
    bridge.poll(start + .1 + RESYNC_S * .9)
    assert bridge.ready and bridge.session == old
    bridge.poll(start + .1 + RESYNC_S)
    assert not bridge.ready and bridge.session != old and bridge.outstanding == {}
    assert bridge.serial.written[-1] == f'HELLO 1 {bridge.session}\n'
    assert bridge.handshake_started == start + .1 + RESYNC_S
    bridge.send(True, 200, start + 1.2)
    assert bridge.serial.written[-1].startswith('HELLO')
    bridge.serial.feed(f'ACK 1 {old} 1 1 200 NONE\nREADY 1 {old} NO_OUTPUT\n'.encode())
    assert bridge.poll(start + 1.25) == [] and not bridge.ready
    bridge.serial.feed(f'READY 1 {bridge.session} NO_OUTPUT\n'.encode())
    bridge.poll(start + 1.3)
    assert bridge.ready and bridge.last_ack == start + 1.3
    bridge.send(False, 0, start + 1.35)
    bridge.serial.feed(f'ACK 1 {bridge.session} 2 0 0 NONE\n'.encode())
    assert bridge.poll(start + 1.4) == [{'seq': 2, 'yaw': 0, 'fault': 'NONE'}]


class HandshakeBridge:
    transport = 'TEST / no physical output'
    fault, accepted_yaw, seq, session = 'none', 0, 0, 'handshake'
    def __init__(self, now): self.last_ack = self.handshake_started = now; self.ready = False; self.commands = []
    def poll(self, now): return []
    def send(self, enabled, yaw, now): self.seq += 1; self.commands.append((enabled, yaw))
    def close(self): pass


@pytest.mark.parametrize('waited,expected', [(.3, None), (BRIDGE_READY_S - .01, None), (BRIDGE_READY_S, 'bridge not responding')])
def test_pending_handshake_stays_manual_until_ready_deadline(tmp_path, monkeypatch, waited, expected):
    clock = 100.
    monkeypatch.setattr(engine_module.time, 'monotonic', lambda: clock)
    bridge = HandshakeBridge(clock - waited)
    engine = Engine(tmp_path, bridge=bridge); engine.frame = Frame(None, clock, 1, {})
    with pytest.raises(ValueError): engine.assist(True)
    engine.running = True
    monkeypatch.setattr(engine_module.time, 'sleep', lambda duration: setattr(engine, 'running', False))
    engine.control_loop()
    assert engine.controller.fault == expected
    assert engine.controller.state == ('FAULT' if expected else 'MANUAL')
    assert bridge.commands == [(False, 0)]
    bridge.ready = True; bridge.last_ack = clock; engine.running = True
    engine.control_loop()
    bridge.ready = False; bridge.handshake_started = clock; engine.running = True
    engine.control_loop()
    engine.stop()
    events = [json.loads(line) for line in (engine.session.path / 'events.jsonl').read_text().splitlines()]
    assert [e['type'] for e in events if e['type'].startswith('bridge_')] == ['bridge_ready', 'bridge_resync']


def test_repeated_bridge_exception_logs_one_fault(tmp_path, monkeypatch):
    engine = Engine(tmp_path)
    def broken(now): raise OSError('port gone')
    monkeypatch.setattr(engine.bridge, 'poll', broken)
    ticks = iter(range(20))
    monkeypatch.setattr(engine_module.time, 'sleep', lambda duration: next(ticks, None) is None and setattr(engine, 'running', False))
    engine.running = True; engine.control_loop()
    assert engine.controller.state == 'FAULT' and engine.controller.fault == 'bridge: port gone'
    engine.stop()
    events = [json.loads(line) for line in (engine.session.path / 'events.jsonl').read_text().splitlines()]
    assert [e['data']['reason'] for e in events if e['type'] == 'fault'] == ['port gone']
