"""Malformed server data and asynchronous operator request ordering regressions."""
import copy
import json

import pytest
pytest.importorskip('PySide6')
from PySide6.QtCore import QTimer
from ball_demo import desktop
from test_desktop import client, workstation, state

pytestmark = pytest.mark.desktop


@pytest.mark.parametrize('change', [
    {'frames': -1}, {'frames': True}, {'fault': 42},
    {'state': 'MANUAL', 'yaw': 500}, {'state': 'LOCKED', 'enabled': False},
    {'detection': {'error': 'bad'}}, {'detection': {'error': float('nan')}},
    {'detection': {'quality': 2}}, {'detection': {'x': float('inf')}},
    {'detection': {'area': -1}}, {'detection': {'bbox': [0, 0, -5, 10]}},
    {'settings': {'gain': 'high'}}, {'settings': {'gain': float('nan')}},
    {'source': {'kind': 'synthetic', 'scenario': []}},
])
def test_snapshot_validation_protects_nested_ui_fields(change):
    with pytest.raises(ValueError): desktop.validate_snapshot(state(**change))


@pytest.mark.parametrize('path,payload', [('/api/state', None), ('/api/operator/assist', {'enabled': False})])
def test_malformed_snapshot_never_reaches_widgets_or_callbacks(client, path, payload):
    snapshots, callbacks, errors, completed = [], [], [], []
    client.state.connect(snapshots.append); client.failed.connect(errors.append); client.completed.connect(completed.append)
    client.request(path, payload, callback=callbacks.append)
    reply = client.network.calls[-1][2]; reply.body = json.dumps(state(fault=42)).encode(); reply.finished.emit()
    assert not snapshots and not completed and callbacks == [None] and errors
    assert client.last_ok == 0 and not client.pending


@pytest.mark.parametrize('value', [None, [], {'authorized': 'false'}, {'authorized': 1}, {'authorized': False}, {}])
def test_authorization_reply_requires_explicit_true(workstation, value):
    workstation.access_checked(value)
    assert not workstation.authorized and not workstation.enable.isEnabled()


def test_authorization_reply_true_keeps_operator_access(workstation):
    workstation.access_checked({'authorized': True})
    assert workstation.authorized and workstation.enable.isEnabled()


@pytest.mark.parametrize('reply', [None, {}, {'enabled': False}, {'enabled': False, 'yaw': 500},
                                  {'enabled': False, 'yaw': True}, state(enabled=True, state='SEARCHING')])
def test_close_neutral_confirmation_requires_complete_zero_snapshot(workstation, monkeypatch, reply):
    monkeypatch.setattr(workstation.api, 'request', lambda *args, callback, **kwargs: QTimer.singleShot(0, lambda: callback(reply)))
    assert not workstation.neutral_remote()
    workstation.authorized = False  # fixture closes without another unconfirmed request


@pytest.mark.parametrize('reason', [None, 'mock unplug'])
def test_neutral_snapshot_confirmation_is_about_requested_internal_state(workstation, monkeypatch, reason):
    # Accepted old yaw can remain until the next bridge poll; no physical ACK claim.
    reply = state(state='FAULT' if reason else 'MANUAL', fault=reason, ack_yaw=500)
    monkeypatch.setattr(workstation.api, 'request', lambda *args, callback, **kwargs: QTimer.singleShot(0, lambda: callback(reply)))
    assert workstation.neutral_remote()


def test_neutral_is_still_sent_when_enable_reply_is_invalid(client):
    client.command('assist', {'enabled': True}); client.command('assist', {'enabled': False})
    first = client.network.calls[-1][2]; first.body = b'{"state":"LOCKED"}'; first.finished.emit()
    assert len(client.network.calls) == 2 and json.loads(client.network.calls[-1][1]) == {'enabled': False}


def test_connection_switch_discards_queued_commands_and_old_credentials(client):
    client.command('assist', {'enabled': True}); client.command('assist', {'enabled': False})
    first = client.network.calls[-1][2]
    client.connect_to('http://new-server:8080', 'new-token')
    first.body = json.dumps(state()).encode(); first.finished.emit()
    assert not client.queued
    assert len([c for c in client.network.calls if c[0].url().path() == '/api/operator/assist']) == 1


@pytest.mark.parametrize('update', [
    {'t': -.1}, {'truth': {'visible': 'yes', 'x': 1, 'y': 1, 'radius': 5}},
    {'truth': {'visible': True, 'x': 1, 'y': 1, 'radius': -5}},
    {'detection': {'bbox': [0, 0, -5, 20]}}, {'detection': {'quality': float('nan')}},
    {'state': 'MANUAL', 'yaw': 500},
])
def test_trace_rejects_invalid_geometry_time_and_state_before_allocation(update):
    sample = {'t': 0, 'state': 'MANUAL', 'yaw': 0, **update}
    with pytest.raises(ValueError): desktop.validate_trace({'samples': [sample]})


@pytest.mark.process
def test_native_module_entrypoint_starts_and_saves_neutral_session(tmp_path):
    import os
    import subprocess
    import sys
    command = [sys.executable, '-m', 'ball_demo.desktop', '--data', str(tmp_path/'data'),
               '--listen', '127.0.0.1', '--port', '0', '--snapshot', str(tmp_path/'window.png'), '--quit-after', '3.3']
    result = subprocess.run(command, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path/'window.png').read_bytes().startswith(b'\x89PNG')
    summaries = list((tmp_path/'data/sessions').glob('*/summary.json')); assert len(summaries) == 1
    summary = json.loads(summaries[0].read_text())
    assert summary['frames'] > 0 and summary['physical_output'] is False
    events = [json.loads(line) for line in (summaries[0].parent/'events.jsonl').read_text().splitlines()]
    assert events[-1]['type'] == 'shutdown' and events[-1]['data']['yaw'] == 0
    commands = [e['data'] for e in events if e['type'] == 'command']; assert commands
    assert all(c['enabled'] is False and c['yaw'] == 0 for c in commands)
