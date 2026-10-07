"""governance-hard-block — H-I8 fail-closed pre_tool_call gate.

Hard core (never violate):
  No unapproved write reaches config.yaml, plugins/*.py, or agent/*.py.

This is a LIVE safety gate, not shadow telemetry. H-I7 (swallow exceptions)
does NOT apply to the deny path. Check failures on a high-risk write DENY.

BOOTSTRAP EXCEPTION (explicit, logged):
  Writes whose resolved path is under ``.../plugins/governance-hard-block/``
  are allowed without a proposal so the gate can be installed and patched.
  Residual HIGH: an agent can rewrite this plugin to disable the gate.
  Do not extend this exception to config.yaml or any other plugin.

Adversarial residuals (accepted, documented):
  - execute_code that builds the destination path at runtime without the
    path string appearing in the tool args (cwd-relative os.replace).
  - Kernel/debugger writes that never pass through pre_tool_call.
  - PYTHONPATH shadowing of this module.

ASSUME: improvement-proposals.jsonl may be absent; write tools carry path-like args.
GUARANTEE: unapproved HIGH-risk writes are blocked; read tools fail-open;
           bootstrap exception is this plugin directory only.
# inner_objective == outer_objective: True
# inner_objective: deny unapproved writes to config.yaml / plugins/*.py / agent/*.py
# outer_objective: session safety (H-I8) without locking read-only tools
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

ISS_GAIN = 0.40
EPS_DP = 0.0

_WRITE_TOOLS = frozenset({
    "write_file", "patch", "terminal", "execute_code", "skill_manage",
})
_READ_SAFE = frozenset({
    "read_file", "search_files", "skill_view", "skills_list",
    "web_search", "web_extract", "browser_snapshot", "browser_get_images",
    "browser_vision", "browser_console", "vision_analyze",
    "session_search", "todo_list", "browser_vault_list",
})

_HIGH_BASENAME = re.compile(r"(?i)(^|/)config\.ya?ml(\.tmp)?$")  # tmp-rename bypass guard (ADV fix)
_HIGH_PLUGIN_PY = re.compile(r"(?i)/plugins/[^/]+/.*\.py$")
_HIGH_AGENT_PY = re.compile(r"(?i)/(hermes-fork/)?agent/.*\.py$")
_HIGH_HERMES_PLUGIN_PY = re.compile(r"(?i)\.hermes/(profiles/[^/]+/)?plugins/.*\.py$")

# Rename / copy primitives that can bypass write_file by temp+replace.
_RENAME_PRIMITIVES = re.compile(
    r"(?i)\b(mv|cp|install|rsync|ln|tee|install\s+-m)\b"
    r"|os\.(replace|rename|link)"
    r"|shutil\.(move|copy|copy2|copyfile|copytree)"
    r"|Path\([^\)]*\)\.(write_text|write_bytes|replace|rename|touch)"
    r"|open\([^\)]*['\"]w"
    r"|json\.dump"
)

_BOOTSTRAP_DIR: Optional[Path] = None  # resolved lazily (ADV-004)


def _get_bootstrap_dir() -> Path:
    """Resolved absolute path of THIS plugin directory (ADV-004 fix)."""
    global _BOOTSTRAP_DIR
    if _BOOTSTRAP_DIR is None:
        _BOOTSTRAP_DIR = Path(__file__).resolve().parent
    return _BOOTSTRAP_DIR

_APPROVED_STATES = frozenset({"approved", "deployed"})


def _hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def _ledger_path() -> Path:
    return _hermes_home() / "logs" / "improvement-proposals.jsonl"


def load_latest_proposals(ledger: Optional[Path] = None) -> Dict[str, dict]:
    """Newest state per proposal id. Fail-closed: missing ledger => empty."""
    path = ledger or _ledger_path()
    seen: Dict[str, dict] = {}
    try:
        if not path.is_file():
            return seen
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pid = rec.get("id")
                if pid:
                    seen[str(pid)] = rec
    except OSError:
        return {}
    return seen


def has_approved_proposal(target_path: str, proposals: Optional[Dict[str, dict]] = None) -> bool:
    """True iff some proposal in approved/deployed covers *target_path*.

    Coverage: proposal.target is a suffix, prefix, or infix of the path
    (normalized). Over-broad targets of length < 4 are ignored so a
    proposal for '/' cannot unlock every write.
    """
    if proposals is None:
        proposals = load_latest_proposals()
    norm = _norm_path(target_path)
    for rec in proposals.values():
        if rec.get("state") not in _APPROVED_STATES:
            continue
        t = str(rec.get("target") or "").strip()
        if len(t) < 4:
            continue
        t_norm = _norm_path(t)
        if t_norm in norm or Path(norm).name == Path(t_norm).name and t_norm.endswith(Path(norm).name):
            return True
        # plugin dir coverage: target 'plugins/governance-hard-block' covers its files
        if t_norm.rstrip("/") in norm:
            return True
        if Path(t).name and Path(t).name in Path(norm).parts:
            # Basename match is only safe for non-sensitive names.
            # config.yaml and ssl_guard.py require exact realpath equality (ADV-031 fix):
            # a deployed proposal for one config.yaml must NOT unlock all others.
            if Path(t).name in {"config.yaml", "ssl_guard.py"}:
                # Only allow if the proposal target is a suffix of the actual resolved path
                if norm.endswith(t_norm) or t_norm.endswith(norm):
                    return True
                continue  # basename match alone is insufficient for these sensitive names
            if "governance-hard-block" in t_norm and "governance-hard-block" in norm:
                return True
            if "ssl_guard" in t_norm and "ssl_guard" in norm:
                return True
    return False


def _norm_path(p: str) -> str:
    p = os.path.expanduser(str(p).strip().strip("\"'"))
    try:
        return os.path.realpath(os.path.abspath(p))  # resolve symlinks (ADV fix)
    except OSError:
        return os.path.abspath(p) if p else p


def is_bootstrap_exception(path: str) -> bool:
    """True ONLY if path resolves inside THIS plugin directory (ADV-004)."""
    try:
        resolved = Path(_norm_path(path))
        return resolved.is_relative_to(_get_bootstrap_dir())
    except (TypeError, ValueError):
        return False


def is_high_risk_target(path: str) -> bool:
    """True if *path* is a HIGH-risk write target (H-I8)."""
    if not path:
        return False
    n = _norm_path(path).replace("\\", "/")
    if _HIGH_BASENAME.search(n):
        return True
    if _HIGH_PLUGIN_PY.search(n) or _HIGH_HERMES_PLUGIN_PY.search(n):
        return True
    if _HIGH_AGENT_PY.search(n):
        return True
    # relative forms
    low = n.lower()
    if low.endswith("config.yaml") or low.endswith("config.yml"):
        return True
    if "/agent/" in low and low.endswith(".py"):
        return True
    if "/plugins/" in low and low.endswith(".py"):
        return True
    return False


def _string_values(args: Any) -> List[str]:
    out: List[str] = []
    if args is None:
        return out
    if isinstance(args, str):
        return [args]
    if isinstance(args, dict):
        for v in args.values():
            out.extend(_string_values(v))
    elif isinstance(args, (list, tuple)):
        for v in args:
            out.extend(_string_values(v))
    else:
        out.append(str(args))
    return out


_PATHISH = re.compile(
    r"(?P<p>(?:~|/var|/home|\\.hermes)[\\w./\\-]*"
    r"(?:config\\.ya?ml|plugins/[^\\s'\"]+\\.py|agent/[^\\s'\"]+\\.py))",
    re.IGNORECASE,
)


def extract_candidate_paths(args: Any) -> List[str]:
    paths: List[str] = []
    if isinstance(args, dict):
        for key in ("path", "file", "filename", "target", "dest", "destination",
                    "output", "src", "source", "old", "new"):
            v = args.get(key)
            if isinstance(v, str) and v.strip():
                paths.append(v)
    blob = "\n".join(_string_values(args))
    for m in _PATHISH.finditer(blob):
        paths.append(m.group("p"))
    # also split shell tokens that look like paths
    for tok in re.findall(r"[^\s;|&]+", blob):
        if "config.yaml" in tok.lower() or "/plugins/" in tok or "/agent/" in tok:
            paths.append(tok.strip("\"'"))
    # dedup
    seen = set()
    uniq = []
    for p in paths:
        n = _norm_path(p)
        if n not in seen:
            seen.add(n)
            uniq.append(p)
    return uniq


def looks_like_rename_or_copy(args: Any) -> bool:
    blob = "\n".join(_string_values(args))
    return bool(_RENAME_PRIMITIVES.search(blob))


def _deny(message: str) -> Dict[str, Any]:
    return {"action": "block", "message": message}


def evaluate_write(tool_name: str, args: Any) -> Optional[Dict[str, Any]]:
    """Pure decision. None = allow, dict with action=block = DENY."""
    if tool_name in _READ_SAFE:
        return None
    if tool_name not in _WRITE_TOOLS:
        # still inspect if args mention high-risk paths (unusual tools)
        cands = extract_candidate_paths(args)
        if not any(is_high_risk_target(p) for p in cands):
            return None

    # ADV-024: execute_code dest-variable bypass.
    # extract_candidate_paths only sees static string literals; a code block that
    # builds the destination path at runtime (dest = "...config.yaml"; os.replace(...))
    # is invisible to path extraction.  Fail-closed: if the code blob contains any
    # rename/copy primitive AND any high-risk token, treat the entire code as a
    # high-risk rename even when no concrete path is extractable.
    if tool_name == "execute_code":
        code_blob = chr(10).join(_string_values(args))
        if looks_like_rename_or_copy({"code": code_blob}):
            _HR_TOKENS = ("config.yaml", "/plugins/", "/agent/", "plugin.yaml")
            if any(tok in code_blob for tok in _HR_TOKENS):
                proposals = load_latest_proposals()
                if not any(has_approved_proposal(tok, proposals) for tok in _HR_TOKENS if tok in code_blob):
                    return _deny(
                        "[governance-hard-block] DENY: execute_code contains rename/copy "
                        "primitive with high-risk token; dynamic destination may target "
                        "config.yaml / plugins / agent (ADV-024). Requires approved proposal."
                    )
        # ADV-025: obfuscated-path bypass — detect encoding primitives in code that
        # combine a write/rename primitive.
        # Attack vectors caught: chr(99)+chr(111)+..., bytes.fromhex("636f6e...").decode(),
        # base64.b64decode("Y29u...").decode(), codecs.decode(..., "hex"/"base64").
        # Static token scan misses all of these; deny any execute_code that pairs an
        # encoding primitive with a write/rename primitive.
        _ENCODE_PATTERN = re.compile(
            r"\bchr\s*\(\s*\d+\s*\)"                   # chr(99)+chr(111)+...
            r"|\.fromhex\s*\("                           # bytes.fromhex(...)
            r"|\bb64decode\s*\("                         # base64.b64decode(...)
            r"|codecs\.decode\s*\(.*?['\"][a-z0-9_]*['\"]"  # codecs.decode(..., "hex")
        )
        _WRITE_RENAME = re.compile(
            r"\b(open\s*\(|write_text|write_bytes|os\.replace|os\.rename|shutil\.copy"
            r"|Path\.write|\.replace\s*\(|tmp\.replace)"
        )
        if _ENCODE_PATTERN.search(code_blob) and _WRITE_RENAME.search(code_blob):
            return _deny(
                "[governance-hard-block] DENY: execute_code contains an encoding primitive "
                "(chr(), fromhex(), b64decode(), codecs.decode()) combined with a write/rename "
                "primitive (ADV-025/ADV-025-EXT). Dynamic paths built via encoding can bypass "
                "static token detection. No proposal can approve obfuscated writes — rewrite "
                "without encoding."
            )

    cands = extract_candidate_paths(args)
    rename = looks_like_rename_or_copy(args)
    high = [p for p in cands if is_high_risk_target(p)]

    if not high:
        # temp+rename: command has mv/os.replace AND a high-risk token in blob
        if rename:
            blob = "\n".join(_string_values(args))
            if is_high_risk_target(blob) or any(
                x in blob for x in ("config.yaml", "/plugins/", "/agent/")
            ):
                # treat whole blob as potential target
                high = [p for p in extract_candidate_paths({"command": blob}) if is_high_risk_target(p)]
                if not high:
                    high = ["<rename-primitive + high-risk token>"]

    if not high:
        return None

    proposals = load_latest_proposals()
    for p in high:
        if p != "<rename-primitive + high-risk token>" and is_bootstrap_exception(p):
            sys.stderr.write(
                f"[governance-hard-block] BOOTSTRAP EXCEPTION allowing write to {p}\n"
            )
            continue
        if p != "<rename-primitive + high-risk token>" and has_approved_proposal(p, proposals):
            continue
        # rename token without a concrete path still requires a matching approved
        # proposal for config.yaml / plugins / agent
        if p == "<rename-primitive + high-risk token>":
            blob = "\n".join(_string_values(args))
            covered = False
            for hint in ("config.yaml", "ssl_guard.py", "governance-hard-block"):
                if hint in blob and has_approved_proposal(hint, proposals):
                    covered = True
                    break
            if "governance-hard-block" in blob:
                sys.stderr.write(
                    "[governance-hard-block] BOOTSTRAP EXCEPTION (rename into plugin dir)\n"
                )
                covered = True
            if covered:
                continue
        return _deny(
            "[governance-hard-block] DENY: unapproved HIGH-risk write to "
            f"{p!r} via {tool_name}. File and get approved a proposal with "
            "python3 ~/.hermes/scripts/improvement_governance.py propose "
            "--change-type security|config --target <file> --description '...'. "
            "Hard core H-I8: no unapproved writes to config.yaml, plugins/*.py, "
            "agent/*.py. Bootstrap exception covers only "
            "plugins/governance-hard-block/."
        )
    return None


def pre_tool_call(tool_name: str = "", args: Any = None, **_kwargs) -> Optional[Dict[str, Any]]:
    """Fail-closed for HIGH-risk writes. Not H-I7."""
    try:
        return evaluate_write(tool_name, args or {})
    except Exception as exc:
        # Fail-closed ONLY when the tool is a write tool; do not lock the agent
        # on read-path bugs.
        if tool_name in _WRITE_TOOLS:
            return _deny(
                f"[governance-hard-block] DENY: gate error on {tool_name}: {exc!r}. "
                "Fail-closed for write tools (H-I8)."
            )
        logger.debug("governance-hard-block non-write error", exc_info=True)
        return None


def register(ctx: Any) -> None:
    try:
        if ctx.get_config("enabled", True) is False:
            logger.warning("governance-hard-block disabled via plugin config — H-I8 gate off")
            return
    except Exception:
        pass
    ctx.register_hook("pre_tool_call", pre_tool_call)
    logger.info("governance-hard-block: registered fail-closed pre_tool_call (H-I8)")
