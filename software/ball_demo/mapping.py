"""Repeatable D435 small-zone mapping from registered rectified depth frames.

Static surveyed stations only. No inferred handheld scanner trajectory or SLAM.
Free voxels require every projected pixel to have a deeper valid return. Sparse
returns, off-camera volume, scan holes and occluded cells stay unknown.
"""
import hashlib
import itertools
import json
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator

from .calibration import invert
from .map_io import Box, Contract, Identifier, Map, Matrix, Nonnegative, Positive, rigid


class DepthIntrinsics(Contract):
    width: int = Field(ge=16, le=1920)
    height: int = Field(ge=16, le=1080)
    fx: Positive
    fy: Positive
    cx: Nonnegative
    cy: Nonnegative
    model: Literal['rectified_pinhole']

    @model_validator(mode='after')
    def center(self):
        if self.cx >= self.width or self.cy >= self.height: raise ValueError('Invalid depth principal point')
        return self


class DepthFrame(Contract):
    file: str = Field(pattern=r'^[A-Za-z0-9_.-]+\.npz$')
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    intrinsics: DepthIntrinsics
    map_from_depth: Matrix
    registration_evidence: str = Field(min_length=1)
    hardware_timestamp_ms: Nonnegative
    hardware_clock_domain: str = Field(min_length=1)
    host_received_s: Nonnegative
    color_hardware_timestamp_ms: Nonnegative | None = None
    color_hardware_clock_domain: str | None = None

    @model_validator(mode='after')
    def transform(self):
        rigid(self.map_from_depth)
        if (self.color_hardware_timestamp_ms is None) != (self.color_hardware_clock_domain is None): raise ValueError('Incomplete RGB clock provenance')
        return self


class Scan(Contract):
    schema_version: Literal[1]
    scan_id: Identifier
    camera_model: Literal['D435']
    serial: str = Field(min_length=1)
    sdk_version: str = Field(min_length=1)
    map_id: Identifier
    map_version: int = Field(ge=1)
    frame_id: Identifier
    units: Literal['m']
    axes: Literal['right_handed_z_up']
    permitted: Box
    voxel_m: Positive
    uncertainty_m: Positive
    max_depth_m: Positive = 4.
    acquired_utc: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    example: bool
    frames: Annotated[list[DepthFrame], Field(min_length=1, max_length=1000)]
    camera_metadata: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def budget(self):
        counts = np.ceil((np.array(self.permitted.maximum) - self.permitted.minimum) / self.voxel_m)
        if np.prod(counts) > 100000: raise ValueError('Small-zone mapper limited to 100000 voxels')
        if len({frame.file for frame in self.frames}) != len(self.frames): raise ValueError('Duplicate depth files')
        return self


def merge_voxels(cells, origin, step, maximum):
    """Merge exact unions of adjacent voxel boxes; no filling unknown gaps."""
    boxes = [(tuple(cell), tuple(i + 1 for i in cell)) for cell in sorted(cells)]
    for axis in (0, 1, 2):
        groups = {}
        for low, high in boxes:
            key = tuple((low[i], high[i]) for i in range(3) if i != axis)
            groups.setdefault(key, []).append((low, high))
        boxes = []
        for group in groups.values():
            group.sort(key=lambda b: b[0][axis])
            low, high = group[0]
            for other_low, other_high in group[1:]:
                if high[axis] == other_low[axis]:
                    high = tuple(other_high[i] if i == axis else high[i] for i in range(3))
                else:
                    boxes.append((low, high)); low, high = other_low, other_high
            boxes.append((low, high))
    return [Box(minimum=(origin + np.array(low) * step).tolist(), maximum=np.minimum(origin + np.array(high) * step, maximum).tolist()) for low, high in boxes]


