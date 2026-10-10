"""Backend high-level mission command gates and operational status contracts."""
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ball_demo.api import create_app
from ball_demo.engine import Engine
from ball_demo.mission_control import MissionCommandRequest, MissionController
from ball_demo.roster import Roster


def test_mission_command_contract_is_strict_and_payload_specific():
    valid = MissionCommandRequest.model_validate({
        'request_id': 'follow-01', 'kind': 'follow', 'person_id': 'person-1', 'tag_id': 586,
    })
    assert valid.person_id == 'person-1' and valid.tag_id == 586

    bad_requests = [
        {'request_id': 'follow-02', 'kind': 'follow'},
        {'request_id': 'follow-03', 'kind': 'follow', 'person_id': None},
        {'request_id': 'follow-04', 'kind': 'follow', 'person_id': ' person-1'},
        {'request_id': 'follow-05', 'kind': 'follow', 'person_id': 'person-1', 'tag_id': True},
        {'request_id': 'land-01', 'kind': 'land_site'},
        {'request_id': 'land-02', 'kind': 'land_current', 'site_id': 'site-1'},
        {'request_id': 'stop-01', 'kind': 'stop', 'mission_id': None},
        {'request_id': 'land-point-partial-tag', 'kind': 'land_point',
         'frame_id': 'frame-1', 'x': .5, 'y': .5, 'tag_id': 7},
        {'request_id': 'bad id', 'kind': 'land_current'},
        {'request_id': 'extra-01', 'kind': 'land_current', 'motor': 1},
    ]
    for data in bad_requests:
        with pytest.raises(ValidationError):
            MissionCommandRequest.model_validate(data)

    with pytest.raises(ValueError, match='history_limit'):
        MissionController(history_limit=True)


def test_physical_mission_requests_are_rejected_and_request_ids_are_idempotent():
    controller = MissionController(history_limit=8)
    gates = {
        'person_follow': {'supported': False, 'ready': False, 'reason': 'Follow is not implemented'},
        'landing_current': {'supported': False, 'ready': False, 'reason': 'Landing is not implemented'},
        'landing_site': {'supported': False, 'ready': False, 'reason': 'No site is configured'},
    }
    requests = [
        {'request_id': 'follow-01', 'kind': 'follow', 'person_id': 'person-1', 'tag_id': 7},
        {'request_id': 'land-current-01', 'kind': 'land_current'},
        {'request_id': 'land-site-01', 'kind': 'land_site', 'site_id': 'pad-a'},
        {'request_id': 'stop-01', 'kind': 'stop', 'mission_id': 'mission-a'},
        {'request_id': 'abort-01', 'kind': 'abort', 'mission_id': 'mission-a'},
    ]
    results = []
    for item in requests:
        result, duplicate = controller.submit(item, gates)
        assert not duplicate
        assert result['state'] == 'rejected'
        assert result['physical_output'] is False
        assert result['control_authority'] == 'advisory_only'
        results.append(result)

    assert 'Follow is not implemented' in results[0]['reason']
    assert 'Landing is not implemented' in results[1]['reason']
    assert 'No site is configured' in results[2]['reason']
    assert 'no accepted physical mission' in results[3]['reason']
    assert 'no accepted physical mission' in results[4]['reason']

    duplicate, was_duplicate = controller.submit(requests[0], gates)
    assert was_duplicate and duplicate == results[0]
    assert controller.get('follow-01') == results[0]
    assert 'recent_commands' not in controller.snapshot(gates, {}, None)
    with pytest.raises(ValueError, match='already bound'):
        controller.submit({**requests[0], 'person_id': 'person-2'}, gates)


