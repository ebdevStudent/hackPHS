"""Independent, non-actuating worker connecting real image inference to mock missions."""
import math
import threading
import time

from .follow_simulation import FollowLimits
from .map_io import Calibration
from .target_tracking import LandingVision, TargetVision


class PortableRuntime:
    def __init__(self, engine, calibration, delay_bound_s):
        self.engine = engine
        self.calibration = Calibration.model_validate(
            calibration.model_dump() if isinstance(calibration, Calibration) else calibration)
        if type(delay_bound_s) not in (int, float) or not math.isfinite(delay_bound_s) or not 0 < delay_bound_s < .25:
            raise ValueError('Target delay bound must be finite and in (0, 0.25) seconds')
        self.delay_bound_s = float(delay_bound_s)
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.tick_at = None
        self.vision = None
        self.identity = None
        self.last_key = None
        self.sequence = 0
        self.speed = 0.
        self.position = [0., 0., 0.]
        self.last_motion_at = None
        self.observed_exposure = None
        self.expired = False
        self.limits = FollowLimits().validate()
        self.report = {'state': 'acquiring', 'reason': 'Waiting for calibrated images',
                       'physical_output': False, 'desired': {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}}

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)
        self.invalidate('Target worker stopped')

    def snapshot(self):
        import copy
        stale = False
        with self.lock:
            if self.observed_exposure is not None and time.monotonic() - self.observed_exposure > .25:
                stale = True
                self.expired = True
                self.speed = 0.
                loss_event = self.report.get('loss_event', False) or self.report['state'] in ('tracking', 'approaching', 'reacquiring')
                self.report.update(state='lost', reason='Target worker observation exceeded its freshness deadline',
                    pose=None, loss_event=loss_event, desired={'forward_m_s': 0., 'yaw_rate_rad_s': 0.})
            report = copy.deepcopy(self.report)
        if stale:
            self.engine.mission_control.invalidate_mock(report['reason'])
        return report

    def neutral(self):
        with self.lock:
            self.speed = 0.
            self.report['desired'] = {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}

    def invalidate(self, reason):
        if self.vision is not None:
            self.vision.tracker.update(None, now_s=time.monotonic())
        with self.lock:
            self.speed = 0.
            self.observed_exposure = None
            self.report.update(state='lost', reason=reason, pose=None,
                               desired={'forward_m_s': 0., 'yaw_rate_rad_s': 0.})
        self.engine.mission_control.invalidate_mock(reason)

    def _motion(self, pose, now, active):
        # These are simulated desired values only. This class has no bridge reference.
        dt = min(.25, max(0., now - self.last_motion_at)) if self.last_motion_at is not None else 0.
        self.last_motion_at = now
        if not active or pose is None:
            self.speed = 0.
            return {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
        forward, lateral = pose.aircraft_from_tag[0][3], pose.aircraft_from_tag[1][3]
        distance = math.hypot(forward, lateral)
        limits = self.limits
        desired = max(0., min(limits.max_speed_m_s,
                             (distance - limits.desired_distance_m - limits.deadband_m) * limits.distance_gain_s))
        yaw_rate = max(-limits.max_yaw_rate_rad_s, min(limits.max_yaw_rate_rad_s,
                                                    pose.bearing_rad * limits.yaw_gain_s))
        self.speed += max(-limits.max_acceleration_m_s2 * dt,
                          min(limits.max_acceleration_m_s2 * dt, desired - self.speed))
        if distance <= limits.min_approach_m:
            self.speed = yaw_rate = 0.
        elif dt > 0:
            self.speed = min(self.speed, (distance - limits.min_approach_m) / dt)
        x, y, yaw = self.position
        yaw += yaw_rate * dt
        x += math.cos(yaw) * self.speed * dt
        y += math.sin(yaw) * self.speed * dt
        xmin, xmax, ymin, ymax = limits.bounds_m
        if not xmin <= x <= xmax or not ymin <= y <= ymax:
            self.engine.mission_control.invalidate_mock('Simulated operating boundary reached', terminal=True)
            self.speed = 0.
            return {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
        self.position = [x, y, yaw]
        return {'forward_m_s': self.speed, 'yaw_rate_rad_s': yaw_rate}

    def process(self, frame, key, source, error=None, *, now=None):
        now = time.monotonic() if now is None else now
        mission = self.engine.mission_control.simulation_mission()
        if error or frame is None or now - frame.captured > .25 or now < frame.captured:
            self.invalidate(error or 'Target image is missing, stale or from the future')
            return
        if self.calibration.example and source != 'synthetic':
            self.invalidate('Example calibration cannot establish live or recorded camera geometry')
            return
        people = [p for p in self.engine.roster.people if p.enabled]
        is_pad = bool(mission and mission['type'] == 'landing' and mission.get('site_id'))
        selected = (self.engine.roster.site_by_id(mission['site_id']) if is_pad else
                    self.engine.roster.by_person_id(mission['person_id']) if mission and mission['type'] == 'follow' else
                    people[0] if people else None)
        if selected is None:
            self.invalidate('No enabled measured target is configured')
            return
        identity = (key[0], mission.get('mission_id') if mission else None,
                    selected.site_id if is_pad else selected.person_id, is_pad)
        if identity != self.identity:
            self.vision = (LandingVision if is_pad else TargetVision)(
                selected, self.calibration, delay_bound_s=self.delay_bound_s)
            self.identity, self.last_key = identity, None
            self.speed, self.position, self.last_motion_at = 0., [0., 0., 0.], None
        with self.lock:
            if self.expired:
                self.vision.tracker.update(None, now_s=now)
                self.expired = False
        if key == self.last_key:
            return  # Repeated control ticks cannot masquerade as fresh camera observations.
        self.last_key = key
        self.sequence += 1
        inference_started = time.monotonic()
        result = self.vision.process(frame.image, sequence=self.sequence,
            captured_s=frame.captured if source == 'synthetic' else None,
            received_s=now, source={'synthetic': 'synthetic_estimate',
                'recorded': 'recorded_estimate', 'camera': 'vision_estimate'}[source])
        with self.engine.lock:
            if self.stop_event.is_set():
                return
            current_key = (self.engine.generation, self.engine.frame.index) if self.engine.frame else None
            if current_key != key:
                return  # A slow inference result belongs to the replaced frame/source.
            if now + time.monotonic() - inference_started - frame.captured > .25:
                self.invalidate('Target inference exceeded the image freshness deadline')
                return
            current_mission = self.engine.mission_control.simulation_mission()
            if (current_mission or {}).get('mission_id') != (mission or {}).get('mission_id'):
                return
            mission = current_mission
            with self.lock:
                if self.expired:
                    result = self.vision.tracker.update(None, now_s=now)
                    self.expired = False
            if source == 'synthetic' and mission and mission['phase'] not in self.engine.mission_control.TERMINAL:
                if is_pad:
                    self.engine.mission_control.update_mock_landing(selected.site_id, result.state, result.reason)
                elif mission['type'] == 'follow':
                    self.engine.mission_control.update_mock_target(selected.person_id, result.state, result.reason)
            active = bool(source == 'synthetic' and mission and mission['type'] == 'follow' and
                          mission['phase'] not in self.engine.mission_control.TERMINAL and result.state == 'tracking')
            desired = self._motion(result.pose, now, active)
            with self.lock:
                self.observed_exposure = result.pose.timing.oldest_exposure() if result.pose is not None else None
                self.report = {**result.model_dump(mode='json'), 'physical_output': False,
                    'desired': desired, 'simulated_position_m': self.position[:2],
                    'calibration_id': self.calibration.calibration_id,
                    'generation': key[0], 'frame_index': key[1]}
            if result.loss_event:
                self.engine.session.event('portable_target_loss', {'sequence': self.sequence,
                    'reason': result.reason, 'physical_output': False})

    def run(self):
        while not self.stop_event.is_set():
            self.tick_at = time.monotonic()
            with self.engine.lock:
                frame = self.engine.frame
                key = (self.engine.generation, frame.index) if frame else None
                source = self.engine.source_spec['kind']
                error = self.engine.source_error or self.engine.video_issue or ('Video EOF' if self.engine.eof else None)
            try:
                self.process(frame, key, source, error)
            except Exception as error:
                self.invalidate('Target inference failed: ' + str(error)[:180])
            self.stop_event.wait(.01)
