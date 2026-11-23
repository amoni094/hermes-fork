#!/usr/bin/env python3
"""
save-primer-batch.py

Call this with the raw text output from a primer subagent.
Detects the category from the PRIMER: line and saves to the right file.

Usage: echo "<primer text>" | python3 save-primer-batch.py
   or: python3 save-primer-batch.py < primer.txt

Also accepts --cat <cat_key> to override detection.
"""
import sys, re
from pathlib import Path

PRIMERS_DIR = Path("~/.hermes/cache/research/primers").expanduser()
PRIMERS_DIR.mkdir(parents=True, exist_ok=True)

SKILL_REFS_DIR = Path("~/.hermes/skills/research/hermes-research/references").expanduser()
SKILL_REFS_DIR.mkdir(parents=True, exist_ok=True)

TITLE_TO_KEY = {
    "Information Theory": "information_theory",
    "Online Learning": "online_learning",
    "Bandits": "online_learning",
    "Generalization Theory": "generalization_theory",
    "Game Theory": "game_theory",
    "Mechanism Design": "game_theory",
    "Stochastic Processes": "stochastic_causal",
    "MDPs": "stochastic_causal",
    "Causal Inference": "stochastic_causal",
    "Multi-Agent Systems Theory": "multiagent_systems_theory",
    "Reinforcement Learning Theory": "rl_theory_comprehensive",
}

def detect_cat(text):
    m = re.match(r"PRIMER:\s*(.+)", text.split('\n')[0])
    if not m:
        return None
    title = m.group(1).strip()
    for keyword, key in TITLE_TO_KEY.items():
        if keyword.lower() in title.lower():
            return key
    # fallback: slugify title
    slug = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
    return slug

def main():
    text = sys.stdin.read().strip()
    if not text:
        print("No input", file=sys.stderr)
        sys.exit(1)
    cat = detect_cat(text)
    if not cat:
        print(f"Could not detect category from: {text[:100]}", file=sys.stderr)
        sys.exit(1)
    out = PRIMERS_DIR / f"{cat}.txt"
    out.write_text(text)
    ref = SKILL_REFS_DIR / f"primer-{cat}.txt"
    ref.write_text(text)
    print(f"Saved {cat}: {len(text)} chars -> {out}")
    print(f"Skill ref: {ref}")

if __name__ == "__main__":
    main()
