"""Navigation isolation, API authorization, real worker epochs and replay logging."""
import copy
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ball_demo.api import create_app
from ball_demo.engine import Engine
from ball_demo.localization import Timing
from ball_demo.navigation import Planner
from ball_demo.navigation_visibility import VisibilityPlanner
from ball_demo.navigation_fixtures import example_bundle, example_mission, example_recording, observations_for, example_pose
from ball_demo.navigation_replay import Input, Recorder, Recording, load_recording, replay
from ball_demo.navigation_runtime import NavigationRuntime
from ball_demo.sources import Frame

AUTH={'Authorization':'Bearer token'}
ROOT=Path(__file__).resolve().parents[2]


def wait_for(predicate,timeout=3):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if predicate(): return
        time.sleep(.01)
    raise AssertionError('Condition did not become true')


def test_baseline_never_imports_optional_navigation_modules():
    code="from ball_demo.engine import Engine; import sys; assert not any(n in sys.modules for n in ('ball_demo.mapping','ball_demo.localization','ball_demo.navigation','pyrealsense2'))"
    subprocess.run([sys.executable,'-c',code],cwd=ROOT/'software',check=True)


def test_paced_navigation_replay_preserves_manual_yaw_and_records_replay(tmp_path):
    recording=example_recording()
    engine=Engine(tmp_path,navigation_bundle=recording.bundle,navigation_recording=recording)
    engine.start()
    try:
        wait_for(lambda:engine.snapshot()['navigation']['guidance_enabled'])
        state=engine.snapshot()
        assert state['state']=='MANUAL' and state['yaw']==0 and not state['enabled']
        assert state['navigation']['control_authority']=='advisory_only' and state['physical_telemetry'] is None and not state['physical_output']
        wait_for(lambda:not engine.snapshot()['navigation']['guidance_enabled'],timeout=2)
    finally: engine.stop()
    paths=list(engine.session.path.glob('navigation-*.jsonl'))
    assert len(paths)==1
    restored=load_recording(paths[0])
    assert restored.bundle.digest==recording.bundle.digest
    assert replay(restored)['physical_output'] is False
    assert engine.health()['logging_errors']==0


def test_planner_hang_cannot_block_yaw_control_or_publish_late_route(tmp_path,monkeypatch):
    entered,release=threading.Event(),threading.Event()
    original=VisibilityPlanner.plan
    def blocked(self,*args,**kw):
        entered.set(); release.wait(2.)
        return original(self,*args,**kw)
    monkeypatch.setattr(VisibilityPlanner,'plan',blocked)
    r=example_recording()
    # No later deliberate restore: test rejects a late result from the stalled
    # request, independently of the fixture's separate recovery demonstration.
    r.events=[event for event in r.events if not (event.kind=='resume' and event.t>1.2)]
    engine=Engine(tmp_path,navigation_bundle=r.bundle,navigation_recording=r)
    engine.start()
    try:
        assert entered.wait(2.)
        sequence=engine.bridge.seq
        epoch=engine.navigation.epoch
        time.sleep(.3)
        state=engine.snapshot()
        assert engine.bridge.seq>=sequence+3 and engine.processed>=3
        assert not state['navigation']['guidance_enabled'] and state['navigation']['route']==[]
        assert engine.navigation.epoch>epoch
        release.set()
        time.sleep(.15)
        assert not engine.snapshot()['navigation']['guidance_enabled']
        assert engine.controller.state=='MANUAL' and engine.controller.yaw==0
    finally: release.set(); engine.stop()


def test_navigation_disable_cancels_pending_restore_and_snapshot_staleness(tmp_path):
    b=example_bundle(); runtime=NavigationRuntime(b,tmp_path/'nav.jsonl')
    runtime.command('resume'); runtime.command('disable')
    assert not runtime.commands and runtime.pending=='operator disabled guidance'
    assert runtime.snapshot(1.)['route']==[]
    runtime.published_at=0.
    old=runtime.epoch
    assert not runtime.snapshot(1.)['guidance_enabled'] and runtime.epoch>old
    with pytest.raises(ValueError): runtime.command('fly')
    with pytest.raises(ValueError,match='Invalid goal heading'):
        runtime.command('goal',[1.,1.,1.],heading_rad=True)
    with pytest.raises(ValueError,match='Unknown goal tag'):
        runtime.command('goal',[1.,1.,1.],tag_id=22)
    with pytest.raises(ValueError,match='requires goal action'):
        runtime.command('resume',heading_rad=0.)
    for i in range(32): runtime.command('goal',[1.,1.,1.])
    with pytest.raises(ValueError,match='queue'): runtime.command('resume')
    with pytest.raises(ValueError): NavigationRuntime(b,tmp_path/'other.jsonl',example_recording().model_copy(update={'bundle':b.model_copy(update={'bundle_id':'different'})}))


