"""Map-independent AprilTag relative pose and target-loss tracking."""
import math
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator

from .localization import Observation, Timing, tag_points
from .map_io import Calibration, Contract, Identifier, Matrix, Nonnegative, Number, Positive, rigid
from .roster import LandingSite, Person
from .tag_detector import AprilTagDetector


class TargetPose(Contract):
    schema_version: Literal[1] = 1
    person_id: Identifier
    tag_id: int = Field(ge=0, lt=587)
    sequence: int = Field(ge=0)
    source: Literal['synthetic_estimate', 'recorded_estimate', 'vision_estimate']
    timing: Timing
    camera_from_tag: Matrix
    aircraft_from_tag: Matrix
    range_m: Positive
    bearing_rad: Number
    reprojection_px: Nonnegative
    ambiguity_gap_px: Nonnegative

    @model_validator(mode='after')
    def geometry(self):
        camera = rigid(self.camera_from_tag)
        aircraft = rigid(self.aircraft_from_tag)
        if not math.isclose(float(np.linalg.norm(camera[:3, 3])), self.range_m, rel_tol=1e-5, abs_tol=1e-6):
            raise ValueError('range_m does not match camera_from_tag')
        expected_bearing = math.atan2(aircraft[1, 3], aircraft[0, 3])
        if not math.isclose(expected_bearing, self.bearing_rad, rel_tol=1e-5, abs_tol=1e-6):
            raise ValueError('bearing_rad does not match aircraft-relative pose')
        return self


class TargetTrackerSnapshot(Contract):
    state: Literal['acquiring', 'tracking', 'lost', 'reacquiring', 'unavailable']
    person_id: Identifier
    tag_id: int = Field(ge=0, lt=587)
    sequence: int | None = Field(default=None, ge=0)
    fresh_frames: int = Field(ge=0, le=100)
    loss_event: bool
    reason: str | None = Field(default=None, max_length=240)
    pose: TargetPose | None = None


class LandingPose(Contract):
    """Relative pad pose computed from a pad tag and its measured pad transform."""
    schema_version: Literal[1] = 1
    site_id: Identifier
    tag_id: int = Field(ge=0, lt=587)
    sequence: int = Field(ge=0)
    source: Literal['synthetic_estimate', 'recorded_estimate', 'vision_estimate']
    timing: Timing
    camera_from_tag: Matrix
    aircraft_from_tag: Matrix
    pad_from_tag: Matrix
    aircraft_from_pad: Matrix
    range_m: Positive
    bearing_rad: Number
    pad_heading_rad: Number
    reprojection_px: Nonnegative
    ambiguity_gap_px: Nonnegative

    @model_validator(mode='after')
    def geometry(self):
        camera, aircraft_tag, pad_tag, aircraft_pad = map(
            rigid, (self.camera_from_tag, self.aircraft_from_tag, self.pad_from_tag, self.aircraft_from_pad))
        expected = aircraft_tag @ np.linalg.inv(pad_tag)
        if not np.allclose(expected, aircraft_pad, atol=1e-6):
            raise ValueError('aircraft_from_pad does not match the tag-to-pad transform')
        x, y = float(aircraft_pad[0, 3]), float(aircraft_pad[1, 3])
        if x <= 0 or not math.isclose(math.hypot(x, y), self.range_m, rel_tol=1e-5, abs_tol=1e-6):
            raise ValueError('Landing-pad range must match a forward aircraft-relative pad pose')
        if not math.isclose(math.atan2(y, x), self.bearing_rad, abs_tol=1e-6):
            raise ValueError('Landing-pad bearing does not match its pose')
        heading = math.atan2(float(aircraft_pad[1, 0]), float(aircraft_pad[0, 0]))
        if not math.isclose(heading, self.pad_heading_rad, abs_tol=1e-6):
            raise ValueError('Landing-pad heading does not match its pose')
        return self


class LandingTrackerSnapshot(Contract):
    state: Literal['acquiring', 'approaching', 'lost', 'reacquiring', 'unavailable']
    site_id: Identifier
    tag_id: int = Field(ge=0, lt=587)
    sequence: int | None = Field(default=None, ge=0)
    fresh_frames: int = Field(ge=0, le=100)
    loss_event: bool
    reason: str | None = Field(default=None, max_length=240)
    pose: LandingPose | None = None


