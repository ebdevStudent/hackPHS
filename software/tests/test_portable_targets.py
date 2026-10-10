"""Generated-image tests for map-independent moving-tag pose and freshness."""
import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from ball_demo.localization import Observation, Timing, tag_points
from ball_demo.navigation_fixtures import example_bundle
from ball_demo.roster import LandingSite, Person, Roster
from ball_demo.target_tracking import (LandingPose, LandingTagTracker, LandingVision,
                                       RelativeTargetTracker, TargetPose, TargetVision,
                                       estimate_relative_landing_pose,
                                       estimate_relative_tag_pose)


@pytest.fixture
def setup_target():
    calibration = example_bundle().calibration
    person = Person(person_id='walker-1', display_name='Synthetic Walker', tag_family='tag36h11',
                    tag_id=7, tag_size_m=.2)
    rotation = np.array([2.6, .5, .1], dtype=float)
    translation = np.array([.2, -.1, 1.8], dtype=float)
    corners = cv2.projectPoints(tag_points(person.tag_size_m), rotation, translation,
                                np.asarray(calibration.intrinsics), np.asarray(calibration.distortion))[0].reshape(4, 2)
    observation = Observation(id=person.tag_id, corners=corners.tolist())
    pose = estimate_relative_tag_pose(observation, person, calibration, sequence=1,
        timing=Timing(host_received_s=10., exposure_s=10., provenance='synthetic'))
    return calibration, person, rotation, translation, observation, pose


def test_roster_strictly_binds_unique_enabled_apriltag_identity(setup_target):
    person = setup_target[1]
    roster = Roster(people=[person])
    assert roster.by_person_id('walker-1') == person
    assert roster.by_tag_id(7) == person
    with pytest.raises(ValidationError):
        Roster(people=[person, person])
    with pytest.raises(ValidationError):
        Roster(people=[person, person.model_copy(update={'person_id': 'walker-2'})])
    with pytest.raises(ValidationError):
        Person(person_id='bad', display_name='Bad', tag_family='tag36h11', tag_id=True, tag_size_m=.2)
    with pytest.raises(ValidationError):
        Person(person_id='bad', display_name='Bad', tag_family='tag36h11', tag_id=2, tag_size_m=.2, enabled='yes')


def test_relative_pose_recovers_range_and_aircraft_bearing_without_a_map(setup_target):
    _, person, _, translation, observation, pose = setup_target
    assert pose.person_id == person.person_id and pose.tag_id == person.tag_id
    assert pose.range_m == pytest.approx(np.linalg.norm(translation), abs=.01)
    assert pose.reprojection_px < .01
    assert pose.aircraft_from_tag[0][3] > 0
    assert pose.bearing_rad < 0  # Camera right is aircraft right for this mount.
    with pytest.raises(ValueError, match='does not match'):
        estimate_relative_tag_pose(Observation(id=8, corners=observation.corners), person,
            setup_target[0], sequence=2,
            timing=Timing(host_received_s=10., exposure_s=10., provenance='synthetic'))


def test_relative_target_tracker_requires_fresh_reacquisition_and_preserves_loss(setup_target):
    _, person, _, _, _, first = setup_target
    tracker = RelativeTargetTracker(person, reacquire_frames=3, max_age_s=.25)
    first.model_copy(update={'sequence': 0})
    for sequence in range(3):
        pose = first.model_copy(update={'sequence': sequence, 'timing': Timing(
            host_received_s=10. + sequence * .03, exposure_s=10. + sequence * .03, provenance='synthetic')})
        snapshot = tracker.update(pose, now_s=10. + sequence * .03)
    assert snapshot.state == 'tracking' and snapshot.pose is not None
    lost = tracker.update(None, now_s=10.1)
    assert lost.state == 'lost' and lost.loss_event and lost.pose is None
    for sequence in range(3, 6):
        pose = first.model_copy(update={'sequence': sequence, 'timing': Timing(
            host_received_s=10. + sequence * .03, exposure_s=10. + sequence * .03, provenance='synthetic')})
        snapshot = tracker.update(pose, now_s=10. + sequence * .03)
    assert snapshot.state == 'tracking' and snapshot.fresh_frames == 3


