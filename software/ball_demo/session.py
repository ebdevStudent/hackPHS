import csv
import json
import platform
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__


class Session:
    def __init__(self, root, settings, source):
        self.started = time.monotonic()
        self.id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]
        self.path = Path(root) / self.id
        self.path.mkdir(parents=True, exist_ok=True)
        self.events = (self.path / 'events.jsonl').open('w')
        self.samples = (self.path / 'samples.csv').open('w', newline='')
        self.writer = csv.DictWriter(self.samples, fieldnames=['t', 'state', 'enabled', 'yaw', 'ack_yaw', 'x', 'y', 'error', 'quality', 'frame_age_ms', 'ack_age_ms', 'processing_ms'])
        self.writer.writeheader()
        self.count, self.faults, self.timings = 0, 0, []
        # Evidence logging must never stop the control worker; failures are counted instead.
        self.errors, self.last_error = 0, None
        self.last_frames = None
        self.source, self.settings = dict(source or {}), settings.dict()
        self.source_changes = 0
        self.meta = {'id': self.id, 'software': __version__, 'environment': platform.platform(),
                     'python': platform.python_version(), 'started_utc': datetime.now(timezone.utc).isoformat(),
                     'source': source, 'settings': settings.dict(), 'physical_output': False}
        (self.path / 'config.json').write_text(json.dumps(self.meta, indent=2))
    def failed(self, error):
        self.errors += 1
        self.last_error = f'{type(error).__name__}: {error}'
    def event(self, kind, data):
        if kind == 'fault': self.faults += 1
        if kind == 'source':
            self.source, self.source_changes = dict(data), self.source_changes + 1
        if kind == 'settings': self.settings.update(data)
        try:
            record = {'t': time.monotonic() - self.started, 'type': kind, 'data': data}
            self.events.write(json.dumps(record) + '\n')
            self.events.flush()
        except Exception as error:
            self.failed(error)
    def sample(self, state):
        # Timing statistics describe processed frames, not repeated control observations.
        frames = state.get('frames')
        if state['processing_ms'] is not None and (frames is None or frames != self.last_frames):
            self.timings.append(state['processing_ms'])
            self.timings = self.timings[-200000:]
        self.last_frames = frames
        try: self.write_sample(state)
        except Exception as error: self.failed(error)
    def write_sample(self, state):
        d = state.get('detection') or {}
        self.writer.writerow({'t': round(time.monotonic() - self.started, 4),
                             'state': state['state'], 'enabled': state['enabled'], 'yaw': state['yaw'],
                             'ack_yaw': state['ack_yaw'], 'x': d.get('x'), 'y': d.get('y'),
                             'error': d.get('error'), 'quality': d.get('quality'),
                             'frame_age_ms': state['frame_age_ms'], 'ack_age_ms': state['ack_age_ms'],
                             'processing_ms': state['processing_ms']})
        self.count += 1
        if self.count % 20 == 0: self.samples.flush()
    def close(self, frames):
        elapsed = max(.001, time.monotonic() - self.started)
        ordered = sorted(self.timings)
        summary = {**self.meta, 'duration_s': elapsed, 'control_samples': self.count, 'frames': frames,
                   'processing_fps': frames / elapsed, 'faults': self.faults,
                   'processing_ms_p95': ordered[int(.95 * (len(ordered) - 1))] if ordered else None,
                   'physical_measurements': None, 'final_source': self.source, 'final_settings': self.settings,
                   'source_changes': self.source_changes, 'timing_basis': 'one value per processed frame',
                   'logging_errors': self.errors, 'last_logging_error': self.last_error}
        for action in (lambda: (self.path / 'summary.json').write_text(json.dumps(summary, indent=2)),
                       self.events.close, self.samples.close):
            try: action()
            except Exception as error: self.failed(error)

