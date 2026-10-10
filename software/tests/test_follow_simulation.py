"""Independent deterministic invariants for the non-actuating follower."""
import copy

import pytest

from ball_demo.follow_simulation import FollowLimits, simulate_follow


def trace(points, visible=None, overrides=None, step=.05):
    visible = visible or [True] * len(points)
    overrides = overrides or [False] * len(points)
    return [{'time_s': i * step, 'x_m': x, 'y_m': y, 'visible': visible[i],
             'pilot_override': overrides[i]} for i, (x, y) in enumerate(points)]


def test_follower_is_repeatable_bounded_and_keeps_truth_separate_from_estimates():
    rows = trace([(1.8, 0.), (1.8, .2), (1.5, .5), (1.2, .7)] * 20)
    first = simulate_follow(rows, seed=23, position_noise_m=.02, bearing_noise_rad=.01)
    second = simulate_follow(copy.deepcopy(rows), seed=23, position_noise_m=.02, bearing_noise_rad=.01)
    assert first == second
    assert first['physical_output'] is False
    assert first['control_authority'] == 'simulation_only'
    assert 'not aircraft telemetry' in first['label']
    for sample in first['samples']:
        assert sample['source'] == 'synthetic'
        assert sample['physical_output'] is False
        assert abs(sample['actual']['forward_m_s']) <= first['limits']['max_speed_m_s']
        assert abs(sample['actual']['yaw_rate_rad_s']) <= first['limits']['max_yaw_rate_rad_s']
        assert sample['truth'] is not sample['estimate']


def test_missing_frames_brake_then_require_consecutive_frames_to_reacquire():
    visibility = [True] * 12 + [False] * 3 + [True] * 5
    result = simulate_follow(trace([(2., 0.)] * len(visibility), visibility), dt_s=.05)
    samples = result['samples']
    assert any(sample['actual']['forward_m_s'] > 0 for sample in samples[:12])
    loss = samples[12]
    assert loss['state'] == 'lost' and loss['estimate'] is None
    assert loss['desired'] == {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
    assert samples[15]['state'] == 'reacquiring'
    assert samples[16]['state'] == 'reacquiring'
    assert samples[17]['state'] == 'following'


def test_pilot_override_and_minimum_approach_are_latched_until_new_run():
    rows = trace([(2., 0.)] * 8 + [(.35, 0.)] * 12)
    close = simulate_follow(rows)
    stopped = next(i for i, sample in enumerate(close['samples']) if sample['reason'] and 'minimum approach' in sample['reason'])
    assert all(sample['state'] == 'stopped' for sample in close['samples'][stopped:])
    assert all(sample['desired']['forward_m_s'] == 0 for sample in close['samples'][stopped:])

    override = [False] * 10 + [True] + [False] * 10
    result = simulate_follow(trace([(2., 0.)] * len(override), overrides=override))
    assert result['samples'][10]['state'] == 'stopped'
    assert all(sample['state'] == 'stopped' for sample in result['samples'][10:])
    assert all(sample['desired'] == {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
               for sample in result['samples'][10:])


@pytest.mark.parametrize('kwargs', [
    {'dt_s': .251}, {'seed': True}, {'position_noise_m': float('nan')},
    {'observation_delay_frames': 101},
])
def test_invalid_simulation_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        simulate_follow(trace([(2., 0.)]), **kwargs)


def test_invalid_trajectory_types_times_and_gaps_are_rejected():
    valid = trace([(2., 0.), (2., 0.)])
    with pytest.raises(ValueError, match='boolean'):
        simulate_follow([{**valid[0], 'visible': 1}])
    with pytest.raises(ValueError, match='strictly increasing'):
        simulate_follow([valid[0], {**valid[1], 'time_s': 0.}])
    with pytest.raises(ValueError, match='250 ms'):
        simulate_follow([valid[0], {**valid[1], 'time_s': .3}])
    with pytest.raises(ValueError, match='pilot_override'):
        simulate_follow([{**valid[0], 'pilot_override': 'yes'}])
    with pytest.raises(ValueError, match='contain the initial'):
        FollowLimits(bounds_m=(1., 2., 1., 2.)).validate()


@pytest.mark.parametrize('limits', [
    FollowLimits(bounds_m=(0., 1., 0.)),
    FollowLimits(desired_distance_m=float('nan')),
    FollowLimits(desired_distance_m=0.),
    FollowLimits(deadband_m=-.1),
    FollowLimits(min_approach_m=1.),
    FollowLimits(max_speed_m_s=0.),
    FollowLimits(max_acceleration_m_s2=0.),
    FollowLimits(max_yaw_rate_rad_s=0.),
    FollowLimits(yaw_gain_s=0.),
    FollowLimits(distance_gain_s=0.),
    FollowLimits(reacquire_frames=True),
    FollowLimits(bounds_m=(1., -1., -1., 1.)),
])
def test_follower_limits_reject_invalid_configuration(limits):
    with pytest.raises(ValueError):
        limits.validate()


def test_follower_fault_latches_at_boundary_and_delayed_observations_are_labeled():
    rows = trace([(2., 0.)] * 60)
    bounded = FollowLimits(bounds_m=(0., .08, -1., 1.), max_speed_m_s=.45,
                           max_acceleration_m_s2=1.0)
    result = simulate_follow(rows, limits=bounded)
    fault = next(i for i, sample in enumerate(result['samples']) if sample['state'] == 'fault')
    assert all(sample['state'] == 'fault' and sample['physical_output'] is False
               for sample in result['samples'][fault:])
    assert all(sample['actual'] == {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
               for sample in result['samples'][fault:])

    moving = trace([(2.0 + i * .02, .1) for i in range(8)])
    delayed = simulate_follow(moving, observation_delay_frames=2, position_noise_m=.01,
                              bearing_noise_rad=.01, seed=4)
    estimates = [sample['estimate'] for sample in delayed['samples'] if sample['estimate']]
    assert estimates and all(item['source'] == 'synthetic_estimate' and item['age_s'] >= 0 for item in estimates)


@pytest.mark.parametrize('trajectory', [
    [],
    [{'time_s': 0., 'x_m': 1., 'y_m': 0., 'visible': True, 'extra': 1}],
    [{'time_s': -1., 'x_m': 1., 'y_m': 0., 'visible': True}],
    [{'time_s': 0., 'x_m': float('nan'), 'y_m': 0., 'visible': True}],
])
def test_follower_rejects_empty_unknown_negative_and_nonfinite_trajectories(trajectory):
    with pytest.raises(ValueError):
        simulate_follow(trajectory)


def test_follower_rejects_invalid_limits_type_noise_and_timestep():
    with pytest.raises(ValueError, match='bounds_m'):
        FollowLimits(bounds_m='invalid').validate()
    with pytest.raises(ValueError, match='finite'):
        FollowLimits(bounds_m=(0., 2., -2., float('inf'))).validate()
    with pytest.raises(ValueError, match='negative'):
        simulate_follow(trace([(1., 0.)]), position_noise_m=-.1)
    with pytest.raises(ValueError, match='dt_s'):
        simulate_follow(trace([(1., 0.)]), dt_s=0.)
    with pytest.raises(ValueError, match='nonnegative'):
        simulate_follow(trace([(1., 0.)]), seed=-1)
    with pytest.raises(ValueError, match='observation_delay_frames'):
        simulate_follow(trace([(1., 0.)]), observation_delay_frames=True)