def _solve_relative_tag(observation, tag_id, tag_size_m, calibration, *,
                        min_ambiguity_gap_px, max_reprojection_px):
    """Shared camera/aircraft relative pose solve; no map or actuator involved."""
    import cv2

    observation = Observation.model_validate(observation.model_dump() if isinstance(observation, Observation) else observation)
    calibration = Calibration.model_validate(calibration.model_dump() if isinstance(calibration, Calibration) else calibration)
    if observation.id != tag_id:
        raise ValueError('Observed tag does not match the selected roster entry')
    if type(tag_id) is not int or not 0 <= tag_id < 587:
        raise ValueError('tag_id is outside the supported tag36h11 range')
    if type(tag_size_m) not in (int, float) or not math.isfinite(tag_size_m) or tag_size_m <= 0:
        raise ValueError('Measured tag size must be finite and positive')
    if type(min_ambiguity_gap_px) not in (int, float) or not math.isfinite(min_ambiguity_gap_px) or min_ambiguity_gap_px < 0:
        raise ValueError('Ambiguity threshold must be finite and nonnegative')
    if type(max_reprojection_px) not in (int, float) or not math.isfinite(max_reprojection_px) or max_reprojection_px <= 0:
        raise ValueError('Reprojection limit must be finite and positive')

    pixels = np.asarray(observation.corners, dtype=float)
    k = np.asarray(calibration.intrinsics, dtype=float)
    distortion = np.asarray(calibration.distortion, dtype=float)
    if observation.pixel_space == 'undistorted':
        rays = np.column_stack(((pixels[:, 0] - k[0, 2]) / k[0, 0],
                                (pixels[:, 1] - k[1, 2]) / k[1, 1], np.ones(4)))
        pixels = cv2.projectPoints(rays, np.zeros(3), np.zeros(3), k, distortion)[0].reshape(4, 2)
    width, height = calibration.image_size
    if np.any(pixels < 0) or np.any(pixels >= [width, height]):
        raise ValueError('Tag corners are outside the calibrated image')

    points = tag_points(tag_size_m)
    result = cv2.solvePnPGeneric(points, pixels, k, distortion, flags=cv2.SOLVEPNP_IPPE_SQUARE)
    if len(result) < 4 or int(result[0]) < 1:
        raise ValueError('AprilTag pose could not be solved')
    candidates = []
    for rotation, translation in zip(result[1], result[2]):
        camera_from_tag = np.eye(4)
        camera_from_tag[:3, :3] = cv2.Rodrigues(rotation)[0]
        camera_from_tag[:3, 3] = np.asarray(translation).reshape(3)
        depths = points @ camera_from_tag[:3, :3].T + camera_from_tag[:3, 3]
        if np.any(depths[:, 2] <= .01):
            continue
        projected = cv2.projectPoints(points, rotation, translation, k, distortion)[0].reshape(-1, 2)
        error = float(np.sqrt(np.mean(np.sum((projected - pixels) ** 2, axis=1))))
        if math.isfinite(error):
            candidates.append((error, camera_from_tag))
    if not candidates:
        raise ValueError('No positive-depth AprilTag pose solution')
    candidates.sort(key=lambda candidate: candidate[0])
    error, camera_from_tag = candidates[0]
    if error > max_reprojection_px:
        raise ValueError('AprilTag reprojection error exceeds the configured limit')
    gap = 1e6
    for other_error, other in candidates[1:]:
        if np.linalg.norm(camera_from_tag - other) > 1e-3:
            gap = max(0., other_error - error)
            break
    if gap < min_ambiguity_gap_px:
        raise ValueError('AprilTag pose is ambiguous')

    aircraft_from_camera = np.asarray(calibration.aircraft_from_camera, dtype=float)
    aircraft_from_tag = aircraft_from_camera @ camera_from_tag
    forward = float(aircraft_from_tag[0, 3])
    if forward <= 0:
        raise ValueError('Selected tag is not in front of the aircraft')
    range_m = float(np.linalg.norm(camera_from_tag[:3, 3]))
    bearing = math.atan2(float(aircraft_from_tag[1, 3]), forward)
    return {'camera_from_tag': camera_from_tag, 'aircraft_from_tag': aircraft_from_tag,
            'range_m': range_m, 'bearing_rad': bearing, 'reprojection_px': error,
            'ambiguity_gap_px': gap}


