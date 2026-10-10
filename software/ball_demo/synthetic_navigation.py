"""Independent image/depth generators. All geometry here is invented test truth.

These functions never call the pose solver, mapper, planner or aircraft bridge.
Depth comes from analytic ray/box intersections; pixels come from camera
projection/rasterization. Their truth is kept separate from inferred estimates.
"""
import numpy as np

from .map_io import Box, CameraGeometry, Survey, rigid


def geometry(camera):
    if isinstance(camera, CameraGeometry):
        return CameraGeometry.model_validate(camera.model_dump(include=set(CameraGeometry.model_fields)))
    return CameraGeometry.model_validate(camera)


def transform(value):
    return rigid(value)


def depth_image(camera, map_from_camera, obstacles, max_depth_m=4.):
    """Optical Z depth of nearest box surface; a missing return is exactly zero."""
    c, t = geometry(camera), transform(map_from_camera)
    if type(max_depth_m) not in (float, int) or not np.isfinite(max_depth_m) or max_depth_m <= 0:
        raise ValueError('Invalid synthetic depth range')
    w, h = c.image_size
    # The depth mapper accepts rectified pinhole samples only.
    if any(c.distortion): raise ValueError('Synthetic depth must be rectified')
    k = np.array(c.intrinsics)
    y, x = np.indices((h, w))
    local = np.stack(((x - k[0, 2]) / k[0, 0], (y - k[1, 2]) / k[1, 1], np.ones((h, w))), axis=-1)
    rays = local @ t[:3, :3].T
    origin = t[:3, 3]
    nearest = np.full((h, w), np.inf)
    for item in obstacles:
        box = Box.model_validate(item.model_dump() if isinstance(item, Box) else item)
        near, far = np.full((h, w), -np.inf), np.full((h, w), np.inf)
        valid = np.ones((h, w), bool)
        for axis in range(3):
            direction = rays[..., axis]
            parallel = abs(direction) < 1e-12
            valid &= ~(parallel & ((origin[axis] < box.minimum[axis]) | (origin[axis] > box.maximum[axis])))
            a = np.divide(box.minimum[axis] - origin[axis], direction, out=np.full((h, w), -np.inf), where=~parallel)
            b = np.divide(box.maximum[axis] - origin[axis], direction, out=np.full((h, w), np.inf), where=~parallel)
            near = np.maximum(near, np.minimum(a, b))
            far = np.minimum(far, np.maximum(a, b))
        distance = np.where(near > 1e-9, near, far)
        hit = valid & (far >= near) & (distance > 1e-9)
        nearest = np.minimum(nearest, np.where(hit, distance, np.inf))
    return np.where(nearest <= max_depth_m, nearest, 0.).astype(float)


def distort(image, camera):
    """Rasterize Brown distortion using inverse pixel mapping, not corner warps."""
    import cv2
    c = geometry(camera)
    w, h = c.image_size
    y, x = np.indices((h, w), dtype=np.float32)
    pixels = np.stack((x, y), axis=-1).reshape(-1, 1, 2)
    k = np.array(c.intrinsics)
    uv = cv2.undistortPoints(pixels, k, np.array(c.distortion), P=k).reshape(h, w, 2)
    return cv2.remap(image, uv[..., 0], uv[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=255)


def tag_image(camera, survey, map_from_camera, *, noise_std=0., blur_px=0, seed=26):
    import cv2
    c, t = geometry(camera), transform(map_from_camera)
    survey = Survey.model_validate(survey.model_dump() if isinstance(survey, Survey) else survey)
    if type(noise_std) not in (int, float) or not np.isfinite(noise_std) or noise_std < 0:
        raise ValueError('Invalid image noise')
    if type(blur_px) is not int or blur_px < 0 or (blur_px and blur_px % 2 != 1):
        raise ValueError('Blur size must be zero or an odd positive integer')
    if type(seed) is not int or seed < 0: raise ValueError('Seed must be a nonnegative integer')
    w, h = c.image_size
    image = np.full((h, w), 255, np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    camera_from_map = np.linalg.inv(t)
    for tag in survey.tags:
        camera_from_tag = camera_from_map @ np.array(tag.map_from_tag)
        half = tag.size_m / 2
        points = np.array([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]], float)
        xyz = points @ camera_from_tag[:3, :3].T + camera_from_tag[:3, 3]
        if np.any(xyz[:, 2] <= .01) or np.dot(camera_from_tag[:3, 2], camera_from_tag[:3, 3]) >= 0: continue
        corners = xyz[:, :2] / xyz[:, 2, None]
        k = np.array(c.intrinsics)
        corners = corners * [k[0, 0], k[1, 1]] + [k[0, 2], k[1, 2]]
        if np.any(corners < 2) or np.any(corners >= [w - 2, h - 2]): continue
        marker = cv2.aruco.generateImageMarker(dictionary, tag.id, 256)
        homography = cv2.getPerspectiveTransform(np.array([[0, 0], [255, 0], [255, 255], [0, 255]], np.float32), corners.astype(np.float32))
        image = np.minimum(image, cv2.warpPerspective(marker, homography, (w, h), borderValue=255))
    image = distort(image, c)
    if blur_px: image = cv2.GaussianBlur(image, (blur_px, blur_px), 0)
    if noise_std:
        image = np.clip(image.astype(float) + np.random.default_rng(seed).normal(0, noise_std, image.shape), 0, 255).astype(np.uint8)
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


def checkerboard_image(camera, camera_from_board, columns=7, rows=5, square_m=.025):
    import cv2
    c, t = geometry(camera), transform(camera_from_board)
    if type(columns) is not int or type(rows) is not int or not 3 <= columns <= 30 or not 3 <= rows <= 30:
        raise ValueError('Invalid checkerboard dimensions')
    if type(square_m) not in (int, float) or not np.isfinite(square_m) or square_m <= 0:
        raise ValueError('Invalid checkerboard spacing')
    w, h = c.image_size
    scale = 4
    image = np.full((h * scale, w * scale), 180, np.uint8)
    k = np.array(c.intrinsics)
    for row in range(-1, rows):
        for col in range(-1, columns):
            xy = np.array([[col, row], [col + 1, row], [col + 1, row + 1], [col, row + 1]], float) * square_m
            xyz = np.column_stack((xy, np.zeros(4))) @ t[:3, :3].T + t[:3, 3]
            if np.any(xyz[:, 2] <= .01): raise ValueError('Checkerboard behind camera')
            uv = xyz[:, :2] / xyz[:, 2, None] * [k[0, 0], k[1, 1]] + [k[0, 2], k[1, 2]]
            cv2.fillConvexPoly(image, np.rint(uv * scale).astype(np.int32), 0 if (row + col) % 2 == 0 else 255, lineType=cv2.LINE_AA)
    image = cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(distort(image, c), cv2.COLOR_GRAY2BGR)
