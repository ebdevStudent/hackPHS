"""Independent geometry, strict contracts, inference and advisory failure regressions."""
import copy
import json
import math

import cv2
import numpy as np
import pytest

from ball_demo.calibration import aircraft_pose, calibrate, invert, undistort
from ball_demo.localization import Localizer, Observation, Pose, Timing
from ball_demo.map_io import Bundle, Calibration, Policy, rigid, load_bundle
from ball_demo.navigation import Advisory, NavigationState, Planner, box_interval, clearance, vector
from ball_demo.navigation_fixtures import example_bundle, example_mission, example_pose, example_recording, observations_for
from ball_demo.navigation_guard import PoseGuard
from ball_demo.navigation_replay import Input, MockPlant, Recording, Recorder, apply_input, load_recording, replay, simulation


@pytest.fixture
def bundle(): return example_bundle()


def pose_at(bundle, seq=0, t=1., position=(1.7, .8, 1.2)):
    return Localizer(bundle).solve(observations_for(bundle, example_pose(position)), Timing(host_received_s=t, exposure_s=t, provenance='synthetic'), seq, 'synthetic_estimate')


def acquired(bundle):
    a = Advisory(bundle)
    a.set_goal([2.2, 1.5, 1.3])
    for i in range(3): a.accept(pose_at(bundle, i, 1. + i * .05), 1. + i * .05)
    a.resume(1.1)
    return a


@pytest.mark.parametrize('seed', range(20))
def test_transform_chain_matches_independent_camera_world_points(seed):
    rng = np.random.default_rng(seed)
    def transform():
        result = np.eye(4)
        result[:3, :3] = cv2.Rodrigues(rng.normal(0, .5, 3))[0]
        result[:3, 3] = rng.normal(0, .4, 3)
        return result
    map_from_aircraft, aircraft_from_camera, camera_from_tag = transform(), transform(), transform()
    map_from_tag = map_from_aircraft @ aircraft_from_camera @ camera_from_tag
    estimated = aircraft_pose(map_from_tag, camera_from_tag, aircraft_from_camera)
    points = np.column_stack((rng.normal(size=(10, 3)), np.ones(10)))
    assert np.allclose((estimated @ points.T).T, (map_from_aircraft @ points.T).T, atol=1e-10)
    assert np.allclose(invert(estimated) @ estimated, np.eye(4), atol=1e-10)


@pytest.mark.parametrize('bad', [np.ones((3, 3)), np.diag([1, 1, -1, 1]), np.diag([2, 1, 1, 1]), np.diag([1, 1, 1, 2]), np.full((4, 4), np.nan), [[1]*4]*4])
def test_nonrigid_transforms_are_rejected(bad):
    with pytest.raises(ValueError): rigid(bad)


@pytest.mark.parametrize('field,value', [('units', 'cm'), ('axes', 'left_handed'), ('frame_id', ''), ('uncertainty_m', -1.), ('uncertainty_m', float('nan')), ('map_version', True), ('schema_version', True), ('schema_version', 2)])
def test_map_units_frames_versions_and_nonfinite_validation(bundle, field, value):
    data = bundle.model_dump()
    data['map'][field] = value
    with pytest.raises(ValueError): Bundle.model_validate(data)


@pytest.mark.parametrize('change', range(12))
def test_bundle_registration_and_geometry_rejects_bad_import(bundle, change):
    data = bundle.model_dump()
    if change == 0: data['survey']['frame_id'] = 'other'
    if change == 1: data['survey']['map_version'] = 2
    if change == 2: data['survey']['map_id'] = 'other'
    if change == 3: data['survey']['tags'].append(data['survey']['tags'][0])
    if change == 4: data['survey']['tags'][0]['size_m'] = 0.
    if change == 5: data['survey']['tags'][0]['map_from_tag'][0][3] = 10.
    if change == 6: data['map']['observed_free'][0]['minimum'][0] = -1.
    if change == 7: data['map']['observed_free'][0]['maximum'][2] = 4.
    if change == 8: data['map']['permitted']['maximum'][0] = 0.
    if change == 9: data['calibration']['example'] = False
    if change == 10: data['calibration']['intrinsics'][0][0] = -500.
    if change == 11: data['policy']['host_delay_bound_s'] = float('inf')
    with pytest.raises(ValueError): Bundle.model_validate(data)


