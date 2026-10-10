"""Offline registration through actual raster images, file checks and CLI."""
import hashlib
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import cv2
import numpy as np
import pytest

from ball_demo import cli
from ball_demo.map_io import CameraGeometry
from ball_demo.navigation_fixtures import example_bundle, example_pose
from ball_demo.registration import RegistrationInput, RegistrationResult, StationRegistrar, register_directory, rgb_geometry
from ball_demo.localization import CameraEstimate
from ball_demo.synthetic_navigation import tag_image


def input_fixture(root):
    root.mkdir()
    b = example_bundle()
    camera = CameraGeometry.model_validate(b.calibration.model_dump(include=set(CameraGeometry.model_fields)))
    truth = example_pose() @ np.array(b.calibration.aircraft_from_camera)
    extr = np.eye(4); extr[:3, :3] = cv2.Rodrigues(np.array([.02, -.04, .01]))[0]; extr[:3, 3] = [.012, -.006, .004]
    images = []
    for i in range(3):
        image = tag_image(camera, b.survey, truth, noise_std=1., seed=i)
        name = f'rgb-{i}.png'
        assert cv2.imwrite(str(root / name), image)
        images.append({'file': name, 'sha256': hashlib.sha256((root / name).read_bytes()).hexdigest(), 'timestamp_s': 1. + .1 * i})
    inputs = RegistrationInput(schema_version=1, camera=camera, survey=b.survey, color_from_depth=extr.tolist(), source='synthetic_estimate', images=images,
        station_template={'schema_version': 1, 'scan_id': 'synthetic-auto-station', 'map_id': b.map.map_id, 'map_version': b.map.map_version,
            'frame_id': b.map.frame_id, 'permitted': b.map.permitted.model_dump(), 'voxel_m': .2, 'uncertainty_m': .15,
            'max_depth_m': 4., 'map_from_depth': np.eye(4).tolist(), 'registration_evidence': 'Synthetic template, pending automatic registration', 'example': True})
    path = root / 'input.json'; path.write_text(inputs.model_dump_json(indent=2))
    return path, inputs, truth @ extr


