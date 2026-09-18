# Agent Runtime Research — Aug 12 2026 Sweep 9 (arXiv ≥ 2608.09931)

**Scope:** Papers with arXiv IDs ≥ 2608.09931 (submitted Aug 11–12, 2026).
**Method:** Monthly listing walk on cs.AI 2026-08 (skip=1850, show=2000) via curl; HTML extraction
of all 83 papers ≥ 2608.09931; individual abstract fetches for candidates; arXiv API has indexing
lag of ~1–2 days for these IDs (API id_list returned 0 results; HTML listing was the ground truth).

---

## Critical Finding: Fixed Cosine Thresholds Are Invalid

**Paper:** arXiv:2608.10216 — "Similarity Gates Approve Reversals: A Validity Audit of
Embedding-Cosine Thresholds in Agent Systems"  
**Categories:** cs.CL  
**Code:** github.com/eigenforma/polaritycheck

**Key finding:** Agent frameworks that gate on fixed cosine thresholds (dedup filters, semantic
caches, drift guards, answer graders) measure *wording change* not *meaning change* — and
frequently fire backwards. Audit results:
- Production drift guard: caught 0 of 56 meaning-breaking mutations
- "Withhold study drug" → "administer study drug": cosine 0.9608 (approved as same meaning)
- Balanced accuracy across 90 configuration-threshold-task cells: max 0.700, **median 0.525** (≈ chance)
- Decision AUROC exactly 0.000 in 13 of 18 cells
- Encoder swap and NLI drop-in didn't help on held-out data

**Hermes implication:** Do NOT use fixed cosine threshold as the final gate for:
- Memory deduplication (l1-promote.py)
- Skill deduplication (hermes-skill-library-consolidation-audit)
- Memory drift detection
- Answer grading

**Fix:** Cosine for fast pre-filter (candidate recall only). NLI-based entailment as the final
binary gate. The existing `contradiction_check()` NLI path in l1-promote.py IS the right
approach — this paper validates it. The two strongest configurations in their study separated
reversal from paraphrase at matched overlap (AUROC 0.79–0.90) using matched-pair design, not
raw cosine thresholds.

---

## Generic Skills Beat Personalized Skills

**Paper:** arXiv:2608.10319 — "Do Personalized Skills Help Coding Agents? An Empirical Study of
Developer Interaction Histories"  
**Categories:** cs.SE  
**Dataset:** 206 real developer-agent sessions from 13 developers

**Key finding:**
- Developer-specific skills distilled from interaction histories: small, *inconsistent*
  improvements over no-skill baseline
- **Generic skills pooled across all developers: largest and most consistent gains**
- Personalized skills only help when same preference appears *frequently* (≥ multiple examples
  relevant to future tasks in history)

**Hermes implication:** Don't over-invest in highly user-specific skill variants.
- Build generic procedural skills with broad applicability (current approach validated)
- Only promote a pattern to a dedicated skill after ≥3 demonstrated instances
- The replay framework they built (LLM-based human developer simulator) is a useful pattern
  for Hermes skill testing harness

---

## Tool Documentation as Live Optimization Target

**Paper:** arXiv:2608.10037 — "DOCSCHISEL: Adaptive Tool Documentation Optimization Framework
for LLM Agents"  
**Categories:** cs.LG

**Key finding:**
- No single static tool documentation generalizes across task domains, LLM backbones, or agent paradigms
- DocsChisel: iteratively analyzes failed execution traces → identifies documentation-related
  issues → adds/removes/refines information fields per tool
- **+95.89%** task success over original docs; **+75.15%** over SOTA baselines (EasyTool, DRAFT)
- Limited optimization time and token overhead

**Hermes implication:** Tool/skill documentation must be treated as a live artifact, not a
one-time write. Add to skill consolidation cron:
1. Review failed invocations from session logs per skill
2. Identify which documentation fields caused failure (missing param descriptions, ambiguous
   trigger conditions, wrong scope)
3. Refine `description:` frontmatter and body content based on failure patterns

---

## Action-Layer Vulnerability Gap

**Paper:** arXiv:2608.10530 — "On Understanding, Identifying, and Mitigating Vulnerabilities
in Agentic Large Language Models"  
**Categories:** cs.CR  
**Method:** PRISMA 2020 systematic review; 743 records screened; 85 papers retained (2023–2025)

