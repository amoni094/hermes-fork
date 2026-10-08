#!/usr/bin/env python3
"""RACS prefix-drift tracker for Hermes sessions.

Hashe stable context blocks per turn and logs prefix_drift events
when stable block hashes change unexpectedly (indicating cache-breaking mutations).

Usage: import and call track_turn(session_id, turn_num, blocks) each turn.
Blocks = dict with keys: system_prompt, skills, memories, history.
Each value is a string (content of that block).

Logs to: ~/.hermes/logs/prefix-drift.jsonl
"""
import hashlib
import json
import os
import time
import fcntl
from pathlib import Path

LOG_PATH = Path.home() / '.hermes' / 'logs' / 'prefix-drift.jsonl'
STATE_PATH = Path.home() / '.hermes' / 'cache' / 'racs-state.json'

STABILITY_ORDER = ['system_prompt', 'skills', 'memories', 'history']  # most to least stable

def _hash_block(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def load_state(session_id: str) -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text())
        return data.get(session_id, {})
    except Exception:
        return {}

def save_state(session_id: str, state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _lock_path = STATE_PATH.with_suffix(".lock")
    with open(_lock_path, "w") as _lf:
        fcntl.flock(_lf, fcntl.LOCK_EX)
        try:
            all_state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
        except Exception:
            all_state = {}
        all_state[session_id] = state
        _st_tmp = STATE_PATH.with_suffix('.tmp')
        _st_tmp.write_text(json.dumps(all_state, indent=2))
        _st_tmp.replace(STATE_PATH)

def track_turn(session_id: str, turn_num: int, blocks: dict) -> list:
    """Track a turn. Returns list of drift events (empty if no drift)."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    prev_state = load_state(session_id)
    current_hashes = {k: _hash_block(blocks.get(k, '')) for k in STABILITY_ORDER}
    
    drifts = []
    for block in STABILITY_ORDER[:3]:  # only track stable blocks (skip history)
        prev_hash = prev_state.get(block)
        curr_hash = current_hashes[block]
        if prev_hash and prev_hash != curr_hash:
            event = {
                'ts': time.time(),
                'session_id': session_id,
                'turn': turn_num,
                'block': block,
                'prev_hash': prev_hash,
                'curr_hash': curr_hash,
                'event': 'prefix_drift'
            }
            drifts.append(event)
            _log_lock = LOG_PATH.with_suffix(".lock")
            with open(_log_lock, "w") as _lf:
                fcntl.flock(_lf, fcntl.LOCK_EX)
                with open(LOG_PATH, 'a') as f:
                    f.write(json.dumps(event) + '\n')
    
    save_state(session_id, current_hashes)
    return drifts

def get_drift_report(session_id: str = None) -> dict:
    """Get drift summary from log."""
    if not LOG_PATH.exists():
        return {'total_events': 0, 'by_block': {}}
    events = []
    with open(LOG_PATH) as f:
        for line in f:
            try:
                e = json.loads(line)
                if session_id is None or e.get('session_id') == session_id:
                    events.append(e)
            except Exception:
                pass
    by_block = {}
    for e in events:
        b = e['block']
        by_block[b] = by_block.get(b, 0) + 1
    return {'total_events': len(events), 'by_block': by_block}

if __name__ == '__main__':
    import sys
    if '--report' in sys.argv:
        report = get_drift_report()
        print(json.dumps(report, indent=2))
    else:
        print('Usage: racs-prefix-tracker.py --report')
        print('Or import and call track_turn(session_id, turn_num, blocks)')
