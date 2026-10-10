"""Synthetic depth evidence only: repeatability, occlusion, holes and SDK lifecycle."""
import hashlib
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from ball_demo.mapping import DepthIntrinsics, Scan, Station, build_map, capture_d435, merge_voxels, rebuild_scans
from ball_demo.navigation import box_interval


def scan_fixture(tmp_path, depth=None):
    depth=np.full((48,64),2.,dtype=float) if depth is None else depth
    path=tmp_path/'frame.npz'
    np.savez_compressed(path,depth_m=depth)
    transform=np.eye(4); transform[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]]; transform[:3,3]=[1.,.1,1.]
    data={'schema_version':1,'scan_id':'EXAMPLE-depth','camera_model':'D435','serial':'SYNTHETIC','sdk_version':'test','map_id':'EXAMPLE-room','map_version':1,'frame_id':'example_world',
          'units':'m','axes':'right_handed_z_up','permitted':{'minimum':[0.,.1,0.],'maximum':[2.,3.1,2.]},'voxel_m':.2,'uncertainty_m':.03,'max_depth_m':4.,
          'acquired_utc':'2026-10-08T00:00:00Z','evidence':'INVENTED synthetic depth plane','example':True,
          'frames':[{'file':'frame.npz','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'intrinsics':{'width':64,'height':48,'fx':50.,'fy':50.,'cx':32.,'cy':24.,'model':'rectified_pinhole'},
                     'map_from_depth':transform.tolist(),'registration_evidence':'INVENTED transform','hardware_timestamp_ms':1000.,'hardware_clock_domain':'test-device-clock','host_received_s':999.}]}
    return Scan.model_validate(data)


def contains(boxes,point):
    return any(all(a<=v<=b for a,v,b in zip(box.minimum,point,box.maximum)) for box in boxes)


def test_saved_depth_reconstruction_is_deterministic_and_behind_wall_unknown(tmp_path):
    scan=scan_fixture(tmp_path)
    mapped,report=build_map(scan,tmp_path)
    other,second=build_map(scan,tmp_path)
    assert mapped.model_dump_json()==other.model_dump_json() and report==second
    assert contains(mapped.observed_free,[1.,1.,1.])
    assert not contains(mapped.observed_free,[1.,2.7,1.])
    assert contains(mapped.occupied,[1.,2.1,1.])
    assert report['unknown_voxels']>0 and report['observed_free_voxels']>0 and not report['physical_acceptance']
    assert report['unknown_voxels']+report['observed_free_voxels']+report['occupied_voxels']==1500


def test_depth_holes_and_foreground_occlusion_never_become_free(tmp_path):
    depth=np.full((48,64),2.,dtype=float)
    depth[19:30,27:38]=0
    m,_=build_map(scan_fixture(tmp_path,depth),tmp_path)
    assert not contains(m.observed_free,[1.,1.,1.])
    depth[19:30,27:38]=1.
    m,_=build_map(scan_fixture(tmp_path,depth),tmp_path)
    assert not contains(m.observed_free,[1.,1.7,1.])
    assert contains(m.occupied,[1.,1.1,1.])


def test_union_repeated_views_cannot_override_observed_obstacle(tmp_path):
    depth=np.full((48,64),2.,dtype=float); depth[19:30,27:38]=1.
    scan=scan_fixture(tmp_path,depth)
    second=tmp_path/'second.npz'; np.savez_compressed(second,depth_m=np.full((48,64),2.,dtype=float))
    frame=scan.frames[0].model_copy(update={'file':'second.npz','sha256':hashlib.sha256(second.read_bytes()).hexdigest()})
    scan.frames.append(frame)
    mapped,_=build_map(scan,tmp_path)
    assert contains(mapped.occupied,[1.,1.2,1.]) and not contains(mapped.observed_free,[1.,1.2,1.])


@pytest.mark.parametrize('bad', ['nan','negative','shape','integer','missing','zero','overrange'])
def test_bad_depth_arrays_and_absent_observations_rejected(tmp_path,bad):
    depth=np.full((48,64),2.,dtype=float)
    if bad=='nan': depth[1,1]=np.nan
    if bad=='negative': depth[1,1]=-1.
    if bad=='shape': depth=depth[:20]
    if bad=='integer': depth=depth.astype(np.uint16)
    if bad=='zero': depth[:]=0.
    if bad=='overrange': depth[:]=8.
    scan=scan_fixture(tmp_path,depth)
    if bad=='missing':
        np.savez_compressed(tmp_path/'frame.npz',foo=depth)
        scan.frames[0].sha256=hashlib.sha256((tmp_path/'frame.npz').read_bytes()).hexdigest()
    with pytest.raises(ValueError): build_map(scan,tmp_path)


