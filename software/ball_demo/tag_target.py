"""AprilTag targets for the existing yaw pipeline: follow a tag, or line up on a landing-pad tag.

Detections use the colored-ball schema (x, y, area, bbox, error, quality), so the unchanged
Controller, freshness watchdogs and loss-to-neutral rules apply exactly as for the ball.
Computer authority stays yaw-only: landing guidance is a pilot cue, never a throttle command.
Range is an estimate from the tag's apparent size and an approximate fisheye focal length
(Caddx Ant ~160° HFOV), not a calibrated pose.
"""
import math
import time

import numpy as np

from .vision import Detector

TARGET_MODES = ('color', 'tag', 'landing')
FAMILY = 'tag36h11'
MAX_TAG_ID = 586
MAX_LISTED = 12
# Landing cues
ALIGN_TOLERANCE = .15          # |error| above this: turn toward the pad first
PASSED_UNDER_S = 1.5           # a close pad that drops out of the bottom of the frame = over it
PASSED_UNDER_Y = .6            # last seen in the lower 40 % of the frame


def focal_px(settings):
    """Equidistant-fisheye centre focal length for the processed frame width."""
    return (settings.width / 2) / math.radians(settings.camera_hfov_deg / 2)


class TagScanner:
    """Thin cv2.aruco wrapper; tolerant of odd corner orders and a missing aruco module."""

    def __init__(self):
        self._detector = None

    def scan(self, image):
        import cv2
        if not hasattr(cv2, 'aruco'):
            raise ValueError('OpenCV AprilTag module unavailable')
        if self._detector is None:
            params = cv2.aruco.DetectorParameters()
            params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
            self._detector = cv2.aruco.ArucoDetector(
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), params)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        corners, ids, _ = self._detector.detectMarkers(gray)
        if ids is None:
            return []
        return [(int(tag_id), np.asarray(corner, float).reshape(4, 2)) for corner, tag_id in zip(corners, ids.ravel())]


def roster_entry(roster, tag_id):
    """(role, name, size_m) for an enabled roster tag, else None."""
    if roster is None:
        return None
    person = roster.by_tag_id(tag_id)
    if person is not None:
        return 'person', person.display_name, float(person.tag_size_m)
    site = roster.site_by_tag_id(tag_id)
    if site is not None:
        return 'landing', site.display_name, float(site.tag_size_m)
    return None


def describe(tag_id, corners, settings, roster, width, height):
    import cv2
    center = corners.mean(axis=0)
    edges = np.linalg.norm(np.roll(corners, -1, axis=0) - corners, axis=1)
    side = float(edges.mean())
    x, y = corners[:, 0], corners[:, 1]
    area = float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)
    bx, by, bw, bh = cv2.boundingRect(np.round(corners).astype(np.int32))
    entry = roster_entry(roster, tag_id)
    role, name, size = entry if entry else ('unregistered', None, float(settings.tag_size_m))
    range_m = focal_px(settings) * size / side if side > 0 else None
    return {'id': tag_id, 'role': role, 'name': name, 'registered': entry is not None,
            'x': float(center[0]), 'y': float(center[1]), 'side_px': round(side, 1), 'area': area,
            'bbox': [int(bx), int(by), max(1, int(bw)), max(1, int(bh))],
            'size_m': size, 'range_m': None if range_m is None else round(float(range_m), 2),
            'corners': [[round(float(a), 1), round(float(b), 1)] for a, b in corners]}


