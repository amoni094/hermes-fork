# Multilingual Memory Research 2026

Extracted from agent-memory-consolidation SKILL.md. Contains the multilingual/cross-lingual
research grounding section — a curated paper list with implementation notes for the
consolidation cron. These are source papers and quantified benchmarks; the actionable
patterns (NREM/REM phases, dedup, hybrid trigger) are summarised inline in the main SKILL.md.

---

## Multilingual research grounding for consolidation (2025–2026 sweep)

### MemoryOS page-full trigger (arXiv 2506.06326, BAI-LAB Beijing, ACL 2025)
BAI-LAB (Beijing Academy Institute, Ting Bai's group) measured that trigger mechanism
matters: **page-full (topic-continuity) beats time-based cron** by +49.1% F1 on LoCoMo
benchmark (+46.2% BLEU). GitHub: github.com/BAI-LAB/MemoryOS

MemoryOS STM→MTM promotion: when the current session's dialogue pages exceed a
page-capacity threshold AND the new topic (measured by embedding distance from prior
page centroids) is distinct from the current page, trigger consolidation immediately —
don't wait for the nightly cron. Current Hermes pattern is time-triggered only.

**Hybrid trigger (recommended)**:
```python
def should_consolidate(session_tokens: int, topic_shift_score: float) -> bool:
    # Page-full (MemoryOS): trigger if context window is >70% full AND topic shifted
    if session_tokens > 0.7 * MAX_CONTEXT and topic_shift_score > 0.6:
        return True
    # Time fallback: also trigger at end of day regardless
    return is_end_of_day()
```

### NEMORI: predict-calibrate distillation (arXiv 2508.03341, ACL 2026)
"What Deserves Memory: Adaptive Memory Distillation for LLM Agents"
GitHub: github.com/nemori-ai/nemori

Key innovation: uses **LLM prediction error** as the distillation signal, not importance
heuristics. Episodes the LLM finds hard to predict = novel/surprising = worth retaining.
Episodes the LLM predicts easily = routine/redundant = prune.

Two-module cascading pipeline:
1. **Episodic Memory Integration**: transform raw interactions → coherent narratives
   (remove clutter, structure into story-form)
2. **Semantic Knowledge Distillation**: measure prediction error per episode segment;
   high-error segments → distill into semantic memory; low-error → archive/prune

Dual-pillar principles: Two-Step Alignment (faithful representation) + Predict-Calibrate
(proactive distillation). Asynchronous predict-calibrate pipeline for efficiency.

**Implementation for Hermes consolidation cron**:
```python
# Dependencies: pip install numpy scikit-learn
# embed() = any embedding function (e.g. OpenAI text-embedding-3-small via Hindsight)
# cosine_similarity(a, b) = numpy.dot(a,b) / (norm(a)*norm(b)) or sklearn.metrics.pairwise
import numpy as np
def embed(text): raise NotImplementedError("wire to Hindsight embedding endpoint")
def cosine_similarity(a, b): return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9))

def nemori_distill(episode_text: str, model="claude-haiku-4-5") -> tuple[float, str]:
    """Predict-calibrate: measure LLM surprise at episode content."""
    # Step 1: Generate prediction from prior context BEFORE seeing episode
    prior_context = get_prior_session_summary()  # MEMORY.md + recent Graphiti facts
    prediction = llm_complete(f"{prior_context}\nPredict what happened next:", model)
    # Step 2: Measure divergence between prediction and actual episode
    pred_embedding = embed(prediction)
    actual_embedding = embed(episode_text)
    prediction_error = 1.0 - cosine_similarity(pred_embedding, actual_embedding)
    # High error (> 0.5) = surprising = keep; low error = routine = prune
    if prediction_error > 0.5:
        fact = llm_complete(f"Extract the key new fact from:\n{episode_text}", model)
        return prediction_error, fact
    return prediction_error, None  # None = prune
```

### SCM NREM/REM sleep phases (arXiv 2604.20943)
"SCM: Sleep-Consolidated Memory with Algorithmic Forgetting"
- **NREM phase**: consolidation of recent memories into structured form
  (deduplication, structuring, summarization)
- **REM phase**: cross-referencing and integration with long-term memory
  (conflict detection, novel pattern promotion)
- **Results**: 100% recall accuracy over 10-turn benchmark; 90.9% noise reduction
  through adaptive forgetting; <1ms search latency

Structure the nightly cron as two sequential phases (implement in agent-memory-consolidation.py):
```
NREM (22:00 UTC):
  1. Collect today's episodes from session_search
  2. Run NEMORI predict-calibrate: measure prediction error per segment
  3. High-error segments → extract key facts (candidate MEMORY.md additions)
  4. Dedup check: cosine distance to existing MEMORY.md entries
  5. Low-error + high-similarity = prune. High-error + low-similarity = keep.

REM (23:00 UTC, after NREM completes):
  6. Cross-reference new facts with Graphiti KG
  7. Conflict detection (MemGraphRAG 2606.00610 pattern)
  8. Resolve conflicts → update Graphiti + MEMORY.md atomically
  9. Identify L1 traces exceeding promotion threshold → create L2 policy candidates
  10. Signal skill crystallization for patterns appearing in ≥3 different episodes
```

### Human-Inspired Memory: dedup-based consolidation (arXiv 2605.08538)
"Human-Inspired Memory Architecture for LLM Agents"
Multi-institution (likely Microsoft Research)
- **Deduplication-based consolidation**: before writing to MEMORY.md, check new content
  against existing entries for semantic similarity → merge duplicates → write only
  genuinely new information
- **97.2% retention precision with 58% store reduction** on VSCode 13K-issue dataset
- **+13.3 pp preference recall** at S-tier scale (50 sessions)

**Gap in current Hermes consolidation**: writing new content without dedup check causes
MEMORY.md bloat (we're at 99%/2,181 chars of 2,200 char limit). Dedup before write:
```python
# Uses same embed() / cosine_similarity() stubs defined in nemori_distill above
def dedup_before_write(new_fact: str, memory_md: str, threshold: float = 0.85) -> bool:
    """Return True if new_fact is genuinely new (not a duplicate)."""
    existing_chunks = memory_md.split('§')
    new_emb = embed(new_fact)
    for chunk in existing_chunks:
        if cosine_similarity(new_emb, embed(chunk)) > threshold:
            return False  # duplicate — skip
    return True  # genuinely new — write
```

---

## ACM: Agentic Context Management 5-primitive framework (arXiv 2607.21503, Jul 2026)

The most complete academic framework for agent context/memory lifecycle — published July 2026,
covers exactly what the consolidation cron implements. Reference implementation achieves
**92% LongMemEval, 93.2% LoCoMo** — the benchmark targets for this skill.

5 primitives (validated with linear cost + preserved fidelity):
1. **Architecting** — pre-task context design: what memory surfaces to activate, in what order
2. **Ingesting** — structured intake: which content enters which memory tier (maps to L1 traces)
3. **Scoping** — per-turn context assembly: which memory surfaces to include for this turn only
4. **Anticipating** — predictive pre-load: retrieve expected-needed facts before the agent needs them
   (related to NEMORI's predict-calibrate: anticipate what will be needed next based on task trajectory)
5. **Compacting & consolidation** — session-end compression + promotion to durable tiers
   (this is the nightly cron's job: NREM phase = compacting; REM phase = consolidation)

Key finding: **compaction = linear cost + preserved fidelity** — this refutes the intuition
that aggressive compression loses information. The ACM paper shows that validated compaction
(structured summarization, not naive truncation) preserves recall at linear compute cost.

ACM primitive mapping to Hermes cron:
```
ACM primitive       → Hermes implementation
─────────────────────────────────────────────────────────────────
Architecting        → skills_list() + memory context injection at session start
Ingesting           → l1-extract.py capturing tool calls + assistant turns to memory-facts/
Scoping             → hermes-memory-surface-selection skill (which surface per query type)
Anticipating        → NEMORI predict-calibrate (pre-predict next episode content)
Compacting          → agent-memory-consolidation.py NREM phase (deduplicate, structure)
Consolidation       → agent-memory-consolidation.py REM phase (promote, KG-sync, conflict-resolve)
```

The 92% LongMemEval / 93.2% LoCoMo reference implementation benchmark gives Hermes a
concrete quality target: if the NREM+REM nightly cron is working correctly, recall on
retrospective long-conversation questions should reach ~90%+ on held-out test turns.