@pytest.mark.parametrize('mutation', ['distortion', 'skew', 'center', 'bottom', 'transform', 'unknown'])
def test_calibration_invalid_contract(bundle, mutation):
    data = bundle.calibration.model_dump()
    if mutation == 'distortion': data['distortion'] = [0.]*3
    if mutation == 'skew': data['intrinsics'][0][1] = 1.
    if mutation == 'center': data['intrinsics'][0][2] = 1000.
    if mutation == 'bottom': data['intrinsics'][2][1] = 1.
    if mutation == 'transform': data['aircraft_from_camera'][0][0] = 2.
    if mutation == 'unknown': data['exposure_safe'] = True
    with pytest.raises(ValueError): Calibration.model_validate(data)


def test_schema_hash_round_trip_and_size_limit(bundle, tmp_path):
    path = tmp_path / 'bundle.json'
    path.write_text(bundle.model_dump_json())
    assert load_bundle(path).digest == bundle.digest
    path.write_text(' ' * 10_000_001)
    with pytest.raises(ValueError, match='size'): load_bundle(path)


def test_checkerboard_calibration_recovers_known_camera(bundle, monkeypatch):
    grid = np.zeros((7*5, 3), np.float32)
    grid[:, :2] = np.mgrid[0:7, 0:5].T.reshape(-1, 2) * .025
    k = np.array([[520., 0, 319], [0, 515., 241], [0, 0, 1]])
    corners = []
    for i in range(12):
        rv = np.array([.15 + i * .03, -.2 + i * .02, .02 * i])
        tv = np.array([-.08 + .005 * i, -.05 + .003 * i, .5 + i * .02])
        corners.append(cv2.projectPoints(grid, rv, tv, k, np.zeros(5))[0])
    iterator = iter(corners)
    monkeypatch.setattr(cv2, 'findChessboardCornersSB', lambda *args: (True, next(iterator)))
    result, views = calibrate([np.zeros((480, 640, 3), np.uint8)]*12, 7, 5, .025, bundle.calibration)
    assert views == 12 and result.reprojection_rms_px < .001
    assert np.allclose(result.intrinsics, k, atol=.03)
    assert result.example   # Capture calibration alone never proves measured mount/survey.


@pytest.mark.parametrize('columns,rows,square', [(True,5,.02),(2,5,.02),(7,31,.02),(7,5,0),(7,5,math.nan),(7,5,True)])
def test_calibration_capture_parameters_rejected(bundle, columns, rows, square):
    with pytest.raises(ValueError): calibrate([], columns, rows, square, bundle.calibration)


def test_calibration_requires_views_and_final_size(bundle, monkeypatch):
    with pytest.raises(ValueError, match='size'): calibrate([np.zeros((100,100),np.uint8)],7,5,.02,bundle.calibration)
    monkeypatch.setattr(cv2, 'findChessboardCornersSB', lambda *args: (False, None))
    with pytest.raises(ValueError, match='ten'): calibrate([np.zeros((480,640),np.uint8)]*10,7,5,.02,bundle.calibration)
    assert undistort(np.zeros((480,640,3),np.uint8),bundle.calibration).shape == (480,640,3)
    with pytest.raises(ValueError, match='size'): undistort(np.zeros((20,20),np.uint8),bundle.calibration)


def render_tags(bundle):
    image = np.full((480,640,3),255,np.uint8)
    observations = observations_for(bundle, example_pose())
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    for observation in observations:
        marker = cv2.aruco.generateImageMarker(dictionary,observation.id,200)
        transform = cv2.getPerspectiveTransform(np.array([[0,0],[199,0],[199,199],[0,199]],np.float32), np.array(observation.corners,np.float32))
        warped = cv2.warpPerspective(marker,transform,(640,480),borderValue=255)
        image = np.minimum(image,cv2.cvtColor(warped,cv2.COLOR_GRAY2BGR))
    return image


