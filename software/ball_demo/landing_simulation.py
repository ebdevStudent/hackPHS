"""Bounded landing scenario with synthetic height/contact evidence only."""
import math


def step_landing(altitude_m, descent_rate_m_s, *, dt_s=.01, safe_touchdown_m_s=.15):
    """Advance a vertical mock descent; never reads sensors or controls hardware.

    A landing event is emitted only when the synthetic altitude reaches zero.
    Excessive contact speed produces an impact event instead of a landed state.
    """
    values = (altitude_m, descent_rate_m_s, dt_s, safe_touchdown_m_s)
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise ValueError('Landing simulation values must be finite numbers')
    altitude_m, descent_rate_m_s, dt_s, safe_touchdown_m_s = map(float, values)
    if altitude_m < 0 or descent_rate_m_s <= 0 or not 0 < dt_s <= .25 or safe_touchdown_m_s <= 0:
        raise ValueError('Landing simulation values are outside their safe bounds')
    next_altitude = max(0., altitude_m - descent_rate_m_s * dt_s)
    event = None
    state = 'descending'
    if next_altitude == 0:
        event = 'synthetic_touchdown' if descent_rate_m_s <= safe_touchdown_m_s else 'synthetic_impact'
        state = 'touchdown' if event == 'synthetic_touchdown' else 'impact'
    return {
        'schema_version': 1,
        'source': 'synthetic',
        'altitude_m': next_altitude,
        'vertical_speed_m_s': -descent_rate_m_s,
        'state': state,
        'event': event,
        'physical_output': False,
    }
