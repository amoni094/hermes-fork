#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_HOME = Path('/var/home/rainbow/.hermes')
VAULT = Path('/var/home/rainbow/Documents/SecondBrain').resolve()
LOG = HERMES_HOME / 'logs' / 'hermes-obsidian-file-events.jsonl'
STATE = HERMES_HOME / 'state' / 'obsidian-dirty-paths.json'
LOG.parent.mkdir(parents=True, exist_ok=True)
STATE.parent.mkdir(parents=True, exist_ok=True)

payload = json.load(sys.stdin)
tool_name = payload.get('tool_name')
tool_input = payload.get('tool_input') or {}
path_str = tool_input.get('path')

if path_str:
    path = Path(path_str).expanduser()
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    if resolved.suffix.lower() == '.md' and VAULT in resolved.parents:
        ts = datetime.now(timezone.utc).isoformat()
        entry = {
            'ts': ts,
            'tool_name': tool_name,
            'path': str(resolved),
            'session_id': payload.get('session_id'),
            'task_id': (payload.get('extra') or {}).get('task_id'),
        }
        with LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        state = {}
        if STATE.exists():
            try:
                state = json.loads(STATE.read_text(encoding='utf-8'))
            except Exception:
                state = {}
        state[str(resolved)] = {'ts': ts, 'tool_name': tool_name}
        STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

sys.stdout.write('{}\n')