def test_stale_and_reordered_target_poses_never_refresh_tracker(setup_target):
    _, person, _, _, _, first = setup_target
    tracker = RelativeTargetTracker(person, reacquire_frames=1, max_age_s=.1)
    pose = first.model_copy(update={'sequence': 5})
    assert tracker.update(pose, now_s=10.).state == 'tracking'
    reordered = first.model_copy(update={'sequence': 4})
    assert tracker.update(reordered, now_s=10.02).state == 'tracking'
    assert tracker._snapshot().reason == 'Out-of-order observation ignored'
    stale = first.model_copy(update={'sequence': 6, 'timing': Timing(
        host_received_s=11., exposure_s=10., provenance='synthetic')})
    result = tracker.update(stale, now_s=11.)
    assert result.state == 'lost' and result.loss_event and result.pose is None


def test_target_vision_detects_rendered_tag_and_reports_blank_frame_loss(setup_target):
    calibration, person, rotation, translation, _, _ = setup_target
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), person.tag_id, 300)
    corners = cv2.projectPoints(tag_points(person.tag_size_m), rotation, translation,
                                np.asarray(calibration.intrinsics), np.asarray(calibration.distortion))[0].reshape(4, 2)
    image = np.full((480, 640), 255, dtype=np.uint8)
    transform = cv2.getPerspectiveTransform(np.array([[0, 0], [299, 0], [299, 299], [0, 299]], np.float32),
                                            corners.astype(np.float32))
    warped = cv2.warpPerspective(marker, transform, (640, 480), borderValue=255)
    image = np.minimum(image, warped)
    vision = TargetVision(person, calibration, delay_bound_s=.08, reacquire_frames=1,
                          max_age_s=.25, max_reprojection_px=3.)
    tracked = vision.process(image, sequence=1, captured_s=10., received_s=10.01)
    assert tracked.state == 'tracking' and tracked.pose is not None
    assert tracked.pose.source == 'recorded_estimate'
    missed = vision.process(np.full_like(image, 255), sequence=2, captured_s=10.03, received_s=10.04)
    assert missed.state == 'lost' and missed.loss_event and missed.pose is None


def test_target_pose_contract_rejects_inconsistent_range_and_future_timing(setup_target):
    pose = setup_target[-1].model_dump()
    pose['range_m'] += .5
    with pytest.raises(ValidationError, match='range_m'):
        TargetPose.model_validate(pose)
    timing = dict(host_received_s=2., exposure_s=3., provenance='synthetic')
    with pytest.raises(ValidationError):
        Timing.model_validate(timing)


def _shift_landing_pose(pose, *, dx=0., dy=0., heading=0., sequence=None,
                        reprojection=None, ambiguity=None, timing=None):
    payload = pose.model_dump()
    tag = np.asarray(payload['aircraft_from_tag'], dtype=float)
    tag[:3, 3] += [dx, dy, 0.]
    pad = tag @ np.linalg.inv(np.asarray(payload['pad_from_tag'], dtype=float))
    if heading:
        c, s = np.cos(heading), np.sin(heading)
        pad[:3, :3] = np.asarray([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])
        tag[:3, :3] = pad[:3, :3] @ np.asarray(payload['pad_from_tag'])[:3, :3]
    x, y = pad[0, 3], pad[1, 3]
    payload.update(aircraft_from_tag=tag.tolist(), aircraft_from_pad=pad.tolist(),
                   range_m=float(np.hypot(x, y)), bearing_rad=float(np.arctan2(y, x)),
                   pad_heading_rad=float(np.arctan2(pad[1, 0], pad[0, 0])))
    if sequence is not None:
        payload['sequence'] = sequence
    if reprojection is not None:
        payload['reprojection_px'] = reprojection
    if ambiguity is not None:
        payload['ambiguity_gap_px'] = ambiguity
    if timing is not None:
        payload['timing'] = timing.model_dump()
    return LandingPose.model_validate(payload)


