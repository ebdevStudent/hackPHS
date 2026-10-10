"""Source CLI integration for repeatable artifacts, calibration and mock-only launch."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from ball_demo import cli
from ball_demo.navigation_fixtures import example_bundle, example_recording, generate, simulation_recording
from ball_demo.navigation_replay import Recording, load_recording, simulation
from test_mapping import scan_fixture


def run(monkeypatch,*args):
    monkeypatch.setattr(sys,'argv',['ball-demo',*map(str,args)])
    return cli.main()


def test_cli_fixtures_replay_demo_and_mapped_simulation(tmp_path,monkeypatch):
    fixtures=tmp_path/'fixtures'
    run(monkeypatch,'nav-fixtures','--output',fixtures)
    assert (fixtures/'station.schema.json').exists()
    assert (fixtures/'visible-route.schema.json').exists() and (fixtures/'example-mission.json').exists()
    session=fixtures/'synthetic-session.json'
    run(monkeypatch,'nav-replay',session,'--output',tmp_path/'replay.json')
    run(monkeypatch,'nav-demo',session,'--output',tmp_path/'demo.json')
    run(monkeypatch,'nav-simulate','--bundle',fixtures/'example-bundle.json','--start','1.7','.8','1.2','--goal','2.2','1.5','1.3','--output',tmp_path/'mapped.json')
    replay=json.loads((tmp_path/'replay.json').read_text())
    demo=json.loads((tmp_path/'demo.json').read_text())
    mapped=json.loads((tmp_path/'mapped.json').read_text())
    assert replay['physical_output'] is False and demo['samples'][-1]['status']=='goal reached'
    assert mapped['source_bundle_sha256']==example_bundle().digest and mapped['samples'][-1]['status']=='goal reached'
    assert not mapped['physical_output'] and mapped['map']['example']


def test_measured_bundle_simulation_copy_never_changes_source_geometry_or_evidence():
    data=example_bundle().model_dump()
    for key in ('map','survey','calibration'): data[key]['example']=False; data[key]['evidence']='MEASURED-FORMAT TEST FIXTURE ONLY'
    from ball_demo.map_io import Bundle
    b=Bundle.model_validate(data); before=b.model_dump_json()
    recording=simulation_recording(b,[1.7,.8,1.2],[2.2,1.5,1.3])
    demo=simulation(recording)
    assert b.model_dump_json()==before and not b.map.example
    assert b.digest in recording.label and recording.bundle.map.example
    assert demo['samples'][-1]['status']=='goal reached'
    with pytest.raises(ValueError): simulation_recording(b,[1.,1.,1.],[2.,2.,2.],yaw_deg=float('nan'))


def test_cli_map_rebuild_and_bundle_assembly_validation(tmp_path,monkeypatch):
    scan=scan_fixture(tmp_path); manifest=tmp_path/'scan.json'; manifest.write_text(scan.model_dump_json())
    run(monkeypatch,'nav-map',manifest,'--output',tmp_path/'rebuild-a')
    run(monkeypatch,'nav-map',manifest,'--output',tmp_path/'rebuild-b')
    assert (tmp_path/'rebuild-a'/'map.json').read_bytes()==(tmp_path/'rebuild-b'/'map.json').read_bytes()
    b=example_bundle()
    for key in ('map','survey','calibration','policy'): (tmp_path/f'{key}.json').write_text(json.dumps(b.model_dump()[key]))
    args=['nav-bundle','--map',tmp_path/'map.json','--survey',tmp_path/'survey.json','--calibration',tmp_path/'calibration.json','--policy',tmp_path/'policy.json','--id','test-bundle','--output',tmp_path/'bundle.json']
    run(monkeypatch,*args)
    assert json.loads((tmp_path/'bundle.json').read_text())['bundle_id']=='test-bundle'
    with pytest.raises(FileExistsError): run(monkeypatch,*args)


def test_cli_calibrate_dispatch_and_unreadable_capture_rejection(tmp_path,monkeypatch):
    from ball_demo import calibration
    b=example_bundle(); bundle=tmp_path/'bundle.json'; bundle.write_text(b.model_dump_json())
    images=tmp_path/'images'; images.mkdir(); cv2.imwrite(str(images/'frame.png'),np.zeros((480,640,3),np.uint8))
    seen=[]
    def calibrate(pictures,columns,rows,square,template):
        seen.append((len(pictures),columns,rows,square,template.calibration_id))
        return template,12
    monkeypatch.setattr(calibration,'calibrate',calibrate)
    args=['nav-calibrate','--bundle',bundle,'--images',images,'--columns','7','--rows','5','--square-m','.025','--output',tmp_path/'calibration.json']
    run(monkeypatch,*args)
    assert seen==[(1,7,5,.025,b.calibration.calibration_id)]
    (images/'frame.png').write_text('invalid')
    with pytest.raises(SystemExit): run(monkeypatch,*args)


def test_cli_capture_dispatch_and_optional_serve_replay_is_disabled_mock(tmp_path,monkeypatch):
    from ball_demo import mapping
    output=generate(tmp_path/'fixtures')
    calls=[]
    monkeypatch.setattr(mapping,'capture_d435',lambda *args:calls.append(args))
    run(monkeypatch,'nav-capture-d435','--station',output/'example-station.json','--output',tmp_path/'capture','--frames','2')
    assert calls[0][2]==2
    engines=[]
    class Server:
        def __init__(self,config): self.config=config
        def run(self):
            e=self.config.app.state.engine; engines.append(e)
            assert not e.controller.enabled and e.bridge.transport.startswith('MOCK')
            assert e.navigation and not e.navigation.cached['guidance_enabled']
            e.stop()
        def handle_exit(self,*args): pass
    monkeypatch.setattr(cli.uvicorn,'Server',Server)
    run(monkeypatch,'serve','--data',tmp_path/'runs','--nav-bundle',output/'example-bundle.json','--nav-replay',output/'synthetic-session.json')
    assert engines[0].navigation.recording.bundle.digest==example_bundle().digest


def test_replay_loss_disable_bad_restore_and_invalid_imports(tmp_path):
    recording=example_recording()
    data=recording.model_dump(); data['events'].append({'t':2.,'kind':'disable'}); data['events'].append({'t':2.1,'kind':'resume'})
    from ball_demo.navigation_replay import replay, Recorder
    result=replay(Recording.model_validate(data))
    assert result['samples'][-1]['route']==[]
    path=tmp_path/'recording.json'; path.write_text(recording.model_dump_json())
    assert load_recording(path).bundle.digest==recording.bundle.digest
    with path.open('w') as f: f.write(' '*50_000_001)
    with pytest.raises(ValueError,match='size'): load_recording(path)
    data=recording.model_dump(); data['events'][1]['observations']=[]
    assert replay(Recording.model_validate(data))['samples'][1]['status']=='No surveyed tags visible'
    recorder=Recorder(tmp_path/'record.jsonl',recording.bundle,recording.label)
    class Broken:
        def close(self): raise OSError('test close')
    recorder.file.close(); recorder.file=Broken(); recorder.close(); assert recorder.errors==1
    measured=recording.model_dump()
    for key in ('map','survey','calibration'): measured['bundle'][key]['example']=False
    from ball_demo.map_io import Bundle
    measured['bundle_sha256']=Bundle.model_validate(measured['bundle']).digest
    for e in measured['events']:
        if e['kind']=='observations': e['source']='recorded_estimate'
    with pytest.raises(ValueError,match='example'): simulation(Recording.model_validate(measured))
    empty=recording.model_dump(); empty['events']=[{'t':1.,'kind':'tick'}]
    with pytest.raises(ValueError,match='initial'): simulation(Recording.model_validate(empty))
