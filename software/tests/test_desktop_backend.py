"""Real server/process lifecycle checks; never open a physical serial device."""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from ball_demo.desktop_backend import DesktopBackend

pytestmark = pytest.mark.process


def fetch(url, route='/api/state', token=None, body=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url + route, data=None if body is None else json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=.5) as reply:
        return json.load(reply)


def until(predicate, timeout=8):
    deadline, last = time.monotonic() + timeout, None
    while time.monotonic() < deadline:
        try:
            last = predicate()
            if last: return last
        except (OSError, urllib.error.URLError, ValueError): pass
        time.sleep(.025)
    raise AssertionError(f'Condition not met within {timeout}s; last value: {last!r}')


@pytest.fixture
def backend(tmp_path):
    server = DesktopBackend(tmp_path, host='127.0.0.1', port=0)
    server.start()
    try:
        until(lambda: fetch(server.url)['frames'] >= 4)
        yield server
    finally:
        server.stop()


def test_startup_auth_preview_and_neutral_shutdown(backend):
    initial = fetch(backend.url)
    assert initial['state'] == 'MANUAL' and not initial['enabled'] and initial['yaw'] == 0
    assert initial['physical_output'] is False and 'MOCK' in initial['bridge']
    with pytest.raises(urllib.error.HTTPError) as error:
        fetch(backend.url, '/api/operator/assist', body={'enabled': True})
    assert error.value.code == 401
    fetch(backend.url, '/api/operator/assist', backend.token, {'enabled': True})
    locked = until(lambda: (state if (state := fetch(backend.url))['state'] == 'LOCKED' else None))
    assert abs(locked['yaw']) <= locked['settings']['max_yaw']
    with urllib.request.urlopen(backend.url + '/api/preview.jpg') as response:
        assert response.read()[:2] == b'\xff\xd8'
    backend.stop()
    assert not backend.process.is_alive()
    summary = json.loads((backend.data / 'sessions' / initial['session'] / 'summary.json').read_text())
    assert summary['physical_output'] is False and summary['frames'] > 0
    events = [json.loads(line) for line in (backend.data / 'sessions' / initial['session'] / 'events.jsonl').read_text().splitlines()]
    assert events[-1]['type'] == 'shutdown' and events[-1]['data']['yaw'] == 0
    with socket.socket() as probe:
        assert probe.connect_ex(('127.0.0.1', backend.port)) != 0


def test_restart_creates_new_session_and_stays_disabled(tmp_path):
    sessions, tokens = [], []
    for _ in range(2):
        server = DesktopBackend(tmp_path, host='127.0.0.1', port=0)
        server.start()
        try:
            state = until(lambda: (state if (state := fetch(server.url))['frames'] >= 4 else None))
            sessions.append(state['session']); tokens.append(server.token)
            assert not state['enabled'] and state['yaw'] == 0 and state['state'] == 'MANUAL'
            fetch(server.url, '/api/operator/assist', server.token, {'enabled': True})
        finally: server.stop()
    assert sessions[0] != sessions[1] and tokens[0] != tokens[1]
    assert len(list((tmp_path / 'sessions').glob('*/summary.json'))) == 2


def test_port_collision_falls_back_and_unstarted_stop_releases_port(tmp_path):
    with socket.socket() as occupied:
        occupied.bind(('127.0.0.1', 0)); occupied.listen()
        port = occupied.getsockname()[1]
        server = DesktopBackend(tmp_path, host='127.0.0.1', port=port)
        actual = server.port
        try: assert port < actual <= port + 9
        finally: server.stop()
        server.stop()
        with socket.socket() as probe: probe.bind(('127.0.0.1', actual))


def test_concurrent_instances_preserve_their_private_tokens(tmp_path):
    first = DesktopBackend(tmp_path, host='127.0.0.1', port=0)
    second = DesktopBackend(tmp_path, host='127.0.0.1', port=0)
    try:
        assert first.token_path != second.token_path
        for server in (first, second):
            assert server.token_path.read_text() == server.token
            assert server.token_path.stat().st_mode & 0o777 == 0o600
    finally: first.stop(); second.stop()


