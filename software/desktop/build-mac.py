"""Run with software/.venv/bin/python; creates a self-contained Apple Silicon .app."""
import os
import sys
import stat
import subprocess
import plistlib
import tempfile
import shutil
from pathlib import Path

import PyInstaller.__main__
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
if sys.platform != 'darwin':
    raise SystemExit('Build the Mac app on macOS. Use install-desktop-pi.sh for Linux ARM64.')
os.chdir(root)
image = Image.new('RGBA', (1024, 1024))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((30, 30, 994, 994), radius=215, fill='#223033')
draw.ellipse((180, 180, 844, 844), outline='#b2ccc7', width=22)
draw.line((332, 332, 692, 692), fill='#eef5f3', width=28)
draw.line((692, 332, 332, 692), fill='#eef5f3', width=28)
for x, y in [(332, 332), (692, 332), (332, 692), (692, 692)]:
    draw.ellipse((x - 92, y - 92, x + 92, y + 92), fill='#223033', outline='#eef5f3', width=22)
draw.ellipse((460, 460, 564, 564), fill='#69b4a1')
image.save(root / 'ball_demo/static/desktop-icon.png')
image.save(root / 'desktop/BallDrone.icns')
staging = tempfile.TemporaryDirectory(prefix='ball-drone-build-', dir='/tmp')
PyInstaller.__main__.run([
    '--noconfirm', '--clean', '--onedir', '--windowed', '--name', 'Ball Drone',
    '--target-arch', 'arm64', '--osx-bundle-identifier', 'org.hackphs.ball-drone',
    '--icon', str(root / 'desktop/BallDrone.icns'),
    '--distpath', staging.name,
    '--paths', str(root), '--add-data', str(root / 'ball_demo/static') + ':ball_demo/static',
    '--hidden-import', 'uvicorn.logging', '--hidden-import', 'uvicorn.loops.asyncio',
    '--hidden-import', 'uvicorn.protocols.http.h11_impl', '--hidden-import', 'uvicorn.lifespan.on',
    '--exclude-module', 'playwright', '--exclude-module', 'pytest',
    '--exclude-module', 'tkinter', '--exclude-module', 'PySide6.QtQml',
    '--exclude-module', 'PySide6.QtQuick', '--exclude-module', 'PySide6.QtWebEngineCore',
    str(root / 'desktop/launch.py'),
])
bundle = Path(staging.name) / 'Ball Drone.app'
for file in bundle.rglob('*'):
    if not file.is_symlink():
        flags = file.stat().st_flags
        if flags & stat.UF_HIDDEN: os.chflags(file, flags & ~stat.UF_HIDDEN)
plist = bundle / 'Contents/Info.plist'
info = plistlib.loads(plist.read_bytes())
info['NSCameraUsageDescription'] = 'Ball Drone reads camera frames for visual target tracking in the demonstration.'
info['CFBundleShortVersionString'] = '0.1.0'
plist.write_bytes(plistlib.dumps(info))
# Strip copied Finder/resource metadata from our generated bundle, then ad hoc sign.
subprocess.run(['xattr', '-cr', str(bundle)], check=True)
subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(bundle)], check=True)
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
destination = Path.home() / 'Applications/Ball Drone.app'
destination.parent.mkdir(parents=True, exist_ok=True)
if destination.exists():
    existing = plistlib.loads((destination / 'Contents/Info.plist').read_bytes())
    if existing.get('CFBundleIdentifier') != 'org.hackphs.ball-drone':
        raise SystemExit('Another app already has this name; refusing to replace it.')
    shutil.rmtree(destination)
shutil.copytree(bundle, destination, symlinks=True, copy_function=shutil.copy)
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(destination)], check=True)
staging.cleanup()
print(destination)
