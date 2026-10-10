"""Regressions for the 2026-10-08 audit: reconnection, stale settings, logging failure, worker health,
target switching, recorded-video pacing, sandbox serialisation and replay provenance."""
import asyncio
import json
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ball_demo import cli, engine as engine_module
from ball_demo.api import create_app
from ball_demo.config import Settings
from ball_demo.control import Controller
from ball_demo.engine import Engine
from ball_demo.session import Session
from ball_demo.sources import Frame, OpenCVSource, synthetic
from ball_demo.vision import Detector


def wait_for(condition, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition(): return
        time.sleep(.01)
    raise AssertionError('condition did not become true')


def disc(x, width=640, height=480, colour=(50, 220, 105)):
    image = np.full((height, width, 3), (24, 30, 33), np.uint8)
    cv2.circle(image, (int(x), height // 2), 25, colour, -1)
    return image


# ---------------------------------------------------------------- #12 target switching
def test_detector_flags_a_jump_to_a_distant_blob():
    detector, settings = Detector(), Settings()
    first = detector.detect(disc(120), settings)
    assert first and 'reacquired' not in first
    near = detector.detect(disc(130), settings)
    assert 'reacquired' not in near
    jumped = detector.detect(disc(520), settings)
    assert jumped['reacquired'] is True and abs(jumped['x'] - 520) < 2
    assert 'reacquired' not in detector.detect(disc(525), settings)


def test_locked_controller_restarts_acquisition_after_a_jump():
    controller, settings = Controller(), Settings()
    controller.enable(True)
    detection = {'error': -.6, 'x': 120.0}
    for _ in range(5): controller.frame(detection, settings, .05)
    assert controller.state == 'LOCKED' and controller.yaw != 0
    controller.frame({'error': .6, 'x': 520.0, 'reacquired': True}, settings, .05)
    assert controller.state == 'SEARCHING' and controller.yaw == 0 and controller.count == 1
    events = [e for e in controller.events if e['to'] == 'SEARCHING']
    assert events[-1]['reason'] == 'target changed'
    for _ in range(settings.acquire_frames - 1): controller.frame({'error': .6}, settings, .05)
    assert controller.state == 'LOCKED'


def test_engine_end_to_end_jump_never_steers_toward_the_new_blob(tmp_path, monkeypatch):
    positions = iter([120] * 40 + [520] * 400)
    class Jumping:
        label, eof = 'CAMERA', False
        def __init__(self, *args): self.index = 0
        def read(self):
            time.sleep(.02); self.index += 1
            noise = np.random.default_rng(self.index).normal(0, 2, (480, 640, 3))
            return Frame(np.clip(disc(next(positions)) + noise, 0, 255).astype(np.uint8), time.monotonic(), self.index, {})
        def close(self): pass
    monkeypatch.setattr(engine_module, 'OpenCVSource', Jumping)
    engine = Engine(tmp_path, source={'kind': 'camera', 'device': 0})
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 5)
        engine.assist(True)
        wait_for(lambda: engine.snapshot()['state'] == 'LOCKED')
        assert engine.snapshot()['yaw'] < 0
        wait_for(lambda: engine.detection and engine.detection['x'] > 400)
        events = (engine.session.path / 'events.jsonl').read_text()
        wait_for(lambda: 'target changed' in (engine.session.path / 'events.jsonl').read_text())
    finally:
        engine.stop()


# ---------------------------------------------------------------- #13 settings changes
def test_detection_made_with_replaced_settings_is_not_published(tmp_path, monkeypatch):
    started, release = threading.Event(), threading.Event()
    real = Detector.detect
    def slow(self, image, settings):
        if settings.hue_low == 35 and not release.is_set():
            started.set(); release.wait(2)
        return real(self, image, settings)
    monkeypatch.setattr(engine_module.Detector, 'detect', slow)
    engine = Engine(tmp_path)
    engine.start()
    try:
        assert started.wait(2)
        published = engine.processed
        engine.configure({'hue_low': 100, 'hue_high': 120})
        release.set()
        wait_for(lambda: engine.processed > published)
        assert engine.settings_version == 1
        time.sleep(.2)
        assert engine.detection is None     # hue 100-120 cannot see the green target
    finally:
        engine.stop()


# ---------------------------------------------------------------- #10 camera recovery
def test_unplugged_camera_is_reopened_and_recovers_without_re_enabling(tmp_path, monkeypatch):
    opened = []
    class Flaky:
        label, eof = 'CAMERA', False
        def __init__(self, *args):
            opened.append(time.monotonic())
            if len(opened) == 2: raise OSError('device busy while replugging')
            self.index = 0
        def read(self):
            time.sleep(.02); self.index += 1
            if len(opened) == 1 and self.index > 10: return None       # cable pulled
            noise = np.random.default_rng(self.index).normal(0, 2, (480, 640, 3))
            return Frame(np.clip(disc(320) + noise, 0, 255).astype(np.uint8), time.monotonic(), self.index, {})
        def close(self): pass
    monkeypatch.setattr(engine_module, 'OpenCVSource', Flaky)
    monkeypatch.setattr(engine_module, 'CAMERA_RETRY_S', .3)
    engine = Engine(tmp_path, source={'kind': 'camera', 'device': 0})
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 3)
        engine.assist(True)
        wait_for(lambda: engine.snapshot()['state'] == 'FAULT')
        wait_for(lambda: len(opened) >= 3 and engine.source_error is None and engine.snapshot()['frame_age_ms'] < 100)
        state = engine.snapshot()
        assert state['state'] == 'FAULT' and not state['enabled'] and state['yaw'] == 0
        events = (engine.session.path / 'events.jsonl').read_text()
        assert 'camera_reopen' in events and 'source_recovered' in events
        engine.assist(True)
        wait_for(lambda: engine.snapshot()['state'] == 'LOCKED')
    finally:
        engine.stop()


def test_recorded_open_failure_is_not_retried(tmp_path, monkeypatch):
    opened = []
    class Missing:
        def __init__(self, *args): opened.append(1); raise OSError('no file')
    monkeypatch.setattr(engine_module, 'OpenCVSource', Missing)
    monkeypatch.setattr(engine_module, 'CAMERA_RETRY_S', .05)
    engine = Engine(tmp_path, source={'kind': 'recorded', 'path': 'missing.avi'})
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['fault'] is not None)
        time.sleep(.4)
        assert opened == [1]
    finally:
        engine.stop()