def test_relative_pose_rejects_bad_thresholds_geometry_and_aircraft_rear(setup_target):
    calibration, person, _, _, observation, _ = setup_target
    timing = Timing(host_received_s=10., exposure_s=10., provenance='synthetic')
    with pytest.raises(ValueError, match='sequence'):
        estimate_relative_tag_pose(observation, person, calibration, sequence=True, timing=timing)
    with pytest.raises(ValueError, match='source'):
        estimate_relative_tag_pose(observation, person, calibration, sequence=2, timing=timing,
                                   source='physical')
    with pytest.raises(ValueError, match='Ambiguity threshold'):
        estimate_relative_tag_pose(observation, person, calibration, sequence=2, timing=timing,
                                   min_ambiguity_gap_px=float('nan'))
    with pytest.raises(ValueError, match='Reprojection limit'):
        estimate_relative_tag_pose(observation, person, calibration, sequence=2, timing=timing,
                                   max_reprojection_px=0.)
    outside = Observation(id=person.tag_id,
        corners=[[x + 800., y + 800.] for x, y in observation.corners])
    with pytest.raises(ValueError, match='outside the calibrated image'):
        estimate_relative_tag_pose(outside, person, calibration, sequence=2, timing=timing)
    with pytest.raises(ValueError, match='ambiguous'):
        estimate_relative_tag_pose(observation, person, calibration, sequence=2, timing=timing,
                                   min_ambiguity_gap_px=1e7)

    data = calibration.model_dump()
    data['aircraft_from_camera'] = [[-1., 0., 0., 0.], [0., 1., 0., 0.],
                                    [0., 0., -1., 0.], [0., 0., 0., 1.]]
    rear_calibration = type(calibration).model_validate(data)
    with pytest.raises(ValueError, match='not in front'):
        estimate_relative_tag_pose(observation, person, rear_calibration, sequence=2, timing=timing)


def test_relative_tracker_rejects_invalid_time_identity_stale_and_unknown_age(setup_target):
    _, person, _, _, _, pose = setup_target
    tracker = RelativeTargetTracker(person, reacquire_frames=1, loss_after_misses=2)
    for kwargs in ({'reacquire_frames': 0}, {'loss_after_misses': True}, {'max_age_s': float('inf')}):
        with pytest.raises(ValueError):
            RelativeTargetTracker(person, **kwargs)
    with pytest.raises(ValueError, match='now_s'):
        tracker.update(None, now_s=float('nan'))

    fresh = pose.model_copy(update={'sequence': 1})
    assert tracker.update(fresh, now_s=10.).state == 'tracking'
    assert tracker.update(None, now_s=10.01).state == 'tracking'  # configured miss hold
    loss = tracker.update(None, now_s=10.02)
    assert loss.state == 'lost' and loss.loss_event is True
    wrong_identity = TargetPose.model_validate({**pose.model_dump(), 'person_id': 'someone-else', 'sequence': 2})
    assert tracker.update(wrong_identity, now_s=10.).state == 'lost'
    unknown_age = TargetPose.model_validate({**pose.model_dump(), 'sequence': 3,
        'timing': Timing(host_received_s=10., provenance='host_read').model_dump()})
    assert 'delay upper bound' in tracker.update(unknown_age, now_s=10.).reason
    future = pose.model_copy(update={'sequence': 4, 'timing': Timing(
        host_received_s=10., exposure_s=10., provenance='synthetic')})
    assert tracker.update(future, now_s=9.8).state == 'lost'
    reset = tracker.reset('new camera session')
    assert reset.state == 'acquiring' and reset.sequence is None and reset.reason == 'new camera session'


