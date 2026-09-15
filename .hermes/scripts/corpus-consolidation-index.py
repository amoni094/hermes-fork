#!/usr/bin/env python3
"""corpus-consolidation-index.py — Unify the three Hermes research corpora.

Sources:
  1. Hardcoded minimal Sweep Boundary Log (from arxiv-sweep-findings SKILL.md)
  2. ~/.hermes/cache/research/cs-interpretation-latest.json (if present)
  3. ~/.hermes/cache/research/math-interpretation-latest.json (if present)

Output:
  /tmp/corpus-index.json — findings deduped by arxiv_id. Each entry:
    arxiv_id, title, sweep_source, status, priority, target_skill

Foundation for future automated gap detection.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
CS_PATH = HERMES_HOME / "cache" / "research" / "cs-interpretation-latest.json"
MATH_PATH = HERMES_HOME / "cache" / "research" / "math-interpretation-latest.json"
DEFAULT_OUT = Path("/tmp/corpus-index.json")

# Minimal Sweep Boundary Log highlights (arxiv-sweep-findings SKILL.md table).
# Not a full census — notable HIGH/MED IDs named in the log body.
BOUNDARY_LOG: list[dict[str, str]] = [
    {
        "arxiv_id": "2608.24188",
        "title": "Paritok intent-conditioned extractive compress",
        "sweep_source": "arxiv-sweep-findings:28",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "compression.intent_conditioned_offload",
    },
    {
        "arxiv_id": "2608.26263",
        "title": "SKILL.state mutable execution state",
        "sweep_source": "arxiv-sweep-findings:29",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "skill-state",
    },
    {
        "arxiv_id": "2608.27454",
        "title": "WikiSkill co-evolving skill wiki",
        "sweep_source": "arxiv-sweep-findings:29",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "skill-wiki",
    },
    {
        "arxiv_id": "2608.23565",
        "title": "ReWorld",
        "sweep_source": "arxiv-sweep-findings:24",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "agent-memory-consolidation",
    },
    {
        "arxiv_id": "2609.08180",
        "title": "Minimal-sufficient profiles",
        "sweep_source": "arxiv-sweep-findings:33",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "agent-memory-consolidation",
    },
    {
        "arxiv_id": "2609.09115",
        "title": "MeClear attribution clearance",
        "sweep_source": "arxiv-sweep-findings:33",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "agent-memory-consolidation",
    },
    {
        "arxiv_id": "2606.10209",
        "title": "Context engineering",
        "sweep_source": "arxiv-sweep-findings:33",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "hermes-context-hygiene",
    },
    {
        "arxiv_id": "2609.08033",
        "title": "Prospect-state",
        "sweep_source": "arxiv-sweep-findings:33",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "dispatching-parallel-agents",
    },
    {
        "arxiv_id": "2609.09153",
        "title": "Procedural graphs",
        "sweep_source": "arxiv-sweep-findings:33",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "autonomous-agent-loop-design",
    },
    {
        "arxiv_id": "2609.08472",
        "title": "Cross-substrate authority",
        "sweep_source": "arxiv-sweep-findings:33",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "trajectory-risk-guardrail",
    },
    {
        "arxiv_id": "2609.09150",
        "title": "Sweep 33 highest ID found",
        "sweep_source": "arxiv-sweep-findings:33",
        "status": "logged",
        "priority": "HIGH",
        "target_skill": "arxiv-sweep-findings",
    },
    {
        "arxiv_id": "2609.00267",
        "title": "Delegation Without Trust",
        "sweep_source": "arxiv-sweep-findings:31",
        "status": "applied",
        "priority": "HIGH",
        "target_skill": "delegation",
    },
]


def _norm_id(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower().startswith("arxiv:"):
        text = text[6:]
    return text.strip()


def _priority_from_status(status: str, explicit: Any = None) -> str:
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    s = (status or "").upper()
    if s in {"SPIKE", "HIGH", "SYSTEMS_APPLICABLE"}:
        return "HIGH"
    if s in {"MED", "MEDIUM", "OPTIMIZATION", "REVIEW", "CHAIN"}:
        return "MED"
    if s in {"SKIP", "LOW"}:
        return "SKIP"
    return s or "unknown"


def _entry(
    arxiv_id: str,
    title: str,
    sweep_source: str,
    status: str,
    priority: str,
    target_skill: str,
) -> dict[str, str]:
    return {
        "arxiv_id": arxiv_id,
        "title": title or "",
        "sweep_source": sweep_source,
        "status": status or "",
        "priority": priority or "",
        "target_skill": (target_skill or "")[:200],
    }


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        print(f"[corpus-index] WARN: failed to read {path}: {exc}", file=sys.stderr)
        return None


def _iter_records(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    records: list[dict[str, Any]] = []
    for key in ("papers", "items", "spikes", "optimizations", "findings", "results"):
        val = payload.get(key)
        if isinstance(val, list):
            records.extend(x for x in val if isinstance(x, dict))
    if not records and (payload.get("id") or payload.get("arxiv_id")):
        records.append(payload)
    return records


def _from_interp(rec: dict[str, Any], sweep_source: str) -> dict[str, str] | None:
    arxiv_id = _norm_id(rec.get("arxiv_id") or rec.get("id") or rec.get("paper_id"))
    if not arxiv_id:
        return None
    status = str(
        rec.get("interpretation_type")
        or rec.get("status")
        or rec.get("verdict")
        or ""
    )
    target = rec.get("component_target") or rec.get("hermes_analogue") or rec.get("target_skill") or ""
    if isinstance(target, str) and len(target) > 80 and status.upper() == "SKIP":
        target = ""
    return _entry(
        arxiv_id=arxiv_id,
        title=str(rec.get("title") or rec.get("paper_title") or ""),
        sweep_source=sweep_source,
        status=status,
        priority=_priority_from_status(status, rec.get("priority")),
        target_skill=str(target),
    )


def consolidate(out_path: Path = DEFAULT_OUT) -> dict[str, Any]:
    by_id: dict[str, dict[str, str]] = {}
    sources_used: list[str] = ["arxiv-sweep-findings:boundary-log"]

    for rec in BOUNDARY_LOG:
        aid = _norm_id(rec["arxiv_id"])
        if aid:
            by_id[aid] = dict(rec)

    cs = _load_json(CS_PATH)
    if cs is not None:
        sources_used.append(str(CS_PATH))
        for rec in _iter_records(cs):
            entry = _from_interp(rec, "cs-interpretation")
            if not entry:
                continue
            existing = by_id.get(entry["arxiv_id"])
            if existing:
                # Boundary-log / prior source wins identity; fill empty fields.
                for field in ("title", "status", "priority", "target_skill"):
                    if not existing.get(field) and entry.get(field):
                        existing[field] = entry[field]
                if existing.get("sweep_source") and "cs-interpretation" not in existing["sweep_source"]:
                    existing["sweep_source"] = f"{existing['sweep_source']}+cs-interpretation"
            else:
                by_id[entry["arxiv_id"]] = entry

    math = _load_json(MATH_PATH)
    if math is not None:
        sources_used.append(str(MATH_PATH))
        for rec in _iter_records(math):
            entry = _from_interp(rec, "math-interpretation")
            if not entry:
                continue
            existing = by_id.get(entry["arxiv_id"])
            if existing:
                for field in ("title", "status", "priority", "target_skill"):
                    if not existing.get(field) and entry.get(field):
                        existing[field] = entry[field]
                if "math-interpretation" not in existing.get("sweep_source", ""):
                    existing["sweep_source"] = f"{existing['sweep_source']}+math-interpretation"
            else:
                by_id[entry["arxiv_id"]] = entry

    findings = [by_id[k] for k in sorted(by_id.keys())]
    payload = {
        "schema": "hermes-corpus-index/v1",
        "count": len(findings),
        "sources": sources_used,
        "findings": findings,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    payload = consolidate(out)
    print(f"[corpus-index] wrote {payload['count']} findings -> {out}")
    print(f"[corpus-index] sources: {', '.join(payload['sources'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
