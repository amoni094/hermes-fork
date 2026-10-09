"""Unit tests for the compaction-gate plugin.
Run: PYTHONPATH=hermes-fork python3 -m pytest hermes-fork/tests/test_compaction_gate.py -v
"""
from __future__ import annotations
import importlib.util, sqlite3, time
from pathlib import Path
from types import ModuleType
import pytest

def _load_plugin() -> ModuleType:
    import os
    hermes_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    p1 = hermes_home / "plugins" / "compaction-gate" / "__init__.py"
    p2 = Path.home() / ".hermes" / "profiles" / "fork" / "plugins" / "compaction-gate" / "__init__.py"
    init_path = p1 if p1.exists() else p2
    spec = importlib.util.spec_from_file_location("cg_mod", str(init_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

try:
    cg = _load_plugin()
    PLUGIN_AVAILABLE = True
except Exception as e:
    print(f"Plugin load failed: {e}")
    PLUGIN_AVAILABLE = False
    cg = None

pytestmark = pytest.mark.skipif(not PLUGIN_AVAILABLE, reason="compaction-gate not found")

@pytest.fixture()
def mc(tmp_path):
    db = tmp_path / "cg_test.db"
    conn = sqlite3.connect(str(db), check_same_thread=False)
    cg._ensure_schema(conn)
    yield conn
    conn.close()

@pytest.fixture(autouse=True)
def reset():
    cg._schema_ready = False; cg._last_fire.clear()
    yield
    cg._schema_ready = False; cg._last_fire.clear()

def test_ensure_schema(mc):
    tables = {r[0] for r in mc.execute("SELECT name FROM sqlite_master WHERE type IN ('table','shadow')").fetchall()}
    assert "compaction_gate_facts" in tables and any("cgf_fts" in t for t in tables)

def test_gate_fires_on_turn_count(mc):
    ff, fs = cg._check_gate("s1", 1200, mc); assert ff and not fs

def test_gate_fires_on_hhr(mc):
    mc.execute("CREATE TABLE IF NOT EXISTS compaction_telemetry(id INTEGER PRIMARY KEY, session_id TEXT, after_tokens INTEGER, before_tokens INTEGER)")
    for _ in range(3):
        mc.execute("INSERT INTO compaction_telemetry(session_id,after_tokens,before_tokens)VALUES(?,?,?)", ("s2", 50, 1000))
    mc.commit(); ff, _ = cg._check_gate("s2", 500, mc); assert ff

def test_gate_hysteresis(mc):
    # First fire records turn=1200 atomically in _check_gate
    ff, _ = cg._check_gate("s3", 1200, mc); assert ff
    # 1350 - 1200 = 150 < 200 hysteresis — should NOT fire again
    ff2, fs2 = cg._check_gate("s3", 1350, mc); assert not ff2 and not fs2

def test_dedup_prevents_duplicate_facts(mc):
    fact = "Rate-distortion gate prevents deep-tier lossiness beyond threshold"
    dh = cg._dedup_hash(fact); ts = time.time()
    def ins():
        if mc.execute("SELECT 1 FROM compaction_gate_facts WHERE dedup_hash=?", (dh,)).fetchone(): return False
        mc.execute("INSERT INTO compaction_gate_facts(session_id,topic,fact_text,confidence,created_at,dedup_hash)VALUES(?,?,?,?,?,?)", ("s4","decision",fact,0.9,ts,dh))
        return True
    assert ins() and not ins(); mc.commit()
    assert mc.execute("SELECT COUNT(*) FROM compaction_gate_facts").fetchone()[0] == 1

def test_auto_draw_returns_context(mc):
    fact = "Medium sessions get 60.8 percent recall with where-hint plus reranking"
    dh = cg._dedup_hash(fact)
    mc.execute("INSERT INTO compaction_gate_facts(session_id,topic,fact_text,confidence,created_at,dedup_hash)VALUES(?,?,?,?,?,?)", ("s5","eval_result",fact,0.95,time.time(),dh))
    mc.commit()
    rid = mc.execute("SELECT id FROM compaction_gate_facts WHERE dedup_hash=?", (dh,)).fetchone()[0]
    mc.execute("INSERT INTO cgf_fts(rowid,fact_text)VALUES(?,?)", (rid, fact)); mc.commit()
    result = cg._auto_draw(mc, "s5")
    assert result and fact in result and "[HINDSIGHT CONTEXT" in result

def test_fail_open(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "bad"))
    assert cg.pre_compress(session_id="s6", turn_count=500) == {}

def test_short_to_medium_gate(mc):
    mc.execute("CREATE TABLE IF NOT EXISTS compaction_telemetry(id INTEGER PRIMARY KEY, session_id TEXT, after_tokens INTEGER, before_tokens INTEGER)")
    mc.execute("INSERT INTO compaction_telemetry(session_id,after_tokens,before_tokens)VALUES(?,?,?)", ("s7", 50, 1000))
    mc.commit(); ff, fs = cg._check_gate("s7", 200, mc); assert fs and not ff