def test_target_vision_host_read_timing_duplicate_and_pose_failure(setup_target):
    calibration, person, rotation, translation, _, _ = setup_target
    marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(
        cv2.aruco.DICT_APRILTAG_36h11), person.tag_id, 250)
    corners = cv2.projectPoints(tag_points(person.tag_size_m), rotation, translation,
                                np.asarray(calibration.intrinsics), np.asarray(calibration.distortion))[0].reshape(4, 2)
    def render():
        image = np.full((480, 640), 255, dtype=np.uint8)
        source_corners = np.array([[0, 0], [249, 0], [249, 249], [0, 249]], np.float32)
        transform = cv2.getPerspectiveTransform(source_corners, corners.astype(np.float32))
        tag = cv2.warpPerspective(marker, transform, (640, 480), borderValue=255)
        image = np.minimum(image, tag)
        return image

    vision = TargetVision(person, calibration, delay_bound_s=.08, reacquire_frames=1,
                          max_reprojection_px=3.)
    host_read = vision.process(render(), sequence=1, received_s=10.)
    assert host_read.state == 'tracking' and host_read.pose.timing.provenance == 'host_read'
    invalid_time = pytest.raises(ValueError, match='capture/receipt')
    with invalid_time:
        vision.process(render(), sequence=2, captured_s=11., received_s=10.)
    with pytest.raises(ValueError, match='sequence'):
        vision.process(render(), sequence=True, received_s=10.)

    strict = TargetVision(person, calibration, delay_bound_s=.08, reacquire_frames=1,
                          max_reprojection_px=1e-6)
    failed = strict.process(render(), sequence=1, captured_s=10., received_s=10.)
    assert failed.state == 'lost' and 'reprojection error' in failed.reason
    duplicate = TargetVision(person, calibration, delay_bound_s=.08, reacquire_frames=1)
    pair = np.full((480, 640), 255, dtype=np.uint8)
    square_marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(
        cv2.aruco.DICT_APRILTAG_36h11), person.tag_id, 160)
    pair[100:260, 60:220] = square_marker
    pair[100:260, 380:540] = square_marker
    assert duplicate.process(pair, sequence=1, captured_s=10., received_s=10.).state == 'lost'


