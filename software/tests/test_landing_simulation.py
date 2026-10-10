import pytest

from ball_demo.landing_simulation import step_landing


def test_touchdown_requires_synthetic_altitude_crossing_and_safe_vertical_rate():
    first = step_landing(.1, .1, dt_s=.05)
    assert first['state'] == 'descending' and first['event'] is None
    second = first
    while second['event'] is None:
        second = step_landing(second['altitude_m'], .1, dt_s=.05)
    assert second['state'] == 'touchdown'
    assert second['event'] == 'synthetic_touchdown'
    assert second['source'] == 'synthetic' and second['physical_output'] is False


def test_unsafe_impact_is_not_reported_as_landing():
    result = step_landing(.01, .4, dt_s=.05)
    assert result['state'] == 'impact'
    assert result['event'] == 'synthetic_impact'


@pytest.mark.parametrize('args', [
    (-.1, .1), (.1, 0), (.1, .1, .3), (float('nan'), .1), (.1, True),
])
def test_landing_simulation_rejects_invalid_limits(args):
    altitude, rate, *rest = args
    with pytest.raises(ValueError):
        step_landing(altitude, rate, dt_s=rest[0] if rest else .01)
