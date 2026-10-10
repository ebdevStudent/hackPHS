"""Bounded 3D A* over observed free space, with continuous swept-envelope checks."""
import heapq
import itertools
import time
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator

from .map_io import Contract, Identifier, Nonnegative, Number, Vector
from .localization import Pose

Heading = Annotated[Number, Field(ge=-np.pi, le=np.pi)]

MAX_CLEARANCE_FRAGMENTS = 4096

AUTHORITY = 'Advisory only; pilot owns roll, pitch, throttle, ARM/DISARM and independent takeover. Physical computer authority: yaw only; trainer output unverified.'


class NavigationState(Contract):
    available: bool
    status: str
    guidance_enabled: bool
    control_authority: Literal['advisory_only'] = 'advisory_only'
    authority_text: str = AUTHORITY
    physical_output: Literal[False] = False
    pose: Pose | None = None
    pose_age_s: Nonnegative | None = None
    route: list[Vector] = Field(default_factory=list, max_length=200002)
    route_headings_rad: list[Heading] = Field(default_factory=list, max_length=200002)
    route_tag_ids: list[list[int]] = Field(default_factory=list, max_length=200002)
    next_waypoint: Vector | None = None
    waypoint_heading_rad: Number | None = None
    bearing_rad: Number | None = None
    clearance_m: Nonnegative | None = None
    map_id: Identifier | None = None
    map_version: int | None = Field(default=None, ge=1)
    example: bool = False
    mission: dict | None = None

    @model_validator(mode='after')
    def consistency(self):
        if (self.pose is None) != (self.pose_age_s is None): raise ValueError('Pose/age must be paired')
        if not self.guidance_enabled and (self.route or self.next_waypoint is not None): raise ValueError('Inactive guidance has route')
        if self.guidance_enabled and (self.pose is None or len(self.route) < 2 or self.next_waypoint != self.route[1] or self.clearance_m is None): raise ValueError('Incomplete route guidance')
        if self.route_headings_rad and len(self.route_headings_rad) != len(self.route): raise ValueError('Route position/heading count mismatch')
        if self.route_tag_ids and len(self.route_tag_ids) != len(self.route): raise ValueError('Route position/visibility count mismatch')
        if any(len(ids) < 2 or len(set(ids)) != len(ids) or any(type(tag) is not int or not 0 <= tag < 587 for tag in ids) for ids in self.route_tag_ids):
            raise ValueError('Invalid route tag visibility')
        if (self.waypoint_heading_rad is None) != (self.next_waypoint is None): raise ValueError('Waypoint heading/position must be paired')
        if self.pose is not None and (self.pose.map_id != self.map_id or self.pose.map_version != self.map_version): raise ValueError('Display pose/map mismatch')
        if self.mission is not None:
            from .mission import MissionState
            MissionState.model_validate(self.mission)
        return self


def vector(value):
    if not isinstance(value, (list, tuple, np.ndarray)) or len(value) != 3 or any(not isinstance(x, (int, float, np.number)) or isinstance(x, (bool, np.bool_)) for x in value): raise ValueError('Expected metric 3-vector')
    result = np.array(value, dtype=float)
    if result.shape != (3,) or not np.isfinite(result).all(): raise ValueError('Expected finite metric 3-vector')
    return result


def clearance(bundle, uncertainty):
    p = bundle.policy
    if not np.isfinite(uncertainty) or uncertainty < 0 or uncertainty > p.max_uncertainty_m: raise ValueError('Invalid planning uncertainty')
    return p.cage_radius_m + p.flex_margin_m + bundle.map.uncertainty_m + uncertainty + p.speed_m_s * p.delay_bound_s + p.speed_m_s ** 2 / (2 * p.deceleration_m_s2)


def box_interval(start, end, minimum, maximum):
    """Closed slab intersection; contact with occupied boundaries is blocked."""
    low, high = 0., 1.
    for a, b, lo, hi in zip(start, end, minimum, maximum):
        delta = b - a
        if lo > hi: return None
        if abs(delta) < 1e-12:
            if a < lo or a > hi: return None
        else:
            x, y = sorted(((lo - a) / delta, (hi - a) / delta))
            low, high = max(low, x), min(high, y)
            if low > high: return None
    return low, high


