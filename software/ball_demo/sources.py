import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import cv2
import numpy as np

log = logging.getLogger(__name__)

# V4L2 and AVFoundation report fps rounded or as 0; NTSC is really 29.97. Beyond this is a real mismatch.
FPS_TOLERANCE = 1.0

SCENARIOS = ['centered', 'moving', 'approach', 'edges', 'brightness', 'distractions', 'small',
             'occlusion', 'blur', 'noise', 'loss', 'absent', 'reappear', 'freeze', 'delay', 'stop', 'response']


@dataclass
class Frame:
    image: np.ndarray
    captured: float
    index: int
    truth: dict
    captured_utc: str = ''

    def __post_init__(self):
        if not self.captured_utc:
            self.captured_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def synthetic(index, settings, scenario='moving', yaw=0, plant_x=None):
    w, h = settings.width, settings.height
    t = index / settings.processing_hz
    x = w / 2 if scenario == 'centered' else w / 2 + w * .30 * math.sin(t * .8)
    y, radius, visible = h / 2, 25, True
    if scenario == 'approach': radius = int(10 + 45 * (1 + math.sin(t)) / 2)
    if scenario == 'edges': x = 28 + (w - 56) * (1 + math.sin(t)) / 2
    if scenario == 'small': radius = 4
    if scenario == 'loss': visible = not (2 <= t % 8 < 4)
    if scenario == 'absent': visible = False
    if scenario == 'reappear':
        visible = not (2 <= t % 8 < 5)
        x = w * (.25 if t % 8 < 2 else .75)
    if scenario == 'response': x = float(plant_x if plant_x is not None else w * .8)
    image = np.full((h, w, 3), (24, 30, 33), np.uint8)
    for gx in range(0, w, 40): cv2.line(image, (gx, 0), (gx, h), (32, 39, 42), 1)
    for gy in range(0, h, 40): cv2.line(image, (0, gy), (w, gy), (32, 39, 42), 1)
    color = (50, 220, 105)
    if scenario == 'brightness': color = tuple(int(c * (.4 + .6 * (1 + math.sin(t)) / 2)) for c in color)
    if visible:
        cv2.circle(image, (round(x), round(y)), radius, color, -1)
    if scenario == 'distractions' and index > 10:
        cv2.circle(image, (int(w * .12), int(h * .22)), 32, color, -1)
    if scenario == 'occlusion':
        cv2.rectangle(image, (round(x), round(y - radius)), (round(x + radius), round(y + radius)), (24, 30, 33), -1)
    if scenario == 'blur': image = cv2.GaussianBlur(image, (17, 17), 4)
    if scenario == 'noise':
        noise = np.random.default_rng(index).normal(0, 16, image.shape)
        image = np.clip(image.astype(float) + noise, 0, 255).astype(np.uint8)
    return image, {'x': round(x), 'y': round(y), 'radius': radius, 'visible': visible,
                   'clear': scenario in ['centered', 'moving', 'approach', 'edges', 'loss', 'reappear', 'response']}


class SyntheticSource:
    label = 'SYNTHETIC'
    def __init__(self, settings, scenario='moving'):
        self.settings, self.scenario, self.index = settings, scenario, 0
        self.last = None
        self.yaw = 0
        self.plant_x = settings.width * .8
    def read(self):
        t = self.index / self.settings.processing_hz
        if self.scenario in ['stop', 'freeze', 'delay'] and t >= 2:
            if self.scenario == 'stop':
                time.sleep(.05)
                return None
            if self.scenario == 'freeze':
                return self.last
            time.sleep(.40)
        self.plant_x = max(30, min(self.settings.width - 30, self.plant_x - self.yaw / 1000 * 9))
        image, truth = synthetic(self.index, self.settings, self.scenario, self.yaw, self.plant_x)
        self.last = Frame(image, time.monotonic(), self.index, truth)
        self.index += 1
        return self.last
    def close(self): pass


class OpenCVSource:
    def __init__(self, identifier, settings, recorded=False, backend=None, paced=False):
        self.label = 'RECORDED' if recorded else 'CAMERA'
        self.recorded, self.settings, self.index, self.eof = recorded, settings, 0, False
        # backend 'v4l2' selects Linux Video4Linux2 explicitly (USB composite capture on the Pi).
        self.capture = cv2.VideoCapture(identifier, cv2.CAP_V4L2) if backend == 'v4l2' else cv2.VideoCapture(identifier)
        if not self.capture.isOpened():
            self.capture.release()
            raise ValueError('Cannot open video source')
        self.file_fps, self.position, self.started, self.last = None, 0, None, None
        if not recorded:
            try:
                self.negotiate_capture_mode(settings)
            except Exception:
                self.capture.release()
                raise
        elif paced:
            # paced: the engine plays files in real time at their own rate; tools read sequentially.
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            self.file_fps = fps if fps and 1 <= fps <= 240 else None
    def negotiate_capture_mode(self, settings):
        """Request the configured mode (FOURCC first, as V4L2 needs), then read back and log what opened."""
        fourcc = settings.capture_fourcc
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, settings.capture_width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.capture_height)
        self.capture.set(cv2.CAP_PROP_FPS, settings.capture_fps)
        # Keep at most one queued frame so the newest picture is processed, not an old backlog.
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        code = int(self.capture.get(cv2.CAP_PROP_FOURCC))
        actual_fourcc = ''.join(chr((code >> (8 * i)) & 0xFF) for i in range(4)).strip(' \x00') or 'unknown'
        width, height = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 0)
        self.mode = {'width': width, 'height': height, 'fps': fps, 'fourcc': actual_fourcc}
        log.info('capture opened: %dx%d @ %.2f fps %s (requested %dx%d @ %g %s)', width, height, fps, actual_fourcc,
                 settings.capture_width, settings.capture_height, settings.capture_fps, fourcc)
        # A wrong size or pixel format means the card never accepted the mode (no signal lock or wrong
        # standard), so fail like an unopenable device; the engine reports it and retries.
        if (width, height) != (settings.capture_width, settings.capture_height) or actual_fourcc != fourcc:
            raise ValueError(f'Capture mode mismatch: requested {settings.capture_width}x{settings.capture_height} {fourcc}, '
                             f'device gave {width}x{height} {actual_fourcc}')
        # fps read-back is unreliable on some drivers, so a mismatch is a loud warning rather than a failure.
        if fps and abs(fps - settings.capture_fps) > FPS_TOLERANCE:
            log.warning('CAPTURE FPS MISMATCH: requested %g fps, device reports %.2f fps', settings.capture_fps, fps)

    def read(self):
        if self.file_fps:
            # Play a recording at its own frame rate: skip frames the processing rate cannot keep up
            # with, and hold the current frame while a slow recording has not advanced.
            now = time.monotonic()
            self.started = self.started if self.started is not None else now
            due = int((now - self.started) * self.file_fps + 1e-6)   # float drift at exact frame boundaries
            if self.last is not None and due < self.position:
                return self.last
            while self.position < due:
                if not self.capture.grab():
                    self.eof = True
                    return None
                self.position += 1
        ok, image = self.capture.read()
        if not ok:
            self.eof = self.recorded
            return None
        image = cv2.resize(image, (self.settings.width, self.settings.height))
        frame = Frame(image, time.monotonic(), self.index, {})
        self.index += 1
        self.position += 1
        self.last = frame
        return frame
    def close(self): self.capture.release()

