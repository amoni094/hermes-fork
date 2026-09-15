#!/usr/bin/env python3
"""
kg-contradiction-check.py — Lightweight KG contradiction detector (M3).
Checks if a new fact contradicts an existing fact for the same entity.
Standalone utility; wire into l1-graphiti-write.py as a pre-write check.

Usage: python3 kg-contradiction-check.py --entity "entity name" --new-text "new fact" --old-text "existing fact"
"""
import argparse
import sys

OPPOSITION_PAIRS = [
    ("enabled", "disabled"),
    ("active", "inactive"),
    ("connected", "disconnected"),
    ("running", "stopped"),
    ("true", "false"),
    ("on", "off"),
    ("open", "closed"),
    ("valid", "invalid"),
    ("present", "absent"),
    ("installed", "uninstalled"),
]


def check_contradiction(entity_key: str, old_text: str, new_text: str) -> bool:
    """Return True if old_text and new_text contain opposing polarity terms for same entity."""
    old_lower = old_text.lower()
    new_lower = new_text.lower()
    for a, b in OPPOSITION_PAIRS:
        if (a in old_lower and b in new_lower) or (b in old_lower and a in new_lower):
            print(
                f"CONTRADICTION detected: entity={entity_key} "
                f"old={old_text[:70]!r} new={new_text[:70]!r}"
            )
            return True
    return False


def extract_entity_key(text: str) -> str:
    """Extract first 3 significant words as entity key."""
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "has", "have", "had",
        "be", "been", "being", "in", "on", "at", "to", "for", "of", "and",
        "or", "but", "with", "from", "that", "this", "it", "its",
    }
    punct = ".,;:!?\"'()[]{}"
    words = [w.strip(punct) for w in text.split()]
    sig = [w for w in words if w.lower() not in stopwords and len(w) > 2]
    return " ".join(sig[:3]).lower()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KG contradiction checker")
    parser.add_argument("--entity", help="Entity key (auto-extracted if omitted)")
    parser.add_argument("--new-text", required=True, help="New fact text")
    parser.add_argument("--old-text", required=True, help="Existing fact text")
    args = parser.parse_args()

    entity = args.entity or extract_entity_key(args.new_text)
    contradiction = check_contradiction(entity, args.old_text, args.new_text)
    sys.exit(1 if contradiction else 0)
