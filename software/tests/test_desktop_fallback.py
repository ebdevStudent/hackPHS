"""Native manual-fallback overlays, click-to-pick colour and operator-lease heartbeats."""
import json
import time
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

pytest.importorskip('PySide6')
from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QPixmap, QImage, QColor
from PySide6.QtWidgets import QToolBar

from ball_demo import desktop
from ball_demo.engine import STEERING_UNAVAILABLE
from test_desktop import FakeClient, Network, state

pytestmark = pytest.mark.desktop


def camera_state(**changes):
    detection = {'x': 480.0, 'y': 240.0, 'area': 1900.0, 'bbox': [455, 215, 51, 51], 'error': .5, 'quality': .9}
    value = state(source={'kind': 'camera', 'device': 0}, source_label='CAMERA', detection=detection,
                  steering_available=False, steering_status=STEERING_UNAVAILABLE)
    return {**value, **changes}


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, 'ApiClient', FakeClient)
    backend = SimpleNamespace(url='http://127.0.0.1:1', token='test-token', data=tmp_path, stop=lambda: None)
    window = desktop.Workstation(backend)
    window.freshness.stop()
    window.api.last_ok = time.monotonic()
    window.update_state(state(steering_status=STEERING_UNAVAILABLE, steering_available=False))
    yield window
    window.close(); window.deleteLater(); qapp.processEvents()


