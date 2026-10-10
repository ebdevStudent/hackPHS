"""Flutter wire-contract integration against the real authenticated FastAPI app."""
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ball_demo.api import create_app
from ball_demo.engine import Engine
from ball_demo.roster import Roster
from ball_demo.sources import Frame


TOKEN = 'portable-contract-token'
AUTH = {'Authorization': f'Bearer {TOKEN}'}


def roster():
    return {'people': [
        {'person_id': 'walker', 'display_name': 'Synthetic Walker', 'tag_family': 'tag36h11',
         'tag_id': 7, 'tag_size_m': .18},
        {'person_id': 'runner', 'display_name': 'Synthetic Runner', 'tag_family': 'tag36h11',
         'tag_id': 8, 'tag_size_m': .18},
    ], 'landing_sites': [
        {'site_id': 'pad-a', 'display_name': 'Synthetic Pad A', 'tag_family': 'tag36h11',
         'tag_id': 10, 'tag_size_m': .2, 'width_m': .6, 'length_m': .6},
    ]}


def seed_preview(engine, marker_id=None, *, kind='synthetic'):
    image = np.full((480, 640, 3), 255, np.uint8)
    if marker_id is not None:
        marker = cv2.aruco.generateImageMarker(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), marker_id, 180)
        image[150:330, 230:410] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    ok, encoded = cv2.imencode('.jpg', image)
    assert ok
    engine.source_spec = {'kind': kind, 'scenario': 'moving'}
    engine.frame = Frame(image, time.monotonic(), 5, {})
    engine.preview = encoded.tobytes()
    engine.source_error = engine.video_issue = None
    engine.eof = False


@pytest.fixture
def api(tmp_path):
    from ball_demo.portable_demo import demo_calibration
    engine = Engine(tmp_path, roster=roster(), portable_calibration=demo_calibration(), portable_delay_s=.01)
    client = TestClient(create_app(engine, TOKEN))
    yield client, engine
    client.close()
    engine.stop()


def test_snapshot_matches_flutter_v1_shape_and_keeps_mock_source_explicit(api):
    client, engine = api
    seed_preview(engine)
    response = client.get('/api/ui/v1/snapshot', headers=AUTH)
    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot['api_version'] == 1 and snapshot['operator_authorized'] is True
    assert snapshot['source'] == 'mock'
    assert snapshot['roster'][0]['detection_state'] == 'unavailable'
    assert snapshot['roster'][0]['available'] is True
    assert snapshot['camera']['name'].endswith('(mock)')
    assert snapshot['mission'] == {'type': 'none', 'phase': 'idle'}
    assert snapshot['audio']['state'] == 'unavailable'
    assert {item['state'] for item in snapshot['components']} <= {
        'ready', 'degraded', 'fault', 'offline', 'unknown', 'mock'}
    assert set(snapshot['capabilities']) == {
        'follow', 'land_current', 'land_point', 'land_tag', 'audio_receive', 'audio_transmit', 'tts'}


def test_reads_are_anonymous_but_commands_require_operator_authentication(api):
    client, engine = api
    assert client.get('/api/ui/v1/snapshot').json()['operator_authorized'] is False
    assert client.get('/api/ui/v1/commands/missing').json()['state'] == 'unknown'
    assert client.get('/api/ui/v1/snapshot', headers={'Authorization': 'Bearer wrong'}).status_code == 401
    assert client.post('/api/ui/v1/commands', json={}).status_code == 401
    seed_preview(engine)
    still = client.post('/api/ui/v1/camera/still', json={})
    assert still.status_code == 200
    frame = still.json()['frame']
    assert frame['image_path'].startswith('/api/ui/v1/camera/frames/')
    fetched = client.get(frame['image_path'])
    assert fetched.status_code == 200 and fetched.headers['content-type'].startswith('image/jpeg')
    assert fetched.content == engine.preview
    assert client.get(frame['image_path'], headers={'Authorization': 'Bearer wrong'}).status_code == 401


