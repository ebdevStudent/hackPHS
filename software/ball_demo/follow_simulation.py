"""Deterministic, bounded 2D follow controller simulation; no aircraft outputs."""
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class FollowLimits:
    desired_distance_m: float = 1.0
    deadband_m: float = .15
    min_approach_m: float = .45
    max_speed_m_s: float = .45
    max_acceleration_m_s2: float = .7
    max_yaw_rate_rad_s: float = 1.2
    yaw_gain_s: float = 1.8
    distance_gain_s: float = .8
    reacquire_frames: int = 3
    bounds_m: tuple = (-4., 4., -4., 4.)

    def validate(self):
        if not isinstance(self.bounds_m, (tuple, list)) or len(self.bounds_m) != 4:
            raise ValueError('bounds_m must contain xmin, xmax, ymin, ymax')
        values = (self.desired_distance_m, self.deadband_m, self.min_approach_m,
                  self.max_speed_m_s, self.max_acceleration_m_s2,
                  self.max_yaw_rate_rad_s, self.yaw_gain_s, self.distance_gain_s, *self.bounds_m)
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
            raise ValueError('Follow simulation settings must be finite')
        if self.desired_distance_m <= 0 or self.deadband_m < 0 or self.min_approach_m <= 0:
            raise ValueError('Follow distances must be positive (deadband may be zero)')
        if self.min_approach_m >= self.desired_distance_m:
            raise ValueError('Minimum approach distance must be below the desired distance')
        if min(self.max_speed_m_s, self.max_acceleration_m_s2, self.max_yaw_rate_rad_s,
               self.yaw_gain_s, self.distance_gain_s) <= 0:
            raise ValueError('Follow controller rates and limits must be positive')
        if type(self.reacquire_frames) is not int or not 1 <= self.reacquire_frames <= 30:
            raise ValueError('reacquire_frames must be an integer from 1 to 30')
        xmin, xmax, ymin, ymax = self.bounds_m
        if xmin >= xmax or ymin >= ymax:
            raise ValueError('Simulation operating bounds are empty or inverted')
        if not (xmin <= 0 <= xmax and ymin <= 0 <= ymax):
            raise ValueError('Simulation bounds must contain the initial aircraft position')
        return self