def test_real_apriltag_detector_on_rendered_bitmap_and_blank(bundle, monkeypatch):
    localizer = Localizer(bundle)
    observed = localizer.detect(render_tags(bundle))
    assert {o.id for o in observed} == {0,1}
    pose = localizer.solve(observed,Timing(host_received_s=1.,exposure_s=1.,provenance='synthetic'),0,'synthetic_estimate')
    assert np.linalg.norm(pose.position - example_pose()[:3,3]) < .04
    assert localizer.detect(np.zeros((480,640,3),np.uint8)) == []
    with pytest.raises(ValueError,match='size'): localizer.detect(np.zeros((100,100),np.uint8))
    monkeypatch.delattr(cv2,'aruco')
    with pytest.raises(ValueError,match='unavailable'): localizer.detect(np.zeros((480,640,3),np.uint8))


@pytest.mark.parametrize('position', [(1.7,.8,1.2),(2.,1.,1.4),(2.3,1.2,1.5),(1.6,.7,1.1)])
def test_pose_solver_metric_position_orientation_and_distortion(bundle, position):
    pose = pose_at(bundle,position=position)
    assert np.allclose(pose.map_from_aircraft,example_pose(position),atol=1e-6)
    assert pose.reprojection_px < 1e-6 and pose.uncertainty_m > 0
    assert pose.source == 'synthetic_estimate'


def test_single_tag_branches_and_solver_rejects_invalid_observations(bundle, monkeypatch):
    localizer=Localizer(bundle)
    o=observations_for(bundle,example_pose())
    t=Timing(host_received_s=1.,exposure_s=1.,provenance='synthetic')
    pose=localizer.solve(o[:1],t,0,'synthetic_estimate')
    assert np.allclose(pose.position,[1.7,.8,1.2],atol=1e-6)
    for observed in ([],[o[0],o[0]],[{'id':10,'corners':o[0].corners}]):
        with pytest.raises(ValueError): localizer.solve(observed,t,1)
    outside=o[0].model_dump(); outside['corners']=[[x+1000,y] for x,y in outside['corners']]
    with pytest.raises(ValueError,match='outside'): localizer.solve([outside],t,1)
    with pytest.raises(ValueError,match='convex'): Observation(id=0,corners=[[0.,0.],[0.,0.],[2.,2.],[1.,1.]])
    monkeypatch.setattr(cv2,'solvePnPGeneric',lambda *a,**kw:(0,[],[],None))
    with pytest.raises(ValueError,match='positive-depth'): localizer.solve(o,t,1)


@pytest.mark.parametrize('data', [dict(host_received_s=1.,exposure_s=2.,provenance='synthetic'),dict(host_received_s=1.,exposure_s=1.,provenance='host_read'),dict(host_received_s=1.,provenance='exposure_monotonic')])
def test_timestamp_provenance_is_explicit(data):
    with pytest.raises(ValueError): Timing(**data)


def test_host_read_is_not_exposure_and_freshness_uses_delay(bundle):
    guard=PoseGuard(bundle)
    pose=pose_at(bundle)
    pose.timing=Timing(host_received_s=1.,provenance='host_read')
    assert not guard.check(pose,1.01) and 'Unknown camera' in guard.status
    pose.sequence=1; pose.timing.delay_bound_s=.2
    assert not guard.check(pose,1.051) and 'Stale' in guard.status
    pose.sequence=2; pose.timing.delay_bound_s=.01
    assert not guard.check(pose,1.05) and guard.status=='acquiring'
    with pytest.raises(ValueError,match='clock'): guard.freshness(pose,.9)


@pytest.mark.parametrize('field,value,reason', [('bundle_id','wrong','registration'),('frame_id','other','registration'),('calibration_id','wrong','registration'),('map_version',2,'registration'),('tag_ids',[55],'supporting'),('uncertainty_m',.16,'uncertainty'),('reprojection_px',3.1,'reprojection'),('ambiguity_gap_px',.1,'Ambiguous')])
def test_guard_rejection_latches_and_suppresses_route(bundle, field, value, reason):
    a=acquired(bundle)
    assert a.update(1.1)['guidance_enabled']
    p=pose_at(bundle,3,1.15); setattr(p,field,value)
    assert not a.accept(p,1.15)
    state=a.update(1.15)
    assert not state['guidance_enabled'] and state['route']==[] and reason in state['status']


