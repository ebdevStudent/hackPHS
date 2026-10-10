"""Standalone guided room-mapper checks; no physical D435 used."""
import numpy as np
import pytest
from pathlib import Path
from PySide6.QtWidgets import QComboBox, QFileDialog, QMessageBox, QPushButton, QTableWidgetItem

from ball_demo import mapping
from ball_demo import room_mapper
from ball_demo.navigation_fixtures import example_bundle
from ball_demo.room_mapper import (
    CaptureWorker, FACING_ROTATIONS, GuidedRoomMapper, PreviewWorker,
    RebuildWorker, _sdk_name, build_room_setup,
)


def tag_rows():
    return [
        {'id': 3, 'size_m': .12, 'x': 0., 'y': .5, 'z': 1.2, 'facing': 'Into room from x=0 wall (+X)'},
        {'id': 8, 'size_m': .12, 'x': 2., 'y': 1.5, 'z': 1.2, 'facing': 'Into room from x=max wall (-X)'},
    ]


def fill_dialog(dialog, output):
    dialog.map_id.setText('practice_room')
    dialog.room_x.setValue(2.)
    dialog.room_y.setValue(2.)
    dialog.room_z.setValue(2.)
    dialog.output_path.setText(str(output))
    for row in tag_rows():
        dialog.add_tag_row()
        index = dialog.tag_table.rowCount() - 1
        for column, value in enumerate((row['id'], row['size_m'], row['x'], row['y'], row['z'])):
            dialog.tag_table.setItem(index, column, QTableWidgetItem(str(value)))
        dialog.tag_table.cellWidget(index, 5).setCurrentText(row['facing'])


def test_gui_room_setup_builds_measured_tag_frames_and_station_contract():
    station, survey, cells = build_room_setup('practice_room', [2., 2., 2.], .1, .1, 4., tag_rows(), 'Tape measure, tag centers from floor corner.')
    assert cells == 8000
    assert station.permitted.maximum == [2., 2., 2.] and station.example is False
    assert survey.example is False and [tag.id for tag in survey.tags] == [3, 8]
    for tag, facing in zip(survey.tags, (FACING_ROTATIONS['Into room from x=0 wall (+X)'], FACING_ROTATIONS['Into room from x=max wall (-X)'])):
        rotation = np.array(tag.map_from_tag)[:3, :3]
        assert np.allclose(rotation, facing) and np.allclose(rotation.T @ rotation, np.eye(3))
        assert np.isclose(np.linalg.det(rotation), 1.)


@pytest.mark.parametrize('rows,dims,voxel,match', [
    (tag_rows()[:1], [2., 2., 2.], .1, 'at least two'),
    ([tag_rows()[0], {**tag_rows()[1], 'id': 3}], [2., 2., 2.], .1, 'Duplicate'),
    ([tag_rows()[0], {**tag_rows()[1], 'x': 2.1}], [2., 2., 2.], .1, 'inside'),
    (tag_rows(), [5., 5., 3.], .05, '100,000'),
    ([{**tag_rows()[0], 'facing': 'choose'}, tag_rows()[1]], [2., 2., 2.], .1, 'choose which wall'),
])
def test_gui_room_setup_rejects_incomplete_or_unsafe_survey(rows, dims, voxel, match):
    with pytest.raises(ValueError, match=match):
        build_room_setup('practice_room', dims, voxel, .1, 4., rows, 'operator-entered')


@pytest.mark.parametrize('map_id,dims,voxel,uncertainty,depth,rows,note,match', [
    ('not a valid ID', [2., 2., 2.], .1, .1, 4., tag_rows(), 'measured', 'Map ID'),
    ('room', [2., 2.], .1, .1, 4., tag_rows(), 'measured', 'dimensions'),
    ('room', [2., 2., 2.], 0., .1, 4., tag_rows(), 'measured', 'must be positive'),
    ('room', [2., 2., 2.], .1, .1, 4., [{**tag_rows()[0], 'id': True}, tag_rows()[1]], 'measured', 'integer'),
    ('room', [2., 2., 2.], .1, .1, 4., [{**tag_rows()[0], 'size_m': float('inf')}, tag_rows()[1]], 'measured', 'finite'),
    ('room', [2., 2., 2.], .1, .1, 4., tag_rows(), '', 'short note'),
])
def test_gui_room_setup_rejects_bad_fields(map_id, dims, voxel, uncertainty, depth, rows, note, match):
    with pytest.raises(ValueError, match=match):
        build_room_setup(map_id, dims, voxel, uncertainty, depth, rows, note)