def test_landing_tracker_enforces_fresh_quality_geometry_and_stability(setup_target):
    calibration, person, _, _, observation, _ = setup_target
    site = LandingSite(site_id='pad-a', display_name='Synthetic pad', tag_family='tag36h11',
        tag_id=person.tag_id, tag_size_m=person.tag_size_m, width_m=.6, length_m=.5,
        approach_tolerance_rad=3.14)
    timing = Timing(host_received_s=10., exposure_s=10., provenance='synthetic')
    pose = estimate_relative_landing_pose(observation, site, calibration, sequence=1, timing=timing)
    for kwargs in ({'max_age_s': 0}, {'max_range_m': float('nan')}, {'max_bearing_rad': 0},
                   {'max_reprojection_px': 0}, {'min_ambiguity_gap_px': -1},
                   {'stable_range_delta_m': 0}, {'reacquire_frames': False}):
        with pytest.raises(ValueError):
            LandingTagTracker(site, **kwargs)
    tracker = LandingTagTracker(site, reacquire_frames=2, max_range_m=5., max_bearing_rad=.8)
    assert tracker.update(None, now_s=10.).state == 'lost'
    with pytest.raises(ValueError, match='now_s'):
        tracker.update(None, now_s=float('inf'))
    assert tracker.update(pose, now_s=10.).state == 'reacquiring'
    assert tracker.update(pose, now_s=10.01).reason == 'Out-of-order landing observation ignored'
    stable = _shift_landing_pose(pose, sequence=2, timing=Timing(
        host_received_s=10.03, exposure_s=10.03, provenance='synthetic'))
    assert tracker.update(stable, now_s=10.03).state == 'approaching'

    movement_tracker = LandingTagTracker(site, reacquire_frames=3, max_range_m=5., max_bearing_rad=.8,
                                        stable_range_delta_m=.1)
    assert movement_tracker.update(pose, now_s=10.).state == 'reacquiring'
    moved = _shift_landing_pose(pose, dx=.4, sequence=2,
        timing=Timing(host_received_s=10.03, exposure_s=10.03, provenance='synthetic'))
    assert movement_tracker.update(moved, now_s=10.03).fresh_frames == 1
    quality_tracker = LandingTagTracker(site, max_range_m=5., max_bearing_rad=.8,
                                        max_reprojection_px=1.)
    poor = _shift_landing_pose(pose, sequence=2, reprojection=2., ambiguity=0.)
    assert 'quality' in quality_tracker.update(poor, now_s=10.).reason
    geometry_tracker = LandingTagTracker(site, max_range_m=.1, max_bearing_rad=.8)
    assert 'approach geometry' in geometry_tracker.update(pose, now_s=10.).reason

    unknown = _shift_landing_pose(pose, sequence=3, timing=Timing(
        host_received_s=10., provenance='host_read'))
    assert 'delay upper bound' in tracker.update(unknown, now_s=10.).reason
    stale = _shift_landing_pose(pose, sequence=4, timing=Timing(
        host_received_s=11., exposure_s=10., provenance='synthetic'))
    assert 'stale' in tracker.update(stale, now_s=11.).reason
    wrong = LandingPose.model_validate({**pose.model_dump(), 'site_id': 'another-pad', 'sequence': 5})
    assert 'identity' in tracker.update(wrong, now_s=10.).reason


def test_landing_vision_detects_relative_pad_pose_and_handles_missing_frames(setup_target):
    calibration, person, rotation, translation, _, _ = setup_target
    site = LandingSite(site_id='pad-a', display_name='Synthetic pad', tag_family='tag36h11',
        tag_id=person.tag_id, tag_size_m=person.tag_size_m, width_m=.6, length_m=.5,
        approach_tolerance_rad=3.14)
    marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(
        cv2.aruco.DICT_APRILTAG_36h11), site.tag_id, 300)
    corners = cv2.projectPoints(tag_points(site.tag_size_m), rotation, translation,
                                np.asarray(calibration.intrinsics), np.asarray(calibration.distortion))[0].reshape(4, 2)
    transform = cv2.getPerspectiveTransform(np.array([[0, 0], [299, 0], [299, 299], [0, 299]], np.float32),
                                            corners.astype(np.float32))
    image = np.minimum(np.full((480, 640), 255, dtype=np.uint8),
                       cv2.warpPerspective(marker, transform, (640, 480), borderValue=255))
    vision = LandingVision(site, calibration, delay_bound_s=.08, reacquire_frames=1)
    pose = vision.process(image, sequence=1, captured_s=10., received_s=10.01)
    assert pose.state == 'approaching' and pose.pose.site_id == site.site_id
    assert pose.pose.timing.provenance == 'exposure_monotonic'
    missing = vision.process(np.full_like(image, 255), sequence=2, captured_s=10.02, received_s=10.03)
    assert missing.state == 'lost'
    host_read = vision.process(image, sequence=3, received_s=10.04)
    assert host_read.state == 'approaching' and host_read.pose.timing.provenance == 'host_read'
    with pytest.raises(ValueError, match='sequence'):
        vision.process(image, sequence=True, received_s=10.05)
    with pytest.raises(ValueError, match='capture/receipt'):
        vision.process(image, sequence=4, captured_s=11., received_s=10.05)


