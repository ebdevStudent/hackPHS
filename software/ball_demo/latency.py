"""Camera-to-decision latency: flash a target in front of the camera and time detection.

Each trial shows a blank scene, waits until the detector reports no target, then
switches the target on through a trigger and reads frames until the same
Detector used by the engine finds it. The interval runs from the trigger call to
the moment the detection decision is available on the host. It therefore
includes the trigger's own display or LED delay, the camera, receiver, capture
adapter, driver buffering and processing. It excludes the ESP32-S3 bridge, radio and flight
controller, which need their own measurement.
"""
import json
import statistics
import time
from pathlib import Path

import numpy as np

from .config import Settings
from .vision import Detector


def measure(source, trigger, settings=None, trials=10, timeout=2.0, settle=0.3, clock=time.monotonic):
    """source.read() -> Frame or None; trigger(on: bool) switches the target and returns when issued."""
    settings = settings or Settings()
    detector = Detector()
    results = []
    for trial in range(trials):
        trigger(False)
        quiet_since, deadline = None, clock() + timeout
        while clock() < deadline:
            frame = source.read()
            if frame is None:
                continue
            if detector.detect(frame.image, settings) is None:
                quiet_since = quiet_since or clock()
                if clock() - quiet_since >= settle:
                    break
            else:
                quiet_since = None
        else:
            results.append({'trial': trial, 'error': 'target still visible with the trigger off'})
            continue
        detector = Detector()
        started = clock()
        trigger(True)
        deadline = started + timeout
        found = None
        while clock() < deadline:
            frame = source.read()
            if frame is None:
                continue
            if detector.detect(frame.image, settings) is not None:
                found = clock()
                break
        if found is None:
            results.append({'trial': trial, 'error': 'target not detected before timeout'})
        else:
            results.append({'trial': trial, 'latency_ms': round((found - started) * 1000, 2)})
    trigger(False)
    return summarise(results)


def summarise(results):
    values = sorted(r['latency_ms'] for r in results if 'latency_ms' in r)
    summary = {'trials': len(results), 'measured': len(values), 'failed': len(results) - len(values), 'results': results}
    if values:
        summary.update({'min_ms': values[0], 'median_ms': round(statistics.median(values), 2),
                        'p95_ms': values[min(len(values) - 1, int(round(.95 * (len(values) - 1))))],
                        'max_ms': values[-1]})
    summary['scope'] = ('Trigger-to-host-detection only. Includes trigger display/LED delay; excludes '
                        'ESP32-S3 bridge, radio, receiver-to-motor and flight-controller response.')
    return summary


def save(summary, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2))
    return path


class QtFlash:
    """Full-screen window that turns from black to a bright green disc. Point the camera at it."""

    def __init__(self, settings=None):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QPainter
        from PySide6.QtWidgets import QApplication, QWidget
        self.app = QApplication.instance() or QApplication([])
        self.on = False
        flash = self

        class Window(QWidget):
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.fillRect(self.rect(), QColor('black'))
                if flash.on:
                    painter.setBrush(QColor(50, 220, 105))
                    painter.setPen(Qt.PenStyle.NoPen)
                    side = min(self.width(), self.height()) * .6
                    painter.drawEllipse(int((self.width() - side) / 2), int((self.height() - side) / 2), int(side), int(side))

        self.window = Window()
        self.window.setWindowTitle('Ball Drone latency target')
        self.window.showFullScreen()
        self.app.processEvents()

    def __call__(self, on):
        self.on = bool(on)
        self.window.repaint()
        self.app.processEvents()

    def close(self):
        self.window.close()
        self.app.processEvents()


class GpioLed:
    """Bright LED on a Raspberry Pi GPIO pin (gpiozero), positioned in the camera view."""

    def __init__(self, pin):
        from gpiozero import LED
        self.led = LED(pin)

    def __call__(self, on):
        self.led.on() if on else self.led.off()

    def close(self):
        self.led.close()


class SimulatedCamera:
    """Deterministic camera model for checking the tool: the picture follows the trigger after delay_s."""

    def __init__(self, delay_s=0.08, frame_s=1 / 30, settings=None, clock=time.monotonic, sleep=time.sleep):
        from .sources import Frame
        self.Frame, self.delay, self.frame_s = Frame, delay_s, frame_s
        self.settings = settings or Settings()
        self.clock, self.sleep = clock, sleep
        self.events = [(-1e9, False)]
        self.index = 0

    def trigger(self, on):
        self.events.append((self.clock(), bool(on)))

    def read(self):
        self.sleep(self.frame_s)
        now = self.clock()
        visible = [on for t, on in self.events if t + self.delay <= now][-1]
        image = np.zeros((self.settings.height, self.settings.width, 3), np.uint8)
        if visible:
            import cv2
            cv2.circle(image, (self.settings.width // 2, self.settings.height // 2), 60, (50, 220, 105), -1)
        self.index += 1
        return self.Frame(image, now, self.index, {'visible': visible})
