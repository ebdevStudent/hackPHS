"""Native operator workstation. No HTML/WebView; the HTTP server remains for visitors."""
import argparse
import json
import sys
import time
import shutil
import os
import tempfile
import multiprocessing
import math
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QTimer, QUrl, Signal, QStandardPaths, QRect, QRectF, QPointF, QEvent, QEventLoop, QLibraryInfo, QFileInfo, QCoreApplication
from PySide6.QtGui import QAction, QColor, QDesktopServices, QPainter, QPen, QPixmap, QFontDatabase, QGuiApplication, QIcon, QPalette
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QDockWidget, QFormLayout, QDialog, QDialogButtonBox, QLineEdit,
    QFileDialog, QMessageBox, QDoubleSpinBox, QSpinBox, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QSplitter, QSlider, QGroupBox, QToolBar, QStyle, QSizePolicy, QFrame,
)

from .sources import SCENARIOS


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_detection(value):
    if value is None: return
    if not isinstance(value, dict): raise ValueError('Invalid detection')
    for key in ('x', 'y', 'area', 'error', 'quality'):
        if key in value and not finite_number(value[key]): raise ValueError('Invalid detection measurement')
    if 'error' in value and not -1 <= value['error'] <= 1: raise ValueError('Invalid detection error')
    if 'quality' in value and not 0 <= value['quality'] <= 1: raise ValueError('Invalid detection quality')
    if 'area' in value and value['area'] < 0: raise ValueError('Invalid detection area')
    if 'bbox' in value:
        box = value['bbox']
        if (not isinstance(box, (list, tuple)) or len(box) != 4 or not all(finite_number(n) for n in box)
            or min(box[2:]) <= 0): raise ValueError('Invalid detection bounds')


def validate_snapshot(value):
    required = {'state', 'enabled', 'yaw', 'ack_yaw', 'source', 'source_label',
                'settings', 'session', 'bridge', 'bridge_fault', 'fault', 'detection',
                'frame_age_ms', 'ack_age_ms', 'processing_ms', 'frames'}
    if not isinstance(value, dict) or not required.issubset(value):
        raise ValueError('Incomplete state snapshot')
    if value['state'] not in ('MANUAL', 'SEARCHING', 'LOCKED', 'FAULT') or type(value['enabled']) is not bool:
        raise ValueError('Invalid controller state')
    for key in ('yaw', 'ack_yaw'):
        if type(value[key]) is not int or abs(value[key]) > 1000: raise ValueError('Invalid yaw')
    if not isinstance(value['settings'], dict) or not isinstance(value['source'], dict):
        raise ValueError('Invalid source/settings')
    if value['source'].get('kind') not in ('synthetic', 'recorded', 'camera'):
        raise ValueError('Unknown source kind')
    if any(not finite_number(number) for number in value['settings'].values()):
        raise ValueError('Invalid settings measurement')
    if 'scenario' in value['source'] and not isinstance(value['source']['scenario'], str):
        raise ValueError('Invalid source scenario')
    if type(value['frames']) is not int or value['frames'] < 0: raise ValueError('Invalid frame count')
    if value['fault'] is not None and not isinstance(value['fault'], str): raise ValueError('Invalid fault label')
    if ((value['state'] in ('MANUAL', 'FAULT') and value['enabled']) or
        (value['state'] in ('SEARCHING', 'LOCKED') and not value['enabled']) or
        (value['state'] != 'LOCKED' and value['yaw'] != 0)):
        raise ValueError('Inconsistent controller state')
    validate_detection(value['detection'])
    for key in ('frame_age_ms', 'ack_age_ms', 'processing_ms'):
        number = value[key]
        if number is not None and (type(number) not in (int, float) or not math.isfinite(number) or number < 0):
            raise ValueError('Invalid timing measurement')
    for key in ('source_label', 'session', 'bridge', 'bridge_fault'):
        if not isinstance(value[key], str): raise ValueError('Invalid state label')
    if value.get('navigation') is not None:
        from .navigation import NavigationState
        NavigationState.model_validate(value['navigation'])
        if value['navigation'].get('mission') is not None:
            from .mission import MissionState
            MissionState.model_validate(value['navigation']['mission'])


def validate_trace(value):
    if not isinstance(value, dict) or not isinstance(value.get('samples'), list) or not 1 <= len(value['samples']) <= 100000:
        raise ValueError('Expected a nonempty fixture sample list')
    settings = value.get('settings', {})
    if not isinstance(settings, dict): raise ValueError('Invalid trace settings')
    width, height, hz = settings.get('width', 640), settings.get('height', 480), settings.get('processing_hz', 20)
    if type(width) is not int or type(height) is not int or min(width, height) < 1 or max(width, height) > 4096 or width * height > 4000000:
        raise ValueError('Invalid trace dimensions')
    if type(hz) not in (int, float) or not math.isfinite(hz) or not 0 < hz <= 240:
        raise ValueError('Invalid trace processing rate')
    def finite(number): return type(number) in (int, float) and math.isfinite(number)
    previous = -1
    for sample in value['samples']:
        if not isinstance(sample, dict) or not finite(sample.get('t')) or sample['t'] < 0 or sample['t'] < previous:
            raise ValueError('Invalid or unordered trace timestamp')
        previous = sample['t']
        if sample.get('state') not in ('MANUAL', 'SEARCHING', 'LOCKED', 'FAULT') or type(sample.get('yaw')) is not int or abs(sample['yaw']) > 1000:
            raise ValueError('Invalid trace state/yaw')
        if sample['state'] != 'LOCKED' and sample['yaw'] != 0: raise ValueError('Inconsistent trace state/yaw')
        truth, detection = sample.get('truth', {}), sample.get('detection')
        if not isinstance(truth, dict) or (detection is not None and not isinstance(detection, dict)):
            raise ValueError('Invalid trace geometry')
        if 'visible' in truth and type(truth['visible']) is not bool: raise ValueError('Invalid target visibility')
        if truth.get('visible') and not all(finite(truth.get(key)) for key in ('x', 'y', 'radius')):
            raise ValueError('Invalid visible target')
        if truth.get('visible') and truth['radius'] <= 0: raise ValueError('Invalid target radius')
        validate_detection(detection)


HEARTBEAT = '/api/operator/heartbeat'
HEARTBEAT_S = .3