def test_loss_stale_reacquisition_and_deliberate_restore(bundle):
    a=acquired(bundle); a.update(1.1)
    a.invalidate('tag loss')
    for seq,t in enumerate([1.2,1.25,1.3],start=3): a.accept(pose_at(bundle,seq,t),t); a.update(t)
    assert a.guard.status=='valid' and not a.snapshot(1.3)['guidance_enabled']
    a.resume(1.3); assert a.update(1.3)['route']
    stale=a.update(1.551)
    assert stale['route']==[] and stale['pose'] is None and 'Stale' in stale['status']
    with pytest.raises(ValueError): a.resume(1.56)


def test_duplicate_reordered_time_outliers_and_long_outage(bundle):
    guard=PoseGuard(bundle)
    p=pose_at(bundle)
    guard.check(p,1.)
    assert not guard.check(p,1.01) and 'duplicate' in guard.status
    p=pose_at(bundle,1,1.,(1.7,.8,1.2))
    assert not guard.check(p,1.) and 'Nonadvancing' in guard.status
    p=pose_at(bundle,2,1.01,(2.4,.8,1.2))
    assert not guard.check(p,1.01) and 'Position outlier' in guard.status
    p=pose_at(bundle,3,1.02)
    transform=np.array(p.map_from_aircraft); transform[:3,:3]=np.eye(3); p.map_from_aircraft=transform.tolist()
    assert not guard.check(p,1.02) and 'Orientation' in guard.status
    p=pose_at(bundle,4,4.,(2.3,.8,1.2))
    assert not guard.check(p,4.) and guard.status=='acquiring'
    p=pose_at(bundle,5,4.05); p.map_from_aircraft[0][3]=6.
    assert not guard.check(p,4.05) and 'outside' in guard.status


def test_stopping_envelope_full_cage_and_overhang(bundle):
    margin=clearance(bundle,.03)
    assert margin == pytest.approx(.125+.02+.03+.03+.2*.25+.2**2/(2*.5))
    planner=Planner(bundle)
    assert not planner.segment_clear([.1,1.,1.],[1.,1.,1.],margin)
    data=bundle.model_dump(); data['map']['occupied']=[{'minimum':[1.8,1.,1.55],'maximum':[2.2,2.,2.9]}]
    planner=Planner(Bundle.model_validate(data))
    assert not planner.segment_clear([2.,.8,1.4],[2.,2.4,1.4],margin)
    assert planner.segment_clear([2.,.8,.8],[2.,2.4,.8],margin)
    with pytest.raises(ValueError): planner.plan([2.,1.5,1.5],[2.,2.5,1.5],.03)


def test_three_dimensional_detour_and_continuous_route_clearance(bundle):
    data=bundle.model_dump()
    data['map']['occupied']=[{'minimum':[1.8,.5,.3],'maximum':[2.2,3.5,1.7]}]
    data['policy']['planner_timeout_s']=2.
    b=Bundle.model_validate(data); planner=Planner(b)
    route,margin=planner.plan([1.,2.,1.],[3.,2.,1.],.03)
    assert len(route)>2 and max(p[2] for p in route)>1.7+margin
    assert all(planner.segment_clear(a,z,margin) for a,z in zip(route,route[1:]))
    # Every swept endpoint lies in the eroded permitted volume.
    assert all(all(margin<=x<=max_x-margin for x,max_x in zip(p,b.map.permitted.maximum)) for p in route)


def test_unknown_gap_does_not_become_free_or_cut_corner(bundle):
    data=bundle.model_dump(); data['map']['observed_free']=[{'minimum':[0.,0.,0.],'maximum':[1.8,4.,3.]},{'minimum':[2.2,0.,0.],'maximum':[4.,4.,3.]}]
    b=Bundle.model_validate(data); planner=Planner(b)
    assert not planner.segment_clear([1.,2.,1.],[3.,2.,1.],.01)
    with pytest.raises(ValueError): planner.plan([1.,2.,1.],[3.,2.,1.],.01,clock=lambda:0.)