def test_registration_cli_writes_registered_station_and_verified_completion(tmp_path, monkeypatch):
    path, inputs, expected = input_fixture(tmp_path / 'inputs')
    output = tmp_path / 'registered'
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'nav-register-d435', '--input', str(path), '--output', str(output)])
    cli.main()
    result = json.loads((output / 'registration.json').read_text())
    station = json.loads((output / 'station.json').read_text())
    complete = json.loads((output / 'complete.json').read_text())
    assert np.linalg.norm(np.array(station['map_from_depth'])[:3, 3] - expected[:3, 3]) < .04
    assert station['uncertainty_m'] == inputs.station_template.uncertainty_m  # Uniform map budget across stations.
    assert result['image_digest_kind'] == 'decoded_pixels_sha256' and not result['physical_acceptance']
    assert complete['source_manifest_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    for name, digest in complete['files'].items(): assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    assert complete['example'] and complete['physical_acceptance'] is False and not (output / 'INCOMPLETE.json').exists()
    with pytest.raises(FileExistsError): register_directory(path, output)


@pytest.mark.parametrize('failure', ['hash', 'decode', 'escape'])
def test_bad_registration_image_cannot_produce_station(tmp_path, failure):
    path, inputs, _ = input_fixture(tmp_path / 'inputs')
    image = path.parent / inputs.images[0].file
    if failure in ('hash', 'decode'):
        image.write_bytes(b'not a PNG')
        if failure == 'decode':
            inputs.images[0].sha256 = hashlib.sha256(image.read_bytes()).hexdigest()
            path.write_text(inputs.model_dump_json())
    else:
        outside = tmp_path / 'outside.png'; image.rename(outside); image.symlink_to(outside)
    with pytest.raises(ValueError): register_directory(path, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


@pytest.mark.parametrize('change', ['duplicate', 'time', 'survey', 'source', 'path', 'few', 'unknown'])
def test_input_manifest_rejects_bad_registration_evidence(tmp_path, change):
    _, inputs, _ = input_fixture(tmp_path / 'inputs')
    data = inputs.model_dump()
    if change == 'duplicate': data['images'][1]['file'] = data['images'][0]['file']
    if change == 'time': data['images'][1]['timestamp_s'] = data['images'][0]['timestamp_s']
    if change == 'survey': data['station_template']['frame_id'] = 'wrong-frame'
    if change == 'source': data['source'] = 'recorded_estimate'
    if change == 'path': data['images'][0]['file'] = '../secret.png'
    if change == 'few': data['images'] = data['images'][:2]
    if change == 'unknown': data['unsafe_output'] = True
    with pytest.raises(ValueError): RegistrationInput.model_validate(data)


@pytest.mark.parametrize('change', ['duplicate-tags', 'quality', 'movement'])
def test_registration_result_rejects_inconsistent_pose_evidence(tmp_path, change):
    path, _, _ = input_fixture(tmp_path / 'inputs')
    result, _ = register_directory(path, tmp_path / 'registered')
    data = result.model_dump()
    if change == 'duplicate-tags': data['tag_ids'] = [data['tag_ids'][0], data['tag_ids'][0]]
    elif change == 'quality': data['ambiguity_gap_px'] = 0.
    else: data['translation_spread_m'] = data['policy']['max_translation_m'] + .01
    with pytest.raises(ValueError): RegistrationResult.model_validate(data)


def test_station_registration_timestamp_and_rgb_distortion_profiles(tmp_path):
    path, inputs, _ = input_fixture(tmp_path / 'inputs')
    registrar = StationRegistrar(inputs.camera, inputs.survey, inputs.color_from_depth,
                                 inputs.policy, inputs.source)
    for record in inputs.images:
        image = cv2.imread(str(path.parent / record.file), cv2.IMREAD_COLOR)
        registrar.observe(image, record.timestamp_s)
    estimate = CameraEstimate(map_from_camera=np.eye(4).tolist(), uncertainty_m=.01,
                              reprojection_px=.1, ambiguity_gap_px=1., tag_ids=[0, 1])
    with pytest.raises(ValueError, match='Invalid registration timestamp'):
        registrar.observe_estimate(estimate, -1., 'a' * 64, 100.)

    base = dict(width=640, height=480, fx=500., fy=500., ppx=320., ppy=240., coeffs=[0.] * 5)
    assert rgb_geometry(SimpleNamespace(**base, model='distortion.none')).image_size == [640, 480]
    with pytest.raises(ValueError, match='Unsupported'):
        rgb_geometry(SimpleNamespace(**base, model='inverse_brown_conrady'))
    with pytest.raises(ValueError, match='Nonzero distortion'):
        rgb_geometry(SimpleNamespace(**{**base, 'coeffs': [.1, 0., 0., 0., 0.]}, model='none'))


@pytest.mark.parametrize('marker_write_fails', [False, True])
def test_registration_partial_output_is_marked_incomplete_on_write_error(tmp_path, monkeypatch, marker_write_fails):
    path, _, _ = input_fixture(tmp_path / 'inputs')
    output = tmp_path / 'registered'
    original_write = Path.write_text

    def injected_write(target, *args, **kwargs):
        if target.name == 'station.json' or (marker_write_fails and target.name == 'INCOMPLETE.json'):
            raise OSError('injected registration manifest write failure')
        return original_write(target, *args, **kwargs)

    monkeypatch.setattr(Path, 'write_text', injected_write)
    with pytest.raises(OSError, match='injected registration manifest'):
        register_directory(path, output)
    assert (output / 'registration.json').exists()
    assert (output / 'INCOMPLETE.json').exists() is not marker_write_fails
    assert not (output / 'complete.json').exists()