class ApiClient(QWidget):
    state = Signal(dict)
    image = Signal(bytes)
    failed = Signal(str)
    completed = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        self.url, self.token = '', ''
        self.pending = set()
        self.queued = {}
        self.generation = 0
        self.last_ok = 0.
        # Operator lease: while true, renew the server's assistance lease on every poll cycle.
        self.lease = False
        self.last_heartbeat = 0.
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)

    def connect_to(self, url, token):
        self.generation += 1
        self.url, self.token = url.rstrip('/'), token
        self.pending.clear()
        self.queued.clear()
        self.last_ok = 0.
        self.timer.start()
        self.poll()

    def request(self, path, payload=None, callback=None, binary=False):
        if not self.url:
            return
        if path in self.pending:
            if payload is not None:
                previous = self.queued.get(path)
                if previous and ((path.endswith('/assist') and previous[0].get('enabled') is False and payload.get('enabled') is True) or
                                 (path.endswith('/navigation') and previous[0].get('action') == 'disable' and payload.get('action') == 'resume')):
                    self.failed.emit('Enable cancelled: a neutral request is pending')
                    if callback: callback(None)
                else:
                    self.queued[path] = (payload, callback, binary)
            return
        generation = self.generation
        self.pending.add(path)
        request = QNetworkRequest(QUrl(self.url + path))
        request.setTransferTimeout(1800)
        # Never forward operator credentials to redirects.
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        if self.token and '/operator/' in path:
            request.setRawHeader(b'Authorization', ('Bearer ' + self.token).encode())
        if payload is None:
            reply = self.network.get(request)
        else:
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
            reply = self.network.post(request, json.dumps(payload).encode())

        def finished():
            if generation != self.generation:
                reply.deleteLater()
                return
            self.pending.discard(path)
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            body = bytes(reply.readAll())
            error = reply.error()
            if error != QNetworkReply.NetworkError.NoError or not status or not 200 <= status < 300:
                try:
                    detail = json.loads(body).get('detail', reply.errorString())
                except (ValueError, AttributeError):
                    detail = reply.errorString()
                if path != '/api/preview.jpg':
                    self.failed.emit(str(detail))
                if callback:
                    callback(None)
            else:
                try:
                    result = body if binary else (json.loads(body) if body else {})
                    if path == '/api/state':
                        validate_snapshot(result)
                        self.last_ok = time.monotonic()
                        self.state.emit(result)
                    elif path == '/api/preview.jpg' and body:
                        self.image.emit(body)
                    if payload is not None:
                        if isinstance(result, dict) and 'state' in result: validate_snapshot(result)
                        if path != HEARTBEAT: self.completed.emit(path.rsplit('/', 1)[-1])
                        if isinstance(result, dict) and 'state' in result:
                            self.state.emit(result)
                    if callback:
                        callback(result)
                except (ValueError, TypeError) as exc:
                    self.failed.emit('Invalid server response: ' + str(exc))
                    if callback:
                        callback(None)
            queued = self.queued.pop(path, None) if generation == self.generation else None
            if queued: self.request(path, queued[0], queued[1], queued[2])
            reply.deleteLater()
        reply.finished.connect(finished)

    def poll(self):
        self.request('/api/state')
        self.request('/api/preview.jpg', binary=True)
        now = time.monotonic()
        if self.lease and self.token and now - self.last_heartbeat >= HEARTBEAT_S:
            self.last_heartbeat = now
            self.request(HEARTBEAT, {})

    def command(self, action, values):
        self.request('/api/operator/' + action, values)


def fit_frame(frame, available):
    """Shrink and shift a window frame until it lies inside the visible screen."""
    if available.width() < 1 or available.height() < 1:
        return QRect(frame)
    width = min(frame.width(), available.width())
    height = min(frame.height(), available.height())
    x = min(max(frame.x(), available.x()), available.right() - width + 1)
    y = min(max(frame.y(), available.y()), available.bottom() - height + 1)
    return QRect(x, y, width, height)


def real_operator_source(state):
    """Recorded video and a camera are samples. The default synthetic scene is not."""
    source = state.get('source') if isinstance(state, dict) else None
    return isinstance(source, dict) and source.get('kind') in ('recorded', 'camera')


def session_caption(session):
    if isinstance(session, str) and len(session) >= 15 and session[8] == 'T':
        return f'{session[9:11]}:{session[11:13]}:{session[13:15]} UTC'
    return session or ''


SOURCE_RAIL_STYLE = """
QWidget#sourceRail { background: #16191c; }
QComboBox, QLineEdit, QSpinBox {
    background: #23282c; color: #d7dee3; border: 1px solid #3a4248;
    border-radius: 2px; padding: 4px 8px; min-height: 22px;
}
QComboBox::drop-down { border: none; width: 16px; }
QPushButton#primaryAction {
    background: #2c6b3a; color: #f3f7f4; border: none; border-radius: 2px;
    padding: 7px 8px; text-align: left;
}
QPushButton#primaryAction:disabled { background: #243028; color: #7f8c86; }
QPushButton#secondaryAction {
    background: transparent; color: #d7dee3; border: 1px solid #4a545c;
    border-radius: 2px; padding: 6px 8px; text-align: left;
}
QPushButton#secondaryAction:disabled { color: #6d767c; border-color: #2e363c; }
QPushButton#disclosure {
    background: transparent; color: #8e989f; border: none;
    padding: 2px 0; text-align: left;
}
QPushButton#disclosure:disabled { color: #5c656b; }
"""


def tinted(text, color):
    label = QLabel(text)
    palette = label.palette()
    palette.setColor(QPalette.ColorRole.WindowText, QColor(color))
    label.setPalette(palette)
    return label


