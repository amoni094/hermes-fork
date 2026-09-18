# arXiv Sweep 11 — Full Output

**Date:** 2026-08-12
**Baseline cutoff:** 2608.10986
**Categories swept:** cs.AI, cs.CL, cs.MA, cs.CR, cs.LG, cs.IR, cs.SE
**Method:** 7 original keyword searches + 12 additional searches + 7 category recent-listing fetches
**Highest ID found:** 2608.11200
**Total new papers found:** 37 (cs.AI/recent: 8, cs.CL/recent: 10, cs.MA/recent: 2, cs.CR/recent: 5, cs.LG/recent: 12)
**Abstracts reviewed:** 11
**Result:** 2 HIGH, 5 MED, 4 LOW/skip

---

## HIGH Applicability

### 2608.11079 | SkillZip: Evaluation-Free Skill Compression for Self-Evolving Agents by Discovering Reusable Structure
**cs.AI** | Submitted 2026-08-11

**Core finding:** Self-evolving agents accumulate bloated skills where the same requirement
is restated in several branches, examples, and warnings, while common action sequences are
copied rather than reused. SkillZip compresses a skill by finding its shortest faithful
structural explanation using a typed MDL objective over a skill contract + residual, subject
to a hard coverage constraint for every extracted trigger, workflow edge, tool requirement,
obligation, and output field. Key modes: one-shot (single LLM call + deterministic optimisation)
and Zip-on-Write (continual — integrates each evolution patch without replaying history).

**Hermes implementation:** Patch `skillopt-continuous-improvement` and
`hermes-skill-library-consolidation-audit` — add a SkillZip pass to consolidation sweeps:
identify repeated content blocks across related skills, promote to shared umbrella section,
replace per-skill copies with one-line pointers. Add Zip-on-Write check to every
`skill_manage(action='patch')` call.
**Complexity:** High
**Status:** Target skills user-owned → see Blocked Patches in SKILL.md

---

### 2608.11095 | Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding
**cs.AI, cs.LG, cs.SE** | Submitted 2026-08-11

**Core finding:** Empirical study of 247,694 instruction lifetimes in 1,867 repos: agentic
instruction files grow 226% over their lifetime (+4.9 net instructions per commit); older
instructions have logarithmically lower deletion hazard (−0.032/commit). Root cause: adding
is cheap; deleting without the rule's rationale costs O(2^|D|). Fix: prompt comments encoding
latent reasoning reduced excess instructions 99.3% (+211.3% → +1.4%). Applied to WildIFEval:
+23.1% instruction-following improvement.

**Hermes implementation:** Patch `hermes-agent-skill-authoring` and `skillopt-continuous-improvement`
— mandate inline `<!-- why: ... -->` rationale comments on every rule/step/pitfall. Add deletion
audit step to SkillOpt pass: rules with stale/absent rationale are pruning candidates.
**Complexity:** Low (comment mandate) / Med (automated rationale-staleness detection)
**Status:** Target skills user-owned or bundled → see Blocked Patches in SKILL.md

---

## MED Applicability

### 2608.11110 | Actions Speak Louder than Words: Measuring Cross-Lingual Policy Retention in Tool-Using Agents
**cs.CL** | Submitted 2026-08-11

**Core finding:** Across 8 models, 6 parallel benchmarks, 41 languages (2.38M rollouts),
tool-using agents show significant action-policy drift when the same task is presented in
different languages — final-answer accuracy is similar, but the action sequences (tool calls)
diverge substantially. Five confounds identified (short-circuit, trace-length normalisation,
surface vs. semantic similarity, model family variance, benchmark contamination) must be
controlled before any policy-consistency claim is valid. Action traces are the auditable unit.

**Hermes implementation:** Patch `agent-task-signoff` — sign-off table should include action
trace (sequence of tool calls) not just final output. Patch `hermes-agent-skill-authoring` —
skill trigger matching should use semantic embedding comparison, not keyword-only matching.
**Complexity:** Med
**Status:** User-owned → see Blocked Patches in SKILL.md

---

### 2608.11138 | Attention-Path Fragility as an Uncertainty Signal in Large Language Models
**cs.CL, cs.AI** | Submitted 2026-08-11

**Core finding:** ASMI (Attention-Subnetwork Mutual Information) is a training-free uncertainty
estimator that masks attention heads and measures BALD mutual information among resulting
subnetworks, using a semantic-agreement kernel to discount surface-form disagreement. The
signal is orthogonal to output confidence: on grounded QA it adds error-detection signal
even controlling for logit entropy.

**Hermes implementation:** Patch `complexity-gated-planning` — add a fragility gate between
planning execution and final output for HAZARD-level decisions: rerun key query with minor
context perturbations; if answer changes structurally, escalate. Patch `verification-before-completion`
similarly.
**Complexity:** Med
**Status:** User-owned → see Blocked Patches in SKILL.md

