#!/usr/bin/python3
"""Validate SKILL.md trigger phrases (OMH trigger_language_packs.py inspired).

Walks ~/.hermes/skills/ and ~/.hermes/profiles/fork/skills/ recursively,
extracts the top-level YAML frontmatter `triggers:` list, and checks:

  1. Phrase is non-empty after NFKD normalization + strip
  2. Phrase is <= MAX_TRIGGER_PHRASE_CHARS (120)
  3. No duplicate phrases within the same skill
  4. Phrase is not purely whitespace

Stdlib only. Prints a JSON array of skills that have violations, then an
ALARM line. --dry-run scans and reports without writing any files.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

# OMH omh/routing/trigger_language_packs.py
MAX_TRIGGER_PHRASE_CHARS = 120

DEFAULT_SKILL_ROOTS = (
    Path.home() / ".hermes" / "skills",
    Path.home() / ".hermes" / "profiles" / "fork" / "skills",
)

REASON_EMPTY_NFKD = "empty after NFKD normalization"
REASON_TOO_LONG = f"exceeds {MAX_TRIGGER_PHRASE_CHARS} characters"
REASON_DUPLICATE = "duplicate phrase within skill"
REASON_WHITESPACE = "purely whitespace"


def _try_yaml_load(text: str):
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    try:
        loaded = yaml.safe_load(text)
    except Exception:
        return None
    return loaded if isinstance(loaded, dict) else None


def extract_frontmatter(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    body = text[3:]
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    match = re.search(r"\r?\n---\s*(?:\r?\n|$)", body)
    if not match:
        return None
    return body[: match.start()]


def _unquote(item: str) -> str:
    item = item.strip()
    if len(item) >= 2 and item[0] == item[-1] and item[0] in ("'", '"'):
        return item[1:-1]
    return item


def _split_flow_sequence(inner: str) -> list[str]:
    items: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    escaped = False
    for ch in inner:
        if quote:
            buf.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\" and quote == '"':
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            token = "".join(buf).strip()
            if token:
                items.append(_unquote(token))
            buf = []
            continue
        buf.append(ch)
    token = "".join(buf).strip()
    if token:
        items.append(_unquote(token))
    return items


def _join_plain_continuations(lines: list[str], start: int, dash_indent: int) -> tuple[str, int]:
    """Join YAML plain-scalar continuation lines after a `- item` dash.

    Trigger phrases often contain colons (`chain: web_extract`). PyYAML then
    parses the item as a mapping; we keep the authored text instead.
    """
    pieces: list[str] = []
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip(" ")
        if not stripped.strip():
            break
        indent = len(line) - len(stripped)
        if stripped.startswith("- ") or stripped == "-":
            break
        if indent <= dash_indent:
            break
        pieces.append(stripped.strip())
        i += 1
    return " ".join(pieces), i


def parse_triggers_linewise(fm_text: str) -> list[str] | None:
    """Parse a top-level `triggers:` list. None means the key is absent."""
    lines = fm_text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if raw.startswith("triggers:"):
            rest = raw.split(":", 1)[1].strip()
            if rest in (">", "|", ">-", "|-"):
                collected: list[str] = []
                i += 1
                while i < len(lines) and (
                    lines[i].startswith(" ") or lines[i].startswith("\t") or not lines[i].strip()
                ):
                    if lines[i].strip():
                        collected.append(lines[i].strip())
                    i += 1
                return [" ".join(collected)] if collected else [""]
            if rest.startswith("["):
                buf = rest
                while buf.count("[") > buf.count("]") and i + 1 < len(lines):
                    i += 1
                    buf += " " + lines[i].strip()
                inner = buf[buf.find("[") + 1 :]
                if inner.endswith("]"):
                    inner = inner[:-1]
                return _split_flow_sequence(inner)
            if rest:
                return [_unquote(rest)]
            items: list[str] = []
            i += 1
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                if not stripped:
                    i += 1
                    continue
                if stripped.startswith("- ") or stripped == "-":
                    dash_indent = len(line) - len(line.lstrip(" "))
                    phrase = _unquote(stripped[1:])
                    cont, nxt = _join_plain_continuations(lines, i + 1, dash_indent)
                    if cont:
                        phrase = (phrase + " " + cont).strip() if phrase else cont
                    items.append(phrase)
                    i = nxt
                    continue
                break
            return items
        i += 1
    return None


def parse_name_linewise(fm_text: str) -> str:
    for line in fm_text.splitlines():
        if line.startswith("name:"):
            return _unquote(line.split(":", 1)[1])
    return ""


def extract_triggers_and_name(text: str) -> tuple[str, list[str] | None]:
    fm = extract_frontmatter(text)
    if fm is None:
        return "", None
    # Line parsing is authoritative for triggers. Phrases commonly contain
    # colons (`step 2 in chain: web_extract → …`); PyYAML then treats the
    # list item as a mapping and `str(dict)` is not the authored phrase.
    name_s = parse_name_linewise(fm)
    loaded = _try_yaml_load(fm)
    if loaded is not None:
        name = loaded.get("name")
        if isinstance(name, str) and name.strip():
            name_s = name.strip()
    return name_s, parse_triggers_linewise(fm)


def nfkd_stripped(phrase: str) -> str:
    return unicodedata.normalize("NFKD", phrase).strip()


def is_pure_whitespace(phrase: str) -> bool:
    return phrase.strip() == ""


def validate_phrases(phrases: list[str]) -> list[dict[str, str]]:
    """Return violation dicts `{phrase, reason}` (all problems, not first-only)."""
    violations: list[dict[str, str]] = []
    seen: set[str] = set()
    for phrase in phrases:
        if not isinstance(phrase, str):
            phrase = str(phrase)
        if is_pure_whitespace(phrase):
            violations.append({"phrase": phrase, "reason": REASON_WHITESPACE})
            # Still run the remaining checks so a blank also shows as empty-NFKD.
        normalized = nfkd_stripped(phrase)
        if not normalized and not is_pure_whitespace(phrase):
            violations.append({"phrase": phrase, "reason": REASON_EMPTY_NFKD})
        elif not normalized and is_pure_whitespace(phrase):
            violations.append({"phrase": phrase, "reason": REASON_EMPTY_NFKD})
        if len(phrase) > MAX_TRIGGER_PHRASE_CHARS:
            violations.append({"phrase": phrase, "reason": REASON_TOO_LONG})
        elif len(phrase.strip()) > MAX_TRIGGER_PHRASE_CHARS:
            violations.append({"phrase": phrase, "reason": REASON_TOO_LONG})
        # Duplicate identity: NFKD + strip, matching the live matcher fold.
        # Whitespace-only / empty-NFKD phrases share one identity; still flag repeats.
        identity = normalized if normalized else "\0empty"
        if identity in seen:
            violations.append({"phrase": phrase, "reason": REASON_DUPLICATE})
        else:
            seen.add(identity)
    return violations


def iter_skill_md(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            rel_parts = path.relative_to(root).parts[:-1]
            if any(part.startswith(".") for part in rel_parts):
                continue
            seen.add(resolved)
            found.append(path)
    return found


def skill_name_for(path: Path, frontmatter_name: str) -> str:
    if frontmatter_name:
        return frontmatter_name
    return path.parent.name


def scan_skills(roots: list[Path]) -> list[dict]:
    report: list[dict] = []
    for path in iter_skill_md(roots):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            report.append(
                {
                    "skill_name": path.parent.name,
                    "path": str(path),
                    "violations": [{"phrase": "", "reason": f"unreadable: {exc}"}],
                }
            )
            continue
        name, phrases = extract_triggers_and_name(text)
        if phrases is None:
            continue
        violations = validate_phrases(phrases)
        if violations:
            report.append(
                {
                    "skill_name": skill_name_for(path, name),
                    "path": str(path),
                    "violations": violations,
                }
            )
    return report


def default_roots() -> list[Path]:
    extra = os.environ.get("HERMES_SKILLS_ROOT", "").strip()
    roots = [Path(p) for p in DEFAULT_SKILL_ROOTS]
    if extra:
        extra_path = Path(extra).expanduser()
        if extra_path not in roots:
            roots.append(extra_path)
    return roots


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate SKILL.md frontmatter trigger phrases (OMH-inspired)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and print the report; do not write any files.",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        help="Write the JSON report to PATH (skipped under --dry-run).",
    )
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        metavar="DIR",
        help="Extra skills root to scan (repeatable). Defaults still apply.",
    )
    parser.add_argument(
        "--only-root",
        action="append",
        dest="only_roots",
        metavar="DIR",
        help="Replace default roots; scan only these directories (repeatable).",
    )
    return parser.parse_args(argv)


def emit_alarm(n_skills: int) -> None:
    if n_skills:
        print(f"ALARM: yes -- {n_skills} skills with dead/invalid trigger phrases")
    else:
        print("ALARM: no")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.only_roots:
        roots = [Path(p).expanduser() for p in args.only_roots]
    else:
        roots = default_roots()
        if args.roots:
            roots.extend(Path(p).expanduser() for p in args.roots)

    report = scan_skills(roots)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    emit_alarm(len(report))

    if args.output and not args.dry_run:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(out)

    print(f"DONE {Path(__file__).resolve()}")
    return 1 if report else 0


if __name__ == "__main__":
    sys.exit(main())