# ---------------------------------------------------------------- #14 logging failures
class BrokenFile:
    closed = False
    def write(self, data): raise OSError('disk full')
    def flush(self): raise OSError('disk full')
    def close(self): raise OSError('disk full')


def test_logging_failure_is_counted_not_fatal(tmp_path):
    session = Session(tmp_path, Settings(), {'kind': 'synthetic'})
    session.events = BrokenFile()
    session.samples = BrokenFile()
    session.writer = type('W', (), {'writerow': lambda self, row: (_ for _ in ()).throw(OSError('disk full'))})()
    session.event('fault', {'reason': 'x'})
    session.sample({'state': 'MANUAL', 'enabled': False, 'yaw': 0, 'ack_yaw': 0, 'detection': None,
                    'frame_age_ms': 1, 'ack_age_ms': 1, 'processing_ms': 2.0, 'frames': 1})
    session.close(1)
    assert session.errors >= 3 and 'disk full' in session.last_error and session.faults == 1
    assert session.timings == [2.0]


def test_control_worker_survives_a_failing_log(tmp_path):
    engine = Engine(tmp_path)
    engine.start()
    try:
        wait_for(lambda: engine.snapshot()['frames'] > 3)
        engine.session.events = BrokenFile()
        engine.session.samples = BrokenFile()
        engine.session.writer = type('W', (), {'writerow': lambda self, row: (_ for _ in ()).throw(OSError('disk full'))})()
        before = engine.control_tick_at
        time.sleep(.4)
        assert engine.control_tick_at > before and engine.health()['ok']
        assert engine.health()['logging_errors'] > 0
        engine.assist(True)
        wait_for(lambda: engine.snapshot()['state'] == 'LOCKED')
    finally:
        engine.stop()


