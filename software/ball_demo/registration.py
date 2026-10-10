"""Surveyed-tag registration of a stationary D435 RGB/depth camera pair.

No SLAM or aircraft output. Survey and factory geometry are inputs; stability
and image residuals do not establish independently measured physical accuracy.
"""
import hashlib
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator

from .localization import CameraEstimate, CameraPoseSolver
from .map_io import CameraGeometry, Contract, Identifier, Matrix, Nonnegative, Positive, Survey, rigid

Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]


class RegistrationPolicy(Contract):
    schema_version: Literal[1] = 1
    min_tags: int = Field(default=2, ge=2, le=587)
    stable_frames: int = Field(default=3, ge=2, le=100)
    min_pixel_span: Positive = 30.
    max_reprojection_px: Positive = 3.
    min_ambiguity_gap_px: Nonnegative = .4
    max_translation_m: Positive = .02
    max_rotation_rad: Positive = .05
    max_uncertainty_m: Positive = .15
    survey_uncertainty_m: Nonnegative = .03
    factory_uncertainty_m: Nonnegative = .005
    depth_uncertainty_m: Nonnegative = .02


class RegistrationResult(Contract):
    schema_version: Literal[1] = 1
    survey_id: Identifier
    map_id: Identifier
    map_version: int = Field(ge=1)
    frame_id: Identifier
    camera: CameraGeometry
    map_from_color: Matrix
    color_from_depth: Matrix
    map_from_depth: Matrix
    tag_ids: Annotated[list[int], Field(min_length=2, max_length=587)]
    timestamps_s: Annotated[list[Nonnegative], Field(min_length=2, max_length=1000)]
    image_sha256: Annotated[list[Digest], Field(min_length=2, max_length=1000)]
    image_digest_kind: Literal['decoded_pixels_sha256'] = 'decoded_pixels_sha256'
    reprojection_px: Nonnegative
    ambiguity_gap_px: Nonnegative
    translation_spread_m: Nonnegative
    rotation_spread_rad: Nonnegative
    uncertainty_m: Nonnegative
    camera_uncertainty_m: Nonnegative
    uncertainty_provisional: Literal[True] = True
    source: Literal['synthetic_estimate', 'recorded_estimate', 'vision_estimate']
    example: bool
    physical_acceptance: Literal[False] = False
    policy: RegistrationPolicy

    @model_validator(mode='after')
    def consistency(self):
        color, extr, depth = (rigid(value) for value in (self.map_from_color, self.color_from_depth, self.map_from_depth))
        if not np.allclose(color @ extr, depth, atol=1e-9): raise ValueError('Depth/color registration direction mismatch')
        if self.example != (self.source == 'synthetic_estimate'): raise ValueError('Registration source/example mismatch')
        if any(type(i) is not int or not 0 <= i < 587 for i in self.tag_ids) or len(set(self.tag_ids)) != len(self.tag_ids):
            raise ValueError('Invalid registration tags')
        if len(self.timestamps_s) != len(self.image_sha256) or len(self.timestamps_s) < self.policy.stable_frames:
            raise ValueError('Incomplete stable-frame evidence')
        if any(b <= a for a, b in zip(self.timestamps_s, self.timestamps_s[1:])): raise ValueError('Nonadvancing registration timestamps')
        if len(self.tag_ids) < self.policy.min_tags or self.reprojection_px > self.policy.max_reprojection_px or self.ambiguity_gap_px < self.policy.min_ambiguity_gap_px:
            raise ValueError('Registration image quality failed')
        if self.translation_spread_m > self.policy.max_translation_m or self.rotation_spread_rad > self.policy.max_rotation_rad:
            raise ValueError('Scanner moved during registration')
        if self.uncertainty_m > self.policy.max_uncertainty_m: raise ValueError('Excessive registration uncertainty')
        minimum = self.camera_uncertainty_m + self.policy.survey_uncertainty_m + self.policy.factory_uncertainty_m + self.translation_spread_m
        if self.uncertainty_m + 1e-12 < minimum: raise ValueError('Registration uncertainty omits declared input bounds')
        return self


