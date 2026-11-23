#!/usr/bin/env python3
"""Propose harness-skill updates from session summaries.

Strips task-specific artifacts, clusters remaining text by keyword overlap,
and emits proposed harness updates only when a cluster has >=3 similar
task completions. Does not apply patches.

Usage:
    python3 evo-harness-compile.py SESSION_SUMMARY [SESSION_SUMMARY ...]
    python3 evo-harness-compile.py --min-cluster 3 --json path/a.md path/b.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "were", "was",
    "are", "been", "have", "has", "had", "but", "not", "you", "your",
    "into", "onto", "over", "under", "then", "than", "also", "just",
    "after", "before", "when", "what", "which", "while", "where",
    "task", "session", "agent", "hermes", "file", "files", "used",
    "using", "use", "did", "does", "done", "ran", "run", "via",
}

ARTIFACT_RES = [
    re.compile(r"`[^`]{1,200}`"),
    re.compile(r"https?://\S+"),
    re.compile(r"\b[0-9a-f]{8,}\b", re.I),
    re.compile(r"(?:/var/home|/home|~)/[^\s,;:]+"),
    re.compile(r"\b(?:session|run|job)[_-][A-Za-z0-9._-]+\b", re.I),
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?\b"),
    re.compile(r"\barXiv:\d{4}\.\d{4,5}(?:v\d+)?\b", re.I),
    re.compile(r"```[\s\S]*?```"),
]


def strip_artifacts(text: str) -> str:
    cleaned = text
    for pat in ARTIFACT_RES:
        cleaned = pat.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def keywords(text: str) -> set[str]:
    tokens = re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower())
    return {t for t in tokens if t not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass
class Summary:
    path: str
    raw: str
    stripped: str
    kws: set[str]


@dataclass
class Cluster:
    members: list[Summary] = field(default_factory=list)
    centroid: set[str] = field(default_factory=set)

    def add(self, item: Summary) -> None:
        self.members.append(item)
        counts: Counter[str] = Counter()
        for m in self.members:
            counts.update(m.kws)
        # Keep tokens that appear in at least half the members (ceil).
        thresh = max(1, (len(self.members) + 1) // 2)
        self.centroid = {t for t, n in counts.items() if n >= thresh}


def cluster_summaries(items: list[Summary], threshold: float) -> list[Cluster]:
    clusters: list[Cluster] = []
    for item in items:
        best_i = -1
        best_sim = threshold
        for i, cl in enumerate(clusters):
            sim = jaccard(item.kws, cl.centroid or (cl.members[0].kws if cl.members else set()))
            if sim >= best_sim:
                best_sim = sim
                best_i = i
        if best_i >= 0:
            clusters[best_i].add(item)
        else:
            cl = Cluster()
            cl.add(item)
            clusters.append(cl)
    return clusters


def propose(cluster: Cluster) -> dict:
    topic_tokens = sorted(cluster.centroid, key=len, reverse=True)[:8]
    topic = " ".join(topic_tokens[:4]) or "untitled-cluster"
    lesson = (
        f"Cluster of {len(cluster.members)} similar completions on '{topic}'. "
        "Consider adding a named recipe or pitfall to the harness skill covering "
        "the shared procedure; keep task-specific paths out of the skill body."
    )
    return {
        "topic": topic,
        "size": len(cluster.members),
        "keywords": topic_tokens,
        "sources": [m.path for m in cluster.members],
        "proposed_update": lesson,
        "apply": False,
    }


def load_summary(path: Path) -> Summary:
    raw = path.read_text(encoding="utf-8", errors="replace")
    stripped = strip_artifacts(raw)
    return Summary(path=str(path), raw=raw, stripped=stripped, kws=keywords(stripped))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Propose harness updates from clustered session summaries (no auto-apply)."
    )
    p.add_argument("summaries", nargs="+", type=Path, help="Session summary files")
    p.add_argument("--min-cluster", type=int, default=3, help="Minimum completions per cluster (default 3)")
    p.add_argument("--threshold", type=float, default=0.25, help="Jaccard overlap to join a cluster")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = p.parse_args(argv)

    items: list[Summary] = []
    errors: list[str] = []
    for path in args.summaries:
        if not path.is_file():
            errors.append(f"missing: {path}")
            continue
        items.append(load_summary(path))

    if not items:
        print("No readable session summaries.", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 2

    clusters = cluster_summaries(items, args.threshold)
    proposals = [propose(c) for c in clusters if len(c.members) >= args.min_cluster]
    skipped = [
        {"size": len(c.members), "sources": [m.path for m in c.members]}
        for c in clusters
        if len(c.members) < args.min_cluster
    ]

    payload = {
        "input_count": len(items),
        "cluster_count": len(clusters),
        "min_cluster": args.min_cluster,
        "proposals": proposals,
        "below_threshold": skipped,
        "errors": errors,
        "auto_apply": False,
        "note": "Proposals only. Do not patch a harness skill from this output without human review.",
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"summaries={payload['input_count']} clusters={payload['cluster_count']} "
          f"proposals={len(proposals)} (min_cluster={args.min_cluster})")
    if not proposals:
        print("No cluster reached the completion threshold. No harness update proposed.")
    for i, prop in enumerate(proposals, 1):
        print(f"\n[{i}] topic={prop['topic']} n={prop['size']}")
        print(f"    sources: {', '.join(prop['sources'])}")
        print(f"    proposed: {prop['proposed_update']}")
        print("    apply: no")
    if skipped:
        print(f"\nbelow threshold: {len(skipped)} cluster(s)")
    if errors:
        print("errors:")
        for e in errors:
            print(f"  {e}")
    print("\nDo not auto-apply. Human-gate any harness skill patch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
