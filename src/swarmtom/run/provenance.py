"""Immutable run identity: reject legacy checkpoints and changed scientific inputs on resume."""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import asdict
from pathlib import Path

import yaml


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def identity(cfg, kind: str) -> dict:
    root = cfg.repo_root
    files = {str(p.relative_to(root)): digest(p)
             for folder in ('src', 'scripts') for p in sorted((root / folder).rglob('*'))
             if p.is_file() and p.suffix in ('.py', '.sh')}
    if kind == 'dose':
        files.update({str(p.relative_to(root)): digest(p)
                      for p in sorted((root / 'assets/manipulation_checks').glob('*.jsonl'))})
    lesions = None
    if cfg.lesions_config:
        spec = yaml.safe_load(cfg.lesions_config.read_text())
        lesions = {'definition': spec,
                   'files': {key: digest((root / value['path']).resolve())
                             for key, value in spec['vector_files'].items()}}
    return {'schema_version': 1, 'kind': kind,
            'config': json.loads(json.dumps(asdict(cfg), default=str)),
            'source_sha256': files, 'lesions': lesions}


def git_snapshot(root: Path) -> dict:
    def git(*args):
        import shutil
        if shutil.which("git") is None:
            return None
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    return {'commit': git('rev-parse', 'HEAD'), 'dirty': bool(git('status', '--porcelain', '--untracked-files=no'))}


def ensure_manifest(cfg, kind='game') -> dict:
    directory = cfg.run_dir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'manifest.json'
    current = identity(cfg, kind)
    # Multiple seed shards may initialise the same run concurrently.
    with (directory / '.manifest.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            saved = json.loads(path.read_text())
            if saved['identity'] != current:
                raise ValueError('Run inputs changed (code/config/lesions/tasks). Use a fresh run_id; do not mix checkpoints.')
            return saved
        old_games = any((directory / 'games').glob('*/state.json'))
        generations = directory / 'generations.jsonl'
        if old_games or (generations.exists() and generations.stat().st_size):
            raise ValueError('Legacy outputs have no immutable manifest. Use a fresh run_id after the cache fix.')
        saved = {'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                 'git': git_snapshot(cfg.repo_root), 'identity': current}
        temporary = directory / f'.manifest-{uuid.uuid4().hex}.tmp'
        temporary.write_text(json.dumps(saved, indent=2))
        os.replace(temporary, path)
        return saved


def record_session(directory: Path, meta: dict) -> None:
    """Keep every restart's metadata instead of overwriting the evidence of earlier sessions."""
    sessions = directory / 'sessions'
    sessions.mkdir(exist_ok=True)
    (sessions / f'{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex}.json').write_text(
        json.dumps(meta, indent=2, default=str))


def runtime_versions() -> dict:
    import importlib.metadata
    import platform
    versions = {'python': platform.python_version()}
    for package in ('torch', 'transformers', 'vllm', 'numpy', 'pandas', 'openpyxl', 'python-docx'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def ensure_runtime(directory: Path, backend: dict, tool_runtime: dict | None = None) -> None:
    value = {'backend': backend, 'packages': runtime_versions(), 'python_tool': tool_runtime}
    path = directory / 'runtime.json'
    with (directory / '.runtime.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            if json.loads(path.read_text()) != value:
                raise ValueError('Backend/runtime changed on resume. Use the original environment or a fresh run_id.')
        else:
            temporary = directory / f'.runtime-{uuid.uuid4().hex}.tmp'
            temporary.write_text(json.dumps(value, indent=2))
            os.replace(temporary, path)