def test_camera_frame_timing_rejects_unknown_exposure_age_and_example_geometry(tmp_path,monkeypatch):
    b=example_bundle(); runtime=NavigationRuntime(b,tmp_path/'nav.jsonl')
    frame=Frame(np.zeros((480,640,3),np.uint8),10.,0,{'exposure_s':9.9})
    with pytest.raises(ValueError,match='Example'): runtime.frame_input(frame,'camera',0,10.)
    data=b.model_dump()
    for key in ('map','survey','calibration'): data[key]['example']=False
    from ball_demo.map_io import Bundle
    runtime=NavigationRuntime(Bundle.model_validate(data),tmp_path/'measured.jsonl')
    from ball_demo.localization import Localizer
    runtime.localizer=Localizer(runtime.bundle)
    monkeypatch.setattr(runtime.localizer,'detect',lambda image:observations_for(b,example_pose()))
    event=runtime.frame_input(frame,'camera',0,10.01)
    assert event.timing.provenance=='host_read' and event.timing.exposure_s is None
    with pytest.raises(ValueError,match='Unknown'): event.timing.oldest_exposure()
    event=runtime.frame_input(frame,'recorded',1,10.02)
    assert event.source=='recorded_estimate' and event.timing.provenance=='host_read'
    event=runtime.frame_input(frame,'synthetic',2,10.03)
    assert event.source=='synthetic_estimate' and event.timing.exposure_s==10.
    with pytest.raises(ValueError,match='Unknown navigation frame source'):
        runtime.frame_input(frame,'unrecognized',3,10.04)


def test_mission_snapshot_save_is_private_and_rejects_invalid_frames(tmp_path,monkeypatch):
    import os
    import stat
    from ball_demo.navigation import Advisory
    from ball_demo.mission import MissionRunner

    bundle=example_bundle(); runtime=NavigationRuntime(bundle,tmp_path/'nav.jsonl')
    runtime.advisory=Advisory(bundle)
    runner=MissionRunner(example_mission(bundle),bundle)
    runner.status='snapshot_pending'; runner.snapshot_status='requested'
    runtime.advisory.mission_runner=runner
    frame=Frame(np.zeros((48,64,3),np.uint8),time.monotonic(),0,{})
    saved=runtime.save_mission_snapshot(frame,'synthetic')
    directory=tmp_path/'navigation_snapshots'
    files=list(directory.glob('*.jpg'))
    assert saved.kind=='snapshot_saved' and saved.snapshot_source=='synthetic'
    assert len(files)==1 and stat.S_IMODE(directory.stat().st_mode)==0o700
    assert stat.S_IMODE(files[0].stat().st_mode)==0o600

    runner.status='running'
    assert runtime.save_mission_snapshot(frame,'synthetic') is None
    runner.status='snapshot_pending'; runner.snapshot_status='requested'
    for invalid in (None,Frame(np.zeros((32,32),np.uint8),1.,1,{}),
                    Frame(np.zeros((32,32,3),np.float32),1.,1,{})):
        with pytest.raises(ValueError,match='valid frame'):
            runtime.save_mission_snapshot(invalid,'synthetic')
    with pytest.raises(ValueError,match='Unknown mission snapshot source'):
        runtime.save_mission_snapshot(frame,'unrecognized')
    monkeypatch.setattr(cv2,'imencode',lambda *args,**kwargs:(False,None))
    with pytest.raises(ValueError,match='Could not encode'):
        runtime.save_mission_snapshot(frame,'synthetic')


