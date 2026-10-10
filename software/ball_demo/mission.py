"""Versioned inspection intentions; no flight commands or implied observations."""
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator

from .arrival import ArrivalPolicy
from .arrival import ArrivalState, ArrivalTracker
from .localization import Pose
from .map_io import Contract, Identifier, Nonnegative, Number, Vector


class InspectionTarget(Contract):
    target_id: Identifier
    name: str = Field(min_length=1, max_length=120)
    tag_id: int | None = Field(default=None, ge=0, lt=587)
    viewing_position_m: Vector
    heading_rad: Annotated[Number, Field(ge=-np.pi, le=np.pi)] | None = None
    arrival: ArrivalPolicy = Field(default_factory=ArrivalPolicy)
    snapshot: Literal['none', 'image'] = 'image'

    @model_validator(mode='after')
    def name_present(self):
        if not self.name.strip(): raise ValueError('Inspection target needs a name')
        return self


class Mission(Contract):
    schema_version: Literal[1]
    mission_id: Identifier
    map_id: Identifier
    map_version: int = Field(ge=1)
    frame_id: Identifier
    survey_id: Identifier
    targets: Annotated[list[InspectionTarget], Field(min_length=1, max_length=100)]
    example: bool
    control_authority: Literal['advisory_only'] = 'advisory_only'
    physical_output: Literal[False] = False

    @model_validator(mode='after')
    def unique_targets(self):
        if len({t.target_id for t in self.targets}) != len(self.targets): raise ValueError('Duplicate inspection target IDs')
        return self

    def validate_bundle(self, bundle):
        from .map_io import Bundle
        from .navigation import Planner, clearance
        from .navigation_visibility import VisibilityPlanner
        bundle = Bundle.model_validate(bundle.model_dump())
        m, s = bundle.map, bundle.survey
        if (self.map_id, self.map_version, self.frame_id, self.survey_id, self.example) != (m.map_id, m.map_version, m.frame_id, s.survey_id, m.example):
            raise ValueError('Mission/bundle registration mismatch')
        ids = {tag.id for tag in s.tags}
        planner = Planner(bundle)
        visibility = VisibilityPlanner(bundle)
        for target in self.targets:
            if target.tag_id is not None and target.tag_id not in ids: raise ValueError('Unknown mission tag')
            margin = clearance(bundle, bundle.policy.max_uncertainty_m)
            if not planner.segment_clear(target.viewing_position_m, target.viewing_position_m, margin):
                raise ValueError('Inspection viewing position lacks cage clearance')
            headings = ([target.heading_rad] if target.heading_rad is not None else
                        [2 * np.pi * i / visibility.heading_bins for i in range(visibility.heading_bins)])
            if not any(visibility.visible_tag_ids(target.viewing_position_m, heading, target.tag_id)
                       for heading in headings):
                raise ValueError('Inspection target has no calibrated, unoccluded AprilTag view')
        return self


class MissionState(Contract):
    schema_version: Literal[1] = 1
    mission_id: Identifier | None
    status: Literal['unloaded', 'ready', 'running', 'waiting_for_localization',
                    'waiting_for_target', 'reacquiring_target', 'snapshot_pending',
                    'target_complete', 'complete', 'aborted', 'fault']
    target_index: int | None = Field(default=None, ge=0, le=99)
    target_id: Identifier | None
    target_name: str | None
    target_count: int = Field(ge=0, le=100)
    arrival: ArrivalState | None
    snapshot_status: Literal['not_requested', 'not_required', 'requested', 'saved', 'failed']
    snapshot_sha256: Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')] | None
    snapshot_source: Literal['camera', 'recording', 'synthetic'] | None
    physical_output: Literal[False] = False
    uncertainty_provisional: Literal[True] = True
    physical_acceptance: Literal[False] = False

    @model_validator(mode='after')
    def consistent(self):
        terminal_without_target = self.status in ('complete', 'aborted', 'unloaded')
        has_target = self.target_index is not None
        if has_target == terminal_without_target:
            raise ValueError('Mission status/target fields are inconsistent')
        if has_target and (self.mission_id is None or self.target_id is None or self.target_name is None or self.arrival is None):
            raise ValueError('Active mission target fields are incomplete')
        if (self.snapshot_sha256 is None) != (self.snapshot_source is None):
            raise ValueError('Mission snapshot digest/source must be paired')
        if self.status == 'snapshot_pending' and self.snapshot_status != 'requested':
            raise ValueError('Pending snapshot status must be requested')
        if self.status == 'target_complete' and self.snapshot_status not in ('saved', 'not_required'):
            raise ValueError('Target completion needs its requested snapshot')
        if self.status == 'complete' and any(x is not None for x in (self.target_id, self.target_name, self.arrival)):
            raise ValueError('Completed mission cannot retain an active target')
        if self.status == 'aborted' and self.snapshot_status != 'not_requested':
            raise ValueError('Aborted mission cannot retain a pending snapshot')
        return self