def test_mock_follow_requires_fresh_observations_and_loss_reacquisition_then_stop_latches():
    controller = MissionController()
    roster = Roster.model_validate({'people': [{'person_id': 'walker', 'display_name': 'Synthetic Walker',
        'tag_family': 'tag36h11', 'tag_id': 7, 'tag_size_m': .18}], 'landing_sites': []})
    gates = {'person_follow': {'supported': True, 'ready': True, 'reason': None}}
    result, duplicate = controller.submit_mock({'request_id': 'follow-mock-1', 'kind': 'follow',
        'person_id': 'walker', 'tag_id': 7, 'tag_family': 'tag36h11'}, gates, roster)
    assert not duplicate and result['state'] == 'accepted' and result['physical_output'] is False
    mission_id = result['mission_id']
    assert controller.ui_mission()['phase'] == 'accepted'
    assert controller.tick_mock(True)['phase'] == 'accepted'
    assert controller.tick_mock(True)['phase'] == 'reacquiring'
    assert controller.tick_mock(True)['phase'] == 'active'
    assert controller.tick_mock(True, target_visible=False)['phase'] == 'lost'
    assert controller.tick_mock(True)['phase'] == 'reacquiring'
    assert controller.tick_mock(True)['phase'] == 'reacquiring'
    assert controller.tick_mock(True)['phase'] == 'active'
    stopped, _ = controller.submit_mock({'request_id': 'stop-mock-1', 'kind': 'stop',
        'mission_id': mission_id}, gates, roster)
    assert stopped['state'] == 'accepted' and controller.ui_mission()['phase'] == 'stopped'
    assert controller.tick_mock(True)['phase'] == 'stopped'
    assert 'motor stop or disarm' in controller.ui_mission()['abort_summary']


def test_mock_video_loss_stops_lifecycle_and_recovery_requires_reacquisition():
    controller = MissionController()
    roster = Roster(people=[{'person_id': 'walker', 'display_name': 'Synthetic Walker',
        'tag_family': 'tag36h11', 'tag_id': 7, 'tag_size_m': .18}])
    gates = {'person_follow': {'supported': True, 'ready': True}}
    result, _ = controller.submit_mock({'request_id': 'source-loss-follow', 'kind': 'follow',
        'person_id': 'walker'}, gates, roster)
    for _ in range(3):
        state = controller.tick_mock(True)
    assert state['phase'] == 'active'
    assert controller.tick_mock(False)['phase'] == 'lost'
    assert controller.tick_mock(True)['phase'] == 'reacquiring'
    assert controller.tick_mock(True)['phase'] == 'reacquiring'
    assert controller.tick_mock(True)['phase'] == 'active'


def test_mock_stop_cancels_a_pending_start_and_abort_is_not_disarm():
    controller = MissionController()
    roster = Roster(people=[{'person_id': 'walker', 'display_name': 'Synthetic Walker',
        'tag_family': 'tag36h11', 'tag_id': 7, 'tag_size_m': .18}])
    gates = {'person_follow': {'supported': True, 'ready': True}}
    stopped, _ = controller.submit_mock({'request_id': 'cancel-pending', 'kind': 'stop',
        'mission_id': None, 'pending_request_id': 'delayed-start'}, gates, roster)
    assert stopped['state'] == 'accepted'
    delayed, _ = controller.submit_mock({'request_id': 'delayed-start', 'kind': 'follow',
        'person_id': 'walker'}, gates, roster)
    assert delayed['state'] == 'rejected' and 'cancelled' in delayed['reason']

    accepted, _ = controller.submit_mock({'request_id': 'follow-then-abort', 'kind': 'follow',
        'person_id': 'walker'}, gates, roster)
    aborted, _ = controller.submit_mock({'request_id': 'abort-mock', 'kind': 'abort',
        'mission_id': accepted['mission_id']}, gates, roster)
    assert aborted['state'] == 'accepted'
    assert controller.ui_mission()['phase'] == 'aborted'
    assert 'no aircraft command' in aborted['reason']


def test_mock_landings_need_simulated_touchdown_and_tag_loss_stops_descent():
    controller = MissionController()
    roster = Roster(landing_sites=[{'site_id': 'pad', 'display_name': 'Synthetic pad',
        'tag_family': 'tag36h11', 'tag_id': 10, 'tag_size_m': .2, 'width_m': .6, 'length_m': .6}])
    gates = {'landing_current': {'supported': True, 'ready': True},
             'landing_site': {'supported': True, 'ready': True}}
    current, _ = controller.submit_mock({'request_id': 'land-current', 'kind': 'land_current'}, gates, roster)
    assert current['state'] == 'accepted'
    assert controller.ui_mission()['phase'] == 'landing'
    assert controller.tick_mock(True, dt_s=.25)['phase'] == 'landing'
    for _ in range(40):
        state = controller.tick_mock(True, dt_s=.25)
        if state['phase'] == 'landed':
            break
    assert state['phase'] == 'landed'
    assert 'Synthetic touchdown event' in state['reason']

    site, _ = controller.submit_mock({'request_id': 'land-pad', 'kind': 'land_site', 'site_id': 'pad'}, gates, roster)
    assert site['state'] == 'accepted'
    before = controller.ui_mission()['progress']
    lost = controller.tick_mock(True, site_visible=False, dt_s=.05)
    assert lost['phase'] == 'lost' and lost['progress'] == before


