"""Native error, dialog, rendering and launch paths without camera/radio hardware."""
import copy
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip('PySide6')
from PySide6.QtCore import QBuffer, QIODevice, QTimer
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtNetwork import QNetworkReply
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLineEdit, QMessageBox

from ball_demo import desktop
from ball_demo.config import Settings
from ball_demo.fixtures import trace
from test_desktop import client, workstation, state, FakeClient

pytestmark = pytest.mark.desktop


@pytest.mark.parametrize('change', [
    {'state': 'ARMED'}, {'enabled': 1}, {'yaw': True}, {'yaw': 1001}, {'ack_yaw': -1001},
    {'settings': []}, {'source': []}, {'source': {'kind': 'unknown'}}, {'detection': []},
    {'frame_age_ms': -1}, {'ack_age_ms': float('nan')}, {'processing_ms': float('inf')},
    {'processing_ms': '1'}, {'source_label': None}, {'session': 2}, {'bridge_fault': False},
])
def test_invalid_snapshot_values_are_rejected(change):
    with pytest.raises(ValueError): desktop.validate_snapshot(state(**change))


def test_snapshot_accepts_null_timing_and_real_detection():
    desktop.validate_snapshot(state(frame_age_ms=None, processing_ms=None, ack_age_ms=None,
                                    detection={'error': .3, 'quality': .9}))


@pytest.mark.parametrize('change', [
    {'settings': []}, {'settings': {'width': 0}}, {'settings': {'height': 4097}},
    {'settings': {'width': True}}, {'settings': {'width': 3000, 'height': 3000}},
    {'settings': {'processing_hz': 0}}, {'settings': {'processing_hz': '20'}},
    {'settings': {'processing_hz': float('nan')}},
    {'samples': [None]}, {'samples': [{'t': float('nan'), 'state': 'MANUAL', 'yaw': 0}]},
    {'samples': [{'t': 0, 'state': 'ARMED', 'yaw': 0}]},
    {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 1001}]},
    {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': True}]},
    {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 0, 'truth': []}]},
    {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 0, 'detection': 'bad'}]},
    {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 0, 'truth': {'visible': True, 'x': 10}}]},
    {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 0, 'detection': {'bbox': [1, 2]}}]},
    {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 0, 'detection': {'bbox': [1, 2, 3, float('inf')]}}]},
    {'samples': [{'t': 1, 'state': 'MANUAL', 'yaw': 0}, {'t': 0, 'state': 'MANUAL', 'yaw': 0}]},
])
def test_trace_validation_checks_each_field_before_allocating(change):
    value = {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 0}], **change}
    with pytest.raises(ValueError): desktop.validate_trace(value)


def test_empty_client_does_not_send_requests(client):
    client.url = ''; client.request('/api/state')
    assert not client.network.calls and not client.pending


def test_pending_neutral_rejects_enable_callback(client):
    callbacks = []
    client.command('assist', {'enabled': True})
    client.command('assist', {'enabled': False})
    client.request('/api/operator/assist', {'enabled': True}, callback=callbacks.append)
    assert callbacks == [None]


def test_successful_mutation_notifies_and_calls_callback(client):
    callbacks, states, completed = [], [], []
    client.state.connect(states.append); client.completed.connect(completed.append)
    client.request('/api/operator/assist', {'enabled': False}, callback=callbacks.append)
    reply = client.network.calls[-1][2]; reply.body = json.dumps(state()).encode(); reply.finished.emit()
    assert callbacks == states == [state()] and completed == ['assist']


def test_empty_success_returns_empty_object(client):
    callbacks = []
    client.request('/api/operator/reset', {}, callback=callbacks.append)
    client.network.calls[-1][2].finished.emit()
    assert callbacks == [{}]


def test_preview_error_does_not_spam_events(client):
    failures, callbacks = [], []
    client.failed.connect(failures.append)
    client.request('/api/preview.jpg', callback=callbacks.append, binary=True)
    reply = client.network.calls[-1][2]; reply.status = 503; reply.body = b'not json'; reply.finished.emit()
    assert callbacks == [None] and not failures


def test_failed_enable_still_dispatches_queued_disable(client):
    client.command('assist', {'enabled': True}); client.command('assist', {'enabled': False})
    reply = client.network.calls[-1][2]; reply.status = 500; reply.finished.emit()
    assert json.loads(client.network.calls[-1][1]) == {'enabled': False}


