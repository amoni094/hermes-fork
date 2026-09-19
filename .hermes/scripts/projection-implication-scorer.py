#!/usr/bin/python3
"""
projection-implication-scorer.py

Content-addressable skill retrieval using projection-based similarity:
scores skill candidates by their geometric projection onto the query vector
in a keyword embedding space, enabling retrieval that respects implication
structure (if A implies B, queries for A should also retrieve B).

Math basis (lattice_theory / order_theory): the implication ordering on a
Boolean lattice gives rise to a partial order where A <= B iff A implies B.
Projection onto a query vector in the lattice's metric embedding respects
this order: proj(A, q) >= proj(B, q) whenever A <= B and q is aligned with A.

For Hermes skill routing:
  - Skills = points in a keyword-frequency vector space
  - Query = keyword vector from user request
  - Score = cosine similarity (projection angle)
  - Implication bonus: if skill A's keywords are a superset of skill B's,
    queries matching B also match A (upward closure in the lattice)
  - Result: ranked skill list with implication-aware boosting

Unlike the hermes skill router (which uses exact name matching or embedding
recall), this operates purely on keyword overlap + implication structure,
with no LLM call required.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

HOME      = Path.home()
SKILLS_DIR = HOME / ".hermes/skills"
CACHE_DIR  = _HH / "cache" / "monitors"
OUT_FILE   = CACHE_DIR / "projection-skill-index.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MIN_SCORE = 0.05   # minimum cosine score to include in results
TOP_K     = 15


def _load_skills() -> dict[str, str]:
    """Load skill name → description text."""
    skills: dict[str, str] = {}
    for skill_dir in SKILLS_DIR.rglob("SKILL.md"):
        try:
            text = skill_dir.read_text()
            # Extract description from frontmatter
            m = re.search(r"description:\s*['\"]?(.+?)['\"]?\n", text)
            desc = m.group(1) if m else ""
            # Also grab first paragraph of body
            body = text.split("---", 2)[-1].strip()
            first_para = body.split("\n\n")[0].replace("#", "").strip()
            name = skill_dir.parent.name
            skills[name] = f"{desc} {first_para}"
        except Exception:
            pass
    return skills


def _keyword_vec(text: str, vocab: dict[str, int]) -> np.ndarray:
    """TF-IDF-lite: term frequency vector over shared vocabulary."""
    words = re.findall(r"[a-z]{3,}", text.lower())
    counts = Counter(words)
    vec = np.zeros(len(vocab))
    for w, c in counts.items():
        if w in vocab:
            vec[vocab[w]] = c
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _build_vocab(skill_texts: dict[str, str]) -> dict[str, int]:
    """Build vocabulary from all skill texts."""
    word_counts: Counter = Counter()
    for text in skill_texts.values():
        word_counts.update(re.findall(r"[a-z]{3,}", text.lower()))
    # Keep words appearing in at least 2 skills but not too common
    vocab_words = [w for w, c in word_counts.items() if 2 <= c <= len(skill_texts) * 0.8]
    return {w: i for i, w in enumerate(vocab_words)}


def _implication_bonus(skill_a: str, skill_b: str,
                        skill_vecs: dict[str, np.ndarray]) -> float:
    """
    Bonus for A if A's keyword set implies B's (A is more specific).
    A implies B if A's non-zero indices are a superset of B's non-zero indices.
    """
    va = skill_vecs[skill_a]
    vb = skill_vecs[skill_b]
    a_nonzero = set(np.where(va > 0)[0])
    b_nonzero = set(np.where(vb > 0)[0])
    if not b_nonzero:
        return 0.0
    overlap = len(a_nonzero & b_nonzero) / len(b_nonzero)
    return overlap * 0.1  # small bonus, don't overwhelm cosine score


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """Retrieve and rank skills for a query using projection scoring."""
    skills = _load_skills()
    if not skills:
        return []

    vocab = _build_vocab(skills)
    if not vocab:
        return []

    skill_vecs = {name: _keyword_vec(text, vocab) for name, text in skills.items()}
    query_vec  = _keyword_vec(query, vocab)

    if np.linalg.norm(query_vec) == 0:
        return []

    # Cosine similarities
    scores: dict[str, float] = {}
    for name, vec in skill_vecs.items():
        cos = float(np.dot(query_vec, vec))
        scores[name] = cos

    # Implication bonus: boost skills that imply highly-scoring skills
    top_scores = sorted(scores.items(), key=lambda x: -x[1])[:5]
    for candidate in list(scores.keys()):
        for top_skill, _ in top_scores:
            if candidate != top_skill and top_skill in skill_vecs:
                scores[candidate] += _implication_bonus(candidate, top_skill, skill_vecs)

    ranked = sorted(
        [(name, score) for name, score in scores.items() if score >= MIN_SCORE],
        key=lambda x: -x[1]
    )[:top_k]

    return [
        {"skill": name, "score": round(score, 4), "description": skills[name][:80]}
        for name, score in ranked
    ]


def run(query: str, dry_run: bool = False) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    results = retrieve(query)
    print(f"\n=== Projection Implication Scorer ===")
    print(f"Query: '{query}'")
    print(f"Skills indexed: {len(_load_skills())}")
    print(f"Results (top {len(results)}):")
    print(f"\n  {'Score':>6}  Skill")
    print("  " + "-" * 55)
    for r in results:
        print(f"  {r['score']:>6.4f}  {r['skill']}")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "query": query, "results": results
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Projection-implication skill scorer")
    parser.add_argument("query", nargs="?", default="research arxiv math sweep",
                        help="Query string to score skills against")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(query=args.query, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
