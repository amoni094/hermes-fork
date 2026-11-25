"""Unit tests for the compaction-gate plugin.
Run: PYTHONPATH=hermes-fork python3 -m pytest hermes-fork/tests/test_compaction_gate.py -v
"""
from __future__ import annotations
import importlib.util, math, sqlite3, time
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
    # 3 consecutive HHR=0.05 rows: SPRT LLR >> A → hard gate
    mc.execute("CREATE TABLE IF NOT EXISTS compaction_telemetry(id INTEGER PRIMARY KEY, session_id TEXT, after_tokens INTEGER, before_tokens INTEGER)")
    for _ in range(3):
        mc.execute("INSERT INTO compaction_telemetry(session_id,after_tokens,before_tokens)VALUES(?,?,?)", ("s2", 50, 1000))
    mc.commit(); ff, fs = cg._check_gate("s2", 500, mc); assert ff and not fs

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
    # One low-HHR row: LLR > 0; hard if LLR >= A, else soft
    mc.execute("CREATE TABLE IF NOT EXISTS compaction_telemetry(id INTEGER PRIMARY KEY, session_id TEXT, after_tokens INTEGER, before_tokens INTEGER)")
    mc.execute("INSERT INTO compaction_telemetry(session_id,after_tokens,before_tokens)VALUES(?,?,?)", ("s7", 200, 1000))
    mc.commit(); ff, fs = cg._check_hhr("s7", mc)
    assert (fs and not ff) or (ff and not fs)

def test_hhr_zero_rows_no_gate(mc):
    mc.execute("CREATE TABLE IF NOT EXISTS compaction_telemetry(id INTEGER PRIMARY KEY, session_id TEXT, after_tokens INTEGER, before_tokens INTEGER)")
    mc.commit(); ff, fs = cg._check_hhr("s8", mc)
    assert not ff and not fs

def test_hhr_sprt_soft_mixed(mc):
    # One low + one healthy HHR: net LLR in (0, A) → soft gate
    mc.execute("CREATE TABLE IF NOT EXISTS compaction_telemetry(id INTEGER PRIMARY KEY, session_id TEXT, after_tokens INTEGER, before_tokens INTEGER)")
    mc.execute("INSERT INTO compaction_telemetry(session_id,after_tokens,before_tokens)VALUES(?,?,?)", ("s9", 200, 1000))
    mc.execute("INSERT INTO compaction_telemetry(session_id,after_tokens,before_tokens)VALUES(?,?,?)", ("s9", 700, 1000))
    mc.commit(); ff, fs = cg._check_hhr("s9", mc)
    assert fs and not ff


def _fact_item(text: str) -> dict:
    return {"text": text, "redundant": False, "mdl_saving": 1.0}


def test_sprt_bounds():
    a, b = cg.sprt_bounds()
    # Wald A = log((1-β)/α) = log(18), not the α=β approx log(19).
    assert abs(a - math.log((1.0 - cg.SPRT_BETA) / cg.SPRT_ALPHA)) < 1e-9
    assert abs(a - math.log(18)) < 1e-9
    assert b < 0


def test_sprt_increments():
    assert cg.sprt_llr_increment(1) < 0
    assert cg.sprt_llr_increment(0) > 0


def test_sprt_persist_across_reopen(tmp_path):
    db = tmp_path / "sprt_reopen.db"
    conn = sqlite3.connect(str(db))
    cg._schema_ready = False
    cg._ensure_schema(conn)
    for _ in range(5):
        last = cg.update_sprt(conn, "s-reopen", 0)
    llr = last["llr"]
    conn.close()
    conn2 = sqlite3.connect(str(db))
    row = conn2.execute(
        "SELECT llr, n_obs FROM compaction_sprt_state WHERE session_id=?",
        ("s-reopen",),
    ).fetchone()
    assert row is not None
    assert abs(row[0] - llr) < 1e-12
    assert row[1] == 5
    conn2.close()


def test_sprt_inherit_parent(mc):
    parent = cg.update_sprt(mc, "parent", 0)
    child = cg.update_sprt(mc, "child", 1, parent_session_id="parent")
    expected = parent["llr"] + cg.sprt_llr_increment(1)
    assert abs(child["llr"] - expected) < 1e-12
    assert child["n_obs"] == parent["n_obs"] + 1


def test_sprt_needs_many_misses_not_3(mc):
    d = None
    for _ in range(3):
        d = cg.update_sprt(mc, "s-miss3", 0)
    assert d["decision"] == "continue"


