#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILLS_ROOT = Path(os.environ.get("HERMES_SKILLS_ROOT", os.path.expanduser("~/.hermes/skills")))
SECURITY_ROOT = Path(os.environ.get("HERMES_SKILLS_SECURITY_ROOT", os.path.expanduser("~/.hermes/skills-security")))
REPORTS_ROOT = SECURITY_ROOT / "reports"
STATE_PATH = SECURITY_ROOT / "state.json"
ALLOWLIST_PATH = SECURITY_ROOT / "allowlist.json"
QUARANTINE_ROOT = Path(os.environ.get("HERMES_SKILLS_QUARANTINE_ROOT", os.path.expanduser("~/.hermes/skills-quarantine")))
SKILLSPECTOR_BIN = os.environ.get("SKILLSPECTOR_BIN", os.path.expanduser("~/.local/bin/skillspector"))
DEFAULT_THRESHOLD = int(os.environ.get("HERMES_SKILLS_QUARANTINE_SCORE", "60"))


@dataclass
class SkillResult:
    rel: str
    path: Path
    name: str
    bundled: bool
    hash: str
    scan_exit: int
    score: int | None
    severity: str | None
    recommendation: str | None
    findings: int
    raw: dict[str, Any]
    stdout_path: Path
    quarantined_to: str | None = None
    baseline_trusted: bool = False
    allowlisted: bool = False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)


def load_bundled_names() -> set[str]:
    manifest = SKILLS_ROOT / ".bundled_manifest"
    bundled = set()
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            if ":" in line:
                bundled.add(line.split(":", 1)[0].strip())
    return bundled


def find_skill_dirs() -> list[Path]:
    seen = set()
    skill_dirs = []
    for p in SKILLS_ROOT.rglob("SKILL.md"):
        rel_parts = p.relative_to(SKILLS_ROOT).parts[:-1]
        if any(part.startswith(".") for part in rel_parts):
            continue
        parent = p.parent
        if parent not in seen:
            seen.add(parent)
            skill_dirs.append(parent)
    return sorted(skill_dirs)


def result_from_cache(path: Path, bundled_names: set[str], cached: dict[str, Any], file_hash_value: str) -> SkillResult:
    rel = path.relative_to(SKILLS_ROOT).as_posix()
    report = Path(str(cached.get("report", REPORTS_ROOT / (rel.replace("/", "__") + ".json"))))
    raw: dict[str, Any] = {}
    if report.exists():
        try:
            loaded = json.loads(report.read_text())
            if isinstance(loaded, dict):
                raw = loaded
        except Exception:
            raw = {"cache_read_error": True}
    findings_raw = raw.get("findings", [])
    findings = findings_raw if isinstance(findings_raw, list) else []
    return SkillResult(
        rel=rel,
        path=path,
        name=path.name,
        bundled=path.name in bundled_names,
        hash=file_hash_value,
        scan_exit=int(cached.get("scan_exit", 0)),
        score=cached.get("score") if isinstance(cached.get("score"), int) else None,
        severity=cached.get("severity") if isinstance(cached.get("severity"), str) else None,
        recommendation=cached.get("recommendation") if isinstance(cached.get("recommendation"), str) else None,
        findings=len(findings),
        raw=raw,
        stdout_path=report,
        quarantined_to=cached.get("quarantined_to") if isinstance(cached.get("quarantined_to"), str) else None,
    )

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in path.rglob("*") if x.is_file() and ".hub" not in x.parts):
        rel = p.relative_to(path).as_posix().encode()
        h.update(rel)
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "version": 1,
        "created_at": now_iso(),
        "approved_hashes": {},
        "last_results": {},
        "last_run": None,
    }


def save_state(state: dict[str, Any]) -> None:
    SECURITY_ROOT.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def load_allowlist() -> dict[str, Any]:
    if ALLOWLIST_PATH.exists():
        data = json.loads(ALLOWLIST_PATH.read_text())
        if isinstance(data, dict):
            return data
    return {
        "version": 1,
        "updated_at": now_iso(),
        "skills": {},
    }


def save_allowlist(allowlist: dict[str, Any]) -> None:
    allowlist["updated_at"] = now_iso()
    ALLOWLIST_PATH.write_text(json.dumps(allowlist, indent=2, sort_keys=True) + "\n")