**4-Layer Taxonomy:**
1. **Perception layer** (66% of papers): prompt injection, jailbreaking, adversarial perturbations
2. **Brain layer**: planning manipulation, goal hijacking
3. **Action layer** (4.7% of papers): tool misuse, code injection, sandbox escape — UNDERADDRESSED
4. **Interaction layer**: cross-agent contamination, memory poisoning

**Attack:Defense ratio:** 3.9:1 — research is attack-heavy

**Hermes implication:**
- Current `mnemosyne-atp-safety` covers ATP (brain layer)
- Action-layer gap: validate file paths before writes, sanitize tool return values before
  feeding back to LLM, add memory isolation between sessions
- Cross-reference `mnemosyne-atp-safety` against this 4-layer taxonomy for coverage gaps
- The "architectural coupling" root cause: weak isolation allows vulnerabilities to propagate
  across layers — design for containment at each layer boundary

---

## KG Entity Graph vs Document Retrieval for Implicit Relations

**Paper:** arXiv:2608.10679 — "ENTLORE: A Graph-Grounded Benchmark for Latent Organizational
Reasoning in Enterprise Question Answering"  
**Categories:** cs.IR  
**Dataset:** 2,341 documents, 907 questions, 56 model × access configurations

**Key finding:**
- With gold documents: 30.4% of *latent* (implicit cross-entity) questions unanswered
- With gold documents: 12.6% of *explicit* questions unanswered; 6.2% of compositional
- **Structuring knowledge as induced entity graph or navigable knowledge base gives the
  strongest deployable results**
- Organizational relations remain implicit across heterogeneous sources — documents alone
  are insufficient

**Hermes/Graphiti implication (validates current investment):**
- Storing cross-session task patterns as Graphiti triplets (not just episodic memories)
  directly addresses the latent-relation gap
- In `hermes-memory-capture-and-bridge`, add step: extract entity-relation triplets from
  session summaries and store in Graphiti as `(entity_A, relation, entity_B)` triplets,
  annotated with `source_session_id` and `valid_from`
- Entity graph navigation > vector search for "where did X happen" or "who did Y" queries

---

## Agent Retrieval from Structured Profile Repository

**Paper:** arXiv:2608.09934 — "LLM Agents Factory: Retrieval of Domain-Specific LLM Agents"  
**Categories:** cs.CL  
**Code:** HuggingFace frontier-ai/llm-agent-factory  
**Benchmark:** MMLU, BIG-bench, BIG-bench Hard

**Key finding:**
- Pre-built repository of 20K+ domain-specific agent profiles + semantic search retrieval
  matches AutoGen on-the-fly generation quality (120B backbone) at substantially lower cost
- Retrieval-based construction is cost-efficient, accurate, and controllable vs dynamic generation
- Two modes: (1) semantic search retrieval, (2) distillation into compact fine-tuned model

**Hermes implication:**
- Skills already act as an agent profile library — this validates the approach
- Apply: embed all skill frontmatter descriptions once using Hindsight/OpenAI embeddings,
  store in FAISS or Hindsight index. On task dispatch, retrieve top-k skills by embedding
  similarity rather than relying on LLM keyword matching
- `hermes-semantic-skill-routing` already captures this pattern; this paper quantifies the
  cost-quality tradeoff in favor of retrieval (20K profiles → same quality as generation)

---

## Actionable Hallucination Detection (Tool Call Level)

**Paper:** arXiv:2608.10430 — "Actionable Hallucination Detection: Translating Latent
Uncertainty into Agentic Critique"  
**Categories:** cs.LG

**Key finding:**
- "Latent Critic": lightweight LoRA running concurrently with frozen LLM, restructures
  residual stream to detect tool-call hallucinations in real-time
- **0.966 AUROC**, >80% argument-level localization accuracy (e.g. "ungrounded: date")
- Negligible latency overhead vs secondary inference loops
- Deployed in ReAct loop: prevents hallucinated actions before execution + enables localized
  self-correction (e.g. "the date argument is ungrounded — ask user")

**Hermes implication (no LoRA, but pattern applies):**
- Add pre-execution tool call argument validation for critical tools (file writes, API calls)
- Implement in `verification-before-completion`: for each tool call argument, check against
  conversation context — if argument references a fact not established in context, flag
