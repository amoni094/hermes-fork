#!/usr/bin/env python3
"""anytime_checkpoint: Anytime algorithm semantics for hermes-fork cron jobs.

Based on Dean & Boddy (1988) anytime planning. Provides partial-result
checkpointing so long-running jobs survive timeout without losing progress.

Usage:
    from anytime_checkpoint import Checkpoint
    with Checkpoint('job-name') as chk:
        for item in all_items[chk.start_index:]:
            process(item)
            chk.save(item)  # checkpoint after each item
"""
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
import re


_SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9._-]+$')


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checkpoint_dir() -> Path:
    base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    profile = os.environ.get('HERMES_PROFILE', '')
    if profile and 'profiles' not in str(base):
        base = base / 'profiles' / profile
    return base / 'cache' / 'scratch' / 'checkpoints'


class Checkpoint:
    """Context manager providing anytime semantics for long-running cron jobs."""

    def __init__(self, job_name: str, checkpoint_dir: Optional[Path] = None):
        if not _SAFE_NAME_RE.match(job_name):
            raise ValueError(f"job_name must match [A-Za-z0-9._-]+, got: {job_name!r}")
        self.job_name = job_name
        self.checkpoint_dir = checkpoint_dir or _checkpoint_dir()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.checkpoint_dir / f'{job_name}.json'
        self._completed: List[Any] = []
        self._saved_count = 0  # items saved THIS run (not from prior partial)
        self.start_index = 0
        self._started_at = _utcnow()
        self._interrupted = False
        self._orig_sigterm = None

    def _load(self) -> None:
        if self._path.exists():
            try:
                rec = json.loads(self._path.read_text())
                if rec.get('status') == 'partial':
                    self._completed = rec.get('completed', [])
                    self.start_index = rec.get('start_index', len(self._completed))
                    print(f'[checkpoint] Resuming {self.job_name} from index {self.start_index} '
                          f'({len(self._completed)} items done)')
                    return
            except Exception as e:
                print(f'[checkpoint] Failed to load checkpoint: {e}', file=sys.stderr)
        self.start_index = 0

    def _write(self, status: str) -> None:
        rec = {
            'job_name': self.job_name,
            'completed': self._completed,
            'start_index': len(self._completed),
            'started_at': self._started_at,
            'updated_at': _utcnow(),
            'status': status,
            'item_count': len(self._completed),
        }
        tmp = self._path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(rec, indent=2, default=str))
        os.replace(str(tmp), str(self._path))

    def save(self, item: Any) -> None:
        """Save a completed item to the checkpoint (call after each processed item)."""
        self._completed.append(item)
        self._saved_count += 1
        self._write('partial')

    def _handle_signal(self, signum, frame) -> None:
        """SIGTERM handler: save partial, restore original handler, re-raise signal.

        Finding 7 fix: chain original handler so nested Checkpoint+ClaimHeartbeat works.
        SIGTERM propagates to the outer context manager's handler after we save.
        """
        print(f'[checkpoint] {self.job_name} interrupted by signal {signum}, saving partial checkpoint',
              file=sys.stderr)
        self._interrupted = True
        try:
            self._write('partial')
        except Exception as e:
            print(f'[checkpoint] Failed to save on signal: {e}', file=sys.stderr)
        # Restore original handler and re-deliver signal (enables proper shutdown cascade)
        orig = self._orig_sigterm
        signal.signal(signal.SIGTERM, orig if orig is not None else signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    def __enter__(self) -> 'Checkpoint':
        self._load()
        self._orig_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, self._handle_signal)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._orig_sigterm is not None:
            signal.signal(signal.SIGTERM, self._orig_sigterm)
        if exc_type is None:
            # Finding 14 fix: only mark complete if something was saved this run.
            # An empty exit (no saves) doesn't retroactively complete a prior partial.
            if self._saved_count > 0 or self.start_index == 0:
                self._write('complete')
                print(f'[checkpoint] {self.job_name} complete ({len(self._completed)} items)')
            else:
                print(f'[checkpoint] {self.job_name} no new saves this run; leaving checkpoint as-is')
        elif exc_type is SystemExit and self._interrupted:
            # Signal handler already saved partial and is re-raising SystemExit via os.kill.
            # Let it propagate so the process exits with the correct signal code.
            return False
        else:
            # Finding 3 fix: do NOT swallow the exception with sys.exit(0).
            # Write partial and let the original exception propagate — cron marks it failed,
            # which is correct. Operator can inspect the checkpoint for progress info.
            print(f'[checkpoint] {self.job_name} failed ({exc_type.__name__}), '
                  f'saving {len(self._completed)} items', file=sys.stderr)
            try:
                if self._saved_count > 0:
                    self._write('partial')
            except Exception:
                pass
            return False  # propagate original exception
        return False

    @classmethod
    def clear(cls, job_name: str, checkpoint_dir: Optional[Path] = None) -> None:
        """Clear checkpoint to force fresh restart on next run."""
        d = checkpoint_dir or _checkpoint_dir()
        p = d / f'{job_name}.json'
        if p.exists():
            p.unlink()
            print(f'[checkpoint] Cleared checkpoint for {job_name}')

    @classmethod
    def status(cls, job_name: str, checkpoint_dir: Optional[Path] = None) -> Optional[dict]:
        """Return current checkpoint record or None."""
        d = checkpoint_dir or _checkpoint_dir()
        p = d / f'{job_name}.json'
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
        return None


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='anytime-checkpoint CLI')
    ap.add_argument('command', choices=['status', 'clear', 'list'])
    ap.add_argument('job_name', nargs='?')
    args = ap.parse_args()
    chk_dir = _checkpoint_dir()
    if args.command == 'list':
        for f in sorted(chk_dir.glob('*.json')):
            rec = json.loads(f.read_text())
            print(f"{f.stem}: status={rec.get('status')} items={rec.get('item_count', 0)} updated={rec.get('updated_at', '?')}")
    elif args.command == 'status' and args.job_name:
        rec = Checkpoint.status(args.job_name)
        print(json.dumps(rec, indent=2) if rec else 'No checkpoint found')
    elif args.command == 'clear' and args.job_name:
        Checkpoint.clear(args.job_name)
