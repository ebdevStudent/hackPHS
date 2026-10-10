"""Invented geometry for software tests only. Never a room survey or calibration."""
import json
from pathlib import Path

import numpy as np

from .calibration import invert
from .localization import Observation, Timing, tag_points
from .map_io import Bundle
from .navigation_replay import Input, Recording


def example_bundle():
    identity = np.eye(4).tolist()
    mount = np.eye(4)
    mount[:3, :3] = [[0, 0, 1], [-1, 0, 0], [0, -1, 0]]
    tags = []
    for i, x in enumerate([1.5, 2.5]):
        t = np.eye(4)
        t[:3, :3] = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
        t[:3, 3] = [x, 3., 1.4]
        tags.append({'id': i, 'size_m': .3, 'map_from_tag': t.tolist()})
    extent = {'minimum': [0., 0., 0.], 'maximum': [4., 4., 3.]}
    return Bundle.model_validate({'schema_version': 1, 'bundle_id': 'EXAMPLE-corner-v1',
        'calibration': {'schema_version': 1, 'calibration_id': 'EXAMPLE-camera-v1', 'camera_frame': 'camera_optical', 'aircraft_frame': 'aircraft_flu',
            'image_size': [640, 480], 'intrinsics': [[500., 0., 320.], [0., 500., 240.], [0., 0., 1.]],
            'distortion_model': 'opencv_brown', 'distortion': [-.08, .01, 0., 0., 0.], 'aircraft_from_camera': mount.tolist(),
            'reprojection_rms_px': .2, 'evidence': 'INVENTED EXAMPLE; no hardware measurement', 'example': True},
        'survey': {'schema_version': 1, 'survey_id': 'EXAMPLE-tags-v1', 'map_id': 'EXAMPLE-corner', 'map_version': 1, 'frame_id': 'example_world',
            'units': 'm', 'family': 'tag36h11', 'tags': tags, 'evidence': 'INVENTED EXAMPLE; no tag survey', 'example': True},
        'map': {'schema_version': 1, 'map_id': 'EXAMPLE-corner', 'map_version': 1, 'frame_id': 'example_world', 'axes': 'right_handed_z_up',
            'units': 'm', 'permitted': extent, 'observed_free': [extent], 'occupied': [], 'uncertainty_m': .03,
            'acquired_utc': '2026-10-08T00:00:00Z', 'evidence': 'INVENTED EXAMPLE; not a completed room map', 'example': True}, 'policy': {}})


