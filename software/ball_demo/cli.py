import argparse
import csv
import json
import logging
import os
import re
import secrets
import sys
import time
from pathlib import Path

import cv2
import uvicorn

from .api import create_app
from .bridge import DEFAULT_BAUD, SerialBridge
from .config import Settings
from .engine import Engine
from .fixtures import generate
from .protocol import BridgeCore


def main():
    parser = argparse.ArgumentParser(description='Ball Drone software demo; transmitter output only via an opted-in ESP32-S3 bridge')
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve')
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', type=int, default=8080)
    serve.add_argument('--data', default=os.environ.get('BALL_DATA_DIR', 'runs'))
    serve.add_argument('--roster', default=os.environ.get('BALL_ROSTER_FILE'),
                       help='Private server-owned JSON file containing measured person tags and landing pads')
    serve.add_argument('--serial', help='Explicit ESP32-S3 bridge device opt-in, e.g. /dev/ttyACM0')
    serve.add_argument('--baud', type=int, default=DEFAULT_BAUD,
                       help=f'Bridge serial baud; must match the sketch (default {DEFAULT_BAUD})')
    serve.add_argument('--trainer-output', action='store_true',
                       help='Accept an ESP32-S3 bridge that reports PPM trainer yaw output (arming jumper fitted). '
                            'Startup stays MANUAL and disabled; output is not physically verified')
    serve.add_argument('--portable-demo', action='store_true',
                       help='Generated AprilTag images and invented geometry; no hardware or aircraft output')
    serve.add_argument('--target-calibration', help='Versioned FPV Calibration JSON for informational relative tracking')
    serve.add_argument('--target-delay-ms', type=float, help='Measured positive capture/exposure delay bound below 250 ms')
    serve.add_argument('--nav-bundle', help='Validated versioned navigation bundle; advisory only')
    serve.add_argument('--nav-replay', help='Paced observation recording; no navigation bridge output')
    start = serve.add_mutually_exclusive_group()
    start.add_argument('--recorded', help='Start disabled on a video file')
    start.add_argument('--camera', help='Start disabled on a live camera: index such as 0, or a device path such as /dev/video0')
    serve.add_argument('--camera-backend', choices=['auto', 'v4l2', 'default'], default='auto',
                       help='auto uses Video4Linux2 on Linux and the OpenCV default elsewhere')
    serve.add_argument('--capture-mode', default='720x480@30', type=capture_mode,
                       help='Mode requested from the live camera as WIDTHxHEIGHT@FPS (default 720x480@30, NTSC; '
                            'PAL is 720x576@25). The opened mode is read back and a size/format mismatch is a fault')
    serve.add_argument('--capture-fourcc', default='YUYV', help='Pixel format requested from the live camera (default YUYV)')
    serve.add_argument('--target-mode', choices=['color', 'tag', 'landing'], default='color',
                       help='Steer toward the HSV ball (color), follow an AprilTag (tag) or line up on a landing-pad '
                            'tag (landing). Changeable live from the operator panel; yaw-only either way')
    serve.add_argument('--tag-id', type=int, default=-1, help='AprilTag ID to steer toward (-1: choose from the roster)')
    tags = sub.add_parser('tags', help='AprilTag kit: register, print and test tags (see `ball-demo tags -h`)')
    from .tag_kit import add_arguments as tag_arguments
    tag_arguments(tags)
    fixtures = sub.add_parser('fixtures')
    fixtures.add_argument('--output', default='runs/fixtures')
    fixtures.add_argument('--frames', type=int, default=160)
    replay = sub.add_parser('replay')
    replay.add_argument('session')
    replay.add_argument('--output', default='runs/replay.json')
    nav_fixtures = sub.add_parser('nav-fixtures', help='Clearly labeled invented navigation fixtures and schemas')
    nav_fixtures.add_argument('--output', default='runs/navigation-fixtures')
    nav_replay = sub.add_parser('nav-replay', help='Deterministically replay navigation observations without bridge access')
    nav_replay.add_argument('recording')
    nav_replay.add_argument('--output', default='runs/navigation-replay.json')
    nav_demo = sub.add_parser('nav-demo', help='Estimated-vision mock waypoint follower; no aircraft output')
    nav_demo.add_argument('recording')
    nav_demo.add_argument('--output', default='runs/navigation-demo.json')
    nav_simulate = sub.add_parser('nav-simulate', help='Mock autonomous route using a labeled simulation copy of a D435 map bundle')
    nav_simulate.add_argument('--bundle', required=True)
    nav_simulate.add_argument('--start', nargs=3, type=float, required=True)
    nav_simulate.add_argument('--goal', nargs=3, type=float, required=True)
    nav_simulate.add_argument('--yaw-deg', type=float, default=90.)
    nav_simulate.add_argument('--frames', type=int, default=600)
    nav_simulate.add_argument('--output', default='runs/mapped-navigation-demo.json')
    nav_calibrate = sub.add_parser('nav-calibrate', help='Calibrate final resized checkerboard captures')
    nav_calibrate.add_argument('--bundle', required=True, help='Template bundle with independently measured mount transform')
    nav_calibrate.add_argument('--images', required=True, help='Directory of final-size PNG images')
    nav_calibrate.add_argument('--columns', type=int, required=True)
    nav_calibrate.add_argument('--rows', type=int, required=True)
    nav_calibrate.add_argument('--square-m', type=float, required=True)
    nav_calibrate.add_argument('--output', required=True)
    nav_map = sub.add_parser('nav-map', help='Repeatable map rebuild from registered D435 captures')
    nav_map.add_argument('scan', nargs='+', help='One or more saved, registered scan.json manifests')
    nav_map.add_argument('--output', required=True, help='New directory for map and reconstruction report')
    nav_capture = sub.add_parser('nav-capture-d435', help='Capture static surveyed D435 station; requires optional RealSense SDK')
    nav_capture.add_argument('--station', required=True, help='Measured Station JSON, in the tag/map frame')
    nav_capture.add_argument('--output', required=True, help='New capture directory')
    nav_capture.add_argument('--frames', type=int, default=30)
    nav_capture.add_argument('--registration-survey', help='Automatically register and monitor this fixed station using surveyed RGB AprilTags')
    nav_capture.add_argument('--registration-policy', help='Optional strict registration quality/stability policy JSON')
    nav_register = sub.add_parser('nav-register-d435', help='Register a stationary scanner from saved RGB/tag images; no device access')
    nav_register.add_argument('--input', required=True, help='Versioned registration manifest with hashes, RGB geometry, depth extrinsic and surveyed tags')
    nav_register.add_argument('--output', required=True, help='New directory for station, registration and completion reports')
    nav_bundle = sub.add_parser('nav-bundle', help='Validate and assemble versioned measured map/survey/calibration')
    nav_bundle.add_argument('--map', required=True)
    nav_bundle.add_argument('--survey', required=True)
    nav_bundle.add_argument('--calibration', required=True)
    nav_bundle.add_argument('--policy', required=True)
    nav_bundle.add_argument('--id', required=True)
    nav_bundle.add_argument('--output', required=True)
    sub.add_parser('bridge-check')
    cameras = sub.add_parser('cameras', help='List cameras OpenCV can open, with their frame size')
    cameras.add_argument('--max-index', type=int, default=5)
    latency = sub.add_parser('latency', help='Measure camera-to-decision latency with a flashing target')
    latency_source = latency.add_mutually_exclusive_group(required=True)
    latency_source.add_argument('--camera', help='Camera index or device path')
    latency_source.add_argument('--simulated-delay-ms', type=float, help='Check the tool against a simulated camera with this delay')
    latency.add_argument('--camera-backend', choices=['auto', 'v4l2', 'default'], default='auto')
    latency.add_argument('--trigger', choices=['screen', 'gpio'], default='screen', help='screen: full-screen flash window; gpio: Pi LED')
    latency.add_argument('--gpio-pin', type=int, default=17)
    latency.add_argument('--trials', type=int, default=20)
    latency.add_argument('--timeout', type=float, default=2.0)
    latency.add_argument('--output', default='runs/latency.json')
    card = sub.add_parser('connection-card')
    card.add_argument('--url', required=True)
    card.add_argument('--network', default='Shared network')
    card.add_argument('--output', default='runs/connection-card')
    args = parser.parse_args()
    if args.command == 'tags':
        from .tag_kit import run as run_tags
        try:
            raise SystemExit(run_tags(args))
        except ValueError as error:
            raise SystemExit(f'Error: {error}')
    if args.command == 'serve' and not -1 <= args.tag_id <= 586:
        serve.error('--tag-id must be -1 or 0-586')
    if args.command == 'serve' and args.trainer_output and not args.serial:
        serve.error('--trainer-output requires --serial')
    if args.command == 'serve':
        if args.portable_demo and (args.camera or args.recorded or args.serial or args.roster or args.nav_bundle or args.nav_replay or args.target_calibration):
            parser.error('--portable-demo uses generated images, mock bridge and its own fictional roster/geometry')
        if bool(args.target_calibration) != (args.target_delay_ms is not None):
            parser.error('--target-calibration and --target-delay-ms are required together')
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
        logging.getLogger(__name__).info('OpenCV %s', cv2.__version__)
        for warning in startup_warnings(args): logging.getLogger(__name__).warning(warning)
        token = os.environ.get('BALL_OPERATOR_TOKEN') or secrets.token_urlsafe(24)
        Path(args.data).mkdir(parents=True, exist_ok=True)
        token_path = Path(args.data) / 'operator-token'
        fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as f: f.write(token + '\n')
        print(f'Visitor URL: http://{args.host}:{args.port}/', flush=True)
        print(f'Operator token saved to {token_path.resolve()} (local, private). Startup: MANUAL.', flush=True)
        source = {'kind': 'recorded', 'path': args.recorded} if args.recorded else camera_spec(args.camera, args.camera_backend) if args.camera else None
        bridge = SerialBridge(args.serial, baud=args.baud, trainer_output=args.trainer_output) if args.serial else None
        bundle, recording = None, None
        if args.nav_bundle or args.nav_replay:
            from .map_io import load_bundle
            from .navigation_replay import load_recording
            bundle = load_bundle(args.nav_bundle) if args.nav_bundle else None
            recording = load_recording(args.nav_replay) if args.nav_replay else None
            bundle = bundle or recording.bundle
        from .roster import load_roster
        # A roster path that does not exist yet is allowed: tags can be added later and reloaded live.
        prepared_roster = load_roster(args.roster) if args.roster and Path(args.roster).exists() else None
        calibration, delay_s = None, None
        if args.portable_demo:
            from .portable_demo import demo_calibration, demo_roster
            source, prepared_roster = {'kind': 'synthetic', 'scenario': 'portable-tags'}, demo_roster()
            calibration, delay_s = demo_calibration(), .01
        elif args.target_calibration:
            from .map_io import Calibration
            calibration = Calibration.model_validate_json(Path(args.target_calibration).read_text())
            delay_s = args.target_delay_ms / 1000
        width, height, fps = args.capture_mode
        settings = Settings(capture_width=width, capture_height=height, capture_fps=fps, capture_fourcc=args.capture_fourcc,
                            target_mode=args.target_mode, tag_id=args.tag_id)
        engine = Engine(args.data, settings=settings, bridge=bridge, source=source, navigation_bundle=bundle,
                        navigation_recording=recording, roster=prepared_roster,
                        portable_calibration=calibration, portable_delay_s=delay_s,
                        roster_path=None if args.portable_demo else args.roster)
        class DemoServer(uvicorn.Server):
            def handle_exit(self, sig, frame):
                engine.assist(False)
                engine.running = False
                super().handle_exit(sig, frame)
        server = DemoServer(uvicorn.Config(create_app(engine, token), host=args.host, port=args.port,
                                          log_level='warning', timeout_graceful_shutdown=2))
        server.run()
    elif args.command == 'nav-map':
        from .mapping import rebuild_scans
        mapped, report = rebuild_scans(args.scan)
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=False)
        (output / 'map.json').write_text(mapped.model_dump_json(indent=2) + '\n')
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(output.resolve())
    elif args.command == 'nav-register-d435':
        from .registration import register_directory
        register_directory(args.input, args.output)
        print(Path(args.output).resolve())
    elif args.command == 'nav-capture-d435':
        from .mapping import Station, capture_d435
        station = Station.model_validate_json(Path(args.station).read_text())
        if args.registration_survey:
            from .map_io import Survey
            from .registration import RegistrationPolicy
            survey = Survey.model_validate_json(Path(args.registration_survey).read_text())
            policy = RegistrationPolicy.model_validate_json(Path(args.registration_policy).read_text()) if args.registration_policy else None
            capture_d435(station, args.output, args.frames, registration_survey=survey, registration_policy=policy)
        else:
            if args.registration_policy: raise SystemExit('--registration-policy requires --registration-survey')
            capture_d435(station, args.output, args.frames)
        print(Path(args.output).resolve())
    elif args.command == 'nav-bundle':
        from .map_io import Bundle
        data = {'schema_version': 1, 'bundle_id': args.id}
        for name in ('map', 'survey', 'calibration', 'policy'):
            data[name] = json.loads(Path(getattr(args, name)).read_text())
        bundle = Bundle.model_validate(data)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x') as file: file.write(bundle.model_dump_json(indent=2) + '\n')
        print(f'{output.resolve()} / SHA256 {bundle.digest}')
    elif args.command == 'nav-fixtures':
        from .navigation_fixtures import generate as navigation_fixtures
        print(navigation_fixtures(args.output).resolve())
    elif args.command == 'nav-simulate':
        from .map_io import load_bundle
        from .navigation_fixtures import simulation_recording
        from .navigation_replay import simulation
        bundle = load_bundle(args.bundle)
        recording = simulation_recording(bundle, args.start, args.goal, args.yaw_deg)
        result = simulation(recording, limit=args.frames)
        result['source_bundle_sha256'] = bundle.digest
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print(output.resolve())
    elif args.command in ('nav-replay', 'nav-demo'):
        from .navigation_replay import load_recording, replay as navigation_replay, simulation
        recording = load_recording(args.recording)
        result = navigation_replay(recording) if args.command == 'nav-replay' else simulation(recording)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print(output.resolve())
    elif args.command == 'nav-calibrate':
        from .map_io import load_bundle
        from .calibration import calibrate
        template = load_bundle(args.bundle)
        paths = sorted(Path(args.images).glob('*.png'))
        images = [cv2.imread(str(path)) for path in paths]
        if not images or any(image is None for image in images): parser.error('Supply readable final-size PNG images')
        calibration, views = calibrate(images, args.columns, args.rows, args.square_m, template.calibration)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(calibration.model_dump_json(indent=2) + '\n')
        print(f'{output.resolve()} / {views} detected views / RMS {calibration.reprojection_rms_px:.3f} px; independent validation pending')
    elif args.command == 'fixtures': generate(args.output, args.frames)
    elif args.command == 'cameras':
        found = probe_cameras(args.max_index)
        for entry in found: print(f"{entry['device']}: {entry['width']} x {entry['height']} @ {entry['fps']:.1f} fps (reported)")
        if not found: print('No camera opened. Check the capture adapter, permissions and /dev/video* devices.')
    elif args.command == 'latency': run_latency(args)
    elif args.command == 'bridge-check':
        core = BridgeCore()
        print(core.receive('HELLO 1 demo\n', 0), end='')
        print(core.receive('CMD 1 demo 1 1 200\n', .1), end='')
        core.tick(.351)
        assert core.yaw == 0 and core.fault == 'WATCHDOG'
        print('WATCHDOG: neutral; no physical output')
    elif args.command == 'replay':
        root = Path(args.session)
        samples = []
        with (root / 'samples.csv').open() as f:
            for row in csv.DictReader(f):
                detection = None
                if row['x']:
                    detection = {'x': float(row['x']), 'y': float(row['y']), 'error': float(row['error']), 'quality': float(row['quality'])}
                samples.append({'t': float(row['t']), 'state': row['state'], 'yaw': int(row['yaw']), 'detection': detection})
        events = [json.loads(line) for line in (root / 'events.jsonl').read_text().splitlines()]
        config = json.loads((root / 'config.json').read_text()) if (root / 'config.json').exists() else {}
        sources = [config.get('source')] + [e['data'] for e in events if e.get('type') == 'source']
        kinds = sorted({s.get('kind') for s in sources if isinstance(s, dict) and s.get('kind')})
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Recorded sessions keep their provenance; the video itself is not part of a replay file.
        output.write_text(json.dumps({'label': 'REPLAY / ' + ('+'.join(k.upper() for k in kinds) or 'UNKNOWN') + ' session / no bridge output',
                                      'session': config.get('id', root.name), 'sources': [s for s in sources if s],
                                      'settings': config.get('settings', {}), 'video_included': False,
                                      'samples': samples, 'events': events}))
        print(output.resolve())
    elif args.command == 'connection-card':
        import qrcode
        from urllib.parse import urlparse
        if urlparse(args.url).scheme not in ['http', 'https']: parser.error('Provide the active HTTP visitor URL')
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        qrcode.make(args.url).save(output / 'visitor-qr.png')
        (output / 'visitor.txt').write_text(f'Ball Drone visitor access\nNetwork: {args.network}\nURL: {args.url}\nNo operator credentials required.\n')
        print(output.resolve())



