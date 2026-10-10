"""Self-contained navigation recordings and deterministic offline execution."""
import json
import math
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator

from .localization import Localizer, Observation, Timing
from .map_io import Bundle, Contract, Identifier, Nonnegative, Number, Vector
from .mission import Mission
from .navigation import Advisory, vector


class Input(Contract):
    t: Nonnegative
    kind: Literal['observations', 'loss', 'goal', 'resume', 'disable', 'tick', 'mission',
                   'mission_start', 'mission_advance', 'mission_abort', 'snapshot_saved']
    sequence: int | None = Field(default=None, ge=0)
    timing: Timing | None = None
    observations: list[Observation] | None = Field(default=None, max_length=587)
    source: Literal['vision_estimate', 'synthetic_estimate', 'recorded_estimate'] | None = None
    goal: Vector | None = None
    heading_rad: Number | None = None
    tag_id: int | None = Field(default=None, ge=0, lt=587)
    mission: Mission | None = None
    snapshot_sha256: str | None = None
    snapshot_source: Literal['camera', 'recording', 'synthetic'] | None = None
    reason: str | None = None

    @model_validator(mode='after')
    def fields(self):
        names = ('sequence', 'timing', 'observations', 'source', 'goal', 'heading_rad', 'tag_id', 'mission',
                 'snapshot_sha256', 'snapshot_source', 'reason')
        supplied = {key for key in names if getattr(self, key) is not None}
        required = {'observations': {'sequence', 'timing', 'observations', 'source'}, 'goal': {'goal'},
                    'loss': {'reason'}, 'mission': {'mission'},
                    'snapshot_saved': {'snapshot_sha256', 'snapshot_source'}}.get(self.kind, set())
        optional = {'goal': {'heading_rad', 'tag_id'}}.get(self.kind, set())
        if not required <= supplied or not supplied <= required | optional: raise ValueError('Invalid fields for navigation event')
        if self.heading_rad is not None and (type(self.heading_rad) not in (int, float) or not np.isfinite(self.heading_rad)):
            raise ValueError('Invalid goal heading')
        if self.timing is not None and self.timing.host_received_s > self.t: raise ValueError('Observation received after event')
        if self.snapshot_sha256 is not None and (len(self.snapshot_sha256) != 64 or any(c not in '0123456789abcdef' for c in self.snapshot_sha256)):
            raise ValueError('Invalid snapshot SHA256')
        return self


class Recording(Contract):
    schema_version: Literal[1]
    label: str
    bundle: Bundle
    bundle_sha256: Identifier
    physical_output: Literal[False]
    events: Annotated[list[Input], Field(min_length=1, max_length=100000)]

    @model_validator(mode='after')
    def integrity(self):
        if self.bundle_sha256 != self.bundle.digest: raise ValueError('Bundle hash mismatch')
        previous, seq = -1., -1
        for event in self.events:
            if event.t < previous: raise ValueError('Unordered navigation timeline')
            previous = event.t
            if event.kind == 'observations':
                if event.sequence <= seq: raise ValueError('Unordered navigation sequence')
                seq = event.sequence
                if event.source == 'synthetic_estimate' and not self.bundle.map.example: raise ValueError('Synthetic inputs need example bundle')
                if event.source != 'synthetic_estimate' and self.bundle.map.example: raise ValueError('Example geometry cannot localize physical/recorded camera')
            elif event.kind == 'mission':
                if event.mission.example != self.bundle.map.example: raise ValueError('Mission/bundle provenance mismatch')
                event.mission.validate_bundle(self.bundle)
            elif event.kind == 'snapshot_saved' and (event.snapshot_source == 'synthetic') != self.bundle.map.example:
                raise ValueError('Mission snapshot/bundle provenance mismatch')
        return self


def load_recording(path):
    path = Path(path)
    if path.stat().st_size > 50_000_000: raise ValueError('Recording exceeds size limit')
    # A completed recorder is JSONL; fixtures are a single JSON document.
    raw = path.read_text()
    if path.suffix == '.jsonl':
        lines = raw.splitlines()
        header = json.loads(lines[0])
        header['events'] = [json.loads(line) for line in lines[1:]]
        return Recording.model_validate(header)
    return Recording.model_validate_json(raw)