- The "localized feedback" pattern: tell the model *which* argument is ungrounded (not just
  "hallucination detected") to enable targeted self-correction

---

## Three-Layer Agent Evaluation Framework

**Paper:** arXiv:2608.09939 — "How to Dogfood Your AI Chat Agent: A Three-Layer Evaluation
Framework with Goal-Directed NPC Simulation"  
**Categories:** cs.AI  
**Deployment:** Longitudinal case study, ~3 months, 257 evaluation runs on production multi-agent system

**Framework:**
1. **Layer 1:** Canonical question-bank testing (known Q&A pairs, regression detection)
2. **Layer 2:** Random-walk multi-turn evaluation (explores conversation paths)
3. **Layer 3:** Goal-directed NPC simulator with 5 structured goal types + 10-category failure taxonomy

**Finding:** Layer 3 (goal-directed NPC) revealed failures invisible to layers 1 and 2.
Longitudinal runs over 3 months showed systematic failure pattern detection that ad-hoc
testing missed.

**Hermes implication:**
- Build a `hermes-agent-evaluation` skill implementing this 3-layer framework as a weekly cron
- Layer 1: use FTS5 session_search to replay known-good Q&A pairs
- Layer 2: random session trace replay
- Layer 3: LLM-simulated user pursuing structured goals (fetch-info, complete-task, explore,
  compare-options, handle-failure)
- 10-category failure taxonomy should be added to `agent-task-signoff` skill

---

## arXiv Listing Navigation Technique (Methodology Note)

**Problem:** Papers submitted Aug 11–12, 2026 (IDs ≥ 2608.09931) had an indexing lag of 1–2 days.
The arXiv API (`export.arxiv.org/api/query?id_list=...`) returned 0 results for these IDs.
The arXiv HTML search UI returned only papers up to 2608.09885.

**Working technique:** Monthly listing walk via curl:
```bash
curl -sL 'https://arxiv.org/list/cs.AI/2026-08?skip=1850&show=2000' | \
grep -oP 'arXiv:\K[0-9]{4}\.[0-9]+' | sort -u | \
awk -F. '{if ($1 == "2608" && $2+0 >= 9931) print}'
```
Then extract titles via Python from saved HTML. Then fetch abstracts per-paper via:
```bash
curl -sL 'https://arxiv.org/abs/ID' | python3 -c "
import sys, re
c = sys.stdin.read()
m = re.search(r'<blockquote class=.abstract[^>]*>(.*?)</blockquote>', c, re.DOTALL)
if m: print(re.sub(r'<[^>]+>', '', m.group(1)).strip())
"
```

**Key finding:** The monthly listing (e.g., `arxiv.org/list/cs.AI/2026-08`) includes ALL
papers cross-listed to cs.AI for the month, even those submitted in the last 24–48 hours
that are not yet indexed in the API or search UI. Use `show=2000` and `skip=` to paginate
to the tail of a large listing. The valid `show=` values are: 25, 50, 100, 250, 500, 1000, 2000.

**HAL note:** hal.science main site is now Anubis PoW bot-blocked (Aug 2026). The API
endpoint `api.archives-ouvertes.fr` still works for programmatic access.

---

## Papers Checked but Not Qualifying

| ID | Title | Reason excluded |
|----|-------|-----------------|
| 2608.10362 | MemSpec: Memory-Aware Runtime for Adaptive Draft Scheduling | Speculative decoding for edge devices; Hermes uses API, not local model |
| 2608.10357 | SINKFLEX-RL | RL training system for long-horizon tool use; inference-time not applicable |
| 2608.10196 | ELMER: Evolutionary Language Model | Policy evolution in GPTL DSL; not directly applicable to Python CLI agents |
| 2608.10525 | Dynamic Context Adapters | VLM history injection (visual modality specific) |
| 2608.10232 | FACT: Failure-Aware Causal Training | World-action model training (not inference) |
| 2608.10279 | Withholding Completing Chunk guardrails | Streaming-specific; Hermes uses batch responses |
| 2608.10545 | ImpactHO: KV Cache Transfer | Edge node handover; not applicable to API usage |
| 2608.09931 | Perception Before Supervision (visual distillation) | CV domain, not text agent |
| 2608.10126 | Procedural Fairness Failures in RLHF | Alignment research, not runtime agent behavior |