class StationRegistrar:
    """Acquire a fixed pose; every supplied frame must satisfy the quality gates.

    An error clears acquisition and is raised to the capture caller. It must not
    swallow a movement/loss error and certify an incomplete capture as successful.
    """
    def __init__(self, camera, survey, color_from_depth, policy=None, source='synthetic_estimate'):
        if isinstance(camera, CameraGeometry):
            camera = camera.model_dump(include=set(CameraGeometry.model_fields))
        self.camera = CameraGeometry.model_validate(camera)
        self.survey = Survey.model_validate(survey.model_dump() if isinstance(survey, Survey) else survey)
        self.extr = rigid(color_from_depth)
        self.policy = RegistrationPolicy.model_validate(policy.model_dump() if isinstance(policy, RegistrationPolicy) else policy or {})
        if source not in ('synthetic_estimate', 'recorded_estimate', 'vision_estimate') or self.survey.example != (source == 'synthetic_estimate'):
            raise ValueError('Registration source/example mismatch')
        self.source = source
        self.solver = CameraPoseSolver(self.camera, self.survey)
        self.last_time = None
        self.reset()

    def reset(self):
        self.anchor = None
        self.samples = []
        self.translation_spread = self.rotation_spread = 0.
        self.issue = 'acquiring station'

    def observe(self, image, timestamp_s):
        try:
            if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim not in (2, 3):
                raise ValueError('Expected uint8 scanner RGB image')
            observations = self.solver.detect(image)
            estimate = self.solver.solve(observations)
            corners = np.array([p for o in observations for p in o.corners])
            span = float(np.linalg.norm(np.ptp(corners, axis=0)))
            digest = hashlib.sha256(image.tobytes()).hexdigest()
            return self.observe_estimate(estimate, timestamp_s, digest, span)
        except Exception as error:
            self.reset()
            self.issue = str(error)
            raise

    def observe_estimate(self, estimate, timestamp_s, image_sha256, pixel_span):
        """Accept independently supplied estimates; image path calls this as well."""
        try:
            if type(timestamp_s) not in (int, float) or not np.isfinite(timestamp_s) or timestamp_s < 0:
                raise ValueError('Invalid registration timestamp')
            if self.last_time is not None and timestamp_s <= self.last_time: raise ValueError('Nonadvancing registration timestamp')
            self.last_time = timestamp_s
            estimate = CameraEstimate.model_validate(estimate.model_dump() if isinstance(estimate, CameraEstimate) else estimate)
            if not isinstance(image_sha256, str) or len(image_sha256) != 64 or any(c not in '0123456789abcdef' for c in image_sha256):
                raise ValueError('Invalid image digest')
            if type(pixel_span) not in (int, float) or not np.isfinite(pixel_span) or pixel_span < self.policy.min_pixel_span:
                raise ValueError('Insufficient tag image spread')
            p = self.policy
            if len(estimate.tag_ids) < p.min_tags or any(i not in self.solver.tags for i in estimate.tag_ids):
                raise ValueError('Insufficient surveyed registration tags')
            if estimate.reprojection_px > p.max_reprojection_px or estimate.ambiguity_gap_px < p.min_ambiguity_gap_px:
                raise ValueError('Registration image quality failed')
            current = np.array(estimate.map_from_camera)
            if self.anchor is None: self.anchor = current.copy()
            anchored_depth, current_depth = self.anchor @ self.extr, current @ self.extr
            displacement = float(np.linalg.norm(anchored_depth[:3, 3] - current_depth[:3, 3]))
            delta = anchored_depth[:3, :3].T @ current_depth[:3, :3]
            angle = float(np.arccos(np.clip((np.trace(delta) - 1) / 2, -1., 1.)))
            if displacement > p.max_translation_m or angle > p.max_rotation_rad: raise ValueError('Scanner moved during registration/capture')
            uncertainty = estimate.uncertainty_m + p.survey_uncertainty_m + p.factory_uncertainty_m + displacement
            if uncertainty > p.max_uncertainty_m: raise ValueError('Excessive registration uncertainty')
            if len(self.samples) >= 1000: raise ValueError('Registration frame budget exceeded')
            self.samples.append((estimate, timestamp_s, image_sha256, uncertainty))
            self.translation_spread = max(self.translation_spread, displacement)
            self.rotation_spread = max(self.rotation_spread, angle)
            self.issue = 'station registered' if len(self.samples) >= p.stable_frames else 'acquiring station'
            return self.result()
        except Exception as error:
            self.reset()
            self.issue = str(error)
            raise

    def result(self):
        if len(self.samples) < self.policy.stable_frames: return None
        return RegistrationResult(survey_id=self.survey.survey_id, map_id=self.survey.map_id,
            map_version=self.survey.map_version, frame_id=self.survey.frame_id, camera=self.camera,
            map_from_color=self.anchor.tolist(), color_from_depth=self.extr.tolist(), map_from_depth=(self.anchor @ self.extr).tolist(),
            tag_ids=sorted({i for sample in self.samples for i in sample[0].tag_ids}),
            timestamps_s=[sample[1] for sample in self.samples], image_sha256=[sample[2] for sample in self.samples],
            reprojection_px=max(s[0].reprojection_px for s in self.samples), ambiguity_gap_px=min(s[0].ambiguity_gap_px for s in self.samples),
            translation_spread_m=self.translation_spread, rotation_spread_rad=self.rotation_spread,
            uncertainty_m=max(s[0].uncertainty_m for s in self.samples) + self.policy.survey_uncertainty_m + self.policy.factory_uncertainty_m + self.translation_spread,
            camera_uncertainty_m=max(s[0].uncertainty_m for s in self.samples), source=self.source, example=self.survey.example, policy=self.policy)

    def station(self, template):
        from .mapping import Station
        template = Station.model_validate(template.model_dump() if isinstance(template, Station) else template)
        result = self.result()
        if result is None: raise ValueError('Acquire a stable registered station first')
        if (template.map_id, template.map_version, template.frame_id, template.example) != (result.map_id, result.map_version, result.frame_id, result.example):
            raise ValueError('Station/survey registration mismatch')
        data = template.model_dump()
        if template.uncertainty_m < result.uncertainty_m + self.policy.depth_uncertainty_m:
            raise ValueError('Station map uncertainty must cover registration and depth bounds')
        digest = hashlib.sha256(result.model_dump_json().encode()).hexdigest()
        data.update(map_from_depth=result.map_from_depth,
            registration_evidence=f'{result.source}; surveyed tags {result.tag_ids}; registration SHA256 {digest}; uncertainty provisional; physical acceptance unverified')
        return Station.model_validate(data)