def test_mock_point_landing_stays_unavailable_and_audio_is_explicitly_rejected():
    controller = MissionController()
    roster = Roster()
    gates = {'landing_point': {'supported': False, 'ready': False,
        'reason': 'Image points cannot be converted into safe landing coordinates.'}}
    point, _ = controller.submit_mock({'request_id': 'land-point', 'kind': 'land_point',
        'frame_id': 'frame-1', 'x': .5, 'y': .5}, gates, roster)
    assert point['state'] == 'rejected' and 'Image points' in point['reason']
    audio, _ = controller.submit_mock({'request_id': 'audio-off', 'kind': 'audio_unavailable'}, {}, roster)
    assert audio['state'] == 'rejected' and 'outside' in audio['reason']


def test_mock_request_idempotency_binds_full_client_payload_digest():
    controller = MissionController()
    roster = Roster()
    request = {'request_id': 'same-id', 'kind': 'land_current',
        'client_payload_sha256': 'a' * 64}
    gates = {'landing_current': {'supported': True, 'ready': True}}
    first, duplicate = controller.submit_mock(request, gates, roster)
    again, duplicate_again = controller.submit_mock(request, gates, roster)
    assert not duplicate and duplicate_again and again == first
    with pytest.raises(ValueError, match='already bound'):
        controller.submit_mock({**request, 'client_payload_sha256': 'b' * 64}, gates, roster)


def test_mock_start_rejections_cover_busy_capability_roster_and_role_mismatch():
    controller = MissionController()
    person = {'person_id': 'walker', 'display_name': 'Synthetic Walker',
              'tag_family': 'tag36h11', 'tag_id': 7, 'tag_size_m': .18}
    roster = Roster(people=[person], landing_sites=[{'site_id': 'pad', 'display_name': 'Synthetic pad',
        'tag_family': 'tag36h11', 'tag_id': 10, 'tag_size_m': .2, 'width_m': .6, 'length_m': .6}])
    ready = {'person_follow': {'supported': True, 'ready': True},
             'landing_site': {'supported': True, 'ready': True}}
    first, _ = controller.submit_mock({'request_id': 'first', 'kind': 'follow', 'person_id': 'walker'}, ready, roster)
    busy, _ = controller.submit_mock({'request_id': 'busy', 'kind': 'land_current'}, ready, roster)
    assert busy['state'] == 'rejected' and 'already active' in busy['reason']
    assert busy['mission_id'] == first['mission_id']

    checks = [
        ({'request_id': 'disabled', 'kind': 'follow', 'person_id': 'absent'}, ready, roster, 'enabled'),
        ({'request_id': 'wrong-id', 'kind': 'follow', 'person_id': 'walker', 'tag_id': 8}, ready, roster, 'tag ID'),
        ({'request_id': 'missing-site', 'kind': 'land_site', 'site_id': 'missing'}, ready, roster, 'Landing site'),
        ({'request_id': 'unready', 'kind': 'land_current'}, {'landing_current': {'supported': True, 'ready': False}}, Roster(), 'Mock capability'),
    ]
    # Each check needs an idle ledger so its rejection reason is not masked by the active mission.
    for request, capabilities, prepared, reason in checks:
        isolated = MissionController()
        result, _ = isolated.submit_mock(request, capabilities, prepared)
        assert result['state'] == 'rejected' and reason in result['reason']

    point = MissionController()
    rejected, _ = point.submit_mock({'request_id': 'point', 'kind': 'land_point',
        'frame_id': 'frame', 'x': .5, 'y': .5}, {'landing_point': {'supported': True, 'ready': True}}, roster)
    assert rejected['state'] == 'rejected' and 'Image points' in rejected['reason']


