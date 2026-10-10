"""Real local HTTP and optional Flutter-client rehearsals; no camera/serial hardware."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from verify import fingerprint

ROOT = Path(__file__).resolve().parents[1]
TOKEN = 'synthetic-rehearsal-token'  # Test-only token; never a saved operator credential.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--flutter', help='Also exercise the real Dart REST gateway against this Python server')
    args = parser.parse_args()
    if not 1 <= args.rounds <= 10:
        parser.error('rounds must be between 1 and 10')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'pass': False, 'started_utc': datetime.now(timezone.utc).isoformat(),
        'environment': platform.platform(), 'python': sys.version, 'source_before': fingerprint(), 'rounds': [],
        'limits': ['Generated AprilTag images, invented optics, mock missions and local HTTP only.',
                   'No Pi, camera, USB board, radio, physical flight or network-profile verification.']}
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    endpoint = f'http://127.0.0.1:{port}'
    def request(path, body=None, authorized=True):
        headers = {'Content-Type': 'application/json'}
        if authorized:
            headers['Authorization'] = 'Bearer ' + TOKEN
        req = urllib.request.Request(endpoint + path,
            data=None if body is None else json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=3) as response:
            data = response.read()
            return json.loads(data) if 'json' in response.headers.get('Content-Type', '') else data
    def snapshot():
        value = request('/api/ui/v1/snapshot')
        baseline = request('/api/state')
        assert value['source'] == 'mock' and value['operator_authorized']
        assert baseline['physical_output'] is False and baseline['enabled'] is False and baseline['yaw'] == 0
        return value
    def phase(expected, timeout=4):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = snapshot()
            if value['mission']['phase'] == expected:
                return value
            time.sleep(.03)
        raise AssertionError(f'Mission did not reach {expected}: {value["mission"]}')
    with tempfile.TemporaryDirectory(prefix='portable-rehearsal-') as runtime:
        env = {**os.environ, 'BALL_OPERATOR_TOKEN': TOKEN, 'PYTHONPATH': str(ROOT / 'software')}
        with (output / 'server.txt').open('w') as log:
            server = subprocess.Popen([sys.executable, '-m', 'ball_demo.cli', 'serve', '--portable-demo',
                '--port', str(port), '--data', runtime], cwd=ROOT / 'software', env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if server.poll() is not None:
                        raise RuntimeError('Server exited during startup')
                    try:
                        if snapshot()['capabilities']['follow']['ready']:
                            break
                    except (OSError, urllib.error.URLError):
                        pass
                    time.sleep(.05)
                else:
                    raise RuntimeError('Server did not become ready')
                assert request('/api/ui/v1/snapshot', authorized=False)['operator_authorized'] is False
                try:
                    request('/api/ui/v1/commands', {'request_id': 'unauthorized', 'kind': 'land',
                        'payload': {'mode': 'current_position'}}, authorized=False)
                except urllib.error.HTTPError as error:
                    assert error.code == 401
                else:
                    raise AssertionError('Anonymous mutation was accepted')
                for index in range(args.rounds):
                    prefix = f'rehearsal-{index}-'
                    body = {'request_id': prefix + 'follow', 'kind': 'follow',
                        'payload': {'person_id': 'synthetic-walker', 'tag_id': 7, 'tag_family': 'tag36h11'}}
                    accepted = request('/api/ui/v1/commands', body)
                    assert accepted['state'] == 'accepted'
                    assert request('/api/ui/v1/commands', body) == accepted
                    active = phase('active')
                    assert active['tracking']['pose']['source'] == 'synthetic_estimate'
                    assert .9 < active['tracking']['pose']['range_m'] < 2.5
                    mid = active['mission']['mission_id']
                    request('/api/ui/v1/commands', {'request_id': prefix + 'stop', 'kind': 'stop',
                        'payload': {'mission_id': mid, 'pending_request_id': None}})
                    stopped = phase('stopped')
                    assert stopped['tracking']['desired'] == {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
                    still = request('/api/ui/v1/camera/still', {})['frame']
                    image = request(still['image_path'])
                    assert image.startswith(b'\xff\xd8')
                    (output / f'{prefix}frame.jpg').write_bytes(image)
                    pending = prefix + 'delayed-start'
                    request('/api/ui/v1/commands', {'request_id': prefix + 'cancel', 'kind': 'stop',
                        'payload': {'mission_id': None, 'pending_request_id': pending}})
                    rejected = request('/api/ui/v1/commands', {**body, 'request_id': pending})
                    assert rejected['state'] == 'rejected'
                    restart = request('/api/ui/v1/commands', {**body, 'request_id': prefix + 'abort-start'})
                    assert restart['state'] == 'accepted'
                    mid = phase('active')['mission']['mission_id']
                    abort = request('/api/ui/v1/commands', {'request_id': prefix + 'abort', 'kind': 'abort',
                        'payload': {'mission_id': mid}})
                    assert abort['state'] == 'accepted'
                    assert phase('aborted')['tracking']['desired'] == {'forward_m_s': 0., 'yaw_rate_rad_s': 0.}
                    land = request('/api/ui/v1/commands', {'request_id': prefix + 'land', 'kind': 'land',
                        'payload': {'mode': 'current_position'}})
                    assert land['state'] == 'accepted'
                    assert snapshot()['mission']['phase'] != 'landed'
                    landed = phase('landed', timeout=10)
                    assert landed['mission']['progress'] == 1
                    assert 'Synthetic touchdown' in landed['mission']['reason']
                    report['rounds'].append({'index': index + 1, 'pass': True,
                        'checks': ['real calibrated pixel pose', 'follow lifecycle', 'exact-request idempotency',
                            'immediate stop/abort/zero', 'late-start cancellation', 'JPEG transport',
                            'explicit simulated touchdown', 'bridge isolation']})
                    print(f'PASS: portable rehearsal {index + 1}', flush=True)
                if args.flutter:
                    command = [args.flutter, 'test', 'test/backend_contract_test.dart', '--reporter=expanded',
                        '--dart-define=BACKEND_URL=' + endpoint, '--dart-define=BACKEND_TOKEN=' + TOKEN]
                    with (output / 'flutter-client.txt').open('w') as client_log:
                        result = subprocess.run(command, cwd=ROOT / 'software/flutter_operator',
                            stdout=client_log, stderr=subprocess.STDOUT, timeout=180)
                    report['flutter_client'] = {'pass': result.returncode == 0, 'command': command}
                    assert result.returncode == 0, 'Flutter backend contract failed; see flutter-client.txt'
                report['pass'] = True
            except Exception as error:
                report['error'] = type(error).__name__ + ': ' + str(error)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
                report['server_exit'] = server.returncode
    report['source_after'] = fingerprint()
    report['source_stable'] = report['source_before'] == report['source_after']
    report['pass'] = report['pass'] and report['source_stable']
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'SHA256SUMS.json').write_text(json.dumps({f.name: hashlib.sha256(f.read_bytes()).hexdigest()
        for f in output.iterdir() if f.is_file() and f.name != 'SHA256SUMS.json'}, indent=2) + '\n')
    print(output / 'report.json', flush=True)
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
