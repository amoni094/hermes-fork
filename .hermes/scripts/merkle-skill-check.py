#!/usr/bin/env python3
"""
merkle-skill-check.py — Merkle root over all SKILL.md SHA256 hashes.

Builds a binary Merkle tree over sorted SHA256(file_bytes) for all SKILL.md
files found under ~/.hermes/profiles/fork/skills/.

Stores result in ~/.hermes/cache/skill-merkle.json.

On verify run, recomputes and compares root.
Prints 'MERKLE_OK' or 'MERKLE_FAIL: N files changed'.

Usage:
  python3 merkle-skill-check.py generate
  python3 merkle-skill-check.py verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SKILLS_DIR = HERMES_HOME / "skills"
MERKLE_PATH = HERMES_HOME / "cache" / "skill-merkle.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scan_skills() -> list[Path]:
    if not SKILLS_DIR.exists():
        return []
    # rglob from SKILLS_DIR may not traverse if dir perms prevent stat from parent;
    # iterate top-level category dirs explicitly instead.
    results: list[Path] = []
    for child in SKILLS_DIR.iterdir():
        if child.is_dir():
            results.extend(child.rglob("SKILL.md"))
        elif child.name == "SKILL.md":
            results.append(child)
    return sorted(results)


def _merkle_root(hashes: list[str]) -> str:
    """Build a binary Merkle root from a sorted list of leaf hashes."""
    if not hashes:
        return hashlib.sha256(b"").hexdigest()
    layer = list(hashes)
    while len(layer) > 1:
        next_layer: list[str] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left  # duplicate last if odd
            combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
            next_layer.append(combined)
        layer = next_layer
    return layer[0]


def _compute_state(files: list[Path]) -> tuple[str, dict[str, str]]:
    """Returns (merkle_root, {rel_path: sha256})."""
    leaf_map: dict[str, str] = {}
    for f in files:
        rel = str(f.relative_to(HERMES_HOME))
        leaf_map[rel] = _sha256_file(f)
    sorted_hashes = [leaf_map[k] for k in sorted(leaf_map)]
    root = _merkle_root(sorted_hashes)
    return root, leaf_map


def cmd_generate(args: argparse.Namespace) -> int:
    files = _scan_skills()
    root, leaf_map = _compute_state(files)
    MERKLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"merkle_root": root, "file_count": len(files), "leaves": leaf_map}
    MERKLE_PATH.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"MERKLE_ROOT: {root}")
    print(f"Files: {len(files)} → {MERKLE_PATH}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    if not MERKLE_PATH.exists():
        print("[WARN] No Merkle baseline found — run 'generate' first.")
        return 1

    try:
        stored = json.loads(MERKLE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[ERROR] Cannot read Merkle file: {exc}", file=sys.stderr)
        return 1

    stored_root = stored.get("merkle_root", "")
    stored_leaves: dict[str, str] = stored.get("leaves", {})

    files = _scan_skills()
    current_root, current_leaves = _compute_state(files)

    if current_root == stored_root:
        print(f"MERKLE_OK (root={current_root[:16]}…, {len(files)} files)")
        return 0

    # Count changed files
    changed = 0
    for rel, old_hash in stored_leaves.items():
        if current_leaves.get(rel) != old_hash:
            changed += 1
    # New files not in baseline
    for rel in current_leaves:
        if rel not in stored_leaves:
            changed += 1

    print(f"MERKLE_FAIL: {changed} files changed")
    print(f"  stored_root:  {stored_root[:32]}…")
    print(f"  current_root: {current_root[:32]}…")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Merkle root integrity check for skill files")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate", help="Compute and store Merkle root baseline")
    sub.add_parser("verify", help="Recompute and compare Merkle root")
    args = ap.parse_args()
    dispatch = {"generate": cmd_generate, "verify": cmd_verify}
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
