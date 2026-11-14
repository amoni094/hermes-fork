#!/usr/bin/env python3
"""cron-sandbox-runner.py — invoke OpenShell wrapper for Hermes cron jobs.

Usage:
  cron-sandbox-runner.py SCRIPT [ARGS...]
  cron-sandbox-runner.py --self-test
  cron-sandbox-runner.py --wrap-jobs
  cron-sandbox-runner.py --unwrap-jobs
  cron-sandbox-runner.py --smoke
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

_raw_home = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
if _raw_home.parent.name == 'profiles':
    _hermes_base = _raw_home.parent.parent
    _hermes_root = _raw_home
    if not _hermes_profile:
        _hermes_profile = _raw_home.name
else:
    _hermes_base = _raw_home
    _hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile else _hermes_base


def _profile_root() -> Path:
    env_home = os.environ.get('HERMES_HOME', '').strip()
    base = Path(env_home) if env_home else Path.home() / '.hermes'
    if base.parent.name == 'profiles':
        return base
    prof = os.environ.get('HERMES_PROFILE', 'fork').strip() or 'fork'
    return base / 'profiles' / prof


def _hermes_home() -> Path:
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def _wrapper_sh() -> Path:
    return _profile_root() / 'scripts' / 'cron-sandbox-wrapper.sh'


def _jobs_path() -> Path:
    return _profile_root() / 'cron' / 'jobs.json'


def _shim_dir() -> Path:
    return _profile_root() / 'scripts' / 'cron-sandboxed'


def _scripts_dir() -> Path:
    return _profile_root() / 'scripts'


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@contextlib.contextmanager
def _jobs_exclusive_lock(jobs_path: Path):
    """flock a sibling jobs.json.lock that is never inode-swapped."""
    lock_path = jobs_path.with_name(jobs_path.name + '.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


def _job_timeout_seconds(job: dict) -> int:
    raw = job.get('timeout_seconds')
    if raw is None or raw == '':
        return 180
    try:
        timeout_sec = int(raw)
    except (TypeError, ValueError):
        return 180
    if timeout_sec < 1:
        return 180
    return timeout_sec


def _atomic_replace_jobs(jobs_path: Path, text: str) -> None:
    """Write jobs.json.tmp then os.replace while caller holds jobs.json.lock."""
    tmp_path = jobs_path.with_name(jobs_path.name + '.tmp')
    fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as tfh:
            tfh.write(text)
            tfh.flush()
            os.fsync(tfh.fileno())
        os.replace(tmp_path, jobs_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _run_wrapper(argv: list[str], extra_env: dict | None = None) -> int:
    wrapper = _wrapper_sh()
    if not wrapper.is_file():
        print('ERROR: wrapper missing: ' + str(wrapper), file=sys.stderr)
        return 2
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run([str(wrapper), *argv], env=env, check=False)
    return int(proc.returncode)


def _extract_shim_inner(shim: Path) -> str | None:
    try:
        text = shim.read_text(encoding='utf-8')
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('exec '):
            parts = shlex.split(stripped)
            if len(parts) >= 3:
                return parts[2]
            break
    return None


def _is_shim_path(script: str, shim_dir: Path) -> bool:
    try:
        return Path(script).resolve().is_relative_to(shim_dir.resolve())
    except (OSError, ValueError):
        return False


def _resolve_job_script(script: str) -> Path | None:
    """Resolve relative job scripts against the profile scripts dir. None if not a file."""
    raw = str(script).strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = _scripts_dir() / raw
    try:
        p = p.resolve()
    except OSError:
        pass
    try:
        _allowed_scripts = _scripts_dir().resolve()
        if not p.is_relative_to(_allowed_scripts):
            print(
                f'ERROR: job script {p} is outside allowed dir {_allowed_scripts}',
                file=sys.stderr,
            )
            return None
    except Exception:
        pass
    if p.is_file():
        return p
    return None


def cmd_smoke() -> int:
    openshell = shutil.which('openshell') or str(Path.home() / '.local' / 'bin' / 'openshell')
    if not os.access(openshell, os.X_OK):
        print('SMOKE: openshell binary missing')
        return 1
    ver = subprocess.run([openshell, '--version'], capture_output=True, text=True, check=False)
    print((ver.stdout or ver.stderr or '').strip() or 'openshell --version ok')
    policy = _profile_root() / 'openshell-policy.yaml'
    cmd = [
        openshell, 'sandbox', 'create',
        '--policy', str(policy),
        '--no-keep', '--no-auto-providers', '--no-tty',
        '--', 'echo', 'openshell-smoke-ok',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = (proc.stdout or '') + (proc.stderr or '')
    print(out[-4000:])
    if proc.returncode == 0 and 'openshell-smoke-ok' in out:
        print('SMOKE: sandbox echo ok')
        return 0
    print(f'SMOKE: sandbox create rc={proc.returncode} (no host fallback)')
    return proc.returncode or 1


def cmd_self_test() -> int:
    failed = 0
    wrapper = _wrapper_sh()
    policy = _profile_root() / 'openshell-policy.yaml'
    cache = _profile_root() / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    vlog = cache / 'openshell-violations.log'
    sandbox_ok = False

    def probe(name: str, argv: list[str], env: dict, expect_rc: int | None = 0, expect_out: str | None = None, expect_log: str | None = None, forbid_out: str | None = None) -> bool:
        nonlocal failed
        merged = os.environ.copy()
        merged.update(env)
        merged['HERMES_OPENSHELL_VIOLATION_LOG'] = str(vlog)
        proc = subprocess.run([str(wrapper), *argv], env=merged, capture_output=True, text=True, check=False)
        ok = True
        if expect_rc is not None and proc.returncode != expect_rc:
            ok = False
        blob = (proc.stdout or '') + (proc.stderr or '')
        if expect_out and expect_out not in blob:
            ok = False
        if forbid_out and forbid_out in blob:
            ok = False
        logtxt = vlog.read_text(encoding='utf-8', errors='replace') if vlog.exists() else ''
        if expect_log and expect_log not in logtxt and expect_log not in blob:
            ok = False
        status = 'PASS' if ok else 'FAIL'
        print(f'{status} {name} rc={proc.returncode}')
        if not ok:
            failed += 1
            print('  stdout=', (proc.stdout or '')[-500:])
            print('  stderr=', (proc.stderr or '')[-500:])
        return ok

    # Probe 1: openshell not installed — the only allowed host fallback
    echo = shutil.which('echo') or '/usr/bin/echo'
    probe(
        'missing-openshell-fallback',
        [echo, 'fallback-ok'],
        {'OPENSHELL_BIN': '/no/such/openshell', 'HERMES_OPENSHELL_FALLBACK': '1'},
        expect_rc=0,
        expect_out='fallback-ok',
        expect_log='openshell not installed',
    )
    # Default (unset/empty) must DENY host exec when openshell is missing.
    probe(
        'missing-openshell-deny-default',
        [echo, 'deny-default-ok'],
        {'OPENSHELL_BIN': '/no/such/openshell', 'HERMES_OPENSHELL_FALLBACK': ''},
        expect_rc=1,
        forbid_out='deny-default-ok',
        expect_log='openshell not installed',
    )

    # Probe 2: policy missing — fail closed, never host-exec
    probe(
        'missing-policy-fail-closed',
        [echo, 'policy-fallback-ok'],
        {
            'OPENSHELL_BIN': str(Path.home() / '.local' / 'bin' / 'openshell'),
            'OPENSHELL_SANDBOX_POLICY': str(cache / 'no-such-policy.yaml'),
            'HERMES_OPENSHELL_FALLBACK': '1',
        },
        expect_rc=2,
        expect_log='policy file missing',
        forbid_out='policy-fallback-ok',
    )

    # Probe 3: script path does not exist
    probe(
        'missing-script',
        [str(cache / 'no-such-cron-script.py')],
        {'HERMES_OPENSHELL_FALLBACK': '0'},
        expect_rc=2,
        expect_log='script path does not exist',
    )

    # Probe 4: FALLBACK=0 must run real host python3 inside the sandbox
    scratch = cache / 'scratch'
    scratch.mkdir(parents=True, exist_ok=True)
    probe_py = scratch / 'openshell-selftest-probe.py'
    probe_py.write_text(
        'import os, pathlib, sys\n'
        'prof = os.environ.get("HERMES_PROFILE", "")\n'
        'if not prof:\n'
        '    print("ERROR: HERMES_PROFILE empty", file=sys.stderr)\n'
        '    sys.exit(1)\n'
        'home = os.environ.get("HERMES_HOME", "")\n'
        'hp = pathlib.Path(home)\n'
        'if hp.parent.name == "profiles":\n'
        '    wrapper = hp / "scripts" / "cron-sandbox-wrapper.sh"\n'
        'else:\n'
        '    wrapper = hp / "profiles" / prof / "scripts" / "cron-sandbox-wrapper.sh"\n'
        'if not wrapper.is_file():\n'
        '    print("ERROR: cannot read", wrapper, file=sys.stderr)\n'
        '    sys.exit(1)\n'
        'print("sandbox-exec-ok")\n',
        encoding='utf-8',
    )
    sandbox_ok = probe(
        'sandbox-execution',
        [str(probe_py)],
        {'HERMES_OPENSHELL_FALLBACK': '0', 'HERMES_OPENSHELL_TIMEOUT': '60'},
        expect_rc=0,
        expect_out='sandbox-exec-ok',
        forbid_out='FALLBACK: running on host',
    )
    if not sandbox_ok:
        print(
            'ERROR: OpenShell sandbox did not succeed with HERMES_OPENSHELL_FALLBACK=0. '
            'Self-test refuses to pass via host fallback. Check the container image, '
            'gateway provisioning, and policy — then re-run --self-test.',
            file=sys.stderr,
        )

    print(f'self-test failed={failed} policy={policy.is_file()} wrapper={wrapper.is_file()} sandbox_ok={sandbox_ok}')
    return 1 if failed else 0


def _load_jobs_locked(fh):
    fh.seek(0)
    raw = fh.read()
    data = json.loads(raw) if raw.strip() else {}
    if isinstance(data, list):
        jobs = data
        envelope = None
    elif isinstance(data, dict) and isinstance(data.get('jobs'), list):
        jobs = data['jobs']
        envelope = data
    else:
        raise SystemExit('jobs.json has unexpected shape')
    return jobs, envelope


def cmd_wrap_jobs() -> int:
    jobs_path = _jobs_path()
    shim_dir = _shim_dir()
    wrapper = _wrapper_sh()
    shim_dir.mkdir(parents=True, exist_ok=True)
    jobs_path.parent.mkdir(parents=True, exist_ok=True)
    refused = 0
    with _jobs_exclusive_lock(jobs_path):
        with open(jobs_path, 'r', encoding='utf-8') as fh:
            jobs, envelope = _load_jobs_locked(fh)
        changed = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            script = str(job.get('script') or '').strip()
            if not script:
                continue
            jid = str(job.get('id') or Path(script).stem)
            if Path(script).name == 'cron-sandbox-wrapper.sh':
                continue
            inner_spec = script
            if _is_shim_path(script, shim_dir):
                extracted = _extract_shim_inner(Path(script))
                if extracted:
                    inner_spec = extracted
            if Path(inner_spec).name == 'cron-sandbox-wrapper.sh':
                continue
            resolved = _resolve_job_script(inner_spec)
            if resolved is None:
                print(
                    f'ERROR: refuse to wrap job {jid}: resolved path is not a file: {inner_spec}',
                    file=sys.stderr,
                )
                refused += 1
                continue
            safe = ''.join(ch if ch.isalnum() or ch in '-_.' else '_' for ch in jid)
            shim = shim_dir / (safe + '.sh')
            timeout_sec = _job_timeout_seconds(job)
            body = (
                '#!/usr/bin/env bash' + '\n'
                'export HERMES_OPENSHELL_TIMEOUT=%s\n'
                'exec %s %s "$@"\n'
            ) % (
                timeout_sec,
                shlex.quote(str(wrapper)),
                shlex.quote(str(resolved)),
            )
            _atomic_write(shim, body)
            os.chmod(shim, os.stat(shim).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            job['script'] = str(shim)
            changed += 1
        payload = envelope if envelope is not None else jobs
        if envelope is not None:
            envelope['jobs'] = jobs
            payload = envelope
        text = json.dumps(payload, indent=2) + '\n'
        _atomic_replace_jobs(jobs_path, text)
    print(f'wrapped {changed} jobs -> {shim_dir} (refused={refused})')
    return 1 if refused else 0


def cmd_unwrap_jobs() -> int:
    jobs_path = _jobs_path()
    shim_dir = _shim_dir()
    with _jobs_exclusive_lock(jobs_path):
        with open(jobs_path, 'r', encoding='utf-8') as fh:
            jobs, envelope = _load_jobs_locked(fh)
        changed = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            script = str(job.get('script') or '')
            if not script.startswith(str(shim_dir)):
                continue
            inner = _extract_shim_inner(Path(script))
            if inner:
                job['script'] = inner
                changed += 1
        payload = envelope if envelope is not None else jobs
        if envelope is not None:
            envelope['jobs'] = jobs
            payload = envelope
        text = json.dumps(payload, indent=2) + '\n'
        _atomic_replace_jobs(jobs_path, text)
    print(f'unwrapped {changed} jobs')
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['--self-test']:
        return cmd_self_test()
    if argv[:1] == ['--wrap-jobs']:
        return cmd_wrap_jobs()
    if argv[:1] == ['--unwrap-jobs']:
        return cmd_unwrap_jobs()
    if argv[:1] == ['--smoke']:
        return cmd_smoke()
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0 if argv else 2
    return _run_wrapper(argv)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