def build_map(scan, root):
    """Deterministic rebuild; validates hashes and all array data before mapping."""
    scan = Scan.model_validate(scan.model_dump() if isinstance(scan, Scan) else scan)
    root = Path(root).resolve()
    loaded = []
    for frame in scan.frames:
        path = (root / frame.file).resolve()
        if path.parent != root: raise ValueError('Depth path escapes capture directory')
        if path.stat().st_size > 30_000_000: raise ValueError('Depth file too large')
        if hashlib.sha256(path.read_bytes()).hexdigest() != frame.sha256: raise ValueError('Depth hash mismatch')
        with np.load(path, allow_pickle=False) as archive:
            if 'depth_m' not in archive: raise ValueError('Missing metric depth array')
            depth = archive['depth_m']
            if depth.shape != (frame.intrinsics.height, frame.intrinsics.width) or depth.dtype.kind != 'f' or not np.isfinite(depth).all() or np.any(depth < 0): raise ValueError('Invalid depth units/shape/nonfinite samples')
            loaded.append((frame, depth.copy()))
    origin, maximum = np.array(scan.permitted.minimum), np.array(scan.permitted.maximum)
    dims = np.ceil((maximum - origin) / scan.voxel_m).astype(int)
    occupied, free = set(), set()
    for frame, depth in loaded:
        k, transform = frame.intrinsics, np.array(frame.map_from_depth)
        y, x = np.indices(depth.shape)
        valid = (depth > 0) & (depth <= scan.max_depth_m)
        z = depth[valid]
        points = np.column_stack(((x[valid] - k.cx) * z / k.fx, (y[valid] - k.cy) * z / k.fy, z))
        world = points @ transform[:3, :3].T + transform[:3, 3]
        indices = np.floor((world - origin) / scan.voxel_m).astype(int)
        for index, point in zip(indices, world):
            if np.all(index >= 0) and np.all(index < dims) and np.all(point < maximum): occupied.add(tuple(index))
        camera_from_map = invert(transform)
        for index in itertools.product(*(range(int(d)) for d in dims)):
            if index in occupied: continue
            lo = origin + np.array(index) * scan.voxel_m
            hi = np.minimum(lo + scan.voxel_m, maximum)
            corners = np.array(list(itertools.product(*zip(lo, hi))))
            camera = corners @ camera_from_map[:3, :3].T + camera_from_map[:3, 3]
            if np.any(camera[:, 2] <= .1): continue
            pixels = camera[:, :2] / camera[:, 2, None] * [k.fx, k.fy] + [k.cx, k.cy]
            lower, upper = np.floor(pixels.min(axis=0)).astype(int), np.ceil(pixels.max(axis=0)).astype(int)
            if np.any(lower < 0) or np.any(upper >= [k.width, k.height]): continue
            patch = depth[lower[1]:upper[1] + 1, lower[0]:upper[0] + 1]
            if np.all(patch > 0) and np.all(patch <= scan.max_depth_m) and float(patch.min()) > float(camera[:, 2].max()) + scan.uncertainty_m:
                free.add(index)
    free.difference_update(occupied)
    if not free: raise ValueError('No fully observed free volume; add registered station/coverage')
    free_boxes = merge_voxels(free, origin, scan.voxel_m, maximum)
    occupied_boxes = merge_voxels(occupied, origin, scan.voxel_m, maximum)
    if len(free_boxes) > 1000 or len(occupied_boxes) > 1000: raise ValueError('Map fragmentation exceeds contract: reduce zone or inspect scan quality')
    m = Map(schema_version=1, map_id=scan.map_id, map_version=scan.map_version, frame_id=scan.frame_id, axes=scan.axes, units='m', permitted=scan.permitted,
            observed_free=free_boxes, occupied=occupied_boxes, uncertainty_m=scan.uncertainty_m, acquired_utc=scan.acquired_utc, evidence=scan.evidence, example=scan.example)
    digest = hashlib.sha256(scan.model_dump_json().encode()).hexdigest()
    report = {'scan_id': scan.scan_id, 'scan_sha256': digest, 'map_sha256': hashlib.sha256(m.model_dump_json().encode()).hexdigest(),
              'voxel_m': scan.voxel_m, 'occupied_voxels': len(occupied), 'observed_free_voxels': len(free), 'unknown_voxels': int(np.prod(dims)) - len(free) - len(occupied),
              'frames': len(loaded), 'physical_acceptance': False, 'example': scan.example,
              'limitations': 'Static surveyed stations; no SLAM, dynamic obstacle sensing or glass/reflectivity guarantee. Recheck controlled zone before use.'}
    return m, report