@pytest.mark.skipif(os.name != 'posix', reason='Uses POSIX parent-death signals; Mac/Pi target')
def test_parent_death_neutralizes_and_saves_summary(tmp_path):
    code = '''
import json, time
from pathlib import Path
from ball_demo.desktop_backend import DesktopBackend
if __name__ == '__main__':
    server = DesktopBackend(Path(__import__('sys').argv[1]), host='127.0.0.1', port=0)
    server.start()
    print(json.dumps({'url': server.url, 'pid': server.process.pid}), flush=True)
    while True: time.sleep(1)
'''
    parent = subprocess.Popen([sys.executable, '-c', code, str(tmp_path)], stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True)
    child_pid = None
    try:
        import select
        assert select.select([parent.stdout], [], [], 5)[0], 'Parent did not publish its child'
        info = json.loads(parent.stdout.readline()); child_pid = info['pid']
        state = until(lambda: (state if (state := fetch(info['url']))['frames'] >= 4 else None))
        token = next(tmp_path.glob('operator-token*')).read_text()
        fetch(info['url'], '/api/operator/assist', token, {'enabled': True})
        until(lambda: fetch(info['url'])['state'] == 'LOCKED')
        os.kill(parent.pid, signal.SIGKILL); parent.wait(timeout=3)
        summary = tmp_path / 'sessions' / state['session'] / 'summary.json'
        until(summary.exists)
        events = [json.loads(line) for line in (summary.parent / 'events.jsonl').read_text().splitlines()]
        assert events[-1]['type'] == 'shutdown' and events[-1]['data']['yaw'] == 0
        with pytest.raises(urllib.error.URLError): fetch(info['url'])
    finally:
        if parent.poll() is None: parent.kill(); parent.wait(timeout=3)
        parent.stdout.close()
        if child_pid:
            try: os.kill(child_pid, signal.SIGTERM)
            except ProcessLookupError: pass


def test_exhausted_port_range_closes_listener(tmp_path, monkeypatch):
    from ball_demo import desktop_backend as module
    attempts, closed = [], []
    class Listener:
        def setsockopt(self, *args): pass
        def bind(self, address): attempts.append(address); raise OSError('occupied')
        def close(self): closed.append(True)
    monkeypatch.setattr(module.socket, 'socket', lambda *args: Listener())
    with pytest.raises(RuntimeError, match='No available demo port'):
        DesktopBackend(tmp_path, host='127.0.0.1', port=8080)
    assert attempts == [('127.0.0.1', port) for port in range(8080, 8090)] and closed == [True]


def test_stuck_backend_uses_terminate_after_graceful_timeout(tmp_path):
    from types import SimpleNamespace
    calls = []
    backend = DesktopBackend(tmp_path, host='127.0.0.1', port=0)
    backend.process = SimpleNamespace(pid=123, join=lambda timeout: calls.append(('join', timeout)),
                                     is_alive=lambda: True, terminate=lambda: calls.append(('terminate',)))
    backend.stop()
    assert backend.stop_event.is_set() and backend.socket.fileno() == -1
    assert calls == [('join', 4), ('terminate',), ('join', 2)]


def test_server_tick_and_parent_watch_request_neutral(monkeypatch, tmp_path):
    import asyncio
    import threading
    import uvicorn
    from types import SimpleNamespace
    from ball_demo import desktop_backend as module, api, engine
    events, disabled = [], []
    stop = threading.Event()
    class TestEngine:
        def __init__(self, root): assert root == tmp_path / 'sessions'
        def assist(self, enabled): disabled.append(enabled)
    monkeypatch.setattr(engine, 'Engine', TestEngine)
    monkeypatch.setattr(api, 'create_app', lambda current, token: (current, token))
    monkeypatch.setattr(module, 'os', SimpleNamespace(getppid=lambda: 999))
    class Thread:
        def __init__(self, target, daemon): self.target = target; assert daemon
        def start(self): self.target()
    monkeypatch.setattr(threading, 'Thread', Thread)
    monkeypatch.setattr(uvicorn, 'Config', lambda app, **kwargs: SimpleNamespace(app=app, **kwargs))
    class Server:
        def __init__(self, config): self.config = config
        async def on_tick(self, counter): events.append(counter); return False
        def run(self, sockets):
            assert stop.is_set() and sockets == ['listener']
            stop.clear()
            assert asyncio.run(self.on_tick(0)) is False
            stop.set()
            assert asyncio.run(self.on_tick(1)) is True
    monkeypatch.setattr(uvicorn, 'Server', Server)
    module.run_server(str(tmp_path), 'test-token', '127.0.0.1', 8080, 'listener', stop, 456)
    assert disabled == [False] and events == [0]
