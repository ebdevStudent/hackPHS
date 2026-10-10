"""Native navigation validation, display, deliberate requests and stale clearing."""
import copy
import json
import time

import pytest
from PySide6.QtWidgets import QDialog, QFileDialog, QLineEdit

from ball_demo import desktop
from ball_demo.navigation_fixtures import example_bundle, example_mission, example_recording
from ball_demo.mission import MissionRunner
from ball_demo.navigation_replay import replay
from test_desktop import state, Network

pytestmark=pytest.mark.desktop


def nav_state():
    return next(s for s in replay(example_recording())['samples'] if s['guidance_enabled'])


@pytest.fixture
def window(qapp,monkeypatch):
    monkeypatch.setattr(desktop.ApiClient,'poll',lambda self:None)
    w=desktop.Workstation(url='http://127.0.0.1:1')
    w.api.timer.stop(); w.api.network=Network(); w.authorized=True
    yield w
    w.authorized=False; w.api.url=''; w.api.timer.stop(); w.freshness.stop(); w.close(); w.deleteLater(); qapp.processEvents()


def test_native_navigation_readouts_route_and_stale_clear(window):
    nav=nav_state()
    window.update_state(state(navigation=nav))
    assert 'SYNTHETIC estimate' in window.navigation_pose.text()
    assert window.navigation_route.topLevelItemCount()==len(nav['route'])
    assert 'ARM/DISARM' in window.navigation_authority.text()
    window.api.last_ok=time.monotonic()-1.
    window.check_freshness()
    assert window.navigation_route.topLevelItemCount()==0 and 'suppressed' in window.navigation_status.text()
    assert not window.navigation_resume.isEnabled()
    window.update_state(state(navigation=None))
    assert window.navigation_waypoint.text().endswith('—')


@pytest.mark.parametrize('mutation', ['nan','reflection','source','timing','physical','inactive','registration','missing_age','age_without_pose'])
def test_native_rejects_complete_nested_navigation_before_widgets(mutation):
    nav=copy.deepcopy(nav_state())
    if mutation=='nan': nav['pose']['uncertainty_m']=float('nan')
    if mutation=='reflection': nav['pose']['map_from_aircraft'][2][2]=-1.
    if mutation=='source': nav['pose']['source']='aircraft_telemetry'
    if mutation=='timing': nav['pose']['timing']['exposure_s']=100.
    if mutation=='physical': nav['physical_output']=True
    if mutation=='inactive': nav['guidance_enabled']=False
    if mutation=='missing_age': nav['pose_age_s']=None
    if mutation=='age_without_pose': nav.update(pose=None,guidance_enabled=False,route=[],next_waypoint=None)
    if mutation=='registration': nav['map_id']='wrong'
    nav.pop('t')
    with pytest.raises(ValueError): desktop.validate_snapshot(state(navigation=nav))


@pytest.mark.parametrize('text,expected', [('1.0 1.5 1.2',[1.,1.5,1.2]),('nan 1 1',None),('1 2',None)])
def test_native_goal_dialog_emits_only_finite_metric_request(window,monkeypatch,text,expected):
    calls=[]
    monkeypatch.setattr(window.api,'command',lambda *args:calls.append(args))
    def execute(dialog):
        dialog.findChild(QLineEdit).setText(text)
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',execute)
    window.choose_navigation_goal()
    assert calls==([('navigation',{'action':'goal','goal':expected})] if expected else [])
    window.authorized=False; window.choose_navigation_goal()
    assert len(calls)==(1 if expected else 0)


def test_native_goal_cancel_and_bundle_import_validation(window,monkeypatch,tmp_path):
    calls=[]
    monkeypatch.setattr(window.api,'command',lambda *args:calls.append(args))
    monkeypatch.setattr(QDialog,'exec',lambda d:QDialog.DialogCode.Rejected)
    window.choose_navigation_goal(); assert not calls
    path=tmp_path/'bundle.json'; path.write_text(example_recording().bundle.model_dump_json())
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *args:(str(path),''))
    window.import_navigation_bundle(); assert calls[0][0]=='navigation/bundle'
    path.write_text('{}'); window.import_navigation_bundle(); assert len(calls)==1
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *args:('',''))
    window.import_navigation_bundle(); assert len(calls)==1
    window.authorized=False; window.import_navigation_bundle(); assert len(calls)==1