def capture_mode(value):
    """'720x480@30' -> (720, 480, 30.0)."""
    match = re.fullmatch(r'(\d+)x(\d+)@(\d+(?:\.\d+)?)', value)
    if not match: raise argparse.ArgumentTypeError('capture mode must look like 720x480@30')
    return int(match[1]), int(match[2]), float(match[3])


def startup_warnings(args):
    """Loud lines for every input that fell back to synthetic/mock instead of real hardware."""
    if args.portable_demo: return []
    warnings = []
    if not args.camera and not args.recorded:
        warnings.append('NO CAMERA CONFIGURED (--camera): running on SYNTHETIC video, NOT a live FPV feed')
    if not args.serial:
        warnings.append('NO SERIAL BRIDGE CONFIGURED (--serial): MOCK bridge, no PPM output reaches the transmitter')
    return warnings


def camera_device(value):
    """'0' -> 0 (OpenCV index); anything else stays a device path."""
    return int(value) if str(value).isdigit() else value


def camera_spec(value, backend='auto', platform=None):
    platform = platform or sys.platform
    spec = {'kind': 'camera', 'device': camera_device(value)}
    if backend == 'v4l2' or (backend == 'auto' and platform.startswith('linux')):
        spec['backend'] = 'v4l2'
    return spec


