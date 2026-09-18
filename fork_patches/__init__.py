"""fork_patches — catalogue of architectural overrides made in the hermes fork.

Every direct patch to an upstream file that would normally require a PR is
documented here with: file, line, issue-id, description, and the fix approach.
This module is import-only (no runtime effect) and serves as the authoritative
record of fork-vs-upstream divergence.
"""

FORK_PATCHES = [
    # (issue_id, file, approx_line, description)
    ("F01", "agent/turn_truncation.py", 246, "user→user adjacency guard: skip nudge if last msg role==user"),
    ("F02", "hermes_cli/plugins.py", 1887, "_SESSION_AGENTS weakref registry (register/get/unregister_session_agent); agent_init.py calls register at line ~2009"),
    ("F03", "agent/context_compressor.py", 2158, "bind_session_state resets summary_target_ratio+protect_first_n"),
    ("F04", "agent/conversation_loop.py", 766, "on_session_start now passes agent= kwarg"),
    ("F05", "agent/chat_completion_helpers.py", 1643, "skip identity rewrite on Anthropic failover to preserve prefix cache"),
    ("F08", "agent/cli_session_mixin.py", 447, "on_session_finalize failures logged not silently swallowed"),
    ("F09", "agent/turn_loop_errors.py", 80, "_persist_session failure logged at ERROR"),
    ("F10", "plugins/memory/hindsight/__init__.py", 920, "prefetch result bound to session_id; stale discarded"),
    ("F11", "gateway/input_sanitizer.py", 1, "sanitize_inbound_text() strips prompt injection from event.text"),
    ("F16", "agent/context_compressor.py", 2185, "entropy estimator reset failure logs warning and creates fresh"),
    ("H3",  "plugins/user/lambda-tuner/__init__.py", 22, "DEFAULT_SCORER singleton → _session_scorers keyed dict"),
    ("M-1", "plugins/memory/hindsight/__init__.py", None, "on_memory_write dedup gate: LRU fingerprint set blocks double-write"),
    ("M-5", "agent/memory_manager.py", None, "sync_turn atomicity: enqueue failure rolls back append"),
    ("M-8", "agent/memory_manager.py", None, "shutdown idempotency: threading.Lock + _shutdown_done flag"),
    ("C-H1","hermes_cli/skin_engine.py", 422, "load_skin path traversal: Path(name).name + resolve containment"),
    ("C-H2","tools/approval_smart.py", 100, "XML injection: html.escape() on command before guardian prompt"),
    ("C-H3","hermes_cli/worktree_gc.py", 94, "_archive_untracked uses get_hermes_home() not Path.home()"),
    ("CLI-1","hermes_cli/main.py", 234, "HERMES_HOME hardcode replaced with env-aware read"),
    ("CLI-4","hermes_cli/env_loader.py", 335, "env_loader fallbacks use HERMES_HOME env var"),
    ("CLI-5","hermes_cli/main_dashboard.py", 556, "desktop-ssh token path uses get_hermes_home()"),
    ("CLI-7","cron/scheduler.py", None, "claim TTL 300→1800s; pre-launch heartbeat write closes race window"),
    ("S-1", "tools/file_tools.py", 123, "/proc blocklist: _BLOCKED_PROC_EXPLICIT + _BLOCKED_PROC_FD_PREFIX + suffix check in _is_blocked_device_path"),
    ("S-5", "tools/approval.py", 1179, "CLI non-gateway execute_code no longer unconditionally auto-approved"),
    ("N6",  "tests/agent/conftest.py", 1, "autouse HERMES_HOME fixture isolates test suite from live ~/.hermes"),
]
