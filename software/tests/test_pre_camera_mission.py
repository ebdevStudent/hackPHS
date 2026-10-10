"""Mission-state invariants and dry-run progression using invented poses."""
import copy
import pytest

from ball_demo.localization import Localizer, Timing
from ball_demo.mission import Mission, MissionRunner, MissionState
from ball_demo.navigation_fixtures import example_bundle, example_mission, example_pose, observations_for


def state_fixture(bundle=None):
    bundle = bundle or example_bundle()
    runner = MissionRunner(example_mission(bundle), bundle)
    return runner.snapshot()


def target_pose(bundle, sequence, at, position=None):
    mission = example_mission(bundle)
    position = position or mission.targets[0].viewing_position_m
    return Localizer(bundle).solve(
        observations_for(bundle, example_pose(position)),
        Timing(host_received_s=at, exposure_s=at, provenance='synthetic'),
        sequence,
        'synthetic_estimate',
    )


def runner_at_snapshot_pending(bundle=None, mission=None):
    bundle = bundle or example_bundle()
    mission = mission or example_mission(bundle)
    runner = MissionRunner(mission, bundle)
    runner.start()
    target = mission.targets[0].viewing_position_m
    for sequence, at in enumerate((1.05, 1.10, 1.15, 1.25)):
        state = runner.observe(target_pose(bundle, sequence, at, target), at)
    assert state['status'] == 'snapshot_pending'
    return runner


@pytest.mark.parametrize('changes', [
    {'status': 'ready', 'target_index': None},
    {'status': 'complete', 'target_index': 0},
    {'target_name': None},
    {'snapshot_sha256': 'a' * 64},
    {'status': 'snapshot_pending', 'snapshot_status': 'not_requested'},
    {'status': 'target_complete', 'snapshot_status': 'failed'},
    {'status': 'complete', 'target_index': None, 'target_id': 'leftover-target',
     'target_name': None, 'arrival': None},
    {'status': 'aborted', 'target_index': None, 'target_id': None,
     'target_name': None, 'arrival': None, 'snapshot_status': 'failed'},
])
def test_mission_state_rejects_inconsistent_status_and_snapshot_contracts(changes):
    data = copy.deepcopy(state_fixture())
    data.update(changes)
    with pytest.raises(ValueError):
        MissionState.model_validate(data)


def test_mission_target_without_image_completes_after_estimated_arrival():
    bundle = example_bundle()
    data = example_mission(bundle).model_dump()
    data['targets'][0]['snapshot'] = 'none'
    mission = Mission.model_validate(data)
    runner = MissionRunner(mission, bundle)
    assert runner.active is False
    runner.start()
    for sequence, at in enumerate((1.05, 1.10, 1.15, 1.25)):
        state = runner.observe(target_pose(bundle, sequence, at), at)
    assert state['status'] == 'target_complete'
    assert state['snapshot_status'] == 'not_required'
    assert runner.active


def test_mission_reports_target_loss_reacquisition_and_localization_loss():
    bundle = example_bundle()
    mission = example_mission(bundle)
    runner = MissionRunner(mission, bundle)
    runner.start()
    missing_tag = target_pose(bundle, 0, 1.05)
    missing_tag.tag_ids = [1]
    state = runner.observe(missing_tag, 1.05)
    assert state['status'] == 'waiting_for_target' and state['arrival']['fresh_frames'] == 0

    visible = target_pose(bundle, 1, 1.10)
    assert runner.observe(visible, 1.10)['status'] == 'reacquiring_target'
    reacquired = target_pose(bundle, 2, 1.15)
    state = runner.observe(reacquired, 1.15)
    assert state['status'] == 'running' and state['arrival']['fresh_frames'] == 1

    runner.localization_lost()
    first_loss = runner.snapshot()
    runner.localization_lost()
    assert runner.snapshot() == first_loss
    assert runner.localization_restored()['status'] == 'running'

    stale = target_pose(bundle, 3, 2.)
    with pytest.raises(ValueError, match='Stale/invalid arrival pose'):
        runner.observe(stale, 1.9)
    assert runner.status == 'waiting_for_localization'


@pytest.mark.parametrize('status', ['waiting_for_target', 'reacquiring_target'])
def test_mission_state_accepts_explicit_target_loss_phases(status):
    data = state_fixture()
    data['status'] = status
    assert MissionState.model_validate(data).status == status


@pytest.mark.parametrize('status', ['waiting_for_target', 'reacquiring_target'])
def test_advisory_mission_abort_is_allowed_during_target_loss(tmp_path, status):
    from ball_demo.navigation_runtime import NavigationRuntime

    bundle = example_bundle()
    runtime = NavigationRuntime(bundle, tmp_path / f'{status}.jsonl')
    runtime.cached['mission'] = {'status': status}
    runtime.command('mission_abort')
    assert runtime.commands.pop()[0] == 'mission_abort'


def test_mission_snapshot_validation_loss_resume_and_multi_target_advance():
    bundle = example_bundle()
    data = example_mission(bundle).model_dump()
    data['targets'].append({**data['targets'][0], 'target_id': 'synthetic-target-b',
                            'name': 'Synthetic inspection B', 'viewing_position_m': [2.3, 1.5, 1.3]})
    mission = Mission.model_validate(data)
    runner = runner_at_snapshot_pending(bundle, mission)
    with pytest.raises(ValueError, match='SHA256'):
        runner.snapshot_saved('bad', 'synthetic')
    with pytest.raises(ValueError, match='source'):
        runner.snapshot_saved('a' * 64, 'unknown')
    with pytest.raises(ValueError, match='source/example mismatch'):
        runner.snapshot_saved('a' * 64, 'camera')

    waiting = runner.localization_lost()
    assert waiting['snapshot_status'] == 'not_requested'
    assert runner.localization_restored()['status'] == 'running'
    with pytest.raises(ValueError, match='pending image snapshot'):
        runner.snapshot_saved('a' * 64, 'synthetic')

    runner = runner_at_snapshot_pending(bundle, mission)
    complete = runner.snapshot_saved('c' * 64, 'synthetic')
    assert complete['status'] == 'target_complete' and runner.active
    second = runner.advance()
    assert second['status'] == 'running' and second['target_index'] == 1
    assert second['target_id'] == 'synthetic-target-b'
    assert second['snapshot_status'] == 'not_requested' and second['snapshot_sha256'] is None

    runner.abort()
    assert runner.snapshot()['status'] == 'aborted' and runner.active is False
    with pytest.raises(ValueError, match='before arrival'):
        runner.advance()

    failed = runner_at_snapshot_pending(bundle)
    assert failed.snapshot_failed()['status'] == 'fault'
    assert failed.active is False
    with pytest.raises(ValueError, match='pending image snapshot'):
        failed.snapshot_failed()


def test_mission_bundle_requires_a_visible_tag_and_unique_target_ids():
    bundle = example_bundle()
    data = example_mission(bundle).model_dump()
    data['targets'][0]['tag_id'] = 22
    with pytest.raises(ValueError, match='Unknown mission tag'):
        Mission.model_validate(data).validate_bundle(bundle)

    data['targets'][0]['tag_id'] = 0
    data['targets'][0]['viewing_position_m'] = [1.7, .8, 1.2]
    data['targets'][0]['heading_rad'] = 0.
    mission = Mission.model_validate(data)
    with pytest.raises(ValueError, match='no calibrated'):
        mission.validate_bundle(bundle)

    duplicate = example_mission(bundle).model_dump()
    duplicate['targets'].append(dict(duplicate['targets'][0]))
    with pytest.raises(ValueError, match='Duplicate inspection target'):
        Mission.model_validate(duplicate)
