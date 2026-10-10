"""Versioned adapter for the existing Flutter operator client."""
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import re
import threading
import time
import uuid

import cv2
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from .mission_control import MissionCommandRequest, capability
from .tag_detector import AprilTagDetector


_REQUEST_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$')


class EmptyRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')


class UICommand(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    request_id: str = Field(min_length=1, max_length=100, pattern=_REQUEST_ID.pattern)
    kind: str = Field(min_length=1, max_length=40)
    payload: dict


def _require_keys(payload, required, optional=()):
    if not isinstance(payload, dict) or not set(required) <= payload.keys() or payload.keys() - set(required) - set(optional):
        raise ValueError('Command payload fields do not match this command')


def _text(value, label, maximum=100):
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > maximum:
        raise ValueError(f'{label} must be nonblank trimmed text')
    return value


def _number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    return float(value)


class PortableAPI:
    """Builds snapshots and command mappings over Engine's shared ledger."""

    def __init__(self, app: FastAPI, engine, token: str):
        self.engine, self.token = engine, token
        self.lock = threading.RLock()
        self.detector = AprilTagDetector()
        self.last_detection_key = None
        self.last_detections = []
        self.last_detection_error = None
        self.frame_cache = OrderedDict()
        self.frame_cache_bytes = 0
        self.current_key = None
        self.current_frame_id = None
        self.sequence = 0

        async def read_access(authorization: str = Header(default='')):
            # An empty token is read-only access, matching the operator client.
            # If a token is supplied it must be valid; never silently downgrade.
            if not authorization:
                return False
            if not hmac.compare_digest(authorization, 'Bearer ' + token):
                raise HTTPException(401, 'Operator token required')
            return True

        async def authorized(authorization: str = Header(default='')):
            if not authorization or not hmac.compare_digest(authorization, 'Bearer ' + token):
                raise HTTPException(401, 'Operator token required')

        @app.get('/api/ui/v1/snapshot')
        async def snapshot(operator_authorized=Depends(read_access)):
            return self.snapshot(operator_authorized=operator_authorized)

        @app.post('/api/ui/v1/commands', dependencies=[Depends(authorized)])
        async def command(request: UICommand):
            try:
                result = self.command(request)
                return {key: result[key] for key in ('request_id', 'state', 'reason')}
            except ValueError as error:
                raise HTTPException(409, str(error))

        @app.get('/api/ui/v1/commands/{request_id}')
        async def command_status(request_id: str, _operator_authorized=Depends(read_access)):
            result = self.engine.mission_command_result(request_id)
            if result is None:
                return {'request_id': request_id, 'state': 'unknown',
                        'reason': 'No result is retained for this request ID; after restart or eviction its outcome is unknown.'}
            return {key: result[key] for key in ('request_id', 'state', 'reason')}

        @app.post('/api/ui/v1/camera/still')
        async def camera_still(_request: EmptyRequest, _operator_authorized=Depends(read_access)):
            record = self.latest_frame(require_fresh=True)
            if record is None:
                raise HTTPException(409, 'A fresh preview frame is not available')
            return {'frame': record['descriptor']}

        @app.get('/api/ui/v1/camera/frames/{frame_id}.jpg')
        async def camera_frame(frame_id: str, _operator_authorized=Depends(read_access)):
            record = self.get_frame(frame_id)
            if record is None:
                raise HTTPException(404, 'Frame is expired or unknown')
            return Response(record['jpeg'], media_type='image/jpeg',
                            headers={'Cache-Control': 'private, no-store'})

    def _tag_list(self, frame, frame_key):
        with self.lock:
            if frame_key == self.last_detection_key:
                return list(self.last_detections)
        detections = []
        detection_error = None
        try:
            observations = self.detector.detect(frame.image) if frame is not None and frame.image is not None else []
            height, width = frame.image.shape[:2] if frame is not None and frame.image is not None else (0, 0)
            if width and height:
                people = {p.tag_id: p.person_id for p in self.engine.roster.people if p.enabled}
                for observation in observations:
                    corners = observation.corners
                    xs, ys = [point[0] / width for point in corners], [point[1] / height for point in corners]
                    x, y = max(0., min(xs)), max(0., min(ys))
                    right, bottom = min(1., max(xs)), min(1., max(ys))
                    if right > x and bottom > y:
                        detections.append({'tag_id': observation.id, 'tag_family': 'tag36h11',
                                           'bounds': [x, y, right - x, bottom - y],
                                           'person_id': people.get(observation.id)})
        except (ValueError, AttributeError, cv2.error) as error:
            detections = []
            detection_error = str(error)[:200]
        with self.lock:
            self.last_detection_key, self.last_detections = frame_key, detections
            self.last_detection_error = detection_error
        return list(detections)

    def _frame_record(self, *, require_fresh=False):
        with self.engine.lock:
            frame = self.engine.preview_frame if self.engine.preview_frame is not None else self.engine.frame
            jpeg = self.engine.preview
            source_kind = self.engine.source_spec.get('kind')
            generation = self.engine.generation
            source_error = self.engine.source_error or self.engine.video_issue
            eof = self.engine.eof
            stale_ms = self.engine.settings.stale_ms
            frame_age_ms = None if frame is None else max(0., (time.monotonic() - frame.captured) * 1000)
            session_id = f'{self.engine.session.id}-{generation}'
            width = self.engine.settings.width
            height = self.engine.settings.height
        if frame is None or jpeg is None:
            return None
        if require_fresh and (source_error or eof or frame_age_ms is None or frame_age_ms > stale_ms):
            return None
        frame_key = (generation, frame.index)
        tags = self._tag_list(frame, frame_key)
        with self.lock:
            if self.current_key == frame_key and self.current_frame_id in self.frame_cache:
                entry = self.frame_cache[self.current_frame_id]
                return entry
            frame_id = 'frame-' + uuid.uuid4().hex
            image = frame.image
            if image is not None and getattr(image, 'ndim', 0) >= 2:
                height, width = image.shape[:2]
            captured_at = getattr(frame, 'captured_utc', '') or datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            valid_for_ms = 4000
            descriptor = {
                'frame_id': frame_id,
                'camera_session_id': session_id,
                'width': int(width), 'height': int(height),
                'captured_at': captured_at,
                'valid_for_ms': valid_for_ms,
                'rotation': 0, 'mirrored': False,
                'crop': [0., 0., 1., 1.],
                'image_path': f'/api/ui/v1/camera/frames/{frame_id}.jpg',
                'tags': tags,
            }
            entry = {'descriptor': descriptor, 'jpeg': bytes(jpeg), 'created': time.monotonic(),
                     'captured_monotonic': frame.captured, 'key': frame_key}
            if len(entry['jpeg']) <= 8 * 1024 * 1024:
                self.frame_cache[frame_id] = entry
                self.frame_cache_bytes += len(entry['jpeg'])
                self.current_key, self.current_frame_id = frame_key, frame_id
                self._trim_frames()
            return entry if frame_id in self.frame_cache else None

    def _trim_frames(self):
        now = time.monotonic()
        for frame_id in list(self.frame_cache):
            entry = self.frame_cache[frame_id]
            if now - entry['created'] > 15 or self.frame_cache_bytes > 8 * 1024 * 1024 or len(self.frame_cache) > 10:
                self.frame_cache_bytes -= len(entry['jpeg'])
                del self.frame_cache[frame_id]
                if self.current_frame_id == frame_id:
                    self.current_key = self.current_frame_id = None

    def get_frame(self, frame_id):
        with self.lock:
            self._trim_frames()
            return self.frame_cache.get(frame_id)

    def latest_frame(self, *, require_fresh=False):
        return self._frame_record(require_fresh=require_fresh)

    def _video_state(self):
        with self.engine.lock:
            kind = self.engine.source_spec.get('kind')
            frame = self.engine.frame
            error = self.engine.source_error or self.engine.video_issue
            eof = self.engine.eof
            age = None if frame is None else max(0., (time.monotonic() - frame.captured) * 1000)
            stale = self.engine.settings.stale_ms
        if error:
            return 'offline', str(error), age
        if eof:
            return 'offline', 'Video source reached end of stream', age
        if age is None:
            return 'reconnecting', 'Waiting for a video frame', age
        if age > stale:
            return 'stale', 'Most recent frame exceeded the configured freshness limit', age
        if kind == 'camera':
            return 'live', None, age
        return 'live', 'Synthetic or recorded preview; not aircraft video', age

    def _capabilities(self):
        with self.engine.lock:
            kind = self.engine.source_spec.get('kind')
            camera_state, _, _ = self._video_state()
            is_mock = kind == 'synthetic'
            people = [person for person in self.engine.roster.people if person.enabled]
            sites = [site for site in self.engine.roster.landing_sites if site.enabled]
        if is_mock:
            preview_ready = camera_state == 'live'
            tracking_ready = self.engine.portable is not None
            follow_reason = ('Add an enabled person with a measured tag size to BALL_ROSTER_FILE.' if not people else
                             (None if preview_ready else 'A fresh synthetic preview is required for mock missions.'))
            current_reason = None if preview_ready else 'A fresh synthetic preview is required for mock missions.'
            tag_reason = ('No enabled AprilTag landing site is configured.' if not sites else
                          (None if preview_ready else 'A fresh synthetic preview is required for mock missions.'))
            if not tracking_ready:
                follow_reason = tag_reason = 'Configure calibrated AprilTag tracking or use --portable-demo.'
            return {
                'follow': capability(bool(people), bool(people and preview_ready and tracking_ready), follow_reason),
                'land_current': capability(True, preview_ready, current_reason),
                'land_point': capability(False, False, 'Image points are not safe physical landing coordinates.'),
                'land_tag': capability(bool(sites), bool(sites and preview_ready and tracking_ready), tag_reason),
                'audio_receive': capability(False, False, 'Audio is outside the portable missions scope.'),
                'audio_transmit': capability(False, False, 'Audio is outside the portable missions scope.'),
                'tts': capability(False, False, 'Audio/TTS is outside the portable missions scope.'),
            }
        if camera_state == 'live':
            live_reason = 'Live AprilTag observation is informational; physical follow is not implemented or authorized.'
        else:
            live_reason = 'Physical follow requires a healthy camera and separately verified translation, override, and failsafe gates.'
        return {
            'follow': capability(False, False, live_reason),
            'land_current': capability(False, False, 'Verified altitude, vertical control, touchdown sensing, and landing failsafes are unavailable.'),
            'land_point': capability(False, False, 'Image points cannot be converted into a safe landing coordinate.'),
            'land_tag': capability(False, False, 'Physical landing-pad descent and loss response are unverified.'),
            'audio_receive': capability(False, False, 'Audio is outside the portable missions scope.'),
            'audio_transmit': capability(False, False, 'Audio is outside the portable missions scope.'),
            'tts': capability(False, False, 'Audio/TTS is outside the portable missions scope.'),
        }

    def snapshot(self, *, operator_authorized=False):
        camera_state, camera_reason, _ = self._video_state()
        record = self.latest_frame()
        with self.engine.lock:
            source_kind = self.engine.source_spec.get('kind')
            observed_at = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            self.sequence += 1
            sequence = self.sequence
            session_id = f'{self.engine.session.id}-{self.engine.generation}'
            target_state = self.engine.mission_control.ui_mission()
            detections = [] if record is None else record['descriptor']['tags']
            with self.lock:
                detector_error = self.last_detection_error
            by_person = {item['person_id']: item for item in detections if item.get('person_id')}
            roster = []
            for person in self.engine.roster.people:
                detection = by_person.get(person.person_id)
                if not person.enabled:
                    state, reason = 'unavailable', 'Roster entry is disabled.'
                elif source_kind == 'synthetic' and camera_state == 'live' and detection:
                    state, reason = 'visible', 'Generated AprilTag observation; not live aircraft video.'
                elif source_kind != 'camera':
                    state, reason = 'unavailable', 'Virtual roster target is available in the mock simulator only.'
                elif camera_state != 'live':
                    state, reason = 'unavailable', camera_reason or 'Live camera is unavailable.'
                elif detector_error:
                    state, reason = 'unavailable', 'AprilTag detection is unavailable: ' + detector_error
                elif detection:
                    state, reason = 'visible', None
                else:
                    state, reason = 'lost', 'The assigned AprilTag is not visible in the latest frame.'
                roster.append({'person_id': person.person_id, 'display_name': person.display_name,
                    'tag_id': person.tag_id, 'tag_family': person.tag_family,
                    'detection_state': state,
                    'available': bool(person.enabled and (state == 'visible' or source_kind == 'synthetic')),
                    'reason': reason})
            if record is None:
                camera = {'state': camera_state, 'name': 'FPV camera' if source_kind == 'camera' else 'Synthetic preview',
                          'session_id': session_id, 'transport': 'none', 'frame': None}
            else:
                preview_name = ('FPV camera' if source_kind == 'camera' else
                    ('Synthetic preview (mock)' if source_kind == 'synthetic' else 'Recorded preview (mock)'))
                camera = {'state': camera_state,
                    'name': preview_name,
                    'session_id': session_id, 'transport': 'jpeg', 'frame': record['descriptor']}
            mission = target_state
            source = 'live' if source_kind == 'camera' and camera_state == 'live' else 'mock'
            components = [
                {'id': 'camera', 'name': 'Video source',
                 'state': 'ready' if camera_state == 'live' and source_kind == 'camera' else ('mock' if source_kind == 'synthetic' else 'offline'),
                 'observed_at': observed_at, 'detail': camera_reason or ('Live camera frames received.' if source_kind == 'camera' else 'Synthetic preview only.')},
                {'id': 'aircraft', 'name': 'Aircraft link', 'state': 'unknown',
                 'observed_at': observed_at, 'detail': 'No verified flight-control or aircraft telemetry path is connected.'},
                {'id': 'mission-simulation', 'name': 'Mission simulation', 'state': 'mock',
                 'observed_at': observed_at, 'detail': 'Simulated mission output never reaches the aircraft bridge.'},
            ]
            if detector_error:
                components.append({'id': 'apriltag-detector', 'name': 'AprilTag detector',
                    'state': 'degraded', 'observed_at': observed_at, 'detail': detector_error})
            tracking = self.engine.portable.snapshot() if self.engine.portable else None
            if tracking is not None:
                components.append({'id': 'relative-target', 'name': 'Relative target observation',
                    'state': 'mock' if source_kind == 'synthetic' else
                             ('ready' if tracking['state'] in ('tracking', 'approaching') else 'degraded'),
                    'observed_at': observed_at,
                    'detail': (tracking.get('reason') or 'Calibrated relative AprilTag pose; no aircraft output.')[:240]})
        return {'api_version': 1, 'sequence': sequence, 'observed_at': observed_at,
            'operator_authorized': bool(operator_authorized), 'source': source,
            'server_name': 'Ball Drone operator backend', 'capabilities': self._capabilities(),
            'roster': roster, 'camera': camera, 'mission': mission,
            'audio': {'state': 'unavailable', 'reason': 'Audio is outside the portable missions scope.',
                      'max_text_length': 2000, 'voices': [], 'speech': []},
            'components': components, 'events': [], 'tracking': tracking}

    def _tag_for_frame(self, frame_id, tag_id):
        record = self._require_fresh_frame(frame_id)
        return next((tag for tag in record['descriptor']['tags'] if tag['tag_id'] == tag_id), None)

    def _require_fresh_frame(self, frame_id):
        record = self.get_frame(frame_id)
        if record is None:
            raise ValueError('The selected camera frame is expired or unknown')
        with self.engine.lock:
            current_generation = self.engine.generation
        age = time.monotonic() - record['captured_monotonic']
        if (record['key'][0] != current_generation or
                age > record['descriptor']['valid_for_ms'] / 1000):
            raise ValueError('The selected camera frame is expired or belongs to a previous camera session')
        return record

    def command(self, request: UICommand):
        if not _REQUEST_ID.fullmatch(request.request_id):
            raise ValueError('Invalid request ID')
        payload = request.payload
        try:
            serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        except (ValueError, TypeError) as error:
            raise ValueError('Command payload must be valid finite JSON') from error
        if len(serialized) > 8192:
            raise ValueError('Command payload exceeds 8 KB')
        digest = hashlib.sha256(serialized).hexdigest()
        command = {'request_id': request.request_id, 'client_payload_sha256': digest}
        if request.kind == 'follow':
            _require_keys(payload, ('person_id',), ('tag_id', 'tag_family'))
            person_id = _text(payload['person_id'], 'person_id', 80)
            person = self.engine.roster.by_person_id(person_id)
            if person is None or not person.enabled:
                raise ValueError('Person is not present and enabled in the server-owned roster')
            if payload.get('tag_id') is not None and (type(payload['tag_id']) is not int or payload['tag_id'] != person.tag_id):
                raise ValueError('Command tag ID does not match the server-owned roster')
            if payload.get('tag_family') is not None and payload['tag_family'] != person.tag_family:
                raise ValueError('Command tag family does not match the server-owned roster')
            command.update(kind='follow', person_id=person_id, tag_id=person.tag_id,
                           tag_family=person.tag_family)
        elif request.kind == 'stop':
            _require_keys(payload, ('mission_id', 'pending_request_id'))
            for key in ('mission_id', 'pending_request_id'):
                if payload[key] is not None:
                    _text(payload[key], key)
            command.update(kind='stop', **payload)
        elif request.kind == 'abort':
            _require_keys(payload, ('mission_id',))
            command.update(kind='abort', mission_id=_text(payload['mission_id'], 'mission_id'))
        elif request.kind == 'land':
            mode = payload.get('mode')
            if mode == 'current_position':
                _require_keys(payload, ('mode',))
                command.update(kind='land_current')
            elif mode in ('camera_point', 'apriltag'):
                _require_keys(payload, ('mode', 'frame_id', 'point'), ('tag_id', 'tag_family'))
                frame_id = _text(payload['frame_id'], 'frame_id')
                point = payload['point']
                _require_keys(point, ('x', 'y'))
                x, y = _number(point['x'], 'point.x'), _number(point['y'], 'point.y')
                if not 0 <= x <= 1 or not 0 <= y <= 1:
                    raise ValueError('Landing point coordinates must be normalized to [0, 1]')
                if mode == 'camera_point':
                    if 'tag_id' in payload or 'tag_family' in payload:
                        raise ValueError('camera_point cannot include AprilTag identity')
                    self._require_fresh_frame(frame_id)
                    command.update(kind='land_point', frame_id=frame_id, x=x, y=y)
                else:
                    if set(('tag_id', 'tag_family')) - payload.keys():
                        raise ValueError('AprilTag landing requires a tag ID and family')
                    tag_id = payload['tag_id']
                    if type(tag_id) is not int or not 0 <= tag_id < 587 or payload['tag_family'] != 'tag36h11':
                        raise ValueError('Invalid landing AprilTag identity')
                    observed = self._tag_for_frame(frame_id, tag_id)
                    site = self.engine.roster.site_by_tag_id(tag_id)
                    if observed is None or site is None:
                        raise ValueError('The selected frame does not show a configured AprilTag landing site')
                    command.update(kind='land_site', site_id=site.site_id)
            else:
                raise ValueError('Unknown landing mode')
        elif request.kind in ('speak', 'audio_uplink'):
            if request.kind == 'speak':
                _require_keys(payload, ('text', 'voice_id'))
                _text(payload['text'], 'text', 2000)
                if payload['voice_id'] is not None:
                    _text(payload['voice_id'], 'voice_id')
            else:
                _require_keys(payload, ('enabled', 'sequence', 'lease_ms'))
                if type(payload['enabled']) is not bool or type(payload['sequence']) is not int or type(payload['lease_ms']) is not int:
                    raise ValueError('Audio uplink fields have invalid types')
            command.update(kind='audio_unavailable')
        else:
            raise ValueError('Unsupported operator command kind')
        validated = MissionCommandRequest.model_validate(command)
        with self.engine.lock:
            is_mock = self.engine.source_spec.get('kind') == 'synthetic'
            caps = self._capabilities()
            simulation_caps = {
                'person_follow': caps['follow'],
                'landing_current': caps['land_current'],
                'landing_site': caps['land_tag'],
                'landing_point': caps['land_point'],
            }
            if is_mock:
                result, duplicate = self.engine.mission_control.submit_mock(validated, simulation_caps, self.engine.roster)
            else:
                result, duplicate = self.engine.mission_control.submit(validated, simulation_caps)
            if self.engine.portable and result['state'] == 'accepted' and request.kind in ('stop', 'abort'):
                self.engine.portable.neutral()
        if not duplicate:
            self.engine.session.event('portable_mission_command', {
                'request_id': result['request_id'], 'kind': request.kind,
                'state': result['state'], 'reason': result['reason'], 'physical_output': False})
        return result


def register_portable_routes(app, engine, token):
    return PortableAPI(app, engine, token)
