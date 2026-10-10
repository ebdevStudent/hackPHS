"""Live-camera picture checks that frame timestamps cannot provide.

An analog receiver and USB capture adapter keep delivering fresh frames after the
radio link is lost: some repeat the last buffer (frozen), others send a uniform
blue/black screen. Both look "fresh" to the host clock, so the engine also asks
this monitor whether the picture itself is still changing and has content.
"""
import cv2
import numpy as np

# Mean absolute difference (0-255 grey levels) between consecutive frames below which
# they are treated as the same picture. A repeated capture buffer is bit-identical and
# measures 0; live analog video and camera sensors carry per-pixel noise of a grey level
# or more. Pixels are subsampled without averaging, which would smooth that noise away.
FROZEN_DIFFERENCE = 0.05
# Grey-level standard deviation below which the picture is a uniform screen.
BLANK_CONTRAST = 3.0
STRIDE = 8


class VideoHealth:
    """Tracks how long the picture has been frozen or blank, using caller-supplied time."""

    def __init__(self):
        self.previous = None
        self.frozen_since = None
        self.blank_since = None
        self.difference = None
        self.contrast = None

    def update(self, image, now):
        grey = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        small = grey[::STRIDE, ::STRIDE].astype(np.float32)
        self.contrast = float(small.std())
        self.difference = None if self.previous is None else float(np.abs(small - self.previous).mean())
        self.previous = small
        if self.difference is not None and self.difference < FROZEN_DIFFERENCE:
            if self.frozen_since is None:
                self.frozen_since = now
        else:
            self.frozen_since = None
        if self.contrast < BLANK_CONTRAST:
            if self.blank_since is None:
                self.blank_since = now
        else:
            self.blank_since = None

    def issue(self, now, limit_ms):
        """Return a fault reason once a frozen or blank picture has lasted limit_ms."""
        limit = limit_ms / 1000
        if self.blank_since is not None and now - self.blank_since >= limit:
            return 'no video signal (blank picture)'
        if self.frozen_since is not None and now - self.frozen_since >= limit:
            return 'frozen video'
        return None

    def report(self, now):
        def held(since):
            return None if since is None else round((now - since) * 1000, 1)
        return {'difference': None if self.difference is None else round(self.difference, 3),
                'contrast': None if self.contrast is None else round(self.contrast, 3),
                'frozen_ms': held(self.frozen_since), 'blank_ms': held(self.blank_since)}
