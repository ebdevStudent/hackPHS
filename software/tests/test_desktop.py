"""Native widgets and asynchronous client behavior, with no physical devices."""
import json
import time
from types import SimpleNamespace

import pytest

pytest.importorskip('PySide6')
from PySide6.QtCore import QObject, Signal, QByteArray, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ball_demo import desktop
from ball_demo.config import Settings
from ball_demo.desktop_backend import DesktopBackend
from ball_demo.fixtures import trace

pytestmark = pytest.mark.desktop


def state(**changes):
    value = {'state': 'MANUAL', 'enabled': False, 'yaw': 0, 'ack_yaw': 0,
             'bridge': 'MOCK / no physical output', 'bridge_fault': 'none',
             'source': {'kind': 'synthetic', 'scenario': 'moving'}, 'source_label': 'SYNTHETIC',
             'frame_age_ms': 10, 'ack_age_ms': 10, 'fault': None, 'detection': None,
             'processing_ms': 1.2, 'frames': 10, 'preview_index': 3,
             'settings': Settings().dict(), 'session': 'test-session', 'physical_output': False}
    return {**value, **changes}


def pump(app, condition, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition(): return
        time.sleep(.005)
    raise AssertionError('Qt condition did not become true')


class Reply(QObject):
    finished = Signal()
    def __init__(self, body=b'', status=200, error=QNetworkReply.NetworkError.NoError):
        super().__init__()
        self.body, self.status, self.code = body, status, error
    def attribute(self, _): return self.status
    def readAll(self): return QByteArray(self.body)
    def error(self): return self.code
    def errorString(self): return 'fake network failure'


class Network:
    def __init__(self): self.calls = []
    def get(self, request): return self.record(request, None)
    def post(self, request, body): return self.record(request, bytes(body))
    def record(self, request, body):
        reply = Reply()
        self.calls.append((request, body, reply))
        return reply


@pytest.fixture
def client(qapp):
    client = desktop.ApiClient(None)
    client.url, client.token = 'http://127.0.0.1:1', 'test-token'
    client.network = Network()
    yield client
    client.timer.stop(); client.deleteLater(); qapp.processEvents()


def test_qt_noerror_response_counts_as_success(client):
    seen, errors = [], []
    client.state.connect(seen.append); client.failed.connect(errors.append)
    client.request('/api/state')
    reply = client.network.calls[-1][2]
    reply.body = json.dumps(state()).encode(); reply.finished.emit()
    assert seen == [state()] and not errors and client.last_ok > 0


@pytest.mark.parametrize('body,status,error', [
    (b'{broken json', 200, QNetworkReply.NetworkError.NoError),
    (b'{"detail":"Operator token required"}', 401, QNetworkReply.NetworkError.AuthenticationRequiredError),
    (b'', None, QNetworkReply.NetworkError.ConnectionRefusedError),
])
def test_failed_responses_do_not_refresh_freshness(client, body, status, error):
    errors, callbacks, states = [], [], []
    client.failed.connect(errors.append); client.state.connect(states.append)
    client.request('/api/state', callback=callbacks.append)
    reply = client.network.calls[-1][2]
    reply.body, reply.status, reply.code = body, status, error
    reply.finished.emit()
    assert errors and callbacks == [None] and not states and client.last_ok == 0
    assert not client.pending


@pytest.mark.parametrize('body', [b'{}', b'[]', b'null', b'{"state":"LOCKED"}'])
def test_incompatible_snapshot_is_not_considered_fresh(client, body):
    seen, errors = [], []
    client.state.connect(seen.append); client.failed.connect(errors.append)
    client.request('/api/state')
    reply = client.network.calls[-1][2]; reply.body = body; reply.finished.emit()
    assert not seen and errors and client.last_ok == 0


def test_token_only_on_operator_routes_and_no_redirect_following(client):
    for path in ['/api/state', '/api/preview.jpg', '/api/operator/access']:
        client.request(path)
        request = client.network.calls[-1][0]
        assert bytes(request.rawHeader('Authorization')) == (b'Bearer test-token' if '/operator/' in path else b'')
        assert request.attribute(QNetworkRequest.Attribute.RedirectPolicyAttribute) == QNetworkRequest.RedirectPolicy.ManualRedirectPolicy


def test_duplicate_poll_has_at_most_one_outstanding_request_per_endpoint(client):
    for _ in range(20): client.poll()
    assert len(client.network.calls) == 2 and len(client.pending) == 2


def test_old_connection_reply_cannot_update_new_server(client):
    seen = []; client.state.connect(seen.append)
    client.request('/api/state'); old = client.network.calls[-1][2]
    client.connect_to('http://127.0.0.1:2', '')
    old.body = json.dumps(state(session='old')).encode(); old.finished.emit()
    assert not seen and client.last_ok == 0
    new = next(reply for request, _, reply in client.network.calls[1:] if request.url().path() == '/api/state')
    new.body = json.dumps(state(session='new')).encode(); new.finished.emit()
    assert seen[-1]['session'] == 'new'


def test_disable_is_not_dropped_while_enable_request_is_pending(client):
    client.command('assist', {'enabled': True})
    client.command('assist', {'enabled': False})
    first = client.network.calls[0][2]
    first.body = json.dumps(state(enabled=True, state='SEARCHING')).encode()
    first.finished.emit()
    assert len(client.network.calls) == 2
    assert json.loads(client.network.calls[1][1]) == {'enabled': False}


def test_queued_neutral_cannot_be_replaced_by_enable(client):
    errors = []; client.failed.connect(errors.append)
    client.command('assist', {'enabled': True})
    client.command('assist', {'enabled': False})
    client.command('assist', {'enabled': True})
    first = client.network.calls[0][2]
    first.body = json.dumps(state(enabled=True, state='SEARCHING')).encode(); first.finished.emit()
    assert errors and json.loads(client.network.calls[1][1]) == {'enabled': False}


class FakeClient(QObject):
    state = Signal(dict); image = Signal(bytes); failed = Signal(str); completed = Signal(str)
    def __init__(self, parent):
        super().__init__(parent)
        self.url, self.token, self.last_ok = '', '', 0
        self.timer = QTimer(self); self.commands = []
    def connect_to(self, url, token): self.url, self.token = url, token
    def command(self, action, values): self.commands.append((action, values))
    def request(self, path, payload=None, callback=None, binary=False):
        self.commands.append((path, payload))
        if callback: QTimer.singleShot(0, lambda: callback(state(authorized=bool(self.token))))


@pytest.fixture
def workstation(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, 'ApiClient', FakeClient)
    stops = []
    backend = SimpleNamespace(url='http://127.0.0.1:1', token='test-token', data=tmp_path, stop=lambda: stops.append(True))
    window = desktop.Workstation(backend)
    window.freshness.stop()
    window.api.last_ok = time.monotonic()
    window.update_state(state())
    yield window
    for dialog in window.trace_windows: dialog.timer.stop(); dialog.close()
    window.close(); window.deleteLater(); qapp.processEvents()


def test_enable_is_the_only_primary_control(workstation):
    assert workstation.enable.objectName() == 'primaryAction'
    assert workstation.disable.objectName() == 'secondaryAction'
    assert workstation.source_apply.objectName() == 'secondaryAction'
    assert workstation.settings_button.objectName() == 'disclosure'
    assert workstation.state_label.font().pointSize() <= 13


def test_native_buttons_send_explicit_commands(workstation):
    workstation.enable.click(); workstation.disable.click()
    assert workstation.api.commands == [('assist', {'enabled': True}), ('assist', {'enabled': False})]
    workstation.api.commands.clear()
    workstation.fault_choice.setCurrentIndex(2); workstation.fault_apply.click()
    assert workstation.api.commands == [('fault', {'fault': 'missing_ack'})]


@pytest.mark.parametrize('kind,values', [
    (0, {'kind': 'synthetic', 'scenario': 'loss'}),
    (1, {'kind': 'recorded', 'path': '/server/clip.avi'}),
    (2, {'kind': 'camera', 'device': 2}),
])
def test_source_controls_send_the_selected_source(workstation, kind, values):
    workstation.scenario.setCurrentIndex(workstation.scenario.findData('loss'))
    workstation.path.setText('/server/clip.avi'); workstation.camera.setValue(2)
    workstation.source_kind.setCurrentIndex(kind); workstation.source_apply.click()
    assert workstation.api.commands[-1] == ('source', values)


def test_native_file_picker_applies_recorded_video(workstation, monkeypatch):
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: ('/tmp/test.avi', ''))
    workstation.choose_video()
    assert workstation.api.commands[-1] == ('source', {'kind': 'recorded', 'path': '/tmp/test.avi'})


