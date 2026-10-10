import cv2
import numpy as np


class Detector:
    def __init__(self):
        self.previous = None
        self.misses = 0

    def detect(self, image, settings):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([settings.hue_low, settings.saturation_min, settings.value_min]),
                           np.array([settings.hue_high, 255, 255]))
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if not settings.min_area <= area <= settings.max_area:
                continue
            moment = cv2.moments(contour)
            if not moment['m00']:
                continue
            center = (moment['m10'] / moment['m00'], moment['m01'] / moment['m00'])
            candidates.append((area, center, cv2.boundingRect(contour)))
        if not candidates:
            self.misses += 1
            if self.misses >= settings.acquire_frames:
                self.previous = None
            return None
        self.misses = 0
        chosen = max(candidates, key=lambda c: c[0])
        distance = 0.
        jumped = False
        if self.previous is not None:
            nearest = min(candidates, key=lambda c: np.hypot(c[1][0] - self.previous[0], c[1][1] - self.previous[1]))
            distance = float(np.hypot(nearest[1][0] - self.previous[0], nearest[1][1] - self.previous[1]))
            if distance < image.shape[1] * .2:
                chosen = nearest
            else:
                # No candidate continues the tracked target: this is a different blob.
                jumped = True
        area, (x, y), bbox = chosen
        self.previous = (x, y)
        quality = float(min(1., area / 2000) * max(.2, 1 - distance / image.shape[1]))
        result = {'x': x, 'y': y, 'area': area, 'bbox': list(bbox),
                  'error': float(np.clip((x - (image.shape[1] - 1) / 2) / ((image.shape[1] - 1) / 2), -1, 1)),
                  'quality': round(quality, 3)}
        if jumped: result['reacquired'] = True
        return result

