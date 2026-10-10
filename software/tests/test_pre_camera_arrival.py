"""Arrival and mission contracts against independently constructed pose states."""
import copy

import numpy as np
import pytest

from ball_demo.arrival import ArrivalPolicy, ArrivalTracker
from ball_demo.localization import Pose, Timing
from ball_demo.mission import Mission, MissionRunner
from ball_demo.navigation import Advisory
from ball_demo.navigation_fixtures import example_bundle


def pose(sequence, t, position=(1., 1., 1.), uncertainty=.02, yaw=0.):
    transform = np.eye(4)
    transform[:3, :3] = [[np.cos(yaw), -np.sin(yaw), 0.], [np.sin(yaw), np.cos(yaw), 0.], [0., 0., 1.]]
    transform[:3, 3] = position
    return Pose(sequence=sequence, bundle_id='synthetic-bundle', map_id='synthetic-map', map_version=1, frame_id='world', calibration_id='synthetic-calibration',
        source='synthetic_estimate', timing=Timing(host_received_s=t, exposure_s=t, provenance='synthetic'), map_from_aircraft=transform.tolist(), uncertainty_m=uncertainty,
        reprojection_px=.1, ambiguity_gap_px=1., tag_ids=[0, 1])


def test_only_distinct_fresh_observations_advance_arrival():
    tracker = ArrivalTracker()
    first = pose(0, 1.)
    assert tracker.update(first, [1., 1., 1.], 1.)['status'] == 'dwelling'
    for now in (1.05, 1.1, 1.2):
        state = tracker.update(first, [1., 1., 1.], now)
        assert state['fresh_frames'] == 1 and state['elapsed_s'] == 0.
    assert not tracker.update(pose(1, 1.1), [1., 1., 1.], 1.1)['estimated_arrival']
    state = tracker.update(pose(2, 1.2), [1., 1., 1.], 1.2)
    assert state['estimated_arrival'] and state['uncertainty_provisional'] and not state['physical_acceptance']


@pytest.mark.parametrize('position,uncertainty', [((1., 1., 1.), .12), ((1.09, 1., 1.), .02), ((1.2, 1., 1.), .01)])
def test_uncertain_or_outside_goal_cannot_arrive(position, uncertainty):
    tracker = ArrivalTracker()
    for seq in range(10):
        state = tracker.update(pose(seq, 1. + seq * .05, position, uncertainty), [1., 1., 1.], 1. + seq * .05)
        assert state['status'] == 'approaching' and not state['estimated_arrival']


def test_boundary_departure_change_and_gap_reset_dwell():
    tracker = ArrivalTracker(ArrivalPolicy(radius_m=.12))
    tracker.update(pose(0, 1.), [1., 1., 1.], 1.)
    tracker.update(pose(1, 1.1, (1.2, 1., 1.)), [1., 1., 1.], 1.1)
    assert tracker.update(pose(2, 1.2), [1., 1., 1.], 1.2)['fresh_frames'] == 1
    assert tracker.update(pose(3, 1.3), [1.05, 1., 1.], 1.3)['fresh_frames'] == 1
    changed = pose(4, 1.4); changed.bundle_id = 'other-bundle'
    assert tracker.update(changed, [1.05, 1., 1.], 1.4)['fresh_frames'] == 1
    changed = pose(5, 1.8); changed.bundle_id = 'other-bundle'
    assert tracker.update(changed, [1.05, 1., 1.], 1.8)['fresh_frames'] == 1


def test_heading_wraparound_and_wrong_heading():
    tracker = ArrivalTracker()
    for i in range(3): state = tracker.update(pose(i, 1. + i * .1, yaw=-np.pi + .01), [1., 1., 1.], 1. + i * .1, heading_rad=np.pi - .01)
    assert state['estimated_arrival']
    state = tracker.update(pose(3, 1.3, yaw=0.), [1., 1., 1.], 1.3, heading_rad=np.pi - .01)
    assert state['status'] == 'approaching'


