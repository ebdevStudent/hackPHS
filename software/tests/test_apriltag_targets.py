"""AprilTag follow/landing targets, the tag kit, and their wiring into the unchanged yaw path."""
import argparse
import json
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ball_demo import tag_kit
from ball_demo.api import create_app
from ball_demo.config import Settings
from ball_demo.control import Controller
from ball_demo.engine import Engine
from ball_demo.roster import Roster
from ball_demo.sources import Frame
from ball_demo.tag_target import TargetDetector, draw_overlay, focal_px

pytestmark = pytest.mark.skipif(not hasattr(cv2, 'aruco'), reason='OpenCV aruco module required')


def scene(*tags, size=(480, 640)):
    """White frame with (tag_id, x_left, y_top, side_px) tags pasted in."""
    image = np.full((*size, 3), 255, np.uint8)
    for tag_id, x, y, side in tags:
        image[y:y + side, x:x + side] = cv2.cvtColor(tag_kit.tag_image(tag_id, side), cv2.COLOR_GRAY2BGR)
    return image


def roster(*entries):
    r = Roster()
    for role, name, size, tag_id in entries:
        r, _ = tag_kit.add(r, role, name, size, tag_id=tag_id)
    return r


TEAM = roster(('person', 'Rahul', .12, 3), ('pad', 'Pad', .16, 7))


class Clock:
    def __init__(self): self.t = 100.
    def __call__(self): return self.t


# --- target selection ---------------------------------------------------------------------------

def test_follow_picks_registered_person_with_ball_schema_and_range():
    detector = TargetDetector(lambda: TEAM)
    settings = Settings(target_mode='tag')
    detection = detector.detect(scene((3, 450, 200, 80), (7, 100, 100, 40)), settings)
    assert detection['tag_id'] == 3 and detection['tag_role'] == 'person' and detection['tag_name'] == 'Rahul'
    assert set(['x', 'y', 'area', 'bbox', 'error', 'quality']) <= set(detection)
    assert 0 < detection['error'] <= 1 and 0 < detection['quality'] <= 1      # tag is right of centre
    assert detection['range_m'] == pytest.approx(focal_px(settings) * .12 / detection['side_px'], abs=.01)
    assert detector.guidance['stage'] == 'TRACK' and 'Rahul' in detector.guidance['cue']
    assert {t['id'] for t in detector.guidance['tags_seen']} == {3, 7}
    json.dumps(detection); json.dumps(detector.guidance)


def test_left_tag_gives_negative_error_and_controller_turns_the_same_way_as_for_the_ball():
    detector, controller = TargetDetector(lambda: TEAM), Controller()
    settings = Settings(target_mode='tag')
    controller.enable(True)
    yaw = 0
    for _ in range(settings.acquire_frames + 3):
        yaw = controller.frame(detector.detect(scene((3, 60, 200, 80)), settings), settings, .05)
    assert controller.state == 'LOCKED' and yaw < 0


def test_landing_mode_selects_pad_and_explicit_id_overrides_roster():
    detector = TargetDetector(lambda: TEAM)
    image = scene((3, 450, 200, 80), (7, 100, 100, 40))
    assert detector.detect(image, Settings(target_mode='landing'))['tag_id'] == 7
    assert detector.detect(image, Settings(target_mode='tag', tag_id=7))['tag_id'] == 7
    assert detector.detect(image, Settings(target_mode='tag', tag_id=9)) is None


def test_without_people_any_non_pad_tag_is_followed_using_default_size():
    pads_only = roster(('pad', 'Pad', .16, 7))
    detector = TargetDetector(lambda: pads_only)
    settings = Settings(target_mode='tag', tag_size_m=.2)
    detection = detector.detect(scene((5, 300, 200, 60), (7, 100, 100, 40)), settings)
    assert detection['tag_id'] == 5 and detection['tag_role'] == 'unregistered'
    assert detection['range_m'] == pytest.approx(focal_px(settings) * .2 / detection['side_px'], abs=.01)


def test_registered_people_present_means_unregistered_tags_are_ignored():
    detector = TargetDetector(lambda: TEAM)
    assert detector.detect(scene((5, 300, 200, 60)), Settings(target_mode='tag')) is None
    assert detector.guidance['stage'] == 'SEARCH'


def test_switching_target_tag_is_reported_as_reacquired_and_restarts_acquisition():
    team = roster(('person', 'A', .12, 3), ('person', 'B', .12, 4))
    detector, controller = TargetDetector(lambda: team), Controller()
    settings = Settings(target_mode='tag')
    controller.enable(True)
    for _ in range(settings.acquire_frames + 1):
        controller.frame(detector.detect(scene((3, 450, 200, 80)), settings), settings, .05)
    assert controller.state == 'LOCKED'
    detection = detector.detect(scene((4, 100, 200, 80)), settings)
    assert detection['reacquired'] is True
    assert controller.frame(detection, settings, .05) == 0 and controller.state == 'SEARCHING'


