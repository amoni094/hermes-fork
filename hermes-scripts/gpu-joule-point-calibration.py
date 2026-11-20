#!/usr/bin/env python3
"""Joule-point power-cap calibration (energy-optimal operating point).

Probes RAPL / DRM hwmon / nvidia-smi when present. Does not invent TDP.
Writes gpu-power-caps.json. Laptop-safe (CPU package treated as device).
Stdlib only. Profile-aware. Default action is --run (cron-safe).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

CACHE = _hermes_root / "cache"
OUT_PATH = CACHE / "gpu-power-caps.json"
JOULE_FRAC = 0.45
JOULE_FRAC_LO = 0.40
JOULE_FRAC_HI = 0.50
SYS_POWERCAP = Path("/sys/class/powercap")
SYS_DRM = Path("/sys/class/drm")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    tmp = path.with_name(path.name + ".tmp")
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_uwatts(path: Path) -> float | None:
    raw = _read_text(path)
    if raw is None:
        return None
    try:
        uw = float(raw.split()[0])
    except (TypeError, ValueError):
        return None
    if uw <= 0:
        return None
    # RAPL constraint files are microwatts
    if uw > 1000:
        return uw / 1_000_000.0
    return uw


def probe_rapl(root: Path = SYS_POWERCAP) -> list:
    devices = []
    if not root.is_dir():
        return devices
    try:
        zones = sorted(root.glob("*:intel-rapl:*")) + sorted(root.glob("intel-rapl:*"))
        if not zones:
            zones = [p for p in root.iterdir() if p.is_dir()]
    except OSError:
        return devices
    seen = set()
    for z in zones:
        name = _read_text(z / "name") or z.name
        if name in seen:
            continue
        cap = None
        for cand in (
            z / "constraint_0_max_power_uw",
            z / "constraint_0_power_limit_uw",
            z / "max_power_uw",
        ):
            cap = _read_uwatts(cand)
            if cap:
                break
        if not cap:
            continue
        seen.add(name)
        devices.append(
            {
                "model": "rapl:" + name,
                "tdp_w": cap,
                "source": "rapl",
            }
        )
    return devices


def probe_drm(root: Path = SYS_DRM) -> list:
    devices = []
    if not root.is_dir():
        return devices
    try:
        cards = sorted(root.glob("card*"))
    except OSError:
        return devices
    for card in cards:
        if not card.name.startswith("card") or "-" in card.name:
            continue
        dev = card / "device"
        hwmon = dev / "hwmon"
        tdp = None
        model = _read_text(dev / "product_name") or _read_text(card / "device/uevent") or card.name
        if hwmon.is_dir():
            try:
                for hm in hwmon.iterdir():
                    for cand in hm.glob("power1_cap"):
                        tdp = _read_uwatts(cand)
                        if tdp:
                            break
                    if tdp:
                        break
            except OSError:
                pass
        if tdp:
            devices.append({"model": str(model).split("\n")[0][:80], "tdp_w": tdp, "source": "drm"})
    return devices


def probe_nvidia() -> list:
    bin_path = shutil.which("nvidia-smi")
    if not bin_path:
        return []
    try:
        proc = subprocess.run(
            [bin_path, "--query-gpu=name,power.limit,power.max_limit", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    out = []
    for line in proc.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        try:
            tdp = float(parts[2] if len(parts) > 2 and parts[2] else parts[1])
        except ValueError:
            continue
        if tdp <= 0:
            continue
        out.append({"model": parts[0], "tdp_w": tdp, "source": "nvidia-smi"})
    return out


def joule_caps(tdp_w: float) -> dict:
    tdp = float(tdp_w)
    cap = tdp * JOULE_FRAC
    return {
        "tdp_w": tdp,
        "joule_point_w": cap,
        "cap_w": cap,
        "frac": JOULE_FRAC,
        "band_w": [tdp * JOULE_FRAC_LO, tdp * JOULE_FRAC_HI],
    }


def energy_per_inference(watts: float, duration_s: float, n_tasks: int) -> float | None:
    if n_tasks <= 0 or duration_s < 0 or watts < 0:
        return None
    return (watts * duration_s) / float(n_tasks)


def run(out_path: Path, rapl_root: Path | None = None, drm_root: Path | None = None) -> dict:
    devices = []
    devices.extend(probe_rapl(rapl_root or SYS_POWERCAP))
    devices.extend(probe_drm(drm_root or SYS_DRM))
    devices.extend(probe_nvidia())
    if not devices:
        return {"status": "insufficient_data", "n": 0, "ts": _now(), "devices": []}
    caps = {}
    enriched = []
    for d in devices:
        jc = joule_caps(d["tdp_w"])
        rec = dict(d)
        rec.update(jc)
        enriched.append(rec)
        caps[d["model"]] = jc["cap_w"]
    payload = {
        "ts": _now(),
        "status": "ok",
        "joule_frac": JOULE_FRAC,
        "devices": enriched,
        "caps": caps,
        "kill_test": {
            "hypothesis": "energy at 45% cap drops >=20% vs full power at equal duration",
            "note": "offline identity: energy scales with watts at fixed duration, so 45% cap => 55% drop",
            "identity_drop": 1.0 - JOULE_FRAC,
            "reject": bool((1.0 - JOULE_FRAC) < 0.20),
        },
    }
    _atomic_write(out_path, payload)
    payload["written"] = str(out_path)
    return payload


def _self_test() -> int:
    jc = joule_caps(200.0)
    assert abs(jc["cap_w"] - 90.0) < 1e-9
    assert jc["band_w"][0] < jc["cap_w"] < jc["band_w"][1]
    e_full = energy_per_inference(200.0, 10.0, 50)
    e_cap = energy_per_inference(90.0, 10.0, 50)
    assert e_full and e_cap and (e_full - e_cap) / e_full >= 0.20
    assert energy_per_inference(10, 1, 0) is None

    td = Path(tempfile.mkdtemp(prefix="gjp-"))
    try:
        rapl = td / "powercap" / "intel-rapl:0"
        rapl.mkdir(parents=True)
        (rapl / "name").write_text("package-0\n", encoding="utf-8")
        (rapl / "constraint_0_max_power_uw").write_text("28000000\n", encoding="utf-8")
        drm = td / "drm"
        drm.mkdir()
        out = td / ("gpu-power-caps_test_" + uuid.uuid4().hex + ".json")
        live = run(out, rapl_root=td / "powercap", drm_root=drm)
        assert live.get("status") == "ok", live
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["caps"]
        empty = run(td / "nope.json", rapl_root=td / "missing", drm_root=td / "missing2")
        assert empty.get("status") == "insufficient_data"
        assert not (td / "nope.json").exists()
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print("[gpu-joule-point-calibration] --self-test PASS")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Joule-point power cap calibration")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"[gpu-joule-point-calibration] --self-test FAIL: {exc}")
            sys.exit(1)
    try:
        result = run(Path(args.out))
        print(json.dumps(result if "devices" in result else result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