@pytest.mark.parametrize('bad', ['stale', 'future', 'reorder', 'duplicate', 'changed_duplicate', 'exposure', 'goal', 'heading', 'clock'])
def test_bad_arrival_inputs_reset_and_raise(bad):
    tracker = ArrivalTracker()
    tracker.update(pose(2, 1.), [1., 1., 1.], 1.)
    candidate, goal, now, heading = pose(3, 1.1), [1., 1., 1.], 1.1, None
    if bad == 'stale': now = 2.
    if bad == 'future': now = 1.
    if bad == 'reorder': candidate.sequence = 1
    if bad == 'duplicate': candidate.sequence = 2
    if bad == 'changed_duplicate':
        candidate = pose(2, 1., (1.05, 1., 1.))
    if bad == 'exposure': candidate.timing = Timing(host_received_s=1.1, exposure_s=1., provenance='synthetic')
    if bad == 'goal': goal = [True, 1., 1.]
    if bad == 'heading': heading = float('nan')
    if bad == 'clock': now = True
    with pytest.raises(ValueError): tracker.update(candidate, goal, now, heading)
    assert tracker.snapshot()['status'] == 'waiting'


def mission_data():
    b = example_bundle()
    return dict(schema_version=1, mission_id='synthetic-inspection', map_id=b.map.map_id, map_version=b.map.map_version, frame_id=b.map.frame_id,
        survey_id=b.survey.survey_id, example=True, targets=[dict(target_id='machine-a', name='Synthetic inspection A', tag_id=0, viewing_position_m=[1.7, .8, 1.2], heading_rad=1.57)])


def test_mission_contract_and_compatible_viewing_position():
    mission = Mission.model_validate(mission_data()).validate_bundle(example_bundle())
    assert not mission.physical_output and mission.control_authority == 'advisory_only'
    assert Mission.model_validate_json(mission.model_dump_json()) == mission


def test_arrival_accepts_numpy_goal_and_rejects_integer_evidence_flags():
    tracker = ArrivalTracker()
    assert tracker.update(pose(0, 1.), np.array([1., 1., 1.]), 1.)['status'] == 'dwelling'
    from ball_demo.arrival import ArrivalState
    for field in ('uncertainty_provisional', 'physical_acceptance'):
        data = tracker.snapshot(); data[field] = 0
        with pytest.raises(ValueError): ArrivalState.model_validate(data)


@pytest.mark.parametrize('change', ['duplicate', 'unknown_tag', 'blocked', 'map', 'source', 'authority', 'heading', 'name', 'numeric', 'extra'])
def test_invalid_missions_rejected(change):
    data = mission_data()
    if change == 'duplicate': data['targets'].append(copy.deepcopy(data['targets'][0]))
    if change == 'unknown_tag': data['targets'][0]['tag_id'] = 99
    if change == 'blocked': data['targets'][0]['viewing_position_m'] = [0., 0., 0.]
    if change == 'map': data['map_version'] = 2
    if change == 'source': data['example'] = False
    if change == 'authority': data['physical_output'] = True
    if change == 'heading': data['targets'][0]['heading_rad'] = float('inf')
    if change == 'name': data['targets'][0]['name'] = '   '
    if change == 'numeric': data['targets'][0]['viewing_position_m'][0] = True
    if change == 'extra': data['command_yaw'] = .5
    with pytest.raises(ValueError): Mission.model_validate(data).validate_bundle(example_bundle())