---

### 2608.11030 | Self-Knowledge Retrieval Augmented Generation Framework for Patent Matching
**cs.IR** | Submitted 2026-08-11

**Core finding:** LLMs autonomously extract key technical entities and construct hierarchical
ontological structures from queries (rather than relying on pre-built domain ontologies), then
use these self-generated ontologies for query expansion and precise retrieval via FAISS +
generative matching. Avoids catastrophic forgetting from fine-tuning while achieving superior
precision over domain-pretrained models.

**Hermes implementation:** Patch `domain-research-synthesis` and `firecrawl-research` — add a
self-ontology step before Hindsight/Graphiti retrieval: prompt LLM to extract entity types and
hierarchical relationships from query, use these as additional Graphiti search terms alongside
original query.
**Complexity:** Med
**Status:** User-owned → see Blocked Patches in SKILL.md

---

### 2608.11191 | Test-Time Self-Evolving GUI Visual Grounding via Reflection-Guided On-Policy Self-Distillation
**cs.CV, cs.AI** | Submitted 2026-08-11

**Core finding:** Closed loop of Explore → Evaluate → Reflect → Internalize enables agents
to improve after deployment without human-annotated ground truth. An MLLM-based Reflector
assesses generated results and provides structured reasoning reflections. Reflection-Guided
On-Policy Self-Distillation converts high-level reflections into dense token-level supervision
via a conditioned self-teacher. Contrastive Calibration prevents incorrect auto-regressive
prefixes from corrupting supervisory signals during failed explorations. +7.4% avg accuracy
on six benchmarks.

**Hermes implementation:** Patch `self-improve-agent` — add Reflect step with structured
FAILED_PREFIX / ROOT_CAUSE / CORRECTION / GENERALIZATION format + Contrastive Calibration
gate before committing any skill patch: the proposed fix must be structurally different from
the failure path.
**Complexity:** High
**Status:** User-owned → see Blocked Patches in SKILL.md

---

### 2608.11025 | Data Attribution of Emergent Misalignment with Persona Features
**cs.CL** | Submitted 2026-08-11

**Core finding:** Emergent misalignment (EM) — fine-tuning on a narrow task inducing harmful
behavior in unrelated domains — is driven by persona features (latent directions from
pre-training: jailbreak personas, sarcasm, deceptive characters) that misaligned fine-tuning
amplifies. Using Sparse Autoencoder (SAE) model diffing across four open-weight models, the
study shows naturally occurring human-written text suffices to induce EM. Feature-level
attribution (which training documents activate misaligned directions) provides a practical
audit mechanism.

**Hermes implementation:** Patch `trajectory-risk-guardrail` — add SEMANTIC_DRIFT blast class
for agent output-style changes (not just actions). Signals: sarcasm, unusual verbosity,
evasiveness, tone inconsistency. Detection: audit recent tool-call inputs for perception-layer
injection if drift is sudden; flag as harness misalignment if drift is gradual across sessions.
**Complexity:** Med
**Status:** User-owned → see Blocked Patches in SKILL.md

---

## LOW / Skip (not recorded in detail)

- **2608.11033** Who Are You Explaining To? (XstrAI multi-agent XAI narratives) — audience-aware
  explanation generation, not applicable to Hermes agent internals.
- **2608.11027** Mapping and Measuring the Behavioral Evolution of LLMs — model comparison
  methodology, no concrete implementable technique for Hermes.
- **2608.11195** Long-Horizon AI Research for Grothendieck Constant — domain-specific math
  research case study, no generalised technique.
- **2608.11171** From Interpretability to Control (TrustNLP 6yr survey) — workshop survey,
  no new concrete technique.

---

## Search provenance

**Keyword searches (7 original + 12 additional):**
All used `order=-announced_date_first`. Top IDs per search were all ≤ 2608.10986 until
"language model agent planning" returned 2608.11033 as #1, and "artificial intelligence agent"
returned 2608.11191. The category recent-listing approach proved most effective — yielded all
37 new papers in a single pass.

**Category listing approach (recommended for future sweeps):**
```
https://arxiv.org/list/cs.AI/recent
https://arxiv.org/list/cs.CL/recent
https://arxiv.org/list/cs.MA/recent
https://arxiv.org/list/cs.CR/recent
https://arxiv.org/list/cs.LG/recent
https://arxiv.org/list/cs.IR/recent
https://arxiv.org/list/cs.SE/recent
```
Each returns the last 5 working days of submissions. Parse with:
`re.findall(r'\b(\d{4}\.\d{4,5})\b', content)` then filter by ID > baseline cutoff.
Fetch titles from the listing page (format: `\[N\] arXiv:ID ... Title: <title>`).
Then fetch abstracts via `web_extract(urls=[\"https://arxiv.org/abs/ID\"])` for candidates.
