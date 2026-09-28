#!/usr/bin/env python3
"""
catastrophic-forgetting-guard.py — Continual learning protection for skill patches
arXiv:2609.23916 — Time-Incremental Continued Pretraining without Catastrophic Forgetting

Called with --skill-path PATH --patch-sha SHA before applying a skill patch.
Reads patch from stdin as unified diff text.
Blocks patches that REMOVE sections present for >30 days.

Exit 0 = allow patch
Exit 1 = block patch (logs warning)

Usage:
  echo '<diff>' | python3 catastrophic-forgetting-guard.py --skill-path SKILL.md --patch-sha abc123
"""
import sys
import re
import json
import os
import hashlib
import argparse
import datetime
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
SHADOW_REGISTRY = _HERMES_HOME / "profiles/fork/logs/skill-shadow-registry.jsonl"
FORGET_LOG = _HERMES_HOME / "profiles/fork/logs/forgetting-guard.jsonl"
FORGET_LOG.parent.mkdir(parents=True, exist_ok=True)

SECTION_HEADER_RE = re.compile(r'^#{2,4}\s+(.+)$', re.MULTILINE)
REMOVED_LINE_RE = re.compile(r'^-(.*)$', re.MULTILINE)
ADDED_LINE_RE = re.compile(r'^\+(.*)$', re.MULTILINE)

PROTECTION_DAYS = 30  # sections older than this are protected


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _mtime_days_ago(path: Path) -> float:
    try:
        import os
        mtime = path.stat().st_mtime
        age_seconds = datetime.datetime.utcnow().timestamp() - mtime
        return age_seconds / 86400.0
    except Exception:
        return 0.0


def _load_shadow_registry() -> dict[str, dict]:
    """Load shadow registry, keyed by skill file PATH for forgetting-guard lookups.

    The registry file is keyed by sha256 of full file content (written by
    skill-shadow-registry.py), but we look up by path here so section-level
    checks can retrieve the confirmed state of the skill file that contains the
    section being removed.
    """
    registry: dict[str, dict] = {}
    if not SHADOW_REGISTRY.exists():
        return registry
    try:
        with SHADOW_REGISTRY.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    # Key by path so lookup in main() can match skill_path directly.
                    # The registry file uses sha256 of full content as the primary key,
                    # but forgetting-guard needs to locate a skill file's record by path.
                    key = rec.get("path") or rec.get("sha256", "")
                    if key:
                        registry[key] = rec
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return registry


def _extract_sections(text: str) -> list[str]:
    return SECTION_HEADER_RE.findall(text)


def _days_since(iso_str: str) -> float:
    try:
        dt = datetime.datetime.fromisoformat(iso_str.rstrip("Z"))
        delta = datetime.datetime.utcnow() - dt
        return delta.total_seconds() / 86400.0
    except Exception:
        return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Catastrophic forgetting guard")
    parser.add_argument("--skill-path", required=True, help="Path to SKILL.md")
    parser.add_argument("--patch-sha", default="", help="SHA of incoming patch")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    patch_sha = args.patch_sha

    # Read patch from stdin
    patch_text = sys.stdin.read()

    # Read current skill content
    if not skill_path.exists():
        # No existing file — nothing to protect
        sys.exit(0)

    try:
        current_content = skill_path.read_text()
    except OSError:
        # Cannot read skill file — pass through (no basis to block)
        return

    current_sections = _extract_sections(current_content)
    skill_age_days = _mtime_days_ago(skill_path)

    # Extract removed section headers from the diff
    removed_lines = REMOVED_LINE_RE.findall(patch_text)
    removed_sections = []
    for line in removed_lines:
        m = SECTION_HEADER_RE.match(line.strip())
        if m:
            removed_sections.append(m.group(1).strip())

    if not removed_sections:
        # Patch adds or modifies, doesn't remove sections — allow
        sys.exit(0)

    # Load shadow registry for confirmed section check
    registry = _load_shadow_registry()

    # Check each removed section
    blocked_sections = []
    for section in removed_sections:
        if section not in current_sections:
            continue  # section doesn't actually exist in current — skip

        # Check age via git (try) or mtime (fallback)
        section_age_days = skill_age_days  # conservative: use whole-file age

        # Check shadow registry for this skill file's confirmed entry.
        # Registry is keyed by skill path; section-level sha was incorrect (F22).
        reg_rec = registry.get(str(skill_path), {})
        if reg_rec.get("state") == "confirmed":
            first_seen = reg_rec.get("first_seen", "")
            if first_seen:
                section_age_days = max(section_age_days, _days_since(first_seen))

        if section_age_days >= PROTECTION_DAYS:
            blocked_sections.append({
                "section": section,
                "age_days": round(section_age_days, 1),
                "registry_state": reg_rec.get("state", "unknown"),
            })

    if blocked_sections:
        log_entry = {
            "ts": _now_iso(),
            "skill_path": str(skill_path),
            "patch_sha": patch_sha,
            "decision": "BLOCKED",
            "blocked_sections": blocked_sections,
        }
        with FORGET_LOG.open("a") as f:
            f.write(json.dumps(log_entry) + "\n")

        print(
            f"CATASTROPHIC FORGETTING GUARD: patch blocked — would remove "
            f"{len(blocked_sections)} protected section(s) "
            f"(present >{PROTECTION_DAYS} days):",
            file=sys.stderr
        )
        for b in blocked_sections:
            print(f"  - '{b['section']}' (age={b['age_days']}d, "
                  f"state={b['registry_state']})", file=sys.stderr)
        sys.exit(1)

    # Allow
    log_entry = {
        "ts": _now_iso(),
        "skill_path": str(skill_path),
        "patch_sha": patch_sha,
        "decision": "ALLOW",
        "removed_sections": removed_sections,
    }
    with FORGET_LOG.open("a") as f:
        f.write(json.dumps(log_entry) + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