class MissionRunner:
    """Dry-run mission progress driven only by distinct accepted poses."""
    def __init__(self, mission, bundle):
        self.bundle = bundle
        self.mission = Mission.model_validate(mission.model_dump() if isinstance(mission, Mission) else mission)
        self.mission.validate_bundle(bundle)
        self.index = 0
        self.status = 'ready'
        self.snapshot_status = 'not_requested'
        self.snapshot_sha256 = None
        self.snapshot_source = None
        self.resume_status = None
        self.tracker = ArrivalTracker(self.target.arrival)

    @property
    def target(self):
        return self.mission.targets[self.index]

    @property
    def active(self):
        return self.status in ('running', 'waiting_for_localization', 'waiting_for_target',
                               'reacquiring_target', 'snapshot_pending', 'target_complete')

    def start(self):
        if self.status != 'ready': raise ValueError('Mission must be ready before dry run starts')
        self.status = 'running'
        return self.snapshot()

    def observe(self, pose, now):
        if self.status not in ('running', 'waiting_for_target', 'reacquiring_target'):
            return self.snapshot()
        from .localization import Pose
        pose = Pose.model_validate(pose.model_dump() if isinstance(pose, Pose) else pose)
        if self.target.tag_id is not None and self.target.tag_id not in pose.tag_ids:
            self.tracker.reset()
            self.status = 'waiting_for_target'
            return self.snapshot()
        if self.status == 'waiting_for_target':
            self.tracker.reset()
            self.status = 'reacquiring_target'
            return self.snapshot()
        if self.status == 'reacquiring_target':
            self.tracker.reset()
            self.status = 'running'
        try:
            state = self.tracker.update(pose, self.target.viewing_position_m, now, self.target.heading_rad)
        except ValueError:
            self.status = 'waiting_for_localization'
            raise
        if state['estimated_arrival']:
            if self.target.snapshot == 'image':
                self.snapshot_status = 'requested'
                self.status = 'snapshot_pending'
            else:
                self.snapshot_status = 'not_required'
                self.status = 'target_complete'
        return self.snapshot()

    def localization_lost(self):
        self.tracker.reset()
        if self.status in ('running', 'waiting_for_localization', 'waiting_for_target',
                           'reacquiring_target', 'snapshot_pending', 'target_complete'):
            if self.status == 'waiting_for_localization':
                pass  # Repeated loss reports must retain the state to restore.
            elif self.status == 'snapshot_pending':
                self.snapshot_status, self.snapshot_sha256, self.snapshot_source = 'not_requested', None, None
                self.resume_status = 'running'
            else:
                self.resume_status = self.status
            self.status = 'waiting_for_localization'
        return self.snapshot()

    def localization_restored(self):
        if self.status == 'waiting_for_localization':
            self.tracker.reset()
            self.status = self.resume_status or 'running'
            self.resume_status = None
        return self.snapshot()

    def snapshot_saved(self, digest, source):
        if self.status != 'snapshot_pending' or self.snapshot_status != 'requested':
            raise ValueError('Mission has no pending image snapshot')
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid mission snapshot SHA256')
        if source not in ('camera', 'recording', 'synthetic'):
            raise ValueError('Invalid mission snapshot source')
        if self.mission.example != (source == 'synthetic'):
            raise ValueError('Mission snapshot source/example mismatch')
        self.snapshot_sha256, self.snapshot_source = digest, source
        self.snapshot_status, self.status = 'saved', 'target_complete'
        return self.snapshot()

    def snapshot_failed(self):
        if self.status != 'snapshot_pending': raise ValueError('Mission has no pending image snapshot')
        self.snapshot_status, self.status = 'failed', 'fault'
        return self.snapshot()

    def advance(self):
        if self.status != 'target_complete': raise ValueError('Target cannot advance before arrival and requested snapshot')
        if self.index + 1 == len(self.mission.targets):
            self.status = 'complete'
            return self.snapshot()
        self.index += 1
        self.tracker = ArrivalTracker(self.target.arrival)
        self.snapshot_status, self.snapshot_sha256, self.snapshot_source = 'not_requested', None, None
        self.resume_status = None
        self.status = 'running'
        return self.snapshot()

    def abort(self):
        self.tracker.reset()
        self.status = 'aborted'
        self.resume_status = None
        self.snapshot_status = 'not_requested'
        self.snapshot_sha256 = self.snapshot_source = None
        return self.snapshot()

    def snapshot(self):
        target = self.target if self.status not in ('complete', 'aborted') else None
        return MissionState(mission_id=self.mission.mission_id, status=self.status, target_index=self.index if target else None,
            target_id=target.target_id if target else None, target_name=target.name if target else None,
            target_count=len(self.mission.targets), arrival=self.tracker.snapshot() if target else None,
            snapshot_status=self.snapshot_status, snapshot_sha256=self.snapshot_sha256,
            snapshot_source=self.snapshot_source).model_dump()
