#!/usr/bin/env python3
"""
memory-buffer-flush.py — Infini Memory write-buffer management.

Based on:
  - arXiv:2606.10677 (Infini Memory): stage writes to buffer, consolidate into topic docs
  - arXiv:2601.02428 (ARM): frequency-protected remembrance with decay scoring

Manages ~/.hermes/memory/buffer.md (append-only write staging) and
~/.hermes/memory/topics/<slug>.md (consolidated topic files).

Usage:
  python3 memory-buffer-flush.py --append "fact text" --source session  # stage a new fact
  python3 memory-buffer-flush.py --flush                                  # cluster + merge to topics
  python3 memory-buffer-flush.py --stats                                  # buffer line count + ARM scores
  python3 memory-buffer-flush.py --decay                                  # apply ARM decay, cold-store low scorers
"""
import argparse, json, os, pathlib, re, sys, time
from collections import defaultdict

HERMES_HOME = pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes")))
MEMORY_DIR = HERMES_HOME / "memory"
BUFFER_PATH = MEMORY_DIR / "buffer.md"
TOPICS_DIR = MEMORY_DIR / "topics"
COLD_DIR = MEMORY_DIR / "cold"
ARM_STATE_PATH = HERMES_HOME / "cache" / "arm-memory-state.json"

BUFFER_MAX_LINES = 200
DECAY_TAU = 0.1            # Decay threshold: score below this → cold storage
DECAY_PROTECTED_TYPES = {"SAFETY", "CONSTRAINT", "DECISION"}


# ── ARM state helpers ──────────────────────────────────────────────────────────

def load_arm_state() -> dict:
    if ARM_STATE_PATH.exists():
        try:
            return json.loads(ARM_STATE_PATH.read_text())
        except Exception:
            pass
    return {}


def save_arm_state(state: dict) -> None:
    ARM_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARM_STATE_PATH.write_text(json.dumps(state, indent=2))


def arm_score(entry: dict) -> float:
    """
    ARM decay score = hits / (1 + days_since_last_hit).
    Protected entries and SAFETY/CONSTRAINT types always score >= 1.0.
    """
    if entry.get("protected") or entry.get("type") in DECAY_PROTECTED_TYPES:
        return 1.0
    hits = entry.get("hits", 0)
    last_hit = entry.get("last_hit", 0.0)
    days_since = (time.time() - last_hit) / 86400.0
    return hits / (1.0 + days_since)


def record_hit(slug: str) -> None:
    """Increment hit counter for an ARM entry."""
    state = load_arm_state()
    entry = state.get(slug, {"hits": 0, "last_hit": 0.0, "protected": False, "type": "general"})
    entry["hits"] = entry.get("hits", 0) + 1
    entry["last_hit"] = time.time()
    state[slug] = entry
    save_arm_state(state)