def test_native_video_and_plot_render_data_and_stale_state(qapp):
    original = QPixmap(640, 480); original.fill(QColor('#69dc32'))
    buffer = QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly); original.save(buffer, 'PNG')
    video = desktop.VideoView(); video.resize(960, 400)
    frame = video.preview_rect()
    assert frame.width() / frame.height() == pytest.approx(16 / 9, abs=0.01)
    assert frame.x() == pytest.approx((960 - frame.width()) / 2, abs=1)
    assert frame.height() == pytest.approx(400, abs=1)
    image = video.grab().toImage()
    assert video.message == 'No signal'
    assert image.pixelColor(int(frame.left()) + 8, int(frame.top()) + 8) == QColor('#191d20')
    assert image.pixelColor(2, 200) == QColor('#121417')
    center = image.pixelColor(int(frame.center().x()), int(frame.center().y()))
    assert center != QColor('#191d20') and center != QColor('#69dc32')
    video.show_signal = True
    video.set_frame(bytes(buffer.data())); assert not video.pixmap.isNull()
    painted = video.grab().toImage().pixelColor(int(frame.center().x()), int(frame.center().y()))
    assert painted.green() > 180 and painted != center
    video.set_frame(b'invalid image'); assert video.pixmap.toImage() == original.toImage()
    tall = desktop.VideoView(); tall.resize(400, 600)
    portrait = tall.preview_rect()
    assert portrait.width() / portrait.height() == pytest.approx(16 / 9, abs=0.01)
    assert portrait.height() < 600 and portrait.y() == pytest.approx((600 - portrait.height()) / 2, abs=1)
    plot = desktop.CommandPlot(); plot.resize(640, 140)
    empty = plot.grab().toImage()
    for i in range(310): plot.append(state(yaw=500, ack_yaw=-500))
    assert len(plot.samples) == 300 and plot.grab().toImage() != empty
    video.close(); plot.close()


def test_choose_video_viewer_remote_and_cancel_never_change_source(workstation, monkeypatch):
    workstation.authorized = False; workstation.choose_video()
    assert 'Operator access' in workstation.statusBar().currentMessage()
    workstation.authorized = True; original = workstation.backend; workstation.backend = None
    workstation.choose_video()
    assert 'connected server' in workstation.statusBar().currentMessage()
    workstation.backend = original
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: ('', ''))
    workstation.choose_video(); assert not workstation.api.commands


def test_settings_dialog_apply_and_cancel(workstation, monkeypatch):
    workstation.authorized = False; workstation.settings_dialog()
    assert 'operator access' in workstation.statusBar().currentMessage()
    workstation.authorized = True
    monkeypatch.setattr(desktop.SettingsDialog, 'exec', lambda _: QDialog.DialogCode.Rejected)
    workstation.settings_dialog(); assert not workstation.api.commands
    monkeypatch.setattr(desktop.SettingsDialog, 'exec', lambda _: QDialog.DialogCode.Accepted)
    workstation.settings_dialog()
    assert workstation.api.commands[-1] == ('settings', {k: workstation.snapshot['settings'][k] for k in
        ('gain', 'smoothing', 'deadband', 'max_yaw', 'slew_per_s', 'hue_low', 'hue_high',
         'saturation_min', 'value_min', 'min_area', 'max_area', 'direction')})
    dialog = desktop.SettingsDialog(Settings(direction=-1).dict(), workstation)
    dialog.apply(); assert dialog.result() == QDialog.DialogCode.Accepted and dialog.values()['direction'] == -1


def test_repeated_errors_and_event_history_are_bounded(workstation):
    assert workstation.events.topLevelItem(0).text(2) == 'No events'
    workstation.failure('same failure'); workstation.failure('same failure')
    assert workstation.events.topLevelItemCount() == 1
    assert workstation.events.topLevelItem(0).text(2) == 'same failure'
    for i in range(350): workstation.add_event('Test', str(i))
    assert workstation.events.topLevelItemCount() == 300
    assert workstation.events.topLevelItem(0).text(2) == '50'


def test_trace_reaches_end_and_can_restart_or_reject(workstation):
    workstation.show_trace(trace('centered', 3)); playback = workstation.trace_windows[-1]
    playback.toggle(); playback.advance(); playback.advance(); playback.advance()
    assert playback.index == 2 and not playback.timer.isActive()
    playback.toggle(); assert playback.index == 0 and playback.timer.isActive()
    playback.reject(); assert not playback.timer.isActive()


