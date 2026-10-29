"""skill-access-logger -- post_tool_call shadow plugin for Hermes fork.

Logs skill_view calls to cache/skill-access.log (JSONL) for ripple-mem-graph
co-occurrence graph construction.

H-I7: shadow annotation path, never raises. H-I6: stdlib only.
Fail-open on all errors. Registered via register(ctx) per Hermes plugin API.

Hook kwargs for post_tool_call (from _emit_post_tool_call_hook):
  tool_name=function_name, args=function_args, result=result,
  session_id, task_id, tool_call_id, turn_id, api_request_id,
  duration_ms, status, error_type, error_message, middleware_trace
"""
from __future__ import annotations
import json, logging, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger('skill-access-logger')

ISS_GAIN = 0.0   # observer only, no perturbation
EPS_DP = 0.0     # does not read vault.db / memories/
MAX_LOG_BYTES = 102400


def _log_path() -> Path:
    base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    profile = os.environ.get('HERMES_PROFILE', '')
    # Guard: if HERMES_HOME already contains profiles/<profile>, don't double-nest
    if profile and 'profiles' not in str(base):
        return base / 'profiles' / profile / 'cache' / 'skill-access.log'
    return base / 'cache' / 'skill-access.log'


def _on_post_tool_call(
    tool_name: str = '',
    args: dict | None = None,
    result: Any = None,
    session_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Shadow log skill_view calls. Never raises. Kwargs narrowed by _hook_callback_kwargs."""
    try:
        if tool_name != 'skill_view':
            return
        skill_name = None
        if isinstance(args, dict):
            skill_name = (
                args.get('name') or args.get('skill_name') or ''
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
        entry = json.dumps({
            'ts': datetime.now(timezone.utc).isoformat(),
            'skill': skill_name,
            'session': str(session_id or '')[:36],
        })
        with open(str(log_path), 'a') as f:
            f.write(entry + '\n')
    except Exception as exc:
        logger.debug('skill-access-logger: %s', exc)


def register(ctx: Any) -> None:
    """Register with Hermes plugin context. Fail-open on registration error."""
    try:
        ctx.register_hook('post_tool_call', _on_post_tool_call)
        logger.debug('skill-access-logger: registered post_tool_call hook')
    except Exception as exc:
        logger.warning('skill-access-logger: failed to register: %s', exc)
