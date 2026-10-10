"""AprilTag observations -> estimated pose. No bridge/control imports or outputs."""
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator

from .calibration import aircraft_pose, invert, undistort
from .map_io import CameraGeometry, Contract, Identifier, Matrix, Nonnegative, Number, Survey, Vector, rigid


class Observation(Contract):
    id: int = Field(ge=0, lt=587)
    corners: Annotated[list[Annotated[list[Number], Field(min_length=2, max_length=2)]], Field(min_length=4, max_length=4)]
    pixel_space: Literal['distorted', 'undistorted'] = 'distorted'

    @model_validator(mode='after')
    def shape(self):
        p = np.array(self.corners)
        edges = np.roll(p, -1, axis=0) - p
        crosses = edges[:, 0] * np.roll(edges[:, 1], -1) - edges[:, 1] * np.roll(edges[:, 0], -1)
        if not np.all(crosses > 1e-3): raise ValueError('Corners must be convex TL/TR/BR/BL in image order')
        return self


class Timing(Contract):
    host_received_s: Nonnegative
    exposure_s: Nonnegative | None = None
    provenance: Literal['exposure_monotonic', 'host_read', 'recorded_timeline', 'synthetic']
    delay_bound_s: Nonnegative | None = None

    @model_validator(mode='after')
    def consistency(self):
        if self.exposure_s is not None and self.exposure_s > self.host_received_s: raise ValueError('Exposure after receipt')
        if (self.provenance == 'host_read') != (self.exposure_s is None): raise ValueError('Exposure provenance mismatch')
        return self

    def oldest_exposure(self):
        if self.exposure_s is not None: return self.exposure_s
        if self.delay_bound_s is None: raise ValueError('Unknown camera exposure age: measure a delay upper bound')
        return self.host_received_s - self.delay_bound_s


class Pose(Contract):
    sequence: int = Field(ge=0)
    bundle_id: Identifier
    map_id: Identifier
    map_version: int = Field(ge=1)
    frame_id: Identifier
    calibration_id: Identifier
    source: Literal['vision_estimate', 'synthetic_estimate', 'recorded_estimate']
    timing: Timing
    map_from_aircraft: Matrix
    uncertainty_m: Nonnegative
    reprojection_px: Nonnegative
    ambiguity_gap_px: Nonnegative
    tag_ids: Annotated[list[int], Field(min_length=1, max_length=587)]

    @model_validator(mode='after')
    def transform(self):
        rigid(self.map_from_aircraft)
        if any(type(i) is not int or not 0 <= i < 587 for i in self.tag_ids) or len(set(self.tag_ids)) != len(self.tag_ids): raise ValueError('Invalid supporting tags')
        return self

    @property
    def position(self): return np.array(self.map_from_aircraft)[:3, 3]


def tag_points(size):
    half = size / 2
    return np.array([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]], dtype=float)


class CameraEstimate(Contract):
    """Camera pose only; deliberately carries no aircraft or control authority."""
    map_from_camera: Matrix
    uncertainty_m: Nonnegative
    reprojection_px: Nonnegative
    ambiguity_gap_px: Nonnegative
    tag_ids: Annotated[list[int], Field(min_length=1, max_length=587)]

    @model_validator(mode='after')
    def geometry(self):
        rigid(self.map_from_camera)
        if any(type(i) is not int or not 0 <= i < 587 for i in self.tag_ids) or len(set(self.tag_ids)) != len(self.tag_ids):
            raise ValueError('Invalid supporting tags')
        return self


