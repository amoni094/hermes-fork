# Non-English Agent Patterns — August 2026

Findings from the Sweep 7 non-English source research pass (Aug 12, 2026).
These patterns extend Section 6 (Enterprise Grounding) of the main SKILL.md.

---

## 1. Idle-Drift Pathology

**Source:** Sakana AI × KPMG Azusa Audit Corp — CoffeeBench  
**Language/Venue:** Japanese blog + arXiv:2606.16613, ICML 2026 Workshop on Failure Modes in Agentic AI  
**URL:** https://sakana.ai/coffee-bench/

### What it is

In a 90-day multi-agent economic simulation (6 LLM agents running a coffee supply-chain),
Claude Haiku 4.5 exhibited **"thought-action decoupling"** across all 3 runs:
- Reasoning log showed coherent analysis: "I should buy from farmer A, demand is rising…"
- Actual tool calls: `wait_for_next_day()` every turn
- Result: accumulated losses from fixed costs while reasoning correctly about how to avoid them

No other tested model (GPT-5.5, Claude Opus 4.7, Gemini 3.1 Pro, Kimi K2.6) showed this.
The pathology is **long-horizon specific** — invisible in standard short-task benchmarks.

### Key secondary finding

High tool-call volume ≠ high performance. Kimi K2.6 matched top models in raw tool-call count
but directed calls to non-productive operations (reads, waits) rather than `make_offer`/`accept_offer`.
Action *type* matters more than action *count*.

### Hermes implementation pattern

**Idle-drift detector** — complementary to LivePlan SQL watchdog (which catches repeated *failed* calls):

```
# Define "productive" tool calls as those that change external state:
# make_offer, accept_offer, send_message, write_file, execute_code, computer_use(click/type)
# 
# "Non-productive": wait, sleep, read_file, browser_snapshot, ls, pwd, etc.

After each tool call:
  productive_calls_last_N = count(productive tool calls in last 5 turns)
  avg_reasoning_tokens_last_N = mean(reasoning tokens in last 5 turns)
  
  if productive_calls_last_N == 0 AND avg_reasoning_tokens_last_N > 200:
    inject: "You've analyzed the situation thoroughly but taken no concrete action in 
             the last 5 turns. Stop analyzing. Execute the single most important next 
             step right now — one tool call that changes something."
```

This fires recovery without requiring a failed call. The watchdog pattern (repeated-failure)
and the idle-drift detector (analysis-without-action) together cover the two main loop
stall modes.

---

## 2. LLM Scope Minimization with Deterministic Safety Gates

**Source:** Yandex Cloud & ASPiRRe (Russian Association of Pediatric Rheumatologists)  
**Language/Venue:** Russian — Habr engineering blog, Aug 12 2026  
**URL:** https://habr.com/ru/companies/yandex_cloud_and_infra/articles/1068692/

### Context

Production deployment: AI monitoring agent for ~1500 pediatric rheumatology patients.
Key constraint: LLM hallucinations in safety-critical decisions are unacceptable.

Adversarial test results:
- Injecting one false fact into patient description → LLM propagated it in 50–83% of cases
- Additional instructions (e.g., "do not hallucinate") halved error rate → still 25–42%
- Conclusion: LLMs cannot be trusted for binary safety decisions regardless of prompting

### Architecture pattern

```
Patient message (free text)
        |
        v
[LLM Call 1: Structured Extraction]
  - Input: patient free-text
  - Output: structured JSON {symptom, lab_value, dose_missed, drug_name, ...}
  - Role: NLP extraction only, no decisions
        |
        v
[Deterministic Python + safety_rules.yaml]
  - Input: structured JSON from LLM Call 1
  - Logic: if lab_value["creatinine"] > threshold["creatinine_alert"]: escalate_to_doctor()
  - All risk/escalation decisions happen here — NEVER through LLM
  - Auditable: clinician opens YAML, reads exact thresholds
        |
        v
[LLM Call 2: Response Generation]
  - Input: relevant RAG chunks (48 PDF docs, 5070 fragments, pgvector/multilingual-e5-base)
            + patient history summary + structured data from Call 1
  - Output: natural-language response to patient
  - Role: text generation only, no decisions
```

### Why it works

1. **Hallucination isolation**: LLMs only touch the 2 tasks they're reliable at (extraction + fluent text generation)
2. **Auditability**: risk logic in YAML is readable by non-engineers (clinicians, regulators)
3. **Testability**: deterministic rules are unit-testable; LLM outputs are not
4. **Scope discipline**: "if the answer is in a deterministic rule, don't ask the LLM"

### Hermes application

Define `safety_gate.yaml` evaluated by a deterministic Python wrapper before LLM proceeds
to any high-stakes action:

