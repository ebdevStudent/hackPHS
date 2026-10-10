"""Automatic scanner registration with fake hardware, real tag image inference."""
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from ball_demo.map_io import CameraGeometry
from ball_demo.mapping import Station, capture_d435
from ball_demo.navigation_fixtures import example_bundle, example_pose
from ball_demo.synthetic_navigation import tag_image
from test_mapping import sdk_fixture


def automatic_sdk(mode='normal', *, depth_mm=2000, wide_depth=False):
    sdk, state = sdk_fixture()
    b = example_bundle()
    camera = CameraGeometry.model_validate(b.calibration.model_dump(include=set(CameraGeometry.model_fields)))
    camera.distortion = [0.] * 5
    truth = example_pose() @ np.array(b.calibration.aircraft_from_camera)
    extr = np.eye(4); extr[:3, :3] = cv2.Rodrigues(np.array([.02, -.03, .01]))[0]; extr[:3, 3] = [.012, .002, -.003]
    rgb = tag_image(camera, b.survey, truth)
    moved = truth.copy(); moved[0, 3] += .15
    moved_image = tag_image(camera, b.survey, moved)
    intr = SimpleNamespace(width=640, height=480, fx=500., fy=500., ppx=320., ppy=240., coeffs=[0.] * 5, model='none')
    depth_intr = SimpleNamespace(width=640, height=480, fx=120. if wide_depth else 500., fy=120. if wide_depth else 500.,
        ppx=320., ppy=240., coeffs=[0.] * 5, model='none')
    cprofile = SimpleNamespace(get_intrinsics=lambda: intr)
    dprofile = SimpleNamespace(get_intrinsics=lambda: depth_intr, get_extrinsics_to=lambda p: SimpleNamespace(rotation=extr[:3, :3].ravel(order='F').tolist(), translation=extr[:3, 3].tolist()))
    depth = SimpleNamespace(profile=SimpleNamespace(as_video_stream_profile=lambda: dprofile), get_data=lambda: np.full((480, 640), depth_mm, np.uint16),
        get_timestamp=lambda: float(state['reads']) * 33., get_frame_timestamp_domain=lambda: 'hardware_clock')
    def color_data():
        if state['reads'] >= 34:
            if mode == 'movement': return moved_image
            if mode == 'loss': return np.zeros_like(rgb)
        return rgb
    color = SimpleNamespace(profile=SimpleNamespace(as_video_stream_profile=lambda: cprofile), get_data=color_data,
        get_timestamp=lambda: 0. if mode == 'clock' and state['reads'] >= 34 else float(state['reads']) * 33., get_frame_timestamp_domain=lambda: 'hardware_clock')
    sample = SimpleNamespace(get_depth_frame=lambda: depth, get_color_frame=lambda: color)
    pipeline = sdk.pipeline()
    def read(timeout):
        state['reads'] += 1
        if mode == 'timeout' and state['reads'] >= 33: raise RuntimeError('Injected mid-capture timeout')
        if mode == 'calibration' and state['reads'] >= 34: intr.fx = 501.
        return sample
    pipeline.wait_for_frames = read
    sdk.pipeline = lambda: pipeline
    template = Station(schema_version=1, scan_id='synthetic-auto', map_id=b.map.map_id, map_version=b.map.map_version, frame_id=b.map.frame_id,
        permitted=b.map.permitted, voxel_m=.2, uncertainty_m=.15, max_depth_m=4., map_from_depth=np.eye(4).tolist(), registration_evidence='Synthetic automatic-registration template', example=True)
    return sdk, state, b.survey, template, truth @ extr


def test_fake_capture_uses_rgb_registration_and_preserves_depth_extrinsic(tmp_path):
    sdk, state, survey, template, expected = automatic_sdk()
    scan = capture_d435(template, tmp_path / 'capture', frames=4, sdk=sdk, registration_survey=survey)
    assert scan.example and scan.camera_metadata['capture_environment'] == 'injected_test_sdk'
    assert np.linalg.norm(np.array(scan.frames[0].map_from_depth)[:3, 3] - expected[:3, 3]) < .04
    assert np.linalg.norm(np.array(scan.frames[0].map_from_depth)[:3, :3] - expected[:3, :3]) < .06
    assert all(f.map_from_depth == scan.frames[0].map_from_depth for f in scan.frames)
    assert all('registration SHA256' in f.registration_evidence for f in scan.frames)
    assert (tmp_path / 'capture' / 'registration.json').exists() and (tmp_path / 'capture' / 'scan.json').exists()
    assert state['stopped'] and not (tmp_path / 'capture' / 'INCOMPLETE.json').exists()


@pytest.mark.parametrize('mode', ['movement', 'loss', 'clock', 'calibration', 'timeout'])
def test_mid_capture_failure_preserves_partial_data_without_valid_manifest(tmp_path, mode):
    sdk, state, survey, template, _ = automatic_sdk(mode)
    output = tmp_path / 'capture'
    with pytest.raises((ValueError, RuntimeError)):
        capture_d435(template, output, frames=5, sdk=sdk, registration_survey=survey)
    assert state['stopped'] and (output / 'INCOMPLETE.json').exists()
    assert (output / 'frame-0000.npz').exists() and not (output / 'scan.json').exists()


def test_mid_capture_disk_error_preserves_previous_frames(tmp_path, monkeypatch):
    sdk, state, survey, template, _ = automatic_sdk()
    save, calls = np.savez_compressed, []
    def fail_second(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2: raise OSError('Injected disk failure')
        return save(*args, **kwargs)
    monkeypatch.setattr(np, 'savez_compressed', fail_second)
    with pytest.raises(OSError): capture_d435(template, tmp_path / 'capture', frames=4, sdk=sdk, registration_survey=survey)
    assert state['stopped'] and (tmp_path / 'capture' / 'frame-0000.npz').exists()
    assert (tmp_path / 'capture' / 'INCOMPLETE.json').exists() and not (tmp_path / 'capture' / 'scan.json').exists()


def test_automatic_capture_requires_compatible_policy_and_enough_frames(tmp_path):
    sdk, state, survey, template, _ = automatic_sdk()
    with pytest.raises(ValueError, match='requires a survey'):
        capture_d435(template, tmp_path / 'no-survey', sdk=sdk, registration_policy={})
    with pytest.raises(ValueError, match='Not enough'):
        capture_d435(template, tmp_path / 'few', frames=2, sdk=sdk, registration_survey=survey)
    assert state['stopped'] and not (tmp_path / 'few' / 'scan.json').exists()
