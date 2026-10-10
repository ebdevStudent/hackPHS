"""Bounded heading-aware routes that retain surveyed AprilTag visibility.

The route is an advisory geometric estimate. Visibility uses the saved map,
camera calibration and tag survey; a real camera must still prove each pose.
"""
import heapq
import itertools
import math
import time
from typing import Annotated, Literal

import numpy as np
import cv2
from pydantic import Field, model_validator

from .calibration import invert
from .localization import tag_points
from .map_io import Contract, Nonnegative, Number, Vector
from .navigation import Planner, vector


Angle = Annotated[Number, Field(ge=-math.pi, le=math.pi)]


class VisibleRoute(Contract):
    schema_version: Literal[1] = 1
    points_m: Annotated[list[Vector], Field(min_length=2, max_length=200002)]
    headings_rad: Annotated[list[Angle], Field(min_length=2, max_length=200002)]
    visible_tag_ids: Annotated[list[list[int]], Field(min_length=2, max_length=200002)]
    clearance_m: Nonnegative
    example: bool
    physical_output: Literal[False] = False

    @model_validator(mode='after')
    def aligned(self):
        if len(self.points_m) != len(self.headings_rad) or len(self.points_m) != len(self.visible_tag_ids):
            raise ValueError('Route position, heading and visibility counts differ')
        if any(len(ids) < 2 or len(set(ids)) != len(ids) or any(type(tag) is not int or not 0 <= tag < 587 for tag in ids)
               for ids in self.visible_tag_ids):
            raise ValueError('Every route sample must retain surveyed tag visibility')
        return self