def register_images(camera, survey, color_from_depth, images, timestamps_s, policy=None, source='synthetic_estimate'):
    registrar = StationRegistrar(camera, survey, color_from_depth, policy, source)
    if not images or len(images) != len(timestamps_s) or len(images) > 1000: raise ValueError('Supply 1–1000 timestamped registration images')
    for image, timestamp in zip(images, timestamps_s): registrar.observe(image, timestamp)
    if registrar.result() is None: raise ValueError('Not enough stable registration frames')
    return registrar


def rgb_geometry(intrinsics):
    """Explicit SDK model support; inverse/modified Brown cannot be guessed."""
    model = str(intrinsics.model)
    if model not in ('none', 'distortion.none', 'brown_conrady', 'distortion.brown_conrady'):
        raise ValueError('Unsupported scanner RGB distortion model')
    coefficients = list(intrinsics.coeffs)
    if model in ('none', 'distortion.none') and any(coefficients): raise ValueError('Nonzero distortion in pinhole RGB profile')
    return CameraGeometry(image_size=[intrinsics.width, intrinsics.height],
        intrinsics=[[float(intrinsics.fx), 0., float(intrinsics.ppx)], [0., float(intrinsics.fy), float(intrinsics.ppy)], [0., 0., 1.]],
        distortion_model='opencv_brown', distortion=[float(c) for c in coefficients])


from .mapping import Station


class RegistrationImage(Contract):
    file: str = Field(pattern=r'^[A-Za-z0-9_.-]+\.png$')
    sha256: Digest
    timestamp_s: Nonnegative


class RegistrationInput(Contract):
    schema_version: Literal[1]
    camera: CameraGeometry
    survey: Survey
    color_from_depth: Matrix
    policy: RegistrationPolicy = Field(default_factory=RegistrationPolicy)
    source: Literal['synthetic_estimate', 'recorded_estimate']
    station_template: Station
    images: Annotated[list[RegistrationImage], Field(min_length=2, max_length=1000)]

    @model_validator(mode='after')
    def consistency(self):
        rigid(self.color_from_depth)
        t, s = self.station_template, self.survey
        if (t.map_id, t.map_version, t.frame_id, t.example) != (s.map_id, s.map_version, s.frame_id, s.example):
            raise ValueError('Station/survey registration mismatch')
        if s.example != (self.source == 'synthetic_estimate'): raise ValueError('Registration source/example mismatch')
        if len(self.images) < self.policy.stable_frames: raise ValueError('Not enough registration images')
        if len({f.file for f in self.images}) != len(self.images): raise ValueError('Duplicate registration image files')
        if any(b.timestamp_s <= a.timestamp_s for a, b in zip(self.images, self.images[1:])):
            raise ValueError('Nonadvancing registration timestamps')
        return self


def register_directory(manifest, output):
    """Offline PNG registration; no SDK/device import and no source relabelling."""
    import cv2
    import json
    from pathlib import Path
    manifest, output = Path(manifest).resolve(), Path(output)
    if manifest.stat().st_size > 10_000_000: raise ValueError('Registration manifest too large')
    raw = manifest.read_bytes()
    inputs = RegistrationInput.model_validate_json(raw)
    registrar = StationRegistrar(inputs.camera, inputs.survey, inputs.color_from_depth, inputs.policy, inputs.source)
    for frame in inputs.images:
        path = (manifest.parent / frame.file).resolve()
        if path.parent != manifest.parent: raise ValueError('Registration image path escapes input directory')
        if path.stat().st_size > 30_000_000: raise ValueError('Registration image too large')
        encoded = path.read_bytes()
        if hashlib.sha256(encoded).hexdigest() != frame.sha256: raise ValueError('Registration image hash mismatch')
        image = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
        if image is None: raise ValueError('Unreadable registration image')
        registrar.observe(image, frame.timestamp_s)
    result, station = registrar.result(), registrar.station(inputs.station_template)
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / 'registration.json').write_text(result.model_dump_json(indent=2) + '\n')
        (output / 'station.json').write_text(station.model_dump_json(indent=2) + '\n')
        completion = {'schema_version': 1, 'source_manifest_sha256': hashlib.sha256(raw).hexdigest(),
            'files': {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in ('registration.json', 'station.json')},
            'source': inputs.source, 'example': inputs.survey.example, 'physical_acceptance': False}
        (output / 'complete.json').write_text(json.dumps(completion, indent=2) + '\n')
    except Exception as error:
        try: (output / 'INCOMPLETE.json').write_text(json.dumps({'error': str(error), 'physical_acceptance': False}) + '\n')
        except OSError: pass
        raise
    return result, station
