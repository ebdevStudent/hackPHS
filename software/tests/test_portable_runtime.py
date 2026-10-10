"""Pixel-to-mission behavior, independent freshness bounds, and bridge isolation."""
import time

import cv2
import numpy as np
import pytest

from ball_demo.api import create_app
from ball_demo.config import Settings
from ball_demo.engine import Engine
from ball_demo.portable_demo import demo_calibration, demo_roster, render_tag, PortableDemoSource
from ball_demo.sources import Frame
from ball_demo.ui_api import PortableAPI, UICommand


@pytest.fixture
def runtime(tmp_path):
    engine = Engine(tmp_path, roster=demo_roster(), portable_calibration=demo_calibration(),
                    portable_delay_s=.01)
    yield engine, engine.portable
    engine.stop()


def submit(engine, kind='follow', request_id='start', **payload):
    defaults = {'person_id': 'synthetic-walker'} if kind == 'follow' else {}
    caps = {k: {'supported': True, 'ready': True} for k in ('person_follow', 'landing_site', 'landing_current')}
    return engine.mission_control.submit_mock({'request_id': request_id, 'kind': kind,
        **defaults, **payload}, caps, engine.roster)[0]


def frame(engine, worker, index, now, image=None, *, tag_id=7, translation=(.2, -.04, 1.8)):
    if image is None:
        image = cv2.cvtColor(render_tag(worker.calibration, tag_id, translation), cv2.COLOR_GRAY2BGR)
    engine.frame = Frame(image, now, index, {'visible': False})  # Truth deliberately contradicts pixels.
    worker.process(engine.frame, (engine.generation, index), 'synthetic', now=now + .01)


def test_real_pixels_drive_acquisition_loss_reacquisition_and_bounded_motion(runtime):
    engine, worker = runtime
    submit(engine)
    now = time.monotonic()
    for i in range(3):
        frame(engine, worker, i, now + i * .05)
        mission = engine.mission_control.ui_mission()
        assert mission['phase'] == ('active' if i == 2 else 'reacquiring')
    sample = worker.snapshot()
    assert sample['pose']['range_m'] == pytest.approx(np.linalg.norm([.2, -.04, 1.8]), abs=.04)
    assert 0 < sample['desired']['forward_m_s'] <= .7 * .05 + 1e-9
    assert abs(sample['desired']['yaw_rate_rad_s']) <= 1.2
    assert not sample['physical_output'] and not engine.controller.enabled and engine.controller.yaw == 0
    frame(engine, worker, 3, now + .15, image=np.full((480, 640, 3), 255, np.uint8))
    assert engine.mission_control.ui_mission()['phase'] == 'lost'
    assert worker.snapshot()['loss_event'] and worker.snapshot()['desired']['forward_m_s'] == 0
    for i in range(4, 7):
        frame(engine, worker, i, now + i * .05)
        assert engine.mission_control.ui_mission()['phase'] == ('active' if i == 6 else 'reacquiring')


def test_frozen_frames_never_supply_three_fresh_observations(runtime):
    engine, worker = runtime
    submit(engine)
    now = time.monotonic()
    frame(engine, worker, 0, now)
    for _ in range(10):
        worker.process(engine.frame, (0, 0), 'synthetic', now=now + .02)
        engine.mission_control.tick_mock(True, vision_driven=True)
    assert engine.mission_control.ui_mission()['phase'] == 'reacquiring'
    worker.process(engine.frame, (0, 0), 'synthetic', now=now + .26)
    assert worker.snapshot()['state'] == 'lost'
    for i in range(1, 4):
        frame(engine, worker, i, now + .3 + i * .05)
        assert engine.mission_control.ui_mission()['phase'] == ('active' if i == 3 else 'reacquiring')


def test_wrong_tag_geometry_and_example_calibration_never_advance_a_live_mission(runtime):
    engine, worker = runtime
    submit(engine)
    now = time.monotonic()
    for i in range(4):
        frame(engine, worker, i, now + i * .05, tag_id=8)
    assert engine.mission_control.ui_mission()['phase'] != 'active'
    worker.process(engine.frame, (0, 3), 'camera', now=now + .16)
    assert 'Example calibration' in worker.snapshot()['reason']
    assert worker.snapshot()['desired']['forward_m_s'] == 0