# ---------------------------------------------------------------- #15 worker health
def test_health_reports_worker_liveness(tmp_path):
    engine = Engine(tmp_path)
    assert engine.health()['ok'] is False               # not started
    with TestClient(create_app(engine, 'token')) as client:
        wait_for(lambda: client.get('/api/health').json()['ok'])
        body = client.get('/api/health').json()
        assert body['workers_alive'] == [True, True] and body['control_tick_age_ms'] < 3000
        assert body['physical_output'] is False and body['service'] == 'ball-demo'
        engine.control_tick_at -= 10                    # a stalled control worker
        assert client.get('/api/health').json()['ok'] is False


def test_health_detects_a_dead_worker(tmp_path):
    engine = Engine(tmp_path)
    engine.start()
    try:
        wait_for(lambda: engine.health()['ok'])
        engine.threads[1] = threading.Thread(target=lambda: None); engine.threads[1].start(); engine.threads[1].join()
        assert engine.health()['ok'] is False and engine.health()['workers_alive'] == [True, False]
    finally:
        engine.stop()


# ---------------------------------------------------------------- #17/#18 session statistics and provenance
def test_timing_uses_one_value_per_processed_frame(tmp_path):
    session = Session(tmp_path, Settings(), {'kind': 'synthetic'})
    base = {'state': 'MANUAL', 'enabled': False, 'yaw': 0, 'ack_yaw': 0, 'detection': None, 'frame_age_ms': 1, 'ack_age_ms': 1}
    for frames, processing in [(1, 1.0), (1, 1.0), (1, 1.0), (2, 9.0), (3, 2.0), (3, 2.0)]:
        session.sample({**base, 'frames': frames, 'processing_ms': processing})
    session.close(3)
    summary = json.loads((session.path / 'summary.json').read_text())
    assert session.timings == [1.0, 9.0, 2.0] and summary['control_samples'] == 6
    assert summary['timing_basis'] == 'one value per processed frame'


def test_summary_records_the_final_source_and_settings(tmp_path):
    engine = Engine(tmp_path)
    engine.set_source({'kind': 'synthetic', 'scenario': 'loss'})
    engine.configure({'gain': 123.0})
    engine.session.close(0)
    summary = json.loads((engine.session.path / 'summary.json').read_text())
    assert summary['source'] == {'kind': 'synthetic', 'scenario': 'moving'}          # startup, unchanged
    assert summary['final_source'] == {'kind': 'synthetic', 'scenario': 'loss'}
    assert summary['final_settings']['gain'] == 123.0 and summary['source_changes'] == 1


def test_replay_export_keeps_camera_provenance(tmp_path, monkeypatch):
    engine = Engine(tmp_path, source={'kind': 'camera', 'device': 0})
    engine.set_source({'kind': 'recorded', 'path': '/data/flight.avi'})
    engine.session.sample({'state': 'MANUAL', 'enabled': False, 'yaw': 0, 'ack_yaw': 0, 'detection': None,
                           'frame_age_ms': 1, 'ack_age_ms': 1, 'processing_ms': None, 'frames': 0})
    engine.session.close(0)
    output = tmp_path / 'replay.json'
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'replay', str(engine.session.path), '--output', str(output)])
    cli.main()
    replay = json.loads(output.read_text())
    assert replay['label'] == 'REPLAY / CAMERA+RECORDED session / no bridge output'
    assert replay['sources'] == [{'kind': 'camera', 'device': 0}, {'kind': 'recorded', 'path': '/data/flight.avi'}]
    assert replay['video_included'] is False and replay['session'] == engine.session.id