def example_pose(position=(1.7, .8, 1.2)):
    t = np.eye(4)
    t[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    t[:3, 3] = position
    return t


def observations_for(bundle, transform, visible_only=False, noise_std=0., seed=0):
    import cv2
    if type(noise_std) not in (int, float) or not np.isfinite(noise_std) or noise_std < 0: raise ValueError('Invalid synthetic pixel noise')
    if type(seed) is not int or seed < 0: raise ValueError('Invalid synthetic image seed')
    camera_from_map = invert(transform @ np.array(bundle.calibration.aircraft_from_camera))
    result = []
    rng = np.random.default_rng(seed)
    for tag in bundle.survey.tags:
        t = camera_from_map @ np.array(tag.map_from_tag)
        corners = cv2.projectPoints(tag_points(tag.size_m), cv2.Rodrigues(t[:3, :3])[0], t[:3, 3], np.array(bundle.calibration.intrinsics), np.array(bundle.calibration.distortion))[0].reshape(4, 2)
        if visible_only and (t[2, 3] <= .01 or np.dot(t[:3, 2], t[:3, 3]) >= 0 or np.any(corners < 0) or np.any(corners >= bundle.calibration.image_size)): continue
        if noise_std: corners = corners + rng.normal(0., noise_std, corners.shape)
        result.append(Observation(id=tag.id, corners=corners.tolist()))
    return result


def example_recording():
    b = example_bundle()
    events = [Input(t=1., kind='goal', goal=[2.2, 1.5, 1.3])]
    sequence = 0
    for t in [1.05, 1.10, 1.15, 1.2, 1.25, 1.4, 1.45, 1.5, 1.55]:
        events.append(Input(t=t, kind='observations', sequence=sequence, timing=Timing(host_received_s=t, exposure_s=t, provenance='synthetic'), source='synthetic_estimate', observations=observations_for(b, example_pose())))
        sequence += 1
    events.extend([Input(t=1.16, kind='resume'), Input(t=1.3, kind='loss', reason='EXAMPLE tag occlusion'), Input(t=1.51, kind='resume'), Input(t=1.81, kind='tick')])
    events.sort(key=lambda e: e.t)
    return Recording(schema_version=1, label='SYNTHETIC EXAMPLE / no room measurement', bundle=b, bundle_sha256=b.digest, physical_output=False, events=events)


def example_mission(bundle=None):
    """An invented one-target inspection contract for offline workflow tests."""
    from .mission import Mission
    bundle = bundle or example_bundle()
    mission = Mission.model_validate({'schema_version': 1, 'mission_id': 'synthetic-inspection-v1',
        'map_id': bundle.map.map_id, 'map_version': bundle.map.map_version, 'frame_id': bundle.map.frame_id,
        'survey_id': bundle.survey.survey_id, 'example': bundle.map.example,
        'targets': [{'target_id': 'synthetic-target-a', 'name': 'Synthetic inspection A', 'tag_id': 0,
                     'viewing_position_m': [2.2, 1.5, 1.3], 'heading_rad': float(np.pi / 2)}]})
    return mission.validate_bundle(bundle)


def simulation_recording(bundle, start, goal, yaw_deg=90.):
    """A labeled in-memory simulation copy can use a real D435 map and tag survey."""
    from .navigation import vector
    start, goal = vector(start), vector(goal)
    if type(yaw_deg) not in (int, float) or not np.isfinite(yaw_deg): raise ValueError('Invalid simulation heading')
    base_hash = bundle.digest
    data = bundle.model_dump()
    for key in ('calibration', 'survey', 'map'):
        data[key]['example'] = True
        data[key]['evidence'] = 'SIMULATION COPY of bundle SHA256 ' + base_hash + '; ' + data[key]['evidence']
    b = Bundle.model_validate(data)
    t = np.eye(4)
    yaw = np.deg2rad(yaw_deg)
    t[:3, :3] = [[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]]
    t[:3, 3] = start
    observations = observations_for(b, t, visible_only=True)
    events = [Input(t=1., kind='goal', goal=goal.tolist()), Input(t=1.01, kind='observations', sequence=0,
        observations=observations, timing=Timing(host_received_s=1.01, exposure_s=1.01, provenance='synthetic'), source='synthetic_estimate')]
    return Recording(schema_version=1, label='SIMULATION COPY / source bundle SHA256 ' + base_hash, bundle=b, bundle_sha256=b.digest, physical_output=False, events=events)


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    recording = example_recording()
    from .mapping import Scan, Station
    from .registration import RegistrationInput, RegistrationPolicy, RegistrationResult
    from .arrival import ArrivalPolicy
    from .mission import Mission
    from .navigation import NavigationState
    from .navigation_visibility import VisibleRoute
    for name, data in [('example-bundle.json', recording.bundle.model_dump()), ('synthetic-session.json', recording.model_dump()),
                       ('bundle.schema.json', Bundle.model_json_schema()), ('recording.schema.json', Recording.model_json_schema()),
                       ('scan.schema.json', Scan.model_json_schema()), ('station.schema.json', Station.model_json_schema()),
                       ('navigation-state.schema.json', NavigationState.model_json_schema()), ('visible-route.schema.json', VisibleRoute.model_json_schema()),
                       ('registration-input.schema.json', RegistrationInput.model_json_schema()),
                       ('registration-policy.schema.json', RegistrationPolicy.model_json_schema()),
                       ('registration-result.schema.json', RegistrationResult.model_json_schema()),
                       ('arrival-policy.schema.json', ArrivalPolicy.model_json_schema()), ('mission.schema.json', Mission.model_json_schema()),
                       ('example-mission.json', example_mission(recording.bundle).model_dump()),
                       ('example-station.json', {'schema_version': 1, 'scan_id': 'EXAMPLE-station', 'map_id': 'EXAMPLE-corner', 'map_version': 1,
                        'frame_id': 'example_world', 'permitted': recording.bundle.map.permitted.model_dump(), 'voxel_m': .1, 'uncertainty_m': .03,
                        'max_depth_m': 4., 'map_from_depth': (example_pose() @ np.array(recording.bundle.calibration.aircraft_from_camera)).tolist(),
                        'registration_evidence': 'EXAMPLE ONLY: replace with independently surveyed depth-camera station pose', 'example': True})]:
        (output / name).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    return output
