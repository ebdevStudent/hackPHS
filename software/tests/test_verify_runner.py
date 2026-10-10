"""The verification harness itself must reject failed, skipped or changed-source runs."""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('ball_verification_runner', ROOT / 'tools/verify.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.parametrize('failure', [None, 'pytest', 'skipped', 'coverage', 'source_changed', 'dependency',
                                     'compiler_missing', 'compile', 'firmware_run', 'pytest_timeout',
                                     'report_missing', 'coverage_missing', 'firmware_timeout', 'esp32_missing', 'esp32_compile', 'esp32_warning'])
def test_verifier_preserves_evidence_and_fails_closed(tmp_path, monkeypatch, failure):
    output = tmp_path / 'report'
    monkeypatch.setattr(sys, 'argv', ['verify', '--output', str(output), '--profile', 'core'])
    if failure and failure.startswith('esp32_'):
        sys.argv.append('--require-esp32')
    fingerprints = iter([{'sha256': 'before', 'files': {}},
                         {'sha256': 'changed' if failure == 'source_changed' else 'before', 'files': {}}])
    monkeypatch.setattr(runner, 'fingerprint', lambda: next(fingerprints))
    monkeypatch.setattr(runner.platform, 'platform', lambda: 'isolated-test-platform')
    monkeypatch.setattr(runner.platform, 'machine', lambda: 'test-architecture')
    def version(name):
        if failure == 'dependency': raise runner.importlib.metadata.PackageNotFoundError(name)
        return 'test-version'
    monkeypatch.setattr(runner.importlib.metadata, 'version', version)
    monkeypatch.setattr(runner.shutil, 'which', lambda _: None if failure == 'compiler_missing' else '/fake/clang')
    def execute(command, **kwargs):
        if command[1:3] == ['core', 'list']:
            return SimpleNamespace(returncode=0, stdout=json.dumps({'platforms': [] if failure == 'esp32_missing' else [{'id': 'esp32:esp32', 'installed_version': '3.3.12'}]}))
        if '-m' in command and 'pytest' in command:
            if failure == 'pytest_timeout': raise runner.subprocess.TimeoutExpired(command, 240)
            if failure == 'report_missing': return SimpleNamespace(returncode=0)
            output.joinpath('junit.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="' + ('1' if failure == 'skipped' else '0') + '"/></testsuites>')
            files = {'ball_demo/' + name: {'summary': {'percent_covered': 80 if failure == 'coverage' and name == 'control.py' else 100}}
                     for name in runner.MODULE_FLOORS if name != 'desktop.py'}
            if failure != 'coverage_missing':
                output.joinpath('coverage.json').write_text(json.dumps({'totals': {'percent_covered': 100}, 'files': files}))
            return SimpleNamespace(returncode=1 if failure == 'pytest' else 0)
        if 'esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=default' in command:
            if failure == 'esp32_warning':
                kwargs['stdout'].write('ball_bridge_esp32.ino: warning: forced project warning\n')
            return SimpleNamespace(returncode=1 if failure == 'esp32_compile' else 0)
        if '-o' in command and failure == 'compile': return SimpleNamespace(returncode=1)
        if command[0].endswith('firmware-tests'):
            if failure == 'firmware_timeout': raise runner.subprocess.TimeoutExpired(command, 30)
            if failure == 'firmware_run': return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0, stdout='fake compiler\n')
    monkeypatch.setattr(runner.subprocess, 'run', execute)
    result = runner.main()
    report = json.loads(output.joinpath('report.json').read_text())
    assert report['pass'] is (failure is None)
    assert result == (0 if failure is None else 1)
    assert output.joinpath('SHA256SUMS.json').exists()
    if failure:
        assert any(not check['pass'] for check in report['checks'])
    if failure == 'source_changed':
        assert report['checks'][-1]['name'] == 'tested sources unchanged during run'
        assert report['checks'][-1]['pass'] is False


def test_verifier_refuses_to_overwrite_previous_evidence(tmp_path, monkeypatch):
    existing = tmp_path / 'existing'; existing.mkdir()
    marker = existing / 'report.json'; marker.write_text('preserve me')
    monkeypatch.setattr(sys, 'argv', ['verify', '--output', str(existing)])
    with pytest.raises(SystemExit) as error: runner.main()
    assert error.value.code == 2 and marker.read_text() == 'preserve me'


@pytest.mark.parametrize('hidden,fail_inside', [(False, False), (True, False), (True, True)])
def test_coverage_startup_flag_is_restored_on_success_and_error(tmp_path, monkeypatch, hidden, fail_inside):
    path = tmp_path / 'a1_coverage.pth'; path.write_text('coverage startup')
    flag = runner.stat.UF_HIDDEN
    flags = {'value': flag if hidden else 0}
    changed = []
    original_stat = type(path).stat
    def metadata(self, *args, **kwargs):
        if self == path: return SimpleNamespace(st_flags=flags['value'])
        return original_stat(self, *args, **kwargs)
    def chflags(file, value): flags['value'] = value; changed.append(value)
    monkeypatch.setattr(type(path), 'stat', metadata)
    monkeypatch.setattr(path.__class__, 'exists', lambda self: True if self == path else original_stat(self) is not None)
    monkeypatch.setattr(runner.os, 'chflags', chflags, raising=False)
    monkeypatch.setattr(runner.sys, 'platform', 'darwin')
    monkeypatch.setattr(runner.importlib.metadata, 'distribution', lambda _: SimpleNamespace(locate_file=lambda name: path))
    try:
        with runner.visible_coverage_startup() as info:
            assert info['temporarily_unhidden'] is hidden and flags['value'] == 0
            if fail_inside: raise RuntimeError('forced failure')
    except RuntimeError:
        assert fail_inside
    assert flags['value'] == (flag if hidden else 0)
    assert changed == ([0, flag] if hidden else [])
