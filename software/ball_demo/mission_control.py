"""Authenticated mission ledger and simulation-only lifecycle; never actuates."""
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import json
import threading
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MissionCommandRequest(BaseModel):
    """Typed operator intent. Unknown fields and coercible values are rejected."""

    model_config = ConfigDict(strict=True, extra='forbid')

    request_id: str = Field(min_length=1, max_length=100,
                            pattern=r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$')
    kind: Literal['follow', 'land_current', 'land_site', 'land_point', 'stop', 'abort', 'audio_unavailable']
    person_id: str | None = Field(default=None, min_length=1, max_length=80)
    tag_id: int | None = Field(default=None, ge=0, lt=587)
    tag_family: Literal['tag36h11'] | None = None
    site_id: str | None = Field(default=None, min_length=1, max_length=80)
    mission_id: str | None = Field(default=None, min_length=1, max_length=100)
    pending_request_id: str | None = Field(default=None, min_length=1, max_length=100)
    frame_id: str | None = Field(default=None, min_length=1, max_length=100)
    x: float | None = Field(default=None, ge=0, le=1)
    y: float | None = Field(default=None, ge=0, le=1)
    client_payload_sha256: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')

    @field_validator('person_id', 'site_id', 'mission_id', 'pending_request_id', 'frame_id')
    @classmethod
    def nonblank_identifier(cls, value):
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError('Identifiers must be nonblank and trimmed')
        return value

    @model_validator(mode='after')
    def command_fields(self):
        allowed = {
            'follow': {'person_id', 'tag_id', 'tag_family'},
            'land_current': set(),
            'land_site': {'site_id'},
            'land_point': {'frame_id', 'x', 'y', 'tag_id', 'tag_family'},
            'stop': {'mission_id', 'pending_request_id'},
            'abort': {'mission_id'},
            'audio_unavailable': set(),
        }[self.kind]
        supplied = self.model_fields_set - {'request_id', 'kind', 'client_payload_sha256'}
        if not supplied <= allowed:
            raise ValueError(f'{self.kind} does not accept {sorted(supplied - allowed)}')
        required = {
            'follow': {'person_id'},
            'land_current': set(),
            'land_site': {'site_id'},
            'land_point': {'frame_id', 'x', 'y'},
            'stop': set(),
            'abort': {'mission_id'},
            'audio_unavailable': set(),
        }[self.kind]
        if not required <= supplied:
            raise ValueError(f'{self.kind} requires {sorted(required - supplied)}')
        if any(getattr(self, name) is None for name in required):
            raise ValueError(f'{self.kind} required fields cannot be null')
        if self.kind == 'stop' and self.mission_id is None and self.pending_request_id is None:
            raise ValueError('stop requires a mission_id or pending_request_id')
        if self.kind == 'land_point' and (self.tag_id is None) != (self.tag_family is None):
            raise ValueError('A tag landing point requires both tag_id and tag_family')
        return self


class MissionCommandResult(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    request_id: str
    kind: Literal['follow', 'land_current', 'land_site', 'land_point', 'stop', 'abort', 'audio_unavailable']
    state: Literal['accepted', 'rejected']
    reason: str = Field(min_length=1, max_length=400)
    observed_at: str
    mission_id: str | None = None
    simulated: bool = False
    control_authority: Literal['advisory_only'] = 'advisory_only'
    physical_output: Literal[False] = False


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def capability(supported, ready, reason=None):
    """Produce an explicit readiness record; unavailable is never implied healthy."""
    return {
        'supported': bool(supported),
        'ready': bool(ready),
        'reason': reason if reason is not None else (None if supported and ready else 'Unavailable'),
    }


class MissionController:
    """Single bounded command ledger shared by legacy and portable API routes.

    The legacy command surface always refuses physical follow/landing. The
    portable client may run the same lifecycle in a visibly mocked source;
    mock results are marked simulated and can never reach the aircraft bridge.
    """

    TERMINAL = {'stopped', 'aborted', 'completed', 'landed', 'failed'}

    def __init__(self, history_limit=128):
        if type(history_limit) is not int or history_limit < 1:
            raise ValueError('history_limit must be a positive integer')
        self._lock = threading.RLock()
        self._history_limit = history_limit
        self._records = OrderedDict()
        self._cancelled_pending = OrderedDict()
        self._mission = None
        self._mock_ticks = 0

    @staticmethod
    def _fingerprint(request):
        body = json.dumps(request.model_dump(mode='json'), sort_keys=True,
                          separators=(',', ':'), allow_nan=False)
        return hashlib.sha256(body.encode('utf-8')).hexdigest()

    def _remember(self, request, result):
        self._records[request.request_id] = (self._fingerprint(request), result)
        while len(self._records) > self._history_limit:
            self._records.popitem(last=False)

    def _result(self, request, state, reason, mission_id=None, simulated=False):
        return MissionCommandResult(request_id=request.request_id, kind=request.kind,
            state=state, reason=reason, observed_at=utc_now(), mission_id=mission_id,
            simulated=simulated)

    def submit(self, request, capabilities, active_mission=None):
        """Handle old mission API requests: they can never actuate or simulate."""
        request = request if isinstance(request, MissionCommandRequest) else MissionCommandRequest.model_validate(request)
        return self._submit(request, capabilities, simulation=False, roster=None,
                            active_mission=active_mission)[0:2]

    def submit_mock(self, request, capabilities, roster):
        """Start or reconcile a software-only mission from a mock video source."""
        request = request if isinstance(request, MissionCommandRequest) else MissionCommandRequest.model_validate(request)
        return self._submit(request, capabilities, simulation=True, roster=roster,
                            active_mission=None)[0:2]

    def _submit(self, request, capabilities, *, simulation, roster, active_mission):
        with self._lock:
            fingerprint = self._fingerprint(request)
            previous = self._records.get(request.request_id)
            if previous is not None:
                if previous[0] != fingerprint:
                    raise ValueError('Request ID is already bound to a different mission command')
                self._records.move_to_end(request.request_id)
                return previous[1].model_dump(), True

            result = self._execute(request, capabilities, simulation, roster, active_mission)
            self._remember(request, MissionCommandResult.model_validate(result))
            return result, False

    def _execute(self, request, capabilities, simulation, roster, active_mission):
        if request.kind == 'audio_unavailable':
            return self._result(request, 'rejected',
                'Audio is outside the portable missions scope and is unavailable.').model_dump()
        if request.kind in ('follow', 'land_current', 'land_site', 'land_point'):
            return self._start(request, capabilities, simulation, roster)
        if request.kind == 'stop':
            return self._stop(request, simulation, active_mission)
        return self._abort(request, simulation, active_mission)

    def _start(self, request, capabilities, simulation, roster):
        if request.request_id in self._cancelled_pending:
            return self._result(request, 'rejected', 'This pending request was cancelled before it could start.').model_dump()
        if not simulation:
            key = {'follow': 'person_follow', 'land_current': 'landing_current',
                   'land_site': 'landing_site', 'land_point': 'landing_point'}[request.kind]
            gate = capabilities.get(key, {})
            reason = gate.get('reason') or 'Mission capability is unavailable'
            if gate.get('supported') and gate.get('ready'):
                reason = 'Physical mission execution is not connected to a verified flight-control path'
            return self._result(request, 'rejected', reason).model_dump()

        if self._mission and self._mission['phase'] not in self.TERMINAL:
            return self._result(request, 'rejected', 'Another high-level mission is already active.',
                                self._mission['mission_id'], True).model_dump()
        key = {'follow': 'person_follow', 'land_current': 'landing_current',
               'land_site': 'landing_site', 'land_point': 'landing_point'}[request.kind]
        gate = capabilities.get(key, {})
        if not (gate.get('supported') and gate.get('ready')):
            return self._result(request, 'rejected', gate.get('reason') or 'Mock capability is unavailable.',
                                simulated=True).model_dump()

        person = None
        site = None
        if request.kind == 'follow':
            person = roster.by_person_id(request.person_id) if roster else None
            if person is None or not person.enabled:
                return self._result(request, 'rejected', 'Person is not present and enabled in the prepared server roster.', simulated=True).model_dump()
            if request.tag_id is not None and request.tag_id != person.tag_id:
                return self._result(request, 'rejected', 'Command tag ID does not match the server-owned roster.', simulated=True).model_dump()
        elif request.kind == 'land_site':
            site = roster.site_by_id(request.site_id) if roster else None
            if site is None:
                return self._result(request, 'rejected', 'Landing site is not present and enabled in the prepared server configuration.', simulated=True).model_dump()
        elif request.kind == 'land_point':
            return self._result(request, 'rejected',
                'Image points cannot be converted to a safe landing location without validated ground geometry and aircraft state.', simulated=True).model_dump()

        mission_id = 'mock-' + uuid.uuid4().hex
        is_follow = request.kind == 'follow'
        is_tag_landing = request.kind == 'land_site'
        self._mission = {
            'type': 'follow' if is_follow else 'landing',
            'phase': 'accepted' if is_follow or is_tag_landing else 'landing',
            'mission_id': mission_id,
            'person_id': person.person_id if person else None,
            'site_id': site.site_id if site else None,
            'request_id': request.request_id,
            'reason': ('Mock simulation only; no aircraft command was sent.' if not is_tag_landing else
                       'Synthetic pad-tag approach is awaiting three fresh, stable observations.'),
            'abort_summary': 'Ends the simulated mission only; it is not a motor stop or disarm.',
            'simulated': True,
            'mock_fresh_frames': 0,
            'landing_altitude_m': .8 if not is_follow else None,
            'landing_descent_rate_m_s': .12 if not is_follow else None,
        }
        self._mock_ticks = 0
        return self._result(request, 'accepted',
            'Accepted in the labeled mock simulator; no aircraft command was sent.', mission_id, True).model_dump()

    def _cancel_pending(self, request_id):
        self._cancelled_pending[request_id] = True
        self._cancelled_pending.move_to_end(request_id)
        while len(self._cancelled_pending) > self._history_limit:
            self._cancelled_pending.popitem(last=False)

    def _stop(self, request, simulation, active_mission=None):
        if not simulation:
            active_id = active_mission.get('mission_id') if isinstance(active_mission, dict) else None
            if active_id is None:
                reason = 'There is no accepted physical mission to stop or abort'
            elif active_id != request.mission_id:
                reason = 'Mission ID does not match the active physical mission'
            else:
                reason = 'Physical stop behavior is not implemented; no command was sent'
            return self._result(request, 'rejected', reason).model_dump()
        if request.pending_request_id is not None:
            self._cancel_pending(request.pending_request_id)
        mission = self._mission
        matches = bool(mission and mission['phase'] not in self.TERMINAL and
            ((request.mission_id is not None and mission['mission_id'] == request.mission_id) or
             (request.pending_request_id is not None and mission['request_id'] == request.pending_request_id)))
        if matches:
            mission['phase'] = 'stopped'
            mission['request_id'] = request.request_id
            mission['reason'] = 'Simulated mission stopped by operator.'
            return self._result(request, 'accepted', 'Mock mission stopped; no aircraft command was sent.',
                                mission['mission_id'], True).model_dump()
        if request.pending_request_id is not None:
            return self._result(request, 'accepted', 'Pending start cancelled; no physical mission existed.', simulated=True).model_dump()
        return self._result(request, 'rejected', 'Mission ID does not match an active mock mission.', simulated=True).model_dump()

    def _abort(self, request, simulation, active_mission=None):
        if not simulation:
            active_id = active_mission.get('mission_id') if isinstance(active_mission, dict) else None
            if active_id is None:
                reason = 'There is no accepted physical mission to stop or abort'
            elif active_id != request.mission_id:
                reason = 'Mission ID does not match the active physical mission'
            else:
                reason = 'Physical abort behavior is not implemented; it is not a motor stop or disarm.'
            return self._result(request, 'rejected', reason, request.mission_id).model_dump()
        mission = self._mission
        if not mission or mission['phase'] in self.TERMINAL or mission['mission_id'] != request.mission_id:
            return self._result(request, 'rejected', 'Mission ID does not match an active mock mission.', request.mission_id, True).model_dump()
        mission['phase'] = 'aborted'
        mission['request_id'] = request.request_id
        mission['reason'] = 'Simulated mission aborted by operator.'
        return self._result(request, 'accepted', 'Mock mission aborted; no aircraft command was sent.',
                            mission['mission_id'], True).model_dump()

    def tick_mock(self, enabled, *, target_visible=True, site_visible=True, dt_s=.01, vision_driven=False):
        """Advance only a labeled synthetic scene; no physical state/output is read."""
        if type(enabled) is not bool or type(target_visible) is not bool or type(site_visible) is not bool:
            raise ValueError('Mock lifecycle gates must be explicit booleans')
        if type(dt_s) not in (int, float) or not 0 < dt_s <= .25:
            raise ValueError('Mock lifecycle step must be in (0, 0.25] seconds')
        if not enabled:
            with self._lock:
                mission = self._mission
                if mission and mission['phase'] not in self.TERMINAL:
                    mission['phase'] = 'lost'
                    mission['mock_fresh_frames'] = 0
                    mission['reason'] = 'Mock source or healthy video became unavailable; simulated mission is stopped.'
                return self.ui_mission()
        with self._lock:
            mission = self._mission
            if not mission or mission['phase'] in self.TERMINAL:
                return self.ui_mission()
            self._mock_ticks += 1
            if mission['type'] == 'follow':
                if vision_driven:
                    return self.ui_mission()
                if not target_visible:
                    if mission['phase'] in ('active', 'reacquiring'):
                        mission['phase'] = 'lost'
                    mission['mock_fresh_frames'] = 0
                    mission['reason'] = 'Synthetic target observation lost; simulated motion is stopped.'
                else:
                    mission['mock_fresh_frames'] += 1
                    if mission['mock_fresh_frames'] < 3:
                        mission['phase'] = 'reacquiring' if self._mock_ticks > 1 else 'accepted'
                        mission['reason'] = f'Awaiting fresh synthetic target observations ({mission["mock_fresh_frames"]}/3).'
                    else:
                        mission['phase'] = 'active'
                        mission['reason'] = 'Synthetic target observations are fresh; simulated follow only.'
            elif mission['type'] == 'landing':
                if mission['site_id'] is not None and mission['phase'] not in ('landed', 'failed', 'stopped', 'aborted'):
                    if not site_visible:
                        mission['phase'] = 'lost'
                        mission['mock_fresh_frames'] = 0
                        mission['reason'] = 'Synthetic landing-tag visibility lost; approach/descent is stopped.'
                        return self.ui_mission()
                    if mission['phase'] in ('accepted', 'lost', 'reacquiring'):
                        if vision_driven:
                            return self.ui_mission()
                        mission['mock_fresh_frames'] += 1
                        if mission['mock_fresh_frames'] < 3:
                            mission['phase'] = 'reacquiring' if self._mock_ticks > 1 else 'accepted'
                            mission['reason'] = f'Awaiting stable synthetic landing-tag observations ({mission["mock_fresh_frames"]}/3).'
                            return self.ui_mission()
                        mission['phase'] = 'landing'
                        mission['reason'] = 'Synthetic pad identity, pose and approach geometry are stable; mock descent started.'
                        return self.ui_mission()
                if mission['phase'] != 'landing':
                    return self.ui_mission()
                from .landing_simulation import step_landing
                sample = step_landing(mission['landing_altitude_m'], mission['landing_descent_rate_m_s'], dt_s=dt_s)
                mission['landing_altitude_m'] = sample['altitude_m']
                mission['reason'] = f'Synthetic descent at {sample["altitude_m"]:.2f} m; no aircraft command was sent.'
                if sample['event'] == 'synthetic_touchdown':
                    self.confirm_mock_touchdown(mission['mission_id'], evidence=sample['event'])
                elif sample['event'] == 'synthetic_impact':
                    mission['phase'] = 'failed'
                    mission['reason'] = 'Synthetic touchdown speed exceeded the mock landing limit.'
            return self.ui_mission()

    def simulation_mission(self):
        """Worker view including the server-owned pad identity, never an actuator handle."""
        with self._lock:
            return None if self._mission is None else dict(self._mission)

    def invalidate_mock(self, reason, *, terminal=False):
        with self._lock:
            if self._mission and self._mission['phase'] not in self.TERMINAL:
                self._mission.update(phase='failed' if terminal else 'lost', reason=reason,
                                     mock_fresh_frames=0)

    def update_mock_landing(self, site_id, state, reason=None):
        if state not in {'acquiring', 'approaching', 'lost', 'reacquiring', 'unavailable'}:
            raise ValueError('Unknown landing tracking state')
        with self._lock:
            mission = self._mission
            if not mission or mission['type'] != 'landing' or mission['phase'] in self.TERMINAL:
                return
            if mission['site_id'] != site_id:
                mission.update(phase='failed', reason='Landing-pad identity changed during the mock mission.')
                return
            mission.update(phase={'acquiring': 'accepted', 'approaching': 'landing',
                'lost': 'lost', 'reacquiring': 'reacquiring', 'unavailable': 'failed'}[state],
                reason=reason or 'Synthetic landing-pad observation')

    def update_mock_target(self, person_id, state, reason=None):
        """Apply a validated simulated target state to the active mock follow."""
        allowed = {'acquiring', 'tracking', 'lost', 'reacquiring', 'unavailable'}
        if state not in allowed:
            raise ValueError('Unknown target tracking state')
        if not isinstance(person_id, str) or not person_id.strip() or person_id != person_id.strip():
            raise ValueError('person_id must be nonblank trimmed text')
        if reason is not None and (not isinstance(reason, str) or len(reason) > 240):
            raise ValueError('Mock target reason must be text up to 240 characters')
        with self._lock:
            mission = self._mission
            if not mission or mission['type'] != 'follow' or mission['phase'] in self.TERMINAL:
                return self.ui_mission()
            if mission['person_id'] != person_id:
                mission['phase'] = 'failed'
                mission['reason'] = 'Target identity changed during the mock mission.'
            else:
                mission['phase'] = {'acquiring': 'accepted', 'tracking': 'active', 'lost': 'lost',
                                    'reacquiring': 'reacquiring', 'unavailable': 'failed'}[state]
                mission['reason'] = (reason or 'Mock target state.' if state != 'tracking' else
                                     'Mock simulation only; no aircraft command was sent.')
            return self.ui_mission()

    def confirm_mock_touchdown(self, mission_id, evidence):
        """Finish a mock landing only after explicit simulator touchdown evidence."""
        if evidence != 'synthetic_touchdown':
            raise ValueError('Mock touchdown must carry explicit synthetic_touchdown evidence')
        with self._lock:
            mission = self._mission
            if not mission or mission['type'] != 'landing' or mission['phase'] != 'landing' or mission['mission_id'] != mission_id:
                raise ValueError('No matching active mock landing')
            mission['phase'] = 'landed'
            mission['reason'] = 'Synthetic touchdown event; no physical landing occurred.'
            return self.ui_mission()

    def ui_mission(self):
        with self._lock:
            if self._mission is None:
                return {'type': 'none', 'phase': 'idle'}
            mission = dict(self._mission)
            mission.pop('site_id', None)
            mission.pop('simulated', None)
            altitude = mission.pop('landing_altitude_m', None)
            mission.pop('landing_descent_rate_m_s', None)
            mission.pop('mock_fresh_frames', None)
            if altitude is not None:
                mission['progress'] = max(0., min(1., 1. - altitude / .8))
            return mission

    def get(self, request_id):
        with self._lock:
            record = self._records.get(request_id)
            return None if record is None else record[1].model_dump()

    def snapshot(self, capabilities, subsystems, advisory_inspection=None):
        return {
            'schema_version': 1,
            'observed_at': utc_now(),
            'mode': 'MANUAL',
            'control_authority': 'advisory_only',
            'physical_output': False,
            'active_physical_mission': None,
            'mission_state': 'idle',
            'mission_reason': 'No physical follow or landing mission is active',
            'stop_semantics': 'Mock stop ends only the labeled simulation; physical stop is unavailable.',
            'abort_semantics': 'Mission abort is not an emergency motor stop or disarm.',
            'capabilities': capabilities,
            'subsystems': subsystems,
            'advisory_inspection': advisory_inspection,
        }
