#!/usr/bin/env python3
"""claim_heartbeat: Keep-alive for long-running hermes-fork cron jobs.

Prevents wedge failures by emitting periodic heartbeats that the scheduler
can use to distinguish a slow-but-running job from a truly wedged one.

Based on Chubby/ZooKeeper lease-renewal protocol (Burrows 2006, Hunt 2010):
- A live job emits heartbeats; absence of heartbeat signals wedge
- Heartbeat file mtime is the liveness indicator (simple and kernel-atomic)
- Scheduler checks mtime age vs 3x heartbeat interval before declaring wedge

Usage:
    from claim_heartbeat import ClaimHeartbeat
    with ClaimHeartbeat('research-pipeline-weekly', interval=300) as hb:
        do_long_running_work()
"""
import json
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import re


_SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9._-]+$')


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hb_dir() -> Path:
    base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    profile = os.environ.get('HERMES_PROFILE', '')
    if profile and 'profiles' not in str(base):
        base = base / 'profiles' / profile
    return base / 'cache' / 'scratch' / 'heartbeats'


class ClaimHeartbeat:
    """Context manager that emits periodic heartbeats for a cron job."""

    def __init__(self, job_name: str, interval: int = 300, hb_dir: Optional[Path] = None):
        if not _SAFE_NAME_RE.match(job_name):
            raise ValueError(f"job_name must match [A-Za-z0-9._-]+, got: {job_name!r}")
        self.job_name = job_name
        self.interval = interval
        self.hb_dir = hb_dir or _hb_dir()
        self.hb_dir.mkdir(parents=True, exist_ok=True)
        self._hb_path = self.hb_dir / f'{job_name}.hb'
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._beat_count = 0
        self._started_at = _utcnow()
        self._pid = os.getpid()
        self._orig_sigterm = None

    def _beat(self) -> None:
        rec = {
            'job_name': self.job_name,
            'pid': self._pid,
            'started_at': self._started_at,
            'last_beat': _utcnow(),
            'beat_count': self._beat_count,
            'interval_seconds': self.interval,
        }
        tmp = self._hb_path.with_suffix('.hb.tmp')
        try:
            tmp.write_text(json.dumps(rec, indent=2))
            os.replace(str(tmp), str(self._hb_path))
        except Exception as e:
            print(f'[heartbeat] Failed to write heartbeat: {e}', file=sys.stderr)

    def _loop(self) -> None:
        self._beat()  # initial beat on entry
        while not self._stop_event.wait(timeout=self.interval):
            self._beat_count += 1
            self._beat()

    def _handle_sigterm(self, signum, frame) -> None:
        """SIGTERM handler: stop heartbeat, clean up, then forward to original handler.

        Finding 2 fix: previous implementation swallowed SIGTERM (only called
        _stop_event.set(), leaving the process running). Now we stop+unlink, restore
        the original handler, and re-raise the signal so the process actually exits.
        """
        print(f'[heartbeat] {self.job_name} received SIGTERM, stopping heartbeat', file=sys.stderr)
        self.stop()  # unlinks .hb file, stops thread
        # Restore original handler before re-raising so we don't recurse
        orig = self._orig_sigterm
        signal.signal(signal.SIGTERM, orig if orig is not None else signal.SIG_DFL)
        # Re-deliver the signal to get the correct exit behaviour
        os.kill(os.getpid(), signum)

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name=f'hb-{self.job_name}'
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join(timeout=5)
            self._thread = None
        try:
            if self._hb_path.exists():
                self._hb_path.unlink()
        except Exception:
            pass

    def __enter__(self) -> 'ClaimHeartbeat':
        self._orig_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._orig_sigterm is not None:
            signal.signal(signal.SIGTERM, self._orig_sigterm)
        self.stop()
        return False

    @classmethod
    def is_alive(cls, job_name: str, max_age_seconds: Optional[int] = None,
                 hb_dir: Optional[Path] = None) -> bool:
        """Check if a job is emitting heartbeats. Used by scheduler to detect wedges."""
        d = hb_dir or _hb_dir()
        hb = d / f'{job_name}.hb'
        if not hb.exists():
            return False
        try:
            rec = json.loads(hb.read_text())
            interval = rec.get('interval_seconds', 300)
        except Exception:
            interval = 300
        threshold = max_age_seconds or (interval * 3)
        return (time.time() - hb.stat().st_mtime) < threshold

    @classmethod
    def list_alive(cls, hb_dir: Optional[Path] = None) -> list:
        """Return list of job names currently emitting heartbeats."""
        d = hb_dir or _hb_dir()
        if not d.exists():
            return []
        alive = []
        for f in d.glob('*.hb'):
            job_name = f.stem
            if cls.is_alive(job_name, hb_dir=d):
                try:
                    rec = json.loads(f.read_text())
                    alive.append(rec)
                except Exception:
                    alive.append({'job_name': job_name})
        return alive


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='claim-heartbeat CLI')
    ap.add_argument('command', choices=['list', 'check'])
    ap.add_argument('job_name', nargs='?')
    args = ap.parse_args()
    if args.command == 'list':
        alive = ClaimHeartbeat.list_alive()
        if alive:
            for rec in alive:
                print(f"{rec.get('job_name')}: pid={rec.get('pid')} beats={rec.get('beat_count')} last={rec.get('last_beat')}")
        else:
            print('No jobs currently alive')
    elif args.command == 'check' and args.job_name:
        is_alive = ClaimHeartbeat.is_alive(args.job_name)
        print(f"{args.job_name}: {'ALIVE' if is_alive else 'WEDGED/STOPPED'}")