def test_cors_allows_the_published_operator_origin_and_required_headers(api):
    client, _ = api
    origin = 'https://chessdroid108.github.io'
    reply = client.options('/api/ui/v1/commands', headers={
        'Origin': origin, 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type,x-operator-client'})
    assert reply.status_code == 200
    assert reply.headers['access-control-allow-origin'] == origin
    assert 'authorization' in reply.headers['access-control-allow-headers'].lower()
    denied = client.options('/api/ui/v1/commands', headers={
        'Origin': 'https://untrusted.example', 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization'})
    assert 'access-control-allow-origin' not in denied.headers


def test_mock_follow_reuses_idempotent_request_and_stop_cancels_it(api):
    client, engine = api
    seed_preview(engine)
    request = {'request_id': 'follow-001', 'kind': 'follow', 'payload': {
        'person_id': 'walker', 'tag_id': 7, 'tag_family': 'tag36h11'}}
    first = client.post('/api/ui/v1/commands', json=request, headers=AUTH)
    duplicate = client.post('/api/ui/v1/commands', json=request, headers=AUTH)
    assert first.status_code == 200 and duplicate.json() == first.json()
    assert first.json()['state'] == 'accepted'
    assert engine.mission_control.ui_mission()['phase'] == 'accepted'
    ticked = engine.mission_control.tick_mock(True)
    assert ticked['phase'] == 'accepted'
    assert engine.mission_control.tick_mock(True)['phase'] == 'reacquiring'
    assert engine.mission_control.tick_mock(True)['phase'] == 'active'
    stop = client.post('/api/ui/v1/commands', json={'request_id': 'stop-001', 'kind': 'stop',
        'payload': {'mission_id': engine.mission_control.ui_mission()['mission_id'],
                    'pending_request_id': 'follow-001'}}, headers=AUTH)
    assert stop.status_code == 200 and stop.json()['state'] == 'accepted'
    assert engine.mission_control.tick_mock(True)['phase'] == 'stopped'
    assert client.get('/api/ui/v1/commands/follow-001', headers=AUTH).json()['state'] == 'accepted'
    assert client.get('/api/ui/v1/commands/not-seen', headers=AUTH).json()['state'] == 'unknown'


def test_conflicting_request_reuse_and_invalid_payloads_are_rejected(api):
    client, engine = api
    seed_preview(engine)
    body = {'request_id': 'same-follow', 'kind': 'follow', 'payload': {'person_id': 'walker'}}
    assert client.post('/api/ui/v1/commands', json=body, headers=AUTH).status_code == 200
    changed = {**body, 'payload': {'person_id': 'runner'}}
    conflict = client.post('/api/ui/v1/commands', json=changed, headers=AUTH)
    assert conflict.status_code == 409 and 'already bound' in conflict.json()['detail']
    for invalid in (
        {'request_id': 'bad-unknown', 'kind': 'follow', 'payload': {'person_id': 'missing'}},
        {'request_id': 'bad-extra', 'kind': 'land', 'payload': {'mode': 'current_position', 'motors': True}},
        {'request_id': 'bad-number', 'kind': 'land', 'payload': {'mode': 'camera_point', 'frame_id': 'x', 'point': {'x': True, 'y': .5}}},
        {'request_id': 'bad-audio', 'kind': 'audio_uplink', 'payload': {'enabled': 'yes', 'sequence': 1, 'lease_ms': 600}},
        {'request_id': 'too-large', 'kind': 'speak', 'payload': {'text': 'x' * 9000, 'voice_id': None}},
    ):
        response = client.post('/api/ui/v1/commands', json=invalid, headers=AUTH)
        assert response.status_code in (409, 422)
    assert engine.controller.enabled is False and engine.controller.yaw == 0


def test_camera_tags_can_select_only_a_configured_pad_and_live_follow_stays_rejected(api):
    client, engine = api
    seed_preview(engine, marker_id=10, kind='camera')
    snapshot = client.get('/api/ui/v1/snapshot', headers=AUTH).json()
    assert snapshot['source'] == 'live'
    assert snapshot['camera']['frame']['tags'][0]['tag_id'] == 10
    descriptor = snapshot['camera']['frame']
    landing = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'live-pad', 'kind': 'land', 'payload': {'mode': 'apriltag',
            'frame_id': descriptor['frame_id'], 'point': {'x': .5, 'y': .5},
            'tag_id': 10, 'tag_family': 'tag36h11'}})
    assert landing.status_code == 200 and landing.json()['state'] == 'rejected'
    assert engine.mission_control.ui_mission()['phase'] == 'idle'
    follow = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'live-follow', 'kind': 'follow', 'payload': {'person_id': 'walker'}})
    assert follow.status_code == 200 and follow.json()['state'] == 'rejected'
    assert follow.json()['reason']
    assert engine.controller.enabled is False and engine.controller.yaw == 0


