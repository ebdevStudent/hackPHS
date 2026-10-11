import threading
import time
from pathlib import Path

import cv2

from . import color_pick
from .bridge import MockBridge
from .config import Settings
from .control import Controller
from .mission_control import MissionController, capability
from .session import Session
from .sources import OpenCVSource, SyntheticSource
from .video_health import VideoHealth
from .tag_target import TargetDetector, draw_overlay
from .vision import Detector  # noqa: F401 - the colour path (tests patch engine.Detector)

STEERING_UNAVAILABLE = 'Manual steering — computer steering unavailable'
CAMERA_RETRY_S = 1.0
# A camera open/read can legitimately block for a while; beyond this the worker is reported stalled.
WORKER_STALL_MS = 3000
# The ESP32-S3 can reset when its port opens and needs time to boot before answering HELLO. Stay MANUAL
# while the handshake is pending; only an unanswered handshake beyond this is a fault.
BRIDGE_READY_S = 3.0
# Judge yaw slider: a command older than this (page closed, network gap) sends yaw 0.
JUDGE_LEASE_S = .5
JUDGE_DEFAULT_MAX_YAW = 300
# Wrong judge PINs allowed per minute before refusing further attempts.
JUDGE_MAX_FAILURES = 20


class Engine:
    """Capture may block; control and neutralization have their own clock/thread."""
    def __init__(self, root, settings=None, bridge=None, source=None, navigation_bundle=None, navigation_recording=None, roster=None,
                 portable_calibration=None, portable_delay_s=None, roster_path=None):
        self.settings = settings or Settings()
        self.bridge = bridge or MockBridge(self.settings.watchdog_ms)
        self.bridge_ready = getattr(self.bridge, 'ready', True)
        self.controller = Controller()
        self.lock = threading.RLock()
        self.source_spec = source or {'kind': 'synthetic', 'scenario': 'moving'}
        # True while synthetic frames are running only because no real source was configured.
        self.source_defaulted = source is None
        self.generation = 0
        self.frame = None
        self.detection = None
        self.guidance = None
        self.processing_ms = None
        self.preview = None
        self.preview_frame = None
        self.preview_index = 0
        self.processed = 0
        self.source_error = None
        self.eof = False
        self.running = False
        self.started = time.monotonic()
        self.session = Session(root, self.settings, self.source_spec)
        self.mission_control = MissionController()
        if roster is not None:
            from .roster import Roster
            self.roster = Roster.model_validate(roster.model_dump() if isinstance(roster, Roster) else roster)
        else:
            import os
            from .roster import Roster, load_roster
            roster_path = roster_path or os.environ.get('BALL_ROSTER_FILE')
            self.roster = load_roster(roster_path) if roster_path and Path(roster_path).exists() else Roster()
        self.roster_path = roster_path
        self.ui_sequence = 0
        self.current_source = None
        self.threads = []
        self.video_issue = None
        self.video_report = None
        self.decision_ms = None
        self.lease_deadline = None
        self.settings_version = 0
        self.capture_tick_at = self.control_tick_at = None
        self.navigation = None
        self.portable = None
        if portable_calibration is not None:
            from .portable_runtime import PortableRuntime
            self.portable = PortableRuntime(self, portable_calibration, portable_delay_s)
        self.navigation_config_lock = threading.Lock()
        import os, secrets
        # Judges get a PIN (not the operator token); it only unlocks the yaw slider.
        self.judge_pin = os.environ.get('BALL_JUDGE_PIN') or f'{secrets.randbelow(10 ** 6):06d}'
        self.judge = {'active': False, 'yaw': 0, 'max_yaw': JUDGE_DEFAULT_MAX_YAW, 'updated': None}
        self.judge_failures = []
        if navigation_bundle is not None:
            self.configure_navigation(navigation_bundle, navigation_recording)
    def configure_navigation(self, bundle, recording=None):
        # Import only on opt-in; baseline never loads tag/pose/planner modules.
        from .navigation_runtime import NavigationRuntime
        runtime = NavigationRuntime(bundle, self.session.path / f'navigation-{time.monotonic_ns()}.jsonl', recording)
        def get_frame():
            with self.lock:
                return self.frame, (self.generation, self.frame.index) if self.frame else None, self.source_spec['kind'], self.source_error or self.video_issue or ('video EOF' if self.eof else None)
        runtime.get_frame = get_frame
        # Serialize operator imports/lifecycle without holding the control lock.
        # Otherwise concurrent imports can orphan a running navigation worker.
        with self.navigation_config_lock:
            previous = self.navigation
            self.navigation = runtime
            if previous: previous.stop()
            if self.running: runtime.start()
            self.session.event('navigation_bundle', {'bundle_id': bundle.bundle_id, 'sha256': bundle.digest, 'example': bundle.map.example, 'physical_output': False})
    def navigation_command(self, kind, goal=None, heading_rad=None, tag_id=None):
        with self.navigation_config_lock:
            if self.navigation is None: raise ValueError('Load a navigation bundle first')
            self.navigation.command(kind, goal, heading_rad, tag_id)
    def configure_mission(self, mission):
        with self.navigation_config_lock:
            if self.navigation is None: raise ValueError('Load a navigation bundle first')
            self.navigation.configure_mission(mission)
    def start(self):
        self.running = True
        for target in (self.capture_loop, self.control_loop):
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self.threads.append(thread)
        self.session.event('startup', {'state': 'MANUAL', 'bridge': self.bridge.transport,
                                       'synthetic_fallback': self.synthetic_fallback})
        if self.portable:
            self.portable.start()
        with self.navigation_config_lock:
            if self.navigation: self.navigation.start()
    def stop(self):
        with self.lock:
            self.judge.update(active=False, yaw=0, updated=None)
            self.controller.enable(False)
            try: self.bridge.send(False, 0, time.monotonic())
            except Exception as error: self.session.event('neutral_send_failed', {'reason': str(error)})
            self.running = False
        for thread in self.threads: thread.join(timeout=1)
        if self.portable:
            self.portable.stop()
        with self.navigation_config_lock:
            if self.navigation:
                self.navigation.stop()
                self.session.event('navigation_shutdown', {'logging_errors': self.navigation.logging_errors, 'physical_output': False})
        with self.lock:
            try: self.bridge.close()
            except Exception as error: self.session.event('bridge_close_failed', {'reason': str(error)})
            self.session.event('shutdown', {'yaw': 0})
            self.session.close(self.processed)
    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            return {'state': self.controller.state, 'enabled': self.controller.enabled,
                    'yaw': self.controller.yaw, 'ack_yaw': self.bridge.accepted_yaw,
                    'bridge': self.bridge.transport, 'bridge_fault': self.bridge.fault,
                    'source': dict(self.source_spec),
                    'synthetic_fallback': self.synthetic_fallback,
                    'mock_bridge': isinstance(self.bridge, MockBridge),
                    'source_label': {'synthetic': 'SYNTHETIC', 'recorded': 'RECORDED', 'camera': 'CAMERA'}[self.source_spec['kind']],
                    'frame_age_ms': round((now - self.frame.captured) * 1000, 1) if self.frame else None,
                    'ack_age_ms': round((now - self.bridge.last_ack) * 1000, 1),
                    'fault': self.controller.fault, 'detection': self.detection, 'guidance': self.guidance,
                    'processing_ms': self.processing_ms, 'frames': self.processed,
                    'preview_index': self.preview_index, 'settings': self.settings.dict(),
                    'session': self.session.id, 'physical_telemetry': None,
                    'physical_output': False, 'quality_label': 'heuristic, not a safety probability',
                    # No bridge drives a verified transmitter path, so the pilot steers manually.
                    'steering_available': bool(getattr(self.bridge, 'physical_output', False)),
                    'steering_status': self.steering_status(),
                    'video_health': self.video_report, 'decision_ms': self.decision_ms,
                    'lease_ms_remaining': None if self.lease_deadline is None else
                        max(0., round((self.lease_deadline - now) * 1000, 1)),
                    'judge': self.judge_snapshot(now),
                    'navigation': self.navigation.snapshot(now) if self.navigation else None}
    @property
    def synthetic_fallback(self):
        return self.source_defaulted and self.source_spec['kind'] == 'synthetic'
    def mission_status(self):
        """Return explicit subsystem readiness and non-actuating mission gates."""
        with self.lock:
            state = self.snapshot()
            source_error, eof, video_issue = self.source_error, self.eof, self.video_issue
        source_kind = state['source']['kind']
        frame_age = state['frame_age_ms']
        stale_ms = state['settings']['stale_ms']
        if source_kind == 'synthetic':
            video_state, video_reason = 'mock', 'Synthetic frames are not live aircraft video'
        elif source_error:
            video_state, video_reason = 'fault', str(source_error)
        elif video_issue:
            video_state, video_reason = 'degraded', str(video_issue)
        elif eof:
            video_state, video_reason = 'offline', 'Video source reached end of stream'
        elif frame_age is None:
            video_state, video_reason = 'connecting', 'No frame has arrived from the selected source'
        elif frame_age >= stale_ms:
            video_state, video_reason = 'stale', 'Most recent frame exceeded the freshness limit'
        elif source_kind == 'camera':
            video_state, video_reason = 'live', None
        else:
            video_state, video_reason = 'recorded', 'Recorded video is not live aircraft input'

        output_reported = bool(state['steering_available'])
        if state['bridge_fault'] != 'none':
            bridge_state, bridge_reason = 'fault', str(state['bridge_fault'])
        elif output_reported and state['ack_age_ms'] >= state['settings']['ack_ms']:
            bridge_state, bridge_reason = 'stale', 'Bridge acknowledgement exceeded its freshness limit'
        elif output_reported:
            bridge_state = 'unverified'
            bridge_reason = 'Firmware reports trainer output; transmitter, override and failsafe behavior are not physically verified'
        else:
            bridge_state, bridge_reason = 'unverified', 'Bridge does not provide verified transmitter output'

        navigation = state['navigation']
        if navigation is None:
            localization_state, localization_reason = 'unavailable', 'No navigation bundle is loaded'
        elif navigation.get('pose') is not None:
            localization_state, localization_reason = 'localized', None
        else:
            localization_state = 'waiting'
            localization_reason = navigation.get('status') or 'No accepted pose is available'
        inspection = navigation.get('mission') if navigation else None
        inspection_status = inspection.get('status') if inspection else None
        nav_supported = navigation is not None
        physical_nav_supported = bool(navigation and not navigation.get('example'))
        pose_ready = bool(navigation and navigation.get('pose') is not None and
                          not navigation.get('example') and source_kind == 'camera' and
                          video_state == 'live')
        guidance_ready = bool(navigation and navigation.get('guidance_enabled'))
        inspection_ready = bool(inspection and inspection_status == 'ready')
        if pose_ready:
            localization_capability_reason = None
        elif navigation and navigation.get('example'):
            localization_capability_reason = 'Example map cannot establish physical aircraft localization'
        else:
            localization_capability_reason = localization_reason
        capabilities = {
            'static_tag_localization': capability(
                physical_nav_supported, pose_ready,
                localization_capability_reason),
            'mapped_guidance': capability(
                nav_supported, guidance_ready,
                None if guidance_ready else (navigation.get('status') if navigation else 'No navigation bundle is loaded')),
            'inspection_mission': capability(
                nav_supported, inspection_ready,
                None if inspection_ready else ('No inspection mission is loaded' if not inspection else
                                                f'Inspection mission is {inspection_status}')),
            'person_follow': capability(
                False, False,
                'Moving-target tracking and verified physical flight control are not implemented'),
            'landing_current': capability(
                False, False,
                'Verified vertical control, altitude/velocity state, touchdown detection, and landing failsafes are unavailable'),
            'landing_site': capability(
                False, False,
                'No measured landing-site envelope or verified descent controller is available'),
            'physical_yaw_assistance': capability(
                False, False,
                'End-to-end trainer, transmitter, pilot-override and failsafe behavior lacks physical verification'),
        }
        subsystems = {
            'video': {'state': video_state, 'source': source_kind,
                      'frame_age_ms': frame_age, 'freshness_limit_ms': stale_ms,
                      'reason': video_reason},
            'bridge': {'state': bridge_state, 'transport': state['bridge'],
                       'ack_age_ms': state['ack_age_ms'], 'output_mode_reported': output_reported,
                       'physical_output_verified': False,
                       'reason': bridge_reason},
            'localization': {'state': localization_state,
                             'pose_age_s': navigation.get('pose_age_s') if navigation else None,
                             'reason': localization_reason},
            'flight_controller': {'state': 'unknown',
                                  'reason': 'No measured flight-controller telemetry is connected'},
        }
        return self.mission_control.snapshot(
            capabilities=capabilities,
            subsystems=subsystems,
            advisory_inspection=inspection,
        )
    def submit_mission_command(self, request):
        status = self.mission_status()
        result, duplicate = self.mission_control.submit(
            request,
            status['capabilities'],
            status['active_physical_mission'],
        )
        if not duplicate:
            self.session.event('mission_command', {
                'request_id': result['request_id'],
                'kind': result['kind'],
                'state': result['state'],
                'reason': result['reason'],
                'physical_output': False,
            })
        return result
    def mission_command_result(self, request_id):
        return self.mission_control.get(request_id)
    def health(self):
        """Worker liveness for supervision: running flag alone does not prove the loops still run."""
        now = time.monotonic()
        def age(at): return None if at is None else round((now - at) * 1000, 1)
        threads = [thread.is_alive() for thread in self.threads]
        control_age, capture_age = age(self.control_tick_at), age(self.capture_tick_at)
        ok = (self.running and len(threads) == 2 and all(threads) and control_age is not None and
              control_age < WORKER_STALL_MS and capture_age is not None and capture_age < WORKER_STALL_MS)
        return {'ok': ok, 'workers_alive': threads, 'control_tick_age_ms': control_age,
                'capture_tick_age_ms': capture_age, 'logging_errors': self.session.errors,
                'navigation': None if self.navigation is None else {'worker_alive': bool(self.navigation.thread and self.navigation.thread.is_alive()), 'logging_errors': self.navigation.logging_errors}}
    def steering_status(self):
        if not getattr(self.bridge, 'physical_output', False):
            return STEERING_UNAVAILABLE
        return 'Computer yaw assistance available'
    def assist(self, enabled, leased=False):
        """leased: the request came from a remote operator, so it lapses without heartbeats."""
        with self.lock:
            now = time.monotonic()
            if enabled and (self.frame is None or self.eof or self.source_error or self.video_issue or
                            now - self.frame.captured >= self.settings.stale_ms / 1000 or
                            now - self.bridge.last_ack >= self.settings.ack_ms / 1000 or
                            self.bridge.fault != 'none'):
                raise ValueError('Resolve the source or bridge fault before enabling assistance')
            if enabled and self.judge['active']:
                self.judge.update(active=False, yaw=0, updated=None)
                self.session.event('judge_mode', {'enabled': False, 'reason': 'vision assistance enabled'})
            self.controller.enable(enabled)
            self.lease_deadline = now + self.settings.lease_ms / 1000 if enabled and leased else None
            if not enabled:
                try: self.bridge.send(False, 0, now)
                except Exception as error:
                    self.controller.fail('bridge: ' + str(error))
                    self.session.event('neutral_send_failed', {'reason': str(error)})
            self.session.event('operator_assistance', {'enabled': enabled, 'leased': bool(enabled and leased)})
    # --- judge yaw slider --------------------------------------------------------------------
    def judge_blocked(self, now):
        """Why judge yaw cannot reach the bridge right now, or None."""
        if self.bridge.fault != 'none': return 'bridge fault: ' + str(self.bridge.fault)
        if not getattr(self.bridge, 'ready', True): return 'bridge handshake pending'
        if now - self.bridge.last_ack >= self.settings.ack_ms / 1000: return 'bridge acknowledgement stale'
        return None
    def judge_snapshot(self, now=None):
        now = time.monotonic() if now is None else now
        j = self.judge
        fresh = j['active'] and j['updated'] is not None and now - j['updated'] <= JUDGE_LEASE_S
        return {'active': j['active'], 'yaw': j['yaw'] if fresh else 0, 'max_yaw': j['max_yaw'],
                'lease_ms': int(JUDGE_LEASE_S * 1000)}
    def set_judge_mode(self, enabled, max_yaw=None):
        """Operator-only: allow (or stop) the judges' yaw slider. Turning it on turns vision assist off."""
        with self.lock:
            now = time.monotonic()
            if max_yaw is not None:
                self.judge['max_yaw'] = int(max_yaw)
            if enabled:
                reason = self.judge_blocked(now)
                if reason: raise ValueError(f'Cannot enable judge yaw: {reason}')
                if self.controller.enabled: self.assist(False)
            self.judge.update(active=bool(enabled), yaw=0, updated=None)
            if not enabled:
                try: self.bridge.send(False, 0, now)
                except Exception as error: self.session.event('neutral_send_failed', {'reason': str(error)})
            self.session.event('judge_mode', {'enabled': bool(enabled), 'max_yaw': self.judge['max_yaw']})
            return self.judge_snapshot(now)
    def check_judge_pin(self, pin):
        import hmac
        now = time.monotonic()
        with self.lock:
            self.judge_failures = [t for t in self.judge_failures if now - t < 60]
            if len(self.judge_failures) >= JUDGE_MAX_FAILURES:
                raise PermissionError('Too many wrong PINs: wait a minute')
            if not hmac.compare_digest(str(pin).encode(), self.judge_pin.encode()):
                self.judge_failures.append(now)
                raise PermissionError('Wrong judge PIN')
    def judge_command(self, pin, yaw_pct):
        """Judge slider position in percent of the operator's judge yaw limit."""
        self.check_judge_pin(pin)
        with self.lock:
            if not self.judge['active']:
                raise ValueError('Judge mode is off: ask the operator to turn it on')
            pct = max(-100, min(100, int(yaw_pct)))
            self.judge.update(yaw=int(round(pct / 100 * self.judge['max_yaw'])), updated=time.monotonic())
            return self.judge_snapshot()
    def judge_output(self, tick):
        """Control-loop side (lock held): yaw to send for the judge, or None when judge mode is off."""
        if not self.judge['active']:
            return None
        reason = self.judge_blocked(tick)
        if reason:
            self.judge.update(active=False, yaw=0, updated=None)
            self.session.event('judge_mode', {'enabled': False, 'reason': reason})
            return None
        if self.judge['updated'] is None or tick - self.judge['updated'] > JUDGE_LEASE_S:
            return 0
        return self.judge['yaw']
    def heartbeat(self):
        """Renew an operator lease. Never enables assistance by itself."""
        with self.lock:
            if self.lease_deadline is not None:
                self.lease_deadline = time.monotonic() + self.settings.lease_ms / 1000
            return self.lease_deadline is not None
    def pick_color(self, x, y, apply=False):
        with self.lock:
            if self.frame is None: raise ValueError('No video frame is available to sample')
            image = self.frame.image
        result = color_pick.suggest(image, x, y)
        candidate = {**self.settings.dict(), **result['settings']}
        if candidate['hue_low'] > candidate['hue_high']:
            raise ValueError('Sampled hue range is empty')
        if apply: self.configure(result['settings'])
        result['applied'] = bool(apply)
        return result
    def reload_roster(self):
        """Re-read the operator roster file (tags added with `ball-demo tags`). Disables assistance."""
        from .roster import load_roster
        if not self.roster_path:
            raise ValueError('No roster file configured (start serve with --roster or BALL_ROSTER_FILE)')
        roster = load_roster(self.roster_path)
        with self.lock:
            self.assist(False)
            self.roster = roster
            self.session.event('roster_reload', {'people': len(roster.people), 'landing_sites': len(roster.landing_sites)})
        return roster
    def roster_summary(self):
        with self.lock:
            roster = self.roster
            return {'path': self.roster_path,
                    'people': [{'tag_id': p.tag_id, 'name': p.display_name, 'size_m': p.tag_size_m, 'enabled': p.enabled}
                               for p in roster.people],
                    'landing_sites': [{'tag_id': s.tag_id, 'name': s.display_name, 'size_m': s.tag_size_m, 'enabled': s.enabled}
                                      for s in roster.landing_sites]}
    def set_source(self, spec):
        with self.lock:
            self.assist(False)
            self.mission_control.invalidate_mock('Video source changed; start a new simulated mission explicitly', terminal=True)
            if self.portable:
                self.portable.neutral()
            self.source_spec = spec
            self.source_defaulted = False
            self.generation += 1
            self.frame, self.detection, self.preview = None, None, None
            self.guidance = None
            self.preview_frame = None
            self.source_error, self.eof = None, False
            self.video_issue = self.video_report = self.decision_ms = None
            self.started = time.monotonic()
            if self.navigation: self.navigation.invalidate('video source changed')
            self.session.event('source', spec)
    def configure(self, values):
        with self.lock:
            self.assist(False)
            self.mission_control.invalidate_mock('Capture/settings changed; restart the simulated mission explicitly', terminal=True)
            if self.portable:
                self.portable.neutral()
            for key, value in values.items(): setattr(self.settings, key, value)
            self.settings_version += 1
            self.session.event('settings', values)
    def inject(self, fault):
        if not isinstance(self.bridge, MockBridge): raise ValueError('Fault injection is for the mock bridge only')
        with self.lock:
            self.bridge.fault = fault
            if fault == 'none':
                self.bridge.pending.clear()
                now = time.monotonic()
                self.bridge.send(False, 0, now)
                self.bridge.poll(now)
                # A recovered transport never restores operator assistance.
                self.controller.enable(False)
            self.session.event('bridge_injection', {'fault': fault})
    def open_source(self, spec, settings):
        if spec['kind'] == 'synthetic':
            if spec.get('scenario') == 'portable-tags':
                from .portable_demo import PortableDemoSource
                return PortableDemoSource(settings)
            return SyntheticSource(settings, spec.get('scenario', 'moving'))
        if spec['kind'] == 'recorded':
            return OpenCVSource(spec['path'], settings, True, None, True)
        return OpenCVSource(spec.get('device', 0), settings, False, spec.get('backend'))
    def capture_loop(self):
        source, generation, detector, health = None, -1, TargetDetector(lambda: self.roster), None
        last_preview = 0.
        last_frame_at = retry_at = time.monotonic()
        try:
            while self.running:
                tick = time.monotonic()
                self.capture_tick_at = tick
                with self.lock:
                    spec, requested = dict(self.source_spec), self.generation
                    settings, version = Settings(**self.settings.dict()), self.settings_version
                live = spec['kind'] == 'camera'
                if requested != generation:
                    if source: source.close()
                    generation, detector = requested, TargetDetector(lambda: self.roster)
                    health = VideoHealth() if live else None
                    last_frame_at = tick
                    try:
                        source = self.open_source(spec, settings)
                        self.current_source = source
                    except Exception as error:
                        with self.lock:
                            if generation == self.generation:
                                self.source_error = str(error)
                                if self.navigation and self.navigation.recording is None: self.navigation.invalidate('capture open failed')
                        source = None
                        retry_at = tick + CAMERA_RETRY_S
                if source is None:
                    # A live camera that failed to open is retried; files and scenes are not.
                    if live and tick >= retry_at:
                        generation = -1
                    time.sleep(.05)
                    continue
                if isinstance(source, SyntheticSource): source.yaw = self.controller.yaw
                try: frame = source.read()
                except Exception as error:
                    if not self.running: break
                    with self.lock:
                        # A replaced source may finish its blocked read after the
                        # operator has selected another input. Its failure belongs
                        # to the old generation, not the new source's fault state.
                        if generation == self.generation:
                            self.source_error = str(error)
                            if self.navigation and self.navigation.recording is None: self.navigation.invalidate('capture read failed')
                    frame = None
                    time.sleep(.05)
                if not self.running: break
                if frame is None:
                    if getattr(source, 'eof', False):
                        with self.lock:
                            if generation == self.generation and not self.eof:
                                self.eof = True
                                self.controller.enable(False)
                                if self.navigation and self.navigation.recording is None: self.navigation.invalidate('video EOF')
                                self.session.event('eof', {'action': 'MANUAL'})
                    elif live and time.monotonic() - last_frame_at >= CAMERA_RETRY_S:
                        # Unplugged/stalled capture: reopen the same device. The control loop
                        # has already faulted on the stale frame; recovery never re-enables.
                        source.close()
                        source, generation = None, -1
                        with self.lock: self.session.event('camera_reopen', {'device': spec.get('device')})
                    time.sleep(.01)
                    continue
                last_frame_at = time.monotonic()
                if self.frame is not None and generation == self.generation and frame.index == self.frame.index:
                    time.sleep(1 / settings.processing_hz)
                    continue
                began = time.monotonic()
                if health is not None: health.update(frame.image, frame.captured)
                detection = detector.detect(frame.image, settings)
                guidance = detector.guidance
                processing_ms = round((time.monotonic() - began) * 1000, 3)
                jpeg = None
                if began - last_preview >= 1 / settings.preview_hz:
                    image = frame.image.copy()
                    cv2.line(image, (settings.width // 2, 0), (settings.width // 2, settings.height), (160, 164, 168), 1)
                    if detection:
                        x, y, w, h = detection['bbox']
                        cv2.rectangle(image, (x - 4, y - 4), (x + w + 4, y + h + 4), (90, 240, 160), 2)
                    if guidance: draw_overlay(image, guidance)
                    cv2.putText(image, source.label, (18, 28), cv2.FONT_HERSHEY_SIMPLEX, .65, (210, 224, 233), 1)
                    if self.synthetic_fallback:
                        # No real camera was configured: make fake video impossible to mistake for live FPV.
                        cv2.rectangle(image, (0, settings.height - 36), (settings.width, settings.height), (0, 0, 200), -1)
                        cv2.putText(image, 'SYNTHETIC - NO CAMERA CONFIGURED - NOT LIVE VIDEO', (12, settings.height - 12),
                                    cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2)
                    ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    if ok: jpeg = encoded.tobytes()
                    last_preview = began
                with self.lock:
                    # Drop a detection computed with settings the operator has since replaced.
                    if generation == self.generation and version == self.settings_version:
                        if live and self.source_error:
                            self.source_error = None
                            self.session.event('source_recovered', {'device': spec.get('device')})
                        self.frame, self.detection, self.processing_ms = frame, detection, processing_ms
                        self.guidance = guidance
                        if health is not None:
                            self.video_issue = health.issue(frame.captured, settings.picture_ms)
                            self.video_report = health.report(frame.captured)
                            if self.video_issue and self.navigation and self.navigation.recording is None: self.navigation.invalidate(self.video_issue)
                        # Retain every loss even if the latest-frame mailbox is overwritten
                        # before a control tick; neutral bypasses filtering/slew immediately.
                        if detection is None and self.controller.enabled:
                            self.controller.neutral()
                            self.controller.transition('SEARCHING', 'target lost')
                        self.processed += 1
                        if jpeg is not None:
                            self.preview, self.preview_frame = jpeg, frame
                            self.preview_index += 1
                time.sleep(max(0, 1 / settings.processing_hz - (time.monotonic() - tick)))
        finally:
            if source: source.close()
    def control_loop(self):
        previous_key = None
        last = time.monotonic()
        while self.running:
            tick = time.monotonic()
            self.control_tick_at = tick
            with self.lock:
                try:
                    acks = self.bridge.poll(tick)
                    if getattr(self.bridge, 'ready', True) != self.bridge_ready:
                        self.bridge_ready = not self.bridge_ready
                        self.session.event('bridge_ready' if self.bridge_ready else 'bridge_resync', {'session': self.bridge.session})
                    for ack in acks: self.session.event('ack', ack)
                    reason = None
                    if self.source_error: reason = 'source: ' + self.source_error
                    elif self.video_issue: reason = 'source: ' + self.video_issue
                    elif not self.eof and tick - (self.frame.captured if self.frame else self.started) >= self.settings.stale_ms / 1000: reason = 'stale frame'
                    elif not getattr(self.bridge, 'ready', True):
                        if tick - self.bridge.handshake_started >= BRIDGE_READY_S: reason = 'bridge not responding'
                    elif tick - self.bridge.last_ack >= self.settings.ack_ms / 1000: reason = 'missing acknowledgement'
                    elif self.lease_deadline is not None and self.controller.enabled and tick >= self.lease_deadline:
                        reason = 'operator connection lost'
                    if reason: self.lease_deadline = None
                    if reason and self.controller.state != 'FAULT':
                        self.controller.fail(reason)
                        self.session.event('fault', {'reason': reason, 'yaw': 0})
                        if self.navigation and self.navigation.recording is None: self.navigation.invalidate(reason)
                    key = (self.generation, self.frame.index) if self.frame else None
                    if key is not None and key != previous_key and not reason and not self.eof:
                        self.controller.frame(self.detection, self.settings, tick - last)
                        self.decision_ms = round((time.monotonic() - self.frame.captured) * 1000, 1)
                        previous_key = key
                    judge_yaw = self.judge_output(tick)
                    if judge_yaw is not None:
                        sent_enabled, sent_yaw = True, judge_yaw
                    else:
                        sent_enabled, sent_yaw = self.controller.enabled and self.controller.state == 'LOCKED', self.controller.yaw
                    self.bridge.send(sent_enabled, sent_yaw, tick)
                    mock_source = self.source_spec.get('kind') == 'synthetic'
                    mock_video_healthy = (mock_source and self.frame is not None and not self.source_error and
                        not self.video_issue and not self.eof and
                        tick - self.frame.captured < self.settings.stale_ms / 1000)
                    tracking = self.portable.snapshot() if self.portable else {}
                    self.mission_control.tick_mock(bool(mock_video_healthy),
                        target_visible=False, site_visible=tracking.get('state') == 'approaching',
                        vision_driven=True, dt_s=1 / self.settings.control_hz)
                    state = self.snapshot()
                    self.session.sample(state)
                    self.session.event('command', {'seq': self.bridge.seq, 'enabled': sent_enabled, 'yaw': sent_yaw,
                                                   **({'source': 'judge'} if judge_yaw is not None else {})})
                    for event in self.controller.events: self.session.event('state', event)
                    self.controller.events.clear()
                except Exception as error:
                    # A failing port raises every tick; log the fault once, not at control_hz.
                    if self.controller.state != 'FAULT' or self.controller.fault != 'bridge: ' + str(error):
                        self.controller.fail('bridge: ' + str(error))
                        self.session.event('fault', {'reason': str(error), 'yaw': 0})
            last = tick
            time.sleep(max(0, 1 / self.settings.control_hz - (time.monotonic() - tick)))