def test_planner_stall_and_node_budget_latch(bundle):
    a=acquired(bundle)
    clock_values=iter([0.,0.,100.])
    result=a.update(1.1,clock=lambda:next(clock_values,100.))
    assert not result['guidance_enabled'] and 'deadline' in result['status']
    data=bundle.model_dump(); data['policy']['max_nodes']=1
    data['map']['occupied']=[{'minimum':[1.8,.5,.3],'maximum':[2.2,3.5,1.7]}]
    with pytest.raises(ValueError,match='node budget'): Planner(Bundle.model_validate(data)).plan([1.,2.,1.],[3.,2.,1.],.03,clock=lambda:0.)


@pytest.mark.parametrize('bad', [[True,0.,1.],[0.,1.],[0.,float('nan'),1.],None,'1,2,3'])
def test_invalid_goal_and_margin(bundle,bad):
    with pytest.raises(ValueError): vector(bad)
    with pytest.raises(ValueError): Planner(bundle).segment_clear([1.,1.,1.],[2.,2.,1.],-.1)


def test_route_ttl_goal_change_and_display_validation(bundle):
    a=acquired(bundle); state=a.update(1.1)
    NavigationState.model_validate(state)
    a.bundle.policy.route_ttl_s=.05
    assert a.snapshot(1.16)['route']==[]
    a.set_goal([1.5,1.2,1.2]); assert not a.enabled and not a.route
    bad=copy.deepcopy(state); bad['physical_output']=0
    with pytest.raises(ValueError): NavigationState.model_validate(bad)
    bad=copy.deepcopy(state); bad['guidance_enabled']=False
    with pytest.raises(ValueError): NavigationState.model_validate(bad)
    bad=copy.deepcopy(state); bad['pose']['map_id']='wrong'
    with pytest.raises(ValueError): NavigationState.model_validate(bad)


def test_recording_determinism_loss_resume_and_synthetic_demo():
    recording=example_recording()
    first=replay(recording)
    assert json.dumps(first,sort_keys=True)==json.dumps(replay(recording),sort_keys=True)
    assert any(s['guidance_enabled'] for s in first['samples'])
    assert all(not s['guidance_enabled'] for s in first['samples'] if 1.3<=s['t']<1.51)
    assert not first['samples'][-1]['route'] and first['physical_telemetry'] is None
    demo=simulation(recording)
    assert demo['samples'][-1]['status']=='goal reached'
    assert np.linalg.norm(np.array(demo['samples'][-1]['simulation_truth_position_m'])-[2.2,1.5,1.3])<.06
    assert all(s['mock_commanded_velocity_m_s']==[0.,0.,0.] for s in demo['samples'] if not s['guidance_enabled'])
    assert all(np.linalg.norm(s['mock_velocity_m_s'])<=recording.bundle.policy.speed_m_s+1e-9 for s in demo['samples'])
    assert json.dumps(demo,sort_keys=True)==json.dumps(simulation(recording),sort_keys=True)


@pytest.mark.parametrize('mutation', ['hash','time','sequence','physical','source','extra','fields'])
def test_whole_recording_is_validated_before_playback(mutation):
    data=example_recording().model_dump()
    if mutation=='hash': data['bundle_sha256']='wrong'
    if mutation=='time': data['events'][-1]['t']=0.
    if mutation=='sequence': data['events'][2]['sequence']=0
    if mutation=='physical': data['physical_output']=True
    if mutation=='source': data['events'][1]['source']='vision_estimate'
    if mutation=='extra': data['events'][1]['command_roll']=.2
    if mutation=='fields': data['events'][0]['reason']='bad'
    with pytest.raises(ValueError): Recording.model_validate(data)


