"""Versioned, strict metric navigation contracts. No scan holes become free space."""
import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

Number = Annotated[float, Field(allow_inf_nan=False)]
Positive = Annotated[Number, Field(gt=0)]
Nonnegative = Annotated[Number, Field(ge=0)]
Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_.-]+$')]
Vector = Annotated[list[Number], Field(min_length=3, max_length=3)]
Matrix = Annotated[list[Annotated[list[Number], Field(min_length=4, max_length=4)]], Field(min_length=4, max_length=4)]


class Contract(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', validate_assignment=True)

    @model_validator(mode='before')
    @classmethod
    def strict_literals(cls, value):
        if isinstance(value, dict):
            if 'schema_version' in value and type(value['schema_version']) is not int: raise ValueError('Schema version must be an integer')
            for field in ('physical_output', 'physical_acceptance', 'uncertainty_provisional'):
                if field in value and type(value[field]) is not bool: raise ValueError(f'{field} must be a boolean')
        return value


def rigid(value):
    t = np.asarray(value, dtype=float)
    if t.shape != (4, 4) or not np.isfinite(t).all(): raise ValueError('Expected finite 4x4 transform')
    r = t[:3, :3]
    if not np.allclose(t[3], [0, 0, 0, 1], atol=1e-8) or not np.allclose(r.T @ r, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(r), 1, atol=1e-6):
        raise ValueError('Transform must be right-handed rigid SE(3), without scaling')
    return t


class Box(Contract):
    minimum: Vector
    maximum: Vector

    @model_validator(mode='after')
    def ordered(self):
        if any(a >= b for a, b in zip(self.minimum, self.maximum)): raise ValueError('Empty/inverted box')
        return self


class CameraGeometry(Contract):
    """Optical geometry shared by the FPV camera and stationary scanner RGB."""
    image_size: Annotated[list[Annotated[int, Field(ge=16, le=4096)]], Field(min_length=2, max_length=2)]
    intrinsics: Annotated[list[Annotated[list[Number], Field(min_length=3, max_length=3)]], Field(min_length=3, max_length=3)]
    distortion_model: Literal['opencv_brown']
    distortion: list[Number]

    @model_validator(mode='after')
    def geometry(self):
        k = np.array(self.intrinsics)
        w, h = self.image_size
        if k[0, 0] <= 0 or k[1, 1] <= 0 or not 0 <= k[0, 2] < w or not 0 <= k[1, 2] < h or not np.allclose(k[2], [0, 0, 1]) or k[0, 1] != 0 or k[1, 0] != 0:
            raise ValueError('Invalid camera intrinsics')
        if len(self.distortion) not in (4, 5, 8, 12, 14): raise ValueError('Unsupported Brown coefficient count')
        return self


class Calibration(CameraGeometry):
    schema_version: Literal[1]
    calibration_id: Identifier
    camera_frame: Literal['camera_optical']
    aircraft_frame: Literal['aircraft_flu']
    aircraft_from_camera: Matrix
    reprojection_rms_px: Nonnegative
    evidence: str = Field(min_length=1)
    example: bool

    @model_validator(mode='after')
    def mount(self):
        rigid(self.aircraft_from_camera)
        return self


class Tag(Contract):
    id: int = Field(ge=0, lt=587)
    size_m: Positive
    map_from_tag: Matrix

    @model_validator(mode='after')
    def transform(self):
        rigid(self.map_from_tag)
        return self


class Survey(Contract):
    schema_version: Literal[1]
    survey_id: Identifier
    map_id: Identifier
    map_version: int = Field(ge=1)
    frame_id: Identifier
    units: Literal['m']
    family: Literal['tag36h11']
    tags: Annotated[list[Tag], Field(min_length=1, max_length=587)]
    evidence: str = Field(min_length=1)
    example: bool

    @model_validator(mode='after')
    def unique(self):
        if len({t.id for t in self.tags}) != len(self.tags): raise ValueError('Duplicate tag IDs')
        return self


class Map(Contract):
    schema_version: Literal[1]
    map_id: Identifier
    map_version: int = Field(ge=1)
    frame_id: Identifier
    axes: Literal['right_handed_z_up']
    units: Literal['m']
    permitted: Box
    observed_free: Annotated[list[Box], Field(min_length=1, max_length=1000)]
    occupied: Annotated[list[Box], Field(max_length=1000)]
    uncertainty_m: Nonnegative
    acquired_utc: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    example: bool

    @model_validator(mode='after')
    def extent(self):
        for box in self.observed_free + self.occupied:
            if any(a < b for a, b in zip(box.minimum, self.permitted.minimum)) or any(a > b for a, b in zip(box.maximum, self.permitted.maximum)):
                raise ValueError('Geometry outside permitted volume')
        return self


class Policy(Contract):
    # Provisional bounds; physical adequacy needs real measurements.
    cage_radius_m: Positive = .125
    flex_margin_m: Nonnegative = .02
    speed_m_s: Positive = .2
    delay_bound_s: Nonnegative = .25
    deceleration_m_s2: Positive = .5
    grid_m: Positive = .2
    max_nodes: int = Field(default=20000, ge=1, le=200000)
    planner_timeout_s: Positive = .5
    route_ttl_s: Positive = 1.
    pose_max_age_s: Positive = .25
    max_uncertainty_m: Positive = .15
    max_reprojection_px: Positive = 3.
    ambiguity_gap_px: Nonnegative = .4
    max_speed_m_s: Positive = 2.
    max_angular_speed_rad_s: Positive = 4.
    reacquire_frames: int = Field(default=3, ge=1, le=30)
    host_delay_bound_s: Nonnegative | None = None

    @model_validator(mode='after')
    def timing(self):
        if self.delay_bound_s < self.pose_max_age_s: raise ValueError('Stopping delay must cover allowed pose age')
        return self


class Bundle(Contract):
    schema_version: Literal[1]
    bundle_id: Identifier
    calibration: Calibration
    survey: Survey
    map: Map
    policy: Policy

    @model_validator(mode='after')
    def registration(self):
        s, m = self.survey, self.map
        if (s.map_id, s.map_version, s.frame_id) != (m.map_id, m.map_version, m.frame_id): raise ValueError('Survey/map registration mismatch')
        if len({self.calibration.example, s.example, m.example}) != 1: raise ValueError('Mixed example and measured artifacts')
        for tag in s.tags:
            p = np.array(tag.map_from_tag)[:3, 3]
            if np.any(p < m.permitted.minimum) or np.any(p > m.permitted.maximum): raise ValueError('Tag outside map extent')
        return self

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True, allow_nan=False).encode()).hexdigest()


def load_bundle(path):
    path = Path(path)
    if path.stat().st_size > 10_000_000: raise ValueError('Bundle exceeds size limit')
    return Bundle.model_validate_json(path.read_text())
