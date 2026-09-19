#!/usr/bin/env python3
"""
spike-queue-actuator.py — Dispatch accepted SPIKE items from cs/math spike queues
as Hermes improvement proposals via improvement_governance.py CLI.

Reads:
  cache/research/cs-*-spike-queue.json   (items[] with interpretation_type==SPIKE)
  cache/research/math-*-spike-queue.json (pending_spikes[])

State:
  cache/spike-actuator-state.json  — keyed by paper_id, records proposal_id + ts

Runs daily at 10:00 via cron (spike-queue-actuator-0001).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ── Profile-aware root resolution ─────────────────────────────────────────────
_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_profile = os.environ.get("HERMES_PROFILE", "")
_root = (_base / "profiles" / _profile) if _profile and "profiles" not in str(_base) else _base

CACHE_DIR = _root / "cache" / "research"
STATE_PATH = _root / "cache" / "spike-actuator-state.json"
SCRIPTS_DIR = Path(__file__).parent
GOVERNANCE_SCRIPT = SCRIPTS_DIR / "improvement_governance.py"

# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | list | None:
    """Load JSON from path; return None on missing/parse error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"[actuator] WARNING: could not read {path}: {exc}", file=sys.stderr)
        return None


def _atomic_write(path: Path, data: dict) -> None:
    """Write JSON to path atomically via a temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _load_state() -> dict:
    """Load actuator state; returns {} on missing."""
    raw = _load_json(STATE_PATH)
    if isinstance(raw, dict):
        return raw
    return {}


def _save_state(state: dict) -> None:
    _atomic_write(STATE_PATH, state)


# ── Spike queue loaders ────────────────────────────────────────────────────────

def _collect_cs_spikes() -> list[dict]:
    """
    Collect SPIKE items from all cs-*-spike-queue.json files.
    CS items schema (items[]): interpretation_type, title, abstract (or given_when_then),
    category_key, component; paper id is in item["id"] or item["arxiv_id"].
    """
    spikes: list[dict] = []
    # Glob for any cs-*-spike-queue.json in cache/research
    if not CACHE_DIR.exists():
        return spikes
    for path in sorted(CACHE_DIR.glob("*-spike-queue.json")):
        if "math" in path.name:
            continue  # handled separately
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        items = data.get("items", [])
        for item in items:
            if item.get("interpretation_type") != "SPIKE":
                continue
            paper_id = item.get("id") or item.get("arxiv_id") or item.get("title", "")[:40]
            if not paper_id:
                continue
            spikes.append({
                "paper_id": str(paper_id),
                "title": item.get("title", ""),
                "description": item.get("abstract") or item.get("given_when_then") or "",
                "category": item.get("category_key") or item.get("category") or "",
                "source_file": str(path),
                "queue_type": "cs",
            })
    return spikes


def _collect_math_spikes() -> list[dict]:
    """
    Collect items from all math-*-spike-queue.json files.
    Math items schema (pending_spikes[]): id, title, category, target, given, when, then, url.
    """
    spikes: list[dict] = []
    if not CACHE_DIR.exists():
        return spikes
    for path in sorted(CACHE_DIR.glob("math-*-spike-queue.json")):
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        pending = data.get("pending_spikes", [])
        for item in pending:
            paper_id = item.get("id") or item.get("arxiv_id") or item.get("title", "")[:40]
            if not paper_id:
                continue
            # Compose a description from given/when/then
            given = item.get("given", "")
            when = item.get("when", "")
            then = item.get("then", "")
            description = f"Given: {given} When: {when} Then: {then}".strip()
            if not description:
                description = item.get("hypothesis", "")
            spikes.append({
                "paper_id": str(paper_id),
                "title": item.get("title", ""),
                "description": description,
                "category": item.get("category", ""),
                "source_file": str(path),
                "queue_type": "math",
            })
    return spikes


# ── Governance call ────────────────────────────────────────────────────────────

def _propose(item: dict) -> dict | None:
    """
    Call improvement_governance.py propose and return the parsed proposal dict.
    Returns None on failure.
    """
    title_str = f"[SPIKE] {item['title']}"
    # Truncate description to 300 chars
    desc = item["description"][:300] if item["description"] else f"Research spike: {item['title'][:100]}"
    # Use 'research' as change_type (maps to a known type)
    # change_type must be one of: skill_body | skill_routing | cron | config | security | schema
    # Use 'skill_body' as the closest match for research spikes proposing capability additions
    change_type = "skill_body"
    target = item["title"][:60].replace(" ", "-").lower() or "research-spike"
    # Sanitize target to avoid shell issues
    target = "".join(c if c.isalnum() or c in "-_." else "-" for c in target).strip("-")

    cmd = [
        sys.executable,
        str(GOVERNANCE_SCRIPT),
        "propose",
        "--change-type", change_type,
        "--target", target,
        "--description", f"{title_str}: {desc}",
        "--evidence", f"source={item['queue_type']}-spike-queue",
        "--evidence", f"category={item['category']}",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(SCRIPTS_DIR),
        )
    except subprocess.TimeoutExpired:
        print(f"[actuator] TIMEOUT proposing {item['paper_id']!r}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"[actuator] ERROR running governance CLI: {exc}", file=sys.stderr)
        return None

    if result.returncode != 0:
        err = result.stderr.strip()[:200]
        print(f"[actuator] governance propose failed for {item['paper_id']!r}: {err}", file=sys.stderr)
        return None

    try:
        proposal = json.loads(result.stdout)
        return proposal
    except json.JSONDecodeError as exc:
        print(f"[actuator] could not parse governance output: {exc}", file=sys.stderr)
        print(f"  stdout: {result.stdout[:200]}", file=sys.stderr)
        return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"[actuator] spike-queue-actuator starting — profile={_profile or '(default)'}")
    print(f"[actuator] cache dir: {CACHE_DIR}")

    # Collect all spikes from both queues
    cs_spikes = _collect_cs_spikes()
    math_spikes = _collect_math_spikes()
    all_spikes = cs_spikes + math_spikes
    print(f"[actuator] found {len(cs_spikes)} CS spikes, {len(math_spikes)} math spikes "
          f"({len(all_spikes)} total)")

    if not all_spikes:
        print("[actuator] no spike items found — nothing to do")
        print("[actuator] summary: 0 processed, 0 new proposals, 0 already-done")
        return 0

    # Load existing state
    state = _load_state()
    done_ids: set[str] = set(state.keys())

    n_processed = 0
    n_created = 0
    n_skipped = 0

    for item in all_spikes:
        paper_id = item["paper_id"]
        n_processed += 1

        if paper_id in done_ids:
            n_skipped += 1
            continue

        print(f"[actuator] proposing: {paper_id!r} — {item['title'][:60]}")
        proposal = _propose(item)

        if proposal is None:
            # Failed — do not record so it can be retried next run
            print(f"[actuator] WARNING: proposal failed for {paper_id!r}, will retry next run",
                  file=sys.stderr)
            continue

        proposal_id = proposal.get("id", "unknown")
        ts = datetime.now(timezone.utc).isoformat()
        state[paper_id] = {
            "paper_id": paper_id,
            "proposal_id": proposal_id,
            "title": item["title"][:100],
            "queue_type": item["queue_type"],
            "proposed_at": ts,
        }
        # Atomic write after each successful proposal (crash-safe)
        try:
            _save_state(state)
        except Exception as exc:
            print(f"[actuator] ERROR saving state: {exc}", file=sys.stderr)
            return 1

        n_created += 1
        print(f"[actuator] created proposal {proposal_id!r} for {paper_id!r}")

    print(f"\n[actuator] summary: {n_processed} processed, "
          f"{n_created} new proposals created, "
          f"{n_skipped} already-done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
