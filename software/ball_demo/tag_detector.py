"""Shared AprilTag 36h11 image detection for fixed and moving tags."""


class AprilTagDetector:
    def __init__(self, calibration=None):
        self.calibration = calibration
        self._detector = None

    def detect(self, image):
        import cv2
        from .localization import Observation

        if image is None or getattr(image, 'ndim', 0) not in (2, 3):
            raise ValueError('Expected a grayscale or color image')
        if self.calibration is not None:
            width, height = self.calibration.image_size
            if image.shape[:2] != (height, width):
                raise ValueError('Image size differs from calibration')
        if not hasattr(cv2, 'aruco'):
            raise ValueError('OpenCV AprilTag module unavailable; baseline HSV remains usable')
        if self._detector is None:
            params = cv2.aruco.DetectorParameters()
            params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
            self._detector = cv2.aruco.ArucoDetector(
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), params)
        source = image
        pixel_space = 'distorted'
        if self.calibration is not None:
            from .calibration import undistort
            source = undistort(image, self.calibration)
            pixel_space = 'undistorted'
        corners, ids, _ = self._detector.detectMarkers(source)
        if ids is None:
            return []
        return [Observation(id=int(tag_id), corners=corner.reshape(4, 2).astype(float).tolist(),
                            pixel_space=pixel_space)
                for corner, tag_id in zip(corners, ids.ravel())]