def test_stop_abort_and_cancelled_request_ledgers_are_bounded_and_match_identity():
    controller = MissionController(history_limit=1)
    roster = Roster()
    gates = {'landing_current': {'supported': True, 'ready': True}}
    for request_id in ('cancel-a', 'cancel-b'):
        controller.submit_mock({'request_id': 'stop-' + request_id, 'kind': 'stop',
            'mission_id': None, 'pending_request_id': request_id}, {}, roster)
    delayed, _ = controller.submit_mock({'request_id': 'cancel-a', 'kind': 'land_current'}, gates, roster)
    assert delayed['state'] == 'accepted'  # Old cancellation was evicted from the bounded ledger.
    mismatch, _ = controller.submit_mock({'request_id': 'abort-wrong', 'kind': 'abort',
        'mission_id': 'not-the-mission'}, {}, roster)
    assert mismatch['state'] == 'rejected'

    active = MissionController()
    result, _ = active.submit_mock({'request_id': 'landing', 'kind': 'land_current'}, gates, roster)
    stop, _ = active.submit_mock({'request_id': 'stop-wrong', 'kind': 'stop',
        'mission_id': 'other'}, {}, roster)
    assert stop['state'] == 'rejected' and 'does not match' in stop['reason']
    abort, _ = active.submit_mock({'request_id': 'abort-right', 'kind': 'abort',
        'mission_id': result['mission_id']}, {}, roster)
    assert abort['state'] == 'accepted' and active.ui_mission()['phase'] == 'aborted'


def test_mock_ticking_and_target_updates_validate_inputs_and_cover_terminal_edges():
    controller = MissionController()
    for kwargs in ({'enabled': 1}, {'enabled': True, 'target_visible': 'yes'},
                   {'enabled': True, 'site_visible': 0}, {'enabled': True, 'dt_s': 0},
                   {'enabled': True, 'dt_s': .251}):
        with pytest.raises(ValueError):
            controller.tick_mock(**kwargs)
    assert controller.tick_mock(False)['phase'] == 'idle'
    with pytest.raises(ValueError, match='Unknown target'):
        controller.update_mock_target('walker', 'unknown-state')
    with pytest.raises(ValueError, match='person_id'):
        controller.update_mock_target(' ', 'tracking')
    with pytest.raises(ValueError, match='reason'):
        controller.update_mock_target('walker', 'lost', 'x' * 241)
    with pytest.raises(ValueError, match='explicit synthetic_touchdown'):
        controller.confirm_mock_touchdown('mission', 'touchdown')
    with pytest.raises(ValueError, match='No matching'):
        controller.confirm_mock_touchdown('mission', 'synthetic_touchdown')

    roster = Roster(people=[{'person_id': 'walker', 'display_name': 'Synthetic Walker',
        'tag_family': 'tag36h11', 'tag_id': 7, 'tag_size_m': .18}])
    gates = {'person_follow': {'supported': True, 'ready': True}}
    accepted, _ = controller.submit_mock({'request_id': 'target-states', 'kind': 'follow',
        'person_id': 'walker'}, gates, roster)
    assert controller.tick_mock(True, target_visible=False)['phase'] == 'accepted'
    assert controller.update_mock_target('runner', 'tracking')['phase'] == 'failed'
    assert controller.tick_mock(True)['phase'] == 'failed'

    controller = MissionController()
    accepted, _ = controller.submit_mock({'request_id': 'target-states-2', 'kind': 'follow',
        'person_id': 'walker'}, gates, roster)
    assert controller.update_mock_target('walker', 'acquiring')['phase'] == 'accepted'
    assert controller.update_mock_target('walker', 'tracking')['phase'] == 'active'
    assert controller.update_mock_target('walker', 'reacquiring')['phase'] == 'reacquiring'
    assert controller.update_mock_target('walker', 'lost')['phase'] == 'lost'
    assert controller.update_mock_target('walker', 'unavailable')['phase'] == 'failed'