# ── Buffer operations ──────────────────────────────────────────────────────────

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def cmd_append(fact_text: str, source: str, fact_type: str = "general") -> None:
    """Append a new fact to the buffer."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    BUFFER_PATH.touch(exist_ok=True)

    lines = BUFFER_PATH.read_text(errors="replace").splitlines()
    if len(lines) >= BUFFER_MAX_LINES:
        print(f"[memory-buffer] Buffer at {len(lines)}/{BUFFER_MAX_LINES} lines — run --flush first",
              file=sys.stderr)

    entry_line = f"- [{_now_iso()}] [src:{source}] [type:{fact_type}] {fact_text.strip()}"
    with BUFFER_PATH.open("a") as f:
        f.write(entry_line + "\n")
    print(f"Appended to buffer ({len(lines)+1} lines).")


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:40]


def _cluster_lines(lines: list[str]) -> dict[str, list[str]]:
    """
    Naive clustering: group by first meaningful keyword (first noun/verb after metadata).
    Returns {slug: [lines]}.
    """
    clusters: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        # Strip metadata prefix
        clean = re.sub(r"^-\s+\[.*?\]\s*\[.*?\]\s*\[.*?\]\s*", "", line).strip()
        if not clean:
            continue
        # First word as cluster key
        first_word = re.sub(r"[^a-z0-9]", "", clean.split()[0].lower()) if clean.split() else "misc"
        if len(first_word) < 3:
            first_word = "misc"
        clusters[first_word[:20]].append(line)
    return dict(clusters)


def cmd_flush() -> None:
    """Cluster buffer lines, merge into topic files, clear buffer."""
    if not BUFFER_PATH.exists():
        print("Buffer is empty.")
        return

    raw = BUFFER_PATH.read_text(errors="replace")
    lines = [l for l in raw.splitlines() if l.strip()]
    if not lines:
        print("Buffer is empty.")
        return

    TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    clusters = _cluster_lines(lines)
    flushed = 0

    for slug, cluster_lines in clusters.items():
        topic_path = TOPICS_DIR / f"{slug}.md"
        header = f"# {slug.replace('-', ' ').title()}\n\n"
        if not topic_path.exists():
            topic_path.write_text(header)

        existing = topic_path.read_text(errors="replace")
        # Mark superseded entries (same slug, contradicted by negation or new value)
        new_entries = []
        for line in cluster_lines:
            clean = re.sub(r"^-\s+\[.*?\]\s*", "", line).strip()
            # Check for explicit supersession markers
            is_supersession = bool(re.search(r'\bno longer\b|\bnot anymore\b|\bupdated to\b', clean, re.I))
            new_entries.append(line)
            if is_supersession:
                new_entries[-1] += "  <!-- supersedes previous -->"
            flushed += 1

        with topic_path.open("a") as f:
            f.write("\n".join(new_entries) + "\n")

        # Update ARM state for this topic
        arm_state = load_arm_state()
        if slug not in arm_state:
            arm_state[slug] = {"hits": 0, "last_hit": time.time(), "protected": False, "type": "general"}
        save_arm_state(arm_state)

    # Clear buffer
    BUFFER_PATH.write_text("")
    print(f"Flushed {flushed} lines across {len(clusters)} topic(s). Buffer cleared.")


def cmd_stats() -> None:
    """Show buffer line count and ARM scores."""
    lines = BUFFER_PATH.read_text(errors="replace").splitlines() if BUFFER_PATH.exists() else []
    print(f"Buffer: {len(lines)}/{BUFFER_MAX_LINES} lines")

    arm_state = load_arm_state()
    if arm_state:
        print("\nARM scores (topics):")
        scored = [(slug, arm_score(entry)) for slug, entry in arm_state.items()]
        scored.sort(key=lambda x: -x[1])
        for slug, score in scored[:20]:
            status = "PROTECTED" if arm_state[slug].get("protected") else f"score={score:.3f}"
            print(f"  {slug:<35} {status}")
    else:
        print("ARM state: empty (no topics flushed yet)")


def cmd_decay() -> None:
    """Apply ARM decay: cold-store topics with score below DECAY_TAU."""
    arm_state = load_arm_state()
    if not arm_state:
        print("ARM state empty.")
        return

    COLD_DIR.mkdir(parents=True, exist_ok=True)
    demoted = []
    for slug, entry in arm_state.items():
        if arm_score(entry) < DECAY_TAU and not entry.get("protected"):
            topic_path = TOPICS_DIR / f"{slug}.md"
            cold_path = COLD_DIR / f"{slug}.md"
            if topic_path.exists():
                topic_path.rename(cold_path)
                demoted.append(slug)

    if demoted:
        print(f"Cold-stored {len(demoted)} topics: {', '.join(demoted)}")
    else:
        print(f"No topics below decay threshold τ={DECAY_TAU}.")
    save_arm_state(arm_state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Infini Memory + ARM buffer manager")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--append", metavar="TEXT", help="Append fact to buffer")
    group.add_argument("--flush", action="store_true", help="Cluster buffer + merge to topics")
    group.add_argument("--stats", action="store_true", help="Buffer stats + ARM scores")
    group.add_argument("--decay", action="store_true", help="Apply ARM decay, cold-store low scorers")
    parser.add_argument("--source", default="session", help="Source label for --append")
    parser.add_argument("--type", default="general", dest="fact_type",
                        help="Fact type: SAFETY|CONSTRAINT|DECISION|general")
    args = parser.parse_args()

    if args.append:
        cmd_append(args.append, args.source, args.fact_type)
    elif args.flush:
        cmd_flush()
    elif args.stats:
        cmd_stats()
    elif args.decay:
        cmd_decay()


if __name__ == "__main__":
    main()