# ---------------------------------------------------------------- #20 recorded frame rate
def write_clip(path, fps, frames=30):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), fps, (640, 480))
    for index in range(frames): writer.write(disc(40 + index * 15))
    writer.release()


@pytest.mark.parametrize('fps', [60, 10])
def test_paced_recording_plays_at_its_own_rate(tmp_path, monkeypatch, fps):
    path = tmp_path / f'clip{fps}.avi'
    write_clip(path, fps)
    now = [50.0]
    monkeypatch.setattr('ball_demo.sources.time.monotonic', lambda: now[0])
    source = OpenCVSource(str(path), Settings(), True, None, True)
    assert source.file_fps == pytest.approx(fps, rel=.01)
    seen = []
    for step in range(8):                    # reads at the 20 Hz processing rate
        frame = source.read()
        seen.append(frame.index if frame else None)
        now[0] += .05
    if fps == 60:
        assert seen == list(range(8))  and source.position == 1 + 7 * 3   # two of every three file frames skipped
    else:
        assert seen == [0, 0, 1, 1, 2, 2, 3, 3]                          # 10 fps file held for two reads
    source.close()


def test_paced_recording_reaches_eof_while_skipping(tmp_path, monkeypatch):
    path = tmp_path / 'short.avi'
    write_clip(path, 60, frames=6)
    now = [0.0]
    monkeypatch.setattr('ball_demo.sources.time.monotonic', lambda: now[0])
    source = OpenCVSource(str(path), Settings(), True, None, True)
    assert source.read() is not None
    now[0] = 1.0
    assert source.read() is None and source.eof
    source.close()


def test_unpaced_reads_and_implausible_rates_stay_sequential(tmp_path):
    path = tmp_path / 'clip.avi'
    write_clip(path, 60, frames=5)
    source = OpenCVSource(str(path), Settings(), True)
    assert source.file_fps is None and [source.read().index for _ in range(5)] == [0, 1, 2, 3, 4]
    assert source.read() is None and source.eof
    source.close()


# ---------------------------------------------------------------- #21 sandbox serialisation
def test_sandbox_generations_run_one_at_a_time(tmp_path, monkeypatch):
    import ball_demo.api as api_module
    active, peak = [0], [0]
    lock = threading.Lock()
    def slow_trace(scenario):
        with lock:
            active[0] += 1; peak[0] = max(peak[0], active[0])
        time.sleep(.1)
        with lock: active[0] -= 1
        return {'scenario': scenario, 'samples': []}
    monkeypatch.setattr(api_module, 'trace', slow_trace)
    engine = Engine(tmp_path)
    monkeypatch.setattr(engine, 'start', lambda: setattr(engine, 'running', True))
    app = create_app(engine, 'token')
    route = next(r for r in app.routes if getattr(r, 'path', '') == '/api/sandbox/{scenario}')
    async def burst():
        return await asyncio.gather(*(route.endpoint(name) for name in ['moving', 'loss', 'edges', 'blur']))
    results = asyncio.run(burst())
    assert [r['scenario'] for r in results] == ['moving', 'loss', 'edges', 'blur'] and peak[0] == 1
    engine.session.close(0)


# ---------------------------------------------------------------- browser script contracts
STATIC = Path(__file__).resolve().parents[1] / 'ball_demo' / 'static'


def test_browser_script_serialises_commands_and_locks_to_neutral():
    script = (STATIC / 'app.js').read_text()
    assert 'commandChain.then(run, run)' in script and 'neutralEpoch' in script
    lock = script[script.index("element('operator-lock').onclick"):][:400]
    assert lock.index("operatorAction('assist', { enabled: false })") < lock.index("operatorToken = ''")
    assert 'validateTrace(value)' in script and 'MAX_REPLAY_BYTES' in script
    assert 'id="video-stale"' in (STATIC / 'index.html').read_text()