def test_landing_point_is_rejected_and_audio_is_reported_unavailable(api):
    client, engine = api
    seed_preview(engine)
    frame = client.post('/api/ui/v1/camera/still', json={}, headers=AUTH).json()['frame']
    point = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'point-land', 'kind': 'land', 'payload': {'mode': 'camera_point',
            'frame_id': frame['frame_id'], 'point': {'x': .5, 'y': .5}}})
    assert point.status_code == 200 and point.json()['state'] == 'rejected'
    audio = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'speak-no-audio', 'kind': 'speak', 'payload': {'text': 'Hello', 'voice_id': None}})
    assert audio.status_code == 200 and audio.json()['state'] == 'rejected'
    assert 'outside' in audio.json()['reason']
    assert engine.controller.enabled is False and engine.controller.yaw == 0


def test_frame_from_old_camera_generation_cannot_be_used_for_landing(api):
    client, engine = api
    seed_preview(engine)
    frame = client.post('/api/ui/v1/camera/still', json={}, headers=AUTH).json()['frame']
    engine.generation += 1
    response = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'old-frame-point', 'kind': 'land', 'payload': {'mode': 'camera_point',
            'frame_id': frame['frame_id'], 'point': {'x': .5, 'y': .5}}})
    assert response.status_code == 409 and 'previous camera session' in response.json()['detail']


def test_camera_states_roster_detection_and_detector_failures_are_explicit(api, monkeypatch):
    client, engine = api
    no_frame = client.get('/api/ui/v1/snapshot').json()
    assert no_frame['camera']['state'] == 'reconnecting'
    seed_preview(engine, marker_id=7, kind='camera')
    live = client.get('/api/ui/v1/snapshot').json()
    assert live['roster'][0]['detection_state'] == 'visible'
    assert live['roster'][0]['available'] is True
    assert live['roster'][1]['detection_state'] == 'lost'
    engine.roster = Roster(people=[{**roster()['people'][0], 'enabled': False}])
    disabled = client.get('/api/ui/v1/snapshot').json()['roster'][0]
    assert disabled['detection_state'] == 'unavailable' and disabled['available'] is False

    engine.roster = Roster.model_validate(roster())
    portable = client.app.state.portable_api
    def fail_detection(_image):
        raise ValueError('simulated detector failure')
    monkeypatch.setattr(portable.detector, 'detect', fail_detection)
    engine.frame.index += 1
    degraded = client.get('/api/ui/v1/snapshot').json()
    assert any(row['id'] == 'apriltag-detector' and row['state'] == 'degraded'
               for row in degraded['components'])
    assert degraded['roster'][0]['detection_state'] == 'unavailable'
    engine.source_error = 'capture failed'
    assert client.get('/api/ui/v1/snapshot').json()['camera']['state'] == 'offline'
    engine.source_error = None
    engine.eof = True
    assert client.get('/api/ui/v1/snapshot').json()['camera']['state'] == 'offline'