def test_viewer_and_stale_connection_cannot_enable_or_configure(workstation):
    workstation.authorized = False; workstation.update_access()
    for widget in [workstation.enable, workstation.disable, workstation.source_apply, workstation.settings_button, workstation.fault_apply]:
        assert not widget.isEnabled()
    workstation.authorized = True; workstation.api.last_ok = time.monotonic() - 1
    workstation.check_freshness()
    assert workstation.state_label.text() == 'OFFLINE' and workstation.video.stale
    assert not workstation.enable.isEnabled() and not workstation.settings_button.isEnabled()
    assert all(label.text() == '—' for label in workstation.readouts.values())
    assert workstation.disable.isEnabled()  # still permit a deliberate neutral attempt


def test_startup_wait_is_not_a_lost_connection(workstation):
    workstation.snapshot = {}
    workstation.api.last_ok = 0
    workstation.api.url = 'http://127.0.0.1:8091'
    workstation.check_freshness()
    assert workstation.state_label.text() == 'STARTING' and not workstation.video.stale
    assert workstation.video.notice == 'Starting local session'
    assert 'lost' not in workstation.video.notice.lower()
    assert workstation.connection_label.full == 'Starting  ·  http://127.0.0.1:8091'
    assert workstation.connection_label.toolTip() == workstation.connection_label.full
    assert workstation.connection_label.minimumWidth() >= workstation.connection_label.fontMetrics().horizontalAdvance(workstation.connection_label.full)


