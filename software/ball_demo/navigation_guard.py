"""Independent pose validity, acquisition and explicit restoration latch."""
import numpy as np

from .localization import Pose


class PoseGuard:
    def __init__(self, bundle):
        self.bundle = bundle
        self.last = None
        self.last_sequence = -1
        self.count = 0
        self.status = 'waiting for pose'

    def reject(self, reason):
        self.count = 0
        self.status = reason
        return False

    def freshness(self, pose, now):
        if not np.isfinite(now) or now < pose.timing.host_received_s: raise ValueError('Invalid clock/receipt time')
        age = now - pose.timing.oldest_exposure()
        if age < 0 or age >= self.bundle.policy.pose_max_age_s: raise ValueError('Stale localization')
        return age

    def check(self, pose, now):
        try:
            pose = Pose.model_validate(pose.model_dump() if isinstance(pose, Pose) else pose)
            b, m, p = self.bundle, self.bundle.map, self.bundle.policy
            if (pose.bundle_id, pose.map_id, pose.map_version, pose.frame_id, pose.calibration_id) != (b.bundle_id, m.map_id, m.map_version, m.frame_id, b.calibration.calibration_id): raise ValueError('Pose registration mismatch')
            if b.map.example != (pose.source == 'synthetic_estimate'): raise ValueError('Pose source/example provenance mismatch')
            if any(i not in {t.id for t in b.survey.tags} for i in pose.tag_ids): raise ValueError('Unknown supporting tag')
            if pose.sequence <= self.last_sequence: raise ValueError('Reordered/duplicate pose')
            self.last_sequence = pose.sequence
            self.freshness(pose, now)
            if pose.uncertainty_m > p.max_uncertainty_m: raise ValueError('Excessive pose uncertainty')
            if pose.reprojection_px > p.max_reprojection_px: raise ValueError('Excessive reprojection error')
            if pose.ambiguity_gap_px < p.ambiguity_gap_px: raise ValueError('Ambiguous planar pose')
            position = pose.position
            if np.any(position < m.permitted.minimum) or np.any(position > m.permitted.maximum): raise ValueError('Pose outside permitted volume')
            if self.last is not None:
                dt = pose.timing.oldest_exposure() - self.last.timing.oldest_exposure()
                if dt <= 0: raise ValueError('Nonadvancing exposure time')
                # Reset jump baseline only after a long outage; acquisition still required.
                if dt < 2:
                    displacement = np.linalg.norm(position - self.last.position)
                    if displacement > p.max_speed_m_s * dt + pose.uncertainty_m + self.last.uncertainty_m: raise ValueError('Position outlier')
                    r = np.array(self.last.map_from_aircraft)[:3, :3].T @ np.array(pose.map_from_aircraft)[:3, :3]
                    angle = np.arccos(np.clip((np.trace(r) - 1) / 2, -1, 1))
                    if angle > p.max_angular_speed_rad_s * dt + .05: raise ValueError('Orientation outlier')
            self.last = pose
            self.count += 1
            self.status = 'valid' if self.count >= p.reacquire_frames else 'acquiring'
            return self.status == 'valid'
        except ValueError as error:
            return self.reject(str(error))