@pytest.mark.parametrize('contents', [None, '{invalid', json.dumps({'samples': []})])
def test_open_trace_missing_invalid_empty_file(workstation, monkeypatch, tmp_path, contents):
    path = tmp_path / 'trace.json'
    if contents is not None: path.write_text(contents)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(path), ''))
    workstation.open_trace()
    assert not workstation.trace_windows and workstation.statusBar().currentMessage()


def test_open_trace_and_scenario_fetch_are_isolated(workstation, monkeypatch, tmp_path):
    path = tmp_path / 'trace.json'; path.write_text(json.dumps(trace('loss', 5)))
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(path), ''))
    workstation.open_trace(); assert len(workstation.trace_windows) == 1
    workstation.play_scenario()
    assert workstation.api.commands[-1] == ('/api/sandbox/moving', None)
    assert not any(action in ('assist', 'source') for action, _ in workstation.api.commands)


def test_session_folder_uses_local_backend_only(workstation, monkeypatch):
    opened = []; monkeypatch.setattr(desktop.QDesktopServices, 'openUrl', lambda url: opened.append(url.toLocalFile()))
    workstation.open_session_folder()
    assert opened == [str(workstation.backend.data / 'sessions/test-session')]
    workstation.backend = None; workstation.open_session_folder()
    assert 'connected server' in workstation.statusBar().currentMessage()
    workstation.authorized = False


def select_connection(monkeypatch, address, token='', accepted=True):
    def execute(dialog):
        fields = dialog.findChildren(QLineEdit)
        fields[0].setText(address); fields[1].setText(token)
        return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected
    monkeypatch.setattr(QDialog, 'exec', execute)
    warnings = []; monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    return warnings


@pytest.mark.parametrize('address', ['ftp://host', 'http://', 'http://user:pass@host',
                                     'http://host/path', 'http://host?query=1', 'http://host#fragment'])
def test_connection_dialog_rejects_nonorigin_addresses(workstation, monkeypatch, address):
    old = workstation.backend; warnings = select_connection(monkeypatch, address)
    workstation.connect_dialog()
    assert warnings and workstation.backend is old and not workstation.api.commands


def test_connection_dialog_cancel_does_not_stop_backend(workstation, monkeypatch):
    old = workstation.backend; select_connection(monkeypatch, 'http://host', accepted=False)
    workstation.connect_dialog(); assert workstation.backend is old


def test_switch_from_local_session_stops_backend_and_checks_remote_token(workstation, monkeypatch, qapp):
    stops = []; workstation.backend.stop = lambda: stops.append(True)
    select_connection(monkeypatch, ' http://remote:8080/ ', 'new-token')
    workstation.connect_dialog(); qapp.processEvents()
    assert stops == [True] and workstation.backend is None
    assert workstation.api.url == 'http://remote:8080' and workstation.api.token == 'new-token'
    assert workstation.snapshot == {} and workstation.video.pixmap.isNull() and not workstation.plot.samples
    assert workstation.authorized and workstation.api.commands[-1] == ('/api/operator/access', None)


def test_switch_remote_requires_neutral_and_viewer_switch_needs_no_token(workstation, monkeypatch):
    workstation.backend = None; select_connection(monkeypatch, 'http://newhost')
    monkeypatch.setattr(workstation, 'neutral_remote', lambda: False)
    workstation.connect_dialog(); assert workstation.api.url != 'http://newhost'
    monkeypatch.setattr(workstation, 'neutral_remote', lambda: True)
    workstation.connect_dialog()
    assert workstation.api.url == 'http://newhost' and not workstation.authorized
    assert not workstation.api.commands


def test_remote_neutral_fails_on_empty_ack_and_viewer_needs_no_ack(workstation, monkeypatch):
    workstation.backend = None
    monkeypatch.setattr(workstation.api, 'request', lambda *args, callback, **kwargs: QTimer.singleShot(0, lambda: callback(None)))
    assert not workstation.neutral_remote()
    workstation.authorized = False; assert workstation.neutral_remote()


