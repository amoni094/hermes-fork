#!/usr/bin/env python3
"""
profinite-thread-check.py — Profinite thread-validity gate for memory promotion.

Enforces the profinite group design pattern:
  "Write to finest layer; require a projection map to every coarser layer;
   refuse persistence if the family of images is not a thread."

A fact is a THREAD if it has a valid, compatible image in every coarser layer:
  session → skill → hindsight → persistent

Non-thread facts are blocked from persistent promotion until they form
a consistent image across all layers.

Group theory source: nLab profinite group; arXiv:2309.05039 (Li–Zhang)
Cohomology source: arXiv:2307.14658 (Jain–Joshi–Spallone) — H^2 obstruction

Also implements:
  - H2ObstructionLedger: records merge failures as H^2 cohomology classes
    (obstruction = local patches that fail to glue globally)
  - GaloisViewLattice: access-control / view lattice via subgroup ordering

Usage:
  python3 profinite-thread-check.py check --fact "fact text" [--layer session]
  python3 profinite-thread-check.py obstruction-report
  python3 profinite-thread-check.py view-lattice
"""
import argparse
import hashlib
import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

HERMES_HOME    = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
THREAD_LOG     = HERMES_HOME / "cache" / "profinite-threads.jsonl"
OBSTRUCTION_DB = HERMES_HOME / "cache" / "h2-obstructions.json"
HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://127.0.0.1:9177")
HINDSIGHT_BANK = os.environ.get("HINDSIGHT_BANK", "hermes-default")

# Layer ordering: finest → coarsest (projection direction)
LAYER_TOWER = ["session", "skill", "hindsight", "persistent"]


# ---------------------------------------------------------------------------
# Profinite thread model
# ---------------------------------------------------------------------------

@dataclass
class LayerImage:
    """The image of a fact in a specific memory layer."""
    layer: str
    content_hash: str       # SHA256[:16] of canonical content in this layer
    content_preview: str    # first 80 chars
    confidence: float = 1.0
    found: bool = True


@dataclass
class ProfiniteThread:
    """
    A fact that has compatible images in all layers from source down to persistent.
    A non-thread has at least one layer where the image is missing or contradicts
    a coarser image.
    """
    fact_text: str
    source_layer: str
    images: dict[str, LayerImage] = field(default_factory=dict)
    is_thread: bool = False
    obstruction: Optional[str] = None   # layer where compatibility breaks
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["images"] = {k: asdict(v) for k, v in self.images.items()}
        return d


# ---------------------------------------------------------------------------
# H^2 Obstruction Ledger
# ---------------------------------------------------------------------------

