"""ssl_guard — TLS trust + skill-SSL enforcement for Hermes.

This module is the missing ``agent.ssl_guard`` import target (Wave 16/18).

Hard core (never violate):
  - Certificate verification is NOT disabled by this module.
  - ``resolve_httpx_verify()`` default is the platform trust store, never False.
  - Skill SSL validation is a linter of SKILL.md frontmatter; it does not
    and must not change TLS policy.

This is NOT a stub that returns verify=False. TLS policy lives in
``agent.ssl_verify`` and is re-exported unchanged. Spoofing this module
to weaken TLS is a security bug, not a compatibility shim.

Import path (hermes-fork layout):
    from agent.ssl_guard import resolve_httpx_verify, install_truststore, guard_skill_ssl

There is no ``hermes_fork`` Python package. ``from hermes_fork.agent import ssl_guard``
fails because the repo root is the ``agent`` package parent, not a namespace
package named hermes_fork.

delegate_task: this module is imported at agent startup via ssl_verify;
delegate_tool does not import ssl_guard directly. Providing the module
removes the ModuleNotFoundError if any plugin/validator does.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from agent.ssl_verify import (  # noqa: F401 — re-export, do not wrap to weaken
    install_truststore,
    platform_ssl_context,
    resolve_httpx_verify,
)

logger = logging.getLogger(__name__)

# Public re-exports (TLS). Callers that imported agent.ssl_guard for TLS
# get the same objects as agent.ssl_verify.
__all__ = [
    "install_truststore",
    "platform_ssl_context",
    "resolve_httpx_verify",
    "guard_skill_ssl",
    "assert_tls_not_disabled",
]

# ADV-015: identity marker — verifies correct module loaded (not hello_agent_clone/src/agent.py)
_HERMES_SSL_GUARD_MARKER: str = "hermes-fork/agent/ssl_guard v18"



def assert_tls_not_disabled(verify: Any = None) -> None:
    """Raise if a caller (or a spoofed ssl_verify) disabled verification.

    Used as a canary against ssl_guard spoofing: a replacement module that
    returns False from resolve_httpx_verify() fails this check.
    """
    if verify is None:
        verify = resolve_httpx_verify()
    if verify is False:
        raise RuntimeError(
            "ssl_guard: TLS verification is disabled. Refusing to proceed. "
            "This module must never default ssl_verify to False."
        )


def _validator_script() -> Optional[Path]:
    candidates = [
        Path.home() / ".hermes" / "scripts" / "validate-skill-ssl.py",
        Path.home() / ".hermes" / "profiles" / "fork" / "scripts" / "validate-skill-ssl.py",
        Path.home() / ".hermes" / "hermes-scripts" / "validate-skill-ssl.py",
        Path.home() / ".hermes" / "hermes-fork" / "hermes-scripts" / "validate-skill-ssl.py",
    ]
    env_home = Path(__import__("os").environ.get("HERMES_HOME", ""))
    if env_home:
        candidates.insert(0, env_home / "scripts" / "validate-skill-ssl.py")
    for p in candidates:
        if p.is_file():
            return p
    return None


def guard_skill_ssl(skill_md: str | Path, *, block_on_fail: bool = True) -> dict:
    """Run validate-skill-ssl.py on a SKILL.md path.

    Returns a dict {ok: bool, returncode: int, path: str}. Does not touch TLS.
    """
    import subprocess
    import sys

    path = Path(skill_md)
    script = _validator_script()
    if script is None:
        return {"ok": False, "returncode": 2, "path": str(path), "error": "validator missing"}
    proc = subprocess.run(
        [sys.executable, str(script), str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    ok = proc.returncode == 0
    if block_on_fail and not ok:
        logger.warning("ssl_guard skill SSL FAIL rc=%s path=%s", proc.returncode, path)
    return {
        "ok": ok,
        "returncode": proc.returncode,
        "path": str(path),
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }


# Import-time canary: loading this module must not disable TLS.
assert_tls_not_disabled.__doc__  # keep exported
try:
    _v = resolve_httpx_verify()
    if _v is False:
        raise RuntimeError("agent.ssl_verify returned False at ssl_guard import — refusing")
except Exception as _exc:  # noqa: BLE001 — import-time canary, log not raise on truststore miss
    if isinstance(_exc, RuntimeError) and "refusing" in str(_exc):
        raise
    logger.debug("ssl_guard TLS canary skipped: %s", _exc)
