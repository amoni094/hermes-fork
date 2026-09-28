#!/usr/bin/env python3
"""
session-warm-start.py — Reusable context sidecar for session warm-start.

Based on: arXiv:2607.09493 — Shared selective memory (4 reusable categories).
Keeps task specs, schemas, tool configs, and output constraints across compactions.
Full history (CoT, tool dumps) is dropped; the sidecar is injected at session start.

Usage:
  python3 session-warm-start.py --update KEY VALUE  # update a sidecar field
  python3 session-warm-start.py --read              # print current sidecar as context block
  python3 session-warm-start.py --clear KEY         # remove a field
  python3 session-warm-start.py --compact           # extract from recent session + write sidecar
"""
import argparse, json, os, pathlib, re, sys, time

HERMES_HOME = pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes")))
HERMES_PROFILE = os.environ.get("HERMES_PROFILE", "")
if HERMES_PROFILE and "profiles" not in str(HERMES_HOME):
    _ROOT = HERMES_HOME / "profiles" / HERMES_PROFILE
else:
    _ROOT = HERMES_HOME

SIDECAR_PATH = _ROOT / "cache" / "reusable-context.json"

# The four reusable categories from arXiv:2607.09493
SIDECAR_KEYS = ("task_spec", "schemas", "tool_config", "output_constraints")

_EMPTY_SIDECAR: dict = {k: "" for k in SIDECAR_KEYS}
_EMPTY_SIDECAR["_updated_at"] = ""
_EMPTY_SIDECAR["_source"] = "arXiv:2607.09493"


def load_sidecar() -> dict:
    if SIDECAR_PATH.exists():
        try:
            return json.loads(SIDECAR_PATH.read_text())
        except Exception:
            pass
    return dict(_EMPTY_SIDECAR)


def save_sidecar(sidecar: dict) -> None:
    SIDECAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    sidecar["_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    SIDECAR_PATH.write_text(json.dumps(sidecar, indent=2))


def cmd_update(key: str, value: str) -> None:
    if key not in SIDECAR_KEYS:
        print(f"Unknown key '{key}'. Valid keys: {', '.join(SIDECAR_KEYS)}", file=sys.stderr)
        sys.exit(1)
    sidecar = load_sidecar()
    sidecar[key] = value
    save_sidecar(sidecar)
    print(f"Updated sidecar[{key!r}] ({len(value)} chars).")


def cmd_read() -> None:
    sidecar = load_sidecar()
    updated = sidecar.get("_updated_at", "never")
    print(f"# Reusable Context Sidecar (updated: {updated})")
    print()
    for key in SIDECAR_KEYS:
        val = sidecar.get(key, "")
        if val:
            print(f"## {key.replace('_', ' ').title()}")
            print(val.strip())
            print()


def cmd_clear(key: str) -> None:
    sidecar = load_sidecar()
    if key in sidecar:
        sidecar[key] = ""
        save_sidecar(sidecar)
        print(f"Cleared sidecar[{key!r}].")
    else:
        print(f"Key '{key}' not in sidecar.")


def _extract_from_text(text: str) -> dict:
    """
    Heuristic extraction of the 4 categories from raw session text.
    Used by --compact to bootstrap the sidecar from a session transcript.
    """
    sidecar: dict = {k: "" for k in SIDECAR_KEYS}

    # task_spec: lines starting with "Goal:", "Task:", "Do:", or first user message
    task_matches = re.findall(r'(?:Goal|Task|Do|Objective)\s*:\s*(.+?)(?:\n|$)', text, re.I)
    if task_matches:
        sidecar["task_spec"] = "\n".join(task_matches[:3])

    # schemas: JSON-like blocks (objects or arrays)
    schema_matches = re.findall(r'```(?:json|yaml)?\s*(\{[^`]+\}|\[[^`]+\])\s*```', text, re.DOTALL)
    if schema_matches:
        sidecar["schemas"] = "\n---\n".join(s[:500] for s in schema_matches[:3])

    # tool_config: lines mentioning config keys, env vars, paths
    config_lines = [l for l in text.splitlines()
                    if re.search(r'(?:HERMES_|config\.|\.yaml|\.json|\.env)\s*=', l, re.I)]
    if config_lines:
        sidecar["tool_config"] = "\n".join(config_lines[:10])

    # output_constraints: lines with format/length/style requirements
    constraint_lines = [l for l in text.splitlines()
                        if re.search(r'(?:must|should|always|never|format|limit|max\s+\d+)', l, re.I)]
    if constraint_lines:
        sidecar["output_constraints"] = "\n".join(constraint_lines[:10])

    return sidecar


def cmd_compact(session_file: str | None = None) -> None:
    """Extract sidecar fields from a session file or STDIN."""
    if session_file:
        text = pathlib.Path(session_file).read_text(errors="replace")
    else:
        text = sys.stdin.read()

    extracted = _extract_from_text(text)
    sidecar = load_sidecar()
    updated_keys = []
    for key in SIDECAR_KEYS:
        if extracted[key] and not sidecar.get(key):
            sidecar[key] = extracted[key]
            updated_keys.append(key)

    if updated_keys:
        save_sidecar(sidecar)
        print(f"Compact: updated {', '.join(updated_keys)}")
    else:
        print("Compact: no new fields extracted (sidecar already populated or no patterns found).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Session warm-start reusable context sidecar")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--read", action="store_true", help="Print current sidecar as context block")
    group.add_argument("--update", nargs=2, metavar=("KEY", "VALUE"), help="Update a sidecar field")
    group.add_argument("--clear", metavar="KEY", help="Clear a sidecar field")
    group.add_argument("--compact", nargs="?", const="", metavar="SESSION_FILE",
                       help="Extract from session file (or STDIN) and update empty fields")
    args = parser.parse_args()

    if args.read:
        cmd_read()
    elif args.update:
        cmd_update(args.update[0], args.update[1])
    elif args.clear:
        cmd_clear(args.clear)
    elif args.compact is not None:
        cmd_compact(args.compact or None)


if __name__ == "__main__":
    main()
