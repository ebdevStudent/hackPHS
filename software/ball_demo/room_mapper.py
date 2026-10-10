"""Standalone guided, tag-registered RealSense room capture application.

The scanner stays still for each capture. AprilTags register successive views;
this tool does not estimate a moving handheld trajectory or implement SLAM.
"""
from datetime import datetime
import json
import math
from pathlib import Path
import re

import numpy as np
from PySide6.QtCore import Qt, QStandardPaths, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMessageBox, QProgressBar, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .map_io import Survey, Tag
from .mapping import Station, rebuild_scans


FACING_ROTATIONS = {
    # Columns are tag-right, tag-up, and the normal pointing out of its face.
    'Into room from x=0 wall (+X)': [[0., 0., 1.], [1., 0., 0.], [0., 1., 0.]],
    'Into room from x=max wall (-X)': [[0., 0., -1.], [-1., 0., 0.], [0., 1., 0.]],
    'Into room from y=0 wall (+Y)': [[-1., 0., 0.], [0., 0., 1.], [0., 1., 0.]],
    'Into room from y=max wall (-Y)': [[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]],
}


def _number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return float(value)


def build_room_setup(map_id, dimensions, voxel_m, uncertainty_m, max_depth_m, tag_rows, evidence_note=None):
    """Build validated map settings and surveyed AprilTags from GUI values."""
    if not isinstance(map_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,96}', map_id):
        raise ValueError('Map ID must use 1–96 letters, numbers, dots, underscores or hyphens.')
    dims = [_number(value, 'Room dimension') for value in dimensions]
    if len(dims) != 3:
        raise ValueError('Room dimensions must include width (X), length (Y), and height (Z).')
    if any(value <= 0 for value in dims):
        raise ValueError('Enter positive room width (X), length (Y), and height (Z).')
    step = _number(voxel_m, 'Voxel size')
    uncertainty = _number(uncertainty_m, 'Map uncertainty')
    max_depth = _number(max_depth_m, 'Maximum depth')
    if min(step, uncertainty, max_depth) <= 0:
        raise ValueError('Voxel size, uncertainty and maximum depth must be positive.')
    cell_count = math.prod(math.ceil(d / step) for d in dims)
    if cell_count > 100_000:
        raise ValueError(f'This scan would contain {cell_count:,} voxels; the current mapper limit is 100,000. Increase voxel size or scan a smaller zone.')
    if len(tag_rows) < 2:
        raise ValueError('Add at least two surveyed AprilTags. Keep both visible in each capture.')
    if len(tag_rows) > 587:
        raise ValueError('AprilTag 36h11 has IDs 0–586; remove extra rows.')
    tags, seen = [], set()
    for row_number, row in enumerate(tag_rows, 1):
        try:
            tag_id = row['id']
            if type(tag_id) is not int or not 0 <= tag_id < 587: raise ValueError('ID must be an integer from 0 to 586')
            if tag_id in seen: raise ValueError(f'Duplicate AprilTag ID {tag_id}')
            seen.add(tag_id)
            size = _number(row['size_m'], f'Tag {tag_id} size')
            if size <= 0: raise ValueError('black-square side length must be positive')
            pos = [_number(row[key], f'Tag {tag_id} {key}') for key in ('x', 'y', 'z')]
            if any(v < 0 or v > limit for v, limit in zip(pos, dims)):
                raise ValueError('tag center must be inside the surveyed room bounds')
            facing = row['facing']
            if facing not in FACING_ROTATIONS: raise ValueError('choose which wall the printed face points into the room from')
            transform = np.eye(4)
            transform[:3, :3] = np.array(FACING_ROTATIONS[facing])
            transform[:3, 3] = pos
            tags.append(Tag(id=tag_id, size_m=size, map_from_tag=transform.tolist()))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f'AprilTag row {row_number}: {error}') from error
    note = (evidence_note or '').strip()
    if not note: raise ValueError('Add a short note about how the room and tag positions were measured.')
    survey = Survey(schema_version=1, survey_id=f'{map_id}_survey', map_id=map_id, map_version=1,
                    frame_id=f'{map_id}_frame', units='m', family='tag36h11', tags=tags,
                    evidence=f'Operator-entered measurements: {note}; accuracy has not been independently checked.',
                    example=False)
    station = Station(schema_version=1, scan_id=f'{map_id}_view_001', map_id=map_id, map_version=1,
                      frame_id=f'{map_id}_frame', permitted={'minimum': [0., 0., 0.], 'maximum': dims},
                      voxel_m=step, uncertainty_m=uncertainty, max_depth_m=max_depth,
                      map_from_depth=np.eye(4).tolist(),
                      registration_evidence='Pose will be estimated during capture from surveyed AprilTags.', example=False)
    return station, survey, cell_count


