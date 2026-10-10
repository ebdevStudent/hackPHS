"""Heading and visibility routes use only independently constructed geometry."""
import copy
import math

import numpy as np
import pytest

from ball_demo.map_io import Bundle
from ball_demo.navigation_fixtures import example_bundle
from ball_demo.navigation_visibility import VisibleRoute, VisibilityPlanner


def test_route_keeps_two_localization_tags_through_turns_and_goal_view():
    bundle = example_bundle()
    planner = VisibilityPlanner(bundle)
    assert planner.visible_tag_ids([1.7, .8, 1.2], math.pi / 2) == [0, 1]
    route = planner.plan([1.7, .8, 1.2], [2.2, 1.5, 1.3], .02,
                         math.pi / 2, math.pi / 2, required_tag_id=0)
    assert route.visible_tag_ids[0] == [0, 1]
    assert 0 in route.visible_tag_ids[-1]
    assert all(len(ids) >= 2 for ids in route.visible_tag_ids)
    for start, end, heading in zip(route.points_m, route.points_m[1:], route.headings_rad[1:]):
        assert planner._visible_along(start, end, heading) is not None
    for i, (before, after) in enumerate(zip(route.headings_rad, route.headings_rad[1:])):
        delta = math.atan2(math.sin(after - before), math.cos(after - before))
        if abs(delta) > math.radians(.1):
            assert np.allclose(route.points_m[i], route.points_m[i + 1])
            assert planner._rotation_visible(route.points_m[i], before, after)


@pytest.mark.parametrize('gap', ['occupied', 'unknown'])
def test_occlusion_and_unknown_space_both_remove_apriltag_visibility(gap):
    data = example_bundle().model_dump()
    if gap == 'occupied':
        data['map']['occupied'] = [{'minimum': [0., 1.6, 0.], 'maximum': [4., 2., 3.]}]
    else:
        data['map']['observed_free'] = [
            {'minimum': [0., 0., 0.], 'maximum': [4., 1.6, 3.]},
            {'minimum': [0., 2., 0.], 'maximum': [4., 4., 3.]},
        ]
    planner = VisibilityPlanner(Bundle.model_validate(data))
    assert planner.visible_tag_ids([1.7, .8, 1.2], math.pi / 2) == []


@pytest.mark.parametrize('bad', ['start_heading', 'goal_heading', 'tag'])
def test_invalid_route_intent_is_rejected(bad):
    planner = VisibilityPlanner(example_bundle())
    args = [[1.7, .8, 1.2], [2.2, 1.5, 1.3], .02, math.pi / 2]
    kwargs = {}
    if bad == 'start_heading': args[3] = float('nan')
    if bad == 'goal_heading': kwargs['goal_heading'] = 4.
    if bad == 'tag': kwargs['required_tag_id'] = 22
    with pytest.raises(ValueError): planner.plan(*args, **kwargs)


def test_unknown_tag_does_not_become_a_localization_route():
    planner = VisibilityPlanner(example_bundle())
    with pytest.raises(ValueError, match='Unknown required'):
        planner.visible_tag_ids([1.7, .8, 1.2], math.pi / 2, 22)


def test_visibility_astar_routes_around_a_known_occupied_obstacle():
    data = example_bundle().model_dump()
    data['map']['occupied'] = [{'minimum': [1.9, .6, .7], 'maximum': [2.1, 1.4, 1.7]}]
    planner = VisibilityPlanner(Bundle.model_validate(data), clock=lambda: 0.)
    route = planner.plan([1.5, 1., 1.2], [2.5, 1., 1.2], .02, math.pi / 2,
                         goal_heading=math.pi / 2, required_tag_id=0)
    assert len(route.points_m) > 2
    assert any(point[2] > 1.7 for point in route.points_m)
    assert all(len(ids) >= 2 and 0 in ids for ids in route.visible_tag_ids)
    for start, end, heading in zip(route.points_m, route.points_m[1:], route.headings_rad[1:]):
        assert planner._visible_along(start, end, heading) is not None