def test_recording_jsonl_roundtrip_and_logging_errors(tmp_path):
    recording=example_recording(); path=tmp_path/'navigation.jsonl'
    recorder=Recorder(path,recording.bundle,recording.label)
    for event in recording.events: recorder.write(event)
    recorder.close()
    restored=load_recording(path)
    assert replay(restored)==replay(recording)
    recorder.write(recording.events[0]); assert recorder.errors==1
    with pytest.raises(ValueError): Input(t=1.,kind='observations',sequence=1,source='synthetic_estimate',timing=Timing(host_received_s=2.,exposure_s=2.,provenance='synthetic'),observations=[])
    with pytest.raises(ValueError): Policy(delay_bound_s=.1)
    with pytest.raises(ValueError): simulation(recording,step_s=.5)
    with pytest.raises(ValueError): simulation(recording,limit=True)


def test_replay_contract_error_paths_json_load_and_synthetic_simulation_guards(tmp_path,monkeypatch):
    recording=example_recording()
    with pytest.raises(ValueError,match='goal heading'):
        Input.model_construct(t=1.,kind='goal',goal=[1.,1.,1.],heading_rad=True).fields()
    with pytest.raises(ValueError,match='snapshot SHA256'):
        Input(t=1.,kind='snapshot_saved',snapshot_sha256='bad',snapshot_source='synthetic')

    bad=recording.model_dump()
    bad['events'].append({'t':2.,'kind':'snapshot_saved','snapshot_sha256':'a'*64,'snapshot_source':'camera'})
    with pytest.raises(ValueError,match='snapshot/bundle provenance'):
        Recording.model_validate(bad)
    path=tmp_path/'recording.json'; path.write_text(recording.model_dump_json())
    assert load_recording(path).bundle.digest==recording.bundle.digest

    advisory=Advisory(recording.bundle)
    localizer=Localizer(recording.bundle)
    state=apply_input(advisory,localizer,Input(t=1.,kind='resume'))
    assert state['status']=='Fresh acquired pose and goal required'

    class BrokenClose:
        def write(self,*args): pass
        def flush(self): pass
        def close(self): raise OSError('injected close failure')
    monkeypatch.setattr('pathlib.Path.open',lambda *args,**kwargs:BrokenClose())
    recorder=Recorder(tmp_path/'close.jsonl',recording.bundle,'SYNTHETIC close failure')
    recorder.close()
    assert recorder.errors==1

    plant=MockPlant(np.eye(4))
    plant.step([1.,0.,0.],None,.05,.2,.6,.8,2.,4.)
    assert np.isfinite(plant.yaw)
    with pytest.raises(ValueError,match='dynamics'):
        simulation(recording,acceleration_m_s2=0.)


def test_synthetic_mission_simulation_advances_only_after_arrival_and_snapshot():
    from ball_demo.navigation_fixtures import example_mission, simulation_recording
    from ball_demo.mission import Mission
    bundle=example_bundle()
    data=example_mission(bundle).model_dump()
    data['targets'].append({**data['targets'][0],'target_id':'second-target','name':'Second synthetic target'})
    mission=Mission.model_validate(data).validate_bundle(bundle)
    point=mission.targets[0].viewing_position_m
    recording=simulation_recording(bundle,point,point,90.)
    result=simulation(recording,limit=120,mission=mission)
    assert result['mission']['status']=='target_complete'
    assert result['mission']['target_index']==1 and result['mission']['snapshot_status']=='saved'
    assert any(sample.get('mission',{}).get('target_index')==1 for sample in result['samples'])
    assert all(sample['physical_output'] is False for sample in result['samples'])


def test_simulated_swept_envelope_violation_stops_mock_follower(monkeypatch):
    from ball_demo.navigation_replay import MockPlant
    recording=example_recording()
    step=MockPlant.step
    def unsafe_step(self,*args,**kwargs):
        state=step(self,*args,**kwargs)
        if args[0] is not None and np.linalg.norm(self.velocity)>1e-9:
            self.position+=np.array([100.,0.,0.])
        return state
    monkeypatch.setattr(MockPlant,'step',unsafe_step)
    with pytest.raises(ValueError,match='swept-envelope clearance violation'):
        simulation(recording,limit=100)