def test_live_worker_saves_requested_mission_frame_and_survives_save_failure(tmp_path,monkeypatch):
    from ball_demo.localization import Localizer
    bundle=example_bundle(); runtime=NavigationRuntime(bundle,tmp_path/'mission.jsonl')
    target=example_mission(bundle).targets[0].viewing_position_m
    feed=threading.Event(); state={'index':0}
    monkeypatch.setattr(Localizer,'detect',lambda self,image:observations_for(bundle,example_pose(target)))
    def get_frame():
        if not feed.is_set(): return None,None,'synthetic',None
        state['index']+=1
        captured=time.monotonic()
        return Frame(np.zeros((480,640,3),np.uint8),captured,state['index'],{}),(0,state['index']),'synthetic',None
    runtime.get_frame=get_frame
    runtime.start()
    try:
        wait_for(lambda:hasattr(runtime,'advisory'))
        runtime.configure_mission(example_mission(bundle))
        wait_for(lambda:(runtime.snapshot(time.monotonic()).get('mission') or {}).get('status')=='ready')
        runtime.command('mission_start')
        feed.set()
        wait_for(lambda:(runtime.snapshot(time.monotonic()).get('mission') or {}).get('status')=='target_complete')
        mission=runtime.snapshot(time.monotonic())['mission']
        saved=list((tmp_path/'navigation_snapshots').glob('*.jpg'))
        assert mission['snapshot_status']=='saved' and mission['snapshot_source']=='synthetic'
        assert len(saved)==1 and runtime.thread.is_alive()
    finally: runtime.stop()

    # A failed disk/encoder path faults the mission safely. If a concurrent
    # state transition has already removed the pending request, that secondary
    # failure is swallowed and the worker still remains alive.
    runtime=NavigationRuntime(bundle,tmp_path/'failed-mission.jsonl')
    feed=threading.Event(); state['index']=0
    runtime.get_frame=get_frame
    runtime.start()
    try:
        wait_for(lambda:hasattr(runtime,'advisory'))
        runtime.configure_mission(example_mission(bundle))
        wait_for(lambda:(runtime.snapshot(time.monotonic()).get('mission') or {}).get('status')=='ready')
        runtime.command('mission_start')
        runtime.save_mission_snapshot=lambda *args:(_ for _ in ()).throw(OSError('injected snapshot failure'))
        runtime.advisory.mission_snapshot_failed=lambda:(_ for _ in ()).throw(ValueError('already transitioned'))
        feed.set()
        wait_for(lambda:(runtime.snapshot(time.monotonic()).get('mission') or {}).get('status')=='snapshot_pending')
        assert runtime.thread.is_alive()
    finally: runtime.stop()


def test_replay_worker_rejects_invalid_mission_transition_without_stopping(tmp_path):
    bundle=example_bundle(); mission=example_mission(bundle)
    events=[Input(t=1.,kind='mission',mission=mission),Input(t=1.01,kind='mission_advance')]
    recording=Recording(schema_version=1,label='SYNTHETIC invalid mission transition',bundle=bundle,
                        bundle_sha256=bundle.digest,physical_output=False,events=events)
    runtime=NavigationRuntime(bundle,tmp_path/'rejected.jsonl',recording)
    runtime.start()
    try:
        wait_for(lambda:'command rejected' in runtime.snapshot(time.monotonic())['status'])
        assert runtime.thread.is_alive()
        assert runtime.snapshot(time.monotonic())['mission']['status']=='ready'
    finally:runtime.stop()


def test_capture_failure_event_cannot_be_overwritten_by_recovery(tmp_path,monkeypatch):
    r=example_recording(); engine=Engine(tmp_path,navigation_bundle=r.bundle)
    class Source:
        eof=False
        def read(self): raise RuntimeError('test capture failure')
        def close(self): pass
    monkeypatch.setattr(engine,'open_source',lambda *args:Source())
    engine.start()
    try:
        wait_for(lambda:engine.navigation.epoch>=2)
        assert engine.snapshot()['navigation']['route']==[]
        assert not engine.controller.enabled
    finally: engine.stop()


def test_source_switch_rejects_old_navigation_epoch_and_bundle_replacement(tmp_path):
    r=example_recording(); engine=Engine(tmp_path,navigation_bundle=r.bundle,navigation_recording=r)
    engine.start()
    try:
        wait_for(lambda:engine.snapshot()['navigation']['guidance_enabled'])
        old=engine.navigation; epoch=old.epoch
        engine.set_source({'kind':'synthetic','scenario':'centered'})
        assert old.epoch>epoch and not engine.snapshot()['navigation']['guidance_enabled']
        engine.configure_navigation(r.bundle)
        assert engine.navigation is not old and old.stop_event.is_set()
        assert not engine.snapshot()['navigation']['guidance_enabled']
    finally: engine.stop()


