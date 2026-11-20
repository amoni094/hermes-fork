#!/usr/bin/env python3
"""
Reflection Distiller

Emits structured FAILED_PREFIX + ROOT_CAUSE + CORRECTION reflection records
before skill re-patching. Records go to a JSONL log so the agent can inspect
why a patch failed and avoid repeating the same mistake.

Hypothesis: structured reflection before re-patching reduces repeat-error rate
    by capturing root cause explicitly, targeting < 10% same-error recurrence
    over 50 patch cycles.

GWT:
  Given:  a failed skill patch with an error message,
  When:   reflect() is called before re-attempting,
  Then:   a FAILED_PREFIX/ROOT_CAUSE/CORRECTION record is appended to the log
          within 10 ms and returned to the caller.

Kill test:
    r = reflect('my-skill', 'patch', 'SyntaxError at line 5')
    assert r['root_cause']
    assert r['correction']

Metric: repeat_error_rate = same_error_recurrence_count / total_repatch_attempts
    target < 0.10, measured over 50 patch cycles from reflection-distiller.log.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
HERMES_HOME  = Path(__file__).resolve().parents[3]
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
LOG_PATH     = PROFILE_ROOT / "cache" / "reflection-distiller.log"

# ── Root-cause heuristics ─────────────────────────────────────────────────────
_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"SyntaxError.*line\s+(\d+)", re.IGNORECASE),
     "SyntaxError in generated patch text",
     "Validate patch string with ast.parse() before applying; check indentation and string escapes."),
    (re.compile(r"IndentationError", re.IGNORECASE),
     "Inconsistent indentation in patch",
     "Use 4-space indentation throughout; avoid mixing tabs and spaces."),
    (re.compile(r"assert.*failed|AssertionError", re.IGNORECASE),
     "Layer1 assertion failed after patch",
     "Re-read the kill-test criteria; ensure the patch satisfies the invariant, not just the syntax."),
    (re.compile(r"unique match|multiple matches|no match", re.IGNORECASE),
     "patch() old_string did not uniquely match file content",
     "Add more surrounding context lines to old_string so it uniquely identifies the target span."),
    (re.compile(r"FileNotFoundError|No such file", re.IGNORECASE),
     "Target file does not exist at the expected path",
     "Verify the skill path with skill_view() before patching; check profile root resolution."),
    (re.compile(r"PermissionError|DENY|governance", re.IGNORECASE),
     "Write blocked by governance gate or permission error",
     "File a governance proposal for the target path; ensure HERMES_HOME resolves to base profile."),
    (re.compile(r"json.*decode|JSONDecodeError", re.IGNORECASE),
     "JSON parse error in skill content or config file",
     "Validate JSON with json.loads() on the raw text before embedding it in a patch."),
    (re.compile(r"import.*error|ModuleNotFoundError", re.IGNORECASE),
     "Import error — dependency unavailable",
     "Use stdlib only, or add a try/except import with a fallback stub."),
    (re.compile(r"KeyError|AttributeError", re.IGNORECASE),
     "Missing key or attribute in data structure",
     "Check dict keys with .get() and add defensive None checks before attribute access."),
]

_DEFAULT_RC  = "Unknown error pattern — inspect error text for specific cause."
_DEFAULT_FIX = "Read the skill content again with skill_view(), identify the failing span, and rewrite the patch with more context."


def _classify(error_text: str) -> tuple[str, str]:
    """Return (root_cause, correction) from error_text heuristics."""
    for pattern, rc, fix in _PATTERNS:
        if pattern.search(error_text):
            return rc, fix
    return _DEFAULT_RC, _DEFAULT_FIX


def _fingerprint(skill_name: str, failed_operation: str, root_cause: str) -> str:
    key = f"{skill_name}|{failed_operation}|{root_cause}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


# ── Public API ────────────────────────────────────────────────────────────────
def reflect(
    skill_name: str,
    failed_operation: str,
    error_text: str,
    confidence: float = 0.7,
    extra: Optional[dict] = None,
) -> dict:
    """
    Classify a failed skill operation and emit a structured reflection record.

    Returns the reflection dict (also appended to LOG_PATH as JSONL).
    """
    root_cause, correction = _classify(error_text)
    record = {
        "ts":               datetime.now(UTC).isoformat(),
        "skill_name":       skill_name,
        "failed_operation": failed_operation,
        "error_snippet":    error_text[:200],
        "root_cause":       root_cause,
        "correction":       correction,
        "confidence":       confidence,
        "fingerprint":      _fingerprint(skill_name, failed_operation, root_cause),
        **(extra or {}),
    }
    _append(record)
    return record


def get_recent(n: int = 20) -> list[dict]:
    """Return last n reflection records from log."""
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text().splitlines()
    records = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records[-n:]


def repeat_error_rate(skill_name: Optional[str] = None) -> float:
    """
    Compute repeat_error_rate = recurring_fingerprints / total_records.
    A fingerprint that appears > 1 time is a repeat.
    """
    records = get_recent(200)
    if skill_name:
        records = [r for r in records if r.get("skill_name") == skill_name]
    if not records:
        return 0.0
    from collections import Counter
    counts = Counter(r.get("fingerprint", "") for r in records)
    repeats = sum(v - 1 for v in counts.values() if v > 1)
    return repeats / len(records)


def _append(record: dict) -> None:
    t0 = time.monotonic()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as fh:
        fh.write(json.dumps(record) + "\n")
    elapsed_ms = (time.monotonic() - t0) * 1000
    if elapsed_ms > 10:
        import logging
        logging.getLogger("reflection-distiller").warning(
            "reflect() write took %.1f ms (> 10 ms SLA)", elapsed_ms
        )


# ── Layer1 demo ───────────────────────────────────────────────────────────────
def layer1_demo() -> None:
    import tempfile, os

    # Use a temp log so we don't pollute the real log during tests
    tmp = Path(tempfile.mktemp(suffix=".log"))
    global LOG_PATH
    orig_log = LOG_PATH
    LOG_PATH = tmp

    try:
        # Case 1: SyntaxError
        r1 = reflect("my-skill", "patch", "SyntaxError at line 5: unexpected indent")
        assert r1["root_cause"], "root_cause must be non-empty"
        assert r1["correction"], "correction must be non-empty"
        assert r1["skill_name"] == "my-skill"
        assert r1["failed_operation"] == "patch"
        assert r1["fingerprint"]

        # Case 2: AssertionError
        r2 = reflect("other-skill", "layer1_test", "AssertionError: expected PASS got FAIL")
        assert "assertion" in r2["root_cause"].lower() or "layer1" in r2["root_cause"].lower()

        # Case 3: unique match failure
        r3 = reflect("routing-skill", "patch", "no match found for old_string in file")
        assert "match" in r3["root_cause"].lower() or "unique" in r3["root_cause"].lower()

        # Verify log written
        assert tmp.exists(), "log file must be created"
        lines = [l for l in tmp.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 3, f"Expected 3 log lines, got {len(lines)}"
        for line in lines:
            parsed = json.loads(line)
            assert parsed["ts"]
            assert parsed["root_cause"]
            assert parsed["correction"]

        # Verify repeat_error_rate doesn't crash
        rate = repeat_error_rate()
        assert 0.0 <= rate <= 1.0

        print(f"[layer1] PASS — 3 reflections written, log intact, repeat_rate={rate:.2f}")
    finally:
        LOG_PATH = orig_log
        tmp.unlink(missing_ok=True)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    import argparse
    pa = argparse.ArgumentParser(description="Reflection Distiller")
    pa.add_argument("--layer1",    action="store_true", help="Run layer1 demo and exit")
    pa.add_argument("--stats",     action="store_true", help="Print repeat_error_rate and recent records")
    pa.add_argument("--skill",     default=None,        help="Filter stats by skill name")
    pa.add_argument("--reflect",   nargs=3, metavar=("SKILL", "OP", "ERROR"),
                    help="Record a reflection from the command line")
    args = pa.parse_args()

    if args.layer1:
        layer1_demo()
        return

    if args.reflect:
        skill, op, err = args.reflect
        r = reflect(skill, op, err)
        print(json.dumps(r, indent=2))
        return

    if args.stats:
        records = get_recent(50)
        rate = repeat_error_rate(args.skill)
        print(f"Recent reflections: {len(records)}")
        print(f"Repeat error rate: {rate:.3f}")
        for r in records[-5:]:
            print(f"  [{r['ts'][:19]}] {r['skill_name']} / {r['failed_operation']}: {r['root_cause'][:60]}")
        return

    pa.print_help()


if __name__ == "__main__":
    main()
