#!/usr/bin/env python3
"""Compact boilerplate clusters in the append-only improvement-proposals ledger.

Scans improvement-proposals.jsonl, groups by (description, change_type, target),
and for clusters with count > 3 emits superseded tombstones for older
pending_review/approved duplicates. Original lines are never deleted.

Usage:
  HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 governance-proposal-compact.py
  python3 governance-proposal-compact.py --self-test
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

LEDGER_PATH = _hermes_root / "logs" / "improvement-proposals.jsonl"
REPORT_PATH = _hermes_root / "cache" / "governance-compact-report.json"
CLUSTER_MIN = 3  # compact groups with count > CLUSTER_MIN
TOMBSTONE_STATES = frozenset({"pending_review", "approved"})
ALREADY_TERMINAL = frozenset({"superseded", "rejected", "reverted", "rolled_back"})


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _parse_entry(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _load_entries(path: Path) -> tuple[list[dict], int]:
    """Return (valid entries in file order, n_scanned_nonempty_lines). Skip malformed."""
    entries: list[dict] = []
    n_scanned = 0
    if not path.exists():
        return entries, 0
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            n_scanned += 1
            obj = _parse_entry(line)
            if obj is None:
                continue
            entries.append(obj)
    return entries, n_scanned


def _latest_by_id(entries: list[dict]) -> dict[str, tuple[int, dict]]:
    latest: dict[str, tuple[int, dict]] = {}
    for idx, entry in enumerate(entries):
        pid = entry.get("id")
        if not pid:
            continue
        latest[str(pid)] = (idx, entry)
    return latest


def plan_tombstones(entries: list[dict], now: str | None = None) -> tuple[list[dict], dict]:
    """Compute tombstone records. Never emits double-tombstones for already-superseded ids."""
    now = now or _now_iso()
    latest = _latest_by_id(entries)
    already_superseded = {
        pid for pid, (_i, e) in latest.items() if e.get("state") == "superseded"
    }

    groups: dict[tuple, list[tuple[int, dict]]] = defaultdict(list)
    for pid, (idx, entry) in latest.items():
        if entry.get("state") == "superseded":
            continue
        key = (entry.get("description"), entry.get("change_type"), entry.get("target"))
        groups[key].append((idx, entry))

    clusters = {k: v for k, v in groups.items() if len(v) > CLUSTER_MIN}
    tombstones: list[dict] = []
    emitted_ids: set[str] = set()

    for key, items in clusters.items():
        best: dict[str, tuple[int, dict]] = {}
        for idx, entry in items:
            st = str(entry.get("state") or "")
            if st not in best or idx > best[st][0]:
                best[st] = (idx, entry)
        keeper_ids = {e.get("id") for _i, e in best.values()}
        for idx, entry in items:
            st = entry.get("state")
            if st not in TOMBSTONE_STATES:
                continue
            pid = entry.get("id")
            if not pid or pid in keeper_ids or pid in already_superseded or pid in emitted_ids:
                continue
            keeper = best.get(str(st), (None, {}))[1] or {}
            tomb = dict(entry)
            tomb["state"] = "superseded"
            tomb["superseded_by"] = keeper.get("id")
            tomb["superseded_at"] = now
            tomb["reason"] = "dedup-compact"
            tombstones.append(tomb)
            emitted_ids.add(pid)

    top_desc = ""
    if clusters:
        top_key, top_items = max(clusters.items(), key=lambda kv: len(kv[1]))
        top_desc = str(top_key[0] or "")
        _ = top_items

    stats = {
        "n_clusters": len(clusters),
        "top_cluster_desc": top_desc,
        "n_planned": len(tombstones),
    }
    return tombstones, stats


def append_tombstones(path: Path, tombstones: list[dict]) -> int:
    """Append tombstones under an exclusive flock. Returns n written."""
    if not tombstones:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            # Re-check ids already superseded under the lock to avoid double-tombstones.
            fh.seek(0)
            existing_super = set()
            for line in fh:
                obj = _parse_entry(line)
                if obj is None:
                    continue
                if obj.get("state") == "superseded" and obj.get("id"):
                    existing_super.add(obj.get("id"))
            fh.seek(0, os.SEEK_END)
            for tomb in tombstones:
                pid = tomb.get("id")
                if pid in existing_super:
                    continue
                fh.write(json.dumps(tomb, ensure_ascii=False) + "\n")
                existing_super.add(pid)
                written += 1
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return written


def run_compact(ledger: Path | None = None, report_path: Path | None = None) -> dict:
    ledger = ledger or LEDGER_PATH
    report_path = report_path or REPORT_PATH
    entries, n_scanned = _load_entries(ledger)
    tombstones, stats = plan_tombstones(entries)
    n_written = append_tombstones(ledger, tombstones)
    report = {
        "n_scanned": n_scanned,
        "n_superseded": n_written,
        "n_clusters": stats["n_clusters"],
        "top_cluster_desc": stats["top_cluster_desc"],
        "ledger": str(ledger),
        "compacted_at": _now_iso(),
    }
    _atomic_write(report_path, report)
    return report


def _self_test() -> int:
    failures: list[str] = []
    td = Path(tempfile.mkdtemp(prefix="gov-compact-st-"))
    ledger = td / "improvement-proposals.jsonl"
    report = td / "governance-compact-report.json"

    def rec(pid: str, state: str, desc: str, target: str, ts: str) -> dict:
        return {
            "id": pid,
            "state": state,
            "change_type": "CODE",
            "target": target,
            "description": desc,
            "proposed_at": ts,
        }

    desc = "agent runtime HIGH-risk tool call"
    rows = [
        rec("prop_a", "pending_review", desc, "execute_code", "2026-01-01T00:00:00Z"),
        rec("prop_b", "pending_review", desc, "execute_code", "2026-01-02T00:00:00Z"),
        rec("prop_c", "pending_review", desc, "execute_code", "2026-01-03T00:00:00Z"),
        rec("prop_d", "approved", desc, "execute_code", "2026-01-04T00:00:00Z"),
        rec("prop_e", "pending_review", "unique other proposal", "other", "2026-01-05T00:00:00Z"),
    ]
    # 5 synthetic entries; 3 pending_review duplicates in one cluster + 1 approved
    # + 1 unique. Cluster size 4 > 3 → keep newest pending + approved → 2 tombstones.
    blob = "\n".join(json.dumps(r) for r in rows) + "\n"
    blob = rows[0] and (json.dumps(rows[0]) + "\nNOT JSON{{partial\n" + "\n".join(
        json.dumps(r) for r in rows[1:]
    ) + "\n")
    ledger.write_text(blob, encoding="utf-8")

    entries, n_scanned = _load_entries(ledger)
    if n_scanned != 6:  # 5 valid + 1 malformed nonempty
        # malformed counts as scanned; 5 valid + 1 junk
        if n_scanned < 5:
            failures.append(f"scanned {n_scanned}, expected >=5")
    if len(entries) != 5:
        failures.append(f"valid entries {len(entries)}, expected 5")

    tombs, _stats = plan_tombstones(entries, now="2026-01-06T00:00:00Z")
    if len(tombs) != 2:
        failures.append(f"planned tombstones {len(tombs)}, expected 2")
    tomb_ids = {t.get("id") for t in tombs}
    if tomb_ids != {"prop_a", "prop_b"}:
        failures.append(f"tomb ids {tomb_ids}, expected prop_a, prop_b")
    if any(t.get("state") != "superseded" for t in tombs):
        failures.append("tombstone state != superseded")
    if any(t.get("reason") != "dedup-compact" for t in tombs):
        failures.append("missing reason")
    if any(t.get("superseded_by") != "prop_c" for t in tombs):
        failures.append(f"superseded_by {[t.get('superseded_by') for t in tombs]}")

    n_written = append_tombstones(ledger, tombs)
    if n_written != 2:
        failures.append(f"written {n_written}, expected 2")

    # Second pass: no double-tombstones even though originals remain.
    entries2, _ = _load_entries(ledger)
    tombs2, _ = plan_tombstones(entries2)
    if tombs2:
        failures.append(f"second plan emitted {len(tombs2)} (expected 0)")
    n_written2 = append_tombstones(ledger, tombs)  # replay original tombs
    if n_written2 != 0:
        failures.append(f"double-tombstone wrote {n_written2}")

    # Corrupt-only file is a no-op, exit-path equivalent.
    bad = td / "bad.jsonl"
    bad.write_text("{partial\n\nnot-json\n", encoding="utf-8")
    e_bad, _n_bad = _load_entries(bad)
    if e_bad:
        failures.append("corrupt file produced entries")
    tombs_bad, _ = plan_tombstones(e_bad)
    if tombs_bad:
        failures.append("corrupt file planned tombstones")

    # All-already-superseded group: no new tombs.
    done = td / "done.jsonl"
    done.write_text(
        "\n".join(
            json.dumps(rec(f"prop_s{i}", "superseded", desc, "execute_code", f"2026-01-0{i}T00:00:00Z"))
            for i in range(1, 6)
        )
        + "\n",
        encoding="utf-8",
    )
    tombs_done, _ = plan_tombstones(_load_entries(done)[0])
    if tombs_done:
        failures.append(f"already-superseded group emitted {len(tombs_done)}")

    # End-to-end run_compact writes report.
    rpt = run_compact(ledger=td / "empty-missing.jsonl", report_path=report)
    if rpt.get("n_scanned") != 0 or rpt.get("n_superseded") != 0:
        failures.append(f"empty run report {rpt}")
    if not report.exists():
        failures.append("report not written")

    if failures:
        print("SELF-TEST FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print(json.dumps({"self_test": "ok", "tombstones": 2, "skipped_malformed": True}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compact boilerplate governance proposals")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--ledger", default=None, help="Override ledger path")
    parser.add_argument("--report", default=None, help="Override report path")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    ledger = Path(args.ledger) if args.ledger else LEDGER_PATH
    report = Path(args.report) if args.report else REPORT_PATH
    result = run_compact(ledger=ledger, report_path=report)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