def apply_input(advisory, localizer, event, clock=lambda: 0.):
    if event.kind == 'observations':
        try: advisory.accept(localizer.solve(event.observations, event.timing, event.sequence, event.source), event.t)
        except ValueError as error: advisory.invalidate(str(error))
    elif event.kind == 'loss': advisory.invalidate(event.reason)
    elif event.kind == 'goal': advisory.set_goal(event.goal, event.heading_rad, event.tag_id)
    elif event.kind == 'disable': advisory.invalidate('operator disabled guidance')
    elif event.kind == 'mission': advisory.load_mission(event.mission)
    elif event.kind == 'mission_start': advisory.start_mission()
    elif event.kind == 'mission_advance': advisory.advance_mission()
    elif event.kind == 'mission_abort': advisory.abort_mission()
    elif event.kind == 'snapshot_saved': advisory.mission_snapshot_saved(event.snapshot_sha256, event.snapshot_source)
    elif event.kind == 'resume':
        try: advisory.resume(event.t)
        except ValueError as error: advisory.invalidate(str(error))
    # Replay uses the node budget, not machine-dependent wall time.
    return advisory.update(event.t, clock=clock)


def replay(recording):
    # Validate the entire file before performing any playback.
    recording = Recording.model_validate(recording.model_dump())
    advisory, localizer = Advisory(recording.bundle), Localizer(recording.bundle)
    samples = [{'t': e.t, **apply_input(advisory, localizer, e)} for e in recording.events]
    return {'schema_version': 1, 'label': recording.label + ' / deterministic replay / no bridge output',
            'map': recording.bundle.map.model_dump(),
            'bundle_sha256': recording.bundle_sha256, 'physical_telemetry': None, 'physical_output': False, 'samples': samples}


class Recorder:
    def __init__(self, path, bundle, label):
        self.path = Path(path)
        self.file = self.path.open('x')
        self.errors = 0
        self.file.write(json.dumps({'schema_version': 1, 'label': label, 'bundle': bundle.model_dump(), 'bundle_sha256': bundle.digest, 'physical_output': False}, allow_nan=False) + '\n')
        self.file.flush()

    def write(self, event):
        try:
            self.file.write(event.model_dump_json(exclude_none=True) + '\n')
            self.file.flush()
        except Exception: self.errors += 1

    def close(self):
        try: self.file.close()
        except Exception: self.errors += 1