def test_mock_landing_pad_reacquires_and_impact_is_failed_not_landed():
    controller = MissionController()
    roster = Roster(landing_sites=[{'site_id': 'pad', 'display_name': 'Synthetic pad',
        'tag_family': 'tag36h11', 'tag_id': 10, 'tag_size_m': .2, 'width_m': .6, 'length_m': .6}])
    gates = {'landing_site': {'supported': True, 'ready': True}}
    result, _ = controller.submit_mock({'request_id': 'pad', 'kind': 'land_site', 'site_id': 'pad'}, gates, roster)
    assert controller.tick_mock(True, site_visible=False)['phase'] == 'lost'
    assert controller.tick_mock(True)['phase'] == 'reacquiring'
    assert controller.tick_mock(True)['phase'] == 'reacquiring'
    assert controller.tick_mock(True)['phase'] == 'landing'

    # Force the pure simulator's excessive-impact branch without touching an actuator.
    controller._mission['landing_altitude_m'] = .01
    controller._mission['landing_descent_rate_m_s'] = .2
    failed = controller.tick_mock(True, dt_s=.1)
    assert failed['phase'] == 'failed' and 'exceeded' in failed['reason']
    with pytest.raises(ValueError, match='No matching'):
        controller.confirm_mock_touchdown(result['mission_id'], 'synthetic_touchdown')


def test_stop_and_abort_never_claim_to_have_operated_hardware():
    controller = MissionController()
    capabilities = {}
    for kind in ('stop', 'abort'):
        request = {'request_id': f'{kind}-active', 'kind': kind, 'mission_id': 'mission-1'}
        result, _ = controller.submit(request, capabilities, {'mission_id': 'mission-1'})
        assert result['state'] == 'rejected'
        assert result['physical_output'] is False
        assert 'not implemented' in result['reason']

    mismatch, _ = controller.submit(
        {'request_id': 'stop-mismatch', 'kind': 'stop', 'mission_id': 'mission-2'},
        capabilities,
        {'mission_id': 'mission-1'},
    )
    assert mismatch['state'] == 'rejected'
    assert 'does not match' in mismatch['reason']


def test_ready_capability_still_cannot_execute_without_a_control_path():
    controller = MissionController()
    ready = {'person_follow': {'supported': True, 'ready': True, 'reason': None}}
    result, duplicate = controller.submit(
        {'request_id': 'follow-ready', 'kind': 'follow', 'person_id': 'person-1'}, ready,
    )
    assert not duplicate
    assert result['state'] == 'rejected'
    assert 'not connected to a verified flight-control path' in result['reason']


def test_mission_command_history_is_bounded_and_evicted_results_are_unknown():
    controller = MissionController(history_limit=2)
    for index in range(3):
        controller.submit(
            {'request_id': f'land-{index}', 'kind': 'land_current'},
            {'landing_current': {'supported': False, 'ready': False}},
        )
    assert controller.get('land-0') is None
    assert controller.get('land-1')['state'] == 'rejected'


def test_engine_status_labels_mock_stale_and_live_sources_and_blocks_unbuilt_features(tmp_path):
    engine = Engine(tmp_path)
    try:
        status = engine.mission_status()
        assert status['mode'] == 'MANUAL'
        assert status['control_authority'] == 'advisory_only'
        assert status['physical_output'] is False
        assert status['active_physical_mission'] is None
        assert status['subsystems']['video']['state'] == 'mock'
        assert status['subsystems']['bridge']['state'] == 'unverified'
        assert status['subsystems']['flight_controller']['state'] == 'unknown'
        assert status['capabilities']['person_follow']['supported'] is False
        assert status['capabilities']['landing_current']['ready'] is False
        assert status['capabilities']['landing_site']['ready'] is False

        engine.source_spec = {'kind': 'camera', 'device': 0}
        engine.frame = SimpleNamespace(captured=time.monotonic() - 5.)
        stale = engine.mission_status()
        assert stale['subsystems']['video']['state'] == 'stale'
        assert stale['capabilities']['physical_yaw_assistance']['ready'] is False

        engine.frame.captured = time.monotonic()
        live = engine.mission_status()
        assert live['subsystems']['video']['state'] == 'live'
        assert live['capabilities']['person_follow']['supported'] is False
        assert live['capabilities']['physical_yaw_assistance']['supported'] is False
    finally:
        engine.stop()


