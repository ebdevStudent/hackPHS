import json
from pathlib import Path

from ball_demo.config import Settings
from ball_demo.fixtures import trace
from ball_demo.sources import SCENARIOS

root = Path(__file__).resolve().parents[1]
report = {'scope': 'Deterministic synthetic image fixtures; not measured camera or flight accuracy', 'scenarios': []}
for name in SCENARIOS:
    result = trace(name, 160)
    errors, visible, detected, max_yaw = [], 0, 0, 0
    for sample in result['samples']:
        truth, detection = sample['truth'], sample['detection']
        visible += int(truth['visible'])
        detected += int(detection is not None)
        max_yaw = max(max_yaw, abs(sample['yaw']))
        if truth['visible'] and detection:
            errors.append(((detection['x']-truth['x'])**2 + (detection['y']-truth['y'])**2)**.5)
    clear = name in ['centered', 'moving', 'approach', 'edges', 'loss', 'reappear', 'response']
    report['scenarios'].append({'name': name, 'visible_frames': visible, 'detected_frames': detected,
                                'clear_accuracy_gate': clear, 'max_center_error_px': max(errors) if errors else None,
                                'max_yaw': max_yaw, 'states': sorted(set(s['state'] for s in result['samples']))})
    assert max_yaw <= Settings().max_yaw
    if clear: assert max(errors) <= 5 and detected == visible
report['pass'] = True
(root / 'evidence/fixtures.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