def test_landing_site_pose_applies_pad_transform_and_requires_stable_fresh_tag(setup_target):
    calibration, person, _, _, observation, _ = setup_target
    site = LandingSite(site_id='pad-a', display_name='Synthetic pad', tag_family='tag36h11',
        tag_id=person.tag_id, tag_size_m=person.tag_size_m, width_m=.6, length_m=.5,
        approach_tolerance_rad=3.14,
        pad_from_tag=[[1., 0., 0., .05], [0., 1., 0., -.02],
                      [0., 0., 1., 0.], [0., 0., 0., 1.]])
    tracker = LandingTagTracker(site, reacquire_frames=3, max_range_m=5., max_bearing_rad=.8)
    result = None
    for sequence in range(3):
        pose = estimate_relative_landing_pose(observation, site, calibration, sequence=sequence,
            timing=Timing(host_received_s=10. + sequence * .03, exposure_s=10. + sequence * .03,
                          provenance='synthetic'))
        expected = np.asarray(pose.aircraft_from_tag) @ np.linalg.inv(np.asarray(site.pad_from_tag))
        assert np.allclose(pose.aircraft_from_pad, expected)
        result = tracker.update(pose, now_s=10. + sequence * .03)
    assert result.state == 'approaching' and result.pose is not None and result.fresh_frames == 3
    lost = tracker.update(None, now_s=10.1)
    assert lost.state == 'lost' and lost.loss_event and lost.pose is None