def rebuild_scans(paths):
    """Combine independently registered stationary captures without changing geometry."""
    import shutil
    import tempfile
    if not paths or len(paths) > 20: raise ValueError('Supply 1–20 registered scans')
    scans = [(Path(path), Scan.model_validate_json(Path(path).read_text())) for path in paths]
    first = scans[0][1]
    fields = ('map_id', 'map_version', 'frame_id', 'units', 'axes', 'permitted', 'voxel_m', 'uncertainty_m', 'max_depth_m', 'example')
    for _, scan in scans:
        if any(getattr(first, field) != getattr(scan, field) for field in fields): raise ValueError('Registered scan map/settings mismatch')
    with tempfile.TemporaryDirectory(prefix='ball-map-rebuild-') as directory:
        combined = []
        for index, (path, scan) in enumerate(scans):
            root = path.parent.resolve()
            for frame in scan.frames:
                source = (root / frame.file).resolve()
                if source.parent != root or source.stat().st_size > 30_000_000: raise ValueError('Invalid capture file path/size')
                name = f'station-{index}-{frame.file}'
                shutil.copyfile(source, Path(directory) / name)
                combined.append(frame.model_copy(update={'file': name}))
        data = first.model_dump()
        data.update(frames=[frame.model_dump() for frame in combined], evidence='; '.join(scan.evidence for _, scan in scans))
        mapped, report = build_map(Scan.model_validate(data), directory)
        report['source_manifests'] = [{'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path, _ in scans]
        return mapped, report


class Station(Contract):
    schema_version: Literal[1]
    scan_id: Identifier
    map_id: Identifier
    map_version: int = Field(ge=1)
    frame_id: Identifier
    permitted: Box
    voxel_m: Positive
    uncertainty_m: Positive
    max_depth_m: Positive
    map_from_depth: Matrix
    registration_evidence: str = Field(min_length=1)
    example: bool

    @model_validator(mode='after')
    def transform(self):
        rigid(self.map_from_depth)
        return self


def capture_d435(station, output, frames=30, sdk=None, *, registration_survey=None, registration_policy=None,
                 on_frame=None, on_progress=None, on_registration=None):
    """Native rectified depth + color + raw BAG; no alignment/exposure-time guesses."""
    import importlib.metadata
    import time
    from datetime import datetime, timezone
    if type(frames) is not int or not 1 <= frames <= 1000: raise ValueError('Capture 1–1000 frames')
    station = Station.model_validate(station.model_dump() if isinstance(station, Station) else station)
    injected = sdk is not None and getattr(sdk, '__name__', '') != 'pyrealsense2'
    if station.example and not injected: raise ValueError('Measure station registration; examples cannot capture real hardware')
    if registration_policy is not None and registration_survey is None: raise ValueError('Registration policy requires a survey')
    if registration_survey is not None:
        from .map_io import Survey
        from .registration import StationRegistrar, rgb_geometry
        registration_survey = Survey.model_validate(registration_survey.model_dump() if isinstance(registration_survey, Survey) else registration_survey)
        if (station.map_id, station.map_version, station.frame_id, station.example) != (registration_survey.map_id, registration_survey.map_version, registration_survey.frame_id, registration_survey.example):
            raise ValueError('Station/survey registration mismatch')
        if injected and not station.example: raise ValueError('Automatic injected-SDK capture requires synthetic station/survey')
    if sdk is None:
        try: import pyrealsense2 as sdk
        except ImportError as error: raise ValueError('D435 SDK unavailable on this Python/platform; use a supported capture environment and import saved frames') from error
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    pipeline, config = sdk.pipeline(), sdk.config()
    config.enable_stream(sdk.stream.depth, 640, 480, sdk.format.z16, 30)
    config.enable_stream(sdk.stream.color, 640, 480, sdk.format.bgr8, 30)
    config.enable_record_to_file(str(output / 'raw.bag'))
    started = False
    try:
        profile = pipeline.start(config)
        started = True
        device = profile.get_device()
        name = device.get_info(sdk.camera_info.name)
        if name.strip() not in ('Intel RealSense D435', 'Intel RealSense D435 Camera', 'RealSense D435'): raise ValueError('Expected exact D435 device; review capabilities for other models')
        scale = device.first_depth_sensor().get_depth_scale()
        if not np.isfinite(scale) or scale <= 0: raise ValueError('Invalid SDK depth scale')
        for _ in range(30): pipeline.wait_for_frames(5000)
        captures, metadata = [], {}
        registrar, previous_stamps = None, None
        for i in range(frames):
            sample = pipeline.wait_for_frames(5000)
            received = time.monotonic()
            depth, color = sample.get_depth_frame(), sample.get_color_frame()
            if not depth or not color: raise ValueError('Incomplete D435 frame set')
            dprofile, cprofile = depth.profile.as_video_stream_profile(), color.profile.as_video_stream_profile()
            intr = dprofile.get_intrinsics()
            if any(abs(c) > 1e-10 for c in intr.coeffs): raise ValueError('Mapper requires rectified pinhole depth; preserve raw BAG and explicitly rectify')
            k = DepthIntrinsics(width=intr.width, height=intr.height, fx=float(intr.fx), fy=float(intr.fy), cx=float(intr.ppx), cy=float(intr.ppy), model='rectified_pinhole')
            raw_depth = np.asanyarray(depth.get_data())
            if raw_depth.dtype != np.uint16 or raw_depth.shape != (k.height, k.width): raise ValueError('Expected final-size z16 depth format')
            ci = cprofile.get_intrinsics()
            # Validate factory RGB and inter-camera geometry before preserving it.
            DepthIntrinsics(width=ci.width, height=ci.height, fx=float(ci.fx), fy=float(ci.fy), cx=float(ci.ppx), cy=float(ci.ppy), model='rectified_pinhole')
            if not np.isfinite(ci.coeffs).all(): raise ValueError('Nonfinite RGB calibration')
            extr = dprofile.get_extrinsics_to(cprofile)
            color_from_depth = np.eye(4)
            color_from_depth[:3, :3] = np.array(extr.rotation).reshape(3, 3, order='F')
            color_from_depth[:3, 3] = extr.translation
            rigid(color_from_depth)
            color_data = np.asanyarray(color.get_data())
            if color_data.dtype != np.uint8 or color_data.shape != (ci.height, ci.width, 3): raise ValueError('Expected final-size BGR8 color format')
            if on_frame is not None: on_frame(color_data)
            if registration_survey is not None:
                current_camera = rgb_geometry(ci)
                if registrar is None:
                    registrar = StationRegistrar(current_camera, registration_survey, color_from_depth, registration_policy,
                        'synthetic_estimate' if injected else 'vision_estimate')
                elif current_camera != registrar.camera or not np.allclose(color_from_depth, registrar.extr, atol=1e-9):
                    raise ValueError('Scanner calibration changed during capture')
                stamps = (float(depth.get_timestamp()), float(color.get_timestamp()), str(depth.get_frame_timestamp_domain()), str(color.get_frame_timestamp_domain()))
                if previous_stamps is not None and (stamps[2:] != previous_stamps[2:] or stamps[0] <= previous_stamps[0] or stamps[1] <= previous_stamps[1]):
                    raise ValueError('Scanner timestamps stopped advancing or changed domains')
                try:
                    registrar.observe(color_data, received)
                except Exception as error:
                    if on_registration is not None: on_registration({'stable': False, 'message': str(error), 'tag_ids': []})
                    raise
                if on_registration is not None:
                    result = registrar.result()
                    on_registration({'stable': result is not None, 'message': registrar.issue,
                                     'tag_ids': result.tag_ids if result else [],
                                     'uncertainty_m': result.uncertainty_m if result else None})
                previous_stamps = stamps
            filename = f'frame-{i:04d}.npz'
            np.savez_compressed(output / filename, depth_m=raw_depth.astype(float) * scale, raw_depth=raw_depth, color_bgr=color_data)
            captures.append(DepthFrame(file=filename, sha256=hashlib.sha256((output / filename).read_bytes()).hexdigest(), intrinsics=k,
                map_from_depth=station.map_from_depth, registration_evidence=station.registration_evidence,
                hardware_timestamp_ms=float(depth.get_timestamp()), hardware_clock_domain=str(depth.get_frame_timestamp_domain()), host_received_s=received,
                color_hardware_timestamp_ms=float(color.get_timestamp()), color_hardware_clock_domain=str(color.get_frame_timestamp_domain())))
            metadata = {'device_name': name, 'firmware': device.get_info(sdk.camera_info.firmware_version), 'depth_scale_m': scale,
                        'depth_model': str(intr.model), 'depth_coefficients': list(intr.coeffs),
                        'color_intrinsics': {'width': ci.width, 'height': ci.height, 'fx': ci.fx, 'fy': ci.fy, 'cx': ci.ppx, 'cy': ci.ppy, 'model': str(ci.model), 'coefficients': list(ci.coeffs)},
                        'depth_to_color': {'rotation_column_major': list(extr.rotation), 'translation_m': list(extr.translation)},
                        'color_hardware_timestamp_ms': float(color.get_timestamp()), 'color_clock_domain': str(color.get_frame_timestamp_domain()),
                        'timestamp_note': 'Device clock timestamps and host receipt remain separate; no host exposure timestamp inferred.'}
            if on_progress is not None: on_progress(i + 1, frames)
        if registrar is not None:
            result = registrar.result()
            if result is None: raise ValueError('Not enough stable registration frames')
            station = registrar.station(station)
            for frame in captures:
                frame.map_from_depth = station.map_from_depth
                frame.registration_evidence = station.registration_evidence
            (output / 'registration.json').write_text(result.model_dump_json(indent=2) + '\n')
            metadata['registration_sha256'] = hashlib.sha256((output / 'registration.json').read_bytes()).hexdigest()
        metadata['capture_environment'] = 'injected_test_sdk' if injected else 'real_sdk'
        values = station.model_dump(exclude={'map_from_depth', 'registration_evidence'})
        values.update(camera_model='D435', example=station.example or injected, serial=device.get_info(sdk.camera_info.serial_number), sdk_version=importlib.metadata.version('pyrealsense2') if sdk.__name__ == 'pyrealsense2' else 'injected-test-sdk',
            units='m', axes='right_handed_z_up', acquired_utc=datetime.now(timezone.utc).isoformat(), evidence=station.registration_evidence, frames=captures, camera_metadata=metadata)
        scan = Scan.model_validate(values)
        (output / 'scan.json').write_text(scan.model_dump_json(indent=2) + '\n')
        return scan
    except Exception as error:
        try: (output / 'INCOMPLETE.json').write_text(json.dumps({'error': str(error), 'physical_acceptance': False}) + '\n')
        except OSError: pass
        raise
    finally:
        if started: pipeline.stop()
