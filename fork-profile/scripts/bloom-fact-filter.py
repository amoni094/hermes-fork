#!/usr/bin/env python3
"""Bloom filter for injected-facts dedup (Motwani Ch 4).

Persist to profiles/fork/cache/bloom-fact-filter.bin
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
BLOOM_PATH = _hermes_root / "cache" / "bloom-fact-filter.bin"

try:
    import mmh3  # type: ignore
except Exception:
    mmh3 = None


def _hashes(key: str, k: int, m: int) -> list[int]:
    data = key.encode("utf-8", errors="replace")
    if mmh3 is not None:
        h1 = mmh3.hash(data, 0) & 0xFFFFFFFF
        h2 = mmh3.hash(data, 1) & 0xFFFFFFFF
    else:
        d1 = hashlib.sha256(data).digest()
        d2 = hashlib.md5(data).digest()
        h1 = int.from_bytes(d1[:4], "little")
        h2 = int.from_bytes(d2[:4], "little") or 1
    return [(h1 + i * h2) % m for i in range(k)]


class BloomFilter:
    def __init__(self, capacity=10000, error_rate=0.01, nbits: int | None = None, nhash: int | None = None):
        try:
            capacity = int(capacity or 10000)
        except (TypeError, ValueError):
            capacity = 10000
        try:
            error_rate = float(error_rate or 0.01)
        except (TypeError, ValueError):
            error_rate = 0.01
        capacity = max(16, capacity)
        error_rate = min(0.5, max(1e-9, error_rate))
        m = nbits if nbits is not None else math.ceil(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        k = nhash if nhash is not None else max(1, round((m / capacity) * math.log(2)))
        self.m = max(8, m)
        self.k = max(1, k)
        self.bits = bytearray((self.m + 7) // 8)

    def add(self, key: str) -> None:
        for h in _hashes(str(key), self.k, self.m):
            self.bits[h // 8] |= 1 << (h % 8)

    def __contains__(self, key: str) -> bool:
        for h in _hashes(str(key), self.k, self.m):
            if not (self.bits[h // 8] & (1 << (h % 8))):
                return False
        return True

    def dumps(self) -> bytes:
        header = struct.pack(">II", self.m, self.k)
        return header + bytes(self.bits)

    @classmethod
    def loads(cls, data: bytes) -> BloomFilter:
        m, k = struct.unpack(">II", data[:8])
        bf = cls(capacity=10000, nbits=m, nhash=k)
        bf.bits = bytearray(data[8:8 + (m + 7) // 8])
        if len(bf.bits) < (m + 7) // 8:
            bf.bits.extend(b"\x00" * ((m + 7) // 8 - len(bf.bits)))
        return bf

    def save(self, path: Path | None = None) -> Path:
        path = Path(path or BLOOM_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(self.dumps())
        os.replace(str(tmp), str(path))
        return path

    @classmethod
    def load(cls, path: Path | None = None, capacity=10000, error_rate=0.01) -> BloomFilter:
        path = Path(path or BLOOM_PATH)
        if path.exists():
            try:
                return cls.loads(path.read_bytes())
            except Exception:
                pass
        return cls(capacity=capacity, error_rate=error_rate)


def filter_injected(items: list, bloom: BloomFilter | None = None) -> list:
    bloom = bloom or BloomFilter.load()
    out = []
    for it in items:
        key = str(it.get("id") if isinstance(it, dict) else it)
        if key in bloom:
            continue
        out.append(it)
        bloom.add(key)
    return out


def _self_test() -> int:
    bf = BloomFilter(capacity=1000, error_rate=0.01)
    bf.add("alpha")
    bf.add("beta")
    assert "alpha" in bf
    assert "beta" in bf
    assert "gamma" not in bf
    data = bf.dumps()
    bf2 = BloomFilter.loads(data)
    assert "alpha" in bf2 and "gamma" not in bf2
    items = [{"id": "alpha"}, {"id": "gamma"}]
    kept = filter_injected(items, bf2)
    assert [x["id"] for x in kept] == ["gamma"]
    print(json.dumps({"ok": True, "m": bf.m, "k": bf.k, "backend": "mmh3" if mmh3 else "hashlib"}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Bloom injected-facts filter")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    print(json.dumps({"ok": True, "usage": "--self-test"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
