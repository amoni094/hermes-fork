#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path('/var/home/rainbow/.hermes')
LOG = HOME / 'logs' / 'hermes-memory-capture.jsonl'
LOG.parent.mkdir(parents=True, exist_ok=True)

payload = json.load(sys.stdin)
extra = payload.get('extra') or {}
user_message = (extra.get('user_message') or '').strip()
assistant_response = (extra.get('assistant_response') or '').strip()
# ClawSentry traceability (sweep 22): capture which tools fired this turn for audit trail.
# tool_calls is a list of tool names; empty list means no tools fired (pure text turn).
tool_calls = extra.get('tool_calls') or []
if isinstance(tool_calls, list):
    tool_names = [t.get('name', '') if isinstance(t, dict) else str(t) for t in tool_calls]
else:
    tool_names = []
text = f"{user_message}\n{assistant_response}".lower()

keywords = re.compile(r"\b(config|configured|rename|renamed|update|updated|verify|verified|fix|fixed|hook|cron|obsidian|vault|memory|bridge|ledger|skill|workflow|policy|scorecard)\b")
meaningful = len(user_message) + len(assistant_response) >= 160 or bool(keywords.search(text))

if meaningful and assistant_response:
    entry = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'session_id': payload.get('session_id'),
        'task_id': extra.get('task_id'),
        'platform': extra.get('platform'),
        'model': extra.get('model'),
        'tool_calls': [n for n in tool_names if n],  # tools fired this turn
        'user_message': user_message[:800],
        'assistant_response': assistant_response[:2000],
    }
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

sys.stdout.write('{}\n')
