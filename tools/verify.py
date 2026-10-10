"""Reproducible software/host-firmware verification with traceable, failure-preserving output."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOFTWARE = ROOT / 'software'
MODULE_FLOORS = {'control.py': 100, 'protocol.py': 95, 'engine.py': 95, 'bridge.py': 95,
                 'api.py': 95, 'desktop_backend.py': 95, 'serial_emulator.py': 90,
                 'sources.py': 100, 'vision.py': 100, 'desktop.py': 95,
                 'video_health.py': 100, 'color_pick.py': 100, 'latency.py': 90, 'session.py': 95}
MODULE_FLOORS.update({name: 95 for name in ('calibration.py', 'map_io.py', 'localization.py', 'navigation_guard.py',
    'navigation.py', 'navigation_runtime.py', 'navigation_replay.py', 'navigation_fixtures.py', 'mapping.py',
    'navigation_visibility.py', 'registration.py', 'synthetic_navigation.py', 'arrival.py', 'mission.py',
    'mission_control.py')})
MODULE_FLOORS.update({'roster.py': 95, 'target_tracking.py': 95, 'ui_api.py': 95,
                     'portable_runtime.py': 95, 'portable_demo.py': 95,
                     'tag_detector.py': 100, 'follow_simulation.py': 100, 'landing_simulation.py': 100})
# Everything that executes or is served: browser assets, deploy scripts and the Mac builder count too.
FINGERPRINT_DIRS = ('software/ball_demo', 'software/tests', 'software/deploy', 'software/desktop',
                    'software/examples', 'software/flutter_operator', 'firmware', 'tools', '.github/workflows')
FINGERPRINT_SUFFIXES = ('.py', '.c', '.h', '.ino', '.toml', '.lock', '.js', '.mjs', '.html', '.css',
                       '.sh', '.service', '.txt', '.json', '.npz', '.dart', '.yaml', '.yml', '.kt',
                       '.kts', '.swift', '.xml', '.plist', '.png', '.svg', '.gradle', '.properties')


@contextmanager
def visible_coverage_startup():
    """Python 3.13 skips UF_HIDDEN .pth files in this Mac's file-provider venv."""
    path = Path(importlib.metadata.distribution('coverage').locate_file('a1_coverage.pth'))
    info = {'path': str(path), 'temporarily_unhidden': False}
    original = None
    if sys.platform == 'darwin' and path.exists():
        flags = path.stat().st_flags
        if flags & stat.UF_HIDDEN:
            original = flags
            os.chflags(path, flags & ~stat.UF_HIDDEN)
            info['temporarily_unhidden'] = True
    try:
        yield info
    finally:
        if original is not None:
            current = path.stat().st_flags
            os.chflags(path, current | stat.UF_HIDDEN)


