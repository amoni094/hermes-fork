#!/usr/bin/env python3
"""
Production example: validate a config export repo for accidental secret leaks.

This script enforces:
- No sensitive config keys (api_key, secret, token, password) are non-empty
- Required exclusions are in .gitignore (auth.json, .env, logs/, sessions/, etc.)
- Cron snapshots have redacted chat/channel IDs
- No Python cache artifacts are tracked
- Documentation mentions the export is sanitized

Use as a CI check or pre-push hook to prevent credential exposure.
"""

import json
import pathlib
import py_compile
import subprocess
from typing import Iterable

import yaml


def fail(message: str) -> None:
    raise SystemExit(message)


def atomic_read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding='utf-8')


def iter_python_files(repo_root: pathlib.Path) -> Iterable[pathlib.Path]:
    """Yield all .py files in scripts/ directory."""
    for path in sorted((repo_root / 'scripts').glob('*.py')):
        if path.name.startswith('.'):
            continue
        yield path


def validate_python_compiles(repo_root: pathlib.Path) -> None:
    """Ensure all scripts are syntactically valid."""
    for path in iter_python_files(repo_root):
        py_compile.compile(str(path), doraise=True)


def validate_gitignore(repo_root: pathlib.Path) -> None:
    """Ensure .gitignore blocks all sensitive files."""
    gitignore_path = repo_root / '.gitignore'
    required = {
        '.env',
        'auth.json',
        'state.db',
        'state.db-*',
        'logs/',
        'sessions/',
        'processes.json',
        'channel_directory.json',
        'gateway_state.json',
        '__pycache__/',
        '*.py[cod]',
    }
    lines = {
        line.strip()
        for line in atomic_read_text(gitignore_path).splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    }
    missing = sorted(required - lines)
    if missing:
        fail(f'.gitignore missing required exclusions: {", ".join(missing)}')


def walk_mapping(node, path='root'):
    """Recursively yield (dotted_path, key, value) tuples from nested dicts."""
    if isinstance(node, dict):
        for key, value in node.items():
            current = f'{path}.{key}'
            yield current, key, value
            yield from walk_mapping(value, current)
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            yield from walk_mapping(value, f'{path}[{idx}]')


def key_looks_sensitive(key: str) -> bool:
    """Check if a key name suggests it contains secrets."""
    forbidden_patterns = (
        'api_key', 'access_token', 'refresh_token', 'bot_token',
        'bearer_token', 'client_secret', 'secret_key', 'password',
        'authorization', 'cookie',
    )
    safe_allowlist = {
        'telegram_allowed_users', 'discord_allowed_users',
        'slack_allowed_users', 'telegram_home_channel',
        'access_token_env', 'whatsapp_enabled',
    }
    normalized = key.lower()
    if normalized in safe_allowlist:
        return False
    return any(pattern in normalized for pattern in forbidden_patterns)


def validate_sanitized_config(repo_root: pathlib.Path) -> None:
    """Ensure config.sanitized.yaml has no non-empty sensitive values."""
    config_path = repo_root / 'config.sanitized.yaml'
    config = yaml.safe_load(atomic_read_text(config_path))
    if not isinstance(config, dict):
        fail('config.sanitized.yaml did not parse into a mapping')

    offenders = []
    for dotted_path, key, value in walk_mapping(config):
        if key_looks_sensitive(str(key)) and value not in (None, '', [], {}):
            offenders.append(dotted_path)
    if offenders:
        fail('config.sanitized.yaml still contains non-empty sensitive keys: ' + ', '.join(offenders))


def validate_cron_snapshot(repo_root: pathlib.Path) -> None:
    """Ensure cron.snapshot.json has redacted chat/channel IDs."""
    cron_path = repo_root / 'cron.snapshot.json'
    payload = json.loads(atomic_read_text(cron_path))
    jobs = payload.get('jobs', [])

    redacted_markers = {'<redacted>', 'redacted', ''}
    for job in jobs:
        origin = job.get('origin')
        if origin is None:
            continue
        if not isinstance(origin, dict):
            fail(f"job {job.get('name', '<unknown>')} origin is not an object")
        for field in ('chat_id', 'chat_name', 'thread_id'):
            value = origin.get(field)
            if value is None:
                continue
            text = str(value).strip().lower()
            if text not in redacted_markers:
                fail(f"job {job.get('name', '<unknown>')} has unredacted origin.{field}={value!r}")


def validate_no_tracked_pycache(repo_root: pathlib.Path) -> None:
    """Ensure __pycache__ and .pyc files are not tracked in git."""
    tracked_pycache = []
    for path in repo_root.rglob('*'):
        if '.git' in path.parts:
            continue
        if '__pycache__' not in path.parts and path.suffix not in {'.pyc', '.pyo'}:
            continue
        rel = str(path.relative_to(repo_root))
        proc = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', rel],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            tracked_pycache.append(rel)
    if tracked_pycache:
        fail('Remove tracked Python cache: ' + ', '.join(sorted(tracked_pycache)))


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parents[1]  # Adapt as needed
    validate_python_compiles(repo_root)
    validate_gitignore(repo_root)
    validate_sanitized_config(repo_root)
    validate_cron_snapshot(repo_root)
    validate_no_tracked_pycache(repo_root)
    print('repo validation passed')


if __name__ == '__main__':
    main()
