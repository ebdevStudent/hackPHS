import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from ball_demo.navigation_fixtures import example_bundle
from ball_demo.roster import LandingSite, Person, Roster, load_roster
from ball_demo.tag_detector import AprilTagDetector
from ball_demo.sources import Frame


def valid_person(person_id='person-a', tag_id=7):
    return {'person_id': person_id, 'display_name': 'Synthetic Person',
            'tag_family': 'tag36h11', 'tag_id': tag_id, 'tag_size_m': .18}


def valid_site(site_id='pad-a', tag_id=10):
    return {'site_id': site_id, 'display_name': 'Synthetic Landing Pad',
            'tag_family': 'tag36h11', 'tag_id': tag_id, 'tag_size_m': .2,
            'width_m': .6, 'length_m': .5}


def test_roster_enforces_separate_unique_person_and_pad_tag_assignments():
    roster = Roster(people=[valid_person()], landing_sites=[valid_site()])
    assert roster.by_person_id('person-a').tag_id == 7
    assert roster.by_tag_id(7).person_id == 'person-a'
    assert roster.site_by_id('pad-a').tag_id == 10
    assert roster.site_by_tag_id(10).site_id == 'pad-a'
    with pytest.raises(ValidationError, match='Duplicate person_id'):
        Roster(people=[valid_person(), valid_person()])
    with pytest.raises(ValidationError, match='Duplicate site_id'):
        Roster(landing_sites=[valid_site(), valid_site()])
    with pytest.raises(ValidationError, match='distinct'):
        Roster(people=[valid_person(tag_id=7)], landing_sites=[valid_site(tag_id=7)])
    with pytest.raises(ValidationError):
        Roster(people=[{**valid_person(), 'enabled': 'yes'}])


@pytest.mark.parametrize('person', [
    {**valid_person(), 'person_id': ' bad'},
    {**valid_person(), 'display_name': ' Synthetic Person'},
    {**valid_person(), 'tag_family': 'tag25h9'},
    {**valid_person(), 'tag_id': True},
    {**valid_person(), 'tag_size_m': float('inf')},
])
def test_person_contract_rejects_unmeasured_or_malformed_assignments(person):
    with pytest.raises(ValidationError):
        Person.model_validate(person)


def test_person_and_landing_names_must_be_trimmed_and_supplied_frame_time_is_preserved():
    with pytest.raises(ValidationError, match='Display name'):
        Person.model_validate({**valid_person(), 'display_name': ' '})
    with pytest.raises(ValidationError, match='Landing-site name'):
        LandingSite.model_validate({**valid_site(), 'display_name': ' '})
    frame = Frame(np.zeros((2, 2), dtype=np.uint8), 1., 0, {}, captured_utc='2026-10-09T12:00:00Z')
    assert frame.captured_utc == '2026-10-09T12:00:00Z'


@pytest.mark.parametrize('site', [
    {**valid_site(), 'display_name': '  '},
    {**valid_site(), 'tag_id': 587},
    {**valid_site(), 'width_m': 0},
    {**valid_site(), 'approach_tolerance_rad': 0},
    {**valid_site(), 'enabled': 'yes'},
    {**valid_site(), 'pad_from_tag': [[2., 0., 0., 0.], [0., 1., 0., 0.],
        [0., 0., 1., 0.], [0., 0., 0., 1.]]},
])
def test_landing_site_contract_rejects_bad_geometry_and_identity(site):
    with pytest.raises(ValidationError):
        LandingSite.model_validate(site)


def test_roster_loader_accepts_private_json_and_reports_invalid_files(tmp_path):
    path = tmp_path / 'roster.json'
    path.write_text('{"schema_version":1,"people":[],"landing_sites":[]}')
    assert load_roster(path) == Roster()
    with pytest.raises(ValueError, match='Invalid prepared roster'):
        load_roster(tmp_path / 'missing.json')
    path.write_text('{broken json')
    with pytest.raises(ValueError, match='Invalid prepared roster'):
        load_roster(path)
    path.write_text(' ' * 128_001)
    with pytest.raises(ValueError, match='128 KB'):
        load_roster(path)


def test_apriltag_detector_detects_generated_marker_and_reuses_backend():
    calibration = example_bundle().calibration
    detector = AprilTagDetector(calibration)
    image = np.full((480, 640, 3), 255, dtype=np.uint8)
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), 7, 180)
    image[150:330, 230:410] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    first = detector.detect(image)
    second = detector.detect(image)
    assert [entry.id for entry in first] == [7]
    assert second[0].pixel_space == 'undistorted'
    assert detector._detector is not None


def test_apriltag_detector_reports_invalid_images_dimensions_and_missing_module(monkeypatch):
    detector = AprilTagDetector(example_bundle().calibration)
    with pytest.raises(ValueError, match='grayscale or color'):
        detector.detect(None)
    with pytest.raises(ValueError, match='differs from calibration'):
        detector.detect(np.zeros((32, 32, 3), dtype=np.uint8))
    monkeypatch.delattr(cv2, 'aruco', raising=False)
    with pytest.raises(ValueError, match='module unavailable'):
        AprilTagDetector().detect(np.zeros((32, 32), dtype=np.uint8))
