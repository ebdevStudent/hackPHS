"""tools/sync_to_repo.sh on a throwaway project: what is copied, kept, mirrored and never copied."""
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'tools' / 'sync_to_repo.sh'


def write(path, text='x'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def project(tmp_path):
    if not shutil.which('rsync') or not shutil.which('git'):
        pytest.fail('rsync and git are required for the repository sync tests')
    root = tmp_path / 'project'
    (root / 'tools').mkdir(parents=True)
    shutil.copy(SCRIPT, root / 'tools' / 'sync_to_repo.sh')
    for name in ('docs/new.md', 'software/ball_demo/app.py', 'firmware/core.c', 'cad/kit/tool.py', 'evidence/report.json',
                 'tools/shared.py', 'AGENTS.md'):
        write(root / name, 'current ' + name)
    for name in ('software/runs/operator-token', 'software/.venv/lib/x.py', 'software/.venv-desktop/bin/y', 'cad/kit/.venv/z',
                 'firmware/build/out.uf2', 'evidence/raw/capture.bin', 'docs/operator-token-8080', 'software/x.egg-info/PKG-INFO',
                 'software/ball_demo/__pycache__/app.cpython-313.pyc', 'cad/apex2-cage/measurements.backup-1.json'):
        write(root / name, 'private')
    repo = root / 'simulation'
    for name in ('server.py', 'tools/autocommit.sh', 'docs/new.md', 'docs/removed.md', 'tools/shared.py'):
        write(repo / name, 'old ' + name)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'add', '-A'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-qm', 'base'], check=True)
    return root, repo


def run(root, *args):
    return subprocess.run(['bash', str(root / 'tools' / 'sync_to_repo.sh'), *args], capture_output=True, text=True, timeout=60)


def test_dry_run_changes_nothing(project):
    root, repo = project
    result = run(root)
    assert result.returncode == 0 and 'Dry run only' in result.stdout
    assert (repo / 'docs/new.md').read_text() == 'old docs/new.md' and (repo / 'docs/removed.md').exists()
    assert not (repo / 'firmware').exists()


def test_apply_copies_current_work_and_never_private_data(project):
    root, repo = project
    result = run(root, '--apply')
    assert result.returncode == 0 and 'nothing was pushed' in result.stdout
    for name in ('docs/new.md', 'software/ball_demo/app.py', 'firmware/core.c', 'cad/kit/tool.py', 'evidence/report.json', 'tools/shared.py'):
        assert (repo / name).read_text() == 'current ' + name
    assert not (repo / 'AGENTS.md').exists()                            # repository keeps its own AGENTS.md/README.md
    for name in ('software/runs', 'software/.venv', 'software/.venv-desktop', 'cad/kit/.venv', 'firmware/build', 'evidence/raw',
                 'docs/operator-token-8080', 'software/x.egg-info', 'software/ball_demo/__pycache__', 'cad/apex2-cage/measurements.backup-1.json'):
        assert not (repo / name).exists(), name
    assert not (repo / 'docs/removed.md').exists()                     # owned folders are mirrored
    assert (repo / 'server.py').read_text() == 'old server.py'          # simulator files untouched
    assert (repo / 'tools/autocommit.sh').exists()                      # simulator-only tools kept
    log = subprocess.run(['git', '-C', str(repo), 'log', '--oneline'], capture_output=True, text=True).stdout.splitlines()
    assert len(log) == 1                                                # nothing committed


def test_refuses_without_a_git_checkout(tmp_path):
    root = tmp_path / 'p'
    (root / 'tools').mkdir(parents=True)
    shutil.copy(SCRIPT, root / 'tools' / 'sync_to_repo.sh')
    (root / 'simulation').mkdir()
    result = run(root, '--apply')
    assert result.returncode == 1 and 'No git checkout' in result.stdout