def test_hash_path_frame_ids_and_bounded_volume_validation(tmp_path):
    scan=scan_fixture(tmp_path)
    scan.frames[0].sha256='a'*64
    with pytest.raises(ValueError,match='hash'): build_map(scan,tmp_path)
    data=scan.model_dump(); data['frames'][0]['file']='../secret.npz'
    with pytest.raises(ValueError): Scan.model_validate(data)
    data=scan.model_dump(); data['frames'].append(data['frames'][0])
    with pytest.raises(ValueError,match='Duplicate'): Scan.model_validate(data)
    data=scan.model_dump(); data['voxel_m']=.001
    with pytest.raises(ValueError,match='100000'): Scan.model_validate(data)
    with pytest.raises(ValueError): DepthIntrinsics(width=64,height=48,fx=50.,fy=50.,cx=64.,cy=24.,model='rectified_pinhole')


def test_exact_voxel_merging_never_fills_hole_or_expands_extent():
    cells={(x,y,z) for x in range(4) for y in range(3) for z in range(2)}-{(1,1,1)}
    boxes=merge_voxels(cells,np.zeros(3),.1,np.array([.35,.3,.2]))
    assert not contains(boxes,[.15,.15,.15])
    assert max(b.maximum[0] for b in boxes)==.35
    for x,y,z in cells:
        assert contains(boxes,[(x+.5)*.1 if x<3 else .325,(y+.5)*.1,(z+.5)*.1])


def test_multi_station_rebuild_preserves_hashes_and_registration(tmp_path):
    scan=scan_fixture(tmp_path)
    manifest=tmp_path/'scan.json'; manifest.write_text(scan.model_dump_json())
    mapped,report=rebuild_scans([manifest,manifest])
    assert report['frames']==2 and len(report['source_manifests'])==2
    assert contains(mapped.observed_free,[1.,1.,1.])
    other=scan.model_dump(); other['frame_id']='other'; path=tmp_path/'other.json'; path.write_text(json.dumps(other))
    with pytest.raises(ValueError,match='mismatch'): rebuild_scans([manifest,path])
    with pytest.raises(ValueError): rebuild_scans([])


def sdk_fixture(mode='success'):
    intr=SimpleNamespace(width=64,height=48,fx=50.,fy=50.,ppx=32.,ppy=24.,coeffs=[0.]*5,model='none')
    if mode=='distortion': intr.coeffs[0]=.1
    profile=SimpleNamespace(get_intrinsics=lambda:intr,get_extrinsics_to=lambda p:SimpleNamespace(rotation=[1.,0.,0.,0.,1.,0.,0.,0.,1.],translation=[0.,0.,0.]))
    depth=np.ones((48,64),np.uint16)*2000
    if mode=='dtype': depth=depth.astype(float)
    frame=SimpleNamespace(profile=SimpleNamespace(as_video_stream_profile=lambda:profile),get_data=lambda:depth,get_timestamp=lambda:1234.,get_frame_timestamp_domain=lambda:'hardware_clock')
    color=SimpleNamespace(profile=frame.profile,get_data=lambda:np.zeros((48,64,3),np.uint8),get_timestamp=lambda:1235.,get_frame_timestamp_domain=lambda:'hardware_clock')
    sample=SimpleNamespace(get_depth_frame=lambda:frame,get_color_frame=lambda:None if mode=='incomplete' else color)
    info=SimpleNamespace(name='name',firmware_version='firmware',serial_number='serial')
    values={'name':'Intel RealSense D435' if mode!='wrong-device' else 'D435i','firmware':'fake-firmware','serial':'fake-serial'}
    device=SimpleNamespace(get_info=lambda key:values[key],first_depth_sensor=lambda:SimpleNamespace(get_depth_scale=lambda:float('nan') if mode=='scale' else .001))
    device_profile=SimpleNamespace(get_device=lambda:device)
    state={'stopped':False,'reads':0,'configured':[]}
    def read(timeout): state['reads']+=1; return sample
    def start(config):
        if mode=='start': raise RuntimeError('fake SDK start failed')
        return device_profile
    pipeline=SimpleNamespace(start=start,wait_for_frames=read,stop=lambda:state.update(stopped=True))
    config=SimpleNamespace(enable_stream=lambda *args:state['configured'].append(args),enable_record_to_file=lambda path:state.update(bag=path))
    sdk=SimpleNamespace(__name__='injected-test-sdk',pipeline=lambda:pipeline,config=lambda:config,stream=SimpleNamespace(depth='depth',color='color'),format=SimpleNamespace(z16='z16',bgr8='bgr8'),camera_info=info)
    return sdk,state


