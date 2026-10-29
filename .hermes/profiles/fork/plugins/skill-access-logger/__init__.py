"""skill-access-logger -- post_tool_call shadow plugin for Hermes fork.

Logs skill_view calls to cache/skill-access.log (JSONL) for ripple-mem-graph
co-occurrence graph construction.

H-I7: shadow annotation path, never raises. H-I6: stdlib only.
Fail-open on all errors.
"""
from __future__ import annotations
import json, logging, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger('skill-access-logger')
MAX_LOG_BYTES = 102400


def _log_path() -> Path:
    base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    profile = os.environ.get('HERMES_PROFILE', '')
    if profile:
        return base / 'profiles' / profile / 'cache' / 'skill-access.log'
    return base / 'cache' / 'skill-access.log'


def post_tool_call(tool_name: str, tool_args: dict, tool_result: Any,
                   context: dict, **kwargs: Any) -> None:
    """Shadow log skill_view calls. Never raises."""
    try:
        if tool_name != 'skill_view':
            return
        skill_name = None
        if isinstance(tool_args, dict):
            skill_name = (
                tool_args.get('name') or tool_args.get('skill_name') or ''
            ).strip()
        if not skill_name:
            return
        log_path = _log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Rotate if too large
        try:
            if log_path.exists() and log_path.stat().st_size > MAX_LOG_BYTES:
                rotated = log_path.with_suffix('.log.1')
                os.replace(str(log_path), str(rotated))
        except Exception:
            pass
        session_id = str(
            context.get('session_id') or kwargs.get('session_id') or ''
        )[:36]
        entry = json.dumps({
            'ts': datetime.now(timezone.utc).isoformat(),
            'skill': skill_name,
            'session': session_id,
        })
        with open(str(log_path), 'a') as f:
            f.write(entry + '\n')
    except Exception as exc:
        logger.debug('skill-access-logger: %s', exc)