def test_engine_status_covers_video_localization_and_unverified_output_states(tmp_path):
    engine = Engine(tmp_path)
    try:
        engine.source_spec = {'kind': 'camera', 'device': 0}
        assert engine.mission_status()['subsystems']['video']['state'] == 'connecting'
        engine.source_error = 'capture open failed'
        assert engine.mission_status()['subsystems']['video']['state'] == 'fault'
        engine.source_error = None
        engine.video_issue = 'uniform black frames'
        assert engine.mission_status()['subsystems']['video']['state'] == 'degraded'
        engine.video_issue = None
        engine.eof = True
        assert engine.mission_status()['subsystems']['video']['state'] == 'offline'

        engine.eof = False
        engine.source_spec = {'kind': 'recorded', 'path': 'session.mp4'}
        engine.frame = SimpleNamespace(captured=time.monotonic())
        assert engine.mission_status()['subsystems']['video']['state'] == 'recorded'

        engine.source_spec = {'kind': 'camera', 'device': 0}
        engine.bridge.physical_output = True  # Simulated firmware report, not hardware evidence.
        engine.bridge.last_ack = time.monotonic()
        engine.frame.captured = time.monotonic()
        engine.navigation = SimpleNamespace(
            snapshot=lambda now: {
                'pose': None, 'pose_age_s': None, 'status': 'waiting for pose',
                'example': True, 'guidance_enabled': False, 'mission': None,
            },
            stop=lambda: None,
            logging_errors=0,
        )
        status = engine.mission_status()
        assert status['subsystems']['localization']['state'] == 'waiting'
        assert status['subsystems']['bridge']['state'] == 'unverified'
        assert status['subsystems']['bridge']['output_mode_reported'] is True
        assert status['subsystems']['bridge']['physical_output_verified'] is False
        assert status['capabilities']['physical_yaw_assistance']['ready'] is False
        assert status['capabilities']['static_tag_localization']['ready'] is False
        assert status['capabilities']['static_tag_localization']['reason'].startswith('Example map')

        engine.bridge.last_ack = time.monotonic() - 5.
        stale = engine.mission_status()
        assert stale['subsystems']['bridge']['state'] == 'stale'

        engine.bridge.last_ack = time.monotonic()
        engine.bridge.fault = 'bridge fault'
        fault = engine.mission_status()
        assert fault['subsystems']['bridge']['state'] == 'fault'

        engine.bridge.fault = 'none'
        engine.navigation = SimpleNamespace(
            snapshot=lambda now: {
                'pose': {'estimate': True}, 'pose_age_s': 0.05, 'status': 'valid',
                'example': False, 'guidance_enabled': True, 'mission': {'status': 'ready'},
            },
            stop=lambda: None,
            logging_errors=0,
        )
        ready = engine.mission_status()
        assert ready['subsystems']['localization']['state'] == 'localized'
        assert ready['capabilities']['static_tag_localization']['ready'] is True
        assert ready['capabilities']['mapped_guidance']['ready'] is True
        assert ready['capabilities']['inspection_mission']['ready'] is True
        assert ready['capabilities']['physical_yaw_assistance']['ready'] is False
        assert ready['physical_output'] is False
    finally:
        engine.stop()


def test_mission_command_api_auth_replay_conflict_and_status(tmp_path):
    request = {'request_id': 'land-current-1', 'kind': 'land_current'}
    with TestClient(create_app(Engine(tmp_path), token='operator-token')) as client:
        status = client.get('/api/mission/status')
        assert status.status_code == 200
        assert status.json()['physical_output'] is False
        assert status.json()['capabilities']['landing_current']['supported'] is False

        route = '/api/operator/mission-commands'
        assert client.post(route, json=request).status_code == 401
        headers = {'Authorization': 'Bearer operator-token'}
        first = client.post(route, json=request, headers=headers)
        assert first.status_code == 200
        assert first.json()['state'] == 'rejected'
        assert first.json()['physical_output'] is False
        repeated = client.post(route, json=request, headers=headers)
        assert repeated.json() == first.json()

        command_url = route + '/land-current-1'
        assert client.get(command_url).status_code == 401
        assert client.get(command_url, headers=headers).json() == first.json()
        assert client.get(route + '/unknown', headers=headers).status_code == 404
        conflict = client.post(route, json={
            'request_id': 'land-current-1', 'kind': 'follow', 'person_id': 'person-1',
        }, headers=headers)
        assert conflict.status_code == 409
        assert client.post(route, json={**request, 'ignored': True}, headers=headers).status_code == 422