def test_still_requires_a_fresh_bounded_frame_and_reuses_immutable_frame_identity(api):
    client, engine = api
    assert client.post('/api/ui/v1/camera/still', json={}).status_code == 409
    seed_preview(engine)
    portable = client.app.state.portable_api
    first = client.post('/api/ui/v1/camera/still', json={}).json()['frame']
    second = client.post('/api/ui/v1/camera/still', json={}).json()['frame']
    assert first['frame_id'] == second['frame_id']
    assert first['captured_at'].endswith('Z') and first['valid_for_ms'] == 4000
    engine.frame.index += 1
    engine.preview = b'x' * (8 * 1024 * 1024 + 1)
    assert client.post('/api/ui/v1/camera/still', json={}).status_code == 409

    portable.frame_cache.clear()
    portable.frame_cache_bytes = 0
    for index in range(11):
        frame_id = f'test-{index}'
        portable.frame_cache[frame_id] = {'jpeg': b'abc', 'created': time.monotonic(), 'key': (0, index)}
        portable.frame_cache_bytes += 3
    portable.current_frame_id = 'test-0'
    portable.current_key = (0, 0)
    portable._trim_frames()
    assert len(portable.frame_cache) == 10
    assert portable.current_frame_id is None and portable.current_key is None
    portable.frame_cache['expired'] = {'jpeg': b'1234', 'created': time.monotonic() - 16, 'key': (0, 0)}
    portable.frame_cache_bytes += 4
    portable._trim_frames()
    assert 'expired' not in portable.frame_cache


def test_command_adapter_rejects_malformed_requests_and_handles_mock_land_stop_abort(api):
    client, engine = api
    seed_preview(engine)
    assert client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'family-mismatch', 'kind': 'follow',
        'payload': {'person_id': 'walker', 'tag_family': 'tag25h9'}}).status_code == 409
    assert client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'tag-mismatch', 'kind': 'follow',
        'payload': {'person_id': 'walker', 'tag_id': 8}}).status_code == 409
    assert client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'bad-id', 'kind': 'bad kind', 'payload': {}}).status_code == 409
    assert client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'stop-no-target', 'kind': 'stop',
        'payload': {'mission_id': None, 'pending_request_id': None}}).status_code == 409
    assert client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'unknown-mode', 'kind': 'land', 'payload': {'mode': 'unknown'}}).status_code == 409

    start = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'current-land', 'kind': 'land',
        'payload': {'mode': 'current_position'}})
    assert start.status_code == 200 and start.json()['state'] == 'accepted'
    mission_id = engine.mission_control.ui_mission()['mission_id']
    abort = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'abort-land', 'kind': 'abort', 'payload': {'mission_id': mission_id}})
    assert abort.status_code == 200 and abort.json()['state'] == 'accepted'
    assert engine.controller.enabled is False and engine.controller.yaw == 0


def test_land_tag_and_recorded_sources_reject_unconfigured_or_non_mock_actions(api):
    client, engine = api
    seed_preview(engine, marker_id=7, kind='synthetic')
    descriptor = client.get('/api/ui/v1/snapshot').json()['camera']['frame']
    wrong_role = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'person-is-not-pad', 'kind': 'land', 'payload': {'mode': 'apriltag',
            'frame_id': descriptor['frame_id'], 'point': {'x': .5, 'y': .5},
            'tag_id': 7, 'tag_family': 'tag36h11'}})
    assert wrong_role.status_code == 409 and 'configured AprilTag landing site' in wrong_role.json()['detail']
    camera_point_with_tag = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'point-with-tag', 'kind': 'land', 'payload': {'mode': 'camera_point',
            'frame_id': descriptor['frame_id'], 'point': {'x': .5, 'y': .5},
            'tag_id': 10, 'tag_family': 'tag36h11'}})
    assert camera_point_with_tag.status_code == 409

    engine.source_spec = {'kind': 'recorded', 'path': 'recorded-test.avi'}
    result = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'recorded-follow', 'kind': 'follow', 'payload': {'person_id': 'walker'}})
    assert result.status_code == 200 and result.json()['state'] == 'rejected'
    assert engine.controller.enabled is False and engine.controller.yaw == 0


def test_preview_descriptor_describes_the_encoded_frame_even_when_capture_has_advanced(api):
    client, engine = api
    seed_preview(engine, marker_id=10)
    engine.preview_frame = engine.frame
    encoded = engine.preview
    engine.frame = Frame(np.full((200, 300, 3), 255, np.uint8), time.monotonic(), 6, {})
    descriptor = client.post('/api/ui/v1/camera/still', json={}).json()['frame']
    assert (descriptor['width'], descriptor['height']) == (640, 480)
    assert descriptor['tags'][0]['tag_id'] == 10
    assert client.get(descriptor['image_path']).content == encoded
    engine.preview_frame.captured = time.monotonic() - 1
    assert client.post('/api/ui/v1/camera/still', json={}).status_code == 409