def test_pose_provenance_and_in_place_corrupted_observations_rejected(bundle):
    p=pose_at(bundle); p.source='vision_estimate'
    guard=PoseGuard(bundle)
    assert not guard.check(p,1.) and 'provenance' in guard.status
    observations=observations_for(bundle,example_pose())
    observations[0].corners[0][0]=float('nan')
    with pytest.raises(ValueError): Localizer(bundle).solve(observations,Timing(host_received_s=1.,exposure_s=1.,provenance='synthetic'),0)
    with pytest.raises(ValueError): vector(['1',2,3])
    with pytest.raises(ValueError): vector(np.array([True,False,True]))


def test_corrected_corner_space_is_not_distortion_corrected_twice(bundle):
    observations=observations_for(bundle,example_pose())
    for o in observations:
        corrected=cv2.undistortPoints(np.array(o.corners).reshape(4,1,2),np.array(bundle.calibration.intrinsics),np.array(bundle.calibration.distortion),P=np.array(bundle.calibration.intrinsics)).reshape(4,2)
        o.corners=corrected.tolist(); o.pixel_space='undistorted'
    solved=Localizer(bundle).solve(observations,Timing(host_received_s=1.,exposure_s=1.,provenance='synthetic'),0,'synthetic_estimate')
    assert np.linalg.norm(solved.position-[1.7,.8,1.2])<1e-5


def test_navigation_state_strictly_validates_nested_mission_and_visibility(bundle):
    a=acquired(bundle); state=a.update(1.1)
    from ball_demo.navigation_fixtures import example_mission
    from ball_demo.arrival import ArrivalTracker
    state['mission']=dict(schema_version=1,mission_id='synthetic-mission',status='ready',target_index=0,
        target_id='target-a',target_name='Target A',target_count=1,arrival=ArrivalTracker().snapshot(),snapshot_status='not_requested',
        snapshot_sha256=None,snapshot_source=None,physical_output=False,uncertainty_provisional=True,physical_acceptance=False)
    assert NavigationState.model_validate(state).mission['status']=='ready'
    bad=copy.deepcopy(state); bad['mission']['snapshot_sha256']='not-a-hash'
    with pytest.raises(ValueError): NavigationState.model_validate(bad)
    bad=copy.deepcopy(state); bad['route_tag_ids']=[[0]] * len(bad['route'])
    with pytest.raises(ValueError): NavigationState.model_validate(bad)
    assert example_mission(bundle).example


def test_mock_plant_respects_acceleration_braking_and_yaw_rate_limits():
    from ball_demo.navigation_replay import MockPlant
    plant=MockPlant(np.eye(4))
    acceleration_limit=.6; braking_limit=.8; yaw_rate_limit=2.; yaw_accel_limit=4.
    for _ in range(10):
        state=plant.step([1.,0.,0.],np.pi/2,.05,.2,acceleration_limit,braking_limit,yaw_rate_limit,yaw_accel_limit)
        assert np.linalg.norm(state['acceleration_m_s2'])<=acceleration_limit+1e-9
        assert abs(state['yaw_rate_rad_s'])<=yaw_rate_limit+1e-9
    before=plant.velocity.copy()
    stopped=plant.step(None,None,.05,.2,acceleration_limit,braking_limit,yaw_rate_limit,yaw_accel_limit)
    assert stopped['commanded_velocity_m_s']==[0.,0.,0.]
    assert 0 < np.linalg.norm(plant.velocity) < np.linalg.norm(before)
    assert np.linalg.norm(stopped['acceleration_m_s2'])<=braking_limit+1e-9


