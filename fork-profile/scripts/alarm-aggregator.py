#!/usr/bin/env python3
"""
alarm-aggregator.py — Scan cache/ for *-alarm.json files, aggregate active alarms.

Reads HERMES_HOME / HERMES_PROFILE env vars for profile-aware cache path.
Writes cache/alarm-summary.json (atomic).
Exits 1 if any HIGH alarm active, 0 otherwise.

Stdout: JSON summary dict, suitable for subprocess capture.

Schema of alarm-summary.json:
  {
    "active_alarms": [{"source": str, "severity": str, "alarm": bool, "msg": str}],
    "checked_at": ISO8601,
    "count": int   # number of active (alarm==True) alarms found
  }

Severity derivation (no severity field in current monitors):
  - Alarm files containing "HIGH" in any string value → HIGH
  - Alarm files containing "oscillation", "fragmentation", "saturated" → MEDIUM
  - All others with alarm==True → LOW
  - alarm==False (or missing) → INFO (not counted as active)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ── Profile-aware root ────────────────────────────────────────────────────────
_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_profile = os.environ.get("HERMES_PROFILE", "")
_root = (
    (_base / "profiles" / _profile)
    if _profile and "profiles" not in str(_base)
    else _base
)
CACHE_DIR = _root / "cache"
SUMMARY_PATH = CACHE_DIR / "alarm-summary.json"

# Alarm files older than this are ignored (2 hours)
MAX_AGE_SECONDS = 2 * 3600


def _derive_severity(data: dict, source: str) -> str:
    """Derive severity from alarm JSON content heuristics."""
    # Check for explicit severity key first
    if "severity" in data:
        sev = str(data["severity"]).upper()
        if sev in ("HIGH", "MEDIUM", "LOW"):
            return sev

    # Heuristics from field values
    text = json.dumps(data).lower()
    if any(kw in text for kw in ("high", "critical", "threshold_breach")):
        return "HIGH"
    if any(kw in text for kw in ("oscillation", "fragmentation", "saturated", "medium")):
        return "MEDIUM"
    if data.get("alarm"):
        return "LOW"
    return "UNKNOWN"


def _msg_snippet(data: dict, source: str) -> str:
    """Build a short human-readable message from alarm fields."""
    parts: list[str] = []

    # Common informative fields across monitors
    for key in ("reason", "alarm_type", "recommendation"):
        val = data.get(key)
        if val:
            parts.append(f"{key}={val}")

    # Numeric summaries
    for key in ("relative_gap", "mean_js", "v_t", "saturated_chains"):
        val = data.get(key)
        if val is not None:
            if isinstance(val, float):
                parts.append(f"{key}={val:.4f}")
            else:
                parts.append(f"{key}={val}")

    if parts:
        return "; ".join(parts[:4])  # cap length
    return f"{source} alarm triggered"


def aggregate() -> dict:
    """Scan cache/ for *-alarm.json files ≤2h old, return summary dict."""
    now_ts = datetime.now(timezone.utc)
    now_epoch = now_ts.timestamp()
    checked_at = now_ts.isoformat()

    active_alarms: list[dict] = []

    if not CACHE_DIR.exists():
        return {"active_alarms": [], "checked_at": checked_at, "count": 0}

    alarm_files = sorted(CACHE_DIR.glob("*-alarm.json"))

    for fpath in alarm_files:
        # Skip the summary itself
        if fpath.name == "alarm-summary.json":
            continue

        # Age check
        try:
            mtime = fpath.stat().st_mtime
        except OSError:
            continue
        if (now_epoch - mtime) > MAX_AGE_SECONDS:
            continue

        # Parse
        try:
            data = json.loads(fpath.read_text())
        except Exception:
            continue

        # Only surface entries where alarm is truthy
        if not data.get("alarm"):
            continue

        source = fpath.stem  # e.g. "stability-alarm"
        severity = _derive_severity(data, source)
        msg = _msg_snippet(data, source)

        active_alarms.append({
            "source": source,
            "severity": severity,
            "alarm": True,
            "msg": msg,
        })

    # Fix B: also surface gate-audit.json findings
    active_alarms.extend(_gate_audit_alarms(CACHE_DIR, now_epoch))
    # M6: surface callgraph-audit risk paths and HERMES_HOME gaps
    active_alarms.extend(_callgraph_audit_alarms(CACHE_DIR))

    return {
        "active_alarms": active_alarms,
        "checked_at": checked_at,
        "count": len(active_alarms),
    }


def _gate_audit_alarms(cache_dir: Path, now_epoch: float) -> list[dict]:
    """Fix B: read gate-audit.json and surface REVIEW/no-records as alarms."""
    gate_path = cache_dir / "gate-audit.json"
    entries: list[dict] = []
    try:
        if not gate_path.exists():
            return entries
        mtime = gate_path.stat().st_mtime
        if (now_epoch - mtime) > MAX_AGE_SECONDS:
            return entries
        data = json.loads(gate_path.read_text())
        # Top-level overall_verdict (compact form written by gate_audit.py main())
        overall_verdict = data.get("overall_verdict")
        # Also accept nested summary form written by audit_gate_decisions()
        if overall_verdict is None:
            overall_verdict = (data.get("summary") or {}).get("overall_verdict")
        n_records = data.get("n_records", None)
        if n_records is None:
            # In full form n_records is top-level; in summary form infer from gates
            n_records = len(data.get("gates", {})) or None
        if overall_verdict == "REVIEW":
            entries.append({
                "source": "gate_audit",
                "severity": "HIGH",
                "alarm": True,
                "msg": "gate-audit REVIEW verdict",
            })
        if n_records == 0:
            entries.append({
                "source": "gate_audit",
                "severity": "MEDIUM",
                "alarm": True,
                "msg": "gate-audit: no gate records found",
            })
    except Exception:
        pass
    return entries


def _callgraph_audit_alarms(cache_dir: Path) -> list[dict]:
    """M6: surface callgraph-audit-report.json risk_paths as alarms."""
    report_path = cache_dir / "callgraph-audit-report.json"
    entries: list[dict] = []
    try:
        if not report_path.exists():
            return entries
        data = json.loads(report_path.read_text())
        risk_paths = data.get("risk_paths", [])
        if risk_paths:
            entries.append({
                "source": "callgraph_audit",
                "severity": "MEDIUM",
                "alarm": True,
                "msg": f"callgraph-audit: {len(risk_paths)} unguarded error-propagator call chain(s)",
                "detail": risk_paths[:5],
            })
        unvalidated = data.get("hermes_home_unvalidated", [])
        if unvalidated:
            entries.append({
                "source": "callgraph_audit",
                "severity": "LOW",
                "alarm": True,
                "msg": f"callgraph-audit: {len(unvalidated)} script(s) missing HERMES_HOME validation",
                "detail": unvalidated[:10],
            })
    except Exception:
        pass
    return entries


def _atomic_write(path: Path, data: dict) -> None:
    """Write JSON atomically via a temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, prefix=".alarm-summary.", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def main() -> None:
    summary = aggregate()
    _atomic_write(SUMMARY_PATH, summary)

    # Emit JSON to stdout (for subprocess capture by pre-compact-annotate.py)
    print(json.dumps(summary))

    # Exit 1 if any HIGH alarm active
    has_high = any(a["severity"] == "HIGH" for a in summary["active_alarms"])
    sys.exit(1 if has_high else 0)


if __name__ == "__main__":
    main()