@pytest.mark.parametrize('mode', ['local', 'remote', 'startup_error', 'token_error', 'hidden_plugins', 'viewer'])
def test_desktop_entrypoint_boot_snapshot_and_cleanup(qapp, monkeypatch, tmp_path, mode):
    # Test launch wiring separately from the actual-widget and actual-server tests.
    callbacks, backends, windows, errors = [], [], [], []
    class Signal:
        def connect(self, f): callbacks.append(f)
    class App:
        aboutToQuit = Signal()
        def __init__(self, args): self.args = args
        def setApplicationName(self, value): assert value == 'Ball Drone'
        def setOrganizationName(self, value): assert value == 'BallDrone'
        def setApplicationDisplayName(self, value): assert value == 'Ball Drone'
        def setWindowIcon(self, icon): assert not icon.isNull()
        def exec(self):
            for _, f in sorted(timers, key=lambda item: item[0]): f()
            for f in callbacks: f()
            return 0
    class Backend:
        def __init__(self, data, host, port):
            self.data, self.host, self.port, self.started, self.stopped = data, host, port, False, False
            backends.append(self)
            if mode == 'startup_error': raise RuntimeError('occupied ports')
        def start(self): self.started = True
        def stop(self): self.stopped = True
    class Window:
        def __init__(self, backend, url, token): self.backend, self.url, self.token = backend, url, token; windows.append(self)
        def show(self): self.shown = True
        def close(self): self.closed = True
        def grab(self):
            pixmap = QPixmap(20, 20); pixmap.fill(QColor('green')); return pixmap
    from ball_demo import desktop_backend
    monkeypatch.setattr(desktop, 'QApplication', App); monkeypatch.setattr(desktop, 'Workstation', Window)
    monkeypatch.setattr(desktop_backend, 'DesktopBackend', Backend)
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: errors.append(args[-1]))
    # Avoid changing the actual process's Qt plugin paths while testing startup.
    monkeypatch.setattr(desktop.QFileInfo, 'isHidden', lambda _: mode == 'hidden_plugins')
    if mode == 'hidden_plugins':
        plugins = tmp_path / 'plugins'; (plugins / 'platforms').mkdir(parents=True)
        (plugins / 'platforms/libqcocoa.dylib').write_bytes(b'plugin fixture')
        monkeypatch.setattr(desktop.QLibraryInfo, 'path', lambda _: str(plugins))
        monkeypatch.setattr(desktop.sys, 'platform', 'darwin')
        library_paths = []
        monkeypatch.setattr(desktop.QCoreApplication, 'setLibraryPaths', library_paths.append)
        for key in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'):
            monkeypatch.setenv(key, desktop.os.environ.get(key, ''))
    timers = []; monkeypatch.setattr(desktop.QTimer, 'singleShot', lambda ms, f: timers.append((ms, f)))
    token = tmp_path / 'token'
    if mode != 'token_error': token.write_text('remote-token\n')
    args = ['desktop', '--data', str(tmp_path), '--snapshot', str(tmp_path / 'render.png'), '--quit-after', '3']
    if mode == 'remote': args += ['--connect', 'http://remote:8080', '--token-file', str(token)]
    if mode == 'token_error': args += ['--token-file', str(token)]
    if mode == 'viewer': args = ['desktop', '--connect', 'http://remote:8080']
    monkeypatch.setattr(sys, 'argv', args)
    result = desktop.main()
    if mode in ('startup_error', 'token_error'):
        assert result == 1 and errors and not windows
        if mode == 'token_error': assert backends[0].stopped
    else:
        assert result == 0 and windows[0].shown
        if mode != 'viewer':
            assert windows[0].closed and (tmp_path / 'render.png').read_bytes().startswith(b'\x89PNG')
        else: assert not backends and windows[0].token == ''
        if mode == 'remote': assert windows[0].url == 'http://remote:8080' and windows[0].token == 'remote-token' and not backends
        elif mode != 'viewer': assert backends[0].started and backends[0].stopped
        if mode == 'hidden_plugins':
            assert library_paths and not Path(library_paths[0][0]).exists()  # cache cleaned after event loop


def test_trace_hidden_target_and_detection_without_box_can_render(workstation):
    value = {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 0, 'truth': {'visible': False}, 'detection': {'error': 0}}]}
    workstation.show_trace(value)
    assert workstation.trace_windows[-1].index == 0
    assert 'MANUAL' in workstation.trace_windows[-1].readout.text()


def test_import_cancel_and_oversized_trace_do_not_start_playback(workstation, monkeypatch):
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: ('', ''))
    workstation.open_trace(); assert not workstation.trace_windows
    with pytest.raises(ValueError): desktop.validate_trace({'samples': [None] * 100001})
