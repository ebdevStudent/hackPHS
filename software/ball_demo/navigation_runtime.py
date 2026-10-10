"""Optional slow worker; control only reads cached results and posts invalidation.

No navigation lock is held during image processing, planning or disk writes.
Every invalidation increments an epoch so a late result cannot restore guidance.
"""
import threading
import time
import math
from collections import deque

from .localization import Localizer, Timing
from .navigation import Advisory, NavigationState, vector
from .navigation_replay import Input, Recorder, apply_input


def unavailable(reason='navigation not configured'):
    return NavigationState(available=False, status=reason, guidance_enabled=False).model_dump()


class NavigationRuntime:
    def __init__(self, bundle, path, recording=None):
        from .map_io import Bundle
        from .navigation_replay import Recording
        bundle = Bundle.model_validate(bundle.model_dump())
        recording = Recording.model_validate(recording.model_dump()) if recording is not None else None
        self.bundle, self.recording = bundle, recording
        if recording is not None and recording.bundle.digest != bundle.digest: raise ValueError('Replay/bundle mismatch')
        self.lock = threading.Lock()
        self.commands = deque()
        self.pending = None
        self.epoch = 0
        self.cached = unavailable('waiting for navigation worker')
        self.published_at = None
        self.stop_event = threading.Event()
        self.thread = None
        self.path = path
        self.logging_errors = 0

    def start(self):
        if self.thread is not None: return
        self.thread = threading.Thread(target=self.run, name='navigation', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.invalidate('navigation stopped')
        if self.thread is not None: self.thread.join(timeout=1)

    def invalidate(self, reason):
        with self.lock:
            self.epoch += 1
            self.pending = reason
            self.commands.clear()
            self.cached = unavailable(reason)

    def command(self, kind, goal=None, heading_rad=None, tag_id=None):
        if kind not in ('goal', 'resume', 'disable', 'mission_start', 'mission_advance', 'mission_abort'):
            raise ValueError('Invalid guidance/mission command')
        if kind == 'goal':
            goal = vector(goal).tolist()
            if heading_rad is not None and (type(heading_rad) not in (int, float) or not math.isfinite(heading_rad)):
                raise ValueError('Invalid goal heading')
            if tag_id is not None and (type(tag_id) is not int or tag_id not in {tag.id for tag in self.bundle.survey.tags}):
                raise ValueError('Unknown goal tag')
        elif heading_rad is not None or tag_id is not None:
            raise ValueError('Goal heading/tag requires goal action')
        if kind in ('mission_start', 'mission_advance', 'mission_abort'):
            mission = self.cached.get('mission')
            if mission is None: raise ValueError('Load an inspection mission first')
            status = mission.get('status')
            allowed = {'mission_start': {'ready'}, 'mission_advance': {'target_complete'},
                       'mission_abort': {'ready', 'running', 'waiting_for_localization',
                                         'waiting_for_target', 'reacquiring_target',
                                         'snapshot_pending', 'target_complete', 'fault'}}
            if status not in allowed[kind]: raise ValueError(f'Mission cannot {kind.removeprefix("mission_")} while {status}')
        if kind == 'disable':
            self.invalidate('operator disabled guidance')
            return
        with self.lock:
            if len(self.commands) >= 32: raise ValueError('Navigation command queue full')
            self.commands.append((kind, goal, heading_rad, tag_id))

    def configure_mission(self, mission):
        from .mission import Mission
        mission = Mission.model_validate(mission.model_dump() if isinstance(mission, Mission) else mission)
        mission.validate_bundle(self.bundle)
        with self.lock:
            if len(self.commands) >= 32: raise ValueError('Navigation command queue full')
            self.commands.append(('mission', mission, None, None))

    def snapshot(self, now):
        with self.lock:
            value = dict(self.cached)
            published = self.published_at
        # This gate runs even when the planner or detector is blocked.
        if published is None or now - published >= min(self.bundle.policy.route_ttl_s, self.bundle.policy.pose_max_age_s):
            if published is not None: self.invalidate('navigation worker stalled')
            return unavailable('navigation worker stalled/waiting')
        pose = value.get('pose')
        if pose:
            timing = Timing.model_validate(pose['timing'])
            age = now - timing.oldest_exposure()
            if age >= self.bundle.policy.pose_max_age_s:
                self.invalidate('Stale localization')
                return unavailable('Stale localization')
            value['pose_age_s'] = max(0., age)
        return value

    def frame_input(self, frame, source_kind, sequence, now):
        if source_kind not in ('camera', 'recorded', 'synthetic'):
            raise ValueError('Unknown navigation frame source')
        if self.bundle.map.example and source_kind != 'synthetic': raise ValueError('Example bundle cannot localize a real camera/recording')
        if source_kind == 'synthetic':
            # Existing HSV scenes contain no AprilTags; do not consume their truth.
            provenance, exposure, label = 'synthetic', frame.captured, 'synthetic_estimate'
        else:
            provenance, exposure = 'host_read', None
            label = 'vision_estimate' if source_kind == 'camera' else 'recorded_estimate'
        timing = Timing(host_received_s=frame.captured, exposure_s=exposure, provenance=provenance,
                        delay_bound_s=self.bundle.policy.host_delay_bound_s)
        observations = self.localizer.detect(frame.image)
        return Input(t=now, kind='observations', sequence=sequence, observations=observations, timing=timing, source=label)

    def save_mission_snapshot(self, frame, source_kind):
        """Save a requested operator-approved inspection frame under session storage."""
        import hashlib
        import os
        import cv2
        import numpy as np
        from pathlib import Path
        runner = self.advisory.mission_runner
        if runner is None or runner.status != 'snapshot_pending': return None
        if frame is None or not isinstance(frame.image, np.ndarray) or frame.image.dtype != np.uint8 or frame.image.ndim != 3:
            raise ValueError('No valid frame is available for requested mission snapshot')
        ok, encoded = cv2.imencode('.jpg', frame.image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not ok: raise ValueError('Could not encode requested mission snapshot')
        content = encoded.tobytes()
        digest = hashlib.sha256(content).hexdigest()
        directory = Path(self.path).parent / 'navigation_snapshots'
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        source = {'camera': 'camera', 'recorded': 'recording', 'synthetic': 'synthetic'}.get(source_kind)
        if source is None: raise ValueError('Unknown mission snapshot source')
        name = f'{runner.mission.mission_id}-{runner.index:03d}-{time.monotonic_ns()}-{digest[:16]}.jpg'
        target = directory / name
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return Input(t=time.monotonic(), kind='snapshot_saved', snapshot_sha256=digest, snapshot_source=source)

    def run(self):
        self.advisory, self.localizer = Advisory(self.bundle), Localizer(self.bundle)
        recorder = None
        try:
            try: recorder = Recorder(self.path, self.bundle, 'REPLAY / ' + self.recording.label if self.recording else 'CAMERA/RECORDED estimated vision')
            except Exception: self.logging_errors += 1
            started, index, previous, seen_epoch, sequence = time.monotonic(), 0, None, -1, 0
            replay_origin = self.recording.events[0].t if self.recording else 0
            while not self.stop_event.is_set():
                now = time.monotonic()
                with self.lock:
                    epoch, pending, commands = self.epoch, self.pending, list(self.commands)
                    self.pending, self.commands = None, deque()
                inputs = []
                if epoch != seen_epoch:
                    inputs.append(Input(t=now, kind='loss', reason=pending or 'navigation startup disabled'))
                    seen_epoch = epoch
                for kind, value, heading, tag_id in commands:
                    if kind == 'mission': inputs.append(Input(t=now, kind='mission', mission=value))
                    elif kind in ('mission_start', 'mission_advance', 'mission_abort', 'resume', 'disable'):
                        inputs.append(Input(t=now, kind=kind))
                    else: inputs.append(Input(t=now, kind=kind, goal=value, heading_rad=heading, tag_id=tag_id))
                frame_for_snapshot, snapshot_source = None, None
                if self.recording:
                    while index < len(self.recording.events) and self.recording.events[index].t - replay_origin <= now - started:
                        original = self.recording.events[index]
                        data = original.model_dump(exclude_none=True)
                        offset = started - replay_origin
                        # Intake time is real worker time; the original exposure and
                        # receipt timeline stays in Timing. Backlogged replay events
                        # must not be appended behind a newer watchdog tick.
                        data['t'] = now
                        if data.get('source') == 'vision_estimate': data['source'] = 'recorded_estimate'
                        if original.timing is not None:
                            data['timing']['host_received_s'] += offset
                            if original.timing.exposure_s is not None: data['timing']['exposure_s'] += offset
                        inputs.append(Input.model_validate(data))
                        index += 1
                    # UI restore/goal commands and fixture events share the worker,
                    # but paced replay is always visibly labeled synthetic/recorded.
                    inputs.sort(key=lambda event: event.t)
                else:
                    # Engine offers a mailbox; read it briefly without blocking its worker.
                    frame, key, source_kind, issue = self.get_frame()
                    if issue:
                        if issue != self.advisory.status: inputs.append(Input(t=now, kind='loss', reason=issue))
                    elif frame is not None and key != previous:
                        frame_for_snapshot, snapshot_source = frame, source_kind
                        if previous is not None and (key[0] != previous[0] or key[1] != previous[1] + 1):
                            inputs.append(Input(t=now, kind='loss', reason='Unprocessed video gap; reacquire localization'))
                        previous = key
                        try:
                            inputs.append(self.frame_input(frame, source_kind, sequence, time.monotonic()))
                        except Exception as error:
                            inputs.append(Input(t=time.monotonic(), kind='loss', reason=str(error)))
                        sequence += 1
                for event in inputs:
                    # Live planner keeps its wall deadline. Replay geometry is deterministic.
                    try:
                        apply_input(self.advisory, self.localizer, event, clock=time.monotonic)
                    except ValueError as error:
                        # An invalid operator transition is a rejected command,
                        # not a reason to terminate localization/replay workers.
                        self.advisory.status = 'command rejected: ' + str(error)
                        continue
                    if recorder: recorder.write(event)
                    if self.advisory.mission_runner is not None and self.advisory.mission_runner.status == 'snapshot_pending' and frame_for_snapshot is not None:
                        try:
                            saved = self.save_mission_snapshot(frame_for_snapshot, snapshot_source)
                            if saved is not None:
                                apply_input(self.advisory, self.localizer, saved, clock=time.monotonic)
                                if recorder: recorder.write(saved)
                        except Exception:
                            try: self.advisory.mission_snapshot_failed()
                            except ValueError: pass
                # Always check real elapsed time after solving/planning.
                state = self.advisory.update(time.monotonic())
                with self.lock:
                    if epoch == self.epoch:
                        self.cached, self.published_at = state, time.monotonic()
                if recorder:
                    recorder.write(Input(t=time.monotonic(), kind='tick'))
                    self.logging_errors = recorder.errors
                # Account for work time, avoiding a fixed post-work sleep that
                # steadily skips camera frames even when solving fits the budget.
                self.stop_event.wait(max(0., .05 - (time.monotonic() - now)))
        except Exception as error:
            self.invalidate('navigation worker failed: ' + str(error))
        finally:
            if recorder:
                recorder.close()
                self.logging_errors = recorder.errors
