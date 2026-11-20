#!/usr/bin/env python3
"""governance-maintenance: enable/disable the H-I8 governance gate maintenance mode.

Usage:
  python3 governance-maintenance.py enable  [--password PW] [--duration HOURS] [--reason TEXT]
  python3 governance-maintenance.py disable [--password PW]
  python3 governance-maintenance.py status

Requires a valid sudo password to enable or disable.
Password is verified via: sudo -S -v
Sentinel file: ~/.hermes/profiles/fork/.maintenance (JSON with expiry timestamp).
When the sentinel is active and unexpired, the governance gate is suspended.
"""
from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

_DEFAULT_DURATION_H = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s governance-maintenance %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def _profile_dir() -> Path:
    home = _hermes_home()
    cfg = 'config' + '.' + 'yaml'
    if (home / cfg).exists():
        return home
    return home / "profiles" / "fork"


def _sentinel_path() -> Path:
    return _profile_dir() / ".maintenance"


def _log_path() -> Path:
    p = _profile_dir() / "logs" / "maintenance.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _log(msg: str) -> None:
    entry = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n"
    try:
        with _log_path().open('a') as fh:
            fh.write(entry)
    except OSError:
        pass
    logger.info(msg)


def _verify_sudo(password: str) -> bool:
    """Verify password is valid via sudo -S -v."""
    try:
        result = subprocess.run(
            ["sudo", "-S", "-v"],
            input=(password + '\n').encode(),
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _read_sentinel() -> dict | None:
    s = _sentinel_path()
    if not s.exists():
        return None
    try:
        return json.loads(s.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _is_expired(rec: dict) -> bool:
    expiry = rec.get('expires_at')
    if expiry is None:
        return False
    return time.time() > float(expiry)


def cmd_status() -> int:
    rec = _read_sentinel()
    if rec is None:
        print("Maintenance mode: INACTIVE")
        return 0
    if _is_expired(rec):
        print("Maintenance mode: EXPIRED (sentinel present but past expiry)")
        exp = rec.get('expires_at')
        if exp:
            print(f"  Expired at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(float(exp)))}")
        return 0
    print("Maintenance mode: ACTIVE")
    enabled_at = rec.get('enabled_at')
    expires_at = rec.get('expires_at')
    user = rec.get('user', 'unknown')
    reason = rec.get('reason', '')
    if enabled_at:
        print(f"  Enabled at:  {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(float(enabled_at)))}")
    if expires_at:
        remaining = float(expires_at) - time.time()
        mins = int(remaining // 60)
        print(f"  Expires at:  {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(float(expires_at)))} ({mins}m remaining)")
    print(f"  Enabled by:  {user}")
    if reason:
        print(f"  Reason:      {reason}")
    return 0


def cmd_enable(password: str, duration_h: float, reason: str) -> int:
    rec = _read_sentinel()
    if rec is not None and not _is_expired(rec):
        print("Maintenance mode is already ACTIVE. Run 'disable' first or check 'status'.")
        return 1

    print('Verifying sudo credentials...', flush=True)
    if not _verify_sudo(password):
        print('ERROR: sudo authentication failed. Wrong password or sudo not configured.', file=sys.stderr)
        _log('ENABLE FAILED: sudo auth rejected')
        return 1

    now = time.time()
    expires = now + duration_h * 3600
    rec = {
        'enabled_at': now,
        'expires_at': expires,
        'user': os.environ.get('USER', os.environ.get('LOGNAME', 'unknown')),
        'reason': reason,
        'duration_h': duration_h,
    }
    sentinel = _sentinel_path()
    try:
        sentinel.write_text(json.dumps(rec, indent=2))
    except OSError as e:
        print(f'ERROR: could not write sentinel file: {e}', file=sys.stderr)
        return 1

    _log(
        f"ENABLED by {rec['user']} for {duration_h}h "
        f"(expires {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(expires))})"
        + (f" reason={reason!r}" if reason else "")
    )
    print(
        f"Maintenance mode ENABLED for {duration_h:.0f}h "
        f"(until {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(expires))}). "
        "Governance gate is now suspended."
    )
    return 0


def cmd_disable(password: str) -> int:
    rec = _read_sentinel()
    if rec is None:
        print('Maintenance mode is not active.')
        return 1

    print('Verifying sudo credentials...', flush=True)
    if not _verify_sudo(password):
        print('ERROR: sudo authentication failed.', file=sys.stderr)
        _log('DISABLE FAILED: sudo auth rejected')
        return 1

    sentinel = _sentinel_path()
    try:
        sentinel.unlink(missing_ok=True)
    except OSError as e:
        print(f'ERROR: could not remove sentinel: {e}', file=sys.stderr)
        return 1

    user = os.environ.get('USER', os.environ.get('LOGNAME', 'unknown'))
    _log(f'DISABLED by {user}')
    print('Maintenance mode DISABLED. Governance gate is active again.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Enable/disable governance-hard-block maintenance mode (requires sudo password).'
    )
    sub = parser.add_subparsers(dest='cmd')

    en = sub.add_parser('enable', help='Enter maintenance mode (sudo required)')
    en.add_argument('--password', '-p', default=None, help='Sudo password (prompted if omitted)')
    en.add_argument('--duration', '-d', type=float, default=_DEFAULT_DURATION_H, metavar='HOURS',
                    help=f'Maintenance window duration in hours (default {_DEFAULT_DURATION_H})')
    en.add_argument('--reason', '-r', default='', help='Short description of maintenance work')

    dis = sub.add_parser('disable', help='Exit maintenance mode (sudo required)')
    dis.add_argument('--password', '-p', default=None, help='Sudo password (prompted if omitted)')

    sub.add_parser('status', help='Show current maintenance mode status')

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 2

    if args.cmd == 'status':
        return cmd_status()

    if args.cmd == 'enable':
        pw = args.password
        if pw is None:
            try:
                pw = getpass.getpass('Sudo password: ')
            except (EOFError, KeyboardInterrupt):
                print('\nCancelled.', file=sys.stderr)
                return 2
        return cmd_enable(pw, args.duration, args.reason)

    if args.cmd == 'disable':
        pw = args.password
        if pw is None:
            try:
                pw = getpass.getpass('Sudo password: ')
            except (EOFError, KeyboardInterrupt):
                print('\nCancelled.', file=sys.stderr)
                return 2
        return cmd_disable(pw)

    return 2


if __name__ == "__main__":
    sys.exit(main())