@pytest.mark.parametrize('path,data', [('/api/operator/navigation',{'action':'resume'}),('/api/operator/navigation',{'action':'disable'}),('/api/operator/navigation',{'action':'goal','goal':[1.,1.,1.]}),('/api/operator/navigation/bundle',{'bundle':example_bundle().model_dump()})])
def test_every_navigation_mutation_requires_token(tmp_path,path,data):
    e=Engine(tmp_path)
    try:
        c=TestClient(create_app(e,'token'))
        assert c.post(path,json=data).status_code==401
        assert c.post(path,json=data,headers={'Authorization':'Bearer wrong'}).status_code==401
        assert e.navigation is None and not e.controller.enabled
    finally:e.session.close(0)


@pytest.mark.parametrize('data', [{'action':True},{'action':'fly'},{'action':'resume','goal':[1.,1.,1.]},{'action':'goal'},{'action':'goal','goal':[1.,2.]},{'action':'goal','goal':[True,1.,1.]},{'action':'goal','goal':['1',1.,1.]},{'action':'disable','enabled':True}])
def test_operator_navigation_strict_types_and_unknown_fields(tmp_path,data):
    e=Engine(tmp_path); c=TestClient(create_app(e,'token'))
    try: assert c.post('/api/operator/navigation',json=data,headers=AUTH).status_code==422
    finally:e.session.close(0)


def test_navigation_api_import_and_actions_do_not_enable_yaw(tmp_path):
    e=Engine(tmp_path); c=TestClient(create_app(e,'token'))
    try:
        assert c.get('/api/navigation').json() is None
        assert c.get('/api/navigation/map').json() is None
        assert c.post('/api/operator/navigation',json={'action':'resume'},headers=AUTH).status_code==409
        assert c.post('/api/operator/navigation/bundle',json={'bundle':{}},headers=AUTH).status_code==422
        assert c.post('/api/operator/navigation/bundle',json={'bundle':example_bundle().model_dump()},headers=AUTH).status_code==200
        assert c.get('/api/navigation/map').json()['example'] is True
        assert c.post('/api/operator/navigation',json={'action':'goal','goal':[1.,1.,1.]},headers=AUTH).status_code==200
        assert c.post('/api/operator/navigation',json={'action':'disable'},headers=AUTH).status_code==200
        assert e.controller.yaw==0 and not e.controller.enabled
        response=c.post('/api/operator/navigation',content='{"action":"goal","goal":[NaN,1,1]}',headers={**AUTH,'Content-Type':'application/json'})
        assert response.status_code==422
        json.loads(response.content)
    finally:e.stop()


def test_mission_api_is_operator_only_and_rejects_early_advance_without_killing_worker(tmp_path):
    engine=Engine(tmp_path)
    with TestClient(create_app(engine,'token')) as client:
        assert client.post('/api/operator/navigation/mission',json={'mission':example_mission().model_dump()}).status_code==401
        assert client.post('/api/operator/navigation/bundle',json={'bundle':example_bundle().model_dump()},headers=AUTH).status_code==200
        mission=example_mission()
        assert client.post('/api/operator/navigation/mission',json={'mission':mission.model_dump()},headers=AUTH).status_code==200
        wait_for(lambda:(client.get('/api/navigation/mission').json() or {}).get('status')=='ready')
        assert client.post('/api/operator/navigation',json={'action':'mission_start'},headers={'Authorization':'Bearer wrong'}).status_code==401
        assert client.post('/api/operator/navigation',json={'action':'mission_start'},headers=AUTH).status_code==200
        # No source is configured in this test, so the worker correctly waits
        # for a fresh localization after accepting the start command.
        wait_for(lambda:(client.get('/api/navigation/mission').json() or {}).get('status')=='waiting_for_localization')
        assert client.post('/api/operator/navigation',json={'action':'mission_advance'},headers=AUTH).status_code==409
        wait_for(lambda:engine.navigation.thread.is_alive())
        assert engine.controller.yaw==0 and not engine.controller.enabled
        assert client.post('/api/operator/navigation',json={'action':'mission_abort'},headers=AUTH).status_code==200
        wait_for(lambda:(client.get('/api/navigation/mission').json() or {}).get('status')=='aborted')