def jpeg(width=640, height=480):
    image = np.zeros((height, width, 3), np.uint8)
    cv2.circle(image, (width // 2, height // 2), 40, (50, 220, 105), -1)
    return cv2.imencode('.jpg', image)[1].tobytes()


def banner_pixels(widget):
    """Count yellow-ish banner text pixels in the top band of the 16:9 plate."""
    image = widget.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    frame = widget.preview_rect()
    count = 0
    for y in range(int(frame.top()), int(frame.top()) + 34):
        for x in range(int(frame.left()), int(frame.right()), 2):
            colour = QColor(image.pixel(x, y))
            if colour.red() > 180 and colour.green() > 140 and colour.blue() < 140:
                count += 1
    return count


# ---------------------------------------------------------------- overlay
def test_status_banner_is_drawn_even_without_a_live_picture(qapp, window):
    video = window.video
    assert video.steering_text == 'Manual steering — computer steering unavailable'
    assert not video.show_signal and video.error is None and video.target_text == ''
    video.resize(800, 450); video.show(); qapp.processEvents()
    assert banner_pixels(video) > 20
    video.steering_text = ''
    assert banner_pixels(video) == 0


def test_live_camera_state_sets_error_indicator_and_target_text(qapp, window):
    window.update_state(camera_state())
    assert window.video.error == .5 and window.video.target_text == 'Target tracked'
    window.update_state(camera_state(detection=None))
    assert window.video.error is None and window.video.target_text == 'Target not found'
    window.update_state(camera_state(steering_status=123))
    assert window.video.steering_text == ''


def test_synthetic_state_never_shows_an_error_value(window):
    window.update_state(state(detection={'x': 1.0, 'y': 1.0, 'area': 200.0, 'bbox': [0, 0, 5, 5], 'error': -.9, 'quality': .4},
                              steering_status=STEERING_UNAVAILABLE))
    assert window.video.error is None and window.video.target_text == ''


@pytest.mark.parametrize('error', [-1.0, -.25, 0.0, .7, 1.0, 3.0, None])
def test_overlay_paints_for_every_error_value(qapp, error):
    video = desktop.VideoView()
    video.resize(640, 360)
    video.show_signal = True
    video.set_frame(jpeg())
    video.steering_text = STEERING_UNAVAILABLE
    video.error, video.target_text = error, 'Target tracked'
    assert not video.grab().isNull() and banner_pixels(video) > 20
    video.stale = True
    assert banner_pixels(video) == 0   # stale overlay replaces live overlays
    video.deleteLater()


def test_overlay_skips_the_indicator_on_a_tiny_picture(qapp):
    video = desktop.VideoView()
    video.resize(320, 180)
    video.show_signal = True
    pixmap = QPixmap(20, 200); pixmap.fill(Qt.GlobalColor.darkGray)
    video.pixmap = pixmap
    video.error = .3
    assert not video.grab().isNull()
    video.deleteLater()


# ---------------------------------------------------------------- picking
def test_picture_position_maps_the_letterboxed_image(qapp):
    video = desktop.VideoView()
    video.resize(800, 450)
    assert video.picture_position(QPointF(400, 225)) is None      # no picture yet
    video.set_frame(jpeg(640, 480))
    rect = video.image_rect()
    assert abs(rect.height() - 450) < 1 and abs(rect.width() - 600) < 1
    x, y = video.picture_position(QPointF(400, 225))
    assert abs(x - .5) < .01 and abs(y - .5) < .01
    x, y = video.picture_position(QPointF(rect.left() + 1, rect.top() + 1))
    assert x < .01 and y < .01
    assert video.picture_position(QPointF(rect.left() - 5, 225)) is None
    video.deleteLater()


def test_clicks_emit_only_in_pick_mode_with_a_live_picture(qapp):
    from PySide6.QtTest import QTest
    video = desktop.VideoView()
    video.resize(800, 450); video.set_frame(jpeg())
    picks = []
    video.picked.connect(lambda x, y: picks.append((round(x, 2), round(y, 2))))
    QTest.mouseClick(video, Qt.MouseButton.LeftButton, pos=QPointF(400, 225).toPoint())
    video.pick_enabled = True
    QTest.mouseClick(video, Qt.MouseButton.LeftButton, pos=QPointF(400, 225).toPoint())
    video.show_signal = True
    QTest.mouseClick(video, Qt.MouseButton.LeftButton, pos=QPointF(10, 225).toPoint())   # letterbox
    QTest.mouseClick(video, Qt.MouseButton.LeftButton, pos=QPointF(400, 225).toPoint())
    assert picks == [(.5, .5)]
    video.deleteLater()


def test_pick_button_is_enabled_only_for_an_authorised_live_source(qapp, window):
    assert not window.pick_button.isEnabled()
    window.update_state(camera_state())
    assert window.pick_button.isEnabled()
    window.pick_button.setChecked(True)
    assert window.video.pick_enabled
    window.authorized = False
    window.update_access()
    assert not window.pick_button.isEnabled() and not window.pick_button.isChecked() and not window.video.pick_enabled


def test_pick_sends_an_apply_request_and_reports_warnings(qapp, window):
    window.update_state(camera_state())
    window.pick_button.setChecked(True)
    window.video.picked.emit(.25, .75)
    assert not window.pick_button.isChecked()
    assert window.api.commands[-1] == ('/api/operator/pick', {'x': .25, 'y': .75, 'apply': True})
    window.pick_done({'settings': {'hue_low': 50, 'hue_high': 70, 'saturation_min': 90, 'value_min': 60},
                      'warnings': ['Red hues wrap around 0/179 and cannot be tracked with one range; use a green, blue or yellow target.']})
    last = window.events.topLevelItem(window.events.topLevelItemCount() - 1)
    assert last.text(1) == 'Colour' and 'Hue 50–70' in last.text(2) and 'wrap' in last.text(2)
    assert 'wrap' in window.statusBar().currentMessage()
    count = window.events.topLevelItemCount()
    for bad in (None, {}, {'settings': 'x'}):
        window.pick_done(bad)
    assert window.events.topLevelItemCount() == count


def test_unauthorised_pick_is_refused_locally(qapp, window):
    window.authorized = False
    window.api.commands.clear()
    window.pick_at(.5, .5)
    assert window.api.commands == [] and 'Operator access' in window.statusBar().currentMessage()


# ---------------------------------------------------------------- fallback view
def test_fallback_view_hides_everything_but_the_video(qapp, window):
    window.show(); qapp.processEvents()
    window.fallback_action.trigger()
    qapp.processEvents()
    assert window.fallback_action.isChecked()
    assert not any(d.isVisible() for d in (window.source_dock, window.inspect_dock, window.events_dock))
    assert not window.plot_wrap.isVisible() and window.video.isVisible()
    assert not any(t.isVisible() for t in window.findChildren(QToolBar))
    window.set_fallback_view(False)
    qapp.processEvents()
    assert not window.fallback_action.isChecked() and window.source_dock.isVisible() and window.plot_wrap.isVisible()


# ---------------------------------------------------------------- heartbeats
@pytest.fixture
def client(qapp):
    client = desktop.ApiClient(None)
    client.url, client.token = 'http://127.0.0.1:1', 'test-token'
    client.network = Network()
    yield client
    client.timer.stop(); client.deleteLater(); qapp.processEvents()


def paths(client):
    return [request.url().path() for request, _, _ in client.network.calls]


def test_heartbeat_only_with_a_lease_and_a_token(client):
    client.poll()
    assert desktop.HEARTBEAT not in paths(client)
    client.lease = True
    client.poll()
    assert paths(client).count(desktop.HEARTBEAT) == 1
    request, body, _ = client.network.calls[-1]
    assert json.loads(body) == {} and bytes(request.rawHeader('Authorization')) == b'Bearer test-token'
    client.token = ''
    client.last_heartbeat = 0
    client.poll()
    assert paths(client).count(desktop.HEARTBEAT) == 1


def test_heartbeats_are_rate_limited_and_silent(client):
    completed = []
    client.completed.connect(completed.append)
    client.lease = True
    client.poll()
    for _ in range(5): client.poll()
    assert paths(client).count(desktop.HEARTBEAT) == 1
    reply = next(reply for request, _, reply in client.network.calls if request.url().path() == desktop.HEARTBEAT)
    reply.body = b'{"leased": true, "lease_ms": 1500}'; reply.finished.emit()
    assert completed == []
    client.last_heartbeat -= desktop.HEARTBEAT_S
    client.poll()
    assert paths(client).count(desktop.HEARTBEAT) == 2


def test_workstation_lease_follows_authorisation(window):
    assert window.api.lease is True
    window.authorized = False
    window.update_access()
    assert window.api.lease is False


# ---------------------------------------------------------------- audit #1 / #6: live picture and stale video
def test_live_camera_picture_is_shown_and_synthetic_is_not(qapp, window):
    window.update_state(camera_state())
    assert window.video.show_signal is True and not window.video.stale
    window.update_state(state(steering_status=STEERING_UNAVAILABLE))
    assert window.video.show_signal is False and window.video.pixmap.isNull()


@pytest.mark.parametrize('age', [None, 250, 900])
def test_stale_camera_video_is_marked_even_while_the_server_answers(qapp, window, age):
    window.update_state(camera_state(frame_age_ms=age))
    assert window.video.stale and window.video.notice == 'Video stale · no fresh frames'
    assert window.video.error is None and window.video.target_text == ''
    window.check_freshness()                        # fresh server connection must not clear it
    assert window.video.stale
    window.update_state(camera_state(frame_age_ms=40))
    assert not window.video.stale and window.video.error == .5


def test_trace_window_uses_the_trace_label(qapp):
    from ball_demo.fixtures import trace
    value = trace('centered', 5)
    value['label'] = 'REPLAY / CAMERA session / no bridge output'
    dialog = desktop.TraceWindow(value, None)
    labels = [w.text() for w in dialog.findChildren(desktop.QLabel)]
    assert any(text.startswith('REPLAY / CAMERA session') for text in labels)
    dialog.timer.stop(); dialog.deleteLater()