def station_fixture():
    transform=np.eye(4); transform[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]]; transform[:3,3]=[1.,.1,1.]
    return Station(schema_version=1,scan_id='test-station',map_id='test-map',map_version=1,frame_id='world',permitted={'minimum':[0.,.1,0.],'maximum':[2.,3.1,2.]},voxel_m=.2,uncertainty_m=.03,max_depth_m=4.,map_from_depth=transform.tolist(),registration_evidence='FAKE SDK TEST ONLY',example=False)


def test_fake_d435_sdk_capture_records_raw_units_and_separate_clock_domains(tmp_path):
    sdk,state=sdk_fixture()
    previews, progress = [], []
    scan=capture_d435(station_fixture(),tmp_path/'capture',frames=2,sdk=sdk,
                      on_frame=lambda image: previews.append(image.copy()),
                      on_progress=lambda current,total: progress.append((current,total)))
    assert state['stopped'] and state['reads']==32
    assert len(scan.frames)==2 and scan.frames[0].hardware_timestamp_ms==1234.
    assert scan.frames[0].host_received_s != 1.234 and scan.frames[0].hardware_clock_domain=='hardware_clock'
    assert scan.frames[0].color_hardware_timestamp_ms==1235. and scan.frames[1].color_hardware_clock_domain=='hardware_clock'
    assert scan.camera_metadata['depth_scale_m']==.001 and scan.sdk_version=='injected-test-sdk'
    assert len(previews)==2 and previews[0].shape==(48,64,3) and progress==[(1,2),(2,2)]
    with np.load(tmp_path/'capture'/'frame-0000.npz') as data:
        assert data['raw_depth'].dtype==np.uint16 and np.all(data['depth_m']==2.)
    mapped,report=build_map(scan,tmp_path/'capture')
    assert report['observed_free_voxels']>0
    assert (tmp_path/'capture'/'scan.json').exists()


@pytest.mark.parametrize('mode', ['wrong-device','distortion','dtype','incomplete','scale','start'])
def test_fake_d435_failures_preserve_partial_capture_and_stop_sdk(tmp_path,mode):
    sdk,state=sdk_fixture(mode)
    with pytest.raises((ValueError,RuntimeError)): capture_d435(station_fixture(),tmp_path/'capture',1,sdk)
    assert state['stopped']==(mode!='start')
    assert (tmp_path/'capture').is_dir() and not (tmp_path/'capture'/'scan.json').exists()


def test_capture_example_invalid_count_missing_sdk_and_existing_output(tmp_path,monkeypatch):
    station=station_fixture()
    with pytest.raises(ValueError): capture_d435(station,tmp_path/'capture',True)
    station.example=True
    with pytest.raises(ValueError,match='examples'): capture_d435(station,tmp_path/'capture')
    station.example=False
    monkeypatch.setitem(sys.modules,'pyrealsense2',None)
    with pytest.raises(ValueError,match='SDK unavailable'): capture_d435(station,tmp_path/'capture')
    sdk,_=sdk_fixture()
    with pytest.raises(FileExistsError): capture_d435(station,tmp_path,1,sdk)


def test_reconstructed_depth_map_blocks_mock_goal_without_two_tag_visibility_coverage(tmp_path):
    from ball_demo.map_io import Bundle
    from ball_demo.navigation import Planner
    from ball_demo.navigation_fixtures import example_bundle, simulation_recording
    from ball_demo.navigation_replay import simulation
    scan=scan_fixture(tmp_path)
    # Independently measured-format synthetic wide-angle camera seeing a plane.
    # Wide coverage produces adjacent differently-sized free boxes, not one room box.
    scan.frames[0].intrinsics.fx=scan.frames[0].intrinsics.fy=20.
    mapped,_=build_map(scan,tmp_path)
    data=example_bundle().model_dump(); data['map']=mapped.model_dump()
    data['survey'].update(map_id=mapped.map_id,map_version=mapped.map_version,frame_id=mapped.frame_id)
    for tag,x in zip(data['survey']['tags'],[.7,1.3]): tag['map_from_tag'][0][3]=x
    b=Bundle.model_validate(data)
    route,margin=Planner(b).plan([1.,.9,1.],[1.,1.4,1.],.03)
    assert len(route)>=2 and all(Planner(b).segment_clear(a,z,margin) for a,z in zip(route,route[1:]))
    start=[1.,.9,1.]
    result=simulation(simulation_recording(b,start,[1.,1.4,1.]),limit=60)
    assert result['samples'][0]['status']!='goal reached'
    assert all(not s['guidance_enabled'] for s in result['samples'])
    assert all(s['mock_commanded_velocity_m_s']==[0.,0.,0.] for s in result['samples'])
    assert all(np.allclose(s['simulation_truth_position_m'],start) for s in result['samples'])
    assert result['physical_output'] is False and result['physical_telemetry'] is None