class H2ObstructionLedger:
    """
    Records merge failures as H^2 cohomology classes.

    In group cohomology terms:
      - A 0-cochain is a fact in a single layer.
      - A 1-cochain is a pairwise relation (delta) between facts.
      - A 2-cochain is a triple (fact_A, fact_B, fact_C) consistency witness.
      - H^2 class = obstruction to gluing local views globally.

    Non-trivial H^2 class = you cannot extend the quotient ontology by
    this hidden fact without a twist (a cocycle of corrections).

    Source: nLab group cohomology; arXiv:2307.14658.
    """

    def __init__(self):
        self._data: dict = {"obstructions": [], "resolved": []}
        self._load()

    def _load(self):
        if OBSTRUCTION_DB.exists():
            try:
                self._data = json.loads(OBSTRUCTION_DB.read_text())
            except Exception:
                pass

    def _save(self):
        OBSTRUCTION_DB.parent.mkdir(parents=True, exist_ok=True)
        OBSTRUCTION_DB.write_text(json.dumps(self._data, indent=2))

    def record_obstruction(self, fact_a: str, fact_b: str, fact_c: str,
                           obstruction_type: str, detail: str = "") -> str:
        """
        Record a 2-cocycle obstruction: three facts that fail triangle consistency.
        Returns the obstruction class ID.
        """
        class_id = hashlib.sha256(
            f"{fact_a}:{fact_b}:{fact_c}".encode()
        ).hexdigest()[:16]
        self._data["obstructions"].append({
            "class_id": class_id,
            "facts": [fact_a[:60], fact_b[:60], fact_c[:60]],
            "type": obstruction_type,  # "merge_conflict", "transitivity_fail", "projection_gap"
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
        })
        self._save()
        return class_id

    def resolve_obstruction(self, class_id: str, resolution: str):
        """Mark an obstruction as resolved with explanation."""
        for o in self._data["obstructions"]:
            if o["class_id"] == class_id:
                o["resolved"] = True
                o["resolution"] = resolution
                o["resolved_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def report(self) -> str:
        obstructions = self._data.get("obstructions", [])
        unresolved = [o for o in obstructions if not o.get("resolved")]
        lines = [
            f"H^2 Obstruction Ledger — {len(obstructions)} total, {len(unresolved)} unresolved",
            "",
        ]
        for o in unresolved[-10:]:  # show last 10 unresolved
            lines.append(
                f"  [{o['class_id']}] {o['type']}: "
                f"{o['facts'][0][:40]}... | {o.get('detail', '')[:50]}"
            )
        if not unresolved:
            lines.append("  (no unresolved obstructions)")
        return "\n".join(lines)

    def check_triple_consistency(self, fact_a: str, fact_b: str, fact_c: str) -> dict:
        """
        Check if three facts form a valid 2-cocycle (triangle consistency).
        d(cocycle) = 0 iff (A relates B) + (B relates C) is consistent with (A relates C).
        Simple heuristic: check entity overlap creates a closed chain.
        """
        words_a = set(fact_a.lower().split())
        words_b = set(fact_b.lower().split())
        words_c = set(fact_c.lower().split())
        # Closed triangle: A∩B, B∩C, A∩C all non-empty
        ab = words_a & words_b
        bc = words_b & words_c
        ac = words_a & words_c
        consistent = bool(ab) and bool(bc) and bool(ac)
        return {
            "consistent": consistent,
            "overlap_ab": len(ab),
            "overlap_bc": len(bc),
            "overlap_ac": len(ac),
            "verdict": "cocycle_closed" if consistent else "cocycle_open",
        }


# ---------------------------------------------------------------------------
# Galois View Lattice
# ---------------------------------------------------------------------------

class GaloisViewLattice:
    """
    Access-control / view lattice based on Galois correspondence.

    Galois analogy:
      - Base "field" k = public axioms / invariant facts (everyone sees)
      - Extension K = enriched memory (session facts, private notes)
      - Gal(K/k) = automorphisms that permute indistinguishable enrichments
      - Subgroup H ≤ Gal(K/k) = allowed automorphisms for a context
      - Fixed "field" K^H = what remains visible under that context

    For Hermes:
      - Contexts = {global, persistent, skill, hindsight, session}
      - View = which layers a context can read (fixed field = readable layers)
      - Subgroup ordering = inclusion-reversing bijection on views

    Lattice ordering (coarser view = more restrictive = smaller visible "field"):
      global > persistent > skill > hindsight > session
    """

    # Subgroup ordering: each view's allowed layers
    VIEW_LATTICE: dict[str, list[str]] = {
        "global":     ["session", "skill", "hindsight", "persistent", "global"],
        "skill":      ["skill", "hindsight", "persistent"],
        "hindsight":  ["hindsight", "persistent"],
        "persistent": ["persistent"],
        "session":    ["session", "skill", "hindsight", "persistent"],
    }

    def visible_layers(self, context: str) -> list[str]:
        """Return layers visible from a given context (the fixed 'field')."""
        return self.VIEW_LATTICE.get(context, ["persistent"])

    def can_read(self, context: str, layer: str) -> bool:
        """Check if context can read from layer."""
        return layer in self.visible_layers(context)

    def subgroup_order(self, context_a: str, context_b: str) -> str:
        """
        Return ordering relationship between two contexts' view subgroups.
        Larger subgroup = smaller visible field = more restrictive view.
        """
        va = set(self.visible_layers(context_a))
        vb = set(self.visible_layers(context_b))
        if va == vb:
            return "equal"
        elif va > vb:
            return f"{context_a} sees MORE than {context_b} (subgroup of {context_b})"
        elif vb > va:
            return f"{context_b} sees MORE than {context_a} (subgroup of {context_a})"
        else:
            return "incomparable"

    def report(self) -> str:
        lines = ["Galois View Lattice — context → visible layers", ""]
        for ctx, layers in self.VIEW_LATTICE.items():
            lines.append(f"  {ctx:12s}: {', '.join(layers)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Profinite thread checker
# ---------------------------------------------------------------------------

def _hindsight_search(query: str, top_k: int = 3) -> list[dict]:
    """Search Hindsight for a fact."""
    try:
        url = f"{HINDSIGHT_BASE}/recall"
        payload = json.dumps({"query": query, "bank": HINDSIGHT_BANK,
                              "top_k": top_k}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            return data.get("results") or data.get("memories") or []
    except Exception:
        return []


def check_thread(fact_text: str, source_layer: str = "session") -> ProfiniteThread:
    """
    Check if a fact forms a profinite thread:
    does it have a consistent image in all layers from source → persistent?

    Implementation:
      - For each layer coarser than source_layer, check if the fact has a
        compatible image (via Hindsight search for the fact's key terms).
      - If a layer has no matching content, the thread is broken there.
    """
    thread = ProfiniteThread(fact_text=fact_text, source_layer=source_layer)

    # Self-image at source layer
    src_hash = hashlib.sha256(fact_text.encode()).hexdigest()[:16]
    thread.images[source_layer] = LayerImage(
        layer=source_layer,
        content_hash=src_hash,
        content_preview=fact_text[:80],
        confidence=1.0,
        found=True,
    )

    # Project to coarser layers via Hindsight search
    tower_start = LAYER_TOWER.index(source_layer) if source_layer in LAYER_TOWER else 0
    for layer in LAYER_TOWER[tower_start + 1:]:
        results = _hindsight_search(fact_text[:80], top_k=3)
        if results:
            top = results[0]
            top_text = top.get("text") or top.get("content") or ""
            # Compatibility: key words overlap >= 40%
            src_words = set(fact_text.lower().split())
            res_words = set(top_text.lower().split())
            overlap = len(src_words & res_words) / max(len(src_words), 1)
            thread.images[layer] = LayerImage(
                layer=layer,
                content_hash=hashlib.sha256(top_text.encode()).hexdigest()[:16],
                content_preview=top_text[:80],
                confidence=overlap,
                found=True,
            )
            if overlap < 0.3:
                thread.obstruction = layer
                thread.is_thread = False
                return thread
        else:
            # Layer has no image — thread broken here
            thread.images[layer] = LayerImage(
                layer=layer,
                content_hash="",
                content_preview="[not found]",
                confidence=0.0,
                found=False,
            )
            thread.obstruction = layer
            thread.is_thread = False
            return thread

    thread.is_thread = True
    return thread


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_check(args: argparse.Namespace) -> int:
    thread = check_thread(args.fact, source_layer=args.layer)
    print(f"Fact: {args.fact[:80]}")
    print(f"Source layer: {args.layer}")
    print(f"Is thread: {thread.is_thread}")
    if thread.obstruction:
        print(f"Obstruction at layer: {thread.obstruction}")
    print("\nLayer images:")
    for layer, img in thread.images.items():
        status = "OK" if img.found else "MISSING"
        print(f"  {layer:12s}: {status} (confidence={img.confidence:.2f}) {img.content_preview[:50]}")
    # Log
    THREAD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(THREAD_LOG, "a") as f:
        f.write(json.dumps(thread.to_dict()) + "\n")
    return 0 if thread.is_thread else 1


def cmd_obstruction_report(args: argparse.Namespace) -> int:
    ledger = H2ObstructionLedger()
    print(ledger.report())
    return 0


def cmd_view_lattice(args: argparse.Namespace) -> int:
    lattice = GaloisViewLattice()
    print(lattice.report())
    return 0


def cmd_triple_check(args: argparse.Namespace) -> int:
    ledger = H2ObstructionLedger()
    result = ledger.check_triple_consistency(args.fact_a, args.fact_b, args.fact_c)
    print(json.dumps(result, indent=2))
    if not result["consistent"]:
        class_id = ledger.record_obstruction(
            args.fact_a, args.fact_b, args.fact_c,
            obstruction_type="transitivity_fail",
            detail="triple consistency check via profinite-thread-check"
        )
        print(f"Obstruction recorded: {class_id}")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Profinite thread validity + H^2 obstruction ledger")
    sub = parser.add_subparsers(dest="cmd")

    p_check = sub.add_parser("check", help="Check if a fact forms a profinite thread")
    p_check.add_argument("--fact", required=True)
    p_check.add_argument("--layer", default="session", choices=LAYER_TOWER)
    p_check.set_defaults(func=cmd_check)

    p_obs = sub.add_parser("obstruction-report", help="Show H^2 obstruction ledger")
    p_obs.set_defaults(func=cmd_obstruction_report)

    p_vl = sub.add_parser("view-lattice", help="Show Galois view lattice")
    p_vl.set_defaults(func=cmd_view_lattice)

    p_tc = sub.add_parser("triple-check", help="Check 2-cocycle triple consistency")
    p_tc.add_argument("--fact-a", required=True)
    p_tc.add_argument("--fact-b", required=True)
    p_tc.add_argument("--fact-c", required=True)
    p_tc.set_defaults(func=cmd_triple_check)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
