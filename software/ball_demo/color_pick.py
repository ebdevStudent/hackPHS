"""Suggest HSV detector thresholds from a patch the operator clicks in the video."""
import cv2
import numpy as np

HUE_MARGIN = 10          # OpenCV hue units (0-179) either side of the sampled spread
MIN_SATURATION = 60      # below this the patch is grey/white and HSV tracking is unreliable
FLOOR = 40               # lowest saturation/value threshold the suggestion will propose


def suggest(image, x, y, radius=6):
    """Sample a square patch centred on normalised (x, y) and return settings plus warnings.

    The detector's inRange does not wrap around hue 0/179, so red targets are
    reported with a warning rather than silently clamped.
    """
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise ValueError('Pick position must be inside the video frame')
    height, width = image.shape[:2]
    cx, cy = min(width - 1, int(x * width)), min(height - 1, int(y * height))
    patch = image[max(0, cy - radius):cy + radius + 1, max(0, cx - radius):cx + radius + 1]
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(int)
    hue, saturation, value = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    median_hue = int(np.median(hue))
    warnings = []
    if np.median(saturation) < MIN_SATURATION:
        warnings.append('Picked area is not a saturated colour; choose a brighter, more colourful target.')
    # Measure hue spread on the circle so a red patch straddling 0/179 is recognised.
    offsets = (hue - median_hue + 90) % 180 - 90
    low = median_hue + int(np.percentile(offsets, 5)) - HUE_MARGIN
    high = median_hue + int(np.percentile(offsets, 95)) + HUE_MARGIN
    if low < 0 or high > 179:
        warnings.append('Red hues wrap around 0/179 and cannot be tracked with one range; use a green, blue or yellow target.')
    settings = {'hue_low': max(0, low), 'hue_high': min(179, high),
                'saturation_min': int(max(FLOOR, np.percentile(saturation, 10) - 40)),
                'value_min': int(max(FLOOR, np.percentile(value, 10) - 40))}
    sample = {'x': cx, 'y': cy, 'pixels': int(len(hsv)), 'hue': median_hue,
              'saturation': int(np.median(saturation)), 'value': int(np.median(value))}
    return {'settings': settings, 'sample': sample, 'warnings': warnings}