def estimate_relative_tag_pose(observation, person, calibration, *, sequence, timing,
                               source='synthetic_estimate', min_ambiguity_gap_px=0.4,
                               max_reprojection_px=3.0):
    """Estimate a moving tag's pose without consulting a map or fixed survey."""
    person = Person.model_validate(person.model_dump() if isinstance(person, Person) else person)
    if type(sequence) is not int or sequence < 0:
        raise ValueError('sequence must be a nonnegative integer')
    timing = Timing.model_validate(timing.model_dump() if isinstance(timing, Timing) else timing)
    if source not in ('synthetic_estimate', 'recorded_estimate', 'vision_estimate'):
        raise ValueError('Unknown target pose source')
    result = _solve_relative_tag(observation, person.tag_id, person.tag_size_m, calibration,
        min_ambiguity_gap_px=min_ambiguity_gap_px, max_reprojection_px=max_reprojection_px)
    return TargetPose(person_id=person.person_id, tag_id=person.tag_id, sequence=sequence,
        source=source, timing=timing, camera_from_tag=result['camera_from_tag'].tolist(),
        aircraft_from_tag=result['aircraft_from_tag'].tolist(), range_m=result['range_m'],
        bearing_rad=result['bearing_rad'], reprojection_px=result['reprojection_px'],
        ambiguity_gap_px=result['ambiguity_gap_px'])


def estimate_relative_landing_pose(observation, site, calibration, *, sequence, timing,
                                   source='synthetic_estimate', min_ambiguity_gap_px=0.4,
                                   max_reprojection_px=3.0):
    """Estimate pad center/orientation relative to aircraft using a surveyed tag offset."""
    site = LandingSite.model_validate(site.model_dump() if isinstance(site, LandingSite) else site)
    if type(sequence) is not int or sequence < 0:
        raise ValueError('sequence must be a nonnegative integer')
    timing = Timing.model_validate(timing.model_dump() if isinstance(timing, Timing) else timing)
    if source not in ('synthetic_estimate', 'recorded_estimate', 'vision_estimate'):
        raise ValueError('Unknown landing pose source')
    result = _solve_relative_tag(observation, site.tag_id, site.tag_size_m, calibration,
        min_ambiguity_gap_px=min_ambiguity_gap_px, max_reprojection_px=max_reprojection_px)
    pad_from_tag = np.asarray(site.pad_from_tag, dtype=float)
    aircraft_from_pad = result['aircraft_from_tag'] @ np.linalg.inv(pad_from_tag)
    x, y = float(aircraft_from_pad[0, 3]), float(aircraft_from_pad[1, 3])
    if x <= 0:
        raise ValueError('Landing pad center is not in front of the aircraft')
    return LandingPose(site_id=site.site_id, tag_id=site.tag_id, sequence=sequence,
        source=source, timing=timing, camera_from_tag=result['camera_from_tag'].tolist(),
        aircraft_from_tag=result['aircraft_from_tag'].tolist(), pad_from_tag=pad_from_tag.tolist(),
        aircraft_from_pad=aircraft_from_pad.tolist(), range_m=math.hypot(x, y),
        bearing_rad=math.atan2(y, x),
        pad_heading_rad=math.atan2(float(aircraft_from_pad[1, 0]), float(aircraft_from_pad[0, 0])),
        reprojection_px=result['reprojection_px'], ambiguity_gap_px=result['ambiguity_gap_px'])


