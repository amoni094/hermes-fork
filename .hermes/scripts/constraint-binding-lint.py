#!/usr/bin/env python3
"""
constraint-binding-lint.py — Detect Constraint Weakening (arXiv:2608.24569).

Scans handoff docs, context packets, focus YAML, or WM exports for action-binding
constraints that lost their force (must → maybe/should/info) or lost authority /
fallback / consequence fields.

Exit codes:
  0 — clean (or only warnings with --strict off)
  1 — weakening / missing binding detected
  2 — usage / parse error

Usage:
  python3 ~/.hermes/scripts/constraint-binding-lint.py PATH [PATH ...]
  python3 ~/.hermes/scripts/constraint-binding-lint.py --stdin < handoff.md
  python3 ~/.hermes/scripts/constraint-binding-lint.py --wm-session SID
  python3 ~/.hermes/scripts/constraint-binding-lint.py --subsumption [--session SID]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))

# Patterns that often mean a must-constraint was paraphrased into soft guidance
SOFTEN_RE = re.compile(
    r"\b(consider|might want to|optional(?:ly)?|if convenient|nice to have|"
    r"as appropriate|when possible|if possible|feel free to|you may want to|"
    r"maybe|perhaps|try to|ideally|preferably|it would be good to)\b",
    re.I,
)
MUSTISH_RE = re.compile(
    r"\b(must|must not|do not|don't|never|required|blocker|hard (?:rule|constraint)|"
    r"forbidden|shall not|mandatory)\b",
    re.I,
)
# Soft obligation that often replaces a must after handoff rewrite
SOFT_OBLIGATION_RE = re.compile(
    r"\b(should(?:\s+not)?|ought to|recommended|advisable|avoid|try not to)\b",
    re.I,
)
BINDING_LINE_RE = re.compile(
    r"binding\s*[:=]\s*[\"']?(must|should|info)[\"']?",
    re.I,
)
NUMERIC_CONSTRAINT_RE = re.compile(r"(\w+)\s*(>=|<=|!=|>|<|==)\s*([\d.]+)")
CONSTRAINT_HEADING_RE = re.compile(
    r"^#+\s*(?:action-binding\s+)?constraints?\b|^constraints\s*:",
    re.I,
)


def lint_text(text: str, source: str) -> list[dict]:
    issues: list[dict] = []
    lines = text.splitlines()
    # JSON-ish constraints array
    if '"constraints"' in text or "'constraints'" in text:
        try:
            # try whole-doc JSON
            data = json.loads(text)
            issues.extend(_lint_json_constraints(data, source))
        except Exception:
            # try extract first JSON object
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    data = json.loads(m.group(0))
                    issues.extend(_lint_json_constraints(data, source))
                except Exception:
                    pass

    # Markdown / YAML prose constraints section
    in_constraints = False
    section_start = 0
    section_has_binding_must = False
    section_has_soft_only = False
    section_lines = 0

    def _flush_section(end_line: int) -> None:
        nonlocal section_has_binding_must, section_has_soft_only, section_lines, section_start
        if section_lines > 0 and not section_has_binding_must and section_has_soft_only:
            issues.append(
                {
                    "source": source,
                    "line": section_start,
                    "severity": "high",
                    "code": "constraints_section_soft_only",
                    "text": f"constraints section L{section_start}-L{end_line}",
                    "fix": (
                        "Constraints section has soft/maybe language and no binding:must — "
                        "likely Constraint Weakening (must→maybe on handoff)"
                    ),
                }
            )
        section_has_binding_must = False
        section_has_soft_only = False
        section_lines = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if CONSTRAINT_HEADING_RE.match(stripped) or re.match(
            r"^#+\s*.*\bconstraints?\b", stripped, re.I
        ):
            if in_constraints:
                _flush_section(i - 1)
            in_constraints = True
            section_start = i
            continue
        if in_constraints and re.match(r"^#+\s+\w", stripped) and not CONSTRAINT_HEADING_RE.match(stripped):
            _flush_section(i - 1)
            in_constraints = False
        if not in_constraints and "constraint" not in line.lower():
            continue
        if in_constraints and stripped and not stripped.startswith("```"):
            section_lines += 1
        if BINDING_LINE_RE.search(line) and re.search(r"binding\s*[:=]\s*[\"']?must", line, re.I):
            section_has_binding_must = True
        if MUSTISH_RE.search(line) and SOFTEN_RE.search(line):
            issues.append(
                {
                    "source": source,
                    "line": i,
                    "severity": "high",
                    "code": "must_softened_in_place",
                    "text": stripped[:200],
                    "fix": "Must-language co-occurs with softener — likely Constraint Weakening",
                }
            )
        # Soft obligation inside a constraints section without binding:must nearby
        if in_constraints and (SOFTEN_RE.search(line) or SOFT_OBLIGATION_RE.search(line)):
            window = "\n".join(lines[max(0, i - 4) : i + 4])
            if not re.search(r"binding\s*[:=]\s*[\"']?must", window, re.I):
                section_has_soft_only = True
                issues.append(
                    {
                        "source": source,
                        "line": i,
                        "severity": "high",
                        "code": "soft_constraint_without_must_binding",
                        "text": stripped[:200],
                        "fix": "Soft constraint language without binding:must — treat as weakened hard rule",
                    }
                )
        # bare bullet that looks like a hard rule but has no binding tag nearby
        if in_constraints and stripped.startswith("-") and MUSTISH_RE.search(line):
            window = "\n".join(lines[max(0, i - 3) : i + 3])
            if not BINDING_LINE_RE.search(window) and "binding:" not in window.lower():
                issues.append(
                    {
                        "source": source,
                        "line": i,
                        "severity": "med",
                        "code": "must_without_binding_field",
                        "text": stripped[:200],
                        "fix": "Hard constraint without explicit binding: must|should|info field",
                    }
                )
    if in_constraints:
        _flush_section(len(lines))
    return issues


def _lint_json_constraints(data: object, source: str) -> list[dict]:
    issues: list[dict] = []
    constraints = []
    if isinstance(data, dict):
        c = data.get("constraints")
        if isinstance(c, list):
            constraints = c
        wm = data.get("working_memory") if isinstance(data.get("working_memory"), dict) else None
        if wm and isinstance(wm.get("constraints"), list):
            constraints = list(constraints) + list(wm["constraints"])
    for idx, item in enumerate(constraints):
        if isinstance(item, str):
            if MUSTISH_RE.search(item):
                issues.append(
                    {
                        "source": source,
                        "line": None,
                        "severity": "high",
                        "code": "string_constraint_no_binding",
                        "text": item[:200],
                        "fix": f"constraints[{idx}] is a bare string; use object with binding/authority/fallback",
                    }
                )
            continue
        if not isinstance(item, dict):
            continue
        binding = str(item.get("binding") or "").lower()
        text = str(item.get("text") or item.get("rule") or "")
        if MUSTISH_RE.search(text) and binding in ("", "info", "should"):
            # mustish text with weak or missing binding
            if binding != "must":
                issues.append(
                    {
                        "source": source,
                        "line": None,
                        "severity": "high",
                        "code": "binding_weaker_than_text",
                        "text": text[:200],
                        "fix": f"constraints[{idx}] text is must-like but binding={binding or 'missing'}",
                    }
                )
        if binding == "must":
            for field in ("authority", "consequence_if_ignored"):
                if not item.get(field) and not item.get("consequence"):
                    if field == "consequence_if_ignored" and item.get("consequence"):
                        continue
                    issues.append(
                        {
                            "source": source,
                            "line": None,
                            "severity": "med",
                            "code": f"must_missing_{field}",
                            "text": text[:200],
                            "fix": f"binding:must constraints[{idx}] missing {field}",
                        }
                    )
    return issues


def _wm_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]
    return HERMES_HOME / "cache" / "working-memory" / f"{safe}.json"


def _constraint_text(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("text", "rule", "constraint", "value"):
            val = item.get(key)
            if val:
                return str(val)
        return json.dumps(item, ensure_ascii=False)
    return str(item)


def _load_wm_constraint_texts(session: str | None) -> tuple[str, list[str]]:
    wm_dir = HERMES_HOME / "cache" / "working-memory"
    if session:
        p = _wm_path(session)
        if not p.exists():
            return session, []
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            return session, []
        items = data.get("constraints") or []
        return session, [_constraint_text(c) for c in items]
    texts: list[str] = []
    if wm_dir.is_dir():
        for p in sorted(wm_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            for c in data.get("constraints") or []:
                texts.append(_constraint_text(c))
    return "all", texts


def _a_subsumes_b(op_a: str, val_a: float, op_b: str, val_b: float) -> str | None:
    """Return reason if A makes B redundant; else None.

    != is incomparable to inequalities. == subsumes nothing except exact duplicate.
    """
    if op_a == "!=" or op_b == "!=":
        if op_a == op_b and val_a == val_b:
            return "exact duplicate"
        return None
    if op_a == op_b and val_a == val_b:
        return "exact duplicate"
    if op_a == "==":
        return None
    if op_a == ">" and op_b == ">=" and val_a >= val_b:
        return f"> subsumes >= ({val_a}>={val_b})"
    if op_a == ">=" and op_b == ">=" and val_a >= val_b:
        return f">= subsumes >= ({val_a}>={val_b})"
    if op_a == "<" and op_b == "<=" and val_a <= val_b:
        return f"< subsumes <= ({val_a}<={val_b})"
    if op_a == "<=" and op_b == "<=" and val_a <= val_b:
        return f"<= subsumes <= ({val_a}<={val_b})"
    return None


def cmd_subsumption(session: str | None) -> int:
    """Read-only numeric constraint subsumption diagnostic."""
    sid, texts = _load_wm_constraint_texts(session)
    n_constraints = len(texts)
    parsed: list[tuple[str, str, str, float]] = []  # (raw, key, op, val)
    for raw in texts:
        m = NUMERIC_CONSTRAINT_RE.search(raw)
        if not m:
            continue
        key, op, val_s = m.group(1), m.group(2), m.group(3)
        try:
            val = float(val_s)
        except ValueError:
            continue
        parsed.append((raw, key, op, val))
    if not parsed:
        print(json.dumps({
            "session": sid,
            "n_constraints": n_constraints,
            "n_parsed_numeric": 0,
            "subsumptions": [],
            "duplicates": [],
            "diagnostic_only": True,
        }))
        return 0
    subsumptions: list[dict] = []
    duplicates: list[dict] = []
    n = len(parsed)
    for i in range(n):
        raw_a, key_a, op_a, val_a = parsed[i]
        for j in range(n):
            if i == j:
                continue
            raw_b, key_b, op_b, val_b = parsed[j]
            if key_a != key_b:
                continue
            reason = _a_subsumes_b(op_a, val_a, op_b, val_b)
            if not reason:
                continue
            if reason == "exact duplicate":
                if i < j:
                    duplicates.append({"a": raw_a, "b": raw_b, "key": key_a})
                continue
            subsumptions.append({
                "dominant": raw_a,
                "redundant": raw_b,
                "key": key_a,
                "reason": reason,
            })
    print(json.dumps({
        "session": sid,
        "n_constraints": n_constraints,
        "n_parsed_numeric": len(parsed),
        "subsumptions": subsumptions,
        "duplicates": duplicates,
        "diagnostic_only": True,
    }))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="Files to lint")
    ap.add_argument("--stdin", action="store_true", help="Read from stdin")
    ap.add_argument("--wm-session", default=None, help="Lint WM JSON for session")
    ap.add_argument("--session", default=None, help="WM session for --subsumption (or all)")
    ap.add_argument("--subsumption", action="store_true",
                    help="Numeric constraint subsumption diagnostic (read-only)")
    ap.add_argument("--strict", action="store_true", help="Treat med as failure")
    args = ap.parse_args()

    if args.subsumption:
        return cmd_subsumption(args.session or args.wm_session)

    blobs: list[tuple[str, str]] = []
    if args.stdin:
        blobs.append(("<stdin>", sys.stdin.read()))
    if args.wm_session:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.wm_session)[:120]
        p = HERMES_HOME / "cache" / "working-memory" / f"{safe}.json"
        if not p.exists():
            print(json.dumps({"ok": False, "error": f"WM not found: {p}"}))
            return 2
        blobs.append((str(p), p.read_text()))
    for path in args.paths:
        p = Path(path)
        if not p.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 2
        blobs.append((str(p), p.read_text(errors="replace")))

    if not blobs:
        ap.print_help()
        return 2

    all_issues: list[dict] = []
    for src, text in blobs:
        all_issues.extend(lint_text(text, src))

    high = [i for i in all_issues if i["severity"] == "high"]
    med = [i for i in all_issues if i["severity"] == "med"]
    print(
        json.dumps(
            {
                "ok": not high and not (args.strict and med),
                "high": len(high),
                "med": len(med),
                "issues": all_issues,
            },
            indent=2,
        )
    )
    if high:
        return 1
    if args.strict and med:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
