"""Save additional FlashPrint profiles without replacing the user's originals.

Run with software/.venv/bin/python so Qt itself verifies the INI variants.
STL scale/orientation belong to the model, not a profile. No job is sent.
"""
import hashlib
import json
import re
import struct
from pathlib import Path

from PySide6.QtCore import QSettings

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / 'cad/apex2-cage'
INSTALLED = Path.home() / '.FlashPrint-MP/slice_profile'
BASE = CAD / 'print_now/profiles/9_Voxel PETG T3 cage section.profile'


def save(name, destination):
    content = BASE.read_text()
    changes = {'firstMaxSpeed': 10., 'brimSpeed': 25., 'leftTemp': 235.}
    for key, value in changes.items():
        data = b'\0\0\0\x87' + struct.pack('>f', value)
        variant = '@Variant(' + ''.join('\\x%02x' % b for b in data) + ')'
        content, count = re.subn('^' + key + '=.*$', lambda _: key + '=' + variant,
                                content, flags=re.MULTILINE)
        assert count == 1
    content = re.sub('^profileName=.*$', lambda _: 'profileName=' + name, content, flags=re.MULTILINE)
    destination.mkdir(exist_ok=True, parents=True)
    path = destination / ('9_' + name + '.profile')
    installed = INSTALLED / path.name
    # Original profiles have different names. Preserve a prior generated copy
    # if the content changes on a later run.
    for target in (path, installed):
        if target.exists() and target.read_text() != content:
            old = hashlib.sha256(target.read_bytes()).hexdigest()[:12]
            backup = target.with_suffix('.' + old + '.previous')
            if not backup.exists():
                backup.write_bytes(target.read_bytes())
        target.write_text(content)
    expected = {'machineId': 9, 'profileName': name, 'layerHeight': .15,
                'firstHeight': .27, 'baseSpeed': 35., 'firstMaxSpeed': 10.,
                'perimeterShellCnt': 3., 'infillTopSolidCnt': 5., 'infillBottomSolidCnt': 5.,
                'infillDensity': 25., 'infillPattern': 1, 'brimEnable': True,
                'brimMargin': 5., 'brimLayerCnt': 1., 'brimSpeed': 25.,
                'travelSpeed': 100., 'rightTemp': 235., 'platTemp': 60.,
                'retractLen': 1.5, 'retractSpeed': 30., 'fanMode': 4, 'fanHeight': .6,
                'supportEnable': False, 'raftEnable': False, 'offsetEnable': False}
    settings = {}
    for target in (path, installed):
        q = QSettings(str(target), QSettings.IniFormat)
        for key, value in expected.items():
            actual = q.value(key, type=type(value))
            assert abs(actual - value) < 1e-5 if isinstance(value, float) else actual == value, (target, key, actual, value)
            settings[key] = actual
    assert path.read_bytes() == installed.read_bytes()
    return {'name': name, 'file': path.name, 'installed': str(installed),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'qt_readback': settings}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--t3-only', action='store_true')
    args = parser.parse_args()
    t3 = save('Voxel PETG T3 socket 2 FINAL', CAD / 'print_now/profiles')
    rows = [t3] if args.t3_only else []
    if not args.t3_only:
        package = CAD / 'print_ready_p1b'
        manifest = json.loads((package / 'manifest.json').read_text())
        for plate in manifest['plates']:
            rows.append(save('Voxel PETG FINAL ' + plate['name'], package / 'profiles'))
    output = CAD / ('print_now/profiles/final-profile-manifest.json' if args.t3_only
                    else 'print_ready_p1b/profiles/manifest.json')
    output.write_text(json.dumps({'profiles': rows, 'scope': 'Saved files and Qt readback; no physical job sent'}, indent=2) + '\n')
    print(json.dumps({'saved_and_qt_verified': [r['name'] for r in rows]}, indent=2))