class RelativeTargetTracker:
    """Freshness-gated acquire/loss/reacquire state for one roster target."""
    def __init__(self, person, *, reacquire_frames=3, max_age_s=.25, loss_after_misses=1):
        self.person = Person.model_validate(person.model_dump() if isinstance(person, Person) else person)
        if type(reacquire_frames) is not int or not 1 <= reacquire_frames <= 30:
            raise ValueError('reacquire_frames must be an integer from 1 to 30')
        if type(loss_after_misses) is not int or not 1 <= loss_after_misses <= 30:
            raise ValueError('loss_after_misses must be an integer from 1 to 30')
        if type(max_age_s) not in (int, float) or not math.isfinite(max_age_s) or max_age_s <= 0:
            raise ValueError('max_age_s must be finite and positive')
        self.reacquire_frames, self.max_age_s, self.loss_after_misses = reacquire_frames, float(max_age_s), loss_after_misses
        self.state = 'acquiring'
        self.last_sequence = None
        self.last_pose = None
        self.fresh_frames = 0
        self.misses = 0
        self.reason = 'Waiting for the selected AprilTag'

    def _snapshot(self, loss_event=False):
        return TargetTrackerSnapshot(state=self.state, person_id=self.person.person_id,
                                     tag_id=self.person.tag_id, sequence=self.last_sequence,
                                     fresh_frames=self.fresh_frames, loss_event=loss_event,
                                     reason=self.reason, pose=self.last_pose if self.state == 'tracking' else None)

    def _lose(self, reason):
        loss_event = self.state in ('tracking', 'reacquiring')
        self.state = 'lost'
        self.last_pose = None
        self.fresh_frames = 0
        self.misses += 1
        self.reason = reason
        return self._snapshot(loss_event)

    def update(self, pose=None, *, now_s):
        if type(now_s) not in (int, float) or not math.isfinite(now_s) or now_s < 0:
            raise ValueError('now_s must be finite and nonnegative')
        if pose is None:
            if self.misses + 1 < self.loss_after_misses and self.state == 'tracking':
                self.misses += 1
                self.reason = 'Target observation missing; holding simulated motion'
                self.last_pose = None
                return self._snapshot(False)
            return self._lose('Target tag not detected')
        pose = TargetPose.model_validate(pose.model_dump() if isinstance(pose, TargetPose) else pose)
        if pose.person_id != self.person.person_id or pose.tag_id != self.person.tag_id:
            return self._lose('Observation identity differs from the selected roster entry')
        if self.last_sequence is not None and pose.sequence <= self.last_sequence:
            if self.last_pose is not None and now_s - self.last_pose.timing.oldest_exposure() > self.max_age_s:
                return self._lose('Target observation is stale')
            self.reason = 'Out-of-order observation ignored'
            return self._snapshot(False)
        self.last_sequence = pose.sequence
        try:
            age = now_s - pose.timing.oldest_exposure()
        except ValueError as error:
            return self._lose(str(error))
        if age < -0.001 or age > self.max_age_s:
            return self._lose('Target observation is stale or from the future')
        self.misses = 0
        if self.state == 'tracking':
            self.last_pose = pose
            self.reason = None
            return self._snapshot(False)
        self.fresh_frames += 1
        self.last_pose = pose
        if self.fresh_frames >= self.reacquire_frames:
            self.state = 'tracking'
            self.reason = None
        else:
            self.state = 'reacquiring' if self.last_sequence != 0 else 'acquiring'
            self.reason = f'Need {self.reacquire_frames - self.fresh_frames} more fresh observations'
        return self._snapshot(False)

    def reset(self, reason='Target tracker reset'):
        self.state = 'acquiring'
        self.last_sequence = None
        self.last_pose = None
        self.fresh_frames = self.misses = 0
        self.reason = reason
        return self._snapshot(False)


