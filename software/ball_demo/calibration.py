"""Calibration for the final resized capture pipeline, without changing HSV images."""
import numpy as np

from .map_io import Calibration, rigid


def invert(transform):
    t = rigid(transform)
    result = np.eye(4)
    result[:3, :3] = t[:3, :3].T
    result[:3, 3] = -result[:3, :3] @ t[:3, 3]
    return result


def aircraft_pose(map_from_tag, camera_from_tag, aircraft_from_camera):
    return rigid(map_from_tag) @ invert(camera_from_tag) @ invert(aircraft_from_camera)


def undistort(image, calibration):
    import cv2
    w, h = calibration.image_size
    if image.shape[:2] != (h, w): raise ValueError('Image size differs from calibration')
    k = np.array(calibration.intrinsics)
    return cv2.undistort(image, k, np.array(calibration.distortion), None, k)


def calibrate(images, columns, rows, square_m, template):
    """Measured checkerboard corner spacing in metres; template supplies mount transform."""
    import cv2
    if type(columns) is not int or type(rows) is not int or min(columns, rows) < 3 or max(columns, rows) > 30:
        raise ValueError('Use 3–30 internal corners per dimension')
    if type(square_m) not in (float, int) or not np.isfinite(square_m) or square_m <= 0:
        raise ValueError('Checker square spacing must be finite positive metres')
    objects, pixels = [], []
    grid = np.zeros((columns * rows, 3), np.float32)
    grid[:, :2] = np.mgrid[0:columns, 0:rows].T.reshape(-1, 2) * square_m
    for image in images:
        if image.shape[:2] != tuple(reversed(template.image_size)): raise ValueError('Mixed capture sizes')
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        ok, corners = cv2.findChessboardCornersSB(gray, (columns, rows))
        if ok: objects.append(grid.copy()); pixels.append(corners)
    if len(pixels) < 10: raise ValueError('At least ten detected varied checkerboard views required')
    rms, k, distortion, _, _ = cv2.calibrateCamera(objects, pixels, tuple(template.image_size), None, None)
    data = template.model_dump()
    data.update(intrinsics=k.tolist(), distortion=distortion.ravel().tolist(), reprojection_rms_px=float(rms))
    return Calibration.model_validate(data), len(pixels)