def test_panels_cannot_float_and_frames_stay_on_screen(workstation):
    from PySide6.QtCore import QRect
    from PySide6.QtWidgets import QDockWidget
    locked = QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
    for dock in (workstation.source_dock, workstation.inspect_dock, workstation.events_dock):
        assert dock.features() == locked and dock.titleBarWidget() is not None
    assert workstation.events.indentation() == 0
    screen = QRect(0, 33, 1470, 840)
    assert desktop.fit_frame(QRect(10, 40, 800, 600), screen) == QRect(10, 40, 800, 600)
    fitted = desktop.fit_frame(QRect(-40, -20, 1800, 1200), screen)
    assert screen.contains(fitted)
    assert fitted.width() == screen.width() and fitted.height() == screen.height()


def test_synthetic_state_stays_placeholder(workstation):
    assert all(label.text() == '—' for label in workstation.readouts.values())
    assert workstation.fault_label.text() == '—'
    assert workstation.source_label.text() == ''
    assert not workstation.plot.samples
    assert workstation.events.topLevelItem(0).text(2) == 'No events'
    assert 'SYNTHETIC' not in workstation.video.caption
    workstation.update_state(state(yaw=40, frames=9, source_label='SYNTHETIC'))
    assert workstation.readouts['yaw'].text() == '—' and workstation.readouts['frames'].text() == '—'
    assert not workstation.plot.samples
    recorded = state(source={'kind': 'recorded', 'path': '/clip.avi'}, source_label='RECORDED', yaw=12, frames=3)
    workstation.update_state(recorded)
    assert workstation.readouts['yaw'].text() == '12' and workstation.readouts['bridge'].text() == '—'
    assert workstation.plot.samples and 'RECORDED' in workstation.source_label.text()
    assert workstation.events.topLevelItem(0).text(2) != 'No events'


def test_reconnection_refreshes_readouts_without_enabling(workstation):
    workstation.api.last_ok = 0; workstation.check_freshness()
    workstation.api.last_ok = time.monotonic(); workstation.update_state(state())
    assert not workstation.video.stale and workstation.state_label.text() == 'MANUAL'
    assert not workstation.api.commands and workstation.snapshot['enabled'] is False


@pytest.mark.parametrize('fields', [ {'hue_low': 90, 'hue_high': 30}, {'min_area': 1000, 'max_area': 100} ])
def test_settings_reject_crossed_ranges(qapp, fields):
    dialog = desktop.SettingsDialog(Settings().dict(), None)
    for key, value in fields.items(): dialog.fields[key].setValue(value)
    dialog.apply()
    assert dialog.result() != QDialog.DialogCode.Accepted and dialog.error.text()
    dialog.close()


def test_fractional_controller_values_are_editable_from_defaults(qapp):
    dialog = desktop.SettingsDialog(Settings().dict(), None)
    dialog.fields['gain'].setValue(123.5)
    dialog.fields['slew_per_s'].setValue(999.5)
    assert dialog.values()['gain'] == 123.5 and dialog.values()['slew_per_s'] == 999.5
    dialog.close()


