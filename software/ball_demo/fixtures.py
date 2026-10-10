import csv
import json
from pathlib import Path

import cv2

from .config import Settings
from .control import Controller
from .sources import SCENARIOS, synthetic
from .vision import Detector


def trace(scenario, frames=200, settings=None):
    settings = settings or Settings()
    detector, control = Detector(), Controller()
    control.enable(True)
    result, plant_x = [], settings.width * .8
    for index in range(frames):
        if scenario == 'response': plant_x -= control.yaw / 1000 * 9
        image, truth = synthetic(index, settings, scenario, plant_x=plant_x)
        detection = detector.detect(image, settings)
        if scenario in ['freeze', 'delay', 'stop'] and index >= 45:
            control.fail('stale frame')
        else: control.frame(detection, settings, 1 / settings.control_hz)
        result.append({'t': index / settings.processing_hz, 'truth': truth, 'detection': detection,
                       'state': control.state, 'yaw': control.yaw, 'enabled': control.enabled})
    return {'scenario': scenario, 'label': 'SYNTHETIC / offline isolated trace',
            'settings': settings.dict(), 'samples': result}


def generate(root, frames=160):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    for scenario in SCENARIOS:
        result = trace(scenario, frames)
        (root / f'{scenario}.json').write_text(json.dumps(result))
        video = cv2.VideoWriter(str(root / f'{scenario}.avi'), cv2.VideoWriter_fourcc(*'MJPG'), settings.processing_hz, (settings.width, settings.height))
        if not video.isOpened(): raise RuntimeError('MJPEG writer unavailable')
        with (root / f'{scenario}-truth.csv').open('w', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=['index', 't', 'x', 'y', 'radius', 'visible', 'clear'])
            writer.writeheader()
            for index, sample in enumerate(result['samples']):
                image, _ = synthetic(index, settings, scenario, plant_x=sample['truth']['x'])
                video.write(image)
                writer.writerow({'index': index, 't': sample['t'], **sample['truth']})
        video.release()
    (root / 'manifest.json').write_text(json.dumps({'scenarios': SCENARIOS, 'frames': frames, 'fps': 20,
                                                  'note': 'Video fixtures show images. Timing faults are injected by the live synthetic adapter, not by the AVI decoder.'}, indent=2))

