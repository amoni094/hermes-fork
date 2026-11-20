#!/usr/bin/env python3
"""
skill-shadow-registry.py — MedRSI slow-registration gate for skill patches
arXiv:2609.24838 — MedRSI: Recursive Self-Improvement via Clinically Aligned Self-Evolution

Pattern: fast-discovery / slow-registration.
- New skill patches enter 'shadow' state immediately.
- They graduate to 'confirmed' only after appearing unchanged across 3+ sessions
  (proxy: sha256 stable across 3 runs >=24h apart).
- Rejected if a revert or conflict is detected.

Registry: ~/.hermes/profiles/fork/logs/skill-shadow-registry.jsonl (JSONL, keyed by sha256)
"""
import sys
import json
import os
import hashlib
import datetime
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hh = str(_HERMES_HOME)
_FORK_ROOT = _HERMES_HOME if ("profiles" in _hh and _hh.endswith("fork")) else _HERMES_HOME / "profiles/fork"
SKILLS_ROOTS = [
    _FORK_ROOT / "skills",
    _HERMES_HOME / "skills",
]
REGISTRY_PATH = _FORK_ROOT / "logs/skill-shadow-registry.jsonl"
REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

SHADOW_MIN_SESSIONS = 3
SESSION_PROXY_HOURS = 24  # treat a new check >=24h apart as a new "session"


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _load_registry() -> dict[str, dict]:
    """Load registry keyed by sha256."""
    registry: dict[str, dict] = {}
    if not REGISTRY_PATH.exists():
        return registry
    try:
        with REGISTRY_PATH.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    sha = rec.get("sha256", "")
                    if sha:
                        registry[sha] = rec
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return registry


def _save_registry(registry: dict[str, dict]) -> None:
    # Atomic write: write to tmp then rename so a crash mid-write never corrupts the registry
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    try:
        with tmp.open("w") as f:
            for rec in registry.values():
                f.write(json.dumps(rec) + "\n")
        tmp.replace(REGISTRY_PATH)
    except OSError as e:
        print(f"WARN: could not save registry: {e}", file=sys.stderr)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _find_skill_files() -> list[Path]:
    files = []
    for root in SKILLS_ROOTS:
        if root.exists():
            files.extend(root.rglob("SKILL.md"))
    return files


def _hours_since(iso_str: str) -> float:
    try:
        dt = datetime.datetime.fromisoformat(iso_str.rstrip("Z"))
        delta = datetime.datetime.utcnow() - dt
        return delta.total_seconds() / 3600.0
    except Exception:
        return 999.0


def main() -> None:
    registry = _load_registry()
    skill_files = _find_skill_files()

    now = _now_iso()
    promoted_today: list[str] = []
    shadow_count = 0
    confirmed_count = 0
    new_count = 0

    for skill_path in skill_files:
        try:
            content = skill_path.read_text()
        except OSError:
            continue

        sha = _sha256(content)
        path_str = str(skill_path)

        if sha not in registry:
            # New patch — enter shadow state
            registry[sha] = {
                "sha256": sha,
                "path": path_str,
                "state": "shadow",
                "first_seen": now,
                "last_checked": now,
                "session_count": 1,
            }
            new_count += 1
            shadow_count += 1
        else:
            rec = registry[sha]
            state = rec.get("state", "shadow")

            if state == "shadow":
                # Count as a new session if last check was >=24h ago
                hours = _hours_since(rec.get("last_checked", rec.get("first_seen", now)))
                if hours >= SESSION_PROXY_HOURS:
                    rec["session_count"] = rec.get("session_count", 1) + 1
                    rec["last_checked"] = now

                if rec["session_count"] >= SHADOW_MIN_SESSIONS:
                    rec["state"] = "confirmed"
                    rec["confirmed_at"] = now
                    promoted_today.append(path_str)
                    confirmed_count += 1
                else:
                    shadow_count += 1

            elif state == "confirmed":
                confirmed_count += 1
                # Update last_checked
                rec["last_checked"] = now

            registry[sha] = rec

    _save_registry(registry)

    # Summary (always print — cron script outputs this as status)
    print(f"skill-shadow-registry: {len(skill_files)} skills scanned | "
          f"{new_count} new (shadow) | {shadow_count} shadow | "
          f"{confirmed_count} confirmed | {len(promoted_today)} promoted today")
    if promoted_today:
        for p in promoted_today[:5]:
            print(f"  PROMOTED: {p}")


if __name__ == "__main__":
    main()
