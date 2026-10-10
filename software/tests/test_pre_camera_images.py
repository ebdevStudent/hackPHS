"""Real OpenCV detection on independent synthetic rasterized images.

Requires OpenCV; never silently skip when the required dependency is unavailable.
"""
import cv2
import numpy as np
import pytest

from ball_demo.calibration import calibrate
from ball_demo.localization import Localizer, Timing
from ball_demo.map_io import CameraGeometry
from ball_demo.navigation_fixtures import example_bundle, example_pose
from ball_demo.registration import StationRegistrar, register_images
from ball_demo.synthetic_navigation import checkerboard_image, tag_image


@pytest.mark.parametrize('noise,blur', [(0., 0), (2., 3), (5., 3)])
def test_independent_tag_rasters_localize_through_real_detector(noise, blur):
    b = example_bundle()
    truth = example_pose()
    map_from_camera = truth @ np.array(b.calibration.aircraft_from_camera)
    image = tag_image(b.calibration, b.survey, map_from_camera, noise_std=noise, blur_px=blur)
    solver = Localizer(b)
    pose = solver.solve(solver.detect(image), Timing(host_received_s=1., exposure_s=1., provenance='synthetic'), 0, 'synthetic_estimate')
    assert np.linalg.norm(pose.position - truth[:3, 3]) < .06
    assert pose.tag_ids == [0, 1] or pose.tag_ids == [1, 0]
    assert np.array_equal(image, tag_image(b.calibration, b.survey, map_from_camera, noise_std=noise, blur_px=blur))


def test_rgb_images_register_nonidentity_depth_extrinsics_and_clear_after_loss():
    b = example_bundle()
    rgb_truth = example_pose() @ np.array(b.calibration.aircraft_from_camera)
    extr = np.eye(4); extr[:3, :3] = cv2.Rodrigues(np.array([.03, -.06, .02]))[0]; extr[:3, 3] = [.014, -.004, .002]
    images = [tag_image(b.calibration, b.survey, rgb_truth, noise_std=1., seed=i) for i in range(3)]
    reg = register_images(b.calibration, b.survey, extr, images, [1., 1.1, 1.2])
    expected = rgb_truth @ extr
    result = reg.result()
    assert np.linalg.norm(np.array(result.map_from_depth)[:3, 3] - expected[:3, 3]) < .04
    assert np.linalg.norm(np.array(result.map_from_depth)[:3, :3] - expected[:3, :3]) < .06
    assert len(result.image_sha256) == 3 and not result.physical_acceptance
    with pytest.raises(ValueError, match='No surveyed tags'): reg.observe(np.zeros_like(images[0]), 1.3)
    assert reg.result() is None


def test_checkerboard_pixels_recover_known_camera_and_predict_withheld_projection():
    template = example_bundle().calibration
    k = np.array([[600., 0., 318.], [0., 620., 243.], [0., 0., 1.]])
    distortion = np.array([-.04, .004, .001, -.001, 0.])
    camera = CameraGeometry(image_size=[640, 480], intrinsics=k.tolist(), distortion_model='opencv_brown', distortion=distortion.tolist())
    images = []
    rng = np.random.default_rng(42)
    for i in range(14):
        board = np.eye(4)
        board[:3, :3] = cv2.Rodrigues(rng.uniform(-.42, .42, 3))[0]
        board[:3, 3] = [rng.uniform(-.11, .11), rng.uniform(-.07, .07), rng.uniform(.45, .72)]
        images.append(checkerboard_image(camera, board))
    fitted, count = calibrate(images, 7, 5, .025, template)
    assert count >= 10 and fitted.reprojection_rms_px < .8
    assert np.allclose(np.diag(fitted.intrinsics)[:2], np.diag(k)[:2], rtol=.035)
    # Held-out independent board pose and points never supplied to calibration.
    points = np.array([[x * .025, y * .025, 0.] for x in range(7) for y in range(5)])
    rv, tv = np.array([.28, -.12, .08]), np.array([-.07, -.04, .58])
    actual = cv2.projectPoints(points, rv, tv, k, distortion)[0]
    predicted = cv2.projectPoints(points, rv, tv, np.array(fitted.intrinsics), np.array(fitted.distortion))[0]
    assert np.sqrt(np.mean((actual - predicted) ** 2)) < 2.
    assert fitted.example  # Generated pixels cannot establish physical calibration.


@pytest.mark.parametrize('kwargs', [{'noise_std': True}, {'noise_std': float('nan')}, {'blur_px': 2}, {'seed': -1}])
def test_synthetic_image_parameters_are_strict(kwargs):
    b = example_bundle()
    with pytest.raises(ValueError): tag_image(b.calibration, b.survey, np.eye(4), **kwargs)


def test_checkerboard_and_registration_image_input_failures():
    b = example_bundle()
    with pytest.raises(ValueError): checkerboard_image(b.calibration, np.eye(4), columns=True)
    with pytest.raises(ValueError): checkerboard_image(b.calibration, np.eye(4), square_m=float('nan'))
    behind = np.eye(4); behind[2, 3] = -1.
    with pytest.raises(ValueError): checkerboard_image(b.calibration, behind)
    with pytest.raises(ValueError): register_images(b.calibration, b.survey, np.eye(4), [], [])
    reg = StationRegistrar(b.calibration, b.survey, np.eye(4))
    with pytest.raises(ValueError): reg.observe(np.zeros((480, 640), float), 1.)
    with pytest.raises(ValueError): reg.observe(np.zeros((20, 20), np.uint8), 1.)