def test_visibility_astar_turns_in_place_when_only_a_later_heading_can_move(monkeypatch):
    """Exercise heading-state transitions and route reconstruction deterministically."""
    planner = VisibilityPlanner(example_bundle(), clock=lambda: 0.)
    def clear(start, end, margin, budget=lambda: None):
        # Force the direct edge to fail, while allowing adjacent grid steps and
        # the final short connection to the exact goal.
        return float(np.linalg.norm(np.asarray(end) - np.asarray(start))) <= .21

    def visible_along(start, end, heading, required_tag_id=None):
        start_point = np.asarray(start)
        length = float(np.linalg.norm(np.asarray(end) - np.asarray(start)))
        index = round((heading % (2 * math.pi)) / (2 * math.pi / planner.heading_bins)) % planner.heading_bins
        if length > .5:
            return None
        initial_seed = np.allclose(start_point, [1.5, 1., 1.2]) and index == 6
        subsequent_move = not np.allclose(start_point, [1.5, 1., 1.2]) and index == 12
        if length <= .21 and (length < 1e-8 or initial_seed or subsequent_move):
            return [[0, 1], [0, 1]]
        return None

    monkeypatch.setattr(planner.planner, 'segment_clear', clear)
    monkeypatch.setattr(planner, '_visible_along', visible_along)
    monkeypatch.setattr(planner, '_rotation_visible', lambda *args: True)
    monkeypatch.setattr(planner, 'visible_tag_ids', lambda *args: [0, 1])
    route = planner.plan([1.5, 1., 1.2], [2.5, 1., 1.2], .02, math.pi / 2,
                         goal_heading=math.pi / 2)
    assert any(abs(math.atan2(math.sin(b - a), math.cos(b - a))) > math.radians(5)
               for a, b in zip(route.headings_rad, route.headings_rad[1:]))
    assert route.headings_rad[-1] == pytest.approx(math.pi / 2)
    assert all(len(tags) >= 2 for tags in route.visible_tag_ids)


def test_visibility_rejects_invalid_heading_bins_start_and_goal_envelope():
    with pytest.raises(ValueError, match='Heading bins'):
        VisibilityPlanner(example_bundle(), heading_bins=10)
    planner = VisibilityPlanner(example_bundle())
    with pytest.raises(ValueError, match='visibility heading'):
        planner.visible_tag_ids([1.7, .8, 1.2], float('nan'))
    with pytest.raises(ValueError, match='within ±π'):
        planner.plan([1.7, .8, 1.2], [2.2, 1.5, 1.3], .02, 4.)
    with pytest.raises(ValueError, match='goal heading'):
        planner.plan([1.7, .8, 1.2], [2.2, 1.5, 1.3], .02, math.pi / 2, float('nan'))
    with pytest.raises(ValueError, match='observed envelope clearance'):
        planner.plan([.1, .1, .1], [2.2, 1.5, 1.3], .02, math.pi / 2)


def test_visibility_goal_tag_selects_a_visible_heading_or_fails_closed(monkeypatch):
    planner = VisibilityPlanner(example_bundle(), clock=lambda: 0.)
    route = planner.plan([1.7, .8, 1.2], [2.2, 1.5, 1.3], .02, math.pi / 2,
                         required_tag_id=0)
    assert 0 in route.visible_tag_ids[-1]
    monkeypatch.setattr(planner, 'visible_tag_ids', lambda *args: [])
    with pytest.raises(ValueError, match='No route retains'):
        planner.plan([1.7, .8, 1.2], [2.2, 1.5, 1.3], .02, math.pi / 2,
                     required_tag_id=0)


