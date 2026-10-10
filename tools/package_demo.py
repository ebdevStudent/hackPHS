"""Build a local handoff archive without credentials, runtime data or simulation Git."""
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / 'evidence/ball-drone-software-0.1.0.zip'
excluded_parts = {'__pycache__', '.venv', '.venv-desktop', 'runs', '.git', '.pytest_cache', 'raw', 'build', 'build-host', 'dist'}
files = [root / 'README.md', root / 'AGENTS.md', root / '.gitignore']
for folder in ['software', 'firmware', 'docs', 'tools', 'evidence']:
    for file in (root / folder).rglob('*'):
        if not file.is_file() or any(part in excluded_parts or part.endswith('.egg-info') for part in file.relative_to(root).parts): continue
        if file.name.startswith(('.env', 'operator-token')) or file.name in [output.name, 'handoff-sha256.txt', 'package-manifest.json']: continue
        files.append(file)
manifest = {str(file.relative_to(root)): hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(set(files))}
(root / 'evidence/package-manifest.json').write_text(json.dumps({'version': '0.1.0', 'files': manifest,
    'scope': 'Software/firmware/docs/evidence only; simulation stays in its independent Mac repository; no runtime/private tokens.'}, indent=2))
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(set(files)):
        archive.write(file, 'BallDrone-Software/' + str(file.relative_to(root)))
    archive.write(root / 'evidence/package-manifest.json', 'BallDrone-Software/evidence/package-manifest.json')
(root / 'evidence/handoff-sha256.txt').write_text(hashlib.sha256(output.read_bytes()).hexdigest() + '  ball-drone-software-0.1.0.zip\n')
print(f'{output}: {len(manifest)} files, {output.stat().st_size} bytes')