class VisibilityPlanner:
    """Search position/yaw states; every move, turn and goal view is checked.

    Unknown/occluded rays and any exceeded work/deadline limit reject the whole
    route. The orientation model assumes level flight and uses yaw only.
    """
    def __init__(self, bundle, heading_bins=24, clock=time.monotonic):
        if type(heading_bins) is not int or not 8 <= heading_bins <= 72 or heading_bins % 4:
            raise ValueError('Heading bins must be a multiple of four from 8 through 72')
        self.bundle = bundle
        self.planner = Planner(bundle)
        self.heading_bins = heading_bins
        # A route that leaves one marker in view can still put planar PnP on an
        # ambiguous branch. Require two surveyed support tags until a measured
        # camera/tag geometry explicitly justifies a weaker rule.
        self.minimum_visible_tags = 2
        self.clock = clock
        self.cache = {}
        self.max_cache_entries = max(4096, min(250_000, bundle.policy.max_nodes * 8))
        self.started = clock()
        self.margin = None

    def _budget(self):
        policy = self.bundle.policy
        if self.clock() - self.started >= policy.planner_timeout_s:
            raise ValueError('Visibility planner deadline exceeded')

    @staticmethod
    def _wrap(angle):
        return float(math.atan2(math.sin(angle), math.cos(angle)))

    def _camera_pose(self, position, heading):
        t = np.eye(4)
        c, s = math.cos(heading), math.sin(heading)
        t[:3, :3] = [[c, -s, 0.], [s, c, 0.], [0., 0., 1.]]
        t[:3, 3] = vector(position)
        return t @ np.array(self.bundle.calibration.aircraft_from_camera, dtype=float)

    def visible_tag_ids(self, position, heading, required_tag_id=None):
        """Tags fully in frame, front-facing and joined by observed free space."""
        position = vector(position)
        if type(heading) not in (int, float, np.float64, np.float32) or not np.isfinite(heading):
            raise ValueError('Invalid visibility heading')
        if required_tag_id is not None and (type(required_tag_id) is not int or required_tag_id not in {t.id for t in self.bundle.survey.tags}):
            raise ValueError('Unknown required visibility tag')
        key = (tuple(np.round(position, 5)), round(self._wrap(float(heading)), 6), required_tag_id)
        if key in self.cache:
            return list(self.cache[key])
        self._budget()
        map_from_camera = self._camera_pose(position, float(heading))
        camera_from_map = invert(map_from_camera)
        camera_position = map_from_camera[:3, 3]
        calibration = self.bundle.calibration
        width, height = calibration.image_size
        k = np.array(calibration.intrinsics, dtype=float)
        tags = self.bundle.survey.tags
        visible = []
        for tag in tags:
            self._budget()
            map_from_tag = np.array(tag.map_from_tag, dtype=float)
            center = map_from_tag[:3, 3]
            normal = map_from_tag[:3, 2]
            camera_side = camera_position - center
            distance = float(np.linalg.norm(camera_side))
            if distance <= max(.03, self.bundle.policy.grid_m * .5) or float(np.dot(normal, camera_side)) <= 0:
                continue
            corners_map = tag_points(tag.size_m) @ map_from_tag[:3, :3].T + center
            corners_camera = corners_map @ camera_from_map[:3, :3].T + camera_from_map[:3, 3]
            if np.any(corners_camera[:, 2] <= .02):
                continue
            distortion = np.array(calibration.distortion, dtype=float)
            # Check the raw FPV pixels and the rectified coordinates used by the
            # detector. Strong edge distortion can otherwise claim that a tag
            # fits even though the capture sensor or undistorted detector crops it.
            pixels = cv2.projectPoints(corners_camera, np.zeros(3), np.zeros(3), k, distortion)[0].reshape(-1, 2)
            rectified = cv2.undistortPoints(pixels.reshape(-1, 1, 2), k, distortion, P=k).reshape(-1, 2)
            if any(not np.isfinite(points).all() or np.any(points[:, 0] < 1) or np.any(points[:, 0] >= width - 1) or
                   np.any(points[:, 1] < 1) or np.any(points[:, 1] >= height - 1)
                   for points in (pixels, rectified)):
                continue
            # End just in front of the printed face. A wall or unknown voxel
            # between the camera and tag blocks visibility; the tag surface itself
            # is not incorrectly treated as an intervening obstacle.
            endpoint = center + camera_side / distance * max(.03, self.bundle.policy.grid_m * .5)
            if self.planner.segment_clear(camera_position, endpoint, 0., self._budget):
                visible.append(tag.id)
        visible.sort()
        if required_tag_id is not None and required_tag_id not in visible:
            visible = []
        elif len(visible) < self.minimum_visible_tags:
            visible = []
        self.cache[key] = tuple(visible)
        if len(self.cache) > self.max_cache_entries:
            self.cache.pop(key, None)
            raise ValueError('Visibility planner cache budget exceeded')
        return visible

    def _visible_along(self, start, end, heading, required_tag_id=None):
        start, end = vector(start), vector(end)
        length = float(np.linalg.norm(end - start))
        spacing = max(.025, min(self.bundle.policy.grid_m * .5, .1))
        steps = max(1, math.ceil(length / spacing))
        tags_by_sample = []
        for i in range(steps + 1):
            self._budget()
            point = start + (end - start) * (i / steps)
            ids = self.visible_tag_ids(point, heading, required_tag_id)
            if len(ids) < self.minimum_visible_tags:
                return None
            tags_by_sample.append(ids)
        return tags_by_sample

    def _rotation_visible(self, position, start_heading, end_heading):
        delta = self._wrap(end_heading - start_heading)
        steps = max(1, math.ceil(abs(delta) / math.radians(5)))
        for i in range(steps + 1):
            self._budget()
            yaw = start_heading + delta * i / steps
            if len(self.visible_tag_ids(position, yaw)) < self.minimum_visible_tags:
                return False
        return True

    def _finish_heading(self, position, current_heading, goal_heading, required_tag_id):
        if goal_heading is None and required_tag_id is None:
            return current_heading if self.visible_tag_ids(position, current_heading) else None
        if goal_heading is not None:
            heading = self._wrap(float(goal_heading))
            if required_tag_id is not None and required_tag_id not in self.visible_tag_ids(position, heading, required_tag_id):
                return None
            if required_tag_id is None and not self.visible_tag_ids(position, heading):
                return None
            return heading if self._rotation_visible(position, current_heading, heading) else None
        # When the mission names a tag but no preferred yaw, choose the nearest
        # surveyed heading that sees that target and preserves a localization tag
        # throughout the turn.
        candidates = sorted((2 * math.pi * i / self.heading_bins for i in range(self.heading_bins)),
                            key=lambda h: abs(self._wrap(h - current_heading)))
        for heading in candidates:
            self._budget()
            if required_tag_id in self.visible_tag_ids(position, heading, required_tag_id) and self._rotation_visible(position, current_heading, heading):
                return self._wrap(heading)
        return None

    def _direct(self, start, goal, start_heading, goal_heading, required_tag_id, margin):
        for index in range(self.heading_bins):
            self._budget()
            heading = 2 * math.pi * index / self.heading_bins
            if not self._rotation_visible(start, start_heading, heading):
                continue
            if not self.planner.segment_clear(start, goal, margin, self._budget):
                return None
            samples = self._visible_along(start, goal, heading)
            if samples is None:
                continue
            final = self._finish_heading(goal, heading, goal_heading, required_tag_id)
            if final is None:
                continue
            points, headings, tags = [start.tolist()], [self._wrap(start_heading)], [self.visible_tag_ids(start, start_heading)]
            if abs(self._wrap(heading - start_heading)) > math.radians(.1):
                points.append(start.tolist()); headings.append(self._wrap(heading)); tags.append(self.visible_tag_ids(start, heading))
            points.append(goal.tolist()); headings.append(self._wrap(heading)); tags.append(samples[-1])
            if abs(self._wrap(final - heading)) > math.radians(.1):
                points.append(goal.tolist()); headings.append(self._wrap(final)); tags.append(self.visible_tag_ids(goal, final, required_tag_id) or self.visible_tag_ids(goal, final))
            return VisibleRoute(points_m=points, headings_rad=headings, visible_tag_ids=tags,
                                clearance_m=margin, example=self.bundle.map.example)
        return None

    def plan(self, start, goal, uncertainty, start_heading, goal_heading=None, required_tag_id=None):
        start, goal = vector(start), vector(goal)
        if type(start_heading) not in (int, float, np.float64, np.float32) or not np.isfinite(start_heading):
            raise ValueError('Invalid start heading')
        if goal_heading is not None and (type(goal_heading) not in (int, float, np.float64, np.float32) or not np.isfinite(goal_heading)):
            raise ValueError('Invalid goal heading')
        if abs(float(start_heading)) > math.pi or (goal_heading is not None and abs(float(goal_heading)) > math.pi):
            raise ValueError('Visibility headings must be within ±π')
        if required_tag_id is not None and (type(required_tag_id) is not int or required_tag_id not in {t.id for t in self.bundle.survey.tags}):
            raise ValueError('Unknown required visibility tag')
        self.cache.clear()
        self.started = self.clock()
        self.margin = self.planner.bundle.policy.cage_radius_m
        # Reuse the validated stopping-envelope calculation for the full path.
        from .navigation import clearance
        self.margin = clearance(self.bundle, uncertainty)
        if not self.planner.segment_clear(start, start, self.margin, self._budget) or not self.planner.segment_clear(goal, goal, self.margin, self._budget):
            raise ValueError('Start/goal lacks observed envelope clearance')
        direct = self._direct(start, goal, float(start_heading), goal_heading, required_tag_id, self.margin)
        if direct is not None:
            return direct

        policy = self.bundle.policy
        bins = self.heading_bins
        step = 2 * math.pi / bins
        origin = np.array(self.bundle.map.permitted.minimum, dtype=float)
        def point(node): return origin + np.array(node, dtype=float) * policy.grid_m
        center = tuple(np.rint((start - origin) / policy.grid_m).astype(int))
        start_yaw = self._wrap(float(start_heading))
        queue, costs, parents = [], {}, {}
        for delta in itertools.product((-1, 0, 1), repeat=3):
            node = tuple(a + b for a, b in zip(center, delta))
            p = point(node)
            if not self.planner.segment_clear(start, p, self.margin, self._budget):
                continue
            for heading_index in range(bins):
                heading = heading_index * step
                if not self._rotation_visible(start, start_yaw, heading):
                    continue
                if self._visible_along(start, p, heading) is None:
                    continue
                state = (node, heading_index)
                distance = float(np.linalg.norm(p - start))
                turn = abs(self._wrap(heading - start_yaw)) * policy.grid_m
                cost = distance + turn
                if cost < costs.get(state, float('inf')):
                    costs[state], parents[state] = cost, None
                    heapq.heappush(queue, (cost + float(np.linalg.norm(p - goal)), cost, state))
                self._budget()

        visited = set()
        directions = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
        while queue:
            self._budget()
            _, cost, state = heapq.heappop(queue)
            if state in visited:
                continue
            visited.add(state)
            if len(visited) > policy.max_nodes:
                raise ValueError('Visibility planner node budget exceeded')
            node, heading_index = state
            here, heading = point(node), heading_index * step
            if self.planner.segment_clear(here, goal, self.margin, self._budget):
                visibility = self._visible_along(here, goal, heading)
                final = self._finish_heading(goal, heading, goal_heading, required_tag_id) if visibility is not None else None
                if final is not None:
                    chain, cursor = [], state
                    while cursor is not None:
                        chain.append(cursor)
                        cursor = parents[cursor]
                    chain.reverse()
                    points, headings, tags = [start.tolist()], [start_yaw], [self.visible_tag_ids(start, start_yaw)]
                    for item in chain:
                        p = point(item[0]); h = item[1] * step
                        previous = headings[-1]
                        if np.linalg.norm(p - np.array(points[-1])) > 1e-6 or abs(self._wrap(h - previous)) > math.radians(.1):
                            points.append(p.tolist()); headings.append(self._wrap(h)); tags.append(self.visible_tag_ids(p, h))
                    if np.linalg.norm(goal - np.array(points[-1])) > 1e-6 or abs(self._wrap(heading - headings[-1])) > math.radians(.1):
                        points.append(goal.tolist()); headings.append(self._wrap(heading)); tags.append(visibility[-1])
                    if abs(self._wrap(final - headings[-1])) > math.radians(.1):
                        points.append(goal.tolist()); headings.append(self._wrap(final)); tags.append(self.visible_tag_ids(goal, final, required_tag_id) or self.visible_tag_ids(goal, final))
                    return VisibleRoute(points_m=points, headings_rad=headings, visible_tag_ids=tags,
                                        clearance_m=self.margin, example=self.bundle.map.example)

            for delta in directions:
                neighbor = tuple(a + b for a, b in zip(node, delta))
                next_point = point(neighbor)
                next_state = (neighbor, heading_index)
                candidate = cost + policy.grid_m
                if next_state not in visited and candidate < costs.get(next_state, float('inf')) and self.planner.segment_clear(here, next_point, self.margin, self._budget):
                    if self._visible_along(here, next_point, heading) is not None:
                        costs[next_state], parents[next_state] = candidate, state
                        heapq.heappush(queue, (candidate + float(np.linalg.norm(next_point - goal)), candidate, next_state))
                for turn in (-1, 1):
                    next_heading = (heading_index + turn) % bins
                    turned = (node, next_heading)
                    next_yaw = next_heading * step
                    candidate = cost + policy.grid_m * step
                    if turned not in visited and candidate < costs.get(turned, float('inf')) and self._rotation_visible(here, heading, next_yaw):
                        costs[turned], parents[turned] = candidate, state
                        heapq.heappush(queue, (candidate + float(np.linalg.norm(here - goal)), candidate, turned))
        raise ValueError('No route retains surveyed AprilTag visibility through known-free space')
