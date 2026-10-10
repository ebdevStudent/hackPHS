"""Arrival from distinct fresh pose estimates, never a physical stopping claim."""
from typing import Literal

import numpy as np
from pydantic import Field

from .localization import Pose
from .map_io import Contract, Nonnegative, Positive


class ArrivalPolicy(Contract):
    schema_version: Literal[1] = 1
    radius_m: Positive = .1
    max_uncertainty_m: Nonnegative = .05
    heading_tolerance_rad: Positive = .15
    angular_uncertainty_rad: Nonnegative = .05
    dwell_s: Nonnegative = .15
    min_distinct_frames: int = Field(default=3, ge=2, le=100)
    pose_max_age_s: Positive = .25


class ArrivalState(Contract):
    schema_version: Literal[1] = 1
    status: Literal['waiting', 'approaching', 'dwelling', 'arrived_estimate']
    estimated_arrival: bool
    distance_m: Nonnegative | None
    uncertainty_m: Nonnegative | None
    elapsed_s: Nonnegative
    fresh_frames: int = Field(ge=0, le=100)
    uncertainty_provisional: Literal[True] = True
    physical_acceptance: Literal[False] = False


class ArrivalTracker:
    def __init__(self, policy=None):
        self.policy = ArrivalPolicy.model_validate(policy.model_dump() if isinstance(policy, ArrivalPolicy) else policy or {})
        self.reset()

    def reset(self):
        self.context = None
        self.last_sequence = -1
        self.last_exposure = None
        self.last_payload = None
        self.start = None
        self.count = 0
        self.elapsed = 0.
        self.distance = self.uncertainty = None
        self.status = 'waiting'

    def snapshot(self):
        return ArrivalState(status=self.status, estimated_arrival=self.status == 'arrived_estimate',
            distance_m=self.distance, uncertainty_m=self.uncertainty, elapsed_s=self.elapsed, fresh_frames=self.count).model_dump()

    def update(self, pose, goal, now, heading_rad=None):
        try:
            pose = Pose.model_validate(pose.model_dump() if isinstance(pose, Pose) else pose)
            if not isinstance(goal, (tuple, list, np.ndarray)) or len(goal) != 3 or any(not isinstance(x, (float, int, np.number)) or isinstance(x, (bool, np.bool_)) for x in goal):
                raise ValueError('Expected finite metric arrival goal')
            goal = np.array(goal, float)
            if not np.isfinite(goal).all(): raise ValueError('Nonfinite arrival goal')
            if type(now) not in (float, int) or not np.isfinite(now): raise ValueError('Invalid arrival clock')
            if heading_rad is not None and (type(heading_rad) not in (float, int) or not np.isfinite(heading_rad)):
                raise ValueError('Invalid arrival heading')
            exposure = pose.timing.oldest_exposure()
            if now < pose.timing.host_received_s or not 0 <= now - exposure < self.policy.pose_max_age_s:
                raise ValueError('Stale/invalid arrival pose')
            context = (pose.bundle_id, pose.map_id, pose.map_version, pose.frame_id, pose.calibration_id, tuple(goal), heading_rad)
            if context != self.context:
                self.reset()
                self.context = context
            if pose.sequence < self.last_sequence: raise ValueError('Reordered arrival pose')
            if pose.sequence == self.last_sequence:
                if pose.model_dump_json() != self.last_payload: raise ValueError('Changed duplicate arrival pose')
                return self.snapshot()  # UI polling cannot add observations or dwell time.
            if self.last_exposure is not None and exposure <= self.last_exposure: raise ValueError('Nonadvancing arrival exposure')
            if self.last_exposure is not None and exposure - self.last_exposure >= self.policy.pose_max_age_s:
                self.start, self.count = None, 0
            self.last_sequence, self.last_exposure = pose.sequence, exposure
            self.last_payload = pose.model_dump_json()
            self.distance = float(np.linalg.norm(pose.position - goal))
            self.uncertainty = pose.uncertainty_m
            inside = self.uncertainty <= self.policy.max_uncertainty_m and self.distance + self.uncertainty <= self.policy.radius_m
            if heading_rad is not None:
                forward = np.array(pose.map_from_aircraft)[:2, 0]
                if np.linalg.norm(forward) < 1e-6: raise ValueError('Undefined horizontal aircraft heading')
                yaw = np.arctan2(forward[1], forward[0])
                error = abs(float(np.arctan2(np.sin(yaw - heading_rad), np.cos(yaw - heading_rad))))
                inside = inside and error + self.policy.angular_uncertainty_rad <= self.policy.heading_tolerance_rad
            if not inside:
                self.start, self.count, self.elapsed, self.status = None, 0, 0., 'approaching'
            else:
                if self.start is None: self.start = exposure
                self.count = min(self.policy.min_distinct_frames, self.count + 1)
                self.elapsed = exposure - self.start
                self.status = 'arrived_estimate' if self.count >= self.policy.min_distinct_frames and self.elapsed >= self.policy.dwell_s else 'dwelling'
            return self.snapshot()
        except Exception:
            self.reset()
            raise