def test_stale_video_unknown_frames_and_unconfigured_tracking_disable_readiness(api):
    client, engine = api
    seed_preview(engine)
    engine.frame.captured = time.monotonic() - 1
    snapshot = client.get('/api/ui/v1/snapshot').json()
    assert snapshot['camera']['state'] == 'stale'
    assert not snapshot['capabilities']['follow']['ready']
    assert client.get('/api/ui/v1/camera/frames/missing.jpg').status_code == 404
    seed_preview(engine)
    engine.portable = None
    snapshot = client.get('/api/ui/v1/snapshot').json()
    assert not snapshot['capabilities']['follow']['ready']
    assert 'calibrated' in snapshot['capabilities']['follow']['reason']


@pytest.mark.parametrize('payload', [
    {'person_id': ' walker'},
    {'mode': 'camera_point', 'frame_id': 'unknown', 'point': {'x': 1.01, 'y': .5}},
    {'mode': 'camera_point', 'frame_id': 'unknown', 'point': {'x': .5, 'y': .5}},
    {'mode': 'apriltag', 'frame_id': 'unknown', 'point': {'x': .5, 'y': .5}},
    {'mode': 'apriltag', 'frame_id': 'unknown', 'point': {'x': .5, 'y': .5}, 'tag_id': True, 'tag_family': 'tag36h11'},
])
def test_trimmed_identity_normalized_points_and_complete_tag_identity_are_required(api, payload):
    client, engine = api
    seed_preview(engine)
    response = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'malformed', 'kind': 'follow' if 'person_id' in payload else 'land', 'payload': payload})
    assert response.status_code == 409
    assert engine.mission_control.ui_mission()['phase'] == 'idle'


def test_nonfinite_json_and_payload_budget_are_rejected_before_mission_mutation(api):
    from ball_demo.ui_api import UICommand
    client, engine = api
    portable = client.app.state.portable_api
    for payload, message in (({'point': float('nan')}, 'finite JSON'), ({'text': 'x' * 9000}, '8 KB')):
        with pytest.raises(ValueError, match=message):
            portable.command(UICommand(request_id='invalid-json', kind='land', payload=payload))
    assert engine.mission_control.ui_mission()['phase'] == 'idle'


def test_mock_pad_landing_selects_the_visible_configured_pad_and_audio_stays_unavailable(api):
    client, engine = api
    seed_preview(engine, marker_id=10)
    descriptor = client.post('/api/ui/v1/camera/still', json={}).json()['frame']
    response = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'pad-land', 'kind': 'land', 'payload': {'mode': 'apriltag',
            'frame_id': descriptor['frame_id'], 'point': {'x': .5, 'y': .5}, 'tag_id': 10, 'tag_family': 'tag36h11'}})
    assert response.status_code == 200 and response.json()['state'] == 'accepted'
    assert engine.mission_control.simulation_mission()['site_id'] == 'pad-a'
    response = client.post('/api/ui/v1/commands', headers=AUTH, json={
        'request_id': 'voice-unavailable', 'kind': 'speak', 'payload': {'text': 'Test', 'voice_id': 'test-voice'}})
    assert response.status_code == 200 and response.json()['state'] == 'rejected'


def test_live_tracking_is_reported_as_observation_only(api):
    client, engine = api
    seed_preview(engine, kind='camera')
    component = next(row for row in client.get('/api/ui/v1/snapshot').json()['components'] if row['id'] == 'relative-target')
    assert component['state'] == 'degraded'
    engine.portable.report.update(state='tracking', reason=None)
    snapshot = client.get('/api/ui/v1/snapshot').json()
    assert next(row for row in snapshot['components'] if row['id'] == 'relative-target')['state'] == 'ready'
    assert not snapshot['capabilities']['follow']['ready']


def test_mock_roster_reports_detected_pixels_with_synthetic_provenance(api):
    client, engine = api
    seed_preview(engine, marker_id=7)
    person = client.get('/api/ui/v1/snapshot').json()['roster'][0]
    assert person['detection_state'] == 'visible' and person['available']
    assert 'Generated' in person['reason']
