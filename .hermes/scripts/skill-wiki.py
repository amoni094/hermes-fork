#!/usr/bin/env python3
"""
skill-wiki.py — WikiSkill pattern: co-evolve agent skills with a persistent wiki.

arXiv:2608.27454 (WikiSkill): separates raw execution history from optimization
insight. Instead of scattering improvement notes across optimization logs, each
skill co-evolves with a structured wiki entry that captures WHY it works,
known failure modes, and verified successor patterns.

This script manages the wiki layer:
  ~/.hermes/cache/skill-wiki/<skill_name>.json

Wiki entry schema:
  - skill_name: str
  - description_why: str       # why this skill works / intended use
  - failure_modes: list[str]   # known failure patterns with conditions
  - successor_patterns: list   # verified improvement sequences
  - precondition_notes: list   # context conditions for reliable invocation
  - calibration_notes: list    # edge cases and confidence adjustments
  - evidence_refs: list[str]   # arXiv IDs / sources supporting entries
  - last_updated: ISO8601

Usage:
  python3 skill-wiki.py upsert --skill SKILL_NAME --section failure_modes \\
      --text "Fails when X because Y" --ref "2608.27454"
  python3 skill-wiki.py show --skill SKILL_NAME
  python3 skill-wiki.py search --query "context rot"
  python3 skill-wiki.py export    # exports all as markdown summary
  python3 skill-wiki.py prune     # removes stale entries (>90d, no access)

Integration with skill lifecycle:
  - skill_prune_audit.py reads wiki failure_modes before pruning
  - l1-promote.py checks wiki precondition_notes for memory routing
  - hermes-agent-skill-authoring skill recommends wiki upsert on skill update
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
WIKI_DIR = HERMES_HOME / "cache" / "skill-wiki"
ENABLED = True


def _load_runtime_config() -> None:
    global WIKI_DIR, ENABLED
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        return
    text = cfg_path.read_text()
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        sec = data.get("skill_wiki") or (data.get("memory") or {}).get("skill_wiki") or {}
        if sec.get("enabled") is False:
            ENABLED = False
        if sec.get("dir"):
            WIKI_DIR = HERMES_HOME / str(sec["dir"])
        return
    except Exception:
        pass


_load_runtime_config()
VALID_SECTIONS = (
    "description_why",
    "failure_modes",
    "successor_patterns",
    "precondition_notes",
    "calibration_notes",
    "evidence_refs",
    "results",
    "source_context",  # WikiSkill: where this insight was observed
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:80]


def _path(skill_name: str) -> Path:
    return WIKI_DIR / f"{_safe_name(skill_name)}.json"


def _load(skill_name: str) -> dict[str, Any]:
    p = _path(skill_name)
    if not p.exists():
        return {
            "schema": "hermes-skill-wiki/v1",
            "skill_name": skill_name,
            "description_why": "",
            "failure_modes": [],
            "successor_patterns": [],
            "precondition_notes": [],
            "calibration_notes": [],
            "evidence_refs": [],
            "results": [],
            "source_context": [],
            "last_updated": None,
            "access_count": 0,
        }
    return json.loads(p.read_text())


def _save(doc: dict[str, Any]) -> Path:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    doc["last_updated"] = _now()
    p = _path(doc["skill_name"])
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return p


def cmd_upsert(args: argparse.Namespace) -> int:
    if not ENABLED:
        print("[wiki] skipped: skill_wiki.enabled=false")
        return 0
    doc = _load(args.skill)
    section = args.section
    text = args.text
    ref = getattr(args, "ref", None)

    if section == "description_why":
        doc["description_why"] = text
    elif section in ("failure_modes", "successor_patterns", "precondition_notes", "calibration_notes", "source_context"):
        entry: dict[str, Any] = {"text": text, "added": _now()}
        if ref:
            entry["ref"] = ref
        existing_texts = [e["text"] if isinstance(e, dict) else e for e in doc[section]]
        if text not in existing_texts:
            doc[section].append(entry)
        else:
            print(f"[wiki] duplicate text in {section}, skipped", file=sys.stderr)
            return 0
    elif section == "evidence_refs":
        if text not in doc["evidence_refs"]:
            doc["evidence_refs"].append(text)
    elif section == "results":
        entry: dict = {"text": text, "added": _now()}
        if ref:
            entry["ref"] = ref
        existing = [e["text"] if isinstance(e, dict) else e for e in doc.get("results", [])]
        if text not in existing:
            doc.setdefault("results", []).append(entry)
        else:
            print(f"[wiki] duplicate result text, skipped", file=sys.stderr)
            return 0

    p = _save(doc)
    print(f"[wiki] updated {section} for skill '{args.skill}' -> {p}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    doc = _load(args.skill)
    doc["access_count"] = doc.get("access_count", 0) + 1
    _save(doc)
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    query = args.query.lower()
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    hits: list[tuple[str, str, str]] = []
    for p in sorted(WIKI_DIR.glob("*.json")):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        for section in VALID_SECTIONS:
            val = doc.get(section, "")
            haystack = json.dumps(val).lower() if not isinstance(val, str) else val.lower()
            if query in haystack:
                hits.append((doc.get("skill_name", p.stem), section, haystack[:120]))
    if not hits:
        print(f"[wiki] no matches for '{args.query}'")
    else:
        for skill, section, ctx in hits:
            print(f"  {skill} [{section}]: ...{ctx}...")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"# Hermes Skill Wiki — exported {_now()}\n"]
    for p in sorted(WIKI_DIR.glob("*.json")):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        lines.append(f"\n## {doc.get('skill_name', p.stem)}")
        if doc.get("description_why"):
            lines.append(f"\n**Why:** {doc['description_why']}")
        for section, label in [
            ("failure_modes", "Failure modes"),
            ("precondition_notes", "Preconditions"),
            ("calibration_notes", "Calibration notes"),
            ("successor_patterns", "Successor patterns"),
            ("results", "Results"),
            ("source_context", "Source context"),
            ("evidence_refs", "References"),
        ]:
            items = doc.get(section, [])
            if items:
                lines.append(f"\n**{label}:**")
                for item in items:
                    text = item["text"] if isinstance(item, dict) else item
                    ref = item.get("ref", "") if isinstance(item, dict) else ""
                    lines.append(f"  - {text}" + (f" [{ref}]" if ref else ""))
        lines.append(f"\n_Last updated: {doc.get('last_updated', 'unknown')}_\n")
    out = Path(args.output) if getattr(args, "output", None) else HERMES_HOME / "cache" / "skill-wiki-export.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"[wiki] exported to {out}")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    from datetime import timedelta
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    cutoff_days = getattr(args, "days", 90)
    cutoff = datetime.now(timezone.utc) - timedelta(days=cutoff_days)
    pruned = 0
    for p in WIKI_DIR.glob("*.json"):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        updated = doc.get("last_updated")
        if updated:
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if dt < cutoff and doc.get("access_count", 0) == 0:
                    p.unlink()
                    pruned += 1
                    print(f"[wiki] pruned {p.stem} (last={updated}, access=0)")
            except Exception:
                pass
    print(f"[wiki] prune complete: {pruned} removed")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Hermes skill wiki — WikiSkill pattern (arXiv:2608.27454)")
    sub = p.add_subparsers(dest="cmd")

    upsert = sub.add_parser("upsert", help="Add/update a wiki entry section")
    upsert.add_argument("--skill", required=True)
    upsert.add_argument("--section", required=True, choices=VALID_SECTIONS)
    upsert.add_argument("--text", required=True)
    upsert.add_argument("--ref", default=None, help="Evidence reference (e.g. arXiv:2608.27454)")

    show = sub.add_parser("show", help="Show wiki entry for a skill")
    show.add_argument("--skill", required=True)

    search = sub.add_parser("search", help="Search wiki entries by keyword")
    search.add_argument("--query", required=True)

    export = sub.add_parser("export", help="Export all wiki entries as markdown")
    export.add_argument("--output", default=None)

    prune = sub.add_parser("prune", help="Remove stale unaccessed entries")
    prune.add_argument("--days", type=int, default=90)

    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.cmd == "upsert":
        return cmd_upsert(args)
    elif args.cmd == "show":
        return cmd_show(args)
    elif args.cmd == "search":
        return cmd_search(args)
    elif args.cmd == "export":
        return cmd_export(args)
    elif args.cmd == "prune":
        return cmd_prune(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