def is_allowlisted(result: SkillResult, allowlist: dict[str, Any]) -> bool:
    skill_entry = allowlist.get("skills", {}).get(result.rel)
    if not isinstance(skill_entry, dict):
        return False
    hashes = skill_entry.get("hashes", [])
    return isinstance(hashes, list) and result.hash in hashes


def populate_allowlist_from_flagged(results: list[SkillResult], allowlist: dict[str, Any], threshold: int) -> dict[str, Any]:
    skills = allowlist.setdefault("skills", {})
    for r in results:
        if r.bundled or (r.score or 0) < threshold:
            continue
        entry = skills.setdefault(r.rel, {})
        entry["hashes"] = sorted(set(entry.get("hashes", [])) | {r.hash})
        entry["reason"] = entry.get("reason") or "Explicitly exempted current flagged skill pending manual review"
        entry["last_score"] = r.score
        entry["last_severity"] = r.severity
        entry["recommendation"] = r.recommendation
        entry["report"] = str(r.stdout_path)
    return allowlist


def remove_allowlisted_from_baseline(state: dict[str, Any], allowlist: dict[str, Any]) -> None:
    approved = state.setdefault("approved_hashes", {})
    for rel in allowlist.get("skills", {}):
        approved.pop(rel, None)


def scan_skill(path: Path, bundled_names: set[str]) -> SkillResult:
    rel = path.relative_to(SKILLS_ROOT).as_posix()
    out_path = REPORTS_ROOT / (rel.replace("/", "__") + ".json")
    proc = subprocess.run(
        [SKILLSPECTOR_BIN, "scan", str(path), "--no-llm", "--format", "json"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    data: dict[str, Any]
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
            data = parsed if isinstance(parsed, dict) else {"raw": parsed}
        except json.JSONDecodeError:
            data = {
                "parse_error": True,
                "stdout_prefix": proc.stdout[:2000],
                "stderr_prefix": proc.stderr[:2000],
            }
    else:
        data = {"stderr_prefix": proc.stderr[:2000]}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    risk_raw = data.get("risk_assessment", {})
    risk = risk_raw if isinstance(risk_raw, dict) else {}
    findings_raw = data.get("findings", [])
    findings = findings_raw if isinstance(findings_raw, list) else []
    return SkillResult(
        rel=rel,
        path=path,
        name=path.name,
        bundled=path.name in bundled_names,
        hash=file_hash(path),
        scan_exit=proc.returncode,
        score=risk.get("score") if isinstance(risk.get("score"), int) else None,
        severity=risk.get("severity") if isinstance(risk.get("severity"), str) else None,
        recommendation=risk.get("recommendation") if isinstance(risk.get("recommendation"), str) else None,
        findings=len(findings),
        raw=data,
        stdout_path=out_path,
    )


def should_quarantine(result: SkillResult, state: dict[str, Any], allowlist: dict[str, Any], threshold: int) -> bool:
    approved = state.get("approved_hashes", {})
    if result.bundled:
        return False
    if result.allowlisted:
        return False
    if result.scan_exit not in (0, 1):
        return False
    if (result.score or 0) < threshold:
        return False
    if approved.get(result.rel) == result.hash:
        return False
    return True


def quarantine_skill(result: SkillResult) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = QUARANTINE_ROOT / ts / result.rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(result.path), str(dest))
    return str(dest)


def summarize(results: list[SkillResult], threshold: int) -> dict[str, Any]:
    return {
        "skills": len(results),
        "bundled": sum(1 for r in results if r.bundled),
        "non_bundled": sum(1 for r in results if not r.bundled),
        "severity_counts": dict(Counter((r.severity or "UNKNOWN") for r in results)),
        "allowlisted": [
            {
                "skill": r.rel,
                "score": r.score,
                "severity": r.severity,
                "report": str(r.stdout_path),
            }
            for r in results if r.allowlisted
        ],
        "quarantined": [
            {"skill": r.rel, "score": r.score, "severity": r.severity, "to": r.quarantined_to}
            for r in results if r.quarantined_to
        ],
        "flagged": [
            {
                "skill": r.rel,
                "score": r.score,
                "severity": r.severity,
                "recommendation": r.recommendation,
                "bundled": r.bundled,
                "baseline_trusted": r.baseline_trusted,
                "allowlisted": r.allowlisted,
                "report": str(r.stdout_path),
            }
            for r in results if (r.score or 0) >= threshold
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Hermes skills with SkillSpector and optionally quarantine risky future additions.")
    parser.add_argument("--refresh-baseline", action="store_true", help="Trust the current hashes of all existing skills and reset approved baseline.")
    parser.add_argument("--enforce", action="store_true", help="Quarantine new or changed non-bundled skills whose score meets the threshold.")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="Score threshold for quarantine in enforce mode.")
    parser.add_argument("--sync-allowlist-from-flagged", action="store_true", help="Write current flagged non-bundled skills into the explicit allowlist and remove them from baseline trust.")
    args = parser.parse_args()

    ensure_dirs()
    state = load_state()
    allowlist = load_allowlist()
    bundled_names = load_bundled_names()
    skill_dirs = find_skill_dirs()
    previous_approved = state.get("approved_hashes", {})
    cached_results = state.get("last_results", {})
    results: list[SkillResult] = []
    for path in skill_dirs:
        rel = path.relative_to(SKILLS_ROOT).as_posix()
        current_hash = file_hash(path)
        cached = cached_results.get(rel)
        report_path = Path(str(cached.get("report", ""))) if isinstance(cached, dict) else None
        allowlisted_hashes = allowlist.get("skills", {}).get(rel, {}).get("hashes", [])
        can_reuse_cache = (
            not args.refresh_baseline
            and isinstance(cached, dict)
            and cached.get("hash") == current_hash
            and report_path is not None
            and report_path.exists()
        )
        if can_reuse_cache:
            results.append(result_from_cache(path, bundled_names, cached, current_hash))
        else:
            results.append(scan_skill(path, bundled_names))

    if args.refresh_baseline:
        state["approved_hashes"] = {r.rel: r.hash for r in results}
    else:
        state.setdefault("approved_hashes", {})
        for r in results:
            if previous_approved.get(r.rel) == r.hash:
                r.baseline_trusted = True

    if args.sync_allowlist_from_flagged:
        allowlist = populate_allowlist_from_flagged(results, allowlist, args.threshold)
        save_allowlist(allowlist)
        remove_allowlisted_from_baseline(state, allowlist)

    for r in results:
        r.allowlisted = is_allowlisted(r, allowlist)

    if args.enforce:
        for r in results:
            if should_quarantine(r, state, allowlist, args.threshold):
                r.quarantined_to = quarantine_skill(r)

    state["last_results"] = {
        r.rel: {
            "hash": r.hash,
            "score": r.score,
            "severity": r.severity,
            "recommendation": r.recommendation,
            "bundled": r.bundled,
            "scan_exit": r.scan_exit,
            "report": str(r.stdout_path),
            "quarantined_to": r.quarantined_to,
            "allowlisted": r.allowlisted,
        }
        for r in results
    }
    state["last_run"] = now_iso()
    save_state(state)

    summary = summarize(results, args.threshold)
    summary_path = SECURITY_ROOT / "last-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    lines = [
        f"skills={summary['skills']} bundled={summary['bundled']} non_bundled={summary['non_bundled']}",
        f"severity_counts={json.dumps(summary['severity_counts'], sort_keys=True)}",
        f"allowlisted={len(summary['allowlisted'])}",
        f"quarantined={len(summary['quarantined'])}",
        f"flagged={len(summary['flagged'])}",
        f"summary={summary_path}",
        f"allowlist={ALLOWLIST_PATH}",
    ]
    if summary["quarantined"]:
        for item in summary["quarantined"]:
            lines.append(f"QUARANTINED {item['skill']} score={item['score']} severity={item['severity']} -> {item['to']}")
    elif args.sync_allowlist_from_flagged:
        lines.append("Explicit allowlist synced from current flagged non-bundled skills and removed from baseline trust.")
    elif args.refresh_baseline:
        lines.append("Baseline refreshed; current skills trusted by hash for future drift detection.")
    else:
        changed_high_risk = [
            r for r in results
            if not r.baseline_trusted and not r.allowlisted and (r.score or 0) >= args.threshold and not r.bundled
        ]
        if changed_high_risk:
            for r in changed_high_risk:
                lines.append(f"FLAGGED {r.rel} score={r.score} severity={r.severity} report={r.stdout_path}")
        else:
            lines = []
    if lines:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