def test_visibility_checks_back_faces_goal_rotation_and_node_budgets(monkeypatch):
    planner = VisibilityPlanner(example_bundle(), clock=lambda: 0.)
    assert planner.visible_tag_ids([1.7, 3.5, 1.2], math.pi / 2) == []

    monkeypatch.setattr(planner, 'visible_tag_ids', lambda *args: [])
    assert planner._finish_heading([2.2, 1.5, 1.3], 0., 0., 0) is None
    assert planner._finish_heading([2.2, 1.5, 1.3], 0., 0., None) is None
    assert planner._finish_heading([2.2, 1.5, 1.3], 0., None, 0) is None

    planner = VisibilityPlanner(example_bundle(), clock=lambda: 0.)
    monkeypatch.setattr(planner, 'visible_tag_ids', lambda *args: [0, 1])
    monkeypatch.setattr(planner, '_visible_along', lambda *args, **kwargs: [[0, 1], [0, 1]])
    monkeypatch.setattr(planner, '_rotation_visible', lambda *args: True)
    monkeypatch.setattr(planner, '_finish_heading', lambda *args: None)
    assert planner._direct(np.array([1.7, .8, 1.2]), np.array([2.2, 1.5, 1.3]),
                           math.pi / 2, 0., None, .1) is None
    monkeypatch.setattr(planner.planner, 'segment_clear', lambda *args, **kwargs: True)
    monkeypatch.setattr(planner, '_finish_heading', lambda *args: math.pi / 2)
    direct = planner._direct(np.array([1.7, .8, 1.2]), np.array([2.2, 1.5, 1.3]),
                             0., math.pi / 2, None, .1)
    assert direct.points_m[-1] == direct.points_m[-2]
    assert direct.headings_rad[-1] == pytest.approx(math.pi / 2)

    data = example_bundle().model_dump()
    data['policy']['max_nodes'] = 1
    data['map']['occupied'] = [{'minimum': [1.9, .6, .7], 'maximum': [2.1, 1.4, 1.7]}]
    bounded = VisibilityPlanner(Bundle.model_validate(data), clock=lambda: 0.)
    with pytest.raises(ValueError, match='node budget'):
        bounded.plan([1.5, 1., 1.2], [2.5, 1., 1.2], .02, math.pi / 2)


def test_visibility_uses_distorted_sensor_and_rectified_detector_pixel_bounds():
    data = example_bundle().model_dump()
    data['calibration']['distortion'] = [5., 0., 0., 0., 0.]
    planner = VisibilityPlanner(Bundle.model_validate(data))
    # Ideal pinhole projection puts both tags inside the image. The calibrated
    # raw projection clips one tag at the sensor boundary, leaving localization
    # without the required two surveyed markers.
    assert planner.visible_tag_ids([1.7, .8, 1.2], math.pi / 2) == []


def test_nonfinite_distorted_projection_is_never_reported_visible(monkeypatch):
    import cv2
    planner = VisibilityPlanner(example_bundle())
    invalid = np.full((4, 1, 2), np.nan)
    monkeypatch.setattr(cv2, 'projectPoints', lambda *args, **kwargs: (invalid, None))
    monkeypatch.setattr(cv2, 'undistortPoints', lambda *args, **kwargs: invalid)
    assert planner.visible_tag_ids([1.7, .8, 1.2], math.pi / 2) == []


def test_deadline_cache_and_route_contract_budgets_fail_closed():
    ticks = iter(range(10000))
    planner = VisibilityPlanner(example_bundle(), clock=lambda: next(ticks) * .02)
    with pytest.raises(ValueError, match='deadline'):
        planner.plan([1.7, .8, 1.2], [2.2, 1.5, 1.3], .02, math.pi / 2)

    planner = VisibilityPlanner(example_bundle())
    planner.max_cache_entries = 0
    with pytest.raises(ValueError, match='cache budget'):
        planner.visible_tag_ids([1.7, .8, 1.2], math.pi / 2)

    with pytest.raises(ValueError):
        VisibleRoute(points_m=[[0., 0., 0.], [1., 1., 1.]], headings_rad=[0.],
                     visible_tag_ids=[[0], [0]], clearance_m=.1, example=True)
    with pytest.raises(ValueError):
        VisibleRoute(points_m=[[0., 0., 0.], [1., 1., 1.]], headings_rad=[0., 0.],
                     visible_tag_ids=[[], [0]], clearance_m=.1, example=True)
    with pytest.raises(ValueError, match='Every route sample'):
        VisibleRoute(points_m=[[0., 0., 0.], [1., 1., 1.]], headings_rad=[0., 0.],
                     visible_tag_ids=[[0, 0], [0, 1]], clearance_m=.1, example=True)
    with pytest.raises(ValueError, match='counts differ'):
        VisibleRoute(points_m=[[0., 0., 0.], [1., 1., 1.], [2., 2., 2.]],
                     headings_rad=[0., 0.], visible_tag_ids=[[0, 1], [0, 1]],
                     clearance_m=.1, example=True)
