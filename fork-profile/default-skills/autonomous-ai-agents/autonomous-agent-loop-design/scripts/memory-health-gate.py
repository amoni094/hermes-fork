#!/usr/bin/env python3
"""memory-health-gate.py - Session-start memory health check (arXiv:2609.05510).
Month-long autonomous run: 85 failures before gate; 1 after; 0 in final 20 days.

Checks: WAL status, Graphiti node count, Hindsight integrity, rejected-routes dir.

Usage:
  python memory-health-gate.py [--project PROJECT] [--check-only]
  python memory-health-gate.py --init-project PROJECT
Exit codes: 0=OK, 1=warn (skip inject), 2=halt (do not proceed), 3=usage error
"""
import argparse, json, pathlib, subprocess, sys, datetime

DEFAULTS = {
    "graphiti_warn_nodes": 40000, "graphiti_halt_nodes": 50000,
    "hindsight_db_path": "~/.hermes/memory-facts/hindsight.db",
    "rejected_routes_dir": "~/.hermes/cache/rejected-routes",
    "wal_script": "~/.hermes/scripts/state-wal-checkpoint.py",
}

def load_cfg(path=None):
    cfg = dict(DEFAULTS)
    for p in [path, "~/.hermes/config.yaml"]:
        if not p: continue
        try:
            import yaml
            d = yaml.safe_load(pathlib.Path(p).expanduser().read_text())
            th = d.get("memory", {}).get("tier_thresholds", {})
            cfg["graphiti_warn_nodes"] = th.get("graphiti_warn_nodes", cfg["graphiti_warn_nodes"])
            cfg["graphiti_halt_nodes"] = th.get("graphiti_halt_nodes", cfg["graphiti_halt_nodes"])
            break
        except Exception:
            pass
    return cfg

def check_wal(cfg):
    s = pathlib.Path(cfg["wal_script"]).expanduser()
    if not s.exists(): return "skip", "wal script not found"
    try:
        r = subprocess.run([sys.executable, str(s), "--status"],
                          capture_output=True, text=True, timeout=10)
        return ("ok", r.stdout.strip()[:120]) if r.returncode == 0 else \
               ("warn", f"exit {r.returncode}: {r.stderr.strip()[:80]}")
    except Exception as e:
        return "warn", f"WAL check failed: {e}"

def check_graphiti(cfg):
    try:
        import sqlite3
        for cp in ["~/.hermes/memory-facts/graphiti.db", "~/.local/share/graphiti/graphiti.db"]:
            p = pathlib.Path(cp).expanduser()
            if p.exists():
                conn = sqlite3.connect(str(p))
                try:
                    count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                    conn.close()
                    warn, halt = cfg["graphiti_warn_nodes"], cfg["graphiti_halt_nodes"]
                    if count >= halt: return "halt", f"nodes={count} >= halt {halt}"
                    if count >= warn: return "warn", f"nodes={count} >= warn {warn}"
                    return "ok", f"nodes={count} (warn={warn}, halt={halt})"
                except Exception as e:
                    conn.close(); return "skip", f"query failed: {e}"
        return "skip", "Graphiti DB not found"
    except Exception as e:
        return "warn", f"check error: {e}"

def check_hindsight(cfg):
    try:
        import sqlite3
        p = pathlib.Path(cfg["hindsight_db_path"]).expanduser()
        if not p.exists(): return "skip", "Hindsight DB not found"
        conn = sqlite3.connect(str(p))
        try:
            r = conn.execute("PRAGMA integrity_check").fetchone(); conn.close()
            return ("ok", "integrity OK") if r and r[0] == "ok" else \
                   ("halt", f"integrity FAILED: {r}")
        except Exception as e:
            conn.close(); return "warn", f"check error: {e}"
    except Exception as e:
        return "warn", str(e)

def check_routes(cfg, project):
    d = pathlib.Path(cfg["rejected_routes_dir"]).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    if project:
        f = d / f"{project}.jsonl"
        if not f.exists(): f.touch()
        n = len([l for l in f.read_text().splitlines() if l.strip()])
        return "ok", f"{n} dead-ends for '{project}'"
    return "ok", f"dir ready: {d}"

def run_gate(args):
    cfg = load_cfg(getattr(args, "config", None))
    project = getattr(args, "project", None)
    checks = [("WAL", check_wal(cfg)), ("Graphiti", check_graphiti(cfg)),
              ("Hindsight", check_hindsight(cfg)), ("Routes", check_routes(cfg, project))]
    sev = {"ok": 0, "skip": 0, "warn": 1, "halt": 2}
    max_sev, log = "ok", []
    for name, (status, detail) in checks:
        icon = {"ok": "V", "skip": "~", "warn": "!", "halt": "X"}.get(status, "?")
        print(f"  [{icon}] {name}: {detail}")
        log.append({"check": name, "status": status, "detail": detail,
                    "ts": datetime.datetime.utcnow().isoformat() + "Z"})
        if sev.get(status, 0) > sev.get(max_sev, 0): max_sev = status
    lp = pathlib.Path("~/.hermes/cache/memory-health-gate.jsonl").expanduser()
    lp.parent.mkdir(parents=True, exist_ok=True)
    with lp.open("a") as f:
        f.write(json.dumps({"run_at": datetime.datetime.utcnow().isoformat() + "Z",
                             "project": project, "max_severity": max_sev,
                             "checks": log}) + "\n")
    if max_sev == "halt":
        print("\n[memory-health-gate] HALT"); return 2
    if max_sev == "warn":
        print("\n[memory-health-gate] WARN")
        return 0 if getattr(args, "check_only", False) else 1
    print("\n[memory-health-gate] OK"); return 0

def main():
    p = argparse.ArgumentParser(description="Memory Health Gate")
    p.add_argument("--project"); p.add_argument("--config")
    p.add_argument("--check-only", action="store_true")
    p.add_argument("--init-project")
    a = p.parse_args()
    if a.init_project:
        cfg = load_cfg(None)
        d = pathlib.Path(cfg["rejected_routes_dir"]).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{a.init_project}.jsonl"
        if not f.exists(): f.touch()
        print(f"[memory-health-gate] Initialized: {f}")
        return 0
    return run_gate(a)

if __name__ == "__main__": sys.exit(main())