def test_stop_abort_and_source_change_neutralize_without_reactivation(runtime):
    engine, worker = runtime
    result = submit(engine)
    now = time.monotonic()
    for i in range(3):
        frame(engine, worker, i, now + i * .05)
    api = PortableAPI(create_app(engine, 'secret'), engine, 'secret')
    api.command(UICommand(request_id='stop', kind='stop', payload={
        'mission_id': result['mission_id'], 'pending_request_id': None}))
    assert worker.snapshot()['desired']['forward_m_s'] == 0
    frame(engine, worker, 4, now + .2)
    assert engine.mission_control.ui_mission()['phase'] == 'stopped'
    result = submit(engine, request_id='again')
    api.command(UICommand(request_id='abort', kind='abort', payload={'mission_id': result['mission_id']}))
    frame(engine, worker, 5, now + .25)
    assert engine.mission_control.ui_mission()['phase'] == 'aborted'
    submit(engine, request_id='third')
    engine.set_source({'kind': 'synthetic', 'scenario': 'moving'})
    assert engine.mission_control.ui_mission()['phase'] == 'failed'


def test_inference_finishing_after_stop_or_source_switch_cannot_restore_motion(runtime, monkeypatch):
    engine, worker = runtime
    result = submit(engine)
    now = time.monotonic()
    for i in range(3):
        frame(engine, worker, i, now + i * .05)
    original = worker.vision.process
    def stop_during_inference(*args, **kwargs):
        observation = original(*args, **kwargs)
        submit(engine, 'stop', 'stop-race', mission_id=result['mission_id'])
        return observation
    monkeypatch.setattr(worker.vision, 'process', stop_during_inference)
    frame(engine, worker, 3, now + .15)
    assert worker.snapshot()['desired']['forward_m_s'] == 0
    def switch_during_inference(*args, **kwargs):
        observation = original(*args, **kwargs)
        engine.set_source({'kind': 'camera', 'device': 0})
        return observation
    monkeypatch.setattr(worker.vision, 'process', switch_during_inference)
    frame(engine, worker, 4, now + .2)
    assert worker.snapshot()['desired']['forward_m_s'] == 0


def test_landing_requires_pixel_pose_then_an_independent_touchdown_event(runtime):
    engine, worker = runtime
    submit(engine, 'land_site', site_id='synthetic-pad')
    now = time.monotonic()
    for i in range(3):
        frame(engine, worker, i, now + i * .05, tag_id=8, translation=(-.38, .16, 2.))
    assert engine.mission_control.ui_mission()['phase'] == 'landing'
    engine.mission_control.tick_mock(True, vision_driven=True, site_visible=True, dt_s=.25)
    assert engine.mission_control.ui_mission()['phase'] == 'landing'
    frame(engine, worker, 3, now + .15, image=np.full((480, 640, 3), 255, np.uint8))
    assert engine.mission_control.ui_mission()['phase'] == 'lost'
    for i in range(4, 7):
        frame(engine, worker, i, now + i * .05, tag_id=8, translation=(-.38, .16, 2.))
    for _ in range(30):
        engine.mission_control.tick_mock(True, vision_driven=True, site_visible=True, dt_s=.25)
    assert engine.mission_control.ui_mission()['phase'] == 'landed'
    assert engine.mission_control.ui_mission()['progress'] == 1


def test_real_worker_runs_with_generated_images_and_stops_cleanly(runtime):
    engine, worker = runtime
    engine.source_spec = {'kind': 'synthetic', 'scenario': 'portable-tags'}
    engine.start()
    try:
        submit(engine)
        deadline = time.monotonic() + 3
        while engine.mission_control.ui_mission()['phase'] != 'active' and time.monotonic() < deadline:
            time.sleep(.02)
        assert engine.mission_control.ui_mission()['phase'] == 'active'
        assert engine.health()['ok']
        assert engine.controller.yaw == 0 and not engine.controller.enabled
    finally:
        engine.stop()
    assert not worker.thread.is_alive()
    assert worker.snapshot()['desired']['forward_m_s'] == 0


@pytest.mark.parametrize('delay', [None, True, 0, -.1, .25, float('nan')])
def test_invalid_delay_bound_cannot_start_a_target_worker(tmp_path, delay):
    with pytest.raises(ValueError):
        Engine(tmp_path, portable_calibration=demo_calibration(), portable_delay_s=delay)


