"""Independent numeric/ray geometry checks; these also run without OpenCV.

Passing this subset alone does not establish image inference or Python 3.13.
"""
import copy
import hashlib

import numpy as np
import pytest

from ball_demo.localization import CameraEstimate
from ball_demo.map_io import CameraGeometry, Survey
from ball_demo.registration import RegistrationPolicy, RegistrationResult, StationRegistrar
from ball_demo.synthetic_navigation import depth_image


def camera():
    return CameraGeometry(image_size=[64, 48], intrinsics=[[50., 0., 32.], [0., 50., 24.], [0., 0., 1.]], distortion_model='opencv_brown', distortion=[0.] * 5)


def survey():
    return Survey(schema_version=1, survey_id='synthetic-survey', map_id='synthetic-room', map_version=1, frame_id='world', units='m', family='tag36h11',
        tags=[{'id': i, 'size_m': .3, 'map_from_tag': np.eye(4).tolist()} for i in range(2)], evidence='Invented numeric fixture', example=True)


def rotation(axis, angle):
    # Rodrigues independently expanded here, without using application transforms.
    axis = np.array(axis, float); axis /= np.linalg.norm(axis)
    x, y, z = axis
    skew = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
    return np.eye(3) * np.cos(angle) + (1 - np.cos(angle)) * np.outer(axis, axis) + np.sin(angle) * skew


def estimate(transform=None, **changes):
    data = dict(map_from_camera=(np.eye(4) if transform is None else transform).tolist(), uncertainty_m=.025, reprojection_px=.1, ambiguity_gap_px=1., tag_ids=[0, 1])
    data.update(changes)
    return CameraEstimate(**data)


@pytest.mark.parametrize('seed', range(12))
def test_rgb_registration_places_depth_points_in_independent_world_coordinates(seed):
    rng = np.random.default_rng(seed)
    rgb, extr = np.eye(4), np.eye(4)
    rgb[:3, :3] = rotation(rng.normal(size=3), .3)
    extr[:3, :3] = rotation(rng.normal(size=3), .15)
    rgb[:3, 3], extr[:3, 3] = rng.normal(size=3), rng.normal(0, .02, 3)
    reg = StationRegistrar(camera(), survey(), extr)
    for i in range(3): result = reg.observe_estimate(estimate(rgb), 1. + i * .1, hashlib.sha256(str(i).encode()).hexdigest(), 100.)
    points = rng.normal(size=(10, 3))
    expected = (points @ extr[:3, :3].T + extr[:3, 3]) @ rgb[:3, :3].T + rgb[:3, 3]
    actual = points @ np.array(result.map_from_depth)[:3, :3].T + np.array(result.map_from_depth)[:3, 3]
    assert np.allclose(expected, actual, atol=1e-10)
    assert not result.physical_acceptance and result.uncertainty_provisional and result.example
    bad = result.model_dump(); bad['map_from_depth'] = (rgb @ np.linalg.inv(extr)).tolist()
    with pytest.raises(ValueError, match='direction'): RegistrationResult.model_validate(bad)


@pytest.mark.parametrize('change', ['tags', 'unknown', 'residual', 'ambiguity', 'uncertainty', 'translation', 'rotation', 'time', 'spread', 'digest'])
def test_station_acquisition_resets_after_bad_quality_motion_or_clock(change):
    reg = StationRegistrar(camera(), survey(), np.eye(4))
    reg.observe_estimate(estimate(), 1., 'a' * 64, 100.)
    bad = estimate(); timestamp, span, digest = 1.1, 100., 'b' * 64
    if change == 'tags': bad.tag_ids = [0]
    if change == 'unknown': bad.tag_ids = [0, 99]
    if change == 'residual': bad.reprojection_px = 4.
    if change == 'ambiguity': bad.ambiguity_gap_px = .1
    if change == 'uncertainty': bad.uncertainty_m = .2
    if change == 'translation': bad.map_from_camera[0][3] = .03
    if change == 'rotation': bad.map_from_camera = np.block([[rotation([0, 0, 1], .1), np.zeros((3, 1))], [np.zeros((1, 3)), np.ones((1, 1))]]).tolist()
    if change == 'time': timestamp = 1.
    if change == 'spread': span = 5.
    if change == 'digest': digest = 'invalid'
    with pytest.raises(ValueError): reg.observe_estimate(bad, timestamp, digest, span)
    assert reg.result() is None and not reg.samples