def test_mission_recording_replays_arrival_snapshot_and_operator_advance(bundle):
    mission=example_mission(bundle)
    goal=mission.targets[0].viewing_position_m
    events=[Input(t=1.,kind='mission',mission=mission),Input(t=1.01,kind='mission_start')]
    for sequence,t in enumerate((1.05,1.10,1.15,1.25,1.35)):
        events.append(Input(t=t,kind='observations',sequence=sequence,
            timing=Timing(host_received_s=t,exposure_s=t,provenance='synthetic'),
            observations=observations_for(bundle,example_pose(goal)),source='synthetic_estimate'))
    events.extend([Input(t=1.36,kind='snapshot_saved',snapshot_sha256='c'*64,snapshot_source='synthetic'),
                   Input(t=1.37,kind='mission_advance')])
    recording=Recording(schema_version=1,label='SYNTHETIC mission cycle',bundle=bundle,bundle_sha256=bundle.digest,
                        physical_output=False,events=events)
    result=replay(recording)
    assert result['samples'][-2]['mission']['status']=='target_complete'
    assert result['samples'][-1]['mission']['status']=='complete'
    assert result['samples'][-2]['mission']['snapshot_sha256']=='c'*64
    assert json.dumps(result,sort_keys=True)==json.dumps(replay(recording),sort_keys=True)


def test_advisory_handles_mission_arrival_errors_and_snapshot_failure(bundle,monkeypatch):
    advisory=Advisory(bundle)
    with pytest.raises(ValueError,match='goal heading'): advisory.set_goal([2.,1.,1.],float('nan'))
    with pytest.raises(ValueError,match='goal tag'): advisory.set_goal([2.,1.,1.],tag_id=22)
    with pytest.raises(ValueError,match='No inspection mission'): advisory.mission_snapshot_failed()

    advisory.load_mission(example_mission(bundle))
    advisory.start_mission()
    runner=advisory.mission_runner
    for sequence in range(3):
        advisory.accept(pose_at(bundle,sequence,1.+sequence*.05),1.+sequence*.05)
    monkeypatch.setattr(runner,'observe',lambda *args:(_ for _ in ()).throw(ValueError('arrival estimate rejected')))
    assert advisory.accept(pose_at(bundle,3,1.15),1.15)
    assert not advisory.enabled and advisory.route==[]
    assert runner.status=='waiting_for_localization' and 'arrival estimate rejected' in advisory.status

    runner.status='snapshot_pending'; runner.snapshot_status='requested'
    failed=advisory.mission_snapshot_failed()
    assert failed['status']=='fault' and not advisory.enabled and advisory.route==[]


@pytest.mark.parametrize('axis',range(3))
def test_full_cage_can_span_adjacent_observed_boxes_without_inferred_space(bundle,axis):
    data=bundle.model_dump(); boxes=[]
    for i in range(20):
        lo=[0.,0.,0.]; hi=[4.,4.,3.]
        lo[axis]=i*.15; hi[axis]=(i+1)*.15
        boxes.append({'minimum':lo,'maximum':hi})
    data['map']['observed_free']=boxes
    planner=Planner(Bundle.model_validate(data))
    start=[1.,1.,1.]; end=[2.,2.,2.]
    assert planner.segment_clear(start,end,.3)
    # A one-cell unknown slit is real even if smaller than the cage envelope.
    data['map']['observed_free'].pop(10)
    assert not Planner(Bundle.model_validate(data)).segment_clear(start,end,.3)


def test_swept_union_rejects_unknown_corner_inside_cage_and_honours_work_budget(bundle,monkeypatch):
    import ball_demo.navigation as navigation
    data=bundle.model_dump()
    data['map']['observed_free']=[
        {'minimum':[0.,0.,0.],'maximum':[2.,4.,3.]},
        {'minimum':[2.,0.,0.],'maximum':[4.,2.,3.]}]
    p=Planner(Bundle.model_validate(data))
    assert p.segment_clear([1.,1.,1.],[3.,1.,1.],.2)
    assert not p.segment_clear([1.,1.,1.],[2.,2.,1.],.2)
    monkeypatch.setattr(navigation,'MAX_CLEARANCE_FRAGMENTS',0)
    with pytest.raises(ValueError,match='fragment budget'): p.segment_clear([1.,1.,1.],[3.,1.,1.],.2)
    monkeypatch.setattr(navigation,'MAX_CLEARANCE_FRAGMENTS',4096)
    calls=[]
    def expired():
        calls.append(1)
        if len(calls)>4: raise ValueError('Injected clearance deadline')
    with pytest.raises(ValueError,match='clearance deadline'): p.segment_clear([1.,1.,1.],[3.,1.,1.],.2,expired)