def test_demo_scene_and_configuration_remain_explicitly_synthetic():
    source = PortableDemoSource(Settings())
    frame = source.read()
    assert frame.truth['source'] == 'synthetic' and source.calibration.example
    source.index = int(2.1 * source.settings.processing_hz)
    assert not source.read().truth['visible']
    source.close()


def test_missing_roster_and_worker_failure_hold_a_neutral_lost_mission(runtime, monkeypatch):
    from ball_demo.roster import Roster
    engine, worker = runtime
    submit(engine)
    engine.roster = Roster()
    frame(engine, worker, 0, time.monotonic())
    assert 'No enabled' in worker.snapshot()['reason']
    engine.roster = demo_roster()
    def fail(*args, **kwargs):
        worker.stop_event.set()
        raise RuntimeError('Detector stopped unexpectedly')
    monkeypatch.setattr(worker, 'process', fail)
    worker.run()
    assert worker.snapshot()['state'] == 'lost'
    assert 'Detector stopped unexpectedly' in worker.snapshot()['reason']
    assert worker.snapshot()['desired'] == {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}


def test_close_approach_and_simulated_boundary_stop_motion(runtime):
    from ball_demo.target_tracking import estimate_relative_tag_pose
    from ball_demo.localization import Observation, Timing, tag_points
    engine, worker = runtime
    submit(engine)
    def pose_at(z):
        corners = cv2.projectPoints(tag_points(.2), np.array([2.6, .5, .1]), np.array([0., 0., z]),
            np.asarray(worker.calibration.intrinsics), np.zeros(5))[0].reshape(4, 2)
        return estimate_relative_tag_pose(Observation(id=7, corners=corners.tolist()), engine.roster.people[0],
            worker.calibration, sequence=1, timing=Timing(host_received_s=10., exposure_s=10., provenance='synthetic'))
    worker.last_motion_at = 10.
    assert worker._motion(pose_at(.44), 10., True) == {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
    worker.position, worker.speed = [4., 0., 0.], .45
    assert worker._motion(pose_at(2.), 10.05, True)['forward_m_s'] == 0
    assert engine.mission_control.ui_mission()['phase'] == 'failed'


@pytest.mark.parametrize('change', ['shutdown', 'new-mission'])
def test_obsolete_inference_result_cannot_update_the_new_worker_state(runtime, monkeypatch, change):
    engine, worker = runtime
    result = submit(engine)
    now = time.monotonic()
    frame(engine, worker, 0, now)
    original = worker.vision.process
    def replace(*args, **kwargs):
        observation = original(*args, **kwargs)
        if change == 'shutdown':
            worker.stop_event.set()
        else:
            submit(engine, 'stop', 'stop-first', mission_id=result['mission_id'])
            submit(engine, request_id='new-mission')
        return observation
    monkeypatch.setattr(worker.vision, 'process', replace)
    frame(engine, worker, 1, now + .05)
    assert worker.snapshot()['frame_index'] == 0
    assert worker.snapshot()['desired']['forward_m_s'] == 0


def test_stalled_worker_cannot_keep_mock_motion_or_descent_fresh(runtime, monkeypatch):
    engine, worker = runtime
    submit(engine)
    now = time.monotonic()
    for i in range(3):
        frame(engine, worker, i, now + i * .05)
    assert worker.snapshot()['state'] == 'tracking'
    monkeypatch.setattr('ball_demo.portable_runtime.time.monotonic', lambda: now + .4)
    report = worker.snapshot()
    assert report['state'] == 'lost' and report['pose'] is None
    assert report['desired'] == {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
    assert engine.mission_control.ui_mission()['phase'] == 'lost'
    for i in range(3, 6):
        frame(engine, worker, i, now + .4 + i * .05)
        assert engine.mission_control.ui_mission()['phase'] == ('active' if i == 5 else 'reacquiring')


def test_inference_that_finishes_beyond_deadline_cannot_publish_a_fresh_pose(runtime, monkeypatch):
    engine, worker = runtime
    submit(engine)
    now = time.monotonic()
    frame(engine, worker, 0, now)
    original = worker.vision.process
    def slow(*args, **kwargs):
        result = original(*args, **kwargs)
        monkeypatch.setattr('ball_demo.portable_runtime.time.monotonic', lambda: now + 1.)
        return result
    monkeypatch.setattr(worker.vision, 'process', slow)
    frame(engine, worker, 1, now + .05)
    assert 'inference exceeded' in worker.snapshot()['reason']
    assert worker.snapshot()['desired']['forward_m_s'] == 0