def test_guided_room_mapper_edits_tags_and_creates_setup_without_device(qapp, tmp_path):
    dialog = GuidedRoomMapper()
    fill_dialog(dialog, tmp_path / 'scan-session')
    assert isinstance(dialog.tag_table.cellWidget(0, 5), QComboBox)
    station, survey, cells = dialog._validated_setup()
    assert station.map_id == 'practice_room' and survey.tags[0].id == 3 and cells == 8000
    assert any(button.text() == 'Create printable tag sheet…' for button in dialog.findChildren(QPushButton))
    dialog.close()


def test_standalone_entrypoint_shows_its_own_window(qapp, monkeypatch):
    shown = []

    class FakeApp:
        def __init__(self, *_):
            pass

        @staticmethod
        def instance():
            return None

        def exec(self):
            return 7

    class FakeWindow:
        def show(self):
            shown.append(True)

    from PySide6 import QtWidgets
    monkeypatch.setattr(QtWidgets, 'QApplication', FakeApp)
    monkeypatch.setattr(room_mapper, 'GuidedRoomMapper', FakeWindow)
    assert room_mapper.main() == 7
    assert shown == [True]


def test_gui_printable_tag_sheet_keeps_page_artifact_separate(qapp, tmp_path, monkeypatch):
    import cv2
    from types import SimpleNamespace
    dialog = GuidedRoomMapper()
    for row in tag_rows():
        dialog.add_tag_row()
        index = dialog.tag_table.rowCount() - 1
        for column, value in enumerate((row['id'], row['size_m'])):
            dialog.tag_table.setItem(index, column, QTableWidgetItem(str(value)))
    fake_aruco = SimpleNamespace(DICT_APRILTAG_36h11=1, getPredefinedDictionary=lambda *_: object(),
                                 generateImageMarker=lambda _dict, _id, size: np.zeros((size, size), np.uint8))
    monkeypatch.setattr(cv2, 'aruco', fake_aruco, raising=False)
    output = tmp_path / 'tags.pdf'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(output), 'PDF files (*.pdf)'))
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: QMessageBox.StandardButton.Ok)
    dialog.save_tag_sheet()
    assert output.read_bytes().startswith(b'%PDF')
    dialog.close()


def test_workers_forward_capture_callbacks_and_preserve_errors(qapp, tmp_path, monkeypatch):
    station, survey, _ = build_room_setup('practice_room', [2., 2., 2.], .1, .1, 4., tag_rows(), 'measured')
    seen = {}
    def fake_capture(station_arg, output, frames, *, registration_survey, on_frame, on_progress, on_registration):
        output.mkdir()
        seen.update(station=station_arg, frames=frames, survey=registration_survey)
        on_frame(np.zeros((8, 8, 3), np.uint8)); on_progress(1, frames)
        on_registration({'stable': True, 'tag_ids': [3, 8], 'uncertainty_m': .05})
        (output / 'scan.json').write_text('{}')
    monkeypatch.setattr(mapping, 'capture_d435', fake_capture)
    worker = CaptureWorker(station, survey, tmp_path / 'capture', 30)
    frames, progress, registration, done, failed = [], [], [], [], []
    worker.frame.connect(frames.append); worker.progress.connect(lambda a,b: progress.append((a,b)))
    worker.registration.connect(registration.append); worker.done.connect(done.append); worker.failed.connect(failed.append)
    worker.run()
    assert seen['station'].map_id == 'practice_room' and seen['survey'] == survey and seen['frames'] == 30
    assert len(frames) == 1 and progress == [(1, 30)] and registration[0]['stable']
    assert done == [str(tmp_path / 'capture' / 'scan.json')] and not failed

    def fail(*args, **kwargs): raise ValueError('synthetic capture failure')
    monkeypatch.setattr(mapping, 'capture_d435', fail)
    failed_worker = CaptureWorker(station, survey, tmp_path / 'failed')
    errors = []; failed_worker.failed.connect(errors.append); failed_worker.run()
    assert errors == ['synthetic capture failure']


def test_preview_worker_reports_missing_sdk_and_camera_name_is_strict(qapp, monkeypatch):
    _, survey, _ = build_room_setup('practice_room', [2., 2., 2.], .1, .1, 4., tag_rows(), 'measured')
    monkeypatch.setitem(__import__('sys').modules, 'pyrealsense2', None)
    worker = PreviewWorker(survey, .1)
    failures=[]; worker.failed.connect(failures.append); worker.run()
    assert failures and 'SDK is unavailable' in failures[0]
    class Sdk: camera_info = type('CameraInfo', (), {'name': 'name'})
    assert _sdk_name(type('Device', (), {'get_info': lambda *_: ' Intel RealSense D435 '})(), Sdk) == 'Intel RealSense D435'
    with pytest.raises(ValueError, match='Expected an Intel RealSense D435'):
        _sdk_name(type('Device', (), {'get_info': lambda *_: 'D435i'})(), Sdk)