def test_trace_play_pause_reset_and_close_are_isolated(workstation):
    before = dict(workstation.snapshot)
    workstation.show_trace(trace('loss', 80))
    playback = workstation.trace_windows[-1]
    playback.toggle(); assert playback.timer.isActive()
    playback.advance(); assert playback.index == 1
    playback.toggle(); assert not playback.timer.isActive()
    playback.slider.setValue(25); assert playback.index == 25
    playback.slider.setValue(0); assert playback.index == 0
    playback.toggle(); playback.close()
    assert not playback.timer.isActive()
    assert workstation.snapshot == before and not workstation.api.commands


@pytest.mark.parametrize('invalid', [None, {}, {'samples': []}, {'samples': [{'t': 0}]},
                                     {'samples': [{'t': 0, 'state': 'MANUAL', 'yaw': 0}, {'t': 'bad', 'state': 'MANUAL', 'yaw': 0}]}])
def test_invalid_trace_is_rejected_before_playback(workstation, invalid):
    workstation.show_trace(invalid)
    assert not workstation.trace_windows
    assert 'compatible' in workstation.statusBar().currentMessage()


def test_remote_close_requires_confirmed_neutral(workstation, monkeypatch):
    workstation.backend = None
    monkeypatch.setattr(workstation, 'neutral_remote', lambda: False)
    warnings = []; monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    event = QCloseEvent(); workstation.closeEvent(event)
    assert not event.isAccepted() and warnings
    monkeypatch.setattr(workstation, 'neutral_remote', lambda: True)
    event = QCloseEvent(); workstation.closeEvent(event)
    assert event.isAccepted()


@pytest.mark.process
def test_real_qt_client_operator_and_viewer_against_real_server(qapp, tmp_path):
    backend = DesktopBackend(tmp_path, host='127.0.0.1', port=0)
    backend.start()
    operator = desktop.Workstation(backend)
    viewer = desktop.Workstation(url=backend.url)
    try:
        pump(qapp, lambda: operator.snapshot.get('frames', 0) >= 4 and viewer.snapshot.get('frames', 0) >= 4)
        assert operator.enable.isEnabled() and not viewer.enable.isEnabled()
        assert not operator.video.pixmap.isNull() and not viewer.video.pixmap.isNull()
        operator.enable.click()
        pump(qapp, lambda: operator.snapshot.get('state') == 'LOCKED')
        operator.fault_choice.setCurrentIndex(2); operator.fault_apply.click()
        pump(qapp, lambda: operator.snapshot.get('state') == 'FAULT')
        assert not operator.snapshot['enabled'] and operator.snapshot['yaw'] == 0
        operator.fault_choice.setCurrentIndex(0); operator.fault_apply.click()
        pump(qapp, lambda: operator.snapshot.get('state') == 'MANUAL')
        assert not operator.snapshot['enabled']
        operator.close()
        pump(qapp, lambda: viewer.video.stale)
        assert not backend.process.is_alive()
    finally:
        viewer.close(); operator.close(); backend.stop()
        viewer.deleteLater(); operator.deleteLater(); qapp.processEvents()


@pytest.mark.process
def test_remote_operator_close_neutralizes_without_stopping_server(qapp, tmp_path):
    from urllib.request import urlopen
    backend = DesktopBackend(tmp_path, host='127.0.0.1', port=0)
    backend.start()
    # Wait for readiness before the remote authorization handshake.
    from test_desktop_backend import until, fetch
    until(lambda: fetch(backend.url)['frames'] >= 4)
    window = desktop.Workstation(url=backend.url, token=backend.token)
    try:
        pump(qapp, lambda: window.authorized and window.snapshot.get('frames', 0) >= 4)
        window.enable.click(); pump(qapp, lambda: window.snapshot.get('state') == 'LOCKED')
        window.close()
        with urlopen(backend.url + '/api/state') as response: actual = json.load(response)
        assert actual['state'] == 'MANUAL' and not actual['enabled'] and actual['yaw'] == 0
        assert backend.process.is_alive()
        assert not window.authorized  # a repeated close needs no second remote handshake
    finally:
        window.authorized = False; window.close(); backend.stop()
        window.deleteLater(); qapp.processEvents()
