import json
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
python = sys.argv[1]
data = Path(tempfile.mkdtemp(prefix='ball-fresh-'))
process = subprocess.Popen([python, '-m', 'ball_demo.cli', 'serve', '--port', '8083', '--data', str(data)], cwd='/tmp', stdout=subprocess.DEVNULL)
try:
    for _ in range(100):
        try:
            state = json.load(urllib.request.urlopen('http://127.0.0.1:8083/api/state', timeout=1))
            if state['frames'] >= 10: break
        except OSError: pass
        time.sleep(.1)
    assert state['state'] == 'MANUAL' and state['yaw'] == 0 and state['frames'] >= 10
    assert urllib.request.urlopen('http://127.0.0.1:8083/').status == 200
finally:
    process.terminate()
    process.wait(timeout=10)
summaries = list(data.glob('*/summary.json'))
assert len(summaries) == 1
result = {'environment': platform.platform(), 'fresh_python': python, 'state': state,
          'summary': json.loads(summaries[0].read_text()), 'pass': True}
(root / 'evidence/fresh-smoke.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