def test_room_mapper_capture_and_map_buttons_save_new_artifacts(qapp, tmp_path, monkeypatch):
    dialog = GuidedRoomMapper()
    fill_dialog(dialog, tmp_path / 'new-session')
    dialog.continue_to_capture()
    assert dialog.tabs.currentWidget() is dialog.capture_tab and not (tmp_path / 'new-session').exists()

    def fake_capture(station_arg, output, frames, *, registration_survey, on_frame, on_progress, on_registration):
        output.mkdir()
        on_frame(np.zeros((8, 8, 3), np.uint8)); on_progress(frames, frames)
        on_registration({'stable': True, 'tag_ids': [3, 8], 'uncertainty_m': .05})
        (output / 'scan.json').write_text('{}')
    monkeypatch.setattr(mapping, 'capture_d435', fake_capture)
    monkeypatch.setattr(CaptureWorker, 'start', lambda self: self.run())
    dialog.capture_view()
    session = tmp_path / 'new-session'
    assert (session / 'survey.json').exists() and len(dialog.scan_paths) == 1
    assert (session / 'capture-01' / 'scan.json').exists() and dialog.build_button.isEnabled()

    bundle_map = example_bundle().map
    report = {'observed_free_voxels': 5, 'occupied_voxels': 2, 'unknown_voxels': 3}
    monkeypatch.setattr(room_mapper, 'rebuild_scans', lambda paths: (bundle_map, report))
    monkeypatch.setattr(RebuildWorker, 'start', lambda self: self.run())
    dialog.build_map()
    assert (session / 'map-01' / 'map.json').exists() and (session / 'map-01' / 'report.json').exists()
    assert 'Observed free: 5 voxels' in dialog.map_result.text() and dialog.open_result.isEnabled()
    dialog.close()


def test_room_mapper_handles_cancelled_folder_and_preview_capture_handoff(qapp, tmp_path, monkeypatch):
    dialog = GuidedRoomMapper()
    original = dialog.output_path.text()
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *args: '')
    dialog.choose_output_folder(); assert dialog.output_path.text() == original
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *args: str(tmp_path))
    dialog.choose_output_folder(); assert Path(dialog.output_path.text()).parent == tmp_path

    class RunningPreview:
        def __init__(self): self.stopped = False
        def isRunning(self): return True
        def requestInterruption(self): self.stopped = True
    worker = RunningPreview(); dialog.preview_worker = worker
    dialog._begin_capture = lambda: setattr(dialog, 'capture_started', True)
    dialog.capture_view()
    assert worker.stopped and dialog.capture_after_preview
    dialog.preview_finished()
    assert dialog.capture_started and not dialog.capture_after_preview


def test_room_mapper_reports_capture_and_rebuild_failures_and_opens_folder(qapp, tmp_path, monkeypatch):
    dialog = GuidedRoomMapper()
    messages=[]
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: messages.append(args[1:3]))
    dialog.capture_failed('lost tag'); assert 'lost tag' in dialog.capture_status.text() and messages
    dialog.rebuild_failed('no free voxels'); assert 'no free voxels' in dialog.capture_status.text()
    opened=[]
    monkeypatch.setattr(room_mapper.QDesktopServices, 'openUrl', lambda url: opened.append(url.toString()))
    dialog.map_folder = str(tmp_path)
    dialog.open_map_folder(); assert opened and str(tmp_path) in opened[0]
    dialog.capture_finished(); dialog.rebuild_finished()
    dialog.close()


def test_rebuild_worker_writes_report_and_surfaces_failure(qapp, tmp_path, monkeypatch):
    mapped = example_bundle().map
    report = {'observed_free_voxels': 1}
    monkeypatch.setattr(room_mapper, 'rebuild_scans', lambda paths: (mapped, report))
    worker = RebuildWorker(['unused'], tmp_path / 'map-out')
    done=[]; errors=[]; worker.done.connect(lambda path, value: done.append((path,value)))
    worker.failed.connect(errors.append); worker.run()
    assert not errors and done[0][1] == report
    assert (tmp_path / 'map-out' / 'map.json').exists() and (tmp_path / 'map-out' / 'report.json').exists()
    failing = RebuildWorker([], tmp_path / 'failed-map')
    failing_errors=[]; failing.failed.connect(failing_errors.append)
    monkeypatch.setattr(room_mapper, 'rebuild_scans', lambda paths: (_ for _ in ()).throw(ValueError('bad scans')))
    failing.run(); assert failing_errors == ['bad scans']