def _sdk_name(device, sdk):
    name = device.get_info(sdk.camera_info.name).strip()
    if name not in ('Intel RealSense D435', 'Intel RealSense D435 Camera', 'RealSense D435'):
        raise ValueError(f'Expected an Intel RealSense D435; found {name or "unknown device"}.')
    return name


class PreviewWorker(QThread):
    frame = Signal(object)
    status = Signal(str)
    failed = Signal(str)

    def __init__(self, survey, map_uncertainty_m, parent=None):
        super().__init__(parent)
        self.survey = survey
        self.map_uncertainty_m = map_uncertainty_m

    def run(self):
        pipeline = None
        try:
            try:
                import pyrealsense2 as sdk
            except ImportError as error:
                raise ValueError('The optional RealSense SDK is unavailable for this Python/OS. Use a supported D435 capture computer or install a compatible librealsense binding.') from error
            from .registration import RegistrationPolicy, rgb_geometry
            from .localization import CameraPoseSolver
            pipeline, config = sdk.pipeline(), sdk.config()
            config.enable_stream(sdk.stream.color, 640, 480, sdk.format.bgr8, 30)
            profile = pipeline.start(config)
            _sdk_name(profile.get_device(), sdk)
            color_profile = profile.get_stream(sdk.stream.color).as_video_stream_profile()
            intr = color_profile.get_intrinsics()
            solver = CameraPoseSolver(rgb_geometry(intr), self.survey)
            policy = RegistrationPolicy()
            self.status.emit('Camera connected. Aim it so at least two surveyed tags are visible.')
            count = 0
            while not self.isInterruptionRequested():
                sample = pipeline.wait_for_frames(1000)
                color = sample.get_color_frame()
                if not color:
                    continue
                image = np.asanyarray(color.get_data()).copy()
                count += 1
                if count % 3 == 0:
                    try:
                        observations = solver.detect(image)
                        known = [o for o in observations if o.id in solver.tags]
                        if len(known) < policy.min_tags:
                            message = f'{len(known)} surveyed tags visible; need at least {policy.min_tags}.'
                        else:
                            estimate = solver.solve(known)
                            full_bound = (estimate.uncertainty_m + policy.survey_uncertainty_m +
                                          policy.factory_uncertainty_m + policy.depth_uncertainty_m)
                            quality_ok = (estimate.reprojection_px <= policy.max_reprojection_px and
                                          estimate.ambiguity_gap_px >= policy.min_ambiguity_gap_px and
                                          full_bound <= self.map_uncertainty_m)
                            import cv2
                            camera_matrix = np.array(solver.calibration.intrinsics)
                            image = cv2.undistort(image, camera_matrix, np.array(solver.calibration.distortion), None, camera_matrix)
                            outline_color = (60, 220, 100) if quality_ok else (0, 190, 255)
                            for observation in known:
                                points = np.round(observation.corners).astype(np.int32).reshape(-1, 1, 2)
                                cv2.polylines(image, [points], True, outline_color, 2)
                                cv2.putText(image, f'ID {observation.id}', tuple(points[0, 0]), cv2.FONT_HERSHEY_SIMPLEX, .6, outline_color, 2)
                            if estimate.reprojection_px > policy.max_reprojection_px or estimate.ambiguity_gap_px < policy.min_ambiguity_gap_px:
                                message = 'Pose quality is ambiguous; move tags farther apart or adjust the camera.'
                            elif full_bound > self.map_uncertainty_m:
                                message = (f'Estimated registration bound {full_bound:.3f} m exceeds the '
                                           f'{self.map_uncertainty_m:.3f} m map bound; improve tag coverage or increase the bound.')
                            else:
                                message = (f'Ready · tags {", ".join(map(str, estimate.tag_ids))} · '
                                           f'reprojection {estimate.reprojection_px:.1f} px · '
                                           f'estimated registration bound at least {full_bound:.3f} m')
                    except Exception as error:
                        message = str(error)
                    self.status.emit(message)
                self.frame.emit(image)
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            if pipeline is not None:
                try: pipeline.stop()
                except Exception: pass


