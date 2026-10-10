import json
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import cv2
import numpy
import serial

from ball_demo.control import Controller
from ball_demo.config import Settings
from ball_demo.sources import synthetic
from ball_demo.vision import Detector

assert platform.machine() == 'aarch64', platform.machine()
root = Path(tempfile.mkdtemp())
process = subprocess.Popen([sys.executable, '-m', 'ball_demo.cli', 'serve', '--port', '8080', '--data', str(root)])
try:
    health = None
    for _ in range(100):
        try:
            health = json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=1))
            break
        except OSError: time.sleep(.1)
    assert health and health['ok'] and health['state'] == 'MANUAL'
    settings, detector, control = Settings(), Detector(), Controller()
    control.enable(True)
    for index in range(30):
        image, truth = synthetic(index, settings)
        d = detector.detect(image, settings)
        assert abs(d['x'] - truth['x']) <= 5
        control.frame(d, settings, .05)
        assert abs(control.yaw) <= settings.max_yaw
    time.sleep(1)
    state = json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/state'))
    assert state['frames'] >= 10 and state['yaw'] == 0
    assert urllib.request.urlopen('http://127.0.0.1:8080/').status == 200
finally:
    process.terminate()
    process.wait(timeout=10)
summary = list(root.glob('*/summary.json'))
assert len(summary) == 1
report = {'environment': platform.platform(), 'machine': platform.machine(), 'python': platform.python_version(),
          'opencv': cv2.__version__, 'numpy': numpy.__version__, 'pyserial': serial.VERSION,
          'health': health, 'summary': json.loads(summary[0].read_text()),
          'pass': True, 'scope': 'Linux ARM64 container; not a Raspberry Pi performance or USB test'}
print(json.dumps(report, indent=2))