def test_optional_runtime_worker_failure_and_logging_error_are_visible(tmp_path,monkeypatch):
    b=example_bundle()
    runtime=NavigationRuntime(b,tmp_path/'missing'/'nav.jsonl')
    runtime.get_frame=lambda:(_ for _ in ()).throw(RuntimeError('test fatal worker'))
    runtime.start()
    wait_for(lambda:runtime.thread and not runtime.thread.is_alive())
    assert runtime.logging_errors==1 and 'worker failed' in runtime.cached['status']
    runtime.stop()


def test_browser_navigation_replay_validator_executes(tmp_path):
    import shutil
    node=shutil.which('node')
    assert node, 'Browser contract tests require the available Node runtime'
    value=replay(example_recording())
    path=tmp_path/'replay.json'; path.write_text(json.dumps(value))
    script="const fs=require('fs');const v=require(process.argv[1]);const data=JSON.parse(fs.readFileSync(process.argv[2]));v.validateNavigationReplay(data);const state=data.samples.find(x=>x.guidance_enabled);v.validateNavigation(state);state.mission={schema_version:1,mission_id:'m',status:'ready',target_index:0,target_id:'t',target_name:'T',target_count:1,arrival:{schema_version:1,status:'waiting',estimated_arrival:false,distance_m:null,uncertainty_m:null,elapsed_s:0,fresh_frames:0,uncertainty_provisional:true,physical_acceptance:false},snapshot_status:'not_requested',snapshot_sha256:null,snapshot_source:null,physical_output:false,uncertainty_provisional:true,physical_acceptance:false};v.validateNavigation(state);for(const phase of ['waiting_for_target','reacquiring_target']){state.mission.status=phase;v.validateNavigation(state)}state.mission.status='ready';state.mission.snapshot_sha256='bad';let threw=false;try{v.validateNavigation(state)}catch(e){threw=true}if(!threw)process.exit(1);state.mission.snapshot_sha256=null;state.route_tag_ids=state.route.map(()=>[0]);threw=false;try{v.validateNavigation(state)}catch(e){threw=true}if(!threw)process.exit(1);state.physical_output=true;threw=false;try{v.validateNavigationReplay(data)}catch(e){threw=true}if(!threw)process.exit(1);"
    subprocess.run([node,'-e',script,str(ROOT/'software/ball_demo/static/navigation.js'),str(path)],check=True)


def test_live_worker_frame_gaps_loss_and_read_errors_force_reacquisition(tmp_path,monkeypatch):
    from ball_demo.localization import Localizer
    b=example_bundle(); runtime=NavigationRuntime(b,tmp_path/'live.jsonl')
    monkeypatch.setattr(Localizer,'detect',lambda self,image:observations_for(b,example_pose()))
    state={'index':0,'gap':False,'issue':None,'error':False}
    def get_frame():
        state['index']+=5 if state['gap'] else 1
        state['gap']=False
        now=time.monotonic()
        return Frame(np.zeros((480,640,3),np.uint8),now,state['index'],{}),(0,state['index']),'synthetic',state['issue']
    runtime.get_frame=get_frame
    runtime.start()
    try:
        wait_for(lambda:hasattr(runtime,'advisory') and runtime.advisory.guard.status=='valid')
        runtime.command('goal',[2.2,1.5,1.3]); runtime.command('resume')
        wait_for(lambda:runtime.snapshot(time.monotonic())['guidance_enabled'])
        state['gap']=True
        wait_for(lambda:not runtime.snapshot(time.monotonic())['guidance_enabled'])
        assert not runtime.advisory.enabled
        state['issue']='source disconnect'
        wait_for(lambda:runtime.advisory.status=='source disconnect')
        state['issue']=None
        monkeypatch.setattr(Localizer,'detect',lambda *args:(_ for _ in ()).throw(ValueError('test detector failure')))
        wait_for(lambda:runtime.advisory.status=='test detector failure')
    finally:runtime.stop()
    recording=load_recording(tmp_path/'live.jsonl')
    assert any(e.reason and 'gap' in e.reason for e in recording.events)