class CaptureWorker(QThread):
    frame = Signal(object)
    progress = Signal(int, int)
    registration = Signal(dict)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, station, survey, output, frames=30, parent=None):
        super().__init__(parent)
        self.station, self.survey, self.output, self.frames = station, survey, Path(output), frames

    def run(self):
        try:
            from .mapping import capture_d435
            capture_d435(self.station, self.output, self.frames, registration_survey=self.survey,
                         on_frame=lambda image: self.frame.emit(image.copy()),
                         on_progress=lambda current, total: self.progress.emit(current, total),
                         on_registration=lambda value: self.registration.emit(value))
            self.done.emit(str(self.output / 'scan.json'))
        except Exception as error:
            self.failed.emit(str(error))


class RebuildWorker(QThread):
    done = Signal(str, dict)
    failed = Signal(str)

    def __init__(self, scans, output, parent=None):
        super().__init__(parent)
        self.scans, self.output = list(scans), Path(output)

    def run(self):
        try:
            mapped, report = rebuild_scans(self.scans)
            self.output.mkdir(parents=True, exist_ok=False)
            (self.output / 'map.json').write_text(mapped.model_dump_json(indent=2) + '\n')
            (self.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            self.done.emit(str(self.output / 'map.json'), report)
        except Exception as error:
            self.failed.emit(str(error))


class GuidedRoomMapper(QDialog):
    """Two-step standalone UI for setting up, capturing and rebuilding a room map."""
    capture_frames = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Guided D435 Room Mapper')
        self.resize(920, 760)
        self.setMinimumSize(760, 620)
        self.station_template = None
        self.survey = None
        self.cell_count = 0
        self.scan_paths = []
        self.preview_worker = None
        self.capture_worker = None
        self.rebuild_worker = None
        self.capture_after_preview = False
        self.session_path = ''
        self.build_count = 0
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel('Scan the room with guided, registered views')
        title.setStyleSheet('font-size: 20px; font-weight: 600;')
        root.addWidget(title)
        intro = QLabel('Set the room bounds and survey at least two AprilTags. Then keep the D435 still at each spot and click Capture this view. The app records 30 frames, registers the camera from the tags, and builds the map for you.')
        intro.setWordWrap(True)
        root.addWidget(intro)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.setup_tab = QWidget()
        self.capture_tab = QWidget()
        self.tabs.addTab(self.setup_tab, '1 · Room setup')
        self.tabs.addTab(self.capture_tab, '2 · Capture and build')
        self._build_setup()
        self._build_capture()
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close = QPushButton('Close')
        close.clicked.connect(self.close)
        close_row.addWidget(close)
        root.addLayout(close_row)

    def _spin(self, low, high, value, step, decimals=2):
        item = QDoubleSpinBox()
        item.setRange(low, high); item.setDecimals(decimals); item.setSingleStep(step); item.setValue(value)
        return item

    def _build_setup(self):
        layout = QVBoxLayout(self.setup_tab)
        axes = QLabel('Measure the room from one floor corner: origin (0,0,0), X and Y along the floor edges, Z upward. Enter actual bounds; the displayed values are starting examples, not measurements.')
        axes.setWordWrap(True)
        layout.addWidget(axes)
        group = QGroupBox('Room and map settings')
        form = QFormLayout(group)
        self.map_id = QLineEdit('room_scan')
        form.addRow('Map ID', self.map_id)
        dimensions = QWidget(); dims = QGridLayout(dimensions); dims.setContentsMargins(0, 0, 0, 0)
        self.room_x = self._spin(.1, 30., 2., .1)
        self.room_y = self._spin(.1, 30., 2., .1)
        self.room_z = self._spin(.1, 10., 2., .1)
        dims.addWidget(QLabel('X width (m)'), 0, 0); dims.addWidget(self.room_x, 0, 1)
        dims.addWidget(QLabel('Y length (m)'), 0, 2); dims.addWidget(self.room_y, 0, 3)
        dims.addWidget(QLabel('Z height (m)'), 0, 4); dims.addWidget(self.room_z, 0, 5)
        form.addRow('Room bounds', dimensions)
        self.voxel = self._spin(.025, .5, .1, .01, 3)
        self.uncertainty = self._spin(.02, .5, .1, .01, 3)
        self.max_depth = self._spin(.2, 10., 4., .1)
        form.addRow('Voxel size (m)', self.voxel)
        form.addRow('Provisional uncertainty bound (m)', self.uncertainty)
        form.addRow('Maximum depth (m)', self.max_depth)
        self.cell_label = QLabel()
        form.addRow('Mapper budget', self.cell_label)
        for widget in (self.room_x, self.room_y, self.room_z, self.voxel):
            widget.valueChanged.connect(self.update_cell_estimate)
        layout.addWidget(group)
        tags_group = QGroupBox('Surveyed AprilTags')
        tags_layout = QVBoxLayout(tags_group)
        note = QLabel('Use AprilTag 36h11 markers. Measure each black square edge and its center from the room origin. Mount each printed tag upright with its top edge pointing up; select the wall direction its face points toward. Spread the tags out and keep at least two visible from each capture spot.')
        note.setWordWrap(True)
        tags_layout.addWidget(note)
        self.tag_table = QTableWidget(0, 6)
        self.tag_table.setHorizontalHeaderLabels(['Tag ID', 'Black edge (m)', 'Center X (m)', 'Center Y (m)', 'Center Z (m)', 'Printed face points into room from'])
        self.tag_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tag_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tag_table.horizontalHeader().setStretchLastSection(True)
        tags_layout.addWidget(self.tag_table, 1)
        tag_actions = QHBoxLayout()
        add = QPushButton('Add measured tag'); add.clicked.connect(self.add_tag_row)
        remove = QPushButton('Remove selected tag'); remove.clicked.connect(self.remove_tag_row)
        print_tags = QPushButton('Create printable tag sheet…'); print_tags.clicked.connect(self.save_tag_sheet)
        tag_actions.addWidget(add); tag_actions.addWidget(remove); tag_actions.addStretch(1); tag_actions.addWidget(print_tags)
        tags_layout.addLayout(tag_actions)
        layout.addWidget(tags_group, 1)
        evidence_group = QGroupBox('Save your scan')
        evidence_layout = QFormLayout(evidence_group)
        self.output_path = QLineEdit(self._default_session_path())
        browse = QPushButton('Choose folder…'); browse.clicked.connect(self.choose_output_folder)
        path_row = QWidget(); path_layout = QHBoxLayout(path_row); path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.output_path, 1); path_layout.addWidget(browse)
        evidence_layout.addRow('New scan folder', path_row)
        self.evidence_note = QLineEdit('Operator-entered room and tag values; measurement method not independently checked.')
        evidence_layout.addRow('Survey note', self.evidence_note)
        layout.addWidget(evidence_group)
        go = QPushButton('Continue to camera preview →')
        go.clicked.connect(self.continue_to_capture)
        layout.addWidget(go, alignment=Qt.AlignmentFlag.AlignRight)
        self.update_cell_estimate()

    def _build_capture(self):
        layout = QVBoxLayout(self.capture_tab)
        help_text = QLabel('At each spot, keep the camera still and aim until two surveyed tag outlines are green. Capture the view, then move to another spot to cover hidden areas. Do not walk with the camera during a capture.')
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.preview = QLabel('Camera preview will appear here')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(640, 400)
        self.preview.setStyleSheet('background: #111820; color: #b8c1c8; border: 1px solid #66727c;')
        layout.addWidget(self.preview, 1)
        self.capture_status = QLabel('Set up the room and tags first.')
        self.capture_status.setWordWrap(True)
        layout.addWidget(self.capture_status)
        self.progress = QProgressBar(); self.progress.setRange(0, self.capture_frames); self.progress.setValue(0)
        layout.addWidget(self.progress)
        actions = QHBoxLayout()
        self.preview_button = QPushButton('Start camera preview'); self.preview_button.clicked.connect(self.toggle_preview)
        self.capture_button = QPushButton('Capture this view'); self.capture_button.clicked.connect(self.capture_view); self.capture_button.setEnabled(False)
        self.build_button = QPushButton('Build map from captured views'); self.build_button.clicked.connect(self.build_map); self.build_button.setEnabled(False)
        actions.addWidget(self.preview_button); actions.addWidget(self.capture_button); actions.addStretch(1); actions.addWidget(self.build_button)
        layout.addLayout(actions)
        self.views = QListWidget()
        self.views.setMaximumHeight(100)
        layout.addWidget(self.views)
        self.map_result = QLabel('No map built yet.')
        self.map_result.setWordWrap(True)
        layout.addWidget(self.map_result)
        self.open_result = QPushButton('Open map folder'); self.open_result.clicked.connect(self.open_map_folder); self.open_result.setEnabled(False)
        layout.addWidget(self.open_result, alignment=Qt.AlignmentFlag.AlignRight)

    def _default_session_path(self):
        docs = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        parent = Path(docs) if docs else Path.home()
        return str(parent / 'Ball Drone Room Scans' / f'room-scan-{datetime.now():%Y%m%d-%H%M%S}')

    def update_cell_estimate(self, *_):
        count = math.prod(math.ceil(widget.value() / self.voxel.value()) for widget in (self.room_x, self.room_y, self.room_z))
        self.cell_label.setText(f'{count:,} / 100,000 voxels' + (' · increase voxel size or reduce zone' if count > 100_000 else ''))
        self.cell_label.setStyleSheet('color: #b42318;' if count > 100_000 else '')

    def add_tag_row(self):
        row = self.tag_table.rowCount()
        self.tag_table.insertRow(row)
        for col in range(5): self.tag_table.setItem(row, col, QTableWidgetItem(''))
        facing = QComboBox(); facing.addItem('Choose wall direction')
        facing.addItems(FACING_ROTATIONS.keys())
        self.tag_table.setCellWidget(row, 5, facing)
        self.tag_table.setCurrentCell(row, 0)

    def remove_tag_row(self):
        row = self.tag_table.currentRow()
        if row >= 0: self.tag_table.removeRow(row)

    def _tag_rows(self):
        rows = []
        for row in range(self.tag_table.rowCount()):
            values = []
            for col in range(5):
                item = self.tag_table.item(row, col)
                value = item.text().strip() if item else ''
                if not value: raise ValueError(f'Fill in all measurements for AprilTag row {row + 1}.')
                values.append(value)
            try:
                tag_id = int(values[0])
                size, x, y, z = map(float, values[1:])
            except ValueError as error:
                raise ValueError(f'AprilTag row {row + 1} has a nonnumeric measurement.') from error
            facing = self.tag_table.cellWidget(row, 5).currentText()
            rows.append({'id': tag_id, 'size_m': size, 'x': x, 'y': y, 'z': z, 'facing': facing})
        return rows

    def choose_output_folder(self):
        parent = QFileDialog.getExistingDirectory(self, 'Choose parent folder for room scan')
        if parent:
            name = Path(self.output_path.text()).name or f'room-scan-{datetime.now():%Y%m%d-%H%M%S}'
            self.output_path.setText(str(Path(parent) / name))

    def _printable_tag_rows(self):
        rows, seen = [], set()
        for index in range(self.tag_table.rowCount()):
            id_item, size_item = self.tag_table.item(index, 0), self.tag_table.item(index, 1)
            if not id_item or not size_item or not id_item.text().strip() or not size_item.text().strip():
                raise ValueError(f'Enter the ID and black-square side length for AprilTag row {index + 1}.')
            try:
                tag_id = int(id_item.text().strip())
                size = float(size_item.text().strip())
            except ValueError as error:
                raise ValueError(f'AprilTag row {index + 1} needs a numeric ID and size.') from error
            if type(tag_id) is not int or not 0 <= tag_id < 587: raise ValueError(f'AprilTag row {index + 1}: ID must be 0–586.')
            if tag_id in seen: raise ValueError(f'Duplicate AprilTag ID {tag_id}.')
            if not math.isfinite(size) or size <= 0: raise ValueError(f'AprilTag row {index + 1}: size must be positive.')
            seen.add(tag_id); rows.append({'id': tag_id, 'size_m': size})
        if not rows: raise ValueError('Add tag IDs and black-square sizes before creating a sheet.')
        return rows

    def _validated_setup(self):
        if not self.evidence_note.text().strip(): raise ValueError('Add a short note about how the room and tag positions were measured.')
        station, survey, count = build_room_setup(
            self.map_id.text().strip(), [self.room_x.value(), self.room_y.value(), self.room_z.value()],
            self.voxel.value(), self.uncertainty.value(), self.max_depth.value(), self._tag_rows(), self.evidence_note.text())
        return station, survey, count

    def continue_to_capture(self):
        try:
            self.station_template, self.survey, self.cell_count = self._validated_setup()
            folder = Path(self.output_path.text()).expanduser()
            if not folder.is_absolute(): raise ValueError('Choose an absolute folder path for the scan output.')
            if folder.exists(): raise ValueError('The scan folder already exists. Choose a new folder so earlier captures are preserved.')
            self.session_path = str(folder.resolve())
            self.tabs.setCurrentWidget(self.capture_tab)
            self.capture_status.setText(f'Ready for a {self.station_template.map_id} scan · {self.cell_count:,} voxels · keep at least two tags visible.')
        except Exception as error:
            QMessageBox.warning(self, 'Room setup needs attention', str(error))

    def toggle_preview(self):
        if self.preview_worker and self.preview_worker.isRunning():
            self.preview_button.setText('Stopping preview…')
            self.preview_button.setEnabled(False)
            self.preview_worker.requestInterruption()
            return
        try:
            if self.station_template is None:
                self.station_template, self.survey, self.cell_count = self._validated_setup()
            self.preview_button.setText('Stop camera preview')
            self.preview_button.setEnabled(True)
            self.capture_button.setEnabled(True)
            self.capture_status.setText('Starting D435 preview…')
            self.preview_worker = PreviewWorker(self.survey, self.station_template.uncertainty_m, self)
            self.preview_worker.frame.connect(self.show_frame)
            self.preview_worker.status.connect(self.capture_status.setText)
            self.preview_worker.failed.connect(self.preview_failed)
            self.preview_worker.finished.connect(self.preview_finished)
            self.preview_worker.start()
        except Exception as error:
            QMessageBox.warning(self, 'Room setup needs attention', str(error))

    def preview_failed(self, message):
        self.capture_status.setText('Camera preview stopped: ' + message)
        self.capture_button.setEnabled(False)

    def preview_finished(self):
        self.preview_button.setText('Start camera preview')
        self.preview_button.setEnabled(True)
        self.capture_button.setEnabled(bool(self.station_template) and len(self.scan_paths) < 20)
        if self.capture_after_preview:
            self.capture_after_preview = False
            self._begin_capture()

    def show_frame(self, image):
        if image is None or not isinstance(image, np.ndarray) or image.ndim != 3: return
        h, w, channels = image.shape
        if channels != 3: return
        qimage = QImage(image.data, w, h, int(image.strides[0]), QImage.Format.Format_BGR888).copy()
        self.preview.setPixmap(QPixmap.fromImage(qimage).scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                                  Qt.TransformationMode.SmoothTransformation))

    def capture_view(self):
        if self.capture_worker and self.capture_worker.isRunning(): return
        if self.preview_worker and self.preview_worker.isRunning():
            self.capture_after_preview = True
            self.capture_status.setText('Closing preview before capture…')
            self.preview_button.setEnabled(False)
            self.capture_button.setEnabled(False)
            self.preview_worker.requestInterruption()
        else:
            self._begin_capture()

    def _begin_capture(self):
        try:
            self.station_template, self.survey, self.cell_count = self._validated_setup()
            session = Path(self.session_path or self.output_path.text()).expanduser().resolve()
            if not session.exists():
                session.parent.mkdir(parents=True, exist_ok=True)
                session.mkdir(exist_ok=False)
                (session / 'survey.json').write_text(self.survey.model_dump_json(indent=2) + '\n', encoding='utf-8')
                self.session_path = str(session)
            index = 1
            while (session / f'capture-{index:02d}').exists(): index += 1
            if index > 20: raise ValueError('The current map combines at most 20 captures.')
            station = self.station_template.model_copy(update={'scan_id': f'{self.station_template.map_id}_view_{index:03d}'})
            target = session / f'capture-{index:02d}'
            self.progress.setRange(0, self.capture_frames); self.progress.setValue(0)
            self.capture_status.setText(f'Capturing view {index}: hold the D435 still and keep two or more surveyed tags visible…')
            self.capture_button.setEnabled(False); self.preview_button.setEnabled(False); self.build_button.setEnabled(False)
            self.capture_worker = CaptureWorker(station, self.survey, target, self.capture_frames, self)
            self.capture_worker.frame.connect(self.show_frame)
            self.capture_worker.progress.connect(self.progress.setValue)
            self.capture_worker.registration.connect(self.update_registration)
            self.capture_worker.done.connect(self.capture_done)
            self.capture_worker.failed.connect(self.capture_failed)
            self.capture_worker.finished.connect(self.capture_finished)
            self.capture_worker.start()
        except Exception as error:
            QMessageBox.warning(self, 'Could not start capture', str(error))

    def update_registration(self, result):
        if result.get('stable'):
            ids = ', '.join(map(str, result.get('tag_ids', [])))
            uncertainty = result.get('uncertainty_m')
            self.capture_status.setText(f'Camera registered from tags {ids} · provisional bound {uncertainty:.3f} m' if uncertainty is not None else f'Camera registered from tags {ids}.')
        elif result.get('message'):
            self.capture_status.setText('Registration failed: ' + result['message'])

    def capture_done(self, manifest):
        self.scan_paths.append(manifest)
        self.views.addItem(f'View {len(self.scan_paths):02d} captured · {Path(manifest).parent}')
        self.capture_status.setText(f'Captured {len(self.scan_paths)} view(s). Move the D435 to another still position for hidden areas, or build the map.')
        self.build_button.setEnabled(True)

    def capture_failed(self, message):
        self.capture_status.setText('Capture failed. Its incomplete folder was preserved. ' + message)
        QMessageBox.warning(self, 'D435 capture failed', message + '\n\nThe partial capture folder is preserved; a retry will use a new folder.')

    def capture_finished(self):
        self.capture_button.setEnabled(len(self.scan_paths) < 20)
        self.preview_button.setEnabled(True)
        if self.scan_paths: self.build_button.setEnabled(True)

    def build_map(self):
        if not self.scan_paths or (self.rebuild_worker and self.rebuild_worker.isRunning()): return
        session = Path(self.session_path)
        self.build_count += 1
        target = session / f'map-{self.build_count:02d}'
        while target.exists():
            self.build_count += 1; target = session / f'map-{self.build_count:02d}'
        self.capture_status.setText('Building map from the saved views. Larger zones can take a while…')
        self.capture_button.setEnabled(False); self.preview_button.setEnabled(False); self.build_button.setEnabled(False)
        self.rebuild_worker = RebuildWorker(self.scan_paths, target, self)
        self.rebuild_worker.done.connect(self.rebuild_done)
        self.rebuild_worker.failed.connect(self.rebuild_failed)
        self.rebuild_worker.finished.connect(self.rebuild_finished)
        self.rebuild_worker.start()

    def rebuild_done(self, map_path, report):
        self.map_result.setText(f'Map saved: {map_path}\nObserved free: {report["observed_free_voxels"]:,} voxels · occupied: {report["occupied_voxels"]:,} · unknown: {report["unknown_voxels"]:,}. Unknown areas remain unobserved.')
        self.map_folder = str(Path(map_path).parent)
        self.open_result.setEnabled(True)
        self.capture_status.setText('Map built. Check coverage and unknown space before relying on it.')

    def rebuild_failed(self, message):
        self.capture_status.setText('Map build failed: ' + message)
        QMessageBox.warning(self, 'Could not build the map', message + '\n\nAdd another registered view if coverage is incomplete, then try again.')

    def rebuild_finished(self):
        self.capture_button.setEnabled(len(self.scan_paths) < 20)
        self.preview_button.setEnabled(True)
        self.build_button.setEnabled(bool(self.scan_paths))

    def open_map_folder(self):
        folder = getattr(self, 'map_folder', '')
        if folder: QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def save_tag_sheet(self):
        try:
            rows = self._printable_tag_rows()
            import cv2
            from PIL import Image, ImageDraw
            if not hasattr(cv2, 'aruco'): raise ValueError('This OpenCV build does not include AprilTag generation.')
            dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
            dpi = 300
            page_w, page_h = round(8.5 * dpi), round(11 * dpi)
            pages = []
            for row in rows:
                side = round(row['size_m'] / .0254 * dpi)
                if side <= 0 or side > page_w - 2 * round(.35 * dpi):
                    raise ValueError(f'Tag {row["id"]} is too large for a letter page at 100% scale.')
                marker = cv2.aruco.generateImageMarker(dictionary, row['id'], min(1200, max(400, side)))
                marker = Image.fromarray(marker).convert('RGB').resize((side, side), Image.Resampling.NEAREST)
                page = Image.new('RGB', (page_w, page_h), 'white')
                left = (page_w - side) // 2; top = round(.55 * dpi)
                page.paste(marker, (left, top))
                draw = ImageDraw.Draw(page)
                y = top + side + round(.25 * dpi)
                draw.text((round(.5 * dpi), y), f'AprilTag 36h11 · ID {row["id"]} · black square {row["size_m"]:.4f} m', fill='black')
                y += round(.35 * dpi)
                draw.text((round(.5 * dpi), y), 'Print at 100% / actual size. Measure the outer black square after printing.', fill='black')
                # A separately measured 100 mm reference line reveals print scaling.
                y += round(.35 * dpi)
                x0, x1 = round(.5 * dpi), round(.5 * dpi) + round(.1 / .0254 * dpi)
                draw.line((x0, y, x1, y), fill='black', width=3)
                draw.line((x0, y-round(.05*dpi), x0, y+round(.05*dpi)), fill='black', width=3)
                draw.line((x1, y-round(.05*dpi), x1, y+round(.05*dpi)), fill='black', width=3)
                draw.text((x1 + round(.1 * dpi), y-round(.08*dpi)), '100 mm check', fill='black')
                pages.append(page)
            documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
            start = Path(documents) / f'{self.map_id.text().strip() or "room"}-april-tags.pdf' if documents else Path.home() / 'april-tags.pdf'
            path, _ = QFileDialog.getSaveFileName(self, 'Save AprilTag sheet', str(start), 'PDF files (*.pdf)')
            if not path: return
            if not path.lower().endswith('.pdf'): path += '.pdf'
            pages[0].save(path, 'PDF', resolution=dpi, save_all=True, append_images=pages[1:])
            QMessageBox.information(self, 'AprilTag sheet saved', f'Saved {len(pages)} printable tag(s). Print at 100% / actual size and verify the black square and 100 mm line with a ruler before surveying them.')
        except Exception as error:
            QMessageBox.warning(self, 'Could not create AprilTag sheet', str(error))

    def closeEvent(self, event):
        busy = any(worker and worker.isRunning() for worker in (self.capture_worker, self.rebuild_worker))
        if busy:
            QMessageBox.information(self, 'Work is still running', 'Wait for the D435 capture or map build to finish before closing this window.')
            event.ignore(); return
        if self.preview_worker and self.preview_worker.isRunning():
            self.preview_worker.requestInterruption()
            self.preview_worker.wait(2000)
        event.accept()


def main():
    """Open the separate room-mapping app; this does not start the demo server."""
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    window = GuidedRoomMapper()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
