## LLMA-Mem: Non-Monotonic Team Scaling (arXiv:2606.06447 / HF papers, Sweep 12)

**Key finding:** Multi-agent teams with poor memory topology perform WORSE than solo agents
with good memory. Small team + good memory > large team + bad memory. Performance is not
monotonically increasing with team size.

**Practical rule:** Before adding a subagent to a task, invest in memory topology first:
1. Does the existing agent have the right facts accessible at each step?
2. Can session_search or Hindsight answer the key questions without a new agent?
3. Only add an agent if the task is genuinely parallelizable AND memory is already well-organized

**Memory topology quality gate (run before delegate_task with parallel subagents):**
- Each subagent receives the minimal context it needs (not a dump of everything)
- Each subagent has a clear write-back path (output_schema + validation)
- Shared facts are pre-committed to a common store (Graphiti group_id or Hindsight) before dispatch
- No two subagents are simultaneously writing to the same Graphiti group without conflict protocol

Standard Hermes consolidation uses a time-based cron trigger (nightly). BAI-LAB Beijing
(Jiazheng Kang, Mingming Ji, Zhe Zhao, Ting Bai — ACL 2025) measured that **trigger
mechanism matters**: page-full (topic-continuity) beats time-based cron by +49.1% F1
and +46.2% BLEU on the LoCoMo benchmark. GitHub: github.com/BAI-LAB/MemoryOS

MemoryOS STM→MTM architecture:
- STM = dialogue pages {Q, R, T} — each page is a topic-coherent exchange cluster
- MTM = segmented pages by topic — FIFO dialogue-chain principle
- Trigger: when STM page is FULL (topic-continuity boundary detected, not just token count)
- LPM (Long-term Personal Memory) = persistent user/agent preferences + important decisions

Trigger decision rule (add this as a pre-check before any write to hermes memory tools):
```
session_tokens > 0.7 * MAX_CONTEXT  AND  topic_shift_score > 0.6
  → flush STM to MTM immediately (don't wait for nightly cron)
  → topic_shift_score = 1 - cosine_similarity(new_turn_embedding, current_page_centroid)
```

This is currently missing from Hermes. The nightly cron fires regardless of topic
continuity, producing fragmented MTM entries that mix unrelated contexts. MemoryOS's
page-full trigger keeps topic-coherent content together, improving retrieval precision.