def test_landing_site_and_pad_pose_contract_reject_bad_geometry(setup_target):
    calibration, person, _, _, observation, _ = setup_target
    with pytest.raises(ValidationError):
        LandingSite(site_id='pad-a', display_name='Pad', tag_family='tag36h11', tag_id=10,
            tag_size_m=.2, width_m=.6, length_m=.6,
            pad_from_tag=[[2., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
    site = LandingSite(site_id='pad-a', display_name='Pad', tag_family='tag36h11',
        tag_id=person.tag_id, tag_size_m=person.tag_size_m, width_m=.6, length_m=.6)
    with pytest.raises(ValueError, match='does not match'):
        estimate_relative_landing_pose(Observation(id=8, corners=observation.corners), site,
            calibration, sequence=1,
            timing=Timing(host_received_s=10., exposure_s=10., provenance='synthetic'))


def test_duplicate_pose_cannot_hold_tracking_past_its_exposure_deadline(setup_target):
    calibration, person, _, _, observation, pose = setup_target
    target = RelativeTargetTracker(person, reacquire_frames=1, max_age_s=.1)
    target.update(pose, now_s=10.)
    lost = target.update(pose, now_s=10.101)
    assert lost.state == 'lost' and lost.loss_event and lost.pose is None
    site = LandingSite(site_id='pad', display_name='Pad', tag_family='tag36h11', tag_id=7, tag_size_m=.2,
                       width_m=.5, length_m=.5, approach_tolerance_rad=3.14)
    pad = estimate_relative_landing_pose(observation, site, calibration, sequence=1, timing=pose.timing)
    landing = LandingTagTracker(site, reacquire_frames=1, max_age_s=.1)
    assert landing.update(pad, now_s=10.).state == 'approaching'
    lost = landing.update(pad, now_s=10.101)
    assert lost.state == 'lost' and lost.loss_event and lost.pose is None


@pytest.mark.parametrize('field', ['bearing_rad', 'aircraft_from_pad', 'range_m', 'pad_heading_rad'])
def test_pose_contracts_reject_inconsistent_aircraft_geometry(setup_target, field):
    calibration, person, _, _, observation, pose = setup_target
    if field == 'bearing_rad':
        with pytest.raises(ValidationError, match='bearing_rad'):
            TargetPose.model_validate({**pose.model_dump(), 'bearing_rad': pose.bearing_rad + .1})
    site = LandingSite(site_id='pad', display_name='Pad', tag_family='tag36h11', tag_id=7, tag_size_m=.2, width_m=.5, length_m=.5)
    data = estimate_relative_landing_pose(observation, site, calibration, sequence=1, timing=pose.timing).model_dump()
    if field == 'aircraft_from_pad':
        data[field][0][3] += .1
    else:
        data[field] += .1
    with pytest.raises(ValidationError):
        LandingPose.model_validate(data)


def test_pose_solver_rejects_degenerate_and_behind_camera_solutions(setup_target, monkeypatch):
    from ball_demo.target_tracking import _solve_relative_tag
    calibration, _, _, _, observation, _ = setup_target
    def solve(**kwargs):
        return _solve_relative_tag(observation, kwargs.get('tag_id', 7), kwargs.get('size', .2), calibration,
                                  min_ambiguity_gap_px=.4, max_reprojection_px=3.)
    with pytest.raises(ValueError, match='tag_id'):
        solve(tag_id=7.)
    with pytest.raises(ValueError, match='tag size'):
        solve(size=True)
    monkeypatch.setattr(cv2, 'solvePnPGeneric', lambda *a, **k: (0, (), (), ()))
    with pytest.raises(ValueError, match='could not be solved'):
        solve()
    monkeypatch.setattr(cv2, 'solvePnPGeneric', lambda *a, **k:
                        (1, [np.zeros(3)], [np.array([0., 0., -1.])], [0.]))
    with pytest.raises(ValueError, match='positive-depth'):
        solve()


@pytest.mark.parametrize('landing', [False, True])
def test_pose_failure_preserves_loss_event_and_constructor_rejects_unknown_delay(setup_target, monkeypatch, landing):
    import ball_demo.target_tracking as module
    from ball_demo.portable_demo import render_tag
    calibration, person, _, _, _, _ = setup_target
    selected = LandingSite(site_id='pad', display_name='Pad', tag_family='tag36h11', tag_id=7, tag_size_m=.2,
                           width_m=.5, length_m=.5, approach_tolerance_rad=3.14) if landing else person
    cls = LandingVision if landing else TargetVision
    with pytest.raises(ValueError, match='delay bound'):
        cls(selected, calibration, delay_bound_s=0)
    vision = cls(selected, calibration, delay_bound_s=.01, reacquire_frames=1)
    image = render_tag(calibration, 7, (.2, -.1, 1.8))
    assert vision.process(image, sequence=1, received_s=10.).pose is not None
    def fail(*args, **kwargs):
        raise ValueError('Pose quality rejected')
    monkeypatch.setattr(module, 'estimate_relative_landing_pose' if landing else 'estimate_relative_tag_pose', fail)
    lost = vision.process(image, sequence=2, received_s=10.03)
    assert lost.state == 'lost' and lost.loss_event and lost.pose is None
    assert lost.reason == 'Pose quality rejected'


def test_landing_estimator_rejects_sequence_source_and_pad_center_behind_aircraft(setup_target):
    calibration, _, _, _, observation, pose = setup_target
    site = LandingSite(site_id='pad', display_name='Pad', tag_family='tag36h11', tag_id=7, tag_size_m=.2, width_m=.5, length_m=.5)
    for kwargs in ({'sequence': True}, {'source': 'physical'}):
        with pytest.raises(ValueError):
            estimate_relative_landing_pose(observation, site, calibration,
                                           timing=pose.timing, **({'sequence': 1} | kwargs))
    data = site.model_dump()
    # A measured tag offset can place the inferred pad behind the aircraft.
    tag = np.asarray(pose.aircraft_from_tag)
    data['pad_from_tag'] = np.eye(4).tolist()
    data['pad_from_tag'][0][3] = float((tag[:3, :3].T @ np.array([10., 0., 0.]))[0])
    data['pad_from_tag'][1][3] = float((tag[:3, :3].T @ np.array([10., 0., 0.]))[1])
    data['pad_from_tag'][2][3] = float((tag[:3, :3].T @ np.array([10., 0., 0.]))[2])
    with pytest.raises(ValueError, match='pad center'):
        estimate_relative_landing_pose(observation, data, calibration, sequence=1, timing=pose.timing)