```yaml
# safety_gate.yaml
protected_paths:
  - ~/.hermes/
  - ~/.ssh/
  - /etc/
  - /var/home/rainbow/repo1/

blocked_domains:
  - "*.internal"

confirmation_required:
  - pattern: "rm -rf"
  - pattern: "git push --force"
  - pattern: "DROP TABLE"

computer_use_blocked_targets:
  - "Password"
  - "payment"
  - "credit card"
```

This parallels SHE's Tool Policy artifact (arXiv:2608.09885, Section 5 of SKILL.md) but
grounds it in a production-validated architecture from a safety-critical domain with
real adversarial-test data backing the design decision.

---

## 3. RUMBA — Russian Long-Term Memory Benchmark

**Source:** Sber AI (Lisa Tikhonova / spreadingmind)  
**Language/Venue:** Russian — Habr engineering blog, July 24 2026  
**URL:** https://habr.com/ru/companies/sberbank/articles/1060432/

### What it is

First Russian-language multi-session long-term memory benchmark for dialogue systems.

| Metric | Value |
|--------|-------|
| Dialogues | 85 |
| Questions | 1,543 |
| Avg dialogue length | ~340,000 chars |
| Avg dialogue span | 191 days |
| Sessions per dialogue | 12–85 |
| Languages | Russian (primary) + English (auto-translated) |

### 3-axis compositional taxonomy

Every question is tagged with all three axes — enabling fine-grained diagnosis:

| Axis | Values |
|------|--------|
| **Semantic type** | StaticUser, UpdatingInfo, DeleteInfo, AsstQuery, OpenDomainType, DateExtraction, SocialRelationship, Ordering, Arithmetic, Comparison, UserQA, CalendarUnderstanding, TemporalCommonsense, TemporallyModifiedGeneralReasoning, ComplexRelations, OtherReasoning, Abstention |
| **Session scope** | Single session \| Multi-session |
| **Temporality** | Atemporal \| Temporal |

For temporal questions, a 4th tag: **temporal expression** = Explicit / Implicit / None.

### Question types unique to RUMBA (not in English benchmarks like LoCoMo/LongMemEval)

- **DeleteInfo**: "User previously stated X, then asked to delete it. What is the answer?" → expected: "I have no information about this." Tests whether agent correctly *forgets* on request.
- **AsstQuery**: "What did *you* (the assistant) recommend in session 3?" Tests whether memory system stores agent outputs, not just user inputs.
- **UpdatingInfo**: multi-step update chain — user states X, then Y, then Z → only Z is correct answer. Tests recency-aware retrieval.

### Hermes memory evaluation implication

Hermes memory systems (MEMORY.md, Graphiti, Hindsight) lack test coverage for:
1. **DeleteInfo**: does the system actually remove or suppress memories when user says "forget this"?
2. **AsstQuery**: does the system store the agent's own outputs as memories (not just user inputs)?
3. **UpdatingInfo**: when a fact changes, does retrieval return the latest version or an old one?
4. **Temporal anchoring**: when asking "what did you recommend before I started my new job?" does the system correctly locate the time-relevant session?

Adopt RUMBA's 3-axis taxonomy as a test-design framework when evaluating memory subsystems.

---

## Source Access Notes (this sweep)

| Source | Access | Notes |
|--------|--------|-------|
| Sakana AI blog (sakana.ai) | ✅ Full text via web_extract | Japanese primary language; arXiv cross-posts available |
| J-STAGE TJSAI (jstage.jst.go.jp) | ⚠️ Metadata only | Full-text requires institutional login; article-level URLs work for metadata/abstract |
| CyberLeninka (cyberleninka.ru) | ⚠️ Search page only | Direct article extraction works; search index renders JS-only |
| Habr/Sber (habr.com) | ✅ Full text via web_extract | Russian corporate engineering blogs; good signal |
| Habr/Yandex (habr.com) | ✅ Full text via web_extract | Same; most-recent articles load cleanly |
| RISS/KISS (Korean) | ❌ Blocked | Korea institutional repos require login |
| NAVER AI blog | ❌ No Aug 2026 AI agent content | Recent posts are infra/product, not research |
| Kakao tech blog (kakaoenterprise.github.io) | ❌ No Aug 2026 content | |
| DFKI (dfki.de) | ❌ No Aug 2026 AI agent content | News section; no research blog format |
| Inria (inria.fr) | ❌ No Aug 2026 AI agent content | |
| web_search | ❌ HTTP 429 rate-limited | Entire session; use web_extract directly on target URLs |
| Yandex Research (research.yandex.com) | ✅ Publications list accessible | Primarily English papers; Russian-specific eng work on Habr instead |