def test_color_mode_is_unchanged_and_has_no_guidance():
    detector = TargetDetector(lambda: TEAM)
    assert detector.detect(scene((3, 450, 200, 80)), Settings()) is None
    assert detector.guidance is None


# --- landing cues (pilot guidance only) ---------------------------------------------------------

def test_landing_stages_align_approach_descend_then_over_pad_after_it_drops_below():
    clock = Clock()
    detector = TargetDetector(lambda: TEAM, clock)
    settings = Settings(target_mode='landing', land_range_m=.6)
    detector.detect(scene((7, 20, 200, 40)), settings)                    # far left
    assert detector.guidance['stage'] == 'ALIGN'
    detector.detect(scene((7, 300, 200, 30)), settings)                   # centred, small = far
    assert detector.guidance['stage'] == 'APPROACH' and 'forward' in detector.guidance['cue']
    side = int(focal_px(settings) * .16 / .5) + 1                          # ~0.5 m away
    detector.detect(scene((7, 320 - side // 2, 470 - side, side)), settings)   # centred, low in frame
    assert detector.guidance['stage'] == 'DESCEND'
    clock.t += .5
    detector.detect(scene(), settings)
    assert detector.guidance['stage'] == 'OVER PAD'
    clock.t += 2
    detector.detect(scene(), settings)
    assert detector.guidance['stage'] == 'SEARCH'


def test_overlay_draws_without_error():
    detector = TargetDetector(lambda: TEAM)
    image = scene((3, 450, 200, 80))
    detector.detect(image, Settings(target_mode='tag'))
    before = image.copy()
    draw_overlay(image, detector.guidance)
    assert not np.array_equal(before, image)


# --- tag kit ------------------------------------------------------------------------------------

def test_kit_add_assigns_free_ids_and_rejects_duplicates(tmp_path):
    r, first = tag_kit.add(Roster(), 'person', 'Rahul', .12)
    r, second = tag_kit.add(r, 'pad', 'Landing pad', .16)
    assert (first.tag_id, second.tag_id) == (0, 1)
    assert second.width_m >= .3 and second.length_m == second.width_m
    with pytest.raises(ValueError, match='already'):
        tag_kit.add(r, 'person', 'Other', .1, tag_id=1)
    with pytest.raises(ValueError):
        tag_kit.add(r, 'person', '  ', .1)
    with pytest.raises(ValueError):
        tag_kit.add(r, 'person', 'Big', 3)
    r, third = tag_kit.add(r, 'person', 'Rahul', .1)                     # same name -> distinct id
    assert third.person_id != first.person_id
    path = tag_kit.save(r, tmp_path / 'sub' / 'roster.json')
    loaded = tag_kit.load_or_new(path)
    assert [e[1] for e in tag_kit.entries(loaded)] == [0, 1, 2]
    assert tag_kit.entries(tag_kit.remove(loaded, 1)) == [e for e in tag_kit.entries(loaded) if e[1] != 1]
    with pytest.raises(ValueError):
        tag_kit.remove(loaded, 99)


def test_printed_tags_are_exact_size_and_detectable():
    pages = tag_kit.render_pages([(3, .12, 'Rahul'), (7, .16, 'Pad'), (11, .05, 'small')])
    assert pages and pages[0].size == (2550, 3300)
    image = cv2.cvtColor(np.array(pages[0]), cv2.COLOR_GRAY2BGR)
    found = tag_kit.TagScanner().scan(image)
    assert 3 in [i for i, _ in found]
    corners = dict(found)[3]
    side = np.linalg.norm(corners[1] - corners[0])
    assert side == pytest.approx(.12 / .0254 * 300, rel=.01)               # 12.0 cm at 300 dpi


def test_tag_too_big_for_the_page_is_refused():
    with pytest.raises(ValueError, match='does not fit'):
        tag_kit.render_pages([(1, .30, 'huge')])


def test_kit_cli_add_list_print_and_detect(tmp_path, capsys):
    parser = argparse.ArgumentParser()
    tag_kit.add_arguments(parser)
    roster_path = str(tmp_path / 'roster.json')
    run = lambda *argv: tag_kit.run(parser.parse_args(['--roster', roster_path, *argv]))
    run('add', 'person', 'Rahul', '--size-cm', '12')
    run('add', 'pad', 'Pad', '--size-cm', '16', '--id', '7')
    run('list')
    out = capsys.readouterr().out
    assert 'Added tag 0' in out and 'Added tag 7' in out and 'Rahul' in out
    pdf = tmp_path / 'tags.pdf'
    run('print', '--output', str(pdf))
    assert pdf.exists() and pdf.read_bytes()[:4] == b'%PDF'
    shot = tmp_path / 'shot.png'
    cv2.imwrite(str(shot), scene((0, 300, 200, 90), (7, 60, 60, 50), (9, 500, 300, 40), size=(480, 720)))
    run('detect', '--image', str(shot), '--annotate', str(tmp_path / 'out.png'))
    out = capsys.readouterr().out
    assert 'person: Rahul' in out and 'landing pad: Pad' in out and 'NOT in roster' in out
    assert (tmp_path / 'out.png').exists()


def test_wizard_adds_tags_and_writes_printable(tmp_path, monkeypatch):
    answers = iter(['f', 'Rahul', '12', 'l', '', '', 'x', 'd'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))
    monkeypatch.chdir(tmp_path)
    lines = []
    r = tag_kit.wizard(tmp_path / 'roster.json', lines.append)
    assert [(p.display_name, p.tag_size_m) for p in r.people] == [('Rahul', .12)]
    assert [(s.display_name, s.tag_size_m) for s in r.landing_sites] == [('Landing pad', .16)]
    assert (tmp_path / 'runs' / 'apriltags.pdf').exists()


# --- API / engine -------------------------------------------------------------------------------

@pytest.fixture
def api(tmp_path):
    path = tmp_path / 'roster.json'
    engine = Engine(tmp_path, roster_path=str(path))
    client = TestClient(create_app(engine, 'tag-token'))
    yield client, engine, {'Authorization': 'Bearer tag-token'}, path
    client.close(); engine.stop()


def test_api_sets_target_mode_and_rejects_bad_values(api):
    client, engine, auth, _ = api
    reply = client.post('/api/operator/settings', headers=auth,
                        json={'target_mode': 'landing', 'tag_id': 7, 'land_range_m': .8, 'camera_hfov_deg': 150})
    assert reply.status_code == 200
    assert (engine.settings.target_mode, engine.settings.tag_id, engine.settings.land_range_m) == ('landing', 7, .8)
    for bad in [{'target_mode': 'follow'}, {'target_mode': 1}, {'tag_id': 587}, {'tag_id': -2},
                {'tag_id': '3'}, {'land_range_m': 0}, {'tag_size_m': True}]:
        assert client.post('/api/operator/settings', headers=auth, json=bad).status_code == 422
    assert engine.settings.target_mode == 'landing'


def test_roster_reload_picks_up_tags_added_by_the_kit(api):
    client, engine, auth, path = api
    assert client.get('/api/operator/roster').status_code == 401
    assert client.get('/api/operator/roster', headers=auth).json()['people'] == []
    r, _ = tag_kit.add(Roster(), 'person', 'Rahul', .12, tag_id=3)
    tag_kit.save(r, path)
    reply = client.post('/api/operator/roster/reload', headers=auth)
    assert reply.status_code == 200 and reply.json()['people'][0]['name'] == 'Rahul'
    assert engine.roster.by_tag_id(3).display_name == 'Rahul'


def test_roster_reload_without_a_file_is_a_clear_error(tmp_path):
    engine = Engine(tmp_path)
    client = TestClient(create_app(engine, 't'))
    try:
        reply = client.post('/api/operator/roster/reload', headers={'Authorization': 'Bearer t'})
        assert reply.status_code == 409 and 'roster' in reply.json()['detail'].lower()
    finally:
        client.close(); engine.stop()


def test_engine_steers_toward_a_live_tag_through_the_normal_control_loop(tmp_path, monkeypatch):
    engine = Engine(tmp_path, settings=Settings(target_mode='tag'), roster=TEAM)

    class Source:
        label, eof = 'CAMERA', False
        def __init__(self): self.index = 0
        def read(self):
            time.sleep(.02)
            self.index += 1
            return Frame(scene((3, 500, 200, 80)), time.monotonic(), self.index, {})
        def close(self): pass

    monkeypatch.setattr(engine, 'open_source', lambda *args: Source())
    engine.start()
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (engine.snapshot()['detection'] or {}).get('tag_id') == 3:
            time.sleep(.02)
        state = engine.snapshot()
        assert state['detection']['tag_id'] == 3 and state['guidance']['stage'] == 'TRACK'
        engine.assist(True)
        while time.monotonic() < deadline and engine.controller.yaw <= 0:
            time.sleep(.02)
        assert engine.controller.state == 'LOCKED' and engine.controller.yaw > 0
        assert engine.preview is not None
    finally:
        engine.stop()
    assert engine.controller.yaw == 0 and not engine.controller.enabled