def test_native_guidance_stop_cannot_be_overwritten_by_queued_restore(window):
    c=window.api
    c.command('navigation',{'action':'resume'})
    c.command('navigation',{'action':'disable'})
    c.command('navigation',{'action':'resume'})
    assert c.queued['/api/operator/navigation'][0]['action']=='disable'
    response=c.network.calls[0][2]
    response.body=json.dumps(state()).encode(); response.finished.emit()
    assert json.loads(c.network.calls[-1][1])['action']=='disable'


def test_native_restore_disable_buttons_request_guidance_only(window,monkeypatch):
    calls=[]
    monkeypatch.setattr(window.api,'command',lambda *args:calls.append(args))
    window.update_state(state(navigation=nav_state()))
    window.navigation_resume.click(); window.navigation_disable.click()
    assert calls==[('navigation',{'action':'resume'}),('navigation',{'action':'disable'})]


def test_native_mission_state_is_validated_rendered_and_actions_are_gated(window,monkeypatch):
    runner=MissionRunner(example_mission(),example_bundle())
    ready=runner.snapshot()
    nav=nav_state(); nav.pop('t'); nav['mission']=ready
    desktop.validate_snapshot(state(navigation=nav))
    window.update_state(state(navigation=nav))
    assert 'ready' in window.navigation_mission.text() and '1/1' in window.navigation_mission.text()
    assert window.navigation_mission_start.isEnabled()
    assert not window.navigation_mission_advance.isEnabled()
    assert window.navigation_mission_abort.isEnabled()

    calls=[]
    monkeypatch.setattr(window.api,'command',lambda *args:calls.append(args))
    window.navigation_mission_start.click(); window.navigation_mission_abort.click()
    assert calls==[('navigation',{'action':'mission_start'}),('navigation',{'action':'mission_abort'})]

    runner.status='target_complete'; runner.snapshot_status='saved'
    runner.snapshot_sha256='a'*64; runner.snapshot_source='synthetic'
    nav['mission']=runner.snapshot()
    window.update_state(state(navigation=nav))
    assert 'snapshot saved' in window.navigation_mission.text()
    assert not window.navigation_mission_start.isEnabled()
    assert window.navigation_mission_advance.isEnabled()
    window.navigation_mission_advance.click()
    assert calls[-1]==('navigation',{'action':'mission_advance'})

    bad=copy.deepcopy(nav); bad['mission']['snapshot_sha256']='bad'
    with pytest.raises(ValueError): desktop.validate_snapshot(state(navigation=bad))


def test_native_mission_import_requires_authorization_and_valid_json(window,monkeypatch,tmp_path):
    calls=[]
    monkeypatch.setattr(window.api,'command',lambda *args:calls.append(args))
    path=tmp_path/'mission.json'; path.write_text(example_mission().model_dump_json())
    selected={'path':str(path)}
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *args:(selected['path'],''))
    window.authorized=False
    window.import_navigation_mission()
    assert not calls and 'Operator access' in window.statusBar().currentMessage()

    window.authorized=True
    window.import_navigation_mission()
    assert len(calls)==1 and calls[0][0]=='navigation/mission'
    path.write_text('{ invalid json')
    window.import_navigation_mission()
    assert len(calls)==1
    path.write_bytes(b' '*1_000_001)
    window.import_navigation_mission()
    assert len(calls)==1
    selected['path']=''
    window.import_navigation_mission()
    assert len(calls)==1


def test_actual_offscreen_latency_flash_disc_is_detectable(qapp):
    from ball_demo.latency import QtFlash
    from ball_demo.vision import Detector
    from ball_demo.config import Settings
    import numpy as np
    flash=QtFlash()
    try:
        flash(True); qapp.processEvents()
        image=flash.window.grab().toImage().convertToFormat(__import__('PySide6.QtGui',fromlist=['QImage']).QImage.Format.Format_RGB888)
        rgb=np.array(image.bits(),dtype=np.uint8).reshape(image.height(),image.bytesPerLine())[:,:image.width()*3].reshape(image.height(),image.width(),3)
        import cv2
        frame=cv2.resize(rgb[:,:,::-1],(640,480))
        settings=Settings(); settings.max_area=200000
        assert Detector().detect(frame,settings) is not None
        flash(False); qapp.processEvents()
        image=flash.window.grab().toImage()
        assert image.pixelColor(image.width()//2,image.height()//2).red()==0
    finally:flash.close()