def test_mission_requires_distinct_arrival_frames_snapshot_and_operator_advance():
    bundle = example_bundle()
    runner = MissionRunner(Mission.model_validate(mission_data()), bundle)
    assert runner.start()['status'] == 'running'
    with pytest.raises(ValueError, match='cannot advance'):
        runner.advance()
    states = [runner.observe(pose(i, 1. + i * .1, (1.7, .8, 1.2), yaw=np.pi / 2), 1. + i * .1) for i in range(3)]
    assert [state['arrival']['fresh_frames'] for state in states] == [1, 2, 3]
    assert states[-1]['status'] == 'snapshot_pending'
    assert states[-1]['snapshot_status'] == 'requested'
    complete = runner.snapshot_saved('a' * 64, 'synthetic')
    assert complete['status'] == 'target_complete' and complete['snapshot_sha256'] == 'a' * 64
    assert runner.advance()['status'] == 'complete'


def test_target_tag_gates_arrival_and_localization_loss_cancels_snapshot():
    runner = MissionRunner(Mission.model_validate(mission_data()), example_bundle())
    runner.start()
    for i in range(3):
        candidate = pose(i, 1. + i * .1, (1.7, .8, 1.2), yaw=np.pi / 2)
        candidate.tag_ids = [1]  # Position may be estimated, but target A is not in view.
        state = runner.observe(candidate, 1. + i * .1)
    assert state['status'] == 'waiting_for_target' and state['arrival']['fresh_frames'] == 0
    visible_states = []
    for i in range(3, 7):
        state = runner.observe(pose(i, 1. + i * .1, (1.7, .8, 1.2), yaw=np.pi / 2), 1. + i * .1)
        visible_states.append(state['status'])
    assert visible_states[:2] == ['reacquiring_target', 'running']
    assert state['status'] == 'snapshot_pending'
    lost = runner.localization_lost()
    assert lost['status'] == 'waiting_for_localization'
    assert lost['snapshot_status'] == 'not_requested' and lost['snapshot_sha256'] is None
    assert runner.localization_restored()['status'] == 'running'


def test_completed_target_waits_for_localization_before_operator_advance():
    runner = MissionRunner(Mission.model_validate(mission_data()), example_bundle())
    runner.start()
    for i in range(3): runner.observe(pose(i, 1. + i * .1, (1.7, .8, 1.2), yaw=np.pi / 2), 1. + i * .1)
    runner.snapshot_saved('b' * 64, 'synthetic')
    assert runner.localization_lost()['status'] == 'waiting_for_localization'
    with pytest.raises(ValueError, match='cannot advance'): runner.advance()
    assert runner.localization_restored()['status'] == 'target_complete'
    assert runner.advance()['status'] == 'complete'


def test_failed_snapshot_can_be_aborted_cleanly():
    runner = MissionRunner(Mission.model_validate(mission_data()), example_bundle())
    runner.start()
    for i in range(3): runner.observe(pose(i, 1. + i * .1, (1.7, .8, 1.2), yaw=np.pi / 2), 1. + i * .1)
    assert runner.snapshot_failed()['status'] == 'fault'
    aborted = runner.abort()
    assert aborted['status'] == 'aborted' and aborted['snapshot_status'] == 'not_requested'


def test_rejected_pose_resets_mission_arrival_dwell():
    bundle = example_bundle()
    from ball_demo.localization import Localizer, Timing
    from ball_demo.navigation_fixtures import example_pose, observations_for
    def accepted_pose(sequence, t):
        transform = example_pose((1.7, .8, 1.2))
        return Localizer(bundle).solve(observations_for(bundle, transform),
            Timing(host_received_s=t, exposure_s=t, provenance='synthetic'), sequence, 'synthetic_estimate')
    advisory = Advisory(bundle)
    advisory.load_mission(Mission.model_validate(mission_data()))
    advisory.start_mission()
    for i in range(3):
        candidate = accepted_pose(i, 1. + i * .05)
        advisory.accept(candidate, 1. + i * .05)
    assert advisory.mission_runner.tracker.snapshot()['fresh_frames'] == 1
    bad = accepted_pose(3, 1.15)
    bad.tag_ids = [99]
    assert not advisory.accept(bad, 1.15)
    assert advisory.mission_runner.status == 'waiting_for_localization'
    assert advisory.mission_runner.tracker.snapshot()['fresh_frames'] == 0