class CameraPoseSolver:
    def __init__(self, calibration, survey):
        self.calibration = calibration if isinstance(calibration, CameraGeometry) else CameraGeometry.model_validate(calibration)
        survey = Survey.model_validate(survey.model_dump() if isinstance(survey, Survey) else survey)
        self.tags = {tag.id: tag for tag in survey.tags}
        self.reprojection_rms_px = getattr(calibration, 'reprojection_rms_px', 0.)
        self.detector = None

    def detect(self, image):
        if self.detector is None:
            from .tag_detector import AprilTagDetector
            self.detector = AprilTagDetector(self.calibration)
        # Shared detector preserves explicit undistorted-pixel provenance for
        # the fixed-map localizer and the independent moving-target tracker.
        return self.detector.detect(image)

    def solve(self, observations):
        import cv2
        observations = [Observation.model_validate(o.model_dump() if isinstance(o, Observation) else o) for o in observations]
        if not observations: raise ValueError('No surveyed tags visible')
        ids = [o.id for o in observations]
        if len(set(ids)) != len(ids) or any(i not in self.tags for i in ids): raise ValueError('Duplicate/unknown tag observation')
        k = np.array(self.calibration.intrinsics)
        d = np.array(self.calibration.distortion)
        # Solve in raw calibrated pixel space. Convert corrected detector corners
        # back once; recorded/synthetic raw corners already include distortion.
        normalized = []
        for o in observations:
            if o.pixel_space == 'undistorted':
                pixels = np.array(o.corners)
                rays = np.column_stack(((pixels[:, 0] - k[0, 2]) / k[0, 0], (pixels[:, 1] - k[1, 2]) / k[1, 1], np.ones(4)))
                pixels = cv2.projectPoints(rays, np.zeros(3), np.zeros(3), k, d)[0].reshape(4, 2)
                o = Observation(id=o.id, corners=pixels.tolist())
            normalized.append(o)
        observations = normalized
        objects, pixels = [], []
        for o in observations:
            points = tag_points(self.tags[o.id].size_m)
            t = np.array(self.tags[o.id].map_from_tag)
            objects.extend(points @ t[:3, :3].T + t[:3, 3])
            pixels.extend(o.corners)
        objects, pixels = np.array(objects), np.array(pixels)
        w, h = self.calibration.image_size
        if np.any(pixels < 0) or np.any(pixels >= [w, h]): raise ValueError('Tag corners outside calibrated image')
        # Solve each tag's two planar branches, then refine each against ALL observations.
        # This retains alternatives even for a coplanar multi-tag survey.
        candidates = []
        first = observations[0]
        tag = self.tags[first.id]
        _, rotations, translations, _ = cv2.solvePnPGeneric(tag_points(tag.size_m), np.array(first.corners), k, d, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        seeds = []
        for rv, tv in zip(rotations, translations):
            camera_from_tag = np.eye(4)
            camera_from_tag[:3, :3] = cv2.Rodrigues(rv)[0]
            camera_from_tag[:3, 3] = tv.ravel()
            seeds.append(camera_from_tag @ invert(tag.map_from_tag))
        # Near a pi rotation, OpenCV IPPE can produce a numerically degenerate
        # Rodrigues branch. Add a global SQPnP solution, retaining IPPE alternatives
        # for ambiguity checks instead of trusting its first returned branch.
        _, global_rotations, global_translations, _ = cv2.solvePnPGeneric(objects, pixels, k, d, flags=cv2.SOLVEPNP_SQPNP)
        for rv, tv in zip(global_rotations, global_translations):
            camera_from_map = np.eye(4)
            camera_from_map[:3, :3] = cv2.Rodrigues(rv)[0]
            camera_from_map[:3, 3] = tv.ravel()
            seeds.append(camera_from_map)
        for camera_from_map in seeds:
            if len(observations) > 1:
                rv, tv = cv2.Rodrigues(camera_from_map[:3, :3])[0], camera_from_map[:3, 3].copy()
                ok, rv, tv = cv2.solvePnP(objects, pixels, k, d, rv, tv, True, flags=cv2.SOLVEPNP_ITERATIVE)
                if not ok: continue
                rv, tv = cv2.solvePnPRefineLM(objects, pixels, k, d, rv, tv,
                    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-10))
                camera_from_map[:3, :3] = cv2.Rodrigues(rv)[0]
                camera_from_map[:3, 3] = tv.ravel()
            depths = (objects @ camera_from_map[:3, :3].T + camera_from_map[:3, 3])[:, 2]
            if np.any(depths <= .01): continue
            rv = cv2.Rodrigues(camera_from_map[:3, :3])[0]
            projected = cv2.projectPoints(objects, rv, camera_from_map[:3, 3], k, d)[0].reshape(-1, 2)
            error = float(np.sqrt(np.mean(np.sum((projected - pixels) ** 2, axis=1))))
            map_from_camera = invert(camera_from_map)
            if np.isfinite(error): candidates.append((error, map_from_camera, float(np.max(depths))))
        if not candidates: raise ValueError('No positive-depth pose solution')
        candidates.sort(key=lambda c: c[0])
        error, transform, depth = candidates[0]
        gap = 1e6
        for other_error, other, _ in candidates[1:]:
            # Numerically identical branches do not constitute a distinct ambiguity.
            if np.linalg.norm(transform - other) > 1e-3: gap = max(0., other_error - error); break
        # Conservative PROVISIONAL image/range bound, not calibrated confidence/covariance.
        # Physical acceptance requires independent ground-truth error characterization.
        uncertainty = .02 + depth * (error + self.reprojection_rms_px + 1) / min(k[0, 0], k[1, 1])
        return CameraEstimate(map_from_camera=transform.tolist(), uncertainty_m=uncertainty,
                              reprojection_px=error, ambiguity_gap_px=gap, tag_ids=ids)


class Localizer(CameraPoseSolver):
    def __init__(self, bundle):
        self.bundle = bundle
        super().__init__(bundle.calibration, bundle.survey)

    def solve(self, observations, timing, sequence, source='vision_estimate'):
        estimate = super().solve(observations)
        transform = np.array(estimate.map_from_camera) @ invert(self.bundle.calibration.aircraft_from_camera)
        m = self.bundle.map
        return Pose(sequence=sequence, bundle_id=self.bundle.bundle_id, map_id=m.map_id, map_version=m.map_version,
                    frame_id=m.frame_id, calibration_id=self.bundle.calibration.calibration_id,
                    source=source, timing=timing, map_from_aircraft=transform.tolist(), uncertainty_m=estimate.uncertainty_m,
                    reprojection_px=estimate.reprojection_px, ambiguity_gap_px=estimate.ambiguity_gap_px, tag_ids=estimate.tag_ids)