class LandingTagTracker:
    """Fresh, stable AprilTag pad-pose gate; it does not control descent."""
    def __init__(self, site, *, reacquire_frames=3, max_age_s=.25, max_range_m=3.,
                 max_bearing_rad=.5, max_reprojection_px=3., min_ambiguity_gap_px=.4,
                 stable_range_delta_m=.12, stable_bearing_delta_rad=.08,
                 stable_heading_delta_rad=.1):
        self.site = LandingSite.model_validate(site.model_dump() if isinstance(site, LandingSite) else site)
        settings = (max_age_s, max_range_m, max_bearing_rad, max_reprojection_px,
                    min_ambiguity_gap_px, stable_range_delta_m, stable_bearing_delta_rad,
                    stable_heading_delta_rad)
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in settings):
            raise ValueError('Landing tracker limits must be finite numbers')
        if max_age_s <= 0 or max_range_m <= 0 or not 0 < max_bearing_rad <= math.pi:
            raise ValueError('Landing freshness, range and bearing limits are invalid')
        if max_reprojection_px <= 0 or min_ambiguity_gap_px < 0:
            raise ValueError('Landing pose quality limits are invalid')
        if min(stable_range_delta_m, stable_bearing_delta_rad, stable_heading_delta_rad) <= 0:
            raise ValueError('Landing stability limits must be positive')
        if type(reacquire_frames) is not int or not 1 <= reacquire_frames <= 30:
            raise ValueError('reacquire_frames must be an integer from 1 to 30')
        self.max_age_s, self.max_range_m = float(max_age_s), float(max_range_m)
        self.max_bearing_rad, self.max_reprojection_px = float(max_bearing_rad), float(max_reprojection_px)
        self.min_ambiguity_gap_px = float(min_ambiguity_gap_px)
        self.stable_range_delta_m = float(stable_range_delta_m)
        self.stable_bearing_delta_rad = float(stable_bearing_delta_rad)
        self.stable_heading_delta_rad = float(stable_heading_delta_rad)
        self.reacquire_frames = reacquire_frames
        self.state, self.reason = 'acquiring', 'Waiting for the configured AprilTag landing pad'
        self.last_sequence, self.last_pose, self.fresh_frames = None, None, 0

    def _snapshot(self, loss_event=False):
        return LandingTrackerSnapshot(state=self.state, site_id=self.site.site_id,
            tag_id=self.site.tag_id, sequence=self.last_sequence, fresh_frames=self.fresh_frames,
            loss_event=loss_event, reason=self.reason,
            pose=self.last_pose if self.state == 'approaching' else None)

    def _lose(self, reason):
        loss_event = self.state in ('approaching', 'reacquiring')
        self.state, self.last_pose, self.fresh_frames = 'lost', None, 0
        self.reason = reason
        return self._snapshot(loss_event)

    @staticmethod
    def _angle_delta(a, b):
        return (a - b + math.pi) % (2 * math.pi) - math.pi

    def update(self, pose=None, *, now_s):
        if type(now_s) not in (int, float) or not math.isfinite(now_s) or now_s < 0:
            raise ValueError('now_s must be a finite nonnegative number')
        if pose is None:
            return self._lose('Configured landing AprilTag is not visible')
        pose = LandingPose.model_validate(pose.model_dump() if isinstance(pose, LandingPose) else pose)
        if pose.site_id != self.site.site_id or pose.tag_id != self.site.tag_id:
            return self._lose('Landing tag identity differs from the selected pad')
        if self.last_sequence is not None and pose.sequence <= self.last_sequence:
            if self.last_pose is not None and now_s - self.last_pose.timing.oldest_exposure() > self.max_age_s:
                return self._lose('Landing tag observation is stale')
            self.reason = 'Out-of-order landing observation ignored'
            return self._snapshot(False)
        self.last_sequence = pose.sequence
        try:
            age = now_s - pose.timing.oldest_exposure()
        except ValueError as error:
            return self._lose(str(error))
        if age < -.001 or age > self.max_age_s:
            return self._lose('Landing tag observation is stale or from the future')
        if (pose.range_m > self.max_range_m or abs(pose.bearing_rad) > self.max_bearing_rad or
                abs(self._angle_delta(pose.pad_heading_rad, 0.)) > self.site.approach_tolerance_rad):
            return self._lose('Landing pad is outside the configured approach geometry')
        if pose.reprojection_px > self.max_reprojection_px or pose.ambiguity_gap_px < self.min_ambiguity_gap_px:
            return self._lose('Landing pad pose quality is insufficient')
        previous = self.last_pose
        stable = previous is None or (
            abs(pose.range_m - previous.range_m) <= self.stable_range_delta_m and
            abs(self._angle_delta(pose.bearing_rad, previous.bearing_rad)) <= self.stable_bearing_delta_rad and
            abs(self._angle_delta(pose.pad_heading_rad, previous.pad_heading_rad)) <= self.stable_heading_delta_rad)
        self.fresh_frames = self.fresh_frames + 1 if stable else 1
        self.last_pose = pose
        if self.fresh_frames >= self.reacquire_frames:
            self.state, self.reason = 'approaching', 'Landing pad pose is fresh, stable, and within the configured approach geometry.'
        else:
            self.state = 'reacquiring' if self.last_sequence else 'acquiring'
            self.reason = f'Need {self.reacquire_frames - self.fresh_frames} more stable AprilTag observations.'
        return self._snapshot(False)