@pytest.mark.parametrize('field,value', [('stable_frames', True), ('min_tags', 1), ('max_translation_m', float('nan')), ('unknown', 2)])
def test_registration_policy_is_strict(field, value):
    with pytest.raises(ValueError): RegistrationPolicy.model_validate({field: value})


def test_registration_report_rejects_provenance_and_incomplete_evidence():
    reg = StationRegistrar(camera(), survey(), np.eye(4))
    for i in range(3): reg.observe_estimate(estimate(), float(i), 'a' * 64, 100.)
    for field, value in [('physical_acceptance', True), ('source', 'vision_estimate'), ('timestamps_s', [0., 0., 2.]), ('image_sha256', ['a' * 64] * 2)]:
        data = reg.result().model_dump(); data[field] = value
        with pytest.raises(ValueError): RegistrationResult.model_validate(data)
    with pytest.raises(ValueError): StationRegistrar(camera(), survey(), np.eye(4), source='vision_estimate')


def test_registered_station_requires_shared_uncertainty_budget_and_matching_survey():
    from ball_demo.mapping import Station
    reg = StationRegistrar(camera(), survey(), np.eye(4))
    template = Station(schema_version=1, scan_id='synthetic-station', map_id='synthetic-room', map_version=1, frame_id='world',
        permitted={'minimum': [-2., -2., -2.], 'maximum': [2., 2., 2.]}, voxel_m=.2, uncertainty_m=.15, max_depth_m=4.,
        map_from_depth=np.eye(4).tolist(), registration_evidence='Synthetic template', example=True)
    with pytest.raises(ValueError): reg.station(template)
    for i in range(3): reg.observe_estimate(estimate(), float(i), 'a' * 64, 100.)
    actual = reg.station(template)
    assert actual.uncertainty_m == .15 and 'provisional' in actual.registration_evidence
    template.uncertainty_m = .01
    with pytest.raises(ValueError, match='uncertainty'): reg.station(template)
    template.uncertainty_m = .15; template.frame_id = 'other-frame'
    with pytest.raises(ValueError, match='mismatch'): reg.station(template)
    data = reg.result().model_dump(); data['uncertainty_m'] = 0.
    with pytest.raises(ValueError, match='omits'): RegistrationResult.model_validate(data)


def test_independent_depth_rays_observe_known_planes_and_changed_camera_pose():
    wall = {'minimum': [-10., -10., 2.], 'maximum': [10., 10., 2.1]}
    first = depth_image(camera(), np.eye(4), [wall])
    assert np.allclose(first, 2.)
    shifted = np.eye(4); shifted[2, 3] = .5
    assert np.allclose(depth_image(camera(), shifted, [wall]), 1.5)
    assert not depth_image(camera(), np.eye(4), [wall], max_depth_m=1.).any()
    assert not depth_image(camera(), np.eye(4), []).any()
    # A nearby obstacle changes precisely the rays through its angular footprint.
    obstacle = {'minimum': [-.1, -.1, 1.], 'maximum': [.1, .1, 1.2]}
    image = depth_image(camera(), np.eye(4), [wall, obstacle])
    assert image[24, 32] == 1. and image[0, 0] == 2.


@pytest.mark.parametrize('bad', [True, 0, -1., float('nan')])
def test_invalid_synthetic_depth_range(bad):
    with pytest.raises(ValueError): depth_image(camera(), np.eye(4), [], bad)


def test_camera_geometry_keeps_existing_calibration_shape_and_rejects_distorted_depth():
    from ball_demo.navigation_fixtures import example_bundle
    c = example_bundle().calibration
    with pytest.raises(ValueError, match='rectified'): depth_image(c, np.eye(4), [])
    data = camera().model_dump(); data['intrinsics'][0][0] = -1.
    with pytest.raises(ValueError): CameraGeometry.model_validate(data)
