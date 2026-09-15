#!/usr/bin/env python3
"""
canvas-offload.py — Mermaid canvas symbolic memory for Hermes sessions.

Implements the TencentDB Agent Memory short-term offload pattern locally:
- Reads tool output blobs from stdin OR a session's recent messages in state.db
- Writes raw content to refs/<node_id>.md
- Builds / updates a compact Mermaid canvas summarising task state
- Prints the canvas to stdout (for injection into context or inspection)

Usage:
  # Offload a specific tool output blob piped in:
  echo "big tool output" | python3 canvas-offload.py --session SESSION_ID --label "search:redis"

  # View current canvas for a session:
  python3 canvas-offload.py --session SESSION_ID --show

  # Rebuild canvas from all refs for a session:
  python3 canvas-offload.py --session SESSION_ID --rebuild

  # List all sessions with a canvas:
  python3 canvas-offload.py --list

Canvas lives at:  ~/.hermes/canvas/<session_id>/canvas.md
Refs live at:     ~/.hermes/canvas/<session_id>/refs/<node_id>.md
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
CANVAS_DIR = HERMES_HOME / "canvas"
STATE_DB = HERMES_HOME / "state.db"


# --------------------------------------------------------------------------- #
# Storage helpers
# --------------------------------------------------------------------------- #

def session_dir(session_id: str) -> Path:
    d = CANVAS_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "refs").mkdir(exist_ok=True)
    return d


def node_id(label: str, content: str) -> str:
    """Deterministic 6-char node id from label + content hash."""
    h = hashlib.sha256((label + content).encode()).hexdigest()[:6]
    slug = re.sub(r"[^a-z0-9]", "", label.lower())[:8]
    return f"{slug}_{h}"


def write_ref(session_id: str, nid: str, label: str, content: str) -> Path:
    ref_path = session_dir(session_id) / "refs" / f"{nid}.md"
    ref_path.write_text(
        f"# {label}\n\n> node_id: {nid}  |  captured: {datetime.now(timezone.utc).isoformat()}Z\n\n{content}\n",
        encoding="utf-8",
    )
    return ref_path


def load_canvas(session_id: str) -> dict:
    """Load existing canvas metadata (JSON sidecar) or return empty skeleton."""
    meta_path = session_dir(session_id) / "canvas.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return {"session_id": session_id, "nodes": [], "edges": []}


def save_canvas(session_id: str, canvas: dict):
    sdir = session_dir(session_id)
    meta_path = sdir / "canvas.json"
    meta_path.write_text(json.dumps(canvas, indent=2), encoding="utf-8")
    # Render Mermaid
    mmd = render_mermaid(canvas)
    (sdir / "canvas.md").write_text(mmd, encoding="utf-8")


def render_mermaid(canvas: dict) -> str:
    lines = ["```mermaid", "graph LR"]
    for n in canvas["nodes"]:
        label = n["label"].replace('"', "'")
        nid = n["node_id"]
        char_count = n.get("chars", 0)
        lines.append(f'  {nid}["{label}\\n▸{nid} ({char_count}c)"]')
    for e in canvas["edges"]:
        rel = e.get("rel", "→").replace('"', "'")
        lines.append(f'  {e["from"]} -->|"{rel}"| {e["to"]}')
    lines.append("```")
    lines.append(f"\n_Canvas updated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M')}Z_")
    lines.append(f"_Nodes: {len(canvas['nodes'])}  |  Refs: refs/<node_id>.md_")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_offload(session_id: str, label: str, content: str, rel: str | None, after: str | None):
    """Add one node to the canvas."""
    nid = node_id(label, content)
    ref_path = write_ref(session_id, nid, label, content)
    canvas = load_canvas(session_id)

    # Add node if new
    existing_ids = {n["node_id"] for n in canvas["nodes"]}
    if nid not in existing_ids:
        canvas["nodes"].append({
            "node_id": nid,
            "label": label,
            "chars": len(content),
            "ref": str(ref_path),
        })

    # Add edge if requested
    if after and rel:
        # Find or use the provided after node_id directly
        canvas["edges"].append({"from": after, "to": nid, "rel": rel})

    save_canvas(session_id, canvas)
    mmd = render_mermaid(canvas)
    print(mmd)
    print(f"\n[offloaded → {ref_path} | node_id: {nid}]", file=sys.stderr)
    return nid


def cmd_show(session_id: str):
    """Print current canvas."""
    canvas_path = session_dir(session_id) / "canvas.md"
    if canvas_path.exists():
        print(canvas_path.read_text())
    else:
        print(f"No canvas for session {session_id}")


def cmd_recall(session_id: str, nid: str):
    """Print the raw ref for a node_id."""
    ref_path = session_dir(session_id) / "refs" / f"{nid}.md"
    if ref_path.exists():
        print(ref_path.read_text())
    else:
        # Fuzzy: find any ref whose name starts with nid
        matches = list((session_dir(session_id) / "refs").glob(f"{nid}*"))
        if matches:
            print(matches[0].read_text())
        else:
            print(f"No ref found for node_id '{nid}' in session {session_id}")
            sys.exit(1)


def cmd_list():
    """List all sessions with a canvas."""
    if not CANVAS_DIR.exists():
        print("No canvas directory yet.")
        return
    for sdir in sorted(CANVAS_DIR.iterdir()):
        canvas_path = sdir / "canvas.md"
        if canvas_path.exists():
            meta_path = sdir / "canvas.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                print(f"{sdir.name}  nodes={len(meta['nodes'])}  edges={len(meta['edges'])}")
            else:
                print(sdir.name)


def cmd_rebuild(session_id: str):
    """Rebuild canvas.json/canvas.md from refs on disk."""
    refs_dir = session_dir(session_id) / "refs"
    canvas = {"session_id": session_id, "nodes": [], "edges": []}
    for ref_file in sorted(refs_dir.glob("*.md")):
        nid = ref_file.stem
        content = ref_file.read_text()
        # Extract label from first heading
        label = nid
        for line in content.splitlines():
            if line.startswith("# "):
                label = line[2:].strip()
                break
        chars = len(content)
        canvas["nodes"].append({"node_id": nid, "label": label, "chars": chars, "ref": str(ref_file)})
    save_canvas(session_id, canvas)
    print(render_mermaid(canvas))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main():
    p = argparse.ArgumentParser(description="Mermaid canvas offload for Hermes sessions")
    p.add_argument("--session", "-s", help="Session ID (required for most commands)")
    p.add_argument("--label", "-l", default="tool-output", help="Human label for this node")
    p.add_argument("--rel", "-r", default=None, help="Edge relation label (e.g. 'found', 'fixed')")
    p.add_argument("--after", "-a", default=None, help="node_id of previous node to link from")
    p.add_argument("--show", action="store_true", help="Print current canvas")
    p.add_argument("--recall", metavar="NODE_ID", help="Print raw ref for a node_id")
    p.add_argument("--rebuild", action="store_true", help="Rebuild canvas from refs on disk")
    p.add_argument("--list", action="store_true", help="List sessions with a canvas")
    args = p.parse_args()

    if args.list:
        cmd_list()
        return

    if not args.session:
        p.error("--session is required")

    if args.show:
        cmd_show(args.session)
    elif args.recall:
        cmd_recall(args.session, args.recall)
    elif args.rebuild:
        cmd_rebuild(args.session)
    else:
        # Default: read stdin and offload
        content = sys.stdin.read()
        if not content.strip():
            print("No content on stdin. Use --show, --recall, --list, or --rebuild.", file=sys.stderr)
            sys.exit(1)
        nid = cmd_offload(args.session, args.label, content, args.rel, args.after)
        print(f"node_id={nid}", file=sys.stderr)


if __name__ == "__main__":
    main()