def _finite(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    return float(value)


def simulate_follow(trajectory, *, limits=None, dt_s=.05, seed=0, position_noise_m=0.,
                    bearing_noise_rad=0., observation_delay_frames=0):
    """Simulate a pilot-overridable follower using delayed/noisy relative estimates.

    Trajectory rows use `{time_s, x_m, y_m, visible}` in a synthetic world.
    Estimated pose and truth stay in separate fields. Missing/stale observations
    request zero motion and turn; velocity is bounded by the simulated braking
    limit. The output explicitly has no actuator/physical authority.
    """
    limits = (limits or FollowLimits()).validate()
    dt_s = _finite(dt_s, 'dt_s')
    position_noise_m = _finite(position_noise_m, 'position_noise_m')
    bearing_noise_rad = _finite(bearing_noise_rad, 'bearing_noise_rad')
    if not 0 < dt_s <= .25:
        raise ValueError('dt_s must be in (0, 0.25]')
    if position_noise_m < 0 or bearing_noise_rad < 0:
        raise ValueError('Noise standard deviations cannot be negative')
    if type(seed) is not int or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    if type(observation_delay_frames) is not int or not 0 <= observation_delay_frames <= 100:
        raise ValueError('observation_delay_frames must be an integer from 0 to 100')
    if not isinstance(trajectory, (list, tuple)) or not 1 <= len(trajectory) <= 20_000:
        raise ValueError('trajectory must contain 1–20000 samples')

    parsed = []
    previous_time = -math.inf
    for row in trajectory:
        if not isinstance(row, dict) or not {'time_s', 'x_m', 'y_m', 'visible'} <= set(row) or set(row) - {
                'time_s', 'x_m', 'y_m', 'visible', 'pilot_override'}:
            raise ValueError('Each trajectory row must contain time_s, x_m, y_m, visible, and optional pilot_override only')
        t = _finite(row['time_s'], 'time_s')
        if t < 0:
            raise ValueError('Trajectory times must be nonnegative')
        x, y = _finite(row['x_m'], 'x_m'), _finite(row['y_m'], 'y_m')
        if t <= previous_time:
            raise ValueError('Trajectory times must be strictly increasing')
        if type(row['visible']) is not bool:
            raise ValueError('visible must be a boolean')
        pilot_override = row.get('pilot_override', False)
        if type(pilot_override) is not bool:
            raise ValueError('pilot_override must be a boolean')
        parsed.append((t, x, y, row['visible'], pilot_override))
        previous_time = t

    rng = np.random.default_rng(seed)
    drone_x = drone_y = yaw = speed = yaw_rate = 0.
    samples = []
    xmin, xmax, ymin, ymax = limits.bounds_m
    status, reason = 'acquiring', 'Waiting for fresh synthetic target observations'
    fresh_after_loss = 0
    latched_stop = False
    latched_override = False
    previous_time = None
    for index, (time_s, target_x, target_y, visible, pilot_override) in enumerate(parsed):
        step_dt = dt_s if previous_time is None else time_s - previous_time
        if step_dt > .25:
            raise ValueError('Trajectory sample gap exceeds the 250 ms simulation limit')
        previous_time = time_s
        delayed = max(0, index - observation_delay_frames)
        sample_time, observed_x, observed_y, observed_visible, _ = parsed[delayed]
        observed_age = time_s - sample_time
        dx, dy = target_x - drone_x, target_y - drone_y
        distance = math.hypot(dx, dy)
        absolute_bearing = math.atan2(dy, dx)
        bearing = (absolute_bearing - yaw + math.pi) % (2 * math.pi) - math.pi
        estimate = None
        can_follow = observed_visible and observed_age <= max(dt_s * (observation_delay_frames + 1), dt_s)
        if pilot_override:
            latched_override = True
            desired_speed, desired_yaw_rate = 0., 0.
            status, reason = 'stopped', 'Synthetic pilot override latched; explicit mission restart is required'
        elif latched_override:
            desired_speed, desired_yaw_rate = 0., 0.
            status, reason = 'stopped', 'Synthetic pilot override remains latched after release'
        elif latched_stop:
            desired_speed, desired_yaw_rate = 0., 0.
            status = 'stopped'
        elif not can_follow:
            desired_speed, desired_yaw_rate = 0., 0.
            status, reason = 'lost', 'Target observation is missing or too old; simulated motion is stopping'
            fresh_after_loss = 0
        else:
            fresh_after_loss += 1
            if fresh_after_loss < limits.reacquire_frames:
                desired_speed, desired_yaw_rate = 0., 0.
                status = 'acquiring' if index == 0 else 'reacquiring'
                reason = f'Need {limits.reacquire_frames - fresh_after_loss} more fresh observations'
            else:
                status, reason = 'following', None
        if can_follow and not latched_stop and not latched_override:
            observed_dx, observed_dy = observed_x - drone_x, observed_y - drone_y
            observed_distance = math.hypot(observed_dx, observed_dy) + float(rng.normal(0., position_noise_m))
            observed_bearing = ((math.atan2(observed_dy, observed_dx) - yaw + math.pi) % (2 * math.pi) - math.pi
                                + float(rng.normal(0., bearing_noise_rad)))
            estimate = {'range_m': max(0., observed_distance), 'bearing_rad': observed_bearing,
                        'age_s': observed_age, 'source': 'synthetic_estimate'}
            if fresh_after_loss < limits.reacquire_frames:
                desired_speed, desired_yaw_rate = 0., 0.
            elif observed_distance < limits.min_approach_m:
                desired_speed, desired_yaw_rate = 0., 0.
                status, reason = 'stopped', 'Synthetic target crossed the minimum approach distance'
                latched_stop = True
            else:
                error = observed_distance - limits.desired_distance_m
                desired_speed = 0. if abs(error) <= limits.deadband_m else min(
                    limits.max_speed_m_s, max(0., limits.distance_gain_s * error))
                desired_yaw_rate = min(limits.max_yaw_rate_rad_s,
                                       max(-limits.max_yaw_rate_rad_s, limits.yaw_gain_s * observed_bearing))

        acceleration = min(limits.max_acceleration_m_s2,
                           max(-limits.max_acceleration_m_s2, (desired_speed - speed) / step_dt))
        speed = min(limits.max_speed_m_s, max(0., speed + acceleration * step_dt))
        yaw_accel = min(4., max(-4., (desired_yaw_rate - yaw_rate) / step_dt))
        yaw_rate = min(limits.max_yaw_rate_rad_s, max(-limits.max_yaw_rate_rad_s, yaw_rate + yaw_accel * step_dt))
        yaw = (yaw + yaw_rate * step_dt + math.pi) % (2 * math.pi) - math.pi
        drone_x += math.cos(yaw) * speed * step_dt
        drone_y += math.sin(yaw) * speed * step_dt
        if not (xmin <= drone_x <= xmax and ymin <= drone_y <= ymax):
            status, reason = 'fault', 'Simulated follower reached the configured operating boundary'
            speed = yaw_rate = desired_speed = desired_yaw_rate = 0.

        samples.append({
            'time_s': time_s,
            'source': 'synthetic',
            'truth': {'drone_x_m': drone_x, 'drone_y_m': drone_y, 'drone_yaw_rad': yaw,
                      'target_x_m': target_x, 'target_y_m': target_y},
            'estimate': estimate,
            'desired': {'forward_m_s': desired_speed, 'yaw_rate_rad_s': desired_yaw_rate},
            'actual': {'forward_m_s': speed, 'yaw_rate_rad_s': yaw_rate},
            'state': status,
            'reason': reason,
            'physical_output': False,
        })
        if status == 'fault':
            # Retain a stopped record for the rest of the trace; never resume
            # automatically after an operating-boundary violation.
            for later_time, tx, ty, _, _ in parsed[index + 1:]:
                samples.append({'time_s': later_time, 'source': 'synthetic',
                    'truth': {'drone_x_m': drone_x, 'drone_y_m': drone_y, 'drone_yaw_rad': yaw,
                              'target_x_m': tx, 'target_y_m': ty},
                    'estimate': None, 'desired': {'forward_m_s': 0., 'yaw_rate_rad_s': 0.},
                    'actual': {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}, 'state': 'fault',
                    'reason': reason, 'physical_output': False})
            break

    return {'schema_version': 1, 'label': 'SYNTHETIC FOLLOW SIMULATION — not aircraft telemetry',
            'control_authority': 'simulation_only', 'physical_output': False,
            'limits': {'desired_distance_m': limits.desired_distance_m,
                       'min_approach_m': limits.min_approach_m,
                       'max_speed_m_s': limits.max_speed_m_s,
                       'max_acceleration_m_s2': limits.max_acceleration_m_s2,
                       'max_yaw_rate_rad_s': limits.max_yaw_rate_rad_s,
                       'bounds_m': list(limits.bounds_m),
                       'reacquire_frames': limits.reacquire_frames},
            'samples': samples}
