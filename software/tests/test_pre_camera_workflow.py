"""CLI-to-app integration using RGB bitmaps and a fake D435 SDK only."""
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from ball_demo import cli, mapping
from ball_demo.api import create_app
from ball_demo.engine import Engine
from ball_demo.localization import Localizer, Timing
from ball_demo.mapping import build_map
from ball_demo.map_io import Bundle
from ball_demo.mission import Mission
from ball_demo.navigation_fixtures import example_bundle, example_pose, observations_for, simulation_recording
from ball_demo.navigation_replay import Input, Recording, replay, simulation
from test_pre_camera_capture import automatic_sdk
from test_pre_camera_registration_cli import input_fixture


def test_synthetic_capture_registration_bundle_localization_mission_replay_and_app(tmp_path, monkeypatch):
    source, registration_input, expected_depth_pose = input_fixture(tmp_path / 'registration-input')
    registered = tmp_path / 'offline-registration'
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'nav-register-d435', '--input', str(source), '--output', str(registered)])
    cli.main()
    registration = json.loads((registered / 'registration.json').read_text())
    station_data = json.loads((registered / 'station.json').read_text())
    station_data['uncertainty_m'] = .1  # Synthetic integration budget for generated depth.
    station_path = tmp_path / 'station.json'
    station_path.write_text(json.dumps(station_data))
    survey_path = tmp_path / 'survey.json'
    survey_path.write_text(registration_input.survey.model_dump_json())

    sdk, sdk_state, _, _, _ = automatic_sdk(depth_mm=4000, wide_depth=True)
    actual_capture = mapping.capture_d435
    def fake_capture(station, output, frames=30, registration_survey=None, registration_policy=None):
        return actual_capture(station, output, frames=4, sdk=sdk, registration_survey=registration_survey,
                              registration_policy=registration_policy)
    monkeypatch.setattr(mapping, 'capture_d435', fake_capture)
    captured = tmp_path / 'capture'
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'nav-capture-d435', '--station', str(station_path),
        '--output', str(captured), '--frames', '4', '--registration-survey', str(survey_path)])
    cli.main()
    assert sdk_state['stopped'] and (captured / 'registration.json').exists()
    scan = mapping.Scan.model_validate_json((captured / 'scan.json').read_text())
    assert scan.example and scan.camera_metadata['capture_environment'] == 'injected_test_sdk'
    assert np.linalg.norm(np.array(scan.frames[0].map_from_depth)[:3, 3] - np.array(expected_depth_pose)[:3, 3]) < .05

    rebuilt = tmp_path / 'rebuild'
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'nav-map', str(captured / 'scan.json'), '--output', str(rebuilt)])
    cli.main()
    map_data = json.loads((rebuilt / 'map.json').read_text())
    assert map_data['observed_free'] and json.loads((rebuilt / 'report.json').read_text())['unknown_voxels'] > 0

    template = example_bundle()
    calibration_path, policy_path = tmp_path / 'calibration.json', tmp_path / 'policy.json'
    calibration_path.write_text(template.calibration.model_dump_json())
    policy_path.write_text(template.policy.model_dump_json())
    bundle_path = tmp_path / 'bundle.json'
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'nav-bundle', '--map', str(rebuilt / 'map.json'),
        '--survey', str(survey_path), '--calibration', str(calibration_path), '--policy', str(policy_path),
        '--id', 'synthetic-workflow-v1', '--output', str(bundle_path)])
    cli.main()
    bundle = Bundle.model_validate_json(bundle_path.read_text())

    start, goal = [1.9, 1.6, 1.2], [2., 1.8, 1.2]
    observations = observations_for(bundle, example_pose(start), visible_only=True)
    pose = Localizer(bundle).solve(observations, Timing(host_received_s=1., exposure_s=1., provenance='synthetic'), 0,
                                   'synthetic_estimate')
    assert np.linalg.norm(pose.position - start) < .04 and set(pose.tag_ids) == {0, 1}
    mission = Mission.model_validate({'schema_version': 1, 'mission_id': 'workflow-mission',
        'map_id': bundle.map.map_id, 'map_version': bundle.map.map_version, 'frame_id': bundle.map.frame_id,
        'survey_id': bundle.survey.survey_id, 'example': True, 'targets': [{'target_id': 'target-a',
        'name': 'Synthetic target A', 'tag_id': 0, 'viewing_position_m': goal, 'heading_rad': math.pi / 2}]})
    mission.validate_bundle(bundle)
    mock = simulation(simulation_recording(bundle, start, goal, 90.), mission=mission)
    assert mock['mission']['status'] == 'target_complete' and mock['mission']['snapshot_status'] == 'saved'
    assert mock['mission']['snapshot_source'] == 'synthetic' and len(mock['mission']['snapshot_sha256']) == 64
    assert mock['physical_output'] is False and mock['physical_telemetry'] is None

    events = [Input(t=1., kind='mission', mission=mission), Input(t=1.01, kind='mission_start')]
    for sequence, t in enumerate((1.05, 1.10, 1.15, 1.25, 1.35)):
        events.append(Input(t=t, kind='observations', sequence=sequence,
            timing=Timing(host_received_s=t, exposure_s=t, provenance='synthetic'),
            observations=observations_for(bundle, example_pose(goal)), source='synthetic_estimate'))
    events.extend([Input(t=1.36, kind='snapshot_saved', snapshot_sha256=mock['mission']['snapshot_sha256'], snapshot_source='synthetic'),
                   Input(t=1.37, kind='mission_advance')])
    recording = Recording(schema_version=1, label='SYNTHETIC full workflow', bundle=bundle, bundle_sha256=bundle.digest,
                          physical_output=False, events=events)
    replayed = replay(recording)
    assert replayed['samples'][-1]['mission']['status'] == 'complete'
    replay_path = tmp_path / 'replay.json'
    replay_path.write_text(json.dumps(replayed))
    node = shutil.which('node')
    assert node, 'Browser contract integration requires Node.js'
    script = "const fs=require('fs');const v=require(process.argv[1]);const d=JSON.parse(fs.readFileSync(process.argv[2]));v.validateNavigationReplay(d);v.validateNavigation(d.samples[d.samples.length-1]);"
    subprocess.run([node, '-e', script, str(Path(__file__).resolve().parents[1] / 'ball_demo' / 'static' / 'navigation.js'), str(replay_path)], check=True)

    engine = Engine(tmp_path / 'app', navigation_bundle=bundle, navigation_recording=recording)
    with TestClient(create_app(engine, 'token')) as client:
        deadline = time.monotonic() + 5.
        while time.monotonic() < deadline:
            state = client.get('/api/navigation/mission').json()
            if state and state['status'] == 'complete': break
            time.sleep(.02)
        assert state and state['status'] == 'complete'
        assert client.get('/api/navigation').json()['physical_output'] is False