class Planner:
    def __init__(self, bundle): self.bundle = bundle

    def segment_clear(self, start, end, margin, budget=lambda: None):
        start, end = vector(start), vector(end)
        if not np.isfinite(margin) or margin < 0: raise ValueError('Invalid clearance margin')
        m = self.bundle.map
        # A spherical enclosing cage is conservatively checked by its axis-aligned box.
        permitted = box_interval(start, end, np.array(m.permitted.minimum) + margin, np.array(m.permitted.maximum) - margin)
        if permitted is None or permitted[0] > 0 or permitted[1] < 1: return False
        for box in m.occupied:
            budget()
            if box_interval(start, end, np.array(box.minimum) - margin, np.array(box.maximum) + margin) is not None: return False
        # Fast case: one box contains the complete swept envelope.
        for box in m.observed_free:
            budget()
            interval = box_interval(start, end, np.array(box.minimum) + margin, np.array(box.maximum) - margin)
            if interval is not None and interval[0] <= 0 and interval[1] >= 1: return True
        # Subtract the exact union of known-free boxes from the swept bounds.
        # Remaining fragments are unknown. Testing the centre line against each
        # expanded fragment tests the complete moving cage box, including faces
        # between neighbouring reconstructed voxels. Individual erosion would
        # incorrectly block a cage spanning several adjacent thin free boxes.
        unknown = [(np.minimum(start, end) - margin, np.maximum(start, end) + margin)]
        for box in m.observed_free:
            budget()
            free_lo, free_hi = np.array(box.minimum), np.array(box.maximum)
            remaining = []
            for low, high in unknown:
                budget()
                overlap_lo, overlap_hi = np.maximum(low, free_lo), np.minimum(high, free_hi)
                if np.any(overlap_lo >= overlap_hi):
                    remaining.append((low, high))
                    continue
                # At most six disjoint slabs partition the difference. No hole filling.
                inner_lo, inner_hi = low.copy(), high.copy()
                for axis in range(3):
                    if inner_lo[axis] < overlap_lo[axis]:
                        cut_hi = inner_hi.copy(); cut_hi[axis] = overlap_lo[axis]
                        remaining.append((inner_lo.copy(), cut_hi))
                    if overlap_hi[axis] < inner_hi[axis]:
                        cut_lo = inner_lo.copy(); cut_lo[axis] = overlap_hi[axis]
                        remaining.append((cut_lo, inner_hi.copy()))
                    inner_lo[axis], inner_hi[axis] = overlap_lo[axis], overlap_hi[axis]
            # AABB corners outside the actual sweep do not block the segment.
            unknown = [(lo, hi) for lo, hi in remaining if box_interval(start, end, lo - margin, hi + margin) is not None]
            if len(unknown) > MAX_CLEARANCE_FRAGMENTS: raise ValueError('Clearance fragment budget exceeded')
            if not unknown: return True
        return False

    def plan(self, start, goal, uncertainty, clock=time.monotonic):
        start, goal = vector(start), vector(goal)
        p = self.bundle.policy
        margin = clearance(self.bundle, uncertainty)
        began = clock()
        def budget():
            if clock() - began >= p.planner_timeout_s: raise ValueError('Planner deadline exceeded')
        if not self.segment_clear(start, start, margin, budget) or not self.segment_clear(goal, goal, margin, budget): raise ValueError('Start/goal lacks observed envelope clearance')
        if self.segment_clear(start, goal, margin, budget):
            budget()
            return [start.tolist(), goal.tolist()], margin
        origin = np.array(self.bundle.map.permitted.minimum)
        def point(node): return origin + np.array(node) * p.grid_m
        seed = tuple(np.rint((start - origin) / p.grid_m).astype(int))
        # Attach exact endpoints to nearby grid vertices; don't round through a wall.
        seeds = []
        for delta in itertools.product((-1, 0, 1), repeat=3):
            node = tuple(a + b for a, b in zip(seed, delta))
            if self.segment_clear(start, point(node), margin, budget): seeds.append(node)
            budget()
        queue, costs, parents = [], {}, {}
        for node in seeds:
            cost = float(np.linalg.norm(point(node) - start))
            costs[node], parents[node] = cost, None
            heapq.heappush(queue, (cost + float(np.linalg.norm(point(node) - goal)), cost, node))
        directions = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
        visited = set()
        while queue:
            budget()
            _, cost, node = heapq.heappop(queue)
            if node in visited: continue
            visited.add(node)
            if len(visited) > p.max_nodes: raise ValueError('Planner node budget exceeded')
            if self.segment_clear(point(node), goal, margin, budget):
                chain = [goal.tolist()]
                cursor = node
                while cursor is not None:
                    chain.append(point(cursor).tolist())
                    cursor = parents[cursor]
                chain.append(start.tolist())
                chain.reverse()
                budget()
                return chain, margin
            for delta in directions:
                neighbor = tuple(a + b for a, b in zip(node, delta))
                candidate = cost + p.grid_m
                if neighbor not in visited and candidate < costs.get(neighbor, float('inf')) and self.segment_clear(point(node), point(neighbor), margin, budget):
                    costs[neighbor], parents[neighbor] = candidate, node
                    heapq.heappush(queue, (candidate + float(np.linalg.norm(point(neighbor) - goal)), candidate, neighbor))
        raise ValueError('No route through observed free space')