class MockPlant:
    """Small bounded 3D plant with independent truth and estimated feedback."""
    def __init__(self, map_from_aircraft):
        import numpy as np
        transform = np.array(map_from_aircraft, dtype=float)
        if transform.shape != (4, 4) or not np.isfinite(transform).all(): raise ValueError('Invalid mock initial pose')
        self.position = transform[:3, 3].copy()
        self.yaw = float(np.arctan2(transform[1, 0], transform[0, 0]))
        self.velocity = np.zeros(3)
        self.yaw_rate = 0.

    def transform(self):
        import numpy as np
        result = np.eye(4)
        c, s = np.cos(self.yaw), np.sin(self.yaw)
        result[:3, :3] = [[c, -s, 0.], [s, c, 0.], [0., 0., 1.]]
        result[:3, 3] = self.position
        return result

    def step(self, target, heading_rad, dt, max_speed, acceleration, braking, max_yaw_rate, yaw_acceleration):
        import numpy as np
        if type(dt) not in (int, float) or not np.isfinite(dt) or dt <= 0: raise ValueError('Invalid mock step')
        if target is None:
            commanded = np.zeros(3)
            distance = 0.
        else:
            target = np.array(vector(target), dtype=float)
            delta = target - self.position
            distance = float(np.linalg.norm(delta))
            speed = min(max_speed, np.sqrt(2 * braking * max(0., distance - .025)))
            commanded = delta / max(distance, 1e-9) * speed
        change = commanded - self.velocity
        limit = braking if np.linalg.norm(commanded) + 1e-9 < np.linalg.norm(self.velocity) else acceleration
        change_norm = float(np.linalg.norm(change))
        if change_norm > limit * dt: change *= limit * dt / change_norm
        self.velocity += change
        displacement = self.velocity * dt
        self.position += displacement
        if heading_rad is None and target is not None and distance > .03:
            heading_rad = float(np.arctan2(target[1] - (self.position[1] - displacement[1]),
                                           target[0] - (self.position[0] - displacement[0])))
        if heading_rad is not None:
            error = float(np.arctan2(np.sin(heading_rad - self.yaw), np.cos(heading_rad - self.yaw)))
            desired_rate = float(np.clip(error / dt, -max_yaw_rate, max_yaw_rate))
            self.yaw_rate += float(np.clip(desired_rate - self.yaw_rate, -yaw_acceleration * dt, yaw_acceleration * dt))
            turn = self.yaw_rate * dt
            if abs(error) <= abs(turn):
                self.yaw, self.yaw_rate = float(heading_rad), 0.
            else:
                self.yaw = float(np.arctan2(np.sin(self.yaw + turn), np.cos(self.yaw + turn)))
        return {'commanded_velocity_m_s': commanded.tolist(), 'velocity_m_s': self.velocity.tolist(),
                'acceleration_m_s2': (change / dt).tolist(), 'yaw_rate_rad_s': self.yaw_rate,
                'distance_to_waypoint_m': distance}


