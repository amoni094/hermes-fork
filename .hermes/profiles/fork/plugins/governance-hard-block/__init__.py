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
_HIGH_PLUGIN_PY = re.compile(r"(?i)/plugins/[^/]+/.*\.py(?:\.tmp)?$")  # ADV-W14-008
_HIGH_AGENT_PY = re.compile(r"(?i)/(hermes-fork/)?agent/.*\.py(?:\.tmp)?$")  # ADV-W14-008
_HIGH_HERMES_PLUGIN_PY = re.compile(r"(?i)\.hermes/(profiles/[^/]+/)?plugins/.*\.py(?:\.tmp)?$")

# Rename / copy primitives that can bypass write_file by temp+replace.
_RENAME_PRIMITIVES = re.compile(
    # Python file-write primitives (execute_code context)
    r"os\.(replace|rename|link)"
    r"|shutil\.(move|copy|copy2|copyfile|copytree|rmtree)"  # ADV-W25-004 shutil.rmtree
    r"|Path\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,100}\)\.(write_text|write_bytes|replace|rename|touch|unlink)"
    r"|\.(write_text|write_bytes)\s*\("
    r"|\.(?:symlink_to|hardlink_to)\s*\("
    # open() write-mode: (?:[^()\n]|\([^()]*\)){0,100} — allows one level of nested parens
    # (covers os.path.join(a,b)) while stopping at ) that closes the open() call itself.
    # This fixes ADV-W8-001 (nested-paren bypass) while preserving ADV-W7-004 FP guard.
    # ADV-W8-002 note: a single \n before the path arg (open(\np,'w')) is a documented miss;
    # mitigated by the encode+open+HR_TOKEN secondary check below in evaluate_write().
    # open() write-mode: two levels of nested parens, optional leading whitespace/newline.
    # Pattern: [ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150}
    #   - [ \t\n]? absorbs single leading whitespace after open( (ADV-W9-002 partial fix)
    #   - outer alt: non-paren-non-newline char, OR (...) where ... is non-paren or single (...)
    #   = two levels of nesting (e.g. os.path.split(os.path.join(a,b))[0]) (ADV-W9-001 fix)
    #   - {0,150} cap restored from {0,100} (ADV-W9-005: 101-char ident bypass)
    #   ADV-W7-004 guard: exec(open(f).read()), chr — the ) of .read() terminates the outer alt.
    #   ADV-W8-002 residual: open(\n\np,'w') (two+ newlines before path) is a documented miss;
    #   mitigated by secondary encode+open+HR_TOKEN check in evaluate_write() for high-risk targets.
    r"|open\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150},\s*['\"][^'\"]*[wax+]"
    r"|open\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150},\s*['\"]r[bt]*\+[bt]*['\"]"
    r"|open\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150}mode\s*=\s*['\"][awx][bt+]*['\"]"
    r"|open\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150}mode\s*=\s*['\"]r[bt]*\+[bt]*['\"]"
    r"|(?:\(open\)|\[open\](?:\[\w*\])?)\s*\("  # ADV-W25-003 (open)(...) and [open][N](...) grouped/subscript
    # Path.open: unified with \s* after ( (ADV-W8-003); mode=[awx] only for keyword (ADV-W9-006 fix)
    r"|\.open\s*\(\s*(?:['\"][awx][bt+]*['\"]|['\"]r[bt]*\+[bt]*['\"]|mode\s*=\s*['\"][awx]|mode\s*=\s*['\"]r[bt]*\+|chr\s*\()"
    # open() dynamic mode: two-level nested-paren path + comma required (ADV-W7-004 guard)
    r"|open\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150},\s*chr\s*\("
    r"|open\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150}mode\s*=\s*chr\s*\("
    # Path(nested).write_text/write_bytes: two-level nested parens in Path() arg (ADV-W9-003)
    r"|Path\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,100}\)\.(write_text|write_bytes|replace|rename|touch|unlink)"
    # getattr obfuscation bypass (ADV-W9-003): getattr(obj,'write_text'/'open'/'write_bytes')
    r"|getattr\s*\(\s*(?:[a-zA-Z_][\w.]*(?:\([^)]*\))?(?:\.[a-zA-Z_]\w*(?:\([^)]*\))?)*|Path\s*\([^)]{0,200}\)|\w+\s*\([^)]*\)|\([a-zA-Z_][\w.]*(?:\([^)]*\))?\)|[a-zA-Z_][\w.]*(?:\[[^\]]*\])+(?:\.[a-zA-Z_]\w*(?:\([^)]*\))?)*|[a-zA-Z_][\w.]*\s*\([^)]*\)(?:\[[^\]]*\])+|\((?:[a-zA-Z_][\w.]*(?:\.[a-zA-Z_]\w*)*\s*\([^)]*\)(?:\[[^\]]*\])+|[a-zA-Z_][\w.]*(?:\[[^\]]*\])+)\)|\w+\s*\([^)]*\)(?:\[[^\]]*\])+|\w+\s*\([^)]*\)\[[^\]]*\])\s*,\s*(?:[bBfFrRuU]{0,2})?['\"]{1,3}(?:write_text|write_bytes|open|replace|rename|system|popen|symlink|unlink|touch|extract|extractall|unpack_archive|symlink_to|hardlink_to|copy|copy2|move|rmtree|execv|execl|execle|execlp|execvp|execvpe|link|copytree|run|check_output|check_call|execve|remove|execlpe|truncate|FileIO|link|copytree|run|check_output|check_call|execve|remove|execlpe)['\"]{1,3}"
    r"|getattr\s*\(\s*(?:object\s*=|name\s*=[bBfFrRuU]{0,2}['\"][^'\"]*(?:write_text|write_bytes|open|replace|rename|unlink|truncate|link|copytree|run|execve|remove)[^'\"]*[\'\"]{1,3})"  # ADV-W24-008 getattr keyword/object= form
    r"|getattr\s*\(\s*\*\s*[\[(]"  # ADV-W24-008 getattr star-unpack (*[list] or *(tuple))
    r"|io\.FileIO\s*\((?:[^()]|\([^)]*\)){0,200},\s*(?:['\"'][^'\"']*[wax+]|chr\s*\()"  # ADV-W24-001+004 io.FileIO positional nested+chr
    r'|io\.FileIO\s*\((?:[^()]|\([^)]*\))*\bmode\s*=\s*(?:[^)]*[wax+]|chr\s*\()'  # ADV-W24-001+004 io.FileIO mode= nested+chr
    r"|io\.FileIO\s*\([^)]*\*\*\s*(?:\{[^}]*mode[^}]*[wax+]|dict\s*\([^)]*mode\s*=)"  # ADV-W24-005 io.FileIO dict-unpack mode
    r"|io\.open\s*\([^)]{0,200},\s*['\"][awx]"  # ADV-W16-007 io.open write-mode only (W17-004)
    r"|operator\.(?:attrgetter|methodcaller)\s*\("  # ADV-W16-009 operator bypass
    r"|(?:\.extract(?:all)?|extractall|unpack_archive)\s*\("  # ADV-W17SAT-006 archive extract
    r"|fileinput\.(?:input|FileInput)\s*\((?:[^()]|\((?:[^()]|\((?:[^()]|\([^)]*\))*\))*\))*(?:inplace\s*=\s*(?!\s*(?:False|0(?![\d.])|None|'')\s*[,)#])|\*\*\s*(?:\{|(?:dict|vars|locals|globals)\s*\())"  # ADV-W17SAT-008+W22-001+003+004 fileinput keyword
    r"|fileinput\.(?:input|FileInput)\s*\((?:[^(),]|\((?:[^()]|\((?:[^()]|\([^)]*\))*\))*\))+,\s*(?!\s*(?:[a-zA-Z_]\w*\s*=|(?:False|0(?![\d.])|None|'')\s*[,)#]))"  # ADV-W22-002 fileinput positional inplace
    r"|partial\s*\(\s*(?:open|io\.open|io\.FileIO|builtins\.open|(?:pathlib\.)?Path\.(?:write_text|write_bytes|open|replace|rename|touch|symlink_to|hardlink_to|unlink))\b"  # ADV-W17SAT-010 partial(open,...)
    r"|partial\s*\(\s*(?:os\.(?:system|popen|replace|exec\w+|symlink|link|remove|unlink|truncate)|subprocess\.(?:run|call|Popen|check_output|check_call)|shutil\.(?:copy|copy2|move|copyfile|unpack_archive|copytree|rmtree))\b"  # ADV-W20-003 partial(os.system|subprocess.run|shutil.*)
    r"|\.(?:rename|touch|replace|unlink)\s*\("  # ADV-W16-002+W17-007 instance Path.rename/touch
    r"|json\.dump\b"
    r"|os\.(open|popen|system|replace)\s*\("
    r"|os\.(remove|unlink|truncate)\s*\("  # ADV-W22-006+011
    r"|os\.(symlink|symlinkat)\s*\("
    r"|subprocess\.(run|call|check_call|check_output|Popen)\s*\("
    r"|(?<![\w.])(?:system|execv|execve|execl|execle|execlp|execvp|execvpe|FileIO|truncate|remove|unlink)\s*\("  # ADV-W14-005+W24-002+003
    r"|os\.exec[vle]\w*\s*\("  # ADV-W16-003 os.execv/execve/execl*
    r"|os\.(?:spawn[levpa]*|posix_spawn)\s*\("  # ADV-W25-008 os.spawnl/spawnle/spawnv/spawnlp/posix_spawn
    r"|pty\.spawn\s*\("  # ADV-W25-008 pty.spawn write-capable
    r"|zipfile\.ZipFile\s*\([^)]*,\s*[\x27\x22]w[\x27\x22]"  # ADV-W25-009 zipfile.ZipFile write-mode
    r"|gzip\.(?:open|GzipFile)\s*\([^)]*[\x27\x22][wa][\x27\x22]"  # ADV-W25-009 gzip write-mode
    r"|urllib\.request\.urlretrieve\s*\("  # ADV-W25-009 urlretrieve
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

    ADV-031: realpath-suffix check only. No basename short-circuits.
    A proposal for /profiles/default/config.yaml must NOT unlock /profiles/fork/config.yaml.
    Coverage rule: proposal.target resolves to a suffix of the resolved write target,
    with a path-separator boundary (so 'fork/config.yaml' is not a suffix of 'default/config.yaml').

    Over-broad targets of length < 4 are ignored so '/' cannot unlock every write.
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
        # ADV-W12-007: reject relative proposal targets. A proposal with target='config.yaml'
        # (no leading /) resolves via CWD to e.g. ~/config.yaml — whichever directory the
        # process runs in. This is a ledger-pollution risk: the proposal was created with CWD
        # set to a safe directory, but evaluate_write resolves 'config.yaml' from whatever CWD
        # the tool hook runs in, approving ANY write to the CWD's config.yaml.
        # Fix: only accept proposals whose STORED target is an absolute path (starts with /).
        # Relative targets in the ledger are ignored; they must be re-proposed with full paths.
        if not t.startswith("/") and not t.startswith("~"):
            continue
        if t_norm == norm:
            return True
        # Directory coverage: proposal target is the DIRECT parent of the write target.
        # (e.g. target='plugins/governance-hard-block' covers its __init__.py).
        # Must be a DIRECT child — no additional slashes in the remainder — so that
        # a proposal for ~/.hermes does NOT unlock profiles/fork/config.yaml.
        t_stripped = t_norm.rstrip("/")
        if norm.startswith(t_stripped + "/"):
            remainder = norm[len(t_stripped) + 1:]
            if "/" not in remainder:   # direct child only
                return True
        # Suffix coverage: proposal target path is a suffix of the write target,
        # with a path-separator boundary before the match.
        # e.g. t_norm='/profiles/fork/config.yaml' matches norm='/var/home/...fork/config.yaml'
        # but t_norm='/profiles/default/config.yaml' does NOT match the fork path.
        # Note: _norm_path always returns an absolute path; relative proposals resolve via
        # realpath(abspath(t)) so they match only if they resolve to the correct absolute path.
        if norm.endswith(t_norm):
            boundary_pos = len(norm) - len(t_norm)
            if boundary_pos == 0 or norm[boundary_pos - 1] == "/":
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
    r"(?P<p>(?:~|/var|/home|\.hermes)[\w./\-]*"
    r"(?:config\.ya?ml|plugins/[^\s'\"]+\.py|agent/[^\s'\"]+\.py))",
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


# ADV-W13-005: removed 'install' (matched pip/apt-get install FP).
# ADV-W13-005: ONE optional prefix word only (sudo/time/nice/env) — not unbounded chain.
#   Consequence: 'sudo nice cp' misses (two prefixes); accepted as exotic.
# ADV-W12-002: 'ln' retained.
_SHELL_RENAME = re.compile(
    r"(?:^|[;|&\n])"           # start of command or after operator
    r"\s*(?:\w+\s+)?"          # ONE optional prefix word (sudo, time, nice, env, command)
    r"(?:/\S+/)?"              # optional absolute-path prefix (/bin/, /usr/bin/)
    r"\s*(?:mv|cp|ln|rsync|tee)\b"
)
# ADV-W14-001: tightened redirect reverted — space was over-restrictive.
# fd digits accepted (1>file, 2>>file); terminal-only gate prevents non-shell FPs.
_SHELL_REDIRECT = re.compile(r"(?:\d+)?>>?[|]?\s*(?:[./~]|[\'\"$`]|[a-zA-Z_]\w*[./])")  # ADV-W16-001+W15-004: quoted/special redirect targets; terminal-only gate

# ADV-W14-002+006+009: terminal copy-verb scan — catches prefix chains (sudo -n cp),
# wrappers (sh -c 'cp ...'), dd of=, install, and any verb depth not anchored to line start.
_COPY_VERB = re.compile(r"\b(?:mv|cp|scp|ln|rsync|tee|install|dd|patch|ed|ex)\b")
_INPLACE_EDITOR = re.compile(r"\b(?:sed|perl|awk|gawk|ruby)\b")  # ADV-W16-008 in-place editors


def looks_like_rename_or_copy(args: Any) -> bool:
    blob = "\n".join(_string_values(args))
    return bool(_RENAME_PRIMITIVES.search(blob) or _SHELL_RENAME.search(blob))


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
    # ADV-025/ADV-025-EXT/ADV-025-TERMINAL/ADV-025-OSSYSTEM/ADV-025-OBFUSCATION:
    # Encoding + write primitive bypass detection. Fires on execute_code AND terminal.
    # ENCODE: chr(x), '%c' quoted literal, fromhex, b64decode, codecs.decode, bytes([...]),
    #         eval(), exec(). (\x hex escapes and string concat are out-of-scope.)
    # WRITE (Python): reuse _RENAME_PRIMITIVES — shutil, os.replace/rename, json.dump,
    #         open(p,'w'/'a'/'x'), open(p,mode=chr(119)), subprocess, os.popen.
    # WRITE (shell, terminal only): mv/cp/install/rsync/ln/tee command verbs (anchored to shell
    #         context), shell redirects (> path or >> path, not arithmetic >1).
    # NOTE: exec(open('file').read()) does NOT fire — open(path,'r') won't match _RENAME_PRIMITIVES.
    _ENCODE_PATTERN = re.compile(
        r"\bchr\s*\("                                   # chr(99) / chr(c) / chr(0x63)
        r"|['\"]%c['\"]"                                # '%c' string literal used as format-char
        r"|[b\w]\.fromhex\s*\("                              # bytes.fromhex(...) / b.fromhex(...)
        r"|\bb64decode\s*\("                            # base64.b64decode(...)
        r"|codecs\.decode\s*\("                         # codecs.decode(...)
        r"|bytes\s*\(\s*\["                             # bytes([99, 111, ...]).decode()
        r"|\beval\s*\("                                 # eval(encoded_string)
        r"|\bexec\s*\("                                 # exec(compiled/encoded)
    )
    # Shell-specific write primitives for terminal blobs (command verbs + redirect).
    # Anchored to shell context: preceded by start-of-line, whitespace, ;, |, &.
    # Redirect: >\s*[path-starting char] — avoids arithmetic 'x > 1' or '>> count'.
    _SHELL_WRITE = re.compile(
        r"(?:^|[;|&\n])\s*(mv|cp|install|rsync|tee|ln)\b"  # shell command verbs (after shell operator)
        r"|(?:^|[\s;|&])\d*(?:&?>>?)\s*[/'\"~]"            # shell redirect: >/path, 2>/path, &>/path
        # Not \w or . — avoids 'x > 1', 'n > 0', 'x > .5' arithmetic false positives
    )
    _encode_blob = ""
    if tool_name in ("execute_code", "terminal"):
        _encode_blob = chr(10).join(_string_values(args))
    if _encode_blob and _ENCODE_PATTERN.search(_encode_blob):
        # Python write primitive (both tool types) OR shell write primitive (terminal only)
        if _RENAME_PRIMITIVES.search(_encode_blob):
            return _deny(
                "[governance-hard-block] DENY: code contains an encoding primitive "
                "(chr(), '%c', fromhex(), b64decode(), codecs.decode(), bytes([...]), eval(), exec()) "
                "combined with a write/rename primitive (ADV-025/ADV-025-EXT/ADV-025-TERMINAL/"
                "ADV-025-OSSYSTEM/ADV-025-TEE). Dynamic paths built via encoding bypass static "
                "token detection. No proposal can approve obfuscated writes — rewrite without encoding."
            )
        # Secondary fail-closed: encode + open( + high-risk token — deny even when _RENAME_PRIMITIVES
        # can't match (e.g. newline before path arg, ADV-W8-002). If someone is encoding a value
        # AND calling open() AND referencing config.yaml / plugins / agent — deny regardless.
        _HR_TOKENS_ENC = ("config.yaml", "config.yml", "/plugins/", "plugins/", "/agent/", "agent/", "plugin.yaml")
        if (tool_name == "execute_code"
                and r"open(" in _encode_blob.replace(" ", "").replace("\n", "")
                and any(tok in _encode_blob for tok in _HR_TOKENS_ENC)):
            return _deny(
                "[governance-hard-block] DENY: execute_code contains an encoding primitive "
                "combined with open() and a high-risk path token (config.yaml/plugins/agent). "
                "Fail-closed: encode+open+HR_TOKEN is always denied regardless of mode syntax "
                "(ADV-W8-002). Rewrite without encoding primitives."
            )
        if tool_name == "terminal" and _SHELL_WRITE.search(_encode_blob):
            return _deny(
                "[governance-hard-block] DENY: terminal command contains an encoding primitive "
                "combined with a shell write primitive (mv/cp/install/tee/redirect) "
                "(ADV-025-TEE-REDIRECT/ADV-025-CMD). Dynamic shell paths built via encoding "
                "bypass static token detection. No proposal can approve obfuscated writes."
            )
    if tool_name == "execute_code":
        code_blob = chr(10).join(_string_values(args))
        _HR_TOKENS = (
            "config.yaml", "config.yml",
            "/plugins/", "/agent/",           # absolute forms
            "plugin.yaml",
        )
        # ADV-W13-001: also match relative 'plugins/' and 'agent/' when NOT preceded by
        # a word char (avoids matching 'subagent/', 'user_agent/', 'myplugins/').
        _HR_REL = re.compile(r"(?<!\w)(?:plugins(?:/|\b)|agent/)")
        hr_tokens_present = [tok for tok in _HR_TOKENS if tok in code_blob]
        if not hr_tokens_present and _HR_REL.search(code_blob):
            hr_tokens_present = ["<relative-plugin-path>"]
        # ADV-W12-005: kwargs/var-mode open('plugins/evil.py', **mode) remains a documented
        # miss — we cannot safely distinguish write vs read from an arbitrary open() call without
        # parsing. has_open was removed because it caused FP on open('/plugins/x','r') reads.
        if hr_tokens_present and (
            looks_like_rename_or_copy({"code": code_blob})
            or _RENAME_PRIMITIVES.search(code_blob)
        ):
            # ADV-W10-002: do NOT call has_approved_proposal here. Obfuscated writes
            # (encode primitive + write primitive + HR token) cannot be approved via a
            # proposal — the proposal system covers known concrete paths, not dynamic
            # encode-built destinations. Fail-closed unconditionally.
            return _deny(
                "[governance-hard-block] DENY: execute_code contains rename/copy "
                "primitive with high-risk token and was already approved by ADV-025 encode "
                "gate. Dynamic destinations cannot be approved — rewrite without encoding "
                "(ADV-024/ADV-W10-002)."
            )
        # ADV-W10-003/W11-001..004: relative plugins/*.py paths covered by extended
        # _HR_TOKENS above ('plugins/' without leading /). The old _REL_HR quote-anchored
        # regex was too narrow (missed os.system shells, split/concat, unquoted paths).
        # The extended token scan + _RENAME_PRIMITIVES gate is the correct approach.
        # Also catch quoted bare 'plugins' or 'agent' as os.path.join arguments (no trailing /).
        # ADV-W12-003 fix: only fire when a HR token is ALSO present OR a join/Path context
        # is present — prevents FP on open('/tmp/x','w') with 'agent' as an unrelated variable.
        _QUOTED_REL_HR = re.compile(r"""['"](plugins|agent)['"]\s*[,)]""")
        # ADV-W13-004: removed bare Path( — too broad (print("agent") + Path("x").write_text fires FP).
        # ADV-W14-003: also catch Path("plugins")/"..." and aliased join
        _join_context = bool(
            re.search(r"(?:os\.path\.join|joinpath)", code_blob)
            or re.search(r"Path\s*\([^)]*['\"](?:plugins|agent)/", code_blob)
            or "from os.path import join" in code_blob
            or bool(re.search("['\"](?:plugins|agent)['\"]\\s*,", code_blob))  # ADV-W17-006 multi-arg Path join
        )
        if _QUOTED_REL_HR.search(code_blob) and _RENAME_PRIMITIVES.search(code_blob) and (hr_tokens_present or _join_context):
            return _deny(
                "[governance-hard-block] DENY: execute_code contains quoted relative "
                "plugin/agent directory token combined with a write primitive. "
                "Relative paths via os.path.join('plugins',…) require an approved "
                "proposal with the absolute path (ADV-W11-003)."
            )
    cands = extract_candidate_paths(args)
    rename = looks_like_rename_or_copy(args)
    high = [p for p in cands if is_high_risk_target(p)]

    if not high:
        # temp+rename: command has mv/os.replace AND a high-risk token in blob
        # ADV-W13-001: use word-boundary anchored _HR_REL for relative plugin paths.
        _HR_REL_FALLBACK = re.compile(r"(?<!\w)(?:plugins(?:/|\b)|agent/)")
        if rename:
            blob = "\n".join(_string_values(args))
            if is_high_risk_target(blob) or any(
                x in blob for x in (
                    "config.yaml", "config.yml",
                    "/plugins/", "/agent/",
                )
            ) or _HR_REL_FALLBACK.search(blob):
                # treat whole blob as potential target
                high = [p for p in extract_candidate_paths({"command": blob}) if is_high_risk_target(p)]
                if not high:
                    high = ["<rename-primitive + high-risk token>"]
        # ADV-W12-006 / ADV-W13-002: shell redirect to HR path.
        # ADV-W13-002: moved from 'elif' to a separate check so it fires even when rename=True
        #   (e.g. os.system('echo x > plugins/evil.py') triggers RENAME on os.system AND redirect).
        # ADV-W13-003: only apply for terminal tool (avoids matching Python >> or HTML > in other tools).
        if not high and tool_name == "terminal":
            blob = "\n".join(_string_values(args))
            if _SHELL_REDIRECT.search(blob) and (
                any(x in blob for x in ("config.yaml", "config.yml", "/plugins/", "/agent/", "plugin.yaml"))
                or _HR_REL_FALLBACK.search(blob)
            ):
                high = ["<shell-redirect + high-risk token>"]
        # ADV-W14-002+006+009: terminal copy-verb blob scan.
        # Catches prefix chains (sudo -n cp), dd of=, install, and other non-anchored patterns.
        if not high and tool_name == "terminal":
            blob = "\n".join(_string_values(args))
            if _COPY_VERB.search(blob) and (
                any(t in blob for t in ("config.yaml", "config.yml", "/plugins/", "/agent/", "plugin.yaml"))
                or bool(re.search(r"(?<!\w)(?:plugins(?:/|\b)|agent/)", blob))
            ):
                high = ["<copy-verb + high-risk token>"]
            if _INPLACE_EDITOR.search(blob) and re.search(r"(?:--in-place|-[a-zA-Z]{0,4}i[a-zA-Z]{0,4}\b)", blob) and (
                any(t in blob for t in ("config.yaml", "config.yml", "/plugins/", "/agent/", "plugin.yaml"))
                or bool(re.search(r"(?<!\w)(?:plugins(?:/|\b)|agent/)", blob))
                ):
                    high = ["<inplace-editor -i + high-risk token>"]  # ADV-W16-008

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
            # ADV-W10-004: removed unconditional bootstrap exception for 'governance-hard-block'
            # substring. The synthetic placeholder must go through the same proposal check.
            # Bootstrap exception applies only to concrete paths via is_bootstrap_exception(path).
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