class TargetVision:
    """Per-frame relative tracker; caller chooses the worker and timing bound."""
    def __init__(self, person, calibration, *, delay_bound_s, reacquire_frames=3,
                 max_age_s=.25, max_reprojection_px=3.0, min_ambiguity_gap_px=.4):
        self.person = Person.model_validate(person.model_dump() if isinstance(person, Person) else person)
        self.calibration = Calibration.model_validate(calibration.model_dump() if isinstance(calibration, Calibration) else calibration)
        if type(delay_bound_s) not in (int, float) or not math.isfinite(delay_bound_s) or delay_bound_s <= 0:
            raise ValueError('A measured positive delay bound is required')
        self.delay_bound_s = float(delay_bound_s)
        self.tracker = RelativeTargetTracker(self.person, reacquire_frames=reacquire_frames, max_age_s=max_age_s)
        self.detector = AprilTagDetector(self.calibration)
        self.max_reprojection_px, self.min_ambiguity_gap_px = max_reprojection_px, min_ambiguity_gap_px

    def process(self, image, *, sequence, captured_s=None, received_s, source='recorded_estimate'):
        if type(sequence) is not int or sequence < 0:
            raise ValueError('sequence must be a nonnegative integer')
        if type(received_s) not in (int, float) or not math.isfinite(received_s) or (captured_s is not None and
                (type(captured_s) not in (int, float) or not math.isfinite(captured_s) or received_s < captured_s)):
            raise ValueError('Invalid capture/receipt times')
        observations = self.detector.detect(image)
        matches = [item for item in observations if item.id == self.person.tag_id]
        if len(matches) != 1:
            return self.tracker.update(None, now_s=received_s)
        timing = (Timing(host_received_s=received_s, exposure_s=captured_s,
                         provenance='exposure_monotonic', delay_bound_s=self.delay_bound_s)
                  if captured_s is not None else
                  Timing(host_received_s=received_s, provenance='host_read',
                         delay_bound_s=self.delay_bound_s))
        try:
            pose = estimate_relative_tag_pose(matches[0], self.person, self.calibration,
                sequence=sequence, timing=timing, source=source,
                min_ambiguity_gap_px=self.min_ambiguity_gap_px,
                max_reprojection_px=self.max_reprojection_px)
        except (ValueError, TypeError) as error:
            loss = self.tracker.update(None, now_s=received_s)
            self.tracker.reason = str(error)[:240]
            return self.tracker._snapshot(loss.loss_event)
        return self.tracker.update(pose, now_s=received_s)


class LandingVision:
    """Shared AprilTag detector plus relative pad pose/stability tracker."""
    def __init__(self, site, calibration, *, delay_bound_s, reacquire_frames=3,
                 max_age_s=.25, max_reprojection_px=3., min_ambiguity_gap_px=.4):
        self.site = LandingSite.model_validate(site.model_dump() if isinstance(site, LandingSite) else site)
        self.calibration = Calibration.model_validate(calibration.model_dump() if isinstance(calibration, Calibration) else calibration)
        if type(delay_bound_s) not in (int, float) or not math.isfinite(delay_bound_s) or delay_bound_s <= 0:
            raise ValueError('A measured positive delay bound is required')
        self.delay_bound_s = float(delay_bound_s)
        self.max_reprojection_px, self.min_ambiguity_gap_px = max_reprojection_px, min_ambiguity_gap_px
        self.tracker = LandingTagTracker(self.site, reacquire_frames=reacquire_frames, max_age_s=max_age_s,
            max_reprojection_px=max_reprojection_px, min_ambiguity_gap_px=min_ambiguity_gap_px)
        self.detector = AprilTagDetector(self.calibration)

    def process(self, image, *, sequence, captured_s=None, received_s,
                source='recorded_estimate'):
        if type(sequence) is not int or sequence < 0:
            raise ValueError('sequence must be a nonnegative integer')
        if type(received_s) not in (int, float) or not math.isfinite(received_s) or (captured_s is not None and
                (type(captured_s) not in (int, float) or not math.isfinite(captured_s) or received_s < captured_s)):
            raise ValueError('Invalid capture/receipt times')
        observations = self.detector.detect(image)
        matches = [item for item in observations if item.id == self.site.tag_id]
        if len(matches) != 1:
            return self.tracker.update(None, now_s=received_s)
        timing = (Timing(host_received_s=received_s, exposure_s=captured_s,
                         provenance='exposure_monotonic', delay_bound_s=self.delay_bound_s)
                  if captured_s is not None else Timing(host_received_s=received_s,
                         provenance='host_read', delay_bound_s=self.delay_bound_s))
        try:
            pose = estimate_relative_landing_pose(matches[0], self.site, self.calibration,
                sequence=sequence, timing=timing, source=source,
                min_ambiguity_gap_px=self.min_ambiguity_gap_px,
                max_reprojection_px=self.max_reprojection_px)
        except (ValueError, TypeError) as error:
            loss = self.tracker.update(None, now_s=received_s)
            self.tracker.reason = str(error)[:240]
            return self.tracker._snapshot(loss.loss_event)
        return self.tracker.update(pose, now_s=received_s)
