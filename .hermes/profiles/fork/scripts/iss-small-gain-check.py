#!/usr/bin/env python3
"""iss-small-gain-check.py — Sontag/Khalil ISS small-gain composition.

Two ISS systems with gains gamma1, gamma2 may be composed iff gamma1 * gamma2 < 1.
Reads plugin ISS gain annotations (plugin.json / iss_gain.json) or estimates
from loop-pid gain-check telemetry. Hard core: product < 1.

Usage:
  python3 iss-small-gain-check.py --self-test
  python3 iss-small-gain-check.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_profile = os.environ.get("HERMES_PROFILE", "")
_root = (_base / "profiles" / _profile) if _profile and "profiles" not in str(_base) else _base
PLUGIN_DIRS = [
    _root / "plugins",
    _base / "plugins",
]
OUT_PATH = _root / "cache" / "iss-small-gain.json"
DEFAULT_GAIN = 0.6  # conservative unlabeled plugin


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def small_gain_ok(gains: list[float]) -> bool:
    """Pairwise (and total product) small-gain: every pair product < 1, product of all < 1."""
    gs = [float(g) for g in gains if g is not None]
    if len(gs) < 2:
        return True
    prod = 1.0
    for g in gs:
        if g < 0:
            return False
        prod *= g
        if not (prod < 1.0):
            return False
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            if not (gs[i] * gs[j] < 1.0):
                return False
    return True


def load_plugin_gains() -> list[dict]:
    found = []
    seen = set()
    for d in PLUGIN_DIRS:
        if not d.is_dir():
            continue
        for plug in sorted(d.iterdir()):
            if not plug.is_dir() or plug.name in seen:
                continue
            seen.add(plug.name)
            gain = None
            source = None
            for name in ("iss_gain.json", "plugin.json", "iss.json"):
                p = plug / name
                if not p.exists():
                    continue
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(data, dict) and "iss_gain" in data:
                    try:
                        gain = float(data["iss_gain"])
                        source = str(p)
                        break
                    except (TypeError, ValueError):
                        continue
            if gain is None:
                gain = DEFAULT_GAIN
                source = "default"
            found.append({"plugin": plug.name, "iss_gain": gain, "source": source})
    return found


def self_test() -> int:
    assert small_gain_ok([0.4, 0.4]) is True
    assert small_gain_ok([0.5, 0.5]) is True
    assert small_gain_ok([0.9, 0.9]) is True  # 0.81 < 1
    assert small_gain_ok([2.0, 0.6]) is False
    assert small_gain_ok([1.0, 0.5]) is False  # product == 1 is not < 1
    assert small_gain_ok([0.8, 0.9, 1.5]) is False
    assert small_gain_ok([0.3]) is True
    print(json.dumps({"property": "small-gain product < 1", "passed": True}))
    return 0


def run() -> int:
    plugins = load_plugin_gains()
    gains = [p["iss_gain"] for p in plugins]
    ok = small_gain_ok(gains)
    prod = 1.0
    for g in gains:
        prod *= float(g)
    pairs = []
    for i in range(len(plugins)):
        for j in range(i + 1, len(plugins)):
            gij = plugins[i]["iss_gain"] * plugins[j]["iss_gain"]
            pairs.append({
                "a": plugins[i]["plugin"],
                "b": plugins[j]["plugin"],
                "product": round(gij, 6),
                "ok": gij < 1.0,
            })
    bad = [p for p in pairs if not p["ok"]]
    out = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "theorem": "Sontag/Khalil ISS small-gain: gamma_i * gamma_j < 1",
        "n_plugins": len(plugins),
        "plugins": plugins,
        "product_all": round(prod, 6) if plugins else None,
        "small_gain_ok": ok,
        "violating_pairs": bad,
        "note": "Unlabeled plugins default iss_gain=0.6; joint deploy blocked if not ok.",
    }
    _atomic_write(OUT_PATH, out)
    print(json.dumps({
        "small_gain_ok": ok,
        "n_plugins": len(plugins),
        "product_all": out["product_all"],
        "n_violating_pairs": len(bad),
    }))
    if not ok:
        print("SMALL-GAIN FAIL: do not jointly deploy violating plugin pair")
        for p in bad[:10]:
            print(f"  {p['a']} x {p['b']} = {p['product']}")
        return 1
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    return run()


if __name__ == "__main__":
    sys.exit(main())
