#!/usr/bin/env python3
"""
Adversarial review helper for skillspector_guard pending-quarantine proposals.

skillspector's static scanner pattern-matches on text strings inside SKILL.md /
references/*.md files. It cannot tell the difference between:
  - a skill that actually instructs an agent to run a dangerous command, and
  - a skill that *documents* (as prose, in a troubleshooting/reference section)
    a command a human or agent might run deliberately and conditionally, or
    a skill that *warns against* a dangerous pattern (negation).

This script re-reads each flagged finding in its surrounding source context and
classifies it as LIKELY_FALSE_POSITIVE / NEEDS_HUMAN_REVIEW / LIKELY_TRUE_POSITIVE,
then rolls up an overall recommendation. It does NOT move files or touch
pending_quarantine.json / allowlist.json — it only produces a report to inform
a human (or the agent, with the human's confirmation) calling
skillspector_guard.py --confirm-quarantine / --reject-quarantine.

Usage:
  python3 adversarial_quarantine_review.py <rel_path> [<rel_path> ...]
  python3 adversarial_quarantine_review.py --all-pending

Reads reports from ~/.hermes/skills-security/reports/<rel_with_underscores>.json
(same convention skillspector_guard.py uses: rel.replace('/', '__') + '.json').
Writes verdicts to ~/.hermes/skills-security/reports/adversarial/<rel_with_underscores>.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
SECURITY_ROOT = HOME / ".hermes" / "skills-security"
REPORTS_DIR = SECURITY_ROOT / "reports"
ADVERSARIAL_DIR = REPORTS_DIR / "adversarial"
PENDING_PATH = SECURITY_ROOT / "pending_quarantine.json"
SKILLS_ROOT = HOME / ".hermes" / "skills"

# Words/phrases near a flagged snippet that suggest it's descriptive/conditional/
# cautionary rather than an unconditional executable instruction.
NEGATION_MARKERS = [
    "avoid", "do not", "don't", "never", "poor proxy", "not equivalent",
    "false positive", "should not", "must not", "prevent", "detect and reject",
    "guard against", "warns against", "pitfall", "anti-pattern",
]
CONDITIONAL_MARKERS = [
    "if ", "when ", "only if", "if at or over", "if needed", "rebuild venv before use if",
    "if the", "verify", "detection:", "check live", "manual review",
]
DOCS_ONLY_MARKERS = [
    "reference", "troubleshooting", "e.g.", "example:", "for example",
]
INSPECTION_AUDIT_RATE = 0.10  # 10% random spot-check; prevents gaming negation markers

CODE_FENCE_RE = re.compile(r"```")


def rel_to_report_path(rel: str) -> Path:
    return REPORTS_DIR / (rel.replace("/", "__") + ".json")


def load_pending() -> dict[str, Any]:
    if PENDING_PATH.exists():
        return json.loads(PENDING_PATH.read_text())
    return {"proposals": {}}


def load_report(rel: str) -> dict[str, Any] | None:
    path = rel_to_report_path(rel)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def get_source_lines(skill_dir: Path, file_rel: str) -> list[str] | None:
    p = skill_dir / file_rel
    if not p.exists():
        return None
    return p.read_text(errors="replace").splitlines()


def context_window(lines: list[str], start_line: int | None, before: int = 8, after: int = 2) -> str:
    if not start_line:
        return ""
    idx = max(0, start_line - 1)
    lo = max(0, idx - before)
    hi = min(len(lines), idx + after + 1)
    return "\n".join(lines[lo:hi]).lower()


def classify_finding(finding: dict[str, Any], skill_dir: Path, has_executable_scripts: bool) -> dict[str, Any]:
    loc = finding.get("location") or {}
    file_rel = loc.get("file") or "SKILL.md"
    start_line = loc.get("start_line")
    lines = get_source_lines(skill_dir, file_rel)
    ctx = context_window(lines, start_line) if lines else (finding.get("code_snippet") or "").lower()
    snippet_lower = (finding.get("code_snippet") or "").lower()
    combined = ctx + "\n" + snippet_lower

    signals = []
    score = 0  # higher = more likely true positive

    if any(m in combined for m in NEGATION_MARKERS):
        signals.append("negation/cautionary language nearby")
        score -= 2
    if any(m in combined for m in CONDITIONAL_MARKERS):
        signals.append("conditional/documented usage (if/when/verify/detection)")
        score -= 1
    if any(m in combined for m in DOCS_ONLY_MARKERS):
        signals.append("reference/example framing")
        score -= 1
    if not has_executable_scripts and file_rel.endswith(".md"):
        signals.append("skill has no executable scripts; finding is in prose markdown, not auto-run code")
        score -= 2
    fence_count = CODE_FENCE_RE.findall(ctx)
    if fence_count and "```" in ctx:
        signals.append("inside a fenced code block presented as reference material")
        score -= 1

    # bump back up if it looks like an unconditional imperative with no hedging
    imperative_open = re.match(r"^\s*(run|execute|curl|rm |del |format |kill )", snippet_lower.strip())
    if imperative_open and score >= 0:
        signals.append("unhedged imperative opener")
        score += 2

    if score <= -3:
        verdict = "LIKELY_FALSE_POSITIVE"
    elif score >= 2:
        verdict = "LIKELY_TRUE_POSITIVE"
    else:
        verdict = "NEEDS_HUMAN_REVIEW"

    import random as _random
    _audit_flag = False
    if verdict == "LIKELY_FALSE_POSITIVE" and _random.random() < INSPECTION_AUDIT_RATE:
        _audit_flag = True
        signals.append("[INSPECTION_GAME] random audit sample - verify manually")
        verdict = "NEEDS_HUMAN_REVIEW"

    return {
        "id": finding.get("id"),
        "category": finding.get("category"),
        "pattern": finding.get("pattern"),
        "severity": finding.get("severity"),
        "finding": finding.get("finding"),
        "file": file_rel,
        "start_line": start_line,
        "verdict": verdict,
        "score": score,
        "signals": signals,
        "audit_sampled": _audit_flag,
    }


def review_skill(rel: str) -> dict[str, Any]:
    report = load_report(rel)
    if report is None:
        return {"skill": rel, "error": f"no report found at {rel_to_report_path(rel)}"}

    skill_dir = SKILLS_ROOT / rel
    has_exec = bool((report.get("metadata") or {}).get("has_executable_scripts"))
    findings = report.get("issues", [])
    verdicts = [classify_finding(f, skill_dir, has_exec) for f in findings]

    n = len(verdicts)
    n_fp = sum(1 for v in verdicts if v["verdict"] == "LIKELY_FALSE_POSITIVE")
    n_tp = sum(1 for v in verdicts if v["verdict"] == "LIKELY_TRUE_POSITIVE")
    n_review = n - n_fp - n_tp

    if n == 0:
        overall = "NO_FINDINGS"
    elif n_tp > 0:
        overall = "LIKELY_TRUE_POSITIVE_ESCALATE"
    elif n_review > 0:
        overall = "NEEDS_HUMAN_REVIEW"
    else:
        overall = "LIKELY_FALSE_POSITIVE_SAFE_TO_REJECT"

    result = {
        "skill": rel,
        "risk_assessment": report.get("risk_assessment"),
        "finding_count": n,
        "counts": {"false_positive": n_fp, "true_positive": n_tp, "needs_review": n_review},
        "overall_recommendation": overall,
        "findings": verdicts,
    }

    ADVERSARIAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ADVERSARIAL_DIR / (rel.replace("/", "__") + ".json")
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    result["_written_to"] = str(out_path)
    return result


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1

    rels: list[str]
    if args[0] == "--all-pending":
        pending = load_pending()
        rels = list(pending.get("proposals", {}).keys())
        if not rels:
            print("No pending proposals.")
            return 0
    else:
        rels = args

    for rel in rels:
        result = review_skill(rel)
        print(f"\n=== {rel} ===")
        if "error" in result:
            print(f"ERROR: {result['error']}")
            continue
        print(f"risk_assessment: {result['risk_assessment']}")
        print(f"overall_recommendation: {result['overall_recommendation']}")
        print(f"counts: {result['counts']}")
        for f in result["findings"]:
            print(f"  [{f['verdict']}] {f['id']} ({f['category']}/{f['pattern']}) "
                  f"{f['file']}:{f['start_line']} score={f['score']}")
            for s in f["signals"]:
                print(f"      - {s}")
        print(f"written: {result['_written_to']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