def test_sprt_h1_fires_at_19_misses(mc):
    d = None
    for _ in range(19):
        d = cg.update_sprt(mc, "s-miss19", 0)
    assert d["decision"] == "accept_h1"


def test_sprt_truncated_reject_at_nmax(mc):
    """n=N_MAX without crossing A/B must fail-closed, never promote."""
    d = None
    # 20 misses + 10 hits: LLR ≈ 0.21 ∈ (B, A) at n=30.
    xs = [0] * 20 + [1] * 10
    for x in xs:
        d = cg.update_sprt(mc, "s-trunc", x)
    assert d["n_obs"] == cg.SPRT_N_MAX
    assert d["decision"] == "truncated_reject"
    ff, fs = cg._check_hhr("s-trunc", mc)
    assert ff and not fs


def test_check_hhr_reads_state_table(mc):
    a, _ = cg.sprt_bounds()
    mc.execute(
        "INSERT INTO compaction_sprt_state(session_id, llr, n_obs, n_hits, last_decision) "
        "VALUES (?,?,?,?,?)",
        ("s-state", a, 0, 0, "continue"),
    )
    mc.commit()
    ff, fs = cg._check_hhr("s-state", mc)
    assert ff and not fs


def test_cosine_identical(mc):
    t = "compaction gate stores facts from the session archive today"
    assert cg._persist_facts(mc, "s-cos", [_fact_item(t)]) == 1
    assert cg._persist_facts(mc, "s-cos", [_fact_item(t)]) == 0
    df, n = cg._corpus_df(mc)
    v = cg._tfidf_vector(t, df, n)
    assert abs(cg._cosine_sparse(v, v) - 1.0) < 1e-9


def test_cosine_disjoint(mc):
    a = "Rate distortion theory sets a hard bound on lossy compression of memory facts"
    b = "Unrelated cooking recipe uses unsalted butter flour sugar eggs and vanilla extract"
    assert cg._persist_facts(mc, "s-dis", [_fact_item(a)]) == 1
    assert cg._persist_facts(mc, "s-dis", [_fact_item(b)]) == 1


def test_cosine_near_dup(mc):
    a = "compaction gate fires at turn 1100"
    b = "the compaction gate fires at turn 1100"
    assert cg._persist_facts(mc, "s-near", [_fact_item(a)]) == 1
    assert cg._persist_facts(mc, "s-near", [_fact_item(b)]) == 0


def test_cosine_prospective_kept(mc):
    a = "ping at 09:00 every weekday morning without fail"
    b = "[PROSPECTIVE] ping at 09:00"
    assert cg._persist_facts(mc, "s-pro", [_fact_item(a)]) == 1
    assert cg._persist_facts(mc, "s-pro", [_fact_item(b)]) == 1


def test_sha_still_first(mc, monkeypatch):
    t = "Exact hash dedup must fire before cosine near duplicate checks"
    assert cg._persist_facts(mc, "s-sha", [_fact_item(t)]) == 1

    def boom(*_a, **_k):
        raise AssertionError("cosine should not run on sha hit")

    monkeypatch.setattr(cg, "_max_cosine_against_corpus", boom)
    assert cg._persist_facts(mc, "s-sha", [_fact_item(t)]) == 0


def test_distortion_identical():
    g = cg.distortion_gate("alpha beta gamma", "alpha beta gamma")
    assert g["distortion"] == 0.0
    assert g["refuse"] is False


def test_distortion_disjoint():
    g = cg.distortion_gate("alpha beta", "gamma delta")
    assert g["distortion"] == 1.0
    assert g["refuse"] is True


def test_distortion_half():
    g = cg.distortion_gate("a b c d", "a b")
    assert abs(g["distortion"] - 0.5) < 1e-12
    assert g["refuse"] is False


def test_distortion_just_over():
    # Fabrication: 5 unique pre, 2 from pre + 3 new post. |∩|=2 |∪|=8 → 0.75.
    g = cg.distortion_gate("a b c d e", "a b x y z")
    assert abs(g["distortion"] - 0.75) < 1e-12
    assert g["refuse"] is True
    # Extractive drop (post ⊆ pre): Jaccard 0.6 but DPI forbids refuse.
    g60 = cg.distortion_gate("a b c d e", "a b")
    assert abs(g60["distortion"] - 0.6) < 1e-12
    assert g60["refuse"] is False
    assert g60.get("extractive") is True


def test_distortion_empty():
    g = cg.distortion_gate("", "")
    assert g["distortion"] == 0.0
    assert g["refuse"] is False