def simulation(recording, step_s=.05, limit=600, *, mission=None, observation_delay_s=.05, pixel_noise_px=.25,
               acceleration_m_s2=.6, braking_m_s2=.8, yaw_acceleration_rad_s2=8.):
    """Kinematic MOCK OUTPUT ONLY; no aircraft/serial/firmware access.

    Feedback uses rendered noisy tag corners, not exact state. Truth is separate.
    """
    import cv2
    import numpy as np
    if not recording.bundle.map.example: raise ValueError('Simulation requires example geometry')
    if type(step_s) not in (int, float) or not np.isfinite(step_s) or not 0 < step_s < recording.bundle.policy.pose_max_age_s: raise ValueError('Invalid simulation step')
    if type(limit) is not int or not 1 <= limit <= 10000: raise ValueError('Invalid simulation limit')
    values = (observation_delay_s, pixel_noise_px, acceleration_m_s2, braking_m_s2, yaw_acceleration_rad_s2)
    if any(type(v) not in (int, float) or not np.isfinite(v) for v in values) or observation_delay_s < 0 or pixel_noise_px < 0 or min(acceleration_m_s2, braking_m_s2, yaw_acceleration_rad_s2) <= 0:
        raise ValueError('Invalid mock dynamics or feedback policy')
    if observation_delay_s >= recording.bundle.policy.pose_max_age_s: raise ValueError('Mock feedback delay must fit the pose freshness bound')
    first = next((e for e in recording.events if e.kind == 'observations' and e.observations), None)
    goal_event = next((e for e in recording.events if e.kind == 'goal'), None)
    if first is None or (goal_event is None and mission is None): raise ValueError('Simulation needs initial observations and a goal or mission')
    b, localizer = recording.bundle, Localizer(recording.bundle)
    initial = localizer.solve(first.observations, first.timing, 0, 'synthetic_estimate')
    plant = MockPlant(initial.map_from_aircraft)
    advisory = Advisory(b)
    if mission is None:
        advisory.set_goal(goal_event.goal, goal_event.heading_rad, goal_event.tag_id)
    else:
        advisory.load_mission(mission)
        advisory.start_mission()
    samples = []
    restored = False
    delay_steps = int(math.ceil(observation_delay_s / step_s))
    # Seed pre-roll history so the first simulated feedback frame has a
    # distinct delayed exposure. Reusing the initial exposure would make the
    # pose guard correctly reject frame two as nonadvancing.
    history = [(plant.transform(), 1. - (delay_steps - index) * step_s)
               for index in range(delay_steps)]
    from .navigation_fixtures import observations_for
    for i in range(limit):
        now = 1. + i * step_s
        history.append((plant.transform(), now))
        measured, exposure = history[max(0, len(history) - 1 - delay_steps)]
        observations = observations_for(b, measured, visible_only=True, noise_std=pixel_noise_px, seed=i)
        # Feedback loss is applied to the delayed camera image, demonstrating
        # stale-pose neutralization, reacquisition and deliberate restoration.
        if 34 <= i < 38: observations = []
        try:
            timing = Timing(host_received_s=now, exposure_s=exposure, provenance='synthetic')
            acquired = advisory.accept(localizer.solve(observations, timing, i, 'synthetic_estimate'), now)
        except ValueError as error: advisory.invalidate(str(error)); acquired = False
        if acquired and (not restored or i == 43): advisory.resume(now); restored = True
        state = advisory.update(now, clock=lambda: 0.)
        target = state['next_waypoint'] if state['guidance_enabled'] and state['status'] != 'goal reached' else None
        heading = state.get('waypoint_heading_rad') if target is not None else None
        dynamics = plant.step(target, heading, step_s, b.policy.speed_m_s, acceleration_m_s2, braking_m_s2,
                              b.policy.max_angular_speed_rad_s, yaw_acceleration_rad_s2)
        from .navigation import clearance
        safe_margin = state['clearance_m'] if state['clearance_m'] is not None else clearance(b, b.policy.max_uncertainty_m)
        if np.linalg.norm(plant.velocity) > 1e-9 and not advisory.planner.segment_clear(history[-1][0][:3, 3], plant.position, safe_margin):
            raise ValueError('Mock plant swept-envelope clearance violation')
        if mission is not None and advisory.mission_runner is not None and advisory.mission_runner.status == 'snapshot_pending':
            from .synthetic_navigation import tag_image
            image = tag_image(b.calibration, b.survey, measured, noise_std=pixel_noise_px, seed=i)
            ok, encoded = cv2.imencode('.png', image)
            if not ok: raise ValueError('Mock mission snapshot encoding failed')
            import hashlib
            digest = hashlib.sha256(encoded.tobytes()).hexdigest()
            advisory.mission_snapshot_saved(digest, 'synthetic')
            state = advisory.snapshot(now)
            if advisory.mission_runner.status == 'target_complete' and advisory.mission_runner.index + 1 < len(advisory.mission_runner.mission.targets):
                advisory.advance_mission()
                if acquired and advisory.guard.status == 'valid': advisory.resume(now)
        samples.append({'t': now, **state, 'simulation_truth_position_m': plant.position.tolist(),
            'simulation_truth_heading_rad': plant.yaw, 'mock_velocity_m_s': dynamics['velocity_m_s'],
            'mock_commanded_velocity_m_s': dynamics['commanded_velocity_m_s'],
            'mock_acceleration_m_s2': dynamics['acceleration_m_s2'], 'mock_yaw_rate_rad_s': dynamics['yaw_rate_rad_s'],
            'mock_feedback_age_s': now - exposure})
        if mission is None and state['status'] == 'goal reached' and np.linalg.norm(plant.velocity) < .02: break
        if mission is not None and advisory.mission_runner is not None:
            runner = advisory.mission_runner
            if runner.status in ('target_complete', 'complete', 'aborted') and runner.index + 1 == len(runner.mission.targets):
                break
    return {'schema_version': 1, 'label': 'SYNTHETIC estimated-vision waypoint follower / MOCK OUTPUT ONLY', 'map': b.map.model_dump(),
            'physical_output': False, 'physical_telemetry': None, 'mock_dynamics': {'acceleration_m_s2': acceleration_m_s2,
            'braking_m_s2': braking_m_s2, 'yaw_acceleration_rad_s2': yaw_acceleration_rad_s2,
            'observation_delay_s': observation_delay_s, 'pixel_noise_px': pixel_noise_px},
            'mission': None if mission is None else advisory.mission_runner.snapshot(), 'samples': samples}