class Advisory:
    """Pure deterministic state machine. Call with logical time for replay."""
    def __init__(self, bundle):
        from .navigation_guard import PoseGuard
        self.bundle, self.guard, self.planner = bundle, PoseGuard(bundle), Planner(bundle)
        self.pose = None
        self.goal = None
        self.goal_heading_rad = None
        self.goal_tag_id = None
        self.route = []
        self.route_headings = []
        self.route_tags = []
        self.margin = None
        self.planned_at = None
        self.enabled = False
        self.status = 'guidance disabled'
        self.mission_runner = None

    def invalidate(self, reason):
        self.guard.reject(reason)
        self.enabled = False
        self.route, self.route_headings, self.route_tags, self.planned_at = [], [], [], None
        self.status = reason
        if self.mission_runner is not None: self.mission_runner.localization_lost()

    def accept(self, pose, now):
        if not self.guard.check(pose, now):
            if self.guard.status == 'acquiring': self.pose = self.guard.last
            self.enabled = False
            self.route, self.route_headings, self.route_tags, self.planned_at = [], [], [], None
            self.status = self.guard.status
            if self.mission_runner is not None: self.mission_runner.localization_lost()
            return False
        self.pose = self.guard.last
        mission_status = None
        if self.mission_runner is not None:
            if self.mission_runner.status == 'waiting_for_localization': self.mission_runner.localization_restored()
            if self.mission_runner.status in ('running', 'waiting_for_target', 'reacquiring_target'):
                try:
                    mission = self.mission_runner.observe(self.pose, now)
                    if mission['status'] in ('snapshot_pending', 'target_complete'):
                        self.enabled = False
                        self.route, self.route_headings, self.route_tags, self.planned_at = [], [], [], None
                        mission_status = 'mission ' + mission['status']
                    elif mission['status'] in ('waiting_for_target', 'reacquiring_target'):
                        mission_status = 'mission ' + mission['status']
                except ValueError as error:
                    self.mission_runner.localization_lost()
                    self.enabled = False
                    self.route, self.route_headings, self.route_tags, self.planned_at = [], [], [], None
                    mission_status = str(error)
        self.status = mission_status or ('valid; restore guidance deliberately' if not self.enabled else 'valid')
        return True

    def set_goal(self, goal, heading_rad=None, tag_id=None):
        if heading_rad is not None and (type(heading_rad) not in (int, float, np.float64, np.float32) or not np.isfinite(heading_rad)):
            raise ValueError('Invalid goal heading')
        if tag_id is not None and (type(tag_id) is not int or tag_id not in {tag.id for tag in self.bundle.survey.tags}):
            raise ValueError('Unknown goal tag')
        self.mission_runner = None
        self.goal = vector(goal).tolist()
        self.goal_heading_rad, self.goal_tag_id = heading_rad, tag_id
        self.enabled, self.route, self.route_headings, self.route_tags, self.planned_at = False, [], [], [], None
        self.status = 'goal changed; guidance disabled'

    def load_mission(self, mission):
        from .mission import MissionRunner
        runner = MissionRunner(mission, self.bundle)
        self.mission_runner = runner
        self.goal = None
        self.goal_heading_rad = self.goal_tag_id = None
        self.enabled, self.route, self.route_headings, self.route_tags, self.planned_at = False, [], [], [], None
        self.status = 'mission loaded; guidance disabled'
        return runner.snapshot()

    def start_mission(self):
        if self.mission_runner is None: raise ValueError('Load an inspection mission first')
        state = self.mission_runner.start()
        self._set_mission_target()
        self.status = 'mission ready; guidance disabled'
        return state

    def _set_mission_target(self):
        if self.mission_runner is None or self.mission_runner.status in ('complete', 'aborted'):
            self.goal = self.goal_heading_rad = self.goal_tag_id = None
            return
        target = self.mission_runner.target
        self.goal = list(target.viewing_position_m)
        self.goal_heading_rad, self.goal_tag_id = target.heading_rad, target.tag_id

    def advance_mission(self):
        if self.mission_runner is None: raise ValueError('Load an inspection mission first')
        state = self.mission_runner.advance()
        self._set_mission_target()
        self.enabled, self.route, self.route_headings, self.route_tags, self.planned_at = False, [], [], [], None
        self.status = 'mission complete' if state['status'] == 'complete' else 'mission target changed; guidance disabled'
        return state

    def abort_mission(self):
        if self.mission_runner is None: raise ValueError('Load an inspection mission first')
        state = self.mission_runner.abort()
        self.goal = self.goal_heading_rad = self.goal_tag_id = None
        self.enabled, self.route, self.route_headings, self.route_tags, self.planned_at = False, [], [], [], None
        self.status = 'mission aborted'
        return state

    def mission_snapshot_saved(self, digest, source):
        if self.mission_runner is None: raise ValueError('No inspection mission is loaded')
        state = self.mission_runner.snapshot_saved(digest, source)
        self.status = 'mission target complete'
        return state

    def mission_snapshot_failed(self):
        if self.mission_runner is None: raise ValueError('No inspection mission is loaded')
        state = self.mission_runner.snapshot_failed()
        self.enabled, self.route, self.route_headings, self.route_tags, self.planned_at = False, [], [], [], None
        self.status = 'mission snapshot failed'
        return state

    def resume(self, now):
        if self.guard.status != 'valid' or self.pose is None or self.goal is None: raise ValueError('Fresh acquired pose and goal required')
        self.guard.freshness(self.pose, now)
        self.enabled = True
        self.status = 'planning'

    def update(self, now, clock=time.monotonic):
        if self.pose is not None:
            try: self.guard.freshness(self.pose, now)
            except ValueError as error: self.invalidate(str(error))
        if not self.enabled: return self.snapshot(now)
        try:
            from .navigation_visibility import VisibilityPlanner
            transform = np.array(self.pose.map_from_aircraft)
            forward = transform[:2, 0]
            if np.linalg.norm(forward) < 1e-6: raise ValueError('Undefined horizontal aircraft heading')
            heading = float(np.arctan2(forward[1], forward[0]))
            plan = VisibilityPlanner(self.bundle, clock=clock).plan(self.pose.position, self.goal, self.pose.uncertainty_m,
                heading, self.goal_heading_rad, self.goal_tag_id)
            route, headings, tags, margin = plan.points_m, plan.headings_rad, plan.visible_tag_ids, plan.clearance_m
            self.route, self.route_headings, self.route_tags, self.margin, self.planned_at = route, headings, tags, margin, now
            self.status = 'goal reached' if np.linalg.norm(self.pose.position - self.goal) < .05 else 'advisory route'
        except ValueError as error: self.invalidate(str(error))
        return self.snapshot(now)

    def snapshot(self, now):
        age, valid = None, False
        if self.pose is not None:
            try: age = self.guard.freshness(self.pose, now); valid = self.guard.status == 'valid'
            except ValueError: pass
        fresh_route = self.enabled and valid and self.planned_at is not None and 0 <= now - self.planned_at < self.bundle.policy.route_ttl_s
        route = self.route if fresh_route else []
        headings = self.route_headings if fresh_route else []
        tags = self.route_tags if fresh_route else []
        next_point = route[1] if len(route) > 1 else None
        bearing = float(np.arctan2(next_point[1] - self.pose.position[1], next_point[0] - self.pose.position[0])) if next_point else None
        waypoint_heading = headings[1] if len(headings) > 1 else (bearing if next_point is not None else None)
        mission = None if self.mission_runner is None else self.mission_runner.snapshot()
        return NavigationState(available=True, status=self.status, guidance_enabled=bool(fresh_route),
            pose=self.pose.model_dump() if valid else None, pose_age_s=age if valid else None,
            route=route, route_headings_rad=headings, route_tag_ids=tags, next_waypoint=next_point, waypoint_heading_rad=waypoint_heading,
            bearing_rad=bearing, clearance_m=self.margin if fresh_route else None,
            map_id=self.bundle.map.map_id, map_version=self.bundle.map.map_version, example=self.bundle.map.example, mission=mission).model_dump()