def fingerprint():
    files = {}
    for directory in FINGERPRINT_DIRS:
        for base, dirs, names in os.walk(ROOT / directory):
            dirs[:] = [name for name in dirs if not name.startswith('build') and name not in
                       ('__pycache__', '.venv', '.dart_tool', '.gradle', 'ephemeral', 'coverage')]
            for name in names:
                path = Path(base) / name
                if path.suffix not in FINGERPRINT_SUFFIXES or name in ('local.properties', '.flutter-plugins-dependencies'): continue
                files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [SOFTWARE / 'pyproject.toml', *SOFTWARE.glob('requirements*.lock')]:
        files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {'sha256': digest, 'files': files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('core', 'desktop', 'flutter'), default='desktop')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--min-coverage', type=float, default=95)
    parser.add_argument('--require-esp32', action='store_true', help='Fail unless the selected ESP32-S3 target compiles')
    parser.add_argument('--sanitizers', choices=('undefined', 'address,undefined'),
                        default='undefined' if sys.platform == 'darwin' else 'address,undefined')
    args = parser.parse_args()
    if args.profile == 'flutter':
        runner = ROOT / 'software/flutter_operator/tool/verify.py'
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        output = args.output or ROOT / 'evidence/verification' / (stamp + '-flutter')
        return subprocess.call([sys.executable, str(runner), '--output', str(output)])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = (args.output or ROOT / 'evidence/verification' / stamp).resolve()
    if output.exists(): parser.error('Output must be a new directory; prior evidence is never overwritten')
    output.mkdir(parents=True)
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'profile': args.profile,
              'environment': {'platform': platform.platform(), 'architecture': platform.machine(),
                              'python': sys.version, 'executable': sys.executable},
              'dependencies': {}, 'source_before': fingerprint(), 'checks': [],
              'limits': ['Synthetic/PTY/software only; no physical serial port or aircraft.',
                         'Offscreen Qt checks do not establish Pi display/device/performance behavior.',
                         'Coverage records executed paths, not correctness or flight readiness.',
                         'No packaged-app/endurance or browser rehearsal is implied by this run.']}
    started = time.monotonic()
    def check(name, passed, **data):
        report['checks'].append({'name': name, 'pass': bool(passed), **data})
        print(('PASS' if passed else 'FAIL') + ': ' + name, flush=True)
    try:
        required = ['pytest', 'pytest-cov', 'coverage', 'opencv-python-headless', 'fastapi', 'pyserial']
        if args.profile == 'desktop': required += ['PySide6-Essentials', 'shiboken6']
        for name in required: report['dependencies'][name] = importlib.metadata.version(name)
        check('required dependencies', True)
        with visible_coverage_startup() as startup, tempfile.TemporaryDirectory(prefix='ball-verify-') as runtime:
            report['coverage_startup'] = startup
            env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'COVERAGE_FILE': str(Path(runtime) / '.coverage'),
                   # Resolve source packages before any installed copy even during
                   # Python's early .pth/coverage startup in subprocesses.
                   'PYTHONPATH': str(SOFTWARE) + (os.pathsep + os.environ['PYTHONPATH'] if os.environ.get('PYTHONPATH') else '')}
            coverage_config = SOFTWARE / 'pyproject.toml'
            if args.profile == 'core':
                coverage_config = Path(runtime) / 'core.coveragerc'
                coverage_config.write_text('[run]\nbranch = true\nparallel = true\nconcurrency = thread, multiprocessing\npatch = subprocess, _exit\nsigterm = true\nomit = */ball_demo/desktop.py\n')
            command = [sys.executable, '-m', 'pytest', 'tests', '-q', '--tb=short',
                       '--junitxml=' + str(output / 'junit.xml'), '--cov=ball_demo', '--cov-branch',
                       '--cov-config=' + str(coverage_config), '--cov-fail-under=' + str(args.min_coverage),
                       '--cov-report=term-missing', '--cov-report=json:' + str(output / 'coverage.json'),
                       '--cov-report=html:' + str(output / 'coverage-html')]
            if args.profile == 'core': command += ['--ignore=tests/test_desktop.py', '--ignore=tests/test_desktop_edges.py',
                                                  '--ignore=tests/test_desktop_robustness.py', '--ignore=tests/test_desktop_matrix.py', '--ignore=tests/test_navigation_desktop.py']
            with (output / 'pytest.txt').open('w') as log:
                result = subprocess.run(command, cwd=SOFTWARE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=240)
            check('pytest and coverage floor', result.returncode == 0, exit_code=result.returncode,
                  command=command, minimum_coverage=args.min_coverage, output='pytest.txt')
            tree = ET.parse(output / 'junit.xml')
            suites = list(tree.getroot().iter('testsuite'))
            counts = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
                      for key in ('tests', 'failures', 'errors', 'skipped')}
            report['pytest'] = counts
            check('no silently skipped checks', counts['skipped'] == 0, **counts)
            coverage = json.loads((output / 'coverage.json').read_text())
            report['coverage'] = {'totals': coverage['totals'], 'files': {
                name: data['summary'] for name, data in coverage['files'].items()}}
            for module, minimum in MODULE_FLOORS.items():
                if args.profile == 'core' and module == 'desktop.py': continue
                entry = next(data for name, data in coverage['files'].items() if name.endswith('/' + module))
                actual = entry['summary']['percent_covered']
                check('coverage floor: ' + module, actual >= minimum, actual=actual, minimum=minimum)
            compiler = shutil.which('clang') or shutil.which('cc')
            if not compiler: raise RuntimeError('A host C compiler is required for portable firmware checks')
            report['compiler'] = subprocess.run([compiler, '--version'], capture_output=True, text=True, check=True).stdout
            binary = Path(runtime) / 'firmware-tests'
            compile_command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                               '-fsanitize=' + args.sanitizers, '-fno-omit-frame-pointer',
                               str(ROOT / 'firmware/core.c'), str(ROOT / 'firmware/test_core.c'), '-o', str(binary)]
            with (output / 'firmware.txt').open('w') as log:
                built = subprocess.run(compile_command, stdout=log, stderr=subprocess.STDOUT, timeout=60)
                run_code = None
                if built.returncode == 0:
                    run = subprocess.run([str(binary)], stdout=log, stderr=subprocess.STDOUT, timeout=30)
                    run_code = run.returncode
            check('portable firmware sanitizers: ' + args.sanitizers, built.returncode == 0 and run_code == 0,
                  compile_exit=built.returncode, run_exit=run_code, command=compile_command, output='firmware.txt')
            reader_binary = Path(runtime) / 'line-reader-tests'
            reader_command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                              '-fsanitize=' + args.sanitizers, '-fno-sanitize-recover=all', '-fno-omit-frame-pointer',
                              *(str(ROOT / 'firmware' / f) for f in ('core.c', 'line_reader.c', 'test_line_reader.c')),
                              '-o', str(reader_binary)]
            with (output / 'firmware-line-reader.txt').open('w') as log:
                built = subprocess.run(reader_command, stdout=log, stderr=subprocess.STDOUT, timeout=60)
                run_code = subprocess.run([str(reader_binary)], stdout=log, stderr=subprocess.STDOUT, timeout=30).returncode if built.returncode == 0 else None
            check('Mega line framing sanitizers: ' + args.sanitizers, built.returncode == 0 and run_code == 0,
                  compile_exit=built.returncode, run_exit=run_code, command=reader_command, output='firmware-line-reader.txt')
            arduino = shutil.which('arduino-cli')
            if arduino:
                command = [arduino, 'compile', '--fqbn', 'arduino:avr:mega:cpu=atmega2560', '--warnings', 'all',
                           '--output-dir', str(Path(runtime) / 'mega'), str(ROOT / 'firmware/mega/ball_bridge_mega')]
                with (output / 'mega-compile.txt').open('w') as log:
                    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
                own_warnings = [line for line in (output / 'mega-compile.txt').read_text().splitlines()
                                if 'ball_bridge_mega' in line and 'warning' in line.lower()]
                check('Arduino Mega 2560 sketch compiles without warnings in project files',
                      result.returncode == 0 and not own_warnings, command=command, output='mega-compile.txt')
                cores = subprocess.run([arduino, 'core', 'list', '--format', 'json'], capture_output=True, text=True, check=True)
                (output / 'arduino-cores.json').write_text(cores.stdout)
                installed = json.loads(cores.stdout)
                if any(item.get('id') == 'esp32:esp32' for item in installed.get('platforms', [])):
                    command = [arduino, 'compile', '--fqbn', 'esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=default',
                        '--warnings', 'all', '--output-dir', str(output / 'esp32-binaries'),
                        str(ROOT / 'firmware/esp32/ball_bridge_esp32')]
                    with (output / 'esp32-compile.txt').open('w') as log:
                        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
                    own_warnings = [line for line in (output / 'esp32-compile.txt').read_text().splitlines()
                                    if 'ball_bridge_esp32' in line and 'warning' in line.lower()]
                    check('ESP32-S3 no-output sketch compiles without warnings in project files',
                        result.returncode == 0 and not own_warnings, command=command, output='esp32-compile.txt')
                elif args.require_esp32:
                    check('ESP32-S3 toolchain installed', False)
                else:
                    report.setdefault('not_run', []).append('ESP32-S3 compile: esp32:esp32 core not installed')
            else:
                # Recorded, not counted as a pass: the Mega build needs arduino-cli with arduino:avr installed.
                report.setdefault('not_run', []).append('Arduino Mega 2560 compile: arduino-cli not installed')
                if args.require_esp32: check('ESP32-S3 toolchain installed', False)
    except Exception as error:
        check('verification execution', False, error=type(error).__name__ + ': ' + str(error))
    report['source_after'] = fingerprint()
    check('tested sources unchanged during run', report['source_before'] == report['source_after'])
    report['duration_s'] = time.monotonic() - started
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    report['pass'] = bool(report['checks']) and all(item['pass'] for item in report['checks'])
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    artifacts = {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'SHA256SUMS.json'}
    (output / 'SHA256SUMS.json').write_text(json.dumps(artifacts, indent=2))
    print(str(output / 'report.json'))
    return 0 if report['pass'] else 1


if __name__ == '__main__': raise SystemExit(main())
