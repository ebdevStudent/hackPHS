"""Invented optical geometry and generated marker images for hardware-free rehearsal."""
import math
import time

import cv2
import numpy as np

from .localization import tag_points
from .map_io import Calibration
from .roster import Roster
from .sources import Frame


def demo_calibration(width=640, height=480):
    return Calibration(schema_version=1, calibration_id='synthetic-portable-v1',
        image_size=[width, height], intrinsics=[[float(width), 0., width / 2],
            [0., float(width), height / 2], [0., 0., 1.]],
        distortion_model='opencv_brown', distortion=[0., 0., 0., 0., 0.],
        camera_frame='camera_optical', aircraft_frame='aircraft_flu',
        aircraft_from_camera=[[0., 0., 1., 0.], [-1., 0., 0., 0.],
                              [0., -1., 0., 0.], [0., 0., 0., 1.]],
        reprojection_rms_px=0., evidence='Invented pinhole camera and mount; synthetic only', example=True)


def demo_roster():
    return Roster(people=[{'person_id': 'synthetic-walker', 'display_name': 'Synthetic Walker',
        'tag_family': 'tag36h11', 'tag_id': 7, 'tag_size_m': .2}],
        landing_sites=[{'site_id': 'synthetic-pad', 'display_name': 'Synthetic Pad',
            'tag_family': 'tag36h11', 'tag_id': 8, 'tag_size_m': .2,
            'width_m': .5, 'length_m': .5, 'approach_tolerance_rad': 3.14}])


def render_tag(calibration, tag_id, translation, rotation=(2.6, .5, .1), *, size_m=.2):
    width, height = calibration.image_size
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), tag_id, 300)
    corners = cv2.projectPoints(tag_points(size_m), np.asarray(rotation, dtype=float),
        np.asarray(translation, dtype=float), np.asarray(calibration.intrinsics),
        np.asarray(calibration.distortion))[0].reshape(4, 2)
    matrix = cv2.getPerspectiveTransform(np.array([[0, 0], [299, 0], [299, 299], [0, 299]], np.float32),
                                        corners.astype(np.float32))
    return cv2.warpPerspective(marker, matrix, (width, height), borderValue=255)


class PortableDemoSource:
    label = 'SYNTHETIC'

    def __init__(self, settings, calibration=None):
        self.settings = settings
        self.calibration = calibration or demo_calibration(settings.width, settings.height)
        self.index = 0

    def read(self):
        t = self.index / self.settings.processing_hz
        # The truth is recorded separately and never sent to the target-pose estimator.
        visible = not 2. <= t % 6. < 3.
        translation = [.28 * math.sin(t * .5), -.04, 1.8]
        width, height = self.calibration.image_size
        image = np.full((height, width), 255, dtype=np.uint8)
        if visible:
            image = np.minimum(image, render_tag(self.calibration, 7, translation))
        # Stable second marker; pad pose is derived from pixels, not this translation.
        image = np.minimum(image, render_tag(self.calibration, 8, [-.38, .16, 2.0]))
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        cv2.putText(image, 'SYNTHETIC APRILTAG SCENE - NO AIRCRAFT OUTPUT', (12, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, .48, (20, 20, 20), 1)
        frame = Frame(image, time.monotonic(), self.index,
                      {'source': 'synthetic', 'visible': visible, 'camera_from_tag_m': translation})
        self.index += 1
        return frame

    def close(self):
        pass