def probe_cameras(max_index=5, platform=None):
    import cv2
    from pathlib import Path as _Path
    platform = platform or sys.platform
    candidates = list(range(max_index + 1))
    if platform.startswith('linux'):
        candidates = sorted(str(path) for path in _Path('/dev').glob('video*')) or candidates
    found = []
    for device in candidates:
        capture = cv2.VideoCapture(device)
        try:
            if capture.isOpened():
                found.append({'device': device, 'width': int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                              'height': int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                              'fps': float(capture.get(cv2.CAP_PROP_FPS) or 0)})
        finally:
            capture.release()
    return found


def run_latency(args):
    from .config import Settings
    from .latency import GpioLed, QtFlash, SimulatedCamera, measure, save
    from .sources import OpenCVSource
    settings = Settings()
    if args.simulated_delay_ms is not None:
        camera = SimulatedCamera(args.simulated_delay_ms / 1000, settings=settings)
        source, trigger, closers = camera, camera.trigger, []
    else:
        spec = camera_spec(args.camera, args.camera_backend)
        source = OpenCVSource(spec['device'], settings, backend=spec.get('backend'))
        trigger = GpioLed(args.gpio_pin) if args.trigger == 'gpio' else QtFlash(settings)
        closers = [source, trigger]
    try:
        summary = measure(source, trigger, settings, args.trials, args.timeout)
    finally:
        for item in closers: item.close()
    summary['configuration'] = {'camera': args.camera, 'simulated_delay_ms': args.simulated_delay_ms,
                                'trigger': 'simulated' if args.simulated_delay_ms is not None else args.trigger}
    path = save(summary, args.output)
    print(json.dumps({k: v for k, v in summary.items() if k != 'results'}, indent=2))
    print(path.resolve())
    return summary


if __name__ == '__main__': main()