class TagTargetDetector:
    """Chooses one tag to steer toward and keeps pilot-facing guidance for every frame."""

    def __init__(self, roster_getter=lambda: None, clock=time.monotonic):
        self.roster = roster_getter
        self.clock = clock
        self.scanner = TagScanner()
        self.previous_id = None
        self.misses = 0
        self.last_close = None   # (time, y fraction) of the last close landing-pad sighting
        self.guidance = None

    def candidates(self, tags, settings, roster):
        if settings.tag_id >= 0:
            return [t for t in tags if t['id'] == settings.tag_id]
        if settings.target_mode == 'landing':
            return [t for t in tags if t['role'] == 'landing']
        people = [t for t in tags if t['role'] == 'person']
        if people or (roster is not None and any(p.enabled for p in roster.people)):
            return people
        # No people registered yet: follow any tag that is not a landing pad.
        return [t for t in tags if t['role'] != 'landing']

    def detect(self, image, settings):
        now = self.clock()
        height, width = image.shape[:2]
        roster = self.roster()
        tags = [describe(i, c, settings, roster, width, height) for i, c in self.scanner.scan(image)]
        tags.sort(key=lambda t: -t['side_px'])
        choices = self.candidates(tags, settings, roster)
        chosen, reacquired = None, False
        if choices:
            self.misses = 0
            same = [t for t in choices if t['id'] == self.previous_id]
            chosen = same[0] if same else choices[0]
            reacquired = self.previous_id is not None and not same
            self.previous_id = chosen['id']
        else:
            self.misses += 1
            if self.misses >= settings.acquire_frames:
                self.previous_id = None
        detection = None
        if chosen is not None:
            half = (width - 1) / 2
            detection = {'x': chosen['x'], 'y': chosen['y'], 'area': chosen['area'], 'bbox': chosen['bbox'],
                         'error': float(np.clip((chosen['x'] - half) / half, -1, 1)),
                         'quality': round(float(min(1., chosen['side_px'] / 40)), 3),
                         'tag_id': chosen['id'], 'tag_role': chosen['role'], 'tag_name': chosen['name'],
                         'side_px': chosen['side_px'], 'range_m': chosen['range_m']}
            if reacquired:
                detection['reacquired'] = True
        self.guidance = self.guide(tags, chosen, detection, settings, now, height)
        return detection

    def guide(self, tags, chosen, detection, settings, now, height):
        listed = [{k: t[k] for k in ('id', 'role', 'name', 'registered', 'x', 'y', 'side_px', 'range_m', 'corners')}
                  for t in tags[:MAX_LISTED]]
        guidance = {'mode': settings.target_mode, 'tags_seen': listed,
                    'target_id': chosen['id'] if chosen else None,
                    'range_m': chosen['range_m'] if chosen else None,
                    'range_note': 'estimate from tag size; not calibrated'}
        if settings.target_mode == 'landing':
            stage, cue = self.landing_stage(chosen, detection, settings, now, height)
        elif chosen is None:
            stage = 'SEARCH'
            cue = (f'Looking for tag {settings.tag_id}' if settings.tag_id >= 0 else
                   'Looking for a registered tag' if any(t['role'] == 'person' for t in tags) or tags == [] else
                   'Only landing-pad / other tags in view')
        else:
            who = chosen['name'] or f"tag {chosen['id']}"
            cue = f"Tracking {who}" + (f" · ~{chosen['range_m']:.1f} m" if chosen['range_m'] else '')
            stage = 'TRACK'
        guidance.update(stage=stage, cue=cue)
        return guidance

    def landing_stage(self, chosen, detection, settings, now, height):
        if chosen is None:
            if self.last_close and now - self.last_close[0] <= PASSED_UNDER_S and self.last_close[1] >= PASSED_UNDER_Y:
                return 'OVER PAD', 'Pad dropped below the camera: you are over it. Descend gently and land.'
            return 'SEARCH', 'Find the landing-pad tag'
        if chosen['range_m'] is not None and chosen['range_m'] <= 2 * settings.land_range_m:
            self.last_close = (now, chosen['y'] / max(1, height - 1))
        if abs(detection['error']) > ALIGN_TOLERANCE:
            return 'ALIGN', 'Turn toward the pad (assistance can hold yaw on it)'
        if chosen['range_m'] is None or chosen['range_m'] > settings.land_range_m:
            far = f" · ~{chosen['range_m']:.1f} m" if chosen['range_m'] else ''
            return 'APPROACH', f'Pad ahead: fly forward slowly{far}'
        return 'DESCEND', 'At the pad: lower throttle smoothly and land'


class TargetDetector:
    """Dispatches to the HSV ball detector or the AprilTag detector by settings.target_mode."""

    def __init__(self, roster_getter=lambda: None, clock=time.monotonic):
        self.roster_getter, self.clock = roster_getter, clock
        self.mode = 'color'
        self.color = Detector()
        self.tags = TagTargetDetector(roster_getter, clock)
        self.guidance = None

    def detect(self, image, settings):
        mode = settings.target_mode if settings.target_mode in TARGET_MODES else 'color'
        if mode != self.mode:
            self.mode = mode
            self.color = Detector()
            self.tags = TagTargetDetector(self.roster_getter, self.clock)
        if mode == 'color':
            self.guidance = None
            return self.color.detect(image, settings)
        try:
            detection = self.tags.detect(image, settings)
        except ValueError as error:
            self.guidance = {'mode': mode, 'stage': 'UNAVAILABLE', 'cue': str(error), 'tags_seen': [],
                             'target_id': None, 'range_m': None}
            return None
        self.guidance = self.tags.guidance
        return detection


STAGE_COLORS = {'TRACK': (90, 240, 160), 'DESCEND': (90, 240, 160), 'OVER PAD': (90, 240, 160),
                'APPROACH': (60, 200, 255), 'ALIGN': (60, 200, 255)}


def draw_overlay(image, guidance):
    """Outline every visible tag and print the cue; preview only."""
    import cv2
    if not guidance:
        return image
    for tag in guidance.get('tags_seen', []):
        target = tag['id'] == guidance.get('target_id')
        color = (90, 240, 160) if target else (200, 190, 80) if tag['registered'] else (150, 150, 150)
        points = np.round(np.array(tag['corners'])).astype(np.int32)
        cv2.polylines(image, [points], True, color, 3 if target else 1)
        label = f"{tag['id']}" + (f" {tag['name']}" if tag['name'] else '') + \
                (f" ~{tag['range_m']:.1f}m" if tag['range_m'] else '')
        anchor = (int(points[:, 0].min()), max(14, int(points[:, 1].min()) - 6))
        cv2.putText(image, label, anchor, cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1, cv2.LINE_AA)
    cue = f"{guidance.get('stage', '')}: {guidance.get('cue', '')}"
    cv2.rectangle(image, (0, 34), (image.shape[1], 60), (20, 20, 20), -1)
    cv2.putText(image, cue[:80], (10, 53), cv2.FONT_HERSHEY_SIMPLEX, .5,
                STAGE_COLORS.get(guidance.get('stage'), (210, 224, 233)), 1, cv2.LINE_AA)
    return image