def test_snapshot_checks_exposure_age_even_with_recent_publication(tmp_path):
    b=example_bundle(); runtime=NavigationRuntime(b,tmp_path/'nav.jsonl')
    state=next(s for s in replay(example_recording())['samples'] if s['guidance_enabled'])
    state.pop('t')
    runtime.cached=state; runtime.published_at=2.
    assert not runtime.snapshot(2.01)['guidance_enabled'] and runtime.cached['status']=='Stale localization'


def test_engine_real_bitmap_localization_guidance_loss_and_recovery(tmp_path,monkeypatch):
    """Rendered bitmap/fake capture: exercises real correction, tag detector and solve.

    This is NOT camera, Pi or measured-calibration evidence.
    """
    from test_navigation import render_tags
    from ball_demo.map_io import Bundle
    b=example_bundle(); data=b.model_dump()
    for key in ('map','survey','calibration'):
        data[key]['example']=False
        data[key]['evidence']='Synthetic bitmap in measured-format contract; NO hardware measurement'
    data['policy']['host_delay_bound_s']=.01
    b=Bundle.model_validate(data)
    image=render_tags(b)
    class Source:
        label='RECORDED'
        eof=False
        hidden=False
        index=0
        def read(self):
            time.sleep(.1)
            self.index+=1
            return Frame(np.zeros_like(image) if self.hidden else image.copy(),time.monotonic(),self.index,{})
        def close(self): pass
    source=Source()
    e=Engine(tmp_path,navigation_bundle=b,source={'kind':'recorded','path':'fake-bitmap-stream'})
    monkeypatch.setattr(e,'open_source',lambda *args:source)
    e.start()
    try:
        wait_for(lambda:e.navigation.advisory.guard.status=='valid')
        e.navigation_command('goal',[2.2,1.5,1.3]); e.navigation_command('resume')
        wait_for(lambda:e.snapshot()['navigation']['guidance_enabled'])
        snapshot=e.snapshot()
        pose=snapshot['navigation']['pose']
        assert np.linalg.norm(np.array(pose['map_from_aircraft'])[:3,3]-[1.7,.8,1.2])<.04
        assert pose['source']=='recorded_estimate' and pose['timing']['provenance']=='host_read' and pose['timing']['exposure_s'] is None
        assert not snapshot['enabled'] and snapshot['yaw']==0 and snapshot['physical_telemetry'] is None
        source.hidden=True
        wait_for(lambda:e.snapshot()['navigation']['status']=='No surveyed tags visible')
        assert e.snapshot()['navigation']['route']==[]
        source.hidden=False
        wait_for(lambda:e.navigation.advisory.guard.status=='valid')
        assert not e.snapshot()['navigation']['guidance_enabled']
    finally:e.stop()


def test_concurrent_bundle_imports_stop_every_replaced_worker_without_blocking_control(tmp_path,monkeypatch):
    engine=Engine(tmp_path,navigation_bundle=example_bundle())
    engine.start()
    original=NavigationRuntime.__init__
    barrier=threading.Barrier(2)
    runtimes=[]; errors=[]
    def synchronized(self,*args,**kwargs):
        original(self,*args,**kwargs)
        runtimes.append(self)
        barrier.wait(timeout=3)
    monkeypatch.setattr(NavigationRuntime,'__init__',synchronized)
    def replace():
        try: engine.configure_navigation(example_bundle())
        except Exception as error: errors.append(error)
    threads=[threading.Thread(target=replace) for _ in range(2)]
    old=engine.navigation
    try:
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=4)
        assert not errors and not any(thread.is_alive() for thread in threads)
        assert old.stop_event.is_set() and len(runtimes)==2
        assert all(runtime is engine.navigation or runtime.stop_event.is_set() for runtime in runtimes)
        assert sum(bool(runtime.thread and runtime.thread.is_alive()) for runtime in runtimes)==1
        # Lifecycle calls are idempotent for the optional worker.
        thread=engine.navigation.thread; engine.navigation.start()
        assert engine.navigation.thread is thread
        wait_for(lambda:engine.control_tick_at is not None)
        assert engine.snapshot()['state']=='MANUAL'
    finally: engine.stop()
    assert all(runtime.stop_event.is_set() for runtime in runtimes)