class VideoView(QWidget):
    """Operator preview. A 16:9 plate, letterboxed, with no synthetic picture.

    Manual-fallback overlays: the steering status banner, and for a live source the
    horizontal centre/error indicator under the server-drawn target box."""

    message = 'No signal'
    picked = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap()
        self.caption = ''
        self.notice = ''
        self.stale = False
        self.show_signal = False
        self.steering_text = ''
        self.error = None
        self.target_text = ''
        self.pick_enabled = False
        self.setMinimumSize(320, 180)

    def preview_rect(self):
        area = QRectF(self.rect())
        if area.width() < 1 or area.height() < 1:
            return area
        ratio = 16 / 9
        if area.width() / area.height() > ratio:
            height = area.height()
            width = height * ratio
        else:
            width = area.width()
            height = width / ratio
        return QRectF((area.width() - width) / 2, (area.height() - height) / 2, width, height)

    def image_rect(self):
        """Where the current pixmap is drawn inside the 16:9 plate."""
        frame = self.preview_rect()
        if self.pixmap.isNull():
            return QRectF()
        scaled = self.pixmap.size().scaled(frame.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
        return QRectF(frame.x() + (frame.width() - scaled.width()) / 2,
                      frame.y() + (frame.height() - scaled.height()) / 2,
                      scaled.width(), scaled.height())

    def picture_position(self, point):
        """Normalised (x, y) of a widget point on the picture, or None outside it."""
        rect = self.image_rect()
        if rect.width() < 1 or rect.height() < 1 or not rect.contains(point):
            return None
        return ((point.x() - rect.x()) / rect.width(), (point.y() - rect.y()) / rect.height())

    def mousePressEvent(self, event):
        position = self.picture_position(event.position()) if self.pick_enabled and self.show_signal else None
        if position is not None:
            self.picked.emit(*position)
        super().mousePressEvent(event)

    def paint_fallback(self, painter, frame):
        if self.steering_text:
            band = QRectF(frame.x(), frame.y(), frame.width(), 34)
            painter.fillRect(band, QColor(15, 18, 20, 205))
            painter.setPen(QColor('#ffd166'))
            font = painter.font()
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(band, Qt.AlignmentFlag.AlignCenter, self.steering_text)
        if not self.show_signal:
            return
        rect = self.image_rect()
        track_y = rect.bottom() - 26
        left, right = rect.left() + 40, rect.right() - 40
        if right - left < 40:
            return
        painter.fillRect(QRectF(left, track_y - 3, right - left, 6), QColor(15, 18, 20, 190))
        middle = (left + right) / 2
        painter.setPen(QPen(QColor('#ffffff'), 2))
        painter.drawLine(QPointF(middle, track_y - 11), QPointF(middle, track_y + 11))
        font = painter.font()
        font.setPointSize(12)
        font.setBold(False)
        painter.setFont(font)
        if self.error is not None:
            x = middle + max(-1., min(1., self.error)) * (right - left) / 2
            painter.setBrush(QColor('#69dc32'))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, track_y), 8, 8)
            label = f'Centre error {self.error:+.3f}'
        else:
            label = 'Centre error —'
        painter.setPen(QColor('#e8eef1'))
        painter.drawText(QRectF(left, track_y - 30, right - left, 18), Qt.AlignmentFlag.AlignLeft, label)
        painter.drawText(QRectF(left, track_y - 30, right - left, 18), Qt.AlignmentFlag.AlignRight, self.target_text)

    def set_frame(self, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.pixmap = pixmap
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#121417'))
        frame = self.preview_rect()
        painter.fillRect(frame, QColor('#191d20'))
        if self.show_signal and not self.pixmap.isNull():
            scaled = self.pixmap.size().scaled(frame.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
            rect = QRectF(frame.x() + (frame.width() - scaled.width()) / 2,
                          frame.y() + (frame.height() - scaled.height()) / 2,
                          scaled.width(), scaled.height())
            painter.drawPixmap(rect, self.pixmap, QRectF(self.pixmap.rect()))
            if self.caption and not self.notice:
                painter.setPen(QColor('#d5dde0'))
                painter.drawText(int(frame.left()) + 16, int(frame.bottom()) - 12, self.caption)
            if self.stale:
                painter.fillRect(frame, QColor(15, 18, 20, 175))
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(frame, Qt.AlignmentFlag.AlignCenter,
                                 self.notice or 'Connection lost · preview is stale')
            elif self.notice:
                painter.setPen(QColor('#d5dde0'))
                painter.drawText(frame, Qt.AlignmentFlag.AlignCenter, self.notice)
            if not self.stale:
                self.paint_fallback(painter, frame)
            return
        painter.setPen(QColor('#c5ced4'))
        font = painter.font()
        font.setPointSize(15)
        painter.setFont(font)
        painter.drawText(frame, Qt.AlignmentFlag.AlignCenter, self.message)
        self.paint_fallback(painter, frame)


class CommandPlot(QWidget):
    """Small oscilloscope-style plot of requested and accepted software yaw."""
    def __init__(self):
        super().__init__()
        self.samples = deque(maxlen=300)
        self.setMinimumHeight(115)

    def append(self, state):
        self.samples.append((state.get('yaw', 0), state.get('ack_yaw', 0)))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#191d20'))
        left, right, top, bottom = 56, self.width() - 12, 10, self.height() - 18
        requested, accepted = QColor('#69dc32'), QColor('#9ecbff')
        for value in (-1000, 0, 1000):
            y = top + (1000 - value) / 2000 * (bottom - top)
            p.setPen(QColor('#5c6770') if value == 0 else QColor('#2e363c'))
            p.drawLine(QPointF(left, y), QPointF(right, y))
            p.setPen(QColor('#b7c2c8'))
            p.drawText(QRectF(0, y - 8, left - 8, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(value))
        for column, color in ((1, accepted), (0, requested)):
            p.setPen(QPen(color, 1.6))
            points = [QPointF(left + i / 299 * (right - left),
                             top + (1000 - sample[column]) / 2000 * (bottom - top))
                      for i, sample in enumerate(self.samples)]
            for a, b in zip(points, points[1:]):
                p.drawLine(a, b)
        p.setPen(QColor('#b7c2c8'))
        p.drawText(left, self.height() - 4, '30 s history · software commands only')


class SettingsDialog(QDialog):
    def __init__(self, settings, parent):
        super().__init__(parent)
        self.setWindowTitle('Detector and controller settings')
        self.fields = {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Applying settings disables assistance. Values are provisional demo settings.'))
        tabs = QTabWidget()
        layout.addWidget(tabs)
        definitions = {
            'Controller': [('gain', 'Proportional gain', 0, 2000, 1),
                           ('smoothing', 'Smoothing', .001, 1, .01),
                           ('deadband', 'Deadband', 0, .5, .01),
                           ('max_yaw', 'Maximum yaw', 0, 1000, 10),
                           ('slew_per_s', 'Slew / second', 1, 10000, 100)],
            'Detector': [('hue_low', 'Hue minimum', 0, 179, 1), ('hue_high', 'Hue maximum', 0, 179, 1),
                         ('saturation_min', 'Minimum saturation', 0, 255, 1),
                         ('value_min', 'Minimum value', 0, 255, 1),
                         ('min_area', 'Minimum blob area (px²)', 1, 50000, 10),
                         ('max_area', 'Maximum blob area (px²)', 1, 307200, 100)],
        }
        for name, entries in definitions.items():
            page, form = QWidget(), QFormLayout()
            page.setLayout(form)
            tabs.addTab(page, name)
            for key, label, low, high, step in entries:
                value = settings.get(key, low)
                field = QSpinBox() if key in ('max_yaw', 'hue_low', 'hue_high', 'saturation_min', 'value_min', 'min_area', 'max_area') else QDoubleSpinBox()
                if isinstance(field, QDoubleSpinBox):
                    field.setDecimals(3)
                field.setRange(low, high)
                field.setSingleStep(step)
                field.setValue(value)
                self.fields[key] = field
                form.addRow(label, field)
        direction = QComboBox()
        direction.addItem('Positive (+1)', 1)
        direction.addItem('Reversed (−1)', -1)
        direction.setCurrentIndex(0 if settings.get('direction', 1) == 1 else 1)
        self.fields['direction'] = direction
        tabs.widget(0).layout().addRow('Direction', direction)
        self.error = QLabel()
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {key: field.currentData() if isinstance(field, QComboBox) else field.value()
                for key, field in self.fields.items()}

    def apply(self):
        values = self.values()
        if values['hue_low'] > values['hue_high'] or values['min_area'] > values['max_area']:
            self.error.setText('Minimum thresholds must not exceed maximum thresholds.')
        else:
            self.accept()


class TraceWindow(QDialog):
    """Read-only replay of a fixture trace, without a live client or bridge reference."""
    def __init__(self, trace, parent):
        validate_trace(trace)
        super().__init__(parent)
        self.setWindowTitle('Isolated playback — ' + trace.get('scenario', 'trace'))
        self.resize(800, 660)
        self.samples = trace['samples']
        self.settings = trace.get('settings', {})
        self.index = 0
        layout = QVBoxLayout(self)
        title = trace.get('label') if isinstance(trace.get('label'), str) else 'OFFLINE TRACE'
        label = QLabel(f'{title} · Independent playback; no bridge commands')
        layout.addWidget(label)
        self.video = VideoView()
        self.video.show_signal = True
        layout.addWidget(self.video, 1)
        self.readout = QLabel()
        layout.addWidget(self.readout)
        row = QHBoxLayout()
        self.play = QPushButton('Play')
        self.play.clicked.connect(self.toggle)
        row.addWidget(self.play)
        reset = QPushButton('Reset')
        reset.clicked.connect(lambda: self.slider.setValue(0))
        row.addWidget(reset)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, len(self.samples) - 1)
        self.slider.valueChanged.connect(self.render)
        row.addWidget(self.slider, 1)
        layout.addLayout(row)
        self.timer = QTimer(self)
        self.timer.setInterval(round(1000 / self.settings.get('processing_hz', 20)))
        self.timer.timeout.connect(self.advance)
        self.render(0)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def reject(self):
        self.timer.stop()
        super().reject()

    def toggle(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play.setText('Play')
        else:
            if self.index == len(self.samples) - 1:
                self.slider.setValue(0)
            self.timer.start()
            self.play.setText('Pause')

    def advance(self):
        if self.index >= len(self.samples) - 1:
            self.toggle()
        else:
            self.slider.setValue(self.index + 1)

    def render(self, index):
        self.index = index
        sample = self.samples[index]
        truth = sample.get('truth', {})
        w, h = self.settings.get('width', 640), self.settings.get('height', 480)
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor('#191d20'))
        p = QPainter(pixmap)
        p.setPen(QColor('#353b40'))
        for x in range(0, w, 40): p.drawLine(x, 0, x, h)
        for y in range(0, h, 40): p.drawLine(0, y, w, y)
        p.setPen(QColor('#8b9298'))
        p.drawLine(w // 2, 0, w // 2, h)
        if truth.get('visible'):
            p.setBrush(QColor('#69dc32'))
            p.setPen(Qt.PenStyle.NoPen)
            r = truth.get('radius', 25)
            p.drawEllipse(QPointF(truth['x'], truth['y']), r, r)
        detection = sample.get('detection')
        if detection and 'bbox' in detection:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor('#b8f5cf'), 2))
            p.drawRect(QRectF(*detection['bbox']))
        p.end()
        self.video.pixmap = pixmap
        self.video.caption = 'Ground truth reconstruction · visual effects are not replayed'
        self.video.update()
        self.readout.setText(f"{sample['t']:.2f} s    {sample['state']}    Requested yaw: {sample['yaw']}    Frame {index + 1}/{len(self.samples)}")


class StatusLine(QLabel):
    """Session address kept visible beside the macOS status-bar resize grip."""

    def __init__(self):
        super().__init__()
        self.full = ''
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

    def set_status(self, text):
        self.full = text
        self.setToolTip(text)
        self.setText(text)
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(text) + 12)


class Workstation(QMainWindow):
    def __init__(self, backend=None, url='', token=''):
        super().__init__()
        self.backend = backend
        self.snapshot = {}
        self.authorized = False
        self.last_event = None
        self.trace_windows = []
        self.setWindowTitle('Ball Drone — Operator Workstation')
        self.resize(1220, 800)
        self.setMinimumSize(1040, 680)
        self._containing = False
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AllowNestedDocks)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.api = ApiClient(self)
        self.api.state.connect(self.update_state)
        self.api.failed.connect(self.failure)
        self.api.completed.connect(lambda action: self.statusBar().showMessage(action.capitalize() + ' accepted', 3500))
        self.build_workspace()
        self.build_menus()
        self.api.image.connect(self.video.set_frame)
        self.video.picked.connect(self.pick_at)
        self.api.connect_to(backend.url if backend else url, backend.token if backend else token)
        self.authorized = bool(backend)
        if not backend and token:
            self.api.request('/api/operator/access', callback=self.access_checked)
        self.freshness = QTimer(self)
        self.freshness.setInterval(200)
        self.freshness.timeout.connect(self.check_freshness)
        self.freshness.start()
        self.update_access()

    def dock(self, title, widget, area):
        dock = QDockWidget(self)
        dock.setObjectName(title)
        dock.setWindowTitle(title)
        # Float turns the panel into its own window, with a zoom button that grows it past the frame.
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setAllowedAreas(area)
        dock.setTitleBarWidget(self.section_bar(title))
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def rail_label(self, text):
        label = tinted(text, '#9aa3a9')
        font = label.font()
        font.setPointSize(11)
        label.setFont(font)
        return label

    def rail_rule(self):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet('background: #2a3136; border: none; max-height: 1px;')
        return line

    def section_bar(self, title):
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 8, 12, 2)
        label = tinted(title, '#9aa3a9')
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        row.addWidget(label)
        return bar

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.contain_on_screen)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            QTimer.singleShot(0, self.contain_on_screen)

    def contain_on_screen(self):
        if self._containing or not self.isVisible():
            return
        # The green button enters full screen. Leave that state, then fill the visible screen
        # once the title-bar margins belong to a normal window again.
        if self.windowState() & (Qt.WindowState.WindowFullScreen | Qt.WindowState.WindowMaximized):
            self._containing = True
            try:
                self.setWindowState(Qt.WindowState.WindowNoState)
            finally:
                self._containing = False
            QTimer.singleShot(0, self.zoom_to_available)
            return
        self.pull_inside()

    def _screen_available(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return None
        available = screen.availableGeometry()
        if available.width() < 640 or available.height() < 480:
            return None
        return available

    def _place_frame(self, target):
        frame = self.frameGeometry()
        client = self.geometry()
        extra_w = max(0, frame.width() - client.width())
        extra_h = max(0, frame.height() - client.height())
        self.setMaximumSize(max(640, target.width() - extra_w), max(480, target.height() - extra_h))
        self.setGeometry(target.x() - (frame.x() - client.x()), target.y() - (frame.y() - client.y()),
                         target.width() - extra_w, target.height() - extra_h)

    def zoom_to_available(self):
        if self._containing or not self.isVisible():
            return
        if self.windowState() & (Qt.WindowState.WindowFullScreen | Qt.WindowState.WindowMaximized):
            QTimer.singleShot(50, self.zoom_to_available)
            return
        available = self._screen_available()
        if available is None:
            return
        self._containing = True
        try:
            self.setMaximumSize(16777215, 16777215)
            self._place_frame(available)
            frame = self.frameGeometry()
            shift_x = available.x() - frame.x()
            shift_y = available.y() - frame.y()
            grow_w = available.width() - frame.width()
            grow_h = available.height() - frame.height()
            if max(abs(shift_x), abs(shift_y), abs(grow_w), abs(grow_h)) > 2:
                self.move(self.x() + shift_x, self.y() + shift_y)
                self.resize(max(1, self.width() + grow_w), max(1, self.height() + grow_h))
            self.setMaximumSize(self.width(), self.height())
        finally:
            self._containing = False

    def pull_inside(self):
        available = self._screen_available()
        if available is None:
            return
        frame = self.frameGeometry()
        fitted = fit_frame(frame, available)
        if fitted == frame:
            return
        self._containing = True
        try:
            self._place_frame(fitted)
        finally:
            self._containing = False

    def build_workspace(self):
        self.video = VideoView()
        self.plot = CommandPlot()
        plot_wrap = QWidget()
        plot_layout = QVBoxLayout(plot_wrap)
        plot_layout.setContentsMargins(12, 4, 12, 0)
        plot_layout.setSpacing(0)
        legend = QHBoxLayout()
        legend.addWidget(tinted('Yaw command', '#b7c2c8'))
        legend.addStretch()
        legend.addWidget(tinted('Requested', '#69dc32'))
        legend.addSpacing(16)
        legend.addWidget(tinted('Accepted (ACK)', '#9ecbff'))
        plot_layout.addLayout(legend)
        plot_layout.addWidget(self.plot)
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.video)
        split.addWidget(plot_wrap)
        split.setSizes([510, 160])
        split.setChildrenCollapsible(False)
        self.plot_wrap = plot_wrap
        self.setCentralWidget(split)
        source_widget = QWidget()
        source_widget.setObjectName('sourceRail')
        source_widget.setStyleSheet(SOURCE_RAIL_STYLE)
        source_layout = QVBoxLayout(source_widget)
        source_layout.setContentsMargins(8, 8, 8, 8)
        source_layout.setSpacing(8)
        source_layout.addWidget(self.rail_label('Source'))
        self.source_kind = QComboBox()
        self.source_kind.addItems(['Synthetic', 'Recorded video', 'Camera'])
        source_layout.addWidget(self.source_kind)
        self.scenario = QComboBox()
        for scenario in SCENARIOS:
            self.scenario.addItem(scenario.replace('_', ' ').title(), scenario)
        self.scenario.setCurrentText('Moving')
        source_layout.addWidget(self.scenario)
        self.path = QLineEdit()
        self.path.setPlaceholderText('Video path on processing device')
        source_layout.addWidget(self.path)
        self.browse = QPushButton('Choose video…')
        self.browse.setObjectName('disclosure')
        self.browse.clicked.connect(self.choose_video)
        source_layout.addWidget(self.browse)
        self.camera = QSpinBox()
        self.camera.setRange(0, 10)
        self.camera.setPrefix('Camera device ')
        source_layout.addWidget(self.camera)
        self.source_apply = QPushButton('Apply source')
        self.source_apply.setObjectName('secondaryAction')
        self.source_apply.clicked.connect(self.apply_source)
        source_layout.addWidget(self.source_apply)
        self.source_kind.currentIndexChanged.connect(self.source_visibility)
        self.source_visibility()
        source_layout.addWidget(self.rail_rule())
        source_layout.addWidget(self.rail_label('Assistance'))
        state_row = QHBoxLayout()
        state_row.setSpacing(8)
        state_row.addWidget(self.rail_label('State'))
        self.state_label = QLabel('MANUAL')
        state_font = self.state_label.font()
        state_font.setPointSize(13)
        self.state_label.setFont(state_font)
        state_row.addWidget(self.state_label)
        state_row.addStretch(1)
        source_layout.addLayout(state_row)
        self.enable = QPushButton('Enable yaw assistance')
        self.enable.setObjectName('primaryAction')
        self.enable.clicked.connect(lambda: self.api.command('assist', {'enabled': True}))
        source_layout.addWidget(self.enable)
        self.disable = QPushButton('Disable · neutral')
        self.disable.setObjectName('secondaryAction')
        self.disable.clicked.connect(lambda: self.api.command('assist', {'enabled': False}))
        source_layout.addWidget(self.disable)
        self.settings_button = QPushButton('Detector / controller…')
        self.settings_button.setObjectName('disclosure')
        self.settings_button.clicked.connect(self.settings_dialog)
        source_layout.addWidget(self.settings_button)
        self.pick_button = QPushButton('Pick target colour from video')
        self.pick_button.setObjectName('disclosure')
        self.pick_button.setCheckable(True)
        self.pick_button.toggled.connect(self.toggle_pick)
        source_layout.addWidget(self.pick_button)
        source_layout.addWidget(self.rail_rule())
        source_layout.addWidget(self.rail_label('Mock bridge'))
        self.fault_choice = QComboBox()
        for label, value in [('Normal', 'none'), ('Disconnect', 'disconnect'),
                             ('Missing ACK', 'missing_ack'), ('Delayed ACK', 'delayed_ack')]:
            self.fault_choice.addItem(label, value)
        source_layout.addWidget(self.fault_choice)
        self.fault_apply = QPushButton('Apply bridge condition')
        self.fault_apply.setObjectName('secondaryAction')
        self.fault_apply.clicked.connect(lambda: self.api.command('fault', {'fault': self.fault_choice.currentData()}))
        source_layout.addWidget(self.fault_apply)
        source_layout.addStretch(1)
        source_layout.addWidget(tinted('Manual until yaw assistance is enabled', '#6d767c'))
        self.source_dock = self.dock('Source & control', source_widget, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.source_dock.setMinimumWidth(248)
        inspect = QWidget()
        inspect_layout = QVBoxLayout(inspect)
        inspect_layout.setContentsMargins(12, 8, 12, 12)
        inspect_layout.setSpacing(6)
        self.readouts = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(5)
        grid.setColumnStretch(1, 1)
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        rows = [('yaw', 'Requested yaw'), ('ack_yaw', 'Accepted yaw'), ('error', 'Horizontal error'),
                ('quality', 'Tracking quality'), ('frame_age_ms', 'Frame age'),
                ('ack_age_ms', 'ACK age'), ('processing_ms', 'Processing'), ('bridge', 'Transport'),
                ('bridge_fault', 'Bridge condition'), ('frames', 'Processed frames')]
        for row, (key, label) in enumerate(rows):
            name = tinted(label, '#9aa3a9')
            value = QLabel('—')
            value.setFont(mono)
            value.setWordWrap(True)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.readouts[key] = value
            grid.addWidget(name, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(value, row, 1)
        inspect_layout.addLayout(grid)
        self.fault_label = QLabel('—')
        self.fault_label.setWordWrap(True)
        inspect_layout.addWidget(self.fault_label)
        inspect_layout.addStretch()
        self.inspect_dock = self.dock('Live measurements', inspect, Qt.DockWidgetArea.RightDockWidgetArea)
        self.inspect_dock.setMinimumWidth(300)
        self.events = QTreeWidget()
        self.events.setColumnCount(3)
        self.events.setHeaderLabels(['Time', 'Event', 'Details'])
        self.events.setRootIsDecorated(False)
        self.events.setIndentation(0)
        self.events.setFrameShape(QFrame.Shape.NoFrame)
        self.events.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.events.header().setStretchLastSection(True)
        self.events.header().setMinimumSectionSize(72)
        self.events.setColumnWidth(0, 96)
        self.events.setColumnWidth(1, 128)
        events_holder = QWidget()
        events_layout = QVBoxLayout(events_holder)
        events_layout.setContentsMargins(12, 4, 12, 8)
        events_layout.addWidget(self.events)
        self.events_dock = self.dock('Session events', events_holder, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.show_event_placeholder()
        self.events_dock.setMinimumHeight(132)
        self.events_dock.setMaximumHeight(210)
        toolbar = QToolBar('Session', self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        open_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), 'Open video', self)
        open_action.triggered.connect(self.choose_video)
        toolbar.addAction(open_action)
        toolbar.addSeparator()
        self.source_label = QLabel('')
        toolbar.addWidget(self.source_label)
        stretch = QWidget()
        stretch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(stretch)
        self.session_label = QLabel('Starting session')
        toolbar.addWidget(self.session_label)
        self.limit_label = tinted('Heuristic quality · no aircraft telemetry · no transmitter output', '#8e989f')
        navigation_holder = QWidget()
        navigation_layout = QVBoxLayout(navigation_holder)
        self.navigation_status = QLabel('Navigation not configured')
        self.navigation_status.setWordWrap(True)
        self.navigation_pose = QLabel('Estimated XYZ: —')
        self.navigation_waypoint = QLabel('Next waypoint: —')
        self.navigation_timing = QLabel('Pose age / uncertainty: —')
        self.navigation_mission = QLabel('Inspection mission: —')
        self.navigation_mission.setWordWrap(True)
        self.navigation_authority = QLabel('Advisory only. Pilot owns roll, pitch, throttle, ARM/DISARM and independent takeover. Physical computer authority: yaw only; trainer output unverified.')
        self.navigation_authority.setWordWrap(True)
        self.navigation_route = QTreeWidget()
        self.navigation_route.setHeaderLabels(['Waypoint', 'X · m', 'Y · m', 'Z · m', 'Yaw · °', 'Visible tags'])
        for widget in (self.navigation_status, self.navigation_pose, self.navigation_waypoint, self.navigation_timing, self.navigation_mission, self.navigation_authority, self.navigation_route): navigation_layout.addWidget(widget)
        actions = QHBoxLayout()
        self.navigation_goal = QPushButton('Set goal')
        self.navigation_resume = QPushButton('Restore guidance')
        self.navigation_disable = QPushButton('Stop guidance')
        self.navigation_mission_start = QPushButton('Start mission dry run')
        self.navigation_mission_advance = QPushButton('Advance target')
        self.navigation_mission_abort = QPushButton('Abort mission')
        self.navigation_goal.clicked.connect(self.choose_navigation_goal)
        self.navigation_resume.clicked.connect(lambda: self.api.command('navigation', {'action': 'resume'}))
        self.navigation_disable.clicked.connect(lambda: self.api.command('navigation', {'action': 'disable'}))
        self.navigation_mission_start.clicked.connect(lambda: self.api.command('navigation', {'action': 'mission_start'}))
        self.navigation_mission_advance.clicked.connect(lambda: self.api.command('navigation', {'action': 'mission_advance'}))
        self.navigation_mission_abort.clicked.connect(lambda: self.api.command('navigation', {'action': 'mission_abort'}))
        for button in (self.navigation_goal, self.navigation_resume, self.navigation_disable,
                       self.navigation_mission_start, self.navigation_mission_advance, self.navigation_mission_abort): actions.addWidget(button)
        navigation_layout.addLayout(actions)
        self.navigation_dock = self.dock('Mapped guidance · advisory', navigation_holder, Qt.DockWidgetArea.RightDockWidgetArea)
        self.navigation_dock.hide()
        self.statusBar().addWidget(self.limit_label, 1)
        self.connection_label = StatusLine()
        self.statusBar().addPermanentWidget(self.connection_label)
        # The macOS size grip is drawn over the right edge of the last permanent widget.
        grip_pad = QWidget()
        grip_pad.setFixedWidth(18)
        self.statusBar().addPermanentWidget(grip_pad)

    def build_menus(self):
        file_menu = self.menuBar().addMenu('&File')
        self.action(file_menu, 'Open recorded video…', self.choose_video, 'Ctrl+O')
        self.action(file_menu, 'Open fixture trace…', self.open_trace)
        self.action(file_menu, 'Open session folder', self.open_session_folder)
        file_menu.addSeparator()
        self.action(file_menu, 'Connect to Pi / server…', self.connect_dialog)
        self.action(file_menu, 'Open visitor page', lambda: QDesktopServices.openUrl(QUrl(self.api.url)))
        file_menu.addSeparator()
        self.action(file_menu, 'Close', self.close, 'Ctrl+W')
        view = self.menuBar().addMenu('&View')
        for dock in (self.source_dock, self.inspect_dock, self.events_dock, self.navigation_dock):
            view.addAction(dock.toggleViewAction())
        view.addSeparator()
        self.fallback_action = self.action(view, 'Manual fallback view', self.set_fallback_view, 'Ctrl+Shift+F')
        self.fallback_action.setCheckable(True)
        tools = self.menuBar().addMenu('&Tools')
        self.action(tools, 'Detector / controller settings…', self.settings_dialog, 'Ctrl+,')
        self.action(tools, 'Reset demonstration', lambda: self.api.command('reset', {}))
        self.action(tools, 'Play isolated scenario…', self.play_scenario)
        self.action(tools, 'Import navigation bundle…', self.import_navigation_bundle)
        self.action(tools, 'Import inspection mission…', self.import_navigation_mission)
        help_menu = self.menuBar().addMenu('&Help')
        self.action(help_menu, 'About Ball Drone', lambda: QMessageBox.about(
            self, 'Ball Drone', 'Native Qt operator workstation for Mac and Raspberry Pi.\n\n'
            'Synthetic/recorded tracking and bounded yaw demonstration. '
            'ACKs describe software state. No physical transmitter output.'))

    def action(self, menu, label, callback, shortcut=None):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def source_visibility(self):
        kind = self.source_kind.currentIndex()
        self.scenario.setVisible(kind == 0)
        self.path.setVisible(kind == 1)
        self.browse.setVisible(kind == 1)
        self.camera.setVisible(kind == 2)

    def choose_video(self):
        if not self.authorized:
            self.failure('Operator access is required to change the video source.')
            return
        if not self.backend:
            self.source_kind.setCurrentIndex(1)
            self.failure('Enter a video path that exists on the connected server, then Apply source.')
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Open recorded video', '', 'Video files (*.avi *.mp4 *.mov *.mkv);;All files (*)')
        if path:
            self.path.setText(path)
            self.source_kind.setCurrentIndex(1)
            self.apply_source()

    def choose_navigation_goal(self):
        if not self.authorized: return
        dialog = QDialog(self)
        dialog.setWindowTitle('Advisory goal · pilot retains control')
        layout = QVBoxLayout(dialog)
        entry = QLineEdit()
        entry.setPlaceholderText('X Y Z in map metres, e.g. 1.5 1.0 1.2')
        layout.addWidget(entry)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                values = [float(x) for x in entry.text().split()]
                if len(values) != 3 or not all(math.isfinite(x) for x in values): raise ValueError('Enter three finite coordinates in metres')
                self.api.command('navigation', {'action': 'goal', 'goal': values})
            except ValueError as error: self.failure(str(error))

    def import_navigation_bundle(self):
        if not self.authorized:
            self.failure('Operator access is required to import a navigation bundle.')
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Import navigation bundle', '', 'JSON files (*.json)')
        if not path: return
        try:
            from .map_io import load_bundle
            bundle = load_bundle(path)
            self.api.command('navigation/bundle', {'bundle': bundle.model_dump()})
        except (ValueError, OSError) as error: self.failure(str(error))

    def import_navigation_mission(self):
        if not self.authorized:
            self.failure('Operator access is required to import an inspection mission.')
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Import inspection mission', '', 'JSON files (*.json)')
        if not path: return
        try:
            raw = Path(path).read_bytes()
            if len(raw) > 1_000_000: raise ValueError('Mission file too large')
            mission = json.loads(raw)
            from .mission import Mission
            Mission.model_validate(mission)
            self.api.command('navigation/mission', {'mission': mission})
        except (ValueError, OSError) as error: self.failure(str(error))

    def apply_source(self):
        kind = ['synthetic', 'recorded', 'camera'][self.source_kind.currentIndex()]
        values = {'kind': kind}
        if kind == 'synthetic': values['scenario'] = self.scenario.currentData()
        elif kind == 'recorded': values['path'] = self.path.text()
        else: values['device'] = self.camera.value()
        self.api.command('source', values)

    def settings_dialog(self):
        if not self.authorized or not self.snapshot:
            self.failure('Connect with operator access before changing settings.')
            return
        dialog = SettingsDialog(self.snapshot['settings'], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.api.command('settings', dialog.values())

    def access_checked(self, result):
        self.authorized = isinstance(result, dict) and result.get('authorized') is True
        self.update_access()

    def update_access(self):
        fresh = bool(self.api.last_ok and time.monotonic() - self.api.last_ok < .5)
        self.api.lease = bool(self.authorized)
        self.pick_button.setEnabled(self.authorized and fresh and real_operator_source(self.snapshot))
        if not self.pick_button.isEnabled() and self.pick_button.isChecked():
            self.pick_button.setChecked(False)
        for control in (self.source_apply, self.settings_button, self.fault_apply):
            control.setEnabled(self.authorized and fresh)
        self.enable.setEnabled(self.authorized and fresh and not self.snapshot.get('enabled', False))
        self.disable.setEnabled(self.authorized)
        self.browse.setEnabled(self.authorized)

    def show_event_placeholder(self):
        self.events.clear()
        self.events.addTopLevelItem(QTreeWidgetItem(['', '', 'No events']))
        self.last_event = None

    def show_placeholders(self):
        for label in self.readouts.values():
            label.setText('—')
        self.fault_label.setText('—')
        self.source_label.setText('')
        if self.plot.samples:
            self.plot.samples.clear()
            self.plot.update()

    def set_fallback_view(self, on):
        """Presentation layout for the manual demo: the video well with its fallback overlays only."""
        for dock in (self.source_dock, self.inspect_dock, self.events_dock):
            dock.setVisible(not on)
        self.plot_wrap.setVisible(not on)
        for toolbar in self.findChildren(QToolBar):
            toolbar.setVisible(not on)
        if self.fallback_action.isChecked() != bool(on):
            self.fallback_action.setChecked(bool(on))

    def toggle_pick(self, on):
        self.video.pick_enabled = bool(on)
        self.video.setCursor(Qt.CursorShape.CrossCursor if on else Qt.CursorShape.ArrowCursor)
        if on:
            self.statusBar().showMessage('Click the coloured target in the video to set the detector colour range', 8000)

    def pick_at(self, x, y):
        self.pick_button.setChecked(False)
        if not self.authorized:
            self.failure('Operator access is required to change detector settings.')
            return
        self.api.request('/api/operator/pick', {'x': x, 'y': y, 'apply': True}, callback=self.pick_done)

    def pick_done(self, result):
        if not isinstance(result, dict) or not isinstance(result.get('settings'), dict):
            return
        values = result['settings']
        detail = (f"Hue {values.get('hue_low')}–{values.get('hue_high')}, saturation ≥ {values.get('saturation_min')}, "
                  f"value ≥ {values.get('value_min')}. Assistance disabled.")
        warnings = [w for w in result.get('warnings', []) if isinstance(w, str)]
        self.add_event('Colour', detail + (' ' + ' '.join(warnings) if warnings else ''))
        self.statusBar().showMessage(warnings[0] if warnings else 'Detector colour range updated from the picked target', 8000)

    def update_state(self, state):
        self.snapshot = state
        navigation = state.get('navigation')
        self.navigation_status.setText(navigation['status'] if navigation else 'Navigation not configured')
        if navigation:
            self.navigation_dock.show()
            self.navigation_authority.setText(navigation['authority_text'])
        pose = navigation.get('pose') if navigation else None
        prefix = {'synthetic_estimate': 'SYNTHETIC estimate', 'recorded_estimate': 'RECORDED estimate', 'vision_estimate': 'Vision estimate'}.get(pose['source'], 'Vision estimate') if pose else 'Vision estimate'
        position = [row[3] for row in pose['map_from_aircraft'][:3]] if pose else None
        self.navigation_pose.setText(prefix + ' XYZ: ' + (', '.join(f'{n:.3f}' for n in position) + ' m' if position else '—'))
        waypoint = navigation.get('next_waypoint') if navigation else None
        self.navigation_waypoint.setText('Next waypoint: ' + (', '.join(f'{n:.3f}' for n in waypoint) + ' m' if waypoint else '—'))
        self.navigation_timing.setText(f"Pose age / provisional uncertainty: {navigation['pose_age_s'] * 1000:.0f} ms / {pose['uncertainty_m']:.3f} m" if pose else 'Pose age / uncertainty: —')
        mission = navigation.get('mission') if navigation else None
        if mission:
            target = f" · {mission['target_index'] + 1}/{mission['target_count']} {mission['target_name']}" if mission.get('target_index') is not None else ''
            digest = f" · {mission['snapshot_sha256'][:12]}" if mission.get('snapshot_sha256') else ''
            self.navigation_mission.setText(f"Inspection mission: {mission['status']}{target} · snapshot {mission['snapshot_status']}{digest}")
        else:
            self.navigation_mission.setText('Inspection mission: —')
        self.navigation_route.clear()
        for i, point in enumerate(navigation['route'] if navigation else []):
            headings = navigation.get('route_headings_rad') or []
            tags = navigation.get('route_tag_ids') or []
            yaw = f'{math.degrees(headings[i]):.1f}' if i < len(headings) else '—'
            visible = ','.join(map(str, tags[i])) if i < len(tags) else '—'
            self.navigation_route.addTopLevelItem(QTreeWidgetItem([str(i), *(f'{n:.3f}' for n in point), yaw, visible]))
        available = bool(self.authorized and navigation)
        for button in (self.navigation_goal, self.navigation_resume, self.navigation_disable): button.setEnabled(available)
        status = mission.get('status') if mission else None
        self.navigation_mission_start.setEnabled(available and status == 'ready')
        self.navigation_mission_advance.setEnabled(available and status == 'target_complete')
        self.navigation_mission_abort.setEnabled(available and status in ('ready', 'running', 'waiting_for_localization', 'waiting_for_target', 'reacquiring_target', 'snapshot_pending', 'target_complete', 'fault'))
        self.state_label.setText(state['state'])
        self.video.caption = ''
        self.video.stale = False
        self.video.notice = ''
        status = state.get('steering_status')
        self.video.steering_text = status if isinstance(status, str) else ''
        live = real_operator_source(state)
        # Recorded/camera pictures are shown; the synthetic scene never is (2026-10-05 decision).
        self.video.show_signal = live
        if not live:
            self.video.pixmap = QPixmap()
        detection = state.get('detection') or {}
        self.video.error = detection.get('error') if live else None
        self.video.target_text = ('Target tracked' if detection else 'Target not found') if live else ''
        # Server connection can be fresh while the video itself has stopped.
        age, limit = state.get('frame_age_ms'), state['settings'].get('stale_ms', 250)
        if live and (age is None or age >= limit):
            self.video.stale = True
            self.video.notice = 'Video stale · no fresh frames'
            self.video.error, self.video.target_text = None, ''
        self.video.update()
        self.session_label.setText(session_caption(state['session']))
        self.session_label.setToolTip(state['session'])
        if not real_operator_source(state):
            self.show_placeholders()
            mode = 'Local session' if self.backend else ('Remote operator' if self.authorized else 'Remote viewer')
            self.connection_label.set_status(f'{mode}  ·  {self.api.url}')
            self.update_access()
            return
        self.source_label.setText(' ' + state['source_label'] + ' ')
        detection = state.get('detection') or {}
        for key, label in self.readouts.items():
            if key in ('bridge', 'bridge_fault') and not (state.get('physical_output') or state.get('steering_available')):
                label.setText('—')
                continue
            value = detection.get(key) if key in ('error', 'quality') else state.get(key)
            text = '—' if value is None else f'{value:.3f}' if key in ('error', 'quality') else str(value)
            if value is not None and key.endswith('_ms'): text += ' ms'
            label.setText(text)
        self.fault_label.setText('Fault: ' + state['fault'] if state.get('fault') else 'No active fault')
        self.plot.append(state)
        event = (state['state'], state.get('fault'), state['source_label'], json.dumps(state['source']), state['enabled'])
        if event != self.last_event:
            self.add_event(state['state'], state.get('fault') or (state['source_label'] + ' · assistance ' + ('enabled' if state['enabled'] else 'disabled')))
            self.last_event = event
        mode = 'Local session' if self.backend else ('Remote operator' if self.authorized else 'Remote viewer')
        self.connection_label.set_status(f'{mode}  ·  {self.api.url}')
        self.update_access()

    def check_freshness(self):
        age = None if not self.api.last_ok else time.monotonic() - self.api.last_ok
        lost = age is not None and age > .5
        waiting = age is None
        if lost:
            self.navigation_status.setText('Connection lost · guidance suppressed')
            self.navigation_mission.setText('Inspection mission: server disconnected')
            self.navigation_pose.setText('Estimated XYZ: —')
            self.navigation_waypoint.setText('Next waypoint: —')
            self.navigation_timing.setText('Pose age / uncertainty: —')
            self.navigation_route.clear()
            for button in (self.navigation_goal, self.navigation_resume, self.navigation_disable): button.setEnabled(False)
            for button in (self.navigation_mission_start, self.navigation_mission_advance, self.navigation_mission_abort): button.setEnabled(False)
            # Only set here: update_state owns clearing, including its own stale-video check.
            self.video.stale = True
            self.video.notice = 'Connection lost · preview is stale'
            self.connection_label.set_status('Disconnected  ·  ' + self.api.url)
            self.state_label.setText('OFFLINE')
            for label in self.readouts.values(): label.setText('—')
        elif waiting:
            self.video.notice = 'Starting local session' if self.backend else 'Waiting for server'
            self.connection_label.set_status(('Starting' if self.backend else 'Waiting') + '  ·  ' + self.api.url)
            if not self.snapshot:
                self.state_label.setText('STARTING')
        self.video.update()
        self.update_access()

    def failure(self, message):
        self.statusBar().showMessage(message, 8000)
        # Avoid filling the event list with every reconnect attempt.
        if not getattr(self, '_last_error', None) == message:
            self.add_event('Client', message)
            self._last_error = message

    def add_event(self, kind, detail):
        if self.events.topLevelItemCount() == 1 and self.events.topLevelItem(0).text(2) == 'No events':
            self.events.clear()
        self.events.addTopLevelItem(QTreeWidgetItem([time.strftime('%H:%M:%S'), kind, detail]))
        if self.events.topLevelItemCount() > 300:
            self.events.takeTopLevelItem(0)
        self.events.scrollToBottom()

    def neutral_remote(self):
        if not self.authorized:
            return True
        loop = QEventLoop()
        result = []
        self.api.request('/api/operator/assist', {'enabled': False},
                         callback=lambda reply: (result.append(reply), loop.quit()))
        QTimer.singleShot(2000, loop.quit)
        loop.exec()
        if not result: return False
        try: validate_snapshot(result[0])
        except ValueError: return False
        return result[0]['enabled'] is False and result[0]['yaw'] == 0

    def connect_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Connect to Pi / demo server')
        form = QFormLayout(dialog)
        url = QLineEdit('http://ball-drone.local:8080')
        token = QLineEdit()
        token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Server URL', url)
        form.addRow('Operator token (optional)', token)
        form.addRow(QLabel('Leave the token empty for read-only viewing.\nTokens are kept in memory only; use a trusted demo network.'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        address = url.text().strip().rstrip('/')
        parsed = urlparse(address)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            QMessageBox.warning(self, 'Invalid server', 'Use an HTTP(S) origin such as http://ball-drone.local:8080.')
            return
        if self.backend:
            self.backend.stop()
            self.backend = None
        elif not self.neutral_remote():
            QMessageBox.warning(self, 'Could not confirm neutral', 'The previous server did not confirm disabled assistance. Reconnect and disable it before switching servers.')
            return
        self.authorized = False
        self.snapshot = {}
        self.video.pixmap = QPixmap()
        self.plot.samples.clear()
        self.api.connect_to(address, token.text())
        if token.text(): self.api.request('/api/operator/access', callback=self.access_checked)
        self.update_access()

    def open_session_folder(self):
        if self.backend:
            folder = self.backend.data / 'sessions' / self.snapshot.get('session', '')
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        else:
            self.failure('Session files are stored on the connected server, not on this device.')

    def show_trace(self, trace):
        try:
            if not isinstance(trace, dict) or not trace.get('samples'):
                raise ValueError('No fixture samples found')
            dialog = TraceWindow(trace, self)
        except (KeyError, TypeError, ValueError) as error:
            self.failure('Not a compatible synthetic fixture trace: ' + str(error))
            return
        self.trace_windows.append(dialog)
        dialog.show()

    def open_trace(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open synthetic fixture trace', '', 'JSON trace (*.json)')
        if path:
            try: self.show_trace(json.loads(Path(path).read_text()))
            except (ValueError, OSError) as error: self.failure(str(error))

    def play_scenario(self):
        self.api.request('/api/sandbox/' + self.scenario.currentData(), callback=self.show_trace)
        self.statusBar().showMessage('Loading isolated fixture trace…', 3000)

    def closeEvent(self, event):
        if self.backend:
            self.backend.stop()
            self.backend = None
        elif not self.neutral_remote():
            QMessageBox.warning(self, 'Could not confirm neutral', 'The server did not acknowledge disable. This window will stay open so you can reconnect. A client disconnect does not itself stop a remote server.')
            event.ignore()
            return
        self.api.timer.stop()
        self.freshness.stop()
        self.authorized = False
        event.accept()


def main():
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description='Native Ball Drone workstation for Mac and Pi')
    parser.add_argument('--connect', help='Connect to a running Pi/server instead of starting a local mock session')
    parser.add_argument('--token-file', type=Path, help='Operator token file for a connected server; omitted means viewer')
    parser.add_argument('--data', type=Path, help='Local sessions/private token directory')
    parser.add_argument('--listen', default='0.0.0.0', help='Local visitor server bind address')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--snapshot', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--quit-after', type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()
    # This Mac's .venv plugin files carry UF_HIDDEN flags; Qt skips them.
    # Copy without file metadata for source launches rather than changing the venv.
    # The standalone .app has visible bundled plugins and needs no workaround.
    plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    plugin_cache = None
    if sys.platform == 'darwin' and QFileInfo(str(plugins / 'platforms/libqcocoa.dylib')).isHidden():
        plugin_cache = tempfile.TemporaryDirectory(prefix='ball-drone-qt-', dir='/tmp')
        cache = Path(plugin_cache.name)
        shutil.copytree(plugins, cache, dirs_exist_ok=True, copy_function=shutil.copy)
        os.environ['QT_PLUGIN_PATH'] = str(cache)
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(cache / 'platforms')
        QCoreApplication.setLibraryPaths([str(cache)])
    app = QApplication([sys.argv[0]])
    app.setApplicationName('Ball Drone')
    app.setOrganizationName('BallDrone')
    app.setApplicationDisplayName('Ball Drone')
    icon = Path(__file__).parent / 'static' / 'desktop-icon.png'
    if icon.exists(): app.setWindowIcon(QIcon(str(icon)))
    data = args.data or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    backend = None
    try:
        if not args.connect:
            from .desktop_backend import DesktopBackend
            backend = DesktopBackend(data, args.listen, args.port)
        token = args.token_file.read_text().strip() if args.token_file else ''
        window = Workstation(backend, args.connect or '', token)
    except Exception as error:
        if backend: backend.stop()
        QMessageBox.critical(None, 'Cannot start Ball Drone', str(error))
        return 1
    window.show()
    if backend: QTimer.singleShot(0, backend.start)
    def shutdown():
        if window.backend:
            window.backend.stop()
            window.backend = None
    app.aboutToQuit.connect(shutdown)
    if args.snapshot:
        def capture():
            args.snapshot.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.snapshot))
        QTimer.singleShot(2500, capture)
    if args.quit_after:
        QTimer.singleShot(int(args.quit_after * 1000), window.close)
    result = app.exec()
    if plugin_cache: plugin_cache.cleanup()
    return result


if __name__ == '__main__':
    sys.exit(main())
